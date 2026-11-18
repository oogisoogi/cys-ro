#!/usr/bin/env python3
"""javis_idle_gate.py — 사용자 입력 유휴 관문 (TICKET=cysr-no-hands-gui-1118 · 1.1.16).

왜: 자비스가 앱을 앞으로 부르거나 키·클릭을 보내는 순간 사용자가 다른 앱에서 타이핑 중이면 그 키가 엉뚱한 문서·창으로 샌다
(10-25 한글을 앞으로 부른 순간 타이핑이 문서·저장 창에 들어감 「것죄은」 · 10-28 키 보내기가 맨 앞 카톡 답글 창으로 샐 뻔).
그렇다고 사용자에게 손을 비켜 달라고 하면 자비스를 쓰는 뜻이 사라진다. 그래서 **기계가 기다린다** — 사용자 키보드·마우스가
정한 초만큼 쉬었을 때만 화면 작업을 하고, 도중에 다시 손을 대면 멈췄다가 이어 한다. 못 기다리면 실패가 아니라 대기열이다.

이 관문이 필요한 것 = 입력을 건드리는 조작만(앱을 앞으로 부르기 · 키 보내기 · 픽셀 클릭 · 창 끌기 · 끝의 원래 앱 복귀).
셸·파일·설정·한글 파일 도구(hwp·rhwp-edit)·포커스를 안 건드리는 접근성 동작은 관문 없이 한다.

동사(모두 stdout 에 JSON 한 줄 · 사용자에게 묻지 않는다):
  idle                               지금 유휴 초(맥 ioreg HIDIdleTime · 윈 GetLastInputInfo)
  wait --seconds 20 --timeout 90 [--task "<한 줄>"] [--est N] [--target "<대상 앱>"] [--step-quiet Q]
                                     유휴 ≥ seconds 를 기다림 → go(exit 0 · sid · 시작 알림 say) / 시간 초과 → 미룸(exit 3 · 대기열)
                                     --target 이 카카오톡·메일·한글이면 매 동작 전 내 입력까지 포함해 20초(앱별 쉼 상향표 · 그 밖 0)
  mark --sid S                       「방금 내 화면 동작이 끝났다」 기록(다음 check 의 기준점) — 동작 직후 곧바로
  check --sid S [--timeout 90]       다음 화면 동작 직전 — mark 뒤 입력이 하나라도 있었으면 멈추고 다시 유휴를 기다린다
  end --sid S [--restore]            화면 작업 끝(끝 알림 say) · --restore = 시작 때 맨 앞이던 앱으로 되돌림(맥 · mark 뒤 입력 0 일 때만)
  pending                            미룬 화면 작업 목록(자동으로 버리지 않는다)
  done --id <ID>                     미룬 작업 하나를 목록에서 지움

exit: 0 진행 · 2 사용 오류(sid 없음·다름 등) · 3 미룸(대기열 · 실패 아님) · 4 유휴를 잴 수 없음 · 5 다른 화면 작업 진행 중

★결정론·보수 판정(codex 1R 반영):
  · 유휴는 OS 값만 · 못 읽으면 쉬지 않은 것(fail-closed).
  · 시각 비교는 단조 시계(time.monotonic)로 한다 — 벽시계 조정에 흔들리지 않는다. 세션에 「벽시계−단조」 차를 적어 두고
    다른 프로세스에서 그 차가 2초 넘게 다르면(재부팅·시계 기준 변경) 그 사이 입력을 모르는 것으로 보고 다시 기다린다.
  · 「마지막 입력 시각」은 관측한 값 중 가장 늦은 것(최고값)을 세션에 이어 쓴다 — 윈도우 SendInput 이 옛 틱을 넣어 값이
    뒤로 가도(MS 문서) 이미 본 사용자 입력이 지워지지 않는다. 관측 간격 ≤ 1초.
  · 자비스 자신의 키·클릭도 OS 유휴 시계를 0 으로 돌릴 수 있다 → 동작 직후 mark, 다음 동작 전 check 가 「mark 뒤 입력 1개라도」를
    사용자 입력으로 본다(여유 0 · 늦게 반영된 내 입력을 사용자 입력으로 오인하는 쪽 = 멈췄다 다시 기다림 = 안전 쪽).
    ⚠ 잔여(숨기지 않는다 · master#18af38d1 조건 1): 내 동작이 끝난 순간 ~ mark 사이에 사용자가 한 번 치고 멈춘 입력은 내 입력과
      구분하지 못해 그대로 진행할 수 있다(계속 치는 입력은 mark 뒤까지 이어져 잡힌다) — mark 는 동작 직후 곧바로 부른다.
      Return 한 번이 바깥으로 나가는 앱(카카오톡·메일·한글)은 앱별 쉼 상향표로 매 동작 전 20초(내 입력 포함)라 이 틈이 없다.
  · go 직전 준비(맨 앞 앱 기록 · 알림)가 끝난 뒤 다시 확인한다 — 준비 중 입력이 있으면 go 하지 않고 계속 기다린다.
  · 화면 작업은 한 번에 하나(세션 sid · 잠금) · 대기열 쓰기는 잠금 안에서.
★시험: CYS_IDLE_GATE_FAKE = 가짜 시계 JSON 파일({"now": 초, "inputs": [입력 시각…]}) — 실제 대기 0 · 실제 OS 값 0.
"""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
sys.dont_write_bytecode = True
import time

NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_SECONDS = 20          # 선례 hancom-front-needs-idle-gate(10-25) — 키보드·마우스 유휴 20초
DEFAULT_TIMEOUT = 90          # 마스터 Bash 도구 기본 시간 상한(120초) 안
MAX_TIMEOUT = 540
POLL_MIN = 0.2
POLL_MAX = 1.0                # 관측 간격 상한 — 최고값 추적이 입력을 놓치지 않게
CLOCK_SKEW = 2.0              # 프로세스 사이 「벽시계−단조」 차 허용(초)
SESSION_TTL = 900             # 이보다 오래된 세션은 버려진 것으로 본다(초 · 단조)
SUBPROC_TIMEOUT = 5
REGRESS = 1.0                 # OS 마지막 입력 시각이 이만큼 뒤로 가면 역행으로 본다(초)
LOCK_WAIT = 10.0              # 잠금 대기 상한(초) — 넘으면 「다른 화면 작업 진행 중」
MAX_ATTEMPTS = 50             # wait 의 「쉼 → 준비 → 재확인」 되풀이 상한(시계가 안 가는 경우까지 끝나게)
# 앱별 쉼 상향표(master#16466ff6) — Return 한 번이 바깥(남에게)으로 나가는 앱은 매 동작 전 내 입력까지 포함해 20초(엄격) ·
#   그 밖의 앱은 0(관문 1회 → 한 번에 · mark 뒤 입력만 사용자로 판정). 대상 이름·번들 ID 를 소문자로 낱말 대조.
STEP_QUIET_TABLE = (
    (("kakao", "카카오"), 20.0),                                    # 카카오톡(맥 com.kakao.KakaoTalkMac · 윈 KakaoTalk.exe)
    (("com.apple.mail", "outlook", "메일", "mail"), 20.0),          # 메일
    (("hancom", "hwp", "한글", "hnc"), 20.0),                       # 한글(한컴오피스)
)


# ───────────────────────── 시계 · 유휴 원천 ─────────────────────────
def _fake_path():
    return os.environ.get("CYS_IDLE_GATE_FAKE")


def _fake_load():
    with open(_fake_path(), encoding="utf-8") as f:
        return json.load(f)


def _fake_save(d):
    p = _fake_path()
    tmp = "%s.tmp-%d" % (p, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.replace(tmp, p)


def mono():
    """비교용 시각(단조)."""
    if _fake_path():
        return float(_fake_load()["now"])
    return time.monotonic()


def wall():
    """표시·시계 기준 검사용 벽시계."""
    if _fake_path():
        d = _fake_load()
        return float(d["now"]) + float(d.get("wall_skew", 0))
    return time.time()


def sleep(sec):
    if sec <= 0:
        return
    if _fake_path():
        d = _fake_load()
        d["now"] = float(d["now"]) + sec
        _fake_save(d)
        return
    time.sleep(sec)


def platform():
    p = os.environ.get("CYS_IDLE_PLATFORM")
    if p:
        return p
    if sys.platform == "darwin":
        return "darwin"
    if os.name == "nt":
        return "win"
    return "other"


def _run(argv):
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=SUBPROC_TIMEOUT, **NOWIN)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", errors="replace")


_HID = re.compile(r'"HIDIdleTime"\s*=\s*(\d+)')


def parse_hid_idle(text):
    """ioreg 출력 → 유휴 초(HIDIdleTime = 나노초). 못 찾으면 None."""
    m = _HID.search(text or "")
    if not m:
        return None
    return int(m.group(1)) / 1e9


def mac_idle_secs():
    """맥 — IOHIDSystem 의 HIDIdleTime(마지막 키보드·마우스 입력 뒤 나노초). 실패 = None."""
    return parse_hid_idle(_run(["/usr/sbin/ioreg", "-c", "IOHIDSystem", "-r", "-k", "HIDIdleTime", "-d", "1"]))


def win_idle_secs(user32=None, kernel32=None):
    """윈 — GetLastInputInfo(이 세션 마지막 입력 틱) 와 GetTickCount 의 차(밀리초 · 32비트 감김 보정). 실패 = None.
    값이 뒤로 가는 경우(SendInput 이 옛 틱을 넣음 · MS 문서)는 호출부의 최고값 추적이 막는다.
    user32·kernel32 는 시험이 가짜를 넣는 자리다."""
    try:
        import ctypes
        from ctypes import wintypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        if user32 is None:
            user32 = ctypes.windll.user32
        if kernel32 is None:
            kernel32 = ctypes.windll.kernel32
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not user32.GetLastInputInfo(ctypes.byref(lii)):
            return None
        tick = int(kernel32.GetTickCount()) & 0xFFFFFFFF
        return ((tick - int(lii.dwTime)) & 0xFFFFFFFF) / 1000.0
    except Exception:
        return None


def idle_secs():
    """지금 유휴 초 · 못 읽으면 None(= 쉬고 있다고 치지 않는다)."""
    if _fake_path():
        d = _fake_load()
        if d.get("broken"):
            return None
        if d.get("idle_override"):          # 시험: OS 값이 뒤로 가는 경우(윈 SendInput 옛 틱) — 한 번씩 꺼내 쓴다
            v = d["idle_override"].pop(0)
            _fake_save(d)
            return None if v is None else float(v)
        t = float(d["now"])
        past = [float(x) for x in d.get("inputs", []) if float(x) <= t]
        return t - max(past) if past else t
    plat = platform()
    if plat == "darwin":
        return mac_idle_secs()
    if plat == "win":
        return win_idle_secs()
    return None


def observe(hi=None, raw=None):
    """(마지막 입력 시각(단조) | None, 이번 원시값 | 직전 원시값).
    마지막 입력 = 이번 관측과 이전 최고값(hi) 중 늦은 것 · 못 읽으면 None.
    순서 = 유휴를 읽은 **뒤** 시각을 잰다(마지막 입력을 늦게 잡는 쪽 = 「입력 있었다」 쪽으로 기운다).
    OS 원시값이 **직전 원시값**보다 REGRESS 초 넘게 뒤로 가면(윈 SendInput 옛 틱 · MS 문서) 그 사이 입력을 가렸을 수 있으므로
    「지금 막 입력이 있었다」로 본다(codex 2R) — 뒤로 간 값이 그대로 머물면 다음 관측부터는 역행이 아니다(영구 정지 방지)."""
    idle = idle_secs()
    t = mono()
    if idle is None:
        return None, raw
    cur = t - idle
    if raw is not None and cur < float(raw) - REGRESS:
        return t, cur
    return (max(cur, float(hi)) if hi is not None else cur), cur


def front_app():
    """맨 앞 앱(되돌리기용 · 맥 = 번들 ID). 묻는 창 0(lsappinfo 는 자동화 허락이 필요 없다). 실패 = None."""
    if _fake_path():
        d = _fake_load()
        if d.get("input_on_front"):            # 시험: 준비 도중 사용자 입력
            d["input_on_front"] = False
            d.setdefault("inputs", []).append(d["now"])
            _fake_save(d)
        return d.get("front")
    if platform() != "darwin":
        return None
    asn = _run(["/usr/bin/lsappinfo", "front"])
    if not asn or not asn.strip():
        return None
    info = _run(["/usr/bin/lsappinfo", "info", "-only", "bundleid", asn.strip()])
    m = re.search(r'"CFBundleIdentifier"\s*=\s*"([^"]+)"', info or "")
    return m.group(1) if m else None


def activate(bundle):
    """원래 앱으로 되돌리기(맥). 시험에서는 실행하지 않고 기록만."""
    if _fake_path():
        d = _fake_load()
        d["activated"] = bundle
        _fake_save(d)
        return True
    if platform() != "darwin":
        return False
    return _run(["/usr/bin/open", "-b", bundle]) is not None


def notify(text):
    """사용자가 다른 앱에 있어도 보이는 알림 1줄(맥 알림 센터 · 포커스를 가져가지 않는다). 최선 노력 · 실패해도 진행."""
    if _fake_path() or os.environ.get("CYS_IDLE_NO_NOTIFY"):
        return False
    if platform() != "darwin":
        return False
    s = text.replace("\\", "\\\\").replace('"', '\\"')
    return _run(["/usr/bin/osascript", "-e", 'display notification "%s" with title "cysr"' % s]) is not None


# ───────────────────────── 상태(세션 · 대기열 · 잠금) ─────────────────────────
def state_dir():
    return os.environ.get("CYS_IDLE_STATE") or os.path.join(os.path.expanduser("~"), ".cys", "computer-control")


def _p(name):
    return os.path.join(state_dir(), name)


def _read(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.tmp-%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


SESSION = "idle-session.json"
PENDING = "idle-pending.json"


class LockBusy(Exception):
    pass


@contextlib.contextmanager
def locked():
    """세션·대기열 읽고-고쳐-쓰기를 한 번에 한 프로세스만(맥 flock · 윈 msvcrt) · 대기 상한 LOCK_WAIT → LockBusy."""
    os.makedirs(state_dir(), exist_ok=True)
    f = open(_p("idle-gate.lock"), "a+b")
    deadline = time.monotonic() + LOCK_WAIT
    got = False
    try:
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                got = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise LockBusy()
                time.sleep(0.05)
        yield
    finally:
        try:
            if got:
                if os.name == "nt":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        finally:
            f.close()


def _iso(t):
    return datetime.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")


def _task_id(task):
    return hashlib.sha256((task or "").strip().encode("utf-8")).hexdigest()[:10]


def step_quiet_for(target):
    """대상 앱 → 매 동작 전 쉼(초). 표에 없으면 0."""
    t = (target or "").lower()
    for words, q in STEP_QUIET_TABLE:
        if any(w in t for w in words):
            return q
    return 0.0


def _session_raw():
    s = _read(_p(SESSION), None)
    return s if isinstance(s, dict) and "sid" in s and "mark" in s else None


def _clock_ok(s):
    """세션을 쓴 프로세스와 지금의 「벽시계−단조」 차가 같은가(재부팅·시계 기준 변경 검출)."""
    return abs((wall() - mono()) - float(s.get("offset", 0))) <= CLOCK_SKEW


def _active(s):
    """살아 있는 세션인가 — 소유자가 마지막으로 부른 뒤 SESSION_TTL 안(codex 2R: 입력 판정의 불확실성과 소유권을 분리 —
    시계 기준이 바뀌어도 소유권은 풀지 않고, 그때는 벽시계로 나이를 잰다)."""
    if s is None:
        return False
    if _clock_ok(s):
        age = mono() - float(s.get("seen_mono", s["mark"]))
    else:
        age = wall() - float(s.get("seen_wall", 0))
    return age <= SESSION_TTL


def _touch_seen(s):
    s["seen_mono"] = mono()
    s["seen_wall"] = wall()


def _defer_locked(task, reason):
    """대기열에 올림(같은 일은 한 줄 · 자동으로 버리지 않는다). 잠금 안에서 부른다."""
    items = _read(_p(PENDING), [])
    if not isinstance(items, list):
        items = []
    tid = _task_id(task)
    if task and not any(isinstance(i, dict) and i.get("id") == tid for i in items):
        items.append({"id": tid, "task": task[:300], "at": _iso(wall()), "reason": reason})
        _write(_p(PENDING), items)
    return tid


def _drop_session_locked(sid=None):
    s = _session_raw()
    if s is not None and (sid is None or s.get("sid") == sid):
        try:
            os.remove(_p(SESSION))
        except OSError:
            pass


# ───────────────────────── 관문 ─────────────────────────
def wait_quiet(seconds, timeout, hi=None, raw=None):
    """마지막 입력 뒤 seconds 가 지날 때까지 기다린다. (go, 유휴 초|None, 기다린 초, 마지막 입력 최고값|None, 원시값).
    못 읽는 값은 쉬지 않은 것으로 본다 · 관측 간격 ≤ POLL_MAX(최고값 추적)."""
    start = mono()
    deadline = start + timeout
    while True:
        last, raw = observe(hi, raw)
        if last is not None:
            hi = last
        t = mono()
        if last is not None and t - last >= seconds:
            return True, t - last, t - start, hi, raw
        if t >= deadline:
            return False, (None if last is None else t - last), t - start, hi, raw
        need = (seconds - (t - last)) if last is not None else POLL_MAX
        sleep(max(POLL_MIN, min(need, POLL_MAX, deadline - t)))


def touched(sess):
    """다음 입력 동작을 해도 되는가의 반대 — (touched, 최고값, 원시값).
    ① mark 뒤 입력 1개라도(여유 0 · 늦게 반영된 내 입력도 사용자로 = 멈췄다 다시 기다림 = 안전 쪽)
    ② 대상 앱의 쉼 상향(step_quiet > 0): 내 입력까지 포함해 마지막 입력 뒤 step_quiet 초가 안 지났으면
    ③ 못 읽거나 시계 기준이 바뀌었으면."""
    if not _clock_ok(sess):
        return True, sess.get("hi"), sess.get("raw")
    last, raw = observe(sess.get("hi"), sess.get("raw"))
    if last is None:
        return True, sess.get("hi"), raw
    q = float(sess.get("step_quiet", 0) or 0)
    return (last > float(sess["mark"])) or (q > 0 and mono() - last < q), last, raw


def out(obj, rc=0):
    print(json.dumps(obj, ensure_ascii=False))
    return rc


START_SAY = "잠깐 화면을 씁니다(약 %d초). 하시던 일은 그대로 하셔도 됩니다 — 키보드나 마우스를 쓰시면 제가 멈췄다가 쉬실 때 이어 합니다."
DEFER_SAY = ("지금은 컴퓨터를 쓰고 계셔서 화면이 필요한 일은 나중에 하겠습니다(대기열에 올려 두었습니다). "
             "파일로 할 수 있는 일은 먼저 진행합니다.")
END_SAY = "화면 쓰기를 마쳤습니다(%d초)."
NO_IDLE_SAY = "이 컴퓨터에서는 키보드·마우스 쉼을 잴 수 없어 화면이 필요한 일은 하지 않고 미뤄 두겠습니다."
BUSY_SAY = "다른 화면 작업이 진행 중입니다 — 그것이 끝난 뒤 이어 하겠습니다."


def _timeout(v):
    return max(0.0, min(float(v), MAX_TIMEOUT))


def _busy():
    return out({"ok": False, "reason": "busy", "say": BUSY_SAY}, 5)


def cmd_idle(a):
    v = idle_secs()
    if v is None:
        return out({"ok": False, "reason": "idle_unknown", "platform": platform()}, 4)
    return out({"ok": True, "idle_secs": round(v, 1), "platform": platform()})


def _deferred(task, reason, waited, idle=None, sid=None):
    with locked():
        tid = _defer_locked(task, reason)
        if sid is not None:
            _drop_session_locked(sid)
    return out({"ok": True, "go": False, "deferred": True, "id": tid, "reason": reason,
                "idle_secs": None if idle is None else round(idle, 1), "waited_secs": round(waited, 1),
                "say": NO_IDLE_SAY if reason == "unsupported_platform" else DEFER_SAY}, 3)


def cmd_wait(a):
    if platform() not in ("darwin", "win") and not _fake_path():
        return _deferred(a.task, "unsupported_platform", 0.0)
    with locked():
        if _active(_session_raw()):
            return _busy()
    start = mono()
    deadline = start + _timeout(a.timeout)        # 명령 전체 하나의 단조 마감(codex 2R)
    q = a.step_quiet if a.step_quiet is not None else step_quiet_for(a.target)
    say = START_SAY % max(1, int(a.est))
    notified = None
    hi = raw = None
    last_idle = None
    for _attempt in range(MAX_ATTEMPTS):
        go, idle, _w, hi, raw = wait_quiet(a.seconds, max(0.0, deadline - mono()), hi, raw)
        last_idle = idle
        if not go:
            break
        front = front_app()                     # 준비(맨 앞 앱 기록 · 알림)는 go 판정 뒤 — 끝나고 잠금 안에서 다시 확인한다
        if notified is None:
            notified = notify(say)
        with locked():
            if _active(_session_raw()):
                return _busy()
            last, raw = observe(hi, raw)        # 잠금을 잡은 **뒤** 다시 관측 · 반환 시각도 그 뒤(codex 2R)
            t = mono()
            if last is not None and t - last >= a.seconds:
                sid = secrets.token_hex(4)
                sess = {"sid": sid, "go_at": t, "mark": t, "hi": last, "raw": raw, "offset": wall() - t, "seconds": a.seconds,
                        "step_quiet": q, "target": a.target or "", "front": front, "task": a.task or "", "pauses": 0}
                _touch_seen(sess)
                _write(_p(SESSION), sess)
                if a.task:
                    items = _read(_p(PENDING), [])
                    if isinstance(items, list):
                        keep = [i for i in items if not (isinstance(i, dict) and i.get("id") == _task_id(a.task))]
                        if len(keep) != len(items):
                            _write(_p(PENDING), keep)
                return out({"ok": True, "go": True, "sid": sid, "idle_secs": round(t - last, 1),
                            "waited_secs": round(t - start, 1), "step_quiet": q, "front_app": front,
                            "notified": bool(notified), "say": say})
            hi = last if last is not None else hi   # 준비 중 입력(또는 못 읽음) → go 하지 않고 계속 기다린다
            last_idle = None if last is None else t - last
        if mono() >= deadline:
            break
    return _deferred(a.task, "idle_unknown" if last_idle is None else "user_active", mono() - start, last_idle)


def _owned(a):
    s = _session_raw()
    if s is None:
        return None, out({"ok": False, "reason": "no_session", "say": "먼저 wait 로 관문을 통과해야 합니다."}, 2)
    if s.get("sid") != a.sid:
        return None, out({"ok": False, "reason": "not_owner", "say": "이 화면 작업의 세션이 아닙니다."}, 2)
    return s, None


def cmd_mark(a):
    with locked():
        s, err = _owned(a)
        if err is not None:
            return err
        last, raw = observe(s.get("hi"), s.get("raw"))   # 내 동작의 입력 시각까지 넣어 둔다(뒤의 역행 검출 기준)
        t = mono()
        s["mark"] = t
        s["raw"] = raw
        if last is not None:
            s["hi"] = last
        _touch_seen(s)
        _write(_p(SESSION), s)
    return out({"ok": True})


def cmd_check(a):
    with locked():
        s, err = _owned(a)
        if err is not None:
            return err
        _touch_seen(s)
        _write(_p(SESSION), s)
    hit, hi, raw = touched(s)
    if not hit:
        with locked():
            s2, err = _owned(a)
            if err is not None:
                return err
            s2["hi"] = hi
            s2["raw"] = raw
            _write(_p(SESSION), s2)
        return out({"ok": True, "go": True, "touched": False})
    seconds = a.seconds if a.seconds is not None else float(s.get("seconds", DEFAULT_SECONDS))
    go, idle, waited, hi, raw = wait_quiet(seconds, _timeout(a.timeout), hi, raw)
    if not go:
        return _deferred(s.get("task") or "", "idle_unknown" if idle is None else "user_active", waited, idle, sid=a.sid)
    with locked():
        s2, err = _owned(a)
        if err is not None:
            return err
        t = mono()
        s2.update(mark=t, hi=hi, raw=raw, offset=wall() - t, pauses=int(s2.get("pauses", 0)) + 1)   # 재개 = 새 기준점
        _touch_seen(s2)
        _write(_p(SESSION), s2)
    return out({"ok": True, "go": True, "touched": True, "resumed": True, "paused_secs": round(waited, 1)})


def cmd_end(a):
    with locked():
        s, err = _owned(a)
        if err is not None:
            return err
    restored, why = None, None
    if a.restore:
        cur = front_app() if s.get("front") else None   # 앱 조회를 먼저 끝내고 — 복귀 직전에 입력·소유권을 다시 본다(codex 2R)
        with locked():
            s2, err = _owned(a)
            if err is not None:
                return err
            hit, _hi, _raw = touched(s2)
            if not s2.get("front"):
                restored, why = False, "no_front"
            elif hit:
                restored, why = False, "user_active"   # 복귀도 입력 조작 — 사용자가 손을 댔으면 끌어오지 않는다
            elif cur == s2["front"]:
                restored, why = True, "same_app"
            else:
                restored = activate(s2["front"])
                why = "activated" if restored else "activate_failed"
    used = int(round(mono() - float(s["go_at"]))) if _clock_ok(s) else None
    with locked():
        _drop_session_locked(a.sid)
    say = END_SAY % (used or 0)
    return out({"ok": True, "ended": True, "used_secs": used, "pauses": int(s.get("pauses", 0)),
                "restored": restored, "restore_reason": why, "notified": notify(say), "say": say})


def cmd_pending(a):
    with locked():
        items = _read(_p(PENDING), [])
    items = items if isinstance(items, list) else []
    return out({"ok": True, "count": len(items), "items": items})


def cmd_done(a):
    with locked():
        items = _read(_p(PENDING), [])
        items = items if isinstance(items, list) else []
        keep = [i for i in items if not (isinstance(i, dict) and i.get("id") == a.id)]
        if len(keep) == len(items):
            return out({"ok": False, "reason": "not_found"}, 4)
        _write(_p(PENDING), keep)
    return out({"ok": True, "removed": a.id})


def main(argv=None):
    ap = argparse.ArgumentParser(prog="javis_idle_gate.py")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("idle")
    w = sp.add_parser("wait")
    w.add_argument("--seconds", type=float, default=DEFAULT_SECONDS)
    w.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    w.add_argument("--task", default="")
    w.add_argument("--est", type=float, default=10)
    w.add_argument("--target", default="", help="화면 조작 대상 앱(이름·번들 ID) — 앱별 쉼 상향표에 쓴다")
    w.add_argument("--step-quiet", type=float, default=None, help="매 동작 전 쉼(초) — 주면 표보다 우선")
    m = sp.add_parser("mark")
    m.add_argument("--sid", required=True)
    c = sp.add_parser("check")
    c.add_argument("--sid", required=True)
    c.add_argument("--seconds", type=float, default=None)
    c.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    e = sp.add_parser("end")
    e.add_argument("--sid", required=True)
    e.add_argument("--restore", action="store_true")
    sp.add_parser("pending")
    d = sp.add_parser("done")
    d.add_argument("--id", required=True)
    a = ap.parse_args(argv)
    try:
        return {"idle": cmd_idle, "wait": cmd_wait, "mark": cmd_mark, "check": cmd_check, "end": cmd_end,
                "pending": cmd_pending, "done": cmd_done}[a.cmd](a)
    except LockBusy:
        return _busy()


if __name__ == "__main__":
    sys.exit(main())
