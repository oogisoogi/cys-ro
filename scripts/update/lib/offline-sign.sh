# shellcheck shell=bash
# 오프라인 매체 서명 의식 공용 함수(1.1.8 U3 · 설계 AUTO-UPDATE-118 §8 「U 의식 절차(📌11)」 ①~⑥ · R 의식 같은 틀).
#
# 불변식(이 함수가 기계로 강제한다 — 사람의 조심에 맡기지 않는다):
#   · 개인키는 **매체 안에서만** 열린다: `-s` 경로(실경로)가 매체 마운트 아래가 아니면 거부. 매체 = 마운트 지점이고
#     빌드 기기 디스크(/ · $HOME · 이 저장소)와 **다른 장치**여야 한다. 키 경로가 심링크여도 거부.
#   · 이 함수는 개인키 파일을 **읽지도 복사하지도 않는다** — 경로만 minisign 에 넘긴다(클립보드·셸 기록·임시 파일 0).
#   · 서명 대상(공개 정보)만 매체 쪽 임시 폴더로 옮겨 그 자리에서 서명하고, 서명(.minisig)만 꺼낸다(④).
#   · 매체를 뺀 뒤(⑤ · 기본 = 빠질 때까지 기다림) 내장 키링의 같은 용도 공개키로 검증해야(⑥) 산출물이 생긴다.
#   · ★3판(codex 2R #3): 이 파일(실 의식)에는 **환경 변수 손잡이가 하나도 없다** — minisign = PATH 의 `minisign` · 매체 부모 =
#     `/Volumes` · 매체 빼기 대기 ≥ 1초가 고정값이다. 시험 대역(가짜 minisign·가짜 매체·대기 0)은 시험 전용 파일
#     `lib/offline-sign-dev.sh` 가 아래 세 함수를 덮어써서만 생긴다 — 실 스크립트(sign-release.sh · sign-revocations.sh ·
#     gen-offline-key.sh)는 그 파일을 읽지 않는다(시험은 시험용 사본 트리에서 두 파일을 함께 읽는다).
# 시험 = 가짜 키(scripts/tests/fixtures/fake_minisign.py) + 가짜 매체(hdiutil 로 만든 진짜 마운트) — 실키 0.

# 실 의식의 고정값(시험 대역이 덮어쓰는 자리는 이 세 함수뿐).
_offline_minisign() { echo minisign; }
_offline_prefix() { echo /Volumes; }
# offline_dev_policy <expect_key_id|-> <wait_eject_secs> — 실 의식: 대기는 정수 ≥ 1(매체 빼기 생략 불가). 0 | 2.
offline_dev_policy() {
  local wait="$2"
  # 4판(Fable 3R MINOR-2): 파이썬 도구의 시험 시각 손잡이가 보이면 실 의식을 시작하지 않는다(무시가 아니라 거부 · rc 2).
  if [ -n "${CYS_SIGN_DEV+x}" ] || [ -n "${CYS_TEST_NOW+x}" ]; then
    echo "거부: 실 의식인데 시험 시각 손잡이(CYS_SIGN_DEV/CYS_TEST_NOW)가 환경에 있다 — 새 셸에서 다시" >&2; return 2
  fi
  case "$wait" in ''|*[!0-9]*) echo "거부: --wait-eject 정수 아님: $wait" >&2; return 2 ;; esac
  [ "$wait" -ge 1 ] || { echo "거부: --wait-eject 0(매체 빼기 생략)은 실 의식에서 쓸 수 없다" >&2; return 2; }
  return 0
}

_os_dev() {  # 경로의 장치 번호(BSD·GNU stat 둘 다 — GNU 의 `stat -f` 는 파일 시스템 정보라 먼저 갈라야 한다)
  if stat --version >/dev/null 2>&1; then stat -c %d "$1"; else stat -f %d "$1"; fi
}

# ★1.1.20 #39(TICKET=cysr-1120-integ2 · 536 F5 = codex 1R 2번): 이 파일·의식 스크립트의 python3 는 전부 `-I`(격리) — `-c`·`-`(stdin)
#   실행은 sys.path[0] = 지금 폴더라 그 자리의 json.py·hashlib.py 류가 표준 모듈보다 먼저 읽힐 길이 있었다. update_common 은
#   스크립트가 sys.path 에 직접 넣는 $here 에서만 읽는다(-I 는 그 삽입을 막지 않음 · PYTHON* 환경·사용자 site 도 무시).
#   ⚠-I 는 PYTHON* 환경도 무시한다 — sign-release.sh --expect-head 가 세우는 pyc 차단(pyc 쓰기 끔 환경변수·PYTHONPYCACHEPREFIX =
#   scripts/update/__pycache__ 를 읽지 않음 · 1.1.19 codex 1R B2)이 꺼지므로, update_common 을 읽는 호출은 _offline_py 로 같은 뜻을
#   옵션(-B · -X pycache_prefix)으로 다시 준다(시험 = test_co_l3_b2_ignored_outside_and_pycache_allowed_but_not_read · -I 만 붙이면 PYC-HIJACK).
_offline_py() {
  if [ -n "${PYTHONPYCACHEPREFIX:-}" ]; then python3 -I -B -X "pycache_prefix=$PYTHONPYCACHEPREFIX" "$@"; else python3 -I "$@"; fi
}

_realpath() {
  python3 -I -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

# offline_sha256 <file> — 64자 소문자 hex 한 줄 · 계산 실패·형식 밖 = rc 2(★1.1.20 F8: 해시 실패를 검사하지 않으면
#   두 쪽이 모두 빈 값일 때 「같다」 가 됐다 — 빈 값 비교로 대조를 지나지 않게 한다).
offline_sha256() {
  local h
  h="$(python3 -I -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1")" \
    || { echo "거부: sha256 을 계산하지 못했다: $1" >&2; return 2; }
  [[ "$h" =~ ^[0-9a-f]{64}$ ]] || { echo "거부: sha256 형식이 아니다: $1" >&2; return 2; }
  printf '%s\n' "$h"
}

# offline_place_pair <tmp_doc> <tmp_sig> <out_doc> — ★1.1.20 F9: 산출 자리에 **본문 먼저 · 서명 나중**(서명만 있고 본문이 없는
#   반쪽 상태 0). 둘 다 덮어쓰기 0(ln = 이미 있으면 실패 · mv -n 은 거절해도 rc 0 이라 쓰지 않음) · 서명을 못 놓으면 놓은 본문을
#   거둔다(산출 0 · 다시 돌릴 때 「이미 있다」 로 막히지 않음) · 임시 파일 정리 실패 = 거부(산출도 거둠). 0 | 2.
#   ★검증 R2: 두 ln 사이에 INT·TERM·HUP 이 오면 서명 없는 본문이 최종 이름으로 남았다 → 이 함수가 도는 동안 신호를 미뤘다가
#     (자식 ln 이 끝난 뒤 표시만) 끝에서 처리한다: 쌍을 다 놓았어도 신호가 왔으면 둘 다 거두고 rc 2 로 끝낸다(산출 0 · 다시 돌릴 수 있음).
#   ★검증 R3: 거두는 rm 의 결과를 보고 말한다 — 못 지웠으면 「남았다: <경로>」.
offline_place_pair() {
  local td="$1" ts="$2" od="$3" _pp_sig=0 _pp_rc=0 _pp_saved
  _pp_saved="$(trap -p INT TERM HUP)"
  trap '_pp_sig=1' INT TERM HUP
  if ! ln "$td" "$od"; then
    echo "거부: 본문을 산출 자리에 놓지 못했다(이미 있음 또는 ln 실패): $od" >&2; _pp_rc=2
  elif ! ln "$ts" "$od.minisig"; then
    if rm -f "$od"; then
      echo "거부: 서명을 산출 자리에 놓지 못했다 — 먼저 놓은 본문을 거뒀다(산출 0): $od.minisig" >&2
    else
      echo "거부: 서명을 산출 자리에 놓지 못했다 — 먼저 놓은 본문을 지우지 못해 남았다(서명 없음 · 손으로 지울 것): $od" >&2
    fi
    _pp_rc=2
  elif ! rm -f "$td" "$ts"; then
    if rm -f "$od" "$od.minisig"; then
      echo "거부: 임시 파일을 지우지 못했다 — 산출을 거뒀다(산출 0): $td $ts" >&2
    else
      echo "거부: 임시 파일을 지우지 못했고 산출도 지우지 못해 남았다(손으로 지울 것): $od $od.minisig" >&2
    fi
    _pp_rc=2
  fi
  if [ "$_pp_sig" = 1 ] && [ "$_pp_rc" = 0 ]; then
    if rm -f "$od" "$od.minisig"; then
      echo "거부: 산출을 놓는 중에 신호를 받았다 — 놓은 본문·서명을 거뒀다(산출 0)" >&2
    else
      echo "거부: 산출을 놓는 중에 신호를 받았고 놓은 것을 지우지 못해 남았다(손으로 지울 것): $od $od.minisig" >&2
    fi
    _pp_rc=2
  fi
  trap - INT TERM HUP
  eval "$_pp_saved"
  [ "$_pp_sig" = 0 ] || exit 2
  return "$_pp_rc"
}

# offline_media_check <media> — 매체가 /Volumes 아래 마운트 지점이고 빌드 기기 디스크와 다른 장치인가. 0 | 2.
offline_media_check() {
  local media="$1" prefix rm dm dp p
  prefix="$(_realpath "$(_offline_prefix)")/"  # 실경로로 맞춘다(/var → /private/var)
  [ -n "$media" ] && [ -d "$media" ] || { echo "거부: 매체 폴더 없음: $media" >&2; return 2; }
  rm="$(_realpath "$media")"
  case "$rm/" in "$prefix"*) ;; *) echo "거부: 매체가 $prefix 아래 마운트가 아니다: $rm" >&2; return 2 ;; esac
  dm="$(_os_dev "$rm")"; dp="$(_os_dev "$(dirname "$rm")")"
  [ "$dm" != "$dp" ] || { echo "거부: 매체 경로가 마운트 지점이 아니다(부모와 같은 장치 $dm): $rm" >&2; return 2; }
  for p in / "$HOME" "$(pwd)" "${TMPDIR:-/tmp}"; do
    [ -e "$p" ] || continue
    [ "$(_os_dev "$p")" != "$dm" ] || { echo "거부: 매체가 빌드 기기 디스크와 같은 장치다($p): $rm" >&2; return 2; }
  done
  return 0
}

# offline_media_guard <media> <key> — 매체 검사 + 키가 그 매체 안의 실파일인가. 통과하면 0, 아니면 이유를 stderr 에 쓰고 2.
offline_media_guard() {
  local media="$1" key="$2" rm rk
  [ -n "$key" ] || { echo "거부: 키 경로 없음" >&2; return 2; }
  [ -L "$key" ] && { echo "거부: 키 경로가 심링크다: $key" >&2; return 2; }
  [ -f "$key" ] || { echo "거부: 키 파일 없음: $key" >&2; return 2; }
  offline_media_check "$media" || return 2
  rm="$(_realpath "$media")"; rk="$(_realpath "$key")"
  case "$rk" in "$rm"/*) ;; *) echo "거부: 키(-s)가 매체 아래가 아니다: $rk (매체 $rm)" >&2; return 2 ;; esac
  [ "$(_os_dev "$rk")" = "$(_os_dev "$rm")" ] || { echo "거부: 키 파일 장치 ≠ 매체 장치" >&2; return 2; }
  return 0
}

_mounted() {  # 매체가 아직 마운트돼 있는가(장치가 부모와 다르면 마운트)
  [ -d "$1" ] && [ "$(_os_dev "$1")" != "$(_os_dev "$(dirname "$1")")" ]
}

# offline_sign <purpose> <doc> <key> <media> <keyring> <expect_key_id> <out_sig> <trusted_comment> <wait_eject_secs>
#   purpose = release(U) | root(R). wait_eject_secs ≥ 1(실 의식 · 0 은 시험 대역 lib/offline-sign-dev.sh 에서만).
#   ★1.1.19 CO-L3: 호출부가 `if ! offline_sign …`·`offline_sign … || exit` 꼴이라 이 함수 안에서는 set -e 가 꺼진다 —
#     실패할 수 있는 명령(mktemp·cp·mv)마다 명시 검사로 치우고 2 를 돌려준다(set -e 의존 0) · 거부 갈래는 매체 작업 폴더를 남기지 않는다.
#   ★1.1.20 B4: 매체 작업 중 INT·TERM·HUP(비밀번호 대기 중 Ctrl-C·종료 신호)이면 매체 작업 폴더·공개키 임시 파일·꺼낸 서명 임시
#     파일을 지우고 rc 2 로 끝낸다(종전 trap 0 = 남았다) · 함수가 끝나면 부른 쪽의 원래 신호 처리로 되돌린다.
#     bash 는 앞에서 도는 자식(minisign)이 끝난 뒤에 trap 을 돈다 — 자식이 비밀번호를 기다리는 동안 받은 TERM 은 자식이 끝날 때 정리된다.
offline_sign() {
  local _os_saved_traps _os_rc
  _os_saved_traps="$(trap -p INT TERM HUP)"
  trap '_offline_sign_abort' INT TERM HUP
  _offline_sign_body "$@"; _os_rc=$?
  trap - INT TERM HUP
  eval "$_os_saved_traps"
  return "$_os_rc"
}

# 신호 정리 — 본문 함수가 도는 중에만 불린다(그 함수의 지역 변수가 보인다 · 아직 안 만든 것은 빈 값).
_offline_sign_abort() {
  if [ -n "${mw:-}" ] && [ -d "${mw:-}" ]; then rm -f "$mw/doc" "$mw/doc.minisig"; rmdir "$mw" 2>/dev/null; fi
  [ -z "${pub:-}" ] || rm -f "$pub"
  [ -z "${tmp_sig:-}" ] || rm -f "$tmp_sig"
  echo "거부: 서명 의식이 신호로 멈췄다 — 매체 작업 폴더·임시 파일을 지웠다(산출 0)" >&2
  exit 2
}

_offline_sign_body() {
  local purpose="$1" doc="$2" key="$3" media="$4" keyring="$5" kid="$6" out_sig="$7" tc="$8" wait="$9"
  local here mini pub="" mw="" tmp_sig=""
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  umask 077
  offline_dev_policy "$kid" "$wait" || return 2
  mini="$(_offline_minisign)"
  [ -f "$doc" ] && [ ! -L "$doc" ] || { echo "거부: 서명 대상 없음(또는 심링크): $doc" >&2; return 2; }
  [ -e "$out_sig" ] && { echo "거부: 산출 서명이 이미 있다(덮어쓰기 0): $out_sig" >&2; return 2; }
  offline_media_guard "$media" "$key" || return 2
  # 내장 키링에서 같은 용도·같은 key_id 공개키를 먼저 꺼낸다(⑥ 준비 — 매체를 꽂기 전에 실패할 것은 먼저 실패).
  # (B4) 임시 파일 자리 = TMPDIR 틀(macOS `mktemp` 는 틀이 없으면 TMPDIR 를 무시하고 사용자 임시 폴더에 tmp.* 를 만든다) · 이름표 cys-sign-*
  pub="$(mktemp "${TMPDIR:-/tmp}/cys-sign-pub.XXXXXX")" || { echo "거부: 임시 파일을 못 만든다" >&2; return 2; }
  _offline_py - "$here" "$keyring" "$purpose" "$kid" "$pub" <<'PY' || { rm -f "$pub"; return 2; }
import sys
sys.path.insert(0, sys.argv[1])
import update_common as uc
try:
    k = uc.find_key(uc.load_keyring(sys.argv[2]), sys.argv[3], sys.argv[4])
except uc.PublishError as e:
    print("거부: %s" % e, file=sys.stderr); sys.exit(2)
open(sys.argv[5], "w", encoding="utf-8").write(uc.pub_file_text(k["pubkey"]))
PY
  # ② 서명 대상만 매체 쪽으로 · ③ 매체 경로의 키로 그 자리에서 서명 · ④ 서명만 꺼낸다.
  local doc_sha
  mw="$(_realpath "$media")/.cys-sign-$$"
  mkdir "$mw" || { rm -f "$pub"; echo "거부: 매체에 작업 폴더를 못 만든다(읽기 전용?)" >&2; return 2; }
  cp "$doc" "$mw/doc" || { rm -f "$mw/doc"; rmdir "$mw" 2>/dev/null; rm -f "$pub"; echo "거부: 서명 대상을 매체로 옮기지 못했다(cp 실패)" >&2; return 2; }
  doc_sha="$(offline_sha256 "$doc")" || { rm -f "$mw/doc"; rmdir "$mw" 2>/dev/null; rm -f "$pub"; return 2; }  # (F8)
  # 비밀번호는 minisign 이 터미널에서 직접 묻는다(이 스크립트는 비밀번호도 만지지 않는다 · 재시도 0).
  if ! "$mini" -S -s "$key" -m "$mw/doc" -x "$mw/doc.minisig" -t "$tc"; then
    rm -f "$mw/doc" "$mw/doc.minisig"; rmdir "$mw" 2>/dev/null; rm -f "$pub"
    echo "거부: minisign 서명 실패" >&2; return 2
  fi
  tmp_sig="$(mktemp "${TMPDIR:-/tmp}/cys-sign-sig.XXXXXX")" || { rm -f "$mw/doc" "$mw/doc.minisig"; rmdir "$mw" 2>/dev/null; rm -f "$pub"; echo "거부: 임시 파일을 못 만든다" >&2; return 2; }
  cp "$mw/doc.minisig" "$tmp_sig" \
    || { rm -f "$mw/doc" "$mw/doc.minisig"; rmdir "$mw" 2>/dev/null; rm -f "$tmp_sig" "$pub"; echo "거부: 매체에서 서명을 꺼내지 못했다(cp 실패)" >&2; return 2; }
  local media_sha  # (F8) 계산 실패 = 거부(빈 값끼리 「같다」 0)
  media_sha="$(offline_sha256 "$mw/doc")" && [ "$media_sha" = "$doc_sha" ] \
    || { echo "거부: 매체 쪽 서명 대상이 바뀌었다(또는 해시 실패)" >&2; rm -f "$mw/doc" "$mw/doc.minisig"; rmdir "$mw" 2>/dev/null; rm -f "$tmp_sig" "$pub"; return 2; }
  # (★1.1.20 B3) 성공 갈래의 매체 정리 실패 = 거부(종전 = 무시하고 rc 0 · 매체에 사본이 남았다)
  if ! { rm -f "$mw/doc" "$mw/doc.minisig" && rmdir "$mw"; }; then
    rm -f "$tmp_sig" "$pub"
    echo "거부: 매체 작업 폴더를 지우지 못했다 — 산출 0(남은 것 = 공개 본문·서명뿐): $mw" >&2; return 2
  fi
  mw=""
  # ⑤ 매체를 뺀다(사람 손 1단계) — 기다린다.
  if [ "$wait" -gt 0 ]; then
    echo "⑤ 서명을 꺼냈습니다. 이제 매체를 빼 주세요(최대 ${wait}초 기다림): $media" >&2
    local t=0
    while _mounted "$media"; do
      sleep 2; t=$((t + 2))
      [ "$t" -lt "$wait" ] || { echo "거부: 매체가 ${wait}초 안에 빠지지 않았다 — 산출물 0" >&2; rm -f "$tmp_sig" "$pub"; return 2; }
    done
  fi
  # ⑥ 내장(같은 용도) 공개키로 검증 + 서명 key id = 기대 key id.
  local sk
  sk="$(_offline_py -c 'import sys; sys.path.insert(0, sys.argv[1]); import update_common as uc; print(uc.sig_key_id(open(sys.argv[2],encoding="utf-8").read()))' "$here" "$tmp_sig")" \
    || { rm -f "$tmp_sig" "$pub"; return 2; }
  [ "$sk" = "$kid" ] || { echo "거부: 서명 key id $sk ≠ 기대 $kid(다른 키로 서명)" >&2; rm -f "$tmp_sig" "$pub"; return 2; }
  if ! "$mini" -V -p "$pub" -m "$doc" -x "$tmp_sig" >/dev/null; then
    echo "거부: 내장 $purpose 공개키 검증 실패" >&2; rm -f "$tmp_sig" "$pub"; return 2
  fi
  # (★1.1.20 B3) 공개키 임시 파일 정리 실패 = 거부(종전 = 산출 뒤 rm 실패 무시)
  rm -f "$pub" || { rm -f "$tmp_sig"; echo "거부: 공개키 임시 파일을 지우지 못했다 — 산출 0: $pub" >&2; return 2; }
  pub=""
  mv "$tmp_sig" "$out_sig" || { rm -f "$tmp_sig"; echo "거부: 서명을 산출 자리로 옮기지 못했다(mv 실패) — 산출물 0" >&2; return 2; }
  tmp_sig=""
  return 0
}
