#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_ppt_styles_render_overlap.py — ppt-styles check_pptx.py 의 렌더 실측 겹침·잘림 점검(--pdf · pdftotext)
대조군 시험(TICKET=pptstyles-overlap-review-1126 · 1.1.21 재료).

★무엇을 재나: 겹침을 일부러 넣은 대조군 2벌(CTL-A 제목↔부제 겹침 · CTL-B 본문 겹침 + 아래로 잘림)은 붉고,
  깨끗한 견본(church-navy-gold · 작은따옴표가 pdftotext 에서 &apos; 로 나옴)은 조용한가.
★LibreOffice 없이 돈다: 대조군 PDF 를 맥 LibreOffice 26 · poppler 26.07 로 한 번 그려 pdftotext -bbox-layout 출력의
  <page> 부분만 고정본(fixtures/ppt-styles-overlap/*.bbox.xml)으로 두고, subprocess.run·shutil.which 를 가로채
  render_check 에 그 출력을 먹인다. 장 글자는 같은 폴더의 대조군 pptx 에서 check_pptx.shown_text 로 읽는다.
  soffice 와 pdftotext 가 다 있는 기기에서는 끝까지 그리는 시험(E2E)도 돈다(없으면 건너뜀 · CI 는 보통 건너뜀).
★되돌리면 붉음(2026-11-26 실측): html.unescape 를 빼면 test_clean_sample_quiet 붉음(&apos; 오탐) · encoding 인자를
  빼면 test_utf8_decode_pinned 붉음 · 쪽 0개 안내를 빼면 test_pdftotext_failure_is_announced 붉음 ·
  shown_text 의 숨김/필드 제외를 빼면 test_shown_text_skips_hidden_and_fields 붉음 · 글꼴 없음 건너뜀을 빼면
  test_missing_font_skips 붉음(대체 글꼴 렌더는 LibreOffice 프로필 상태에 따라 같은 덱도 경고가 달라짐 — 실측).
★공허 방지: 대조군 고정본에 정말 겹친 낱말 상자가 있는지(교차 넓이 > 0) 먼저 단언한다.
"""
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.normpath(os.path.join(HERE, "..", ".."))
TOOL = os.path.join(PACK, "skills", "ppt-styles", "tools", "check_pptx.py")
FX = os.path.join(HERE, "fixtures", "ppt-styles-overlap")

spec = importlib.util.spec_from_file_location("check_pptx", TOOL)
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


def slide_texts(pptx):
    """대조군 pptx 의 장별 글자(check_pptx 와 같은 규칙 · 장 순서 = 파일 번호 · 대조군은 3장 순서대로)."""
    z = zipfile.ZipFile(pptx)
    names = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                   key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
    import xml.etree.ElementTree as ET
    return {i: cp.shown_text(ET.fromstring(z.read(n))) for i, n in enumerate(names, 1)}


def fake_run(stdout, rc=0, seen=None):
    def run(args, **kw):
        if seen is not None:
            seen.append((args, kw))
        return subprocess.CompletedProcess(args, rc, stdout=stdout, stderr="")
    return run


def render(name, rc=0, which="/usr/bin/pdftotext", stdout=None, subst=False, seen=None):
    if stdout is None:
        with open(os.path.join(FX, name + ".bbox.xml"), encoding="utf-8") as f:
            stdout = f.read()
    warns, buf = [], io.StringIO()
    with mock.patch.object(cp.shutil, "which", lambda c: which if c == "pdftotext" else None), \
            mock.patch.object(cp.subprocess, "run", fake_run(stdout, rc, seen)), redirect_stdout(buf):
        cp.render_check("x.pdf", slide_texts(os.path.join(FX, name + ".pptx")), warns, subst)
    return warns, buf.getvalue()


class RenderOverlap(unittest.TestCase):
    def test_fixture_not_vacuous(self):
        with open(os.path.join(FX, "ctl-a-title-subtitle-overlap.bbox.xml"), encoding="utf-8") as f:
            page1 = re.search(r"<page [^>]*>(.*?)</page>", f.read(), re.S).group(1)
        ws = [tuple(map(float, m)) for m in re.findall(r'<word xMin="([\d.-]+)" yMin="([\d.-]+)" xMax="([\d.-]+)" yMax="([\d.-]+)">', page1)]
        hit = any(min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]) for i, a in enumerate(ws) for b in ws[i + 1:])
        self.assertTrue(hit, "대조군 고정본에 겹친 낱말 상자가 없다 — 시험이 공허함")

    def test_ctl_a_overlap_red(self):
        warns, _ = render("ctl-a-title-subtitle-overlap")
        self.assertTrue(any(w.startswith("1장: 글끼리 겹침") for w in warns), warns)
        self.assertFalse(any(w.startswith(("2장", "3장")) for w in warns), warns)  # 3장 &apos; 오탐 없음

    def test_ctl_b_overlap_and_clip_red(self):
        warns, _ = render("ctl-b-body-overlap-bottom-clip")
        self.assertTrue(any(w.startswith("1장: 글끼리 겹침") for w in warns), warns)
        self.assertTrue(any(w.startswith("1장: PDF 에 안 나온 글자") for w in warns), warns)
        self.assertFalse(any(w.startswith(("2장", "3장")) for w in warns), warns)

    def test_clean_sample_quiet(self):
        warns, _ = render("clean-church-navy-gold")
        self.assertEqual(warns, [])

    def test_missing_font_skips(self):
        seen = []
        warns, out = render("ctl-a-title-subtitle-overlap", subst=True, seen=seen)
        self.assertEqual((warns, seen), ([], []))  # 대체 글꼴 렌더는 재지 않는다(pdftotext 도 안 부름)
        self.assertIn("이 컴퓨터에 없는 것이 있어 렌더 실측 겹침 점검을 건너뜁니다", out)

    def test_utf8_decode_pinned(self):
        seen = []
        render("clean-church-navy-gold", seen=seen)
        args, kw = seen[0]
        self.assertIn("-bbox-layout", args)
        self.assertEqual((args[args.index("-enc") + 1], kw.get("encoding")), ("UTF-8", "utf-8"))  # 윈도 cp949 디코드 방지
        self.assertEqual({k: kw.get(k) for k in cp.NOWIN}, cp.NOWIN)  # 윈도 콘솔 창 숨김(NOWIN) 동반

    def test_pdftotext_missing_skips(self):
        warns, out = render("ctl-a-title-subtitle-overlap", which=None)
        self.assertEqual(warns, [])
        self.assertIn("pdftotext(poppler)가 없어", out)

    def test_pdftotext_failure_is_announced(self):
        warns, out = render("ctl-a-title-subtitle-overlap", rc=99, stdout="")
        self.assertEqual(warns, [])
        self.assertIn("낱말 좌표를 내지 못해(끝 코드 99)", out)

    def test_shown_text_skips_hidden_and_fields(self):
        import xml.etree.ElementTree as ET
        a, p = cp.NS["a"], cp.NS["p"]
        x = (f'<p:spTree xmlns:a="{a}" xmlns:p="{p}">'
             '<p:sp><p:nvSpPr><p:cNvPr id="2" name="v"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>보임</a:t></a:r>'
             '<a:fld type="datetime1"><a:t>2020-01-01</a:t></a:fld></a:p></p:txBody></p:sp>'
             '<p:sp><p:nvSpPr><p:cNvPr id="3" name="h" hidden="1"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>숨김</a:t></a:r></a:p></p:txBody></p:sp>'
             '</p:spTree>')
        self.assertEqual(cp.shown_text(ET.fromstring(x)), "보임")

    def test_cap_all_not_lost(self):
        page = '<page width="720" height="405"><word xMin="10" yMin="10" xMax="60" yMax="30">HELLO</word></page>'
        warns, buf = [], io.StringIO()
        with mock.patch.object(cp.shutil, "which", lambda c: "/x/pdftotext"), \
                mock.patch.object(cp.subprocess, "run", fake_run(page)), redirect_stdout(buf):
            cp.render_check("x.pdf", {1: "hello"}, warns)
        self.assertEqual(warns, [])


@unittest.skipUnless(cp.find_soffice() and shutil.which("pdftotext") and cp.has_font("Apple SD Gothic Neo", cp.installed_families()),
                     "LibreOffice·pdftotext·대조군 글꼴(Apple SD Gothic Neo) 중 없는 것이 있음 — 끝까지 그리는 시험 건너뜀")
class RenderOverlapE2E(unittest.TestCase):
    def run_check(self, name):
        buf = io.StringIO()
        prof = tempfile.mkdtemp(prefix="ppt-overlap-lo-")
        with mock.patch.dict(os.environ, {"LO_PROFILE": prof}), redirect_stdout(buf):
            cp.check(os.path.join(FX, name + ".pptx"), None, True, True)
        shutil.rmtree(prof, ignore_errors=True)
        return buf.getvalue()

    def test_controls_red(self):
        self.assertRegex(self.run_check("ctl-a-title-subtitle-overlap"), r"\[경고\] 1장: 글끼리 겹침")
        out = self.run_check("ctl-b-body-overlap-bottom-clip")
        self.assertRegex(out, r"\[경고\] 1장: 글끼리 겹침")
        self.assertRegex(out, r"\[경고\] 1장: PDF 에 안 나온 글자")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    r = unittest.main(exit=False, verbosity=2).result
    sys.exit(0 if r.wasSuccessful() else 1)
