#!/usr/bin/env python3
"""TICKET=win-dept-chat-inject-timeout — 윈 1.1.10 마스터 hook.rc124 × hook.dept-chat-inject(10-28·10-29 각 1건).

결함: dept-chat-inject.sh 가 hook-prompt 파이썬을 안쪽 상한 4초(cys_timeout_run 4)로 돌린다. 본체 일은 가볍다(맥 실측
~0.04초 · 표준 모듈만 · 열린 제안 없으면 잠금·하위 프로세스 0) — 4초를 먹는 것은 윈의 해석기 기동(냉시작·백신 검사·
같은 UserPromptSubmit 의 role-bootstrap 파이썬과 동시 기동)이다. 넘으면 rc124 → 안내·소식·사람 확인 축 기록이 그 턴에 빠진다.
수리: 안쪽 상한 4→8초(같은 이벤트 role-bootstrap hook-triage 와 같은 값) · 하네스 선언 5→10초(안쪽 < 바깥 — 바깥이 먼저
자르면 rc 기록도 못 남긴다).

축 A = 기동이 5초 걸리는 해석기에서도 안내가 나오고 rc124 기록 0 (수리 전 = rc124 재현)
축 B = 멈춘 해석기는 여전히 안쪽 상한에서 끊기고 rc124 가 hook-errors.log 에 남는다(상한이 살아 있다)
축 C = 안쪽 상한 < 하네스 선언 timeout (계약 결박)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

PACK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SH = os.path.join(PACK, "hooks", "dept-chat-inject.sh")


def _inner_cap():
    with open(SH, encoding="utf-8") as f:
        m = re.search(r"cys_timeout_run (\d+) \"\$CYS_PY\".*hook-prompt", f.read())
    return int(m.group(1)) if m else None


class TestDeptChatInjectTimeout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dci-timeout-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, delay):
        """hook-prompt 를 부를 때만 delay 초 늦게 뜨는 해석기(그 밖 = cys_hook_fail 의 상담소 신호는 즉시).
        GNU timeout 없는 맥은 cys_timeout_run 이 `$CYS_PY -c …` 를 시계로 쓴다 — 시계(-c)는 늦추지 않는다."""
        w = os.path.join(self.tmp, "slow-py")
        with open(w, "w") as f:
            f.write('#!/bin/sh\n[ "$1" = "-c" ] || case "$*" in *hook-prompt*) sleep %s ;; esac\nexec "%s" "$@"\n'
                    % (delay, sys.executable))
        os.chmod(w, 0o755)
        env = {k: v for k, v in os.environ.items() if not k.startswith("CYS_")}
        env.update(HOME=self.home, CYS_ROLE="master", CYS_SURFACE_ID="7", CYS_PACK_DIR=PACK, CYS_PY=w,
                   CYS_STATE_DIR=os.path.join(self.home, ".cys", "state"),
                   CYS_DEPT_REQUESTS=os.path.join(self.home, ".cys", "dept-requests"))
        inp = json.dumps({"prompt": "교육부 만들어 줘", "session_id": "s"}, ensure_ascii=False)
        t0 = time.monotonic()
        p = subprocess.run(["sh", SH], input=inp, capture_output=True, text=True, env=env, timeout=60)
        log = os.path.join(self.home, ".cys", "state", "hook-errors.log")
        errs = ""
        if os.path.exists(log):
            with open(log, encoding="utf-8") as f:
                errs = f.read()
        return p, time.monotonic() - t0, errs

    def test_a_slow_interpreter_start_fits_budget(self):
        p, el, errs = self._run(5)
        self.assertEqual(p.returncode, 0)
        self.assertNotIn("rc=124", errs, "기동 5초 해석기에서 rc124 — 윈 rc124 재현(상한이 기동 시간보다 짧다)")
        self.assertIn("dept-by-chat", p.stdout, "안내 주입이 빠졌다")

    def test_b_hung_interpreter_still_cut_and_recorded(self):
        cap = _inner_cap()
        p, el, errs = self._run(60)
        self.assertEqual((p.returncode, p.stdout), (0, ""))
        self.assertIn("dept-chat-inject role=master surface=7 rc=124", errs, errs)
        self.assertLess(el, cap + 4, "안쪽 상한이 걸리지 않았다(%.1fs)" % el)

    def test_c_inner_cap_below_declared_harness_timeout(self):
        sys.path.insert(0, os.path.join(PACK, "bin"))
        import javis_preflight
        declared = javis_preflight.HOOK_TIMEOUT_S[("dept-chat-inject.sh", "UserPromptSubmit")]
        cap = _inner_cap()
        self.assertIsNotNone(cap, "훅의 hook-prompt 상한 줄을 못 찾았다")
        self.assertGreaterEqual(cap, 8, "안쪽 상한이 윈 기동 여유(8초)보다 짧다")
        self.assertLess(cap, declared, "안쪽 상한 %s ≥ 하네스 선언 %s — 하네스가 먼저 잘라 rc 기록도 못 남긴다"
                        % (cap, declared))


if __name__ == "__main__":
    unittest.main(verbosity=2)
