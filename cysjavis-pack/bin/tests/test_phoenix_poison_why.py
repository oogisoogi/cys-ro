#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_poison_why.py — 독약 강등(Phase 11)의 **까닭**이 로그·저널·결과에 남는가(TICKET=cysr-1118u-debug · 1.1.18 · 데몬 불요).

결함(윈 실기 1.1.17 관찰 ③ · 11-19·11-22·11-23 worker 「poison」 반복): resume 회차(`cys restore`)가 그 역할을 부활로 세지 않은
까닭(이번 출력의 「기동 실패」 줄 · 좌석 없음 · 좌석은 있으나 agent_alive/seat 미달)이 어디에도 남지 않았다 — phoenix-restore.log 에는
`cys restore` 원문과 「★독약 세션 fresh 강등: … (resume 불가 → 무 resume 부활)」 만 있어 왜 resume 을 버렸는지 가를 수 없었다.
수리(관측 전용 · 판정 그대로): 미달 회차마다 역할별 사유 1줄을 로그 + 저널(spawn 사건 status=miss)에 · 강등 때 roles.<역할>.poison_why ·
강등 로그 줄과 verify 사유에 「까닭」 을 붙인다.

  U1 restore_role_lines: 800자 뒤 역할 줄도 원문으로 뽑는다 · 역할별로 모은다
  U2 spawn_miss_reason: 기동 실패 / 좌석 없음 / 부활 조건 미달(좌석 사실) 셋을 가르고 rc·원문을 싣는다
  P  기동 실패 꼴: 판정 불변(restore 4 · fresh 1 = 수리 전과 같음) · 미달 사건 4건 · poison_why · 강등 로그 까닭 · verify 사유 까닭 ·
     결과 honesty_note 까닭
  Q  좌석 미달 꼴(실패 줄 없음 · agent_alive=None · seat=empty): 사유 = 좌석 사실 원문
  M  뮤턴트(미달 사유 기록 제거 · 변이 적용 선-assert) → P 적색

실행: python3 cysjavis-pack/bin/tests/test_phoenix_poison_why.py → 종료 토큰 PHOENIX-POISON-WHY-OK
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
        print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + str(detail)[:400]) if detail else ""))
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


FAIL_LINE = "· master: 기동 실패 — 나머지 역할 계속 진행"
FAIL_OUT = "· master: claude 재기동…\n%s\nrestore 완료: 재기동 0 · 실패 1" % FAIL_LINE
QUIET_OUT = "· master: claude 재기동…\nrestore 완료: 재기동 1 · 실패 0"
EMPTY_SEAT = {"surface": "surface:7", "pid": 70, "exited": False, "agent_alive": None, "seat": "empty"}


def scenario(src, tmp, tag, out, seat_rows):
    """죽은 master 1명 부활 1사이클(생산 경로 · 대역) — 반환 = (restore 수, fresh 수, 저널, 로그 줄, 결과)."""
    d = tempfile.mkdtemp(prefix=tag + "-", dir=tmp)
    m = load_src(src, "ph_" + tag, d)
    sockdir = os.path.join(d, "sock")
    os.makedirs(os.path.join(sockdir, "phoenix"), exist_ok=True)
    sock = os.path.join(sockdir, "cys.sock")
    calls = {"restore": 0, "fresh": 0}
    st = {"live": {}, "journal": None}
    logs = []
    m.CYS = os.path.join(d, "nonexistent-cys")
    m.log = logs.append
    m._emit_evt = lambda *a, **k: None
    m._acquire_restore_lease = lambda s: (True, None)
    m.get_boot_epoch = lambda s: "EPOCH-POISON-WHY"
    m._recover_retention_file = lambda s, p, k: {"status": "missing"}
    m._recovered_provenance = lambda p: None
    m.c6_reap_stale_surfaces = lambda s: {}
    entry = {"agent": "claude", "session_id": "S1", "cwd": d}
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
        calls["restore"] += 1
        st["live"] = {"master": [dict(x) for x in seat_rows]}
        # 실물 spawn_production 과 같은 키: out 은 800자 절단 · 역할 줄은 전량에서(수리 전 소스엔 이 키가 없다 = .get 이 None)
        return {"rc": 1, "out": out[:800], "restore_role_lines": m.restore_role_lines(out)
                if hasattr(m, "restore_role_lines") else None}
    m.spawn_production = _restore
    m.spawn_in_seat_production = lambda s, include_master=False, cwd=None, units=None: {"rc": 1, "out": "stub"}

    def _fresh(s, role, agent, cwd=None):
        calls["fresh"] += 1
        st["live"] = {"master": [{"surface": "surface:99", "pid": None, "exited": False,
                                  "agent_alive": True, "seat": "occupied"}]}
        return {"rc": 0, "out": "launched"}
    m.spawn_fresh_production = _fresh
    m.close_surface = lambda *a, **k: None
    m.cys = lambda *a, **k: type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()
    _save = m.save_journal

    def _cap(s, t, j):
        st["journal"] = j
        _save(s, t, j)
    m.save_journal = _cap
    m.stage_ready = lambda s, role, surf, stub: (True, "ready-stub")
    m.stage_observe_session = lambda s, surf, stub, role=None: ("S-NEW", "stub")
    m.stage_reinject = lambda s, role, surf, stub: (True, "stub")
    m.stage_g2_ack = lambda s, role, surf, stub: (True, "stub")
    m.SPAWN_SETTLE = 0.0
    m.SPAWN_BACKOFF = 0.0
    res = m.run_restore(sock, ticket="poisonwhy", stub=False, no_breaker=True, print_result=False, include_master=True)
    return calls["restore"], calls["fresh"], st["journal"], logs, res


def miss_events(j):
    return [e for e in (j or {}).get("events", []) if e.get("role") == "master" and e.get("status") == "miss"]


def axes(src, tmp, tag, sink=None):
    r, f, j, logs, res = scenario(src, tmp, tag + "p", FAIL_OUT, [])
    ev = miss_events(j)
    why = ((j or {}).get("roles", {}).get("master", {}) or {}).get("poison_why", "")
    text = "\n".join(logs)
    check("P 판정 불변: restore 4 · fresh 1(수리 전과 같음)", (r, f) == (4, 1), (r, f), sink)
    check("P 미달 사건 = 회차마다 1건(4) · 사유 기동 실패 · 원문 줄", len(ev) == 4 and all(
        "cys restore 「기동 실패」" in e["msg"] and FAIL_LINE in e["msg"] and "rc=1" in e["msg"] for e in ev), ev, sink)
    check("P roles.master.poison_why = 마지막 회차 사유", why.startswith("attempt 3 · cys restore 「기동 실패」") and FAIL_LINE in why,
          why, sink)
    check("P 로그: 회차별 미달 사유 줄 4 + 강등 줄에 까닭",
          text.count("★부활 미달 사유 master: attempt") == 4
          and any(x.startswith("★독약 세션 fresh 강등: role=master") and "까닭: attempt 3" in x for x in logs), text[-600:], sink)
    vr = ((j or {}).get("roles", {}).get("master", {}) or {}).get("verify_reason", "")
    check("P 저널 verify 사유에 강등 까닭", "강등 까닭: attempt 3 · cys restore 「기동 실패」" in vr, vr, sink)
    hn = (res or {}).get("honesty_note", "") if isinstance(res, dict) else ""
    check("P 결과 honesty_note 에 강등 까닭(역할별)", '강등 까닭={"master": "attempt 3 · cys restore 「기동 실패」' in hn, hn[-400:], sink)
    r, f, j, logs, _ = scenario(src, tmp, tag + "q", QUIET_OUT, [EMPTY_SEAT])
    ev = miss_events(j)
    check("Q 좌석 미달: 사유 = 좌석 사실 원문(agent_alive=None seat=empty) · 판정 불변",
          (r, f) == (4, 1) and len(ev) == 4 and all(
              "부활 조건 미달(surface:7 exited=False agent_alive=None seat=empty)" in e["msg"] for e in ev), (r, f, ev[:1]), sink)


def main():
    sys.path.insert(0, os.path.dirname(PH))
    with open(PH, encoding="utf-8") as f:
        src = f.read()
    tmp = tempfile.mkdtemp(prefix="ph-poison-why-")
    m = load_src(src, "ph_unit", tempfile.mkdtemp(dir=tmp))
    long_out = "x" * 900 + "\n· worker: claude 재기동…\n· worker: 기동 실패 — 나머지 역할 계속 진행\n· cso: 좌석 내 재연결\n"
    rl = m.restore_role_lines(long_out) if hasattr(m, "restore_role_lines") else {}
    check("U1 800자 뒤 역할 줄도 원문 · 역할별", rl.get("worker") == ["· worker: claude 재기동…", "· worker: 기동 실패 — 나머지 역할 계속 진행"]
          and rl.get("cso") == ["· cso: 좌석 내 재연결"] and m.restore_role_lines(None) == {}, rl)
    f = getattr(m, "spawn_miss_reason", None)
    check("U2 사유 3갈래 · rc · 원문(없으면 그렇게 적음)", f is not None
          and f("worker", {"worker"}, [], rl, 1).startswith("cys restore 「기동 실패」 · restore rc=1 · 원문: · worker: claude 재기동…")
          and f("cso", set(), [], {}, 0) == "역할 좌석 없음 · restore rc=0 · 원문: (이 역할 줄 없음)"
          and f("cso", set(), [EMPTY_SEAT], rl, 0).startswith("부활 조건 미달(surface:7 exited=False agent_alive=None seat=empty)"),
          "missing" if f is None else f("worker", {"worker"}, [], rl, 1))
    axes(src, tmp, "base")
    a = '                    jevent(j, role, "spawn", "miss", "부활 미달 " + miss_why[role])\n'
    n = src.count(a)
    check("M1 미달 사건 기록 제거 변이 적용 선-assert(정확 1곳)", n == 1, "count=%d" % n)
    if n == 1:
        sink = []
        axes(src.replace(a, ""), tmp, "m1", sink=sink)
        check("M1 미달 사건 기록 제거 → KILLED(P 축 적색)", any(x.startswith("P 미달") for x in sink), "적색=%s" % sink)
    if fails:
        print("FAIL 합계 %d: %s" % (len(fails), fails))
        sys.exit(1)
    print("PHOENIX-POISON-WHY-OK")


if __name__ == "__main__":
    main()
