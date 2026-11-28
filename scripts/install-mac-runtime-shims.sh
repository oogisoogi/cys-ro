#!/usr/bin/env bash
# install-mac-runtime-shims.sh — 동봉 런타임 트리에 cys 자체 감싸개를 깐다(1.1.21 A · 멱등).
# 지금 까는 것: runtime/git/cysbin/git = scripts/mac-runtime/git-wrapper.sh(0755).
#   동봉 dugite git 은 --exec-path 가 빌드 접두(//libexec/git-core)로 박혀 있어 부르는 쪽이 GIT_EXEC_PATH 를
#   주지 않으면 https·init 템플릿을 못 찾는다 — 감싸개가 자기 자리 기준으로 세운다. bin/git(Mach-O)은 그대로
#   둔다(check_macho_arch·업데이터 tarball 의 --require runtime/git/bin/git 단언 · dedup 기준점 무접촉).
#   PATH 에는 runtime_bin_dirs(src/lib.rs)가 git/cysbin 을 git/bin 앞에 더한다.
# 부르는 곳: prep-mac-runtime.sh 끝(CI·로컬 첫 준비) + mac-bundle-common.sh mac_prep_runtime(준비를 건너뛰는
#   로컬 재빌드에도 실리게 — 건너뛰기 조건 밖에서 매번).
# 사용: scripts/install-mac-runtime-shims.sh <runtime-dir(기본 src-tauri/runtime)>
set -euo pipefail
RT="${1:-src-tauri/runtime}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/mac-runtime/git-wrapper.sh"
[ -f "$SRC" ] || { echo "✗ 감싸개 원본 없음: $SRC" >&2; exit 2; }
[ -d "$RT/git/libexec/git-core" ] || { echo "✗ 동봉 git 트리 없음: $RT/git/libexec/git-core" >&2; exit 2; }
mkdir -p "$RT/git/cysbin"
install -m 0755 "$SRC" "$RT/git/cysbin/git"
echo "✓ 동봉 git 감싸개 → $RT/git/cysbin/git"
