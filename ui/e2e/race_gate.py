#!/usr/bin/env python3
"""새 좌석 생성 중 전환 경합 게이트 — TICKET=cysr-tabs-sidebar-impl · ChatGPT 대체 1R #2·#3(master#4e00a677 · 수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(statusboard_gate SHIM) · create_surface 응답을 1.5초 늦추고 그 사이에:
  R1(#2) 본부 작업공간에서 ⌘T → 부서 작업공간(lms)으로 전환 → 새 좌석(본부 데몬 것)은 본부 트리에만 · 부서 트리에 0 · 화면 포커스는 지금 작업공간 좌석
  R2(#3) site 탭 좌석 4 에서 ⌘D → 탭 lms 로 전환 → 새 좌석은 시작한 탭(site) 묶음 · 지금 보이는 lms 화면에 없음 · 포커스 = 보이는 좌석(숨은 좌석 아님)
  R3(#3) site 탭 좌석 4 에서 ⌘D → 그 사이 좌석 4 닫힘(surface.closed) → 새 좌석이 화면에 보이고 포커스도 그 좌석 · 오류 0
실행: CHROME_PATH=<chrome-headless-shell> [GATE_DIST=<다른 번들>] cys run -- <playwright python3> ui/e2e/race_gate.py
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else sbg.DIST

SPY = r"""
(() => {
  window.__calls = [];
  const orig = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    if (['send_input', 'close_surface', 'create_surface'].includes(cmd)) window.__calls.push([cmd, args?.surfaceId ?? null, args?.socket ?? null]);
    if (cmd === 'create_surface') return new Promise((res) => setTimeout(() => {
      window.__SEATS.push({ sock: args?.socket ?? '__BASE__', sid: 50, no: 950, role: null, cwd: '/Users/sim', act: 'waiting', raw: 'idle', approval: false, self: null, task: null, ctx: null });
      res({ surface_id: 50, display_no: 950 });
    }, 1500));
    if (cmd === 'close_surface') return Promise.resolve({ ok: true });
    return orig(cmd, args);
  };
})();
"""

STATE = r"""
() => { const lay = JSON.parse(localStorage.getItem('cys-layout-v2') || '{}'); const sids = (n) => !n ? [] : n.type === 'pane' ? [n.sid] : [...sids(n.a), ...sids(n.b)];
  return { panes: [...document.querySelectorAll('#root .pane')].map((p) => +p.dataset.sid).sort((a, b) => a - b),
    focused: [...document.querySelectorAll('.pane.focused')].filter((p) => p.isConnected).map((p) => +p.dataset.sid),
    active: (() => { const a = document.activeElement; const p = a?.closest?.('.pane'); return p ? +p.dataset.sid : (a?.tagName ?? null); })(),
    tab: document.querySelector('#root .group-tab.active .group-tab-name')?.textContent ?? null,
    trees: (lay.workspaces || []).map((w) => ({ socket: w.socket ?? null, sids: sids(w.tree) })) }; }
"""


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    js = lambda rows: [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=False, self=s[8], task=s[9], ctx=s[10]) for s in rows]  # noqa: E731
    print("번들:", DIST)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

            def page(seats, depts):
                ctx = br.new_context(viewport={"width": 1920, "height": 1200})
                pg = ctx.new_page()
                errs: list[str] = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                pg.add_init_script(sbg.SHIM.replace("__SEATS__", "window.__SEATS = " + json.dumps(seats)).replace("__DEPTS__", json.dumps(depts)).replace("__BASE__", sbg.BASE))
                pg.add_init_script(SPY.replace("__BASE__", sbg.BASE))
                pg.goto(url)
                pg.wait_for_timeout(11500)
                return ctx, pg, errs

            # R1
            print("== R1(#2) ⌘T 생성 중 작업공간 전환")
            seats, depts = sbg.SCEN["dept3"]
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            s0 = pg.evaluate(STATE)
            base_i = next(i for i, t in enumerate(s0["trees"]) if t["socket"] in (None, sbg.BASE))
            pg.click('#root .pane[data-sid="1"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.keyboard.press("Meta+t")
            pg.wait_for_timeout(300)
            tabs = pg.query_selector_all("#ws-tabs .ws-tab")
            other = next((i for i in range(len(tabs)) if i != base_i), None)
            sbg.check(other is not None, f"작업공간 {len(tabs)}개(전환할 곳 있음)")
            if other is not None:
                tabs[other].click()
            pg.wait_for_timeout(2500)
            s1 = pg.evaluate(STATE)
            in_base = 50 in s1["trees"][base_i]["sids"]
            in_other = [t["socket"] for i, t in enumerate(s1["trees"]) if i != base_i and 50 in t["sids"]]
            sbg.check(in_base and not in_other, f"새 좌석 50 = 본부 트리에만(부서 트리 {in_other}) · 트리 {s1['trees']}")
            sbg.check(50 not in s1["panes"], f"지금 화면(부서) 에 본부 좌석 50 없음 {s1['panes']}")
            sbg.check(not s1["focused"] or s1["focused"][0] in s1["panes"], f"포커스 = 지금 화면 좌석 {s1['focused']}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            seats7 = js(sbg.W7)
            # R2
            print("== R2(#3) ⌘D 생성 중 탭 전환")
            ctx, pg, errs = page(seats7, [])
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.keyboard.press("Meta+d")
            pg.wait_for_timeout(300)
            pg.click('#root .group-tab:has-text("lms")')
            pg.wait_for_timeout(2500)
            s2 = pg.evaluate(STATE)
            sbg.check(s2["tab"] == "lms" and 50 not in s2["panes"], f"지금 lms 화면 = 새 좌석 없음(시작한 site 탭 묶음) {s2['panes']} · 탭 {s2['tab']}")
            sbg.check(len(s2["focused"]) == 1 and s2["focused"][0] in s2["panes"] and s2["active"] in s2["panes"], f"포커스 = 보이는 좌석(숨은 새 좌석 아님) {s2['focused']} · {s2['active']}")
            pg.click('#root .group-tab:has-text("site")')
            pg.wait_for_timeout(600)
            s2b = pg.evaluate(STATE)
            sbg.check(50 in s2b["panes"], f"site 탭으로 돌아가면 새 좌석 50 보임 {s2b['panes']}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R3
            print("== R3(#3) ⌘D 생성 중 대상 좌석 닫힘")
            ctx, pg, errs = page(seats7, [])
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.keyboard.press("Meta+d")
            pg.wait_for_timeout(300)
            pg.evaluate("""() => { const a = window.__SEATS; a.splice(a.findIndex((s) => s.sid === 4), 1);
              window.__emit('daemon-event', { type: 'event', seq: 5, name: 'surface.closed', category: 'surface', surface_id: 4, socket_slug: 'base', payload: { surface_id: 4 } }); }""")
            pg.wait_for_timeout(2500)
            s3 = pg.evaluate(STATE)
            sbg.check(4 not in s3["panes"] and 50 in s3["panes"], f"대상 닫힘 뒤 새 좌석 50 보임 {s3['panes']}")
            sbg.check(s3["focused"] == [50], f"포커스 = 새 좌석 {s3['focused']}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    for f in sbg.failures:
        print("  FAIL:", f)
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
