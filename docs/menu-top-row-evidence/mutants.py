#!/usr/bin/env python3
# 뮤턴트 — 상담소·아고라 상단 이동(TICKET=cysr-menu-top-row). 각 뮤턴트가 시험(단위 + 헤드리스) 중 적어도 하나를 빨강으로 만드는지 잰다.
# usage: python3 mutants.py <작업트리 ui 폴더> <scratch 폴더> <chrome-headless-shell>  → 표 출력 · 하나라도 초록이면 exit 1
# 원본은 건드리지 않는다 — ui 를 scratch 로 복사해 그 사본을 고치고 빌드·시험한다.
import os, shutil, subprocess, sys

UI, SCR, CHS = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
UNIT = ["src/counselwiring.test.ts", "src/feedbacktop.test.ts", "src/topbarlayout.test.ts"]

TOP_PAIR = ('<button id="btn-counsel" title="상담소 — cysr 사용자들이 묻고 받은 답을 한곳에서 봅니다(보기 전용)">상담소 <span id="counsel-badge" class="badge" hidden>0</span></button>'
            '<button id="btn-agora" title="아고라 — AI 동료들이 토론하는 광장을 봅니다(보기 전용) · 참여는 마스터에게 말로 부탁하세요">아고라</button>')
COUNSEL, AGORA = TOP_PAIR.split("</button>", 1)[0] + "</button>", TOP_PAIR.split("</button>", 1)[1]
EQ = '    <button id="btn-equalize"'


def m_reverse(f):  # 순서 뒤집기 — 아고라가 상담소보다 앞
    return {"index.html": f["index.html"].replace(TOP_PAIR, AGORA + COUNSEL)}


def m_after_equalize(f):  # 피드백 바로 뒤가 아니라 정렬 뒤
    h = f["index.html"].replace("    " + TOP_PAIR + "\n", "")
    i = h.index("\n", h.index(EQ)) + 1
    return {"index.html": h[:i] + "    " + TOP_PAIR + "\n" + h[i:]}


def m_left_remains(f):  # 왼쪽 잔존 — 상단에 옮겼지만 사이드바 줄도 남김
    h = f["index.html"].replace('      <div id="ws-tabs"></div>\n', '      <div id="ws-tabs"></div>\n      <div id="ws-counsel-row">' + TOP_PAIR + "</div>\n")
    return {"index.html": h}


def m_append_end(f):  # 저장된 배치의 새 단추 = 맨 끝(종전 규칙으로 되돌림)
    t = f["src/topbarlayout.ts"]
    a = t.index("  domIds.forEach((id, i) => {")
    b = t.index("  });\n", a) + len("  });\n")
    return {"src/topbarlayout.ts": t[:a] + "  for (const id of domIds) if (!seen.has(id)) out.push({ id, on: true });\n" + t[b:]}


def m_no_narrow(f):  # 좁은 창 여백 규칙 제거
    c = f["src/style.css"]
    a = c.index("@media (max-width: 900px) {\n  #topbar button { padding: 4px 8px; }")
    b = c.index("}\n}\n", a) + 4
    return {"src/style.css": c[:a] + c[b:]}


MUTANTS = [("M1 순서 뒤집기(아고라 · 상담소)", m_reverse, "m1,m3"),
           ("M2 정렬 뒤에 놓기", m_after_equalize, "m1,m3"),
           ("M3 왼쪽 잔존(사이드바 줄 남김)", m_left_remains, "m1"),
           ("M4 저장 배치 새 단추 = 맨 끝", m_append_end, "m5"),
           ("M5 좁은 창 여백 규칙 제거", m_no_narrow, "m4")]


def run(cmd, cwd, env=None):
    p = subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


rows, green = [], 0
for name, fn, only in MUTANTS:
    work = os.path.join(SCR, "mut-ui")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(UI, work, symlinks=True, ignore=shutil.ignore_patterns("dist"))
    files = {k: open(os.path.join(work, k), encoding="utf-8").read() for k in ("index.html", "src/topbarlayout.ts", "src/style.css")}
    changed = fn(files)
    for k, v in changed.items():
        assert v != files[k], f"{name}: 변이 적용 실패({k})"
        open(os.path.join(work, k), "w", encoding="utf-8").write(v)
    urc, uout = run(["bun", "test", *UNIT], work)
    ufail = [l.strip()[:90] for l in uout.splitlines() if l.startswith("(fail)")]
    brc, bout = run(["sh", "build.sh"], work)
    assert brc == 0, bout
    hrc, hout = run(["bun", os.path.join(HERE, "menu-top-row-headless.ts")], HERE, {"DIST": os.path.join(work, "dist"), "CHS": CHS, "ONLY": only})
    hfail = [l[:90] for l in hout.splitlines() if l.startswith("FAIL m")]
    red = urc != 0 or hrc != 0
    green += not red
    rows.append((name, "빨강" if red else "★초록(놓침)", len(ufail), ufail[:2], hfail[:2]))

for r in rows:
    print(f"{r[0]} → {r[1]} · 단위 실패 {r[2]}건 {r[3]} · 헤드리스 {r[4]}")
shutil.rmtree(os.path.join(SCR, "mut-ui"), ignore_errors=True)
print("ALL RED" if not green else f"GREEN {green}")
sys.exit(1 if green else 0)
