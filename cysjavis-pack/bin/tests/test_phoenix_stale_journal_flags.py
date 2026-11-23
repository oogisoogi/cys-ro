#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_stale_journal_flags.py — 앞 실행의 fresh 표식이 이번 resume 성공 verify 로 새지 않는가(TICKET=cysr-1118u-debug · 1.1.18 · 데몬 불요).

결함(윈 1.1.17 관찰 ④ · 1.1.18 rc1 실측): 저널(journal-default.json · 실행·재부팅을 넘어 남음)의 역할 표식 fresh_expected·fresh_reason·
fresh_fallback·fresh_pre_*·fresh_evidence 는 세우는 곳만 있고 지우는 곳이 없었다 → 같은 회차 「F-1 예상 근거」 = 4좌석 예상=resume 인데
판정 = master no_session_file(unverified) · cso cli_fresh(unverified) · worker poison(fresh) · 실제는 4좌석 원 대화 resume.
수리: 이번 실행에 cys restore 로 선 역할은 spawn 성공 지점에서 앞 실행 표식 6종을 지우고 이번 근거로만 다시 세운다(판정 규칙 자체는 그대로).

  A 앞 실행 fresh_expected/no_session_file 잔존 + 이번엔 resume · 같은 대화 → verified · 표식 0
  B 앞 실행 cli_fresh 잔존 → verified · 표식 0
  C 앞 실행 fresh_fallback/poison 잔존 → verified(「독약 강등」 아님) · 표식 0
  D 대조군(표식 없음) → verified
  E 이번 실행이 정말 fresh 를 예상하면(no_session_file) 표식이 이번 근거로 다시 선다(지우기가 진짜 예상까지 지우지 않음)
  F (2396) 앞 F-1 잔존 + 이번엔 resume 예상이나 CLI 가 새 대화로 띄움 관측 → fresh_expected · reason=cli_fresh(이번 근거)
  G (2396) 앞 독약 잔존 + resume 은 됐으나 다른 대화 관측 → unverified fork(앞 독약 표식이 오복원을 「독약 강등」 으로 덮지 않음)
  H (2396 R1) 앞 F-1 잔존 + 이번 실행은 독약 강등 갈래(force_fresh) → fresh(poison) · 앞 fresh_expected·fresh_pre_*·fresh_evidence 0
  M 뮤턴트(지우기 제거 · 변이 적용 선-assert) → A·B·C 적색 · M-R1(독약 갈래 지우기 제거) → H 적색

실행: python3 cysjavis-pack/bin/tests/test_phoenix_stale_journal_flags.py → 종료 토큰 PHOENIX-STALE-JOURNAL-FLAGS-OK
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pw_harness", os.path.join(HERE, "test_phoenix_poison_why.py"))
pw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pw)  # 같은 생산 경로 대역 하네스(scenario) 재사용 — main() 은 돌지 않는다
FLAGS = ("fresh_expected", "fresh_reason", "fresh_fallback", "fresh_pre_dir", "fresh_pre_sids", "fresh_evidence")
ALIVE = [{"surface": "surface:5", "pid": 50, "exited": False, "agent_alive": True, "seat": "occupied"}]
CASES = [
    ("A", "앞 실행 F-1 표식(no_session_file) 잔존", {"fresh_expected": True, "fresh_reason": "no_session_file", "fresh_pre_dir": "/x", "fresh_pre_sids": ["S1"]}),
    ("B", "앞 실행 cli_fresh 잔존", {"fresh_expected": True, "fresh_reason": "cli_fresh", "fresh_evidence": {"provenance": "pre_existing"}}),
    ("C", "앞 실행 독약 강등 잔존", {"fresh_fallback": True, "fresh_reason": "poison"}),
    ("D", "대조군(표식 없음)", {"x": 1}),
]
fails = []


def run_axes(src, tmp, tag, report=True):
    red = []
    for key, name, pre in CASES:
        r, f, j, logs, res = pw.scenario(src, tmp, tag + key.lower(), pw.QUIET_OUT, ALIVE, preload=pre, revive=True, observed="S1")
        rr = j["roles"]["master"]
        left = [k for k in FLAGS if k in rr]
        ok = (r, f) == (1, 0) and rr.get("outcome") == "verified" and not left
        if report:
            print("%s %s %s → restore %d fresh %d · outcome=%s · 남은 표식=%s" % ("PASS" if ok else "FAIL", key, name, r, f, rr.get("outcome"), left))
            if not ok:
                fails.append(key)
        if not ok:
            red.append(key)
    if report:
        r, f, j, logs, res = pw.scenario(src, tmp, tag + "e", pw.QUIET_OUT, ALIVE, preload={"x": 1}, revive=True, observed="S1",
                                         fresh_pred=(True, "no_session_file"))
        rr = j["roles"]["master"]
        ok = rr.get("fresh_expected") is True and rr.get("fresh_reason") == "no_session_file"
        print("%s E 이번 실행 진짜 fresh 예상 → 표식이 이번 근거로 다시 섬(fresh_expected=%s · reason=%s)"
              % ("PASS" if ok else "FAIL", rr.get("fresh_expected"), rr.get("fresh_reason")))
        if not ok:
            fails.append("E")
    red += extra_axes(src, tmp, tag, report)
    return red


def extra_axes(src, tmp, tag, report=True):
    """F·G·H(독립 검증 2396 · R1) — (키, 통과 여부) 판정 후 적색 키 목록."""
    out = []
    r, f, j, logs, res = pw.scenario(src, tmp, tag + "f", pw.QUIET_OUT, ALIVE, revive=True, observed="S1", cli_fresh=True,
                                     preload={"fresh_expected": True, "fresh_reason": "no_session_file", "fresh_pre_dir": "/x"})
    rr = j["roles"]["master"]
    out.append(("F", rr.get("fresh_expected") is True and rr.get("fresh_reason") == "cli_fresh" and rr.get("fresh_pre_dir") != "/x",
                "fresh_expected=%s reason=%s pre_dir=%r" % (rr.get("fresh_expected"), rr.get("fresh_reason"), rr.get("fresh_pre_dir"))))
    r, f, j, logs, res = pw.scenario(src, tmp, tag + "g", pw.QUIET_OUT, ALIVE, revive=True, observed="S-OTHER",
                                     preload={"fresh_fallback": True, "fresh_reason": "poison"})
    rr = j["roles"]["master"]
    out.append(("G", rr.get("outcome") == "unverified" and "fork" in (rr.get("verify_reason") or "") and not rr.get("fresh_fallback"),
                "outcome=%s fresh_fallback=%s" % (rr.get("outcome"), rr.get("fresh_fallback"))))
    r, f, j, logs, res = pw.scenario(src, tmp, tag + "h", pw.FAIL_OUT, [], revive=False,
                                     preload={"force_fresh": True, "fresh_expected": True, "fresh_reason": "no_session_file",
                                              "fresh_pre_dir": "/x", "fresh_pre_sids": ["S1"], "fresh_evidence": {"provenance": "pre_existing"}})
    rr = j["roles"]["master"]
    left = [k for k in ("fresh_expected", "fresh_pre_dir", "fresh_pre_sids", "fresh_evidence") if k in rr]
    out.append(("H", f == 1 and rr.get("outcome") == "fresh" and rr.get("fresh_reason") == "poison" and rr.get("fresh_fallback") is True and not left,
                "fresh 호출 %d · outcome=%s reason=%s · 남은 앞 표식=%s" % (f, rr.get("outcome"), rr.get("fresh_reason"), left)))
    red = []
    for key, ok, detail in out:
        if report:
            print("%s %s → %s" % ("PASS" if ok else "FAIL", key, detail))
            if not ok:
                fails.append(key)
        if not ok:
            red.append(key)
    return red


def main():
    with open(pw.PH, encoding="utf-8") as f:
        src = f.read()
    tmp = tempfile.mkdtemp(prefix="ph-stale-")
    run_axes(src, tmp, "base")
    a = ('                    for _k in ("fresh_expected", "fresh_reason", "fresh_fallback", "fresh_pre_dir", "fresh_pre_sids", "fresh_evidence"):\n'
         '                        j["roles"][role].pop(_k, None)\n')
    n = src.count(a)
    print("%s M 지우기 제거 변이 선-assert(정확 1곳) — count=%d" % ("PASS" if n == 1 else "FAIL", n))
    if n != 1:
        fails.append("M 선-assert")
    else:
        red = run_axes(src.replace(a, ""), tmp, "mut", report=False)
        ok = {"A", "B", "C"} <= set(red) and "D" not in red
        print("%s M 지우기 제거 → KILLED(A·B·C 적색 · D 녹) — 적색=%s" % ("PASS" if ok else "FAIL", red))
        if not ok:
            fails.append("M")
    b = ('                for _stale in ("fresh_expected", "fresh_reason", "fresh_fallback", "fresh_pre_dir", "fresh_pre_sids", "fresh_evidence"):\n'
         '                    rr.pop(_stale, None)\n')
    n = src.count(b)
    print("%s M-R1 독약 갈래 지우기 제거 변이 선-assert(정확 1곳) — count=%d" % ("PASS" if n == 1 else "FAIL", n))
    if n != 1:
        fails.append("M-R1 선-assert")
    else:
        red = run_axes(src.replace(b, ""), tmp, "mr1", report=False)
        ok = "H" in red and "D" not in red
        print("%s M-R1 독약 갈래 지우기 제거 → KILLED(H 적색) — 적색=%s" % ("PASS" if ok else "FAIL", red))
        if not ok:
            fails.append("M-R1")
    if fails:
        print("FAIL 합계 %d: %s" % (len(fails), fails))
        sys.exit(1)
    print("PHOENIX-STALE-JOURNAL-FLAGS-OK")


if __name__ == "__main__":
    main()
