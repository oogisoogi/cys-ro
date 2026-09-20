#!/usr/bin/env python3
"""latest.json 맥 행 생성기 회귀 — B7 · TICKET=v110-darwin-update.

이 시험이 지키는 성질 셋:
  ① 검증 칸 넷(url·sha256·size·cdhash)을 **실측으로** 채운다 — 하나라도 없으면 앱이 거부한다.
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
        self.assertEqual(row["size"], 104)
        self.assertEqual(len(row["sha256"]), 64)
        self.assertEqual(row["cdhash"], "abcd1234")  # 소문자 정규화(앱 쪽 대조와 같은 규칙)
        self.assertTrue(row["url"].endswith("/v1.1.0/cysr-macos-arm64-v1.1.0.zip"))

    def test_signature_key_always_present(self):
        # ★이 한 줄이 윈도 업데이트를 지킨다 — 값이 아니라 **키의 존재**가 계약이다.
        row = darwin_row.build_row("1.1.0", self.zip, "ab")
        self.assertIn("signature", row)
        self.assertIsInstance(row["signature"], str)

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

    def test_cli_merge_writes_file(self):
        path = os.path.join(self.tmp.name, "latest.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"version": "1.1.0", "platforms": {"windows-x86_64": dict(WIN_ROW)}}, fh)
        rc = darwin_row.main(["--version", "1.1.0", "--zip", self.zip, "--cdhash", "ab", "--merge", path])
        self.assertEqual(rc, 0)
        with open(path, encoding="utf-8") as fh:
            out = json.load(fh)
        self.assertEqual(sorted(out["platforms"]), ["darwin-aarch64", "windows-x86_64"])


class PublishedManifestShape(unittest.TestCase):
    """발행본 규약 — platforms 의 **모든** 행에 url·signature 가 있어야 한다(윈도 보호)."""

    def test_predicate_is_the_one_the_script_uses(self):
        # 술어를 두 벌로 두지 않는다 — 스크립트가 발행 전에 부르는 바로 그 함수를 시험한다.
        self.assertTrue(callable(darwin_row.every_row_has_url_and_signature))
        src = open(os.path.join(os.path.dirname(HERE), "make-darwin-update-row.py"), encoding="utf-8").read()
        self.assertIn("missing = every_row_has_url_and_signature(out)", src)


if __name__ == "__main__":
    unittest.main()
