#!/bin/sh
# Claude Code UserPromptSubmit hook — 말로 부서 만들기 배선(v113 · TICKET=v113-dept A1 · master 판정 aa33c5cb Q3).
#
# 왜 있는가: 도구(bin/javis_dept_request.py)·스케줄 틱·시험은 1.1.0 부터 실재했으나, 마스터(LLM)에게 그 도구를
#   부르라고 알려 주는 경로가 팩 어디에도 없었다(A1-2d 미구현 · 참조처 0). 디렉티브 절 원문은 세션 주입 때
#   요지(CORE)만 실리고 사건 때만 들어오므로, 사용자가 「부서 만들어 줘」라고 말하는 **그 턴**에 절차를 붙이는
#   것은 이 훅이 한다. 판정·조립은 javis_dept_request.py hook-prompt(파이썬) — 이 셸의 몫은 싼 거름뿐이다.
#
# 하는 일(파이썬 쪽 · 전부 fail-open):
#   ① 부서 낱말·[부서결과]/[부서가동] 입력 → 절차 요지 5줄 이내(같은 세션 반복 억제 — 알림 입력은 예외)
#   ② 매 턴 그물 = 「아직 말하지 않은 부서 소식」(status --pending 과 같은 판정 · 같은 소식은 세션당 1회)
#   ③ 사람 확인 축 = 열린 제안 뒤에 사람이 직접 친 입력(배달 원장 대조 = javis_mission.machine_origin)을 기록 —
#      confirm 이 그 기록을 요구한다(이 훅이 한 번이라도 돈 기계에서만 · 훅 없는 기계는 종전대로).
# 비용: 부서 요청 폴더가 비어 있고 부서 낱말이 없으면 외부 프로세스 0 으로 끝난다(셸 내장뿐).
# 4군① 폭주 큐: 주입은 요지·소식 합쳐 상한(파이썬 쪽 MAX 줄)·세션 반복 억제 — 같은 턴을 늘리지 않는다.
# 계약: 무슨 일이 있어도 exit 0 · stdout = 훅 JSON 한 개 또는 무출력.
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

_RQ="${CYS_DEPT_REQUESTS:-$HOME/.cys/dept-requests}"
_HAS_REQ=0
for _d in "$_RQ"/dr-*; do
  [ -d "$_d" ] && { _HAS_REQ=1; break; }
done
if [ "$_HAS_REQ" = "0" ]; then
  case "$HOOK_IN" in
    *부서*|*팀*|*'[부서결과]'*|*'[부서가동]'*) ;;
    *) exit 0 ;;
  esac
fi

_H="${0%/*}"; [ "$_H" = "$0" ] && _H="."
. "$_H/_lib.sh" 2>/dev/null \
  || . "${CYS_PACK_DIR:-$HOME/.cys/pack}/hooks/_lib.sh" 2>/dev/null \
  || { echo "[cys-hook] _lib.sh 소실 — 훅 강등(dept-chat-inject)" >&2; exit 0; }

T="$_H/../bin/javis_dept_request.py"
[ -f "$T" ] || T="${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_dept_request.py"
[ -n "$CYS_PY" ] && [ -f "$T" ] || exit 0

OUT=$(printf '%s' "$HOOK_IN" | cys_timeout_run 4 "$CYS_PY" "$(cys_native_path "$T")" hook-prompt 2>/dev/null)
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "[cys-hook] 부서 대화 주입 실패(rc=$RC) — 주입 생략(dept-chat-inject)" >&2
  exit 0
fi
[ -n "$OUT" ] && printf '%s\n' "$OUT"
exit 0
