#!/usr/bin/env python3
"""숨은 탭 좌석 포커스 게이트 — TICKET=cysr-tabs-sidebar-impl · 독립 검증 948 D1(blocking)·D2·D6 고침(master#07acca07 · 수동 실행 — CI 미배선).

원형 = 948 의 ~/axdev/.wt/cys-tabs-sidebar-verify/docs/verify-out/v_focus_gate.py(기록만 하던 것) → 여기서는 단언하는 게이트.
실제 번들 + __TAURI__ 대역(statusboard_gate SHIM). 장면 W7(고정 1·2 · site 3·4·5 · lms 6·7 · video 8·9) · 1920×1200.
  ① 좌석 4(site) 포커스 → 탭 lms → 포커스가 보이는 lms 좌석으로 옮겨 간다 · 친 「abc」 = 그 보이는 좌석으로(D6) · 숨은 4 로 0
  ② ⌘W → 숨은 4 를 닫자고 묻지 않는다 · close_surface(4) 0(확인 창은 취소)
  ③ 숨은 동안 4 가 끝남(exited) → ⌘W → close_surface(4) 0(확인 창 없는 닫힘 경로)
  ④ ⌘D → 새 좌석이 지금 탭(lms)에 바로 보이고 7초(목록 2바퀴) 뒤에도 보인다 · 숨은 4 옆에 붙지 않는다(D2)
  ⑤ 탭 lms 에서 ⌘T → 새 좌석이 바로 보이고 7초 뒤에도 보인다 · 탭은 lms 그대로(D2)
  ⑥ 파일 트리 「cd 텍스트 삽입」 → send_input 대상 = 보이는 좌석(숨은 4 아님)
  ⑦ 넓게 보기(좌석 줄 6 클릭) → 포커스 = 6 · ⌘W 확인 창 = 6 의 이름
  ⑧ 한글 조합 중(CDP imeSetComposition 「한」) 탭 전환 → 숨은 4 로 send_input 0 · 다음 글자 = 보이는 좌석(조합 중이던 글자가 버려지는지는 실측 출력만 ·
     헤드리스 Chromium IME ≠ 실앱 WKWebView → HANDOFF canary 확인 항목)
  ⑨ (master#1dc9bd83) 좌석 4 에 입력 중 묶음 옮김 이벤트(4 → lms) → 탭이 lms 로 따라가고 포커스·입력 = 4 그대로 · 다른 좌석 send_input 0
  ⑩ 같은 장면을 한글 조합 중에 → send_input 대상 = 4 뿐
  ⑪ (codex 2R #2) 좌석 3(site) 「경로 삽입」 → 실재 확인(list_dir)을 1.5초 늦추고 그 사이 탭 lms 로 전환(3 숨음) → 3 으로 send_input 0 ·
     알림 「그 좌석이 화면에 없어서 넣지 않았어요」 (대조 = 전환하지 않으면 3 에 들어간다 — 게이트가 빈 통과가 아님)
  ⑫ (codex 2R #2) OS 드롭(tauri://drag-drop)으로 좌석 3 에 경로 → 같은 늦춤 사이 탭 전환 → 3 으로 send_input 0 · 알림
  ⑬ (codex 2R #1 · 불변식 정의 고정 — master 처분) 불변식 = 「숨은 좌석에 **새로 시작되는** 입력 0」(이미 시작된 입력을 숨었다고 버리거나 보류하지 않는다):
     ⓑ 좌석 4 가 보일 때 친 「abcd」 = send_input 을 0.4초씩 늦춰 줄 세운 채 바로 탭 lms 로 전환 → 남은 글자도 4 에만 · 순서대로 · 유실 0 ·
        다른 좌석 0(줄 선 글자 일부가 실제로 숨은 뒤에 나갔음을 함께 단언 — 장면이 빈 통과가 아님)
     ⓒ 숨은 뒤 새로 누른 「xy」 = 4 로 0(보이는 lms 좌석으로)
  ⑭ (codex 3R blocking 1) 좌석 4 머리 우클릭 「이름 변경」 → 「ab」 입력 중 3초 입양 틱이 새 역할 좌석 60 을 데려온다(attach_surface(60) 로 장면 성립 단언) →
     이어 친 「cd」 + Enter = 터미널 send_input 0(어느 좌석으로도) · 키보드는 편집 칸에 그대로 · 이름 = 「abcd」 로 확정(rename_surface(4)) ·
     확정 즉시(0.15초 · 주기 그리기를 기다리지 않음) 밀린 그리기 1회로 새 좌석 60 이 화면에 보인다
  ⑮ (ChatGPT F4) 좌석 이름 편집 중 사람 손 동작 — 탭 클릭 · ⌘T · ⌘W 마다: 화면이 그 동작대로 바뀌고(옛 화면으로 남지 않음) 편집은 「ab」 로 확정되어 끝나며
     터미널 send_input 0
실행: CHROME_PATH=<chrome-headless-shell> [GATE_DIST=<다른 번들 폴더>] cys run -- <playwright python3> ui/e2e/focus_gate.py
  (GATE_DIST = 고치기 전 번들로 돌려 붉음을 재는 대조용)
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else sbg.DIST
OUT = sbg.UI.parent / "docs" / "evidence-tabs-sidebar" / "948-focus"

SPY = r"""
(() => {
  window.__calls = [];
  window.__toasts = []; // 알림은 몇 초 뒤 사라진다 — 붙는 순간 글을 적어 둔다
  document.addEventListener('DOMContentLoaded', () => new MutationObserver((ms) => { for (const m of ms) for (const n of m.addedNodes) if (n.classList?.contains('toast')) window.__toasts.push(n.textContent); }).observe(document.body, { childList: true, subtree: true }));
  const orig = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    if (['send_input', 'close_surface', 'create_surface', 'attach_surface'].includes(cmd)) window.__calls.push([cmd, args?.surfaceId ?? null, args?.data ?? null, !!window.__HIDDEN_SINCE]);
    if (cmd === 'rename_surface') { window.__calls.push([cmd, args?.surfaceId ?? null, args?.title ?? null, false]); return Promise.resolve({ ok: true }); } // ⑭ = 이름 확정 기록
    if (cmd === 'send_input' && window.__SEND_DELAY) return new Promise((res) => setTimeout(res, window.__SEND_DELAY)).then(() => orig(cmd, args)); // ⑬ = 느린 데몬 흉내(앞 글자 응답이 늦어 뒤 글자가 줄 선다)
    if (cmd === 'create_surface') { window.__SEATS.push({ sock: args?.socket ?? '/sandbox/cys.sock', sid: 50, no: 950, role: null, cwd: '/Users/sim', act: 'waiting', raw: 'idle', approval: false, self: null, task: null, ctx: null }); return Promise.resolve({ surface_id: 50, display_no: 950 }); }
    if (cmd === 'list_surfaces') return orig(cmd, args).then((r) => { for (const s of r.surfaces) if ((window.__EXITED ?? []).includes(s.surface_id)) s.exited = true; return r; });
    if (cmd === 'close_surface') return Promise.resolve({ ok: true });
    if (cmd === 'list_dir') return new Promise((res) => setTimeout(() => res([{ name: 'proj', is_dir: true }, { name: 'a.txt', is_dir: false }]), window.__LISTDIR_DELAY ?? 0)); // ⑪⑫ = 느린 데몬 흉내
    if (cmd === 'path_exists' || cmd === 'stat_path') return Promise.resolve(true);
    return orig(cmd, args);
  };
})();
"""

STATE = r"""
() => ({ panes: [...document.querySelectorAll('#root .pane')].map((p) => +p.dataset.sid).sort((a, b) => a - b),
  focused: [...document.querySelectorAll('.pane.focused')].filter((p) => p.isConnected).map((p) => +p.dataset.sid),
  active: (() => { const a = document.activeElement; const p = a?.closest?.('.pane'); return p ? +p.dataset.sid : (a?.tagName ?? null); })(),
  tab: document.querySelector('#root .group-tab.active .group-tab-name')?.textContent ?? null,
  modal: document.querySelector('.modal-overlay')?.textContent ?? null })
"""

LMS = {6, 7}


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    seats = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=False, self=s[8], task=s[9], ctx=s[10]) for s in sbg.W7]
    print("번들:", DIST)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

            def page():
                ctx = br.new_context(viewport={"width": 1920, "height": 1200})
                pg = ctx.new_page()
                errs: list[str] = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
                pg.add_init_script(sbg.SHIM.replace("__SEATS__", "window.__SEATS = " + json.dumps(seats)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE))
                pg.add_init_script(SPY)
                pg.goto(url)
                pg.wait_for_timeout(11500)
                return ctx, pg, errs

            def focus4_then_lms(pg):
                pg.click('#root .pane[data-sid="4"] .xterm-screen')
                pg.wait_for_timeout(300)
                pg.click('#root .group-tab:has-text("lms")')
                pg.wait_for_timeout(500)
                pg.evaluate("() => { window.__calls = []; }")
                return pg.evaluate(STATE)

            def calls(pg, cmd):
                return pg.evaluate(f"() => window.__calls.filter((c) => c[0] === '{cmd}')")

            def cancel_modal(pg):
                if pg.query_selector(".modal-overlay"):
                    btns = pg.query_selector_all(".modal-overlay button")
                    no = [b for b in btns if "닫기" not in (b.text_content() or "")]
                    (no[0] if no else btns[-1]).click()
                    pg.wait_for_timeout(300)

            # ①② 포커스 옮김 · 글자 · ⌘W
            print("== ①② 탭 전환 뒤 포커스 · 글자 · ⌘W")
            ctx, pg, errs = page()
            s1 = focus4_then_lms(pg)
            sbg.check(s1["tab"] == "lms" and 4 not in s1["panes"], f"탭 lms · 좌석 4 숨김 {s1['panes']}")
            sbg.check(len(s1["focused"]) == 1 and s1["focused"][0] in LMS and s1["active"] in LMS, f"포커스 = 보이는 lms 좌석(표시 {s1['focused']} · 키보드 {s1['active']})")
            pg.keyboard.type("abc")
            pg.wait_for_timeout(400)
            typed = calls(pg, "send_input")
            sbg.check(bool(typed) and all(c[1] in LMS for c in typed), f"(D6) 친 글자 = 보이는 좌석으로 {typed}")
            pg.keyboard.press("Meta+w")
            pg.wait_for_timeout(500)
            s2 = pg.evaluate(STATE)
            pg.screenshot(path=str(OUT / "cmdw-after-tab.png"))
            sbg.check(not (s2["modal"] and "932" in s2["modal"]), f"⌘W 확인 창이 숨은 4(932)를 묻지 않는다 · {s2['modal']!r}")
            cancel_modal(pg)
            sbg.check(not any(c[1] == 4 for c in calls(pg, "close_surface")), f"close_surface(4) 0 {calls(pg, 'close_surface')}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # ③ 숨은 동안 끝난 4 + ⌘W
            print("== ③ 끝난 숨은 좌석 + ⌘W")
            ctx, pg, errs = page()
            focus4_then_lms(pg)
            pg.evaluate("() => { window.__EXITED = [4]; }")
            pg.wait_for_timeout(4000)
            pg.keyboard.press("Meta+w")
            pg.wait_for_timeout(600)
            cancel_modal(pg)
            sbg.check(not any(c[1] == 4 for c in calls(pg, "close_surface")), f"확인 창 없는 닫힘 경로로도 close_surface(4) 0 {calls(pg, 'close_surface')}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # ④ ⌘D
            print("== ④ 탭 전환 뒤 ⌘D")
            ctx, pg, errs = page()
            focus4_then_lms(pg)
            pg.keyboard.press("Meta+d")
            pg.wait_for_timeout(800)
            s2 = pg.evaluate(STATE)
            pg.wait_for_timeout(7000)
            s3 = pg.evaluate(STATE)
            pg.screenshot(path=str(OUT / "cmdd-after-tab.png"))
            sbg.check(50 in s2["panes"] and 50 in s3["panes"] and s3["tab"] == "lms", f"(D2) ⌘D 새 좌석 50 = 바로 {s2['panes']} · 7초 뒤 {s3['panes']} · 탭 {s3['tab']}")
            sbg.check(4 not in s3["panes"], "숨은 4 는 여전히 숨김(분할 대상 아님)")
            sbg.check(s3["focused"] == [50], f"포커스 = 새 좌석 {s3['focused']}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # ⑤ ⌘T
            print("== ⑤ 탭 lms 에서 ⌘T")
            ctx, pg, errs = page()
            pg.click('#root .group-tab:has-text("lms")')
            pg.wait_for_timeout(500)
            pg.keyboard.press("Meta+t")
            pg.wait_for_timeout(800)
            t1 = pg.evaluate(STATE)
            pg.wait_for_timeout(7000)
            t2 = pg.evaluate(STATE)
            pg.screenshot(path=str(OUT / "cmdt-after-tab.png"))
            sbg.check(50 in t1["panes"] and 50 in t2["panes"] and t2["tab"] == "lms", f"(D2) ⌘T 새 좌석 50 = 바로 {t1['panes']} · 7초 뒤 {t2['panes']} · 탭 {t2['tab']}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # ⑥ 파일 트리 cd 삽입
            print("== ⑥ 파일 트리 「cd 텍스트 삽입」")
            ctx, pg, errs = page()
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.evaluate("() => document.getElementById('btn-files').click()")
            pg.wait_for_timeout(800)
            pg.click('#root .group-tab:has-text("lms")')
            pg.wait_for_timeout(800)
            pg.evaluate("() => { window.__calls = []; }")
            row = pg.query_selector('#ft-body .ft-row.dir:has-text("proj")')
            sbg.check(row is not None, "파일 트리 폴더 줄 proj")
            if row:
                row.click(button="right")
                pg.wait_for_timeout(300)
                item = pg.query_selector('#ctx-menu :text("cd 텍스트 삽입")')
                sbg.check(item is not None, "메뉴 「cd 텍스트 삽입」")
                if item:
                    item.click()
                    pg.wait_for_timeout(500)
            ins = calls(pg, "send_input")
            sbg.check(bool(ins) and all(c[1] in LMS for c in ins), f"cd 삽입 대상 = 보이는 좌석 {ins}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # ⑦ 넓게 보기 전환
            print("== ⑦ 좌석 4 포커스 → 좌석 줄 6 클릭(넓게 보기)")
            ctx, pg, errs = page()
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.click('.ws-seat[data-sid="6"]')
            pg.wait_for_timeout(600)
            z = pg.evaluate(STATE)
            sbg.check(4 not in z["panes"] and z["focused"] == [6], f"넓게 보기 = 포커스 6 {z}")
            pg.keyboard.press("Meta+w")
            pg.wait_for_timeout(500)
            m = pg.evaluate(STATE)["modal"]
            sbg.check(not (m and "932" in m), f"⌘W 가 숨은 4 를 묻지 않는다 {m!r}")
            cancel_modal(pg)
            sbg.check(not any(c[1] == 4 for c in calls(pg, "close_surface")), "close_surface(4) 0")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            MOVE4 = "() => window.__emit('daemon-event', { type: 'event', seq: 9, name: 'surface.group.changed', category: 'surface', surface_id: 4, socket_slug: 'base', payload: { surface_id: 4, group: 'lms', previous: null } })"
            # ⑨ 묶음 옮김 = 좌석 따라가기
            print("== ⑨ 입력 중 묶음 옮김(사람 손 아님) → 좌석 따라가기")
            ctx, pg, errs = page()
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.evaluate("() => { window.__calls = []; }")
            pg.keyboard.type("ab")
            pg.wait_for_timeout(200)
            pg.evaluate(MOVE4)
            pg.wait_for_timeout(800)
            st = pg.evaluate(STATE)
            pg.keyboard.type("cd")
            pg.wait_for_timeout(400)
            sent = calls(pg, "send_input")
            pg.screenshot(path=str(OUT / "follow-after-regroup.png"))
            sbg.check(st["tab"] == "lms" and 4 in st["panes"] and st["focused"] == [4] and st["active"] == 4, f"탭이 4 의 새 묶음 lms 로 따라감 · 포커스 4 그대로 {st}")
            sbg.check(sent and all(c[1] == 4 for c in sent) and "".join(c[2] for c in sent) == "abcd", f"입력 = 4 뿐 · 유실 0 {sent}")
            sbg.check(not (st["modal"] or "").strip(), "확인 창 0")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            # ⑩ 조합 중 묶음 옮김
            print("== ⑩ 한글 조합 중 묶음 옮김")
            ctx, pg, errs = page()
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.evaluate("() => { window.__calls = []; }")
            cdp = ctx.new_cdp_session(pg)
            cdp.send("Input.imeSetComposition", {"text": "한", "selectionStart": 1, "selectionEnd": 1})
            pg.wait_for_timeout(200)
            pg.evaluate(MOVE4)
            pg.wait_for_timeout(800)
            cdp.send("Input.insertText", {"text": "글"})
            pg.wait_for_timeout(500)
            sent = calls(pg, "send_input")
            sbg.check(sent and all(c[1] == 4 for c in sent), f"조합 중 옮김 → 입력 대상 = 4 뿐 {sent}")
            print(f"  (실측) 보낸 글자 = {''.join(c[2] for c in sent)!r}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            # ⑪ 경로 삽입 메뉴 — 실재 확인을 기다리는 사이 대상이 숨음
            HIDDEN_MSG = "그 좌석이 화면에 없어서 넣지 않았어요"

            def menu_insert_to3(pg):
                pg.click('#root .pane[data-sid="3"] .xterm-screen')
                pg.wait_for_timeout(300)
                pg.evaluate("() => { if (!document.getElementById('ft-body')?.offsetParent) document.getElementById('btn-files').click(); }")
                pg.wait_for_timeout(800)
                name3 = pg.evaluate("() => document.querySelector('#root .pane[data-sid=\"3\"] .pane-title-text')?.textContent ?? ''")
                pg.evaluate("() => { window.__calls = []; window.__toasts = []; window.__LISTDIR_DELAY = 1500; }")
                row = pg.query_selector('#ft-body .ft-row:has-text("a.txt")')
                sbg.check(row is not None, "파일 트리 파일 줄 a.txt")
                if not row:
                    return False
                row.click(button="right")
                pg.wait_for_timeout(300)
                item = next((i for i in pg.query_selector_all("#ctx-menu *") if (i.text_content() or "").strip() == f"➤ {name3} 에 경로 삽입"), None)
                sbg.check(item is not None, f"메뉴 「➤ {name3} 에 경로 삽입」")
                if not item:
                    return False
                item.click()
                return True

            print("== ⑪ 경로 삽입 — 실재 확인 사이 탭 전환(대조: 전환 없음)")
            ctx, pg, errs = page()
            if menu_insert_to3(pg):
                pg.wait_for_timeout(2200)
                ctl = calls(pg, "send_input")
                sbg.check(any(c[1] == 3 for c in ctl), f"(대조) 전환 없으면 좌석 3 에 들어간다 {ctl}")
            if menu_insert_to3(pg):
                pg.wait_for_timeout(300)
                pg.click('#root .group-tab:has-text("lms")')
                pg.wait_for_timeout(2200)
                ins = calls(pg, "send_input")
                tst = pg.evaluate("() => window.__toasts")
                sbg.check(not any(c[1] == 3 for c in ins), f"숨은 좌석 3 으로 send_input 0 {ins}")
                sbg.check(not ins, f"다른 좌석으로도 0(대상을 바꾸지 않는다) {ins}")
                sbg.check(any(HIDDEN_MSG in (t or "") for t in tst), f"알림 「{HIDDEN_MSG}」 {tst}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            # ⑫ OS 드롭 — 같은 늦춤 사이 탭 전환
            print("== ⑫ OS 드롭 — 실재 확인 사이 탭 전환")
            ctx, pg, errs = page()
            box = pg.query_selector('#root .pane[data-sid="3"] .xterm-screen').bounding_box()
            pg.evaluate("() => { window.__calls = []; window.__toasts = []; window.__LISTDIR_DELAY = 1500; }")
            pg.evaluate("([x, y]) => window.__emit('tauri://drag-drop', { paths: ['/Users/sim/proj'], position: { x, y } })", [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
            pg.wait_for_timeout(300)
            pg.click('#root .group-tab:has-text("lms")')
            pg.wait_for_timeout(2200)
            ins = calls(pg, "send_input")
            tst = pg.evaluate("() => window.__toasts")
            sbg.check(not ins, f"숨은 좌석 3 · 다른 좌석으로 send_input 0 {ins}")
            sbg.check(any(HIDDEN_MSG in (t or "") for t in tst), f"알림 「{HIDDEN_MSG}」 {tst}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            # ⑬ 숨기 전에 시작된 입력 · 숨은 뒤 새 입력
            print("== ⑬ 보일 때 시작된 입력은 숨은 뒤에도 그 좌석에 끝까지 · 숨은 뒤 새 키는 그 좌석으로 0")
            ctx, pg, errs = page()
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.evaluate("() => { window.__calls = []; window.__SEND_DELAY = 400; window.__HIDDEN_SINCE = 0; }")
            pg.keyboard.type("abcd")
            pg.click('#root .group-tab:has-text("lms")')
            pg.evaluate("() => { window.__HIDDEN_SINCE = Date.now(); }")
            pg.wait_for_timeout(300)
            s13 = pg.evaluate(STATE)
            sbg.check(s13["tab"] == "lms" and 4 not in s13["panes"], f"탭 lms · 좌석 4 숨음 {s13['panes']}")
            pg.keyboard.type("xy")
            pg.wait_for_timeout(2500)
            sent = calls(pg, "send_input")
            to4 = [c for c in sent if c[1] == 4]
            sbg.check("".join(c[2] for c in to4) == "abcd", f"ⓑ 보일 때 친 글자 = 4 에 끝까지 · 순서대로 · 유실 0 {to4}")
            sbg.check(any(c[3] for c in to4), f"ⓑ 줄 선 글자 일부가 숨은 뒤에 4 로 나갔다(장면 성립) {to4}")
            sbg.check(not any(c[1] not in (4, *LMS) for c in sent) and not any(c[1] in LMS and c[2] in "abcd" for c in sent), f"ⓑ 보일 때 친 글자 = 다른 좌석 0 {sent}")
            sbg.check(not any(c[1] == 4 and c[2] in ("x", "y") for c in sent), f"ⓒ 숨은 뒤 새 키 = 4 로 0 {sent}")
            sbg.check("".join(c[2] for c in sent if c[1] in LMS) == "xy", f"ⓒ 숨은 뒤 새 키 = 보이는 lms 좌석으로 {sent}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            # ⑭ 좌석 이름 변경 중 입양 틱
            print("== ⑭ 좌석 이름 변경 중 3초 입양 틱 → 이어 친 글자·Enter 는 편집 칸에(터미널 0)")
            ctx, pg, errs = page()
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.click('#root .pane[data-sid="4"] .pane-title-text', button="right")
            pg.wait_for_timeout(300)
            item = next((i for i in pg.query_selector_all("#ctx-menu .ctx-item") if (i.text_content() or "").strip() == "이름 변경"), None)
            sbg.check(item is not None, "좌석 머리 우클릭 = 「이름 변경」")
            if item:
                item.click()
                pg.wait_for_timeout(200)
                pg.evaluate("() => { window.__calls = []; }")
                pg.keyboard.type("ab")
                pg.evaluate("() => window.__SEATS.push({ sock: '__BASE__', sid: 60, no: 960, role: 'worker-8', cwd: '/u/axdev/site', act: 'waiting', raw: 'idle', approval: false, self: null, task: null, ctx: null })".replace("__BASE__", sbg.BASE))
                pg.wait_for_timeout(4000)  # 3초 목록 1바퀴 + 입양
                att = calls(pg, "attach_surface")
                sbg.check(any(c[1] == 60 for c in att), f"(장면 성립) 편집 중 입양 틱이 새 좌석 60 을 데려왔다 {att}")
                ed = pg.evaluate("() => { const a = document.activeElement; return { editing: !!a?.classList?.contains('pane-title-text') && a.isContentEditable, sid: +(a?.closest?.('.pane')?.dataset.sid ?? -1), tag: a?.tagName ?? null }; }")
                sbg.check(ed["editing"] and ed["sid"] == 4, f"입양 틱 뒤에도 키보드 = 좌석 4 이름 편집 칸 {ed}")
                pg.keyboard.type("cd")
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(150)
                s14 = pg.evaluate(STATE)  # 확정(blur) 처리기가 그 자리에서 밀린 그리기 1회 — 다른 주기 그리기를 기다리지 않는다
                pg.wait_for_timeout(650)
                sent = calls(pg, "send_input")
                ren = calls(pg, "rename_surface")
                sbg.check(not sent, f"이어 친 「cd」·Enter = 터미널 send_input 0 {sent}")
                sbg.check([c[1:3] for c in ren] == [[4, "abcd"]], f"이름 = 「abcd」 로 한 번 확정 {ren}")
                sbg.check(60 in s14["panes"], f"확정 즉시(0.15초) 밀린 그리기 1회 = 새 좌석 60 보임 {s14['panes']}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            # ⑮ 좌석 이름 편집 중 사람 손 동작
            print("== ⑮(ChatGPT F4) 좌석 이름 편집 중 사람 손 동작 — 화면이 옛 상태로 남지 않는다")

            def start_rename4(pg):
                pg.click('#root .pane[data-sid="4"] .xterm-screen')
                pg.wait_for_timeout(300)
                pg.click('#root .pane[data-sid="4"] .pane-title-text', button="right")
                pg.wait_for_timeout(300)
                it = next((i for i in pg.query_selector_all("#ctx-menu .ctx-item") if (i.text_content() or "").strip() == "이름 변경"), None)
                if it:
                    it.click()
                    pg.wait_for_timeout(200)
                    pg.evaluate("() => { window.__calls = []; }")
                    pg.keyboard.type("ab")
                return it is not None

            def editing(pg):
                return pg.evaluate("() => !!document.querySelector('.pane-title-text[contenteditable=\"true\"]')")

            for case in ("tab-click", "cmd-t", "cmd-w"):
                ctx, pg, errs = page()
                sbg.check(start_rename4(pg), f"[{case}] 이름 변경 시작")
                if case == "tab-click":
                    pg.click('#root .group-tab:has-text("lms")')
                    pg.wait_for_timeout(600)
                    st = pg.evaluate(STATE)
                    if st["tab"] != "lms":  # (실측 · 이 티켓 전 aa110891 번들도 같음) 편집을 끝내는 첫 클릭은 탭을 못 바꾼다 — 화면·상태는 같이 site(어긋남 없음) · 다시 누르면 바뀐다
                        print(f"  (실측) 편집 중 첫 탭 클릭 = 편집 확정만 · 탭 그대로 {st['tab']}")
                        pg.click('#root .group-tab:has-text("lms")')
                        pg.wait_for_timeout(600)
                        st = pg.evaluate(STATE)
                    sbg.check(st["tab"] == "lms" and 4 not in st["panes"], f"[{case}] 화면 = 누른 탭(lms) · 좌석 4 숨음 {st['panes']} · 탭 {st['tab']}")
                elif case == "cmd-t":
                    pg.keyboard.press("Meta+t")
                    pg.wait_for_timeout(800)
                    st = pg.evaluate(STATE)
                    sbg.check(50 in st["panes"], f"[{case}] ⌘T 로 만든 새 좌석 50 이 바로 보인다(이름 편집에 묶여 옛 화면으로 남지 않음) {st['panes']}")
                else:
                    pg.keyboard.press("Meta+w")
                    pg.wait_for_timeout(600)
                    st = pg.evaluate(STATE)
                    sbg.check(st["modal"] is not None, f"[{case}] ⌘W = 닫기 확인 창이 뜬다 {st['modal']!r}")
                    cancel_modal(pg)
                ren = calls(pg, "rename_surface")
                sbg.check(not editing(pg) and [c[1:3] for c in ren] == [[4, "ab"]], f"[{case}] 편집은 확정(「ab」)되고 끝났다 · 편집 중 {editing(pg)} · {ren}")
                sbg.check(not calls(pg, "send_input"), f"[{case}] 터미널 send_input 0 {calls(pg, 'send_input')}")
                sbg.check(not errs, f"[{case}] 오류 0 {errs[:2]}")
                ctx.close()
            # ⑧ 한글 조합 중 탭 전환
            print("== ⑧ 한글 조합 중 탭 전환")
            ctx, pg, errs = page()
            pg.click('#root .pane[data-sid="4"] .xterm-screen')
            pg.wait_for_timeout(300)
            pg.evaluate("() => { window.__calls = []; }")
            cdp = ctx.new_cdp_session(pg)
            cdp.send("Input.imeSetComposition", {"text": "한", "selectionStart": 1, "selectionEnd": 1})
            pg.wait_for_timeout(200)
            pg.click('#root .group-tab:has-text("lms")')
            pg.wait_for_timeout(600)
            mid = calls(pg, "send_input")
            cdp.send("Input.insertText", {"text": "글"})
            pg.wait_for_timeout(500)
            sent = calls(pg, "send_input")
            sbg.check(not any(c[1] == 4 for c in sent), f"조합 중 탭 전환 → 숨은 4 로 0 {sent}")
            sbg.check(any(c[1] in LMS and c[2] == "글" for c in sent), f"다음 글자 = 보이는 좌석 {sent}")
            print(f"  (실측) 조합 중이던 「한」 = {'버려짐(어디로도 안 감)' if not mid else mid}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    for f in sbg.failures:
        print("  FAIL:", f)
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
