#!/usr/bin/env python3
"""1.1.9 좌석 판정 R4 뮤턴트 — 한 번에 하나 · try/finally 로 원본 복원 · cargo 와 겹쳐 돌리지 않는다.
실행: python3 mutants-r4.py <격리 실행 래퍼>   (ONLY=T2 처럼 접두로 하나만)"""
import os, subprocess, sys, re, pathlib
HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2] if "docs" in HERE.parts else pathlib.Path.cwd()
F = ROOT / "src/bin/cysd/governance.rs"
ISO = sys.argv[1]
ORIG = F.read_bytes()
src = ORIG.decode()
M = [
 ("T1 인터프리터 뿌리가 비옵션 낱말 전부를 봄(= R3 ⓑ 복귀)",
  [("        let entry_hit = entry.is_some_and(|e| entry_of(spec, e));",
    "        let entry_hit = entry.is_some_and(|e| entry_of(spec, e))\n            || (is_interpreter_name(&root_argv[0]) && root_argv[1..].iter().any(|w| !w.starts_with('-') && entry_of(spec, w)));")]),
 ("T2 Windows 규약을 문자열 내용으로 켬(= R3 판별 복귀)",
  [("    if windows {\n        let norm =", "    if windows || spec_entry.contains('\\\\') || root_entry.contains('\\\\') {\n        let norm =")]),
 ("T3 빈 인자 유실 가드 제거",
  [("        if lost_empty_value(i) {", "        if false && lost_empty_value(i) {")]),
 ("T4 값 받는 옵션 표 비움(R4 에서는 엔트리 시험이 적색이어야 한다 — 표가 유일한 방어)",
  [('    if is_shell_name(interp) {\n        return &["-o", "+o", "--rcfile", "--init-file"];\n    }\n    let n = interp.rsplit',
    '    if !interp.is_empty() || interp.is_empty() {\n        return &[];\n    }\n    let n = interp.rsplit')]),
 ("T5 가드가 뒤따르는 비옵션 낱말을 안 봄(값 자리 낱말이 후보 엔트리면 무조건 엔트리)",
  [("is_candidate(v) && rest[at + 1..].iter().all(|w| w.starts_with('-')));", "is_candidate(v));")]),
]
caught = 0; ran = 0
try:
    for name, edits in M:
        if os.environ.get("ONLY") and not name.startswith(os.environ["ONLY"]):
            continue
        ran += 1
        cur = src
        bad = [old[:50] for old, _ in edits if cur.count(old) != 1]
        if bad:
            print(name, "→ 적용 불가", bad, flush=True); continue
        for old, new in edits:
            cur = cur.replace(old, new)
        F.write_text(cur)
        p = subprocess.run([ISO, "cargo", "test", "--bin", "cysd", "--", "seat119", "v113_root"], cwd=ROOT, capture_output=True, text=True)
        txt = p.stdout + p.stderr
        failed = sorted(set(re.findall(r"^test (\S+) \.\.\. FAILED", txt, re.M)))
        res = re.findall(r"^test result: .*$", txt, re.M)
        compiled = "could not compile" not in txt
        verdict = "잡음" if (failed and compiled) else ("컴파일 실패" if not compiled else "놓침")
        caught += verdict == "잡음"
        print(f"{name} → {verdict} rc={p.returncode} {res[-1] if res else ''}\n    FAILED: {[f.split('::')[-1] for f in failed]}", flush=True)
        if not compiled:
            print("    " + "\n    ".join(l for l in txt.splitlines() if l.startswith("error"))[:600], flush=True)
finally:
    F.write_bytes(ORIG)
    print("복원:", F.read_bytes() == ORIG, flush=True)
print(f"합계 {caught}/{ran} 잡음", flush=True)
