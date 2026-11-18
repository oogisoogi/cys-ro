#!/bin/bash
# 1.1.16 후보 확정 전 전체 게이트 (TICKET=cysr-1116-integ-1118) — master 통제 실행용. 스냅샷 작업트리 뿌리에서 실행한다.
#   사용: bash docs/integ-1116/gate-1116.sh <결과 폴더>
#   GATE_DRY=1  = 실행 없이 단계 이름만 출력 · GATE_ONLY='<정규식>' = 이름이 맞는 단계만
# 규칙: 모든 대상 1회만(반복·자동 재시도 없음) · 단계 실행 중 5초마다 syspolicyd·fake 보고 수를 대조해 늘면 그 단계를 끊고 전체 중단(rc 3).
# 맥에서 돌리지 않는 것 = scripts/tests/test_release_postprocess_gate.py
#   (갓 만든 번들을 spctl·gktool 에 넘긴다 · CONTRIBUTING.md 「사람 맥에서 반복 금지」 대상) → CI 몫.
set -u
OUT=${1:?결과 폴더를 주세요}; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd); SUM="$OUT/summary.txt"; : > "$SUM"
ROOT=$(pwd); RH=$HOME; G="$RH/.claude/channels/syspolicyd-guard.sh"
DRY=${GATE_DRY:-0}; ONLY=${GATE_ONLY:-.}
PW_VENV="$RH/axdev/.wt/.gate-pw-venv"; PW="$PW_VENV/bin/python"
CHROME="$RH/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell"
BASE_DIST="$RH/axdev/.wt/cys-1116-base-1118/ui/dist"
CYS=$(command -v cys || echo /Applications/cys.app/Contents/MacOS/cys)
T=$(mktemp -d /tmp/i16XXXX); mkdir -p "$T/h" "$T/t"
BASEPATH="$RH/.cargo/bin:$RH/.bun/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ISO=(env -i "HOME=$T/h" "TMPDIR=$T/t" "PATH=$BASEPATH" "CARGO_HOME=$RH/.cargo" "RUSTUP_HOME=$RH/.rustup" CARGO_BUILD_JOBS=6 "CARGO_TARGET_DIR=$ROOT/target")
REAL=(env -i "HOME=$RH" "PATH=$BASEPATH" "CHROME_PATH=$CHROME")
say() { echo "$*" | tee -a "$SUM"; }
read -r A B <<<"$("$G" count)"
say "head=$(git rev-parse --short HEAD) pwd=$ROOT GUARD-BASE syspolicyd=$A fake=$B $(date +%T)"
if [ "$DRY" = 0 ] && [ "$ONLY" = . ] && [ -n "$(git status --short)" ]; then say "ABORT 작업트리가 깨끗하지 않음"; exit 2; fi
FAILS=0
# 프로세스 그룹으로 띄우고, 시간 초과(rc 124) · 보호 계수 증가(rc 125)면 그 그룹만 끊는다.
guarded() { /usr/bin/python3 -c '
import os,signal,subprocess,sys,time
limit,g,a,b=int(sys.argv[1]),sys.argv[2],sys.argv[3],sys.argv[4]
p=subprocess.Popen(sys.argv[5:],start_new_session=True); t0=time.time()
def stop(rc):
    try: os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError: pass
    p.wait(); sys.exit(rc)
while True:
    try: rc=p.wait(timeout=5); sys.exit(rc if rc>=0 else 128-rc)
    except subprocess.TimeoutExpired: pass
    if subprocess.run([g,"check",a,b],stdout=subprocess.DEVNULL).returncode: stop(125)
    if time.time()-t0>limit: stop(124)
' "$@"; }
# step <이름> <상한초> <명령…>
step() {
  local n=$1 lim=$2; shift 2
  [[ $n =~ $ONLY ]] || return 0
  if [ "$DRY" != 0 ]; then echo "$n"; return 0; fi
  local s=$SECONDS rc
  guarded "$lim" "$G" "$A" "$B" "$@" > "$OUT/$n.log" 2>&1; rc=$?
  local extra; extra=$(grep -E '^test result:|^ *[0-9]+ (pass|fail)$|^Ran [0-9]+ test|^(OK|FAILED)( |$)' "$OUT/$n.log" | tail -2 | cut -c1-90 | tr '\n' ' ')
  say "$n rc=$rc $((SECONDS-s))s $extra"
  [ $rc -eq 0 ] || FAILS=$((FAILS+1))
  if [ $rc -eq 125 ] || ! "$G" check "$A" "$B" >/dev/null; then say "ABORT 보호 계수 증가 — $n 에서 중단"; say "gate_rc=3"; exit 3; fi
}
cargo_step() { local n=$1; shift; step "$n" 5400 "${ISO[@]}" cargo "$@"; [[ $n =~ $ONLY ]] && [ "$DRY" = 0 ] && sleep 12; return 0; }
py_step() { local n=$1 f=$2; [ -f "$f" ] || { [[ $n =~ $ONLY ]] && say "$n 파일 없음(이 머리에 아직 안 들어옴) · 건너뜀"; return 0; }; step "$n" 1800 "${ISO[@]}" /usr/bin/python3 "$f"; }

# ── 정적·문서(빠른 것 먼저)
step gen-ceo 300 "${ISO[@]}" /usr/bin/python3 scripts/gen_ceo_template.py --check
step gen-hashes 300 "${ISO[@]}" /usr/bin/python3 scripts/gen_released_directive_hashes.py --check
step secret-scan 900 "${ISO[@]}" bash scripts/secret-scan.sh --all
step pack-secrets 300 "${ISO[@]}" bash scripts/scan-pack-secrets.sh
# ── Rust(대상마다 1회)
cargo_step build build --bins --tests
cargo_step lib test --lib -- --test-threads=4
cargo_step bin-cys test --bin cys -- --test-threads=4
cargo_step bin-cysd test --bin cysd -- --test-threads=4
cargo_step bin-seatkeep test --bin cys-seatkeep -- --test-threads=4
for t in hidden_seat_screen rotate_autorestore_hold seat_group update_drainhold_e2e win_job_exit win_pack_swap; do cargo_step "it-$t" test --test "$t" -- --test-threads=4; done
cargo_step portable-pty test --manifest-path vendor/portable-pty/Cargo.toml --lib --locked
cargo_step cys-app test -p cys-app --bin cys-app -- --test-threads=4
# ── 팩 파이썬(HANDOFF §4 와 같은 묶음 + 지침 예산 + 파리티 + 들어올 두 가지의 새 시험)
for t in test_wakeup_durable_receipt test_wakeup_liveness test_wakeup_park_failure test_refl_wakeup_expiry_attribution test_radio \
         test_computer_control test_hook_fail_log test_hook_fail_timing test_javis_counsel test_agy_door test_agy_door_phoenix_loop \
         test_agents_notes_personal_hooks test_dept_chat_inject_timeout test_phoenix_fresh_honest \
         test_bootv2_doc_contract test_event_inject test_cso_directive_rev parity_todo_decl parity_todo_scan \
         test_idle_gate test_owner_desk; do py_step "pack-$t" "cysjavis-pack/bin/tests/$t.py"; done
# ── scripts/tests(맥 제외 1건은 머리말 참조)
for f in scripts/tests/test_*.py; do b=$(basename "$f" .py); [ "$b" = test_release_postprocess_gate ] && continue; py_step "script-$b" "$f"; done
# ── 건강 검체 전량
step health 3600 "${ISO[@]}" /bin/sh -c 'exec /usr/bin/python3 cysjavis-pack/bin/tests/run_bootstrap_health.py --json > "$0"' "$OUT/health.json"
if [ "$DRY" = 0 ] && [[ health =~ $ONLY ]]; then /usr/bin/python3 - "$OUT/health.json" <<'PY' | tee -a "$SUM"
import json,sys
try:
    d=json.load(open(sys.argv[1],encoding="utf-8")); s=d["summary"]
    print("health-detail pass=%s fail=%s skip=%s total=%s fail_ids=%s"%(s["pass"],s["fail"],s["skip"],s["total"],[r["id"] for r in d["specimens"] if r["status"]=="fail"]))
except Exception as e: print("health-detail 읽기 실패:",e)
PY
fi
# ── 화면: bun test 는 CI 와 같이 node_modules 없이 먼저
step ui-test 1800 "${ISO[@]}" /bin/sh -c 'cd ui && exec bun test'
step ui-install 600 "${ISO[@]}" /bin/sh -c 'cd ui && exec bun install --frozen-lockfile'
step ui-tsc 600 "${ISO[@]}" /bin/sh -c 'cd ui && bunx -p typescript@7.0.2 tsc -v && exec bunx -p typescript@7.0.2 tsc -p tsconfig.check.json'
step ui-build 600 "${ISO[@]}" /bin/sh -c 'cd ui && exec sh build.sh'
# ── 화면 게이트(실제 번들 + 대역 · playwright 는 이 게이트 전용 venv · 브라우저는 이미 받아 둔 것)
step pw-venv 600 "${ISO[@]}" /bin/sh -c '[ -x "$0/bin/python" ] || /usr/bin/python3 -m venv "$0"; "$0/bin/python" -c "import playwright" 2>/dev/null || "$0/bin/pip" install -q "playwright==1.60.0"; exec "$0/bin/python" -c "import playwright; print(playwright.__version__)"' "$PW_VENV"
step e2e-tickrec 900 "${REAL[@]}" "BASE_DIST=$BASE_DIST" "$CYS" run -- "$PW" ui/e2e/tickrec_gate.py
for g in chat confirm cc_popover_z restart_confirm race focus seatrows pillar seatgroup rolereuse stty nodept restart hidden_block; do step "e2e-$g" 900 "${REAL[@]}" "$CYS" run -- "$PW" "ui/e2e/${g}_gate.py"; done

[ "$DRY" = 0 ] || exit 0
sleep 20; "$G" check "$A" "$B" | tee -a "$SUM"; g=${PIPESTATUS[0]}
rm -rf "$T"
say "실패 단계 수=$FAILS(기준선부터 붉은 것 포함 · 판정은 HANDOFF §11 표로)"
say "gate_rc=$(( g != 0 ? 3 : (FAILS != 0 ? 1 : 0) )) $(date +%T)"
[ $g -eq 0 ] && [ $FAILS -eq 0 ]
