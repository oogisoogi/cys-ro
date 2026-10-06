# shellcheck shell=bash
# ★시험 전용 대역(1.1.8 U3 3판 · codex 2R #3) — 실 의식 스크립트는 이 파일을 읽지 않는다.
#
# 시험(scripts/tests/test_update_publish.py)이 시험용 사본 트리를 만들고 그 `lib/offline-sign.sh` 를
# 「실 lib 을 읽은 뒤 이 파일을 읽는」 두 줄로 바꿔 끼운다 — 그래서 실 lib 의 고정값 세 함수만 이 파일이 덮어쓴다:
#   · minisign  = env `MINISIGN`(시험 대역 fake_minisign)          · 매체 부모 = env `CYS_SIGN_MEDIA_PREFIX`(가짜 매체의 부모)
#   · 대기 0 허용(매체 빼기 생략)
# 이 대역이 스스로 거는 제한(사고로 실 키를 쓰는 길 봉쇄):
#   · 매체 부모는 **시험 임시 폴더 아래**(`$TMPDIR`·/tmp·/private/var/folders)여야 한다 — /Volumes(실 매체) = 거부.
#   · 기대 key id 가 저장소 실 키링(`cysjavis-pack/trusted-keys.json`)에 있으면 거부.
_offline_minisign() { echo "${MINISIGN:?시험 대역: MINISIGN 필요}"; }
_offline_prefix() {
  local p r
  p="${CYS_SIGN_MEDIA_PREFIX:?시험 대역: CYS_SIGN_MEDIA_PREFIX 필요}"
  r="$(_realpath "$p")"
  case "$r/" in
    "$(_realpath "${TMPDIR:-/tmp}")"/*|/private/tmp/*|/tmp/*|/private/var/folders/*) echo "$p" ;;
    *) echo "거부: 시험 대역의 매체 부모가 임시 폴더 밖이다: $r" >&2; echo /nonexistent-test-prefix ;;
  esac
}
offline_dev_policy() {
  local kid="$1" real
  real="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/cysjavis-pack/trusted-keys.json"
  [ "$kid" = "-" ] && return 0
  python3 - "$real" "$kid" <<'PY' || return 2
import json, sys
try:
    ids = {k.get("key_id") for k in json.load(open(sys.argv[1], encoding="utf-8")).get("keys", [])}
except (OSError, ValueError) as e:
    print("거부: 시험 대역인데 저장소 실 키링을 못 읽는다(%s) — 실 키 대조 불가" % e, file=sys.stderr); sys.exit(2)
if sys.argv[2] in ids:
    print("거부: 시험 대역으로 저장소 실 키링의 key id %s 를 쓰려 한다" % sys.argv[2], file=sys.stderr); sys.exit(2)
PY
}
