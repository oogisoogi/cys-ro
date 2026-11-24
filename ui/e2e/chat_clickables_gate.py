#!/usr/bin/env python3
"""대화 화면 첫 장면 「누를 수 있는 요소」 계수 게이트 — TICKET=cysr-1119-p0-e2e · 1.1.19 DESIGN §2-1 M-18 · PLAN §5 P0-L3 (수동 실행 — CI 미배선).

1.1.18(838f24421)에서 기준값을 먼저 재고, 1.1.19 는 같은 파일 그대로 다시 잰다(CLICKABLES_MAX 로 상한 대조).

■ ★합격선 판정([master#32eac45c] · 2026-11-24 · P0-L3 기준선 = 1.1.18 실측 run-1118)
  · 합격선 = **view-host(대화 화면 안) 셈** — 기준 3 → 1.1.19 ≤ 7 · 도우미 있을 때 ≤ 8.
  · 문서 전체 셈(1.1.18 기준 12)은 함께 기록만 — 상한 없음 · 사람 눈의 가벼움 참고값 · 1.1.19 값이 12 를 넘으면 완료 보고에 이유 1줄.
  · ★(TICKET=cysr-1119-s5) CLICKABLES_MAX = view-host 셈 상한으로 바꿈(판정 집행 · 1.1.19 실행 = CLICKABLES_MAX=7 · 원본 = review/evidence/p0/e2e/ 사본 sha256 424fab9b…).

■ 장면(「첫 장면」 = 빈 대화 · 결과 0 · 도우미 0)
  · 실제 번들(GATE_DIST 또는 ui/dist) + 기존 e2e 대역 = tickrec_gate.SHIM(좌석·데몬 명령) 위에 chat_gate.CHAT_SHIM(대화 화면 명령)을 덧씌움 · 가짜 시계(chat_gate 와 같은 T0).
  · 좌석 = 본부 master(1) · cso(2) 둘뿐(chat_gate A 장면과 같음) — 워커 0 = 맡긴 일 카드 0 = 도우미 0 · 부서 0(= 부서 안내 카드 자동 펼침 0).
  · 빈 localStorage(새 문맥) · 창 1280×800 · 작업 화면으로 뜬 뒤 공통 전환 단추 #view-switch button[data-view=chat] 을 누름.
  · 잰 시각 = 누른 뒤 가짜 시계 +100ms · +3,100ms(3초 고리 1바퀴) · +15,000ms — **세 시각 값이 같아야** 「첫 장면」 값으로 씀(다르면 FAIL · 각 값 출력).
  · 전제 단언(틀리면 FAIL · 계수 안 믿음): 대화 화면 보임 · 작업 화면 숨김 · 대화 말 0(.cv-me·.cv-master 0 · .cv-empty 보임) · 결과 0(결과 카드 0 · data-count 0 · 왼쪽 결과 칸 숨김) ·
    맡긴 일 카드 0(.cvr-tasks .cvr-card 0 · .cvr-help 0 = 도우미 0) · 부서 안내 카드 0 · pageerror 0.

■ 세는 규칙(이 파일이 정본 — 1.1.19 도 이 규칙 그대로)
  1. 후보 = document.querySelectorAll('button, [role=button], a[href], input, textarea')  (DESIGN §2-1 고정 선택자 · 한 요소가 여러 갈래에 맞아도 1번)
  2. 「보이는 것」 = 아래 넷 모두 참:
     ⑴ el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })  (display:none · hidden · visibility:hidden · opacity:0 · 조상 포함)
     ⑵ getBoundingClientRect() 폭 > 0 ∧ 높이 > 0
     ⑶ 그 사각형이 창(0,0)-(1280,800) 과 넓이 > 0 으로 겹침(스크롤해야 보이는 것 = 셈 밖 · 따로 「창 밖」 목록으로 출력)
     ⑷ input 의 type=hidden 은 ⑴에서 이미 빠짐(브라우저가 렌더하지 않음)
  3. disabled 인 것도 센다(보이는 단추는 누를 수 있어 보인다 = 가벼움 지표) — 단 disabled 수를 따로 출력.
  4. 셈 = 문서 전체(대화 화면이 보일 때 함께 보이는 공통 자리·상단 포함) · 덧붙여 자리별 나눔 = view-host(대화 화면 안) / view-switch(공통 전환 단추) / 그 밖(상단 등).
  5. 출력 = 총수 + 요소 목록(tag · class · type · role · 글자 앞 30자 · 자리 · disabled · 사각형) · CLICKABLES_OUT(기본 스크래치) 에 JSON · CLICKABLES_SHOT 이 있으면 1280×800 그림.

■ 계수기 자체 대조(같은 실행 안 · 틀리면 FAIL)
  · 결정론: 같은 장면 새 문맥으로 두 번 = 같은 총수·같은 목록.
  · 음성 대조: 대화 화면 안에 보이는 단추 1개를 끼우면 +1 · display:none 단추 +0 · 창 밖(top 2000px) 단추 +0 · opacity:0 단추 +0 · a(href 없음) +0 · a[href] +1 · [role=button] div +1.

실행: CHROME_PATH=<chrome-headless-shell> [GATE_DIST=<ui/dist>] [CLICKABLES_MAX=<상한>] [CLICKABLES_OUT=<json>] [CLICKABLES_SHOT=<png>] cys run -- <진짜 playwright python3> ui/e2e/chat_clickables_gate.py
  · ⚠ 진짜 playwright 만(patchright 별칭 금지 — 대역 차이로 수치가 달라진 전례 · 1.1.18u-chat HANDOFF).
"""
import http.server
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tickrec_gate import BASE, CWD, SHIM, seat  # noqa: E402  (기존 e2e 대역)
from chat_gate import CHAT_SHIM, T0  # noqa: E402  (대화 화면 명령 대역 · 같은 가짜 시계 기점)

UI = Path(__file__).resolve().parent.parent
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else UI / "dist"
OUT = Path(os.environ.get("CLICKABLES_OUT") or (Path(os.environ.get("TMPDIR", "/tmp")) / "chat-clickables.json"))
SHOT = os.environ.get("CLICKABLES_SHOT")
MAX = int(os.environ["CLICKABLES_MAX"]) if os.environ.get("CLICKABLES_MAX") else None
W, H = 1280, 800
SELECTOR = "button, [role=button], a[href], input, textarea"

failures: list[str] = []


def check(c: bool, m: str) -> None:
    print(("  ok   " if c else "  FAIL ") + m)
    if not c:
        failures.append(m)


COUNT_JS = r"""
([sel, W, H]) => {
  const host = document.getElementById('view-host');
  const sw = document.getElementById('view-switch');
  const rows = [];
  const offscreen = [];
  for (const e of document.querySelectorAll(sel)) {
    if (!e.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const r = e.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0)) continue;
    const ix = Math.min(r.right, W) - Math.max(r.left, 0);
    const iy = Math.min(r.bottom, H) - Math.max(r.top, 0);
    const row = { tag: e.tagName.toLowerCase(), cls: e.className || '', type: e.getAttribute('type'), role: e.getAttribute('role'),
      text: (e.textContent || e.getAttribute('aria-label') || e.getAttribute('placeholder') || '').trim().slice(0, 30),
      where: sw && sw.contains(e) ? 'view-switch' : host && host.contains(e) ? 'view-host' : 'other',
      disabled: !!e.disabled, rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] };
    if (ix > 0 && iy > 0) rows.push(row); else offscreen.push(row);
  }
  return { rows, offscreen };
}
"""

PRE_JS = r"""
() => {
  const host = document.getElementById('view-host');
  const body = document.getElementById('body-row');
  const vis = (q) => { const e = document.querySelector(q); return !!e && e.checkVisibility({ checkVisibilityCSS: true }); };
  return {
    chatShown: !!host && host.hidden === false,
    workHidden: !!body && getComputedStyle(body).display === 'none',
    msgs: document.querySelectorAll('.cv-me, .cv-master').length,
    emptyShown: vis('.cv-empty'),
    resultsCount: document.querySelector('.cv-results')?.dataset.count ?? null,
    resultItems: document.querySelectorAll('.cv-results .cvr-list > *, .cvr-logrow').length,
    railResultsShown: vis('.cvr-results'),
    taskCards: document.querySelectorAll('.cvr-tasks .cvr-card').length,
    helperLines: document.querySelectorAll('.cvr-help').length,
    deptCards: document.querySelectorAll('.cvr-dept').length,
    guideCards: document.querySelectorAll('.cv-guide').length,
    railEmpty: vis('.cvr-tasks .cvr-empty'),
  };
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright
    import playwright as _pw  # noqa: F401
    try:
        import importlib.metadata as md
        pwv = md.version("playwright")
    except Exception:  # pragma: no cover
        pwv = "?"
    print(f"playwright {pwv} · dist {DIST} · 창 {W}×{H}")

    h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
    shim = SHIM.replace("__BASE__", BASE).replace("__CWD__", CWD)
    report: dict = {"playwright": pwv, "dist": str(DIST), "viewport": [W, H], "selector": SELECTOR}

    with sync_playwright() as p:
        exe = os.environ.get("CHROME_PATH")
        br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        report["browser"] = br.version

        def scene():
            ctx = br.new_context(viewport={"width": W, "height": H})
            ctx.clock.install(time=T0)
            ctx.clock.pause_at(datetime(2026, 11, 17, 10, 0, 1, tzinfo=timezone.utc))
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(shim)
            pg.add_init_script(CHAT_SHIM)
            pg.goto(url)
            pg.clock.run_for(9_000)
            pg.evaluate(f"() => {{ window.__SEATS.push({seat(BASE, 1, 'master')}, {seat(BASE, 2, 'cso')}); }}")
            pg.clock.run_for(15_000)
            pg.click("#view-switch button[data-view=chat]")
            snaps = []
            for step in (100, 3_000, 11_900):  # 누른 뒤 +100 · +3,100 · +15,000 ms
                pg.clock.run_for(step)
                snaps.append(pg.evaluate(COUNT_JS, [SELECTOR, W, H]))
            pre = pg.evaluate(PRE_JS)
            return ctx, pg, errs, snaps, pre

        print("== 1 첫 장면 계수(1차)")
        ctx, pg, errs, snaps, pre = scene()
        print(f"  전제 {json.dumps(pre, ensure_ascii=False)}")
        check(pre["chatShown"] and pre["workHidden"], f"대화 화면 보임 · 작업 화면 숨김 ({pre['chatShown']} · {pre['workHidden']})")
        check(pre["msgs"] == 0 and pre["emptyShown"], f"빈 대화(말 0 · 빈 안내 보임) ({pre['msgs']} · {pre['emptyShown']})")
        check(pre["resultsCount"] in ("0", None) and pre["resultItems"] == 0 and not pre["railResultsShown"], f"결과 0(결과 카드 0 · 왼쪽 결과 칸 숨김) ({pre['resultsCount']} · {pre['resultItems']} · {pre['railResultsShown']})")
        check(pre["taskCards"] == 0 and pre["helperLines"] == 0 and pre["railEmpty"], f"도우미 0(맡긴 일 카드 0 · 도우미 줄 0 · 빈 안내 보임) ({pre['taskCards']} · {pre['helperLines']} · {pre['railEmpty']})")
        check(pre["deptCards"] == 0 and pre["guideCards"] == 0, f"부서 0 · 부서 안내 카드 0 ({pre['deptCards']} · {pre['guideCards']})")
        check(not errs, f"pageerror 0 {errs}")
        counts = [len(s["rows"]) for s in snaps]
        check(len(set(json.dumps(s, sort_keys=True, ensure_ascii=False) for s in snaps)) == 1, f"누른 뒤 +100 · +3,100 · +15,000ms 목록 같음 (수 {counts})")
        first = snaps[-1]
        rows = first["rows"]
        n = len(rows)
        by = {k: sum(1 for r in rows if r["where"] == k) for k in ("view-host", "view-switch", "other")}
        dis = sum(1 for r in rows if r["disabled"])
        print(f"  ★ 누를 수 있는 요소(창 안·보임) = {n}  · 자리별 {by} · disabled {dis} · 창 밖 {len(first['offscreen'])}")
        for i, r in enumerate(rows, 1):
            print(f"    {i:2d}. {r['where']:<11} <{r['tag']} class={r['cls']!r} type={r['type']} role={r['role']}> {r['text']!r} dis={r['disabled']} rect={r['rect']}")
        for r in first["offscreen"]:
            print(f"    (창 밖) {r['where']} <{r['tag']} class={r['cls']!r}> {r['text']!r} rect={r['rect']}")
        if SHOT:
            pg.screenshot(path=SHOT)
            print(f"  그림 {SHOT}")
        report.update({"precondition": pre, "count": n, "by_region": by, "disabled": dis, "snap_counts": counts, "rows": rows, "offscreen": first["offscreen"], "pageerrors": errs})

        print("== 2 계수기 음성 대조(같은 장면에 끼움)")
        probes = [
            ("보이는 button", "const b=document.createElement('button');b.textContent='probe';host.prepend(b);", 1),
            ("display:none button", "const b=document.createElement('button');b.style.display='none';host.prepend(b);", 0),
            ("창 밖 button(top 2000)", "const b=document.createElement('button');b.style.cssText='position:fixed;top:2000px;left:10px';document.body.append(b);", 0),
            ("opacity:0 button", "const b=document.createElement('button');b.textContent='o';b.style.opacity='0';host.prepend(b);", 0),
            ("href 없는 a", "const a=document.createElement('a');a.textContent='a';host.prepend(a);", 0),
            ("a[href]", "const a=document.createElement('a');a.href='#x';a.textContent='a';host.prepend(a);", 1),
            ("[role=button] div", "const d=document.createElement('div');d.setAttribute('role','button');d.textContent='d';host.prepend(d);", 1),
        ]
        neg = []
        for name, js, want in probes:
            before = len(pg.evaluate(COUNT_JS, [SELECTOR, W, H])["rows"])
            pg.evaluate("() => { const host=document.querySelector('#view-host .cv'); " + js + " }")
            after = len(pg.evaluate(COUNT_JS, [SELECTOR, W, H])["rows"])
            check(after - before == want, f"{name} → +{after - before} (기대 +{want})")
            neg.append([name, after - before, want])
        report["negative_controls"] = neg
        ctx.close()

        print("== 3 결정론(새 문맥 2차)")
        ctx2, _pg2, errs2, snaps2, _pre2 = scene()
        same = json.dumps(snaps2[-1], sort_keys=True, ensure_ascii=False) == json.dumps(first, sort_keys=True, ensure_ascii=False)
        check(same and not errs2, f"2차 = 1차 (수 {len(snaps2[-1]['rows'])} · pageerror {errs2})")
        report["determinism_second_count"] = len(snaps2[-1]["rows"])
        ctx2.close()
        br.close()
    httpd.shutdown()

    if MAX is not None:  # (TICKET=cysr-1119-s5 · 판정 [master#32eac45c] 집행) 상한 = view-host 셈(문서 전체는 기록만)
        vh = (report.get("by_region") or {}).get("view-host")
        check(vh is not None and vh <= MAX, f"상한 대조 view-host {vh} ≤ {MAX} (문서 전체 {report['count']} = 기록만)")
        report["max"] = MAX
        report["max_applies_to"] = "view-host"
    report["failures"] = failures
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"  기록 {OUT}")
    print(("PASS" if not failures else f"FAIL {len(failures)}") + f" · 대화 화면 첫 장면 누를 것 = {report.get('count')}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
