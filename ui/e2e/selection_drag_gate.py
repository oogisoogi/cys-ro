#!/usr/bin/env python3
"""선택 드래그 잔류(클릭 없이 커서만 움직여도 선택 블록이 따라 늘어남) 재현·회귀 게이트 (수동 실행 — CI 미배선).

TICKET=cysr-stuck-selection-drag · 박사님 영상 2026-10-28 22:53(클릭 없이 커서 이동 → 연보라 선택이 커서를 따라 늘어남).

기제(xterm 5.5.0 SelectionService · node_modules/@xterm/xterm/src/browser/services/SelectionService.ts):
  mousedown 때 document 에 mousemove·mouseup 처리기를 붙이고(_addMouseDownListeners), mouseup 이 와야만 뗀다.
  _handleMouseMove 는 event.buttons 를 보지 않는다 → mouseup 한 번을 못 받으면 단추를 뗀 뒤의 **모든 커서 이동**이
  선택 끝점을 옮긴다. 그 사이 새 mousedown 이 오면 _dragScrollIntervalTimer 를 덮어써 옛 타이머가 고아로 남는다.

판정(케이스마다 같은 입력 · 진짜 입력 경로 = Playwright 마우스):
  A. 정상      : 누름 → 끌기 → 뗌 → 이동. 뗀 뒤 선택이 그대로여야 한다.
  B. 뗌 유실   : 같은 입력이되 창 capture 에서 mouseup 을 삼켜 「웹뷰가 mouseup 을 못 받은」 상황을 만든다.
                 수리 전 = 뗀 뒤 이동에 선택이 커서를 따라 늘어남(영상 증상) · 수리 후 = 그대로.
  C. 끄는 중 재배치(대조군만): 끄는 중 터미널 요소를 DOM 에서 뗐다 다시 붙인다(앱 재렌더 후보 ②) — 정상 뗌이면 잔류 없음.
  D. 끄는 중 휠 : 누름 → 끌기 → 휠 → 뗌 → 이동(후보 ③) — 정상 뗌이면 잔류 없음.
  E. 뗌 유실 후 창 blur : 수리 후 = blur 로 끄기가 끝나 이후 이동에 선택 불변.
  F. 일반 기능 회귀 : 끌기 선택 텍스트·더블클릭 단어 선택이 수리 전후 같다.

대상: control(순수 xterm 5.5.0 페이지 = 같은 판 대조군) · app(ui/dist 실제 번들 + __TAURI__ 대역).
엔진: Playwright WebKit(맥 WKWebView 와 같은 엔진 계열) + Chromium(윈 WebView2 계열).

사전: sh ui/build.sh · pip install playwright · playwright install webkit chromium
실행: python3 ui/e2e/selection_drag_gate.py            # exit 0 = PASS (수리된 앱 기준)
      python3 ui/e2e/selection_drag_gate.py --expect-bug  # 수리 전 앱 번들에서 B 가 재현되는지(뮤테이션 확인용)
"""
import http.server
import shutil
import sys
import tempfile
import threading
from pathlib import Path

UI = Path(__file__).resolve().parent.parent
DIST = UI / "dist"
XTERM = UI / "node_modules" / "@xterm" / "xterm"

CONTROL_HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="xterm.css"><style>html,body{margin:0;background:#111}#t{width:900px;height:600px}</style>
</head><body><div id="host"><div id="t"></div></div><script src="xterm.js"></script><script>
  const term = new Terminal({ cols: 100, rows: 30, macOptionClickForcesSelection: true });
  term.open(document.getElementById('t'));
  window.__term = term;
  window.__fill = () => new Promise((r) => {
    let s = '';
    for (let i = 0; i < 28; i++) s += 'line' + String(i).padStart(2, '0') + ' alpha beta gamma delta epsilon zeta eta theta\\r\\n';
    term.write(s, r);
  });
</script></body></html>"""

SHIM = r"""
(() => {
  const listeners = {};
  window.__sim = { listeners };
  const respond = (cmd, a) => {
    switch (cmd) {
      case 'daemon_status': return { daemon_pid: 4242, socket_path: '/sandbox/cys.sock', version: '1.1.10', app_version: '1.1.10' };
      case 'app_version': return '1.1.10';
      case 'list_depts': return { depts: {} };
      case 'dept_tombstones': return [];
      case 'fresh_start_check': return { ask: false };
      case 'list_surfaces': return { surfaces: [{ surface_id: 1, title: 'zsh', exited: false, role: null, agent: null, live_cwd: '/sandbox' }] };
      case 'attach_surface': return { output_event: 'sim-out-' + a.surfaceId, exited_event: 'sim-exit-' + a.surfaceId };
      default: return null;
    }
  };
  window.__TAURI__ = {
    core: { invoke: (cmd, args) => new Promise((res, rej) => { try { res(respond(cmd, args ?? {})); } catch (e) { rej(e); } }) },
    event: { listen: (name, h) => { (listeners[name] ??= []).push(h); return Promise.resolve(() => {}); } },
  };
  window.__emit = (name, payload) => { for (const h of listeners[name] ?? []) h({ payload }); return (listeners[name] ?? []).length; };
  window.__fill = () => new Promise((r) => {
    let s = '';
    for (let i = 0; i < 28; i++) s += 'line' + String(i).padStart(2, '0') + ' alpha beta gamma delta epsilon zeta eta theta\r\n';
    const b64 = btoa(s);
    window.__emit('sim-out-1', b64);
    setTimeout(r, 300);
  });
})();
"""

# 화면에 그려진 선택 = DOM 렌더러의 .xterm-selection 자식 사각형들의 합(두 대상 공통 · 제품 내부 API 무의존).
JS_SEL = r"""
() => {
  const boxes = [...document.querySelectorAll('.xterm-selection div')].map((d) => d.getBoundingClientRect()).filter((r) => r.width > 0 && r.height > 0);
  if (!boxes.length) return null;
  const top = Math.min(...boxes.map((b) => b.top)), bottom = Math.max(...boxes.map((b) => b.bottom));
  return { top: Math.round(top), bottom: Math.round(bottom), n: boxes.length };
}
"""

JS_SCREEN = r"""
() => {
  const s = document.querySelector('.xterm-screen');
  const r = s.getBoundingClientRect();
  const rows = document.querySelectorAll('.xterm-rows > div').length || 30;
  return { x: r.left, y: r.top, w: r.width, h: r.height, rowH: r.height / rows };
}
"""

# 복사 = xterm 자체 copy 처리기(요소의 copy 이벤트 → clipboardData)에 맡긴다 — ⌘C·Ctrl+Shift+C 와 같은 끝 경로.
JS_COPY = r"""
() => {
  const ta = document.querySelector('.xterm-helper-textarea');
  if (!ta) return null;
  const dt = new DataTransfer();
  ta.dispatchEvent(new ClipboardEvent('copy', { clipboardData: dt, bubbles: true, cancelable: true }));
  return dt.getData('text/plain');
}
"""

# 뗌 유실 흉내 — 페이지 스크립트보다 **먼저** 붙는 창 capture 처리기라 앱·xterm 의 어떤 처리기도 그 mouseup 을 못 본다
# (웹뷰가 mouseup 을 아예 배달하지 않은 상황과 같다 · 나중에 붙이면 수리 처리기가 뗌을 먼저 봐 시험이 거짓 적색이 된다).
LOSE_UP_INIT = r"""
window.addEventListener('mouseup', (e) => { if (window.__loseUp) e.stopImmediatePropagation(); }, true);
"""
JS_SWALLOW_UP = "() => { window.__loseUp = true; }"
JS_UNSWALLOW_UP = "() => { window.__loseUp = false; }"

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def serve(root: Path):
    handler_cls = type("Quiet", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: handler_cls(*a, directory=str(root), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def open_target(browser, kind, port, errs):
    ctx = browser.new_context(viewport={"width": 1200, "height": 800})
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    pg.add_init_script(LOSE_UP_INIT)
    if kind == "app":
        pg.add_init_script(SHIM)
        pg.goto(f"http://127.0.0.1:{port}/index.html")
        pg.wait_for_function("document.querySelectorAll('.pane .xterm-screen').length >= 1 && (window.__sim.listeners['sim-out-1']||[]).length > 0", timeout=15000)
    else:
        pg.goto(f"http://127.0.0.1:{port}/control.html")
        pg.wait_for_function("!!window.__term", timeout=15000)
    pg.evaluate("() => window.__fill()")
    pg.wait_for_timeout(250)
    return ctx, pg


def cell(sc, col, row):
    cw = sc["w"] / 100 if sc["w"] > 0 else 8
    return sc["x"] + 4 + col * min(cw, 8), sc["y"] + sc["rowH"] * (row + 0.5)


def drag(pg, sc, before_up=None, lose_up=False):
    """행 3 → 행 8 로 끌고 떼기. lose_up=True 면 그 뗌을 페이지가 못 받게 한다."""
    x0, y0 = cell(sc, 2, 3)
    x1, y1 = cell(sc, 20, 8)
    pg.mouse.move(x0, y0)
    pg.mouse.down()
    pg.mouse.move(x1, y1, steps=6)
    if before_up:
        before_up()
    if lose_up:
        pg.evaluate(JS_SWALLOW_UP)
    pg.mouse.up()
    if lose_up:
        pg.evaluate(JS_UNSWALLOW_UP)
    pg.wait_for_timeout(120)


def wander(pg, sc):
    """단추를 뗀 채로 아래로 커서만 움직인다(영상의 손짓)."""
    x, y = cell(sc, 40, 20)
    pg.mouse.move(x, y, steps=8)
    pg.wait_for_timeout(200)


def reset(pg, sc):
    x, y = cell(sc, 60, 26)
    pg.mouse.move(x, y)
    pg.mouse.click(x, y)  # 빈 곳 단일 클릭 = 선택 해제·끄기 상태 정리
    pg.wait_for_timeout(120)


def case_normal(pg, sc):
    drag(pg, sc)
    a = pg.evaluate(JS_SEL)
    wander(pg, sc)
    b = pg.evaluate(JS_SEL)
    return a, b


def case_lost_up(pg, sc):
    drag(pg, sc, lose_up=True)
    a = pg.evaluate(JS_SEL)
    wander(pg, sc)
    b = pg.evaluate(JS_SEL)
    return a, b


def case_lost_up_then_blur(pg, sc):
    drag(pg, sc, lose_up=True)
    pg.evaluate("() => window.dispatchEvent(new FocusEvent('blur'))")
    a = pg.evaluate(JS_SEL)
    # blur 뒤 움직임은 buttons 검사에 걸리지 않게(단추 정보가 없는 합성 이동) — blur 만으로 끝났는지 본다.
    pg.evaluate("""() => { const s = document.querySelector('.xterm-screen').getBoundingClientRect();
      for (let i = 0; i < 6; i++) document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: s.left + 300, clientY: s.top + 300 + i * 20, buttons: 1 })); }""")
    pg.wait_for_timeout(150)
    b = pg.evaluate(JS_SEL)
    return a, b


def case_reparent(pg, sc):
    def reparent():
        pg.evaluate("() => { const h = document.getElementById('host'); const t = document.getElementById('t'); h.removeChild(t); h.appendChild(t); }")
    drag(pg, sc, before_up=reparent)
    a = pg.evaluate(JS_SEL)
    wander(pg, sc)
    b = pg.evaluate(JS_SEL)
    return a, b


def case_wheel(pg, sc):
    drag(pg, sc, before_up=lambda: pg.mouse.wheel(0, 0.0001))
    a = pg.evaluate(JS_SEL)
    wander(pg, sc)
    b = pg.evaluate(JS_SEL)
    return a, b


def regress(pg, sc, kind):
    """일반 기능: 끌기 선택 텍스트 · 더블클릭 단어 선택. 텍스트는 대조군만 공개 API 로 읽는다(앱은 사각형 판정)."""
    drag(pg, sc)
    sel = pg.evaluate(JS_SEL)
    ok_drag = bool(sel) and sel["bottom"] - sel["top"] >= sc["rowH"] * 5
    txt = pg.evaluate(JS_COPY)
    reset(pg, sc)
    x, y = cell(sc, 9, 5)  # 'alpha' 위
    pg.mouse.dblclick(x, y)
    pg.wait_for_timeout(150)
    w = pg.evaluate(JS_SEL)
    wtxt = pg.evaluate("() => window.__term ? window.__term.getSelection() : null") if kind == "control" else None
    ok_word = bool(w) and w["n"] >= 1 and (w["bottom"] - w["top"]) <= sc["rowH"] * 1.5
    reset(pg, sc)
    return ok_drag, ok_word, txt, wtxt


def grew(a, b):
    return bool(a) and bool(b) and b["bottom"] > a["bottom"] + 4


def run(browser, label, kind, port, expect_bug):
    errs: list[str] = []
    ctx, pg = open_target(browser, kind, port, errs)
    try:
        sc = pg.evaluate(JS_SCREEN)
        print(f"\n== {label} · {kind}")
        a, b = case_normal(pg, sc)
        check(bool(a) and not grew(a, b), f"{label}/{kind} A 정상 뗌 → 뗀 뒤 이동에 선택 불변 ({a} → {b})")
        reset(pg, sc)
        a, b = case_lost_up(pg, sc)
        if kind == "control":
            # 대조군은 수리가 없다 — 같은 판 xterm 이 뗌 유실에서 잔류함을 증명하는 칸(기제의 관측).
            check(grew(a, b), f"{label}/{kind} B 뗌 유실 → 순수 xterm 은 커서를 따라 선택이 늘어남(기제 재현) ({a} → {b})")
        elif expect_bug:
            check(grew(a, b), f"{label}/{kind} B 뗌 유실 → 수리 전 앱 = 잔류 재현(뮤테이션 적색 확인) ({a} → {b})")
        else:
            check(bool(a) and not grew(a, b), f"{label}/{kind} B 뗌 유실 → 수리된 앱은 선택 불변 ({a} → {b})")
            txt = pg.evaluate(JS_COPY) or ""
            check("03 alpha" in txt[:16] and "line08" in txt and "line09" not in txt,
                  f"{label}/{kind} B 뗌 유실 뒤 복사 = 뗀 자리까지(line03~line08) ({txt[:12]!r}…{txt[-24:]!r})")
        reset(pg, sc)
        if kind == "app" and not expect_bug:
            a, b = case_lost_up_then_blur(pg, sc)
            check(bool(a) and not grew(a, b), f"{label}/{kind} E 뗌 유실 후 창 blur → 끄기 종료 ({a} → {b})")
            reset(pg, sc)
        if kind == "control":
            a, b = case_reparent(pg, sc)
            check(bool(a) and not grew(a, b), f"{label}/{kind} C 끄는 중 요소 재배치 + 정상 뗌 → 잔류 없음(후보② 기각 근거) ({a} → {b})")
            reset(pg, sc)
        a, b = case_wheel(pg, sc)
        check(bool(a) and not grew(a, b), f"{label}/{kind} D 끄는 중 휠 + 정상 뗌 → 잔류 없음(후보③ 기각 근거) ({a} → {b})")
        reset(pg, sc)
        ok_drag, ok_word, txt, wtxt = regress(pg, sc, kind)
        check(ok_drag, f"{label}/{kind} F 끌기 선택 그려짐(6행)")
        check(bool(txt) and "03 alpha" in txt[:16] and "line08" in txt and "line09" not in txt,
              f"{label}/{kind} F 복사 = 끈 범위(line03~line08) ({(txt or '')[:12]!r}…{(txt or '')[-24:]!r})")
        check(ok_word, f"{label}/{kind} F 더블클릭 단어 선택(1행)" + (f" · {wtxt!r}" if wtxt is not None else ""))
        if kind == "control":
            check(wtxt == "alpha", f"{label}/{kind} F 더블클릭 단어 = 'alpha' ({wtxt!r})")
        check(not errs, f"{label}/{kind} pageerror 0건 ({errs[:2]})")
    finally:
        ctx.close()


def main() -> int:
    from playwright.sync_api import sync_playwright

    expect_bug = "--expect-bug" in sys.argv
    if not (DIST / "main.js").exists() or not (XTERM / "lib" / "xterm.js").exists():
        print("사전 준비 필요: sh ui/build.sh")
        return 2
    ctl = Path(tempfile.mkdtemp(prefix="seldrag-ctl-"))
    shutil.copy(XTERM / "lib" / "xterm.js", ctl / "xterm.js")
    shutil.copy(XTERM / "css" / "xterm.css", ctl / "xterm.css")
    (ctl / "control.html").write_text(CONTROL_HTML, encoding="utf-8")
    h1, p_ctl = serve(ctl)
    h2, p_app = serve(DIST)
    try:
        with sync_playwright() as pw:
            for label, launcher in (("webkit", pw.webkit), ("chromium", pw.chromium)):
                browser = launcher.launch()
                try:
                    run(browser, label, "control", p_ctl, expect_bug)
                    run(browser, label, "app", p_app, expect_bug)
                finally:
                    browser.close()
    finally:
        h1.shutdown()
        h2.shutdown()
        shutil.rmtree(ctl, ignore_errors=True)
    print(f"\n{'PASS' if not failures else 'FAIL'} — 실패 {len(failures)}건")
    for f in failures:
        print("  -", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
