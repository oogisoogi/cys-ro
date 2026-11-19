#!/usr/bin/env python3
"""Control Center 위 팝오버 층서 게이트 — TICKET=cysr-cc-popover-z-1118(CI 배선 = ci-branch ui-check · TICKET=cysr-1116-s79-1119).
결함: Control Center(#cc-panel z 1500)를 연 채 상단바 「화면 설정」(#btn-theme)을 누르면 #theme-pop(z 1000)이 패널 뒤에 열려 안 보였다.
캡처: CC 연 상태 + 화면 설정 팝오버 1장. 단언: 팝오버 존재 · 팝오버 중앙점의 최상위 요소가 팝오버 자신 · 콘솔 오류 0.
실행: CHROME_PATH=<chrome-headless-shell> <playwright python3> ui/e2e/cc_popover_z_gate.py [캡처 파일.png]
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else sbg.evidence_dir("evidence-cc-popover-z", "theme-pop-over-cc-1920.png")


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    SHOT.parent.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(sbg.DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in sbg.W7]
    shim = sbg.SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1920, "height": 1200})
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.goto(f"http://127.0.0.1:{port}/index.html")
            pg.wait_for_timeout(3000)
            pg.evaluate("() => document.getElementById('btn-cc').click()")  # 단추가 숨어 있어도 click = setCcOpen(!ccOpen)
            pg.wait_for_timeout(500)
            cc_open = pg.evaluate("() => !document.getElementById('cc-panel').hidden")
            sbg.check(cc_open, "Control Center 열림(전제)")
            pg.click("#btn-theme")
            pg.wait_for_timeout(500)
            info = pg.evaluate("""() => {
              const pop = document.getElementById('theme-pop');
              if (!pop) return null;
              const r = pop.getBoundingClientRect();
              const top = document.elementFromPoint(r.left + r.width / 2, r.top + Math.min(r.height / 2, 40));
              return { z: getComputedStyle(pop).zIndex, ccz: getComputedStyle(document.getElementById('cc-panel')).zIndex,
                       topIsPop: !!top && (top === pop || pop.contains(top)), topId: top ? (top.id || top.className || top.tagName) : null };
            }""")
            sbg.check(info is not None, "화면 설정 팝오버(#theme-pop) 생성")
            print(f"   z(theme-pop)={info['z']} z(cc-panel)={info['ccz']} 중앙점 최상위={info['topId']}")
            sbg.check(info["topIsPop"], "CC 연 상태에서 팝오버 중앙점의 최상위 요소 = 팝오버 자신(패널 뒤에 깔리지 않음)")
            pg.screenshot(path=str(SHOT))
            sbg.check(not errs, f"콘솔 오류 0 {errs[:3]}")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
