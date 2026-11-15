#!/usr/bin/env python3
"""새 좌석 생성 중 전환 경합 게이트 — TICKET=cysr-tabs-sidebar-impl · ChatGPT 대체 1R #2·#3(master#4e00a677 · 수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(statusboard_gate SHIM) · create_surface 응답을 1.5초 늦추고 그 사이에:
  R1(#2) 본부 작업공간에서 ⌘T → 부서 작업공간(lms)으로 전환 → 새 좌석(본부 데몬 것)은 본부 트리에만 · 부서 트리에 0 · 화면 포커스는 지금 작업공간 좌석
  R2(#3) site 탭 좌석 4 에서 ⌘D → 탭 lms 로 전환 → 새 좌석은 시작한 탭(site) 묶음 · 지금 보이는 lms 화면에 없음 · 포커스 = 보이는 좌석(숨은 좌석 아님)
    (codex 2R #4) 뒤이은 3초 목록 render(새 좌석을 데려와 창을 떼었다 붙임)를 지난 뒤에도 **실제 키보드 포커스**(document.activeElement)가
    포커스 표시된 보이는 좌석 안에 있고(BODY 아님) · 이어 친 글자의 send_input 목적지 = 그 좌석뿐(유실 0)
  R3(#3) site 탭 좌석 4 에서 ⌘D → 그 사이 좌석 4 닫힘(surface.closed) → 새 좌석이 화면에 보이고 포커스도 그 좌석 · 오류 0
  R4(codex 2R #3) 본부 작업공간에서 ⌘T → 응답 전에 그 작업공간 삭제 확인 → 새 좌석 50 = 닫힘(close_surface(50)) · 어느 트리에도 없음(고아 0) · 알림 1
  R4b(codex 2R #3 · 삭제 「진행 중」 갈래) 같은 장면에서 좌석 닫기를 0.6초씩 늦춰 생성 응답이 삭제가 끝나기 전(ws.deleting)에 온다 → 새 좌석 50 = 닫힘 · 어느 트리에도 없음
  R5(codex 2R #3) 같은 장면을 나누기(⌘D · actionSplit)로 — 본부 좌석 1 에서 ⌘D → 응답 전에 그 작업공간 삭제 → 새 좌석 50 = 닫힘 · 어느 트리에도 없음
    (작업공간이 하나뿐이면 상황판 화면은 작업공간 탭을 숨겨 사람이 지울 길이 없다 — 그래서 부서 3개 장면)
  R6(await 전수 표 · 같은 모양) 빈 작업공간의 「새 셸 열기」 → 응답 전에 그 작업공간 삭제 → 새 좌석 = 닫힘 · 어느 트리에도 없음 · 알림 1
  ── 아래 = codex 3R · 공통 단언 「화면 밖 런타임 0」(좌석 출력 듣기가 살아 있는 (소켓, 좌석) 은 전부 그 소켓 작업공간 트리에 있다 · ChatGPT F8 복합 키) ──
  (ChatGPT F10) R7b·R9d·R9e = 지연 시간이 아니라 명시 대기 지점(닫기 붙잡기 __CLOSE_HOLD → 응답 도착 표지 → 「삭제 진행 중」 단언 → 풀기)
  (ChatGPT F9) R8·R10b = 새 좌석의 close_surface 와 데몬 목록에서 빠짐을 직접 단언
  R0(F8) 검출기 자가 시험 — 본부 1 과 같은 번호의 LMS 1 출력 듣기가 살아 있으면 잡는다(좌석 번호만 보던 판은 못 잡음)
  R11(ChatGPT F1) 기동 복원: 활성 LMS(좌석 0)의 첫 좌석 생성이 실패하는 사이 본부 탭으로 전환 → 본부 데몬 좌석이 LMS 트리에 붙지 않는다
  R7(3R blocking 2) 본부 작업공간 2개(A=1~5 · B=새 셸) · 새 역할 좌석 60 자동 입양의 attach 를 늦추고 그 사이 A 삭제 → 60 = 살아 있는 같은 데몬 작업공간 B 에 · 닫지 않음
  R7b(3R blocking 2) 본부 작업공간 1개 · 같은 장면(삭제 「진행 중」 에 attach 응답) → 붙일 곳 없음 = 런타임만 파기(화면 밖 0) · 좌석 60 은 닫지 않음(외부 역할 좌석)
  R8(3R blocking 3) 본부 셸 좌석 50 을 LMS 부서 탭으로 끌어 전출 → 새 좌석 응답 전에 LMS 삭제 → 원본 50 보존(close_surface(50) 0 · 본부 트리에 그대로) ·
     새 좌석 51 = 거둠 · 알림 「전출 중단」
  R9a(3R major 4) R4 장면에서 새 좌석 50 닫기를 1번 거부 → 삭제 확정 뒤 다시 닫아 거둠(close_surface(50) 2회) · 화면 밖 0
  R9b(3R major 4) 닫기를 계속 거부 · 같은 데몬 작업공간 없음 → 새 작업공간에 붙여 보이게 · 화면 밖 0 · 알림
  R9c(3R major 4) LMS 부서에서 ⌘T → 응답 전 LMS 삭제(데몬 종료 확인) · 50 닫기 계속 거부 → 런타임 파기 · 화면 밖 0
  R9d(3R major 4) 본부 삭제가 좌석 1 닫기 거부로 보존되는데 그 「진행 중」 에 새 좌석 50 닫기도 거부 → 결과 확정 뒤 보존된 본부 작업공간에 붙임 · 화면 밖 0
  R9e(3R major 4 · 「진행 중」 갈래) 새 좌석 닫기 계속 거부 · 그 순간 삭제가 아직 진행 중(좌석 닫기 0.6초씩)이고 결국 성공 → 결과 확정 뒤 판정 = 새 작업공간에 보이게 ·
     화면 밖 0(확정 전에 「지금 목록에 있는 그 작업공간」 에 붙이면 곧 지워져 고아가 된다)
  R10(3R 전수 표 · start() 같은 모양) 기동 복원 중 — 탭은 이미 그려져 지울 수 있다 — 좌석 1 의 붙이기(attach)를 늦추고 그 사이 본부 작업공간 삭제 →
     복원 좌석 1~5 = 지워진 작업공간에 안 붙음 · 닫지 않음(외부 좌석) · 화면 밖 0
  R10b(같은 모양 · 빈 부서 자리 좌석) LMS 좌석이 하나도 없는 기동 → 복원이 LMS 에 빈 자리 좌석을 만드는 응답 전에 LMS 삭제 → 새 좌석 거둠 · 화면 밖 0
실행: CHROME_PATH=<chrome-headless-shell> [GATE_DIST=<다른 번들>] cys run -- <playwright python3> ui/e2e/race_gate.py
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else sbg.DIST

SPY = r"""
(() => {
  window.__calls = [];
  window.__toasts = []; // 알림은 몇 초 뒤 사라진다 — 붙는 순간 글을 적어 둔다
  document.addEventListener('DOMContentLoaded', () => new MutationObserver((ms) => { for (const m of ms) for (const n of m.addedNodes) if (n.classList?.contains('toast')) window.__toasts.push(n.textContent); }).observe(document.body, { childList: true, subtree: true }));
  window.__LIVE = {}; // 좌석 런타임 생존 = 그 좌석 출력 듣기(attach 가 준 이름)가 풀리지 않았다
  const ol = window.__TAURI__.event.listen;
  window.__TAURI__.event.listen = (name, h) => { window.__LIVE[name] = (window.__LIVE[name] ?? 0) + 1;
    return ol(name, h).then((u) => { let done = false; return () => { if (!done) { done = true; window.__LIVE[name]--; } u(); }; }); };
  const orig = window.__TAURI__.core.invoke;
  const doClose = (args) => { // 닫힌 좌석은 목록에서도 빠진다(데몬과 같게)
    if ((window.__REFUSE?.[args?.surfaceId] ?? 0) > 0) { window.__REFUSE[args.surfaceId]--; // R9 = 데몬이 닫기를 거부
      return new Promise((_, rej) => setTimeout(() => rej('close refused (sim)'), window.__CLOSE_DELAY ?? 0)); }
    const i = window.__SEATS.findIndex((s) => s.sid === args?.surfaceId && s.sock === (args?.socket ?? '__BASE__'));
    if (i >= 0) window.__SEATS.splice(i, 1);
    return new Promise((res) => setTimeout(() => res({ ok: true }), window.__CLOSE_DELAY ?? 0)); // R4b = 느린 닫기(삭제가 「진행 중」인 채 생성 응답이 온다)
  };
  window.__TAURI__.core.invoke = (cmd, args) => {
    if (['send_input', 'close_surface', 'create_surface', 'attach_surface'].includes(cmd)) window.__calls.push([cmd, args?.surfaceId ?? null, args?.socket ?? null]);
    if (cmd === 'attach_surface') { // (ChatGPT F8) 출력 듣기 이름 = 소켓#좌석(본부 50 과 부서 50 을 가른다) · 붙이기 끝남 기록(F10 명시 대기 지점)
      const d = window.__ATTACH_DELAY?.[args?.surfaceId] ?? 0; // R7 = 느린 입양
      return new Promise((res) => setTimeout(res, d)).then(() => orig(cmd, args)).then((r) => { (window.__attached ??= []).push([args?.socket ?? '__BASE__', args?.surfaceId]);
        return { ...r, output_event: 'sim-out-' + (args?.socket ?? '__BASE__') + '#' + args?.surfaceId, exited_event: 'sim-exit-' + (args?.socket ?? '__BASE__') + '#' + args?.surfaceId }; });
    }
    if (cmd === 'list_surfaces') return orig(cmd, args).then((r) => { for (const row of r?.surfaces ?? []) if (window.__SEATS.some((x) => x.sid === row.surface_id && x.shell)) row.agent = null; return r; }); // R8 = 셸 좌석(에이전트 아님)
    if (cmd === 'create_surface' && (window.__CREATE_FAIL ?? []).includes(args?.socket ?? '__BASE__')) return new Promise((_, rej) => setTimeout(() => rej('create failed (sim)'), 1500)); // R11 = 부서 데몬 생성 실패
    if (cmd === 'create_surface') return new Promise((res) => setTimeout(() => {
      const sid = window.__nextSid = (window.__nextSid ?? 49) + 1; // 50, 51, … (대체 작업공간이 또 만들 수 있다)
      window.__SEATS.push({ sock: args?.socket ?? '__BASE__', sid, no: 900 + sid, role: null, cwd: '/Users/sim', act: 'waiting', raw: 'idle', approval: false, self: null, task: null, ctx: null, shell: true });
      (window.__made ??= []).push([args?.socket ?? '__BASE__', sid]); // (F9·F10) 만든 좌석 기록 = 응답 도착 표지
      res({ surface_id: sid, display_no: 900 + sid });
    }, 1500));
    if (cmd === 'close_surface' && window.__CLOSE_HOLD) return new Promise((res, rej) => (window.__held ??= []).push(() => doClose(args).then(res, rej))); // (F10) 명시 대기 지점 — __releaseClose() 까지 닫기를 붙잡는다
    if (cmd === 'close_surface') return doClose(args);
    return orig(cmd, args);
  };
  window.__releaseClose = () => { window.__CLOSE_HOLD = false; const h = window.__held ?? []; window.__held = []; for (const f of h) f(); };
})();
"""

STATE = (r"""
() => { const lay = JSON.parse(localStorage.getItem('cys-layout-v2') || '{}'); const sids = (n) => !n ? [] : n.type === 'pane' ? [n.sid] : [...sids(n.a), ...sids(n.b)];
  return { panes: [...document.querySelectorAll('#root .pane')].map((p) => +p.dataset.sid).sort((a, b) => a - b),
    focused: [...document.querySelectorAll('.pane.focused')].filter((p) => p.isConnected).map((p) => +p.dataset.sid),
    active: (() => { const a = document.activeElement; const p = a?.closest?.('.pane'); return p ? +p.dataset.sid : (a?.tagName ?? null); })(),
    tab: document.querySelector('#root .group-tab.active .group-tab-name')?.textContent ?? null,
    trees: (lay.workspaces || []).map((w) => ({ socket: w.socket ?? null, sids: sids(w.tree) })),
    // (ChatGPT F8) 화면 밖 런타임 = 출력 듣기가 살아 있는 (소켓, 좌석) 이 그 소켓 작업공간 트리에 없다 — 좌석 번호만 보면 본부 50 이 부서 50 을 가린다
    offscreen: (() => { const inTree = new Set((lay.workspaces || []).flatMap((w) => sids(w.tree).map((sid) => (w.socket ?? '__BASE__') + '#' + sid)));
      return Object.entries(window.__LIVE || {}).filter(([n, c]) => n.startsWith('sim-out-') && c > 0).map(([n]) => n.slice(8)).filter((k) => !inTree.has(k)); })(),
    // (ChatGPT F1) 다른 데몬 좌석이 붙은 트리 = 트리의 좌석 번호가 그 소켓 데몬 좌석 목록엔 없고 다른 소켓에만 있다
    wrongSock: (lay.workspaces || []).flatMap((w) => sids(w.tree).filter((sid) => !window.__SEATS.some((x) => x.sid === sid && x.sock === (w.socket ?? '__BASE__')) && window.__SEATS.some((x) => x.sid === sid)).map((sid) => (w.socket ?? '__BASE__') + '#' + sid)) }; }
""").replace("__BASE__", sbg.BASE)


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    js = lambda rows: [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=False, self=s[8], task=s[9], ctx=s[10]) for s in rows]  # noqa: E731
    print("번들:", DIST)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

            def page(seats, depts):
                ctx = br.new_context(viewport={"width": 1920, "height": 1200})
                pg = ctx.new_page()
                errs: list[str] = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                pg.add_init_script(sbg.SHIM.replace("__SEATS__", "window.__SEATS = " + json.dumps(seats)).replace("__DEPTS__", json.dumps(depts)).replace("__BASE__", sbg.BASE))
                pg.add_init_script(SPY.replace("__BASE__", sbg.BASE))
                pg.goto(url)
                pg.wait_for_timeout(11500)
                return ctx, pg, errs

            def delete_ws(pg, idx):
                pg.query_selector_all("#ws-tabs .ws-tab")[idx].query_selector(".ws-close").click()
                pg.wait_for_timeout(300)
                btn = next((b for b in pg.query_selector_all(".modal-overlay button") if (b.text_content() or "").strip() == "삭제"), None)
                sbg.check(btn is not None, "삭제 확인 창의 「삭제」 단추")
                if btn:
                    btn.click()

            def toasts(pg):
                return pg.evaluate("() => window.__toasts")

            def no_offscreen(st, tag):
                sbg.check(not st["offscreen"], f"{tag} 화면 밖 런타임 0 {st['offscreen']} · 트리 {st['trees']}")

            def wait_attach(pg, sid, ms=6000):
                pg.wait_for_function(f"() => window.__calls.some((c) => c[0] === 'attach_surface' && c[1] === {sid})", timeout=ms)

            NEW_ROLE = "{ sock: '__BASE__', sid: 60, no: 960, role: 'worker-9', cwd: '/u/axdev', act: 'waiting', raw: 'idle', approval: false, self: null, task: null, ctx: null }".replace("__BASE__", sbg.BASE)

            BUSY = "() => document.querySelector('#ws-tabs .ws-tab[aria-busy=\"true\"]') !== null"

            def made_on(pg, sock):
                return [m[1] for m in pg.evaluate("() => window.__made ?? []") if m[0] == sock]

            def reclaimed(pg, sock, sid):  # (ChatGPT F9) 그 데몬에 닫기 요청이 갔고 데몬 좌석 목록에서도 빠졌다
                closed = [c for c in pg.evaluate("() => window.__calls") if c[0] == "close_surface" and c[1] == sid and (c[2] or sbg.BASE) == sock]
                alive = pg.evaluate(f"() => window.__SEATS.some((x) => x.sid === {sid} && x.sock === {json.dumps(sock)})")
                return bool(closed) and not alive

            def new_then_delete(pg, refuse, close_delay=0, ws_i=None, hold=False):
                pg.click('#root .pane[data-sid="1"] .xterm-screen')
                pg.wait_for_timeout(300)
                pg.evaluate(f"() => {{ window.__calls = []; window.__toasts = []; window.__REFUSE = {json.dumps(refuse)}; window.__CLOSE_DELAY = {close_delay}; window.__CLOSE_HOLD = {'true' if hold else 'false'}; }}")
                pg.keyboard.press("Meta+t")
                pg.wait_for_timeout(200)
                delete_ws(pg, base_i if ws_i is None else ws_i)

            def boot(seats_, depts_, init_js):
                ctx = br.new_context(viewport={"width": 1920, "height": 1200})
                pg = ctx.new_page()
                errs: list[str] = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                pg.add_init_script(sbg.SHIM.replace("__SEATS__", "window.__SEATS = " + json.dumps(seats_)).replace("__DEPTS__", json.dumps(depts_)).replace("__BASE__", sbg.BASE))
                pg.add_init_script(SPY.replace("__BASE__", sbg.BASE))
                pg.add_init_script(init_js)
                pg.goto(url)
                return ctx, pg, errs

            def tab_index(pg, pred):
                names = [(t.text_content() or "") for t in pg.query_selector_all("#ws-tabs .ws-tab")]
                return next((i for i, n in enumerate(names) if pred(n)), None), names


            # R1
            print("== R1(#2) ⌘T 생성 중 작업공간 전환")
            seats, depts = sbg.SCEN["dept3"]
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            s0 = pg.evaluate(STATE)
            base_i = next(i for i, t in enumerate(s0["trees"]) if t["socket"] in (None, sbg.BASE))
            pg.click('#root .pane[data-sid="1"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.keyboard.press("Meta+t")
            pg.wait_for_timeout(300)
            tabs = pg.query_selector_all("#ws-tabs .ws-tab")
            other = next((i for i in range(len(tabs)) if i != base_i), None)
            sbg.check(other is not None, f"작업공간 {len(tabs)}개(전환할 곳 있음)")
            if other is not None:
                tabs[other].click()
            pg.wait_for_timeout(2500)
            s1 = pg.evaluate(STATE)
            in_base = 50 in s1["trees"][base_i]["sids"]
            in_other = [t["socket"] for i, t in enumerate(s1["trees"]) if i != base_i and 50 in t["sids"]]
            sbg.check(in_base and not in_other, f"새 좌석 50 = 본부 트리에만(부서 트리 {in_other}) · 트리 {s1['trees']}")
            sbg.check(50 not in s1["panes"], f"지금 화면(부서) 에 본부 좌석 50 없음 {s1['panes']}")
            sbg.check(not s1["focused"] or s1["focused"][0] in s1["panes"], f"포커스 = 지금 화면 좌석 {s1['focused']}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            seats7 = js(sbg.W7)
            # R2
            print("== R2(#3) ⌘D 생성 중 탭 전환")
            ctx, pg, errs = page(seats7, [])
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.keyboard.press("Meta+d")
            pg.wait_for_timeout(300)
            pg.click('#root .group-tab:has-text("lms")')
            # 생성 응답(1.5초) + 그 뒤 3초 목록 1바퀴(새 좌석을 목록에서 데려와 render — 창을 떼었다 붙인다)를 넉넉히 지난다
            pg.wait_for_timeout(5000)
            s2 = pg.evaluate(STATE)
            sbg.check(s2["tab"] == "lms" and 50 not in s2["panes"], f"지금 lms 화면 = 새 좌석 없음(시작한 site 탭 묶음) {s2['panes']} · 탭 {s2['tab']}")
            sbg.check(len(s2["focused"]) == 1 and s2["focused"][0] in s2["panes"], f"포커스 표시 = 보이는 좌석(숨은 새 좌석 아님) {s2['focused']}")
            # (codex 2R #4) 표시만이 아니라 실제 키보드 포커스 — BODY 면 친 글자가 어디로도 안 간다(유실)
            sbg.check(s2["active"] in s2["panes"] and s2["focused"] == [s2["active"]], f"실제 키보드 포커스 = 포커스 표시된 보이는 좌석(BODY 아님) · 키보드 {s2['active']} · 표시 {s2['focused']}")
            pg.evaluate("() => { window.__calls = []; }")
            pg.keyboard.type("xy")
            pg.wait_for_timeout(500)
            sent = [c for c in pg.evaluate("() => window.__calls") if c[0] == "send_input"]
            sbg.check(bool(sent) and all(c[1] == (s2["focused"] or [None])[0] for c in sent), f"이어 친 글자 = 그 보이는 좌석으로만(유실 0 · 숨은 좌석 0) {sent} · 표시 {s2['focused']}")
            pg.click('#root .group-tab:has-text("site")')
            pg.wait_for_timeout(600)
            s2b = pg.evaluate(STATE)
            sbg.check(50 in s2b["panes"], f"site 탭으로 돌아가면 새 좌석 50 보임 {s2b['panes']}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R3
            print("== R3(#3) ⌘D 생성 중 대상 좌석 닫힘")
            ctx, pg, errs = page(seats7, [])
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.keyboard.press("Meta+d")
            pg.wait_for_timeout(300)
            pg.evaluate("""() => { const a = window.__SEATS; a.splice(a.findIndex((s) => s.sid === 4), 1);
              window.__emit('daemon-event', { type: 'event', seq: 5, name: 'surface.closed', category: 'surface', surface_id: 4, socket_slug: 'base', payload: { surface_id: 4 } }); }""")
            pg.wait_for_timeout(2500)
            s3 = pg.evaluate(STATE)
            sbg.check(4 not in s3["panes"] and 50 in s3["panes"], f"대상 닫힘 뒤 새 좌석 50 보임 {s3['panes']}")
            sbg.check(s3["focused"] == [50] and s3["active"] == 50, f"포커스 = 새 좌석(표시 {s3['focused']} · 키보드 {s3['active']})")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R4
            print("== R4(codex 2R #3) ⌘T 생성 중 그 작업공간 삭제")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            s0 = pg.evaluate(STATE)
            base_i = next(i for i, t in enumerate(s0["trees"]) if t["socket"] in (None, sbg.BASE))
            pg.click('#root .pane[data-sid="1"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.keyboard.press("Meta+t")
            pg.wait_for_timeout(200)
            delete_ws(pg, base_i)
            pg.wait_for_timeout(4500)
            s4 = pg.evaluate(STATE)
            closed = [c for c in pg.evaluate("() => window.__calls") if c[0] == "close_surface"]
            sbg.check(not any(t["socket"] in (None, sbg.BASE) for t in s4["trees"]), f"본부 작업공간 지워짐 {s4['trees']}")
            sbg.check(any(c[1] == 50 for c in closed), f"새 좌석 50 = 닫힘(고아 0) · close_surface {closed}")
            sbg.check(not any(50 in t["sids"] for t in s4["trees"]) and 50 not in s4["panes"], f"새 좌석 50 = 어느 트리·화면에도 없음 {s4['trees']}")
            sbg.check(any("새 좌석 닫음" in (t or "") for t in toasts(pg)), f"알림 「새 좌석 닫음」 {toasts(pg)}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R4b
            print("== R4b(codex 2R #3) ⌘T 생성 응답이 삭제 진행 중(ws.deleting)에 도착")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            pg.click('#root .pane[data-sid="1"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.evaluate("() => { window.__CLOSE_DELAY = 600; }")
            pg.keyboard.press("Meta+t")
            pg.wait_for_timeout(200)
            delete_ws(pg, base_i)
            pg.wait_for_timeout(1300)
            mid = pg.evaluate("() => JSON.parse(localStorage.getItem('cys-layout-v2') || '{}').workspaces?.length ?? null")
            pg.wait_for_timeout(5500)
            s4b = pg.evaluate(STATE)
            closed = [c for c in pg.evaluate("() => window.__calls") if c[0] == "close_surface"]
            print(f"  (실측) 생성 응답 무렵 저장 작업공간 수 = {mid}(3 = 아직 삭제 진행 중)")
            sbg.check(any(c[1] == 50 for c in closed), f"새 좌석 50 = 닫힘(고아 0) · close_surface {closed}")
            sbg.check(not any(50 in t["sids"] for t in s4b["trees"]) and 50 not in s4b["panes"], f"새 좌석 50 = 어느 트리·화면에도 없음 {s4b['trees']}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R5
            print("== R5(codex 2R #3) ⌘D 생성 중 그 작업공간 삭제")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            pg.click('#root .pane[data-sid="1"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.keyboard.press("Meta+d")
            pg.wait_for_timeout(200)
            delete_ws(pg, base_i)
            pg.wait_for_timeout(5000)
            s5 = pg.evaluate(STATE)
            closed = [c for c in pg.evaluate("() => window.__calls") if c[0] == "close_surface"]
            sbg.check(any(c[1] == 50 for c in closed), f"새 좌석 50 = 닫힘(고아 0) · close_surface {closed}")
            sbg.check(not any(50 in t["sids"] for t in s5["trees"]) and 50 not in s5["panes"], f"새 좌석 50 = 어느 트리·화면에도 없음 {s5['trees']} · 화면 {s5['panes']}")
            sbg.check(any("새 좌석 닫음" in (t or "") for t in toasts(pg)), f"알림 「새 좌석 닫음」 {toasts(pg)}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            # R6
            print("== R6(전수 표) 빈 작업공간 「새 셸 열기」 생성 중 그 작업공간 삭제")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            pg.click("#btn-ws-new")
            pg.wait_for_timeout(2500)
            s6a = pg.evaluate(STATE)
            sbg.check(s6a["panes"] == [50], f"새 작업공간 = 좌석 50 하나 {s6a['panes']}")
            pg.click('#root .pane[data-sid="50"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.keyboard.press("Meta+w")
            pg.wait_for_timeout(400)
            yes = next((b for b in pg.query_selector_all(".modal-overlay button") if (b.text_content() or "").strip() == "닫기"), None)
            if yes:
                yes.click()
            pg.wait_for_timeout(800)
            btn = pg.query_selector("#root .dept-idle-btn")
            sbg.check(btn is not None, "빈 작업공간 = 「새 셸 열기」 단추")
            if btn:
                pg.evaluate("() => { window.__calls = []; window.__toasts = []; }")
                btn.click()
                pg.wait_for_timeout(200)
                delete_ws(pg, len(pg.query_selector_all("#ws-tabs .ws-tab")) - 1)
                pg.wait_for_timeout(4500)
                s6 = pg.evaluate(STATE)
                closed = [c for c in pg.evaluate("() => window.__calls") if c[0] == "close_surface"]
                sbg.check(any(c[1] == 51 for c in closed), f"새 좌석 51 = 닫힘(고아 0) · close_surface {closed}")
                sbg.check(not any(51 in t["sids"] for t in s6["trees"]) and 51 not in s6["panes"], f"새 좌석 51 = 어느 트리·화면에도 없음 {s6['trees']} · 화면 {s6['panes']}")
                sbg.check(any("새 좌석 닫음" in (t or "") for t in toasts(pg)), f"알림 「새 좌석 닫음」 {toasts(pg)}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R7
            print("== R7(3R blocking 2) 입양 attach 사이 그 작업공간 삭제 → 같은 데몬의 다른 작업공간에")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            pg.click("#btn-ws-new")  # 본부 데몬 작업공간 B(새 셸 50)
            pg.wait_for_timeout(2500)
            s7a = pg.evaluate(STATE)
            a_i = next(i for i, t in enumerate(s7a["trees"]) if t["socket"] in (None, sbg.BASE) and 1 in t["sids"])
            b_i = next((i for i, t in enumerate(s7a["trees"]) if t["socket"] in (None, sbg.BASE) and i != a_i), None)
            sbg.check(b_i is not None, f"본부 데몬 작업공간 2개 {s7a['trees']}")
            pg.evaluate("() => { window.__calls = []; window.__ATTACH_DELAY = { 60: 2500 }; window.__SEATS.push(" + NEW_ROLE + "); }")
            wait_attach(pg, 60)
            delete_ws(pg, a_i)
            pg.wait_for_timeout(4500)
            s7 = pg.evaluate(STATE)
            closed = [c for c in pg.evaluate("() => window.__calls") if c[0] == "close_surface"]
            b_now = [t for t in s7["trees"] if t["socket"] in (None, sbg.BASE)]
            sbg.check(len(b_now) == 1 and 1 not in b_now[0]["sids"], f"작업공간 A 지워짐 · 남은 본부 작업공간 1 {s7['trees']}")
            sbg.check(len(b_now) == 1 and 60 in b_now[0]["sids"], f"입양 좌석 60 = 살아 있는 같은 데몬 작업공간 B 에 {s7['trees']}")
            sbg.check(not any(c[1] == 60 for c in closed), f"좌석 60 은 닫지 않음(외부 역할 좌석) {closed}")
            no_offscreen(s7, "R7")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R7b
            print("== R7b(3R blocking 2) 입양 attach 응답이 유일한 본부 작업공간 삭제 「진행 중」 에 → 런타임만 파기")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            pg.evaluate("() => { window.__calls = []; window.__CLOSE_HOLD = true; window.__ATTACH_DELAY = { 60: 1000 }; window.__SEATS.push(" + NEW_ROLE + "); }")
            wait_attach(pg, 60)
            delete_ws(pg, base_i)
            # (ChatGPT F10) 명시 대기 지점: 삭제의 좌석 닫기를 붙잡아 둔 채 attach 응답이 도착 → 그때 삭제 「진행 중」 을 단언 → 닫기 풀기
            pg.wait_for_function("() => (window.__attached ?? []).some((a) => a[1] === 60)", timeout=8000)
            mid = pg.evaluate(BUSY)
            sbg.check(mid, f"(순서 단언) attach 응답이 도착한 때 = 삭제 진행 중 {mid}")
            pg.evaluate("() => window.__releaseClose()")
            pg.wait_for_timeout(6000)
            s7b = pg.evaluate(STATE)
            closed = [c for c in pg.evaluate("() => window.__calls") if c[0] == "close_surface"]
            sbg.check(not any(t["socket"] in (None, sbg.BASE) for t in s7b["trees"]), f"본부 작업공간 지워짐 {s7b['trees']}")
            sbg.check(not any(60 in t["sids"] for t in s7b["trees"]), f"입양 좌석 60 = 지워진 작업공간에 안 붙음 {s7b['trees']}")
            sbg.check(not any(c[1] == 60 for c in closed), f"좌석 60 은 닫지 않음(외부 역할 좌석) {closed}")
            no_offscreen(s7b, "R7b")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R8
            print("== R8(3R blocking 3) 셸 좌석 부서 전출 — 새 좌석 응답 전 목적지 부서 삭제 → 원본 보존")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            pg.click("#btn-ws-new")  # 새 본부 작업공간 = 셸 좌석 50 하나(R6 과 같은 출발)
            pg.wait_for_timeout(2500)
            s8a = pg.evaluate(STATE)
            sbg.check(50 in s8a["panes"], f"본부 셸 좌석 50 보임 {s8a['panes']}")
            lms_i = next(i for i, t in enumerate(s8a["trees"]) if t["socket"] == sbg.LMS)
            hb = pg.query_selector('#root .pane[data-sid="50"] .pane-title-text').bounding_box()
            tb = pg.query_selector_all("#ws-tabs .ws-tab")[lms_i].bounding_box()
            pg.evaluate("() => { window.__calls = []; window.__toasts = []; }")
            pg.mouse.move(hb["x"] + 10, hb["y"] + hb["height"] / 2)
            pg.mouse.down()
            pg.mouse.move(tb["x"] + tb["width"] / 2, tb["y"] + tb["height"] / 2, steps=12)
            pg.mouse.up()
            pg.wait_for_timeout(500)
            ok = next((b for b in pg.query_selector_all(".modal-overlay button") if (b.text_content() or "").strip() == "전출"), None)
            sbg.check(ok is not None, "전출 확인 창의 「전출」 단추")
            if ok:
                ok.click()
                pg.wait_for_timeout(200)
                delete_ws(pg, lms_i)
                pg.wait_for_timeout(5000)
                s8 = pg.evaluate(STATE)
                calls8 = pg.evaluate("() => window.__calls")
                closed = [c for c in calls8 if c[0] == "close_surface"]
                made = [c for c in calls8 if c[0] == "create_surface"]
                sbg.check(any(c[2] == sbg.LMS for c in made), f"(장면 성립) 목적지 LMS 에 새 좌석 생성 요청 {made}")
                sbg.check(not any(c[1] == 50 for c in closed), f"원본 50 = 닫지 않음(원본 보존) {closed}")
                sbg.check(any(50 in t["sids"] for t in s8["trees"] if t["socket"] in (None, sbg.BASE)), f"원본 50 = 본부 트리에 그대로 {s8['trees']}")
                sbg.check(not any(t["socket"] == sbg.LMS for t in s8["trees"]), f"LMS 작업공간 지워짐 {s8['trees']}")
                sbg.check(any("전출 중단" in (t or "") for t in toasts(pg)), f"알림 「전출 중단」 {toasts(pg)}")
                new8 = made_on(pg, sbg.LMS)
                sbg.check(len(new8) == 1 and reclaimed(pg, sbg.LMS, new8[0]), f"(F9) 새 좌석 {new8} = LMS 데몬에 close_surface · 데몬 목록에서 빠짐")
                no_offscreen(s8, "R8")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R9a
            print("== R9a(3R major 4) 새 좌석 닫기 1번 거부 → 삭제 확정 뒤 다시 닫음")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            new_then_delete(pg, {"50": 1})
            pg.wait_for_timeout(5000)
            s9 = pg.evaluate(STATE)
            closed = [c for c in pg.evaluate("() => window.__calls") if c[0] == "close_surface" and c[1] == 50]
            sbg.check(len(closed) == 2, f"close_surface(50) = 거부 1 + 다시 1 {closed}")
            sbg.check(not any(50 in t["sids"] for t in s9["trees"]), f"새 좌석 50 = 어느 트리에도 없음 {s9['trees']}")
            no_offscreen(s9, "R9a")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R9b
            print("== R9b(3R major 4) 새 좌석 닫기 계속 거부 · 같은 데몬 작업공간 없음 → 새 작업공간에 보이게")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            new_then_delete(pg, {"50": 99})
            pg.wait_for_timeout(5000)
            s9b = pg.evaluate(STATE)
            sbg.check(any(t["socket"] in (None, sbg.BASE) and t["sids"] == [50] for t in s9b["trees"]), f"새 좌석 50 = 새 본부 데몬 작업공간에 {s9b['trees']}")
            sbg.check(any("새 작업공간에 두었어요" in (t or "") for t in toasts(pg)), f"알림 {toasts(pg)}")
            no_offscreen(s9b, "R9b")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R9c
            print("== R9c(3R major 4) 부서(LMS)에서 ⌘T → LMS 삭제(데몬 종료 확인) · 새 좌석 닫기 계속 거부 → 런타임 파기")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            s0c = pg.evaluate(STATE)
            lms_i = next(i for i, t in enumerate(s0c["trees"]) if t["socket"] == sbg.LMS)
            pg.query_selector_all("#ws-tabs .ws-tab")[lms_i].click()
            pg.wait_for_timeout(600)
            pg.click('#root .pane[data-sid="21"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.evaluate("() => { window.__calls = []; window.__toasts = []; window.__REFUSE = { 50: 99 }; }")
            pg.keyboard.press("Meta+t")
            pg.wait_for_timeout(200)
            delete_ws(pg, lms_i)
            pg.wait_for_timeout(5000)
            s9c = pg.evaluate(STATE)
            made = [c for c in pg.evaluate("() => window.__calls") if c[0] == "create_surface"]
            sbg.check(any(c[2] == sbg.LMS for c in made), f"(장면 성립) LMS 데몬에 새 좌석 {made}")
            sbg.check(not any(t["socket"] == sbg.LMS for t in s9c["trees"]), f"LMS 작업공간 지워짐 {s9c['trees']}")
            no_offscreen(s9c, "R9c")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R9d
            print("== R9d(3R major 4) 본부 삭제가 좌석 1 닫기 거부로 보존 · 그 「진행 중」 에 새 좌석 닫기도 거부 → 보존된 작업공간에")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            new_then_delete(pg, {"1": 99, "50": 99}, hold=True)
            pg.wait_for_function("() => (window.__made ?? []).length > 0", timeout=8000)  # (F10) 생성 응답 도착 = 명시 대기 지점
            pg.wait_for_timeout(100)
            mid = pg.evaluate(BUSY)
            sbg.check(mid, f"(순서 단언) 새 좌석 응답이 도착한 때 = 삭제 진행 중 {mid}")
            pg.evaluate("() => window.__releaseClose()")
            pg.wait_for_timeout(5500)
            s9d = pg.evaluate(STATE)
            base_now = [t for t in s9d["trees"] if t["socket"] in (None, sbg.BASE)]
            sbg.check(len(base_now) == 1 and 1 in base_now[0]["sids"], f"본부 작업공간 보존(좌석 1 닫기 거부) {s9d['trees']}")
            sbg.check(len(base_now) == 1 and 50 in base_now[0]["sids"], f"새 좌석 50 = 보존된 본부 작업공간에 붙음 {s9d['trees']}")
            no_offscreen(s9d, "R9d")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            # R9e
            print("== R9e(3R major 4) 새 좌석 닫기 계속 거부 · 삭제 「진행 중」 에 판정 → 결과 확정 뒤 새 작업공간에")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            new_then_delete(pg, {"50": 99}, hold=True)
            pg.wait_for_function("() => (window.__made ?? []).length > 0", timeout=8000)  # (F10) 생성 응답 도착 = 명시 대기 지점
            pg.wait_for_timeout(100)
            mid = pg.evaluate(BUSY)
            sbg.check(mid, f"(순서 단언) 새 좌석 응답이 도착한 때 = 삭제 진행 중 {mid}")
            pg.evaluate("() => window.__releaseClose()")
            pg.wait_for_timeout(6500)
            s9e = pg.evaluate(STATE)
            sbg.check(not any(t["socket"] in (None, sbg.BASE) and 1 in t["sids"] for t in s9e["trees"]), f"본부 작업공간(좌석 1~5) 지워짐 {s9e['trees']}")
            sbg.check(any(t["socket"] in (None, sbg.BASE) and t["sids"] == [50] for t in s9e["trees"]), f"새 좌석 50 = 새 본부 데몬 작업공간에 {s9e['trees']}")
            no_offscreen(s9e, "R9e")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R10
            print("== R10(3R 전수 표 · start()) 기동 복원 중 붙이기 사이 본부 작업공간 삭제")
            ctx, pg, errs = boot(js(seats), [list(d) for d in depts], "window.__ATTACH_DELAY = { 1: 4000 };")
            pg.wait_for_function("() => window.__calls.some((c) => c[0] === 'attach_surface' && c[1] === 1)", timeout=15000)
            bi, names = tab_index(pg, lambda n: "LMS" not in n and "영상" not in n)
            sbg.check(bi is not None, f"(장면 성립) 붙이기 대기 중 탭이 이미 보인다 {names}")
            if bi is not None:
                delete_ws(pg, bi)
            pg.wait_for_timeout(9000)
            s10 = pg.evaluate(STATE)
            closed = [c for c in pg.evaluate("() => window.__calls") if c[0] == "close_surface"]
            sbg.check(not any(t["socket"] in (None, sbg.BASE) for t in s10["trees"]), f"본부 작업공간 지워짐 {s10['trees']}")
            sbg.check(not closed, f"복원 좌석은 닫지 않음(외부 좌석) {closed}")
            no_offscreen(s10, "R10")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R10b
            print("== R10b(같은 모양) 기동 복원의 빈 부서 자리 좌석 응답 전 그 부서 삭제")
            seats_nolms = [x for x in js(seats) if x["sock"] != sbg.LMS]
            ctx, pg, errs = boot(seats_nolms, [list(d) for d in depts], "")
            pg.wait_for_function(f"() => window.__calls.some((c) => c[0] === 'create_surface' && c[2] === {json.dumps(sbg.LMS)})", timeout=15000)
            li, names = tab_index(pg, lambda n: "LMS" in n)
            sbg.check(li is not None, f"(장면 성립) 자리 좌석 응답 대기 중 LMS 탭이 보인다 {names}")
            if li is not None:
                delete_ws(pg, li)
            pg.wait_for_timeout(9000)
            s10b = pg.evaluate(STATE)
            sbg.check(not any(t["socket"] == sbg.LMS for t in s10b["trees"]), f"LMS 작업공간 지워짐 {s10b['trees']}")
            new10 = made_on(pg, sbg.LMS)
            sbg.check(bool(new10) and all(reclaimed(pg, sbg.LMS, x) for x in new10), f"(F9) 새 자리 좌석 {new10} = LMS 데몬에 close_surface · 데몬 목록에서 빠짐")
            no_offscreen(s10b, "R10b")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # R0
            print("== R0(ChatGPT F8) 화면 밖 검출기 자가 시험 — 본부 좌석 1(트리에 있음)과 같은 번호의 LMS 좌석 1 출력 듣기가 살아 있으면 잡는다")
            ctx, pg, errs = page(js(seats), [list(d) for d in depts])
            pg.evaluate(f"() => {{ window.__LIVE['sim-out-' + {json.dumps(sbg.LMS)} + '#1'] = 1; }}")
            s0x = pg.evaluate(STATE)
            sbg.check(f"{sbg.LMS}#1" in s0x["offscreen"], f"겹침 검체(본부 1 · LMS 1) = LMS 1 화면 밖으로 잡힘 {s0x['offscreen']}")
            old0 = pg.evaluate("""() => { const lay = JSON.parse(localStorage.getItem('cys-layout-v2') || '{}'); const sids = (n) => !n ? [] : n.type === 'pane' ? [n.sid] : [...sids(n.a), ...sids(n.b)];
              const inTree = new Set((lay.workspaces || []).flatMap((w) => sids(w.tree)));
              return Object.entries(window.__LIVE).filter(([n, c]) => n.startsWith('sim-out-') && c > 0).map(([n]) => +n.split('#').pop()).filter((sid) => !inTree.has(sid)); }""")
            sbg.check(old0 == [], f"(대조) 좌석 번호만 보는 옛 검출기 = 같은 검체를 놓친다 {old0}")
            pg.evaluate(f"() => {{ delete window.__LIVE['sim-out-' + {json.dumps(sbg.LMS)} + '#1']; }}")
            no_offscreen(pg.evaluate(STATE), "R0 대조(검체 뺌)")
            ctx.close()

            # R11
            print("== R11(ChatGPT F1) 기동 복원 첫 좌석 — 활성 LMS 의 생성이 실패하는 사이 본부 탭으로 전환 → 본부 데몬 좌석이 LMS 트리에 붙지 않는다")
            seats_nolms = [x for x in js(seats) if x["sock"] != sbg.LMS]
            ctx, pg, errs = boot(seats_nolms, [list(d) for d in depts], f"window.__CREATE_FAIL = [{json.dumps(sbg.LMS)}];")
            pg.wait_for_timeout(11500)
            li, names = tab_index(pg, lambda n: "LMS" in n)
            bi, _ = tab_index(pg, lambda n: "LMS" not in n and "영상" not in n)
            if li is not None:
                pg.query_selector_all("#ws-tabs .ws-tab")[li].click()  # 활성 = LMS(좌석 0) 로 저장
            pg.wait_for_timeout(800)
            pg.reload()
            # 기동: LMS 빈 자리 좌석 생성 실패(1차) → 활성 LMS 첫 좌석 생성 대기(2차) — 그 대기 중에 본부 탭으로
            pg.wait_for_function(f"() => window.__calls.filter((c) => c[0] === 'create_surface' && c[2] === {json.dumps(sbg.LMS)}).length >= 2", timeout=20000)
            bi, names = tab_index(pg, lambda n: "LMS" not in n and "영상" not in n)
            sbg.check(li is not None and bi is not None, f"(장면 성립) 활성 LMS 첫 좌석 생성 대기 중 본부 탭이 보인다 {names}")
            if bi is not None:
                pg.query_selector_all("#ws-tabs .ws-tab")[bi].click()
            pg.wait_for_timeout(6000)
            s11 = pg.evaluate(STATE)
            lms11 = [t for t in s11["trees"] if t["socket"] == sbg.LMS]
            sbg.check(not s11["wrongSock"], f"다른 데몬 좌석이 붙은 트리 0 {s11['wrongSock']} · 트리 {s11['trees']}")
            sbg.check(all(not t["sids"] for t in lms11), f"LMS 트리 = 비어 있음(본부 좌석 없음) {lms11}")
            no_offscreen(s11, "R11")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    for f in sbg.failures:
        print("  FAIL:", f)
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
