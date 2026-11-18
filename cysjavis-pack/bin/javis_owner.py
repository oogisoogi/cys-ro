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
HOOK_EVENTS = {"SessionStart": "session", "UserPromptSubmit": "prompt", "Stop": "stop", "PreToolUse": "pretool",
               "PostToolUse": "posttool"}
# 윈 무콘솔 세대: 캡처 하위 프로세스는 콘솔 창을 띄우지 않고(CREATE_NO_WINDOW) stdin 을 명시한다(WinError 6 방지 ·
#   팩 계약 tests/test_nowin_captured_spawns.py · test_dept_tick_stdin.py).
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}
MAX_BLOCKS = 2                 # 한 오너 턴에서 Stop 훅이 막는 최대 횟수(고리 방지)
HOOK_JSON_CAP = 9500           # 훅 출력 상한(하네스 10,000자 · 직렬화 뒤 길이로 잰다)
ITEM_CAP = 120                 # 목록 항목(규칙·일 제목) 표시 상한
MAX_ASKS = 5                   # 한 번에 묻는 사흘 넘은 일 수
APP_CLAIM_STALE = 60           # 앱 알림 「보내는 중」 표지가 이보다 오래면 재시도(보내다 죽은 경우)
APP_SEND_BUDGET = 4.0          # 한 번의 flush 가 새 발송을 시작하는 시간 상한(훅 안쪽 상한 8초 안에서 끝나게)
PHONE_CLAIM_STALE = 600        # 폰 알림을 맡은 좌석 표지가 이보다 오래면 다른 좌석이 넘겨받는다
BRIEF_CLAIM_STALE = 600        # 아침 보고를 맡은 좌석 표지 만료
CARRY_MAX = 20                 # 이월 항목 상한(오래된 「다시 보기」부터 버림)
PHONE_SENDING_STALE = 120      # PushNotification 「보내는 중」 표지(PreToolUse 가 잡음) 만료 — 실패로 PostToolUse 가 안 오면 다시 허용
PHONE_REMINDERS = 2            # 폰 알림 미발송을 다음 오너 턴에 다시 일러 주는 최대 횟수(그 뒤 포기 기록)
PHONE_OPEN = ("pending", "unsent", "present", "undelivered", "unknown")   # 도구 결과로 바뀔 수 있는 상태(sent 는 되돌리지 않는다)
PHONE_NOT_SENT_SAY = {"no_transport": "Remote Control 이 연결돼 있지 않아 폰으로 못 보냈어요",
                      "config_off": "폰 알림 설정이 꺼져 있어 못 보냈어요"}
PHONE_UNKNOWN_SAY = "폰으로 갔는지 확인하지 못했어요"
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
                            "message": _push_message(it), "phone_reminders": 0,
                            "phone_claim": {"by": surface(), "at": time.time()}}
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


def _request_id(event):
    return "owner-" + re.sub(r"[^0-9A-Za-z_.-]", "-", event)[:100]


def flush_app_notices(budget=APP_SEND_BUDGET):
    """원장의 앱 알림 의무를 보낸다 — 잠금 안에서 「보내는 중」 표지를 잡은 것만 보내고(좌석 간 중복 0), **한 건씩 바로**
    sent/pending 을 확정한다(배치 도중 끊겨도 앞서 보낸 건은 다시 안 보냄). 같은 사건은 데몬에도 같은 request_id 로
    보내 데몬이 중복을 거절한다(보낸 직후 끊겨 표지가 남은 틈의 재발송 방지). 새 발송은 budget 초 안에서만 시작하고
    못 보낸 것은 pending 으로 돌린다. 반환 = {id: "sent"|"failed"}."""
    if not os.path.exists(_todo_path()):
        return {}
    t0 = time.time()
    claimed = []

    def claim(data):
        for it in data["items"]:
            n = it.get("notice") or {}
            st = n.get("app")
            if st == "pending" or (isinstance(st, str) and st.startswith("claimed:")
                                   and t0 - float(st.split(":", 1)[1]) > APP_CLAIM_STALE):
                n["app"] = "claimed:%f" % t0
                claimed.append({"id": it["id"], "what": it["what"], "evidence": it.get("evidence", ""),
                                "event": n.get("event") or "done-%d" % it["id"]})

    _mutate(claim)
    results = {}
    for c in claimed:
        remaining = budget - (time.time() - t0)
        if remaining < 1.0:
            ok = None                                       # 시간 상한 — 보내지 않고 되돌린다(훅 안쪽 상한 8초 안 · 3R #4)
        else:
            title = "끝났어요: %s" % clean(c["what"], 60)
            body = "#%d %s\n근거: %s" % (c["id"], c["what"], c["evidence"])
            try:
                p = subprocess.run([_cys_bin(), "feed", "push", "--kind", "ceo-notice", "--title", title, "--body", body,
                                    "--request-id", _request_id(c["event"])],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=remaining,
                                   stdin=subprocess.DEVNULL, **NOWIN)
                ok = p.returncode == 0 or "duplicate request_id" in ((p.stdout or "") + (p.stderr or ""))
            except (OSError, subprocess.SubprocessError):
                ok = False

        def settle(data, c=c, ok=ok):
            it = _find(data, c["id"])
            if it is None:
                return
            n = it.get("notice") or {}
            if ok:
                n["app"] = "sent"
                n["app_sent_at"] = now_iso()
            else:
                n["app"] = "pending"
                if ok is False:
                    n["app_attempts"] = n.get("app_attempts", 0) + 1

        _mutate(settle)
        if ok is not None:
            results[c["id"]] = "sent" if ok else "failed"
            log_event("notify.app", id=c["id"], result=results[c["id"]])
    return results


def phone_pending():
    return [it for it in load_todos()["items"] if (it.get("notice") or {}).get("phone") == "pending"]


def claim_phone(only_ids=None):
    """이 좌석이 보낼 폰 알림을 잡는다 — 다른 좌석이 맡은 것(만료 전)은 건너뛴다(두 마스터 좌석의 이중 발송 방지)."""
    me, now = surface(), time.time()
    got = []

    def f(data):
        for it in data["items"]:
            n = it.get("notice") or {}
            if n.get("phone") != "pending" or (only_ids is not None and it["id"] not in only_ids):
                continue
            if now - (n.get("phone_sending") or 0) < PHONE_SENDING_STALE:
                continue                                    # 보내는 중(PreToolUse 표지) — 지시·안내 안 함(4R ①)
            cl = n.get("phone_claim") or {}
            if not cl or cl.get("by") == me or now - cl.get("at", 0) > PHONE_CLAIM_STALE:
                n["phone_claim"] = {"by": me, "at": now}
                got.append({"id": it["id"], "message": n.get("message", "")})

    if os.path.exists(_todo_path()):
        _mutate(f)
    return got


_TRAIL_ID = re.compile(r"\(#(\d+)\)\s*$")


def trailing_id(message):
    """PushNotification 메시지 **끝**의 (#번호) 하나만 읽는다 — 제목 속 「(#2)」 같은 글자로 다른 일을 닫지 않게(3R #2)."""
    m = _TRAIL_ID.search(message or "")
    return int(m.group(1)) if m else None


def gate_phone_send(message):
    """PreToolUse(PushNotification) — 실제 발송 경로의 중복 거절(3R #3). 끝 (#번호)가 우리 의무면 잠금 안에서:
    이미 sent 이거나 다른 호출이 「보내는 중」(만료 전)이면 거절, 아니면 「보내는 중」 표지를 잡고 허용.
    번호가 없거나 우리 의무가 아니면 관여하지 않는다(None)."""
    tid = trailing_id(message)
    if tid is None or not os.path.exists(_todo_path()):
        return None
    now = time.time()
    res = {}

    def f(data):
        it = _find(data, tid)
        n = (it or {}).get("notice") or {}
        st = n.get("phone")
        if not st:
            return
        sending = n.get("phone_sending") or 0
        if st == "sent" or (now - sending) < PHONE_SENDING_STALE:
            res["deny"] = "이미 보냈거나 다른 곳에서 보내는 중인 알림(#%d)이다 — 다시 보내지 마라." % tid
            return
        n["phone_sending"] = now
        res["allow"] = True

    _mutate(f)
    return res


def phone_outcome(response):
    """PushNotification 도구 결과(훅의 tool_response) → (원장 상태, 사유). 도구가 불렸다고 보낸 것이 아니다.
    sent = 실제로 보냄 · present = 오너가 화면 앞이라 도구가 건너뜀(재안내·포기 대상 아님) · undelivered = 보낼 길이
    없거나 꺼짐(오너에게 알린다) · unknown = 결과가 없거나 모르는 모양(보냈다고 적지 않는다)."""
    r = response if isinstance(response, dict) else {}
    if r.get("pushSent") is True or r.get("localSent") is True:
        return "sent", None
    why = r.get("disabledReason")
    if why == "user_present":
        return "present", why
    if why in ("no_transport", "config_off"):
        return "undelivered", why
    return "unknown", None


def settle_phone(message, response):
    """PostToolUse(PushNotification) — 끝 (#번호)의 폰 의무를 도구 결과대로 정산한다. 도구가 끝났으니 「보내는 중」 표지는
    늘 내린다. 포기 기록 뒤의 늦은 성공도 sent 로(3R #6) · 이미 sent 면 그대로. 반환 = 정산한 번호 목록."""
    tid = trailing_id(message)
    if tid is None:
        return []
    outcome, why = phone_outcome(response)
    done = []

    def f(data):
        it = _find(data, tid)
        n = (it or {}).get("notice") or {}
        if n.get("phone") in PHONE_OPEN:
            n["phone"] = outcome
            n["phone_reason"] = why
            n.pop("phone_sending", None)
            if outcome == "sent":
                n["phone_sent_at"] = now_iso()
            done.append(tid)

    _mutate(f)
    return done


def phone_to_tell():
    """못 보냈거나 확인이 안 된 폰 알림 중 오너에게 아직 말하지 않은 것 → [(번호, 안내 줄)]."""
    out = []
    for it in load_todos()["items"]:
        n = it.get("notice") or {}
        if n.get("phone") in ("undelivered", "unknown") and not n.get("phone_told"):
            say = PHONE_NOT_SENT_SAY.get(n.get("phone_reason"), PHONE_UNKNOWN_SAY)
            out.append((it["id"], "【폰 알림 결과 — 답에서 오너에게 먼저 말하고, 다시 보내지는 마라】#%d %s: %s"
                        % (it["id"], clean(it["what"], ITEM_CAP), say)))
    return out


def mark_phone_told(ids):
    """실제로 출력에 실린 안내만 「말함」으로 적는다(못 실은 것은 다음 입력에 다시)."""
    if not ids:
        return

    def f(data):
        for it in data["items"]:
            if it["id"] in ids and it.get("notice"):
                it["notice"]["phone_told"] = True

    _mutate(f)


def expire_phone():
    """PHONE_REMINDERS 번 일러 줬는데도 남은 폰 의무는 포기 기록(unsent) — 다음 안내를 내기 **전에** 판정한다(마지막 안내의
    실행 기회를 빼앗지 않게 · 3R #6). 늦게라도 보내면 settle_phone 이 sent 로 바꾼다."""
    def f(data):
        for it in data["items"]:
            n = it.get("notice") or {}
            if n.get("phone") == "pending" and n.get("phone_reminders", 0) >= PHONE_REMINDERS \
                    and time.time() - (n.get("phone_sending") or 0) >= PHONE_SENDING_STALE:
                n["phone"] = "unsent"

    if os.path.exists(_todo_path()):
        _mutate(f)


def bump_phone_reminders(ids):
    """실제로 일러 준(출력에 실린) 폰 알림만 횟수를 올린다(포기 판정은 다음 입력 때 expire_phone)."""
    if not ids:
        return

    def f(data):
        for it in data["items"]:
            n = it.get("notice") or {}
            if it["id"] in ids and n.get("phone") == "pending" \
                    and time.time() - (n.get("phone_sending") or 0) >= PHONE_SENDING_STALE:
                n["phone_reminders"] = n.get("phone_reminders", 0) + 1

    _mutate(f)


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


def _fit(event, must, groups):
    """must(규약·점검·보고 줄 — 호출처가 이미 정리·상한 적용)는 늘 싣고, groups=[(태그, [(키, 줄)…], 넘침 고지 %d)]
    는 순서대로 직렬화 길이가 HOOK_JSON_CAP 안에 드는 만큼만 싣는다. 반환 = (훅 JSON, {태그: [실린 키…]}).
    호출처는 **실린 키만** 소비한다(못 실은 이월·알림 안내는 남겨 다음에 싣는다 · codex 2R #1)."""
    body = list(must)
    used = len(json.dumps(_ctx(event, "\n".join(body)), ensure_ascii=False))
    emitted = {}
    notes = []
    for tag, items, note in groups:
        emitted[tag] = []
        dropped = 0
        for key, line in items:
            add = len(json.dumps(line, ensure_ascii=False)) + 2
            if dropped or used + add + 160 > HOOK_JSON_CAP:     # 160 = 넘침 고지 자리
                dropped += 1
                continue
            body.append(line)
            used += add
            emitted[tag].append(key)
        if dropped and note:
            notes.append(note % dropped)
    return _ctx(event, "\n".join(body + notes)), emitted


# ── 턴 정산(이월) ─────────────────────────────────────────────────────────────
def _load_carry():
    c = _load_json(_carry_path(), {})
    return c.get("items", []) if isinstance(c, dict) else []


def _save_carry(items):
    cp = _carry_path()
    if items:
        if len(items) > CARRY_MAX:                          # 넘치면 오래된 「다시 보기」부터 버린다
            looks = [i for i, x in enumerate(items) if x.get("k") == "second"]
            for i in reversed(looks[:len(items) - CARRY_MAX]):
                items.pop(i)
            items = items[-CARRY_MAX:]
        _atomic_write(cp, json.dumps({"items": items}, ensure_ascii=False))
    else:
        try:
            os.unlink(cp)
        except OSError:
            pass


def settle_turn(turn):
    """끝난(또는 끊긴) 오너 턴을 이월 항목으로 정산한다 — 다음 오너 입력·세션 시작이 부른다(Stop 이 아니라).

    왜 Stop 이 아니라 다음 입력인가: ①사용자가 중간에 끊으면 Stop 이 오지 않는다(공식 hooks 문서) ②Stop 이 한 턴에
    여러 번 올 수 있다(막기 뒤 이어진 답) — 마지막 Stop 을 알 수 없으므로 턴 전체의 「보였다」 기록(saved_shown 등)을
    모았다가 다음 입력에서 한 번 정산한다(codex 2R #7·논쟁점)."""
    if not turn.get("owner") or turn.get("settled"):
        return
    ev = events_since(turn.get("start_ts", 0), surface())
    ops = [e.get("op") for e in ev]
    items = _load_carry()
    adds = [e.get("text", "") for e in ev if e.get("op") == "rule.add" and not e.get("duplicate")]
    if adds and not turn.get("saved_shown"):
        items += [{"k": "saved", "text": x} for x in adds]
    rms = [e.get("text", "") for e in ev if e.get("op") == "rule.remove"]
    if rms and not turn.get("removed_shown"):
        items += [{"k": "removed", "text": x} for x in rms]
    if config()["selfcheck"] and not any(o and (o.startswith("rule.") or o.startswith("todo.")) for o in ops):
        items.append({"k": "second", "text": turn.get("prompt_excerpt", "")})
    _save_carry(items)
    turn["settled"] = True
    _atomic_write(_turn_path(), json.dumps(turn, ensure_ascii=False))


def _carry_line(item, tl):
    k, txt = item.get("k"), item.get("text", "")
    if k == "saved":
        return "【직전 턴 확인 줄 누락 — 이번 답에 1줄】%s: 「%s」" % (SAVED_MARK, clean(txt, ITEM_CAP))
    if k == "removed":
        return "【직전 턴 확인 줄 누락 — 이번 답에 1줄】%s: 「%s」" % (REMOVED_MARK, clean(txt, ITEM_CAP))
    return ("【직전 오너 입력 다시 보기 · owner-desk】직전 오너 입력 «%s» 에 앞으로 계속 지킬 지시나 맡긴 일·끝 알림 "
            "부탁이 있었는데 기록하지 않았다면 이번 턴에 %s 로 기록하고 say 1줄을 보여라(없었으면 이 줄은 무시)."
            % (clean(txt, 300), tl))


PROTOCOL = ("■ 규약: 오너가 앞으로 계속 지킬 지시를 주면 그 턴 안에 `rule add --text` 로 저장하고 도구가 준 say 1줄"
            "(「%s: …」)을 보인다 · 「그 규칙 지워」 = `rule remove <번호>` · 「기억하는 규칙 보여 줘」 = `rule list` · "
            "오너가 일을 시키면 `todo add --what`(여럿이면 --what 여러 번 · 급한 것 --urgent N · 짧은 것 --short N) · "
            "끝나면 `todo done <id> --evidence` · 「끝나면 알려 줘」 = `todo add … --notify`(늘 그렇게 = `notify set --all-done on`) · "
            "끝 알림 기본 = 앱 알림 + 폰(PushNotification) · 오너가 카톡을 원하면 「컴퓨터 조작으로 카톡 보내기는 불안정할 수 "
            "있어요」 1줄 안내 뒤 오너가 고르면 스킬 computer-control 길로 보낸다(새 로그인·외부 API 만들지 않음)." % SAVED_MARK)


def _reserve_brief(t, open_n):
    """아침 보고 = 오너 전체 하루 1번 — 공유 잠금 아래 맡을 좌석을 예약한다(두 마스터 좌석이 동시에 받지 않게 ·
    codex 2R #5). 맡은 좌석이 끊기면 그 좌석의 다음 입력이 다시 싣고, 만료(BRIEF_CLAIM_STALE) 뒤엔 다른 좌석이 넘겨받는다.
    「말했다」 확인(confirmed_on)은 Stop 이 기록한다."""
    if open_n <= 0:
        return False
    me, now = surface(), time.time()
    res = {}

    def f(d):
        if d.get("confirmed_on") == t:
            res["due"] = False
            return
        r = d.get("reserved") or {}
        if not r or r.get("day") != t or r.get("by") == me or now - r.get("at", 0) > BRIEF_CLAIM_STALE:
            d["reserved"] = {"by": me, "at": now, "day": t}
            res["due"] = True
        else:
            res["due"] = False

    _update_json(_brief_path(), {}, f)
    return res.get("due", False)


def hook_session(hin):
    if hin.get("agent_id"):
        return None
    flush_app_notices()                                     # 보내다 실패한 앱 알림 재시도
    # /clear·재개 = 직전 턴은 끝났다 → 정산해 새 대화에 싣는다. 압축(compact)은 턴 도중에도 일어난다(공식 hooks 문서) —
    #   진행 중 턴의 Stop 안전망을 풀지 않도록 정산하지 않고 문맥만 다시 싣는다(3R #1).
    if hin.get("source") != "compact":
        settle_turn(_load_json(_turn_path(), {}))
    rules = list_rules()
    b = brief()
    tl = _tool_line()
    must = ["■ 오너 책상(owner-desk) — 오너가 한 번 시킨 것을 잊지 않기 위한 기록이다. 도구 = %s" % tl,
            PROTOCOL, "■ 오너 할 일 원장: %s" % b["say"],
            ("■ 오너가 앞으로 계속 지키라고 한 지시 %d개(장기기억 · 이 대화에서도 그대로 지킨다):" % len(rules))
            if rules else "■ 오너가 저장해 둔 지속 지시: 없음"]
    # 이월은 여기서 보여 주기만 한다(소비는 다음 오너 입력 훅 — 그 턴 첫머리에 다시 실린다).
    carry = [(i, _carry_line(x, tl)) for i, x in enumerate(_load_carry())]
    out, _ = _fit("SessionStart", must, [
        ("rules", [(r["no"], "  %d. %s" % (r["no"], clean(r["text"], ITEM_CAP * 2))) for r in rules],
         "  …외 %d개 — 전부 보려면 rule list"),
        ("carry", carry, "【이월 %d건 더 — 다음 입력에 이어서】")])
    return out


def hook_prompt(hin):
    if hin.get("agent_id"):
        return None
    prompt = hin.get("prompt") or ""
    tp = _turn_path()
    state = _load_json(tp, {})
    settle_turn(state)                                      # 직전 오너 턴(끊긴 턴 포함) 정산 → 이월
    if not prompt.strip() or is_machine(prompt):
        # 기계 입력 턴은 오너 턴이 아니다 — 앞 오너 턴의 표지가 남아 이 턴 끝에서 대조되지 않게 내린다.
        if state.get("owner"):
            state["owner"] = False
            _atomic_write(tp, json.dumps(state, ensure_ascii=False))
        return None
    flush_app_notices()                                     # 보내다 실패한 앱 알림 재시도
    t = today().isoformat()
    b = brief()
    brief_due = _reserve_brief(t, b["open"])
    tl = _tool_line()
    must = []
    if brief_due:
        must.append("【오늘 첫 오너 대화 — 답 첫 줄에 이 문장을 그대로 먼저 말한다】%s" % b["say"])
    must.append("【오너 지시 점검 · owner-desk】이 오너 입력에 ⑴앞으로 계속 지킬 지시(선호·습관·규칙)가 있으면 이 턴 안에 "
                "%s rule add --text \"<지시>\" 로 저장하고 say 1줄(「%s: …」)을 보여라 ⑵새로 시킨 일이면 todo add "
                "(여럿이면 순서를 정해 say 1줄로 알림) ⑶「끝나면 알려 줘」면 --notify(앞으로 늘 그렇게면 notify set "
                "--all-done on 도) ⑷일을 끝내면 todo done <id> --evidence. 판단은 낱말이 아니라 뜻으로 한다 · 일회성 "
                "부탁이나 잡담이면 아무것도 저장하지 않는다." % (tl, SAVED_MARK))
    carry_items = _load_carry()
    expire_phone()
    phones = claim_phone()
    asks = b.get("ask", []) if brief_due else []
    out, emitted = _fit("UserPromptSubmit", must, [
        ("carry", [(i, _carry_line(x, tl)) for i, x in enumerate(carry_items)], "【이월 %d건 더 — 다음 입력에 이어서】"),
        ("phone", [(p["id"], "【보내지 않은 폰 알림 — PushNotification 으로 보내라】%s" % clean(p["message"], ITEM_CAP))
                   for p in phones], "【보내지 않은 폰 알림 %d건 더】"),
        ("phone_told", phone_to_tell(), "【폰 알림 결과 %d건 더 — 다음 입력에 이어서】"),
        ("ask", [(i, "【사흘 넘은 일 — 오너에게 먼저 물어라】%s → 답에 따라 `todo keep|defer|cancel <id>`" % a)
                 for i, a in enumerate(asks[:MAX_ASKS])], "【사흘 넘은 일 %d건 더 — todo brief】")])
    if len(asks) > MAX_ASKS:
        out["hookSpecificOutput"]["additionalContext"] += \
            "\n【사흘 넘은 일 %d건 더 — 오늘은 위 것부터 · todo brief】" % (len(asks) - MAX_ASKS)
    shown = set(emitted["carry"])                           # 실린 이월만 소비한다
    _save_carry([x for i, x in enumerate(carry_items) if i not in shown])
    bump_phone_reminders(set(emitted["phone"]))             # 실제로 일러 준 폰 알림만 센다
    mark_phone_told(set(emitted["phone_told"]))
    turn = {"start_ts": time.time(), "owner": True, "brief_due": brief_due, "brief_day": t,
            "carried_saved": [carry_items[i].get("text", "") for i in shown if carry_items[i].get("k") == "saved"],
            "prompt_excerpt": clean(prompt, 300),
            "prompt_sha": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]}
    _atomic_write(tp, json.dumps(turn, ensure_ascii=False))
    return out


def _block(reason):
    return {"decision": "block", "reason": reason}


def hook_stop(hin):
    """턴 끝 안전망(11-18 실좌석 실측 반영).

    막는 것(decision=block)은 둘뿐이다 — ①「저장했습니다」라고 말했는데 저장 근거가 없음(이번 턴 rule add · 이월된
    확인 줄 · 같은 지시 재저장 어느 것도 없음 = 거짓 확인) ②이 좌석이 맡은 끝난 일의 폰 알림 의무가 남음.
    그 밖은 막지 않는다 — 막으면 모델이 빈 답을 내고 하네스가 보이는 답을 강요해 같은 답이 되풀이됐다(실측: 같은 표
    3번). 이 훅은 「이번 턴에 무엇을 보였나」만 턴 표지에 모으고, 이월 정산은 다음 오너 입력이 한 번 한다(settle_turn).
    """
    if hin.get("agent_id"):
        return None
    tp = _turn_path()
    turn = _load_json(tp, {})
    if not turn.get("owner") or turn.get("settled"):
        return None
    msg = hin.get("last_assistant_message") or ""
    if SAVED_MARK in msg:
        turn["saved_shown"] = True
    if REMOVED_MARK in msg:
        turn["removed_shown"] = True
    if turn.get("brief_due") and BRIEF_MARK in msg:
        day = turn.get("brief_day") or today().isoformat()  # 보고를 실은 날로 확인(자정 넘긴 Stop 이 다음 날을 소비하지 않게 · 3R #5)
        # 확인 날짜는 뒤로 가지 않는다 — 전날 턴의 늦은 Stop 이 오늘 확인을 되돌리지 않게(4R ②).
        _update_json(_brief_path(), {}, lambda d: d.update(confirmed_on=max(d.get("confirmed_on") or "", day)))
    turn["stopped"] = True
    ev = events_since(turn.get("start_ts", 0), surface())
    tl = _tool_line()
    reasons = []
    if turn.get("blocks", 0) < MAX_BLOCKS:                  # 고리 방지
        evidence = [e for e in ev if e.get("op") == "rule.add"] or turn.get("carried_saved")
        if SAVED_MARK in msg and not evidence:
            reasons.append("답에 「%s」라고 했지만 저장 기록이 없다 — 지금 %s rule add --text \"…\" 로 실제로 저장하거나, "
                           "저장하지 않았다면 그 문장을 바로잡아라(답 전체를 되풀이하지 말고 고친 1줄만)." % (SAVED_MARK, tl))
        mine = claim_phone()
        if mine:
            reasons.append("끝난 일 폰 알림이 아직 남았다 — PushNotification 도구로 %s 를 보내라(끝의 (#번호) 그대로 · "
                           "답을 되풀이하지 말고 「알림을 보냈어요」 1줄만)."
                           % " · ".join("「%s」" % clean(p["message"], ITEM_CAP) for p in mine[:3]))
    if reasons:
        turn["blocks"] = turn.get("blocks", 0) + 1
    _atomic_write(tp, json.dumps(turn, ensure_ascii=False))
    return _block("【owner-desk 대조】" + " / ".join(reasons)) if reasons else None


def hook_pretool(hin):
    if (hin.get("tool_name") or "") != "PushNotification":
        return None
    r = gate_phone_send(str((hin.get("tool_input") or {}).get("message", "")))
    if r and r.get("deny"):
        log_event("notify.phone_denied", reason=r["deny"])
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": r["deny"]}}
    return None


def hook_posttool(hin):
    """PushNotification 결과 정산 — 하위 에이전트가 부른 것도 정산한다(그래야 부모가 다시 보내지 않는다 · codex 2R #4)."""
    if (hin.get("tool_name") or "") == "PushNotification":
        msg = str((hin.get("tool_input") or {}).get("message", ""))
        resp = hin.get("tool_response")
        ids = settle_phone(msg, resp)
        log_event("notify.phone", message=clean(msg, 200), ids=ids, result=phone_outcome(resp)[0],
                  agent=bool(hin.get("agent_id")))
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
    h.add_argument("event", choices=("auto", "session", "prompt", "stop", "pretool", "posttool"))

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
                   "pretool": hook_pretool, "posttool": hook_posttool}[ev](hin)
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
