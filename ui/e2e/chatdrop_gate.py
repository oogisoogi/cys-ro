#!/usr/bin/env python3
"""대화 입력칸 끌어 놓기 게이트 — TICKET=cysr-1119-s11 · DESIGN TC3(끌어 놓기만 · 「+」 단추 = 1.1.20) (수동 실행 — CI 배선은 통합 때 master).

실제 번들 + __TAURI__ 대역(tickrec_gate SHIM + chat_gate CHAT_SHIM + rail_gate RAIL_SHIM) + 가짜 시계 · IPC 계수(window.__INVOKES).
받는 자리 = Tauri 전역 `tauri://drag-drop`(window.__emit) — 놓은 점 = 화면 요소 가운데(맥 = 논리 px 그대로).

A 1280×800 대화 화면
  ① 입력칸 카드 위 → 칩 1(이름 = 파일 이름 · title = 경로) · list_dir 1 · send_input 0 · chat_send 0
  ② 같은 파일 다시 → 칩 1(중복 0)
  ③ 「<이름> 빼기」 = 입력칸에서 Shift+Tab 으로 닿음 · Enter → 칩 0 · 포커스 = 입력칸
  ④ 다시 놓고 글 + Enter → chat_send 1 · text = 「글 @경로」(펼친 입력칸 글 바이트) · 보낸 뒤 칩 0
  ⑤ 결과 3종 나머지: 폴더 못 읽음 = 「경로 확인 실패」 · 없음 = 「경로가 더 이상 없음」 · 둘 다 칩 0 · send_input 0
  ⑥ 입력칸 밖(대화 목록) = 칩 0 · list_dir 0 · (1.1.20 #51) 안내 토스트 「여기에는 놓을 수 없어요」(대화 화면 = 런타임 유무와 무관 · 「pane 위」 문구 0)
  ⑥′ (1.1.20 #51) 끄는 동안 입력칸 위 = .cv-form.cv-drop-target(점선 테두리) · 목록 위로 옮김·떠남·놓음 = 꺼짐
  ⑦ 보기 칸(덮개 · ≤1410) 위 = 칩 0 · send_input 0 · chat_send 0 (S12 판정 그대로) · 칩이 든 채 작업 화면 → 대화 화면 = 칩 남음
B 1600×900 보기 칸 = 오른쪽 칸 → 입력칸이 안 가려짐 = 입력칸 위 놓기 = 칩 1 · 보기 칸 위 = 칩 그대로
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/chatdrop_gate.py
"""
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

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


COUNT = "(cmd) => window.__INVOKES.filter((x) => x[1] === cmd).length"
SENT = "() => window.__CHAT.writes.map((w) => w.args.text)"  # chat_send 는 CHAT_SHIM 이 받는다(__INVOKES 밖)
CHATSENDS = "() => window.__CHAT.writes.length"
CHIPS = "() => [...document.querySelectorAll('.cv-chip')].map((c) => [c.querySelector('.cv-chip-name').textContent, c.querySelector('.cv-chip-name').title, c.querySelector('.cv-chip-x').getAttribute('aria-label')])"
TOASTS = "() => [...document.querySelectorAll('#toasts .toast-name')].map((t) => t.textContent)"
CENTER = "(sel) => { const r = document.querySelector(sel).getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; }"
# list_dir 대역 — 모드: ok(파일 있음) · fail(폴더 못 읽음) · missing(폴더는 읽히나 파일 없음)
DIR_SHIM = r"""
(() => {
  const prev = window.__TAURI__.core.invoke;
  window.__LISTDIR = 'ok';
  window.__TAURI__.core.invoke = (cmd, args) => {
    if (cmd === 'list_dir') {
      window.__INVOKES.push([Date.now(), cmd, JSON.stringify(args ?? {})]);
      if (window.__LISTDIR === 'fail') return Promise.reject(new Error('EACCES sim'));
      if (window.__LISTDIR === 'missing') return Promise.resolve([{ name: 'other.md', is_dir: false }]);
      return Promise.resolve([{ name: 'report.md', is_dir: false }, { name: '보고서 초안.md', is_dir: false }]);
    }
    return prev(cmd, args);
  };
})();
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

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

        def page(width: int, height: int):
            ctx = br.new_context(viewport={"width": width, "height": height})
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            for s in (shim, CHAT_SHIM, rail_shim, DIR_SHIM):
                pg.add_init_script(s)
            pg.add_init_script("localStorage.setItem('cys-view', JSON.stringify({ v: 1, id: 'chat', decidedBy: 'user' }))")
            pg.goto(url)
            pg.clock.run_for(9_000)
            seats = [json.loads(seat(BASE, 1, "master"))]
            s4 = json.loads(seat(BASE, 4, "worker-4", site))
            s4["task"] = "글 쓰기"
            seats.append(s4)
            pg.evaluate(f"() => {{ window.__SEATS.push(...{json.dumps(seats)}); }}")
            pg.clock.run_for(12_300)
            return ctx, pg, errs

        n = lambda pg, cmd: pg.evaluate(COUNT, cmd)  # noqa: E731

        def drop(pg, paths: list[str], at: dict) -> None:
            pg.evaluate(f"() => window.__emit('tauri://drag-drop', {{ paths: {json.dumps(paths)}, position: {{ x: {at['x']}, y: {at['y']} }} }})")
            for _ in range(10):
                pg.clock.run_for(50)

        def open_peek(pg) -> None:
            pg.click('.cvr-card[data-task="글 쓰기"]')
            for _ in range(20):
                pg.clock.run_for(50)

        print("== A. 1280×800 대화 화면")
        ctx, pg, errs = page(1280, 800)
        check(pg.evaluate("() => document.body.classList.contains('view-chat') && !!document.querySelector('.cv-form')"), "대화 화면 · 입력칸 카드 있음")
        si0, ld0 = n(pg, "send_input"), n(pg, "list_dir")
        form = pg.evaluate(CENTER, ".cv-form")
        drop(pg, ["/sandbox/report.md"], form)
        chips = pg.evaluate(CHIPS)
        check(chips == [["report.md", "/sandbox/report.md", "report.md 빼기"]], f"① 입력칸 위 → 칩 1 · 이름·경로·빼기 이름 {chips}")
        check(n(pg, "list_dir") - ld0 == 1 and n(pg, "send_input") == si0 and pg.evaluate(CHATSENDS) == 0, f"① list_dir 1 · send_input 0 · chat_send 0 ({n(pg, 'list_dir') - ld0} · {n(pg, 'send_input') - si0} · {pg.evaluate(CHATSENDS)})")
        check(not pg.evaluate("() => document.querySelector('.cv-send').disabled"), "① 칩만 있어도 보내기 단추 켜짐")
        drop(pg, ["/sandbox/report.md"], form)
        check(len(pg.evaluate(CHIPS)) == 1, f"② 같은 파일 다시 → 칩 1(중복 0) {len(pg.evaluate(CHIPS))}")
        pg.focus(".cv-input")
        pg.keyboard.press("Shift+Tab")
        lab = pg.evaluate("() => document.activeElement?.getAttribute('aria-label')")
        check(lab == "report.md 빼기", f"③ 입력칸에서 Shift+Tab → 「report.md 빼기」 단추 ({lab!r})")
        pg.keyboard.press("Enter")
        pg.clock.run_for(100)
        check(pg.evaluate(CHIPS) == [] and pg.evaluate("() => document.querySelector('.cv-chips').hidden"), "③ Enter → 칩 0 · 칩 줄 숨김")
        check(pg.evaluate("() => document.activeElement?.classList.contains('cv-input')"), "③ 뺀 뒤 포커스 = 입력칸")
        drop(pg, ["/sandbox/report.md", "/sandbox/보고서 초안.md"], form)
        pg.fill(".cv-input", "이 두 파일 봐 줘")
        pg.press(".cv-input", "Enter")
        for _ in range(20):
            pg.clock.run_for(100)
        sent = pg.evaluate(SENT)
        check(sent == ["이 두 파일 봐 줘 @/sandbox/report.md '/sandbox/보고서 초안.md'"], f"④ chat_send 1 · 보낸 글 = 펼친 입력칸 글 {sent}")
        check(pg.evaluate(CHIPS) == [] and n(pg, "send_input") == si0, f"④ 보낸 뒤 칩 0 · send_input 0 ({n(pg, 'send_input') - si0})")
        for mode, want in (("fail", "경로 확인 실패"), ("missing", "경로가 더 이상 없음")):
            pg.evaluate(f"() => {{ window.__LISTDIR = '{mode}'; }}")
            t0 = len(pg.evaluate(TOASTS))
            drop(pg, ["/sandbox/report.md"], form)
            ts = pg.evaluate(TOASTS)[t0:]
            check(want in ts and pg.evaluate(CHIPS) == [] and n(pg, "send_input") == si0, f"⑤ {mode} → 토스트 「{want}」 · 칩 0 · send_input 0 {ts}")
        pg.evaluate("() => { window.__LISTDIR = 'ok'; }")
        ld1 = n(pg, "list_dir")
        t0 = len(pg.evaluate(TOASTS))
        drop(pg, ["/sandbox/report.md"], pg.evaluate(CENTER, ".cv-log"))
        ts6 = pg.evaluate(TOASTS)[t0:]
        check(pg.evaluate(CHIPS) == [] and n(pg, "list_dir") == ld1 and n(pg, "send_input") == si0, f"⑥ 입력칸 밖(대화 목록) → 칩 0 · list_dir 0 · send_input 0 ({n(pg, 'list_dir') - ld1})")
        check(ts6 == ["여기에는 놓을 수 없어요"], f"⑥ (#51) 입력칸 밖 → 안내 1 · 「드롭 취소」 0 {ts6}")
        # ⑥′ (1.1.20 #51) 끄는 동안 강조
        HL = "() => [...document.querySelectorAll('.cv-form')].map((f) => f.classList.contains('cv-drop-target'))"
        def drag(ev, at=None):
            pos = f", position: {{ x: {at['x']}, y: {at['y']} }}" if at else ""
            pg.evaluate(f"() => window.__emit('tauri://{ev}', {{ paths: ['/sandbox/report.md']{pos} }})")
            pg.clock.run_for(50)
        logc = pg.evaluate(CENTER, ".cv-log")
        drag("drag-enter", form); h1 = pg.evaluate(HL)
        bw = pg.evaluate("() => getComputedStyle(document.querySelector('.cv-form')).borderTopStyle")
        if os.environ.get("CHATDROP_SHOT"):
            pg.screenshot(path=os.environ["CHATDROP_SHOT"])
        drag("drag-over", logc); h2 = pg.evaluate(HL)
        drag("drag-over", form); h3 = pg.evaluate(HL)
        drag("drag-leave"); h4 = pg.evaluate(HL)
        drag("drag-over", form); drop(pg, ["/sandbox/report.md"], form); h5 = pg.evaluate(HL)
        check(h1 == [True] and bw == "dashed", f"⑥′ 입력칸 위로 끌어 옴 → 강조 켬 · 점선 ({h1} · {bw})")
        check(h2 == [False] and h3 == [True], f"⑥′ 목록 위로 옮김 = 끔 · 다시 입력칸 = 켬 ({h2} · {h3})")
        check(h4 == [False] and h5 == [False], f"⑥′ 떠남 = 끔 · 놓음 = 끔 ({h4} · {h5})")
        pg.click(".cv-chip-x") if pg.evaluate(CHIPS) else None
        for _ in range(4):
            pg.clock.run_for(50)
        # ⑦ 보기 칸(덮개) 위
        drop(pg, ["/sandbox/report.md"], form)  # 칩 하나 든 채로
        open_peek(pg)
        peek_open = pg.evaluate("() => window.__cysPeek.open()")
        body = pg.evaluate(CENTER, ".cv-peek-body")
        hit_peek = pg.evaluate(f"() => !!document.elementFromPoint({body['x']}, {body['y']})?.closest('.cv-peek')")
        cs0, si1 = pg.evaluate(CHATSENDS), n(pg, "send_input")
        drop(pg, ["/sandbox/보고서 초안.md"], body)
        check(peek_open == 4 and hit_peek, f"⑦ 전제: 보기 칸 열림(좌석 {peek_open}) · 놓은 점 = 보기 칸 ({hit_peek})")
        check(len(pg.evaluate(CHIPS)) == 1 and n(pg, "send_input") == si1 and pg.evaluate(CHATSENDS) == cs0, f"⑦ 보기 칸 위 → 칩 그대로 1 · send_input 0 · chat_send 0 ({n(pg, 'send_input') - si1} · {pg.evaluate(CHATSENDS) - cs0})")
        pg.keyboard.press("Escape")
        pg.clock.run_for(300)
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(3_300)
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_300)
        check([c[0] for c in pg.evaluate(CHIPS)] == ["report.md"], f"⑦ 칩이 든 채 작업 화면 → 대화 화면 = 칩 남음 {pg.evaluate(CHIPS)}")
        check(not errs, f"A 페이지 오류 0 {errs}")
        ctx.close()

        print("== B. 1600×900 보기 칸 = 오른쪽 칸")
        ctx, pg, errs = page(1600, 900)
        open_peek(pg)
        form = pg.evaluate(CENTER, ".cv-form")
        covered = pg.evaluate(f"() => !document.elementFromPoint({form['x']}, {form['y']})?.closest('.cv-form')")
        drop(pg, ["/sandbox/report.md"], form)
        check(pg.evaluate("() => window.__cysPeek.open()") == 4 and not covered, f"B 전제: 보기 칸 열림 · 입력칸 안 가려짐 ({covered})")
        check(len(pg.evaluate(CHIPS)) == 1, f"B 보기 칸 열린 채 입력칸 위 → 칩 1 {pg.evaluate(CHIPS)}")
        si0 = n(pg, "send_input")
        drop(pg, ["/sandbox/보고서 초안.md"], pg.evaluate(CENTER, ".cv-peek-body"))
        check(len(pg.evaluate(CHIPS)) == 1 and n(pg, "send_input") == si0, f"B 보기 칸 위 → 칩 그대로 · send_input 0 ({n(pg, 'send_input') - si0})")
        check(not errs, f"B 페이지 오류 0 {errs}")
        ctx.close()
        br.close()
    httpd.shutdown()
    print("PASS" if not failures else f"FAIL {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
