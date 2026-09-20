#!/usr/bin/env python3
"""latest.json 의 맥 행(darwin-aarch64 / darwin-x86_64) 생성·병합 — B7 · TICKET=v110-darwin-update.

앱(cys-app)의 맥 업데이트 경로는 minisign 이 아니라 **sha256 · 크기 · codesign 봉인 · CDHash**
넷으로 받은 물건을 정박한다(src-tauri/src/macupdate.rs 머리말). 그 넷을 발행 자산에서 실측해
latest.json 행으로 찍는 것이 이 스크립트다.

🔴 이 스크립트는 darwin 행의 **앱 절반(zip_*)만** 찍는다(TICKET=v110-zipurl · 2026-09-20):
  같은 행의 `url`·`signature` 는 **구판(1.0.2) 플러그인 경로**가 먹는 `.app.tar.gz` 자리이고
  `scripts/make-update-manifest.sh` 가 찍는다. 둘이 한 칸을 나눠 쓰면 다음 판에서 한쪽이 반드시
  틀린 물건을 받으므로 칸을 갈랐다 — 병합은 **덮어쓰기가 아니라 합치기**다.

🔴 반드시 알아야 할 것 — `signature` 칸을 **비워서라도 반드시 넣는다**:
  tauri-plugin-updater 2.10.1 의 `ReleaseManifestPlatform` 은 `url`+`signature` 를 요구하고
  `RemoteReleaseInner` 가 `#[serde(untagged)]` 다(updater.rs:71-85). 그래서 platforms 안의
  **어느 한 행**이라도 signature 가 없으면 platforms 전체 역직렬화가 실패하고 — 맥이 아니라
  **윈도 사용자의 업데이트가 통째로 죽는다.** 이 스크립트는 그 칸을 언제나 채운다.

사용:
  python3 scripts/make-darwin-update-row.py --version 1.1.0 \
      --zip dist-mac/cysr-macos-arm64-v1.1.0.zip --app dist-mac/staging/cysr.app     # 행만 출력
  python3 scripts/make-darwin-update-row.py ... --merge dist-update/latest.json      # 병합 저장

⚠ 발행(릴리스 자산·latest.json 갱신)은 master 게이트다 — 이 스크립트는 파일을 만들 뿐 올리지 않는다.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

RELEASE_REPO = "oogisoogi/cys-ro"  # release-postprocess.py 의 RELEASE_REPO 와 같은 레포여야 한다.
TARGETS = ("darwin-aarch64", "darwin-x86_64")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cdhash_of(app_path):
    """`codesign -dvvv` 의 CDHash — 출력은 **stderr** 로 나온다(stdout 으로 읽으면 언제나 빈 값)."""
    p = subprocess.run(["/usr/bin/codesign", "-dvvv", app_path], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"::error::codesign -dvvv 실패({p.returncode}): {p.stderr.strip()}")
    return parse_cdhash(p.stderr)


def parse_cdhash(text):
    """CDHash 한 줄을 뽑는다(macupdate.rs 의 parse_cdhash 와 같은 규칙 — 첫 줄·소문자)."""
    m = re.search(r"^CDHash=([0-9a-fA-F]+)\s*$", text or "", re.M)
    return m.group(1).lower() if m else None


def asset_url(version, asset_name, repo=RELEASE_REPO):
    return f"https://github.com/{repo}/releases/download/v{version}/{asset_name}"


ZIP_KEYS = ("zip_url", "zip_sha256", "zip_size", "zip_cdhash")
LEGACY_KEYS = ("url", "signature")


def build_row(version, zip_path, cdhash, url=None, repo=RELEASE_REPO):
    """**앱 절반**(zip_*) 하나. 구판 절반(url·signature)은 여기서 만들지 않는다.

    ★칸을 가른 이유(TICKET=v110-zipurl · 2026-09-20): 같은 darwin 행을 두 클라이언트가 읽는다 —
      구판(1.0.2)은 `url` 을 **tar.gz** 로 받아 풀고, 1.1+ 앱은 **zip** 을 받아 검증한다.
      한 칸을 나눠 쓰면 다음 판 발행에서 한쪽이 반드시 틀린 물건을 받는다. 그래서 이 스크립트는
      `zip_*` 넷만 찍고, `url`·`signature` 는 `make-update-manifest.sh` 가 찍은 것을 **보존**한다.
    """
    if not cdhash:
        raise SystemExit("::error::CDHash 를 읽지 못했다 — 검증 칸이 빈 행은 만들지 않는다(fail-closed)")
    return {
        "zip_url": url or asset_url(version, os.path.basename(zip_path), repo),
        "zip_sha256": sha256_file(zip_path),
        "zip_size": os.path.getsize(zip_path),
        "zip_cdhash": cdhash.lower(),
    }


def merge_row(manifest, target, row, legacy=None):
    """기존 latest.json 에 **앱 절반을 얹는다** — 덮어쓰지 않고 합친다.

    ⚠종전에는 행을 통째로 **대체**했다. 그래서 `make-update-manifest.sh` 가 찍어 둔 구판 절반
      (url=tar.gz · signature=.sig)이 이 병합 한 번에 사라졌다 — 그 순간 1.0.2 맥의 갱신 경로가
      끊긴다(무증상: 매니페스트는 멀쩡해 보인다). 합치기가 정본이다.
    **다른 행은 건드리지 않는다**(윈도 발행본 보존).
    """
    out = json.loads(json.dumps(manifest))  # 입력을 제자리 수정하지 않는다
    platforms = out.setdefault("platforms", {})
    existing = platforms.get(target)
    merged = dict(existing) if isinstance(existing, dict) else {}
    for k, v in (legacy or {}).items():
        if v is not None:
            merged[k] = v
    merged.update(row)
    platforms[target] = merged
    return out


def legacy_half_problem(row):
    """구판 절반이 성립하는가 — 문제 문장(차단 사유) 또는 None(통과).

    ★`url` 은 **있기만 해서는 안 되고 tar.gz 여야 한다.** 비었거나 zip 을 가리키면 구판이
      우리 zip 을 tar.gz 로 풀려다 실패한다(이 티켓이 막는 사고의 거울상). 그리고 빈 문자열
      url 은 플러그인 역직렬화 자체를 깨서 **윈도까지** 죽인다.
    """
    url = (row.get("url") or "").strip()
    if not url:
        return ("darwin 행에 구판 url(.app.tar.gz)이 없다 — 먼저 scripts/make-update-manifest.sh 로 "
                "구판 절반을 찍거나 --tarball-url 로 넘겨라")
    if not url.endswith(".app.tar.gz"):
        return f"구판 url 이 .app.tar.gz 가 아니다: {url}"
    if "signature" not in row:
        return "darwin 행에 signature 칸이 없다 — platforms 전체 역직렬화가 깨져 윈도까지 죽는다"
    return None


def every_row_has_url_and_signature(manifest):
    """윈도까지 죽이는 그 결손을 발행 전에 잡는 술어(스크립트·시험이 함께 쓴다)."""
    missing = []
    for name, row in (manifest.get("platforms") or {}).items():
        if not isinstance(row, dict) or "url" not in row or "signature" not in row:
            missing.append(name)
    return missing


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--zip", required=True, help="발행할 맥 zip (cysr-macos-<arch>-v<판>.zip)")
    ap.add_argument("--app", help="CDHash 를 잴 .app (미지정 시 --cdhash 필수)")
    ap.add_argument("--cdhash", help="이미 재 둔 CDHash")
    ap.add_argument("--target", default="darwin-aarch64", choices=TARGETS)
    ap.add_argument("--url", help="자산 URL(기본: 릴리스 레포 규칙에서 파생)")
    ap.add_argument("--repo", default=RELEASE_REPO)
    ap.add_argument("--merge", help="이 latest.json 에 병합해 덮어쓴다(미지정 시 행만 출력)")
    ap.add_argument("--tarball-url", help="구판(plugin) 자산 url — 기존 행에 없을 때만 필요하다")
    ap.add_argument("--tarball-sig", help="구판 .sig 전문 — 기존 행에 없을 때만 필요하다")
    a = ap.parse_args(argv)

    cdhash = a.cdhash or (cdhash_of(a.app) if a.app else None)
    row = build_row(a.version, a.zip, cdhash, a.url, a.repo)
    legacy = {"url": a.tarball_url, "signature": a.tarball_sig}
    if not a.merge:
        print(json.dumps({a.target: row}, ensure_ascii=False, indent=2))
        return 0

    with open(a.merge, encoding="utf-8") as fh:
        manifest = json.load(fh)
    out = merge_row(manifest, a.target, row, legacy)
    # ★구판 절반이 성립하는지 **먼저** 본다 — 이 행은 1.0.2 맥의 유일한 갱신 경로다.
    problem = legacy_half_problem(out["platforms"][a.target])
    if problem:
        raise SystemExit(f"::error::{problem}")
    missing = every_row_has_url_and_signature(out)
    if missing:
        raise SystemExit(f"::error::url·signature 가 빠진 행: {missing} — 발행하면 윈도 업데이트까지 죽는다")
    with open(a.merge, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"병합됨: {a.merge} ← {a.target} zip {row['zip_size']} B · "
          f"sha {row['zip_sha256'][:12]}… · cdhash {row['zip_cdhash'][:12]}… "
          f"(구판 url 보존: {out['platforms'][a.target]['url']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
