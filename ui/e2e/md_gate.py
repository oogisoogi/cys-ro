#!/usr/bin/env python3
"""V1 마크다운 게이트 — TICKET=cysr-1119-s6 · DESIGN §6 V1 (CI 배선 = ci-branch.yml ui-check · 1.1.20 #30).

진짜 번들(ui/dist) + 대화 화면 대역(chat_gate CHAT_SHIM) + 가짜 시계. 마스터 답 = 믿지 못할 글(견본 20종 = src/views/md_samples.json).

A 안전: 견본 20종을 마스터 답으로 → .cv-md 안 script·img·a·iframe·svg·style·link·object·embed·video·audio·source·form·input 0 ·
       .cv-md 안 속성 = class 만(href·src·title·style·on* 0) · window.__pwn 없음 · 답이 들어온 뒤 바깥 요청 0(전체 요청 목록 기록)
B 글: 견본마다 그린 글 = 정답 보이는 글(글자 손실 0 · 글자째) · 보이는 마크다운 기호 0(measure.mjs 식 · 코드 안 글 제외)
C 글자: 대화 화면 18px 미만 0(S4 chat_gate 측정 식 그대로 · 코드·울타리·표·목록 번호·주소 포함) · 제목 22px · 코드 고정폭
D 넘침(master#126780e8): 420px 에서 긴 주소 링크 「글 (주소)」·맨 주소·넓은 울타리·넓은 표 → 대화 칸 가로 넘침 0 · 말 오른쪽 끝 ≤ 칸 오른쪽 · 문서 가로 스크롤 0 · 그림 1장
E 긴 답: 64KB 넘는 답 → 앞 서식 + .cv-md-raw 원문(기호 포함) · 글자 손실 0
F 다시 그리기(fix-1119-s6-adv M3): 넓은 울타리를 가로로 300px 밀어 두고 조회 3번(9.5초) → 같은 요소(새로 만들지 않음) · scrollLeft 그대로
(글자 손실 0 = 「입력 − 기호」 가 아니라 정답 글 src/views/md_samples_visible.json 과 글자째 같음 — 정답 = 나무의 보이는 글 · chatmd.test 가 지킴)
R 되돌리기(MD_EXPECT_OFF=1 · chat/md.ts MD_RENDER=false 로 만든 번들 · GATE_DIST): 마스터 말 = cv-text 글 그대로 · pre-wrap · 회색 풍선 80% · .cv-md 0
실행: CHROME_PATH=<chrome-headless-shell> MD_SHOTS=<폴더> cys run -- <playwright python3> ui/e2e/md_gate.py
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

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"
OUT = Path(os.environ.get("MD_SHOTS", "/tmp/md-gate-shots"))
SAMPLES = json.loads((UI / "src/views/md_samples.json").read_text(encoding="utf-8"))
GOLD = json.loads((UI / "src/views/md_samples_visible.json").read_text(encoding="utf-8"))  # (fix M5) 정답 보이는 글(기호를 지우고 견주지 않음)

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


LONG_URL = "https://example.invalid/" + "very-long-path-segment-without-any-break-" * 6 + "?q=" + "x" * 80
WIDE = (
    f"긴 주소 링크: [설명서]({LONG_URL})\n\n맨 주소: {LONG_URL}\n\n"
    + "```\n" + "const wide = '" + "가나다라마바사" * 30 + "';\n```\n\n"
    + "| " + " | ".join(f"칸{i}" for i in range(12)) + " |\n|" + "---|" * 12 + "\n| " + " | ".join("valuewithoutanybreak" * 2 for _ in range(12))  # 끊을 자리(빈칸·하이픈) 없는 영문 = 표가 칸보다 넓어지는 길(한글 칸은 글자 사이 줄바꿈으로 맞춰짐) + " |\n"
)


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{httpd.server_address[1]}"
    url = f"{origin}/index.html"
    shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
    errs: list[str] = []
    with sync_playwright() as p:
        exe = os.environ.get("CHROME_PATH")
        br = p.chromium.launch(executable_path=exe, args=["--use-mock-keychain"]) if exe else p.chromium.launch(args=["--use-mock-keychain"])

        def page(width: int, height: int = 800):
            ctx = br.new_context(viewport={"width": width, "height": height}, color_scheme="light")
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            reqs: list[str] = []
            pg.on("request", lambda r: reqs.append(r.url))
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.goto(url)
            pg.clock.run_for(9_000)
            pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}, {seat(BASE, 2, 'cso')}); }}")
            pg.clock.run_for(6_000)
            pg.click("#view-switch button[data-view=chat]")
            pg.clock.run_for(3_300)
            return ctx, pg, reqs

        def replies(pg, items: list[tuple[str, str]]) -> None:
            pg.evaluate("""(xs) => { const C = window.__CHAT; const ts = new Date(Date.now()).toISOString();
                for (const [u, t] of xs) C.file.push({ uuid: u, parent: null, role: 'assistant', text: t, ts }); C.master.idle_secs = 0; }""", [list(x) for x in items])
            pg.clock.run_for(3_100)
            pg.evaluate("() => { window.__CHAT.master.idle_secs = 999; }")
            pg.clock.run_for(3_100)

        if os.environ.get("MD_EXPECT_OFF") == "1":
            print("== R 되돌리기(MD_RENDER=false 로 만든 번들) = 1.1.18 꼴: cv-text 글 그대로 · 풍선 · .cv-md 0")
            ctx, pg, reqs = page(1280)
            replies(pg, [("off", SAMPLES[11][1])])
            r = pg.evaluate("""() => { const m = document.querySelector('[data-uuid=off]'); const t = m.querySelector('.cv-text'); const cs = getComputedStyle(m);
                return { md: document.querySelectorAll('.cv-md').length, cls: m.className, text: t ? t.textContent : null, ws: t ? getComputedStyle(t).whiteSpace : null, bg: cs.backgroundColor, maxw: cs.maxWidth }; }""")
            check(r["md"] == 0 and r["cls"] == "cv-msg cv-master" and r["text"] == SAMPLES[11][1] and r["ws"] == "pre-wrap" and r["bg"] != "rgba(0, 0, 0, 0)" and r["maxw"] == "80%",
                  f"되돌리기 = 지금 꼴(글 그대로 · pre-wrap · 회색 풍선 80%) {dict((k, v) for k, v in r.items() if k != 'text')}")
            ctx.close()
            br.close()
            httpd.shutdown()
            print("FAIL 0" if not failures else f"FAIL {len(failures)}")
            return 1 if failures else 0

        print("== A 안전 · B 글 · C 글자(1280)")
        ctx, pg, reqs = page(1280)
        n0 = len(reqs)
        replies(pg, [(f"md{i:02d}", s[1]) for i, s in enumerate(SAMPLES)])
        st = pg.evaluate("""() => {
            const mds = [...document.querySelectorAll('.cv-master.cv-mdmsg[data-uuid^="md"]')];
            const bad = 'script,img,a,iframe,frame,svg,math,style,link,meta,base,object,embed,video,audio,source,picture,form,input,button,textarea,select';
            const inMd = [...document.querySelectorAll('.cv-md, .cv-md *')];
            const attrs = new Set(); for (const e of inMd) for (const a of e.attributes) attrs.add(a.name);
            return { n: mds.length, keys: mds.map((m) => m.dataset.uuid), bad: [...document.querySelectorAll('.cv-log ' + bad.split(',').join(', .cv-log '))].map((e) => e.tagName),
              attrs: [...attrs], onAny: inMd.filter((e) => [...e.attributes].some((a) => /^on/i.test(a.name))).length, pwn: typeof window.__pwn,
              texts: mds.map((m) => m.querySelector('.cv-md')?.textContent ?? null) }; }""")
        check(st["n"] == 20 and st["keys"] == [f"md{i:02d}" for i in range(20)], f"견본 20종 = 마스터 답 20 · 풍선 없는 본문 표지 cv-mdmsg ({st['n']})")
        check(st["bad"] == [], f"대화 칸 안 script·img·a·iframe·svg·style·object·form … 0 ({st['bad']})")
        check(st["attrs"] == ["class"] and st["onAny"] == 0, f".cv-md 안 속성 = class 만 · on* 0 ({st['attrs']} · on {st['onAny']})")
        check(st["pwn"] == "undefined" and errs == [], f"스크립트 실행 0(window.__pwn {st['pwn']}) · 쪽 오류 0 {errs}")
        after = reqs[n0:]
        check([u for u in after if not u.startswith(origin)] == [] and after == [], f"답이 들어온 뒤 요청 0(바깥 0 · 그림 불러오기 0) ({after[:5]})")
        loss = [SAMPLES[i][0] for i, t in enumerate(st["texts"]) if t is None or t != GOLD[i]]
        check(len(GOLD) == 20 and loss == [], f"견본 20종 글자 손실 0(그린 글 = 정답 보이는 글 · 글자째) ({loss})")
        sym = pg.evaluate("""() => { let n = 0; const hits = [];
            for (const m of document.querySelectorAll('.cv-md')) { const c = m.cloneNode(true); c.querySelectorAll('code, pre').forEach((x) => x.remove());
              document.body.append(c); const t = c.innerText; c.remove();
              for (const x of t.match(/\\*\\*[^*]+\\*\\*|^#{1,3} |\\|---|`[^`]+`/gm) || []) { n += 1; hits.push(x); } }
            return { n, hits: hits.slice(0, 5) }; }""")
        check(sym["n"] == 0, f"보이는 마크다운 기호 0(measure.mjs 식 · 코드 안 글 제외) ({sym})")
        kinds = pg.evaluate("""() => { const q = (s) => document.querySelectorAll('.cv-md ' + s).length;
            return { h: q('h1') + q('h2') + q('h3'), strong: q('strong'), em: q('em'), code: q(':not(pre) > code'), pre: q('pre'), li: q('li'), table: q('table'), link: q('.cv-md-link'), raw: q('.cv-md-raw') }; }""")
        check(all(kinds[k] > 0 for k in ("h", "strong", "em", "code", "pre", "li", "table", "link")), f"지원 꼴이 실제로 그려짐 {kinds}")
        small = pg.evaluate("""() => { const out = []; let n = 0;
            for (const e of [document.querySelector('.cv'), ...document.querySelectorAll('.cv *')]) {
              if (!e || e.getClientRects().length === 0) continue;
              const own = [...e.childNodes].some((c) => c.nodeType === 3 && c.textContent.trim() !== '') || e.matches('input, textarea, button');
              if (!own) continue; n += 1;
              const px = parseFloat(getComputedStyle(e).fontSize); if (px < 18) out.push(`${e.tagName.toLowerCase()}.${[...e.classList].join('.')} ${px}px`);
            }
            const fs = (s) => [...document.querySelectorAll(s)].map((e) => parseFloat(getComputedStyle(e).fontSize));
            const mono = getComputedStyle(document.querySelector('.cv-md pre')).fontFamily;
            return { n, out, h: [...new Set(fs('.cv-md h1, .cv-md h2, .cv-md h3'))], code: [...new Set(fs('.cv-md code, .cv-md pre, .cv-md th, .cv-md td, .cv-md-n, .cv-md-url'))], mono }; }""")
        check(small["n"] > 50 and small["out"] == [], f"대화 화면 18px 미만 0(글 있는 요소 {small['n']} · 미만 {small['out'][:5]})")
        check(small["h"] == [22] and min(small["code"]) >= 18 and "monospace" in small["mono"], f"제목 22px · 코드·울타리·표·번호·주소 ≥18px · 고정폭 ({small['h']} · {small['code']} · {small['mono'][:40]})")
        pg.evaluate("() => { const l = document.querySelector('.cv-log'); const t = l.querySelector('[data-uuid=md11]'); l.scrollTop = t.offsetTop - l.offsetTop - 8; }")
        pg.clock.run_for(50)
        pg.screenshot(path=str(OUT / "md-1280-mixed.png"))
        ctx.close()

        print("== D 420px 긴 주소·넓은 울타리·넓은 표 = 가로 넘침 0")
        ctx, pg, reqs = page(420, 800)
        replies(pg, [("wide", WIDE)])
        g = pg.evaluate("""() => { const l = document.querySelector('.cv-log'); const m = l.querySelector('[data-uuid=wide]'); const lr = l.getBoundingClientRect(); const mr = m.getBoundingClientRect();
            const pre = m.querySelector('pre'); const tw = m.querySelector('.cv-md-table'); const url = m.querySelector('.cv-md-url');
            return { logSW: l.scrollWidth, logCW: l.clientWidth, docSW: document.documentElement.scrollWidth, vw: innerWidth, mRight: mr.right, lRight: lr.right, mLeft: mr.left, lLeft: lr.left,
              urlText: url?.textContent ?? null, urlRight: url ? Math.max(...[...url.getClientRects()].map((r) => r.right)) : null, urlLines: url ? url.getClientRects().length : 0,
              preScroll: pre ? pre.scrollWidth > pre.clientWidth : null, preRight: pre ? pre.getBoundingClientRect().right : null,
              tableScroll: tw ? tw.scrollWidth > tw.clientWidth : null, tableRight: tw ? tw.getBoundingClientRect().right : null }; }""")
        check(g["urlText"] == f" ({LONG_URL})", f"링크 = 「글 (주소)」 주소 글 그대로 ({(g['urlText'] or '')[:40]}…)")
        check(g["logSW"] <= g["logCW"] and g["docSW"] <= g["vw"], f"대화 칸·문서 가로 넘침 0 (칸 {g['logSW']}/{g['logCW']} · 문서 {g['docSW']}/{g['vw']})")
        check(g["mRight"] <= g["lRight"] + 0.5 and g["urlRight"] <= g["lRight"] + 0.5 and g["urlLines"] >= 2, f"말·긴 주소 오른쪽 끝 ≤ 칸 오른쪽 · 주소는 줄바꿈({g['urlLines']}줄) ({g['mRight']:.1f} · {g['urlRight']:.1f} ≤ {g['lRight']:.1f})")
        # 울타리 = white-space:pre → 그 칸 안 가로 스크롤 · 표 = .cv-msg 의 word-break:break-word 를 물려받아 긴 낱말도 칸 안에서 끊김(맞춤) — 둘 다 칸 밖 넘침 0
        check(g["preScroll"] is True and g["preRight"] <= g["lRight"] + 0.5 and g["tableRight"] <= g["lRight"] + 0.5,
              f"넓은 울타리 = 그 칸 안 가로 스크롤 · 넓은 표 = 칸 안(맞춤 {not g['tableScroll']} · 스크롤 {g['tableScroll']}) · 칸 밖 넘침 0 ({g['preRight']:.1f} · {g['tableRight']:.1f} ≤ {g['lRight']:.1f})")
        pg.evaluate("() => { const l = document.querySelector('.cv-log'); const m = l.querySelector('[data-uuid=wide]'); l.scrollTop = m.offsetTop - l.offsetTop - 8; }")
        pg.clock.run_for(50)
        pg.screenshot(path=str(OUT / "md-420-longurl.png"))

        print("== E 64KB 넘는 답 = 앞 서식 + 뒤 원문")
        big = "**굵게** 줄\n" * 8000
        replies(pg, [("big", big)])
        e = pg.evaluate("""() => { const m = document.querySelector('[data-uuid=big] .cv-md'); const raw = m.querySelector('.cv-md-raw');
            return { raw: raw ? raw.textContent.length : -1, rawHasSym: raw ? raw.textContent.includes('**') : null, strong: m.querySelectorAll('strong').length, total: m.textContent }; }""")
        head_len = len(big) - e["raw"]
        check(e["raw"] > 0 and e["rawHasSym"] and e["strong"] > 1000 and head_len <= 65536 and big[head_len - 1] == "\n", f"앞 64KB 서식(굵게 {e['strong']}) · 뒤 {e['raw']}자 원문(기호 그대로) · 줄 경계")
        check(e["total"] == big[:head_len].replace("**", "")[:-1] + big[head_len:], "긴 답 글자 손실 0(앞 = 굵게 표지만 빠짐 · 뒤 = 원문 글자째)")

        print("== F 조회마다 다시 그리지 않음(M3) = 같은 요소 · 가로 스크롤 자리 그대로")
        pg.evaluate("() => { const p = document.querySelector('[data-uuid=wide] pre'); p.scrollLeft = 300; p.__mark = 1; document.querySelector('[data-uuid=wide] .cv-md').__mark = 1; }")
        f0 = pg.evaluate("() => document.querySelector('[data-uuid=wide] pre').scrollLeft")
        pg.clock.run_for(9_500)
        f = pg.evaluate("""() => { const p = document.querySelector('[data-uuid=wide] pre'); const md = document.querySelector('[data-uuid=wide] .cv-md');
            return { same: p.__mark === 1 && md.__mark === 1, conn: p.isConnected, sl: p.scrollLeft, n: document.querySelectorAll('[data-uuid=wide]').length }; }""")
        check(f0 == 300 and f["same"] and f["conn"] and f["n"] == 1 and f["sl"] == 300, f"조회 3번 뒤 같은 울타리 요소 · scrollLeft {f0} → {f['sl']} ({f})")
        ctx.close()
        br.close()
    httpd.shutdown()
    print(f"그림 = {OUT}")
    print("FAIL 0" if not failures else f"FAIL {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
