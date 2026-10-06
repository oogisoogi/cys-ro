# shellcheck shell=bash
# 오프라인 매체 서명 의식 공용 함수(1.1.8 U3 · 설계 AUTO-UPDATE-118 §8 「U 의식 절차(📌11)」 ①~⑥ · R 의식 같은 틀).
#
# 불변식(이 함수가 기계로 강제한다 — 사람의 조심에 맡기지 않는다):
#   · 개인키는 **매체 안에서만** 열린다: `-s` 경로(실경로)가 매체 마운트 아래가 아니면 거부. 매체 = 마운트 지점이고
#     빌드 기기 디스크(/ · $HOME · 이 저장소)와 **다른 장치**여야 한다. 키 경로가 심링크여도 거부.
#   · 이 함수는 개인키 파일을 **읽지도 복사하지도 않는다** — 경로만 minisign 에 넘긴다(클립보드·셸 기록·임시 파일 0).
#   · 서명 대상(공개 정보)만 매체 쪽 임시 폴더로 옮겨 그 자리에서 서명하고, 서명(.minisig)만 꺼낸다(④).
#   · 매체를 뺀 뒤(⑤ · 기본 = 빠질 때까지 기다림) 내장 키링의 같은 용도 공개키로 검증해야(⑥) 산출물이 생긴다.
# 시험 = 가짜 키(scripts/tests/fixtures/fake_minisign.py) + 가짜 매체(hdiutil 로 만든 진짜 마운트) — 실키 0.

_os_dev() {  # 경로의 장치 번호(BSD·GNU stat 둘 다 — GNU 의 `stat -f` 는 파일 시스템 정보라 먼저 갈라야 한다)
  if stat --version >/dev/null 2>&1; then stat -c %d "$1"; else stat -f %d "$1"; fi
}

_realpath() {
  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

# offline_media_guard <media> <key> — 통과하면 0, 아니면 이유를 stderr 에 쓰고 2.
offline_media_guard() {
  local media="$1" key="$2" prefix
  prefix="$(_realpath "${CYS_SIGN_MEDIA_PREFIX:-/Volumes}")/"  # 실경로로 맞춘다(/var → /private/var)
  [ -n "$media" ] && [ -d "$media" ] || { echo "거부: 매체 폴더 없음: $media" >&2; return 2; }
  [ -n "$key" ] || { echo "거부: 키 경로 없음" >&2; return 2; }
  [ -L "$key" ] && { echo "거부: 키 경로가 심링크다: $key" >&2; return 2; }
  [ -f "$key" ] || { echo "거부: 키 파일 없음: $key" >&2; return 2; }
  local rm rk
  rm="$(_realpath "$media")"; rk="$(_realpath "$key")"
  case "$rm/" in "$prefix"*) ;; *) echo "거부: 매체가 $prefix 아래 마운트가 아니다: $rm" >&2; return 2 ;; esac
  case "$rk" in "$rm"/*) ;; *) echo "거부: 키(-s)가 매체 아래가 아니다: $rk (매체 $rm)" >&2; return 2 ;; esac
  local dm dp
  dm="$(_os_dev "$rm")"; dp="$(_os_dev "$(dirname "$rm")")"
  [ "$dm" != "$dp" ] || { echo "거부: 매체 경로가 마운트 지점이 아니다(부모와 같은 장치 $dm): $rm" >&2; return 2; }
  local p
  for p in / "$HOME" "$(pwd)" "${TMPDIR:-/tmp}"; do
    [ -e "$p" ] || continue
    [ "$(_os_dev "$p")" != "$dm" ] || { echo "거부: 매체가 빌드 기기 디스크와 같은 장치다($p): $rm" >&2; return 2; }
  done
  [ "$(_os_dev "$rk")" = "$dm" ] || { echo "거부: 키 파일 장치 ≠ 매체 장치" >&2; return 2; }
  return 0
}

_mounted() {  # 매체가 아직 마운트돼 있는가(장치가 부모와 다르면 마운트)
  [ -d "$1" ] && [ "$(_os_dev "$1")" != "$(_os_dev "$(dirname "$1")")" ]
}

# offline_sign <purpose> <doc> <key> <media> <keyring> <expect_key_id> <out_sig> <trusted_comment> <wait_eject_secs>
#   purpose = release(U) | root(R). wait_eject_secs = 0 이면 기다리지 않는다(시험).
offline_sign() {
  local purpose="$1" doc="$2" key="$3" media="$4" keyring="$5" kid="$6" out_sig="$7" tc="$8" wait="$9"
  local here mini
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  mini="${MINISIGN:-minisign}"
  umask 077
  [ -f "$doc" ] && [ ! -L "$doc" ] || { echo "거부: 서명 대상 없음(또는 심링크): $doc" >&2; return 2; }
  [ -e "$out_sig" ] && { echo "거부: 산출 서명이 이미 있다(덮어쓰기 0): $out_sig" >&2; return 2; }
  offline_media_guard "$media" "$key" || return 2
  # 내장 키링에서 같은 용도·같은 key_id 공개키를 먼저 꺼낸다(⑥ 준비 — 매체를 꽂기 전에 실패할 것은 먼저 실패).
  local pub
  pub="$(mktemp)"
  python3 - "$here" "$keyring" "$purpose" "$kid" "$pub" <<'PY' || { rm -f "$pub"; return 2; }
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
  local mw doc_sha
  mw="$(_realpath "$media")/.cys-sign-$$"
  mkdir "$mw" || { rm -f "$pub"; echo "거부: 매체에 작업 폴더를 못 만든다(읽기 전용?)" >&2; return 2; }
  cp "$doc" "$mw/doc"
  doc_sha="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$doc")"
  # 비밀번호는 minisign 이 터미널에서 직접 묻는다(이 스크립트는 비밀번호도 만지지 않는다 · 재시도 0).
  if ! "$mini" -S -s "$key" -m "$mw/doc" -x "$mw/doc.minisig" -t "$tc"; then
    rm -f "$mw/doc" "$mw/doc.minisig"; rmdir "$mw" 2>/dev/null; rm -f "$pub"
    echo "거부: minisign 서명 실패" >&2; return 2
  fi
  local tmp_sig
  tmp_sig="$(mktemp)"
  cp "$mw/doc.minisig" "$tmp_sig"
  [ "$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$mw/doc")" = "$doc_sha" ] \
    || { echo "거부: 매체 쪽 서명 대상이 바뀌었다" >&2; rm -f "$tmp_sig" "$pub"; return 2; }
  rm -f "$mw/doc" "$mw/doc.minisig"; rmdir "$mw" 2>/dev/null
  # ⑤ 매체를 뺀다(사람 손 1단계) — 기다린다.
  if [ "${wait:-0}" -gt 0 ]; then
    echo "⑤ 서명을 꺼냈습니다. 이제 매체를 빼 주세요(최대 ${wait}초 기다림): $media" >&2
    local t=0
    while _mounted "$media"; do
      sleep 2; t=$((t + 2))
      [ "$t" -lt "$wait" ] || { echo "거부: 매체가 ${wait}초 안에 빠지지 않았다 — 산출물 0" >&2; rm -f "$tmp_sig" "$pub"; return 2; }
    done
  fi
  # ⑥ 내장(같은 용도) 공개키로 검증 + 서명 key id = 기대 key id.
  local sk
  sk="$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import update_common as uc; print(uc.sig_key_id(open(sys.argv[2],encoding="utf-8").read()))' "$here" "$tmp_sig")" \
    || { rm -f "$tmp_sig" "$pub"; return 2; }
  [ "$sk" = "$kid" ] || { echo "거부: 서명 key id $sk ≠ 기대 $kid(다른 키로 서명)" >&2; rm -f "$tmp_sig" "$pub"; return 2; }
  if ! "$mini" -V -p "$pub" -m "$doc" -x "$tmp_sig" >/dev/null; then
    echo "거부: 내장 $purpose 공개키 검증 실패" >&2; rm -f "$tmp_sig" "$pub"; return 2
  fi
  mv "$tmp_sig" "$out_sig"
  rm -f "$pub"
  return 0
}
