#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_hud_bridge_unwatched_no_spawn.py — 보는 사람이 없으면 오피스 브리지가 cys 를 스폰하지 않는다.

★배경(TICKET=cysr-console-flicker-r2 · 2026-09-15): cysr 1.0.0 윈도우 참가자 기기에서 설치 뒤에도
  약 2초마다 cys.exe(+conhost)가 새로 생기며 콘솔 창이 깜빡였다. 코드상 2초 주기로 cys 를 낳는
  경로는 cysd 가 자동 기동하는 이 브리지의 fleet_loop(FLEET_POLL_SECS=2.0 · 틱당 fleet+status 2회)
  하나였고, 오피스 탭을 연 적이 없어도 상시 돌았다.

지키는 것
  ① 접속 클라이언트 0 — fleet_loop 는 cys 호출(run_json)을 **0회** 한다
  ② attach 즉시 폴링이 시작된다(화면이 비지 않게)
  ③ 마지막 detach 뒤 폴링이 멈춘다(진행 중이던 한 바퀴 이후 추가 호출 0)
  ④ Hub.watched 신호가 attach/detach 의 클라이언트 수와 일치한다(여럿 중 하나만 떠나도 켜진 채)

사거리(정직): 파이썬 스레드 단위 검사다. 윈도우에서 창이 실제로 안 뜨는지는 재지 않는다.
  구독 슈퍼바이저의 상주 `cys events` 자식(장수 1회 스폰)은 이 게이트 대상이 아니다.

실행: python3 test_hud_bridge_unwatched_no_spawn.py   (unittest·파일 직접 실행 — 저장소 관례 준거)
"""
import os
import sys
import threading
import time
import unittest

SELF = os.path.dirname(os.path.abspath(__file__))                        # …/bin/tests
BIN = os.path.dirname(SELF)                                              # cysjavis-pack/bin
sys.path.insert(0, BIN)
import javis_hud_bridge as HB                                            # noqa: E402


class _World:
    def merge_fleet(self, fleet, status):
        return [], False

    def accumulate_heat(self, now):
        pass


class UnwatchedNoSpawn(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.lock = threading.Lock()
        self._orig_run_json = HB.run_json
        self._orig_poll = HB.FLEET_POLL_SECS

        def fake_run_json(args, timeout=10):
            with self.lock:
                self.calls.append(tuple(args))
            return {}

        HB.run_json = fake_run_json
        HB.FLEET_POLL_SECS = 0.02
        self.hub = HB.Hub()
        self.poke = threading.Event()
        t = threading.Thread(target=HB.fleet_loop, args=(_World(), self.hub, self.poke), daemon=True)
        t.start()

    def tearDown(self):
        # ★순서가 계약이다(agy R2 · 누수 지적): 원본 run_json 을 되돌리기 **전에** 모든 클라이언트를
        #   떼어 루프를 대기로 돌려놓는다. 붙은 채 되돌리면 남은 daemon 스레드가 진짜 `cys` 를 스폰한다.
        with self.hub.lock:
            clients = list(self.hub.clients)
        for q in clients:
            self.hub.detach(q)
        self.assertFalse(self.hub.watched.is_set())
        time.sleep(0.1)   # 진행 중이던 한 바퀴가 가짜 run_json 으로 끝날 시간
        HB.run_json = self._orig_run_json
        HB.FLEET_POLL_SECS = self._orig_poll
        # 스레드는 daemon — 클라이언트 0 이므로 영구 대기(스폰 0) 상태로 남는다.

    def n(self):
        with self.lock:
            return len(self.calls)

    def test_no_client_means_zero_spawn(self):
        time.sleep(0.3)   # 종전 코드라면 이 사이 ~15틱·30회 호출
        self.assertEqual(self.n(), 0, "보는 사람이 없는데 cys 를 불렀다: %r" % self.calls[:4])

    def test_attach_starts_and_last_detach_stops(self):
        time.sleep(0.1)
        self.assertEqual(self.n(), 0)
        q1 = self.hub.attach()
        q2 = self.hub.attach()
        deadline = time.time() + 2.0
        while self.n() < 4 and time.time() < deadline:
            time.sleep(0.01)
        self.assertGreaterEqual(self.n(), 4, "attach 뒤 폴링이 시작되지 않았다")
        self.assertIn(("fleet", "--json"), self.calls)
        self.hub.detach(q1)
        self.assertTrue(self.hub.watched.is_set(), "클라이언트가 남았는데 신호가 꺼졌다")
        self.hub.detach(q2)
        self.assertFalse(self.hub.watched.is_set())
        time.sleep(0.1)   # 진행 중이던 한 바퀴가 끝날 시간
        settled = self.n()
        time.sleep(0.3)
        self.assertEqual(self.n(), settled, "마지막 detach 뒤에도 스폰이 계속됐다")

    def test_selftest_counter_reaches_target(self):
        # 공허 통과 차단 — 계수기가 실제 호출을 세는지(이게 초록이어야 ① 의 0 이 의미를 가진다).
        self.hub.attach()
        deadline = time.time() + 2.0
        while self.n() == 0 and time.time() < deadline:
            time.sleep(0.01)
        self.assertGreater(self.n(), 0)


if __name__ == "__main__":
    unittest.main()
