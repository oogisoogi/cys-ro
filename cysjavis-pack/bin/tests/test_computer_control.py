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
        # cu-1111-precedent: 연결 파일 없음·끊김 = 마스터가 chrome-enable 로 만든다 → 바로(제가 할 것)
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


# ───────────────────────── 크롬 켜기·끄기 = 마스터 직접 (cu-1111-precedent) ─────────────────────────
class TestChromeEnable(Base):
    """실제 크롬·좌석 무접촉: 외부 명령은 전부 CYS_CC_FAKE_ACT 기록 파일로만 간다(더블)."""
    def setUp(self):
        super().setUp()
        self.act_log = os.path.join(self.tmp, "acts.jsonl")
        os.environ["CYS_CC_FAKE_ACT"] = self.act_log
        self.manifest = os.path.join(self.ud, "NativeMessagingHosts", "com.anthropic.claude_code_browser_extension.json")
        self.host = os.path.join(self.ccd, "chrome", "chrome-native-host")
        self.set_probes(ae={"com.google.Chrome": 0}, chrome_running=False, idle=60, windows=3, act={})

    def acts(self):
        if not os.path.exists(self.act_log):
            return []
        return [json.loads(x) for x in lines(self.act_log)]

    def kinds(self):
        return [a["kind"] for a in self.acts()]

    def cfg(self):
        return jload(os.path.join(self.ccd, ".claude.json"))

    def nmh_touch(self):
        os.makedirs(os.path.dirname(self.host), exist_ok=True)
        open(self.host, "w").close()
        return {"touch": {self.manifest: json.dumps({"name": "com.anthropic.claude_code_browser_extension",
                                                     "path": self.host})}}

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
        self.assertEqual(os.stat(p).st_mode & 0o777, 0o600)   # 권한 유지
        self.assertIn("default_on", d["done"])
        self.assertNotIn("quit", self.kinds())                # 연결 파일이 이미 있으면 크롬을 건드리지 않는다
        self.assertIn("되돌릴 수 있습니다", d["say"])

    def test_enable_already_on_is_noop(self):
        self.make_chrome()
        p = os.path.join(self.ccd, ".claude.json")
        raw = rb(p)
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual((rc, d["done"]), (0, []))
        self.assertEqual(rb(p), raw)
        self.assertEqual(self.kinds(), [])                    # 할 일 없음 = 외부 명령 0(좌석 재시작도 없음)

    def test_enable_schedules_seat_restart_detached_after_turn(self):
        self.make_chrome()
        self.write_cfg(chrome_default=None)
        rc, d, _ = self.run_cli("chrome-enable")
        sr = [a for a in self.acts() if a["kind"] == "seat_restart"]
        self.assertEqual(len(sr), 1)
        self.assertTrue(sr[0]["detach"])
        cmd = " ".join(sr[0]["argv"])
        self.assertIn("rotate --skip-depts", cmd)
        self.assertIn("sleep %d" % self.m.SEAT_RESTART_DELAY_SEC, cmd)   # 이 턴이 끝난 뒤
        self.assertIn("seat_restart", d["done"])
        rc, d, _ = self.run_cli("chrome-enable", "--seat-restart", "no")
        self.assertEqual(len([a for a in self.acts() if a["kind"] == "seat_restart"]), 1)

    def test_nmh_created_by_headless_claude_in_seat_config(self):
        self.make_chrome(nmh=False)
        self.set_probes(act={"nmh": self.nmh_touch()})
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual(rc, 0, d)
        nm = [a for a in self.acts() if a["kind"] == "nmh"][0]
        self.assertEqual(nm["argv"][1:3], ["-p", "--chrome"])
        self.assertTrue(nm["cwd"].startswith(self.state))     # 마스터 폴더가 아닌 상태 폴더에서
        self.assertIn("nmh", d["done"])
        self.assertNotIn("quit", self.kinds())                # 크롬이 꺼져 있었으면 다시 켤 필요 없음

    def test_restart_only_new_nmh_and_running_graceful(self):
        self.make_chrome(nmh=False)
        self.set_probes(chrome_running=[True, False, True], act={"nmh": self.nmh_touch()})
        rc, d, _ = self.run_cli("chrome-enable")
        k = self.kinds()
        self.assertLess(k.index("notify"), k.index("quit"))   # 화면 알림 1줄이 먼저
        self.assertLess(k.index("quit"), k.index("open"))
        quit = [a for a in self.acts() if a["kind"] == "quit"][0]["argv"]
        self.assertIn('tell application "Google Chrome" to quit', " ".join(quit))
        blob = json.dumps(self.acts())
        for bad in ("-9", "KILL", "pkill", "killall", "taskkill", "Stop-Process", "Force"):
            self.assertNotIn(bad, blob)
        op = [a for a in self.acts() if a["kind"] == "open"][0]["argv"]
        self.assertIn("--restore-last-session", op)
        self.assertIn("chrome_restart", d["done"])
        self.assertIn("창 3개 그대로", d["say"])

    def test_tab_count_compared_and_loss_reported(self):
        self.make_chrome(nmh=False)
        self.set_probes(chrome_running=[True, False, True], windows=[[2, 9], [2, 7]], act={"nmh": self.nmh_touch()})
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertIn("탭이 9개 → 7개", d["say"])
        self.assertIn("최근에 닫은 탭", d["say"])
        rows = [json.loads(x) for x in lines(os.path.join(self.state, "ledger.jsonl"))]
        ro = [r for r in rows if r.get("event") == "chrome_reopened"][0]
        self.assertEqual((ro["before"], ro["after"]), ([2, 9], [2, 7]))

    def test_mac_count_script_parsed(self):
        self.make_chrome(nmh=False)
        self.set_probes(chrome_running=[True, False, True],
                        act={"nmh": self.nmh_touch(), "windows": [{"out": "2 9\n"}, {"out": "2 9\n"}]})
        p = dict(self.probes)
        p.pop("windows")
        os.environ["CYS_CC_FAKE_PROBES"] = json.dumps(p)
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertIn("탭 9개 그대로", d["say"])

    def test_restart_without_automation_permission_terms_one_pid(self):
        self.make_chrome(nmh=False)
        self.set_probes(ae={"com.google.Chrome": -1744}, chrome_running=[True, False, True],
                        act={"nmh": self.nmh_touch(), "chrome_pid": {"out": "4242\n"}})
        rc, d, _ = self.run_cli("chrome-enable")
        quit = [a for a in self.acts() if a["kind"] == "quit"][0]["argv"]
        self.assertEqual(quit, ["/bin/kill", "-TERM", "4242"])   # 이름 일괄 종료가 아니라 본 프로세스 하나 · 정상 종료 신호
        self.assertNotIn("windows", self.kinds())              # 허락 없으면 osascript 로 세지 않는다(허락 창 0)

    def test_idle_gate_defers_without_touching_chrome(self):
        self.make_chrome(nmh=False)
        self.set_probes(chrome_running=True, idle=[3, 3, 3], act={"nmh": self.nmh_touch()})
        rc, d, _ = self.run_cli("chrome-enable", "--wait", "4")
        self.assertEqual(rc, 0)
        for k in ("notify", "quit", "open", "seat_restart"):
            self.assertNotIn(k, self.kinds())
        self.assertEqual(d["pending"], ["chrome_restart"])

    def test_wait_is_capped(self):
        self.make_chrome(nmh=False)
        self.set_probes(chrome_running=True, idle=[0], act={"nmh": self.nmh_touch()})
        rc, d, _ = self.run_cli("chrome-enable", "--wait", "99999")
        self.assertEqual(d["pending"], ["chrome_restart"])
        self.assertLessEqual(self.m._seq_idle, 540 // 2 + 1)    # 4군① — 기다림 상한 540초(2초 간격)

    def test_not_quit_is_left_alone(self):
        self.make_chrome(nmh=False)
        self.set_probes(chrome_running=True, act={"nmh": self.nmh_touch()})
        rc, d, _ = self.run_cli("chrome-enable")
        self.assertEqual(self.kinds().count("quit"), 1)      # 한 번 정상 종료 요청 · 다시 세게 안 함
        self.assertNotIn("open", self.kinds())
        self.assertIn("강제로 끄지 않습니다", d["say"])

    def test_win_quit_is_close_main_window(self):
        os.environ["CYS_CC_PLATFORM"] = "win"
        self.set_probes(chrome={"app": True, "profiles": 1, "with_ext": 1, "ext_enabled": True,
                                "nmh": False, "default_on": False, "playwright_ext": False},
                        chrome_running=[True, False, True])
        self.m.platform = lambda: "win"
        self.m._nmh_ok = lambda plat, ud, _s=[False, True]: _s.pop(0) if len(_s) > 1 else _s[0]
        rc, d, _ = self.run_cli("chrome-enable")
        quit = " ".join([a for a in self.acts() if a["kind"] == "quit"][0]["argv"])
        self.assertIn("CloseMainWindow", quit)
        op = [a for a in self.acts() if a["kind"] == "open"][0]
        self.assertTrue(op["detach"])

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

    def test_disable_restores_prior_absent_and_removes_our_nmh(self):
        self.make_chrome(nmh=False)
        self.write_cfg(chrome_default=None)
        self.set_probes(act={"nmh": self.nmh_touch()})
        self.run_cli("chrome-enable")
        self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], True)
        n0 = len(self.acts())
        rc, d, _ = self.run_cli("chrome-disable")
        self.assertEqual(rc, 0, d)
        self.assertNotIn("claudeInChromeDefaultEnabled", self.cfg())   # 원래 없던 키 = 없앤다
        rm = [a for a in self.acts() if a["kind"] == "nmh_remove"]
        self.assertEqual(rm[0]["argv"][-1], self.manifest)
        self.assertNotIn("seat_restart", [a["kind"] for a in self.acts()[n0:]])   # 끄기는 기본으로 좌석을 재시작하지 않는다

    def test_disable_keeps_nmh_rewritten_by_others(self):
        self.make_chrome(nmh=False)
        self.write_cfg(chrome_default=False)
        self.set_probes(act={"nmh": self.nmh_touch()})
        self.run_cli("chrome-enable")
        with open(self.manifest, "w") as f:
            f.write('{"path": "/elsewhere"}')
        rc, d, _ = self.run_cli("chrome-disable")
        self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], False)
        self.assertNotIn("nmh_remove", self.kinds())
        self.assertIn("그대로 두었습니다", d["say"])

    def test_disable_without_record_turns_off(self):
        self.make_chrome()
        rc, d, _ = self.run_cli("chrome-disable")
        self.assertIs(self.cfg()["claudeInChromeDefaultEnabled"], False)
        self.assertNotIn("nmh_remove", self.kinds())

    def test_act_stdin_devnull_and_cwd(self):
        del os.environ["CYS_CC_FAKE_ACT"]
        seen = {}

        def fake_run(argv, **kw):
            seen.update(kw)
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        orig = self.m.subprocess.run
        self.m.subprocess.run = fake_run
        try:
            self.m._act("x", ["true"], cwd=self.tmp)
        finally:
            self.m.subprocess.run = orig
        self.assertIs(seen.get("stdin"), subprocess.DEVNULL)
        self.assertEqual(seen.get("cwd"), self.tmp)

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
        self.assertEqual(d["decision"], "do")
        self.assertIn("조건: 교회 내부 공유 드라이브 한정", d["report"])

    def test_remember_ledger_first(self):
        def boom(_e):
            raise OSError("ledger")
        self.m._ledger = boom
        rc, r, _ = self.run_cli("remember", "external_send", "--subject", "x", "--answer-file", self.answer("네"),
                                "--meaning", "allow")
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(os.path.join(self.state, "decisions.json")))

    def test_decisions_cap(self):
        self.m.MAX_DECISIONS = 3
        for i in range(5):
            self.run_cli("remember", "external_send", "--subject", "s%d" % i, "--answer-file", self.answer("네"),
                         "--meaning", "allow")
        self.assertLessEqual(len(self.dec()), 3)
        self.assertIn("external_send:s4", self.dec())     # 오래된 것부터 정리

    def test_decide_writes_nothing(self):
        before = os.path.exists(self.state) and sorted(os.listdir(self.state))
        self.run_cli("decide", "login", "--subject", "gmail")
        self.run_cli("decide", "external_send", "--subject", "y")
        after = os.path.exists(self.state) and sorted(os.listdir(self.state))
        self.assertEqual(before, after)

    def test_usage_installed_app_counts_as_in_use(self):
        os.makedirs(os.path.join(self.apps, "KakaoTalk.app"))
        u = self.m.usage_pattern("darwin")
        self.assertIn("kakaotalk", u["apps"])
        self.assertEqual(u["services"], ["Gmail"])          # 커넥터 이름만(계정·내용 0)
        rc, d, _ = self.run_cli("decide", "login", "--subject", "카카오톡")
        self.assertEqual(d["decision"], "do")
        self.assertIn("설치된 앱(카카오톡", d["report"])
