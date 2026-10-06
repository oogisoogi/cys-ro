#!/usr/bin/env bash
# 릴리스 본문 재료 수집기(1.1.8 U3 · 설계 §6-1 · §3-7 ①) — make-release-json.py 의 기판별 입력을 **실물에서 잰다**.
#
#   collect-inputs.sh mac <asset.zip> <target> <outdir>
#       맥 자산 zip(발행할 그 바이트)을 풀어(ditto -x -k) 번들 1개 확인 → codesign -dvvv 의 CDHash(40 hex) →
#       <outdir>/cdhash-<target>.txt · 번들 안 cys build-info --json → <outdir>/build-info-<target>.json
#       (맥 자산은 master 로컬 빌드 — 설계 §4-1 · 그래서 이 모드는 master 기기에서 돈다)
#   collect-inputs.sh win <setup.exe> <outdir>            (윈 · Git Bash — release.yml 윈 레그가 부른다)
#       설치기를 빈 임시 폴더에 무인 설치(/S /D=…)해 **설치기가 실제로 놓는 바이트**를 잰다 → <outdir>/payload-windows-x64/
#       (아무것도 지우지 않는다 — 제외는 make-release-json 이 scripts/update/payload-exclude.txt 명시 규칙으로만 · 실패 기록
#       cys-install-failure.txt 가 있으면 설치 실패이므로 중단) · 설치된 cys.exe build-info --json → <outdir>/build-info-windows-x64.json
#       ⚠러너 첫 실측 전(이 기계엔 윈 실행 기층이 없다) — 첫 발행 리허설이 계수·동작을 확정한다(HANDOFF-U3 §4).
# 종료: 0 = 재료 생성 · 2 = 거부(재료 0 — 본문 생성기가 그 행을 만들지 못해 발행이 멈춘다 = fail-closed).
set -euo pipefail
die() { echo "collect-inputs: $*" >&2; exit 2; }
mode="${1:-}"
case "$mode" in
  mac)
    zip="${2:-}" target="${3:-}" out="${4:-}"
    [ -f "$zip" ] && [ -n "$target" ] && [ -n "$out" ] || die "사용: mac <asset.zip> <target> <outdir>"
    case "$target" in macos-arm64|macos-x64) ;; *) die "맥 target 값: $target" ;; esac
    mkdir -p "$out"
    st="$(mktemp -d)"
    trap 'rm -rf "$st"' EXIT
    ditto -x -k "$zip" "$st" || die "zip 풀기 실패: $zip"
    apps=()
    for a in "$st"/*.app; do if [ -d "$a" ]; then apps+=("$a"); fi; done
    [ "${#apps[@]}" -eq 1 ] || die "zip 최상위 .app 이 1개가 아니다(${#apps[@]})"
    cd="$( (codesign -dvvv "${apps[0]}" 2>&1 || true) | sed -n 's/^CDHash=//p' | head -1 | tr 'A-F' 'a-f')"
    [[ "$cd" =~ ^[0-9a-f]{40}$ ]] || die "CDHash 를 못 읽었다(서명 안 된 번들?)"
    # 봉인·DR 핀(설계 §3-6 ② · 기기가 S2 에서 같은 대조를 한다 — 발행 쪽에서 먼저 막는다). 링커 자동 서명된 Mach-O 하나만
    #   있어도 CDHash 는 읽히므로 CDHash 존재 ≠ 서명된 번들이다(실측 2026-10-06). -R 문법 = 「identifier … and certificate leaf =
    #   H"…"」(앞에 '=designated =>' 를 붙이면 이 macOS 에서 문법 오류 — 실측). 핀 기본 = cys-local leaf · 시험만 none.
    codesign --verify --deep --strict "${apps[0]}" 2>/dev/null || die "codesign --verify 실패(봉인되지 않은 번들)"
    pin="${CYS_COLLECT_DR_PIN:-a426231e7dc737ee1d74962b346c23d3acacb18d}"
    if [ "$pin" != "none" ]; then
      [[ "$pin" =~ ^[0-9a-f]{40}$ ]] || die "DR 핀 형식(40 hex): $pin"
      codesign --verify -R="identifier \"com.cysjavis.terminal\" and certificate leaf = H\"$pin\"" "${apps[0]}" 2>/dev/null \
        || die "DR 핀 불일치 — 번들이 identifier com.cysjavis.terminal + leaf $pin 으로 서명되지 않았다"
    else
      echo "collect-inputs: ⚠DR 핀 대조 건너뜀(CYS_COLLECT_DR_PIN=none · 시험 전용)" >&2
    fi
    bin="${apps[0]}/Contents/MacOS/cys"
    [ -x "$bin" ] || die "번들 안 cys 없음: $bin"
    "$bin" build-info --json > "$out/build-info-$target.json.tmp" || die "cys build-info 실패(1.1.8 U1 이전 바이너리?)"
    mv "$out/build-info-$target.json.tmp" "$out/build-info-$target.json"
    echo "$cd" > "$out/cdhash-$target.txt"
    echo "✅ 맥 재료 $target — CDHash $cd · build-info $(tr -d '\n' < "$out/build-info-$target.json" | cut -c1-120)"
    ;;
  win)
    setup="${2:-}" out="${3:-}"
    [ -f "$setup" ] && [ -n "$out" ] || die "사용: win <setup.exe> <outdir>"
    command -v cygpath >/dev/null || die "윈(Git Bash) 전용 모드"
    dest="$out/payload-windows-x64"
    [ ! -e "$dest" ] || die "대상 폴더가 이미 있다(빈 폴더에만 설치): $dest"
    mkdir -p "$out"
    # /D 는 마지막 인자 · 따옴표 없음(NSIS 규칙 · 설계 §3-7 S9 와 같은 규약). 무인(/S) = 창 0.
    "$setup" /S "/D=$(cygpath -w "$(cd "$out" && pwd)/payload-windows-x64")" || die "무인 설치 실패(rc $?)"
    [ ! -e "$dest/cys-install-failure.txt" ] || die "설치기가 실패 기록을 남겼다: $(head -c 400 "$dest/cys-install-failure.txt")"
    [ -x "$dest/cys.exe" ] || die "설치된 cys.exe 없음"
    "$dest/cys.exe" build-info --json > "$out/build-info-windows-x64.json.tmp" || die "cys build-info 실패(1.1.8 U1 이전 바이너리?)"
    mv "$out/build-info-windows-x64.json.tmp" "$out/build-info-windows-x64.json"
    echo "✅ 윈 재료 — 페이로드 $(find "$dest" -type f | wc -l | tr -d ' ')개 파일 · build-info $(tr -d '\r\n' < "$out/build-info-windows-x64.json" | cut -c1-120)"
    ;;
  *) die "모드 = mac | win" ;;
esac
