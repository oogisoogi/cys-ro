#!/usr/bin/env python3
"""latest.json 맥 행 생성기 회귀 — B7 · TICKET=v110-darwin-update.

이 시험이 지키는 성질:
  ① 검증 칸 넷(zip_url·zip_sha256·zip_size·zip_cdhash)을 **실측으로** 채운다 — 하나라도 없으면 앱이 거부한다.
  ①-b 병합이 **구판 절반(url=tar.gz · signature)을 보존**한다 — 덮어쓰면 1.0.2 맥의 갱신이 끊긴다.
  ② `signature` 칸을 비워서라도 반드시 넣는다 — 없으면 platforms 전체 역직렬화가 깨져 **윈도**
     사용자의 업데이트까지 죽는다(tauri-plugin-updater 의 untagged enum).
  ③ 병합이 기존 행(윈도 발행본)을 건드리지 않는다.
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import importlib.util

# 파일명에 하이픈이 있어 일반 import 가 안 된다 — 경로로 적재한다(스크립트 이름은 관례를 따른다).
spec = importlib.util.spec_from_file_location("darwin_row", os.path.join(os.path.dirname(HERE), "make-darwin-update-row.py"))
darwin_row = importlib.util.module_from_spec(spec)
spec.loader.exec_module(darwin_row)

LEGACY_HALF = {
    "signature": "dW50cnVzdGVkY29tbWVudA==",
    "url": "https://github.com/oogisoogi/cys-ro/releases/download/v1.1.0/cysr_aarch64.app.tar.gz",
}

WIN_ROW = {
    "signature": "dW50cnVzdGVk...",
    "url": "https://github.com/oogisoogi/cys-ro/releases/download/v1.0.2/cysr_1.0.2_x64-setup.exe",
}


class DarwinRow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.zip = os.path.join(self.tmp.name, "cysr-macos-arm64-v1.1.0.zip")
        with open(self.zip, "wb") as fh:
            fh.write(b"PK\x03\x04" + b"0" * 100)

    def tearDown(self):
        self.tmp.cleanup()

    def test_row_carries_all_four_verification_fields(self):
        row = darwin_row.build_row("1.1.0", self.zip, "ABCD1234")
        self.assertEqual(row["zip_size"], 104)
        self.assertEqual(len(row["zip_sha256"]), 64)
        self.assertEqual(row["zip_cdhash"], "abcd1234")  # 소문자 정규화(앱 쪽 대조와 같은 규칙)
        self.assertTrue(row["zip_url"].endswith("/v1.1.0/cysr-macos-arm64-v1.1.0.zip"))

    def test_app_half_never_writes_the_legacy_url_slot(self):
        """★이 티켓의 축 — 앱 절반은 `url` 칸을 **건드리지 않는다**.

        건드리면 구판(1.0.2)이 우리 zip 을 tar.gz 로 풀려다 실패한다. 칸을 가른 뜻이 여기 있다.
        """
        row = darwin_row.build_row("1.1.0", self.zip, "ab")
        self.assertNotIn("url", row)
        self.assertEqual(sorted(row), sorted(darwin_row.ZIP_KEYS))

    def test_signature_key_always_present(self):
        # ★이 한 줄이 윈도 업데이트를 지킨다 — 값이 아니라 **키의 존재**가 계약이다.
        # (구판 절반이 그 칸의 주인이므로, 병합 결과에서 단언한다.)
        manifest = {"version": "1.1.0", "platforms": {"darwin-aarch64": dict(LEGACY_HALF)}}
        out = darwin_row.merge_row(manifest, "darwin-aarch64",
                                   darwin_row.build_row("1.1.0", self.zip, "ab"))
        self.assertIn("signature", out["platforms"]["darwin-aarch64"])
        self.assertEqual(darwin_row.every_row_has_url_and_signature(out), [])

    def test_merge_preserves_the_legacy_half(self):
        """★회귀 그물 — 종전 merge_row 는 행을 **대체**해 구판 절반을 지웠다."""
        manifest = {"version": "1.1.0", "platforms": {"darwin-aarch64": dict(LEGACY_HALF)}}
        row = darwin_row.build_row("1.1.0", self.zip, "ab")
        out = darwin_row.merge_row(manifest, "darwin-aarch64", row)
        merged = out["platforms"]["darwin-aarch64"]
        self.assertEqual(merged["url"], LEGACY_HALF["url"])
        self.assertEqual(merged["signature"], LEGACY_HALF["signature"])
        self.assertTrue(merged["url"].endswith(".app.tar.gz"))
        self.assertEqual(merged["zip_url"], row["zip_url"])
        self.assertNotEqual(merged["url"], merged["zip_url"], "두 소비자가 같은 자산을 받고 있다")

    def test_legacy_half_predicate_is_fail_closed(self):
        ok = dict(LEGACY_HALF); ok.update({"zip_url": "z"})
        self.assertIsNone(darwin_row.legacy_half_problem(ok))
        # url 부재 · zip 을 가리키는 url · signature 부재 — 셋 다 차단 사유다.
        self.assertIsNotNone(darwin_row.legacy_half_problem({"signature": ""}))
        self.assertIsNotNone(darwin_row.legacy_half_problem(
            {"signature": "", "url": "https://x/cysr-macos-arm64-v1.1.0.zip"}))
        self.assertIsNotNone(darwin_row.legacy_half_problem({"url": LEGACY_HALF["url"]}))

    def test_missing_cdhash_is_fail_closed(self):
        with self.assertRaises(SystemExit):
            darwin_row.build_row("1.1.0", self.zip, None)

    def test_merge_keeps_windows_rows(self):
        manifest = {"version": "1.1.0", "platforms": {"windows-x86_64": dict(WIN_ROW)}}
        row = darwin_row.build_row("1.1.0", self.zip, "ab")
        out = darwin_row.merge_row(manifest, "darwin-aarch64", row)
        self.assertEqual(out["platforms"]["windows-x86_64"], WIN_ROW)
        self.assertIn("darwin-aarch64", out["platforms"])
        # 입력을 제자리 수정하지 않는다(호출부가 원본을 다시 쓸 수 있어야 한다).
        self.assertNotIn("darwin-aarch64", manifest["platforms"])

    def test_every_row_predicate_catches_missing_signature(self):
        bad = {"platforms": {"darwin-aarch64": {"url": "u", "sha256": "x", "size": 1, "cdhash": "y"}}}
        self.assertEqual(darwin_row.every_row_has_url_and_signature(bad), ["darwin-aarch64"])
        good = {"platforms": {"darwin-aarch64": {"url": "u", "signature": ""}}}
        self.assertEqual(darwin_row.every_row_has_url_and_signature(good), [])

    def test_cdhash_parser_matches_codesign_shape(self):
        out = "Identifier=com.cysjavis.terminal\nCDHash=0A1b2C3d\nSignature=adhoc\n"
        self.assertEqual(darwin_row.parse_cdhash(out), "0a1b2c3d")
        self.assertIsNone(darwin_row.parse_cdhash("CDHash 없음"))

    def _manifest_file(self, darwin=None):
        path = os.path.join(self.tmp.name, "latest.json")
        platforms = {"windows-x86_64": dict(WIN_ROW)}
        if darwin is not None:
            platforms["darwin-aarch64"] = dict(darwin)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"version": "1.1.0", "platforms": platforms}, fh)
        return path

    def test_cli_merge_writes_file(self):
        path = self._manifest_file(LEGACY_HALF)
        rc = darwin_row.main(["--version", "1.1.0", "--zip", self.zip, "--cdhash", "ab", "--merge", path])
        self.assertEqual(rc, 0)
        with open(path, encoding="utf-8") as fh:
            out = json.load(fh)
        self.assertEqual(sorted(out["platforms"]), ["darwin-aarch64", "windows-x86_64"])
        self.assertEqual(out["platforms"]["darwin-aarch64"]["url"], LEGACY_HALF["url"])
        self.assertIn("zip_url", out["platforms"]["darwin-aarch64"])

    def test_cli_refuses_when_legacy_half_absent(self):
        """구판 절반이 없는 매니페스트에 앱 절반만 얹어 발행하지 않는다(1.0.2 갱신 보호)."""
        path = self._manifest_file()
        with self.assertRaises(SystemExit):
            darwin_row.main(["--version", "1.1.0", "--zip", self.zip, "--cdhash", "ab", "--merge", path])

    def test_cli_can_supply_the_legacy_half(self):
        path = self._manifest_file()
        rc = darwin_row.main(["--version", "1.1.0", "--zip", self.zip, "--cdhash", "ab",
                              "--merge", path,
                              "--tarball-url", LEGACY_HALF["url"], "--tarball-sig", "sig"])
        self.assertEqual(rc, 0)
        with open(path, encoding="utf-8") as fh:
            row = json.load(fh)["platforms"]["darwin-aarch64"]
        self.assertEqual(row["url"], LEGACY_HALF["url"])
        self.assertEqual(row["signature"], "sig")


class PublishedManifestShape(unittest.TestCase):
    """발행본 규약 — platforms 의 **모든** 행에 url·signature 가 있어야 한다(윈도 보호)."""

    def test_predicate_is_the_one_the_script_uses(self):
        # 술어를 두 벌로 두지 않는다 — 스크립트가 발행 전에 부르는 바로 그 함수를 시험한다.
        self.assertTrue(callable(darwin_row.every_row_has_url_and_signature))
        src = open(os.path.join(os.path.dirname(HERE), "make-darwin-update-row.py"), encoding="utf-8").read()
        self.assertIn("missing = every_row_has_url_and_signature(out)", src)


if __name__ == "__main__":
    unittest.main()
