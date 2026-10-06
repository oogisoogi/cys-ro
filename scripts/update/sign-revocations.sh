#!/usr/bin/env bash
# R 의식 — 폐기문에 R(복구 루트) 키로 서명한다(1.1.8 U3 · 설계 §4-1 R 행 · 절차 1쪽 = docs/update/R-RITUAL.md).
# U 의식과 같은 틀(scripts/update/lib/offline-sign.sh): R 개인키는 오프라인 매체 안에서만 열린다 · 서명만 꺼낸다 ·
# 매체를 뺀 뒤 내장 R 공개키(키링 purpose=root)로 검증해야 산출물이 생긴다. 사건 때만 돈다(정기 0).
#
# 사용:
#   scripts/update/sign-revocations.sh --doc revocations.json --media /Volumes/CYS-R --key /Volumes/CYS-R/r.key \
#       [--keyring cysjavis-pack/trusted-keys.json] [--out-dir dist/update] [--wait-eject 300]
# 산출: <out-dir>/revocations.json + .minisig · 종료 0 = 통과 · 2 = 거부(산출물 0)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck source=lib/offline-sign.sh
. "$HERE/lib/offline-sign.sh"

DOC="" MEDIA="" KEY="" KEYRING="$ROOT/cysjavis-pack/trusted-keys.json" OUT_DIR="." WAIT=300
while [ $# -gt 0 ]; do
  case "$1" in
    --doc) DOC="$2"; shift 2 ;;
    --media) MEDIA="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    --keyring) KEYRING="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --wait-eject) WAIT="$2"; shift 2 ;;
    *) echo "모르는 인자: $1" >&2; exit 2 ;;
  esac
done
[ -n "$DOC" ] && [ -n "$MEDIA" ] && [ -n "$KEY" ] || { echo "사용: --doc <폐기문> --media <매체> --key <매체 안 r.key>" >&2; exit 2; }

META="$(python3 - "$HERE" "$DOC" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1])
import update_common as uc
d = json.load(open(sys.argv[2], encoding="utf-8"))
if d.get("kind") != uc.REVOCATIONS_KIND or not isinstance(d.get("rev"), int) or d["rev"] < 1:
    print("거부: 폐기문 서식 아님(kind/rev)", file=sys.stderr); sys.exit(2)
if not uc.KEY_ID_RE.match(d.get("key_id") or ""):
    print("거부: key_id 형식", file=sys.stderr); sys.exit(2)
print(d["rev"], d["key_id"])
PY
)" || exit 2
read -r REV KID <<<"$META"

mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/revocations.json"
[ -e "$OUT" ] || [ -e "$OUT.minisig" ] && { echo "거부: 산출물이 이미 있다(덮어쓰기 0): $OUT" >&2; exit 2; }
DIGEST="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$DOC")"
offline_sign root "$DOC" "$KEY" "$MEDIA" "$KEYRING" "$KID" "$OUT.minisig" "update-revocations rev=$REV sha256=$DIGEST" "$WAIT" || exit 2
cp "$DOC" "$OUT"
echo "✅ R 의식 통과 — $OUT(.minisig) · rev $REV · key $KID · sha256 $DIGEST"
