#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_psaxis_self_pid.py — ps 축이 「좌석 pid 자신이 에이전트」 인 좌석을 살아 있다고 보는가(TICKET=cysr-1118u-debug · 1.1.18 · 데몬 불요).

결함(윈 실기 1.1.17 관찰 ④ 의 맥 쪽 원인 · u17 VM 저널 실측): 설치기 wake 경로 master 좌석(`cys new-surface --cmd 'bash wake.sh'` ·
wake.sh 끝 = `exec "$CLAUDE" …`)은 셸이 claude 로 바뀌어 **좌석 pid 자신이 claude** 이고 자식이 없다. agent_process_verdict 는 좌석 pid 의
자손만 보고 자기 자신은 건너뛰어 dead → 같은 대화(expected == observed)인데 UNVERIFIED · 다음 회차 재대상(「이미 가동 중 — 건너뜀」).
수리: 좌석 pid 의 **실행 파일**(따옴표 경로 · basename · .exe 뗌) 또는 node/bun 의 옵션 뒤 첫 인자가 **알려진 에이전트 진입점**일 때만 alive.
인자 부분 문자열로 보지 않는다 — 셸 `-c 'claude …; exec zsh'` 에서 claude 가 죽은 좌석을 alive 로 세면 거짓 verified(A3 가 막는 방향).

  T  진리표 12칸(설치기 wake · node 진입점 · 셸 잔존 · 보통 좌석 · 표 밖 · codex 1R 반례 X1~X3·Q1~Q3)
  M1 뮤턴트(자기 판정 제거 · 변이 적용 선-assert) → W·N·Q1·Q2 적색
  M2 뮤턴트(실행 파일 대신 인자 부분 문자열) → D·X1·Q3 적색

실행: python3 cysjavis-pack/bin/tests/test_phoenix_psaxis_self_pid.py → 종료 토큰 PHOENIX-PSAXIS-SELF-PID-OK
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.normpath(os.path.join(HERE, "..", "javis_phoenix.py"))
fails = []

CASES = [
    ("W 설치기 wake.sh exec claude = 좌석 pid 자신이 claude(자식 0)", {100: (1, "/opt/dummy/.local/bin/claude --dangerously-skip-permissions hi")}, "alive"),
    ("N node 꼴 claude 진입점이 좌석 pid 자신", {100: (1, "node /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js --resume X")}, "alive"),
    ("D 셸 -c 'claude …; exec zsh' 인데 claude 죽음(dead 유지)", {100: (1, "/bin/zsh -l -c claude --resume X; exec zsh")}, "dead"),
    ("S 보통 좌석(셸 아래 claude 자식)", {100: (1, "-zsh"), 101: (100, "claude --resume X")}, "alive"),
    ("E 보통 좌석 claude 죽음", {100: (1, "-zsh")}, "dead"),
    ("U 셸 pid 표에 없음", {101: (1, "claude")}, "unknown"),
    ("X1 node 진입점 아님 /tmp/claude-monitor.js", {100: (1, "node /tmp/claude-monitor.js")}, "dead"),
    ("X2 node /tmp/agy/audit.js", {100: (1, "node /tmp/agy/audit.js")}, "dead"),
    ("X3 node --require=/tmp/claude-debug.js /tmp/audit.js", {100: (1, "node --require=/tmp/claude-debug.js /tmp/audit.js")}, "dead"),
    ("Q1 윈 따옴표 \"C:\\Tools\\claude.exe\"", {100: (1, '"C:\\Tools\\claude.exe" --resume X')}, "alive"),
    ("Q2 윈 공백 경로 \"C:\\Program Files\\Claude\\claude.exe\"", {100: (1, '"C:\\Program Files\\Claude\\claude.exe" --resume X')}, "alive"),
    ("Q3 claude-monitor 실행 파일(부분 일치 아님)", {100: (1, "/usr/local/bin/claude-monitor --watch")}, "dead"),
]


def load_src(src, name, d):
    path = os.path.join(d, name + ".py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def table_axes(m, report=True):
    red = []
    for name, table, want in CASES:
        got = m.agent_process_verdict(100, "claude", table)
        if report:
            print("%s %s → %s (want %s)" % ("PASS" if got == want else "FAIL", name, got, want))
            if got != want:
                fails.append(name)
        if got != want:
            red.append(name.split()[0])
    return red


def main():
    with open(PH, encoding="utf-8") as f:
        src = f.read()
    tmp = tempfile.mkdtemp(prefix="ph-psaxis-")
    table_axes(load_src(src, "ph_base", tmp))
    a = "    if _self_is_agent((table.get(shell_pid) or (None, \"\"))[1], tokens):\n        return \"alive\"\n"
    n = src.count(a)
    print("%s M1 자기 판정 제거 변이 선-assert(정확 1곳) — count=%d" % ("PASS" if n == 1 else "FAIL", n))
    if n != 1:
        fails.append("M1 선-assert")
    else:
        red = table_axes(load_src(src.replace(a, ""), "ph_m1", tmp), report=False)
        ok = set(red) == {"W", "N", "Q1", "Q2"}
        print("%s M1 자기 판정 제거 → KILLED(W·N·Q1·Q2 적색) — 적색=%s" % ("PASS" if ok else "FAIL", red))
        if not ok:
            fails.append("M1")
    b = "    if exe in tokens:\n        return True\n"
    n = src.count(b)
    print("%s M2 부분 문자열 변이 선-assert(정확 1곳) — count=%d" % ("PASS" if n == 1 else "FAIL", n))
    if n != 1:
        fails.append("M2 선-assert")
    else:
        m2 = src.replace(b, "    if any(t in (cmdline or \"\").lower() for t in tokens):\n        return True\n")
        red = table_axes(load_src(m2, "ph_m2", tmp), report=False)
        ok = {"D", "X1", "Q3"} <= set(red)
        print("%s M2 부분 문자열 → KILLED(D·X1·Q3 적색) — 적색=%s" % ("PASS" if ok else "FAIL", red))
        if not ok:
            fails.append("M2")
    if fails:
        print("FAIL 합계 %d: %s" % (len(fails), fails))
        sys.exit(1)
    print("PHOENIX-PSAXIS-SELF-PID-OK")


if __name__ == "__main__":
    main()
