"""TTS 어댑터(교체형) — 문장 하나 → 오디오 파일 하나(.m4a) + 길이(초).

  ⓐ elevenlabs : 환경변수 ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID 가 있을 때만(팩 규약 suite-runtime-keys).
                 키를 파일에서 읽지 않는다 · 화면·로그에 찍지 않는다 · 가입·결제를 시도하지 않는다.
  ⓑ say        : macOS 내장 한국어 목소리(Yuna) — 맥 전용 대체 수단(초안용). 윈도·리눅스에는 없다.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

# 윈도에서 출력 캡처 자식의 콘솔 창을 숨긴다(test_nowin_captured_spawns 규칙)
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

EL_KEY_URL = "https://elevenlabs.io/app/settings/api-keys"
SAY_VOICE = "Yuna"
SAY_RATE = 190


class Missing(SystemExit):
    """필요한 것이 없어 멈춘다 — 안내를 표준 오류에 찍고 코드 4."""

    def __init__(self, *lines):
        for ln in lines:
            print(ln, file=sys.stderr)
        super().__init__(4)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True, **NOWIN)
    return float(r.stdout.strip())


def _say_ready():
    """맥이고 say 와 Yuna 목소리가 있으면 None, 아니면 안내 줄 목록."""
    if sys.platform != "darwin":
        return ["say 목소리는 맥 전용입니다 — 이 기기에서는 ElevenLabs 키로만 목소리를 만들 수 있다:",
                "  export ELEVENLABS_API_KEY=<당신의 키> ELEVENLABS_VOICE_ID=<목소리 id>  (발급: %s)" % EL_KEY_URL]
    if not shutil.which("say"):
        return ["없음 say(macOS 내장 음성 명령) — 맥 기본 명령이 PATH 에 없다. /usr/bin 이 PATH 에 있는지 확인한다."]
    r = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, **NOWIN)
    if not any(line.split()[:1] == [SAY_VOICE] for line in r.stdout.splitlines()):
        return ["없음 한국어 목소리 %s — 시스템 설정 → 손쉬운 사용 → 읽기 및 말하기 → 시스템 목소리 → 목소리 관리에서 한국어 %s 를 받는다." % (SAY_VOICE, SAY_VOICE)]
    return None


def pick(prefer="auto"):
    """auto = 키가 있으면 elevenlabs, 없으면 맥에서만 say · elevenlabs·say = 그것만(없으면 안내 후 멈춤)."""
    if prefer not in ("auto", "say", "elevenlabs"):
        raise Missing("입력 오류 --tts 는 auto · say · elevenlabs 중 하나: %s" % prefer)
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if prefer == "elevenlabs" or (prefer == "auto" and key):
        if not key:
            raise Missing("ElevenLabs API 키 미설정 — `export ELEVENLABS_API_KEY=<당신의 키>` 후 재시도.", "발급: %s" % EL_KEY_URL)
        if not voice:
            raise Missing("ELEVENLABS_VOICE_ID 미설정 — 쓸 목소리 id 를 `export ELEVENLABS_VOICE_ID=<목소리 id>` 로 넣고 재시도.",
                          "목소리 id: https://elevenlabs.io/app/voice-library")
        return "elevenlabs"
    why = _say_ready()
    if why:
        if prefer == "auto":
            why.append("(ElevenLabs 키가 없어 say 로 내려가려 했다 — 키를 넣으면 say 없이도 된다)")
        raise Missing(*why)
    return "say"


def _say(text, out, voice=SAY_VOICE, rate=SAY_RATE):
    aiff = out[:-4] + ".aiff"
    subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", aiff, text], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", aiff, "-ar", "48000", "-ac", "1", "-c:a", "aac", "-b:a", "160k", out], check=True)
    os.remove(aiff)


EL_SETTINGS = {"stability": 0.5, "similarity_boost": 0.75}


def _el_params():
    """ElevenLabs 결과를 바꾸는 값 전부(키 제외) — 합성 요청과 캐시 이름이 같은 값을 쓴다."""
    return {"voice": os.environ.get("ELEVENLABS_VOICE_ID", "").strip(),
            "model": os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
            "settings": EL_SETTINGS}


def _elevenlabs(text, out):
    key = os.environ["ELEVENLABS_API_KEY"].strip()
    prm = _el_params()
    voice = prm["voice"]
    body = json.dumps({"text": text, "model_id": prm["model"], "voice_settings": prm["settings"]}).encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=mp3_44100_128" % voice,
                                 data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    mp3 = out[:-4] + ".mp3"
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(mp3, "wb") as f:
            f.write(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise Missing("ElevenLabs 가 키를 거절했다(HTTP %d) — ELEVENLABS_API_KEY 값을 확인한다(키는 화면에 찍지 않는다)." % e.code,
                          "발급: %s" % EL_KEY_URL)
        raise Missing("ElevenLabs 호출 실패 HTTP %d — 목소리 id·남은 글자 수를 확인한다." % e.code)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ar", "48000", "-ac", "1", "-c:a", "aac", "-b:a", "160k", out], check=True)
    os.remove(mp3)


def synth(text, outdir, engine):
    """같은 문장·같은 목소리 설정이면 다시 만들지 않는다(문장만 고쳐 재합성할 때 시간 절약).
    캐시 이름에 결과를 바꾸는 값(say = 목소리·속도 · elevenlabs = 목소리 id·모델·voice_settings)을 모두 넣는다 —
    목소리를 바꾼 뒤 옛 소리를 다시 쓰지 않게."""
    prm = {"voice": SAY_VOICE, "rate": SAY_RATE} if engine == "say" else _el_params()
    key = hashlib.sha1((engine + "|" + json.dumps(prm, sort_keys=True) + "|" + text).encode()).hexdigest()[:12]
    out = os.path.join(outdir, "%s-%s.m4a" % (engine, key))
    if not os.path.exists(out):
        (_elevenlabs if engine == "elevenlabs" else _say)(text, out)
    return out, duration(out)
