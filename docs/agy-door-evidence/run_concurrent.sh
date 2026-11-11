#!/bin/sh
# agy 좌석 문 acceptance 를 N 회 **동시에** 돌리고 원시 기록(회차별 결과 JSON · 표준 출력 · 시작/끝 시각 · 부하)을 남긴다
# (TICKET=cysr-agy-door-r5 · codex 4R 발견 6: 「동시 5회」 원시 기록을 저장소에). 각 회차는 자기 격리 하네스 홈·데몬을 쓴다.
# 실행: sh docs/agy-door-evidence/run_concurrent.sh [N=5] [출력 폴더=docs/agy-door-evidence/concurrent-5]
#   (저장소 뿌리에서 · cargo build --bin cys --bin cysd 선행 · 실 agy 실행 0 — acceptance.py 머리 참조)
set -u
N=${1:-5}
OUT=${2:-docs/agy-door-evidence/concurrent-5}
mkdir -p "$OUT"
HERE=$(cd "$(dirname "$0")" && pwd)
{
  echo "start=$(date '+%Y-%m-%dT%H:%M:%S%z') n=$N source_commit=$(git rev-parse HEAD)"
  echo "load_start=$(uptime | sed 's/.*load averages*: //')"
} > "$OUT/run-meta.txt"
pids=""
i=1
while [ "$i" -le "$N" ]; do
  AGY_ACCEPT_OUT="$OUT/run$i.json" python3 "$HERE/acceptance.py" > "$OUT/run$i.stdout.log" 2>&1 &
  pids="$pids $!"
  i=$((i + 1))
done
rc_all=0
i=1
for p in $pids; do
  wait "$p"; rc=$?
  echo "run$i rc=$rc end=$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$OUT/run-meta.txt"
  [ "$rc" -eq 0 ] || rc_all=1
  i=$((i + 1))
done
echo "load_end=$(uptime | sed 's/.*load averages*: //')" >> "$OUT/run-meta.txt"
python3 "$HERE/acceptance.py" --redact-text "$OUT"/run*.stdout.log
echo "all_rc=$rc_all" >> "$OUT/run-meta.txt"
exit $rc_all
