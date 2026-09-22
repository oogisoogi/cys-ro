#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_v115_spawn_settle.py — 스폰 정착 판정이 가짜 부활을 세지 않는다 (TICKET=v115-restore A4 · 905 A2 흡수).

실측 계기(904 VM ↻-B1 · A4-FINDINGS.md): `cys restore` 4회가 전부 `· master: 기동 실패` 였는데 phoenix 가 정착 확인
순간 **다른 복원 경로가 만든, 에이전트 안 선 좌석**(surface:15)을 부활 성공으로 기록 → fresh 강등 누락 → INCOMPLETE
→ 데몬 60초 대기 → 2차 → master 3분 공백. 판정 = run_restore 스폰 재시도 루프의 `_revived_seat` + 이번 회차 실패 줄.

  P  대조군: 좌석 occupied · agent_alive True · 출력 정상 → 1회차 성공(restore 1 · fresh 0)
  E1 빈 셸 좌석(seat=empty · agent_alive True)      → 부활 아님(restore 4 = 재시도 소진)  ← 905 기대 동형
  E2 agent_alive None(에이전트 안 섬 · occupied)      → 부활 아님(restore 4)
  E3 출력에 `· master: 기동 실패` (좌석은 멀쩡해 보임) → 부활 아님(restore 4)
  M  뮤턴트 3(조건 각각 제거 · 변이 적용 선-assert) → 각각 해당 축 적색

실행: python3 cysjavis-pack/bin/tests/test_phoenix_v115_spawn_settle.py → 종료 토큰 PHOENIX-V115-SPAWN-SETTLE-OK
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


def scenario(src, tmp, tag, seat_after, out_after):
    """죽은 master 1명을 부활시키는 1사이클. 반환 = (restore 호출 수, fresh 호출 수)."""
    d = tempfile.mkdtemp(prefix=tag + "-", dir=tmp)
    m = load_src(src, "ph_" + tag, d)
    sockdir = os.path.join(d, "sock")
    os.makedirs(os.path.join(sockdir, "phoenix"), exist_ok=True)
    sock = os.path.join(sockdir, "cys.sock")
    st = {"live": {}}
    calls = {"restore": 0, "fresh": 0}
    m.CYS = os.path.join(d, "nonexistent-cys")
    m.log = lambda msg: None
    m._emit_evt = lambda *a, **k: None
    m._acquire_restore_lease = lambda s: (True, None)
    m.get_boot_epoch = lambda s: "EPOCH-V115"
    m._recover_retention_file = lambda s, p, k: {"status": "missing"}
    m._recovered_provenance = lambda p: None
    m.c6_reap_stale_surfaces = lambda s: {}
    m.observe_and_persist_roster = lambda s, rebase=False: (
        {"master": {"agent": "claude", "session_id": "S1", "cwd": d}}, set())
    m.live_role_surfaces = lambda s: {k: [dict(x) for x in v] for k, v in st["live"].items()}
    m._surface_shell_pids = lambda s: {}
    m._ps_table = lambda: None
    m.restore_supports_per_entry_cwd = lambda s=None: False
    m.master_seat_cwd = lambda s, entries=None: None
    m.seat_fresh_cwd = lambda role, c, mc, log_fn=None: c
    m.fresh_awaken = lambda *a, **k: "awaken-stub"

    def _restore(s, roles, include_master=False, cwd=None):
        calls["restore"] += 1
        st["live"] = {"master": [dict(seat_after)]}
        return {"rc": 0 if "기동 실패" not in out_after else 1, "out": out_after}
    m.spawn_production = _restore
    m.spawn_in_seat_production = lambda s, include_master=False, cwd=None: {"rc": 1, "out": "stub"}

    def _fresh(s, role, agent, cwd=None):
        calls["fresh"] += 1
        st["live"] = {"master": [{"surface": "surface:99", "pid": None, "exited": False,
                                  "agent_alive": True, "seat": "occupied"}]}
        return {"rc": 0, "out": "launched"}
    m.spawn_fresh_production = _fresh
    m.stage_ready = lambda s, role, surf, stub: (True, "ready-stub")
    m.stage_observe_session = lambda s, surf, stub, role=None: ("S1", "stub")
    m.stage_reinject = lambda s, role, surf, stub: (True, "stub")
    m.stage_g2_ack = lambda s, role, surf, stub: (True, "stub")
    m.SPAWN_SETTLE = 0.0
    m.SPAWN_BACKOFF = 0.0
    m.run_restore(sock, ticket="v115", stub=False, no_breaker=True, print_result=False, include_master=True)
    return calls["restore"], calls["fresh"]


OK_OUT = "· master: claude 재기동…\nsurface:15\nrestore 완료: 재기동 1 · 실패 0 · 관문 보류 0"
FAIL_OUT = "· master: claude 재기동…\nsurface:15\n· master: 기동 실패 — 나머지 역할 계속 진행\nrestore 완료: 재기동 0 · 실패 1"
GOOD = {"surface": "surface:15", "pid": None, "exited": False, "agent_alive": True, "seat": "occupied"}


def axes(src, tmp, tag, sink=None):
    r = scenario(src, tmp, tag + "p", GOOD, OK_OUT)
    check("P 대조군: 에이전트 선 좌석 = 1회차 부활(restore 1 · fresh 0)", r == (1, 0), r, sink)
    r = scenario(src, tmp, tag + "e1", dict(GOOD, seat="empty"), OK_OUT)
    check("E1 빈 셸 좌석은 부활 아님(restore 4 · fresh 1)", r == (4, 1), r, sink)
    r = scenario(src, tmp, tag + "e2", dict(GOOD, agent_alive=None), OK_OUT)
    check("E2 agent_alive None 좌석은 부활 아님(restore 4 · fresh 1)", r == (4, 1), r, sink)
    r = scenario(src, tmp, tag + "e3", GOOD, FAIL_OUT)
    check("E3 이번 회차 「master: 기동 실패」 = 부활 아님(restore 4 · fresh 1)", r == (4, 1), r, sink)


def main():
    sys.path.insert(0, os.path.dirname(PH))
    with open(PH, encoding="utf-8") as f:
        src = f.read()
    tmp = tempfile.mkdtemp(prefix="ph-v115-settle-")
    axes(src, tmp, "base")
    mutants = [
        ("M1 기동 실패 줄 조건 제거",
         '                alive = [] if role in _failed_now else [s for s in live2.get(role, []) if _revived_seat(s)]',
         '                alive = [s for s in live2.get(role, []) if _revived_seat(s)]', "E3"),
        ("M2 agent_alive 조건 제거",
         'return (not s["exited"]) and s.get("agent_alive") is True and s.get("seat") != "empty"',
         'return (not s["exited"]) and s.get("seat") != "empty"', "E2"),
        ("M3 빈 좌석 조건 제거",
         'return (not s["exited"]) and s.get("agent_alive") is True and s.get("seat") != "empty"',
         'return (not s["exited"]) and s.get("agent_alive") is True', "E1"),
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
    print("PHOENIX-V115-SPAWN-SETTLE-OK")


if __name__ == "__main__":
    main()
