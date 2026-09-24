#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_v116_phoenix_midrun_tomb.py — 진행 중 복원이 새 묘비를 존중한다 (TICKET=v116-pack · R-B1 실사례 2026-09-24).

실측 계기(우리 맥 1.0.2→1.1.5 제자리 교체 09:27): phoenix 자동 복원 도중 master 가 09:31:23 close-surface(OwnerClose
묘비)로 닫은 worker-18·15 를, 진행 중이던 같은 런이 resume 재시도 소진 뒤 fresh 강등(launch-agent)으로 09:33 에 다시
세웠고 데몬은 역할 등록 순간 묘비를 지웠다. 수리 = 스폰 직전 묘비 재조회 3곳(resume 회차마다 · 빈 좌석 재사용 직전 ·
fresh 강등 launch-agent 직전) · 걸린 역할은 저널 tombstoned_mid_run + 완결성·판정 집계 제외.

하니스 = 가짜 spawn 주입(test_phoenix_v115_spawn_settle 형 · 데몬 0 · 실제 운영 경로 = cys restore / launch-agent 대역).
  C0 대조군: 묘비 없음 · 독약 세션 master → 종전대로 부활(restore 4 · fresh 1 · COMPLETE)
  T1 resume 1회차 중 묘비 → restore 1 · fresh 0 · 묘비 유지 · INCOMPLETE 아님
  T2 마지막 resume 회차 중 묘비 + 빈 좌석 있음 → 빈 좌석 재사용 0 · fresh 0 · 묘비 유지
  T3 두 역할 fresh 강등 중 앞 역할 launch 도중 뒤 역할 묘비 → fresh 1(앞만) · 뒤 역할 묘비 유지
  M  뮤턴트 4(재조회 3곳 각각 제거 · 집계 제외 제거 · 변이 적용 선-assert) → 각각 해당 축 적색

실행: python3 cysjavis-pack/bin/tests/test_v116_phoenix_midrun_tomb.py → 종료 토큰 PHOENIX-V116-MIDRUN-TOMB-OK
"""
import importlib.util
import os
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


def load_src(src, name, d):
    path = os.path.join(d, name + ".py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scenario(src, tmp, tag, roles, tomb_on_restore=None, tomb_on_fresh=None, empty_seat=False):
    """roles 전원이 독약 세션(resume 실패)인 1사이클.
    tomb_on_restore = (n, role): n번째 cys restore 호출 도중 role 묘비 생성(사람이 닫음).
    tomb_on_fresh = (launched_role, role): launched_role 의 launch-agent 도중 role 묘비 생성.
    fresh(launch-agent) 대역은 데몬처럼 역할 등록 순간 그 역할 묘비를 지운다(state.rs register 재현)."""
    d = tempfile.mkdtemp(prefix=tag + "-", dir=tmp)
    m = load_src(src, "ph_" + tag, d)
    sockdir = os.path.join(d, "sock")
    os.makedirs(os.path.join(sockdir, "phoenix"), exist_ok=True)
    sock = os.path.join(sockdir, "cys.sock")
    st = {"live": {}, "tomb": set()}
    calls = {"restore": 0, "in_seat": 0, "fresh": []}
    m.CYS = os.path.join(d, "nonexistent-cys")
    m.log = lambda msg: None
    m._emit_evt = lambda *a, **k: None
    m._acquire_restore_lease = lambda s: (True, None)
    m.get_boot_epoch = lambda s: "EPOCH-V116"
    m._recover_retention_file = lambda s, p, k: {"status": "missing"}
    m._recovered_provenance = lambda p: None
    m.c6_reap_stale_surfaces = lambda s: {}
    m.observe_and_persist_roster = lambda s, rebase=False: (
        {r: {"agent": "claude", "session_id": "S-" + r, "cwd": d} for r in roles}, set())
    m.read_topology = lambda s: {"schema_version": 1, "tombstones": sorted(st["tomb"]), "entries": []}
    m.live_role_surfaces = lambda s: {k: [dict(x) for x in v] for k, v in st["live"].items()}
    m._surface_shell_pids = lambda s: {}
    m._ps_table = lambda: None
    m.restore_supports_per_entry_cwd = lambda s=None: False
    m.master_seat_cwd = lambda s, entries=None: None
    m.seat_fresh_cwd = lambda role, c, mc, log_fn=None: c
    m.fresh_awaken = lambda *a, **k: "awaken-stub"

    def _restore(s, need, include_master=False, cwd=None):
        calls["restore"] += 1
        if tomb_on_restore and calls["restore"] == tomb_on_restore[0]:
            st["tomb"].add(tomb_on_restore[1])
        for i, r in enumerate(need):
            if r in st["tomb"]:
                continue  # 실 cys restore 는 매 호출 묘비를 건너뛴다(cys.rs run_restore)
            seat = {"surface": "surface:%d" % (10 + i), "pid": None, "exited": False,
                    "agent_alive": True, "seat": "empty" if empty_seat else "occupied"}
            st["live"][r] = [seat]
        out = "".join("· %s: 기동 실패 — 나머지 역할 계속 진행\n" % r for r in need if not empty_seat)
        return {"rc": 1 if out else 0, "out": out}
    m.spawn_production = _restore

    def _in_seat(s, include_master=False, cwd=None):
        calls["in_seat"] += 1
        return {"rc": 1, "out": "stub"}
    m.spawn_in_seat_production = _in_seat

    def _fresh(s, role, agent, cwd=None):
        calls["fresh"].append(role)
        if tomb_on_fresh and tomb_on_fresh[0] == role:
            st["tomb"].add(tomb_on_fresh[1])
        st["tomb"].discard(role)  # 데몬: 역할 등록 = 부활 의도 → 묘비 해제
        st["live"][role] = [{"surface": "surface:9%d" % len(calls["fresh"]), "pid": None, "exited": False,
                             "agent_alive": True, "seat": "occupied"}]
        return {"rc": 0, "out": "launched"}
    m.spawn_fresh_production = _fresh
    m.cys = lambda *a, **k: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    m.stage_ready = lambda s, role, surf, stub: (True, "ready-stub")
    m.stage_observe_session = lambda s, surf, stub, role=None: ("S-NEW", "stub")
    m.stage_reinject = lambda s, role, surf, stub: (True, "stub")
    m.stage_g2_ack = lambda s, role, surf, stub: (True, "stub")
    m.ack_ping_gate = lambda s, surf: (True, "stub", {})
    m.surface_agent_verdict = lambda s, surf, agent: "alive"
    m.SPAWN_SETTLE = 0.0
    m.SPAWN_BACKOFF = 0.0
    res = m.run_restore(sock, ticket="v116", stub=False, no_breaker=True, print_result=False, include_master=True)
    return calls, st["tomb"], res


def axes(src, tmp, tag, sink=None):
    c, tomb, res = scenario(src, tmp, tag + "c0", ["master"])
    check("C0 대조군: 묘비 없으면 종전대로 부활(restore 4 · fresh 1 · COMPLETE)",
          c["restore"] == 4 and c["fresh"] == ["master"] and res.get("completeness") == "COMPLETE",
          (c, res.get("completeness")), sink)

    c, tomb, res = scenario(src, tmp, tag + "t1", ["master"], tomb_on_restore=(1, "master"))
    check("T1 resume 1회차 중 묘비 → restore 1 · fresh 0 · 묘비 유지",
          c["restore"] == 1 and c["fresh"] == [] and "master" in tomb, (c, sorted(tomb)), sink)
    check("T1 집계: INCOMPLETE 아님 · tombstoned_mid_run_roles=[master]",
          res.get("completeness") != "INCOMPLETE" and res.get("tombstoned_mid_run_roles") == ["master"],
          (res.get("completeness"), res.get("tombstoned_mid_run_roles")), sink)

    c, tomb, res = scenario(src, tmp, tag + "t2", ["master"], tomb_on_restore=(4, "master"), empty_seat=True)
    check("T2 마지막 회차 중 묘비 + 빈 좌석 → 빈 좌석 재사용 0 · fresh 0 · 묘비 유지",
          c["restore"] == 4 and c["in_seat"] == 0 and c["fresh"] == [] and "master" in tomb,
          (c, sorted(tomb)), sink)

    c, tomb, res = scenario(src, tmp, tag + "t3", ["worker-a", "worker-b"],
                            tomb_on_fresh=("worker-a", "worker-b"))
    check("T3 앞 역할 launch 도중 뒤 역할 묘비 → fresh 1(앞만) · 뒤 역할 묘비 유지",
          c["fresh"] == ["worker-a"] and "worker-b" in tomb and "worker-a" not in tomb,
          (c, sorted(tomb)), sink)


def main():
    sys.path.insert(0, os.path.dirname(PH))
    with open(PH, encoding="utf-8") as f:
        src = f.read()
    tmp = tempfile.mkdtemp(prefix="ph-v116-midrun-")
    axes(src, tmp, "base")
    mutants = [
        ("M1 resume 회차 재조회 제거",
         '        need = _drop_tombstoned(need, "resume %d회차" % attempt)\n', "", "T1 resume"),
        ("M2 빈 좌석 재사용 직전 재조회 제거",
         '                need = _drop_tombstoned(need, "빈 좌석 재사용")\n', "", "T2"),
        ("M3 fresh 강등 직전 재조회 제거",
         '            if not _drop_tombstoned([role], "fresh 강등"):\n                continue\n', "", "T3"),
        ("M4 완결성 집계 제외 제거",
         '        target_roles = [r for r in target_roles if r not in _mid_tomb]\n', "", "T1 집계"),
    ]
    for i, (name, a, b, axis) in enumerate(mutants):
        n = src.count(a)
        check(name + " 변이 적용 선-assert(정확 1곳)", n == 1, "count=%d" % n)
        if n != 1:
            continue
        sink = []
        axes(src.replace(a, b), tmp, "m%d" % i, sink=sink)
        check(name + " → KILLED(%s 축 적색)" % axis, any(x.startswith(axis) for x in sink), "적색=%s" % sink)
    if fails:
        print("FAIL 합계 %d: %s" % (len(fails), fails))
        sys.exit(1)
    print("PHOENIX-V116-MIDRUN-TOMB-OK")


if __name__ == "__main__":
    main()
