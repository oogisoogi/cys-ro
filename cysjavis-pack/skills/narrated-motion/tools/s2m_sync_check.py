#!/usr/bin/env python3
"""완성 mp4 에서 소리·그림 싱크를 잰다 — 큐(문장) 시작 시각 대비.

  python3 s2m_sync_check.py <out.mp4> <cues.json> [--tol 0.2] [--dead 0.4] [--json 결과.json]

재는 것(전부 mp4 자체에서 — 우리가 만든 표를 믿지 않고 결과물을 다시 잰다 · 오디오·비디오 스트림의 시작 지연(편집 목록)도
  플레이어처럼 0초 기준으로 살려서 읽는다 — aresample first_pts=0 · fps 필터):
  소리   mp4 의 오디오를 10 ms 창으로 읽어, 큐 시작 −0.5 s ~ 큐 끝 사이에서 80 ms 이상 무음 뒤 처음으로 −40 dBFS 를 넘는 창 = 말 시작
  그림   mp4 를 160×90 회색으로 읽어 이웃 프레임 차이를 내고, 큐 시작 ±0.5 s 안의 가장 큰 변화의 절반을 처음 넘는 프레임 = 그림 바뀜
  판정   |소리 − 큐 시작| ≤ tol · |그림 − 큐 시작| ≤ tol · |소리 − 그림| ≤ tol → 큐마다 OK/FAIL
  덤     dead air: 첫 말 뒤 ~ 마지막 말 끝 사이에서 −40 dBFS 아래가 dead 초 이상 이어지는 곳(script-to-motion 의 0.4 s 규칙)
종료 코드 0 = 전부 OK · 1 = FAIL 있음 · 2 = 사용법/입력 오류
"""
import array
import json
import math
import subprocess
import sys
import os  # NOWIN(윈도 콘솔 창 숨김) 정의용

# 윈도에서 출력 캡처 자식의 콘솔 창을 숨긴다(test_nowin_captured_spawns 규칙)
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

AR, WIN = 16000, 160          # 10 ms
QUIET = 8                     # 말 시작 앞에 있어야 하는 무음 창 수(80 ms)
VW, VH = 160, 90


def opt(name, default):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    mp4, cj = sys.argv[1], sys.argv[2]
    tol, dead = opt("--tol", 0.2), opt("--dead", 0.4)
    cues = json.load(open(cj, encoding="utf-8"))["cues"]
    fps_s = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                            "-of", "csv=p=0", mp4], capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL, **NOWIN).stdout.strip()
    n, d = fps_s.split("/")
    fps = float(n) / float(d)

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vn", "-af", "aresample=async=1:first_pts=0",
                          "-ac", "1", "-ar", str(AR), "-f", "s16le", "-"],
                         capture_output=True, check=True, stdin=subprocess.DEVNULL, **NOWIN).stdout
    a = array.array("h")
    a.frombytes(raw)
    if not len(a):
        print("실패 오디오 트랙이 비어 있다")
        sys.exit(1)
    db = []
    for i in range(0, len(a) - WIN + 1, WIN):
        seg = a[i:i + WIN]
        rms = math.sqrt(sum(x * x for x in seg) / WIN) or 1e-9
        db.append(20 * math.log10(rms / 32768))
    thr = -40.0

    vraw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-an", "-vf", f"fps={fps_s},scale={VW}:{VH},format=gray",
                           "-f", "rawvideo", "-"], capture_output=True, check=True, stdin=subprocess.DEVNULL, **NOWIN).stdout
    fsz = VW * VH
    nf = len(vraw) // fsz
    diff = [0.0]
    for k in range(1, nf):
        p, q = vraw[(k - 1) * fsz:k * fsz], vraw[k * fsz:(k + 1) * fsz]
        diff.append(sum(abs(x - y) for x, y in zip(p, q)) / fsz)

    rows, fail = [], 0
    for c in cues:
        s, e = c["start"], c["end"]
        i0, i1 = max(0, int((s - 0.5) * 100)), min(len(db), int(e * 100))
        # 말 시작 = 무음(QUIET 창 연속) 다음에 처음 소리가 난 창 — 앞 문장의 꼬리를 말 시작으로 잡지 않게
        ao = next((i / 100 for i in range(max(i0, QUIET), i1)
                   if db[i] > thr and all(x <= thr for x in db[i - QUIET:i])), None)
        k0, k1 = max(1, int(round((s - 0.5) * fps))), min(nf - 1, int(round((s + 0.5) * fps)))
        win = diff[k0:k1 + 1]
        vo = None
        if win and max(win) > 0.3:
            m = max(win)
            # 프레임 k 와 k-1 사이에서 바뀌었으면 그림이 바뀐 시각 = 프레임 k 의 시각
            vo = next((k0 + j) / fps for j, x in enumerate(win) if x >= m / 2)
        ok = ao is not None and vo is not None and abs(ao - s) <= tol and abs(vo - s) <= tol and abs(ao - vo) <= tol
        fail += 0 if ok else 1
        rows.append({"id": c["id"], "cue_start": s, "audio_onset": ao, "visual_onset": vo,
                     "audio_err": None if ao is None else round(ao - s, 3),
                     "visual_err": None if vo is None else round(vo - s, 3),
                     "av_err": None if ao is None or vo is None else round(ao - vo, 3), "ok": ok})
        fmt = lambda x: "  없음" if x is None else f"{x:+.3f}"
        print(f"{c['id']}  큐 {s:7.3f}  소리 {fmt(rows[-1]['audio_err'])}  그림 {fmt(rows[-1]['visual_err'])}  "
              f"소리−그림 {fmt(rows[-1]['av_err'])}  {'OK' if ok else 'FAIL'}")

    first = next((i for i, x in enumerate(db) if x > thr), 0)
    last = max((i for i, x in enumerate(db) if x > thr), default=0)
    gaps, run = [], 0
    for i in range(first, last + 1):
        if db[i] <= thr:
            run += 1
        else:
            if run / 100 >= dead:
                gaps.append({"from": round((i - run) / 100, 2), "len": round(run / 100, 2)})
            run = 0
    errs = [abs(r[k]) for r in rows for k in ("audio_err", "visual_err") if r[k] is not None]
    print(f"최대 오차 {max(errs) if errs else float('nan'):.3f}s (허용 {tol}s) · fps {fps:g} · 프레임 {nf} · "
          f"FAIL {fail}/{len(rows)} · {dead}s 이상 무음 {len(gaps)}곳 {gaps}")
    if "--json" in sys.argv:
        json.dump({"tol": tol, "fps": fps, "frames": nf, "rows": rows, "dead_air": gaps},
                  open(sys.argv[sys.argv.index("--json") + 1], "w"), ensure_ascii=False, indent=1)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
