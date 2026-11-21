#!/usr/bin/env python3
"""멈춤·깨우기·다시 켜기 조각 5 게이트 — TICKET=cysr-1116-s5-1119 · P2-DESIGN §6 · §11 조각 5 (수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(tickrec_gate SHIM + chat_gate CHAT_SHIM 위에 start_master·close_surface 계수를 덧씌움) + 가짜 시계.
클릭은 playwright 실제 마우스(page.click = 신뢰 이벤트) · 「대본 클릭」 = element.click()(isTrusted=false).

A 앱 새로 켬 + 마스터 이미 꺼짐(저장소 cys-master-seen · 마스터 좌석 없음) → 꺼짐 띠 「마스터가 멈춰 있어요」 · 대본 클릭 → start_master 0
B 진짜 클릭 → start_master 1 · 「켜는 중…」 잠금 · 연타 20(진짜 클릭) → 그대로 1 · 새 마스터 좌석 생존 → 띠 닫힘 · CSO·워커 좌석 수 그대로 · 사람 말 쓰기(chat_send) 0
C agent_never_started(사건 + 행) → 「아직 시작하지 못했어요」 → 진짜 클릭 → close_surface_if_quiet(그 좌석 · 생성 시각) 뒤 start_master(순서) · 쓰기 0
C2 같은 꼴 + 옛 창에 사람 입력 → 닫지 않음 · start_master 0 · 「그 창에 쓰다 만 글이 있어요」
D 조용함(master.idle) → 「마스터 깨우기」 → 깨움 말 1건(kind auto · 원문) · 120초 무반응 → 「마스터 다시 켜기」 + 「도움 요청 보내기」 함께
E 관문(gate_pending) → 「작업 화면에서 답하기」 → 작업 화면 + 안내 줄(「No, exit」 경고)
F 복원 중(restore-progress start) → 단추 「복원하는 중이에요」 잠금 · 진짜 클릭 → start_master 0
G 띠 그리기 예외 주입 → 작업 화면으로 물러남 + 물러남 띠(FR-V7)
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/revive_gate.py
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

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"
WAKE_TEXT = "[깨우기] 사용자가 대화 화면에서 깨웠어요. 남은 확인할 것을 이어서 봐 주세요."

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


REVIVE_SHIM = r"""
(() => {
  const C = window.__CHAT;
  C.starts = []; C.closes = []; C.order = []; C.startErr = null; C.onStart = null; C.rowOver = null;
  const prev = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    const a = args ?? {};
    // CHAT_SHIM 은 agent_alive 를 `??` 로 합쳐 null 을 못 싣는다 — 마스터 행 칸을 그대로 덮는 자리(never_started 꼴: agent_alive null)
    if (cmd === 'org_status' && (a.socket ?? null) === null && C.rowOver)
      return prev(cmd, args).then((r) => ({ ...r, surfaces: (r.surfaces || []).map((x) => (x.role === 'master' ? { ...x, ...C.rowOver } : x)) }));
    if (cmd === 'start_master') { C.starts.push(Date.now()); C.order.push('start'); if (C.onStart) C.onStart(); return C.startErr ? Promise.reject(C.startErr) : Promise.resolve(null); }
    if (cmd === 'close_surface' && (a.socket ?? null) === null) { C.closes.push(a.surfaceId); C.order.push('close:' + a.surfaceId); }
    // (master#565d7c18 P1) 조건부 닫기 — 데몬 대역: 생성 시각 · 사람 초안을 닫는 순간 다시 본다(맞으면 그 좌석을 닫음 · 아니면 close_refused)
    if (cmd === 'close_surface_if_quiet' && (a.socket ?? null) === null) {
      C.order.push('qclose:' + a.surfaceId + '@' + a.expectedCreatedAt);
      const o = C.rowOver || {};
      if (o.created_at !== a.expectedCreatedAt) return Promise.reject('close_refused: surface.close if_quiet refused: created_at_mismatch · not closed');
      if (o.pending_input_human_bytes) return Promise.reject('close_refused: surface.close if_quiet refused: input_line_has_human_draft · not closed');
      C.closes.push(a.surfaceId);
      return prev('close_surface', { socket: null, surfaceId: a.surfaceId });
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
    with sync_playwright() as p:
        exe = os.environ.get("CHROME_PATH")
        br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

        def page(seats: list[str], seen: "str | None" = None, master: "dict | None" = None):
            ctx = br.new_context(viewport={"width": 1400, "height": 900})
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            if seen is not None:
                pg.add_init_script(f"try {{ localStorage.setItem('cys-master-seen', {json.dumps(seen)}); }} catch {{}}")
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.add_init_script(REVIVE_SHIM)
            pg.goto(url)
            pg.clock.run_for(9_000)
            if seats:
                pg.evaluate(f"() => {{ window.__SEATS.push({', '.join(seats)}); }}")
            if master:
                pg.evaluate(f"() => {{ Object.assign(window.__CHAT.master, {json.dumps(master)}); }}")
            pg.clock.run_for(6_000)
            pg.click("#view-switch button[data-view=chat]")
            pg.clock.run_for(3_200)
            return ctx, pg, errs

        band = lambda pg: pg.evaluate("""() => { const b = document.querySelector('.cv-revive'); return { hidden: !b || b.hidden, key: b?.dataset.key ?? null,
            title: b?.querySelector('.cvr-title')?.textContent ?? '', btns: [...(b?.querySelectorAll('.cvr-btn') ?? [])].map((x) => [x.dataset.act, x.textContent, x.getAttribute('aria-disabled')]) }; }""")  # noqa: E731
        C = lambda pg, k: pg.evaluate(f"() => window.__CHAT.{k}")  # noqa: E731
        roles = lambda pg: pg.evaluate("() => window.__SEATS.filter((s) => s.sock === '" + BASE + "' && !s.ex).map((s) => s.role).sort()")  # noqa: E731

        print("== A 앱 새로 켬 + 마스터 이미 꺼짐 → 꺼짐 띠 · 대본 클릭 = 호출 0")
        ctx, pg, errs = page([seat(BASE, 1, None), seat(BASE, 2, "cso"), seat(BASE, 3, "worker-1")], seen="1")
        b = band(pg)
        check(not b["hidden"] and b["key"] == "down_vacant" and b["title"] == "마스터가 멈춰 있어요.", f"꺼짐 띠 보임 {b}")
        check(b["btns"] and b["btns"][0][0] == "restart" and b["btns"][0][1] == "마스터 다시 켜기", f"다시 켜기 단추 {b['btns']}")
        pg.evaluate("() => document.querySelector('.cvr-btn[data-act=restart]').click()")
        pg.evaluate("() => document.querySelector('.cvr-btn[data-act=restart]').dispatchEvent(new MouseEvent('click', { bubbles: true }))")
        pg.clock.run_for(500)
        check(C(pg, "starts.length") == 0, "★대본 클릭 2종 → start_master 0")

        print("== B 진짜 클릭 → start_master 1 · 연타 20 → 1 · 성공 → 띠 닫힘 · 좌석 수 그대로 · 쓰기 0")
        before = roles(pg)
        pg.click(".cvr-btn[data-act=restart]")
        pg.clock.run_for(300)
        b = band(pg)
        check(C(pg, "starts.length") == 1 and b["key"] == "restarting" and b["btns"][0][1] == "켜는 중…" and b["btns"][0][2] == "true", f"호출 1 · 「켜는 중…」 잠금 {b}")
        for _ in range(20):
            pg.click(".cvr-btn[data-act=restart]", force=True)  # 잠긴 단추(aria-disabled)도 진짜 마우스로 누름 — playwright 기본은 「누를 수 없음」이면 클릭 0
        pg.clock.run_for(300)
        check(C(pg, "starts.length") == 1, f"★연타 20(진짜 클릭) → start_master 그대로 1 ({C(pg, 'starts.length')})")
        pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 9, 'master')}); window.__CHAT.master.agent_alive = true; }}")
        pg.clock.run_for(6_500)
        b = band(pg)
        after = [r for r in roles(pg) if r != "master"]
        check(b["hidden"], f"새 마스터 좌석 생존 → 띠 닫힘 {b}")
        check(after == [r for r in before if r != "master"] and roles(pg).count("master") == 1, f"CSO·워커 수 그대로 · 마스터 1 {before} → {roles(pg)}")
        check(C(pg, "writes.length") == 0, "★다시 켜기 동안 사람 말 쓰기(chat_send) 0")
        check(not errs, f"페이지 오류 0 {errs}")
        ctx.close()

        print("== C agent_never_started → close_surface_if_quiet(그 좌석) 뒤 start_master")
        nev = {"agent": "claude", "agent_alive": None, "agent_seen": False, "seat": "empty", "created_at": 1795000001.25}
        ctx, pg, errs = page([seat(BASE, 1, "master"), seat(BASE, 2, "cso")])
        pg.evaluate(f"() => {{ window.__CHAT.rowOver = {json.dumps(nev)}; }}")
        pg.evaluate("() => window.__emit('daemon-event', { name: 'master.deadman', surface_id: 1, seq: 7001, socket_slug: 'base', timestamp: Date.now() / 1000, payload: { role: 'master', axis: 'agent_never_started' } })")
        pg.clock.run_for(3_200)
        b = band(pg)
        check(b["key"] == "down_never" and b["title"] == "마스터가 아직 시작하지 못했어요.", f"never 띠 {b}")
        pg.evaluate(f"() => {{ window.__CHAT.onStart = () => {{ window.__SEATS.push({seat(BASE, 9, 'master')}); }}; window.__CHAT.order = []; window.__CHAT.closes = []; }}")  # 클릭 전 기록(앱 시작 때 작업 화면 쪽 닫기)은 대조 밖
        pg.click(".cvr-btn[data-act=restart]")
        pg.clock.run_for(500)
        check(C(pg, "order") == ["qclose:1@1795000001.25", "start"], f"★순서 = 조건부 닫기(그 좌석 · 생성 시각) → start_master {C(pg, 'order')}")
        check(C(pg, "closes") == [1], f"그 좌석만 닫힘 {C(pg, 'closes')}")
        check(C(pg, "writes.length") == 0, "쓰기 0")
        ctx.close()

        print("== C2 never + 옛 창에 사람 입력 → 닫지 않음")
        ctx, pg, errs = page([seat(BASE, 1, "master")])
        pg.evaluate(f"() => {{ window.__CHAT.rowOver = {json.dumps({**nev, 'pending_input_human_bytes': 9})}; }}")
        pg.evaluate("() => window.__emit('daemon-event', { name: 'master.deadman', surface_id: 1, seq: 7002, socket_slug: 'base', timestamp: Date.now() / 1000, payload: { role: 'master', axis: 'agent_never_started' } })")
        pg.clock.run_for(3_200)
        pg.evaluate("() => { window.__CHAT.order = []; }")
        pg.click(".cvr-btn[data-act=restart]")
        pg.clock.run_for(500)
        b = band(pg)
        check(C(pg, "order") == [] and b["title"] == "그 창에 쓰다 만 글이 있어요.", f"★사람 입력 있는 창 = 닫기 0 · start_master 0 · 안내 {C(pg, 'order')} {b}")
        ctx.close()

        print("== D 조용함 → 깨우기 1건 · 120초 → 다시 켜기 + 도움 요청")
        ctx, pg, errs = page([seat(BASE, 1, "master"), seat(BASE, 2, "cso")], master={"idle_secs": 900, "agent_alive": True})
        pg.evaluate("() => window.__emit('daemon-event', { name: 'master.idle', surface_id: 1, seq: 7101, socket_slug: 'base', timestamp: Date.now() / 1000, payload: { role: 'master', axis: 'silence', idle_secs: 900 } })")
        pg.clock.run_for(3_200)
        b = band(pg)
        check(b["key"] == "idle" and b["btns"][0][1] == "마스터 깨우기", f"깨우기 띠 {b}")
        pg.click(".cvr-btn[data-act=wake]")
        pg.clock.run_for(300)
        for _ in range(5):
            pg.click(".cvr-btn[data-act=wake]", force=True)
        pg.clock.run_for(300)
        w = pg.evaluate("() => window.__CHAT.writes.map((x) => [x.args.kind, x.args.text])")
        check(w == [["auto", WAKE_TEXT]], f"★깨움 말 1건(kind auto · 원문) · 연타에도 1 {w}")
        pg.clock.run_for(121_000)
        b = band(pg)
        acts = [x[0] for x in b["btns"]]
        check(b["key"] == "wakefail" and acts == ["restart", "help"], f"120초 → 「마스터 다시 켜기」 + 「도움 요청 보내기」 함께 {b}")
        ctx.close()

        print("== E 관문 → 작업 화면에서 답하기")
        ctx, pg, errs = page([seat(BASE, 1, "master")], master={"gate_pending": {"gate": "trust", "since": 1}})
        b = band(pg)
        check(b["key"] == "gate" and b["btns"][0][1] == "작업 화면에서 답하기", f"관문 띠 {b}")
        pg.click(".cvr-btn[data-act=gate_answer]")
        pg.clock.run_for(500)
        st = pg.evaluate("""() => ({ work: document.querySelector('#view-switch button[data-view=work]')?.getAttribute('aria-pressed'),
            hint: (() => { const h = document.querySelector('#view-switch .vs-hint'); return h && !h.hidden ? h.textContent : null; })() })""")
        check(st["work"] == "true" and st["hint"] and "No, exit" in st["hint"], f"작업 화면 + 관문 안내 줄 {st}")
        ctx.close()

        print("== F 복원 중 → 잠금 · 호출 0")
        ctx, pg, errs = page([seat(BASE, 1, None)], seen="1")
        pg.evaluate("() => window.__emit('restore-progress', { phase: 'start' })")
        pg.clock.run_for(3_200)
        b = band(pg)
        check(b["btns"] and b["btns"][0][1] == "복원하는 중이에요" and b["btns"][0][2] == "true", f"「복원하는 중이에요」 잠금 {b}")
        pg.click(".cvr-btn[data-act=restart]", force=True)
        pg.clock.run_for(500)
        check(C(pg, "starts.length") == 0, "★복원 중 진짜 클릭 → start_master 0")
        ctx.close()

        print("== G 띠 그리기 예외 → 작업 화면으로 물러남")
        ctx, pg, errs = page([seat(BASE, 1, "master")])
        pg.evaluate("""() => { const o = Element.prototype.replaceChildren; Element.prototype.replaceChildren = function (...a) {
            if (this.classList && this.classList.contains('cv-revive')) { Element.prototype.replaceChildren = o; throw new Error('주입 예외'); } return o.apply(this, a); }; }""")
        pg.evaluate("() => window.__emit('daemon-event', { name: 'master.deadman', surface_id: 1, seq: 7201, socket_slug: 'base', timestamp: Date.now() / 1000, payload: { role: 'master', axis: 'agent_dead' } })")
        pg.evaluate("() => { window.__CHAT.master.agent_alive = false; }")
        pg.clock.run_for(3_500)
        st = pg.evaluate("""() => ({ work: document.querySelector('#view-switch button[data-view=work]')?.getAttribute('aria-pressed'),
            band: document.querySelector('#view-switch .vs-band')?.textContent ?? '' })""")
        check(st["work"] == "true" and "작업 화면으로 바꿨어요" in st["band"], f"★예외 → 작업 화면 + 물러남 띠 {st}")
        ctx.close()
        br.close()
    httpd.shutdown()
    print(f"\n결과: {'PASS' if not failures else 'FAIL'} · 실패 {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
