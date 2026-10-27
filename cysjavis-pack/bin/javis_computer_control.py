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
import urllib.parse

NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

# ★로케일 비의존 출력(선례 javis_detect.py G9): 윈 파이프의 기본 stdout 은 ANSI 코드페이지(cp949)라 「—」(U+2014)
#   같은 글자에서 UnicodeEncodeError → scan 이 rc 1 로 죽는다(윈 실기 10-26 ①). 마스터의 Bash·PowerShell 도구는
#   이 출력을 UTF-8 로 읽으므로 UTF-8 로 고정한다(콘솔 코드페이지로 쓰면 죽지 않아도 마스터 쪽에서 한글이 깨진다).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
# Claude 데스크톱 앱 MSIX 패키지 = 이름 + 게시자 ID(윈 실기 10-26 Get-AppxPackage: Claude_2.19675.0.0_x64__pzs8sxrjxfjjc).
# 패키지 앱의 사용자 자료 폴더 = %LOCALAPPDATA%\Packages\<이름>_<게시자 ID>(Microsoft Learn · MSIX 문서).
WIN_MSIX_NAME = "Claude"
WIN_MSIX_PUBLISHER = "pzs8sxrjxfjjc"
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


def _sys_codecs():
    """윈 시스템 명령(reg 등) 출력의 코드페이지 — OEM → ANSI 순. 파이썬 UTF-8 모드·로케일이 아니라 운영체제에 묻는다."""
    if os.name != "nt":
        return ["utf-8"]
    try:
        import ctypes
        k = ctypes.windll.kernel32
        return ["cp%d" % k.GetOEMCP(), "cp%d" % k.GetACP()]
    except Exception:
        return ["utf-8"]


def _decode(b):
    """바이트 → 문자열. 어느 코드페이지로도 안 풀리면 대체 문자로(디코드 실패가 칸 판정을 바꾸지 않는다)."""
    for enc in _sys_codecs():
        try:
            return b.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return b.decode("utf-8", "replace")


def _run(argv):
    """외부 호출 1회 · 5초 상한 · 표준입력 없음(윈 콘솔 없는 상속 핸들 방지). 실패 = None.
    ★출력은 바이트로 받아 _decode 로 푼다 — text=True 는 UTF-8 모드(PYTHONUTF8=1 · 좌석 기본)에서 reg 의 cp949 출력에
    UnicodeDecodeError 를 낸다(윈 실기 10-26 ②)."""
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=SUBPROC_TIMEOUT, **NOWIN)
    except (OSError, subprocess.SubprocessError):
        return None
    r.stdout = _decode(r.stdout) if isinstance(r.stdout, bytes) else (r.stdout or "")
    r.stderr = _decode(r.stderr) if isinstance(r.stderr, bytes) else (r.stderr or "")
    return r


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
        "chrome_default": _chrome_default(d),
        "connectors": [str(x) for x in ever if isinstance(x, str)] if isinstance(ever, list) else [],
        "project_cu": {k: ("computer-use" in v.get("enabledMcpServers"))
                       for k, v in projects.items()
                       if isinstance(v, dict) and isinstance(v.get("enabledMcpServers"), list)},
        "project_keys": [k for k in projects.keys() if isinstance(k, str)],
    }


def _chrome_default(d):
    """크롬 「Enabled by default」 — True/False/None(값이 이상함).
    ★키 없음 = 꺼짐(윈 실기 10-26: 좌석 설정 폴더에 키가 없어 「모름」이던 것). 근거 = Claude Code 2.1.310 시작 판정
    (--chrome → CLAUDE_CODE_ENABLE_CFC → 이 키 · 없으면 false) · 공식 문서는 --chrome 없이 켜려면 /chrome 의 Enabled by default 를
    고르라고 한다 · cysr 좌석은 --chrome 없이 뜬다(agents.json cmd). 좌석이 쓰는 설정(CLAUDE_CONFIG_DIR)만 본다."""
    if "claudeInChromeDefaultEnabled" not in d:
        return False
    v = d["claudeInChromeDefaultEnabled"]
    return v if isinstance(v, bool) else None


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
    """Claude 데스크톱 앱 설치 — True/False/None(확인 못 함). 폴더 존재·이름만 본다.
    사용자 쪽 근거(설치 폴더 · MSIX 사용자 자료 폴더)가 먼저 · 없으면 WindowsApps 이름 목록(권한 거부가 흔하다 → None)."""
    la = os.environ.get("LOCALAPPDATA") or ""
    cands = [os.path.join(la, "AnthropicClaude"), os.path.join(la, "Programs", "Claude"),
             os.path.join(la, "Packages", "%s_%s" % (WIN_MSIX_NAME, WIN_MSIX_PUBLISHER))]
    if la and any(os.path.isdir(c) for c in cands):
        return True
    pf = os.environ.get("ProgramFiles") or ""
    if not pf:
        return None
    try:
        names = os.listdir(os.path.join(pf, "WindowsApps"))
    except OSError:
        return None
    return any(n.startswith(WIN_MSIX_NAME + "_") and n.endswith("_" + WIN_MSIX_PUBLISHER) for n in names)


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
            UNKNOWN_HEAD + " 부분이 있습니다 — 한 번 같이 확인해 주세요."
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
        return HAND, True, [k for k, v in parts if v is None], UNKNOWN_HEAD + " 크롬 연결 부분이 있습니다 — 한 번 같이 확인해 주세요."
    if not unknown and set(missing) <= set(CHROME_AUTO):
        # ★cu-1111-precedent(박사님 10-26 21:0x): 기본 켜기·연결 파일·크롬 다시 켜기 = 마스터가 직접(chrome-enable) → 바로
        return READY, False, missing, "확장은 준비돼 있고, 남은 연결은 제가 직접 켭니다."
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
            "missing": list(missing), "reason": reason, "note": note, "members": [[iid, title]]}


CHROME_AUTO = ("default_on", "nmh")    # 마스터가 chrome-enable 로 직접 하는 것(사용자 손 0)
MISSING_LABEL = {
    "cu": "화면 조작 도구 켜기(/mcp)", "ax": "손쉬운 사용 권한", "sc": "화면 기록 권한",
    "ext": "Claude 확장 설치·켜기", "default_on": "크롬 기본 켜기(제가 합니다)", "nmh": "연결 파일·크롬 다시 켜기(제가 합니다)",
}
MERGE_KINDS = ("script", "files")
UNKNOWN_HEAD = "켜져 있는지 제가 확인하지 못한"


def _with_missing(reason, missing, unknown=False):
    """빠진 것 이름을 붙인다. 판정 = 모름뿐(꺼짐 확인 0)이면 「남은 것」이 아니라 「확인할 것」이다(VM 실기 교정)."""
    names = [MISSING_LABEL[m] for m in missing if m in MISSING_LABEL]
    if not names:
        return reason
    head = (" 확인할 것: " if unknown and reason.startswith(UNKNOWN_HEAD)
            else " 제가 할 것: " if all(m in CHROME_AUTO for m in missing) else " 남은 것: ")
    return reason + head + " · ".join(names) + "."


def raw_items(plat, project, cfg=None):
    """판정 단위 항목(합치기 전). 같은 판정의 스크립트·폴더 줄은 merge_items 가 한 줄로 접는다."""
    cfg = cfg if cfg is not None else claude_cfg()
    items = []
    c = probe_chrome(plat, cfg)
    t, u, m, r = verdict_chrome(plat, c)
    items.append(_item("chrome", "크롬으로 웹 일(로그인된 지메일·구글 문서·클라우드플레어 화면 등)", t, u, m,
                       _with_missing(r, m, u)))
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
            dk = _win_claude_desktop()
            sr += " (Claude 데스크톱 앱: %s)" % ("이 컴퓨터에 설치돼 있습니다" if dk
                                              else "? — 설치돼 있는지 확인하지 못했습니다" if dk is None
                                              else "찾지 못했습니다 — 설치 위치가 다를 수 있습니다")
    apps = probe_apps(plat)
    if plat == "darwin":
        names = [name for aid, name, _px, _n in MAC_APPS if aid in apps]
        notes = [n for aid, _name, _px, n in MAC_APPS if aid in apps and n]
    else:
        names = [name for aid, name, _p in WIN_APPS if aid in apps]
        notes = []
    title = "데스크톱 앱 화면 조작" + ("(이 컴퓨터의 앱: %s)" % "·".join(names) if names else "")
    items.append(_item("screen", title, st, su, sm, _with_missing(sr, sm, su), " ".join(notes)))

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
    merged = dict(_item(kind + ":" + ",".join(it["id"].split(":", 1)[1] for it in group), title, worst["tier"],
                        any(it["unknown"] for it in group), missing, worst["reason"]), name="·".join(names))
    merged["members"] = [m for it in group for m in it["members"]]   # ★codex 1R #2: 저장·철회 단위 = 구성원
    return merged


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
    # ★(chrome, default_on)·(chrome, nmh) 손 단계는 없앴다 — 마스터가 chrome-enable 로 직접 한다(cu-1111-precedent).
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
    "chrome": "크롬 연결 설정까지 끄기를 원하시면 「크롬 연결도 꺼 줘」라고 말씀해 주세요 — 제가 끕니다.",
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
def member_ids(iid):
    """`script:mail,calendar` → [`script:mail`, `script:calendar`] · 단일 ID 는 그대로."""
    kind, _, rest = iid.partition(":")
    if kind in MERGE_KINDS and "," in rest:
        return [kind + ":" + x for x in rest.split(",") if x]
    return [iid]


def load_grants():
    """장부 — 키는 언제나 구성원 ID 다(codex 1R #2). 옛 합친 키는 읽을 때 구성원으로 펼친다(active 가 이긴다)."""
    g = _read_json(_p("grants.json"))
    if not isinstance(g, dict) or not isinstance(g.get("items"), dict):
        return {"items": {}}
    items = {}
    for k, v in g["items"].items():
        if not isinstance(v, dict):
            continue
        for mid in member_ids(k):
            cur = items.get(mid)
            if cur is None or (v.get("state") == "active" and cur.get("state") != "active"):
                items[mid] = dict(v)
    g["items"] = items
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
    scan_id = "s" + os.urandom(4).hex()   # ★codex 1R #1: 사용자가 본 목록 = 이 ID(grant 가 같은 ID 를 내야 한다)
    _write_json(_p("scan.json"), {"ts": _now(), "at": _iso(), "platform": plat, "measured_on": MEASURED_ON,
                                  "scan_id": scan_id, "project": os.path.realpath(_project()), "items": items})
    return out({"ok": True, "scan_id": scan_id, "platform": plat,
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


def _fresh_scan(scan_id=None):
    s = load_scan()
    if s is None:
        return None, fail("먼저 컴퓨터를 한 번 살펴봐야 합니다 — 「내 컴퓨터에서 맡을 수 있는 걸 찾아 줘」라고 말씀해 주세요.",
                          "no_scan", 7)
    if _now() - float(s.get("ts") or 0) > SCAN_TTL_SEC:
        return None, fail("살펴본 지 시간이 좀 지났습니다 — 다시 한 번 살펴본 뒤 고르시게 할게요.", "stale_scan", 7)
    if scan_id != s.get("scan_id") or os.path.realpath(_project()) != s.get("project"):
        # ★codex 1R #1: 그 사이 다른 대화·폴더에서 다시 살펴봐 번호가 바뀌었을 수 있다 — 옛 번호로 넘기지 않는다
        return None, fail("보여 드린 목록이 그 사이 바뀌었습니다 — 다시 살펴본 목록에서 골라 주세요.", "scan_replaced", 7)
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
    s, err = _fresh_scan(a.scan)
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
        for mid, mtitle in it.get("members") or [[it["id"], it["title"]]]:
            g["items"][mid] = {"state": state, "title": mtitle, "at": _iso()}
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
    # 사용자가 직접 고른 것 = 전에 「빼라」 한 상시 기록을 푼다
    d = load_decisions()
    lift = [k for it in granted + pending for m, _t in (it.get("members") or [[it["id"], it["title"]]])
            for k in ["take:%s" % m] if k in d["items"]]
    # ★codex 1R #3: 감사 기록이 먼저다 — 기록이 실패하면(예외) 장부는 바뀌지 않는다(기록 없는 active 0)
    _ledger({"event": "grant", "scan_id": s.get("scan_id"), "picks": sorted(set(picks)),
             "active": [it["id"] for it in granted], "pending": [it["id"] for it in pending],
             "refused": [it["id"] for it in refused],
             "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest()})
    save_grants(g)
    if lift:
        for k in lift:
            d["items"].pop(k, None)
        _write_json(_p(DECISIONS), d)
    lines = []
    if granted:
        lines.append("지금부터 제가 맡겠습니다: " + ", ".join(it["title"].split("(")[0].strip() for it in granted) + ".")
    for it in granted:
        if first_use_only(it):
            lines.append("「%s」 — %s" % (it["title"].split("(")[0].strip(), it["reason"]))
    auto = [it["id"] for it in granted if it["id"] == "chrome" and it["missing"]]
    if auto:
        lines.append("크롬 연결 설정은 제가 바로 켜겠습니다(끝나면 짧게 알려 드립니다).")
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
                "next_action": "chrome-enable" if auto else None,
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
    titles = {mid: (t or mid).split("(")[0].strip() for mid, t in (it.get("members") or [[it["id"], it["title"]]])}
    # ★codex R2: 합친 줄의 상태를 첫 구성원으로 대표하지 않는다 — 구성원마다 장부에 실제로 있는지·상태를 따로 본다
    held = [m for m in member_ids(a.id) if m in g["items"]]
    if first_use_only(it):
        return out({"ok": True, "tier": it["tier"], "states": {m: g["items"][m].get("state") for m in held},
                    "say": "이건 지금 하실 것이 없습니다 — %s" % it["reason"]})
    if it["tier"] == READY:
        flip = [m for m in held if g["items"][m].get("state") != "active"]
        if flip:
            _ledger({"event": "activate", "ids": flip})          # ★codex 1R #3: 기록 먼저 · 실패면 장부 불변
            for m in flip:
                g["items"][m]["state"] = "active"
                g["items"][m]["at"] = _iso()
            save_grants(g)
        not_held = [m for m in member_ids(a.id) if m not in held]
        lines = []
        if held:
            lines.append("확인했습니다. 「%s」은(는) 이제 제가 맡습니다." % "·".join(titles.get(m, m) for m in held))
        if not_held:
            lines.append("「%s」은(는) 준비돼 있지만 맡기지 않으셨습니다." % "·".join(titles.get(m, m) for m in not_held))
        return out({"ok": True, "tier": READY, "states": {m: g["items"][m].get("state") for m in held},
                    "say": " ".join(lines)})
    st = steps_for(it)
    tail = (" 남은 단계: " + st[0]) if st else ""
    return out({"ok": True, "tier": it["tier"], "states": {m: g["items"][m].get("state") for m in held},
                "say": "아직 덜 됐습니다 — %s%s" % (it["reason"], tail)})


def cmd_revoke(a):
    g = load_grants()
    mids = [m for m in member_ids(a.id) if m in g["items"]]   # ★codex 1R #2: 합친 ID 면 구성원 전부를 거둔다
    if not mids and a.id not in g.get("folders", {}):
        return fail("그 항목은 맡고 있지 않습니다.", "not_found", 4)
    if mids:
        titles = [(g["items"].pop(m).get("title") or m).split("(")[0].strip() for m in mids]
        title, hint = "·".join(titles), REVOKE_HINT.get(_kind(a.id), "")
    else:
        g["folders"].pop(a.id, None)
        title, hint = "폴더 " + (os.path.basename(a.id) or a.id), REVOKE_HINT["files"]
    save_grants(g)   # 거둠은 저장이 먼저다 — 기록이 실패해도 남는 쪽이 안전한 상태(맡지 않음)
    _ledger({"event": "revoke", "ids": mids or ["folder"]})
    if mids:          # 상시 기록 — adopt 가 다음에 다시 가져오지 않는다(사용자가 고르면 grant 가 지운다)
        d = load_decisions()
        for m in mids:
            d["items"]["take:%s" % m] = {"meaning": "deny", "condition": "", "at": _iso(), "by": "revoke"}
        _write_json(_p(DECISIONS), d)
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
    if a.meaning != "yes":
        # ★codex 1R(논쟁점): 「아니요」도 빈 답이 아니다 — 승낙의 뜻은 마스터가 판단해 명시하고, yes 가 아니면 띄우지 않는다
        _ledger({"event": "request_prompt_declined", "which": a.which, "meaning": a.meaning})
        return fail("알겠습니다. 요청 창은 띄우지 않겠습니다.", "not_yes", 5)
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


# ───────────────────────── 크롬 켜기·끄기 = 마스터가 직접 (TICKET=cu-1111-precedent · 설계 §6-2) ─────────────────────────
# 박사님 원문(10-26 21:0x) 「크롬 조작을 위해 /chrome 실행, 크롬 껐다켜기 같은 작업을 주인에게 시키지 말고 마스터가 직접 하는
#   방법을 찾아라.」 → 사용자 손 칸이던 ①「/chrome 기본 켜기」 ②연결 파일(NMH) ③크롬 다시 켜기 ④좌석 재시작을 이 동작이 한다.
# ① = 좌석 설정 폴더 .claude.json 의 claudeInChromeDefaultEnabled **한 키만**(공식 /chrome·/config 토글이 쓰는 바로 그 키 —
#     Claude Code 2.1.310 시작 판정 --chrome → CLAUDE_CODE_ENABLE_CFC → 이 키). 다른 키는 읽은 그대로 되쓴다.
# ② = 좌석 설정으로 `claude -p --chrome` 1회(Claude Code 가 연결 파일을 만든다 · 윈 실기 10-26 20:3x 실측 길).
# ③ = 「연결 파일을 이번에 새로 만들었고 크롬이 그 전부터 켜져 있었다」일 때만. 키보드·마우스 유휴 ≥ 20초 관문 → 화면 알림 1줄 →
#     정상 종료(맥 quit · 윈 CloseMainWindow — 강제 종료 0) → --restore-last-session 으로 다시 켬 → 창 수 전후 대조.
# ④ = 이 좌석의 대화가 끝난 뒤(지연) `cys rotate --skip-depts`(앱 ↻ 재시작 단추와 같은 저장 검증 → 복원 · 대화 이어짐).
# 외부 명령은 전부 _act 를 지난다 — 시험은 CYS_CC_FAKE_ACT(기록 파일)로 실제 크롬·좌석을 건드리지 않는다.
IDLE_GATE_SEC = 20
SEAT_RESTART_DELAY_SEC = 30
CHROME_QUIT_WAIT_SEC = 20
CHROME_STATE = "chrome-enable.json"
CLAUDE_HEADLESS_TIMEOUT = 90
CHROME_KEY = "claudeInChromeDefaultEnabled"


def _act(kind, argv, timeout=SUBPROC_TIMEOUT, detach=False, cwd=None):
    """크롬 켜기 동작의 외부 명령 1회. 시험 = CYS_CC_FAKE_ACT(경로)에 기록만 하고 결과는 FAKE_PROBES["act"][kind] 로 낸다."""
    log = os.environ.get("CYS_CC_FAKE_ACT")
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": kind, "argv": argv, "detach": detach, "cwd": cwd}, ensure_ascii=False) + "\n")
        acts = _fake("act") or {}
        seq = acts.get(kind)
        if isinstance(seq, list):     # 같은 kind 를 여러 번 부르면 차례대로(마지막 값 유지)
            with open(log, encoding="utf-8") as f:
                n = sum(1 for x in f if json.loads(x).get("kind") == kind)
            seq = seq[min(n, len(seq)) - 1] if seq else None
        r = seq if isinstance(seq, dict) else {}
        hook = r.get("touch")         # 더블: 이 동작이 만들 파일(예: 헤드리스 claude 가 만드는 연결 파일)
        if hook:
            for path, body in hook.items():
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(body)
        return subprocess.CompletedProcess(argv, r.get("rc", 0), r.get("out", ""), "")
    if detach:
        try:
            kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if os.name == "nt":
                # NEW_PROCESS_GROUP · NO_WINDOW — 숨은 새 콘솔이라 좌석 콘솔이 닫혀도 살고 자손(cys 호출)이 그 콘솔을 물려받는다
                #   (콘솔 떼기는 자손마다 새 창이 뜬다 = U5-WIN-FLASH · H-WIN-16)
                kw["creationflags"] = 0x00000200 | 0x08000000
            else:
                kw["start_new_session"] = True     # 좌석 pty 가 닫혀도 살아남는다(재시작이 그 pty 를 닫는다)
            subprocess.Popen(argv, **kw)
            return subprocess.CompletedProcess(argv, 0, "", "")
        except OSError:
            return None
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, cwd=cwd, **NOWIN)
    except (OSError, subprocess.SubprocessError):
        return None
    r.stdout = _decode(r.stdout) if isinstance(r.stdout, bytes) else (r.stdout or "")
    return r


def _fake_seq(key):
    """시험 주입 값 — 목록이면 부를 때마다 다음 값(마지막 값 유지)."""
    v = _fake(key)
    if isinstance(v, list):
        k = "_seq_" + key
        i = globals().get(k, 0)
        globals()[k] = i + 1
        return v[min(i, len(v) - 1)] if v else None
    return v


def _claude_json():
    return os.path.join(claude_config_dir(), ".claude.json")


def read_chrome_key():
    """(있음 여부, 값). 파일을 못 읽으면 (None, None)."""
    d = _read_json(_claude_json())
    if not isinstance(d, dict):
        return None, None
    return (CHROME_KEY in d), d.get(CHROME_KEY)


def _read_raw(path):
    try:
        with open(path, "rb") as f:
            return f.read(MAX_JSON_BYTES + 1)
    except OSError:
        return None


CAS_TRIES = 3
LOCK_WAIT_SEC = 5


def _config_lock(path):
    """Claude Code 와 같은 설정 잠금 — `<.claude.json>.lock` 폴더 mkdir(원자적 · proper-lockfile 방식).
    근거(2.1.310 바이너리 원문): saveConfigWithLock 이 `let P=${y}.lock`(템플릿 문자열 · y = 전역 설정 파일)로 잠그고, 잠금 **안에서 파일을
    다시 읽어** 갱신 함수를 적용한 뒤 쓴다 → 우리가 잠근 동안 Claude 는 기다리고, 풀리면 우리 결과를 다시 읽는다.
    남이 쥔 잠금은 지우지 않는다(오래된 것 포함) — 5초 안에 못 잡으면 쓰지 않는다. 반환 = 잠금 경로 · None."""
    lock = path + ".lock"
    waited = 0.0
    while True:
        try:
            os.mkdir(lock)
            return lock
        except FileExistsError:
            if waited >= LOCK_WAIT_SEC:
                return None
            time.sleep(0.1)
            waited += 0.1
        except OSError:
            return None


def write_chrome_key(value):
    """좌석 .claude.json 의 크롬 키 **하나만** 바꾼다(value=None 이면 키를 지운다 = 원래 없던 상태). 나머지 칸은 읽은 그대로.
    ★codex R1·R2(동시 쓰기): Claude Code 와 같은 잠금(`.claude.json.lock`)을 쥔 채 **잠금 안에서** 다시 읽고 → 키 하나 바꾸고 →
    원자 교체 → 잠금 해제. 덧붙여 교체 직전 원본 바이트 재확인(잠금을 안 지키는 작성자 대비 · 최대 3회 · 끝내 다르면 무변경 실패).
    파일 권한 유지 · 쓴 뒤 다시 읽어 확인. 성공 = True."""
    path = _claude_json()
    lock = _config_lock(path)
    if lock is None:
        _ledger({"event": "chrome_key_lock_busy"})
        return False
    try:
        for _try in range(CAS_TRIES):
            raw = _read_raw(path)
            if raw is None or len(raw) > MAX_JSON_BYTES:
                return False
            try:
                d = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return False
            if not isinstance(d, dict):
                return False
            if value is None:
                d.pop(CHROME_KEY, None)
            else:
                d[CHROME_KEY] = value
            try:
                mode = os.stat(path).st_mode & 0o777
            except OSError:
                return False
            tmp = "%s.cc-tmp-%d" % (path, os.getpid())
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
            os.chmod(tmp, mode)
            _cas_hook()
            if _read_raw(path) != raw:          # 그 사이 누가 고쳐 썼다 — 덮지 않는다
                os.remove(tmp)
                continue
            os.replace(tmp, path)
            has, v = read_chrome_key()
            return (not has) if value is None else (has and v is value)
        _ledger({"event": "chrome_key_conflict", "tries": CAS_TRIES})
        return False
    finally:
        try:
            os.rmdir(lock)
        except OSError:
            pass


def _cas_hook():
    """시험 주입점 — 교체 직전에 다른 쓰기를 끼워 넣는다(실제 실행에서는 아무것도 안 함)."""
    return None


NMH_REG_KEY = r"HKCU\Software\Google\Chrome\NativeMessagingHosts\%s" % NMH_NAME


def _nmh_reg_value():
    """윈 연결 등록의 기본값(가리키는 매니페스트 경로) — 없으면 None."""
    r = _act("nmh_reg_query", ["reg", "query", NMH_REG_KEY, "/ve"])
    if r is None or r.returncode != 0:
        return None
    m = re.search(r"REG_SZ\s+(.+)$", r.stdout or "", re.M)
    return m.group(1).strip() if m else None


def _nmh_manifest_path(plat):
    if plat == "darwin":
        return os.path.join(_chrome_userdata(plat), "NativeMessagingHosts", NMH_NAME + ".json")
    return None   # 윈 = 레지스트리 키가 가리키는 파일(Claude Code 가 만든다)


def _sha_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def chrome_running(plat):
    if _has_fake("chrome_running"):
        return _fake_seq("chrome_running")
    if plat == "darwin":
        r = _act("chrome_running", ["/usr/bin/pgrep", "-x", "Google Chrome"])
        return None if r is None else r.returncode == 0
    if plat == "win":
        r = _act("chrome_running", ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"])
        return None if r is None else "chrome.exe" in (r.stdout or "").lower()
    return None


def idle_seconds(plat):
    """사용자 입력 유휴 초 — 맥 HIDIdleTime · 윈 GetLastInputInfo. 못 재면 None(→ 관문 닫힘 = 기다림)."""
    if _has_fake("idle"):
        return _fake_seq("idle")
    if plat == "darwin":
        r = _act("idle", ["/usr/sbin/ioreg", "-c", "IOHIDSystem", "-d", "4"])
        m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', (r.stdout if r else "") or "")
        return int(m.group(1)) / 1e9 if m else None
    if plat == "win":
        try:
            import ctypes

            class LII(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            li = LII()
            li.cbSize = ctypes.sizeof(LII)
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
                return None
            return ((ctypes.windll.kernel32.GetTickCount() - li.dwTime) & 0xFFFFFFFF) / 1000.0
        except Exception:
            return None
    return None


CHROME_COUNT_SCRIPT = ('tell application "Google Chrome"\nset t to 0\nrepeat with w in windows\n'
                       'set t to t + (count tabs of w)\nend repeat\nreturn ((count windows) as text) & " " & (t as text)\nend tell')


def chrome_windows(plat):
    """(창 수, 탭 수) — 전후 대조용. 모르면 None. 맥 = 크롬 자동화 허락(0)이 있을 때만 osascript 로 센다(없으면 허락 창을
    띄우지 않으려고 세지 않는다) · 윈 = 창 손잡이가 있는 크롬 프로세스 수(근사) · 탭은 셀 길이 없음(None)."""
    if _has_fake("windows"):
        v = _fake_seq("windows")
        return (v, None) if isinstance(v, int) else (tuple(v) if isinstance(v, list) else (None, None))
    if plat == "darwin":
        if probe_ae("com.google.Chrome") != 0:
            return None, None
        r = _act("windows", ["/usr/bin/osascript", "-e", CHROME_COUNT_SCRIPT])
        m = re.match(r"\s*(\d+)\s+(\d+)\s*$", (r.stdout if r and r.returncode == 0 else "") or "")
        return (int(m.group(1)), int(m.group(2))) if m else (None, None)
    if plat == "win":
        r = _act("windows", ["powershell", "-NoProfile", "-Command",
                             "(Get-Process chrome -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne 0}).Count"])
        w = (r.stdout or "").strip() if r and r.returncode == 0 else ""
        return (int(w) if w.isdigit() else None), None
    return None, None


def _chrome_exe():
    for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        if os.environ.get(v):
            c = os.path.join(os.environ[v], "Google", "Chrome", "Application", "chrome.exe")
            if os.path.isfile(c):
                return c
    return "chrome.exe"


def quit_chrome(plat):
    """정상 종료만(강제 종료 0). 맥 = 크롬 자동화 허락이 있으면 AppleScript quit, 없으면 이 사용자의 크롬 **본 프로세스 pid 하나**에
    종료 신호(SIGTERM — 크롬이 정상 종료로 처리해 세션을 저장한다 · SIGKILL 아님 · 이름 일치 일괄 종료(pkill) 금지 = 워커 지침 §1-4).
    윈 = 창마다 CloseMainWindow(닫기 단추와 같다)."""
    if plat == "darwin":
        if probe_ae("com.google.Chrome") == 0:
            return _act("quit", ["/usr/bin/osascript", "-e", 'tell application "Google Chrome" to quit'])
        r = _act("chrome_pid", ["/usr/bin/pgrep", "-u", str(os.getuid()), "-o", "-x", "Google Chrome"])
        pid = (r.stdout or "").strip() if r and r.returncode == 0 else ""
        if not pid.isdigit():
            return None
        return _act("quit", ["/bin/kill", "-TERM", pid])
    return _act("quit", ["powershell", "-NoProfile", "-Command",
                         "Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object { [void]$_.CloseMainWindow() }"])


def open_chrome(plat):
    if plat == "darwin":
        return _act("open", ["/usr/bin/open", "-a", "Google Chrome", "--args", "--restore-last-session"])
    return _act("open", [_chrome_exe(), "--restore-last-session"], detach=True)


def notify(title, body):
    """화면 알림 1줄(cysr Feed · 정보성 — 승인 요청 아님 · 채널 미러 금지 tier d). 실패해도 진행을 막지 않는다."""
    return _act("notify", ["cys", "feed", "push", "--kind", "computer-control", "--tier", "d",
                           "--title", title, "--body", body])


def _sleep(sec):
    if os.environ.get("CYS_CC_FAKE_ACT"):
        return
    time.sleep(sec)


def _cys_bin():
    return os.environ.get("CYS_BIN") or "cys"


SEAT_IDLE_SEC = 20          # 좌석 출력이 이만큼 조용하면 턴이 끝난 것으로 본다(두 번 연속)
SEAT_WAIT_MAX_SEC = 900     # 그때까지 안 끝나면 재시작하지 않고 빚으로 남긴다(다음 chrome-enable 이 다시 예약)


def schedule_seat_restart(delay):
    """이 좌석의 턴이 **실제로 끝난 뒤** 재시작 — 분리된 프로세스(이 도구의 seat-restart-wait)가 delay 초 뒤부터 좌석 출력 유휴
    (`cys status --json` idle_secs ≥ 20 두 번 연속)를 확인하고 `cys rotate --skip-depts`(앱 ↻ 와 같은 저장 검증 → 복원)를 부른다.
    ★codex R1 논쟁점: 고정 30초만으로는 긴 턴을 끊을 수 있었다. 좌석 ID 를 모르면(좌석 밖) 고정 지연으로 폴백."""
    sid = os.environ.get("CYS_SURFACE_ID") or ""
    argv = [sys.executable, os.path.abspath(__file__), "seat-restart-wait", "--min-delay", str(delay)]
    if sid:
        argv += ["--surface", sid]
    return _act("seat_restart", argv, detach=True)


def _seat_status(sid):
    """그 좌석의 (출력 유휴 초, 세션 ID) — `cys status --json`. 못 읽으면 (None, None)."""
    r = _act("seat_status", [_cys_bin(), "status", "--json"], timeout=15)
    try:
        d = json.loads(r.stdout) if r and r.returncode == 0 else None
    except ValueError:
        d = None
    for srf in (d or {}).get("surfaces") or []:
        if str(srf.get("surface_id")) == sid.replace("surface:", "") or srf.get("surface_ref") == sid:
            v = srf.get("idle_secs")
            return (v if isinstance(v, (int, float)) else None), srf.get("registered_session_id")
    return None, None


def _turn_ended(session_id):
    """★codex R2: 출력이 조용한 것은 턴 종료의 증거가 아니다(도구 대기 중에도 조용하다). 좌석 자신의 세션 기록 마지막 대화 줄이
    「assistant · stop_reason = end_turn」이어야 턴이 끝난 것이다. 읽는 칸 = type·stop_reason 뿐(내용 0). True/False/None(못 읽음)."""
    if not session_id or not re.match(r"^[0-9a-fA-F-]{8,64}$", str(session_id)):
        return None
    root = os.path.join(claude_config_dir(), "projects")
    hit = None
    for dirpath in _listdir(root):
        cand = os.path.join(root, dirpath, "%s.jsonl" % session_id)
        if os.path.isfile(cand):
            hit = cand
            break
    if not hit:
        return None
    try:
        with open(hit, "rb") as f:
            f.seek(max(0, os.path.getsize(hit) - 256 * 1024))
            tail = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for line in reversed(tail):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        t = e.get("type") if isinstance(e, dict) else None
        if t == "assistant":
            msg = e.get("message") if isinstance(e.get("message"), dict) else {}
            return msg.get("stop_reason") == "end_turn"
        if t == "user":
            return False
    return None


def cmd_seat_restart_wait(a):
    """(분리된 프로세스 전용) 좌석 턴이 **끝난 것이 확인되면** 재시작. 좌석·세션을 모르거나 15분 안에 확인 못 하면 재시작하지 않고
    빚(pending_seat_restart)으로 남긴다 · rotate 가 실패해도 빚은 남는다(성공해야 지운다 · codex R2)."""
    def owe(why):
        st = _load_chrome_state()
        st["pending_seat_restart"] = True
        st.pop("seat_restart_scheduled_at", None)
        _write_json(_p(CHROME_STATE), st)
        _ledger({"event": "seat_restart_not_done", "why": why})
        return out({"ok": False, "say": "", "reason": why}, 0)
    if not a.surface:
        return owe("no_surface")
    _sleep(a.min_delay)
    quiet, waited = 0, a.min_delay
    while True:
        idle, sess = _seat_status(a.surface)
        ok = idle is not None and idle >= SEAT_IDLE_SEC and _turn_ended(sess) is True
        quiet = quiet + 1 if ok else 0
        if quiet >= 2:
            break
        if waited >= SEAT_WAIT_MAX_SEC:
            return owe("busy")
        _sleep(5)
        waited += 5
    r = _act("rotate", [_cys_bin(), "rotate", "--skip-depts"], timeout=600)
    rc = None if r is None else r.returncode
    _ledger({"event": "seat_restart_rotate", "rc": rc})
    if rc not in (0, 21, 25):          # 21·25 = rotate 의 「끝까지 돌았지만 일부 부족」(중단 아님 · cys.rs rotate_rc 표)
        return owe("rotate_rc_%s" % rc)
    st = _load_chrome_state()
    st.pop("pending_seat_restart", None)
    st.pop("seat_restart_scheduled_at", None)
    _write_json(_p(CHROME_STATE), st)
    return out({"ok": True, "say": ""}, 0)


def _load_chrome_state():
    s = _read_json(_p(CHROME_STATE))
    return s if isinstance(s, dict) else {}


def _ensure_nmh(plat):
    """연결 파일이 없거나 끊겼으면 좌석 설정으로 헤드리스 `claude -p --chrome` 1회 → 만들어졌는지 다시 본다.
    반환 (상태, 이번에 만들었나). 상태 = True/False/None."""
    before = _nmh_ok(plat, _chrome_userdata(plat))
    if before is True:
        return True, False
    claude = os.environ.get("CYS_CC_CLAUDE_BIN") or "claude"
    work = os.path.join(state_dir(), "chrome-probe")
    os.makedirs(work, exist_ok=True)
    # 도구 0(--tools "") · 크롬 도구도 막음 — 연결 파일은 크롬 연동이 켜진 채 **시작**할 때 만들어진다(도구 호출 불필요)
    argv = [claude, "-p", "--chrome", "--max-turns", "1", "--tools", "",
            "--disallowedTools", "mcp__claude-in-chrome", "응답 없이 끝내세요."]
    r = _act("nmh", argv, timeout=CLAUDE_HEADLESS_TIMEOUT, cwd=work)
    if r is None:
        return before, False
    after = _nmh_ok(plat, _chrome_userdata(plat))
    return after, (after is True and before is not True)


def cmd_chrome_enable(a):
    plat = platform()
    if plat not in ("darwin", "win"):
        return fail("이 컴퓨터에서는 크롬 연결을 제가 켤 수 없습니다.", "platform", 5)
    cfg = claude_cfg()
    c = probe_chrome(plat, cfg)
    if not c.get("app"):
        return fail("이 컴퓨터에서 크롬을 찾지 못했습니다. 크롬을 설치하시면 다시 살펴볼게요.", "no_chrome", 5)
    st = _load_chrome_state()
    done, said = [], []
    # ① 기본 켜기(한 키)
    has, v = read_chrome_key()
    if has is None:
        return fail("클로드 설정 파일을 읽지 못해 크롬 연결을 켜지 못했습니다.", "claude_json", 1)
    def keep_prior():
        # 처음 손대기 전의 원래 값만 기억한다(되돌리기 = 이 값) · ★codex R1: 되돌리기 정보가 바꾸기보다 먼저 디스크에
        # ★codex R3: 키가 이미 켜져 있어 연결 파일만 만들 때도 기억한다(안 그러면 끄기가 원래 true 를 false 로 씀) ·
        #   새로 켜면 앞선 끄기의 「키 되돌림 끝」 표지를 지운다(안 그러면 다음 끄기가 키 되돌리기를 건너뜀)
        # ★codex R4: 앞 주기의 키를 이미 되돌렸으면 새 주기다 — 원래 값 = 지금 값(그 사이 사용자가 바꾼 값을 옛 값으로 덮지 않는다)
        if "prior_key" not in st or st.get("key_restored"):
            st["prior_key"] = {"present": has, "value": v}
            st.pop("key_restored", None)
            _write_json(_p(CHROME_STATE), st)
    if v is not True:
        keep_prior()
        _ledger({"event": "chrome_enable_key", "prior": {"present": has, "value": v}})   # 기록 먼저
        if not write_chrome_key(True):
            return fail("크롬 기본 켜기를 저장하지 못했습니다(그 사이 다른 프로그램이 설정을 고쳐 써서 손대지 않았습니다 — 잠시 뒤 다시 하겠습니다).",
                        "write_failed", 1)
        done.append("default_on")
    # ② 연결 파일 — ★codex R1·R2: 처음 만들 때 Claude Code 가 크롬에 「다시 연결」 탭을 연다(바이너리 문자열) → 크롬이 켜져 있든
    #   꺼져 있든(꺼져 있으면 크롬이 떠오른다) 앞으로 나온 창에 타이핑이 샐 수 있으므로 유휴 관문 뒤에만 만든다(못 채우면 미룸)
    was_running = chrome_running(plat)
    nmh_missing = _nmh_ok(plat, _chrome_userdata(plat)) is not True
    if nmh_missing and not wait_idle(plat, a.wait):   # ★codex R2: 꺼진 크롬도 탭이 크롬을 띄울 수 있다
        # 연결 파일이 아직 없으니 크롬 재시작 빚은 없다(다음 호출이 만들고 그때 판단) · 좌석 재시작만 빚으로
        if (done and a.seat_restart == "auto") or a.seat_restart == "now":
            st["pending_seat_restart"] = True
        _write_json(_p(CHROME_STATE), st)
        _ledger({"event": "chrome_nmh_deferred"})
        head = "크롬 기본 켜기를 켰습니다." if done else "크롬 연결은 준비 중입니다."
        return out({"ok": True, "done": done, "pending": ["nmh"], "nmh": False,
                    "say": head + " 지금 키보드·마우스를 쓰고 계셔서 연결 파일 만들기는 잠시 미뤘습니다 — 손을 쉬실 때 다시 하겠습니다."})
    if nmh_missing:
        keep_prior()
    nmh, created = _ensure_nmh(plat)
    if created:
        man = _nmh_manifest_path(plat)
        reg = _nmh_reg_value() if plat == "win" else None     # ★codex R2: 윈 매니페스트 = 등록값이 가리키는 파일
        st["nmh_created"] = {"path": man, "sha256": _sha_file(man or reg) if (man or reg) else None, "plat": plat,
                             "reg": reg}
        _write_json(_p(CHROME_STATE), st)
        _ledger({"event": "chrome_enable_nmh", "path": man})
        done.append("nmh")
    elif nmh is not True:
        said.append("크롬 연결 파일을 만들지 못했습니다 — 다음 대화를 시작할 때 다시 해 보겠습니다.")
    # ③ 크롬 다시 켜기 — 연결 파일이 새로 생겼고 크롬이 그 전부터 켜져 있을 때만, 또는 앞 호출이 미뤄 둔 재시작(빚)
    #   ★agy R1 blocking: 미룬 뒤 다음 턴에 다시 부르면 키·연결 파일이 이미 있어 created=False → 재시작이 영영 빠졌다.
    #   빚은 상태 파일(pending_chrome_restart · pending_seat_restart)에 남기고 갚을 때 지운다.
    pending = []
    owed = bool(st.get("pending_chrome_restart"))
    if (created or owed) and was_running:
        r = restart_chrome(plat, a.wait)
        if r == "deferred":
            pending.append("chrome_restart")
            said.append("지금 키보드·마우스를 쓰고 계셔서 크롬 다시 켜기는 잠시 미뤘습니다 — 손을 쉬실 때 다시 하겠습니다.")
        elif r.startswith("not_quit"):
            pending.append("chrome_restart")
            said.append("크롬이 스스로 닫히지 않아 그대로 두었습니다(강제로 끄지 않습니다). 크롬을 닫으셨다 켜시면 바로 연결됩니다.")
        else:
            done.append("chrome_restart")
            said.append(r)
    elif (created or owed) and was_running is None:
        pending.append("chrome_restart")
        said.append("크롬이 켜져 있는지 확인하지 못해 다시 켜기는 미뤘습니다.")
    # (owed ∧ 크롬이 그 사이 꺼짐 = 다음에 켤 때 연결 파일을 읽는다 → 빚 청산)
    # ④ 좌석 재시작 — 이번에 켠 것이 있거나 앞 호출이 미뤄 둔 재시작이 있으면(설정은 새로 시작하는 대화부터 적용된다)
    changed = "default_on" in done or "nmh" in done
    want_seat = a.seat_restart == "now" or (a.seat_restart == "auto" and (changed or bool(st.get("pending_seat_restart"))))
    if "chrome_restart" in pending:
        st["pending_chrome_restart"] = True
        if want_seat:
            st["pending_seat_restart"] = True       # 크롬을 다시 켠 뒤에 좌석을 재시작한다(순서 보존)
    else:
        st.pop("pending_chrome_restart", None)
        sched = st.get("seat_restart_scheduled_at")
        if want_seat and isinstance(sched, (int, float)) and _now() - sched < SEAT_WAIT_MAX_SEC + 120:
            said.append("cysr 재시작은 이미 예약돼 있습니다(이 대화가 끝나면 합니다).")
        elif want_seat:
            # ★codex R2: 빚은 예약 성공이 아니라 재시작 성공(waiter)에서 지운다 — 예약 실패·rotate 실패면 다음 호출이 다시
            st["pending_seat_restart"] = True
            r = schedule_seat_restart(SEAT_RESTART_DELAY_SEC)
            if r is None:
                said.append("cysr 재시작 예약에 실패했습니다 — 다음에 다시 하겠습니다(위쪽 ↻ 재시작으로도 됩니다).")
            else:
                st["seat_restart_scheduled_at"] = _now()
                _ledger({"event": "seat_restart_scheduled", "delay": SEAT_RESTART_DELAY_SEC})
                done.append("seat_restart")
                said.append("이 대화가 끝나면 cysr 가 잠깐 다시 시작합니다(지금 대화는 저장하고 이어집니다).")
    if owed or changed or want_seat or "chrome_restart" in pending or st != _load_chrome_state():
        _write_json(_p(CHROME_STATE), st)
    head = ("크롬 연결을 켰습니다(기본 켜기%s)." % (" · 연결 파일" if "nmh" in done else "")
            if ("default_on" in done or "nmh" in done) else "크롬 연결은 이미 켜져 있습니다.")
    tail = "" if not done else " 다르게 하시려면 말씀해 주세요 — 되돌릴 수 있습니다."
    return out({"ok": True, "done": done, "pending": pending, "nmh": nmh,
                "say": " ".join([head] + said) + tail})


def wait_idle(plat, wait):
    """사용자 입력 유휴 ≥ 20초가 될 때까지 최대 wait 초(2초 간격). 됐으면 True · 못 재거나 시간이 다 되면 False."""
    waited = 0
    while True:
        idle = idle_seconds(plat)
        if idle is not None and idle >= IDLE_GATE_SEC:
            return True
        if waited >= wait:
            return False
        _sleep(2)
        waited += 2


def restart_chrome(plat, wait):
    """유휴 관문 → 알림 → (유휴 재확인) → 정상 종료 → 다시 켬 → 창·탭 수 대조. 반환 = say 문장 · "deferred" · "not_quit:…"."""
    if not wait_idle(plat, wait):
        _ledger({"event": "chrome_restart_deferred"})
        return "deferred"
    before = chrome_windows(plat)
    notify("크롬을 잠깐 다시 켭니다", "Claude 연결을 붙이려고 크롬을 닫았다가 바로 다시 켭니다. 열린 탭은 그대로 돌아옵니다.")
    _sleep(3)
    idle = idle_seconds(plat)        # ★codex R1: 알림을 보고 다시 손을 댔으면 닫지 않는다(관문 통과 뒤 3초 사이)
    if idle is None or idle < IDLE_GATE_SEC:
        _ledger({"event": "chrome_restart_deferred", "after_notice": True})
        return "deferred"
    _ledger({"event": "chrome_quit", "before": list(before)})
    quit_chrome(plat)
    t = 0
    while chrome_running(plat):
        if t >= CHROME_QUIT_WAIT_SEC:
            _ledger({"event": "chrome_not_quit"})
            return "not_quit:%d" % t
        _sleep(1)
        t += 1
    open_chrome(plat)
    t = 0
    while not chrome_running(plat) and t < CHROME_QUIT_WAIT_SEC:
        _sleep(1)
        t += 1
    _sleep(3)
    after = chrome_windows(plat)
    _ledger({"event": "chrome_reopened", "before": list(before), "after": list(after)})
    restore_hint = " — 크롬 메뉴의 「방문 기록 → 최근에 닫은 탭」에서 되살릴 수 있습니다."
    (bw, bt), (aw, at) = before, after
    if bt is not None and at is not None:
        if at < bt:
            return "크롬을 다시 켰는데 탭이 %d개 → %d개입니다%s" % (bt, at, restore_hint)
        return "크롬을 다시 켰습니다(창 %d개 · 탭 %d개 그대로)." % (aw, at)
    if bw is not None and aw is not None:
        if aw < bw:
            return "크롬을 다시 켰는데 창이 %d개 → %d개입니다%s" % (bw, aw, restore_hint)
        return "크롬을 다시 켰습니다(창 %d개 그대로 · 탭 수는 확인하지 못했습니다)." % aw
    return "크롬을 다시 켰습니다(창·탭 수는 확인하지 못했습니다 — 탭이 안 보이면%s)" % restore_hint.lstrip(" —")


def cmd_chrome_disable(a):
    """되돌리기 = 켤 때 기억한 원래 값으로(기억이 없으면 끔) · 우리가 만든 연결 파일만 지운다(그 사이 바뀌었으면 두고 알림)."""
    plat = platform()
    st = _load_chrome_state()
    said = []
    prior = st.get("prior_key")
    target = (prior["value"] if prior.get("present") else None) if isinstance(prior, dict) else False
    if target is not None and not isinstance(target, bool):
        target = False
    if not st.get("key_restored"):              # ★codex R2: 연결 파일 삭제를 다시 시도할 때 키를 또 바꾸지 않는다
        _ledger({"event": "chrome_disable_key", "to": "absent" if target is None else target})
        if not write_chrome_key(target):
            return fail("크롬 기본 켜기를 되돌리지 못했습니다(설정이 잠겨 있거나 그 사이 바뀌어 손대지 않았습니다).", "write_failed", 1)
        st["key_restored"] = True
    nm = st.get("nmh_created")
    keep_state = False
    if isinstance(nm, dict):
        # ★codex R1: 지우기 전에 지금 값이 「내가 만든 그대로」인지 대조(맥 = 파일 sha256 · 윈 = 등록값 + 그 매니페스트 sha256)
        #   그 사이 다른 프로그램이 고쳐 썼으면 보존 · 지우기 실패면 되돌리기 기록을 남긴다(다음에 다시)
        if plat == "darwin" and nm.get("path"):
            mine = _sha_file(nm["path"]) == nm.get("sha256")
            argv = ["/bin/rm", "-f", nm["path"]]
        elif plat == "win":
            cur = _nmh_reg_value()
            mine = bool(nm.get("reg")) and bool(nm.get("sha256")) and cur == nm.get("reg") and _sha_file(cur) == nm.get("sha256")
            argv = ["reg", "delete", NMH_REG_KEY, "/f"]
        else:
            mine, argv = False, None
        if argv and mine:
            r = _act("nmh_remove", argv)
            if r is not None and r.returncode == 0:
                said.append("제가 만든 연결 파일도 지웠습니다.")
            else:
                keep_state = True
                said.append("제가 만든 연결 파일을 지우지 못했습니다 — 다음에 다시 지우겠습니다.")
        elif argv and plat == "win" and not nm.get("sha256"):
            keep_state = True                           # 소유권을 확인할 근거가 없다 — 지우지도, 기록을 버리지도 않는다
            said.append("연결 등록이 제가 만든 것인지 확인하지 못해 그대로 두었습니다.")
        elif argv:
            said.append("연결 파일은 그 사이 다른 프로그램이 고쳐 써서 그대로 두었습니다.")
    if keep_state:
        _write_json(_p(CHROME_STATE), st)           # prior_key·key_restored 그대로 — 다음 끄기는 연결 파일만 다시
    else:
        try:
            os.remove(_p(CHROME_STATE))
        except OSError:
            pass
    if a.seat_restart in ("auto", "now"):
        if schedule_seat_restart(SEAT_RESTART_DELAY_SEC) is not None:
            said.append("%d초 뒤 cysr 가 잠깐 다시 시작합니다(대화는 이어집니다)." % SEAT_RESTART_DELAY_SEC)
    head = "크롬 연결을 처음 상태로 되돌렸습니다." if prior else "크롬 기본 켜기를 껐습니다."
    return out({"ok": True, "say": " ".join([head] + said)})


# ───────────────────────── 선례 기반 이양 (TICKET=cu-1111-precedent 2단계 · 설계 §14) ─────────────────────────
# 박사님 원문(10-26 21:4x) 「기계적인 적용은 피해야 한다 … 사용자의 컴퓨터 유즈 상황과 패턴을 가능한 파악해서 맞춤형으로 적용해야
#   한다.」 · (21:5x) 「사람이 인공지능을 사용할 때는 보다 고차원의 분석과 판단을 통해 주인의 필요에 맞는 선택과 결정을 기대하는
#   것이다.」 → 「좋다. 보고는 하자. 그리고 우리 선례를 1.1.11에 적용하여 컴퓨터 유즈 자동화 기능을 보완하자.」
# 결정 4가지: do = 마스터가 정하고 한 뒤 짧게 보고(묻지 않음 · 기본값) · ask = 선례로 갈리지 않는 새 유형 — 한 번 묻고 답을 상시 기록
#   (같은 항목 재질문 금지) · each = 그 건마다 사람(결제·서명 제출·새 가입·비밀번호 입력 — 상시 기록 불가) · never = 안 함(사유).
DO, ASK, EACH, NEVER = "do", "ask", "each", "never"
CHECK = "check"     # 조건부 상시 허락 — 이번 건이 그 조건에 맞는지 마스터가 확인하고 --condition-met 으로 다시 부른다
PRECEDENT_SRC = {   # 선례 = 박사님 맥 운영 판례(원문은 각 파일 · 경로 = ~/.claude/projects/-Users-oogisoogi-axdev/memory/)
    "login": "test-login-approval-master-does(10-01·10-02 「필요에 의한 로그인, 권한 인증 … 마스터가 알아서 진행하라」)",
    "exception1": "~/axdev/CLAUDE.md 예외 1(결제·서명 제출·새 서비스 가입 = 건마다 허락)",
    "expand": "domain-management-master-delegated(10-20 「필요성이 확인되는대로 계속 권한을 확대」) · release-work-fully-autonomous(10-11)",
    "church": "jarvis-purpose-no-repeated-approvals 정정 절(10-26 21:4x 디모데·당회록 = 맥락 조건부 자동화 · 새 유형 1회 묻기)",
    "nokill": "never-kill-user-app-without-consent(10-01 한글 손실 · 정상 종료만)",
    "idle": "hancom-front-needs-idle-gate(10-25 · 키보드 유휴 20초 관문)",
    "install3": "install-convenience-security-boundary(원격 명령 통로·자격증명 대행·백신 우회 = 절대 금지)",
    "terms": "SESSION_STATE 10-26 20:0x(네이버 약관 2026-10-01 자동화 수단 로그인·게재 금지)",
    "kakao": "SESSION_STATE 10-26 20:3x(카톡 PC 로그인 = 한 대 · 다른 기기 밀림)",
    "appsec": "SESSION_STATE 10-26 22:3x(한컴 자동화 보안 창 = 공식 보안모듈 상시 설정으로 해소)",
    "universal": "winparity REPORT §10-2·§10-4(일부러 막힌 부류 = 우회 안 함 · 처음 보는 대화상자의 비가역 선택 = 정지·질문)",
}
# 유형(category) → (이름, 기본 결정, 선례 키, 보고·질문에 붙는 한 줄)
CATEGORIES = {
    "login": ("이미 쓰는 서비스 로그인·「허용」·만료 인증 갱신", DO, "login",
              "비밀번호·2단계 인증·지문 입력이 실제로 뜨면 그 한 번만 부탁드립니다."),
    "credential_input": ("비밀번호·2단계 인증 코드·생체 인증 입력", EACH, "login",
                         "이것은 사람 손이 물리적으로 필요합니다 — 제가 받거나 저장하지 않습니다."),
    "payment": ("결제", EACH, "exception1", "결제는 건마다 여쭙니다."),
    "sign_submit": ("서명 제출·약관 동의 제출", EACH, "exception1", "서명·동의 제출은 건마다 여쭙니다."),
    "signup": ("새 서비스 가입", EACH, "exception1", "새 서비스 가입은 건마다 여쭙니다."),
    "send_as_owner": ("주인 이름으로 남에게 보내는 메시지·게시·삭제", EACH, "login",
                      "주인 이름으로 남에게 나가는 것은 건마다 여쭙니다."),
    "external_send": ("자료를 바깥(다른 서비스·사람)으로 보내기", ASK, "church",
                      "자료 종류만 보고 막지 않습니다 — 누가·무엇을·어디로·실제로 안전한 환경인지 한 번 여쭙고, 답은 앞으로 계속 따릅니다."),
    "settings_change": ("cysr·클로드 좌석 설정 바꾸기(크롬 켜기 등)", DO, "expand",
                        "필요가 확인되면 넓히는 방향이 선례입니다 — 되돌릴 수 있게 원래 값을 적어 둡니다."),
    "app_quit": ("사용자 앱 다시 켜기·닫기(정상 종료)", DO, "nokill",
                 "정상 종료만 합니다(저장 확인 · 강제 종료 안 함 · 안 닫히면 그대로)."),
    "app_force_quit": ("멈춘 앱 강제 종료", EACH, "nokill",
                       "자동 저장본을 먼저 확보하고, 저장 안 된 작업이 있는지 여쭌 뒤에만 합니다."),
    "screen_op": ("화면 조작(앱을 앞으로 불러 누르기·입력)", DO, "idle",
                  "사용자 손이 20초 쉴 때만 하고, 결과는 파일·내용·창 제목으로 확인합니다."),
    "app_security_dialog": ("앱 자동화 보안 창", DO, "appsec",
                            "앱의 공식 상시 설정(예: 한컴 보안모듈)으로 창 자체를 없애는 길을 먼저 씁니다."),
    "kakao_login": ("카카오톡 PC 로그인", DO, "kakao",
                    "카톡 PC 로그인은 한 대만 됩니다 — 다른 컴퓨터의 카톡이 로그아웃될 수 있습니다."),
    "terms_risk": ("약관이 자동화를 금지한 서비스(예: 네이버 자동 로그인·게재)", EACH, "terms",
                   "약관 위반은 계정 정지로 되돌릴 수 없습니다 — 그 건마다 여쭙니다."),
    "update_dialog": ("업데이트가 끼운 처음 보는 창의 설치·동의·결제·로그아웃 선택", EACH, "universal",
                      "멈추고 무엇이 떴는지 그대로 여쭙니다."),
    "blocked": ("일부러 막힌 것(관리자 권한 창·UAC·화면 캡처 차단·키보드 보안·안티치트·보안문자)", NEVER, "universal",
                "우회하지 않습니다 — 「사람 손 1회 필요: 무엇」으로 알려 드립니다."),
    "install_boundary": ("원격 명령 통로·자격증명 대행·백신 우회", NEVER, "install3",
                         "편리함과 바꾸지 않는 선입니다(수습 불가)."),
}
TERMS_SERVICES = {"naver": "네이버", "네이버": "네이버"}   # 약관 위험 서비스(로그인·게재 자동화 금지)
DECISIONS = "decisions.json"
MAX_DECISIONS = 5000
MAX_CONDITION = 2000        # 조건 글자 한도 — 넘으면 자르지 않고 거절(codex R3) · 옛 판은 300자에서 잘라 저장했다
LEGACY_CUT = 300            # 옛 판 자르기 길이 — `full` 표지 없는 조건이 이 길이 이상이면 끝이 잘렸을 수 있다




def _norm(s):
    """대상 정규화(공백 하나·소문자) — 자르지 않는다(codex R8 뒤 자가 발견: 자르면 키 충돌·약관 서비스 누락)."""
    return re.sub(r"\s+", " ", (s or "").strip().lower())


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_LONGNUM = re.compile(r"\d[\d\- ]{6,}\d")


def mask(s, limit=80):
    """출력·기록에 싣는 대상 문자열에서 개인정보 모양(이메일·긴 번호)을 가린다(§3-3 · codex R1) · 길이 상한."""
    s = _EMAIL.sub("<이메일>", s or "")
    return _LONGNUM.sub("<번호>", s)[:limit]


def decision_key(cat, subject):
    """상시 기록 키 = 유형 + 대상의 해시(대상 원문을 파일에 남기지 않는다 · 같은 대상은 같은 키).
    목록 밖 새 유형은 유형 이름도 해시(마스터가 지은 이름에 개인정보가 섞여도 키·출력에 원문 0 · codex R2)."""
    n = _norm(subject)
    head = cat if cat in CATEGORIES else "new-" + hashlib.sha256(_norm(cat).encode("utf-8")).hexdigest()[:12]
    return "%s:%s" % (head, hashlib.sha256(n.encode("utf-8")).hexdigest()[:16] if n else "")


def _cut(rec):
    """옛 판이 300자에서 잘라 둔 조건인가(출처 사실 — 뜻은 보지 않는다): 원문 표지(full) 없고 길이가 자르기 길이 이상."""
    return (isinstance(rec, dict) and rec.get("meaning") == "conditional" and not rec.get("full")
            and len(rec.get("condition") or "") >= LEGACY_CUT)


def _lookup(decisions, cat, subject):
    """상시 기록 조회 — 키 하나(유형 + 자르지 않은 대상 해시). ★옛 판 키 호환은 없다(master#7d1b6e77 · codex R10): 이 기능은 이
    티켓에서 처음 생겼고 발행·설치 0 이라 옛 판 기록 = 개발 커밋의 시험 기록뿐 — 호환 층은 대상 간 슬롯 공유(120자 별칭)
    위험만 남겼다. 한 대상 = 한 키 = 한 기록이라 다른 대상의 기록 쓰기는 이 대상의 판정을 바꾸지 못한다."""
    r = (decisions or {}).get(decision_key(cat, subject))
    return r or None


def load_decisions():
    d = _read_json(_p(DECISIONS))
    return d if isinstance(d, dict) and isinstance(d.get("items"), dict) else {"items": {}}


def usage_pattern(plat=None, cfg=None):
    """맞춤 판단의 근거 — 「무엇을 이미 쓰는가」만(존재·빈도). 값(계정·내용)은 읽지 않는다 · 개인 프로필 대리 읽기 0.
    services = 커넥터 연결 기록 이름(S8) · apps = 카탈로그 앱 설치 여부 + 마지막 사용(맥 Spotlight 앱 메타데이터 → 일 수 구간)."""
    plat = plat or platform()
    cfg = cfg if cfg is not None else claude_cfg()
    fk = _fake("usage")
    if isinstance(fk, dict):
        return fk
    services = [n.replace("claude.ai ", "") for n in (cfg.get("connectors") or [])]
    apps = {}
    if plat == "darwin":
        for aid, name, prefixes, _n in MAC_APPS:
            path = next((os.path.join(r, n) for r in _app_roots() for n in (_listdir(r))
                         if any(n.startswith(px) for px in prefixes)), None)
            if not path:
                continue
            r = _run(["/usr/bin/mdls", "-raw", "-name", "kMDItemLastUsedDate", path])
            days = None
            m = re.match(r"(\d{4}-\d{2}-\d{2})", (r.stdout if r else "") or "")
            if m:
                days = (datetime.date.today() - datetime.date.fromisoformat(m.group(1))).days
            apps[aid] = {"name": name, "last_used_days": days}
    elif plat == "win":
        for aid in probe_apps(plat):
            apps[aid] = {"name": dict((a, n) for a, n, _p in WIN_APPS).get(aid, aid), "last_used_days": None}
    return {"services": services, "apps": apps}


def _listdir(root):
    try:
        return os.listdir(root)
    except OSError:
        return []


def _toks(s):
    return [t for t in re.split(r"[\s/.,:;·→()\[\]_\-@]+", _norm(s)) if t]


_DOMAIN = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}")
# URL 호스트의 허용 꼴 = ASCII 글자·숫자·하이픈 라벨(1~63자)을 점으로 이은 것 — 이 꼴 밖은 전부 모름(codex R8 · 금지 목록 아닌 허용 목록)
_HOST_OK = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
# 정식 도메인 목록(커넥터 이름·카탈로그 앱 ID → 그 서비스의 로그인 도메인) — 목록에 없는 도메인은 이름이 닮아도 「모름」(codex R4)
_MS = ("office.com", "microsoft365.com", "login.microsoftonline.com", "login.live.com")
SERVICE_DOMAINS = {
    "gmail": ("gmail.com", "mail.google.com"), "google calendar": ("calendar.google.com",),
    "google drive": ("drive.google.com",), "notion": ("notion.so", "notion.com"), "slack": ("slack.com",),
    "kakaotalk": ("kakao.com",), "word": _MS, "excel": _MS, "powerpoint": _MS, "office": _MS,
    "photoshop": ("adobe.com",), "illustrator": ("adobe.com",), "acrobat": ("adobe.com",),
}


def _hosts(subject):
    """대상 글 속 접속 대상 이름 — URL 은 파서의 실제 hostname(사용자정보·경로·쿼리의 도메인 모양은 대상이 아니다 · codex R5),
    그 밖은 도메인 모양. 둘 이상이거나 URL 이 깨졌으면 대상이 모호하다(호출 쪽이 「모름」)."""
    s = (subject or "").lower()
    if re.search(r"[a-z][a-z0-9+.\-]*://(?![^ \t\r\n])", s):
        return ["?"]                                 # 호스트 없이 끊긴 `://` = 뒤 글이 대상인지 모른다(codex R8)
    hosts, rest = [], s
    # URL = 글의 낱말 경계(ASCII 공백·탭·줄바꿈) 전까지 통째로 — 호스트 뒤 비ASCII 를 잘라 앞부분만 대조하지 않고(codex R7),
    #   그 밖의 공백류(VT · FF · U+3000 …)는 URL 안에 남겨 호스트 꼴 검사에서 모름이 되게 한다(codex R9)
    for m in re.finditer(r"[a-z][a-z0-9+.\-]*://[^ \t\r\n]+", s):
        url = m.group(0).rstrip(").,;:!?]}>'\"")              # 문장 속 URL 뒤 구분 부호는 URL 이 아니다(codex R6)
        try:
            u = urllib.parse.urlsplit(url)
            u.port                                       # 잘못된 포트 = ValueError
            h = None if "\\" in url else u.hostname          # 역슬래시 = 브라우저는 경로 구분으로 읽어 호스트가 갈린다(codex R6)
            h = h[:-1] if h and h.endswith(".") else h
            if h and (not _HOST_OK.fullmatch(h) or any(x.startswith("xn--") for x in h.split("."))):
                # 허용 꼴 밖 호스트(%·비ASCII·빈 라벨·금지 문자 …) = 모름(codex R8) · 퓨니코드 라벨은 이 컴퓨터가 유효성을 못 잰다
                #   (잘못된 A-label 을 브라우저는 거절) — 정식 도메인 목록에 xn-- 이 없으니 모름으로 잃는 do 는 없다(codex R9)
                h = None
        except ValueError:
            h = None
        hosts.append(h or "?")
        rest = rest.replace(m.group(0), " ")
    hosts += _DOMAIN.findall(rest)
    return list(dict.fromkeys(hosts))


def _in_use(subject, usage):
    """그 서비스·앱을 이미 쓰는가 — True(근거 문장)/None(모름). ★codex R2: 임의 부분 문자열이 아니라 **낱말** 대조
    (「카카오톡 로그인」 = 카카오톡 · 「wordpress.com」 ≠ Word) — 이름의 낱말이 전부 대상 낱말 안에 있어야 일치.
    ★codex R3·R4: 대상에 도메인이 있으면 이름 닮음이 아니라 **그 서비스의 정식 도메인 목록**(SERVICE_DOMAINS)으로만 대조
    (word.invalid · gmail.invalid · word.example.invalid = 모름)."""
    st = set(_toks(subject))
    if not st:
        return None, ""
    hosts = _hosts(subject)
    if len(hosts) > 1:
        return None, ""                              # 접속 대상이 둘 이상·깨진 URL = 어느 쪽인지 모름 → 묻는다
    host = hosts[0] if hosts else None

    def hit(key, nt):
        if host is not None:
            return any(host == d or host.endswith("." + d) for d in SERVICE_DOMAINS.get(key, ()))
        return bool(nt) and set(nt) <= st
    for n in usage.get("services", []):
        if hit(_norm(n), _toks(n)):
            return True, "커넥터로 연결해 쓰는 서비스(%s)" % n
    for aid, v in (usage.get("apps") or {}).items():
        if hit(aid, _toks(aid)) or (host is None and hit(aid, _toks(v.get("name")))):
            d = v.get("last_used_days")
            return True, "이 컴퓨터에 설치된 앱(%s%s)" % (v.get("name"), "" if d is None else " · %d일 전 사용" % d)
    return None, ""


def judge(cat, subject="", in_use=None, usage=None, decisions=None, condition_met=None):
    """유형 + 대상 → (결정, 근거, 문장). 순수 판정(쓰기 0) — self-test 가 전수로 돈다.
    순서: 약관 서비스 → 건마다·안 함(상시 기록으로 안 바뀜) → 상시 기록(새 유형 포함 — 한 번 물은 것은 다시 묻지 않는다) → 새 유형 = ask."""
    known = cat in CATEGORIES
    if known and cat in ("login", "external_send") and any(k in _norm(subject) for k in TERMS_SERVICES):
        n2, d2, s2, l2 = CATEGORIES["terms_risk"]
        return d2, "precedent:" + s2, l2
    if known and CATEGORIES[cat][1] in (EACH, NEVER):   # 건마다·안 함 = 상시 기록으로 바뀌지 않는다
        return CATEGORIES[cat][1], "precedent:" + CATEGORIES[cat][2], CATEGORIES[cat][3]
    if known and cat == "login" and in_use is False:      # ★codex R1: 처음 쓰는 서비스 = 가입 = 건마다(상시 기록보다 먼저)
        n2, d2, s2, l2 = CATEGORIES["signup"]
        return d2, "precedent:" + s2, "처음 쓰는 서비스입니다 — " + l2
    rec = _lookup(decisions, cat, subject)
    if isinstance(rec, dict) and rec.get("meaning") in ("allow", "deny", "conditional"):
        if _cut(rec):
            # ★codex R3·R5: 끝이 잘렸을 수 있는 옛 조건으로는 확인이 있어도 do 하지 않는다 — 이번에 조건을 한 번 다시 받아
            #   적어 두면(remember 가 이 기록만은 --user-changed 없이 덮는다) 다음부터 다시 묻지 않는다
            return EACH, "standing:%s" % rec.get("at", ""), ("전에 붙이신 조건이 끝까지 적혀 있지 않습니다 — 이번 건을 진행할지와 "
                                                             "그 조건을 한 번만 다시 말씀해 주시면 적어 두고 다시 여쭙지 않겠습니다.")
        if rec["meaning"] == "conditional" and condition_met is not True:
            # ★codex R2: 조건부 허락은 이번 건이 그 조건에 맞는다는 확인이 있어야 do — 모르면 확인(check) · 아니면 이번만 묻기
            if condition_met is False:
                return EACH, "standing:%s" % rec.get("at", ""), "전에 붙이신 조건에 맞지 않는 건입니다 — 이번 건만 여쭙니다."
            return CHECK, "standing:%s" % rec.get("at", ""), "전에 조건을 붙여 허락하셨습니다 — 이번 건이 그 조건에 맞는지 확인한 뒤 진행합니다."
        dec = DO if rec["meaning"] in ("allow", "conditional") else NEVER
        return dec, "standing:%s" % rec.get("at", ""), "전에 정해 주신 대로 합니다(%s)." % (
            {"allow": "허락", "deny": "안 함", "conditional": "조건부 허락 · 조건 확인됨"}[rec["meaning"]])
    if not known:
        return ASK, "new_type", "선례로 갈리지 않는 새 유형입니다 — 한 번 여쭙고 답을 계속 따르겠습니다."
    name, default, src, line = CATEGORIES[cat]
    if cat == "login":
        if in_use is None:
            in_use, why = _in_use(subject, usage or {})
        else:
            why = "마스터 관측"
        if in_use is True:
            return DO, "precedent:" + src, "%s — %s %s" % (name, why, line)
        if in_use is False:
            n2, d2, s2, l2 = CATEGORIES["signup"]
            return d2, "precedent:" + s2, "처음 쓰는 서비스입니다 — " + l2
        return ASK, "precedent:" + src, "이 서비스를 이미 쓰고 계신지 확인하지 못했습니다 — 한 번 여쭙고 답을 계속 따르겠습니다."
    return default, "precedent:" + src, line


def cmd_decide(a):
    """유형 판정 1회 — 쓰기 0. do 면 마스터가 하고 report 를 말한다 · ask 면 ask 를 그대로 묻고 답을 remember 로 기록."""
    dec = load_decisions()["items"]
    in_use = {"yes": True, "no": False}.get(a.in_use)
    usage = usage_pattern() if a.cat == "login" and in_use is None else {}
    cm = {"yes": True, "no": False}.get(a.condition_met)
    d, basis, line = judge(a.cat, a.subject, in_use, usage, dec, cm)
    name = CATEGORIES.get(a.cat, (mask(a.cat),))[0]
    subj = (" — " + mask(a.subject)) if a.subject else ""
    res = {"ok": True, "decision": d, "basis": basis, "category": mask(a.cat)}
    if d == DO:
        what = mask(a.what) or "%s%s" % (name, subj)
        res["report"] = "이렇게 했습니다: %s. %s 다르게 원하시면 말씀해 주세요." % (what, line)
    elif d == ASK:
        res["ask"] = "「%s%s」 — %s 맡겨 주시겠어요? (허락 · 안 함 · 조건을 붙여 허락 중에서 말씀해 주세요)" % (name, subj, line)
    elif d == EACH:
        res["ask"] = "「%s%s」 — %s 이번 건을 진행할까요?" % (name, subj, line)
        if _cut(_lookup(dec, a.cat, a.subject)):
            res["supplement"] = True             # 답의 조건을 remember 로 적으면 이 항목은 다시 묻지 않는다
    elif d == CHECK:
        rec = _lookup(dec, a.cat, a.subject) or {}
        # ★master#6528f666(D16): 조건 글의 뜻은 도구가 해석하지 않는다 — 사용자 자신의 말 원문을 마스터에게 돌려주고,
        #   이번 건이 그 조건에 맞는지는 마스터가 자연어로 판단한다(애매하면 그때만 사용자에게 1회)
        res["condition"] = rec.get("condition", "")   # 끝이 잘렸을 수 있는 옛 기록은 여기 오지 않는다(judge 가 each)
        res["say"] = line
    else:
        res["say"] = "「%s%s」은(는) 하지 않습니다 — %s" % (name, subj, line)
    return out(res)


def cmd_remember(a):
    """한 번 물은 답을 상시 기록 — 같은 항목은 다시 묻지 않는다. 건마다·안 함 유형은 기록하지 않는다(exit 5)."""
    if a.cat in CATEGORIES and CATEGORIES[a.cat][1] in (EACH, NEVER):
        return fail("이 유형은 건마다 여쭙거나 하지 않는 것이라 상시로 정해 둘 수 없습니다.", "not_recordable", 5)
    try:
        with open(a.answer_file, encoding="utf-8") as f:
            ans = f.read()
    except OSError:
        return fail("사용자 답을 읽지 못했습니다.", "io", 2)
    if not ans.strip():
        return fail("사용자 답이 비어 있습니다 — 여쭌 뒤에 기록해 주세요.", "empty_answer", 2)
    if a.meaning == "conditional" and not (a.condition or "").strip():
        return fail("조건부 허락은 조건을 함께 적어야 합니다.", "condition", 2)
    cond = (a.condition or "").strip()
    if len(cond) > MAX_CONDITION:
        # ★codex R3: 조건을 잘라 저장하면 끝에 붙은 제한(「외부 수신자 금지」 등)이 조용히 사라진다 — 자르지 않고 거절
        return fail("붙이신 조건이 너무 길어(%d자 · 한도 %d자) 기록하지 않았습니다 — 조건을 줄여 다시 말씀해 주세요."
                    % (len(cond), MAX_CONDITION), "condition_too_long", 2)
    d = load_decisions()
    key = decision_key(a.cat, a.subject)
    prev = d["items"].get(key)
    supp = _cut(prev) and not a.user_changed         # 잘린 옛 조건 다시 적기(보완) — 그 기록 자리에서 바꾼다(codex R5·R6)
    if supp and a.meaning != "conditional":
        return fail("끝이 잘린 조건은 조건부 허락으로만 다시 적습니다 — 허락·안 함으로 바꾸신 것이면 사용자 변경으로 적어 주세요.",
                    "supplement_meaning", 7)
    if prev and not a.user_changed and not supp:
        # 재질문 금지 — 이미 정해진 항목을 다시 묻고 기록하는 것은 마스터의 실수다(사용자가 스스로 바꾼 때만 --user-changed)
        return fail("이미 정해 주신 항목입니다 — 다시 여쭙지 않고 그 결정을 따릅니다.", "already_decided", 7)
    if key not in d["items"] and len(d["items"]) >= MAX_DECISIONS:
        # ★codex R1: 상한에서 옛 결정을 지우면 그 항목을 다시 묻게 된다 — 지우지 않고 새 기록을 거절한다(4군① 상한은 유지)
        _ledger({"event": "decisions_full", "count": len(d["items"])})
        return fail("정해 두신 결정이 너무 많아(%d) 더 적어 두지 못했습니다 — 이번 결정은 따르되 기록은 하지 못했습니다."
                    % MAX_DECISIONS, "decisions_full", 7)
    rec = {"meaning": a.meaning, "condition": cond, "at": _iso(),
           "label": mask("%s %s" % (a.cat, a.subject)),
           "answer_sha256": hashlib.sha256(ans.encode("utf-8")).hexdigest()}
    if a.meaning == "conditional":
        rec["full"] = True                           # 자르지 않은 원문(옛 판 300자 기록과 구별)
    _ledger({"event": "decision", "key": key, "meaning": a.meaning, "changed": bool(a.user_changed),
             "supplement": bool(supp),
             "answer_sha256": rec["answer_sha256"]})              # 기록 먼저
    d["items"][key] = rec
    _write_json(_p(DECISIONS), d)
    word = {"allow": "허락", "deny": "안 함", "conditional": "조건부 허락(%s)" % mask(cond)}[a.meaning]
    return out({"ok": True, "key": key, "say": "알겠습니다 — 앞으로 「%s」은(는) %s 으로 계속 따르겠습니다. 다시 여쭙지 않습니다."
                                              % ((CATEGORIES.get(a.cat, (mask(a.cat),))[0] + (" — " + mask(a.subject) if a.subject else "")), word)})


def cmd_adopt(a):
    """기본값 = 마스터가 먼저 정하고 보고(박사님 10-26 21:5x). 지금 바로 맡을 수 있는 칸은 묻지 않고 장부에 올리고
    「이렇게 했습니다 · 다르면 말씀」으로 보고 · 손 칸은 안내 제안 · 사용자가 전에 「빼라」 한 항목(take:<ID> = deny)은 가져오지 않는다."""
    plat = platform()
    items = number_items(build_items(plat, _project()))
    scan_id = "s" + os.urandom(4).hex()
    _write_json(_p("scan.json"), {"ts": _now(), "at": _iso(), "platform": plat, "measured_on": MEASURED_ON,
                                  "scan_id": scan_id, "project": os.path.realpath(_project()), "items": items})
    dec = load_decisions()["items"]
    g = load_grants()
    took, skipped, hand, nope, auto = [], [], [], [], False
    for it in items:
        mids = [m for m, _t in (it.get("members") or [[it["id"], it["title"]]])]
        if any((dec.get("take:%s" % m) or {}).get("meaning") == "deny" for m in mids):
            skipped.append(it)
            continue
        if it["tier"] == READY or first_use_only(it):
            if all((g["items"].get(m) or {}).get("state") == "active" for m in mids):
                continue
            took.append(it)
            auto = auto or (it["id"] == "chrome" and bool(it["missing"]))
        elif it["tier"] == HAND:
            hand.append(it)
        else:
            nope.append(it)
    if took:
        _ledger({"event": "adopt", "scan_id": scan_id, "active": [it["id"] for it in took],
                 "basis": "precedent:default-take-ready"})       # 기록 먼저
        for it in took:
            for mid, mtitle in it.get("members") or [[it["id"], it["title"]]]:
                g["items"][mid] = {"state": "active", "title": mtitle, "at": _iso(), "by": "adopt"}
        save_grants(g)
    short = lambda it: it["title"].split("(")[0].strip()
    lines = []
    if took:
        lines.append("이렇게 했습니다: 지금 바로 맡을 수 있는 %s 을(를) 제가 맡았습니다." % ", ".join(short(it) for it in took))
        if auto:
            lines.append("크롬 연결 설정은 제가 바로 켜겠습니다.")
    else:
        lines.append("새로 맡을 것은 없습니다 — 이미 맡고 있는 것 그대로입니다.")
    if hand:
        lines.append("손이 한 번 필요한 것: %s — 원하시면 「%s 안내해 줘」라고 말씀해 주세요." % (
            ", ".join("%d. %s" % (it["n"], short(it)) for it in hand), short(hand[0])))
    if nope:
        lines.append("지금은 안 되는 것: " + ", ".join(short(it) for it in nope) + ".")
    if skipped:
        lines.append("전에 빼라고 하신 것은 가져오지 않았습니다: " + ", ".join(short(it) for it in skipped) + ".")
    if took:
        lines.append("다르게 원하시면 말씀해 주세요(예: 「%s은 빼」)." % short(took[0]))
    return out({"ok": True, "scan_id": scan_id, "active": [it["id"] for it in took],
                "hand": [it["id"] for it in hand], "not_now": [it["id"] for it in nope],
                "skipped": [it["id"] for it in skipped], "next_action": "chrome-enable" if auto else None,
                "say": "\n".join(lines[:MAX_SAY_LINES])})


# ───────────────────────── self-test ─────────────────────────
FORBIDDEN_MARKS = ("CC-TEST-EMAIL@example.com", "CC-TEST-NAME", "CC-TEST-ORG", "CC-TEST-PROFILE")


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
                        # 바로 = 앱·확장(켜짐)이 있고 모름 0 — 기본 켜기·연결 파일 꺼짐은 마스터가 켠다(chrome-enable)
                        if t == READY and (not app or not with_ext or en is not True or d is None or nmh is None):
                            errs.append("chrome 바로 오판 %r" % (c,))
                        if t == READY and _m and not set(_m) <= set(CHROME_AUTO):
                            errs.append("chrome 사람 손 항목을 바로로 %r" % (c,))
                        if not app and t != NOT_NOW:
                            errs.append("chrome 앱 없음 %r" % (c,))
    for code in (0, -1743, -1744, -600, -1, None):
        n += 1
        t, u, _m, _r = verdict_script(code)
        if (t == READY) != (code == 0):
            errs.append("script %r" % (code,))
    if ASK_USER_IF_NEEDED is not False:
        errs.append("askUserIfNeeded 가 False 가 아니다")
    # 선례 판정: 건마다·안 함 유형은 상시 기록·사용 패턴이 있어도 do 가 되지 않는다 · 모르는 유형 = ask · 약관 서비스 = each
    allow = {"meaning": "allow", "at": "t"}
    use = {"services": ["Gmail"], "apps": {"kakaotalk": {"name": "카카오톡", "last_used_days": 1}}}
    for cat, (_n, default, _s, _l) in CATEGORIES.items():
        for subj in ("", "gmail", "naver", "카카오톡"):
            for iu in (True, False, None):
                n += 1
                dd = {decision_key(cat, subj): allow}
                got = judge(cat, subj, iu, use, dd)[0]
                if cat == "login" and iu is False and got != EACH:
                    errs.append("judge 처음 쓰는 서비스(가입)가 상시 허락으로 do")
                if default in (EACH, NEVER) and got == DO:
                    errs.append("judge %s 건마다·안 함 → do" % cat)
                if "naver" in subj and cat in ("login", "external_send") and got != EACH:
                    errs.append("judge 약관 서비스 %s" % cat)
    cond = {decision_key("external_send", "x"): {"meaning": "conditional", "condition": "c", "at": "t"}}
    for cm, want in ((None, CHECK), (False, EACH), (True, DO)):
        n += 1
        if judge("external_send", "x", None, {}, cond, cm)[0] != want:
            errs.append("judge 조건부 허락 condition_met=%r" % (cm,))
    cut = {decision_key("external_send", "x"): {"meaning": "conditional", "condition": "c" * LEGACY_CUT, "at": "t"}}
    for cm in (None, False, True):
        n += 1
        if judge("external_send", "x", None, {}, cut, cm)[0] != EACH:
            errs.append("judge 잘린 옛 조건 condition_met=%r" % (cm,))
    # ★codex R8·R9: 정식 URL 의 호스트 자리에 글자 하나를 끼운 모든 꼴(ASCII 128 + 비ASCII 표본 10) — do 는 같은 호스트로 읽히는
    #   자리(맨 앞 `@` = 빈 사용자정보 · 맨 끝 `:`(빈 포트)·`.`(끝점)·`/`·`?`·`#` · 글의 낱말 경계 ASCII 공백·탭·줄바꿈)에서만.
    #   그 밖은 전부 모름 — 기대값은 고정 목록이다(구현의 공백 분류를 빌리지 않는다)
    base, a0, a1 = "https://mail.google.com/", 8, 23
    gmail = {"services": ["Gmail"], "apps": {}}
    for pos in range(a0, a1 + 1):
        for c in [chr(i) for i in range(128)] + ["é", "。", "．", "\u200b", "\u3000", "ｍ", "\ufeff", "\u00a0", "\u0085", "\u2028"]:
            n += 1
            sub = base[:pos] + c + base[pos:]
            ok = (pos == a0 and c == "@") or (pos == a1 and c in ":./?# \t\r\n")   # 낱말 경계 = ASCII 공백·탭·줄바꿈만(목록 고정)
            if (_in_use(sub, gmail)[0] is True) and not ok:
                errs.append("host 끼움 do %r" % (sub,))
    n += 1
    if judge("brand-new-type")[0] != ASK:
        errs.append("judge 새 유형이 ask 가 아니다")
    if judge("login", "unknown-service", None, {"services": [], "apps": {}}, {})[0] != ASK:
        errs.append("judge 모르는 서비스 로그인이 ask 가 아니다")
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
    g.add_argument("--scan", required=True, help="사용자가 본 목록의 scan_id(scan 출력)")
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
    rp.add_argument("--meaning", required=True, choices=("yes", "no", "unclear"))
    sp.add_parser("self-test")
    ce = sp.add_parser("chrome-enable")
    ce.add_argument("--wait", type=int, default=120, help="크롬 다시 켜기 전 사용자 유휴(20초)를 기다릴 최대 초(≤ 540)")
    ce.add_argument("--seat-restart", choices=("auto", "now", "no"), default="auto")
    cd = sp.add_parser("chrome-disable")
    cd.add_argument("--seat-restart", choices=("auto", "now", "no"), default="no")
    sp.add_parser("adopt")
    sw = sp.add_parser("seat-restart-wait")
    sw.add_argument("--min-delay", type=int, default=SEAT_RESTART_DELAY_SEC)
    sw.add_argument("--surface", default="")
    dc = sp.add_parser("decide")
    dc.add_argument("cat")
    dc.add_argument("--subject", default="")
    dc.add_argument("--in-use", choices=("yes", "no", "unknown"), default="unknown")
    dc.add_argument("--what", default="", help="한 일 한 줄(보고 문장에 넣는다)")
    dc.add_argument("--condition-met", choices=("yes", "no", "unknown"), default="unknown",
                    help="조건부 상시 허락일 때 이번 건이 그 조건에 맞는가(마스터 판단)")
    rm = sp.add_parser("remember")
    rm.add_argument("cat")
    rm.add_argument("--subject", default="")
    rm.add_argument("--answer-file", required=True)
    rm.add_argument("--meaning", required=True, choices=("allow", "deny", "conditional"))
    rm.add_argument("--condition", default="", help="사용자가 한 말 그대로(기록 파일에만 · 원장엔 해시 · check 때 마스터에게 원문)")
    rm.add_argument("--user-changed", action="store_true", help="사용자가 스스로 결정을 바꾼 때만")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    fn = {"scan": cmd_scan, "grant": cmd_grant, "guide": cmd_guide, "recheck": cmd_recheck,
          "revoke": cmd_revoke, "status": cmd_status, "open-settings": cmd_open_settings,
          "request-prompt": cmd_request_prompt, "self-test": cmd_self_test,
          "chrome-enable": cmd_chrome_enable, "chrome-disable": cmd_chrome_disable,
          "adopt": cmd_adopt, "decide": cmd_decide, "remember": cmd_remember,
          "seat-restart-wait": cmd_seat_restart_wait}.get(a.cmd)
    if a.cmd == "chrome-enable":
        a.wait = max(0, min(a.wait, 540))    # 4군① — 한 번 부를 때 Bash 도구 상한(600초) 안
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
