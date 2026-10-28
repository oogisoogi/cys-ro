#!/bin/sh
# Bundle the aiterm UI into ui/dist (plain static files; no dev server).
set -e
cd "$(dirname "$0")"
bun install --silent
mkdir -p dist
bun build src/main.ts --outdir dist --target browser --minify
cp index.html dist/index.html
cp src/style.css dist/style.css
cp node_modules/@xterm/xterm/css/xterm.css dist/xterm.css
# 동봉 글꼴 JetBrains Mono + OFL 라이선스(글꼴과 함께 배포 의무) — termrender.ts loadBundledFont 가 ./fonts/ 에서 읽는다
mkdir -p dist/fonts
cp fonts/JetBrainsMono-wght.ttf fonts/JetBrainsMono-Italic-wght.ttf fonts/OFL.txt dist/fonts/
echo "ui/dist ready"
