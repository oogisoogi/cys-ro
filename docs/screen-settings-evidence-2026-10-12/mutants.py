import subprocess, os, sys, tempfile, re
UI = sys.argv[1]
env = {k: v for k, v in os.environ.items() if not k.startswith("CYS_") and k != "CLAUDE_CONFIG_DIR"}
env["HOME"] = tempfile.mkdtemp()
env["PATH"] = f"/Users/{os.environ['USER']}/.bun/bin:/usr/bin:/bin:/usr/sbin:/sbin"
def run():
    r = subprocess.run(["bun", "test", "src/topbarlayout.test.ts", "src/screensettings.test.ts"], cwd=UI, env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    p = re.search(r"(\d+) pass", out); f = re.search(r"(\d+) fail", out)
    return (int(p.group(1)) if p else -1, int(f.group(1)) if f else -1, r.returncode)
M = [
 ("M1 기본 끔에서 창 닫기 뺌", "src/topbarlayout.ts", '["btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-factory-reset"]', '["btn-new", "btn-split-h", "btn-split-v", "btn-factory-reset"]'),
 ("M2 새 단추를 끈 채 붙임", "src/topbarlayout.ts", "if (!seen.has(id)) out.push({ id, on: true });", "if (!seen.has(id)) out.push({ id, on: false });"),
 ("M3 고정 단추 토글 허용", "src/topbarlayout.ts", "it.id === id ? { id, on: on || isTopbarPinned(id) } : { ...it }", "it.id === id ? { id, on } : { ...it }"),
 ("M4 고정 단추 끔 저장을 그대로 읽음", "src/topbarlayout.ts", "out.push({ id, on: on || isTopbarPinned(id) });", "out.push({ id, on });"),
 ("M5 구판(version) 검사 뺌", "src/topbarlayout.ts", "if (o.version !== TOPBAR_LAYOUT_VERSION || !Array.isArray(o.items))", "if (!Array.isArray(o.items))"),
 ("M6 맨 아래 ▼ 경계 뺌", "src/topbarlayout.ts", "if (i < 0 || j < 0 || j >= arr.length) return arr;", "if (i < 0 || j < 0) return arr;"),
 ("M7 끌어 놓기 앞/뒤 뒤집힘", "src/topbarlayout.ts", "arr.splice(before ? ai : ai + 1, 0, src);", "arr.splice(before ? ai + 1 : ai, 0, src);"),
 ("M8 팝오버 글자 12px 로 되돌림", "src/style.css", "font-size: calc(20px * var(--ui-chrome-scale)); line-height: 1.35;", "font-size: 12px; line-height: 1.35;"),
 ("M9 선택 상자만 12px 고정", "src/style.css", "  max-width: 11em; padding: .1em .2em; cursor: pointer;", "  max-width: 11em; padding: .1em .2em; cursor: pointer; font-size: 12px;"),
 ("M10 입력 칸 인라인 56px 되살림", "src/main.ts", 'tsInp.max = "40";', 'tsInp.max = "40"; tsInp.style.width = "56px";'),
 ("M11 숨김 대신 요소 제거", "src/main.ts", "    b.hidden = !it.on;\n    topbarEl.appendChild(b);", "    if (!it.on) { b.remove(); continue; }\n    topbarEl.appendChild(b);"),
 ("M12 시작 복원 줄 뺌", "src/main.ts", "\napplyTopbarLayout(topbarLayout, false);\n", "\n"),
 ("M13 단추 이름 테마로 되돌림", "index.html", '<button id="btn-theme" title="화면 설정 — 글자·배경·상단 단추">화면 설정</button>', '<button id="btn-theme" title="배경 테마 — 배경색 커스텀 지정">테마</button>'),
 ("M14 팝오버 스크롤(overflow) 뺌", "src/style.css", "max-height: calc(100vh - var(--topbar-h) - 8px); overflow: auto;", "max-height: calc(100vh - var(--topbar-h) - 8px);"),
 ("M15 꺼진 상단 단추 짝 규칙 뺌", "src/style.css", "#topbar > button[hidden] { display: none; }", ""),
 ("M16 html 에 + New 를 hidden 으로 박음", "index.html", '<button id="btn-new" title="새 surface (⌘T)">+ New</button>', '<button id="btn-new" hidden title="새 surface (⌘T)">+ New</button>'),
]
base = run(); print("기준", base)
bad = 0
for name, rel, a, b in M:
    p = os.path.join(UI, rel); src = open(p, encoding="utf-8").read()
    if src.count(a) != 1: print("SKIP(자리 못 찾음)", name, src.count(a)); bad += 1; continue
    try:
        open(p, "w", encoding="utf-8").write(src.replace(a, b))
        r = run()
    finally:
        open(p, "w", encoding="utf-8").write(src)
    caught = r[1] > 0
    if not caught: bad += 1
    print(("잡음 " if caught else "놓침 ") + name, r)
print("복원 뒤", run(), "놓침·건너뜀", bad)
