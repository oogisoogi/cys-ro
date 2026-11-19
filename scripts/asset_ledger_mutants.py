#!/usr/bin/env python3
"""asset_ledger_mutants.py — 빠짐 방지 게이트(scripts/asset_ledger_check.py)의 뮤테이션 검산
(TICKET=cysr-1116-asset-skills-1120).

각 뮤턴트: 검사기의 한 곳을 정확히 1번 바꾼다(건수 assert) → 시험(scripts/tests/test_asset_ledger_check.py)
→ 종료코드로 판정 → finally 원복.
어휘: KILLED=시험이 적색(잡음) · SURVIVED=시험이 못 잡음(공허) · NOT-APPLIED=변이 미적용.
exit: 0=대조군 초록 ∧ 전 뮤턴트 KILLED · 1=SURVIVED/NOT-APPLIED 있음 · 2=대조군 적색(측정 실패).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "scripts", "asset_ledger_check.py")
TEST = [sys.executable, os.path.join(ROOT, "scripts", "tests", "test_asset_ledger_check.py")]

MUTANTS = [
    ("M1 원천 대조를 끈다(누락 목록 항상 빈)",
     "missing = [] if keys is None else sorted(k for k in keys if not covered(k, seen))",
     "missing = []"),
    ("M2 스킬 폴더 4곳 중 계정2를 뺀다",
     'SKILL_DIRS = (".claude/skills", ".claude-acct2/skills", ".cys/local/skills", ".cys/claude/skills")',
     'SKILL_DIRS = (".claude/skills", ".cys/local/skills", ".cys/claude/skills")'),
    ("M3 자산 묶음 안을 훑지 않는다",
     '            keys.update(f"asset:{b}/{n}" for n in _entries(assets / b))',
     "            pass"),
    ("M4 영상 검토 산출물 폴더를 훑지 않는다",
     '        keys.update(f"path:~/{REVIEW_ASSETS}/{n}" for n in _entries(review))',
     "        pass"),
    ("M5 판정 값 검사를 끈다",
     "        if v not in VERDICTS:",
     "        if False:"),
    ("M6 「넣음」 팩 실재 검사를 끈다",
     '        if v in ("넣음", "팩에있음") and k.startswith("skill:"):',
     "        if False:"),
    ("M7 접두 덮기(*)를 모든 키 덮기로 넓힌다",
     'if k == key or (k.endswith("*") and key.startswith(k[:-1])):',
     'if k == key or k.endswith("*"):'),
    ("M8 원천 없음을 초록으로 접는다",
     "    return keys if seen_any else None",
     "    return keys"),
    ("M9 빈 판정표를 통과시킨다",
     "    if not rows:\n",
     "    if False:\n"),
    ("M10 같은 키 두 줄을 허용한다",
     "        if k in seen:",
     "        if False:"),
    ("M11 백업 사본 제외를 끈다",
     ' and ".bak-" not in n)',
     ")"),
]


def run_tests():
    p = subprocess.run(TEST, capture_output=True, text=True, encoding="utf-8", timeout=300)
    return p.returncode, (p.stdout + p.stderr)


def main(argv):
    want = argv[1:]
    orig = open(TARGET, encoding="utf-8").read()
    rc, out = run_tests()
    if rc != 0:
        print("대조군 적색 — 측정 실패\n" + out[-2000:])
        return 2
    print("대조군: 초록")
    bad = 0
    for name, old, new in MUTANTS:
        if want and not any(name.startswith(w) for w in want):
            continue
        n = orig.count(old)
        if n != 1:
            print(f"NOT-APPLIED  {name} (일치 {n}곳)")
            bad += 1
            continue
        try:
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(orig.replace(old, new))
            rc, out = run_tests()
        finally:
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(orig)
        if rc != 0:
            failed = [l.split(" ")[1] for l in out.splitlines() if l.startswith(("FAIL:", "ERROR:"))]
            print(f"KILLED       {name} ← {', '.join(failed[:3]) or '시험 적색'}")
        else:
            print(f"SURVIVED     {name}")
            bad += 1
    assert open(TARGET, encoding="utf-8").read() == orig, "원복 실패"
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
