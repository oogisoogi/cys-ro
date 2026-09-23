#!/usr/bin/env python3
"""test_d1_dept_ready_probe — dbg-D1 부서 생성 경로의 두 결함(cys-dept · fd356c06 기준 적색).

#1 사전 확인 헛대기: cys-dept 의 ready() = 핑 120회 × (cys ping + sleep 0.1) 기다림 함수다. 이것을 기동
   **전** 「이미 떠 있나」 확인(launch·allocate·create 3자리)에 쓰면, 새 부서는 소켓이 없으므로 120회를 다
   돌고 나서야 cysd 를 띄운다 — 릴리스 빌드 실측 34.2초(핑 1회 ≈0.28초)의 헛대기.
   ⇒ 자리마다 기동 전 핑 수 ≤ 10 단언(패치본 실측 3 = 예약 단계 확인 2 + 사전 확인 1 · 기준선 120+).
#2 편성 백그라운드가 호출자 파이프를 쥔다: formation_ensure_async 의 `( python3 … >>log 2>&1 ) &` 는
   python 의 출력만 돌리고 **서브셸 자신**은 호출자의 stdout/stderr 를 그대로 물려받는다. 앱 직접 실행
   경로(src-tauri run_dept_tool_direct = `cmd.output()` · 윈도 전부 · 맥 대행 실패 폴백)는 EOF 까지 읽으므로
   편성(역할당 최대 200s)이 끝날 때까지 ＋부서 응답이 오지 않는다.
   ⇒ 가짜 javis_formation.py(60초 잠) 를 두고 파이프로 읽은 호출이 50초 안에 끝나는지 단언 — #1(34초)과
     섞이지 않는 문턱이다(#2 만 고침 ≈36초 초록 · #1 만 고침 ≈62초 적색 · 둘 다 ≈2초).

행위 시험: 격리 HOME 에 가짜 cys(핑을 세고 `up` 표식이 있어야 성공) · 가짜 cysd(기동 순간까지 온 핑 수를
기록하고 `up` 을 세움)를 두고 `cys-dept` 를 실제로 돌린다. 가짜 cysd 뒤 꼬리의 성패는 재지 않는다.
라이브 무접촉: HOME·레지스트리·팩 전부 임시 폴더 · 실 cys/cysd 를 부르지 않는다(PATH 맨 앞 가짜 —
cys-dept 가 $HOME/.local/bin 을 PATH 앞에 붙이므로 그 자리에 둔다).
"""
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest

SELF = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(SELF)
CYS_DEPT = os.path.join(BIN, "cys-dept")

FAKE_CYS = r"""#!/bin/bash
T="$D1_T"
if [ "$1" = "ping" ]; then
  echo x >> "$T/pings"
  [ -f "$T/up" ] && exit 0
  exit 1
fi
exit 0
"""

FAKE_CYSD = r"""#!/bin/bash
T="$D1_T"
n=0; [ -f "$T/pings" ] && n=$(wc -l < "$T/pings" | tr -d ' ')
echo "$n" > "$T/spawned"
touch "$T/up"
sleep 3
"""

FAKE_FORMATION = "import time\ntime.sleep(60)\n"


class _Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="d1rp-", dir="/tmp")
        self.home = os.path.join(self.t, "h")
        lb = os.path.join(self.home, ".local", "bin")
        os.makedirs(lb)
        for name, body in (("cys", FAKE_CYS), ("cysd", FAKE_CYSD)):
            p = os.path.join(lb, name)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, 0o755)
        self.env = {
            "HOME": self.home, "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "D1_T": self.t,
            "CYS_DEPTS_JSON": os.path.join(self.t, "depts.json"), "LANG": "C",
        }

    def tearDown(self):
        subprocess.run(["/usr/bin/pkill", "-f", self.t], capture_output=True)
        shutil.rmtree(self.t, ignore_errors=True)

    def _catalog(self):
        cat = os.path.join(self.t, "cat.json")
        cwd = os.path.join(self.t, "work")
        os.makedirs(cwd)
        acct = os.path.join(self.home, ".cys", "claude")
        os.makedirs(acct, exist_ok=True)
        with open(cat, "w") as f:
            json.dump({"accounts": {"owner": acct},
                       "departments": {"probe": {"display": "probe", "account": "owner",
                                                 "mission_key": "probe", "cwd": cwd}}}, f)
        self.env["CYS_DEPT_CATALOG"] = cat
        self.env["CYS_DEPT_MISSIONS"] = os.path.join(self.t, "missions")

    def _pings_before_spawn(self, argv):
        subprocess.run(["/bin/bash", CYS_DEPT] + argv, env=self.env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
        spawned = os.path.join(self.t, "spawned")
        self.assertTrue(os.path.exists(spawned),
                        "전제 실패: 가짜 cysd 가 한 번도 불리지 않았다(시험이 기동 지점에 닿지 않음) · %s" % argv)
        with open(spawned) as f:
            pings = int(f.read().strip() or "0")
        self.assertGreaterEqual(pings, 1, "전제: 기동 전 사전 확인 핑이 0회 — 계측이 대상에 안 닿았다")
        return pings


class DeptReadyProbe(_Base):
    """#1 — 세 자리 각각(자리 하나만 되돌려도 그 자리 시험이 적색)."""

    def _assert_no_wait_loop(self, argv):
        pings = self._pings_before_spawn(argv)
        self.assertLessEqual(
            pings, 10,
            "%s: 새 부서 데몬을 띄우기 전 핑 %d회 — 사전 확인이 기다림 함수(ready · 120회)를 쓰고 있다"
            % (argv[0], pings))

    def test_launch_spawns_daemon_without_ready_wait_loop(self):      # :1236 (rotate 재귀 포함)
        self._assert_no_wait_loop(["launch", "probe"])

    def test_allocate_spawns_daemon_without_ready_wait_loop(self):    # :1348
        self._assert_no_wait_loop(["allocate"])

    def test_create_spawns_daemon_without_ready_wait_loop(self):      # :1517
        self._catalog()
        self._assert_no_wait_loop(["create", "probe"])


class DeptFormationDoesNotHoldCallerPipe(_Base):
    """#2 — 파이프로 읽는 호출자(앱 직접 실행 경로)가 백그라운드 편성 종료까지 묶이지 않는다."""

    def test_create_returns_eof_before_background_formation_ends(self):
        self._catalog()
        fb = os.path.join(self.home, ".cys", "pack", "bin")
        os.makedirs(fb)
        with open(os.path.join(fb, "javis_formation.py"), "w") as f:
            f.write(FAKE_FORMATION)
        # 계정시드(seed_agents_account)의 원천 = 본부 팩 agents.json — 최소 모양만 둔다.
        with open(os.path.join(self.home, ".cys", "pack", "agents.json"), "w") as f:
            json.dump({"claude": {"cmd": "claude", "env": {"CLAUDE_CONFIG_DIR": "x"}}}, f)
        t0 = time.time()
        r = subprocess.run(["/bin/bash", CYS_DEPT, "create", "probe"], env=self.env,
                           capture_output=True, text=True, timeout=90)
        took = time.time() - t0
        self.assertIn("상비편성 ensure 착수", r.stderr,
                      "전제: 편성 착수 지점에 닿지 않았다(시험이 대상에 안 닿음) · stderr=%r" % r.stderr[-400:])
        self.assertLess(
            took, 50,
            "create 를 파이프로 읽은 호출이 %.1f초 걸렸다 — 백그라운드 편성 서브셸이 호출자 stdout/stderr 를 "
            "쥐고 있어 EOF 가 편성 종료(가짜 60초)까지 안 온다(앱 cmd.output() 경로가 그만큼 묶인다)" % took)


if __name__ == "__main__":
    unittest.main()
