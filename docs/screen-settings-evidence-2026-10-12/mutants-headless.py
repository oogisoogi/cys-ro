# 실렌더 시험(screen-settings-headless.ts)의 음성 대조 — 실파일에 결함을 심고(try/finally 복원) 작업 트리 밖에 번들을 만들어 그 칸이 FAIL 하는지 본다.
# usage: python3 mutants-headless.py <repo> <chrome-headless-shell> <임시 번들 폴더>
import subprocess, os, sys, tempfile, shutil
REPO, CHS, DIST = sys.argv[1], sys.argv[2], sys.argv[3]
UI = os.path.join(REPO, "ui")
env = {k: v for k, v in os.environ.items() if not k.startswith("CYS_") and k != "CLAUDE_CONFIG_DIR"}
env["HOME"] = tempfile.mkdtemp()
env["PATH"] = f"/Users/{os.environ['USER']}/.bun/bin:/usr/bin:/bin:/usr/sbin:/sbin"
def build():
    os.makedirs(DIST, exist_ok=True)
    subprocess.run(["bun", "build", "src/main.ts", "--outdir", DIST, "--target", "browser", "--minify"], cwd=UI, env=env, check=True, capture_output=True)
    for f in ("index.html", "src/style.css", "node_modules/@xterm/xterm/css/xterm.css"):
        shutil.copy(os.path.join(UI, f), DIST)
def run(only):
    e = dict(env, DIST=DIST, CHS=CHS, ONLY=only)
    r = subprocess.run(["bun", os.path.join(REPO, "docs/screen-settings-evidence-2026-10-12/screen-settings-headless.ts")], env=e, capture_output=True, text=True)
    lines = [l[:110] for l in r.stdout.splitlines() if l.startswith(("PASS", "FAIL", "ALL"))]
    return r.returncode, lines
M = [
 ("H1 선택 상자만 12px 고정(한 부품이 작게 남음)", "src/style.css", "  max-width: 11em; padding: .1em .2em; cursor: pointer;", "  max-width: 11em; padding: .1em .2em; cursor: pointer; font-size: 12px;", "s2"),
 ("H2 팝오버 스크롤(overflow) 뺌", "src/style.css", "max-height: calc(100vh - var(--topbar-h) - 8px); overflow: auto;", "max-height: calc(100vh - var(--topbar-h) - 8px);", "s3"),
 ("H3 기본 끔에서 창 닫기 뺌", "src/topbarlayout.ts", '["btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-factory-reset"]', '["btn-new", "btn-split-h", "btn-split-v", "btn-factory-reset"]', "s1"),
 ("H4 꺼진 단추에 display 를 주는 규칙(숨김이 풀림) + 짝 규칙 뺌", "src/style.css", "#topbar > button[hidden] { display: none; }", "#topbar button { display: inline-block; }", "s1"),
 ("H5 토글이 저장만 하고 화면에 안 바름", "src/main.ts", "    b.hidden = !it.on;\n    topbarEl.appendChild(b);", "    if (persist === false) b.hidden = !it.on;\n    topbarEl.appendChild(b);", "s4"),
 ("H6 고정 단추 토글 비활성 뺌", "src/main.ts", "      tog.disabled = pinned;", "      tog.disabled = false;", "s5"),
]
bad = 0
for name, rel, a, b, only in M:
    p = os.path.join(UI, rel); src = open(p, encoding="utf-8").read()
    if src.count(a) != 1: print("SKIP(자리 못 찾음)", name, src.count(a)); bad += 1; continue
    try:
        open(p, "w", encoding="utf-8").write(src.replace(a, b))
        build(); rc, lines = run(only)
    finally:
        open(p, "w", encoding="utf-8").write(src)
    caught = rc == 1 and any(l.startswith("FAIL " + only) for l in lines)
    if not caught: bad += 1
    print(("잡음 " if caught else "놓침 ") + name, "rc", rc, "|", " / ".join(l for l in lines if l.startswith("FAIL"))[:260])
build(); rc, lines = run("s1,s2,s3,s4,s5")
print("복원 뒤 rc", rc, lines[-1], "· 놓침·건너뜀", bad)
