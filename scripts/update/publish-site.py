#!/usr/bin/env python3
"""`/update/` 게시기(1.1.8 U3 2판 · 설계 §6-1 · codex 1R #4·#7·#8·#16 · master 결정 ① = /update/* 전용 워커 + R2).

★게시는 master 가 로컬에서만 한다(CI 게시 0 — 결정 ①). 이 도구가 지키는 것:
  · **증표 + 재검증**: 게이트 통과 증표(`<file>.verified.json` · 검증한 바이트 sha)가 지금 파일과 같아야 하고, 게시기도 키링으로
    서명을 **다시 암호 검증**한다(archive = release · revocations = root · envelope = feed 키 · 봉투 증표 = U1 update-verify 만).
  · **불변·단조**: archive = 보관소 색인 최댓값 + 1 인 seq 만(첫 본문 = `--first`) · 같은 바이트면 멱등 · 다른 바이트 = 거부.
    envelope = feed_rev 증가만 · revocations = rev 증가만.
  · **쌍 원자(TOCTOU)**: 내용은 sha256 이름의 불변 객체(`obj/<sha>`)로 먼저 다 올리고, 본문·서명 쌍을 가리키는 **포인터 객체 하나**
    (`ptr/<공개 경로>`)를 마지막에 교체한다 — 클라이언트에게는 쌍이 한 번에 바뀐다. 검사~교체 전체를 OS 잠금(flock) 안에서 하고
    잠금 안에서 다시 읽어 재검사한다(게시자 = master 기기 하나 · 잠금 파일 = `--lock-file`).
  · **라이브 대조**(`--live-check`): 교체 뒤 공개 URL 의 본문·서명 두 파일 sha256 = 포인터 값이어야 성공(아니면 rc 4 · 포인터는
    이미 바뀌었으므로 직전 포인터로 되돌리는 명령을 출력한다).

저장소(같은 배치 · 워커 `update-worker/` 가 R2 를 그대로 읽는다):
  obj/<sha256>                                불변 객체(본문·서명 바이트)
  ptr/update/<c>/<ch>.json                    봉투 포인터 {json, sig, json_sha256, sig_sha256, kind, feed_rev, published_at}
  ptr/update/<c>/releases/<seq>.json          보관소 포인터(한 번 쓰면 바뀌지 않음)
  ptr/update/<c>/releases/_index              보관소 색인 {max_seq}
  ptr/update/revocations.json                 폐기문 포인터
백엔드: `--fs <폴더>`(시험·드라이런) | `--r2 <버킷>`(wrangler r2 object get/put --remote · 비용 = R2 무료 구간 · 버킷 생성 = master).
종료: 0 = 게시(또는 멱등) · 2 = 서식·증표·서명 거부 · 3 = 덮어쓰기·단조 거부 · 4 = 라이브 대조 실패.
"""
import argparse
import fcntl
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_common as uc  # noqa: E402
from store import FsStore, R2Store  # noqa: E402


class Refuse(Exception):
    pass


class LiveFail(Exception):
    pass


def classify(kind, doc):
    if kind == "archive":
        if doc.get("kind") != uc.RELEASE_KIND:
            raise uc.PublishError("보관소 대상이 릴리스 본문이 아니다")
        return uc.archive_path(doc["component"], int(doc["release_seq"])), "release", uc.STAMP_BY_PY
    if kind == "envelope":
        if doc.get("kind") != uc.ENVELOPE_KIND:
            raise uc.PublishError("봉투가 아니다")
        return uc.envelope_path(doc["component"], doc["channel"]), "feed", uc.STAMP_BY_U1
    if kind == "revocations":
        if doc.get("kind") != uc.REVOCATIONS_KIND:
            raise uc.PublishError("폐기문이 아니다")
        return uc.REVOCATIONS_PATH, "root", uc.STAMP_BY_PY
    raise uc.PublishError("종류 %s" % kind)


def plan(store, kind, doc, data, sig):
    """잠금 안에서 부른다. 반환 = (ptr_key, 새 포인터 dict 또는 None(멱등), 옛 포인터 bytes)."""
    rel = classify(kind, doc)[0]
    ptr_key = "ptr" + rel
    old_raw = store.get(ptr_key)
    old = json.loads(old_raw) if old_raw else None
    js, ss = uc.sha256_bytes(data), uc.sha256_bytes(sig)
    if old and old.get("json_sha256") == js and old.get("sig_sha256") == ss:
        return ptr_key, None, old_raw
    if kind == "archive":
        if old:
            raise Refuse("불변 본문 보관소 덮어쓰기 거부: %s 가 이미 있고 바이트가 다르다" % rel)
    elif old:
        field = "feed_rev" if kind == "envelope" else "rev"
        if int(doc[field]) <= int(old.get(field, -1)):
            raise Refuse("%s 단조 위반: 새 %s=%d ≤ 게시본 %d" % (rel, field, int(doc[field]), int(old.get(field, -1))))
    new = {"json": "obj/" + js, "sig": "obj/" + ss, "json_sha256": js, "sig_sha256": ss, "kind": kind,
           "published_at": int(time.time())}
    if kind == "archive":
        new["seq"] = int(doc["release_seq"])
    elif kind == "envelope":
        new["feed_rev"] = int(doc["feed_rev"])
    else:
        new["rev"] = int(doc["rev"])
    return ptr_key, new, old_raw


def archive_index_check(store, doc, first):
    key = "ptr/update/%s/releases/_index" % doc["component"]
    raw = store.get(key)
    top = json.loads(raw)["max_seq"] if raw else None
    seq = int(doc["release_seq"])
    if top is None:
        if not first:
            raise Refuse("보관소 색인이 비었다 — 첫 본문이면 --first 를 명시하라")
    elif seq != top + 1:
        raise Refuse("release_seq %d ≠ 보관소 최댓값 %d + 1 — 역행·건너뜀 거부(게이트 우회 불가)" % (seq, top))
    return key


def live_check(rel, new, base):
    for suffix, want in (("", new["json_sha256"]), (".minisig", new["sig_sha256"])):
        url = base.rstrip("/") + rel + suffix
        got = None
        for _ in range(6):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"Cache-Control": "no-cache"}),
                                            timeout=15) as r:
                    got = uc.sha256_bytes(r.read())
            except Exception:
                got = None
            if got == want:
                break
            time.sleep(5)
        if got != want:
            raise LiveFail("라이브 %s sha256 %s ≠ 게시 %s" % (url, got, want))


def main(argv=None):
    ap = argparse.ArgumentParser(description="/update/ 게시(master 로컬 전용)")
    ap.add_argument("kind", choices=("archive", "envelope", "revocations"))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fs", help="파일 시스템 저장소 루트(시험·드라이런)")
    g.add_argument("--r2", help="R2 버킷 이름(wrangler r2 object --remote)")
    ap.add_argument("--wrangler", default="bunx wrangler", help="wrangler 실행 명령(공백 구분)")
    ap.add_argument("--file", required=True)
    ap.add_argument("--sig", default=None, help="기본 = <file>.minisig")
    ap.add_argument("--keyring", default=os.path.join(uc.REPO_ROOT, "cysjavis-pack", "trusted-keys.json"))
    ap.add_argument("--first", action="store_true", help="보관소 첫 본문(색인 없음)")
    ap.add_argument("--lock-file", default=os.path.expanduser("~/.cache/cys-update-publish.lock"))
    ap.add_argument("--live-check", default=None, help="교체 뒤 공개 URL 대조 기준(예: https://jarvis.godmeyou.kr)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    store = FsStore(a.fs) if a.fs else R2Store(a.r2, a.wrangler.split())
    try:
        data, sig = open(a.file, "rb").read(), open(a.sig or a.file + ".minisig", "rb").read()
        doc = json.loads(data)
        rel, purpose, by = classify(a.kind, doc)
        uc.read_stamp(a.file, data, sig, by=by)
        uc.verify_sig(uc.load_keyring(a.keyring), purpose, doc.get("key_id"), data, sig.decode("utf-8"), uc.trusted_now())
        os.makedirs(os.path.dirname(a.lock_file), exist_ok=True)
        with open(a.lock_file, "a") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)  # 검사~교체 전체가 잠금 안(재검사 포함)
            ptr_key, new, old_raw = plan(store, a.kind, doc, data, sig)  # 잠금 안 재독·재검사
            if new is None:
                print("= %s 이미 같은 바이트로 게시됨(멱등 · 쓰기 0)" % rel)
                return 0
            idx_key = archive_index_check(store, doc, a.first) if a.kind == "archive" else None
            if a.dry_run:
                print("· %s → %s (dry-run · 쓰기 0)" % (rel, ptr_key))
                return 0
            for k, b in ((new["json"], data), (new["sig"], sig)):
                cur = store.get(k)
                if cur is None:
                    store.put(k, b)
                elif cur != b:
                    raise Refuse("불변 객체 %s 가 다른 바이트로 있다(저장소 손상)" % k)
            store.put(ptr_key, (json.dumps(new, sort_keys=True) + "\n").encode())  # ★단일 포인터 교환 = 쌍 원자
            if idx_key:
                store.put(idx_key, (json.dumps({"max_seq": new["seq"]}) + "\n").encode())
    except Refuse as e:
        print("::error::게시 거부(덮어쓰기·단조) — %s" % e, file=sys.stderr)
        return 3
    except (uc.PublishError, OSError, ValueError, KeyError) as e:
        print("::error::게시 거부 — %s" % e, file=sys.stderr)
        return 2
    print("✅ %s 게시 → %s (json %s · sig %s)" % (rel, ptr_key, new["json_sha256"][:12], new["sig_sha256"][:12]))
    if a.live_check:
        try:
            live_check(rel, new, a.live_check)
        except LiveFail as e:
            print("::error::%s — 되돌리기: 직전 포인터 바이트를 %s 에 다시 쓴다(%s)"
                  % (e, ptr_key, "없음 = 첫 게시 · 포인터 삭제" if old_raw is None else uc.sha256_bytes(old_raw)[:12]),
                  file=sys.stderr)
            return 4
        print("✅ 라이브 대조 일치(본문·서명 두 파일)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
