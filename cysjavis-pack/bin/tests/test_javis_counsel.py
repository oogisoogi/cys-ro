#!/usr/bin/env python3
"""test_javis_counsel — ★T3(agora-t3-pack-collector): 상담소 자동 전달의 팩 쪽(`bin/javis_counsel.py`).

지키는 것(agora 클라이언트 `collector.py`·`mail.py` 와 글자 그대로 같은 계약):
  ① 신호 줄 정규식(ts·source·op·error_code·version·os) 수용/거부 벡터 · 형식 밖 줄은 안 쓴다
  ② CYS_ROLE → source 표 · 끄기 규칙 표(config.json 7행) · 2MB 넘으면 버림 · CRLF 0 · 한 줄 = 정렬 키 압축 JSON
  ③ 잠금 — 남이 쥐고 있으면 상한(기본 2초) 뒤 버리고 exit 0(훅을 붙잡지 않는다)
  ④ facts — 가짜 cys(PATH 대역)·가짜 상태 파일로 칸별 산출 · 못 잰 칸은 뺀다(null 0)
  ⑤ ensure-client — 올바른 sha = 설치+.pin · 틀린 sha = 거부 · 남의 lib = 불가침 · 같은 핀 = 무동작 · zip-slip = 거부
  ⑥ tick — 가짜 `lib/bin/agora` 가 받은 인자·AGORA_SIGNING_KEY
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
import time
import unittest
import zipfile

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
        self.assertEqual(facts["seats"], {"count": 5, "roles": ["master", "worker-3"]}, "비종료 5 · 형식 밖 역할은 목록에서만 뺀다")
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
        self.assertEqual(rd(self.lib(".pin")).strip(), line)
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
        self.assertEqual(ev[-1]["why"], "foreign client")

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
