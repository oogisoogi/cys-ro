#!/usr/bin/env bash
# U·R 오프라인 키 생성 — 개인키는 **매체 안에서만** 생긴다(1.1.8 U3 · codex 1R #3 · 설계 §4-1 · 📌11).
#
# 서명 의식(lib/offline-sign.sh)과 같은 가드: 매체 = /Volumes 아래 마운트 지점 · 빌드 기기 디스크와 다른 장치.
#   · `minisign -G` 의 `-s` 를 매체 경로로 준다 — 빌드 기기 디스크에 개인키 파일이 한 번도 생기지 않는다.
#   · `--copy-to` = R 둘째 벌(서로 다른 장소 보관): 매체 → 매체 복사만(둘째 매체도 같은 가드 · 둘이 같은 장치면 거부)
#     → 바이트 대조(cmp) 뒤 끝. 빌드 디스크 경유 0.
#   · 공개키(.pub · 공개 정보)만 `--pub-out` 으로 꺼낸다 → HANDOFF-U3 §1 ② 키링 기입.
# ⚠정직: minisign 은 이 기기의 프로세스다 — 생성 순간 개인키 바이트는 이 기기 메모리를 지난다(파일·클립보드는 0).
#   네트워크와 분리된 서명 기기/HSM 은 이 스크립트 범위 밖(codex 1R #3 처방 ① · HANDOFF-U3 §8 잔여).
#
# 사용:
#   scripts/update/gen-offline-key.sh --media /Volumes/CYS-R1 --name r --copy-to /Volumes/CYS-R2 [--pub-out r.pub]
#   scripts/update/gen-offline-key.sh --media /Volumes/CYS-U --name u [--pub-out u.pub]
# 종료: 0 = 생성(+복제) 통과 · 2 = 거부(이미 있는 키는 덮지 않는다)
# 시험: 이 스크립트는 손잡이 env 가 없다 — 시험은 사본 트리에서 lib/offline-sign-dev.sh(대역)를 함께 읽는다(3판 · 실키 0).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/offline-sign.sh
. "$HERE/lib/offline-sign.sh"

MEDIA="" NAME="" COPY_TO="" PUB_OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --media) MEDIA="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --copy-to) COPY_TO="$2"; shift 2 ;;
    --pub-out) PUB_OUT="$2"; shift 2 ;;
    *) echo "모르는 인자: $1" >&2; exit 2 ;;
  esac
done
case "$NAME" in u) PURPOSE=release ;; r) PURPOSE=root ;; *) echo "사용: --media <매체> --name u|r [--copy-to <둘째 매체>] [--pub-out <.pub>]" >&2; exit 2 ;; esac
[ "$NAME" = r ] || [ -z "$COPY_TO" ] || { echo "거부: --copy-to 는 R(둘째 벌) 전용" >&2; exit 2; }
PUB_OUT="${PUB_OUT:-./$NAME.pub}"
umask 077
# 대기 손잡이가 없는 의식이라 wait 칸 = 1(정책 검사의 「대기 0」 거부와 무관) · key id 는 아직 없다(-).
offline_dev_policy - 1 || exit 2
offline_media_check "$MEDIA" || exit 2
RM="$(_realpath "$MEDIA")"
KEY="$RM/$NAME.key"
[ ! -e "$KEY" ] && [ ! -L "$KEY" ] || { echo "거부: 매체에 키가 이미 있다(덮어쓰기 0): $KEY" >&2; exit 2; }
[ ! -e "$PUB_OUT" ] || { echo "거부: 공개키 산출이 이미 있다(덮어쓰기 0): $PUB_OUT" >&2; exit 2; }
if [ -n "$COPY_TO" ]; then
  offline_media_check "$COPY_TO" || exit 2
  RC="$(_realpath "$COPY_TO")"
  [ "$(_os_dev "$RC")" != "$(_os_dev "$RM")" ] || { echo "거부: 둘째 매체가 첫 매체와 같은 장치다(두 벌 = 서로 다른 매체)" >&2; exit 2; }
  [ ! -e "$RC/$NAME.key" ] && [ ! -L "$RC/$NAME.key" ] || { echo "거부: 둘째 매체에 키가 이미 있다: $RC/$NAME.key" >&2; exit 2; }
fi
MINI="$(_offline_minisign)"
# 비밀번호는 minisign 이 터미널에서 직접 묻는다(이 스크립트는 비밀번호를 만지지 않는다).
"$MINI" -G -p "$RM/$NAME.pub" -s "$KEY" || { rm -f "$KEY" "$RM/$NAME.pub"; echo "거부: minisign 키 생성 실패" >&2; exit 2; }
offline_media_guard "$MEDIA" "$KEY" || exit 2
if [ -n "$COPY_TO" ]; then
  cp "$KEY" "$RC/$NAME.key"
  cmp -s "$KEY" "$RC/$NAME.key" || { rm -f "$RC/$NAME.key"; echo "거부: 둘째 벌 바이트 불일치 — 둘째 매체 키 삭제" >&2; exit 2; }
  offline_media_guard "$COPY_TO" "$RC/$NAME.key" || exit 2
  cp "$RM/$NAME.pub" "$RC/$NAME.pub"
fi
cp "$RM/$NAME.pub" "$PUB_OUT"
KID="$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import update_common as uc; print(uc.pubkey_key_id(open(sys.argv[2], encoding="utf-8").read()))' "$HERE" "$PUB_OUT")" || exit 2
offline_dev_policy "$KID" 1 || { rm -f "$PUB_OUT"; exit 2; }
echo "✅ $PURPOSE 키 생성 — key id $KID · 개인키 = $KEY${COPY_TO:+ + $RC/$NAME.key} · 공개키 = $PUB_OUT"
echo "   다음: HANDOFF-U3 §1 ② 키링 기입(purpose=$PURPOSE · not_after = 결정 ③) · 매체를 빼서 보관"
