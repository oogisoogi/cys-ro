#!/usr/bin/env python3
"""팩 스킬 설명의 상주 비용 실측 (TICKET=cysr-1112-skill-fold).

Claude Code 는 스킬마다 frontmatter 의 description(+when_to_use)을 모든 세션의
스킬 목록에 싣는다. 단 `disable-model-invocation: true` 인 스킬은 목록에 싣지 않는다
(사용자 /이름 호출 전용 · code.claude.com/docs/en/skills). 하위 폴더 안의 참조 파일
(SKILL.md 가 아닌 .md)은 목록에 오르지 않는다.

이 스크립트는 skills/<이름>/SKILL.md 의 frontmatter 만 읽어 「상주 설명 합」을 낸다.
글자 수 = 파이썬 len(str) (유니코드 코드 포인트 · 한글 1자 = 1).

쓰임:
  python3 scripts/skill_desc_budget.py [skills 폴더] [--json] [--max N]
  --max N  : 상주 합이 N 을 넘으면 exit 1 (시험·게이트용)
"""
import json
import pathlib
import sys

import yaml

DOC_CAP = 1536  # 목록 한 줄 상한(description + when_to_use) — 공식 문서


def frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end]
    try:
        data = yaml.safe_load(block) or {}
        if isinstance(data, dict):
            return data
    except yaml.YAMLError:
        pass
    # 엄격 YAML 이 아닌 frontmatter(값 안에 「: 」) — 줄 단위 `키: 값` 으로 읽는다.
    data, key = {}, None
    for line in block.splitlines():
        if line[:1].isalpha() and ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            data[key] = val.strip()
        elif key and line.strip():
            data[key] = (data[key] + " " + line.strip()).strip()
    return data


def measure(skills_dir: pathlib.Path) -> list:
    rows = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        fm = frontmatter(skill_md)
        desc = str(fm.get("description") or "")
        when = str(fm.get("when_to_use") or "")
        listed = desc + ((" " + when) if when else "")
        hidden = fm.get("disable-model-invocation") is True
        rows.append({
            "name": skill_md.parent.name,
            "chars": len(listed),
            "resident": 0 if hidden else min(len(listed), DOC_CAP),
            "disable_model_invocation": hidden,
        })
    return rows


def main(argv: list) -> int:
    args = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    cap = None
    if "--max" in argv:
        cap = int(argv[argv.index("--max") + 1])
        args = [a for a in args if a != str(cap)]
    root = pathlib.Path(args[0]) if args else (
        pathlib.Path(__file__).resolve().parent.parent / "cysjavis-pack" / "skills")
    rows = measure(root)
    total = sum(r["resident"] for r in rows)
    listed = sum(1 for r in rows if not r["disable_model_invocation"])
    if as_json:
        print(json.dumps({"skills": len(rows), "listed": listed,
                          "resident_chars": total, "rows": rows},
                         ensure_ascii=False, indent=1))
    else:
        for r in sorted(rows, key=lambda r: -r["resident"]):
            flag = " (수동 전용)" if r["disable_model_invocation"] else ""
            print(f'{r["resident"]:6d}  {r["name"]}{flag}')
        print(f"스킬 {len(rows)}개 · 목록 상주 {listed}개 · 상주 설명 합 {total}자")
    if cap is not None and total > cap:
        print(f"상한 초과: {total} > {cap}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
