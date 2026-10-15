#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_dbg119_profile_hold.py — 계정 프로필 거부 역할을 Phase 11 이 기본 계정 fresh 로 띄우지 않는다
(TICKET=debug-cysr-119-prerelease ① · master#7a176ca4).

결함: Rust `cys restore` 는 claude 좌석이 `config_dir_authority=="unobserved"` 이거나 `seat_profile` 검증에 실패하면
그 역할 기동을 멈춘다(`cys::restore_config_dir` · cys.rs 「새 대화 폴백도 하지 않는다: 다른 계정으로 뜨는 것이
10-08 한도 정지 사고다」). 그런데 phoenix 는 그 역할을 「미스폰」으로 세어 재시도를 소진한 뒤 Phase 11 독약
fresh 대체로 `cys launch-agent`(agents.json 기본 계정 · 새 대화)를 띄웠다 = Rust 가 막은 바로 그 폴백.
수리: Phase 11 진입에서 `_restore_config_dir` 거부 역할을 fresh 대상에서 빼고 「복원 보류 + 사유 1줄」로 저널에 남긴다.

  P  대조군: 거부 없는 역할의 resume 실패 → 독약 fresh 강등은 그대로(restore 4 · fresh 1)
  H1 config_dir_authority=unobserved → fresh 0 · 저널 spawn 사건 profile_held(사유 unobserved) · spawn 단계 미완
  H2 seat_profile 검증 실패(상대 경로) → fresh 0 · 사유 seat_profile_refused:not_absolute
  M  뮤턴트 1(보류 거르기 제거 · 변이 적용 선-assert) → H1 적색

실행: python3 cysjavis-pack/bin/tests/test_phoenix_dbg119_profile_hold.py → 종료 토큰 PHOENIX-DBG119-PROFILE-HOLD-OK
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
HELD_OUT = "· master: 기동 중단 — 관측 권위 없음\nrestore 완료: 재기동 0 · 실패 1"


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
    m.get_boot_epoch = lambda s: "EPOCH-DBG119"
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
    m.run_restore(sock, ticket="dbg119", stub=False, no_breaker=True, print_result=False, include_master=True)
    return calls["restore"], calls["fresh"], st["journal"]


def held_events(j):
    return [e for e in (j or {}).get("events", []) if e.get("role") == "master" and e.get("status") == "profile_held"]


def axes(src, tmp, tag, sink=None):
    r, f, _j = scenario(src, tmp, tag + "p", {}, FAIL_OUT)
    check("P 대조군: 거부 없는 역할 = 독약 fresh 강등 유지(restore 4 · fresh 1)", (r, f) == (4, 1), (r, f), sink)
    r, f, j = scenario(src, tmp, tag + "h1", {"config_dir_authority": "unobserved"}, HELD_OUT)
    ev = held_events(j)
    spawn = ((j or {}).get("roles", {}).get("master", {}).get("stages", {}).get("spawn") or {})
    check("H1 unobserved = 기본 계정 fresh 0", f == 0, (r, f), sink)
    check("H1 저널 profile_held 1건 · 사유 unobserved", len(ev) == 1 and "unobserved" in ev[0].get("msg", ""),
          ev, sink)
    check("H1 spawn 단계 미완(복원 보류 = INCOMPLETE 유지 · 성공으로 세지 않음)",
          spawn.get("done") is False and "복원 보류" in spawn.get("evidence", ""), spawn, sink)
    r, f, j = scenario(src, tmp, tag + "h2", {"seat_profile": "relative/acct"}, HELD_OUT)
    ev = held_events(j)
    check("H2 seat_profile 검증 실패 = fresh 0 · 사유 seat_profile_refused:not_absolute",
          f == 0 and len(ev) == 1 and "seat_profile_refused:not_absolute" in ev[0].get("msg", ""), (f, ev), sink)


def main():
    sys.path.insert(0, os.path.dirname(PH))
    with open(PH, encoding="utf-8") as f:
        src = f.read()
    tmp = tempfile.mkdtemp(prefix="ph-dbg119-hold-")
    axes(src, tmp, "base")
    a = "    need = _hold_profile_refused(need)\n"
    n = src.count(a)
    check("M1 보류 거르기 제거 변이 적용 선-assert(정확 1곳)", n == 1, "count=%d" % n)
    if n == 1:
        sink = []
        axes(src.replace(a, ""), tmp, "m1", sink=sink)
        check("M1 보류 거르기 제거 → KILLED(H1 축 적색)", any(x.startswith("H1") for x in sink), "적색=%s" % sink)
    if fails:
        print("FAIL 합계 %d: %s" % (len(fails), fails))
        sys.exit(1)
    print("PHOENIX-DBG119-PROFILE-HOLD-OK")


if __name__ == "__main__":
    main()
