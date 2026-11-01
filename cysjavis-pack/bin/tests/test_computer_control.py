#!/usr/bin/env python3
"""test_computer_control.py — javis_computer_control.py 계약 시험 (TICKET=cu-1111 · 설계 docs/DESIGN-cu-1111.md).

격리: 매 시험이 임시 HOME · 임시 클로드 설정 폴더 · 임시 상태 폴더 · 임시 앱 자리(CYS_CC_APP_ROOTS)를 세우고,
맥 권한 탐지(AX·화면 기록·앱 자동화)는 CYS_CC_FAKE_PROBES 로 주입한다. 실 ~/.cys/computer-control 무접촉.
뮤턴트 하네스(mut_computer_control.py)는 CC_MODULE 로 변이 사본을 가리키고 이 파일을 그대로 돌린다.
"""
import builtins
import hashlib
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
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD_PATH = os.environ.get("CC_MODULE") or os.path.join(BIN, "javis_computer_control.py")
REAL_STATE = os.path.join(os.path.expanduser("~"), ".cys", "computer-control")

EMAIL = "CC-TEST-EMAIL@example.com"
NAME = "CC-TEST-NAME"
ORG = "CC-TEST-ORG"
PROFILE = "CC-TEST-PROFILE"
MARKS = (EMAIL, NAME, ORG, PROFILE)
EXT = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
PW = "mmlmfjhmonkocbjadbfplnigmagldckm"


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def rb(p):
    with open(p, "rb") as f:
        return f.read()


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
        d = {"claudeAiMcpEverConnected": list(connectors),
             "projects": {self.proj: {"enabledMcpServers": ["computer-use"] if cu else []}}}
        if chrome_default is not None:   # None = 키 없음(좌석 설정 폴더에 /chrome 을 한 번도 안 한 경우)
            d["claudeInChromeDefaultEnabled"] = chrome_default
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

    def test_chrome_nmh_missing_or_dangling_is_ready_auto(self):
        # chrome-preset: 연결 파일 없음·끊김 = 다음 좌석 시작이 만든다(사용자 손 0) → 바로(제가 할 것)
        self.make_chrome(nmh=False)
        rc, d, _ = self.run_cli("scan")
        it = self.item(d, "chrome")
        self.assertEqual((it["tier"], it["unknown"]), ("ready", False))
        self.assertIn("제가 할 것", d["say"])
        shutil.rmtree(self.ud)
        self.make_chrome(nmh_target=False)
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "chrome")["tier"], "ready")

    def test_chrome_default_off_is_ready_auto(self):
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(self.item(d, "chrome")["tier"], "ready")
        self.assertNotIn("/chrome", d["say"])          # 사용자에게 /chrome 을 시키지 않는다(박사님 10-26 21:0x)
        self.assertIn("크롬 기본 켜기(제가 합니다)", d["say"])

    def test_chrome_default_key_absent_is_off(self):
        # 윈 실기 10-26 r2: 키 없음 = 공식 기본값(꺼짐) — 「모름」이 아니다 → 이제는 마스터가 켜는 바로 칸
        self.make_chrome()
        self.write_cfg(chrome_default=None)
        rc, d, _ = self.run_cli("scan")
        it = self.item(d, "chrome")
        self.assertEqual((it["tier"], it["unknown"]), ("ready", False))
        self.write_cfg(chrome_default="yes")             # 값이 이상하면 여전히 모름(→ 손 · 바로 아님)
        rc, d, _ = self.run_cli("scan")
        it = self.item(d, "chrome")
        self.assertEqual((it["tier"], it["unknown"]), ("hand", True))

    def test_chrome_ext_missing_plus_auto_stays_hand(self):
        # 확장 설치·로그인 = 사람(웹 스토어 클릭·로그인) — 마스터가 할 것이 섞여 있어도 손 칸 · 안내는 확장 단계만
        self.make_chrome(ext=False, nmh=False)
        self.write_cfg(chrome_default=False)
        rc, d, _ = self.run_cli("scan")
        it = self.item(d, "chrome")
        self.assertEqual(it["tier"], "hand")
        rc, g, _ = self.run_cli("guide", "chrome")
        self.assertIn("웹 스토어", g["say"])
        self.assertNotIn("/chrome", g["say"])

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

    def win_desktop_say(self):
        os.environ["CYS_CC_PLATFORM"] = "win"
        self.m._run = lambda argv: subprocess.CompletedProcess(argv, 1, "", "")
        rc, d, _ = self.run_cli("scan")
        self.assertEqual(rc, 0)
        return self.item(d, "screen") and d["say"]

    def test_win_claude_desktop_msix(self):
        # 윈 실기 10-26 ③: MSIX 설치(WindowsApps) — 사용자 자료 폴더가 근거 · 목록 거부면 「?」 · 목록에 없으면 못 찾음.
        la = os.path.join(self.tmp, "la")
        pf = os.path.join(self.tmp, "pf")
        os.environ["LOCALAPPDATA"] = la
        os.environ["ProgramFiles"] = pf
        os.makedirs(os.path.join(la, "Packages", "Claude_pzs8sxrjxfjjc"))
        self.assertIn("데스크톱 앱: 이 컴퓨터에 설치돼 있습니다", self.win_desktop_say())
        shutil.rmtree(os.path.join(la, "Packages"))
        self.assertIn("데스크톱 앱: ? — 설치돼 있는지 확인하지 못했습니다", self.win_desktop_say())   # WindowsApps 못 읽음
        os.makedirs(os.path.join(pf, "WindowsApps", "Other_1.0.0.0_x64__pzs8sxrjxfjjc"))
        self.assertIn("데스크톱 앱: 찾지 못했습니다", self.win_desktop_say())
        os.makedirs(os.path.join(pf, "WindowsApps", "Claude_2.19675.0.0_x64__pzs8sxrjxfjjc"))
        self.assertIn("데스크톱 앱: 이 컴퓨터에 설치돼 있습니다", self.win_desktop_say())

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
                     ("status",), ("guide", "screen"), ("recheck", "chrome"), ("revoke", "chrome"),
                     ("adopt",), ("decide", "login", "--subject", "gmail")):
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


    def test_cp949_stdout_scan_utf8(self):
        # 윈 실기 10-26 ①: 콘솔 코드페이지 cp949(UTF-8 모드 꺼짐)에서도 scan rc 0 · 출력은 UTF-8(마스터가 읽는 쪽).
        os.environ["CYS_CC_PLATFORM"] = "win"
        os.environ["LOCALAPPDATA"] = os.path.join(self.tmp, "la")
        env = dict(os.environ, PYTHONIOENCODING="cp949", PYTHONUTF8="0", PATH="")
        r = subprocess.run([sys.executable, MOD_PATH, "scan"], env=env, capture_output=True,
                           stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
        d = json.loads(r.stdout.decode("utf-8"))
        self.assertTrue(d["ok"])
        self.assertIn("—", d["say"])
        self.assertIn("윈도우", d["say"])

    def test_reg_output_cp949_decoded(self):
        # 윈 실기 10-26 ②: reg 출력(cp949 바이트)은 UTF-8 모드여도 OEM/ANSI 로 푼다 · 못 풀어도 칸 판정을 바꾸지 않는다.
        host = os.path.join(self.tmp, "홍길동", "chrome-native-host.exe")
        os.makedirs(os.path.dirname(host))
        open(host, "w").close()
        manifest = os.path.join(self.tmp, "홍길동", "nmh.json")
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump({"name": "x", "path": host}, f)
        reg_out = {"rc": 0, "out": ("\r\nHKEY_CURRENT_USER\\x\r\n    (기본값)    REG_SZ    %s\r\n\r\n" % manifest).encode("cp949")}

        def fake_run(argv, **kw):
            out = reg_out["out"]
            if kw.get("text"):   # UTF-8 모드의 text=True 와 같게 — 못 풀면 읽기 스레드가 죽고 stdout 은 None
                try:
                    out = out.decode("utf-8")
                except UnicodeDecodeError:
                    out = None
            return subprocess.CompletedProcess(argv, reg_out["rc"], out, b"" if not kw.get("text") else "")
        orig = self.m.subprocess.run
        self.m.subprocess.run = fake_run
        self.m._sys_codecs = lambda: ["cp949", "cp949"]
        try:
            self.assertIs(self.m._nmh_ok("win", self.ud), True)
            reg_out.update(rc=1, out=b"\xbf\xff\xbf")          # 어느 코드페이지로도 안 풀리는 바이트 + 키 없음
            self.assertIs(self.m._nmh_ok("win", self.ud), False)
        finally:
            self.m.subprocess.run = orig


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
        rc, r, _ = self.run_cli("revoke", "connectors")        # 크롬은 장부에 없어도 거둔다(test_revoke_chrome_*)
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


# ───────────────────────── 크롬 켜기·끄기 = 한 키만 (chrome-preset) ─────────────────────────
NEXT_SAY = "다음에 cysr 를 다시 시작하거나 업데이트할 때 연결됩니다."     # 문구 고정(브리프 cysr-1111-chrome-preset §2)
OLD_DEBT = {"pending_seat_restart": True, "pending_chrome_restart": True, "pending_chrome_reopen": True, "chrome_reopen_tries": 2,
            "chrome_reopen_at": 5, "chrome_manual_at": 5, "chrome_in_job": {"pid": 9}, "seat_guided_daemon": 7,
            "seat_restart_scheduled_at": 5, "seat_restart_pid": 9, "seat_restart_start": "t", "nmh_created": {"path": "/x", "sha256": "y"}}


class TestChromeEnable(Base):
    """실제 크롬·좌석 무접촉: 이 동작은 프로세스를 띄우지 않는다(윈 연결 등록 읽기 1건 예외) — 띄우면 spawned 에 남고 실패한다."""
    def setUp(self):
        super().setUp()
        self.manifest = os.path.join(self.ud, "NativeMessagingHosts", "com.anthropic.claude_code_browser_extension.json")
        self.sp = os.path.join(self.state, "chrome-enable.json")
        self.set_probes(ae={"com.google.Chrome": 0})
        self.spawned = []

        def no_spawn(argv, *a, **k):
            self.spawned.append(argv)
            raise OSError("이 동작은 프로세스를 띄우지 않는다")
        patcher = mock.patch.object(self.m.subprocess, "Popen", no_spawn)
        patcher.start()
        self.addCleanup(patcher.stop)

    def cfg(self):
        return jload(os.path.join(self.ccd, ".claude.json"))

    def write_state(self, **st):
        os.makedirs(self.state, exist_ok=True)
        with open(self.sp, "w", encoding="utf-8") as f:
            json.dump(st, f)

    def as_win(self, nmh):
        os.environ["CYS_CC_PLATFORM"] = "win"
        self.set_probes(chrome={"app": True, "profiles": 1, "with_ext": 1, "ext_enabled": True,
                                "nmh": nmh, "default_on": False, "playwright_ext": False})
        self.m._nmh_ok = lambda plat, ud: nmh

    def test_enable_writes_only_the_key(self):
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        p = os.path.join(self.ccd, ".claude.json")
        os.chmod(p, 0o600)
        before = self.cfg()
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual(rc, 0, d)
        after = self.cfg()
        self.assertIs(after.pop("claudeInChromeDefaultEnabled"), True)
        before.pop("claudeInChromeDefaultEnabled")
        self.assertEqual(after, before)                       # 다른 칸은 그대로
        if os.name != "nt":                                   # NTFS 는 유닉스 권한 비트가 없다(st_mode 0o666 고정)
            self.assertEqual(os.stat(p).st_mode & 0o777, 0o600)   # 권한 유지
        self.assertEqual((d["done"], d["pending"]), (["default_on"], []))
        self.assertIn(NEXT_SAY, d["say"])
        self.assertIn("되돌릴 수 있습니다", d["say"])
        self.assertEqual(self.spawned, [])

    def test_enable_already_on_says_so_and_touches_nothing(self):
        self.make_chrome()
        p = os.path.join(self.ccd, ".claude.json")
        raw = rb(p)
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual((rc, d["done"], d["nmh"]), (0, [], True))
        self.assertEqual(d["say"], "크롬 연결은 이미 켜져 있습니다. 이 대화에 크롬 도구가 보이지 않으면 " + NEXT_SAY)      # 키가 켜져도 이 좌석은 그 전에 시작했을 수 있다
        self.assertEqual(rb(p), raw)
        self.assertFalse(os.path.exists(self.sp))
        self.assertEqual(self.spawned, [])

    def test_key_on_without_connection_file_waits_for_next_start(self):
        for kw in ({"nmh": False}, {"nmh_target": False}):
            self.make_chrome(**kw)
            rc, d, _ = self.run_cli("chrome-enable")
            self.assertEqual((rc, d["done"], d["pending"]), (0, [], []))
            self.assertEqual(d["say"], "크롬 연결은 켜 두었습니다. " + NEXT_SAY)
            shutil.rmtree(self.ud)
        self.assertEqual(self.spawned, [])

    def test_enable_with_chrome_missing_writes_nothing(self):
        self.make_chrome(app=False)
        self.write_cfg(chrome_default=None)
        raw = rb(os.path.join(self.ccd, ".claude.json"))
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual((rc, d["reason"]), (5, "no_chrome"))
        self.assertEqual(rb(os.path.join(self.ccd, ".claude.json")), raw)

    def test_win_is_the_same_key_only_path(self):
        self.make_chrome()
        self.write_cfg(chrome_default=None)
        self.as_win(False)
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual((rc, d["done"]), (0, ["default_on"]))
        self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], True)
        self.assertIn(NEXT_SAY, d["say"])
        self.assertEqual(self.spawned, [])

    def test_runtime_paths_are_gone(self):
        for name in ("_ensure_nmh", "schedule_seat_restart", "cmd_seat_restart_wait", "restart_chrome", "quit_chrome", "open_chrome",
                     "reopen_chrome", "_outside_job", "_act"):
            self.assertFalse(hasattr(self.m, name), name)
        src = rb(self.m.__file__).decode("utf-8")
        for bad in ('"rotate"', "--restore-last-session", '"--chrome"', "spawn-outside-job", "seat-restart-wait"):
            self.assertNotIn(bad, src)
        for argv in (["chrome-enable", "--seat-restart", "no"], ["chrome-enable", "--wait", "1"], ["chrome-disable", "--seat-restart", "auto"],
                     ["seat-restart-wait"]):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(self.m.main(argv), 2, argv)

    def test_old_debt_is_dropped_without_acting(self):
        self.make_chrome()
        self.write_state(prior_key={"present": False, "value": None}, **OLD_DEBT)
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual((rc, d["done"], d["pending"]), (0, [], []))
        self.assertEqual(jload(self.sp), {"prior_key": {"present": False, "value": None}})
        self.assertEqual(self.spawned, [])

    def test_old_debt_with_key_off_still_only_writes_the_key(self):
        self.make_chrome(nmh=False)
        self.write_cfg(chrome_default=False)
        self.write_state(**OLD_DEBT)
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual((rc, d["done"]), (0, ["default_on"]))
        self.assertEqual(jload(self.sp), {"prior_key": {"present": True, "value": False}})
        self.assertEqual(self.spawned, [])

    def test_config_lock_respected(self):
        # codex R2 blocking: Claude Code 와 같은 잠금(.claude.json.lock)을 쥔 작성자가 있으면 쓰지 않는다 · 쓴 뒤 잠금을 푼다
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        p = os.path.join(self.ccd, ".claude.json")
        raw = rb(p)
        os.mkdir(p + ".lock")
        self.m.LOCK_WAIT_SEC = 0.2
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual(rc, 1)
        self.assertEqual(rb(p), raw)
        self.assertTrue(os.path.isdir(p + ".lock"))                  # 남의 잠금을 지우지 않는다
        os.rmdir(p + ".lock")
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(p + ".lock"))                # 내 잠금은 풀었다

    def test_disable_trusts_the_key_not_an_old_restored_record(self):
        # 독립 검증 m1: 옛 기록 key_restored 를 믿으면 키가 켜진 채 「되돌렸습니다」라고 답한다
        self.make_chrome()
        self.write_state(prior_key={"present": False, "value": None}, key_restored=True)
        rc, d, _ = self.run_cli("chrome-disable")
        self.assertEqual(rc, 0)
        self.assertNotIn("claudeInChromeDefaultEnabled", self.cfg())
        self.assertFalse(os.path.exists(self.sp))

    def test_non_master_seat_cannot_turn_chrome_on(self):
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        raw = rb(os.path.join(self.ccd, ".claude.json"))
        for role in ("worker", "worker-3", "cso", "reviewer-codex"):
            os.environ["CYS_ROLE"] = role
            rc, d, _ = self.run_cli("chrome-enable")
            self.assertEqual((rc, d["reason"]), (5, "not_master_seat"))
        self.assertEqual(rb(os.path.join(self.ccd, ".claude.json")), raw)
        os.environ["CYS_ROLE"] = "master"
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual((rc, d["done"]), (0, ["default_on"]))

    def test_dept_master_is_told_only_hq_master_seat(self):
        # 독립 검증 n7(codex #7): 부서 master 는 역할이 master 라도 좌석 env 로 꺼진다 — 「연결됩니다」는 거짓이다
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        raw = rb(os.path.join(self.ccd, ".claude.json"))
        os.environ["CYS_ROLE"] = "master"
        for k, v in (("CYS_SOCKET", "/h/.cys/cys-dept-9.sock"), ("CYS_PACK_DIR", "/h/.cys/pack-dept-sales/")):
            os.environ[k] = v
            rc, d, _ = self.run_cli("chrome-enable")
            self.assertEqual((rc, d["reason"]), (5, "not_master_seat"), k)
            self.assertEqual(d["say"], "크롬 연결은 본부 마스터 좌석에서만 씁니다 — 본부 마스터에게 맡겨 주세요.")
            del os.environ[k]
        self.assertEqual(rb(os.path.join(self.ccd, ".claude.json")), raw)

    @unittest.skipIf(os.name == "nt", "심볼릭 링크 권한")
    def test_symlinked_config_is_refused_not_replaced(self):
        # 독립 검증 M2: Claude Code 는 이 파일을 링크 너머로 쓴다 — 원자 교체는 링크를 끊어 설정을 갈라 놓는다
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        p = os.path.join(self.ccd, ".claude.json")
        real = os.path.join(self.tmp, "real.json")
        shutil.move(p, real)
        os.symlink(real, p)
        raw = rb(real)
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual((rc, d["reason"]), (1, "write_failed"))
        self.assertTrue(os.path.islink(p))
        self.assertEqual(rb(real), raw)

    def test_revoke_preset_chrome_turns_key_off_and_records_deny(self):
        # 독립 검증 M3: 설치가 켠 크롬은 장부에 없다 — 「크롬은 빼 줘」가 안 듣으면 공개 노트의 약속이 깨진다
        self.make_chrome()
        rc, d, _ = self.run_cli("revoke", "chrome")
        self.assertEqual(rc, 0, d)
        self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], False)
        self.assertIn("크롬 기본 켜기를 껐습니다", d["say"])
        self.assertIn("다음에 cysr 를 다시 시작하거나 업데이트할 때부터 적용됩니다", d["say"])
        self.assertEqual(jload(os.path.join(self.state, "decisions.json"))["items"]["take:chrome"]["meaning"], "deny")
        rc, a, _ = self.run_cli("adopt")
        self.assertNotIn("chrome", a["active"])                   # 다시 가져가지 않는다

    def test_revoke_preset_chrome_keeps_deny_when_key_cannot_be_written(self):
        self.make_chrome()
        p = os.path.join(self.ccd, ".claude.json")
        os.mkdir(p + ".lock")
        self.m.LOCK_WAIT_SEC = 0.2
        rc, d, _ = self.run_cli("revoke", "chrome")
        os.rmdir(p + ".lock")
        self.assertEqual((rc, d["reason"]), (1, "write_failed"))
        self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], True)
        self.assertEqual(jload(os.path.join(self.state, "decisions.json"))["items"]["take:chrome"]["meaning"], "deny")

    def test_revoke_chrome_with_key_off_records_deny_so_adopt_stays_away(self):
        # 독립 검증 n6(codex #6): 공개 노트 「크롬은 빼 줘 = 다시 가져가지 않는다」 — 이미 꺼져 있어도 기록이 있어야 한다
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        raw = rb(os.path.join(self.ccd, ".claude.json"))
        rc, d, _ = self.run_cli("revoke", "chrome")
        self.assertEqual(rc, 0, d)
        self.assertEqual(d["say"], "알겠습니다. 「크롬」은(는) 이제 맡지 않겠습니다.")
        rc, a, _ = self.run_cli("adopt")
        self.assertNotIn("chrome", a["active"])
        self.assertIsNone(a["next_action"])
        self.assertEqual(rb(os.path.join(self.ccd, ".claude.json")), raw)      # 키 false 유지

    def test_revoke_says_the_key_it_reads_back_not_the_one_it_meant(self):
        # 독립 검증 n4(codex #4): 옛 기록의 원래 값이 true 면 키는 켜진 채다 — 「껐습니다」라고 하지 않는다
        self.make_chrome()
        self.write_state(prior_key={"present": True, "value": True})
        rc, d, _ = self.run_cli("revoke", "chrome")
        self.assertEqual(rc, 0, d)
        self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], True)
        self.assertNotIn("껐습니다", d["say"])
        self.assertIn("켜진 채입니다", d["say"])

    def test_new_cycle_prior_is_value_just_before(self):
        # codex R4 major: 앞 주기를 되돌린 뒤 사용자가 키를 바꾸고 다시 켜면, 새 주기의 원래 값 = 바꾼 그 값
        self.make_chrome()
        for between in (False, None):
            self.write_state(prior_key={"present": True, "value": True}, key_restored=True)
            self.write_cfg(chrome_default=between)
            self.run_cli("chrome-enable")
            self.run_cli("chrome-disable")
            if between is None:
                self.assertNotIn("claudeInChromeDefaultEnabled", self.cfg())
            else:
                self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], between)

    def test_cas_conflict_leaves_file_untouched(self):
        # codex R1 blocking: 읽은 뒤 살아 있는 좌석이 다른 키를 고쳐 쓰면 덮지 않는다
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        p = os.path.join(self.ccd, ".claude.json")

        def concurrent():
            d = jload(p)
            d["numStartups"] = d.get("numStartups", 0) + 1     # 좌석이 그 사이 다른 키를 바꿈
            with open(p, "w") as f:
                json.dump(d, f)
        self.m._cas_hook = concurrent
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual(rc, 1)
        after = jload(p)
        self.assertEqual(after["numStartups"], self.m.CAS_TRIES)   # 남의 변경은 살아 있다
        self.assertIs(after["claudeInChromeDefaultEnabled"], False)
        self.m._cas_hook = lambda: None
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual(rc, 0)
        after = jload(p)
        self.assertEqual((after["numStartups"], after["claudeInChromeDefaultEnabled"]), (self.m.CAS_TRIES, True))

    def test_prior_saved_before_key_write(self):
        # codex R1 major: 되돌리기 정보가 키보다 먼저 디스크에 있어야 한다
        self.make_chrome()
        self.write_cfg(chrome_default=None)

        def check_then_fail(_v):
            self.assertEqual(jload(self.sp)["prior_key"], {"present": False, "value": None})
            raise OSError("disk")
        self.m.write_chrome_key = check_then_fail
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual(rc, 1)
        self.assertIn("prior_key", jload(self.sp))

    def test_ledger_failure_leaves_key_untouched(self):
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        p = os.path.join(self.ccd, ".claude.json")
        raw = rb(p)
        def boom(_e):
            raise OSError("ledger")
        self.m._ledger = boom
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual(rc, 1)
        self.assertEqual(rb(p), raw)

    def test_disable_without_record_turns_off(self):
        self.make_chrome()
        rc, d, _ = self.run_cli("chrome-disable")
        self.assertEqual(rc, 0, d)
        self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], False)
        self.assertEqual(d["say"], "크롬 기본 켜기를 껐습니다. 다음에 cysr 를 다시 시작하거나 업데이트할 때부터 적용됩니다.")
        self.assertEqual(self.spawned, [])

    def test_disable_restores_prior_absent(self):
        self.make_chrome()
        self.write_cfg(chrome_default=None)
        self.run_cli("chrome-enable")
        rc, d, _ = self.run_cli("chrome-disable")
        self.assertEqual(rc, 0, d)
        self.assertNotIn("claudeInChromeDefaultEnabled", self.cfg())
        self.assertIn("처음 상태로 되돌렸습니다", d["say"])
        self.assertFalse(os.path.exists(self.sp))

    def test_disable_never_touches_the_connection_file(self):
        self.make_chrome()
        raw = rb(self.manifest)
        self.write_state(**OLD_DEBT)                            # 옛 판의 「내가 만든 파일」 기록이 있어도
        rc, d, _ = self.run_cli("chrome-disable")
        self.assertEqual(rc, 0, d)
        self.assertEqual(rb(self.manifest), raw)
        self.assertFalse(os.path.exists(self.sp))
        self.assertEqual(self.spawned, [])

    def test_disable_lock_busy_keeps_record(self):
        self.make_chrome()
        self.write_state(prior_key={"present": True, "value": False})
        p = os.path.join(self.ccd, ".claude.json")
        os.mkdir(p + ".lock")
        self.m.LOCK_WAIT_SEC = 0.2
        rc, d, _ = self.run_cli("chrome-disable")
        self.assertEqual(rc, 1)
        os.rmdir(p + ".lock")
        self.assertEqual(jload(self.sp), {"prior_key": {"present": True, "value": False}})

    def test_grant_chrome_auto_points_to_enable(self):
        self.make_chrome()
        self.write_cfg(chrome_default=False)
        rc, d, _ = self.run_cli("scan")
        n = self.item(d, "chrome")["n"]
        rc, g, _ = self.grant_cli("--pick", str(n), "--answer-file", self.answer())
        self.assertEqual((g["active"], g["next_action"]), (["chrome"], "chrome-enable"))
        self.assertIn("제가 바로 켜겠습니다", g["say"])
        self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], False)   # grant 자체는 쓰지 않는다(쓰기 = chrome-enable 만)


# ───────────────────────── 선례 기반 이양 (cu-1111-precedent 2단계) ─────────────────────────
class TestPrecedent(Base):
    def setUp(self):
        super().setUp()
        self.make_chrome()

    def dec(self):
        p = os.path.join(self.state, "decisions.json")
        return jload(p)["items"] if os.path.exists(p) else {}

    def test_adopt_takes_ready_and_reports(self):
        self.set_probes(sc=False)                       # 화면 조작 = 손 칸
        rc, d, _ = self.run_cli("adopt")
        self.assertEqual(rc, 0, d)
        self.assertIn("chrome", d["active"])
        self.assertIn("connectors", d["active"])
        self.assertIn("screen", d["hand"])
        self.assertNotIn("screen", d["active"])         # 손 칸은 가져오지 않는다
        self.assertTrue(d["say"].startswith("이렇게 했습니다"))
        self.assertIn("다르게 원하시면 말씀해 주세요", d["say"])
        g = jload(os.path.join(self.state, "grants.json"))["items"]
        self.assertEqual(g["chrome"]["state"], "active")
        self.assertNotIn("screen", g)

    def test_adopt_idempotent(self):
        self.run_cli("adopt")
        rc, d, _ = self.run_cli("adopt")
        self.assertEqual(d["active"], [])
        self.assertIn("새로 맡을 것은 없습니다", d["say"])

    def test_adopt_respects_revoke_and_grant_lifts(self):
        self.run_cli("adopt")
        self.run_cli("revoke", "connectors")
        self.assertEqual(self.dec()["take:connectors"]["meaning"], "deny")
        rc, d, _ = self.run_cli("adopt")
        self.assertIn("connectors", d["skipped"])        # 빼라고 한 것은 다시 가져오지 않는다
        self.assertNotIn("connectors", d["active"])
        rc, s1, _ = self.run_cli("scan")
        n = self.item(s1, "connectors")["n"]
        self.grant_cli("--pick", str(n), "--answer-file", self.answer())
        self.assertNotIn("take:connectors", self.dec())   # 사용자가 직접 고르면 푼다
        rc, d, _ = self.run_cli("adopt")
        self.assertNotIn("connectors", d["skipped"])

    def test_adopt_chrome_auto_next_action(self):
        self.write_cfg(chrome_default=False)
        rc, d, _ = self.run_cli("adopt")
        self.assertEqual(d["next_action"], "chrome-enable")
        self.assertIn("크롬 연결 설정은 제가 바로 켜겠습니다", d["say"])
        self.assertIs(jload(os.path.join(self.ccd, ".claude.json"))["claudeInChromeDefaultEnabled"], False)

    def test_each_and_never_not_recordable(self):
        for cat, want in (("payment", "each"), ("signup", "each"), ("credential_input", "each"),
                          ("blocked", "never"), ("install_boundary", "never")):
            rc, d, _ = self.run_cli("decide", cat)
            self.assertEqual(d["decision"], want, cat)
            rc, r, _ = self.run_cli("remember", cat, "--answer-file", self.answer("네 항상 해"), "--meaning", "allow")
            self.assertEqual((rc, r["reason"]), (5, "not_recordable"), cat)
        os.makedirs(self.state, exist_ok=True)
        with open(os.path.join(self.state, "decisions.json"), "w") as f:     # 손으로 넣은 상시 기록도 못 뒤집는다
            json.dump({"items": {"payment:": {"meaning": "allow", "at": "t"}}}, f)
        rc, d, _ = self.run_cli("decide", "payment")
        self.assertEqual(d["decision"], "each")

    def test_login_in_use_from_usage_is_do_with_report(self):
        rc, d, _ = self.run_cli("decide", "login", "--subject", "gmail", "--what", "지메일 재로그인")
        self.assertEqual(d["decision"], "do")
        self.assertIn("이렇게 했습니다: 지메일 재로그인", d["report"])
        self.assertIn("커넥터", d["report"])
        self.assertIn("다르게 원하시면", d["report"])
        rc, d, _ = self.run_cli("decide", "login", "--subject", "brandnew.example", "--in-use", "no")
        self.assertEqual(d["decision"], "each")          # 처음 쓰는 서비스 = 가입 = 건마다

    def test_unknown_login_asks_once_then_remembers_no_reask(self):
        rc, d, _ = self.run_cli("decide", "login", "--subject", "hosting.kr")
        self.assertEqual(d["decision"], "ask")
        self.assertIn("한 번 여쭙고", d["ask"])
        rc, r, _ = self.run_cli("remember", "login", "--subject", "hosting.kr", "--answer-file", self.answer("응 맡아"),
                                "--meaning", "allow")
        self.assertEqual(rc, 0, r)
        self.assertIn("다시 여쭙지 않습니다", r["say"])
        rc, d, _ = self.run_cli("decide", "login", "--subject", "Hosting.KR")
        self.assertEqual((d["decision"], d["basis"][:9]), ("do", "standing:"))
        rc, r, _ = self.run_cli("remember", "login", "--subject", "hosting.kr", "--answer-file", self.answer("응"),
                                "--meaning", "deny")
        self.assertEqual((rc, r["reason"]), (7, "already_decided"))   # 재질문·재기록 금지
        rc, r, _ = self.run_cli("remember", "login", "--subject", "hosting.kr", "--answer-file", self.answer("이제 그만"),
                                "--meaning", "deny", "--user-changed")
        self.assertEqual(rc, 0)
        rc, d, _ = self.run_cli("decide", "login", "--subject", "hosting.kr")
        self.assertEqual(d["decision"], "never")

    def test_terms_service_is_each(self):
        for cat in ("login", "external_send"):
            rc, d, _ = self.run_cli("decide", cat, "--subject", "네이버 블로그")
            self.assertEqual(d["decision"], "each", cat)
            self.assertIn("약관", d["ask"])

    def test_new_type_asks(self):
        rc, d, _ = self.run_cli("decide", "drone_flight")
        self.assertEqual((d["decision"], d["basis"]), ("ask", "new_type"))

    def test_new_type_answer_is_remembered_no_reask(self):
        rc, d, _ = self.run_cli("decide", "drone_flight", "--subject", "교회 행사 촬영")
        self.assertEqual(d["decision"], "ask")
        rc, r, _ = self.run_cli("remember", "drone_flight", "--subject", "교회 행사 촬영",
                                "--answer-file", self.answer("그건 해도 돼"), "--meaning", "allow")
        self.assertEqual(rc, 0, r)
        rc, d, _ = self.run_cli("decide", "drone_flight", "--subject", "교회 행사 촬영")
        self.assertEqual((d["decision"], d["basis"][:9]), ("do", "standing:"))   # 새 유형도 한 번 물은 것은 다시 묻지 않는다

    def test_external_send_conditional(self):
        rc, d, _ = self.run_cli("decide", "external_send", "--subject", "당회록 → 교회 드라이브")
        self.assertEqual(d["decision"], "ask")
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "당회록 → 교회 드라이브",
                                "--answer-file", self.answer("교회 안에서만이면 돼"), "--meaning", "conditional")
        self.assertEqual((rc, r["reason"]), (2, "condition"))
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "당회록 → 교회 드라이브",
                                "--answer-file", self.answer("교회 안에서만이면 돼"), "--meaning", "conditional",
                                "--condition", "교회 내부 공유 드라이브 한정")
        self.assertEqual(rc, 0, r)
        rc, d, _ = self.run_cli("decide", "external_send", "--subject", "당회록 → 교회 드라이브")
        self.assertEqual(d["decision"], "check")                     # codex R2: 조건 확인 전에는 do 아님
        # master#6528f666(D16): 조건의 뜻은 도구가 해석하지 않는다 — 원문을 마스터에게 돌려준다
        self.assertEqual(d["condition"], "교회 내부 공유 드라이브 한정")
        rc, d, _ = self.run_cli("decide", "external_send", "--subject", "당회록 → 교회 드라이브", "--condition-met", "yes")
        self.assertEqual(d["decision"], "do")
        rc, d, _ = self.run_cli("decide", "external_send", "--subject", "당회록 → 교회 드라이브", "--condition-met", "no")
        self.assertEqual(d["decision"], "each")

    def test_remember_ledger_first(self):
        def boom(_e):
            raise OSError("ledger")
        self.m._ledger = boom
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "x", "--answer-file", self.answer("네"),
                                "--meaning", "allow")
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(os.path.join(self.state, "decisions.json")))

    def test_decisions_cap(self):
        # codex R1: 상한에서 옛 결정을 지우면 재질문이 생긴다 → 지우지 않고 새 기록만 거절
        self.m.MAX_DECISIONS = 3
        rcs = []
        for i in range(5):
            rc, r, _ = self.run_cli("remember", "external_send", "--subject", "s%d" % i, "--answer-file", self.answer("네"),
                                    "--meaning", "allow")
            rcs.append(rc)
        self.assertEqual(rcs, [0, 0, 0, 7, 7])
        self.assertEqual(len(self.dec()), 3)
        rc, d, _ = self.run_cli("decide", "external_send", "--subject", "s0")
        self.assertEqual(d["decision"], "do")              # 처음 기록은 그대로 — 다시 묻지 않는다

    def test_signup_beats_standing_allow(self):
        # codex R1 blocking: 상시 허락이 있어도 「처음 쓰는 서비스(--in-use no)」 = 가입 = 건마다
        self.run_cli("decide", "login", "--subject", "new.example")
        self.run_cli("remember", "login", "--subject", "new.example", "--answer-file", self.answer("응"), "--meaning", "allow")
        rc, d, _ = self.run_cli("decide", "login", "--subject", "new.example", "--in-use", "no")
        self.assertEqual(d["decision"], "each")

    def test_personal_strings_masked_and_keys_hashed(self):
        # codex R1: 대상·한 일·조건 문자열에 이메일·긴 번호가 섞여도 출력·기록에 원문이 남지 않는다
        subj = "보고서 → %s" % EMAIL
        rc, d, _ = self.run_cli("decide", "external_send", "--subject", subj)
        self.assertNotIn(EMAIL, json.dumps(d, ensure_ascii=False))
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", subj, "--answer-file", self.answer("응"),
                                "--meaning", "conditional", "--condition", "010-1234-5678 로만")
        blob = json.dumps(r, ensure_ascii=False)
        for root, _d, files in os.walk(self.state):
            for f in files:
                blob += "\n".join(lines(os.path.join(root, f)))
        rc, d, _ = self.run_cli("decide", "external_send", "--subject", subj, "--what", "%s 에게 보냄" % EMAIL,
                                "--condition-met", "yes")
        blob += json.dumps(d, ensure_ascii=False)
        self.assertEqual(d["decision"], "do")
        self.assertNotIn(EMAIL, blob)                               # 대상 원문은 출력·파일 어디에도 없다(키 = 해시)
        out_only = json.dumps(r, ensure_ascii=False) + json.dumps(d, ensure_ascii=False)
        self.assertNotIn("010-1234-5678", out_only)                 # 기록 말·do 보고는 가림(조건 원문은 check 때만 마스터에게)
        self.assertNotIn("010-1234-5678", "\n".join(lines(os.path.join(self.state, "ledger.jsonl"))))   # 원장엔 해시만

    def test_new_type_key_hashed(self):
        cat = "send-to-%s" % EMAIL
        rc, r, _ = self.run_cli("remember", cat, "--subject", "x", "--answer-file", self.answer("응"), "--meaning", "allow")
        self.assertEqual(rc, 0, r)
        self.assertNotIn(EMAIL, json.dumps(r, ensure_ascii=False) + json.dumps(self.dec(), ensure_ascii=False))
        rc, d, _ = self.run_cli("decide", cat, "--subject", "x")
        self.assertEqual(d["decision"], "do")

    def test_legacy_keys_not_followed(self):
        # master#7d1b6e77(codex R10 · 설계 B): 옛 판 키 호환 삭제 — decide/remember 는 이 티켓에서 처음 생겨 발행·설치 0(옛 기록 =
        #   개발 시험 기록뿐). 옛 판 꼴(92c47060 `유형:정규화 원문` · ad474d66 `유형 원문:대상 해시` · 앞 120자 해시) 기록은 따르지 않는다
        os.makedirs(self.state, exist_ok=True)
        h = lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()[:16]
        head = "보고서 " * 30
        self._put({"external_send:보고서 → 팀 드라이브": {"meaning": "allow", "at": "t"},
                   "settings_change:크롬 끄기": {"meaning": "deny", "at": "t"},
                   "custom_export:" + h("a"): {"meaning": "deny", "at": "t"},
                   "external_send:" + h(self.m._norm(head + "옛 기록")[:120]): {"meaning": "deny", "at": "t"}})
        self.assertEqual(self.run_cli("decide", "external_send", "--subject", "보고서 → 팀 드라이브")[1]["decision"], "ask")
        self.assertEqual(self.run_cli("decide", "settings_change", "--subject", "크롬 끄기")[1]["decision"],
                         self.m.judge("settings_change", "크롬 끄기")[0])           # 표의 기본 결정 그대로
        self.assertEqual(self.run_cli("decide", "custom_export", "--subject", "a")[1]["decision"], "ask")
        self.assertEqual(self.run_cli("decide", "external_send", "--subject", head + "옛 기록")[1]["decision"], "ask")
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "보고서 → 팀 드라이브",
                                "--answer-file", self.answer("응"), "--meaning", "deny")
        self.assertEqual(rc, 0, r)                                               # 옛 꼴 기록은 재기록을 막지도 않는다
        self.assertEqual(self.run_cli("decide", "external_send", "--subject", "보고서 → 팀 드라이브")[1]["decision"], "never")

    def test_free_text_condition_recorded_and_returned_verbatim(self):
        # master#6528f666(D16): 조건 문법(범위 낱말·받는 사람 목록)을 강제하지 않는다 — 사용자 말 그대로 기록하고 check 때
        #   원문을 마스터에게 · 원장엔 원문 0(답 해시만)
        cond = "%s · %s · %s 안에서만, 다음 달까지" % (NAME, ORG, PROFILE)
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "보고서", "--answer-file", self.answer("응"),
                                "--meaning", "conditional", "--condition", cond)
        self.assertEqual(rc, 0, r)
        rc, d, _ = self.run_cli("decide", "external_send", "--subject", "보고서")
        self.assertEqual((d["decision"], d["condition"]), ("check", cond))
        self.assertTrue(self.dec()[self.m.decision_key("external_send", "보고서")]["full"])
        led = "\n".join(lines(os.path.join(self.state, "ledger.jsonl")))
        for x in (NAME, ORG, PROFILE):
            self.assertNotIn(x, led)

    def test_condition_too_long_rejected_not_truncated(self):
        # codex R3 major: 조건을 잘라 저장하면 끝의 제한이 사라진다 — 한도를 넘으면 기록하지 않는다
        cond = "가" * self.m.MAX_CONDITION + " 외부 수신자 금지"
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "s", "--answer-file", self.answer("응"),
                                "--meaning", "conditional", "--condition", cond)
        self.assertEqual((rc, r["reason"]), (2, "condition_too_long"))
        self.assertEqual(self.dec(), {})
        cond = "가" * 395 + " 외부 수신자 금지"
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "s", "--answer-file", self.answer("응"),
                                "--meaning", "conditional", "--condition", cond)
        self.assertEqual(rc, 0, r)
        self.assertEqual(list(self.dec().values())[0]["condition"], cond)       # 끝까지 그대로

    def test_legacy_truncated_condition_never_do(self):
        # codex R3 major: 옛 판이 300자에서 잘라 둔 조건으로는 조건 확인이 있어도 do 를 내지 않는다
        os.makedirs(self.state, exist_ok=True)
        with open(os.path.join(self.state, "decisions.json"), "w") as f:
            json.dump({"items": {self.m.decision_key("external_send", "s"):
                                 {"meaning": "conditional", "condition": "가" * 300, "at": "t"}}}, f)
        for cm in ("yes", "unknown", "no"):
            rc, d, _ = self.run_cli("decide", "external_send", "--subject", "s", "--condition-met", cm)
            self.assertEqual((d["decision"], d.get("supplement")), ("each", True), cm)
        # codex R5: 이 기록만은 다시 받은 조건으로 --user-changed 없이 덮는다(재질문 고리 차단) — 그 뒤는 보통 조건부
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "s", "--answer-file", self.answer("응 팀 안에서만"),
                                "--meaning", "conditional", "--condition", "팀 안에서만")
        self.assertEqual(rc, 0, r)
        rc, d, _ = self.run_cli("decide", "external_send", "--subject", "s")
        self.assertEqual((d["decision"], d["condition"], d.get("supplement")), ("check", "팀 안에서만", None))
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "s", "--answer-file", self.answer("응"),
                                "--meaning", "allow")
        self.assertEqual((rc, r["reason"]), (7, "already_decided"))       # 다시 적은 뒤에는 보통 항목처럼 재기록 막힘
        os.makedirs(self.state, exist_ok=True)
        with open(os.path.join(self.state, "decisions.json"), "w") as f:
            json.dump({"items": {self.m.decision_key("external_send", "t"):
                                 {"meaning": "conditional", "condition": "가" * 299, "at": "t"}}}, f)
        self.assertEqual(self.run_cli("decide", "external_send", "--subject", "t")[1]["decision"], "check")   # 300자 미만 = 안 잘림

    def _put(self, items):
        os.makedirs(self.state, exist_ok=True)
        with open(os.path.join(self.state, "decisions.json"), "w") as f:
            json.dump({"items": items}, f)

    def test_supplement_only_replaces_cut_records(self):
        # codex R6·R7: --user-changed 없는 보완 = 조건부로만 · 잘린 기록 자리에서 바꾼다
        cur = self.m.decision_key("external_send", "s")
        cut = {"meaning": "conditional", "condition": "가" * 300, "at": "t"}
        base = ("remember", "external_send", "--subject", "s", "--answer-file", self.answer("응"))
        self._put({cur: cut})
        rc, r, _ = self.run_cli(*(base + ("--meaning", "allow")))
        self.assertEqual((rc, r["reason"]), (7, "supplement_meaning"))           # 허락으로 덮기 = 사용자 변경 경로만
        self.assertEqual(self.dec(), {cur: cut})
        rc, r, _ = self.run_cli(*(base + ("--meaning", "conditional", "--condition", "모임 안")))
        self.assertEqual(rc, 0, r)
        self.assertEqual((list(self.dec()), self.dec()[cur]["condition"]), ([cur], "모임 안"))
        self.assertEqual(self.run_cli("decide", "external_send", "--subject", "s")[1]["decision"], "check")

    def test_supplement_at_cap_replaces_in_place(self):
        # codex R6: 한도에서도 잘린 기록 보완은 그 자리 교체라 개수가 늘지 않으므로 된다 — 재질문 고리 0
        self.m.MAX_DECISIONS = 3
        self._put({self.m.decision_key("external_send", "s"): {"meaning": "conditional", "condition": "가" * 300, "at": "t"},
                   "x:1": {"meaning": "allow", "at": "t"}, "x:2": {"meaning": "allow", "at": "t"}})
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "s", "--answer-file", self.answer("응"),
                                "--meaning", "conditional", "--condition", "팀 안")
        self.assertEqual(rc, 0, r)
        self.assertEqual(len(self.dec()), 3)
        self.assertEqual(self.run_cli("decide", "external_send", "--subject", "s")[1]["decision"], "check")
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "new", "--answer-file", self.answer("응"),
                                "--meaning", "allow")
        self.assertEqual((rc, r["reason"]), (7, "decisions_full"))              # 새 항목은 여전히 한도 거절

    def test_long_subject_not_cut(self):
        # codex R8 뒤 자가 발견: 대상을 120자에서 자르면 뒤가 다른 두 대상이 한 결정을 나눠 갖고 120자 뒤 「네이버」를 못 본다
        head = "보고서 " * 30                                          # 정규화 뒤 120자 넘음
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", head + "팀 드라이브", "--answer-file",
                                self.answer("응"), "--meaning", "allow")
        self.assertEqual(rc, 0, r)
        self.assertEqual(self.run_cli("decide", "external_send", "--subject", head + "팀 드라이브")[1]["decision"], "do")
        self.assertEqual(self.run_cli("decide", "external_send", "--subject", head + "외부 메일")[1]["decision"], "ask")
        rc, d, _ = self.run_cli("decide", "login", "--subject", head + "naver", "--in-use", "yes")
        self.assertEqual(d["decision"], "each")                                  # 약관 서비스는 길이와 무관

    def test_record_states_exhaustive(self):
        # 기록 상태 전수 — 한 키 × {없음·허락·안 함·조건·잘린 조건} × 뜻 3 × 사용자 변경 여부 = 30 꼴을 구현과 독립인 판정식과 대조:
        #   조회 = 그 기록 · 보완 = 잘린 조건 + 조건부로만 그 자리 교체 · 사용자 변경·없음 = 씀 · 그 밖 = 무변경 거절
        cur = self.m.decision_key("external_send", "s")
        states = {None: None, "allow": {"meaning": "allow", "at": "t"}, "deny": {"meaning": "deny", "at": "t"},
                  "cond": {"meaning": "conditional", "condition": "팀 안", "full": True, "at": "t"},
                  "cut": {"meaning": "conditional", "condition": "가" * 300, "at": "t"}}
        want_decide = {"deny": "never", "cut": "each", "cond": "check", "allow": "do"}
        n = 0
        for st in states:
            for meaning in ("allow", "deny", "conditional"):
                for uc in (False, True):
                    n += 1
                    items = {cur: states[st]} if st else {}
                    self._put(items)
                    if st:
                        got = self.run_cli("decide", "external_send", "--subject", "s")[1]["decision"]
                        self.assertEqual(got, want_decide[st], st)
                    argv = ["remember", "external_send", "--subject", "s", "--answer-file", self.answer("응"),
                            "--meaning", meaning] + (["--condition", "새 조건"] if meaning == "conditional" else [])
                    rc, r, _ = self.run_cli(*(argv + (["--user-changed"] if uc else [])))
                    after, tag = self.dec(), (st, meaning, uc)
                    if not st or uc or (st == "cut" and meaning == "conditional"):
                        self.assertEqual(rc, 0, (tag, r))
                        self.assertEqual((list(after), after[cur]["meaning"]), ([cur], meaning), tag)
                    elif st == "cut":
                        self.assertEqual((rc, r["reason"], after), (7, "supplement_meaning", items), tag)
                    else:
                        self.assertEqual((rc, r["reason"], after), (7, "already_decided", items), tag)
        self.assertEqual(n, 30)

    def test_key_space_boundary_120(self):
        # codex R9: 정규화 120자 대상의 지금 키 = 그 뒤에 글을 붙인 더 긴 대상의 옛 판(앞 120자) 키 — 지금 판 기록이 옛 키
        #   별칭으로 남에게 옮거나(허락 전이) 남의 「사용자 변경」이 지우면 안 된다. 길이 119·120·121 × 아는 유형·새 유형(이름
        #   120·121자) × 기록 차례 둘 · 새 기록만 있는 상태 전수
        new120, new121 = "t" * 120, "t" * 121
        for cat in ("external_send", "login", new120, new121):
            for la in (119, 120, 121):
                a = ("가" * la)
                b = a + " 추가"
                for first, second in ((a, b), (b, a)):
                    self._put({})
                    extra = ("--in-use", "yes") if cat == "login" else ()
                    rc, r, _ = self.run_cli("remember", cat, "--subject", first, "--answer-file", self.answer("안 돼"),
                                            "--meaning", "deny")
                    self.assertEqual(rc, 0, r)
                    tag = (cat[:14], la, first == a)
                    got = self.run_cli("decide", cat, "--subject", second, *extra)[1]["decision"]
                    self.assertNotEqual(got, "never", tag)                       # 첫 대상의 거절이 둘째로 옮지 않는다
                    for uc in ((), ("--user-changed",)):                             # 처음 기록 · 사용자 변경 둘 다
                        rc, r, _ = self.run_cli("remember", cat, "--subject", second, "--answer-file", self.answer("응"),
                                                "--meaning", "allow", *uc)
                        self.assertEqual(rc, 0, (tag, uc, r))                     # 둘째 대상엔 제 기록이 없다(already_decided 0)
                    self.assertEqual(self.run_cli("decide", cat, "--subject", first, *extra)[1]["decision"], "never", tag)
                    self.assertEqual(self.run_cli("decide", cat, "--subject", second, *extra)[1]["decision"], "do", tag)
                    self.assertEqual(len(self.dec()), 2, tag)                     # 둘 다 남는다

    def test_two_subjects_non_interference(self):
        # master#7d1b6e77(codex R10 반례 포함): 두 대상 A(정규화 120·121자) · B = A + 「 추가」 — A 의 키 자리에 무엇이 있든(없음·허락·
        #   안 함·조건·잘린 조건 = R10 의 옛 잘린 기록 자리) 한 대상의 기록 쓰기(뜻 3 × 사용자 변경 여부)는 다른 대상의 판정을 바꾸지
        #   않는다 · 차례 둘(A→B · B→A) · 유형 = 아는 유형 2(login 은 사용 근거 있음 — R10 반례의 do 경로). 판정식 = 「쓰기 전후 상대
        #   판정 같음」(구현과 독립) · 키가 대상 하나에 하나라 길이 경계(120)는 반례 자리 하나로 충분(옛 판 앞 120자 키는 없앴다)
        cut = {"meaning": "conditional", "condition": "가" * 300, "at": "t"}
        states = [None, {"meaning": "allow", "at": "t"}, {"meaning": "deny", "at": "t"},
                  {"meaning": "conditional", "condition": "팀 안", "full": True, "at": "t"}, cut]
        ops = [(m, uc) for m in ("allow", "deny", "conditional") for uc in (False, True)]
        n = 0
        for cat in ("external_send", "login"):
            extra = ("--in-use", "yes") if cat == "login" else ()
            for la in (120,):
                a = "gmail " + "가" * (la - 6)
                b = a + " 추가"
                dec = lambda x: self.run_cli("decide", cat, "--subject", x, *extra)[1]["decision"]
                for st in states:
                    for (m1, u1) in ops:
                        for (m2, u2) in (("allow", False), ("allow", True), ("conditional", False)):
                            for x, y in ((a, b), (b, a)):
                                n += 1
                                self._put({self.m.decision_key(cat, a): st} if st else {})
                                for subj, m, uc in ((x, m1, u1), (y, m2, u2)):
                                    other = b if subj == a else a
                                    before = dec(other)
                                    self.run_cli("remember", cat, "--subject", subj, "--answer-file", self.answer("응"),
                                                 "--meaning", m, *(["--condition", "새"] if m == "conditional" else []),
                                                 *(["--user-changed"] if uc else []))
                                    self.assertEqual(dec(other), before, (cat[:13], la, st and st["meaning"], subj == a, m, uc))
        self.assertEqual(n, 2 * 1 * 5 * 6 * 3 * 2)

    def test_domain_matches_only_official_domains(self):
        # codex R3·R4: 도메인 대상은 이름 닮음(word.invalid · gmail.invalid · word.example.invalid)이 아니라 정식 도메인 목록으로만
        os.makedirs(os.path.join(self.apps, "Microsoft Word.app"))
        for subj, want in (("word.example.invalid", "ask"), ("word.invalid", "ask"), ("gmail.invalid", "ask"),
                           ("gmail.example.invalid", "ask"), ("evilgmail.com", "ask"), ("mail.google.com", "do"), ("gmail.com", "do"),
                           ("login.microsoftonline.com", "do")):
            rc, d, _ = self.run_cli("decide", "login", "--subject", subj)
            self.assertEqual(d["decision"], want, subj)

    def test_url_target_is_real_hostname(self):
        # codex R5: URL 의 사용자정보·경로·쿼리에 정식 도메인이 있어도 실제 접속 대상이 아니다 · 대상이 둘 이상이면 모름
        at = "mail.google.com" + "@" + "unrelated.invalid"          # 사용자정보 꼴(이메일 모양 리터럴은 팩 발행 스캐너가 막는다)
        for subj, want in (("https://" + at, "ask"), ("https://mail.google.com/mail/u/0", "do"),
                           ("https://unrelated.invalid/?next=mail.google.com", "ask"), ("https://10.0.0.1/mail.google.com", "ask"),
                           (at, "ask"), ("gmail.com 과 unrelated.invalid", "ask"),
                           ("https://[::1/ gmail", "ask"),
                           # codex R6: 역슬래시(브라우저는 경로로 읽음)·잘못된 포트 = 모호 · 문장 속 괄호는 URL 이 아니다
                           ("https://unrelated.invalid\\" + "@" + "mail.google.com/", "ask"), ("https://mail.google.com:bad/", "ask"),
                           ("https://mail.google.com:999999/", "ask"), ("Gmail (https://mail.google.com)", "do"),
                           ("https://mail.google.com:443/mail.", "do"),
                           # codex R7: 호스트 자리의 비ASCII 는 브라우저가 다른 호스트로 정규화 — 앞부분만 잘라 대조하지 않는다
                           ("https://mail.google.comé/", "ask"), ("https://mail.google.com。invalid/", "ask"),
                           ("https://mail.google.com/mail에서", "do"),
                           # codex R8: 호스트의 제어 문자(NUL·SOH·DEL)·% 인코딩·끊긴 :// = 모름 · 끝점 호스트는 같은 호스트
                           ("https://unrelated.invalid\u0000.mail.google.com/", "ask"),
                           ("https://unrelated.invalid\u0001.mail.google.com/", "ask"),
                           ("https://unrelated.invalid\u007f.mail.google.com/", "ask"),
                           ("https://mail%2egoogle.com/", "ask"), ("https:// mail.google.com/", "ask"),
                           ("https://mail.google.com./", "do"),
                           # codex R9: 퓨니코드 라벨(잘못된 A-label 은 브라우저가 거절) = 모름 · 낱말 경계 밖 공백류는 URL 안 → 모름
                           ("https://xn--a.mail.google.com./", "ask"), ("https://xn--a.mail.google.com/", "ask"),
                           ("https://mail.google.com\u000b/", "ask"), ("https://mail.google.com\u3000/", "ask"),
                           ("https://mail.google.com\u00a0로그인", "ask"),
                           ("https://mail.google.com 로그인", "do")):                # ASCII 공백 = 글의 낱말 경계(주소 끝)
            rc, d, _ = self.run_cli("decide", "login", "--subject", subj)
            self.assertEqual(d["decision"], want, subj)

    def test_word_app_does_not_match_wordpress(self):
        os.makedirs(os.path.join(self.apps, "Microsoft Word.app"))
        rc, d, _ = self.run_cli("decide", "login", "--subject", "wordpress.com")
        self.assertEqual(d["decision"], "ask")                       # codex R2: Word 설치 ≠ WordPress 사용
        rc, d, _ = self.run_cli("decide", "login", "--subject", "wordpress 로그인")
        self.assertEqual(d["decision"], "ask")                       # 도메인 없는 글도 낱말 단위(부분 문자열 아님)

    def test_decide_writes_nothing(self):
        before = os.path.exists(self.state) and sorted(os.listdir(self.state))
        self.run_cli("decide", "login", "--subject", "gmail")
        self.run_cli("decide", "external_send", "--subject", "y")
        after = os.path.exists(self.state) and sorted(os.listdir(self.state))
        self.assertEqual(before, after)

    def test_usage_app_name_with_extra_words(self):
        os.makedirs(os.path.join(self.apps, "KakaoTalk.app"))
        rc, d, _ = self.run_cli("decide", "login", "--subject", "카카오톡 로그인")
        self.assertEqual(d["decision"], "do")                         # agy R1 minor: 덧붙은 말이 있어도 설치 앱으로 본다

    def test_usage_installed_app_counts_as_in_use(self):
        os.makedirs(os.path.join(self.apps, "KakaoTalk.app"))
        u = self.m.usage_pattern("darwin")
        self.assertIn("kakaotalk", u["apps"])
        self.assertEqual(u["services"], ["Gmail"])          # 커넥터 이름만(계정·내용 0)
        rc, d, _ = self.run_cli("decide", "login", "--subject", "카카오톡")
        self.assertEqual(d["decision"], "do")
        self.assertIn("설치된 앱(카카오톡", d["report"])


if __name__ == "__main__":
    unittest.main()
