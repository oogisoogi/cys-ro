#!/usr/bin/env python3
"""test_awaken_seat_fold — ★D6(1.1.8 · 윈 실측): 263행 지침 붙여넣기가 제출되지 않은 채 311·312초 멈춤(사람 Return 1회로 풀림).

팩 쪽 몫(각성 보장 루프 javis_awaken.ensure_awake) 두 가지:
  ① 판정 대상 = 데몬이 아는 **그 좌석의** 세션 파일(`cys status --json` usage.session_file · 이번 스폰 이후 갱신값만).
     cwd 폴더 훑기는 같은 cwd 를 쓰는 부모·형제 좌석의 새 user 레코드를 자식의 제출로 셀 수 있다(거짓 확인 → Return 생략).
  ② 길이 무관 — 기본 창(17.5초)이 끝났는데 입력줄에 「[Pasted text」 접힘이 남아 있으면 Return 을 더 보낸다(13·21초).
     판정은 여전히 jsonl · 입력줄 실측은 연장 여부만 · 입양 좌석(may_return=False)엔 여전히 Return 0.
"""
import datetime
import importlib.util
import json
import os
import shutil
import tempfile
import time
import unittest

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("javis_awaken_d6", os.path.join(BIN, "javis_awaken.py"))
aw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aw)


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def append(path, recs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def user(cwd, t, content="# CSO ABSOLUTE DIRECTIVE"):
    return {"type": "user", "cwd": cwd, "timestamp": iso(t), "message": {"role": "user", "content": content}}


class Fake:
    """cys 대역 — status --json(좌석 세션 파일) · read-screen(입력줄) · send-key Return."""

    def __init__(self, surface, seat_file=None, updated_at=None, screen="", on_return=None):
        self.surface, self.seat_file, self.updated_at = surface, seat_file, updated_at
        self.screen, self.on_return, self.calls = screen, on_return, []

    def __call__(self, args):
        args = list(args)
        self.calls.append(args)
        if args[:2] == ["status", "--json"]:
            rows = [{"surface_ref": "surface:1", "usage": {"session_file": "/nope/other.jsonl", "updated_at": time.time()}}]
            if self.seat_file:
                rows.append({"surface_ref": self.surface,
                             "usage": {"session_file": self.seat_file, "updated_at": self.updated_at}})
            return 0, json.dumps({"surfaces": rows})
        if args[:1] == ["read-screen"]:
            return 0, self.screen(self) if callable(self.screen) else self.screen
        if args[:1] == ["send-key"] and "Return" in args:
            if self.on_return:
                self.on_return(self)
            return 0, ""
        return 0, ""

    def returns(self):
        return [c for c in self.calls if c[:1] == ["send-key"]]


FOLD_SCREEN = "╭────╮\n│ ❯ [Pasted text #1 +263 lines]\n╰────╯\n  ? for shortcuts\n"


class T(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="aw-d6-")
        self._st = os.environ.get("CYS_STATE_DIR")
        os.environ["CYS_STATE_DIR"] = os.path.join(self.root, "state")
        self.cwd = "/tmp/jarvis-home/hub"
        self.cfg = os.path.join(self.root, "claude")
        self.slugdir = os.path.join(self.cfg, "projects", aw.slug(self.cwd))
        self.since = time.time()
        self.child = os.path.join(self.slugdir, "child.jsonl")
        self.sibling = os.path.join(self.slugdir, "parent.jsonl")
        # 부모(스폰한 CEO) 세션: 스폰 전부터 있고, 스폰 뒤에도 도구 결과(user 레코드)가 붙는다 — 같은 cwd.
        append(self.sibling, [user(self.cwd, self.since - 600, "선언"),
                              {"type": "user", "cwd": self.cwd, "timestamp": iso(self.since + 0.5),
                               "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}}])
        os.utime(self.sibling, None)
        append(self.child, [{"type": "attachment", "cwd": self.cwd, "timestamp": iso(self.since + 0.2)}])

    def tearDown(self):
        if self._st is None:
            os.environ.pop("CYS_STATE_DIR", None)
        else:
            os.environ["CYS_STATE_DIR"] = self._st
        shutil.rmtree(self.root, ignore_errors=True)

    def ensure(self, fake, **kw):
        return aw.ensure_awake("cso", "surface:103", self.cwd, self.since, fake, pid=7,
                               dirs=[self.cfg], sleep=lambda s: None, report=False, **kw)

    def test_old_scan_false_confirms_on_sibling(self):
        # 대조(문제 실증): 좌석 세션 파일을 모르면 cwd 훑기가 부모의 도구 결과를 「제출」로 센다.
        r = self.ensure(Fake("surface:103"))
        self.assertEqual(r["awaken"], aw.AWAKEN_CONFIRMED)
        self.assertEqual(r["returns_sent"], 0)

    def test_seat_file_ignores_sibling_and_returns(self):
        f = Fake("surface:103", seat_file=self.child, updated_at=self.since + 1)
        r = self.ensure(f)
        self.assertEqual(r["awaken"], aw.AWAKEN_UNCONFIRMED, r["evidence"])
        self.assertEqual(r["evidence"]["source"], "seat")
        self.assertEqual(r["evidence"]["jsonl"], [self.child])
        self.assertEqual(r["returns_sent"], 3)

    def test_seat_file_confirms_on_child_submit(self):
        f = Fake("surface:103", seat_file=self.child, updated_at=self.since + 1,
                 on_return=lambda s: append(self.child, [user(self.cwd, time.time())]))
        r = self.ensure(f)
        self.assertEqual((r["awaken"], r["returns_sent"], r["evidence"]["source"]),
                         (aw.AWAKEN_CONFIRMED, 1, "seat"))

    def test_stale_seat_usage_falls_back(self):
        # 지난 세대의 usage(스폰 이전 갱신) = 이 좌석의 것이라 단정 못 한다 → 종전 훑기.
        f = Fake("surface:103", seat_file=self.child, updated_at=self.since - 3600)
        r = self.ensure(f)
        self.assertNotEqual(r["evidence"]["source"], "seat")

    def test_fold_extends_window_until_submit(self):
        n = {"k": 0}

        def on_ret(s):
            n["k"] += 1
            if n["k"] == 5:   # 콜드스타트가 늦어 다섯 번째 Return 에서야 TUI 가 받는다
                append(self.child, [user(self.cwd, time.time())])
        f = Fake("surface:103", seat_file=self.child, updated_at=self.since + 1, screen=FOLD_SCREEN, on_return=on_ret)
        r = self.ensure(f)
        self.assertEqual(r["awaken"], aw.AWAKEN_CONFIRMED, r)
        self.assertEqual(r["returns_sent"], 5)
        self.assertTrue(r["evidence"]["fold_seen"])

    def test_fold_extension_is_bounded(self):
        f = Fake("surface:103", seat_file=self.child, updated_at=self.since + 1, screen=FOLD_SCREEN)
        r = self.ensure(f)
        self.assertEqual((r["awaken"], r["returns_sent"]),
                         (aw.AWAKEN_UNCONFIRMED, len(aw.RETRY_WAITS_S) + len(aw.EXTEND_WAITS_S)))
        self.assertEqual(len([c for c in f.calls if c[:1] == ["read-screen"]]), 1, "입력줄 실측은 1회")

    def test_no_fold_no_extension(self):
        f = Fake("surface:103", seat_file=self.child, updated_at=self.since + 1, screen="❯ \n  ? for shortcuts\n")
        r = self.ensure(f)
        self.assertEqual((r["returns_sent"], r["evidence"]["fold_seen"]), (3, False))

    def test_fold_far_above_input_is_not_input(self):
        # 대화 본문 위쪽에 인용된 「[Pasted text」 는 입력줄이 아니다(화면 끝 FOLD_TAIL_LINES 줄만 본다).
        screen = "[Pasted text #1 +5 lines] 라는 말이 대화에 있었다\n" + "본문\n" * 40 + "❯ \n"
        f = Fake("surface:103", seat_file=self.child, updated_at=self.since + 1, screen=screen)
        self.assertEqual(self.ensure(f)["returns_sent"], 3)

    def test_adopted_seat_never_returns_even_with_fold(self):
        f = Fake("surface:103", seat_file=self.child, updated_at=self.since + 1, screen=FOLD_SCREEN)
        r = self.ensure(f, may_return=False)
        self.assertEqual((r["returns_sent"], f.returns()), (0, []))


if __name__ == "__main__":
    unittest.main()
