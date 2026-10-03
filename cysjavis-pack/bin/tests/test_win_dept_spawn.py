#!/usr/bin/env python3
"""precut-fix3(10-02 윈 실기 · TICKET=cys-117-precut-fix3-1002) — 말로 부서 만들기·닫기의 **실행 단계**를
진짜 프로세스로 띄워 본다(목(mock) 없음).

원인(윈 실기 tick-errors.log 원문): `OSError: [WinError 193] %1은(는) 올바른 Win32 응용 프로그램이 아닙니다`
@ javis_dept_request._spawn_create — 확장자 없는 bash 스크립트 cys-dept 를 인터프리터 없이 Popen.
윈도우 CreateProcess 는 셔뱅(#!/usr/bin/env bash)을 모른다.

이 파일은 windows-health(윈 러너)와 3완전 레인(맥·우분투)에서 함께 돈다:
  ⒜ 대조군(윈 전용) — 가짜 cys-dept 를 직접 Popen = OSError winerror 193. 고치기 전 코드의 빨강을 러너에서 실증한다
     (이게 초록이면 원인 명명이 기각된 것 — 수리 초록만으로 합격 판정하지 마라).
  ⒝ 만들기 — 실제 `_spawn_create` 가 가짜 cys-dept 를 띄워 rc 0 · 인자 · CYS_ROLE=cso · stdout 파일 기록.
  ⒞ 닫기 — `javis_org.dept_cmd(…, ["down", …])` 를 destroy_dept 와 같은 subprocess.run 꼴로 실행.
  ⒟ 윈 전용 — dept_cmd 가 쓰는 해소(win_bash)가 System32 의 WSL 스텁이 아니다(러너에서 실제 값 · which 값 병기).
  ⒠ 모든 OS — windows=True 강제 감쌈을 진짜 bash 로 실행(인자 순서 [bash, 스크립트, 동사…] 가 실제로 돈다).
stdlib 전용 · 네트워크 0 · 실 ~/.cys 를 건드리지 않는다(경로 전부 임시 폴더 env 주입).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BIN not in sys.path:
    sys.path.insert(0, BIN)

import javis_org  # noqa: E402
import javis_dept_request as dr  # noqa: E402

IS_WIN = os.name == "nt"

# 가짜 cys-dept — 확장자 없음 · 셔뱅 bash(실물과 같은 꼴). 인자와 CYS_ROLE 을 표식 파일에 적고, 만들기는
# 실물처럼 마지막 줄에 부서 이름을 stdout 으로 낸다.
FAKE = ('#!/usr/bin/env bash\n'
        'printf "%s|%s\\n" "${CYS_ROLE:-}" "$*" >> "$FAKE_MARK"\n'
        'if [ "$1" = "create" ]; then echo dept-7; fi\n'
        'exit 0\n')


def _posix(p):
    # bash(msys) 쪽에 넘기는 경로는 정슬래시로 — 백슬래시 해석 차이를 시험 변수에서 뺀다.
    return p.replace("\\", "/")


class TestWinDeptSpawnReal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wds-")
        self.fake = os.path.join(self.tmp, "cys-dept")
        with open(self.fake, "w", newline="\n") as f:
            f.write(FAKE)
        os.chmod(self.fake, 0o755)
        self.mark = os.path.join(self.tmp, "mark.txt")
        self.req = os.path.join(self.tmp, "dept-requests")
        os.makedirs(self.req)
        self._env = {k: os.environ.get(k) for k in ("CYS_DEPT_BIN", "CYS_DEPT_REQUESTS", "FAKE_MARK")}
        os.environ["CYS_DEPT_BIN"] = self.fake
        os.environ["CYS_DEPT_REQUESTS"] = self.req
        os.environ["FAKE_MARK"] = _posix(self.mark)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def marks(self):
        with open(self.mark, encoding="utf-8") as f:
            return f.read().splitlines()

    @unittest.skipUnless(IS_WIN, "대조군 = 윈도우 CreateProcess 전용(맥·리눅스는 셔뱅을 안다)")
    def test_a_control_direct_popen_is_winerror_193(self):
        with self.assertRaises(OSError) as cm:
            subprocess.Popen([self.fake, "create", "k1"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertEqual(getattr(cm.exception, "winerror", None), 193,
                         "원인 명명(WinError 193)이 러너에서 재현되지 않았다: %r" % (cm.exception,))

    def test_b_create_real_spawn_create_runs(self):
        cysd = sys.executable                      # PATH 앞에 붙일 폴더 출처일 뿐 — 실행하지 않는다
        p, lf = dr._spawn_create("k1", cysd, 1)
        try:
            rc = p.wait(timeout=60)
        finally:
            lf.close()
        self.assertEqual(rc, 0)
        self.assertEqual(self.marks(), ["cso|create k1"])
        with open(dr.create_out_path("k1", 1), encoding="utf-8") as f:
            self.assertEqual(f.read().strip().splitlines()[-1], "dept-7")

    def test_c_down_runs_like_destroy_dept(self):
        cmd = javis_org.dept_cmd(self.fake, ["down", "dept-1", "--purge-state"])
        r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ), **javis_org.NOWIN)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.marks()[-1].split("|", 1)[1], "down dept-1 --purge-state")

    @unittest.skipUnless(IS_WIN, "WSL 스텁 = 윈도우 전용")
    def test_d_resolved_bash_is_not_wsl_stub(self):
        b = javis_org.win_bash()                   # dept_cmd 가 실제로 쓰는 해소(WSL 스텁 제외)
        self.assertTrue(b, "PATH 에 (스텁 아닌) bash 가 없다")
        print("which(bash) = %s" % shutil.which("bash"))
        low = os.path.normcase(b)
        sysdir = os.path.normcase(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"))
        self.assertFalse(low.startswith(sysdir + os.sep), "WSL 스텁을 집었다: %s" % b)
        self.assertNotIn(os.path.normcase("\\WindowsApps\\"), low, "WSL 스텁을 집었다: %s" % b)
        print("resolved bash = %s" % b)

    def test_e_forced_windows_wrap_runs_on_real_bash(self):
        # 윈 = 실제 해소(win_bash) · 맥·리눅스 = bash.exe 가 없으니 which 주입(감쌈의 인자 순서를 진짜 bash 로 본다)
        cmd = javis_org.dept_cmd(self.fake, ["create", "k2"], windows=True, which=None if IS_WIN else shutil.which)
        self.assertEqual(cmd[1:], [self.fake, "create", "k2"])
        r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ), **javis_org.NOWIN)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "dept-7")
        self.assertEqual(self.marks()[-1].split("|", 1)[1], "create k2")


CR_PY_WRAPPER = r'''#!/bin/bash
# 맥·리눅스에서 윈 파이썬의 줄 끝(\r\n)을 흉내 — cys-dept create 의 카탈로그 한 줄 읽기(그 파이썬 조각)에만 적용한다.
if [ "${1:-}" = "-" ]; then
  shift; t="$(mktemp)"; cat > "$t"
  if grep -q "d\['departments'\].get(key)" "$t"; then
    "$REAL_PY3" "$t" "$@" | "$REAL_PY3" -c "import sys;sys.stdout.write(sys.stdin.read().replace('\n','\r\n'))"
    rc=${PIPESTATUS[0]}; rm -f "$t"; exit $rc
  fi
  "$REAL_PY3" "$t" "$@"; rc=$?; rm -f "$t"; exit $rc
fi
exec "$REAL_PY3" "$@"
'''


class TestCreateCatalogCR(unittest.TestCase):
    """precut-fix3 다음 벽(윈 러너 관측 실측 · master#057fb9b7): 윈 Git bash 의 `read < <(python3 …)` 는 줄 끝 \\r 을
    남긴다 → cys-dept create 의 카탈로그 한 줄(마지막 칸 = cwd)이 \\r 을 달고 등록부에 들어갔다. 진짜 cys-dept create 를
    REUSE_DEAD 길(등록부 cwd 를 카탈로그 값으로 다시 쓰는 길)로 돌리고, 가짜 데몬이 바로 끝나 기동 실패(등록 유지)로
    멈추게 해서 등록부 cwd 를 본다. 윈 = 진짜 \\r\\n · 맥·리눅스 = 그 조각에만 \\r\\n 을 입히는 python3 감쌈."""

    def test_f_create_catalog_line_cr_not_in_registry_cwd(self):
        import json
        tmp = tempfile.mkdtemp(prefix="wcr-")
        try:
            home = os.path.join(tmp, "home"); os.makedirs(home)
            acct = os.path.join(tmp, "acct"); os.makedirs(acct)
            cwd = os.path.join(tmp, "dept-folder"); os.makedirs(cwd)
            cat = os.path.join(tmp, "catalog.json"); reg = os.path.join(tmp, "depts.json")
            with open(cat, "w", encoding="utf-8") as f:
                json.dump({"accounts": {"acc": acct}, "departments": {"k1": {
                    "display": "시험부", "account": "acc", "mission_key": "mk1", "cwd": cwd}}}, f)
            sock = r"\\.\pipe\cys-dept-wcr-none" if IS_WIN else os.path.join(tmp, "none.sock")
            with open(reg, "w", encoding="utf-8") as f:
                json.dump({"depts": {"dept-1": {"socket": sock, "pack_dir": os.path.join(home, "p"), "role": "dept-master",
                                                "mission_key": "mk1", "cwd": "old", "account_dir": acct,
                                                "reserved_at": 0, "gen": "aa"}}}, f)
            env = {k: v for k, v in os.environ.items() if not k.startswith("CYS_")}
            env.update({"HOME": home, "LOCALAPPDATA": os.path.join(tmp, "la"), "CYS_ROLE": "cso", "CYS_NO_AUTOSTART": "1",
                        "CYS_DEPT_CATALOG": cat, "CYS_DEPTS_JSON": reg,
                        "CYS_DEPT_MISSIONS": os.path.join(tmp, "missions"),
                        # 가짜 데몬·cys = 인자 없는/엉뚱한 인자의 파이썬 → 곧바로 끝남(ping 실패 · 기동 실패)
                        "CYS_CYSD_BIN": sys.executable, "CYS_CYS_BIN": sys.executable})
            if not IS_WIN:
                wd = os.path.join(tmp, "wrap"); os.makedirs(wd)
                w = os.path.join(wd, "python3")
                with open(w, "w", newline="\n") as f:
                    f.write(CR_PY_WRAPPER)
                os.chmod(w, 0o755)
                env["REAL_PY3"] = shutil.which("python3") or sys.executable
                env["PATH"] = wd + os.pathsep + env.get("PATH", "")
            cmd = javis_org.dept_cmd(os.path.join(BIN, "cys-dept"), ["create", "k1"], posix_bash=True)
            r = subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL,
                               timeout=120, **javis_org.NOWIN)
            self.assertIn("등록부 잔존(dept-1)", r.stderr, "REUSE_DEAD 길을 타지 않았다:\n%s" % r.stderr[-1500:])
            with open(reg, encoding="utf-8") as f:
                got = json.load(f)["depts"]["dept-1"]["cwd"]
            self.assertNotIn("\r", got, "등록부 cwd 에 \\r 이 들어갔다: %r" % got)
            self.assertEqual(got, cwd)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestSiblingSweep(unittest.TestCase):
    """형제 스윕(precut-fix3 ②): 같은 cys-dept 를 문자 그대로의 "bash" 로 띄우던 3곳 — 윈도우 CreateProcess 는
    System32 를 PATH 보다 먼저 보므로 WSL 이 깔린 기계에서는 WSL 스텁(System32\\bash.exe)을 집는다.
    윈 = dept_cmd(bash 전체 경로) · 맥·리눅스 = 종전 그대로 ["bash", 스크립트, …](posix_bash=True)."""

    def test_posix_bash_keeps_mac_argv_and_wraps_windows(self):
        which = lambda n: r"C:\cys\runtime\git\usr\bin\bash.exe" if n == "bash" else None
        self.assertEqual(javis_org.dept_cmd("/p/cys-dept", ["launch", "d1"], windows=False, which=which, posix_bash=True),
                         ["bash", "/p/cys-dept", "launch", "d1"])
        self.assertEqual(javis_org.dept_cmd("/p/cys-dept", ["launch", "d1"], windows=True, which=which, posix_bash=True),
                         [r"C:\cys\runtime\git\usr\bin\bash.exe", "/p/cys-dept", "launch", "d1"])
        with self.assertRaises(javis_org.BashNotFound):
            javis_org.dept_cmd("/p/cys-dept", ["launch", "d1"], windows=True, which=lambda n: None, posix_bash=True)

    def test_win_bash_skips_wsl_stub_before_real(self):
        # 윈 기본 시스템 PATH 머리 = C:\Windows\System32 — WSL 이 깔린 기계에서 which("bash") 가 집는 스텁을 건너뛴다.
        real = r"C:\Users\user\AppData\Local\cys\runtime\git\usr\bin"
        path = ";".join([r"C:\WINDOWS\system32", r"C:\Windows\SysWOW64",
                         r"C:\Users\user\AppData\Local\Microsoft\WindowsApps", real])
        files = {r"C:\WINDOWS\system32\bash.exe", r"C:\Windows\SysWOW64\bash.exe",
                 r"C:\Users\user\AppData\Local\Microsoft\WindowsApps\bash.exe", real + r"\bash.exe"}
        got = javis_org.win_bash(path, sysroot=r"C:\Windows", isfile=lambda p: p in files)
        self.assertEqual(got, real + r"\bash.exe")

    def test_win_bash_stub_only_is_bash_not_found(self):
        path = r"C:\Windows\System32;C:\Users\user\AppData\Local\Microsoft\WindowsApps"
        files = {r"C:\Windows\System32\bash.exe", r"C:\Users\user\AppData\Local\Microsoft\WindowsApps\bash.exe"}
        self.assertIsNone(javis_org.win_bash(path, sysroot=r"C:\Windows", isfile=lambda p: p in files))
        orig = javis_org.win_bash
        javis_org.win_bash = lambda *a, **k: orig(path, sysroot=r"C:\Windows", isfile=lambda p: p in files)
        try:
            with self.assertRaises(javis_org.BashNotFound):
                javis_org.dept_cmd("/p/cys-dept", ["create", "k1"], windows=True)
        finally:
            javis_org.win_bash = orig

    def _src(self, name):
        with open(os.path.join(BIN, name), encoding="utf-8") as f:
            return f.read()

    def test_formation_revive_uses_dept_cmd(self):
        s = self._src("javis_formation.py")
        self.assertNotIn('["bash", tool, "launch", name]', s, "부서 다시 켜기가 문자 그대로의 bash 를 띄운다(윈 WSL 스텁)")
        self.assertIn('javis_org.dept_cmd(tool, ["launch", name], posix_bash=True)', s)

    def test_bootstrap_promote_signal_uses_dept_cmd(self):
        s = self._src("javis_bootstrap.py")
        self.assertNotIn('_run(["bash", dept, "promote-if-pending"', s)
        self.assertNotIn('_run(["bash", base_dept, "promote-if-pending"', s)
        self.assertEqual(s.count('["promote-if-pending", "--request-only"], posix_bash=True)'), 2)
        self.assertEqual(s.count("except Exception as e:   # bash 없음(BashNotFound)·형제 import 실패"), 2,
                         "bash 없음이 부트를 죽이면 안 된다(best-effort)")


if __name__ == "__main__":
    unittest.main()
