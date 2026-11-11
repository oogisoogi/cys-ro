#!/usr/bin/env python3
"""앱 재실행 · 재부팅 뒤 탭 배치 동일 게이트 — TICKET=cysr-tabs-sidebar-impl 남은 4번 ⓒ(수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(statusboard_gate SHIM). 1회차: 좌석 W7 · lms 탭 → 934 넓게 보기 · 931 을 video 로 옮김(이벤트) → 저장소(localStorage)만
들고 새 창을 연다(= 앱 종료 → 재실행). 2회차 데몬은 재부팅한 셈 = 같은 좌석(역할·폴더)에 **번호를 새로 발급**(sid +100 · 목록 group 칸 없음).
단언: 탭 강조 = 1회차와 같음 · 넓게 보기 = 같은 좌석(역할 worker-4 = 새 번호 106) · 931(역할 worker)은 video 묶음 그대로 · 탭 순서 그대로 · 콘솔 오류 0.
★헤드리스 브라우저 장면이다 — 실제 앱(Tauri) 창·격리 프로필 실측이 아니다(박사님 화면에 창을 띄우지 않기 위해).
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/restart_gate.py [캡처폴더]
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else sbg.UI.parent / "docs" / "evidence-tabs-sidebar" / "restart"


def js_of(seats, bump: int):
    return [dict(sock=s[0], sid=s[1] + bump, no=s[2] + bump, role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=False, self=s[8], task=s[9], ctx=s[10]) for s in seats]


STATE = r"""
() => ({ tab: document.querySelector('#root .group-tab.active .group-tab-name')?.textContent ?? null,
  tabs: [...document.querySelectorAll('#root .group-tab .group-tab-name')].map((e) => e.textContent),
  panes: [...document.querySelectorAll('#root .pane')].map((p) => +p.dataset.sid).sort((a, b) => a - b),
  groups: (() => { const host = document.querySelector('.ws-seats[data-seat-host]:not([data-seat-host="board"]):not([data-seat-host^="n"])'); const out = {}; let cur = null;
    for (const el of host ? host.children : []) { if (el.classList.contains('ws-seat-group')) { cur = el.querySelector('.ws-seat-group-name')?.textContent; out[cur] = []; }
      else if (cur && el.classList.contains('ws-seat') && !el.classList.contains('named')) out[cur].push(el.querySelector('.ws-seat-no')?.textContent); } return out; })() })
"""


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(sbg.DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    shim = lambda seats: sbg.SHIM.replace("__SEATS__", json.dumps(seats)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            # 1회차
            c1 = br.new_context(viewport={"width": 1920, "height": 1200})
            p1 = c1.new_page()
            e1: list[str] = []
            p1.on("pageerror", lambda e: e1.append(str(e)[:200]))
            p1.add_init_script(shim(js_of(sbg.W7, 0)))
            p1.goto(url)
            p1.wait_for_timeout(11500)
            p1.evaluate("() => window.__emit('daemon-event', { type: 'event', seq: 1, name: 'surface.group.changed', category: 'surface', surface_id: 3, payload: { surface_id: 3, group: 'video', previous: null } })")
            p1.wait_for_timeout(400)
            p1.click('#root .group-tab:has-text("lms")')
            p1.wait_for_timeout(400)
            p1.click('.ws-seat[data-sid="6"]')
            p1.wait_for_timeout(600)
            s1 = p1.evaluate(STATE)
            p1.screenshot(path=str(OUT / "before-1920.png"))
            storage = c1.storage_state()
            c1.close()
            sbg.check(s1["tab"] is None and s1["panes"] == [1, 2, 6], f"1회차 = 934 넓게 보기(넓게 보는 동안 탭 강조 없음 = 원래 동작) {s1['tab']} {s1['panes']}")
            # 2회차 — 저장소만 들고 새 창 · 데몬 재부팅(번호 +100)
            c2 = br.new_context(viewport={"width": 1920, "height": 1200}, storage_state=storage)
            p2 = c2.new_page()
            e2: list[str] = []
            p2.on("pageerror", lambda e: e2.append(str(e)[:200]))
            p2.add_init_script(shim(js_of(sbg.W7, 100)))
            p2.goto(url)
            p2.wait_for_timeout(11500)
            s2 = p2.evaluate(STATE)
            p2.screenshot(path=str(OUT / "after-restart-renumbered-1920.png"))
            c2.close()
            print(f"  1회차 {s1}\n  2회차 {s2}")
            sbg.check(s2["tab"] == s1["tab"], f"재실행 뒤 탭 강조 = 1회차와 같음(넓게 보는 중 = 강조 없음) ({s1['tab']} → {s2['tab']})")
            sbg.check(s2["tabs"] == s1["tabs"], f"탭 순서 그대로 {s1['tabs']} → {s2['tabs']}")
            sbg.check(s2["panes"] == [101, 102, 106], f"넓게 보기 = 같은 좌석(역할 worker-4 · 새 번호 106) + 고정 101·102 {s2['panes']}")
            sbg.check("1031" in s2["groups"].get("video", []), f"옮긴 좌석(역할 worker · 새 번호 1031) = video 그대로 {s2['groups']}")
            sbg.check(not e1 and not e2, f"콘솔 오류 0 {(e1 + e2)[:2]}")
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
