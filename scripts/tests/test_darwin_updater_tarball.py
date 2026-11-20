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



# ★1.1.16(TICKET=cysr-1116-debt-d-1119 · V10): 스크립트가 tar 를 서명 전에 칩 검사한다 → 가짜 앱에도 목표 칩의 Mach-O 머리(합성 ·
#   test_check_macho_arch.thin 과 같은 꼴)와 필수 런타임 4개를 둔다. 칩 = 그 레인(aarch64 → arm64 · x64 → x86_64).
_CPU = {"aarch64": 0x0100000C, "x64": 0x01000007}
_RUNTIME = ("Contents/Resources/runtime/python/bin/python3", "Contents/Resources/runtime/node/bin/node",
            "Contents/Resources/runtime/git/bin/git", "Contents/Resources/runtime/uv/uv")


def _macho(cpu):
    import struct
    sub = 3 if cpu == 0x01000007 else 0   # 검사기 규칙: x86_64 = subtype ALL(3) · arm64 = ALL(0)
    return struct.pack("<IIIIIIII", 0xFEEDFACF, cpu, sub, 2, 0, 0, 0, 0) + b"\0" * 64


def put_macho_bundle(app, arch, skip=()):
    """APP 에 진입점(Contents/MacOS/cys-app)과 필수 런타임 4개를 ARCH 칩 Mach-O 로 심는다(SKIP = 빼 둘 상대 경로)."""
    for rel in ("Contents/MacOS/cys-app",) + _RUNTIME:
        if rel in skip:
            continue
        p = os.path.join(app, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(_macho(_CPU[arch]))
        os.chmod(p, 0o755)


def fake_app(root, arch="aarch64", skip=()):
    app = os.path.join(root, "staging", "cysr.app")
    os.makedirs(os.path.join(app, "Contents", "MacOS"), exist_ok=True)
    with open(os.path.join(app, "Contents", "Info.plist"), "w") as fh:
        fh.write("plist\n")
    put_macho_bundle(app, arch, skip)
    return app


class UpdaterTarball(unittest.TestCase):
    def run_script(self, tmp, arch="aarch64", env=None, app_arch=None, skip=()):
        e = dict(os.environ)
        e.pop("TAURI_SIGNING_PRIVATE_KEY", None)  # 키 없는 경로가 기본 — 시험이 진짜 서명을 하지 않는다
        e.update(env or {})
        return subprocess.run(
            ["sh", SCRIPT, "--app", fake_app(tmp, app_arch or arch, skip), "--out", os.path.join(tmp, "out"), "--arch", arch],
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

    def test_wrong_chip_or_missing_runtime_stops_before_signing(self):
        """★1.1.16(V10): x64 레인에 arm64 바이너리 · 필수 런타임 하나 없음 = 칩 검사 실패 → tar 지움 · 서명 단계(rc 3 자리표시) 0."""
        for kw in ({"arch": "x64", "app_arch": "aarch64"}, {"skip": ("Contents/Resources/runtime/uv/uv",)}):
            with tempfile.TemporaryDirectory() as tmp:
                p = self.run_script(tmp, **kw)
                self.assertNotIn(p.returncode, (0, 3), (kw, p.stdout, p.stderr))
                self.assertIn("칩 검사 실패", p.stderr, kw)
                self.assertEqual([n for n in os.listdir(os.path.join(tmp, "out")) if ".tar.gz" in n], [], kw)

    def test_right_chip_passes_the_gate(self):
        for arch in ("aarch64", "x64"):
            with tempfile.TemporaryDirectory() as tmp:
                p = self.run_script(tmp, arch=arch)
                self.assertEqual(p.returncode, 3, (arch, p.stderr))   # 키 없음 = tar 까지(검사 통과)
                self.assertIn("✓ 칩 검사", p.stdout, arch)

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
