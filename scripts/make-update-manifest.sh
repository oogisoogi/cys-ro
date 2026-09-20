#!/bin/sh
# 자동 업데이트 manifest(latest.json) 생성 — tauri build가 만든 서명(.sig)을 모아
# Tauri updater가 읽는 표준 포맷으로 묶는다.
#
# 전제: `bun x @tauri-apps/cli build`를 TAURI_SIGNING_PRIVATE_KEY(+PASSWORD)로 실행해
#       createUpdaterArtifacts 산출물(.app.tar.gz + .app.tar.gz.sig)이 생성돼 있어야 한다.
#
# 사용:  sh scripts/make-update-manifest.sh <version> <github_owner> [repo]
#   맥 두 칩 번들이 있으면 **둘 다** latest.json 에 실린다(aarch64 · x86_64 · 2026-09-20).
# 예:    sh scripts/make-update-manifest.sh 0.2.0 cysfuturist cys-terminal
set -e
cd "$(dirname "$0")/.."

VERSION="${1:?usage: make-update-manifest.sh <version> <owner> [repo]}"
OWNER="${2:?owner required}"
REPO="${3:-cys-terminal}"
NOTES="${UPDATE_NOTES:-cys $VERSION}"

# ★칩 두 갈래를 **함께** 싣는다 (2026-09-20 · TICKET=v110-mac-x64).
#   종전에는 네이티브 번들 자리(target/release/…) 하나만 읽어 latest.json 에 darwin-aarch64 만 적었다.
#   그래서 인텔 맥은 자동 업데이트 대상에서 통째로 빠져 있었고, 그 사실을 아무 줄도 말하지 않았다
#   (말미 안내문만 「직접 추가하라」고 적혀 있었다 — 사람 기억에 맡긴 자리는 잊힌다).
#   ⇒ 있는 것을 싣고, **하나도 없으면 실패**한다. 한쪽만 있으면 그쪽만 싣고 그 사실을 화면에 적는다.
#   ⚠크로스 빌드는 산출 자리에 타깃 마디가 낀다(target/<triple>/release/…) — 두 자리를 모두 본다.
PUBDATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
HOST_TRIPLE="$([ "$(uname -m)" = "arm64" ] && echo aarch64-apple-darwin || echo x86_64-apple-darwin)"
mkdir -p dist-update
PLATFORMS=""
FOUND=0
for pair in "darwin-aarch64:aarch64-apple-darwin" "darwin-x86_64:x86_64-apple-darwin"; do
  KEY="${pair%%:*}"; TRIPLE="${pair#*:}"
  ARCH="${KEY#darwin-}"
  BUNDLE="target/$TRIPLE/release/bundle/macos"
  [ -f "$BUNDLE/cysr.app.tar.gz.sig" ] || {
    # 네이티브 빌드는 타깃 마디 없이 떨어진다
    [ "$TRIPLE" = "$HOST_TRIPLE" ] && BUNDLE="target/release/bundle/macos"
  }
  SIG_FILE="$BUNDLE/cysr.app.tar.gz.sig"
  TARBALL="$BUNDLE/cysr.app.tar.gz"
  [ -f "$SIG_FILE" ] && [ -f "$TARBALL" ] || { echo "  · $KEY 건너뜀 — $SIG_FILE 없음"; continue; }
  SIGNATURE="$(cat "$SIG_FILE")"
  ASSET="cysr-${VERSION}-macos-${ARCH}.app.tar.gz"
  URL="https://github.com/${OWNER}/${REPO}/releases/download/v${VERSION}/${ASSET}"
  cp "$TARBALL" "dist-update/${ASSET}"
  [ -n "$PLATFORMS" ] && PLATFORMS="$PLATFORMS,"
  PLATFORMS="$PLATFORMS
    \"$KEY\": {
      \"signature\": \"${SIGNATURE}\",
      \"url\": \"${URL}\"
    }"
  FOUND=$((FOUND + 1))
  echo "  · $KEY ← $BUNDLE"
done

if [ "$FOUND" -eq 0 ]; then
  echo "error: 업데이터 산출물(cysr.app.tar.gz(.sig))을 두 칩 자리 어디에서도 못 찾았다 — 먼저 서명 키로 tauri build 를 실행하라:" >&2
  echo "  TAURI_SIGNING_PRIVATE_KEY=\$(cat ~/.tauri/cys-updater-A2.key) bun x @tauri-apps/cli build [--target <triple>]" >&2
  exit 1
fi

cat > dist-update/latest.json <<JSON
{
  "version": "${VERSION}",
  "notes": "${NOTES}",
  "pub_date": "${PUBDATE}",
  "platforms": {${PLATFORMS}
  }
}
JSON

echo "생성됨:"
echo "  dist-update/latest.json"
echo "  dist-update/${ASSET}"
echo ""
echo "GitHub 릴리스에 올릴 자산: 위 두 파일 + DMG"
echo "  gh release create v${VERSION} \\"
echo "    dist-update/latest.json \\"
echo "    dist-update/${ASSET} \\"
echo "    dist-mac/cysr-${VERSION}-macos-arm64.dmg"
echo ""
echo "맥 두 칩(darwin-aarch64·darwin-x86_64)은 위에서 **찾은 만큼 자동으로** 실렸다 — 한쪽이 「건너뜀」이면 그 칩 빌드를 먼저 하라."
echo "⚠ Windows 플랫폼 키는 그 타깃 빌드 후 platforms 에 추가하라(RELEASE.md)."
