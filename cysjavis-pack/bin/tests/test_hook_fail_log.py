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


def _sh(script, env):
    return subprocess.run([SH, "-c", script], capture_output=True, text=True, env=env, timeout=30)


class T(unittest.TestCase):
    def setUp(self):
        self.st = tempfile.mkdtemp(prefix="hf-")
        self.env = dict(os.environ, CYS_STATE_DIR=self.st, CYS_ROLE="cso", CYS_SURFACE_ID="44")
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
            env = dict(self.env, HOME=home, CYS_PACK_DIR=pack, CYS_ROLE="master", CYS_SURFACE_ID="7")
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
        finally:
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


if __name__ == "__main__":
    unittest.main()
