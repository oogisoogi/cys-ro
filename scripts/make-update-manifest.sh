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
  # ★자산 이름의 arch 어휘는 **발행본**을 따른다(2026-09-20 · TICKET=v110-zipurl).
  #   매니페스트 **행 이름**은 darwin-x86_64 지만 **파일 이름**은 x64 다 —
  #   release-postprocess.py MAC_LANE · release-verify.py LANE · verify-release-remote.py
  #   VERSIONLESS_ASSETS 셋이 전부 `cysr_x64.app.tar.gz` 를 못박고 있고, 구판 tarball 생성기
  #   (make-darwin-updater-tarball.sh)도 그 이름으로 낸다. 여기만 다른 어휘를 쓰면
  #   latest.json 의 url 이 **발행되지 않는 이름**을 가리킨다(구판 업데이트 404).
  case "$KEY" in
    darwin-aarch64) ARCH=aarch64 ;;
    darwin-x86_64)  ARCH=x64 ;;
    *) echo "unexpected platform key: $KEY" >&2; exit 2 ;;
  esac
  BUNDLE="target/$TRIPLE/release/bundle/macos"
  [ -f "$BUNDLE/cysr.app.tar.gz.sig" ] || {
    # 네이티브 빌드는 타깃 마디 없이 떨어진다
    [ "$TRIPLE" = "$HOST_TRIPLE" ] && BUNDLE="target/release/bundle/macos"
  }
  SIG_FILE="$BUNDLE/cysr.app.tar.gz.sig"
  TARBALL="$BUNDLE/cysr.app.tar.gz"
  [ -f "$SIG_FILE" ] && [ -f "$TARBALL" ] || { echo "  · $KEY 건너뜀 — $SIG_FILE 없음"; continue; }
  SIGNATURE="$(cat "$SIG_FILE")"
  # ★이름은 `make-darwin-updater-tarball.sh` 와 **한 벌**이어야 한다 —
  #   scripts/tests/test_darwin_asset_name_alignment.py 가 두 생성기를 실제로 돌려 대조한다.
  ASSET="cysr_${ARCH}.app.tar.gz"
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

# ★★darwin 행은 **두 소비자가 나눠 쓴다**(TICKET=v110-zipurl · 2026-09-20).
#   · 이 스크립트가 찍는 `url`+`signature` = **구판(1.0.2) 플러그인 경로**의 `.app.tar.gz`.
#   · `zip_url`/`zip_sha256`/`zip_size`/`zip_cdhash` = **1.1+ 앱**(src-tauri/src/macupdate.rs).
#     그 넷은 `scripts/make-darwin-update-row.py --merge` 가 나중에 얹는다.
#   한 칸(`url`)을 둘이 나눠 쓰면 다음 판에서 반드시 한쪽이 틀린 물건을 받는다 — 그래서 갈랐다.
PREV_JSON=""
[ -f dist-update/latest.json ] && PREV_JSON="$(cat dist-update/latest.json)"

cat > dist-update/latest.json <<JSON
{
  "version": "${VERSION}",
  "notes": "${NOTES}",
  "pub_date": "${PUBDATE}",
  "platforms": {${PLATFORMS}
  }
}
JSON

# ★순서 의존을 없앤다: 앞서 얹혀 있던 zip_* 넷(앱 절반)을 새 파일에 **되살린다**.
#   이 스크립트가 통째로 다시 쓰는 구조라, 이 줄이 없으면 「행 병합 → 매니페스트 재생성」 순서에서
#   앱 절반이 조용히 사라진다(그리고 1.1 맥은 그 판을 「맥 zip 항목 없음」으로 거부한다 — 무증상 아님).
if [ -n "$PREV_JSON" ]; then
  printf '%s' "$PREV_JSON" | python3 - dist-update/latest.json <<'PY'
import json, sys
new_path = sys.argv[1]
prev = json.loads(sys.stdin.read() or "{}")
with open(new_path, encoding="utf-8") as fh:
    cur = json.load(fh)
ZIP_KEYS = ("zip_url", "zip_sha256", "zip_size", "zip_cdhash")
carried = []
for name, row in (prev.get("platforms") or {}).items():
    if not name.startswith("darwin-") or not isinstance(row, dict):
        continue
    keep = {k: row[k] for k in ZIP_KEYS if k in row}
    if keep and name in (cur.get("platforms") or {}):
        cur["platforms"][name].update(keep)
        carried.append(name)
if carried:
    with open(new_path, "w", encoding="utf-8") as fh:
        json.dump(cur, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("  · zip_* 보존:", ", ".join(carried))
PY
fi

echo "생성됨:"
echo "  dist-update/latest.json"
echo "  dist-update/${ASSET}"
echo ""
echo "⚠ 이 매니페스트의 darwin 행은 아직 **구판(plugin) 절반**뿐이다 — 1.1+ 앱이 읽는 zip 칸이 없다."
echo "  이어서 맥 zip 을 얹어라(없으면 1.1 맥은 「이 판의 매니페스트에는 맥 zip 항목이 없습니다」로 거부한다):"
echo "  python3 scripts/make-darwin-update-row.py --version ${VERSION} \\"
echo "    --zip dist-mac/cysr-macos-arm64-v${VERSION}.zip --app dist-mac/staging/cysr.app \\"
echo "    --merge dist-update/latest.json"
echo ""
echo "GitHub 릴리스에 올릴 자산: 위 두 파일 + DMG"
echo "  gh release create v${VERSION} \\"
echo "    dist-update/latest.json \\"
echo "    dist-update/${ASSET} \\"
echo "    dist-mac/cysr-${VERSION}-macos-arm64.dmg"
echo ""
echo "맥 두 칩(darwin-aarch64·darwin-x86_64)은 위에서 **찾은 만큼 자동으로** 실렸다 — 한쪽이 「건너뜀」이면 그 칩 빌드를 먼저 하라."
echo "⚠ Windows 플랫폼 키는 그 타깃 빌드 후 platforms 에 추가하라(RELEASE.md)."
