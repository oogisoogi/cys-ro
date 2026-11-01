#!/usr/bin/env python3
"""★L1(1.1.11 · cysr-1111-worker-swap): phoenix 가 `cys restore` 출력 전문을 로그에 남기는가(데몬 불요).

결함: 저널의 `out` 은 stdout 이 있으면 stderr 를 버리고 800자로 잘렸다 — 윈 r7 에서 「resume 생략」·「fresh 각성」 유무로
좌석 교체 원인을 가를 수 없었다.

실행: python3 cysjavis-pack/bin/tests/test_phoenix_restore_output_log.py   (0 = 전건 PASS)
실패 방향:
  · stdout 이 있을 때 stderr 가 로그에 없으면 적색 · 800자 뒤 줄이 로그에 없으면 적색
  · 타임아웃 때 진단 문안만 남고 stderr_raw 가 없으면 적색
  · `cys restore --no-resume` 경로가 로그를 빠뜨리면 적색
  · 저널 반환값(`out` 800자 · fresh_observed)이 달라지면 적색(동작 무변경)
"""
import importlib.util
import os
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.normpath(os.path.join(HERE, "..", "javis_phoenix.py"))
spec = importlib.util.spec_from_file_location("javis_phoenix", PH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

_results = []


def check(name, cond):
    _results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name)


def run(result, fn):
    """cys·log 를 갈아 끼우고 fn 실행 → (반환값, 로그 줄들)."""
    lines = []
    orig = (m.cys, m.log, m.restore_stall_window_s, m._spawn_heartbeat)
    m.cys = lambda *a, **k: result
    m.log = lines.append
    m.restore_stall_window_s = lambda: (90, "test")
    m._spawn_heartbeat = lambda *a, **k: (lambda: None)
    try:
        return fn(), lines
    finally:
        m.cys, m.log, m.restore_stall_window_s, m._spawn_heartbeat = orig


def main():
    long_tail = "· worker: 저장 대화를 이미 다른 좌석이 잇는 중"
    out = "x" * 900 + "\n" + long_tail + "\n"
    err = "[launch-agent] resume 생략: session_id 없음\n[launch-agent] fresh 각성(role=worker · agent=claude): 없음\n"
    res, lines = run(SimpleNamespace(returncode=0, stdout=out, stderr=err),
                     lambda: m.spawn_production("s", ["worker"], units=1))
    text = "\n".join(lines)
    check("stdout 이 있어도 stderr 전문이 로그에 남는다", "cys restore stderr| [launch-agent] resume 생략" in text)
    check("800자 뒤 stdout 줄도 로그에 남는다", "cys restore stdout| " + long_tail in text)
    check("저널 out 은 종전대로 800자 · stderr 미포함(동작 무변경)",
          len(res["out"]) == 800 and "resume 생략" not in res["out"])
    check("fresh 관측은 종전대로 원문에서 읽는다", res["fresh_observed"] == ["worker"])
    check("로그 줄은 분류기와 겹치지 않는다", m.cli_fresh_roles(text) == set())

    _, lines = run(SimpleNamespace(returncode=124, stdout="", stderr="TIMEOUT 90s", stderr_raw="[launch-agent] 앞선 줄\n"),
                   lambda: m.spawn_production("s", ["worker"], units=1))
    text = "\n".join(lines)
    check("타임아웃이면 stderr_raw 원문을 남긴다", "cys restore stderr| [launch-agent] 앞선 줄" in text)
    check("타임아웃 진단 문안은 원문 자리를 차지하지 않는다", "cys restore stderr| TIMEOUT" not in text)

    _, lines = run(SimpleNamespace(returncode=0, stdout="· worker: 좌석 내 재연결\n", stderr=""),
                   lambda: m.spawn_in_seat_production("s"))
    check("--no-resume 복원 출력도 남는다", any("좌석 내 재연결" in x for x in lines))

    _, lines = run(SimpleNamespace(returncode=0, stdout=None, stderr=None),
                   lambda: m.spawn_production("s", ["worker"], units=1))
    check("출력이 없어도 죽지 않는다", not any("cys restore std" in x for x in lines))

    ok = all(_results)
    print("=== %d checks · FAIL %d ===" % (len(_results), _results.count(False)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
