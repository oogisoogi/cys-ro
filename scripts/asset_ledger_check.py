#!/usr/bin/env python3
"""우리 자산 빠짐 방지 게이트 (TICKET=cysr-1116-asset-skills-1120).

본부 원천(스킬 폴더 4곳 · master 자산 폴더 · 영상 검토 산출물 폴더)의 항목마다
판정표 docs/ASSET-LEDGER.md §4 에 한 줄이 있어야 한다. 없으면 붉음(exit 1).
판정 값은 여섯 어휘 중 하나여야 한다(아니면 붉음). 「넣음」 스킬은 팩에 실재해야 한다.
본부 판정표(공개 판정표 옆 `<이름>.hq.md` · 공개 트리 제외 파일)가 있으면 두 표를 합쳐 읽고,
그때만 본부 전용 원천(영상 검토 산출물 폴더)을 훑는다(TICKET=cysr-1116-pubcand-1120 · D1).

쓰임:
  python3 scripts/asset_ledger_check.py [--ledger PATH] [--ledger-hq PATH] [--home DIR] [--pack-skills DIR] [--json]
exit: 0 = 초록(또는 원천 없음 노랑) · 1 = 붉음 · 2 = 판정표를 읽지 못함
"""
import argparse
import json
import os
import pathlib
import re
import sys

VERDICTS = {"넣음", "넣음-자료", "팩에있음", "링크", "전용", "제외"}
SKILL_DIRS = (".claude/skills", ".claude-acct2/skills", ".cys/local/skills", ".cys/claude/skills")
ASSETS = "axdev/master/assets"
BUNDLES = ("motion-graphics-prompt", "ppt-design-system", "portrait-cutout", "video-production")
REVIEW_ASSETS = "axdev/master/reports/video-reviews/assets"
ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|(.*)\|\s*$")


def _entries(d: pathlib.Path):
    try:
        return sorted(n for n in os.listdir(d) if not n.startswith(".") and ".bak-" not in n)
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return []


def source_keys(home: pathlib.Path, hq: bool = True):
    """원천을 훑어 항목 키 집합을 낸다. 원천 폴더가 하나도 없으면 None.
    hq = 본부 판정표가 있다 — 그때만 본부 전용 원천(영상 검토 산출물)을 훑는다."""
    keys, seen_any = set(), False
    for d in SKILL_DIRS:
        p = home / d
        if p.is_dir():
            seen_any = True
        keys.update(f"skill:{n}" for n in _entries(p))
    assets = home / ASSETS
    if assets.is_dir():
        seen_any = True
        for n in _entries(assets):
            if n not in BUNDLES:  # 묶음은 안 항목 단위로 판정한다
                keys.add(f"asset:{n}")
        for b in BUNDLES:
            keys.update(f"asset:{b}/{n}" for n in _entries(assets / b))
    review = home / REVIEW_ASSETS
    if hq and review.is_dir():
        seen_any = True
        keys.update(f"path:~/{REVIEW_ASSETS}/{n}" for n in _entries(review))
    return keys if seen_any else None


def read_ledger(path: pathlib.Path):
    """§4 표의 (키, 판정) 목록. 판정 = 6번째 칸(키 다음 5번째)."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) < 7:
            continue
        rows.append((m.group(1), cells[4]))
    return rows


def covered(key: str, ledger_keys):
    for k in ledger_keys:
        if k == key or (k.endswith("*") and key.startswith(k[:-1])):
            return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    root = pathlib.Path(__file__).resolve().parent.parent
    ap.add_argument("--ledger", default=str(root / "docs/ASSET-LEDGER.md"))
    ap.add_argument("--ledger-hq", default=None, help="본부 판정표(기본 = 공개 판정표 옆 <이름>.hq.md · 없으면 공개 표만)")
    ap.add_argument("--home", default=str(pathlib.Path.home()))
    ap.add_argument("--pack-skills", default=str(root / "cysjavis-pack/skills"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        rows = read_ledger(pathlib.Path(a.ledger))
    except OSError as e:
        print(f"✗ asset-ledger: 판정표를 읽지 못함 — {e}", file=sys.stderr)
        return 2
    if not rows:
        print("✗ asset-ledger: 판정표에 항목 줄이 0 — 표 서식이 깨졌다", file=sys.stderr)
        return 2
    lp = pathlib.Path(a.ledger)
    hq_path = pathlib.Path(a.ledger_hq) if a.ledger_hq else lp.with_name(lp.name[:-3] + ".hq.md" if lp.name.endswith(".md") else lp.name + ".hq.md")
    hq = hq_path.is_file()
    if hq:
        try:
            rows += read_ledger(hq_path)
        except OSError as e:
            print(f"✗ asset-ledger: 본부 판정표를 읽지 못함 — {e}", file=sys.stderr)
            return 2
    hq_note = "" if hq else " · 본부 판정표 없음(공개 트리) — 본부 전용 원천 대조 생략"

    problems = []
    seen = {}
    for k, v in rows:
        if v not in VERDICTS:
            problems.append(f"판정 값 틀림: `{k}` = 「{v}」 (허용 = {' · '.join(sorted(VERDICTS))})")
        if k in seen:
            problems.append(f"같은 키 두 줄: `{k}`")
        seen[k] = v
    pack = pathlib.Path(a.pack_skills)
    for k, v in rows:
        if v in ("넣음", "팩에있음") and k.startswith("skill:"):
            if not (pack / k[len("skill:"):] / "SKILL.md").is_file():
                problems.append(f"판정 「{v}」 인데 팩에 없음: `{k}` ({pack.name}/{k[6:]}/SKILL.md)")

    keys = source_keys(pathlib.Path(a.home), hq)
    missing = [] if keys is None else sorted(k for k in keys if not covered(k, seen))
    problems += [f"판정표에 없는 새 항목: `{k}` — 넣음/넣음-자료/팩에있음/링크/전용/제외 중 하나로 적어라" for k in missing]

    if a.json:
        print(json.dumps({"rows": len(rows), "sources": None if keys is None else len(keys),
                          "hq": hq, "problems": problems}, ensure_ascii=False))
    else:
        for p in problems:
            print(f"✗ {p}")
    if problems:
        if not a.json:
            print(f"✗ asset-ledger: 붉음 {len(problems)}건 (판정표 {len(rows)}줄){hq_note}")
        return 1
    if keys is None:
        print(f"△ asset-ledger: 원천 없음(이 기계에 본부 폴더 0) — 판정표 서식만 확인 · {len(rows)}줄{hq_note}")
        return 0
    print(f"✓ asset-ledger: 초록 — 원천 {len(keys)}개 전부 판정표에 있음 · 판정표 {len(rows)}줄{hq_note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
