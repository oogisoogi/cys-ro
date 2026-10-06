#!/usr/bin/env python3
"""`/update/` 게시기(1.1.8 U3 3판 · 설계 §6-1 · codex 1R/2R #4·#7·#8·#15·#16·#19 · master 결정 ① = /update/* 전용 워커 + R2).

★게시는 master 가 로컬에서만 한다(CI 게시 0 — 결정 ①). 이 도구가 지키는 것:
  · **직접 검증**(2R #4·#15 — 증표 신뢰 폐지): 통과 증표(`.verified.json`)는 보지 않는다(서명 없는 JSON = 위조 가능). 대신
    게시 직전에 키링으로 서명을 **암호 검증**하고(archive = release · revocations = root · envelope = feed), 봉투는 **U1 검증기를
    직접 다시 돌린다**(`--cys <bin>` 필수 · 저장소에 지금 게시된 폐기문과 함께 · cysr = `--enumerate-installed`) · signed_at =
    신뢰 시각(미래 거부) 그리고 지금 게시본보다 뒤(역행 거부).
  · **불변·단조**: archive = 보관소 최댓값 + 1 인 seq 만(첫 본문 = `--first`) · 같은 바이트면 멱등 · 다른 바이트 = 거부.
    envelope = feed_rev 증가 + 실은 본문·서명 = 보관소 그 seq 의 불변 객체와 바이트 동일(2R #19) · revocations = rev+1 + 후계 규칙(2R #5).
  · **CAS**(2R #8): 내용은 `obj/<sha>` 불변 객체(`If-None-Match: *`) · 공개 경로는 포인터 객체 하나를 `If-Match: <읽은 ETag>` 로
    교체 — 다른 게시자가 그 사이 바꿨으면 거부(rc 3 · 다시 실행 = 처음부터 재검사). 보관소는 포인터와 색인이 **세대 포인터 하나**
    (`ptr/update/<c>/releases/_gen`)라 중단돼도 「멱등인데 색인 없음」 상태가 없다(재실행 = 객체 확인 → 세대 교체).
  · **라이브 대조 + 자동 되돌리기**(2R #16 · `--live-check`): 교체 뒤 공개 URL 의 본문·서명 sha256 이 포인터 값이 아니면 옛 포인터를
    **방금 쓴 ETag 조건으로** 되돌린다(rc 4). 되돌리기 CAS 마저 실패하면(그 사이 누가 또 바꿈) rc 5 + 사람이 칠 명령 1줄
    (`publish-site.py restore …` · 옛 포인터 사본 = `~/.cache/cys-update-rollback/`).
저장소: `--fs <폴더>`(시험·드라이런 · 같은 호스트 flock) | `--r2 <버킷>`(S3 호환 API · env R2_ACCOUNT_ID·R2_ACCESS_KEY_ID·
  R2_SECRET_ACCESS_KEY = master 로컬 · 버킷 생성 = master). 배치 = scripts/update/store.py 머리말.
종료: 0 = 게시(또는 멱등) · 2 = 서식·서명·검증 거부 · 3 = 덮어쓰기·단조·CAS 거부 · 4 = 라이브 불일치(되돌림 완료) ·
      5 = 라이브 불일치 + 되돌리기 실패(비상 · 인쇄된 명령 1줄).
"""
import argparse
import fcntl
import json
import os
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_common as uc  # noqa: E402
from store import CasFail, FsStore, S3Store, gen_key, put_object  # noqa: E402
import u1verify  # noqa: E402

ROLLBACK_DIR = os.path.expanduser("~/.cache/cys-update-rollback")


class Refuse(Exception):
    pass


class LiveFail(Exception):
    pass


def classify(kind, doc):
    if kind == "archive":
        if doc.get("kind") != uc.RELEASE_KIND:
            raise uc.PublishError("보관소 대상이 릴리스 본문이 아니다")
        return uc.archive_path(doc["component"], int(doc["release_seq"])), "release"
    if kind == "envelope":
        if doc.get("kind") != uc.ENVELOPE_KIND:
            raise uc.PublishError("봉투가 아니다")
        return uc.envelope_path(doc["component"], doc["channel"]), "feed"
    if kind == "revocations":
        if doc.get("kind") != uc.REVOCATIONS_KIND:
            raise uc.PublishError("폐기문이 아니다")
        return uc.REVOCATIONS_PATH, "root"
    raise uc.PublishError("종류 %s" % kind)


def _entry(data, sig, extra):
    js, ss = uc.sha256_bytes(data), uc.sha256_bytes(sig)
    return dict({"json": "obj/" + js, "sig": "obj/" + ss, "json_sha256": js, "sig_sha256": ss,
                 "published_at": int(time.time())}, **extra)


def _same(e, data, sig):
    return e and e.get("json_sha256") == uc.sha256_bytes(data) and e.get("sig_sha256") == uc.sha256_bytes(sig)


def _obj(store, key):
    b, _ = store.get(key)
    if b is None:
        raise Refuse("포인터가 가리키는 객체 %s 가 없다(저장소 손상)" % key)
    return b


def plan(store, kind, doc, data, sig, a, now):
    """반환 = (ptr_key, 새 포인터 바이트 또는 None(멱등), 옛 포인터 바이트, 옛 ETag). 읽기만 — 쓰기 0."""
    rel = classify(kind, doc)[0]
    if kind == "archive":
        comp, seq = doc["component"], int(doc["release_seq"])
        key = gen_key(comp)
        raw, etag = store.get(key)
        g = json.loads(raw) if raw else {"max_seq": None, "seqs": {}}
        cur = g["seqs"].get(str(seq))
        if cur:
            if _same(cur, data, sig):
                return key, None, raw, etag
            raise Refuse("불변 본문 보관소 덮어쓰기 거부: %s 가 이미 있고 바이트가 다르다" % rel)
        top = g["max_seq"]
        if top is None:
            if not a.first:
                raise Refuse("보관소가 비었다 — 첫 본문이면 --first 를 명시하라")
        elif seq != top + 1:
            raise Refuse("release_seq %d ≠ 보관소 최댓값 %d + 1 — 역행·건너뜀 거부(게이트 우회 불가)" % (seq, top))
        else:
            prev = json.loads(_obj(store, g["seqs"][str(top)]["json"]))
            uc.check_signed_at(doc.get("signed_at"), now, prev.get("signed_at"), "본문 signed_at")
        g2 = {"max_seq": seq, "seqs": dict(g["seqs"], **{str(seq): _entry(data, sig, {"seq": seq})})}
        return key, (json.dumps(g2, sort_keys=True) + "\n").encode(), raw, etag
    key = "ptr" + rel
    raw, etag = store.get(key)
    old = json.loads(raw) if raw else None
    if _same(old, data, sig):
        return key, None, raw, etag
    field = "feed_rev" if kind == "envelope" else "rev"
    if old:
        if int(doc[field]) <= int(old.get(field, -1)):
            raise Refuse("%s 단조 위반: 새 %s=%d ≤ 게시본 %d" % (rel, field, int(doc[field]), int(old.get(field, -1))))
        prev = json.loads(_obj(store, old["json"]))
        uc.check_signed_at(doc.get("signed_at"), now, prev.get("signed_at"), "%s signed_at" % kind)
        if kind == "revocations":
            if int(doc["rev"]) != int(prev["rev"]) + 1:
                raise Refuse("폐기문 rev %d ≠ 게시본 %d + 1" % (doc["rev"], prev["rev"]))
            uc.check_revocations_successor(prev, doc)
    elif kind == "revocations" and not a.first:
        raise Refuse("게시된 폐기문이 없다 — 첫 폐기문이면 --first 를 명시하라")
    new = _entry(data, sig, {"kind": kind, field: int(doc[field])})
    return key, (json.dumps(new, sort_keys=True) + "\n").encode(), raw, etag


def verify_envelope_now(store, doc, data, sig, a, tmp):
    """봉투: 실은 본문·서명 = 보관소 불변 객체(2R #19) + U1 직접 재검증(2R #4 · 지금 게시된 폐기문과 함께)."""
    import base64
    body_raw, body_sig = base64.b64decode(doc["release"]), base64.b64decode(doc["release_sig"])
    seq = int(json.loads(body_raw)["release_seq"])
    graw, _ = store.get(gen_key(doc["component"]))
    e = (json.loads(graw)["seqs"].get(str(seq)) if graw else None)
    if not e or not _same(e, body_raw, body_sig):
        raise Refuse("봉투에 실은 본문·서명(seq %d)이 보관소 불변 객체와 바이트로 같지 않다(먼저 archive 게시 · 2R #19)" % seq)
    rraw, _ = store.get("ptr" + uc.REVOCATIONS_PATH)
    if not rraw:
        raise Refuse("게시된 폐기문이 없다 — 봉투보다 폐기문을 먼저 게시하라(U1 검증에 필요)")
    rp = json.loads(rraw)
    rev = os.path.join(tmp, "revocations.json")
    open(rev, "wb").write(_obj(store, rp["json"]))
    open(rev + ".minisig", "wb").write(_obj(store, rp["sig"]))
    env = os.path.join(tmp, "envelope.json")
    open(env, "wb").write(data)
    open(env + ".minisig", "wb").write(sig)
    if not a.cys:
        raise uc.PublishError("봉투 게시는 --cys <U1 cys> 가 필수다(U1 직접 재검증 · 증표 신뢰 폐지)")
    try:
        return u1verify.verify_envelope(a.cys, u1verify.args(a.cys, doc["component"], doc["channel"], env, rev),
                                        ["apply", "halt", "not_in_rollout"])
    except (u1verify.GateFail, u1verify.Undetermined) as e:
        raise uc.PublishError("U1 재검증 거부: %s" % e)


def live_check(rel, ptr, base, tries, interval):
    for suffix, want in (("", ptr["json_sha256"]), (".minisig", ptr["sig_sha256"])):
        url = base.rstrip("/") + rel + suffix
        got = None
        for i in range(tries):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"Cache-Control": "no-cache"}),
                                            timeout=15) as r:
                    got = uc.sha256_bytes(r.read())
            except Exception:
                got = None
            if got == want:
                break
            if i + 1 < tries:
                time.sleep(interval)
        if got != want:
            raise LiveFail("라이브 %s sha256 %s ≠ 게시 %s" % (url, got, want))


def _save_rollback(key, old_raw, d):
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "%d-%s" % (int(time.time()), key.replace("/", "_")))
    open(p, "wb").write(old_raw if old_raw is not None else b"")
    if old_raw is None:
        open(p + ".absent", "w").write("직전 포인터 없음(첫 게시) — 되돌리기 = 삭제\n")
    return p


def _store(a):
    return FsStore(a.fs) if a.fs else S3Store(a.r2)


def cmd_restore(a):
    """비상 되돌리기(rc 5 뒤 사람이 1회): 지금 ETag 가 --if-match 일 때만 옛 포인터 바이트로(또는 삭제)."""
    store = _store(a)
    try:
        if os.path.exists(a.from_file + ".absent"):
            store.cas_delete(a.key, a.if_match)
        else:
            store.cas(a.key, open(a.from_file, "rb").read(), a.if_match)
    except CasFail as e:
        print("::error::되돌리기 CAS 실패 — %s(지금 ETag 를 다시 읽고 판단)" % e, file=sys.stderr)
        return 3
    print("✅ %s 되돌림(%s)" % (a.key, a.from_file))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="/update/ 게시(master 로컬 전용)")
    ap.add_argument("kind", choices=("archive", "envelope", "revocations", "restore"))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fs", help="파일 시스템 저장소 루트(시험·드라이런)")
    g.add_argument("--r2", help="R2 버킷 이름(S3 호환 API · env R2_* 자격)")
    ap.add_argument("--file", help="게시할 문서(서명 = <file>.minisig)")
    ap.add_argument("--sig", default=None, help="기본 = <file>.minisig")
    ap.add_argument("--keyring", default=os.path.join(uc.REPO_ROOT, "cysjavis-pack", "trusted-keys.json"))
    ap.add_argument("--cys", default=None, help="U1 cys(update-verify) — envelope 게시 필수")
    ap.add_argument("--first", action="store_true", help="보관소 첫 본문 · 첫 폐기문")
    ap.add_argument("--lock-file", default=os.path.expanduser("~/.cache/cys-update-publish.lock"))
    ap.add_argument("--live-check", default=None, help="교체 뒤 공개 URL 대조 기준(예: https://jarvis.godmeyou.kr)")
    ap.add_argument("--live-tries", type=int, default=6)
    ap.add_argument("--live-interval", type=float, default=5)
    ap.add_argument("--rollback-dir", default=ROLLBACK_DIR, help="교체 전 옛 포인터 사본 자리")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--key", help="restore: 포인터 키")
    ap.add_argument("--from", dest="from_file", help="restore: 옛 포인터 사본(rc 5 가 인쇄한 경로)")
    ap.add_argument("--if-match", help="restore: 지금 ETag")
    a = ap.parse_args(argv)
    if a.kind == "restore":
        if not (a.key and a.from_file and a.if_match):
            ap.error("restore 는 --key --from --if-match 가 필요하다")
        return cmd_restore(a)
    if not a.file:
        ap.error("--file 이 필요하다")
    try:
        store = _store(a)
        data, sig = open(a.file, "rb").read(), open(a.sig or a.file + ".minisig", "rb").read()
        doc = json.loads(data)
        rel, purpose = classify(a.kind, doc)
        now = uc.trusted_now()
        uc.verify_sig(uc.load_keyring(a.keyring), purpose, doc.get("key_id"), data, sig.decode("utf-8"), now)
        uc.check_signed_at(doc.get("signed_at"), now, None, "%s signed_at" % a.kind)
        os.makedirs(os.path.dirname(a.lock_file), exist_ok=True)
        with open(a.lock_file, "a") as lk, tempfile.TemporaryDirectory() as tmp:
            fcntl.flock(lk, fcntl.LOCK_EX)  # 같은 기기의 동시 게시 직렬화(다른 기기와의 경쟁은 CAS 가 막는다)
            if a.kind == "envelope":
                for line in verify_envelope_now(store, doc, data, sig, a, tmp):
                    print("  " + line)
            ptr_key, new, old_raw, old_etag = plan(store, a.kind, doc, data, sig, a, now)
            if new is None:
                print("= %s 이미 같은 바이트로 게시됨(멱등 · 쓰기 0)" % rel)
                return 0
            if a.dry_run:
                print("· %s → %s (dry-run · 쓰기 0)" % (rel, ptr_key))
                return 0
            put_object(store, "obj/" + uc.sha256_bytes(data), data)
            put_object(store, "obj/" + uc.sha256_bytes(sig), sig)
            saved = _save_rollback(ptr_key, old_raw, a.rollback_dir)
            new_etag = store.cas(ptr_key, new, old_etag)  # ★단일 포인터 CAS = 쌍 원자 · 경쟁 = CasFail
    except (Refuse, CasFail) as e:
        print("::error::게시 거부(덮어쓰기·단조·동시 교체) — %s" % e, file=sys.stderr)
        return 3
    except (uc.PublishError, OSError, ValueError, KeyError) as e:
        print("::error::게시 거부 — %s" % e, file=sys.stderr)
        return 2
    ptr = json.loads(new)
    if a.kind == "archive":
        ptr = ptr["seqs"][str(int(doc["release_seq"]))]
    print("✅ %s 게시 → %s (json %s · sig %s)" % (rel, ptr_key, ptr["json_sha256"][:12], ptr["sig_sha256"][:12]))
    if a.live_check:
        try:
            live_check(rel, ptr, a.live_check, a.live_tries, a.live_interval)
        except LiveFail as e:
            try:
                if old_raw is None:
                    store.cas_delete(ptr_key, new_etag)
                else:
                    store.cas(ptr_key, old_raw, new_etag)
            except CasFail as e2:
                _, cur = store.get(ptr_key)
                print("::error::비상 — %s · 되돌리기 CAS 실패(%s). 확인 뒤 이 1줄을 실행:\n"
                      "python3 %s restore %s --key %s --from %s --if-match %s"
                      % (e, e2, os.path.abspath(__file__), store.describe(), ptr_key, saved, cur), file=sys.stderr)
                return 5
            print("::error::%s — 옛 포인터로 되돌렸다(ETag 조건 · 사본 %s)" % (e, saved), file=sys.stderr)
            return 4
        print("✅ 라이브 대조 일치(본문·서명 두 파일)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
