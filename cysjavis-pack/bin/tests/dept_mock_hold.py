#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dept_mock_hold.py — cys-dept 시험의 목 cysd 를 「응답이 관측될 때까지」 살려 두는 sh 조각(TICKET=cysr-1111-dept-mock-siblings).

왜: 우리 boot_wait(cys-dept)는 한 반복에서 (핑 → `kill -0 pid`) 순으로 본다. 목 cysd 가 소켓 파일을 만들자마자 끝나면 그
「생성 → 종료」가 두 관측 사이에 끼는 순간(핑은 생성 전 · kill -0 은 종료 후) 성공해야 할 경로가 '기동 중 종료'로 뒤집힌다
(CI 39707938057 1회차 · test_dept_create_progress 에서 처음 확정 · b5ed5fbc). 실 cysd 는 응답한 뒤 스스로 끝나지 않으므로 목도
**응답이 관측되기 전에는 끝나지 않는다** — 핑 목이 성공을 알릴 때(answered.<소켓키>)까지 살고, 핑 목은 그 목이 끝난(좀비 포함)
뒤에야 성공을 돌려준다(케이스 끝 잔존 프로세스 검사와 경주하지 않게).

조각만 준다 — 목 스크립트의 나머지 꼴(셔뱅 · 호출 기록 · env 덤프 · 서식 방식)은 각 시험 파일이 그대로 갖는다.
조각에는 `%` 가 없다 — `%` 서식 템플릿에 **값**으로 끼워도, 그냥 이어 붙여도 같다. POSIX sh 문법만 쓴다(목이 `#!/bin/sh`).
대기는 `command -p sleep` — PATH 선두에 no-op `sleep` 목을 두는 하네스에서도 실제로 쉰다.
(test_dept_create_progress 는 같은 수리를 자기 bash·@STATE@ 꼴로 먼저 들였다 — 그 파일은 이 모듈을 쓰지 않는다.)
"""
import os


def state_dir(tmp):
    """케이스 임시 폴더 아래 목 상태 폴더(만들어 돌려준다) — 소켓 폴더를 건드리지 않으려고 따로 둔다."""
    d = os.path.join(tmp, "mockhold")
    os.makedirs(d, exist_ok=True)
    return d


def _key():
    return 'k=$(echo "$CYS_SOCKET" | tr / _)'


def ping_answered(state):
    """목 cys 의 ping **성공 갈래** 전체(끝에 `exit 0`) — `[ -e "$CYS_SOCKET" ] && { <이것>; } || exit 1` 꼴로 쓴다.
    관측 신호를 세우고, 그 소켓의 목 cysd 가 떠 있으면 끝날 때(좀비/사라짐)까지 기다린다(상한 500회 — 정상 1~3회)."""
    return ('%s; touch "%s/answered.$k"; '
            'if [ -f "%s/cysd.$k" ]; then read -r p < "%s/cysd.$k"; i=0; '
            'while [ $i -lt 500 ] && kill -0 "$p" 2>/dev/null && [ "$(ps -o stat= -p "$p" 2>/dev/null | cut -c1)" != Z ]; '
            'do command -p sleep 0.01; i=$((i+1)); done; rm -f "%s/cysd.$k"; fi; exit 0'
            ) % (_key(), state, state, state, state)


def cysd_before_touch(state):
    """목 cysd 의 소켓 `touch` **앞** 한 줄 — 묵은 관측 신호를 지우고(같은 소켓 재스폰) 자기 pid 를 남긴다."""
    return '%s; rm -f "%s/answered.$k"; echo $$ > "%s/cysd.$k"\n' % (_key(), state, state)


def cysd_after_touch(state):
    """목 cysd 의 소켓 `touch` **뒤** 한 줄 — 관측 신호가 생길 때까지 산다(상한 1000회 × 0.01초)."""
    return 'i=0; while [ ! -e "%s/answered.$k" ] && [ $i -lt 1000 ]; do command -p sleep 0.01; i=$((i+1)); done\n' % state
