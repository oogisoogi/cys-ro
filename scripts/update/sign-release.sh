#!/usr/bin/env bash
# U 의식 — 릴리스 본문에 U(릴리스) 키로 서명한다(1.1.8 U3 · 설계 AUTO-UPDATE-118 §8 「U 의식 절차(📌11)」 ①~⑥).
#
# 절차(이 스크립트가 ②~⑥ 을 강제한다 · ① = scripts/update/make-release-json.py):
#   ① 빌드 기기에서 릴리스 본문 JSON 을 만든다(서명 없음).
#   ② 본문 파일만 서명 매체 쪽으로 옮긴다(본문은 공개 정보).
#   ③ U 개인키는 매체 안에서만 연다 — `--key` 가 `--media` 마운트 아래가 아니면 거부(복사·클립보드·셸 기록 0).
#   ④ 서명(.minisig)만 꺼낸다.
#   ⑤ 매체를 뺀다(박사님 손 1단계 · 기본 = 빠질 때까지 최대 300초 기다림).
#   ⑥ 내장 U 공개키(키링 purpose=release · 본문 key_id)로 검증해야 산출물이 생긴다 → 게시 단계(publish-archive.py).
#
# 사용:
#   scripts/update/sign-release.sh --body cysr-release-12.json --media /Volumes/CYS-U --key /Volumes/CYS-U/u.key \
#       [--keyring cysjavis-pack/trusted-keys.json] [--out-dir dist/update] [--wait-eject 300]
# 산출: <out-dir>/<component>-release-<seq>.json + .minisig (본문 바이트 그대로 · 서명은 파일 바이트 전체)
# 종료: 0 = 서명·검증 통과 · 2 = 거부(산출물 0)
# 시험: CYS_SIGN_DEV=1 + MINISIGN=<가짜 minisign> · CYS_SIGN_MEDIA_PREFIX=<가짜 매체 부모> · --wait-eject 0 — 실키 0.
#   (개발 모드 밖에서 이 손잡이가 보이면 거부 · 개발 모드는 저장소 실 키링 key id 거부 — lib/offline-sign.sh)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck source=lib/offline-sign.sh
. "$HERE/lib/offline-sign.sh"

BODY="" MEDIA="" KEY="" KEYRING="$ROOT/cysjavis-pack/trusted-keys.json" OUT_DIR="." WAIT=300
while [ $# -gt 0 ]; do
  case "$1" in
    --body) BODY="$2"; shift 2 ;;
    --media) MEDIA="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    --keyring) KEYRING="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --wait-eject) WAIT="$2"; shift 2 ;;
    *) echo "모르는 인자: $1" >&2; exit 2 ;;
  esac
done
[ -n "$BODY" ] && [ -n "$MEDIA" ] && [ -n "$KEY" ] || { echo "사용: --body <본문> --media <매체> --key <매체 안 u.key>" >&2; exit 2; }

# 본문 서식 확인(생산자 검사) — kind·component·release_seq·key_id 를 읽는다.
META="$(python3 - "$HERE" "$BODY" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1])
import update_common as uc
b = json.load(open(sys.argv[2], encoding="utf-8"))
if b.get("kind") != uc.RELEASE_KIND or b.get("component") not in uc.COMPONENTS:
    print("거부: 릴리스 본문 서식 아님(kind/component)", file=sys.stderr); sys.exit(2)
if not isinstance(b.get("release_seq"), int) or b["release_seq"] < 1 or not uc.KEY_ID_RE.match(b.get("key_id") or ""):
    print("거부: release_seq/key_id 형식", file=sys.stderr); sys.exit(2)
try:
    uc.check_notes_ko(b.get("notes_ko"))
except uc.PublishError as e:
    print("거부: %s" % e, file=sys.stderr); sys.exit(2)
print(b["component"], b["release_seq"], b["key_id"])
PY
)" || exit 2
read -r COMP SEQ KID <<<"$META"

mkdir -p "$OUT_DIR"
OUT_BODY="$OUT_DIR/$COMP-release-$SEQ.json"
[ -e "$OUT_BODY" ] || [ -e "$OUT_BODY.minisig" ] && { echo "거부: 산출물이 이미 있다(덮어쓰기 0): $OUT_BODY" >&2; exit 2; }
DIGEST="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$BODY")"

if ! offline_sign release "$BODY" "$KEY" "$MEDIA" "$KEYRING" "$KID" "$OUT_BODY.minisig" \
     "$COMP-release seq=$SEQ sha256=$DIGEST" "$WAIT"; then
  exit 2
fi
cp "$BODY" "$OUT_BODY"
echo "✅ U 의식 통과 — $OUT_BODY(.minisig) · key $KID · 본문 sha256 $DIGEST"
