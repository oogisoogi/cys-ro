#!/usr/bin/env python3
"""test_idle_gate.py — javis_idle_gate.py 계약 시험 + 「손을 빌리지 않기」 문서 계약 (TICKET=cysr-no-hands-gui-1118).

격리: 매 시험이 임시 상태 폴더(CYS_IDLE_STATE)와 가짜 시계 파일(CYS_IDLE_GATE_FAKE)을 세운다 — 실제 대기 0 ·
실제 OS 유휴 값 0 · 알림 0. 뮤턴트 하네스(mut_idle_gate.py)는 IG_MODULE 로 변이 사본을 가리키고 이 파일을 그대로 돌린다.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.dirname(BIN)
MOD_PATH = os.environ.get("IG_MODULE") or os.path.join(BIN, "javis_idle_gate.py")
CC_PATH = os.path.join(BIN, "javis_computer_control.py")

# 사용자에게 손·앱을 비켜 달라는 요청(존댓말 = 사용자에게 하는 말). 지침·스킬·도구 출력 어디에도 없어야 한다.
HANDS_OFF = [
    re.compile(r"(손|키보드|마우스)[을를에서]*\s*(잠깐|잠시|좀)?\s*(떼|놓|치워|멈춰|쉬어|비켜)\s*(주|줘|달라)"),
    re.compile(r"(쓰지|사용하지|만지지|건드리지|누르지|입력하지|움직이지|열지|조작하지)\s*(말아\s*)?(마세요|마시고|마십시오|마시기|주세요)"),
    re.compile(r"(잠깐|잠시)\s*(기다려|멈춰)\s*(주세요|주시겠)"),
]


def hands_off_hits(text):
    return [m.group(0) for rx in HANDS_OFF for m in rx.finditer(text or "")]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ig-ut-")
        self.state = os.path.join(self.tmp, "state")
        self.clock = os.path.join(self.tmp, "clock.json")
        self.set_clock(1000.0, [], front="com.example.UserApp")
        self.env = dict(os.environ, CYS_IDLE_STATE=self.state, CYS_IDLE_GATE_FAKE=self.clock,
                        CYS_IDLE_NO_NOTIFY="1", CYS_IDLE_PLATFORM="darwin")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def set_clock(self, t, inputs, **extra):
        d = dict(extra, now=t, inputs=inputs)
        with open(self.clock, "w", encoding="utf-8") as f:
            json.dump(d, f)

    def clock_get(self):
        with open(self.clock, encoding="utf-8") as f:
            return json.load(f)

    def user_input(self, at=None, **upd):
        d = self.clock_get()
        d["inputs"].append(d["now"] if at is None else at)
        d.update(upd)
        with open(self.clock, "w", encoding="utf-8") as f:
            json.dump(d, f)

    def advance(self, sec):
        d = self.clock_get()
        d["now"] += sec
        with open(self.clock, "w", encoding="utf-8") as f:
            json.dump(d, f)

    def run_gate(self, *args):
        r = subprocess.run([sys.executable, MOD_PATH] + list(args), env=self.env, capture_output=True, timeout=60)
        out = r.stdout.decode("utf-8").strip().splitlines()
        return r.returncode, (json.loads(out[-1]) if out else None)

    # ── 1. 20초 전에는 절대 go 하지 않는다 ──
    def test_no_go_before_20s_idle(self):
        self.set_clock(1000.0, [995.0], front="com.example.UserApp")      # 5초 전 타이핑
        rc, o = self.run_gate("wait", "--seconds", "20", "--timeout", "120", "--task", "한글 PDF 저장")
        self.assertEqual(rc, 0, o)
        self.assertTrue(o["go"])
        go_at = self.clock_get()["now"]
        self.assertGreaterEqual(go_at - 995.0, 20.0, "마지막 입력 뒤 20초가 안 됐는데 go")
        self.assertGreaterEqual(o["idle_secs"], 20.0)

    def test_already_idle_goes_immediately(self):
        self.set_clock(1000.0, [900.0])
        rc, o = self.run_gate("wait", "--seconds", "20", "--timeout", "5")
        self.assertEqual(rc, 0)
        self.assertTrue(o["go"])
        self.assertEqual(o["waited_secs"], 0.0)

    def test_keeps_typing_user_defers_not_fails(self):
        # 사용자가 계속 친다 = 매 초 입력 → 시간 초과 → 미룸(exit 3 · 실패 아님 · 대기열)
        self.set_clock(1000.0, [1000.0 + i for i in range(0, 200)])
        rc, o = self.run_gate("wait", "--seconds", "20", "--timeout", "60", "--task", "카톡 답장 보내기")
        self.assertEqual(rc, 3, o)
        self.assertFalse(o["go"])
        self.assertTrue(o["deferred"])
        self.assertEqual(o["reason"], "user_active")
        rc2, p = self.run_gate("pending")
        self.assertEqual(p["count"], 1)
        self.assertEqual(p["items"][0]["task"], "카톡 답장 보내기")
        self.assertFalse(os.path.exists(os.path.join(self.state, "idle-session.json")), "미룬 뒤 세션이 남음")
        # 같은 일을 다시 미뤄도 한 줄
        self.run_gate("wait", "--seconds", "20", "--timeout", "10", "--task", "카톡 답장 보내기")
        self.assertEqual(self.run_gate("pending")[1]["count"], 1)
        # 나중에 쉬실 때 같은 일로 통과하면 대기열에서 빠진다
        self.advance(500)
        rc3, o3 = self.run_gate("wait", "--seconds", "20", "--timeout", "10", "--task", "카톡 답장 보내기")
        self.assertEqual(rc3, 0)
        self.assertEqual(self.run_gate("pending")[1]["count"], 0)

    def test_unreadable_idle_is_not_idle(self):
        self.set_clock(1000.0, [], broken=True)
        rc, o = self.run_gate("wait", "--seconds", "20", "--timeout", "30", "--task", "x")
        self.assertEqual(rc, 3)
        self.assertEqual(o["reason"], "idle_unknown")

    def test_timeout_capped(self):
        self.set_clock(1000.0, [1000.0 + i for i in range(0, 2000)])
        rc, o = self.run_gate("wait", "--seconds", "20", "--timeout", "100000")
        self.assertEqual(rc, 3)
        self.assertLessEqual(o["waited_secs"], 540.0 + 1.0)

    # ── 2. 도중 입력 → 멈춤 → 쉬면 이어 함 ──
    def test_midway_user_input_pauses_then_resumes(self):
        self.set_clock(1000.0, [900.0])
        rc, o = self.run_gate("wait", "--seconds", "20", "--timeout", "10")
        self.assertTrue(o["go"])
        self.user_input()                 # 내 동작(앞으로 부르기) — 유휴 시계 0
        self.advance(0.2)
        self.assertEqual(self.run_gate("mark")[0], 0)
        self.advance(3)                   # 생각하는 3초 · 입력 없음
        rc, c = self.run_gate("check")
        self.assertEqual(rc, 0)
        self.assertTrue(c["go"])
        self.assertFalse(c["touched"])
        # 사용자가 다시 친다
        self.user_input()
        self.advance(1)
        before = self.clock_get()["now"]
        last_user = before - 1
        rc, c2 = self.run_gate("check", "--timeout", "120")
        self.assertEqual(rc, 0, c2)
        self.assertTrue(c2["touched"])
        self.assertTrue(c2["resumed"])
        self.assertGreaterEqual(self.clock_get()["now"] - last_user, 20.0, "사용자 입력 뒤 20초 전에 이어 함")
        # 재개 = 새 기준점 — 그 뒤 입력이 없으면 다음 check 는 다시 멈추지 않는다
        self.advance(5)
        rc, c3 = self.run_gate("check")
        self.assertEqual(rc, 0)
        self.assertFalse(c3["touched"], "재개 뒤 기준점이 옛 mark 에 남아 같은 입력으로 또 멈춤")
        rc, e = self.run_gate("end")
        self.assertEqual(e["pauses"], 1)

    def test_midway_user_keeps_typing_defers(self):
        self.set_clock(1000.0, [900.0])
        self.run_gate("wait", "--seconds", "20", "--timeout", "10", "--task", "한글 인쇄")
        self.run_gate("mark")
        d = self.clock_get()
        d["inputs"] += [d["now"] + 0.5 + i for i in range(0, 300)]
        with open(self.clock, "w", encoding="utf-8") as f:
            json.dump(d, f)
        self.advance(2)
        rc, c = self.run_gate("check", "--timeout", "30")
        self.assertEqual(rc, 3)
        self.assertTrue(c["deferred"])
        self.assertEqual(self.run_gate("pending")[1]["items"][0]["task"], "한글 인쇄")
        self.assertEqual(self.run_gate("check")[0], 2, "미룬 뒤에도 세션이 살아 있음")

    def test_check_without_wait_refuses(self):
        self.assertEqual(self.run_gate("check")[0], 2)
        self.assertEqual(self.run_gate("mark")[0], 2)

    def test_start_and_end_notice_say(self):
        self.set_clock(1000.0, [900.0], front="com.example.UserApp")
        rc, o = self.run_gate("wait", "--est", "15")
        self.assertIn("잠깐 화면을 씁니다(약 15초)", o["say"])
        self.assertEqual(o["front_app"], "com.example.UserApp")
        self.advance(12)
        rc, e = self.run_gate("end", "--restore")
        self.assertTrue(e["ended"])
        self.assertEqual(e["used_secs"], 12)
        self.assertIn("마쳤습니다", e["say"])

    def test_unsupported_platform_defers(self):
        env = dict(self.env, CYS_IDLE_PLATFORM="other")
        env.pop("CYS_IDLE_GATE_FAKE")
        r = subprocess.run([sys.executable, MOD_PATH, "wait", "--task", "y"], env=env, capture_output=True, timeout=30)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(json.loads(r.stdout)["reason"], "unsupported_platform")

    def test_done_removes_pending(self):
        self.set_clock(1000.0, [1000.0 + i for i in range(0, 100)])
        rc, o = self.run_gate("wait", "--timeout", "10", "--task", "z")
        self.assertEqual(self.run_gate("done", "--id", o["id"])[0], 0)
        self.assertEqual(self.run_gate("pending")[1]["count"], 0)
        self.assertEqual(self.run_gate("done", "--id", "nope")[0], 4)


class Sources(unittest.TestCase):
    """OS 원천 파서 — 맥 ioreg · 윈 GetLastInputInfo(가짜 user32/kernel32 · 32비트 감김)."""
    def setUp(self):
        self.m = load(MOD_PATH, "javis_idle_gate_src")

    def test_mac_ioreg_parse(self):
        txt = '+-o IOHIDSystem  <class IOHIDSystem>\n    {\n      "HIDIdleTime" = 20415437291\n    }\n'
        self.assertAlmostEqual(self.m.parse_hid_idle(txt), 20.415437291)
        self.assertIsNone(self.m.parse_hid_idle(""))
        self.assertIsNone(self.m.parse_hid_idle(None))

    def _fake_win(self, last, tick, ok=True):
        class U:
            def GetLastInputInfo(self, ref):
                ref._obj.dwTime = last
                return 1 if ok else 0

        class K:
            def GetTickCount(self):
                return tick
        return U(), K()

    def test_win_idle(self):
        u, k = self._fake_win(10_000, 35_500)
        self.assertAlmostEqual(self.m.win_idle_secs(u, k), 25.5)

    def test_win_idle_tick_wraparound(self):
        u, k = self._fake_win(0xFFFFFFFF - 999, 4_000)       # 49.7일 감김 뒤
        self.assertAlmostEqual(self.m.win_idle_secs(u, k), 5.0)

    def test_win_idle_failure_is_none(self):
        u, k = self._fake_win(0, 0, ok=False)
        self.assertIsNone(self.m.win_idle_secs(u, k))


class Docs(unittest.TestCase):
    """손을 빌리지 않기 — 지침·스킬·도구 출력 계약."""
    @staticmethod
    def read(rel):
        with open(os.path.join(PACK, rel), encoding="utf-8") as f:
            return f.read()

    def test_no_hands_off_request_anywhere(self):
        texts = {rel: self.read(rel) for rel in (
            "skills/computer-control/SKILL.md", "skills/hwp/SKILL.md", "skills/rhwp-edit/SKILL.md",
            "directives/MASTER_DIRECTIVE.md", "directives/CEO_TEMPLATE.md", "directives/WORKER_DIRECTIVE.md")}
        ig = load(MOD_PATH, "javis_idle_gate_docs")
        for k in ("START_SAY", "DEFER_SAY", "END_SAY", "NO_IDLE_SAY"):
            texts["idle_gate." + k] = getattr(ig, k)
        cc = load(CC_PATH, "javis_computer_control_docs")
        for cat, row in cc.CATEGORIES.items():
            texts["computer_control.CATEGORIES." + cat] = " ".join(str(x) for x in row)
        for row in cc.MAC_APPS:
            texts["computer_control.MAC_APPS." + row[0]] = row[3]
        for name, t in texts.items():
            with self.subTest(src=name):
                self.assertEqual(hands_off_hits(t), [])

    def test_detector_catches_requests(self):
        for s in ("잠깐만 키보드에서 손을 떼 주세요", "손을 잠시 떼 주시겠어요", "작업 중에는 한글 파일을 쓰지 마세요",
                  "제가 하는 동안 마우스를 만지지 마시고", "잠시 기다려 주세요"):
            with self.subTest(s=s):
                self.assertTrue(hands_off_hits(s), s)
        for s in ("하시던 일은 그대로 하셔도 됩니다", "키보드나 마우스를 쓰시면 제가 멈췄다가 쉬실 때 이어 합니다"):
            with self.subTest(s=s):
                self.assertEqual(hands_off_hits(s), [])

    def test_skill_carries_no_hands_rules(self):
        s = self.read("skills/computer-control/SKILL.md")
        self.assertIn("## 사용자가 일하는 동안 — 손을 빌리지 않기", s)
        for need in ("javis_idle_gate.py", "wait --seconds 20", "mark", "check", "end", "백그라운드",
                     "hwp", "rhwp-edit", "사본", "대기열"):
            with self.subTest(need=need):
                self.assertIn(need, s)
        self.assertNotIn("맥 한글은 화면 조작만", s)

    def test_hwp_note_files_first(self):
        cc = load(CC_PATH, "javis_computer_control_hwp")
        note = dict((r[0], r[3]) for r in cc.MAC_APPS)["hwp"]
        self.assertNotIn("화면 조작으로만", note)
        self.assertIn("파일", note)

    def test_master_directive_section(self):
        for rel in ("directives/MASTER_DIRECTIVE.md", "directives/CEO_TEMPLATE.md"):
            with self.subTest(rel=rel):
                t = self.read(rel)
                self.assertIn("## ★ 사용자와 함께 쓰는 컴퓨터 — 손을 빌리지 않기 (1.1.16)", t)
                self.assertIn("javis_idle_gate.py", t)


if __name__ == "__main__":
    unittest.main()
