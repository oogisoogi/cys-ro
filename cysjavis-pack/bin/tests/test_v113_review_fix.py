#!/usr/bin/env python3
"""test_v113_review_fix — 1.1.3 Fable 적대 검증 발견 수리(TICKET=v113-review-fix).

  W1 cys-dept 울타리 _alive: 윈에서 os.kill 을 부르지 않고 QUERY_LIMITED+GetExitCodeProcess 로만 판정
  W4 cys-dept allocate·create 예약: 윈 msvcrt 잠금 실패를 삼키지 않고 exit 11
  W2 javis_ctx_relay 상태 파일 레인: 윈 부서 파이프 2개가 서로 다른 파일 · unix 는 종전 이름 그대로
"""
import os
import re
import sys
import types
import unittest

SELF = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(SELF)
DEPT = os.path.join(BIN, "cys-dept")
sys.path.insert(0, BIN)


def _fence_alive_src():
    s = open(DEPT, encoding="utf-8").read()
    m = re.search(r"^def _alive\(pid\):\n.*?(?=^p,n,me=)", s, re.S | re.M)
    assert m, "reg_fence_close 의 _alive 를 못 찾음"
    return m.group(0)


class _FakeK32:
    def __init__(self, handle=1, err=0, code=259, ok=1):
        self.handle, self.err, self.code, self.ok = handle, err, code, ok
        self.closed = 0

    def OpenProcess(self, access, inherit, pid):
        self.access = access
        return self.handle

    def GetExitCodeProcess(self, h, ref):
        ref._obj.value = self.code
        return self.ok

    def CloseHandle(self, h):
        self.closed += 1


def _load_alive(os_name, k32=None):
    kills = []
    fake_os = types.SimpleNamespace(name=os_name, kill=lambda p, s: kills.append((p, s)))
    real_ct = __import__("ctypes")
    fake_ct = types.SimpleNamespace(
        WinDLL=lambda name, use_last_error=False: k32,
        get_last_error=lambda: k32.err if k32 else 0,
        c_ulong=real_ct.c_ulong, byref=real_ct.byref)
    ns = {"os": fake_os}
    saved = sys.modules.get("ctypes")
    sys.modules["ctypes"] = fake_ct
    try:
        exec(_fence_alive_src(), ns)
    finally:
        pass
    alive = ns["_alive"]

    def call(pid):
        sys.modules["ctypes"] = fake_ct
        try:
            return alive(pid)
        finally:
            sys.modules["ctypes"] = saved
    sys.modules["ctypes"] = saved
    return call, kills


class TestW1FenceAliveWindows(unittest.TestCase):
    def test_nt_never_calls_os_kill(self):
        for k32, want in ((_FakeK32(code=259), True), (_FakeK32(code=0), False),
                          (_FakeK32(handle=0, err=87), False), (_FakeK32(handle=0, err=5), True)):
            alive, kills = _load_alive("nt", k32)
            self.assertEqual(alive(4321), want, vars(k32))
            self.assertEqual(kills, [], "윈에서 os.kill(pid,0)=TerminateProcess 가 불렸다")
        k = _FakeK32(code=259)
        alive, _ = _load_alive("nt", k)
        alive(4321)
        self.assertEqual(k.access, 0x1000, "QUERY_LIMITED 외 권한(TERMINATE 등)을 요청했다")
        self.assertEqual(k.closed, 1, "핸들 누수")

    def test_posix_still_uses_signal_zero(self):
        alive, kills = _load_alive("posix")
        self.assertTrue(alive(4321))
        self.assertEqual(kills, [(4321, 0)])
        self.assertFalse(alive("x"))

    def test_callsites_pass_os_pid(self):
        s = open(DEPT, encoding="utf-8").read()
        self.assertEqual(s.count('reg_fence_close "$name" "$(self_os_pid)"'), 2)
        self.assertNotIn('reg_fence_close "$name" "$$"', s)
        i = s.index("\nself_os_pid(){")
        body = s[i:s.index("\n}\n", i)]
        arm = [l for l in body.splitlines() if l.strip().startswith("MINGW*|MSYS*|CYGWIN*)")]
        self.assertEqual(len(arm), 1, body)
        self.assertIn('cat "/proc/$$/winpid"', arm[0], "윈 갈래가 MSYS pid($$)를 그대로 적는다")


class TestW2CtxRelayLane(unittest.TestCase):
    def _path(self, sock):
        import javis_ctx_relay as r
        old = dict(os.environ)
        try:
            os.environ["CYS_STATE_DIR"] = "/sd"
            if sock is None:
                os.environ.pop("CYS_SOCKET", None)
            else:
                os.environ["CYS_SOCKET"] = sock
            return r.state_path()
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_two_windows_dept_pipes_do_not_share_state(self):
        a = self._path(r"\\.\pipe\cys-dept-dept-1")
        b = self._path(r"\\.\pipe\cys-dept-dept-2")
        self.assertNotEqual(a, b, "윈 부서 2곳이 같은 ctx-relay 상태 파일을 쓴다")
        self.assertEqual(os.path.basename(a), "ctx-relay-cys-dept-dept-1.json")
        self.assertNotIn("pipe", os.path.basename(b))

    def test_unix_and_base_names_unchanged(self):
        self.assertEqual(self._path("/h/.local/state/cys-dept-dept-1/cys.sock"),
                         os.path.join("/sd", "ctx-relay-cys-dept-dept-1.json"))
        self.assertEqual(self._path(None), os.path.join("/sd", "ctx-relay-base.json"))


def _lock_block(section_start, section_end):
    s = open(DEPT, encoding="utf-8").read()
    i = s.index(section_start)
    j = s.index(section_end, i)
    seg = s[i:j]
    a = seg.index("try:\n    import fcntl")
    b = seg.index("    def _ulk(f): pass\n", a) + len("    def _ulk(f): pass\n")
    return seg[a:b]


class TestW4ReserveLockFailClosed(unittest.TestCase):
    def _run(self, block):
        class _Msv:
            LK_LOCK = 1
            @staticmethod
            def locking(fd, mode, n):
                raise OSError(36, "deadlock avoided")
        saved = {k: sys.modules.get(k) for k in ("fcntl", "msvcrt")}
        sys.modules["fcntl"] = None                 # import fcntl → ImportError(윈 흉내)
        sys.modules["msvcrt"] = _Msv
        try:
            ns = {"sys": sys}
            exec(block, ns)
            with open(os.devnull, "w") as f, self.assertRaises(SystemExit) as cm:
                ns["_lk"](f)
            return cm.exception.code
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_allocate_lock_failure_exits_11(self):
        self.assertEqual(self._run(_lock_block("  allocate)\n", "print(name)\nfinally: _ulk(lf)")), 11)

    def test_create_lock_failure_exits_11(self):
        self.assertEqual(self._run(_lock_block("res=$(reg_init; CYS_GRACE=", 'print("NEW "+name)')), 11)


if __name__ == "__main__":
    unittest.main()
