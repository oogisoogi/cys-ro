#!/usr/bin/env python3
"""1.1.9 좌석 판정 뮤턴트 — 한 번에 하나 · try/finally 로 원본 복원 · cargo 와 겹쳐 돌리지 않는다."""
import subprocess, sys, re, pathlib, json
ROOT = pathlib.Path(__file__).resolve().parents[2]  # 저장소 뿌리
F = ROOT / "src/bin/cysd/governance.rs"
ISO = sys.argv[1]
ORIG = F.read_bytes()
src = ORIG.decode()
M = [
 ("M1 판정에서 뿌리 에이전트 절 삭제(= v113 블록 되돌림)",
  "    if descendants > 0 || root_cmd.is_some_and(|c| known_agent_cmd(c, candidates)) {",
  "    if descendants > 0 {"),
 ("M2 존재 판정을 옛 「정확히 한 에이전트」 규칙으로(= 수리 전 재현)",
  "    candidates\n        .iter()\n        .any(|(_, bin_base)| cmdline_matches_agent_exec(cmd, bin_base))\n}",
  "    seat_agent_observed(&[cmd.to_string()], candidates)\n}"),
 ("M3 승계 판정이 Unknown 을 통과",
  "    seat == SeatState::Empty && !meta_blocks && !human_recent",
  "    seat != SeatState::Occupied && !meta_blocks && !human_recent"),
 ("M4 승계 판정이 meta 를 안 봄",
  "    seat == SeatState::Empty && !meta_blocks && !human_recent",
  "    seat == SeatState::Empty && !human_recent"),
 ("M5 판정이 종료를 안 봄",
  "    if exited {\n        return SeatState::Empty;\n    }\n    if !root_in_table {\n        return SeatState::Unknown;\n    }\n    if descendants > 0 ||",
  "    if !root_in_table {\n        return SeatState::Unknown;\n    }\n    if descendants > 0 ||"),
 ("M6 표에 없는 뿌리를 Empty 로",
  "    if !root_in_table {\n        return SeatState::Unknown;\n    }\n    if descendants > 0 ||",
  "    if !root_in_table {\n        return SeatState::Empty;\n    }\n    if descendants > 0 ||"),
 ("M7 승계 게이트가 옛 자손 유무 판정으로 우회",
  "    seat_claimable_verdict(seat_state(sys, s), meta_blocks_seat(s), human_recent)",
  "    seat_claimable_verdict(if collect_descendants(sys, s.pid).is_empty() { SeatState::Empty } else { SeatState::Occupied }, meta_blocks_seat(s), human_recent)"),
 ("M8 본체가 뿌리 argv 를 판정에 안 넘김",
  "    seat_verdict(false, true, 0, root_cmd.as_deref(), cands)",
  "    let _ = &root_cmd;\n    seat_verdict(false, true, 0, None, cands)"),
 ("M9 뿌리 관측을 옛 규칙으로",
  "    known_agent_cmd(&cmd, candidates).then_some(cmd)",
  "    seat_agent_observed(std::slice::from_ref(&cmd), candidates).then_some(cmd)"),
]
out = []
try:
    for name, old, new in M:
        n = src.count(old)
        if n != 1:
            out.append((name, f"적용 불가(일치 {n})", [])); print(name, "→ 적용 불가", n, flush=True); continue
        F.write_text(src.replace(old, new))
        p = subprocess.run([ISO, "cargo", "test", "--bin", "cysd", "--", "seat119", "v113_root", "seat_agent_observed", "select_observed"],
                           cwd=ROOT, capture_output=True, text=True)
        txt = p.stdout + p.stderr
        failed = sorted(set(re.findall(r"^test (\S+) \.\.\. FAILED", txt, re.M)))
        res = re.findall(r"^test result: .*$", txt, re.M)
        compiled = "error[" not in txt and "could not compile" not in txt
        verdict = "잡음" if (failed and compiled) else ("컴파일 실패" if not compiled else "놓침")
        out.append((name, verdict, failed))
        print(f"{name} → {verdict} rc={p.returncode} {res[-1] if res else ''}\n    FAILED: {[f.split('::')[-1] for f in failed]}", flush=True)
finally:
    F.write_bytes(ORIG)
    print("복원:", F.read_bytes() == ORIG, flush=True)
caught = sum(1 for _, v, _ in out if v == "잡음")
print(f"합계 {caught}/{len(M)} 잡음", flush=True)
