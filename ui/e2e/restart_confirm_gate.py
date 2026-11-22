#!/usr/bin/env python3
"""「↻ 재시작」 단추 진입 확인 게이트 — TICKET=cysr-restart-confirm-1118(수동 실행 — CI 미배선).

실제 번들(ui/dist) + __TAURI__ 대역(statusboard_gate SHIM) + invoke 기록. 단추를 누르면 확인 창이 **보이고**, 취소 길(Esc · Enter(기본 초점) · 바깥 클릭)은 어떤 명령도 보내지 않으며,
「다시 시작」 만 drain_verify 를 시작한다. 캡처 1장 = 확인 창이 떠 있는 장면.
★헤드리스 브라우저 장면이다 — 실제 앱(Tauri) 창 실측이 아니다(박사님 화면에 창을 띄우지 않기 위해).
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/restart_confirm_gate.py [캡처폴더]
"""
import http.server
import importlib.util
import json
import os
import sys
import threading
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else sbg.evidence_dir("evidence-restart-confirm")

# SHIM 위에 invoke 기록을 덧씌운다 — 어떤 명령이 나갔는지 직접 센다.
RECORD = r"""
(() => {
  window.__CALLS = [];
  const inv = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => { window.__CALLS.push(cmd); return inv(cmd, args); };
})();
"""
MODAL = r"""
() => { const o = document.querySelector('.confirm-overlay'); if (!o) return null; const r = o.getBoundingClientRect(); const a = document.activeElement;
  return { visible: r.width > 0 && r.height > 0, title: o.querySelector('h3')?.textContent, body: o.querySelector('p')?.textContent,
    yes: o.querySelector('.modal-yes')?.textContent, no: o.querySelector('.modal-no')?.textContent, focusIsNo: a === o.querySelector('.modal-no') }; }
"""
DRAIN = "() => window.__CALLS.filter((c) => c === 'drain_verify').length"
failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(f"  [{'PASS' if c else 'FAIL'}] {m}")
    if not c:
        failures.append(m)


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(sbg.DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    seats = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=False, self=s[8], task=s[9], ctx=s[10]) for s in (sbg.W7[:1] + [sbg.W7[2]])]
    shim = sbg.SHIM.replace("__SEATS__", json.dumps(seats)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1600, "height": 900})
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim + RECORD)
            pg.goto(url)
            pg.wait_for_selector("#btn-restart-daemon", state="visible")
            pg.wait_for_timeout(2500)

            print("[1] 단추 클릭 → 확인 창")
            check(pg.evaluate(MODAL) is None, "클릭 전에는 확인 창이 없다")
            pg.click("#btn-restart-daemon")
            pg.wait_for_selector(".confirm-overlay", state="visible", timeout=3000)
            m = pg.evaluate(MODAL)
            print("   창:", m)
            check(bool(m and m["visible"]), "확인 창이 보인다")
            check(m["title"] == "데몬을 다시 시작할까요?", "제목 = 데몬을 다시 시작할까요?")
            check(m["body"] == "일하던 자리들이 잠깐 멈췄다가 대화 기억과 함께 다시 켜집니다.", "본문 = 박사님 문구")
            check(m["yes"] == "다시 시작" and m["no"] == "취소", "단추 = 다시 시작 / 취소")
            check(m["focusIsNo"] is True, "기본 초점 = 취소")
            check(pg.evaluate(DRAIN) == 0, "창이 떠 있는 동안 drain_verify 0회")
            pg.screenshot(path=str(OUT / "restart-confirm-modal.png"))

            print("[2] Esc = 취소")
            pg.keyboard.press("Escape")
            pg.wait_for_selector(".confirm-overlay", state="detached", timeout=3000)
            pg.wait_for_timeout(300)
            check(pg.evaluate(DRAIN) == 0, "Esc 후 drain_verify 0회")

            print("[3] Enter(기본 초점 = 취소) = 취소")
            pg.click("#btn-restart-daemon")
            pg.wait_for_selector(".confirm-overlay", state="visible", timeout=3000)
            pg.keyboard.press("Enter")
            pg.wait_for_selector(".confirm-overlay", state="detached", timeout=3000)
            pg.wait_for_timeout(300)
            check(pg.evaluate(DRAIN) == 0, "Enter 후 drain_verify 0회")

            print("[4] 바깥 클릭 = 취소")
            pg.click("#btn-restart-daemon")
            pg.wait_for_selector(".confirm-overlay", state="visible", timeout=3000)
            pg.mouse.click(5, 5)
            pg.wait_for_selector(".confirm-overlay", state="detached", timeout=3000)
            pg.wait_for_timeout(300)
            check(pg.evaluate(DRAIN) == 0, "바깥 클릭 후 drain_verify 0회")

            print("[5] 「취소」 단추 = 취소")
            pg.click("#btn-restart-daemon")
            pg.wait_for_selector(".confirm-overlay", state="visible", timeout=3000)
            pg.click(".confirm-overlay .modal-no")
            pg.wait_for_selector(".confirm-overlay", state="detached", timeout=3000)
            pg.wait_for_timeout(300)
            check(pg.evaluate(DRAIN) == 0, "취소 단추 후 drain_verify 0회")

            print("[6] 「다시 시작」 → 기존 흐름(drain_verify 시작)")
            pg.click("#btn-restart-daemon")
            pg.wait_for_selector(".confirm-overlay", state="visible", timeout=3000)
            pg.click(".confirm-overlay .modal-yes")
            pg.wait_for_selector(".confirm-overlay", state="detached", timeout=3000)
            pg.wait_for_function("() => window.__CALLS.includes('drain_verify')", timeout=5000)
            check(pg.evaluate(DRAIN) == 1, "다시 시작 → drain_verify 1회")

            check(not errs, f"콘솔 오류 0 {errs[:2]}")
            br.close()
    finally:
        httpd.shutdown()
    print(f"\n결과: {'전부 통과' if not failures else f'실패 {len(failures)}건'} · 캡처 = {OUT / 'restart-confirm-modal.png'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
