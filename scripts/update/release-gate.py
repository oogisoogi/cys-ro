#!/usr/bin/env python3
"""발행 게이트(1.1.8 U3 · 설계 AUTO-UPDATE-118 §8 U3 · §5-3 · §12 D12 · TICKETS ★U3 추가) — 하나라도 어긋나면 발행 거부.

단계(하위 명령) — 어느 레인이 어느 단계를 부르는지는 HANDOFF-U3 §2 표:
  assets   릴리스 자산 묶음: ① `latest.json` 자산 **존재 의무**(본체 v*·팩 단독 pack-v* 모두 · §5-3 다리) — 고정 tombstone
           파일(`scripts/release/latest-tombstone.json`)이 저장소에 있으면 다리 기간이 끝난 것이므로 sha256 = 그 파일이어야 함
           ② 팩 매니페스트 `min_binary_version` **빈 값 = 거부**(서명 레인 manifest · 앱 동봉 manifest 둘 다 · D23 cutover 대비)
  body     릴리스 본문(서명 전·후): 서식 · cysr 필수 행(맥 arm64·윈 x64) · `notes_ko` · `requires` 빈 값 · URL 규칙표 ·
           맥 cdhash/dr_pin_id · 윈 a2_sig_url/payload_manifest · `release_seq` 증가 ⇒ 판 증가(직전 보관소 본문 대비) ·
           보관소에 같은 seq 가 이미 있으면 바이트 동일만 통과 · (서명이 있으면) 서명 key id = 본문 key_id ∈ 키링 release
  verify   봉투·본문·폐기문을 **U1 `cys update-verify`** 에 통과시킨다(검증 함수는 하나뿐 · §6-2) — 본문의 모든 기판 행마다
           판정 = 기대값(기본 apply) · rc 0. 파이썬은 서명을 검증하지 않는다.
종료: 0 = 통과 · 1 = 게이트 거부 · 3 = 판정 불가(도구 없음·입력 손상 — 조용한 통과 금지).
"""
import argparse
import base64
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import update_common as uc  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TOMBSTONE = os.path.join(ROOT, "scripts", "release", "latest-tombstone.json")


from u1verify import GateFail, Undetermined  # noqa: E402 — 예외는 u1verify 와 하나(게시기·상속기도 같은 것을 잡는다)


# ── assets ─────────────────────────────────────────────────────────────────────────
def check_min_binary(path, what):
    try:
        man = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Undetermined("%s 를 읽을 수 없다(%s): %s" % (what, path, e))
    mb = man.get("min_binary_version") if isinstance(man, dict) else None
    if not isinstance(mb, str) or not mb.strip():
        raise GateFail("%s min_binary_version 빈 값 = 발행 거부(D23 · %s)" % (what, path))
    try:
        uc.semver_core(mb)
    except uc.PublishError as e:
        raise GateFail("%s min_binary_version 형식: %s" % (what, e))
    return mb


def stage_assets(a):
    out = []
    names = None
    if a.asset_list:
        names = [n.strip() for n in a.asset_list.split(",") if n.strip()]
    elif a.release_dir:
        names = sorted(os.listdir(a.release_dir))
    if names is not None:
        if "latest.json" not in names:
            raise GateFail("릴리스 자산에 latest.json 이 없다 — 모든 릴리스 latest.json 의무(설계 §5-3 다리)")
        lp = os.path.join(a.release_dir or ".", "latest.json")
        if not os.path.isfile(lp) or os.path.islink(lp):
            raise GateFail("latest.json 파일 없음(또는 심링크): %s" % lp)
        tomb = a.tombstone or TOMBSTONE
        if os.path.exists(tomb):
            if uc.sha256_file(lp) != uc.sha256_file(tomb):
                raise GateFail("다리 기간 뒤 latest.json 은 고정 tombstone 바이트여야 한다(sha256 불일치 · %s)" % tomb)
            out.append("latest.json = tombstone(%s)" % uc.sha256_file(tomb)[:12])
        else:
            try:
                json.load(open(lp, encoding="utf-8"))
            except ValueError as e:
                raise GateFail("latest.json 이 JSON 이 아니다: %s" % e)
            out.append("latest.json 있음(다리 기간 · 생성본)")
    for p in a.pack_manifest or []:
        out.append("pack-manifest min_binary=%s (%s)" % (check_min_binary(p, "팩 매니페스트"), p))
    for p in a.bundled_manifest or []:
        out.append("동봉 pack-manifest min_binary=%s (%s)" % (check_min_binary(p, "앱 동봉 팩 매니페스트"), p))
    if not out:
        raise Undetermined("잴 대상 0건(--release-dir/--asset-list/--pack-manifest/--bundled-manifest 중 하나 필요)")
    return out


# ── body ───────────────────────────────────────────────────────────────────────────
def check_body_shape(b):
    if b.get("kind") != uc.RELEASE_KIND:
        raise GateFail("본문 kind %r" % b.get("kind"))
    comp = b.get("component")
    if comp not in uc.COMPONENTS:
        raise GateFail("component %r" % comp)
    seq = b.get("release_seq")
    if not isinstance(seq, int) or seq < 1:
        raise GateFail("release_seq %r" % seq)
    if not isinstance(b.get("min_from_release_seq"), int) or not 0 <= b["min_from_release_seq"] < seq:
        raise GateFail("min_from_release_seq 0 ≤ 값 < release_seq")
    if b.get("state_migration") not in uc.STATE_MIGRATIONS:
        raise GateFail("state_migration %r" % b.get("state_migration"))
    if not uc.KEY_ID_RE.match(b.get("key_id") or ""):
        raise GateFail("key_id 형식")
    try:
        uc.check_signed_at(b.get("signed_at"), uc.trusted_now(), None, "본문 signed_at")
    except uc.PublishError as e:
        raise GateFail(str(e))
    try:
        uc.check_notes_ko(b.get("notes_ko"))
        uc.semver_core(b.get("version"))
    except uc.PublishError as e:
        raise GateFail(str(e))
    req = b.get("requires") or {}
    if comp == "cysr":
        mb = req.get("min_binary_for_pack")
        if not isinstance(mb, str) or not mb.strip():
            raise GateFail("requires.min_binary_for_pack 빈 값 = 발행 거부(§6-1)")
    else:
        if not isinstance(req.get("min_cysr_release_seq"), int) or req["min_cysr_release_seq"] < 1 \
                or not str(req.get("python") or "").strip():
            raise GateFail("agora-client requires 빈 값 = 발행 거부(§6-1)")
    assets = b.get("assets") or {}
    if not assets:
        raise GateFail("assets 비었음")
    if comp == "cysr":
        miss = [t for t in uc.REQUIRED_CYSR_TARGETS if t not in assets]
        if miss:
            raise GateFail("cysr 필수 기판 행 부재(G3): %s" % miss)
    for t, r in assets.items():
        if t not in uc.TARGETS or r.get("target") != t:
            raise GateFail("행 %s target" % t)
        if r.get("release_seq") != seq:
            raise GateFail("행 %s release_seq ≠ 본문" % t)
        if not uc.HEX64_RE.match(r.get("sha256") or "") or not r.get("size") or not r.get("max_unpacked"):
            raise GateFail("행 %s sha256/size/max_unpacked" % t)
        if not uc.url_ok_for(comp, "asset", r.get("url")):
            raise GateFail("행 %s url 규칙 밖(§4-4): %s" % (t, r.get("url")))
        if not str(r.get("build_id") or "").strip() or not isinstance(r.get("features"), list):
            raise GateFail("행 %s build_id/features" % t)
        if comp == "cysr":
            bp = r.get("bundled_pack") or {}
            if not str(bp.get("version") or "").strip() or not uc.HEX64_RE.match(str(bp.get("digest") or "")):
                raise GateFail("행 %s bundled_pack" % t)
            if t.startswith("macos-") and not (uc.HEX40_RE.match(r.get("cdhash") or "")
                                               and uc.HEX40_RE.match(r.get("dr_pin_id") or "")):
                raise GateFail("맥 행 %s cdhash/dr_pin_id(40 hex)" % t)
            if t.startswith("windows-"):
                if not uc.url_ok_for(comp, "a2_sig", r.get("a2_sig_url")):
                    raise GateFail("윈 행 %s a2_sig_url 규칙 밖" % t)
                pm = r.get("payload_manifest")
                if not isinstance(pm, list) or not pm:
                    raise GateFail("윈 행 %s payload_manifest 부재(§3-7 ①)" % t)
                seen = set()
                for e in pm:
                    if not isinstance(e, dict) or not uc.HEX64_RE.match(e.get("sha256") or "") \
                            or not isinstance(e.get("size"), int) or not e.get("path") \
                            or e["path"].startswith("/") or ".." in e["path"].split("/") or "\\" in e["path"]:
                        raise GateFail("윈 행 %s payload_manifest 항목 형식: %r" % (t, e))
                    if e["path"].lower() in seen:
                        raise GateFail("윈 행 %s payload_manifest 경로 중복(대소문자 무시): %s" % (t, e["path"]))
                    seen.add(e["path"].lower())
    return comp, seq


def stage_body(a):
    raw = open(a.body, "rb").read()
    try:
        b = json.loads(raw)
    except ValueError as e:
        raise GateFail("본문 JSON 아님: %s" % e)
    comp, seq = check_body_shape(b)
    out = ["본문 서식·필수 행·notes_ko·requires·URL(component 표) 통과 (%s seq %d)" % (comp, seq)]
    if a.expect_seq is not None and seq != a.expect_seq:
        raise GateFail("release_seq %d ≠ 발행 순번 변수 %d(vars.CYSR_RELEASE_SEQ)" % (seq, a.expect_seq))
    if a.sig:
        # ★2판(codex 1R #4): key id 바이트가 아니라 **암호 검증**(키링 release · 만료·폐기 반영) → 통과 증표.
        if not a.keyring:
            raise Undetermined("--sig 검증에는 --keyring 이 필요하다")
        sig_bytes = open(a.sig, "rb").read()
        now = uc.trusted_now()
        try:
            kid = uc.verify_sig(uc.load_keyring(a.keyring), "release", b["key_id"], raw, sig_bytes.decode("utf-8"), now)
        except uc.PublishError as e:
            raise GateFail(str(e))
        out.append("본문 서명 암호 검증 통과(key %s)" % kid)
        if a.stamp:
            uc.write_stamp(a.body, sig_bytes, kid, "release", uc.STAMP_BY_PY, now, {"kind": "archive", "seq": seq})
            out.append("통과 증표 %s" % uc.stamp_path(a.body))
    elif a.stamp:
        raise Undetermined("--stamp 는 --sig 검증과 함께만")
    if a.archive_fs or a.archive_r2:
        from store import FsStore, R2Store, archive_state
        store = FsStore(a.archive_fs) if a.archive_fs else R2Store(a.archive_r2, a.wrangler.split())
        top, body_of = archive_state(store, comp)
        existing = body_of(seq)
        if existing is not None:
            if existing != raw:
                raise GateFail("보관소에 release_seq %d 가 이미 있고 바이트가 다르다(덮어쓰기 거부)" % seq)
            out.append("보관소 seq %d 이미 같은 바이트(멱등)" % seq)
        else:
            if top is not None and seq != top + 1:
                raise GateFail("release_seq %d ≠ 보관소 최댓값 %d + 1(역행·건너뜀 거부)" % (seq, top))
            if top is None and not a.first:
                raise GateFail("보관소가 비었다 — 첫 본문이면 --first 를 명시하라")
            out.append("순번 = 보관소 최댓값+1 (%s → %d)" % (top, seq))
            prev_raw = body_of(top) if top is not None else None
            if prev_raw:
                # ★2판(codex 1R #19): 순서 판정은 release_seq 하나 — 판 문자열은 비보안 경고(게이트 실패 아님).
                pv = json.loads(prev_raw)["version"]
                if uc.semver_core(b["version"]) < uc.semver_core(pv) or b["version"] == pv:
                    print("::warning::판 문자열이 직전(seq %d · %s)보다 크지 않다: %s — 순서는 release_seq 로 판정(비보안 경고)"
                          % (top, pv, b["version"]), file=sys.stderr)
                    out.append("판 문자열 경고(비보안): %s → %s" % (pv, b["version"]))
    return out


def stage_revocations(a):
    raw = open(a.doc, "rb").read()
    d = json.loads(raw)
    if d.get("kind") != uc.REVOCATIONS_KIND or not isinstance(d.get("rev"), int) or d["rev"] < 1:
        raise GateFail("폐기문 서식(kind/rev)")
    now = uc.trusted_now()
    kr = uc.load_keyring(a.keyring)
    sig_bytes = open(a.doc + ".minisig", "rb").read()
    try:
        uc.check_signed_at(d.get("signed_at"), now, None, "폐기문 signed_at")
        kid = uc.verify_sig(kr, "root", d.get("key_id"), raw, sig_bytes.decode("utf-8"), now)
    except uc.PublishError as e:
        raise GateFail(str(e))
    out = ["폐기문 R 서명 암호 검증 통과(rev %d · key %s)" % (d["rev"], kid)]
    if a.prev:
        pb = open(a.prev, "rb").read()
        p = json.loads(pb)
        try:
            uc.verify_sig(kr, "root", p.get("key_id"), pb, open(a.prev + ".minisig", encoding="utf-8").read(), now)
            uc.check_signed_at(d["signed_at"], now, p.get("signed_at"), "폐기문 signed_at")
        except uc.PublishError as e:
            raise GateFail("직전 폐기문: %s" % e)
        if d["rev"] != p["rev"] + 1:
            raise GateFail("rev %d ≠ 직전 %d + 1" % (d["rev"], p["rev"]))
        rk = lambda lst: {(r["component"], r["release_seq"]) for r in lst}
        if not (set(p.get("revoked_key_ids", [])) <= set(d.get("revoked_key_ids", []))
                and rk(p.get("revoked_releases", [])) <= rk(d.get("revoked_releases", []))
                and set((p.get("dr_pins") or {}).get("revoke", [])) <= set((d.get("dr_pins") or {}).get("revoke", []))):
            raise GateFail("폐기 집합이 직전보다 줄었다(단조 위반)")
        out.append("직전 대비 rev+1 · 폐기 집합 단조 · 시각 단조")
    elif not a.first:
        raise GateFail("직전 폐기문(--prev)이 없으면 --first 를 명시하라")
    if a.stamp:
        uc.write_stamp(a.doc, sig_bytes, kid, "root", uc.STAMP_BY_PY, now, {"kind": "revocations", "rev": d["rev"]})
        out.append("통과 증표 %s" % uc.stamp_path(a.doc))
    return out


# ── verify(U1 cys update-verify) — 정본 = u1verify.py(게시기·상속기와 같은 함수) ─────────────────
from u1verify import verify_envelope  # noqa: E402


def stage_verify(a):
    accept = [x.strip() for x in a.expect.split(",") if x.strip()]
    env = json.load(open(a.envelope, encoding="utf-8"))
    out = verify_envelope(a.cys, a, accept)
    if a.stamp:
        uc.write_stamp(a.envelope, open(a.sig, "rb").read(), env.get("key_id"), "feed", uc.STAMP_BY_U1,
                       uc.trusted_now(), {"kind": "envelope", "feed_rev": env.get("feed_rev"),
                                          "revocations_sha256": uc.sha256_bytes(open(a.revocations, "rb").read())})
        out.append("통과 증표 %s" % uc.stamp_path(a.envelope))
    return out


def main(argv=None):
    # 윈 러너 콘솔(cp1252)에서 한국어 출력이 UnicodeEncodeError 로 죽지 않게(bundle-prep.sh 와 같은 처방).
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="발행 게이트 — 설계 §8 U3")
    sub = ap.add_subparsers(dest="stage", required=True)
    s1 = sub.add_parser("assets")
    s1.add_argument("--release-dir", default=None)
    s1.add_argument("--asset-list", default=None, help="쉼표 구분 업로드 자산명(팩 단독 레인)")
    s1.add_argument("--tombstone", default=None)
    s1.add_argument("--pack-manifest", action="append")
    s1.add_argument("--bundled-manifest", action="append")
    s2 = sub.add_parser("body")
    s2.add_argument("--body", required=True)
    s2.add_argument("--sig", default=None)
    s2.add_argument("--keyring", default=None)
    s2.add_argument("--archive-fs", default=None, help="보관소 저장소(FS 백엔드 루트 · publish-site --fs 와 같은 곳)")
    s2.add_argument("--archive-r2", default=None, help="보관소 저장소(R2 버킷)")
    s2.add_argument("--wrangler", default="bunx wrangler")
    s2.add_argument("--expect-seq", type=int, default=None, help="발행 순번 변수(vars.CYSR_RELEASE_SEQ)와 일치 강제")
    s2.add_argument("--first", action="store_true", help="보관소 첫 본문")
    s2.add_argument("--stamp", action="store_true", help="암호 검증 통과 증표(<body>.verified.json)를 쓴다")
    s2v = sub.add_parser("revocations")
    s2v.add_argument("--doc", required=True)
    s2v.add_argument("--keyring", required=True)
    s2v.add_argument("--prev", default=None)
    s2v.add_argument("--first", action="store_true")
    s2v.add_argument("--stamp", action="store_true")
    s3 = sub.add_parser("verify")
    s3.add_argument("--cys", required=True)
    s3.add_argument("--component", required=True)
    s3.add_argument("--channel", required=True)
    s3.add_argument("--envelope", required=True)
    s3.add_argument("--sig", required=True)
    s3.add_argument("--revocations", required=True)
    s3.add_argument("--revocations-sig", required=True)
    s3.add_argument("--target", action="append")
    s3.add_argument("--installed-release-seq", type=int, default=None, help="기본 = 본문 허용 출발 seq 전부")
    s3.add_argument("--allow-expired", action="store_true", help="직전(현재 게시) 봉투 상속 검증용 — 만료(ⓔ)만 허용")
    s3.add_argument("--stamp", action="store_true", help="통과 증표(<envelope>.verified.json)를 쓴다")
    s3.add_argument("--expect", default="apply", help="허용 판정(쉼표 구분 · 예: apply,halt,not_in_rollout)")
    a = ap.parse_args(argv)
    try:
        lines = {"assets": stage_assets, "body": stage_body, "revocations": stage_revocations,
                 "verify": stage_verify}[a.stage](a)
    except GateFail as e:
        print("::error::발행 게이트 거부(%s) — %s" % (a.stage, e), file=sys.stderr)
        return 1
    except Undetermined as e:
        print("::error::발행 게이트 판정 불가(%s) — %s" % (a.stage, e), file=sys.stderr)
        return 3
    except (OSError, ValueError, KeyError, uc.PublishError) as e:
        print("::error::발행 게이트 판정 불가(%s) — %s: %s" % (a.stage, type(e).__name__, e), file=sys.stderr)
        return 3
    for l in lines:
        print("✅ " + l)
    return 0


if __name__ == "__main__":
    sys.exit(main())
