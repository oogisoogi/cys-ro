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
  R5 턴 끝 안전망 = 「저장했다」는 말과 저장 기록 대조(양방향) · 아침 보고 누락 차단 · 자기 점검 턴당 1회 · 고리 상한
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
        fake = os.path.join(self.tmp, "fake-cys")
        with open(fake, "w") as f:
            f.write('#!/bin/sh\nprintf "%%s\\n" "$*" >> "%s"\n' % self.feedlog)
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

    def test_rules_block_fits_hook_cap(self):
        for i in range(60):
            self.tool("rule", "add", "--text", "규칙 %02d " % i + "가" * 80)
        c = self.ctx(self.hook({"hook_event_name": "SessionStart", "source": "clear"}))
        self.assertLess(len(c), 9000)


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
        # 같은 날 두 번째 오너 대화엔 아침 보고 없음.
        c2 = self.ctx(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "그리고 하나 더"}, day="2026-11-18"))
        self.assertNotIn("밀린 일 2건", c2)
        self.assertIn("오너 지시 점검", c2)
        # 하루 더 지나면 #2 도 사흘 넘음(4일).
        b = self.tool("todo", "brief", day="2026-11-19")
        self.assertEqual([s["id"] for s in b["stale"]], [1, 2])

    def test_keep_defer_cancel(self):
        self.tool("todo", "add", "--what", "A", "--what", "B", "--what", "C", day="2026-11-01")
        self.tool("todo", "keep", "1", day="2026-11-18")
        self.tool("todo", "defer", "2", "--days", "5", day="2026-11-18")
        self.tool("todo", "cancel", "3", "--reason", "필요 없어짐", day="2026-11-18")
        b = self.tool("todo", "brief", day="2026-11-19")
        self.assertEqual(b["open"], 2)
        self.assertEqual(b["stale"], [])
        b = self.tool("todo", "brief", day="2026-11-23")   # 계속(11-18)+5일 = 다시 묻고, 미룸(11-23까지)은 아직
        self.assertEqual([s["id"] for s in b["stale"]], [1])
        b = self.tool("todo", "brief", day="2026-11-27")   # 미룸 끝(11-23)+4일 → 묻는다
        self.assertEqual([s["id"] for s in b["stale"]], [1, 2])

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
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "PushNotification",
                   "tool_input": {"message": "끝났어요: 사진 정리 (#1)"}})
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "밀린 일 1건 …\n끝냈어요"})
        self.assertIsNone(out)
        self.assertEqual(self.feeds(), [])   # phone 길 = 앱 알림 0


class R5StopNet(Base):
    def test_claim_without_record_and_record_without_claim(self):
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 보고는 항상 표로 해 줘"})
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "이렇게 저장했습니다: 표로"})
        self.assertEqual(out["decision"], "block")
        self.assertIn("저장 기록이 없다", out["reason"])
        # 새 턴: 저장은 했는데 확인 줄을 안 보임
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 보고는 항상 표로 해 줘"})
        self.tool("rule", "add", "--text", "보고는 항상 표로")
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "네 알겠습니다"})
        self.assertEqual(out["decision"], "block")
        self.assertIn("확인 줄이 없다", out["reason"])
        out = self.hook({"hook_event_name": "Stop", "stop_hook_active": True,
                         "last_assistant_message": "이렇게 저장했습니다: 「보고는 항상 표로」"})
        self.assertIsNone(out)

    def test_selfcheck_once_per_turn_and_loop_cap(self):
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "오늘 날씨 어때"})
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "맑아요"})
        self.assertEqual(out["decision"], "block")
        self.assertIn("턴 끝 점검", out["reason"])
        out = self.hook({"hook_event_name": "Stop", "stop_hook_active": True, "last_assistant_message": ""})
        self.assertIsNone(out)
        # 끄면 자기 점검 없음
        self.tool("notify", "set", "--selfcheck", "off")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "고마워"})
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "천만에요"}))
        # 고리 상한: 대조 실패가 되풀이돼도 MAX_BLOCKS 뒤엔 놓아준다
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "x"})
        n = 0
        for _ in range(5):
            o = self.hook({"hook_event_name": "Stop", "last_assistant_message": "이렇게 저장했습니다"})
            n += 1 if o else 0
        self.assertEqual(n, 2)

    def test_morning_brief_enforced(self):
        self.tool("todo", "add", "--what", "주보", day="2026-11-17")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "안녕"})
        out = self.hook({"hook_event_name": "Stop", "last_assistant_message": "안녕하세요"})
        self.assertIn("밀린 일 1건", out["reason"])
        out = self.hook({"hook_event_name": "Stop", "stop_hook_active": True,
                         "last_assistant_message": "밀린 일 1건 · 가장 오래된 것 받은 지 1일(#1 주보)\n안녕하세요"})
        self.assertIsNone(out)


class R6Guards(Base):
    def test_role_and_machine_and_subagent(self):
        self.tool("rule", "add", "--text", "항상 표로")
        self.assertIsNone(self.hook({"hook_event_name": "SessionStart", "source": "clear"}, role="worker"))
        self.assertIsNone(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 표로"}, role="cso"))
        self.assertIsNone(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "[wakeup] 다음 액션 착수"}))
        self.assertIsNone(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "앞으로 표로", "agent_id": "a1"}))
        # 기계 입력 턴은 오너 턴이 아니다 → Stop 안전망 0
        self.assertIsNone(self.hook({"hook_event_name": "Stop", "last_assistant_message": "x"}))


class R7Wiring(Base):
    def test_c28_registration_and_caps(self):
        import javis_preflight as pf
        rows = dict(pf.SELFCORR_HOOKS)["owner-desk.sh"]
        self.assertEqual(sorted(e for e, _ in rows), ["PostToolUse", "SessionStart", "Stop", "UserPromptSubmit"])
        self.assertIn(("PostToolUse", "PushNotification"), rows)
        inner = int(re.search(r"cys_timeout_run (\d+) ", open(SH, encoding="utf-8").read()).group(1))
        for ev, _ in rows:
            self.assertLess(inner, pf.HOOK_TIMEOUT_S[("owner-desk.sh", ev)])

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
