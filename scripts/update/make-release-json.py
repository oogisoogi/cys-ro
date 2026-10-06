#!/usr/bin/env python3
"""릴리스 본문 생성기(1.1.8 U3 · 설계 AUTO-UPDATE-118 §6-1 · §8 U 의식 ①) — **서명 없는** 본문 JSON 을 만든다.

★언어 = 파이썬(Rust 하위 명령 아님) 근거 1줄: 입력이 전부 CI 산출 파일(SHA256SUMS·build-info JSON·CDHash·
  윈 페이로드 트리)이라 기존 발행 레인(release-postprocess.py·release-verify.py)과 같은 자리에서 빌드 없이 돌아야 하고,
  판정은 어차피 Rust `cys update-verify` 하나가 하므로(§6-2) 생산자가 Rust 일 이유가 없다 — 계약 두 벌 위험은
  발행 게이트가 이 출력을 `cys update-verify` 에 통과시키는 것으로 닫는다.

입력(CI 산출):
  --release-dir      릴리스 자산을 받아 둔 폴더(크기·sha256 을 여기서 잰다)
  --sums             SHA256SUMS.txt(기본 = <release-dir>/SHA256SUMS.txt) — 잰 값과 **둘 다** 같아야 한다
  --asset T=FILE     기판 T 의 자산 파일명(반복) · url = cys-ro 릴리스 다운로드 규칙(§4-4 1홉)
  --build-info T=P   그 기판 바이너리의 `cys build-info --json` 출력 파일(cysr 필수) → build_id·release_seq·
                     bundled_pack·features 를 **이 출력에서** 옮긴다(U1 buildinfo.rs 「같은 정의 한 벌」)
  --cdhash T=HEX     맥 행 CDHash(40 hex · `codesign -dvvv` 의 CDHash)
  --dr-pin-id T=HEX  맥 행 DR 핀 id(기본 = cys-local leaf sha1)
  --a2-sig T=FILE    윈 행 A2 서명 파일명(.sig · 같은 릴리스 자산) → a2_sig_url
  --payload-dir T=D  윈 행 설치 페이로드 트리(빌드 트리) → payload_manifest[{path,size,sha256}] 전수
  --max-unpacked T=N 덮어쓰기(기본 = zip 은 중앙 디렉터리 합 · 윈은 payload 합)

거부(= 발행하지 않음 · rc 2): cysr 의 맥 arm64·윈 x64 행 부재(G3) · notes_ko 규칙 · requires 빈 값(min_binary 빈 값) ·
  build-info 의 release_seq/target/version 불일치 · SHA256SUMS 와 잰 값 불일치 · url 규칙 밖 · 페이로드 심링크.
"""
import argparse
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_common as uc  # noqa: E402


def pairs(values, what):
    out = {}
    for v in values or []:
        if "=" not in v:
            raise uc.PublishError("%s 형식은 TARGET=값: %r" % (what, v))
        k, val = v.split("=", 1)
        if k not in uc.TARGETS:
            raise uc.PublishError("%s 미지 기판 %s" % (what, k))
        if k in out:
            raise uc.PublishError("%s 기판 %s 중복" % (what, k))
        out[k] = val
    return out


def read_sums(path):
    sums = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                raise uc.PublishError("SHA256SUMS 줄 형식: %r" % line)
            h, name = parts[0].lower(), parts[1].lstrip("*")
            sums[name] = h
    return sums


def payload_manifest(root):
    """설치 폴더에 놓일 모든 파일 {path, size, sha256}(경로 = '/' 구분 상대 경로 · 정렬). 심링크·특수 파일 = 거부.
    제외 = scripts/update/payload-exclude.txt 의 명시 규칙만(U2 S9b 와 공유 · codex 1R #18)."""
    excl = uc.load_payload_excludes()
    rows = []
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise uc.PublishError("payload 폴더 없음: %s" % root)
    for dp, dns, fns in os.walk(root, followlinks=False):
        for d in dns:
            if os.path.islink(os.path.join(dp, d)):
                raise uc.PublishError("payload 안 심링크 폴더: %s" % os.path.join(dp, d))
        for n in fns:
            p = os.path.join(dp, n)
            if os.path.islink(p) or not os.path.isfile(p):
                raise uc.PublishError("payload 안 심링크·특수 파일: %s" % p)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if rel.lower() in excl:
                if rel.lower() == "cys-install-failure.txt":
                    raise uc.PublishError("payload 에 설치 실패 기록이 있다(실패한 설치): %s" % p)
                continue
            rows.append({"path": rel, "size": os.path.getsize(p), "sha256": uc.sha256_file(p)})
    if not rows:
        raise uc.PublishError("payload 비었음: %s" % root)
    rows.sort(key=lambda r: r["path"])
    return rows


def zip_unpacked(path):
    with zipfile.ZipFile(path) as z:
        return sum(i.file_size for i in z.infolist())


def build(args):
    if args.component not in uc.COMPONENTS:
        raise uc.PublishError("component %s" % args.component)
    if args.release_seq < 1:
        raise uc.PublishError("release_seq < 1")
    if args.min_from_release_seq < 0 or args.min_from_release_seq >= args.release_seq:
        raise uc.PublishError("min_from_release_seq 는 0 ≤ 값 < release_seq")
    if args.state_migration not in uc.STATE_MIGRATIONS:
        raise uc.PublishError("state_migration %s" % args.state_migration)
    if not uc.KEY_ID_RE.match(args.key_id or ""):
        raise uc.PublishError("key_id 형식(16자 대문자 hex): %r" % args.key_id)
    uc.semver_core(args.version)
    uc.check_notes_ko(args.notes_ko)

    if args.component == "cysr":
        mb = (args.requires_min_binary_for_pack or "").strip()
        if not mb:
            raise uc.PublishError("requires.min_binary_for_pack 빈 값 = 발행 거부(§6-1 · D23)")
        uc.semver_core(mb)
        requires = {"min_binary_for_pack": mb}
    else:
        py = (args.requires_python or "").strip()
        if args.requires_min_cysr_release_seq is None or args.requires_min_cysr_release_seq < 1 or not py:
            raise uc.PublishError("agora-client requires{min_cysr_release_seq, python} 빈 값 = 발행 거부")
        requires = {"min_cysr_release_seq": args.requires_min_cysr_release_seq, "python": py}

    assets_in = pairs(args.asset, "--asset")
    urls_in = pairs(args.asset_url, "--asset-url")
    bis = pairs(args.build_info, "--build-info")
    cdh = pairs(args.cdhash, "--cdhash")
    pins = pairs(args.dr_pin_id, "--dr-pin-id")
    a2 = pairs(args.a2_sig, "--a2-sig")
    pdirs = pairs(args.payload_dir, "--payload-dir")
    maxu = pairs(args.max_unpacked, "--max-unpacked")
    for extra, what in ((bis, "--build-info"), (cdh, "--cdhash"), (a2, "--a2-sig"), (pdirs, "--payload-dir"),
                        (maxu, "--max-unpacked"), (urls_in, "--asset-url"), (pins, "--dr-pin-id")):
        stray = set(extra) - set(assets_in)
        if stray:
            raise uc.PublishError("%s 가 --asset 에 없는 기판을 가리킨다: %s" % (what, sorted(stray)))
    if not assets_in:
        raise uc.PublishError("--asset 0개")
    if args.component == "cysr":
        miss = [t for t in uc.REQUIRED_CYSR_TARGETS if t not in assets_in]
        if miss:
            raise uc.PublishError("cysr 필수 기판 행 부재(G3): %s" % miss)

    sums = read_sums(args.sums or os.path.join(args.release_dir, "SHA256SUMS.txt"))
    assets = {}
    for t in sorted(assets_in):
        fn = assets_in[t]
        if os.path.basename(fn) != fn:
            raise uc.PublishError("자산 파일명에 경로 금지: %s" % fn)
        p = os.path.join(args.release_dir, fn)
        if os.path.islink(p) or not os.path.isfile(p):
            raise uc.PublishError("자산 파일 없음(또는 심링크): %s" % p)
        h = uc.sha256_file(p)
        if sums.get(fn) != h:
            raise uc.PublishError("SHA256SUMS ↔ 잰 값 불일치(또는 목록 밖): %s" % fn)
        url = urls_in.get(t) or uc.asset_url(args.version, fn)
        if not uc.url_ok_for(args.component, "asset", url):
            raise uc.PublishError("자산 url 규칙 밖(§4-4): %s" % url)
        row = {"url": url, "size": os.path.getsize(p), "sha256": h, "target": t,
               "release_seq": args.release_seq, "features": [], "build_id": ""}
        if t in bis:
            with open(bis[t], encoding="utf-8") as f:
                bi = json.load(f)
            if bi.get("release_seq") != args.release_seq:
                raise uc.PublishError("build-info[%s] release_seq %r ≠ %d" % (t, bi.get("release_seq"), args.release_seq))
            if bi.get("target") != t:
                raise uc.PublishError("build-info[%s] target %r ≠ 행" % (t, bi.get("target")))
            if bi.get("version") != args.version:
                raise uc.PublishError("build-info[%s] version %r ≠ %s" % (t, bi.get("version"), args.version))
            if not str(bi.get("build_id") or "").strip():
                raise uc.PublishError("build-info[%s] build_id 빈 값" % t)
            if str(bi["build_id"]).endswith("-dirty"):
                raise uc.PublishError("build-info[%s] build_id 가 -dirty(작업트리 변경 빌드) — 발행 거부" % t)
            bp = bi.get("bundled_pack") or {}
            if not str(bp.get("version") or "").strip() or not uc.HEX64_RE.match(str(bp.get("digest") or "")):
                raise uc.PublishError("build-info[%s] bundled_pack 빈 값·digest 형식" % t)
            if not isinstance(bi.get("features"), list):
                raise uc.PublishError("build-info[%s] features 칸 부재" % t)
            row["build_id"] = bi["build_id"]
            row["bundled_pack"] = {"version": bp["version"], "digest": bp["digest"]}
            row["features"] = list(bi["features"])
        elif args.component == "cysr":
            raise uc.PublishError("cysr 행 %s 에 --build-info 없음" % t)
        else:
            row["build_id"] = args.version
        if t.startswith("macos-") and args.component == "cysr":
            c = (cdh.get(t) or "").lower()
            if not uc.HEX40_RE.match(c):
                raise uc.PublishError("맥 행 %s cdhash 부재·형식(40 hex)" % t)
            pin = (pins.get(t) or uc.DR_PIN_ID_CYS_LOCAL).lower()
            if not uc.HEX40_RE.match(pin):
                raise uc.PublishError("맥 행 %s dr_pin_id 형식(40 hex)" % t)
            row["cdhash"], row["dr_pin_id"] = c, pin
        if t.startswith("windows-") and args.component == "cysr":
            sigf = a2.get(t)
            if not sigf or not os.path.isfile(os.path.join(args.release_dir, sigf)):
                raise uc.PublishError("윈 행 %s A2 서명(.sig) 자산 없음" % t)
            if sums.get(sigf) is None:
                raise uc.PublishError("윈 행 %s A2 서명이 SHA256SUMS 목록 밖: %s" % (t, sigf))
            su = uc.asset_url(args.version, sigf)
            if not uc.url_ok_for(args.component, "a2_sig", su):
                raise uc.PublishError("a2_sig_url 규칙 밖: %s" % su)
            row["a2_sig_url"] = su
            if t not in pdirs:
                raise uc.PublishError("윈 행 %s payload_manifest 입력(--payload-dir) 없음(§3-7 ①)" % t)
        if t in pdirs:
            row["payload_manifest"] = payload_manifest(pdirs[t])
        if t in maxu:
            row["max_unpacked"] = int(maxu[t])
        elif "payload_manifest" in row:
            row["max_unpacked"] = sum(r["size"] for r in row["payload_manifest"])
        elif fn.endswith(".zip"):
            row["max_unpacked"] = zip_unpacked(p)
        else:
            raise uc.PublishError("행 %s max_unpacked 를 잴 수 없다(zip·payload 아님) — --max-unpacked 필요" % t)
        if row["max_unpacked"] <= 0:
            raise uc.PublishError("행 %s max_unpacked 0" % t)
        assets[t] = row

    return {
        "kind": uc.RELEASE_KIND,
        "component": args.component,
        "release_seq": args.release_seq,
        "version": args.version,
        "key_id": args.key_id,
        "signed_at": uc.trusted_now(),
        "min_from_release_seq": args.min_from_release_seq,
        "requires": requires,
        "state_migration": args.state_migration,
        "assets": assets,
        "notes_ko": args.notes_ko,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="릴리스 본문(서명 없음) 생성 — 설계 §6-1")
    ap.add_argument("--component", required=True)
    ap.add_argument("--release-seq", type=int, required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--min-from-release-seq", type=int, required=True)
    ap.add_argument("--state-migration", required=True)
    ap.add_argument("--notes-ko", required=True)
    ap.add_argument("--key-id", required=True, help="U 키 key id(서명 의식이 같은 키인지 대조한다)")
    ap.add_argument("--requires-min-binary-for-pack", default=None)
    ap.add_argument("--requires-min-cysr-release-seq", type=int, default=None)
    ap.add_argument("--requires-python", default=None)
    ap.add_argument("--release-dir", required=True)
    ap.add_argument("--sums", default=None)
    ap.add_argument("--asset", action="append")
    ap.add_argument("--asset-url", action="append")
    ap.add_argument("--build-info", action="append")
    ap.add_argument("--cdhash", action="append")
    ap.add_argument("--dr-pin-id", action="append")
    ap.add_argument("--a2-sig", action="append")
    ap.add_argument("--payload-dir", action="append")
    ap.add_argument("--max-unpacked", action="append")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        body = build(args)
    except (uc.PublishError, OSError, ValueError) as e:
        print("::error::릴리스 본문 생성 거부 — %s" % e, file=sys.stderr)
        return 2
    data = uc.dump_json_bytes(body)
    tmp = args.out + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, args.out)
    print("✅ 릴리스 본문(서명 없음) %s · %s release_seq=%d · 행 %s · sha256 %s"
          % (args.out, body["component"], body["release_seq"], ",".join(sorted(body["assets"])), uc.sha256_bytes(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
