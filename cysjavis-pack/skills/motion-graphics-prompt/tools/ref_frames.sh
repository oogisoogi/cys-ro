#!/usr/bin/env bash
# 레퍼런스 영상 「보기」 — 클로드는 영상을 직접 못 보므로 장면 낱장(초당 N장)과 한 장짜리 모아보기를 뽑는다.
# 사용: ref_frames.sh <prompt-motion 주소 | mp4 주소 | 유튜브 주소 | 로컬 파일> <출력폴더> [초당장수=1]
#
# 남기는 것 = <출력폴더>/f_NNN.png(낱장) · contact.png(모아보기) 뿐이다. 출력폴더는 작업용 임시 폴더로 정하고 다 보면 지운다.
# 받아 온 영상·페이지는 이 스크립트가 만든 임시 폴더에서만 쓰고 끝날 때 지운다.
# Prompt Motion 페이지(사이트 조건 use=reference · ai-train=no)는 참고용으로만 쓴다 — 원 프롬프트는 화면(표준 출력)에만
# 찍고 파일로 저장하지 않는다. 영상·프롬프트를 쌓아 두거나 다시 배포하지 않는다.
# 종료 코드: 0 성공 · 2 사용법·입력 오류 · 3 페이지에서 영상 주소를 못 찾음 · 4 의존 없음
set -euo pipefail

usage() { echo "사용: ref_frames.sh <prompt-motion 주소 | mp4 주소 | 유튜브 주소 | 로컬 파일> <출력폴더> [초당장수=1]" >&2; exit 2; }
[ $# -ge 2 ] || usage
src="$1"; out="$2"; per="${3:-1}"
bad_per() { echo "입력 오류 초당장수는 0보다 큰 수여야 한다: $per" >&2; exit 2; }
case "$per" in ''|*[!0-9.]*|*.*.*) bad_per ;; esac   # 숫자와 점 하나만
case "$per" in *[1-9]*) ;; *) bad_per ;; esac         # 0 · 0.0 · . 거부

need() {  # need <명령> <설치 안내>
  command -v "$1" >/dev/null 2>&1 || { echo "없음 $1 — $2" >&2; exit 4; }
}
FF_HINT="맥: brew install ffmpeg · 리눅스: sudo apt install ffmpeg · 윈도: winget install Gyan.FFmpeg"
need ffmpeg "$FF_HINT"
need ffprobe "$FF_HINT"
case "$src" in
  https://prompt-motion.com/*)
    need curl "맥·리눅스는 보통 기본 설치 · 리눅스: sudo apt install curl"
    need python3 "맥: brew install python · 리눅스: sudo apt install python3 · 윈도: winget install Python.Python.3.12" ;;
  https://youtu.be/*|https://www.youtube.com/*|https://youtube.com/*)
    need yt-dlp "맥: brew install yt-dlp · 리눅스·윈도: python3 -m pip install -U yt-dlp" ;;
  http://*|https://*)
    need curl "맥·리눅스는 보통 기본 설치 · 리눅스: sudo apt install curl" ;;
  *)
    [ -f "$src" ] || { echo "입력 오류 로컬 파일이 없다: $src" >&2; exit 2; } ;;
esac

tmp="$(mktemp -d "${TMPDIR:-/tmp}/ref_frames.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$out"
vid="$tmp/ref.mp4"
case "$src" in
  https://prompt-motion.com/*)
    curl -fsSL -A 'Mozilla/5.0' "$src" -o "$tmp/page.html"
    mp4=$(grep -o 'https://media.prompt-motion.com/[^"]*\.mp4' "$tmp/page.html" | head -1 || true)
    [ -n "$mp4" ] || { echo "실패 페이지에 mp4 주소가 없다: $src" >&2; exit 3; }
    # 페이지의 프롬프트 칸(원 게시물 프롬프트)을 화면에만 찍는다(저장하지 않음 · 참고용)
    echo "----- 원 프롬프트(참고용 · 저장 안 함 · 출처 $src) -----"
    python3 -I - "$tmp/page.html" <<'PY'
import html, re, sys
h = html.unescape(open(sys.argv[1], encoding="utf-8").read())
t = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
t = re.sub(r"<(br|/p|/li|/h\d|/pre|/div)[^>]*>", "\n", t)
t = re.sub(r"<[^>]+>", "", t)
m = re.search(r"Copy\n?(.*?)\n?This prompt was taken", t, re.S)
print(m.group(1).strip() if m else "(프롬프트 칸을 못 찾음 — 사이트 모양이 바뀌었을 수 있다 · 주소를 브라우저로 직접 보라)")
PY
    echo "-----"
    curl -fsSL "$mp4" -o "$vid" ;;
  https://youtu.be/*|https://www.youtube.com/*|https://youtube.com/*)
    yt-dlp -q -f 'bv*[height<=720]+ba/b[height<=720]' --merge-output-format mp4 -o "$vid" "$src" ;;
  http://*|https://*) curl -fsSL "$src" -o "$vid" ;;
  *) vid="$src" ;;
esac
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$vid") || { echo "실패 영상으로 읽을 수 없다: $src" >&2; exit 2; }
rm -f "$out"/f_[0-9][0-9][0-9].png "$out/contact.png"
ffmpeg -loglevel error -y -i "$vid" -vf "fps=$per,scale=640:-2" "$out/f_%03d.png"
n=$(find "$out" -maxdepth 1 -name 'f_[0-9][0-9][0-9].png' | wc -l | tr -d ' ')
cols=4; rows=$(( (n + cols - 1) / cols ))
[ "$rows" -ge 1 ] || rows=1
# 모아보기: 왼쪽 위부터 가로로 읽는다 · k 번째 칸(1부터) = (k-1)/per 초 (drawtext 가 없는 ffmpeg 도 있어 시각 글자는 안 찍는다)
ffmpeg -loglevel error -y -i "$vid" -vf "fps=$per,scale=480:-2,tile=${cols}x${rows}" -frames:v 1 "$out/contact.png"
echo "영상 길이 ${dur}s · 낱장 ${n}장($per/초 · f_001 = 0초) → $out/f_*.png · 모아보기 ${cols}열 → $out/contact.png"
echo "다 본 뒤에는 $out 을 지운다(참고용 낱장은 쌓아 두지 않는다)."
