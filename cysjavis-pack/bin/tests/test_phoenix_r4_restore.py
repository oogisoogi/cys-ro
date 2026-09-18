#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_r4_restore.py — 같은 부트 세대 안에서 죽은 역할을 다시 살린다 (TICKET=restore-impl-A2-2).

실측 계기(R4): master claude 가 SIGTERM 으로 죽고 좌석은 남았다(role=master · exited=false · agent 없음).
`javis_phoenix.py restore --include-master` 는 매번 `spawn = skip 「이미 완료 — 재개」` 만 남겼다 — 같은
epoch 의 spawn 완료 마크가 생존 재확인 없이 skip 근거가 됐기 때문이다(epoch 게이트는 데몬 재기동 때만 리셋).

  A. R4-1  같은 세대 spawn 마크 + 지금 죽음 → 마크 무효화(spawn_mark_invalidated: dead_now) + 재스폰
           대조: 마크 + 살아 있음 → 스폰 0(NOOP) · 명시 --roles 경로도 살아 있으면 스폰 0(P1-3)
  B. R4-2  세대 재스폰 상한 3: 재스폰 4회째 → BREAKER_OPEN(exit 5) · 다음 사이클도 캡 유지(카운트 비리셋)
  C. R4-4  Windows(ps 표 None): 데몬 agent_alive=false → 사망(부활) · true → 생존 · null → unknown
           (부활 보류 + liveness_unknown_roles 보고 · spawn 마크가 있었으면 EVT)
  D. R4-3  빈 좌석 재사용: fresh 대상의 빈 좌석에 in-seat 연결 → 새 좌석 0 · 재사용 실패 → Reap 후 fresh(좌석 수 불변)
  H. I-4   ACK 핑 관문: < 100k 토큰 또는 캐시 생존(< 1h)만 핑 · 그 밖·측정 불가 = unverified(no-ping)(핑·주입 0)
  M. 뮤턴트 4(임시 사본 · 변이 적용 선-assert) — 각각 적색이어야 한다

실행: python3 cysjavis-pack/bin/tests/test_phoenix_r4_restore.py → 종료 토큰 PHOENIX-R4-RESTORE-OK
"""
import copy
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import time

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
T_DEAD = {664: ZSH, 665: ZSH}
T_ALIVE = {664: ZSH, 665: ZSH, 700: (664, "node /opt/homebrew/lib/node_modules/@anthropic-ai/claude-code/cli.js"),
           701: (665, "/usr/local/bin/claude")}


class _R(object):
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def seat(ref, seat_state, agent_alive=None, exited=False):
    return {"surface": ref, "pid": None, "exited": exited, "agent_alive": agent_alive, "seat": seat_state}


def harness(m, root, st):
    """m 의 전역을 대역으로 치환(데몬·cys·ps 실호출 0). st = 가변 세계 상태."""
    os.makedirs(os.path.join(root, "phoenix"), exist_ok=True)
    sock = os.path.join(root, "cys.sock")
    calls = st.setdefault("calls", {"restore": 0, "fresh": 0, "inseat": 0, "reinject": 0, "g2": 0,
                                    "close": [], "evt": []})
    m.CYS = os.path.join(root, "nonexistent-cys")
    m.log = lambda msg: None
    m._emit_evt = lambda *a, **k: calls["evt"].append(k.get("summary", ""))
    m._acquire_restore_lease = lambda s: (True, None)
    m.get_boot_epoch = lambda s: st["epoch"]
    m._recover_retention_file = lambda s, p, k: {"status": "missing"}
    m._recovered_provenance = lambda p: None
    m.c6_reap_stale_surfaces = lambda s: {}
    m.rollback_proposal = lambda s: {"stub": True}
    m.observe_and_persist_roster = lambda s, rebase=False: (copy.deepcopy(st["entries"]), set())
    m.live_role_surfaces = lambda s: copy.deepcopy(st["live"])
    m._surface_shell_pids = lambda s: {"surface:7": 664, "surface:14": 665}
    m._ps_table = lambda: st["table"]
    m._status_json = lambda s: copy.deepcopy(st.get("status"))
    m.restore_supports_per_entry_cwd = lambda s=None: False
    m.master_seat_cwd = lambda s, entries=None: None
    m.seat_fresh_cwd = lambda role, c, mc, log_fn=None: c
    m.fresh_awaken = lambda *a, **k: "awaken-stub"

    def _cys(*args, socket=None, timeout=25):
        if args and args[0] == "close-surface":
            calls["close"].append(list(args))
            st["live"] = {r: [s for s in ss if s["surface"] != args[1]] for r, ss in st["live"].items()}
            return _R(0, "closed")
        return _R(1, "", "stub cys")
    m.cys = _cys

    def _restore(s, roles, include_master=False, cwd=None):
        calls["restore"] += 1
        (st.get("on_restore") or (lambda: None))()
        return {"rc": 0, "out": "ok"}
    m.spawn_production = _restore

    def _fresh(s, role, agent, cwd=None):
        calls["fresh"] += 1
        (st.get("on_fresh") or (lambda: None))()
        return {"rc": 0, "out": "launched"}
    m.spawn_fresh_production = _fresh

    def _inseat(s, include_master=False, cwd=None):
        calls["inseat"] += 1
        (st.get("on_inseat") or (lambda: None))()
        return {"rc": 0, "out": "in-seat"}
    m.spawn_in_seat_production = _inseat
    m.stage_ready = lambda s, role, surf, stub: (True, "ready-stub")
    m.stage_observe_session = lambda s, surf, stub, role=None: ("S1", "topology re-pin(stub)")

    def _reinject(s, role, surf, stub):
        calls["reinject"] += 1
        return True, "reinject-stub"

    def _g2(s, role, surf, stub):
        calls["g2"] += 1
        return True, "g2-stub"
    m.stage_reinject = _reinject
    m.stage_g2_ack = _g2
    m.SPAWN_SETTLE = 0.0
    m.SPAWN_BACKOFF = 0.0
    return sock, calls


MASTER = {"master": {"agent": "claude", "session_id": "S1", "cwd": "/tmp"}}


def run(m, sock, **kw):
    return m.run_restore(sock, ticket="r4", stub=False, no_breaker=True, print_result=False, **kw)


def mac_world():
    """surface:7 = master 좌석(셸 pid 664). 살리기 = 좌석 occupied + ps 표에 claude."""
    st = {"epoch": "EPOCH-R4", "entries": copy.deepcopy(MASTER), "table": T_DEAD,
          "live": {"master": [seat("surface:7", "empty")]}}

    def revive():
        st["live"] = {"master": [seat("surface:7", "occupied", True)]}
        st["table"] = T_ALIVE

    def kill():
        st["live"] = {"master": [seat("surface:7", "empty", False)]}
        st["table"] = T_DEAD
    st["on_restore"] = revive
    return st, revive, kill


# ── A. R4-1 ──
def axis_a(m, root, sink=None):
    st, revive, kill = mac_world()
    sock, calls = harness(m, os.path.join(root, "a"), st)
    r1 = run(m, sock, include_master=True)
    check("A1 첫 부활 → VERIFIED(스폰 1)", r1.get("phoenix_restore") == "VERIFIED" and calls["restore"] == 1,
          (r1.get("phoenix_restore"), calls["restore"]), sink)
    kill()  # SIGTERM — 같은 epoch
    r2 = run(m, sock, include_master=True)
    j = m.load_journal(sock, "r4")
    inval = [e for e in j["events"] if e.get("role") == "master" and e.get("status") == "spawn_mark_invalidated: dead_now"]
    check("A2 같은 세대 spawn 마크 + 지금 죽음 → 재스폰(스폰 2)", calls["restore"] == 2,
          (calls["restore"], r2.get("phoenix_restore")), sink)
    check("A3 저널 spawn_mark_invalidated: dead_now 기록", len(inval) == 1, len(inval), sink)
    check("A4 재스폰 뒤 VERIFIED", r2.get("phoenix_restore") == "VERIFIED", r2.get("phoenix_restore"), sink)
    # 대조: 마크 + 살아 있음 → skip(스폰 0)
    r3 = run(m, sock, include_master=True)
    check("A5 대조: 마크 + 살아 있음 → NOOP · 스폰 0", r3.get("phoenix_restore") == "NOOP" and calls["restore"] == 2,
          (r3.get("phoenix_restore"), calls["restore"]), sink)
    r4 = run(m, sock, include_master=True, roles=["master"])
    check("A6 P1-3: 명시 --roles 경로도 살아 있으면 스폰 0", calls["restore"] == 2 and r4.get("phoenix_restore") == "NOOP",
          (r4.get("phoenix_restore"), calls["restore"]), sink)


# ── B. R4-2 ──
def axis_b(m, root, sink=None):
    st, revive, kill = mac_world()
    sock, calls = harness(m, os.path.join(root, "b"), st)
    verdicts = []
    for _ in range(4):  # 발주 1(부활) + 재스폰 3 = 상한 3 까지는 허용
        verdicts.append(run(m, sock, include_master=True).get("phoenix_restore"))
        kill()
    check("B1 부활 1 + 재스폰 3회는 허용(스폰 4)", calls["restore"] == 4 and "BREAKER_OPEN" not in verdicts,
          (calls["restore"], verdicts), sink)
    r5 = run(m, sock, include_master=True)
    check("B2 재스폰 4회째 → BREAKER_OPEN(respawn_cap) · 스폰 없음",
          r5.get("phoenix_restore") == "BREAKER_OPEN" and r5.get("breaker_reason") == "respawn_cap"
          and calls["restore"] == 4, (r5.get("phoenix_restore"), r5.get("breaker_reason"), calls["restore"]), sink)
    check("B3 exit 5(재시도 금지)", m.restore_exit_code(r5) == 5, m.restore_exit_code(r5), sink)
    r6 = run(m, sock, include_master=True)
    check("B4 다음 사이클도 캡 유지(상한 걸린 역할 카운트 비리셋)",
          r6.get("phoenix_restore") == "BREAKER_OPEN" and calls["restore"] == 4,
          (r6.get("phoenix_restore"), calls["restore"]), sink)
    st["epoch"] = "EPOCH-R4-NEXT"  # 데몬 재기동 = 새 세대 → 카운트 0
    r7 = run(m, sock, include_master=True)
    check("B5 새 세대 → 캡 해제·부활", r7.get("phoenix_restore") == "VERIFIED" and calls["restore"] == 5,
          (r7.get("phoenix_restore"), calls["restore"]), sink)


# ── C. R4-4 Windows ──
def axis_c(m, root, sink=None):
    st = {"epoch": "EPOCH-WIN", "entries": copy.deepcopy(MASTER), "table": None,
          "live": {"master": [seat("surface:7", "occupied", False)]}}

    def revive():
        st["live"] = {"master": [seat("surface:7", "occupied", True)]}
    st["on_restore"] = revive
    sock, calls = harness(m, os.path.join(root, "c"), st)
    r1 = run(m, sock, include_master=True)
    check("C1 ps 표 None + 데몬 agent_alive=false → 사망(부활 대상 · 스폰 1)",
          r1.get("target_roles") == ["master"] and calls["restore"] == 1,
          (r1.get("target_roles"), calls["restore"]), sink)
    st["live"] = {"master": [seat("surface:7", "occupied", False)]}  # 같은 세대에 다시 죽음(데몬 확정)
    run(m, sock, include_master=True)
    check("C2 Windows 에서도 R4 재스폰(스폰 2)", calls["restore"] == 2, calls["restore"], sink)
    st["live"] = {"master": [seat("surface:7", "occupied", True)]}
    r3 = run(m, sock, include_master=True)
    check("C3 agent_alive=true → 생존(NOOP)", r3.get("phoenix_restore") == "NOOP" and calls["restore"] == 2,
          (r3.get("phoenix_restore"), calls["restore"]), sink)
    st["live"] = {"master": [seat("surface:7", "occupied", None)]}
    n_evt = len(calls["evt"])
    r4 = run(m, sock, include_master=True)
    check("C4 agent_alive=null → unknown: 부활 보류(스폰 0 · 맹목 재스폰 없음)",
          calls["restore"] == 2 and r4.get("target_roles") == [], (calls["restore"], r4.get("target_roles")), sink)
    check("C5 unknown 은 정직 보고(liveness_unknown_roles) — 생존 취급 아님",
          r4.get("liveness_unknown_roles") == ["master"], r4.get("liveness_unknown_roles"), sink)
    check("C6 이 세대에 부활시킨 역할의 unknown → EVT(침묵 아님)",
          any("생존 확인 불가" in e for e in calls["evt"][n_evt:]), calls["evt"][n_evt:], sink)


# ── D. R4-3 ──
def axis_d(m, root, sink=None):
    # 1사이클: cys restore 가 빈 좌석에 못 앉힘 → 빈 좌석을 spawn 으로 집음 → verify(ps 죽음) → force_fresh
    st = {"epoch": "EPOCH-SEAT", "entries": copy.deepcopy(MASTER), "table": T_DEAD,
          "live": {"master": [seat("surface:7", "empty")]}}

    def inseat_ok():
        st["live"] = {"master": [seat("surface:7", "occupied", True)]}
        st["table"] = T_ALIVE
    st["on_inseat"] = inseat_ok
    sock, calls = harness(m, os.path.join(root, "d1"), st)
    run(m, sock, include_master=True)
    r2 = run(m, sock, include_master=True)
    j = m.load_journal(sock, "r4")
    n_seats = sum(len(v) for v in st["live"].values())
    check("D1 빈 좌석 in-seat 재사용(fresh launch-agent 0 · in-seat 1)",
          calls["inseat"] == 1 and calls["fresh"] == 0, dict((k, calls[k]) for k in ("inseat", "fresh")), sink)
    check("D2 새 좌석 0 · 그 좌석이 부활 좌석(surface:7)",
          n_seats == 1 and (j["roles"].get("master") or {}).get("surface") == "surface:7" and not calls["close"],
          (n_seats, (j["roles"].get("master") or {}).get("surface"), calls["close"]), sink)
    check("D3 결과 fresh 부활 완료", r2.get("phoenix_restore") == "VERIFIED_FRESH", r2.get("phoenix_restore"), sink)

    # 재사용 불가 → 빈 좌석 Reap 후 fresh(좌석 수 불변 — 4→5 증식 없음)
    st2 = {"epoch": "EPOCH-SEAT2", "entries": copy.deepcopy(MASTER), "table": T_DEAD,
           "live": {"master": [seat("surface:7", "empty")]}}

    def fresh_new_seat():
        st2["live"].setdefault("master", []).append(seat("surface:14", "occupied", True))
        st2["table"] = T_ALIVE
    st2["on_fresh"] = fresh_new_seat
    sock2, calls2 = harness(m, os.path.join(root, "d2"), st2)
    run(m, sock2, include_master=True)
    run(m, sock2, include_master=True)
    n2 = sum(len(v) for v in st2["live"].values())
    check("D4 재사용 불가 → 빈 좌석 --reap 회수", calls2["close"] == [["close-surface", "surface:7", "--reap"]],
          calls2["close"], sink)
    check("D5 회수 뒤 fresh 1 · 좌석 수 불변(1)", calls2["fresh"] == 1 and n2 == 1, (calls2["fresh"], st2["live"]), sink)


# ── H. I-4 ACK 핑 관문 ──
def axis_h(m, root, sink=None):
    old = os.path.join(root, "h-old.jsonl")
    new = os.path.join(root, "h-new.jsonl")
    os.makedirs(root, exist_ok=True)
    for p in (old, new):
        io.open(p, "w", encoding="utf-8").write("{}\n")
    t_old = time.time() - 7200
    os.utime(old, (t_old, t_old))

    def status(usage):
        return {"surfaces": [{"surface_ref": "surface:7", "agent_alive": True, "seat": "occupied", "usage": usage}]}
    cases = [
        ("H1 < 100k 토큰 → 핑", status({"ctx_tokens": 50000, "session_file": old}), True),
        ("H2 대형 + 캐시 만료(2h) → no-ping", status({"ctx_tokens": 500000, "session_file": old}), False),
        ("H3 usage 미관측 → no-ping(측정 불가 = 주입 0)", status(None), False),
        ("H4 대형 + 캐시 생존(<1h) → 핑", status({"ctx_tokens": 500000, "session_file": new}), True),
        ("H5 status 미도달 → no-ping", None, False),
    ]
    for i, (name, stv, want_ping) in enumerate(cases):
        st, revive, kill = mac_world()
        st["status"] = stv
        sock, calls = harness(m, os.path.join(root, "h%d" % i), st)
        run(m, sock, include_master=True)
        j = m.load_journal(sock, "r4")
        ack = (j["roles"].get("master") or {}).get("ack", "")
        pinged = calls["reinject"] + calls["g2"]
        if want_ping:
            check(name, pinged == 2 and ack.startswith("ping("), (pinged, ack), sink)
        else:
            check(name, pinged == 0 and ack == "unverified(no-ping)", (pinged, ack), sink)


def all_axes(m, root, sink=None):
    axis_a(m, root, sink)
    axis_b(m, root, sink)
    axis_c(m, root, sink)
    axis_d(m, root, sink)
    axis_h(m, root, sink)


root = tempfile.mkdtemp(prefix="phoenix-r4-")
try:
    live_mod = load(PH, "_ph_r4_live")
    all_axes(live_mod, os.path.join(root, "live"))

    src = io.open(PH, encoding="utf-8").read()
    mutants = [
        ("M1 skip 조건을 종전(stage_done 만)으로", '        if stage_done(j, role, "spawn") and _alive(role):\n',
         '        if stage_done(j, role, "spawn"):\n'),
        ("M2 Windows ps None 경로 = 생존", '            rec = next((s for s in live.get(role, []) if s.get("surface") == surface), {})\n',
         '            return "alive"\n'),
        ("M3 카운트 프루닝을 이번 사이클 행동 집합으로", '    _eligible = {r for r in entries if r not in _tombstones}\n',
         '    _eligible = set(_acted)\n'),
        ("M4 재스폰 상한 제거", '    _capped = [r for r in target_roles if respawn_capped(_respawn_counts, r)]\n',
         '    _capped = []\n'),
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
            mm = load(mp, "_ph_r4_mut%d" % i)
            all_axes(mm, os.path.join(root, "mut%d" % i), sink)
        except Exception as e:  # noqa: BLE001 — 변이가 크래시를 내도 적색(= 잡힘)
            sink.append("크래시 %s: %s" % (type(e).__name__, e))
        check("%s → 적색(KILLED) — %s" % (name, sink[:3]), bool(sink), sink)
finally:
    shutil.rmtree(root, ignore_errors=True)

if fails:
    print("\n%d FAIL: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("\nALL PASS")
print("PHOENIX-R4-RESTORE-OK")
sys.exit(0)
