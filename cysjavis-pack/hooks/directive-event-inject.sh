#!/bin/sh
# Claude Code PreToolUse(matcher Bash) hook ⓓ — master·CEO 좌석 사건 적시 주입(injection-slim T3 ·
#   DESIGN-v2.1 §4-5 · master 판정 6255b46b = PreToolUse · b286f358 = D10 A).
#
# 왜 있는가: 세션 시작 훅 ①은 요지(CORE)만 ≤9,000자로 싣는다(10,000자를 넘으면 하네스가 본문 대신 파일 저장 +
#   미리보기 2,000자만 넣는다 — T0-PROBES ⓓ). 상황 절(§0-C 임무 게이트·§2 노드 각성·§7 라운드·§4 승인·§8 자원·
#   §14 자율주행)의 **원문**은 그 상황의 명령이 실행되는 순간 이 훅이 넣는다(요지가 원문과 어긋날 수 없게).
#   ⚠ 추가 문맥은 명령 **결과 옆**에 도착한다(T0 ⓑ 실측) — 첫 1회 실행을 막는 것은 §14 거부(D10)뿐이다.
#
# 판정·조립은 hooks/core_inject.py event(트리거 사전 = 그 파일의 EVENT_TRIGGERS 데이터 표). 이 셸의 몫:
#   ① 역할 가드(master 외 즉시 종료 — ~/.claude/settings.json 에 등록돼도 cmux master·워커에서 무동작 · F1·U7)
#   ② stdin 1회 판독(셸 내장 read) ③ 서브에이전트(agent_id 키) 즉시 종료(master 판정 · T0 ⓒ)
#   ④ 트리거 낱말 1차 거름(case) — 여기까지 **외부 프로세스 0**(비일치 경로 비용 = 셸 내장뿐 · §4-5 판정 1)
#   ⑤ 걸린 경우에만 프리루드·파이썬(내부 상한 5초 · 등록 timeout 5초와 이중).
# 계약: fail-open(무슨 일이 있어도 exit 0 · 조립기 실패 = 무출력 = 명령 그대로 진행) · stdout = 훅 JSON 한 개 또는 무출력.
[ "${CYS_ROLE:-}" = "master" ] || exit 0
[ -n "${CYS_SURFACE_ID:-}${AITERM_SURFACE_ID:-}" ] || exit 0

HOOK_IN=""
if [ ! -t 0 ]; then
  while IFS= read -r _l || [ -n "$_l" ]; do
    HOOK_IN="$HOOK_IN$_l
"
  done
fi
case "$HOOK_IN" in
  *'"agent_id"'*) exit 0 ;;
esac
case "$HOOK_IN" in
  *javis_orchestra*|*javis_mission*|*javis_resource_gate*|*launch-agent*|*'cys feed'*|*'cys --socket'*|*'cys -s '*|*cys-dept*) ;;
  *) exit 0 ;;
esac

_H="${0%/*}"; [ "$_H" = "$0" ] && _H="."
. "$_H/_lib.sh" 2>/dev/null \
  || . "${CYS_PACK_DIR:-$HOME/.cys/pack}/hooks/_lib.sh" 2>/dev/null \
  || { echo "[cys-hook] _lib.sh 소실 — 훅 강등(directive-event-inject)" >&2; exit 0; }

JARVIS_DIR="${CYS_PACK_DIR:-$HOME/.cys/pack}"
D="$JARVIS_DIR/directives/MASTER_DIRECTIVE.md"
[ -f "$D" ] || exit 0
CI="$_H/core_inject.py"
[ -f "$CI" ] || CI="$JARVIS_DIR/hooks/core_inject.py"
[ -n "$CYS_PY" ] && [ -f "$CI" ] || exit 0

EV_OUT=$(printf '%s' "$HOOK_IN" | cys_timeout_run 5 "$CYS_PY" "$(cys_native_path "$CI")" event \
           --directive "$(cys_native_path "$D")" --state-dir "$CYS_STATE_DIR" 2>/dev/null)
EV_RC=$?
if [ "$EV_RC" -ne 0 ]; then
  echo "[cys-hook] 사건 주입 조립기 실패(rc=$EV_RC) — 주입 생략(directive-event-inject)" >&2
  exit 0
fi
[ -n "$EV_OUT" ] && printf '%s\n' "$EV_OUT"
exit 0
