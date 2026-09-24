#!/usr/bin/env python3
"""v116_num_mutants.py — TICKET=v116-num ②데몬 층 뮤테이션 검산(설계 docs/design/surface-display-number.md §9).

대상 뮤턴트(설계 표 번호 그대로): M1~M14 · M11b~M11e · M20 · M21 · M24 · M26.
(M15~M19 · M22 · M23 · M25 는 ③표시 층 — 그 티켓의 실행기가 진다.)
각 뮤턴트: 치환 목록의 **각 항목이 정확히 1곳**(건수 assert) → 그 결함의 시험 명령 → **종료코드**로 판정 → finally 원복.
어휘: KILLED=적색(잡음 · 실패한 시험 이름 병기) · SURVIVED=공허 · NOT-APPLIED=변이 미적용 ·
      CRASH=컴파일 실패(측정 무효 — 실패와 같은 급).
exit: 0=대조군 초록 ∧ 전 뮤턴트 KILLED · 1=SURVIVED 있음 · 2=측정 실패.
사용: python3 scripts/v116_num_mutants.py [뮤턴트 이름 접두 …]   (인자 없으면 전부)
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARGO = os.environ.get("CARGO", os.path.expanduser("~/.cargo/bin/cargo"))
STATE = "src/bin/cysd/state.rs"
RECALL = "src/bin/cysd/recall.rs"
HANDLERS = "src/bin/cysd/handlers.rs"
LIB = "src/lib.rs"
T_STATE = [CARGO, "test", "--bin", "cysd", "v116_num_tests"]
T_RPC = [CARGO, "test", "--bin", "cysd", "v116_num_rpc_tests"]
T_RECALL = [CARGO, "test", "--bin", "cysd", "recall::tests::t10"]
T_RECALL_SEED = [CARGO, "test", "--bin", "cysd", "recall::tests::max_surface_id"]
T_LIB = [CARGO, "test", "--lib", "display_ref_grammar"]

INS_OLD = """        match crate::recall::surface_numbers_insert(
            &self.socket_path,
            id,
            grant.display_no,
            now_epoch(),
        ) {"""
INS_NEW = """        let ins_late = (id, grant.display_no, now_epoch());
        match Ok::<(), crate::recall::NumbersWriteErr>(()) {"""
PTY_OLD = """            .map_err(|e| format!("openpty failed: {e}"))?;
"""
PTY_NEW = """            .map_err(|e| format!("openpty failed: {e}"))?;
        let _ = crate::recall::surface_numbers_insert(&self.socket_path, ins_late.0, ins_late.1, ins_late.2);
"""
NUMBERS_PATH = 'let path = state_dir(socket_path).join("transcripts.db");'
SHARED_PATH = 'let path = std::env::temp_dir().join("cys-v116-shared-numbers.db");'

MUTANTS = [
    # (이름, 파일, [(찾을 문자열(정확히 1곳), 바꿀 문자열)…], 시험 명령)
    ("M1-산좌석검사제거", STATE,
     [("Some(Holder { state: HolderState::Live, .. }) => true,",
       "Some(Holder { state: HolderState::Live, .. }) => false,")], T_STATE),
    ("M2-W검사제거", STATE,
     [("Some(Holder { state: HolderState::Closed(t), .. }) => now - *t < w,",
       "Some(Holder { state: HolderState::Closed(_t), .. }) => { let _ = w; false }")], T_STATE),
    ("M3-경계<를<=로", STATE,
     [("Some(Holder { state: HolderState::Closed(t), .. }) => now - *t < w,",
       "Some(Holder { state: HolderState::Closed(t), .. }) => now - *t <= w,")], T_STATE),
    ("M4-후보=직전+1(빈자리첫번호)", STATE,
     [("    let c = display_candidate(id);", "    let c: u16 = 1;")], T_STATE),
    ("M5-999뒤1로안돎", STATE,
     [("        let n = (c - 1 + k) % max + 1;", "        let n = c + k;\n        if n > max {\n            break;\n        }")],
     T_STATE),
    ("M6-I1보호제거(탐색)", STATE,
     [("        return DisplayPick::I1Guard;", "        let _ = DisplayPick::I1Guard;")], T_STATE),
    ("M7-spawn_failed도막힘", STATE,
     [("""        if r.close_kind.as_deref() == Some("spawn_failed") {
            continue;
        }
        let Some(n) = r.display_no else { continue };""",
       """        let Some(n) = r.display_no else { continue };""")], T_STATE),
    ("M8-음수경과를오래됨으로", STATE,
     [("Some(Holder { state: HolderState::Closed(t), .. }) => now - *t < w,",
       "Some(Holder { state: HolderState::Closed(t), .. }) => now - *t >= 0.0 && now - *t < w,")], T_STATE),
    ("M9-시드에서surface_numbers제거", RECALL,
     [('("surface_numbers", "SELECT COALESCE(MAX(surface_id), 0) FROM surface_numbers"),',
       '("surface_numbers", "SELECT 0"),')], T_STATE),
    ("M9b-시드에서surface_numbers제거(recall회귀)", RECALL,
     [('("surface_numbers", "SELECT COALESCE(MAX(surface_id), 0) FROM surface_numbers"),',
       '("surface_numbers", "SELECT 0"),')], T_RECALL_SEED),
    ("M10-부팅고아처리제거(영구막힘)", STATE,
     [("                state: HolderState::Closed(r.closed_at.unwrap_or(boot_now)),",
       "                state: match r.closed_at {\n                    Some(t) => HolderState::Closed(t),\n                    None => HolderState::Live,\n                },")],
     T_STATE),
    ("M11-INSERT를PTY뒤로", STATE, [(INS_OLD, INS_NEW), (PTY_OLD, PTY_NEW)], T_STATE),
    ("M11b-시드실패를경보없이0으로", RECALL,
     [('                alarms.push(("seed_failed", format!("open {}: {e}", path.display())));',
       '                let _ = e;'),
      ('        alarms.push(("seed_failed", failed.join("; ")));', '        let _ = &failed;')], T_STATE),
    ("M11c-표만들기전에3갈래UNION시드", RECALL,
     [("    let conn = match open_db(&path) {", "    let conn = match Connection::open(&path) {"),
      ('("lines", "SELECT COALESCE(MAX(surface_id), 0) FROM lines"),',
       '("lines", "SELECT MAX(m) FROM (SELECT COALESCE(MAX(surface_id),0) m FROM lines UNION ALL SELECT COALESCE(MAX(surface_id),0) FROM chains UNION ALL SELECT COALESCE(MAX(surface_id),0) FROM surface_numbers)"),'),
      ('("chains", "SELECT COALESCE(MAX(surface_id), 0) FROM chains"),', '("chains", "SELECT 0 FROM surface_numbers"),'),
      ], T_STATE),
    ("M11d-⑴에서새표만만듦", RECALL,
     [("    let conn = match open_db(&path) {",
       '    let conn = match Connection::open(&path).and_then(|c| c.execute_batch("CREATE TABLE IF NOT EXISTS surface_numbers(surface_id INTEGER PRIMARY KEY, display_no INTEGER, created_at REAL NOT NULL, closed_at REAL, close_kind TEXT, socket TEXT NOT NULL);").map(|_| c)) {')],
     T_STATE),
    ("M11e-고아UPDATE실패때스냅샷버림", RECALL,
     [('            alarms.push(("write_io", format!("boot_orphan update: {e}")));',
       '            alarms.push(("write_io", format!("boot_orphan update: {e}")));\n            return NumbersBoot { seed: 0, rows: Vec::new(), alarms };')],
     T_STATE),
    ("M12-parse_surface_ref가#를벗김", LIB,
     [('    let t = t.strip_prefix("surface:").unwrap_or(t);',
       '    let t = t.strip_prefix("surface:").unwrap_or(t).trim_start_matches(\'#\');')], T_RPC),
    ("M12b-parse_surface_ref가#를벗김(lib)", LIB,
     [('    let t = t.strip_prefix("surface:").unwrap_or(t);',
       '    let t = t.strip_prefix("surface:").unwrap_or(t).trim_start_matches(\'#\');')], T_LIB),
    ("M13-surface.close가display_no를받음", HANDLERS,
     [('        "surface.close" => {', '        "surface.close" => {\n            let _dn = params.get("display_no");')], T_RPC),
    ("M14-다찼을때생성거부", STATE,
     [("        let id = grant.id;\n", "        let id = grant.id;\n        if grant.display_no.is_none() {\n            return Err(\"display exhausted\".into());\n        }\n")],
     T_STATE),
    ("M20-prune이대응표삭제", RECALL,
     [("    *last_prune = Some(std::time::Instant::now());",
       '    *last_prune = Some(std::time::Instant::now());\n    let _ = conn.execute("DELETE FROM surface_numbers", []);')], T_RECALL),
    ("M21-대응표공용경로", RECALL,
     # 부팅·INSERT·닫기 세 함수의 경로 줄을 전부 공용 파일로 — 순서대로 1곳씩 치환(같은 줄 3회)
     [(NUMBERS_PATH + "\n    let mut alarms", SHARED_PATH + "\n    let mut alarms"),
      (NUMBERS_PATH + "\n    let conn = Connection::open(&path).map_err(|e| NumbersWriteErr::Io",
       SHARED_PATH + "\n    let conn = Connection::open(&path).map_err(|e| NumbersWriteErr::Io"),
      (NUMBERS_PATH + "\n    let conn = Connection::open(&path).map_err(|e| e.to_string())?;\n    conn.execute(\n        \"UPDATE",
       SHARED_PATH + "\n    let conn = Connection::open(&path).map_err(|e| e.to_string())?;\n    conn.execute(\n        \"UPDATE")],
     T_STATE),
    ("M24-쓰기실패를생성실패로", STATE,
     [("""            Err(crate::recall::NumbersWriteErr::Io(e)) => {
                self.numbers_alarm("write_io", Some(id), Some(&e));
            }""",
       """            Err(crate::recall::NumbersWriteErr::Io(e)) => {
                self.numbers_alarm("write_io", Some(id), Some(&e));
                return Err(e);
            }""")], T_STATE),
    ("M26-번호정지제거", STATE,
     [("        if self.suspended {\n            return (None, None, None);\n        }",
       "        if self.suspended && false {\n            return (None, None, None);\n        }")], T_STATE),
]


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, errors="replace",
                       env={k: v for k, v in os.environ.items() if not k.startswith("CYS_")})
    return r.returncode, r.stdout + r.stderr


# 컴파일 실패는 「시험이 잡았다」가 아니다 — 측정 무효(CRASH)로 따로 센다(공짜 KILLED 배제).
CRASH_MARKS = ("could not compile", "error[E")


def evidence(out):
    """적색 귀속 근거 — 실패한 시험 이름들(cargo)."""
    names = [ln.strip()[5:-10] for ln in out.splitlines()
             if ln.strip().startswith("test ") and ln.strip().endswith("FAILED")]
    return ", ".join(n.split("::")[-1] for n in names[:4]) or "(근거 줄 없음)"


def main():
    sel = sys.argv[1:]
    todo = [m for m in MUTANTS if not sel or any(m[0].startswith(s) for s in sel)]
    for cmd in {tuple(m[3]) for m in todo}:
        rc, _ = run(list(cmd))
        print("CONTROL %s rc=%d → %s" % (" ".join(cmd[-2:]), rc, "GREEN" if rc == 0 else "RED(측정 실패)"),
              flush=True)
        if rc != 0:
            return 2
    bad = 0
    for name, rel, reps, cmd in todo:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as f:
            orig = f.read()
        cur = orig
        applied = True
        for old, new in reps:
            n = cur.count(old)
            if n != 1:
                print("%s: NOT-APPLIED(count=%d · %r…)" % (name, n, old[:60]), flush=True)
                applied = False
                break
            cur = cur.replace(old, new)
        if not applied:
            bad = 2
            continue
        mode = os.stat(path).st_mode
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(cur)
            rc, out = run(cmd)
            if rc != 0 and any(m in out for m in CRASH_MARKS):
                v = "CRASH(측정 무효)"
                bad = 2
                print(out[-1500:])
            else:
                v = "KILLED" if rc != 0 else "SURVIVED"
                if v == "SURVIVED" and bad == 0:
                    bad = 1
            print("%s: rc=%d %s · %s" % (name, rc, v, evidence(out) if rc else "-"), flush=True)
        finally:
            with open(path, "w", encoding="utf-8") as f:
                f.write(orig)
            os.chmod(path, mode)
        with open(path, encoding="utf-8") as f:
            assert f.read() == orig, "원복 실패: " + rel
    print("원복 확인: 대상 파일 바이트 동일", flush=True)
    return bad


if __name__ == "__main__":
    sys.exit(main())
