#!/usr/bin/env python3
"""R-B1(재부팅 뒤 빈 셸이 부서장 역할을 먼저 쥔다 · VM r4 §4) + D1 #5 — 편성 쪽 처방 행위 시험.

고정하는 것(HANDOFF-v116-pack §1·§3 · master#5c9ceb39 판정 A):
  P2  데몬 자동 복원이 도는 동안(running·retry_wait) 편성은 좌석을 한 자리도 세우지 않는다 → partial:restoring
      · 복원이 끝나면(done) 그때 세운다 · 칸 없는 옛 데몬은 데몬 나이로 갈음 · 판독 불가면 종전 흐름
  P1  편성 CLI 는 CYS_NO_AUTOSTART=1 로 돈다(심박이 죽은 부서 데몬을 cys-dept launch 밖에서 되살리지 않는다)
  P1′ 무응답 부서 = cys-dept launch 로 되살림 — 묘비·묘비 판독 불가·소진·다른 부서 직후·자원 hard 면 안 함 ·
      launch 에는 봉인 env·CYS_SOCKET·CYS_ROLE 을 넘기지 않는다 · 사람 말 알림
  P3  master 자리 cwd 미지정 = 부서 폴더 · 자식 cwd 상속 = 앉은 master 좌석 우선 · 홈 폴더 상속 0
  D1#4 편성이 매 틱 빈 좌석 회수를 부르고 회수분을 사람 말로 알린다
전부 스텁(라이브 데몬·소켓 무접촉). 실행: python3 -m unittest tests.test_v116_rb1_formation (cwd cysjavis-pack/bin)
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import javis_formation as fm  # noqa: E402

SEAMS = ("gate_check", "_installed_clis", "_live_roles", "_resource_ok", "_boot_node",
         "_ensure_master_seat", "_feed", "_emit_evt", "_master_seat_cwd", "_daemon_down",
         "_wait_restore_settled", "_reap_orphans", "_revive_dept", "_run", "_dept_registry_cwd",
         "_dept_tombstones", "_dept_name_for_socket", "_status_obj")


class _Base(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(fm, k) for k in SEAMS}
        self.saved_env = dict(os.environ)
        self.tmp = tempfile.mkdtemp()
        os.environ["CYS_STATE_DIR"] = self.tmp
        self.feeds, self.boots, self.masters = [], [], []
        fm.gate_check = lambda: True
        fm._installed_clis = lambda: {"claude"}
        fm._live_roles = lambda socket=None, require_live_agent=True: set()
        fm._resource_ok = lambda socket=None: True
        fm._boot_node = lambda role, socket, cwd=None, timeout=200: (self.boots.append(role) or (True, "stub"))
        fm._ensure_master_seat = lambda socket, cwd: (self.masters.append(cwd) or (True, "stub"))
        fm._feed = lambda title, body, kind="formation": self.feeds.append((kind, title, body))
        fm._emit_evt = lambda evt, fields: None
        fm._master_seat_cwd = lambda socket: None
        fm._daemon_down = lambda socket: False
        fm._wait_restore_settled = lambda socket, **kw: (True, None)
        fm._reap_orphans = lambda socket: None

        def _no_cys(argv, timeout=30):
            raise AssertionError("실 cys 호출: %r" % (argv,))
        fm._run = _no_cys

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(fm, k, v)
        os.environ.clear()
        os.environ.update(self.saved_env)
        shutil.rmtree(self.tmp, ignore_errors=True)


class P2RestoreVerdict(unittest.TestCase):
    def test_table(self):
        now = 1000.0
        cases = [
            ({"daemon": {"auto_restore": "running", "started_at": 900}}, "wait"),
            ({"daemon": {"auto_restore": "retry_wait", "started_at": 900}}, "wait"),
            ({"daemon": {"auto_restore": "running"}}, "wait"),                  # 나이 모름 = 기다림(상한은 대기 루프)
            ({"daemon": {"auto_restore": "running", "started_at": 1}}, "go"),   # Fable M-3: 999s = 걸린 복원 → 진행
            ({"daemon": {"auto_restore": "done", "started_at": 999}}, "go"),
            ({"daemon": {"auto_restore": "off", "started_at": 999}}, "go"),
            ({"daemon": {"started_at": 995}}, "wait"),          # 옛 데몬 · 5초
            ({"daemon": {"started_at": 800}}, "go"),            # 옛 데몬 · 200초
            ({}, "go"), (None, "go"), ({"daemon": "x"}, "go"),
        ]
        for obj, want in cases:
            self.assertEqual(fm.restore_settle_verdict(obj, now)[0], want, obj)

    def test_wait_until_done(self):
        seq = ["running", "retry_wait", "done"]
        t = [0.0]
        st = lambda s: {"daemon": {"auto_restore": seq.pop(0) if len(seq) > 1 else seq[0]}}

        def sleep(x):
            t[0] += x
        ok, why = fm._wait_restore_settled("/s", max_wait=100, sleep=sleep, clock=lambda: t[0], status_fn=st)
        self.assertTrue(ok)
        self.assertIn("대기 뒤 진행", why)

    def test_wait_gives_up_bounded(self):
        t = [0.0]

        def sleep(x):
            t[0] += x
        ok, why = fm._wait_restore_settled("/s", max_wait=30, sleep=sleep, clock=lambda: t[0],
                                           status_fn=lambda s: {"daemon": {"auto_restore": "running"}})
        self.assertFalse(ok)
        self.assertLessEqual(t[0], 30 + fm.RESTORE_POLL_S)

    def test_no_wait_when_done(self):
        slept = []
        ok, why = fm._wait_restore_settled("/s", sleep=slept.append, status_fn=lambda s: {"daemon": {"auto_restore": "done"}})
        self.assertEqual((ok, why, slept), (True, None, []))


class P2EnsureHoldsWhileRestoring(_Base):
    def test_restoring_spawns_nothing(self):
        # R-B1 L3·L4 재현 조건: 막 뜬 데몬(로스터 비어 있음) + 자동 복원 진행 중 → 편성 좌석 0
        fm._wait_restore_settled = lambda socket, **kw: (False, "데몬 자동 복원 running — 대기에도 안 끝남")
        state, detail = fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual(state, "partial:restoring")
        self.assertEqual((self.boots, self.masters), ([], []), "복원 중에 좌석을 세웠다(R-B1 재발)")

    def test_settled_then_spawns(self):
        state, _ = fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual(self.masters, [None])
        self.assertEqual(sorted(self.boots), ["cso", "worker"])

    def test_wait_happens_before_roster_read(self):
        order = []
        fm._wait_restore_settled = lambda socket, **kw: (order.append("wait") or (True, None))
        fm._live_roles = lambda socket=None, require_live_agent=True: (order.append("roster") or {"master", "cso", "worker"})
        fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual(order[0], "wait", order)


class D14ReapHook(_Base):
    def test_reap_called_every_tick_even_when_complete(self):
        calls = []
        fm._reap_orphans = lambda socket: (calls.append(socket) or {"reaped": ["surface:4"], "kept": []})
        fm._live_roles = lambda socket=None, require_live_agent=True: {"master", "cso", "worker"}
        fm._dept_name_for_socket = lambda socket, depts=None: "행정부"
        state, _ = fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual(state, "complete")
        self.assertEqual(calls, ["/s/dept-3.sock"])
        reap = [f for f in self.feeds if f[1] == "빈 창 정리"]
        self.assertEqual(len(reap), 1, self.feeds)
        self.assertIn("surface:4", reap[0][2])
        self.assertIn("10분", reap[0][2])

    def test_no_feed_when_nothing_reaped(self):
        fm._reap_orphans = lambda socket: {"reaped": [], "kept": [["surface:9", "root_not_bare_shell"]]}
        fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual([f for f in self.feeds if f[1] == "빈 창 정리"], [])

    def test_restoring_skips_reap(self):
        calls = []
        fm._reap_orphans = lambda socket: calls.append(socket)
        fm._wait_restore_settled = lambda socket, **kw: (False, "running")
        fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual(calls, [])


class P1Seal(_Base):
    def test_cmd_ensure_seals_autostart(self):
        seen = {}
        saved = fm.ensure
        fm.ensure = lambda socket=None, cwd=None, force_surface=False: (
            seen.setdefault("v", os.environ.get("CYS_NO_AUTOSTART")) and ("complete", "stub"))
        try:
            os.environ.pop("CYS_NO_AUTOSTART", None)
            import io
            import contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                fm._cmd_ensure(["--socket", "/s/x.sock", "--json"])
        finally:
            fm.ensure = saved
        self.assertEqual(seen.get("v"), "1")

    def test_cys_env_seals(self):
        env = fm._cys_env("/s/x.sock")
        self.assertEqual((env["CYS_SOCKET"], env["CYS_NO_AUTOSTART"]), ("/s/x.sock", "1"))


class P1ReviveDept(_Base):
    def setUp(self):
        super().setUp()
        self.launches = []
        self.real_sub_run = fm.subprocess.run

        def fake_run(argv, **kw):
            self.launches.append((list(argv), kw.get("env") or {}))

            class R:
                returncode = 0
                stdout = "ok"
                stderr = ""
            return R()
        fm.subprocess.run = fake_run
        fm._dept_name_for_socket = lambda socket, depts=None: "행정부"
        fm._dept_tombstones = lambda: set()
        os.environ.update({"CYS_NO_AUTOSTART": "1", "CYS_SOCKET": "/s/dept-3.sock", "CYS_ROLE": "cso"})
        fm._daemon_down = lambda socket: True

    def tearDown(self):
        fm.subprocess.run = self.real_sub_run
        super().tearDown()

    def test_revives_via_cys_dept_launch_without_seal(self):
        state, detail = fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual(state, "partial:revived", detail)
        self.assertEqual(len(self.launches), 1)
        argv, env = self.launches[0]
        self.assertEqual(argv[-2:], ["launch", "행정부"])
        for k in ("CYS_NO_AUTOSTART", "CYS_SOCKET", "CYS_ROLE"):
            self.assertNotIn(k, env, "launch 에 %s 가 샜다" % k)
        self.assertEqual((self.boots, self.masters), ([], []), "되살린 틱에 좌석을 세웠다")
        self.assertTrue([f for f in self.feeds if f[1] == fm.REVIVE_FEED_TITLE and "다시 켰습니다" in f[2]])

    def test_tombstoned_or_unknown_not_revived(self):
        for tombs in ({"행정부"}, None):
            self.launches.clear()
            fm._dept_tombstones = lambda t=tombs: t
            state, _ = fm.ensure(socket="/s/dept-3.sock")
            self.assertEqual(state, "partial:daemon-down")
            self.assertEqual(self.launches, [], tombs)

    def test_bounded_three_then_exhausted(self):
        for i in range(5):
            fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual(len(self.launches), fm.REVIVE_MAX)

    def test_one_dept_per_tick(self):
        fm.ensure(socket="/s/dept-3.sock")
        fm._dept_name_for_socket = lambda socket, depts=None: "홍보부"
        state, detail = fm.ensure(socket="/s/dept-2.sock")
        self.assertEqual(state, "partial:daemon-down")
        self.assertIn("다음 틱", detail)
        self.assertEqual(len(self.launches), 1)

    def test_resource_hard_holds(self):
        fm._resource_ok = lambda socket=None: False
        state, _ = fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual((state, self.launches), ("partial:daemon-down", []))

    def test_not_a_dept_falls_through(self):
        fm._dept_name_for_socket = lambda socket, depts=None: None
        fm._daemon_down = lambda socket: True
        fm.ensure(socket="/s/unknown.sock")
        self.assertEqual(self.launches, [])

    def test_failure_feed(self):
        def fail_run(argv, **kw):
            self.launches.append((argv, kw.get("env")))

            class R:
                returncode = 1
                stdout = ""
                stderr = "boom"
            return R()
        fm.subprocess.run = fail_run
        state, detail = fm.ensure(socket="/s/dept-3.sock")
        self.assertEqual(state, "partial:daemon-down")
        self.assertTrue([f for f in self.feeds if "실패했습니다" in f[2]])


class P3Cwd(_Base):
    def test_child_cwd_prefers_occupied_master_and_skips_home(self):
        home = os.path.expanduser("~")
        dept = "/Users/u/Desktop/CYSjavis/행정부"
        st = {"surfaces": [
            {"surface_id": 9, "role": "master", "cwd": home, "seat": "empty"},
            {"surface_id": 10, "role": "master", "cwd": dept, "seat": "occupied"}]}
        self.assertEqual(fm._master_seat_cwd_from_status(st), dept)
        self.assertIsNone(fm._master_seat_cwd_from_status({"surfaces": [st["surfaces"][0]]}))

    def test_master_seat_uses_dept_folder_when_cwd_missing(self):
        fm._ensure_master_seat = self.saved["_ensure_master_seat"]
        fm._live_roles = lambda socket=None, require_live_agent=True: set()
        fm._dept_registry_cwd = lambda socket: "/Users/u/Desktop/CYSjavis/행정부"
        ran = []
        fm._run = lambda argv, timeout=30: (ran.append(argv) or (0, "", ""))
        fm._boot_node = lambda role, socket, cwd=None, timeout=200: (True, cwd)
        ok, cwd = fm._ensure_master_seat("/s/dept-3.sock", None)
        self.assertEqual(ran[0][-2:], ["--cwd", "/Users/u/Desktop/CYSjavis/행정부"], ran)
        self.assertEqual(cwd, "/Users/u/Desktop/CYSjavis/행정부")


class M4WindowsTombstones(unittest.TestCase):
    def test_nt_reads_localappdata(self):
        tmp = tempfile.mkdtemp()
        saved = (fm.os.name, dict(os.environ))
        try:
            os.makedirs(os.path.join(tmp, "cys"))
            json.dump({"dept_tombstones": ["교육부"]}, open(os.path.join(tmp, "cys", "dept_tombstones.json"), "w"))
            os.environ["LOCALAPPDATA"] = tmp
            fm.os.name = "nt"
            self.assertEqual(fm._dept_tombstones(), {"교육부"})
            os.environ.pop("LOCALAPPDATA")
            self.assertIsNone(fm._dept_tombstones())
        finally:
            fm.os.name = saved[0]
            os.environ.clear(); os.environ.update(saved[1])
            shutil.rmtree(tmp, ignore_errors=True)


class DeptName(unittest.TestCase):
    def test_socket_match_and_name_rule(self):
        depts = {"dept-3": {"socket": "/h/.local/state/cys-dept-dept-3/cys.sock"}, "dept-9": {}}
        self.assertEqual(fm._dept_name_for_socket("/h/.local/state/cys-dept-dept-3/cys.sock", depts), "dept-3")
        self.assertEqual(fm._dept_name_for_socket("/h/.local/state/cys-dept-dept-9/cys.sock", depts), "dept-9")
        self.assertIsNone(fm._dept_name_for_socket("/h/.local/state/cys/cys.sock", depts))
        self.assertIsNone(fm._dept_name_for_socket(None, depts))


if __name__ == "__main__":
    unittest.main()
