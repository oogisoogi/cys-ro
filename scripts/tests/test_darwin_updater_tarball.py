#!/usr/bin/env python3
"""구판(1.0.2) 맥 레인 자산 생성기 회귀 — TICKET=v110-darwin-update · master 판정 B.

지키는 성질 셋:
  ① tar 최상위 구성요소가 **정확히 하나** — 플러그인이 첫 구성요소를 버리고(updater.rs:1238)
     나머지를 기존 번들 자리에 넣으므로, 둘 이상이면 두 번째부터가 엉뚱한 자리에 풀린다.
  ② 서명 키가 없으면 **rc 3 + 자리표시 파일** — 서명 없는 자산이 조용히 발행되지 않는다.
  ③ 이름이 release-verify.py 의 맥 레인 목록과 같다(두 곳이 갈리면 검증기가 정상 묶음을 죽인다).
"""
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "scripts", "make-darwin-updater-tarball.sh")


def fake_app(root):
    app = os.path.join(root, "staging", "cysr.app")
    os.makedirs(os.path.join(app, "Contents", "MacOS"), exist_ok=True)
    with open(os.path.join(app, "Contents", "Info.plist"), "w") as fh:
        fh.write("plist\n")
    with open(os.path.join(app, "Contents", "MacOS", "cys-app"), "w") as fh:
        fh.write("bin\n")
    return app


class UpdaterTarball(unittest.TestCase):
    def run_script(self, tmp, arch="aarch64", env=None):
        e = dict(os.environ)
        e.pop("TAURI_SIGNING_PRIVATE_KEY", None)  # 키 없는 경로가 기본 — 시험이 진짜 서명을 하지 않는다
        e.update(env or {})
        return subprocess.run(
            ["sh", SCRIPT, "--app", fake_app(tmp), "--out", os.path.join(tmp, "out"), "--arch", arch],
            capture_output=True, text=True, env=e, cwd=ROOT,
        )

    def test_single_top_level_component(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_script(tmp)
            tar = os.path.join(tmp, "out", "cysr_aarch64.app.tar.gz")
            self.assertTrue(os.path.exists(tar))
            with tarfile.open(tar) as tf:
                tops = {n.split("/")[0] for n in tf.getnames()}
            self.assertEqual(tops, {"cysr.app"})

    def test_missing_key_is_rc3_with_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.run_script(tmp)
            self.assertEqual(p.returncode, 3, p.stderr)
            self.assertTrue(os.path.exists(os.path.join(tmp, "out", "cysr_aarch64.app.tar.gz.sig.MISSING")))
            self.assertFalse(os.path.exists(os.path.join(tmp, "out", "cysr_aarch64.app.tar.gz.sig")))

    def test_missing_app_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.run(
                ["sh", SCRIPT, "--app", os.path.join(tmp, "없는.app"), "--out", os.path.join(tmp, "out")],
                capture_output=True, text=True, cwd=ROOT,
            )
            self.assertEqual(p.returncode, 2)

    def test_names_match_release_verify_mac_lane(self):
        """이름을 두 벌로 두지 않는다 — 검증기가 기대하는 목록에서 그대로 읽어 대조한다."""
        src = open(os.path.join(ROOT, "scripts", "release-postprocess.py"), encoding="utf-8").read()
        lane = re.search(r"MAC_LANE = \((.*?)\)", src, re.S).group(1)
        self.assertIn("cysr_aarch64.app.tar.gz", lane)
        self.assertIn("cysr_aarch64.app.tar.gz.sig", lane)
        script = open(SCRIPT, encoding="utf-8").read()
        self.assertIn('TAR="$OUT_ABS/cysr_${ARCH}.app.tar.gz"', script)

    def test_script_never_creates_a_key(self):
        """키 생성 명령이 이 스크립트에 있어서는 안 된다(새 키 = 구판 검증 실패)."""
        script = open(SCRIPT, encoding="utf-8").read()
        self.assertNotIn("signer generate", script)
        self.assertIn("키를 만들지 않는다", script)


if __name__ == "__main__":
    unittest.main()
