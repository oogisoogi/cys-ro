#!/usr/bin/env python3
"""javis_idle_gate.py — 사용자 입력 유휴 관문 (TICKET=cysr-no-hands-gui-1118 · 1.1.16).

왜: 자비스가 앱을 앞으로 부르거나 키·클릭을 보내는 순간 사용자가 다른 앱에서 타이핑 중이면 그 키가 엉뚱한 문서·창으로 샌다
(10-25 한글을 앞으로 부른 순간 타이핑이 문서·저장 창에 들어감 「것죄은」 · 10-28 키 보내기가 맨 앞 카톡 답글 창으로 샐 뻔).
그렇다고 사용자에게 손을 비켜 달라고 하면 자비스를 쓰는 뜻이 사라진다. 그래서 **기계가 기다린다** — 사용자 키보드·마우스가
정한 초만큼 쉬었을 때만 화면 작업을 하고, 도중에 다시 손을 대면 멈췄다가 이어 한다. 못 기다리면 실패가 아니라 대기열이다.

이 관문이 필요한 것 = 입력을 건드리는 조작만(앱을 앞으로 부르기 · 키 보내기 · 픽셀 클릭 · 창 끌기).
셸·파일·설정·한글 파일 도구(hwp·rhwp-edit)·포커스를 안 건드리는 접근성 동작은 관문 없이 한다.

동사(모두 stdout 에 JSON 한 줄 · 사용자에게 묻지 않는다):
  idle                               지금 유휴 초(맥 ioreg HIDIdleTime · 윈 GetLastInputInfo)
  wait --seconds 20 --timeout 90 [--task "<한 줄>"] [--est N]
                                     유휴 ≥ seconds 를 기다림 → go(exit 0 · 시작 알림 say) / 시간 초과 → 미룸(exit 3 · 대기열)
  mark                               「방금 내가 한 화면 동작이 끝났다」 기록(다음 check 의 기준점)
  check [--seconds 20 --timeout 90]  다음 화면 동작 직전 — 마지막 mark 뒤 사용자 입력이 있었으면 멈추고 다시 유휴를 기다린다
  end [--restore]                    화면 작업 끝(끝 알림 say) · --restore = 시작 때 맨 앞이던 앱으로 되돌림(맥)
  pending                            미룬 화면 작업 목록
  done --id <ID>                     미룬 작업 하나를 목록에서 지움

exit: 0 진행 · 2 사용 오류(wait 없이 check 등) · 3 미룸(대기열 · 실패 아님) · 4 이 컴퓨터에서 유휴를 잴 수 없음

★결정론: 유휴 판정은 OS 값만 쓴다 — 값을 못 읽으면 「쉬고 있다」로 치지 않는다(fail-closed · 미룸).
★내 동작과 사용자 입력 구분: 자비스의 키·클릭도 OS 유휴 시계를 0 으로 되돌린다. 그래서 동작 직후 mark 를 찍고, 다음 동작 전
  check 가 「유휴 초 < mark 뒤 흐른 초」(= mark 뒤에 누군가 입력)를 사용자 입력으로 본다.
★시험: CYS_IDLE_GATE_FAKE = 가짜 시계 JSON 파일({"now": 초, "inputs": [입력 시각…]}) — 실제 대기 0 · 실제 OS 값 0.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
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
GRACE = 0.5                   # 시계 해상도 여유(초) — mark 직후 같은 순간의 입력은 내 동작으로 본다
POLL_MIN = 0.5
SUBPROC_TIMEOUT = 5
MAX_PENDING = 200


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


def now():
    if _fake_path():
        return float(_fake_load()["now"])
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
        t = float(d["now"])
        past = [float(x) for x in d.get("inputs", []) if float(x) <= t]
        if d.get("broken"):
            return None
        return t - max(past) if past else t
    plat = platform()
    if plat == "darwin":
        return mac_idle_secs()
    if plat == "win":
        return win_idle_secs()
    return None


def front_app():
    """시작 때 맨 앞 앱(되돌리기용 · 맥 = 번들 ID). 묻는 창 0(lsappinfo 는 자동화 허락이 필요 없다). 실패 = None."""
    if _fake_path():
        return _fake_load().get("front")
    if platform() != "darwin":
        return None
    asn = _run(["/usr/bin/lsappinfo", "front"])
    if not asn or not asn.strip():
        return None
    info = _run(["/usr/bin/lsappinfo", "info", "-only", "bundleid", asn.strip()])
    m = re.search(r'"CFBundleIdentifier"\s*=\s*"([^"]+)"', info or "")
    return m.group(1) if m else None


def notify(text):
    """사용자가 다른 앱에 있어도 보이는 알림 1줄(맥 알림 센터 · 포커스를 가져가지 않는다). 최선 노력 · 실패해도 진행."""
    if _fake_path() or os.environ.get("CYS_IDLE_NO_NOTIFY"):
        return False
    if platform() != "darwin":
        return False
    s = text.replace("\\", "\\\\").replace('"', '\\"')
    return _run(["/usr/bin/osascript", "-e", 'display notification "%s" with title "cysr"' % s]) is not None


# ───────────────────────── 상태(세션 · 대기열) ─────────────────────────
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


def _iso(t):
    return datetime.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")


def _task_id(task):
    return hashlib.sha256((task or "").strip().encode("utf-8")).hexdigest()[:10]


def defer(task, reason):
    """못 기다린 화면 작업 → 대기열(같은 일은 한 줄) · 세션 정리."""
    items = _read(_p(PENDING), [])
    if not isinstance(items, list):
        items = []
    tid = _task_id(task)
    if task and not any(isinstance(i, dict) and i.get("id") == tid for i in items):
        items.append({"id": tid, "task": task[:300], "at": _iso(now()), "reason": reason})
        _write(_p(PENDING), items[-MAX_PENDING:])
    try:
        os.remove(_p(SESSION))
    except OSError:
        pass
    return tid


def _clear_pending(task):
    if not task:
        return
    items = _read(_p(PENDING), [])
    if isinstance(items, list):
        keep = [i for i in items if not (isinstance(i, dict) and i.get("id") == _task_id(task))]
        if len(keep) != len(items):
            _write(_p(PENDING), keep)


# ───────────────────────── 관문 ─────────────────────────
def wait_idle(seconds, timeout):
    """유휴 ≥ seconds 까지 기다린다. (go, 마지막 유휴 초, 기다린 초). 못 읽는 값(None)은 쉬지 않은 것으로 본다."""
    start = now()
    while True:
        idle = idle_secs()
        if idle is not None and idle >= seconds:
            return True, idle, now() - start
        left = timeout - (now() - start)
        if left <= 0:
            return False, idle, now() - start
        need = (seconds - idle) if idle is not None else 1.0
        sleep(max(POLL_MIN, min(need, left)))


def touched_since_mark(sess):
    """마지막 mark 뒤 입력이 있었는가 — 유휴 초가 mark 뒤 흐른 초보다 짧으면 그 사이 누군가 입력했다. 못 읽으면 True."""
    idle = idle_secs()
    if idle is None:
        return True, None
    return idle + GRACE < now() - float(sess["mark"]), idle


def out(obj, rc=0):
    print(json.dumps(obj, ensure_ascii=False))
    return rc


START_SAY = "잠깐 화면을 씁니다(약 %d초). 하시던 일은 그대로 하셔도 됩니다 — 키보드나 마우스를 쓰시면 제가 멈췄다가 쉬실 때 이어 합니다."
DEFER_SAY = ("지금은 컴퓨터를 쓰고 계셔서 화면이 필요한 일은 나중에 하겠습니다(대기열에 올려 두었습니다). "
             "파일로 할 수 있는 일은 먼저 진행합니다.")
END_SAY = "화면 쓰기를 마쳤습니다(%d초)."
NO_IDLE_SAY = "이 컴퓨터에서는 키보드·마우스 쉼을 잴 수 없어 화면이 필요한 일은 하지 않고 미뤄 두겠습니다."


def _timeout(v):
    return max(0, min(int(v), MAX_TIMEOUT))


def cmd_idle(a):
    v = idle_secs()
    if v is None:
        return out({"ok": False, "reason": "idle_unknown", "platform": platform()}, 4)
    return out({"ok": True, "idle_secs": round(v, 1), "platform": platform()})


def cmd_wait(a):
    if platform() not in ("darwin", "win") and not _fake_path():
        tid = defer(a.task, "unsupported_platform")
        return out({"ok": True, "go": False, "deferred": True, "id": tid, "reason": "unsupported_platform",
                    "say": NO_IDLE_SAY}, 3)
    go, idle, waited = wait_idle(a.seconds, _timeout(a.timeout))
    if not go:
        reason = "idle_unknown" if idle is None else "user_active"
        tid = defer(a.task, reason)
        return out({"ok": True, "go": False, "deferred": True, "id": tid, "reason": reason,
                    "idle_secs": None if idle is None else round(idle, 1), "waited_secs": round(waited, 1),
                    "say": DEFER_SAY}, 3)
    t = now()
    sess = {"go_at": t, "mark": t, "seconds": a.seconds, "front": front_app(), "task": a.task or "", "pauses": 0}
    _write(_p(SESSION), sess)
    _clear_pending(a.task)
    say = START_SAY % max(1, int(a.est))
    return out({"ok": True, "go": True, "idle_secs": round(idle, 1), "waited_secs": round(waited, 1),
                "front_app": sess["front"], "notified": notify(say), "say": say})


def _session():
    s = _read(_p(SESSION), None)
    return s if isinstance(s, dict) and "mark" in s else None


def cmd_mark(a):
    s = _session()
    if s is None:
        return out({"ok": False, "reason": "no_session", "say": "먼저 wait 로 관문을 통과해야 합니다."}, 2)
    s["mark"] = now()
    _write(_p(SESSION), s)
    return out({"ok": True})


def cmd_check(a):
    s = _session()
    if s is None:
        return out({"ok": False, "reason": "no_session", "say": "먼저 wait 로 관문을 통과해야 합니다."}, 2)
    touched, idle = touched_since_mark(s)
    if not touched:
        return out({"ok": True, "go": True, "touched": False, "idle_secs": round(idle, 1)})
    seconds = a.seconds if a.seconds is not None else int(s.get("seconds", DEFAULT_SECONDS))
    go, idle2, waited = wait_idle(seconds, _timeout(a.timeout))
    if not go:
        reason = "idle_unknown" if idle2 is None else "user_active"
        tid = defer(s.get("task") or "", reason)
        return out({"ok": True, "go": False, "touched": True, "deferred": True, "id": tid, "reason": reason,
                    "waited_secs": round(waited, 1), "say": DEFER_SAY}, 3)
    s["mark"] = now()
    s["pauses"] = int(s.get("pauses", 0)) + 1
    _write(_p(SESSION), s)
    return out({"ok": True, "go": True, "touched": True, "resumed": True, "paused_secs": round(waited, 1)})


def cmd_end(a):
    s = _session()
    if s is None:
        return out({"ok": True, "ended": False, "reason": "no_session"})
    used = int(round(now() - float(s["go_at"])))
    restored = None
    if a.restore and s.get("front") and platform() == "darwin" and not _fake_path():
        restored = front_app() == s["front"] or _run(["/usr/bin/open", "-b", s["front"]]) is not None
    try:
        os.remove(_p(SESSION))
    except OSError:
        pass
    say = END_SAY % used
    return out({"ok": True, "ended": True, "used_secs": used, "pauses": int(s.get("pauses", 0)),
                "restored": restored, "notified": notify(say), "say": say})


def cmd_pending(a):
    items = _read(_p(PENDING), [])
    items = items if isinstance(items, list) else []
    return out({"ok": True, "count": len(items), "items": items})


def cmd_done(a):
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
    sp.add_parser("mark")
    c = sp.add_parser("check")
    c.add_argument("--seconds", type=float, default=None)
    c.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    e = sp.add_parser("end")
    e.add_argument("--restore", action="store_true")
    sp.add_parser("pending")
    d = sp.add_parser("done")
    d.add_argument("--id", required=True)
    a = ap.parse_args(argv)
    return {"idle": cmd_idle, "wait": cmd_wait, "mark": cmd_mark, "check": cmd_check, "end": cmd_end,
            "pending": cmd_pending, "done": cmd_done}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
