#!/usr/bin/env python3
"""x64 맥 재료의 정적 수집기(1.1.20 #57 · TICKET=cysr-1120-integ2 · master#ddf562c2 A′ · master#58de9790 A).

arm64 맥에서 x64 번들 안 `cys build-info --json` 을 실행하면 Rosetta 경고가 사람 화면에 뜬다. 그래서 x64 바이너리는
**실행하지 않고**, 같은 발행의 arm64 번들 build-info(네이티브 실행 결과)를 입력으로 받아 칸마다 정적으로 대조한 뒤
target 만 macos-x64 로 바꿔 쓴다. 칸마다 무엇으로 대조하는가(하나라도 안 맞으면 rc 2 = 재료 0 · fail-closed):

  release_seq·build_id  x64 Mach-O 바이트 안 빌드 표지 `cysr-buildmark:seq=<n>;build_id=<id>;version=<v>;pack=<sha256>;`(src/update/buildinfo.rs
                        BUILD_MARK)가 **정확히 1번** · 그 글자가 arm64 값과 글자 그대로 같음. 0번(옛 판 · 표지 없음)·2번 이상 = 거부.
                        seq 0(미발행 개발 빌드) = 거부 · build_id 의 -dirty = 거부. 표지의 version(1.1.21 N med1) = 아래 version 칸 값.
  bundled_pack.digest   build_id 앞 12자 커밋 트리에서 build.rs 와 같은 규칙(cysjavis-pack/ 추적 파일 · 점·tests·__pycache__
                        제외 · 바이트 정렬)으로 `rel\\0content\\0` sha256 을 다시 계산 = arm64 값(src/pack.rs pack_items_sha256 식)
                        = x64 표지 pack(1.1.21 N med2 · 빌드 때 build.rs 가 같은 식으로 박은 값 = 정본 결속)
                        + 그 팩 파일 내용이 x64 바이트 안에 순서대로 이어짐(보조 · pack_chain_missing · 심볼릭 링크 거부).
  keyring_ids           그 커밋의 cysjavis-pack/trusted-keys.json 바이트가 x64 바이트 안에 있음 + 그 파일에서 pack 아닌 용도
                        `용도:key_id` 를 파일 순서로 다시 만든 목록 = arm64 값(src/update/keys.rs from_trusted_keys_json·key_ids).
  version               그 커밋 Cargo.toml [package] version = arm64 값 = bundled_pack.version = x64 표지 version.
  features·trash        코드 상수(FEATURES = 빈 목록 · 맥 = 휴지통 삭제 true · cfg 차이는 windows 갈래뿐) — arm64 값이 그 상수와 같아야 함.

사용: collect_x64_static.py --bin <x64 Mach-O> --from <arm64 build-info.json> --repo <저장소> --out <출력 json>
종료: 0 = 출력 씀 · 2 = 거부(이유 = stderr 한 줄 이상).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys

MARK = b"cysr-buildmark:"
MARK_RE = re.compile(rb"cysr-buildmark:seq=([0-9]+);build_id=([0-9A-Za-z.\-]+);version=([0-9A-Za-z.+\-]+);pack=([0-9a-f]{64});")
BUILD_ID_RE = re.compile(r"^[0-9a-f]{12}\.[0-9]{8}T[0-9]{4}Z$")
PURPOSES = {"root", "release", "feed", "win-asset", "pack"}


def refuse(msg):
    print("collect-x64: 거부 — " + msg, file=sys.stderr)
    sys.exit(2)


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        refuse("git %s 실패: %s" % (" ".join(args), r.stderr.decode(errors="replace").strip()[:200]))
    return r.stdout


def pack_items(repo, commit):
    """build.rs 와 같은 집합·순서 — (rel, 바이트)."""
    items = []
    for rec in git(repo, "ls-tree", "-r", "-z", "--full-tree", commit, "--", "cysjavis-pack").split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, typ, oid = meta.split(b" ")
        rel = path.decode("utf-8")[len("cysjavis-pack/"):]
        if any(c.startswith(".") or c in ("tests", "__pycache__") for c in rel.split("/")):
            continue
        if typ != b"blob":
            refuse("팩 트리에 blob 아닌 항목: " + rel)
        if mode == b"120000":  # 1.1.21 N med2: 심볼릭 링크도 typ 은 blob 이다 — 내용(가리키는 경로 글자)으로 대조하지 않는다
            refuse("팩 트리에 심볼릭 링크 항목: " + rel)
        items.append((rel, oid.decode()))
    items.sort(key=lambda x: x[0].encode("utf-8"))
    return [(rel, git(repo, "cat-file", "blob", oid)) for rel, oid in items]


def pack_chain_missing(blob, items):
    """팩 내용이 x64 바이트 안에 **순서대로 · 겹치지 않게 · 앞 항목 끝 뒤 창(len + 64KiB) 안에** 이어지는 사슬이 하나라도
    있는가 — 없으면 사슬이 끊긴 첫 항목 rel(목록 1개) · 있으면 빈 목록. ★보조 대조다: 팩 내용의 정본 결속은 표지의
    pack digest(빌드 때 build.rs 가 박음 = 1.1.21 N med2)이고, 이 사슬은 그 digest 대로의 바이트가 바이너리에 실제로
    실렸는지(include_str! 원문)를 본다.

    1.1.21 N med2(agy · codex N 1R): 전에는 앞 항목 끝 근처에서 못 찾으면 맨 앞(오프셋 0)부터 다시 찾았다(뒤 파일이 깨져도
    앞쪽 같은 바이트에 걸려 통과) · 다시 찾기 없음 + 「가장 이른 출현 하나만」 으로 고르면 앞쪽 다른 사본에 걸려 정상
    배치를 거짓 거부한다(codex 반례) → 출현 자리를 모두 들고 가는 사슬(도달 가능한 끝 자리 집합). 첫 항목만 바이너리 전체
    (실물 1.1.19·1.1.20 x64 = 첫 항목이 약 8.7MB 뒤 · PACK_ALL 은 const 라 사본이 여럿 · 팩 589항목 모두 2번 이상 · 실측
    2026-11-27). 빈 파일 = 찾을 바이트 없음(건너뜀 · digest 가 결속). 겹치는 창은 합쳐 출현마다 한 번만 열고, 한 항목의
    출현 자리가 4096 을 넘으면 즉시 거부한다(병적 입력의 시간·메모리 상한 · fail-closed · codex N 2R minor)."""
    cap, ends, seen = 4096, None, set()
    for rel, data in items:
        if not data:
            continue
        new = []
        if ends is None:
            spans = [(0, len(blob))]
        else:
            # 앞 끝 자리 p 마다 시작 자리 허용 구간 = [p, p + 64KiB] — 겹치는 구간을 합쳐 출현마다 한 번만 연다(codex N 2R minor)
            spans = []
            for p in ends:
                if spans and p <= spans[-1][1]:
                    spans[-1] = (spans[-1][0], max(spans[-1][1], p + 65536))
                else:
                    spans.append((p, p + 65536))
        for lo, hi in spans:
            i = blob.find(data, lo, min(len(blob), hi + len(data)))
            while i >= 0 and i <= hi:
                new.append(i + len(data))
                if len(new) > cap:  # 병적 입력(짧은 공통 내용 · 큰 바이너리) = 판정 불가 → 거부(fail-closed · 시간·메모리 상한)
                    return [rel + " (출현 자리 %d 초과 · 판정 불가)" % cap]
                i = blob.find(data, i + 1, min(len(blob), hi + len(data)))
        if not new:
            return [rel + (" (앞 항목과 같은 내용)" if data in seen else "")]
        ends = sorted(set(new))
        seen.add(data)
    return []


def keyring_ids(raw):
    ids = []
    for k in json.loads(raw.decode("utf-8")).get("keys", []):
        p = k.get("purpose", "pack")
        if p not in PURPOSES:
            refuse("키링 purpose 미지 값: %r" % p)
        if p != "pack":
            ids.append("%s:%s" % (p, k.get("key_id")))
    return ids


def cargo_version(raw):
    in_pkg = False
    for line in raw.decode("utf-8").splitlines():
        s = line.strip()
        if s.startswith("["):
            in_pkg = s == "[package]"
            continue
        m = re.match(r'^version\s*=\s*"([^"]+)"', s)
        if in_pkg and m:
            return m.group(1)
    refuse("Cargo.toml [package] version 을 못 읽었다")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    try:
        bi = json.load(open(a.src, encoding="utf-8"))
    except (OSError, ValueError) as e:
        refuse("arm64 build-info 를 못 읽었다: %s" % e)
    if bi.get("target") != "macos-arm64":
        refuse("입력 build-info 의 target 이 macos-arm64 가 아니다: %r" % bi.get("target"))
    seq, bid = bi.get("release_seq"), bi.get("build_id")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
        refuse("arm64 release_seq 가 1 이상 정수가 아니다(미발행 개발 빌드?): %r" % seq)
    if not isinstance(bid, str) or not BUILD_ID_RE.match(bid):
        refuse("arm64 build_id 형식(<커밋12>.<UTC분> · -dirty 거부): %r" % bid)
    blob = open(a.bin, "rb").read()
    n = blob.count(MARK)
    if n != 1:
        refuse("x64 바이너리 안 빌드 표지가 %d번이다(0 = 표지 없는 옛 판 · 2+ = 모호) — 정확히 1번이어야 한다" % n)
    m = MARK_RE.match(blob, blob.index(MARK))
    if not m:
        refuse("x64 빌드 표지가 닫힌 꼴(seq=…;build_id=…;version=…;pack=…;)이 아니다")
    if m.group(1).decode() != str(seq):
        refuse("x64 표지 seq=%s ≠ arm64 release_seq %d" % (m.group(1).decode(), seq))
    if m.group(2).decode() != bid:
        refuse("x64 표지 build_id=%s ≠ arm64 build_id %s" % (m.group(2).decode(), bid))
    commit = git(a.repo, "rev-parse", "--verify", "--quiet", bid[:12] + "^{commit}").decode().strip()
    items = pack_items(a.repo, commit)
    h = hashlib.sha256()
    for rel, data in items:
        h.update(rel.encode("utf-8") + b"\0" + data + b"\0")
    bp = bi.get("bundled_pack") or {}
    if h.hexdigest() != bp.get("digest"):
        refuse("커밋 %s 팩 다시 계산 digest %s ≠ arm64 %s" % (commit[:12], h.hexdigest(), bp.get("digest")))
    if m.group(4).decode() != h.hexdigest():  # 1.1.21 N med2: 팩 내용의 정본 결속(빌드 때 build.rs 가 박은 digest)
        refuse("x64 표지 pack=%s ≠ 커밋 %s 팩 다시 계산 digest %s" % (m.group(4).decode(), commit[:12], h.hexdigest()))
    missing = pack_chain_missing(blob, items)
    if missing:
        refuse("x64 바이너리에 커밋 팩 내용이 없다 %d건(첫: %s)" % (len(missing), ", ".join(missing[:3])))
    kr = git(a.repo, "show", commit + ":cysjavis-pack/trusted-keys.json")
    if kr not in blob:
        refuse("x64 바이너리에 커밋 trusted-keys.json 바이트가 없다")
    if keyring_ids(kr) != bi.get("keyring_ids"):
        refuse("커밋 키링으로 만든 keyring_ids %r ≠ arm64 %r" % (keyring_ids(kr), bi.get("keyring_ids")))
    ver = cargo_version(git(a.repo, "show", commit + ":Cargo.toml"))
    if bi.get("version") != ver or bp.get("version") != ver or m.group(3).decode() != ver:
        refuse("version: 커밋 Cargo.toml %s · arm64 %r · bundled_pack %r · x64 표지 %s"
               % (ver, bi.get("version"), bp.get("version"), m.group(3).decode()))
    if bi.get("features") != [] or bi.get("trash_delete_supported") is not True:
        refuse("features(빈 목록 상수)·trash_delete_supported(맥 true 상수) 가 코드 상수와 다르다: %r %r"
               % (bi.get("features"), bi.get("trash_delete_supported")))
    out = dict(bi, target="macos-x64")
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print("collect-x64: 정적 대조 통과 — 표지 1 · seq %d · build_id %s · 팩 %d항목 · 키 %d" % (seq, bid, len(items), len(out["keyring_ids"])))


if __name__ == "__main__":
    main()
