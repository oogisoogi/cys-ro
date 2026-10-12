#!/usr/bin/env python3
"""1.1.9 좌석 판정 R3 뮤턴트 — 한 번에 하나 · try/finally 로 원본 복원 · cargo 와 겹쳐 돌리지 않는다.
실행: python3 mutants-r3.py <격리 실행 래퍼>
Q2a(값 옵션 표 비움)는 「놓침이 아니라 갈림」 을 본다: 엔트리를 찾는 시험(…option_values_do_not_hide_the_entry)은 초록이어야 하고
(비옵션 낱말 전부를 보는 장치가 받는다) 표의 몫을 재는 시험(…the_table_drops_option_values)만 적색이어야 한다."""
import subprocess, sys, re, pathlib
HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2] if "docs" in HERE.parts else pathlib.Path.cwd()
F = ROOT / "src/bin/cysd/governance.rs"
ISO = sys.argv[1]
ORIG = F.read_bytes()
src = ORIG.decode()
TABLE = ('    if is_shell_name(interp) {\n        return &["-o", "+o", "--rcfile", "--init-file"];\n    }\n    let n = interp.rsplit',
         '    if !interp.is_empty() || interp.is_empty() {\n        return &[];\n    }\n    let n = interp.rsplit')
ALL_A = ("operands.iter().any(|w| cmdline_matches_agent_exec(w, &spec.bin_base))",
         "operands.iter().take(1).any(|w| cmdline_matches_agent_exec(w, &spec.bin_base))")
ALL_B = ("operands.iter().any(|got| entry_matches(want, got))", "operands.iter().take(1).any(|got| entry_matches(want, got))")
M = [
 ("Q1 후보 기동 문자열을 공백으로만 나눔(따옴표 해석 삭제 = R3 ① 되돌림)",
  [("        let words = cys::first_run_gates::split_shell_words(cmd);",
    "        let words: Vec<String> = cmd.split_whitespace().map(str::to_string).collect();")]),
 ("Q2a 값 받는 옵션 표 비움(비옵션 낱말 전부는 유지)", [TABLE]),
 ("Q2b 표 비움 + 비옵션 낱말을 첫째 하나만(= R3 ② 되돌림 = R2 거동)", [TABLE, ALL_A, ALL_B]),
 ("Q2c 비옵션 낱말을 첫째 하나만(표는 유지)", [ALL_A, ALL_B]),
 ("Q3 Windows 엔트리 규약 끔(= R3 ③ 되돌림)",
  [("    if windows_form(spec_entry) || windows_form(root_entry) {", "    if false && (windows_form(spec_entry) || windows_form(root_entry)) {")]),
 ("Q4 뿌리 argv 의 인자 경계를 버림(공백으로 다시 나눔)",
  [("        argv_parts_snapshot(&[root]).remove(&root)\n    };",
    "        argv_snapshot(&[root]).remove(&root).map(|c| c.split_whitespace().map(str::to_string).collect::<Vec<String>>())\n    };")]),
 ("S1 셸 후보 매칭 허용(엔트리 요구 삭제 = 1R HIGH 되돌림 재확인)",
  [("            cmdline_matches_agent_exec(a0, &spec.bin_base)\n                && spec.entry.as_deref().is_some_and(|want| operands.iter().any(|got| entry_matches(want, got)))",
    "            cmdline_matches_agent_exec(a0, &spec.bin_base)")]),
 ("S2 임의 낱말 매칭 허용(= 1R MED 되돌림 재확인)",
  [("    if descendants > 0 || root_argv.is_some_and(|a| root_cmd_is_agent(a, specs)) {",
    "    if descendants > 0 || root_argv.is_some_and(|a| specs.iter().any(|(_, sp)| cmdline_matches_agent_exec(&a.join(\" \"), &sp.bin_base))) {")]),
]
caught = 0
try:
    import os
    for name, edits in M:
        if os.environ.get('ONLY') and not name.startswith(os.environ['ONLY']):
            continue
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
        passed = sorted(set(re.findall(r"^test (\S+) \.\.\. ok", txt, re.M)))
        res = re.findall(r"^test result: .*$", txt, re.M)
        compiled = "could not compile" not in txt
        verdict = "잡음" if (failed and compiled) else ("컴파일 실패" if not compiled else "놓침")
        caught += verdict == "잡음"
        print(f"{name} → {verdict} rc={p.returncode} {res[-1] if res else ''}\n    FAILED: {[f.split('::')[-1] for f in failed]}", flush=True)
        if name.startswith("Q2a"):
            keep = [t.split('::')[-1] for t in passed if "option_values_do_not_hide_the_entry" in t]
            print(f"    (갈림 확인) 초록으로 남은 엔트리 시험: {keep}", flush=True)
        if not compiled:
            print("    " + "\n    ".join(l for l in txt.splitlines() if l.startswith("error"))[:600], flush=True)
finally:
    F.write_bytes(ORIG)
    print("복원:", F.read_bytes() == ORIG, flush=True)
print(f"합계 {caught}/{len(M)} 잡음", flush=True)
