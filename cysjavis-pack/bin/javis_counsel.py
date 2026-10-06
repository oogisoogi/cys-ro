#!/usr/bin/env python3
"""javis_counsel.py — 상담소 자동 전달의 팩 쪽(TICKET=agora-t3-pack-collector).

참가자 PC 의 agora 클라이언트(`agora counsel auto`)가 읽을 재료를 **팩이** 만든다 — 신호 줄 쓰기 · 일일 사실 수집 ·
동봉 클라이언트 설치 · 30분 틱. 읽고 보내는 쪽은 agora(`agora/collector.py`)다. 두 쪽 계약(정규식·잠금·끄기 규칙)은
글자 그대로 같아야 한다 — 한쪽만 넓으면 한쪽이 버린 줄을 다른 쪽이 보낸다.

동사:
  signal --source <역할|층> --op <op> --error-code <code>   신호 한 줄 append(형식 밖·끔·잠금 2초 초과 = 버림)
  facts          결정론 일일 사실 → `<설정>/counsel/facts.json`(원자 교체 · 못 잰 칸은 뺀다 · null 0)
  ensure-client  `<팩>/install/agora-client.pin` + `.zip.b64` → `<설정>/lib`(없을 때만 · 남의 lib 불가침)
  tick           ensure-client → facts → `agora counsel auto --facts …`(스케줄 잡 `agora-counsel` · 30분)

★언제나 exit 0 · stdout 무출력 — 훅·preflight·cys-dept·Rust 업데이트 경로가 부르므로 이 도구의 실패가 호출자를 바꾸면
  안 된다. 결과는 `<설정>/counsel/tick.log`(JSON 줄 · 256KB 넘으면 `.1`)에만 남긴다.
<설정> = `$AGORA_CONFIG_DIR` 또는 `~/.config/agora`(agora participant.config_dir 와 같은 규칙).
"""
import base64
import datetime
import hashlib
import io
import json
import os
import re
import secrets
import shutil
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
ROLE_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}\Z", re.ASCII)
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
AGORA_TIMEOUT_S = 900
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
        if ROLE_RE.match(m_role.group(1)):
            roles.add(m_role.group(1))
    return {"count": count, "roles": sorted(roles)[:MAX_LIST]}


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
    """핀 한 줄 `<판본> <sha256> <바이트>` → (줄, 판본, sha, 바이트) · 없음/형식 밖 = None."""
    line = _first_line(os.path.join(pack, "install", "agora-client.pin"))
    if not line:
        return None
    parts = line.split()
    if len(parts) != 3 or not VERSION_RE.match(parts[0]) or not SHA_RE.match(parts[1]) or not parts[2].isdigit():
        return None
    return " ".join(parts), parts[0], parts[1], int(parts[2])


def _safe_parts(name):
    """zip 항목 이름 → 경로 조각 · 절대경로·드라이브·`..` = None(zip-slip 거부)."""
    if not name or name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name):
        return None
    parts = [p for p in re.split(r"[\\/]+", name) if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return parts


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


def ensure_client(cfg=None, pack=None):
    """결과 문자열(시험용) — no-pin · same · foreign · installed · refused · error."""
    cfg = cfg or config_dir()
    pack = pack or pack_dir()
    try:
        pin = _read_pin(pack)
        if pin is None:
            return "no-pin"
        line, ver, sha, size = pin
        blob = os.path.join(pack, "install", "agora-client-%s.zip.b64" % ver)
        if not os.path.isfile(blob):
            return "no-pin"
        lib = os.path.join(cfg, "lib")
        if os.path.lexists(lib):
            if _first_line(os.path.join(lib, ".pin")) == line:
                return "same"
            log_event(cfg, "ensure-client", result="foreign", why="foreign client", want=ver)
            return "foreign"
        with open(blob, encoding="ascii") as f:
            data = base64.b64decode("".join(f.read().split()), validate=True)
        got = hashlib.sha256(data).hexdigest()
        if len(data) != size or got != sha:
            log_event(cfg, "ensure-client", result="refused", why="pin mismatch", want=ver, bytes=len(data))
            return "refused"
        os.makedirs(cfg, mode=0o700, exist_ok=True)
        tmp = os.path.join(cfg, "lib.tmp-%s" % secrets.token_hex(4))
        try:
            os.makedirs(tmp)
            _extract(data, tmp)
            with open(os.path.join(tmp, ".pin"), "w", encoding="utf-8", newline="\n") as f:
                f.write(line + "\n")
            os.rename(tmp, lib)
        except ValueError as e:
            shutil.rmtree(tmp, ignore_errors=True)
            log_event(cfg, "ensure-client", result="refused", why=str(e)[:120], want=ver)
            return "refused"
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        log_event(cfg, "ensure-client", result="installed", version=ver)
        return "installed"
    except Exception as e:
        log_event(cfg, "ensure-client", result="error", why=type(e).__name__)
        return "error"


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


def tick(cfg=None):
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
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env=env, timeout=AGORA_TIMEOUT_S, **NOWIN)
    except subprocess.TimeoutExpired:
        log_event(cfg, "tick", result="timeout", timeout_s=AGORA_TIMEOUT_S)
        return "timeout"
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        log_event(cfg, "tick", result="error", why=type(e).__name__)
        return "error"
    tail = (r.stdout or b"").decode("utf-8", errors="replace").strip()[-300:]
    err = (r.stderr or b"").decode("utf-8", errors="replace").strip()[-300:]
    log_event(cfg, "tick", result="ran", rc=r.returncode, out=tail, err=err)
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
