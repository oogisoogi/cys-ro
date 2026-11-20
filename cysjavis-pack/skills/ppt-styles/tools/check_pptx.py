#!/usr/bin/env python3
"""check_pptx.py — 만든 .pptx 를 표준 라이브러리만으로 점검한다(파워포인트 없이).

사용:
  python3 check_pptx.py <덱.pptx> [--slides N] [--pdf] [--strict]

  --slides N  장 수가 N 이 아니면 실패
  --pdf       LibreOffice(soffice)로 PDF 를 만들어 쪽 수 = 장 수인지 대조(없으면 설치 안내 후 코드 3)
  --strict    경고(글 넘침 의심 · 화면 밖 상자 · 빈 장 · 없는 글꼴)도 실패로 친다

점검:
  ① zip 이 온전한가(CRC) · 필수 파일([Content_Types].xml · _rels/.rels · ppt/presentation.xml)
  ② presentation.xml 의 장 목록 = 실제 장 파일 · 장마다 XML 이 읽히고 [Content_Types].xml 에 등록됐는가
  ③ 글 넘침 의심(글자 수·크기로 높이를 어림 — 실제 렌더가 아니다) · 화면 밖으로 나간 상자 · 빈 장
  ④ 덱이 쓰는 글꼴이 이 컴퓨터에 있는가(없으면 열 때 대체 글꼴로 보인다)
끝 코드: 0 통과 · 1 실패 · 2 사용법/파일 오류 · 3 --pdf 인데 LibreOffice 없음
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
EMU_PT = 12700
REQUIRED = ["[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml"]
STYLE_WORDS = ("extrabold", "heavy", "bold", "light", "regular", "medium", "thin", "otf", "ttf", "eb", "b", "l")
FONT_HELP = {
    "applesdgothicneo": "맥 기본 글꼴 — 윈도·리눅스에는 없어 맑은 고딕·Noto Sans KR 등으로 바뀌어 보입니다",
    "nanum": "네이버 나눔글꼴(OFL · 무료) — https://hangeul.naver.com/font 에서 설치",
    "maruburi": "네이버 마루 부리(OFL · 무료) — https://hangeul.naver.com/font 에서 설치",
    "jetbrainsmono": "JetBrains Mono(OFL · 무료) — https://www.jetbrains.com/lp/mono/ 에서 설치",
}


def norm_font(name):
    s = re.sub(r"[\s\-_]", "", name.lower())
    changed = True
    while changed:
        changed = False
        for w in STYLE_WORDS:
            if len(s) > len(w) + 4 and s.endswith(w):
                s, changed = s[: -len(w)], True
    return s


def font_dirs():
    h = Path.home()
    dirs = [Path("/System/Library/Fonts"), Path("/System/Library/Fonts/Supplemental"), Path("/Library/Fonts"),
            h / "Library/Fonts", Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), h / ".local/share/fonts", h / ".fonts"]
    if os.environ.get("WINDIR"):
        dirs.append(Path(os.environ["WINDIR"]) / "Fonts")
    if os.environ.get("LOCALAPPDATA"):
        dirs.append(Path(os.environ["LOCALAPPDATA"]) / "Microsoft/Windows/Fonts")
    return [d for d in dirs if d.is_dir()]


def font_files():
    out = []
    for d in font_dirs():
        for root, _, files in os.walk(d):
            for f in files:
                if f.lower().endswith((".ttf", ".otf", ".ttc")):
                    out.append(Path(root) / f)
    return out


def installed_families():
    fams = set()
    if shutil.which("fc-list"):
        try:
            r = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, timeout=30)
            for line in r.stdout.splitlines():
                for f in line.split(","):
                    if f.strip():
                        fams.add(norm_font(f.strip()))
        except Exception:
            pass
    for p in font_files():
        fams.add(norm_font(p.stem))
    return fams


def has_font(face, fams):
    n = norm_font(face)
    return any(f.startswith(n) or (len(f) >= 6 and n.startswith(f)) for f in fams)


def char_em(ch):
    o = ord(ch)
    if 0x1100 <= o <= 0x11FF or 0x3000 <= o <= 0x9FFF or 0xAC00 <= o <= 0xD7AF or 0xFF00 <= o <= 0xFFEF:
        return 0.92
    if ch == " ":
        return 0.3
    if ch.isupper() or ch.isdigit():
        return 0.62
    return 0.52


def est_height(body, w_pt):
    """글상자 하나의 글 높이를 어림(pt). 줄간 1.2 · 문단 뒤 간격 반영."""
    total = 0.0
    for p in body.findall("a:p", NS):
        size, bold, segs = None, False, [""]
        for el in p:
            tag = el.tag.split("}")[1]
            if tag in ("r", "fld"):
                rpr = el.find("a:rPr", NS)
                if rpr is not None and rpr.get("sz"):
                    size = max(size or 0, int(rpr.get("sz")) / 100)
                bold = bold or (rpr is not None and rpr.get("b") == "1")
                segs[-1] += el.findtext("a:t", default="", namespaces=NS)
            elif tag == "br":
                segs.append("")
        if size is None:
            e = p.find("a:endParaRPr", NS)
            size = int(e.get("sz")) / 100 if e is not None and e.get("sz") else 18.0
        lines = 0
        for seg in segs:
            width = sum(char_em(c) for c in seg) * size * (1.03 if bold else 1.0)
            lines += max(1, -(-int(width) // max(1, int(w_pt * 1.03))))
        after = p.find("a:pPr/a:spcAft/a:spcPts", NS)
        total += lines * size * 1.2 + (int(after.get("val")) / 100 if after is not None else 0)
    return total


def group_transform(grp, T):
    """그룹(grpSp)의 a:xfrm — off·ext(부모 좌표) · chOff·chExt(자식 좌표) — 로 자식 → 슬라이드 좌표 변환을 합성한다.
    T = (ax, bx, ay, by) · 슬라이드 x = ax·x + bx."""
    xf = grp.find("p:grpSpPr/a:xfrm", NS)
    if xf is None:
        return T
    off, ext, cho, che = (xf.find(f"a:{k}", NS) for k in ("off", "ext", "chOff", "chExt"))
    if off is None or ext is None:
        return T
    ox, oy, ex, ey = int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))
    cx, cy = (int(cho.get("x")), int(cho.get("y"))) if cho is not None else (ox, oy)
    cw, ch = (int(che.get("cx")), int(che.get("cy"))) if che is not None else (ex, ey)
    sx, sy = (ex / cw if cw else 1.0), (ey / ch if ch else 1.0)
    ax, bx, ay, by = T
    return (ax * sx, ax * (ox - cx * sx) + bx, ay * sy, ay * (oy - cy * sy) + by)


def shapes_on_slide(el, T=(1.0, 0.0, 1.0, 0.0)):
    """p:sp 를 그 도형에 걸린 그룹 변환(중첩 그룹 합성)과 함께 낸다."""
    for c in el:
        if c.tag == f"{{{NS['p']}}}sp":
            yield c, T
        elif c.tag == f"{{{NS['p']}}}grpSp":
            yield from shapes_on_slide(c, group_transform(c, T))
        else:
            yield from shapes_on_slide(c, T)


def check(path, want, strict, do_pdf):
    errs, warns = [], []
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError, IsADirectoryError) as e:
        print(f"[실패] pptx(zip)로 열리지 않습니다: {path} ({e})")
        return 2
    bad = z.testzip()
    if bad:
        errs.append(f"zip 안 파일이 깨졌습니다: {bad}")
    names = set(z.namelist())
    for r in REQUIRED:
        if r not in names:
            errs.append(f"필수 파일 없음: {r}")
    if errs:
        for e in errs:
            print(f"[실패] {e}")
        return 1
    ct = ET.fromstring(z.read("[Content_Types].xml"))
    overrides = {o.get("PartName") for o in ct.findall("ct:Override", NS)}
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
    rid = {r.get("Id"): r.get("Target") for r in rels.findall("rel:Relationship", NS)}
    sz = pres.find("p:sldSz", NS)
    W, H = (int(sz.get("cx")), int(sz.get("cy"))) if sz is not None else (9144000, 5143500)
    slides = []
    rid_attr = f"{{{NS['r']}}}id"
    for k, s in enumerate(pres.findall("p:sldIdLst/p:sldId", NS), 1):
        t = rid.get(s.get(rid_attr), "")
        if not t:
            errs.append(f"장 목록 {k}번째 항목의 관계(r:id={s.get(rid_attr)})가 presentation.xml.rels 에 없음")
            continue
        t = t.lstrip("/")
        slides.append("ppt/" + (t[4:] if t.startswith("ppt/") else t))
    # 장 목록(presentation.xml) ↔ 실제 장 파일(ppt/slides/slideN.xml) 대조 — 어긋나면 실패
    actual = {n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)}
    listed = set(slides)
    orphan = sorted(actual - listed, key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
    if orphan:
        errs.append(f"장 목록에 없는 장 파일 {len(orphan)}개: {', '.join(orphan)} — 파워포인트에서 보이지 않거나 「복구」 창이 뜬다")
    if len(listed) != len(slides):
        errs.append("장 목록에 같은 장 파일이 두 번 들어 있음")
    if not slides:
        errs.append("장 목록이 비어 있음(장 0개)")
    missing = [n for n in slides if n not in names]
    listcheck = "일치" if not orphan and not missing and slides and len(listed) == len(slides) else "불일치"
    faces = set()
    for i, name in enumerate(slides, 1):
        if name not in names:
            errs.append(f"{i}장: 목록에 있는 파일이 없음 {name}")
            continue
        if "/" + name not in overrides:
            errs.append(f"{i}장: [Content_Types].xml 에 등록 안 됨 {name}")
        try:
            root = ET.fromstring(z.read(name))
        except ET.ParseError as e:
            errs.append(f"{i}장: XML 오류 {e}")
            continue
        text_chars, pics = 0, len(root.findall(".//p:pic", NS))
        for f in root.iter():
            if f.tag.endswith("}latin") or f.tag.endswith("}ea"):
                tf = f.get("typeface")
                if tf and not tf.startswith("+"):
                    faces.add(tf)
        for sp, (ax, bx, ay, by) in shapes_on_slide(root):
            xf = sp.find("p:spPr/a:xfrm", NS)
            body = sp.find("p:txBody", NS)
            txt = "".join(t.text or "" for t in sp.iter(f"{{{NS['a']}}}t")).strip()
            text_chars += len(txt)
            if xf is None:
                continue
            off, ext = xf.find("a:off", NS), xf.find("a:ext", NS)
            # 그룹 안 도형은 그룹 변환을 적용한 슬라이드 좌표로 본다(글자 크기·안쪽 여백은 변환되지 않는다)
            x, y = ax * int(off.get("x")) + bx, ay * int(off.get("y")) + by
            w, h = ax * int(ext.get("cx")), ay * int(ext.get("cy"))
            if txt and (x < -EMU_PT or y < -EMU_PT or x + w > W * 1.005 or y + h > H * 1.005):  # 글 없는 장식 도형의 의도된 걸침은 빼고
                warns.append(f"{i}장: 상자가 화면 밖으로 나감 «{txt[:24]}» (x {x/914400:.2f}in · 오른쪽 끝 {(x+w)/914400:.2f}in / 화면 {W/914400:.2f}in)")
            if body is not None and len(txt) > 2:  # 큰 따옴표·번호 같은 1~2자 장식 글자는 빼고
                bp = body.find("a:bodyPr", NS)
                li = int(bp.get("lIns", 91440)) + int(bp.get("rIns", 91440)) if bp is not None else 182880
                ti = int(bp.get("tIns", 45720)) + int(bp.get("bIns", 45720)) if bp is not None else 91440
                need = est_height(body, (w - li) / EMU_PT)
                have = (h - ti) / EMU_PT
                if need > have * 1.15 + 2:
                    warns.append(f"{i}장: 글 넘침 의심 «{txt[:24]}…» 어림 높이 {need:.0f}pt > 상자 {have:.0f}pt")
        if text_chars == 0 and pics == 0:
            warns.append(f"{i}장: 글도 그림도 없는 빈 장")
    for t in [n for n in names if re.match(r"ppt/theme/theme\d+\.xml$", n)]:
        for f in ET.fromstring(z.read(t)).iter():
            if (f.tag.endswith("}latin") or f.tag.endswith("}ea")) and f.get("typeface"):
                faces.add(f.get("typeface"))
    faces.discard("")
    fams = installed_families()
    for face in sorted(faces):
        if not has_font(face, fams):
            hint = next((v for k, v in FONT_HELP.items() if norm_font(face).startswith(k)), "그 글꼴을 설치하거나 다른 글꼴을 쓰세요")
            warns.append(f"글꼴 없음: {face} — 이 컴퓨터에서 열면 대체 글꼴로 보입니다. {hint}")
    if want is not None and want != len(slides):
        errs.append(f"장 수 {len(slides)} ≠ 기대 {want}")
    code = 0
    if do_pdf:
        code = pdf_check(path, len(slides), faces, errs)
    for e in errs:
        print(f"[실패] {e}")
    for w_ in warns:
        print(f"[경고] {w_}")
    ok = not errs and (not strict or not warns)
    print(f"{'PASS' if ok else 'FAIL'} {Path(path).name} 장 {len(slides)} · 장 목록↔파일 {listcheck}({len(actual)}개 파일) · 글꼴 {', '.join(sorted(faces)) or '-'} · 경고 {len(warns)} · 실패 {len(errs)}")
    if code == 3:
        return 3
    return 0 if ok else 1


def find_soffice():
    for c in ("soffice", "libreoffice"):
        if shutil.which(c):
            return shutil.which(c)
    for c in ("/Applications/LibreOffice.app/Contents/MacOS/soffice", r"C:\Program Files\LibreOffice\program\soffice.exe"):
        if os.path.exists(c):
            return c
    return None


def pdf_check(path, n, faces, errs):
    so = find_soffice()
    if not so:
        print("[안내] LibreOffice(soffice)가 없어 PDF 대조를 못 했습니다. 설치: 맥 `brew install --cask libreoffice` · "
              "리눅스 `sudo apt install libreoffice-impress` · 윈도 https://www.libreoffice.org/download/")
        return 3
    prof = Path(os.environ.get("LO_PROFILE") or tempfile.mkdtemp(prefix="ppt-styles-lo-"))
    fdir = prof / "user/fonts"
    fdir.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":  # 맥 LibreOffice 는 시스템 글꼴 폴더를 못 읽는 경우가 있어 쓰는 글꼴만 프로필에 복사(이 기기 안에서만)
        want = {norm_font(f) for f in faces}
        for p in font_files():
            s = norm_font(p.stem)
            if any(s.startswith(w) or w.startswith(s) for w in want if len(s) >= 6) and not (fdir / p.name).exists():
                try:
                    shutil.copy2(p, fdir / p.name)
                except OSError:
                    pass
    out = Path(tempfile.mkdtemp(prefix="ppt-styles-pdf-"))
    r = subprocess.run([so, f"-env:UserInstallation={prof.as_uri()}", "--headless", "--convert-to", "pdf", "--outdir", str(out), str(path)],
                       capture_output=True, text=True, timeout=300)
    pdf = out / (Path(path).stem + ".pdf")
    if not pdf.exists():
        errs.append(f"LibreOffice PDF 변환 실패: {r.stderr.strip()[:200]}")
        return 1
    pages = None
    if shutil.which("pdfinfo"):
        m = re.search(r"^Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout, re.M)
        pages = int(m.group(1)) if m else None
    if pages is None:
        pages = len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf.read_bytes()))
    print(f"[pdf] {pdf} 쪽 {pages}")
    if shutil.which("pdffonts"):
        fl = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True).stdout.splitlines()[2:]
        print("[pdf 글꼴] " + " ".join(sorted({re.sub(r"^[A-Z]{6}\+", "", l.split()[0]) for l in fl if l.split()})))
    if pages != n:
        errs.append(f"PDF 쪽 수 {pages} ≠ 장 수 {n}")
    return 0


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if a else 2
    want = None
    if "--slides" in a:
        try:
            want = int(a[a.index("--slides") + 1])
        except (IndexError, ValueError):
            print("--slides 다음에 숫자를 주세요")
            return 2
    src = Path(a[0])
    if not src.is_file():
        print(f"[실패] 파일이 없습니다: {src}")
        return 2
    return check(src, want, "--strict" in a, "--pdf" in a)


if __name__ == "__main__":
    sys.exit(main())
