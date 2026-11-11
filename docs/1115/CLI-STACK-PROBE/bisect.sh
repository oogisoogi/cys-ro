#!/bin/bash
# 사용: bisect.sh <test-binary> <test-name> [lo] [hi] [step]
# RUST_MIN_STACK 이분법 — 「통과하는 최소 스택(바이트)」. 통과 = rc 0 + "1 passed".
B=$1; T=$2; LO=${3:-65536}; HI=${4:-8388608}; STEP=${5:-4096}
pass() { RUST_MIN_STACK=$1 "$B" --exact "$T" >/dev/null 2>&1 && return 0 || return 1; }
pass $HI || { echo "HI=$HI 에서도 실패"; exit 2; }
pass $LO && { echo "LO=$LO 에서 통과 — 계기가 대상을 못 만남"; exit 3; }
while [ $((HI-LO)) -gt $STEP ]; do M=$(( (LO+HI)/2 )); if pass $M; then HI=$M; else LO=$M; fi; done
echo "MIN_PASS=$HI MAX_FAIL=$LO"
