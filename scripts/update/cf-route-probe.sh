#!/usr/bin/env bash
# cf-route-probe — 「경로 라우트 jarvis.godmeyou.kr/update/* 가 사이트 커스텀 도메인(jarvis-site)보다 먼저 잡히는가」 실측
# (1.1.8 U3 2판 · master 결정 ① · HANDOFF-U3 §3 ① 단점 「우선순위 미측정」).
#
# ★실행 = master(외부 계정 · Cloudflare 에 워커를 잠깐 올린다 · 실행 직전 확인 대상). 워커는 이 스크립트를 실행하지 않는다.
#   기본 = 드라이런(할 일만 출력 · 네트워크 0). 실제 실행 = `--execute`.
#
# 하는 일(실행 시):
#   ① 빈 탐침 워커(이름 cys-update-route-probe · 응답 헤더 X-Cys-Route-Probe: <1회용 값>)를 **스테이징 경로**
#      `jarvis.godmeyou.kr/update/__route_probe/*` 에만 라우트로 배포한다 — 실제 갱신 경로(/update/<c>/…)는 건드리지 않는다.
#   ② `curl -sI https://jarvis.godmeyou.kr/update/__route_probe/x` 응답 헤더에 그 값이 있으면 = 경로 라우트가 이긴다(통과).
#      없으면 = 커스텀 도메인 정적 자산이 먼저 잡는다(실패 — update-worker 배포 금지 · 대안 = 사이트 워커 안 라우팅).
#   ③ 대조군: `/` 응답에 그 헤더가 **없어야** 한다(사이트가 탐침에 먹히지 않음).
#   ④ 탐침 워커를 지운다(성공·실패 무관 · trap).
# ⚠미측정(정직): wrangler@3 의 `delete --name … --force` 철자는 이 기계에서 돌려 보지 않았다(CF 실행 0) — 첫 실행 때 확인.
# 종료: 0 = 경로 라우트 우선(배포 가능) · 1 = 커스텀 도메인 우선(배포 금지) · 2 = 사용법·도구 · 3 = 판정 불가(전파 시간 초과 등)
set -euo pipefail
HOST="jarvis.godmeyou.kr" ZONE="godmeyou.kr" NAME="cys-update-route-probe" WRANGLER="${WRANGLER:-bunx wrangler@3}"
EXECUTE=0 WAIT=90
while [ $# -gt 0 ]; do
  case "$1" in
    --execute) EXECUTE=1; shift ;;
    --wait) WAIT="$2"; shift 2 ;;
    *) echo "모르는 인자: $1 (사용: cf-route-probe.sh [--execute] [--wait 초])" >&2; exit 2 ;;
  esac
done
NONCE="$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
PROBE_PATH="/update/__route_probe/x"
WORK="$(mktemp -d)"
cat > "$WORK/index.js" <<JS
export default { async fetch() { return new Response("probe\n", { headers: { "X-Cys-Route-Probe": "$NONCE", "Cache-Control": "no-store" } }); } };
JS
cat > "$WORK/wrangler.jsonc" <<JSON
{ "name": "$NAME", "main": "index.js", "compatibility_date": "2026-08-04", "workers_dev": false,
  "routes": [ { "pattern": "$HOST/update/__route_probe/*", "zone_name": "$ZONE" } ] }
JSON
echo "탐침 값 = $NONCE · 탐침 워커 = $NAME · 라우트 = $HOST/update/__route_probe/*"
if [ "$EXECUTE" != 1 ]; then
  echo "드라이런 — 실행할 명령:"
  echo "  (cd <탐침 폴더(실행 때 새로 만든다)> && $WRANGLER deploy)"
  echo "  curl -sSI --max-redirs 0 https://$HOST$PROBE_PATH | grep -i x-cys-route-probe   # = $NONCE 이면 통과"
  echo "  curl -sSI --max-redirs 0 https://$HOST/ | grep -i x-cys-route-probe            # 없어야 함(대조군)"
  echo "  $WRANGLER delete --name $NAME --force   # 성공·실패 무관(trap)"
  echo "실제 실행 = --execute (master · 실행 직전 확인 뒤)"
  rm -rf "$WORK"; exit 0
fi
cleanup() { (cd "$WORK" && $WRANGLER delete --name "$NAME" --force >/dev/null 2>&1) || echo "⚠탐침 워커 삭제 실패 — 손으로: $WRANGLER delete --name $NAME" >&2; rm -rf "$WORK"; }
trap cleanup EXIT
(cd "$WORK" && $WRANGLER deploy) || { echo "탐침 배포 실패" >&2; exit 2; }
hdr() { { curl -sSI --max-redirs 0 -H 'Cache-Control: no-cache' "https://$HOST$1" 2>/dev/null || true; } | tr -d '\r' | awk -F': ' 'tolower($1)=="x-cys-route-probe"{print $2}'; }
t=0 got=""
while [ "$t" -lt "$WAIT" ]; do
  got="$(hdr "$PROBE_PATH")"
  [ "$got" = "$NONCE" ] && break
  sleep 5; t=$((t + 5))
done
ctrl="$(hdr /)"
[ -z "$ctrl" ] || { echo "판정 불가: 대조군 / 에도 탐침 헤더($ctrl) — 라우트가 너무 넓다" >&2; exit 3; }
if [ "$got" = "$NONCE" ]; then
  echo "✅ 경로 라우트 우선 — $PROBE_PATH 응답 = 탐침 워커($NONCE) · / = 사이트 그대로 → update-worker 배포 가능"
  exit 0
fi
code="$(curl -s -o /dev/null -w '%{http_code}' --max-redirs 0 "https://$HOST$PROBE_PATH" || true)"
echo "❌ ${WAIT}초 안에 탐침 헤더 없음(응답 $code) — 커스텀 도메인(jarvis-site)이 먼저 잡는다고 판정 · update-worker 배포 금지" >&2
exit 1
