#!/usr/bin/env bash
# phoenix-host-gate.sh — phoenix host-level 파이썬 게이트의 **한 정의**(TICKET=cysr-1113-release · 1.1.14).
#
# ★왜 스크립트인가: 이 게이트는 release.yml 「phoenix host-level 로직 게이트 (macOS 네이티브)」 스텝과
#   ci-branch.yml `phoenix-host-gate` 잡 두 곳에서 돈다. 두 블록을 문면으로 맞춰 두던 동안(1.1.13) 한쪽에만
#   있던 줄이 태그 런에서야 드러나 판번을 셋 소각했다(v1.1.11 TMPDIR 별칭 · v1.1.12 하네스 소켓 길이 ·
#   v1.1.13 정규화 TMPDIR 이 같은 스텝의 cargo 시험까지 걸려 SUN_LEN). 두 워크플로는 이제 이 파일만 부른다.
#   레인 대조 = scripts/tests/test_phoenix_host_gate_lane.py.
#
# ★정규화 TMPDIR 은 파이썬 phoenix 루프의 서브셸 안에만 건다: macOS 러너 TMPDIR 는 /var/…(= /private/var
#   별칭)이라 하네스가 aliased_harness_root 로 거부한다(javis_phoenix_harness.py · 하네스 홈 = tempfile.mkdtemp).
#   정규 경로는 8바이트 길어 유닉스 소켓 상한(104)에 붙는 시험을 깬다(v1.1.13 태그 런 42160662015 ·
#   src/bin/cys.rs 시험 3건) — 그래서 이 스크립트를 부른 쪽의 TMPDIR 은 바꾸지 않는다(서브셸 밖으로 새지 않는다).
#
# ★cargo 시험(cysd·lib·cys)은 여기 넣지 않는다: scripts/tests/test_c8_ci_consumer.py 의 재고 계약이 워크플로
#   run 본문의 cysd 실행을 직접 세고(「cargo started by a script … audit by hand」), release 스텝의 cysd 로그를
#   C8 표식 게이트가 읽는다. 그 줄들은 release.yml 에 그대로 둔다.
#
# 쓰는 법(저장소 뿌리에서): bash scripts/ci/phoenix-host-gate.sh cysjavis-pack/bin/tests/test_phoenix_*.py
#   인자 = 돌릴 시험 파일들. 글롭은 **부르는 쪽 워크플로 본문에** 둔다 — 레인 대조 스캐너
#   (scripts/lane-parity-rehearsal.sh · ci-branch.yml 레인 게이트)가 워크플로 문면에서 `test_phoenix_` 토큰을 읽는다.
# 종료: 0 = 전건 녹 · 시험 하나라도 실패 = 그 시험의 종료 코드 · 2 = 인자 없음/파일 없음(빈 루프 = 거짓 초록 차단).
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "::error::phoenix-host-gate.sh: 돌릴 시험 파일 인자가 없다(빈 루프 = 거짓 초록)" >&2
  exit 2
fi
for t in "$@"; do
  [ -f "$t" ] || { echo "::error::phoenix-host-gate.sh: 시험 파일이 없다: $t (글롭이 아무것에도 안 걸렸거나 경로 오류)" >&2; exit 2; }
done

# 정규 TMPDIR — 값만 계산한다(export 는 아래 서브셸 안에서만).
NORM_TMPDIR="$(cd "${TMPDIR:-/tmp}" && pwd -P)"
# ★v116-flake-pty ⑶: 팩 임시 폴더를 한 루트 아래 모으고 어떻게 끝나든 지운다.
#   macOS `mktemp -d`(템플릿 없음)는 TMPDIR 를 무시하고 사용자 임시 폴더에 tmp.* 를 남긴다 —
#   로컬 gate_runner 재실행마다 잔재가 쌓였다. trap 은 실패하지 않는다(set -e 아래 rm 실패가
#   초록을 붉히지 않게 · 정리 실패는 경고 1줄). 루트 = 종전 스텝과 같은 값(RUNNER_TEMP 우선 · 없으면 정규 TMPDIR).
CYS_TMP="$(mktemp -d "${RUNNER_TEMP:-$NORM_TMPDIR}/cys-pack.XXXXXX")"
# ★정리는 rc 를 바꾸지 않는다(codex 1R major): 진입 rc 를 먼저 잡고 set -e 를 끈 채 지운 뒤 그 rc 로 끝낸다 —
#   종전 trap 은 chmod 실패가 set -e 를 당겨 재시도·경고를 건너뛰고 시험 rc(0·7 …)를 덮어썼다.
cleanup() {
  local rc=$?
  set +e
  rm -rf "${CYS_TMP:?}" 2>/dev/null || { chmod -R u+w "${CYS_TMP:?}" 2>/dev/null; rm -rf "${CYS_TMP:?}" 2>/dev/null || echo "::warning::임시 팩 폴더 정리 실패: ${CYS_TMP}"; }
  exit "$rc"
}
trap cleanup EXIT

cargo build --bin cys --bin cysd
export PHOENIX_HARNESS_CYSD="$PWD/target/debug/cysd"
export PATH="$PWD/target/debug:$PATH"
export PHOENIX_CYS="$PWD/target/debug/cys"

# ★커밋된 phoenix 시험 전건(부르는 쪽 글롭) — 하드코딩 목록은 새 웨이브 시험을 조용히 빠뜨린다.
(
  export TMPDIR="$NORM_TMPDIR"
  for t in "$@"; do
    echo "== phoenix test: $(basename "$t") =="
    # ★할당을 따로 둔다(codex 1R major): `CYS_PACK_DIR="$(mktemp …)" python3` 꼴은 python3 의 rc 만 남겨
    #   mktemp 실패가 빈 CYS_PACK_DIR 로 시험을 돌리고도 초록이 됐다 — 이제 set -e 가 그 자리에서 끊는다.
    pack_dir="$(mktemp -d "$CYS_TMP/p.XXXXXX")"
    CYS_PACK_DIR="$pack_dir" python3 "$t"
  done
)
