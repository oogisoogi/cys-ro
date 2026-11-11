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
  const orig = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    if (['send_input', 'close_surface', 'create_surface'].includes(cmd)) window.__calls.push([cmd, args?.surfaceId ?? null, args?.data ?? null]);
    if (cmd === 'create_surface') { window.__SEATS.push({ sock: args?.socket ?? '/sandbox/cys.sock', sid: 50, no: 950, role: null, cwd: '/Users/sim', act: 'waiting', raw: 'idle', approval: false, self: null, task: null, ctx: null }); return Promise.resolve({ surface_id: 50, display_no: 950 }); }
    if (cmd === 'list_surfaces') return orig(cmd, args).then((r) => { for (const s of r.surfaces) if ((window.__EXITED ?? []).includes(s.surface_id)) s.exited = true; return r; });
    if (cmd === 'close_surface') return Promise.resolve({ ok: true });
    if (cmd === 'list_dir') return Promise.resolve([{ name: 'proj', is_dir: true }, { name: 'a.txt', is_dir: false }]);
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
