#!/usr/bin/env python3
"""test_hook_timing — v113 Q1 계측: Stop 훅 경과 시간 1줄 기록(_lib.sh cys_hook_timing · cys-hook.sh Stop 분기).

관측 전용 계약: ①어떤 종료 경로(exit 0·exit 3)에서도 한 줄 ②stdout 무출력 ③상태 dir 을 못 써도 훅 종료 코드 불변
④cys-hook.sh 는 Stop 계열에서만 기록(매 툴 호출마다 쓰지 않는다) ⑤Stop 훅 3종이 실제로 부른다.
"""
import os
import subprocess
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks")


def _sh(script, env):
    return subprocess.run(["sh", "-c", script], capture_output=True, text=True, env=env, timeout=30)


class T(unittest.TestCase):
    def setUp(self):
        self.st = tempfile.mkdtemp(prefix="ht-")
        self.env = dict(os.environ, CYS_STATE_DIR=self.st, CYS_ROLE="cso", CYS_SURFACE_ID="44")
        self.log = os.path.join(self.st, "hook-timing.log")

    def lines(self):
        return open(self.log).read().splitlines() if os.path.exists(self.log) else []

    def test_records_one_line_on_any_exit_and_keeps_rc(self):
        r = _sh('. "%s/_lib.sh"; cys_hook_timing save-state; exit 3' % HOOKS, self.env)
        self.assertEqual(r.returncode, 3, "계측이 훅 종료 코드를 바꿨다")
        self.assertEqual(r.stdout, "", "계측이 stdout 을 오염시켰다")
        ln = self.lines()
        self.assertEqual(len(ln), 1, ln)
        self.assertRegex(ln[0], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ save-state role=cso surface=44 \d+s$")

    def test_unwritable_state_dir_is_harmless(self):
        env = dict(self.env, CYS_STATE_DIR="/dev/null/nope")
        r = _sh('. "%s/_lib.sh"; cys_hook_timing grill-stop; exit 0' % HOOKS, env)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_rotates_over_cap(self):
        with open(self.log, "w") as f:
            f.write("x" * 300000)
        _sh('. "%s/_lib.sh"; cys_hook_timing reflect-scan' % HOOKS, self.env)
        self.assertTrue(os.path.exists(self.log + ".1"))
        self.assertEqual(len(self.lines()), 1)

    def _legacy_path(self):
        """★1.1.8 병합(원작자 0.14.42 R3-4 빠른 길 수용): 오버레이 `<이벤트>.d` 가 하나도 없으면 cys-hook.sh 는
        hook JSON 을 읽지 않고(이벤트명 미상) cys 로 곧장 흘리고 끝난다 — 그 길에는 Stop 계측 1줄이 없다
        (cys-hook.sh 는 C33 등록상 Pre/PostToolUse·PermissionRequest 전용이라 운영 Stop 은 이 훅을 타지 않는다 ·
        Stop 계측의 본체는 save-state·reflect-scan·grill-stop 의 cys_hook_timing). 이 계측 분기를 재려면 빈 오버레이
        디렉터리 하나로 종전 경로(윈도 Git Bash·오버레이 설치 좌석과 같은 길)를 태운다."""
        os.makedirs(os.path.join(self.st, "hooks", "Stop.d"), exist_ok=True)

    def test_cys_hook_logs_only_stop_events(self):
        env = dict(self.env, PATH="/usr/bin:/bin", CYS_LOCAL_DIR=self.st)   # cys 부재 = 데몬 push 생략
        self._legacy_path()
        for ev in ("PreToolUse", "Stop"):
            subprocess.run(["sh", os.path.join(HOOKS, "cys-hook.sh")], input='{"hook_event_name": "%s"}' % ev,
                           capture_output=True, text=True, env=env, timeout=30)
        ln = self.lines()
        self.assertEqual(len(ln), 1, ln)
        self.assertIn("cys-hook(Stop)", ln[0])

    def test_cys_hook_rotates_over_cap(self):
        with open(self.log, "w") as f:
            f.write("x" * 300000)
        env = dict(self.env, PATH="/usr/bin:/bin", CYS_LOCAL_DIR=self.st)
        self._legacy_path()
        subprocess.run(["sh", os.path.join(HOOKS, "cys-hook.sh")], input='{"hook_event_name": "Stop"}',
                       capture_output=True, text=True, env=env, timeout=30)
        self.assertTrue(os.path.exists(self.log + ".1"), "cys-hook.sh 기록이 상한 회전을 안 탄다(agy 1R ④)")
        self.assertEqual(len(self.lines()), 1)

    def test_stop_hooks_call_timer(self):
        for f in ("save-state.sh", "reflect-scan.sh", "grill-stop.sh"):
            self.assertIn("\ncys_hook_timing %s " % f[:-3], open(os.path.join(HOOKS, f), encoding="utf-8").read(), f)


if __name__ == "__main__":
    unittest.main()
