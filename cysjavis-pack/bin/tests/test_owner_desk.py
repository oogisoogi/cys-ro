#!/usr/bin/env python3
"""TICKET=cysr-owner-memory-todo-1118 — 오너 책상(한 번 시킨 것은 잊지 않고, 시킨 일은 밀리지 않게).

워크숍 참가자 사용기(11-18): ① 한 번 시킨 것(깔끔한 화면 · 끝나면 알림)을 자꾸 까먹는다 ② 아침에 여러 일을 시키면
쌓여 일주일째 밀린다. 수리 = bin/javis_owner.py + hooks/owner-desk.sh(+ javis_memory retire · preflight C28 등록).

재현 축(수리 전 = 도구·훅 부재로 전부 붉음 · 뒤 = 초록):
  R1 지속 지시 → 저장 → 대화 순환(/clear 흉내 = 새 SessionStart source=clear) 뒤 새 대화 주입에 그 규칙이 있다 ·
     지우면 빠진다 · 목록 질문에 번호 목록
  R2 오너 일 3건 등록 · 하나 완료 → 다음 날 첫 오너 대화에 「밀린 일 2건 · 가장 오래된 것 받은 지 n일」
  R3 사흘 넘은 일 → 묻는 줄(계속/미룸/취소) · 사흘째는 아직 안 묻는다 · 미룸 기간 안이면 안 묻는다
  R4 끝 알림 = 일 끝 사건에서 앱 알림 1회(같은 일 두 번 끝 표시해도 중복 0) · 폰 길은 미발송이면 Stop 이 막는다
  R5 턴 끝 안전망 = 거짓 확인(말했는데 기록 없음)은 막고 · 확인 줄 누락·아침 보고 누락·기록 0건 턴은 다음 오너 턴(및
     순환 뒤 새 대화)으로 이월(다시 보기) · 고리 상한
  R6 역할 가드(master 외 무출력) · 기계 입력(라벨 [wakeup])엔 점검 줄 0 · 하위 에이전트 사건 0
  R7 C28 등록표에 네 사건 · 안쪽 상한 < 하네스 선언 · 윈 경로(USERPROFILE·역슬래시)에서도 원장 위치가 홈 아래
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

PACK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(PACK, "bin", "javis_owner.py")
SH = os.path.join(PACK, "hooks", "owner-desk.sh")
sys.path.insert(0, os.path.join(PACK, "bin"))

# PushNotification 의 PostToolUse tool_response. 실물 표본 = Claude Code 2.1.327 격리 좌석 기록(11-18 · message 만 짧게 바꿈).
PRESENT = {"message": "m", "pushSent": False, "localSent": False, "disabledReason": "user_present", "sentAt": "2026-11-18T11:41:03.420Z"}
NO_TRANSPORT = {"message": "m", "pushSent": False, "localSent": False, "disabledReason": "no_transport", "sentAt": "2026-11-18T11:41:09.375Z"}
# 실물을 얻을 수 없는 갈래 = 설치본 2.1.327 PushNotification 코드의 반환 모양(폰 실제 발송·RC 연결이 필요해 실물 미검증).
CONFIG_OFF = {"message": "m", "pushSent": False, "localSent": False, "disabledReason": "config_off", "sentAt": "2026-11-18T11:41:09.375Z"}
PUSHED = {"message": "m", "pushSent": True, "localSent": False, "sentAt": "2026-11-18T11:41:09.375Z"}
LOCAL_ONLY = {"message": "m", "pushSent": False, "localSent": True, "disabledReason": "no_transport", "sentAt": "2026-11-18T11:41:09.375Z"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="owner-desk-")
        self.home = os.path.join(self.tmp, "home")
        self.pack = os.path.join(self.tmp, "pack")
        os.makedirs(os.path.join(self.pack, "memory"))
        os.makedirs(self.home)
        with open(os.path.join(self.pack, "memory", "MEMORY.md"), "w", encoding="utf-8") as f:
            f.write("# MEMORY\n")
        self.feedlog = os.path.join(self.tmp, "feed.log")
        self.failflag = os.path.join(self.tmp, "fail-feed-once")
        fake = os.path.join(self.tmp, "fake-cys")
        with open(fake, "w") as f:
            f.write('#!/bin/sh\nif [ -f "%s" ]; then rm -f "%s"; exit 1; fi\n'
                    'if [ -f "%s.dup" ]; then echo "duplicate request_id" >&2; exit 1; fi\n'
                    # 느린 데몬 흉내 = exec 로 셸을 갈아 끼운다(발송 timeout 이 잡을 프로세스가 곧 이것 · 고아 sleep 0)
                    'if [ -n "$FAKE_CYS_SLOW" ]; then exec "%s" -c "import sys,time; time.sleep(float(sys.argv[1])); '
                    'open(sys.argv[2], \'a\').write(sys.argv[3] + chr(10))" "$FAKE_CYS_SLOW" "%s" "$*"; fi\n'
                    'printf "%%s\\n" "$*" >> "%s"\n'
                    % (self.failflag, self.failflag, self.failflag, sys.executable, self.feedlog, self.feedlog))
        os.chmod(fake, 0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("CYS_", "AITERM_", "JAVIS_"))}
        self.env.update(HOME=self.home, CYS_PACK_DIR=self.pack, CYS_OWNER_DIR=os.path.join(self.home, ".cys", "owner"),
                        CYS_SURFACE_ID="7", CYS_ROLE="master", CYS_BIN=fake, CYS_PY=sys.executable,
                        CYS_STATE_DIR=os.path.join(self.home, ".cys", "state"), CYS_OWNER_TODAY="2026-11-18")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tool(self, *args, day=None):
        env = dict(self.env)
        if day:
            env["CYS_OWNER_TODAY"] = day
        p = subprocess.run([sys.executable, TOOL] + list(args), capture_output=True, text=True, env=env, timeout=60)
        return json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {"rc": p.returncode, "err": p.stderr}

    def hook(self, payload, day=None, role="master", arg=None):
        env = dict(self.env, CYS_ROLE=role)
        if day:
            env["CYS_OWNER_TODAY"] = day
        cmd = ["sh", SH] + ([arg] if arg else [])
        p = subprocess.run(cmd, input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True,
                           env=env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else None

    def py(self, code, **env):
        e = dict(self.env, **env)
        p = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import javis_owner as o\n"
                            % os.path.join(PACK, "bin") + code], capture_output=True, text=True, env=e)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.strip()

    def ctx(self, out):
        return (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")

    def feeds(self):
        try:
            return [ln for ln in open(self.feedlog, encoding="utf-8").read().splitlines() if ln.startswith("feed push")]
        except OSError:
            return []


class R1Rules(Base):
    def test_rule_survives_cycle_and_can_be_removed(self):
        r = self.tool("rule", "add", "--text", "결과는 항상 표로 깔끔하게 보여 줘")
        self.assertTrue(r["ok"], r)
        self.assertIn("이렇게 저장했습니다", r["say"])
        # 대화 순환(/clear) 흉내 = 새 세션의 SessionStart(source=clear) — 새 대화 주입에 그 규칙이 있어야 한다.
        for src in ("clear", "startup", "resume", "compact"):
            c = self.ctx(self.hook({"hook_event_name": "SessionStart", "source": src, "session_id": "new"}))
            self.assertIn("결과는 항상 표로 깔끔하게 보여 줘", c, src)
        # 저장은 기존 장기기억(javis_memory) 형식 — 색인 1줄 + 파일 · verify 정합.
        idx = open(os.path.join(self.pack, "memory", "MEMORY.md"), encoding="utf-8").read()
        self.assertIn("결과는 항상 표로 깔끔하게 보여 줘", idx)
        v = subprocess.run([sys.executable, os.path.join(PACK, "bin", "javis_memory.py"), "--dir",
                            os.path.join(self.pack, "memory"), "verify"], capture_output=True, text=True)
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
        # 같은 지시 두 번 = 중복 저장 0.
        r2 = self.tool("rule", "add", "--text", "결과는  항상 표로 깔끔하게 보여 줘")
        self.assertTrue(r2.get("duplicate"), r2)
        self.tool("rule", "add", "--text", "일이 끝나면 알려 줘")
        lst = self.tool("rule", "list")
        self.assertEqual(len(lst["rules"]), 2)
        self.assertRegex(lst["say"], r"1\. .*\n2\. ")
        no = [x["no"] for x in lst["rules"] if x["text"].startswith("결과는")][0]
        rm = self.tool("rule", "remove", str(no))
        self.assertTrue(rm["ok"], rm)
        self.assertIn("이렇게 지웠습니다", rm["say"])
        c = self.ctx(self.hook({"hook_event_name": "SessionStart", "source": "clear"}))
        self.assertNotIn("표로 깔끔하게", c)
        self.assertIn("일이 끝나면 알려 줘", c)
        # 은퇴 = 물리 삭제 아님(.retired 로 이동 · 색인에서 빠짐).
        retired = os.listdir(os.path.join(self.pack, "memory", ".retired"))
        self.assertEqual(len(retired), 1)
        self.assertNotIn("표로 깔끔하게", open(os.path.join(self.pack, "memory", "MEMORY.md"), encoding="utf-8").read())

    def test_other_memories_are_not_owner_rules(self):
        subprocess.run([sys.executable, os.path.join(PACK, "bin", "javis_memory.py"), "--dir",
                        os.path.join(self.pack, "memory"), "add", "--type", "feedback", "--name", "seat-tip",
                        "--desc", "좌석 기술 메모", "--body", "기술 메모 본문"], capture_output=True, env=self.env)
        self.tool("rule", "add", "--text", "항상 존댓말")
        self.assertEqual([r["text"] for r in self.tool("rule", "list")["rules"]], ["항상 존댓말"])
        self.assertNotIn("좌석 기술 메모", self.ctx(self.hook({"hook_event_name": "SessionStart", "source": "clear"})))

    def test_rules_block_fits_hook_cap(self):
        for i in range(80):
            self.tool("rule", "add", "--text", "규칙 %02d " % i + "가" * 150)
        self.tool("rule", "add", "--text", "제어문자" + "\x01" * 3000)
        out = self.hook({"hook_event_name": "SessionStart", "source": "clear"})
        self.assertLessEqual(len(json.dumps(out, ensure_ascii=False)), 9500)   # 직렬화 뒤 길이(codex 1R #5)
        c = self.ctx(out)
        self.assertIn("■ 규약:", c)                    # 규약은 목록에 밀려 잘리지 않는다
        self.assertIn("computer-control 길로 보낸다", c)   # 규약 줄 자체도 끝까지
        self.assertIn("  1. 규칙 00 ", c)               # 번호 = 저장한 순서
        self.assertIn("…외", c)                        # 넘친 규칙은 개수로 고지
        self.assertNotIn("\\u0001", json.dumps(out))

    def test_control_chars_are_cleaned(self):
        self.tool("rule", "add", "--text", "짧은\x01\x02규칙")
        out = self.hook({"hook_event_name": "SessionStart", "source": "clear"})
        self.assertIn("짧은 규칙", self.ctx(out))
        self.assertNotIn("\\u0001", json.dumps(out, ensure_ascii=False))


class R2R3Backlog(Base):
    def test_backlog_next_day_and_stale_ask(self):
        self.tool("todo", "add", "--what", "주보 만들기", day="2026-11-10")
        self.tool("todo", "add", "--what", "회계 정리", day="2026-11-15")
        self.tool("todo", "add", "--what", "사진 정리", day="2026-11-17")
        d = self.tool("todo", "done", "3", "--evidence", "앨범 폴더 정리 완료", day="2026-11-17")
        self.assertTrue(d["ok"], d)
        # 다음 날 첫 오너 대화
        out = self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "좋은 아침이에요"}, day="2026-11-18")
        c = self.ctx(out)
        self.assertIn("밀린 일 2건 · 가장 오래된 것 받은 지 8일(#1 주보 만들기)", c)
        # R3: 8일 = 묻는다 · 3일째(11-15 → 11-18 = 3일)는 아직 안 묻는다(「사흘 넘은」).
        self.assertIn("#1 주보 만들기 — 받은 지 8일", c)
        self.assertNotIn("#2 회계 정리 — 받은", c)
        # 보고를 말한 뒤(Stop 확인) 같은 날 두 번째 오너 대화엔 아침 보고 없음 — 다른 마스터 좌석에서도(오너 전체 1번).
        self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 2건 · …"}, day="2026-11-18")
        self.env["CYS_SURFACE_ID"] = "8"
        c2 = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "그리고 하나 더"}, day="2026-11-18"))
        self.assertNotIn("밀린 일 2건", c2)
        self.assertIn("오너 지시 점검", c2)
        # 하루 더 지나면 #2 도 사흘 넘음(4일).
        b = self.tool("todo", "brief", day="2026-11-19")
        self.assertEqual([s["id"] for s in b["stale"]], [1, 2])

    def test_keep_defer_cancel(self):
        self.tool("todo", "add", "--what", "A", "--what", "B", "--what", "C", day="2026-11-01")
        self.tool("todo", "keep", "1", day="2026-11-18")
        d = self.tool("todo", "defer", "2", "--days", "5", day="2026-11-18")
        self.assertIn("2026-11-23 에 다시 여쭐게요", d["say"])
        self.tool("todo", "cancel", "3", "--reason", "필요 없어짐", day="2026-11-18")
        b = self.tool("todo", "brief", day="2026-11-19")
        self.assertEqual(b["open"], 2)
        self.assertEqual(b["stale"], [])
        b = self.tool("todo", "brief", day="2026-11-22")   # 계속(11-18)+4일 = 사흘 넘음 → 묻고, 미룸(11-23)은 아직
        self.assertEqual([s["id"] for s in b["stale"]], [1])
        b = self.tool("todo", "brief", day="2026-11-23")   # 미룬 날이 되면 바로 묻는다(말한 날짜 그대로 · codex 1R)
        self.assertEqual([s["id"] for s in b["stale"]], [1, 2])
        # 「계속」은 미룸을 푼다 — 지금부터 다시 센다
        self.tool("todo", "add", "--what", "D", day="2026-11-01")
        self.tool("todo", "defer", "4", "--days", "30", day="2026-11-18")
        self.tool("todo", "keep", "4", day="2026-11-18")
        b = self.tool("todo", "brief", day="2026-11-22")
        self.assertIn(4, [s["id"] for s in b["stale"]])

    def test_many_stale_items_fit_and_keep_protocol(self):
        for i in range(30):
            self.tool("todo", "add", "--what", "오래된 일 %02d " % i + "나" * 150, day="2026-10-01")
        self.tool("rule", "add", "--text", "보고는 표로")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "보고서는 한 장으로"}, day="2026-10-02")
        self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 …"}, day="2026-10-02")
        out = self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "안녕"})
        self.assertLessEqual(len(json.dumps(out, ensure_ascii=False)), 9500)
        c = self.ctx(out)
        self.assertIn("밀린 일 30건", c)
        self.assertIn("오너 지시 점검", c)            # 필수 규약 줄은 질문 목록에 밀려 잘리지 않는다(codex 1R #5)
        self.assertIn("직전 오너 입력 다시 보기", c)    # 이월도 실리고(실린 것만 소비)
        self.assertLessEqual(c.count("계속할까요"), 5)
        self.assertIn("더 —", c)

    def test_multi_add_order_line(self):
        r = self.tool("todo", "add", "--what", "긴 보고서", "--what", "짧은 답장", "--what", "급한 송금 확인",
                      "--short", "2", "--urgent", "3")
        self.assertIn("이 순서로 할게요: #3 급한 송금 확인 → #2 짧은 답장 → #1 긴 보고서", r["say"])


class R4Notify(Base):
    def test_done_notifies_once(self):
        self.tool("notify", "set", "--channel", "app")
        self.tool("todo", "add", "--what", "주보 만들기", "--notify")
        self.tool("todo", "add", "--what", "알림 없는 일")
        self.tool("todo", "done", "1", "--evidence", "PDF 저장")
        self.tool("todo", "done", "1", "--evidence", "다시")
        self.tool("todo", "done", "2", "--evidence", "끝")
        f = self.feeds()
        self.assertEqual(len(f), 1, f)
        self.assertIn("feed push --kind ceo-notice", f[0])
        self.assertIn("주보 만들기", f[0])

    def test_app_send_failure_is_retried_not_lost(self):
        self.tool("notify", "set", "--channel", "app")
        self.tool("todo", "add", "--what", "주보 만들기", "--notify")
        open(self.failflag, "w").close()                 # 첫 발송 실패(codex 1R #1)
        d = self.tool("todo", "done", "1", "--evidence", "PDF 저장")
        self.assertEqual(d["notify"]["app"], "failed")
        self.assertEqual(self.feeds(), [])
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "다음"})   # 다음 훅이 재시도
        self.assertEqual(len(self.feeds()), 1)
        self.hook({"hook_event_name": "SessionStart", "source": "clear"})     # 보낸 뒤엔 다시 안 보냄
        self.assertEqual(len(self.feeds()), 1)

    def test_all_done_rule(self):
        self.tool("notify", "set", "--channel", "app", "--all-done", "on")
        self.tool("todo", "add", "--what", "X")
        self.tool("todo", "done", "1", "--evidence", "ok")
        self.assertEqual(len(self.feeds()), 1)

    def test_phone_pending_blocks_until_push(self):
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "사진 정리", "--notify")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "사진 정리 끝냈어?"})
        self.tool("todo", "done", "1", "--evidence", "완료")
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "끝냈어요"})
        self.assertEqual(out["decision"], "block")
        self.assertIn("PushNotification", out["reason"])
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_response": PUSHED,
                   "tool_input": {"message": "끝났어요: 사진 정리 (#1)"}})
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 1건 …\n끝냈어요"})
        self.assertIsNone(out)
        self.assertEqual(self.feeds(), [])   # phone 길 = 앱 알림 0

    def test_phone_matched_per_item(self):
        """폰 의무는 일마다 (#번호)로 닫힌다 — 무관한 알림 1번이 A·B 를 함께 닫지 않는다(codex 1R #2)."""
        self.tool("notify", "set", "--channel", "phone", "--all-done", "on")
        self.tool("todo", "add", "--what", "A", "--what", "B")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "둘 다 끝"})
        self.tool("todo", "done", "1", "--evidence", "a")
        self.tool("todo", "done", "2", "--evidence", "b")
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_response": PUSHED, "tool_input": {"message": "작업 완료"}})
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 0건"})
        self.assertIn("(#1)", out["reason"])
        self.assertIn("(#2)", out["reason"])
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_response": PUSHED,
                   "tool_input": {"message": "끝났어요: A (#1)"}})
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "x"})
        self.assertIn("(#2)", out["reason"])
        self.assertNotIn("(#1)", out["reason"])

    def test_phone_reminders_then_give_up(self):
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "A", "--notify")
        self.tool("todo", "done", "1", "--evidence", "a")
        seen = 0
        for i in range(4):
            c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "턴 %d" % i}))
            seen += 1 if "보내지 않은 폰 알림" in c else 0
        self.assertEqual(seen, 2)                        # 두 번 일러 주고 포기(무한히 조르지 않음)
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 0건"}))


class R4NotifyRace(Base):
    def test_app_claim_marker_dedupes(self):
        """두 좌석이 같은 앱 알림 의무를 동시에 flush 해도 1번 — 「보내는 중」 표지를 잠금 안에서 잡은 쪽만 보낸다."""
        self.tool("notify", "set", "--channel", "app")
        self.tool("todo", "add", "--what", "주보", "--notify")
        code = ("import sys; sys.path.insert(0, %r); import javis_owner as o\n"
                "def f(d): d['items'][0].update(status='done', notice={'app': 'pending', 'phone': None, 'message': 'm'})\n"
                "o._mutate(f)\n"
                "a = o.flush_app_notices(); b = o.flush_app_notices(); print(a, b)" % os.path.join(PACK, "bin"))
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.stdout.strip(), "{1: 'sent'} {}", p.stderr)
        self.assertEqual(len(self.feeds()), 1)

    def test_parallel_flush_sends_once(self):
        """두 좌석이 동시에 flush(발송이 1초 걸림) — 「보내는 중」 표지가 없으면 둘 다 보낸다."""
        self.tool("notify", "set", "--channel", "app")
        self.tool("todo", "add", "--what", "주보", "--notify")
        setup = ("import sys; sys.path.insert(0, %r); import javis_owner as o\n"
                 "def f(d): d['items'][0].update(status='done', notice={'app': 'pending', 'phone': None, 'message': 'm'})\n"
                 "o._mutate(f)" % os.path.join(PACK, "bin"))
        subprocess.run([sys.executable, "-c", setup], env=self.env, check=True)
        code = "import sys; sys.path.insert(0, %r); import javis_owner as o; o.flush_app_notices()" % os.path.join(PACK, "bin")
        env = dict(self.env, FAKE_CYS_SLOW="1")
        ps = [subprocess.Popen([sys.executable, "-c", code], env=env) for _ in range(2)]
        for p in ps:
            p.wait(timeout=60)
        self.assertEqual(len(self.feeds()), 1)


class R8Codex2R(Base):
    """codex 2R 지적 재현(수리 전 붉음)."""

    def test_fit_consumes_only_emitted_carry(self):
        # 다시 보기 줄(발췌 300자)은 한 줄이 길어 20건(CARRY_MAX)이면 출력 상한을 넘는다.
        items = [{"k": "second", "text": "확인 %03d " % i + "다" * 300} for i in range(20)]
        self.py("o._save_carry(%r)" % items)
        c1 = self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "첫 입력"})
        self.assertLessEqual(len(json.dumps(c1, ensure_ascii=False)), 9500)
        self.assertIn("오너 지시 점검", self.ctx(c1))          # 규약 줄은 이월에 밀려 잘리지 않는다
        self.assertIn("이월", self.ctx(c1))
        left = int(self.py("print(len(o._load_carry()))"))
        self.assertGreater(left, 0)                             # 못 실은 이월은 남는다(codex 2R #1)
        self.assertLess(left, 20)
        c2 = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "둘째 입력"}))
        self.assertIn("확인 %03d" % (20 - left), c2)            # 다음 입력에 이어서 실린다

    def test_phone_reminder_counts_only_emitted(self):
        self.tool("notify", "set", "--channel", "phone", "--all-done", "on")
        for i in range(150):
            self.tool("todo", "add", "--what", "일 %03d " % i + "라" * 100)
        self.py("\n".join(["def f(d):",
                            "    for it in d['items']:",
                            "        it.update(status='done', notice={'phone': 'pending', 'message': o._push_message(it), 'phone_reminders': 0})",
                            "o._mutate(f)"]))
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "안녕"})
        counts = json.loads(self.py("print(__import__('json').dumps([it['notice']['phone_reminders'] for it in o.load_todos()['items']]))"))
        self.assertIn(0, counts)                                # 안 실린 알림은 세지 않는다
        self.assertIn(1, counts)

    def test_app_flush_per_item_budget_and_request_id(self):
        self.tool("notify", "set", "--channel", "app")
        self.tool("todo", "add", "--what", "A", "--what", "B", "--notify")
        self.py("\n".join(["def f(d):",
                            "    for it in d['items']:",
                            "        it.update(status='done', notice={'event': 'done-%d-x' % it['id'], 'app': 'pending', 'phone': None, 'message': 'm'})",
                            "o._mutate(f)",
                            "print(o.flush_app_notices(budget=1.6))"]), FAKE_CYS_SLOW="1")
        f = self.feeds()
        self.assertEqual(len(f), 1)                              # 시간 상한 — 둘째는 시작하지 않음
        self.assertIn("--request-id owner-done-1-x", open(self.feedlog, encoding="utf-8").read())   # 데몬 쪽 중복 거절 열쇠(2R #2)
        st = self.py("print([it['notice']['app'] for it in o.load_todos()['items']])")
        self.assertEqual(st, "['sent', 'pending']")             # 한 건씩 바로 확정
        open(self.failflag + ".dup", "w").close()               # 데몬이 이미 받은 사건 = 보낸 것으로 정산
        self.assertEqual(self.py("print(o.flush_app_notices())"), "{2: 'sent'}")

    def test_phone_claim_per_seat(self):
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "A", "--notify")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "끝냈어"})
        self.tool("todo", "done", "1", "--evidence", "a")       # 좌석 7 이 맡음
        self.env["CYS_SURFACE_ID"] = "8"
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "다른 좌석"})
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 0건"})
        self.assertTrue(out is None or "(#1)" not in out["reason"])   # 다른 좌석은 같은 폰 알림을 보내지 않는다(codex 2R #3)
        self.env["CYS_SURFACE_ID"] = "7"
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "x"})
        self.assertIn("(#1)", out["reason"])

    def test_subagent_push_is_settled(self):
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "A", "--notify")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "끝냈어"})
        self.tool("todo", "done", "1", "--evidence", "a")
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_response": PUSHED, "agent_id": "sub1",
                   "tool_input": {"message": "끝났어요: A (#1)"}})
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 0건"}))  # codex 2R #4

    def test_daily_brief_one_seat(self):
        self.tool("todo", "add", "--what", "주보", day="2026-11-17")
        self.assertIn("밀린 일 1건", self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "A 좌석"})))
        self.env["CYS_SURFACE_ID"] = "8"
        self.assertNotIn("밀린 일 1건", self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "B 좌석"})))  # 2R #5
        self.env["CYS_SURFACE_ID"] = "7"
        self.assertIn("밀린 일 1건", self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "A 다시(끊김 뒤)"})))

    def test_shown_once_in_turn_survives_followup_answer(self):
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "A", "--notify")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 표로 · A 끝"})
        self.tool("rule", "add", "--text", "표로")
        self.tool("todo", "done", "1", "--evidence", "a")
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 …\n이렇게 저장했습니다: 「표로」"})
        self.assertIn("PushNotification", out["reason"])
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_response": PUSHED, "tool_input": {"message": "끝났어요: A (#1)"}})
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "stop_hook_active": True,
                                     "last_assistant_message": "알림을 보냈어요"}))
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "다음"}))
        self.assertNotIn("확인 줄 누락", c)                      # codex 2R #7

    def test_interrupted_turn_is_settled(self):
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 표로 해 줘"})
        self.tool("rule", "add", "--text", "표로")              # 저장 뒤 확인 줄 전에 사용자가 끊음 → Stop 없음
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "다시"}))
        self.assertIn("이렇게 저장했습니다: 「표로」", c)          # codex 2R 논쟁점(끊긴 턴 정산)
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "보고는 한 장으로"})   # 기록 0건 · 끊김
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "또"}))
        self.assertIn("«보고는 한 장으로»", c)


class R9Codex3R(Base):
    """codex 3R 지적 재현(수리 전 붉음)."""

    def test_compact_keeps_active_turn_net(self):
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 표로"})
        self.hook({"hook_event_name": "SessionStart", "source": "compact"})      # 턴 도중 자동 압축
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "이렇게 저장했습니다: 표로"})
        self.assertEqual(out["decision"], "block")                               # 3R #1 — 안전망 유지

    def test_only_trailing_id_settles(self):
        self.tool("notify", "set", "--channel", "phone", "--all-done", "on")
        self.tool("todo", "add", "--what", "보고서 (#2) 인용 확인", "--what", "B")
        self.tool("todo", "done", "1", "--evidence", "a")
        self.tool("todo", "done", "2", "--evidence", "b")
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_response": PUSHED,
                   "tool_input": {"message": "끝났어요: 보고서 (#2) 인용 확인 (#1)"}})
        st = self.py("print([it['notice']['phone'] for it in o.load_todos()['items']])")
        self.assertEqual(st, "['sent', 'pending']")                              # 3R #2

    def test_pretool_denies_duplicate_send(self):
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "A", "--notify")
        self.tool("todo", "done", "1", "--evidence", "a")
        pre = {"hook_event_name": "PreToolUse", "tool_name": "PushNotification", "tool_input": {"message": "끝났어요: A (#1)"}}
        self.assertIsNone(self.hook(pre))                                        # 첫 발송 허용(보내는 중 표지)
        d = self.hook(dict(pre, agent_id="sub"))                                  # 하위 에이전트·다른 좌석의 겹친 발송
        self.assertEqual(d["hookSpecificOutput"]["permissionDecision"], "deny")  # 3R #3
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_response": PUSHED, "tool_input": pre["tool_input"]})
        d = self.hook(pre)
        self.assertEqual(d["hookSpecificOutput"]["permissionDecision"], "deny")  # 보낸 뒤 재발송도 거절
        self.assertIsNone(self.hook({"hook_event_name": "PreToolUse", "tool_name": "PushNotification",
                                     "tool_input": {"message": "다른 알림"}}))   # 우리 의무 아닌 것은 무관여

    def test_flush_deadline_bounds_subprocess(self):
        self.tool("notify", "set", "--channel", "app")
        self.tool("todo", "add", "--what", "A", "--what", "B", "--notify")
        self.py("\n".join(["def f(d):",
                            "    for it in d['items']:",
                            "        it.update(status='done', notice={'event': 'e%d' % it['id'], 'app': 'pending', 'phone': None, 'message': 'm'})",
                            "o._mutate(f)",
                            "print(o.flush_app_notices(budget=4))"]), FAKE_CYS_SLOW="2")
        # 첫 발송(≈2초) 뒤 남은 시간 < 둘째에 필요한 시간 — 둘째는 끊겨 기록을 못 남긴다(고정 timeout 이면 끝까지 가서 2건).
        # 벽시계 비교는 해석기 기동 시간에 따라 판정이 갈려 쓰지 않는다.
        self.assertEqual(len(self.feeds()), 1)                                   # 3R #4 — 발송 timeout 도 남은 시간 안
        st = self.py("print([it['notice']['app'] for it in o.load_todos()['items']])")
        self.assertEqual(st, "['sent', 'pending']")

    def test_flush_starts_nothing_when_budget_short(self):
        self.tool("notify", "set", "--channel", "app")
        self.tool("todo", "add", "--what", "A", "--notify")
        out = self.py("\n".join(["def f(d):",
                                  "    d['items'][0].update(status='done', notice={'event': 'e1', 'app': 'pending', 'phone': None, 'message': 'm'})",
                                  "o._mutate(f)",
                                  "print(o.flush_app_notices(budget=0.5))"]))
        self.assertEqual(out, "{}")                                              # 남은 시간 1초 미만 = 시작하지 않음(실패로도 안 셈)
        self.assertEqual(self.feeds(), [])
        n = json.loads(self.py("print(__import__('json').dumps(o.load_todos()['items'][0]['notice']))"))
        self.assertEqual((n["app"], n.get("app_attempts", 0)), ("pending", 0))

    def test_brief_confirm_uses_brief_day(self):
        self.tool("todo", "add", "--what", "주보", day="2026-11-16")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "밤 늦게"}, day="2026-11-18")
        self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 1건 …"}, day="2026-11-19")   # 자정 넘김
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "아침"}, day="2026-11-19"))
        self.assertIn("밀린 일 1건", c)                                          # 3R #5

    def test_late_success_after_give_up_is_settled(self):
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "A", "--notify")
        self.tool("todo", "done", "1", "--evidence", "a")
        for i in range(3):
            self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "턴 %d" % i})
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_response": PUSHED,
                   "tool_input": {"message": "끝났어요: A (#1)"}})
        self.assertEqual(self.py("print(o.load_todos()['items'][0]['notice']['phone'])"), "sent")   # 3R #6


class R10Codex4R(Base):
    def test_failed_send_does_not_burn_reminders(self):
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "A", "--notify")
        self.tool("todo", "done", "1", "--evidence", "a")
        self.hook({"hook_event_name": "PreToolUse", "tool_name": "PushNotification",
                   "tool_input": {"message": "끝났어요: A (#1)"}})          # 보내다 실패 — PostToolUse 안 옴
        for i in range(3):
            self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "턴 %d" % i})
        n = json.loads(self.py("print(__import__('json').dumps(o.load_todos()['items'][0]['notice']))"))
        self.assertEqual(n["phone"], "pending")                    # 4R ① — 보내는 중 유예 동안 포기하지 않음
        self.assertEqual(n.get("phone_reminders", 0), 0)

    def test_sending_mark_guards_claim_bump_expire(self):
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "A", "--notify")
        self.tool("todo", "done", "1", "--evidence", "a")
        code = "\n".join(["def f(d):",
                          "    d['items'][0]['notice'].update(phone_sending=o.time.time() - (%s), phone_reminders=o.PHONE_REMINDERS)",
                          "o._mutate(f)",
                          "got = o.claim_phone()",
                          "o.bump_phone_reminders({1})",                   # 안내를 고른 뒤 표지가 찍힌 틈도 세지 않는다
                          "o.expire_phone()",
                          "n = o.load_todos()['items'][0]['notice']",
                          "print(len(got), n['phone_reminders'] - o.PHONE_REMINDERS, n['phone'])"])
        self.assertEqual(self.py(code % "0"), "0 0 pending")               # 보내는 중 — 지시·횟수·포기 모두 멈춤
        self.assertEqual(self.py(code % "o.PHONE_SENDING_STALE + 1"), "1 1 unsent")   # 표지 만료 — 다시 움직임

    def test_brief_confirm_never_moves_back(self):
        self.tool("todo", "add", "--what", "주보", day="2026-11-16")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "A 18일 밤"}, day="2026-11-18")   # A 좌석 18일 보고
        self.env["CYS_SURFACE_ID"] = "8"
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "B 19일"}, day="2026-11-19")
        self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 1건"}, day="2026-11-19")
        self.env["CYS_SURFACE_ID"] = "7"
        self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 1건"}, day="2026-11-19")  # A 의 늦은 Stop
        self.env["CYS_SURFACE_ID"] = "8"
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "B 또"}, day="2026-11-19"))
        self.assertNotIn("밀린 일 1건", c)                          # 4R ② — 19일 확인이 18일로 되돌아가지 않음


class R11PhoneResult(Base):
    MSG = "끝났어요: A (#1)"

    def setUp(self):
        super().setUp()
        self.tool("notify", "set", "--channel", "phone")
        self.tool("todo", "add", "--what", "A", "--notify")
        self.tool("todo", "done", "1", "--evidence", "a")

    def notice(self):
        return json.loads(self.py("print(__import__('json').dumps(o.load_todos()['items'][0]['notice']))"))

    def send(self, resp="absent"):
        self.hook({"hook_event_name": "PreToolUse", "tool_name": "PushNotification", "tool_input": {"message": self.MSG}})
        p = {"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_input": {"message": self.MSG}}
        if resp != "absent":
            p["tool_response"] = resp
        self.hook(p)

    def prompt(self, text="다음"):
        return self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": text}))

    def test_really_sent_is_sent(self):
        for resp in (PUSHED, LOCAL_ONLY):
            self.py("\n".join(["def f(d):", "    d['items'][0]['notice'].update(phone='pending')", "    d['items'][0]['notice'].pop('phone_sent_at', None)", "o._mutate(f)"]))
            self.send(resp)
            n = self.notice()
            self.assertEqual(n["phone"], "sent")
            self.assertIn("phone_sent_at", n)
            self.assertNotIn("phone_sending", n)

    def test_present_is_not_sent_and_not_chased(self):
        self.send(PRESENT)
        n = self.notice()
        self.assertEqual((n["phone"], n["phone_reason"]), ("present", "user_present"))
        self.assertNotIn("phone_sent_at", n)
        self.assertNotIn("phone_sending", n)
        reminders = n.get("phone_reminders", 0)
        for i in range(3):
            c = self.prompt("턴 %d" % i)
            self.assertNotIn("(#1)", c)                              # 재안내 없음
            self.assertNotIn("폰 알림 결과", c)                       # 못 보냄 안내도 아님
        n = self.notice()
        self.assertEqual((n["phone"], n.get("phone_reminders", 0)), ("present", reminders))   # 포기로 몰지 않음
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "x"}))

    def _undelivered(self, resp, reason, phrase):
        self.send(resp)
        n = self.notice()
        self.assertEqual((n["phone"], n["phone_reason"]), ("undelivered", reason))
        self.assertNotIn("phone_sent_at", n)
        self.assertNotIn("phone_sending", n)
        c = self.prompt()
        self.assertIn("폰 알림 결과", c)
        self.assertIn(phrase, c)
        self.assertNotIn("PushNotification 으로 보내라】", c)          # 다시 보내라고 하지 않음
        self.assertNotIn("폰 알림 결과", self.prompt("또"))             # 한 번만 말한다
        self.assertEqual(self.notice()["phone"], "undelivered")

    def test_no_transport_tells_owner_once(self):
        self._undelivered(NO_TRANSPORT, "no_transport", "Remote Control")

    def test_config_off_tells_owner_once(self):
        self._undelivered(CONFIG_OFF, "config_off", "설정이 꺼져")

    def test_unknown_result_is_never_sent(self):
        for resp in ("absent", None, "Mobile push requested.", {"pushSent": False}, {"disabledReason": "새로운_사유"},
                     {"pushSent": "true", "localSent": 1}):
            self.py("\n".join(["def f(d):", "    d['items'][0]['notice'].update(phone='pending', phone_told=False)", "o._mutate(f)"]))
            self.send(resp)
            n = self.notice()
            self.assertEqual(n["phone"], "unknown", resp)
            self.assertNotIn("phone_sent_at", n)
            self.assertIn("확인하지 못했어요", self.prompt())

    def test_retry_can_upgrade_but_sent_never_downgrades(self):
        self.send(NO_TRANSPORT)
        self.send(PUSHED)
        self.assertEqual(self.notice()["phone"], "sent")
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification", "tool_input": {"message": self.MSG},
                   "tool_response": NO_TRANSPORT})
        self.assertEqual(self.notice()["phone"], "sent")

    def test_only_emitted_results_are_marked_told(self):
        self.tool("todo", "add", *sum([["--what", "일 %d " % i + "가" * 110] for i in range(70)], []))
        self.py("\n".join(["def f(d):", "    for it in d['items']:",
                            "        it.update(status='done', notice={'phone': 'undelivered', 'phone_reason': 'no_transport', 'message': 'm'})",
                            "o._mutate(f)"]))
        c = self.prompt()
        told = self.py("print(sum(1 for it in o.load_todos()['items'] if it['notice'].get('phone_told')))")
        self.assertEqual(int(told), c.count("【폰 알림 결과 — "))
        self.assertLess(int(told), 71)
        self.assertGreater(int(told), 0)
        self.prompt("또")
        self.assertGreater(int(self.py("print(sum(1 for it in o.load_todos()['items'] if it['notice'].get('phone_told')))")), int(told))


class R5StopNet(Base):
    """턴 끝 안전망 — 막는 것은 거짓 확인·폰 알림 미발송 둘뿐 · 나머지는 다음 오너 턴으로 이월(막으면 답이 되풀이된다 ·
    11-18 실좌석 실측: 자기 점검 막기 → 빈 답 → 하네스가 보이는 답 강요 → 같은 표 3번)."""

    def test_false_claim_blocks_but_unshown_save_carries(self):
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 보고는 항상 표로 해 줘"})
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "이렇게 저장했습니다: 표로"})
        self.assertEqual(out["decision"], "block")
        self.assertIn("저장 기록이 없다", out["reason"])
        # 새 턴: 저장은 했는데 확인 줄을 안 보임 → 막지 않고 다음 오너 턴 첫머리에 확인 줄을 싣는다
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 보고는 항상 표로 해 줘"})
        self.tool("rule", "add", "--text", "보고는 항상 표로")
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "네 알겠습니다"}))
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "다음 일"}))
        self.assertIn("확인 줄 누락", c)
        self.assertIn("이렇게 저장했습니다: 「보고는 항상 표로」", c)
        # 이월된 확인 줄을 그대로 말한 것은 거짓 확인이 아니다(codex 1R #3-A)
        self.assertIsNone(self.hook({"hook_event_name": "Stop",
                                     "last_assistant_message": "이렇게 저장했습니다: 「보고는 항상 표로」"}))
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "또 다음"}))
        self.assertNotIn("확인 줄 누락", c)

    def test_duplicate_save_is_evidence(self):
        self.tool("rule", "add", "--text", "보고는 항상 표로")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "보고는 항상 표로 해 줘"})
        r = self.tool("rule", "add", "--text", "보고는 항상 표로")
        self.assertTrue(r.get("duplicate"))
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": r["say"]}))   # codex 1R #3-B

    def test_second_look_next_turn_and_after_cycle(self):
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "보고서는 늘 한 장으로 줄여서 줘"})
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "네"}))
        # 순환(/clear) 뒤 새 대화 시작에도 다시 보기가 실린다
        sc = self.ctx(self.hook({"hook_event_name": "SessionStart", "source": "clear"}))
        self.assertIn("직전 오너 입력 다시 보기", sc)
        self.assertIn("보고서는 늘 한 장으로 줄여서 줘", sc)
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "고마워"}))
        self.assertIn("«보고서는 늘 한 장으로 줄여서 줘»", c)
        # 턴이 끊겨 Stop 이 안 와도(중단) 이월은 한 번만 실린다
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "다시"}))
        self.assertNotIn("«보고서는 늘 한 장으로 줄여서 줘»", c)
        # 기록이 있었던 턴은 다시 보기 없음
        self.tool("todo", "add", "--what", "주간 보고")
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "할 일로 적었어요"}))
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "또"}))
        self.assertNotIn("다시 보기", c)
        # 끄면 다시 보기 없음
        self.tool("notify", "set", "--selfcheck", "off")
        self.hook({"hook_event_name": "Stop", "last_assistant_message": "x"})
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "그리고"}))
        self.assertNotIn("다시 보기", c)

    def test_loop_cap(self):
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "x"})
        n = 0
        for _ in range(5):
            o = self.hook({"hook_event_name": "Stop", "last_assistant_message": "이렇게 저장했습니다"})
            n += 1 if o else 0
        self.assertEqual(n, 2)

    def test_morning_brief_carries_when_missed(self):
        self.tool("todo", "add", "--what", "주보", day="2026-11-17")
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "안녕"}))
        self.assertIn("밀린 일 1건", c)
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "안녕하세요"}))
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "뭐 해?"}))
        self.assertIn("밀린 일 1건", c)          # 놓친 아침 보고는 다음 오너 턴에 다시
        self.hook({"hook_event_name": "Stop",
                   "last_assistant_message": "밀린 일 1건 · 가장 오래된 것 받은 지 1일(#1 주보)\n…"})
        c = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "응"}))
        self.assertNotIn("밀린 일 1건", c)       # 말했으면 그날은 끝

    def test_morning_brief_survives_interrupt(self):
        """보고 전에 사용자가 끊으면 Stop 이 오지 않는다(공식 hooks 문서) — 다음 입력에 다시 싣는다(codex 1R #7)."""
        self.tool("todo", "add", "--what", "주보", day="2026-11-17")
        self.assertIn("밀린 일 1건", self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "안녕"})))
        self.assertIn("밀린 일 1건", self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "다시"})))


class R1Retire(Base):
    def test_retire_removes_only_exact_index_row(self):
        mem = os.path.join(self.pack, "memory")
        J = [sys.executable, os.path.join(PACK, "bin", "javis_memory.py"), "--dir", mem]
        subprocess.run(J + ["add", "--type", "feedback", "--name", "x", "--desc", "X 메모", "--body", "x"],
                       capture_output=True, env=self.env)
        subprocess.run(J + ["add", "--type", "feedback", "--name", "y", "--desc", "예시 (feedback_x.md) 참고",
                            "--body", "y"], capture_output=True, env=self.env)
        p = subprocess.run(J + ["retire", "--name", "x"], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        idx = open(os.path.join(mem, "MEMORY.md"), encoding="utf-8").read()
        self.assertIn("(feedback_y.md)", idx)            # codex 1R #8
        self.assertNotIn("](feedback_x.md)", idx)
        v = subprocess.run(J + ["verify"], capture_output=True, text=True)
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)


class R6Guards(Base):
    def test_role_and_machine_and_subagent(self):
        self.tool("rule", "add", "--text", "항상 표로")
        self.assertIsNone(self.hook({"hook_event_name": "SessionStart", "source": "clear"}, role="worker"))
        self.assertIsNone(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 표로"}, role="cso"))
        self.assertIsNone(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "[wakeup] 다음 액션 착수"}))
        self.assertIsNone(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 표로", "agent_id": "a1"}))
        # 기계 입력 턴은 오너 턴이 아니다 → Stop 안전망 0(앞 오너 턴 표지가 있어도)
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "오너 말"})
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "[보고] 워커 완료"})
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "이렇게 저장했습니다"}))


class R7Wiring(Base):
    def test_c28_registration_and_caps(self):
        import javis_preflight as pf
        rows = dict(pf.SELFCORR_HOOKS)["owner-desk.sh"]
        self.assertEqual(sorted(e for e, _ in rows),
                         ["PostToolUse", "PreToolUse", "SessionStart", "Stop", "UserPromptSubmit"])
        self.assertIn(("PostToolUse", "PushNotification"), rows)
        self.assertIn(("PreToolUse", "PushNotification"), rows)
        inner = int(re.search(r"cys_timeout_run (\d+) ", open(SH, encoding="utf-8").read()).group(1))
        for ev, _ in rows:
            self.assertLess(inner, pf.HOOK_TIMEOUT_S[("owner-desk.sh", ev)])

    def test_child_memory_tool_is_utf8(self):
        """한국어 윈 파이프 기본 cp949 와 엇갈리지 않게 자식 javis_memory 를 UTF-8 로 띄운다(codex 1R #6)."""
        import javis_owner
        seen = {}
        real = javis_owner.subprocess.run

        def fake(cmd, **kw):
            seen.update(kw)

            class P:
                returncode, stdout, stderr = 0, "", ""
            return P()
        javis_owner.subprocess.run = fake
        try:
            javis_owner._memory_tool("verify")
        finally:
            javis_owner.subprocess.run = real
        self.assertEqual(seen["env"].get("PYTHONUTF8"), "1")
        self.assertEqual(seen["env"].get("PYTHONIOENCODING"), "utf-8")
        self.assertEqual(seen.get("encoding"), "utf-8")
        self.assertEqual(seen.get("stdin"), subprocess.DEVNULL)

    def test_windows_home_paths(self):
        import importlib
        import javis_owner
        env = {"USERPROFILE": r"C:\Users\참가자", "HOME": r"C:\Users\참가자"}
        old = {k: os.environ.get(k) for k in ("CYS_OWNER_DIR", "CYS_PACK_DIR", "HOME", "USERPROFILE")}
        try:
            for k in ("CYS_OWNER_DIR", "CYS_PACK_DIR"):
                os.environ.pop(k, None)
            os.environ.update(env)
            import ntpath
            real_join, real_expand, real_makedirs = os.path.join, os.path.expanduser, os.makedirs
            javis_owner.os.path.join = ntpath.join
            javis_owner.os.path.expanduser = lambda p: ntpath.expanduser(p) if os.name == "nt" else p.replace("~", env["USERPROFILE"], 1)
            javis_owner.os.makedirs = lambda *a, **k: None
            try:
                self.assertEqual(javis_owner.owner_dir(), r"C:\Users\참가자\.cys\owner")
                self.assertEqual(javis_owner.memory_dir(), r"C:\Users\참가자\.cys\pack\memory")
            finally:
                javis_owner.os.path.join, javis_owner.os.path.expanduser, javis_owner.os.makedirs = \
                    real_join, real_expand, real_makedirs
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            importlib.reload(javis_owner)


if __name__ == "__main__":
    unittest.main(verbosity=1)
