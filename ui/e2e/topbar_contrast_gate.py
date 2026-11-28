#!/usr/bin/env python3
"""(TICKET=cysr-1121-integ · master#3bbe6350 · 686 printshot 발견) 상단 바 「대화 화면 / 작업 화면」 전환 단추 글자 대비 게이트 — 실제 번들 + e2e 대역.
장면: B0 기본 배경 · B1 흰 배경(cys-bg-color=#ffffff · 제보 꼴) · B2 검은 배경(#000000) · B3 밝은 회색(#f0f0f0).
각 장면 = 두 단추 글자색 ↔ 그 단추가 실제로 놓인 배경(눌린 단추 = 자기 배경 · 안 눌린 단추 = 투명 → 상단 바 배경) WCAG 대비 ≥ 4.5 · 옆 상단 단추와 비교.
실행: [GATE_DIST=<번들>] cys run -- <playwright python3> ui/e2e/topbar_contrast_gate.py ui/e2e <캡처 폴더>
"""
import http.server, os, sys, threading, re
from datetime import datetime, timezone
from pathlib import Path

E2E = Path(sys.argv[1])
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(E2E))
from tickrec_gate import BASE, CWD, SHIM, seat  # noqa
from chat_gate import CHAT_SHIM, DIST  # noqa
from playwright.sync_api import sync_playwright

fails = []
def check(c, m):
    print(("  ok   " if c else "  FAIL ") + m, flush=True)
    if not c: fails.append(m)

def rgb(s):
    v = [float(x) for x in re.findall(r"[\d.]+", s)]
    return v[:3], (v[3] if len(v) > 3 else 1.0)
def lum(c):
    def ch(x):
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = c
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)
def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

JS = """() => { const bar = document.querySelector('#topbar'); const bs = [...document.querySelectorAll('#view-switch .vs-group button')];
  const nb = [...document.querySelectorAll('#topbar > button, #topbar button')].find((b) => !b.closest('#view-switch') && b.getClientRects().length > 0);
  return { bar: getComputedStyle(bar).backgroundColor, body: getComputedStyle(document.body).color,
    btns: bs.map((b) => ({ t: b.textContent, pressed: b.getAttribute('aria-pressed'), color: getComputedStyle(b).color, bg: getComputedStyle(b).backgroundColor, op: getComputedStyle(b).opacity })),
    neighbor: nb ? { t: nb.textContent.slice(0, 12), color: getComputedStyle(nb).color, bg: getComputedStyle(nb).backgroundColor } : null }; }"""

h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
print(f"DIST = {DIST}", flush=True)
with sync_playwright() as p:
    exe = os.environ.get("CHROME_PATH")
    br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
    for name, color in (("B0-기본", None), ("B1-흰", "#ffffff"), ("B2-검정", "#000000"), ("B3-밝은회색", "#f0f0f0")):
        ctx = br.new_context(viewport={"width": 1400, "height": 900}, timezone_id="Asia/Seoul", locale="ko-KR")
        ctx.clock.install(time=datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc))
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        pg.add_init_script(shim); pg.add_init_script(CHAT_SHIM)
        if color:
            pg.add_init_script("localStorage.setItem('cys-bg-color', %r);" % color)
        pg.goto(url); pg.clock.run_for(9_000)
        pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}); }}")
        pg.clock.run_for(8_000)
        d = pg.evaluate(JS)
        bar, _ = rgb(d["bar"])
        print(f"[{name}] bar={d['bar']} body={d['body']} neighbor={d['neighbor']}", flush=True)
        check(len(d["btns"]) == 2, f"{name} 전환 단추 2개 ({[b['t'] for b in d['btns']]})")
        for b in d["btns"]:
            fg, _ = rgb(b["color"]); bgc, ba = rgb(b["bg"])
            under = bgc if ba > 0.5 else bar
            cr = contrast(fg, under)
            check(cr >= 4.5, f"{name} 「{b['t']}」(눌림={b['pressed']}) 글자 {b['color']} ↔ 배경 {('자기 ' + b['bg']) if ba > 0.5 else ('상단 바 ' + d['bar'])} 대비 {cr:.2f} ≥ 4.5")
        check(not errs, f"{name} 페이지 오류 0 {errs}")
        pg.screenshot(path=str(OUT / f"{name}.png"), clip={"x": 0, "y": 0, "width": 1400, "height": 60})
        ctx.close()
    br.close()
httpd.shutdown()
print("PASS — 실패 0" if not fails else f"FAIL {len(fails)}건", flush=True)
sys.exit(1 if fails else 0)
