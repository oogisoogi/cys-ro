#!/usr/bin/env python3
"""test_dept_b11_lock — B11 부서 레지스트리·편성 원장 쓰기 측 공통 잠금 + 세대 검증(TICKET=v113-dept).

실 cys-dept(가짜 HOME · 스텁 cys — 실 데몬 무접촉)와 javis_dept_request 로:
  F1 down 울타리 — 기대 세대 불일치 = exit 9 · 레지스트리 무변경
  F2 down 울타리 — 다른 산 프로세스가 닫는 중 = exit 10 · 죽은 pid 표식은 무시하고 닫는다
  F3 destroy --expect-gen 불일치 = pack 격리 없이 중단(번호 재사용된 새 부서 보호)
  R1 편성 원장 청소가 레지스트리 잠금을 기다린다 — 잠금 보유 중 같은 번호가 예약되면(GUI 동시 생성) 옮기지 않는다
  G1 닫기 카드가 gen 을 기록 · 같은 번호가 다른 세대로 바뀌면 target_changed:gen · 같으면 --expect-gen 전달
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest

SELF = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(SELF)
DEPT = os.path.join(BIN, "cys-dept")
sys.path.insert(0, BIN)
sys.path.insert(0, SELF)


def _cysdept_env(tmp, depts):
    home = os.path.join(tmp, "home")
    bindir = os.path.join(home, ".local", "bin")
    fakepack = os.path.join(tmp, "fakepack", "bin")
    os.makedirs(bindir, exist_ok=True)
    os.makedirs(fakepack, exist_ok=True)
    reg = os.path.join(home, ".cys", "depts.json")
    os.makedirs(os.path.dirname(reg), exist_ok=True)
    json.dump({"depts": depts}, open(reg, "w"))
    with open(os.path.join(bindir, "cys"), "w", newline="\n") as f:
        f.write("#!/bin/sh\ncase \"$1\" in identify) exit 1;; esac\nexit 0\n")
    os.chmod(os.path.join(bindir, "cys"), 0o755)
    with open(os.path.join(fakepack, "javis_phoenix.py"), "w") as f:
        f.write("pass\n")
    env = dict(os.environ)
    env.update({"HOME": home, "CYS_DEPTS_JSON": reg, "CYS_PACK_DIR": os.path.join(tmp, "fakepack"),
                "PATH": bindir + os.pathsep + env.get("PATH", "")})
    for k in ("CYS_ROLE", "CYS_SOCKET", "CYS_DEPT_EXPECT_GEN"):
        env.pop(k, None)
    return env, home, reg


def _down(env, name, gen=None):
    e = dict(env)
    if gen is not None:
        e["CYS_DEPT_EXPECT_GEN"] = gen
    r = subprocess.run(["bash", DEPT, "down", name], capture_output=True, text=True, env=e, timeout=60)
    return r.returncode, r.stdout + r.stderr


def _dead_pid():
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


class TestFence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="b11-")
        self.entry = {"socket": "/tmp/b11/cys-dept-dept-2/cys.sock", "gen": "g-new"}

    def test_f1_gen_mismatch_refuses_without_touching(self):
        env, _, reg = _cysdept_env(self.tmp, {"dept-2": dict(self.entry)})
        rc, out = _down(env, "dept-2", gen="g-old")
        self.assertEqual(rc, 9, out)
        self.assertIn("세대 불일치", out)
        self.assertEqual(json.load(open(reg))["depts"]["dept-2"]["gen"], "g-new", "다른 세대 부서를 건드렸다")
        self.assertNotIn("closing", json.load(open(reg))["depts"]["dept-2"])
        rc, out = _down(env, "dept-9", gen="g-old")
        self.assertEqual(rc, 9, "기대 세대가 있는데 대상 부재를 통과시켰다: " + out)

    def test_f1b_gen_match_closes(self):
        env, _, reg = _cysdept_env(self.tmp, {"dept-2": dict(self.entry)})
        rc, out = _down(env, "dept-2", gen="g-new")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("dept-2", json.load(open(reg))["depts"])

    def test_f2_live_closer_blocks_dead_closer_ignored(self):
        e = dict(self.entry, closing={"pid": os.getpid(), "at": time.time()})
        env, _, reg = _cysdept_env(self.tmp, {"dept-2": e})
        rc, out = _down(env, "dept-2")
        self.assertEqual(rc, 10, out)
        self.assertIn("dept-2", json.load(open(reg))["depts"], "닫는 중인 부서를 이중으로 치웠다")
        rc, out = _down(env, "dept-2", gen="g-new")
        self.assertEqual(rc, 10, "세대가 맞아도 다른 산 닫기가 먼저다: " + out)
        d = json.load(open(reg))
        d["depts"]["dept-2"]["closing"] = {"pid": _dead_pid(), "at": 0}
        json.dump(d, open(reg, "w"))
        rc, out = _down(env, "dept-2")
        self.assertEqual(rc, 0, "죽은 표식이 번호를 영구히 잠갔다: " + out)
        self.assertNotIn("dept-2", json.load(open(reg))["depts"])

    def test_f3_destroy_expect_gen_mismatch_keeps_pack(self):
        env, home, reg = _cysdept_env(self.tmp, {"dept-2": dict(self.entry)})
        pack = os.path.join(home, ".cys", "pack-dept-dept-2")
        os.makedirs(pack)
        env.update({"CYS_ROLE": "cso", "CYS_DEPT_BIN": DEPT})
        r = subprocess.run([sys.executable, os.path.join(BIN, "javis_org.py"), "destroy", "--dept", "dept-2",
                            "--purge", "--expect-gen", "g-old"], capture_output=True, text=True, env=env, timeout=60)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.isdir(pack), "세대가 다른 부서의 pack 을 격리했다")
        self.assertIn("dept-2", json.load(open(reg))["depts"])
        self.assertEqual(json.loads(r.stdout)["targets"]["dept-2"], [["gen_mismatch", 9]],
                         "조기 거부 사유(세대 불일치)를 보고하지 않았다 — down 까지 내려갔다")

    def test_f3b_destroy_stops_when_down_fence_refuses(self):
        # 세대는 맞지만 다른 산 프로세스가 닫는 중(울타리 10) — teardown 이 시작되지 않았으니 pack 도 격리하지 않는다.
        e = dict(self.entry, closing={"pid": os.getpid(), "at": time.time()})
        env, home, reg = _cysdept_env(self.tmp, {"dept-2": e})
        pack = os.path.join(home, ".cys", "pack-dept-dept-2")
        os.makedirs(pack)
        env.update({"CYS_ROLE": "cso", "CYS_DEPT_BIN": DEPT})
        r = subprocess.run([sys.executable, os.path.join(BIN, "javis_org.py"), "destroy", "--dept", "dept-2",
                            "--purge", "--expect-gen", "g-new"], capture_output=True, text=True, env=env, timeout=60)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.isdir(pack), "울타리가 거부했는데 pack 을 격리했다")


class TestGenStamp(unittest.TestCase):
    def test_allocate_and_create_stamp_fresh_gen(self):
        # 생성 경로 기능시험은 실 cysd 가 필요해(test_dept_teardown_atomicity 머리 주석과 같은 사유) 정적 핀으로 —
        # 새 예약 두 곳(allocate · create NEW)이 예약마다 새 gen 을 찍는지.
        src = open(DEPT, encoding="utf-8").read()
        self.assertEqual(src.count("'gen':os.urandom(8).hex()"), 2, "예약 두 곳 중 gen 을 안 찍는 곳이 있다")
        self.assertIn('reg_fence_close "$name" "$$"', src.split("\n  down)\n")[1].split("\n    ;;\n")[0],
                      "down 이 울타리를 거치지 않는다")


import test_dept_request as TDR  # noqa: E402  (Base 하네스 재사용 — 가짜 cys·cys-dept·org)


class TestRequestSide(TDR.Base):
    def _ledger(self, name, sock):
        import javis_formation as jf
        fd = os.path.join(os.environ["CYS_STATE_DIR"], "formation")
        os.makedirs(fd, exist_ok=True)
        p = os.path.join(fd, jf._sanitize_key(sock) + ".json")
        json.dump({"state": "partial:x", "socket": sock}, open(p, "w"))
        return p

    def test_r1_orphan_cleanup_waits_registry_lock_and_sees_new_reservation(self):
        import javis_org
        sock = "/a/cys-dept-dept-4/cys.sock"
        p = self._ledger("dept-4", sock)
        lf = open(os.environ["CYS_DEPTS_JSON"] + ".lock", "w")
        javis_org._flock(lf)                             # GUI 예약이 잠금을 쥐고 있다
        res = {}
        th = threading.Thread(target=lambda: res.setdefault("moved", self.m.cleanup_orphan_ledgers()))
        th.start()
        th.join(0.5)
        self.assertTrue(th.is_alive(), "청소가 레지스트리 잠금을 기다리지 않았다(경합 창 열림)")
        with open(os.environ["CYS_DEPTS_JSON"], "w") as f:
            json.dump({"depts": {"dept-4": {"socket": sock}}}, f)
        lf.close()                                       # 예약 완료 → 잠금 해제
        th.join(10)
        self.assertEqual(res.get("moved"), [], "잠금 안에서 방금 예약된 부서의 원장을 옮겼다")
        self.assertTrue(os.path.exists(p))

    def test_r1c_live_dept_ledger_does_not_take_lock(self):
        # agy 1R ②: 산 부서 원장은 잠금 없이 선거름 — GUI 예약이 잠금을 쥔 동안에도 청소가 막히지 않는다.
        import javis_org
        sock = "/a/cys-dept-dept-6/cys.sock"
        with open(os.environ["CYS_DEPTS_JSON"], "w") as f:
            json.dump({"depts": {"dept-6": {"socket": sock}}}, f)
        p = self._ledger("dept-6", sock)
        lf = open(os.environ["CYS_DEPTS_JSON"] + ".lock", "w")
        javis_org._flock(lf)
        try:
            res = {}
            th = threading.Thread(target=lambda: res.setdefault("moved", self.m.cleanup_orphan_ledgers()))
            th.start()
            th.join(3)
            self.assertFalse(th.is_alive(), "산 부서 원장 때문에 레지스트리 잠금을 기다렸다(과차단)")
            self.assertEqual(res.get("moved"), [])
            self.assertTrue(os.path.exists(p))
        finally:
            lf.close()

    def test_r1d_lock_failure_moves_nothing(self):
        # agy 1R ①: 잠금을 못 잡으면(윈 msvcrt 10초 실패) 옮기지 않는다 — 무잠금 진행 금지.
        p = self._ledger("dept-7", "/a/cys-dept-dept-7/cys.sock")

        class NoLock(object):
            def __enter__(self):
                self.held = False
                return self

            def __exit__(self, *e):
                return False
        orig = self.m._registry_lock
        self.m._registry_lock = NoLock
        try:
            self.assertEqual(self.m.cleanup_orphan_ledgers(), [])
        finally:
            self.m._registry_lock = orig
        self.assertTrue(os.path.exists(p), "잠금 실패인데 원장을 옮겼다")

    def test_r1b_orphan_still_cleaned_when_absent(self):
        p = self._ledger("dept-5", "/a/cys-dept-dept-5/cys.sock")
        moved = self.m.cleanup_orphan_ledgers()
        self.assertEqual(len(moved), 1, "진짜 고아 원장을 못 치웠다(과차단)")
        self.assertFalse(os.path.exists(p))

    def _menu_dept(self, gen):
        json.dump({"depts": {"dept-3": {"socket": "/a/cys-dept-dept-3/cys.sock", "display_name": "메뉴부서",
                                        "gen": gen}}}, open(os.environ["CYS_DEPTS_JSON"], "w"))

    def test_g1_menu_dept_recreated_same_number_is_not_closed(self):
        self._menu_dept("g1")
        rc, o = self.run_cmd("propose", "--close", "메뉴부서")
        self.assertEqual(rc, 0, o)
        cid = o["request"]
        self.assertEqual(self.req(cid)["gen"], "g1")
        self.run_cmd("confirm", cid)
        self._menu_dept("g2")                            # 같은 번호 · 같은 이름 · 같은 소켓 — 세대만 다르다
        self.tick()
        c = self.req(cid)
        self.assertEqual(c["state"], "failed")
        self.assertEqual(c["fail_reason"], "target_changed:gen")
        self.assertIn("dept-3", self.reg())
        self.assertFalse(os.path.exists(os.path.join(self.home, "fake-org.log")))

    def test_g1b_same_gen_passes_expect_gen(self):
        self._menu_dept("g1")
        rc, o = self.run_cmd("propose", "--close", "메뉴부서")
        cid = o["request"]
        self.run_cmd("confirm", cid)
        self.tick()
        self.assertEqual(self.req(cid)["state"], "closed")
        a = json.loads(open(os.path.join(self.home, "fake-org.log")).readline())
        self.assertEqual(a[a.index("--expect-gen") + 1], "g1", "울타리에 기대 세대를 넘기지 않았다")


if __name__ == "__main__":
    unittest.main()
