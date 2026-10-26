#!/bin/sh
# PreToolUse GATE hook (matcher Edit|Write|NotebookEdit): grill-me 최소 질문 게이트.
# 의도(워크플로 가드레일, 보안 경계 아님): grill-me 인터뷰가 floor(20·복잡30)만큼
# 서로 다른 결정 브랜치를 해소하기 전에는 '합의 결과물 쓰기(구현)'를 막아 "충분히
# 캐물은 뒤 합의→구현" 순서를 강제한다(제품 기본 절차).
#
# ★GATE hook 클래스(cys-hook.sh의 OBSERVABILITY 불변과 별개 — 차단이 목적):
#   appbuild-gate.sh·role-capability-gate.sh와 동일 계열. 단 차단은 grill_gate.py가
#   exit 2를 '명시'할 때만 — 그 외 모든 경로는 fail-OPEN(작업 차단보다 통과가 안전측).
#
# Threat model = 비악의 오작동 방지(워커가 의도합의 건너뛰고 구현부터). 따라서 fail-OPEN 기본:
#   - .grill_session.json 마커 부재(=grill 세션 아님) → 통과 (grill_gate.py check가 exit 0)
#   - 마커 TTL 만료·status=passed/done → 통과
#   - python3 부재·grill_gate.py 부재·크래시·exit 1 → 통과
#   막는 경우는 오직: 마커 active(collecting) + distinct 결정축 < floor 일 때 grill_gate.py가
#   exit 2를 반환할 때뿐.
#   ※ Bash는 matcher에서 제외한다 — 인터뷰 중 코드베이스 탐색(grep/find)을 막지 않기
#     위함이며, Bash 리다이렉트(echo>file) 우회는 정직한 한계로 둔다(적대 봉쇄 아님).
#     ※ Bash 리다이렉트는 코드 산출물 쓰기뿐 아니라 마커(.grill_session) tamper(status=done
#       덮어쓰기)로도 게이트를 끌 수 있다 — 비악의 오작동 방지 threat model의 명시적 한계
#       (적대 봉쇄가 필요하면 begin이 HMAC 서명·check가 검증하는 무결성 핀이 별도로 필요).

# ★1.1.11 hook-slim(master 재결정 02da1acc = B1): 좌석 아닌 세션(사용자 개인 Claude·cmux 페인·데스크톱 앱) 즉시 탈출 —
#   좌석 env 3키(CYS_/JAVIS_/AITERM_SURFACE_ID · Rust env_compat 와 같은 '비어 있지 않음' 규칙)가 없으면 이 훅은 할 일이 없다
#   (10-27 기록 실측: 할 일 0인 cso 페인에서 Stop 1,059초·도구 866초 붙잡고 취소된 사례). 프리루드 **앞**이라 비용 = 셸 기동뿐.
#   인자 호출(--self-test 등)은 제외 · stdin 은 소진한다(Claude Code 쪽 쓰기 EPIPE 방지 · 단말이면 읽지 않는다).
[ $# -eq 0 ] && [ -z "${CYS_SURFACE_ID:-}${JAVIS_SURFACE_ID:-}${AITERM_SURFACE_ID:-}" ] && { [ -t 0 ] || cat >/dev/null 2>&1; exit 0; }
# ── 공용 프리루드(CS-4①) — loud-skip: 소실 시 조용히 꺼지지 않고 stderr 1줄 후 강등 ──
. "$(dirname "$0")/_lib.sh" 2>/dev/null \
  || . "${CYS_PACK_DIR:-$HOME/.cys/pack}/hooks/_lib.sh" 2>/dev/null \
  || { echo "[cys-hook] _lib.sh 소실 — 훅 강등(grill-gate)" >&2; exit 0; }
command -v cys_lane_redirect >/dev/null 2>&1 && cys_lane_redirect "$@"
# self-test는 엔진에 위임(preflight가 엔진 self-test를 직접 검증)
if [ "${1:-}" = "--self-test" ]; then
  HOOK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
  [ -n "${CYS_PY:-}" ] || exit 0
  exec "$CYS_PY" "$(cys_native_path "$HOOK_DIR/../bin/grill_gate.py")" --self-test
fi

[ -n "${CYS_PY:-}" ] || exit 0                     # G22 fail-open: python(3) 해소 불가
HOOK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd) || exit 0
GATE_PY="$HOOK_DIR/../bin/grill_gate.py"
[ -f "$GATE_PY" ] || exit 0                          # fail-open: 엔진 없음
GATE_PY_N="$(cys_native_path "$GATE_PY")"

cat >/dev/null 2>&1   # PreToolUse stdin(hook JSON)은 check가 쓰지 않음 — 소비만

"$CYS_PY" "$GATE_PY_N" check
rc=$?
# 오직 명시적 floor 미충족(2)만 차단. 0·1·크래시 등 그 외 전부 통과(fail-open).
[ "$rc" = "2" ] && exit 2
exit 0
