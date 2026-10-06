#!/usr/bin/env python3
"""사이트 `/update/` 게시 준비(1.1.8 U3 · 설계 §6-1 「불변 본문 보관소」 · §4-2 단조) — 사이트 원본 트리에 **놓기만** 한다.

★이 도구는 외부에 아무것도 올리지 않는다. 사이트 원본(ai-jarvis `site/`)에 파일을 놓을 뿐이고, 실제 게시
(커밋·push·`wrangler deploy`)는 master 집행(첫 게시) 또는 refresh-feed.yml 의 게시 스위치가 켜진 CI 다.

세 종류 · 규칙(어기면 rc 3 = 덮어쓰기 거부 · rc 2 = 서식 거부 · 그 자리 파일 무접촉):
  archive      /update/<c>/releases/<seq>.json(.minisig) — **불변**: 이미 있으면 바이트가 같을 때만 통과(멱등) · 다르면 거부.
  envelope     /update/<c>/<channel>.json(.minisig)     — 새 feed_rev > 있는 것의 feed_rev(같고 바이트 같음 = 멱등).
  revocations  /update/revocations.json(.minisig)        — 새 rev > 있는 것의 rev(같고 바이트 같음 = 멱등).
서명 파일(.minisig)은 언제나 본문과 **짝으로** 놓는다(한쪽만 바뀌는 순간 0 — 둘 다 임시 파일 뒤 교체).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_common as uc  # noqa: E402


class Refuse(Exception):
    pass


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def plan(kind, site_dir, data, sig):
    doc = json.loads(data)
    if kind == "archive":
        if doc.get("kind") != uc.RELEASE_KIND:
            raise uc.PublishError("보관소 대상이 릴리스 본문이 아니다")
        rel = uc.archive_path(doc["component"], int(doc["release_seq"]))
    elif kind == "envelope":
        if doc.get("kind") != uc.ENVELOPE_KIND:
            raise uc.PublishError("봉투가 아니다")
        rel = uc.envelope_path(doc["component"], doc["channel"])
    elif kind == "revocations":
        if doc.get("kind") != uc.REVOCATIONS_KIND:
            raise uc.PublishError("폐기문이 아니다")
        rel = uc.REVOCATIONS_PATH
    else:
        raise uc.PublishError("종류 %s" % kind)
    if not uc.url_ok(uc.site_url(rel), ("site",)) or not uc.url_ok(uc.site_url(rel + ".minisig"), ("site",)):
        raise uc.PublishError("게시 경로 규칙 밖(§4-4): %s" % rel)
    uc.sig_key_id(sig.decode("utf-8"))
    dest = os.path.join(site_dir, rel.lstrip("/"))
    if os.path.exists(dest) or os.path.exists(dest + ".minisig"):
        if not (os.path.isfile(dest) and os.path.isfile(dest + ".minisig")):
            raise Refuse("짝이 깨진 기존 파일(본문·서명 중 하나만 있음): %s" % dest)
        old, old_sig = _read(dest), _read(dest + ".minisig")
        if old == data and old_sig == sig:
            return rel, dest, "same"
        if kind == "archive":
            raise Refuse("불변 본문 보관소 덮어쓰기 거부: %s 가 이미 있고 바이트가 다르다" % rel)
        field = "feed_rev" if kind == "envelope" else "rev"
        o, n = int(json.loads(old)[field]), int(doc[field])
        if n <= o:
            raise Refuse("%s 단조 위반: 새 %s=%d ≤ 게시본 %d (%s)" % (rel, field, n, o, rel))
    return rel, dest, "write"


def place(dest, data, sig):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for path, b in ((dest + ".tmp", data), (dest + ".minisig.tmp", sig)):
        with open(path, "wb") as f:
            f.write(b)
            f.flush()
            os.fsync(f.fileno())
    os.replace(dest + ".minisig.tmp", dest + ".minisig")
    os.replace(dest + ".tmp", dest)


def main(argv=None):
    ap = argparse.ArgumentParser(description="사이트 /update/ 게시 준비(놓기만 · 외부 게시 0)")
    ap.add_argument("kind", choices=("archive", "envelope", "revocations"))
    ap.add_argument("--site-dir", required=True, help="사이트 원본 루트(ai-jarvis/site)")
    ap.add_argument("--file", required=True)
    ap.add_argument("--sig", default=None, help="기본 = <file>.minisig")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        data, sig = _read(a.file), _read(a.sig or a.file + ".minisig")
        rel, dest, what = plan(a.kind, a.site_dir, data, sig)
    except Refuse as e:
        print("::error::게시 거부(덮어쓰기·단조) — %s" % e, file=sys.stderr)
        return 3
    except (uc.PublishError, OSError, ValueError, KeyError) as e:
        print("::error::게시 거부(서식) — %s" % e, file=sys.stderr)
        return 2
    if what == "same":
        print("= %s 이미 같은 바이트로 있음(멱등 · 쓰기 0)" % rel)
        return 0
    if a.dry_run:
        print("· %s → %s (dry-run · 쓰기 0)" % (rel, dest))
        return 0
    place(dest, data, sig)
    print("✅ %s 놓음 → %s (sha256 %s)" % (rel, dest, uc.sha256_bytes(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
