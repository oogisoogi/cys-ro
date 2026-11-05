"""javis_asset_fetch — 런타임 원문 참조(⑵)의 찾는 순서·캐시·폴백 시험 (TICKET=asset-skills-for-seats).

네트워크 0: 노션 응답은 가짜 opener 로 흉내 낸다.
"""
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "javis_asset_fetch", os.path.join(HERE, "..", "javis_asset_fetch.py"))
af = importlib.util.module_from_spec(spec)
spec.loader.exec_module(af)

PAGE = "40371a69-3e54-80bd-af3a-ec362419d8e0"
LONG = "본문 " * 150


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def notion_opener(text=LONG, fail=False):
    calls = []

    def op(req, timeout=None):
        calls.append(req.full_url)
        if fail:
            raise OSError("network down")
        rec = {"recordMap": {"block": {
            PAGE: {"value": {"value": {"type": "page", "properties": {"title": [["제목"]]},
                                       "content": ["b1", "b2"]}}},
            "b1": {"value": {"value": {"type": "bulleted_list", "properties": {"title": [[text]]}}}},
            "b2": {"value": {"value": {"type": "code", "properties": {"title": [["print(1)"]]}}}},
        }}, "cursor": {"stack": []}}
        return _Resp(json.dumps(rec).encode())
    op.calls = calls
    return op


class AssetFetchTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="asset-fetch-")
        self.pack = os.path.join(self.root, "pack")
        sk = os.path.join(self.pack, "skills", "demo")
        os.makedirs(os.path.join(sk, "references"))
        with open(os.path.join(sk, "references", "s.md"), "w", encoding="utf-8") as f:
            f.write("우리 요약\n")
        with open(os.path.join(sk, "sources.json"), "w", encoding="utf-8") as f:
            json.dump({"sources": [
                {"id": "src", "kind": "notion", "url": "https://app.notion.com/p/x",
                 "page_id": PAGE, "summary": "references/s.md", "attribution": "지은이"},
                {"id": "esc", "kind": "notion", "url": "https://app.notion.com/p/y",
                 "page_id": PAGE, "summary": "../../../../etc/passwd"},
                {"id": "plain", "kind": "http", "url": "http://insecure.example/x",
                 "summary": "references/s.md"},
            ]}, f)
        self.env = {k: os.environ.get(k) for k in ("CYS_PACK_DIR", "CYS_LOCAL_DIR", "CYS_ASSET_CACHE_DIR")}
        os.environ["CYS_PACK_DIR"] = self.pack
        os.environ.pop("CYS_LOCAL_DIR", None)
        os.environ.pop("CYS_ASSET_CACHE_DIR", None)

    def tearDown(self):
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.root, ignore_errors=True)

    def test_fetch_then_cache_then_refresh(self):
        op = notion_opener()
        r = af.resolve("demo", "src", opener=op, now=1000.0)
        self.assertEqual(r["mode"], "fetched")
        self.assertTrue(r["path"].startswith(os.path.join(self.root, "asset-cache")))
        body = open(r["path"], encoding="utf-8").read()
        self.assertIn("# 제목", body)
        self.assertIn("- 본문", body)
        self.assertIn("```\nprint(1)\n```", body)
        self.assertIn("재배포하지 않는다", body)
        r2 = af.resolve("demo", "src", opener=op, now=1000.0 + 6 * 86400)
        self.assertEqual(r2["mode"], "cache")
        self.assertEqual(len(op.calls), 1, "7일 안에는 다시 받지 않는다")
        r3 = af.resolve("demo", "src", opener=op, now=1000.0 + 8 * 86400)
        self.assertEqual(r3["mode"], "fetched")
        self.assertEqual(len(op.calls), 2, "7일이 지나면 새로 받는다")

    def test_stale_cache_when_fetch_fails(self):
        af.resolve("demo", "src", opener=notion_opener(), now=0.0)
        r = af.resolve("demo", "src", opener=notion_opener(fail=True), now=10 * 86400.0)
        self.assertEqual(r["mode"], "stale-cache")
        self.assertIn("10일 전", r["notice"])

    def test_summary_when_nothing(self):
        r = af.resolve("demo", "src", opener=notion_opener(fail=True), now=0.0)
        self.assertEqual(r["mode"], "summary")
        self.assertTrue(r["path"].endswith(os.path.join("references", "s.md")))
        self.assertIn("우리 요약으로", r["notice"])

    def test_too_short_is_failure(self):
        r = af.resolve("demo", "src", opener=notion_opener(text="짧다"), now=0.0)
        self.assertEqual(r["mode"], "summary")
        self.assertIn("너무 짧다", r["notice"])

    def test_local_copy_wins(self):
        p = os.path.join(self.root, "local", "assets", "demo")
        os.makedirs(p)
        with open(os.path.join(p, "src.md"), "w", encoding="utf-8") as f:
            f.write("박사님 사본\n")
        op = notion_opener()
        r = af.resolve("demo", "src", opener=op, now=0.0)
        self.assertEqual(r["mode"], "local")
        self.assertEqual(op.calls, [], "사본이 있으면 네트워크 0")

    def test_summary_path_cannot_escape_skill_dir(self):
        with self.assertRaises(af.FetchError):
            af.resolve("demo", "esc", opener=notion_opener(fail=True), now=0.0)

    def test_https_only(self):
        r = af.resolve("demo", "plain", opener=notion_opener(), now=0.0)
        self.assertEqual(r["mode"], "summary")
        self.assertIn("https", r["notice"])

    def test_unknown_id_and_cli_codes(self):
        self.assertEqual(af.main(["get", "demo", "nope"]), 2)
        self.assertEqual(af.main([]), 3)


if __name__ == "__main__":
    unittest.main()
