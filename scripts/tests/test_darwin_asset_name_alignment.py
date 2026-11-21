#!/usr/bin/env python3
"""구판(plugin) 맥 자산 **이름 정렬** 회귀 — TICKET=v110-zipurl · 2026-09-20.

지키는 성질 하나: **같은 자산을 만드는 두 생성기가 같은 이름을 쓴다.**
  · `scripts/make-update-manifest.sh` — latest.json 의 darwin 행 `url` 에 자산 이름을 **적는다**.
  · `scripts/make-darwin-updater-tarball.sh` — 그 자산을 실제로 **만든다**.
그리고 그 이름은 발행 레인(`release-postprocess.py` MAC_LANE)이 아는 이름이어야 한다.
셋 중 하나라도 어긋나면 latest.json 의 url 이 **발행되지 않는 이름**을 가리켜 구판(1.0.2) 맥의
자동 업데이트가 404 로 죽는다 — 그리고 그 죽음은 매니페스트를 눈으로 봐서는 보이지 않는다.

★이 시험은 소스를 grep 하지 않는다. 두 생성기를 **실제로 돌려** 산출물 이름을 읽는다
  (문자열 대조는 로직이 옮겨 가면 조용히 빗나간다). 실행은 tmp 사본 루트에서만 하며,
  마지막에 **저장소를 건드리지 않았음**을 스스로 단언한다.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
ROOT = os.path.dirname(SCRIPTS)

spec = importlib.util.spec_from_file_location(
    "release_postprocess", os.path.join(SCRIPTS, "release-postprocess.py"))
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

VERSION = "1.1.0"
LEGS = (("darwin-aarch64", "aarch64-apple-darwin", "aarch64"),
        ("darwin-x86_64", "x86_64-apple-darwin", "x64"))



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

def fake_root(tmp):
    """두 생성기만 든 사본 루트 — 스크립트는 제 위치의 `..` 만 보므로 이것으로 충분하다."""
    os.makedirs(os.path.join(tmp, "scripts"))
    for name in ("make-update-manifest.sh", "make-darwin-updater-tarball.sh", "check_macho_arch.py"):   # ★1.1.16 V10: 칩 검사기 동반
        shutil.copy2(os.path.join(SCRIPTS, name), os.path.join(tmp, "scripts", name))
    for _key, triple, _arch in LEGS:
        bundle = os.path.join(tmp, "target", triple, "release", "bundle", "macos")
        os.makedirs(bundle)
        with open(os.path.join(bundle, "cysr.app.tar.gz"), "wb") as fh:
            fh.write(b"\x1f\x8b" + b"0" * 64)          # 내용은 무관 — 이름만 잰다
        with open(os.path.join(bundle, "cysr.app.tar.gz.sig"), "w", encoding="utf-8") as fh:
            fh.write("dW50cnVzdGVkIGNvbW1lbnQ=")
    return tmp


class AssetNameAlignment(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = fake_root(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def manifest_names(self):
        """생성기 ①을 돌려 latest.json 의 darwin url 파일명을 읽는다."""
        p = subprocess.run(["sh", os.path.join(self.root, "scripts", "make-update-manifest.sh"),
                            VERSION, "oogisoogi", "cys-ro"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, f"매니페스트 생성 실패: {p.stderr}")
        with open(os.path.join(self.root, "dist-update", "latest.json"), encoding="utf-8") as fh:
            platforms = json.load(fh)["platforms"]
        return {k: os.path.basename(platforms[k]["url"]) for k, _t, _a in LEGS}

    def tarball_name(self, arch):
        """생성기 ②를 돌려 실제로 만들어진 tar 파일명을 읽는다."""
        app = os.path.join(self.root, "staging-%s" % arch, "cysr.app")
        os.makedirs(os.path.join(app, "Contents"), exist_ok=True)
        put_macho_bundle(app, arch)
        with open(os.path.join(app, "Contents", "Info.plist"), "w", encoding="utf-8") as fh:
            fh.write("<plist/>")
        out = os.path.join(self.root, "out-%s" % arch)
        os.makedirs(out, exist_ok=True)
        env = dict(os.environ)
        env.pop("TAURI_SIGNING_PRIVATE_KEY", None)      # 서명 없이 tar 까지만(rc 3)
        p = subprocess.run(["sh", os.path.join(self.root, "scripts", "make-darwin-updater-tarball.sh"),
                            "--app", app, "--out", out, "--arch", arch],
                           capture_output=True, text=True, env=env)
        self.assertIn(p.returncode, (0, 3), f"tarball 생성 실패({p.returncode}): {p.stderr}")
        made = [n for n in os.listdir(out) if n.endswith(".app.tar.gz")]
        self.assertEqual(len(made), 1, f"tar 산출이 하나가 아니다: {made}")
        return made[0]

    def test_two_generators_agree_on_the_asset_name(self):
        named = self.manifest_names()
        for key, _triple, arch in LEGS:
            self.assertEqual(
                named[key], self.tarball_name(arch),
                f"{key}: 매니페스트가 적는 이름과 생성기가 만드는 이름이 갈렸다 "
                f"— latest.json 의 url 이 발행되지 않는 자산을 가리킨다")

    def test_that_name_is_the_one_the_release_lane_publishes(self):
        """이름 정렬의 **기준점**은 발행 레인이다 — 둘이 합의해도 레인 밖이면 404 다."""
        lane = {n.format(v=VERSION) for n in rp.MAC_LANE}
        for key, _triple, _arch in LEGS:
            self.assertIn(self.manifest_names()[key], lane,
                          f"{key}: 발행 레인(MAC_LANE)에 없는 이름이다")

    def test_harness_did_not_touch_the_repository(self):
        """하네스는 제 tmp 루트에서만 돈다 — 저장소 dist-update 를 만들지 않는다."""
        before = os.path.exists(os.path.join(ROOT, "dist-update"))
        self.manifest_names()
        self.assertEqual(before, os.path.exists(os.path.join(ROOT, "dist-update")),
                         "저장소에 dist-update 가 생겼다 — 하네스가 작업 트리를 건드렸다")


if __name__ == "__main__":
    unittest.main()
