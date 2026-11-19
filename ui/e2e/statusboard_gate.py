#!/usr/bin/env python3
"""상황판 시안 게이트 — TICKET=cysr-tabs-sidebar-impl 조각 1d(master#8ef1fcd7 · 수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역. 캡처: 부서 1개 × 워커 0·1·7 × (가)(나) · 부서 3개 × (가) · 1920·1280.
단언: 부서 1개 = 「본부」 카드 없음(상황판이 대신) · 부서 여럿 = 상황판(합) + 카드 + 카드 아래 부서별 수 ·
  상황판 수 = 좌석 줄 상태 수(같은 판정) · 0 은 흐림·누를 수 없음 · 숫자 누름 = 그 상태 좌석으로(차례로) ·
  (나) = 한도 한 줄 · 새 단추 0(상단 단추 수 그대로) · 가로 넘침 0 · 콘솔 오류 0.
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/statusboard_gate.py [캡처폴더]
"""
import http.server
import json
import os
import re
import sys
import threading
from pathlib import Path

UI = Path(__file__).resolve().parent.parent
DIST = UI / "dist"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else UI.parent / "docs" / "evidence-tabs-sidebar" / "1d"
BASE = "/sandbox/cys.sock"
LMS = "/sandbox/cys-dept-lms/cys.sock"
VID = "/sandbox/cys-dept-video/cys.sock"

# (socket, sid, no, role, cwd, act, raw, approval, self, task, ctx)
W7 = [
    (BASE, 1, 900, "master", "/u/axdev", "working", "active", False, None, None, 41),
    (BASE, 2, 901, "cso", "/u/axdev/cso", "waiting", "idle", False, None, None, 23),
    (BASE, 3, 931, "worker", "/u/axdev/site", "working", "active", False, "working", "홈 화면 수정", 38),
    (BASE, 4, 932, "worker-2", "/u/axdev/site", "waiting", "idle", False, "waiting", "교역자 소개", 47),
    (BASE, 5, 933, "worker-3", "/u/axdev/site", "working", "active", False, None, "모바일 점검", 29),
    (BASE, 6, 934, "worker-4", "/u/axdev/lms", "working", "active", True, None, "6강 발행", 52),
    (BASE, 7, 935, "worker-5", "/u/axdev/lms", "waiting_for_input", "permission", False, None, "묶음 머리 수정", 63),
    (BASE, 8, 936, "worker-6", "/u/axdev/video", "unknown", "unknown", False, None, None, None),
    (BASE, 9, 937, "worker-7", "/u/axdev/video", "waiting", "idle", False, "done", "스킬 초안", 84),
]
SCEN = {
    "dept1-workers1": (W7[:1] + [W7[2]], []),
    "dept1-workers7": (W7, []),
    "dept3": (
        W7[:5] + [
            (LMS, 21, 951, "master", "/u/axdev/lms", "working", "active", False, None, None, 30),
            (LMS, 22, 952, "worker", "/u/axdev/lms", "waiting_for_input", "permission", False, None, "6강 발행", 52),
            (VID, 31, 961, "master", "/u/axdev/video", "waiting", "idle", False, None, None, 12),
            (VID, 32, 962, "worker", "/u/axdev/video", "unknown", "unknown", False, None, None, None),
        ],
        [("lms", LMS, "LMS"), ("video", VID, "영상 자산")],
    ),
}

SHIM = r"""
(() => {
  const SEATS = __SEATS__, DEPTS = __DEPTS__, BASE = '__BASE__';
  const listeners = {}; let seq = 0;
  const act = (s) => s.act === 'unknown' ? { state: 'unknown', raw: 'unknown', reason: 'no observation', retained: false }
    : { state: s.act, raw: s.raw, reason: 'sim', retained: false, display_epoch: 'e1', observation_seq: ++seq,
        observed_age_secs: 0.2, last_positive_age_secs: null, stable_age_secs: null, family: 'claude', grammar_revision: null, consecutive_rejections: 0 };
  const mine = (sock) => SEATS.filter((s) => s.sock === (sock ?? BASE));
  const row = (s) => ({ surface_id: s.sid, display_no: s.no, title: `${s.no} · Opus · ${s.cwd.split('/').pop()}`, role: s.role, cwd: s.cwd, live_cwd: s.cwd,
    exited: false, agent: 'claude', agent_alive: true, usage: s.ctx == null ? null : { ctx_pct: s.ctx, source: 'statusline', updated_at: Date.now() / 1000 }, display_activity: act(s) });
  const respond = (cmd, a) => {
    switch (cmd) {
      case 'daemon_status': return { daemon_pid: 4242, socket_path: BASE, version: '1.1.14', app_version: '1.1.14' };
      case 'app_version': return '1.1.14';
      case 'default_socket_slug': return 'base';
      case 'list_depts': return { depts: Object.fromEntries(DEPTS.map(([k, sock, dn]) => [k, { socket: sock, display_name: dn }])) };
      case 'dept_tombstones': return [];
      case 'fresh_start_check': return { ask: false };
      case 'resolve_list_endpoints': return a.endpoints;
      case 'list_surfaces': return { surfaces: mine(a.socket).map(row) };
      case 'org_status': return { surfaces: mine(a.socket).map((s) => ({ surface_id: s.sid, role: s.role, exited: false, idle_secs: s.act === 'unknown' ? 999 : 1, agent_alive: true,
        usage: row(s).usage, status: s.self || s.task ? { state: s.self ?? 'working', context_pct: null, task: s.task, age_secs: 5 } : null })),
        feed: { pending: mine(a.socket).filter((s) => s.approval).length + ((a.socket ?? BASE) === BASE ? (window.__EXTRA_PENDING ?? 0) : 0) } };
      case 'feed_list_all': return { sockets: [{ socket: BASE, dept: null, ok: true,
        items: [...SEATS.filter((s) => s.approval).map((s, i) => ({ request_id: 'r' + i, kind: 'approval', status: 'pending', surface_id: s.sid, title: 't', body: 'b' })),
          ...Array.from({ length: window.__EXTRA_PENDING ?? 0 }, (_, i) => ({ request_id: 'x' + i, kind: 'approval', status: 'pending', surface_id: null, title: '워커 승인 요청', body: 'b' }))] }] };
      case 'usage_named_reporters': return { named: [] };
      case 'usage_accounts_all': return { accounts: [{ account_id: 'acct-1', label: 'sim@example.com', provider: 'claude', updated_at: Date.now() / 1000,
        rate: [{ label: '7d', used_pct: 86, resets_at: Date.now() / 1000 + 2 * 86400 + 3 * 3600 + 120, stale: false }] }] };
      case 'attach_surface': return { output_event: 'sim-out-' + a.surfaceId, exited_event: 'sim-exit-' + a.surfaceId };
      default: return null;
    }
  };
  window.__TAURI__ = {
    core: { invoke: (cmd, args) => new Promise((res, rej) => { try { res(respond(cmd, args ?? {})); } catch (e) { rej(e); } }) },
    event: { listen: (name, h) => { (listeners[name] ??= []).push(h); return Promise.resolve(() => {}); } },
  };
  window.__emit = (name, payload) => { for (const h of listeners[name] ?? []) h({ payload }); return (listeners[name] ?? []).length; };
})();
"""

JS = r"""
() => {
  const n = (st) => +(document.querySelector(`[data-seat-host="board"] .ws-board-n.st-${st} .ws-board-num`)?.textContent ?? -1); // (master#fcbc46fb ②) 버튼엔 글자 라벨도 있다 — 수 칸만 읽는다
  const rowsBy = (st) => document.querySelectorAll(`.ws-seats[data-seat-host]:not([data-seat-host="board"]):not([data-seat-host^="n"]) .ws-seat.st-${st}:not(.named)`).length;
  const states = ['working', 'idle', 'blocked', 'unknown'];
  return { cards: document.querySelectorAll('#ws-tabs .ws-tab').length, hq: [...document.querySelectorAll('#ws-tabs .ws-name')].map((e) => e.textContent),
    board: states.map(n), rows: states.map(rowsBy), zeroDisabled: [...document.querySelectorAll('.ws-board-n.zero')].every((b) => b.disabled),
    limit: document.querySelector('.ws-board-limit-text')?.textContent ?? null,
    limitCut: (() => { const t = document.querySelector('.ws-board-limit-text'), b = document.querySelector('.ws-board-limit'); return !t || !b ? null : t.scrollWidth > t.clientWidth + 1 || b.scrollWidth > b.clientWidth + 1 || t.getBoundingClientRect().right > b.getBoundingClientRect().right + 1; })(),
    limitTitle: document.querySelector('.ws-board-limit')?.title ?? null,
    labels: [...document.querySelectorAll('[data-seat-host="board"] .ws-board-n')].map((b) => b.querySelector('.ws-board-label')?.textContent ?? null),
    labelCut: [...document.querySelectorAll('[data-seat-host="board"] .ws-board-label')].some((l) => l.scrollWidth > l.clientWidth + 1),
    approvalsChip: document.querySelector('.ws-board-approvals')?.textContent ?? null, perDept: document.querySelectorAll('[data-seat-host^="n"] .ws-board-counts').length,
    usageInBoard: !!document.querySelector('[data-seat-host="board"] .ws-board-more #ws-usage'), usageShown: (() => { const m = document.querySelector('.ws-board-more'); return !!m && !m.hidden && document.querySelectorAll('#ws-usage .wsu-rate').length > 0; })(),
    usageCount: document.querySelectorAll('#ws-usage').length,
    pos: (() => { const b = document.querySelector('[data-seat-host="board"]'); if (!b) return null; const r = b.getBoundingClientRect(); const nav = document.getElementById('wsbar').getBoundingClientRect();
      return { inTabs: b.parentElement?.id === 'ws-tabs', bottomGap: Math.round(nav.bottom - r.bottom), visible: r.bottom <= innerHeight + 1 && r.top >= 0 }; })(),
    topbar: document.querySelectorAll('#topbar button:not([hidden])').length,
    docOver: document.documentElement.scrollWidth > innerWidth, tabsOver: (() => { const t = document.getElementById('ws-tabs'); return t.scrollWidth > t.clientWidth + 1; })() };
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
    topbar_base = None
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            for name, (seats, depts) in SCEN.items():
                js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in seats]
                combos = [("top", "0"), ("top", "1"), ("bottom", "0"), ("bottom", "1")] if name.startswith("dept1") else [("top", "0")]
                for pos, op in combos:
                    var = "1"
                    for w, hgt in ((1920, 1200), (1280, 800)):
                        tag = f"{pos}-{'open' if op == '1' else 'closed'}"
                        print(f"== {name} ({tag}) @ {w}")
                        ctx = br.new_context(viewport={"width": w, "height": hgt})
                        pg = ctx.new_page()
                        errs: list[str] = []
                        pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                        pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
                        pg.add_init_script(f"localStorage.setItem('cys-status-board', '{var}'); localStorage.setItem('cys-status-board-pos', '{pos}'); localStorage.setItem('cys-status-board-open', '{op}');")
                        pg.add_init_script(SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", json.dumps(depts)).replace("__BASE__", BASE))
                        pg.goto(f"http://127.0.0.1:{port}/index.html")
                        pg.wait_for_timeout(11500)
                        st = pg.evaluate(JS)
                        pg.screenshot(path=str(OUT / f"{name}-{tag}-{w}.png"))
                        if var == "0":
                            topbar_base = st["topbar"]
                            check(st["cards"] == 1, f"노브 끔 = 1.1.14 처럼 카드 1개 ({st['cards']})")
                        else:
                            if topbar_base is not None:
                                check(st["topbar"] == topbar_base, f"새 단추 0(상단 단추 {st['topbar']} = 끔 {topbar_base})")
                            if depts:
                                check(st["cards"] == 3 and st["perDept"] == 3, f"부서 3개 = 카드 3 + 부서별 수 3 ({st['cards']}·{st['perDept']})")
                            else:
                                check(st["cards"] == 0, f"부서 1개 = 본부 카드 없음 ({st['cards']} · {st['hq']})")
                            check(st["board"] == st["rows"], f"상황판 수 = 좌석 줄 상태 수 {st['board']} vs {st['rows']}")
                            check(st["zeroDisabled"], "0 인 상태 = 흐림·누를 수 없음")
                            # (master#fcbc46fb ③) 퍼센트 먼저 · 초기화 요일·시각 다음 · 글자 중간 잘림 0 · 전문 = 툴팁
                            check(bool(re.fullmatch(r"86% · [일월화수목금토] \d\d:\d\d 초기화", st["limit"] or "")), f"둘째 줄 한도 한 줄 {st['limit']}")
                            check(st["limitCut"] is False, f"한도 한 줄 잘림 0 @ {w}")
                            check((st["limitTitle"] or "").startswith("7일 한도 86% 사용 · ") and "2일 3시간 남음" in (st["limitTitle"] or ""), f"한도 전문 = 툴팁 {st['limitTitle']!r}")
                            # (master#fcbc46fb ②) 수 옆 글자 라벨 항상 · (master#ec9c8b30 ③) 좌석에 걸린 승인(934)은 ◆ 에만 — 상황판 칩 없음
                            check(st["labels"] == ["작업 중", "대기", "막힘", "모름"] and not st["labelCut"], f"상황판 수 옆 글자 {st['labels']}")
                            check(st["approvalsChip"] is None, f"좌석 밖 승인 요청 0 = 칩 없음(좌석 승인은 ◆ 막힘에) {st['approvalsChip']}")
                            check(st["usageInBoard"] and st["usageCount"] == 1, "사용량 칸 = 상황판 안 한 곳뿐(아래 따로 없음)")
                            check(st["usageShown"] == (op == "1"), f"펼침 {op} = 사용량 막대 보임 {st['usageShown']}")
                            check(st["pos"]["inTabs"] == (pos == "top"), f"위치 {pos} {st['pos']}")
                            check(st["pos"]["visible"], f"상황판 화면 안(가려지지 않음) {st['pos']}")
                            if pos == "bottom":
                                check(abs(st["pos"]["bottomGap"]) <= 2, f"아래 = 막대 맨 아래에 붙음 {st['pos']}")
                            if name == "dept1-workers7" and var == "1" and w == 1920:
                                pg.click('[data-seat-host="board"] .ws-board-n.st-blocked')
                                pg.wait_for_timeout(300)
                                f1 = pg.evaluate("() => [...document.querySelectorAll('#root .pane')].map((p) => +p.dataset.sid).sort((a,b)=>a-b)")
                                check(6 in f1 and 7 in f1, f"▲ 누름 = 막힌 좌석의 묶음(lms)으로 {f1}")
                        check(not st["docOver"] and not st["tabsOver"], "가로 넘침 0")
                        check(not errs, f"콘솔 오류 0 {errs[:3]}")
                        ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
