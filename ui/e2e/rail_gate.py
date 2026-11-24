#!/usr/bin/env python3
"""대화 화면 왼쪽 메뉴바 게이트 — TICKET=cysr-1116-s6-1119 · P2-DESIGN §11 조각 6 (수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(tickrec_gate SHIM + chat_gate CHAT_SHIM 위에 좌석 묶음 칸·org 자기보고를 덧씌움) + 가짜 시계.
클릭은 playwright 실제 마우스(page.click = 신뢰 이벤트) · 「대본 클릭」 = element.click()(isTrusted=false).

A 보임: 1280·1024 폭 = 메뉴바 보임(320px) · 600 폭 = 숨김 · 마스터 카드 · 「맡긴 일 N」 · 결과 자리 = 숨김 · 좌석 번호·모델 이름 0(FR-P1)
B 팀: 묶음 1개 = 팀 머리 0 · 묶음 2개 = 팀 머리 이름이 **작업 화면 왼쪽 묶음 이름과 같다**(개정 E1)
C 「팀 만드는 중」: 마스터 답 ⟪팀 만드는 중: 홍보팀⟫ → 점선 카드 · 본부 묶음 사건 → 카드 내림 + 팀 머리 「홍보팀」 · 부서 slug 사건 = 무시
D 빠른 답: ⟪팀 제안⟫ → 단추 2 · 대본 클릭 = 쓰기 0 · 진짜 클릭 = 쓰기 1(원문 그대로) · 그 뒤 단추 사라짐 · ⟪부서 제안: 홍보팀⟫ → 「네, 부서로 올려 주세요」·「지금은 아니요」
E 부서: 등록부에 부서 1 → 「부서 1」 줄 + 가이드 1회(「알겠어요」 → cys-dept-guide-seen) · 다시 켜면 가이드 0 · 「부서 안내」 = 다시 보기 · ⟪부서로 올리는 중⟫ 카드 → 등록부에 생기면 부서 줄로
F 접근성: 메뉴바 글자 18px 미만 0 · 누를 면 44px 미만 0
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/rail_gate.py
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
OUT = Path(os.environ.get("RAIL_SHOTS", "/tmp/rail-gate-shots"))

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


# 좌석에 묶음 칸(group·group_set) · org.status 자기보고(task) 를 싣는다 — 대역 좌석 s.group · s.task
RAIL_SHIM = r"""
(() => {
  const prev = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    const a = args ?? {};
    const sock = a.socket ?? '__BASE__';
    if (cmd === 'list_surfaces') return prev(cmd, args).then((r) => ({ ...r, surfaces: (r.surfaces || []).map((x) => { const s = window.__SEATS.find((q) => q.sid === x.surface_id && q.sock === sock); return { ...x, group: s?.group ?? null, group_set: s?.group !== undefined }; }) }));
    if (cmd === 'org_status') return prev(cmd, args).then((r) => ({ ...r, surfaces: (r.surfaces || []).map((x) => { const s = window.__SEATS.find((q) => q.sid === x.surface_id && q.sock === sock); return s && s.task ? { ...x, status: { state: 'working', task: s.task, age_secs: 3 } } : x; }) }));
    return prev(cmd, args);
  };
})();
"""

RAIL = """() => { const r = document.querySelector('.cv-rail'); if (!r) return null; const cs = getComputedStyle(r);
  return { shown: cs.display !== 'none', width: Math.round(r.getBoundingClientRect().width), text: r.innerText,
    who: r.querySelector('.cvr-who .cvr-st')?.textContent ?? null, head: r.querySelector('.cvr-tasks .cvr-h')?.textContent ?? null,
    teams: [...r.querySelectorAll('.cvr-team')].map((e) => e.dataset.team), forming: [...r.querySelectorAll('.cvr-forming')].map((e) => [e.dataset.forming, e.querySelector('.cvr-t')?.textContent]),
    cards: [...r.querySelectorAll('.cvr-card[data-task]')].map((e) => [e.dataset.team ?? null, e.dataset.task, e.dataset.status, e.querySelector('.cvr-help')?.textContent]),
    depts: [...r.querySelectorAll('.cvr-dept')].map((e) => e.querySelector('.cvr-t')?.textContent), deptHead: r.querySelector('.cvr-depts .cvr-h')?.textContent ?? null,
    resultsHidden: r.querySelector('[data-rail=results]')?.hidden ?? null }; }"""
WORK_GROUPS = """() => [...document.querySelectorAll('.ws-seats[data-seat-host]:not([data-seat-host="board"]):not([data-seat-host^="n"]) .ws-seat-group-name')].map((e) => e.textContent)"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
    rail_shim = RAIL_SHIM.replace("__BASE__", BASE)
    site, home = CWD.rsplit("/", 1)[0] + "/site", CWD.rsplit("/", 1)[0] + "/home"
    with sync_playwright() as p:
        exe = os.environ.get("CHROME_PATH")
        br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

        def page(width: int = 1280, storage: "dict | None" = None):
            ctx = br.new_context(viewport={"width": width, "height": 800})
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.add_init_script(rail_shim)
            if storage:
                pg.add_init_script("(() => { " + "".join(f"localStorage.setItem({json.dumps(k)}, {json.dumps(v)});" for k, v in storage.items()) + " })();")
            pg.goto(url)
            pg.clock.run_for(9_000)
            s2 = json.loads(seat(BASE, 2, "worker-2", site))
            s2["task"] = "행사 안내 페이지"
            s3 = json.loads(seat(BASE, 3, "worker-3", site))
            s3["task"] = "행사 안내 페이지"
            pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}, {json.dumps(s2)}, {json.dumps(s3)}); }}")
            pg.clock.run_for(6_000)
            pg.click("#view-switch button[data-view=chat]")
            pg.clock.run_for(3_300)
            return ctx, pg, errs

        writes = lambda pg: pg.evaluate("() => window.__CHAT.writes.map((w) => w.args.text)")  # noqa: E731

        def push_reply(pg, uuid: str, text: str) -> None:
            pg.evaluate(f"""() => {{ const C = window.__CHAT; C.file.push({{ uuid: '{uuid}', parent: null, role: 'assistant', text: {json.dumps(text)}, ts: new Date(Date.now()).toISOString() }}); C.master.idle_secs = 0; }}""")
            pg.clock.run_for(3_100)
            pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
            pg.clock.run_for(3_100)

        print("== A 보임 · 마스터 카드 · 맡긴 일 · 결과 자리 숨김 · 번호 0")
        ctx, pg, errs = page(1280)
        r = pg.evaluate(RAIL)
        check(r is not None and r["shown"] and r["width"] == 320, f"1280 폭 = 메뉴바 보임 320px {r and (r['shown'], r['width'])}")
        check(r["head"] == "맡긴 일 1" and r["cards"] == [[None, "행사 안내 페이지", r["cards"][0][2], "도우미 2명"]], f"같은 일 두 좌석 = 카드 1 · 도우미 2명 · 팀 머리 0 {r['head']} {r['cards']}")
        check(r["who"] is not None and r["teams"] == [] and r["resultsHidden"] is True, f"마스터 카드 · 결과 자리 숨김 {r['who']} {r['resultsHidden']}")
        check("Opus" not in r["text"] and "surface" not in r["text"] and not any(t.strip() in ("1", "2", "3") for t in r["text"].split("\n")), f"좌석 번호·모델 이름 0(FR-P1) {r['text']!r}")
        col = pg.evaluate("""() => { const c = document.querySelector('.cvr-card[data-status=run] .cvr-line'); const t = document.querySelector('.cvr-card[data-status=run] .cvr-help');
          return c && t ? { line: getComputedStyle(c).color, help: getComputedStyle(t).color, run: getComputedStyle(document.documentElement).getPropertyValue('--cv-run').trim() } : null; }""")
        check(col is not None and col["line"] != col["help"] and col["line"] == "rgb(45, 91, 203)", f"(검증 X2) 「일하는 중」 상태 줄 = 파랑(--cv-run) · 보조 줄 회색과 다름 {col}")
        pg.screenshot(path=str(OUT / "a-1280.png"))
        # (TICKET=cysr-1119-s5 · CV-RAIL ⑤-1) 결과가 생기면 결과 자리 = 왼쪽 칸에 보임(숨김 판정 = 결과 수 · 자식 수 아님)
        pg.evaluate("() => window.__emit('daemon-event', { name: 'skill.run_finished', socket_slug: 'base', payload: { run_id: 'rr', status: 'done', artifact_dir: '/sandbox/home/cys-runs/rr' } })")
        pg.clock.run_for(3_300)
        rr = pg.evaluate("() => { const x = document.querySelector('.cv-rail [data-rail=results]'); return { hidden: x?.hidden ?? null, shown: !!x && getComputedStyle(x).display !== 'none', inRail: !!x?.querySelector('.cv-results') }; }")
        check(rr == {"hidden": False, "shown": True, "inRail": True}, f"결과 1 = 왼쪽 칸 결과 자리 보임 {rr}")

        print("== B 팀 = 작업 화면 묶음 이름과 같음")
        s4 = json.loads(seat(BASE, 4, "worker-4", home))
        s4["task"] = "집 정리"
        pg.evaluate(f"() => {{ window.__SEATS.push({json.dumps(s4)}); }}")
        pg.clock.run_for(3_300)
        r = pg.evaluate(RAIL)
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(3_300)
        wg = pg.evaluate(WORK_GROUPS)
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_300)
        check(r["teams"] == ["site", "home"] and r["teams"] == wg, f"묶음 2 = 팀 머리 · 작업 화면 묶음 이름과 같음 rail={r['teams']} work={wg}")
        check(r["head"] == "맡긴 일 2", f"맡긴 일 수 {r['head']}")

        print("== C 「팀 만드는 중」 → 묶음 사건 → 진행")
        push_reply(pg, "a1", "홍보 일을 따로 묶을게요.\n⟪팀 만드는 중: 홍보팀⟫")
        r = pg.evaluate(RAIL)
        check(r["forming"] == [["team", "홍보팀"]], f"표식 → 만드는 중 카드 {r['forming']}")
        ev = {"type": "event", "seq": 9, "name": "surface.group.changed", "category": "surface", "surface_id": 4, "payload": {"surface_id": 4, "group": "홍보팀", "previous": None}}
        pg.evaluate("(e) => window.__emit('daemon-event', e)", dict(ev, socket_slug="dept-x"))
        pg.clock.run_for(100)
        check(pg.evaluate(RAIL)["forming"] == [["team", "홍보팀"]], "부서 slug 묶음 사건 = 무시")
        pg.evaluate("() => { window.__SEATS.find((s) => s.sid === 4).group = '홍보팀'; }")
        pg.evaluate("(e) => window.__emit('daemon-event', e)", dict(ev, socket_slug="base"))
        pg.clock.run_for(100)
        r = pg.evaluate(RAIL)
        check(r["forming"] == [] and "홍보팀" in r["teams"], f"본부 묶음 사건 → 카드 내림 · 팀 머리 홍보팀 {r['forming']} {r['teams']}")
        pg.screenshot(path=str(OUT / "c-teams-1280.png"))

        print("== D 빠른 답(원문 그대로 · 신뢰 클릭만)")
        push_reply(pg, "a2", "일이 세 갈래라 팀으로 나눠 맡길까요?\n⟪팀 제안⟫")
        btns = pg.evaluate("() => [...document.querySelectorAll('.cv-quick-btn')].map((b) => b.textContent)")
        check(btns == ["네, 팀으로 나눠 주세요", "아니요, 지금처럼 해 주세요"], f"단추 2 {btns}")
        w0 = len(writes(pg))
        pg.evaluate("() => document.querySelector('.cv-quick-btn').click()")
        pg.clock.run_for(3_300)
        check(len(writes(pg)) == w0, f"대본 클릭 = 쓰기 0 ({len(writes(pg)) - w0})")
        pg.click(".cv-quick-btn >> nth=0")
        pg.clock.run_for(3_300)
        w = writes(pg)
        check(len(w) == w0 + 1 and w[-1] == "네, 팀으로 나눠 주세요", f"진짜 클릭 = 쓰기 1 · 원문 그대로 {w[w0:]}")
        check(pg.evaluate("() => document.querySelectorAll('.cv-quick-btn').length") == 0, "보낸 뒤 단추 사라짐(마지막 말이 아님)")
        push_reply(pg, "a3", "홍보팀 일이 끝났어요. 부서로 올릴까요?\n⟪부서 제안: 홍보팀⟫")
        btns = pg.evaluate("() => [...document.querySelectorAll('.cv-quick-btn')].map((b) => b.textContent)")
        check(btns == ["네, 부서로 올려 주세요", "지금은 아니요"], f"부서 제안 단추 {btns}")
        pg.screenshot(path=str(OUT / "d-quick-1280.png"))

        print("== E 부서 줄 · 가이드 1회 · 다시 보기 · 올리는 중")
        push_reply(pg, "a4", "홍보팀을 부서로 올리는 중이에요.\n⟪부서로 올리는 중: 홍보부⟫")
        check(["promote", "홍보부"] in pg.evaluate(RAIL)["forming"], "부서로 올리는 중 카드")
        pg.evaluate("() => { window.__DEPTS.push(['dept-1', '/sandbox/dept-1.sock', '홍보부']); }")
        pg.clock.run_for(33_000)
        r = pg.evaluate(RAIL)
        check(r["deptHead"] == "부서 1" and r["depts"] == ["홍보부"] and ["promote", "홍보부"] not in r["forming"], f"등록부에 생김 → 부서 줄 · 올리는 중 카드 내림 {r['deptHead']} {r['depts']} {r['forming']}")
        check("홍보부" not in r["teams"], "부서는 팀으로 세지 않음")
        g = pg.evaluate("() => { const g = document.querySelector('.cv-guide'); return g ? { mode: g.dataset.guide, lines: g.querySelectorAll('.cvg-list li').length, ok: g.querySelector('.cvg-btn')?.textContent } : null; }")
        check(g == {"mode": "first", "lines": 5, "ok": "알겠어요"}, f"처음 부서 = 가이드 1회 {g}")
        pg.screenshot(path=str(OUT / "e-guide-1280.png"))
        pg.click(".cvg-btn")
        pg.clock.run_for(200)
        seen = pg.evaluate("() => localStorage.getItem('cys-dept-guide-seen')")
        check(seen is not None and pg.evaluate("() => document.querySelectorAll('.cv-guide').length") == 0, f"알겠어요 → 본 적 있음 기록 · 접힘 {seen}")
        ctx.close()
        ctx, pg, errs2 = page(1280, {"cys-dept-guide-seen": seen or "{}"})
        pg.evaluate("() => { window.__DEPTS.push(['dept-1', '/sandbox/dept-1.sock', '홍보부']); }")
        pg.clock.run_for(33_000)
        check(pg.evaluate(RAIL)["depts"] == ["홍보부"] and pg.evaluate("() => document.querySelectorAll('.cv-guide').length") == 0, "다시 켜도 가이드 저절로 0")
        pg.click(".cv-guide-btn")
        pg.clock.run_for(200)
        check(pg.evaluate("() => document.querySelector('.cv-guide')?.dataset.guide") == "again", "「부서 안내」 = 다시 보기")

        print("== F 접근성(글자 18px · 누를 면 44px)")
        a11y = pg.evaluate("""() => { const small = []; for (const e of document.querySelectorAll('.cv-rail *, .cv-guide *, .cv-guide-btn')) { if (!e.childNodes.length || ![...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue; const f = parseFloat(getComputedStyle(e).fontSize); if (f < 18) small.push([e.className, f]); }
          const tiny = [...document.querySelectorAll('.cv-guide-btn, .cvg-btn, .cv-quick-btn')].filter((b) => b.getBoundingClientRect().height < 44).map((b) => b.className); return { small, tiny }; }""")
        check(a11y["small"] == [] and a11y["tiny"] == [], f"18px 미만 0 · 44px 미만 0 {a11y}")
        ctx.close()

        print("== A2 폭별 보임(1024 보임 · 600 숨김)")
        for wdt, want in ((1024, True), (600, False)):
            ctx, pg, e3 = page(wdt)
            r = pg.evaluate(RAIL)
            check(r is not None and r["shown"] is want, f"{wdt} 폭 = {'보임' if want else '숨김'} {r and r['shown']}")
            pg.screenshot(path=str(OUT / f"a-{wdt}.png"))
            errs += e3
            ctx.close()
        check(errs == [] and errs2 == [], f"페이지 오류 0 {errs + errs2}")
        br.close()
    httpd.shutdown()
    print(f"RESULT {'PASS' if not failures else 'FAIL'} · 실패 {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
