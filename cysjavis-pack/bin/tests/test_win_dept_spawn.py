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
  ⒟ 윈 전용 — 해소된 bash 가 System32 의 WSL 스텁이 아니다(러너 PATH 순서 확인 · 거짓 초록 차단).
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
        b = shutil.which("bash")
        self.assertTrue(b, "PATH 에 bash 가 없다")
        low = os.path.normcase(b)
        sysdir = os.path.normcase(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"))
        self.assertFalse(low.startswith(sysdir + os.sep), "WSL 스텁을 집었다: %s" % b)
        self.assertNotIn(os.path.normcase("\\WindowsApps\\"), low, "WSL 스텁을 집었다: %s" % b)
        print("resolved bash = %s" % b)

    def test_e_forced_windows_wrap_runs_on_real_bash(self):
        cmd = javis_org.dept_cmd(self.fake, ["create", "k2"], windows=True)
        self.assertEqual(cmd[1:], [self.fake, "create", "k2"])
        r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ), **javis_org.NOWIN)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "dept-7")
        self.assertEqual(self.marks()[-1].split("|", 1)[1], "create k2")


if __name__ == "__main__":
    unittest.main()
