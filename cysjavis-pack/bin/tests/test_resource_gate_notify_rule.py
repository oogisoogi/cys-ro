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


def run(gate_exit, gate_json, live=None):
    calls = []
    B._notify_loud = lambda title, body: calls.append(title) or "feed"
    B._run_split = lambda cmd, timeout=120: (gate_exit, json.dumps(gate_json), "")
    B._live_node_count = lambda: live
    B._progress = lambda msg: None
    rc = B._run_resource_gate(sys.executable, _Log())
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


def run_windows_like(load_ratio=None, windows=True):
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
    try:
        B._run_split = _REAL_RUN_SPLIT
        B._live_node_count = _REAL_LIVE
        B._notify_loud = lambda title, body: calls.append(title) or "feed"
        B._progress = lambda msg: None
        log = _Log()
        rc = B._run_resource_gate(sys.executable, log)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    gate_step = [s for s in log.steps if s and s[0] == B.STEP.RESOURCE_GATE]
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

if fails:
    print("FAILED %d: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("RESOURCE-GATE-NOTIFY-RULE-OK")
