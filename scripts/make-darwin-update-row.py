#!/usr/bin/env python3
"""latest.json 의 맥 행(darwin-aarch64 / darwin-x86_64) 생성·병합 — B7 · TICKET=v110-darwin-update.

앱(cys-app)의 맥 업데이트 경로는 minisign 이 아니라 **sha256 · 크기 · codesign 봉인 · CDHash**
넷으로 받은 물건을 정박한다(src-tauri/src/macupdate.rs 머리말). 그 넷을 발행 자산에서 실측해
latest.json 행으로 찍는 것이 이 스크립트다.

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


def build_row(version, zip_path, cdhash, url=None, repo=RELEASE_REPO):
    """맥 행 하나. ★signature 는 빈 문자열이라도 **항상** 넣는다(위 경고)."""
    if not cdhash:
        raise SystemExit("::error::CDHash 를 읽지 못했다 — 검증 칸이 빈 행은 만들지 않는다(fail-closed)")
    return {
        # 우리 맥 경로는 이 칸을 읽지 않는다. 그러나 없으면 윈도까지 죽는다 — 위 경고 참조.
        "signature": "",
        "url": url or asset_url(version, os.path.basename(zip_path), repo),
        "sha256": sha256_file(zip_path),
        "size": os.path.getsize(zip_path),
        "cdhash": cdhash.lower(),
    }


def merge_row(manifest, target, row):
    """기존 latest.json 에 맥 행을 끼운다 — **다른 행은 건드리지 않는다**(윈도 발행본 보존)."""
    out = json.loads(json.dumps(manifest))  # 입력을 제자리 수정하지 않는다
    out.setdefault("platforms", {})[target] = row
    return out


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
    a = ap.parse_args(argv)

    cdhash = a.cdhash or (cdhash_of(a.app) if a.app else None)
    row = build_row(a.version, a.zip, cdhash, a.url, a.repo)
    if not a.merge:
        print(json.dumps({a.target: row}, ensure_ascii=False, indent=2))
        return 0

    with open(a.merge, encoding="utf-8") as fh:
        manifest = json.load(fh)
    out = merge_row(manifest, a.target, row)
    missing = every_row_has_url_and_signature(out)
    if missing:
        raise SystemExit(f"::error::url·signature 가 빠진 행: {missing} — 발행하면 윈도 업데이트까지 죽는다")
    with open(a.merge, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"병합됨: {a.merge} ← {a.target} ({row['size']} B · sha {row['sha256'][:12]}… · cdhash {row['cdhash'][:12]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
