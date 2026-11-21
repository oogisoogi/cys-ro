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
    # ① 규칙
    ("규칙 주입 0(세션 시작에 규칙 안 실음)", OW, '[(r["no"], "  %d. %s" % (r["no"], clean(r["text"], ITEM_CAP * 2))) for r in rules]', "[]"),
    ("규칙 파일명 접두 거름 제거", OW, 'if n.startswith("%s_%s" % (RULE_TYPE, RULE_PREFIX)) and n.endswith(".md"):',
     'if n.endswith(".md") and n != "MEMORY.md":'),
    ("중복 규칙 검사 제거", OW, 'if r["text"] == text:', "if False:"),
    ("중복 저장 확인 사건 미기록", OW, '            log_event("rule.add", slug=r["slug"], text=text, duplicate=True)\n', ""),
    ("제어 문자 정리 제거", OW, '_CTRL.sub(" ", s or "")', '(s or "")'),
    ("은퇴가 색인 줄을 안 지움", MEM, "kept = [ln for ln in lines if not _is_row_of(ln)]", "kept = list(lines)"),
    ("은퇴 색인 = 부분 문자열 일치", MEM, "return bool(m) and m.group(1) == fn", 'return ("(%s)" % fn) in ln'),
    ("은퇴가 본문 파일을 안 옮김", MEM, "            os.unlink(fpath)\n            try:\n                _write_text_atomic(index_path",
     "            try:\n                _write_text_atomic(index_path"),
    # ② 원장·아침 보고
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
    ("아침 보고 확인됨 무시", OW, '        if d.get("confirmed_on") == t:', "        if False:"),
    ("아침 보고 좌석 예약 무시", OW,
     'if not r or r.get("day") != t or r.get("by") == me or now - r.get("at", 0) > BRIEF_CLAIM_STALE:', "if True:"),
    ("아침 보고 확인 기록 제거", OW,
     '        _update_json(_brief_path(), {}, lambda d: d.update(confirmed_on=max(d.get("confirmed_on") or "", day)))', "        pass"),
    ("아침 보고 확인 날짜 후퇴 허용", OW, 'confirmed_on=max(d.get("confirmed_on") or "", day)', "confirmed_on=day"),
    ("보내는 중에도 안내 횟수 소진", OW, '            if it["id"] in ids and n.get("phone") == "pending" \\\n                    and time.time() - (n.get("phone_sending") or 0) >= PHONE_SENDING_STALE:',
     '            if it["id"] in ids and n.get("phone") == "pending":'),
    ("아침 보고 확인 날짜 = Stop 시점 오늘", OW, 'day = turn.get("brief_day") or today().isoformat()', "day = today().isoformat()"),
    # ③ 알림
    ("--notify 무시", OW, 'if (it.get("notify") or c["notify_all_done"]) and c["notify_channel"] != "off":',
     'if c["notify_all_done"] and c["notify_channel"] != "off":'),
    ("앱 알림 보내는 중 표지 제거(중복 발송)", OW, '                n["app"] = "claimed:%f" % t0\n', ""),
    ("앱 발송 실패도 sent 처리(재시도 0)", OW, '                n["app"] = "pending"\n                if ok is False:',
     '                n["app"] = "sent"\n                if ok is False:'),
    ("앱 알림 시간 상한 제거", OW, "        if remaining < 1.0:", "        if False:"),
    ("발송 timeout 고정(남은 시간 무시)", OW, "timeout=remaining,", "timeout=5,"),
    ("앱 알림 request-id 빠짐", OW, '"--request-id", _request_id(c["event"])],', "],"),
    ("데몬 중복 거절을 실패로 셈", OW, '"duplicate request_id" in ((p.stdout', '"__never__" in ((p.stdout'),
    ("앱 알림 재시도 0(훅에서 flush 안 함)", OW, "    flush_app_notices()                                     # 보내다 실패한 앱 알림 재시도\n    t = today()",
     "    t = today()"),
    ("제목 속 (#번호)로 닫음(끝 번호 아님)", OW, '_TRAIL_ID = re.compile(r"\\(#(\\d+)\\)\\s*$")',
     '_TRAIL_ID = re.compile(r"\\(#(\\d+)\\)")'),
    ("발송 경로 중복 거절 제거", OW, '        if st == "sent" or (now - sending) < PHONE_SENDING_STALE:', "        if False:"),
    ("포기 뒤 늦은 성공 불인정", OW, 'PHONE_OPEN = ("pending", "unsent", "present"', 'PHONE_OPEN = ("pending", "present"'),
    ("압축(compact)에도 턴 정산", OW, '    if hin.get("source") != "compact":\n        settle_turn', "    if True:\n        settle_turn"),
    ("폰 좌석 표지 무시", OW, 'if not cl or cl.get("by") == me or now - cl.get("at", 0) > PHONE_CLAIM_STALE:', "if True:"),
    ("폰 미발송 포기 없음", OW,
     'if n.get("phone") == "pending" and n.get("phone_reminders", 0) >= PHONE_REMINDERS \\\n'
     '                    and time.time() - (n.get("phone_sending") or 0) >= PHONE_SENDING_STALE:', "if False:"),
    ("폰 안내 횟수 = 실리지 않은 것도 셈", OW, 'bump_phone_reminders(set(emitted["phone"]))',
     'bump_phone_reminders(set(p["id"] for p in phones))'),
    ("PushNotification 결과 정산 제거", OW, "        ids = settle_phone(msg, resp)", "        ids = []"),
    ("훅이 도구 결과를 안 넘김", OW, "ids = settle_phone(msg, resp)", "ids = settle_phone(msg, None)"),
    ("도구 결과 무시(늘 sent)", OW, "outcome, why = phone_outcome(response)", 'outcome, why = "sent", None'),
    ("pushSent 무시", OW, 'r.get("pushSent") is True or r.get("localSent") is True', 'r.get("localSent") is True'),
    ("localSent 무시", OW, 'r.get("pushSent") is True or r.get("localSent") is True', 'r.get("pushSent") is True'),
    ("참 비슷한 값도 보냄으로", OW, 'r.get("pushSent") is True or r.get("localSent") is True', 'r.get("pushSent") or r.get("localSent")'),
    ("화면 앞 = sent", OW, 'return "present", why', 'return "sent", None'),
    ("화면 앞 갈래 제거", OW, 'if why == "user_present":', "if False:"),
    ("no_transport 갈래 빠짐", OW, 'if why in ("no_transport", "config_off"):', 'if why in ("config_off",):'),
    ("config_off 갈래 빠짐", OW, 'if why in ("no_transport", "config_off"):', 'if why in ("no_transport",):'),
    ("모르는 결과 = sent", OW, 'return "unknown", None', 'return "sent", None'),
    ("결과 뒤 표지 안 내림", OW, '            n.pop("phone_sending", None)\n            if outcome == "sent":', '            if outcome == "sent":'),
    ("못 보낸 것에도 보낸 시각", OW, 'if outcome == "sent":\n                n["phone_sent_at"]', 'if True:\n                n["phone_sent_at"]'),
    ("sent 되돌림 허용", OW, 'PHONE_OPEN = ("pending",', 'PHONE_OPEN = ("sent", "pending",'),
    ("사유 기록 제거", OW, '            n["phone_reason"] = why\n', ""),
    ("못 보냄 안내 제거", OW, '("phone_told", phone_to_tell(), ', '("phone_told", [], '),
    ("확인 불가 안내 빠짐", OW, 'n.get("phone") in ("undelivered", "unknown") and not n.get("phone_told")', 'n.get("phone") in ("undelivered",) and not n.get("phone_told")'),
    ("안내 사유 구분 없음", OW, 'PHONE_NOT_SENT_SAY.get(n.get("phone_reason"), PHONE_UNKNOWN_SAY)', "PHONE_UNKNOWN_SAY"),
    ("안내 말함 기록 제거", OW, '    mark_phone_told(set(emitted["phone_told"]))\n', ""),
    ("못 실은 안내까지 말함", OW, 'mark_phone_told(set(emitted["phone_told"]))', "mark_phone_told(set(k for k, _ in phone_to_tell()))"),
    # 훅·안전망
    ("출력 상한 검사 제거", OW, "if dropped or used + add + 160 > HOOK_JSON_CAP:", "if False:"),
    ("못 실은 이월까지 소비", OW, 'shown = set(emitted["carry"])', "shown = set(range(len(carry_items)))"),
    ("기계 입력 판별 제거", OW, "if not prompt.strip() or is_machine(prompt):", "if not prompt.strip():"),
    ("하위 에이전트 거름 제거(입력 훅)", OW, '    if hin.get("agent_id"):\n        return None\n    prompt = hin.get("prompt")',
     '    prompt = hin.get("prompt")'),
    ("끊긴 턴 정산 제거", OW, "    settle_turn(state)                                      # 직전 오너 턴(끊긴 턴 포함) 정산 → 이월\n", ""),
    ("거짓 확인 막기 제거", OW, "if SAVED_MARK in msg and not evidence:", "if False:"),
    ("이월 확인 줄을 근거로 불인정", OW, 'evidence = [e for e in ev if e.get("op") == "rule.add"] or turn.get("carried_saved")',
     'evidence = [e for e in ev if e.get("op") == "rule.add"]'),
    ("턴 안 「보였다」 기록 제거", OW, '    if SAVED_MARK in msg:\n        turn["saved_shown"] = True\n', ""),
    ("폰 알림 미발송 막기 제거", OW, "        mine = claim_phone()\n        if mine:", "        mine = claim_phone()\n        if False:"),
    ("다시 보기 이월 제거", OW, '        items.append({"k": "second", "text": turn.get("prompt_excerpt", "")})', "        pass"),
    ("확인 줄 누락 이월 제거", OW, '        items += [{"k": "saved", "text": x} for x in adds]', "        pass"),
    ("고리 상한 제거", OW, 'if turn.get("blocks", 0) < MAX_BLOCKS:', "if True:"),
    ("자식 javis_memory UTF-8 고정 제거", OW, 'env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")',
     "env = dict(os.environ)"),
    ("역할 가드 제거(셸)", SH, '[ "${CYS_ROLE:-}" = "master" ] || exit 0', ":"),
    ("C28 등록에서 Stop 빠짐", PF, '("UserPromptSubmit", None), ("Stop", None),\n                       ("PreToolUse", "PushNotification")',
     '("UserPromptSubmit", None),\n                       ("PreToolUse", "PushNotification")'),
    ("C28 등록에서 PreToolUse 빠짐", PF, '("PreToolUse", "PushNotification"), ("PostToolUse", "PushNotification")]),',
     '("PostToolUse", "PushNotification")]),'),
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
            try:
                # -f = 첫 실패에서 멈춤(판정은 rc 그대로 · 잡힌 뮤턴트의 남은 시험 시간을 아낀다).
                p = subprocess.run([sys.executable, TEST, "-f"], capture_output=True, text=True, timeout=900)
                killed = p.returncode != 0
            except subprocess.TimeoutExpired:
                killed = "timeout"                          # 시험이 끝나지 않음 = 정상본과 다르게 움직임(따로 표시)
        finally:
            with open(path, "wb") as f:
                f.write(orig)
        print("%s %s" % ("KILLED(timeout)" if killed == "timeout" else ("KILLED  " if killed else "SURVIVED"), name),
              flush=True)
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
