#!/usr/bin/env python3
"""test_javis_counsel — ★T3(agora-t3-pack-collector): 상담소 자동 전달의 팩 쪽(`bin/javis_counsel.py`).

지키는 것(agora 클라이언트 `collector.py`·`mail.py` 와 글자 그대로 같은 계약):
  ① 신호 줄 정규식(ts·source·op·error_code·version·os) 수용/거부 벡터 · 형식 밖 줄은 안 쓴다
  ② CYS_ROLE → source 표 · 끄기 규칙 표(config.json 7행) · 2MB 넘으면 버림 · CRLF 0 · 한 줄 = 정렬 키 압축 JSON
  ③ 잠금 — 남이 쥐고 있으면 상한(기본 2초) 뒤 버리고 exit 0(훅을 붙잡지 않는다)
  ④ facts — 가짜 cys(PATH 대역)·가짜 상태 파일로 칸별 산출 · 못 잰 칸은 뺀다(null 0)
  ⑤ ensure-client — 올바른 sha = 설치+.pin · 틀린 sha = 거부 · zip-slip = 거부 · 판정 = 트리 지문(같음 = 무동작 ·
     알려진 옛 판 = 교체 · 고친/모르는 트리 = 불가침) · 설치 잠금(대기/포기) · 남의 lib 위로 rename 0
  ⑥ tick — 가짜 `lib/bin/agora` 가 받은 인자(`--facts-nonce` = 그 판 nonce · 파일 nonce 와 결박)·AGORA_SIGNING_KEY ·
     한 판 상한 540초(agora 몫 ≤500 + 끝내기 몫 40 · 시작 → 반환 벽시계 · 시간 초과 = 프로세스 그룹째 끝냄)
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
POSIX_FAKE_CYS = "가짜 cys = #!/bin/sh 스크립트(윈 shutil.which 는 PATHEXT 만 찾아 실행 불가 · POSIX 전용 검체)"


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
    @unittest.skipIf(os.name == "nt", POSIX_FAKE_CYS)
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
        self.assertEqual(facts["since"], jc.ms_iso(since), "since = state.json daily_ok_at 그대로")
        self.assertTrue(jc.TS_RE.match(facts["cutoff"]) and facts["since"] < facts["cutoff"], facts)
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

    @unittest.skipIf(os.name == "nt", POSIX_FAKE_CYS)
    def test_list_failure_omits_seats(self):
        fb = self.make_cys("surface:1\trole=master\texited=false\n", "not json", list_rc=1)
        env = dict(os.environ, PATH=fb + os.pathsep + os.environ.get("PATH", ""))
        env.pop("CYS_CYS_BIN", None)
        with envset(PATH=env["PATH"], CYS_CYS_BIN=None):
            self.assertIsNone(jc.probe_seats())
            self.assertIsNone(jc.probe_doctor())

    @unittest.skipIf(os.name == "nt", POSIX_FAKE_CYS)
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

    def test_error_window_boundaries(self):
        """★리뷰 3R ③ — 창 = (since, cutoff]: since 정각 줄 = 뺌 · cutoff 정각 줄 = 셈 · cutoff 뒤 줄 = 뺌(다음 창 몫)."""
        S, C = 1791100000, 1791100000 + 7200
        st, req = os.path.join(self.tmp, "state"), os.path.join(self.tmp, "req")
        os.makedirs(st)
        os.makedirs(req)
        os.makedirs(os.path.join(self.cfg, "counsel"))
        with open(os.path.join(self.cfg, "counsel", "state.json"), "w") as f:
            json.dump({"daily_ok_at": jc.ms_iso(S)}, f)
        loc = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))
        utc = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
        with open(os.path.join(req, "tick-errors.log"), "w", encoding="utf-8") as f:
            f.write("".join("%s t%d\n" % (loc(t), i) for i, t in enumerate((S - 1, S, S + 1, C - 1, C, C + 1, C + 999))))
        with open(os.path.join(st, "hook-errors.log.1"), "w", encoding="utf-8") as f:
            f.write("%s h rc=1\n%s h rc=1\n" % (utc(S), utc(S + 1)))
        with open(os.path.join(st, "hook-errors.log"), "w", encoding="utf-8") as f:
            f.write("%s h rc=1\n%s h rc=1\n" % (utc(C), utc(C + 1)))
        empty = os.path.join(self.tmp, "emptybin")
        os.makedirs(empty)
        with envset(PATH=empty, CYS_CYS_BIN=None, CYS_STATE_DIR=st, CYS_DEPT_REQUESTS=req):
            facts = jc.collect_facts(self.cfg, now=C + 0.0004)        # cutoff = 밀리초로 자른 C
            self.assertEqual((facts["since"], facts["cutoff"]), (jc.ms_iso(S), jc.ms_iso(C)))
            self.assertEqual(facts["errors"], {"tick_errors": 3, "hook_rc_nonzero": 2},
                             "S+1·C−1·C 만 · S 정각·C 뒤 = 0")
            self.assertEqual(jc.probe_errors(S, C - 1), {"tick_errors": 2, "hook_rc_nonzero": 1})
            os.remove(os.path.join(self.cfg, "counsel", "state.json"))   # daily_ok_at 없음 = cutoff − 24h
            facts = jc.collect_facts(self.cfg, now=C)
            self.assertEqual(facts["since"], jc.ms_iso(C - 86400))
            self.assertEqual(facts["errors"], {"tick_errors": 5, "hook_rc_nonzero": 3})

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
        self.assertEqual(called["argv"][:5], ["counsel", "auto", "--facts",
                                              os.path.join(self.cfg, "counsel", "facts.json"), "--facts-nonce"])
        self.assertEqual(len(called["argv"]), 6)
        nonce1 = called["argv"][5]
        self.assertRegex(nonce1, r"^[0-9a-f]{32}\Z")
        self.assertEqual(called["key"], key)
        self.assertTrue(os.path.isfile(os.path.join(self.cfg, "counsel", "facts.json")))
        # ★리뷰 3R ② 4판(b) — 성공 판: 파일 nonce == argv nonce
        self.assertEqual(json.loads(rd(os.path.join(self.cfg, "counsel", "facts.json")))["nonce"], nonce1)
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual([(e["event"], e["result"]) for e in ev], [("ensure-client", "installed"), ("tick", "ran")])
        self.assertEqual(ev[-1]["rc"], 0)
        # 이미 정한 키는 덮지 않는다
        env["AGORA_SIGNING_KEY"] = "/elsewhere"
        subprocess.run([sys.executable, SCRIPT, "tick"], capture_output=True, env=env, timeout=120)
        called = json.loads(rd(self.lib("called.json")))
        self.assertEqual(called["key"], "/elsewhere")
        self.assertNotEqual(called["argv"][5], nonce1, "nonce 가 판마다 새로 나지 않았다")

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

    def test_tick_facts_failure_still_runs_agora(self):
        """★리뷰 3R ③ — facts 쓰기 실패 = 로그 + agora 는 그대로 돈다 · 팩은 daily 완료 표식(state.json)을 쓰지 않는다."""
        self.put(_zip([("bin/agora", self.AGORA)]))
        empty = os.path.join(self.tmp, "emptybin")
        os.makedirs(empty)
        real = jc.collect_facts

        def boom(cfg, now=None, nonce=None):
            raise RuntimeError("disk")
        jc.collect_facts = boom
        try:
            with envset(PATH=empty, CYS_CYS_BIN=None, AGORA_SIGNING_KEY=None):
                self.assertEqual(jc.tick(), "ran")
        finally:
            jc.collect_facts = real
        self.assertTrue(os.path.isfile(self.lib("called.json")), "facts 실패에 agora 를 건너뛰었다")
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "counsel", "facts.json")))
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "counsel", "state.json")), "팩이 state 를 썼다")
        ev = [(e["event"], e["result"]) for e in map(json.loads, rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines())]
        self.assertIn(("facts", "error"), ev)
        self.assertIn(("tick", "facts-failed"), ev)
        self.assertEqual(ev[-1], ("tick", "ran"))

    def _tick_with_failing_facts(self):
        real = jc.collect_facts

        def boom(cfg, now=None, nonce=None):
            raise RuntimeError("disk")
        jc.collect_facts = boom
        try:
            with envset(PATH=os.path.join(self.tmp, "emptybin"), CYS_CYS_BIN=None, AGORA_SIGNING_KEY=None):
                return jc.tick()
        finally:
            jc.collect_facts = real

    def test_tick_facts_failure_keeps_old_fresh_facts_unbound(self):
        """★리뷰 3R ② 4판(a) — 디스크에 지난 판의 **신선한** facts.json(cutoff = 지금 · 옛 nonce)이 있는데 이번 판 쓰기가 실패해도
        agora 에 넘기는 nonce 는 그 파일의 nonce 와 다르다(아고라 = 사실 없음 → 일일 no_fresh_facts) · 옛 파일은 그대로."""
        self.put(_zip([("bin/agora", self.AGORA)]))
        os.makedirs(os.path.join(self.tmp, "emptybin"))
        os.makedirs(os.path.join(self.cfg, "counsel"))
        old_nonce = "a" * 32
        facts = os.path.join(self.cfg, "counsel", "facts.json")
        now = jc.decide_cutoff()
        doc = {"cutoff": jc.ms_iso(now), "since": jc.ms_iso(now - 86400), "nonce": old_nonce}
        with open(facts, "w") as f:
            json.dump(doc, f)
        self.assertEqual(self._tick_with_failing_facts(), "ran")
        argv = json.loads(rd(self.lib("called.json")))["argv"]
        self.assertEqual(argv[2:5], ["--facts", facts, "--facts-nonce"])
        self.assertRegex(argv[5], r"^[0-9a-f]{32}\Z")
        self.assertEqual(json.loads(rd(facts)), doc, "옛 facts.json 이 바뀌었다(실패 판이 썼다)")
        self.assertEqual(json.loads(rd(facts))["nonce"], old_nonce)
        self.assertNotEqual(argv[5], old_nonce, "실패 판이 옛 facts 의 nonce 를 넘겼다 — 아고라가 옛 사실을 받는다")
        ev = [(e["event"], e["result"]) for e in map(json.loads, rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines())]
        self.assertIn(("tick", "facts-failed"), ev)

    def test_tick_not_due_still_passes_nonce(self):
        """★리뷰 3R ② 4판(c) — 일일이 필요 없는 판(꺼짐 · 그날 끝남)도 `--facts-nonce` 를 넘긴다 · facts 는 안 쓴다."""
        self.put(_zip([("bin/agora", self.AGORA)]))
        os.makedirs(os.path.join(self.tmp, "emptybin"))
        os.makedirs(os.path.join(self.cfg, "counsel"))
        import datetime as _dt
        today = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=3)).date().isoformat()   # = jc._daily_due 의 KST 06:00 선
        cases = (("done", "state.json", {"daily_day": today}), ("off", "config.json", {"counsel": {"auto": False}}))
        for name, fname, doc in cases:
            with self.subTest(name):
                where = os.path.join(self.cfg, "counsel" if fname == "state.json" else "", fname)
                with open(where, "w") as f:
                    json.dump(doc, f)
                self.assertFalse(jc._daily_due(self.cfg), name)
                with envset(PATH=os.path.join(self.tmp, "emptybin"), CYS_CYS_BIN=None, AGORA_SIGNING_KEY=None):
                    self.assertEqual(jc.tick(), "ran")
                argv = json.loads(rd(self.lib("called.json")))["argv"]
                self.assertEqual(argv[4], "--facts-nonce", name)
                self.assertRegex(argv[5], r"^[0-9a-f]{32}\Z")
                self.assertFalse(os.path.exists(os.path.join(self.cfg, "counsel", "facts.json")), name)
                os.remove(where)

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
        rows = ["f\t%s\t%s\n" % (n, hashlib.sha256(b.encode()).hexdigest())
                for n, b in [("bin/agora", self.OLD[0][1]), ("agora/__init__.py", "v=13\n"),
                             ("agora/cli.py", "x = 2\n"), ("README.md", "old\n")]]
        rows += ["d\tagora\t-\n", "d\tbin\t-\n", "d\tdir\t-\n"]      # 파일 경로에서 나온 폴더 + 명시 빈 폴더
        self.assertEqual(jc.tree_fingerprint(d), hashlib.sha256("".join(sorted(rows)).encode("utf-8")).hexdigest(),
                         "지문 산식 v2(문자 그대로)")
        self.assertEqual(jc.FP_FORMULA, "v2")
        self.assertEqual(jc.tree_scan(d)[1], ["dir/"], "빈 폴더 = 이상 목록")

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
        self.assertEqual(jc.tree_scan(d), (fp, []), "동봉 zip 을 푼 트리 = 같은 지문 · 링크·빈 폴더 0")
        # ★핀 넷째 칸 값 자체는 대조하지 않는다 — 0.1.14 재빌드 때 부모가 다시 쓴다(아래 RealBundlePin 이 실행 때 잰 값으로 본다).

    def test_known_file_rows(self):
        known = jc._read_known(os.path.dirname(BIN))
        self.assertEqual(sorted(known.values()), ["0.1.12", "0.1.13", "0.1.14"])
        # ★known 의 동봉 판 줄 = 핀 넷째 칸(다음 판 동봉 때 이 판 PC 가 「모르는 트리」로 남지 않게 · 3판 ⑨)
        pin = rd(os.path.join(os.path.dirname(BIN), "install", "agora-client.pin"), encoding="utf-8").split()
        self.assertEqual({v: f for f, v in known.items()}.get(pin[0]), pin[3], "known 의 동봉 판 지문 ≠ 핀 넷째 칸")
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
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual((ev[-1]["why"], ev[-1]["formula"]), ("pin_fingerprint_mismatch", "v2"))
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

    def _odd_tree_untouched(self, make_odd, why="symlink, special file or empty dir"):
        """알려진 옛 판 트리에 이상 항목 하나 = 교체 0 · 같음 0 · 불가침 + 로그."""
        old = _zip(self.OLD)
        self.unpack_like_invite(old)
        self.known(("0.1.13", jc.zip_fingerprint(old)))
        make_odd()
        snap = sorted(os.listdir(self.lib()))
        self.put(_zip(self.NEW))
        self.assertEqual(jc.ensure_client(), "foreign")
        self.assertEqual(sorted(os.listdir(self.lib())), snap)
        self.assertFalse(os.path.exists(self.lib(".pin")))
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual((ev[-1]["result"], ev[-1]["why"]), ("foreign", why))
        return ev[-1]

    def test_empty_dir_in_tree_is_foreign(self):
        """★v1 은 빈 폴더가 지문에 안 보여 알려진 옛 판으로 보고 교체했다 — v2 = 지문도 다르고 이상 항목으로 불가침."""
        ev = self._odd_tree_untouched(lambda: os.makedirs(self.lib("agora", "empty")))
        self.assertEqual(ev["odd"], ["agora/empty/"])
        self.assertTrue(os.path.isdir(self.lib("agora", "empty")))
        shutil.rmtree(self.lib("agora", "empty"))
        self.assertEqual(jc.ensure_client(), "replaced", "빈 폴더를 치우면 다시 알려진 옛 판")

    def test_empty_pycache_is_not_odd(self):
        old = _zip(self.OLD)
        self.unpack_like_invite(old)
        os.makedirs(self.lib("agora", "__pycache__"))
        self.assertEqual(jc.tree_scan(self.lib()), (jc.zip_fingerprint(old), []))

    @unittest.skipIf(os.name == "nt", "심볼릭 링크 만들기 = 윈 개발자 모드·관리자 권한(POSIX 전용 검체)")
    def test_symlink_in_tree_is_foreign(self):
        ev = self._odd_tree_untouched(lambda: os.symlink("cli.py", self.lib("agora", "link.py")))
        self.assertEqual(ev["odd"], ["agora/link.py"])
        self.assertTrue(os.path.islink(self.lib("agora", "link.py")))
        # 폴더 링크도(따라가지 않는다)
        os.remove(self.lib("agora", "link.py"))
        target = os.path.join(self.tmp, "outside")
        os.makedirs(target)
        os.symlink(target, self.lib("agora", "dirlink"))
        self.assertEqual(jc.ensure_client(), "foreign")
        self.assertEqual(jc.tree_scan(self.lib())[1], ["agora/dirlink"])
        # 종류 칸 = l(문자 그대로 · o 로 뭉개지 않는다)
        d = os.path.join(self.tmp, "kinds")
        os.makedirs(d)
        with open(os.path.join(d, "a"), "wb") as f:
            f.write(b"A")
        os.symlink("a", os.path.join(d, "b"))
        rows = "f\ta\t%s\nl\tb\t-\n" % hashlib.sha256(b"A").hexdigest()
        self.assertEqual(jc.tree_scan(d), (hashlib.sha256(rows.encode()).hexdigest(), ["b"]))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO = POSIX 전용")
    def test_fifo_in_tree_is_foreign(self):
        ev = self._odd_tree_untouched(lambda: os.mkfifo(self.lib("bin", "pipe")))
        self.assertEqual(ev["odd"], ["bin/pipe"])

    def test_bundled_zip_with_empty_dir_refused(self):
        self.put(_zip(self.NEW + [("empty/", "")]))
        self.assertEqual(jc.ensure_client(), "refused")
        self.assertFalse(os.path.exists(self.lib()))
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual(ev[-1]["why"], "bundled zip makes irregular tree")

    def test_real_bundle_pin_fingerprint_checked_at_runtime(self):
        """실 동봉 zip — 넷째 칸 = 실행 때 잰 v2 지문이면 설치 · v1 산식 값(옛 핀 꼴)이면 pin_fingerprint_mismatch 로 거부."""
        real = os.path.join(os.path.dirname(BIN), "install")
        pin = jc._read_pin(os.path.dirname(BIN))
        blob = "agora-client-%s.zip.b64" % pin["ver"]
        data = jc._blob_bytes(os.path.join(real, blob), pin)
        os.makedirs(os.path.join(self.pack, "install"))
        shutil.copy(os.path.join(real, blob), os.path.join(self.pack, "install", blob))
        v1_rows = {}
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if not info.is_dir():
                    v1_rows[info.filename] = hashlib.sha256(zf.read(info)).hexdigest()
        v1 = hashlib.sha256("".join(sorted("%s\t%s\n" % kv for kv in v1_rows.items())).encode()).hexdigest()
        head = "%s %s %d" % (pin["ver"], pin["sha"], pin["size"])
        pin_path = os.path.join(self.pack, "install", "agora-client.pin")
        with open(pin_path, "w", newline="\n") as f:
            f.write("%s %s\n" % (head, v1))
        self.assertNotEqual(v1, jc.zip_fingerprint(data))
        self.assertEqual(jc.ensure_client(), "refused")
        self.assertFalse(os.path.exists(self.lib()))
        with open(pin_path, "w", newline="\n") as f:
            f.write("%s %s\n" % (head, jc.zip_fingerprint(data)))
        self.assertEqual(jc.ensure_client(), "installed")
        self.assertEqual(jc.ensure_client(), "same")

    def test_lib_not_directory_untouched(self):
        self.put(_zip(self.NEW))
        os.makedirs(self.cfg)
        with open(self.lib(), "w") as f:
            f.write("file")
        self.assertEqual(jc.ensure_client(), "foreign")
        os.remove(self.lib())
        if os.name == "nt":
            return                                      # 심볼릭 링크 = 윈 권한 필요(아래 반쪽은 POSIX 만)
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
        """옛 판을 옆으로 치운 뒤 끊김 = lib 없음 + 찌꺼기 → 다음 판이 새로 깐다 · lib.tmp-* 는 치우고 ★lib.old-* 는 남긴다(3R ④)."""
        new = _zip(self.NEW)
        self.put(new)
        os.makedirs(os.path.join(self.cfg, "lib.old-dead", "agora"))
        os.makedirs(os.path.join(self.cfg, "lib.tmp-dead", "bin"))
        self.assertEqual(jc.ensure_client(), "installed")
        self.assertEqual(jc.tree_fingerprint(self.lib()), jc.zip_fingerprint(new))
        self.assertEqual(sorted(n for n in os.listdir(self.cfg) if n.startswith("lib")),
                         ["lib", "lib.install.lock", "lib.old-dead"])
        self.assertTrue(os.path.isdir(os.path.join(self.cfg, "lib.old-dead", "agora")), "옆으로 치운 옛 판을 지웠다")

    def test_replace_race_keeps_moved_aside_old(self):
        """★3R ④ — 옛 판을 옆으로 옮긴 직후 남이 lib 를 만들었다 = raced · 옮긴 옛 판(lib.old-*)은 지우지 않고 로그."""
        old = _zip(self.OLD)
        self.unpack_like_invite(old)
        self.known(("0.1.13", jc.zip_fingerprint(old)))
        self.put(_zip(self.NEW))
        real = jc._rename_noreplace
        calls = []

        def racing(src, dst):
            real(src, dst)
            calls.append(os.path.basename(dst))
            if len(calls) == 1:
                os.makedirs(self.lib())                 # lib → lib.old-* 직후 남이 빈 lib 를 만든다
        jc._rename_noreplace = racing
        try:
            self.assertEqual(jc.ensure_client(), "raced")
        finally:
            jc._rename_noreplace = real
        olds = [n for n in os.listdir(self.cfg) if n.startswith("lib.old-")]
        self.assertEqual(len(olds), 1, "옮긴 옛 판을 지웠다")
        self.assertEqual(jc.tree_fingerprint(os.path.join(self.cfg, olds[0])), jc.zip_fingerprint(old))
        self.assertEqual(os.listdir(self.lib()), [], "남의 lib 를 건드렸다")
        self.assertEqual([n for n in os.listdir(self.cfg) if n.startswith("lib.tmp-")], [])
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual((ev[-1]["result"], ev[-1]["kept_old"]), ("raced", olds[0]))
        self.assertEqual(jc.ensure_client(), "foreign")      # 다음 판도 옛 판을 치우지 않는다
        self.assertEqual([n for n in os.listdir(self.cfg) if n.startswith("lib.old-")], olds)

    @unittest.skipIf(os.name == "nt", "윈 = os.rename 이 원래 「있으면 실패」(수단 판정 대상 아님)")
    def test_no_atomic_noreplace_fails_closed(self):
        """★3R ④ — 원자 「있으면 실패」 수단 없음 = 풀지도 옮기지도 않는다 · 옛 lexists 대체 길 0."""
        real_fn, real_extract = jc._noreplace_fn, jc._extract
        extracted = []
        jc._noreplace_fn = lambda: None
        jc._extract = lambda data, dest: (extracted.append(dest), real_extract(data, dest))
        try:
            with self.assertRaises(jc.NoAtomicNoReplace):
                jc._rename_noreplace(os.path.join(self.tmp, "nope-src"), os.path.join(self.tmp, "nope-dst"))
            self.put(_zip(self.NEW))
            self.assertEqual(jc.ensure_client(), "refused")
            self.assertFalse(os.path.exists(self.lib()))
            old = _zip(self.OLD)
            self.unpack_like_invite(old)
            self.known(("0.1.13", jc.zip_fingerprint(old)))
            self.assertEqual(jc.ensure_client(), "refused")
            self.assertEqual(jc.tree_fingerprint(self.lib()), jc.zip_fingerprint(old), "옛 판을 건드렸다")
        finally:
            jc._noreplace_fn, jc._extract = real_fn, real_extract
        self.assertEqual([d for d in extracted if "lib.tmp-" in d], [], "수단이 없는데 풀었다")
        self.assertEqual([n for n in os.listdir(self.cfg) if n.startswith(("lib.tmp-", "lib.old-"))], [])
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual([e["why"] for e in ev[-2:]], ["no_atomic_noreplace"] * 2)

    @unittest.skipIf(os.name == "nt", "POSIX libc 경로")
    def test_noreplace_unsupported_fs_fails_closed(self):
        """수단은 있는데 그 파일 시스템이 거절(ENOSYS·EINVAL·ENOTSUP) = NoAtomicNoReplace · lib 무접촉."""
        import ctypes
        import errno as _errno
        real_fn = jc._noreplace_fn
        for err in (_errno.ENOSYS, _errno.EINVAL, getattr(_errno, "ENOTSUP", _errno.EINVAL)):
            def fake(a, b, err=err):
                ctypes.set_errno(err)
                return -1
            jc._noreplace_fn = lambda: fake
            try:
                shutil.rmtree(self.cfg, ignore_errors=True)
                shutil.rmtree(os.path.join(self.pack, "install"), ignore_errors=True)
                old = _zip(self.OLD)
                self.unpack_like_invite(old)
                self.known(("0.1.13", jc.zip_fingerprint(old)))
                self.put(_zip(self.NEW))
                self.assertEqual(jc.ensure_client(), "refused", err)
            finally:
                jc._noreplace_fn = real_fn
            self.assertEqual(jc.tree_fingerprint(self.lib()), jc.zip_fingerprint(old), err)
            self.assertEqual([n for n in os.listdir(self.cfg) if n.startswith(("lib.tmp-", "lib.old-"))], [], err)
            ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
            self.assertEqual(ev[-1]["why"], "no_atomic_noreplace", err)


class TickCap(Base):
    """⑨ 한 판 상한 540초 — agora 몫 = 540 − 끝내기 몫 40(taskkill 30 + 회수 10) − 경과(Popen 직전에 잰다) · 남은 몫 < 30 =
    안 띄움(no_time) · 넘으면 프로세스 그룹째 끝내고 로그. ★리뷰 3R ④ 4판 = 시작 → 반환 벽시계 ≤ 540(끝내기 포함)."""

    put = EnsureClient.put
    lib = EnsureClient.lib

    def _patch(self, **kv):
        old = {k: getattr(jc, k) for k in kv}
        for k, v in kv.items():
            setattr(jc, k, v)
        self.addCleanup(lambda: [setattr(jc, k, v) for k, v in old.items()])

    def test_timeout_budget(self):
        self.assertEqual((jc.TICK_CAP_S, jc.TASKKILL_TIMEOUT_S, jc.REAP_TIMEOUT_S, jc.KILL_BUDGET_S), (540, 30, 10, 40))
        table = {0: 500, 0.4: 499, 100: 400, 469: 31, 470: 30, 470.5: None, 471: None, 500: None, 539: None,
                 540: None, 590: None, 900: None}
        self.assertEqual({e: jc.agora_timeout(e) for e in table}, table)
        for e in [x / 100 for x in range(0, 60001, 7)]:
            t = jc.agora_timeout(e)
            if t is None:
                self.assertGreater(e, jc.TICK_CAP_S - jc.KILL_BUDGET_S - jc.AGORA_MIN_TIMEOUT_S, e)   # 몫 < 30 일 때만 None
                continue
            self.assertLessEqual(e + t + jc.KILL_BUDGET_S, jc.TICK_CAP_S, e)   # ★경과 + 몫 + 끝내기 ≤ 540
            self.assertLessEqual(e + t, 500, e)
            self.assertGreaterEqual(t, jc.AGORA_MIN_TIMEOUT_S, e)

    def test_wall_clock_scaled_cap_includes_spawn_and_kill(self):
        """★리뷰 3R ④ 4판 — 상수를 줄인 축척판(상한 8 · 끝내기 몫 4 → agora 몫 = int(4 − 경과)): 띄우는 데 2초 걸리고(Popen
        대역이 늦춤) 끝나지 않는 agora 여도 tick 시작 → 반환 ≤ 상한(계약 · 끝내기 포함).
        ★publish-docs-118 ⑥(10-07 windows-health 37507309556 @33ca7b68 간헐 적색 4.66s): 옛 판별 단언 = 「전체 벽시계 < 몫 상한
        + 1초」 는 경과(ensure_client 등)·끝내기(taskkill) 실소요가 러너 부하로 늘면 같이 늘어 정답 구현도 붉혔다 → 판별은
        **띄우기 시작 → 끝내기 시작** 구간만 잰다(경과·끝내기 실소요가 빠진다). 정답 = 그 구간 ≈ max(띄우기 2, 몫) ·
        띄우는 시간을 몫 밖에서 셌다면(옛 꼴 = Popen 뒤 communicate(timeout=몫)) ≈ 띄우기 2 + 몫 → min(2, 몫) ≥ 2 라 1초 여유로 적색."""
        hang = "#!/usr/bin/env python3\nimport time\ntime.sleep(10000)\n"
        self.put(_zip([("bin/agora", hang)]))
        empty = os.path.join(self.tmp, "emptybin")
        os.makedirs(empty)
        self._patch(TICK_CAP_S=8, TASKKILL_TIMEOUT_S=3, REAP_TIMEOUT_S=1, KILL_BUDGET_S=4, AGORA_MIN_TIMEOUT_S=1)
        spawn_s = 2.0
        real_popen = jc.subprocess.Popen
        real_kill = jc._kill_group
        at = {}

        def slow_popen(argv, *a, **kw):
            if "counsel" in argv:
                at["spawn"] = time.monotonic()           # ≈ tick 의 spawn_at(Popen 직전)
                time.sleep(spawn_s)
            return real_popen(argv, *a, **kw)

        def timed_kill(proc):
            at.setdefault("kill", time.monotonic())      # 몫이 끝나 끝내기를 시작한 순간
            return real_kill(proc)
        jc.subprocess.Popen = slow_popen
        jc._kill_group = timed_kill
        try:
            with envset(PATH=empty, CYS_CYS_BIN=None, AGORA_SIGNING_KEY=None):
                t0 = time.monotonic()
                self.assertEqual(jc.tick(), "timeout")
                took = time.monotonic() - t0
        finally:
            jc.subprocess.Popen = real_popen
            jc._kill_group = real_kill
        self.assertLessEqual(took, jc.TICK_CAP_S, took)  # ★계약 — 시작 → 반환(띄우기·끝내기 포함) ≤ 상한
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        share = ev[-1]["timeout_s"]
        self.assertGreaterEqual(share, 2, "축척판 전제 깨짐(경과 ≥ 2초) — 몫 %s · 판별 여유가 없다" % share)
        window = at["kill"] - at["spawn"]
        self.assertLess(window, max(spawn_s, share) + 1.0,
                        "띄우는 시간이 agora 몫 밖에서 셌다: 띄우기→끝내기 %.2f초 (몫 %s · 띄우기 %.1f)" % (window, share, spawn_s))

    def test_no_time_skips_agora(self):
        """남은 몫 < 30초 = agora 를 띄우지 않는다 · tick.log `no_time`."""
        self.put(_zip([("bin/agora", EnsureClient.AGORA)]))
        empty = os.path.join(self.tmp, "emptybin")
        os.makedirs(empty)
        self._patch(TICK_CAP_S=jc.KILL_BUDGET_S + 29)              # 경과 ≈ 0 → 남은 몫 29 = 471초 경과와 같은 자리
        with envset(PATH=empty, CYS_CYS_BIN=None):
            self.assertEqual(jc.tick(), "no_time")
        self.assertFalse(os.path.exists(self.lib("called.json")), "남은 몫이 없는데 agora 를 띄웠다")
        ev = [json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()]
        self.assertEqual((ev[-1]["event"], ev[-1]["result"]), ("tick", "no_time"))

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
        self._patch(TICK_CAP_S=3 + jc.KILL_BUDGET_S, AGORA_MIN_TIMEOUT_S=1)   # agora 몫 3
        with envset(PATH=empty, CYS_CYS_BIN=None):
            t0 = time.monotonic()
            self.assertEqual(jc.tick(), "timeout")
            self.assertLess(time.monotonic() - t0, 30)
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
        self.assertEqual((ev[-1]["event"], ev[-1]["result"], ev[-1]["killed"]), ("tick", "timeout", "killpg"))
        self.assertIn(ev[-1]["timeout_s"], (1, 2, 3))


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


RACE_WRITER = r'''
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import javis_counsel as jc
# 쓴 줄 수를 종료 코드로 돌려준다(0 = 한 줄 씀 · 3 = 못 씀). 상한은 넉넉히 — 이 시험이 재는 것은 「잠금이 서로를 막는가」다.
sys.exit(0 if jc.write_signals("worker", [(sys.argv[2], "race.e1")], wait_s=float(sys.argv[3])) == 1 else 3)
'''


class CrossLockRace(Base):
    """⑩ 팩 쓰기(`write_signals` 동시 다발 · 별 프로세스) ↔ 동봉 아고라 `collector.move_sent` 반복 — 같은 옆 잠금
    (`signals.lock` 0번 바이트)으로 막히는가. 모든 줄이 signals.jsonl ∪ signals-sent.jsonl 에 정확히 한 번 · LF.

    ★상한(TICKET=cysr-118-counsel-race · 2026-10-07): 쓰는 쪽은 넉넉한 상한(RACE_WAIT_S)으로 부르고 **각자 썼는지**를 종료 코드로 단언한다.
      종전은 CLI(`signal` · 기본 상한 2초 · 넘으면 설계상 버리고 exit 0)로 불러 「버린 쓰기」와 「쓴 뒤 사라진 줄」을 가르지 못했다 —
      윈 러너 부하에서 쓰기 한 번이 2초를 넘어(실측 최대 3.58초 · 옮기는 쪽 보유 최대 1.05초) 설계대로 버려진 줄이 「줄 유실」 적색이 됐다
      (CI 3회 · 누락 21·26·9줄 · 프로브: 부하 30판 중 2판 적색 · 누락 25줄 전부 반환 0 · 쓴 뒤 사라짐 0 · 상한 60초 30판 0 적색).
      2초 버림 계약은 Signal.test_lock_held_drops_after_timeout 이 따로 잰다(CLI 포함)."""

    N = 60
    WAVE = 20
    RACE_WAIT_S = 60.0

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
        writer_py = os.path.join(self.tmp, "writer.py")
        with open(writer_py, "w") as f:
            f.write(RACE_WRITER)
        try:
            ops = ["race.w%03d" % i for i in range(self.N)]
            not_written = []
            for k in range(0, self.N, self.WAVE):
                procs = [(op, subprocess.Popen([sys.executable, writer_py, BIN, op, str(self.RACE_WAIT_S)], env=env))
                         for op in ops[k:k + self.WAVE]]
                for op, p in procs:
                    if p.wait(timeout=self.RACE_WAIT_S + 60) != 0:
                        not_written.append(op)
            self.assertEqual(not_written, [], "쓰는 쪽이 상한(%s초) 안에 잠금을 못 잡았다(기아) — 줄 유실과 다른 실패" % self.RACE_WAIT_S)
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


AGORA_HOLD = r'''
import sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from agora import collector
with collector._file_lock(sys.argv[2], wait=(sys.argv[3] == "wait")) as held:
    print("held" if held else "busy", flush=True)
    if held:
        sys.stdin.readline()                     # 부모가 stdin 을 닫을 때까지 쥔다
'''


class ByteZeroLock(Base):
    """팩 `_acquire`(0번 바이트 · 윈 msvcrt / POSIX flock) ↔ 동봉 아고라 `collector._file_lock` — 서로를 막는다(양방향)."""

    def setUp(self):
        super().setUp()
        self.client = bundled_client(os.path.join(self.tmp, "client"))
        self.hold_py = os.path.join(self.tmp, "hold.py")
        with open(self.hold_py, "w", encoding="utf-8") as f:
            f.write(AGORA_HOLD)
        os.makedirs(os.path.join(self.cfg, "counsel"))
        self.lock = os.path.join(self.cfg, "counsel", "signals.lock")

    def agora(self, mode):
        return subprocess.Popen([sys.executable, self.hold_py, self.client, self.lock, mode], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

    def test_agora_holds_pack_drops(self):
        p = self.agora("wait")
        try:
            self.assertEqual(p.stdout.readline().strip(), b"held", p.stderr.read()[-400:] if p.poll() is not None else "")
            self.assertEqual(jc.write_signals("pack", [("a", "b")], wait_s=0.4), 0, "아고라가 쥔 잠금을 팩이 뚫었다")
        finally:
            p.stdin.close()
            p.wait(timeout=30)
            p.stdout.close()
            p.stderr.close()
        self.assertEqual(jc.write_signals("pack", [("a", "b")], wait_s=2), 1, "놓은 뒤에는 써야 한다")
        self.assertEqual(os.path.getsize(self.lock), 0, "잠금 파일에 내용이 쓰였다")

    def test_pack_holds_agora_busy(self):
        fh = jc._acquire(self.lock, 0)
        self.assertIsNotNone(fh)
        try:
            p = self.agora("nowait")
            out, err = p.communicate(input=b"", timeout=30)
            self.assertEqual(out.strip(), b"busy", err[-400:])
        finally:
            jc._unlock(fh)
            fh.close()
        p = self.agora("nowait")
        out, err = p.communicate(input=b"", timeout=30)
        self.assertEqual(out.strip(), b"held", err[-400:])


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


@unittest.skipIf(os.name == "nt", "cys-dept 를 격리 HOME 에서 bash 로 직접 실행(POSIX 셸·python3 전제) — 윈 cys-dept 실행 단계는 "
                                   "windows-health 의 부서 실행 단계 스텝이 따로 실기한다")
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
