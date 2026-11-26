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
# ★1.1.20(#39 같은 자리 · F9 · B4) — sign-release.sh 와 같은 꼴: 산출 임시 파일은 어떻게 끝나든 지운다 · INT·TERM·HUP = rc 2.
TMP_DOC="" TMP_SIG=""
_sign_rev_cleanup() { set +e; [ -z "$TMP_DOC" ] || rm -f "$TMP_DOC"; [ -z "$TMP_SIG" ] || rm -f "$TMP_SIG"; return 0; }
trap _sign_rev_cleanup EXIT
trap 'exit 2' INT TERM HUP

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

META="$(_offline_py - "$HERE" "$DOC" <<'PY'
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
DIGEST="$(offline_sha256 "$DOC")" || exit 2  # (F8)
# (F9) 산출 폴더 임시 사본에 서명 → 본문 먼저 · 서명 나중으로 놓는다(sign-release.sh 와 같은 도우미).
TMP_DOC="$OUT_DIR/.revocations.json.tmp$$"
TMP_SIG="$TMP_DOC.minisig"
cp "$DOC" "$TMP_DOC" || { echo "거부: 폐기문을 산출 폴더로 옮기지 못했다(cp 실패) — 산출 0" >&2; exit 2; }
TSHA="$(offline_sha256 "$TMP_DOC")" || exit 2
[ "$TSHA" = "$DIGEST" ] || { echo "거부: 산출 폴더 폐기문 사본이 원본과 다르다 — 산출 0" >&2; exit 2; }
offline_sign root "$TMP_DOC" "$KEY" "$MEDIA" "$KEYRING" "$KID" "$TMP_SIG" "update-revocations rev=$REV sha256=$DIGEST" "$WAIT" || exit 2
offline_place_pair "$TMP_DOC" "$TMP_SIG" "$OUT" || exit 2
TMP_DOC="" TMP_SIG=""
echo "✅ R 의식 통과 — $OUT(.minisig) · rev $REV · key $KID · sha256 $DIGEST"
