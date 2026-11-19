#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_seatkeep_t1_lease_hold.py — `cys restore` 가 대화 임대로 띄우지 않은 역할(rc 92 작성자 살아 있음 ·
rc 93 생존 판정 불가)을 phoenix 가 재시도·독약 fresh(새 대화)로 띄우지 않는다(TICKET=cysr-seatkeep-t1 · master#78599b55 조건 ①).

결함(수리 전): phoenix 는 `cys restore` rc 를 읽지 않고 「역할 좌석이 안 섰다」만 보아, 재시도 3회 뒤 Phase 11 독약 fresh
(`cys launch-agent` 새 대화)로 그 역할을 띄웠다 = 살아 있는 작성자 옆에 같은 역할 새 대화.

  P  대조군: 임대 줄 없는 실패 = 독약 fresh 강등 유지(restore 4 · fresh 1)
  L1 「작성자 살아 있음」 줄 → restore 1(재시도 0) · fresh 0 · 저널 lease_held(writer_live) · spawn 미완
  L2 「생존 판정 불가」 줄 → fresh 0 · 사유 liveness_unknown
  M  뮤턴트 1(임대 줄 읽기 제거 · 변이 적용 선-assert) → L1 적색

실행: python3 cysjavis-pack/bin/tests/test_phoenix_seatkeep_t1_lease_hold.py → 종료 토큰 PHOENIX-SEATKEEP-T1-LEASE-HOLD-OK
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


FAIL_OUT = "· master: claude 재기동…\n· master: 기동 실패 — 나머지 역할 계속 진행\nrestore 완료: 재기동 0 · 실패 1"
LIVE_OUT = ("· master: 대화 5e55aaaa — pid 12(출생 1.000002) 가 이 대화를 쓰는 중 — 띄우지 않음(같은 대화 작성자 둘 차단 · 새 대화로도 띄우지 않음)\n"
            "restore 완료: 재기동 0 · 실패 0 · 관문 보류 0 · journal refused 0 · outcome unknown 0 · 현황 `cys status` · 대화 작성자 살아 있음 1 · 생존 판정 불가 0")
UNK_OUT = ("· master: 대화 5e55aaaa 작성자 생존 판정 불가(probe:proc_pidinfo:1:12) — 띄우지 않음 · 확인: `ps -p 12 -o pid,lstart,command`\n"
           "restore 완료: 재기동 0 · 실패 0 · 관문 보류 0 · journal refused 0 · outcome unknown 0 · 현황 `cys status` · 대화 작성자 살아 있음 0 · 생존 판정 불가 1")


def scenario(src, tmp, tag, extra_entry, out):
    """죽은 master 1명 부활 1사이클 — 반환 = (restore 호출 수, fresh 호출 수, 마지막 저널)."""
    d = tempfile.mkdtemp(prefix=tag + "-", dir=tmp)
    m = load_src(src, "ph_" + tag, d)
    sockdir = os.path.join(d, "sock")
    os.makedirs(os.path.join(sockdir, "phoenix"), exist_ok=True)
    sock = os.path.join(sockdir, "cys.sock")
    calls = {"restore": 0, "fresh": 0}
    st = {"live": {}, "journal": None}
    m.CYS = os.path.join(d, "nonexistent-cys")
    m.log = lambda msg: None
    m._emit_evt = lambda *a, **k: None
    m._acquire_restore_lease = lambda s: (True, None)
    m.get_boot_epoch = lambda s: "EPOCH-SKT1"
    m._recover_retention_file = lambda s, p, k: {"status": "missing"}
    m._recovered_provenance = lambda p: None
    m.c6_reap_stale_surfaces = lambda s: {}
    entry = dict({"agent": "claude", "session_id": "S1", "cwd": d}, **extra_entry)
    m.observe_and_persist_roster = lambda s, rebase=False: ({"master": dict(entry)}, set())
    m.live_role_surfaces = lambda s: {k: [dict(x) for x in v] for k, v in st["live"].items()}
    m._surface_shell_pids = lambda s: {}
    m._ps_table = lambda: None
    m.restore_supports_per_entry_cwd = lambda s=None: False
    m.master_seat_cwd = lambda s, entries=None: None
    m.seat_fresh_cwd = lambda role, c, mc, log_fn=None: c
    m.fresh_awaken = lambda *a, **k: "awaken-stub"
    m.fresh_expected = lambda e: (False, "")
    m.resume_arg_effect = lambda agent: ("effective", "")

    def _restore(s, roles, include_master=False, cwd=None, **_kw):
        calls["restore"] += 1          # Rust 가 그 역할을 띄우지 않았다(실패 또는 기동 중단) — 좌석 0
        return {"rc": 1, "out": out}
    m.spawn_production = _restore
    m.spawn_in_seat_production = lambda s, include_master=False, cwd=None, units=None: {"rc": 1, "out": "stub"}

    def _fresh(s, role, agent, cwd=None):
        calls["fresh"] += 1
        st["live"] = {"master": [{"surface": "surface:99", "pid": None, "exited": False,
                                  "agent_alive": True, "seat": "occupied"}]}
        return {"rc": 0, "out": "launched"}
    m.spawn_fresh_production = _fresh
    _save = m.save_journal

    def _cap(s, t, j):
        st["journal"] = j
        _save(s, t, j)
    m.save_journal = _cap
    m.stage_ready = lambda s, role, surf, stub: (True, "ready-stub")
    m.stage_observe_session = lambda s, surf, stub, role=None: ("S1", "stub")
    m.stage_reinject = lambda s, role, surf, stub: (True, "stub")
    m.stage_g2_ack = lambda s, role, surf, stub: (True, "stub")
    m.SPAWN_SETTLE = 0.0
    m.SPAWN_BACKOFF = 0.0
    m.run_restore(sock, ticket="skt1", stub=False, no_breaker=True, print_result=False, include_master=True)
    return calls["restore"], calls["fresh"], st["journal"]


def truncation_axis(src, tmp, sink=None):
    """T 실제 spawn_production(절단 800자) 경로 — 앞에 긴 출력 + 뒤쪽 역할 둘의 거절 줄 → lease_refused 에 둘 다."""
    d = tempfile.mkdtemp(prefix="trunc-", dir=tmp)
    m = load_src(src, "ph_trunc", d)

    class R:
        returncode = 92
        stdout = ("· filler: " + "x" * 1200 + "\n"
                  "· w1: 대화 aaaa1111 — pid 1(출생 1.000000) 가 이 대화를 쓰는 중 — 띄우지 않음(같은 대화 작성자 둘 차단 · 새 대화로도 띄우지 않음)\n"
                  "· w2: 대화 bbbb2222 작성자 생존 판정 불가(scan:argv:9) — 띄우지 않음 · 확인: x\n")
        stderr = ""
        stderr_raw = ""
        stalled = False
    m.cys = lambda *a, **k: R()
    m.log_restore_output = lambda r: None
    m._spawn_heartbeat = lambda *a, **k: (lambda: None)
    m.log = lambda msg: None
    res = m.spawn_production("/nonexistent.sock", ["w1", "w2"], units=2)
    roles = sorted(r for r, _ in res.get("lease_refused") or [])
    check("T 800자 절단 뒤쪽 거절 줄도 추출(w1 · w2)", roles == ["w1", "w2"] and len(res["out"]) <= 800,
          (roles, len(res["out"])), sink)


def inner_refusal_axis(src, tmp, sink=None):
    """R5(codex r4 #3) `cys restore` fresh 안쪽 거절(92·93)의 표준 줄 — 문자열 정본 = session_lease_cli_tests.rs
    restore_inner_refusals_print_the_standard_line(같은 글자) → phoenix 판독기가 두 역할을 사유와 함께 읽는다."""
    d = tempfile.mkdtemp(prefix="inner-", dir=tmp)
    m = load_src(src, "ph_inner", d)
    # ★skt1(codex r5c #3): 대화 표기 = 전체 id(앱이 그 값으로 대화 임대를 찾는다).
    out = ("· w1: 대화 5e55aaaa-0000-4000-8000-000000000001 작성자 생존 판정 불가(seat-unverified) — 띄우지 않음 · 확인: `cys read-screen --surface surface:7` 로 그 좌석이 이 대화를 잇는지 보세요\n"
           "· w2: 대화 5e55aaaa-0000-4000-8000-000000000001 — 그 대화를 잇는 좌석이 이미 있음 — 띄우지 않음 · 확인: 바로 위 [launch-agent] 줄의 좌석을 `cys read-screen` 으로 보세요\n")
    got = m._lease_refusals(out)
    check("R5 안쪽 거절 줄(93·92)을 phoenix 가 읽음",
          [r for r, _ in got] == ["w1", "w2"] and got[0][1].startswith("liveness_unknown:5e55aaaa-0000-4000-8000-000000000001") and got[1][1].startswith("writer_live:5e55aaaa-0000-4000-8000-000000000001"), got, sink)


def held_events(j):
    return [e for e in (j or {}).get("events", []) if e.get("role") == "master" and e.get("status") == "lease_held"]


def axes(src, tmp, tag, sink=None):
    r, f, _j = scenario(src, tmp, tag + "p", {}, FAIL_OUT)
    check("P 대조군: 임대 줄 없는 실패 = 독약 fresh 강등 유지(restore 4 · fresh 1)", (r, f) == (4, 1), (r, f), sink)
    r, f, j = scenario(src, tmp, tag + "l1", {}, LIVE_OUT)
    ev = held_events(j)
    spawn = ((j or {}).get("roles", {}).get("master", {}).get("stages", {}).get("spawn") or {})
    check("L1 작성자 살아 있음 = 재시도 0 · fresh 0(restore 1 · fresh 0)", (r, f) == (1, 0), (r, f), sink)
    check("L1 저널 lease_held · 사유 writer_live", len(ev) >= 1 and "writer_live" in ev[0].get("msg", ""), ev, sink)
    check("L1 spawn 단계 미완(성공으로 세지 않음)",
          spawn.get("done") is False and "복원 보류" in spawn.get("evidence", ""), spawn, sink)
    r, f, j = scenario(src, tmp, tag + "l2", {}, UNK_OUT)
    ev = held_events(j)
    check("L2 생존 판정 불가 = fresh 0 · 사유 liveness_unknown",
          f == 0 and len(ev) >= 1 and "liveness_unknown" in ev[0].get("msg", ""), (f, ev), sink)


def main():
    sys.path.insert(0, os.path.dirname(PH))
    with open(PH, encoding="utf-8") as f:
        src = f.read()
    tmp = tempfile.mkdtemp(prefix="ph-skt1-lease-")
    axes(src, tmp, "base")
    truncation_axis(src, tmp)
    inner_refusal_axis(src, tmp)
    a = "            for _r, _why in (res.get(\"lease_refused\") if \"lease_refused\" in res else _lease_refusals(res.get(\"out\") or \"\")):\n"
    n = src.count(a)
    check("M1 임대 줄 읽기 제거 변이 적용 선-assert(정확 1곳)", n == 1, "count=%d" % n)
    if n == 1:
        sink = []
        axes(src.replace(a, "            for _r, _why in []:\n"), tmp, "m1", sink=sink)
        check("M1 임대 줄 읽기 제거 → KILLED(L1 축 적색)", any(x.startswith("L1") for x in sink), "적색=%s" % sink)
    if fails:
        print("FAIL 합계 %d: %s" % (len(fails), fails))
        sys.exit(1)
    print("PHOENIX-SEATKEEP-T1-LEASE-HOLD-OK")


if __name__ == "__main__":
    main()
