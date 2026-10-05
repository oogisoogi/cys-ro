#!/usr/bin/env python3
"""test_c82_win_isolation — ★D12(1.1.8): 윈 C82 「격리 실패: PATH 해소가 가짜 cys 가 아니다(…cys.EXE)」.

원인 = 윈 shutil.which 가 PATHEXT 확장자 파일만 잇는다(확장자 없는 가짜 cys 를 못 봄) — 훅을 도는 sh 는 가짜를 집는다.
처방 = 윈에서 파이썬 판정이 어긋나면 훅이 쓰는 셸의 `command -v cys` 로 다시 판정(javis_preflight._c82_fake_resolves).
맥에서는 윈 갈래를 is_win 인자로 밟는다(파이썬 which 어긋남 = 진짜 cys 경로를 넘겨 재현).
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import javis_preflight as pf  # noqa: E402

SH = shutil.which("sh") or "/bin/sh"


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c82-")
        self.fb = os.path.join(self.tmp, "bin")
        os.makedirs(self.fb)
        self.fake = os.path.join(self.fb, "cys")
        with open(self.fake, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(self.fake, 0o755)
        # 진짜 cys 흉내(다음 PATH 칸) — 파이썬 which 가 윈에서 집던 쪽
        self.other = os.path.join(tempfile.mkdtemp(prefix="real-"), "cys.EXE")
        open(self.other, "w").close()
        self.env = {"PATH": self.fb + os.pathsep + "/usr/bin:/bin"}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(os.path.dirname(self.other), ignore_errors=True)

    def test_same_file_ok_everywhere(self):
        self.assertEqual(pf._c82_fake_resolves(self.fake, self.fake, SH, self.env, False), (True, self.fake))

    def test_win_python_miss_but_shell_sees_fake(self):
        ok, got = pf._c82_fake_resolves(self.other, self.fake, SH, self.env, True)
        self.assertTrue(ok, got)
        self.assertTrue(got.endswith("/bin/cys") and os.path.basename(self.tmp) in got, got)

    def test_unix_mismatch_still_fails(self):
        ok, got = pf._c82_fake_resolves(self.other, self.fake, SH, self.env, False)
        self.assertEqual((ok, got), (False, self.other))

    def test_win_shell_also_misses_fails(self):
        env = {"PATH": "/usr/bin:/bin"}   # 격리 폴더가 PATH 에 없다 = 진짜 격리 실패
        ok, got = pf._c82_fake_resolves(self.other, self.fake, SH, env, True)
        self.assertFalse(ok)
        self.assertIn("sh=", got)

    def test_win_none_which_no_shell(self):
        self.assertEqual(pf._c82_fake_resolves(None, self.fake, None, self.env, True), (False, None))


if __name__ == "__main__":
    unittest.main()
