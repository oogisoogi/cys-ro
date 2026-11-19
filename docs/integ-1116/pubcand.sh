#!/bin/bash
# pubcand.sh — 공개 후보 커밋 C 만들기(**허용 목록** · 부모 B 하나) + 관문 1 + recheck 호출. push 없음.
#   근거 = 공개 점검 보고 §4 집행 순서(임시 GIT_INDEX_FILE · commit-tree · 로컬 ref 1개)를 손 대신 한 명령으로.
#   ★규칙(유출 쪽 실패가 안전한 쪽): C 의 트리 = H 의 파일 중 **B(이미 공개된 판)에 같은 경로가 있는 것** + **PUB_ALLOW 에 적힌 새 경로**뿐.
#     H 에 새로 생긴 파일이 목록에 없으면 = 공개 안 됨 + 보고(withheld). 목록을 잊으면 덜 공개될 뿐 더 공개되지 않는다
#     (종전 제외 목록 방식은 목록을 잊으면 공개됐다 — codex 1R #1 · master 처분 11-20 #8).
#   ★이 스크립트는 git push·태그·gh 를 부르지 않는다(자기 검체가 집행 본문에 그 명령이 없음을 잰다).
#   ★작업트리 안에서만 쓴다 — bare 저장소에서는 임시 색인 update-index 가 rc 2 로 멈춘다(안전한 쪽).
#
# 사용: bash docs/integ-1116/pubcand.sh [<H>]                          # H 기본 = HEAD
#       bash docs/integ-1116/pubcand.sh --derive-allow <H> <B> <제외목록>   # 옮김 도우미: H−B−제외목록 = 새 공개 경로를 출력
#             제외 목록이 없음·읽을 수 없음·비었음(빈 줄만 포함) = rc 2 · 결과에 지킴 폴더 경로가 섞이면 rc 2(출력 없음)
#       bash docs/integ-1116/pubcand.sh --self-test                     # 임시 저장소 + 가짜 recheck 로 양성·음성 대조
# 환경(필수): PUB_ALLOW = 새 공개 허용 경로 목록(한 줄에 경로 하나 · B 에 없는 경로만 뜻이 있음 · 비어도 됨) · PUB_MSG = 커밋 메시지 파일
# 환경(선택): PUB_BASE(기본 origin/main · refs/remotes/origin/* 어느 것에서 닿는 커밋이어야 한다 = 공개된 판 · 아니면 rc 2)
#             PUB_REF(기본 refs/heads/cand/1116-rc · 관문 1 실패 때 C 는 <PUB_REF>-rejected 에 둔다) · PUB_FORCE=1(있는 ref 덮어쓰기)
#             PUB_RECHECK(기본 ~/axdev/workers/cysr-public-check-1118/recheck.sh) · PUB_NO_RECHECK=1(관문 1까지만)
#             PUB_GUARD_DIRS(기본 docs/integ-1116 — 이 폴더의 새 경로는 허용 목록에 올 수 없다 · 내부 게이트 도구 · 공백 구분)
#             PUB_WITHHELD_OUT = 공개 안 된 새 파일 목록을 이 파일에도 쓴다(표준 출력에는 늘 전부)
# 경로 목록(허용·제외·withheld) = 한 줄에 경로 하나 · 날 바이트(git 의 "\355…" 인용꼴 아님) · 이름 속 줄바꿈은 \001 로 적는다.
#   git 은 -z 로만 읽는다(한글·탭·따옴표·줄바꿈 이름도 그대로) · \001 이 든 이름이 H·B 에 있으면 rc 2(그 이름은 다루지 않는다).
# 종료: 0 = C 생성 · 관문 1 통과 · recheck 깨끗 | 1 = recheck 가 읽을 항목 있음(공개 전 멈춤 · 사람 판정)
#       2 = 입력·도구 실패 또는 관문 1 불일치(C 는 만들었으면 <PUB_REF>-rejected 에 둔다 · 판정 근거로) | 3 = recheck 가 이력 불일치 보고
#       4 = PUB_NO_RECHECK=1 — C·관문 1 까지만(recheck 생략 = 공개 판정 미완 · 성공 코드 아님)
# 관문 1(C 의 실제 트리로 다시 잰다 · 만든 길과 독립): ⑴ C 의 경로 ⊆ B ∪ ALLOW ⑵ C 의 경로 = 계산한 공개 집합 ⑶ C↔H 차 = withheld ⑷ C 부모 = B
# recheck 자식은 push 가 막힌 env(GIT_CONFIG_*)로 돈다: ① url.pubcand-no-push://.pushInsteadOf="" (빈 접두 = 모든 push 주소 ·
#   명령줄 상대 경로·scp 꼴 포함) ② 이 저장소의 각 원격 remote.<이름>.pushurl=pubcand-no-push:// ③ 이미 적힌 pushurl 값마다
#   url.pubcand-no-push://.insteadOf=<그 값>(pushurl 은 여러 값이면 전부에 push 하고 pushInsteadOf 가 안 걸린다 — 덧씌움만으로는
#   원래 pushurl 로 나간다 · git 2.50.1 실측) + PATH 앞 가짜 gh(rc 97). 읽기(fetch·ls-remote)는 그대로(url = pushurl 인 원격은 읽기도 막힘).
#   정직한 한계: 자식이 GIT_CONFIG_*·git -c 를 스스로 덮으면 · 명령줄 주소에 사용자 설정의 더 긴 pushInsteadOf 가 걸리면 ·
#   이 저장소 밖 다른 저장소의 pushurl 명시 원격으로 push 하면 못 막는다(그 밖의 상대 경로 원격·pushurl 명시 원격은 막는다).
# 출력 끝 줄: `PUBCAND H=<> B=<> C=<> ref=<> public=<n> new=<n> withheld=<n> gate1=<0|1> recheck_rc=<n|skip> rc=<n>`
set -u
GIT=/usr/bin/git
GUARD=${PUB_GUARD_DIRS:-docs/integ-1116}

# lstree <트리> <출력> — 경로 목록(머리말의 줄 꼴 · 정렬). rc 2 = git 실패 · rc 3 = \001 이 든 이름
lstree() {
  $GIT ls-tree -r -z --name-only "$1" > "$2.z" || return 2
  [ "$(LC_ALL=C tr -dc '\001' < "$2.z" | wc -c | tr -d ' ')" = 0 ] || return 3
  LC_ALL=C tr '\n\0' '\001\n' < "$2.z" | LC_ALL=C sort > "$2"
}
# listfile <목록 파일> <출력> — 빈 줄을 뺀 정렬·중복 제거. rc 2 = 읽기 실패(grep rc 2 를 삼키지 않는다)
listfile() {
  local rc=0
  LC_ALL=C grep -v '^[[:space:]]*$' "$1" > "$2.raw" || rc=$?
  [ $rc -le 1 ] || return 2
  LC_ALL=C sort -u "$2.raw" > "$2"
}
# guardhits <목록> <출력> — 지킴 폴더 아래 경로
guardhits() {
  : > "$2"; local g
  for g in $GUARD; do LC_ALL=C grep -E "^${g%/}/" "$1" >> "$2"; done
  return 0
}

self_test() {
  local T; T=$(mktemp -d "${TMPDIR:-/tmp}/pubcXXXX") || return 2
  local me; me="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  local fails=0 NL=$'\n' TB=$'\t' SOH=$'\001'
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
    # git 이 인용꼴로 내는 이름(한글·공백 · 탭 · 줄바꿈 · 큰따옴표) — 넷은 목록 밖 · 「공개 메모.md」 는 허용 목록에
    echo k > "비밀 노트.md"; echo t > "t${TB}ab.md"; echo l > "nl${NL}x.md"; echo q > 'q"uote.md'; echo p > "공개 메모.md"
    $GIT add -A; $GIT commit -qm head
    $GIT update-ref refs/remotes/origin/main base0
    $GIT init -q --bare "$T/remote.git"; $GIT remote add origin "$T/remote.git"
    # push 차단 대상: 상대 경로 원격 · pushurl 명시 원격(url 은 닿지 않는 주소) · 명령줄 상대 경로(remote4)
    $GIT init -q --bare "$T/remote2.git"; $GIT remote add orel ../remote2.git
    $GIT init -q --bare "$T/remote3.git"; $GIT remote add opu https://example.invalid/x.git; $GIT config remote.opu.pushurl "$T/remote3.git"
    $GIT init -q --bare "$T/remote4.git"
    # 사용자 설정의 더 긴 pushInsteadOf(「rel5:」 → 실제 폴더)가 빈 접두를 이기는 원격 — 원격별 pushurl 덧씌움이 막는다
    $GIT init -q --bare "$T/remote5.git"; $GIT config "url.$T/.pushInsteadOf" rel5:; $GIT remote add o5 rel5:remote5.git
  ) >/dev/null 2>&1 || { echo "self-test: 임시 저장소 실패"; rm -rf "$T"; return 2; }
  printf 'src/m.rs\nnew/pub.md\n공개 메모.md\n' > "$T/A"; echo "cand 1" > "$T/M"
  printf '#!/bin/sh\necho "fake recheck $1 VERDICT=$VERDICT SRC=$SRC" > "%s/rc.log"\nexit "${FAKE_RC:-0}"\n' "$T" > "$T/rk.sh"
  local R="$T/r" out rc C C0 RUN_ME=""
  run() { ( cd "$R" && env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_AUTHOR_NAME=t GIT_COMMITTER_NAME=t \
      GIT_AUTHOR_EMAIL="t$(printf '\100')t.invalid" GIT_COMMITTER_EMAIL="t$(printf '\100')t.invalid" \
      PUB_BASE=base0 PUB_MSG="$T/M" PUB_RECHECK="$T/rk.sh" "$@" bash "${RUN_ME:-$me}" HEAD ); }
  ctree() { $GIT -C "$R" ls-tree -r -z --name-only "$1" | tr '\0' ' '; }
  echo "[pubcand self-test]"
  out=$(run PUB_ALLOW="$T/A" PUB_WITHHELD_OUT="$T/W" 2>&1); rc=$?
  C=$($GIT -C "$R" rev-parse -q --verify refs/heads/cand/1116-rc)
  [ $rc -eq 0 ] && ok "양성 rc 0" || bad "양성 rc=$rc: $out"
  [ -n "$C" ] && [ "$($GIT -C "$R" rev-parse "$C^@")" = "$($GIT -C "$R" rev-parse base0)" ] && ok "C 부모 = B 하나" || bad "C 부모"
  [ "$(ctree "$C")" = "a.txt new/pub.md src/m.rs 공개 메모.md " ] && ok "C 트리 = (H∩B) ∪ ALLOW(B 에서 지운 파일은 C 에도 없음 · 한글·공백 허용 줄 공개)" || bad "C 트리: $(ctree "$C")"
  [ "$($GIT -C "$R" show "$C:a.txt")" = pub2 ] && ok "B 에 있던 파일은 H 내용으로" || bad "a.txt 내용"
  [ "$(tr '\n' ' ' < "$T/W" 2>/dev/null)" = "HANDOFF.x.md docs/integ-1116/gate.sh nl${SOH}x.md q\"uote.md t${TB}ab.md 비밀 노트.md " ] && echo "$out" | grep -q "withheld=6" \
    && ok "목록 밖 새 파일 = 공개 안 됨 + 보고(6 · 한글·탭·줄바꿈·따옴표 이름도 C 에서 빠짐)" || bad "withheld 보고: $(cat -v "$T/W" 2>&1) · $out"
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
  out=$(run PUB_ALLOW="$T/A" PUB_FORCE=1 PUB_BASE=HEAD 2>&1); rc=$?
  [ $rc -eq 2 ] && echo "$out" | grep -q "닿지 않는다" && ok "B 가 refs/remotes/origin/* 에서 안 닿음(PUB_BASE=HEAD) → rc 2" || bad "공개 안 된 B rc=$rc: $out"
  : > "$T/A0"
  out=$(run PUB_ALLOW="$T/A0" PUB_FORCE=1 2>&1); rc=$?
  C=$($GIT -C "$R" rev-parse -q --verify refs/heads/cand/1116-rc)
  [ $rc -eq 0 ] && [ "$(ctree "$C")" = "a.txt " ] && ok "빈 허용 목록 = B 경로만(새 파일 0 공개)" || bad "빈 허용 목록 rc=$rc"
  out=$(run PUB_ALLOW="$T/no-file" PUB_FORCE=1 2>&1); rc=$?
  [ $rc -eq 2 ] && ok "허용 목록 파일 없음 → rc 2" || bad "허용 목록 없음 rc=$rc"
  cp "$T/A" "$T/A9"; chmod 000 "$T/A9"
  out=$(run PUB_ALLOW="$T/A9" PUB_FORCE=1 2>&1); rc=$?
  [ $rc -eq 2 ] && echo "$out" | grep -q "허용 목록 읽기 실패" && ok "허용 목록 읽기 불가 → rc 2(빈 목록으로 삼키지 않음)" || bad "허용 목록 읽기 불가 rc=$rc: $out"
  out=$(run PUB_ALLOW="$T/A" PUB_FORCE=1 PUB_NO_RECHECK=1 2>&1); rc=$?
  [ $rc -eq 4 ] && ok "recheck 생략 → rc 4(성공 아님)" || bad "recheck 생략 rc=$rc"
  printf '#!/bin/sh\nfor t in origin orel opu o5 ../remote4.git; do git push -q "$t" "$1:refs/heads/leak" 2>/dev/null; done; gh repo view >/dev/null 2>&1; echo "gh=$?" > "%s/gh.rc"; exit 0\n' "$T" > "$T/rk2.sh"
  out=$(run PUB_ALLOW="$T/A" PUB_FORCE=1 PUB_RECHECK="$T/rk2.sh" 2>&1); rc=$?
  local leaks="" b
  for b in remote remote2 remote3 remote4 remote5; do [ -z "$($GIT -C "$T/$b.git" for-each-ref)" ] || leaks="$leaks $b"; done
  if [ -z "$leaks" ] && grep -q "gh=97" "$T/gh.rc" 2>/dev/null; then ok "recheck 안 push·gh 차단(절대 경로·상대 경로·pushurl 명시 원격·더 긴 사용자 pushInsteadOf·명령줄 상대 경로 = 원격 ref 0 · gh rc 97)"; else bad "recheck 안 push/gh 차단 실패: 샘 =$leaks · $(cat "$T/gh.rc" 2>&1)"; fi
  # 관문 1 실패 → C 는 <PUB_REF>-rejected 에(정상 후보 ref 는 그대로) — withheld 를 안 지우는 사본으로 실패를 만든다
  sed 's/| xargs -0 \$GIT update-index --force-remove --/| cat >\/dev\/null/' "$me" > "$T/mut.sh"
  C0=$($GIT -C "$R" rev-parse -q --verify refs/heads/cand/1116-rc)
  if cmp -s "$me" "$T/mut.sh"; then bad "관문 1 실패 사본을 못 만듦(본문 꼴이 바뀜)"; else
    out=$(RUN_ME="$T/mut.sh" run PUB_ALLOW="$T/A" PUB_FORCE=1 2>&1); rc=$?
    C=$($GIT -C "$R" rev-parse -q --verify refs/heads/cand/1116-rc-rejected)
    [ $rc -eq 2 ] && echo "$out" | grep -q "관문 1 ⑴" && [ -n "$C" ] && [ "$C" != "$C0" ] && $GIT -C "$R" cat-file -e "$C:HANDOFF.x.md" \
      && [ "$($GIT -C "$R" rev-parse -q --verify refs/heads/cand/1116-rc)" = "$C0" ] && echo "$out" | grep -q "ref=refs/heads/cand/1116-rc-rejected" \
      && ok "관문 1 실패 → rc 2 · C 는 cand/1116-rc-rejected · 정상 후보 ref 그대로" || bad "관문 1 실패 처리 rc=$rc: $out"
  fi
  # --derive-allow(옮김 도우미)
  printf 'HANDOFF.x.md\ndocs/integ-1116/gate.sh\n비밀 노트.md\n' > "$T/X"
  out=$(cd "$R" && bash "$me" --derive-allow HEAD base0 "$T/X" 2>&1 | tr '\n' ' ')
  [ "$out" = "new/pub.md nl${SOH}x.md q\"uote.md src/m.rs t${TB}ab.md 공개 메모.md " ] && ok "--derive-allow = H−B−제외목록(인용꼴 이름도 날 바이트)" || bad "--derive-allow: $(printf '%s' "$out" | cat -v)"
  out=$(cd "$R" && bash "$me" --derive-allow HEAD base0 "$T/no-such" 2>"$T/err"); rc=$?
  [ $rc -eq 2 ] && [ -z "$out" ] && grep -q "없거나 읽을 수 없음" "$T/err" && ok "--derive-allow 제외 목록 없음 → rc 2 · 출력 0" || bad "--derive-allow 목록 없음 rc=$rc: $out"
  printf '\n  \n' > "$T/X0"
  # 빈 목록 검사만 따로 재도록 지킴 폴더를 비킨다(지킴 폴더 검사가 대신 막아 주면 이 검사가 빠져도 모른다)
  out=$(cd "$R" && export PUB_GUARD_DIRS=no/such; bash "$me" --derive-allow HEAD base0 "$T/X0" 2>&1; echo "rc=$?"; bash "$me" --derive-allow HEAD base0 /dev/null 2>&1; echo "rc=$?")
  [ "$(echo $out | grep -o 'rc=[0-9]*' | tr '\n' ' ')" = "rc=2 rc=2 " ] && [ "$(echo "$out" | grep -c "비었다")" = 2 ] && ok "--derive-allow 빈 제외 목록(빈 줄만 · /dev/null) → rc 2 · 출력 0" || bad "--derive-allow 빈 목록: $out"
  printf 'HANDOFF.x.md\n' > "$T/X2"
  out=$(cd "$R" && bash "$me" --derive-allow HEAD base0 "$T/X2" 2>"$T/err"); rc=$?
  [ $rc -eq 2 ] && [ -z "$out" ] && grep -q "docs/integ-1116/gate.sh" "$T/err" && ok "--derive-allow 결과에 지킴 폴더 경로 → rc 2 · 출력 0" || bad "--derive-allow 지킴 폴더 rc=$rc: $out"
  # 자기 검사: 집행 본문(자기 검체 함수 뒤 · 주석 아닌 줄)에 push·tag 쓰기·gh 명령이 없다(검체 함수는 임시 저장소에 태그를 단다)
  if sed -n '/^\[ "\${1:-}" = --self-test \]/,$p' "$me" | grep -vE '^\s*#' | grep -nE '(^|[;&|( ]+)(\$GIT|git)( -C [^ ]+)? (push|tag)\b|(^|[;&|( ]+)gh ' >/dev/null; then bad "본문에 push/tag/gh 명령"; else ok "본문에 push·tag·gh 명령 0"; fi
  rm -rf "$T"
  [ $fails -eq 0 ] && { echo "[pubcand self-test] OK"; return 0; } || { echo "[pubcand self-test] FAIL $fails"; return 1; }
}

[ "${1:-}" = --self-test ] && { self_test; exit $?; }
if [ "${1:-}" = --derive-allow ]; then
  [ $# -eq 4 ] || { echo "사용: --derive-allow <H> <B> <제외목록>" >&2; exit 2; }
  [ -r "$4" ] && [ ! -d "$4" ] || { echo "✗ 제외 목록 파일이 없거나 읽을 수 없음: $4" >&2; exit 2; }
  dw=$(mktemp -d "${TMPDIR:-/tmp}/pubdXXXX") || exit 2
  trap 'rm -rf "$dw"' EXIT
  $GIT rev-parse -q --verify "$2^{commit}" >/dev/null && $GIT rev-parse -q --verify "$3^{commit}" >/dev/null \
    || { echo "✗ H($2) 또는 B($3)를 못 찾음" >&2; exit 2; }
  lstree "$2" "$dw/h" || { echo "✗ H 트리 읽기 실패(rc $? · 3 = \\001 이 든 이름)" >&2; exit 2; }
  lstree "$3" "$dw/b" || { echo "✗ B 트리 읽기 실패(rc $? · 3 = \\001 이 든 이름)" >&2; exit 2; }
  listfile "$4" "$dw/x" || { echo "✗ 제외 목록 읽기 실패: $4" >&2; exit 2; }
  [ -s "$dw/x" ] || { echo "✗ 제외 목록이 비었다($4) — 빈 목록이면 H 의 새 파일 전부가 나온다" >&2; exit 2; }
  LC_ALL=C comm -23 "$dw/h" "$dw/b" | LC_ALL=C comm -23 - "$dw/x" > "$dw/out"
  guardhits "$dw/out" "$dw/g"
  [ -s "$dw/g" ] && { echo "✗ 결과에 지킴 폴더($GUARD)의 경로 $(wc -l < "$dw/g" | tr -d ' ')건 — 제외 목록에 더하라(내부 도구는 공개하지 않는다):" >&2; sed 's/^/    /' "$dw/g" >&2; exit 2; }
  cat "$dw/out"; exit 0
fi

H_IN=${1:-HEAD}
A=${PUB_ALLOW:-}; M=${PUB_MSG:-}
B_IN=${PUB_BASE:-origin/main}; REF=${PUB_REF:-refs/heads/cand/1116-rc}; REJ="${REF}-rejected"; REF_OUT=$REF
RK=${PUB_RECHECK:-$HOME/axdev/workers/cysr-public-check-1118/recheck.sh}
H=""; B=""; C=""; G1=""; RRC=skip; NPUB=na; NNEW=na; NWH=na
fin() { echo "PUBCAND H=${H:0:12} B=${B:0:12} C=${C:0:12} ref=$REF_OUT public=$NPUB new=$NNEW withheld=$NWH gate1=${G1:-na} recheck_rc=$RRC rc=$1"; exit "$1"; }
die() { echo "✗ $*" >&2; fin 2; }

[ -n "$A" ] && [ -f "$A" ] || die "PUB_ALLOW(새 공개 허용 목록 파일)가 없다 — 새 파일을 하나도 안 내려면 빈 파일을 주라"
[ -n "$M" ] && [ -s "$M" ] || die "PUB_MSG(커밋 메시지 파일)가 없거나 비었다"
H=$($GIT rev-parse --verify -q "$H_IN^{commit}") || die "H($H_IN)를 못 찾음"
B=$($GIT rev-parse --verify -q "$B_IN^{commit}") || die "B($B_IN)를 못 찾음 — fetch 했는가"
# B 는 이미 공개된 판이어야 한다 — PUB_BASE=HEAD·내부 가지면 H 전체가 H∩B 가 되어 새 파일 검사가 통째로 빈다
[ -n "$($GIT for-each-ref --contains "$B" --format='%(refname)' refs/remotes/origin/)" ] \
  || die "B(${B:0:12})가 refs/remotes/origin/* 어디에서도 닿지 않는다 — 공개된 판이 아니다(PUB_BASE 확인 · fetch 했는가)"
OLD=$($GIT rev-parse --verify -q "$REF" || true)
[ -z "$OLD" ] || [ "${PUB_FORCE:-0}" = 1 ] || die "$REF 이미 있음(${OLD:0:12}) — 덮어쓰려면 PUB_FORCE=1"

W=$(mktemp -d "${TMPDIR:-/tmp}/pubcXXXX") || die "임시 폴더"
trap 'rm -rf "$W"' EXIT
listfile "$A" "$W/allow" || die "허용 목록 읽기 실패: $A"
lstree "$H" "$W/htree" || die "H 트리 읽기 실패(rc $? · 3 = \\001 이 든 이름)"
lstree "$B" "$W/btree" || die "B 트리 읽기 실패(rc $? · 3 = \\001 이 든 이름)"
# 허용 줄이 H 에 실재하는가(없는 줄 = 낡은 목록 — 조용히 무시하면 「냈다고 믿은 파일」 이 빠진다)
LC_ALL=C comm -23 "$W/allow" "$W/htree" > "$W/absent"
[ -s "$W/absent" ] && { echo "✗ 허용 목록 줄이 H 트리에 없음 $(wc -l < "$W/absent" | tr -d ' ')건:" >&2; sed 's/^/    /' "$W/absent" >&2; die "목록 갱신 필요"; }
# 지킴 폴더(내부 게이트 도구 폴더)의 경로는 허용 목록에 올 수 없다
guardhits "$W/allow" "$W/guard"
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
if [ -s "$W/withheld" ]; then LC_ALL=C tr '\n\001' '\0\n' < "$W/withheld" | xargs -0 $GIT update-index --force-remove -- || die "update-index"; fi
T=$($GIT write-tree) || die "write-tree"
C=$($GIT commit-tree "$T" -p "$B" -F "$M") || die "commit-tree"
unset GIT_INDEX_FILE
echo "C=$C · 작성자 = $($GIT log -1 --format='%an' "$C")"
echo "공개 안 된 새 파일(withheld) ${NWH}건 — 공개하려면 PUB_ALLOW 에 더한다:"
sed 's/^/    /' "$W/withheld"
[ -n "${PUB_WITHHELD_OUT:-}" ] && cp "$W/withheld" "$PUB_WITHHELD_OUT"

# 관문 1 — C 의 실제 트리로 다시 잰다(위 계산과 독립) · 실패 = C 를 <PUB_REF>-rejected 에 두고 rc 2(정상 후보 ref 는 손대지 않음)
gate1_fail() {
  G1=1; REF_OUT=$REJ
  $GIT update-ref -m "pubcand.sh 관문 1 실패 H=${H:0:12}" "$REJ" "$C" || echo "✗ update-ref $REJ 실패"
  echo "✗ 관문 1 실패 — C 는 $REJ 에 둔다(판정 근거 · $REF 는 그대로)"; fin 2
}
lstree "$C" "$W/ctree" || die "C 트리 읽기 실패(rc $?)"
LC_ALL=C sort -u "$W/btree" "$W/allow" > "$W/ok"
LC_ALL=C comm -23 "$W/ctree" "$W/ok" > "$W/leak"
if [ -s "$W/leak" ]; then echo "✗ 관문 1 ⑴: C 에 B·허용 목록 밖 경로 $(wc -l < "$W/leak" | tr -d ' ')건:"; sed 's/^/    /' "$W/leak"; gate1_fail; fi
cmp -s "$W/ctree" "$W/public" || { echo "✗ 관문 1 ⑵: C 트리 ≠ 계산한 공개 집합"; diff "$W/ctree" "$W/public" | sed 's/^/    /'; gate1_fail; }
$GIT diff -z --no-renames --name-only "$C" "$H" > "$W/diff.z" || die "diff"
LC_ALL=C tr '\n\0' '\001\n' < "$W/diff.z" | LC_ALL=C sort > "$W/diff"
cmp -s "$W/diff" "$W/withheld" || { echo "✗ 관문 1 ⑶: C↔H 차 ≠ withheld"; diff "$W/diff" "$W/withheld" | sed 's/^/    /'; gate1_fail; }
[ "$($GIT rev-parse "$C^@")" = "$B" ] || { echo "✗ 관문 1 ⑷: C 의 부모가 B 하나가 아님"; gate1_fail; }
G1=0; echo "✓ 관문 1: C ⊆ B ∪ 허용($NNEW 새 경로) · C = 공개 집합 $NPUB · C↔H 차 = withheld $NWH · 부모 = B"
$GIT update-ref -m "pubcand.sh H=${H:0:12}" "$REF" "$C" ${OLD:+"$OLD"} || die "update-ref"
echo "ref $REF ← ${C:0:12}${OLD:+ (이전 ${OLD:0:12})}"

[ "${PUB_NO_RECHECK:-0}" = 1 ] && { echo "⚠ recheck 생략(PUB_NO_RECHECK=1) — 공개 판정 미완"; fin 4; }
[ -f "$RK" ] || die "recheck 스크립트 없음: $RK"
mkdir -p "$W/nogh" && printf '#!/bin/sh\necho "pubcand: github CLI 차단(recheck 안)" >&2\nexit 97\n' > "$W/nogh/gh" && chmod +x "$W/nogh/gh"
# push 차단 env(머리말 ①②③) — pushurl 덧씌움은 「값 추가」라 이미 적힌 pushurl 은 insteadOf 로 따로 바꿔 쓴다
NP=pubcand-no-push://; CFG=(); NC=0
addcfg() { CFG+=("GIT_CONFIG_KEY_$NC=$1" "GIT_CONFIG_VALUE_$NC=$2"); NC=$((NC+1)); }
addcfg "url.$NP.pushInsteadOf" ""
while IFS= read -r rn; do [ -n "$rn" ] && addcfg "remote.$rn.pushurl" "$NP"; done < <($GIT remote)
while IFS= read -r -d '' rec; do case $rec in *$'\n'*) addcfg "url.$NP.insteadOf" "${rec#*$'\n'}" ;; esac; done < <($GIT config -z --get-regexp '^remote\..*\.pushurl$')
env GIT_CONFIG_COUNT=$NC "${CFG[@]}" PATH="$W/nogh:$PATH" SRC="$($GIT rev-parse --show-toplevel)" VERDICT="$B" bash "$RK" "$C"; RRC=$?
case $RRC in 0) fin 0 ;; 1) fin 1 ;; 3) fin 3 ;; *) fin 2 ;; esac
