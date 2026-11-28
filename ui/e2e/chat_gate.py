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
H 다시 켬: 저장된 화면이 대화 화면 → 대화 화면 보임 · 작업 화면 숨김 · 단추 눌림 = 대화 · 바로 보내기 1(VERIFY 지적 2)
I 보낸 말 단계 전부(조각 3 · TICKET=cysr-ui-slice3-1118): 여러 줄 → 전달됨 · 응답 없이 3초 → 확인 중(단추 0) · 쓰기 직전 거부 사건 → 확인 중 + 안내(부서 데몬 사건 무시)
  · 같은 말 겹침 → 쓰기 0 · 단추 0 → 앞 말 전달 뒤 「한 번 더 보내기」 1회 · 120초 → 오래 걸려요 + 마스터 상태 · 전달 뒤 마스터 일함 → 답하는 중 · 매 장면 「모든 말에 단계 글」(M2)
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
    sendOutcome: { outcome: 'written', result: { sent: true } }, file: [], session: 'sess-0001-aaaa-bbbb', named: [], calls: [], writes: [], fetchLatency: 0, hangMs: 0 };
  const orig = window.__TAURI__.core.invoke;
  const later = (v) => C.fetchLatency > 0 ? new Promise((r) => setTimeout(() => r(v()), C.fetchLatency)) : Promise.resolve(v());
  window.__TAURI__.core.invoke = (cmd, args) => {
    const a = args ?? {};
    C.kinds = C.kinds ?? {}; C.kinds[cmd] = (C.kinds[cmd] ?? 0) + 1; // (s79 · 독립 검증 V4) 모든 invoke 종류 계수(main.ts 몫 포함 — 기준 창을 빼서 씀)
    if (cmd === 'org_status' && (a.socket ?? null) === null) C.org = (C.org ?? 0) + 1; // (s79) 조회 수 상한 단언용 계수(main.ts 몫 포함 — 기준 창을 빼서 씀)
    if (cmd === 'org_status' && (a.socket ?? null) === null)
      return orig(cmd, args).then((r) => later(() => ({ ...r, surfaces: (r.surfaces || []).map((s) => (s.role === 'master' ? { ...s, ...C.master, agent_alive: C.master.agent_alive ?? s.agent_alive } : s)) })));
    if (cmd === 'feed_list') { C.calls.push([Date.now(), cmd]); return later(() => ({ items: C.approvals.map((sid) => ({ kind: 'approval', status: 'pending', surface_id: sid })) })); }
    if (cmd === 'usage_named_reporters') return Promise.resolve({ named: C.named }); // main.ts 도 부른다 — 대화 화면 계수(C.calls)에 넣지 않음
    if (cmd === 'chat_send') {
      C.calls.push([Date.now(), cmd]);
      const w = { t: Date.now(), args: a, refused: C.screen };
      C.writes.push(w);
      const out = C.screen ? { outcome: 'held', code: 'approval_screen', message: 'refused' } : C.sendOutcome;
      if (C.hangMs > 0) return new Promise((r) => setTimeout(() => r(out), C.hangMs)); // (조각 3) 응답이 걸림
      return Promise.resolve(out);
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
        # (s79 · master#cf75d4e2 ②) org_status 기준 창 — 대화 화면을 켜기 전 30초의 org_status(socket null) 수 = main.ts 몫(뒤 E 에서 빼서 공통층 몫만 셈)
        o0 = pg.evaluate("() => window.__CHAT.org ?? 0")
        k0 = pg.evaluate("() => ({ ...(window.__CHAT.kinds ?? {}) })")
        pg.clock.run_for(30_000)
        org_base = pg.evaluate("() => window.__CHAT.org ?? 0") - o0
        k1 = pg.evaluate("() => ({ ...(window.__CHAT.kinds ?? {}) })")
        kinds_base = {k: k1.get(k, 0) - k0.get(k, 0) for k in k1}
        check(pg.evaluate("() => window.__CHAT.calls.length") == 0, f"대화 화면을 안 켠 30초 = 대화 화면 조회 0(그대로) · 기준 org_status {org_base}")

        print("== B 보내기 1 → 쓰기 1(원자) → 전달됨 → 마스터 답")
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(100)
        # (TICKET=cysr-1119-s5 · CV-EX3) 빈 화면 = 제목 · 예시 단추 3(P2-mock 글 그대로 · 44px 이상)
        ex = pg.evaluate("""() => ({ title: document.querySelector('.cv-empty .cv-empty-title')?.textContent ?? null,
            btns: [...document.querySelectorAll('.cv-empty .cv-ex-btn')].map((b) => [b.textContent, Math.round(b.getBoundingClientRect().height)]) })""")
        check(ex["title"] == "마스터에게 맡길 일을 적어 주세요" and [b[0] for b in ex["btns"]] == ["교회 추수감사 행사 안내 페이지 만들어 줘", "이번 주 주보 PDF 정리해 줘", "다음 달 교사 모임 일정을 표로 만들어 줘"] and all(b[1] >= 44 for b in ex["btns"]), f"빈 화면 = 제목 · 예시 단추 3 · 44px 이상 {ex}")
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
        mtxt = pg.evaluate("() => [...document.querySelectorAll('.cv-master .cv-md')].map((e) => e.textContent)")
        check(mtxt == ["네, 듣고 있어요"], f"마스터 답 말풍선 {mtxt}")
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
        pg.clock.run_for(3_100)
        check(last_step(pg) == "답함", f"쉬면 답함 ({last_step(pg)})")
        # (TICKET=cysr-1118u-chat ⑤ · codex 1R minor) 진행 줄 머리 = 펼침 전용 — 과정 기록(마스터 답 a1)이 있는 말에서 실제로 누른다: 눌림 가능 · 펼침/접힘 · 쓰기 0
        w0 = writes(pg)
        ph = lambda: pg.evaluate("() => { const b = document.querySelector('.cv-me button.cv-prog-head'); const box = b?.closest('.cv-prog'); return b ? { dis: b.disabled, exp: b.getAttribute('aria-expanded'), steps: box ? box.querySelectorAll('.cv-steps li').length : -1 } : null; }")  # noqa: E731
        p0 = ph()
        pg.click(".cv-me button.cv-prog-head")
        pg.clock.run_for(50)
        p1 = ph()
        pg.click(".cv-me button.cv-prog-head")
        pg.clock.run_for(50)
        p2 = ph()
        check(p0 is not None and p0["dis"] is False and p0["exp"] == "false" and p1["exp"] == "true" and p1["steps"] > 0 and p2["exp"] == "false" and p2["steps"] == 0 and writes(pg) == w0,
              f"진행 줄 머리 = 펼침 전용(과정 있는 말 · 누름 → 펼침 · 다시 → 접힘 · 쓰기 0) ({p0} → {p1} → {p2} · 쓰기 {w0}→{writes(pg)})")
        # (TICKET=cysr-1119-s4 · CH-D · V4c) 끝난 말 · 글 답만(도구 0) · 걸린 시간 3초 미만 → 요약 조각 없음 · 경과 없음 = 「과정 보기」(펼침 단추 자리) · 옛 「과정 N단계」 0
        ptxt = pg.evaluate("() => document.querySelector('.cv-me .cv-prog-text')?.textContent ?? null")
        check(ptxt == "과정 보기", f"진행 줄 글 = 과정 보기(글 단계는 요약 글에 안 보임 · 3초 미만 경과 없음) ({ptxt})")
        # (TICKET=cysr-1119-s4 · V4) 대화 화면 18px 미만 0 — 펼친 과정 목록까지 포함해 .cv 안 글 있는 요소 전부 getComputedStyle 측정
        pg.click(".cv-me button.cv-prog-head")
        pg.clock.run_for(50)
        small = pg.evaluate("""() => { const out = []; let n = 0;
            for (const e of [document.querySelector('.cv'), ...document.querySelectorAll('.cv *')]) {
              if (!e || e.getClientRects().length === 0) continue;
              const own = [...e.childNodes].some((c) => c.nodeType === 3 && c.textContent.trim() !== '') || e.matches('input, textarea, button');
              if (!own) continue; n += 1;
              const px = parseFloat(getComputedStyle(e).fontSize); if (px < 18) out.push(`${e.tagName.toLowerCase()}.${[...e.classList].join('.')} ${px}px`);
            }
            return { n, out, prog: parseFloat(getComputedStyle(document.querySelector('.cv-prog')).fontSize), items: document.querySelectorAll('.cv-me .cv-steps li').length }; }""")
        pg.click(".cv-me button.cv-prog-head")
        pg.clock.run_for(50)
        check(small["n"] > 10 and small["items"] > 0 and small["prog"] == 18 and small["out"] == [],
              f"대화 화면 18px 미만 0(글 있는 요소 {small['n']} · 펼친 단계 {small['items']} · 진행 줄 {small['prog']}px · 미만 {small['out']})")

        print("== C 문턱 → 쓰기 0 · 붙잡음")
        pg.evaluate("() => { window.__CHAT.approvals = [1]; }")
        say(pg, "둘")
        check(writes(pg) == 1 and last_step(pg) == "보낼 차례 기다림" and "확인할 것" in last_note(pg), f"★수용2 feed 승인 대기 → 쓰기 0 · 붙잡음 ({writes(pg)} · {last_step(pg)} · {last_note(pg)})")
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
        check(writes(pg) == 4 and pg.evaluate("() => window.__CHAT.writes[3].refused") and last_step(pg) == "보낼 차례 기다림", f"승인 창 → 데몬 거부(바이트 0) = 붙잡음 ({last_step(pg)})")
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
        writes_before_work = pg.evaluate("() => window.__CHAT.writes.length")
        # (s79 · codex 3R ③) 계수 기준 = 전환 **전** — 전환 순간(작업 화면 켜기)의 호출도 센다(옛 = 전환 뒤 기준이라 그 순간 default_socket_slug 등을 놓쳤다)
        c0 = pg.evaluate("() => window.__CHAT.calls.length")
        org0 = pg.evaluate("() => window.__CHAT.org ?? 0")
        ke0 = pg.evaluate("() => ({ ...(window.__CHAT.kinds ?? {}) })")
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(100)
        st = pg.evaluate("() => ({ host: document.getElementById('view-host').hidden, body: getComputedStyle(document.getElementById('body-row')).display, cvs: document.querySelectorAll('.cv').length, chatCalls: window.__CHAT.calls.length })")
        check(st["host"] is True and st["body"] != "none" and st["cvs"] == 0, f"작업 화면으로 — 대화 DOM 내림 {st}")
        pg.clock.run_for(29_900)
        ke1 = pg.evaluate("() => ({ ...(window.__CHAT.kinds ?? {}) })")
        extra = {k: (ke1.get(k, 0) - ke0.get(k, 0)) - kinds_base.get(k, 0) for k in ke1}
        # (integ-1120 · s2 × s79 의미 충돌) 작업 화면으로 돌아온 순간 s2 의 onWorkShown → render() 가 좌석을 한 번 맞춘다(resize_surface · 크기 그대로 · 좌석당 1회).
        #   그 한 바퀴 때문에 주기 맞춤의 위상이 밀려 30초 창에 한 바퀴가 더 든다 → 허용 폭 = 「전환 순간 한 바퀴 = 그려진 좌석 수」 만큼만(그 밖 증가는 그대로 붉음).
        n_panes = pg.evaluate("() => document.querySelectorAll('.pane').length")
        # (1.1.19 · S10b AG5 · DESIGN §8-3 D-11 · TICKET=fix-1119-e2e-red3) 작업 화면 첫 진입 = 「자동 보고」 안내 확인 1회(counsel_auto_status · 화면마다 실행당 1회 · main.ts noteViewEntryForReportNotice).
        #   이 실행에서 작업 화면이 처음 보이는 순간이 이 창 안이므로 기대 = **정확히 1**(0 = 계기 빠짐 · 2↑ = 진입 한 번에 여러 번 확인 · 둘 다 붉음).
        #   ⚠ 이 창은 기준 창(대화 화면 켜기 전 30초)을 빼고 세므로 주기 호출(반복 타이머)은 여기서 안 보인다 — 반복 타이머 0 = counselwiring.test.ts 「D-11」 몫.
        counsel_n = extra.get("counsel_auto_status", 0)
        bad_kinds = {k: v for k, v in extra.items() if v > 0 and k not in ("feed_list", "org_status", "chat_transcript", "counsel_auto_status") and not (k == "resize_surface" and v <= n_panes)}
        check(not bad_kinds and all(v <= 11 for v in extra.values()), f"★작업 화면 30초 = 모든 invoke 종류 대조(기준 창 뺌) · 허용 3종 밖 증가 0(resize_surface = 전환 순간 좌석 {n_panes} 한 바퀴까지 · counsel_auto_status = 아래 줄) · 종류마다 ≤ 11 {dict((k, v) for k, v in extra.items() if v)} · 밖 {bad_kinds}")
        check(counsel_n == 1, f"작업 화면 첫 진입 = 안내 확인 counsel_auto_status 정확히 1(D-11 · 화면마다 실행당 1회) ({counsel_n})")
        org_views = pg.evaluate("() => window.__CHAT.org ?? 0") - org0 - org_base
        check(org_views <= 11, f"작업 화면 30초 org_status(공통층 몫 = 전체 − 기준 창) ≤ 11 ({org_views})")
        c1 = pg.evaluate("() => window.__CHAT.calls.length")
        # (s79 · 조각 9 FR-C7 · master 질의 중 기본값 A) 대화 화면을 이번 실행에서 켠 적이 있으면 작업 화면 띠가 같은 자료를 받는다 —
        #   조회는 feed_list·chat_transcript 만 · 쓰기 0. (대화 화면을 안 켠 실행의 「조회 0」 은 tickrec_gate · s79_gate A 가 지킨다.)
        calls30 = pg.evaluate(f"() => window.__CHAT.calls.slice({c0})")
        kinds = {c[1] for c in calls30}
        w30 = pg.evaluate("() => window.__CHAT.writes.length")
        check(kinds <= {"feed_list", "chat_transcript"} and w30 == writes_before_work, f"작업 화면일 때 = 쓰기 0 · 조회는 띠 자료 종류만 (30초 · {c1 - c0} · {sorted(kinds)} · 쓰기 {writes_before_work}→{w30})")
        # (master#cf75d4e2 ②) 조회 수 상한 — 30초에 종류마다 ≤ 11(3초 주기 10회 + 경계 1) · feed_list 간격 ≥ 3초(주기 ≥3초)
        per = {k: sum(1 for c in calls30 if c[1] == k) for k in kinds}
        ts = [c[0] for c in calls30 if c[1] == "feed_list"]
        gaps = [b - a for a, b in zip(ts, ts[1:])]
        check(all(v <= 11 for v in per.values()) and all(g >= 2_999 for g in gaps), f"작업 화면 조회 상한 30초 종류마다 ≤ 11 · 주기 ≥ 3초 {per} · 최소 간격 {min(gaps) if gaps else None}ms")
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
        check(writes(pg) == 0 and last_step(pg) == "보낼 차례 기다림", f"마스터 없음 → 쓰기 0 · 붙잡음 ({last_step(pg)})")
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

        print("== H 다시 켬 — 저장된 화면이 대화 화면(VERIFY 지적 2)")
        ctx = br.new_context(viewport={"width": 1400, "height": 900})
        ctx.clock.install(time=T0)
        ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        pg.add_init_script(shim)
        pg.add_init_script(CHAT_SHIM)
        pg.add_init_script("""localStorage.setItem('cys-view', JSON.stringify({ v: 1, id: 'chat', decidedBy: 'user' }))""")
        pg.goto(url)
        pg.clock.run_for(9_000)
        pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}); }}")
        pg.clock.run_for(6_000)
        st = pg.evaluate("""() => ({ host: document.getElementById('view-host').hidden, body: getComputedStyle(document.getElementById('body-row')).display,
            cvVisible: !!document.querySelector('.cv') && document.querySelector('.cv').offsetParent !== null,
            pressed: [...document.querySelectorAll('#view-switch button')].map((b) => [b.textContent, b.getAttribute('aria-pressed')]) })""")
        check(st["host"] is False and st["body"] == "none" and st["cvVisible"], f"저장 화면(대화) 그대로 보임 · 작업 화면 숨김 {st}")
        check(st["pressed"] == [["대화 화면", "true"], ["작업 화면", "false"]], f"단추 눌림 = 대화 {st['pressed']}")
        say(pg, "안녕")
        check(writes(pg) == 1, f"다시 켠 대화 화면에서 바로 보내기 = 쓰기 1 ({writes(pg)})")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()

        print("== I 보낸 말 단계 전부(조각 3)")
        ctx, pg, errs = page([seat(BASE, 1, "master")])
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_100)
        every_step = lambda pg: pg.evaluate("() => [...document.querySelectorAll('.cv-me')].every((li) => (li.querySelector('.cv-step')?.textContent || '').length > 0)")  # noqa: E731
        # (TICKET=cysr-1118u-chat ⑤) 1.1.17 진행 줄(cysr-1118-ui ①) 머리 button.cv-prog-head = 「과정 보기」 펼침 전용(쓰기 0 · 단계 없으면 disabled) — 「단추 0」(다시 보내기·보내기 단추) 셈에서 뺀다.
        bubble = lambda pg, i: pg.evaluate(f"() => {{ const li = [...document.querySelectorAll('.cv-me')][{i}]; return li ? {{ step: li.querySelector('.cv-step').textContent, note: [...li.querySelectorAll('.cv-note')].map((n) => n.textContent).join(' | '), btns: [...li.querySelectorAll('button:not(.cv-prog-head)')].map((b) => b.textContent), prog: li.querySelectorAll('button.cv-prog-head').length }} : null; }}")  # noqa: E731
        n0 = writes(pg)
        pg.fill(".cv-input", "첫 줄\n둘째 줄")
        pg.press(".cv-input", "Enter")
        pg.clock.run_for(50)
        w = pg.evaluate("() => window.__CHAT.writes.map((x) => x.args.text)")
        check(w[-1] == "첫 줄\n둘째 줄" and writes(pg) == n0 + 1, f"여러 줄 = 줄바꿈 그대로 쓰기 1 ({w[-1]!r})")
        pg.evaluate("""() => { const C = window.__CHAT; C.file.push({ uuid: 'm1', parent: 'p0', role: 'user', text: '첫 줄\\r\\n둘째 줄', ts: new Date(Date.now()).toISOString() }); }""")
        pg.clock.run_for(1_100)
        check(bubble(pg, 0)["step"] == "전달됨", f"여러 줄 기록(CRLF) 전문 일치 → 전달됨 ({bubble(pg, 0)})")
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 0; }")
        pg.clock.run_for(3_100)
        check(bubble(pg, 0)["step"] == "답하는 중", f"전달 뒤 마스터 일함 → 답하는 중(답 글 전) ({bubble(pg, 0)['step']})")
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
        pg.clock.run_for(40_000)  # 사람 입력 30초 묶음 지나기
        # 응답 없이 3초
        pg.evaluate("() => { window.__CHAT.hangMs = 6_000; }")
        n0 = writes(pg)
        say(pg, "걸린 말")
        pg.clock.run_for(1_000)
        check(bubble(pg, 1)["step"] == "보내는 중", f"응답 전 = 보내는 중 ({bubble(pg, 1)['step']})")
        pg.clock.run_for(2_100)
        b = bubble(pg, 1)
        check(b["step"] == "확인 중" and b["btns"] == [] and every_step(pg), f"응답 없이 3초 → 확인 중 · 단추 0 · 모든 말 단계 글 ({b})")
        # (TICKET=cysr-1118u-chat ⑤) 뺀 진행 줄 머리가 정말 보내기 단추가 아닌지 — 눌러도 쓰기 0(펼침만)
        wpg = writes(pg)
        pg.evaluate("() => { const li = [...document.querySelectorAll('.cv-me')].at(-1); li?.querySelector('button.cv-prog-head')?.click(); }")
        pg.clock.run_for(50)
        dis = pg.evaluate("() => !![...document.querySelectorAll('.cv-me')].at(-1)?.querySelector('button.cv-prog-head')?.disabled")
        check(b["prog"] == 1 and dis and writes(pg) == wpg, f"과정 기록 없는 말의 진행 줄 머리 1개 = 누를 수 없음(disabled) · 쓰기 0 ({b['prog']} · disabled {dis} · {wpg}→{writes(pg)})")
        pg.clock.run_for(3_000)
        check(bubble(pg, 1)["step"] == "전달 확인 중" and writes(pg) == n0 + 1, f"응답(written) 도착 → 전달 확인 중 · 쓰기 1 ({bubble(pg, 1)['step']})")
        pg.evaluate("() => { window.__CHAT.hangMs = 0; }")
        pg.clock.run_for(40_000)
        # 쓰기 직전 거부 사건
        say(pg, "창 뜬 말")
        pg.clock.run_for(300)
        pg.evaluate("() => window.__emit('daemon-event', { name: 'input.refused_at_write', surface_id: 1, seq: 9001, socket_slug: 'dept-x', timestamp: Date.now() / 1000, payload: { reason: 'approval_screen' } })")
        check(bubble(pg, 2)["step"] == "전달 확인 중", f"부서 데몬(다른 소켓) 사건 = 무시 ({bubble(pg, 2)['step']})")
        pg.evaluate("() => window.__emit('daemon-event', { name: 'input.refused_at_write', surface_id: 1, seq: 9002, socket_slug: 'base', timestamp: Date.now() / 1000, payload: { reason: 'approval_screen' } })")
        pg.clock.run_for(50)
        b = bubble(pg, 2)
        check(b["step"] == "확인 중" and "제출이 멈췄을 수" in b["note"] and "Enter 를 누르" not in b["note"] and b["btns"] == [], f"쓰기 직전 거부 사건(통합 빌드 e4499d72 꼴) → 확인 중 + 안내(Enter 권하지 않음) · 다시 보내기 0 ({b})")
        pg.evaluate("() => window.__emit('daemon-event', { name: 'input.refused_at_write', surface_id: 1, seq: 9003, socket_slug: 'base', timestamp: Date.now() / 1000 - 60, payload: { reason: 'approval_screen' } })")
        pg.clock.run_for(40_000)
        # 같은 말 겹침
        pg.evaluate("() => { window.__CHAT.sendOutcome = { outcome: 'uncertain', code: 'transport_uncertain' }; }")
        say(pg, "같은 말")
        pg.evaluate("() => { window.__CHAT.sendOutcome = { outcome: 'written', result: { sent: true } }; }")
        n0 = writes(pg)
        say(pg, "같은 말")
        pg.clock.run_for(40_000)
        b = bubble(pg, 4)
        check(writes(pg) == n0 and b["step"] == "아직 안 보냄" and "같은 말" in b["note"] and b["btns"] == ["보내지 않기"], f"불명 뒤 같은 말 → 쓰기 0 · 붙잡음 · 단추 0 ({writes(pg) - n0} · {b})")
        pg.evaluate("""() => { const C = window.__CHAT; C.file.push({ uuid: 'm4', parent: 'm1', role: 'user', text: '같은 말', ts: new Date(Date.now()).toISOString() }); }""")
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 0; }")
        pg.clock.run_for(3_100)
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
        pg.clock.run_for(3_100)
        b3, b4 = bubble(pg, 3), bubble(pg, 4)
        # ★(TICKET=cysr-1121-ui-kfix2 ② · 통합 codex 3R major) 앞 말은 불명 응답 — 같은 글 기록이 이 화면 것인지 모름 = 「확인 못 함」 → 겹친 말은 계속 막힘(두 번 쓰기 0).
        #   예전 기대(「한 번 더 보내기」 → 쓰기 1)는 불명 시도에서 같은 말이 두 번 가는 길이었다. 글을 바꾸면 새 말로 나간다.
        check(b3["step"] == "확인 못 함" and b4["btns"] == ["보내지 않기"] and "확인 못 함" in b4["note"], f"불명 앞 말에 같은 글 기록 → 「확인 못 함」 · 겹친 말 「한 번 더 보내기」 0 ({b3['step']} · {b4['btns']} · {b4['note']})")
        check(writes(pg) == n0, f"확인 못 함 동안 같은 글 쓰기 0 ({writes(pg) - n0})")
        pg.clock.run_for(40_000)
        # 120초 → 오래 걸려요 + 마스터 상태
        pg.evaluate("() => { window.__CHAT.sendOutcome = { outcome: 'uncertain', code: 'transport_uncertain' }; }")
        n0 = writes(pg)
        say(pg, "느린 말")
        last = pg.evaluate("() => document.querySelectorAll('.cv-me').length") - 1
        ok_all = True
        for _ in range(24):  # 120초를 5초씩 걸으며 M2(모든 말 단계 글) 표본
            pg.clock.run_for(5_000)
            ok_all = ok_all and every_step(pg)
        pg.clock.run_for(3_500)  # 120초 뒤 첫 3초 조회에서 바뀜(조회 박자 ≤ 3초)
        b = bubble(pg, last)
        check(b["step"] == "확인이 오래 걸려요" and "마스터 상태:" in b["note"] and b["btns"] == [] and writes(pg) == n0 + 1, f"120초 → 오래 걸려요 + 마스터 상태 · 다시 보내기 0 · 재전송 0 ({b})")
        check(ok_all and every_step(pg), "120초 동안 5초 표본 모두 「모든 말에 단계 글」(M2)")
        if not ok_all or b["step"] != "확인이 오래 걸려요":
            print("  (진단) 말 목록:", pg.evaluate("() => [...document.querySelectorAll('.cv-me')].map((li) => li.querySelector('.cv-text').textContent + ' = ' + li.querySelector('.cv-step').textContent)"))
            print("  (진단) 쓰기:", pg.evaluate("() => window.__CHAT.writes.slice(-3).map((w) => [w.t % 1000000, w.args.text, w.refused])"))
            print("  (진단) 마지막 조회들:", pg.evaluate("() => window.__CHAT.calls.slice(-6).map(([t, c]) => [t % 1000000, c])"), pg.evaluate("() => Date.now() % 1000000"))
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()

        print("== J 조각 3 고침(검증 지적 H · B · A) — 그려진 화면")
        ctx, pg, errs = page([seat(BASE, 1, "master")])
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_100)
        # (TICKET=cysr-1118u-chat ⑤) 1.1.17 진행 줄(cysr-1118-ui ①) 머리 button.cv-prog-head = 「과정 보기」 펼침 전용(쓰기 0 · 단계 없으면 disabled) — 「단추 0」(다시 보내기·보내기 단추) 셈에서 뺀다.
        bubble = lambda pg, i: pg.evaluate(f"() => {{ const li = [...document.querySelectorAll('.cv-me')][{i}]; return li ? {{ step: li.querySelector('.cv-step').textContent, note: [...li.querySelectorAll('.cv-note')].map((n) => n.textContent).join(' | '), btns: [...li.querySelectorAll('button:not(.cv-prog-head)')].map((b) => b.textContent), prog: li.querySelectorAll('button.cv-prog-head').length }} : null; }}")  # noqa: E731
        pg.evaluate("() => { window.__CHAT.sendOutcome = { outcome: 'failed', code: 'not_found', message: 'gone' }; }")
        say(pg, "같은 글")
        pg.clock.run_for(100)
        check(bubble(pg, 0)["btns"] == ["다시 보내기"], f"확정 실패 X = 다시 보내기 단추 ({bubble(pg, 0)})")
        pg.evaluate("() => { window.__CHAT.sendOutcome = { outcome: 'written', result: { sent: true } }; }")
        n0 = writes(pg)
        say(pg, "같은 글")
        pg.evaluate("""() => { const C = window.__CHAT; C.file.push({ uuid: 'j1', parent: 'p0', role: 'user', text: '같은 글', ts: new Date(Date.now()).toISOString() }); }""")
        pg.clock.run_for(1_100)
        bx, by = bubble(pg, 0), bubble(pg, 1)
        check(by["step"] == "전달됨" and bx["btns"] == [] and "이미 전달됐어요" in bx["note"] and writes(pg) == n0 + 1, f"같은 글 Y 전달됨 → X 다시 보내기 거둠 + 안내 ({bx} · {by['step']})")
        pg.clock.run_for(40_000)
        # B: 고리를 지나 답이 그 말에 붙음 · 안 묶인 답은 시각순
        t_mid = pg.evaluate("() => Date.now()")
        pg.clock.run_for(40_000)
        say(pg, "고리 말")
        pg.evaluate(f"""() => {{ const C = window.__CHAT; const ts = new Date(Date.now()).toISOString();
          C.file.push({{ uuid: 'j2', parent: 'j1', role: 'user', text: '\\n\\n<pasted_content id="3f02">\\n고리 말\\n</pasted_content id="3f02">\\n', ts }});
          C.file.push({{ uuid: 'j3', parent: 'j2', role: 'link', text: null, parts: null, ts: null, sidechain: false }});
          C.file.push({{ uuid: 'j4', parent: 'j3', role: 'assistant', text: '고리 답', ts }});
          C.file.push({{ uuid: 'j5', parent: 'nowhere', role: 'assistant', text: '떠돌이 답', ts: new Date({t_mid}).toISOString() }}); }}""")
        pg.clock.run_for(8_000)
        order = pg.evaluate("() => [...document.querySelectorAll('.cv-log > li')].map((li) => li.querySelector('.cv-text, .cv-md')?.textContent ?? '')")
        b2 = bubble(pg, 2)
        check(b2["step"] in ("전달됨", "답하는 중", "답함") and order.index("고리 답") == order.index("고리 말") + 1, f"감싼 기록 + 고리 → 그 말에 답이 붙음 ({b2['step']} · {order})")
        check(order.index("떠돌이 답") < order.index("고리 말"), f"안 묶인 답 = 시각순(뒤 말 앞) ({order})")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()

        print("== G 경합 기록 — 보내는 중 승인 창(대역 시각 주입)")
        for lag in (() if os.environ.get("CHAT_GATE_SKIP_RACE") else (0, 1000)):  # 진단용 건너뛰기(수용 실행에서는 쓰지 않음)
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
