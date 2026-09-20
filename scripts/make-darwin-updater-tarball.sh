#!/bin/sh
# make-darwin-updater-tarball.sh — 구(1.0.2) 맥 클라이언트를 위한 **플러그인 경로 자산** 생성
# (B 채택 · master 판정 2026-09-20 · TICKET=v110-darwin-update).
#
# 왜 필요한가: 1.1 부터 맥은 우리 경로(zip + sha256/CDHash)로 갱신한다. 그런데 **이미 깔려 있는
# 1.0.2 맥**은 그 코드를 모른다 — tauri-plugin-updater 로만 갱신한다. latest.json 에 darwin 행이
# 생기는 순간 그 구판은 행을 집어 **우리 zip 을 tar.gz 로 풀려다 실패**한다. 그래서 같은 태그에
# 구판이 먹을 수 있는 `.app.tar.gz` + `.sig` 를 함께 올린다(구판 오류 0).
#
# 산출(로컬 자체서명 zip 과 같은 폴더 = 기본 dist-mac):
#   dist-mac/cysr_<arch>.app.tar.gz        ← release-verify.py MAC_LANE 이름과 같다
#   dist-mac/cysr_<arch>.app.tar.gz.sig    ← 서명 키가 있을 때만
#   dist-mac/cysr_<arch>.app.tar.gz.sig.MISSING ← 키가 없을 때의 자리표시(발행 금지 표식)
#
# ⛔키를 만들지 않는다. 서명은 **이미 있는** 비밀로만 한다:
#   TAURI_SIGNING_PRIVATE_KEY (+ TAURI_SIGNING_PRIVATE_KEY_PASSWORD) — 윈도 .sig 와 같은 키.
#   키가 없으면 tar.gz 만 만들고 **rc 3** 으로 끝낸다(서명 없는 자산의 무증상 발행 차단).
#
# 사용: sh scripts/make-darwin-updater-tarball.sh --app dist-mac/staging/cysr.app [--out dist-mac] [--arch aarch64]
set -e

APP=""
OUT="dist-mac"
ARCH=""
while [ $# -gt 0 ]; do
  case "$1" in
    --app) APP="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --arch) ARCH="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$APP" ] || { echo "usage: --app <path/cysr.app> [--out dir] [--arch aarch64|x64]" >&2; exit 2; }
[ -d "$APP" ] || { echo "error: .app 이 없다: $APP" >&2; exit 2; }
if [ -z "$ARCH" ]; then
  case "$(uname -m)" in arm64) ARCH="aarch64" ;; x86_64) ARCH="x64" ;; *) ARCH="$(uname -m)" ;; esac
fi

APP_PARENT="$(cd "$(dirname "$APP")" && pwd)"
APP_NAME="$(basename "$APP")"
mkdir -p "$OUT"
OUT_ABS="$(cd "$OUT" && pwd)"
TAR="$OUT_ABS/cysr_${ARCH}.app.tar.gz"

# ★최상위 구성요소가 **정확히 하나**여야 한다. 플러그인은 각 항목 경로의 첫 구성요소를 버리고
#   (updater.rs:1238 `entry.path()?.iter().skip(1)`) 나머지를 **기존 번들 자리**에 넣기 때문이다.
#   둘 이상이면 두 번째부터가 엉뚱한 자리에 풀린다.
# ★COPYFILE_DISABLE=1 — 맥 tar(bsdtar)는 확장속성이 붙은 항목마다 AppleDouble 짝(`._이름`)을
#   같이 넣는다. 그러면 최상위 구성요소가 `cysr.app` 과 `._cysr.app` **둘**이 되어 위 규칙이 깨지고,
#   구판 플러그인은 그 쓰레기를 번들 자리에 함께 푼다. tauri 번들러는 Rust `tar` 크레이트라 애초에
#   AppleDouble 을 안 만든다 — 그 산출물과 같은 모양으로 맞춘다.
#   (이 줄이 없으면 실제로 `._cysr.app` 이 생기는 것을 scripts/tests/test_darwin_updater_tarball.py 가 잡았다.)
rm -f "$TAR"
COPYFILE_DISABLE=1 tar czf "$TAR" -C "$APP_PARENT" "$APP_NAME"

TOPS="$(tar tzf "$TAR" | awk -F/ '{print $1}' | sort -u | wc -l | tr -d ' ')"
[ "$TOPS" = "1" ] || { echo "error: tar 최상위 구성요소가 $TOPS 개다(1 이어야 한다)" >&2; tar tzf "$TAR" | awk -F/ '{print $1}' | sort -u >&2; rm -f "$TAR"; exit 1; }
# AppleDouble 잔재가 하나라도 있으면 거부한다(최상위가 아니어도 구판이 그대로 푼다).
if tar tzf "$TAR" | grep -q '/\._\|^\._'; then
  echo "error: AppleDouble(._*) 항목이 들어갔다 — COPYFILE_DISABLE 이 먹지 않았다" >&2; rm -f "$TAR"; exit 1
fi
echo "✓ tar 생성: $TAR ($(tar tzf "$TAR" | awk -F/ '{print $1}' | sort -u) · $(wc -c < "$TAR") B)"

if [ -z "${TAURI_SIGNING_PRIVATE_KEY:-}" ]; then
  cat > "$TAR.sig.MISSING" <<'NOTE'
서명 없음 — 이 자산은 발행하면 안 된다.
TAURI_SIGNING_PRIVATE_KEY(+ _PASSWORD)가 있는 환경(CI secrets 또는 키 보유 기기)에서
같은 스크립트를 다시 돌려 .sig 를 만든 뒤 발행하라. 키를 새로 만들지 마라 —
새 키로 서명하면 이미 배포된 1.0.2 의 pubkey 와 어긋나 구판이 검증에 실패한다.
NOTE
  echo "⚠ 서명 키 없음(TAURI_SIGNING_PRIVATE_KEY) — tar 만 만들었다. 자리표시: $TAR.sig.MISSING" >&2
  exit 3
fi

rm -f "$TAR.sig.MISSING"
bunx "@tauri-apps/cli@${TAURI_CLI_VERSION:-2}" signer sign \
  --private-key "$TAURI_SIGNING_PRIVATE_KEY" \
  --password "${TAURI_SIGNING_PRIVATE_KEY_PASSWORD:-}" \
  "$TAR"
[ -s "$TAR.sig" ] || { echo "error: .sig 가 비었다 — 서명 실패" >&2; exit 1; }
echo "✓ 서명: $TAR.sig ($(wc -c < "$TAR.sig") B)"
echo "  latest.json 의 platforms[darwin-${ARCH}].signature = 이 .sig 파일 **전문**(base64 문자열 그대로)"
