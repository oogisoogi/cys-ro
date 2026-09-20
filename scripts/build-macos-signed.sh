#!/usr/bin/env bash
# build-macos-signed.sh — Apple Developer ID 서명 + 공증(notarization) + staple 자동 빌드.
# (오너 2026-06-15) ad-hoc 빌드는 다른 맥으로 전송하면 quarantine + 미공증으로 macOS가
# "손상됨(damaged)"으로 차단한다. Developer ID 인증서 + notarytool 자격증명이 있으면 Tauri가
# 빌드 중 자동으로 codesign(hardened runtime) + notarytool 공증 + stapler staple 한다.
# 이 스크립트는 자격증명을 fail-closed로 검증하고, 빌드 후 Gatekeeper 통과를 실측 확인한다.
#
# 사전(1회 셋업):
#   1) Apple Developer Program 가입($99/년) → "Developer ID Application" 인증서 발급·Keychain 설치
#   2) appleid.apple.com 에서 app-specific password 발급 (또는 App Store Connect API key)
#   3) 아래 env 설정
# 사용:
#   export APPLE_SIGNING_IDENTITY="Developer ID Application: NAME (TEAMID)"
#   export APPLE_ID="you@example.com" APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx" APPLE_TEAM_ID="TEAMID"
#   #   (또는 API key: APPLE_API_KEY_PATH=AuthKey_XXXX.p8 · APPLE_API_KEY=KEYID · APPLE_API_ISSUER=ISSUER)
#   export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/cys-updater.key)" TAURI_SIGNING_PRIVATE_KEY_PASSWORD=""
#   scripts/build-macos-signed.sh
# exit 0=서명·공증·검증 통과 / 1=공증 검증 실패 / 2=자격증명·환경 미비
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
VERSION=$(grep -m1 '"version"' src-tauri/tauri.conf.json | sed -E 's/.*"([0-9][0-9.]*)".*/\1/')

# ── Tauri CLI 버전 고정 (W5-1 · 2026-08-29) ──
# 단일 SOT 는 CI 워크플로 env `TAURI_CLI_VERSION`(release.yml·windows-build.yml)이고, 아래 기본값은
# 로컬 실행용 동치다(CI 는 env 로 이 값을 덮는다 — 값이 갈리면 안 되므로 바꿀 땐 세 곳을 함께).
# 2.11.4 = 오늘 npm latest 실측이자 0.14.27 을 빌드한 버전 — floating(@2·무버전)도 지금은 2.11.4 로
# 해소되므로 동작 무변경이며, 목적은 NSIS 템플릿(installer.nsi)·번들러 거동의 무음 교체 차단이다.
# ★이보다 낮추지 마라: `/UPDATE`→`$UpdateMode` 없는 구 템플릿으로 회귀하면 인앱 업데이트가
#   '제거 후 설치'로 강등된다(무음 재앙 · IMPL-SPEC §W5-1).
TAURI_CLI_VERSION="${TAURI_CLI_VERSION:-2.11.4}"

# ── 비-Apple 단계는 공유 함수 파일 하나에 있다 (2026-09-20 · TICKET=v110-mac-x64) ──
#   같은 단계를 자체서명 경로(scripts/build-macos-local.sh)도 쓴다. 복사해 두 벌로 두면 한쪽만
#   고치는 날이 오므로 **함수로 갈라 양쪽이 source** 한다 — 무엇이 공유이고 무엇이 서명 정책인지는
#   그 파일 머리말에 적혀 있다. 이 스크립트에 남은 것은 Apple 서명·공증·staple·DMG 조립뿐이다.
# 사용: scripts/build-macos-signed.sh [aarch64-apple-darwin|x86_64-apple-darwin]
. scripts/lib/mac-bundle-common.sh   # ★cd 뒤라 저장소 루트 기준 경로가 결정론이다($0 는 호출 방식에 흔들린다)
mac_resolve_target "${1:-}"

# ── 자격증명 fail-closed 검증 ──
: "${APPLE_SIGNING_IDENTITY:?필요: export APPLE_SIGNING_IDENTITY='Developer ID Application: NAME (TEAMID)'}"
if [ -n "${APPLE_NOTARY_PROFILE:-}" ]; then
  echo "공증 자격: notarytool keychain 프로파일($APPLE_NOTARY_PROFILE)"
elif [ -n "${APPLE_API_KEY:-}" ]; then
  : "${APPLE_API_ISSUER:?APPLE_API_KEY 사용 시 APPLE_API_ISSUER 필요}"
  echo "공증 자격: App Store Connect API key"
else
  : "${APPLE_ID:?공증용 Apple ID 필요 (또는 APPLE_NOTARY_PROFILE / APPLE_API_KEY)}"
  : "${APPLE_PASSWORD:?app-specific password 필요 (APPLE_PASSWORD)}"
  : "${APPLE_TEAM_ID:?APPLE_TEAM_ID 필요}"
  echo "공증 자격: Apple ID($APPLE_ID) + app-specific password"
fi
command -v xcrun >/dev/null || { echo "✗ Xcode Command Line Tools 필요(xcrun) — xcode-select --install"; exit 2; }
if ! security find-identity -v -p codesigning 2>/dev/null | grep -q "Developer ID Application"; then
  echo "✗ Keychain에 'Developer ID Application' 인증서 없음 — Apple Developer에서 발급·설치 필요"; exit 2
fi
# ★fail-closed 승격(2026-07-10 · v0.12.35 빌드 1차 실패 원인): 구 경고문("미설정이어도 설치 DMG는 정상")은
# 실동작과 표류 — tauri.conf createUpdaterArtifacts 때문에 tauri build가 빌드 말미(~20분 후)에 hard-fail한다.
# 20분 낭비 대신 여기서 3초 만에 명확히 실패시킨다(다른 자격증명 검증과 동형).
if [ -z "${TAURI_SIGNING_PRIVATE_KEY:-}" ]; then
  echo "✗ TAURI_SIGNING_PRIVATE_KEY 미설정 — tauri build가 updater 아티팩트 서명에서 실패한다(빌드 말미 hard-fail)." >&2
  echo "  설정: export TAURI_SIGNING_PRIVATE_KEY=\"\$(cat ~/.tauri/cys-updater.key)\" TAURI_SIGNING_PRIVATE_KEY_PASSWORD=\"\"" >&2
  exit 2
fi

mac_prep_runtime

mac_precompile_python

echo "== 동봉 runtime Mach-O inside-out 재서명 (Developer ID + hardened + timestamp) =="
ENT="src-tauri/entitlements.plist"
SIGN_N=0
# 1) 동적 라이브러리·로드가능 번들(.dylib/.so/.node) 먼저 — entitlements 불요
while IFS= read -r -d '' lib; do
  codesign --force --timestamp --options runtime --sign "$APPLE_SIGNING_IDENTITY" "$lib"
  SIGN_N=$((SIGN_N+1))
done < <(find src-tauri/runtime \( -name '*.dylib' -o -name '*.so' -o -name '*.node' \) -type f -print0)
# 2) Mach-O 실행 바이너리(라이브러리 제외) — ★최소권한(codex T6b.1): 인터프리터(python·node V8 JIT)만
#    entitlements 적용, git/uv는 entitlements 없이 runtime 서명(경로 기반 분류·불필요 권한 확산 방지).
while IFS= read -r -d '' exe; do
  if file "$exe" | grep -q 'Mach-O'; then
    case "$exe" in
      src-tauri/runtime/python/*|src-tauri/runtime/node/*)
        codesign --force --timestamp --options runtime --entitlements "$ENT" --sign "$APPLE_SIGNING_IDENTITY" "$exe" ;;
      *)  # git·uv 등 — JIT/라이브러리검증 완화 불요 → entitlements 없이 hardened 서명
        codesign --force --timestamp --options runtime --sign "$APPLE_SIGNING_IDENTITY" "$exe" ;;
    esac
    SIGN_N=$((SIGN_N+1))
  fi
done < <(find src-tauri/runtime -type f -perm +111 ! -name '*.dylib' ! -name '*.so' ! -name '*.node' -print0)
echo "  ✓ runtime Mach-O ${SIGN_N}개 재서명 (python/node=entitlements·git/uv=무 entitlements)"

mac_build_app_bundle

mac_assert_pyc_imported

mac_dedup_and_restore

mac_emit_runtime_manifest
# dedup은 Resources를 바꿔 Tauri가 봉인한 외부 앱 서명을 깬다 → 외부 앱 서명만 재봉인(--force · ★--deep 금지).
# 중첩 Mach-O(pre-sign된 runtime bin/git·Tauri가 서명한 sidecar/framework/메인바이너리)는 그대로 유효하다.
echo "== dedup 후 외부 앱 서명 재봉인 (inside-out 유지·--deep 금지) =="
codesign --force --options runtime --timestamp --entitlements "$ENT" --sign "$APPLE_SIGNING_IDENTITY" "$APP"

# ★동봉 Mach-O 포함 앱 전체 서명 무결성 검증 (공증 제출 전) — dedup 심볼릭링크 포함 sealed resource 검증.
# --deep는 *검증 전용*으로만 사용(D-4 규칙 유지 — 서명은 inside-out 개별, 검증은 --deep 허용). 실측: 링크 트리 통과.
echo "== 동봉 서명 검증: codesign --verify --deep --strict (제출 전) =="
if codesign --verify --deep --strict --verbose=4 "$APP" 2>&1; then
  echo "  ✓ codesign --verify --deep --strict 통과 (dedup 링크 포함 중첩 서명 무결)"
else
  echo "  ✗ 서명 검증 실패 — 중첩 바이너리 서명 결손. 위 로그의 offender 재서명 필요"; exit 1
fi

# ── 공증(1회) + staple + DMG/업데이터 재생성 ──
# ⚠ 아래 notarytool/stapler/signer 경로는 Apple Developer 자격·업데이터 키가 필요해 워커 환경에선 실행 검증
#   불가 — dedup/재서명/hdiutil UDZO/codesign --verify 는 실측 통과. 오너 자격으로 최종 실행 검증을 요한다.
# notarytool 자격: APPLE_NOTARY_PROFILE(keychain 프로파일·오너 로컬 기본) > APPLE_API_KEY > APPLE_ID 3원 (상단서 fail-closed 검증됨).
if [ -n "${APPLE_NOTARY_PROFILE:-}" ]; then
  NOTARY_ARGS=(--keychain-profile "$APPLE_NOTARY_PROFILE")
elif [ -n "${APPLE_API_KEY:-}" ]; then
  NOTARY_ARGS=(--key "${APPLE_API_KEY_PATH:?APPLE_API_KEY 사용 시 APPLE_API_KEY_PATH(.p8) 필요}" --key-id "$APPLE_API_KEY" --issuer "$APPLE_API_ISSUER")
else
  NOTARY_ARGS=(--apple-id "$APPLE_ID" --password "$APPLE_PASSWORD" --team-id "$APPLE_TEAM_ID")
fi

echo "== 공증: 앱(zip 제출) → staple (dmg 안에 staple된 앱을 담아 offline 검증까지 견고) =="
APPZIP="$APP.notarize.zip"
ditto -c -k --keepParent "$APP" "$APPZIP"
xcrun notarytool submit "$APPZIP" "${NOTARY_ARGS[@]}" --wait
xcrun stapler staple "$APP"
rm -f "$APPZIP"

# 업데이터 아티팩트 재생성(dedup 반영): Tauri가 만든 fat cysr.app.tar.gz(447MB)를 dedup·staple된 앱으로
# 다시 tar(심볼릭링크 보존 → 다운로드 축소)하고 업데이터 키로 재서명. make-update-manifest.sh가 이 .sig를 읽는다.
# (주의: Tauri 업데이터 *클라이언트*의 심볼릭링크 보존은 버전의존 #7480 — 다운로드는 축소되나 설치 후 on-disk
#  크기는 클라이언트 tauri 동작에 좌우될 수 있음. 신규 설치 경로인 DMG는 확실히 축소된다.)
if [ -n "${TAURI_SIGNING_PRIVATE_KEY:-}" ]; then
  echo "== 업데이터 tar.gz 재생성(dedup 반영) + 재서명 =="
  ( cd "$(dirname "$APP")" && tar czf cysr.app.tar.gz cysr.app )
  bun x "@tauri-apps/cli@${TAURI_CLI_VERSION}" signer sign --private-key "$TAURI_SIGNING_PRIVATE_KEY" --password "" "$APP.tar.gz"
fi

# ★DMG 델타 실측 (2026-08-01 · SEAL-2 opt 레벨 3종 봉합의 배포 크기 비용)
#   동일 조립·ad-hoc 서명 번들(python 3.12.13 + node 22.17.1)로 이 줄과 **같은 UDZO** 를 생성해 비교:
#     opt-0 전용 : 스테이지 213MB → DMG 102,180,464 B (97.4MB)
#     opt-0/1/2  : 스테이지 252MB → DMG 123,644,389 B (117.9MB)
#     델타       : **+21,463,925 B (+20.5MB, +21.0%)** — 비압축 트리 +57MB 가 UDZO 로 약 2.7:1 압축된 값.
#   ※위 수치의 분모는 python+node 만 담은 부분 스테이지다. 실제 DMG 에는 git·uv·앱 바이너리·UI 가
#     더 들어가 **분모가 커지므로 증가율은 위보다 작아진다**(절대 델타 ≈ +20.5MB 는 그대로).
# ── 설치 도우미(Install cys.app) 빌드·서명·공증·staple (3번째 공증 제출) ──
# 왜: Finder 드래그(=최종 경로 직접 복사)는 트랜잭션이 아니라 복사 도중 최종 경로에 반쪽 번들을
#   노출한다 → 그 순간 실행하면 "손상되었기 때문에 열 수 없습니다". 설치 도우미가 원자 교체(숨김
#   스테이징 → 단일 rename/renamex_np)로 그 경합을 제거한다. 원자 로직은 재구현하지 않고 레포 정본
#   scripts/atomic_bundle.py 를 번들 내부에 봉인해 그대로 부른다(installer.applescript → 번들 내부
#   install-core.sh → 번들 내부 atomic_bundle.py). ★install-core 는 오직 서명·공증된 번들 내부에서만
#   실행된다(LPE 방어: DMG 형제·쓰기가능 경로 스크립트를 root 로 실행하는 경로 없음).
# 기존 app/dmg 서명·공증·staple 경로는 그대로 두고, 설치 도우미를 3번째 공증 제출로 **추가**한다.
echo "== 설치 도우미(Install cys.app) 빌드·서명·공증·staple (3번째 제출) =="
INSTALLER_WORK="$(mktemp -d)"
INSTALLER_APP="$INSTALLER_WORK/Install cys.app"
osacompile -o "$INSTALLER_APP" scripts/installer-app/installer.applescript
# CFBundleIdentifier — osacompile 기본값을 com.cysjavis.installer 로 강제(Add 실패 시 Set 폴백).
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.cysjavis.installer" "$INSTALLER_APP/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.cysjavis.installer" "$INSTALLER_APP/Contents/Info.plist"
# ★번들 내부 봉인(LPE 방어): 코어 셸 + 정본 원자 교체 파이썬을 Contents/Resources 에 복사한 뒤 서명한다
#   (복사는 반드시 codesign 前 — 서명이 이 리소스들을 봉인해야 설치 시점 변조가 불가능).
cp scripts/installer-app/install-core.sh "$INSTALLER_APP/Contents/Resources/install-core.sh"
cp scripts/atomic_bundle.py            "$INSTALLER_APP/Contents/Resources/atomic_bundle.py"
chmod 0755 "$INSTALLER_APP/Contents/Resources/install-core.sh"
# 기존 인증서만: Developer ID Application + hardened runtime + timestamp(app/dmg 와 동일 신원·옵션).
codesign --force --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$INSTALLER_APP"
echo "== 공증: 설치 도우미(zip 제출) → staple =="
INSTZIP="$INSTALLER_WORK/installer.notarize.zip"
ditto -c -k --keepParent "$INSTALLER_APP" "$INSTZIP"
xcrun notarytool submit "$INSTZIP" "${NOTARY_ARGS[@]}" --wait
xcrun stapler staple "$INSTALLER_APP"
rm -f "$INSTZIP"
# 게이트(app/dmg 게이트 동형 · hard-fail): 설치 도우미 자체 Gatekeeper + 공증 티켓.
if spctl -a -t exec -vv "$INSTALLER_APP" 2>&1 | grep -qi "accepted"; then
  echo "  ✓ 설치 도우미 spctl: accepted (다른 맥에서도 경고 없이 열림)"
else
  echo "  ✗ 설치 도우미 spctl 거부 — 공증 실패. 위 notarytool 결과 확인"; exit 1
fi
if xcrun stapler validate "$INSTALLER_APP" >/dev/null 2>&1; then
  echo "  ✓ 설치 도우미 공증 티켓 stapled"
else
  echo "  ✗ 설치 도우미 staple 검증 실패" >&2; exit 1
fi

# ── DMG 조립: 설치 도우미를 가시 항목으로, cys.app 은 숨김 .support/ 로 ──
# ★ln -s /Applications 제거: 드래그 설치 자체를 유도하지 않는다(사용자는 'Install cys.app' 만 클릭).
#   cys.app 은 .support/ 아래로 숨겨 원본으로만 쓰이게 하고, 설치 도우미가 거기서 원자 설치한다.
echo "== dedup·staple된 앱으로 UDZO DMG 생성(hdiutil — Tauri 기본 포맷과 동일) =="
DMGSTAGE="$(mktemp -d)"
mkdir -p "$DMGSTAGE/.support"
ditto "$APP"           "$DMGSTAGE/.support/cys.app"   # 원본 앱(숨김) — staple 티켓 승계(ditto)
ditto "$INSTALLER_APP" "$DMGSTAGE/Install cys.app"    # 가시 항목 = 설치 도우미
rm -rf "$INSTALLER_WORK"
mkdir -p "$(dirname "$DMG")"
hdiutil create -volname "cys" -srcfolder "$DMGSTAGE" -ov -format UDZO "$DMG"
rm -rf "$DMGSTAGE"
# DMG 자체도 Developer ID 서명 — 구 Tauri 흐름과 패리티. 서명 없으면 spctl -t open(primary-signature)
# 이 'no usable signature'로 거부한다(2026-07-04 실측). 서명은 반드시 notarytool 제출 전(CDHash 결속).
codesign --force --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$DMG"

echo "== 공증: DMG 제출 → staple =="
xcrun notarytool submit "$DMG" "${NOTARY_ARGS[@]}" --wait
xcrun stapler staple "$DMG"

echo "== 검증: Gatekeeper(spctl) + 공증 티켓(stapler) =="
if spctl -a -vv "$APP" 2>&1 | grep -qi "accepted"; then
  echo "  ✓ spctl: accepted (다른 맥에서도 경고 없이 열림 — '손상됨' 해소)"
else
  echo "  ✗ spctl 거부 — 공증 실패. 위 notarytool 결과를 확인하라"; exit 1
fi
# ★staple 검증 hard-fail 승격 (v0.13.23 백포트 · 2026-07-28) — 종전 '⚠ 경고 후 exit 0'은
#   staple 안 된 산출물이 "빌드 성공"으로 나가는 무음 통과 경로였다(품질 원칙 위배).
if xcrun stapler validate "$APP" >/dev/null 2>&1; then
  echo "  ✓ app 공증 티켓 stapled"
else
  echo "  ✗ app staple 검증 실패" >&2
  exit 1
fi
if xcrun stapler validate "$DMG" >/dev/null 2>&1; then
  echo "  ✓ DMG 공증 티켓 stapled"
else
  echo "  ✗ DMG staple 검증 실패" >&2
  exit 1
fi
# DMG 자체 Gatekeeper 게이트 — .app spctl만으론 DMG 서명 누락을 못 잡는다(2026-07-04 실측 갭).
if spctl -a -t open --context context:primary-signature -vv "$DMG" 2>&1 | grep -qi "accepted"; then
  echo "  ✓ DMG spctl: accepted (primary-signature)"
else
  echo "  ✗ DMG spctl 거부 — DMG codesign/공증 확인 필요"; exit 1
fi

echo "== 배포본 정리 + 자동업데이트 매니페스트 =="
mkdir -p dist-mac
cp "$DMG" "dist-mac/cysr-${VERSION}-macos-${DIST_ARCH}.dmg"
# 실패 가시화(2026-07-28): 종전 '>/dev/null || true'는 실패를 완전 무음 처리했다.
# CI에서는 tauri-action이 latest.json을 생성하므로 이 매니페스트는 미사용(비치명) —
# 따라서 hard-fail 대신 '보이는 경고'로 표면화한다. 로컬 수동 배포 경로에서만 확인 필요.
sh scripts/make-update-manifest.sh "$VERSION" idoforgod cys-terminal \
  || echo "  ⚠ make-update-manifest 실패(비치명 — CI는 tauri-action이 latest.json 생성. 로컬 수동 배포 시에만 조치)" >&2
echo "✓ 공증 빌드 완료: dist-mac/cysr-${VERSION}-macos-${DIST_ARCH}.dmg"
echo "  → ad-hoc 재서명·xattr 우회 불필요. gh release 발행은 오너 승인 후."
