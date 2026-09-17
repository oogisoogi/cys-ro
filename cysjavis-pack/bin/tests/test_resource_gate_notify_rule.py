#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_resource_gate_notify_rule.py — 자원 게이트 승인 알림 발생 규칙 핀 (TICKET=cysr-ui-polish-101 ⓒ).

규칙(master#2ab87335): 부트스트랩이 자원 게이트 결과로 승인 채널(feed · kind=bootstrap-fail)에
알림을 올리는 것은 **verdict != allow** 일 때만이다. allow 인데 요청이 생기면 실질 위험 0 의 소음이고,
참가자 기계에서는 결재할 사람이 없어 Control Center 배지가 영구히 남는다. 함대·프로파일 구분 없이
같은 규칙이다(프로파일 감지는 2026-09-10 폐기 — test_default_fleet_formation ⓐ17).

  ① allow(exit 0)            → _notify_loud 0회
  ② soft_warn(exit 1)         → 1회(현행 유지 · 제목 「자원 soft_warn」)
  ③ hard_block(exit 2 · 실노드 과다) → 1회 + 반환 9(부트 중단 · 현행)
  ④ 측정 실패(exit 64)        → 1회(조용한 allow 금지 · 현행)
  ⑤ 통합 · 윈도 대역(ps 실행 파일·load 평균 부재, 과부하 없음) → 실제 게이트 subprocess 로 0회
     (master#81c7cb4a · 참가자 윈도 실기: ps 부재가 nodes(ps) 측정 실패로 잡혀 매 부트 soft_warn → 배지)
  ⑥ 통합 · 같은 윈도 대역 + 실제 과부하(load/ncpu 1.5 · soft 1.0~hard 2.0) → 1회(자원 soft_warn)
  ⑧ (cysr-102 A2) load hard 지속 → 재측정 정확히 RECHECKS 회(측정 1+6 · 대기 6×30s) 뒤 9 · 알림 1회
  ⑪ (cysr-102 A2 r2) 비-load hard(servers) · 복합(load+servers) → 재측정 0 · 즉시 9 · 알림 1회
  ⑨ (cysr-102 A2) 통합 · 설치 직후 부하 흉내 — 실제 게이트에 --load-override 3.11→3.11→0.79(×ncpu)
     를 차례로 줘 hard→hard→allow 전환 → 대기 2회 · 알림 0회 · 진행(exit 9 아님)
  M1 뮤턴트(재측정 루프 제거) → ⑧·⑨ 적색 · M2 뮤턴트(load 한정 좁힘 제거) → ⑪ 적색(선-assert 동반)

밀폐: HOME·CYS_PACK_DIR·CYS_STATE_DIR 을 임시 디렉터리로 고정한 뒤 import 한다(모듈 전역이 import 시
고정된다). ①~④ 는 _run_split·_live_node_count·_notify_loud 를 대체한다(subprocess 0).
⑤⑥ 은 임시 팩에 복사한 실제 게이트를 부른다 — PATH = 목 cys 만 든 폴더(ps 없음 · `cys ps` 는
빈 원장) · PYTHONPATH 의 sitecustomize 로 getloadavg 를 지우거나 고정값으로 바꾼다. 데몬·실 cys 무접촉.
실행: python3 cysjavis-pack/bin/tests/test_resource_gate_notify_rule.py  → 종료 토큰 RESOURCE-GATE-NOTIFY-RULE-OK
"""
import json
import os
import shutil
import sys
import tempfile

SELF = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(SELF)
sys.path.insert(0, BIN)

_ROOT = tempfile.mkdtemp()
_PACK = os.path.join(_ROOT, "home", ".cys", "pack")
os.makedirs(os.path.join(_PACK, "bin"), exist_ok=True)
# ⑤⑥ 통합용 — 피검 게이트 실물(표준 라이브러리만 import 한다)
shutil.copy2(os.path.join(BIN, "javis_resource_gate.py"), os.path.join(_PACK, "bin", "javis_resource_gate.py"))
os.environ["HOME"] = os.path.join(_ROOT, "home")
os.environ["CYS_PACK_DIR"] = _PACK
os.environ["CYS_STATE_DIR"] = os.path.join(_ROOT, "state")

import javis_bootstrap as B  # noqa: E402

_REAL_RUN_SPLIT = B._run_split
_REAL_LIVE = B._live_node_count
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else " — " + str(detail)))
    if not ok:
        fails.append(name)


class _Log:
    def __init__(self):
        self.steps = []

    def step(self, *a, **k):
        self.steps.append(a)

    def result(self, **k):
        self.steps.append(("result", k))


SLEEPS = []


def run(gate_exit, gate_json, live=None, M=None):
    M = M or B
    calls = []
    del SLEEPS[:]
    M._notify_loud = lambda title, body: calls.append(title) or "feed"
    M._run_split = lambda cmd, timeout=120: (gate_exit, json.dumps(gate_json), "")
    M._live_node_count = lambda: live
    M._progress = lambda msg: None
    M._resource_gate_sleep = SLEEPS.append          # 실 대기 0 — 대기 요청만 기록
    rc = M._run_resource_gate(sys.executable, _Log())
    return rc, calls


check("밀폐: 모듈 PACK 이 임시 팩이다", B.PACK == _PACK, B.PACK)

rc, calls = run(0, {"verdict": "allow", "trips": []})
check("① allow → 승인 알림 0회 · 진행", calls == [] and rc is None, (rc, calls))

rc, calls = run(1, {"verdict": "soft_warn", "trips": [{"axis": "load_ratio", "level": "soft"}]})
check("② soft_warn → 알림 1회(자원 soft_warn) · 진행", calls == ["자원 soft_warn"] and rc is None, (rc, calls))

rc, calls = run(2, {"verdict": "hard_block",
                    "trips": [{"axis": "servers", "level": "hard"}]}, live=99)
check("③ hard_block → 알림 1회 · 부트 중단(9)",
      len(calls) == 1 and calls[0].startswith("자원 hard_block") and rc == B.EXIT_RESOURCE_HARD, (rc, calls))

rc, calls = run(64, None)
check("④ 측정 실패(64) → 알림 1회 · 진행", len(calls) == 1 and "측정 실패" in calls[0] and rc is None, (rc, calls))


def run_windows_like(load_ratio=None, windows=True, load_seq=None, M=None):
    """실제 게이트 subprocess 를 윈도 대역 환경에서 돌린다. load_ratio=None 이면 getloadavg 부재.
    windows=True 면 platform.system() 을 "Windows" 로 바꾼다(subprocess 가 보는 sys.platform·os.name 은
    건드리지 않는다 — 그걸 바꾸면 subprocess 모듈이 윈도 경로로 import 돼 대역 자체가 죽는다)."""
    d = tempfile.mkdtemp(dir=_ROOT)
    mock = os.path.join(d, "bin")
    site = os.path.join(d, "site")
    os.makedirs(mock)
    os.makedirs(site)
    with open(os.path.join(mock, "cys"), "w") as f:
        f.write('#!/bin/sh\n[ "$1" = ps ] && { echo "(ledger empty)"; exit 0; }\nexit 1\n')
    os.chmod(os.path.join(mock, "cys"), 0o755)
    with open(os.path.join(site, "sitecustomize.py"), "w") as f:
        if windows:
            f.write("import platform\nplatform.system = lambda: 'Windows'\n")
        if load_ratio is None:
            f.write("import os\nif hasattr(os, 'getloadavg'):\n    del os.getloadavg\n")
        else:
            f.write("import os\nos.getloadavg = lambda: (%r * (os.cpu_count() or 1), 0.0, 0.0)\n" % load_ratio)
    saved = {k: os.environ.get(k) for k in ("PATH", "PYTHONPATH")}
    os.environ["PATH"] = mock
    os.environ["PYTHONPATH"] = site
    calls = []
    M = M or B
    del SLEEPS[:]
    try:
        if load_seq is None:
            M._run_split = _REAL_RUN_SPLIT
        else:
            # 측정마다 다음 load1 을 --load-override 로 실제 게이트에 넘긴다(마지막 값 유지).
            seq = list(load_seq)

            def _split(cmd, timeout=120):
                v = seq.pop(0) if len(seq) > 1 else seq[0]
                return _REAL_RUN_SPLIT(list(cmd) + ["--load-override", repr(v * (os.cpu_count() or 1))],
                                       timeout=timeout)
            M._run_split = _split
        M._live_node_count = _REAL_LIVE
        M._notify_loud = lambda title, body: calls.append(title) or "feed"
        M._progress = lambda msg: None
        M._resource_gate_sleep = SLEEPS.append
        log = _Log()
        rc = M._run_resource_gate(sys.executable, log)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    gate_step = [s for s in log.steps if s and s[0] == B.STEP.RESOURCE_GATE]
    if load_seq is not None:
        return rc, calls, [s[2] for s in gate_step]
    return rc, calls, (gate_step[0][2] if gate_step else "")


rc, calls, detail = run_windows_like(None)
check("⑤ 통합 윈도 대역(ps·load 부재) → 승인 알림 0회 · 진행",
      calls == [] and rc is None and "verdict=allow" in detail, (rc, calls, detail[:600]))
check("⑤′ 부재 사실은 게이트 기록에 남는다(조용한 삭제 금지)",
      "ps(플랫폼 미제공)" in detail and "load(플랫폼 미제공)" in detail, detail[:600])

rc, calls, detail = run_windows_like(1.5)
check("⑥ 통합 윈도 대역 + 실제 과부하 → 알림 1회(자원 soft_warn) · 진행",
      calls == ["자원 soft_warn"] and rc is None and "verdict=soft" in detail, (rc, calls, detail[:600]))

rc, calls, detail = run_windows_like(None, windows=False)
check("⑦ 통합 POSIX 축소 PATH(ps 안 보임) → 부재로 접지 않고 측정 실패 알림 1회(과부하 은폐 차단 · agy 1R)",
      calls == ["자원 soft_warn"] and "nodes(ps)" in detail and "ps(플랫폼 미제공)" not in detail,
      (rc, calls, detail[:600]))



def a2_axes(M, sink=None):
    """A2 축 ⑧⑨ — sink 가 있으면 출력 없이 실패 이름만 모은다(뮤턴트 판정용)."""
    def ck(name, ok, detail=""):
        if sink is None:
            check(name, ok, detail)
        elif not ok:
            sink.append(name)
    rc, calls = run(2, {"verdict": "hard_block", "trips": [{"metric": "load_ratio", "level": "hard"}]},
                    live=99, M=M)
    ck("⑧ hard 지속 → 대기 정확히 %d회×%ds 뒤 부트 중단(9) · 알림 1회"
       % (M.RESOURCE_GATE_RECHECKS, M.RESOURCE_GATE_RECHECK_S),
       rc == M.EXIT_RESOURCE_HARD and len(calls) == 1 and SLEEPS == [30] * 6
       and (M.RESOURCE_GATE_RECHECKS, M.RESOURCE_GATE_RECHECK_S) == (6, 30), (rc, calls, SLEEPS))
    rc, calls, details = run_windows_like(load_seq=[3.11, 3.11, 0.79], M=M)
    ck("⑨ 설치 직후 부하 흉내(3.11→3.11→0.79) → 대기 2회 · 3번째 측정 allow · 알림 0 · 진행",
       rc is None and calls == [] and SLEEPS == [30, 30] and len(details) == 3
       and "verdict=hard-block" in details[0] and "verdict=hard-block" in details[1]
       and "verdict=allow" in details[2], (rc, calls, SLEEPS, [d[:200] for d in details]))
    for label, trips in (("servers 단독", [{"metric": "servers", "level": "hard"}]),
                         ("load+servers 복합", [{"metric": "load_ratio", "level": "hard"},
                                                {"metric": "servers", "level": "hard"}])):
        rc, calls = run(2, {"verdict": "hard_block", "trips": trips}, live=99, M=M)
        ck("⑪ 비-load hard(%s) → 재측정 0 · 즉시 부트 중단(9) · 알림 1회" % label,
           rc == M.EXIT_RESOURCE_HARD and len(calls) == 1 and SLEEPS == [], (rc, calls, SLEEPS))


a2_axes(B)
check("⑩ 간격 env 파싱 — 불량·음수·inf 는 기본 30 · 0 은 허용(회수 상한은 env 로 불변)",
      [B._recheck_interval_s(v) for v in ("abc", "-1", "inf", "nan", "0", "12.5", None)]
      == [30.0, 30.0, 30.0, 30.0, 0.0, 12.5, 30.0],
      [B._recheck_interval_s(v) for v in ("abc", "-1", "inf", "nan", "0", "12.5", None)])

# M1 — 재측정 루프 제거(즉시 exit 9 로 회귀) → ⑧·⑨ 가 적색이어야 한다.
import importlib.util  # noqa: E402
_src = open(os.path.join(BIN, "javis_bootstrap.py"), encoding="utf-8").read()
_anchor = '    while (verdict == "hard-block" and _hard_is_transient_load(gate_json)'
check("M1 앵커 정확히 1곳(변이 적용 선-assert)", _src.count(_anchor) == 1, _src.count(_anchor))
if _src.count(_anchor) == 1:
    _mp = os.path.join(_ROOT, "javis_bootstrap_mut_a2.py")
    open(_mp, "w", encoding="utf-8").write(_src.replace(_anchor, "    while (False", 1))
    _spec = importlib.util.spec_from_file_location("javis_bootstrap_mut_a2", _mp)
    _Mm = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_Mm)
    check("M1 변이 적용 확인(변이 모듈에 루프 부재)", _anchor not in open(_mp, encoding="utf-8").read())
    _sink = []
    try:
        a2_axes(_Mm, _sink)
    except Exception as e:  # noqa: BLE001 — 크래시도 적색(= 잡힘)
        _sink.append("크래시 %s" % type(e).__name__)
    check("M1 재측정 루프 제거 → 적색(KILLED) — %s" % _sink, bool(_sink), _sink)
_anchor2 = "    return bool(hard) and all(t.get(\"metric\") in RESOURCE_GATE_RECHECK_METRICS for t in hard)"
check("M2 앵커 정확히 1곳(변이 적용 선-assert)", _src.count(_anchor2) == 1, _src.count(_anchor2))
if _src.count(_anchor2) == 1:
    _mp2 = os.path.join(_ROOT, "javis_bootstrap_mut_a2n.py")
    open(_mp2, "w", encoding="utf-8").write(_src.replace(_anchor2, "    return True", 1))
    _spec2 = importlib.util.spec_from_file_location("javis_bootstrap_mut_a2n", _mp2)
    _Mm2 = importlib.util.module_from_spec(_spec2)
    _spec2.loader.exec_module(_Mm2)
    check("M2 변이 적용 확인(좁힘 술어 부재)", _anchor2 not in open(_mp2, encoding="utf-8").read())
    _sink2 = []
    try:
        a2_axes(_Mm2, _sink2)
    except Exception as e:  # noqa: BLE001
        _sink2.append("크래시 %s" % type(e).__name__)
    check("M2 load 한정 좁힘 제거 → 적색(KILLED) — %s" % _sink2, bool(_sink2), _sink2)

if fails:
    print("FAILED %d: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("RESOURCE-GATE-NOTIFY-RULE-OK")
