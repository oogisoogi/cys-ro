#!/bin/bash
# 격리 하네스(스크립트 단위) — 후보 master-send.sh·spawn-worker.sh 를 격리 데몬 + 실 claude 좌석 1 에 그대로 태운다.
#   실 좌석·실 데몬·실 원장·실 인박스 무접촉: HOME·소켓·상태·팩 = 격리 · 원장 = MSEND_LEDGER · 인박스 = SPAWN_INBOX.
#   판정 = 대상 세션 jsonl 의 user 레코드(표식 nonce) 수 — 스크립트 자기 판정(원장 submitted)과 따로 센다.
# 사용: hs.sh <BINDIR> <라벨> <스크립트폴더(master-send.sh·spawn-worker.sh)> [단계...]
set -u
BIN=$1; LABEL=$2; SDIR=$3; shift 3
STEPS="${*:-MS3 SW1 CYC}"; PACKBIN="${PACKBIN:-$(cd "$(dirname "$0")/../.." && pwd)/cysjavis-pack/bin}"
ROOT=$HOME/hx-scratch/hs-$LABEL-$$; mkdir -p "$ROOT"/{home/.claude/channels,home/.cys/claude,pack,state,work,bin}
SOCK=$ROOT/d.sock; REALHOME="${REALHOME:-$HOME}"; PROJ=$REALHOME/.cys/claude/projects
LOG=$ROOT/run.log; : > "$LOG"
ln -s "$REALHOME/.cys/claude/projects" "$ROOT/home/.cys/claude/projects"   # 데몬 사용량 추적이 좌석 세션 파일을 찾게(읽기)
say(){ echo "[$(date +%T)] $*" | tee -a "$LOG"; }
export CYS_NO_AUTOSTART=1
# 격리 데몬으로만 가는 cys 대역(스크립트가 부르는 cys = 이것)
cat > "$ROOT/bin/cys" <<EOF
#!/bin/bash
REAL=(env -u CYS_SURFACE_ID -u CYS_ROLE CYS_SOCKET="$SOCK" CYS_STATE_DIR="$ROOT/state" CYS_PACK_DIR="$ROOT/pack" "$BIN/cys" --socket "$SOCK")
PROJ="$PROJ"; WORK="$ROOT/work"
EOF
# HS_SESSION_SHIM=1(CYCML 단계만) — 좌석이 --setting-sources project 라 세션 보고가 없어 격리 데몬 status 의
#   usage.session_file 이 빈다(→ --cycle 판정 undetermined_대상세션_미상 · 재주입 블록 미실행). 빈 칸만 좌석 프로젝트
#   폴더의 최신 jsonl 로 채운다(채운 값은 실 claude 가 /clear 때 만든 파일 · 데몬 값이 있으면 손대지 않는다).
cat >> "$ROOT/bin/cys" <<'EOF'
if [ "${1:-}" = status ] && [ "${HS_SESSION_SHIM:-0}" = 1 ]; then
  "${REAL[@]}" "$@" | python3 -c '
import json,sys,os,glob,re
proj,work=sys.argv[1:3]; raw=sys.stdin.read()
try: d=json.loads(raw)
except Exception: sys.stdout.write(raw); raise SystemExit
enc=lambda p: re.sub(r"[^A-Za-z0-9]","-",p)
for s in d.get("surfaces",[]):
    u=s.get("usage") or {}
    if u.get("session_file"): continue
    c=[f for p in {work,os.path.realpath(work)} for f in glob.glob(os.path.join(proj,enc(p),"*.jsonl"))]
    if c: u["session_file"]=max(c,key=os.path.getmtime); s["usage"]=u
print(json.dumps(d))' "$PROJ" "$WORK"
  exit "${PIPESTATUS[0]}"
fi
exec "${REAL[@]}" "$@"
EOF
chmod +x "$ROOT/bin/cys"; C="$ROOT/bin/cys"
# 실 채널의 보조 판정기(읽기 전용 사본) — 격리 HOME 안에서 격리 cys 로만 묻는다
for h in agent-alive.sh cycle-human-input-gate.sh; do cp -p "$REALHOME/.claude/channels/$h" "$ROOT/home/.claude/channels/$h"; done
set -m
env -u CYS_SURFACE_ID -u CYS_ROLE HOME="$ROOT/home" CYS_SOCKET="$SOCK" CYS_STATE_DIR="$ROOT/state" CYS_PACK_DIR="$ROOT/pack" CYS_NO_AUTORESTORE=1 "$BIN/cysd" >"$ROOT/daemon.log" 2>&1 &
DPID=$!; set +m
REF=""
cleanup(){ [ -n "$REF" ] && "$C" close-surface "$REF" >/dev/null 2>&1; kill -TERM "-$DPID" 2>/dev/null; sleep 1; kill -KILL "-$DPID" 2>/dev/null; say "cleanup dpid=$DPID"; }
trap cleanup EXIT
for i in $(seq 1 300); do "$C" identify >/dev/null 2>&1 && break; sleep 0.2; done
"$C" identify >/dev/null 2>&1 || { say "daemon not up"; exit 3; }
say "daemon pid=$DPID build=$("$C" identify 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("build_id"),d.get("version"))') scripts=$SDIR"
REF=$("$C" new-surface --agent claude --cwd "$ROOT/work" --cmd "env HOME=$REALHOME CLAUDE_CONFIG_DIR=$REALHOME/.cys/claude claude --setting-sources project --strict-mcp-config --model haiku" | grep -oE 'surface:[0-9]+' | head -1)
say "seat=$REF"
scr(){ "$C" read-screen --surface "$REF" 2>/dev/null; }
for i in $(seq 1 120); do
  s=$(scr); if echo "$s" | grep -qiE 'Syntax theme|OAuth|Select login|text style|Log in|login method'; then say "onboarding/login — 중단"; exit 4; fi
  if echo "$s" | grep -qiE 'trust the files|Do you trust'; then "$C" send-key --surface "$REF" Return >/dev/null; sleep 2; continue; fi
  echo "$s" | grep -q '❯' && echo "$s" | grep -qiE 'for shortcuts|bypass|\? for' && break; sleep 0.5; done
say "ready"
urec(){ python3 - "$PROJ" "$ROOT/work" "$1" <<'EOF'
import json,os,sys,glob
proj,cwd,needle=sys.argv[1:4]; n=0
for f in glob.glob(os.path.join(proj,'*','*.jsonl')):
    try:
        for line in open(f,encoding='utf-8',errors='replace'):
            if needle not in line: continue
            try: r=json.loads(line)
            except Exception: continue
            if r.get('type')=='user' and r.get('cwd','').startswith(cwd): n+=1
    except OSError: pass
print(n)
EOF
}
idle(){ for i in $(seq 1 90); do scr | grep -qiE 'esc to interrupt' || return 0; sleep 1; done; }
pad(){ python3 -c "import sys;n=int(sys.argv[1]);s='filler text for length measurement only please ignore this part '; print((s*80)[:n].rstrip()+'.')" "$1"; }
MSENV=(env HOME="$ROOT/home" PATH="$ROOT/bin:$PATH" MSEND_CYS="$C" MSEND_LEDGER="$ROOT/ledger.jsonl" MSEND_PROJECT_ROOTS="$PROJ" MSEND_TARGET_CWD="$ROOT/work" MSEND_MASTER_REF=surface:99990 MSEND_CSO_REF=surface:99991)
lastled(){ python3 -c 'import json,sys
L=[json.loads(l) for l in open(sys.argv[1],encoding="utf-8") if l.strip()]
r=[x for x in L if x.get("type")=="send"][-1]
print("ledger: kind=%s return=%s submitted=%s verdict_by=%s nonce=%s send_rc=%s send_err=%s"%(r.get("kind"),r.get("return"),r.get("submitted"),r.get("verdict_by"),r.get("nonce"),r.get("send_rc"),(r.get("send_err") or "")[:80]))' "$ROOT/ledger.jsonl" 2>&1; }
TOTAL=0
for st in $STEPS; do
  case $st in
    MS3)
      for k in 1 2 3; do
        idle
        case $k in
          1) B="Reply with exactly OK. (short)";;
          2) B="Reply with exactly OK. $(pad 300)";;
          3) B="Reply with exactly OK."$'\n'"second line $(pad 700)"$'\n'"third line $(pad 700)";;
        esac
        out=$("${MSENV[@]}" bash "$SDIR/master-send.sh" "$REF" "$B" 2>&1); rc=$?
        N=$(python3 -c 'import json,sys;L=[json.loads(l) for l in open(sys.argv[1],encoding="utf-8") if l.strip()];print([x for x in L if x.get("type")=="send"][-1].get("nonce",""))' "$ROOT/ledger.jsonl" 2>/dev/null)
        sleep 3; n=$(urec "[master#$N]")
        TOTAL=$((TOTAL+n))
        say "MS#$k len=${#B} rc=$rc user_records=$n | $(lastled) | $(printf '%s' "$out" | tail -1 | cut -c1-200)"
        [ "$n" = 0 ] && { say "  input: $(scr | grep '❯' | tail -1 | cut -c1-100)"; "$C" send-key --surface "$REF" C-u >/dev/null 2>&1; }
        sleep 2
      done ;;
    SW1)
      idle
      DRV="$ROOT/sw-driver.sh"
      { sed -n '1,/^log "start /p' "$SDIR/spawn-worker.sh" | sed '$d'
        cat <<'EOF'
SREF="$HS_REF"; CWD="$HS_CWD"
inject "$HS_TEXT"; r=$?
echo "INJECT rc=$r state=$INJECT_STATE"
EOF
      } > "$DRV"
      T="[SW-$(openssl rand -hex 3)] Reply with exactly OK. brief-like body $(pad 400)"
      out=$(env HOME="$ROOT/home" PATH="$ROOT/bin:$PATH" CYS="$C" ALIVE_SH="$ROOT/home/.claude/channels/agent-alive.sh" SPAWN_CH="$ROOT/home/.claude/channels" SPAWN_INBOX="$ROOT/inbox.md" CYS_CLAUDE_DIR="$REALHOME/.cys/claude" HS_REF="$REF" HS_CWD="$ROOT/work" HS_TEXT="$T" bash "$DRV" --role hs --cwd "$ROOT/work" 2>&1); rc=$?
      sleep 3; n=$(urec "${T:0:10}"); TOTAL=$((TOTAL+n))
      say "SW inject rc=$rc user_records=$n | $(printf '%s' "$out" | grep -E 'INJECT|⚠|주입|자체' | tail -3 | tr '\n' ' ' | cut -c1-260)"
      [ "$n" = 0 ] && { say "  input: $(scr | grep '❯' | tail -1 | cut -c1-100)"; "$C" send-key --surface "$REF" C-u >/dev/null 2>&1; }
      sleep 2 ;;
    PY3)
      # 팩 2단계 호출 3곳의 실 러너 그대로(같은 Python 부모) — autopilot.run ×2(순환 자동기·확인기 꼴) + HUD 다리 subprocess 꼴 ×1
      for k in 1 2 3; do
        idle; T="[PY-$(openssl rand -hex 3)] Reply with exactly OK. $(pad 300)"
        out=$(env HOME="$ROOT/home" PATH="$ROOT/bin:$PATH" PACKBIN="$PACKBIN" HS_REF="$REF" HS_T="$T" HS_K="$k" python3 - <<'PYH' 2>&1
import os,sys,subprocess
sys.path.insert(0,os.environ["PACKBIN"])
import javis_cycle_autopilot as ap
ref,t,k=os.environ["HS_REF"],os.environ["HS_T"],os.environ["HS_K"]
if k in ("1","2"):
    r1=ap.run([ap.CYS,"send","--surface",ref,t]); r2=ap.run([ap.CYS,"send-key","--surface",ref,"Return"])
    print("autopilot.run send rc=%s send-key rc=%s"%(r1[0],r2[0]))
else:
    r1=subprocess.run(["cys","send","--surface",ref,"--",t],capture_output=True,text=True,timeout=10,stdin=subprocess.DEVNULL)
    r2=subprocess.run(["cys","send-key","--surface",ref,"Return"],capture_output=True,text=True,timeout=10,stdin=subprocess.DEVNULL)
    print("hud-form send rc=%s send-key rc=%s"%(r1.returncode,r2.returncode))
PYH
)
        sleep 8; n=$(urec "${T:0:10}"); TOTAL=$((TOTAL+n))
        say "PY#$k user_records=$n | $out"
        [ "$n" = 0 ] && { say "  input: $(scr | grep '❯' | tail -1 | cut -c1-100)"; "$C" send-key --surface "$REF" C-u >/dev/null 2>&1; }
      done ;;
    CYC)
      idle
      printf '%s\n' "[master] cycle restore pointer test — reply with exactly RESTORED." > "$ROOT/tpl.md"
      out=$("${MSENV[@]}" MSEND_FORCE_CYCLE=1 MSEND_CYCLE_TEMPLATE="$ROOT/tpl.md" GATE_CYS="$C" GATE_PROJECT_ROOTS="$PROJ" MSEND_FORCE_HUMAN_GATE=1 bash "$SDIR/master-send.sh" --cycle "$REF" 2>&1); rc=$?
      say "CYC rc=$rc restored_records=$(urec RESTORED) | $(lastled) | $(printf '%s' "$out" | grep -E '순환 판정|복원 재주입|제출=' | tr '\n' ' ' | cut -c1-300)" ;;
    CYCML)
      # 복원 재주입 블록 실좌석(master#47eb5e7f) — 실 순환과 같은 여러 줄 템플릿(화면엔 접힌 붙여넣기) + 재개 줄
      idle
      { printf '%s\n' "[master] cycle restore pointer test (multi-line) — do nothing else."
        for i in 1 2 3 4 5 6 7 8 9 10; do printf '%s\n' "$i. filler restore line $(pad 90)"; done
        printf '%s\n' "Reply with exactly RESTORED."; } > "$ROOT/tpl-ml.md"
      out=$("${MSENV[@]}" HS_SESSION_SHIM=1 MSEND_FORCE_CYCLE=1 MSEND_CYCLE_TEMPLATE="$ROOT/tpl-ml.md" MSEND_CYCLE_RESUME="reply RESTORED only" GATE_CYS="$C" GATE_PROJECT_ROOTS="$PROJ" MSEND_FORCE_HUMAN_GATE=1 bash "$SDIR/master-send.sh" --cycle "$REF" 2>&1); rc=$?
      RN=$(python3 -c 'import json,sys;L=[json.loads(l) for l in open(sys.argv[1],encoding="utf-8") if l.strip()];r=[x for x in L if x.get("kind")=="cycle_reinject"];print(r[-1].get("nonce","") if r else "")' "$ROOT/ledger.jsonl" 2>/dev/null)
      sleep 3
      say "CYCML rc=$rc reinject_nonce_user_records=$(urec "[master#${RN:-none}]") | $(python3 -c 'import json,sys
L=[json.loads(l) for l in open(sys.argv[1],encoding="utf-8") if l.strip()]
c=[x for x in L if x.get("kind")=="cycle"][-1:]; r=[x for x in L if x.get("kind")=="cycle_reinject"][-1:]
print("cycle: submitted=%s cycle_verified=%s %s->%s | reinject=%s verdict_by=%s err=%s nonce=%s"%(c[0].get("submitted") if c else None,c[0].get("cycle_verified") if c else None,c[0].get("session_before") if c else None,c[0].get("session_after") if c else None,r[0].get("reinject") if r else None,r[0].get("verdict_by") if r else None,r[0].get("error_detail") if r else None,r[0].get("nonce") if r else None))' "$ROOT/ledger.jsonl" 2>&1) | $(printf '%s' "$out" | grep -E '순환 판정|복원 재주입' | tr '\n' ' ' | cut -c1-300)"
      say "  screen: $(scr | grep -E 'Pasted|RESTORED|master#' | tail -3 | tr '\n' ' ' | cut -c1-200)" ;;
  esac
done
say "TOTAL user_records(MS+SW)=$TOTAL"
say "ROOT=$ROOT"
