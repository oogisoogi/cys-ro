#!/usr/bin/env python3
"""javis_dept_request.py — 대화로 부서 만들기 (A1-2 · 설계 DESIGN-v2.1 + 적대 2R 수정 11항).

마스터(본부)가 사용자 발화를 받아 부서를 **제안 → 확인 → (스케줄 틱이) 집행 → 판정**한다.
요청 폴더는 **기록**이고, 사용자에게 하는 말(판정)은 언제나 그 순간의 **실물**(레지스트리·묘비·
부서 데몬·편성 원장·관문)에서 나온다. CLI 계약 정본 = docs/DESIGN-dept-by-conversation.md.

동사:
  propose  (마스터)  새 부서 제안 카드 · 또는 --close 로 닫기 카드. 열린 제안은 언제나 1장.
  confirm  (마스터)  사용자 「네」 뒤. request.json=confirmed 를 **먼저** 쓰고 그다음 .pending 표지.
  tick     (스케줄 틱 `dept-request-tick` 전용 · CYS_ROLE=cso 아니면 exit 3) 집행기.
  status   (마스터)  판정표 v2(13행 결정 트리). --pending · --all · --say <번호>.
  kickoff  (마스터)  첫 일 한 문장을 부서장에게 요청당 1회(--queued · Return 없음).
  discard  (마스터)  레지스트리에 대응 부서가 없을 때만 이 요청이 넣은 흔적을 걷는다.
  self-test          결정 트리 전 조합 · 키 계약 · javis_org 의미 대조 · 내장 뮤턴트.

exit: 0=성공(정상 skip 포함) 2=입출력/사용 오류 3=권한(tick 을 CSO 신원 밖에서 부름)
      4=대상 없음 5=거부(중복·상한·레인·자원 hard — 문장은 stdout JSON 의 say) 6=낡은 번호(superseded)
      7=상태 불일치(지금 할 수 없는 동작) 1=내부 오류/자기시험 실패

★적대 2R 치명 3 봉합 위치:
  ① .pending lost-update  → _pending_claim()(스캔 전 rename 으로 표지를 먼저 치운다) +
                             confirm 은 request.json 을 먼저 쓰고 표지를 나중에 만든다. + 자가복구 벨트.
  ② 청소가 게이트 뒤       → _sweep() 은 매 틱 무조건(표지 유무와 무관 · 잠금 획득 직후 첫 단계).
  ③ 묘비 이름 재사용       → 결정 트리 5행 = R=closed ∨ (T ∧ G=없음). T∧G 는 실물 행으로 판정하고
                             tombstone_residue 로 결정론 표기 + 틱이 자기 생성 직후 해소를 1회 재시도.
"""
import argparse
import datetime
import errno
import hashlib
import itertools
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

def home():
    return os.path.expanduser("~")


def _env(name, default):
    v = os.environ.get(name)
    return v if v else default


# ── 경로(전부 env 주입 가능 — 시험 격리) ─────────────────────────────────────
def root_dir():
    return _env("CYS_DEPT_REQUESTS", os.path.join(home(), ".cys", "dept-requests"))


def depts_json():
    return _env("CYS_DEPTS_JSON", os.path.join(home(), ".cys", "depts.json"))


def catalog_json():
    return _env("CYS_DEPT_CATALOG", os.path.join(home(), ".cys", "dept-catalog.json"))


def missions_dir():
    return _env("CYS_DEPT_MISSIONS", os.path.join(home(), ".cys", "dept-missions"))


def formation_dir():
    return os.path.join(_env("CYS_STATE_DIR", os.path.join(home(), ".cys", "state")), "formation")


def base_state_dir():
    """base 데몬 상태 폴더 — 데몬 묘비(dept_tombstones.json)의 자리(governance::persist_dept_tombstones)."""
    v = os.environ.get("CYS_BASE_STATE_DIR")
    if v:
        return v
    if os.name == "nt":
        return os.path.join(os.environ.get("LOCALAPPDATA", "."), "cys")
    return os.path.join(home(), ".local", "state", "cys")


def trash_root():
    return _env("CYS_DEPT_TRASH", os.path.join(home(), ".local", "state", "cys-trash"))


def pack_default():
    # cys-dept 의 PACK_DEFAULT 와 같은 자리(승격 조건 파일을 같은 곳에서 읽어야 카드가 거짓말하지 않는다)
    return os.path.join(home(), ".cys", "pack")


def dept_sock(name):
    """cys-dept dept_sock 규약 미러(Windows named pipe · 그 외 unix .sock)."""
    if os.name == "nt":
        return r"\\.\pipe\cys-dept-%s" % name
    return os.path.join(home(), ".local", "state", "cys-dept-%s" % name, "cys.sock")


def workdir_for(display):
    """부서 작업 폴더 규약 — javis_org v_quote_binding 의 'Desktop/CYSjavis/<표시명>' 과 같아야 한다
    (self-test 의 의미 대조 시험이 javis_org 코드로 이것을 판정한다)."""
    return os.path.join(home(), "Desktop", "CYSjavis", display)


# ── 상수 ──────────────────────────────────────────────────────────────────────
def chat_cap():
    try:
        return int(_env("CYS_DEPT_CHAT_CAP", "2"))
    except ValueError:
        return 2


def _int_env(name, default):
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


CONFIRM_TTL_SEC = lambda: _int_env("CYS_DEPT_CONFIRM_TTL_SEC", 1800)       # 확인 뒤 30분 = 만료
CREATE_GAP_SEC = lambda: _int_env("CYS_DEPT_CREATE_GAP_SEC", 600)          # 생성 간격 10분
CREATE_WAIT_SEC = lambda: _int_env("CYS_DEPT_CREATE_WAIT_SEC", 300)        # create 기다림 상한
CREATE_HANG_SEC = lambda: _int_env("CYS_DEPT_CREATE_HANG_SEC", 3600)       # 첫 자식이 이보다 오래 살면 실패
GONE_AFTER_SEC = 900                                                       # 판정 8행 경계 15분
RUNNING_WATCH_SEC = 7200                                                   # 가동 알림 대기 상한 2시간
MAX_CREATE_CALLS = 2
DAY = 86400
MARKER_PREFIX = "<!-- cys-dept-mission "
ROLE_GUIDE = ("> 이 안내는 부서장(master)에게 향합니다. 운영 담당·작업자는 자기 역할 지침을 따르고, "
              "부서장이 나눠 준 일만 합니다.")
SHARED_ACCOUNT_KEY = "shared"
# D2(설정 폴더 공유) 기본값. T0 결과가 불성립이면 "fork" 로 바꾼다(현행 로그인 경로 = 폴백).
ACCOUNT_MODE_DEFAULT = "shared"

STATES = ("proposed", "superseded", "confirmed", "expired", "created", "reused",
          "create-timeout", "failed", "closed", "discarded")
IN_FLIGHT = ("confirmed", "create-timeout")


def now():
    return time.time()


def iso(t=None):
    return datetime.datetime.fromtimestamp(t if t is not None else now()).strftime("%Y-%m-%dT%H:%M:%S")


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))


# ── 파일 유틸 ─────────────────────────────────────────────────────────────────
def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (OSError, ValueError):
        return default


def atomic_write_text(path, text):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_json(path, obj):
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def req_dir(rid):
    return os.path.join(root_dir(), rid)


def load_req(rid):
    return load_json(os.path.join(req_dir(rid), "request.json"))


def save_req(r):
    r["updated_at"] = now()
    atomic_write_json(os.path.join(req_dir(r["id"]), "request.json"), r)


def all_reqs():
    rd = root_dir()
    try:
        names = sorted(os.listdir(rd))
    except OSError:
        return []
    res = []
    for n in names:
        if not n.startswith("dr-"):
            continue
        r = load_json(os.path.join(rd, n, "request.json"))
        if isinstance(r, dict) and r.get("id") == n:
            res.append(r)
    return res


def new_req_id():
    return "dr-%s-%s" % (datetime.datetime.now().strftime("%y%m%d-%H%M%S"), secrets.token_hex(2))


def registry():
    reg = load_json(depts_json(), {"depts": {}}) or {"depts": {}}
    d = reg.get("depts")
    return d if isinstance(d, dict) else {}


def catalog():
    cat = load_json(catalog_json(), None)
    if not isinstance(cat, dict):
        cat = {"version": 1, "accounts": {}, "departments": {}}
    cat.setdefault("accounts", {})
    cat.setdefault("departments", {})
    return cat


def tombstones():
    """T 축 = base 데몬 묘비(리바이버·spawn_org_restore 의 게이트 — 되살리기를 실제로 막는 쪽).
    phoenix 미러는 보호집합 보고용이라 읽지 않는다(두 미러가 갈라지면 데몬 쪽이 행동을 결정한다)."""
    d = load_json(os.path.join(base_state_dir(), "dept_tombstones.json"), {}) or {}
    v = d.get("dept_tombstones") if isinstance(d, dict) else None
    return set(x for x in (v or []) if isinstance(x, str))


def reg_name_for_key(key, reg=None):
    reg = registry() if reg is None else reg
    for n, e in reg.items():
        if isinstance(e, dict) and e.get("mission_key") == key:
            return n
    return None


# ── 레인(4군 ① — 연쇄 생성 금지의 입력을 결정론으로) ─────────────────────────
_DEPT_SOCK_RE = re.compile(r"(^|[\\/])cys-dept-[^\\/]+([\\/]|$)")


def lane_is_base(env=None):
    """이 호출자가 본부(base) 레인인가 — LLM 자기신고가 아니라 env 로 판정한다.
    부서 좌석은 cys-dept 가 CYS_SOCKET=<부서 소켓> · CYS_PACK_DIR=~/.cys/pack-dept-<이름> 으로
    띄운 데몬의 자식이라 둘 중 하나라도 부서 모양이면 부서 레인이다(schedule.rs is_dept_socket 동형)."""
    env = os.environ if env is None else env
    s = env.get("CYS_SOCKET", "") or ""
    if s and (_DEPT_SOCK_RE.search(s) or "cys-dept-" in s):
        return False
    p = env.get("CYS_PACK_DIR", "") or ""
    if p and os.path.basename(p.rstrip("/\\")).startswith("pack-dept-"):
        return False
    return True


# ── 표시명 ────────────────────────────────────────────────────────────────────
def norm_name(s):
    return " ".join((s or "").split())


def name_problem(disp):
    if not disp:
        return "부서 이름이 비어 있습니다."
    if len(disp) > 40:
        return "부서 이름은 40자 이하로 말씀해 주세요."
    if any(c in disp for c in "/\\:") or disp in (".", "..") or disp.startswith("."):
        return "부서 이름에 / \\ : 나 맨 앞 점(.)은 쓸 수 없습니다."
    if any(ord(c) < 32 for c in disp):
        return "부서 이름에 보이지 않는 문자가 섞여 있습니다."
    return None


def live_depts(reg=None, ts=None):
    """살아 있는 부서 = 레지스트리 항목 중 묘비 없는 것(메뉴로 만든 부서 포함 — 경로 무관)."""
    reg = registry() if reg is None else reg
    ts = tombstones() if ts is None else ts
    return {n: e for n, e in reg.items() if n not in ts}


def display_of(name, e, cat=None):
    cat = catalog() if cat is None else cat
    d = (e or {}).get("display_name")
    if d:
        return d
    mk = (e or {}).get("mission_key")
    ce = (cat.get("departments") or {}).get(mk) if mk else None
    return (ce or {}).get("display") or name


def display_taken(disp, reg=None, cat=None):
    reg = registry() if reg is None else reg
    cat = catalog() if cat is None else cat
    for k, v in (cat.get("departments") or {}).items():
        if norm_name(v.get("display")) == disp:
            return True
    for n, e in reg.items():
        if norm_name((e or {}).get("display_name")) == disp:
            return True
    return False


# ── 키(C-9) ───────────────────────────────────────────────────────────────────
KEY_RE = re.compile(r"^c[0-9a-f]{6}$")


def new_key(cat=None):
    cat = catalog() if cat is None else cat
    for _ in range(5):
        k = "c" + secrets.token_hex(3)
        if k not in (cat.get("departments") or {}):
            return k
    raise RuntimeError("부서 키 발급 5회 충돌")


# ── 계정(D2 · 2R ④) ───────────────────────────────────────────────────────────
def account_mode():
    m = _env("CYS_DEPT_ACCOUNT_MODE", ACCOUNT_MODE_DEFAULT)
    return m if m in ("shared", "fork") else ACCOUNT_MODE_DEFAULT


def primary_key():
    return os.environ.get("CYS_PRIMARY_ACCOUNT") or "owner"


def base_account_dir():
    return os.environ.get("CYS_ACCOUNT_DIR") or os.path.join(home(), ".cys", "claude")


def account_plan():
    """(카탈로그 계정 키, 로그인 필요 여부). 공유안이 성립하는 유일 조건 = 계정 키 ≠ CYS_PRIMARY_ACCOUNT
    (cys-dept:1335 포크 조건). 매 카드에서 **재판정**한다(2R ④ — T0 1회 결과로 고정하지 않는다)."""
    if account_mode() == "shared" and SHARED_ACCOUNT_KEY != primary_key():
        return SHARED_ACCOUNT_KEY, False
    return primary_key(), True     # 현행(포크) — cys-dept 가 <계정폴더>-<키> 를 만들고 로그인 1회


def trust_state(cwd, cfg_dir=None):
    """새 폴더를 Claude Code 가 신뢰하는가(2R ⑤) — 설정 파일 projects 에 그 폴더나 상위 폴더가
    신뢰로 있으면 trusted. 읽기 전용(신뢰 시드는 javis_seat 단일 소유 — 여기서 쓰지 않는다)."""
    cfg = os.path.join(cfg_dir or base_account_dir(), ".claude.json")
    d = load_json(cfg, None)
    if not isinstance(d, dict):
        return "unknown"
    projects = d.get("projects")
    if not isinstance(projects, dict):
        return "untrusted"
    import unicodedata
    def nfc(p):
        return unicodedata.normalize("NFC", os.path.normpath(p))
    trusted = {nfc(k) for k, v in projects.items()
               if isinstance(v, dict) and v.get("hasTrustDialogAccepted") is True}
    p = nfc(cwd)
    while True:
        if p in trusted:
            return "trusted"
        parent = os.path.dirname(p)
        if parent == p:
            return "untrusted"
        p = parent


# ── 자원 ──────────────────────────────────────────────────────────────────────
def resource_check():
    """javis_resource_gate check --json. 좌석 계수는 그 출력(measured.nodes · dept_seats)을 재사용한다
    (2R ⑥ — 두 번째 계수기를 만들지 않는다). --formation-size 축은 프로덕션 무발화(CYS_FORMATION_BUDGET
    생산자 0)라 hard/soft 는 일반 축(servers·nodes·load·context)에서만 나온다."""
    ov = os.environ.get("CYS_DEPT_GATE_OVERRIDE")
    if ov:
        try:
            return json.loads(ov)
        except ValueError:
            return {"verdict": "unknown"}
    gate = os.path.join(HERE, "javis_resource_gate.py")
    try:
        p = subprocess.run([sys.executable, gate, "check", "--json", "--formation-size", "3"],
                           capture_output=True, text=True, timeout=60, **NOWIN)
        return json.loads(p.stdout)
    except Exception:
        return {"verdict": "unknown"}


# ── 카드 ──────────────────────────────────────────────────────────────────────
def promotion_line_applies():
    """첫 부서 줄(B-5): cys-dept ceo_promote 가 지금 승격할 조건 = 부트 마커 ∧ .pre-ceo 부재 ∧
    MASTER_DIRECTIVE ≠ CEO_TEMPLATE. 거짓이면 줄을 빼서 카드가 거짓말하지 않게 한다."""
    pk = pack_default()
    md = os.path.join(pk, "directives", "MASTER_DIRECTIVE.md")
    ceo = os.path.join(pk, "directives", "CEO_TEMPLATE.md")
    if not os.path.isfile(os.path.join(home(), ".cys", ".master-bootstrapped")):
        return False
    if os.path.exists(md + ".pre-ceo"):
        return False
    try:
        with open(md, "rb") as a, open(ceo, "rb") as b:
            return a.read() != b.read()
    except OSError:
        return False


def login_line(login_needed, trust):
    if login_needed:
        s = "새 부서 화면에서 로그인을 한 번 하셔야 합니다."
    else:
        s = "따로 로그인하지 않습니다."
    if trust != "trusted" or login_needed:
        s += " 처음 한 번 「이 폴더를 믿겠습니까」 확인 창이 뜰 수 있습니다 — 뜨면 「예」 쪽을 눌러 주세요."
    return s


def render_create_card(r, gate, n_live):
    nodes = ((gate or {}).get("measured") or {}).get("nodes")
    if isinstance(nodes, int):
        seats = "켜진 Claude 자리 지금 %d개 → 만들면 %d개" % (nodes, nodes + 3)
    else:
        seats = "켜진 Claude 자리는 세지 못했습니다"
    folder = r["cwd"]
    if not os.path.isdir(os.path.join(home(), "Desktop")):
        folder += "  (이 폴더는 화면의 바탕화면에는 보이지 않을 수 있습니다)"
    lines = [
        "📋 새 부서 제안",
        "  이름        %s" % r["display"],
        "  맡을 일     %s" % r["mission"],
        "  자리        Claude 3개가 새로 켜집니다(부서장·운영 담당·작업자) — 사용량이 그만큼 더 듭니다.",
        "  지금 여유   부서 %d/%d · %s" % (n_live, chat_cap(), seats),
        "  폴더        %s" % folder,
        "  로그인      %s" % login_line(r["login_needed"], r["trust"]),
        "  부서에 적어 둘 안내   %s  (전문: %s)" % (os.path.join(r["cwd"], "CLAUDE.md"),
                                                 os.path.join(req_dir(r["id"]), "claude_md.txt")),
    ]
    if r.get("first_task"):
        lines.append("  처음 맡길 일  %s" % r["first_task"])
    if r.get("promotion_line"):
        lines.append("  첫 부서를 만들면 저(마스터)의 역할이 「부서들을 총괄하는 마스터」로 바뀝니다.")
    lines.append("이대로 만들까요?  (네 / 아니요 / 고칠 곳을 말씀해 주세요)")
    return "\n".join(lines) + "\n"


def render_close_card(r):
    last = r.get("last_dept")
    keep = ("[Windows] 대화 기록은 이 컴퓨터에 그대로 남습니다(자동 정리되지 않습니다)."
            if os.name == "nt" else "대화 기록은 14일 보관됩니다.")
    s = ("「%s」(%s)를 닫습니다. 꺼지는 것: 그 부서의 Claude 3개와 부서 프로그램. %s "
         "그대로 남는 것: 폴더(%s)의 파일 전부." % (r["display"], r["target"], keep, r.get("cwd") or "-"))
    if last:
        s += " 마지막 부서라서 저는 다시 보통 마스터로 돌아옵니다."
    return s + " 닫을까요?\n"


# ── CLAUDE.md(A-1·A-2 · 2R 1-A 정정) ──────────────────────────────────────────
def build_claude_md(rid, display, mission, body):
    """전문 = 표식 줄 + 역할 안내 줄(고정 문구) + LLM 이 지은 본문. 표식의 sha256 = 표식 줄 **아래**
    전부의 해시 — kickoff 본문이 같은 값의 앞 12자리를 싣고 부서장이 자기 CLAUDE.md 와 대조한다.
    ※실제 cwd 로 이 파일을 읽는 것은 부서장(master) 좌석이다. 운영 담당(cso/)·작업자(workers/w1/)는
      하위 폴더에서 뜨고 거기엔 javis_seat 의 얇은 CLAUDE.md 가 먼저 있다 — 이 파일은 상위 폴더 탐색으로만
      닿는다(2R 1-A · 우선순위 = V-MISSION 관찰 항목)."""
    rest = "%s\n# 이 부서: %s\n## 맡은 일\n%s\n%s" % (ROLE_GUIDE, display, mission, body.rstrip("\n") + "\n")
    sha = sha256_text(rest)
    return "%srequest=%s sha256=%s -->\n%s" % (MARKER_PREFIX, rid, sha, rest), sha


def claude_md_marker(path):
    try:
        with open(path, encoding="utf-8") as f:
            first = f.readline()
    except (OSError, UnicodeDecodeError):
        return None
    return first if first.startswith(MARKER_PREFIX) else None


# ── propose ───────────────────────────────────────────────────────────────────
def _supersede_open(except_id=None):
    for r in all_reqs():
        if r.get("state") == "proposed" and r["id"] != except_id:
            r["state"] = "superseded"
            r["superseded_at"] = now()
            save_req(r)


def _refuse(say, code=5, **kw):
    out(dict({"ok": False, "say": say}, **kw))
    return code


def cmd_propose(a):
    if not lane_is_base():
        return _refuse("부서는 맨 처음 화면의 마스터(본부)에서만 만들 수 있습니다. 본부 마스터에게 말씀해 주세요.",
                       reason="lane")
    reg, ts, cat = registry(), tombstones(), catalog()
    live = live_depts(reg, ts)
    if a.close is not None:
        return _propose_close(a, reg, ts, cat, live)
    disp = norm_name(a.name)
    prob = name_problem(disp)
    if prob:
        return _refuse(prob, reason="name")
    if display_taken(disp, reg, cat):
        return _refuse("이미 「%s」가 있습니다. 그 부서를 쓰시거나 다른 이름을 말씀해 주세요." % disp,
                       reason="duplicate")
    if len(live) >= chat_cap():
        return _refuse("지금 부서가 %d개 있어서(메뉴로 만드신 부서 포함) 더 만들 수 없습니다. "
                       "하나를 닫으시면 만들 수 있습니다." % len(live), reason="cap")
    gate = resource_check()
    if gate.get("verdict") == "hard_block":
        return _refuse("지금 컴퓨터가 바빠서 부서를 새로 켜기 어렵습니다. 조금 뒤에 다시 말씀해 주세요.",
                       reason="resource")
    mission = norm_name(a.mission)
    if not mission:
        return _refuse("부서가 맡을 일을 한 줄로 말씀해 주세요.", reason="mission", code=2)
    try:
        with open(a.claude_md_file, encoding="utf-8") as f:
            body = f.read()
    except (OSError, UnicodeDecodeError) as e:
        return _refuse("안내문 파일을 읽지 못했습니다: %s" % e, code=2, reason="io")
    utter = ""
    if a.utterance_file:
        try:
            with open(a.utterance_file, encoding="utf-8") as f:
                utter = f.read()
        except (OSError, UnicodeDecodeError):
            utter = ""
    rid = new_req_id()
    key = new_key(cat)
    acct_key, login_needed = account_plan()
    cwd = workdir_for(disp)
    text, sha = build_claude_md(rid, disp, mission, body)
    first = norm_name(a.first_task) if a.first_task else ""
    r = {"id": rid, "kind": "create", "state": "proposed", "created_at": now(),
         "display": disp, "mission": mission, "key": key, "cwd": cwd,
         "account": acct_key, "account_mode": account_mode(), "login_needed": login_needed,
         "trust": trust_state(cwd), "first_task": first or None,
         "claude_md_sha256": sha256_text(text), "claude_md_marker_sha": sha,
         "promotion_line": promotion_line_applies(), "events": []}
    os.makedirs(req_dir(rid), exist_ok=True)
    atomic_write_text(os.path.join(req_dir(rid), "claude_md.txt"), text)
    if utter:
        atomic_write_text(os.path.join(req_dir(rid), "utterance.txt"), utter)
    card = render_create_card(r, gate, len(live))
    atomic_write_text(os.path.join(req_dir(rid), "card.txt"), card)
    _supersede_open(except_id=rid)       # 열린 제안은 언제나 1장(2-1 ②) — 새 것을 쓴 뒤 옛 것을 닫는다
    save_req(r)
    out({"ok": True, "request": rid, "card": card})
    return 0


def _propose_close(a, reg, ts, cat, live):
    q = norm_name(a.close)
    cands = []
    for n, e in live.items():
        mk = (e or {}).get("mission_key")
        cdisp = ((cat.get("departments") or {}).get(mk) or {}).get("display") if mk else None
        if q and (norm_name((e or {}).get("display_name")) == q or norm_name(cdisp) == q or n == q):
            cands.append(n)
    listing = " ".join("%s %s(%s · 폴더 %s)" % ("①②③④⑤⑥⑦⑧"[i] if i < 8 else "-",
                                               display_of(n, live[n], cat), n, live[n].get("cwd") or "-")
                       for i, n in enumerate(sorted(live)))
    if not cands:
        return _refuse("「%s」이라는 부서를 찾지 못했습니다. 지금 있는 부서는 %s 입니다. 화면 탭 이름을 바꾸셨다면 "
                       "처음 지은 이름으로 말씀해 주세요." % (q, listing or "없음"), reason="not_found", code=4)
    if len(cands) > 1:
        many = " ".join("%s %s(%s · 폴더 %s)" % ("①②③④⑤⑥⑦⑧"[i], display_of(n, live[n], cat), n,
                                                live[n].get("cwd") or "-") for i, n in enumerate(sorted(cands)))
        return _refuse("「%s」에 해당하는 부서가 여럿입니다: %s. 어느 부서를 닫을까요?" % (q, many),
                       reason="ambiguous", candidates=sorted(cands), code=5)
    target = cands[0]
    e = live[target]
    rid = new_req_id()
    r = {"id": rid, "kind": "close", "state": "proposed", "created_at": now(), "target": target,
         "display": display_of(target, e, cat), "cwd": e.get("cwd"), "key": e.get("mission_key"),
         "last_dept": len(live) == 1, "events": []}
    os.makedirs(req_dir(rid), exist_ok=True)
    card = render_close_card(r)
    atomic_write_text(os.path.join(req_dir(rid), "card.txt"), card)
    _supersede_open(except_id=rid)
    save_req(r)
    out({"ok": True, "request": rid, "card": card})
    return 0


# ── confirm ───────────────────────────────────────────────────────────────────
def pending_path():
    return os.path.join(root_dir(), ".pending")


def touch_pending():
    p = pending_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8"):
        pass


def cmd_confirm(a):
    if not lane_is_base():
        return _refuse("부서는 맨 처음 화면의 마스터(본부)에서만 만들 수 있습니다.", reason="lane")
    r = load_req(a.request)
    if not r:
        return _refuse("그런 제안 번호가 없습니다.", code=4, reason="not_found")
    if r["state"] == "superseded":
        return _refuse("앞서 보여 드린 제안은 새 제안으로 바뀌었습니다. 새 제안을 다시 보여 드립니다.",
                       code=6, reason="superseded")
    if r["state"] != "proposed":
        return _refuse("이 제안은 이미 처리됐습니다(%s)." % r["state"], code=7, reason="state")
    if r["kind"] == "create":
        with open(os.path.join(req_dir(r["id"]), "claude_md.txt"), encoding="utf-8") as f:
            text = f.read()
        if sha256_text(text) != r["claude_md_sha256"]:
            return _refuse("부서에 적어 둘 안내가 카드를 보여 드린 뒤 바뀌었습니다. 다시 제안하겠습니다.",
                           code=7, reason="claude_md_changed")
    # ★2R ① 순서 계약: request.json(confirmed) 을 **먼저** 영속하고 표지를 **나중에** 만든다.
    #   틱은 스캔 **전에** 표지를 rename 으로 치우므로(_pending_claim), 어떤 교차에서도
    #   「표지가 있거나 · 틱의 스캔이 이 확인을 본다」 둘 중 하나가 성립한다.
    r["state"] = "confirmed"
    r["confirmed_at"] = now()
    save_req(r)
    touch_pending()
    out({"ok": True, "request": r["id"], "say": "확인했습니다. 1분 안에 시작합니다 — 다 되면 알려 드리겠습니다."})
    return 0


# ── 판정(결정 트리 v2 · 2R ③ 반영) ────────────────────────────────────────────
R_VALUES = ("none", "proposed", "confirmed", "expired", "created", "reused", "create-timeout",
            "failed", "closed")
F_VALUES = ("complete", "pending", "missing")
P_VALUES = ("open", "closed", "unknown")


def _row_rules():
    """(행 번호, 판정 이름, 술어). 위에서부터 첫 매칭. 13행 = 그 밖."""
    return [
        (1, "unconfirmed-dept", lambda x: x["R"] == "none" and x["G"]),
        (2, "awaiting-confirm", lambda x: x["R"] == "proposed"),
        (3, "expired", lambda x: x["R"] == "expired"),
        (4, "failed", lambda x: x["R"] == "failed"),
        # ★2R ③: 묘비는 이름(dept-N)으로만 걸리고 번호는 재사용된다 — T 만으로 닫힘이라 말하면 같은 번호로
        #   다시 만든 부서(묘비 해소 실패·ROTATE·REUSE_UP 경로)를 「닫혀 있습니다」라고 거짓 보고한다.
        (5, "closed", lambda x: x["R"] == "closed" or (x["T"] and not x["G"])),
        (6, "queued", lambda x: x["R"] == "confirmed" and not x["G"]),
        (7, "stalled", lambda x: x["R"] in ("created", "reused", "create-timeout") and not x["G"]),
        (8, "gone", lambda x: x["G"] and not x["D"] and (x["F"] == "complete" or x["E"])),
        (9, "daemon-starting", lambda x: x["G"] and not x["D"]),
        (10, "needs-human", lambda x: x["G"] and x["D"] and x["P"] == "open"),
        (11, "seats-starting", lambda x: x["G"] and x["D"] and x["F"] in ("pending", "missing")),
        (12, "running", lambda x: x["G"] and x["D"] and x["F"] == "complete"),
    ]


def judge(x, rules=None):
    for row, name, pred in (rules if rules is not None else _row_rules()):
        if pred(x):
            return row, name
    return 13, "unknown"


def all_combos():
    for R, G, T, D, F, P, E in itertools.product(R_VALUES, (True, False), (True, False), (True, False),
                                                 F_VALUES, P_VALUES, (True, False)):
        yield {"R": R, "G": G, "T": T, "D": D, "F": F, "P": P, "E": E}


def formation_state(sock):
    import javis_formation as jf
    p = os.path.join(formation_dir(), jf._sanitize_key(sock) + ".json")
    d = load_json(p, None)
    if not isinstance(d, dict):
        return "missing"
    return "complete" if d.get("state") == "complete" else "pending"


def dept_status_json(sock):
    cys = _cys_bin()
    try:
        p = subprocess.run([cys, "--socket", sock, "status", "--json"], capture_output=True, text=True,
                           timeout=5, env=dict(os.environ, CYS_NO_AUTOSTART="1"), **NOWIN)
        if p.returncode != 0:
            return None
        d = json.loads(p.stdout)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def gate_axis_enabled():
    try:
        import javis_boot_node
        return bool(javis_boot_node.gate_pending_axis_enabled())
    except Exception:
        return False


def gate_state(st):
    surfaces = [s for s in (st or {}).get("surfaces") or [] if isinstance(s, dict)]
    if any(s.get("gate_pending") not in (None, False, "", {}) for s in surfaces):
        return "open"
    # null 은 「관문 없음」과 「축이 꺼짐(킬스위치 3종)」을 구별하지 못한다(C18) — 축이 켜져 있다고
    # 같은 스위치 미러로 확인될 때만 닫힘으로 읽는다.
    return "closed" if surfaces and gate_axis_enabled() else "unknown"


def axes_for(r, reg, ts, name=None, probe=True):
    """요청(또는 요청 없는 레지스트리 항목)에 대해 여섯 축 + 8행 경과(E)를 실물에서 읽는다."""
    R = r["state"] if r else "none"
    if R not in R_VALUES:
        R = "none"
    key = (r or {}).get("key")
    if name is None:
        name = reg_name_for_key(key, reg) if key else None
    G = bool(name and name in reg)
    if not name and r and r.get("dept_name"):
        name = r["dept_name"]
    T = bool(name and name in ts)
    D, F, P, E = False, "missing", "unknown", False
    if G and probe:
        sock = (reg.get(name) or {}).get("socket") or dept_sock(name)
        st = dept_status_json(sock)
        D = st is not None
        F = formation_state(sock)
        P = gate_state(st) if D else "unknown"
    started = (r or {}).get("create_started_at")
    E = bool(started and now() - started > GONE_AFTER_SEC) or (r is None)
    return {"R": R, "G": G, "T": T, "D": D, "F": F, "P": P, "E": E}, name


FAIL_SAY = {
    "claude_md_conflict": "그 이름의 폴더에 이미 다른 안내 파일(CLAUDE.md)이 있어서 만들지 않았습니다. "
                          "다른 이름을 말씀해 주시거나 그 파일을 옮겨 주세요.",
    "claude_md_changed": "부서에 적어 둘 안내가 확인 뒤에 바뀌어서 만들지 않았습니다. 다시 말씀해 주세요.",
    "cysd_not_found": "부서 프로그램을 찾지 못해 만들지 못했습니다. 이 프로그램을 다시 설치해야 할 수 있습니다.",
    "cap": "그 사이 부서가 %d개가 되어(메뉴로 만드신 부서 포함) 더 만들 수 없었습니다." ,
    "resource": "컴퓨터가 너무 바빠서 만들지 못했습니다. 조금 뒤에 다시 말씀해 주세요.",
    "create_hang": "부서를 만드는 일이 너무 오래 걸려 멈췄습니다.",
}


def say_for(row, r, name, x, reg=None, cat=None):
    disp = (r or {}).get("display") or (display_of(name, (reg or {}).get(name), cat) if name else "?")
    if r and r.get("kind") == "close":
        return {"proposed": "아직 확인을 받지 않은 닫기 제안입니다.",
                "confirmed": "「%s」을 닫을 차례를 기다리고 있습니다 — 1분 안에 시작합니다." % disp,
                "expired": "확인하신 뒤 30분 안에 닫지 못했습니다(컴퓨터가 잠들었던 경우 등). 다시 닫을까요?",
                "closed": "「%s」은 닫혀 있습니다." % disp,
                "failed": "「%s」을 닫지 못했습니다(%s)." % (disp, r.get("fail_reason") or "사유 불명"),
                }.get(r["state"], "닫기 요청 상태: %s" % r["state"])
    if row == 1:
        return "「%s」은 제가 만든 부서가 아닙니다(메뉴로 만들어진 부서)." % disp
    if row == 2:
        return "아직 확인을 받지 않은 제안입니다."
    if row == 3:
        return "확인하신 뒤 30분 안에 만들지 못했습니다(컴퓨터가 잠들었던 경우 등). 다시 만들까요?"
    if row == 4:
        reason = (r or {}).get("fail_reason") or ""
        base = FAIL_SAY.get(reason.split(":")[0])
        if reason.startswith("cap"):
            base = FAIL_SAY["cap"] % chat_cap()
        left = " 남은 것: %s" % r.get("leftover") if (r or {}).get("leftover") else " 남은 것은 없습니다."
        return "「%s」을 만들지 못했습니다. %s%s" % (disp, base or "(사유: %s)" % reason, left)
    if row == 5:
        return "「%s」은 닫혀 있습니다." % disp
    if row == 6:
        if (r or {}).get("waiting_gap"):
            return ("앞선 부서를 만든 지 10분이 지나야 다음 부서를 만들 수 있습니다 — 그때 자동으로 이어서 "
                    "만듭니다.")
        return "「%s」을 만들 차례를 기다리고 있습니다 — 1분 안에 시작합니다." % disp
    if row == 7:
        return "「%s」을 만들다 멈췄습니다. 이어서 만들까요, 지울까요?" % disp
    if row == 8:
        return ("「%s」이 지금 꺼져 있습니다. 컴퓨터를 다시 켠 뒤 그 부서 화면을 아직 열지 않으셨다면 이런 상태가 "
                "됩니다. 왼쪽 부서 화면(없으면 왼쪽 위 부서 추가 메뉴의 「%s」)을 여시면 다시 켜집니다." % (disp, disp))
    if row == 9:
        return "「%s」을 켜는 중입니다." % disp
    if row == 10:
        return ("「%s」 화면에 확인 창이 떠 있어 사람 손이 필요합니다. 그 부서 화면을 열어 안내대로 진행해 "
                "주십시오(「No, exit」는 누르지 마세요)." % disp)
    if row == 11:
        return "「%s」의 자리(부서장·운영 담당·작업자)를 켜는 중입니다." % disp
    if row == 12:
        s = ("「%s」이 가동 중입니다. 왼쪽 부서 화면에서 부서장에게 직접 말씀하셔도 됩니다." % disp)
        if x.get("P") == "unknown":
            s += " 부서 화면에 확인 창이 떠 있으면 안내대로 진행해 주십시오."
        return s
    return "「%s」의 상태를 확인하지 못했습니다. 잠시 뒤 다시 여쭈어 주세요." % disp


def verdict_for(r, reg, ts, cat, name=None, probe=True):
    x, name = axes_for(r, reg, ts, name=name, probe=probe)
    row, label = judge(x)
    residue = bool(x["T"] and x["G"])
    if row == 13:
        try:
            os.makedirs(root_dir(), exist_ok=True)
            with open(os.path.join(root_dir(), "status-unknown.log"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"at": iso(), "request": (r or {}).get("id"), "dept": name, "axes": x},
                                   ensure_ascii=False) + "\n")
        except OSError:
            pass
    res = {"request": (r or {}).get("id"), "dept": name, "row": row, "verdict": label,
           "axes": x, "say": say_for(row, r, name, x, reg, cat)}
    if residue:
        # ★2R ③: 묘비 잔존 = 코드 자신이 「재시작에서 부서 reap 위험」이라 적은 상태 — WARN 이 아니라 결정론 칸.
        res["tombstone_residue"] = True
    return res


# ── status ────────────────────────────────────────────────────────────────────
def cmd_status(a):
    reg, ts, cat = registry(), tombstones(), catalog()
    reqs = [r for r in all_reqs() if r.get("state") not in ("superseded", "discarded")]
    rows = []
    if a.say:
        r = load_req(a.say)
        if not r:
            return _refuse("그런 번호가 없습니다.", code=4)
        v = verdict_for(r, reg, ts, cat)
        r["said_row"] = v["row"]
        r["said_state"] = r["state"]
        save_req(r)
        out(v)
        return 0
    for r in reqs:
        if a.pending:
            # 「아직 사용자에게 말하지 않은 판정」만 — 확인 대기 제안은 제외, 판정 행이 바뀌면 다시 올라온다.
            # 7일 넘게 움직임 없는 요청은 올리지 않는다(오래된 기록이 매 턴 반복되지 않게).
            if r["state"] == "proposed" or now() - (r.get("updated_at") or 0) > 7 * DAY:
                continue
        v = verdict_for(r, reg, ts, cat)
        if a.pending and r.get("said_row") == v["row"] and r.get("said_state") == r["state"]:
            continue
        rows.append(v)
    if a.all:
        claimed = {reg_name_for_key(r.get("key"), reg) for r in reqs if r.get("key")} | \
                  {r.get("dept_name") for r in reqs}
        for n in sorted(reg):
            if n in claimed:
                continue
            rows.append(verdict_for(None, reg, ts, cat, name=n))
    out({"ok": True, "rows": rows})
    return 0


# ── discard ───────────────────────────────────────────────────────────────────
def cmd_discard(a):
    r = load_req(a.request)
    if not r:
        return _refuse("그런 번호가 없습니다.", code=4)
    reg = registry()
    if r.get("kind") == "create" and r.get("key") and reg_name_for_key(r["key"], reg):
        return _refuse("이미 만들어진 부서가 있어 지울 수 없습니다 — 닫기로 말씀해 주세요.", code=7, reason="exists")
    removed = []
    if r.get("kind") == "create" and r.get("state") not in ("proposed", "superseded"):
        import javis_org
        key = r["key"]
        lock = catalog_json() + ".lock"
        os.makedirs(os.path.dirname(lock) or ".", exist_ok=True)
        with open(lock, "w") as lf:
            javis_org._flock(lf)
            cat = catalog()
            if key in cat["departments"]:
                del cat["departments"][key]
                atomic_write_json(catalog_json(), cat)
                removed.append("catalog")
        mf = os.path.join(missions_dir(), key + ".md")
        if os.path.exists(mf):
            os.remove(mf)
            removed.append("mission")
        cm = os.path.join(r["cwd"], "CLAUDE.md")
        mk = claude_md_marker(cm)
        if mk and ("request=%s " % r["id"]) in mk:
            os.remove(cm)
            removed.append("CLAUDE.md")
    r["state"] = "discarded"
    r["discarded_at"] = now()
    save_req(r)
    out({"ok": True, "request": r["id"], "removed": removed, "say": "지웠습니다."})
    return 0


# ── kickoff ───────────────────────────────────────────────────────────────────
def _cys_bin():
    return os.environ.get("CYS_BIN") or shutil.which("cys") or "cys"


def cmd_kickoff(a):
    if not lane_is_base():
        return _refuse("본부 마스터만 부서장에게 첫 일을 전할 수 있습니다.", reason="lane")
    r = load_req(a.request)
    if not r or r.get("kind") != "create":
        return _refuse("그런 부서 요청이 없습니다.", code=4)
    if not r.get("first_task"):
        return _refuse("처음 맡길 일이 기록돼 있지 않습니다.", code=7, reason="no_first_task")
    if r.get("kicked_off_at"):
        return _refuse("첫 일은 이미 전했습니다.", code=7, reason="already")
    reg, ts, cat = registry(), tombstones(), catalog()
    v = verdict_for(r, reg, ts, cat)
    if v["row"] != 12:
        return _refuse("부서가 아직 가동 전이라 첫 일을 전하지 않았습니다(%s)." % v["verdict"], code=7,
                       reason="not_running")
    name = v["dept"]
    sock = (reg.get(name) or {}).get("socket") or dept_sock(name)
    body = "[부서시작 %s] (CLAUDE.md sha256 %s) 오너가 처음 맡긴 일: %s" % (
        r["id"], r["claude_md_marker_sha"][:12], r["first_task"])
    # ★--queued 는 CR 을 포함해 배달한다 — Return 을 덧붙이지 않는다(이중 제출 · cys.rs 큐 배달 주석).
    p = subprocess.run([_cys_bin(), "--socket", sock, "send", "--queued", "--to", "master", body],
                       capture_output=True, text=True, timeout=20, **NOWIN)
    if p.returncode != 0:
        return _refuse("부서장에게 전하지 못했습니다(rc=%d). 그 부서 화면의 부서장에게 직접 말씀해 주세요."
                       % p.returncode, code=1, reason="send_failed")
    r["kicked_off_at"] = now()
    save_req(r)
    out({"ok": True, "request": r["id"], "say": "부서장에게 처음 맡기실 일을 전했습니다."})
    return 0


# ── tick ──────────────────────────────────────────────────────────────────────
def lock_path():
    return os.path.join(root_dir(), ".lock")


def _pid_alive(pid):
    # 이 프로세스의 자식이 이미 끝났다면 좀비로 남아 kill(0) 이 성공한다 — 먼저 회수를 시도한다
    # (남의 자식이면 ChildProcessError 로 조용히 넘어간다).
    if os.name == "posix":
        try:
            done, _ = os.waitpid(int(pid), os.WNOHANG)
            if done:
                return False
        except (ChildProcessError, ValueError, OSError):
            pass
    try:
        import javis_lock
        return javis_lock.pid_alive(pid)
    except Exception:
        try:
            os.kill(int(pid), 0)
            return True
        except Exception:
            return False


def acquire_lock():
    """mkdir 원자 잠금 · 소유자 pid 사망 시 rename 원자 회수(한 명만 성공)."""
    lp = lock_path()
    os.makedirs(root_dir(), exist_ok=True)
    for _ in range(2):
        try:
            os.mkdir(lp)
            atomic_write_json(os.path.join(lp, "owner.json"), {"pid": os.getpid(), "since": now()})
            return True
        except FileExistsError:
            o = load_json(os.path.join(lp, "owner.json"), {}) or {}
            pid = o.get("pid")
            if pid and _pid_alive(pid):
                return False
            if not pid:
                try:
                    if now() - os.path.getmtime(lp) < 60:   # 소유자 기록 전 찰나 — 회수하지 않는다
                        return False
                except OSError:
                    continue
            stale = "%s.stale-%d-%s" % (lp, os.getpid(), secrets.token_hex(3))
            try:
                os.rename(lp, stale)                     # 회수 권리 = rename 한 명만
            except OSError:
                return False
            shutil.rmtree(stale, ignore_errors=True)
    return False


def release_lock():
    shutil.rmtree(lock_path(), ignore_errors=True)


def _pending_claim():
    """★2R ① 봉합: 스캔 **전에** 표지를 rename 으로 치운다. 이후 confirm 이 만드는 표지는 새 파일이라
    이 틱이 지우지 않는다. 반환 = 표지가 있었는가."""
    p = pending_path()
    claimed = "%s.claimed-%d" % (p, os.getpid())
    try:
        os.rename(p, claimed)
    except FileNotFoundError:
        return False
    try:
        os.remove(claimed)
    except OSError:
        pass
    return True


def _in_progress(r):
    st = r.get("state")
    if st in IN_FLIGHT:
        return True
    if r.get("kind") == "create" and st in ("created", "reused") and not r.get("running_notified") \
            and now() - (r.get("create_started_at") or 0) < RUNNING_WATCH_SEC:
        return True
    return False


_TEST_HOOK_BEFORE_FINALIZE = None   # 시험 전용: 스캔 끝 ~ 표지 결론 사이에 confirm 을 끼운다


def _pending_finalize(any_in_progress):
    if _TEST_HOOK_BEFORE_FINALIZE:
        _TEST_HOOK_BEFORE_FINALIZE()
    if any_in_progress:
        touch_pending()
    # 진행 중 0 이면 아무것도 지우지 않는다 — 표지는 이미 _pending_claim 이 치웠고, 그 뒤에 생긴 표지는
    # 이 틱이 보지 못한 confirm 의 것이다(지우면 lost-update).


def _event(r, what):
    r.setdefault("events", []).append({"at": iso(), "what": what})


def _notify(r, tag):
    """상태 전이당 1회 · base 소켓 · --queued(Return 없음). ACL 에 막혀도 기능은 선다(마스터가 턴마다
    status --pending 을 부른다) — 결과는 기록만 한다."""
    key = "%s:%s" % (tag, r.get("state"))
    if key in (r.get("notified") or []):
        return
    body = "[%s] %s" % (tag, r["id"])
    try:
        env = dict(os.environ)
        p = subprocess.run([_cys_bin(), "send", "--queued", "--to", "master", body], capture_output=True,
                           text=True, timeout=20, env=env, **NOWIN)
        rc = p.returncode
    except Exception:
        rc = 127
    r.setdefault("notified", []).append(key)
    _event(r, "notify %s rc=%s" % (tag, rc))


def _move_to_trash(path, label):
    dest_dir = os.path.join(trash_root(), "%s-%s" % (label, time.strftime("%Y%m%d-%H%M%S")))
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(path))
    os.replace(path, dest)
    return dest


def cleanup_orphan_ledgers():
    """B-1 래치 청소 — 부서 소켓 모양의 편성 원장 중 그 부서가 레지스트리에 없는 것 → 휴지통(삭제 아님).
    ★본부 원장 절대 제외(R4). 원장 키는 javis_formation._sanitize_key 를 import 해 쓴다(재구현 금지 ·
    120자 절단 분기 포함 — 원장 안의 socket 필드로 키를 **재산출해 파일명과 일치할 때만** 대상).
    ★이동 직전 레지스트리 재독(GUI 가 같은 번호를 막 예약한 경합 창을 좁힌다)."""
    import javis_formation as jf
    fd = formation_dir()
    try:
        names = sorted(os.listdir(fd))
    except OSError:
        return []
    moved = []
    base_keys = {jf._sanitize_key(""), jf._sanitize_key(None), "base"}
    base_sock = os.environ.get("CYS_BASE_SOCKET") or os.path.join(base_state_dir(), "cys.sock")
    base_keys.add(jf._sanitize_key(base_sock))
    for fn in names:
        if not fn.endswith(".json"):
            continue
        key = fn[:-5]
        if key in base_keys:
            continue
        d = load_json(os.path.join(fd, fn), None)
        sock = (d or {}).get("socket") if isinstance(d, dict) else None
        if not sock or jf._sanitize_key(sock) != key:
            continue
        m = re.search(r"cys-dept-([A-Za-z0-9][A-Za-z0-9_-]{0,39})", sock)
        if not m:
            continue
        name = m.group(1)
        if name in registry():                 # 이동 직전 재독
            continue
        try:
            moved.append(_move_to_trash(os.path.join(fd, fn), "formation"))
        except OSError:
            pass
    return moved


def _rm(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True
    except FileNotFoundError:
        return False


def _sweep(reqs):
    """★2R ② 봉합: 만료·수명 정리·고아 원장 청소는 **매 틱 무조건**(표지와 무관). 전부 멱등·저비용."""
    t = now()
    changed = []
    for r in reqs:
        st = r.get("state")
        # ⓑ 만료 — 확인 뒤 TTL 넘게 집행이 **시작되지 않은** 요청(절전 뒤 깨어난 경우 포함)
        if st == "confirmed" and not r.get("create_started_at") and not r.get("close_started_at") and \
                t - (r.get("confirmed_at") or t) > CONFIRM_TTL_SEC():
            r["state"] = "expired"
            r["expired_at"] = t
            _event(r, "expired")
            save_req(r)
            changed.append(r)
            st = "expired"
        # 수명(§4-4 · 개인정보) — 발화 원문과 폴더
        age = t - (r.get("updated_at") or r.get("created_at") or t)
        d = req_dir(r["id"])
        utter = os.path.join(d, "utterance.txt")
        if st in ("superseded", "expired", "discarded"):
            if age > 30 * DAY:
                _rm(d)
                continue
            if age > 7 * DAY and os.path.exists(utter):
                _rm(utter)
        elif st in ("closed", "failed") or (st in ("created", "reused") and r.get("running_notified")):
            if age > 30 * DAY and os.path.exists(utter):
                _rm(utter)
    moved = cleanup_orphan_ledgers()
    # 자가복구 벨트: 진행 중 요청이 있는데 표지가 없으면 다시 세운다(어떤 경로로 잃었든 1분 안에 회복).
    if any(_in_progress(r) for r in reqs if os.path.isdir(req_dir(r["id"]))) and \
            not os.path.exists(pending_path()) and _SELF_HEAL:
        touch_pending()
    try:
        atomic_write_text(os.path.join(root_dir(), ".last-sweep"), iso(t) + "\n")
    except OSError:
        pass
    return changed, moved


_SELF_HEAL = True


def tick_state_path():
    return os.path.join(root_dir(), ".tick-state.json")


def find_cysd():
    """V-PATH: ⑴PATH ⑵이 팩을 부르는 cys 와 같은 폴더 ⑶맥 앱 번들 후보 ⑷/opt/homebrew/bin.
    (데몬은 스케줄 자식에 자기 exe_dir 을 PATH 선두로 준다 — schedule.rs apply_spawn_env · 2R 부기)"""
    exe = "cysd.exe" if os.name == "nt" else "cysd"
    c = shutil.which("cysd")
    if c:
        return c
    cands = []
    cy = shutil.which("cys")
    if cy:
        cands.append(os.path.join(os.path.dirname(os.path.realpath(cy)), exe))
    for app in ("cysr.app", "cys.app"):
        cands.append(os.path.join("/Applications", app, "Contents", "MacOS", exe))
        cands.append(os.path.join(home(), "Applications", app, "Contents", "MacOS", exe))
    cands.append("/opt/homebrew/bin/cysd")
    for c in cands:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def cys_dept_bin():
    return os.environ.get("CYS_DEPT_BIN") or os.path.join(HERE, "cys-dept")


def _spawn_create(key, cysd):
    env = dict(os.environ)
    env["CYS_ROLE"] = "cso"
    env["PATH"] = os.path.dirname(cysd) + os.pathsep + env.get("PATH", "")
    logp = os.path.join(root_dir(), ".create-%s.log" % key)
    lf = open(logp, "ab")
    # ★V-DETACH(R1): 틱 세션에서 떼어 낸다 — POSIX = 새 세션, Windows = 새 프로세스 그룹 + 창 숨김
    #   (CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP · 출력을 받는 호출이라 창 숨김 계약 대상).
    flags = (0x08000000 | 0x00000200) if os.name == "nt" else 0
    p = subprocess.Popen([cys_dept_bin(), "create", key], stdout=subprocess.PIPE, stderr=lf,
                         stdin=subprocess.DEVNULL, env=env, creationflags=flags,
                         start_new_session=(os.name != "nt"))
    return p, lf


def _seed_account(cat_path, acct_key):
    import javis_org
    lock = cat_path + ".lock"
    os.makedirs(os.path.dirname(lock) or ".", exist_ok=True)
    with open(lock, "w") as lf:
        javis_org._flock(lf)
        cat = catalog()
        if acct_key not in cat["accounts"]:
            cat["accounts"][acct_key] = base_account_dir()
            atomic_write_json(cat_path, cat)
            return True
    return False


def _write_claude_md(r):
    with open(os.path.join(req_dir(r["id"]), "claude_md.txt"), encoding="utf-8") as f:
        text = f.read()
    if sha256_text(text) != r["claude_md_sha256"]:
        return "claude_md_changed"
    dest = os.path.join(r["cwd"], "CLAUDE.md")
    if os.path.exists(dest) and not claude_md_marker(dest):
        return "claude_md_conflict"            # 사용자 파일 보존이 우선
    atomic_write_text(dest, text)
    return None


def _fail(r, reason, leftover=None):
    r["state"] = "failed"
    r["fail_reason"] = reason
    if leftover:
        r["leftover"] = leftover
    _event(r, "failed %s" % reason)


def _retry_tombstone_remove(name):
    """★2R ③: cys-dept 는 묘비 해소 실패를 WARN 1줄로만 남긴다 — 틱이 **자기 생성 직후 1회** 재시도한다.
    (다른 때는 하지 않는다: GUI 닫기의 의도-선기록 묘비를 지우면 닫은 부서가 되살아난다.)"""
    cys = _cys_bin()
    env = dict(os.environ)
    env.pop("CYS_SOCKET", None)
    try:
        subprocess.run([cys, "tombstone", "--dept", "--remove", "--", name], capture_output=True, text=True,
                       timeout=20, env=env, **NOWIN)
    except Exception:
        pass
    ph = os.path.join(pack_default(), "bin", "javis_phoenix.py")
    if os.path.isfile(ph):
        try:
            subprocess.run([sys.executable, ph, "tombstone", name, "--dept", "--remove"], capture_output=True,
                           text=True, timeout=20, **NOWIN)
        except Exception:
            pass
    return name not in tombstones()


def _finish_create(r, name, pre_reg):
    import javis_org
    r["dept_name"] = name
    r["state"] = "reused" if name in pre_reg else "created"
    javis_org.backfill_mission_key(depts_json(), r["key"], r["key"], r["display"])
    if name in tombstones():
        ok = _retry_tombstone_remove(name)
        r["tombstone_retry"] = "resolved" if ok else "residue"
    _event(r, "%s %s" % (r["state"], name))


def _create_step(r, st, reqs):
    """ⓓ 생성 1건."""
    import javis_org
    reg, ts = registry(), tombstones()
    t = now()
    if r["state"] == "create-timeout":
        pid = r.get("create_pid")
        if pid and _pid_alive(pid):
            # ★2R ⑦: 첫 자식이 살아 있으면 재호출하지 않는다(그 자식의 EXIT trap 이 두 번째 등재를 지운다).
            if t - (r.get("create_started_at") or t) > CREATE_HANG_SEC():
                _fail(r, "create_hang", leftover="부서 만들기 프로그램이 아직 돌고 있습니다(pid %s)" % pid)
            return
        name = reg_name_for_key(r["key"], reg)
        if name:
            _finish_create(r, name, r.get("pre_reg") or [])
            return
        if (r.get("create_calls") or 0) >= MAX_CREATE_CALLS:
            _fail(r, "create_timeout_exhausted")
            return
    else:
        live = live_depts(reg, ts)
        if len(live) >= chat_cap():
            _fail(r, "cap:%d" % len(live))
            return
        last = (st.get("last_create_at") or 0)
        if t - last < CREATE_GAP_SEC():
            r["waiting_gap"] = True
            return
        gate = resource_check()
        if gate.get("verdict") == "hard_block":
            _fail(r, "resource")
            return
        # 효과 함수 순서: catalog_upsert → write_mission → ensure_dirs → CLAUDE.md → create → backfill
        seeded = _seed_account(catalog_json(), r["account"])
        if seeded:
            r["account_seeded"] = r["account"]           # A-7: 시드 사실을 요청 기록에 남긴다
        javis_org.catalog_upsert(catalog_json(), {"key": r["key"], "display": r["display"],
                                                   "account": r["account"], "cwd": r["cwd"]})
        javis_org.MISSIONS = missions_dir()
        javis_org.write_mission(r["key"], "# %s\n%s\n" % (r["display"], r["mission"]))
        javis_org.ensure_dirs({"cwd": r["cwd"]})
        err = _write_claude_md(r)
        if err:
            _fail(r, err, leftover="카탈로그 항목 1개(지우기로 걷을 수 있습니다)")
            return
    cysd = find_cysd()
    if not cysd:
        _fail(r, "cysd_not_found")
        return
    r["pre_reg"] = sorted(registry())
    r["create_started_at"] = r.get("create_started_at") or t
    r["create_calls"] = (r.get("create_calls") or 0) + 1
    st["last_create_at"] = t
    r.pop("waiting_gap", None)
    p, lf = _spawn_create(r["key"], cysd)
    r["create_pid"] = p.pid
    save_req(r)                                          # 기다리는 동안 틱이 죽어도 pid 가 남는다
    try:
        so, _ = p.communicate(timeout=CREATE_WAIT_SEC())
    except subprocess.TimeoutExpired:
        r["state"] = "create-timeout"
        _event(r, "create-timeout pid=%s" % p.pid)
        lf.close()
        return
    lf.close()
    lines = [x.strip() for x in (so or b"").decode("utf-8", "replace").splitlines() if x.strip()]
    name = lines[-1] if lines else ""
    if p.returncode == 0 and re.match(r"^dept-\d+$", name):
        _finish_create(r, name, r["pre_reg"])
    else:
        _fail(r, "create_rc:%s" % p.returncode, leftover="카탈로그 항목 1개(지우기로 걷을 수 있습니다)")


def _close_step(r):
    """ⓔ 닫기 1건 — GUI 와 같은 destroy(묘비를 남기는 기존 명령 · --purge-workdir 절대 금지)."""
    reg = registry()
    if r["target"] not in reg:
        r["state"] = "closed"
        _event(r, "closed(already)")
        return
    r["close_started_at"] = now()
    org = os.environ.get("CYS_DEPT_ORG_BIN") or os.path.join(HERE, "javis_org.py")
    env = dict(os.environ)
    env["CYS_ROLE"] = "cso"
    env["CYS_DEPT_BIN"] = cys_dept_bin()
    try:
        p = subprocess.run([sys.executable, org, "destroy", "--dept", r["target"], "--purge", "--purge-state"],
                           capture_output=True, text=True, timeout=CREATE_WAIT_SEC(), env=env, **NOWIN)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        rc = 124
    if rc == 0:
        r["state"] = "closed"
        _event(r, "closed")
    else:
        _fail(r, "close_rc:%s" % rc)
    cleanup_orphan_ledgers()                           # B-1: 닫기 직후 그 부서의 편성 원장을 치운다


def cmd_tick(a):
    if os.environ.get("CYS_ROLE") != "cso":
        sys.stderr.write("[dept-request] tick 은 스케줄 틱(dept-request-tick) 전용 — CYS_ROLE=cso 신원 밖 호출 거부\n")
        return 3
    if not acquire_lock():
        return 0
    try:
        reqs = all_reqs()
        changed, moved = _sweep(reqs)                   # ★매 틱 무조건(2R ②)
        for r in changed:
            _notify(r, "부서결과")
            save_req(r)
        had = _pending_claim()                         # ★스캔 전에 표지를 치운다(2R ①)
        reqs = all_reqs()
        st = load_json(tick_state_path(), {}) or {}
        if had or any(_in_progress(r) for r in reqs):
            creates = sorted([r for r in reqs if r.get("kind") == "create" and r["state"] in IN_FLIGHT],
                             key=lambda r: (r["state"] != "create-timeout", r.get("confirmed_at") or 0))
            if creates:                                # 한 틱에 생성 1건(4군 ①)
                r = creates[0]
                before = r["state"]
                _create_step(r, st, reqs)
                save_req(r)
                atomic_write_json(tick_state_path(), st)
                if r["state"] != before:
                    _notify(r, "부서결과")
                    save_req(r)
            closes = sorted([r for r in reqs if r.get("kind") == "close" and r["state"] == "confirmed"],
                            key=lambda r: r.get("confirmed_at") or 0)
            if closes:                                 # 한 틱에 닫기 1건
                r = closes[0]
                _close_step(r)
                save_req(r)
                _notify(r, "부서결과")
                save_req(r)
            # ⓖ 가동 알림 — created/reused 중 판정이 가동으로 처음 바뀐 것
            reg, ts, cat = registry(), tombstones(), catalog()
            for r in all_reqs():
                if r.get("kind") == "create" and r["state"] in ("created", "reused") and \
                        not r.get("running_notified") and _in_progress(r):
                    v = verdict_for(r, reg, ts, cat)
                    if v["row"] == 12:
                        r["running_notified"] = now()
                        _notify(r, "부서가동")
                        save_req(r)
        _pending_finalize(any(_in_progress(r) for r in all_reqs()))
        return 0
    finally:
        release_lock()


# ── self-test ─────────────────────────────────────────────────────────────────
def self_test():
    fails = []

    def ck(name, cond, msg=""):
        print(("PASS " if cond else "FAIL ") + name + ((" — " + msg) if (msg and not cond) else ""))
        if not cond:
            fails.append(name)

    # ① 결정 트리 망라성: 9×2×2×2×3×3×2 = 1296 조합 · 전부 1~13 중 정확히 한 행(첫 매칭)
    combos = list(all_combos())
    ck("tree: 조합 수 1296", len(combos) == 1296, str(len(combos)))
    rows = [judge(x)[0] for x in combos]
    ck("tree: 전 조합이 1~13", all(1 <= r <= 13 for r in rows))
    hit = set(rows)
    ck("tree: 1~12 행 전부 도달(죽은 행 0)", all(i in hit for i in range(1, 13)),
       str(sorted(set(range(1, 13)) - hit)))
    unknown = [x for x in combos if judge(x)[0] == 13]
    # 13 행 조합 전수 출력(억제 목록은 전수로 낸다)
    print("INFO tree: 13행(판정 불능) 조합 %d개" % len(unknown))
    for x in unknown:
        print("  13 <- " + json.dumps(x, ensure_ascii=False, sort_keys=True))
    ck("tree: 13행 조합 = R=none∧G=없음∧T=없음 뿐",
       all(x["R"] == "none" and not x["G"] and not x["T"] for x in unknown))
    # 2R ③: 이름 재사용 — T∧G∧D∧F=complete 는 가동(12)이지 닫힘(5)이 아니다
    reuse = {"R": "created", "G": True, "T": True, "D": True, "F": "complete", "P": "closed", "E": False}
    ck("tree: 묘비 잔존+가동 부서 = 12행", judge(reuse)[0] == 12, str(judge(reuse)))
    ck("tree: 묘비+레지스트리 없음 = 5행",
       judge(dict(reuse, R="created", G=False))[0] == 5)
    # 내장 뮤턴트: 8행을 지우면 「레지스트리 ∧ 무응답 ∧ complete」 가 13 으로 떨어져야 한다
    # (설계 §6-2 는 「13번으로 떨어진다」고 적었으나 실제로는 9행(「켜는 중」)이 받는다 — 그래서 더 나쁘다:
    #  꺼진 부서를 켜는 중이라고 거짓 보고한다. 단언은 실제 귀착 행으로 한다.)
    no8 = [x for x in _row_rules() if x[0] != 8]
    gone = {"R": "created", "G": True, "T": False, "D": False, "F": "complete", "P": "unknown", "E": True}
    ck("tree-mutant: 8행 삭제 → 「켜는 중」 거짓 보고", judge(gone)[0] == 8 and judge(gone, no8)[0] == 9,
       "%s / %s" % (judge(gone), judge(gone, no8)))
    old5 = [(5, "closed", lambda x: x["R"] == "closed" or x["T"]) if row == 5 else (row, n, p)
            for row, n, p in _row_rules()]
    ck("tree-mutant: 옛 5행(T 만으로 닫힘) → 재사용 부서 오판", judge(reuse, old5)[0] == 5)
    # ② 키 계약
    ks = [new_key({"departments": {}}) for _ in range(50)]
    ck("key: c+hex6 소문자", all(KEY_RE.match(k) for k in ks))
    try:
        import javis_formation as jf
        ck("key: _sanitize_key 본부 규약", jf._sanitize_key("") == jf._sanitize_key(None) == "base")
    except Exception as e:
        ck("key: javis_formation import", False, str(e))
    # cys-dept dept_name_ok 규칙의 부분집합
    ck("key: cys-dept 이름 규칙 부분집합",
       all(re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$", k) for k in ks))
    # ③ 의미 대조 — javis_org 코드가 도구의 작업 폴더 규약을 받아들이는가
    try:
        import javis_org
        disp = "설교준비부"
        quote = "우리 교회에 %s 부서를 새로 두어 설교 준비를 돕게 한다" % disp
        m = {"kind": "org-manifest", "manifest_version": 1,
             "source": {"design_doc": "x", "design_doc_sha256": "x"},
             "departments": [{"key": "c0a1b2", "display": disp, "account": "shared",
                              "cwd": workdir_for(disp), "mission_md": "m", "source_quote": quote,
                              "new_dept_approved": True}], "tasks": []}
        errs = javis_org.validate_manifest(m, doc_text=quote,
                                           catalog={"accounts": {"shared": "/x"}, "departments": {}})
        ck("semantic: javis_org 가 도구의 cwd 규약을 수용", not [e for e in errs if "cwd" in e], str(errs))
        m2 = json.loads(json.dumps(m))
        m2["departments"][0]["cwd"] = workdir_for(disp).replace("CYSjavis", "CYSJavis")
        errs2 = javis_org.validate_manifest(m2, doc_text=quote,
                                            catalog={"accounts": {"shared": "/x"}, "departments": {}})
        ck("semantic-mutant: 규약 한 글자 변경 → javis_org 거부", any("cwd" in e for e in errs2))
    except Exception as e:
        ck("semantic: javis_org import", False, "%s: %s" % (type(e).__name__, e))
    # ④ 레인
    ck("lane: 본부", lane_is_base({"CYS_SOCKET": os.path.join(home(), ".local/state/cys/cys.sock")}))
    ck("lane: 부서 소켓", not lane_is_base({"CYS_SOCKET": home() + "/.local/state/cys-dept-dept-2/cys.sock"}))
    ck("lane: 부서 팩", not lane_is_base({"CYS_PACK_DIR": home() + "/.cys/pack-dept-dept-1"}))
    ck("lane: 윈 파이프", not lane_is_base({"CYS_SOCKET": r"\\.\pipe\cys-dept-dept-1"}))
    # ⑤ 계정 키 충돌(2R ④)
    saved = dict(os.environ)
    try:
        os.environ["CYS_DEPT_ACCOUNT_MODE"] = "shared"
        os.environ.pop("CYS_PRIMARY_ACCOUNT", None)
        ck("account: 기본 = 공유·로그인 없음", account_plan() == ("shared", False))
        os.environ["CYS_PRIMARY_ACCOUNT"] = "shared"
        ck("account: primary=shared 면 로그인 줄 자동 전환", account_plan()[1] is True)
        os.environ["CYS_DEPT_ACCOUNT_MODE"] = "fork"
        os.environ.pop("CYS_PRIMARY_ACCOUNT", None)
        ck("account: fork 폴백 = primary 키·로그인 1회", account_plan() == ("owner", True))
    finally:
        os.environ.clear()
        os.environ.update(saved)
    print("SELF-TEST %s (%d fail)" % ("PASS" if not fails else "FAIL", len(fails)))
    return 0 if not fails else 1


# ── main ──────────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(prog="javis_dept_request.py")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("propose")
    p.add_argument("--name")
    p.add_argument("--mission")
    p.add_argument("--claude-md-file", dest="claude_md_file")
    p.add_argument("--utterance-file", dest="utterance_file")
    p.add_argument("--first-task", dest="first_task")
    p.add_argument("--close")
    c = sub.add_parser("confirm")
    c.add_argument("request")
    sub.add_parser("tick")
    s = sub.add_parser("status")
    s.add_argument("--pending", action="store_true")
    s.add_argument("--all", action="store_true")
    s.add_argument("--say")
    k = sub.add_parser("kickoff")
    k.add_argument("request")
    d = sub.add_parser("discard")
    d.add_argument("request")
    sub.add_parser("self-test")
    a = ap.parse_args(argv)
    if a.cmd == "propose":
        if a.close is None and not (a.name and a.mission and a.claude_md_file):
            sys.stderr.write("propose: --name · --mission · --claude-md-file 필수(또는 --close <이름>)\n")
            return 2
        return cmd_propose(a)
    fn = {"confirm": cmd_confirm, "tick": cmd_tick, "status": cmd_status, "kickoff": cmd_kickoff,
          "discard": cmd_discard}.get(a.cmd)
    if a.cmd == "self-test":
        return self_test()
    if not fn:
        ap.print_help()
        return 2
    return fn(a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write("[dept-request] 내부 오류: %s: %s\n" % (type(e).__name__, e))
        sys.exit(1)
