#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_a3_ps_axis.py — 재기동 뒤 죽은 마스터 자리를 VERIFIED 로 읽지 않는다 (TICKET=cysr-102-pack-a A3).

실측 계기(run7): VM 재기동 뒤 `cys list` 는 role=master 인데 좌석 셸(zsh pid 664) 아래 claude 프로세스가
없었다. 종전 생존 증거는 데몬 표시(exited·seat)와 세션핀 대조뿐이었고, 세션핀은 topology.json 에 재기동을
넘어 남아 expected==observed → VERIFIED 가 될 수 있었다.

  U. 순수 판정 agent_process_verdict(가짜 프로세스 표)
     U1 살아있음(zsh → node …/claude-code/cli.js) · U2 손자(zsh → bash → claude) · U3 죽음(run7: 셸 단독)
     U4 죽음(에이전트 아닌 자손만) · U5 판정 불가(표 없음·pid 미상·셸이 표에 없음) = unknown
  S. run_restore 2 사이클(prod 경로 · 데몬/cys 무접촉 대역)
     S1 좌석 표시 occupied + ps 죽음 → 부활 대상 편입 · 세션핀 일치여도 VERIFIED 아님 · force_fresh 기록
     S2 다음 사이클 → cys restore(resume) 없이 곧장 fresh 재기동(launch-agent) · ps 살아남 → fresh 확정
     S3 대조군: ps 살아있음 → 생존(NOOP · 오강등 0)
  M. 뮤턴트 3(변이 적용 선-assert 동반) — 각각 위 축 중 하나 이상 적색이어야 한다
     M1 verify ps 축 제거 · M2 대상 산정 ps 축 제거 · M3 순수 판정이 'dead' 대신 'alive'

실행: python3 cysjavis-pack/bin/tests/test_phoenix_a3_ps_axis.py → 종료 토큰 PHOENIX-A3-PS-AXIS-OK
"""
import importlib.util
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.normpath(os.path.join(HERE, "..", "javis_phoenix.py"))
fails = []


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


ZSH = (1, "-zsh")
T_ALIVE = {664: ZSH, 700: (664, "node /opt/homebrew/lib/node_modules/@anthropic-ai/claude-code/cli.js")}
T_GRAND = {664: ZSH, 690: (664, "bash -lc run"), 701: (690, "/srv/agent/bin/claude --resume S1")}
T_DEAD = {664: ZSH, 1: (0, "launchd")}
T_OTHER = {664: ZSH, 710: (664, "sleep 100")}


def unit_axes(m, sink=None):
    v = m.agent_process_verdict
    check("U1 셸 → node …/claude-code/cli.js = alive", v(664, "claude", T_ALIVE) == "alive",
          v(664, "claude", T_ALIVE), sink)
    check("U2 셸 → bash → claude(손자) = alive", v(664, "claude", T_GRAND) == "alive",
          v(664, "claude", T_GRAND), sink)
    check("U3 셸 단독(run7 zsh 664) = dead", v(664, "claude", T_DEAD) == "dead", v(664, "claude", T_DEAD), sink)
    check("U4 에이전트 아닌 자손만(sleep) = dead", v(664, "claude", T_OTHER) == "dead",
          v(664, "claude", T_OTHER), sink)
    got = [v(664, "claude", None), v(None, "claude", T_DEAD), v(999, "claude", T_DEAD)]
    check("U5 표 없음·pid 미상·셸 부재 = unknown(종전 동작 유지)", got == ["unknown"] * 3, got, sink)


def scenario_axes(m, root, sink=None):
    """run_restore 2 사이클. m 의 전역을 대역으로 치환한다(데몬·cys·ps 실호출 0)."""
    sockdir = os.path.join(root, "sock")
    os.makedirs(os.path.join(sockdir, "phoenix"), exist_ok=True)
    sock = os.path.join(sockdir, "cys.sock")
    calls = {"restore": 0, "fresh": 0}
    state = {"table": T_DEAD}
    m.CYS = os.path.join(root, "nonexistent-cys")
    m.log = lambda msg: None
    m._emit_evt = lambda *a, **k: None
    m._acquire_restore_lease = lambda s: (True, None)
    m.get_boot_epoch = lambda s: "EPOCH-A3"
    m._recover_retention_file = lambda s, p, k: {"status": "missing"}
    m._recovered_provenance = lambda p: None
    m.c6_reap_stale_surfaces = lambda s: {}
    m.observe_and_persist_roster = lambda s, rebase=False: (
        {"master": {"agent": "claude", "session_id": "S1", "cwd": root}}, set())
    m.live_role_surfaces = lambda s: {"master": [{"surface": "surface:1", "pid": None, "exited": False,
                                                  "agent_alive": None, "seat": "occupied"}]}
    m._surface_shell_pids = lambda s: {"surface:1": 664}
    m._ps_table = lambda: state["table"]
    m.restore_supports_per_entry_cwd = lambda s=None: False
    m.master_seat_cwd = lambda s, entries=None: None
    m.seat_fresh_cwd = lambda role, c, mc, log_fn=None: c
    m.fresh_awaken = lambda *a, **k: "awaken-stub"
    m.spawn_production = lambda s, roles, include_master=False, cwd=None: (
        calls.__setitem__("restore", calls["restore"] + 1) or {"rc": 0, "out": "ok"})
    m.spawn_fresh_production = lambda s, role, agent, cwd=None: (
        calls.__setitem__("fresh", calls["fresh"] + 1) or {"rc": 0, "out": "launched"})
    m.stage_ready = lambda s, role, surf, stub: (True, "ready-stub")
    m.stage_observe_session = lambda s, surf, stub, role=None: ("S1", "topology re-pin(stub)")
    m.stage_reinject = lambda s, role, surf, stub: (True, "reinject-stub")
    m.stage_g2_ack = lambda s, role, surf, stub: (True, "g2-stub")
    m.SPAWN_SETTLE = 0.0
    m.SPAWN_BACKOFF = 0.0

    # S1 — 좌석 표시는 살아있고(occupied) 세션핀도 일치하지만 ps 로는 죽었다(run7)
    r1 = m.run_restore(sock, ticket="a3", stub=False, no_breaker=True, print_result=False)
    j1 = m.load_journal(sock, "a3")
    check("S1a 표시 occupied + ps 죽음 → 부활 대상 편입", r1.get("target_roles") == ["master"],
          r1.get("target_roles"), sink)
    check("S1b 세션핀 일치여도 VERIFIED 아님(unverified)",
          r1.get("phoenix_restore") != "VERIFIED" and (r1.get("per_role_outcome") or {}).get("master") == "unverified",
          (r1.get("phoenix_restore"), r1.get("per_role_outcome")), sink)
    check("S1c 저널에 force_fresh + verify 사유(ps 축)",
          (j1["roles"].get("master") or {}).get("force_fresh") is True
          and "ps 축" in ((j1["roles"].get("master") or {}).get("verify_reason") or ""),
          (j1["roles"].get("master") or {}).get("verify_reason"), sink)

    # S2 — 다음 사이클: resume 재시도 없이 fresh 재기동 · 이번엔 에이전트가 떠 있다
    restore_before = calls["restore"]
    # ★v115-restore(A4): 1사이클의 정착 판정이 agent_alive True 를 요구하므로(대역 = 항상 None) 1사이클 안에서
    #   이미 fresh 1회가 난다 — S2 는 「이번 사이클의」 증분으로 잰다.
    fresh_before = calls["fresh"]
    # 대상 산정은 이번 사이클도 죽은 좌석을 본다 — fresh 기동 순간에 표가 살아있음으로 바뀐다.
    state["table"] = T_DEAD
    _orig_fresh = m.spawn_fresh_production

    def _fresh_then_alive(s, role, agent, cwd=None):
        state["table"] = T_ALIVE
        return _orig_fresh(s, role, agent, cwd=cwd)
    m.spawn_fresh_production = _fresh_then_alive
    r2 = m.run_restore(sock, ticket="a3", stub=False, no_breaker=True, print_result=False)
    check("S2a force_fresh → cys restore(resume) 재시도 0 · launch-agent fresh 1",
          calls["restore"] == restore_before and calls["fresh"] - fresh_before == 1,
          (calls, restore_before), sink)
    check("S2b fresh 기동 뒤 ps 살아있음 → fresh 확정(VERIFIED_FRESH)",
          r2.get("phoenix_restore") == "VERIFIED_FRESH" and (r2.get("per_role_outcome") or {}).get("master") == "fresh",
          (r2.get("phoenix_restore"), r2.get("per_role_outcome")), sink)

    # S3 — 대조군: ps 살아있음 → 생존 · NOOP
    sockdir3 = os.path.join(root, "sock3")
    os.makedirs(os.path.join(sockdir3, "phoenix"), exist_ok=True)
    state["table"] = T_ALIVE
    r3 = m.run_restore(os.path.join(sockdir3, "cys.sock"), ticket="a3c", stub=False, no_breaker=True,
                       print_result=False)
    check("S3 대조군 ps 살아있음 → NOOP(오강등 0)", r3.get("phoenix_restore") == "NOOP",
          r3.get("phoenix_restore"), sink)


root = tempfile.mkdtemp(prefix="phoenix-a3-")
try:
    live = load(PH, "_ph_a3_live")
    unit_axes(live)
    scenario_axes(live, os.path.join(root, "live"))

    src = io.open(PH, encoding="utf-8").read()
    mutants = [
        ("M1 verify ps 축 제거", '        if not stub and outcome in ("verified", "fresh"):\n',
         "        if False:\n"),
        ("M2 대상 산정 ps 축 제거", '            if _ps_dead(role, s.get("surface")):\n',
         "            if False:\n"),
        ("M3 순수 판정 dead→alive", '        stack.extend(children.get(pid, []))\n    return "dead"\n',
         '        stack.extend(children.get(pid, []))\n    return "alive"\n'),
    ]
    for i, (name, old, new) in enumerate(mutants):
        n = src.count(old)
        check("%s — 앵커 정확히 1곳(변이 적용 선-assert)" % name, n == 1, n)
        if n != 1:
            continue
        mp = os.path.join(root, "ph_mut%d.py" % i)
        io.open(mp, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
        check("%s — 변이 적용 확인" % name, old not in io.open(mp, encoding="utf-8").read())
        sink = []
        try:
            mm = load(mp, "_ph_a3_mut%d" % i)
            unit_axes(mm, sink)
            scenario_axes(mm, os.path.join(root, "mut%d" % i), sink)
        except Exception as e:  # noqa: BLE001 — 변이가 크래시를 내도 적색(= 잡힘)
            sink.append("크래시 %s: %s" % (type(e).__name__, e))
        check("%s → 적색(KILLED) — %s" % (name, sink[:3]), bool(sink), sink)
finally:
    shutil.rmtree(root, ignore_errors=True)

if fails:
    print("\n%d FAIL: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("\nALL PASS")
print("PHOENIX-A3-PS-AXIS-OK")
sys.exit(0)
