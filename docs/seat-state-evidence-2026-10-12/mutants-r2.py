#!/usr/bin/env python3
"""1.1.9 좌석 판정 R2 뮤턴트 — 한 번에 하나 · try/finally 로 원본 복원 · cargo 와 겹쳐 돌리지 않는다.
실행: python3 mutants-r2.py <격리 실행 래퍼>"""
import subprocess, sys, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2] if "docs" in pathlib.Path(__file__).resolve().parts else pathlib.Path.cwd()
F = ROOT / "src/bin/cysd/governance.rs"
ISO = sys.argv[1]
ORIG = F.read_bytes()
src = ORIG.decode()
ANY = "specs.iter().any(|(_, sp)| cmdline_matches_agent_exec({}, &sp.bin_base))"
M = [
 ("R1 셸 후보 매칭 허용(엔트리 요구 삭제 = codex HIGH 되돌림)",
  "            cmdline_matches_agent_exec(a0, &spec.bin_base)\n                && matches!((&spec.entry, entry), (Some(want), Some(got)) if entry_matches(want, got))",
  "            cmdline_matches_agent_exec(a0, &spec.bin_base)"),
 ("R2 임의 낱말 매칭 허용(뿌리를 「어느 낱말이든」 으로 = codex MED 되돌림)",
  "    if descendants > 0 || root_cmd.is_some_and(|c| root_cmd_is_agent(c, specs)) {",
  "    if descendants > 0 || root_cmd.is_some_and(|c| " + ANY.format("c") + ") {"),
 ("R3 빈 셸 가드만 옛 「어느 낱말이든」 규칙",
  "        Some(argv_snapshot(&[s.pid]).remove(&s.pid).is_some_and(|c| root_cmd_is_agent(&c, &specs)))",
  "        Some(argv_snapshot(&[s.pid]).remove(&s.pid).is_some_and(|c| " + ANY.format("&c") + "))"),
 ("R4 셸 -c 묶음 뒤를 엔트리로 침",
  "            if shell && !flags.starts_with('-') && flags.contains('c') {\n                return Some((a0, None));\n            }\n",
  "            let _ = shell;\n"),
 ("R5 엔트리 비교가 늘 참",
  "                && matches!((&spec.entry, entry), (Some(want), Some(got)) if entry_matches(want, got))",
  "                && matches!((&spec.entry, entry), (Some(_), Some(_)))"),
 ("R6 인터프리터 + 엔트리 꼴(shebang 스크립트)을 안 봄",
  "            cmdline_matches_agent_exec(a0, &spec.bin_base)\n                || entry.is_some_and(|e| cmdline_matches_agent_exec(e, &spec.bin_base))",
  "            cmdline_matches_agent_exec(a0, &spec.bin_base)"),
 ("R7 판정에서 뿌리 에이전트 절 삭제(R1 라운드 M1 재확인)",
  "    if descendants > 0 || root_cmd.is_some_and(|c| root_cmd_is_agent(c, specs)) {",
  "    if descendants > 0 {"),
 ("R8 엔트리 없는 셸 후보도 엔트리 없는 뿌리와 맞음",
  "                && matches!((&spec.entry, entry), (Some(want), Some(got)) if entry_matches(want, got))",
  "                && match (&spec.entry, entry) { (Some(want), Some(got)) => entry_matches(want, got), (None, None) => true, _ => false }"),
]
out = []
try:
    for name, old, new in M:
        n = src.count(old)
        if n != 1:
            out.append((name, "적용 불가")); print(name, "→ 적용 불가", n, flush=True); continue
        F.write_text(src.replace(old, new))
        p = subprocess.run([ISO, "cargo", "test", "--bin", "cysd", "--", "seat119", "v113_root"], cwd=ROOT, capture_output=True, text=True)
        txt = p.stdout + p.stderr
        failed = sorted(set(re.findall(r"^test (\S+) \.\.\. FAILED", txt, re.M)))
        res = re.findall(r"^test result: .*$", txt, re.M)
        compiled = "could not compile" not in txt
        verdict = "잡음" if (failed and compiled) else ("컴파일 실패" if not compiled else "놓침")
        out.append((name, verdict))
        print(f"{name} → {verdict} rc={p.returncode} {res[-1] if res else ''}\n    FAILED: {[f.split('::')[-1] for f in failed]}", flush=True)
        if not compiled:
            print("    " + "\n    ".join(l for l in txt.splitlines() if l.startswith("error"))[:600], flush=True)
finally:
    F.write_bytes(ORIG)
    print("복원:", F.read_bytes() == ORIG, flush=True)
print(f"합계 {sum(1 for _, v in out if v == '잡음')}/{len(M)} 잡음", flush=True)
