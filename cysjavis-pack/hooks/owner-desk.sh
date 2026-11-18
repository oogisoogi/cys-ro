#!/bin/sh
# Claude Code 훅 — 오너 책상(owner-desk · TICKET=cysr-owner-memory-todo-1118).
#   SessionStart       → 저장된 오너 지시 전부 + 밀린 일 한 줄 + 규약(늘 · 순환·/clear·재시작 뒤에도)
#   UserPromptSubmit   → 오너 입력(기계 입력 제외)마다 「지속 지시·새 일·끝 알림」 점검 1줄 · 그날 첫 오너 대화면 밀린 일 보고
#   Stop               → 턴 끝 안전망(말과 기록 대조 · 아침 보고 확인 · 폰 알림 미발송 · 자기 점검 턴당 1회)
#   PostToolUse(PushNotification) → 폰 알림 보냄 기록
# 판정·조립은 bin/javis_owner.py hook <사건> — 이 셸의 몫은 역할 가드와 상한뿐이다.
# 계약: master 좌석에서만(다른 좌석은 외부 프로세스 0 으로 exit 0) · 무슨 일이 있어도 exit 0 · stdout = 훅 JSON 또는 무출력.
[ "${CYS_ROLE:-}" = "master" ] || exit 0
[ -n "${CYS_SURFACE_ID:-}${AITERM_SURFACE_ID:-}" ] || exit 0
# 사건 = 인자(시험용) 또는 훅 JSON 의 hook_event_name(등록은 인자 없이 한 줄 — 파이썬이 auto 로 가른다).
EV="${1:-auto}"
case "$EV" in auto|session|prompt|stop|posttool) ;; *) exit 0 ;; esac

HOOK_IN=""
if [ ! -t 0 ]; then
  while IFS= read -r _l || [ -n "$_l" ]; do
    HOOK_IN="$HOOK_IN$_l
"
  done
fi
# 하위 에이전트(서브에이전트) 사건은 오너 턴이 아니다.
case "$HOOK_IN" in
  *'"agent_id"'*) exit 0 ;;
esac

_H="${0%/*}"; [ "$_H" = "$0" ] && _H="."
. "$_H/_lib.sh" 2>/dev/null \
  || . "${CYS_PACK_DIR:-$HOME/.cys/pack}/hooks/_lib.sh" 2>/dev/null \
  || { echo "[cys-hook] _lib.sh 소실 — 훅 강등(owner-desk)" >&2; exit 0; }
command -v cys_lane_redirect >/dev/null 2>&1 && cys_lane_redirect "$@"

T="$_H/../bin/javis_owner.py"
[ -f "$T" ] || T="${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_owner.py"
[ -n "$CYS_PY" ] && [ -f "$T" ] || exit 0

# 안쪽 상한 8초 < 바깥 하네스 선언(javis_preflight HOOK_TIMEOUT_S = 10) — rc 기록이 남게(dept-chat-inject 선례).
OUT=$(printf '%s' "$HOOK_IN" | cys_timeout_run 8 "$CYS_PY" "$(cys_native_path "$T")" hook "$EV" 2>/dev/null)
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "[cys-hook] 오너 책상 훅 실패(rc=$RC · $EV) — 생략(owner-desk)" >&2
  cys_hook_fail owner-desk "$RC" "javis_owner:hook-$EV"
  exit 0
fi
[ -n "$OUT" ] && printf '%s\n' "$OUT"
exit 0
