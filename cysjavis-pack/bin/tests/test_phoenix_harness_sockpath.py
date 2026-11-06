#!/usr/bin/env python3
"""하네스 소켓 경로 상한 — v1.1.12 태그 런(42135725605 arm64) 적색의 회귀 그물 (TICKET=cysr-1113-phoenix-residual).

러너 TMPDIR 를 정규 경로(`/private/var/folders/<2>/<28>/T`)로 바꾸면 하네스 소켓이 111바이트가 되어
macOS 상한(sun_path 104 = 103 + NUL)을 넘는다 → connect 가 errno 없는 OSError → transport_error →
endpoint_unobserved → `_fresh_harness` FATAL. 데몬을 띄우지 않고(바이너리 불요) 세 갈래를 잰다:
  ① 하네스가 스스로 고른 홈은 긴 TMPDIR 아래서도 소켓이 상한 안(정규 /tmp 로 다시 고름)
  ② 명시 PHOENIX_HARNESS_HOME 이 길면 바꾸지 않고 guard_isolation 이 사유와 함께 exit 2
  ③ _harness_paths 는 긴 소켓을 transport_error 가 아니라 고정 사유 socket_path_too_long 으로 거부
  ④ 진단 줄(residual_diag)이 4항목 판정과 소켓 길이를 함께 남긴다
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HARN = os.path.realpath(os.path.join(HERE, "..", "javis_phoenix_harness.py"))
LIMIT = 103 if (sys.platform == "darwin" or "bsd" in sys.platform) else 107

PROBE = r"""
import importlib.util, json, os, sys, io
spec = importlib.util.spec_from_file_location("h", sys.argv[1])
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
mode = sys.argv[2]
if mode == "home":
    print(json.dumps({"home": h.HARN_HOME, "sock": h.HARN_SOCK, "max": h._SUN_PATH_MAX}))
elif mode == "paths":
    try:
        h._harness_paths(); print("ok")
    except h._HarnessError as e:
        print(str(e))
elif mode == "guard":
    h.guard_isolation(); print("guard-passed")
elif mode == "diag":
    buf = io.StringIO()
    ev = h.residual_diag(h.residual_report(), out=buf)
    print(buf.getvalue().strip())
"""


def _long_canonical_dir(root):
    """정규 경로 아래에서 하네스 홈 소켓이 상한을 반드시 넘는 깊이의 폴더."""
    d = root
    while len(os.fsencode(os.path.join(d, "phoenix-harn-home-xxxxxxxx", ".cys", "state-harness", "cys.sock"))) <= LIMIT + 8:
        d = os.path.join(d, "d" * 20)
    os.makedirs(d, exist_ok=True)
    return d


@unittest.skipIf(os.name == "nt", "유닉스 소켓 경로 상한 축 — Windows 는 named pipe")
class SockPath(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="sockpath-"))
        self.long = _long_canonical_dir(self.root)
        self.made = []

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        for d in self.made:
            shutil.rmtree(d, ignore_errors=True)

    def _run(self, mode, **env):
        e = dict(os.environ)
        e.pop("PHOENIX_HARNESS_HOME", None)
        e.update(env)
        return subprocess.run([sys.executable, "-c", PROBE, HARN, mode], env=e, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=60)

    def test_1_self_picked_home_fits_under_long_tmpdir(self):
        import json
        r = self._run("home", TMPDIR=self.long)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.made.append(d["home"])
        self.assertLessEqual(len(os.fsencode(d["sock"])), d["max"], d["sock"])
        self.assertEqual(os.path.realpath(d["home"]), d["home"], "정규 경로여야 별칭 검사를 통과한다")
        self.assertTrue(d["home"].startswith(os.path.realpath("/tmp") + os.sep), d["home"])
        # 긴 TMPDIR 아래 빈 홈을 남기지 않는다(방금 만든 것만 지웠다).
        self.assertEqual([n for n in os.listdir(self.long) if n.startswith("phoenix-harn-home-")], [])
        r2 = self._run("paths", PHOENIX_HARNESS_HOME=d["home"])
        self.assertEqual(r2.stdout.strip(), "ok", r2.stderr)

    def test_2_explicit_long_home_refused_with_reason(self):
        home = os.path.join(self.long, "phoenix-harn-home-explicit")
        os.makedirs(home)
        r = self._run("guard", PHOENIX_HARNESS_HOME=home)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("guard-passed", r.stdout)
        self.assertIn("유닉스 소켓 상한", r.stderr)
        self.assertEqual(os.path.realpath(home), home)

    def test_3_paths_fixed_reason_not_transport_error(self):
        home = os.path.join(self.long, "phoenix-harn-home-explicit")
        os.makedirs(home)
        r = self._run("paths", PHOENIX_HARNESS_HOME=home)
        self.assertEqual(r.stdout.strip(), "socket_path_too_long", r.stderr)

    def test_4_diag_carries_verdict_and_sock_length(self):
        import json
        home = os.path.realpath(tempfile.mkdtemp(prefix="phoenix-harn-home-", dir=os.path.realpath("/tmp")))
        self.made.append(home)
        r = self._run("diag", PHOENIX_HARNESS_HOME=home)
        self.assertEqual(r.returncode, 0, r.stderr)
        line = r.stdout.strip()
        self.assertTrue(line.startswith("[harness][diag] "), line)
        ev = json.loads(line[len("[harness][diag] "):])
        for k in ("clean", "harness_daemon_pids", "owned_process_pids", "unobserved_owned", "harness_ping"):
            self.assertIn(k, ev["verdict"])
        self.assertEqual(ev["sock"]["max"], LIMIT)
        self.assertEqual(ev["paths"], "ok")
        self.assertIn("pgrep", ev)
        self.assertTrue(ev["verdict"]["clean"], ev)


if __name__ == "__main__":
    unittest.main(verbosity=2)
