#!/usr/bin/env python3
"""test_javis_counsel — ★T3(agora-t3-pack-collector): 상담소 자동 전달의 팩 쪽(`bin/javis_counsel.py`).

지키는 것(agora 클라이언트 `collector.py`·`mail.py` 와 글자 그대로 같은 계약):
  ① 신호 줄 정규식(ts·source·op·error_code·version·os) 수용/거부 벡터 · 형식 밖 줄은 안 쓴다
  ② CYS_ROLE → source 표 · 끄기 규칙 표(config.json 7행) · 2MB 넘으면 버림 · CRLF 0 · 한 줄 = 정렬 키 압축 JSON
  ③ 잠금 — 남이 쥐고 있으면 상한(기본 2초) 뒤 버리고 exit 0(훅을 붙잡지 않는다)
  ④ facts — 가짜 cys(PATH 대역)·가짜 상태 파일로 칸별 산출 · 못 잰 칸은 뺀다(null 0)
  ⑤ ensure-client — 올바른 sha = 설치+.pin · 틀린 sha = 거부 · zip-slip = 거부 · 판정 = 트리 지문(같음 = 무동작 ·
     알려진 옛 판 = 교체 · 고친/모르는 트리 = 불가침) · 설치 잠금(대기/포기) · 남의 lib 위로 rename 0
  ⑥ tick — 가짜 `lib/bin/agora` 가 받은 인자·AGORA_SIGNING_KEY · 한 판 상한 540초(시간 초과 = 프로세스 그룹째 끝냄)
  ⑧ 팩 쓰기(`signal` 다중 프로세스) ↔ 동봉 아고라 `collector.move_sent` 교차 잠금 경합 — 줄 유실·중복 0 · LF
  ⑦ preflight 신호 블록(C 번호 FAIL/WARN → 한 실행 안 중복 0) · cys-dept EXIT trap(rc 보존 + 신호 1줄)

실행: python3 test_javis_counsel.py   (unittest · 저장소 관례)
"""
import base64
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile

sys.dont_write_bytecode = True   # 저장소 bin/ 에 __pycache__ 를 남기지 않는다
TESTS = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(TESTS)
if BIN not in sys.path:
    sys.path.insert(0, BIN)
import javis_counsel as jc  # noqa: E402

SCRIPT = os.path.join(BIN, "javis_counsel.py")
NOW = 1791200000.0   # 2026-10-05T…Z 고정 시각


def rd(path, mode="r", encoding=None):
    with open(path, mode, encoding=encoding) as f:
        return f.read()


@contextlib.contextmanager
def envset(**kv):
    old = {k: os.environ.get(k) for k in kv}
    try:
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jc-")
        self.cfg = os.path.join(self.tmp, "cfg")
        self.pack = os.path.join(self.tmp, "pack")
        os.makedirs(os.path.join(self.pack, "bin"))
        with open(os.path.join(self.pack, ".pack-version"), "w") as f:
            f.write("1.1.8\n")
        shutil.copy(SCRIPT, os.path.join(self.pack, "bin", "javis_counsel.py"))
        self._env = envset(AGORA_CONFIG_DIR=self.cfg, CYS_PACK_DIR=self.pack)
        self._env.__enter__()

    def tearDown(self):
        self._env.__exit__(None, None, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sig_path(self):
        return os.path.join(self.cfg, "counsel", "signals.jsonl")

    def sig_lines(self):
        p = self.sig_path()
        if not os.path.exists(p):
            return []
        return rd(p, "rb").decode("utf-8").split("\n")[:-1]

    def config(self, doc_text):
        os.makedirs(self.cfg, exist_ok=True)
        with open(os.path.join(self.cfg, "config.json"), "w", encoding="utf-8") as f:
            f.write(doc_text)


class Regex(unittest.TestCase):
    def test_vectors(self):
        cases = {
            jc.TS_RE: (["2026-10-06T01:02:03.004Z"],
                       ["2026-10-06T01:02:03Z", "2026-10-06T01:02:03.004Z\n", "2026-10-06 01:02:03.004Z",
                        "２026-10-06T01:02:03.004Z", "2026-10-06T01:02:03.0045Z"]),
            jc.OP_RE: (["hook.session-start", "a", "preflight.c03", "x" * 32],
                       ["", "x" * 33, "Hook", "a b", "op\n", "가"]),
            jc.ERROR_CODE_RE: (["hook.rc127", "doctor.c03.fail", "e" * 48],
                               ["", "e" * 49, "RC", "a/b", "a\n"]),
            jc.VERSION_RE: (["1.1.8", "1.1.8-rc.1+b2", "v" * 32], ["", "v" * 33, "1.1 8", "1.1.8\n"]),
            jc.OS_RE: (["macos", "macos-15.6", "windows-10", "linux", "linux-6.1"],
                       ["darwin", "macos-", "macos-15.6a", "windows-" + "1" * 17, "macos-15.6\n"]),
        }
        for rx, (good, bad) in cases.items():
            for v in good:
                self.assertTrue(rx.match(v), (rx.pattern, v))
            for v in bad:
                self.assertFalse(rx.match(v), (rx.pattern, v))

    def test_source_map(self):
        table = {"master": "master", "cso": "cso", "cso-2": "cso", "worker": "worker", "worker-3": "worker",
                 "worker-eduscan": "worker", "reviewer": "worker", "reviewer-codex": "worker", "planner": "worker",
                 "planner-x": "worker", "pack": "pack", "update": "update", "": "pack", "ceo": "pack",
                 "master-2": "pack", "workers": "pack", "csox": "pack", "MASTER": "master", None: "pack"}
        for k, v in table.items():
            self.assertEqual(jc.map_source(k), v, k)

    def test_make_row_validates(self):
        ok = jc.make_row("worker-3", "Hook.X", "HOOK.RC1", now=NOW, version="1.1.8", os_name="macos-15.6")
        self.assertEqual(ok, {"ts": "2026-10-05T11:33:20.000Z", "source": "worker", "op": "hook.x",
                              "error_code": "hook.rc1", "version": "1.1.8", "os": "macos-15.6"})
        self.assertIsNone(jc.make_row("cso", "hook.가", "x", now=NOW, version="1.1.8", os_name="linux"))
        self.assertIsNone(jc.make_row("cso", "x", "", now=NOW, version="1.1.8", os_name="linux"))
        self.assertIsNone(jc.make_row("cso", "x", "y", now=NOW, version="1 1", os_name="linux"))
        self.assertIsNone(jc.make_row("cso", "x", "y", now=NOW, version="1.1", os_name="darwin"))
        self.assertTrue(jc.OS_RE.match(jc.os_tag()), jc.os_tag())


class Signal(Base):
    def test_line_shape_lf_sorted(self):
        self.assertTrue(jc.write_signal("cso", "hook.session-start", "hook.rc127", now=NOW))
        raw = rd(self.sig_path(), "rb")
        self.assertNotIn(b"\r", raw)
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(raw.endswith(b"\n"))
        line = raw.decode("utf-8")[:-1]
        row = json.loads(line)
        self.assertEqual(line, json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        self.assertEqual((row["source"], row["op"], row["error_code"], row["version"]),
                         ("cso", "hook.session-start", "hook.rc127", "1.1.8"))
        self.assertTrue(jc.TS_RE.match(row["ts"]))
        self.assertFalse(os.path.getsize(os.path.join(self.cfg, "counsel", "signals.lock")),
                         "잠금 파일에 내용이 쓰였다")

    def test_invalid_row_not_written(self):
        self.assertFalse(jc.write_signal("cso", "bad op", "x"))
        self.assertEqual(self.sig_lines(), [])

    def test_no_pack_version_writes_nothing(self):
        os.remove(os.path.join(self.pack, ".pack-version"))
        self.assertFalse(jc.write_signal("cso", "a", "b"))
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "counsel")), "판본 모름인데 폴더를 만들었다")

    def test_off_switch_table(self):
        table = [
            (None, True),                                        # config.json 없음 = 켬
            ("{", False),                                        # 못 읽음 = 끔
            ("[]", False),                                       # 객체 아님 = 끔
            ('{"relay": {}}', True),                             # counsel 없음 = 켬
            ('{"counsel": true}', False),                        # counsel 객체 아님 = 끔
            ('{"counsel": {}}', True),                           # auto 없음 = 켬
            ('{"counsel": {"auto": true}}', True),
            ('{"counsel": {"auto": false}}', False),
            ('{"counsel": {"auto": 1}}', False),                 # 정확히 true 만
            ('{"counsel": {"auto": "true"}}', False),
        ]
        for text, want in table:
            shutil.rmtree(self.cfg, ignore_errors=True)
            if text is not None:
                self.config(text)
            self.assertEqual(jc.auto_enabled(self.cfg), want, text)
            self.assertEqual(jc.write_signal("pack", "a", "b"), want, text)
            self.assertEqual(len(self.sig_lines()), 1 if want else 0, text)

    def test_2mb_guard(self):
        os.makedirs(os.path.join(self.cfg, "counsel"))
        with open(self.sig_path(), "wb") as f:
            f.write(b"x" * (2 * 1024 * 1024 + 1))
        self.assertFalse(jc.write_signal("pack", "a", "b"))
        self.assertEqual(os.path.getsize(self.sig_path()), 2 * 1024 * 1024 + 1)
        with open(self.sig_path(), "wb") as f:
            f.write(b"x" * (2 * 1024 * 1024))
        self.assertTrue(jc.write_signal("pack", "a", "b"), "정확히 2MB 는 「넘음」이 아니다")

    def test_lock_held_drops_after_timeout(self):
        os.makedirs(os.path.join(self.cfg, "counsel"))
        holder = jc._acquire(os.path.join(self.cfg, "counsel", "signals.lock"), 0)
        self.assertIsNotNone(holder)
        try:
            t0 = time.monotonic()
            self.assertEqual(jc.write_signals("pack", [("a", "b")], wait_s=0.4), 0)
            self.assertGreaterEqual(time.monotonic() - t0, 0.35)
            # 기본 상한(2초) — CLI 가 버리고 exit 0
            t0 = time.monotonic()
            r = subprocess.run([sys.executable, SCRIPT, "signal", "--source", "cso", "--op", "a",
                                "--error-code", "b"], capture_output=True, timeout=30)
            dt = time.monotonic() - t0
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""))
            self.assertGreaterEqual(dt, 1.9)
            self.assertLess(dt, 10)
            self.assertEqual(self.sig_lines(), [])
        finally:
            jc._unlock(holder)
            holder.close()
        self.assertTrue(jc.write_signal("pack", "a", "b"), "놓은 뒤에는 써야 한다")

    def test_cli_always_zero(self):
        for argv in ([], ["nope"], ["signal"], ["signal", "--op"]):
            r = subprocess.run([sys.executable, SCRIPT] + argv, capture_output=True, timeout=30)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""), argv)
        r = subprocess.run([sys.executable, SCRIPT, "signal", "--source", "worker-2", "--op", "Hook.X",
                            "--error-code", "hook.rc1"], capture_output=True, timeout=30)
        self.assertEqual(r.returncode, 0)
        rows = [json.loads(x) for x in self.sig_lines()]
        self.assertEqual([(x["source"], x["op"]) for x in rows], [("worker", "hook.x")])

    def _off_race(self, actor):
        """첫 끄기 확인 통과 → (이음새) actor 가 끈다 → 쓰는 쪽 재개. 쓴 줄 수."""
        jc._BEFORE_SIGNALS_LOCK = actor
        try:
            return jc.write_signals("pack", [("a", "b")])
        finally:
            jc._BEFORE_SIGNALS_LOCK = None

    def test_off_between_check_and_lock_writes_nothing(self):
        """★리뷰 3R ① — 아고라 set_auto 꼴: 설정 끔 → signals.lock 쥐고 지움 → 놓음. 그 뒤 잠금을 잡은 쓰는 쪽 = 0줄."""
        self.assertEqual(jc.write_signals("pack", [("x", "y")]), 1)

        def agora_off():
            self.config('{"counsel": {"auto": false}}')
            fh = jc._acquire(os.path.join(self.cfg, "counsel", "signals.lock"), 2)
            try:
                open(self.sig_path(), "w").close()
            finally:
                jc._unlock(fh)
                fh.close()
        self.assertEqual(self._off_race(agora_off), 0)
        self.assertEqual(self.sig_lines(), [], "끈 뒤에 새 줄이 생겼다")

    def test_off_while_writer_waits_on_lock(self):
        """끄는 쪽이 잠금을 쥔 채 끄고 잠시 머문다 — 쓰는 쪽은 잠금을 기다렸다 잡은 뒤 재확인에서 멈춘다."""
        held, release = threading.Event(), threading.Event()

        def holder():
            fh = jc._acquire(os.path.join(self.cfg, "counsel", "signals.lock"), 2)
            self.config('{"counsel": {"auto": false}}')
            held.set()
            release.wait(5)
            jc._unlock(fh)
            fh.close()
        th = threading.Thread(target=holder)

        def actor():
            th.start()
            held.wait(5)
            threading.Timer(0.3, release.set).start()
        self.assertEqual(self._off_race(actor), 0)
        th.join()
        self.assertEqual(self.sig_lines(), [])

    def test_off_by_real_agora_set_auto(self):
        """동봉 아고라의 진짜 `collector.set_auto(on=False)`(별 프로세스)가 끼어들어도 0줄."""
        client = bundled_client(os.path.join(self.tmp, "client"))
        code = ("import sys; sys.dont_write_bytecode = True; sys.path.insert(0, sys.argv[1]);"
                "from agora import collector; collector.set_auto(sys.argv[2], on=False)")

        def actor():
            r = subprocess.run([sys.executable, "-c", code, client, self.cfg], capture_output=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-600:])
        self.assertEqual(self._off_race(actor), 0)
        self.assertFalse(jc.auto_enabled(self.cfg))
        self.assertEqual(self.sig_lines(), [])

    def test_batch_one_lock(self):
        self.assertEqual(jc.write_signals("pack", [("a", "b"), ("bad op", "x"), ("c", "d")]), 2)
        self.assertEqual([json.loads(x)["op"] for x in self.sig_lines()], ["a", "c"])


class FakeCys(Base):
    """PATH 앞에 가짜 `cys`(sh) — version·list·doctor 를 준다."""

    def make_cys(self, list_text, doctor_text, list_rc=0):
        d = os.path.join(self.tmp, "fakebin")
        os.makedirs(d, exist_ok=True)
        for name, text in (("list.txt", list_text), ("doctor.json", doctor_text)):
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(text)
        p = os.path.join(d, "cys")
        with open(p, "w") as f:
            f.write('#!/bin/sh\nD="$(dirname "$0")"\ncase "$1" in\n'
                    '  --version) echo "cysr 1.1.8" ;;\n'
                    '  list) cat "$D/list.txt"; exit %d ;;\n'
                    '  doctor) cat "$D/doctor.json"; exit 1 ;;\n'
                    'esac\n' % list_rc)
        os.chmod(p, 0o755)
        return d


class Facts(FakeCys):
    def test_facts_end_to_end(self):
        fb = self.make_cys(
            "surface:1\trole=master\tpid=1\texited=false\tno=1\tx\t/a\n"
            "surface:2\trole=worker-3\tpid=2\texited=false\tno=2\tx\t/b\n"
            "surface:3\trole=worker-3\tpid=3\texited=false\tno=3\tx\t/c\n"
            "surface:4\trole=cso\tpid=4\texited=true\tno=4\tx\t/d\n"
            "surface:5\trole=\tpid=5\texited=false\tno=5\tx\t/e\n"
            "surface:6\trole=Bad_Role\tpid=6\texited=false\tno=6\tx\t/f\n",
            json.dumps({"fix": False, "summary": {"ok": 12, "warn": 2, "fail": 1, "skip": 2},
                        "items": [{"name": "pack-version", "status": "OK"},
                                  {"name": "dept-awakening-seed", "status": "WARN"},
                                  {"name": "hook", "status": "WARN"},
                                  {"name": "Bad Name", "status": "WARN"},
                                  {"name": "socket", "status": "FAIL"},
                                  {"name": "app-seal", "status": "SKIP"}]}))
        home = os.path.join(self.tmp, "home")
        st = os.path.join(self.tmp, "state")
        req = os.path.join(self.tmp, "req")
        for d in (st, req, os.path.join(home, ".local", "state", "cys")):
            os.makedirs(d)
        now = time.time()
        os.makedirs(os.path.join(self.cfg, "counsel"))
        since = now - 3600
        with open(os.path.join(self.cfg, "counsel", "state.json"), "w") as f:
            json.dump({"daily_ok_at": jc.ms_iso(since)}, f)
        loc = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))
        utc = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
        with open(os.path.join(req, "tick-errors.log"), "w", encoding="utf-8") as f:
            f.write("%s old\n%s new1\n%s new2\ngarbage\n" % (loc(since - 60), loc(since + 60), loc(now - 5)))
        with open(os.path.join(st, "hook-errors.log.1"), "w", encoding="utf-8") as f:
            f.write("%s h role=x rc=1\n%s h role=x rc=2\n" % (utc(since - 10), utc(since + 10)))
        with open(os.path.join(st, "hook-errors.log"), "w", encoding="utf-8") as f:
            f.write("%s h rc=1\n시각불명(date 없음) h rc=127\n" % utc(now - 1))
        depts = os.path.join(self.tmp, "depts.json")
        with open(depts, "w") as f:
            json.dump({"depts": {"a": {}, "b": {}}}, f)
        with open(os.path.join(home, ".local", "state", "cys", "dept_tombstones.json"), "w") as f:
            json.dump({"dept_tombstones": ["x", "y", "z"]}, f)
        started = int(now) - 7200
        with open(os.path.join(st, "delivery-base.epoch.json"), "w") as f:
            json.dump({"daemon_epoch": started + 0.5, "started": utc(started), "pid": 1, "v": 1}, f)
        env = dict(os.environ, PATH=fb + os.pathsep + os.environ.get("PATH", ""), HOME=home, CYS_STATE_DIR=st,
                   CYS_DEPT_REQUESTS=req, CYS_DEPTS_JSON=depts, LOCALAPPDATA=os.path.join(home, "la"))
        env.pop("CYS_CYS_BIN", None)
        r = subprocess.run([sys.executable, SCRIPT, "facts"], capture_output=True, env=env, timeout=60)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""))
        raw = rd(os.path.join(self.cfg, "counsel", "facts.json"), "rb")
        self.assertNotIn(b"\r", raw)
        facts = json.loads(raw)
        self.assertEqual(facts["version"], {"host": "1.1.8", "pack": "1.1.8"})
        self.assertTrue(jc.OS_RE.match(facts["os"]))
        self.assertEqual(facts["seats"], {"count": 5, "roles": ["master", "pack", "worker"]},
                         "비종료 5 · 역할은 범주로 접는다(원 이름 0 · 빈 값·형식 밖 = pack)")
        self.assertNotIn(b"worker-3", raw, "원 역할 이름이 실렸다")
        self.assertEqual(facts["doctor"], {"ok": 12, "warn": 2, "fail": 1, "skip": 2,
                                           "warn_ids": ["dept-awakening-seed", "hook"], "fail_ids": ["socket"]})
        self.assertEqual(facts["errors"], {"tick_errors": 2, "hook_rc_nonzero": 2})
        self.assertEqual(facts["depts"], {"active": 2, "tombstones": 3})
        self.assertEqual(facts["uptime"]["last_boot"], jc.ms_iso(started))
        self.assertTrue(7195 <= facts["uptime"]["uptime_s"] <= 7300, facts["uptime"])
        self.assertEqual([n for n in os.listdir(os.path.join(self.cfg, "counsel")) if ".tmp-" in n], [])

    def test_unmeasurable_keys_omitted(self):
        home = os.path.join(self.tmp, "home")
        os.makedirs(home)
        empty = os.path.join(self.tmp, "emptybin")
        os.makedirs(empty)
        bad = os.path.join(self.tmp, "bad.json")
        with open(bad, "w") as f:
            f.write("{")
        env = dict(os.environ, PATH=empty, HOME=home, CYS_STATE_DIR=os.path.join(self.tmp, "nostate"),
                   CYS_DEPT_REQUESTS=os.path.join(self.tmp, "noreq"), CYS_DEPTS_JSON=bad)
        env.pop("CYS_CYS_BIN", None)
        r = subprocess.run([sys.executable, SCRIPT, "facts"], capture_output=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 0)
        facts = json.loads(rd(os.path.join(self.cfg, "counsel", "facts.json")))
        self.assertEqual(facts["version"], {"pack": "1.1.8"}, "cys 없음 = host 칸만 빠진다")
        for k in ("seats", "doctor", "depts", "uptime"):
            self.assertNotIn(k, facts, k)
        self.assertEqual(facts["errors"], {"tick_errors": 0, "hook_rc_nonzero": 0}, "로그 없음 = 0건(잰 값)")
        self.assertNotIn(None, facts.values())

    def test_list_failure_omits_seats(self):
        fb = self.make_cys("surface:1\trole=master\texited=false\n", "not json", list_rc=1)
        env = dict(os.environ, PATH=fb + os.pathsep + os.environ.get("PATH", ""))
        env.pop("CYS_CYS_BIN", None)
        with envset(PATH=env["PATH"], CYS_CYS_BIN=None):
            self.assertIsNone(jc.probe_seats())
            self.assertIsNone(jc.probe_doctor())

    def test_seat_category_table(self):
        table = {"master": "master", "MASTER": "master", "cso": "cso", "cso-2": "cso", "cso-fresh-1791200000": "cso",
                 "worker": "worker", "worker-3": "worker", "worker-oogisoogi-mbp": "worker", "reviewer": "worker",
                 "reviewer-codex": "worker", "reviewers": "worker", "planner": "worker", "planner-x": "worker",
                 "master-2": "pack", "csox": "pack", "workers": "pack", "update": "pack", "pack": "pack",
                 "ceo": "pack", "": "pack", None: "pack", "kim-macbook": "pack"}
        for k, v in table.items():
            self.assertEqual(jc.seat_category(k), v, k)
        fb = self.make_cys("surface:1\trole=worker-kim-imac\texited=false\n"
                           "surface:2\trole=cso-fresh-9\texited=false\n"
                           "surface:3\trole=hong-desk\texited=false\n"
                           "surface:4\trole=master\texited=true\n", "{}")
        with envset(PATH=fb + os.pathsep + os.environ.get("PATH", ""), CYS_CYS_BIN=None):
            self.assertEqual(jc.probe_seats(), {"count": 3, "roles": ["cso", "pack", "worker"]})

    def test_since_default_24h(self):
        self.assertEqual(jc.since_epoch(self.cfg, NOW), NOW - 86400)
        os.makedirs(os.path.join(self.cfg, "counsel"))
        with open(os.path.join(self.cfg, "counsel", "state.json"), "w") as f:
            json.dump({"daily_ok_at": "2026-10-05T00:00:00.500Z"}, f)
        self.assertEqual(jc.since_epoch(self.cfg, NOW), 1791158400.5)


def _zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return buf.getvalue()


class EnsureClient(Base):
    AGORA = ("#!/usr/bin/env python3\nimport json, os, sys\n"
             "out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'called.json')\n"
             "json.dump({'argv': sys.argv[1:], 'key': os.environ.get('AGORA_SIGNING_KEY')}, open(out, 'w'))\n")

    def put(self, data, *, sha=None, size=None, ver="0.1.14"):
        d = os.path.join(self.pack, "install")
        os.makedirs(d, exist_ok=True)
        line = "%s %s %d" % (ver, sha or hashlib.sha256(data).hexdigest(), len(data) if size is None else size)
        with open(os.path.join(d, "agora-client.pin"), "w") as f:
            f.write(line + "\n")
        with open(os.path.join(d, "agora-client-%s.zip.b64" % ver), "w", newline="\n") as f:
            f.write(base64.encodebytes(data).decode("ascii"))
        return line

    def lib(self, *p):
        return os.path.join(self.cfg, "lib", *p)

    def test_no_pin_noop(self):
        self.assertEqual(jc.ensure_client(), "no-pin")
        self.assertFalse(os.path.exists(self.cfg))

    def test_install_and_same(self):
        data = _zip([("bin/agora", self.AGORA), ("agora/__init__.py", "")])
        line = self.put(data)
        self.assertTrue(all(len(x) <= 76 for x in rd(os.path.join(self.pack, "install",
                                                                    "agora-client-0.1.14.zip.b64")).split("\n")))
        self.assertEqual(jc.ensure_client(), "installed")
        self.assertEqual(rd(self.lib(".pin")).strip(), "%s %s" % (line, jc.zip_fingerprint(data)),
                         "3칸 핀 = 지문을 zip 에서 재어 넷째 칸으로")
        self.assertEqual(rd(self.lib("bin", "agora")), self.AGORA)
        self.assertTrue(os.path.isfile(self.lib("agora", "__init__.py")))
        self.assertEqual([n for n in os.listdir(self.cfg) if n.startswith("lib.tmp-")], [])
        m = os.path.getmtime(self.lib(".pin"))
        self.assertEqual(jc.ensure_client(), "same")
        self.assertEqual(os.path.getmtime(self.lib(".pin")), m)

    def test_wrong_sha_and_size_refused(self):
        data = _zip([("bin/agora", "x")])
        self.put(data, sha="0" * 64)
        self.assertEqual(jc.ensure_client(), "refused")
        self.assertFalse(os.path.exists(self.lib()))
        self.put(data, size=len(data) + 1)
        self.assertEqual(jc.ensure_client(), "refused")
        self.assertFalse(os.path.exists(self.lib()))
        log = rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()
        self.assertTrue(all(json.loads(x)["result"] == "refused" for x in log), log)

    def test_foreign_lib_untouched(self):
        os.makedirs(self.lib("bin"))
        with open(self.lib("bin", "agora"), "w") as f:
            f.write("mine")
        self.put(_zip([("bin/agora", "theirs")]))
        self.assertEqual(jc.ensure_client(), "foreign")
        self.assertEqual(rd(self.lib("bin", "agora")), "mine")
        self.assertFalse(os.path.exists(self.lib(".pin")))
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual(ev[-1]["why"], "modified or unknown client")

    def test_zip_slip_refused(self):
        for bad in ("../evil.txt", "/abs.txt", "a/../../evil.txt", "C:/win.txt", "..\\evil.txt"):
            shutil.rmtree(self.cfg, ignore_errors=True)
            self.put(_zip([("bin/agora", "x"), (bad, "boom")]))
            self.assertEqual(jc.ensure_client(), "refused", bad)
            self.assertFalse(os.path.exists(self.lib()), bad)
            self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil.txt")), bad)
            self.assertEqual([n for n in os.listdir(self.cfg) if n.startswith("lib.tmp-")], [], bad)

    def test_tick_runs_agora_with_args_and_key(self):
        self.put(_zip([("bin/agora", self.AGORA)]))
        os.makedirs(self.cfg, exist_ok=True)
        key = os.path.join(self.cfg, "id_ed25519")
        with open(key, "w") as f:
            f.write("k")
        empty = os.path.join(self.tmp, "emptybin")
        os.makedirs(empty)
        env = dict(os.environ, PATH=empty)
        env.pop("AGORA_SIGNING_KEY", None)
        env.pop("CYS_CYS_BIN", None)
        r = subprocess.run([sys.executable, SCRIPT, "tick"], capture_output=True, env=env, timeout=120)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""))
        called = json.loads(rd(self.lib("called.json")))
        self.assertEqual(called["argv"], ["counsel", "auto", "--facts",
                                          os.path.join(self.cfg, "counsel", "facts.json")])
        self.assertEqual(called["key"], key)
        self.assertTrue(os.path.isfile(os.path.join(self.cfg, "counsel", "facts.json")))
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual([(e["event"], e["result"]) for e in ev], [("ensure-client", "installed"), ("tick", "ran")])
        self.assertEqual(ev[-1]["rc"], 0)
        # 이미 정한 키는 덮지 않는다
        env["AGORA_SIGNING_KEY"] = "/elsewhere"
        subprocess.run([sys.executable, SCRIPT, "tick"], capture_output=True, env=env, timeout=120)
        self.assertEqual(json.loads(rd(self.lib("called.json")))["key"], "/elsewhere")

    def test_daily_due_skips_facts_when_off_or_done(self):
        """꺼짐 = doctor·좌석 조회 0 · 그날(06:00 KST) 일일이 끝났고 pending 없음 = 0 · pending 남음 = 다시 모은다."""
        import datetime as _dt
        now = _dt.datetime(2026, 10, 6, 0, 30, tzinfo=_dt.timezone.utc)     # = 09:30 KST → 2026-10-06
        self.assertTrue(jc._daily_due(self.cfg, now))
        os.makedirs(os.path.join(self.cfg, "counsel"), exist_ok=True)
        st = os.path.join(self.cfg, "counsel", "state.json")
        with open(st, "w") as f:
            json.dump({"daily_day": "2026-10-06"}, f)
        self.assertFalse(jc._daily_due(self.cfg, now))
        self.assertTrue(jc._daily_due(self.cfg, _dt.datetime(2026, 10, 6, 21, 1, tzinfo=_dt.timezone.utc)))  # 06:01 KST 다음 날
        self.assertFalse(jc._daily_due(self.cfg, _dt.datetime(2026, 10, 6, 20, 59, tzinfo=_dt.timezone.utc)))  # 05:59 KST = 아직 그날
        with open(st, "w") as f:
            json.dump({"daily_day": "2026-10-06", "daily_pending": {"doc": {}}}, f)
        self.assertTrue(jc._daily_due(self.cfg, now))
        with open(os.path.join(self.cfg, "config.json"), "w") as f:
            json.dump({"counsel": {"auto": False}}, f)
        self.assertFalse(jc._daily_due(self.cfg, now))

    def test_tick_without_client_logs_and_stops(self):
        empty = os.path.join(self.tmp, "emptybin")
        os.makedirs(empty)
        with envset(PATH=empty, CYS_CYS_BIN=None):   # 진짜 cys 를 부르지 않는다(데몬 자동 기동 0)
            self.assertEqual(jc.tick(), "no-client")
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual((ev[-1]["event"], ev[-1]["result"]), ("tick", "no-client"))


class Fingerprint(Base):
    """⑦ 같은 판 판정 = 설치된 트리 지문(`.pin` 글자 아님) · zip 지문 = 푼 트리 지문."""

    OLD = [("bin/agora", "#!/usr/bin/env python3\nprint('old')\n"), ("agora/__init__.py", "v=13\n"),
           ("agora/cli.py", "x = 1\n"), ("README.md", "old\n")]
    NEW = [("bin/agora", "#!/usr/bin/env python3\nprint('new')\n"), ("agora/__init__.py", "v=14\n"),
           ("agora/collector.py", "y = 2\n")]

    put = EnsureClient.put
    lib = EnsureClient.lib

    def known(self, *rows):
        d = os.path.join(self.pack, "install")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, jc.KNOWN_FILE), "w", newline="\n") as f:
            f.write("# 시험 표\n" + "".join("%s %s\n" % r for r in rows))

    def unpack_like_invite(self, data):
        """사람·옛 안내문 설치(INVITE 3) = 그 zip 을 lib 에 통째로 푼다(.pin 없음)."""
        os.makedirs(self.lib())
        jc._extract(data, self.lib())

    def test_zip_fp_equals_unpacked_tree_fp(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")            # zipfile 「Duplicate name」 — 일부러 넣은 겹이름
            data = _zip(self.OLD + [("agora/__pycache__/cli.cpython-312.pyc", b"\x00pyc"), ("x.pyc", b"p"),
                                    (".pin", "stale"), ("dir/", ""), ("agora/cli.py", "x = 2\n")])   # 같은 이름 = 뒤가 이긴다
        d = os.path.join(self.tmp, "unz")
        os.makedirs(d)
        jc._extract(data, d)
        self.assertEqual(jc.zip_fingerprint(data), jc.tree_fingerprint(d))
        rows = "".join(sorted("%s\t%s\n" % (n, hashlib.sha256(b.encode()).hexdigest())
                              for n, b in [("bin/agora", self.OLD[0][1]), ("agora/__init__.py", "v=13\n"),
                                           ("agora/cli.py", "x = 2\n"), ("README.md", "old\n")]))
        self.assertEqual(jc.tree_fingerprint(d), hashlib.sha256(rows.encode("utf-8")).hexdigest(), "지문 정의(문자 그대로)")

    def test_bundled_blob_fp_equals_unpacked_and_pin_parses(self):
        real = os.path.join(os.path.dirname(BIN), "install")
        pin = jc._read_pin(os.path.dirname(BIN))
        self.assertIsNotNone(pin, "팩 핀 판독 실패")
        data = jc._blob_bytes(os.path.join(real, "agora-client-%s.zip.b64" % pin["ver"]), pin)
        self.assertIsNotNone(data, "동봉 b64 가 핀 sha·바이트와 다르다")
        d = os.path.join(self.tmp, "real")
        os.makedirs(d)
        jc._extract(data, d)
        fp = jc.zip_fingerprint(data)
        self.assertEqual(fp, jc.tree_fingerprint(d))
        if pin["fp"] is not None:
            self.assertEqual(pin["fp"], fp, "핀 넷째 칸 ≠ 동봉 zip 지문")

    def test_known_file_rows(self):
        known = jc._read_known(os.path.dirname(BIN))
        self.assertEqual(sorted(known.values()), ["0.1.12", "0.1.13"])
        text = rd(os.path.join(os.path.dirname(BIN), "install", jc.KNOWN_FILE), encoding="utf-8")
        for sha in ("0f3f6616a95428cf0712da578221e3f709590cf3e76fbb6f809e615d458e7632",
                    "3876029b22cfe25f2a43de4937c2dea52719e547eebe448e3149eb0975b03244"):
            self.assertIn(sha, text, "zip sha 주석 누락")
        site = os.path.expanduser(os.path.join("~", "axdev", "ai-jarvis", "site", "install"))
        for fp, ver in known.items():   # 사이트 zip 이 있는 기계(제작 맥)에서만 재계산 대조
            z = os.path.join(site, "agora-client-%s.zip" % ver)
            if os.path.isfile(z):
                self.assertEqual(jc.zip_fingerprint(rd(z, "rb")), fp, ver)

    def test_pin_four_fields(self):
        data = _zip(self.NEW)
        fp = jc.zip_fingerprint(data)
        line = self.put(data)
        d = os.path.join(self.pack, "install")
        with open(os.path.join(d, "agora-client.pin"), "w") as f:
            f.write("%s %s\n" % (line, "0" * 64))
        self.assertEqual(jc.ensure_client(), "refused", "넷째 칸이 zip 지문과 다르면 거부")
        self.assertFalse(os.path.exists(self.lib()))
        with open(os.path.join(d, "agora-client.pin"), "w") as f:
            f.write("%s %s\n" % (line, fp))
        self.assertEqual(jc.ensure_client(), "installed")
        self.assertEqual(rd(self.lib(".pin")).strip(), "%s %s" % (line, fp))
        for bad in ("%s %s" % (line, "xyz"), "%s %s extra" % (line, fp), "0.1.14 abc 12"):
            with open(os.path.join(d, "agora-client.pin"), "w") as f:
                f.write(bad + "\n")
            self.assertIsNone(jc._read_pin(self.pack), bad)

    def test_same_ignores_pycache_and_pin_text(self):
        data = _zip(self.NEW)
        self.put(data)
        self.assertEqual(jc.ensure_client(), "installed")
        os.makedirs(self.lib("agora", "__pycache__"))
        with open(self.lib("agora", "__pycache__", "collector.cpython-312.pyc"), "wb") as f:
            f.write(b"\x00")
        with open(self.lib("stray.pyc"), "wb") as f:
            f.write(b"\x00")
        with open(self.lib(".pin"), "w") as f:
            f.write("whatever\n")                       # .pin 글자는 판정에 안 쓴다
        self.assertEqual(jc.ensure_client(), "same")
        self.assertEqual(rd(self.lib(".pin")), "whatever\n", "같음 = 무동작")

    def test_known_old_tree_replaced(self):
        old = _zip(self.OLD)
        self.unpack_like_invite(old)
        os.makedirs(self.lib("agora", "__pycache__"))     # 돌려 본 옛 판(.pyc 생김)도 그 판이다
        with open(self.lib("agora", "__pycache__", "cli.cpython-312.pyc"), "wb") as f:
            f.write(b"\x00")
        self.known(("0.1.12", "a" * 64), ("0.1.13", jc.zip_fingerprint(old)))
        new = _zip(self.NEW)
        self.put(new)
        self.assertEqual(jc.ensure_client(), "replaced")
        self.assertEqual(jc.tree_fingerprint(self.lib()), jc.zip_fingerprint(new))
        self.assertFalse(os.path.exists(self.lib("agora", "cli.py")), "옛 판 파일이 남았다(덮어쓰기 아님 · 통째 교체)")
        self.assertEqual(rd(self.lib(".pin")).split()[3], jc.zip_fingerprint(new))
        self.assertEqual([n for n in os.listdir(self.cfg) if n.startswith(("lib.tmp-", "lib.old-"))], [])
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual((ev[-1]["result"], ev[-1]["was"]), ("replaced", "0.1.13"))
        self.assertEqual(jc.ensure_client(), "same")

    def test_modified_known_tree_untouched(self):
        old = _zip(self.OLD)
        self.unpack_like_invite(old)
        self.known(("0.1.13", jc.zip_fingerprint(old)))
        with open(self.lib("agora", "cli.py"), "a") as f:
            f.write("# 내가 고침\n")
        snap = jc.tree_fingerprint(self.lib())
        self.put(_zip(self.NEW))
        self.assertEqual(jc.ensure_client(), "foreign")
        self.assertEqual(jc.tree_fingerprint(self.lib()), snap, "고친 트리를 건드렸다")
        self.assertFalse(os.path.exists(self.lib(".pin")))
        # 파일 하나 더한 트리도 모르는 트리다
        shutil.rmtree(self.lib())
        self.unpack_like_invite(old)
        with open(self.lib("mine.txt"), "w") as f:
            f.write("x")
        self.assertEqual(jc.ensure_client(), "foreign")
        self.assertTrue(os.path.exists(self.lib("mine.txt")))

    def test_lib_not_directory_untouched(self):
        self.put(_zip(self.NEW))
        os.makedirs(self.cfg)
        with open(self.lib(), "w") as f:
            f.write("file")
        self.assertEqual(jc.ensure_client(), "foreign")
        os.remove(self.lib())
        target = os.path.join(self.tmp, "elsewhere")
        os.makedirs(target)
        os.symlink(target, self.lib())
        self.assertEqual(jc.ensure_client(), "foreign")
        self.assertEqual(os.listdir(target), [])

    def test_install_lock_waits_then_declines(self):
        self.put(_zip(self.NEW))
        os.makedirs(self.cfg)
        holder = jc._acquire(os.path.join(self.cfg, jc.INSTALL_LOCK), 0)
        self.assertIsNotNone(holder)
        try:
            t0 = time.monotonic()
            self.assertEqual(jc.ensure_client(wait_s=0.4), "busy")
            self.assertGreaterEqual(time.monotonic() - t0, 0.35)
            self.assertFalse(os.path.exists(self.lib()))
            ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
            self.assertEqual(ev[-1]["result"], "busy")
        finally:
            def later():
                time.sleep(0.5)
                jc._unlock(holder)
                holder.close()
            th = threading.Thread(target=later)
            th.start()
        t0 = time.monotonic()
        self.assertEqual(jc.ensure_client(wait_s=10), "installed", "놓이면 기다렸다가 깐다")
        self.assertGreaterEqual(time.monotonic() - t0, 0.4)
        th.join()

    def test_rename_noreplace_never_over_existing(self):
        src = os.path.join(self.tmp, "src")
        os.makedirs(os.path.join(src, "a"))
        for dst_kind in ("empty-dir", "full-dir", "file"):
            dst = os.path.join(self.tmp, "dst-" + dst_kind)
            if dst_kind == "file":
                with open(dst, "w") as f:
                    f.write("x")
            else:
                os.makedirs(dst)
                if dst_kind == "full-dir":
                    open(os.path.join(dst, "k"), "w").close()
            with self.assertRaises(FileExistsError, msg=dst_kind):
                jc._rename_noreplace(src, dst)
            self.assertTrue(os.path.isdir(os.path.join(src, "a")), dst_kind)
        jc._rename_noreplace(src, os.path.join(self.tmp, "fresh"))
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, "fresh", "a")))

    def test_lib_appears_meanwhile_temp_discarded(self):
        self.put(_zip(self.NEW))
        real = jc._extract

        def racing(data, dest):
            real(data, dest)
            os.makedirs(self.lib())                     # 사람·다른 설치기가 그 사이 빈 lib 를 만들었다
        jc._extract = racing
        try:
            self.assertEqual(jc.ensure_client(), "raced")
        finally:
            jc._extract = real
        self.assertEqual(os.listdir(self.lib()), [], "남의 lib(빈 폴더)를 덮었다")
        self.assertEqual([n for n in os.listdir(self.cfg) if n.startswith("lib.tmp-")], [])

    def test_crash_between_aside_and_publish_recovers(self):
        """옛 판을 옆으로 치운 뒤 끊김 = lib 없음 + 찌꺼기 → 다음 판이 새로 깔고 찌꺼기를 치운다."""
        new = _zip(self.NEW)
        self.put(new)
        os.makedirs(os.path.join(self.cfg, "lib.old-dead", "agora"))
        os.makedirs(os.path.join(self.cfg, "lib.tmp-dead", "bin"))
        self.assertEqual(jc.ensure_client(), "installed")
        self.assertEqual(jc.tree_fingerprint(self.lib()), jc.zip_fingerprint(new))
        self.assertEqual(sorted(n for n in os.listdir(self.cfg) if n.startswith("lib")), ["lib", "lib.install.lock"])


class TickCap(Base):
    """⑨ 한 판 상한 540초 — agora 몫 = 540 − 경과(바닥 30) · 넘으면 프로세스 그룹째 끝내고 로그."""

    put = EnsureClient.put
    lib = EnsureClient.lib

    def test_timeout_budget(self):
        self.assertEqual(jc.TICK_CAP_S, 540)
        self.assertEqual([jc.agora_timeout(e) for e in (0, 0.4, 100, 509, 510, 511, 900)],
                         [540, 539, 440, 31, 30, 30, 30])

    @unittest.skipIf(os.name == "nt", "POSIX 프로세스 그룹(윈은 taskkill /T 실기)")
    def test_timeout_kills_group(self):
        hang = ("#!/usr/bin/env python3\nimport os, subprocess, sys, time\n"
                "root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
                "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'])\n"
                "open(os.path.join(root, 'pids'), 'w').write('%d %d' % (os.getpid(), g.pid))\n"
                "time.sleep(300)\n")
        self.put(_zip([("bin/agora", hang)]))
        empty = os.path.join(self.tmp, "emptybin")
        os.makedirs(empty)
        old = (jc.TICK_CAP_S, jc.AGORA_MIN_TIMEOUT_S)
        jc.TICK_CAP_S, jc.AGORA_MIN_TIMEOUT_S = 2, 2
        try:
            with envset(PATH=empty, CYS_CYS_BIN=None):
                t0 = time.monotonic()
                self.assertEqual(jc.tick(), "timeout")
                self.assertLess(time.monotonic() - t0, 30)
        finally:
            jc.TICK_CAP_S, jc.AGORA_MIN_TIMEOUT_S = old
        child, grand = map(int, rd(self.lib("pids")).split())

        def alive(pid):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return False
            return True
        deadline = time.monotonic() + 10
        while alive(grand) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertFalse(alive(grand), "손자(같은 그룹)가 살아 있다 — 그룹째 끝내지 않았다")
        self.assertFalse(alive(child))
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual((ev[-1]["event"], ev[-1]["result"], ev[-1]["killed"], ev[-1]["timeout_s"]),
                         ("tick", "timeout", "killpg", 2))


RACE_MOVER = r'''
import os, sys, time
sys.dont_write_bytecode = True
client, cfg, stop = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, client)
from agora import collector
assert os.path.dirname(os.path.dirname(os.path.abspath(collector.__file__))) == os.path.abspath(client), collector.__file__
path = os.path.join(cfg, "counsel", "signals.jsonl")
rounds = moved = 0
while True:
    done = os.path.exists(stop)
    lines = collector._signal_lines(path)      # 잠금 밖에서 읽고(실제 판처럼) → 잠금 안에서 옮긴다
    if lines:
        moved += collector.move_sent(cfg, lines)
    rounds += 1
    if done:
        break
    time.sleep(0.002)
print(rounds, moved)
'''


def bundled_client(dest):
    """이 팩에 실린 아고라 클라이언트(`install/agora-client-*.zip.b64`)를 dest 에 푼다 → 푼 폴더."""
    pin = jc._read_pin(os.path.dirname(BIN))
    data = jc._blob_bytes(os.path.join(os.path.dirname(BIN), "install", "agora-client-%s.zip.b64" % pin["ver"]), pin)
    jc._extract(data, dest)
    return dest


class CrossLockRace(Base):
    """⑩ 팩 쓰기(`javis_counsel.py signal` 동시 다발) ↔ 동봉 아고라 `collector.move_sent` 반복 — 같은 옆 잠금
    (`signals.lock` 0번 바이트)으로 막히는가. 모든 줄이 signals.jsonl ∪ signals-sent.jsonl 에 정확히 한 번 · LF."""

    N = 60
    WAVE = 20

    def test_writers_vs_mover(self):
        client = bundled_client(os.path.join(self.tmp, "client"))
        mover_py = os.path.join(self.tmp, "mover.py")
        with open(mover_py, "w") as f:
            f.write(RACE_MOVER)
        stop = os.path.join(self.tmp, "stop")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        os.makedirs(os.path.join(self.cfg, "counsel"))
        mover = subprocess.Popen([sys.executable, mover_py, client, self.cfg, stop], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env)
        try:
            ops = ["race.w%03d" % i for i in range(self.N)]
            for k in range(0, self.N, self.WAVE):
                procs = [subprocess.Popen([sys.executable, SCRIPT, "signal", "--source", "worker", "--op", op,
                                           "--error-code", "race.e1"], env=env)
                         for op in ops[k:k + self.WAVE]]
                for p in procs:
                    self.assertEqual(p.wait(timeout=60), 0)
        finally:
            open(stop, "w").close()
            out, err = mover.communicate(timeout=60)
        self.assertEqual(mover.returncode, 0, err.decode("utf-8", "replace")[-800:])
        rounds, moved = map(int, out.split())
        c = os.path.join(self.cfg, "counsel")
        raw_left = rd(os.path.join(c, "signals.jsonl"), "rb")
        raw_sent = rd(os.path.join(c, "signals-sent.jsonl"), "rb")
        for raw in (raw_left, raw_sent):
            self.assertNotIn(b"\r", raw)
            self.assertTrue(raw == b"" or raw.endswith(b"\n"))
        lines = [x for x in (raw_left + raw_sent).decode("utf-8").split("\n") if x]
        got = sorted(json.loads(x)["op"] for x in lines)
        self.assertEqual(got, sorted(ops), "줄 유실 또는 중복")
        self.assertEqual(raw_left, b"", "마지막 판이 다 옮겼어야 한다")
        self.assertEqual(moved, self.N)
        self.assertGreater(rounds, 1)
        self.assertEqual([n for n in os.listdir(c) if ".tmp-" in n], [])


class Preflight(Base):
    def test_signal_pairs_dedup(self):
        import javis_preflight as pf
        results = [{"id": "C03.pin.x", "status": pf.FAIL}, {"id": "C03.pin.y", "status": pf.FAIL},
                   {"id": "c12.daemon", "status": pf.WARN}, {"id": "C28.self", "status": pf.PASS},
                   {"id": "X1", "status": pf.FAIL}, {"id": "C03.z", "status": pf.WARN},
                   {"id": "C07", "status": pf.SKIP}, {"id": None, "status": pf.FAIL}]
        self.assertEqual(pf._counsel_signal_pairs(results),
                         [("preflight.c03", "doctor.c03.fail"), ("preflight.c12", "doctor.c12.warn"),
                          ("preflight.c03", "doctor.c03.warn")])
        pf._counsel_emit(results)
        rows = [json.loads(x) for x in self.sig_lines()]
        self.assertEqual([(r["source"], r["op"], r["error_code"]) for r in rows],
                         [("pack", "preflight.c03", "doctor.c03.fail"), ("pack", "preflight.c12", "doctor.c12.warn"),
                          ("pack", "preflight.c03", "doctor.c03.warn")])
        self.config('{"counsel": {"auto": false}}')
        pf._counsel_emit(results)
        self.assertEqual(len(self.sig_lines()), 3)

    def test_main_wiring_after_counts(self):
        src = rd(os.path.join(BIN, "javis_preflight.py"), encoding="utf-8")
        main = src[src.index("\ndef main():"):]
        i = main.index('warns = sum(1 for r in results if r["status"] == WARN)')
        self.assertLess(i, main.index("_counsel_emit(results)"))
        self.assertLess(main.index("_counsel_emit(results)"), main.index("if args.json:"))


class DeptTrap(Base):
    """cys-dept 판독 실패(exit 12) — 종료코드 그대로 + 신호 1줄 · 사용법 오류(exit 2)는 신호 0."""

    def run_dept(self, *args, **extra):
        home = os.path.join(self.tmp, "home")
        os.makedirs(home, exist_ok=True)
        env = dict(os.environ, HOME=home, CYS_PACK_DIR=self.pack, AGORA_CONFIG_DIR=self.cfg,
                   CYS_STATE_DIR=os.path.join(self.tmp, "st"), **extra)
        for k in ("CYS_SOCKET", "CYS_SURFACE_ID", "CYS_ROLE", "CYS_SEAT_TOKEN"):
            env.pop(k, None)
        return subprocess.run(["bash", os.path.join(BIN, "cys-dept")] + list(args), capture_output=True,
                              env=env, timeout=60)

    def test_exit12_recorded_and_preserved(self):
        bad = os.path.join(self.tmp, "depts.json")
        with open(bad, "w") as f:
            f.write("{not json")
        r = self.run_dept("list", CYS_DEPTS_JSON=bad)
        self.assertEqual(r.returncode, 12, r.stderr.decode("utf-8", "replace")[-400:])
        rows = [json.loads(x) for x in self.sig_lines()]
        self.assertEqual([(x["source"], x["op"], x["error_code"]) for x in rows], [("pack", "dept.list", "dept.exit12")])

    def test_success_and_usage_not_recorded(self):
        ok = os.path.join(self.tmp, "ok.json")
        with open(ok, "w") as f:
            f.write('{"depts": {}}')
        r = self.run_dept("list", CYS_DEPTS_JSON=ok)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-400:])
        self.assertEqual(self.sig_lines(), [])


if __name__ == "__main__":
    unittest.main()
