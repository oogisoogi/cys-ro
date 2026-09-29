#!/usr/bin/env python3
"""(1.1.7 E1-b · TICKET=cysr-117-impl-brand) 맥 번들 명령 별칭 `Contents/MacOS/cysr -> cys` 시험.

`scripts/lib/mac-bundle-common.sh` 의 `mac_link_cli_alias` 를 **실제로 source 해서** 가짜 번들에 돌린다.
  ① 링크 생성(상대 · 대상 `cys`) ② 재실행 멱등 ③ 대상 `cys` 부재 = 빌드 중단(exit≠0)
  ④ 링크 아닌 실파일 `cysr` = 덮지 않고 중단 ⑤ `mac_build_app_bundle` 이 APP 확정 뒤 이 함수를 부른다(배선)
  ⑥ (맥 한정) 링크를 담은 번들이 ad-hoc `codesign --deep` → `--verify --deep --strict` 를 통과한다.
stdlib 전용 · 네트워크 0 · 임시 폴더만 쓴다.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB = os.path.join(REPO, "scripts", "lib", "mac-bundle-common.sh")


def run_fn(app):
    """lib 를 source 하고 mac_link_cli_alias <app> 실행 → (rc, 출력)."""
    r = subprocess.run(
        ["bash", "-c", 'set -euo pipefail; . "$1"; mac_link_cli_alias "$2"', "_", LIB, app],
        capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class MacCliAliasLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cysr-alias-")
        self.app = os.path.join(self.tmp, "cysr.app")
        self.macos = os.path.join(self.app, "Contents", "MacOS")
        os.makedirs(self.macos)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def _read(p):
        with open(p, "rb") as f:
            return f.read()

    def _exe(self, name, src="/usr/bin/true"):
        p = os.path.join(self.macos, name)
        shutil.copyfile(src, p)  # copy2 는 시스템 플래그(restricted)까지 옮겨 chflags 거부
        os.chmod(p, 0o755)
        return p

    def test_creates_relative_link_and_is_idempotent(self):
        self._exe("cys")
        for _ in range(2):  # ② 두 번 불러도 같은 결과
            rc, out = run_fn(self.app)
            self.assertEqual(rc, 0, out)
            link = os.path.join(self.macos, "cysr")
            self.assertTrue(os.path.islink(link), "cysr 가 링크가 아니다")
            self.assertEqual(os.readlink(link), "cys", "상대 링크 대상이 cys 가 아니다")
            self.assertTrue(os.access(link, os.X_OK))

    def test_missing_target_fails_closed(self):
        rc, out = run_fn(self.app)
        self.assertNotEqual(rc, 0, "cys 가 없는데 통과 — 끊어진 링크가 배송된다")
        self.assertFalse(os.path.lexists(os.path.join(self.macos, "cysr")))

    def test_real_file_is_not_overwritten(self):
        self._exe("cys")
        real = self._exe("cysr", "/usr/bin/false")
        before = self._read(real)
        rc, out = run_fn(self.app)
        self.assertNotEqual(rc, 0, "실파일 cysr 를 조용히 덮었다")
        self.assertFalse(os.path.islink(real))
        self.assertEqual(self._read(real), before)

    def test_build_function_wires_the_alias_after_app_is_set(self):
        with open(LIB, encoding="utf-8") as f:
            src = f.read()
        m = re.search(r"^mac_build_app_bundle\(\) \{\n(.*?)^\}", src, re.S | re.M)
        self.assertTrue(m, "mac_build_app_bundle 본문을 못 찾았다")
        body = m.group(1)
        i_app = body.find('APP="$BUNDLE_BASE/macos/cysr.app"')
        i_call = body.find('mac_link_cli_alias "$APP"')
        self.assertGreaterEqual(i_app, 0, "APP 확정 줄이 사라졌다")
        self.assertGreater(i_call, i_app, "별칭 링크 호출이 없거나 APP 확정 전에 있다")

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("codesign"), "맥 codesign 전용")
    def test_link_survives_deep_sign_and_strict_verify(self):
        self._exe("cys-app")
        self._exe("cys")
        with open(os.path.join(self.app, "Contents", "Info.plist"), "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0"><dict>'
                    "<key>CFBundleExecutable</key><string>cys-app</string>"
                    "<key>CFBundleIdentifier</key><string>test.cysr.alias</string></dict></plist>\n")
        rc, out = run_fn(self.app)
        self.assertEqual(rc, 0, out)
        s = subprocess.run(["codesign", "--force", "--deep", "--sign", "-", self.app],
                           capture_output=True, text=True)
        self.assertEqual(s.returncode, 0, s.stderr)
        v = subprocess.run(["codesign", "--verify", "--deep", "--strict", self.app],
                           capture_output=True, text=True)
        self.assertEqual(v.returncode, 0, "링크를 담은 번들이 엄격 검증에서 거부됐다: " + v.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
