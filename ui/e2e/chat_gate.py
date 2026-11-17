#!/usr/bin/env python3
"""대화 화면 조각 1 게이트 — TICKET=cysr-ui-slice1-1117 · P2-DESIGN §11 조각 1 (수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(tickrec_gate.py 의 SHIM 위에 대화 화면 명령 대역을 덧씌움) + 가짜 시계(멈춘 시계 · 실제 기다림 0).
판정 단위: 「PTY 쓰기 = chat_send 호출」(원자 제출 1요청 = 쓰기 1 · 데몬 승인 창 거부는 바이트 0 = 쓰기 0 으로 셈).

A 기본: 시작 = 작업 화면 · 대화 화면 명령 0 · cys-view 쓰기 0
B 보내기: 대화 화면 → 「안녕」 → 쓰기 1(kind human · 마스터 좌석) → 「전달 확인 중」 → 세션 기록 전문 일치 → 「전달됨」 → 마스터 답 말풍선 → 쉬면 「답함」
C 문턱: feed 승인 대기 → 쓰기 0 · 붙잡음 → 풀리면 1건 / 사람 초안 12바이트 → 쓰기 0 → 비면 1건 / `/clear`·`\\u0001/clear` → 쓰기 0
D 응답: 데몬 승인 창 거부 → 붙잡음 · 쉼 동안 재시도 0 · 창 닫힘 뒤 1건 / 불명 → 「확인 중」 · 다시 보내기 단추 0 · 30초에도 재전송 0 / 확정 실패 → 「못 보냄」 + 다시 보내기 1회
E 전환: 초안 왕복 같음 · 최소 계약 4칸 + 공통 전환 단추 · 두 화면 동시 노출 0
F 가용: 새 설치(좌석 0)·마스터 꺼짐 → 흐림 0 / cys 밖 마스터(이름 보고 최근) ∧ cys 마스터 없음 → 전환 0 + 까닭 띠
G 경합(기록): 「보내는 중 승인 창」 — 승인 창이 누름 전후 −1.5~+1.5초(100ms 간격) 중 한 시각에 뜰 때, 화면 문턱·데몬 거부·새는 경우의 비율(대역 시각 주입 · 데몬 Enter 직전 재판정 없음 가정 = 0.5 M2-c)
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/chat_gate.py
"""
import http.server
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tickrec_gate import BASE, CWD, SHIM, seat  # noqa: E402  (같은 대역 위에 덧씌운다)

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"
ATOMIC_MS = 768  # 0.5 M1 실측 Ctrl-U→Enter 중앙값(728.1 / 767.9 / 835.2 ms)

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


CHAT_SHIM = r"""
(() => {
  const C = window.__CHAT = { approvals: [], screen: false, master: { pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, idle_secs: 999, status: null },
    sendOutcome: { outcome: 'written', result: { sent: true } }, file: [], session: 'sess-0001-aaaa-bbbb', named: [], calls: [], writes: [], fetchLatency: 0 };
  const orig = window.__TAURI__.core.invoke;
  const later = (v) => C.fetchLatency > 0 ? new Promise((r) => setTimeout(() => r(v()), C.fetchLatency)) : Promise.resolve(v());
  window.__TAURI__.core.invoke = (cmd, args) => {
    const a = args ?? {};
    if (cmd === 'org_status' && (a.socket ?? null) === null)
      return orig(cmd, args).then((r) => later(() => ({ ...r, surfaces: (r.surfaces || []).map((s) => (s.role === 'master' ? { ...s, ...C.master, agent_alive: C.master.agent_alive ?? s.agent_alive } : s)) })));
    if (cmd === 'feed_list') { C.calls.push([Date.now(), cmd]); return later(() => ({ items: C.approvals.map((sid) => ({ kind: 'approval', status: 'pending', surface_id: sid })) })); }
    if (cmd === 'usage_named_reporters') return Promise.resolve({ named: C.named }); // main.ts 도 부른다 — 대화 화면 계수(C.calls)에 넣지 않음
    if (cmd === 'chat_send') {
      C.calls.push([Date.now(), cmd]);
      const w = { t: Date.now(), args: a, refused: C.screen };
      C.writes.push(w);
      return Promise.resolve(C.screen ? { outcome: 'held', code: 'approval_screen', message: 'refused' } : C.sendOutcome);
    }
    if (cmd === 'chat_transcript') {
      C.calls.push([Date.now(), cmd]);
      if (a.fromEnd) return Promise.resolve({ status: 'ok', session_id: C.session, next_offset: C.file.length, size: C.file.length, records: [] });
      return Promise.resolve({ status: 'ok', session_id: C.session, next_offset: C.file.length, size: C.file.length, records: C.file.slice(a.afterOffset) });
    }
    return orig(cmd, args);
  };
})();
"""

T0 = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)


def main() -> int:
    from playwright.sync_api import sync_playwright

    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
    report: dict = {}
    with sync_playwright() as p:
        exe = os.environ.get("CHROME_PATH")
        br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

        def page(seats: list[str], named_fresh: bool = False):
            ctx = br.new_context(viewport={"width": 1400, "height": 900})
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.goto(url)
            pg.clock.run_for(9_000)
            if seats:
                pg.evaluate(f"() => {{ window.__SEATS.push({', '.join(seats)}); }}")
            if named_fresh:
                pg.evaluate("() => { window.__CHAT.named = [{ name: 'master', updated_at: Date.now() / 1000, ctx_pct: 10 }]; }")
            pg.clock.run_for(15_000)
            return ctx, pg, errs

        writes = lambda pg: pg.evaluate("() => window.__CHAT.writes.length")  # noqa: E731
        last_step = lambda pg: pg.evaluate("() => { const s = [...document.querySelectorAll('.cv-me .cv-step')]; return s.length ? s[s.length - 1].textContent : null; }")  # noqa: E731
        last_note = lambda pg: pg.evaluate("() => { const s = [...document.querySelectorAll('.cv-me')]; const n = s.length ? s[s.length - 1].querySelector('.cv-note') : null; return n ? n.textContent : ''; }")  # noqa: E731

        def say(pg, text: str) -> None:
            pg.fill(".cv-input", text)
            pg.press(".cv-input", "Enter")
            pg.clock.run_for(50)

        ctx, pg, errs = page([seat(BASE, 1, "master"), seat(BASE, 2, "cso")])
        print("== A 기본 = 작업 화면")
        st = pg.evaluate("""() => ({ host: document.getElementById('view-host').hidden, body: getComputedStyle(document.getElementById('body-row')).display,
            pressed: [...document.querySelectorAll('#view-switch button')].map((b) => [b.textContent, b.getAttribute('aria-pressed')]),
            view: localStorage.getItem('cys-view'), chatCalls: window.__CHAT.calls.length, cvs: document.querySelectorAll('.cv').length })""")
        check(st["host"] is True and st["body"] != "none", f"작업 화면 보임 · 대화 자리 숨김 {st['host']} {st['body']}")
        check(st["pressed"] == [["대화 화면", "false"], ["작업 화면", "true"]], f"전환 단추 「대화 화면 | 작업 화면」 · 눌림 = 작업 {st['pressed']}")
        check(st["view"] is None and st["chatCalls"] == 0 and st["cvs"] == 0, f"대화 화면 명령 0 · cys-view 쓰기 0 · 대화 DOM 0 ({st['chatCalls']} · {st['view']})")

        print("== B 보내기 1 → 쓰기 1(원자) → 전달됨 → 마스터 답")
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(100)
        st = pg.evaluate("""() => ({ host: document.getElementById('view-host').hidden, body: getComputedStyle(document.getElementById('body-row')).display,
            view: JSON.parse(localStorage.getItem('cys-view') || 'null'), mins: ['confirms', 'lastSendStep', 'masterHealth', 'errors'].map((k) => !!document.querySelector(`#view-host [data-min=${k}]`)),
            health: document.querySelector('[data-min=masterHealth]')?.textContent, focus: document.activeElement?.className })""")
        check(st["host"] is False and st["body"] == "none", f"대화 화면 보임 · 작업 화면 숨김(두 화면 동시 노출 0) {st['host']} {st['body']}")
        check(st["view"] == {"v": 1, "id": "chat", "decidedBy": "user"}, f"고른 화면 기억 {st['view']}")
        check(all(st["mins"]), f"최소 계약 4칸 + 공통 전환 단추 {st['mins']}")
        check(st["health"] == "마스터가 듣고 있어요", f"마스터 상태 {st['health']}")
        check(st["focus"] == "cv-input", f"입력칸 포커스 {st['focus']}")
        say(pg, "안녕")
        w = pg.evaluate("() => window.__CHAT.writes.map((x) => x.args)")
        check(len(w) == 1 and w[0] == {"socket": None, "surfaceId": 1, "text": "안녕", "kind": "human"}, f"쓰기 1 · kind human · 마스터 좌석 {w}")
        check(last_step(pg) == "전달 확인 중", f"단계 = 전달 확인 중 ({last_step(pg)})")
        pg.evaluate("""() => { const C = window.__CHAT; const t = new Date(Date.now()).toISOString();
            C.file.push({ uuid: 'u1', parent: 'p0', role: 'user', text: '안녕', ts: t }, { uuid: 'a1', parent: 'u1', role: 'assistant', text: '네, 듣고 있어요', ts: t }); C.master.idle_secs = 0; }""")
        pg.clock.run_for(1_100)
        check(last_step(pg) in ("전달됨", "답하는 중"), f"전문 일치 → 전달됨/답하는 중 ({last_step(pg)})")
        mtxt = pg.evaluate("() => [...document.querySelectorAll('.cv-master .cv-text')].map((e) => e.textContent)")
        check(mtxt == ["네, 듣고 있어요"], f"마스터 답 말풍선 {mtxt}")
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
        pg.clock.run_for(3_100)
        check(last_step(pg) == "답함", f"쉬면 답함 ({last_step(pg)})")

        print("== C 문턱 → 쓰기 0 · 붙잡음")
        pg.evaluate("() => { window.__CHAT.approvals = [1]; }")
        say(pg, "둘")
        check(writes(pg) == 1 and last_step(pg) == "붙잡아 둠" and "확인할 것" in last_note(pg), f"★수용2 feed 승인 대기 → 쓰기 0 · 붙잡음 ({writes(pg)} · {last_step(pg)} · {last_note(pg)})")
        pg.evaluate("() => { window.__CHAT.approvals = []; }")
        pg.clock.run_for(3_100)
        check(writes(pg) == 2 and pg.evaluate("() => window.__CHAT.writes[1].args.text") == "둘", f"풀리면 붙잡은 말 1건 ({writes(pg)})")
        pg.evaluate("() => { Object.assign(window.__CHAT.master, { pending_input_bytes: 12, pending_input_human_bytes: 12 }); }")
        say(pg, "셋")
        check(writes(pg) == 2 and "쓰다 만 글" in last_note(pg), f"★수용1 사람 초안 12바이트 → 쓰기 0 · 붙잡음 ({writes(pg)} · {last_note(pg)})")
        pg.clock.run_for(9_000)
        check(writes(pg) == 2, f"초안이 남아 있는 동안 3틱 지나도 쓰기 0 ({writes(pg)})")
        pg.evaluate("() => { Object.assign(window.__CHAT.master, { pending_input_bytes: 0, pending_input_human_bytes: 0 }); }")
        pg.clock.run_for(3_100)
        check(writes(pg) == 3, f"초안이 비면 1건 ({writes(pg)})")
        for bad in ["/clear", "\u0001/clear", "!ls"]:
            pg.fill(".cv-input", bad)
            pg.press(".cv-input", "Enter")
            pg.clock.run_for(50)
        notice = pg.evaluate("() => document.querySelector('.cv-notice').textContent")
        check(writes(pg) == 3 and "명령" in notice, f"`/clear`·`\\u0001/clear`·`!ls` → 쓰기 0 · 안내 ({writes(pg)} · {notice[:30]})")

        print("== D 데몬 응답")
        pg.evaluate("() => { window.__CHAT.screen = true; }")
        say(pg, "넷")
        check(writes(pg) == 4 and pg.evaluate("() => window.__CHAT.writes[3].refused") and last_step(pg) == "붙잡아 둠", f"승인 창 → 데몬 거부(바이트 0) = 붙잡음 ({last_step(pg)})")
        pg.clock.run_for(9_000)
        check(writes(pg) == 4, f"쉼(15초) 동안 재시도 0 ({writes(pg)})")
        pg.evaluate("() => { window.__CHAT.screen = false; }")
        pg.clock.run_for(9_000)
        check(writes(pg) == 5 and not pg.evaluate("() => window.__CHAT.writes[4].refused"), f"창 닫힘 + 쉼 뒤 1건 ({writes(pg)})")
        pg.evaluate("() => { window.__CHAT.sendOutcome = { outcome: 'uncertain', code: 'transport_uncertain' }; }")
        say(pg, "다섯")
        retry_btn = pg.evaluate("() => { const s = [...document.querySelectorAll('.cv-me')]; return !!s[s.length - 1].querySelector('.cv-retry'); }")
        check(last_step(pg) == "확인 중" and not retry_btn, f"불명 → 「확인 중」 · 다시 보내기 단추 0 ({last_step(pg)} · {retry_btn})")
        pg.clock.run_for(30_000)
        check(writes(pg) == 6, f"불명 뒤 30초 재전송 0 ({writes(pg)})")
        pg.evaluate("() => { window.__CHAT.sendOutcome = { outcome: 'failed', code: 'not_found', message: 'gone' }; }")
        say(pg, "여섯")
        check(last_step(pg) == "못 보냄" and pg.evaluate("() => !!document.querySelector('.cv-retry')"), f"확정 실패 → 못 보냄 + 다시 보내기 ({last_step(pg)})")
        pg.click(".cv-retry")
        pg.clock.run_for(50)
        check(writes(pg) == 8 and pg.evaluate("() => document.querySelectorAll('.cv-retry').length") == 0, f"다시 보내기 1회 → 쓰기 +1 · 더 없음 ({writes(pg)})")
        pg.evaluate("() => { window.__CHAT.sendOutcome = { outcome: 'written', result: { sent: true } }; }")

        print("== E 전환 왕복 · 초안")
        pg.fill(".cv-input", "쓰다 만 말")
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(100)
        st = pg.evaluate("() => ({ host: document.getElementById('view-host').hidden, body: getComputedStyle(document.getElementById('body-row')).display, cvs: document.querySelectorAll('.cv').length, chatCalls: window.__CHAT.calls.length })")
        check(st["host"] is True and st["body"] != "none" and st["cvs"] == 0, f"작업 화면으로 — 대화 DOM 내림 {st}")
        c0 = st["chatCalls"]
        pg.clock.run_for(30_000)
        c1 = pg.evaluate("() => window.__CHAT.calls.length")
        check(c1 == c0, f"작업 화면일 때 대화 화면 조회 0 (30초 · {c1 - c0})")
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(100)
        v = pg.evaluate("() => document.querySelector('.cv-input').value")
        check(v == "쓰다 만 말" and writes(pg) == 8, f"초안 왕복 같음 · 쓰기 0 ({v!r})")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()

        print("== F 가용 판정(긍정 신호만)")
        ctx, pg, errs = page([])
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(100)
        st = pg.evaluate("() => ({ cvs: document.querySelectorAll('.cv').length, h: document.querySelector('[data-min=masterHealth]')?.textContent })")
        check(st["cvs"] == 1 and st["h"] == "마스터 준비 중", f"새 설치(좌석 0) → 대화 화면 열림 · 「마스터 준비 중」 {st}")
        say(pg, "안녕")
        check(writes(pg) == 0 and last_step(pg) == "붙잡아 둠", f"마스터 없음 → 쓰기 0 · 붙잡음 ({last_step(pg)})")
        ctx.close()
        ctx, pg, errs = page([seat(BASE, 1, "master")])
        pg.evaluate("() => { window.__CHAT.master.agent_alive = false; }")
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(100)
        check(pg.evaluate("() => document.querySelectorAll('.cv').length") == 1, "마스터 꺼짐 → 흐림 0(대화 화면 열림)")
        ctx.close()
        ctx, pg, errs = page([], named_fresh=True)
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(100)
        st = pg.evaluate("""() => ({ cvs: document.querySelectorAll('.cv').length, band: document.querySelector('#view-switch .vs-band')?.textContent,
            dim: document.querySelector('#view-switch button[data-view=chat]').classList.contains('vs-dim'), view: localStorage.getItem('cys-view') })""")
        check(st["cvs"] == 0 and st["dim"] and "cysr 밖" in (st["band"] or "") and st["view"] is None, f"cys 밖 마스터 최근 ∧ cys 마스터 없음 → 전환 0 · 흐림 · 까닭 띠 · 저장 0 {st}")
        ctx.close()

        print("== G 경합 기록 — 보내는 중 승인 창(대역 시각 주입)")
        for lag in (0, 1000):
            counts = {"screen_gate": 0, "daemon_refused": 0, "leak_enter": 0, "no_overlap": 0}
            offsets = list(range(-1500, 1501, 100))
            for d in offsets:
                ctx, pg, errs = page([seat(BASE, 1, "master")])
                pg.click("#view-switch button[data-view=chat]")
                pg.clock.run_for(3_100)
                pg.evaluate("() => { window.__CHAT.fetchLatency = 20; }")
                # 승인 창이 누름 시각 + d 에 뜬다(d<0 이면 이미 떠 있음) · feed 대기 항목은 lag 뒤에 생긴다
                pre = max(0, -d)
                if pre > 0:
                    pg.evaluate(f"() => {{ setTimeout(() => {{ window.__CHAT.screen = true; }}, 0); setTimeout(() => {{ window.__CHAT.approvals = [1]; }}, {lag}); }}")
                    pg.clock.run_for(pre)
                else:
                    pg.evaluate(f"() => {{ setTimeout(() => {{ window.__CHAT.screen = true; }}, {d}); setTimeout(() => {{ window.__CHAT.approvals = [1]; }}, {d + lag}); }}")
                t_click = pg.evaluate("() => Date.now()")
                say(pg, "경합")
                pg.clock.run_for(2_000)
                w = pg.evaluate("() => window.__CHAT.writes")
                screen_at = t_click + d
                if not w:
                    counts["screen_gate"] += 1
                elif w[0]["refused"]:
                    counts["daemon_refused"] += 1
                elif w[0]["t"] < screen_at <= w[0]["t"] + ATOMIC_MS:
                    counts["leak_enter"] += 1
                else:
                    counts["no_overlap"] += 1
                ctx.close()
            racing = len(offsets) - counts["no_overlap"]
            blocked = counts["screen_gate"] + counts["daemon_refused"]
            pct = round(100 * blocked / racing, 1) if racing else None
            report[f"lag{lag}"] = {"offsets": len(offsets), **counts, "racing": racing, "blocked_pct": pct, "screen_gate_pct": round(100 * counts["screen_gate"] / racing, 1) if racing else None}
            print(f"  feed 지연 {lag}ms: {report[f'lag{lag}']}")
            check(counts["leak_enter"] > 0, f"남는 창 재현됨(데몬 Enter 직전 재판정 없음 가정) leak={counts['leak_enter']} — 0.5 M2-c 와 같은 방향")
    out = Path(os.environ.get("CHAT_GATE_OUT") or (Path(os.environ.get("TMPDIR", "/tmp")) / "chat-gate-race.json"))
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  경합 기록:", out)
    httpd.shutdown()
    print("\nRESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
