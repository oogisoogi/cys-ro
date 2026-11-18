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
    ("규칙 주입 0(세션 시작에 규칙 안 실음)", OW, 'lines += ["  %d. %s" % (r["no"], r["text"]) for r in rules]', "pass"),
    ("규칙 파일명 접두 거름 제거", OW, 'if n.startswith("%s_%s" % (RULE_TYPE, RULE_PREFIX)) and n.endswith(".md"):',
     'if n.endswith(".md") and n != "MEMORY.md":'),
    ("중복 규칙 검사 제거", OW, 'if r["text"] == text:', "if False:"),
    ("은퇴가 색인 줄을 안 지움", MEM, 'kept = [ln for ln in index_text.splitlines(True) if ("(%s)" % fn) not in ln]',
     "kept = index_text.splitlines(True)"),
    ("은퇴가 본문 파일을 안 옮김", MEM, "            os.unlink(fpath)\n            try:\n                _write_text_atomic(index_path",
     "            try:\n                _write_text_atomic(index_path"),
    ("사흘 경계 > → >=", OW, "(t - _anchor(it)).days > STALE_DAYS", "(t - _anchor(it)).days >= STALE_DAYS"),
    ("미룸 기준일 무시", OW, '    if it.get("deferred_until"):\n        cands.append(it["deferred_until"])\n', ""),
    ("계속 답 기준일 무시", OW, '    if it.get("kept_on"):\n        cands.append(it["kept_on"])\n', ""),
    ("가장 오래된 일 = 마지막 일", OW, 'oldest = min(open_items, key=lambda it: (it["received"], it["id"]))',
     'oldest = max(open_items, key=lambda it: (it["received"], it["id"]))'),
    ("끝난 일도 밀린 일로 셈", OW, 'open_items = [it for it in data["items"] if is_open(it)]',
     'open_items = [it for it in data["items"] if it.get("status") != "cancelled"]'),
    ("알림 중복 표지 무시", OW, 'if cur is None or cur.get("notified_at"):', "if cur is None:"),
    ("--notify 무시", OW, 'if (it.get("notify") or c["notify_all_done"]) and c["notify_channel"] != "off":',
     'if c["notify_all_done"] and c["notify_channel"] != "off":'),
    ("순서 = 받은 순서(급한·짧은 무시)", OW, 'order = sorted(made, key=lambda x: (not x["urgent"], not x["short"], x["id"]))',
     "order = made"),
    ("아침 보고 하루 1회 표지 무시", OW, 'brief_due = (state.get("briefed_on") != t or carry.get("brief_missing")) and b["open"] > 0',
     'brief_due = b["open"] > 0'),
    ("아침 보고 누락 이월 제거", OW, '        carry["brief_missing"] = True\n', "        pass\n"),
    ("기계 입력 판별 제거", OW, "if not prompt.strip() or is_machine(prompt):", "if not prompt.strip():"),
    ("거짓 확인 막기 제거", OW, "if SAVED_MARK in msg and not adds:", "if False:"),
    ("폰 알림 미발송 막기 제거", OW, "if due and not sent:", "if False:"),
    ("다시 보기 이월 제거", OW, '        carry["second_look"] = turn.get("prompt_excerpt", "")\n', "        pass\n"),
    ("확인 줄 누락 이월 제거", OW, '        carry["saved_unshown"] = adds\n', "        pass\n"),
    ("이월을 실은 뒤 안 지움", OW, "    if carry:\n        try:\n            os.unlink(cp)", "    if False:\n        try:\n            os.unlink(cp)"),
    ("고리 상한 제거", OW, 'if turn.get("blocks", 0) >= MAX_BLOCKS:', "if False:"),
    ("PushNotification 보냄 기록 제거", OW, '        log_event("notify.phone",', '        (lambda *a, **k: None)("notify.phone",'),
    ("역할 가드 제거(셸)", SH, '[ "${CYS_ROLE:-}" = "master" ] || exit 0', ":"),
    ("하위 에이전트 거름 제거(셸)", SH, "  *'\"agent_id\"'*) exit 0 ;;", "  *'\"agent_id_never\"'*) exit 0 ;;"),
    ("C28 등록에서 Stop 빠짐", PF, '("UserPromptSubmit", None), ("Stop", None),\n                       ("PostToolUse", "PushNotification")',
     '("UserPromptSubmit", None),\n                       ("PostToolUse", "PushNotification")'),
]


def main():
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
