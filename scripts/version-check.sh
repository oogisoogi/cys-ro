#!/bin/sh
# version-check.sh — 버전 SOT 8곳 일치 검증 (드리프트 차단)
#
# 왜: 릴리스 버전이 **8곳(수동 6 + Cargo.lock 2패키지)**에 흩어져 있다(docs/RELEASE.md §0).
#     그중 수동 동기화 대상은 Cargo/tauri/ui/wxs 6곳이고, Cargo.lock 2패키지는 cargo 재생성물이다.
#     0.4.0→0.4.1 범프에서 wxs 2곳이 누락돼 드리프트가 발생한 적이 있다.
#     이 가드를 release.yml build job 첫 step + 로컬 preflight로 걸면 불일치 시 빌드/발행이 차단된다.
#
# ★S23 Cargo.lock 포획 비대칭 교정(2026-07-26). 종전 이 스크립트는 Cargo.lock 을 **전혀 보지
#   않았고**, 리포 전체에서 lock 드리프트를 잡는 유일한 지점은 release.yml 의
#   `cargo build --locked -p cys-browserd` 하나였다. 그 포획은 비대칭이다 —
#     · aarch64 레그: 앞선 unlocked 빌드(`cargo build --bin cys --bin cysd`)가 lock 을 **재생성**해
#       드리프트를 자가치유·은폐한다 → 초록.
#     · x64·Windows 레그: 같은 커밋인데 **20분 뒤** `--locked` 에서 즉사하고, 로그는
#       "브라우저 런타임 스테이징 실패"로 읽혀 원인(버전 범프 후 lock 미갱신)이 드러나지 않는다.
#   Cargo.lock 은 손편집 대상이 아니라 **생성물**이지만, 범프 커밋에 함께 담기지 않으면 위 경로로
#   릴리스가 늦고 애매하게 죽는다. 그래서 여기서 **즉시·명확하게** 잡는다(CI 20분 뒤 오진 대체).
#   ⚠한계: 이건 lock 의 **버전 필드 2개**만 본다. 의존 그래프 전체의 최신성은 `--locked` 빌드만이
#   증명한다 — 이 스크립트가 그 역할을 대신하지 않는다.
#
# 사용:
#   sh scripts/version-check.sh            # 8곳 상호 일치만 검사
#   sh scripts/version-check.sh v0.4.1     # 그 값(태그)과도 일치 검사 (발행 직전 단언)
#
# 종료코드: 0=일치, 1=불일치(또는 추출 실패)
set -eu
cd "$(dirname "$0")/.."

row() { printf '  %-30s %s\n' "$1" "$2"; }

# Cargo.lock 에서 특정 워크스페이스 패키지의 version 값을 뽑는다. `[[package]]` 블록은
# `name = "…"` 다음 줄이 `version = "…"` 이므로 name 매치 후 첫 version 필드를 취한다.
# 추출 실패(빈 문자열)는 아래 NUNIQ 비교에서 자동으로 불일치로 떨어진다(fail-closed).
lockver() {
  awk -v pkg="$1" '
    $0 == "name = \"" pkg "\"" { f = 1; next }
    f && $1 == "version" { gsub(/[",]/, "", $3); print $3; exit }
  ' Cargo.lock
}

V_CARGO=$(grep -m1 '^version'   Cargo.toml                  | sed -E 's/.*"([^"]+)".*/\1/')
V_TCARGO=$(grep -m1 '^version'  src-tauri/Cargo.toml        | sed -E 's/.*"([^"]+)".*/\1/')
V_CONF=$(grep -m1 '"version"'   src-tauri/tauri.conf.json   | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
V_PKG=$(grep -m1 '"version"'    ui/package.json             | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
V_WXS=$(grep -m1 'Product'      dist-win/cys.wxs            | sed -E 's/.*Version="([^"]+)".*/\1/')
V_WXS64=$(grep -m1 'Product'    dist-win/cys-x64.wxs        | sed -E 's/.*Version="([^"]+)".*/\1/')
V_LOCK_ROOT=$(lockver 'cys-terminal')
V_LOCK_APP=$(lockver 'cys-app')

echo "버전 SOT 8곳:"
row "Cargo.toml"                "$V_CARGO"
row "src-tauri/Cargo.toml"      "$V_TCARGO"
row "src-tauri/tauri.conf.json" "$V_CONF"
row "ui/package.json"           "$V_PKG"
row "dist-win/cys.wxs"          "$V_WXS"
row "dist-win/cys-x64.wxs"      "$V_WXS64"
row "Cargo.lock [cys-terminal]" "${V_LOCK_ROOT:-<추출 실패>}"
row "Cargo.lock [cys-app]"      "${V_LOCK_APP:-<추출 실패>}"
echo ""

NUNIQ=$(printf '%s\n' "$V_CARGO" "$V_TCARGO" "$V_CONF" "$V_PKG" "$V_WXS" "$V_WXS64" \
                      "$V_LOCK_ROOT" "$V_LOCK_APP" | sort -u | wc -l | tr -d ' ')
UNIQ=$(printf '%s\n' "$V_CARGO" "$V_TCARGO" "$V_CONF" "$V_PKG" "$V_WXS" "$V_WXS64" \
                     "$V_LOCK_ROOT" "$V_LOCK_APP" | sort -u | tr '\n' ' ')

rc=0
if [ "$NUNIQ" != "1" ]; then
  echo "❌ 버전 불일치 — 8곳이 갈렸다: [ $UNIQ]"
  # Cargo.lock 만 갈렸으면 원인은 거의 항상 "범프 후 lock 미재생성"이다. 손편집 금지 —
  # cargo 가 다시 쓰게 하고 그 결과를 범프 커밋에 함께 담아야 한다(S23).
  if [ "$V_LOCK_ROOT" != "$V_CARGO" ] || [ "$V_LOCK_APP" != "$V_TCARGO" ]; then
    echo "   ↳ Cargo.lock 드리프트 — 손으로 고치지 말고 재생성해 커밋하라:"
    echo "     cargo update -w -p cys-terminal -p cys-app   (또는 cargo build 후 lock 커밋)"
    echo "   ↳ 이걸 방치하면 x64·Windows 레그가 20분 뒤 --locked 에서 죽고 로그가 원인을 감춘다."
  fi
  rc=1
else
  echo "✅ 8곳 일치: $V_CARGO"
fi

# 발행 직전 단언: 태그(vX.Y.Z)와 소스 버전이 같은지
if [ "${1:-}" != "" ]; then
  EXPECT="${1#v}"
  if [ "$NUNIQ" != "1" ] || [ "$V_CARGO" != "$EXPECT" ]; then
    if [ "$V_CARGO" != "$EXPECT" ]; then
      echo "❌ 기대 버전($EXPECT)과 불일치 (소스=$V_CARGO)"
    else
      # Cargo.toml 은 태그와 맞지만 다른 SOT가 갈렸다. 종전엔 여기서도 "기대 버전과 불일치
      # (소스=$V_CARGO)"를 찍어 **같은 두 값을 나란히 보여주는** 모순 메시지가 나왔다(실측).
      echo "❌ 태그 단언 보류 — Cargo.toml 은 $EXPECT 로 맞으나 위 SOT 불일치가 먼저 해소돼야 한다"
    fi
    rc=1
  else
    echo "✅ 기대 버전 일치: $EXPECT"
  fi
fi

# ★벤더 태그 동명 충돌 검사 (2026-09-12 · TICKET=cys-v01436-pack-url)
#   왜: 벤더(idoforgod/cys-terminal)와 우리 포크가 같은 번호 계열을 쓴다. 실측(2026-09-12
#   git ls-remote): 벤더 v0.14.31~35 가 우리 태그와 **같은 이름·다른 커밋**이다(우리 v0.14.33 =
#   6faabbb ↔ 벤더 7879421). 같은 이름의 두 판이 돌면 "v0.14.33 을 설치했다"가 어느 판인지
#   말해 주지 못한다. 그래서 태그를 단언하는 발행 직전 경로에서, 벤더에 같은 이름이 이미 있으면
#   막는다.
#   · 태그 인자가 있을 때만 돈다(인자 없는 상호 일치 검사는 네트워크를 쓰지 않는다).
#   · 조회 불가(오프라인·원격 오류)는 **통과가 아니라 실패**다 — 충돌 여부를 모르는 채 발행하지 않는다.
#   · CYS_VENDOR_TAGS_REMOTE 는 시험용 원격 치환 자리다(test_version_sot_mutation.py 가 로컬
#     저장소를 넣어 네트워크 없이 3상태를 재현한다). 릴리스 워크플로는 이 변수를 주지 않는다.
if [ "${1:-}" != "" ]; then
  VTAG="v${1#v}"
  VENDOR_TAGS_REMOTE="${CYS_VENDOR_TAGS_REMOTE:-https://github.com/idoforgod/cys-terminal.git}"
  if VOUT=$(GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=30 \
              ls-remote --tags "$VENDOR_TAGS_REMOTE" 2>&1); then
    # 정확 일치만 센다 — ls-remote 패턴은 꼬리 일치라 refs/tags/x/v0.14.36 까지 잡는다.
    # 경량 태그는 ref 1줄, 주석 태그는 ref + ^{} 2줄로 나온다(둘 다 충돌이다).
    VHIT=$(printf '%s\n' "$VOUT" | awk -v t="refs/tags/$VTAG" '$2 == t || $2 == t "^{}"' | wc -l | tr -d ' ')
    if [ "$VHIT" != "0" ]; then
      echo "❌ 벤더 태그 동명 충돌 — $VTAG 가 벤더 원격에 이미 있다($VENDOR_TAGS_REMOTE)."
      echo "   ↳ 같은 이름·다른 커밋의 판이 둘이 된다. 번호를 올려 벤더에 없는 태그로 발행하라."
      rc=1
    else
      echo "✅ 벤더 태그 동명 충돌 없음: $VTAG (조회 원격 $VENDOR_TAGS_REMOTE)"
    fi
  else
    echo "❌ 벤더 태그 조회 불가 — 충돌 여부를 판정할 수 없어 실패로 처리한다($VENDOR_TAGS_REMOTE)."
    printf '%s\n' "$VOUT" | sed '/^[[:space:]]*$/d' | tail -3 | sed 's/^/   ↳ /'
    rc=1
  fi
fi

exit $rc
