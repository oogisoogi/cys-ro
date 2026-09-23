#!/usr/bin/env python3
"""D1 #4 — claude 가 죽고 역할 없이 남은 빈 셸 좌석 회수(유예 2분 · master 판정 A-2) 행위 시험.

증상(D1-daemon.md:44): 부서 좌석의 claude 가 죽으면 데드맨(61s)이 역할만 걷고 셸은 남는다 → 편성 심박이
새 좌석을 세운 뒤에도 옛 빈 셸이 영구히 누적된다.

이 시험이 고정하는 것(4군 ④ = 산 좌석을 닫는 경로 0 이 핵심):
  P   대상 1건(역할 없음 · 에이전트 메타 · seat empty · 유예 경과 · 큐 0 · 부서 폴더 안 · 뿌리 = 셸·자식 0) → 회수 1
  N1~N7 조건 하나씩 거짓 → 회수 0
  R1  닫기 직전 재조회에서 좌석이 찼다(사람이 claude 를 다시 띄움) → 회수 0
  R2  재조회에서 pid 가 바뀌었다(같은 번호의 다른 좌석) → 회수 0
  L1  산 claude 좌석(뿌리 = claude 자신 · seat 가 empty 로 잘못 보이는 경우 · agent_alive None/False) → 회수 0
  W   ps 가 없는 OS(윈도) → 회수 0
  Q   status 는 큐 0 이지만 실제 큐 목록에 남아 있음 → 회수 0
  S   status·list 조회 실패 → 아무것도 안 함

전부 가짜 입력(주입)으로 돈다 — 라이브 데몬·소켓 무접촉. 실행: python3 -m unittest tests.test_d1_4_orphan_reap (cwd cysjavis-pack/bin)
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import javis_boot_node as bn  # noqa: E402

DEPT = "/Users/u/Desktop/CYSjavis/행정부"
GRACE = 120.0


def seat(ref="surface:4", **kw):
    s = {"surface_ref": ref, "role": None, "agent": "claude", "agent_alive": False,
         "seat": "empty", "idle_secs": 300, "queue_depth": 0, "exited": False,
         "cwd": DEPT + "/workers/w1"}
    s.update(kw)
    return s


class FakeWorld:
    """cys status / cys list / ps / pgrep / cys queue list / cys close-surface 가짜."""

    def __init__(self, surfaces, pids, comm=None, children=None, queue=None, second=None):
        self.surfaces = surfaces
        self.pids = pids                      # ref → pid
        self.comm = comm or {}                # pid → ps comm 출력
        self.children = children or {}        # pid → 자식 있음(bool)
        self.queue = queue or {}              # ref → 큐 행 수
        self.second = second                  # 두 번째 조회부터 쓸 (surfaces, pids)
        self.status_calls = 0
        self.closed = []
        self.calls = []

    def status(self):
        self.status_calls += 1
        if self.second is not None and self.status_calls >= 2:
            return {"surfaces": self.second[0]}
        return {"surfaces": self.surfaces}

    def list_probe(self):
        pids = self.pids
        if self.second is not None and self.status_calls >= 2:
            pids = self.second[1]
        return True, [{"surface_ref": r, "role": None, "pid": p, "exited": False} for r, p in pids.items()]

    def run(self, args, timeout=15):
        self.calls.append(list(args))
        if args[:2] == ["ps", "-o"]:
            pid = int(args[-1])
            c = self.comm.get(pid)
            return (0, c + "\n", "") if c is not None else (1, "", "")
        if args[0] == "pgrep":
            pid = int(args[-1])
            return (0, "999\n", "") if self.children.get(pid) else (1, "", "")
        if args[:3] == ["cys", "queue", "list"]:
            ref = args[-1]
            n = self.queue.get(ref, 0)
            return 0, "".join("q%d\tx\ty\tz\n" % i for i in range(n)), ""
        if args[:2] == ["cys", "close-surface"]:
            self.closed.append(args[2])
            return 0, "", ""
        return 1, "", "unexpected"


def reap(world, os_name="posix"):
    return bn.reap_orphan_seats(
        socket="/tmp/x.sock", now=None, grace=GRACE, dept_cwd=DEPT,
        status_fn=world.status, list_fn=world.list_probe, runner=world.run, os_name=os_name)


class OrphanVerdict(unittest.TestCase):
    def test_P_target(self):
        ok, why = bn.orphan_seat_verdict(seat(), DEPT, GRACE)
        self.assertTrue(ok, why)

    def test_N_each_condition_false(self):
        cases = {
            "N1 역할 있음": seat(role="worker"),
            "N2 에이전트 메타 없음(사용자 평범한 창)": seat(agent=None),
            "N3 좌석 참(자손 있음)": seat(seat="occupied"),
            "N3b 좌석 미상": seat(seat="unknown"),
            "N4 유예 안(idle 119)": seat(idle_secs=119),
            "N5 큐 남음": seat(queue_depth=1),
            "N6 부서 폴더 밖(홈)": seat(cwd="/Users/u"),
            "N6b 부서 폴더 접두만 같은 형제": seat(cwd=DEPT + "2/workers/w1"),
            "N7 이미 닫힘": seat(exited=True),
            "N8 idle 칸 없음": seat(idle_secs=None),
        }
        for name, s in cases.items():
            ok, _ = bn.orphan_seat_verdict(s, DEPT, GRACE)
            self.assertFalse(ok, name)

    def test_dept_cwd_unknown_never_targets(self):
        ok, _ = bn.orphan_seat_verdict(seat(), None, GRACE)
        self.assertFalse(ok)

    def test_agent_alive_not_used(self):
        # 퇴행 대조: agent_alive 가 None/False/True 무엇이든 판정은 seat·뿌리 사실로만
        for v in (None, False, True):
            ok, _ = bn.orphan_seat_verdict(seat(agent_alive=v), DEPT, GRACE)
            self.assertTrue(ok, v)


class OrphanReap(unittest.TestCase):
    def test_P_reaps_one(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "-zsh"})
        out = reap(w)
        self.assertEqual(w.closed, ["surface:4"])
        self.assertEqual(out["reaped"], ["surface:4"])

    def test_live_seats_untouched(self):
        live = [seat("surface:5", role="worker", seat="occupied", agent_alive=None),
                seat("surface:6", role="master", seat="empty", agent=None),   # 부서 만들기 빈 셸 master(제품 정책)
                seat("surface:7", role=None, agent=None)]                      # 사용자가 연 평범한 창
        w = FakeWorld(live, {"surface:5": 5, "surface:6": 6, "surface:7": 7},
                      comm={5: "-zsh", 6: "-zsh", 7: "-zsh"})
        reap(w)
        self.assertEqual(w.closed, [])

    def test_L1_live_root_claude_misread_as_empty(self):
        # 뿌리 = claude 자신(new-surface --cmd claude) · 자식 0 순간이라 데몬 seat=empty · 역할은 데드맨 오판으로 걷힘
        w = FakeWorld([seat(agent_alive=None)], {"surface:4": 4001}, comm={4001: "/usr/local/bin/claude"})
        reap(w)
        self.assertEqual(w.closed, [], "산 claude 좌석을 닫았다(4군 ④)")

    def test_root_shell_with_child_kept(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "zsh"}, children={4001: True})
        reap(w)
        self.assertEqual(w.closed, [])

    def test_ps_failure_kept(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={})
        reap(w)
        self.assertEqual(w.closed, [])

    def test_R1_recheck_seat_filled(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "-zsh"},
                      second=([seat(seat="occupied")], {"surface:4": 4001}))
        reap(w)
        self.assertEqual(w.closed, [])

    def test_R2_recheck_pid_changed(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "-zsh", 4002: "-zsh"},
                      second=([seat()], {"surface:4": 4002}))
        reap(w)
        self.assertEqual(w.closed, [])

    def test_Q_real_queue_nonempty(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "-zsh"}, queue={"surface:4": 2})
        reap(w)
        self.assertEqual(w.closed, [])

    def test_W_windows_off(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "-zsh"})
        out = reap(w, os_name="nt")
        self.assertEqual(w.closed, [])
        self.assertEqual(w.status_calls, 0)
        self.assertEqual(out.get("skipped"), "windows")

    def test_S_status_unavailable(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "-zsh"})
        w.status = lambda: None
        out = reap(w)
        self.assertEqual(w.closed, [])
        self.assertEqual(out.get("skipped"), "status_unavailable")

    def test_list_unavailable(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "-zsh"})
        w.list_probe = lambda: (False, [])
        out = reap(w)
        self.assertEqual(w.closed, [])
        self.assertEqual(out.get("skipped"), "list_unavailable")

    def test_dept_cwd_unknown_skips(self):
        w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "-zsh"})
        out = bn.reap_orphan_seats(socket="/tmp/x.sock", grace=GRACE, dept_cwd=None,
                                   status_fn=w.status, list_fn=w.list_probe, runner=w.run,
                                   os_name="posix", registry_cwd_fn=lambda s: None)
        self.assertEqual(w.closed, [])
        self.assertEqual(out.get("skipped"), "no_dept_cwd")

    def test_M1_user_shell_from_env_is_a_shell(self):
        old = os.environ.get("SHELL")
        os.environ["SHELL"] = "/opt/homebrew/bin/nu"
        try:
            w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "/opt/homebrew/bin/nu"})
            reap(w)
            self.assertEqual(w.closed, ["surface:4"], "사용자 셸(nu) 뿌리를 셸로 못 봤다")
        finally:
            if old is None:
                os.environ.pop("SHELL", None)
            else:
                os.environ["SHELL"] = old

    def test_M1_shell_env_set_to_agent_never_counts(self):
        old = os.environ.get("SHELL")
        os.environ["SHELL"] = "/usr/local/bin/claude"
        try:
            w = FakeWorld([seat()], {"surface:4": 4001}, comm={4001: "claude"})
            reap(w)
            self.assertEqual(w.closed, [], "SHELL=claude 로 산 claude 뿌리를 셸로 봤다")
        finally:
            if old is None:
                os.environ.pop("SHELL", None)
            else:
                os.environ["SHELL"] = old

    def test_m2_nfd_korean_folder_and_symlink_match(self):
        import tempfile
        import unicodedata
        base = tempfile.mkdtemp()
        dept = os.path.join(base, unicodedata.normalize("NFC", "행정부"))
        os.makedirs(os.path.join(dept, "workers", "w1"))
        nfd = os.path.join(base, unicodedata.normalize("NFD", "행정부"), "workers", "w1")
        ok, why = bn.orphan_seat_verdict(seat(cwd=nfd), dept, GRACE)
        self.assertTrue(ok, why)
        link = base + "-link"
        os.symlink(base, link)
        try:
            ok, why = bn.orphan_seat_verdict(seat(cwd=os.path.join(link, "행정부", "workers", "w1")), dept, GRACE)
            self.assertTrue(ok, why)
        finally:
            os.unlink(link)

    def test_grace_env_default(self):
        old = os.environ.pop(bn.SEAT_ORPHAN_GRACE_ENV, None)
        try:
            self.assertEqual(bn.seat_orphan_grace_s(), 120.0)
            os.environ[bn.SEAT_ORPHAN_GRACE_ENV] = "-5"
            self.assertEqual(bn.seat_orphan_grace_s(), 120.0)
            os.environ[bn.SEAT_ORPHAN_GRACE_ENV] = "abc"
            self.assertEqual(bn.seat_orphan_grace_s(), 120.0)
            os.environ[bn.SEAT_ORPHAN_GRACE_ENV] = "30"
            self.assertEqual(bn.seat_orphan_grace_s(), 30.0)
        finally:
            os.environ.pop(bn.SEAT_ORPHAN_GRACE_ENV, None)
            if old is not None:
                os.environ[bn.SEAT_ORPHAN_GRACE_ENV] = old


if __name__ == "__main__":
    unittest.main()
