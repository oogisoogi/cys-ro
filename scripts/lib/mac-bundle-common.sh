#!/usr/bin/env bash
# mac-bundle-common.sh — macOS 앱 번들을 만드는 **비-Apple 단계**의 단일 출처 (2026-09-20 · TICKET=v110-mac-x64).
#
# ★왜 파일을 갈랐나
#   같은 단계가 두 스크립트에 필요해졌다: `build-macos-signed.sh`(유료 Developer ID + 공증 · 발행용)와
#   `build-macos-local.sh`(자체서명 cys-local · 우리 실제 배포 zip 을 만드는 정본 경로).
#   ⛔복사해 두 벌로 두면 **한쪽만 고치는 날**이 온다 — 이 저장소가 그 형태로 이미 여러 번 데였다
#     (dedup·링크복원 로직을 CI 와 공유 스크립트로 통일한 것과 같은 까닭).
#   ⇒ 갈리면 안 되는 것은 **함수로 한 곳에** 두고 양쪽이 source 한다.
#
# ★이 파일에 있는 것 = 서명·공증과 **무관한** 단계뿐이다:
#   타깃 해석 · 런타임 준비 · 선컴파일 · 앱 번들 빌드 · SEAL-2 반입 검사 · dedup/링크복원 · runtime-manifest.
#   서명(Developer ID inside-out 재서명 · 공증 · staple · DMG 조립)은 발행 스크립트에만 남는다.
#   자체서명(cys-local)은 로컬 스크립트에만 남는다. **서명 정책이 두 갈래라는 사실 자체가 경계선**이다.
#
# 쓰는 법: 저장소 루트에서 `. scripts/lib/mac-bundle-common.sh` 한 뒤 함수를 순서대로 부른다.
#   사전 전제(부르는 쪽 책임): `set -euo pipefail` · cwd = 저장소 루트 · VERSION · TAURI_CLI_VERSION.
#   ⚠source 시점에는 **아무 부작용도 없다**(함수 정의만) — 부르는 쪽이 순서를 통제한다.

# 타깃을 해석해 TARGET·DMG_ARCH·DIST_ARCH·BUNDLE_BASE·TAURI_TARGET_ARGS 를 세운다(크로스면 CYS_TARGET export).
mac_resolve_target() {
  # ── 타깃 아키텍처(무인자=호스트 네이티브 — arm64 경로 완전 불변) ──
  # 사용: scripts/build-macos-signed.sh [aarch64-apple-darwin|x86_64-apple-darwin]
  # arm64 호스트에서 x86_64를 넘기면 크로스빌드 — prep-mac-runtime.sh 도 같은 타깃으로 런타임을 교체한다.
  TARGET="${1:-}"
  if [ -z "$TARGET" ]; then
    case "$(uname -m)" in
      arm64)  TARGET=aarch64-apple-darwin ;;
      x86_64) TARGET=x86_64-apple-darwin ;;
      *) echo "unknown host arch $(uname -m)"; exit 2 ;;
    esac
  fi
  case "$TARGET" in
    aarch64-apple-darwin) DMG_ARCH=aarch64; DIST_ARCH=arm64 ;;   # Tauri DMG 명명 규칙과 일치
    x86_64-apple-darwin)  DMG_ARCH=x64;     DIST_ARCH=x64   ;;
    *) echo "지원하지 않는 타깃: $TARGET (aarch64-apple-darwin|x86_64-apple-darwin)"; exit 2 ;;
  esac
  # 호스트와 타깃이 다르면(크로스빌드) tauri build 에 --target 을 전달하고 산출물 경로에 타깃 세그먼트가 낀다.
  HOST_ARCH_TARGET=$([ "$(uname -m)" = "arm64" ] && echo aarch64-apple-darwin || echo x86_64-apple-darwin)
  if [ "$TARGET" != "$HOST_ARCH_TARGET" ]; then
    TAURI_TARGET_ARGS=(--target "$TARGET"); BUNDLE_BASE="target/$TARGET/release/bundle"
    # 크로스 빌드: bundle-prep.sh(beforeBuildCommand)가 사이드카 cys/cysd를 이 타깃으로
    # 크로스 빌드하도록 CYS_TARGET 전파 — 없으면 host(arm64) 사이드카가 실려 x64 앱이 깨진다.
    export CYS_TARGET="$TARGET"
  else
    TAURI_TARGET_ARGS=(); BUNDLE_BASE="target/release/bundle"
  fi
  echo "== 대상 아키텍처: $TARGET (DMG=$DMG_ARCH · bundle=$BUNDLE_BASE) =="
}

# 동봉 런타임(python·git·uv·node)을 이 타깃으로 준비한다. 이미 같은 타깃이면 건너뛴다(.prep-target 마커).
mac_prep_runtime() {
  # ── 동봉 런타임 준비 + inside-out 재서명 (RC-22/T6b — 공증 필수) ──
  # tauri.conf.json bundle.resources("runtime/")는 Contents/Resources/runtime 으로 실리지만 Tauri는
  # resources 내 Mach-O를 자동 서명하지 않는다(#12001) → ad-hoc(python·uv)/타팀(node) 서명 그대로면
  # 공증이 "signature invalid / hardened runtime 미적용"으로 거부. tauri build **전에** 개별 재서명해
  # .app 안으로 Developer ID 서명본이 실리게 한다. ★codesign --deep 금지(entitlement 오염·실행 차단) —
  # inside-out(라이브러리 먼저·실행 바이너리 나중) 개별 서명. 인터프리터(python/node JIT)는 entitlements 적용.
  # 런타임이 대상 타깃과 다른 아키텍처면(직전 빌드가 다른 arch) 강제 재준비 — arch 혼입 방지.
  # .prep-target 마커로 현재 런타임 아키텍처를 추적한다(없으면 안전측 재준비).
  RT_MARKER="src-tauri/runtime/.prep-target"
  RT_CUR="$(cat "$RT_MARKER" 2>/dev/null || echo '')"
  if [ ! -x "src-tauri/runtime/python/bin/python3" ] || [ "$RT_CUR" != "$TARGET" ]; then
    echo "== 동봉 런타임 준비($TARGET) =="
    bash scripts/prep-mac-runtime.sh "$TARGET"
    printf '%s' "$TARGET" > "$RT_MARKER"
  fi
}

# 동봉 python 선컴파일(SEAL-2) — 조건 없이 매 빌드.
mac_precompile_python() {
  # ── SEAL-2: 동봉 python 선컴파일 (★조건 없이 매 빌드 · 서명 직전) ──
  # prep-mac-runtime.sh 안에도 같은 호출이 있지만, 위 블록은 `.prep-target` 이 맞으면 prep 자체를
  # **건너뛴다** — 이 변경 이전에 만들어진(=`.pyc` 없는) 런타임 트리가 남아 있으면 그 조용한 경로로
  # 봉인이 깨진 앱이 나간다. 그래서 여기서 무조건 한 번 더 돈다(이미 컴파일돼 있으면 동일 결과를
  # 다시 쓰고 검증만 통과 — 실측 ~1.2초). 스크립트가 커버리지 100% + 전량 unchecked-hash 를
  # fail-closed 로 검증하므로, 통과하면 "이 트리에는 런타임에 새로 쓸 `.pyc` 가 없다"가 보장된다.
  # ★반드시 `tauri build` **전**에 = `.app` 밖에서 돌아야 한다: `.app` 안 바이너리를 exec 하면
  #   macOS 가 앱 번들 보호를 걸어 python 이 SIGKILL 되고 codesign 이 "Operation not permitted"가
  #   된다(2026-08-01 실측). 자세한 근거는 precompile-bundled-python.sh 머리 주석.
  bash scripts/precompile-bundled-python.sh src-tauri/runtime
}

# 앱 번들 빌드(--bundles app) 후 APP·DMG 경로를 세운다.
#   ⚠Apple 자격 env 를 벗겨 부르는 것은 **공증을 뒤로 미루기 위한 발행 경로의 장치**인데, 로컬(자체서명)
#     경로에서도 무해하다(그 env 가 아예 없다) — 그래서 한 함수로 둔다.
mac_build_app_bundle() {
  # ── 앱 번들 빌드 (서명만 · 공증은 dedup 뒤로 1회 미룸) — RC-23 git-core dedup ──
  # ★Tauri 번들러는 bundle.resources 디렉토리의 심볼릭링크를 역참조(dereference)한다(upstream #13219, 미해결).
  #   dugite tar.gz는 libexec/git-core 빌트인 143개를 이미 `git` 심볼릭링크로 dedup(트리 141MB)하나, Tauri가
  #   .app으로 복사하며 각 링크를 3.4MB 실복사본으로 부풀려 runtime/git 608MB(중복 464MB)·DMG 434MB가 된다.
  #   → prep-mac-runtime.sh 단계 dedup은 무효(복사 시 재역참조). '.app 생성 후·서명 전' dedup만 유효하다(실측).
  #   Tauri에 서명 신원만 주고 공증 자격은 감춰 '서명만' 시킨다(dedup이 서명 봉인을 깨므로 공증은 1회로 미룸).
  #   fat DMG도 건너뛴다(--bundles app) — DMG는 dedup된 .app에서 hdiutil로 만든다
  #   (`tauri build --bundles dmg`는 .app을 재빌드해 역참조를 되돌리므로 사용 불가 — 실측 확인).
  echo "== 앱 번들 빌드(서명만·공증 보류) v$VERSION =="
  env -u APPLE_ID -u APPLE_PASSWORD -u APPLE_TEAM_ID -u APPLE_API_KEY -u APPLE_API_ISSUER \
    bun x "@tauri-apps/cli@${TAURI_CLI_VERSION}" build ${TAURI_TARGET_ARGS[@]+"${TAURI_TARGET_ARGS[@]}"} --bundles app

  APP="$BUNDLE_BASE/macos/cysr.app"
  DMG="$BUNDLE_BASE/dmg/cysr_${VERSION}_${DMG_ARCH}.dmg"
}

# 선컴파일 산출물이 .app 안에 그대로 실렸는가(fail-closed) — SRC_PYC 를 세운다(뒤 무회귀 검사가 쓴다).
mac_assert_pyc_imported() {
  # ── SEAL-2 반입 확인: 선컴파일 산출물이 실제로 .app 안에 실렸는가 (fail-closed) ──
  # Tauri 번들러가 `__pycache__` 를 빠뜨리면 선컴파일을 해도 봉인엔 안 들어가고, 사용자 머신에서
  # 그대로 새로 쓰이며 봉인이 깨진다 — 서명·공증에 20분 쓰기 **전에** 여기서 잡는다.
  # 개수가 어긋나면(누락·중복 복사) 원인을 규명하기 전엔 진행 금지.
  # ★`set -euo pipefail` 하에서 find 가 0이 아닌 코드를 내면 대입 자체가 스크립트를 조용히 죽인다
  # (경로 부재·권한). 그러면 아래 명시적 실패 메시지가 안 나온다 → find 실패를 삼키고 개수만 센다.
  # ★개수의 의미 (2026-08-01 opt 레벨 봉합 이후): `*.pyc` 는 최적화 레벨별로 **별개 파일**이라
  #   선컴파일 산출물은 `.py` 1개당 3개(opt-0 무태그 + `.opt-1` + `.opt-2`)다. 이 대조는 태그를
  #   가리지 않는 **총량 동일성**만 보므로 레벨이 늘어도 그대로 정합한다 — 실측(python+node 트리):
  #   opt-0 전용 1140/1140 PASS · 3종 3420/3420 PASS(옮겨진 뒤에도 opt-1 1140·opt-2 1140 보존).
  #   레벨별 커버리지 자체는 precompile-bundled-python.sh 의 fail-closed 검증부가 이미 보증한다.
  SRC_PYC=$({ find src-tauri/runtime -name '*.pyc' 2>/dev/null || true; } | wc -l | tr -d ' ')
  APP_PYC=$({ find "$APP/Contents/Resources/runtime" -name '*.pyc' 2>/dev/null || true; } | wc -l | tr -d ' ')
  if [ "$SRC_PYC" -gt 0 ] && [ "$APP_PYC" = "$SRC_PYC" ]; then
    echo "  ✓ 선컴파일 .pyc ${APP_PYC}개가 .app 에 그대로 반입됨 (봉인 대상)"
  else
    echo "  ✗ 선컴파일 .pyc 반입 불일치: runtime 트리 ${SRC_PYC}개 vs .app ${APP_PYC}개" >&2
    echo "    → 이대로 서명하면 사용자 머신에서 .pyc 가 새로 쓰여 봉인이 깨진다(2026-08-01 사고 재발)." >&2
    exit 1
  fi
}

# git-core dedup + 역참조 심볼릭링크 복원 + SEAL-2 무회귀 재확인.
mac_dedup_and_restore() {
  # ── git-core 빌트인 dedup (Tauri 역참조 되돌리기) — 공유 스크립트로 통일 ──
  # 로직·기준점(libexec/git-core/git)·자기제외·동일디렉토리 링크·잔존 중복본 가드는
  # scripts/dedup-git-core.sh 단일 출처(.github/workflows/release.yml CI 경로와 공유 — 드리프트 방지).
  echo "== runtime/git dedup (git-core 빌트인 → 동일 디렉토리 git 심볼릭링크) =="
  bash scripts/dedup-git-core.sh "$APP"

  # ── 잔여 역참조 심볼릭링크 전량 복원 (같은 upstream #13219 결함의 나머지 피해 부위) ──
  # ★위 dedup은 "git-core/git 과 바이트동일"인 142개만 되돌린다. 소스 트리의 심볼릭링크는 157개이고,
  #   나머지 15개는 그 기준에 안 걸려 **실복사본인 채로 출하돼 왔다**(회귀 아님 — 0.13.18·0.14.9 동일 파손).
  #   그중 node/bin/{npm,npx,corepack} 은 용량이 아니라 **기능 파손**이다: 링크 대신 런처 스크립트가
  #   bin/ 에 복사되는 바람에 내부 `require('../lib/cli.js')` 가 realpath 가 아닌 복사 위치 기준으로 풀려
  #   MODULE_NOT_FOUND 로 죽는다 → src/lib.rs:197·:827 이 PATH 에 얹는 앱 안의 모든 npm/npx 호출 불능.
  #   ★반드시 이 자리(=.app 생성 후 · 아래 재봉인 전)여야 한다 — 서명 전이어야 복원된 링크가 봉인에
  #   포함되고, 서명 뒤에 손대면 봉인이 깨져 Gatekeeper 가 앱을 차단한다(dedup 과 완전히 같은 이유).
  #   dedup 뒤에 두는 이유: dedup 이 자기 잔존-중복 가드를 원래 트리 상태에서 판정하게 두고, 이 단계는
  #   그 위에서 '소스 심볼릭링크 전량 = .app 링크' 를 fail-closed 로 마무리하는 상위집합 안전망이 된다.
  #   로직·게이트·자가검증은 scripts/restore-runtime-symlinks.sh 단일 출처(CI 도 이 스크립트를 탄다).
  echo "== runtime 역참조 심볼릭링크 복원 (node/bin/npm·npx·corepack 기능 복구 포함) =="
  bash scripts/restore-runtime-symlinks.sh "$APP" src-tauri/runtime

  # SEAL-2 무회귀 재확인: 위 두 단계(dedup·링크복원)가 Resources 를 건드렸으므로, 선컴파일 `.pyc` 반입
  # 개수가 그대로인지 **서명 직전에** 다시 못박는다. 복원 대상은 소스가 심볼릭링크인 경로뿐이라 `.pyc`
  # 와 겹칠 수 없지만, 이 불변식은 사고 재발 비용이 커서(2026-08-01 "손상되었기 때문에 열 수 없습니다")
  # 값싼 재확인을 남긴다 — 여기서 줄면 봉인이 사용자 머신에서 스스로 깨진다.
  APP_PYC2=$({ find "$APP/Contents/Resources/runtime" -name '*.pyc' 2>/dev/null || true; } | wc -l | tr -d ' ')
  [ "$APP_PYC2" = "$SRC_PYC" ] || {
    echo "  ✗ dedup·링크복원 후 .pyc 개수 변동: ${SRC_PYC} → ${APP_PYC2} (봉인 무회귀 위반)" >&2; exit 1; }
  echo "  ✓ SEAL-2 무회귀: .pyc ${APP_PYC2}개 유지 (dedup·링크복원이 선컴파일 봉인을 건드리지 않음)"
}

# runtime-manifest 산출 + 자기대조. ★자리가 전부다 — dedup·복원 **뒤**, 서명 **앞**에서만 불러야 한다.
mac_emit_runtime_manifest() {
  # ── runtime-manifest 산출 (부트 v2 명세 §2-10 G5 · 티켓 C1) ─────────────────────────────
  # ★자리가 전부다. 여기는 런타임 트리가 **바이트 확정되는 유일한 창**이다:
  #   위쪽 dedup(:176)·링크복원(:190)이 Resources 를 마지막으로 바꾼 뒤이고, 아래 재봉인(:~215)
  #   전이다. 서명 뒤에 쓰면 봉인이 깨지고(Gatekeeper 차단), 그 전 어디에 써도 낡는다 —
  #   ⓐprep 시점 해시는 :117-133 의 inside-out 재서명이 Mach-O 바이트를 바꿔 무효
  #   ⓑTauri 번들러가 심볼릭링크를 역참조(upstream #13219)해 구조가 달라짐
  #   ⓒdedup·복원이 .app 안에서 157 경로를 다시 링크로 되돌림.
  #   즉 **소스 트리(src-tauri/runtime)가 아니라 .app 트리에서** 떠야 한다(2026-09-04 실측 확정).
  # ★번들 밖 python 강제: cys pane 은 동봉 runtime 을 PATH 선두에 물려 `command -v python3` 가
  #   .app 안 python 으로 해소될 수 있다. .app 안 바이너리를 한 번이라도 exec 하면 macOS 가 번들
  #   보호를 걸어 SIGKILL·codesign "Operation not permitted" 를 만든다(2026-08-01 실측 ·
  #   precompile-bundled-python.sh:45-49). release-gate-gatekeeper.sh 의 $GATE_PY 선택과 동형이다.
  SEAL_PY=""
  for cand in /usr/bin/python3 "$(command -v python3 2>/dev/null || true)"; do
    [ -n "$cand" ] && [ -x "$cand" ] || continue
    real="$(readlink -f -- "$cand" 2>/dev/null || printf '%s' "$cand")"
    case "$cand:$real" in *".app/"*) continue ;; esac
    SEAL_PY="$cand"; break
  done
  [ -n "$SEAL_PY" ] || { echo "  ✗ 번들 밖 python3 없음 — runtime-manifest 산출 불가(측정 불능은 통과가 아니다)" >&2; exit 1; }
  echo "== runtime-manifest 산출 (설치 후 변조 검출용 · 서명 대상) =="
  "$SEAL_PY" cysjavis-pack/bin/javis_runtime_seal.py emit \
    --root "$APP/Contents/Resources/runtime" \
    --out  "$APP/Contents/Resources/runtime-manifest.json" \
    --app-version "$VERSION" --source mac-app
  # 산출 직후 자기대조 — 쓰자마자 어긋나면 산출기가 고장 난 것이다(무음 통과 금지).
  "$SEAL_PY" cysjavis-pack/bin/javis_runtime_seal.py verify \
    --root "$APP/Contents/Resources/runtime" \
    --manifest "$APP/Contents/Resources/runtime-manifest.json" >/dev/null || {
    echo "  ✗ 산출 직후 runtime-manifest 자기대조 실패 — 서명 중단" >&2; exit 1; }
  echo "  ✓ runtime-manifest 자기대조 통과 (이 파일은 아래 재봉인에 포함된다)"

}
