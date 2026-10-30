#!/usr/bin/env python3
"""TICKET=cysr-1111-chromeverify 재현 시험 — 통과 = 「결함이 재현됐다」. 제품 코드 무수정 · test_computer_control.py 더블 재사용.
실행: python3 chromeverify-probe/test_probe.py  (임시 HOME · 임시 상태 · 외부 명령 전부 더블)"""
import importlib.util, json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "cysjavis-pack", "bin", "tests", "test_computer_control.py")
spec = importlib.util.spec_from_file_location("tcc", P)
tcc = importlib.util.module_from_spec(spec)
sys.modules["tcc"] = tcc
spec.loader.exec_module(tcc)


class Probe(tcc.TestChromeEnable):
    def next_process(self, **probes):
        """새 프로세스 흉내: 전역 표지·시험 차례 초기화 · 연결 파일은 이미 있음."""
        self.m.CHROME_IN_JOB.clear()
        for k in [k for k in vars(self.m) if k.startswith("_seq_")]:
            setattr(self.m, k, 0)
        open(self.act_log, "w").close()
        self.m._nmh_ok = lambda plat, ud: True
        self.set_probes(**probes)

    def st(self):
        return self.m._load_chrome_state()

    def test_P1_many_windows_debt_never_clears_after_user_followed_guidance(self):
        self.win_restart_setup(chrome_running=[True], windows=2)
        _, a, _ = self.run_cli("chrome-enable")
        self.assertIn("크롬 창이 2개 열려", a["say"])
        print("\nP1 1회차:", a["pending"], "pending_seat", self.st().get("pending_seat_restart"))
        for i in (2, 3):      # 사용자는 안내대로 ⋮ 종료 → 다시 켬(창 2개 복원 · 연결 파일 이미 읽음)
            self.next_process(chrome_running=[True], windows=2)
            _, b, _ = self.run_cli("chrome-enable")
            print("P1 %d회차:" % i, b["pending"], b["say"][:70], "| acts", self.kinds())
            self.assertIn("크롬 창이 2개 열려", b["say"])
            self.assertNotIn("seat_restart", self.kinds())
            self.assertTrue(self.st().get("pending_seat_restart"))

    def test_P2_chrome_in_job_is_killed_by_next_call(self):
        self.win_restart_setup(chrome_running=[True, False, True], windows=1, act={"open": [{"rc": 1}, {"rc": 0}]})
        _, a, _ = self.run_cli("chrome-enable")
        self.assertNotIn("seat_restart", self.kinds())
        print("\nP2 1회차:", a["say"][-90:])
        self.next_process(chrome_running=[True], windows=1, act={})
        _, b, _ = self.run_cli("chrome-enable")
        print("P2 2회차:", b["say"][-70:], "| acts", self.kinds())
        self.assertIn("seat_restart", self.kinds())          # 그 크롬(Job 안)을 닫을 자동 재시작이 예약된다

    def test_P3_gave_up_reports_ok_and_says_already_on(self):
        self.reopen_debt(chrome_reopen_tries=3, chrome_reopen_at=0, pending_seat_restart=True)
        _, a, _ = self.run_cli("chrome-enable")
        print("\nP3 포기:", json.dumps(a, ensure_ascii=False)[:300], "| acts", self.kinds())
        self.assertTrue(a["ok"])
        self.assertEqual(a["pending"], [])
        self.assertIn("이미 켜져 있습니다", a["say"])
        self.next_process(chrome_running=[False], windows=0)
        _, b, _ = self.run_cli("chrome-enable", "--seat-restart", "no")
        print("P3 다음:", b["say"])
        self.assertNotIn("크롬", b["say"].replace("크롬 연결은 이미 켜져 있습니다.", ""))

    def test_P3b_gave_up_sentence_when_chrome_never_started(self):
        self.reopen_debt(chrome_reopen_tries=1, chrome_reopen_at=0)
        self.set_probes(chrome_running=[False], windows=0, act={"open": {"rc": 1}})
        self.m._nmh_ok = lambda plat, ud: True
        for t in (2, 3):
            s = self.st(); s["chrome_reopen_at"] = 0
            with open(os.path.join(self.state, self.m.CHROME_STATE), "w") as f:
                json.dump(s, f)
            self.m.CHROME_QUIT_WAIT_SEC = 0
            self.run_cli("chrome-enable", "--seat-restart", "no")
        self.assertEqual(self.st().get("chrome_reopen_tries"), 3)
        _, c, _ = self.run_cli("chrome-enable", "--seat-restart", "no")
        print("\nP3b 켜지도 못했는데:", c["say"])
        self.assertIn("곧 꺼져서", c["say"])

    def test_P4_background_then_zero_windows_says_menu(self):
        self.win_restart_setup(chrome_running=[True] * 60, windows=[1, 1, 0])
        _, a, _ = self.run_cli("chrome-enable")
        self.assertIn("크롬 창은 닫혔지만", a["say"])
        self.next_process(chrome_running=[True] * 5, windows=0)
        _, b, _ = self.run_cli("chrome-enable")
        print("\nP4 2회차:", b["say"][:90])
        self.assertIn("몇 개인지 확인하지 못해", b["say"])
        self.assertIn("⋮", b["say"])

    def test_P5_r5b_chrome_off_goes_outside_job_and_stale_reservation(self):
        self.make_chrome(nmh=False)
        self.win_restart_setup(chrome_running=[False], windows=0)
        os.environ["CYS_SURFACE_ID"] = "surface:7"
        _, a, _ = self.run_cli("chrome-enable")
        sr = [x for x in self.acts() if x["kind"] == "seat_restart"][0]
        print("\nP5 R5-B:", sr["argv"][1:6], "detach", sr["detach"], "| say:", a["say"][:80])
        self.assertEqual(sr["argv"][1:4], ["spawn-outside-job", "--kind", "seat_restart"])
        self.assertTrue(self.st().get("pending_seat_restart"))
        self.next_process(chrome_running=[False], windows=0)      # 대기가 죽었다(재부팅·프로세스 사망) — 기록은 남음
        _, b, _ = self.run_cli("chrome-enable")
        print("P5 대기 사망 뒤:", b["say"], "| acts", self.kinds())
        self.assertIn("이미 예약돼 있습니다", b["say"])
        self.assertNotIn("seat_restart", self.kinds())

    def test_P6_disable_silent_when_schedule_fails(self):
        self.win_restart_setup(chrome_running=[False], windows=0, act={"seat_restart": {"rc": 1}})
        _, d, _ = self.run_cli("chrome-disable", "--seat-restart", "auto")
        print("\nP6:", d["say"], "| acts", self.kinds())
        self.assertNotIn("재시작", d["say"])
        self.assertNotIn("다시 시작", d["say"])

    def test_P7_killed_between_quit_and_open_leaves_no_debt(self):
        self.win_restart_setup(chrome_running=[True, False, True], windows=1)
        real = self.m.quit_chrome
        def die(plat):
            real(plat)
            raise SystemExit(137)        # 도구 시한·사용자 중단으로 프로세스가 여기서 끊김
        self.m.quit_chrome = die
        with self.assertRaises(SystemExit):
            self.run_cli("chrome-enable")
        st = self.st()
        print("\nP7 끊긴 뒤 상태:", {k: st.get(k) for k in ("pending_chrome_restart", "pending_chrome_reopen")})
        self.assertFalse(st.get("pending_chrome_reopen"))
        self.assertFalse(st.get("pending_chrome_restart"))
        self.m.quit_chrome = real
        self.next_process(chrome_running=[False], windows=0)
        _, b, _ = self.run_cli("chrome-enable", "--seat-restart", "no")
        print("P7 다음 호출:", b["say"], "| acts", self.kinds())
        self.assertNotIn("open", self.kinds())

    def test_P8_mac_reopen_also_takes_stable_window(self):
        self.make_chrome(nmh=False)
        self.set_probes(chrome_running=[True, False, True], windows=[2, 2], act={"nmh": self.nmh_touch()})
        slept = []
        self.m._sleep = lambda n: slept.append(n)
        _, a, _ = self.run_cli("chrome-enable")
        print("\nP8 맥 sleep 합:", sum(slept), slept, "| open", [x["argv"] for x in self.acts() if x["kind"] == "open"])
        self.assertEqual([x["argv"] for x in self.acts() if x["kind"] == "open"][0][:3], ["/usr/bin/open", "-a", "Google Chrome"])
        self.assertTrue([x for x in self.acts() if x["kind"] == "seat_restart"][0]["detach"])
        self.assertGreaterEqual(slept.count(1), self.m.REOPEN_STABLE_SEC)

    # ── 맥에서 실행되지 않는 윈 ctypes 분기를 가짜 DLL 로 실제 실행 ──
    def _fake_win(self, kernel=None, user=None):
        import ctypes
        self.addCleanup(setattr, ctypes, "WinDLL", getattr(ctypes, "WinDLL", None))
        self.addCleanup(setattr, ctypes, "WINFUNCTYPE", getattr(ctypes, "WINFUNCTYPE", None))
        ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE
        ctypes.WinDLL = lambda name, use_last_error=False: {"kernel32": kernel, "user32": user}[name]
        self.m.platform = lambda: "win"

    def test_P9_win_window_count_runs_with_fake_dll(self):
        class F:
            pass
        wins = {101: ("Chrome_WidgetWin_1", 1, 0, 5, 0, 10), 102: ("Chrome_WidgetWin_1", 1, 0, 5, 0, 10),   # 창 2 · 같은 프로세스
                103: ("Chrome_WidgetWin_1", 1, 9, 5, 0, 10),   # 소유자 있음
                104: ("Chrome_WidgetWin_1", 0, 0, 5, 0, 10),   # 숨김
                105: ("Chrome_WidgetWin_1", 1, 0, 0, 0, 10),   # 제목 없음
                106: ("Chrome_WidgetWin_1", 1, 0, 5, 0x80, 10),  # 도구창
                107: ("Chrome_WidgetWin_1", 1, 0, 5, 0, 20),  # 다른 앱(msedge)
                108: ("Shell_TrayWnd", 1, 0, 5, 0, 30)}
        exes = {10: r"C:\Program Files\Google\Chrome\Application\chrome.exe", 20: r"C:\x\msedge.exe"}
        u, k = F(), F()
        u.GetClassNameW = lambda h, buf, n: setattr(buf, "value", wins[h][0]) or 1
        u.IsWindowVisible = lambda h: wins[h][1]
        u.GetWindow = lambda h, c: wins[h][2] or None
        u.GetWindowTextLengthW = lambda h: wins[h][3]
        u.GetWindowLongW = lambda h, i: wins[h][4]
        u.GetWindowThreadProcessId = lambda h, ref: setattr(ref._obj, "value", wins[h][5]) or 1
        k.OpenProcess = lambda acc, inh, pid: pid if pid in exes else None
        k.CloseHandle = lambda h: 1
        def qn(h, fl, buf, ref):
            buf.value = exes[h]
            return 1
        k.QueryFullProcessImageNameW = qn
        def enum(cb, lp):
            return all(cb(h, 0) for h in wins)
        u.EnumWindows = enum
        self._fake_win(k, u)
        self.assertEqual(self.m._win_chrome_window_count(), 2)
        print("\nP9 전수 = 2 (소유·숨김·무제목·도구창·다른 앱·트레이 제외)")
        k.OpenProcess = lambda acc, inh, pid: None       # 크롬 프로세스를 못 열면(다른 계정) 0 → unknown_windows 쪽 = 닫지 않음
        self.assertEqual(self.m._win_chrome_window_count(), 0)
        u.EnumWindows = lambda cb, lp: 0
        self.assertIsNone(self.m._win_chrome_window_count())

    def test_P10_win_proc_start_runs_with_fake_dll(self):
        if not hasattr(self.m, "_proc_start"):
            self.skipTest("f9a7d1ca 에는 없음")
        class F:
            pass
        k = F()
        k.OpenProcess = lambda acc, inh, pid: 7 if pid == 42 else None
        k.CloseHandle = lambda h: 1
        k.GetExitCodeProcess = lambda h, ref: setattr(ref._obj, "value", 259) or 1
        def times(h, a, b, c, d):
            a._obj.dwHighDateTime, a._obj.dwLowDateTime = 31, 77
            b._obj.dwHighDateTime = 99
            return 1
        k.GetProcessTimes = times
        self._fake_win(k, None)
        self.assertEqual(self.m._proc_start(42), "31.77")
        self.assertIsNone(self.m._proc_start(43))
        k.GetExitCodeProcess = lambda h, ref: setattr(ref._obj, "value", 0) or 1
        self.assertIsNone(self.m._proc_start(42))
        k.GetExitCodeProcess = lambda h, ref: setattr(ref._obj, "value", 259) or 1
        k.GetProcessTimes = lambda *a: 0
        self.assertIsNone(self.m._proc_start(42))
        print("\nP10 시작 시각 = 만든 시각 칸 · 죽음·못 엶·실패 = None")

    def test_P11_measure_failure_counts_as_dead_so_second_waiter(self):
        if not hasattr(self.m, "_proc_start"):
            self.skipTest("f9a7d1ca 에는 없음")
        self.waiter_recorded(proc_start=[None, "T2"])    # 대기는 살아 있으나 잠깐 못 잼
        _, d, _ = self.run_cli("chrome-enable")
        print("\nP11 못 잼 = 죽음 취급:", self.kinds())
        self.assertEqual(self.kinds().count("seat_restart"), 1)

    def test_P12_unmeasured_start_keeps_pid_only_trust(self):
        if not hasattr(self.m, "_proc_start"):
            self.skipTest("f9a7d1ca 에는 없음")
        self.set_probes(proc_start="ANYONE")
        self.assertTrue(self.m._waiter_alive({"seat_restart_pid": 777, "seat_restart_start": None}))
        print("\nP12 시작 시각을 못 적었으면 pid 만으로 산 것으로 친다(재사용 pid 도 예약)")


if __name__ == "__main__":
    s = unittest.TestSuite(unittest.TestLoader().loadTestsFromName(n, Probe) for n in sorted(x for x in dir(Probe) if x.startswith("test_P")))
    r = unittest.TextTestRunner(verbosity=1).run(s)
    sys.exit(0 if r.wasSuccessful() else 1)
