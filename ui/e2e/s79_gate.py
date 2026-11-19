#!/usr/bin/env python3
"""조각 7 결과 받기 · 조각 9 작업 화면 띠 · S4-7(F7·F10) 게이트 — TICKET=cysr-1116-s79-1119 · P2-DESIGN §11 조각 7·9 (수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(tickrec_gate SHIM + chat_gate CHAT_SHIM + confirm_gate CONFIRM_SHIM 위에 파일 대역 list_dir·open_path·reveal_path) + 가짜 시계.
클릭 = playwright 실제 마우스(신뢰) · 「대본 클릭」 = element.click()(isTrusted=false).

A 대화 화면을 안 켬: 작업 화면 띠 숨김 · 대화 화면 조회 0 · list_dir·open_path 0
B 답 속 경로: 실재 1(카드 · 새 결과) · 없는 경로·울타리 안 경로 = 카드 0 · 대화 안 카드 = 그 답 뒤 · 열기(진짜 클릭) = open_path 1 + 새 결과 풀림 · 대본 클릭 = 0
  · 폴더 보기 = reveal_path 1 · 고쳐 달라고 하기 = 입력칸 앞글 + 쓰던 글 그대로 · 파일 사라짐 → 열기 = 호출 0 + 「찾을 수 없어요」 + 「마스터에게 물어보기」
C 스킬 산출 폴더: skill.run_finished(본부 slug) → 카드 · 부서 slug = 0
D 실행형 파일: open_path 거절(executable_confirm) → force 재호출 0 + 폴더 보기 안내
E 조각 9: 초안 → 작업 화면 띠 「대화 화면에 쓰다 만 말」 → 누르면 대화 화면 · 초안 그대로 / 마스터 물음 → 작업 화면 띠 「마스터 창에서 답하기」 → 마스터 좌석 포커스
  · 작업 화면에서 살피는 중엔 붙잡은 말 쓰기 0 → 대화 화면으로 돌아오면 1
F F7: 「이 물음은 끝났어요」(진짜 클릭) → 띠 내림 · 보낸 말 0 · 대본 클릭 = 0
G F10: 보던 물음이 해결돼 다음 물음이 저절로 옴 → 2초 안 「끝났어요」 = 처리 0 + 안내 → 2초 뒤 = 처리
H F10 거절: 마스터 멈춤 · 보던 도우미 요청이 처리돼 다른 요청이 저절로 옴 → 곧바로 거절 = confirm_reply 0 + 안내 → 2초 뒤 = 그 요청 1건
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/s79_gate.py
"""
import http.server
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tickrec_gate import BASE, CWD, SHIM, seat  # noqa: E402
from chat_gate import CHAT_SHIM, T0  # noqa: E402
from confirm_gate import CONFIRM_SHIM, item_js  # noqa: E402

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"
HOME = "/sandbox/home"  # tickrec_gate SHIM 의 home_dir_path

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


FS_SHIM = r"""
(() => {
  const C = window.__CHAT;
  C.fs = {}; C.opens = []; C.reveals = []; C.lists = 0; C.openErr = null;
  const prev = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    const a = args ?? {};
    if (cmd === 'list_dir') { C.lists++; const l = C.fs[a.path]; return l ? Promise.resolve(l.map((x) => ({ ...x }))) : Promise.reject('No such file or directory (os error 2)'); }
    if (cmd === 'open_path' || cmd === 'reveal_path') { C.legacyOpen = (C.legacyOpen ?? 0) + 1; return Promise.resolve(null); } // 화면은 우리 result_open 만 불러야 함
    if (cmd === 'result_open') { // 우리 Tauri 명령(정규 경로 가둠 = cargo 시험 몫) — 열기·폴더 보기로 나눠 적음
      if (a.reveal) { C.reveals.push({ path: a.path }); return Promise.resolve(null); }
      C.opens.push({ path: a.path }); return C.openErr ? Promise.reject(C.openErr) : Promise.resolve(null); }
    return prev(cmd, args);
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

        def page(chat: bool = True):
            ctx = br.new_context(viewport={"width": 1400, "height": 900})
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.add_init_script(CONFIRM_SHIM)
            pg.add_init_script(FS_SHIM)
            pg.goto(url)
            pg.clock.run_for(9_000)
            pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}, {seat(BASE, 2, 'worker')}); }}")
            pg.clock.run_for(6_000)
            if chat:
                pg.click("#view-switch button[data-view=chat]")
                pg.clock.run_for(3_200)
            return ctx, pg, errs

        def push_reply(pg, uuid: str, text: str) -> None:
            pg.evaluate(f"""() => {{ const C = window.__CHAT; C.file.push({{ uuid: '{uuid}', parent: null, role: 'assistant', text: {text!r}, ts: new Date(Date.now()).toISOString() }}); C.master.idle_secs = 0; }}""")
            pg.clock.run_for(3_100)
            pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
            pg.clock.run_for(3_100)

        rail = lambda pg: pg.evaluate("""() => { const r = document.querySelector('.cv-results'); return { head: r?.querySelector('.cvr-head')?.textContent ?? null,
            cards: [...(r?.querySelectorAll('.cvr-card') ?? [])].map((c) => ({ id: c.dataset.result, src: c.dataset.source, fresh: !!c.querySelector('.cvr-new'), missing: c.dataset.missing === '1', name: c.querySelector('.cvr-name')?.textContent })),
            inlog: [...document.querySelectorAll('.cv-log .cvr-inlog')].map((c) => ({ id: c.dataset.result, after: c.closest('li')?.previousElementSibling?.dataset.uuid ?? null })),
            notice: r?.querySelector('.cvr-notice')?.textContent ?? '' }; }""")  # noqa: E731
        wband = lambda pg: pg.evaluate("""() => { const b = document.querySelector('.wv-band'); return { hidden: !b || b.hidden, kind: b?.dataset.kind ?? null, text: b?.querySelector('.wvb-text')?.textContent ?? '', act: b?.querySelector('.wvb-act')?.textContent ?? '' }; }""")  # noqa: E731
        band = lambda pg: pg.evaluate("""() => { const b = document.querySelector('.cv-band'); return { hidden: !b || b.hidden, head: b?.querySelector('.cvb-head')?.textContent ?? '', text: b?.querySelector('.cvb-text')?.textContent ?? '', notice: b?.querySelector('.cvb-notice')?.textContent ?? '', swapped: !!b?.querySelector('[data-swapped]') }; }""")  # noqa: E731
        p_html = f"{HOME}/교회/행사안내.html"

        print("== A 대화 화면을 안 켬 = 작업 화면 띠 0 · 조회 0")
        ctx, pg, errs = page(chat=False)
        pg.clock.run_for(9_000)
        st = pg.evaluate("() => ({ calls: window.__CHAT.calls.length, lists: window.__CHAT.lists, opens: window.__CHAT.opens.length })")
        check(wband(pg)["hidden"] and st == {"calls": 0, "lists": 0, "opens": 0}, f"작업 화면만 = 띠 숨김 · 대화 화면 조회 0 · list_dir·open_path 0 {st} {wband(pg)}")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()

        print("== B 답 속 경로 → 결과 카드")
        ctx, pg, errs = page()
        pg.evaluate(f"() => {{ window.__CHAT.fs['{HOME}/교회'] = [{{ name: '행사안내.html', is_dir: false }}]; }}")
        push_reply(pg, "m1", f"다 만들었어요: {p_html}.\n메모는 {HOME}/교회/메모.txt 에 둘 수도 있어요.\n```\nopen {HOME}/교회/명령예시.html\n```")
        pg.clock.run_for(3_100)
        r = rail(pg)
        check(r["head"] == "결과 1 · 새 결과 1" and [c["id"] for c in r["cards"]] == [p_html] and r["cards"][0]["fresh"], f"실재 1 = 카드 1 · 새 결과 · 없는 경로·울타리 안 = 0 {r}")
        check(r["inlog"] == [{"id": p_html, "after": "m1"}], f"대화 안 카드 = 그 경로를 말한 답 바로 뒤 {r['inlog']}")
        pg.evaluate("() => document.querySelector('.cv-results .cvr-open').click()")
        pg.clock.run_for(100)
        check(pg.evaluate("() => window.__CHAT.opens.length") == 0, "★대본 클릭(isTrusted=false) 열기 → open_path 0")
        pg.click(".cv-results .cvr-open")
        pg.clock.run_for(200)
        r = rail(pg)
        check(pg.evaluate("() => window.__CHAT.opens") == [{"path": p_html}] and r["head"] == "결과 1" and not r["cards"][0]["fresh"], f"열기(진짜 클릭) → open_path 1(force 없음) · 새 결과 풀림 {r}")
        pg.click(".cv-results .cvr-reveal")
        pg.clock.run_for(200)
        check(pg.evaluate("() => window.__CHAT.reveals") == [{"path": p_html}], "폴더 보기 → reveal_path 1")
        pg.fill(".cv-input", "날짜 글씨를 키워 줘")
        pg.click(".cv-results .cvr-revise")
        pg.clock.run_for(50)
        st = pg.evaluate("() => ({ v: document.querySelector('.cv-input').value, focus: document.activeElement?.className })")
        check(st["v"] == f"이 결과를 고쳐 주세요 — {p_html}\n고칠 점: 날짜 글씨를 키워 줘" and st["focus"] == "cv-input", f"고쳐 달라고 하기 = 앞글 + 쓰던 글 그대로 · 입력칸 포커스 {st}")
        check(pg.evaluate("() => window.__CHAT.writes.length") == 0, "고쳐 달라고 하기만으로 보낸 말 0(사람이 보냄)")
        pg.evaluate(f"() => {{ window.__CHAT.fs['{HOME}/교회'] = []; }}")
        pg.click(".cv-results .cvr-open")
        pg.clock.run_for(200)
        r = rail(pg)
        check(pg.evaluate("() => window.__CHAT.opens.length") == 1 and "찾을 수 없어요" in r["notice"] and r["cards"][0]["missing"], f"★파일 사라짐 → 열기 호출 0 · 「찾을 수 없어요」 · 없음 카드 {r}")
        pg.fill(".cv-input", "")
        pg.click(".cv-results .cvr-ask")
        pg.clock.run_for(50)
        v = pg.evaluate("() => document.querySelector('.cv-input').value")
        check(v.startswith("이 결과 파일을 찾을 수 없어요") and p_html in v, f"마스터에게 물어보기 = 입력칸 준비 {v!r}")
        saved = pg.evaluate("() => localStorage.getItem('cys-chat-results')")
        check(saved is not None and "다 만들었어요" not in saved and "메모.txt" not in saved and p_html in saved, f"저장 = 경로만(말 원문 0자 · 설명 경로 0) {saved}")

        print("== C 스킬 산출 폴더")
        pg.evaluate(f"() => {{ window.__CHAT.fs['{HOME}/cys-runs'] = [{{ name: 'r1', is_dir: true }}]; window.__emit('daemon-event', {{ name: 'skill.run_finished', socket_slug: 'dept-x', payload: {{ run_id: 'r0', status: 'done', artifact_dir: '{HOME}/cys-runs/r0' }} }}); }}")
        pg.clock.run_for(3_100)
        check(not any(c["src"] == "skill" for c in rail(pg)["cards"]), "부서 slug 사건 → 카드 0")
        pg.evaluate(f"() => window.__emit('daemon-event', {{ name: 'skill.run_finished', socket_slug: 'base', payload: {{ run_id: 'r1', status: 'done', artifact_dir: '{HOME}/cys-runs/r1' }} }})")
        pg.clock.run_for(3_100)
        r = rail(pg)
        check(r["cards"][0]["id"] == f"{HOME}/cys-runs/r1" and r["cards"][0]["src"] == "skill" and r["cards"][0]["fresh"], f"본부 skill.run_finished → 폴더 카드(맨 위 · 새 결과) {r['cards'][:1]}")

        print("== D 실행형 파일 = force 재호출 0")
        pg.evaluate(f"() => {{ window.__CHAT.fs['{HOME}/x'] = [{{ name: 'run.sh', is_dir: false }}]; window.__CHAT.openErr = 'executable_confirm'; }}")
        push_reply(pg, "m2", f"실행 파일은 {HOME}/x/run.sh 예요")
        pg.clock.run_for(3_100)
        n0 = pg.evaluate("() => window.__CHAT.opens.length")
        pg.click(f".cv-results .cvr-card[data-result='{HOME}/x/run.sh'] .cvr-open")
        pg.clock.run_for(200)
        o = pg.evaluate("() => window.__CHAT.opens")
        check(len(o) == n0 + 1 and "force" not in o[-1] and "폴더 보기" in rail(pg)["notice"], f"★실행형 → open_path 1회(force 없음) · 다시 묻지 않음 · 폴더 보기 안내 {o[-1:]} {rail(pg)['notice']}")
        print("== D2 마스터 글 속 앱 꾸러미(.app = 폴더라 Tauri 실행형 검사 밖) → 열기 호출 0")
        pg.evaluate(f"() => {{ window.__CHAT.openErr = null; window.__CHAT.fs['{HOME}/Downloads'] = [{{ name: 'Evil.app', is_dir: true }}]; }}")
        push_reply(pg, "m3", f"받은 앱은 {HOME}/Downloads/Evil.app 이에요")
        pg.clock.run_for(3_100)
        n0 = pg.evaluate("() => window.__CHAT.opens.length")
        pg.click(f".cv-results .cvr-card[data-result='{HOME}/Downloads/Evil.app'] .cvr-open")
        pg.clock.run_for(200)
        check(pg.evaluate("() => window.__CHAT.opens.length") == n0 and "열지 않았어요" in rail(pg)["notice"], f"★.app 열기 → open_path 0 · 안내 {rail(pg)['notice']}")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        check(pg.evaluate("() => window.__CHAT.legacyOpen ?? 0") == 0, "원작자 open_path·reveal_path 직접 호출 0(화면은 result_open 만)")
        ctx.close()

        print("== E 조각 9 작업 화면 띠")
        ctx, pg, errs = page()
        pg.fill(".cv-input", "행사 순서에 어린이 합창도 넣어 줘")
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(3_200)
        b = wband(pg)
        check(not b["hidden"] and b["kind"] == "draft" and "쓰다 만 말" in b["text"] and b["act"] == "대화 화면에서 이어 쓰기", f"초안 → 작업 화면 띠(마스터 창엔 안 넣음) {b}")
        pg.click(".wv-band .wvb-act")
        pg.clock.run_for(300)
        st = pg.evaluate("() => ({ host: document.getElementById('view-host').hidden, v: document.querySelector('.cv-input')?.value, band: document.querySelector('.wv-band') === null })")
        check(st == {"host": False, "v": "행사 순서에 어린이 합창도 넣어 줘", "band": True}, f"누르면 대화 화면 · 초안 그대로 · 작업 화면 띠 떼어짐 {st}")
        pg.fill(".cv-input", "")
        pg.evaluate("() => { const i = document.querySelector('.cv-input'); i.dispatchEvent(new Event('input')); }")
        push_reply(pg, "q1", "⟪확인 요청: 주보를 금요일에 인쇄할까요?⟫")
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(3_200)
        b = wband(pg)
        check(b["kind"] == "confirm" and "마스터가 물어요: 주보를 금요일에 인쇄할까요?" in b["text"] and b["act"] == "마스터 창에서 답하기", f"마스터 물음 → 작업 화면 확인 띠(초안보다 먼저) {b}")
        pg.click(".wv-band .wvb-act")
        pg.clock.run_for(300)
        foc = pg.evaluate("() => ({ focused: [...document.querySelectorAll('.pane.focused')].map((e) => e.dataset.sid), host: document.getElementById('view-host').hidden })")
        check(foc["focused"] == ["1"] and foc["host"] is True, f"★「마스터 창에서 답하기」 → 마스터 좌석 포커스 · 작업 화면 그대로(대화 화면으로 안 데려감) {foc}")
        print("== E1 작업 화면에 있는 동안 새 물음 → 띠에 옴(대화 화면 내림이 살핌을 끄지 않음)")
        pg.evaluate("() => { const C = window.__CHAT; C.file.push({ uuid: 'q9', parent: null, role: 'assistant', text: '⟪확인 해결: 주보를 금요일에 인쇄할까요?⟫\\n⟪확인 요청: 작업 화면에서 새로 온 물음⟫', ts: new Date(Date.now()).toISOString() }); C.master.idle_secs = 0; }")
        pg.clock.run_for(3_100)
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
        pg.clock.run_for(6_200)
        b = wband(pg)
        check(b["kind"] == "confirm" and "작업 화면에서 새로 온 물음" in b["text"], f"★작업 화면에서 받은 새 물음 = 띠 {b}")
        print("== E2 작업 화면에서 살피는 중엔 붙잡은 말 쓰기 0")
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_200)
        pg.evaluate("() => { window.__CHAT.approvals = [1]; }")
        pg.clock.run_for(3_200)
        pg.fill(".cv-input", "작업 화면 가기 전 말")
        pg.press(".cv-input", "Enter")
        pg.clock.run_for(500)
        w0 = pg.evaluate("() => window.__CHAT.writes.length")
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(500)
        pg.evaluate("() => { window.__CHAT.approvals = []; }")
        c0 = pg.evaluate("() => window.__CHAT.calls.length")
        pg.clock.run_for(30_000)
        st = pg.evaluate("() => ({ w: window.__CHAT.writes.length, c: window.__CHAT.calls.length })")
        check(w0 == 0 and st["w"] == 0 and st["c"] > c0, f"★작업 화면 = 띠 자료는 받음(조회 {st['c'] - c0}) · 붙잡은 말 쓰기 0 ({w0}→{st['w']})")
        pg.click("#view-switch button[data-view=chat]")
        pg.clock.run_for(3_500)
        w = pg.evaluate("() => window.__CHAT.writes.map((x) => x.args.text)")
        check(w == ["작업 화면 가기 전 말"], f"대화 화면으로 돌아오면 1건 {w}")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()

        print("== F F7 사람이 물음을 띠에서 내림")
        ctx, pg, errs = page()
        push_reply(pg, "q1", "⟪확인 요청: 이 물음은 마스터가 안 닫아요⟫")
        check(band(pg)["head"] == "확인이 필요해요 1", f"물음 1 {band(pg)}")
        pg.evaluate("() => document.querySelector('.cvb-dismiss').click()")
        pg.clock.run_for(50)
        check(band(pg)["head"] == "확인이 필요해요 1", "대본 클릭 → 내림 0")
        pg.click(".cvb-dismiss")
        pg.clock.run_for(50)
        b = band(pg)
        check(b["head"] == "" and "마스터에게는 아무것도 보내지 않았어요" in b["notice"] and pg.evaluate("() => window.__CHAT.writes.length") == 0, f"★진짜 클릭 → 띠 내림 · 보낸 말 0 · 안내 {b}")
        log = pg.evaluate("() => localStorage.getItem('cys-chat-decisions')")
        check(log is not None and "dismiss" in log and "안 닫아요" not in log, f"기록(번호·dismiss · 물음 글 0자) {log}")

        print("== G F10 보던 물음이 해결돼 다음 물음이 저절로 옴")
        push_reply(pg, "q2", "⟪확인 요청: 첫째 물음이에요 보던 것⟫\n⟪확인 요청: 둘째 물음이에요 다른 것⟫")
        check("첫째 물음" in band(pg)["text"], f"보던 항목 = 첫째 {band(pg)['text']}")
        push_reply(pg, "q3", "⟪확인 해결: 첫째 물음이에요 보던 것⟫")
        b = band(pg)
        check("둘째 물음" in b["text"] and b["swapped"], f"해결 → 둘째가 저절로 옴 · 표시 {b}")
        pg.click(".cvb-dismiss")
        pg.clock.run_for(50)
        b = band(pg)
        check("둘째 물음" in b["text"] and "다른 요청이 그 자리에 왔어요" in b["notice"], f"★온 지 2초 안 누름 → 처리 0 + 안내 {b}")
        # 그리기 뒤 2초 넘게 지나면 사람이 본 것으로 — 같은 진짜 클릭이 처리된다(가짜 시계)
        pg.clock.run_for(2_100)
        pg.click(".cvb-dismiss")
        pg.clock.run_for(50)
        check(band(pg)["head"] == "", f"2초 뒤 진짜 클릭 → 내림 {band(pg)}")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()

        print("== G2 F10 「다음」 왕복 — 저절로 온 항목에서 다음으로 갔다 2초 안 되돌아와도 보호 유지(codex 1R major)")
        ctx, pg, errs = page()
        push_reply(pg, "q4", "⟪확인 요청: 가 물음 보던 것⟫\n⟪확인 요청: 나 물음 저절로 옴⟫\n⟪확인 요청: 다 물음 셋째⟫")
        pg.clock.run_for(2_100)
        check("가 물음" in band(pg)["text"], f"보던 것 = 가 {band(pg)['text']}")
        pg.evaluate("() => { const C = window.__CHAT; C.file.push({ uuid: 'q5', parent: null, role: 'assistant', text: '⟪확인 해결: 가 물음 보던 것⟫', ts: new Date(Date.now()).toISOString() }); C.master.idle_secs = 0; }")
        pg.clock.run_for(3_100)
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")  # 쉬게 된 틱에 세션 읽기 → 그 틱에 나 가 옴
        for _ in range(80):
            pg.clock.run_for(100)
            if "나 물음" in band(pg)["text"]:
                break
        check("나 물음" in band(pg)["text"], f"가 해결 → 나 가 저절로 옴 {band(pg)['text']}")
        pg.click(".cvb-next")
        pg.clock.run_for(50)
        pg.click(".cvb-next")
        pg.clock.run_for(50)
        check("나 물음" in band(pg)["text"], "다음 → 다 → 다음 → 나(2초 안)")
        pg.click(".cvb-dismiss")
        pg.clock.run_for(50)
        check("나 물음" in band(pg)["text"] and "다른 요청이 그 자리에 왔어요" in band(pg)["notice"], f"★되돌아온 나 에 곧바로 누름 → 처리 0 + 안내 {band(pg)}")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        check(pg.evaluate("() => window.__CHAT.legacyOpen ?? 0") == 0, "원작자 open_path·reveal_path 직접 호출 0(화면은 result_open 만)")
        ctx.close()

        print("== H F10 거절 — 보던 도우미 요청이 처리돼 다른 요청이 저절로 옴 → 곧바로 거절 = 처리 0")
        ctx, pg, errs = page()
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 120; window.__emit('daemon-event', { name: 'master.deadman', category: 'alert', surface_id: 1, socket_slug: 'base', payload: { role: 'master', axis: 'agent_dead' } }); }")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('rA', 2, 'ls a', '1763373000', fp=None)}, {item_js('rB', 3, 'rm -rf b', '1763373001', fp=None)}]; }}")
        pg.clock.run_for(3_100)
        check(pg.evaluate("() => !!document.querySelector('.cvb-deny')") and "1 / 2" in pg.evaluate("() => document.querySelector('.cvb-pos')?.textContent ?? ''"), "멈춤 · 요청 2 · 보던 것 = 첫째(거절 단추 있음)")
        pg.evaluate("() => { window.__CHAT.feedItems = window.__CHAT.feedItems.filter((x) => x.request_id !== 'rA'); }")
        for _ in range(40):  # 그리기가 바뀌는 바로 그 틱까지(100ms 씩)
            pg.clock.run_for(100)
            if pg.evaluate("() => !!document.querySelector('.cv-band [data-swapped]')"):
                break
        check(pg.evaluate("() => !!document.querySelector('.cv-band [data-swapped]')"), "rA 처리됨 → rB 가 저절로 옴(표시)")
        pg.click(".cvb-deny")
        pg.clock.run_for(100)
        rp = pg.evaluate("() => window.__CHAT.replies.map((r) => r.args)")
        check(rp == [] and "다른 요청이 그 자리에 왔어요" in band(pg)["notice"], f"★저절로 온 rB 에 곧바로 거절 → confirm_reply 0 + 안내 {rp} · {band(pg)['notice']}")
        pg.clock.run_for(2_100)
        pg.click(".cvb-deny")
        pg.clock.run_for(200)
        rp = pg.evaluate("() => window.__CHAT.replies.map((r) => r.args)")
        check(rp == [{"requestId": "rB", "decision": "deny", "screenFingerprint": None}], f"2초 뒤(사람이 봄) 거절 → rB 1건 {rp}")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()
    httpd.shutdown()
    print("\nRESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
