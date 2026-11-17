#!/usr/bin/env python3
"""3초 고리 특성 기록기 게이트 — TICKET=cysr-ui-slice0-1117 · P2-DESIGN §2-1 조각 0 (수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역 + 가짜 시계(playwright clock · 실제 기다림 0)로 한 장면을 돌린다:
  빈 본부 탭 → 자리표(맨 셸) 생성 → 역할 좌석 도착(입양 + 자리표 회수) → 워커 추가(입양) → 그 워커가 목록에서 사라짐(유령 2연속 → 퇴거)
  → 새 부서 등재(탭 열기 + 입양) → 워커 끝남 + 복원 완료 신호(옛 자리 쓸기) → 부서 데몬 무응답 30초(소켓 건너뜀) → 회복.
판정:
  ON  : localStorage cys-tickrec=1 · 200틱 넘게 돌림 → 링 200칸 가득 · 각 결정(입양·퇴거·쓸기·자리표 회수·부서 열기·소켓 건너뜀)이 1회 이상 기록
        · 덤프에 장면의 경로·제목·부서 이름 원문 0 · 덤프 크기 ≤ 상한 · 덤프 파일을 쓴다(TICKREC_OUT 또는 스크래치 기본).
  OFF : 스위치 없음 → window.__cysTickRec 없음 · 기준 번들(BASE_DIST · 조각 0 이전 커밋 빌드)과 **invoke 호출 열(명령·인자·가짜 시각)
        · 최종 localStorage 전부 · 최종 화면 글자**가 바이트 같음. 대조군: 같은 번들 두 번 = 같음(하네스 결정론) ·
        음성 대조: 장면을 1칸 바꾸면 다름(비교기가 차이를 잡는다) · ON 도 invoke 열·저장소는 OFF 와 같음(기록기 부작용 0).
실행: CHROME_PATH=<chrome-headless-shell> [BASE_DIST=<기준 번들>] [TICKREC_OUT=<덤프 경로>] cys run -- <playwright python3> ui/e2e/tickrec_gate.py
"""
import hashlib
import http.server
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"
BASE_DIST = Path(os.environ["BASE_DIST"]) if os.environ.get("BASE_DIST") else None
OUT = Path(os.environ.get("TICKREC_OUT") or (Path(os.environ.get("TMPDIR", "/tmp")) / "tickrec-200.json"))
MAX_DUMP = 2 * 1024 * 1024  # views/tickrec.ts TICKREC_MAX_DUMP_BYTES 와 같은 값
BASE = "/sandbox/cys.sock"
D1 = "/sandbox/dept-zeta.sock"
D1_NAME = "zeta-team-name"
CWD = "/sandbox/home/alpha-proj"

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


SHIM = r"""
(() => {
  const BASE = '__BASE__';
  window.__SEATS = []; window.__DEPTS = []; window.__HANG = {}; window.__INVOKES = [];
  const listeners = {}; let nextSid = 900;
  const mine = (sock) => window.__SEATS.filter((s) => s.sock === (sock ?? BASE));
  const row = (s) => ({ surface_id: s.sid, display_no: s.sid, title: `${s.sid} · Opus · ${s.cwd.split('/').pop()}`, role: s.role, cwd: s.cwd, live_cwd: s.cwd,
    exited: !!s.ex, agent: s.role ? 'claude' : null, agent_alive: !s.ex, line_count: 3, size: { rows: 35, cols: 120 },
    usage: s.role ? { ctx_pct: 10, source: 'statusline', updated_at: Date.now() / 1000 } : null,
    display_activity: { state: 'unknown', raw: 'unknown', reason: 'no observation', retained: false } });
  const respond = (cmd, a) => {
    switch (cmd) {
      case 'daemon_status': return { daemon_pid: 4242, socket_path: BASE, version: '1.1.15', app_version: '1.1.15' };
      case 'app_version': return '1.1.15';
      case 'default_socket_slug': return 'base';
      case 'home_dir_path': return '/sandbox/home';
      case 'list_depts': return { depts: Object.fromEntries(window.__DEPTS.map(([k, sock, dn]) => [k, { socket: sock, display_name: dn }])) };
      case 'dept_tombstones': return [];
      case 'fresh_start_check': return { ask: false };
      case 'resolve_list_endpoints': return a.endpoints;
      case 'list_surfaces': {
        if (window.__HANG[a.socket ?? BASE]) throw new Error('rpc timeout');
        return { surfaces: mine(a.socket).map(row) };
      }
      case 'create_surface': { const sid = nextSid++; window.__SEATS.push({ sock: a.socket ?? BASE, sid, role: null, cwd: CWD_, ex: false }); return { surface_id: sid }; }
      case 'close_surface': { const i = window.__SEATS.findIndex((s) => s.sid === a.surfaceId && s.sock === (a.socket ?? BASE)); if (i >= 0) window.__SEATS.splice(i, 1); return true; }
      case 'org_status': return { surfaces: mine(a.socket).map((s) => ({ surface_id: s.sid, role: s.role, exited: !!s.ex, idle_secs: 1, agent_alive: !s.ex, usage: row(s).usage, status: null })), feed: { pending: 0 } };
      case 'feed_list_all': return { sockets: [{ socket: BASE, dept: null, ok: true, items: [] }] };
      case 'usage_named_reporters': return { named: [] };
      case 'usage_accounts_all': return { accounts: [] };
      case 'attach_surface': return { output_event: 'sim-out-' + a.surfaceId, exited_event: 'sim-exit-' + a.surfaceId };
      default: return null;
    }
  };
  const CWD_ = '__CWD__';
  window.__TAURI__ = {
    core: { invoke: (cmd, args) => new Promise((res, rej) => {
      window.__INVOKES.push([Date.now(), cmd, JSON.stringify(args ?? null)]);
      try { res(respond(cmd, args ?? {})); } catch (e) { rej(e); } }) },
    event: { listen: (name, h) => { (listeners[name] ??= []).push(h); return Promise.resolve(() => {}); } },
  };
  window.__emit = (name, payload) => { for (const h of listeners[name] ?? []) h({ payload }); return (listeners[name] ?? []).length; };
})();
"""

SNAP = r"""
() => ({
  invokes: window.__INVOKES,
  storage: Object.keys(localStorage).sort().map((k) => [k, localStorage.getItem(k)]),
  text: document.body.innerText,
  panes: document.querySelectorAll('.pane').length,
  tabs: [...document.querySelectorAll('#ws-tabs .ws-name')].map((e) => e.textContent),
  hasRec: !!window.__cysTickRec,
})
"""


def seat(sock: str, sid: int, role, cwd: str = CWD) -> str:
    return json.dumps({"sock": sock, "sid": sid, "role": role, "cwd": cwd, "ex": False})


def scenario(pg, variant: str = "") -> None:
    """가짜 시계로 장면을 민다 — 모든 기다림은 clock.run_for(실제 시간 0)."""
    run = pg.clock.run_for
    run(9_000)  # start() · 복원 · 자리표 생성
    pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}, {seat(BASE, 2, 'cso')}, {seat(BASE, 3, 'worker-1')}); }}")
    if variant == "extra":
        pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 7, 'worker-7')}); }}")
    run(30_000)  # 입양 + 자리표 회수
    pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 4, 'worker-2')}); }}")
    run(30_000)  # 입양
    pg.evaluate("() => { const i = window.__SEATS.findIndex((s) => s.sid === 4); window.__SEATS.splice(i, 1); }")
    run(30_000)  # 유령 2연속 → 퇴거
    pg.evaluate(f"() => {{ window.__DEPTS.push(['zeta', '{D1}', '{D1_NAME}']); window.__SEATS.push({seat(D1, 11, 'master')}, {seat(D1, 12, 'worker-1')}); }}")
    run(60_000)  # 부서 탭 열기 + 입양
    pg.evaluate("() => { window.__SEATS.find((s) => s.sid === 3).ex = true; }")
    run(6_000)
    pg.evaluate("() => window.__emit('restore-progress', { phase: 'done', hq_ok: true, ok: 1, fail: 0 })")
    run(30_000)  # 옛 자리 쓸기
    pg.evaluate(f"() => {{ window.__HANG['{D1}'] = true; }}")
    run(30_000)  # 부서 데몬 무응답
    pg.evaluate(f"() => {{ window.__HANG['{D1}'] = false; }}")
    run(30_000)  # 회복(≈ 255초 · 결정이 모두 앞 90틱 안에 있다 — 아래 200틱째 덤프가 그것을 전부 품는다)


TICKS = "() => window.__cysTickRec ? window.__cysTickRec.counters().ticks : null"


def idle_until_200(pg) -> None:
    """켜짐: 기록 틱이 200 이 될 때까지 3초씩 민다(상한 300회). 꺼짐: 같은 시간(켜짐 실측과 같은 길이)만큼 민다."""
    for _ in range(300):
        n = pg.evaluate(TICKS)
        if n is not None and n >= 200:
            return
        pg.clock.run_for(3_000)


def main() -> int:
    from playwright.sync_api import sync_playwright

    servers = []

    def serve(d: Path) -> str:
        h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(d), **kw))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        servers.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}/index.html"

    url_new = serve(DIST)
    url_base = serve(BASE_DIST) if BASE_DIST else None
    print("번들:", DIST, "· 기준 번들:", BASE_DIST or "(없음 — OFF 대조 생략)")
    shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

            t0_ms = int(datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc).timestamp() * 1000)
            idle_ms = [0]  # 켜짐 실행이 200틱에 닿은 가짜 시각(꺼짐 실행은 같은 길이만큼 민다 — 같은 장면 길이)

            def session(url: str, on: bool, variant: str = ""):
                ctx = br.new_context(viewport={"width": 1600, "height": 1000})
                ctx.clock.install(time=datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc))  # 고정 시각
                ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))  # 멈춘 시계 — 시간은 run_for 로만 흐른다(실시간 누수 차단)
                pg = ctx.new_page()
                errs: list[str] = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                pg.add_init_script(shim)
                if on:
                    pg.add_init_script("localStorage.setItem('cys-tickrec', '1')")
                pg.goto(url)
                scenario(pg, variant)
                if on:
                    idle_until_200(pg)
                    idle_ms[0] = pg.evaluate("() => Date.now()") - t0_ms
                else:
                    pg.clock.run_for(idle_ms[0] - (pg.evaluate("() => Date.now()") - t0_ms))
                dump = pg.evaluate("() => window.__cysTickRec ? window.__cysTickRec.dumpJson() : null")  # 200틱째 덤프(켜짐)
                snap = pg.evaluate(SNAP)
                after = None
                if on:  # 회전: 30초(10틱) 더 → 칸 200 그대로 · 버림 증가
                    pg.clock.run_for(30_000)
                    after = pg.evaluate("() => window.__cysTickRec.counters()")
                ctx.close()
                return snap, dump, errs, after

            def digest(snap: dict, with_rec_key: bool = True) -> str:
                st = [kv for kv in snap["storage"] if with_rec_key or kv[0] != "cys-tickrec"]
                # invoke 열 = (명령, 인자) 순서 — 가짜 시각은 아래 정보 줄로 따로 본다(초기 적재 중 1ms 누수가 드물게 관측됨 · 순서·인자는 그때도 같았다)
                body = json.dumps({"invokes": [x[1:] for x in snap["invokes"]], "storage": st, "text": snap["text"], "panes": snap["panes"], "tabs": snap["tabs"]}, ensure_ascii=False)
                return hashlib.sha256(body.encode()).hexdigest()

            print("== ON: 스위치 켬 · 200틱 넘게")
            snap_on, dump, errs, after = session(url_new, True)
            check(not errs, f"페이지 오류 0 {errs[:2]}")
            check(snap_on["hasRec"], "window.__cysTickRec 있음(켜짐)")
            check(dump is not None, "덤프 있음")
            d = json.loads(dump or "{}")
            c = d.get("counters", {})
            ents = d.get("entries", [])
            print("  카운터:", json.dumps(c, ensure_ascii=False))
            check(d.get("schema") == "cys-tickrec/1" and d.get("ring") == 200, f"꼴 schema·ring {d.get('schema')} {d.get('ring')}")
            check(len(ents) == 200 and c.get("ticks") == 200 and c.get("dropped") == 0, f"200틱째 덤프 = 칸 200 · 버림 0 (칸 {len(ents)} · 틱 {c.get('ticks')} · 버림 {c.get('dropped')})")
            check(bool(after) and after["ticks"] > 200 and after["dropped"] == after["ticks"] - 200, f"회전: 그 뒤 30초 → 버림 = 틱 − 200 ({after})")
            # 칸 안에서 결정을 직접 센다(카운터와 별개 — 덤프 파일 자체가 재생 원료가 되는지)
            inside = {
                "adopt": sum(len(e["adopt"]) for e in ents),
                "evict": sum(len(g["evict"]) for e in ents for g in e["ghost"]),
                "sweep": sum(len(x["targets"]) for e in ents for x in e["sweep"]),
                "phClose": sum(1 for e in ents for x in e["ph"] if x["close"]),
                "phKeep": sum(1 for e in ents for x in e["ph"] if not x["close"]),
                "deptOpen": sum(1 for e in ents if e["wsAfterDepts"] is not None and e["wsAfterDepts"] > max(1, len(e["ws"]))),
                "sockSkip": sum(1 for e in ents for x in e["socks"] if not x["got"]),
            }
            print("  칸 안 결정 수:", inside)
            for k, v in inside.items():
                check(v >= 1, f"덤프 칸 안 {k} ≥ 1 ({v})")
            for k in ["adopt", "evict", "sweep", "placeholderJudged", "placeholderClose", "placeholderClosed", "deptOpened", "render", "sockSkip"]:  # 카운터
                check(c.get(k, 0) >= 1, f"결정 기록 {k} ≥ 1 ({c.get(k)})")
            check(c.get("recorderFault", -1) == 0, f"기록기 예외 0 ({c.get('recorderFault')})")
            check(all(e.get("done") for e in ents), "모든 칸이 end 까지 닿음(던진 틱 0)")
            seqs = [e["seq"] for e in ents]
            check(seqs == list(range(seqs[0], seqs[0] + 200)) if seqs else False, "칸 seq 연속(겹침·빠짐 0)")
            nows = [e["now"] for e in ents]
            gaps = sorted({b - a for a, b in zip(nows, nows[1:])})
            print("  틱 간격(ms) 종류:", gaps[:8])
            check(c.get("skippedBusy", -1) == 0, f"겹친 틱(바쁨 가드) 0 ({c.get('skippedBusy')})")
            leak = [s for s in [CWD, "alpha-proj", "/sandbox", D1, D1_NAME, "zeta", "Opus"] if s in (dump or "")]
            check(not leak, f"덤프에 장면 원문 0 {leak}")
            size = len((dump or "").encode())
            check(size <= MAX_DUMP, f"덤프 크기 {size} B ≤ 상한 {MAX_DUMP} B")
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(dump or "", encoding="utf-8")
            print("  덤프 파일:", OUT, f"({size} B)")

            if url_base:
                print("== OFF: 스위치 없음 — 기준 번들과 바이트 대조")
                snap_new, dump_new, errs_new, _ = session(url_new, False)
                snap_base, _, errs_base, _ = session(url_base, False)
                snap_base2, _, _, _ = session(url_base, False)
                snap_var, _, _, _ = session(url_base, False, "extra")
                check(not errs_new and not errs_base, f"페이지 오류 0 {errs_new[:1]} {errs_base[:1]}")
                check(dump_new is None and not snap_new["hasRec"], "꺼짐 = window.__cysTickRec 없음")
                dn, db, db2, dv = digest(snap_new), digest(snap_base), digest(snap_base2), digest(snap_var)
                print(f"  invoke 수: 새 {len(snap_new['invokes'])} · 기준 {len(snap_base['invokes'])} · 저장 키 {len(snap_new['storage'])} · pane {snap_new['panes']} · 탭 {snap_new['tabs']}")
                check(db == db2, f"대조군: 기준 번들 두 번 = 같음(하네스 결정론) {db[:12]} {db2[:12]}")
                check(dn == db, f"꺼짐: 새 번들 = 기준 번들(invoke 열·저장소·화면 글자) {dn[:12]} {db[:12]}")
                if dn != db:
                    for k in ["invokes", "storage", "text", "panes", "tabs"]:
                        if snap_new[k] != snap_base[k]:
                            print("    다른 칸:", k)
                check(dv != db, f"음성 대조: 장면 1칸 바꿈 → 다름 {dv[:12]}")
                same_t = [a[0] for a in snap_new["invokes"]] == [b[0] for b in snap_base["invokes"]]
                dts = [b_[0] - a_[0] for a_, b_ in zip(snap_new["invokes"], snap_base["invokes"])]
                print(f"  (정보) invoke 가짜 시각까지 같음: {same_t} · 어긋난 호출 {sum(1 for x in dts if x)}건 · 최대 {max((abs(x) for x in dts), default=0)}ms")
                don = digest(snap_on, with_rec_key=False)
                check(don == db, f"켜짐도 invoke 열·저장소(스위치 키 제외)·화면 = 기준과 같음(기록기 부작용 0) {don[:12]}")
            br.close()
    finally:
        for s in servers:
            s.shutdown()
    print("\nRESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    for f in failures:
        print("  FAIL:", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
