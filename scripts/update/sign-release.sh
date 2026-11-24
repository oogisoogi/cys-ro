#!/usr/bin/env bash
# U 의식 — 릴리스 본문에 U(릴리스) 키로 서명한다(1.1.8 U3 · 설계 AUTO-UPDATE-118 §8 「U 의식 절차(📌11)」 ①~⑥).
#
# 절차(이 스크립트가 ②~⑥ 을 강제한다 · ① = scripts/update/make-release-json.py):
#   ① 빌드 기기에서 릴리스 본문 JSON 을 만든다(서명 없음).
#   ② 본문 파일만 서명 매체 쪽으로 옮긴다(본문은 공개 정보).
#   ③ U 개인키는 매체 안에서만 연다 — `--key` 가 `--media` 마운트 아래가 아니면 거부(복사·클립보드·셸 기록 0).
#   ④ 서명(.minisig)만 꺼낸다.
#   ⑤ 매체를 뺀다(박사님 손 1단계 · 기본 = 빠질 때까지 최대 300초 기다림).
#   ⑥ 내장 U 공개키(키링 purpose=release · 본문 key_id)로 검증해야 산출물이 생긴다 → 게시 단계(publish-archive.py).
#
# 사용:
#   scripts/update/sign-release.sh --body cysr-release-12.json --media /Volumes/CYS-U --key /Volumes/CYS-U/u.key \
#       [--keyring cysjavis-pack/trusted-keys.json] [--out-dir dist/update] [--wait-eject 300] [--expect-head <40자 sha>]
#   --expect-head(1.1.19 CO-L3 · L4): 이 스크립트가 든 저장소(ROOT)의 HEAD = 그 sha ∧ 작업트리가 HEAD 와 같아야 시작한다
#     (아니면 · git 작업트리가 아니면 = 거부 rc 2 · 매체에 손대기 전 · 산출 0). 안 주면 검사 0 = 1.1.18 과 같은 동작.
#     인자를 줬으면 값이 비었거나 없거나 두 번 줘도 거부(검사를 건너뛰지 않음 · codex 1R B1).
#     「같다」 = git 설정에 기대지 않는 네 겹(codex 1R B2): ① status 를 명령에서 고정(추적 안 된 파일 전부 · 하위 모듈 무시 0 ·
#     fsmonitor·untrackedCache 끔) ② 색인 표시(assume-unchanged·skip-worktree 등 · `ls-files -v` 의 H 아닌 줄) 0
#     ③ scripts/update/ 아래 추적 안 된 파일 0(무시 규칙과 무관 · __pycache__ 만 예외 — 아래 PYTHONPYCACHEPREFIX 로 읽지 않음)
#     ④ HEAD 트리의 추적 파일마다 작업 파일 바이트를 직접 해시해 대조(색인·stat·필터와 무관 · 다르면 git 내장 줄끝 변환으로만
#     풀어 봄 = 저장소 `*.nsh text eol=crlf` 같은 체크아웃 변환 · filter·ident·working-tree-encoding 속성이 걸린 파일은 풀지 않고 거부).
#     빌드 산출(target/ 등) 같은 다른 자리의 무시된 파일은 막지 않는다 — 서명 때 실행·읽히는 코드는 scripts/update/ 와 추적 파일뿐이다.
# 산출: <out-dir>/<component>-release-<seq>.json + .minisig (본문 바이트 그대로 · 서명은 파일 바이트 전체)
# 종료: 0 = 서명·검증 통과 · 2 = 거부(산출물 0)
# 시험: 이 스크립트는 손잡이 env 가 없다 — 시험은 사본 트리에서 lib/offline-sign-dev.sh(대역)를 함께 읽는다(3판 · 실키 0).
#   (개발 모드 밖에서 이 손잡이가 보이면 거부 · 개발 모드는 저장소 실 키링 key id 거부 — lib/offline-sign.sh)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck source=lib/offline-sign.sh
. "$HERE/lib/offline-sign.sh"

BODY="" MEDIA="" KEY="" KEYRING="$ROOT/cysjavis-pack/trusted-keys.json" OUT_DIR="." WAIT=300 EXPECT_HEAD="" EXPECT_HEAD_SET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --body) BODY="$2"; shift 2 ;;
    --media) MEDIA="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    --keyring) KEYRING="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --wait-eject) WAIT="$2"; shift 2 ;;
    --expect-head)
      [ "$EXPECT_HEAD_SET" = 0 ] || { echo "거부: --expect-head 를 두 번 줬다" >&2; exit 2; }
      [ $# -ge 2 ] || { echo "거부: --expect-head 에 값이 없다(40자 소문자 sha)" >&2; exit 2; }
      EXPECT_HEAD="$2"; EXPECT_HEAD_SET=1; shift 2 ;;
    *) echo "모르는 인자: $1" >&2; exit 2 ;;
  esac
done
[ -n "$BODY" ] && [ -n "$MEDIA" ] && [ -n "$KEY" ] || { echo "사용: --body <본문> --media <매체> --key <매체 안 u.key>" >&2; exit 2; }

# (1.1.19 CO-L3 · L4) 작업트리 검사 — 인자를 줬을 때만 · 닫힌 쪽(모르면 거부).
if [ "$EXPECT_HEAD_SET" = 1 ]; then
  case "$EXPECT_HEAD" in ""|*[!0-9a-f]*) echo "거부: --expect-head 는 40자 소문자 sha: $EXPECT_HEAD" >&2; exit 2 ;; esac
  [ "${#EXPECT_HEAD}" -eq 40 ] || { echo "거부: --expect-head 는 40자 소문자 sha: $EXPECT_HEAD" >&2; exit 2; }
  TOP="$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null)" || TOP=""
  [ -n "$TOP" ] && [ "$(cd "$TOP" && pwd -P)" = "$(cd "$ROOT" && pwd -P)" ] \
    || { echo "거부: --expect-head 인데 $ROOT 가 git 작업트리가 아니다(맨 위 폴더 아님 포함)" >&2; exit 2; }
  GOT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null)" || { echo "거부: HEAD 를 읽지 못했다: $ROOT" >&2; exit 2; }
  [ "$GOT" = "$EXPECT_HEAD" ] || { echo "거부: 작업트리 HEAD $GOT ≠ 기대 $EXPECT_HEAD" >&2; exit 2; }
  # ① 사용자 git 설정이 더러움을 숨기지 못하게 명령에서 고정(B2)
  DIRTY="$(git -C "$ROOT" -c core.fsmonitor=false -c core.untrackedCache=false -c status.showUntrackedFiles=all \
    status --porcelain --untracked-files=all --ignore-submodules=none 2>/dev/null)" || { echo "거부: git status 실패: $ROOT" >&2; exit 2; }
  [ -z "$DIRTY" ] || { echo "거부: 작업트리에 커밋 안 된 변경이 있다(git status --porcelain):" >&2; printf '%s\n' "$DIRTY" >&2; exit 2; }
  # ②③④ 색인 표시 · 서명 코드 자리의 추적 안 된 파일 · 바이트 == HEAD(B2)
  python3 -I -B - "$ROOT" "$EXPECT_HEAD" <<'PY' || exit 2
import hashlib, os, stat, subprocess, sys
root, head = sys.argv[1], sys.argv[2]
G = ["git", "-C", root, "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c", "core.quotePath=true"]
def git(*a):
    return subprocess.run(G + list(a), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout
def refuse(msg, items):
    print("거부: " + msg, file=sys.stderr)
    for x in items[:20]:
        print("  " + x, file=sys.stderr)
    if len(items) > 20:
        print("  … 외 %d" % (len(items) - 20), file=sys.stderr)
    sys.exit(2)
try:
    # ② assume-unchanged(소문자)·skip-worktree(S) 는 status 에서 변경을 숨긴다 → H(보통 추적) 아닌 표시가 하나라도 있으면 거부
    flagged = [r.decode(errors="replace") for r in git("ls-files", "-v", "-z").split(b"\0") if r and not r.startswith(b"H ")]
    if flagged:
        refuse("색인에 변경을 숨길 수 있는 표시가 있다(git ls-files -v 가 H 아님 · assume-unchanged/skip-worktree 등):", flagged)
    # ③ 서명 때 실행·import 되는 자리 — 무시 규칙(.gitignore·info/exclude·excludesFile)과 무관하게 추적 안 된 파일 전부
    others = [p.decode(errors="replace") for p in git("ls-files", "-z", "--others", "--", "scripts/update").split(b"\0") if p]
    others = [p for p in others if "__pycache__" not in p.split("/")]
    if others:
        refuse("서명 코드 자리(scripts/update/)에 추적 안 된 파일이 있다(무시된 파일 포함):", others)
    # ④ 추적 파일의 실제 바이트 == HEAD — 색인 표시·stat·필터와 무관하게 직접 해시
    fmt = git("rev-parse", "--show-object-format").decode().strip()
    if fmt not in ("sha1", "sha256"):
        refuse("알 수 없는 object format: " + fmt, [])
    H = getattr(hashlib, fmt)
    bad, conv = [], []
    for rec in git("ls-tree", "-r", "-z", "--full-tree", head).split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, _typ, oid = meta.split(b" ")
        name = path.decode(errors="replace")
        p = os.path.join(os.fsencode(root), path)
        if mode == b"160000":
            bad.append("하위 모듈(대조 불가) " + name)
            continue
        try:
            st = os.lstat(p)
            if mode == b"120000":
                if not stat.S_ISLNK(st.st_mode):
                    bad.append("심링크 아님 " + name)
                    continue
                data = os.readlink(p)
            else:
                if not stat.S_ISREG(st.st_mode):
                    bad.append("보통 파일 아님 " + name)
                    continue
                if (mode == b"100755") != bool(st.st_mode & 0o100):
                    bad.append("실행 권한 다름 " + name)
                    continue
                with open(p, "rb") as f:
                    data = f.read()
        except OSError:
            bad.append("없음 " + name)
            continue
        if H(b"blob %d\0" % len(data) + data).hexdigest().encode() != oid:
            conv.append((path, name, oid))
    # 바이트가 다른 보통 파일 = git 내장 줄끝 변환(저장소 .gitattributes 의 text·eol — 예: `*.nsh text eol=crlf`)만으로 풀릴 때만 깨끗.
    # 필터 드라이버(filter = 설정의 clean 명령)·ident·working-tree-encoding 이 걸린 파일은 풀어 주지 않는다(그 길로 변경을 씻어 숨길 수 있음).
    for path, name, oid in conv:
        attrs = git("check-attr", "-z", "filter", "ident", "working-tree-encoding", "--", name).split(b"\0")
        risky = [attrs[i + 1].decode() for i in range(0, len(attrs) - 2, 3) if attrs[i + 2] != b"unspecified"]
        if risky:
            bad.append("내용 ≠ HEAD %s(변환 속성 %s · 대조 불가)" % (name, ",".join(risky)))
            continue
        with open(os.path.join(os.fsencode(root), path), "rb") as f:
            got = subprocess.run(G + ["-c", "core.autocrlf=false", "-c", "core.safecrlf=false", "hash-object", "--path=" + name, "--stdin"],
                                 input=f.read(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout.strip()
        if got != oid:
            bad.append("내용 ≠ HEAD " + name)
    if bad:
        refuse("작업트리 파일이 HEAD 와 다르다(색인 표시와 무관한 바이트 해시 대조):", bad)
except subprocess.CalledProcessError as e:
    refuse("git 실행 실패: %s" % " ".join(str(x) for x in e.cmd[len(G):]), [])
PY
  # ③ 의 __pycache__ 예외가 안전하려면 그 자리를 읽지 않아야 한다 — 이 실행의 python 은 pyc 를 빈 임시 자리에서만 찾고 쓰지 않는다
  NOPYC="$(mktemp -d)" || { echo "거부: 임시 폴더를 만들지 못했다" >&2; exit 2; }
  trap 'rmdir "$NOPYC" 2>/dev/null' EXIT
  export PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$NOPYC"
fi

# 본문 서식 확인(생산자 검사) — kind·component·release_seq·key_id 를 읽는다.
META="$(python3 - "$HERE" "$BODY" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1])
import update_common as uc
b = json.load(open(sys.argv[2], encoding="utf-8"))
if b.get("kind") != uc.RELEASE_KIND or b.get("component") not in uc.COMPONENTS:
    print("거부: 릴리스 본문 서식 아님(kind/component)", file=sys.stderr); sys.exit(2)
if not isinstance(b.get("release_seq"), int) or b["release_seq"] < 1 or not uc.KEY_ID_RE.match(b.get("key_id") or ""):
    print("거부: release_seq/key_id 형식", file=sys.stderr); sys.exit(2)
try:
    uc.check_notes_ko(b.get("notes_ko"))
except uc.PublishError as e:
    print("거부: %s" % e, file=sys.stderr); sys.exit(2)
print(b["component"], b["release_seq"], b["key_id"])
PY
)" || exit 2
read -r COMP SEQ KID <<<"$META"

mkdir -p "$OUT_DIR"
OUT_BODY="$OUT_DIR/$COMP-release-$SEQ.json"
[ -e "$OUT_BODY" ] || [ -e "$OUT_BODY.minisig" ] && { echo "거부: 산출물이 이미 있다(덮어쓰기 0): $OUT_BODY" >&2; exit 2; }
DIGEST="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$BODY")"

if ! offline_sign release "$BODY" "$KEY" "$MEDIA" "$KEYRING" "$KID" "$OUT_BODY.minisig" \
     "$COMP-release seq=$SEQ sha256=$DIGEST" "$WAIT"; then
  exit 2
fi
cp "$BODY" "$OUT_BODY"
echo "✅ U 의식 통과 — $OUT_BODY(.minisig) · key $KID · 본문 sha256 $DIGEST"
