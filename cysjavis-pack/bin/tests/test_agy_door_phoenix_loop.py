#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_agy_door_phoenix_loop.py — agy 좌석 문 × phoenix 복원 루프(TICKET=cysr-agy-policy-exposure · codex 2R major).

상황: 오라클(`cys agent-detect --json`)이 실패해 phoenix 가 reviewer-gemini 를 미리 가르지 못했다. 그러면 `cys restore` 가
그 역할을 「· reviewer-gemini: 건너뜀(agy_consumer_policy)」로 건너뛴다(Rust agy_door::restore_skip_line_with). phoenix 는
그 줄을 **첫 restore 결과에서 곧바로** 소비해야 한다 — 재시도·fresh 강등·재스폰 계수·차단기에 넣지 않는다.

하니스 = 가짜 spawn 주입(test_v116_phoenix_midrun_tomb 형 · 데몬 0).
  P1 fresh 강등 켬: restore 1회 · fresh 0 · agy_policy_skipped_roles=[reviewer-gemini] · 실패·미완 아님 · 재스폰 계수 0
  P2 fresh 강등 끔(PHOENIX_POISON_FRESH_FALLBACK=0): 같은 결과(종전엔 FAILED/INCOMPLETE)
  P3 차단기: 대상이 정책 건너뜀뿐인 런을 연달아 돌려도 BREAKER_OPEN 이 아니다(창 리셋)
  C0 대조군: worker(claude) 는 그대로 부활 · 건너뜀 줄 없는 역할은 종전대로 재시도
  M  뮤턴트: resume 루프의 소비 줄 제거 → P1 적색(restore 4회 재시도)

실행: python3 cysjavis-pack/bin/tests/test_agy_door_phoenix_loop.py → 종료 토큰 AGY-DOOR-PHOENIX-LOOP-OK
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.normpath(os.path.join(HERE, "..", "javis_phoenix.py"))
SKIP = "· reviewer-gemini: 건너뜀(agy_consumer_policy) — 구글 개인 요금제 약관 때문에 cysr 은 Antigravity(agy) 좌석을 다시 띄우지 않습니다.\n"
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


def scenario(src, tmp, tag, roles, fresh_fallback=True, runs=1, no_breaker=True, skip_line=True, breaker_seed=0):
    d = tempfile.mkdtemp(prefix=tag + "-", dir=tmp)
    m = load_src(src, "ph_" + tag, d)
    sockdir = os.path.join(d, "sock")
    os.makedirs(os.path.join(sockdir, "phoenix"), exist_ok=True)
    sock = os.path.join(sockdir, "cys.sock")
    st = {"live": {}}
    calls = {"restore": 0, "fresh": []}
    agents = {r: ("gemini" if r == "reviewer-gemini" else "claude") for r in roles}
    m.CYS = os.path.join(d, "nonexistent-cys")
    m.POISON_FRESH_FALLBACK = fresh_fallback
    m.log = lambda msg: None
    m._emit_evt = lambda *a, **k: None
    m._acquire_restore_lease = lambda s: (True, None)
    m.get_boot_epoch = lambda s: "EPOCH-AGY"
    m._recover_retention_file = lambda s, p, k: {"status": "missing"}
    m._recovered_provenance = lambda p: None
    m.c6_reap_stale_surfaces = lambda s: {}
    m.observe_and_persist_roster = lambda s, rebase=False: (
        {r: {"agent": agents[r], "session_id": "S-" + r, "cwd": d} for r in roles}, set())
    m.read_topology = lambda s: {"schema_version": 1, "tombstones": [], "entries": []}
    m.live_role_surfaces = lambda s: {k: [dict(x) for x in v] for k, v in st["live"].items()}
    m._surface_shell_pids = lambda s: {}
    m._ps_table = lambda: None
    m.restore_supports_per_entry_cwd = lambda s=None: False
    m.master_seat_cwd = lambda s, entries=None: None
    m.seat_fresh_cwd = lambda role, c, mc, log_fn=None: c
    m.fresh_awaken = lambda *a, **k: "awaken-stub"
    m.fresh_expected = lambda e: (False, "")
    m.resume_arg_effect = lambda agent: ("effective", "")

    def _restore(s, need, include_master=False, cwd=None, **_kw):
        calls["restore"] += 1
        out = ""
        for i, r in enumerate(need):
            if agents[r] == "gemini":
                if skip_line:
                    out += SKIP      # 실 cys restore: 문 닫힘 → 건너뜀 줄 · 좌석 안 만듦(skip_line=False = 건너뜀 줄 없는 구 cys)
                continue
            st["live"][r] = [{"surface": "surface:%d" % (10 + i), "pid": None, "exited": False,
                              "agent_alive": True, "seat": "occupied"}]
        return {"rc": 0, "out": out}
    m.spawn_production = _restore
    m.spawn_in_seat_production = lambda s, include_master=False, cwd=None, units=None: {"rc": 1, "out": "stub"}

    def _fresh(s, role, agent, cwd=None):
        calls["fresh"].append(role)
        if agent == "gemini":
            return {"rc": m.AGY_POLICY_RC, "out": "agy_consumer_policy"}   # 실 launch-agent: 76
        st["live"][role] = [{"surface": "surface:9%d" % len(calls["fresh"]), "pid": None, "exited": False,
                             "agent_alive": True, "seat": "occupied"}]
        return {"rc": 0, "out": "launched"}
    m.spawn_fresh_production = _fresh
    # 오라클 실패: agent-detect 가 비0 → agy_door_split 이 가르지 못한다(이 시험의 전제)
    m.cys = lambda *a, **k: type("R", (), {"returncode": 1, "stdout": "", "stderr": "detect failed"})()
    m.stage_ready = lambda s, role, surf, stub: (True, "ready-stub")
    m.stage_observe_session = lambda s, surf, stub, role=None: ("S-%s" % role, "stub")   # 세션핀 재개 성공(이 축과 무관한 verify 를 통과시킨다)
    m.stage_reinject = lambda s, role, surf, stub: (True, "stub")
    m.stage_g2_ack = lambda s, role, surf, stub: (True, "stub")
    m.ack_ping_gate = lambda s, surf: (True, "stub", {})
    m.surface_agent_verdict = lambda s, surf, agent: "alive"
    m.SPAWN_SETTLE = 0.0
    m.SPAWN_BACKOFF = 0.0
    if breaker_seed:
        import time as _t
        with open(m.breaker_file(sock), "w") as f:
            json.dump({"attempts": [_t.time() - 5 * k for k in range(breaker_seed)]}, f)
    res = None
    for _ in range(runs):
        res = m.run_restore(sock, ticket="agy", stub=False, no_breaker=no_breaker, print_result=False,
                            include_master=True)
    counts = m.load_respawn_counts(sock, "EPOCH-AGY")
    try:
        with open(m.breaker_file(sock)) as f:
            counts["__breaker__"] = len(json.load(f).get("attempts", []))
    except (OSError, ValueError):
        counts["__breaker__"] = 0
    return calls, res, counts


def axes(src, tmp, tag, sink=None):
    for label, ff in (("P1 fresh 강등 켬", True), ("P2 fresh 강등 끔", False)):
        c, res, counts = scenario(src, tmp, tag + label[:2], ["reviewer-gemini", "worker"], fresh_fallback=ff)
        check("%s: restore 1회 · fresh 0(재시도·강등 없음)" % label,
              c["restore"] == 1 and c["fresh"] == [], c, sink)
        check("%s: agy_policy_skipped_roles=[reviewer-gemini] · 미완·빈 좌석 아님" % label,
              res.get("agy_policy_skipped_roles") == ["reviewer-gemini"]
              and "reviewer-gemini" not in res.get("incomplete_roles", [])
              and "reviewer-gemini" not in res.get("manual_seats", []),
              {k: res.get(k) for k in ("agy_policy_skipped_roles", "incomplete_roles", "manual_seats")}, sink)
        check("%s: 판정이 실패가 아니다(phoenix_restore ∉ FAILED/UNVERIFIED · COMPLETE)" % label,
              res.get("phoenix_restore") not in ("FAILED", "UNVERIFIED") and res.get("completeness") == "COMPLETE",
              (res.get("phoenix_restore"), res.get("completeness")), sink)
        check("%s: 재스폰 계수 — reviewer-gemini 0 · worker 1" % label,
              counts.get("reviewer-gemini", 0) == 0 and counts.get("worker") == 1, counts, sink)

    c, res, counts = scenario(src, tmp, tag + "P4", ["reviewer-gemini", "worker"], skip_line=False)
    check("P4 건너뜀 줄 없는 구 cys → fresh launch-agent rc 76 소비: agy_policy_skipped ∋ · 실패·미완 아님",
          c["fresh"] == ["reviewer-gemini"] and res.get("agy_policy_skipped_roles") == ["reviewer-gemini"]
          and res.get("completeness") == "COMPLETE" and res.get("phoenix_restore") not in ("FAILED", "UNVERIFIED")
          and counts.get("reviewer-gemini", 0) == 0,
          (c, res.get("agy_policy_skipped_roles"), res.get("completeness"), res.get("phoenix_restore"), counts), sink)
    c, res, counts = scenario(src, tmp, tag + "P5", ["reviewer-gemini"], no_breaker=False, breaker_seed=2)
    check("P5 차단기: 기존 실패 이력 2(임계 3) + 정책 좌석뿐 → BREAKER_OPEN 아님 · 이력 그대로 2(지우지도 늘리지도 않음)",
          res.get("phoenix_restore") != "BREAKER_OPEN" and counts["__breaker__"] == 2,
          (res.get("phoenix_restore"), counts), sink)
    c, res, counts = scenario(src, tmp, tag + "P3", ["reviewer-gemini"], runs=6, no_breaker=False)
    check("P3 정책 건너뜀뿐인 런 6회 연속 → BREAKER_OPEN 아님 · 재스폰 계수 0",
          res.get("phoenix_restore") != "BREAKER_OPEN" and counts.get("reviewer-gemini", 0) == 0,
          (res.get("phoenix_restore"), counts), sink)


def main():
    sys.path.insert(0, os.path.dirname(PH))
    with open(PH, encoding="utf-8") as f:
        src = f.read()
    tmp = tempfile.mkdtemp(prefix="ph-agy-loop-")
    axes(src, tmp, "base")
    # C0 대조군: 순수 판독 함수 — 건너뜀 줄만 고르고 기동 실패 줄은 고르지 않는다
    m = load_src(src, "ph_pure", tempfile.mkdtemp(dir=tmp))
    got = m.agy_policy_skipped_in(SKIP + "· worker: 기동 실패 — 나머지 역할 계속 진행\n· x: 건너뜀(other)\n")
    check("C0 agy_policy_skipped_in = {reviewer-gemini} 만", got == {"reviewer-gemini"}, got)
    mutants = [
        ("M1 resume 루프 소비 줄 제거",
         '            for _r in [r for r in need if r in agy_policy_skipped_in(res.get("out"))]:\n'
         '                _agy_policy_consume(_r, "cys restore 출력 「건너뜀(%s)」(attempt %d)" % (AGY_POLICY_CODE, attempt))\n',
         "", "P1"),
        ("M2 재스폰 계수 되돌림 제거",
         "            _respawn_counts[role] -= 1\n", "            pass\n", "재스폰 계수"),
        ("M3 fresh rc 76 소비 제거(독립 검증 뮤턴트 M15)",
         '                if res.get("rc") == AGY_POLICY_RC:', '                if False:', "P4"),
        ("M4 차단기 기록 조건 제거(codex 3R)",
         '    elif not no_breaker and not (not _agy_oracle.get("oracle_ok", True)',
         '    elif not no_breaker and not (False', "P5"),
    ]
    for name, old, new, axis in mutants:
        assert src.count(old) == 1, "변이 대상 부재/중복: " + name
        sink = []
        axes(src.replace(old, new), tmp, "m" + name[:2].lower(), sink=sink)
        check("%s → %s 축 적색" % (name, axis), any(axis in s for s in sink), sink)
    if fails:
        print("FAILED: %s" % fails)
        sys.exit(1)
    print("AGY-DOOR-PHOENIX-LOOP-OK")


if __name__ == "__main__":
    main()
