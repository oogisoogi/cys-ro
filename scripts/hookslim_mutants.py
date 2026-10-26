#!/usr/bin/env python3
"""hook-slim 뮤턴트 — 핵심 줄을 하나씩 망가뜨려 시험이 적색이 되는지(KILLED) 본다. 작업 트리는 매번 원복한다.
    python3 scripts/hookslim_mutants.py            # 파이썬·셸 뮤턴트(빠름)
    python3 scripts/hookslim_mutants.py --rust     # Rust 뮤턴트 포함(cargo test --lib hookslim)
"""
import os, subprocess, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = "cysjavis-pack/hooks/"
PF = "cysjavis-pack/bin/javis_preflight.py"
GATE = '[ $# -eq 0 ] && [ -z "${CYS_SURFACE_ID:-}${JAVIS_SURFACE_ID:-}${AITERM_SURFACE_ID:-}" ] && { [ -t 0 ] || cat >/dev/null 2>&1; exit 0; }'
HOOKS = ["HOOKSLIM_ONLY=hooks", "python3", "cysjavis-pack/bin/tests/test_hook_slim.py"]
HEXIT8 = ["python3", "cysjavis-pack/bin/tests/run_bootstrap_health.py", "--only", "H-EXIT-8"]
M = [
    ("M1 cys-hook 좌석 탈출 제거", H + "cys-hook.sh",
     'if [ -z "${CYS_SURFACE_ID:-}${JAVIS_SURFACE_ID:-}${AITERM_SURFACE_ID:-}" ]; then', "if false; then", HOOKS),
    ("M2 cys-hook 좌석 키 1개만(JAVIS 누락)", H + "cys-hook.sh",
     'if [ -z "${CYS_SURFACE_ID:-}${JAVIS_SURFACE_ID:-}${AITERM_SURFACE_ID:-}" ]; then',
     'if [ -z "${CYS_SURFACE_ID:-}${AITERM_SURFACE_ID:-}" ]; then', HOOKS),
    ("M3 save-state 좌석 탈출 제거", H + "save-state.sh", GATE, ":", HOOKS),
    ("M4 inject-context 좌석 탈출 제거", H + "inject-context.sh", GATE, ":", HOOKS),
    ("M5 commit-memory-nudge 좌석 탈출 제거", H + "commit-memory-nudge.sh", GATE, ":", HOOKS),
    ("M6 grill-stop 탈출이 인자 호출도 삼킴", H + "grill-stop.sh", GATE,
     GATE.replace("[ $# -eq 0 ] && ", ""), HOOKS),
    ("M7 분리 실행 끔(항상 동기)", H + "_lib.sh", '  [ -n "$_cys_hd_hit" ] || return 1', "  return 1", HOOKS),
    ("M8 분리 잠금 해제 누락", H + "_lib.sh",
     "trap '[ -n \"${_cys_hd_held:-}\" ] && rm -rf \"$_cys_hd_held\" 2>/dev/null; _cys_hook_timing_end' EXIT",
     "trap '_cys_hook_timing_end' EXIT", HOOKS),
    ("M9 롤백 노브 무시", H + "_lib.sh", '  [ "${CYS_HOOK_STOP_SYNC:-}" = "1" ] && return 1', "  :", HOOKS),
    ("M10 save-state PreCompact 도 분리", H + "save-state.sh",
     'cys_hook_detach save-state "$0" "$INPUT" Stop && exit 0', 'cys_hook_detach save-state "$0" "$INPUT" Stop PreCompact && exit 0',
     HOOKS),
    ("M11 죽은 주인 잠금 회수 없음", H + "_lib.sh",
     '      rm -rf "$_cys_hd_l" 2>/dev/null; continue      # 죽은 주인 — 회수', '      :', HOOKS),
    ("M12 파이썬 등록 대상 개인 프로필 필터 제거", PF,
     "        targets = [t for t in targets if not _is_personal_profile_settings(t)]", "        pass", HEXIT8),
    ("M13 파이썬 신규 머신 폴백 = ~/.claude 로 회귀", PF,
     '    return ([os.path.join(account_dir, "settings.json")], None)',
     '    return ([os.path.join(os.path.expanduser("~"), ".claude", "settings.json")], None)', HEXIT8),
    ("M14 파이썬 옵트인 env 엄격 비교 깨짐", PF, '    if env_value == "1":', "    if env_value:", HEXIT8),
]
RUST = [
    ("R1 옵트인 표지 존재를 무시", "src/pack.rs", "        Ok(_) => Some(true),", "        Ok(_) => Some(false),"),
    ("R2 판독 불가를 부재로 접음", "src/pack.rs", "        Err(_) => None,\n    }\n}", "        Err(_) => Some(false),\n    }\n}"),
    ("R3 갈아끼우기 대신 전체 재직렬화", "src/factory_reset.rs",
     "        Ok(back) if back == *root => Ok(out),", "        Ok(back) if false && back == *root => Ok(out),"),
    ("R4 BOM 버림", "src/factory_reset.rs", "    if bom {\n        out.extend_from_slice", "    if false && bom {\n        out.extend_from_slice"),
    ("R5 읽기 전용 무시", "src/factory_reset.rs", "    if respect_readonly {", "    if false && respect_readonly {"),
    ("R6 CRLF 무시", "src/factory_reset.rs", 'let nl = if text.contains("\\r\\n") { "\\r\\n" } else { "\\n" };', 'let nl = "\\n";'),
]


def run(cmd):
    env = dict(os.environ)
    c = list(cmd)
    if c[0].startswith("HOOKSLIM_ONLY="):
        k, v = c.pop(0).split("=", 1)
        env[k] = v
    return subprocess.run(c, cwd=R, env=env, capture_output=True, text=True, timeout=1800).returncode


def mutate(path, old, new):
    p = os.path.join(R, path)
    src = open(p, encoding="utf-8").read()
    if src.count(old) != 1:
        return None, src
    open(p, "w", encoding="utf-8").write(src.replace(old, new))
    return p, src


killed = survived = 0
for name, path, old, new, cmd in M:
    p, src = mutate(path, old, new)
    if p is None:
        print("ERR  %s — 앵커 %d회(1이어야 함)" % (name, src.count(old))); survived += 1; continue
    try:
        rc = run(cmd)
    finally:
        open(p, "w", encoding="utf-8").write(src)
    ok = rc != 0
    killed += ok; survived += not ok
    print("%s %s" % ("KILLED  " if ok else "SURVIVED", name))
if "--rust" in sys.argv:
    for name, path, old, new in RUST:
        p, src = mutate(path, old, new)
        if p is None:
            print("ERR  %s — 앵커 %d회" % (name, src.count(old))); survived += 1; continue
        try:
            rc = run(["cargo", "test", "--lib", "hookslim"])
        finally:
            open(p, "w", encoding="utf-8").write(src)
        ok = rc != 0
        killed += ok; survived += not ok
        print("%s %s" % ("KILLED  " if ok else "SURVIVED", name))
print("뮤턴트 %d/%d KILLED" % (killed, killed + survived))
sys.exit(0 if survived == 0 else 1)
