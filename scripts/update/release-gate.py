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
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import update_common as uc  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TOMBSTONE = os.path.join(ROOT, "scripts", "release", "latest-tombstone.json")


class GateFail(Exception):
    pass


class Undetermined(Exception):
    pass


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
def archive_bodies(archive_dir, component):
    d = os.path.join(archive_dir, component, "releases")
    out = {}
    for p in glob.glob(os.path.join(d, "*.json")):
        m = re.match(r"^(\d+)\.json$", os.path.basename(p))
        if m:
            out[int(m.group(1))] = p
    return out


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
    if not isinstance(b.get("signed_at"), int):
        raise GateFail("signed_at 정수 아님")
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
        if not uc.url_ok(r.get("url"), ("asset", "site")):
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
                if not uc.url_ok(r.get("a2_sig_url"), ("asset",)):
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
    out = ["본문 서식·필수 행·notes_ko·requires·URL 통과 (%s seq %d)" % (comp, seq)]
    if a.sig:
        sig_text = open(a.sig, encoding="utf-8").read()
        try:
            sk = uc.sig_key_id(sig_text)
        except uc.PublishError as e:
            raise GateFail(str(e))
        if sk != b["key_id"]:
            raise GateFail("본문 서명 key id %s ≠ 본문 key_id %s" % (sk, b["key_id"]))
        out.append("서명 key id = 본문 key_id %s" % sk)
    if a.keyring:
        try:
            uc.find_key(uc.load_keyring(a.keyring), "release", b["key_id"])
        except uc.PublishError as e:
            raise GateFail("본문 key_id 가 키링 release 용도에 없다: %s" % e)
        out.append("key_id ∈ 키링 release")
    if a.archive_dir:
        bodies = archive_bodies(a.archive_dir, comp)
        if seq in bodies:
            if open(bodies[seq], "rb").read() != raw:
                raise GateFail("보관소에 release_seq %d 가 이미 있고 바이트가 다르다(덮어쓰기 거부)" % seq)
            out.append("보관소 seq %d 이미 같은 바이트(멱등)" % seq)
        older = [s for s in bodies if s < seq]
        newer = [s for s in bodies if s > seq]
        if newer:
            raise GateFail("release_seq 역행: 보관소에 더 큰 seq %s 가 있다" % sorted(newer))
        if older:
            prev = json.load(open(bodies[max(older)], encoding="utf-8"))
            pc, nc = uc.semver_core(prev["version"]), uc.semver_core(b["version"])
            if nc > pc:
                out.append("판 증가 %s → %s (seq %d → %d)" % (prev["version"], b["version"], max(older), seq))
            elif nc == pc and b["version"] != prev["version"] and "+" in b["version"] and a.allow_canary:
                out.append("캐너리 판(같은 3마디 · 빌드 꼬리 · --allow-canary) %s → %s" % (prev["version"], b["version"]))
            else:
                raise GateFail("release_seq 증가 ⇒ 판 증가 위반: %s(seq %d) → %s(seq %d)"
                               % (prev["version"], max(older), b["version"], seq))
        else:
            out.append("보관소 첫 본문(직전 없음)")
    return out


# ── verify(U1 cys update-verify) ─────────────────────────────────────────────────────
def stage_verify(a):
    if not a.cys or not os.access(a.cys, os.X_OK):
        raise Undetermined("cys 바이너리 없음(update-verify 필요 · U1 이상): %r" % a.cys)
    env = json.load(open(a.envelope, encoding="utf-8"))
    body = json.loads(base64.b64decode(env["release"]))
    targets = a.target or sorted(body["assets"])
    out = []
    for t in targets:
        cmd = [a.cys, "update-verify", "--component", a.component, "--channel", a.channel,
               "--envelope", a.envelope, "--sig", a.sig, "--revocations", a.revocations,
               "--revocations-sig", a.revocations_sig, "--target", t,
               "--installed-release-seq", str(a.installed_release_seq), "--json"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        try:
            v = json.loads(p.stdout)
        except ValueError:
            raise Undetermined("update-verify 출력이 JSON 아님(rc %d): %s %s" % (p.returncode, p.stdout[-300:], p.stderr[-300:]))
        if v.get("verdict") != a.expect or (a.expect not in ("reject", "undetermined") and p.returncode != 0):
            raise GateFail("update-verify[%s] = %s/%s(step %s · %s) rc %d — 기대 %s"
                           % (t, v.get("verdict"), v.get("code"), v.get("step"), v.get("detail"), p.returncode, a.expect))
        asset = v.get("asset") or {}
        if a.expect == "apply" and asset.get("sha256") != body["assets"][t]["sha256"]:
            raise GateFail("update-verify[%s] asset 이 본문 행과 다르다" % t)
        out.append("update-verify[%s] = %s rc %d" % (t, v.get("verdict"), p.returncode))
    return out


def main(argv=None):
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
    s2.add_argument("--archive-dir", default=None, help="사이트 /update 원본 폴더(<c>/releases/<seq>.json)")
    s2.add_argument("--allow-canary", action="store_true")
    s3 = sub.add_parser("verify")
    s3.add_argument("--cys", required=True)
    s3.add_argument("--component", required=True)
    s3.add_argument("--channel", required=True)
    s3.add_argument("--envelope", required=True)
    s3.add_argument("--sig", required=True)
    s3.add_argument("--revocations", required=True)
    s3.add_argument("--revocations-sig", required=True)
    s3.add_argument("--target", action="append")
    s3.add_argument("--installed-release-seq", type=int, default=0)
    s3.add_argument("--expect", default="apply")
    a = ap.parse_args(argv)
    try:
        lines = {"assets": stage_assets, "body": stage_body, "verify": stage_verify}[a.stage](a)
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
