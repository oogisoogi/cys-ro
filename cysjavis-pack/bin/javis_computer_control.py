#!/usr/bin/env python3
"""javis_computer_control.py — 컴퓨터 통제권 넘기기 (TICKET=cu-1111 · 1.1.11 · 설계 docs/DESIGN-cu-1111.md).

사용자 컴퓨터를 **읽기만** 해서 「마스터가 맡을 수 있는 항목」을 세 칸(바로 가능 / 손 한 번 필요 / 지금은 안 됨)으로
나누고, 사용자가 고른 것만 넘김 장부(grants.json)에 올린다. 손이 필요한 것은 단계 안내 → 다시 확인.

동사:
  scan                    항목 탐지 → 번호 목록 say(세 칸) · scan.json 기록
  grant --pick 1,3 --answer-file F [--folder P]
                          고른 번호만 넘김(바로 → active · 손 → pending + 첫 안내) · 안 됨 → 거부 문장
  guide <ID> [--step n]   손 칸 단계 안내(한 번에 한 단계 · 지금 빠진 단계만)
  recheck <ID>            그 항목만 다시 탐지 → 됐으면 pending → active
  revoke <ID>             장부에서 거둠 + 끄는 곳 안내(마스터가 끌 수 없는 것)
  status                  장부 + 지금 상태
  open-settings <pane>    (맥) 허용 목록의 시스템 설정 화면만 연다 — 사용자가 「열어 줘」 한 뒤에만
  request-prompt <ax|sc> --answer-file F
                          (맥) 손쉬운 사용·화면 기록 **요청 창을 띄운다**(누르는 것은 사용자 · D2 = 사용자 「네」 뒤에만)
  self-test               판정표 전 조합 · 개인정보 · 내장 뮤턴트

exit: 0 성공 · 1 내부 오류 · 2 사용 오류 · 4 대상 없음 · 5 거부(안 됨 항목 · 허용 밖) · 7 상태 불일치(scan 없음·낡음)

★경계(설계 §6 · 시험이 단언): 탐지는 전부 「묻지 않는」 API(AXIsProcessTrusted · CGPreflightScreenCaptureAccess ·
  AEDeterminePermissionToAutomateTarget(askUserIfNeeded=false))와 파일 존재·이름 확인뿐이다. TCC 데이터베이스·키체인·
  쿠키·Login Data·보호 폴더(바탕화면·문서·다운로드) **내용**은 열지 않는다. 클로드 설정·크롬 설정은 읽기만 한다.
  출력에 이메일·이름·조직 이름·크롬 프로필 이름·파일 목록을 싣지 않는다(출력은 마스터 대화 = 모델 제공자로 간다).
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

MEASURED_ON = "2.1.310"            # S9 computer-use 켜짐 기록(enabledMcpServers) 실측 판본
CLAUDE_EXT_ID = "fcoeoabgfenejglbffodgkkbkcdhcgfn"      # Claude in Chrome (S4 실측)
PLAYWRIGHT_EXT_ID = "mmlmfjhmonkocbjadbfplnigmagldckm"  # Playwright Extension (VM-LOG V13)
NMH_NAME = "com.anthropic.claude_code_browser_extension"
SCAN_TTL_SEC = 30 * 60
MAX_PROFILES = 20
MAX_SAY_LINES = 25
MAX_LEDGER_LINES = 1000
MAX_JSON_BYTES = 20 * 1024 * 1024
SUBPROC_TIMEOUT = 5

READY, HAND, NOT_NOW = "ready", "hand", "not_now"
TIER_LABEL = {READY: "바로 가능", HAND: "내 손 한 번 필요", NOT_NOW: "지금은 안 됨"}

PLAN_OK = {"claude_pro", "claude_max"}
PLAN_NO = {"claude_team", "claude_enterprise"}

SETTINGS_URLS = {
    "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "screen": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
    "automation": "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation",
}

# 맥 앱 카탈로그(화면 조작 대상) — 이름 접두로 /Applications 꼭대기만 본다(카탈로그 밖은 출력하지 않는다).
MAC_APPS = [
    ("kakaotalk", "카카오톡", ("KakaoTalk",),
     "보이는 만큼 읽고 직접 보내는 것까지만 합니다(카카오는 대화 읽기 API 가 없고 대량 자동 발송을 막습니다)."),
    ("hwp", "한글", ("Hancom Office HWP", "한컴오피스 한글"), "맥 한글은 화면 조작으로만 다룹니다(스크립트 길 없음)."),
    ("word", "Word", ("Microsoft Word",), ""),
    ("excel", "Excel", ("Microsoft Excel",), ""),
    ("powerpoint", "PowerPoint", ("Microsoft PowerPoint",), ""),
    ("photoshop", "포토샵", ("Adobe Photoshop",), ""),
    ("illustrator", "일러스트레이터", ("Adobe Illustrator",), ""),
    ("acrobat", "애크로뱃", ("Adobe Acrobat",), ""),
]
# 맥 스크립트(자동화) 카탈로그 — (ID, 이름, 번들, 설치 확인용 앱 접두 · None = 기본 앱)
MAC_SCRIPT = [
    ("finder", "Finder", "com.apple.finder", None),
    ("mail", "메일", "com.apple.mail", None),
    ("calendar", "캘린더", "com.apple.iCal", None),
    ("word", "Word", "com.microsoft.Word", ("Microsoft Word",)),
    ("excel", "Excel", "com.microsoft.Excel", ("Microsoft Excel",)),
    ("powerpoint", "PowerPoint", "com.microsoft.Powerpoint", ("Microsoft PowerPoint",)),
]
WIN_APPS = [   # (ID, 이름, ((환경변수, 경로 조각…), …)) — 존재만 본다(★윈 실기 전 가정 · 설계 §3-2)
    ("kakaotalk", "카카오톡", (("ProgramFiles(x86)", "Kakao", "KakaoTalk", "KakaoTalk.exe"),
                              ("ProgramFiles", "Kakao", "KakaoTalk", "KakaoTalk.exe"))),
    ("hwp", "한글", (("ProgramFiles(x86)", "HNC"), ("ProgramFiles", "HNC"))),
    ("office", "오피스(Word·Excel·PowerPoint)", (("ProgramFiles", "Microsoft Office"),
                                               ("ProgramFiles(x86)", "Microsoft Office"))),
]
# 맥이 보호하는 폴더 — 존재만 본다(내용을 열면 그 자체가 맥의 허락 창을 띄운다).
MAC_PROTECTED = [("desktop", "바탕화면", "Desktop"), ("documents", "문서", "Documents"), ("downloads", "다운로드", "Downloads")]


# ───────────────────────── 경로·환경 ─────────────────────────
def home():
    return os.path.expanduser("~")


def platform():
    p = os.environ.get("CYS_CC_PLATFORM")
    if p:
        return p
    if sys.platform == "darwin":
        return "darwin"
    if os.name == "nt":
        return "win"
    try:
        with open("/proc/version", encoding="utf-8", errors="replace") as f:
            if "microsoft" in f.read().lower():
                return "wsl"
    except OSError:
        pass
    return "linux"


def state_dir():
    return os.environ.get("CYS_CC_STATE") or os.path.join(home(), ".cys", "computer-control")


def claude_config_dir():
    return (os.environ.get("CLAUDE_CONFIG_DIR") or os.environ.get("CYS_ACCOUNT_DIR")
            or os.path.join(home(), ".cys", "claude"))


def _p(name):
    return os.path.join(state_dir(), name)


def _now():
    return time.time()


def _iso(t=None):
    return datetime.datetime.fromtimestamp(t or _now()).astimezone().isoformat(timespec="seconds")


def _read_json(path):
    """작은 JSON 만 읽는다(상한 · 실패 = None). 내용은 호출부가 필요한 칸만 꺼낸다."""
    try:
        if os.path.getsize(path) > MAX_JSON_BYTES:
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.tmp-%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _ledger(event):
    path = _p("ledger.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    event = dict(event, ts=_iso())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    _trim_ledger(path)


def _trim_ledger(path):
    """4군① — 장부 기록 상한. 넘으면 뒤쪽 MAX 줄만 남긴다(새 파일로 바꿔 끼움 · 단일 쓰기 주체)."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return
    if len(lines) <= MAX_LEDGER_LINES:
        return
    tmp = path + ".trim-%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(lines[-MAX_LEDGER_LINES:])
    os.replace(tmp, path)


def _run(argv):
    """외부 호출 1회 · 5초 상한 · 표준입력 없음(윈 콘솔 없는 상속 핸들 방지). 실패 = None."""
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           timeout=SUBPROC_TIMEOUT, **NOWIN)
        return r
    except (OSError, subprocess.SubprocessError):
        return None


# ───────────────────────── 탐지(전부 읽기·팝업 없음) ─────────────────────────
def _fake(key):
    """시험 주입(CYS_CC_FAKE_PROBES = JSON). 키가 없으면 None → 실제 탐지."""
    raw = os.environ.get("CYS_CC_FAKE_PROBES")
    if not raw:
        return None
    try:
        d = json.loads(raw)
    except ValueError:
        return None
    return d.get(key, None) if isinstance(d, dict) else None


def _has_fake(key):
    raw = os.environ.get("CYS_CC_FAKE_PROBES")
    if not raw:
        return False
    try:
        d = json.loads(raw)
    except ValueError:
        return False
    return isinstance(d, dict) and key in d


def probe_ax():
    """손쉬운 사용 — AXIsProcessTrusted()(창을 띄우지 않는 판). True/False/None."""
    if _has_fake("ax"):
        return _fake("ax")
    try:
        import ctypes
        ap = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
        ap.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(ap.AXIsProcessTrusted())
    except Exception:
        return None


def probe_sc():
    """화면 기록 — CGPreflightScreenCaptureAccess()(창을 띄우지 않는 판). True/False/None."""
    if _has_fake("sc"):
        return _fake("sc")
    try:
        import ctypes
        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool
        return bool(cg.CGPreflightScreenCaptureAccess())
    except Exception:
        return None


ASK_USER_IF_NEEDED = False   # ★경계: 언제나 False(창을 띄우지 않는다) — 뮤턴트 M3 가 True 로 바꾸면 시험이 죽는다


def probe_ae(bundle):
    """앱 자동화 — AEDeterminePermissionToAutomateTarget(…, askUserIfNeeded=false).
    0 허용 · -1743 거부 · -1744 아직 안 물음 · -600 앱 꺼짐 · None 판정 불가."""
    fk = _fake("ae")
    if isinstance(fk, dict) and bundle in fk:
        return fk[bundle]
    try:
        import ctypes
        import struct
        cs = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreServices.framework/CoreServices")

        class AEDesc(ctypes.Structure):
            _fields_ = [("descriptorType", ctypes.c_uint32), ("dataHandle", ctypes.c_void_p)]

        def fcc(s):
            return struct.unpack(">I", s.encode())[0]
        d = AEDesc()
        b = bundle.encode()
        if cs.AECreateDesc(fcc("bund"), b, len(b), ctypes.byref(d)):
            return None
        cs.AEDeterminePermissionToAutomateTarget.restype = ctypes.c_int32
        r = cs.AEDeterminePermissionToAutomateTarget(ctypes.byref(d), fcc("****"), fcc("****"),
                                                     ctypes.c_bool(ASK_USER_IF_NEEDED))
        cs.AEDisposeDesc(ctypes.byref(d))
        return int(r)
    except Exception:
        return None


def claude_cfg():
    """클로드 설정(.claude.json)에서 **필요한 칸만** 꺼낸다 — 이메일·이름·조직 이름은 꺼내지 않는다."""
    d = _read_json(os.path.join(claude_config_dir(), ".claude.json"))
    if not isinstance(d, dict):
        return {"readable": False}
    oa = d.get("oauthAccount")
    plan = oa.get("organizationType") if isinstance(oa, dict) else None
    projects = d.get("projects") if isinstance(d.get("projects"), dict) else {}
    ever = d.get("claudeAiMcpEverConnected")
    return {
        "readable": True,
        "logged_in": isinstance(oa, dict),
        "plan": plan if isinstance(plan, str) else None,
        "chrome_default": d.get("claudeInChromeDefaultEnabled") if isinstance(d.get("claudeInChromeDefaultEnabled"), bool) else None,
        "connectors": [str(x) for x in ever if isinstance(x, str)] if isinstance(ever, list) else [],
        "project_cu": {k: ("computer-use" in v.get("enabledMcpServers"))
                       for k, v in projects.items()
                       if isinstance(v, dict) and isinstance(v.get("enabledMcpServers"), list)},
        "project_keys": [k for k in projects.keys() if isinstance(k, str)],
    }


def _git_root(path):
    d = path
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


def computer_use_enabled(cfg, project):
    """S9 — 마스터 폴더의 프로젝트 설정에 computer-use 가 켜져 있는가. 대조 키 = 그 폴더 그대로, 없으면 그 폴더의
    git 최상위 — 그보다 위(예: 홈)의 기록은 **다른 프로젝트**라 쓰지 않는다. True/False/None(못 읽음 · 기록 없음)."""
    if not cfg.get("readable") or not project:
        return None
    proj = os.path.realpath(project)
    keys = {os.path.realpath(k): k for k in cfg.get("project_keys", [])}
    for cand in (proj, _git_root(proj)):
        if cand and cand in keys:
            return bool(cfg["project_cu"].get(keys[cand], False))
    return None


def plan_state(cfg):
    p = cfg.get("plan")
    if p in PLAN_OK:
        return "ok"
    if p in PLAN_NO:
        return "no"
    return None


def _app_roots():
    """맥 앱 자리 — 시험은 CYS_CC_APP_ROOTS(: 구분)로 바꾼다(호스트 /Applications 에 기대지 않게)."""
    env = os.environ.get("CYS_CC_APP_ROOTS")
    if env:
        return [r for r in env.split(os.pathsep) if r]
    return ["/Applications", os.path.join(home(), "Applications")]


def _chrome_userdata(plat):
    if plat == "darwin":
        return os.path.join(home(), "Library", "Application Support", "Google", "Chrome")
    if plat == "win":
        la = os.environ.get("LOCALAPPDATA") or os.path.join(home(), "AppData", "Local")
        return os.path.join(la, "Google", "Chrome", "User Data")
    return os.path.join(home(), ".config", "google-chrome")


def _chrome_app(plat):
    if plat == "darwin":
        return any(os.path.isdir(os.path.join(r, "Google Chrome.app")) for r in _app_roots())
    if plat == "win":
        cands = [os.path.join(os.environ.get(v, ""), "Google", "Chrome", "Application", "chrome.exe")
                 for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA") if os.environ.get(v)]
        return any(os.path.isfile(c) for c in cands)
    return False


def _profiles(ud):
    try:
        names = sorted(n for n in os.listdir(ud) if n == "Default" or n.startswith("Profile "))
    except OSError:
        return []
    return names[:MAX_PROFILES]


def _ext_state(ud, prof, ext_id):
    """확장 켜짐 — Secure Preferences / Preferences 의 그 ID 항목 하나만. True/False/None."""
    for fn in ("Secure Preferences", "Preferences"):
        d = _read_json(os.path.join(ud, prof, fn))
        if not isinstance(d, dict):
            continue
        s = ((d.get("extensions") or {}).get("settings") or {}).get(ext_id)
        if isinstance(s, dict):
            dr = s.get("disable_reasons")
            if s.get("state") == 0 or (isinstance(dr, list) and dr) or (isinstance(dr, int) and dr):
                return False
            return True
    return None


def _nmh_ok(plat, ud):
    """확장 연결 파일(native messaging host) — 있고 가리키는 실행 파일이 있는가. True/False/None."""
    if plat == "win":
        r = _run(["reg", "query", r"HKCU\Software\Google\Chrome\NativeMessagingHosts\%s" % NMH_NAME, "/ve"])
        if r is None:
            return None
        if r.returncode != 0:
            return False
        m = re.search(r"REG_SZ\s+(.+)$", r.stdout or "", re.M)
        manifest = m.group(1).strip() if m else ""
    else:
        manifest = os.path.join(ud, "NativeMessagingHosts", NMH_NAME + ".json")
    if not manifest or not os.path.isfile(manifest):
        return False
    d = _read_json(manifest)
    if not isinstance(d, dict) or not isinstance(d.get("path"), str):
        return None
    return os.path.exists(d["path"])


def probe_chrome(plat, cfg):
    fk = _fake("chrome")
    if isinstance(fk, dict):
        return fk
    ud = _chrome_userdata(plat)
    profs = _profiles(ud)
    states = []
    alt = False
    for p in profs:
        ext_dir = os.path.join(ud, p, "Extensions")
        if os.path.isdir(os.path.join(ext_dir, CLAUDE_EXT_ID)):
            states.append(_ext_state(ud, p, CLAUDE_EXT_ID))
        if os.path.isdir(os.path.join(ext_dir, PLAYWRIGHT_EXT_ID)):
            alt = True
    # 한 프로필이라도 켜져 있으면 켜짐 · 모르는 것이 섞이면 모름 · 전부 꺼짐이면 꺼짐
    enabled = True if True in states else (None if None in states else False)
    return {
        "app": _chrome_app(plat),
        "profiles": len(profs),
        "with_ext": len(states),
        "ext_enabled": enabled,
        "nmh": _nmh_ok(plat, ud),
        "default_on": cfg.get("chrome_default"),
        "playwright_ext": alt,
    }


def _mac_app_installed(prefixes):
    for root in _app_roots():
        try:
            names = os.listdir(root)
        except OSError:
            continue
        for n in names:
            if any(n.startswith(px) for px in prefixes):
                return True
    return False


def probe_apps(plat):
    fk = _fake("apps")
    if isinstance(fk, list):
        return fk
    found = []
    if plat == "darwin":
        for aid, name, prefixes, _note in MAC_APPS:
            if _mac_app_installed(prefixes):
                found.append(aid)
    elif plat == "win":
        for aid, _name, paths in WIN_APPS:
            if any(os.environ.get(p[0]) and os.path.exists(os.path.join(os.environ[p[0]], *p[1:])) for p in paths):
                found.append(aid)
    return found


def _win_claude_desktop():
    la = os.environ.get("LOCALAPPDATA") or ""
    cands = [os.path.join(la, "AnthropicClaude"), os.path.join(la, "Programs", "Claude")]
    return any(os.path.isdir(c) for c in cands if la)


# ───────────────────────── 판정(순수 함수 · self-test 전수) ─────────────────────────
def verdict_screen(plat, plan, cu, ax, sc):
    """화면 조작 — (tier, unknown, missing[], reason)."""
    if plat != "darwin":
        if plat == "win":
            return NOT_NOW, False, [], ("윈도우에서는 이 칸의 마스터가 화면을 조작할 수 없습니다(Claude 공식 안내). "
                                        "Claude 데스크톱 앱에서는 가능합니다 — 그 앱에 직접 시키셔야 합니다.")
        return NOT_NOW, False, [], "이 컴퓨터(맥이 아님)에서는 마스터의 화면 조작이 지원되지 않습니다."
    if plan == "no":
        return NOT_NOW, False, [], "지금 쓰시는 요금제(팀·기업용)에는 화면 조작 기능이 없습니다(Pro·Max 전용)."
    missing = [k for k, v in (("cu", cu), ("ax", ax), ("sc", sc)) if v is False]
    unknown = plan is None or any(v is None for v in (cu, ax, sc))
    if not missing and not unknown:
        return READY, False, [], "화면 조작 도구와 맥 권한(손쉬운 사용·화면 기록)이 모두 켜져 있습니다."
    if unknown and not missing:
        return HAND, True, [k for k, v in (("cu", cu), ("ax", ax), ("sc", sc)) if v is None], \
            "켜져 있는지 제가 확인하지 못한 부분이 있습니다 — 한 번 같이 확인해 주세요."
    return HAND, unknown, missing, "몇 가지만 켜 주시면 됩니다."


def verdict_chrome(plat, c):
    if plat == "wsl":
        return NOT_NOW, False, [], "WSL 안에서는 크롬 연결이 지원되지 않습니다 — 윈도우 그대로에서 쓰셔야 합니다."
    if not c.get("app"):
        return NOT_NOW, False, [], "이 컴퓨터에서 크롬을 찾지 못했습니다. 크롬을 설치하시면 다시 살펴볼게요."
    parts = (("ext", c.get("ext_enabled") if c.get("with_ext") else False),
             ("default_on", c.get("default_on")),
             ("nmh", c.get("nmh")))
    missing = [k for k, v in parts if v is False]
    unknown = any(v is None for _, v in parts)
    if not missing and not unknown:
        return READY, False, [], "크롬의 Claude 확장과 연결이 준비돼 있습니다."
    if unknown and not missing:
        return HAND, True, [k for k, v in parts if v is None], "크롬 연결 상태를 제가 다 확인하지 못했습니다 — 한 번 같이 확인해 주세요."
    return HAND, unknown, missing, "크롬에 Claude 확장을 연결하는 단계가 남아 있습니다."


def verdict_connectors(cfg):
    if not cfg.get("readable") or not cfg.get("logged_in"):
        return HAND, True, ["login"], "클로드 로그인 정보를 확인하지 못했습니다."
    names = cfg.get("connectors") or []
    if names:
        return READY, False, [], "연결 기록이 있습니다: " + ", ".join(n.replace("claude.ai ", "") for n in names[:10])
    return HAND, False, ["connect"], "아직 연결된 서비스가 없습니다(지메일·캘린더·드라이브 등은 claude.ai 에서 연결합니다)."


def verdict_script(code):
    if code == 0:
        return READY, False, [], "자동화를 이미 허락받았습니다."
    if code == -1744:
        return HAND, False, ["first_ask"], "처음 시킬 때 맥이 한 번 묻습니다 — 「허용」만 누르시면 됩니다(암호 없음)."
    if code == -1743:
        return HAND, False, ["denied"], "예전에 「허용 안 함」을 고르셨습니다 — 설정에서 다시 켜 주셔야 합니다."
    if code == -600:
        return HAND, True, ["not_running"], "앱이 꺼져 있어서 확인하지 못했습니다 — 앱을 켜 두시면 다시 볼게요."
    return HAND, True, ["unknown"], "자동화 허락 상태를 확인하지 못했습니다."


def verdict_folder(plat, protected):
    if plat == "darwin" and protected:
        return HAND, False, ["first_ask"], "제가 처음 열 때 맥이 한 번 묻습니다 — 「허용」을 눌러 주세요."
    return READY, False, [], "바로 쓸 수 있습니다."


# ───────────────────────── 항목 만들기 ─────────────────────────
def _item(iid, title, tier, unknown, missing, reason, note=""):
    return {"id": iid, "title": title, "tier": tier, "unknown": bool(unknown),
            "missing": list(missing), "reason": reason, "note": note}


MISSING_LABEL = {
    "cu": "화면 조작 도구 켜기(/mcp)", "ax": "손쉬운 사용 권한", "sc": "화면 기록 권한",
    "ext": "Claude 확장 설치·켜기", "default_on": "/chrome 기본 켜기", "nmh": "크롬 다시 켜기(연결 파일)",
}
MERGE_KINDS = ("script", "files")


def _with_missing(reason, missing):
    names = [MISSING_LABEL[m] for m in missing if m in MISSING_LABEL]
    return reason + (" 남은 것: " + " · ".join(names) + "." if names else "")


def raw_items(plat, project, cfg=None):
    """판정 단위 항목(합치기 전). 같은 판정의 스크립트·폴더 줄은 merge_items 가 한 줄로 접는다."""
    cfg = cfg if cfg is not None else claude_cfg()
    items = []
    c = probe_chrome(plat, cfg)
    t, u, m, r = verdict_chrome(plat, c)
    items.append(_item("chrome", "크롬으로 웹 일(로그인된 지메일·구글 문서·클라우드플레어 화면 등)", t, u, m,
                       _with_missing(r, m)))
    if t != READY and c.get("app"):
        items.append(_item("browser-alt", "예비 브라우저 길(Playwright 확장 — 강사와 함께)", HAND, False,
                           ["alt"], "크롬 확장이 끝내 안 될 때만 쓰는 예비 길입니다. 확장의 보호 규칙이 같다는 보장은 없습니다."))
    t, u, m, r = verdict_connectors(cfg)
    items.append(_item("connectors", "커넥터(메일·일정·드라이브 등 — 내용은 커넥터로 다룹니다)", t, u, m, r))

    plan = plan_state(cfg)
    if plat == "darwin":
        cu = _fake("cu") if _has_fake("cu") else computer_use_enabled(cfg, project)
        st, su, sm, sr = verdict_screen(plat, plan, cu, probe_ax(), probe_sc())
    else:
        st, su, sm, sr = verdict_screen(plat, plan, None, None, None)
        if plat == "win":
            sr += " (Claude 데스크톱 앱: %s)" % ("이 컴퓨터에 설치돼 있습니다" if _win_claude_desktop()
                                              else "찾지 못했습니다 — 설치 위치가 다를 수 있습니다")
    apps = probe_apps(plat)
    if plat == "darwin":
        names = [name for aid, name, _px, _n in MAC_APPS if aid in apps]
        notes = [n for aid, _name, _px, n in MAC_APPS if aid in apps and n]
    else:
        names = [name for aid, name, _p in WIN_APPS if aid in apps]
        notes = []
    title = "데스크톱 앱 화면 조작" + ("(이 컴퓨터의 앱: %s)" % "·".join(names) if names else "")
    items.append(_item("screen", title, st, su, sm, _with_missing(sr, sm), " ".join(notes)))

    if plat == "darwin":
        for sid, name, bundle, need in MAC_SCRIPT:
            if need is not None and not _mac_app_installed(need):
                continue
            t, u, m, r = verdict_script(probe_ae(bundle))
            items.append(dict(_item("script:" + sid, "%s 자동화(스크립트)" % name, t, u, m, r), name=name))
    elif plat == "win":
        if "hwp" in apps or "office" in apps:
            items.append(_item("script:win", "한글·오피스 자동화(스크립트)", NOT_NOW, False, [],
                               "윈도우 스크립트 길은 아직 확인 중입니다(다음 판에서 엽니다)."))

    if os.path.isdir(os.path.join(home(), "CYSjavis")):
        t, u, m, r = verdict_folder(plat, False)
        items.append(dict(_item("files:cysjavis", "파일·폴더: CYSjavis", t, u, m, r), name="CYSjavis"))
    for fid, name, sub in MAC_PROTECTED:
        if os.path.isdir(os.path.join(home(), sub)):     # 존재만(내용 열람 0)
            t, u, m, r = verdict_folder(plat, True)
            items.append(dict(_item("files:" + fid, "파일·폴더: %s" % name, t, u, m, r), name=name))
    return items


def _merge(group):
    """같은 종류 항목 여러 개 → 한 줄. 판정은 가장 나쁜 것(안 됨 > 손 > 바로) · 모름은 하나라도 있으면 모름."""
    if len(group) == 1:
        return group[0]
    kind = _kind(group[0]["id"])
    rank = {READY: 0, HAND: 1, NOT_NOW: 2}
    worst = max(group, key=lambda it: rank[it["tier"]])
    names = [it.get("name") or it["id"] for it in group]
    missing = []
    for it in group:
        missing += [m for m in it["missing"] if m not in missing]
    title = ("%s 자동화(스크립트)" if kind == "script" else "파일·폴더: %s") % "·".join(names)
    return dict(_item(kind + ":" + ",".join(it["id"].split(":", 1)[1] for it in group), title, worst["tier"],
                      any(it["unknown"] for it in group), missing, worst["reason"]), name="·".join(names))


def merge_items(items):
    """스크립트·폴더 중 판정(칸·모름·빠진 것)이 같은 줄을 한 줄로 접는다 — 목록을 짧게(왕초보 화면)."""
    out_, groups = [], {}
    for it in items:
        k = _kind(it["id"])
        if k in MERGE_KINDS:
            key = (k, it["tier"], it["unknown"], tuple(it["missing"]))
            if key not in groups:
                groups[key] = []
                out_.append(key)
            groups[key].append(it)
        else:
            out_.append(it)
    return [_merge(groups[x]) if isinstance(x, tuple) else x for x in out_]


def build_items(plat, project, cfg=None):
    return merge_items(raw_items(plat, project, cfg))


def number_items(items):
    order = {READY: 0, HAND: 1, NOT_NOW: 2}
    items = sorted(items, key=lambda it: order[it["tier"]])
    for i, it in enumerate(items, 1):
        it["n"] = i
    return items


# ───────────────────────── 안내 문장 ─────────────────────────
STEPS = {
    ("screen", "cu"): [
        "마스터 칸(지금 저와 대화하는 칸)의 입력줄에 /mcp 를 입력하고 Enter 를 누르세요.",
        "목록에서 computer-use 를 화살표로 골라 Enter → Enable(켜기)을 고르세요. 이 설정은 이 폴더에서만 켜집니다.",
    ],
    ("screen", "ax"): [
        "화면 왼쪽 위 사과 메뉴 → 시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용 으로 가세요.",
        "목록에서 cysr 스위치를 켜세요. 맥 로그인 암호를 물으면 이 맥에 로그인할 때 쓰는 암호를 넣으세요(정상입니다).",
        "목록에 cysr 이 없으면 목록 아래 「+」 → 응용 프로그램 → cysr → 열기 로 넣고 켜세요.",
    ],
    ("screen", "sc"): [
        "같은 「개인정보 보호 및 보안」에서 화면 및 시스템 오디오 녹음 으로 가세요.",
        "cysr 스위치를 켜세요(암호를 물으면 맥 로그인 암호). 「종료 및 다시 열기」 창이 뜨면 눌러도 됩니다 — 저와의 대화는 이어집니다.",
        "이름이 「cysd」로 뜨는 창이 나오면 cysr 안의 엔진이니 「허용」을 누르세요.",
    ],
    ("chrome", "ext"): [
        "크롬에서 Chrome 웹 스토어의 「Claude」 확장을 찾아 「Chrome에 추가」를 누르세요.",
        "확장에 마스터와 **같은 Claude 계정**으로 로그인하고, 주소창 오른쪽 퍼즐 조각에서 Claude 를 압정으로 고정하세요.",
    ],
    ("chrome", "default_on"): [
        "마스터 칸 입력줄에 /chrome 을 입력하고 Enter → Enabled by default(기본으로 켜기)를 고르세요.",
        "이 설정은 다음 대화부터 적용됩니다 — cysr 위쪽의 ↻ 재시작 단추를 눌러 주세요(직접 claude 를 다시 치지 마세요).",
    ],
    ("chrome", "nmh"): [
        "크롬을 완전히 끄세요(맥: 크롬 메뉴 → Chrome 종료 / 윈도우: 모든 크롬 창 닫기) 그리고 다시 켜세요 — 연결 파일은 크롬이 켜질 때만 읽힙니다.",
        "그래도 안 되면 마스터 칸에서 /chrome → Reconnect extension 을 고르세요.",
    ],
    ("browser-alt", "alt"): [
        "이 길은 강사와 함께 하세요. 크롬 웹 스토어에서 「Playwright Extension」을 추가합니다.",
        "연결할 때마다 크롬에 「연결하려고 합니다」 탭이 뜨면 맡길 탭만 「Allow & select」로 고르세요. 화면에 보이는 토큰을 어디에도 붙여 넣지 마세요.",
    ],
    ("connectors", "connect"): [
        "인터넷 창에서 claude.ai 에 마스터와 같은 계정으로 로그인하세요.",
        "왼쪽 아래 이름 → 설정 → 커넥터 → 「+」 에서 지메일·캘린더·드라이브 등 맡길 것을 연결하세요. 비밀번호는 Google 화면에만 넣습니다(Claude 는 보지 않습니다).",
    ],
    ("connectors", "login"): [
        "마스터 칸에 /status 를 입력해 로그인 상태를 봐 주세요. 로그인이 안 돼 있으면 cysr 위쪽 ↻ 재시작 뒤 안내대로 로그인하세요.",
    ],
    ("script", "first_ask"): [
        "따로 하실 것은 없습니다. 제가 이 앱을 처음 다룰 때 「'cysr'에서 '<앱>'을(를) 제어하려고 합니다」 창이 뜨면 「허용」을 눌러 주세요.",
    ],
    ("script", "denied"): [
        "사과 메뉴 → 시스템 설정 → 개인정보 보호 및 보안 → 자동화 로 가세요.",
        "cysr 아래에서 이 앱 스위치를 켜세요.",
    ],
    ("script", "not_running"): [
        "그 앱을 한 번 켜 두세요. 켠 뒤 「켰어」라고 말씀해 주시면 다시 확인하겠습니다.",
    ],
    ("script", "unknown"): [
        "확인이 잘 안 됐습니다. 그 앱을 켜 두고 「다시 봐 줘」라고 말씀해 주세요.",
    ],
    ("files", "first_ask"): [
        "따로 하실 것은 없습니다. 제가 이 폴더를 처음 열 때 맥이 「접근하려고 합니다」 창을 띄우면 「허용」을 눌러 주세요.",
    ],
}
CLOSING = "다 하셨으면 「했어」라고 말씀해 주세요. 제가 다시 확인하겠습니다."

REVOKE_HINT = {
    "screen": "맥 권한까지 끄시려면: 시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용 · 화면 및 시스템 오디오 녹음 에서 cysr 스위치를 끄세요. "
              "화면 조작 도구는 마스터 칸 /mcp → computer-use → Disable 로 끕니다.",
    "chrome": "크롬 연결까지 끄시려면: 마스터 칸 /chrome 에서 끄시거나, 크롬 확장 관리(chrome://extensions)에서 Claude 를 끄세요.",
    "browser-alt": "예비 길을 끝내시려면: 확장의 상태 화면에서 연결을 끊고, 강사와 함께 연결 설정을 지우세요.",
    "connectors": "커넥터까지 끊으시려면: claude.ai → 설정 → 커넥터 에서 그 서비스의 연결 끊기(Disconnect)를 누르세요.",
    "script": "자동화 허락까지 끄시려면: 시스템 설정 → 개인정보 보호 및 보안 → 자동화 → cysr 아래 그 앱 스위치를 끄세요.",
    "files": "이 폴더는 이제 제가 다루지 않겠습니다.",
}


def first_use_only(it):
    """손 칸이지만 **지금 할 일은 없고** 처음 쓸 때 맥이 한 번 묻는 것(보호 폴더 · 아직 안 물은 앱 자동화)."""
    return it["tier"] == HAND and not it["unknown"] and it["missing"] == ["first_ask"]


def _kind(iid):
    return iid.split(":", 1)[0]


def steps_for(it):
    """손 칸 항목 → 지금 빠진 것의 단계만(순서 고정)."""
    kind = _kind(it["id"])
    base = kind
    out = []
    for m in it.get("missing", []):
        out += STEPS.get((base, m), [])
    if not out and it.get("unknown") and base == "screen":
        for m in ("cu", "ax", "sc"):
            out += STEPS[("screen", m)][:1]
    app = it["title"].split(" 자동화")[0]
    return [s.replace("<앱>", app) for s in out]


# ───────────────────────── 장부 ─────────────────────────
def load_grants():
    g = _read_json(_p("grants.json"))
    if not isinstance(g, dict) or not isinstance(g.get("items"), dict):
        return {"items": {}}
    return g


def save_grants(g):
    _write_json(_p("grants.json"), g)


def load_scan():
    s = _read_json(_p("scan.json"))
    return s if isinstance(s, dict) and isinstance(s.get("items"), list) else None


# ───────────────────────── 출력 ─────────────────────────
def out(obj, rc=0):
    print(json.dumps(obj, ensure_ascii=False))
    return rc


def fail(say, reason, rc):
    return out({"ok": False, "say": say, "reason": reason}, rc)


def _project():
    return os.environ.get("CYS_CC_PROJECT") or os.getcwd()


def render_scan(items):
    lines = ["이 컴퓨터에서 제가 맡을 수 있는 것을 살펴봤습니다(내용은 열어 보지 않았고, 무엇이 있고 연결됐는지만 봤습니다)."]
    for tier in (READY, HAND, NOT_NOW):
        group = [it for it in items if it["tier"] == tier]
        if not group:
            continue
        lines.append("■ %s" % TIER_LABEL[tier])
        for it in group:
            mark = " (확인 필요)" if it["unknown"] else ""
            lines.append("%d. %s%s — %s" % (it["n"], it["title"], mark, it["reason"]))
    if len(lines) > MAX_SAY_LINES - 1:
        lines = lines[:MAX_SAY_LINES - 2] + ["…(더 있습니다 — 「나머지도 보여 줘」라고 말씀해 주세요)"]
    lines.append("맡기실 번호를 말씀해 주세요. 고르지 않은 것은 넘겨받지 않습니다.")
    return "\n".join(lines)


# ───────────────────────── 동사 ─────────────────────────
def cmd_scan(a):
    plat = platform()
    items = number_items(build_items(plat, _project()))
    _write_json(_p("scan.json"), {"ts": _now(), "at": _iso(), "platform": plat, "measured_on": MEASURED_ON,
                                  "items": items})
    return out({"ok": True, "platform": plat,
                "groups": {t: [it["n"] for it in items if it["tier"] == t] for t in (READY, HAND, NOT_NOW)},
                "items": [{k: it[k] for k in ("n", "id", "tier", "unknown")} for it in items],
                "say": render_scan(items)})


def _parse_pick(s):
    nums = []
    for tok in re.split(r"[,\s]+", s or ""):
        if not tok:
            continue
        if not tok.isdigit():
            return None
        nums.append(int(tok))
    return nums


def _fresh_scan():
    s = load_scan()
    if s is None:
        return None, fail("먼저 컴퓨터를 한 번 살펴봐야 합니다 — 「내 컴퓨터에서 맡을 수 있는 걸 찾아 줘」라고 말씀해 주세요.",
                          "no_scan", 7)
    if _now() - float(s.get("ts") or 0) > SCAN_TTL_SEC:
        return None, fail("살펴본 지 시간이 좀 지났습니다 — 다시 한 번 살펴본 뒤 고르시게 할게요.", "stale_scan", 7)
    return s, None


def cmd_grant(a):
    try:
        with open(a.answer_file, encoding="utf-8") as f:
            answer = f.read()
    except OSError:
        return fail("사용자 답을 읽지 못했습니다.", "io", 2)
    if not answer.strip():
        return fail("사용자 답이 비어 있습니다 — 고르신 번호를 다시 여쭤 주세요.", "empty_answer", 2)
    picks = _parse_pick(a.pick)
    if not picks:
        return fail("번호를 알아듣지 못했습니다 — 맡기실 번호를 숫자로 말씀해 주세요.", "pick", 2)
    s, err = _fresh_scan()
    if err is not None:
        return err
    by_n = {it["n"]: it for it in s["items"]}
    unknown_n = [n for n in picks if n not in by_n]
    if unknown_n:
        return fail("목록에 없는 번호가 있습니다: %s" % ", ".join(map(str, unknown_n)), "not_found", 4)
    g = load_grants()
    said, granted, pending, refused = [], [], [], []
    for n in sorted(set(picks)):
        it = by_n[n]
        if it["tier"] == NOT_NOW:
            refused.append(it)
            said.append("%d. %s — 지금은 안 됩니다: %s" % (n, it["title"], it["reason"]))
            continue
        state = "active" if it["tier"] == READY or first_use_only(it) else "pending"
        g["items"][it["id"]] = {"state": state, "title": it["title"], "at": _iso()}
        (granted if state == "active" else pending).append(it)
    if a.folder:
        fp = os.path.realpath(os.path.expanduser(a.folder))
        prot = platform() == "darwin" and any(
            fp == os.path.join(home(), sub) or fp.startswith(os.path.join(home(), sub) + os.sep)
            for _f, _n, sub in MAC_PROTECTED)
        t, _u, _m, r = verdict_folder(platform(), prot)
        g.setdefault("folders", {})[fp] = {"state": "active" if t == READY else "pending", "at": _iso()}
        said.append("폴더 %s — %s" % (os.path.basename(fp) or fp, r))
    if not granted and not pending and not a.folder:
        return fail("\n".join(said), "not_now", 5)
    save_grants(g)
    _ledger({"event": "grant", "picks": sorted(set(picks)),
             "active": [it["id"] for it in granted], "pending": [it["id"] for it in pending],
             "refused": [it["id"] for it in refused],
             "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest()})
    lines = []
    if granted:
        lines.append("지금부터 제가 맡겠습니다: " + ", ".join(it["title"].split("(")[0].strip() for it in granted) + ".")
    for it in granted:
        if first_use_only(it):
            lines.append("「%s」 — %s" % (it["title"].split("(")[0].strip(), it["reason"]))
    for it in pending:
        lines.append("「%s」은(는) 손이 한 번 필요합니다." % it["title"].split("(")[0].strip())
    lines += said
    first = None
    if pending:
        first = pending[0]
        st = steps_for(first)
        if st:
            lines.append("먼저 「%s」부터 하겠습니다 — 1단계(1/%d): %s" % (first["title"].split("(")[0].strip(), len(st), st[0]))
            lines.append(CLOSING if len(st) == 1 else "끝나시면 「다음」이라고 말씀해 주세요.")
    return out({"ok": True, "active": [it["id"] for it in granted], "pending": [it["id"] for it in pending],
                "refused": [it["id"] for it in refused], "next_guide": first["id"] if first else None,
                "say": "\n".join(lines)})


def _scan_item(iid):
    """이 항목만 다시 탐지. 합친 ID(script:mail,calendar)는 구성원을 지금 판정으로 다시 합친다
    — 판정 경로는 raw_items 하나다."""
    items = raw_items(platform(), _project())
    for it in items:
        if it["id"] == iid:
            return it
    kind, _, rest = iid.partition(":")
    if kind in MERGE_KINDS and rest:
        want = [kind + ":" + x for x in rest.split(",")]
        group = [it for it in items if it["id"] in want]
        if group and len(group) == len(want):
            return _merge(group)
    return None


def cmd_guide(a):
    it = _scan_item(a.id)
    if it is None:
        return fail("그 항목을 찾지 못했습니다.", "not_found", 4)
    if it["tier"] == READY:
        return out({"ok": True, "done": True, "say": "「%s」은(는) 이미 준비돼 있습니다 — 하실 것이 없습니다." % it["title"]})
    if it["tier"] == NOT_NOW:
        return fail("「%s」은(는) 지금은 안 됩니다: %s" % (it["title"], it["reason"]), "not_now", 5)
    st = steps_for(it)
    if not st:
        return out({"ok": True, "done": False, "say": it["reason"] + " " + CLOSING})
    n = max(1, min(a.step or 1, len(st)))
    last = n == len(st)
    say = "「%s」 %d단계(%d/%d): %s\n%s" % (it["title"].split("(")[0].strip(), n, n, len(st), st[n - 1],
                                         CLOSING if last else "끝나시면 「다음」이라고 말씀해 주세요.")
    return out({"ok": True, "step": n, "total": len(st), "last": last, "say": say})


def cmd_recheck(a):
    it = _scan_item(a.id)
    if it is None:
        return fail("그 항목을 찾지 못했습니다.", "not_found", 4)
    g = load_grants()
    cur = g["items"].get(a.id)
    if first_use_only(it):
        return out({"ok": True, "tier": it["tier"], "state": (cur or {}).get("state"),
                    "say": "이건 지금 하실 것이 없습니다 — %s" % it["reason"]})
    if it["tier"] == READY:
        if cur is not None and cur.get("state") != "active":
            cur["state"] = "active"
            cur["at"] = _iso()
            save_grants(g)
            _ledger({"event": "activate", "id": a.id})
        head = "확인했습니다. 「%s」은(는) 이제 제가 맡습니다." % it["title"].split("(")[0].strip() if cur is not None \
            else "확인했습니다. 「%s」은(는) 준비돼 있습니다(아직 맡기지는 않으셨습니다)." % it["title"].split("(")[0].strip()
        return out({"ok": True, "tier": READY, "state": (cur or {}).get("state"), "say": head})
    st = steps_for(it)
    tail = (" 남은 단계: " + st[0]) if st else ""
    return out({"ok": True, "tier": it["tier"], "state": (cur or {}).get("state"),
                "say": "아직 덜 됐습니다 — %s%s" % (it["reason"], tail)})


def cmd_revoke(a):
    g = load_grants()
    if a.id not in g["items"] and a.id not in g.get("folders", {}):
        return fail("그 항목은 맡고 있지 않습니다.", "not_found", 4)
    v = g["items"].pop(a.id, None)
    if v is None:
        g.get("folders", {}).pop(a.id, None)
        title, hint = "폴더 " + (os.path.basename(a.id) or a.id), REVOKE_HINT["files"]
    else:
        title, hint = (v.get("title") or a.id).split("(")[0].strip(), REVOKE_HINT.get(_kind(a.id), "")
    save_grants(g)
    _ledger({"event": "revoke", "id": a.id if v is not None else "folder"})
    return out({"ok": True, "say": "알겠습니다. 「%s」은(는) 이제 맡지 않겠습니다. %s" % (title, hint)})


def cmd_status(a):
    g = load_grants()
    if not g["items"] and not g.get("folders"):
        return out({"ok": True, "rows": [], "say": "아직 제게 맡기신 것이 없습니다."})
    rows, lines = [], ["제가 맡은 것:"]
    for iid, v in sorted(g["items"].items()):
        it = _scan_item(iid)       # 장부 ID 그대로 지금 판정(합친 ID 는 구성원을 다시 합친다)
        now = it["tier"] if it else "missing"
        rows.append({"id": iid, "state": v.get("state"), "now": now})
        word = {"active": "맡는 중", "pending": "준비 중(손이 필요)"}.get(v.get("state"), v.get("state"))
        off = it is None or it["tier"] == NOT_NOW or (it["tier"] == HAND and not first_use_only(it))
        warn = " — 지금 확인하니 꺼져 있습니다(「다시 봐 줘」)" if v.get("state") == "active" and off else ""
        lines.append("· %s: %s%s" % (v.get("title") or iid, word, warn))
    for fp, v in sorted(g.get("folders", {}).items()):
        rows.append({"id": fp, "state": v.get("state"), "now": "folder"})
        lines.append("· 폴더 %s: %s" % (os.path.basename(fp) or fp, "맡는 중" if v.get("state") == "active" else "처음 열 때 허락 필요"))
    return out({"ok": True, "rows": rows, "say": "\n".join(lines[:MAX_SAY_LINES])})


def cmd_open_settings(a):
    if platform() != "darwin":
        return fail("이 컴퓨터에서는 제가 설정 화면을 열어 드릴 수 없습니다 — 안내대로 직접 열어 주세요.", "platform", 5)
    url = SETTINGS_URLS.get(a.pane)
    if url is None:
        return fail("열 수 있는 화면이 아닙니다.", "pane", 5)
    r = _run(["/usr/bin/open", url])
    if r is None or r.returncode != 0:
        return fail("설정 화면을 열지 못했습니다 — 사과 메뉴 → 시스템 설정 → 개인정보 보호 및 보안 으로 직접 가 주세요.", "open_failed", 1)
    return out({"ok": True, "say": "설정 화면을 열었습니다. 스위치는 직접 켜 주세요(암호를 물으면 맥 로그인 암호입니다)."})


def cmd_request_prompt(a):
    """D2 — 맥의 요청 창을 사용자 앞에 띄운다(누르는 것은 사용자). 사용자 「네」 답 원문 파일이 있어야 한다."""
    if platform() != "darwin":
        return fail("이 컴퓨터에서는 해당 없습니다.", "platform", 5)
    try:
        with open(a.answer_file, encoding="utf-8") as f:
            ans = f.read()
    except OSError:
        return fail("사용자 답을 읽지 못했습니다.", "io", 2)
    if not ans.strip():
        return fail("창을 띄우기 전에 사용자께 먼저 여쭤 주세요.", "empty_answer", 2)
    if os.environ.get("CYS_CC_FAKE_PROBES"):
        shown = True
    else:
        try:
            import ctypes
            if a.which == "sc":
                cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
                cg.CGRequestScreenCaptureAccess.restype = ctypes.c_bool
                cg.CGRequestScreenCaptureAccess()
            else:
                cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
                ap = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
                key = ctypes.c_void_p.in_dll(ap, "kAXTrustedCheckOptionPrompt")
                true = ctypes.c_void_p.in_dll(cf, "kCFBooleanTrue")
                cf.CFDictionaryCreate.restype = ctypes.c_void_p
                cf.CFDictionaryCreate.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                                                  ctypes.POINTER(ctypes.c_void_p), ctypes.c_long,
                                                  ctypes.c_void_p, ctypes.c_void_p]
                keys = (ctypes.c_void_p * 1)(key.value)
                vals = (ctypes.c_void_p * 1)(true.value)
                kcb = ctypes.c_void_p.in_dll(cf, "kCFTypeDictionaryKeyCallBacks")
                vcb = ctypes.c_void_p.in_dll(cf, "kCFTypeDictionaryValueCallBacks")
                d = cf.CFDictionaryCreate(None, keys, vals, 1, ctypes.addressof(kcb), ctypes.addressof(vcb))
                ap.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
                ap.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
                ap.AXIsProcessTrustedWithOptions(d)
                cf.CFRelease.argtypes = [ctypes.c_void_p]
                cf.CFRelease(d)
            shown = True
        except Exception:
            shown = False
    _ledger({"event": "request_prompt", "which": a.which, "shown": shown,
             "answer_sha256": hashlib.sha256(ans.encode("utf-8")).hexdigest()})
    if not shown:
        return fail("요청 창을 띄우지 못했습니다 — 안내대로 설정 화면에서 직접 켜 주세요.", "prompt_failed", 1)
    name = "손쉬운 사용" if a.which == "ax" else "화면 기록"
    return out({"ok": True, "say": "맥의 「%s」 요청 창을 띄웠습니다. 창이 다른 창 뒤에 숨어 있을 수 있어요 — "
                                    "「시스템 설정 열기」를 눌러 cysr 스위치를 켜 주세요." % name})


# ───────────────────────── self-test ─────────────────────────
FORBIDDEN_MARKS = ("CC-TEST-EMAIL@example.invalid", "CC-TEST-NAME", "CC-TEST-ORG", "CC-TEST-PROFILE")


def self_test():
    errs = []
    tri = (True, False, None)
    n = 0
    for plat in ("darwin", "win", "linux"):
        for plan in ("ok", "no", None):
            for cu in tri:
                for ax in tri:
                    for sc in tri:
                        n += 1
                        t, u, m, _r = verdict_screen(plat, plan, cu, ax, sc)
                        if t == READY and (u or plan is None or None in (cu, ax, sc)):
                            errs.append("screen ?→바로 %r" % ((plat, plan, cu, ax, sc),))
                        if t == READY and plat != "darwin":
                            errs.append("screen 맥 밖 바로 %r" % ((plat, plan, cu, ax, sc),))
                        if plan == "no" and t != NOT_NOW:
                            errs.append("screen 팀 요금제 통과 %r" % ((plat, plan, cu, ax, sc),))
                        if t == READY and False in (cu, ax, sc):
                            errs.append("screen 꺼짐→바로 %r" % ((plat, plan, cu, ax, sc),))
    for app in (True, False):
        for with_ext in (0, 1):
            for en in tri:
                for d in tri:
                    for nmh in tri:
                        n += 1
                        c = {"app": app, "with_ext": with_ext, "ext_enabled": en, "default_on": d, "nmh": nmh}
                        t, u, _m, _r = verdict_chrome("darwin", c)
                        if t == READY and (not app or not with_ext or en is not True or d is not True or nmh is not True):
                            errs.append("chrome 바로 오판 %r" % (c,))
                        if not app and t != NOT_NOW:
                            errs.append("chrome 앱 없음 %r" % (c,))
    for code in (0, -1743, -1744, -600, -1, None):
        n += 1
        t, u, _m, _r = verdict_script(code)
        if (t == READY) != (code == 0):
            errs.append("script %r" % (code,))
    if ASK_USER_IF_NEEDED is not False:
        errs.append("askUserIfNeeded 가 False 가 아니다")
    return {"ok": not errs, "combos": n, "errors": errs[:20]}


def cmd_self_test(a):
    r = self_test()
    return out(r, 0 if r["ok"] else 1)


# ───────────────────────── main ─────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(prog="javis_computer_control.py")
    sp = ap.add_subparsers(dest="cmd")
    sp.add_parser("scan")
    g = sp.add_parser("grant")
    g.add_argument("--pick", required=True)
    g.add_argument("--answer-file", required=True)
    g.add_argument("--folder")
    for name in ("guide", "recheck", "revoke"):
        p = sp.add_parser(name)
        p.add_argument("id")
        if name == "guide":
            p.add_argument("--step", type=int, default=1)
    sp.add_parser("status")
    o = sp.add_parser("open-settings")
    o.add_argument("pane")
    rp = sp.add_parser("request-prompt")
    rp.add_argument("which", choices=("ax", "sc"))
    rp.add_argument("--answer-file", required=True)
    sp.add_parser("self-test")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    fn = {"scan": cmd_scan, "grant": cmd_grant, "guide": cmd_guide, "recheck": cmd_recheck,
          "revoke": cmd_revoke, "status": cmd_status, "open-settings": cmd_open_settings,
          "request-prompt": cmd_request_prompt, "self-test": cmd_self_test}.get(a.cmd)
    if fn is None:
        ap.print_usage(sys.stderr)
        return 2
    try:
        return fn(a)
    except Exception as e:   # 4군③ — 내부 오류도 JSON 한 줄(마스터가 정적 안내로 폴백)
        return fail("제가 확인하다가 막혔습니다. 대신 「처음 한 번 준비」 안내를 따라 직접 확인해 주세요.",
                    "internal:%s" % type(e).__name__, 1)


if __name__ == "__main__":
    sys.exit(main())
