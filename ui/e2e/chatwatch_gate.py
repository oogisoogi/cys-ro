#!/usr/bin/env python3
"""(1.1.19 · TICKET=cysr-1119-s3 · CH-C) 기록 바뀌면 곧 보이기 — 실제 번들(ui/dist) + 대역 Tauri 위에서 watch 길을 본다.

장면 = P0 K3b(「계기 없는 덧붙임 → 화면」 · 1.1.18 = 안 옴 · review/evidence/p0/vm/RESULT.md §3):
  A. 되돌리기 끔: 대화 화면을 켜면 watch 1회(3초 조회의 결속 id 로) → 기록 끝에 assistant 줄 하나 + 사건 1 → 0.3초 안 DOM 에 보임 ·
     그 읽기는 tail(RPC 0)이고 기존 chat_transcript(데몬 RPC 2) 수는 늘지 않음 · 작업 화면으로 → unwatch 1 · 대화 화면으로 → 다시 watch.
  B. 되돌리기 켬(chat_compat_env = true): watch·tail 0 · 같은 덧붙임은 10초 동안 DOM 에 안 보임(1.1.18 과 같음 = 대조군).
  C. 결속 id 없음(옛 데몬 꼴): watch 0(1.1.18 길).
대역 = tickrec_gate SHIM + chat_gate CHAT_SHIM 위에 덧씌움(새 명령 4개 · org_status 행에 registered_session_id). 포트 = 0(빈 포트 자동) · 헤드리스.
실기(맥 VM · 윈)의 K3 숫자는 이 시험이 아니다 — 통합 뒤 master(P3 v4 §6-3 · T-E5).
"""
from __future__ import annotations

import http.server
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
failures: list[str] = []


def check(ok: bool, m: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + m)
    if not ok:
        failures.append(m)


WATCH_SHIM = r"""
(() => {
  const C = window.__CHAT;
  const W = window.__WATCH = { compat: __COMPAT__, regSid: __REGSID__, gen: 0, watch: 0, unwatch: 0, tail: 0, env: 0 };
  const prev = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    const a = args ?? {};
    if (cmd === 'chat_compat_env') { W.env++; return Promise.resolve(W.compat); }
    if (cmd === 'chat_transcript_watch') { W.watch++; W.lastWatch = a; return Promise.resolve(a.sessionId === C.session ? { status: 'ok', session_id: C.session, size: C.file.length, gen: ++W.gen } : { status: 'unknown', why: 'session_mismatch' }); }
    if (cmd === 'chat_transcript_unwatch') { W.unwatch++; return Promise.resolve({ status: 'ok', was: true }); }
    if (cmd === 'chat_transcript_tail') { W.tail++; const f = a.afterOffset; return Promise.resolve({ status: 'ok', session_id: C.session, gen: W.gen, from_offset: f, to_offset: C.file.length, next_offset: C.file.length, size: C.file.length, records: C.file.slice(f), reset: false }); }
    const r = prev(cmd, args);
    if (cmd === 'org_status' && (a.socket ?? null) === null && W.regSid !== null)
      return r.then((v) => ({ ...v, surfaces: (v.surfaces || []).map((s) => (s.role === 'master' ? { ...s, registered_session_id: W.regSid === 'SAME' ? C.session : W.regSid } : s)) }));
    return r;
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

        def page(compat: str, reg: str):
            ctx = br.new_context(viewport={"width": 1400, "height": 900})
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.add_init_script(WATCH_SHIM.replace("__COMPAT__", compat).replace("__REGSID__", reg))
            pg.goto(url)
            pg.clock.run_for(9_000)
            pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}); }}")
            pg.clock.run_for(15_000)
            pg.click("#view-switch button[data-view=chat]")
            pg.clock.run_for(7_000)  # 3초 조회 두 바퀴 — 결속·시작점·watch
            return ctx, pg, errs

        # (TICKET=cysr-1119-integ1 · S3×S6 풀이) 마스터 답 글 칸 = S6 V1(MD_RENDER) 이면 .cv-md · 끄면 .cv-text — chat_gate.py 의 S6 고침과 같은 꼴
        texts = lambda pg: pg.evaluate("() => [...document.querySelectorAll('.cv-master .cv-text, .cv-master .cv-md')].map((e) => e.textContent)")  # noqa: E731
        W = lambda pg: pg.evaluate("() => ({ ...window.__WATCH, transcript: window.__CHAT.calls.filter((c) => c[1] === 'chat_transcript').length })")  # noqa: E731
        append = "() => { const C = window.__CHAT; C.file.push({ uuid: 'k3b-1', parent: null, role: 'assistant', text: '계기 없는 덧붙임 1', ts: new Date(Date.now()).toISOString() }); }"

        print("== A 되돌리기 끔 — watch · 사건 → 0.3초 안 화면 · tail = RPC 0")
        ctx, pg, errs = page("false", "'SAME'")
        w0 = W(pg)
        check(w0["watch"] == 1 and w0["env"] == 1 and w0["lastWatch"] == {"socket": None, "surfaceId": 1, "sessionId": "sess-0001-aaaa-bbbb"}, f"watch 1 · 값 원천 1회 · 결속 id 로 {w0}")
        pg.evaluate(append)
        n = pg.evaluate("() => window.__emit('chat-transcript-changed', { surface_id: 1, session_id: 'sess-0001-aaaa-bbbb', gen: window.__WATCH.gen, size: window.__CHAT.file.length, reset: false })")
        check(n == 1, f"사건 구독 1(대화 화면이 켜진 동안) ({n})")
        pg.clock.run_for(300)
        w1 = W(pg)
        check("계기 없는 덧붙임 1" in texts(pg), f"계기 없는 덧붙임이 0.3초 안 화면에 {texts(pg)}")
        check(w1["tail"] >= 1 and w1["transcript"] == w0["transcript"], f"그 읽기 = tail · 기존 chat_transcript 수 그대로({w0['transcript']}→{w1['transcript']} · tail {w1['tail']})")
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(200)
        w2 = W(pg)
        check(w2["unwatch"] == 1, f"작업 화면으로 = unwatch 1 ({w2['unwatch']})")
        n2 = pg.evaluate("() => window.__emit('chat-transcript-changed', { surface_id: 1, session_id: 'sess-0001-aaaa-bbbb', gen: window.__WATCH.gen, size: 99, reset: false })")
        pg.clock.run_for(300)
        check(W(pg)["tail"] == w2["tail"], f"내린 뒤 사건 = 읽기 0 (구독 {n2})")
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_500)
        check(W(pg)["watch"] == 2, f"다시 켜면 다시 watch ({W(pg)['watch']})")
        check(not errs, f"페이지 오류 0 {errs}")
        ctx.close()

        print("== B 되돌리기 켬(CYS_CHAT_COMPAT_1118=1 꼴) — watch·tail 0 · 같은 덧붙임 = 10초 동안 안 보임(1.1.18 대조)")
        ctx, pg, errs = page("true", "'SAME'")
        pg.evaluate(append)
        pg.evaluate("() => window.__emit('chat-transcript-changed', { surface_id: 1, session_id: 'sess-0001-aaaa-bbbb', gen: 1, size: window.__CHAT.file.length, reset: false })")
        pg.clock.run_for(10_000)
        w = W(pg)
        check(w["watch"] == 0 and w["tail"] == 0 and w["env"] == 1, f"watch 0 · tail 0 · 값 원천 1회 {w}")
        check("계기 없는 덧붙임 1" not in texts(pg), f"1.1.18 꼴 = 계기 없는 덧붙임 안 보임 {texts(pg)}")
        check(not errs, f"페이지 오류 0 {errs}")
        ctx.close()

        print("== C 결속 id 없음(옛 데몬 꼴) — watch 0")
        ctx, pg, errs = page("false", "null")
        check(W(pg)["watch"] == 0, f"watch 0 {W(pg)}")
        check(not errs, f"페이지 오류 0 {errs}")
        ctx.close()
        br.close()
    httpd.shutdown()
    print("RESULT:", "PASS" if not failures else f"FAIL {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
