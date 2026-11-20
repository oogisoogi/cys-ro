#!/usr/bin/env python3
"""두 줄 격자 게이트 — TICKET=cysr-tabs-sidebar-impl 조각 2b-2(master#fcbc46fb 결정 ① A안 · 수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(statusboard_gate 의 SHIM 재사용). 장면 = 고정 master·cso + site 묶음 좌석 3·7·12 + lms 1(탭이 생기게).
단언(site 탭): 보이는 site 칸 = 좌석 수 · 줄 = ⌈n÷한 줄⌉ · 줄마다 고르게(2b-3 한 규칙 · 옛 「4개 이하 한 줄」 예외 폐지) · 가장 좁은 칸 열 수는 실측 출력(최소 40열은 지킬 수 있을 때만 · grouptabs.gridColumns) ·
      가로 넘침 0 · 고정 기둥 폭 그대로 · 콘솔 오류 0. 캡처 = 3·7·12 × 1920·1280.
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/grid_gate.py [캡처폴더]
"""
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else sbg.evidence_dir("evidence-tabs-sidebar", "2b-2")
B = sbg.BASE


def seats(n: int):
    out = [(B, 1, 900, "master", "/u/axdev", "working", "active", False, None, None, 41),
           (B, 2, 901, "cso", "/u/axdev/cso", "waiting", "idle", False, None, None, 23)]
    for i in range(n):
        out.append((B, 10 + i, 931 + i, "worker" if i == 0 else f"worker-{i + 1}", "/u/axdev/site", "working" if i % 2 == 0 else "waiting",
                    "active" if i % 2 == 0 else "idle", False, None, f"일 {i + 1}", 30 + i))
    out.append((B, 40, 970, "worker-40", "/u/axdev/lms", "waiting", "idle", False, None, "강의", 20))
    return out


JS = r"""
() => {
  const ps = [...document.querySelectorAll('#root .pane')].map((p) => { const r = p.getBoundingClientRect(); const s = p.querySelector('.xterm-screen')?.getBoundingClientRect();
    const rows = p.querySelector('.xterm-rows'); const cols = (() => { const ch = p.querySelector('.xterm-char-measure-element')?.getBoundingClientRect().width; return ch && s ? Math.floor(s.width / (ch / (p.querySelector('.xterm-char-measure-element')?.textContent?.length || 1))) : null; })();
    return { sid: +p.dataset.sid, left: Math.round(r.left), top: Math.round(r.top), w: Math.round(r.width), cols }; });
  return { ps, docOver: document.documentElement.scrollWidth > innerWidth, tab: document.querySelector('#root .group-tab.active .group-tab-name')?.textContent ?? null };
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
            for n in (3, 7, 12):
                js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in seats(n)]
                for w, hgt in ((1920, 1200), (1280, 800)):
                    print(f"== site {n} @ {w}")
                    ctx = br.new_context(viewport={"width": w, "height": hgt})
                    pg = ctx.new_page()
                    errs: list[str] = []
                    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                    pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
                    pg.add_init_script(sbg.SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", "[]").replace("__BASE__", B))
                    pg.goto(f"http://127.0.0.1:{port}/index.html")
                    pg.wait_for_timeout(11500)
                    st = pg.evaluate(JS)
                    shot = OUT / f"site{n}-{w}.png"
                    pg.screenshot(path=str(shot))
                    print(f"  캡처 {shot}")
                    site = [x for x in st["ps"] if 10 <= x["sid"] < 40]
                    fixed = [x for x in st["ps"] if x["sid"] in (1, 2)]
                    sbg.check(st["tab"] == "site" and len(site) == n and not any(x["sid"] == 40 for x in st["ps"]), f"site 탭 = site 칸 {len(site)}/{n} · lms 숨김")
                    tops = sorted({x["top"] for x in site})
                    per = max(sum(1 for x in site if x["top"] == t) for t in tops) if site else 0
                    # (2b-3) 「4개 이하 한 줄」 예외 폐지 — 한 규칙: 줄 = ⌈n÷한 줄⌉ · 줄마다 고르게(가장 긴 줄과 가장 짧은 줄 차이 ≤ 한 줄 칸 수). 칸 수 기대값 대조 = pillar_gate.
                    rows_n = [sum(1 for x in site if x["top"] == t) for t in tops]
                    sbg.check(len(tops) == math.ceil(n / per) and (len(tops) == 1 or per == math.ceil(n / len(tops))), f"줄 {len(tops)} = ⌈{n}÷{per}⌉ · 줄마다 {rows_n}(고르게)")
                    mins = min((x["cols"] for x in site if x["cols"] is not None), default=None)
                    print(f"  (실측) 한 줄 최대 {per}칸 · 줄 {len(tops)} · 가장 좁은 칸 {mins}열")
                    sbg.check(len(fixed) == 2 and all(f["left"] < min(x["left"] for x in site) for f in fixed), "고정 기둥 master·cso = 왼쪽 그대로")
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
