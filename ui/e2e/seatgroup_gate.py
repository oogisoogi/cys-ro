#!/usr/bin/env python3
"""말로 옮기기 · 말로 열기 게이트 — TICKET=cysr-tabs-sidebar-impl 조각 2d(수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(statusboard_gate 의 SHIM 재사용 · window.__emit 으로 데몬 이벤트를 흉내).
단언: `surface.group.changed`(931 → video) = 좌석 줄에서 931 이 video 묶음으로 · 앱 기록(cys-seat-group)에 역할 열쇠로 영속 ·
      새로 고침(데몬 목록의 group = null = 데몬이 다시 켜진 셈) 뒤에도 video 그대로 · 해제(group = null) = site 로 복귀 ·
      `ui.open_panel`(control-center) = 숨은 단추와 무관하게 컨트롤 센터 열림 · 다른 패널 이름 = 무동작 · 콘솔 오류 0.
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/seatgroup_gate.py [캡처폴더]
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else sbg.evidence_dir("evidence-tabs-sidebar", "2d")

GROUPS = """() => { const host = document.querySelector('.ws-seats[data-seat-host]:not([data-seat-host="board"]):not([data-seat-host^="n"])'); const out = {}; let cur = null;
  for (const el of host ? host.children : []) { if (el.classList.contains('ws-seat-group')) { cur = el.querySelector('.ws-seat-group-name')?.textContent; out[cur] = []; }
    else if (cur && el.classList.contains('ws-seat') && !el.classList.contains('named')) out[cur].push(el.querySelector('.ws-seat-no')?.textContent); } return out; }"""


def ev(name: str, sid, payload: dict, seq: int) -> str:
    return "() => window.__emit('daemon-event', " + json.dumps({"type": "event", "seq": seq, "name": name, "category": "surface", "surface_id": sid, "payload": payload}) + ")"


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(sbg.DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in sbg.W7]
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1920, "height": 1200})
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
            pg.add_init_script(sbg.SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE))
            pg.goto(f"http://127.0.0.1:{port}/index.html")
            pg.wait_for_timeout(11500)
            g0 = pg.evaluate(GROUPS)
            sbg.check(g0.get("site") == ["931", "932", "933"] and g0.get("video") == ["936", "937"], f"처음 = 폴더 묶음 {g0}")
            n = pg.evaluate(ev("surface.group.changed", 3, {"surface_id": 3, "group": "video", "previous": None}, 1))
            pg.wait_for_timeout(400)
            g1 = pg.evaluate(GROUPS)
            sbg.check(n >= 1 and "931" in g1.get("video", []) and "931" not in g1.get("site", []), f"옮김 이벤트 = 931 → video {g1}")
            saved = pg.evaluate("() => JSON.parse(localStorage.getItem('cys-seat-group') || '{}')")
            sbg.check(saved == {"#role:worker": "video"}, f"앱 기록 = 역할 열쇠로 영속 {saved}")
            pg.screenshot(path=str(OUT / "moved-1920.png"))
            pg.reload()
            pg.wait_for_timeout(11500)
            g2 = pg.evaluate(GROUPS)
            sbg.check("931" in g2.get("video", []), f"새로 고침(데몬 목록 group = null) 뒤에도 video {g2}")
            pg.evaluate(ev("surface.group.changed", 3, {"surface_id": 3, "group": None, "previous": "video"}, 2))
            pg.wait_for_timeout(400)
            g3 = pg.evaluate(GROUPS)
            saved = pg.evaluate("() => JSON.parse(localStorage.getItem('cys-seat-group') || '{}')")
            sbg.check("931" in g3.get("site", []) and saved == {}, f"해제 = 폴더 묶음(site)으로 · 기록 지움 {g3} {saved}")
            closed = pg.evaluate("() => document.getElementById('cc-panel').hidden")
            pg.evaluate("() => window.__emit('daemon-event', { type: 'event', seq: 3, name: 'ui.open_panel', category: 'ui', payload: { panel: 'feed' } })")
            pg.wait_for_timeout(300)
            still = pg.evaluate("() => document.getElementById('cc-panel').hidden")
            pg.evaluate("() => window.__emit('daemon-event', { type: 'event', seq: 4, name: 'ui.open_panel', category: 'ui', payload: { panel: 'control-center' } })")
            pg.wait_for_timeout(400)
            opened = pg.evaluate("() => !document.getElementById('cc-panel').hidden")
            btn_hidden = pg.evaluate("() => document.getElementById('btn-cc').hidden")
            sbg.check(closed and still, "다른 패널 이름 = 무동작(컨트롤 센터 닫힌 그대로)")
            sbg.check(opened and btn_hidden, f"말로 열기 = 단추가 숨어 있어도 컨트롤 센터 열림 (opened={opened} · 단추 숨김={btn_hidden})")
            pg.screenshot(path=str(OUT / "open-cc-1920.png"))
            sbg.check(not errs, f"콘솔 오류 0 {errs[:3]}")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
