#!/usr/bin/env python3
"""워크스페이스 사이드바 폭 드래그·글자 배율 회귀 게이트 (수동 실행 — CI 미배선).

검증 항목 (2026-07-12 오너 요청):
  1. #wsbar 폭이 --wsbar-w 변수로 구동(기본 216px)·#wsbar-drag 핸들 존재.
  2. 핸들 드래그로 폭이 변하고 localStorage(cys-wsbar-w) 영속·리로드 복원.
  3. 더블클릭=기본폭 복귀.
  4. A−/A＋ 버튼으로 --wsbar-font 배율 증감·영속·클램프(0.8~2.2).
     (1.1.20 #26) 단추 자리 = 화면 설정 「글자·배경」 「왼쪽 목록 글자 크기」(1.1.20 F2 · 사이드바 머리
     #btn-ws-font-plus/minus 는 1.1.19 cysr-1119-s10b MD-S1S2 에서 빠졌다) — 지금 % 표시도 함께 잰다.
  5. 콘솔 에러 0.
  6. 최소폭 176·배율 2.2·낮은 창에서도 #wsbar 가로 넘침 0.
     (1.1.20 #26) 옛 6번의 바닥 꼬리 #wsbar-foot·전문가용 토글(#btn-expert-toggle·#wsbar-expert-body)·
     사용량 요약 줄(#wsbar-usage)은 화면에서 빠졌다 — 그 단언은 지웠다(전문가 입구 = 화면 설정 「전문가」).
(pane 재적합은 기존 pane별 ResizeObserver→fitPane 경로 + 드래그 종료 refitAllPanes —
 PTY 없는 브라우저 하네스에선 코드 경로가 unittest·리뷰로 커버되므로 여기선 폭·배율만 단언.)

사전: sh ui/build.sh · pip install playwright · playwright install chromium
실행: python3 ui/e2e/wsbar_gate.py   # exit 0 = PASS
"""
import http.server
import socket
import sys
import threading
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "dist"
SHIM = """
window.__TAURI__ = {
  core: { invoke: (c,a) => new Promise(()=>{}) },
  event: { listen: (n,h) => Promise.resolve(()=>{}) },
};
"""
failures: list[str] = []

def check(cond: bool, msg: str) -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)

def main() -> int:
    if not (DIST / "index.html").exists():
        print("FAIL: ui/dist 없음 — 먼저 `sh ui/build.sh`")
        return 2
    from playwright.sync_api import sync_playwright
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(DIST), **kw)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1400, "height": 900})
            pg.add_init_script(SHIM)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
            url = f"http://127.0.0.1:{port}/index.html"
            pg.goto(url); pg.wait_for_timeout(500)

            w0 = pg.evaluate("document.getElementById('wsbar').getBoundingClientRect().width")
            check(abs(w0 - 216) < 2, f"기본폭 216px (got {w0})")
            check(pg.evaluate("!!document.getElementById('wsbar-drag')"), "드래그 핸들 존재")

            # 최소폭 경계: 크게 왼쪽으로 드래그 → 하한(176) 클램프 + 헤더 1줄 유지(≤40px — 140px 시절 2단 랩 회귀 방지)
            hb0 = pg.evaluate("(() => { const r = document.getElementById('wsbar-drag').getBoundingClientRect(); return {x: r.x + r.width/2, y: r.y + 200}; })()")
            pg.mouse.move(hb0["x"], hb0["y"]); pg.mouse.down()
            pg.mouse.move(hb0["x"] - 300, hb0["y"], steps=6); pg.mouse.up()
            pg.wait_for_timeout(200)
            wmin = pg.evaluate("document.getElementById('wsbar').getBoundingClientRect().width")
            hh = pg.evaluate("document.getElementById('wsbar-head').getBoundingClientRect().height")
            check(abs(wmin - 176) < 2, f"최소폭 클램프 176px (got {wmin})")
            check(hh <= 40, f"최소폭에서 헤더 1줄 유지 ≤40px (got {hh})")
            pg.dblclick("#wsbar-drag"); pg.wait_for_timeout(150)  # 기본폭 복귀 후 본 시나리오 진행

            # 드래그: 216 → +140
            hb = pg.evaluate("(() => { const r = document.getElementById('wsbar-drag').getBoundingClientRect(); return {x: r.x + r.width/2, y: r.y + 200}; })()")
            pg.mouse.move(hb["x"], hb["y"]); pg.mouse.down()
            pg.mouse.move(hb["x"] + 140, hb["y"], steps=8); pg.mouse.up()
            pg.wait_for_timeout(200)
            w1 = pg.evaluate("document.getElementById('wsbar').getBoundingClientRect().width")
            check(abs(w1 - (w0 + 140)) < 4, f"드래그 후 폭 {w0}+140≈{w1}")
            saved = pg.evaluate("localStorage.getItem('cys-wsbar-w')")
            check(saved and abs(int(saved) - w1) < 4, f"폭 영속 (localStorage={saved})")

            # 리로드 복원
            pg.reload(); pg.wait_for_timeout(400)
            w2 = pg.evaluate("document.getElementById('wsbar').getBoundingClientRect().width")
            check(abs(w2 - w1) < 4, f"리로드 후 폭 복원 ({w2})")

            # 더블클릭 = 기본폭
            pg.dblclick("#wsbar-drag")
            pg.wait_for_timeout(150)
            w3 = pg.evaluate("document.getElementById('wsbar').getBoundingClientRect().width")
            check(abs(w3 - 216) < 2, f"더블클릭 기본폭 복귀 ({w3})")

            # 글자 배율: A＋ ×3 → 1.3, 클램프 상한 2.2 — (1.1.20 #26) 입구 = 화면 설정 「왼쪽 목록 글자 크기」
            pg.click("#btn-theme"); pg.wait_for_timeout(200)
            plus = pg.get_by_role("button", name="왼쪽 목록 글자 확대")
            minus = pg.get_by_role("button", name="왼쪽 목록 글자 축소")
            pct = lambda: pg.evaluate("document.querySelector('.sp-wsfont-pct')?.textContent")
            check(pct() == "100%", f"화면 설정 % 표시 100% (got {pct()!r})")
            for _ in range(3):
                plus.click()
            f1 = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--wsbar-font').trim()")
            check(f1 == "1.3", f"A＋×3 → --wsbar-font=1.3 (got {f1})")
            check(pg.evaluate("localStorage.getItem('cys-wsbar-font')") == "1.3", "배율 영속")
            check(pct() == "130%", f"화면 설정 % 표시 130% (got {pct()!r})")
            for _ in range(20):
                plus.click()
            f2 = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--wsbar-font').trim()")
            check(f2 == "2.2", f"상한 클램프 2.2 (got {f2})")
            for _ in range(30):
                minus.click()
            f3 = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--wsbar-font').trim()")
            check(f3 == "0.8", f"하한 클램프 0.8 (got {f3})")

            # 6. 최소폭·최대 배율·낮은 창의 극단에서 가로 넘침 0
            pg.evaluate("localStorage.setItem('cys-wsbar-w','176'); localStorage.setItem('cys-wsbar-font','2.2')")
            pg.set_viewport_size({"width": 1400, "height": 480})
            pg.reload(); pg.wait_for_timeout(400)
            nav = pg.evaluate("(() => { const n = document.querySelector('#wsbar'); return { sw: n.scrollWidth, cw: n.clientWidth, w: n.getBoundingClientRect().width, f: getComputedStyle(document.documentElement).getPropertyValue('--wsbar-font').trim() }; })()")
            check(abs(nav["w"] - 176) < 2 and nav["f"] == "2.2", f"극단 복원 176px · 2.2 ({nav})")
            check(nav["sw"] <= nav["cw"] + 1, f"가로 넘침 0 (nav {nav['sw']}/{nav['cw']})")
            pg.evaluate("localStorage.setItem('cys-wsbar-w','216'); localStorage.setItem('cys-wsbar-font','1')")

            check(not errs, f"콘솔 pageerror 0건 (got {errs})")
            b.close()
    finally:
        httpd.shutdown()
    print(f"\n{'PASS' if not failures else 'FAIL'} — 실패 {len(failures)}건")
    for f in failures:
        print(f"  ✗ {f}")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
