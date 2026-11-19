#!/bin/bash
# 노브 켬(CYS_SEATKEEP=1) cysd 시험 실행기 — handshake-timeout(master#5b9e1d26 ⑶).
# 왜 병렬 상한이 있나: seatkeep 핸드셰이크는 절대 기한 3초(HELLO_TIMEOUT) 안에 상대 신원을 두 번 확인하고, 그 안의 Security 실행 파일 조회가
# 상대 = 디버그 시험 바이너리(수백 MB)일 때 동시 호출 수에 비례해 느려진다(accounts:: 실측 p50 = 1·2·4·8 스레드 107·155·380·984ms ·
# 기본 16 스레드 = 실패 13~30). 4 이하에서 0 실패(노브 켬 전체 실행 실측). 운영 코드와 무관한 시험 조건이다.
# 쓰임: scripts/seatkeep-knob-on-tests.sh [cargo test 거르개·인자…]   (스레드 = SEATKEEP_TEST_THREADS · 기본 4 · 4 넘으면 4 로 낮춤)
set -euo pipefail
cd "$(dirname "$0")/.."
threads="${SEATKEEP_TEST_THREADS:-4}"
if ! [[ "$threads" =~ ^[0-9]+$ ]] || [ "$threads" -lt 1 ]; then threads=4; fi
if [ "$threads" -gt 4 ]; then echo "seatkeep-knob-on-tests: 스레드 $threads → 4 로 낮춤(핸드셰이크 3초 기한)" >&2; threads=4; fi
# 시험은 target/debug/cys-seatkeep 를 cysd 옆에서 찾는다 — 낡은 실행 파일로 돌지 않게 먼저 빌드.
cargo build --bin cys-seatkeep
filters=(); rest=()
seen_dd=0
for a in "$@"; do
  if [ "$a" = "--" ]; then seen_dd=1; continue; fi
  if [ $seen_dd -eq 0 ]; then filters+=("$a"); else rest+=("$a"); fi
done
exec env CYS_SEATKEEP=1 cargo test --bin cysd ${filters[@]+"${filters[@]}"} -- --test-threads="$threads" ${rest[@]+"${rest[@]}"}
