#!/usr/bin/env python3
"""대화 화면 틀 게이트 — TICKET=cysr-1119-s5 · DESIGN §4-1 CV-RAIL · §4-2 CV-EX3 · §6 V2·V3·V5·V6·V8·V11 (수동 실행 — CI 미배선).

실제 번들 + __TAURI__ 대역(tickrec_gate SHIM + chat_gate CHAT_SHIM + s79_gate FS_SHIM) + 가짜 시계. 클릭 = playwright 실제 마우스.

A CV-RAIL: 1280×800 · 1024×700 · 600×800 에서 가운데 칸(.cv) 안 overflow-y auto|scroll 요소 = .cv-log 하나(입력칸 제외) · 결과 50장에도 가운데 칸 높이 불변 ·
  결과 칸 = 왼쪽 칸 안 · 결과 있을 때 보임 · 머리 기본 접힘 · 펼친 카드 높이 ≤ 2줄(100px) · 왼쪽 칸이 스크롤 · 600 = 「결과 N」 한 줄 단추 → 덮개
B CV-EX3: 빈 화면 단추 3 · 누름 → 입력칸 = 예시 · 보낸 말 0 · 쓰던 글이 있으면 그대로
C V2: 밝은 대화 화면 상단바 바탕 = --cv-bg(흰) · 작업 화면 = #161b22 · 800/1024/1280 상단바 넘침 0
D V3: 머리 18px/400 동률 ≤ 3 · data-min 4칸 · 한도 줄 = 넓은 창 왼쪽 칸 아래 / 420 = 머리
E V5: 빈 칸 = 한 줄(≤ 31px) · 보내기 꺼짐 · 9줄 = 8줄 높이 + 칸 안 스크롤 · 조합 중 Enter = 쓰기 0
F V6: 위 200px 에서 답 1 → 위치 불변 + 「↓ 새 답 1 · 맨 아래로」 · 누르면 맨 아래 · 칸 1.5배 답 → 첫 줄이 칸 위 24px 안 · 바닥 48px 안 짧은 답 → 따라감(단추 0) · 단추 44px
G V8: Tab 으로 옮긴 단추 = 2px 링 · 마우스 클릭 = 링 0
H V11: 뼈대 = 시각 100ms 불투명도 0 · 1000ms 보임 · 움직임 줄이기 = 반짝임 애니메이션 0
I 대화 화면(.cv-wrap) 글자 18px 미만 0 · 페이지 오류 0
실행: CHROME_PATH=<chrome-headless-shell> cys run -- <진짜 playwright python3> ui/e2e/chatscroll_gate.py
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
from s79_gate import FS_SHIM, HOME  # noqa: E402

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"
OUT = Path(os.environ.get("CHATSCROLL_SHOTS", "/tmp/chatscroll-gate-shots"))

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


SCROLLERS = """() => [...document.querySelectorAll('#view-host .cv, #view-host .cv *')].filter((e) => { if (e.tagName === 'TEXTAREA') return false;
  const o = getComputedStyle(e).overflowY; return (o === 'auto' || o === 'scroll') && e.getBoundingClientRect().height > 0; }).map((e) => e.className)"""
LOGH = "() => Math.round(document.querySelector('.cv-log').getBoundingClientRect().height)"


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
    errs: list[str] = []
    with sync_playwright() as p:
        exe = os.environ.get("CHROME_PATH")
        br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

        def page(width: int = 1280, height: int = 800, chat: bool = True):
            ctx = br.new_context(viewport={"width": width, "height": height}, color_scheme="light")
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.add_init_script(FS_SHIM)
            pg.goto(url)
            pg.clock.run_for(9_000)
            pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}, {seat(BASE, 2, 'cso')}); }}")
            pg.clock.run_for(6_000)
            if chat:
                pg.click("#view-switch button[data-view=chat]")
                pg.clock.run_for(3_300)
            return ctx, pg

        def reply(pg, uuid: str, text: str) -> None:
            pg.evaluate(f"""() => {{ const C = window.__CHAT; C.file.push({{ uuid: '{uuid}', parent: null, role: 'assistant', text: {json.dumps(text)}, ts: new Date(Date.now()).toISOString() }}); C.master.idle_secs = 0; }}""")
            pg.clock.run_for(3_100)
            pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
            pg.clock.run_for(3_100)

        def results(pg, n: int) -> None:
            dirs = [f"{HOME}/cys-runs/r{i}" for i in range(n)]
            pg.evaluate(f"""(ds) => {{ window.__CHAT.fs['{HOME}/cys-runs'] = ds.map((d) => ({{ name: d.split('/').pop(), is_dir: true }}));
              ds.forEach((d, i) => window.__emit('daemon-event', {{ name: 'skill.run_finished', socket_slug: 'base', payload: {{ run_id: 'r' + i, status: 'done', artifact_dir: d }} }})); }}""", dirs)
            pg.clock.run_for(3_300)

        print("== A CV-RAIL 가운데 칸 스크롤 상자 하나 · 결과 칸 = 왼쪽 칸")
        for w, hh in ((1280, 800), (1024, 700), (600, 800)):
            ctx, pg = page(w, hh)
            s0 = pg.evaluate(SCROLLERS)
            h0 = pg.evaluate(LOGH)
            check(s0 == ["cv-log"], f"[{w}×{hh}] 빈 장면 가운데 스크롤 상자 = .cv-log 하나 {s0}")
            check(pg.evaluate("() => document.querySelector('[data-rail=results]').hidden") is True, f"[{w}] 결과 0 = 결과 칸 숨김")
            results(pg, 1)
            hone = pg.evaluate(LOGH)
            results(pg, 50)
            s1 = pg.evaluate(SCROLLERS)
            h1 = pg.evaluate(LOGH)
            # 가운데 칸 높이 = 결과 수와 무관(1장 = 50장) · 넓은 창은 결과 0 과도 같음 · 600 은 「결과 N」 한 줄 단추 몫(DESIGN §4-1 ⑤)만 줄어듦
            check(s1 == ["cv-log"] and h1 == hone and (w <= 600 or h1 == h0), f"[{w}×{hh}] 결과 50 = 스크롤 상자 그대로 하나 · 가운데 칸 높이 불변(0 {h0} · 1장 {hone} · 50장 {h1})")
            st = pg.evaluate("""() => { const r = document.querySelector('.cv-rail'); const res = document.querySelector('.cv-results');
              return { inRail: !!res && r.contains(res), hidden: document.querySelector('[data-rail=results]').hidden, exp: res?.querySelector('.cvr-head')?.getAttribute('aria-expanded'),
                head: res?.querySelector('.cvr-head')?.textContent, railShown: getComputedStyle(r).display !== 'none' }; }""")
            check(st["inRail"] and st["hidden"] is False and st["exp"] == "false" and st["head"] == "결과 50 · 새 결과 50", f"[{w}] 결과 칸 = 왼쪽 칸 안 · 보임 · 머리 기본 접힘 {st}")
            if w > 600:
                pg.click(".cv-results .cvr-head")
                pg.clock.run_for(100)
                cards = pg.evaluate("""() => { const r = document.querySelector('.cv-rail'); return { hs: [...document.querySelectorAll('.cv-rail .cvr-res-card')].map((c) => Math.round(c.getBoundingClientRect().height)),
                  scroll: r.scrollHeight > r.clientHeight, w: Math.round(r.getBoundingClientRect().width) }; }""")
                check(len(cards["hs"]) == 50 and max(cards["hs"]) <= 100 and cards["scroll"], f"[{w}] 펼침 = 카드 50 · 카드 높이 ≤ 2줄(100px · 최대 {max(cards['hs'] or [0])}) · 왼쪽 칸 한 스크롤")
                check(pg.evaluate(SCROLLERS) == ["cv-log"] and pg.evaluate(LOGH) == h0, f"[{w}] 펼쳐도 가운데 칸 그대로")
                pg.click(".cv-results .cvr-res-card >> nth=0 >> .cvr-more")
                pg.clock.run_for(3_300)  # 3초 다시 그리기 뒤에도 펼침 유지(C-18)
                ex = pg.evaluate("() => { const c = document.querySelector('.cv-rail .cvr-res-card'); return { exp: c.querySelector('.cvr-more').getAttribute('aria-expanded'), reveal: !!c.querySelector('.cvr-reveal'), revise: !!c.querySelector('.cvr-revise') }; }")
                check(ex == {"exp": "true", "reveal": True, "revise": True}, f"[{w}] 카드 이름 누름 = 펼침(폴더 보기 · 고쳐 달라고 하기) · 다시 그린 뒤 유지 {ex}")
                pg.screenshot(path=str(OUT / f"a-rail-{w}.png"))
            else:
                nb = pg.evaluate("() => { const b = document.querySelector('.cv-res-narrow'); return { shown: getComputedStyle(b).display !== 'none', text: b.textContent, h: Math.round(b.getBoundingClientRect().height) }; }")
                check(nb["shown"] and nb["text"] == "결과 50 · 새 결과 50" and nb["h"] >= 44, f"[600] 가운데 칸 위 「결과 N」 한 줄 단추 {nb}")
                pg.click(".cv-res-narrow")
                pg.clock.run_for(100)
                ov = pg.evaluate("() => { const r = document.querySelector('.cv-rail'); const cs = getComputedStyle(r); return { shown: cs.display !== 'none', pos: cs.position, exp: document.querySelector('.cv-results .cvr-head').getAttribute('aria-expanded') }; }")
                check(ov == {"shown": True, "pos": "absolute", "exp": "true"} and pg.evaluate(SCROLLERS) == ["cv-log"], f"[600] 누름 = 왼쪽 칸 덮개 · 결과 칸 펼침 · 가운데 스크롤 상자 그대로 {ov}")
                pg.screenshot(path=str(OUT / "a-rail-600-overlay.png"))
                pg.mouse.click(560, 400)  # 덮개 밖 가운데 칸 누름 = 닫힘(덮개가 「결과 N」 단추를 가리므로)
                pg.clock.run_for(100)
                check(pg.evaluate("() => getComputedStyle(document.querySelector('.cv-rail')).display") == "none", "[600] 가운데 칸 누름 = 덮개 닫힘")
                pg.click(".cv-res-narrow")
                pg.keyboard.press("Escape")
                pg.clock.run_for(100)
                check(pg.evaluate("() => getComputedStyle(document.querySelector('.cv-rail')).display") == "none", "[600] Esc = 덮개 닫힘")
            ctx.close()

        print("== B CV-EX3 빈 화면 예시")
        ctx, pg = page()
        btns = pg.evaluate("() => [...document.querySelectorAll('.cv-empty .cv-ex-btn')].map((b) => [b.textContent, Math.round(b.getBoundingClientRect().height)])")
        check(len(btns) == 3 and all(b[1] >= 44 for b in btns), f"단추 3 · 44px 이상 {btns}")
        pg.click(".cv-ex-btn >> nth=1")
        pg.clock.run_for(3_300)
        st = pg.evaluate("() => ({ v: document.querySelector('.cv-input').value, focus: document.activeElement?.className, writes: window.__CHAT.writes.length, dis: document.querySelector('.cv-send').disabled })")
        check(st == {"v": "이번 주 주보 PDF 정리해 줘", "focus": "cv-input", "writes": 0, "dis": False}, f"누름 → 입력칸 = 예시 · 포커스 · 보낸 말 0 · 보내기 켜짐 {st}")
        pg.fill(".cv-input", "쓰던 말")
        pg.click(".cv-ex-btn >> nth=0")
        pg.clock.run_for(100)
        check(pg.evaluate("() => document.querySelector('.cv-input').value") == "쓰던 말", "쓰던 글이 있으면 그대로(예시 무시)")
        pg.screenshot(path=str(OUT / "b-empty-1280.png"))

        print("== C V2 상단바 · D V3 머리줄 · I 글자 18px")
        bar = lambda: pg.evaluate("() => getComputedStyle(document.getElementById('topbar')).backgroundColor")  # noqa: E731
        check(bar() == "rgb(255, 255, 255)" and pg.evaluate("() => document.body.classList.contains('view-chat')"), f"밝은 대화 화면 상단바 = --cv-bg(흰) {bar()}")
        hd = pg.evaluate("""() => { const kids = [...document.querySelector('.cv-head').children].filter((e) => e.getBoundingClientRect().width > 0);
          return { same: kids.filter((e) => { const cs = getComputedStyle(e); return cs.fontSize === '18px' && cs.fontWeight === '400'; }).map((e) => e.className),
            mins: ['confirms', 'lastSendStep', 'masterHealth', 'errors'].map((k) => !!document.querySelector(`#view-host [data-min=${k}]`)), line: getComputedStyle(document.querySelector('.cv-head')).borderBottomWidth }; }""")
        check(len(hd["same"]) <= 3 and all(hd["mins"]) and hd["line"] == "0px", f"머리 18px/400 동률 ≤ 3 · data-min 4칸 · 아래 선 0 {hd}")
        small = pg.evaluate("""() => { const out = []; for (const e of document.querySelectorAll('.cv-wrap *')) { if (![...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
          if (!e.checkVisibility()) continue; const f = parseFloat(getComputedStyle(e).fontSize); if (f < 18) out.push([e.className, f]); } return out; }""")
        check(small == [], f"대화 화면 글자 18px 미만 0 {small}")
        for w in (800, 1024, 1280):
            pg.set_viewport_size({"width": w, "height": 800})
            pg.clock.run_for(100)
            ov = pg.evaluate("() => { const t = document.getElementById('topbar'); return t.scrollWidth - t.clientWidth; }")
            check(ov <= 0, f"[{w}] 상단바 넘침 0 ({ov})")
        pg.screenshot(path=str(OUT / "c-topbar-chat.png"))
        pg.click("#view-switch button[data-view=work]")
        pg.clock.run_for(3_300)
        check(bar() == "rgb(22, 27, 34)" and not pg.evaluate("() => document.body.classList.contains('view-chat')"), f"작업 화면 상단바 = #161b22 {bar()}")
        pg.screenshot(path=str(OUT / "c-topbar-work.png"))
        ctx.close()

        print("== E V5 입력칸")
        ctx, pg = page()
        st = pg.evaluate("() => { const i = document.querySelector('.cv-input'); return { ih: Math.round(i.getBoundingClientRect().height), fh: Math.round(document.querySelector('.cv-form').getBoundingClientRect().height), dis: document.querySelector('.cv-send').disabled, ph: i.placeholder, hint: document.querySelector('.cv-hint')?.textContent, sendName: document.querySelector('.cv-send').getAttribute('aria-label') }; }")
        check(st["ih"] <= 31 and st["fh"] <= 110 and st["dis"] is True and st["ph"] == "마스터에게 보낼 말" and st["hint"] == "Enter 보내기 · Shift+Enter 줄바꿈" and st["sendName"] == "보내기", f"빈 칸 = 한 줄 · 카드 ≤ 110px · 보내기 꺼짐 · 안내 아래 줄 {st}")
        pg.fill(".cv-input", "\n".join(f"{k}줄" for k in range(1, 10)))
        pg.clock.run_for(100)
        g = pg.evaluate("() => { const i = document.querySelector('.cv-input'); const lh = parseFloat(getComputedStyle(i).lineHeight); return { h: i.clientHeight, sh: i.scrollHeight, lh }; }")
        check(abs(g["h"] - 8 * g["lh"]) <= 2 and g["sh"] > g["h"], f"9줄 = 8줄 높이({8 * g['lh']}) + 칸 안 스크롤 {g}")
        pg.evaluate("() => { const i = document.querySelector('.cv-input'); i.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', isComposing: true, bubbles: true, cancelable: true })); }")
        pg.clock.run_for(3_300)
        check(pg.evaluate("() => window.__CHAT.writes.length") == 0, "한글 조합 중 Enter = 쓰기 0(그대로)")
        pg.screenshot(path=str(OUT / "e-input-9lines.png"))

        print("== F V6 새 답 단추")
        pg.fill(".cv-input", "")
        for k in range(14):
            reply(pg, f"f{k}", f"앞선 답 {k}번 — 줄을 채우는 글입니다.\n둘째 줄\n셋째 줄")
        geo = "() => { const l = document.querySelector('.cv-log'); return { top: l.scrollTop, ch: l.clientHeight, sh: l.scrollHeight }; }"
        g0 = pg.evaluate(geo)
        check(g0["sh"] - g0["ch"] - g0["top"] <= 48, f"앞선 답들 = 바닥에 붙어 따라옴 {g0}")
        pg.evaluate("() => { const l = document.querySelector('.cv-log'); l.scrollTop = l.scrollHeight - l.clientHeight - 200; }")
        pg.clock.run_for(100)
        t0 = pg.evaluate(geo)["top"]
        reply(pg, "f-up", "위를 읽는 동안 온 답")
        st = pg.evaluate("() => { const j = document.querySelector('.cv-jump'); return { top: document.querySelector('.cv-log').scrollTop, shown: !j.hidden, text: j.textContent, h: Math.round(j.getBoundingClientRect().height) }; }")
        check(st["top"] == t0 and st["shown"] and st["text"] == "↓ 새 답 1 · 맨 아래로" and st["h"] >= 44, f"① 위 200px + 답 1 → 위치 불변 · 단추 「↓ 새 답 1 · 맨 아래로」 · 44px {t0} {st}")
        pg.screenshot(path=str(OUT / "f-jump.png"))
        pg.click(".cv-jump")
        pg.clock.run_for(100)
        g1 = pg.evaluate(geo)
        check(g1["sh"] - g1["ch"] - g1["top"] <= 1 and pg.evaluate("() => document.querySelector('.cv-jump').hidden"), f"누르면 맨 아래 · 단추 사라짐 {g1}")
        long_lines = max(20, int(g1["ch"] * 1.5 / 30) + 4)
        reply(pg, "f-long", "\n".join(f"긴 답 {k}째 줄" for k in range(long_lines)))
        pos = pg.evaluate("""() => { const l = document.querySelector('.cv-log'); const m = l.querySelector('.cv-master[data-reply-key="f-long"]');
          return { d: Math.round(m.getBoundingClientRect().top - l.getBoundingClientRect().top), mh: Math.round(m.getBoundingClientRect().height), ch: l.clientHeight }; }""")
        check(pos["mh"] >= 1.5 * pos["ch"] - 1 and 0 <= pos["d"] <= 24 and pg.evaluate("() => document.querySelector('.cv-jump').hidden"), f"② 칸 1.5배 답 → 첫 줄이 칸 위 24px 안 · 단추 0 {pos}")
        pg.evaluate("() => { const l = document.querySelector('.cv-log'); l.scrollTop = l.scrollHeight - l.clientHeight - 30; }")
        pg.clock.run_for(100)
        reply(pg, "f-near", "짧은 답")
        g2 = pg.evaluate(geo)
        check(g2["sh"] - g2["ch"] - g2["top"] <= 1 and pg.evaluate("() => document.querySelector('.cv-jump').hidden"), f"③ 바닥 30px(48 안) + 짧은 답 → 따라감 · 단추 0 {g2}")

        print("== G V8 포커스 링")
        pg.click(".cv-guide-btn")
        pg.clock.run_for(100)
        click_ring = pg.evaluate("() => { const e = document.activeElement; return [e.className, e.matches(':focus-visible'), getComputedStyle(e).outlineStyle]; }")
        pg.focus(".cv-input")
        pg.keyboard.press("Shift+Tab")
        pg.clock.run_for(100)
        tab_ring = pg.evaluate("() => { const e = document.activeElement; const cs = getComputedStyle(e); return [e.className, e.matches(':focus-visible'), cs.outlineStyle, cs.outlineWidth, cs.outlineColor]; }")
        check(click_ring[1] is False and click_ring[2] == "none", f"마우스 클릭 = 링 0 {click_ring}")
        check(tab_ring[1] is True and tab_ring[2] == "solid" and tab_ring[3] == "2px", f"Tab 으로 옮김 = 2px 링 {tab_ring}")
        pg.screenshot(path=str(OUT / "g-focus.png"))
        ctx.close()

        print("== H V11 뼈대 지연 등장")
        for reduce in (False, True):
            ctx, pg = page()
            if reduce:
                pg.emulate_media(reduced_motion="reduce")
            sk = pg.evaluate("""() => { const t = document.querySelector('.cvr-tasks'); const s = document.createElement('div'); s.className = 'cvr-skel'; t.append(s);
              const an = s.getAnimations(); const at = (ms) => { an.forEach((a) => { a.pause(); a.currentTime = ms; }); return getComputedStyle(s).opacity; };
              const r = { names: an.map((a) => a.animationName), o100: at(100), o200: at(200), o1000: at(1000) }; s.remove(); return r; }""")
            if not reduce:
                check(sk["o100"] == "0" and sk["o200"] == "0" and float(sk["o1000"]) > 0.3 and "cv-skel-shimmer" in sk["names"], f"100·200ms = 보이지 않음 · 1초 = 보임 · 반짝임 {sk}")
            else:
                check(sk["o100"] == "0" and float(sk["o1000"]) > 0.3 and "cv-skel-shimmer" not in sk["names"], f"움직임 줄이기 = 반짝임 0 · 지연 등장은 그대로 {sk}")
            ctx.close()

        check(errs == [], f"페이지 오류 0 {errs}")
        br.close()
    httpd.shutdown()
    print(f"RESULT {'PASS' if not failures else 'FAIL'} · 실패 {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
