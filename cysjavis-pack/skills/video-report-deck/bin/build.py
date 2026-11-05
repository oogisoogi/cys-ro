"""video-report-deck 빌더 — 장면 JSON → 문장별 목소리 → 프레임 계획(등장 움직임·자막 조각) → 렌더 → ffmpeg.

  python3 build.py --deck deck.json --out report.mp4 [--work 작업폴더] [--tts auto|say|elevenlabs]

장면 JSON 규격은 SKILL.md. 결과 = out.mp4(H.264·AAC·mov_text 자막 트랙) + 같은 이름 .srt(문장 단위).
종료 코드: 0 성공 · 2 입력(장면 JSON) 오류 · 4 의존(ffmpeg·node·Pillow·playwright·목소리) 없음 · 그 밖 = 렌더·합성 오류.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tts  # noqa: E402

PAD = 0.45          # 문장 사이 쉼(초)
SCENE_PAD = 0.7     # 장면이 바뀌기 전 추가 쉼
ENTER_FRAMES = 6    # 요소가 켜지는 움직임 프레임 수
ENTER_STEP = 1 / 15  # 그 한 프레임 길이(초) → 6×1/15 = 0.4초
CHUNK_CHARS = 10    # 자막 조각 하나에 담을 글자 수(공백 뺀 기준) 목표
FADE_FRAMES = 3     # 장면·자막이 바뀔 때 앞뒤 화면을 섞는 프레임 수(1/30초씩 = 0.1초 · tokens.css --fade)


def chunks(sentence):
    """자막 조각 — 어절을 모아 공백 뺀 글자 수가 CHUNK_CHARS 를 넘으면 끊는다. 문장부호에서도 끊는다."""
    out, cur = [], []
    for w in sentence.split():
        cur.append(w)
        n = sum(len(x) for x in cur)
        if n >= CHUNK_CHARS or re.search(r"[,.?!]$", w):
            out.append(" ".join(cur))
            cur = []
    if cur:
        if out and sum(len(x) for x in cur) < 4:
            out[-1] += " " + " ".join(cur)
        else:
            out.append(" ".join(cur))
    return out


def srt_time(t):
    ms = int(round(t * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


SCRATCH_MARK = ".cys-render-tmp"   # 이 도구가 만든 임시 하위 폴더라는 표지 — 표지가 있는 폴더만 지우고 다시 만든다


def scratch_check(d):
    """d 를 지워도 되는지 미리 본다 — 이 도구가 만든 폴더(표지 있음)이거나 비어 있거나 없을 때만 통과, 아니면 코드 2."""
    if os.path.islink(d) or (os.path.exists(d) and not os.path.isdir(d)):
        print("입력 오류 %s 는 폴더가 아니거나 바로가기(심볼릭 링크)다 — 다른 --work 를 쓴다." % d, file=sys.stderr)
        sys.exit(2)
    if os.path.isdir(d) and os.listdir(d) and not os.path.exists(os.path.join(d, SCRATCH_MARK)):
        print("입력 오류 %s 에 이 도구가 만들지 않은 파일이 있다(표지 %s 없음) — 지우지 않고 멈춘다. 다른 --work 를 쓰거나 그 폴더를 직접 옮긴다."
              % (d, SCRATCH_MARK), file=sys.stderr)
        sys.exit(2)


def scratch_make(d):
    """scratch_check 를 통과한 폴더만 비우고 표지와 함께 새로 만든다."""
    scratch_check(d)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    open(os.path.join(d, SCRATCH_MARK), "w").close()


def concat_line(path):
    """ffconcat 의 file 줄 — 절대 경로 · 작은따옴표는 '\\'' 로 이스케이프(목록 파일 위치 기준 재해석·구문 깨짐 방지)."""
    return "file '%s'\n" % os.path.abspath(path).replace("'", "'\\''")


def need_deps():
    """없는 의존을 한 번에 모아 설치 안내를 찍고 코드 4 로 멈춘다(자동 설치하지 않는다)."""
    miss = []
    ff = "맥: brew install ffmpeg · 리눅스: sudo apt install ffmpeg · 윈도: winget install Gyan.FFmpeg"
    for b, hint in (("ffmpeg", ff), ("ffprobe", ff), ("node", "Node.js 18 이상 — https://nodejs.org/ (맥: brew install node)")):
        if not shutil.which(b):
            miss.append("없음 %s — %s" % (b, hint))
    try:
        import PIL  # noqa: F401
    except ImportError:
        miss.append("없음 Pillow(파이썬 그림 모듈) — python3 -m pip install Pillow")
    if miss:
        for m in miss:
            print(m, file=sys.stderr)
        sys.exit(4)


def load_deck(path):
    """장면 JSON 을 읽고 렌더 전에 모양을 검사한다 — 틀리면 어느 장면이 왜 틀렸는지 찍고 코드 2."""
    def bad(msg):
        print("입력 오류 %s: %s" % (path, msg), file=sys.stderr)
        sys.exit(2)
    try:
        deck = json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        bad("파일이 없다")
    except ValueError as e:
        bad("JSON 이 아니다(%s)" % e)
    if not isinstance(deck, dict) or not isinstance(deck.get("scenes"), list) or not deck["scenes"]:
        bad("최상위에 비어 있지 않은 \"scenes\" 목록이 있어야 한다")
    types = {f[:-3] for f in os.listdir(os.path.join(os.path.dirname(HERE), "templates")) if f.endswith(".js")}
    for i, sc in enumerate(deck["scenes"]):
        where = "scenes[%d]" % i
        if not isinstance(sc, dict):
            bad("%s 는 객체여야 한다" % where)
        if sc.get("type") not in types:
            bad("%s 의 type %r 를 모른다 — 쓸 수 있는 것: %s" % (where, sc.get("type"), " ".join(sorted(types))))
        lines = sc.get("lines")
        if not isinstance(lines, list) or not lines:
            bad("%s 에 내레이션 lines(문장 목록)가 없다" % where)
        for k, ln in enumerate(lines):
            say = ln.get("say") if isinstance(ln, dict) else ln
            if not isinstance(say, str) or not say.strip():
                bad("%s.lines[%d] 가 빈 문장이다" % (where, k))
    return deck


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work")
    ap.add_argument("--tts", default="auto", choices=["auto", "say", "elevenlabs"])
    a = ap.parse_args()
    deck = load_deck(a.deck)
    need_deps()
    engine = tts.pick(a.tts)
    # 경로는 처음에 모두 절대 경로로 고정한다(render.js 는 스킬 폴더에서 돌고, ffconcat 은 목록 파일 기준으로 상대 경로를 푼다)
    a.out = os.path.abspath(a.out)
    work = os.path.abspath(a.work or os.path.splitext(a.out)[0] + "-work")
    frames_dir = os.path.join(work, "frames")
    padded = os.path.join(work, "padded")
    for d in (frames_dir, padded):   # 비싼 목소리 합성 전에 「남의 폴더를 지우게 되는가」부터 본다
        scratch_check(d)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    os.makedirs(os.path.join(work, "audio"), exist_ok=True)
    scratch_make(frames_dir)

    # 1) 목소리
    lines = []
    for si, sc in enumerate(deck["scenes"]):
        for k, ln in enumerate(sc["lines"]):
            ln = ln if isinstance(ln, dict) else {"say": ln}
            audio, dur = tts.synth(ln["say"], os.path.join(work, "audio"), engine)
            last = k == len(sc["lines"]) - 1
            lines.append({"scene": si, "k": k, "say": ln["say"], "step": ln.get("step", k), "audio": audio, "dur": dur,
                          "len": dur + PAD + (SCENE_PAD if last else 0)})
    # 2) 프레임 계획
    frames, t0 = [], 0.0
    scene_len = {}
    for ln in lines:
        scene_len[ln["scene"]] = scene_len.get(ln["scene"], 0) + ln["len"]
    scene_start, acc = {}, 0.0
    for ln in lines:
        scene_start.setdefault(ln["scene"], acc)
        acc += ln["len"]
    prev = (None, None)
    for ln in lines:
        ln["start"] = t0
        sc0, sclen = scene_start[ln["scene"]], scene_len[ln["scene"]]
        cs = chunks(ln["say"])
        weights = [max(1, len(c.replace(" ", ""))) for c in cs]
        total_w = sum(weights)
        times = []
        for w in weights:
            times.append(ln["dur"] * w / total_w)
        times[-1] += ln["len"] - ln["dur"]   # 쉼 동안 마지막 조각 유지
        entering = (ln["scene"], ln["step"]) != prev
        prev = (ln["scene"], ln["step"])
        tcur = t0
        for ci, (c, d) in enumerate(zip(cs, times)):
            prog = (tcur - sc0) / sclen
            if ci == 0 and entering:
                for e in range(1, ENTER_FRAMES + 1):
                    frames.append({"scene": ln["scene"], "step": ln["step"], "t": round(e / ENTER_FRAMES, 3), "caption": c,
                                   "progress": prog, "dur": ENTER_STEP})
                d -= ENTER_FRAMES * ENTER_STEP
            frames.append({"scene": ln["scene"], "step": ln["step"], "t": 1, "caption": c, "progress": prog, "dur": max(d, 1 / 30)})
            tcur += times[ci]
        t0 += ln["len"]
    # 같은 화면은 한 번만 찍는다
    keyed = {}
    for f in frames:
        key = (f["scene"], f["step"], f["t"], f["caption"], round(f["progress"], 3))
        if key not in keyed:
            keyed[key] = "f%05d.png" % len(keyed)
        f["png"] = keyed[key]
    uniq = {f["png"]: f for f in frames}
    plan = {"deck": deck.get("deck", {}), "scenes": deck["scenes"], "frames": list(uniq.values())}
    plan_path = os.path.join(work, "plan.json")
    json.dump(plan, open(plan_path, "w", encoding="utf-8"), ensure_ascii=False)
    env = dict(os.environ)
    env.pop("NODE_OPTIONS", None)
    r = subprocess.run(["node", os.path.join(HERE, "render.js"), plan_path, frames_dir], env=env, cwd=os.path.dirname(HERE))
    if r.returncode:
        sys.exit(r.returncode)   # render.js 가 이미 이유를 찍었다(4 = playwright·크롬 없음)

    # 2-1) 0.1초 페이드 — 장면이 바뀌거나 자막 조각이 바뀌는 자리에서 앞 화면과 뒤 화면을 섞은 프레임을 끼운다
    #      (요소 등장 움직임 프레임 사이에는 넣지 않는다 · 시간은 뒤 화면 몫에서 뺀다)
    from PIL import Image
    seq, cache = [frames[0]], {}
    for fa, fb in zip(frames, frames[1:]):
        change = fb["scene"] != fa["scene"] or fb["caption"] != fa["caption"]
        fd = FADE_FRAMES / 30
        take_prev = seq[-1]["dur"] > fd + 0.05          # 앞 화면 몫에서 뺄 수 있으면 앞에서(장면 끝 쉼이 넉넉하다)
        if change and fb["png"] != fa["png"] and (take_prev or fb["dur"] > fd + 0.05):
            key = (fa["png"], fb["png"])
            if key not in cache:
                ia = Image.open(os.path.join(frames_dir, fa["png"])).convert("RGB")
                ib = Image.open(os.path.join(frames_dir, fb["png"])).convert("RGB")
                names = []
                for j in range(1, FADE_FRAMES + 1):
                    n = "x%05d_%d.png" % (len(cache), j)
                    Image.blend(ia, ib, j / (FADE_FRAMES + 1)).save(os.path.join(frames_dir, n), compress_level=1)
                    names.append(n)
                cache[key] = names
            if take_prev:
                seq[-1] = dict(seq[-1], dur=seq[-1]["dur"] - fd)
            else:
                fb = dict(fb, dur=fb["dur"] - fd)
            for n in cache[key]:
                seq.append({"png": n, "dur": 1 / 30})
        seq.append(fb)
    frames = seq

    # 3) 영상(프레임 + 길이) · 소리(문장 + 쉼) · 자막
    video_list, audio_list = os.path.join(work, "video.txt"), os.path.join(work, "audio.txt")
    with open(video_list, "w", encoding="utf-8") as f:
        for fr in frames:
            f.write(concat_line(os.path.join(frames_dir, fr["png"])) + "duration %.4f\n" % fr["dur"])
        f.write(concat_line(os.path.join(frames_dir, frames[-1]["png"])))
    scratch_make(padded)
    with open(audio_list, "w", encoding="utf-8") as f:
        for i, ln in enumerate(lines):
            p = os.path.join(padded, "a%04d.wav" % i)
            run(["ffmpeg", "-v", "error", "-y", "-i", ln["audio"], "-af", "apad=whole_dur=%.4f" % ln["len"], "-t", "%.4f" % ln["len"],
                 "-ar", "48000", "-ac", "1", p])
            f.write(concat_line(p))
    total = sum(ln["len"] for ln in lines)
    srt = os.path.splitext(a.out)[0] + ".srt"
    with open(srt, "w", encoding="utf-8") as f:
        for i, ln in enumerate(lines):
            f.write("%d\n%s --> %s\n%s\n\n" % (i + 1, srt_time(ln["start"]), srt_time(ln["start"] + ln["dur"]), ln["say"]))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", video_list,
         "-f", "concat", "-safe", "0", "-i", audio_list, "-i", srt,
         "-map", "0:v", "-map", "1:a", "-map", "2", "-vf", "fps=30,format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-c:a", "aac", "-b:a", "160k",
         "-c:s", "mov_text", "-metadata:s:s:0", "language=kor", "-t", "%.3f" % total, "-movflags", "+faststart", a.out])
    print(json.dumps({"engine": engine, "lines": len(lines), "scenes": len(deck["scenes"]), "frames": len(frames), "fades": len(cache),
                      "unique_png": len(uniq), "seconds": round(total, 1), "mp4": a.out, "srt": srt}, ensure_ascii=False))


if __name__ == "__main__":
    main()
