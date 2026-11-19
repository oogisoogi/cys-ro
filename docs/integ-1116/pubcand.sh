#!/bin/bash
# pubcand.sh — 공개 후보 커밋 C 만들기(**허용 목록** · 부모 B 하나) + 관문 1 + recheck 호출. push 없음.
#   근거 = 공개 점검 보고 §4 집행 순서(임시 GIT_INDEX_FILE · commit-tree · 로컬 ref 1개)를 손 대신 한 명령으로.
#   ★규칙(유출 쪽 실패가 안전한 쪽): C 의 트리 = H 의 파일 중 **B(이미 공개된 판)에 같은 경로가 있는 것** + **PUB_ALLOW 에 적힌 새 경로**뿐.
#     H 에 새로 생긴 파일이 목록에 없으면 = 공개 안 됨 + 보고(withheld). 목록을 잊으면 덜 공개될 뿐 더 공개되지 않는다
#     (종전 제외 목록 방식은 목록을 잊으면 공개됐다 — codex 1R #1 · master 처분 11-20 #8).
#   ★이 스크립트는 git push·태그·gh 를 부르지 않는다(자기 검체가 집행 본문에 그 명령이 없음을 잰다).
#
# 사용: bash docs/integ-1116/pubcand.sh [<H>]                          # H 기본 = HEAD
#       bash docs/integ-1116/pubcand.sh --derive-allow <H> <B> <제외목록>   # 옮김 도우미: H−B−제외목록 = 새 공개 경로를 출력
#       bash docs/integ-1116/pubcand.sh --self-test                     # 임시 저장소 + 가짜 recheck 로 양성·음성 대조
# 환경(필수): PUB_ALLOW = 새 공개 허용 경로 목록(한 줄에 경로 하나 · B 에 없는 경로만 뜻이 있음 · 비어도 됨) · PUB_MSG = 커밋 메시지 파일
# 환경(선택): PUB_BASE(기본 origin/main) · PUB_REF(기본 refs/heads/cand/1116-rc) · PUB_FORCE=1(있는 ref 덮어쓰기)
#             PUB_RECHECK(기본 ~/axdev/workers/cysr-public-check-1118/recheck.sh) · PUB_NO_RECHECK=1(관문 1까지만)
#             PUB_GUARD_DIRS(기본 docs/integ-1116 — 이 폴더의 새 경로는 허용 목록에 올 수 없다 · 내부 게이트 도구 · 공백 구분)
#             PUB_WITHHELD_OUT = 공개 안 된 새 파일 목록을 이 파일에도 쓴다(표준 출력에는 늘 전부)
# 종료: 0 = C 생성 · 관문 1 통과 · recheck 깨끗 | 1 = recheck 가 읽을 항목 있음(공개 전 멈춤 · 사람 판정)
#       2 = 입력·도구 실패 또는 관문 1 불일치(C 는 만들었으면 ref 에 둔다 · 판정 근거로) | 3 = recheck 가 이력 불일치 보고
#       4 = PUB_NO_RECHECK=1 — C·관문 1 까지만(recheck 생략 = 공개 판정 미완 · 성공 코드 아님)
# 관문 1(C 의 실제 트리로 다시 잰다 · 만든 길과 독립): ⑴ C 의 경로 ⊆ B ∪ ALLOW ⑵ C 의 경로 = 계산한 공개 집합 ⑶ C↔H 차 = withheld ⑷ C 부모 = B
# recheck 자식은 push 가 막힌 env 로 돈다: git pushInsteadOf(/ · file:// · https:// · git@ · ssh:// → 없는 전송기) + PATH 앞 가짜 gh(rc 97).
#   읽기(fetch·ls-remote)는 그대로 · 자식이 GIT_CONFIG_* 를 스스로 덮으면 못 막는다(정직한 한계).
# 출력 끝 줄: `PUBCAND H=<> B=<> C=<> ref=<> public=<n> new=<n> withheld=<n> gate1=<0|1> recheck_rc=<n|skip> rc=<n>`
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
    echo pub > a.txt; echo old > gone.txt; $GIT add a.txt gone.txt; $GIT commit -qm base; $GIT tag base0
    mkdir -p docs/integ-1116 src new; echo x > docs/integ-1116/gate.sh; echo s > src/m.rs; echo h > HANDOFF.x.md
    echo n > new/pub.md; echo pub2 > a.txt; $GIT rm -q gone.txt
    $GIT add -A; $GIT commit -qm head
    $GIT init -q --bare "$T/remote.git"; $GIT remote add origin "$T/remote.git"
  ) >/dev/null 2>&1 || { echo "self-test: 임시 저장소 실패"; rm -rf "$T"; return 2; }
  printf 'src/m.rs\nnew/pub.md\n' > "$T/A"; echo "cand 1" > "$T/M"
  printf '#!/bin/sh\necho "fake recheck $1 VERDICT=$VERDICT SRC=$SRC" > "%s/rc.log"\nexit "${FAKE_RC:-0}"\n' "$T" > "$T/rk.sh"
  local R="$T/r" out rc C
  run() { ( cd "$R" && env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_AUTHOR_NAME=t GIT_COMMITTER_NAME=t \
      GIT_AUTHOR_EMAIL="t$(printf '\100')t.invalid" GIT_COMMITTER_EMAIL="t$(printf '\100')t.invalid" \
      PUB_BASE=base0 PUB_MSG="$T/M" PUB_RECHECK="$T/rk.sh" "$@" bash "$me" HEAD ); }
  echo "[pubcand self-test]"
  out=$(run PUB_ALLOW="$T/A" PUB_WITHHELD_OUT="$T/W" 2>&1); rc=$?
  C=$($GIT -C "$R" rev-parse -q --verify refs/heads/cand/1116-rc)
  [ $rc -eq 0 ] && ok "양성 rc 0" || bad "양성 rc=$rc: $out"
  [ -n "$C" ] && [ "$($GIT -C "$R" rev-parse "$C^@")" = "$($GIT -C "$R" rev-parse base0)" ] && ok "C 부모 = B 하나" || bad "C 부모"
  [ "$($GIT -C "$R" ls-tree -r --name-only "$C" | tr '\n' ' ')" = "a.txt new/pub.md src/m.rs " ] && ok "C 트리 = (H∩B) ∪ ALLOW(B 에서 지운 파일은 C 에도 없음)" || bad "C 트리: $($GIT -C "$R" ls-tree -r --name-only "$C" | tr '\n' ' ')"
  [ "$($GIT -C "$R" show "$C:a.txt")" = pub2 ] && ok "B 에 있던 파일은 H 내용으로" || bad "a.txt 내용"
  [ "$(tr '\n' ' ' < "$T/W" 2>/dev/null)" = "HANDOFF.x.md docs/integ-1116/gate.sh " ] && echo "$out" | grep -q "withheld=2" && ok "목록 밖 새 파일 = 공개 안 됨 + 보고(2)" || bad "withheld 보고: $(cat "$T/W" 2>&1)"
  grep -q "fake recheck $C VERDICT=$($GIT -C "$R" rev-parse base0) SRC=" "$T/rc.log" 2>/dev/null && ok "recheck 가 C·VERDICT=B 로 불림" || bad "recheck 호출: $(cat "$T/rc.log" 2>&1)"
  out=$(run PUB_ALLOW="$T/A" 2>&1); rc=$?
  [ $rc -eq 2 ] && echo "$out" | grep -q "이미 있음" && ok "있는 ref 덮어쓰기 거부(rc 2)" || bad "ref 덮어쓰기 rc=$rc"
  out=$(run PUB_ALLOW="$T/A" PUB_FORCE=1 FAKE_RC=1 2>&1); rc=$?
  [ $rc -eq 1 ] && ok "recheck rc 1 → rc 1" || bad "recheck rc1 전달 rc=$rc"
  printf 'src/m.rs\ndocs/integ-1116/gate.sh\n' > "$T/A2"
  out=$(run PUB_ALLOW="$T/A2" PUB_FORCE=1 2>&1); rc=$?
  [ $rc -eq 2 ] && echo "$out" | grep -q "docs/integ-1116/gate.sh" && ok "지킴 폴더 경로를 허용 목록에 올림 → rc 2" || bad "지킴 폴더 rc=$rc"
  printf 'src/m.rs\nno/such.md\n' > "$T/A3"
  out=$(run PUB_ALLOW="$T/A3" PUB_FORCE=1 2>&1); rc=$?
  [ $rc -eq 2 ] && echo "$out" | grep -q "no/such.md" && ok "H 에 없는 허용 줄 → rc 2" || bad "없는 줄 rc=$rc"
  out=$(run PUB_ALLOW="$T/A" PUB_FORCE=1 PUB_BASE=no-such 2>&1); rc=$?
  [ $rc -eq 2 ] && ok "못 찾는 B → rc 2" || bad "B rc=$rc"
  : > "$T/A0"
  out=$(run PUB_ALLOW="$T/A0" PUB_FORCE=1 2>&1); rc=$?
  C=$($GIT -C "$R" rev-parse -q --verify refs/heads/cand/1116-rc)
  [ $rc -eq 0 ] && [ "$($GIT -C "$R" ls-tree -r --name-only "$C" | tr '\n' ' ')" = "a.txt " ] && ok "빈 허용 목록 = B 경로만(새 파일 0 공개)" || bad "빈 허용 목록 rc=$rc"
  out=$(run PUB_ALLOW="$T/no-file" PUB_FORCE=1 2>&1); rc=$?
  [ $rc -eq 2 ] && ok "허용 목록 파일 없음 → rc 2" || bad "허용 목록 없음 rc=$rc"
  out=$(run PUB_ALLOW="$T/A" PUB_FORCE=1 PUB_NO_RECHECK=1 2>&1); rc=$?
  [ $rc -eq 4 ] && ok "recheck 생략 → rc 4(성공 아님)" || bad "recheck 생략 rc=$rc"
  printf '#!/bin/sh\ngit push -q origin "$1:refs/heads/leak" 2>/dev/null; gh repo view >/dev/null 2>&1; echo "gh=$?" > "%s/gh.rc"; exit 0\n' "$T" > "$T/rk2.sh"
  out=$(run PUB_ALLOW="$T/A" PUB_FORCE=1 PUB_RECHECK="$T/rk2.sh" 2>&1); rc=$?
  if [ -z "$($GIT -C "$T/remote.git" for-each-ref)" ] && grep -q "gh=97" "$T/gh.rc" 2>/dev/null; then ok "recheck 안 push·gh 차단(원격 ref 0 · gh rc 97)"; else bad "recheck 안 push/gh 차단 실패: $($GIT -C "$T/remote.git" for-each-ref) $(cat "$T/gh.rc" 2>&1)"; fi
  out=$(cd "$R" && bash "$me" --derive-allow HEAD base0 /dev/stdin <<< "HANDOFF.x.md" 2>&1 | tr '\n' ' ')
  [ "$out" = "docs/integ-1116/gate.sh new/pub.md src/m.rs " ] && ok "--derive-allow = H−B−제외목록" || bad "--derive-allow: $out"
  # 자기 검사: 집행 본문(자기 검체 함수 뒤 · 주석 아닌 줄)에 push·tag 쓰기·gh 명령이 없다(검체 함수는 임시 저장소에 태그를 단다)
  if sed -n '/^\[ "\${1:-}" = --self-test \]/,$p' "$me" | grep -vE '^\s*#' | grep -nE '(^|[;&|( ]+)(\$GIT|git)( -C [^ ]+)? (push|tag)\b|(^|[;&|( ]+)gh ' >/dev/null; then bad "본문에 push/tag/gh 명령"; else ok "본문에 push·tag·gh 명령 0"; fi
  rm -rf "$T"
  [ $fails -eq 0 ] && { echo "[pubcand self-test] OK"; return 0; } || { echo "[pubcand self-test] FAIL $fails"; return 1; }
}

[ "${1:-}" = --self-test ] && { self_test; exit $?; }
if [ "${1:-}" = --derive-allow ]; then
  [ $# -eq 4 ] || { echo "사용: --derive-allow <H> <B> <제외목록>" >&2; exit 2; }
  dw=$(mktemp -d "${TMPDIR:-/tmp}/pubdXXXX") || exit 2
  $GIT ls-tree -r --name-only "$2" | LC_ALL=C sort > "$dw/h" || exit 2
  $GIT ls-tree -r --name-only "$3" | LC_ALL=C sort > "$dw/b" || exit 2
  grep -v '^[[:space:]]*$' "$4" | LC_ALL=C sort -u > "$dw/x" || true
  LC_ALL=C comm -23 "$dw/h" "$dw/b" | LC_ALL=C comm -23 - "$dw/x"
  rm -rf "$dw"; exit 0
fi

H_IN=${1:-HEAD}
A=${PUB_ALLOW:-}; M=${PUB_MSG:-}
B_IN=${PUB_BASE:-origin/main}; REF=${PUB_REF:-refs/heads/cand/1116-rc}
RK=${PUB_RECHECK:-$HOME/axdev/workers/cysr-public-check-1118/recheck.sh}
GUARD=${PUB_GUARD_DIRS:-docs/integ-1116}
H=""; B=""; C=""; G1=""; RRC=skip; NPUB=na; NNEW=na; NWH=na
fin() { echo "PUBCAND H=${H:0:12} B=${B:0:12} C=${C:0:12} ref=$REF public=$NPUB new=$NNEW withheld=$NWH gate1=${G1:-na} recheck_rc=$RRC rc=$1"; exit "$1"; }
die() { echo "✗ $*" >&2; fin 2; }

[ -n "$A" ] && [ -f "$A" ] || die "PUB_ALLOW(새 공개 허용 목록 파일)가 없다 — 새 파일을 하나도 안 내려면 빈 파일을 주라"
[ -n "$M" ] && [ -s "$M" ] || die "PUB_MSG(커밋 메시지 파일)가 없거나 비었다"
H=$($GIT rev-parse --verify -q "$H_IN^{commit}") || die "H($H_IN)를 못 찾음"
B=$($GIT rev-parse --verify -q "$B_IN^{commit}") || die "B($B_IN)를 못 찾음 — fetch 했는가"
OLD=$($GIT rev-parse --verify -q "$REF" || true)
[ -z "$OLD" ] || [ "${PUB_FORCE:-0}" = 1 ] || die "$REF 이미 있음(${OLD:0:12}) — 덮어쓰려면 PUB_FORCE=1"

W=$(mktemp -d "${TMPDIR:-/tmp}/pubcXXXX") || die "임시 폴더"
trap 'rm -rf "$W"' EXIT
grep -v '^[[:space:]]*$' "$A" | LC_ALL=C sort -u > "$W/allow"
$GIT ls-tree -r --name-only "$H" | LC_ALL=C sort > "$W/htree"
$GIT ls-tree -r --name-only "$B" | LC_ALL=C sort > "$W/btree"
# 허용 줄이 H 에 실재하는가(없는 줄 = 낡은 목록 — 조용히 무시하면 「냈다고 믿은 파일」 이 빠진다)
LC_ALL=C comm -23 "$W/allow" "$W/htree" > "$W/absent"
[ -s "$W/absent" ] && { echo "✗ 허용 목록 줄이 H 트리에 없음 $(wc -l < "$W/absent" | tr -d ' ')건:" >&2; sed 's/^/    /' "$W/absent" >&2; die "목록 갱신 필요"; }
# 지킴 폴더(내부 게이트 도구 폴더)의 경로는 허용 목록에 올 수 없다
: > "$W/guard"
for g in $GUARD; do grep -E "^${g%/}/" "$W/allow" >> "$W/guard"; done
[ -s "$W/guard" ] && { echo "✗ 지킴 폴더($GUARD)의 경로를 허용 목록에 올렸다:" >&2; sed 's/^/    /' "$W/guard" >&2; die "내부 도구는 공개하지 않는다"; }
LC_ALL=C comm -12 "$W/allow" "$W/btree" > "$W/redundant"
[ -s "$W/redundant" ] && echo "ℹ 허용 목록 중 이미 B 에 있는 경로 $(wc -l < "$W/redundant" | tr -d ' ')건(뜻 없음 · 지워도 됨)"
# 공개 집합 = (H ∩ B) ∪ ALLOW · withheld = H − 공개 집합
LC_ALL=C comm -12 "$W/htree" "$W/btree" | LC_ALL=C sort -u - "$W/allow" > "$W/public"
LC_ALL=C comm -23 "$W/htree" "$W/public" > "$W/withheld"
NPUB=$(wc -l < "$W/public" | tr -d ' '); NWH=$(wc -l < "$W/withheld" | tr -d ' ')
NNEW=$(LC_ALL=C comm -23 "$W/public" "$W/btree" | wc -l | tr -d ' ')

export GIT_INDEX_FILE="$W/index"
$GIT read-tree "$H" || die "read-tree"
if [ -s "$W/withheld" ]; then tr '\n' '\0' < "$W/withheld" | xargs -0 $GIT update-index --force-remove -- || die "update-index"; fi
T=$($GIT write-tree) || die "write-tree"
C=$($GIT commit-tree "$T" -p "$B" -F "$M") || die "commit-tree"
unset GIT_INDEX_FILE
$GIT update-ref -m "pubcand.sh H=${H:0:12}" "$REF" "$C" ${OLD:+"$OLD"} || die "update-ref"
echo "C=$C (ref $REF${OLD:+ · 이전 ${OLD:0:12}}) · 작성자 = $($GIT log -1 --format='%an' "$C")"
echo "공개 안 된 새 파일(withheld) ${NWH}건 — 공개하려면 PUB_ALLOW 에 더한다:"
sed 's/^/    /' "$W/withheld"
[ -n "${PUB_WITHHELD_OUT:-}" ] && cp "$W/withheld" "$PUB_WITHHELD_OUT"

# 관문 1 — C 의 실제 트리로 다시 잰다(위 계산과 독립)
$GIT ls-tree -r --name-only "$C" | LC_ALL=C sort > "$W/ctree"
LC_ALL=C sort -u "$W/btree" "$W/allow" > "$W/ok"
LC_ALL=C comm -23 "$W/ctree" "$W/ok" > "$W/leak"
if [ -s "$W/leak" ]; then G1=1; echo "✗ 관문 1 ⑴: C 에 B·허용 목록 밖 경로 $(wc -l < "$W/leak" | tr -d ' ')건:"; sed 's/^/    /' "$W/leak"; fin 2; fi
cmp -s "$W/ctree" "$W/public" || { G1=1; echo "✗ 관문 1 ⑵: C 트리 ≠ 계산한 공개 집합"; diff "$W/ctree" "$W/public" | sed 's/^/    /'; fin 2; }
$GIT diff --name-only "$C" "$H" | LC_ALL=C sort > "$W/diff"
cmp -s "$W/diff" "$W/withheld" || { G1=1; echo "✗ 관문 1 ⑶: C↔H 차 ≠ withheld"; diff "$W/diff" "$W/withheld" | sed 's/^/    /'; fin 2; }
[ "$($GIT rev-parse "$C^@")" = "$B" ] || { G1=1; echo "✗ 관문 1 ⑷: C 의 부모가 B 하나가 아님"; fin 2; }
G1=0; echo "✓ 관문 1: C ⊆ B ∪ 허용($NNEW 새 경로) · C = 공개 집합 $NPUB · C↔H 차 = withheld $NWH · 부모 = B"

[ "${PUB_NO_RECHECK:-0}" = 1 ] && { echo "⚠ recheck 생략(PUB_NO_RECHECK=1) — 공개 판정 미완"; fin 4; }
[ -f "$RK" ] || die "recheck 스크립트 없음: $RK"
mkdir -p "$W/nogh" && printf '#!/bin/sh\necho "pubcand: github CLI 차단(recheck 안)" >&2\nexit 97\n' > "$W/nogh/gh" && chmod +x "$W/nogh/gh"
NP=url.pubcand-no-push://.pushInsteadOf
env GIT_CONFIG_COUNT=5 GIT_CONFIG_KEY_0=$NP GIT_CONFIG_VALUE_0=/ GIT_CONFIG_KEY_1=$NP GIT_CONFIG_VALUE_1=file:// \
    GIT_CONFIG_KEY_2=$NP GIT_CONFIG_VALUE_2=https:// GIT_CONFIG_KEY_3=$NP GIT_CONFIG_VALUE_3=git@ GIT_CONFIG_KEY_4=$NP GIT_CONFIG_VALUE_4=ssh:// \
    PATH="$W/nogh:$PATH" SRC="$($GIT rev-parse --show-toplevel)" VERDICT="$B" bash "$RK" "$C"; RRC=$?
case $RRC in 0) fin 0 ;; 1) fin 1 ;; 3) fin 3 ;; *) fin 2 ;; esac
