#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_psaxis_self_pid.py — ps 축이 「좌석 pid 자신이 에이전트」 인 좌석을 살아 있다고 보는가(TICKET=cysr-1118u-debug · 1.1.18 · 데몬 불요).

결함(윈 실기 1.1.17 관찰 ④ 의 맥 쪽 원인 · u17 VM 저널 실측): 설치기 wake 경로 master 좌석(`cys new-surface --cmd 'bash wake.sh'` ·
wake.sh 끝 = `exec "$CLAUDE" …`)은 셸이 claude 로 바뀌어 **좌석 pid 자신이 claude** 이고 자식이 없다. agent_process_verdict 는 좌석 pid 의
자손만 보고 자기 자신은 건너뛰어 dead → 같은 대화(expected == observed)인데 UNVERIFIED · 다음 회차 재대상(「이미 가동 중 — 건너뜀」).
수리: 좌석 pid 의 **실행 파일**(따옴표 경로 · basename · .exe 뗌) 또는 node/bun 의 옵션 뒤 첫 인자가 **알려진 에이전트 진입점**일 때만 alive.
인자 부분 문자열로 보지 않는다 — 셸 `-c 'claude …; exec zsh'` 에서 claude 가 죽은 좌석을 alive 로 세면 거짓 verified(A3 가 막는 방향).

  T  진리표 12칸(설치기 wake · node 진입점 · 셸 잔존 · 보통 좌석 · 표 밖 · codex 1R 반례 X1~X3·Q1~Q3)
     + 독립 검증 2390 칸(V1~V8 · C1~C5 · codex 생존 변이 칸 K1~K3 · comm 으로 넘긴 실행 경로 P1~P3) — REVISE ①대소문자 ②node 옵션 ③공백 경로
  M1 뮤턴트(자기 판정 제거 · 변이 적용 선-assert) → W·N·Q1·Q2 적색
  M2 뮤턴트(실행 파일 대신 인자 부분 문자열) → D·X1·Q3 적색
  M3~M15 뮤턴트(검증자 M3~M11 · codex 3종 · REVISE 고침 되돌리기 4종) → 전부 KILLED
  ⚠알려진 한계(막지 않음 · 2390 기록): pid 재사용 결속 없음(C6) · `exec -a claude` 위장(R4) · comm 없는 표에서 공백 경로 CLI = 거짓 dead(C2)

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
    # ── 독립 검증 2390(VERIFY-628e4ce28.md) 칸 ──
    ("V1 node 값 붙은 옵션 뒤 진입점", {100: (1, "node --max-old-space-size=4096 /usr/lib/node_modules/@anthropic-ai/claude-code/cli.js")}, "alive"),
    ("V2 node 앞 스크립트 무관 · 뒤 인자에 진입점", {100: (1, "node /tmp/audit.js /usr/lib/node_modules/@anthropic-ai/claude-code/cli.js")}, "dead"),
    ("V3 맥 Claude 데스크톱 앱", {100: (1, "/Applications/Claude.app/Contents/MacOS/Claude")}, "dead"),
    ("V4 맥 Claude Helper(공백 경로 무따옴표)", {100: (1, "/Applications/Claude.app/Contents/Frameworks/Claude Helper.app/Contents/MacOS/Claude Helper --type=gpu-process")}, "dead"),
    ("V5 좀비", {100: (1, "<defunct>")}, "dead"),
    ("V6 bun 진입점", {100: (1, "bun /x/node_modules/@anthropic-ai/claude-code/cli.js")}, "alive"),
    ("V7 node -r 값이 진입점 · 본 스크립트 무관", {100: (1, "node -r /x/node_modules/@anthropic-ai/claude-code/cli.js server.js")}, "dead"),
    ("V8 우리 좌석 꼴(~/.local/bin/claude 직접)", {100: (1, "/opt/dummy/.local/bin/claude --model x --dangerously-skip-permissions")}, "alive"),
    ("C1 무따옴표 공백 경로 /tmp/claude tools/helper(comm 없음)", {100: (1, "/tmp/claude tools/helper --watch")}, "dead"),
    ("C3 POSIX 대문자 /tmp/Claude", {100: (1, "/tmp/Claude --watch")}, "dead"),
    ("C4 node --check cli.js(구문 검사)", {100: (1, "node --check /tmp/@anthropic-ai/claude-code/cli.js")}, "dead"),
    ("C4b node -e 인라인", {100: (1, "node -e require('/x/@anthropic-ai/claude-code/cli.js')")}, "dead"),
    ("C5 node --title worker cli.js(값 받는 옵션)", {100: (1, "node --title worker /tmp/@anthropic-ai/claude-code/cli.js")}, "alive"),
    ("K1 codex 진입점(목록 축소 변이)", {100: (1, "node /usr/lib/node_modules/@openai/codex/bin/codex.js")}, "alive"),
    ("K2 node --no-warnings cli.js(words[1] 변이)", {100: (1, "node --no-warnings /usr/lib/node_modules/@anthropic-ai/claude-code/cli.js")}, "alive"),
    ("K3 bun run 진입점", {100: (1, "bun run /x/node_modules/@anthropic-ai/claude-code/cli.js")}, "alive"),
    ("Q4 윈 대문자 CLAUDE.EXE(.exe 뗀 토큰만 대소문자 무시)", {100: (1, '"C:\\Tools\\CLAUDE.EXE" --resume X')}, "alive"),
    ("P1 comm 실행 경로 = 공백 경로 CLI(C2)", {100: (1, "/opt/A B/.local/bin/claude --resume X")}, "alive", "/opt/A B/.local/bin/claude"),
    ("P2 comm 실행 경로 = /tmp/claude tools/helper(C1)", {100: (1, "/tmp/claude tools/helper --watch")}, "dead", "/tmp/claude tools/helper"),
    ("P3 comm 실행 경로 = Claude Helper", {100: (1, "/Applications/Claude.app/Contents/Frameworks/Claude Helper.app/Contents/MacOS/Claude Helper --type=gpu-process")}, "dead",
     "/Applications/Claude.app/Contents/Frameworks/Claude Helper.app/Contents/MacOS/Claude Helper"),
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
    for case in CASES:
        name, table, want = case[:3]
        got = m.agent_process_verdict(100, "claude", table, case[3] if len(case) > 3 else None)
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
    a = "    if _self_is_agent((table.get(shell_pid) or (None, \"\"))[1], tokens, self_exe):\n        return \"alive\"\n"
    n = src.count(a)
    print("%s M1 자기 판정 제거 변이 선-assert(정확 1곳) — count=%d" % ("PASS" if n == 1 else "FAIL", n))
    if n != 1:
        fails.append("M1 선-assert")
    else:
        red = table_axes(load_src(src.replace(a, ""), "ph_m1", tmp), report=False)
        ok = {"W", "N", "Q1", "Q2", "V8", "P1"} <= set(red)
        print("%s M1 자기 판정 제거 → KILLED(W·N·Q1·Q2·V8·P1 적색) — 적색=%s" % ("PASS" if ok else "FAIL", red))
        if not ok:
            fails.append("M1")
    b = "    if exe in tokens and bounded:\n        return True\n"
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
    # 검증자 M3~M11 · codex 생존 3종 · REVISE 고침 되돌리기 — 각 변이 = (찾을 원문, 바꿀 글) · 정확 1곳 선-assert · 저자 칸 적색이 1개 이상이면 KILLED
    MUT = [
        ("M3 .exe 떼기 제거", '    exe = raw[:-4].lower() if win else raw\n', '    exe = raw.lower() if win else raw\n'),
        ("M4 따옴표 무시(split)", '    words = _argv_words(cmdline)\n    if self_exe:', '    words = (cmdline or "").split()\n    if self_exe:'),
        ("M5 node 아무 인자나 진입점", '        script = _node_entry_script(args) or ""\n',
         '        script = next((w for w in args if w.replace("\\\\", "/").endswith(_AGENT_NODE_ENTRY_SUFFIXES)), "")\n'),
        ("M6 대소문자 무조건 무시(종전 lower)", '    exe = raw[:-4].lower() if win else raw\n', '    exe = raw[:-4].lower() if win else raw.lower()\n'),
        ("M7 옵션 건너뛰기 제거(args[0])", '        script = _node_entry_script(args) or ""\n', '        script = args[0] if args else ""\n'),
        ("M8 node/bun 갈래 제거", '    if exe in ("node", "bun"):\n', '    if False:\n'),
        ("M11 접두 일치", '    if exe in tokens and bounded:\n', '    if exe.startswith(tuple(tokens)) and bounded:\n'),
        ("M12 bun 갈래 제거(codex)", '    if exe in ("node", "bun"):\n', '    if exe == "node":\n'),
        ("M13 진입점 목록 claude 하나(codex)", '_AGENT_NODE_ENTRY_SUFFIXES = ("/@anthropic-ai/claude-code/cli.js", "/@openai/codex/bin/codex.js", "/@google/gemini-cli/dist/index.js")',
         '_AGENT_NODE_ENTRY_SUFFIXES = ("/@anthropic-ai/claude-code/cli.js",)'),
        ("M14 실행 안 하는 옵션 거부 제거", '            if name in _NODE_NON_EXEC_OPTS or (not w.startswith("--") and set(w[1:]) & {"c", "e", "p"}):\n                return None\n', ''),
        ("M15 값 받는 옵션 건너뛰기 제거", '            if name in _NODE_VALUE_OPTS and "=" not in w:\n                skip = True\n', ''),
        ("M16 경계 모호 판정 제거", '        exe_path, args, bounded = words[0], words[1:], not (len(words) > 1 and not words[1].startswith("-") and "/" in words[1])\n',
         '        exe_path, args, bounded = words[0], words[1:], True\n'),
        ("M17 comm(self_exe) 무시", '    if self_exe:\n        rest =', '    if False:\n        rest ='),
        ("M18 bun run 건너뛰기 제거", '        if w == "run" and i == 0:\n            continue  # `bun run <script>`\n', ''),
    ]
    for name, a2, b2 in MUT:
        n = src.count(a2)
        if n != 1:
            print("FAIL %s 선-assert(정확 1곳) — count=%d" % (name, n))
            fails.append(name + " 선-assert")
            continue
        red = table_axes(load_src(src.replace(a2, b2), "ph_mut", tmp), report=False)
        print("%s %s → %s — 적색=%s" % ("PASS" if red else "FAIL", name, "KILLED" if red else "SURVIVED", red))
        if not red:
            fails.append(name)
    if fails:
        print("FAIL 합계 %d: %s" % (len(fails), fails))
        sys.exit(1)
    print("PHOENIX-PSAXIS-SELF-PID-OK")


if __name__ == "__main__":
    main()
