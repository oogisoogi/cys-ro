#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_restore_order_1121.py — 복원 기동 순서 = master 먼저 (TICKET=cysr-1121-restore D4).

  U. 순수 함수 restore_order — master 만 앞으로 · 나머지 받은 순서 그대로(안정) · 비슷한 이름은 master 아님
  S. run_restore(prod 경로 · 데몬/cys 무접촉 대역) fresh 강등 루프의 실제 기동 호출 순서
     S1 master 가 force_fresh(앞 사이클 ps 축) · worker 는 보통 resume 실패 → fresh 루프 직전 재결합(:need + forced_fresh)
        뒤에도 첫 기동 = master
     S2 대조: force_fresh 없이 명부 순서 [worker, cso, master] 전원 resume 실패 → fresh 순서 첫째 = master · 나머지 명부 순서
  R. 수동 복원 runbook(MANUAL_RESTORE.sh · .ps1 · Fable 코드 1R minor) — launch-agent 줄 순서 = master 먼저 · 자동 복원 끝 대기 줄이
     launch-agent 줄보다 앞 · rc 95 뜻 안내 · sh 문법(bash -n)
  M. 뮤턴트 — 재결합 지점 restore_order 제거 → S1 적색 · restore_order 가 정렬을 안 함 → U·S2·R 적색 · runbook 순서 정렬 제거 → R 적색

실행: python3 cysjavis-pack/bin/tests/test_phoenix_restore_order_1121.py → 종료 토큰 PHOENIX-RESTORE-ORDER-1121-OK
"""
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.normpath(os.path.join(HERE, "..", "javis_phoenix.py"))
fails = []

ZSH = (1, "-zsh")
T_DEAD = {664: ZSH, 665: ZSH, 666: ZSH, 1: (0, "launchd")}


def check(name, cond, detail="", sink=None):
    if sink is None:
        print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + str(detail)) if detail else ""))
        if not cond:
            fails.append(name)
    elif not cond:
        sink.append(name)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def unit_axes(m, sink=None):
    ro = m.restore_order
    for given, want in [
        (["worker", "cso", "master"], ["master", "worker", "cso"]),
        (["cso", "master", "worker-2", "worker"], ["master", "cso", "worker-2", "worker"]),
        (["master", "worker"], ["master", "worker"]),
        (["worker", "cso"], ["worker", "cso"]),
        ([], []),
        (["master-2", "dept-master", "master"], ["master", "master-2", "dept-master"]),
    ]:
        check("U restore_order(%s)" % given, ro(list(given)) == want, ro(list(given)), sink)


def stub_world(m, root, roster, seats, shell_pids, fresh_calls):
    m.CYS = os.path.join(root, "nonexistent-cys")
    m.log = lambda msg: None
    m._emit_evt = lambda *a, **k: None
    m._acquire_restore_lease = lambda s: (True, None)
    m.get_boot_epoch = lambda s: "EPOCH-1121"
    m._recover_retention_file = lambda s, p, k: {"status": "missing"}
    m._recovered_provenance = lambda p: None
    m.c6_reap_stale_surfaces = lambda s: {}
    m.observe_and_persist_roster = lambda s, rebase=False: (dict(roster), set())
    m.live_role_surfaces = lambda s: {r: list(v) for r, v in seats.items()}
    m._surface_shell_pids = lambda s: dict(shell_pids)
    m._ps_table = lambda: T_DEAD
    m._ps_comm = lambda pid: None
    m.restore_supports_per_entry_cwd = lambda s=None: False
    m.master_seat_cwd = lambda s, entries=None: None
    m.seat_fresh_cwd = lambda role, c, mc, log_fn=None: c
    m.fresh_awaken = lambda *a, **k: "awaken-stub"
    m.spawn_production = lambda s, roles, include_master=False, cwd=None, **_kw: {"rc": 0, "out": "ok"}
    m.spawn_in_seat_production = lambda s, include_master=False, cwd=None, units=None: {"rc": 0, "out": "ok"}

    def _fresh(s, role, agent, cwd=None):
        fresh_calls.append(role)
        return {"rc": 0, "out": "launched"}
    m.spawn_fresh_production = _fresh
    m.stage_ready = lambda s, role, surf, stub: (True, "ready-stub")
    m.stage_observe_session = lambda s, surf, stub, role=None: (None, "stub")
    m.stage_reinject = lambda s, role, surf, stub: (True, "reinject-stub")
    m.stage_g2_ack = lambda s, role, surf, stub: (True, "g2-stub")
    m.SPAWN_SETTLE = 0.0
    m.SPAWN_BACKOFF = 0.0


def _sock(root, name):
    d = os.path.join(root, name)
    os.makedirs(os.path.join(d, "phoenix"), exist_ok=True)
    return os.path.join(d, "cys.sock")


def scenario_axes(m, root, sink=None):
    # S1 — 1사이클: master 좌석 표시 occupied + ps 죽음 → force_fresh 표식(test_phoenix_a3 와 같은 길).
    #      2사이클: worker 가 명부 앞에 새로 생기고(좌석 없음 = 보통 resume 실패 길) master 는 force_fresh 그대로.
    sock = _sock(root, "s1")
    roster1 = {"master": {"agent": "claude", "session_id": "SM", "cwd": root}}
    seats1 = {"master": [{"surface": "surface:1", "pid": None, "exited": False, "agent_alive": None, "seat": "occupied"}]}
    calls = []
    stub_world(m, root, roster1, seats1, {"surface:1": 664}, calls)
    m.spawn_fresh_production = lambda s, role, agent, cwd=None: {"rc": 1, "out": "stub-fail"}  # 1사이클 fresh 는 실패시켜 force_fresh 를 남긴다
    m.run_restore(sock, ticket="o1", stub=False, no_breaker=True, print_result=False)
    j = m.load_journal(sock, "o1")
    forced = (j["roles"].get("master") or {}).get("force_fresh") is True
    check("S1-pre 1사이클 뒤 master force_fresh 표식", forced, (j["roles"].get("master") or {}).get("force_fresh"), sink)
    roster2 = {"worker": {"agent": "claude", "session_id": "SW", "cwd": root},
               "master": {"agent": "claude", "session_id": "SM", "cwd": root}}
    calls2 = []
    stub_world(m, root, roster2, seats1, {"surface:1": 664}, calls2)
    m.run_restore(sock, ticket="o1", stub=False, no_breaker=True, print_result=False)
    check("S1 force_fresh master + 보통 worker → fresh 첫 기동 = master", calls2[:1] == ["master"] and "worker" in calls2,
          calls2, sink)

    # S2 — force_fresh 없음 · 명부 [worker, cso, master] 전원 좌석 없음(resume 실패) → fresh 순서
    sock2 = _sock(root, "s2")
    roster3 = {"worker": {"agent": "claude", "session_id": "SW", "cwd": root},
               "cso": {"agent": "claude", "session_id": "SC", "cwd": root},
               "master": {"agent": "claude", "session_id": "SM", "cwd": root}}
    calls3 = []
    stub_world(m, root, roster3, {}, {}, calls3)
    m.run_restore(sock2, ticket="o2", stub=False, no_breaker=True, print_result=False)
    check("S2 명부 [worker,cso,master] → fresh 순서 = [master, worker, cso]", calls3[:3] == ["master", "worker", "cso"],
          calls3, sink)


def runbook_axes(m, root, sink=None):
    import subprocess
    roster = {"cso": {"agent": "claude"}, "worker": {"agent": "codex"}, "master": {"agent": "claude"}}
    for name, render, wait_mark in [("sh", m._render_deploy_runbook, '"auto_restore": *"(running|retry_wait|held)"'),
                                    ("ps1", m._render_deploy_runbook_ps1, "@('running','retry_wait','held')")]:
        text = render(roster)
        lines = text.splitlines()
        la = [l.split()[3] for l in lines if l.startswith("cys launch-agent --role ")]
        check("R %s launch-agent 순서 = master 먼저 · 나머지 이름순" % name, la == ["master", "cso", "worker"], la, sink)
        wait_at = next((i for i, l in enumerate(lines) if wait_mark in l), None)
        first_la = next((i for i, l in enumerate(lines) if l.startswith("cys launch-agent ")), None)
        check("R %s 자동 복원 끝 대기 줄이 launch-agent 앞" % name,
              wait_at is not None and first_la is not None and wait_at < first_la, (wait_at, first_la), sink)
        check("R %s rc 95 뜻 안내" % name, "rc 95" in text and "CYS_LAUNCH_DURING_RESTORE" in text, None, sink)
    p = os.path.join(root, "MR-%d.sh" % os.getpid())
    with open(p, "w", encoding="utf-8") as f:
        f.write(m._render_deploy_runbook(roster))
    rc = subprocess.run(["bash", "-n", p], capture_output=True).returncode
    check("R sh bash -n 문법", rc == 0, rc, sink)


def mutants(root):
    src = open(PH, encoding="utf-8").read()
    remerge = "    need = restore_order(need + [r for r in forced_fresh if r not in need and r not in session_lease_held])\n"
    sorter = '    return sorted(roles, key=lambda r: 0 if r == "master" else 1)\n'
    muts = [
        ("M1 재결합 지점 restore_order 제거", remerge,
         "    need = need + [r for r in forced_fresh if r not in need and r not in session_lease_held]\n", ["S1"]),
        ("M2 restore_order 가 정렬 안 함", sorter, "    return list(roles)\n", ["U", "S2", "R"]),
        ("M3 runbook sh 순서 정렬 제거", "    for role in restore_order(sorted(roster.keys())):\n        agent = (roster.get(role) or {}).get(\"agent\") or \"claude\"\n        lines.append('cys",
         "    for role in sorted(roster.keys()):\n        agent = (roster.get(role) or {}).get(\"agent\") or \"claude\"\n        lines.append('cys", ["R"]),
    ]
    for name, old, new, want_red in muts:
        assert src.count(old) == 1, "변이 자리 소실: %s" % name  # 선-assert: 변이가 실제로 적용된다
        mp = os.path.join(root, "mut_%d.py" % len(name))
        with open(mp, "w", encoding="utf-8") as f:
            f.write(src.replace(old, new))
        mm = load(mp, "ph_mut_%d" % abs(hash(name)))
        sink = []
        unit_axes(mm, sink)
        r = tempfile.mkdtemp(prefix="ph1121m-")
        try:
            scenario_axes(mm, r, sink)
            runbook_axes(mm, r, sink)
        finally:
            shutil.rmtree(r, ignore_errors=True)
        red = [w for w in want_red if any(s.startswith(w) for s in sink)]
        check("%s → 적색 %s" % (name, want_red), red == want_red, sink)


def main():
    root = tempfile.mkdtemp(prefix="ph1121-")
    try:
        m = load(PH, "ph_1121")
        unit_axes(m)
        scenario_axes(m, root)
        runbook_axes(m, root)
        mutants(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if fails:
        print("FAIL %d: %s" % (len(fails), fails))
        return 1
    print("PHOENIX-RESTORE-ORDER-1121-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
