#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_counsel_doctor_timeout.py — 상담소 daily 의 doctor 칸이 윈에서 60초 상한에 잘리지 않는가 + 시간 초과 때 자손째 끝내는가
(1.1.21 · TICKET=cysr-1121-pack · TODO 76 · 분석 reports/user-reports/2026-11-27-anomaly-analysis.md §10).

★왜: 윈 daily 에서 doctor 칸이 빠진 328건 중 300건이 수집~도착 60초 이상(중앙 63.2초 · 실림 77/404) — javis_counsel.py
  DOCTOR_TIMEOUT_S = 60 에 걸렸다. 고침 = 윈 상한 DOCTOR_TIMEOUT_NT_S(doctor_timeout_s()) + 시간 초과 때 _kill_group 재사용(_run_tree).
세 칸:
  ① 고르기·예산 — 윈 꼴(counsel 모듈의 os 만 name="nt")이면 윈 상한 · 윈 상한 > 70초 · 틱 예산 불변식(최악 합 ≤ 500 − agora 최소 30)
  ② 가짜 cys 가 70초 뒤 doctor JSON 을 내면 윈 상한으로 칸이 실린다(옛 60초면 None)
  ③ 상한 안에 안 끝나면 None 이고, 가짜 cys 가 띄운 손자 프로세스까지 끝난다(옛 subprocess.run 이면 손자가 남는다)
★되돌리면 붉음(2026-11-27 실측 · 변이 4): 윈 상한 60 · probe_doctor 가 DOCTOR_TIMEOUT_S 직접 사용 · probe_doctor 가 옛 _run 사용 ·
  _run_tree 에서 _kill_group 빼고 proc.kill() 만.
★소요 ≈75초(② 가 실제로 70초 기다린다 — 60초 경계를 넘는 것이 재는 대상이라 줄일 수 없다).
"""
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.dont_write_bytecode = True

import javis_counsel as jc  # noqa: E402

NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

DOCTOR_JSON = {"fix": False, "summary": {"ok": 3, "warn": 1, "fail": 1, "skip": 0},
               "items": [{"name": "hook", "status": "WARN", "detail": "", "action": ""},
                         {"name": "runtime-seal", "status": "FAIL", "detail": "", "action": ""}]}


class _OsNtShape:
    """counsel 모듈의 os 만 윈 꼴로(전역 os.name 무변경)."""
    name = "nt"

    def __getattr__(self, k):
        return getattr(os, k)


def _fake_cys(d, doctor_sleep, grandchild_pidfile=None):
    """가짜 cys — `doctor --json` 이면 (손자를 띄우고) doctor_sleep 초 뒤 JSON. 그 밖 동사 = rc 0 빈 출력."""
    body = [
        "import json, subprocess, sys, time",
        "a = sys.argv[1:]",
        "if a[:2] == ['doctor', '--json']:",
    ]
    if grandchild_pidfile:
        body += [
            "    g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'],",
            "                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)",
            "    open(%r, 'w').write(str(g.pid))" % grandchild_pidfile,
        ]
    body += [
        "    time.sleep(%r)" % float(doctor_sleep),
        "    print(json.dumps(%r))" % (DOCTOR_JSON,),
        "sys.exit(0)",
    ]
    if os.name == "nt":                     # 윈 = .cmd 감싸개(가짜 cys 가 python 스크립트라)
        py = os.path.join(d, "fakecys.py")
        with open(py, "w", encoding="utf-8") as f:
            f.write("\n".join(body) + "\n")
        exe = os.path.join(d, "cys.cmd")
        with open(exe, "w", encoding="utf-8") as f:
            f.write('@"%s" "%s" %%*\r\n' % (sys.executable, py))
        return exe
    exe = os.path.join(d, "cys")
    with open(exe, "w", encoding="utf-8") as f:
        f.write("#!%s\n" % sys.executable + "\n".join(body) + "\n")
    os.chmod(exe, os.stat(exe).st_mode | stat.S_IXUSR)
    return exe


def _alive(pid):
    if os.name == "nt":
        r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"], stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=30, **NOWIN)
        return str(pid) in r.stdout.decode("utf-8", "replace")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # 좀비(끝났으나 아직 회수 전)는 산 것이 아니다 — ps 상태로 가른다.
    r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
    st = r.stdout.decode("utf-8", "replace").strip()
    return bool(st) and not st.startswith("Z")


def _cleanup(pid):
    if pid and _alive(pid):
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=30, **NOWIN)
            else:
                os.kill(pid, signal.SIGKILL)
        except (OSError, subprocess.SubprocessError):
            pass


def main():
    fails = []

    # ① 고르기 · 예산
    with mock.patch.object(jc, "os", _OsNtShape()):
        if jc.doctor_timeout_s() != jc.DOCTOR_TIMEOUT_NT_S:
            fails.append("윈 꼴인데 doctor_timeout_s()=%r ≠ DOCTOR_TIMEOUT_NT_S" % jc.doctor_timeout_s())
    if os.name != "nt" and jc.doctor_timeout_s() != jc.DOCTOR_TIMEOUT_S:
        fails.append("맥·리눅스 상한이 바뀜: %r" % jc.doctor_timeout_s())
    if not jc.DOCTOR_TIMEOUT_NT_S > 70:
        fails.append("윈 상한 %r ≤ 70초 — 60초에서 잘리던 기기(중앙 63.2초)를 못 덮는다" % jc.DOCTOR_TIMEOUT_NT_S)
    # 틱 예산: 한 판 agora 몫(500 = TICK_CAP_S − KILL_BUDGET_S) 안에서 facts 최악 합 + agora 최소가 넘치면 안 된다.
    worst_facts = (jc.INSTALL_LOCK_WAIT_S + 2 * jc.CLI_TIMEOUT_S + jc.DOCTOR_TIMEOUT_NT_S + jc.KILL_BUDGET_S
                   + 2 * jc.HELP_TIMEOUT_S)
    room = jc.TICK_CAP_S - jc.KILL_BUDGET_S
    if worst_facts + jc.AGORA_MIN_TIMEOUT_S > room:
        fails.append("틱 예산 초과: facts 최악 %.0f + agora 최소 %d > %d" % (worst_facts, jc.AGORA_MIN_TIMEOUT_S, room))

    tmp = tempfile.mkdtemp(prefix="counsel-doctor-")

    # ② 70초 걸리는 doctor — 윈 상한이면 실린다
    exe = _fake_cys(os.path.join(tmp), 70)
    with mock.patch.dict(os.environ, {"CYS_CYS_BIN": exe}), \
            mock.patch.object(jc, "doctor_timeout_s", lambda: jc.DOCTOR_TIMEOUT_NT_S):
        t = time.monotonic()
        got = jc.probe_doctor()
        took = time.monotonic() - t
    want = {"ok": 3, "warn": 1, "fail": 1, "skip": 0, "warn_ids": ["hook"], "fail_ids": ["runtime-seal"]}
    if got != want:
        fails.append("70초 doctor 가 윈 상한에서 안 실림(%.1f초 · got=%r)" % (took, got))

    # ③ 상한 안에 안 끝나면 None · 손자까지 끝남
    d3 = os.path.join(tmp, "kill")
    os.makedirs(d3)
    pidfile = os.path.join(d3, "grandchild.pid")
    exe3 = _fake_cys(d3, 60, grandchild_pidfile=pidfile)
    gpid = None
    try:
        with mock.patch.dict(os.environ, {"CYS_CYS_BIN": exe3}), \
                mock.patch.object(jc, "doctor_timeout_s", lambda: 3):
            t = time.monotonic()
            got3 = jc.probe_doctor()
            took3 = time.monotonic() - t
        if got3 is not None:
            fails.append("상한(3초) 넘긴 doctor 가 None 이 아님: %r" % (got3,))
        if took3 > 3 + jc.KILL_BUDGET_S:
            fails.append("시간 초과 뒤 회수가 끝내기 몫을 넘김(%.1f초)" % took3)
        try:
            gpid = int(open(pidfile).read().strip())
        except (OSError, ValueError):
            fails.append("가짜 cys 가 손자 pid 를 못 남김 — ③ 이 공허함")
        if gpid:
            deadline = time.monotonic() + 5
            while _alive(gpid) and time.monotonic() < deadline:
                time.sleep(0.2)
            if _alive(gpid):
                fails.append("시간 초과 뒤 손자 프로세스(pid %d)가 살아 있음 — 자손째 끝내기 실패" % gpid)
    finally:
        _cleanup(gpid)

    if fails:
        print("FAIL: " + " | ".join(fails))
        return 1
    print("PASS: 윈 doctor 상한 %d초 — 70초 doctor 실림(%.1f초) · 상한 넘김 None + 손자 끝남(%.1f초) · 틱 예산 최악 %.0f+%d ≤ %d"
          % (jc.DOCTOR_TIMEOUT_NT_S, took, took3, worst_facts, jc.AGORA_MIN_TIMEOUT_S, room))
    return 0


if __name__ == "__main__":
    sys.exit(main())
