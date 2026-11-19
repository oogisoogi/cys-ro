#!/usr/bin/env python3
"""1.1.14 기준 대조 게이트 — TICKET=cysr-tabs-sidebar-impl 남은 4번(워커 0·1 「새 단추 0 · 새 질문 0」 · 수동 실행 — CI 미배선).

같은 __TAURI__ 대역(statusboard_gate SHIM)으로 기준판(BASE_DIST = v1.1.14 270e3e21 의 ui/dist)과 이 가지(ui/dist)를 나란히 띄워
보이는 조작 요소(단추·입력·체크)와 떠 있는 질문 창(모달)을 센다. 장면 = 본부만 · 워커 0명 / 1명 · 1920.
단언: 상단 막대 보이는 단추 = 기준과 같거나 그 부분집합(1e 로 Control Center 단추가 기본 숨김) · 질문 창 0(두 판 모두) · 콘솔 오류 0.
덤프(판정 아님 · 보고 재료): 이 가지에만 보이는 조작 요소 목록 · 기준에만 보이는 것 목록 · 캡처 쌍.
실행: BASE_DIST=<1.1.14 ui/dist> CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/baseline_gate.py [캡처폴더]
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else sbg.UI.parent / "docs" / "evidence-tabs-sidebar" / "baseline"
BASE_DIST = Path(os.environ.get("BASE_DIST", ""))
SCEN = {"workers0": [sbg.W7[0]], "workers1": [sbg.W7[0], sbg.W7[2]]}

JS = r"""
() => {
  const vis = (e) => { const r = e.getBoundingClientRect(); if (!(r.width > 0 && r.height > 0)) return false; const cs = getComputedStyle(e); return cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0.05; };
  const label = (e) => (e.id ? '#' + e.id : (e.className && typeof e.className === 'string' ? '.' + e.className.split(' ')[0] : e.tagName)) + ' ' + (e.textContent || e.getAttribute('aria-label') || e.title || '').trim().slice(0, 24);
  const ctl = [...document.querySelectorAll('button, input, select, [role="button"]')].filter((e) => !e.closest('#root') && vis(e));
  return { topbar: [...document.querySelectorAll('#topbar button')].filter(vis).map(label),
    controls: ctl.map(label), modals: [...document.querySelectorAll('.modal-overlay, .palette-overlay, dialog[open]')].filter(vis).length };
}
"""


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    if not (BASE_DIST / "index.html").exists():
        print("BASE_DIST 없음 — v1.1.14 ui/dist 경로를 주어라")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    servers = {}
    for tag, d in (("base", BASE_DIST), ("new", sbg.DIST)):
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, _d=str(d), **kw: h(*a, directory=_d, **kw))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        servers[tag] = httpd
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            for name, seats in SCEN.items():
                js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in seats]
                got = {}
                for tag, httpd in servers.items():
                    ctx = br.new_context(viewport={"width": 1920, "height": 1200})
                    pg = ctx.new_page()
                    errs: list[str] = []
                    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                    pg.add_init_script(sbg.SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE))
                    pg.goto(f"http://127.0.0.1:{httpd.server_address[1]}/index.html")
                    pg.wait_for_timeout(11500)
                    got[tag] = pg.evaluate(JS)
                    got[tag]["errs"] = errs
                    pg.screenshot(path=str(OUT / f"{name}-{tag}-1920.png"))
                    ctx.close()
                b, n = got["base"], got["new"]
                print(f"== {name}")
                print(f"  상단 막대 기준 {b['topbar']}")
                print(f"  상단 막대 이 가지 {n['topbar']}")
                sbg.check(set(n["topbar"]) <= set(b["topbar"]), f"상단 막대 새 단추 0 (더해진 것 {sorted(set(n['topbar']) - set(b['topbar']))} · 빠진 것 {sorted(set(b['topbar']) - set(n['topbar']))})")
                sbg.check(b["modals"] == 0 and n["modals"] == 0, f"질문 창 0 (기준 {b['modals']} · 이 가지 {n['modals']})")
                sbg.check(not n["errs"], f"이 가지 콘솔 오류 0 {n['errs'][:2]}")
                print(f"  (덤프) 이 가지에만 보이는 조작 요소: {sorted(set(n['controls']) - set(b['controls']))}")
                print(f"  (덤프) 기준에만 보이는 조작 요소: {sorted(set(b['controls']) - set(n['controls']))}")
            br.close()
    finally:
        for s in servers.values():
            s.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
