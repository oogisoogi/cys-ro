"""release-verify.py 의 밀폐 unittest — 네트워크·토큰·실자산 불요, 합성 픽스처만 사용.

★왜 이 테스트가 필요한가
  `scripts/release-verify.py` 는 **비가역 공개 발행 직전의 마지막 fail-closed 관문**이다
  (`release-publish.yml` 이 이걸로 죽으면 `gh release edit --draft=false` 가 실행되지 않는다).
  그런데 이 관문의 검사들은 **손으로 돌린 결함주입**으로만 실증돼 있었다 — 회귀 자산이 0이었다.
  실제로 2026-08-18 적대적 리뷰에서 fail-open 2건(플랫폼 키 집합 무단언 · 키→자산 결속 무단언)이
  발견됐다. 그 2건을 포함해 **"통과해선 안 될 입력"을 여기 전부 못박는다.**

★설계
  픽스처는 실물 13종의 **구조만** 축소 재현한다(수 KB). 실물 대조는 별도다 —
  `python3 scripts/release-verify.py --version 0.14.19 --release-dir ~/cys-release-backup/v0.14.19-assets`.
  각 테스트는 정상 픽스처를 만든 뒤 **한 곳만** 망가뜨리고, 그 사유가 나오는지 본다.
  경로는 전부 tempfile — 개인 경로·실 홈 디렉터리 금지(시크릿 스캔 계약, test_verify_win_crt.py 관례).

사용: python3 scripts/tests/test_release_verify.py
"""

import base64
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import re
import tempfile
import time
import unittest
import zipfile

# ★하이픈 파일명(`release-verify.py`)은 `import` 문으로 못 부른다. 형제 테스트들이 쓰는
#   `sys.path.insert` + `import <모듈>` 관례를 쓸 수 없어 importlib 로 파일을 직접 적재한다.
#   (파일명을 바꾸는 쪽이 아니라 테스트가 맞추는 이유: 하이픈 명명은 scripts/ 의 다수파이고
#    워크플로가 그 경로를 문자열로 부른다 — 이름을 바꾸면 발행 레인이 끊긴다.)
_RV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "release-verify.py")
_spec = importlib.util.spec_from_file_location("release_verify", _RV_PATH)
rv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rv)

V = "0.14.19"
# ★검증기 상수에서 **유도**한다(2026-09-09). 종전엔 벤더 URL 을 테스트가 따로 적어 뒀는데,
#   그래서 검증기 쪽 배포 원본이 벤더로 남아 있는 동안에도 이 테스트는 초록이었다 — 포크 전환
#   차단(F1)을 회귀 자산이 하나도 못 잡은 이유다. 이름을 참조해 그 괴리 자체를 없앤다.
BASE = "https://github.com/%s/releases/download/v%s/" % (rv.RELEASE_REPO, V)


class AssetNamesFollowProductName(unittest.TestCase):
    """★자산 이름 = tauri.conf productName 파생 (cysr-product-rename · 2026-09-16).

    tauri 번들러는 설치 파일·dmg·업데이터 tar 이름을 productName 으로 만든다. 검증기·후처리는
    그 이름을 문자열로 들고 있으므로, productName 을 바꾸고 이 표를 안 바꾸면 발행이 「자산 부재」로
    죽고(반대면 옛 이름을 통과시킨다). 표를 설정에서 읽어 오지 않고 **대조**로 묶는 이유:
    검증기는 저장소 없이도 단독으로 돌아야 한다(scripts/release-verify.py 머리말).
    """

    def setUp(self):
        conf = os.path.join(os.path.dirname(_RV_PATH), "..", "src-tauri", "tauri.conf.json")
        with open(conf, encoding="utf-8") as fh:
            self.product = json.load(fh)["productName"]
        rp_path = os.path.join(os.path.dirname(_RV_PATH), "release-postprocess.py")
        spec = importlib.util.spec_from_file_location("release_postprocess_names", rp_path)
        self.rp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.rp)

    def test_every_asset_name_starts_with_product_name(self):
        prefix = self.product + "_"
        names = (list(rv.REQUIRED_ASSETS) + list(rv.MAC_ASSETS)
                 + list(rv.REQUIRED_PLATFORMS.values()) + list(rv.MAC_PLATFORMS.values())
                 + list(self.rp.MAC_LANE))
        product_assets = [n for n in names if not n.startswith(("latest", "pack"))]
        self.assertGreaterEqual(len(product_assets), 12, product_assets)
        wrong = [n for n in product_assets if not n.startswith(prefix)]
        self.assertEqual(wrong, [], "productName=%r 인데 자산 이름이 다르다" % self.product)
# ★8단계(팩 replay 단조 · 2026-09-12) 픽스처 — 우리 팩이 벤더 latest 보다 **1초** 새로 서명된
#   최소 통과 형태. 1초 차이로 둬야 `<=` → `<` 완화 같은 경계 회귀가 test_61 에서 드러난다.
#   ★r2: 타당 범위(now-90일..now+300초)가 생겨 고정 시각은 90일 뒤 스스로 적색이 된다 — 실행 시각 기준.
FIXTURE_SIGNED_AT = int(time.time()) - 3600
VENDOR = {"pack_version": "0.14.33", "signed_at": FIXTURE_SIGNED_AT - 1}
# ★9단계(판번 증가 · cysr 1.0.0) 픽스처 — 픽스처 판(V)이 직전 공개판보다 **높은** 최소 통과 형태.
BID = "0123456789ab.20260915T1030Z"
PREV = {"version": "0.14.18", "build_id": "fedcba987654.20260801T0000Z"}


# ★7-b(키 브리지 게이트 · 2026-09-15) 픽스처 키 id — 직전 판 바이너리 pubkey 의 key id 역할.
FIXTURE_KEY_ID = "0123456789ABCDEF"
OTHER_KEY_ID = "FEDCBA9876543210"
# ★8-a(팩 서명 키 게이트 · 2026-09-16) 픽스처 — 팩 매니페스트 서명 키와 직전 판 팩 키링.
FIXTURE_PACK_KEY_ID = "1122334455667788"
PACK_KEYRING = ({FIXTURE_PACK_KEY_ID: 4102444800}, set())      # not_after = 2100-01-01
# 실물 대조용 — 현행 배포 키의 tauri.conf.json updater.pubkey(공개값). key id = 54FBA04AD0E0F49D.
REAL_TAURI_PUBKEY = ("dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IDU0RkJBMDRBRDBFMEY0OUQKUldTZDlPRFFT"
                     "cUQ3VkQ5M284TVJWMUd6ZnBLbHcwTFFMeHlqazBiZUt2MWNWUklmd0RuVGxKaDAK")


def _sig_text(tag, key_id=FIXTURE_KEY_ID):
    """tauri updater 서명 형식 재현 — minisign 서명 텍스트(4줄)를 base64 로 감싼 한 줄.

    본문 줄 = b"ED" + keynum(리틀엔디언 8B) + 서명 64B. 서명 바이트는 tag 에서 유도해 자산마다 다르다
    (암호적으로 유효하진 않다 — 검증기는 key id 까지만 본다).
    """
    keynum = bytes.fromhex(key_id)[::-1]
    sig = hashlib.sha512(tag.encode()).digest()
    body = ("untrusted comment: signature from tauri secret key\n%s\n"
            "trusted comment: timestamp:0\tfile:%s\n%s\n"
            % (base64.b64encode(b"ED" + keynum + sig).decode(), tag,
               base64.b64encode(sig).decode()))
    return base64.b64encode(body.encode()).decode()


def _minisig_text(tag, key_id=FIXTURE_PACK_KEY_ID):
    """표준 minisign 서명 텍스트(.minisig) — tauri .sig 를 base64 로 푼 형태와 같다."""
    return base64.b64decode(_sig_text(tag, key_id)).decode()


def _keyring_json(key_ids, revoked=(), not_after="2100-01-01T00:00:00Z"):
    """cysjavis-pack/trusted-keys.json 형식 — 공개키는 key id 를 파생하도록 합성한다."""
    return {"keys": [{"key_id": k, "pubkey": _tauri_pub(k), "not_after": not_after, "comment": "fixture"}
                     for k in key_ids],
            "revoked_key_ids": list(revoked)}


def _tauri_pub(key_id):
    """tauri 표기 공개키(전체 .pub 텍스트 base64) — 본문 = b"Ed" + keynum + 32B."""
    line = base64.b64encode(b"Ed" + bytes.fromhex(key_id)[::-1] + b"\x07" * 32).decode()
    text = "untrusted comment: minisign public key: %s\n%s\n" % (key_id, line)
    return base64.b64encode(text.encode()).decode()


def _dmg_bytes(payload):
    """UDIF dmg 재현 — 머리는 zlib(78 01), **끝 512B 가 'koly' 트레일러**."""
    return b"\x78\x01" + payload + b"koly" + b"\x00" * 508


def write_sums(root):
    """디렉터리 실물에서 SHA256SUMS.txt 를 다시 만든다(자기 자신 제외)."""
    rows = []
    for name in sorted(os.listdir(root)):
        if name == rv.SUMS_NAME:
            continue
        path = os.path.join(root, name)
        if not os.path.isfile(path) or os.path.islink(path):
            continue
        rows.append("%s  %s" % (rv.sha256_file(path), name))
    with open(os.path.join(root, rv.SUMS_NAME), "w", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")


def build_fixture(root, mac=True):
    """정상 통과하는 묶음을 합성한다(실물 v0.14.19 의 구조를 축소 재현).

    mac=True  → 13종(맥 포함) · mac=False → 8종(윈도우 단독 — 2026-09-09 발효 형태).
    ★한 함수가 두 형태를 다 내는 이유: 픽스처가 갈리면 「윈도우 단독만 통과하고 맥 포함은
      깨지는」 회귀를 아무도 못 잡는다. 분기 지점을 한 곳으로 모아 둔다.
    """
    exe_bytes = b"MZ\x90\x00" + b"windows-nsis-installer-payload" * 8

    def w(name, data):
        with open(os.path.join(root, name), "wb") as fh:
            fh.write(data)

    if mac:
        w("cysr_%s_aarch64.dmg" % V, _dmg_bytes(b"macos-arm-disk-image" * 16))
        w("cysr_%s_x64.dmg" % V, _dmg_bytes(b"macos-intel-disk-image" * 16))
        w("cysr_aarch64.app.tar.gz", gzip.compress(b"macos-arm-app-bundle" * 32))
        w("cysr_x64.app.tar.gz", gzip.compress(b"macos-intel-app-bundle" * 32))
    w("cysr_%s_x64-setup.exe" % V, exe_bytes)
    w("pack.tar.gz", gzip.compress(b"cysjavis-pack-payload" * 32))
    w("pack-manifest.json", json.dumps({"files": [], "expires_at": "2027-01-01T00:00:00Z",
                                        "signed_at": FIXTURE_SIGNED_AT,
                                        "key_id": FIXTURE_PACK_KEY_ID}).encode())
    w("pack-manifest.json.minisig", _minisig_text("pack").encode())

    # zip 은 setup.exe **한 개**만, 바이트 동일하게 품어야 한다.
    with zipfile.ZipFile(os.path.join(root, "cysr_%s_x64-setup.zip" % V), "w") as z:
        z.writestr("cysr_%s_x64-setup.exe" % V, exe_bytes)

    sigs = {"cysr_%s_x64-setup.exe.sig" % V: _sig_text("win")}
    if mac:
        sigs["cysr_aarch64.app.tar.gz.sig"] = _sig_text("arm")
        sigs["cysr_x64.app.tar.gz.sig"] = _sig_text("intel")
    for name, text in sigs.items():
        w(name, (text + "\n").encode())

    expected = dict(rv.REQUIRED_PLATFORMS)
    if mac:
        expected.update(rv.MAC_PLATFORMS)
    platforms = {}
    for key, asset_tpl in expected.items():
        asset = asset_tpl.format(v=V)
        platforms[key] = {"signature": sigs[asset + ".sig"], "url": BASE + asset}
    w("latest.json", json.dumps({
        "version": V,
        "notes": "cys %s — 릴리스 안내" % V,
        "pub_date": "2026-08-17T14:36:35Z",
        "platforms": platforms,
        "build_id": BID,
    }, ensure_ascii=False).encode())

    write_sums(root)
    return root


class ReleaseVerifyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = build_fixture(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # ── 헬퍼 ──────────────────────────────────────────────────────────────
    def p(self, name):
        return os.path.join(self.root, name)

    def load_latest(self):
        return json.load(open(self.p("latest.json"), encoding="utf-8"))

    def save_latest(self, obj):
        with open(self.p("latest.json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False)

    def assert_pass(self):
        assets, platforms, mac_included = rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        return assets, platforms, mac_included

    def assert_fail(self, needle):
        """비영 종료 사유에 needle 이 들어 있어야 한다 — '조용한 통과'를 막는 본체."""
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        self.assertIn(needle, str(cm.exception),
                      "예상 사유 %r 가 아니라 %r 로 죽었다" % (needle, str(cm.exception)))
        return str(cm.exception)

    # ── 0. 기준선 ─────────────────────────────────────────────────────────
    def test_00_baseline_passes(self):
        assets, platforms, mac_included = self.assert_pass()
        self.assertEqual(len(assets), 13)
        self.assertEqual(platforms, sorted(rv.UPDATER_PLATFORMS))
        self.assertTrue(mac_included, "맥 13종 묶음인데 맥 미포함으로 판정됐다")

    # ── 1. 완전성(디렉터리 ↔ SUMS 양방향) ─────────────────────────────────
    def test_01_asset_missing_from_dir(self):
        os.remove(self.p("cysr_%s_x64.dmg" % V))
        self.assert_fail("자산 누락")

    def test_02_unlisted_stowaway(self):
        open(self.p("stowaway.bin"), "wb").write(b"not-in-sums")
        self.assert_fail("SUMS 에 없는 자산이 섞여 있다")

    def test_03_symlink_rejected(self):
        os.symlink(self.p("pack.tar.gz"), self.p("linked.tar.gz"))
        self.assert_fail("일반 파일이 아닌 항목")

    def test_04_asset_and_sums_row_both_removed(self):
        """대조만으로는 절대 못 잡는 케이스 — 독립 하한선이 유일한 포획 지점.

        ★윈도우 자산으로 찌른다(2026-09-09 개정). 종전엔 DMG 를 지웠는데, DMG 는 이제
        `MAC_ASSETS` 로 갈라져 '맥 레인 반쪽' 이 잡는다(그 경로는 test_04b 가 따로 박제).
        """
        os.remove(self.p("pack.tar.gz"))
        write_sums(self.root)
        self.assert_fail("배포 필수 자산 누락")

    def test_04b_mac_lane_half_removed(self):
        """★맥 레인 전부-또는-전무 — DMG 한 짝만 사라진 묶음은 통과해선 안 된다."""
        os.remove(self.p("cysr_%s_aarch64.dmg" % V))
        write_sums(self.root)
        self.assert_fail("맥 레인이 반쪽이다")

    # ── 2. 체크섬·SUMS 형식 ───────────────────────────────────────────────
    def test_05_checksum_mismatch_on_byte_flip(self):
        raw = bytearray(open(self.p("pack.tar.gz"), "rb").read())
        raw[-1] ^= 0xFF                      # gzip CRC 꼬리를 흔든다
        open(self.p("pack.tar.gz"), "wb").write(bytes(raw))
        self.assert_fail("pack.tar.gz")      # 지문 또는 체크섬 — 어느 쪽이든 죽어야 한다

    def test_06_sums_digest_tampered(self):
        text = open(self.p(rv.SUMS_NAME), encoding="utf-8").read()
        first = text.splitlines()[0]
        flipped = ("b" if first[0] != "b" else "c") + first[1:]
        open(self.p(rv.SUMS_NAME), "w", encoding="utf-8").write(text.replace(first, flipped))
        self.assert_fail("체크섬 불일치")

    def test_07_sums_malformed_row(self):
        with open(self.p(rv.SUMS_NAME), "a", encoding="utf-8") as fh:
            fh.write("deadbeef  ../escape.bin\n")
        self.assert_fail("형식 오류")

    def test_08_sums_lists_itself(self):
        with open(self.p(rv.SUMS_NAME), "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % ("0" * 64, rv.SUMS_NAME))
        self.assert_fail("자기 제외 규약 위반")

    # ── 3. 버전 토큰 ──────────────────────────────────────────────────────
    def test_09_version_token_mismatch(self):
        """구버전 자산이 섞여 든 묶음. ★REQUIRED_ASSETS 8종이 아닌 자산으로 찔러야
        3단계까지 도달한다 — 8종 중 하나면 2단계(배포 필수 자산 누락)가 먼저 잡는다."""
        stale = "cysr_0.14.18_x64-setup.exe.sig"
        os.rename(self.p("cysr_%s_x64-setup.exe.sig" % V), self.p(stale))
        write_sums(self.root)
        self.assert_fail("파일명 버전 토큰 불일치")

    def test_09b_required_asset_wins_over_token_check(self):
        """같은 사고라도 필수 자산이면 2단계가 먼저 잡는다 — 사유 순서를 못박는다."""
        os.rename(self.p("cysr_%s_x64-setup.zip" % V), self.p("cysr_0.14.18_x64-setup.zip"))
        write_sums(self.root)
        self.assert_fail("배포 필수 자산 누락")

    def test_09c_stale_dmg_name_caught_as_half_lane(self):
        """구버전 토큰이 박힌 DMG = 그 버전의 맥 레인은 반쪽이다 — 2-b 가 잡는다."""
        os.rename(self.p("cysr_%s_x64.dmg" % V), self.p("cysr_0.14.18_x64.dmg"))
        write_sums(self.root)
        self.assert_fail("맥 레인이 반쪽이다")

    # ── 4. 컨테이너 지문(ASSET_SHAPES) ────────────────────────────────────
    #    ★SUMS 를 쓰레기에 맞춰 재생성해도 통과해선 안 된다.
    def test_10_zero_byte_asset(self):
        open(self.p("cysr_%s_aarch64.dmg" % V), "wb").close()
        write_sums(self.root)
        self.assert_fail("0바이트")

    def test_11_dmg_without_koly_trailer(self):
        open(self.p("cysr_%s_x64.dmg" % V), "wb").write(b"\x78\x01" + b"J" * 4096)
        write_sums(self.root)
        self.assert_fail("koly")

    def test_12_targz_is_junk(self):
        open(self.p("pack.tar.gz"), "wb").write(b"not a tarball")
        write_sums(self.root)
        self.assert_fail("gzip 매직이 아니다")

    def test_13_targz_truncated_midstream(self):
        """머리 매직은 멀쩡한데 중간에서 잘린 tar.gz — 끝까지 풀어야만 잡힌다."""
        raw = open(self.p("cysr_aarch64.app.tar.gz"), "rb").read()
        open(self.p("cysr_aarch64.app.tar.gz"), "wb").write(raw[: len(raw) // 2])
        write_sums(self.root)
        self.assert_fail("gzip 스트림이 끝까지 풀리지 않는다")

    def test_14_exe_not_pe(self):
        open(self.p("cysr_%s_x64-setup.exe" % V), "wb").write(b"#!/bin/sh\necho pwned\n")
        write_sums(self.root)
        self.assert_fail("컨테이너 지문 불일치")

    def test_15_sig_not_base64(self):
        open(self.p("cysr_x64.app.tar.gz.sig"), "wb").write(b"!!! not base64 !!!")
        latest = self.load_latest()
        for key in ("darwin-x86_64", "darwin-x86_64-app"):
            latest["platforms"][key]["signature"] = "!!! not base64 !!!"
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("base64 가 아니다")

    def test_16_json_asset_not_parseable(self):
        open(self.p("pack-manifest.json"), "wb").write(b"{ broken json,,,")
        write_sums(self.root)
        self.assert_fail("JSON 자산이 파싱되지 않는다")

    def test_17_unknown_extension_rejected(self):
        """배포 구성이 몰래 늘어나는 걸 막는다 — 사람이 상수를 고쳐야 통과한다."""
        open(self.p("cysr_%s_x64.msi" % V), "wb").write(b"\xd0\xcf\x11\xe0msi")
        write_sums(self.root)
        self.assert_fail("확장자 규칙에 없는 자산")

    # ── 5. Windows zip ↔ exe ──────────────────────────────────────────────
    def test_18_zip_holds_different_bytes(self):
        with zipfile.ZipFile(self.p("cysr_%s_x64-setup.zip" % V), "w") as z:
            z.writestr("cysr_%s_x64-setup.exe" % V, b"MZ\x90\x00different-installer")
        write_sums(self.root)
        self.assert_fail("바이트 동일하지 않다")

    def test_19_zip_holds_extra_member(self):
        exe = "cysr_%s_x64-setup.exe" % V
        with zipfile.ZipFile(self.p("cysr_%s_x64-setup.zip" % V), "w") as z:
            z.writestr(exe, open(self.p(exe), "rb").read())
            z.writestr("README.txt", b"stowaway")
        write_sums(self.root)
        self.assert_fail("하나만 있어야 한다")

    # ── 6. 업데이터(latest.json) — ①②③④ ──────────────────────────────────
    def test_20_top_level_field_set_notes_deleted(self):
        latest = self.load_latest()
        del latest["notes"]
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("최상위 필드 집합 오류")

    def test_21_top_level_field_set_junk_injected(self):
        latest = self.load_latest()
        latest["injected_junk"] = "x"
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("최상위 필드 집합 오류")

    def test_22_macos_updater_lane_removed_but_dmg_kept(self):
        """★fail-open 반증 케이스 1 — 초판이 exit 0 으로 통과시켰던 입력. 지금도 죽어야 한다.

        macOS 업데이터 4종만 지우고 **DMG 2종은 남긴다**. = 다운로드 버튼은 살아 있는데 앱 내
        Update 가 죽은 묶음. 2026-09-09 분할 뒤에도 이건 「맥 레인 반쪽」으로 즉사한다 —
        맥 레인을 통째로 뺀 윈도우 단독 배포(test_22b)와 **혼동되지 않는다는 것**이 요지다.
        """
        for name in ("cysr_aarch64.app.tar.gz", "cysr_aarch64.app.tar.gz.sig",
                     "cysr_x64.app.tar.gz", "cysr_x64.app.tar.gz.sig"):
            os.remove(self.p(name))
        latest = self.load_latest()
        latest["platforms"] = {k: v for k, v in latest["platforms"].items()
                               if k.startswith("windows-")}
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("맥 레인이 반쪽이다")

    def test_23_updater_rows_all_repointed_to_windows_exe(self):
        """★fail-open 반증 케이스 2 — 초판이 exit 0 으로 통과시켰던 입력.

        6행 전부를 Windows 설치본으로 덮는다. = macOS 업데이터가 NSIS exe 를 받는 묶음.
        """
        latest = self.load_latest()
        exe = "cysr_%s_x64-setup.exe" % V
        sig = open(self.p(exe + ".sig"), encoding="utf-8").read().strip()
        for key in latest["platforms"]:
            latest["platforms"][key] = {"signature": sig, "url": BASE + exe}
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("url 결속 위반")

    def test_24_single_row_repointed(self):
        latest = self.load_latest()
        latest["platforms"]["darwin-aarch64"]["url"] = BASE + "cysr_x64.app.tar.gz"
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("url 결속 위반")

    def test_25_updater_signature_mismatch(self):
        latest = self.load_latest()
        latest["platforms"]["darwin-aarch64"]["signature"] = _sig_text("forged")
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("업데이터 서명 불일치")

    def test_26_updater_sig_file_removed_everywhere(self):
        """`.sig` 는 REQUIRED_ASSETS 밖 — latest.json 교차대조만이 유일한 포획 지점.

        ★윈도우 서명으로 찌른다(2026-09-09 개정). 맥 서명은 이제 맥 레인 6종의 일부라
        2-b 가 **더 먼저·더 구체적인 사유**로 잡는다(그 경로는 test_26b 가 박제).
        윈도우 exe 서명에는 그런 상위 그물이 없으므로 이 테스트의 원래 취지가 여기 남는다.
        """
        os.remove(self.p("cysr_%s_x64-setup.exe.sig" % V))
        write_sums(self.root)
        self.assert_fail("서명 파일이 없다")

    def test_26b_mac_sig_removed_is_a_half_lane(self):
        """맥 서명 1종 증발 = 맥 레인 반쪽 — 사유가 더 구체적인 쪽으로 바뀐 것을 못박는다."""
        os.remove(self.p("cysr_aarch64.app.tar.gz.sig"))
        write_sums(self.root)
        self.assert_fail("맥 레인이 반쪽이다")

    def test_27_latest_json_version_mismatch(self):
        latest = self.load_latest()
        latest["version"] = "0.14.18"
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("version 불일치")

    def test_28_pub_date_without_timezone(self):
        latest = self.load_latest()
        latest["pub_date"] = "2026-08-17T14:36:35"
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("타임존이 없다")

    def test_29_updater_row_extra_field(self):
        latest = self.load_latest()
        latest["platforms"]["windows-x86_64"]["with_elevated_task"] = False
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("업데이터 행 필드 집합 오류")

    def test_30_notes_emptied(self):
        latest = self.load_latest()
        latest["notes"] = "   "
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("notes 가 비어 있거나")

    # ── 7. 껍데기 입력 ────────────────────────────────────────────────────
    def test_31_sums_absent(self):
        os.remove(self.p(rv.SUMS_NAME))
        self.assert_fail("%s 가 없다" % rv.SUMS_NAME)

    def test_32_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(rv.VerifyError) as cm:
                rv.verify(V, d, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
            self.assertIn("비어 있다", str(cm.exception))

    def test_33_missing_dir(self):
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, os.path.join(self.root, "no-such-dir"), VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        self.assertIn("릴리스 디렉터리가 없다", str(cm.exception))


class WindowsOnlyLaneTests(unittest.TestCase):
    """★2026-09-09 신설 — 「맥 서명 없이 윈도우 먼저」(박사님 09:05) 가 성립하는지, 그리고
    그 완화가 **딱 그 하나만** 열었는지 못박는다.

    분할이 진짜로 위험한 지점은 통과 케이스가 아니라 **반쪽 케이스**다. 그래서 이 클래스는
    윈도우 단독 통과 1건과, 그 통과 판정을 흉내 내려는 반쪽 입력 4건을 함께 둔다.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        build_fixture(self.root, mac=False)

    def tearDown(self):
        self._tmp.cleanup()

    def p(self, name):
        return os.path.join(self.root, name)

    def load_latest(self):
        return json.load(open(self.p("latest.json"), encoding="utf-8"))

    def save_latest(self, obj):
        with open(self.p("latest.json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False)

    def assert_fail(self, needle):
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        self.assertIn(needle, str(cm.exception),
                      "예상 사유 %r 가 아니라 %r 로 죽었다" % (needle, str(cm.exception)))

    def test_40_windows_only_passes_and_reports_mac_absent(self):
        """맥 자산 0종 + darwin 행 0 = 통과하되 **미포함으로 판정**돼야 한다."""
        assets, platforms, mac_included = rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        self.assertFalse(mac_included, "맥 미포함 묶음인데 포함으로 판정됐다")
        self.assertEqual(platforms, sorted(rv.REQUIRED_PLATFORMS))
        # 반환되는 `assets` 는 SUMS 등재분이다 — SHA256SUMS.txt 자신은 자기 제외 규약으로 빠진다.
        # 필수 6종 + 윈도우 exe 서명 1 = 7. (릴리스 자산 실물은 여기에 SUMS 를 더해 8종)
        self.assertEqual(len(assets), 7, "윈도우 단독 등재 자산이 7종이 아니다: %s" % assets)

    def test_41_windows_lane_still_required(self):
        """맥을 뺐다고 윈도우까지 물러지면 안 된다 — exe 가 없으면 여전히 즉사."""
        os.remove(self.p("cysr_%s_x64-setup.exe" % V))
        os.remove(self.p("cysr_%s_x64-setup.zip" % V))
        write_sums(self.root)
        self.assert_fail("배포 필수 자산 누락")

    def test_42_darwin_rows_without_mac_assets(self):
        """★latest.json 만 맥을 주장하는 묶음 — 맥 사용자가 없는 파일을 받으러 간다."""
        latest = self.load_latest()
        exe = "cysr_%s_x64-setup.exe" % V
        sig = open(self.p(exe + ".sig"), encoding="utf-8").read().strip()
        for key, tpl in rv.MAC_PLATFORMS.items():
            latest["platforms"][key] = {"signature": sig, "url": BASE + tpl.format(v=V)}
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("platforms 키 집합 오류")

    def test_43_dmg_smuggled_in_without_updater_lane(self):
        """★DMG 만 슬쩍 낀 묶음 — 다운로드는 되는데 앱 내 Update 는 죽는다. 반쪽이다."""
        with open(self.p("cysr_%s_aarch64.dmg" % V), "wb") as fh:
            fh.write(_dmg_bytes(b"macos-arm-disk-image" * 16))
        write_sums(self.root)
        self.assert_fail("맥 레인이 반쪽이다")

    def test_44_windows_platform_row_dropped(self):
        """윈도우 단독인데 윈도우 행이 줄면 = 아무도 못 받는 묶음."""
        latest = self.load_latest()
        del latest["platforms"]["windows-x86_64-nsis"]
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("platforms 키 집합 오류")

    def test_45_windows_row_repointed(self):
        """결속(③)은 맥 유무와 무관하게 계속 산다."""
        latest = self.load_latest()
        latest["platforms"]["windows-x86_64"]["url"] = BASE + "pack.tar.gz"
        self.save_latest(latest)
        write_sums(self.root)
        self.assert_fail("url 결속 위반")


class ReleaseRepoBindingTests(unittest.TestCase):
    """★2026-09-09 신설 — url 결속의 기준 레포가 **우리 포크**인지, 그리고 그것이 바뀌면
    실제로 판정이 달라지는지(= 상수가 살아 있는 검사인지) 못박는다.

    F1 이 오래 살아남은 이유가 정확히 이것이다: 검증기는 벤더 URL 을 보고 있었는데 테스트는
    같은 벤더 URL 을 따로 적어 뒀다. 두 벌이 사이좋게 틀려서 아무도 못 잡았다.
    """

    def test_50_default_repo_is_our_fork(self):
        self.assertEqual(rv.RELEASE_REPO, "oogisoogi/cys-ro",
                         "배포 원본이 우리 포크가 아니다 — tauri.conf endpoints·release.yml "
                         "SRC_REPO 와 같은 레포여야 한다")

    def test_51_vendor_urls_now_rejected(self):
        """벤더 URL 로 만든 묶음은 (같은 검증기에서) 결속 위반으로 죽어야 한다."""
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d, mac=False)
            latest = json.load(open(os.path.join(d, "latest.json"), encoding="utf-8"))
            vendor = "https://github.com/idoforgod/cys-terminal/releases/download/v%s/" % V
            for key in latest["platforms"]:
                latest["platforms"][key]["url"] = vendor + "cysr_%s_x64-setup.exe" % V
            with open(os.path.join(d, "latest.json"), "w", encoding="utf-8") as fh:
                json.dump(latest, fh, ensure_ascii=False)
            write_sums(d)
            with self.assertRaises(rv.VerifyError) as cm:
                rv.verify(V, d, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
            self.assertIn("url 결속 위반", str(cm.exception))

    def test_52_repo_override_changes_the_verdict(self):
        """--repo 는 장식이 아니다 — 넘긴 값으로 실제 판정이 바뀌어야 한다."""
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d, mac=False)
            latest = json.load(open(os.path.join(d, "latest.json"), encoding="utf-8"))
            other = "https://github.com/someone/cys-mirror/releases/download/v%s/" % V
            for key in latest["platforms"]:
                latest["platforms"][key]["url"] = other + "cysr_%s_x64-setup.exe" % V
            with open(os.path.join(d, "latest.json"), "w", encoding="utf-8") as fh:
                json.dump(latest, fh, ensure_ascii=False)
            write_sums(d)
            with self.assertRaises(rv.VerifyError):
                rv.verify(V, d, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)                                   # 기본(우리 포크)으로는 실패
            _, _, mac = rv.verify(V, d, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING, repo="someone/cys-mirror")  # 지목하면 통과
            self.assertFalse(mac)


class PackReplayMonotonicTests(unittest.TestCase):
    """★2026-09-12 신설(TICKET=cys-v01436-pack-url) — 8단계 팩 replay 단조.

    지키는 계약: 우리 pack-manifest.json signed_at > 벤더 latest signed_at. 같거나 작으면 벤더 팩을
    받은 기계(`~/.cys/.pack-accepted.json` 기준선 보유)가 우리 팩을 replay 로 영구 거부한다
    (`src/packsig.rs` ⓔ 는 `<=` 를 거부한다). 그리고 이 검사는 **건너뛸 수 없어야** 한다.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        build_fixture(self.root, mac=False)

    def tearDown(self):
        self._tmp.cleanup()

    def rewrite_ours(self, **fields):
        path = os.path.join(self.root, "pack-manifest.json")
        obj = json.load(open(path, encoding="utf-8"))
        for k, v in fields.items():
            if v is KeyError:
                obj.pop(k, None)
            else:
                obj[k] = v
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        write_sums(self.root)

    def assert_fail(self, vendor, needle):
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, vendor, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        self.assertIn(needle, str(cm.exception),
                      "예상 사유 %r 가 아니라 %r 로 죽었다" % (needle, str(cm.exception)))

    def test_60_ours_newer_passes(self):
        rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        files = rv.collect_files(self.root)
        self.assertEqual(rv.check_pack_replay_monotonic(files, VENDOR),
                         (FIXTURE_SIGNED_AT, FIXTURE_SIGNED_AT - 1))

    def test_61_equal_signed_at_rejected(self):
        """★경계 — 같은 초도 거부다(수용 측이 `<=` 를 거부하므로 발행 측도 엄격 부등호)."""
        self.assert_fail({"signed_at": FIXTURE_SIGNED_AT}, "팩 replay 단조 위반")

    def test_62_vendor_newer_rejected(self):
        # ★벤더가 더 늦게 서명했지만 타당 범위(now+300초) 안 — 범위 검사가 아니라 단조 검사가 죽여야 한다.
        #   (r2 R4 이후 +1일 값은 범위 밖으로 먼저 죽어 이 축을 재지 못했다 — 대조군 적색으로 실측)
        self.assert_fail({"signed_at": FIXTURE_SIGNED_AT + 60}, "팩 replay 단조 위반")

    def test_63_ours_signed_at_missing(self):
        self.rewrite_ours(signed_at=KeyError)
        self.assert_fail(VENDOR, "pack-manifest.json 의 signed_at 이 정수가 아니다")

    def test_64_ours_signed_at_not_exact_int(self):
        """bool 은 int 하위형이라 isinstance 로는 통과한다 — 정확 타입으로 막는다."""
        for bad in (True, str(FIXTURE_SIGNED_AT), float(FIXTURE_SIGNED_AT)):
            with self.subTest(bad=bad):
                self.rewrite_ours(signed_at=bad)
                self.assert_fail(VENDOR, "pack-manifest.json 의 signed_at 이 정수가 아니다")

    def test_65_vendor_manifest_malformed(self):
        self.assert_fail({}, "벤더 latest 팩 매니페스트 의 signed_at 이 정수가 아니다")
        self.assert_fail([], "벤더 latest 팩 매니페스트 가 JSON 객체가 아니다")
        self.assert_fail(None, "벤더 latest 팩 매니페스트 가 JSON 객체가 아니다")

    def test_66_vendor_manifest_is_not_optional(self):
        """★건너뛰는 선택지가 없어야 한다 — 기본값을 붙이는 순간 호출부가 조용히 생략할 수 있다."""
        import inspect
        param = inspect.signature(rv.verify).parameters["vendor_manifest"]
        self.assertIs(param.default, inspect.Parameter.empty,
                      "verify() 의 vendor_manifest 에 기본값이 생겼다 — 8단계를 생략할 수 있게 된다")

    def test_67_vendor_fetch_failure_is_failure(self):
        """네트워크 불가 = 통과가 아니라 실패(명시 사유)."""
        from unittest import mock
        with mock.patch.object(rv.urllib.request, "urlopen", side_effect=OSError("offline")):
            with self.assertRaises(rv.VerifyError) as cm:
                rv.load_vendor_manifest()
        self.assertIn("벤더 팩 매니페스트 조회 불가", str(cm.exception))
        self.assertIn(rv.VENDOR_PACK_MANIFEST_URL, str(cm.exception))

    def test_68_vendor_file_not_json(self):
        path = os.path.join(self.root, "..", os.path.basename(self.root) + "-vendor.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("<html>not json</html>")
        try:
            with self.assertRaises(rv.VerifyError) as cm:
                rv.load_vendor_manifest(path=path)
            self.assertIn("벤더 팩 매니페스트가 JSON 이 아니다", str(cm.exception))
        finally:
            os.remove(path)

    def test_69_vendor_url_is_vendor_not_our_fork(self):
        """비교 기준이 우리 레포를 가리키면 자기 자신과 비교하는 검사가 된다."""
        self.assertIn("/idoforgod/cys-terminal/", rv.VENDOR_PACK_MANIFEST_URL)
        self.assertNotIn(rv.RELEASE_REPO, rv.VENDOR_PACK_MANIFEST_URL)
        self.assertTrue(rv.VENDOR_PACK_MANIFEST_URL.endswith("/releases/latest/download/pack-manifest.json"))


class SignedAtPlausibilityTests(unittest.TestCase):
    """★r2 R4 · r3 S1 — signed_at 타당 범위: 우리 `now-90일 ≤ signed_at ≤ now+300초` · 벤더 `≤ now+300초`(과거 하한 없음).

    각 음성 케이스는 **단조 조건은 만족**하게 골랐다(우리 > 벤더) — 타당 범위 검사를 지우면
    통과해 버리도록. 그래야 이 검사가 살아 있는지를 잰다.
    """

    NOW = 1_800_000_000
    AGE = 90 * 86400

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "pack-manifest.json")

    def tearDown(self):
        self._tmp.cleanup()

    def check(self, ours, vendor):
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"signed_at": ours}, fh)
        return rv.check_pack_replay_monotonic({"pack-manifest.json": self.path},
                                              {"signed_at": vendor}, now=self.NOW)

    def assert_fail(self, ours, vendor, needle):
        with self.assertRaises(rv.VerifyError) as cm:
            self.check(ours, vendor)
        self.assertIn(needle, str(cm.exception),
                      "예상 사유 %r 가 아니라 %r 로 죽었다" % (needle, str(cm.exception)))

    def test_70_window_constants(self):
        self.assertEqual(rv.SIGNED_AT_MAX_AGE_SEC, 90 * 86400)
        self.assertEqual(rv.SIGNED_AT_MAX_FUTURE_SEC, 300)

    def test_71_future_skew_boundary_passes(self):
        self.assertEqual(self.check(self.NOW + 300, self.NOW), (self.NOW + 300, self.NOW))

    def test_72_ours_beyond_future_skew(self):
        self.assert_fail(self.NOW + 301, self.NOW, "pack-manifest.json 의 signed_at 이 타당 범위 밖")

    def test_73_age_boundary_passes(self):
        self.check(self.NOW - self.AGE + 1, self.NOW - self.AGE)

    def test_74_ours_too_old(self):
        self.assert_fail(self.NOW - self.AGE - 1, self.NOW - self.AGE - 2,
                         "pack-manifest.json 의 signed_at 이 타당 범위 밖")

    def test_75_vendor_future_signature(self):
        """벤더가 미래 시각으로 서명했으면 그걸 기준으로 삼지 않는다(실패로 사람에게 올린다)."""
        self.assert_fail(self.NOW + 300, self.NOW + 301,
                         "벤더 latest 팩 매니페스트 의 signed_at 이 타당 범위 밖")

    def test_76_vendor_old_signature_still_a_valid_baseline(self):
        """★r3 S1 — 벤더가 100일 발행을 멈췄어도 그 옛 signed_at 은 안전한 비교 기준이다(가용성).
        과거 90일 하한은 **우리 산출물에만** 적용한다 — 벤더 휴면이 우리 발행을 막으면 안 된다."""
        old = self.NOW - 100 * 86400
        self.assertEqual(self.check(self.NOW, old), (self.NOW, old))

    def test_76b_ours_100_days_old_still_rejected(self):
        """같은 100일 전 값이 **우리** 매니페스트면 여전히 실패 — 하한 면제는 벤더 쪽 한정."""
        self.assert_fail(self.NOW - 100 * 86400, self.NOW - 101 * 86400,
                         "pack-manifest.json 의 signed_at 이 타당 범위 밖")

    def test_77_negative_signed_at(self):
        self.assert_fail(-1, -2, "pack-manifest.json 의 signed_at 이 타당 범위 밖")

    def test_78_verify_threads_now_into_step8(self):
        """verify() 가 now 를 8단계까지 전달하는가 — 픽스처(1시간 전 서명)를 91일 뒤 시각으로 재면 실패."""
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d, mac=False)
            with self.assertRaises(rv.VerifyError) as cm:
                rv.verify(V, d, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING, now=FIXTURE_SIGNED_AT + self.AGE + 10)
            self.assertIn("타당 범위 밖", str(cm.exception))


class PackOnlyLaneTests(unittest.TestCase):
    """★r2 R1 — 팩 전용 레인이 replay 단조 검사를 우회하지 못한다.

    ①진입점(`--pack-only`)이 같은 함수로 판정하고 종료코드로 막는가 ②`pack-release.yml` 이 그
    진입점을 **발행 단계 이전·서명 이후**에 조건 없이 부르는가(워크플로 문면 검체).
    """

    WF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                      ".github", "workflows", "pack-release.yml")

    def run_pack_only(self, manifest, vendor=VENDOR, extra=(), sig_key=FIXTURE_PACK_KEY_ID,
                      keyring=(FIXTURE_PACK_KEY_ID,)):
        with tempfile.TemporaryDirectory() as d:
            args = ["--pack-only"]
            if manifest is not None:
                if isinstance(manifest, dict):
                    manifest = dict({"key_id": FIXTURE_PACK_KEY_ID}, **manifest)
                mp = os.path.join(d, "pack-manifest.json")
                with open(mp, "w", encoding="utf-8") as fh:
                    json.dump(manifest, fh)
                args += ["--pack-manifest", mp]
                if sig_key is not None:
                    with open(mp + ".minisig", "w", encoding="utf-8") as fh:
                        fh.write(_minisig_text("pack-only", sig_key))
            if keyring is not None:
                kf = os.path.join(d, "prev-trusted-keys.json")
                with open(kf, "w", encoding="utf-8") as fh:
                    json.dump(_keyring_json(keyring), fh)
                args += ["--prev-pack-keyring", kf]
            if vendor is not None:
                vf = os.path.join(d, "vendor-pack-manifest.json")
                with open(vf, "w", encoding="utf-8") as fh:
                    json.dump(vendor, fh)
                args += ["--vendor-manifest-file", vf]
            return subprocess.run([sys.executable, os.path.abspath(_RV_PATH)] + args + list(extra),
                                  capture_output=True, text=True)

    def test_80_pack_only_pass(self):
        r = self.run_pack_only({"signed_at": FIXTURE_SIGNED_AT})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("팩 replay 단조 통과", r.stdout)

    def test_81_pack_only_violation_exit_1(self):
        r = self.run_pack_only({"signed_at": FIXTURE_SIGNED_AT}, vendor={"signed_at": FIXTURE_SIGNED_AT})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("팩 replay 단조 위반", r.stderr)

    def test_82_pack_only_requires_manifest(self):
        r = self.run_pack_only(None)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_83_pack_only_vendor_unreadable_exit_1(self):
        r = self.run_pack_only({"signed_at": FIXTURE_SIGNED_AT}, vendor=None,
                               extra=("--vendor-manifest-file", os.path.join(tempfile.gettempdir(),
                                                                             "no-such-vendor-pack.json")))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("벤더 팩 매니페스트 조회 불가", r.stderr)

    def test_84_pack_release_lane_runs_gate_between_sign_and_publish(self):
        with open(self.WF, encoding="utf-8") as fh:
            body = "\n".join(l for l in fh.read().splitlines() if not l.lstrip().startswith("#"))
        gate = body.find("scripts/release-verify.py --pack-only")
        sign = body.find("- name: Sign pack-manifest.json")
        publish = body.find("gh release create")
        self.assertNotEqual(gate, -1, "pack-release.yml 이 --pack-only 검사를 부르지 않는다(우회)")
        self.assertNotEqual(sign, -1, "서명 단계를 못 찾았다 — 워크플로 구조 변경 의심")
        self.assertNotEqual(publish, -1, "발행 명령을 못 찾았다 — 워크플로 구조 변경 의심")
        self.assertLess(sign, gate, "replay 검사가 서명 이전에 있다 — 최종 매니페스트를 재지 않는다")
        self.assertLess(gate, publish, "replay 검사가 발행 이후에 있다 — 막지 못한다")
        start = body.rfind("- name:", 0, gate)
        end = body.find("- name:", gate)
        step = body[start:end if end != -1 else len(body)]
        for bad in ("continue-on-error", "if:", "|| true", "--vendor-manifest-file"):
            self.assertNotIn(bad, step, "replay 검사 단계에 우회 여지 %r 가 있다" % bad)
        self.assertIn("--pack-manifest pack-manifest.json", step)


class ExitCodeContractTests(unittest.TestCase):
    """★워크플로 계약 — `set -euo pipefail` 아래에서 종료코드가 곧 fail-closed 다."""

    def run_cli(self, *args, vendor=VENDOR, key_id=FIXTURE_KEY_ID, prev=PREV,
                keyring=(FIXTURE_PACK_KEY_ID,)):
        """8·9단계 기준은 사본 파일로 넘긴다 — 테스트가 네트워크에 닿지 않게(None 이면 안 넘김).
        7-b 기준(key_id)도 기본으로 넘긴다(key_id=None 이면 안 넘김).
        ★9단계(cysr 1.0.0): prev 를 안 넘기면 CLI 가 실제 공개판 latest.json 을 받아 판정한다 —
          2026-09-15 실측: 공개판 0.14.36 > 픽스처 0.14.19 → 「판번 역행」 적색(fail-closed 확인)."""
        with tempfile.TemporaryDirectory() as vd:
            extra = []
            if vendor is not None:
                vf = os.path.join(vd, "vendor-pack-manifest.json")
                with open(vf, "w", encoding="utf-8") as fh:
                    json.dump(vendor, fh)
                extra = ["--vendor-manifest-file", vf]
            if key_id is not None:
                extra += ["--updater-key-id", key_id]
            if keyring is not None:
                kf = os.path.join(vd, "prev-trusted-keys.json")
                with open(kf, "w", encoding="utf-8") as fh:
                    json.dump(_keyring_json(keyring), fh)
                extra += ["--prev-pack-keyring", kf]
            if prev is not None:
                pf = os.path.join(vd, "previous-latest.json")
                with open(pf, "w", encoding="utf-8") as fh:
                    json.dump(prev, fh)
                extra += ["--previous-latest-file", pf]
            return subprocess.run([sys.executable, os.path.abspath(_RV_PATH)] + list(args) + extra,
                                  capture_output=True, text=True)

    def test_exit_1_when_vendor_manifest_unreadable(self):
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d)
            r = self.run_cli("--version", V, "--release-dir", d,
                             "--vendor-manifest-file", os.path.join(d, "no-such-vendor.json"),
                             vendor=None)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("벤더 팩 매니페스트 조회 불가", r.stderr)

    def test_exit_1_when_previous_latest_unreadable(self):
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d)
            r = self.run_cli("--version", V, "--release-dir", d,
                             "--previous-latest-file", os.path.join(d, "no-such-previous.json"),
                             prev=None)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("직전 공개판 latest.json 조회 불가", r.stderr)

    def test_exit_1_when_version_not_bumped(self):
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d)
            r = self.run_cli("--version", V, "--release-dir", d,
                             prev={"version": V, "build_id": "fedcba987654.20260801T0000Z"})
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("판번 미증가", r.stderr)

    def test_exit_1_when_replay_monotonic_violated(self):
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d)
            r = self.run_cli("--version", V, "--release-dir", d,
                             vendor={"signed_at": FIXTURE_SIGNED_AT})
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("팩 replay 단조 위반", r.stderr)

    def test_exit_0_on_pass(self):
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d)
            r = self.run_cli("--version", V, "--release-dir", d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("릴리스 검증 통과", r.stdout)

    def test_exit_1_on_failure_with_reason(self):
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d)
            os.remove(os.path.join(d, "latest.json"))
            r = self.run_cli("--version", V, "--release-dir", d)
            self.assertEqual(r.returncode, 1)
            self.assertIn("::error::", r.stderr)          # GitHub Actions 주석 형식
            self.assertIn("자산 누락", r.stderr)

    def test_exit_1_on_bad_version_arg(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli("--version", "v0.14.19", "--release-dir", d)
            self.assertEqual(r.returncode, 1)
            self.assertIn("X.Y.Z", r.stderr)

    def test_exit_2_on_missing_arg(self):
        r = self.run_cli("--version", V)
        self.assertEqual(r.returncode, 2)                 # argparse 사용법 오류

    def test_print_assets_lists_all_13(self):
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d)
            r = self.run_cli("--version", V, "--release-dir", d, "--print-assets")
            self.assertEqual(r.returncode, 0, r.stderr)
            listed = [ln for ln in r.stdout.splitlines() if not ln.startswith("✅")]
            self.assertEqual(len(listed), 13)
            self.assertIn("맥 자산 포함", r.stdout)

    def test_windows_only_exit_0_and_says_mac_absent(self):
        """★윈도우 단독 묶음의 CLI 계약 — 통과(0) + 「미포함」을 **말로 남긴다**.

        사람이 로그만 보고 「조용히 빠진 것」과 「의도해서 뺀 것」을 구분할 수 있어야 한다.
        """
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d, mac=False)
            r = self.run_cli("--version", V, "--release-dir", d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("릴리스 검증 통과", r.stdout)
            self.assertIn("맥 자산 미포함", r.stdout)


class KeyBridgeGateTests(unittest.TestCase):
    """★7-b 키 브리지 게이트 — 업데이터 서명 키 == 직전 판 바이너리 pubkey 키(docs/KEY-ROTATION.md)."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = self._td.name

    def tearDown(self):
        self._td.cleanup()

    def _resign_all(self, key_id, only=None):
        """업데이터 .sig 를 key_id 로 다시 쓰고 latest.json·SUMS 를 맞춘다(only=그 .sig 만)."""
        latest_p = os.path.join(self.root, "latest.json")
        with open(latest_p, encoding="utf-8") as fh:
            latest = json.load(fh)
        for name in sorted(os.listdir(self.root)):
            if not name.endswith(".sig") or (only and name != only):
                continue
            text = _sig_text("re-" + name, key_id)
            with open(os.path.join(self.root, name), "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
            asset = name[:-4]
            for row in latest["platforms"].values():
                if row["url"].endswith("/" + asset):
                    row["signature"] = text
        with open(latest_p, "w", encoding="utf-8") as fh:
            json.dump(latest, fh, ensure_ascii=False)
        write_sums(self.root)

    def test_kb1_pass_when_sig_key_matches_prev_binary(self):
        build_fixture(self.root)
        rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)

    def test_kb2_reject_when_all_sigs_use_other_key(self):
        """브리지 실수 — 직전 판 바이너리(pubkey=FIXTURE)가 받지 못할 키로 서명한 판."""
        build_fixture(self.root)
        self._resign_all(OTHER_KEY_ID)
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        self.assertIn("업데이터 서명 키 불일치", str(cm.exception))

    def test_kb3_reject_when_one_platform_sig_uses_other_key(self):
        """한 레그만 다른 키 — 전수 대조가 아니면 빠져나간다."""
        build_fixture(self.root)
        self._resign_all(OTHER_KEY_ID, only="cysr_x64.app.tar.gz.sig")
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        self.assertIn("cysr_x64.app.tar.gz.sig", str(cm.exception))

    def test_kb4_windows_only_bundle_also_gated(self):
        build_fixture(self.root, mac=False)
        self._resign_all(OTHER_KEY_ID)
        with self.assertRaises(rv.VerifyError):
            rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, PACK_KEYRING)
        rv.verify(V, self.root, VENDOR, OTHER_KEY_ID, PREV, PACK_KEYRING)

    def test_kb5_bad_expected_key_id_format_rejected(self):
        build_fixture(self.root)
        for bad in ("", "0123456789abcdef", "0123", None):
            with self.assertRaises(rv.VerifyError):
                rv.verify(V, self.root, VENDOR, bad, PREV, PACK_KEYRING)

    def test_kb6_real_pubkey_derives_deploy_key_id(self):
        """실물 대조 — 현행 배포 pubkey 에서 파생한 id 가 알려진 key id 와 같다(바이트 순서 회귀 검출)."""
        self.assertEqual(rv.tauri_pubkey_key_id(REAL_TAURI_PUBKEY), "54FBA04AD0E0F49D")
        self.assertEqual(rv.updater_sig_key_id(_sig_text("x", "54FBA04AD0E0F49D")), "54FBA04AD0E0F49D")

    def test_kb7_cli_prev_tauri_conf_pass_and_reject(self):
        build_fixture(self.root)
        with tempfile.TemporaryDirectory() as cd:
            conf = os.path.join(cd, "tauri.conf.json")
            for key_id, want_rc in ((FIXTURE_KEY_ID, 0), (OTHER_KEY_ID, 1)):
                with open(conf, "w", encoding="utf-8") as fh:
                    json.dump({"plugins": {"updater": {"pubkey": _tauri_pub(key_id)}}}, fh)
                r = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root,
                                                  "--prev-tauri-conf", conf, key_id=None)
                self.assertEqual(r.returncode, want_rc, r.stderr)
                if want_rc:
                    self.assertIn("업데이터 서명 키 불일치", r.stderr)

    def test_kb8_cli_requires_key_source(self):
        build_fixture(self.root)
        r = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root, key_id=None)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("--updater-key-id", r.stderr)

    def test_kb9_prev_conf_without_pubkey_fails_closed(self):
        build_fixture(self.root)
        with tempfile.TemporaryDirectory() as cd:
            conf = os.path.join(cd, "tauri.conf.json")
            with open(conf, "w", encoding="utf-8") as fh:
                json.dump({"plugins": {}}, fh)
            r = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root,
                                              "--prev-tauri-conf", conf, key_id=None)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("pubkey 가 없다", r.stderr)


class PackSigningKeyGateTests(unittest.TestCase):
    """★8-a 팩 서명 키 게이트 — 팩 key_id ∈ 직전 판 바이너리 팩 키링 · .minisig key id == manifest key_id.

    지키는 사고: 업데이터 비밀과 팩 비밀을 가르지 않은 채 업데이터 키를 회전하면 팩이 새 업데이터 키로
    서명된다 — 설치된 앱의 키링에 그 키가 없어 전 사용자의 팩 갱신이 「알 수 없는 key_id」로 멈춘다.
    """

    ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = self._td.name
        build_fixture(self.root)

    def tearDown(self):
        self._td.cleanup()

    def _rewrite_pack(self, manifest_key=FIXTURE_PACK_KEY_ID, sig_key=FIXTURE_PACK_KEY_ID):
        mp = os.path.join(self.root, "pack-manifest.json")
        with open(mp, encoding="utf-8") as fh:
            man = json.load(fh)
        man["key_id"] = manifest_key
        with open(mp, "w", encoding="utf-8") as fh:
            json.dump(man, fh)
        with open(mp + ".minisig", "w", encoding="utf-8") as fh:
            fh.write(_minisig_text("pack-re", sig_key))
        write_sums(self.root)

    def _keyring(self, *key_ids, revoked=(), not_after="2100-01-01T00:00:00Z"):
        path = os.path.join(self.root + "-kr.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(_keyring_json(key_ids, revoked, not_after), fh)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return rv.load_pack_keyring(path)

    def assert_fail(self, keyring, needle, now=None):
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, keyring, now=now)
        self.assertIn(needle, str(cm.exception))

    def test_pk1_pass_when_pack_key_in_prev_keyring(self):
        rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, PREV, self._keyring(OTHER_KEY_ID, FIXTURE_PACK_KEY_ID))

    def test_pk2_reject_pack_signed_with_key_absent_from_prev_keyring(self):
        """회전 사고 재현 — 팩이 업데이터 키(FIXTURE_KEY_ID)로 서명됐고 키링엔 팩 키만 있다."""
        self._rewrite_pack(FIXTURE_KEY_ID, FIXTURE_KEY_ID)
        self.assert_fail(self._keyring(FIXTURE_PACK_KEY_ID), "직전 판 바이너리 팩 키링")

    def test_pk3_reject_minisig_key_differs_from_manifest_key_id(self):
        """key_id 칸은 키링에 있는 값인데 실제 서명은 다른 키 — 칸만 맞춘 사고."""
        self._rewrite_pack(FIXTURE_PACK_KEY_ID, OTHER_KEY_ID)
        self.assert_fail(self._keyring(FIXTURE_PACK_KEY_ID, OTHER_KEY_ID), "팩 서명 키 불일치")

    def test_pk4_reject_revoked_key(self):
        self.assert_fail(self._keyring(FIXTURE_PACK_KEY_ID, revoked=(FIXTURE_PACK_KEY_ID,)), "폐기")

    def test_pk5_reject_expired_key(self):
        self.assert_fail(self._keyring(FIXTURE_PACK_KEY_ID, not_after="2026-01-01T00:00:00Z"), "만료")

    def test_pk6_reject_malformed_or_missing_manifest_key_id(self):
        for bad in ("11223344556677aa", "", 1234, None):
            with self.subTest(bad=bad):
                self._rewrite_pack(bad, FIXTURE_PACK_KEY_ID)
                self.assert_fail(PACK_KEYRING, "key_id 형식 오류")

    def test_pk7_keyring_with_mislabeled_key_id_fails_closed(self):
        path = self.root + "-bad-kr.json"
        data = _keyring_json([FIXTURE_PACK_KEY_ID])
        data["keys"][0]["pubkey"] = _tauri_pub(OTHER_KEY_ID)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        self.addCleanup(os.remove, path)
        with self.assertRaises(rv.VerifyError) as cm:
            rv.load_pack_keyring(path)
        self.assertIn("공개키 파생 key id", str(cm.exception))

    def test_pk8_cli_requires_prev_pack_keyring_both_modes(self):
        r = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root, keyring=None)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("--prev-pack-keyring", r.stderr)
        r = PackOnlyLaneTests.run_pack_only(self, {"signed_at": FIXTURE_SIGNED_AT}, keyring=None)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("--prev-pack-keyring", r.stderr)

    def test_pk9_cli_full_and_pack_only_reject_key_absent_from_keyring(self):
        r = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root,
                                          keyring=(OTHER_KEY_ID,))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("직전 판 바이너리 팩 키링", r.stderr)
        r = PackOnlyLaneTests.run_pack_only(self, {"signed_at": FIXTURE_SIGNED_AT}, keyring=(OTHER_KEY_ID,))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("직전 판 바이너리 팩 키링", r.stderr)
        r = PackOnlyLaneTests.run_pack_only(self, {"signed_at": FIXTURE_SIGNED_AT}, sig_key=OTHER_KEY_ID,
                                            keyring=(FIXTURE_PACK_KEY_ID, OTHER_KEY_ID))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("팩 서명 키 불일치", r.stderr)
        r = PackOnlyLaneTests.run_pack_only(self, {"signed_at": FIXTURE_SIGNED_AT}, sig_key=None)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("팩 파일이 없다", r.stderr)

    def test_pk10_real_repo_keyring_loads_and_trusts_workflow_key_id(self):
        """실물 대조 — 저장소 키링이 게이트 로더를 통과하고, 두 레인의 KEY_ID 가 그 키링에 있다."""
        keys, revoked = rv.load_pack_keyring(os.path.join(self.ROOT, "cysjavis-pack", "trusted-keys.json"))
        for wf in ("release.yml", "pack-release.yml"):
            with open(os.path.join(self.ROOT, ".github", "workflows", wf), encoding="utf-8") as fh:
                body = fh.read()
            ids = re.findall(r"^\s*KEY_ID: '([0-9A-F]{16})'", body, re.M)
            self.assertEqual(len(ids), 1, wf)
            self.assertIn(ids[0], keys, "%s KEY_ID %s 가 저장소 팩 키링에 없다" % (wf, ids[0]))
            self.assertNotIn(ids[0], revoked)

    def test_pk11_workflows_wire_pack_secret_and_keyring(self):
        """워크플로 문면 — 팩 서명은 팩 전용 비밀 · 발행 두 잡과 팩-온리 게이트는 --prev-pack-keyring 을 넘긴다."""
        def body(wf):
            with open(os.path.join(self.ROOT, ".github", "workflows", wf), encoding="utf-8") as fh:
                return "\n".join(l for l in fh.read().splitlines() if not l.lstrip().startswith("#"))
        for wf in ("release.yml", "pack-release.yml"):
            b = body(wf)
            start = b.find("- name: Sign pack-manifest.json")
            end = b.find("- name:", start + 1)
            step = b[start:end]
            self.assertNotEqual(start, -1, wf)
            self.assertIn("secrets.CYS_PACK_SIGNING_PRIVATE_KEY }}", step, wf)
            self.assertNotIn("TAURI_SIGNING_PRIVATE_KEY", step, "%s 팩 서명이 업데이터 비밀을 쓴다" % wf)
        pub = body("release-publish.yml")
        self.assertEqual(pub.count("python3 .release-tools/scripts/release-verify.py"), 2)
        self.assertEqual(pub.count("--prev-pack-keyring prev-trusted-keys.json"), 2)
        self.assertEqual(pub.count('git show "$PREV_TAG:cysjavis-pack/trusted-keys.json" > prev-trusted-keys.json'), 2)
        pr = body("pack-release.yml")
        gate = pr.find("scripts/release-verify.py --pack-only")
        step = pr[pr.rfind("- name:", 0, gate):pr.find("- name:", gate)]
        self.assertIn("--prev-pack-keyring prev-trusted-keys.json", step)
        self.assertIn('git show "v$MIN_BINARY:cysjavis-pack/trusted-keys.json"', step)


class ConstantsSanityTests(unittest.TestCase):
    """상수 자체의 자기정합 — 손으로 고치다 어긋나는 걸 잡는다."""

    def test_required_and_updater_cover_thirteen(self):
        covered = {a.format(v=V) for a in rv.REQUIRED_ASSETS}
        covered |= {a.format(v=V) for a in rv.MAC_ASSETS}
        for asset_tpl in rv.UPDATER_PLATFORMS.values():
            asset = asset_tpl.format(v=V)
            covered.add(asset)
            covered.add(asset + ".sig")
        self.assertEqual(len(covered), 13,
                         "하한선이 덮는 자산이 13종이 아니다: %s" % sorted(covered))

    def test_lane_split_is_a_partition(self):
        """★분할이 겹치거나 새면 안 된다 — 종전 8종이 지금 두 튜플의 **합**이어야 한다."""
        self.assertEqual(set(rv.REQUIRED_ASSETS) & set(rv.MAC_ASSETS), set(),
                         "필수 레인과 맥 레인이 겹친다")
        self.assertEqual(sorted(set(rv.REQUIRED_ASSETS) | set(rv.MAC_ASSETS)),
                         sorted(("cysr_{v}_aarch64.dmg", "cysr_{v}_x64.dmg",
                                 "cysr_{v}_x64-setup.exe", "cysr_{v}_x64-setup.zip",
                                 "latest.json", "pack.tar.gz", "pack-manifest.json",
                                 "pack-manifest.json.minisig")),
                         "분할 전 8종의 합이 아니다 — 자산이 조용히 빠졌거나 늘었다")
        self.assertEqual(set(rv.REQUIRED_PLATFORMS) & set(rv.MAC_PLATFORMS), set(),
                         "필수 플랫폼과 맥 플랫폼이 겹친다")
        self.assertEqual(rv.UPDATER_PLATFORMS,
                         dict(rv.REQUIRED_PLATFORMS, **rv.MAC_PLATFORMS),
                         "UPDATER_PLATFORMS 가 두 레인의 합이 아니다")

    def test_mac_lane_files_is_exactly_six(self):
        lane = rv.mac_lane_files(V)
        self.assertEqual(len(lane), 6, "맥 레인 전집합이 6종이 아니다: %s" % lane)
        self.assertTrue(all(("darwin" in k) for k in rv.MAC_PLATFORMS))

    def test_every_covered_asset_has_a_shape_rule(self):
        covered = {a.format(v=V) for a in rv.REQUIRED_ASSETS}
        for asset_tpl in rv.UPDATER_PLATFORMS.values():
            asset = asset_tpl.format(v=V)
            covered.add(asset)
            covered.add(asset + ".sig")
        for name in sorted(covered):
            self.assertTrue(any(name.endswith(sfx) for sfx, _ in rv.ASSET_SHAPES),
                            "지문 규칙이 없는 자산: %s" % name)


class VersionProgressGateTests(unittest.TestCase):
    """9단계 — 판번·build_id 이중 게이트의 발행 쪽 방어선(TICKET=cysr-brand-version · 2026-09-15)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = build_fixture(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def set_build_id(self, bid):
        p = os.path.join(self.root, "latest.json")
        d = json.load(open(p, encoding="utf-8"))
        d["build_id"] = bid
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False)
        write_sums(self.root)

    def fail_with(self, prev, needle):
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, prev, PACK_KEYRING)
        self.assertIn(needle, str(cm.exception))

    def test_91_higher_version_passes_even_if_previous_has_no_build_id(self):
        rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, {"version": "0.14.18"}, PACK_KEYRING)          # 0.14.x 구판 = build_id 없음

    def test_92_same_version_different_build_id_is_refused(self):
        self.fail_with({"version": V, "build_id": "fedcba987654.20260801T0000Z"}, "판번 미증가")

    def test_93_same_version_same_build_id_passes(self):
        rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, {"version": V, "build_id": BID}, PACK_KEYRING)  # 공개된 그 발행의 재검증

    def test_94_lower_version_is_refused(self):
        self.fail_with({"version": "0.14.20", "build_id": BID}, "판번 역행")

    def test_95_same_version_previous_without_build_id_is_refused(self):
        self.fail_with({"version": "v" + V}, "판번 미증가")

    def test_96_missing_or_dirty_build_id_is_refused(self):
        for bad in (None, "", "0123456789ab-dirty.20260915T1030Z", "0123456789AB.20260915T1030Z",
                    "0123456789ab.20260915T1030Z\n"):
            with self.subTest(bad=bad):
                self.set_build_id(bad)
                self.fail_with(PREV, "build_id 형식 오류")

    def test_97_previous_unreadable_is_a_failure_not_a_skip(self):
        with self.assertRaises(rv.VerifyError) as cm:
            rv.load_previous_latest("unused", path=os.path.join(self.root, "no-such-latest.json"))
        self.assertIn("조회 불가", str(cm.exception))
        with self.assertRaises(rv.VerifyError):
            rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, ["not", "an", "object"], PACK_KEYRING)

    def test_98_previous_latest_has_no_default(self):
        import inspect
        param = inspect.signature(rv.verify).parameters["previous_latest"]
        self.assertIs(param.default, inspect.Parameter.empty,
                      "verify() 의 previous_latest 에 기본값이 생겼다 — 9단계를 생략할 수 있게 된다")


class KeyBridgeVersionProgressCrossTests(unittest.TestCase):
    """★두 게이트 합성 지점(TICKET=cys-v1-integrate · 2026-09-15) — 7-b(키 브리지)와 9(판번·build_id)가
    한 verify() 안에서 **둘 다** 산다. 한쪽 통과가 다른 쪽을 면제하지 않고, 둘 다 깨지면 7-b 가 먼저 죽인다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = build_fixture(self._tmp.name)
        self.same_build = {"version": V, "build_id": BID}   # 9단계 통과(공개된 그 발행의 재검증)

    def tearDown(self):
        self._tmp.cleanup()

    def test_x1_build_id_gate_passes_and_key_gate_passes(self):
        rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, self.same_build, PACK_KEYRING)

    def test_x2_build_id_gate_passes_but_key_gate_refuses(self):
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, VENDOR, OTHER_KEY_ID, self.same_build, PACK_KEYRING)
        self.assertIn("업데이터 서명 키 불일치", str(cm.exception))

    def test_x3_key_gate_passes_but_version_gate_refuses(self):
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, VENDOR, FIXTURE_KEY_ID, {"version": V, "build_id": "fedcba987654.20260801T0000Z"}, PACK_KEYRING)
        self.assertIn("판번 미증가", str(cm.exception))

    def test_x4_both_broken_key_gate_reports_first(self):
        with self.assertRaises(rv.VerifyError) as cm:
            rv.verify(V, self.root, VENDOR, OTHER_KEY_ID, {"version": "0.14.20", "build_id": BID}, PACK_KEYRING)
        self.assertIn("업데이터 서명 키 불일치", str(cm.exception))

    def test_x5_updater_key_id_has_no_default(self):
        import inspect
        params = inspect.signature(rv.verify).parameters
        self.assertIs(params["updater_key_id"].default, inspect.Parameter.empty,
                      "verify() 의 updater_key_id 에 기본값이 생겼다 — 7-b 를 생략할 수 있게 된다")
        self.assertEqual(list(params)[:5],
                         ["version", "release_dir", "vendor_manifest", "updater_key_id", "previous_latest"])

    def test_x6_cli_needs_both_sources(self):
        """CLI: 7-b 기준(--prev-tauri-conf)과 9단계 기준(--previous-latest-file)을 함께 받아 둘 다 판정한다."""
        with tempfile.TemporaryDirectory() as cd:
            conf = os.path.join(cd, "tauri.conf.json")
            with open(conf, "w", encoding="utf-8") as fh:
                json.dump({"plugins": {"updater": {"pubkey": _tauri_pub(FIXTURE_KEY_ID)}}}, fh)
            ok = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root,
                                               "--prev-tauri-conf", conf, key_id=None)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            # 직전판 파일의 build_id 까지 CLI 가 온전히 넘기는가 — 같은 판번·같은 build_id 는 통과여야 한다.
            same = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root,
                                                 "--prev-tauri-conf", conf, key_id=None,
                                                 prev={"version": V, "build_id": BID})
            self.assertEqual(same.returncode, 0, same.stderr)
            bad = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root,
                                                "--prev-tauri-conf", conf, key_id=None,
                                                prev={"version": "0.14.20", "build_id": BID})
            self.assertEqual(bad.returncode, 1, bad.stdout)
            self.assertIn("판번 역행", bad.stderr)

    def test_x7_cli_both_gates_broken_key_gate_reports_first(self):
        """codex 1R 지적 경로 — CLI 에서도 둘 다 깨지면 7-b 사유가 먼저 나온다."""
        r = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root,
                                          key_id=OTHER_KEY_ID, prev={"version": "0.14.20", "build_id": BID})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("업데이터 서명 키 불일치", r.stderr)
        self.assertNotIn("판번 역행", r.stderr)

    def test_x8_cli_key_sources_are_mutually_exclusive(self):
        """codex 1R 지적 경로 — --updater-key-id 와 --prev-tauri-conf 동시 지정은 사용법 오류(2)."""
        with tempfile.TemporaryDirectory() as cd:
            conf = os.path.join(cd, "tauri.conf.json")
            with open(conf, "w", encoding="utf-8") as fh:
                json.dump({"plugins": {"updater": {"pubkey": _tauri_pub(FIXTURE_KEY_ID)}}}, fh)
            r = ExitCodeContractTests.run_cli(self, "--version", V, "--release-dir", self.root,
                                              "--prev-tauri-conf", conf)   # key_id 기본값도 함께 넘어간다
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_x9_previous_latest_remote_fetch_success_and_failure(self):
        """codex 1R 지적 경로 — --previous-latest-file 생략 시의 원격 조회를 네트워크 없이 통제한다."""
        from unittest import mock
        url = rv.PREVIOUS_LATEST_URL_TPL % rv.RELEASE_REPO
        body = json.dumps({"version": "0.14.36"}).encode()
        fake = mock.MagicMock()
        fake.__enter__.return_value.read.return_value = body
        with mock.patch.object(rv.urllib.request, "urlopen", return_value=fake) as uo:
            self.assertEqual(rv.load_previous_latest(url), {"version": "0.14.36"})
        self.assertEqual(uo.call_args[0][0], url)
        with mock.patch.object(rv.urllib.request, "urlopen", side_effect=OSError("offline")):
            with self.assertRaises(rv.VerifyError) as cm:
                rv.load_previous_latest(url)
        self.assertIn("직전 공개판 latest.json 조회 불가", str(cm.exception))
        self.assertIn(url, str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
