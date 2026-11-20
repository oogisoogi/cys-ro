#!/usr/bin/env python3
"""고정 기둥 폭 규칙 게이트 — 탭·옆 막대 조각 2b-3(수동 실행 — CI 미배선 · 규칙 = ui/src/grouptabs.ts pillarCols).

실제 번들 + __TAURI__ 대역(statusboard_gate SHIM 재사용 · grid_gate 장면 재사용). 장면 = 고정 master·cso + site 묶음 좌석 3·4·7 + lms 1(탭이 생기게).
폭 = 1371(노트북 창) · 1920(싱글) · 2786(4K 창).
단언(site 탭):
  ① 기둥 열 수(master 칸이 실제로 보낸 PTY 열) = clamp(64, ⌊배치 영역 열 수 × 36%⌋, 96) ±1(여백 근사) · 글자 칸 = 글자 화면 폭 ÷ PTY 열
  ② 한 줄 칸 수 = grouptabs.gridColumns 를 실측 재료(오른쪽 px · 높이 · 40열 px · 12줄 px)로 다시 계산한 값 · 줄 = ⌈n÷한 줄⌉
  ③ 40열×12줄을 지킬 수 있는 장면이면 가장 좁은 칸 ≥ 40열(못 지키면 「가장 덜 모자란 격자」 = 실측만 적음) · 가로 넘침 0 · 콘솔 오류 0
  ④ 탭 20회 왕복(site↔lms) 동안 resize_surface 재전송 ≤ 4(2c-1 실측 4) · 숨은 탭 좌석의 마지막 PTY 크기 = 보일 때 맞춘 크기
노브 끔(cys-group-tabs=0) 1920 = 옛 규칙(기둥 ≥ 90열 · 탭 줄 0) — 1.1.14 화면 그대로.
캡처 = docs/evidence-tabs-sidebar/2b-3/site{3,4,7}-{1371,1920,2786}.png + 실측 표(stdout · CAPTIONS.md 재료).
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/pillar_gate.py [캡처폴더]
"""
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sbg = _load("sbg", "statusboard_gate.py")
grid = _load("grid", "grid_gate.py")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else sbg.UI.parent / "docs" / "evidence-tabs-sidebar" / "2b-3"
SIZES = ((1371, 860), (1920, 1080), (2786, 1600))

# resize_surface 를 세는 덧씌움(SHIM 뒤에 실행) — sid 별 마지막 보낸 열·행도 남긴다.
COUNT = r"""
(() => {
  const inv = window.__TAURI__.core.invoke;
  window.__resizes = []; window.__lastSize = {};
  window.__TAURI__.core.invoke = (cmd, a) => {
    if (cmd === 'resize_surface') { window.__resizes.push([a.surfaceId, a.cols, a.rows]); window.__lastSize[a.surfaceId] = [a.cols, a.rows]; }
    return inv(cmd, a);
  };
})();
"""

MEASURE = r"""
() => {
  const root = document.getElementById('root').getBoundingClientRect();
  const ps = [...document.querySelectorAll('#root .pane')].map((p) => {
    const r = p.getBoundingClientRect(); const s = p.querySelector('.xterm-screen')?.getBoundingClientRect();
    const m = p.querySelector('.xterm-char-measure-element'); const cw = m ? m.getBoundingClientRect().width / (m.textContent?.length || 1) : null;
    const rows = p.querySelectorAll('.xterm-rows > div').length;
    return { sid: +p.dataset.sid, left: r.left, top: Math.round(r.top), w: r.width, h: r.height, sw: s?.width ?? null, sh: s?.height ?? null, cw,
      cols: cw && s ? Math.floor(s.width / cw) : null, rows };
  });
  const tabbar = document.querySelector('#root .group-tabbar')?.getBoundingClientRect() ?? null;
  const area = document.querySelector('#root .group-tab-area')?.getBoundingClientRect() ?? null;
  return { root: { w: root.width, h: root.height, left: root.left }, ps, tabbar: tabbar && { h: tabbar.height }, area: area && { w: area.width, h: area.height, left: area.left },
    docOver: document.documentElement.scrollWidth > innerWidth, tab: document.querySelector('#root .group-tab.active .group-tab-name')?.textContent ?? null };
}
"""


def pillar_cols(area_cols: int) -> int:
    return min(96, max(64, (max(0, area_cols) * 36) // 100))


def grid_columns(n: int, aw: float, ah: float, mw: float, mh: float) -> int:
    """grouptabs.gridColumns 그대로(파이썬 대조본)."""
    if n <= 1:
        return 1
    if not (aw > 0 and ah > 0 and mw > 0 and mh > 0):
        return n if n <= 4 else math.ceil(n / 2)
    even = lambda c: math.ceil(n / math.ceil(n / c))  # noqa: E731
    fit = lambda c: min(aw / c / mw, ah / math.ceil(n / c) / mh)  # noqa: E731
    mx = min(n, max(1, math.floor(aw / mw)))
    if fit(mx) >= 1:
        return even(mx)
    best, bf = mx, -1.0
    for c in range(n, 0, -1):
        f = fit(even(c))
        if f > bf:
            best, bf = even(c), f
    return best


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(sbg.DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    table: list[str] = []
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

            def page(n: int, w: int, hgt: int, knob_off: bool = False):
                js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in grid.seats(n)]
                ctx = br.new_context(viewport={"width": w, "height": hgt})
                pg = ctx.new_page()
                errs: list[str] = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
                if knob_off:
                    pg.add_init_script("localStorage.setItem('cys-group-tabs', '0')")
                pg.add_init_script(sbg.SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE))
                pg.add_init_script(COUNT)
                pg.goto(f"http://127.0.0.1:{port}/index.html")
                pg.wait_for_timeout(11500)
                return ctx, pg, errs

            for w, hgt in SIZES:
                for n in (3, 4, 7):
                    print(f"== site {n} @ {w}x{hgt}")
                    ctx, pg, errs = page(n, w, hgt)
                    st = pg.evaluate(MEASURE)
                    shot = OUT / f"site{n}-{w}.png"
                    pg.screenshot(path=str(shot))
                    print(f"  캡처 {shot}")
                    last0 = pg.evaluate("window.__lastSize")
                    for x in st["ps"]:  # 열·행 = 실제로 보낸 PTY 크기(글자 측정 요소는 칸 폭보다 좁게 재여 2열쯤 부풀었다)
                        sz = last0.get(str(x["sid"]))
                        x["cols"], x["rows"] = (sz[0], sz[1]) if sz else (None, x["rows"])
                        x["cw"] = x["sw"] / sz[0] if sz and x["sw"] else None
                    site = [x for x in st["ps"] if 10 <= x["sid"] < 40]
                    master = next((x for x in st["ps"] if x["sid"] == 1), None)
                    sbg.check(st["tab"] == "site" and len(site) == n and not any(x["sid"] == 40 for x in st["ps"]), f"site 탭 = site 칸 {len(site)}/{n} · lms 숨김")
                    if not site or not master or not master["cw"]:
                        sbg.check(False, "실측 재료 없음")
                        ctx.close()
                        continue
                    cw = master["cw"]
                    area_cols = math.floor(st["root"]["w"] / cw)
                    want_pillar = pillar_cols(area_cols)
                    sbg.check(abs(master["cols"] - want_pillar) <= 1, f"기둥 열 수 {master['cols']} = clamp(64, ⌊{area_cols}×36%⌋, 96) = {want_pillar} ±1")
                    # 격자 재료(실측): 오른쪽 영역 px(탭 줄 아래 높이) · 칸 여백 = 칸 − 글자 화면
                    s0 = site[0]
                    pad_w, pad_h = s0["w"] - s0["sw"], s0["h"] - s0["sh"]
                    ch = s0["sh"] / s0["rows"] if s0["rows"] else None
                    aw = st["area"]["w"] if st["area"] else st["root"]["w"]
                    ah = st["root"]["h"]
                    mw, mh = 40 * cw + pad_w, (12 * ch + pad_h) if ch else 0
                    want_per = grid_columns(n, aw, ah, mw, mh)
                    tops = sorted({x["top"] for x in site})
                    per = max(sum(1 for x in site if x["top"] == t) for t in tops)
                    sbg.check(per == want_per and len(tops) == math.ceil(n / per), f"한 줄 {per}칸(기대 {want_per}) · 줄 {len(tops)} = ⌈{n}÷{per}⌉")
                    mins = min(x["cols"] for x in site if x["cols"] is not None)
                    mx = min(n, max(1, math.floor(aw / mw)))
                    meets = aw / mx / mw >= 1 and mh > 0 and ah / math.ceil(n / mx) / mh >= 1
                    if meets:
                        sbg.check(mins >= 40, f"가장 좁은 칸 {mins}열 ≥ 40(40열×12줄을 지킬 수 있는 장면)")
                    else:
                        print(f"  (40열×12줄 못 지킴 → 가장 덜 모자란 격자 · 가장 좁은 칸 {mins}열)")
                    sbg.check(not st["docOver"], "가로 넘침 0")
                    # ④ 탭 20회 왕복 resize 재전송 · 숨은 탭 PTY 크기
                    before = pg.evaluate("window.__resizes.length")
                    vis = {x["sid"]: [x["cols"], x["rows"]] for x in site}
                    for _ in range(20):
                        pg.click('#root .group-tab:has-text("lms")')
                        pg.wait_for_timeout(60)
                        pg.click('#root .group-tab:has-text("site")')
                        pg.wait_for_timeout(60)
                    pg.wait_for_timeout(400)
                    rz = pg.evaluate("window.__resizes.length") - before
                    sbg.check(rz <= 4, f"탭 20회 왕복 resize_surface 재전송 {rz} ≤ 4(2c-1 실측)")
                    last = pg.evaluate("window.__lastSize")
                    pg.click('#root .group-tab:has-text("lms")')
                    pg.wait_for_timeout(400)
                    hidden_same = all(last.get(str(s)) == vis[s] for s in vis)
                    sbg.check(hidden_same, f"숨은 site 좌석 PTY 열 = 보일 때 맞춘 열 {[(s, last.get(str(s))) for s in vis]} vs {vis}")
                    sbg.check(not errs, f"콘솔 오류 0 {errs[:3]}")
                    line = (f"| site{n}-{w}.png | {w}×{hgt} · 좌석 {n} | {st['root']['w']:.0f}px = {area_cols}열(칸 {cw:.2f}px) | {master['cols']}열(기대 {want_pillar}) · {master['w'] / st['root']['w'] * 100:.1f}% "
                            f"| {per}칸 × {len(tops)}줄(기대 한 줄 {want_per}) | {mins}열 × {min(x['rows'] for x in site)}줄{'' if meets else '(못 지킴)'} | {rz} |")
                    print("  " + line)
                    table.append(line)
                    ctx.close()
            # (948 못 본 것 · master#07acca07) 경계를 끌지 않고 눌렀다 떼기만 하면 기본 폭 표지(leftAuto)가 그대로여야 한다
            print("== 경계 눌렀다 떼기(끌지 않음) @ 1920 좌석 3")
            ctx, pg, errs = page(3, 1920, 1080)
            lay = lambda: json.loads(pg.evaluate("() => localStorage.getItem('cys-layout-v2')") or "{}")  # noqa: E731
            t0 = (lay().get("workspaces") or [{}])[0].get("tree") or {}
            box = pg.query_selector("#root > .split.row > .divider").bounding_box()
            pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            pg.mouse.down()
            pg.mouse.up()
            pg.wait_for_timeout(400)
            t1 = (lay().get("workspaces") or [{}])[0].get("tree") or {}
            sbg.check(t0.get("leftAuto") is True, f"준비: 저장 트리 = 기본 폭 표지 {t0.get('leftAuto')} · 몫 {t0.get('ratio')}")
            sbg.check(t1.get("leftAuto") is True and t1.get("ratio") == t0.get("ratio"), f"눌렀다 떼기 뒤에도 표지·몫 그대로 {t1.get('leftAuto')} · {t0.get('ratio')} → {t1.get('ratio')}")
            # 실제로 끌면 사람 폭(표지 지움 · 그 몫 저장)
            pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            pg.mouse.down()
            pg.mouse.move(box["x"] + 120, box["y"] + box["height"] / 2, steps=5)
            pg.mouse.up()
            pg.wait_for_timeout(400)
            t2 = (lay().get("workspaces") or [{}])[0].get("tree") or {}
            sbg.check("leftAuto" not in t2 and t2.get("ratio") != t0.get("ratio"), f"끌면 사람 폭 = 표지 지움·몫 바뀜 {t2.get('leftAuto')} · {t2.get('ratio')}")
            sbg.check(not errs, f"콘솔 오류 0 {errs[:3]}")
            ctx.close()
            # 노브 끔 = 옛 규칙(1.1.14) 그대로
            print("== 노브 끔 site 3 @ 1920")
            ctx, pg, errs = page(3, 1920, 1080, knob_off=True)
            st = pg.evaluate(MEASURE)
            master = next((x for x in st["ps"] if x["sid"] == 1), None)
            sbg.check(st["tabbar"] is None and any(x["sid"] == 40 for x in st["ps"]), "노브 끔 = 탭 줄 0 · lms 좌석도 나란히")
            sbg.check(master is not None and master["cols"] is not None and master["cols"] >= 89, f"노브 끔 기둥 = 옛 최소 90열 규칙 그대로({master and master['cols']}열)")
            sbg.check(not errs, f"콘솔 오류 0 {errs[:3]}")
            pg.screenshot(path=str(OUT / "knoboff-site3-1920.png"))
            print(f"  노브 끔 기둥 {master and master['cols']}열")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\n| 파일 | 장면 | 배치 영역 | 기둥 | 격자 | 가장 좁은 칸 | 왕복 resize |")
    print("|---|---|---|---|---|---|---|")
    for line in table:
        print(line)
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    for f in sbg.failures:
        print("  FAIL:", f)
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
