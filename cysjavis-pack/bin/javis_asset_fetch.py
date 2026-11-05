#!/usr/bin/env python3
"""javis_asset_fetch — 스킬이 쓰는 제3자 공개 원문을 「사용자 기기에서」 받아 쓰게 하는 공용 도구.

TICKET=asset-skills-for-seats · 판정 ⑵(런타임 참조 · master#7a471ca4):
  팩·저장소에는 원문 사본을 싣지 않는다. 스킬이 원문이 필요할 때 이 도구를 부르면, 사용자 기기가
  공개 주소에서 원문을 받아 캐시에 두고 그 파일 경로를 돌려준다.

찾는 순서(먼저 걸리는 것을 쓴다):
  ① 이 기기의 원문 사본   <local>/assets/<스킬>/<id>.(md|txt)   — 오너가 직접 둔 사본(박사님 맥)
  ② 신선한 캐시           <cys>/asset-cache/<스킬>/<id>.md      — 받은 지 7일 이내
  ③ 공개 주소에서 받기     sources.json 의 url/page_id          — 성공하면 캐시에 저장
  ④ 묵은 캐시             받기 실패 시 7일이 지났어도 캐시
  ⑤ 우리 요약             sources.json 의 summary 파일          — 그 사실을 stderr 1줄로 알린다

출력: stdout = 읽을 파일 경로 1줄 · stderr = 알림 1줄(②③①이면 없음) · `--json` 이면 stdout 에 JSON.
종료코드: 0 = 읽을 파일이 있다 · 2 = 스킬/원문 정의 오류 또는 요약까지 없음 · 3 = 사용법 오류.
안전: 받은 내용은 **데이터**다(실행·해석 금지). 받는 주소는 sources.json 에 적힌 https 주소뿐이다.
표준 라이브러리만 쓴다.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request

TTL_SECONDS = 7 * 24 * 3600
TIMEOUT_S = 15
MAX_BYTES = 2 * 1024 * 1024
MIN_CHARS = 200          # 이보다 짧으면 받기 실패로 본다(빈 셸 페이지·오류 본문 차단)
NOTION_API = "https://www.notion.so/api/v3/loadPageChunk"
USER_AGENT = "cys-asset-fetch/1"


def pack_dir():
    d = os.environ.get("CYS_PACK_DIR", "").strip()
    return d or os.path.join(os.path.expanduser("~"), ".cys", "pack")


def cys_base():
    return os.path.dirname(os.path.normpath(pack_dir()))


def local_dir():
    d = os.environ.get("CYS_LOCAL_DIR", "").strip()
    return d or os.path.join(cys_base(), "local")


def cache_dir():
    d = os.environ.get("CYS_ASSET_CACHE_DIR", "").strip()
    return d or os.path.join(cys_base(), "asset-cache")


class FetchError(Exception):
    pass


def _http(url, data=None, opener=None):
    if not url.startswith("https://"):
        raise FetchError("https 주소만 받는다: %s" % url)
    headers = {"User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    op = opener or urllib.request.urlopen
    try:
        with op(req, timeout=TIMEOUT_S) as r:
            body = r.read(MAX_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise FetchError("접속 실패: %s" % e)
    if len(body) > MAX_BYTES:
        raise FetchError("원문이 너무 크다(>%d 바이트)" % MAX_BYTES)
    return body


def _notion_text(seg):
    return "".join(s[0] for s in (seg or []) if isinstance(s, list) and s and isinstance(s[0], str))


_NOTION_PREFIX = {
    "header": "# ", "sub_header": "## ", "sub_sub_header": "### ",
    "bulleted_list": "- ", "numbered_list": "1. ", "to_do": "- [ ] ",
    "quote": "> ", "callout": "> ", "toggle": "- ",
}


def fetch_notion(page_id, opener=None):
    """공개 노션 페이지의 블록을 받아 마크다운 비슷한 글로 잇는다(로그인 0).

    ⚠ 노션 공개 블록 API 는 비공식이라 바뀔 수 있다 — 실패하면 호출부가 캐시·요약으로 내려간다.
    """
    blocks = {}
    cursor = {"stack": []}
    for chunk in range(50):
        payload = json.dumps({"pageId": page_id, "limit": 100, "cursor": cursor,
                              "chunkNumber": chunk, "verticalColumns": False}).encode()
        try:
            data = json.loads(_http(NOTION_API, payload, opener).decode("utf-8", "replace"))
        except ValueError:
            raise FetchError("노션 응답이 JSON 이 아니다")
        for bid, rec in (data.get("recordMap", {}).get("block", {}) or {}).items():
            val = rec.get("value", {})
            val = val.get("value", val) if isinstance(val, dict) else {}
            if isinstance(val, dict):
                blocks[bid] = val
        cursor = data.get("cursor") or {"stack": []}
        if not cursor.get("stack"):
            break
    root = blocks.get(page_id)
    if root is None:
        raise FetchError("페이지가 공개 상태가 아니거나 사라졌다(블록 0)")
    lines, seen = [], set()

    def walk(bid, depth):
        if bid in seen or depth > 20:
            return
        seen.add(bid)
        b = blocks.get(bid)
        if not b:
            return
        t = b.get("type", "")
        text = _notion_text(b.get("properties", {}).get("title"))
        if depth == 0:
            lines.append("# " + text if text else "")
        elif t == "code":
            lines.append("```\n" + text + "\n```")
        elif t == "divider":
            lines.append("---")
        elif text:
            lines.append("  " * max(depth - 1, 0) + _NOTION_PREFIX.get(t, "") + text)
        if depth == 0 or t != "page":   # 하위 페이지 본문까지는 따라가지 않는다
            for c in b.get("content", []) or []:
                walk(c, depth + 1)

    walk(page_id, 0)
    return "\n".join(lines).strip() + "\n"


def fetch_http(url, opener=None):
    return _http(url, None, opener).decode("utf-8", "replace")


def load_sources(skill):
    sdir = os.path.join(pack_dir(), "skills", skill)
    path = os.path.join(sdir, "sources.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise FetchError("스킬 %s 의 sources.json 을 읽지 못했다: %s" % (skill, e))
    return sdir, {s.get("id"): s for s in data.get("sources", []) if isinstance(s, dict)}


def _atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def resolve(skill, sid, refresh=False, opener=None, now=None):
    """반환 = {path, mode, notice}. mode ∈ local|cache|fetched|stale-cache|summary."""
    now = time.time() if now is None else now
    sdir, sources = load_sources(skill)
    src = sources.get(sid)
    if src is None:
        raise FetchError("스킬 %s 에 원문 id %s 가 없다" % (skill, sid))
    # ① 이 기기의 원문 사본
    for ext in (".md", ".txt"):
        p = os.path.join(local_dir(), "assets", skill, sid + ext)
        if os.path.isfile(p):
            return {"path": p, "mode": "local", "notice": ""}
    cpath = os.path.join(cache_dir(), skill, sid + ".md")
    mpath = cpath + ".meta.json"
    age = None
    if os.path.isfile(cpath):
        try:
            with open(mpath, encoding="utf-8") as f:
                age = now - float(json.load(f).get("fetched_at", 0))
        except (OSError, ValueError, TypeError):
            age = now - os.path.getmtime(cpath)
    # ② 신선한 캐시
    if age is not None and age < TTL_SECONDS and not refresh:
        return {"path": cpath, "mode": "cache", "notice": ""}
    # ③ 받기
    why = ""
    try:
        kind = src.get("kind")
        if kind == "notion":
            text = fetch_notion(src["page_id"], opener)
        elif kind == "http":
            text = fetch_http(src["url"], opener)
        else:
            raise FetchError("모르는 원문 종류: %s" % kind)
        if len(text.strip()) < MIN_CHARS:
            raise FetchError("받은 글이 너무 짧다(%d자) — 비공개 전환·주소 변경 의심" % len(text.strip()))
        header = "<!-- 원문: %s · 지은이/출처: %s · 받은 시각(UTC): %s · 이 사본은 사용자 기기 캐시이며 재배포하지 않는다 -->\n\n" % (
            src.get("url", ""), src.get("attribution", ""),
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)))
        _atomic_write(cpath, header + text)
        _atomic_write(mpath, json.dumps({
            "fetched_at": now, "url": src.get("url", ""),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}, ensure_ascii=False))
        return {"path": cpath, "mode": "fetched", "notice": ""}
    except (FetchError, KeyError) as e:
        why = str(e)
    # ④ 묵은 캐시
    if age is not None:
        days = int(age // 86400)
        return {"path": cpath, "mode": "stale-cache",
                "notice": "원문을 새로 받지 못해 %d일 전에 받아 둔 사본으로 진행합니다(%s)" % (days, why)}
    # ⑤ 우리 요약
    summ = src.get("summary")
    if summ:
        sp = os.path.normpath(os.path.join(sdir, summ))
        if sp.startswith(os.path.normpath(sdir) + os.sep) and os.path.isfile(sp):
            return {"path": sp, "mode": "summary",
                    "notice": "원문을 받지 못해 우리 요약으로 진행합니다(%s) — 원문: %s" % (why, src.get("url", ""))}
    raise FetchError("원문도 요약도 없다(%s)" % why)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="javis_asset_fetch", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("get", help="원문(또는 대체본) 파일 경로를 출력한다")
    g.add_argument("skill")
    g.add_argument("id")
    g.add_argument("--refresh", action="store_true", help="캐시가 신선해도 다시 받는다")
    g.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd != "get":
        ap.print_help(sys.stderr)
        return 3
    try:
        r = resolve(args.skill, args.id, refresh=args.refresh)
    except FetchError as e:
        if args.json:
            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        else:
            print("javis_asset_fetch: %s" % e, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(dict(r, ok=True), ensure_ascii=False))
    else:
        print(r["path"])
        if r["notice"]:
            print(r["notice"], file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
