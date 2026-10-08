#!/usr/bin/env python3
"""아고라 로비의 틀(frame) 탐색 실측 — 앱 아고라 창의 이동 판정(`about:` 전면 거부)이 사이트를 깨는가 (수동 · 망 사용 · CI 미배선).

배경(TICKET=cysr-119-t4-app 2판 · codex 1R BLOCK 3): 앱의 `on_navigation` 은 맥 WKWebView 에서 **모든 틀**에 URL 만 넘겨 불린다
(wry 0.55.1 `navigation_policy` — 메인/서브 구분 없음). 그래서 `about:blank`·`about:srcdoc` 를 허용하면 top-level 도 그리로
나갈 수 있고, 거부하면 사이트의 숨은 보안 확인 틀(src 없는 iframe)이 깨질 수 있다 — 그 틀이 **탐색을 일으키는지** 잰다.

측정: 실 로비(https://agora.godmeyou.kr/)를 WebKit·Chromium 으로 열어
  ① 모든 틀의 탐색 사건(framenavigated · 메인/서브 · URL)을 기록
  ② 앱 판정과 같은 규칙(https + 호스트 agora.godmeyou.kr + 포트·사용자정보 없음)을 **문서 요청**에 적용해 밖은 abort
  ③ 방 목록(#board) 이 그려지는가 · 페이지 오류 0 인가
  ④ 「틀이 깨진」 상황 재현 = 숨은 틀이 싣는 Cloudflare 확인 스크립트(`/cdn-cgi/challenge-platform/`)를 막은 채 ③ 반복
판정(엔진마다): 메인 틀이 아고라 밖으로 0회 · 두 방식(정상 · 확인 스크립트 막음) 모두 목록이 그려지고 페이지 오류 0 → PASS.
서브 틀의 `about:` 탐색 횟수는 **관측으로만** 싣는다(2026-10-09 실측 = 두 엔진 2회씩 · 앱이 맥에서 이를 거부하면 ④ 의 상황이 된다).
⚠ 한계(정직): about: 는 망 요청이 아니라 헤드리스에서 「거부」 자체는 재현 못 한다 — ④ 는 그 거부의 귀결(확인 스크립트 미실행)을 재현한다.

실행: python3 ui/e2e/agora_frames_probe.py   # exit 0 = 두 엔진 × 두 방식 전부 PASS
"""
import sys
from urllib.parse import urlsplit

HOME = "https://agora.godmeyou.kr/"
HOST = "agora.godmeyou.kr"


def ours(url: str) -> bool:
    u = urlsplit(url)
    return u.scheme == "https" and u.hostname == HOST and u.port is None and not u.username and not u.password


def probe(pw, engine: str, block_cf: bool) -> bool:
    browser = getattr(pw, engine).launch()
    pg = browser.new_page()
    navs: list[tuple[bool, str]] = []
    blocked: list[str] = []
    errs: list[str] = []
    pg.on("framenavigated", lambda f: navs.append((f == pg.main_frame, f.url)))
    pg.on("pageerror", lambda e: errs.append(str(e)[:120]))

    def route(r):
        if block_cf and "/cdn-cgi/challenge-platform/" in r.request.url:
            blocked.append(r.request.url)
            return r.abort()
        if r.request.is_navigation_request() and not ours(r.request.url):
            blocked.append(r.request.url)
            return r.abort()
        return r.continue_()

    pg.route("**/*", route)
    pg.goto(HOME, wait_until="load")
    pg.wait_for_timeout(4000)
    frames = [(f == pg.main_frame, f.url) for f in pg.frames]
    board = pg.evaluate("() => { const b = document.getElementById('board'); return b ? b.children.length : -1; }")
    browser.close()
    sub_about = [u for (main, u) in navs if not main and u.startswith("about:")]
    main_off = [u for (main, u) in navs if main and not ours(u)]
    print(f"■ {engine} · {'확인 스크립트 막음' if block_cf else '정상'}")
    print(f"  탐색 사건 {len(navs)}건: {navs}")
    print(f"  틀 목록: {frames}")
    print(f"  막은 문서 요청: {blocked}")
    print(f"  서브 틀 about: 탐색 = {sub_about} · 메인 틀 밖 탐색 = {main_off}")
    print(f"  #board 자식 = {board} · 페이지 오류 = {errs}")
    ok = not main_off and board > 0 and not errs
    print(f"  판정 = {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> int:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        results = [probe(pw, e, b) for e in ("webkit", "chromium") for b in (False, True)]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
