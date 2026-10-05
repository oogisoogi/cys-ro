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
import subprocess
import unittest

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


if __name__ == "__main__":
    unittest.main()
