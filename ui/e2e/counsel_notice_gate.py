#!/usr/bin/env python3
"""「자동 보고」 첫 안내·켜기/끄기 헤드리스 게이트 — TICKET=cysr-1119-s10b(DESIGN §8-3 AG5 · D-11 · 1.1.19 · 수동 실행 · CI 배선 = master 판단).

1.1.19 에서 상단 「상담소」 창·45초 배지·「아고라」 단추·30분 반복 확인을 화면에서 뺐다. 남은 것을 실제 번들 + __TAURI__ 대역으로 잰다:
  1. 상단바·사이드바에 #btn-counsel·#btn-agora·#counsel-badge 0.
  2. needs_notice=true 대역 → 앱이 뜬 뒤 5초 안(여유 포함 8초) 안내 창 1(제목 「자동 보고 안내」 · 끝 문장 정본) ·
     [확인] → counsel_notice_seen 1 · counsel_auto_set 0(끄기를 안 눌렀다).
  3. 화면 설정 → 「자동 보고」 한 줄: 「자동 보고: 켜짐」 + [자동 보고 끄기] · 누름 → counsel_auto_set{on:false} → 「꺼짐」 + [자동 보고 켜기] ·
     누름 → counsel_auto_set{on:true} → 「켜짐」. (켜기/끄기 = 1.1.18 set_auto 길 그대로 — 팩 쪽은 test_javis_counsel 이 잰다.)
  4. (D-11) 화면 설정을 열 때 needs_notice=true 면 안내 창이 다시 뜬다(첫 확인이 실패한 기기의 다음 기회 · 반복 타이머 0).
  5. 판 2 를 본 기기의 재안내(needs_notice 계산) = 팩 시험 몫(test_notice_v3_1119_reshows_once_for_v2_viewers).
  6. 콘솔 오류 0.
실행: sh ui/build.sh(또는 같은 dist) 뒤 CHROME_PATH=<chrome-headless-shell> <playwright python3> ui/e2e/counsel_notice_gate.py   # exit 0 = PASS
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("sbg", Path(__file__).with_name("statusboard_gate.py"))
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)

TAIL = "끄려면 화면 설정 → ‘자동 보고’를 끄세요."

# 자동 보고 대역 — 상태를 들고 있다가 counsel_auto_set 으로 바꾼다 · 호출 장부 window.__calls · needs_notice 는 window.__NEEDS 로 켠다.
COUNSEL_SHIM = r"""
(() => {
  const base = window.__TAURI__.core.invoke;
  window.__calls = [];
  window.__AUTO = true;
  window.__NEEDS = true;
  window.__TAURI__.core.invoke = (cmd, args) => {
    if (cmd === 'counsel_auto_status' || cmd === 'counsel_auto_set' || cmd === 'counsel_notice_seen') {
      window.__calls.push([cmd, args ?? null]);
      if (cmd === 'counsel_auto_set') window.__AUTO = !!(args && args.on);
      if (cmd === 'counsel_notice_seen') { window.__NEEDS = false; return Promise.resolve({ ok: true }); }
      return Promise.resolve({ auto: window.__AUTO, notice_seen: !window.__NEEDS, needs_notice: window.__AUTO && window.__NEEDS });
    }
    return base(cmd, args);
  };
})();
"""

MODAL = r"""() => { const o = [...document.querySelectorAll('.modal-overlay.confirm-overlay')];
  return o.map((ov) => ({ title: ov.querySelector('h3')?.textContent ?? '', body: ov.textContent ?? '',
    yes: ov.querySelector('.modal-yes')?.textContent ?? '', no: ov.querySelector('.modal-no')?.textContent ?? '' })); }"""
ROW = r"""() => { const r = document.querySelector('#theme-pop .sp-auto-row'); if (!r) return null;
  return { state: r.querySelector('.sp-auto-state')?.textContent ?? '', btn: r.querySelector('.sp-auto-toggle')?.textContent ?? '',
    disabled: !!r.querySelector('.sp-auto-toggle')?.disabled, title: r.title }; }"""
CALLS = "() => window.__calls.map(([c, a]) => c + (a ? JSON.stringify(a) : ''))"


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(sbg.DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    js = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=s[7], self=s[8], task=s[9], ctx=s[10]) for s in sbg.W7]
    shim = sbg.SHIM.replace("__SEATS__", json.dumps(js)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1280, "height": 800})
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(COUNSEL_SHIM)
            pg.goto(f"http://127.0.0.1:{port}/index.html")
            # 1. 단추 0
            gone = pg.evaluate("() => ['btn-counsel','btn-agora','counsel-badge'].filter((id) => document.getElementById(id))")
            sbg.check(gone == [], f"상담소·아고라 단추·배지 0 {gone}")
            # 2. 첫 안내 — 5초 계기(여유 3초)
            pg.wait_for_timeout(1500)
            early = pg.evaluate(MODAL)
            sbg.check(not any(m["title"] == "자동 보고 안내" for m in early), "1.5초 시점엔 아직 안내 창 0(5초 계기)")
            pg.wait_for_timeout(6500)
            mods = [m for m in pg.evaluate(MODAL) if m["title"] == "자동 보고 안내"]
            sbg.check(len(mods) == 1, f"5초 계기 뒤 안내 창 1(실측 {len(mods)})")
            if mods:
                sbg.check(TAIL in mods[0]["body"], "안내문 끝 문장 = 정본(§8-3-1)")
                sbg.check((mods[0]["yes"], mods[0]["no"]) == ("자동 보고 끄기", "확인"), f"단추 = [확인]·[자동 보고 끄기] {mods[0]['yes']!r} {mods[0]['no']!r}")
                pg.click(".confirm-overlay .modal-no")
                pg.wait_for_timeout(300)
            calls = pg.evaluate(CALLS)
            sbg.check(calls.count("counsel_notice_seen") == 1 and not any(c.startswith("counsel_auto_set") for c in calls), f"[확인] → 봤음 표식 1 · 끄기 0 {calls}")
            # 3. 화면 설정 「자동 보고」 줄
            pg.click("#btn-theme")
            pg.wait_for_timeout(400)
            row = pg.evaluate(ROW)
            sbg.check(row is not None and row["state"] == "자동 보고: 켜짐" and row["btn"] == "자동 보고 끄기", f"화면 설정 줄 = 켜짐 + [자동 보고 끄기] {row}")
            sbg.check(row is not None and row["title"].endswith(TAIL), "줄 툴팁 = 안내문(켜짐)")
            pg.click("#theme-pop .sp-auto-toggle")
            pg.wait_for_timeout(300)
            row = pg.evaluate(ROW)
            sbg.check(row is not None and row["state"] == "자동 보고: 꺼짐" and row["btn"] == "자동 보고 켜기", f"끔 → 꺼짐 + [자동 보고 켜기] {row}")
            pg.click("#theme-pop .sp-auto-toggle")
            pg.wait_for_timeout(300)
            row = pg.evaluate(ROW)
            sbg.check(row is not None and row["state"] == "자동 보고: 켜짐", f"켬 → 켜짐 {row}")
            calls = pg.evaluate(CALLS)
            sbg.check('counsel_auto_set{"on":false}' in calls and 'counsel_auto_set{"on":true}' in calls, f"켜기/끄기 = counsel_auto_set 하나 {calls}")
            # 4. D-11 — 화면 설정을 열 때 needs_notice 면 다시 뜬다
            pg.keyboard.press("Escape")
            pg.evaluate("() => { window.__NEEDS = true; }")
            pg.click("#btn-theme")
            pg.wait_for_timeout(600)
            again = [m for m in pg.evaluate(MODAL) if m["title"] == "자동 보고 안내"]
            sbg.check(len(again) == 1, f"(D-11) 화면 설정 열 때 needs_notice → 안내 창 1(실측 {len(again)})")
            sbg.check(not errs, f"콘솔 오류 0 {errs[:3]}")
            ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
