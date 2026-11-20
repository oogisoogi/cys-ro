#!/usr/bin/env python3
"""노트북(NotebookLM · 제미나이 노트북) 소스를 파일 묶음(pack)으로 뽑는다.

하는 일
  1. `nlm source list <노트북> --json` 으로 소스 목록을 받는다.
  2. 처리 실패(status 3) · 처리 중 소스는 뽑지 않고 manifest 의 「제외」 칸에 이유와 함께 적는다.
  3. 나머지는 `nlm source content <소스> --json` 으로 원문 글(모델 가공 없음)을 받는다.
  4. 글자 수가 --min-chars 미만이면 「빈 소스 후보」로 제외 칸에 적는다(지우지 않는다 — 노트북은 그대로).
  5. 출력 폴더에 pack.md(전체 한 파일) · sources/NNN.md(소스별) · manifest.json(목록·글자 수·sha256) 을 쓴다.
  6. pack.md 가 --part-chars 를 넘으면 pack-01.md, pack-02.md … 로 나눈다(받는 AI 의 한도 대비).

노트북 여러 개를 한 번에 넘기면 하나의 묶음으로 합친다(노트북 소스 상한을 넘는 조사용).
노트북·소스를 지우거나 바꾸는 호출은 하지 않는다(읽기 전용).
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import os  # NOWIN(윈도 콘솔 창 숨김) 정의용

# 윈도에서 출력 캡처 자식의 콘솔 창을 숨긴다(test_nowin_captured_spawns 규칙)
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

STATUS_READY = 2
STATUS_ERROR = 3
# 글자 수는 넘지만 본문이 없는 페이지(쿠키 동의문·로그인 벽 등) 의심 낱말 — 빼지 않고 manifest 에 「의심」으로만 표시
BOILER = ("cookie", "consent", "javascript", "sign in", "log in", "subscribe", "access denied",
          "쿠키", "로그인", "구독하", "접근이 거부", "자바스크립트")


def run_nlm(nlm, args, profile):
    cmd = [nlm, *args, "--json"]
    if profile:
        cmd += ["--profile", profile]
    p = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, **NOWIN)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} 실패(rc={p.returncode}): {(p.stderr.strip() or p.stdout.strip())[:300]}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{' '.join(cmd)} 출력이 JSON 이 아님: {e}: {p.stdout[:200]!r}")


def unwrap(obj, key):
    """nlm 판에 따라 바로 목록/객체이거나 {key: ...} 로 싸여 올 수 있다."""
    if isinstance(obj, dict) and key in obj and not ("content" in obj and key == "content"):
        return obj[key]
    return obj


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notebooks", nargs="+", help="노트북 ID 또는 nlm 별칭(여러 개 가능)")
    ap.add_argument("--out", required=True, help="출력 폴더(없으면 만든다 · 비어 있지 않으면 멈춘다)")
    ap.add_argument("--min-chars", type=int, default=500, help="이보다 짧으면 빈 소스 후보로 제외(기본 500)")
    ap.add_argument("--part-chars", type=int, default=400_000, help="pack 한 파일 최대 글자 수(기본 40만)")
    ap.add_argument("--nlm", default="nlm", help="nlm 실행 파일(기본 PATH 의 nlm)")
    ap.add_argument("--profile", default=None, help="nlm 프로필")
    ap.add_argument("--url-map", default=None, help="1단계 yt-dlp 목록(id|길이|조회수|제목) — nlm 이 유튜브 주소를 비워 줄 때 제목으로 주소를 채운다")
    a = ap.parse_args()

    out = Path(a.out).expanduser()
    if out.exists() and any(out.iterdir()):
        sys.exit(f"멈춤: 출력 폴더가 비어 있지 않다 — {out}")
    a.notebooks = list(dict.fromkeys(a.notebooks))  # 같은 노트북 두 번 = 한 번
    urlmap = {}
    if a.url_map:
        for line in Path(a.url_map).expanduser().read_text(encoding="utf-8").splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4 and parts[0].strip():
                urlmap[parts[3].strip()] = f"https://youtu.be/{parts[0].strip()}"

    kept, excluded, seen = [], [], set()
    n = 0
    made_dir = False
    for nb in a.notebooks:
        sources = unwrap(run_nlm(a.nlm, ["source", "list", nb], a.profile), "sources")
        if not made_dir:  # 첫 목록 조회가 성공한 뒤에만 폴더를 만든다(실패 뒤 빈 폴더가 남아 재실행을 막지 않게)
            (out / "sources").mkdir(parents=True, exist_ok=True)
            made_dir = True
        for s in sources:
            sid = s.get("id", "")
            if sid and sid in seen:
                continue
            seen.add(sid)
            title = s.get("title", "")
            base = {"notebook": nb, "id": sid, "title": title,
                    "type": s.get("type", ""), "url": s.get("url") or urlmap.get(title.strip(), "")}
            st = s.get("status")
            if st == STATUS_ERROR:
                excluded.append({**base, "reason": "처리 실패(status 3)"})
                continue
            if st not in (None, STATUS_READY):
                excluded.append({**base, "reason": f"아직 처리 중(status {st})"})
                continue
            c = unwrap(run_nlm(a.nlm, ["source", "content", base["id"]], a.profile), "content")
            text = c.get("content", "") if isinstance(c, dict) else str(c)
            if not base["url"] and isinstance(c, dict) and c.get("url"):
                base["url"] = c["url"]
            if len(text) < a.min_chars:
                excluded.append({**base, "reason": f"빈 소스 후보({len(text)}자 < {a.min_chars})", "chars": len(text)})
                continue
            low = text.lower()
            hits = [w for w in BOILER if w in low]
            suspect = bool(hits) and len(text) < a.min_chars * 6
            n += 1
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            head = (f"## [{n:03d}] {base['title']}\n\n- 출처: {base['url'] or '(주소 없음)'}\n"
                    f"- 종류: {base['type']} · 노트북: {nb} · 소스 ID: {base['id']}\n"
                    f"- 글자 수: {len(text)} · sha256: {sha[:16]}\n\n")
            (out / "sources" / f"{n:03d}.md").write_text(head + text + "\n", encoding="utf-8")
            kept.append({**base, "no": n, "chars": len(text), "sha256": sha,
                         "suspect_boilerplate": hits if suspect else [], "block": head + text + "\n\n"})

    # pack 나누기(소스 하나는 쪼개지 않는다)
    parts, cur, size = [], [], 0
    for k in kept:
        if cur and size + len(k["block"]) > a.part_chars:
            parts.append(cur)
            cur, size = [], 0
        cur.append(k)
        size += len(k["block"])
    if cur:
        parts.append(cur)
    names = ["pack.md"] if len(parts) <= 1 else [f"pack-{i:02d}.md" for i in range(1, len(parts) + 1)]
    made = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    for name, part in zip(names, parts):
        top = (f"# 소스 묶음 {name}\n\n- 만든 때: {made} · 노트북: {', '.join(a.notebooks)}\n"
               f"- 이 파일 소스 {len(part)}개 · 전체 {len(kept)}개(제외 {len(excluded)}개 = manifest.json)\n"
               "- 각 소스 머리의 「출처」를 인용 근거로 쓴다. 원문 저작권은 각 출처에 있다(내부 조사용).\n\n")
        (out / name).write_text(top + "".join(k["block"] for k in part), encoding="utf-8")

    manifest = {"made_at": made, "notebooks": a.notebooks, "min_chars": a.min_chars,
                "pack_files": names if kept else [],
                "kept": [{k2: v for k2, v in k.items() if k2 != "block"} for k in kept],
                "excluded": excluded}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"뽑음 {len(kept)} · 제외 {len(excluded)} · 파일 {', '.join(manifest['pack_files']) or '없음'} → {out}")
    for e in excluded:
        print(f"  제외: {e['title'][:40]} — {e['reason']}")
    for k in kept:
        if k["suspect_boilerplate"]:
            print(f"  의심(직접 열어 확인): [{k['no']:03d}] {k['title'][:40]} — {', '.join(k['suspect_boilerplate'])}")
    no_url = sum(1 for k in kept if not k["url"])
    if no_url:
        print(f"  주의: 출처 주소 빈 소스 {no_url}개 — 유튜브면 --url-map <1단계 목록> 을 넘겨라")
    if not kept:
        print("  경고: 뽑힌 소스 0개 — pack 파일 없음", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        sys.exit(f"멈춤: {e}")
