#!/usr/bin/env bash
# build-macos-local.sh — 유료 서명 없이 **우리가 실제로 배포하는 맥 zip** 을 만드는 정본 경로
#   (2026-09-20 · TICKET=v110-mac-x64 · 오너 절대 규칙 「유료 서명 금지」의 집행 경로).
#
# ★왜 이 스크립트가 있나
#   형제 스크립트 `build-macos-signed.sh` 는 유료 Apple Developer ID 를 **fail-closed 로 요구**한다
#   (인증서가 없으면 3초 만에 exit 2). 우리는 그 길을 쓰지 않기로 했으므로, 지금까지 맥 자산은
#   사람이 그 스크립트의 비-Apple 단계를 손으로 골라 돌려 만들었다 — 손 절차는 적히지 않으면 사라진다.
#   ⇒ 그 절차를 여기 고정한다. 단계 자체는 `scripts/lib/mac-bundle-common.sh` 한 곳에 있고
#     발행 스크립트도 같은 함수를 부른다(한쪽만 고치는 날 차단).
#
# ★서명은 **cys-local 자체서명**이다(공증 없음). 그래서 설치기는 원작자 dmg 의 설치 도우미를 쓰지 않고
#   zip 을 받아 풀어 넣는다(install-master/bootstrap.sh 의 그 경로). 공증이 없어도 되는 까닭은
#   사람이 「열기」를 누르는 경로를 타지 않기 때문이다 — 설치기가 격리 속성을 지우고 서명 무결성을 본다.
#
# 쓰는 법:
#   scripts/build-macos-local.sh [aarch64|x86_64|both] [산출폴더]
#     인자 없음 = 호스트 아키텍처 1종 · 산출폴더 기본 = dist-local/
#     별칭 허용: arm64=aarch64 · x64=x86_64 · 전체 트리플(aarch64-apple-darwin 등)도 그대로 받는다
#   전제: export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/cys-updater-A2.key)" TAURI_SIGNING_PRIVATE_KEY_PASSWORD=""
#
# exit 0=성공 / 1=단계 실패 / 2=전제 미비
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
VERSION=$(grep -m1 '"version"' src-tauri/tauri.conf.json | sed -E 's/.*"([0-9][0-9.]*)".*/\1/')
TAURI_CLI_VERSION="${TAURI_CLI_VERSION:-2.11.4}"   # 발행 스크립트와 같은 핀(그 파일 머리말의 까닭 그대로)
. scripts/lib/mac-bundle-common.sh   # ★cd 뒤라 저장소 루트 기준 경로가 결정론이다

WHICH="${1:-host}"
OUTDIR="${2:-dist-local}"
SIGN_ID="${CYS_LOCAL_SIGN_IDENTITY:-cys-local}"

# ── 전제 fail-closed ─────────────────────────────────────────────────────────
# ⑴ 업데이터 서명키 — 없으면 tauri build 가 **빌드 말미에** 죽는다(createUpdaterArtifacts). 20분 뒤가 아니라 지금 죽인다.
if [ -z "${TAURI_SIGNING_PRIVATE_KEY:-}" ]; then
  echo "✗ TAURI_SIGNING_PRIVATE_KEY 미설정 — tauri build 가 updater 아티팩트 서명에서 실패한다(빌드 말미 hard-fail)." >&2
  echo '  설정: export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/cys-updater-A2.key)" TAURI_SIGNING_PRIVATE_KEY_PASSWORD=""' >&2
  exit 2
fi
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="${TAURI_SIGNING_PRIVATE_KEY_PASSWORD:-}"
# ⑵ 자체서명 신원이 Keychain 에 있는가. 없는 채로 codesign 을 부르면 「그 신원 없음」이 단계 한복판에서 난다.
security find-certificate -c "$SIGN_ID" >/dev/null 2>&1 || {
  echo "✗ Keychain 에 '$SIGN_ID' 인증서가 없다 — 자체서명을 할 수 없다." >&2
  echo "  다른 이름을 쓰려면: CYS_LOCAL_SIGN_IDENTITY=<이름> scripts/build-macos-local.sh …" >&2
  exit 2; }
# ⑶ ★이 스크립트는 Apple 자격이 **있어도** 쓰지 않는다. 유료 서명은 오너 절대 규칙으로 금지돼 있고,
#    그 길이 필요하면 build-macos-signed.sh 가 따로 있다. 여기서 조용히 갈아타지 않는다.

case "$WHICH" in
  host)   case "$(uname -m)" in arm64) TARGETS=(aarch64-apple-darwin) ;; x86_64) TARGETS=(x86_64-apple-darwin) ;;
            *) echo "unknown host arch $(uname -m)" >&2; exit 2 ;; esac ;;
  both)   TARGETS=(aarch64-apple-darwin x86_64-apple-darwin) ;;
  aarch64|arm64|aarch64-apple-darwin) TARGETS=(aarch64-apple-darwin) ;;
  x86_64|x64|intel|x86_64-apple-darwin) TARGETS=(x86_64-apple-darwin) ;;
  *) echo "모르는 대상: $WHICH (aarch64|x86_64|both)" >&2; exit 2 ;;
esac

mkdir -p "$OUTDIR"
OUTDIR="$(cd "$OUTDIR" && pwd)"
ROWS=()

for T in "${TARGETS[@]}"; do
  echo
  echo "════ $T ════"
  # ⚠두 아키텍처를 이어서 만들 때 순서가 중요하다: mac_prep_runtime 은 src-tauri/runtime 을 **지우고 다시 받는다**.
  #   그래서 한 타깃을 끝까지 묶은 뒤 다음 타깃으로 간다(동시에 돌리면 런타임이 섞인다).
  mac_resolve_target "$T"
  mac_prep_runtime
  mac_precompile_python
  mac_build_app_bundle
  mac_assert_pyc_imported
  mac_dedup_and_restore
  mac_emit_runtime_manifest

  # ── 자체서명(cys-local) ──
  #   발행 경로는 --deep 를 금지한다(entitlement 오염). 여기는 entitlements 를 쓰지 않는 ad-hoc 성격의
  #   자체서명이고, 운영계약(CYS-UPDATE-POLICY §업데이트 경로 ③)이 `codesign --force --deep --sign cys-local`
  #   을 정본으로 적고 있다 — 발행된 자산의 CDHash 핀이 그 형태로 만들어졌으므로 형태를 바꾸지 않는다.
  echo "== 자체서명($SIGN_ID · 공증 없음) =="
  codesign --force --deep --sign "$SIGN_ID" "$APP"
  codesign --verify --deep --strict "$APP" || { echo "  ✗ 자체서명 검증 실패" >&2; exit 1; }
  echo "  ✓ codesign --verify --deep --strict 통과"

  # ── 배포 zip (설치기가 받는 바로 그 형태) ──
  #   ★ditto -c -k --keepParent — 심볼릭링크·확장속성·서명을 보존한다. zip(1) 로 묶으면 dedup 링크가
  #     실복사본이 되거나 서명이 깨진다(설치기는 푼 뒤 codesign --verify 를 한다).
  ZIP="$OUTDIR/cysr-macos-${DIST_ARCH}-v${VERSION}.zip"
  rm -f "$ZIP"
  ditto -c -k --keepParent "$APP" "$ZIP"
  BYTES="$(wc -c < "$ZIP" | tr -d ' ')"
  SHA="$(shasum -a 256 "$ZIP" | awk '{print $1}')"
  CDH="$(codesign -dvvv "$APP" 2>&1 | awk -F= '/^CDHash=/{print $2}')"
  [ -n "$CDH" ] || { echo "  ✗ CDHash 를 못 쟀다 — 핀을 채울 수 없다(측정 불능은 통과가 아니다)" >&2; exit 1; }
  ROWS+=("$(basename "$ZIP")|$BYTES|$SHA|$CDH")
done

# ── 핀 표 (설치기 install-master/bootstrap.sh 의 CYS_FORK_* / CYS_FORK_X64_* 를 이 값으로 채운다) ──
echo
echo "════ 산출 · 핀 값 ════  (폴더: $OUTDIR)"
printf '%-34s %14s  %-64s %s\n' "파일" "크기(B)" "sha256" "CDHash"
for r in "${ROWS[@]}"; do
  IFS='|' read -r f b s c <<< "$r"
  printf '%-34s %14s  %-64s %s\n' "$f" "$b" "$s" "$c"
done
echo
echo "⚠발행(릴리스 업로드)·핀 값 확정은 이 스크립트가 하지 않는다 — 오너/마스터 게이트다."
