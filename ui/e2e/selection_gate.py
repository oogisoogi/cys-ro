#!/usr/bin/env python3
"""선택 표시·작업 화면 표시 게이트 — TICKET=cysr-1119-s7(SEL+W2 · W5 · W6 · BA5 · 설계 review/1119-DESIGN.md §5·§6·§7).

실제 번들(ui/dist) + __TAURI__ 대역(statusboard_gate.py 꼴) + headless chromium — 데몬·앱 기동 0.
단언(SEL): 좌석 줄 클릭 → 좌석 줄 .sel 1개(aria-current) ∧ 위 묶음 탭 .active 1개 ∧ 그 창 .focused 머리줄 바탕 #1a4f9c ·
  누른 직후 100ms 안 제목 글자 #ffffff(C-08) · 다른 좌석 → 표시 이동(이전 것 0) · 넓게 보기 풀기 → 유지 · 3초 다시 그리기 뒤 유지 ·
  부서 2개에서 같은 번호(sid) 줄 표시 1개(C-09) · 창 포커스 이동 20회 = resize_surface 0(C-17) · 부서 카드(W2) 바탕·막대.
단언(W5): 막힌 좌석 창에만 「승인 기다림 · N분」 알약 · 풀리면 다음 갱신 안에 사라짐.
단언(BA5): 대기·막힘 줄 = 경과 글 · 작업 중 줄 = 없음 · 216px 사이드바 줄 가로 넘침 0.
단언(W6): 토스트 글 13px 미만 0 · 왼쪽 막대 3px(색 = 종류 테두리색) · 150ms 등장 · 확인 창이 떠 있으면 위로 비켜 섬(#toasts 회피 그대로) ·
  1024×700 넘침 0. 콘솔 오류 0.
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/selection_gate.py [캡처폴더]
  (SELECTION_GATE_DIST=<폴더> = 다른 번들로 돌림 — 뮤턴트 대조용)
"""
import http.server
import json
import os
import re
import sys
import threading
from pathlib import Path

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ.get("SELECTION_GATE_DIST") or (UI / "dist"))


def evidence_dir(*parts: str) -> Path:
    """캡처 기본 자리 = 작업트리 밖(GATE_EVIDENCE_DIR 또는 TMPDIR/cys-gate-evidence) — 게이트를 돌려도 작업트리가 바뀌지 않는다."""
    import tempfile

    base = Path(os.environ.get("GATE_EVIDENCE_DIR") or Path(tempfile.gettempdir()) / "cys-gate-evidence")
    return base.joinpath(*parts)


OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else evidence_dir("evidence-1119-s7")
if OUT.suffix == ".png":  # CI 는 캡처 파일 경로 하나를 넘긴다(cc_popover_z_gate 꼴) — 그 옆 폴더에 둔다
    OUT = OUT.with_suffix("")
BASE = "/sandbox/cys.sock"
LMS = "/sandbox/cys-dept-lms/cys.sock"

# (socket, sid, no, role, cwd, act, raw, approval, task, ctx, stable_age_secs)
SEATS = [
    (BASE, 1, 900, "master", "/u/axdev", "working", "active", False, None, 41, 5),
    (BASE, 3, 931, "worker", "/u/axdev/site", "working", "active", False, "홈 화면 수정", 38, 5),
    (BASE, 4, 932, "worker-2", "/u/axdev/site", "waiting", "idle", False, "교역자 소개", 47, 200),
    (BASE, 6, 934, "worker-4", "/u/axdev/site", "waiting_for_input", "permission", False, "행사 포스터", 52, 125),
    (BASE, 5, 933, "worker-3", "/u/axdev/lms", "working", "active", False, "6강 발행", 29, 5),
    (LMS, 1, 951, "master", "/u/axdev/lms", "working", "active", False, None, 30, 5),
    (LMS, 3, 952, "worker", "/u/axdev/lms", "waiting", "idle", False, "같은 번호 좌석", 52, 40),
]
DEPTS = [("lms", LMS, "LMS")]

SHIM = r"""
(() => {
  window.__SEATS = __SEATS__;
  const DEPTS = __DEPTS__, BASE = '__BASE__';
  const listeners = {}; let seq = 0;
  window.__CALLS = {};
  const act = (s) => s.act === 'unknown' ? { state: 'unknown', raw: 'unknown', reason: 'no observation', retained: false }
    : { state: s.act, raw: s.raw, reason: 'sim', retained: false, display_epoch: 'e1', observation_seq: ++seq,
        observed_age_secs: 0.2, last_positive_age_secs: null, stable_age_secs: s.stable, family: 'claude', grammar_revision: null, consecutive_rejections: 0 };
  const mine = (sock) => window.__SEATS.filter((s) => s.sock === (sock ?? BASE));
  const row = (s) => ({ surface_id: s.sid, display_no: s.no, title: `${s.no} · Opus · ${s.cwd.split('/').pop()}`, role: s.role, cwd: s.cwd, live_cwd: s.cwd,
    exited: false, agent: 'claude', agent_alive: true, usage: { ctx_pct: s.ctx, source: 'statusline', updated_at: Date.now() / 1000 }, display_activity: act(s) });
  const respond = (cmd, a) => {
    window.__CALLS[cmd] = (window.__CALLS[cmd] ?? 0) + 1;
    switch (cmd) {
      case 'daemon_status': return { daemon_pid: 4242, socket_path: BASE, version: '1.1.18', app_version: '1.1.18' };
      case 'app_version': return '1.1.18';
      case 'default_socket_slug': return 'base';
      case 'list_depts': return { depts: Object.fromEntries(DEPTS.map(([k, sock, dn]) => [k, { socket: sock, display_name: dn }])) };
      case 'dept_tombstones': return [];
      case 'fresh_start_check': return { ask: false };
      case 'resolve_list_endpoints': return a.endpoints;
      case 'list_surfaces': return { surfaces: mine(a.socket).map(row) };
      case 'org_status': return { surfaces: mine(a.socket).map((s) => ({ surface_id: s.sid, role: s.role, exited: false, idle_secs: 1, agent_alive: true,
        usage: row(s).usage, status: s.task ? { state: 'working', context_pct: null, task: s.task, age_secs: 5 } : null })), feed: { pending: 0 } };
      case 'feed_list_all': return { sockets: [{ socket: BASE, dept: null, ok: true, items: [] }] };
      case 'usage_named_reporters': return { named: [] };
      case 'usage_accounts_all': return { accounts: [] };
      case 'attach_surface': return { output_event: 'sim-out-' + a.surfaceId, exited_event: 'sim-exit-' + a.surfaceId };
      default: return null;
    }
  };
  window.__TAURI__ = {
    core: { invoke: (cmd, args) => new Promise((res, rej) => { try { res(respond(cmd, args ?? {})); } catch (e) { rej(e); } }) },
    event: { listen: (name, h) => { (listeners[name] ??= []).push(h); return Promise.resolve(() => {}); } },
  };
})();
"""

# 지금 보이는(작업공간) 좌석 줄 호스트만 — 상황판·부서별 수 호스트 제외
HOSTS = '.ws-seats[data-seat-host]:not([data-seat-host="board"]):not([data-seat-host^="n"])'

STATE_JS = r"""
() => {
  const HOSTS = '__HOSTS__';
  const sel = [...document.querySelectorAll(`${HOSTS} .ws-seat.sel`)];
  const bar = document.querySelector('#root .group-tabbar');
  const act = bar ? [...bar.querySelectorAll('.group-tab.active')] : [];
  const foc = [...document.querySelectorAll('#root .pane.focused')];
  const title = foc[0]?.querySelector('.pane-title');
  const text = foc[0]?.querySelector('.pane-title-text');
  const wsAct = document.querySelector('#ws-tabs .ws-tab.active');
  return {
    sel: sel.map((e) => ({ sid: +e.dataset.sid, host: e.closest('[data-seat-host]').dataset.seatHost, cur: e.getAttribute('aria-current') })),
    ariaCurrent: document.querySelectorAll('[aria-current="true"].ws-seat').length,
    tabs: act.map((b) => ({ name: b.querySelector('.group-tab-name')?.textContent, zoomed: b.classList.contains('zoomed'), zoomMark: !!b.querySelector('.group-tab-zoom'), sel: b.getAttribute('aria-selected') })),
    tabCount: bar ? bar.querySelectorAll('.group-tab').length : 0,
    focused: foc.map((p) => +p.dataset.sid),
    headBg: title ? getComputedStyle(title).backgroundColor : null,
    titleColor: text ? getComputedStyle(text).color : null,
    focusOutline: foc[0] ? getComputedStyle(foc[0]).outlineWidth + ' ' + getComputedStyle(foc[0]).outlineColor : null,
    wsBg: wsAct ? getComputedStyle(wsAct).backgroundColor : null,
    wsBar: wsAct ? getComputedStyle(wsAct).borderLeftColor : null,
    wsName: wsAct?.querySelector('.ws-name') ? getComputedStyle(wsAct.querySelector('.ws-name')).color : null,
    pills: [...document.querySelectorAll('#root .pane .pane-pill')].map((p) => ({ sid: +p.closest('.pane').dataset.sid, text: p.textContent, blocked: p.closest('.pane').classList.contains('blocked') })),
    blockedPanes: [...document.querySelectorAll('#root .pane.blocked')].map((p) => +p.dataset.sid),
    ages: Object.fromEntries([...document.querySelectorAll(`${HOSTS} .ws-seat`)].map((r) => [r.closest('[data-seat-host]').dataset.seatHost + '#' + r.dataset.sid, r.querySelector('.ws-seat-age')?.textContent ?? null])),
    rowOver: [...document.querySelectorAll(`${HOSTS} .ws-seat`)].filter((r) => r.scrollWidth > r.clientWidth + 1).map((r) => r.dataset.sid),
    docOver: document.documentElement.scrollWidth > innerWidth,
    resizes: window.__CALLS['resize_surface'] ?? 0,
    curWs: document.querySelector('#ws-tabs .ws-tab.active')?.dataset.wsId ?? null, // 좌석 줄 호스트 열쇠 = 부서 카드 data-ws-id(호스트는 카드 바로 뒤 형제)
  };
}
""".replace("__HOSTS__", HOSTS)

TOAST_JS = r"""
() => {
  const box = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = 'toast watchdog';
  el.innerHTML = '<span class="toast-name"></span><span class="toast-detail"></span><button class="toast-x">×</button><details class="toast-raw" open><summary>자세히</summary><div class="toast-raw-text"></div></details>';
  el.querySelector('.toast-name').textContent = 'pane 종료 실패';
  el.querySelector('.toast-detail').textContent = '데몬이 닫힘을 확인하지 않아 창을 그대로 두었습니다 — 다시 닫아 보세요.';
  el.querySelector('.toast-raw-text').textContent = 'Error: close_surface timeout';
  box.appendChild(el);
  const small = [...el.querySelectorAll('*')].concat([el]).filter((n) => [...n.childNodes].some((c) => c.nodeType === 3 && c.textContent.trim()))
    .map((n) => ({ cls: n.className, px: parseFloat(getComputedStyle(n).fontSize) })).filter((x) => x.px < 13);
  const cs = getComputedStyle(el);
  const before = getComputedStyle(box).top;
  const ov = document.createElement('div'); ov.className = 'modal-overlay confirm-overlay'; document.body.appendChild(ov);
  const during = getComputedStyle(box).top;
  ov.remove();
  return { small, size: cs.fontSize, lh: cs.lineHeight, left: cs.borderLeftWidth, leftColor: cs.borderLeftColor, topColor: cs.borderTopColor,
    anim: cs.animationDuration, before, during, over: document.documentElement.scrollWidth > innerWidth || el.getBoundingClientRect().right > innerWidth };
}
"""

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(f"  [{'PASS' if c else 'FAIL'}] {m}")
    if not c:
        failures.append(m)


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], task=s[8], ctx=s[9], stable=s[10]) for s in SEATS]
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe, args=["--use-mock-keychain"]) if exe else p.chromium.launch(args=["--use-mock-keychain"])
            ctx = br.new_context(viewport={"width": 1280, "height": 800})
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
            pg.add_init_script(SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", json.dumps(DEPTS)).replace("__BASE__", BASE))
            pg.goto(f"http://127.0.0.1:{port}/index.html")
            pg.wait_for_timeout(11500)
            st = pg.evaluate(STATE_JS)
            cur = st["curWs"]
            print(f"== 첫 화면 · 지금 작업공간 호스트 {cur} · 탭 {st['tabCount']}")
            check(cur is not None and st["tabCount"] >= 2, f"묶음 탭 2개 이상 + 지금 작업공간 좌석 줄 있음 ({cur} · {st['tabCount']})")

            # ① 좌석 줄 클릭(사이드바로 고름 = 넓게 보기) → 세 곳 표시
            row = f'{HOSTS}[data-seat-host="{cur}"] .ws-seat[data-sid="4"]'
            pg.click(row)
            pg.wait_for_timeout(100)  # (C-08) 누른 직후 100ms
            st = pg.evaluate(STATE_JS)
            check(st["titleColor"] == "rgb(255, 255, 255)", f"누른 직후 100ms 제목 글자 #fff ({st['titleColor']})")
            pg.wait_for_timeout(300)
            st = pg.evaluate(STATE_JS)
            pg.screenshot(path=str(OUT / "sel-pick-4.png"))
            check([s["sid"] for s in st["sel"]] == [4] and st["sel"][0]["host"] == cur and st["sel"][0]["cur"] == "true" and st["ariaCurrent"] == 1,
                  f"좌석 줄 .sel 1개 = 4 · aria-current ({st['sel']} · {st['ariaCurrent']})")
            check(len(st["tabs"]) == 1 and st["tabs"][0]["name"] == "site", f"위 탭 .active 1개 = site ({st['tabs']})")
            check(bool(st["tabs"]) and st["tabs"][0]["zoomed"] and st["tabs"][0]["zoomMark"] and st["tabs"][0]["sel"] == "true", f"넓게 보기 = active zoomed + ⤢ ({st['tabs']})")
            check(st["focused"] == [4] and st["headBg"] == "rgb(26, 79, 156)", f"창 4 .focused 머리줄 바탕 #1a4f9c ({st['focused']} · {st['headBg']})")
            check(st["focusOutline"] == "2px rgb(88, 166, 255)", f"창 테두리 2px #58a6ff(outline) ({st['focusOutline']})")
            check(st["wsBg"] == "rgb(31, 38, 48)" and st["wsBar"] == "rgb(47, 129, 247)" and st["wsName"] == "rgb(255, 255, 255)",
                  f"부서 카드(W2) 바탕 #1f2630 · 왼쪽 막대 accent · 이름 #fff ({st['wsBg']} · {st['wsBar']} · {st['wsName']})")

            # ② 다른 좌석 → 표시 이동(이전 것 0) · C-09(부서 LMS 의 같은 sid 3 줄은 켜지지 않음)
            pg.click(f'{HOSTS}[data-seat-host="{cur}"] .ws-seat[data-sid="3"]')
            pg.wait_for_timeout(400)
            st = pg.evaluate(STATE_JS)
            check([s["sid"] for s in st["sel"]] == [3] and st["sel"][0]["host"] == cur, f"다른 좌석 → .sel 이동 · 이전 0 · 다른 부서 같은 sid 줄 표시 0 ({st['sel']})")
            check(st["focused"] == [3], f"창 3 포커스 ({st['focused']})")

            # ③ 넓게 보기 풀기(같은 줄 다시) → 표시 유지 · 탭 active(zoomed 아님)
            pg.click(f'{HOSTS}[data-seat-host="{cur}"] .ws-seat[data-sid="3"]')
            pg.wait_for_timeout(400)
            st = pg.evaluate(STATE_JS)
            check([s["sid"] for s in st["sel"]] == [3] and len(st["tabs"]) == 1 and not st["tabs"][0]["zoomed"], f"넓게 보기 풀기 → .sel 유지 · 탭 active 1(zoomed 아님) ({st['sel']} · {st['tabs']})")

            # ④ 3초 다시 그리기 뒤에도 유지
            pg.wait_for_timeout(3500)
            st = pg.evaluate(STATE_JS)
            check([s["sid"] for s in st["sel"]] == [3] and len(st["tabs"]) == 1 and st["focused"] == [3], f"3초 다시 그리기 뒤 유지 ({st['sel']} · {st['tabs']} · {st['focused']})")
            pg.screenshot(path=str(OUT / "sel-after-tick.png"))

            # ⑤ 창 포커스 이동 20회 = resize_surface 0(C-17 · 테두리 두께 무변경)
            r0 = st["resizes"]
            for k in range(20):
                pg.mouse.click(*(lambda b: (b["x"] + b["width"] / 2, b["y"] + b["height"] / 2))(pg.locator(f'#root .pane[data-sid="{4 if k % 2 == 0 else 3}"] .term-host').bounding_box()))
                pg.wait_for_timeout(30)
            pg.wait_for_timeout(500)
            st = pg.evaluate(STATE_JS)
            check(st["resizes"] - r0 == 0, f"포커스 이동 20회 동안 resize_surface {st['resizes'] - r0}")
            check([s["sid"] for s in st["sel"]] == [3] and st["focused"] == [3], f"창 클릭으로도 좌석 줄 표시가 따라감 ({st['sel']} · {st['focused']})")

            # ⑥ W5 막힌 창 알약 + BA5 경과
            check(len(st["pills"]) == 1 and st["pills"][0]["sid"] == 6 and st["pills"][0]["blocked"] and st["pills"][0]["text"] == "승인 기다림 · 2분",
                  f"막힌 창(6)에만 알약 「승인 기다림 · 2분」 ({st['pills']})")
            ages = st["ages"]
            check(ages.get(f"{cur}#6") == "2분 전" and ages.get(f"{cur}#4") == "3분 전", f"대기·막힘 줄 경과 = agoText ({ages})")
            check(ages.get(f"{cur}#3") is None and ages.get(f"{cur}#5") is None, f"작업 중 줄 = 경과 없음 ({ages})")
            check(not st["rowOver"] and not st["docOver"], f"216px 사이드바 줄 가로 넘침 0 ({st['rowOver']})")
            pg.screenshot(path=str(OUT / "w5-blocked.png"))
            pg.evaluate("() => { const s = window.__SEATS.find((x) => x.sid === 6 && x.sock === '%s'); s.act = 'waiting'; s.raw = 'idle'; s.stable = 1; }" % BASE)
            pg.wait_for_timeout(3600)
            st = pg.evaluate(STATE_JS)
            check(not st["pills"] and 6 not in st["blockedPanes"], f"풀리면 다음 갱신 안에 알약 사라짐 ({st['pills']} · {st['blockedPanes']})")
            check(st["ages"].get(f"{cur}#6") == "방금", f"풀린 좌석 경과 = 방금 ({st['ages'].get(f'{cur}#6')})")
            check(not errs, f"콘솔 오류 0 {errs[:3]}")
            ctx.close()

            # ⑦ W6 토스트 @ 1024×700
            ctx = br.new_context(viewport={"width": 1024, "height": 700})
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", json.dumps(DEPTS)).replace("__BASE__", BASE))
            pg.goto(f"http://127.0.0.1:{port}/index.html")
            pg.wait_for_timeout(4000)
            t = pg.evaluate(TOAST_JS)
            pg.screenshot(path=str(OUT / "w6-toast-1024.png"))
            check(not t["small"] and t["size"] == "14px", f"토스트 글 13px 미만 0 · 본문 14px ({t['small']} · {t['size']})")
            check(t["lh"] == f"{14 * 1.45:.1f}px" or t["lh"] == "20.3px", f"줄 높이 1.45 ({t['lh']})")
            check(t["left"] == "3px" and t["leftColor"] == t["topColor"], f"왼쪽 막대 3px · 색 = 종류 테두리색 ({t['left']} · {t['leftColor']} = {t['topColor']})")
            check(t["anim"] == "0.15s", f"150ms 등장 ({t['anim']})")
            check(t["during"] == "56px" and t["before"] != "56px", f"확인 창이 떠 있으면 위로 비켜 섬(#toasts 회피 그대로) ({t['before']} → {t['during']})")
            check(not t["over"], "1024×700 넘침 0")
            check(not errs, f"콘솔 오류 0 {errs[:3]}")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
