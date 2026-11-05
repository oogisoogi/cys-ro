#!/usr/bin/env python3
"""pptx_design_extract.py — PPT 파일 안의 실제 값(글꼴·크기·굵기·색·위치)을 읽어 디자인 분석의 근거표를 만든다.

헤이디 지침의 「화면을 보고 추측하지 말고 파일 안의 실제 값을 읽고, 근거 슬라이드 번호를 함께 적어줘」를
도구로 강제한다(LLM 이 눈대중으로 세지 않게 — 결정론 환원). 의존성 0(표준 라이브러리 · OOXML 직접 파싱).

사용:
  python3 pptx_design_extract.py <덱.pptx> [--out <폴더>]
  → <폴더>/<덱이름>.design.json (전체 원자료) + <덱이름>.design.md (분석 기준 1~4 의 숫자 근거 요약)
  .ppt(옛 형식)·.key 는 먼저 pptx 로 바꾼다: soffice --headless --convert-to pptx <파일> (키노트는 「파일 → 내보내기 → PowerPoint」)

한계(정직):
- 글자 크기·글꼴이 런(run)에 없고 레이아웃/마스터 자리표시자에서 상속되면 「상속」으로 센다(값을 지어내지 않음).
- 면적 비율(1-2)·밀도(3-8)는 도형 상자 면적 기준 근사다(실제 픽셀 아님).
- 그림 안의 색은 읽지 않는다(그림은 위치·크기만).
"""
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
EMU_PER_PT = 12700


def pt(emu):
    return round(int(emu) / EMU_PER_PT, 1)


def theme_info(z):
    names = sorted(n for n in z.namelist() if re.match(r"ppt/theme/theme\d+\.xml$", n))
    colors, fonts = {}, {}
    if not names:
        return colors, fonts
    root = ET.fromstring(z.read(names[0]))
    cs = root.find(".//a:clrScheme", NS)
    if cs is not None:
        for el in cs:
            tag = el.tag.split("}")[1]
            c = el.find("a:srgbClr", NS)
            s = el.find("a:sysClr", NS)
            if c is not None:
                colors[tag] = c.get("val").upper()
            elif s is not None:
                colors[tag] = (s.get("lastClr") or "").upper()
    fs = root.find(".//a:fontScheme", NS)
    if fs is not None:
        for kind in ("majorFont", "minorFont"):
            f = fs.find(f"a:{kind}", NS)
            if f is not None:
                lat = f.find("a:latin", NS)
                ea = f.find("a:ea", NS)
                fonts[kind] = {"latin": lat.get("typeface") if lat is not None else None,
                               "ea": ea.get("typeface") if ea is not None else None}
    return colors, fonts


SCHEME_ALIAS = {"tx1": "dk1", "tx2": "dk2", "bg1": "lt1", "bg2": "lt2"}


def color_of(el, theme):
    """solidFill 안의 색을 HEX 로. schemeClr 은 테마로 풀고 원래 이름을 괄호로 남긴다."""
    if el is None:
        return None
    c = el.find("a:srgbClr", NS)
    if c is not None:
        return c.get("val").upper()
    s = el.find("a:schemeClr", NS)
    if s is not None:
        name = s.get("val")
        hexv = theme.get(SCHEME_ALIAS.get(name, name))
        mods = [m.tag.split("}")[1] for m in s]
        tag = f"scheme:{name}" + (f"+{'/'.join(mods)}" if mods else "")
        return f"{hexv}({tag})" if hexv else tag
    return None


def slide_order(z):
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
    rid2t = {r.get("Id"): r.get("Target") for r in rels}
    out = []
    for s in pres.findall(".//p:sldIdLst/p:sldId", NS):
        t = rid2t.get(s.get(f"{{{NS['r']}}}id"))
        if t:
            out.append("ppt/" + t.lstrip("/").replace("ppt/", "") if not t.startswith("ppt/") else t)
    sz = pres.find("p:sldSz", NS)
    size = (pt(sz.get("cx")), pt(sz.get("cy"))) if sz is not None else None
    return out, size


SHAPES = ("sp", "pic", "graphicFrame", "cxnSp")
IDENT = (1.0, 0.0, 1.0, 0.0)  # 슬라이드 좌표 = (ax·x + bx, ay·y + by)


def local(el):
    return el.tag.split("}")[1] if "}" in el.tag else el.tag


def group_transform(grp, T):
    """그룹(grpSp)의 a:xfrm(off·ext = 부모 좌표 · chOff·chExt = 자식 좌표)로 자식 좌표 → 슬라이드 좌표 변환을 합성."""
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
    # 부모 좌표 = ox + (x - cx)·sx → 슬라이드 = ax·(부모) + bx
    return (ax * sx, ax * (ox - cx * sx) + bx, ay * sy, ay * (oy - cy * sy) + by)


def shapes_with_transform(el, T=IDENT):
    """도형(sp·pic·graphicFrame·cxnSp)을 그룹 변환(중첩 그룹 합성)과 함께 문서 순서로 낸다."""
    for c in el:
        tag = local(c)
        if tag in SHAPES:
            yield c, tag, T
        elif tag == "grpSp":
            yield from shapes_with_transform(c, group_transform(c, T))
        else:
            yield from shapes_with_transform(c, T)


def analyze(path):
    z = zipfile.ZipFile(path)
    theme, tfonts = theme_info(z)
    slides, size = slide_order(z)
    W, H = size if size else (720.0, 405.0)
    per = []
    agg_font = Counter()
    agg_size = Counter()
    agg_size_bold = Counter()
    agg_tcolor = Counter()
    agg_fill = Counter()
    size_slides = defaultdict(set)
    tcolor_slides = defaultdict(set)
    fill_slides = defaultdict(set)
    for idx, name in enumerate(slides, 1):
        root = ET.fromstring(z.read(name))
        s = {"no": idx, "shapes": 0, "pics": 0, "tables": 0, "charts": 0, "chars": 0, "paras": 0,
             "box_area_pt2": 0.0, "bbox": None, "bg": None, "sizes": Counter(), "radius_shapes": 0,
             "lines": 0, "shadow": 0}
        bg = root.find(".//p:bg//a:solidFill", NS)
        s["bg"] = color_of(bg, theme)
        xs = []
        for sp, tag, (ax, bx, ay, by) in shapes_with_transform(root):
            off = sp.find(".//a:off", NS)
            ext = sp.find(".//a:ext", NS)
            if off is not None and ext is not None and ext.get("cx"):
                # 그룹 안 도형은 그룹 변환을 적용해 슬라이드 좌표로(중첩 그룹 합성)
                x, y = pt(ax * int(off.get("x")) + bx), pt(ay * int(off.get("y")) + by)
                w, h = pt(ax * int(ext.get("cx"))), pt(ay * int(ext.get("cy")))
                if w > 0 and h > 0:
                    xs.append((x, y, x + w, y + h))
                    s["box_area_pt2"] += w * h
            if tag == "pic":
                s["pics"] += 1
                continue
            if tag == "cxnSp":
                s["lines"] += 1
                continue
            if tag == "graphicFrame":
                g = sp.find(".//a:graphicData", NS)
                uri = g.get("uri", "") if g is not None else ""
                if uri.endswith("/table"):
                    s["tables"] += 1
                    for tc in sp.findall(".//a:tc", NS):  # 표 칸 채움 색
                        f = color_of(tc.find("a:tcPr/a:solidFill", NS), theme)
                        if f:
                            agg_fill[f + "(표칸)"] += 1
                            fill_slides[f + "(표칸)"].add(idx)
                elif "chart" in uri:
                    s["charts"] += 1
                    continue
                else:
                    continue
            if tag == "sp":
                s["shapes"] += 1
            geom = sp.find(".//a:prstGeom", NS)
            if geom is not None and geom.get("prst") in ("roundRect", "round1Rect", "round2SameRect"):
                s["radius_shapes"] += 1
            if sp.find(".//a:effectLst/a:outerShdw", NS) is not None:
                s["shadow"] += 1
            spPr = sp.find("p:spPr", NS)
            if spPr is not None:
                f = color_of(spPr.find("a:solidFill", NS), theme)
                if f:
                    agg_fill[f] += 1
                    fill_slides[f].add(idx)
            for para in sp.findall(".//a:p", NS):
                txt = "".join(t.text or "" for t in para.findall(".//a:t", NS))
                if txt.strip():
                    s["paras"] += 1
                for r in para.findall("a:r", NS):
                    t = (r.findtext("a:t", default="", namespaces=NS) or "")
                    n = len(t.strip())
                    if not n:
                        continue
                    s["chars"] += n
                    rpr = r.find("a:rPr", NS)
                    szv = rpr.get("sz") if rpr is not None else None
                    key = f"{int(szv)/100:g}pt" if szv else "상속"
                    bold = rpr is not None and rpr.get("b") == "1"
                    s["sizes"][key] += n
                    agg_size[key] += n
                    if bold:
                        agg_size_bold[key] += n
                    size_slides[key].add(idx)
                    face = None
                    if rpr is not None:
                        for k in ("ea", "latin"):
                            e = rpr.find(f"a:{k}", NS)
                            if e is not None and e.get("typeface") and not e.get("typeface").startswith("+"):
                                face = e.get("typeface")
                                break
                    agg_font[face or "상속(테마/마스터)"] += n
                    tc = color_of(rpr.find("a:solidFill", NS), theme) if rpr is not None else None
                    tc = tc or "상속"
                    agg_tcolor[tc] += n
                    tcolor_slides[tc].add(idx)
        if xs:
            s["bbox"] = {"left": min(a[0] for a in xs), "top": min(a[1] for a in xs),
                         "right": round(W - max(a[2] for a in xs), 1), "bottom": round(H - max(a[3] for a in xs), 1)}
        s["box_ratio"] = round(min(s["box_area_pt2"] / (W * H), 9.99), 2)
        s["sizes"] = dict(s["sizes"].most_common())
        per.append(s)
    total_chars = sum(agg_size.values()) or 1

    def ev(sset, k=8):
        l = sorted(sset)
        return ",".join(map(str, l[:k])) + ("…" if len(l) > k else "")

    return {
        "file": str(path), "slide_size_pt": [W, H], "slides": len(slides),
        "theme_colors": theme, "theme_fonts": tfonts,
        "fonts_by_chars": agg_font.most_common(),
        "sizes_by_chars": [(k, v, round(v / total_chars * 100, 1), agg_size_bold.get(k, 0), ev(size_slides[k]))
                           for k, v in agg_size.most_common()],
        "text_colors_by_chars": [(k, v, ev(tcolor_slides[k])) for k, v in agg_tcolor.most_common()],
        "shape_fills_by_count": [(k, v, ev(fill_slides[k])) for k, v in agg_fill.most_common()],
        "per_slide": per,
    }


def to_md(d):
    W, H = d["slide_size_pt"]
    L = [f"# 디자인 근거표 — {Path(d['file']).name}", "",
         f"- 장 수 {d['slides']} · 크기 {W}×{H}pt(비율 {W/H:.3f}) · 도구 = pptx_design_extract.py(파일 실제 값 · 상속값은 「상속」)", ""]
    L += ["## 테마", f"- 색: " + " · ".join(f"{k} #{v}" for k, v in d["theme_colors"].items()),
          f"- 글꼴: {json.dumps(d['theme_fonts'], ensure_ascii=False)}", ""]
    L += ["## 2-1 글꼴(글자 수 가중)", "| 글꼴 | 글자 수 |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in d["fonts_by_chars"][:12]]
    L += ["", "## 2-2·2-3·2-4 크기 위계(글자 수 가중 · 굵게 글자 수 · 근거 장)", "| 크기 | 글자 수 | 비율% | 굵게 | 근거 장 |", "|---|---|---|---|---|"]
    L += [f"| {k} | {v} | {p} | {b} | {e} |" for k, v, p, b, e in d["sizes_by_chars"][:20]]
    L += ["", "## 1-3·1-5 글자 색(글자 수 가중)", "| 색 | 글자 수 | 근거 장 |", "|---|---|---|"]
    L += [f"| {k} | {v} | {e} |" for k, v, e in d["text_colors_by_chars"][:15]]
    L += ["", "## 1-1·3-5 도형 채움 색(도형 수)", "| 색 | 도형 수 | 근거 장 |", "|---|---|---|"]
    L += [f"| {k} | {v} | {e} |" for k, v, e in d["shape_fills_by_count"][:15]]
    L += ["", "## 3-1·3-8·2-7 장별(바깥 여백 pt · 상자 면적 비율 · 글자 수)",
          "| 장 | 배경 | 여백 좌/상/우/하 | 상자면적비 | 글자 | 문단 | 도형/그림/표/차트/선 | 둥근모서리 | 그림자 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in d["per_slide"]:
        b = s["bbox"] or {}
        m = "/".join(str(b.get(k, "-")) for k in ("left", "top", "right", "bottom"))
        L.append(f"| {s['no']} | {s['bg'] or '상속'} | {m} | {s['box_ratio']} | {s['chars']} | {s['paras']} | "
                 f"{s['shapes']}/{s['pics']}/{s['tables']}/{s['charts']}/{s['lines']} | {s['radius_shapes']} | {s['shadow']} |")
    ch = [s["chars"] for s in d["per_slide"]]
    if ch:
        mx = max(d["per_slide"], key=lambda s: s["chars"])
        L += ["", f"- 2-7 텍스트 양: 장당 평균 {sum(ch)/len(ch):.0f}자 · 최다 {mx['chars']}자({mx['no']}장)"]
    return "\n".join(L) + "\n"


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    src = Path(a[0])
    if "--out" in a and a.index("--out") + 1 >= len(a):
        print("--out 다음에 폴더를 주세요", file=sys.stderr)
        return 2
    if not src.is_file():
        print(f"파일이 없습니다: {src}", file=sys.stderr)
        return 2
    if src.suffix.lower() in (".ppt", ".key", ".odp"):
        print(f"{src.suffix} 는 바로 못 읽습니다 — 먼저 pptx 로 바꾸세요: soffice --headless --convert-to pptx \"{src}\" "
              "(LibreOffice 없으면 맥 `brew install --cask libreoffice` · 키노트는 「파일 → 내보내기 → PowerPoint」)", file=sys.stderr)
        return 2
    if not zipfile.is_zipfile(src):
        print(f"pptx(zip)로 열리지 않습니다: {src}", file=sys.stderr)
        return 2
    out = Path(a[a.index("--out") + 1]) if "--out" in a else src.parent
    out.mkdir(parents=True, exist_ok=True)
    d = analyze(src)
    stem = src.stem
    (out / f"{stem}.design.json").write_text(json.dumps(d, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    (out / f"{stem}.design.md").write_text(to_md(d), encoding="utf-8")
    print(f"OK {d['slides']}장 → {out / (stem + '.design.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
