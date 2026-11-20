#!/bin/bash
# ppt-styles 실행 입구(맥·리눅스 · 윈도는 SKILL.md 의 node/python 직접 실행).
#   bash run.sh setup                          의존 폴더 준비(package.json 복사) + 설치 명령 안내(자동 설치는 하지 않는다)
#   bash run.sh deck <내용.json> <결과.pptx>    내용 JSON → .pptx → 점검(check_pptx.py · LibreOffice 있으면 PDF 대조)
#   bash run.sh samples [id …]                 스타일 견본(3장씩) → $OUT(기본 ./ppt-styles-samples) · 점검 · 있으면 PNG·한눈 시트
# 환경: PPT_STYLES_DEPS(node_modules 가 든 폴더 · 기본 ~/.cys/deps/ppt-styles) · OUT · LO_PROFILE
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
DEPS="${PPT_STYLES_DEPS:-$HOME/.cys/deps/ppt-styles}"
PY="$(command -v python3 || command -v python || true)"
SOFFICE="$(command -v soffice || true)"; [ -z "$SOFFICE" ] && [ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ] && SOFFICE=/Applications/LibreOffice.app/Contents/MacOS/soffice
export LO_PROFILE="${LO_PROFILE:-${TMPDIR:-/tmp}/ppt-styles-lo}"   # LibreOffice 프로필(글꼴 복사본 포함 · 이 기기 임시 폴더)

need_node() {
  if ! command -v node >/dev/null 2>&1; then
    echo "[ppt-styles] node(Node.js 18 이상)가 없습니다 — .pptx 를 만들려면 필요합니다."
    echo "  설치: 맥 \`brew install node\` · 리눅스 배포판 패키지 또는 https://nodejs.org · 윈도 https://nodejs.org 설치본"
    exit 3
  fi
  local major; major="$(node -p 'process.versions.node.split(".")[0]')"
  if [ "$major" -lt 18 ]; then echo "[ppt-styles] node $major 판은 너무 낮습니다 — 18 이상으로 올려 주세요."; exit 3; fi
}
need_py() {
  if [ -z "$PY" ]; then
    echo "[ppt-styles] python3 가 없습니다 — 결과 점검(check_pptx.py)에 필요합니다."
    echo "  설치: 맥 \`brew install python\` · 리눅스 \`sudo apt install python3\` · 윈도 https://www.python.org/downloads/"
    exit 3
  fi
}
need_modules() {
  if [ ! -d "$DEPS/node_modules/pptxgenjs" ]; then
    echo "[ppt-styles] node 패키지가 설치돼 있지 않습니다(찾은 곳: $DEPS/node_modules)."
    echo "  한 번만: bash \"$HERE/run.sh\" setup  을 실행하고 안내대로 npm ci 를 돌리세요."
    exit 3
  fi
}
check() { # $1 = pptx · $2 = 기대 장 수
  local pdf=""
  if [ -n "$SOFFICE" ]; then pdf="--pdf"
  else echo "[안내] LibreOffice 가 없어 PDF 대조는 건너뜁니다(구조 점검만). 설치: 맥 \`brew install --cask libreoffice\` · 리눅스 \`sudo apt install libreoffice-impress\`"; fi
  "$PY" "$HERE/tools/check_pptx.py" "$1" --slides "$2" $pdf
}

cmd="${1:-}"; [ $# -gt 0 ] && shift
case "$cmd" in
  setup)
    need_node
    command -v npm >/dev/null 2>&1 || { echo "[ppt-styles] npm 이 없습니다 — Node.js 설치본에 함께 들어 있습니다(https://nodejs.org)."; exit 3; }
    mkdir -p "$DEPS" && cp "$HERE/package.json" "$HERE/package-lock.json" "$DEPS/" || exit 1
    echo "의존 폴더를 준비했습니다: $DEPS"
    echo "이제 다음 한 줄을 실행하세요(인터넷으로 약 130MB 를 받습니다):"
    echo "  cd \"$DEPS\" && npm ci"
    ;;
  deck)
    [ $# -eq 2 ] || { echo "사용: bash run.sh deck <내용.json> <결과.pptx>"; exit 2; }
    need_node; need_py; need_modules
    log="$(PPT_STYLES_DEPS="$DEPS" node "$HERE/tools/make_deck.js" "$1" "$2")" || { echo "$log"; exit 1; }
    echo "$log"
    n="$(echo "$log" | sed -n 's/^SLIDES=//p')"
    check "$2" "$n"
    ;;
  samples)
    need_node; need_py; need_modules
    OUT="${OUT:-$PWD/ppt-styles-samples}"; mkdir -p "$OUT"
    PPT_STYLES_DEPS="$DEPS" node "$HERE/tools/build_samples.js" "$OUT" "$@" || exit 1
    rc=0
    for x in "$OUT"/*.pptx; do
      id="$(basename "$x" .pptx)"
      if [ $# -gt 0 ] && ! echo " $* " | grep -q " $id "; then continue; fi
      check "$x" 3 || rc=1
      if command -v pdftoppm >/dev/null 2>&1 && [ -n "$SOFFICE" ]; then
        "$SOFFICE" "-env:UserInstallation=file://$LO_PROFILE" --headless --convert-to pdf --outdir "$OUT" "$x" >/dev/null 2>&1
        [ -f "$OUT/$id.pdf" ] && pdftoppm -png -r 96 "$OUT/$id.pdf" "$OUT/$id"
      fi
    done
    if ls "$OUT"/*-1.png >/dev/null 2>&1; then PPT_STYLES_DEPS="$DEPS" node "$HERE/tools/sheet.js" "$OUT"; fi
    echo "견본: $OUT"
    exit $rc
    ;;
  *)
    sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
