#!/bin/bash
# 격리 하네스 — 0.14.52 직접 보내기 60초 보류 × 우리 2단계(send + 별도 send-key) 실측. 실 좌석·실 데몬 무접촉.
set -u
WT="${WT:-$HOME/cys-terminal-src-wt/rebase-01452}"
CYS=$WT/target/debug/cys; CYSD=$WT/target/debug/cysd
ROOT=$WT/target/h60-$$; mkdir -p "$ROOT"/{home,pack,state,work}
SOCK=$ROOT/d.sock; REALHOME="${REALHOME:-$HOME}"
LOG=$ROOT/run.log; : > "$LOG"
say(){ echo "[$(date +%T)] $*" | tee -a "$LOG"; }
export CYS_NO_AUTOSTART=1
c(){ env -u CYS_SURFACE_ID -u CYS_ROLE HOME="$ROOT/home" CYS_SOCKET="$SOCK" CYS_STATE_DIR="$ROOT/state" CYS_PACK_DIR="$ROOT/pack" "$CYS" --socket "$SOCK" "$@"; }
set -m
env -u CYS_SURFACE_ID -u CYS_ROLE HOME="$ROOT/home" CYS_SOCKET="$SOCK" CYS_STATE_DIR="$ROOT/state" CYS_PACK_DIR="$ROOT/pack" CYS_NO_AUTORESTORE=1 "$CYSD" >"$ROOT/daemon.log" 2>&1 &
DPID=$!; set +m
cleanup(){ c close-surface "$REF" >/dev/null 2>&1; kill -TERM "-$DPID" 2>/dev/null; sleep 1; kill -KILL "-$DPID" 2>/dev/null; say "cleanup dpid=$DPID"; }
trap cleanup EXIT
REF=""; for i in $(seq 1 300); do c identify >/dev/null 2>&1 && break; sleep 0.2; done
say "daemon pid=$DPID $(c identify 2>&1 | tr -d ' \n' | cut -c1-300)"; c identify >/dev/null 2>&1 || { say "daemon not up"; tail -20 "$ROOT/daemon.log"; exit 3; }
REF=$(c new-surface --agent claude --cwd "$ROOT/work" --cmd "env HOME=$REALHOME CLAUDE_CONFIG_DIR=$REALHOME/.cys/claude claude --setting-sources project --strict-mcp-config --model haiku" | grep -oE 'surface:[0-9]+' | head -1)
say "seat=$REF"
scr(){ c read-screen --surface "$REF" 2>/dev/null; }
# 준비: 신뢰 창이면 Return · 입력 상자 대기(최대 60s)
for i in $(seq 1 120); do
  s=$(scr); if echo "$s" | grep -qiE 'Syntax theme|OAuth|Select login|text style|Log in|login method'; then say "onboarding/login 화면 — 중단(아무것도 치지 않음)"; echo "$s" | tail -8 | tee -a "$LOG"; exit 4; fi
  if echo "$s" | grep -qiE 'trust the files|Do you trust'; then say "trust prompt → Return"; c send-key --surface "$REF" Return >/dev/null; sleep 2; continue; fi
  echo "$s" | grep -q '❯' && echo "$s" | grep -qiE 'for shortcuts|bypass|\? for' && break; sleep 0.5; done
say "ready screen tail:"; scr | grep -v '^\s*$' | tail -6 | tee -a "$LOG"
probe(){ # $1 label $2 nonce
  for i in $(seq 1 60); do scr | grep -q "$2" && { say "$1: 화면에 $2 관측 (${i}×0.5s)"; return 0; }; sleep 0.5; done; say "$1: 30s 안에 $2 미관측"; return 1; }
# A: 같은 bash 에서 직접 send → 1초 뒤 화면 → 직접 send-key Return
say "=== A 직접 send + 직접 send-key (같은 부모) ==="
out=$(true); c send --surface "$REF" "Reply with exactly the word PONGAAA and nothing else" > "$ROOT/a.out" 2>&1; say "A send rc=$? out=$(cat $ROOT/a.out)"
sleep 1; if scr | grep -q 'PONGAAA and nothing'; then say "A: Return 전 입력줄에 본문 보임"; else say "A: Return 전 입력줄에 본문 안 보임(held 추정)"; fi
c send-key --surface "$REF" Return > "$ROOT/a2.out" 2>&1; say "A send-key rc=$? out=$(cat $ROOT/a2.out)"
probe A PONGAAA$ || probe A2 PONGAAA
sleep 3
# B: $(...) 안에서 send → 직접 send-key (master-send.sh:421 꼴)
say "=== B \$(send) + 직접 send-key ==="
bo="$(c send --surface "$REF" "Reply with exactly the word PONGBBB and nothing else" 2>&1)"; say "B send out=$bo"
sleep 1; if scr | grep -q 'PONGBBB and nothing'; then say "B: Return 전 본문 보임"; else say "B: Return 전 본문 안 보임"; fi
c send-key --surface "$REF" Return > "$ROOT/b2.out" 2>&1; say "B send-key rc=$? out=$(cat $ROOT/b2.out)"
probe B PONGBBB$ || true
sleep 3
# C: 본문+CR 한 번(SelfSubmitting · 고칠 방안 후보)
say "=== C 본문 끝 CR 1회 ==="
c send --surface "$REF" "Reply with exactly the word PONGCCC and nothing else"$'\r' > "$ROOT/c.out" 2>&1; say "C send rc=$? out=$(cat $ROOT/c.out)"
probe C PONGCCC$ || true
sleep 3
# D: --queued (고칠 방안 후보 2)
say "=== D --queued ==="
c send --queued --surface "$REF" "Reply with exactly the word PONGDDD and nothing else" > "$ROOT/d.out" 2>&1; say "D send rc=$? out=$(cat $ROOT/d.out)"
probe D PONGDDD$ || true
say "final screen tail:"; scr | grep -v '^\s*$' | tail -14 | tee -a "$LOG"
grep -iE 'held|awaiting_submit|submit_undelivered|bound|associat' "$ROOT/daemon.log" | tail -20 | tee -a "$LOG"
say "ROOT=$ROOT"
