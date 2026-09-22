#!/usr/bin/env python3
"""test_v115_dept — cysr 1.1.5 트랙 P(팩·부서) 수리(TICKET=v115-dept).

  A2 부서장 좌석 회수 오판(1.1.4 VM 904 §5-②):
     ⓐ 편성·phoenix 가 빈 부서장 좌석을 채운다 — boot_node 는 빈 좌석을 「입양-주입」하지 않고 승계 기동,
        (phoenix 스폰 판정의 빈 좌석 제외 = 트랙 D 906 소유 · master#6e260aed B안 — 이 파일 밖)
     ⓑ --cwd 미지정이면 부서 레지스트리 폴더(dept_registry_cwd — lib.rs 미러) · phoenix master_seat_cwd 3순위
     ⓒ 부팅 유예 안의 빈 좌석 = 회수 금지(_reclaim_verdict hold-grace)
  B8 빈 셸 좌석(에이전트가 붙었다 죽은 좌석) = 유예 뒤 회수-재기동(비승계 역할) · 이벤트 1줄
  A5 CSO·워커 사용자 환경 변경 금지 문안 + 스텁뿐인 맥에서 세션 python3 = 번들(CLAUDE_ENV_FILE)
  B2 참가자 좌석 recap 줄 기본 off(preflight C83 · awaySummaryEnabled 사전 기입 · 사용자 값 존중)
  B3 [DRAIN-VERIFY] 발신 주체 문구 = 「오너의 재시작 조작(앱 재시작 단추 · 새 판 설치)」 — 설치기 드레인 포함
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

SELF = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(SELF)
PACK = os.path.dirname(BIN)
REPO = os.path.dirname(PACK)
sys.path.insert(0, BIN)

import javis_boot_node as bn  # noqa: E402

NOW = 1_800_000_000.0


def _st(role="master", seat="empty", created=NOW - 10, agent=None, extra=None):
    s = {"role": role, "exited": False, "seat": seat, "created_at": created, "agent": agent,
         "surface_ref": "surface:1", "pid": 111}
    s.update(extra or {})
    return {"surfaces": [s]}


class A2GraceAndVerdict(unittest.TestCase):
    def test_grace_only_for_young_empty_seat(self):
        self.assertTrue(bn.seat_in_boot_grace(_st(created=NOW - 10), "master", now=NOW, grace=180))
        self.assertFalse(bn.seat_in_boot_grace(_st(created=NOW - 181), "master", now=NOW, grace=180))
        self.assertFalse(bn.seat_in_boot_grace(_st(seat="occupied"), "master", now=NOW, grace=180))
        # 필드 부재·비수치는 판정으로 융합하지 않는다(단방향)
        self.assertFalse(bn.seat_in_boot_grace(_st(created=None), "master", now=NOW, grace=180))
        self.assertFalse(bn.seat_in_boot_grace(_st(created=True), "master", now=NOW, grace=180))

    def test_grace_env_default_180(self):
        old = os.environ.pop(bn.SEAT_BOOT_GRACE_ENV, None)
        try:
            self.assertEqual(bn.seat_boot_grace_s(), 180.0)
            for bad in ("-5", "abc", ""):
                os.environ[bn.SEAT_BOOT_GRACE_ENV] = bad
                self.assertEqual(bn.seat_boot_grace_s(), 180.0, bad)
            os.environ[bn.SEAT_BOOT_GRACE_ENV] = "30"
            self.assertEqual(bn.seat_boot_grace_s(), 30.0)
        finally:
            os.environ.pop(bn.SEAT_BOOT_GRACE_ENV, None)
            if old is not None:
                os.environ[bn.SEAT_BOOT_GRACE_ENV] = old

    def test_reclaim_verdict_holds_in_grace(self):
        # 904 재현: 부팅 3분차(생성 170초 뒤) 빈 부서장 좌석 — 종전엔 kill 이었다
        st = _st(created=NOW - 170)
        self.assertEqual(bn._reclaim_verdict(st, "master", 111, 111, now=NOW, grace=180), "hold-grace")
        # 유예 뒤에는 종전 판정 그대로(kill)
        st2 = _st(created=NOW - 400)
        self.assertEqual(bn._reclaim_verdict(st2, "master", 111, 111, now=NOW, grace=180), "kill")
        # 순서: 생존이 유예보다 먼저 · 상태 불명이 제일 먼저
        self.assertEqual(bn._reclaim_verdict(None, "master", 111, 111, now=NOW, grace=180), "hold-status")

    def test_empty_seat_action_table(self):
        a = lambda **k: bn.empty_seat_action(_st(**k), k.get("role", "master"), now=NOW, grace=180)  # noqa: E731
        # 한 번도 에이전트가 없던 부서장 빈 셸(allocate) = 편성이 곧장 채운다(유예 무관)
        self.assertEqual(a(role="master", agent=None, created=NOW - 5), "takeover")
        self.assertEqual(a(role="cso", agent=None, created=NOW - 5), "takeover")
        # 에이전트가 붙었다 죽은 좌석(B8) = 유예 안 보류 · 유예 뒤 처분
        self.assertEqual(a(role="master", agent="claude", created=NOW - 5), "hold-grace")
        self.assertEqual(a(role="master", agent="claude", created=NOW - 500), "takeover")
        self.assertEqual(a(role="worker", agent="claude", created=NOW - 5), "hold-grace")
        self.assertEqual(a(role="worker", agent="claude", created=NOW - 500), "reap-launch")
        self.assertEqual(a(role="worker", agent=None, created=NOW - 500), "reap-launch")
        # 비어 있지 않거나 좌석 차원 없음 = 비해당(종전 흐름)
        self.assertIsNone(a(role="master", seat="occupied"))
        self.assertIsNone(a(role="master", seat=None))


class A2DeptRegistryCwd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.d1 = os.path.join(self.tmp, "교육부")
        os.makedirs(self.d1)

    def test_socket_match_name_rule_and_dir_required(self):
        reg = {"depts": {
            "dept-1": {"socket": "/s/one.sock", "cwd": self.d1},
            "dept-2": {"socket": "/s/two.sock", "cwd": "/gone/x"},
            "dept-3": {"cwd": self.d1},
        }}
        f = lambda s: bn.dept_registry_cwd(socket=s, reg=reg)  # noqa: E731
        self.assertEqual(f("/s/one.sock"), self.d1)
        self.assertIsNone(f("/s/two.sock"), "없는 폴더를 좌석 cwd 로")
        self.assertIsNone(f("/s/nope.sock"), "남의 부서 폴더")
        self.assertEqual(f("/h/.local/state/cys-dept-dept-3/cys.sock"), self.d1, "이름 규약 미적용")
        self.assertIsNone(bn.dept_registry_cwd(socket="", reg=reg))

    def test_reads_file_from_env(self):
        p = os.path.join(self.tmp, "depts.json")
        json.dump({"depts": {"dept-1": {"socket": "/s/one.sock", "cwd": self.d1}}}, open(p, "w"))
        old = os.environ.get("CYS_DEPTS_JSON")
        os.environ["CYS_DEPTS_JSON"] = p
        try:
            self.assertEqual(bn.dept_registry_cwd(socket="/s/one.sock"), self.d1)
        finally:
            if old is None:
                os.environ.pop("CYS_DEPTS_JSON", None)
            else:
                os.environ["CYS_DEPTS_JSON"] = old

    def test_phoenix_master_seat_cwd_third_candidate(self):
        import javis_phoenix as ph
        p = os.path.join(self.tmp, "depts.json")
        json.dump({"depts": {"dept-1": {"socket": "/s/one.sock", "cwd": self.d1}}}, open(p, "w"))
        saved = (ph._status_json, os.environ.get("CYS_DEPTS_JSON"))
        home = os.path.expanduser("~")
        # 904 재현: 라이브 master = 홈 빈 셸 · 토폴로지 master = 홈(오판 회수가 덮음)
        ph._status_json = lambda s: {"surfaces": [{"role": "master", "exited": False, "cwd": home}]}
        os.environ["CYS_DEPTS_JSON"] = p
        try:
            self.assertEqual(ph.master_seat_cwd("/s/one.sock", {"master": {"cwd": home}}), self.d1)
            self.assertIsNone(ph.master_seat_cwd("/s/base.sock", {"master": {"cwd": home}}), "본부 소켓에 부서 폴더")
        finally:
            ph._status_json = saved[0]
            if saved[1] is None:
                os.environ.pop("CYS_DEPTS_JSON", None)
            else:
                os.environ["CYS_DEPTS_JSON"] = saved[1]



class _FakeCys:
    """boot_node 의 run() 대역 — cys 명령을 기록하고 좌석 표를 바꾼다(라이브 데몬 무접촉)."""

    def __init__(self, rows):
        self.rows = rows      # [{ref, role, pid, exited, seat, agent, created}]
        self.calls = []
        self.next_id = 50
        self.queues = {}      # ref → 큐 줄 수(cys queue list 4칸 행)

    def status(self):
        self.status_calls = getattr(self, "status_calls", 0) + 1
        flip = getattr(self, "flip_on_status", None)   # (n번째 조회, ref) — 그 조회부터 좌석이 산 것으로
        if flip and self.status_calls >= flip[0]:
            for r in self.rows:
                if r["ref"] == flip[1]:
                    r["seat"] = "occupied"
        for r in self.rows:   # (v115r3-d7) 조회마다 좌석 사실을 차례로 — 데몬 워치독이 unknown 을 채우는 흉내
            seq = getattr(self, "seat_seq", {}).get(r["ref"])
            if seq:
                r["seat"] = seq.pop(0)
        return {"surfaces": [{"surface_ref": r["ref"], "role": r["role"], "pid": r["pid"], "exited": False,
                              "seat": r["seat"], "agent": r["agent"], "created_at": r["created"]}
                             for r in self.rows if r["role"]]}

    def __call__(self, args, timeout=15):
        self.calls.append(list(args))
        a = args[1:]
        if a[:2] == ["status", "--json"]:
            return 0, json.dumps(self.status()), ""
        if a[:1] == ["list"]:
            out = "\n".join("%s\trole=%s\tpid=%s\texited=false" % (r["ref"], r["role"] or "-", r["pid"])
                            for r in self.rows)
            return 0, out, ""
        if a[:1] == ["launch-agent"]:
            role = a[a.index("--role") + 1]
            for r in self.rows:           # 승계: 옛 빈 좌석의 role 이 새 좌석으로
                if r["role"] == role:
                    r["role"] = None
            self.rows.append({"ref": "surface:%d" % self.next_id, "role": role, "pid": 900 + self.next_id,
                              "seat": "occupied", "agent": "claude", "created": time.time()})
            self.next_id += 1
            return 0, "", ""
        if a[:2] == ["queue", "list"]:
            n = self.queues.get(a[a.index("--surface") + 1], 0)
            return 0, "\n".join("q%d\tx\ty\tpreview" % i for i in range(n)), ""
        if a[:1] == ["close-surface"]:
            self.rows = [r for r in self.rows if r["ref"] != a[1]]
            return 0, "", ""
        return 0, "", ""


class D7FormationRecordsBootReason(unittest.TestCase):
    """v115r3-d7(D7⑴): 편성이 빠진 역할의 boot_node result/reason 을 detail(=formation.log)에 싣는다.
    09-22 VM formation.log 는 「기동=cso,worker」 뿐이라 master 가 왜 빠졌는지 0자였다."""

    def test_boot_verdict_text_reads_last_json_line(self):
        import javis_formation as fm
        out = 'noise\n{"role": "master", "result": "injected_unverified", "reason": "queue_pending", "log": []}\n'
        self.assertEqual(fm._boot_verdict_text(out), "injected_unverified/queue_pending")
        self.assertIsNone(fm._boot_verdict_text("not json"))
        self.assertIsNone(fm._boot_verdict_text(""))

    def test_failed_master_reason_lands_in_detail(self):
        import javis_formation as fm
        keys = ("gate_check", "_installed_clis", "_live_roles", "_resource_ok", "_boot_node",
                "_ensure_master_seat", "_feed", "_emit_evt")
        saved = {k: getattr(fm, k) for k in keys}
        saved_env = dict(os.environ)
        os.environ["CYS_STATE_DIR"] = tempfile.mkdtemp()
        os.environ.pop("CYS_FORMATION_EXTERNAL_ROLES", None)
        try:
            fm.gate_check = lambda: True
            fm._installed_clis = lambda: {"claude"}
            fm._live_roles = lambda socket=None, require_live_agent=True: set()
            fm._resource_ok = lambda socket=None: True
            fm._boot_node = lambda role, socket, cwd=None, timeout=200: (True, "stub")
            fm._ensure_master_seat = lambda socket, cwd: (False, "injected_unverified/queue_pending")
            fm._feed = lambda *a, **k: None
            fm._emit_evt = lambda *a, **k: None
            _state, detail = fm.ensure(socket="/tmp/d7-reason.sock", cwd=os.environ["CYS_STATE_DIR"])
        finally:
            for k, v in saved.items():
                setattr(fm, k, v)
            os.environ.clear()
            os.environ.update(saved_env)
        self.assertIn("기동실패=master:injected_unverified/queue_pending", detail)
        self.assertNotIn("cso:", detail.split("기동실패=", 1)[1].split(" · ", 1)[0], "성공 역할을 실패로 적었다")


class A2B8BootNodeRun(unittest.TestCase):
    def _run(self, rows, role, extra_env=None, queues=None, flip_on_status=None, seat_seq=None):
        fake = _FakeCys(rows)
        fake.queues = queues or {}
        fake.flip_on_status = flip_on_status
        fake.seat_seq = seat_seq or {}
        saved = (bn.run, bn._awaken, time.sleep, sys.argv, dict(os.environ))
        bn.run, bn._awaken = fake, None
        time.sleep = lambda s: None
        sys.argv = ["javis_boot_node.py", "--role", role, "--agent", "claude", "--json", "--timeout", "0.5"]
        os.environ.update(extra_env or {})
        out = []
        import io
        import contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = bn.main()
        finally:
            bn.run, bn._awaken, time.sleep, sys.argv = saved[0], saved[1], saved[2], saved[3]
            os.environ.clear()
            os.environ.update(saved[4])
        out = json.loads(buf.getvalue().strip().splitlines()[-1])
        return rc, out, fake

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dept = os.path.join(self.tmp, "교육부")
        os.makedirs(self.dept)
        self.reg = os.path.join(self.tmp, "depts.json")
        json.dump({"depts": {"dept-1": {"socket": "/s/one.sock", "cwd": self.dept}}}, open(self.reg, "w"))
        self.env = {"CYS_SOCKET": "/s/one.sock", "CYS_DEPTS_JSON": self.reg,
                    "CYS_STATE_DIR": os.path.join(self.tmp, "state")}   # 보존 래치를 실 ~/.cys 에 쓰지 않는다

    def test_formation_fills_fresh_master_shell_with_dept_cwd(self):
        # allocate 가 만든 부서장 빈 셸(에이전트 한 번도 없음 · 방금 생성) → 입양-주입이 아니라 승계 기동
        rows = [{"ref": "surface:1", "role": "master", "pid": 111, "seat": "empty", "agent": None,
                 "created": time.time() - 5}]
        rc, out, fake = self._run(rows, "master", self.env)
        launches = [c for c in fake.calls if c[1:2] == ["launch-agent"]]
        self.assertEqual(len(launches), 1, fake.calls)
        self.assertIn("--cwd", launches[0])
        self.assertEqual(launches[0][launches[0].index("--cwd") + 1], self.dept, "부서 폴더가 아니다")
        sends_old = [c for c in fake.calls if c[1:2] == ["send"] and fake.calls.index(c) < fake.calls.index(launches[0])]
        self.assertEqual(sends_old, [], "승계 전에 빈 셸에 주입했다")
        self.assertNotEqual(out.get("surface"), "surface:1", "옛 빈 좌석을 결과 좌석으로 보고")

    def test_d7_fresh_master_shell_unknown_seat_is_taken_over_not_adopted(self):
        # v115r3-d7(D7⑴) 실물 모양: allocate 직후 좌석 사실은 "unknown"(데몬 seat_cache 초기값 · 워치독 틱 전).
        #   종전: empty_seat_action=None → 입양-주입(빈 셸에 각성문 505B) → rc=1 「기동=cso,worker」.
        #   수리: 워치독이 채울 때까지 재조회 → empty → 첫 시도 승계(launch-agent) · 빈 셸 주입 0.
        rows = [{"ref": "surface:1", "role": "master", "pid": 111, "seat": "unknown", "agent": None,
                 "created": time.time() - 1}]
        rc, out, fake = self._run(rows, "master", self.env, seat_seq={"surface:1": ["unknown", "empty"]})
        launches = [i for i, c in enumerate(fake.calls) if c[1:2] == ["launch-agent"]]
        self.assertEqual(len(launches), 1, fake.calls)
        sends_old = [c for c in fake.calls[:launches[0]] if c[1:2] == ["send"]]
        self.assertEqual(sends_old, [], "승계 전에 빈 셸에 주입했다(D7⑴ 재발)")
        self.assertNotEqual(out.get("surface"), "surface:1", "옛 빈 좌석을 결과 좌석으로 보고")
        self.assertTrue(any("unknown" in (l.get("msg") or "") and "empty" in (l.get("msg") or "")
                            for l in out.get("log", [])), "좌석 판정 대기 근거 줄이 없다: %s" % out)

    def test_d7_settle_unknown_seat_pure(self):
        saved = time.sleep
        time.sleep = lambda s: None
        try:
            seq = [_st(seat="unknown"), _st(seat="unknown"), _st(seat="empty")]
            st, why = bn.settle_unknown_seat(_st(seat="unknown"), "master", lambda: seq.pop(0), tick_s=1.0,
                                             max_wait_s=10)
            self.assertEqual(bn.seat_state(st, "master"), "empty")
            self.assertIn("3s", why)
            # 이미 판정된 좌석은 재조회 0(값·사유 그대로)
            calls = []
            st2, why2 = bn.settle_unknown_seat(_st(seat="occupied"), "master", lambda: calls.append(1), max_wait_s=10)
            self.assertEqual((bn.seat_state(st2, "master"), why2, calls), ("occupied", None, []))
            # 상한 안에 안 풀리면 스냅샷 그대로 · 유계(재조회 수 = 상한/틱)
            n = []
            st3, why3 = bn.settle_unknown_seat(_st(seat="unknown"), "master",
                                               lambda: n.append(1) or _st(seat="unknown"), tick_s=1.0, max_wait_s=4)
            self.assertEqual((bn.seat_state(st3, "master"), len(n)), ("unknown", 4))
            self.assertIn("미해소", why3)
            # 에이전트 좌석의 unknown 은 대상 아님(master 지시: unknown ∧ agent None) — 재조회 0
            calls2 = []
            st5, why5 = bn.settle_unknown_seat(_st(seat="unknown", agent="claude"), "master",
                                               lambda: calls2.append(1), max_wait_s=10)
            self.assertEqual((bn.seat_state(st5, "master"), why5, calls2), ("unknown", None, []))
            # 재조회 실패(None)는 직전 스냅샷 유지
            st4, _ = bn.settle_unknown_seat(_st(seat="unknown"), "master", lambda: None, tick_s=1.0, max_wait_s=2)
            self.assertEqual(bn.seat_state(st4, "master"), "unknown")
        finally:
            time.sleep = saved

    def test_dead_agent_seat_in_grace_is_left_alone(self):
        rows = [{"ref": "surface:1", "role": "master", "pid": 111, "seat": "empty", "agent": "claude",
                 "created": time.time() - 30}]
        rc, out, fake = self._run(rows, "master", self.env)
        self.assertEqual(out["result"], "seat_in_grace")
        self.assertEqual(rc, 1)
        acted = [c for c in fake.calls if c[1:2] in (["launch-agent"], ["close-surface"], ["send"])]
        self.assertEqual(acted, [], "유예 안 빈 좌석을 건드렸다")

    def test_b8_worker_dead_shell_after_grace_reaped_then_relaunched(self):
        rows = [{"ref": "surface:3", "role": "worker", "pid": 333, "seat": "empty", "agent": "claude",
                 "created": time.time() - 900}]
        rc, out, fake = self._run(rows, "worker", self.env)
        kinds = [c[1] for c in fake.calls if c[1] in ("close-surface", "launch-agent")]
        self.assertEqual(kinds, ["close-surface", "launch-agent"], fake.calls)
        reap = [c for c in fake.calls if c[1] == "close-surface"][0]
        self.assertEqual(reap[2:], ["surface:3", "--reap"])

    def test_b8_worker_seat_with_queue_is_kept_not_reaped(self):
        # v115-review 발견 1: close-surface --reap 은 데몬이 큐를 무조건 폐기 — 큐 7건 워커 좌석은 보존·기동 0
        rows = [{"ref": "surface:3", "role": "worker", "pid": 333, "seat": "empty", "agent": "claude",
                 "created": time.time() - 900}]
        rc, out, fake = self._run(rows, "worker", self.env, queues={"surface:3": 7})
        acted = [c for c in fake.calls if c[1] in ("close-surface", "launch-agent", "send")]
        self.assertEqual(acted, [], "큐가 찬 워커 좌석을 회수·재기동했다")
        self.assertEqual(rc, 1)
        self.assertEqual(out["result"], "seat_kept_queue_nonempty")
        self.assertTrue(any("seat.kept:queue_nonempty(7)" in (l.get("msg") or "") for l in out.get("log", [])), out)

    def test_b8_kept_seat_two_heartbeats_one_event(self):
        # master#58624550 추가 요구: 보존 좌석이 심박마다 같은 이벤트를 반복하지 않는다 — 2회 연속 → reap 0 · 이벤트 1
        events = []
        saved = bn._seat_event
        bn._seat_event = lambda role, ref, action, cwd: events.append(action) or True
        try:
            for _ in range(2):
                rows = [{"ref": "surface:3", "role": "worker", "pid": 333, "seat": "empty", "agent": "claude",
                         "created": time.time() - 900}]
                rc, out, fake = self._run(rows, "worker", self.env, queues={"surface:3": 7})
                self.assertEqual([c for c in fake.calls if c[1] in ("close-surface", "launch-agent")], [])
        finally:
            bn._seat_event = saved
        self.assertEqual(events, ["seat.kept:queue_nonempty(7)"], events)
        self.assertFalse(os.path.exists(os.path.join(os.path.expanduser("~"), ".cys", "state", "seat-kept",
                                                     "_s_one.sock.json")), "래치가 실 상태 폴더에 샜다")

    def test_b8_worker_seat_queue_empty_reaped_once_launched_once(self):
        rows = [{"ref": "surface:3", "role": "worker", "pid": 333, "seat": "empty", "agent": "claude",
                 "created": time.time() - 900}]
        rc, out, fake = self._run(rows, "worker", self.env, queues={"surface:3": 0})
        self.assertEqual(len([c for c in fake.calls if c[1] == "close-surface"]), 1, fake.calls)
        self.assertEqual(len([c for c in fake.calls if c[1] == "launch-agent"]), 1, fake.calls)
        q = [i for i, c in enumerate(fake.calls) if c[1:3] == ["queue", "list"]]
        r = [i for i, c in enumerate(fake.calls) if c[1] == "close-surface"]
        self.assertTrue(q and q[0] < r[0], "큐 선검사 없이 회수했다")

    def test_b8_worker_seat_revived_before_reap_is_left_alone(self):
        # v115-review 발견 2: 첫 스냅샷 뒤 사람이 그 셸에서 claude 를 띄움 → 재조회에서 occupied → 회수 0
        rows = [{"ref": "surface:3", "role": "worker", "pid": 333, "seat": "empty", "agent": "claude",
                 "created": time.time() - 900}]
        rc, out, fake = self._run(rows, "worker", self.env, flip_on_status=(2, "surface:3"))
        acted = [c for c in fake.calls if c[1] in ("close-surface", "launch-agent")]
        self.assertEqual(acted, [], "재조회에서 산 좌석을 회수했다")
        self.assertEqual(out["result"], "seat_kept_recheck")

    def test_succession_reaps_old_shell_when_queue_empty(self):
        rows = [{"ref": "surface:1", "role": "master", "pid": 111, "seat": "empty", "agent": None,
                 "created": time.time() - 5}]
        rc, out, fake = self._run(rows, "master", self.env)
        kinds = [c[1] for c in fake.calls if c[1] in ("launch-agent", "close-surface")]
        self.assertEqual(kinds, ["launch-agent", "close-surface"], fake.calls)
        self.assertEqual([c for c in fake.calls if c[1] == "close-surface"][0][2:], ["surface:1", "--reap"])

    def test_succession_keeps_old_shell_when_queue_nonempty(self):
        rows = [{"ref": "surface:1", "role": "master", "pid": 111, "seat": "empty", "agent": None,
                 "created": time.time() - 5}]
        rc, out, fake = self._run(rows, "master", self.env, queues={"surface:1": 7})
        self.assertEqual([c for c in fake.calls if c[1] == "close-surface"], [], "큐가 찬 옛 좌석을 회수했다")
        self.assertTrue(any("queue_nonempty(7)" in (l.get("msg") or "") for l in out.get("log", [])), out)

    def test_base_socket_keeps_old_default_cwd(self):
        rows = []
        env = {"CYS_SOCKET": "/s/base.sock", "CYS_DEPTS_JSON": self.reg}
        rc, out, fake = self._run(rows, "cso", env)
        launch = [c for c in fake.calls if c[1:2] == ["launch-agent"]][0]
        self.assertNotIn("--cwd", launch, "본부 소켓에 부서 폴더를 줬다")


class A5BundlePyEnv(unittest.TestCase):
    def _sh(self, path_dirs, cys_py):
        tmp = tempfile.mkdtemp()
        tb = os.path.join(tmp, "tb")
        os.makedirs(tb)
        for t in ("uname", "sed", "readlink", "dirname", "cat", "head", "tr"):
            try:
                os.symlink("/usr/bin/" + t, os.path.join(tb, t))
            except OSError:
                pass
        ef = os.path.join(tmp, "env")
        open(ef, "w").close()
        env = {"PATH": ":".join([tb] + path_dirs), "CYS_PACK_DIR": PACK, "CLAUDE_ENV_FILE": ef,
               "HOME": tmp}
        r = subprocess.run(["/bin/sh", "-c", '. "$0/hooks/_lib.sh"; CYS_PY="$1"; cys_export_bundle_py_env',
                            PACK, cys_py], capture_output=True, text=True, env=env, timeout=30)
        return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "", open(ef).read()

    @unittest.skipUnless(sys.platform == "darwin", "맥 전용 분기")
    def test_stub_only_mac_gets_bundle_python(self):
        tmp = tempfile.mkdtemp()
        py = os.path.join(tmp, "app", "Resources", "runtime", "python", "bin", "python3")
        os.makedirs(os.path.dirname(py))
        open(py, "w").write("#!/bin/sh\n")
        os.chmod(py, 0o755)
        n, body = self._sh(["/bin", "/usr/sbin"], py)
        self.assertEqual(n, "2")
        self.assertIn("export CYS_PY=", body)
        self.assertIn("runtime/python/bin", body)
        # 진짜 파이썬이 PATH 에 있으면 세션 python3 는 건드리지 않는다
        real = os.path.join(tmp, "real")
        os.makedirs(real)
        open(os.path.join(real, "python3"), "w").write("#!/bin/sh\n")
        os.chmod(os.path.join(real, "python3"), 0o755)
        n2, body2 = self._sh([real, "/bin"], py)
        self.assertEqual((n2, body2), ("0", ""))
        # 번들이 아닌 CYS_PY 면 비발동
        n3, body3 = self._sh(["/bin"], os.path.join(real, "python3"))
        self.assertEqual((n3, body3), ("0", ""))

    def test_session_start_calls_it(self):
        s = open(os.path.join(PACK, "hooks", "session-start.sh"), encoding="utf-8").read()
        self.assertIn("cys_export_bundle_py_env", s)


class A5A2DirectiveContract(unittest.TestCase):
    def _d(self, n):
        return open(os.path.join(PACK, "directives", n), encoding="utf-8").read()

    def test_cso_lines(self):
        t = self._d("CSO_DIRECTIVE.md")
        self.assertIn("부서장 좌석 회수 = 부팅 유예 뒤", t)
        self.assertIn("부서 편성이 띄운다", t)
        self.assertIn("사용자 환경 변경 금지", t)
        self.assertIn("~/.local/bin", t)

    def test_worker_line(self):
        self.assertIn("사용자 환경 변경 금지", self._d("WORKER_DIRECTIVE.md"))


class B2RecapDefault(unittest.TestCase):
    def _pf(self, targets, home=None):
        import javis_preflight as pf
        p = pf.Preflight(True, set())
        saved = pf.resolve_registration_targets, os.environ.get("HOME")
        pf.resolve_registration_targets = lambda: (targets, None)
        if home:
            os.environ["HOME"] = home          # 대상 술어가 ~ 를 가짜 홈으로 풀게(실 홈 무접촉)
        try:
            p.c83_recap_default()
        finally:
            pf.resolve_registration_targets = saved[0]
            if saved[1] is not None:
                os.environ["HOME"] = saved[1]
        return [r for r in p.results if "C83" in json.dumps(r, ensure_ascii=False, default=str)]

    def test_seeds_false_and_respects_user_value(self):
        tmp = tempfile.mkdtemp()
        a, b = (os.path.join(tmp, ".cys", "claude", "settings.json"),
                os.path.join(tmp, ".cys", "claude-b", "settings.json"))
        os.makedirs(os.path.dirname(a))
        os.makedirs(os.path.dirname(b))
        json.dump({"hooks": {}}, open(a, "w"))
        json.dump({"awaySummaryEnabled": True}, open(b, "w"))
        self._pf([a, b], home=tmp)
        self.assertIs(json.load(open(a))["awaySummaryEnabled"], False)
        self.assertIn("hooks", json.load(open(a)), "다른 키를 잃었다")
        self.assertIs(json.load(open(b))["awaySummaryEnabled"], True, "사용자 값을 덮었다")

    def test_registered_in_run_order(self):
        src = open(os.path.join(BIN, "javis_preflight.py"), encoding="utf-8").read()
        self.assertIn("self.c83_recap_default,", src)

    def test_personal_profile_untouched(self):
        # v115-review 발견 5: 개발 맥 개인 프로필(~/.claude*)엔 기입하지 않는다 — 격리 프로필만 기입(대조군)
        tmp = tempfile.mkdtemp()
        personal = [os.path.join(tmp, ".claude", "settings.json"), os.path.join(tmp, ".claude-work", "settings.json")]
        iso = os.path.join(tmp, ".cys", "claude", "settings.json")
        for f in personal + [iso]:
            os.makedirs(os.path.dirname(f))
            json.dump({"hooks": {}}, open(f, "w"))
        self._pf(personal + [iso], home=tmp)
        for f in personal:
            self.assertNotIn("awaySummaryEnabled", json.load(open(f)), "개인 프로필에 기입했다: %s" % f)
        self.assertIs(json.load(open(iso))["awaySummaryEnabled"], False, "격리 프로필 기입 안 됨(대조군)")


class D2SkillProfiles(unittest.TestCase):
    """★D2(1.1.5 6차) dept-by-chat 스킬 등록 + 스킬 프로필 발견 SOT.

    무엇이 깨졌었나: 스킬 심링크 검사(C26·C27·C29)가 제 손으로 `$HOME/.claude*` 만 훑었다.
    좌석이 실제로 읽는 프로필은 `~/.cys/claude`(본부)·`~/.cys/claude-<부서>`(부서)라, 스킬
    53종이 개인 프로필에만 걸리고 좌석에서는 한 종도 안 보였다 — 그 위에 dept-by-chat 은
    어느 목록에도 없어 본부 master 가 「Unknown skill: dept-by-chat」으로 대화 폴백했다
    (2026-09-22 윈 실기 · 914 축3 실측: `~/.cys/claude/skills` 폴더 자체가 없었다).
    """

    def test_dept_by_chat_is_in_a_linked_list(self):
        import javis_preflight as pf
        linked = set(pf.HARNESS_SKILLS) | set(pf.VIDEO_SKILLS) | set(pf.APPBUILD_SKILLS) | set(pf.WORK_SKILLS)
        self.assertIn("dept-by-chat", linked,
                      "dept-by-chat 이 어느 심링크 목록에도 없다 — 좌석에 Skill 로 등록되지 않는다")
        self.assertTrue(os.path.isfile(os.path.join(PACK, "skills", "dept-by-chat", "SKILL.md")),
                        "실체(pack/skills/dept-by-chat/SKILL.md)가 없다")

    def test_profile_sot_covers_seat_profiles(self):
        import javis_preflight as pf
        tmp = tempfile.mkdtemp()
        seat = os.path.join(tmp, ".cys", "claude")          # 좌석(본부)
        dept = os.path.join(tmp, ".cys", "claude-default-dept-1")  # 좌석(부서)
        personal = os.path.join(tmp, ".claude")             # 개인
        for d in (seat, dept, personal):
            os.makedirs(d)
        saved = pf.discover_claude_settings
        pf.discover_claude_settings = lambda: [os.path.join(d, "settings.json")
                                               for d in (personal, seat, dept)]
        try:
            profs = pf.discover_skill_profiles()
        finally:
            pf.discover_claude_settings = saved
        for d in (seat, dept, personal):
            self.assertIn(d, profs, "스킬 프로필 SOT 가 %s 를 빠뜨린다" % d)

    def test_link_checks_use_the_shared_sot(self):
        # 좁은 자기 home-glob 이 되살아나면(같은 결함 계열) 여기서 적색이 된다.
        src = open(os.path.join(BIN, "javis_preflight.py"), encoding="utf-8").read()
        self.assertNotIn('if (d == ".claude" or d.startswith(".claude-"))', src,
                         "스킬 링크 검사가 좁은 home-glob 으로 되돌아갔다(좌석 프로필 미도달)")
        self.assertGreaterEqual(src.count("discover_skill_profiles()"), 4,
                                "공용 SOT 소비처가 줄었다(C26·C27·C29·보드 카탈로그 4곳)")

    def test_guidance_does_not_use_bare_python3(self):
        # ★D3 와 같은 축: CLT 없는 맥에서 맨 `python3` 는 /usr/bin 스텁이라 안내대로 치면 설치 창만 뜬다.
        src = open(os.path.join(BIN, "javis_dept_request.py"), encoding="utf-8").read()
        hook = src[src.index("def _hook_lines") if "def _hook_lines" in src else 0:]
        self.assertNotIn('python3 \\"%s\\"', hook, "부서 안내문이 맨 python3 를 되살렸다")
        self.assertIn("sys.executable", src, "해석기 절대경로(sys.executable) 사용 부재")


class B3DrainIssuer(unittest.TestCase):
    OLD = ("재시작 단추를 누른", "재시작 단추를 눌러 발신")
    NEW = "새 판 설치"

    def test_no_button_only_issuer_left(self):
        files = [os.path.join(PACK, "directives", n) for n in
                 ("MASTER_DIRECTIVE.md", "CEO_TEMPLATE.md", "CSO_DIRECTIVE.md", "WORKER_DIRECTIVE.md")]
        files += [os.path.join(PACK, "hooks", "session-start.sh"), os.path.join(REPO, "src", "bin", "cys.rs")]
        for f in files:
            with open(f, encoding="utf-8") as fh:
                t = fh.read()
            for o in self.OLD:
                self.assertNotIn(o, t, "%s 에 옛 발신 주체 문구" % f)
            self.assertIn(self.NEW, t, "%s 에 새 문구 없음" % f)


if __name__ == "__main__":
    unittest.main(verbosity=1)
