#!/bin/bash
# 격리 하네스(사전 측정) — 발신 꼴별 제출 여부를 대상 세션 jsonl user 레코드로 판정. 실 좌석·실 데몬 무접촉.
# 사용: hx.sh <BINDIR(cys·cysd 가 있는 폴더)> <라벨> [케이스...]
set -u
BIN=$1; LABEL=$2; shift 2
CASES="${*:-C52 C300 E300 EML D300 F300}"
CYS=$BIN/cys; CYSD=$BIN/cysd
ROOT=$HOME/hx-scratch/hx-$LABEL-$$; mkdir -p "$ROOT"/{home,pack,state,work}
SOCK=$ROOT/d.sock; REALHOME="${REALHOME:-$HOME}"
PROJ=$REALHOME/.cys/claude/projects
LOG=$ROOT/run.log; : > "$LOG"
say(){ echo "[$(date +%T)] $*" | tee -a "$LOG"; }
export CYS_NO_AUTOSTART=1
c(){ env -u CYS_SURFACE_ID -u CYS_ROLE HOME="$ROOT/home" CYS_SOCKET="$SOCK" CYS_STATE_DIR="$ROOT/state" CYS_PACK_DIR="$ROOT/pack" "$CYS" --socket "$SOCK" "$@"; }
set -m
env -u CYS_SURFACE_ID -u CYS_ROLE HOME="$ROOT/home" CYS_SOCKET="$SOCK" CYS_STATE_DIR="$ROOT/state" CYS_PACK_DIR="$ROOT/pack" CYS_NO_AUTORESTORE=1 "$CYSD" >"$ROOT/daemon.log" 2>&1 &
DPID=$!; set +m
REF=""
cleanup(){ [ -n "$REF" ] && c close-surface "$REF" >/dev/null 2>&1; kill -TERM "-$DPID" 2>/dev/null; sleep 1; kill -KILL "-$DPID" 2>/dev/null; say "cleanup dpid=$DPID"; }
trap cleanup EXIT
for i in $(seq 1 300); do c identify >/dev/null 2>&1 && break; sleep 0.2; done
c identify >/dev/null 2>&1 || { say "daemon not up"; tail -20 "$ROOT/daemon.log"; exit 3; }
say "daemon pid=$DPID build=$(c identify 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("build_id"),d.get("version"))')"
REF=$(c new-surface --agent claude --cwd "$ROOT/work" --cmd "env HOME=$REALHOME CLAUDE_CONFIG_DIR=$REALHOME/.cys/claude claude --setting-sources project --strict-mcp-config --model haiku" | grep -oE 'surface:[0-9]+' | head -1)
say "seat=$REF"
scr(){ c read-screen --surface "$REF" 2>/dev/null; }
for i in $(seq 1 120); do
  s=$(scr); if echo "$s" | grep -qiE 'Syntax theme|OAuth|Select login|text style|Log in|login method'; then say "onboarding/login 화면 — 중단"; echo "$s" | tail -8 | tee -a "$LOG"; exit 4; fi
  if echo "$s" | grep -qiE 'trust the files|Do you trust'; then say "trust prompt → Return"; c send-key --surface "$REF" Return >/dev/null; sleep 2; continue; fi
  echo "$s" | grep -q '❯' && echo "$s" | grep -qiE 'for shortcuts|bypass|\? for' && break; sleep 0.5; done
say "ready"
# 대상 세션 jsonl 에서 nonce 를 담은 user 레코드 수
urec(){ python3 - "$PROJ" "$ROOT/work" "$1" <<'EOF'
import json,os,sys,glob
proj,cwd,nonce=sys.argv[1:4]
n=0
for d in glob.glob(os.path.join(proj,'*')):
    for f in glob.glob(os.path.join(d,'*.jsonl')):
        try:
            for line in open(f,encoding='utf-8',errors='replace'):
                if nonce not in line: continue
                try: r=json.loads(line)
                except Exception: continue
                if r.get('type')=='user' and r.get('cwd','').startswith(cwd): n+=1
        except OSError: pass
print(n)
EOF
}
waitrec(){ for i in $(seq 1 45); do n=$(urec "$1"); [ "$n" -ge 1 ] && { echo "$n"; return 0; }; sleep 1; done; echo 0; }
clr(){ python3 - "$PROJ" "$ROOT/work" <<'PYX'
import os,sys,glob
proj,cwd=sys.argv[1:3]; n=0
for f in glob.glob(os.path.join(proj,'*','*.jsonl')):
    try: t=open(f,encoding='utf-8',errors='replace').read()
    except OSError: continue
    if cwd in t: n+=t.count('<command-name>/clear')
print(n)
PYX
}
pad(){ python3 -c "import sys;n=int(sys.argv[1]);s='filler text for length measurement only please ignore this part '; print((s*50)[:n])" "$1"; }
idle(){ for i in $(seq 1 60); do scr | grep -qiE 'esc to interrupt' || return 0; sleep 1; done; }
for k in $CASES; do
  idle; N="HX$(openssl rand -hex 3)"; ASK="[$N] Reply with exactly OK."
  case $k in
    C52)  B="$ASK"; c send --surface "$REF" "$B"$'\r' > "$ROOT/$k.out" 2>&1; rc=$? ;;
    C300) B="$ASK $(pad 280)"; c send --surface "$REF" "$B"$'\r' > "$ROOT/$k.out" 2>&1; rc=$? ;;
    E300) B="$ASK $(pad 280)"; c send --clear-first --surface "$REF" "$B" > "$ROOT/$k.out" 2>&1; rc=$? ;;
    EML)  B="$ASK"$'\n'"line two $(pad 150)"$'\n'"line three $(pad 150)"; c send --clear-first --surface "$REF" "$B" > "$ROOT/$k.out" 2>&1; rc=$? ;;
    D300) B="$ASK $(pad 280)"; c send --queued --surface "$REF" "$B" > "$ROOT/$k.out" 2>&1; rc=$? ;;
    F300) B="$ASK $(pad 280)"; c send --surface "$REF" "$B" > "$ROOT/$k.out" 2>&1; rc=$?; sleep 1; c send-key --surface "$REF" Return >> "$ROOT/$k.out" 2>&1 ;;
    SLC|SLR|SLB) B="/clear"; before=$(clr); case $k in SLC) c send --clear-first --surface "$REF" "/clear" > "$ROOT/$k.out" 2>&1; rc=$? ;; SLR) c send --surface "$REF" "/clear"$'\r' > "$ROOT/$k.out" 2>&1; rc=$? ;; SLB) o="$(c send --surface "$REF" "/clear" 2>&1)"; rc=$?; echo "$o" > "$ROOT/$k.out"; sleep 1; c send-key --surface "$REF" Return >> "$ROOT/$k.out" 2>&1 ;; esac
          for i in $(seq 1 20); do [ "$(clr)" -gt "$before" ] && break; sleep 1; done
          say "case=$k send_rc=$rc out=$(tr '\n' ' ' < "$ROOT/$k.out") clear_records=$before->$(clr) input=$(scr | grep '❯' | tail -1 | cut -c1-60)"; c send-key --surface "$REF" C-u >/dev/null 2>&1; sleep 3; continue ;;
    B300) B="$ASK $(pad 280)"; o="$(c send --surface "$REF" "$B" 2>&1)"; rc=$?; echo "$o" > "$ROOT/$k.out"; sleep 1; c send-key --surface "$REF" Return >> "$ROOT/$k.out" 2>&1 ;;
  esac
  n=$(waitrec "$N")
  say "case=$k len=${#B} send_rc=$rc out=$(tr '\n' ' ' < "$ROOT/$k.out" | cut -c1-160) user_records=$n"
  [ "$n" = 0 ] && { say "  input line: $(scr | grep '❯' | tail -1 | cut -c1-120)"; c send-key --surface "$REF" C-u >/dev/null 2>&1; }
  sleep 2
done
say "ROOT=$ROOT"
