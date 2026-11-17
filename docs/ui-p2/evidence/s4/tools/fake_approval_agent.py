#!/usr/bin/env python3
"""대역 도우미 — Claude Code 도구 허락 창 모양을 그리고 받은 바이트를 (단조 시각 · 길이 · 16진)으로 기록(조각 4 바깥 증거).
쓰는 법: python3 fake_approval_agent.py <기록 파일>"""
import os, sys, termios, time, tty

log = open(sys.argv[1], "a", buffering=1)
fd = sys.stdin.fileno()
try:
    tty.setraw(fd)
except termios.error:
    pass
sys.stdout.write("\x1b[2J\x1b[H")
sys.stdout.write(" Bash command\r\n\r\n   rm -rf build\r\n   빌드 폴더 지우기\r\n\r\n Do you want to proceed?\r\n❯ 1. Yes\r\n   2. No\r\n")
sys.stdout.write("\x1b[7;1H")  # 커서 = 「❯ 1. Yes」 행(claude 선택 창의 실제 커서 자리 · 데몬 approval_in_prompt_tail 의 가로줄 없는 갈래 조건)
sys.stdout.flush()
log.write(f"# drawn {time.monotonic():.6f}\n")
while True:
    b = os.read(fd, 4096)
    if not b:
        break
    log.write(f"{time.monotonic():.6f} {len(b)} {b.hex()}\n")
    if b"\r" in b or b"\x1b" in b:
        sys.stdout.write("\x1b[2J\x1b[H(창 닫힘)\r\n")
        sys.stdout.flush()
