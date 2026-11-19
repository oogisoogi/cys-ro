#!/usr/bin/env python3
"""끝난 좌석의 옮긴 묶음 = 새 좌석이 물려받지 않음 게이트 — TICKET=cysr-tabs-sidebar-impl · 독립 검증 948 D3(master#07acca07 · 수동 실행 — CI 미배선).

원형 = 948 v_restore_gate.py 「A_role_reuse」. 실제 번들 + __TAURI__ 대역(statusboard_gate SHIM) · W7.
  끝(end): 좌석 6(worker-4 · lms)을 video 로 옮김(surface.group.changed) → 좌석 6 끝남(데몬이 실제로 내는 surface.exited) · 목록에서 사라짐
          → 같은 데몬에 새 좌석 60(역할 worker-4 재배정 · 폴더 newproj) → 60 = newproj 묶음 · 저장 기록에 #role:worker-4 없음
  재시작(restart): 같은 옮김 → 끝 이벤트 없이 좌석 6 이 번호만 61 로 바뀜(데몬 재시작 복원 · 같은 역할·폴더) → 61 = video 그대로 · 기록 유지
  목록 끝남(exited-row): 끝 이벤트를 놓치고 목록에 exited 표시만 온 경우도 기록을 지운다
실행: CHROME_PATH=<chrome-headless-shell> [GATE_DIST=<다른 번들>] cys run -- <playwright python3> ui/e2e/rolereuse_gate.py
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

GROUPS = r"""
() => { const host = document.querySelector('.ws-seats[data-seat-host]:not([data-seat-host="board"]):not([data-seat-host^="n"])'); const out = {}; let cur = '(묶음 머리 없음)';
  for (const el of host ? host.children : []) { if (el.classList.contains('ws-seat-group')) { cur = el.querySelector('.ws-seat-group-name')?.textContent; out[cur] = []; }
    else if (el.classList.contains('ws-seat') && !el.classList.contains('named')) (out[cur] ??= []).push(el.querySelector('.ws-seat-no')?.textContent); } return out; }
"""
EXITED = r"""
(() => { const orig = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => cmd === 'list_surfaces'
    ? orig(cmd, args).then((r) => { for (const s of r.surfaces) if ((window.__EXITED ?? []).includes(s.surface_id)) s.exited = true; return r; })
    : orig(cmd, args); })();
"""
MOVE = "() => window.__emit('daemon-event', { type: 'event', seq: 1, name: 'surface.group.changed', category: 'surface', surface_id: 6, socket_slug: 'base', payload: { surface_id: 6, group: 'video', previous: null } })"
END = "() => window.__emit('daemon-event', { type: 'event', seq: 2, name: 'surface.exited', category: 'surface', surface_id: 6, socket_slug: 'base', payload: { surface_id: 6, role: 'worker-4', agent: 'claude' } })"


def group_of(groups: dict, no: str):
    return next((g for g, nos in groups.items() if no in nos), None)


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

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
                pg.add_init_script(EXITED)
                pg.goto(url)
                pg.wait_for_timeout(11500)
                pg.evaluate(MOVE)
                pg.wait_for_timeout(4000)
                g = pg.evaluate(GROUPS)
                sbg.check(group_of(g, "934") == "video", f"준비: 좌석 6(934) = video 로 옮김 {g}")
                return ctx, pg, errs

            def replace6(pg, sid, no, cwd):
                pg.evaluate(f"""() => {{ const a = window.__SEATS; const i = a.findIndex((s) => s.sid === 6); if (i >= 0) a.splice(i, 1);
                  a.push({{ sock: '{sbg.BASE}', sid: {sid}, no: {no}, role: 'worker-4', cwd: '{cwd}', act: 'working', raw: 'active', approval: false, self: null, task: '새 일감', ctx: 5 }}); }}""")
                pg.wait_for_timeout(7500)

            rec = lambda pg: json.loads(pg.evaluate("() => localStorage.getItem('cys-seat-group')") or "{}")  # noqa: E731

            print("== 끝(end): 좌석 6 끝남 → 새 worker-4 좌석 60")
            ctx, pg, errs = page()
            pg.evaluate(END)
            pg.wait_for_timeout(500)
            replace6(pg, 60, 960, "/u/axdev/newproj")
            g = pg.evaluate(GROUPS)
            sbg.check(group_of(g, "960") == "newproj", f"새 좌석 960 = 제 폴더 newproj(옛 video 물려받지 않음) {g}")
            sbg.check("#role:worker-4" not in rec(pg), f"기록에서 #role:worker-4 지워짐 {rec(pg)}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            print("== 목록 끝남(exited-row): 끝 이벤트 놓침 · 목록 exited 표시만")
            ctx, pg, errs = page()
            pg.evaluate("() => { window.__EXITED = [6]; }")
            pg.wait_for_timeout(4000)
            sbg.check("#role:worker-4" not in rec(pg), f"목록 exited 표시로 기록 지워짐 {rec(pg)}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()

            print("== 재시작(restart): 끝 신호 없이 번호만 6 → 61")
            ctx, pg, errs = page()
            replace6(pg, 61, 961, "/u/axdev/lms")
            g = pg.evaluate(GROUPS)
            sbg.check(group_of(g, "961") == "video", f"번호만 바뀐 같은 좌석 961 = video 유지 {g}")
            sbg.check(rec(pg).get("#role:worker-4") == "video", f"기록 유지 {rec(pg)}")
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
