#!/usr/bin/env python3
"""숨은 탭 막힘 표시 지연 실측 — TICKET=cysr-tabs-sidebar-impl 조각 2c-2 남은 것(수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(statusboard_gate SHIM · 좌석 배열만 window.__SEATS 로 열어 둔다). site 탭을 보는 동안 숨은 lms 묶음의 좌석이 막히면
좌석 줄(●→◆)·탭 머리 표지·상황판 ◆ 수에 닿기까지 걸린 시간을 잰다. 두 길:
  (가) 화면 승인 창 = 데몬 활동 관측 raw=permission(surface.list display_activity) — 앱 3초 목록 고리가 실어 온다
  (나) 승인 요청 = feed 대기 + approval.request 이벤트 — 이벤트가 사이드바 갱신을 바로 부른다
단언: 둘 다 좌석 줄·탭 머리·상황판에 닿는다 · 상한 = (가) 3초 고리 1바퀴 + 여유 = 4.5초 · (나) 1.5초. 3회씩 · 최소·최대 출력.
★이것은 앱 쪽 길(관측이 데몬에 들어온 뒤 → 화면)만 잰다 — 데몬이 승인 창을 알아채는 시간(활동 판독)은 포함하지 않는다.
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/hidden_block_gate.py
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)

# 고정 master·cso + site 3 + lms 2(숨은 묶음) — 처음엔 아무도 막히지 않았다
SEATS = [list(s) for s in sbg.W7[:5]] + [[sbg.BASE, 6, 934, "worker-4", "/u/axdev/lms", "working", "active", False, None, "6강 발행", 52],
                                        [sbg.BASE, 7, 935, "worker-5", "/u/axdev/lms", "working", "active", False, None, "묶음 머리", 63]]

WATCH = r"""
(sid) => new Promise((done) => {
  const t0 = performance.now(); const hit = {};
  const tick = () => {
    const t = Math.round(performance.now() - t0);
    if (hit.row === undefined && document.querySelector(`.ws-seat[data-sid="${sid}"]`)?.classList.contains('st-blocked')) hit.row = t;
    if (hit.tab === undefined && [...document.querySelectorAll('#root .group-tab')].some((g) => g.textContent.includes('lms') && g.querySelector('.act-input'))) hit.tab = t;
    if (hit.board === undefined && +(document.querySelector('[data-seat-host="board"] .ws-board-n.st-blocked .ws-board-num')?.textContent ?? 0) >= 1) hit.board = t;
    if ((hit.row !== undefined && hit.tab !== undefined && hit.board !== undefined) || t > 12000) return done(hit);
    setTimeout(tick, 25);
  };
  tick();
})
"""


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(sbg.DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in SEATS]
    shim = sbg.SHIM.replace("const SEATS = __SEATS__,", "const SEATS = window.__SEATS = __SEATS__,", 1)
    assert shim != sbg.SHIM, "SHIM 모양이 바뀌었다 — 좌석 배열을 열 수 없음"
    shim = shim.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE)
    res = {"가": [], "나": []}
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            for trial in range(3):
                for path in ("가", "나"):
                    ctx = br.new_context(viewport={"width": 1920, "height": 1200})
                    pg = ctx.new_page()
                    errs: list[str] = []
                    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                    pg.add_init_script(shim)
                    pg.goto(f"http://127.0.0.1:{httpd.server_address[1]}/index.html")
                    pg.wait_for_timeout(11500 + trial * 900)  # 3초 고리의 서로 다른 위상에서 시작
                    hidden = pg.evaluate("() => !document.querySelector('#root .pane[data-sid=\"6\"]') && !document.querySelector('#root .pane[data-sid=\"7\"]')")
                    sbg.check(hidden, f"[{path}#{trial}] lms 좌석 6·7 = 숨은 탭(site 탭을 보는 중)")
                    if path == "가":
                        pg.evaluate("() => { const s = window.__SEATS.find((x) => x.sid === 6); s.act = 'waiting_for_input'; s.raw = 'permission'; }")
                        hit = pg.evaluate(WATCH, 6)
                    else:
                        pg.evaluate("""() => { window.__SEATS.find((x) => x.sid === 7).approval = true;
                          window.__emit('daemon-event', { type: 'event', seq: 1, name: 'approval.request', category: 'approval', surface_id: 7, payload: { role: 'worker-5', surface_ref: 'surface:7', excerpt: 'run?' } }); }""")
                        hit = pg.evaluate(WATCH, 7)
                    res[path].append(hit)
                    print(f"  [{path}#{trial}] 좌석 줄 {hit.get('row')}ms · 탭 머리 {hit.get('tab')}ms · 상황판 {hit.get('board')}ms")
                    sbg.check(not errs, f"[{path}#{trial}] 콘솔 오류 0 {errs[:2]}")
                    ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    for path, cap in (("가", 4500), ("나", 1500)):
        for k in ("row", "tab", "board"):
            xs = [r.get(k) for r in res[path]]
            ok = all(x is not None and x <= cap for x in xs)
            sbg.check(ok, f"({path}) {k} 닿음 · 상한 {cap}ms · 실측 {xs} (최소 {min((x for x in xs if x is not None), default=None)} · 최대 {max((x for x in xs if x is not None), default=None)})")
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
