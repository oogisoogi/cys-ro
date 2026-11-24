#!/usr/bin/env python3
"""(TICKET=cysr-1118u-chat ①) 대화 화면 한도 줄 캡처 — 실제 번들 + chat_gate 대역 + 계정 2개(이메일 라벨) 대역.
단언: 대화 화면 머리 .cv-limits 보임 · 줄 = 작업 화면 상황판 계정 줄과 같은 글 · 이메일 0 · 폭 1400/700/420 에서 덩이 안 잘림 0 · 콘솔 오류 0.
실행(수동 · CI 미배선): CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/chatlimit_gate.py ui/e2e [캡처폴더]
  (playwright 대신 patchright 로 돌릴 때는 evaluate 가 격리 세계에서 돌므로 아래 ev 가 주 세계를 고른다.)"""
import http.server, json, os, sys, threading
from datetime import datetime, timezone
from pathlib import Path
E2E = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(os.environ.get("TMPDIR", "/tmp")) / "cys-gate-evidence" / "chatlimit"; OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(E2E))
from tickrec_gate import BASE, CWD, SHIM, seat  # noqa
from chat_gate import CHAT_SHIM, DIST  # noqa
from playwright.sync_api import sync_playwright


def ev(pg, js):
    """주 세계에서 평가 — patchright 는 기본이 격리 세계라 isolated_context=False 를 준다 · playwright 는 그 인자가 없어 TypeError → 그냥."""
    try:
        return pg.evaluate(js, isolated_context=False)
    except TypeError:
        return pg.evaluate(js)

ACCTS = r"""
(() => {
  const orig = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    if (cmd === 'usage_accounts_all') {
      const now = Date.now() / 1000;
      const fri = Date.UTC(2026, 10, 20, 21, 0, 0) / 1000, thu = Date.UTC(2026, 10, 19, 8, 0, 0) / 1000;
      return Promise.resolve({ accounts: [
        { provider: 'claude', account_id: 'a1', label: 'one@example.com', profiles: ['/u/.claude'], current_profiles: ['/u/.claude'], updated_at: now - 5, source: 'oauth', rate: [{ label: '5h', used_pct: 12, resets_at: now + 600 }, { label: '7d', used_pct: 43, resets_at: fri }] },
        { provider: 'claude', account_id: 'a2', label: 'two@example.com', profiles: ['/u/.claude-acct2'], current_profiles: ['/u/.claude-acct2'], updated_at: now - 5, source: 'oauth', rate: [{ label: '5h', used_pct: 90, resets_at: now + 60 }, { label: '7d', used_pct: 81, resets_at: thu }] },
      ] });
    }
    return orig(cmd, args);
  };
})();
"""
fails = []
def check(c, m):
    print(("  ok   " if c else "  FAIL ") + m)
    if not c: fails.append(m)
h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
    ctx = br.new_context(viewport={"width": 1400, "height": 900})
    T0 = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)
    ctx.clock.install(time=T0); ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    pg.add_init_script(shim); pg.add_init_script(CHAT_SHIM); pg.add_init_script(ACCTS)
    pg.goto(url); pg.clock.run_for(9_000)
    ev(pg, f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}, {seat(BASE, 2, 'cso')}); }}")
    pg.clock.run_for(20_000)
    board = ev(pg, "() => [...document.querySelectorAll('.ws-board-acct-row')].map((r) => [r.querySelector('.ws-board-acct-name').textContent, r.querySelector('.ws-board-limit-text').textContent])")
    check(len(board) == 2, f"작업 화면 상황판 계정 줄 2 {board}")
    pg.screenshot(path=str(OUT / "work-1400.png"))
    pg.click("#view-switch button[data-view=chat]"); pg.clock.run_for(6_000)
    for w in (1400, 700, 420):
        pg.set_viewport_size({"width": w, "height": 900}); pg.clock.run_for(200)
        pg.wait_for_timeout(300)  # (TICKET=cysr-1119-s5 · V3) 한도 줄 자리 = matchMedia 사건(다음 그리기 = 실시간 · 가짜 시계 밖) → 실시간 300ms
        st = ev(pg, """() => { const L = document.querySelector('.cv-limits'); if (!L) return null;
          return { hidden: L.hidden, vis: L.getBoundingClientRect().width > 0, rows: [...L.querySelectorAll('.cv-limit')].map((r) => [r.querySelector('.cv-limit-name').textContent, r.querySelector('.cv-limit-text').textContent, r.className, r.title]),
            clip: [...L.querySelectorAll('.cv-limit, .cv-limit-name, .cv-limit-text')].filter((e) => e.scrollWidth > e.clientWidth + 1).length,
            over: [...L.querySelectorAll('.cv-limit')].filter((e) => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1).length,
            text: L.textContent } }""")
        check(st is not None and not st["hidden"] and st["vis"], f"[{w}] 대화 화면 머리 한도 줄 보임")
        if st:
            check([r[:2] for r in st["rows"]] == board, f"[{w}] 줄 = 상황판 계정 줄과 같은 글 {[r[:2] for r in st['rows']]}")
            check("@" not in st["text"] and all("@" not in r[3] for r in st["rows"]), f"[{w}] 이메일 0")
            check(st["clip"] == 0 and st["over"] == 0, f"[{w}] 잘림 0 · 화면 밖 0 (clip {st['clip']} · over {st['over']})")
            check(any("crit" in r[2] for r in st["rows"]), f"[{w}] 81% 줄 = crit 색")
        pg.screenshot(path=str(OUT / f"chat-{w}.png"))
    check(errs == [], f"콘솔 오류 0 {errs}")
    br.close()
print(json.dumps({"fails": fails}, ensure_ascii=False))
sys.exit(1 if fails else 0)
