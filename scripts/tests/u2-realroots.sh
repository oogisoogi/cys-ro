#!/usr/bin/env bash
# U2 2판(codex 1R C17): 「실 ~/.cys 쓰기 0」 증명 = 두 실 루트(+ LaunchAgents · counsel)의 **전후 전수 메타데이터 대조**.
#   사용: bash scripts/tests/u2-realroots.sh <명령…>   (예: bash scripts/tests/u2-realroots.sh cargo test --lib)
#   ① 시작 전 목록(경로·종류·크기·mtime(ns)·권한) ② 명령 실행 ③ 끝난 뒤 목록 → 바뀐/생긴/사라진 경로 전수 출력.
#   판정: U2 이름공간(갱신 폴더 `~/.cys/update/**` · 복구기 plist · install_id · txn.* · journal* · hold-* · seats-stop · candidate ·
#   backup/ · installers/ · counsel/updates.jsonl) 변화 = 0 이어야 통과(rc 1). 그 밖의 변화는 **숨기지 않고 전부 적되**
#   이 기계의 살아 있는 데몬·다른 세션이 같은 시간에 쓴 것일 수 있어(대조군 = 같은 길이 무작업 창을 따로 재서 비교) 판정에 넣지 않는다.
set -u
[ $# -ge 1 ] || { echo "사용: $0 <명령…>" >&2; exit 2; }
ROOTS=("$HOME/.cys" "$HOME/.local/state/cys" "$HOME/Library/LaunchAgents")
OUT=${U2_REALROOTS_OUT:-$(mktemp -d /tmp/u2rr.XXXXXX)}
# ★후속(Fable 5R n15 · 5판 정직 고지 1): 지정 폴더가 없으면 만든다(5판 첫 전수 = 부재 → 목록 0 · rc 1 · 판정 무효였다) · 그래도 목록이 안
#   생기면 「판정 불가」 rc 2(U2 쓰기 rc 1 과 가른다).
mkdir -p "$OUT" || { echo "u2-realroots: 판정 불가 — 출력 폴더 $OUT 생성 실패" >&2; exit 2; }
list() { # $1 = 출력 파일
  python3 - "$1" "${ROOTS[@]}" <<'PY'
import os, sys, stat
out = open(sys.argv[1], "w")
for root in sys.argv[2:]:
    if not os.path.lexists(root):
        continue
    for dp, dns, fns in os.walk(root, followlinks=False):
        for n in dns + fns:
            p = os.path.join(dp, n)
            try:
                st = os.lstat(p)
            except FileNotFoundError:
                continue
            k = "l" if stat.S_ISLNK(st.st_mode) else ("d" if stat.S_ISDIR(st.st_mode) else "f")
            size = 0 if k == "d" else st.st_size
            mt = 0 if k == "d" else st.st_mtime_ns
            out.write(f"{p}\t{k}\t{size}\t{mt}\t{oct(st.st_mode & 0o7777)}\n")
PY
  sort -o "$1" "$1"
}
list "$OUT/before.tsv"
[ -f "$OUT/before.tsv" ] || { echo "u2-realroots: 판정 불가 — 시작 전 목록 없음($OUT)" >&2; exit 2; }
start=$(date +%s)
"$@"
rc=$?
list "$OUT/after.tsv"
[ -f "$OUT/after.tsv" ] || { echo "u2-realroots: 판정 불가 — 끝난 뒤 목록 없음($OUT)" >&2; exit 2; }
python3 - "$OUT/before.tsv" "$OUT/after.tsv" "$OUT" <<'PY'
import sys, re, os
def load(p):
    d = {}
    for line in open(p):
        path, *rest = line.rstrip("\n").split("\t")
        d[path] = tuple(rest)
    return d
b, a, out = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
home = os.path.expanduser("~")
# ★3판(Fable 2R m5): 상담소 신호(notify::signal → javis_counsel 대기열)도 U2 쓰기 — counsel 폴더 전체를 U2 이름공간에
u2 = re.compile(r"^(%s/\.cys/update(/|$)|.*cysr-update-recover|.*/counsel(/|$))" % re.escape(home))
changed = sorted(p for p in set(a) | set(b) if a.get(p) != b.get(p))
hits = [p for p in changed if u2.match(p)]
with open(os.path.join(out, "changed.txt"), "w") as f:
    for p in changed:
        tag = "U2" if u2.match(p) else "그 밖"
        f.write(f"{tag}\t{'생김' if p not in b else ('사라짐' if p not in a else '바뀜')}\t{p}\n")
print(f"u2-realroots: 대상 {len(b)}→{len(a)} 항목 · 바뀜·생김·사라짐 {len(changed)} · U2 이름공간 {len(hits)} · 목록 {out}/changed.txt")
for p in hits:
    print(f"  U2 쓰기: {p}")
sys.exit(1 if hits else 0)
PY
verdict=$?
echo "u2-realroots: 명령 rc=$rc · 경과 $(( $(date +%s) - start ))s · 판정 rc=$verdict(0 = U2 이름공간 실 쓰기 0)"
[ $rc -eq 0 ] && [ $verdict -eq 0 ]
