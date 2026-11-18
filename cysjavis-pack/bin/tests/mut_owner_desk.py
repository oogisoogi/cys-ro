#!/usr/bin/env python3
"""TICKET=cysr-owner-memory-todo-1118 — 오너 책상 뮤턴트 하네스(핵심 줄을 되돌리면 test_owner_desk 가 붉어야 한다).

⚠ 편집 중인 작업 사본에서 돌리지 마라 — 뮤턴트마다 파일을 바꿨다가 원래 바이트로 되돌리지만, 도중에 끊기면 그 사본이
뮤턴트 상태로 남는다. 별도 작업트리(`git worktree add --detach <임시> HEAD`)에서 `python3 cysjavis-pack/bin/tests/mut_owner_desk.py`.
판정 토큰: 전부 잡히면 `MUTANTS ALL-KILLED`(exit 0) · 살아남은 뮤턴트가 있으면 이름을 찍고 exit 1.
"""
import os
import subprocess
import sys

PACK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST = os.path.join(PACK, "bin", "tests", "test_owner_desk.py")
OW = "bin/javis_owner.py"
MEM = "bin/javis_memory.py"
PF = "bin/javis_preflight.py"
SH = "hooks/owner-desk.sh"

MUTANTS = [
    ("규칙 주입 0(세션 시작에 규칙 안 실음)", OW, 'optional = ["  %d. %s" % (r["no"], clean(r["text"], ITEM_CAP * 2)) for r in rules]',
     "optional = []"),
    ("규칙 파일명 접두 거름 제거", OW, 'if n.startswith("%s_%s" % (RULE_TYPE, RULE_PREFIX)) and n.endswith(".md"):',
     'if n.endswith(".md") and n != "MEMORY.md":'),
    ("중복 규칙 검사 제거", OW, 'if r["text"] == text:', "if False:"),
    ("중복 저장 확인 사건 미기록", OW, '            log_event("rule.add", slug=r["slug"], text=text, duplicate=True)\n', ""),
    ("제어 문자 정리 제거", OW, '_CTRL.sub(" ", s or "")', '(s or "")'),
    ("은퇴가 색인 줄을 안 지움", MEM, "kept = [ln for ln in lines if not _is_row_of(ln)]", "kept = list(lines)"),
    ("은퇴 색인 = 부분 문자열 일치", MEM, "return bool(m) and m.group(1) == fn", 'return ("(%s)" % fn) in ln'),
    ("은퇴가 본문 파일을 안 옮김", MEM, "            os.unlink(fpath)\n            try:\n                _write_text_atomic(index_path",
     "            try:\n                _write_text_atomic(index_path"),
    ("사흘 경계 > → >=", OW, "return (t - anchor).days > STALE_DAYS", "return (t - anchor).days >= STALE_DAYS"),
    ("미룬 날 무시", OW, "    if du:\n        return t >= _dt.date.fromisoformat(du)\n", ""),
    ("계속 답 기준일 무시", OW, '(it.get("received"), it.get("kept_on"))', '(it.get("received"),)'),
    ("계속이 미룸을 안 풂", OW, '            it.pop("deferred_until", None)', "            pass"),
    ("가장 오래된 일 = 마지막 일", OW, 'oldest = min(open_items, key=lambda it: (it["received"], it["id"]))',
     'oldest = max(open_items, key=lambda it: (it["received"], it["id"]))'),
    ("끝난 일도 밀린 일로 셈", OW, 'open_items = [it for it in data["items"] if is_open(it)]',
     'open_items = [it for it in data["items"] if it.get("status") != "cancelled"]'),
    ("순서 = 받은 순서(급한·짧은 무시)", OW, 'order = sorted(made, key=lambda x: (not x["urgent"], not x["short"], x["id"]))',
     "order = made"),
    ("--notify 무시", OW, 'if (it.get("notify") or c["notify_all_done"]) and c["notify_channel"] != "off":',
     'if c["notify_all_done"] and c["notify_channel"] != "off":'),
    ("앱 알림 보내는 중 표지 제거(중복 발송)", OW, '                n["app"] = "claimed:%f" % now\n', ""),
    ("앱 발송 실패도 sent 처리(재시도 0)", OW, '                    n["app"] = "pending"\n                    n["app_attempts"]',
     '                    n["app"] = "sent"\n                    n["app_attempts"]'),
    ("앱 알림 재시도 0(훅에서 flush 안 함)", OW, "    flush_app_notices()                                     # 보내다 실패한 앱 알림 재시도\n    t = today()",
     "    t = today()"),
    ("폰 의무를 번호 없이 전부 닫음", OW, 'ids = set(int(x) for x in re.findall(r"\\(#(\\d+)\\)", message or ""))',
     'ids = set(it["id"] for it in load_todos()["items"])'),
    ("폰 미발송 포기 없음", OW, 'if n["phone_reminders"] > PHONE_REMINDERS:', "if False:"),
    ("PushNotification 보냄 기록 제거", OW, "        ids = mark_phone_sent(msg)", "        ids = []"),
    ("아침 보고 하루 1회 확인 무시", OW, 'brief_due = _load_json(_brief_path(), {}).get("confirmed_on") != t and b["open"] > 0',
     'brief_due = b["open"] > 0'),
    ("아침 보고 확인 기록 제거", OW, "        _update_json(_brief_path(), {}, lambda d: d.update(confirmed_on=t))", "        pass"),
    ("출력 상한 검사 제거", OW, "if used + add + 80 > HOOK_JSON_CAP:", "if False:"),
    ("기계 입력 판별 제거", OW, "if not prompt.strip() or is_machine(prompt):", "if not prompt.strip():"),
    ("거짓 확인 막기 제거", OW, "if SAVED_MARK in msg and not evidence:", "if False:"),
    ("이월 확인 줄을 근거로 불인정", OW, 'evidence = ops.count("rule.add") or turn.get("carried_saved")',
     'evidence = ops.count("rule.add")'),
    ("폰 알림 미발송 막기 제거", OW, "    pend = phone_pending()\n    if pend:", "    pend = phone_pending()\n    if False:"),
    ("다시 보기 이월 제거", OW, '        carry["second_look"] = turn.get("prompt_excerpt", "")\n', "        pass\n"),
    ("확인 줄 누락 이월 제거", OW, '        carry["saved_unshown"] = adds\n', "        pass\n"),
    ("이월을 실은 뒤 안 지움", OW, "    if carry:                                               # 실은 이월만 지운다",
     "    if False:"),
    ("고리 상한 제거", OW, 'if turn.get("blocks", 0) >= MAX_BLOCKS:', "if False:"),
    ("자식 javis_memory UTF-8 고정 제거", OW, 'env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")',
     "env = dict(os.environ)"),
    ("역할 가드 제거(셸)", SH, '[ "${CYS_ROLE:-}" = "master" ] || exit 0', ":"),
    ("하위 에이전트 거름 제거(셸)", SH, "  *'\"agent_id\"'*) exit 0 ;;", "  *'\"agent_id_never\"'*) exit 0 ;;"),
    ("C28 등록에서 Stop 빠짐", PF, '("UserPromptSubmit", None), ("Stop", None),\n                       ("PostToolUse", "PushNotification")',
     '("UserPromptSubmit", None),\n                       ("PostToolUse", "PushNotification")'),
]


def main():
    # 기준선 먼저: 정상본이 초록이 아니면 「붉음 = 뮤턴트 검출」 판정이 무의미하다(codex 1R 논쟁점).
    base = subprocess.run([sys.executable, TEST], capture_output=True, text=True, timeout=600)
    if base.returncode != 0:
        print("BASELINE-RED — 정상본 시험이 붉다(뮤턴트 판정 불가)\n" + base.stderr[-2000:])
        return 2
    survived, missing = [], []
    for name, rel, old, new in MUTANTS:
        path = os.path.join(PACK, rel)
        with open(path, "rb") as f:
            orig = f.read()
        text = orig.decode("utf-8")
        if text.count(old) != 1:
            missing.append("%s (%s · 일치 %d)" % (name, rel, text.count(old)))
            continue
        try:
            with open(path, "wb") as f:
                f.write(text.replace(old, new).encode("utf-8"))
            p = subprocess.run([sys.executable, TEST], capture_output=True, text=True, timeout=600)
            killed = p.returncode != 0
        finally:
            with open(path, "wb") as f:
                f.write(orig)
        print("%s %s" % ("KILLED  " if killed else "SURVIVED", name), flush=True)
        if not killed:
            survived.append(name)
    for m in missing:
        print("NO-MATCH %s" % m)
    if survived or missing:
        print("MUTANTS SURVIVED %d · NO-MATCH %d / %d" % (len(survived), len(missing), len(MUTANTS)))
        return 1
    print("MUTANTS ALL-KILLED %d/%d" % (len(MUTANTS), len(MUTANTS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
