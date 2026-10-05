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
  ★1.1.8 병합(K53 = 원작자 U11 채택): 재측정 구현은 우리 cysr-102 A2(load_ratio · RECHECKS 6) 대신 원작자 U11
    (fleet_cpu_ratio 단독 hard · 벽시계 TOTAL 180 / INTERVAL 30 · env 는 줄이기만)이다. ⑧~⑪·M1·M2 는 같은 목적
    (기다리면 풀리는 부하만 다시 재고 · 최종 판정에서 알림 정확히 1회 · 해소되면 0회)을 U11 기준으로 잰다.
  ⑧ fleet_cpu hard 지속 → 재측정 6회(대기 6×30s · 가짜 시계) 뒤 9 · 알림 1회
  ⑪ 재확인 축 밖 hard(servers) · 복합(fleet+servers) → 재측정 0 · 즉시 9 · 알림 1회
  ⑨ 설치 직후 부하 흉내 — 게이트 출력 hard→hard→allow → 대기 2회 · 알림 0회 · 진행(exit 9 아님)
  ⑩ 간격 env(CYS_BOOT_RESOURCE_RECHECK_INTERVAL_S) 파싱 — 상한 30 · 하한 0.05(줄이기만)
  M1 뮤턴트(재확인 진입 제거) → ⑧·⑨ 적색 · M2 뮤턴트(fleet_cpu 한정 좁힘 제거) → ⑪ 적색(선-assert 동반)

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



class _FakeTime:
    """U11 재확인 루프의 벽시계·대기만 가짜로(실 대기 0 · 회차 결정론). 나머지는 실 time 모듈."""
    def __init__(self, real):
        self._real, self.now = real, 1000.0

    def monotonic(self):
        return self.now

    def sleep(self, s):
        SLEEPS.append(s)
        self.now += s

    def __getattr__(self, name):
        return getattr(self._real, name)


class _LogP(_Log):
    def progress(self, info):
        self.steps.append(("progress", info))


def _fleet_json(verdict="hard_block", extra_trips=(), fleet=True):
    trips = ([{"metric": "fleet_cpu_ratio", "level": "hard"}] if fleet else []) + list(extra_trips)
    return {"verdict": verdict, "trips": trips if verdict == "hard_block" else [],
            "measured": {"fleet_cpu_reason": "ok", "fleet_cpu_ratio": 1.4}}


def run_u11(seq, M):
    """(1.1.8 · K53 원작자 U11 채택) 게이트 출력 순서 seq=[(exit, json), …]를 차례로 내고(마지막 유지)
    U11 재확인 루프를 기본 상수(TOTAL 180·INTERVAL 30) 그대로 가짜 시계로 돌린다 → (rc, 알림, 측정 수)."""
    calls, n = [], [0]
    del SLEEPS[:]
    seq = list(seq)

    def _split(cmd, timeout=120):
        n[0] += 1
        code, js = seq.pop(0) if len(seq) > 1 else seq[0]
        return code, json.dumps(js), ""
    real_time = M.time
    M.time = _FakeTime(real_time)
    M._notify_loud = lambda title, body: calls.append(title) or "feed"
    M._run_split = _split
    M._live_node_count = lambda: 99
    M._progress = lambda msg: None
    M._live_master_from_status = lambda status, exclude_sid=None: (True, "master 생존(대역)")
    M._cys_status_json = lambda: {}
    try:
        rc = M._run_resource_gate(sys.executable, _LogP())
    finally:
        M.time = real_time
    return rc, calls, n[0]


def a2_axes(M, sink=None):
    """A2 축 ⑧⑨⑪ — U11(fleet_cpu 단독 hard 만 벽시계 상한 안 재확인) 기준. sink 가 있으면 출력 없이
    실패 이름만 모은다(뮤턴트 판정용). 지키는 목적은 종전과 같다: 기다리면 풀리는 부하만 다시 재고,
    알림은 최종 판정에서 정확히 1회(해소되면 0회)."""
    def ck(name, ok, detail=""):
        if sink is None:
            check(name, ok, detail)
        elif not ok:
            sink.append(name)
    rounds = M._recheck_rounds(M.RESOURCE_RECHECK_TOTAL_S, M.RESOURCE_RECHECK_INTERVAL_S)
    rc, calls, n = run_u11([(2, _fleet_json())], M)
    ck("⑧ fleet_cpu hard 지속 → 대기 정확히 %d회×%ds 뒤 부트 중단(9) · 알림 1회"
       % (rounds, M.RESOURCE_RECHECK_INTERVAL_S),
       rc == M.EXIT_RESOURCE_HARD and len(calls) == 1 and SLEEPS == [30.0] * 6 and n == 7
       and (rounds, M.RESOURCE_RECHECK_INTERVAL_S) == (6, 30.0), (rc, calls, SLEEPS, n))
    rc, calls, n = run_u11([(2, _fleet_json()), (2, _fleet_json()), (0, _fleet_json("allow"))], M)
    ck("⑨ 설치 직후 부하 흉내(hard→hard→allow) → 대기 2회 · 3번째 측정 allow · 알림 0 · 진행",
       rc is None and calls == [] and SLEEPS == [30.0, 30.0] and n == 3, (rc, calls, SLEEPS, n))
    for label, js in (("servers 단독", _fleet_json(extra_trips=[{"metric": "servers", "level": "hard"}],
                                                   fleet=False)),
                      ("fleet+servers 복합", _fleet_json(extra_trips=[{"metric": "servers", "level": "hard"}]))):
        rc, calls, n = run_u11([(2, js)], M)
        ck("⑪ 재확인 축 밖 hard(%s) → 재측정 0 · 즉시 부트 중단(9) · 알림 1회" % label,
           rc == M.EXIT_RESOURCE_HARD and len(calls) == 1 and SLEEPS == [] and n == 1, (rc, calls, SLEEPS, n))


a2_axes(B)


def _env_s(v):
    saved = os.environ.get("CYS_BOOT_RESOURCE_RECHECK_INTERVAL_S")
    if v is None:
        os.environ.pop("CYS_BOOT_RESOURCE_RECHECK_INTERVAL_S", None)
    else:
        os.environ["CYS_BOOT_RESOURCE_RECHECK_INTERVAL_S"] = v
    try:
        return B._env_capped_seconds("CYS_BOOT_RESOURCE_RECHECK_INTERVAL_S", B.RESOURCE_RECHECK_INTERVAL_CAP_S,
                                     B.RESOURCE_RECHECK_INTERVAL_FLOOR_S)
    finally:
        if saved is None:
            os.environ.pop("CYS_BOOT_RESOURCE_RECHECK_INTERVAL_S", None)
        else:
            os.environ["CYS_BOOT_RESOURCE_RECHECK_INTERVAL_S"] = saved


_got = [_env_s(v) for v in ("abc", "-1", "inf", "nan", "0", "12.5", "99", None)]
check("⑩ 간격 env 파싱 — 불량·inf·nan·미설정은 상한 30 · 음수·0 은 하한 0.05 · 상한 위는 30(줄이기만)",
      _got == [30.0, 0.05, 30.0, 30.0, 0.05, 12.5, 30.0, 30.0], _got)

# M1 — 재확인 진입 제거(즉시 exit 9 로 회귀) → ⑧·⑨ 가 적색이어야 한다.
import importlib.util  # noqa: E402
_src = open(os.path.join(BIN, "javis_bootstrap.py"), encoding="utf-8").read()
_anchor = "    if RESOURCE_RECHECK_TOTAL_S > 0 and _resource_recheckable(verdict, gate_json):"
check("M1 앵커 정확히 1곳(변이 적용 선-assert)", _src.count(_anchor) == 1, _src.count(_anchor))
if _src.count(_anchor) == 1:
    _mp = os.path.join(_ROOT, "javis_bootstrap_mut_a2.py")
    open(_mp, "w", encoding="utf-8").write(_src.replace(_anchor, "    if False:", 1))
    _spec = importlib.util.spec_from_file_location("javis_bootstrap_mut_a2", _mp)
    _Mm = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_Mm)
    check("M1 변이 적용 확인(변이 모듈에 재확인 진입 부재)", _anchor not in open(_mp, encoding="utf-8").read())
    _sink = []
    try:
        a2_axes(_Mm, _sink)
    except Exception as e:  # noqa: BLE001 — 크래시도 적색(= 잡힘)
        _sink.append("크래시 %s" % type(e).__name__)
    check("M1 재확인 루프 제거 → 적색(KILLED) — %s" % _sink, bool(_sink), _sink)
_anchor2 = "    return bool(hard) and all(t.get(\"metric\") in RESOURCE_RECHECK_AXES for t in hard)"
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
    check("M2 fleet_cpu 한정 좁힘 제거 → 적색(KILLED) — %s" % _sink2, bool(_sink2), _sink2)

if fails:
    print("FAILED %d: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("RESOURCE-GATE-NOTIFY-RULE-OK")
