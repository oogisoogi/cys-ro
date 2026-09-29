#!/bin/sh
# place-sidecar.sh — tauri externalBin 사이드카(cys·cysd) 배치의 단일 출처 (TICKET=cysr-117-impl-lead · master#5daf328b).
#
# ★왜 따로 두나: `cp` 는 대상 파일이 **이미 있으면 그 파일의 권한을 그대로 둔다**. 한 번이라도 644 로 남은
#   사이드카는 그 뒤 빌드마다 644 인 채 번들에 실렸다 — 2026-09-25 arm64 zip 의 cys·cysd 가 실행 비트 없이
#   나갔고(codesign·CDHash 는 통과 · Gatekeeper -x 검사만 잡음) 이는 「전 pane 사망」 계급이다.
#   ⇒ 옛 파일을 지우고 복사 → 실행 비트 강제 → 확인. 확인 실패 = 빌드 중단(번들에 싣지 않는다).
# 시험 = run_bootstrap_health.py H-BUNDLE-PERM-1(기존 644 대상 위에 배치 → 실행 비트 · 원본 바이트 동일).
# 쓰는 법: `. scripts/lib/place-sidecar.sh` 뒤 `place_sidecar <원본> <대상>` · source 시점 부작용 없음(함수 정의만).

place_sidecar() {  # $1=원본(빌드 산출) $2=대상(src-tauri/binaries/…)
  rm -f "$2"
  cp "$1" "$2"
  chmod 755 "$2"
  case "$2" in
    *.exe) ;;  # Windows 는 실행 비트 개념이 없다(확장자로 실행)
    *) [ -x "$2" ] || { echo "bundle-prep: 사이드카 실행 비트 없음: $2 — 번들에 싣지 않고 중단" >&2; exit 1; } ;;
  esac
}
