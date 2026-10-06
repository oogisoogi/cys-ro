#!/usr/bin/env python3
"""javis_counsel.py — 상담소 자동 전달의 팩 쪽(TICKET=agora-t3-pack-collector).

참가자 PC 의 agora 클라이언트(`agora counsel auto`)가 읽을 재료를 **팩이** 만든다 — 신호 줄 쓰기 · 일일 사실 수집 ·
동봉 클라이언트 설치 · 30분 틱. 읽고 보내는 쪽은 agora(`agora/collector.py`)다. 두 쪽 계약(정규식·잠금·끄기 규칙)은
글자 그대로 같아야 한다 — 한쪽만 넓으면 한쪽이 버린 줄을 다른 쪽이 보낸다.

동사:
  signal --source <역할|층> --op <op> --error-code <code>   신호 한 줄 append(형식 밖·끔·잠금 2초 초과 = 버림)
  facts          결정론 일일 사실 → `<설정>/counsel/facts.json`(원자 교체 · 못 잰 칸은 뺀다 · null 0)
  ensure-client  `<팩>/install/agora-client.pin` + `.zip.b64` → `<설정>/lib`(설치 잠금 안 · 판정 = 트리 지문:
                 없음 = 설치 · 핀 지문 = 무동작 · 알려진 옛 판 지문 = 교체 · 그 밖(고친·모르는 트리) = 불가침 + 로그)
  tick           ensure-client → facts → `agora counsel auto --facts …`(스케줄 잡 `agora-counsel` · 30분 · 한 판 상한 540초)

★언제나 exit 0 · stdout 무출력 — 훅·preflight·cys-dept·Rust 업데이트 경로가 부르므로 이 도구의 실패가 호출자를 바꾸면
  안 된다. 결과는 `<설정>/counsel/tick.log`(JSON 줄 · 256KB 넘으면 `.1`)에만 남긴다.
<설정> = `$AGORA_CONFIG_DIR` 또는 `~/.config/agora`(agora participant.config_dir 와 같은 규칙).
"""
import base64
import datetime
import errno
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import time
import zipfile
sys.dont_write_bytecode = True  # SEAL-1 층4(형제 관례 · 이 파일은 형제 import 0)

NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

# ── 계약값 — agora `mail.py` 와 같은 글자(`\Z` + re.ASCII) ─────────────────────────
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\Z", re.ASCII)
OP_RE = re.compile(r"^[a-z0-9_.-]{1,32}\Z", re.ASCII)
ERROR_CODE_RE = re.compile(r"^[a-z0-9._-]{1,48}\Z", re.ASCII)
VERSION_RE = re.compile(r"^[0-9A-Za-z.+-]{1,32}\Z", re.ASCII)
OS_RE = re.compile(r"^(macos|windows|linux)(-[0-9.]{1,16})?\Z", re.ASCII)
CHECK_ID_RE = re.compile(r"^[a-z0-9-]{1,40}\Z", re.ASCII)
SHA_RE = re.compile(r"^[0-9a-f]{64}\Z", re.ASCII)
SIGNAL_SOURCES = ("master", "worker", "cso", "pack", "update")

COUNSEL_DIR = "counsel"
SIGNALS_FILE = "signals.jsonl"
SIGNALS_LOCK = "signals.lock"
STATE_FILE = "state.json"
FACTS_FILE = "facts.json"
TICK_LOG = "tick.log"
SIGNALS_MAX_BYTES = 2 * 1024 * 1024   # 넘으면 그 줄을 버린다(미발신 PC 의 무한 증가 차단)
LOG_MAX_BYTES = 256 * 1024
LOCK_WAIT_S = 2.0                      # 쓰는 쪽은 훅을 붙잡지 않는다 — 넘으면 버림
LOCK_RETRY_S = 0.05
DOCTOR_TIMEOUT_S = 60
CLI_TIMEOUT_S = 20
TICK_CAP_S = 540                       # 한 판 전체 상한 — cysd command 잡 600초 안쪽(cysd 는 시간 초과 자식을 안 죽인다)
AGORA_MIN_TIMEOUT_S = 30               # agora 에 남은 몫(540 − 경과)의 바닥
INSTALL_LOCK = "lib.install.lock"      # <설정> 옆 파일 · 존재 판정 ~ 게시까지 한 손
INSTALL_LOCK_WAIT_S = 60.0
KNOWN_FILE = "agora-client-known.txt"  # 자동 교체해도 되는 옛 판 지문 표(`<판본> <트리 지문>`)
MAX_LIST = 64


# ── 자리 ───────────────────────────────────────────────────────────────────
def config_dir():
    return os.path.abspath(os.environ.get("AGORA_CONFIG_DIR") or os.path.expanduser(os.path.join("~", ".config", "agora")))


def pack_dir():
    return os.environ.get("CYS_PACK_DIR") or os.path.join(os.path.expanduser("~"), ".cys", "pack")


def state_dir():
    v = os.environ.get("CYS_STATE_DIR") or ""
    return v if v.strip() else os.path.join(os.path.expanduser("~"), ".cys", "state")


def _counsel(cfg, name):
    return os.path.join(cfg, COUNSEL_DIR, name)


def _mkcounsel(cfg):
    d = os.path.join(cfg, COUNSEL_DIR)
    os.makedirs(d, mode=0o700, exist_ok=True)
    return d


def _first_line(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.readline().strip()
    except (OSError, ValueError):
        return None


def pack_version(pack=None):
    v = _first_line(os.path.join(pack or pack_dir(), ".pack-version"))
    return v if v and VERSION_RE.match(v) else None


def ms_iso(epoch):
    t = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (t.microsecond // 1000)


def os_tag():
    import platform
    if sys.platform == "darwin":
        base, ver = "macos", platform.mac_ver()[0]
    elif os.name == "nt":
        base, ver = "windows", platform.release()
    else:
        return "linux"
    tag = "%s-%s" % (base, ver) if ver else base
    return tag if OS_RE.match(tag) else base


# ── 끄기(agora collector.auto_enabled 와 같은 규칙) ─────────────────────────────
def auto_enabled(cfg):
    """config.json 없음 = 켬 · 못 읽음/객체 아님 = 끔 · counsel 없음 = 켬 · counsel 객체 아님 = 끔 · auto 없음 = 켬 · 그 밖 = 정확히 true 만 켬."""
    path = os.path.join(cfg, "config.json")
    if not os.path.exists(path):
        return True
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return False
    if type(doc) is not dict:
        return False
    if "counsel" not in doc:
        return True
    sec = doc["counsel"]
    if type(sec) is not dict:
        return False
    return sec.get("auto", True) is True


# ── 잠금(옆 파일 · 0번 바이트 · agora collector._FileLock 과 같은 수단) ─────────────
def _try_lock(fh):
    if os.name == "nt":
        import msvcrt
        try:
            fh.seek(0)   # ★매 시도 0번 바이트(아고라 _lock 과 같은 자리)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    import fcntl
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(fh):
    try:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


def _acquire(path, wait_s):
    """잡으면 열린 손잡이 · 상한 안에 못 잡으면 None(★잠금 파일에는 아무것도 쓰지 않는다)."""
    fh = open(path, "a+", encoding="utf-8")
    fh.seek(0)
    deadline = time.monotonic() + wait_s
    while True:
        if _try_lock(fh):
            return fh
        if time.monotonic() >= deadline:
            fh.close()
            return None
        time.sleep(LOCK_RETRY_S)


# ── 신호 ───────────────────────────────────────────────────────────────────
def map_source(value):
    """CYS_ROLE 값 또는 층 이름 → 계약 source(master·worker·cso·pack·update) — 모르는 것·빈 값 = pack."""
    v = (value or "").strip().lower()
    if v in ("master", "pack", "update"):
        return v
    if v == "cso" or v.startswith("cso-"):
        return "cso"
    for p in ("worker", "reviewer", "planner"):
        if v == p or v.startswith(p + "-"):
            return "worker"
    return "pack"


def make_row(source, op, error_code, *, now=None, version=None, os_name=None):
    """계약 한 줄(dict) · 형식 밖이면 None."""
    row = {"ts": ms_iso(time.time() if now is None else now), "source": map_source(source),
           "op": str(op or "").lower(), "error_code": str(error_code or "").lower(),
           "version": version if version is not None else pack_version(), "os": os_name or os_tag()}
    ok = (TS_RE.match(row["ts"]) and row["source"] in SIGNAL_SOURCES and type(row["version"]) is str
          and OP_RE.match(row["op"]) and ERROR_CODE_RE.match(row["error_code"])
          and VERSION_RE.match(row["version"]) and OS_RE.match(row["os"]))
    return row if ok else None


def serialize(row):
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def write_signals(source, pairs, *, now=None, cfg=None, wait_s=LOCK_WAIT_S):
    """(op, error_code) 여러 개를 잠금 1회로 append — 쓴 줄 수. 끔·판본 모름·잠금 초과·2MB 초과 = 그 줄 버림. 예외 0."""
    try:
        cfg = cfg or config_dir()
        if not auto_enabled(cfg):
            return 0
        version = pack_version()
        if version is None:
            return 0
        rows = [r for r in (make_row(source, op, code, now=now, version=version) for op, code in pairs) if r]
        if not rows:
            return 0
        _mkcounsel(cfg)
        fh = _acquire(_counsel(cfg, SIGNALS_LOCK), wait_s)
        if fh is None:
            return 0
        n = 0
        try:
            path = _counsel(cfg, SIGNALS_FILE)
            with open(path, "a", encoding="utf-8", newline="\n") as out:
                for row in rows:
                    size = os.path.getsize(path) if os.path.exists(path) else 0
                    if size > SIGNALS_MAX_BYTES:
                        break
                    out.write(serialize(row))   # 한 줄 = write 1회
                    out.flush()
                    n += 1
        finally:
            _unlock(fh)
            fh.close()
        return n
    except Exception:
        return 0


def write_signal(source, op, error_code, **kw):
    """in-process 호출자(preflight 등)용 한 줄 판 — 썼으면 True."""
    return write_signals(source, [(op, error_code)], **kw) == 1


# ── 로그 ───────────────────────────────────────────────────────────────────
def log_event(cfg, event, **fields):
    try:
        _mkcounsel(cfg)
        path = _counsel(cfg, TICK_LOG)
        if os.path.exists(path) and os.path.getsize(path) > LOG_MAX_BYTES:
            os.replace(path, path + ".1")
        row = dict(fields, ts=ms_iso(time.time()), event=event)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass


# ── 사실 수집 ─────────────────────────────────────────────────────────────────
def cys_bin():
    p = os.environ.get("CYS_CYS_BIN") or ""
    if p and os.path.isfile(p):
        return p
    return shutil.which("cys")


def _run(argv, timeout):
    """stdout(text) · 실행 실패·시간 초과 = None. (rc 는 호출측이 따로 본다)"""
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=timeout, **NOWIN)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None, None
    return r.returncode, r.stdout.decode("utf-8", errors="replace")


def probe_version():
    out = {}
    exe = cys_bin()
    if exe:
        rc, text = _run([exe, "--version"], CLI_TIMEOUT_S)
        if rc == 0 and text:
            for tok in text.split():
                if tok[:1].isdigit() and VERSION_RE.match(tok):
                    out["host"] = tok
                    break
    pv = pack_version()
    if pv:
        out["pack"] = pv
    return out or None


def seat_category(role):
    """좌석 역할 → 범주(★원 이름은 사용자·호스트 이름을 품을 수 있어 싣지 않는다):
    master · cso(cso·cso-*) · worker(worker·worker-*·reviewer*·planner*) · 그 밖(빈 값 포함) = pack."""
    v = (role or "").strip().lower()
    if v == "master":
        return "master"
    if v == "cso" or v.startswith("cso-"):
        return "cso"
    if v == "worker" or v.startswith(("worker-", "reviewer", "planner")):
        return "worker"
    return "pack"


def probe_seats():
    exe = cys_bin()
    if not exe:
        return None
    rc, text = _run([exe, "list"], CLI_TIMEOUT_S)
    if rc != 0 or text is None:
        return None
    count, roles = 0, set()
    for line in text.splitlines():
        m_role = re.search(r"(?:^|\s)role=(\S*)", line)
        if not m_role:
            continue
        m_ex = re.search(r"(?:^|\s)exited=(\S+)", line)
        if m_ex and m_ex.group(1).lower() == "true":
            continue
        count += 1
        roles.add(seat_category(m_role.group(1)))
    return {"count": count, "roles": sorted(roles)}


def _count_ok(v):
    return type(v) is int and 0 <= v <= 999


def probe_doctor():
    exe = cys_bin()
    if not exe:
        return None
    _rc, text = _run([exe, "doctor", "--json"], DOCTOR_TIMEOUT_S)   # FAIL 이 있으면 rc≠0 일 수 있다 — JSON 으로 판정
    if not text:
        return None
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    if type(doc) is not dict or type(doc.get("summary")) is not dict:
        return None
    s = doc["summary"]
    out = {k: s.get(k) for k in ("ok", "warn", "fail", "skip")}
    if not all(_count_ok(v) for v in out.values()):
        return None
    ids = {"WARN": set(), "FAIL": set()}
    for it in doc.get("items") or []:
        if type(it) is dict and it.get("status") in ids and type(it.get("name")) is str \
                and CHECK_ID_RE.match(it["name"]):
            ids[it["status"]].add(it["name"])
    out["warn_ids"] = sorted(ids["WARN"])[:MAX_LIST]
    out["fail_ids"] = sorted(ids["FAIL"])[:MAX_LIST]
    return out


def since_epoch(cfg, now):
    """`state.json` daily_ok_at(UTC 밀리초) · 없으면 지금−24h."""
    try:
        with open(_counsel(cfg, STATE_FILE), encoding="utf-8") as f:
            doc = json.load(f)
        v = doc.get("daily_ok_at") if type(doc) is dict else None
        if type(v) is str and TS_RE.match(v):
            t = datetime.datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
            return t.timestamp()
    except (OSError, ValueError):
        pass
    return now - 86400


def _count_after(paths, since, parse):
    """줄머리 시각이 since 보다 뒤인 줄 수 · 파일 없음 = 0 · 그 밖의 판독 실패 = None(못 잼)."""
    n = 0
    for p in paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    t = parse(line)
                    if t is not None and t > since:
                        n += 1
        except FileNotFoundError:
            continue
        except OSError:
            return None
    return n


def _local_head(line):
    # javis_dept_request._tick_log: `%Y-%m-%dT%H:%M:%S <msg>` (로컬 시각 · 오프셋 없음)
    try:
        return time.mktime(time.strptime(line[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def _utc_head(line):
    # _lib.sh cys_hook_fail: `%Y-%m-%dT%H:%M:%SZ <훅> …` (UTC · date 없으면 「시각불명」 = 못 잼)
    try:
        t = datetime.datetime.strptime(line[:20], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return t.replace(tzinfo=datetime.timezone.utc).timestamp()


def probe_errors(cfg, now):
    since = since_epoch(cfg, now)
    req = os.environ.get("CYS_DEPT_REQUESTS") or os.path.join(os.path.expanduser("~"), ".cys", "dept-requests")
    hook = os.path.join(state_dir(), "hook-errors.log")
    tick = _count_after([os.path.join(req, "tick-errors.log")], since, _local_head)
    hooks = _count_after([hook + ".1", hook], since, _utc_head)
    if tick is None or hooks is None:
        return None
    return {"tick_errors": tick, "hook_rc_nonzero": hooks}


def _tombstones_path():
    if os.name == "nt":
        la = os.environ.get("LOCALAPPDATA")
        return os.path.join(la, "cys", "dept_tombstones.json") if la else None
    return os.path.join(os.path.expanduser("~"), ".local", "state", "cys", "dept_tombstones.json")


def _json_len(path, key):
    """파일 없음 = 0 · `{key: dict|list}` 의 항목 수 · 그 밖 = None."""
    if path is None:
        return None
    try:
        with open(path, encoding="utf-8-sig") as f:
            doc = json.load(f)
    except FileNotFoundError:
        return 0
    except (OSError, ValueError):
        return None
    v = doc.get(key) if type(doc) is dict else None
    return len(v) if isinstance(v, (dict, list)) else None


def probe_depts():
    active = _json_len(os.environ.get("CYS_DEPTS_JSON") or os.path.join(os.path.expanduser("~"), ".cys", "depts.json"),
                       "depts")
    tomb = _json_len(_tombstones_path(), "dept_tombstones")
    if active is None or tomb is None:
        return None
    return {"active": active, "tombstones": tomb}


def probe_uptime(now):
    try:
        with open(os.path.join(state_dir(), "delivery-base.epoch.json"), encoding="utf-8") as f:
            doc = json.load(f)
        started = datetime.datetime.strptime(doc["started"], "%Y-%m-%dT%H:%M:%SZ")
    except (OSError, ValueError, KeyError, TypeError):
        return None
    t = started.replace(tzinfo=datetime.timezone.utc).timestamp()
    if t > now:
        return None
    return {"last_boot": ms_iso(t), "uptime_s": int(now - t)}


def collect_facts(cfg, now=None):
    now = time.time() if now is None else now
    facts = {}
    probes = (("version", probe_version), ("os", os_tag), ("seats", probe_seats), ("doctor", probe_doctor),
              ("errors", lambda: probe_errors(cfg, now)), ("depts", probe_depts), ("uptime", lambda: probe_uptime(now)))
    for key, fn in probes:
        try:
            v = fn()
        except Exception:
            v = None
        if v is not None:
            facts[key] = v
    return facts


def write_facts(cfg=None, now=None):
    cfg = cfg or config_dir()
    try:
        facts = collect_facts(cfg, now)
        _mkcounsel(cfg)
        path = _counsel(cfg, FACTS_FILE)
        tmp = "%s.tmp-%d-%s" % (path, os.getpid(), secrets.token_hex(4))
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(facts, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
        os.replace(tmp, path)
        return facts
    except Exception as e:
        log_event(cfg, "facts", result="error", why=type(e).__name__)
        return None


# ── 동봉 클라이언트 설치 ───────────────────────────────────────────────────────
def _read_pin(pack):
    """핀 한 줄 `<판본> <zip sha256> <zip 바이트> [<트리 지문>]` → dict · 없음/형식 밖 = None.
    ★3칸(옛 꼴)도 받는다 — 그때 지문은 None 이고 동봉 zip 에서 실행 때 잰다."""
    line = _first_line(os.path.join(pack, "install", "agora-client.pin"))
    if not line:
        return None
    p = line.split()
    if len(p) not in (3, 4) or not VERSION_RE.match(p[0]) or not SHA_RE.match(p[1]) or not p[2].isdigit():
        return None
    if len(p) == 4 and not SHA_RE.match(p[3]):
        return None
    return {"ver": p[0], "sha": p[1], "size": int(p[2]), "fp": p[3] if len(p) == 4 else None}


def _read_known(pack):
    """`install/agora-client-known.txt` → {트리 지문: 판본} · `#` 줄·형식 밖 줄은 건너뛴다 · 파일 없음 = {}."""
    out = {}
    try:
        with open(os.path.join(pack, "install", KNOWN_FILE), encoding="utf-8-sig") as f:
            for line in f:
                p = line.split()
                if len(p) == 2 and not p[0].startswith("#") and VERSION_RE.match(p[0]) and SHA_RE.match(p[1]):
                    out[p[1]] = p[0]
    except (OSError, ValueError):
        pass
    return out


def _safe_parts(name):
    """zip 항목 이름 → 경로 조각 · 절대경로·드라이브·`..` = None(zip-slip 거부)."""
    if not name or name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name):
        return None
    parts = [p for p in re.split(r"[\\/]+", name) if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return parts


# ── 트리 지문 — 「같은 판인가」는 `.pin` 글자가 아니라 **설치된 트리 내용**으로 판다 ─────────────
# 지문 = sha256( 정렬한 줄 `<posix 상대경로>\t<파일 바이트 sha256 hex>\n` 의 UTF-8 ) · 대상 = 일반 파일 전부
# · 뺌 = 맨 위 `.pin`(우리 표식) · `__pycache__/` 아래 · `*.pyc`(실행만 해도 생기는 것 — 사람 손이 아니다).
def _fp_skip(parts):
    return parts == [".pin"] or "__pycache__" in parts or parts[-1].endswith(".pyc")


def _fp_digest(rows):
    text = "".join(sorted("%s\t%s\n" % (rel, h) for rel, h in rows.items()))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_fingerprint(root):
    """폴더 트리 지문(링크는 따라가지 않는다 · 일반 파일 아닌 것은 빼서 지문이 달라진다 = 고친 트리)."""
    rows = {}
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for name in files:
            p = os.path.join(d, name)
            if not stat.S_ISREG(os.lstat(p).st_mode):
                continue
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if not _fp_skip(rel.split("/")):
                rows[rel] = _sha_file(p)
    return _fp_digest(rows)


def zip_fingerprint(data):
    """zip 항목으로 잰 지문 — 그 zip 을 `_extract` 로 푼 트리의 `tree_fingerprint` 와 같다(같은 이름은 뒤 항목이 이긴다)."""
    rows = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            parts = _safe_parts(info.filename)
            if parts is None:
                raise ValueError("zip-slip:%s" % info.filename[:80])
            if not parts or info.is_dir() or _fp_skip(parts):
                continue
            rows["/".join(parts)] = hashlib.sha256(zf.read(info)).hexdigest()
    return _fp_digest(rows)


def _extract(data, dest):
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        infos = zf.infolist()
        plan = []
        for info in infos:
            parts = _safe_parts(info.filename)
            if parts is None:
                raise ValueError("zip-slip:%s" % info.filename[:80])
            plan.append((info, parts))
        root = os.path.realpath(dest)
        for info, parts in plan:
            if not parts:
                continue
            target = os.path.join(dest, *parts)
            if not os.path.realpath(target).startswith(root + os.sep):
                raise ValueError("zip-slip:%s" % info.filename[:80])
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


_NOREPLACE = []


def _noreplace_fn():
    """POSIX 의 「있으면 실패」 rename(맥 renamex_np RENAME_EXCL · 리눅스 renameat2 RENAME_NOREPLACE) · 없으면 None."""
    if not _NOREPLACE:
        fn = None
        try:
            import ctypes
            libc = ctypes.CDLL(None, use_errno=True)
            if sys.platform == "darwin":
                f = libc.renamex_np
                f.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
                fn = lambda a, b: f(a, b, 0x4)                       # RENAME_EXCL
            elif hasattr(libc, "renameat2"):
                f = libc.renameat2
                f.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
                fn = lambda a, b: f(-100, a, -100, b, 1)             # AT_FDCWD · RENAME_NOREPLACE
        except Exception:
            fn = None
        _NOREPLACE.append(fn)
    return _NOREPLACE[0]


def _rename_noreplace(src, dst):
    """`dst` 가 있으면(빈 폴더라도) FileExistsError — ★POSIX `rename` 은 빈 폴더를 조용히 덮는다.
    윈 `os.rename`(MoveFileEx · 덮어쓰기 플래그 없음)은 원래 있으면 실패한다."""
    if os.name != "nt":
        fn = _noreplace_fn()
        if fn is not None:
            import ctypes
            if fn(os.fsencode(src), os.fsencode(dst)) == 0:
                return
            err = ctypes.get_errno()
            if err in (errno.EEXIST, errno.ENOTEMPTY):
                raise FileExistsError(err, os.strerror(err), dst)
            if err not in (errno.ENOSYS, errno.EINVAL, getattr(errno, "ENOTSUP", -1), getattr(errno, "EOPNOTSUPP", -1)):
                raise OSError(err, os.strerror(err), dst)
        if os.path.lexists(dst):   # 수단 없는 판(옛 libc · 지원 안 하는 파일 시스템) = 확인 뒤 rename
            raise FileExistsError(errno.EEXIST, "exists", dst)
    os.rename(src, dst)


def _sweep(cfg):
    """끊긴 판의 찌꺼기(`lib.tmp-*` · `lib.old-*`) — 설치 잠금 안에서만 부른다(그 이름은 잠금 쥔 우리만 만든다)."""
    try:
        names = os.listdir(cfg)
    except OSError:
        return
    for n in names:
        if n.startswith(("lib.tmp-", "lib.old-")):
            shutil.rmtree(os.path.join(cfg, n), ignore_errors=True)


def _blob_bytes(blob, pin):
    """동봉 b64 → zip 바이트 · 핀 sha·바이트와 다르면 None."""
    with open(blob, encoding="ascii") as f:
        data = base64.b64decode("".join(f.read().split()), validate=True)
    if len(data) != pin["size"] or hashlib.sha256(data).hexdigest() != pin["sha"]:
        return None
    return data


def ensure_client(cfg=None, pack=None, wait_s=INSTALL_LOCK_WAIT_S):
    """결과 문자열(시험용) — no-pin · same · foreign · installed · replaced · refused · busy · raced · error.
    ★설치 잠금(`<설정>/lib.install.lock`)을 존재 판정부터 게시까지 쥔다 · 잠금 안에서 다시 판다 · 남의 `lib` 위로 rename 0."""
    cfg = cfg or config_dir()
    pack = pack or pack_dir()
    try:
        pin = _read_pin(pack)
        if pin is None:
            return "no-pin"
        blob = os.path.join(pack, "install", "agora-client-%s.zip.b64" % pin["ver"])
        if not os.path.isfile(blob):
            return "no-pin"
        os.makedirs(cfg, mode=0o700, exist_ok=True)
        fh = _acquire(os.path.join(cfg, INSTALL_LOCK), wait_s)
        if fh is None:
            log_event(cfg, "ensure-client", result="busy", why="install lock held", want=pin["ver"])
            return "busy"
        try:
            return _ensure_locked(cfg, pack, pin, blob)
        except ValueError as e:            # zip-slip · 깨진 b64/zip(지문 재는 자리) = 거부
            return _refused(cfg, pin["ver"], str(e)[:120])
        finally:
            _unlock(fh)
            fh.close()
    except Exception as e:
        log_event(cfg, "ensure-client", result="error", why=type(e).__name__)
        return "error"


def _refused(cfg, ver, why, **kw):
    log_event(cfg, "ensure-client", result="refused", why=why, want=ver, **kw)
    return "refused"


def _ensure_locked(cfg, pack, pin, blob):
    ver = pin["ver"]
    lib = os.path.join(cfg, "lib")
    _sweep(cfg)
    data = None
    want = pin["fp"]
    if want is None:                       # 3칸 핀 — 지문을 동봉 zip 에서 잰다
        data = _blob_bytes(blob, pin)
        if data is None:
            return _refused(cfg, ver, "pin mismatch")
        want = zip_fingerprint(data)
    replace_from = None
    if os.path.lexists(lib):
        if os.path.islink(lib) or not os.path.isdir(lib):
            log_event(cfg, "ensure-client", result="foreign", why="lib is not a directory", want=ver)
            return "foreign"
        have = tree_fingerprint(lib)
        if have == want:
            return "same"
        replace_from = _read_known(pack).get(have)
        if replace_from is None:
            log_event(cfg, "ensure-client", result="foreign", why="modified or unknown client", want=ver,
                      have_fp=have[:16])
            return "foreign"
    if data is None:
        data = _blob_bytes(blob, pin)
        if data is None:
            return _refused(cfg, ver, "pin mismatch")
    if zip_fingerprint(data) != want:
        return _refused(cfg, ver, "pin fingerprint mismatch")
    tmp = os.path.join(cfg, "lib.tmp-%s" % secrets.token_hex(4))
    old = None
    try:
        os.makedirs(tmp)
        _extract(data, tmp)
        if tree_fingerprint(tmp) != want:
            raise ValueError("unpacked fingerprint mismatch")
        with open(os.path.join(tmp, ".pin"), "w", encoding="utf-8", newline="\n") as f:
            f.write("%s %s %d %s\n" % (ver, pin["sha"], pin["size"], want))
        if replace_from is not None:       # 옛 판은 옆으로 → 새 판 게시 → 옛 판 삭제(사이에 끊기면 lib 없음 = 다음 판이 새로 깐다)
            old = os.path.join(cfg, "lib.old-%s" % secrets.token_hex(4))
            _rename_noreplace(lib, old)
        _rename_noreplace(tmp, lib)
    except ValueError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return _refused(cfg, ver, str(e)[:120])
    except FileExistsError:
        shutil.rmtree(tmp, ignore_errors=True)
        if old:
            shutil.rmtree(old, ignore_errors=True)
        log_event(cfg, "ensure-client", result="raced", why="lib appeared meanwhile", want=ver)
        return "raced"
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    if old:
        shutil.rmtree(old, ignore_errors=True)
        log_event(cfg, "ensure-client", result="replaced", version=ver, was=replace_from)
        return "replaced"
    log_event(cfg, "ensure-client", result="installed", version=ver)
    return "installed"


# ── 틱 ─────────────────────────────────────────────────────────────────────
def _read_state(cfg):
    try:
        with open(_counsel(cfg, STATE_FILE), encoding="utf-8") as f:
            doc = json.load(f)
        return doc if type(doc) is dict else {}
    except (OSError, ValueError):
        return {}


def _daily_due(cfg, now=None):
    """일일 사실이 필요한 판인가 — 꺼짐이면 아니다(doctor·좌석 조회 0) · 그날(06:00 KST 경계) 일일이 끝났고 pending 이 없으면 아니다.
    ★날짜 경계 = 아고라 `counsel.day_of` 와 같은 선(KST 06:00) · 판정 재료 = state.json 의 `daily_day`·`daily_pending`(아고라가 쓴다)."""
    if not auto_enabled(cfg):
        return False
    now = now or datetime.datetime.now(datetime.timezone.utc)
    today = (now + datetime.timedelta(hours=9) - datetime.timedelta(hours=6)).date().isoformat()
    st = _read_state(cfg)
    return not (st.get("daily_day") == today and not st.get("daily_pending"))


def agora_timeout(elapsed):
    """agora 에 줄 시간 = 한 판 상한(540초) − 지금까지 쓴 시간 · 바닥 30초."""
    return max(AGORA_MIN_TIMEOUT_S, int(TICK_CAP_S - elapsed))


def _kill_group(proc):
    """시간 초과 자식을 **자손째** 끝낸다 — POSIX = 새 세션의 프로세스 그룹 killpg · 윈 = taskkill /T /F. 쓴 수단 이름."""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, **NOWIN)
            how = "taskkill"
        except (OSError, subprocess.SubprocessError):
            how = "kill"
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)   # start_new_session → 그룹 id = 자식 pid
            how = "killpg"
        except OSError:
            how = "kill"
    try:
        proc.kill()
    except OSError:
        pass
    return how


def tick(cfg=None):
    t0 = time.monotonic()
    cfg = cfg or config_dir()
    ensure_client(cfg)
    if _daily_due(cfg):
        write_facts(cfg)
    agora = os.path.join(cfg, "lib", "bin", "agora")
    if not os.path.isfile(agora):
        log_event(cfg, "tick", result="no-client")
        return "no-client"
    env = dict(os.environ)
    key = os.path.join(cfg, "id_ed25519")
    if not env.get("AGORA_SIGNING_KEY") and os.path.isfile(key):
        env["AGORA_SIGNING_KEY"] = key
    argv = [sys.executable, agora, "counsel", "auto", "--facts", _counsel(cfg, FACTS_FILE)]
    timeout = agora_timeout(time.monotonic() - t0)
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, start_new_session=(os.name != "nt"), **NOWIN)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        log_event(cfg, "tick", result="error", why=type(e).__name__)
        return "error"
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        how = _kill_group(proc)
        try:
            proc.communicate(timeout=10)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
        log_event(cfg, "tick", result="timeout", timeout_s=timeout, killed=how)
        return "timeout"
    tail = (out or b"").decode("utf-8", errors="replace").strip()[-300:]
    err = (err or b"").decode("utf-8", errors="replace").strip()[-300:]
    log_event(cfg, "tick", result="ran", rc=proc.returncode, out=tail, err=err)
    return "ran"


# ── CLI ────────────────────────────────────────────────────────────────────
def _arg(argv, name):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def main(argv=None):
    """언제나 0 — 인자 오류도 조용히 무동작."""
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        verb = argv[0] if argv else ""
        if verb == "signal":
            write_signal(_arg(argv, "--source") or "", _arg(argv, "--op") or "", _arg(argv, "--error-code") or "")
        elif verb == "facts":
            write_facts()
        elif verb == "ensure-client":
            ensure_client()
        elif verb == "tick":
            tick()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
