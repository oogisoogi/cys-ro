#!/usr/bin/env python3
"""Control Center 단추 내리기 게이트 — TICKET=cysr-tabs-sidebar-impl 조각 1e(master#b1b8d7df · 수동 실행).
캡처: 단추 숨김(기본) · 단추 켬(저장 배치에서 사람이 켬) · 승인 대기 2(좌석 승인 1 + 좌석 없는 승인 1)인 상황판.
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/cc_button_gate.py
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
OUT = sbg.UI.parent / "docs" / "evidence-tabs-sidebar" / "1e"
ON_LAYOUT = json.dumps({"version": 1, "items": [{"id": i, "on": i not in ("btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-factory-reset")} for i in
  ["btn-feedback", "btn-counsel", "btn-agora", "btn-equalize", "btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-files", "btn-cc", "btn-restart-daemon", "btn-factory-reset", "btn-theme"]]})


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(sbg.DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    seats = [s for s in sbg.W7 if s[2] != 935]  # 935(화면 입력 대기)를 빼 막힌 좌석 = 934(승인 피드) 하나
    js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in seats]
    shim = sbg.SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            for case, init in (
                ("default-hidden", ""),
                ("saved-layout-migrated", f"localStorage.setItem('cys-topbar-layout', {json.dumps(ON_LAYOUT)});"),
                ("user-turned-on", f"localStorage.setItem('cys-topbar-layout', {json.dumps(ON_LAYOUT)}); localStorage.setItem('cys-cc-btn-off-115', '1');"),
            ):
                print(f"== {case}")
                ctx = br.new_context(viewport={"width": 1920, "height": 1200})
                pg = ctx.new_page()
                errs: list[str] = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                pg.add_init_script("window.__EXTRA_PENDING = 1;" + init)
                pg.add_init_script(shim)
                pg.goto(f"http://127.0.0.1:{port}/index.html")
                pg.wait_for_timeout(11500)
                hidden = pg.evaluate("() => document.getElementById('btn-cc').hidden")
                chip = pg.evaluate("() => document.querySelector('.ws-board-approvals')?.textContent ?? null")
                pg.screenshot(path=str(OUT / f"{case}-1920.png"))
                sbg.check(hidden == (case != "user-turned-on"), f"Control Center 단추 숨김 = {hidden}")
                sbg.check(chip == "승인 대기 2", f"상황판 승인 대기 수 {chip}")
                if case == "default-hidden":
                    pg.click(".ws-board-approvals")
                    pg.wait_for_timeout(400)
                    vis = pg.evaluate("() => [...document.querySelectorAll('#root .pane')].map((p) => +p.dataset.sid)")
                    sbg.check(6 in vis, f"승인 대기 누름 = 승인 창 좌석(934)으로 {vis}")
                    # 감사 §2-1 #4(master#cc01161f ①): 단추가 숨어 있어도 approval.stalled 자동 열림(openFeed)은 그대로다
                    n = pg.evaluate("() => window.__emit('daemon-event', { type: 'event', seq: 1, name: 'approval.stalled', category: 'feed', surface_id: 6, payload: { surface_ref: 'surface:6', age_secs: 300 } })")
                    pg.wait_for_timeout(500)
                    auto = pg.evaluate("() => !document.getElementById('cc-panel').hidden")
                    sbg.check(n >= 1 and auto, f"단추 숨김 상태에서 approval.stalled = 컨트롤 센터 자동 열림(승인 Feed) (listeners={n})")
                    pg.screenshot(path=str(OUT / "auto-open-stalled-1920.png"))
                    pg.evaluate("() => document.getElementById('btn-cc').click()")  # 닫기(숨은 단추의 click = setCcOpen(!ccOpen))
                    pg.wait_for_timeout(300)
                    pg.click("#btn-theme")
                    pg.wait_for_timeout(300)
                    pg.click("text=컨트롤 센터 열기")
                    pg.wait_for_timeout(500)
                    opened = pg.evaluate("() => !document.getElementById('cc-panel').hidden")
                    sbg.check(opened, "화면 설정 「컨트롤 센터 열기」 = 열림")
                    pg.screenshot(path=str(OUT / "open-from-settings-1920.png"))
                sbg.check(not errs, f"콘솔 오류 0 {errs[:3]}")
                ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
