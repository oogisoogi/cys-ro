#!/usr/bin/env python3
"""arm64 맥 바이너리에서 함수 머리말(prologue)의 정적 스택 틀 크기(바이트)를 잰다.
사용: frame_size.py <binary> <regex-on-mangled-symbol> ...
머리말 규칙(LLVM aarch64): stp ..., [sp, #-N]! (레지스터 저장) + `sub x9, sp, #P, lsl #12` 탐침 고리(P 쪽)
+ 뒤이은 `sub sp, sp, #M`(남은 바이트) · 큰 틀이 아니면 `sub sp, sp, #M` 만."""
import re, subprocess, sys
B = sys.argv[1]
syms = subprocess.run(["nm", B], capture_output=True, text=True).stdout.split("\n")
names = [l.split()[-1] for l in syms if len(l.split()) == 3 and l.split()[1] in "tT"]
for pat in sys.argv[2:]:
    for n in [x for x in names if re.search(pat, x)]:
        asm = subprocess.run(["otool", "-tV", "-p", n, B], capture_output=True, text=True).stdout.split("\n")[2:40]
        push = big = small = 0
        for l in asm:
            m = re.search(r"stp\s.*\[sp, #-0x([0-9a-f]+)\]!", l)
            if m: push += int(m.group(1), 16); continue
            m = re.search(r"sub\s+x9, sp, #0x([0-9a-f]+), lsl #12", l)
            if m: big = int(m.group(1), 16) * 4096; continue
            m = re.search(r"sub\s+sp, sp, #0x([0-9a-f]+)(, lsl #12)?$", l)
            if m:
                v = int(m.group(1), 16) * (4096 if m.group(2) else 1)
                if big and m.group(2): continue  # 탐침 고리 안의 한 쪽 단위 — big 에 이미 포함
                small += v
            if re.search(r"\b(bl|ret)\b", l): break
        print(f"{push+big+small:>10}  {n}")
