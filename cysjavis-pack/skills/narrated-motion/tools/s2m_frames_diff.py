#!/usr/bin/env python3
"""두 번 렌더한 프레임 폴더가 같은지 본다 — 「같은 t 에는 언제나 같은 그림」의 영상 전체 판 검사.

  python3 s2m_frames_diff.py <첫번째/frames> <두번째/frames>

seek_render.js --duration 을 서로 다른 --out 으로 두 번 돌린 뒤 쓴다(두 번은 서로 다른 브라우저 실행 = 불러올 때의
무작위·현재 시각까지 잡힌다). 출력 = 프레임 수 · 같은 장수 · 다른 프레임 번호(앞 10개)와 그 시각. 종료 0 = 전부 같음.
"""
import hashlib
import os
import sys


def shas(d):
    fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    return fs, [hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest() for f in fs]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    fps = float(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 30.0
    fa, ha = shas(sys.argv[1])
    fb, hb = shas(sys.argv[2])
    if fa != fb:
        print(f"FAIL 프레임 목록이 다르다 ({len(fa)} vs {len(fb)})")
        sys.exit(1)
    bad = [i for i, (x, y) in enumerate(zip(ha, hb)) if x != y]
    print(f"프레임 {len(fa)} · 같음 {len(fa) - len(bad)} · 다름 {len(bad)}"
          + (" · 예: " + ", ".join(f"{fa[i]}({i / fps:.2f}s)" for i in bad[:10]) if bad else "") + f" · {'OK' if not bad else 'FAIL'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
