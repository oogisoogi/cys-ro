#!/usr/bin/env python3
"""런타임 미룸 게이트 — TICKET=cysr-1116-s2-1119 · P2-DESIGN §2-3 ㉢ · §2-4 ㉣ · §9-4 · §7 4군 ③④ (수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(tickrec_gate.py 의 SHIM 그대로) + 가짜 시계(멈춘 시계 · 실제 기다림 0)로 두 장면을 돌린다.

  A. 대화 화면으로 시작한 새 설치(cys-view = chat · 배치 저장본 없음 · 3초 고리 기록기 켬)
     ① 좌석 12개(master·cso·worker-1..10) 도착 → 입양 = 모형만: start_surface_stream 0 · attach_surface 0 (§9-4 「출력 흐름 0」)
     ② 1시간(가짜 시계 1,200틱) → 틱이 이어짐(list_surfaces ≥ 1,150) · 겹친 틱 0 · 배치 저장(cys-layout-v2)에 12좌석 · 여전히 흐름 0 (4군 ③)
     ③ 작업 화면 첫 진입 → 보이는 탭 좌석 전부 xterm 이 섬 · 「(없음)」 칸 0 · resize_surface = 보이는 좌석 × 1 (§2-4 · 4군 ④)
        · 붙기마다 기록 이어 붙이기 인자(화면 행 커서 · codex 3R) · 결과 ok = 안내 줄 0
        · 가짜 시계 1초 안에 끝남(설계 목표값 · 실물 측정 = 측정 대기) · 실시간 경과 보고
     ④ 전환 100회 → 런타임 다시 만들기 0(start_surface_stream 그대로 · 부수지 않음) · 그 뒤 30초 틱이 이어짐 · 페이지 오류 0
     ⑤ 분리 뒤 코드의 기록 덤프를 RUNTIME_DEFER_OUT 에 쓴다(bun 재생 = tick.test.ts ⑤ TICKREC_REPLAY)
  B. 대조군 — 작업 화면으로 시작(기본) · 같은 좌석 → 런타임 즉시(start_surface_stream ≥ 12) · 셈 장치가 비어 있지 않음을 보인다.

실행: CHROME_PATH=<chrome-headless-shell> [GATE_DIST=<번들>] [RUNTIME_DEFER_OUT=<덤프>] cys run -- <playwright python3> ui/e2e/runtime_defer_gate.py
"""
import http.server
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tickrec_gate import SHIM, BASE, CWD, seat  # noqa: E402  같은 대역(장면 차이 0)

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"
OUT = Path(os.environ.get("RUNTIME_DEFER_OUT") or (Path(os.environ.get("TMPDIR", "/tmp")) / "runtime-defer-tickrec.json"))
ROLES = ["master", "cso"] + [f"worker-{i}" for i in range(1, 11)]

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


COUNT = "(cmd) => window.__INVOKES.filter((x) => x[1] === cmd).length"
SIDS_OF = "(cmd) => window.__INVOKES.filter((x) => x[1] === cmd).map((x) => JSON.parse(x[2]).surfaceId)"
VISIBLE = r"""
() => {
  const root = document.getElementById('root');
  const panes = [...root.querySelectorAll('.pane')];
  return {
    panes: panes.length,
    xterm: panes.filter((p) => p.querySelector('.xterm')).length,
    missing: (root.innerText.match(/\(없음\)/g) || []).length,
    bodyShown: document.getElementById('body-row').style.display !== 'none',
  };
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
    print("번들:", DIST)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

            def session(view: str):
                ctx = br.new_context(viewport={"width": 1280, "height": 800})
                ctx.clock.install(time=datetime(2026, 11, 19, 10, 0, tzinfo=timezone.utc))
                ctx.clock.pause_at(datetime(2026, 11, 19, 10, 0, 1, tzinfo=timezone.utc))
                pg = ctx.new_page()
                errs: list[str] = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                pg.add_init_script(shim)
                pg.add_init_script("localStorage.setItem('cys-tickrec', '1')")
                if view == "chat":
                    pg.add_init_script("localStorage.setItem('cys-view', JSON.stringify({ v: 1, id: 'chat', decidedBy: 'user' }))")
                pg.goto(url)
                pg.clock.run_for(9_000)  # start() · 복원 · 빈 탭 충전(자리표 1)
                seats = ", ".join(seat(BASE, 1 + i, r) for i, r in enumerate(ROLES))
                pg.evaluate(f"() => {{ window.__SEATS.push({seats}); }}")
                pg.clock.run_for(30_000)  # 입양
                return ctx, pg, errs

            n = lambda pg, cmd: pg.evaluate(COUNT, cmd)  # noqa: E731

            # ── B. 대조군: 작업 화면 시작 ────────────────────────────────────────────
            print("== B. 대조군 — 작업 화면으로 시작(기본)")
            ctx, pg, errs = session("work")
            sb, ab = n(pg, "start_surface_stream"), n(pg, "attach_surface")
            vb = pg.evaluate(VISIBLE)
            print(f"  start_surface_stream {sb} · attach_surface {ab} · 화면 {vb}")
            check(sb >= 12 and ab >= 12, f"작업 화면 시작 = 입양 즉시 런타임(흐름 {sb} ≥ 12 · attach {ab} ≥ 12) — 셈 장치가 비어 있지 않다")
            check(vb["xterm"] >= 12 and vb["missing"] == 0, f"작업 화면 시작 = 좌석 xterm {vb['xterm']} ≥ 12 · 「(없음)」 0")
            check(not errs, f"페이지 오류 0 {errs[:2]}")
            ctx.close()

            # ── A. 대화 화면으로 시작한 새 설치 ──────────────────────────────────────
            print("== A. 대화 화면으로 시작한 새 설치")
            ctx, pg, errs = session("chat")
            s0, a0 = n(pg, "start_surface_stream"), n(pg, "attach_surface")
            check(s0 == 0 and a0 == 0, f"① 입양 = 모형만: start_surface_stream {s0} = 0 · attach_surface {a0} = 0")
            check(not pg.evaluate(VISIBLE)["bodyShown"], "① 작업 화면은 숨김(대화 화면이 켜짐)")
            l0 = n(pg, "list_surfaces")
            for _ in range(120):
                pg.clock.run_for(30_000)  # 1시간 = 1,200틱
            l1 = n(pg, "list_surfaces")
            c = pg.evaluate("() => window.__cysTickRec.counters()")
            check(l1 - l0 >= 1150, f"② 1시간 동안 3초 틱이 이어짐(list_surfaces +{l1 - l0} ≥ 1150)")
            check(c["skippedBusy"] == 0 and c["err"] == 0, f"② 겹친 틱 0 · 고리 오류 0 ({c['skippedBusy']} · {c['err']})")
            s1 = n(pg, "start_surface_stream")
            check(s1 == 0, f"② 1시간 뒤에도 출력 흐름 0 ({s1})")
            lay = json.loads(pg.evaluate("() => localStorage.getItem('cys-layout-v2')") or "null")
            saved = json.dumps(lay)
            have = [sid for sid in range(1, 13) if f'"sid": {sid}' in saved or f'"sid":{sid}' in saved]
            check(lay is not None and len(have) == 12, f"② 대화 화면에서도 배치 저장(cys-layout-v2 에 좌석 {len(have)}/12)")
            dump = pg.evaluate("() => window.__cysTickRec.dumpJson()")
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(dump, encoding="utf-8")
            print("  ⑤ 기록 덤프:", OUT, f"({len(dump.encode())} B · 입양 {c['adopt']} · 자리표 판정 {c['placeholderJudged']} · 회수 {c['placeholderClose']})")
            check(c["adopt"] >= 12, f"⑤ 기록에 입양 ≥ 12 ({c['adopt']})")

            # ③ 작업 화면 첫 진입
            r0 = n(pg, "resize_surface")
            t0 = time.perf_counter()
            pg.click('#view-switch button[data-view="work"]')
            fake = 0
            v = pg.evaluate(VISIBLE)
            while fake < 1000 and not (v["bodyShown"] and v["panes"] > 0 and v["xterm"] == v["panes"]):
                pg.clock.run_for(16)
                fake += 16
                v = pg.evaluate(VISIBLE)
            wall = (time.perf_counter() - t0) * 1000
            pg.clock.run_for(200)  # 크기 맞춤(rAF) · ResizeObserver 한 바퀴
            v = pg.evaluate(VISIBLE)
            tree = pg.evaluate("() => { const t = JSON.parse(localStorage.getItem('cys-layout-v2')); const ws = t.workspaces[t.active]; const out = []; const walk = (n) => { if (!n) return; if (n.type === 'pane') out.push(n.sid); else { walk(n.a); walk(n.b); } }; walk(ws.tree); return out; }")
            print(f"  첫 진입: 가짜 시계 {fake} ms · 실시간 {wall:.0f} ms · 화면 {v} · 보이는 탭 좌석 {tree}")
            check(v["bodyShown"] and v["xterm"] == v["panes"] and v["panes"] == len(tree) and len(tree) >= 12, f"③ 보이는 탭 좌석 전부 xterm({v['xterm']}/{v['panes']} · 탭 좌석 {len(tree)})")
            check(v["missing"] == 0, f"③ 「(없음)」 칸 0 ({v['missing']})")
            check(fake < 1000, f"③ 첫 진입이 가짜 시계 1초 안(설계 목표값 · {fake} ms)")
            rs = pg.evaluate(SIDS_OF, "resize_surface")[r0:]
            check(len(rs) == len(set(rs)) and set(rs) == set(tree), f"③ resize_surface = 보이는 좌석 × 1 ({len(rs)}건 · 겹침 {len(rs) - len(set(rs))} · 좌석 일치 {set(rs) == set(tree)})")
            s2 = n(pg, "start_surface_stream")
            ss = pg.evaluate(SIDS_OF, "start_surface_stream")
            # (codex 3R blocking) 미룬 좌석마다 붙을 때 기록 이어 붙이기 인자 = 미룬 그때 화면 행 커서(대역 목록 7 · 빈 탭 새 셸 = 생성 때 0) + xterm 행 수 ·
            #   결과 ok = 안내 줄 0 · 데몬이 한 락으로 이어 주므로 따로 묻는 기록 조회 RPC 는 없다
            starts = pg.evaluate("() => window.__INVOKES.filter((x) => x[1] === 'start_surface_stream').map((x) => JSON.parse(x[2]))")
            with_hist = [a for a in starts if a.get("historySince") is not None]
            check(len(with_hist) == len(tree) and all(isinstance(a.get("historyRows"), int) and a["historyRows"] > 0 for a in with_hist)
                  and sorted({a["historySince"] for a in with_hist}) in ([7], [0, 7]), f"③ 붙기 = 미룬 좌석마다 화면 행 커서 인자({len(with_hist)}건 · 커서 {sorted({a['historySince'] for a in with_hist})})")
            gaps = pg.evaluate("() => document.querySelectorAll('.pane-history-gap').length")
            check(gaps == 0, f"③ 기록 이어 붙이기 ok = 안내 줄 0 ({gaps})")
            check(n(pg, "seat_history") == 0, "③ 따로 묻는 기록 조회 0(데몬 한 락)")
            check(s2 == len(tree) and len(set(ss)) == len(ss), f"③ 출력 흐름 = 보이는 좌석 수({s2} = {len(tree)}) · 같은 좌석 두 번 0")

            # ④ 전환 100회
            for _ in range(100):
                pg.click('#view-switch button[data-view="chat"]')
                pg.clock.run_for(20)
                pg.click('#view-switch button[data-view="work"]')
                pg.clock.run_for(20)
            l2 = n(pg, "list_surfaces")
            pg.clock.run_for(30_000)
            l3 = n(pg, "list_surfaces")
            v = pg.evaluate(VISIBLE)
            s3 = n(pg, "start_surface_stream")
            c2 = pg.evaluate("() => window.__cysTickRec.counters()")
            check(s3 == s2, f"④ 전환 100회 뒤 런타임 다시 만들기 0(흐름 {s3} = {s2})")
            check(l3 - l2 >= 9, f"④ 전환 100회 뒤 30초 틱이 이어짐(list_surfaces +{l3 - l2} ≥ 9)")
            check(c2["skippedBusy"] == 0 and c2["err"] == 0, f"④ 겹친 틱 0 · 고리 오류 0 ({c2['skippedBusy']} · {c2['err']})")
            check(v["xterm"] == v["panes"] and v["missing"] == 0, f"④ 작업 화면 좌석 그대로({v})")
            check(not errs, f"페이지 오류 0 {errs[:2]}")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    for f in failures:
        print("  FAIL:", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
