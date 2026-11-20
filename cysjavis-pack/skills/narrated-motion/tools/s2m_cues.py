#!/usr/bin/env python3
"""대본(script.json) → 문장(큐)별 무료 내레이션 + 시각표.

  python3 s2m_cues.py <프로젝트폴더>            # script.json 을 읽어 아래를 만든다
  python3 s2m_cues.py <프로젝트폴더> --check    # 만들지 않고 큐·길이만 출력

만드는 것(프로젝트 폴더 안):
  audio/cues/<id>.wav   큐 하나 = 문장 하나(48 kHz · 모노 · 앞뒤 무음을 잘라 낸 것)
  audio/narration.wav   leadIn + (큐 + gapAfter)… + tail — 영상 0초 = 이 파일 0초
  cues.json             [{id, text, say, start, end, dur}] · duration — 측정값(샘플 수 ÷ 48000)
  js/cues.js            window.CUES = […]; window.DURATION = … (페이지가 file:// 로 읽는다)
  narration.srt         자막(큐 = 한 줄)
  script.txt            대본 글자만(큐 하나 = 한 줄 · 처음 듣는 사람 검토용)
  synth-manifest.json   엔진·목소리·빠르기·큐별 sha256(재현용)

목소리(무료만):
  say  (기본) macOS 내장 · 기기 밖으로 아무것도 나가지 않는다 · 목소리 기본 "Yuna (Premium)"
  edge (선택) edge-tts(설치돼 있을 때) · 무료지만 문장이 마이크로소프트 서버로 간다 → 개인정보 대본 금지
  ⛔ 유료 API(ElevenLabs·Fish Audio 등)는 이 도구가 부르지 않는다 — 쓰려면 별도 게이트(cost-preview-confirm).

규칙: 시각은 LLM 이 듣고 적지 않는다. 합성된 파일의 샘플 수로만 정한다(결정론).
      같은 문장·같은 엔진·같은 목소리·같은 빠르기면 다시 합성하지 않는다(audio/.cache).
"""
import array
import hashlib
import json
import os
import shutil
import subprocess
import sys
import wave

# 윈도에서 출력 캡처 자식의 콘솔 창을 숨긴다(test_nowin_captured_spawns 규칙)
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

SR = 48000
TRIM_DBFS = -45.0      # 이보다 작은 소리는 앞뒤 무음으로 보고 잘라 낸다
TRIM_KEEP = 0.03       # 잘라 낸 뒤 앞뒤로 남겨 두는 여유(초) — 자음 첫소리 보호


def sh(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, **NOWIN)


def synth(engine, voice, rate, text, out_wav):
    tmp = out_wav + ".src"
    if engine == "say":
        sh(["say", "-v", voice, "-r", str(rate), "-o", tmp + ".aiff", text])
        src = tmp + ".aiff"
    elif engine == "edge":
        if not shutil.which("edge-tts"):
            sys.exit("실패 edge-tts 가 없다 — say 를 쓰거나 설치는 master 게이트")
        sh(["edge-tts", "--voice", voice, "--text", text, "--write-media", tmp + ".mp3"])
        src = tmp + ".mp3"
    else:
        sys.exit("실패 엔진은 say | edge 만(무료 경로)")
    sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", out_wav])
    os.remove(src)


def read_pcm(path):
    with wave.open(path) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2, path
        a = array.array("h")
        a.frombytes(w.readframes(w.getnframes()))
    return a


def write_pcm(path, a):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(a.tobytes())


def trim(a):
    thr = 32768 * 10 ** (TRIM_DBFS / 20)
    win = SR // 100
    loud = [i for i in range(0, len(a), win) if max(abs(x) for x in a[i:i + win]) > thr]
    if not loud:
        return a
    keep = int(TRIM_KEEP * SR)
    s = max(0, loud[0] - keep)
    e = min(len(a), loud[-1] + win + keep)
    return a[s:e]


def srt_time(t):
    ms = int(round(t * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    proj = os.path.abspath(sys.argv[1])
    only_check = "--check" in sys.argv
    sc = json.load(open(os.path.join(proj, "script.json"), encoding="utf-8"))
    v = sc.get("voice", {})
    engine, voice, rate = v.get("engine", "say"), v.get("name", "Yuna (Premium)"), int(v.get("rate", 185))
    lead, tail, gap0 = float(sc.get("leadIn", 0.5)), float(sc.get("tail", 1.0)), float(sc.get("gapAfter", 0.25))
    ids = [c["id"] for c in sc["cues"]]
    if len(set(ids)) != len(ids):
        sys.exit("실패 큐 id 중복")
    for d in ("audio/cues", "audio/.cache", "js"):
        os.makedirs(os.path.join(proj, d), exist_ok=True)

    cues, pieces, t, manifest = [], [array.array("h", [0] * int(lead * SR))], lead, []
    for c in sc["cues"]:
        say = c.get("say") or c["text"]
        key = hashlib.sha256(f"{engine}|{voice}|{rate}|{say}".encode()).hexdigest()[:16]
        cache = os.path.join(proj, "audio/.cache", key + ".wav")
        if not os.path.exists(cache):
            if only_check:
                print(f"{c['id']} (아직 합성 안 됨) {c['text']}")
                continue
            synth(engine, voice, rate, say, cache)
        a = trim(read_pcm(cache))
        cue_wav = os.path.join(proj, "audio/cues", c["id"] + ".wav")
        if not only_check:
            write_pcm(cue_wav, a)
        dur = len(a) / SR
        gap = float(c.get("gapAfter", gap0))
        cues.append({"id": c["id"], "text": c["text"], "say": say, "start": round(t, 4), "end": round(t + dur, 4),
                     "dur": round(dur, 4), "gapAfter": gap})
        manifest.append({"id": c["id"], "cache": key, "sha256": hashlib.sha256(a.tobytes()).hexdigest()})
        pieces += [a, array.array("h", [0] * int(round(gap * SR)))]
        t += dur + gap
    pieces.append(array.array("h", [0] * int(tail * SR)))
    total = sum(len(p) for p in pieces) / SR
    for c in cues:
        print(f"{c['id']}  {c['start']:7.3f} → {c['end']:7.3f}  ({c['dur']:.3f}s)  {c['text']}")
    print(f"전체 {total:.3f}s · 큐 {len(cues)} · 엔진 {engine} · 목소리 {voice} · 빠르기 {rate}")
    if only_check:
        return
    nar = array.array("h")
    for p in pieces:
        nar.extend(p)
    write_pcm(os.path.join(proj, "audio/narration.wav"), nar)
    out = {"title": sc.get("title", ""), "duration": round(total, 4), "leadIn": lead, "tail": tail,
           "engine": engine, "voice": voice, "rate": rate, "cues": cues}
    json.dump(out, open(os.path.join(proj, "cues.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(proj, "js/cues.js"), "w", encoding="utf-8") as f:
        f.write("// s2m_cues.py 가 만든 파일 — 손으로 고치지 않는다(script.json 을 고치고 다시 실행)\n")
        f.write("window.CUES = " + json.dumps([{k: c[k] for k in ("id", "text", "start", "end")} for c in cues],
                                              ensure_ascii=False) + ";\n")
        f.write(f"window.DURATION = {round(total, 4)};\n")
    with open(os.path.join(proj, "narration.srt"), "w", encoding="utf-8") as f:
        for i, c in enumerate(cues):
            f.write(f"{i + 1}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n")
    with open(os.path.join(proj, "script.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(c["text"] for c in cues) + "\n")
    json.dump({"engine": engine, "voice": voice, "rate": rate, "sr": SR, "trim_dbfs": TRIM_DBFS, "cues": manifest,
               "narration_sha256": hashlib.sha256(nar.tobytes()).hexdigest()},
              open(os.path.join(proj, "synth-manifest.json"), "w"), indent=1)
    print("완료 audio/narration.wav · cues.json · js/cues.js · narration.srt · script.txt · synth-manifest.json")


if __name__ == "__main__":
    main()
