#!/usr/bin/env python3
"""asset_ledger_check.py 시험 (TICKET=cysr-1116-asset-skills-1120).

격리 HOME(임시 폴더)에 가짜 원천을 만들어 게이트가 대상을 실제로 때리는지 잰다 —
새 스킬·새 자산이 판정표에 없으면 붉음, 판정 값 오타면 붉음, 「넣음」 인데 팩에 없으면 붉음,
원천이 없는 기계면 초록이 아니라 「원천 없음」(rc 0 · 표지 문구), 표가 깨지면 rc 2.
본부 판정표(옆 .hq.md)가 있으면 합쳐 읽고, 그때만 본부 전용 원천(영상 검토 산출물)을 훑는다(TICKET=cysr-1116-pubcand-1120 D1).
쓰임: python3 scripts/tests/test_asset_ledger_check.py
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "asset_ledger_check.py"
LEDGER = ROOT / "docs" / "ASSET-LEDGER.md"

HEAD = """# t

## 4. 판정표

| 항목 키 | 종류 | 있는 곳 | 출처 | 팩 | 판정 | 초보 유익 | 근거 |
|---|---|---|---|---|---|---|---|
"""


def row(key, verdict):
    return f"| `{key}` | 스킬 | 본부 | 우리 | 있음 | {verdict} | 상 | 시험 |\n"


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="asset-ledger-t-"))
        self.home = self.tmp / "home"
        self.pack = self.tmp / "pack-skills"
        (self.pack / "alpha").mkdir(parents=True)
        (self.pack / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
        self.ledger = self.tmp / "LEDGER.md"
        self.hq = self.tmp / "LEDGER.hq.md"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_check(self, ledger_body=None, ledger=None):
        if ledger_body is not None:
            self.ledger.write_text(ledger_body, encoding="utf-8")
        p = subprocess.run([sys.executable, str(CHECK), "--ledger", str(ledger or self.ledger),
                            "--home", str(self.home), "--pack-skills", str(self.pack)],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        return p.returncode, p.stdout + p.stderr

    def mkskill(self, where, name):
        d = self.home / where / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")

    # ── 원천 대조 ──
    def test_new_home_skill_not_in_ledger_is_red(self):
        self.mkskill(".claude/skills", "alpha")
        self.mkskill(".claude/skills", "brand-new-skill")
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣음"))
        self.assertEqual(rc, 1, out)
        self.assertIn("skill:brand-new-skill", out)

    def test_each_of_four_skill_folders_is_a_source(self):
        for i, where in enumerate((".claude/skills", ".claude-acct2/skills", ".cys/local/skills", ".cys/claude/skills")):
            with self.subTest(where=where):
                shutil.rmtree(self.home, ignore_errors=True)
                self.mkskill(where, f"only-here-{i}")
                rc, out = self.run_check(HEAD + row("skill:alpha", "넣음"))
                self.assertEqual(rc, 1, out)
                self.assertIn(f"skill:only-here-{i}", out)

    def test_new_asset_and_bundle_item_and_review_asset_are_red(self):
        a = self.home / "axdev/master/assets"
        (a / "new-tool-bundle").mkdir(parents=True)
        (a / "video-production" / "tools").mkdir(parents=True)
        (a / "video-production" / "new-sheet.md").write_text("x", encoding="utf-8")
        r = self.home / "axdev/master/reports/video-reviews/assets"
        r.mkdir(parents=True)
        (r / "new-checklist.md").write_text("x", encoding="utf-8")
        self.hq.write_text(HEAD, encoding="utf-8")  # 본부 판정표가 있어야 본부 전용 원천을 훑는다
        rc, out = self.run_check(HEAD + row("asset:video-production/tools", "전용"))
        self.assertEqual(rc, 1, out)
        self.assertIn("asset:new-tool-bundle", out)
        self.assertIn("asset:video-production/new-sheet.md", out)
        self.assertIn("path:~/axdev/master/reports/video-reviews/assets/new-checklist.md", out)
        # 묶음 자체(video-production)는 키를 만들지 않는다 — 안 항목 단위로 판정
        self.assertNotIn("`asset:video-production` ", out)

    def test_glob_row_covers_prefix_and_backups_dots_are_ignored(self):
        a = self.home / "axdev/master/assets"
        a.mkdir(parents=True)
        (a / "REFERENCE-TOOLS.md").write_text("x", encoding="utf-8")
        (a / "REFERENCE-TOOLS.md.bak-20261110-x").write_text("x", encoding="utf-8")
        (a / ".DS_Store").write_text("x", encoding="utf-8")
        self.mkskill(".cys/claude/skills", ".trash")
        rc, out = self.run_check(HEAD + row("asset:REFERENCE-*", "전용"))
        self.assertEqual(rc, 0, out)
        self.assertIn("초록", out)

    def test_glob_row_does_not_cover_other_prefixes(self):
        """`*` 줄은 그 접두만 덮는다 — 다른 새 항목까지 덮으면 게이트가 눈이 먼다."""
        a = self.home / "axdev/master/assets"
        a.mkdir(parents=True)
        (a / "REFERENCE-TOOLS.md").write_text("x", encoding="utf-8")
        (a / "brand-new-folder").mkdir()
        rc, out = self.run_check(HEAD + row("asset:REFERENCE-*", "전용"))
        self.assertEqual(rc, 1, out)
        self.assertIn("asset:brand-new-folder", out)
        self.assertNotIn("asset:REFERENCE-TOOLS.md", out)

    def test_backup_copy_without_glob_is_ignored(self):
        """백업 사본(`.bak-`)은 원천이 아니다 — 원본 한 줄로 충분해야 한다."""
        a = self.home / "axdev/master/assets"
        a.mkdir(parents=True)
        (a / "sheet.md").write_text("x", encoding="utf-8")
        (a / "sheet.md.bak-20261111-x").write_text("x", encoding="utf-8")
        rc, out = self.run_check(HEAD + row("asset:sheet.md", "전용"))
        self.assertEqual(rc, 0, out)

    def test_all_covered_is_green(self):
        self.mkskill(".claude/skills", "alpha")
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣음"))
        self.assertEqual(rc, 0, out)
        self.assertIn("✓ asset-ledger: 초록", out)

    # ── 본부 판정표(.hq.md) ──
    def _review_item(self, name="new-checklist.md"):
        r = self.home / "axdev/master/reports/video-reviews/assets"
        r.mkdir(parents=True)
        (r / name).write_text("x", encoding="utf-8")
        self.mkskill(".claude/skills", "alpha")
        return f"path:~/axdev/master/reports/video-reviews/assets/{name}"

    def test_review_source_scanned_only_with_hq_ledger(self):
        key = self._review_item()
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣음"))
        self.assertEqual(rc, 0, out)
        self.assertIn("본부 판정표 없음", out)
        self.assertNotIn(key, out)
        self.hq.write_text(HEAD, encoding="utf-8")
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣음"))
        self.assertEqual(rc, 1, out)
        self.assertIn(key, out)

    def test_hq_rows_cover_keys_and_are_verdict_checked(self):
        key = self._review_item()
        self.hq.write_text(HEAD + row(key, "전용"), encoding="utf-8")
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣음"))
        self.assertEqual(rc, 0, out)
        self.assertIn("초록", out)
        self.assertNotIn("본부 판정표 없음", out)
        self.hq.write_text(HEAD + row(key, "아마"), encoding="utf-8")
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣음"))
        self.assertEqual(rc, 1, out)
        self.assertIn("판정 값 틀림", out)

    def test_same_key_in_public_and_hq_is_red(self):
        self.hq.write_text(HEAD + row("skill:alpha", "전용"), encoding="utf-8")
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣음"))
        self.assertEqual(rc, 1, out)
        self.assertIn("같은 키 두 줄", out)

    # ── 판정 값·팩 실재 ──
    def test_bad_verdict_is_red(self):
        self.mkskill(".claude/skills", "alpha")
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣을까"))
        self.assertEqual(rc, 1, out)
        self.assertIn("판정 값 틀림", out)

    def test_duplicate_key_is_red(self):
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣음") + row("skill:alpha", "전용"))
        self.assertEqual(rc, 1, out)
        self.assertIn("같은 키 두 줄", out)

    def test_included_skill_missing_from_pack_is_red(self):
        self.mkskill(".claude/skills", "ghost")
        rc, out = self.run_check(HEAD + row("skill:ghost", "넣음"))
        self.assertEqual(rc, 1, out)
        self.assertIn("팩에 없음", out)

    # ── 원천 없음 · 표 깨짐 ──
    def test_no_sources_is_not_green_label(self):
        rc, out = self.run_check(HEAD + row("skill:alpha", "넣음"))
        self.assertEqual(rc, 0, out)
        self.assertIn("원천 없음", out)
        self.assertNotIn("초록", out)

    def test_no_sources_still_checks_verdicts(self):
        rc, out = self.run_check(HEAD + row("skill:alpha", "아마"))
        self.assertEqual(rc, 1, out)

    def test_broken_table_is_rc2(self):
        rc, out = self.run_check("# 빈 표\n")
        self.assertEqual(rc, 2, out)
        rc, out = self.run_check(ledger=self.tmp / "absent.md")
        self.assertEqual(rc, 2, out)

    # ── 저장소 정본 판정표 ──
    def test_repo_ledger_parses_and_verdicts_valid(self):
        """정본 판정표를 원천 없는 HOME 으로 — 판정 값·팩 실재만 검사(CI 와 같은 조건)."""
        p = subprocess.run([sys.executable, str(CHECK), "--home", str(self.home)],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("원천 없음", p.stdout)
        n = sum(1 for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.startswith("| `"))
        self.assertGreaterEqual(n, 100)

    def test_repo_public_ledger_alone_and_no_hq_only_lines(self):
        """공개 판정표만으로(본부 판정표 없이) 통과 · 공개 본문에 본부 전용 표기(다계정 폴더·본부 운영 경로) 0."""
        p = subprocess.run([sys.executable, str(CHECK), "--home", str(self.home),
                            "--ledger-hq", str(self.tmp / "absent.hq.md")],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("본부 판정표 없음", p.stdout)
        body = LEDGER.read_text(encoding="utf-8")
        for bad in ("계정2", "acct2", "~/axdev"):
            self.assertNotIn(bad, body)


if __name__ == "__main__":
    unittest.main()
