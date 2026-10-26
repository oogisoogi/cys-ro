#!/usr/bin/env python3
"""test_computer_control.py — javis_computer_control.py 계약 시험 (TICKET=cu-1111 · 설계 docs/DESIGN-cu-1111.md).

격리: 매 시험이 임시 HOME · 임시 클로드 설정 폴더 · 임시 상태 폴더 · 임시 앱 자리(CYS_CC_APP_ROOTS)를 세우고,
맥 권한 탐지(AX·화면 기록·앱 자동화)는 CYS_CC_FAKE_PROBES 로 주입한다. 실 ~/.cys/computer-control 무접촉.
뮤턴트 하네스(mut_computer_control.py)는 CC_MODULE 로 변이 사본을 가리키고 이 파일을 그대로 돌린다.
"""
import builtins
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD_PATH = os.environ.get("CC_MODULE") or os.path.join(BIN, "javis_computer_control.py")
REAL_STATE = os.path.join(os.path.expanduser("~"), ".cys", "computer-control")

EMAIL = "CC-TEST-EMAIL@example.invalid"
NAME = "CC-TEST-NAME"
ORG = "CC-TEST-ORG"
PROFILE = "CC-TEST-PROFILE"
MARKS = (EMAIL, NAME, ORG, PROFILE)
EXT = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
PW = "mmlmfjhmonkocbjadbfplnigmagldckm"


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def lines(p):
    with open(p, encoding="utf-8") as f:
        return f.read().splitlines()


def load_mod():
    spec = importlib.util.spec_from_file_location("javis_computer_control_ut", MOD_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cc-ut-")
        self.home = os.path.join(self.tmp, "home")
        self.ccd = os.path.join(self.tmp, "claude")
        self.state = os.path.join(self.tmp, "state")
        self.apps = os.path.join(self.tmp, "Applications")
        self.proj = os.path.join(self.home, "CYSjavis")
        for d in (self.home, self.ccd, self.apps, self.proj):
            os.makedirs(d)
        self.ud = os.path.join(self.home, "Library", "Application Support", "Google", "Chrome")
        self._env = dict(os.environ)
        os.environ.update({
            "HOME": self.home, "CLAUDE_CONFIG_DIR": self.ccd, "CYS_CC_STATE": self.state,
            "CYS_CC_PLATFORM": "darwin", "CYS_CC_PROJECT": self.proj, "CYS_CC_APP_ROOTS": self.apps,
        })
        self.probes = {"ax": True, "sc": True, "ae": {}}
        self.set_probes()
        self.write_cfg()
        self.m = load_mod()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── 고정물 ──
    def set_probes(self, **kw):
        self.probes.update(kw)
        os.environ["CYS_CC_FAKE_PROBES"] = json.dumps(self.probes)

    def write_cfg(self, plan="claude_max", cu=True, chrome_default=True, connectors=("claude.ai Gmail",),
                  logged_in=True, extra_projects=None):
        d = {"claudeInChromeDefaultEnabled": chrome_default,
             "claudeAiMcpEverConnected": list(connectors),
             "projects": {self.proj: {"enabledMcpServers": ["computer-use"] if cu else []}}}
        if extra_projects:
            d["projects"].update(extra_projects)
        if logged_in:
            d["oauthAccount"] = {"emailAddress": EMAIL, "displayName": NAME, "fullName": NAME,
                                 "organizationName": ORG, "organizationType": plan}
        with open(os.path.join(self.ccd, ".claude.json"), "w", encoding="utf-8") as f:
            json.dump(d, f)

    def make_chrome(self, app=True, ext=True, disabled=False, nmh=True, nmh_target=True, playwright=False):
        if app:
            os.makedirs(os.path.join(self.apps, "Google Chrome.app"), exist_ok=True)
        prof = os.path.join(self.ud, "Default")
        os.makedirs(os.path.join(prof, "Extensions"), exist_ok=True)
        with open(os.path.join(self.ud, "Local State"), "w") as f:
            json.dump({"profile": {"info_cache": {"Default": {"name": PROFILE}}}}, f)
        sp = {"extensions": {"settings": {}}}
        if ext:
            os.makedirs(os.path.join(prof, "Extensions", EXT, "1.0"), exist_ok=True)
            sp["extensions"]["settings"][EXT] = {"disable_reasons": [1] if disabled else [], "from_webstore": True}
        if playwright:
            os.makedirs(os.path.join(prof, "Extensions", PW, "1.0"), exist_ok=True)
        with open(os.path.join(prof, "Secure Preferences"), "w") as f:
            json.dump(sp, f)
        with open(os.path.join(prof, "Cookies"), "w") as f:
            f.write("secret-cookie")
        with open(os.path.join(prof, "Login Data"), "w") as f:
            f.write("secret-login")
        if nmh:
            host = os.path.join(self.tmp, "chrome-native-host")
            if nmh_target:
                open(host, "w").close()
            nd = os.path.join(self.ud, "NativeMessagingHosts")
            os.makedirs(nd, exist_ok=True)
            with open(os.path.join(nd, "com.anthropic.claude_code_browser_extension.json"), "w") as f:
                json.dump({"name": "x", "path": host}, f)

    def make_protected(self):
        for sub in ("Desktop", "Documents", "Downloads"):
            os.makedirs(os.path.join(self.home, sub), exist_ok=True)
            with open(os.path.join(self.home, sub, "private-%s.txt" % sub), "w") as f:
                f.write("private")

    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.m.main(list(argv))
        txt = buf.getvalue().strip()
        return rc, (json.loads(txt) if txt else None), txt

    def seen_scan_id(self):
        sp = os.path.join(self.state, "scan.json")
        return jload(sp).get("scan_id") if os.path.exists(sp) else "none"

    def grant_cli(self, *argv):
        """grant = 사용자가 본(마지막) 목록의 scan_id 를 함께 낸다(codex 1R #1)."""
        return self.run_cli("grant", "--scan", self.seen_scan_id(), *argv)

    def answer(self, text="1번 맡겨 줘"):
        p = os.path.join(self.tmp, "answer.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def item(self, scan, iid):
        for it in scan["items"]:
            if it["id"] == iid:
                return it
        return None


# ───────────────────────── 판정 ─────────────────────────
class TestVerdicts(Base):
    def test_self_test_passes(self):
        rc, d, _ = self.run_cli("self-test")
        self.assertEqual(rc, 0, d)
        self.assertTrue(d["ok"])

    def test_all_ready_when_everything_on(self):
        self.make_chrome()
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(rc, 0)
        self.assertEqual(self.item(d, "chrome")["tier"], "ready")
        self.assertEqual(self.item(d, "screen")["tier"], "ready")
        self.assertEqual(self.item(d, "connectors")["tier"], "ready")

    def test_unknown_never_ready_screen(self):
        self.make_chrome()
        for kw in ({"ax": None}, {"sc": None}):
            self.set_probes(**dict({"ax": True, "sc": True}, **kw))
            rc, d, _ = self.run_cli("scan")
            it = self.item(d, "screen")
            self.assertEqual(it["tier"], "hand", kw)
            self.assertTrue(it["unknown"], kw)
        self.set_probes(ax=True, sc=True)
        self.write_cfg(plan="mystery_plan")
        rc, d, _ = self.run_cli("scan")
        self.assertNotEqual(self.item(d, "screen")["tier"], "ready")
        self.write_cfg(plan="claude_max", extra_projects=None)
        os.environ["CYS_CC_PROJECT"] = os.path.join(self.home, "elsewhere")
        rc, d, _ = self.run_cli("scan")
        self.assertNotEqual(self.item(d, "screen")["tier"], "ready", "기록 없는 폴더의 computer-use 는 모름")

    def test_screen_off_parts_are_named(self):
        self.write_cfg(cu=False)
        self.set_probes(ax=True, sc=False)
        rc, d, _ = self.run_cli("scan")
        it = self.item(d, "screen")
        self.assertEqual(it["tier"], "hand")
        self.assertIn("화면 기록 권한", d["say"])
        self.assertIn("/mcp", d["say"])

    def test_unknown_parts_say_check_not_missing(self):
        # VM 실기 교정: 로그인 전(설정 기록 없음)은 「꺼짐」이 아니라 「확인 못 함」 — 「남은 것」이라 말하지 않는다
        os.environ["CYS_CC_PROJECT"] = os.path.join(self.home, "elsewhere")
        rc, d, _ = self.run_cli("scan")
        line = [l for l in d["say"].splitlines() if "화면 조작" in l][0]
        self.assertIn("확인할 것", line)
        self.assertNotIn("남은 것", line)

    def test_team_plan_not_now(self):
        for plan in ("claude_team", "claude_enterprise"):
            self.write_cfg(plan=plan)
            rc, d, _ = self.run_cli("scan")
            self.assertEqual(self.item(d, "screen")["tier"], "not_now", plan)

    def test_windows_screen_not_now(self):
        os.environ["CYS_CC_PLATFORM"] = "win"
        os.environ["LOCALAPPDATA"] = os.path.join(self.tmp, "la")
        orig = self.m._run
        self.m._run = lambda argv: subprocess.CompletedProcess(argv, 1, "", "")
        try:
            rc, d, _ = self.run_cli("scan")
        finally:
            self.m._run = orig
        self.assertEqual(self.item(d, "screen")["tier"], "not_now")
        self.assertIn("윈도우", d["say"])

    def test_wsl_chrome_not_now(self):
        os.environ["CYS_CC_PLATFORM"] = "wsl"
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "chrome")["tier"], "not_now")

    def test_chrome_absent_not_now(self):
        self.make_chrome(app=False)
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "chrome")["tier"], "not_now")

    def test_chrome_missing_ext_is_hand(self):
        self.make_chrome(ext=False)
        rc, d, _ = self.run_cli("scan")
        it = self.item(d, "chrome")
        self.assertEqual(it["tier"], "hand")
        self.assertFalse(it["unknown"])

    def test_chrome_disabled_ext_is_hand(self):
        self.make_chrome(disabled=True)
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "chrome")["tier"], "hand")

    def test_chrome_nmh_missing_or_dangling_is_hand(self):
        self.make_chrome(nmh=False)
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "chrome")["tier"], "hand")
        shutil.rmtree(self.ud)
        self.make_chrome(nmh_target=False)
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "chrome")["tier"], "hand")

    def test_chrome_default_off_is_hand(self):
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "chrome")["tier"], "hand")
        self.assertIn("/chrome", d["say"])

    def test_browser_alt_only_when_chrome_not_ready(self):
        self.make_chrome()
        rc, d, _ = self.run_cli("scan")
        self.assertIsNone(self.item(d, "browser-alt"))
        shutil.rmtree(self.ud)
        self.make_chrome(ext=False)
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "browser-alt")["tier"], "hand")

    def test_connectors(self):
        self.write_cfg(connectors=())
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "connectors")["tier"], "hand")
        self.write_cfg(logged_in=False)
        rc, d, _ = self.run_cli("scan")
        it = self.item(d, "connectors")
        self.assertEqual(it["tier"], "hand")
        self.assertTrue(it["unknown"])

    def test_script_codes_and_merge(self):
        self.set_probes(ae={"com.apple.finder": 0, "com.apple.mail": -1744, "com.apple.iCal": -1744})
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "script:finder")["tier"], "ready")
        merged = self.item(d, "script:mail,calendar")
        self.assertIsNotNone(merged, [it["id"] for it in d["items"]])
        self.assertEqual(merged["tier"], "hand")
        self.set_probes(ae={"com.apple.finder": -1743, "com.apple.mail": -600, "com.apple.iCal": 0})
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "script:finder")["tier"], "hand")
        self.assertTrue(self.item(d, "script:mail")["unknown"])

    def test_merged_id_rejudged_by_members(self):
        self.set_probes(ae={"com.apple.finder": 0, "com.apple.mail": 0, "com.apple.iCal": 0})
        self.run_cli("scan")
        self.set_probes(ae={"com.apple.finder": 0, "com.apple.mail": -1743, "com.apple.iCal": 0})
        it = self.m._scan_item("script:finder,mail,calendar")
        self.assertIsNotNone(it)
        self.assertEqual(it["tier"], "hand", "구성원 하나가 꺼지면 합친 줄도 손")

    def test_cu_project_lookup_strict(self):
        other = os.path.join(self.home, "other", "deep")    # 자기 기록 없음 · 유일한 상위 기록 = 홈(켜짐)
        os.makedirs(other)
        self.write_cfg(cu=False, extra_projects={self.home: {"enabledMcpServers": ["computer-use"]}})
        os.environ["CYS_CC_PROJECT"] = other
        rc, d, _ = self.run_cli("scan")
        self.assertNotEqual(self.item(d, "screen")["tier"], "ready", "상위(홈) 기록을 빌려 쓰면 안 된다")
        sub = os.path.join(self.proj, "deep")
        os.makedirs(sub)
        os.environ["CYS_CC_PROJECT"] = sub
        os.makedirs(os.path.join(self.proj, ".git"))
        self.write_cfg(cu=True)
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "screen")["tier"], "ready", "git 최상위 기록은 쓴다")

    def test_apps_folded_into_screen(self):
        for n in ("KakaoTalk.app", "Microsoft Word.app"):
            os.makedirs(os.path.join(self.apps, n))
        rc, d, _ = self.run_cli("scan")
        it = self.item(d, "screen")
        self.assertIn("카카오톡", d["say"])
        self.assertIn("Word", d["say"])
        self.assertFalse([x for x in d["items"] if x["id"].startswith("app:")])

    def test_win_script_not_now(self):
        os.environ["CYS_CC_PLATFORM"] = "win"
        os.environ["ProgramFiles"] = os.path.join(self.tmp, "pf")
        os.makedirs(os.path.join(self.tmp, "pf", "HNC"))
        self.m._run = lambda argv: subprocess.CompletedProcess(argv, 1, "", "")
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "script:win")["tier"], "not_now")

    def test_say_line_cap(self):
        self.m.MAX_SAY_LINES = 5
        self.make_protected()
        rc, d, _ = self.run_cli("scan")
        self.assertLessEqual(len(d["say"].splitlines()), 5)
        self.assertIn("더 있습니다", d["say"])


# ───────────────────────── 경계 ─────────────────────────
class TestBoundaries(Base):
    def _all_verbs(self):
        outs = []
        for argv in (("scan",), ("grant", "--scan", "__SEEN__", "--pick", "1,2,3", "--answer-file", self.answer()),
                     ("status",), ("guide", "screen"), ("recheck", "chrome"), ("revoke", "chrome")):
            argv = tuple(self.seen_scan_id() if x == "__SEEN__" else x for x in argv)
            outs.append(self.run_cli(*argv)[2])
        return outs

    def test_privacy_no_markers_in_any_output(self):
        self.make_chrome()
        self.make_protected()
        self.write_cfg(cu=False)
        outs = self._all_verbs()
        blob = "\n".join(outs)
        for root, _d, files in os.walk(self.state):
            for f in files:
                blob += "\n".join(lines(os.path.join(root, f)))
        for mark in MARKS + ("private-Desktop", "secret-cookie", "secret-login"):
            self.assertNotIn(mark, blob, mark)

    def test_no_protected_or_secret_reads(self):
        self.make_chrome()
        self.make_protected()
        seen = []
        real_listdir, real_open, real_scandir = os.listdir, builtins.open, os.scandir

        def rec(p):
            seen.append(os.path.realpath(str(p)))

        def listdir(p="."):
            rec(p)
            return real_listdir(p)

        def scandir(p="."):
            rec(p)
            return real_scandir(p)

        def opener(p, *a, **k):
            if isinstance(p, (str, bytes, os.PathLike)):
                rec(p)
            return real_open(p, *a, **k)
        os.listdir, builtins.open, os.scandir = listdir, opener, scandir
        try:
            self._all_verbs()
        finally:
            os.listdir, builtins.open, os.scandir = real_listdir, real_open, real_scandir
        bad_roots = [os.path.realpath(os.path.join(self.home, s)) for s in ("Desktop", "Documents", "Downloads")]
        for p in seen:
            for b in bad_roots:
                self.assertFalse(p == b or p.startswith(b + os.sep), "보호 폴더 열람: %s" % p)
            self.assertNotIn("Cookies", p)
            self.assertNotIn("Login Data", p)
            self.assertNotIn("Keychains", p)
            self.assertNotIn("Local State", p)

    def test_settings_files_unchanged_and_writes_only_state(self):
        self.make_chrome()
        snap = {}
        for root, _d, files in os.walk(self.tmp):
            for f in files:
                p = os.path.join(root, f)
                with open(p, "rb") as fh:
                    snap[p] = fh.read()
        self._all_verbs()
        for p, b in snap.items():
            if p.startswith(self.state) or p == self.answer():
                continue
            with open(p, "rb") as fh:
                self.assertEqual(fh.read(), b, "바뀐 파일: %s" % p)
        for root, _d, files in os.walk(self.tmp):
            for f in files:
                p = os.path.join(root, f)
                if p not in snap:
                    self.assertTrue(p.startswith(self.state) or p.endswith("answer.txt"), "상태 폴더 밖 쓰기: %s" % p)

    def test_real_state_untouched(self):
        before = os.path.exists(REAL_STATE) and sorted(os.listdir(REAL_STATE))
        self._all_verbs()
        after = os.path.exists(REAL_STATE) and sorted(os.listdir(REAL_STATE))
        self.assertEqual(before, after)

    def test_ask_user_flag_is_false(self):
        self.assertIs(self.m.ASK_USER_IF_NEEDED, False)

    def test_open_settings_allowlist(self):
        calls = []
        self.m._run = lambda argv: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", "")
        rc, d, _ = self.run_cli("open-settings", "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles")
        self.assertEqual(rc, 5)
        rc, d, _ = self.run_cli("open-settings", "screen")
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [["/usr/bin/open", self.m.SETTINGS_URLS["screen"]]])
        os.environ["CYS_CC_PLATFORM"] = "win"
        rc, d, _ = self.run_cli("open-settings", "screen")
        self.assertEqual(rc, 5)
        self.assertEqual(len(calls), 1)

    def test_request_prompt_needs_meaning_yes(self):
        rc, d, _ = self.run_cli("request-prompt", "ax", "--answer-file", self.answer("아니요, 띄우지 마세요"),
                                "--meaning", "no")
        self.assertEqual((rc, d["reason"]), (5, "not_yes"))

    def test_request_prompt_requires_user_answer(self):
        empty = os.path.join(self.tmp, "empty.txt")
        open(empty, "w").close()
        rc, d, _ = self.run_cli("request-prompt", "ax", "--answer-file", empty, "--meaning", "yes")
        self.assertEqual(rc, 2)
        rc, d, _ = self.run_cli("request-prompt", "sc", "--answer-file", self.answer("네 띄워 주세요"), "--meaning", "yes")
        self.assertEqual(rc, 0)
        os.environ["CYS_CC_PLATFORM"] = "win"
        rc, d, _ = self.run_cli("request-prompt", "sc", "--answer-file", self.answer("네"), "--meaning", "yes")
        self.assertEqual(rc, 5)

    def test_subprocess_stdin_devnull(self):
        seen = {}

        def fake_run(argv, **kw):
            seen.update(kw)
            return subprocess.CompletedProcess(argv, 1, "", "")
        orig = self.m.subprocess.run
        self.m.subprocess.run = fake_run
        try:
            self.m._run(["reg", "query", "x"])
        finally:
            self.m.subprocess.run = orig
        self.assertIs(seen.get("stdin"), subprocess.DEVNULL)
        self.assertEqual(seen.get("timeout"), self.m.SUBPROC_TIMEOUT)


# ───────────────────────── 장부 ─────────────────────────
class TestGrants(Base):
    def grants(self):
        return jload(os.path.join(self.state, "grants.json"))["items"]

    def test_grant_only_picked(self):
        self.make_chrome()
        rc, d, _ = self.run_cli("scan")
        n_chrome = self.item(d, "chrome")["n"]
        rc, g, _ = self.grant_cli("--pick", str(n_chrome), "--answer-file", self.answer())
        self.assertEqual(rc, 0, g)
        self.assertEqual(sorted(self.grants()), ["chrome"])

    def test_grant_gates(self):
        rc, d, _ = self.grant_cli("--pick", "1", "--answer-file", self.answer())
        self.assertEqual((rc, d["reason"]), (7, "no_scan"))
        self.run_cli("scan")
        rc, d, _ = self.grant_cli("--pick", "99", "--answer-file", self.answer())
        self.assertEqual(rc, 4)
        rc, d, _ = self.grant_cli("--pick", "1", "--answer-file", self.answer(" \n"))
        self.assertEqual(rc, 2)
        rc, d, _ = self.grant_cli("--pick", "다", "--answer-file", self.answer())
        self.assertEqual(rc, 2)
        sp = os.path.join(self.state, "scan.json")
        s = jload(sp)
        s["ts"] = time.time() - 31 * 60
        with open(sp, "w") as f:
            json.dump(s, f)
        rc, d, _ = self.grant_cli("--pick", "1", "--answer-file", self.answer())
        self.assertEqual((rc, d["reason"]), (7, "stale_scan"))

    def test_not_now_refused(self):
        self.write_cfg(plan="claude_team")
        rc, d, _ = self.run_cli("scan")
        n = self.item(d, "screen")["n"]
        rc, g, _ = self.grant_cli("--pick", str(n), "--answer-file", self.answer())
        self.assertEqual(rc, 5)
        self.assertFalse(os.path.exists(os.path.join(self.state, "grants.json")))

    def test_hand_is_pending_then_recheck_activates(self):
        self.set_probes(sc=False)
        rc, d, _ = self.run_cli("scan")
        n = self.item(d, "screen")["n"]
        rc, g, _ = self.grant_cli("--pick", str(n), "--answer-file", self.answer())
        self.assertEqual(g["pending"], ["screen"])
        self.assertIn("1단계", g["say"])
        self.assertEqual(self.grants()["screen"]["state"], "pending")
        rc, r, _ = self.run_cli("recheck", "screen")
        self.assertEqual(self.grants()["screen"]["state"], "pending")
        self.set_probes(sc=True)
        rc, r, _ = self.run_cli("recheck", "screen")
        self.assertEqual(r["tier"], "ready")
        self.assertEqual(self.grants()["screen"]["state"], "active")

    def test_first_use_only_active(self):
        self.make_protected()
        rc, d, _ = self.run_cli("scan")
        it = self.item(d, "files:desktop,documents,downloads")
        self.assertEqual(it["tier"], "hand")
        rc, g, _ = self.grant_cli("--pick", str(it["n"]), "--answer-file", self.answer())
        for mid in ("files:desktop", "files:documents", "files:downloads"):
            self.assertEqual(self.grants()[mid]["state"], "active", mid)

    def test_guide_steps_only_missing(self):
        self.set_probes(ax=True, sc=False)
        self.write_cfg(cu=True)
        rc, g, _ = self.run_cli("guide", "screen")
        self.assertEqual(g["total"], 3)
        self.assertIn("화면 및 시스템 오디오 녹음", g["say"])
        rc, g, _ = self.run_cli("guide", "screen", "--step", "99")
        self.assertTrue(g["last"])

    def test_revoke_removes(self):
        self.make_chrome()
        rc, d, _ = self.run_cli("scan")
        self.grant_cli("--pick", str(self.item(d, "chrome")["n"]), "--answer-file", self.answer())
        rc, r, _ = self.run_cli("revoke", "chrome")
        self.assertEqual(rc, 0)
        self.assertEqual(self.grants(), {})
        rc, r, _ = self.run_cli("revoke", "chrome")
        self.assertEqual(rc, 4)

    def test_status_warns_when_active_turns_off(self):
        self.run_cli("scan")
        rc, d, _ = self.run_cli("scan")
        self.grant_cli("--pick", str(self.item(d, "screen")["n"]), "--answer-file", self.answer())
        self.set_probes(ax=False)
        rc, s, _ = self.run_cli("status")
        self.assertIn("꺼져 있습니다", s["say"])

    def test_ledger_append_only(self):
        self.make_chrome()
        lp = os.path.join(self.state, "ledger.jsonl")
        sizes = []
        rc, d, _ = self.run_cli("scan")
        for argv in (("grant", "--pick", str(self.item(d, "chrome")["n"]), "--answer-file", self.answer()),
                     ("revoke", "chrome"),
                     ("grant", "--pick", str(self.item(d, "chrome")["n"]), "--answer-file", self.answer())):
            (self.grant_cli(*argv[1:]) if argv[0] == "grant" else self.run_cli(*argv))
            sizes.append(os.path.getsize(lp))
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual(len(lines(lp)), 3)

    # ── codex 1R 회귀 ──
    def test_grant_bound_to_seen_list(self):
        self.make_chrome(ext=False)              # A 목록: chrome 은 손, connectors 는 바로
        rc, a, _ = self.run_cli("scan")
        seen = a["scan_id"]
        n_chrome = self.item(a, "chrome")["n"]
        self.run_cli("scan")                     # 다른 대화가 다시 살펴봄(목록 교체)
        rc, d, _ = self.run_cli("grant", "--scan", seen, "--pick", str(n_chrome), "--answer-file", self.answer())
        self.assertEqual((rc, d["reason"]), (7, "scan_replaced"))
        self.assertFalse(os.path.exists(os.path.join(self.state, "grants.json")))
        rc, b, _ = self.run_cli("scan")
        os.environ["CYS_CC_PROJECT"] = os.path.join(self.home, "other-folder")
        rc, d, _ = self.run_cli("grant", "--scan", b["scan_id"], "--pick", "1", "--answer-file", self.answer())
        self.assertEqual((rc, d["reason"]), (7, "scan_replaced"), "다른 폴더에서 본 목록으로 넘기지 않는다")

    def test_member_revoke_removes_everywhere(self):
        self.set_probes(ae={"com.apple.finder": 0, "com.apple.mail": 0, "com.apple.iCal": 0})
        rc, d, _ = self.run_cli("scan")
        merged = self.item(d, "script:finder,mail,calendar")
        self.grant_cli("--pick", str(merged["n"]), "--answer-file", self.answer())
        self.assertEqual(sorted(self.grants()), ["script:calendar", "script:finder", "script:mail"])
        self.set_probes(ae={"com.apple.finder": 0, "com.apple.mail": -1744, "com.apple.iCal": 0})
        rc, d, _ = self.run_cli("scan")
        self.grant_cli("--pick", str(self.item(d, "script:mail")["n"]), "--answer-file", self.answer())
        rc, r, _ = self.run_cli("revoke", "script:mail")
        self.assertEqual(rc, 0)
        self.assertNotIn("script:mail", self.grants())
        self.assertEqual(sorted(self.grants()), ["script:calendar", "script:finder"])
        rc, r, _ = self.run_cli("revoke", "script:finder,calendar")
        self.assertEqual(self.grants(), {})

    def test_legacy_merged_key_normalized(self):
        os.makedirs(self.state, exist_ok=True)
        with open(os.path.join(self.state, "grants.json"), "w") as f:
            json.dump({"items": {"script:mail,calendar": {"state": "active", "title": "x"}}}, f)
        rc, r, _ = self.run_cli("revoke", "script:mail")
        self.assertEqual(rc, 0)
        self.assertEqual(sorted(self.grants()), ["script:calendar"])

    def test_ledger_failure_leaves_no_active(self):
        self.make_chrome()
        rc, d, _ = self.run_cli("scan")

        def boom(event):
            raise PermissionError("ledger")
        self.m._ledger = boom
        rc, g, _ = self.grant_cli("--pick", str(self.item(d, "chrome")["n"]), "--answer-file", self.answer())
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(os.path.join(self.state, "grants.json")), "기록 실패인데 장부가 바뀜")

    def test_recheck_ledger_failure_keeps_pending(self):
        self.set_probes(sc=False)
        rc, d, _ = self.run_cli("scan")
        self.grant_cli("--pick", str(self.item(d, "screen")["n"]), "--answer-file", self.answer())
        self.set_probes(sc=True)

        def boom(event):
            raise PermissionError("ledger")
        self.m._ledger = boom
        rc, r, _ = self.run_cli("recheck", "screen")
        self.assertEqual(rc, 1)
        self.assertEqual(self.grants()["screen"]["state"], "pending")

    def test_recheck_merged_reports_per_member(self):
        # codex R2 재현 ①: 묶음을 맡기고 메일만 거둔 뒤 옛 묶음 ID 로 recheck → 메일을 맡는다고 말하면 안 된다
        self.set_probes(ae={"com.apple.finder": 0, "com.apple.mail": 0, "com.apple.iCal": 0})
        rc, d, _ = self.run_cli("scan")
        merged = self.item(d, "script:finder,mail,calendar")
        self.grant_cli("--pick", str(merged["n"]), "--answer-file", self.answer())
        self.run_cli("revoke", "script:mail")
        rc, r, _ = self.run_cli("recheck", "script:finder,mail,calendar")
        self.assertNotIn("script:mail", r["states"])
        self.assertNotIn("script:mail", self.grants())
        held_line = r["say"].split("이제 제가 맡습니다")[0]
        self.assertNotIn("메일", held_line)
        self.assertIn("맡기지 않으셨습니다", r["say"])

    def test_recheck_merged_activates_all_pending_members(self):
        # codex R2 재현 ②: 첫 구성원 active · 다음 구성원 pending → recheck 가 pending 도 활성화·기록
        os.makedirs(self.state, exist_ok=True)
        with open(os.path.join(self.state, "grants.json"), "w") as f:
            json.dump({"items": {"script:finder": {"state": "active", "title": "Finder"},
                                 "script:mail": {"state": "pending", "title": "메일"}}}, f)
        self.set_probes(ae={"com.apple.finder": 0, "com.apple.mail": 0, "com.apple.iCal": 0})
        rc, r, _ = self.run_cli("recheck", "script:finder,mail")
        self.assertEqual(self.grants()["script:mail"]["state"], "active")
        self.assertEqual(r["states"], {"script:finder": "active", "script:mail": "active"})
        led = lines(os.path.join(self.state, "ledger.jsonl"))
        self.assertTrue(any('"activate"' in l and "script:mail" in l for l in led))

    def test_ledger_cap(self):
        self.m.MAX_LEDGER_LINES = 4
        for _ in range(7):
            self.m._ledger({"event": "x"})
        self.assertEqual(len(lines(os.path.join(self.state, "ledger.jsonl"))), 4)


if __name__ == "__main__":
    unittest.main()
