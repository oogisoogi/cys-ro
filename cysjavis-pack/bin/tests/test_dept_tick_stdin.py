#!/usr/bin/env python3
"""test_dept_tick_stdin — ★D18(1.1.8 · 윈 실측): 대화 닫기 틱이 확정 1초 뒤 `OSError: [WinError 6] 핸들이 잘못되었습니다`
로 죽었고(부서는 무손상) 같은 사건의 결과 알림이 `notify 부서결과 rc=127` 로 미도달 — GUI 닫기·틱 만들기는 성공.

원인 = 콘솔 없는 틱에서 stdin 을 지정하지 않은 subprocess 호출이 부모의 무효 stdin 핸들을 복제하다 실패(만들기 Popen 만
stdin=DEVNULL 이었다). 처방 = 이 모듈의 하위 프로세스 호출 전부 stdin=DEVNULL · 알림 실패는 예외 이름까지 기록.
윈 핸들 실패는 맥에서 재현 불가 → ①전수 정적 핀 ②호출 인자 실측(대역 run) ③예외 기록 문면.
"""
import ast
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BIN, "javis_dept_request.py")


def load():
    spec = importlib.util.spec_from_file_location("javis_dept_request_d18", SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class T(unittest.TestCase):
    def test_every_subprocess_call_sets_stdin(self):
        with open(SRC, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        calls, missing = 0, []
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"
                    and n.func.attr in ("run", "Popen", "call", "check_call", "check_output")):
                calls += 1
                kws = {k.arg for k in n.keywords}
                if not ({"stdin", "input"} & kws):
                    missing.append(n.lineno)
        self.assertGreaterEqual(calls, 8, "호출 계수 이상(핀이 아무것도 안 잰다)")
        self.assertEqual(missing, [], "stdin 미지정 호출(윈 무콘솔 틱에서 WinError 6): 줄 %s" % missing)

    def test_notify_passes_devnull_and_records_exception(self):
        m = load()
        events, seen = [], {}
        m.save_req = lambda r: None
        m._event = lambda r, s: events.append(s)
        m._cys_bin = lambda: "cys"
        real_run = subprocess.run
        self.addCleanup(setattr, subprocess, "run", real_run)   # m.subprocess 는 전역 모듈이다 — 반드시 복원

        def fake_ok(argv, **kw):
            seen.update(kw)
            return subprocess.CompletedProcess(argv, 0, "", "")
        m.subprocess.run = fake_ok
        m._notify({"id": "dr-x", "state": "closed"}, "부서결과")
        self.assertIs(seen.get("stdin"), subprocess.DEVNULL)
        self.assertEqual(events[-1], "notify 부서결과 rc=0")

        def fake_boom(argv, **kw):
            raise OSError(6, "핸들이 잘못되었습니다")
        m.subprocess.run = fake_boom
        m._notify({"id": "dr-y", "state": "failed"}, "부서결과")
        self.assertTrue(events[-1].startswith("notify 부서결과 rc=127(OSError:"), events[-1])
        self.assertIn("핸들이 잘못되었습니다", events[-1])


# ── ★M1(1.1.11 · 윈 실측 재발): D18 은 javis_dept_request 만 고쳤다 — 재부팅 로그온 세대에서 팩 파이썬의 `cys gate-check` 가 같은
#   WinError 6 으로 죽어 fail-closed(편성·자동 사이클 보류). 처방 = 팩 전체의 입력 없는 캡처 호출 stdin=DEVNULL.
#   윈 `_get_handles` 규칙: stdin·stdout·stderr 셋 다 None 이면 복제 없이 넘어가고, 하나라도 지정되면 stdin=None 일 때 부모 핸들을 복제한다.
PACK = os.path.dirname(BIN)
SPAWN = ("run", "Popen", "call", "check_call", "check_output")


def _pack_sources():
    for root, dirs, files in os.walk(PACK):
        dirs[:] = [d for d in dirs if d not in ("tests", "__pycache__", ".venv", "node_modules")]
        for n in files:
            if n.endswith(".py"):
                yield os.path.join(root, n)


def _none_default_params(fn):
    a = fn.args
    pos = a.posonlyargs + a.args
    pairs = list(zip(pos[len(pos) - len(a.defaults):], a.defaults)) + list(zip(a.kwonlyargs, a.kw_defaults))
    return {p.arg for p, d in pairs if isinstance(d, ast.Constant) and d.value is None}


def _splat_sets_stdin(call, scope):
    """**X 가 stdin 을 싣는가 — `_nostdin()` 또는 같은 함수의 kw = {"stdin": …} 사전."""
    for k in call.keywords:
        if k.arg is not None:
            continue
        if isinstance(k.value, ast.Call) and getattr(k.value.func, "id", "") == "_nostdin":
            return True
        if isinstance(k.value, ast.Name):
            for n in ast.walk(scope):
                if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)
                        and any(getattr(t, "id", "") == k.value.id for t in n.targets)
                        and any(getattr(x, "value", None) == "stdin" for x in n.value.keys)):
                    return True
    return False


def _scan(path):
    """(스폰 호출 수, 위반 목록). 위반 = 출력을 돌리면서 stdin·input 이 없거나, input 이 기본값 None 인 인자 그대로인데 stdin 이 없다."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    aliases = {"subprocess"}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            aliases |= {a.asname for a in n.names if a.name == "subprocess" and a.asname}
    scopes = [tree] + [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    count, bad, seen = 0, [], set()
    for scope in reversed(scopes):      # 안쪽 함수부터 — 호출을 가장 가까운 함수에 귀속
        none_params = _none_default_params(scope) if scope is not tree else set()
        for n in ast.walk(scope):
            if (not isinstance(n, ast.Call) or id(n) in seen or not isinstance(n.func, ast.Attribute)
                    or not isinstance(n.func.value, ast.Name) or n.func.value.id not in aliases
                    or n.func.attr not in SPAWN):
                continue
            seen.add(id(n))
            count += 1
            kws = {k.arg: k.value for k in n.keywords}
            if not ({"capture_output", "stdout", "stderr"} & set(kws)) and n.func.attr != "check_output":
                continue                # 셋 다 None = 윈이 부모 핸들을 건드리지 않는다
            if "stdin" in kws or _splat_sets_stdin(n, scope) or (
                    isinstance(scope, ast.FunctionDef) and scope.name == "_run_decoded"):
                continue                # _run_decoded = kw.setdefault("stdin", …) · 시험이 따로 잰다
            inp = kws.get("input")
            if inp is None or (isinstance(inp, ast.Constant) and inp.value is None) or (
                    isinstance(inp, ast.Name) and inp.id in none_params):
                bad.append("%s:%d" % (os.path.relpath(path, PACK), n.lineno))
    return count, bad


class PackWide(unittest.TestCase):
    def test_every_redirected_spawn_in_pack_sets_stdin(self):
        calls, missing = 0, []
        for p in _pack_sources():
            c, b = _scan(p)
            calls += c
            missing += b
        self.assertGreaterEqual(calls, 250, "호출 계수 이상(핀이 아무것도 안 잰다)")
        self.assertEqual(missing, [], "stdin 미지정 캡처 호출(윈 무콘솔 세대에서 WinError 6)")

    def test_scan_flags_the_defect_shapes(self):
        src = (
            "import subprocess\nimport subprocess as sp\n"
            "def a(x, t=None):\n"
            "    subprocess.run(x, capture_output=True, input=t)\n"      # 입력이 None 일 수 있다
            "    sp.check_output(x)\n"                                    # 별칭 · 캡처 내장
            "    subprocess.run(x, stderr=subprocess.DEVNULL, input=None)\n"
            "    subprocess.run(x, stdin=subprocess.DEVNULL, capture_output=True)\n"
            "    subprocess.run(x, capture_output=True, input='y')\n"
            "    subprocess.run(x)\n"
        )
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.py")
            with open(p, "w", encoding="utf-8") as f:
                f.write(src)
            _c, bad = _scan(p)
        self.assertEqual([b.rsplit(":", 1)[1] for b in bad], ["4", "5", "6"])


def _load_pack(name):
    spec = importlib.util.spec_from_file_location(name + "_m1", os.path.join(BIN, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class InvalidStdin(unittest.TestCase):
    """윈 재부팅 로그온 세대 모의 — 실제 Popen 경로에서 `_get_handles` 만 윈 규칙으로 죽인다(자식은 진짜로 뜬다)."""

    def setUp(self):
        real = subprocess.Popen._get_handles
        self.seen = []

        def invalid_parent_stdin(popen, stdin, stdout, stderr):
            self.seen.append(stdin)
            if stdin is None and (stdout is not None or stderr is not None):
                raise OSError(6, "핸들이 잘못되었습니다")
            return real(popen, stdin, stdout, stderr)
        subprocess.Popen._get_handles = invalid_parent_stdin
        self.addCleanup(setattr, subprocess.Popen, "_get_handles", real)
        self.tmp = tempfile.mkdtemp(prefix="m1-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = {k: v for k, v in os.environ.items() if not k.startswith("CYS_")}
        env.update(HOME=self.tmp, USERPROFILE=self.tmp, CYS_PACK_DIR=os.path.join(self.tmp, "pack"),
                   CYS_STATE_DIR=os.path.join(self.tmp, "state"))
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ok = [sys.executable, "-c", "pass"]

    def _fake_cys(self):
        p = os.path.join(self.tmp, "cys")
        with open(p, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(p, 0o755)
        os.environ["PATH"] = self.tmp + os.pathsep + os.environ.get("PATH", "")
        return p

    def test_probe_reproduces_the_failure(self):
        with self.assertRaises(OSError):            # 모의가 실제로 무효 핸들을 재현한다(이게 안 죽으면 아래 시험은 무의미)
            subprocess.run(self.ok, capture_output=True)

    def test_runners_survive_without_input(self):
        ap = _load_pack("javis_cycle_autopilot")
        self.assertEqual(ap.run(self.ok)[0], 0)
        self.assertEqual(ap.run_wakeup(self.ok)[0], 0)
        self.assertEqual(_load_pack("javis_cycle_verifier").run(self.ok)[0], 0)
        self.assertEqual(_load_pack("javis_formation")._run(self.ok)[0], 0)
        self.assertEqual(_load_pack("javis_bootstrap")._run_split(self.ok)[0], 0)
        self.assertEqual(_load_pack("javis_phoenix")._run_decoded(self.ok).returncode, 0)

    def test_runners_still_deliver_input(self):
        echo = [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read())"]
        self.assertEqual(_load_pack("javis_cycle_autopilot").run(echo, stdin_text="왕복")[:2], (0, "왕복"))
        self.assertEqual(_load_pack("javis_cycle_verifier").run(echo, stdin_text="왕복")[:2], (0, "왕복"))
        self.assertEqual(_load_pack("javis_bootstrap")._run_split(echo, input_text="왕복")[:2], (0, "왕복"))

    @unittest.skipIf(os.name == "nt", "가짜 cys = 셸 스크립트")
    def test_gate_check_is_not_fail_closed(self):
        ap = _load_pack("javis_cycle_autopilot")
        ap.CYS = self._fake_cys()
        self.assertEqual(ap.kill_switch(), (False, ""))
        self._fake_cys()
        self.assertTrue(bool(_load_pack("javis_formation").gate_check()))


if __name__ == "__main__":
    unittest.main()
