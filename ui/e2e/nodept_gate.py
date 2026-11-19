#!/usr/bin/env python3
"""부서 0개 = 부서 흔적 화면 0 게이트 — TICKET=cysr-tabs-sidebar-impl 조각 1h(master#edd9d8a8 · 수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(statusboard_gate 의 SHIM 재사용).
단언: 부서 0개(본부만) = 화면 글자에 「부서」 0건 · 「본부」 0건 · 명령 팔레트에 「부서」 항목 0 ·
      부서 1개 = 부서 카드 보임 · 안내 줄 보임 · 팔레트 「부서 워크스페이스 추가」 있음 · 콘솔 오류 0.
덤프(판정 아님 · 보고 표 재료): 보이는 요소의 툴팁(title) 중 「부서」 를 담은 것.
캡처: 부서 0개 / 1개 각 1장(1920).
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/nodept_gate.py [캡처폴더]
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else sbg.evidence_dir("evidence-tabs-sidebar", "1h")

BASE_SEATS = [sbg.W7[0], sbg.W7[2]]  # master + 워커 1(본부만)
LMS_SEATS = [
    (sbg.LMS, 21, 951, "master", "/u/axdev/lms", "working", "active", False, None, None, 30),
    (sbg.LMS, 22, 952, "worker", "/u/axdev/lms", "waiting", "idle", False, None, "6강 발행", 52),
]
SCEN = {
    "dept0": (BASE_SEATS, []),
    "dept1": (BASE_SEATS + LMS_SEATS, [("lms", sbg.LMS, "LMS")]),
}

JS = r"""
() => {
  const txt = document.body.innerText;
  const count = (w) => txt.split(w).length - 1;
  const lines = (w) => txt.split('\n').filter((l) => l.includes(w)).slice(0, 10);
  const vis = (e) => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const titles = [...document.querySelectorAll('[title]')].filter((e) => vis(e) && e.title.includes('부서')).map((e) => (e.id || e.className || e.tagName) + ': ' + e.title.slice(0, 60));
  const hint = document.getElementById('ws-dept-hint');
  return { dept: count('부서'), hq: count('본부'), deptLines: lines('부서'), hqLines: lines('본부'), titles,
    hintShown: !!hint && vis(hint), names: [...document.querySelectorAll('#ws-tabs .ws-name')].map((e) => e.textContent),
    noDeptsClass: document.body.classList.contains('no-depts'),
    docOver: document.documentElement.scrollWidth > innerWidth };
}
"""


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(sbg.DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            for name, (seats, depts) in SCEN.items():
                print(f"== {name} @ 1920")
                js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in seats]
                ctx = br.new_context(viewport={"width": 1920, "height": 1200})
                pg = ctx.new_page()
                errs: list[str] = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
                pg.add_init_script(sbg.SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", json.dumps(depts)).replace("__BASE__", sbg.BASE))
                pg.goto(f"http://127.0.0.1:{port}/index.html")
                pg.wait_for_timeout(11500)
                st = pg.evaluate(JS)
                pg.screenshot(path=str(OUT / f"{name}-1920.png"))
                print(f"  캡처 {OUT / f'{name}-1920.png'}")
                print(f"  (덤프) 툴팁 속 「부서」 {len(st['titles'])}건: {st['titles']}")
                # 명령 팔레트(⌘K) — 항목 제목 전부
                pg.keyboard.press("Meta+k")
                pg.wait_for_timeout(600)
                pal = pg.evaluate("() => [...document.querySelectorAll('.palette-item .pi-title')].map((e) => e.textContent)")
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(200)
                sbg.check(len(pal) > 0, f"팔레트 열림 · 항목 {len(pal)}")
                if not depts:
                    sbg.check(st["noDeptsClass"], "부서 0개 = body.no-depts")
                    sbg.check(st["dept"] == 0, f"화면 글자 「부서」 0건 ({st['dept']} · {st['deptLines']})")
                    sbg.check(st["hq"] == 0, f"화면 글자 「본부」 0건 ({st['hq']} · {st['hqLines']})")
                    sbg.check(not st["hintShown"], "안내 줄 「새 부서가 필요하면…」 안 보임")
                    sbg.check(not any("부서" in t for t in pal), f"팔레트 「부서」 항목 0 {[t for t in pal if '부서' in t]}")
                    # 대조: 숨김 클래스를 떼면 같은 측정이 흔적을 잡아야 한다(측정이 장님이 아님을 같은 화면에서 확인)
                    ctl = pg.evaluate("() => { document.body.classList.remove('no-depts'); const n = document.body.innerText.split('부서').length - 1; document.body.classList.add('no-depts'); return n; }")
                    sbg.check(ctl >= 1, f"대조: no-depts 를 떼면 「부서」 {ctl}건 보임(측정 유효)")
                else:
                    sbg.check(not st["noDeptsClass"], "부서 1개 = no-depts 아님(지금 그대로)")
                    sbg.check("LMS" in st["names"] and len(st["names"]) >= 2, f"부서 카드 보임 {st['names']}")
                    sbg.check(st["hintShown"], "안내 줄 보임(지금 그대로)")
                    sbg.check(any(t.startswith("부서 워크스페이스 추가") for t in pal), "팔레트 「부서 워크스페이스 추가」 있음")
                sbg.check(not st["docOver"], "가로 넘침 0")
                sbg.check(not errs, f"콘솔 오류 0 {errs[:3]}")
                ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
