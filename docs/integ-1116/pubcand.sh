#!/bin/bash
# pubcand.sh — 공개 후보 커밋 C 만들기(H − 제외 목록 · 부모 B 하나) + 관문 1(트리 차 = 제외 목록) + recheck 호출. push 없음.
#   근거 = 공개 점검 보고 §4 집행 순서(임시 GIT_INDEX_FILE · commit-tree · 로컬 ref 1개)를 손 대신 한 명령으로.
#   ★이 스크립트는 git push·태그·gh 를 부르지 않는다(맨 아래 자기 검사가 본문에 그 낱말이 명령으로 없음을 잰다).
#
# 사용: bash docs/integ-1116/pubcand.sh [<H>]          # H 기본 = HEAD
#       bash docs/integ-1116/pubcand.sh --self-test     # 임시 저장소 + 가짜 recheck 로 양성·음성 대조
# 환경(필수): PUB_EXCLUDE = 제외 목록(한 줄에 경로 하나) · PUB_MSG = 커밋 메시지 파일
# 환경(선택): PUB_BASE(기본 origin/main) · PUB_REF(기본 refs/heads/cand/1116-rc) · PUB_FORCE=1(있는 ref 덮어쓰기)
#             PUB_RECHECK(기본 ~/axdev/workers/cysr-public-check-1118/recheck.sh) · PUB_NO_RECHECK=1(관문 1까지만)
#             PUB_GUARD_DIRS(기본 docs/integ-1116 — 이 폴더의 H 파일은 전부 제외 목록에 있어야 한다 · 공백 구분)
# 종료: 0 = C 생성 · 관문 1 통과 · recheck 깨끗 | 1 = recheck 가 읽을 항목 있음(공개 전 멈춤 · 사람 판정)
#       2 = 입력·도구 실패 또는 관문 1 불일치(C 는 만들었으면 ref 에 둔다 · 판정 근거로) | 3 = recheck 가 이력 불일치 보고
# 출력 끝 줄: `PUBCAND H=<> B=<> C=<> ref=<> gate1=<0|1> recheck_rc=<n|skip> rc=<n>`
set -u
GIT=/usr/bin/git

self_test() {
  local T; T=$(mktemp -d "${TMPDIR:-/tmp}/pubcXXXX") || return 2
  local me; me="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  local fails=0
  ok() { echo "  ok  $1"; }
  bad() { echo "  BAD $1"; fails=$((fails+1)); }
  (
    set -e
    export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_AUTHOR_NAME=t GIT_COMMITTER_NAME=t
    export GIT_AUTHOR_EMAIL="t$(printf '\100')t.invalid" GIT_COMMITTER_EMAIL="t$(printf '\100')t.invalid"
    cd "$T"; $GIT init -q -b main r; cd r
    echo pub > a.txt; $GIT add a.txt; $GIT commit -qm base; $GIT tag base0
    mkdir -p docs/integ-1116 src; echo x > docs/integ-1116/gate.sh; echo s > src/m.rs; echo h > HANDOFF.x.md
    $GIT add -A; $GIT commit -qm head
  ) >/dev/null 2>&1 || { echo "self-test: 임시 저장소 실패"; rm -rf "$T"; return 2; }
  printf 'docs/integ-1116/gate.sh\nHANDOFF.x.md\n' > "$T/L"; echo "cand 1" > "$T/M"
  printf '#!/bin/sh\necho "fake recheck $1 VERDICT=$VERDICT SRC=$SRC" > "%s/rc.log"\nexit "${FAKE_RC:-0}"\n' "$T" > "$T/rk.sh"
  local R="$T/r" out rc C
  run() { ( cd "$R" && env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_AUTHOR_NAME=t GIT_COMMITTER_NAME=t \
      GIT_AUTHOR_EMAIL="t$(printf '\100')t.invalid" GIT_COMMITTER_EMAIL="t$(printf '\100')t.invalid" \
      PUB_BASE=base0 PUB_MSG="$T/M" PUB_RECHECK="$T/rk.sh" "$@" bash "$me" HEAD ); }
  echo "[pubcand self-test]"
  out=$(run PUB_EXCLUDE="$T/L" 2>&1); rc=$?
  C=$($GIT -C "$R" rev-parse -q --verify refs/heads/cand/1116-rc)
  [ $rc -eq 0 ] && ok "양성 rc 0" || bad "양성 rc=$rc: $out"
  [ -n "$C" ] && [ "$($GIT -C "$R" rev-parse "$C^@")" = "$($GIT -C "$R" rev-parse base0)" ] && ok "C 부모 = B 하나" || bad "C 부모"
  [ "$($GIT -C "$R" ls-tree -r --name-only "$C" | tr '\n' ' ')" = "a.txt src/m.rs " ] && ok "C 트리 = H − 제외" || bad "C 트리"
  grep -q "fake recheck $C VERDICT=$($GIT -C "$R" rev-parse base0) SRC=" "$T/rc.log" 2>/dev/null && ok "recheck 가 C·VERDICT=B 로 불림" || bad "recheck 호출: $(cat "$T/rc.log" 2>&1)"
  out=$(run PUB_EXCLUDE="$T/L" 2>&1); rc=$?
  [ $rc -eq 2 ] && echo "$out" | grep -q "이미 있음" && ok "있는 ref 덮어쓰기 거부(rc 2)" || bad "ref 덮어쓰기 rc=$rc"
  out=$(run PUB_EXCLUDE="$T/L" PUB_FORCE=1 FAKE_RC=1 2>&1); rc=$?
  [ $rc -eq 1 ] && ok "recheck rc 1 → rc 1" || bad "recheck rc1 전달 rc=$rc"
  printf 'HANDOFF.x.md\n' > "$T/L2"
  out=$(run PUB_EXCLUDE="$T/L2" PUB_FORCE=1 2>&1); rc=$?
  [ $rc -eq 2 ] && echo "$out" | grep -q "docs/integ-1116/gate.sh" && ok "지킴 폴더 파일이 목록에 없음 → rc 2" || bad "지킴 폴더 rc=$rc"
  printf 'docs/integ-1116/gate.sh\nHANDOFF.x.md\nno/such.md\n' > "$T/L3"
  out=$(run PUB_EXCLUDE="$T/L3" PUB_FORCE=1 2>&1); rc=$?
  [ $rc -eq 2 ] && echo "$out" | grep -q "no/such.md" && ok "H 에 없는 목록 줄 → rc 2" || bad "없는 줄 rc=$rc"
  out=$(run PUB_EXCLUDE="$T/L" PUB_FORCE=1 PUB_BASE=no-such 2>&1); rc=$?
  [ $rc -eq 2 ] && ok "못 찾는 B → rc 2" || bad "B rc=$rc"
  # 자기 검사: 집행 본문(자기 검체 함수 뒤 · 주석 아닌 줄)에 push·tag 쓰기·gh 명령이 없다(검체 함수는 임시 저장소에 태그를 단다)
  if sed -n '/^\[ "\${1:-}" = --self-test \]/,$p' "$me" | grep -vE '^\s*#' | grep -nE '(^|[;&|( ]+)(\$GIT|git)( -C [^ ]+)? (push|tag)\b|(^|[;&|( ]+)gh ' >/dev/null; then bad "본문에 push/tag/gh 명령"; else ok "본문에 push·tag·gh 명령 0"; fi
  rm -rf "$T"
  [ $fails -eq 0 ] && { echo "[pubcand self-test] OK"; return 0; } || { echo "[pubcand self-test] FAIL $fails"; return 1; }
}

[ "${1:-}" = --self-test ] && { self_test; exit $?; }

H_IN=${1:-HEAD}
L=${PUB_EXCLUDE:-}; M=${PUB_MSG:-}
B_IN=${PUB_BASE:-origin/main}; REF=${PUB_REF:-refs/heads/cand/1116-rc}
RK=${PUB_RECHECK:-$HOME/axdev/workers/cysr-public-check-1118/recheck.sh}
GUARD=${PUB_GUARD_DIRS:-docs/integ-1116}
H=""; B=""; C=""; G1=""; RRC=skip
fin() { echo "PUBCAND H=${H:0:12} B=${B:0:12} C=${C:0:12} ref=$REF gate1=${G1:-na} recheck_rc=$RRC rc=$1"; exit "$1"; }
die() { echo "✗ $*" >&2; fin 2; }

[ -n "$L" ] && [ -f "$L" ] || die "PUB_EXCLUDE(제외 목록 파일)가 없다"
[ -n "$M" ] && [ -s "$M" ] || die "PUB_MSG(커밋 메시지 파일)가 없거나 비었다"
H=$($GIT rev-parse --verify -q "$H_IN^{commit}") || die "H($H_IN)를 못 찾음"
B=$($GIT rev-parse --verify -q "$B_IN^{commit}") || die "B($B_IN)를 못 찾음 — fetch 했는가"
OLD=$($GIT rev-parse --verify -q "$REF" || true)
[ -z "$OLD" ] || [ "${PUB_FORCE:-0}" = 1 ] || die "$REF 이미 있음(${OLD:0:12}) — 덮어쓰려면 PUB_FORCE=1"

W=$(mktemp -d "${TMPDIR:-/tmp}/pubcXXXX") || die "임시 폴더"
trap 'rm -rf "$W"' EXIT
grep -v '^[[:space:]]*$' "$L" | LC_ALL=C sort -u > "$W/list"
$GIT ls-tree -r --name-only "$H" | LC_ALL=C sort > "$W/htree"
# 목록 줄이 H 에 실재하는가(없는 줄 = 낡은 목록 · 조용히 무시하면 관문 1 이 뜻을 잃는다)
LC_ALL=C comm -23 "$W/list" "$W/htree" > "$W/absent"
[ -s "$W/absent" ] && { echo "✗ 제외 목록 줄이 H 트리에 없음 $(wc -l < "$W/absent" | tr -d ' ')건:" >&2; sed 's/^/    /' "$W/absent" >&2; die "목록 갱신 필요"; }
# 지킴 폴더(내부 게이트 도구 폴더)의 H 파일은 전부 목록에 있어야 한다 — 없으면 그 파일이 공개 트리에 실린다
: > "$W/leak"
for g in $GUARD; do grep -E "^${g%/}/" "$W/htree" | LC_ALL=C comm -23 - "$W/list" >> "$W/leak"; done
[ -s "$W/leak" ] && { echo "✗ 지킴 폴더($GUARD)의 파일이 제외 목록에 없음:" >&2; sed 's/^/    /' "$W/leak" >&2; die "목록에 더하라"; }

export GIT_INDEX_FILE="$W/index"
$GIT read-tree "$H" || die "read-tree"
tr '\n' '\0' < "$W/list" | xargs -0 $GIT update-index --force-remove -- || die "update-index"
T=$($GIT write-tree) || die "write-tree"
C=$($GIT commit-tree "$T" -p "$B" -F "$M") || die "commit-tree"
unset GIT_INDEX_FILE
$GIT update-ref -m "pubcand.sh H=${H:0:12}" "$REF" "$C" ${OLD:+"$OLD"} || die "update-ref"
echo "C=$C (ref $REF${OLD:+ · 이전 ${OLD:0:12}}) · 작성자 = $($GIT log -1 --format='%an' "$C")"

# 관문 1: C↔H 트리 차 = 제외 목록 정확히
$GIT diff --name-only "$C" "$H" | LC_ALL=C sort > "$W/diff"
if diff "$W/diff" "$W/list" > "$W/g1"; then G1=0; echo "✓ 관문 1: C↔H 차 = 제외 목록 $(wc -l < "$W/list" | tr -d ' ')건"; else G1=1; echo "✗ 관문 1 불일치:"; sed 's/^/    /' "$W/g1"; fin 2; fi
[ "$($GIT rev-parse "$C^@")" = "$B" ] || { G1=1; echo "✗ C 의 부모가 B 하나가 아님"; fin 2; }

[ "${PUB_NO_RECHECK:-0}" = 1 ] && fin 0
[ -f "$RK" ] || die "recheck 스크립트 없음: $RK"
SRC="$($GIT rev-parse --show-toplevel)" VERDICT="$B" bash "$RK" "$C"; RRC=$?
case $RRC in 0) fin 0 ;; 1) fin 1 ;; 3) fin 3 ;; *) fin 2 ;; esac
