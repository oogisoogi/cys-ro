#!/usr/bin/env python3
"""좌석 줄(왼쪽 막대) 게이트 — TICKET=cysr-tabs-sidebar-impl 조각 1b (수동 실행 — CI 미배선).

실제 번들(ui/dist) + __TAURI__ 대역(가짜 데몬 응답)으로 사이드바를 띄워, 좌석 0·1·7 에서
  ① 부서 카드 아래 좌석 줄 수 = 화면 좌석 수(+ 이름 보고자 0)
  ② 상태 모양 = 데몬 값 그대로(작업 중 ● · 대기 ◆ · 막힘 ▲(화면 입력 대기 또는 승인 피드) · 모름 ○)
  ③ 「확인」 꼬리표 = 자기보고 waiting/done 일 때만 · 막힘 = 「승인 창」
  ④ 묶음 머리 = 묶음 2개 이상일 때만(좌석 0·1 = 머리 없음)
  ⑤ 옛 「페인 CTX」 머리 없음
  ⑥ 1920·1280 폭 모두 문서·사이드바 가로 넘침 0 · 콘솔 오류 0
을 단언하고 캡처를 남긴다.

사전: sh ui/build.sh · playwright(파이썬) + chromium
실행: cys run -- <playwright 있는 python3> ui/e2e/seatrows_gate.py [캡처폴더]   # exit 0 = PASS
"""
import http.server
import json
import os
import sys
import threading
from pathlib import Path

UI = Path(__file__).resolve().parent.parent
DIST = UI / "dist"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else UI.parent / "docs" / "evidence-tabs-sidebar" / "1b"

# 좌석 정의: (sid, display_no, role, cwd, activity_state, raw, approval, self_state, task, ctx)
SCENARIOS = {
    "workers0": [(1, 900, "master", "/Users/u/axdev", "waiting", "idle", False, None, None, 41)],
    "workers1": [
        (1, 900, "master", "/Users/u/axdev", "working", "active", False, None, None, 41),
        (2, 931, "worker", "/Users/u/axdev/site", "waiting", "idle", False, None, None, None),
    ],
    "workers7": [
        (1, 900, "master", "/Users/u/axdev", "working", "active", False, None, None, 41),
        (2, 901, "cso", "/Users/u/axdev/cso", "waiting", "idle", False, None, None, 23),
        (3, 931, "worker", "/Users/u/axdev/site", "working", "active", False, "working", "홈 화면 수정", 38),
        (4, 932, "worker-2", "/Users/u/axdev/site", "waiting", "idle", False, "waiting", "교역자 소개", 47),
        (5, 933, "worker-3", "/Users/u/axdev/site", "working", "active", False, None, "모바일 점검", 29),
        (6, 934, "worker-4", "C:\\Users\\u\\work\\lms", "working", "active", True, None, "6강 발행", 52),
        (7, 935, "worker-5", "C:\\Users\\u\\work\\lms", "waiting_for_input", "permission", False, None, "묶음 머리 수정", 63),
        (8, 936, "worker-6", "/Users/u/axdev/video", "unknown", "unknown", False, None, None, None),  # 관측 없음 + 자기보고 없음 = 모름(○) — 자기보고 working 이 있으면 역할 점과 같이 작업 중이 된다
        (9, 937, "worker-7", "/Users/u/axdev/video", "waiting", "idle", False, "done", "스킬 초안", 84),
    ],
}
# 기대 모양(sid → 모양 · 꼬리표)
EXPECT7 = {
    "900": ("●", None), "901": ("◆", None), "931": ("●", None), "932": ("◆", "확인"), "933": ("●", None),
    "934": ("▲", "승인 창"), "935": ("▲", "승인 창"), "936": ("○", None), "937": ("◆", "확인"),
}

SHIM = r"""
(() => {
  const SEATS = __SEATS__;
  const listeners = {};
  let seq = 0;
  const act = (s) => s.act === 'unknown'
    ? { state: 'unknown', raw: 'unknown', reason: 'no observation', retained: false }
    : { state: s.act, raw: s.raw, reason: 'sim', retained: false, display_epoch: 'e1', observation_seq: ++seq,
        observed_age_secs: 0.2, last_positive_age_secs: null, stable_age_secs: null, family: 'claude', grammar_revision: null, consecutive_rejections: 0 };
  const row = (s) => ({ surface_id: s.sid, display_no: s.no, title: `${s.no} · Opus · ${s.cwd.split(/[\\/]/).pop()}`, role: s.role,
    cwd: s.cwd, live_cwd: s.cwd, exited: false, agent: 'claude', agent_alive: true,
    usage: s.ctx == null ? null : { ctx_pct: s.ctx, source: 'statusline', updated_at: Date.now() / 1000 }, display_activity: act(s) });
  const respond = (cmd, a) => {
    switch (cmd) {
      case 'daemon_status': return { daemon_pid: 4242, socket_path: '/sandbox/cys.sock', version: '1.1.14', app_version: '1.1.14' };
      case 'app_version': return '1.1.14';
      case 'list_depts': return { depts: {} };
      case 'dept_tombstones': return [];
      case 'fresh_start_check': return { ask: false };
      case 'resolve_list_endpoints': return a.endpoints;
      case 'list_surfaces': return { surfaces: SEATS.map(row) };
      case 'org_status': return { surfaces: SEATS.map((s) => ({ surface_id: s.sid, role: s.role, exited: false, idle_secs: s.act === 'unknown' ? 999 : 1, agent_alive: true,
        usage: row(s).usage, status: s.self || s.task ? { state: s.self ?? 'working', context_pct: null, task: s.task, age_secs: 5 } : null })),
        feed: { pending: SEATS.filter((s) => s.approval).length } };
      case 'feed_list_all': return { sockets: [{ socket: '/sandbox/cys.sock', dept: null, ok: true,
        items: SEATS.filter((s) => s.approval).map((s, i) => ({ request_id: 'r' + i, kind: 'approval', status: 'pending', surface_id: s.sid, title: 't', body: 'b' })) }] };
      case 'usage_named_reporters': return { named: [] };
      // 사용량 칸(사용량 · 7d · 7d·Fable) — 계정 자료가 있으면 그대로 그려져야 한다(1c ②: 좌석 줄 작업으로 칸이 사라지지 않았음을 확인)
      case 'usage_accounts_all': return { accounts: [{ account_id: 'acct-1', label: 'sim@example.com', provider: 'claude', updated_at: Date.now() / 1000,
        rate: [{ label: '7d', used_pct: 86, resets_at: Date.now() / 1000 + 86400, stale: false }] }] };
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

JS_STATE = r"""
() => {
  const rows = [...document.querySelectorAll('.ws-seats .ws-seat')].map((r) => ({
    no: r.querySelector('.ws-seat-no')?.textContent, shape: r.querySelector('.ws-seat-shape')?.textContent,
    tag: r.querySelector('.ws-seat-tag')?.textContent ?? null, name: r.querySelector('.ws-seat-name')?.textContent,
    ctx: r.querySelector('.ws-seat-ctx')?.textContent, over: r.scrollWidth > r.clientWidth + 1 }));
  const heads = [...document.querySelectorAll('.ws-seat-group-name')].map((h) => h.textContent);
  const tabs = document.getElementById('ws-tabs');
  // 이름 칸: 다 보이거나(자르지 않음) 최소 6글자 폭(한글 1글자 ≈ 1em) — 1c ①
  const nameShort = [...document.querySelectorAll('.ws-seats .ws-seat-name')].filter((n) => {
    const em = parseFloat(getComputedStyle(n).fontSize);
    return n.scrollWidth > n.clientWidth + 1 && n.clientWidth < 6 * em - 1;
  }).map((n) => n.textContent);
  // 역할 점(창 머리) ↔ 좌석 줄이 같은 값인가 — 1c ④
  const dotOf = (sid) => { const e = document.querySelector(`#root .pane[data-sid="${sid}"] .pane-role-dot`); if (!e) return null;
    for (const [c, v] of [['act-working', 'working'], ['act-waiting', 'idle'], ['act-input', 'blocked'], ['act-unknown', 'unknown'], ['act-stale', 'unknown']]) if (e.classList.contains(c)) return v; return '?'; };
  const mismatch = [...document.querySelectorAll('.ws-seats .ws-seat:not(.named)')].map((r) => {
    const st = [...r.classList].find((c) => c.startsWith('st-')).slice(3); const d = dotOf(r.dataset.sid);
    return d === null || d === st ? null : `${r.dataset.sid}:${d}≠${st}`; }).filter(Boolean);
  const rates = [...document.querySelectorAll('#ws-usage .wsu-rate')].length;
  return { rows, heads, docOver: document.documentElement.scrollWidth > innerWidth,
    tabsOver: tabs ? tabs.scrollWidth > tabs.clientWidth + 1 : null,
    oldCtx: [...document.querySelectorAll('.wsu-head')].some((h) => h.textContent === '페인 CTX'),
    panes: document.querySelectorAll('#root .pane').length, nameShort, mismatch, rates };
}
"""

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


def main() -> int:
    from playwright.sync_api import sync_playwright

    if not (DIST / "index.html").exists():
        print("ui/dist 없음 — sh ui/build.sh 먼저")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    httpd, port = serve(DIST)
    try:
        with sync_playwright() as p:
            # 설치된 playwright 판과 브라우저 판이 어긋난 기계: CHROME_PATH 로 이미 있는 실행 파일을 쓴다(새로 내려받지 않는다)
            exe = os.environ.get("CHROME_PATH")
            browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            for name, seats in SCENARIOS.items():
                js_seats = [dict(sid=s[0], no=s[1], role=s[2], cwd=s[3], act=s[4], raw=s[5], approval=s[6], self=s[7], task=s[8], ctx=s[9]) for s in seats]
                for w, h in ((1920, 1200), (1280, 800)):
                    print(f"== {name} @ {w}x{h}")
                    ctx = browser.new_context(viewport={"width": w, "height": h})
                    pg = ctx.new_page()
                    errs: list[str] = []
                    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                    pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
                    pg.add_init_script(SHIM.replace("__SEATS__", json.dumps(js_seats)))
                    pg.goto(f"http://127.0.0.1:{port}/index.html")
                    # 3초 고리 + 10초 사이드바 고리(승인 좌석) 한 바퀴를 기다린다
                    pg.wait_for_timeout(11500)
                    st = pg.evaluate(JS_STATE)
                    shot = OUT / f"{name}-{w}.png"
                    pg.screenshot(path=str(shot))
                    print(f"  캡처 {shot}")
                    check(len(st["rows"]) == len(seats), f"좌석 줄 수 {len(st['rows'])} = 좌석 수 {len(seats)}")
                    check(not st["oldCtx"], "옛 「페인 CTX」 머리 없음")
                    check(not st["docOver"], "문서 가로 넘침 0")
                    check(st["tabsOver"] is False, "사이드바 목록 가로 넘침 0")
                    check(not any(r["over"] for r in st["rows"]), "좌석 줄 한 줄 안에서 넘침 0")
                    groups = {s[3].replace("\\", "/").rstrip("/").split("/")[-1] for s in seats if s[2] not in ("master", "cso")}
                    if len(groups) <= 1:
                        check(st["heads"] == [], f"묶음 {len(groups)}개 = 머리 없음(왕초보 화면)")
                    else:
                        check(st["heads"] == ["site", "lms", "video"], f"묶음 머리 = 처음 나타난 순 {st['heads']}")
                    if name == "workers7":
                        got = {r["no"]: (r["shape"], r["tag"]) for r in st["rows"]}
                        check(got == EXPECT7, f"상태 모양·꼬리표 판정표 일치 {got}")
                    check(not st["nameShort"], f"이름이 잘리면 최소 6글자 폭 {st['nameShort']}")
                    check(not st["mismatch"], f"역할 점 = 좌석 줄(같은 좌석 같은 값) {st['mismatch']}")
                    check(st["rates"] >= 1, f"사용량 칸 막대 그려짐 {st['rates']}")
                    check(not errs, f"콘솔 오류 0 {errs[:3]}")
                    ctx.close()
            browser.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
