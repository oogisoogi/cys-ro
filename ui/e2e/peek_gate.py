#!/usr/bin/env python3
"""워커 창 보기 게이트 — TICKET=cysr-1119-s12 · DESIGN §4-3 CV-PEEK 고침판 합격 ①~⑥ (수동 실행 — CI 배선은 통합 때 master).

실제 번들 + __TAURI__ 대역(tickrec_gate SHIM + chat_gate CHAT_SHIM + rail_gate RAIL_SHIM) + 가짜 시계 · IPC 계수(window.__INVOKES).
대역 좌석: 마스터 1 · 「행사 안내 페이지」 도우미 2(좌석 2·3) · 「글 쓰기」 1(좌석 4).

A 런타임 없던 좌석(대화 화면으로 시작)
  ① 카드 누름 → 보기 칸에 그 좌석 터미널 · xterm +1 · 처음 크기 = 120×35(대역 PTY 크기가 기본값과 같아 「PTY 크기를 따름」 은 못 가름 — peekpane.test ④ 97×41 이 잰다) · 그 동안 resize_surface 0 · 머리줄 요소 0 → 닫으면 원래 수(해제)
  ② K-2 여섯 길(Shift+Enter keydown · 한글 입력 사건(크롬 UA 라 WKWebView 한글 우회 배선은 이 장면에 없음) · 보기 칸 위 끌어 놓기 · 보기 칸 머리줄 = 0 · ⌘W·⌘D·⌘T·⌘+ · 보기 칸 xterm 포커스) →
     send_input·close_surface·rename_surface·create_surface 0 · 막은 계수 = 단축키 4(send·inject 계수는 단언 밖 — 그 행동은 peekpane.test ② · (1.1.20 #46 · S12 L4) 이름을 단언에 맞춤)
  ④ 해제 지점: Esc · 닫기 단추 · 좌석 사라짐(파기) · 대화 화면 떠남 → 표지 0 · 열린 칸 0
  ⑥ 1024·1280·1371·1410·1411·1600 — 대화 칸 폭 ≥ 600px(덮개 모드 포함) · >1410 = 오른쪽 칸 · ≤1410 = 덮개(master#048a4917)
  펼침: 도우미 2명 카드 = 이름 목록(다시 그리기에도 유지) → 고름
B 런타임 있던 좌석(작업 화면으로 시작 → 대화 화면)
  ① xterm 수 그대로 · 닫은 뒤에도 그대로
  ③ K-3: 열기 → 창 1600 ↔ 1024 → 원래 폭 → 닫기 → 작업 화면 → render 까지 그 좌석 resize_surface 0 · fontSize·열·행 = 열기 전 값
  ④ 작업 화면에서 그 좌석 키 입력 → send_input 1(되살아남)
  ⑤ 「작업 화면에서 크게」 → 작업 화면 · 그 좌석 포커스 + 좌석 줄 선택 표시
C 윈 휠 번역(Windows UA · 대체 화면 + 1003) — 대조: 작업 화면 휠 = send_input 1 · 보기 칸 휠 = 0 · 막은 계수 +1
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/peek_gate.py
"""
import base64
import http.server
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tickrec_gate import BASE, CWD, SHIM, seat  # noqa: E402
from chat_gate import CHAT_SHIM, T0  # noqa: E402
from rail_gate import RAIL_SHIM  # noqa: E402

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"
OUT = Path(os.environ.get("PEEK_SHOTS", "/tmp/peek-gate-shots"))

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


COUNT = "(cmd) => window.__INVOKES.filter((x) => x[1] === cmd).length"
SIDS = "(cmd) => window.__INVOKES.filter((x) => x[1] === cmd).map((x) => JSON.parse(x[2]).surfaceId)"
STATE = r"""() => { const p = window.__cysPeek; const box = document.querySelector('.cv-peek');
  return { open: p.open(), info: p.info(), flags: p.flags(), stats: JSON.parse(JSON.stringify(p.stats)),
    shown: !!box && !box.hidden && getComputedStyle(box).display !== 'none', xterm: document.querySelectorAll('.xterm').length,
    inPeek: !!document.querySelector('.cv-peek-host .xterm'), heads: document.querySelectorAll('.cv-peek .pane-title, .cv-peek .pane-close').length,
    name: document.querySelector('.cv-peek-name')?.textContent ?? null }; }"""
WRITES = ["send_input", "close_surface", "rename_surface", "create_surface"]
# 좌석 PTY 크기 대역 — resize_surface 가 바꾼 크기를 surface.list size 로 돌려준다(실제 데몬과 같은 꼴 · 없으면 948 D5 의 「목록 크기 ≠ 기억」 이 대역 탓으로 매번 다시 맞춤)
SIZE_SHIM = r"""
(() => {
  const prev = window.__TAURI__.core.invoke;
  const sizes = {};
  window.__TAURI__.core.invoke = (cmd, args) => {
    const a = args ?? {};
    if (cmd === 'resize_surface') sizes[a.surfaceId] = { rows: a.rows, cols: a.cols };
    if (cmd === 'attach_surface' && (window.__ATTACH_FAIL ?? 0) > 0) { window.__ATTACH_FAIL--; window.__INVOKES.push([Date.now(), 'attach_fail', JSON.stringify(a)]); return Promise.reject(new Error('sim attach fail')); }
    if (cmd === 'start_surface_stream' && window.__HOLD_START && (window.__HOLD_START === true || window.__HOLD_START === a.surfaceId)) { window.__INVOKES.push([Date.now(), cmd, JSON.stringify(a)]); return new Promise((res) => (window.__RELEASE_START = res)).then(() => ({ stream_gen: 7, history: { status: 'ok', rows: 0 } })); }
    if (cmd === 'list_dir') { const go = () => [{ name: 'report.md', is_dir: false }]; return window.__HOLD_LISTDIR ? new Promise((res) => (window.__RELEASE_LISTDIR = () => res(go()))) : Promise.resolve(go()); }
    if (cmd === 'list_surfaces' && window.__PEEK_HOLD) return new Promise((res) => (window.__PEEK_RELEASE = res)).then(() => prev(cmd, args)).then((r) => ({ ...r, surfaces: (r.surfaces || []).map((x) => sizes[x.surface_id] ? { ...x, size: sizes[x.surface_id] } : x) }));
    if (cmd === 'list_surfaces') return prev(cmd, args).then((r) => ({ ...r, surfaces: (r.surfaces || []).map((x) => sizes[x.surface_id] ? { ...x, size: sizes[x.surface_id] } : x) }));
    return prev(cmd, args);
  };
})();
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
    rail_shim = RAIL_SHIM.replace("__BASE__", BASE)
    site = CWD.rsplit("/", 1)[0] + "/site"
    print("번들:", DIST)
    with sync_playwright() as p:
        exe = os.environ.get("CHROME_PATH")
        br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

        def page(view: str, width: int = 1280, height: int = 800, ua: "str | None" = None):
            ctx = br.new_context(viewport={"width": width, "height": height}, **({"user_agent": ua} if ua else {}))
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.add_init_script(rail_shim)
            pg.add_init_script(SIZE_SHIM)
            if view == "chat":
                pg.add_init_script("localStorage.setItem('cys-view', JSON.stringify({ v: 1, id: 'chat', decidedBy: 'user' }))")
            pg.goto(url)
            pg.clock.run_for(9_000)
            seats = [json.loads(seat(BASE, 1, "master"))]
            for sid, task in ((2, "행사 안내 페이지"), (3, "행사 안내 페이지"), (4, "글 쓰기")):
                s = json.loads(seat(BASE, sid, f"worker-{sid}", site))
                s["task"] = task
                seats.append(s)
            pg.evaluate(f"() => {{ window.__SEATS.push(...{json.dumps(seats)}); }}")
            pg.clock.run_for(9_000)
            if view == "work":
                pg.clock.run_for(3_000)
                pg.click("#view-switch button[data-view=chat]")
            pg.clock.run_for(3_300)
            return ctx, pg, errs

        n = lambda pg, cmd: pg.evaluate(COUNT, cmd)  # noqa: E731
        st = lambda pg: pg.evaluate(STATE)  # noqa: E731
        writes = lambda pg: {c: n(pg, c) for c in WRITES}  # noqa: E731

        def open_single(pg) -> None:
            pg.click('.cvr-card[data-task="글 쓰기"]')
            for _ in range(20):
                pg.clock.run_for(50)

        # ── A. 런타임 없던 좌석 ─────────────────────────────────────────────
        print("== A. 대화 화면으로 시작(런타임 없음)")
        ctx, pg, errs = page("chat")
        s0 = st(pg)
        r0, ss0 = n(pg, "resize_surface"), n(pg, "start_surface_stream")
        check(s0["open"] is None and s0["xterm"] == 0 and ss0 == 0, f"시작 = 보기 칸 0 · xterm 0 · 흐름 0 ({s0['xterm']} · {ss0})")
        a11y = pg.evaluate("() => [...document.querySelectorAll('.cvr-peekable')].map((c) => [c.getAttribute('role'), c.getAttribute('aria-label'), c.tabIndex])")
        labs = [lab for _, lab, _ in a11y]
        check("글 쓰기 창 보기" in labs and "행사 안내 페이지 — 도우미 2명 창 고르기" in labs and all(r == "button" and lab and t == 0 for r, lab, t in a11y), f"누를 카드(도우미 있는 카드 전부) · 접근성 이름 {a11y}")
        open_single(pg)
        s1 = st(pg)
        check(s1["shown"] and s1["inPeek"] and s1["open"] == 4 and s1["xterm"] == 1, f"① 카드 누름 → 보기 칸에 좌석 4 터미널 · xterm +1 {s1['open']} {s1['xterm']} {s1['shown']}")
        check(s1["info"] and s1["info"]["cols"] == 120 and s1["info"]["rows"] == 35 and s1["info"]["made"], f"① 처음 크기 = 120×35 · 보기 칸이 만든 런타임 {s1['info']}")
        check(n(pg, "resize_surface") == r0, f"① 만드는 동안 resize_surface 0 ({n(pg, 'resize_surface') - r0})")
        check(s1["heads"] == 0, f"② 보기 칸 안 머리줄·닫기(×) 요소 = 0 ({s1['heads']})")
        check(s1["name"] == "글 쓰기" and "4" not in (s1["name"] or ""), f"이름표 = 좌석 이름(번호 0) {s1['name']!r}")
        pg.screenshot(path=str(OUT / "a-1280-open.png"))

        # ② K-2 여섯 길
        w0 = writes(pg)
        d0 = dict(s1["stats"]["drops"])
        pg.evaluate("""() => { const ta = document.querySelector('.cv-peek-host .xterm-helper-textarea');
          ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, shiftKey: true, bubbles: true, cancelable: true }));
          ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'a', code: 'KeyA', keyCode: 65, bubbles: true, cancelable: true }));
          ta.dispatchEvent(new InputEvent('input', { inputType: 'insertText', data: '가', bubbles: true }));
          ta.dispatchEvent(new CompositionEvent('compositionend', { data: '가', bubbles: true }));
          ta.dispatchEvent(new FocusEvent('blur'));
          ta.focus(); }""")
        pg.clock.run_for(300)
        foc = pg.evaluate("() => ({ ta: document.activeElement?.classList?.contains('xterm-helper-textarea') ?? false, inPeek: !!document.activeElement?.closest?.('.cv-peek-host'), tab: document.querySelector('.cv-peek-host .xterm-helper-textarea')?.getAttribute('tabindex') })")
        check(foc["tab"] == "-1", f"② 보기 칸 xterm 글칸 tabindex = -1 ({foc})")
        box = pg.evaluate("() => { const r = document.querySelector('.cv-peek-body').getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; }")
        pg.evaluate(f"() => window.__emit('tauri://drag-drop', {{ paths: ['/sandbox/a.txt'], position: {{ x: {box['x']}, y: {box['y']} }} }})")
        pg.clock.run_for(500)
        for k in ("Meta+w", "Meta+d", "Meta+t", "Meta+Equal"):
            pg.keyboard.press(k)
            pg.clock.run_for(200)
        w1 = writes(pg)
        s2 = st(pg)
        check(w1 == w0, f"② 여섯 길 → send_input·close·rename·create 0 ({ {k: w1[k] - w0[k] for k in WRITES} })")
        dd = {k: s2["stats"]["drops"].get(k, 0) - d0.get(k, 0) for k in ("send", "shortcut", "inject")}
        check(dd["shortcut"] == 4, f"② 막은 계수 단축키 = 4 ({dd})")
        check(s2["open"] == 4 and s2["flags"] == 1, f"② 단축키·끌어 놓기 뒤에도 보기 칸 그대로 · 표지 1 ({s2['open']} · {s2['flags']})")

        # ⑥ 폭
        for (wd, ht) in ((1024, 700), (1280, 800), (1371, 800), (1410, 800), (1411, 800), (1600, 900)):  # (master#048a4917) 문턱 1410 · 박사님 노트북 1371 · 윈 1366 근처
            pg.set_viewport_size({"width": wd, "height": ht})
            pg.clock.run_for(300)
            g = pg.evaluate("() => { const c = document.querySelector('.cv').getBoundingClientRect(); const p = document.querySelector('.cv-peek'); const pr = p.getBoundingClientRect(); return { cv: Math.round(c.width), peek: Math.round(pr.width), pos: getComputedStyle(p).position, k: window.__cysPeek.info()?.k }; }")
            mode_ok = (g["pos"] == "absolute") if wd <= 1410 else (g["pos"] != "absolute")
            check(g["cv"] >= 600 and mode_ok, f"⑥ {wd}×{ht} 대화 칸 {g['cv']} ≥ 600 · 보기 칸 {g['peek']} · {'덮개' if wd <= 1410 else '오른쪽 칸'}({g['pos']}) · k {g['k']}")
            pg.screenshot(path=str(OUT / f"a-{wd}.png"))
        pg.set_viewport_size({"width": 1280, "height": 800})
        pg.clock.run_for(300)
        check(n(pg, "resize_surface") == r0, f"③ 창 폭 세 번 바꿔도 resize_surface 0 ({n(pg, 'resize_surface') - r0})")

        # ④ 닫기 지점 — Esc · 닫기 단추 · 좌석 사라짐 · 화면 떠남
        pg.keyboard.press("Escape")
        pg.clock.run_for(200)
        s3 = st(pg)
        check(s3["open"] is None and not s3["shown"] and s3["flags"] == 0 and s3["xterm"] == 0, f"④ Esc → 닫힘 · 표지 0 · 만든 런타임 해제(xterm {s3['xterm']})")
        check(n(pg, "stop_surface_stream") >= 1, f"④ 닫으면 흐름 멈춤(stop_surface_stream {n(pg, 'stop_surface_stream')})")
        open_single(pg)
        pg.click(".cv-peek-close")
        pg.clock.run_for(200)
        s4 = st(pg)
        check(s4["open"] is None and s4["flags"] == 0 and s4["xterm"] == 0, f"④ 닫기 단추 → 닫힘 · 표지 0 ({s4['xterm']})")
        # 펼침: 도우미 2명 카드 → 이름 목록(다시 그리기에도 유지) → 고름
        pg.click('.cvr-card[data-task="행사 안내 페이지"]')
        pg.clock.run_for(3_300)  # 3초 다시 그리기 한 바퀴
        picks = pg.evaluate("() => [...document.querySelectorAll('.cvr-peek-pick')].map((b) => [b.textContent, b.getAttribute('aria-label')])")
        check(len(picks) == 2 and picks[0][0].startswith("도우미 1 · ") and picks[1][0].startswith("도우미 2 · "), f"펼침 = 이름 목록 2(다시 그리기 뒤에도) {picks}")
        pg.click(".cvr-peek-pick >> nth=1")
        for _ in range(20):
            pg.clock.run_for(50)
        s5 = st(pg)
        check(s5["open"] == 3 and s5["name"].startswith("도우미 2"), f"이름 고름 → 좌석 3 보기 칸 {s5['open']} {s5['name']!r}")
        # 경합(㉯ 고침 2): 좌석 4 열기가 목록 조회에서 멈춘 사이 좌석 2 를 고름 → 나중 누름이 이김 · 이름 = 터미널 · 좌석 4 런타임 남음 0
        pg.keyboard.press("Escape")
        pg.clock.run_for(200)
        pg.evaluate("() => { window.__PEEK_HOLD = true; }")
        pg.click('.cvr-card[data-task="글 쓰기"]')
        pg.clock.run_for(50)
        pg.click(".cvr-peek-pick >> nth=0")
        pg.clock.run_for(50)
        pg.evaluate("() => { window.__PEEK_HOLD = false; window.__PEEK_RELEASE?.(); }")
        for _ in range(40):
            pg.clock.run_for(50)
        sr = st(pg)
        made4 = pg.evaluate("() => window.__INVOKES.filter((x) => x[1] === 'start_surface_stream' && JSON.parse(x[2]).surfaceId === 4).length - window.__INVOKES.filter((x) => x[1] === 'stop_surface_stream' && JSON.parse(x[2]).surfaceId === 4).length")
        check(sr["open"] == 2 and (sr["name"] or "").startswith("도우미 1") and sr["xterm"] == 1 and made4 == 0, f"경합: 나중 누름(좌석 2) 이김 · 이름 {sr['name']!r} · xterm {sr['xterm']} · 좌석 4 열린 흐름 {made4}")
        # 좌석 사라짐(파기) → 닫힘
        pg.evaluate("() => { const i = window.__SEATS.findIndex((s) => s.sid === 2); window.__SEATS.splice(i, 1); }")  # 지금 보기 칸 좌석(경합 단계 뒤 = 2)
        pg.clock.run_for(9_000)
        s6 = st(pg)
        check(s6["open"] is None and s6["flags"] == 0, f"④ 좌석 사라짐 → 닫힘 · 표지 0 (닫은 까닭 {s6['stats']['closes']})")
        open_single(pg)
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(3_000)
        s7 = st(pg)
        check(s7["open"] is None and s7["flags"] == 0, f"④ 대화 화면 떠남 → 닫힘 · 표지 0 (까닭 {s7['stats']['closes']})")
        xt = pg.evaluate("() => ({ panes: document.querySelectorAll('#root .pane').length, xterm: document.querySelectorAll('#root .pane .xterm').length, missing: (document.getElementById('root').innerText.match(/\\(없음\\)/g) || []).length })")
        check(xt["xterm"] == xt["panes"] and xt["missing"] == 0, f"④ 작업 화면 = 좌석 xterm 전부 · 「(없음)」 0 {xt}")
        check(not errs, f"A 페이지 오류 0 {errs[:2]}")
        ctx.close()

        # ── B. 런타임 있던 좌석 ─────────────────────────────────────────────
        print("== B. 작업 화면으로 시작 → 대화 화면(런타임 있음)")
        ctx, pg, errs = page("work")
        x0 = st(pg)["xterm"]
        r0 = pg.evaluate(SIDS, "resize_surface").count(4)
        open_single(pg)
        b1 = st(pg)
        before = b1["info"]
        check(b1["open"] == 4 and b1["xterm"] == x0 and not before["made"], f"① 런타임 있던 좌석 = xterm 수 그대로({b1['xterm']} = {x0}) · 새 런타임 0")
        FOC = "() => document.querySelector('#root .pane.focused')?.dataset.sid ?? null"
        f0 = pg.evaluate(FOC)
        pg.evaluate("() => { const ta = document.querySelector('.cv-peek-host .xterm-helper-textarea'); ta.focus(); ta.dispatchEvent(new FocusEvent('focus')); }")
        pg.clock.run_for(200)
        f1 = pg.evaluate(FOC)
        check(f0 != "4" and f1 == f0, f"② 보기 칸 글칸 포커스 → 좌석 포커스 옮김 0(setFocus 첫 줄 · 포커스 좌석 {f0} → {f1})")
        for wd in (1600, 1024, 1600, 1280):
            pg.set_viewport_size({"width": wd, "height": 800})
            pg.clock.run_for(300)
            i = st(pg)["info"]
            check(i["fontSize"] == before["fontSize"] and i["cols"] == before["cols"] and i["rows"] == before["rows"], f"③ 창 {wd} — fontSize {i['fontSize']} · 열 {i['cols']} · 행 {i['rows']} = 열기 전 · k {i['k']}")
        pg.screenshot(path=str(OUT / "b-1280-open.png"))
        rp = pg.evaluate(SIDS, "resize_surface")
        check(rp.count(4) == r0, f"③ 열기 → 창 1600↔1024 → 원래 폭(보기 칸 동안) 좌석 4 resize_surface 0 ({rp.count(4) - r0})")
        pg.keyboard.press("Escape")
        pg.clock.run_for(200)
        rc = pg.evaluate(SIDS, "resize_surface")
        check(rc.count(4) == r0, f"③ 닫기 직후 좌석 4 resize_surface 0 ({rc.count(4) - r0})")
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(3_000)
        rw = pg.evaluate(SIDS, "resize_surface")[len(rc):]
        # 작업 화면 복귀 render 는 보기 칸과 무관하게 모든 좌석을 다시 맞춘다(1.1.18 꼴 · 대조 실측 = 보기 칸 없이 같은 순서에서도 좌석마다 1~2회 · HANDOFF §5) →
        #   판정 = 본 좌석 4 가 안 본 좌석 2 보다 더 받지 않는다(보기 칸이 더한 크기 변경 0)
        check(rw.count(4) <= rw.count(2), f"③ 작업 화면 복귀 render — 좌석 4 resize {rw.count(4)} ≤ 안 본 좌석 2 {rw.count(2)}(보기 칸이 더한 것 0)")
        check(rw.count(4) <= 2, f"③ (고침2 ④) 복귀 render 좌석 4 resize 절대 {rw.count(4)} ≤ 2(기준판 대조 = 좌석마다 1~2회 · 보기 칸이 한 번 더 맞추면 붉음)")
        # (검증 M4) 절대값도 기록 · 복귀 뒤 마지막으로 보낸 열·행 = 열기 전 열·행(엉뚱한 크기로 맞춰지면 붉음)
        #   ★「열기 전 크기」 와 같음은 기준이 아니다 — 복귀 render 가 배치를 네 칸 같은 폭으로 다시 짜서 보기 칸 없이도 20 → 31열(대조 실측 · HANDOFF 고침1 M4)
        lastof = lambda sid: (lambda xs: (xs[-1]["cols"], xs[-1]["rows"]) if xs else None)([json.loads(x) for x in pg.evaluate(f"() => window.__INVOKES.filter((x) => x[1] === 'resize_surface' && JSON.parse(x[2]).surfaceId === {sid}).map((x) => x[2])")])  # noqa: E731
        w42 = pg.evaluate("() => [4, 2].map((s) => Math.round(document.querySelector(`#root .pane[data-sid=\"${s}\"] .term-host`).getBoundingClientRect().width))")
        check(abs(w42[0] - w42[1]) < 7 and lastof(4) == lastof(2),  # 폭 차 < 한 글자 칸(≈7.8px)
              f"③ (M4) 복귀 때 좌석 4 resize 절대 {rw.count(4)}회 · 안 본 좌석 2 {rw.count(2)}회 · 마지막 크기 좌석 4 {lastof(4)} = 같은 폭({w42}) 좌석 2 {lastof(2)}")
        check(st(pg)["xterm"] == x0, f"① 닫은 뒤 xterm 수 그대로 ({st(pg)['xterm']} = {x0})")
        # ④ 되살아남 — 작업 화면에서 그 좌석에 키 입력
        s_in = n(pg, "send_input")
        pg.click('#root .pane[data-sid="4"] .term-host')
        pg.keyboard.type("z")
        pg.clock.run_for(300)
        check(n(pg, "send_input") == s_in + 1, f"④ 작업 화면 좌석 4 키 입력 → send_input 1 ({n(pg, 'send_input') - s_in})")
        # ⑤ 「작업 화면에서 크게」 — 먼저 좌석 2 에 포커스를 두고 대화 화면으로
        pg.click('#root .pane[data-sid="2"] .term-host')
        pg.clock.run_for(200)
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_300)
        open_single(pg)
        pg.click(".cv-peek-big")
        pg.clock.run_for(3_000)
        sel = pg.evaluate("() => ({ view: document.getElementById('body-row').style.display !== 'none', focused: document.querySelector('#root .pane.focused')?.dataset.sid ?? null, row: document.querySelector('.ws-seat.sel')?.dataset?.sid ?? document.querySelector('.ws-seat.sel')?.getAttribute('data-sid') ?? null, rowText: document.querySelector('.ws-seat.sel')?.textContent ?? null, open: window.__cysPeek.open() })")
        check(sel["view"] and sel["focused"] == "4" and sel["open"] is None, f"⑤ 크게 → 작업 화면 · 좌석 4 포커스(창 머리) · 보기 칸 닫힘 {sel}")
        check(sel["rowText"] is not None, f"⑤ 좌석 줄 선택 표시(.ws-seat.sel) {sel['rowText']!r}")
        check(not errs, f"B 페이지 오류 0 {errs[:2]}")
        ctx.close()

        # ── D. 검증 고침 1(master#d470f594) — B1 · H1 · M1 · M2 · M3 ─────────────────
        print("== D. 실패·취소·경합·Esc·경로 넣기 순서")
        ctx, pg, errs = page("chat")
        streams4 = "() => window.__INVOKES.filter((x) => x[1] === 'start_surface_stream' && JSON.parse(x[2]).surfaceId === 4).length - window.__INVOKES.filter((x) => x[1] === 'stop_surface_stream' && JSON.parse(x[2]).surfaceId === 4).length"
        # B1: 열기 실패 1회 → 안내 → 「작업 화면에서 보기」 → 그 좌석 런타임은 표지 없음 · 키 → send_input 1
        pg.evaluate("() => { window.__ATTACH_FAIL = 1; }")
        open_single(pg)
        note = pg.evaluate("() => { const n = document.querySelector('.cv-peek-note'); return n && !n.hidden ? n.textContent : null; }")
        check(note is not None and pg.evaluate(COUNT, "attach_fail") == 1, f"B1 열기 실패 1회 → 안내 {note!r}")
        pg.click(".cv-peek-note .cv-peek-btn")
        pg.clock.run_for(6_000)
        fl = st(pg)["flags"]
        s0 = n(pg, "send_input")
        pg.click('#root .pane[data-sid="4"] .term-host')
        pg.keyboard.type("k")
        pg.clock.run_for(300)
        tab = pg.evaluate("() => document.querySelector('#root .pane[data-sid=\"4\"] .xterm-helper-textarea')?.getAttribute('tabindex')")
        check(fl == 0 and n(pg, "send_input") == s0 + 1 and tab != "-1", f"B1 작업 화면 좌석 4 = 표지 0({fl}) · 키 → send_input {n(pg, 'send_input') - s0}(기대 1) · tabindex {tab!r}")
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_300)
        ctx.close()
        ctx, pg, errs = page("chat")
        # H1: 흐름 시작 응답을 붙잡은 채 닫기 → 응답 → 좌석 4 열린 흐름 0
        pg.evaluate("() => { window.__HOLD_START = true; }")
        pg.click('.cvr-card[data-task="글 쓰기"]')
        pg.clock.run_for(200)
        pg.click(".cv-peek-close")
        pg.evaluate("() => { window.__HOLD_START = false; window.__RELEASE_START?.(); }")
        for _ in range(20):
            pg.clock.run_for(50)
        check(pg.evaluate(streams4) == 0 and st(pg)["open"] is None and st(pg)["xterm"] == 0, f"H1 만드는 중 닫기 → 좌석 4 열린 흐름 {pg.evaluate(streams4)}(기대 0) · xterm {st(pg)['xterm']}")
        # M1: 만드는 중 Esc → 칸 닫힘 · 응답 뒤에도 안 열림
        pg.evaluate("() => { window.__HOLD_START = true; }")
        pg.click('.cvr-card[data-task="글 쓰기"]')
        pg.clock.run_for(200)
        pg.keyboard.press("Escape")
        shown = st(pg)["shown"]
        pg.evaluate("() => { window.__HOLD_START = false; window.__RELEASE_START?.(); }")
        for _ in range(20):
            pg.clock.run_for(50)
        check(not shown and st(pg)["open"] is None and pg.evaluate(streams4) == 0, f"M1 만드는 중 Esc → 닫힘({shown}) · 응답 뒤 열림 {st(pg)['open']} · 흐름 {pg.evaluate(streams4)}")
        # NEW-2(XB 꼴): 조합 중 Esc(isComposing · keyCode 229) = 칸 그대로
        open_single(pg)
        pg.evaluate("() => { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', isComposing: true, bubbles: true })); document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', keyCode: 229, bubbles: true })); }")
        pg.clock.run_for(100)
        kept = st(pg)["shown"]
        pg.keyboard.press("Escape")
        pg.clock.run_for(100)
        check(kept and not st(pg)["shown"], f"NEW-2 조합 중 Esc 2갈래 → 칸 그대로({kept}) · 보통 Esc → 닫힘({st(pg)['shown']})")
        # M1 ㉡: 안내만 뜬 칸 Esc
        pg.evaluate("() => { window.__ATTACH_FAIL = 1; }")
        open_single(pg)
        pg.keyboard.press("Escape")
        pg.clock.run_for(100)
        check(not st(pg)["shown"], f"M1 안내만 뜬 칸 Esc → 닫힘({st(pg)['shown']})")
        # M2: 앞 열기가 6초 걸려도 나중 누름(좌석 2)이 열림
        pg.evaluate("() => { window.__HOLD_START = true; }")
        pg.click('.cvr-card[data-task="글 쓰기"]')
        pg.clock.run_for(100)
        pg.click('.cvr-card[data-task="행사 안내 페이지"]')
        pg.clock.run_for(100)
        pg.click(".cvr-peek-pick >> nth=0")
        pg.clock.run_for(6_000)
        pg.evaluate("() => { window.__HOLD_START = false; window.__RELEASE_START?.(); }")
        for _ in range(40):
            pg.clock.run_for(50)
        m2 = st(pg)
        check(m2["open"] == 2 and m2["inPeek"] and pg.evaluate(streams4) == 0, f"M2 앞 열기 6초 → 나중 누름 좌석 2 열림({m2['open']}) · 터미널 {m2['inPeek']} · 좌석 4 흐름 {pg.evaluate(streams4)}")
        pg.keyboard.press("Escape")
        pg.clock.run_for(200)
        ctx.close()
        # NEW-1(XA 꼴): 터미널이 붙기 전에 「작업 화면에서 크게」 → 넘김 뒤 좌석 4 포커스 · 친 키 → send_input 1
        ctx, pg, errs = page("chat")
        pg.evaluate("() => { window.__HOLD_START = 4; }")
        pg.click('.cvr-card[data-task="글 쓰기"]')
        pg.clock.run_for(300)
        pg.click(".cv-peek-big")
        pg.clock.run_for(300)
        pg.evaluate("() => { window.__HOLD_START = false; window.__RELEASE_START?.(); }")
        pg.clock.run_for(1_000)
        s0 = n(pg, "send_input")
        pg.keyboard.type("y")
        pg.clock.run_for(300)
        foc = pg.evaluate("() => document.querySelector('#root .pane.focused')?.dataset.sid ?? null")
        check(foc == "4" and n(pg, "send_input") == s0 + 1, f"NEW-1 붙기 전 크게 → 넘김 뒤 포커스 좌석 {foc} · 친 키 send_input {n(pg, 'send_input') - s0}(기대 1)")
        ctx.close()
        # M3: 작업 화면에서 좌석 4 에 끌어 놓기(경로 확인 대기) → 대화 화면 보기 칸 → 확인 끝 → send_input 0 · 안내 토스트
        ctx, pg, errs = page("work")
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(3_000)
        r4 = pg.evaluate("() => { const r = document.querySelector('#root .pane[data-sid=\"4\"]').getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; }")
        pg.evaluate("() => { window.__HOLD_LISTDIR = true; }")
        pg.evaluate(f"() => window.__emit('tauri://drag-drop', {{ paths: ['/sandbox/report.md'], position: {{ x: {r4['x']}, y: {r4['y']} }} }})")
        pg.clock.run_for(100)
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_300)
        open_single(pg)
        s0, d0 = n(pg, "send_input"), st(pg)["stats"]["drops"].get("inject", 0)
        pg.evaluate("() => { window.__HOLD_LISTDIR = false; window.__RELEASE_LISTDIR?.(); }")
        pg.clock.run_for(500)
        toasts = pg.evaluate("() => [...document.querySelectorAll('.toast')].map((t) => t.textContent)")
        check(n(pg, "send_input") == s0 and st(pg)["stats"]["drops"].get("inject", 0) == d0 + 1 and any("삽입 안 함" in t for t in toasts), f"M3 경로 확인 대기 뒤 보기 칸 좌석 → send_input 0 · inject 계수 +1 · 안내 토스트 {[t[:30] for t in toasts]}")
        check(not errs, f"D 페이지 오류 0 {errs[:2]}")
        ctx.close()

        # ── C. 윈 휠 번역(Windows UA) ──────────────────────────────────────
        print("== C. 윈 휠 번역 — 작업 화면(대조) vs 보기 칸")
        ctx, pg, errs = page("work", ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 Edg/130.0")
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(3_000)
        alt = base64.b64encode(b"\x1b[?1049h\x1b[?1000h\x1b[?1003h\x1b[?1006hALT").decode()
        pg.evaluate(f"() => window.__emit('sim-out-4', '{alt}')")
        pg.clock.run_for(300)
        wheel = "() => { const v = document.querySelector('{sel} .xterm'); v.dispatchEvent(new WheelEvent('wheel', { deltaY: -120, deltaMode: 0, bubbles: true, cancelable: true })); }"
        c0 = n(pg, "send_input")
        pg.evaluate(wheel.replace("{sel}", '#root .pane[data-sid="4"]'))
        pg.clock.run_for(300)
        c1 = n(pg, "send_input")
        check(c1 - c0 >= 1, f"C 대조: 작업 화면 대체 화면 휠 → send_input {c1 - c0} ≥ 1(번역 길이 살아 있음)")
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_300)
        open_single(pg)
        d0 = st(pg)["stats"]["drops"].get("send", 0)
        pg.evaluate(wheel.replace("{sel}", ".cv-peek-host"))
        pg.clock.run_for(300)
        c2 = n(pg, "send_input")
        d1 = st(pg)["stats"]["drops"].get("send", 0)
        check(c2 == c1 and d1 - d0 >= 1, f"C 보기 칸 휠 → send_input 0 ({c2 - c1}) · 막은 계수 +{d1 - d0}")
        check(not errs, f"C 페이지 오류 0 {errs[:2]}")
        ctx.close()
        br.close()
    httpd.shutdown()
    print("\nRESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    for f in failures:
        print("  FAIL:", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
