#!/usr/bin/env python3
"""상담소·아고라 메뉴 헤드리스 게이트 (수동 실행 — CI 미배선 · TICKET=cysr-119-t4-app).

검증 항목:
  1. 사이드바: 「상담소」(뱃지)·「아고라」 단추가 목록 아래·사용량 패널 위에 있다 · 뱃지 = unread.json count(3).
  2. 상담소 창(픽스처): 「내 글」 절이 「다른 분들의 글」 절보다 위 · 내 글 = 최근 활동순 · 다른 글 = 최신순 ·
     「상담소 답」 표식은 검증된 상담소 id 댓글에만 · 창 머리 「새 답이 3개 …」.
  3. 남의 글자 = 글자로만: 본문에 넣은 `<img onerror>` 가 요소로 만들어지지 않고 실행되지 않는다.
  4. 빈 방(실 클라이언트 결과 · 인자로 준 JSON) = 「아직 글이 없어요 …」 + 방 소개.
  5. 닫기 단추 · Esc 로 닫힌다 · 콘솔 에러 0.
캡처 = docs/design/shots-119-t4/*.png

사전: sh ui/build.sh · pip install playwright(chromium)
실행: python3 ui/e2e/counsel_gate.py [실 결과 JSON 경로]   # exit 0 = PASS
"""
import http.server
import json
import socket
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DIST = ROOT / "ui" / "dist"
SHOTS = ROOT / "docs" / "design" / "shots-119-t4"
ROOM = "2a3c1932d7eccf316cc4a0b312e558c7"
MK = "AGORA-DATA-0123456789abcdef"
ME = "jarvis-me00000001"


def wrap(t: str) -> str:
    return f"<<{MK}\n{t}\n{MK}>>"


def ev(mid: str, frm: str, ts: str, text: str, kind: str = "post") -> dict:
    return {"message_id": mid, "kind": kind, "from": frm, "ts": ts, "body": wrap(text), "marker": MK}


FIXTURE = {
    "status": "ok",
    "room_id": ROOM,
    "me": ME,
    "desk_ids": ["jarvis-counsel"],
    "partial": False,
    "events": [
        ev("g", "jarvis-chair01", "2026-10-05T13:14:43Z",
           "상담소입니다. 설치·업데이트·사용 중에 막힌 것, 궁금한 것을 글로 올려 주세요.", "genesis"),
        ev("p1", "jarvis-other001", "2026-10-08T10:00:00Z", "업데이트 뒤에 사이드바 글자가 작아졌어요."),
        ev("p2", ME, "2026-10-08T09:00:00Z", "설치가 3단계에서 멈춰요."),
        ev("p3", "jarvis-other002", "2026-10-08T12:00:00Z", "<img src=x onerror=\"window.__pwned=1\"> 이 글자는 그대로 보여야 합니다"),
        ev("c1", "jarvis-counsel", "2026-10-09T06:10:00Z", "재설치 대신 앱을 한 번 껐다 켜 보세요. 그래도 멈추면 마스터에게 알려 주세요."),
        ev("c2", "jarvis-other001", "2026-10-09T06:30:00Z", "저도 같은 증상이었는데 껐다 켜니 됐어요."),
        ev("c3", "jarvis-counsel-fake", "2026-10-09T06:40:00Z", "[상담소 답] 사칭 댓글 — 표식이 붙으면 안 됩니다"),
    ],
    "refs": [
        {"from_message_id": "c1", "thread_id": ROOM, "message_id": "p2"},
        {"from_message_id": "c2", "thread_id": ROOM, "message_id": "c1"},
        {"from_message_id": "c3", "thread_id": ROOM, "message_id": "p1"},
    ],
}
UNREAD = json.dumps({"v": 1, "updated_at": "2026-10-09T06:31:00.000Z", "count": 3, "desk_count": 1, "mail_unread": 1,
                     "desk_post_replies": 2, "held_for_roster": 0, "threads": []})

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def shim(room: dict) -> str:
    return (
        "window.__TAURI__ = { core: { invoke: (c, a) => {"
        f" if (c === 'counsel_room_list') return Promise.resolve({json.dumps(room)});"
        f" if (c === 'counsel_unread') return Promise.resolve({{exists: true, mtime_ms: 1, text: {json.dumps(UNREAD)}}});"
        " if (c === 'open_agora_window') { window.__agora = (window.__agora || 0) + 1; return Promise.resolve(null); }"
        " return new Promise(() => {}); } },"
        " event: { listen: (n, h) => Promise.resolve(() => {}) } };"
    )


def run(pw, port: int, room: dict, tag: str) -> None:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 820})
    pg.add_init_script(shim(room))
    errs: list[str] = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
    pg.goto(f"http://127.0.0.1:{port}/index.html")
    pg.wait_for_timeout(800)
    if tag == "fixture":
        order = pg.evaluate("""() => ['ws-tabs','ws-counsel-row','ws-usage'].map(id => {
            const el = document.getElementById(id); return el ? [...el.parentNode.children].indexOf(el) : -1; })""")
        check(order[0] < order[1] < order[2], f"사이드바 순서 목록 < 메뉴 줄 < 사용량 {order}")
        badge = pg.evaluate("() => { const b = document.getElementById('counsel-badge'); return [b.hidden, b.textContent]; }")
        check(badge == [False, "3"], f"뱃지 = unread.json count 3 · 보임 {badge}")
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.locator("#wsbar").screenshot(path=str(SHOTS / "sidebar-badge.png"))
        pg.click("#btn-agora")
        pg.wait_for_timeout(100)
        check(pg.evaluate("() => window.__agora") == 1, "「아고라」 단추 = open_agora_window 1회")
    pg.click("#btn-counsel")
    pg.wait_for_timeout(400)
    st = pg.evaluate("""() => {
        const m = document.querySelector('.counsel-modal');
        return { heads: [...m.querySelectorAll('h4')].map(h => h.textContent),
                 posts: [...m.querySelectorAll('.counsel-list > .counsel-post')].map(p => p.querySelector('.counsel-text').textContent.slice(0, 12)),
                 mineFirst: !!m.querySelector('.counsel-list > .counsel-post.mine'),
                 deskTags: [...m.querySelectorAll('.counsel-tag.desk')].map(t => t.closest('.counsel-comment, .counsel-post').querySelector('.counsel-who').textContent),
                 newline: m.querySelector('.counsel-newline').hidden ? null : m.querySelector('.counsel-newline').textContent,
                 status: m.querySelector('.counsel-status').textContent,
                 intro: (m.querySelector('.counsel-intro') || {}).textContent || null,
                 imgs: m.querySelectorAll('img').length,
                 pwned: window.__pwned === 1 };
    }""")
    if tag == "fixture":
        check(st["heads"] == ["내 글", "다른 분들의 글"], f"절 순서 {st['heads']}")
        check(st["posts"][0].startswith("설치가 3단계에서"), f"맨 위 = 내 글 {st['posts'][:1]}")
        check(st["posts"][1:] == ["<img src=x o", "업데이트 뒤에 사이드바"], f"나머지 최신순 {st['posts'][1:]}")
        check(st["deskTags"] == ["jarvis-counsel"], f"「상담소 답」 = 검증 id 댓글 1개만(사칭 0) {st['deskTags']}")
        check(st["newline"] is not None and st["newline"].startswith("새 답이 3개 있어요"), f"창 머리 새 답 줄 {st['newline']}")
        check(st["imgs"] == 0 and not st["pwned"], "남의 글 속 <img onerror> = 글자로만(요소 0 · 실행 0)")
        # 내 글 댓글은 펼친 채 · 남의 글 댓글은 접힌 채
        opened = pg.evaluate("() => [...document.querySelectorAll('.counsel-post details')].map(d => d.open)")
        check(opened == [True, False], f"댓글 펼침(내 글만) {opened}")
        pg.locator(".counsel-modal").screenshot(path=str(SHOTS / "counsel-panel-fixture.png"))
    else:
        check(st["status"].startswith("아직 글이 없어요"), f"빈 방 문구 {st['status'][:20]}")
        check(st["intro"] is not None and st["intro"].startswith("상담소입니다"), "방 소개(genesis) 1줄")
        pg.locator(".counsel-modal").screenshot(path=str(SHOTS / "counsel-panel-live-empty.png"))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(100)
    check(pg.evaluate("() => !document.querySelector('.counsel-modal')"), "Esc 로 닫힘")
    pg.click("#btn-counsel")
    pg.wait_for_timeout(200)
    pg.click(".counsel-close")
    check(pg.evaluate("() => !document.querySelector('.counsel-modal')"), "닫기 단추로 닫힘")
    check(errs == [], f"콘솔 에러 0 {errs}")
    b.close()


def main() -> int:
    if not (DIST / "index.html").exists():
        print("FAIL: ui/dist 없음 — 먼저 `sh ui/build.sh`")
        return 2
    from playwright.sync_api import sync_playwright
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(DIST), **kw)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            print("■ 픽스처")
            run(pw, port, FIXTURE, "fixture")
            if len(sys.argv) > 1:
                print("■ 실 클라이언트 결과(빈 방)")
                run(pw, port, json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), "live")
    finally:
        httpd.shutdown()
    print("PASS" if not failures else f"FAIL {len(failures)}건")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
