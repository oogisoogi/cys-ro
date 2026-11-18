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
  todo done <id> --evidence "<근거>" 끝 표시 → 알림 켜져 있으면 그 자리에서 알림 1회(중복 0)
  todo keep|defer|cancel <id> …      사흘 넘은 일에 대한 오너 답(계속 / 미룸 / 취소)
  todo list [--all] [--json] · todo brief [--json]   밀린 일 n건 · 가장 오래된 것 · 물어볼 일
  notify set --channel app|phone|both|off [--all-done on|off] · notify status
  hook session|prompt|stop|posttool  Claude Code 훅 본체(stdin = 훅 JSON · stdout = 훅 JSON 또는 무출력 · 늘 exit 0)

저장 위치: 규칙 = 팩 장기기억 폴더(javis_memory 와 같은 곳 · 새 저장소 없음) · 원장·설정·턴 표지 = ${CYS_OWNER_DIR:-~/.cys/owner}
(오너 기기 안에만 · 바깥 전송 0 · 알림 「phone」 길만 Claude Code 자체 PushNotification 을 모델이 부른다).
의존성: 파이썬 표준 라이브러리 + 같은 bin 의 javis_memory(하위 프로세스) · javis_mission(기계 입력 판별 · 없으면 라벨 폴백).
"""

import argparse
import datetime as _dt
import hashlib
import json
import os
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
STALE_DAYS = 3                 # 「사흘 넘은」 = 받은(또는 계속 답한·미룸 끝난) 날부터 3일 초과
SESSION_RULES_CAP = 2600       # 세션 주입 안 규칙 블록 상한(훅 출력 10,000자 상한 · 다른 훅과 별개)
PROMPT_CAP = 2400
SAVED_MARK = "이렇게 저장했습니다"
REMOVED_MARK = "이렇게 지웠습니다"
BRIEF_MARK = "밀린 일"
VALID_CHANNELS = ("app", "phone", "both", "off")
HOOK_EVENTS = {"SessionStart": "session", "UserPromptSubmit": "prompt", "Stop": "stop", "PostToolUse": "posttool"}
MAX_BLOCKS = 2                 # 한 오너 턴에서 Stop 훅이 막는 최대 횟수(고리 방지)


# ── 경로·시각 ─────────────────────────────────────────────────────────────────
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


def log_event(op, **kw):
    """턴 대조용 사건 원장(append 전용) — 훅의 Stop 검사가 「이번 턴에 저장했는가」를 이것으로 잰다."""
    rec = {"ts": time.time(), "at": now_iso(), "surface": surface(), "op": op}
    rec.update(kw)
    with open(os.path.join(owner_dir(), "events.jsonl"), "a", encoding="utf-8") as f:
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
def config():
    c = _load_json(os.path.join(owner_dir(), "config.json"), {})
    c.setdefault("notify_channel", "both")   # 기본 = 앱 안 알림 + 폰/바탕화면(PushNotification)
    c.setdefault("notify_all_done", False)   # 「일이 끝나면 늘 알려 줘」 지속 지시 = True
    c.setdefault("selfcheck", True)          # 다시 보기(안전망) — 기록 0건인 오너 턴을 다음 턴에 한 번 더 점검시킨다
    return c


def save_config(c):
    path = os.path.join(owner_dir(), "config.json")
    with Lock(path):
        _atomic_write(path, json.dumps(c, ensure_ascii=False, indent=1) + "\n")


# ── ① 오래 지킬 지시(규칙) ─────────────────────────────────────────────────────
def _parse_rule_file(path):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    head, body = text[3:end], text[end + 4:].strip() if end > 0 else ""
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
                rules.append(r)
    rules.sort(key=lambda r: (r["saved"], r["slug"]))
    for i, r in enumerate(rules, 1):
        r["no"] = i
    return rules


def _memory_tool(*args):
    tool = os.path.join(_SELF_DIR, "javis_memory.py")
    p = subprocess.run([sys.executable, tool, "--dir", memory_dir()] + list(args),
                       capture_output=True, text=True, encoding="utf-8", timeout=30)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def rule_add(text):
    text = " ".join((text or "").split())
    if not text:
        return {"ok": False, "say": "저장할 지시 내용이 비어 있어요. 어떤 것을 앞으로 지키면 될지 한 줄로 알려 주세요."}
    for r in list_rules():
        if r["text"] == text:
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
    rules = list_rules()
    hit = None
    for r in rules:
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
    path = _todo_path()
    with Lock(path):
        data = load_todos()
        res = fn(data)
        _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    return res


def _anchor(it):
    """경과일 기준일 — 받은 날 · 「계속」 답한 날 · 미룸이 끝난 날 중 가장 늦은 것."""
    cands = [it.get("received")]
    if it.get("kept_on"):
        cands.append(it["kept_on"])
    if it.get("deferred_until"):
        cands.append(it["deferred_until"])
    return max(_dt.date.fromisoformat(c) for c in cands if c)


def is_open(it):
    return it.get("status") == "open"


def age_days(it, t=None):
    return ((t or today()) - _dt.date.fromisoformat(it["received"])).days


def todo_add(whats, urgent=(), short=(), notify=False):
    whats = [" ".join(w.split()) for w in whats if w and w.strip()]
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


def todo_done(tid, evidence):
    if not (evidence or "").strip():
        return {"ok": False, "say": "끝 표시에는 근거 한 줄이 필요해요(무엇을 했는지)."}
    holder = {}

    def f(data):
        it = _find(data, tid)
        if it is None:
            return None
        if it["status"] == "done":
            holder["already"] = True
            return it
        it.update(status="done", done_at=now_iso(), done_on=today().isoformat(), evidence=evidence.strip())
        return it

    it = _mutate(f)
    if it is None:
        return {"ok": False, "say": "#%s 번 일을 원장에서 찾지 못했어요." % tid}
    if holder.get("already"):
        return {"ok": True, "already": True, "say": "#%d 은 이미 끝 표시가 돼 있어요." % it["id"]}
    log_event("todo.done", id=it["id"], what=it["what"])
    res = {"ok": True, "id": it["id"], "say": "끝냈어요: #%d %s — %s" % (it["id"], it["what"], it["evidence"])}
    c = config()
    if (it.get("notify") or c["notify_all_done"]) and c["notify_channel"] != "off":
        res["notify"] = send_done_notice(it, c)
        if res["notify"].get("phone_pending"):
            # 모델이 이 JSON 을 읽는 그 자리에서 보내게 한다(안 보내면 Stop 훅이 1번 막는다).
            res["do_now"] = ("이어서 PushNotification 도구로 「%s」를 보내라 — 오너가 이 화면을 보고 있으면 Claude Code 가 "
                             "알아서 생략한다(그래도 이 호출은 한다). 보내기 전에 「폰 알림을 보냈다」고 말하지 마라."
                             % res["notify"]["push_message"])
    return res


def todo_answer(tid, kind, days=None, reason=""):
    def f(data):
        it = _find(data, tid)
        if it is None or it["status"] != "open":
            return None
        t = today()
        if kind == "keep":
            it["kept_on"] = t.isoformat()
        elif kind == "defer":
            it["deferred_until"] = (t + _dt.timedelta(days=days or 7)).isoformat()
        elif kind == "cancel":
            it.update(status="cancelled", cancelled_on=t.isoformat(), cancel_reason=reason)
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
    """밀린 일 보고(결정론) — 개수·가장 오래된 날·물어볼 일(사흘 넘음 · 미룸 기간 안이면 제외)."""
    t = t or today()
    data = load_todos()
    open_items = [it for it in data["items"] if is_open(it)]
    # 미룸 기간 안의 일은 기준일(_anchor)이 미룸 끝날이라 경과일이 음수 → 자연히 묻지 않는다.
    stale = [it for it in open_items if (t - _anchor(it)).days > STALE_DAYS]
    out = {"open": len(open_items), "stale": [{"id": it["id"], "what": it["what"],
                                               "days": age_days(it, t)} for it in stale]}
    if open_items:
        oldest = min(open_items, key=lambda it: (it["received"], it["id"]))
        out["oldest_days"] = age_days(oldest, t)
        out["oldest"] = {"id": oldest["id"], "what": oldest["what"], "received": oldest["received"]}
        out["say"] = "%s %d건 · 가장 오래된 것 받은 지 %d일(#%d %s)" % (
            BRIEF_MARK, len(open_items), out["oldest_days"], oldest["id"], oldest["what"])
    else:
        out["oldest_days"] = 0
        out["say"] = "%s 0건이에요." % BRIEF_MARK
    if stale:
        out["ask"] = ["#%d %s — 받은 지 %d일 됐어요. 계속할까요, 미룰까요, 취소할까요?" % (
            s["id"], s["what"], s["days"]) for s in out["stale"]]
    return out


def todos_say(items):
    if not items:
        return "적어 둔 열린 일이 없어요."
    t = today()
    return "\n".join("#%d %s (받은 지 %d일%s)" % (it["id"], it["what"], age_days(it, t),
                                                ", 끝나면 알림" if it.get("notify") else "") for it in items)


# ── ③ 끝나면 알림 ─────────────────────────────────────────────────────────────
def _cys_bin():
    for c in (os.environ.get("CYS_BIN"), "cys"):
        if c:
            return c
    return "cys"


def send_done_notice(it, c):
    """일 끝 사건에서 알림 1회 — 같은 일은 두 번 보내지 않는다(notified_on 표지 · 잠금 안에서 판정)."""
    title = "끝났어요: %s" % it["what"][:60]
    body = "#%d %s\n근거: %s" % (it["id"], it["what"], it.get("evidence", ""))
    first = {}

    def f(data):
        cur = _find(data, it["id"])
        if cur is None or cur.get("notified_at"):
            return
        cur["notified_at"] = now_iso()
        first["yes"] = True

    _mutate(f)
    if not first.get("yes"):
        return {"sent": False, "reason": "already-notified"}
    ch = c["notify_channel"]
    res = {"sent": True, "channel": ch}
    if ch in ("app", "both"):
        try:
            p = subprocess.run([_cys_bin(), "feed", "push", "--kind", "ceo-notice", "--title", title,
                                "--body", body], capture_output=True, text=True, timeout=10)
            res["app_rc"] = p.returncode
        except (OSError, subprocess.SubprocessError) as e:
            res["app_rc"] = -1
            res["app_error"] = str(e)[:200]
    if ch in ("phone", "both"):
        # 폰·바탕화면 푸시 = Claude Code 자체 PushNotification 도구(Remote Control 연결 시 폰까지) — 모델만 부를
        #   수 있다. 그래서 「보내야 함」을 원장에 남기고, Stop 훅이 이번 턴 안에 보냈는지(PostToolUse 기록) 대조한다.
        res["phone_pending"] = True
        res["push_message"] = "%s (#%d)" % (title, it["id"])
    log_event("notify.due", id=it["id"], channel=ch, phone=bool(res.get("phone_pending")),
              message=res.get("push_message", ""))
    return res


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


def _turn_path():
    d = os.path.join(owner_dir(), "turns")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "%s.json" % surface().replace("/", "_").replace(":", "_"))


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


def _cap(s, n):
    return s if len(s) <= n else s[:n - 20] + "\n…(이하 생략 — rule list)"


def _carry_path():
    d = os.path.join(owner_dir(), "carry")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "%s.json" % surface().replace("/", "_").replace(":", "_"))


def _carry_lines(carry, tl):
    """직전 오너 턴에서 넘어온 할 일 — 턴 끝에 막지 않고(막으면 답이 되풀이된다 · 11-18 실좌석 실측) 다음 턴에 싣는다."""
    out = []
    for txt in carry.get("saved_unshown", []):
        out.append("【직전 턴 확인 줄 누락 — 이번 답에 1줄】%s: 「%s」" % (SAVED_MARK, txt))
    for txt in carry.get("removed_unshown", []):
        out.append("【직전 턴 확인 줄 누락 — 이번 답에 1줄】%s: 「%s」" % (REMOVED_MARK, txt))
    if carry.get("second_look"):
        out.append("【직전 오너 입력 다시 보기 · owner-desk】직전 오너 입력 «%s» 에 앞으로 계속 지킬 지시나 맡긴 일·끝 알림 "
                   "부탁이 있었는데 기록하지 않았다면 이번 턴에 %s 로 기록하고 say 1줄을 보여라(없었으면 이 줄은 무시)."
                   % (carry["second_look"], tl))
    return out


def hook_session(hin):
    rules = list_rules()
    b = brief()
    tl = _tool_line()
    lines = ["■ 오너 책상(owner-desk) — 오너가 한 번 시킨 것을 잊지 않기 위한 기록이다. 도구 = %s" % tl]
    if rules:
        lines.append("■ 오너가 앞으로 계속 지키라고 한 지시 %d개(장기기억 · 이 대화에서도 그대로 지킨다):" % len(rules))
        lines += ["  %d. %s" % (r["no"], r["text"]) for r in rules]
    else:
        lines.append("■ 오너가 저장해 둔 지속 지시: 없음")
    lines.append("■ 오너 할 일 원장: %s" % b["say"])
    lines.append("■ 규약: 오너가 앞으로 계속 지킬 지시를 주면 그 턴 안에 `rule add --text` 로 저장하고 도구가 준 say 1줄"
                 "(「%s: …」)을 보인다 · 「그 규칙 지워」 = `rule remove <번호>` · 「기억하는 규칙 보여 줘」 = `rule list` · "
                 "오너가 일을 시키면 `todo add --what`(여럿이면 --what 여러 번 · 급한 것 --urgent N · 짧은 것 --short N) · "
                 "끝나면 `todo done <id> --evidence` · 「끝나면 알려 줘」 = `todo add … --notify`(늘 그렇게 = `notify set --all-done on`) · "
                 "끝 알림 기본 = 앱 알림 + 폰(PushNotification) · 오너가 카톡을 원하면 「컴퓨터 조작으로 카톡 보내기는 불안정할 수 "
                 "있어요」 1줄 안내 뒤 오너가 고르면 스킬 computer-control 길로 보낸다(새 로그인·외부 API 만들지 않음)."
                 % SAVED_MARK)
    # 순환(/clear·압축) 직전 턴에서 넘어온 것도 잃지 않는다(지우지는 않음 — 다음 오너 입력 훅이 싣고 지운다).
    lines += _carry_lines(_load_json(_carry_path(), {}), tl)
    return _ctx("SessionStart", _cap("\n".join(lines), SESSION_RULES_CAP + 1400))


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
    t = today().isoformat()
    b = brief()
    cp = _carry_path()
    carry = _load_json(cp, {})
    brief_due = (state.get("briefed_on") != t or carry.get("brief_missing")) and b["open"] > 0
    turn = {"start_ts": time.time(), "owner": True, "brief_due": brief_due,
            "briefed_on": t if brief_due else state.get("briefed_on"), "brief_say": b["say"] if brief_due else "",
            "prompt_excerpt": " ".join(prompt.split())[:300],
            "prompt_sha": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]}
    _atomic_write(tp, json.dumps(turn, ensure_ascii=False))
    tl = _tool_line()
    lines = []
    if brief_due:
        lines.append("【오늘 첫 오너 대화 — 답 첫 줄에 이 문장을 그대로 먼저 말한다】%s" % b["say"])
        for a in b.get("ask", []):
            lines.append("【사흘 넘은 일 — 오너에게 먼저 물어라】%s → 답에 따라 `todo keep|defer|cancel <id>`" % a)
    lines += _carry_lines(carry, tl)
    if carry:
        try:
            os.unlink(cp)
        except OSError:
            pass
    lines.append("【오너 지시 점검 · owner-desk】이 오너 입력에 ⑴앞으로 계속 지킬 지시(선호·습관·규칙)가 있으면 이 턴 안에 "
                 "%s rule add --text \"<지시>\" 로 저장하고 say 1줄(「%s: …」)을 보여라 ⑵새로 시킨 일이면 todo add "
                 "(여럿이면 순서를 정해 say 1줄로 알림) ⑶「끝나면 알려 줘」면 --notify(앞으로 늘 그렇게면 notify set --all-done on 도) ⑷일을 끝내면 todo done <id> --evidence. "
                 "판단은 낱말이 아니라 뜻으로 한다 · 일회성 부탁이나 잡담이면 아무것도 저장하지 않는다." % (tl, SAVED_MARK))
    return _ctx("UserPromptSubmit", _cap("\n".join(lines), PROMPT_CAP))


def _block(reason):
    return {"decision": "block", "reason": reason}


def hook_stop(hin):
    """턴 끝 안전망(11-18 실좌석 실측 반영).

    막는 것(decision=block)은 둘뿐이다 — ①「저장했습니다」라고 말했는데 저장 기록이 없음(거짓 확인 · 지금 고쳐야 한다)
    ②끝난 일의 폰 알림을 아직 안 보냄(도구 호출 1번이면 된다). 그 밖(저장했는데 확인 줄 누락 · 아침 보고 누락 · 이번 턴에
    기록이 하나도 없어 지속 지시를 놓쳤을 수 있음)은 **막지 않고 다음 오너 턴으로 넘긴다** — 막으면 모델이 「덧붙일 말 없음」
    으로 빈 답을 내고, 하네스가 보이는 답을 강요해 같은 답이 되풀이됐다(실측: 한 턴에 같은 표 3번).
    """
    tp = _turn_path()
    turn = _load_json(tp, {})
    if not turn.get("owner"):
        return None
    msg = hin.get("last_assistant_message") or ""
    ev = events_since(turn.get("start_ts", 0), surface())
    ops = [e.get("op") for e in ev]
    tl = _tool_line()
    carry = {}
    adds = [e.get("text", "") for e in ev if e.get("op") == "rule.add"]
    if adds and SAVED_MARK not in msg:
        carry["saved_unshown"] = adds
    rms = [e.get("text", "") for e in ev if e.get("op") == "rule.remove"]
    if rms and REMOVED_MARK not in msg:
        carry["removed_unshown"] = rms
    if turn.get("brief_due") and BRIEF_MARK not in msg:
        carry["brief_missing"] = True
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
    # 고리 방지: 한 오너 턴에서 막는 것은 최대 MAX_BLOCKS 번.
    if turn.get("blocks", 0) >= MAX_BLOCKS:
        return None
    reasons = []
    if SAVED_MARK in msg and not adds:
        reasons.append("답에 「%s」라고 했지만 이번 턴 저장 기록이 없다 — 지금 %s rule add --text \"…\" 로 실제로 "
                       "저장하거나, 저장하지 않았다면 그 문장을 바로잡아라(답 전체를 되풀이하지 말고 고친 1줄만)." % (SAVED_MARK, tl))
    due = [e for e in ev if e.get("op") == "notify.due" and e.get("phone")]
    sent = [e for e in ev if e.get("op") == "notify.phone"]
    if due and not sent:
        reasons.append("끝난 일 알림을 아직 폰으로 보내지 않았다 — PushNotification 도구로 「%s」를 보내라"
                       "(답을 되풀이하지 말고 「알림을 보냈어요」 1줄만)." % due[-1].get("message", ""))
    if reasons:
        turn["blocks"] = turn.get("blocks", 0) + 1
        _atomic_write(tp, json.dumps(turn, ensure_ascii=False))
        return _block("【owner-desk 대조】" + " / ".join(reasons))
    return None


def hook_posttool(hin):
    if (hin.get("tool_name") or "") == "PushNotification":
        log_event("notify.phone", message=str((hin.get("tool_input") or {}).get("message", ""))[:200])
    return None


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv=None):
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
            c = config()
            if a.act == "set":
                if a.channel:
                    c["notify_channel"] = a.channel
                if a.all_done:
                    c["notify_all_done"] = a.all_done == "on"
                if a.selfcheck:
                    c["selfcheck"] = a.selfcheck == "on"
                save_config(c)
                log_event("notify.set", channel=c["notify_channel"], all_done=c["notify_all_done"])
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
