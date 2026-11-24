#!/usr/bin/env python3
"""상단 첫 화면 누를 것 계수 게이트 — TICKET=cysr-1119-s10b(DESIGN §2-1 「상단 첫 화면 누를 것」 · §8-3 MD-T7 · §8-4 MD-T4 · §8-5 MD-CC · 수동 실행 · CI 배선 = master 판단).

기대값은 하드코딩하지 않는다(M-16) — ui/src/topbarlayout.ts 의 두 빌드 상수(SORT_BUTTON_MODE · FILES_BUTTON_DEFAULT)를 읽어 계산한다:
  상단 첫 화면 누를 것 = 늘 보이는 셋(피드백 · 화면 설정 · ↻ 재시작) + 정렬(fold 아니면 1) + 파일(on 이면 1) + 「대화 화면 | 작업 화면」 전환 2
  → fold·off = 5 · keep/dim·off = 6(DESIGN §2-1 합격선).
함께 잰다: 저장 배치 없음(새 설치) · 1280×800 · 콘솔 오류 0 · Control Center(숨은 단추라도 click = 열기) 탭 3(승인 Feed 첫 탭 · 알람 · 휴지통) · 머리 단추 1(닫기).
실행: sh ui/build.sh(또는 같은 dist) 뒤 CHROME_PATH=<chrome-headless-shell> <playwright python3> ui/e2e/topbar_count_gate.py   # exit 0 = PASS
"""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)

SRC = (Path(__file__).resolve().parent.parent / "src" / "topbarlayout.ts").read_text(encoding="utf-8")


def const(name: str) -> str:
    m = re.search(rf'export const {name}: \w+ = "([a-z]+)";', SRC)
    if not m:
        raise SystemExit(f"상수 {name} 를 topbarlayout.ts 에서 찾지 못했다")
    return m.group(1)


SORT = const("SORT_BUTTON_MODE")
FILES = const("FILES_BUTTON_DEFAULT")
EXPECT_TOPBAR = 3 + (0 if SORT == "fold" else 1) + (1 if FILES == "on" else 0) + 2

COUNT = r"""() => {
  const vis = (el) => { if (!el || el.hidden) return false; const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const top = [...document.querySelectorAll('#topbar button, #topbar [role=button], #topbar a[href], #topbar input')].filter(vis);
  return { n: top.length, labels: top.map((b) => (b.textContent || b.getAttribute('aria-label') || b.id).trim()) };
}"""
CC = r"""() => { const vis = (el) => { const r = el.getBoundingClientRect(); return !el.hidden && r.width > 0 && r.height > 0; };
  const tabs = [...document.querySelectorAll('#cc-tabs .cc-tab')].filter(vis).map((b) => b.dataset.view);
  const head = [...document.querySelectorAll('#cc-header button')].filter(vis).map((b) => b.id || b.textContent.trim());
  const active = document.querySelector('#cc-tabs .cc-tab.active')?.dataset.view ?? null;
  const shown = ['feed','alarms','trash'].filter((v) => !document.getElementById('cc-view-' + v)?.hidden);
  return { tabs, head, active, shown }; }"""


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    print(f"상수: SORT_BUTTON_MODE={SORT} · FILES_BUTTON_DEFAULT={FILES} → 기대 상단 누를 것 {EXPECT_TOPBAR}")
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
            ctx = br.new_context(viewport={"width": 1280, "height": 800})
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.goto(f"http://127.0.0.1:{port}/index.html")
            pg.wait_for_timeout(2500)
            c = pg.evaluate(COUNT)
            print(f"   상단 보이는 누를 것 = {c['n']} {c['labels']}")
            sbg.check(c["n"] == EXPECT_TOPBAR, f"상단 첫 화면 누를 것 = {EXPECT_TOPBAR}(상수 계산 · 실측 {c['n']})")
            sbg.check(not any(l in ("상담소", "아고라") or l.startswith("상담소") for l in c["labels"]), "상담소·아고라 없음")
            pg.evaluate("() => document.getElementById('btn-cc').click()")
            pg.wait_for_timeout(500)
            cc = pg.evaluate(CC)
            print(f"   CC 탭 {cc['tabs']} · 머리 단추 {cc['head']} · 활성 {cc['active']} · 보이는 뷰 {cc['shown']}")
            sbg.check(cc["tabs"] == ["feed", "alarms", "trash"], "Control Center 탭 3 = 승인 Feed(첫) · 알람 · 휴지통")
            sbg.check(cc["head"] == ["btn-cc-close"], "Control Center 머리 단추 1 = 닫기")
            sbg.check(cc["active"] == "feed" and cc["shown"] == ["feed"], "처음 여는 탭 = 승인 Feed")
            sbg.check(not errs, f"콘솔 오류 0 {errs[:3]}")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
