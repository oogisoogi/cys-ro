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
T=$(mktemp -d /tmp/i16XXXX); mkdir -p "$T/h" "$T/t"
BASEPATH="$RH/.cargo/bin:$RH/.bun/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ISO=(env -i "HOME=$T/h" "TMPDIR=$T/t" "PATH=$BASEPATH" "CARGO_HOME=$RH/.cargo" "RUSTUP_HOME=$RH/.rustup" CARGO_BUILD_JOBS=6 "CARGO_TARGET_DIR=$ROOT/target")
REAL=(env -i "HOME=$RH" "PATH=$BASEPATH" "CHROME_PATH=$CHROME")
say() { echo "$*" | tee -a "$SUM"; }
read -r A B <<<"$("$G" count)"
say "head=$(git rev-parse --short HEAD) pwd=$ROOT GUARD-BASE syspolicyd=$A fake=$B $(date +%T)"
if [ "$DRY" = 0 ] && [ "$ONLY" = . ] && [ -n "$(git status --short)" ]; then say "ABORT 작업트리가 깨끗하지 않음"; exit 2; fi
FAILS=0
# CI 팩 단계 생성물(DRY 에서도 만든다 — 단계 이름을 보여 주려고). 판정 불가(rc 3)면 게이트 전체를 멈춘다.
CI_DIR="$T/ci"
CI_IDS=$(/usr/bin/python3 docs/integ-1116/ci_pack_steps.py emit "$CI_DIR") || { say "ABORT ci_pack_steps emit 판정 불가 — 고르는 규칙과 워크플로가 어긋남(위 stderr)"; exit 2; }
UNREG_IDS=$(/usr/bin/python3 docs/integ-1116/ci_pack_steps.py unregistered) || { say "ABORT ci_pack_steps unregistered 판정 불가"; exit 2; }
# 프로세스 그룹으로 띄우고, 시간 초과(rc 124) · 보호 계수 증가(rc 125)면 그 그룹만 끊는다. 정상 종료 뒤에도 그룹의 남은 자식을 정리한다.
guarded() { /usr/bin/python3 -c '
import os,signal,subprocess,sys,time
limit,g,a,b=int(sys.argv[1]),sys.argv[2],sys.argv[3],sys.argv[4]
p=subprocess.Popen(sys.argv[5:],start_new_session=True); t0=time.time()
def sweep():
    try: os.killpg(p.pid,signal.SIGKILL)
    except (ProcessLookupError,PermissionError): pass
def stop(rc):
    sweep(); p.wait(); sys.exit(rc)
while True:
    try: rc=p.wait(timeout=5)
    except subprocess.TimeoutExpired: rc=None
    if rc is not None:
        sweep(); sys.exit(rc if rc>=0 else 128-rc)
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
# ci_step <id> — ci_pack_steps.py 가 뽑은 CI 스텝 1개. CI 본문이 cwd 에 남기는 health-full.json 은 결과 폴더로 옮기고,
#   그 밖에 작업트리가 바뀌면 경고 1줄(CI 러너는 매번 새 checkout 이라 안 보이는 오염).
ci_step() {
  local id=$1
  step "$id" 5400 "${ISO[@]}" /bin/bash --noprofile --norc -eo pipefail "$CI_DIR/$id.sh"
  [[ $id =~ $ONLY ]] && [ "$DRY" = 0 ] || return 0
  [ -f health-full.json ] && mv -f health-full.json "$OUT/$id.health-full.json"
  local d; d=$(git status --short)
  [ -z "$d" ] || say "WARN $id 뒤 작업트리 변화: $(echo "$d" | head -5 | tr '\n' ' ')"
  return 0
}
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
# ── 팩 파이썬 = .github/workflows/ci-branch.yml 의 팩 단계 본문 그대로(정의 1곳 · 손 목록 없음 · 11-19 교훈:
#    손 목록 21개 밖 151개가 CI 에서만 붉었다). 고르는 규칙·판정 불가 조건 = docs/integ-1116/ci_pack_steps.py 머리말.
#    본문은 GitHub Actions bash 스텝과 같은 꼴(bash --noprofile --norc -eo pipefail)로 · 잡/스텝 env 는 생성물 머리 export.
#    ⚠차이(정직): 파이썬 = 이 맥 /usr/bin/python3(CI = setup-python 3.12) · 우분투 잡 본문도 이 맥에서 돈다(리눅스 아님).
step ci-pack-extract-selftest 60 "${ISO[@]}" /usr/bin/python3 docs/integ-1116/ci_pack_steps.py --self-test
step pubcand-selftest 120 "${ISO[@]}" /bin/bash docs/integ-1116/pubcand.sh --self-test
for id in $CI_IDS; do ci_step "$id"; done
# ── CI 0회 팩 시험 = lane-parity-rehearsal.sh UNREGISTERED_OK ∩ 실재 파일 − 위 CI 단계가 부르는 것(같은 정의에서 읽음)
#    격리 = CI 루프와 같은 CYS_PACK_DIR 임시 폴더 + 시험이 스스로 요구하는 JAVIS_ROOT·CYS_PROBE_RUNS(test_verify_gate·
#    test_preflight_phase1_checks 는 이 둘이 없으면 REFUSE rc 2 = 설계상 거부). test_agora_known_authentic 는 제작 맥 전용
#    (게시 zip 폴더 CYS_AGORA_ZIP_DIR 필요 · 없으면 FAIL 이 설계) — 그 env 가 이 게이트 env 에 있을 때만 돈다.
for t in $UNREG_IDS; do
  if [ "$t" = test_agora_known_authentic ] && [ -z "${CYS_AGORA_ZIP_DIR:-}" ]; then [[ unreg-$t =~ $ONLY ]] && [ "$DRY" = 0 ] && say "unreg-$t 건너뜀(CYS_AGORA_ZIP_DIR 없음 · 제작 맥 전용)"; continue; fi
  step "unreg-$t" 1800 "${ISO[@]}" "CYS_AGORA_ZIP_DIR=${CYS_AGORA_ZIP_DIR:-}" /bin/sh -c 'p=$(mktemp -d "$TMPDIR/p.XXXXXX") && j=$(mktemp -d "$TMPDIR/j.XXXXXX") && CYS_PACK_DIR="$p" JAVIS_ROOT="$j" CYS_PROBE_RUNS="$j/probe_runs.jsonl" exec /usr/bin/python3 "$0"' "cysjavis-pack/bin/tests/$t.py"
done
# ── scripts/tests(맥 제외 1건은 머리말 참조)
#    test_release_trigger_split 은 PyYAML 이 필요해 게이트 전용 venv 로 아래에서 돌린다.
for f in scripts/tests/test_*.py; do b=$(basename "$f" .py); case "$b" in test_release_postprocess_gate|test_release_trigger_split) continue;; esac; py_step "script-$b" "$f"; done
# ── 건강 검체 전량 = 위 CI 단계 boot-health-full(같은 러너 · 등재 전량)가 돌린다 · 그 결과 JSON 을 여기서 다시 읽는다
HJ=$(ls "$OUT"/*.health-full.json 2>/dev/null | head -1)
if [ "$DRY" = 0 ] && [ -n "$HJ" ]; then /usr/bin/python3 - "$HJ" <<'PY' | tee -a "$SUM"
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
# ── cys-app: tauri 빌드 입력(.gitignore 대상)이 깨끗한 스냅샷에는 없다. 시험은 내용을 쓰지 않는다.
#    tauri-build 가 binaries 를 target/debug 로 되복사하므로 0바이트 자리표시자는 금지 · 같은 내용의 APFS 복제만 쓴다(실행 안 함 · 지우지 않음).
#    target/debug/runtime 이 다른 시험에 영향을 주지 않게 cargo 시험·팩·health 뒤로 옮겼다.
step cys-app-inputs 120 "${ISO[@]}" /bin/sh -c 'set -e; t=$(rustc -vV | sed -n "s/^host: //p"); mkdir -p src-tauri/binaries src-tauri/resources src-tauri/runtime; for b in cys cysd; do [ -e "src-tauri/binaries/$b-$t" ] || cp -c "target/debug/$b" "src-tauri/binaries/$b-$t"; done; [ -e src-tauri/resources/pack.tar.gz ] || : > src-tauri/resources/pack.tar.gz; [ -e src-tauri/resources/pack-manifest.json ] || echo "{}" > src-tauri/resources/pack-manifest.json; [ -n "$(ls -A src-tauri/runtime)" ] || echo placeholder > src-tauri/runtime/GATE-PLACEHOLDER.txt; [ -f ui/dist/index.html ]; ls -la src-tauri/binaries'
cargo_step cys-app test -p cys-app --bin cys-app -- --test-threads=4
# ── 화면 게이트(실제 번들 + 대역 · playwright·PyYAML 은 이 게이트 전용 venv · 브라우저는 이미 받아 둔 것)
#    `cys run` 을 쓰지 않는다: 좌석 밖 실행은 데몬이 external 로 보고 ledger.register 를 거부한다(write-shell). 생명주기는 guarded 가 맡는다.
step pw-venv 600 "${ISO[@]}" /bin/sh -c '[ -x "$0/bin/python" ] || /usr/bin/python3 -m venv "$0"; "$0/bin/python" -c "import playwright, yaml" 2>/dev/null || "$0/bin/pip" install -q "playwright==1.60.0" "PyYAML==6.0.2"; exec "$0/bin/python" -c "import playwright, yaml; from importlib.metadata import version; print(version(\"playwright\"), yaml.__version__)"' "$PW_VENV"
step script-test_release_trigger_split 300 "${ISO[@]}" "$PW" scripts/tests/test_release_trigger_split.py
step e2e-tickrec 900 "${REAL[@]}" "BASE_DIST=$BASE_DIST" "$PW" ui/e2e/tickrec_gate.py
for g in chat confirm cc_popover_z restart_confirm race focus seatrows pillar seatgroup rolereuse stty nodept restart hidden_block; do step "e2e-$g" 900 "${REAL[@]}" "$PW" "ui/e2e/${g}_gate.py"; done

[ "$DRY" = 0 ] || { rm -rf "$T"; exit 0; }
sleep 20; "$G" check "$A" "$B" | tee -a "$SUM"; g=${PIPESTATUS[0]}
rm -rf "$T"
say "실패 단계 수=$FAILS(기준선부터 붉은 것 포함 · 판정은 HANDOFF §11 표로)"
say "gate_rc=$(( g != 0 ? 3 : (FAILS != 0 ? 1 : 0) )) $(date +%T)"
[ $g -eq 0 ] && [ $FAILS -eq 0 ]
