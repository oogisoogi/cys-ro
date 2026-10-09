#!/usr/bin/env python3
"""test_hook_fail_log — ★D9-b(1.1.8): 훅 안쪽 실패(rc≠0)를 `<상태 dir>/hook-errors.log` 에 한 줄로 남긴다.

윈 실측(2026-10-05 보고 D9·D10): 「요지 조립기 실패(rc=127)」가 화면 고지로만 남고 파일 기록이 없어,
rc 127 이 「명령 없음」인지 「실행 전 기본값(해석기 미해소·조립기 부재)」인지 사후 판정할 수 없었다.
계약: ①한 줄(시각·훅·역할·surface·rc·사유·해석기·cys/cat 보임·PATH 앞부분) ②stdout 무출력 · 종료 코드 불변
③PATH 가 깨진 순간(cat·date 없음 = D10)에도 기록 ④상태 dir 을 못 써도 무해 ⑤session-start 폴백이 사유를 갈라 기록
⑥형제 주입 훅 5곳이 같은 기록을 부른다.
⑦(T3) 같은 실패를 상담소 신호 한 줄로도 남긴다 · 끄면 0줄 · rc·stdout·호출 훅 CYS_PY 불변.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks")
SH = "/bin/sh"
# ★1.1.10 ④(TODO 팩 시험 teardown 2종째 · 10-06 hf-ss-* 잔존 9 ≈400MB): 물려받은 CYS_* 는 인터프리터 해소 2종만 남긴다
#   (test_dept_create_progress SANDBOX_KEEP_CYS 와 같은 화이트리스트 — 좌석 CYS_SOCKET 이 남으면 훅이 실 데몬에 역할을 묻는다).
KEEP_CYS = ("CYS_PY", "CYS_PY_ORIGIN")
# 목 cys = 「데몬 미응답」(rc 2) · 목 cysd = 기록만. session-start 는 cys claim-role·usage-register 를 부르는데 PATH 의 실 cys 는
#   소켓이 없으면 형제 cysd 를 띄운다(가짜 HOME 에 고아 데몬 + 그 데몬이 시험 팩에 hooks/ 를 깔아 「조립기 없음」 전제까지 깬다 — 1.1.10 실측).
STUB_CYS = '#!/bin/sh\necho "cys $*" >> "$(dirname "$0")/calls.log"\nexit 2\n'
STUB_CYSD = '#!/bin/sh\necho "cysd $*" >> "$(dirname "$0")/calls.log"\nexit 0\n'


def _base_env():
    return {k: v for k, v in os.environ.items() if not k.startswith("CYS_") or k in KEEP_CYS}


def _procs_holding(path):
    """path 아래 파일을 연 프로세스 pid(나 제외) — lsof 없음 = None(판정 불가)."""
    lsof = shutil.which("lsof")
    if os.name == "nt" or not lsof:
        return None
    r = subprocess.run([lsof, "-t", "+D", path], capture_output=True, text=True, timeout=60)
    return sorted({int(x) for x in r.stdout.split() if x.isdigit()} - {os.getpid()})


def _sh(script, env):
    return subprocess.run([SH, "-c", script], capture_output=True, text=True, env=env, timeout=30)


class T(unittest.TestCase):
    def setUp(self):
        self.st = tempfile.mkdtemp(prefix="hf-")
        self.env = dict(_base_env(), CYS_STATE_DIR=self.st, CYS_ROLE="cso", CYS_SURFACE_ID="44")
        self.log = os.path.join(self.st, "hook-errors.log")

    def tearDown(self):
        shutil.rmtree(self.st, ignore_errors=True)

    def lines(self):
        return open(self.log, encoding="utf-8").read().splitlines() if os.path.exists(self.log) else []

    def test_one_line_fields_and_rc_kept(self):
        r = _sh('. "%s/_lib.sh"; cys_hook_fail session-start 127 "core_inject:해석기 미해소"; exit 3' % HOOKS, self.env)
        self.assertEqual(r.returncode, 3, "기록이 훅 종료 코드를 바꿨다")
        self.assertEqual(r.stdout, "", "기록이 stdout 을 오염시켰다")
        ln = self.lines()
        self.assertEqual(len(ln), 1, ln)
        self.assertRegex(ln[0], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ session-start role=cso surface=44 rc=127 "
                                r"why=core_inject:해석기 미해소 py=\S+ cys=(yes|no) cat=yes path=")

    def test_broken_path_still_records(self):
        # D10 재현: PATH 에 아무것도 없다(cat·date·wc·mkdir 전부 command not found) — 셸 내장만으로 한 줄이 남아야 한다.
        r = _sh('. "%s/_lib.sh"; PATH=""; cys_hook_fail inject-background 127 x; exit 0' % HOOKS, self.env)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        ln = self.lines()
        self.assertEqual(len(ln), 1, ln)
        self.assertIn("시각불명(date 없음) inject-background", ln[0])
        self.assertIn("cys=no cat=no path=", ln[0])

    def test_long_path_is_capped(self):
        env = dict(self.env, PATH=os.environ["PATH"] + ":" + "/x" * 400)
        _sh('. "%s/_lib.sh"; cys_hook_fail h 1 y' % HOOKS, env)
        tail = self.lines()[0].split(" path=", 1)[1]
        self.assertLessEqual(len(tail.encode("utf-8")), 160 + len("…".encode("utf-8")))
        self.assertTrue(tail.endswith("…"))

    def test_unwritable_state_dir_is_harmless(self):
        env = dict(self.env, CYS_STATE_DIR="/dev/null/nope")
        r = _sh('. "%s/_lib.sh"; cys_hook_fail h 9 y; exit 0' % HOOKS, env)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_rotates_over_256k(self):
        with open(self.log, "w") as f:
            f.write("x" * 262145)
        _sh('. "%s/_lib.sh"; cys_hook_fail h 1 y' % HOOKS, self.env)
        self.assertTrue(os.path.exists(self.log + ".1"))
        self.assertEqual(len(self.lines()), 1)

    def test_session_start_fallback_records_reason(self):
        # 조립기 파일이 없는 사본(t6 F7f 와 같은 꼴) — 실행 전 기본값 rc 127 을 「조립기 파일 없음」으로 가른다.
        tmp = tempfile.mkdtemp(prefix="hf-ss-")
        try:
            hk = os.path.join(tmp, "hooks")
            shutil.copytree(HOOKS, hk)
            os.remove(os.path.join(hk, "core_inject.py"))
            pack = os.path.join(tmp, "pack")
            os.makedirs(os.path.join(pack, "directives"))
            os.makedirs(os.path.join(pack, "bin"))
            open(os.path.join(pack, "directives", "MASTER_DIRECTIVE.md"), "w").write("BODY\n")
            open(os.path.join(pack, "bin", "javis_bootstrap.py"), "w").write("# stub\n")
            home = os.path.join(tmp, "h")
            os.makedirs(home)
            tp = os.path.join(tmp, "t.jsonl")
            open(tp, "w").write("")
            stub = os.path.join(tmp, "stubbin")
            os.makedirs(stub)
            for name, body in (("cys", STUB_CYS), ("cysd", STUB_CYSD)):
                with open(os.path.join(stub, name), "w") as f:
                    f.write(body)
                os.chmod(os.path.join(stub, name), 0o755)
            env = dict(self.env, HOME=home, CYS_PACK_DIR=pack, CYS_ROLE="master", CYS_SURFACE_ID="7",
                       PATH=stub + os.pathsep + self.env.get("PATH", ""))
            r = subprocess.run([SH, os.path.join(hk, "session-start.sh")], capture_output=True, text=True,
                               encoding="utf-8", env=env, timeout=60,
                               input=json.dumps({"transcript_path": tp, "source": "startup"}) + "\n")
            self.assertEqual(r.returncode, 0)
            self.assertIn("요지 조립기(hooks/core_inject.py)가 실패", r.stdout)
            self.assertIn("조립기 파일 없음(실행 안 함)", r.stdout)
            ln = [l for l in self.lines() if " session-start " in l]
            self.assertEqual(len(ln), 1, self.lines())
            self.assertIn("rc=127 why=core_inject:조립기 파일 없음(실행 안 함)", ln[0])
            self.assertIn("role=master surface=7", ln[0])
            self.assertFalse(os.path.exists(os.path.join(pack, "hooks")), "시험 팩에 hooks/ 가 깔렸다(실 cys·cysd 가 탔다)")
            self.assertIn("cys claim-role master", open(os.path.join(stub, "calls.log")).read(), "목 cys 가 안 탔다")
            left = _procs_holding(tmp)
            self.assertFalse(left, "케이스 끝에 이 폴더를 쥔 프로세스가 남았다(고아 cysd 의심): %r" % (left,))
        finally:
            for pid in _procs_holding(tmp) or []:   # 회귀 시에도 고아를 남기지 않는다(이 케이스 폴더를 쥔 것만)
                try:
                    os.kill(pid, 15)
                except OSError:
                    pass
            shutil.rmtree(tmp, ignore_errors=True)

    def _counsel_env(self, config=None):
        # ★T3(agora-t3-pack-collector): 가짜 팩(.pack-version + bin/javis_counsel.py 사본) · 격리 agora 설정 폴더
        pack = os.path.join(self.st, "pack")
        os.makedirs(os.path.join(pack, "bin"))
        open(os.path.join(pack, ".pack-version"), "w").write("1.1.8\n")
        shutil.copy(os.path.join(os.path.dirname(HOOKS), "bin", "javis_counsel.py"), os.path.join(pack, "bin"))
        cfg = os.path.join(self.st, "agora")
        if config is not None:
            os.makedirs(cfg)
            open(os.path.join(cfg, "config.json"), "w").write(config)
        return dict(self.env, CYS_PACK_DIR=pack, AGORA_CONFIG_DIR=cfg), os.path.join(cfg, "counsel", "signals.jsonl")

    def test_counsel_signal_line(self):
        # ★T3: 같은 실패가 상담소 신호 한 줄로도 남는다 — source=역할 매핑 · op=hook.<훅> · error_code=hook.rc<rc> · rc·stdout 불변.
        env, sig = self._counsel_env()
        r = _sh('. "%s/_lib.sh"; cys_hook_fail session-start 127 "core_inject:x"; exit 3' % HOOKS, env)
        self.assertEqual((r.returncode, r.stdout), (3, ""))
        self.assertEqual(len(self.lines()), 1, "기존 파일 기록이 사라졌다")
        rows = [json.loads(x) for x in open(sig, encoding="utf-8").read().splitlines()]
        self.assertEqual([(x["source"], x["op"], x["error_code"], x["version"]) for x in rows],
                         [("cso", "hook.session-start", "hook.rc127", "1.1.8")])
        r = _sh('. "%s/_lib.sh"; CYS_PY=/nonexistent/py; cys_hook_fail h 1 y; echo "py=$CYS_PY"' % HOOKS, env)
        self.assertEqual((r.returncode, r.stdout), (0, "py=/nonexistent/py\n"), "호출 훅의 CYS_PY 를 바꿨다")

    def test_counsel_off_writes_nothing(self):
        env, sig = self._counsel_env('{"counsel": {"auto": false}}')
        r = _sh('. "%s/_lib.sh"; cys_hook_fail h 1 y; exit 0' % HOOKS, env)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual(len(self.lines()), 1)
        self.assertFalse(os.path.exists(sig), "끈 상태에서 신호를 썼다")

    def test_sibling_hooks_call_recorder(self):
        want = {
            "session-start.sh": 'cys_hook_fail session-start "$CI_RC"',
            "directive-event-inject.sh": 'cys_hook_fail directive-event-inject "$EV_RC"',
            "dept-chat-inject.sh": 'cys_hook_fail dept-chat-inject "$RC"',
            "inject-background.sh": 'cys_hook_fail inject-background "$BG_RC"',
            "role-bootstrap-legacy.sh": 'cys_hook_fail role-bootstrap "$DETECT_RC"',
        }
        for f, s in want.items():
            self.assertIn(s, open(os.path.join(HOOKS, f), encoding="utf-8").read(), f)
        self.assertIn('cys_hook_fail role-bootstrap "$ROLE_RC"',
                      open(os.path.join(HOOKS, "role-bootstrap-legacy.sh"), encoding="utf-8").read())



class SessionStartNoAutostart(unittest.TestCase):
    """★1.1.10 4b(master#4ec83d4b): session-start 가 부르는 cys 호출 전부(usage-register 두 갈래 · surface-role · claim-role)가
    CYS_NO_AUTOSTART=1 로 봉인된다 — 데몬 없는 HOME 에서 훅이 cysd 를 낳지 않는다. 종전 = usage-register(clear 아님)·claim-role 무봉인.
    부른 쪽 env 에 플래그가 없어도(unset) 호출 자체·인자는 종전 그대로다(봉인은 그 호출의 서브셸 안에서만)."""

    STUB = ('#!/bin/sh\necho "NA=${CYS_NO_AUTOSTART:-} $*" >> "$(dirname "$0")/calls.log"\n'
            'case "$1" in --version) echo "cys 0.0.0-stub" ;; esac\nexit 2\n')

    def run_hook(self, source):
        tmp = tempfile.mkdtemp(prefix="hf-na-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        stub = os.path.join(tmp, "stubbin")
        os.makedirs(stub)
        for name, body in (("cys", self.STUB), ("cysd", STUB_CYSD)):
            with open(os.path.join(stub, name), "w") as f:
                f.write(body)
            os.chmod(os.path.join(stub, name), 0o755)
        home = os.path.join(tmp, "h")
        os.makedirs(home)
        tp = os.path.join(tmp, "t.jsonl")
        open(tp, "w").write("")
        pack = os.path.join(tmp, "pack")                     # test_session_start_fallback_records_reason 와 같은 최소 팩
        os.makedirs(os.path.join(pack, "directives"))
        os.makedirs(os.path.join(pack, "bin"))
        open(os.path.join(pack, "directives", "MASTER_DIRECTIVE.md"), "w").write("BODY\n")
        open(os.path.join(pack, "bin", "javis_bootstrap.py"), "w").write("# stub\n")
        env = dict(_base_env(), HOME=home, CYS_PACK_DIR=pack, CYS_STATE_DIR=os.path.join(tmp, "st"),
                   CYS_ROLE="master", CYS_SURFACE_ID="7", PATH=stub + os.pathsep + os.environ.get("PATH", ""))
        env.pop("CYS_NO_AUTOSTART", None)                    # unset = 종전 조건
        r = subprocess.run([SH, os.path.join(HOOKS, "session-start.sh")], capture_output=True, text=True, encoding="utf-8",
                           env=env, timeout=60, input=json.dumps({"transcript_path": tp, "source": source}) + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = open(os.path.join(stub, "calls.log"), encoding="utf-8").read().splitlines()
        return calls, tp

    def assert_sealed(self, calls, tp, usage_args):
        by_verb = {}
        for c in calls:
            na, _, rest = c.partition(" ")
            by_verb.setdefault(rest.split(" ")[0], []).append((na, rest))
        self.assertNotIn("cysd", by_verb, "cysd 가 불렸다")
        for verb in ("usage-register", "surface-role", "claim-role"):
            self.assertIn(verb, by_verb, "%s 호출이 사라졌다(종전 동작 변경): %r" % (verb, calls))
            for na, rest in by_verb[verb]:
                if verb == "cys" or rest.startswith("--version"):
                    continue
                self.assertEqual(na, "NA=1", "봉인 없는 cys 호출: %s" % rest)
        self.assertEqual(by_verb["usage-register"][0][1], "usage-register --transcript %s%s" % (tp, usage_args))
        self.assertEqual(by_verb["claim-role"][0][1], "claim-role master")

    def test_startup_all_sealed(self):
        calls, tp = self.run_hook("startup")
        self.assert_sealed(calls, tp, "")

    def test_clear_all_sealed(self):
        calls, tp = self.run_hook("clear")
        self.assert_sealed(calls, tp, " --source clear")


if __name__ == "__main__":
    unittest.main()
