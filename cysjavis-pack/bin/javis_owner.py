#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""javis_owner — 오너 책상(한 번 시킨 것은 잊지 않고, 시킨 일은 밀리지 않게 · TICKET=cysr-owner-memory-todo-1118).

왜 있는가(11-18 워크숍 참가자 사용기): ① 한 번 시킨 것(깔끔한 화면 · 끝나면 알림)을 자꾸 까먹는다 ② 아침에 여러 일을
시키면 쌓여 일주일째 밀린다. 대화 속 지시는 그 대화 기억에만 있어 요약·순환·재시작 뒤 사라지고, 오너가 시킨 일을
적는 원장도 아침 보고 장치도 없었다. 이 도구가 셋을 결정론으로 맡는다 — 모델은 「무엇이 지속 지시인가 · 무엇이 일인가」
뜻만 판단하고, 저장·개수·날짜·보고 시점·알림 1회는 기계가 한다.

  rule add --text "<지시>"          오래 지킬 지시 저장(장기기억 javis_memory · feedback_owner-rule-*.md) → say 1줄
  rule list [--json]                 지금 기억하는 오너 규칙 목록(번호)
  rule remove <번호|슬러그>          은퇴(javis_memory retire — 물리 삭제 아님) → say 1줄
  todo add --what "<일>" [--what …] [--urgent N…] [--short N…] [--notify]   받은 일 원장 1줄(여럿이면 순서 1줄)
  todo done <id> --evidence "<근거>" 끝 표시 → 알림 켜져 있으면 그 자리에서 앱 알림(실패하면 다음 훅에서 재시도 · 중복 0)
  todo keep|defer|cancel <id> …      사흘 넘은 일에 대한 오너 답(계속 / 미룸 / 취소)
  todo list [--all] [--json] · todo brief [--json]   밀린 일 n건 · 가장 오래된 것 · 물어볼 일
  notify set --channel app|phone|both|off [--all-done on|off] [--selfcheck on|off] · notify status
  hook auto|session|prompt|stop|posttool  Claude Code 훅 본체(stdin = 훅 JSON · stdout = 훅 JSON 또는 무출력 · 늘 exit 0)

저장 위치: 규칙 = 팩 장기기억 폴더(javis_memory 와 같은 곳 · 새 저장소 없음) · 원장·설정·턴 표지 = ${CYS_OWNER_DIR:-~/.cys/owner}
(파일은 오너 기기 안에만 둔다 · 단 규칙·할 일 제목·직전 오너 입력 발췌는 모델 문맥으로, 끝 알림 제목은 폰 푸시로 전달된다).
의존성: 파이썬 표준 라이브러리 + 같은 bin 의 javis_memory(하위 프로세스) · javis_mission(기계 입력 판별 · 없으면 라벨 폴백).
"""

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
import time

_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
if _SELF_DIR not in sys.path:
    sys.path.append(_SELF_DIR)

RULE_PREFIX = "owner-rule-"
RULE_TYPE = "feedback"
STALE_DAYS = 3                 # 「사흘 넘은」 = 받은 날(또는 「계속」 답한 날)부터 3일 초과
SAVED_MARK = "이렇게 저장했습니다"
REMOVED_MARK = "이렇게 지웠습니다"
BRIEF_MARK = "밀린 일"
VALID_CHANNELS = ("app", "phone", "both", "off")
HOOK_EVENTS = {"SessionStart": "session", "UserPromptSubmit": "prompt", "Stop": "stop", "PostToolUse": "posttool"}
# 윈 무콘솔 세대: 캡처 하위 프로세스는 콘솔 창을 띄우지 않고(CREATE_NO_WINDOW) stdin 을 명시한다(WinError 6 방지 ·
#   팩 계약 tests/test_nowin_captured_spawns.py · test_dept_tick_stdin.py).
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}
MAX_BLOCKS = 2                 # 한 오너 턴에서 Stop 훅이 막는 최대 횟수(고리 방지)
HOOK_JSON_CAP = 9500           # 훅 출력 상한(하네스 10,000자 · 직렬화 뒤 길이로 잰다)
ITEM_CAP = 120                 # 목록 항목(규칙·일 제목) 표시 상한
MAX_ASKS = 5                   # 한 번에 묻는 사흘 넘은 일 수
APP_CLAIM_STALE = 60           # 앱 알림 「보내는 중」 표지가 이보다 오래면 재시도(보내다 죽은 경우)
PHONE_REMINDERS = 2            # 폰 알림 미발송을 다음 오너 턴에 다시 일러 주는 최대 횟수(그 뒤 포기 기록)
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


# ── 경로·시각·공통 ────────────────────────────────────────────────────────────
def owner_dir():
    d = os.environ.get("CYS_OWNER_DIR") or os.path.join(os.path.expanduser("~"), ".cys", "owner")
    os.makedirs(d, exist_ok=True)
    return d


def memory_dir():
    for key in ("CYS_PACK_DIR", "JAVIS_PACK_DIR", "AITERM_PACK_DIR", "AITERM_JARVIS_DIR"):
        v = os.environ.get(key, "")
        if v:
            return os.path.join(v, "memory")
    return os.path.join(os.path.expanduser("~"), ".cys", "pack", "memory")


def today():
    """오늘(로컬 날짜) — 시험은 CYS_OWNER_TODAY=YYYY-MM-DD 로 고정한다."""
    v = os.environ.get("CYS_OWNER_TODAY", "")
    if v:
        return _dt.date.fromisoformat(v)
    return _dt.date.today()


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def surface():
    return os.environ.get("CYS_SURFACE_ID") or os.environ.get("AITERM_SURFACE_ID") or "-"


def clean(s, cap=None):
    """한 줄 정리 — 제어 문자 제거(직렬화 때 \\uXXXX 로 6배 부푸는 것 방지) · 공백 접기 · 상한."""
    s = " ".join(_CTRL.sub(" ", s or "").split())
    if cap and len(s) > cap:
        s = s[:cap - 1] + "…"
    return s


def _atomic_write(path, text):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".swap")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class Lock:
    """O_CREAT|O_EXCL 잠금(javis_memory.FileLock 과 같은 규약 · posix·windows 공통)."""

    def __init__(self, target, timeout=5.0, stale=30.0):
        self.path = target + ".lock"
        self.timeout, self.stale, self.fd = timeout, stale, None

    def __enter__(self):
        deadline = time.time() + self.timeout
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > self.stale:
                        os.unlink(self.path)
                        continue
                except OSError:
                    pass
                if time.time() > deadline:
                    raise TimeoutError("잠금 획득 실패: %s" % self.path)
                time.sleep(0.05)

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
        try:
            os.unlink(self.path)
        except OSError:
            pass
        return False


def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _update_json(path, default, fn):
    """잠금 안에서 최신 값을 읽어 고친 뒤 원자 교체(읽기-수정-쓰기 경합으로 남의 변경을 지우지 않게)."""
    with Lock(path):
        data = _load_json(path, default)
        res = fn(data)
        _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    return res


def log_event(op, **kw):
    """턴 대조용 사건 원장(append 전용 · 잠금 아래 1줄) — Stop 검사가 「이번 턴에 저장했는가」를 이것으로 잰다."""
    rec = {"ts": time.time(), "at": now_iso(), "surface": surface(), "op": op}
    rec.update(kw)
    path = os.path.join(owner_dir(), "events.jsonl")
    with Lock(path):
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def events_since(ts, surf=None):
    out = []
    try:
        with open(os.path.join(owner_dir(), "events.jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("ts", 0) >= ts and (surf is None or e.get("surface") == surf):
                    out.append(e)
    except OSError:
        pass
    return out


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False))


# ── 설정 ─────────────────────────────────────────────────────────────────────
CONFIG_DEFAULTS = {"notify_channel": "both",   # 기본 = 앱 안 알림 + 폰/바탕화면(PushNotification)
                   "notify_all_done": False,   # 「일이 끝나면 늘 알려 줘」 지속 지시 = True
                   "selfcheck": True}          # 다시 보기 — 기록 0건 오너 턴을 다음 턴에 한 번 더 점검시킨다


def _config_path():
    return os.path.join(owner_dir(), "config.json")


def config():
    c = _load_json(_config_path(), {})
    for k, v in CONFIG_DEFAULTS.items():
        c.setdefault(k, v)
    return c


def update_config(changes):
    def f(c):
        c.update(changes)
        for k, v in CONFIG_DEFAULTS.items():
            c.setdefault(k, v)
        return dict(c)
    return _update_json(_config_path(), {}, f)


# ── ① 오래 지킬 지시(규칙) ─────────────────────────────────────────────────────
def _parse_rule_file(path):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    head, body = text[3:end], text[end + 4:]
    meta = {}
    for ln in head.splitlines():
        s = ln.strip()
        for k in ("name", "description"):
            if s.startswith(k + ":"):
                meta[k] = s[len(k) + 1:].strip()
    if not meta.get("name"):
        return None
    saved = ""
    for ln in body.splitlines():
        if ln.startswith("받은 날:"):
            saved = ln.split(":", 1)[1].strip()
    return {"slug": meta["name"], "text": meta.get("description", ""), "saved": saved,
            "file": os.path.basename(path)}


def list_rules():
    d = memory_dir()
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return []
    rules = []
    for n in names:
        if n.startswith("%s_%s" % (RULE_TYPE, RULE_PREFIX)) and n.endswith(".md"):
            r = _parse_rule_file(os.path.join(d, n))
            if r:
                try:
                    r["_m"] = os.stat(os.path.join(d, n)).st_mtime_ns
                except OSError:
                    r["_m"] = 0
                rules.append(r)
    rules.sort(key=lambda r: (r["saved"], r.pop("_m"), r["slug"]))   # 같은 날은 저장한 순서
    for i, r in enumerate(rules, 1):
        r["no"] = i
    return rules


def _memory_tool(*args):
    """javis_memory 하위 프로세스 — 자식·부모 모두 UTF-8 로 고정(한국어 윈의 파이프 기본 cp949 와 엇갈리지 않게)."""
    tool = os.path.join(_SELF_DIR, "javis_memory.py")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, tool, "--dir", memory_dir()] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
                       env=env, stdin=subprocess.DEVNULL, **NOWIN)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def rule_add(text):
    text = clean(text)
    if not text:
        return {"ok": False, "say": "저장할 지시 내용이 비어 있어요. 어떤 것을 앞으로 지키면 될지 한 줄로 알려 주세요."}
    for r in list_rules():
        if r["text"] == text:
            # 같은 지시를 다시 받음 = 저장 확인이다(Stop 대조가 이것을 근거로 인정한다).
            log_event("rule.add", slug=r["slug"], text=text, duplicate=True)
            return {"ok": True, "duplicate": True, "slug": r["slug"],
                    "say": "%s: 「%s」 (이미 %d번으로 기억하고 있어요)" % (SAVED_MARK, text, r["no"])}
    stamp = time.strftime("%Y%m%d%H%M%S")
    slug = "%s%s-%s" % (RULE_PREFIX, stamp, hashlib.sha256(text.encode("utf-8")).hexdigest()[:6])
    body = "오너(사용자)가 앞으로 계속 지켜 달라고 한 지시다.\n\n지시: %s\n받은 날: %s\n" % (
        text, today().isoformat())
    rc, out, err = _memory_tool("add", "--type", RULE_TYPE, "--name", slug, "--desc", text, "--body", body)
    if rc != 0:
        return {"ok": False, "rc": rc, "error": err[-300:],
                "say": "지시를 저장하지 못했어요(장기기억 도구 오류). 잠시 뒤 다시 해 볼게요."}
    log_event("rule.add", slug=slug, text=text)
    return {"ok": True, "slug": slug, "say": "%s: 「%s」 — 다음 대화에서도 이대로 지킬게요." % (SAVED_MARK, text)}


def rule_remove(key):
    hit = None
    for r in list_rules():
        if str(r["no"]) == str(key) or r["slug"] == key:
            hit = r
    if hit is None:
        return {"ok": False, "say": "그 번호의 규칙을 찾지 못했어요. 「기억하는 규칙 보여 줘」로 번호를 먼저 확인해 주세요."}
    rc, out, err = _memory_tool("retire", "--name", hit["slug"], "--reason", "오너 요청으로 지움")
    if rc != 0:
        return {"ok": False, "rc": rc, "error": err[-300:], "say": "규칙을 지우지 못했어요(장기기억 도구 오류)."}
    log_event("rule.remove", slug=hit["slug"], text=hit["text"])
    return {"ok": True, "slug": hit["slug"], "say": "%s: 「%s」 — 이제 이 지시는 따르지 않아요." % (REMOVED_MARK, hit["text"])}


def rules_say(rules):
    if not rules:
        return "지금 기억하고 있는 오래 지킬 지시는 없어요."
    lines = ["지금 기억하고 있는 지시 %d개예요:" % len(rules)]
    lines += ["%d. %s (받은 날 %s)" % (r["no"], r["text"], r["saved"] or "?") for r in rules]
    return "\n".join(lines)


# ── ② 오너 할 일 원장 ─────────────────────────────────────────────────────────
def _todo_path():
    return os.path.join(owner_dir(), "todo.json")


def load_todos():
    return _load_json(_todo_path(), {"next_id": 1, "items": []})


def _mutate(fn):
    return _update_json(_todo_path(), {"next_id": 1, "items": []}, fn)


def is_open(it):
    return it.get("status") == "open"


def age_days(it, t=None):
    return ((t or today()) - _dt.date.fromisoformat(it["received"])).days


def should_ask(it, t):
    """사흘 넘은 일인가 — 미룸이 걸려 있으면 미룬 날이 되면 묻고, 아니면 받은 날(또는 「계속」 답한 날)부터 3일 초과."""
    du = it.get("deferred_until")
    if du:
        return t >= _dt.date.fromisoformat(du)
    anchor = max(_dt.date.fromisoformat(c) for c in (it.get("received"), it.get("kept_on")) if c)
    return (t - anchor).days > STALE_DAYS


def todo_add(whats, urgent=(), short=(), notify=False):
    whats = [clean(w) for w in whats if clean(w)]
    if not whats:
        return {"ok": False, "say": "적을 일이 비어 있어요."}
    t = today().isoformat()

    def f(data):
        made = []
        for i, w in enumerate(whats, 1):
            it = {"id": data["next_id"], "what": w, "received": t, "received_at": now_iso(),
                  "status": "open", "urgent": i in urgent, "short": i in short, "notify": bool(notify)}
            data["next_id"] += 1
            data["items"].append(it)
            made.append(it)
        return made

    made = _mutate(f)
    for it in made:
        log_event("todo.add", id=it["id"], what=it["what"])
    if len(made) == 1:
        say = "할 일로 적었어요: #%d %s" % (made[0]["id"], made[0]["what"])
    else:
        order = sorted(made, key=lambda x: (not x["urgent"], not x["short"], x["id"]))
        say = "할 일 %d건을 적었고, 이 순서로 할게요: %s" % (
            len(made), " → ".join("#%d %s" % (x["id"], x["what"]) for x in order))
    if notify:
        say += " (끝나면 알려 드릴게요)"
    return {"ok": True, "ids": [x["id"] for x in made], "say": say}


def _find(data, tid):
    for it in data["items"]:
        if str(it["id"]) == str(tid):
            return it
    return None


def _push_message(it):
    return "끝났어요: %s (#%d)" % (clean(it["what"], 60), it["id"])


def todo_done(tid, evidence):
    evidence = clean(evidence)
    if not evidence:
        return {"ok": False, "say": "끝 표시에는 근거 한 줄이 필요해요(무엇을 했는지)."}
    c = config()
    holder = {}

    def f(data):
        it = _find(data, tid)
        if it is None:
            return None
        if it["status"] == "done":
            holder["already"] = True
            return dict(it)
        it.update(status="done", done_at=now_iso(), done_on=today().isoformat(), evidence=evidence)
        # 알림 의무는 끝 표시와 **같은 잠금 안에서** 원장에 박는다 — 발송이 실패해도 의무는 남아 다음 훅이 재시도한다.
        if (it.get("notify") or c["notify_all_done"]) and c["notify_channel"] != "off":
            ch = c["notify_channel"]
            it["notice"] = {"event": "done-%d-%s" % (it["id"], it["done_at"]), "channel": ch,
                            "app": "pending" if ch in ("app", "both") else None,
                            "phone": "pending" if ch in ("phone", "both") else None,
                            "message": _push_message(it), "phone_reminders": 0}
        return dict(it)

    it = _mutate(f)
    if it is None:
        return {"ok": False, "say": "#%s 번 일을 원장에서 찾지 못했어요." % tid}
    if holder.get("already"):
        return {"ok": True, "already": True, "say": "#%d 은 이미 끝 표시가 돼 있어요." % it["id"]}
    log_event("todo.done", id=it["id"], what=it["what"])
    res = {"ok": True, "id": it["id"], "say": "끝냈어요: #%d %s — %s" % (it["id"], it["what"], it["evidence"])}
    n = it.get("notice")
    if n:
        res["notify"] = {"channel": n["channel"], "app": flush_app_notices().get(it["id"])}
        if n.get("phone"):
            res["notify"]["phone_pending"] = True
            # 모델이 이 JSON 을 읽는 그 자리에서 보내게 한다(안 보내면 Stop 훅이 막는다).
            res["do_now"] = ("이어서 PushNotification 도구로 「%s」를 보내라(끝의 (#번호)를 그대로 — 기계가 그 번호로 "
                             "보냄을 확인한다). 오너가 이 화면을 보고 있으면 Claude Code 가 알아서 생략한다(그래도 이 호출은 "
                             "한다). 보내기 전에 「폰 알림을 보냈다」고 말하지 마라." % n["message"])
    return res


def todo_answer(tid, kind, days=None, reason=""):
    def f(data):
        it = _find(data, tid)
        if it is None or it["status"] != "open":
            return None
        t = today()
        if kind == "keep":                     # 「계속」 = 지금부터 다시 센다(미룸이 걸려 있었으면 푼다)
            it["kept_on"] = t.isoformat()
            it.pop("deferred_until", None)
        elif kind == "defer":                  # 「미룸」 = 그날이 되면 다시 묻는다
            it["deferred_until"] = (t + _dt.timedelta(days=days or 7)).isoformat()
        elif kind == "cancel":
            it.update(status="cancelled", cancelled_on=t.isoformat(), cancel_reason=clean(reason))
        return dict(it)

    it = _mutate(f)
    if it is None:
        return {"ok": False, "say": "#%s 번은 열린 일이 아니에요." % tid}
    log_event("todo." + kind, id=it["id"])
    say = {"keep": "계속할게요: #%d %s" % (it["id"], it["what"]),
           "defer": "미뤄 둘게요: #%d %s (%s 에 다시 여쭐게요)" % (it["id"], it["what"], it.get("deferred_until")),
           "cancel": "취소했어요: #%d %s" % (it["id"], it["what"])}[kind]
    return {"ok": True, "id": it["id"], "say": say}


def brief(t=None):
    """밀린 일 보고(결정론) — 개수·가장 오래된 날·물어볼 일."""
    t = t or today()
    data = load_todos()
    open_items = [it for it in data["items"] if is_open(it)]
    stale = [it for it in open_items if should_ask(it, t)]
    out = {"open": len(open_items), "stale": [{"id": it["id"], "what": it["what"],
                                               "days": age_days(it, t)} for it in stale]}
    if open_items:
        oldest = min(open_items, key=lambda it: (it["received"], it["id"]))
        out["oldest_days"] = age_days(oldest, t)
        out["oldest"] = {"id": oldest["id"], "what": oldest["what"], "received": oldest["received"]}
        out["say"] = "%s %d건 · 가장 오래된 것 받은 지 %d일(#%d %s)" % (
            BRIEF_MARK, len(open_items), out["oldest_days"], oldest["id"], clean(oldest["what"], ITEM_CAP))
    else:
        out["oldest_days"] = 0
        out["say"] = "%s 0건이에요." % BRIEF_MARK
    if stale:
        out["ask"] = ["#%d %s — 받은 지 %d일 됐어요. 계속할까요, 미룰까요, 취소할까요?" % (
            s["id"], clean(s["what"], ITEM_CAP), s["days"]) for s in out["stale"]]
    return out


def todos_say(items):
    if not items:
        return "적어 둔 열린 일이 없어요."
    t = today()
    return "\n".join("#%d %s (받은 지 %d일%s)" % (it["id"], it["what"], age_days(it, t),
                                                ", 끝나면 알림" if it.get("notify") else "") for it in items)


# ── ③ 끝나면 알림 ─────────────────────────────────────────────────────────────
def _cys_bin():
    return os.environ.get("CYS_BIN") or "cys"


def flush_app_notices():
    """원장의 앱 알림 의무를 보낸다 — 잠금 안에서 「보내는 중」 표지를 잡은 것만 보내고(중복 0), 성공이면 sent ·
    실패면 pending 으로 되돌려 다음 훅(오너 입력·세션 시작)에서 재시도한다. 반환 = {id: "sent"|"failed"}."""
    now = time.time()
    claimed = []

    def claim(data):
        for it in data["items"]:
            n = it.get("notice") or {}
            st = n.get("app")
            if st == "pending" or (isinstance(st, str) and st.startswith("claimed:")
                                   and now - float(st.split(":", 1)[1]) > APP_CLAIM_STALE):
                n["app"] = "claimed:%f" % now
                claimed.append({"id": it["id"], "what": it["what"], "evidence": it.get("evidence", "")})

    if not os.path.exists(_todo_path()):
        return {}
    _mutate(claim)
    results = {}
    for c in claimed:
        title = "끝났어요: %s" % clean(c["what"], 60)
        body = "#%d %s\n근거: %s" % (c["id"], c["what"], c["evidence"])
        try:
            p = subprocess.run([_cys_bin(), "feed", "push", "--kind", "ceo-notice", "--title", title, "--body", body],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
                               stdin=subprocess.DEVNULL, **NOWIN)
            ok = p.returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
        results[c["id"]] = "sent" if ok else "failed"

    def settle(data):
        for it in data["items"]:
            if it["id"] in results:
                n = it.get("notice") or {}
                if results[it["id"]] == "sent":
                    n["app"] = "sent"
                    n["app_sent_at"] = now_iso()
                else:
                    n["app"] = "pending"
                    n["app_attempts"] = n.get("app_attempts", 0) + 1

    if claimed:
        _mutate(settle)
        for i, st in results.items():
            log_event("notify.app", id=i, result=st)
    return results


def phone_pending():
    return [it for it in load_todos()["items"] if (it.get("notice") or {}).get("phone") == "pending"]


def mark_phone_sent(message):
    """PushNotification 메시지 끝의 (#번호)로 그 일의 폰 의무만 닫는다(엉뚱한 알림 1번이 여러 의무를 닫지 않게)."""
    ids = set(int(x) for x in re.findall(r"\(#(\d+)\)", message or ""))
    if not ids:
        return []
    done = []

    def f(data):
        for it in data["items"]:
            n = it.get("notice") or {}
            if it["id"] in ids and n.get("phone") == "pending":
                n["phone"] = "sent"
                n["phone_sent_at"] = now_iso()
                done.append(it["id"])

    _mutate(f)
    return done


def _phone_reminder_lines():
    """다음 오너 턴에 미발송 폰 알림을 일러 준다(일마다 최대 PHONE_REMINDERS 번 · 그 뒤 포기 기록)."""
    pend = phone_pending()
    if not pend:
        return []
    ids = [it["id"] for it in pend]
    out = []

    def f(data):
        for it in data["items"]:
            n = it.get("notice") or {}
            if it["id"] in ids and n.get("phone") == "pending":
                n["phone_reminders"] = n.get("phone_reminders", 0) + 1
                if n["phone_reminders"] > PHONE_REMINDERS:
                    n["phone"] = "unsent"          # 포기 — 무한히 조르지 않는다(원장에 남는다)
                else:
                    out.append(n.get("message", ""))

    _mutate(f)
    return ["【보내지 않은 폰 알림 — PushNotification 으로 보내라】%s" % m for m in out]


# ── 훅 ───────────────────────────────────────────────────────────────────────
def _read_hook_in():
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        return json.loads(raw) if raw.strip() else {}
    except (ValueError, OSError):
        return {}


def _tool_line():
    py = os.environ.get("CYS_PY") or sys.executable or "python3"
    return '"%s" "%s"' % (py, os.path.abspath(__file__))


def _slot(name):
    d = os.path.join(owner_dir(), name)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "%s.json" % re.sub(r"[^0-9A-Za-z_.-]", "_", surface()))


def _turn_path():
    return _slot("turns")


def _carry_path():
    return _slot("carry")


def _brief_path():
    return os.path.join(owner_dir(), "brief.json")


def is_machine(prompt):
    """기계 채널 입력인가(wake·노드 push·알림) — javis_mission.machine_origin 단일 소유를 쓴다(사본 금지).
    판별기가 없거나 실패하면 라벨 폴백: 대괄호 라벨([wakeup]·[schedule]·[보고] …)로 시작하면 기계로 접는다."""
    try:
        import javis_mission
        return bool(javis_mission.machine_origin(prompt)[0])
    except Exception:
        return (prompt or "").lstrip().startswith("[")


def _ctx(event, text):
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def _fit(event, required, optional, more_note):
    """필수 줄(호출처가 이미 정리·상한 적용)을 먼저 확보하고, 선택 줄은 직렬화 뒤 길이가 HOOK_JSON_CAP 안에 드는
    만큼만 싣는다. 잘린 선택 줄 수는 more_note 로 고지한다. 반환 = 훅 JSON(직렬화 길이 ≤ HOOK_JSON_CAP 보장)."""
    body = list(required)
    used = len(json.dumps(_ctx(event, "\n".join(body)), ensure_ascii=False))
    dropped = 0
    for i, line in enumerate(optional):
        add = len(json.dumps(line, ensure_ascii=False)) + 2
        if used + add + 80 > HOOK_JSON_CAP:
            dropped = len(optional) - i
            break
        body.append(line)
        used += add
    if dropped and more_note:
        body.append(more_note % dropped)
    out = _ctx(event, "\n".join(body))
    while len(json.dumps(out, ensure_ascii=False)) > HOOK_JSON_CAP and len(body) > 1:   # 최후 방어
        body.pop(-1)
        out = _ctx(event, "\n".join(body))
    return out


def _carry_lines(carry, tl):
    """직전 오너 턴에서 넘어온 할 일 — 턴 끝에 막지 않고(막으면 답이 되풀이된다 · 11-18 실좌석 실측) 다음 턴에 싣는다."""
    out = []
    for txt in carry.get("saved_unshown", []):
        out.append("【직전 턴 확인 줄 누락 — 이번 답에 1줄】%s: 「%s」" % (SAVED_MARK, clean(txt, ITEM_CAP)))
    for txt in carry.get("removed_unshown", []):
        out.append("【직전 턴 확인 줄 누락 — 이번 답에 1줄】%s: 「%s」" % (REMOVED_MARK, clean(txt, ITEM_CAP)))
    if carry.get("second_look"):
        out.append("【직전 오너 입력 다시 보기 · owner-desk】직전 오너 입력 «%s» 에 앞으로 계속 지킬 지시나 맡긴 일·끝 알림 "
                   "부탁이 있었는데 기록하지 않았다면 이번 턴에 %s 로 기록하고 say 1줄을 보여라(없었으면 이 줄은 무시)."
                   % (clean(carry["second_look"], 300), tl))
    return out


PROTOCOL = ("■ 규약: 오너가 앞으로 계속 지킬 지시를 주면 그 턴 안에 `rule add --text` 로 저장하고 도구가 준 say 1줄"
            "(「%s: …」)을 보인다 · 「그 규칙 지워」 = `rule remove <번호>` · 「기억하는 규칙 보여 줘」 = `rule list` · "
            "오너가 일을 시키면 `todo add --what`(여럿이면 --what 여러 번 · 급한 것 --urgent N · 짧은 것 --short N) · "
            "끝나면 `todo done <id> --evidence` · 「끝나면 알려 줘」 = `todo add … --notify`(늘 그렇게 = `notify set --all-done on`) · "
            "끝 알림 기본 = 앱 알림 + 폰(PushNotification) · 오너가 카톡을 원하면 「컴퓨터 조작으로 카톡 보내기는 불안정할 수 "
            "있어요」 1줄 안내 뒤 오너가 고르면 스킬 computer-control 길로 보낸다(새 로그인·외부 API 만들지 않음)." % SAVED_MARK)


def hook_session(hin):
    flush_app_notices()                                     # 보내다 실패한 앱 알림 재시도
    rules = list_rules()
    b = brief()
    tl = _tool_line()
    required = ["■ 오너 책상(owner-desk) — 오너가 한 번 시킨 것을 잊지 않기 위한 기록이다. 도구 = %s" % tl,
                PROTOCOL, "■ 오너 할 일 원장: %s" % b["say"]]
    # 순환(/clear·압축) 직전 턴에서 넘어온 것도 잃지 않는다(지우지는 않음 — 다음 오너 입력 훅이 싣고 지운다).
    required += _carry_lines(_load_json(_carry_path(), {}), tl)
    if rules:
        required.append("■ 오너가 앞으로 계속 지키라고 한 지시 %d개(장기기억 · 이 대화에서도 그대로 지킨다):" % len(rules))
    else:
        required.append("■ 오너가 저장해 둔 지속 지시: 없음")
    optional = ["  %d. %s" % (r["no"], clean(r["text"], ITEM_CAP * 2)) for r in rules]
    return _fit("SessionStart", required, optional, "  …외 %d개 — 전부 보려면 rule list")


def hook_prompt(hin):
    prompt = hin.get("prompt") or ""
    tp = _turn_path()
    state = _load_json(tp, {})
    if not prompt.strip() or is_machine(prompt):
        # 기계 입력 턴은 오너 턴이 아니다 — 앞 오너 턴의 표지가 남아 이 턴 끝에서 대조되지 않게 내린다.
        if state.get("owner"):
            state["owner"] = False
            _atomic_write(tp, json.dumps(state, ensure_ascii=False))
        return None
    flush_app_notices()                                     # 보내다 실패한 앱 알림 재시도
    t = today().isoformat()
    b = brief()
    # 아침 보고 = 오너 전체에서 하루 1번 · 「말했다」가 Stop 에서 확인될 때까지(중단·누락이면 다음 입력에 다시).
    brief_due = _load_json(_brief_path(), {}).get("confirmed_on") != t and b["open"] > 0
    cp = _carry_path()
    carry = _load_json(cp, {})
    tl = _tool_line()
    required = []
    if brief_due:
        required.append("【오늘 첫 오너 대화 — 답 첫 줄에 이 문장을 그대로 먼저 말한다】%s" % b["say"])
    required += _carry_lines(carry, tl)
    required += _phone_reminder_lines()
    required.append("【오너 지시 점검 · owner-desk】이 오너 입력에 ⑴앞으로 계속 지킬 지시(선호·습관·규칙)가 있으면 이 턴 안에 "
                    "%s rule add --text \"<지시>\" 로 저장하고 say 1줄(「%s: …」)을 보여라 ⑵새로 시킨 일이면 todo add "
                    "(여럿이면 순서를 정해 say 1줄로 알림) ⑶「끝나면 알려 줘」면 --notify(앞으로 늘 그렇게면 notify set "
                    "--all-done on 도) ⑷일을 끝내면 todo done <id> --evidence. 판단은 낱말이 아니라 뜻으로 한다 · 일회성 "
                    "부탁이나 잡담이면 아무것도 저장하지 않는다." % (tl, SAVED_MARK))
    asks = b.get("ask", []) if brief_due else []
    optional = ["【사흘 넘은 일 — 오너에게 먼저 물어라】%s → 답에 따라 `todo keep|defer|cancel <id>`" % a
                for a in asks[:MAX_ASKS]]
    more = len(asks) - len(optional)
    out = _fit("UserPromptSubmit", required, optional, "【사흘 넘은 일 …외 %d건 — todo brief 로 확인】")
    if more > 0:
        out["hookSpecificOutput"]["additionalContext"] += "\n【사흘 넘은 일 %d건 더 — 오늘은 위 것부터 · todo brief】" % more
    turn = {"start_ts": time.time(), "owner": True, "brief_due": brief_due,
            "carried_saved": carry.get("saved_unshown", []),
            "prompt_excerpt": clean(prompt, 300),
            "prompt_sha": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]}
    _atomic_write(tp, json.dumps(turn, ensure_ascii=False))
    if carry:                                               # 실은 이월만 지운다(필수 줄이라 늘 실린다)
        try:
            os.unlink(cp)
        except OSError:
            pass
    return out


def _block(reason):
    return {"decision": "block", "reason": reason}


def hook_stop(hin):
    """턴 끝 안전망(11-18 실좌석 실측 반영).

    막는 것(decision=block)은 둘뿐이다 — ①「저장했습니다」라고 말했는데 저장 근거가 없음(이번 턴 rule add · 이월된
    확인 줄 · 같은 지시 재저장 어느 것도 없음 = 거짓 확인) ②끝난 일의 폰 알림 의무가 남음(도구 호출 1번이면 된다).
    그 밖(저장했는데 확인 줄 누락 · 기록 0건 턴)은 **막지 않고 다음 오너 턴으로 넘긴다** — 막으면 모델이 빈 답을 내고
    하네스가 보이는 답을 강요해 같은 답이 되풀이됐다(실측: 한 턴에 같은 표 3번). 아침 보고는 「말했다」 확인만 기록하고,
    확인이 없으면 다음 오너 입력이 다시 싣는다(사용자가 중간에 끊어 Stop 이 오지 않아도 같다).
    """
    tp = _turn_path()
    turn = _load_json(tp, {})
    if not turn.get("owner"):
        return None
    msg = hin.get("last_assistant_message") or ""
    ev = events_since(turn.get("start_ts", 0), surface())
    ops = [e.get("op") for e in ev]
    tl = _tool_line()
    if turn.get("brief_due") and BRIEF_MARK in msg:
        t = today().isoformat()
        _update_json(_brief_path(), {}, lambda d: d.update(confirmed_on=t))
    carry = {}
    adds = [e.get("text", "") for e in ev if e.get("op") == "rule.add" and not e.get("duplicate")]
    if adds and SAVED_MARK not in msg:
        carry["saved_unshown"] = adds
    rms = [e.get("text", "") for e in ev if e.get("op") == "rule.remove"]
    if rms and REMOVED_MARK not in msg:
        carry["removed_unshown"] = rms
    if config()["selfcheck"] and not any(o and (o.startswith("rule.") or o.startswith("todo.")) for o in ops):
        carry["second_look"] = turn.get("prompt_excerpt", "")
    cp = _carry_path()
    if carry:
        _atomic_write(cp, json.dumps(carry, ensure_ascii=False))
    else:
        try:
            os.unlink(cp)
        except OSError:
            pass
    if turn.get("blocks", 0) >= MAX_BLOCKS:                 # 고리 방지
        return None
    reasons = []
    evidence = ops.count("rule.add") or turn.get("carried_saved")
    if SAVED_MARK in msg and not evidence:
        reasons.append("답에 「%s」라고 했지만 저장 기록이 없다 — 지금 %s rule add --text \"…\" 로 실제로 저장하거나, "
                       "저장하지 않았다면 그 문장을 바로잡아라(답 전체를 되풀이하지 말고 고친 1줄만)." % (SAVED_MARK, tl))
    pend = phone_pending()
    if pend:
        reasons.append("끝난 일 폰 알림이 아직 남았다 — PushNotification 도구로 %s 를 보내라(끝의 (#번호) 그대로 · "
                       "답을 되풀이하지 말고 「알림을 보냈어요」 1줄만)."
                       % " · ".join("「%s」" % (it["notice"].get("message", "")) for it in pend[:3]))
    if reasons:
        turn["blocks"] = turn.get("blocks", 0) + 1
        _atomic_write(tp, json.dumps(turn, ensure_ascii=False))
        return _block("【owner-desk 대조】" + " / ".join(reasons))
    return None


def hook_posttool(hin):
    if (hin.get("tool_name") or "") == "PushNotification":
        msg = str((hin.get("tool_input") or {}).get("message", ""))
        ids = mark_phone_sent(msg)
        log_event("notify.phone", message=clean(msg, 200), ids=ids)
    return None


# ── CLI ──────────────────────────────────────────────────────────────────────
def _utf8_stdio():
    """윈 파이프 기본 인코딩(cp949 등)과 무관하게 훅 JSON 을 UTF-8 로 주고받는다."""
    for s in (sys.stdin, sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _utf8_stdio()
    ap = argparse.ArgumentParser(description="오너 책상 — 지속 지시·할 일 원장·끝 알림")
    sub = ap.add_subparsers(dest="area")
    r = sub.add_parser("rule")
    rs = r.add_subparsers(dest="act")
    ra = rs.add_parser("add")
    ra.add_argument("--text", required=True)
    rl = rs.add_parser("list")
    rl.add_argument("--json", action="store_true")
    rr = rs.add_parser("remove")
    rr.add_argument("key")

    t = sub.add_parser("todo")
    ts = t.add_subparsers(dest="act")
    ta = ts.add_parser("add")
    ta.add_argument("--what", action="append", required=True)
    ta.add_argument("--urgent", type=int, action="append", default=[], help="급한 것(--what 순번 1부터)")
    ta.add_argument("--short", type=int, action="append", default=[], help="짧은 것(--what 순번 1부터)")
    ta.add_argument("--notify", action="store_true")
    td = ts.add_parser("done")
    td.add_argument("id")
    td.add_argument("--evidence", required=True)
    tk = ts.add_parser("keep")
    tk.add_argument("id")
    tf = ts.add_parser("defer")
    tf.add_argument("id")
    tf.add_argument("--days", type=int, default=7)
    tc = ts.add_parser("cancel")
    tc.add_argument("id")
    tc.add_argument("--reason", default="")
    tl = ts.add_parser("list")
    tl.add_argument("--all", action="store_true")
    tl.add_argument("--json", action="store_true")
    tb = ts.add_parser("brief")
    tb.add_argument("--json", action="store_true")

    n = sub.add_parser("notify")
    ns = n.add_subparsers(dest="act")
    nset = ns.add_parser("set")
    nset.add_argument("--channel", choices=VALID_CHANNELS)
    nset.add_argument("--all-done", choices=("on", "off"))
    nset.add_argument("--selfcheck", choices=("on", "off"))
    ns.add_parser("status")

    h = sub.add_parser("hook")
    h.add_argument("event", choices=("auto", "session", "prompt", "stop", "posttool"))

    a = ap.parse_args(argv)
    if a.area == "hook":
        # 훅 계약: 무슨 일이 있어도 exit 0 · stdout = 훅 JSON 한 개 또는 무출력.
        try:
            hin = _read_hook_in()
            ev = a.event
            if ev == "auto":
                ev = HOOK_EVENTS.get(hin.get("hook_event_name") or "", "")
                if not ev:
                    return 0
            out = {"session": hook_session, "prompt": hook_prompt, "stop": hook_stop,
                   "posttool": hook_posttool}[ev](hin)
            if out:
                emit(out)
        except Exception as e:  # fail-open
            print("[owner-desk] 훅 실패(%s): %s" % (a.event, e), file=sys.stderr)
        return 0
    try:
        if a.area == "rule":
            if a.act == "add":
                res = rule_add(a.text)
            elif a.act == "remove":
                res = rule_remove(a.key)
            elif a.act == "list":
                rules = list_rules()
                res = {"ok": True, "rules": rules, "say": rules_say(rules)}
            else:
                ap.print_help()
                return 2
        elif a.area == "todo":
            if a.act == "add":
                res = todo_add(a.what, set(a.urgent), set(a.short), a.notify)
            elif a.act == "done":
                res = todo_done(a.id, a.evidence)
            elif a.act in ("keep", "defer", "cancel"):
                res = todo_answer(a.id, a.act, getattr(a, "days", None), getattr(a, "reason", ""))
            elif a.act == "list":
                items = [it for it in load_todos()["items"] if a.all or is_open(it)]
                res = {"ok": True, "items": items, "say": todos_say([i for i in items if is_open(i)])}
            elif a.act == "brief":
                res = dict(brief(), ok=True)
            else:
                ap.print_help()
                return 2
        elif a.area == "notify":
            if a.act == "set":
                changes = {}
                if a.channel:
                    changes["notify_channel"] = a.channel
                if a.all_done:
                    changes["notify_all_done"] = a.all_done == "on"
                if a.selfcheck:
                    changes["selfcheck"] = a.selfcheck == "on"
                c = update_config(changes)
                log_event("notify.set", **changes)
            else:
                c = config()
            names = {"app": "앱 안 알림", "phone": "폰·바탕화면 알림", "both": "앱 안 알림 + 폰·바탕화면 알림", "off": "끔"}
            res = {"ok": True, "config": c, "say": "끝 알림: %s · 모든 일 끝날 때마다 알림: %s" % (
                names[c["notify_channel"]], "켬" if c["notify_all_done"] else "끔(--notify 한 일만)")}
        else:
            ap.print_help()
            return 2
    except TimeoutError as e:
        res = {"ok": False, "error": str(e), "say": "원장이 잠겨 있어 잠시 뒤 다시 해 볼게요."}
    emit(res)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
