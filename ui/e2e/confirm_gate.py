#!/usr/bin/env python3
"""확인 대기 조각 4 게이트 — TICKET=cysr-ui-slice4-1118 · P2-DESIGN §11 조각 4 (수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(tickrec_gate SHIM + chat_gate CHAT_SHIM 위에 feed 항목·confirm_reply 대역을 덧씌움) + 가짜 시계.
클릭은 playwright 실제 마우스(page.click = 신뢰 이벤트) · 「대본 클릭」 = element.click()/dispatchEvent(isTrusted=false).
판정 단위: 「허락 집행 = confirm_reply 호출」(우리 Tauri 명령 = 데몬 feed.reply · 결과 actuated 그대로). 원작자 feed_reply 호출 = 늘 0.

A 표식 없음: 마스터 답에 표식 없음 → 띠 숨김 · 머리 「확인할 것 없음」(꾸미지 않음)
B 마스터 물음: ⟪확인 요청⟫ → 「마스터 물음 1」(1.1.21 L ㉢ 갈래별 머리) · 대화에서 답하기(진짜 클릭) → 입력칸 포커스 · 입력칸 글 불변 · 보낸 말 = 원문 그대로 · 해결 표식 → 띠 숨김
C 도우미 허락 평소: 「마스터가 확인하는 중」 · 허락·거절 단추 0
D 마스터 멈춤(master.deadman 주입): 단추 보임 · 펼치기 전 허락(진짜 클릭) → 호출 0 + 안내 · 대본 클릭 → 호출 0 · 펼친 뒤 진짜 클릭 → 호출 1(번호·allow)
E 이미 처리된 요청(그리기 뒤 목록에서 빠짐) → 진짜 클릭 → 호출 0 + 「이미 처리됐거나 바뀐 요청이에요」
F 펼친 뒤 판 바뀜(같은 번호 · 다른 명령 · 시각 주입: 그리기와 클릭 사이) → 호출 0 + 안내 · 다음 그리기 = 접힌 채 새 명령
G 거절 · 마스터 창 승인 = 「작업 화면에서 보기」(진짜 클릭 → 작업 화면)
D0·F0(독립 검증 1회 고침) 사건은 앱 꼴(본부 slug = 대역 default_socket_slug 'base') · 부서 slug 사건 = 버림 · daemon_issued 아닌 approval = 멈춤이어도 직접 단추 0
D1(codex 1R blocking) 지금 데몬(지문 표지 screen_fingerprint 없음) = 멈춤이어도 허락 단추 0 · 거절 + 「작업 화면에서 그 창 보기」 + 안내 · D~G 는 지문 표지가 있는 판(앞날 데몬)
F2(codex 1R major 2) 펼친 뒤 좌석만 바뀜 → 다음 그리기 = 접힌 채 · 허락(진짜 클릭) = 호출 0 · G2(major 5) 데몬이 기록만 해소(actuated null) → 「작업 화면에서 확인」
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/confirm_gate.py
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

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


CONFIRM_SHIM = r"""
(() => {
  const C = window.__CHAT;
  C.feedItems = null; C.replies = []; C.replyErr = null; C.replyResult = null; C.legacy = 0;
  const prev = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    const a = args ?? {};
    if (cmd === 'feed_list' && C.feedItems !== null) { C.calls.push([Date.now(), cmd]); return Promise.resolve({ items: C.feedItems.map((x) => ({ ...x })) }); }
    if (cmd === 'feed_reply') { C.legacy++; return Promise.resolve(null); }
    if (cmd === 'confirm_reply') {
      C.replies.push({ t: Date.now(), args: a });
      if (C.replyErr) return Promise.reject(C.replyErr);
      if (C.feedItems) C.feedItems = C.feedItems.filter((x) => x.request_id !== a.requestId);
      return Promise.resolve(C.replyResult ?? { request_id: a.requestId, decision: a.decision, actuated: a.decision === 'allow' ? 'return' : 'esc' });
    }
    return prev(cmd, args);
  };
})();
"""

BODY = "Do you want to proceed?\n— 명령 원문:\n{cmd}\n— 읽기 전용 판정(기계 추정 · 근거 아님): 쓰기·삭제 가능"


def item_js(rid: str, sid: int, cmd: str, created: str = "Date.now() / 1000 - 10", daemon: bool = True, fp: "str | None" = "fp-1") -> str:
    """fp = 데몬 지문 표지(screen_fingerprint) · None = 지금 데몬(칸 없음)."""
    body = BODY.format(cmd=cmd).replace("\\", "\\\\").replace("`", "\\`")
    issued = "true" if daemon else "false"
    fpf = f", screen_fingerprint: '{fp}'" if fp is not None else ""
    return f"{{ request_id: '{rid}', kind: 'approval', status: 'pending', surface_id: {sid}, created_at: {created}, daemon_issued: {issued}, title: 't', body: `{body}`{fpf} }}"


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

        def page():
            ctx = br.new_context(viewport={"width": 1400, "height": 900})
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.add_init_script(CONFIRM_SHIM)
            pg.goto(url)
            pg.clock.run_for(9_000)
            pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}, {seat(BASE, 2, 'worker')}); }}")
            pg.clock.run_for(6_000)
            pg.click("#view-switch button[data-view=chat]")
            pg.clock.run_for(3_200)
            return ctx, pg, errs

        replies = lambda pg: pg.evaluate("() => window.__CHAT.replies.map((r) => r.args)")  # noqa: E731
        band = lambda pg: pg.evaluate("""() => { const b = document.querySelector('.cv-band'); return { hidden: !b || b.hidden, head: b?.querySelector('.cvb-head')?.textContent ?? '',
            text: b?.querySelector('.cvb-text')?.textContent ?? '', notice: b?.querySelector('.cvb-notice')?.textContent ?? '', allow: !!b?.querySelector('.cvb-allow'),
            deny: !!b?.querySelector('.cvb-deny'), what: !!b?.querySelector('.cvb-what'), work: b?.querySelector('.cvb-work')?.textContent ?? null,
            dim: !!b?.querySelector('.cvb-allow.cvb-dim'), cmd: b?.querySelector('.cvb-cmd')?.textContent ?? null, min: document.querySelector('[data-min=confirms]')?.textContent }; }""")  # noqa: E731

        def push_reply(pg, uuid: str, text: str) -> None:
            """마스터가 답을 내고(일함) 쉼 → 쉬게 된 틱에 세션 읽기."""
            pg.evaluate(f"""() => {{ const C = window.__CHAT; C.file.push({{ uuid: '{uuid}', parent: null, role: 'assistant', text: {text!r}, ts: new Date(Date.now()).toISOString() }}); C.master.idle_secs = 0; }}""")
            pg.clock.run_for(3_100)
            pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
            pg.clock.run_for(3_100)

        print("== A 표식 없음 = 띠 0")
        ctx, pg, errs = page()
        push_reply(pg, "a0", "📌 결정 필요: 이건 표식이 아니에요")
        b = band(pg)
        check(b["hidden"] and b["min"] == "확인할 것 없음", f"표식 없는 마스터 답 → 띠 숨김 · 머리 「확인할 것 없음」 {b}")

        print("== B 마스터 물음 · 대화에서 답하기 · 원문 그대로 · 해결")
        push_reply(pg, "a1", "정리했어요.\n⟪확인 요청: 금요일 배포를 다음 주로 미뤄도 될까요?⟫")
        b = band(pg)
        check(not b["hidden"] and b["head"] == "마스터 물음 1" and "금요일 배포" in b["text"], f"물음 → 띠 1 {b}")
        check(b["min"] == "마스터 물음 1", f"최소 계약 칸 = 띠와 같은 값 {b['min']}")
        pg.click(".cvb-answer")
        pg.clock.run_for(50)
        st = pg.evaluate("""() => ({ focus: document.activeElement?.className, value: document.querySelector('.cv-input').value,
            hint: document.querySelector('.cv-answering')?.hidden === false ? document.querySelector('.cva-text').textContent : null,
            asked: !!document.querySelector('.cv-master.cv-asked[data-uuid=a1]') })""")
        check(st["focus"] == "cv-input" and st["value"] == "" and st["hint"] and st["asked"], f"그 물음 자리 표시 · 입력칸 포커스 · 입력칸 글 불변(빈칸) · 답하는 물음 줄 {st}")
        pg.fill(".cv-input", "네 미뤄 주세요")
        pg.press(".cv-input", "Enter")
        pg.clock.run_for(50)
        w = pg.evaluate("() => window.__CHAT.writes.map((x) => x.args.text)")
        check(w == ["네 미뤄 주세요"], f"★보낸 말 = 원문 그대로(물음 글·꼬리표 0) {w}")
        check(band(pg)["head"] == "마스터 물음 1", "사람 답만으로는 띠가 닫히지 않음(마스터 해결 표식만 · FR-C3)")
        push_reply(pg, "a2", "알겠습니다.\n⟪확인 해결: 금요일 배포를 다음 주로 미뤄도 될까요?⟫")
        b = band(pg)
        check(b["hidden"], f"해결 표식 → 띠 숨김 {b}")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()

        print("== C 도우미 허락 평소 = 마스터가 확인하는 중")
        ctx, pg, errs = page()
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('r1', 2, 'rm -rf build', fp=None)}]; }}")
        pg.clock.run_for(3_100)
        b = band(pg)
        check(b["head"] == "마스터가 확인하는 중 1" and "마스터가 확인하는 중" in b["text"] and not b["allow"] and not b["deny"], f"「마스터가 확인하는 중」 · 허락·거절 단추 0 {b}")

        print("== D0 앱 꼴 사건(검증 F1) — 부서 slug 사건 = 버림")
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 120; window.__emit('daemon-event', { name: 'master.deadman', category: 'alert', surface_id: 1, socket_slug: 'dept-xyz', payload: { role: 'master' } }); }")
        pg.clock.run_for(3_100)
        check(not band(pg)["allow"], f"부서 slug 의 deadman → 직접 단추 0 {band(pg)['text']}")
        print("== D1 지금 데몬(지문 표지 없음 · codex 1R blocking) — 멈춤이어도 허락 단추 0")
        pg.evaluate("() => { window.__CHAT.master.idle_secs = 120; window.__emit('daemon-event', { name: 'master.deadman', category: 'alert', surface_id: 1, socket_slug: 'base', payload: { role: 'master', axis: 'agent_dead', reason: 'agent process dead' } }); }")
        pg.clock.run_for(3_100)
        b = band(pg)
        check(not b["allow"] and b["deny"] and not b["what"] and b["work"] == "작업 화면에서 그 창 보기" and "허락은 작업 화면의 그 도우미 창에서 직접 눌러 주세요" in b["text"],
              f"★멈춤 · 지문 표지 없음 → 허락 0 · 거절 + 작업 화면에서 그 창 보기 + 안내 {b}")
        check(replies(pg) == [], "그리기만으로 호출 0")
        print("== D 마스터 멈춤 → 펼침 · 신뢰 클릭(지문 표지가 있는 판 = 앞날 데몬)")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('r1', 2, 'rm -rf build')}]; }}")
        pg.clock.run_for(3_100)
        b = band(pg)
        check(b["allow"] and b["dim"] and "마스터가 멈췄어요" in b["text"] and b["cmd"] is None, f"멈춤 → 허락(흐림)·거절 · 펼치기 전 명령 숨김 {b}")
        pg.click(".cvb-allow", force=True)  # aria-disabled 라 playwright 가 「안 켜짐」으로 봄 — 실제 마우스 클릭은 그대로(대기 검사만 건너뜀)
        pg.clock.run_for(50)
        b = band(pg)
        check(replies(pg) == [] and "무엇을 보기" in b["notice"], f"★펼치기 전 허락(진짜 클릭) → 호출 0 + 흐린 허락 안내 ({b['notice']})")
        pg.click(".cvb-what")
        pg.clock.run_for(50)
        b = band(pg)
        check(b["cmd"] == "rm -rf build" and not b["dim"], f"펼침 → 명령 원문 그대로 · 허락 흐림 풀림 {b['cmd']!r}")
        why = pg.evaluate("() => document.querySelector('.cvb-why')?.textContent")
        check(why and "마스터를 깨워" in why, f"「왜」 = 자료 없음 정직 표시 {why}")
        pg.evaluate("() => { const b = document.querySelector('.cvb-allow'); b.click(); b.dispatchEvent(new MouseEvent('click', { bubbles: true })); }")
        pg.clock.run_for(50)
        check(replies(pg) == [], f"★대본 클릭(isTrusted=false) 2종 → 호출 0 ({replies(pg)})")
        pg.click(".cvb-allow")
        pg.clock.run_for(100)
        b = band(pg)
        check(replies(pg) == [{"requestId": "r1", "decision": "allow", "screenFingerprint": "fp-1"}], f"★펼친 뒤 진짜 클릭 → confirm_reply 1(번호·allow·지문) {replies(pg)}")
        check("허락했어요" in b["notice"] and b["head"] == "", f"결과 안내 · 처리된 항목 내려감 {b}")
        log = pg.evaluate("() => localStorage.getItem('cys-chat-decisions')")
        check(log is not None and "r1" in log and "rm -rf" not in log, f"누른 기록(번호·결정 · 명령 원문 0자) {log}")
        check(not errs, f"페이지 오류 0 {errs[:2]}")

        print("== E 이미 처리된 요청 → 호출 0 + 안내")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('r2', 2, 'git push')}]; }}")
        pg.clock.run_for(3_100)
        pg.click(".cvb-what")
        pg.clock.run_for(50)
        pg.evaluate("() => { window.__CHAT.feedItems = []; }")  # 그리기는 그대로(다음 고리 전) — 다른 길에서 처리됨
        pg.click(".cvb-allow")
        pg.clock.run_for(100)
        b = band(pg)
        check(len(replies(pg)) == 1 and b["notice"] == "이미 처리됐거나 바뀐 요청이에요.", f"★이미 처리된 요청 → 호출 0 + 안내 ({len(replies(pg))} · {b['notice']})")

        print("== F 펼친 뒤 판 바뀜(같은 번호 · 다른 명령 · 시각 주입)")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('r3', 2, 'ls build', '1763373000')}]; }}")
        pg.clock.run_for(3_100)
        pg.click(".cvb-what")
        pg.clock.run_for(50)
        check(band(pg)["cmd"] == "ls build", "펼친 판 = ls build")
        # 그리기와 클릭 사이(다음 3초 고리 전)에 데몬 쪽 판이 바뀐다 — 화면은 옛 판을 보인 채
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('r3', 2, 'rm -rf ~', '1763373000')}]; }}")
        pg.click(".cvb-allow")
        pg.clock.run_for(100)
        b = band(pg)
        check(len(replies(pg)) == 1 and b["notice"] == "이미 처리됐거나 바뀐 요청이에요.", f"★판 바뀜 → 호출 0 + 안내 ({len(replies(pg))} · {b['notice']})")
        pg.clock.run_for(3_100)
        b = band(pg)
        check(b["cmd"] is None and b["dim"], f"다음 그리기 = 새 판은 접힌 채(펼침이 이어지지 않음) · 허락 흐림 {b}")
        pg.click(".cvb-what")
        pg.clock.run_for(50)
        check(band(pg)["cmd"] == "rm -rf ~", "다시 펼치면 새 명령")

        print("== F2 펼친 뒤 좌석만 바뀜(codex 1R major 2)")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('r4', 2, 'ls seat', '1763373100')}]; }}")
        pg.clock.run_for(3_100)
        pg.click(".cvb-what")
        pg.clock.run_for(50)
        check(band(pg)["cmd"] == "ls seat" and not band(pg)["dim"], "펼친 판 = ls seat")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('r4', 3, 'ls seat', '1763373100')}]; }}")
        pg.clock.run_for(3_100)
        b = band(pg)
        check(b["cmd"] is None and b["dim"], f"★좌석만 바뀐 판 = 접힌 채 · 허락 흐림(펼침 승계 0) {b}")
        n_before = len(replies(pg))
        pg.click(".cvb-allow", force=True)
        pg.clock.run_for(100)
        check(len(replies(pg)) == n_before and "무엇을 보기" in band(pg)["notice"], f"★새 판을 펼치지 않은 허락(진짜 클릭) → 호출 0 + 흐린 허락 안내 ({len(replies(pg)) - n_before} · {band(pg)['notice']})")

        print("== F0 좌석이 직접 올린 approval(검증 F0) — 멈춤이어도 직접 단추 0")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('req-77', 2, 'ls -la', daemon=False)}]; }}")
        pg.clock.run_for(3_100)
        b = band(pg)
        check("마스터가 확인하는 중" in b["text"] and not b["allow"], f"daemon_issued 아님 → 「마스터가 확인하는 중」 · 단추 0 {b}")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('r3', 2, 'rm -rf ~', '1763373000')}]; }}")
        pg.clock.run_for(3_100)
        print("== G 거절 · 마스터 창 승인")
        pg.click(".cvb-deny")
        pg.clock.run_for(100)
        check(replies(pg)[-1] == {"requestId": "r3", "decision": "deny", "screenFingerprint": "fp-1"}, f"거절(진짜 클릭) → confirm_reply deny {replies(pg)[-1]}")
        check("거절했어요" in band(pg)["notice"], f"창을 실제로 누른 거절 = 「거절했어요」 {band(pg)['notice']}")
        print("== G2 데몬이 기록만 해소(actuated null · codex 1R major 5)")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('r5', 2, 'ls rec', fp=None)}]; window.__CHAT.replyResult = {{ request_id: 'r5', decision: 'deny', actuated: null }}; }}")
        pg.clock.run_for(3_100)
        pg.click(".cvb-deny")
        pg.clock.run_for(100)
        b = band(pg)
        check(replies(pg)[-1] == {"requestId": "r5", "decision": "deny", "screenFingerprint": None} and "기록만 됐고" in b["notice"] and "거절했어요" not in b["notice"],
              f"★기록만 해소 → 「했어요」 아님 · 작업 화면 확인 안내 {replies(pg)[-1]} · {b['notice']}")
        pg.evaluate("() => { window.__CHAT.replyResult = null; }")
        pg.evaluate(f"() => {{ window.__CHAT.feedItems = [{item_js('rm', 1, 'cargo build')}]; }}")
        pg.clock.run_for(3_100)
        b = band(pg)
        check("마스터 창에 확인할 것" in b["text"] and not b["allow"], f"마스터 좌석 승인 = 마스터 창 · 직접 단추 0 {b}")
        pg.click(".cvb-work")
        pg.clock.run_for(200)
        st = pg.evaluate("() => ({ host: document.getElementById('view-host').hidden, cvs: document.querySelectorAll('.cv').length })")
        check(st["host"] is True and st["cvs"] == 0, f"작업 화면에서 보기 → 작업 화면 {st}")
        check(pg.evaluate("() => window.__CHAT.legacy") == 0, "원작자 feed_reply 호출 0(대화 화면은 confirm_reply 만)")
        check(not errs, f"페이지 오류 0 {errs[:2]}")
        ctx.close()
    httpd.shutdown()
    print("\nRESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
