#!/bin/sh
# Claude Code SessionStart hook ②' — master 좌석 배경층 주입(injection-slim T2 · DESIGN-v2.1 §4-4 · D5′).
#
# 왜 따로 있는가: 훅 ①(session-start.sh)의 master 분기는 요지(CORE)만 ≤9,000자로 싣는다. Claude Code 는
#   훅 출력이 10,000자를 넘으면 본문 대신 파일 저장 + 약 2,000자 미리보기만 모델에 넣으므로(T0-PROBES ⓓ),
#   soul·메모리 색인·로컬 오버레이를 훅 ①에 함께 두면 다시 넘친다. 그래서 같은 이벤트의 **다른 훅**으로
#   분리하고, 이 훅도 스스로 글자를 재서 ≤9,000자만 낸다(상한은 훅 출력 단위).
#   inject-context.sh 로 옮기지 않은 이유(§4-4 · N1·R4): 그 훅은 이미 적재가 크고 cmux master 에도 돈다.
#
# 출력 우선순위(앞 = 끝까지 살아남는 쪽 · 넘치면 뒤 블록부터 빠지고 이름이 고지된다):
#   ①(source=clear|compact|resume|fork) §11 컨텍스트 60% 원문 ②같은 조건의 §9 복원·todo 원문
#   ③soul.md(clear|compact|fork — startup·resume 은 inject-context.sh 가 이미 넣는다 · F3 중복 제거)
#   ④메모리 색인(≤4,000자) ⑤로컬 오버레이(≤3,000자 · 안전핵 키워드 줄 제외 + 재선언 1줄)
#
# 계약: 역할 가드(master 외 즉시 종료 — ~/.claude/settings.json 에 잘못 등록돼도 cmux master·워커에서
#   아무것도 하지 않는다 · F1) · 내부 상한 5초(cys_timeout_run) · fail-open(무슨 일이 있어도 exit 0 —
#   조립기 실패는 stderr 1줄 + stdout 경로 고지 1줄). 등록(settings 표·preflight·Rust 소망상태)은 T3 에서
#   사건 훅과 함께 2행으로 넣는다(master 판정 5cdfbd54 ②A) — 등록 시 "timeout": 5 를 명시한다.
[ "${CYS_ROLE:-}" = "master" ] || exit 0
. "$(dirname "$0")/_lib.sh" 2>/dev/null \
  || . "${CYS_PACK_DIR:-$HOME/.cys/pack}/hooks/_lib.sh" 2>/dev/null \
  || { echo "[cys-hook] _lib.sh 소실 — 훅 강등(inject-background)" >&2; exit 0; }

JARVIS_DIR="${CYS_PACK_DIR:-$HOME/.cys/pack}"
[ -d "$JARVIS_DIR" ] || exit 0
cys_require_surface

HOOK_IN=""
if [ ! -t 0 ]; then
  IFS= read -r HOOK_IN || true
fi

D="$JARVIS_DIR/directives/MASTER_DIRECTIVE.md"
SOUL="$JARVIS_DIR/soul.md"
M="$JARVIS_DIR/memory/MEMORY.md"
LD="${CYS_LOCAL_DIR:-$HOME/.cys/local}/directives/MASTER_DIRECTIVE.local.md"
CI="$(dirname "$0")/core_inject.py"
[ -f "$CI" ] || CI="$JARVIS_DIR/hooks/core_inject.py"

BG_OUT=""; BG_RC=127
if [ -n "$CYS_PY" ] && [ -f "$CI" ]; then
  BG_OUT=$(export CYS_CI_HOOK_IN="$HOOK_IN"
           cys_timeout_run 5 "$CYS_PY" "$(cys_native_path "$CI")" background \
             --directive "$(cys_native_path "$D")" --soul "$(cys_native_path "$SOUL")" \
             --memory "$(cys_native_path "$M")" --memory-tool "$JARVIS_DIR/bin/javis_memory.py add" \
             --overlay "$(cys_native_path "$LD")" </dev/null 2>/dev/null)
  BG_RC=$?
fi
if [ "$BG_RC" -eq 0 ]; then
  [ -n "$BG_OUT" ] && printf '%s\n' "$BG_OUT"
  exit 0
fi
echo "[cys-hook] 배경층 조립기 실패(rc=$BG_RC) — 배경층 생략(inject-background)" >&2
# G8 동형: 경로가 든 줄은 printf — macOS /bin/sh 의 xpg_echo 가 백슬래시를 먹는다.
printf '■ 배경층 생략(조립기 rc=%s) — 필요하면 직접 읽어라: soul %s · 메모리 색인 %s · 로컬 오버레이 %s\n' \
  "$BG_RC" "$SOUL" "$M" "$LD"
exit 0
