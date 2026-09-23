#!/usr/bin/env python3
"""dbg-D3 D11 검출 시험 — 부서 팩 preflight --fix 가 공유 계정(본부) 프로필의 본부 훅을 덮지 않는가.

결함(2026-09-23 971 VM 실측 · 증거 reports/cysr-115-2026-09-22/vm-verify-r2/logs/d11-hook/):
기본 공유 계정 모드에서 부서 좌석의 CYS_ACCOUNT_DIR = 본부 ~/.cys/claude 다. 부서 팩 컨텍스트
preflight(C28 등 등록기)가 그 settings.json 을 「자기 account dir」로 좁혀 등록하고,
`_prune_stale_hook_entries` 가 레거시 루트 `/.cys/` 규칙으로 본부 `~/.cys/pack/hooks/*` 를 옛 항목으로
지운 뒤 부서 경로로 갈아 끼운다 → 본부 dept-chat-inject 소실 → 두 번째 부서부터 「네」 확인 정지.

재는 법(라이브 무접촉 · 실행 0 외부 명령): 임시 HOME 에 팩 두 벌(본부 `.cys/pack` · 부서
`.cys/pack-dept-dept-9` — 둘 다 저장소 팩을 가리키는 심링크)과 본부 프로필(`.cys/claude/settings.json`)을
만들고 ①본부 컨텍스트로 C28 --fix(본부 훅 등록) ②부서 컨텍스트(공유 계정)로 C28 --fix 를 돈 뒤 대조한다.
  축 A = ①의 본부 훅 집합 ⊆ ②뒤 집합(본부 항목 제거 금지)
  축 B = 본부 dept-chat-inject 가 ②뒤에도 실재
  축 C(회귀) = 부서 전용 계정(포크 모드 · CYS_ACCOUNT_DIR basename 'dept-')이면 부서 훅이 **자기 프로필**에
          등록되고 본부 프로필은 바이트 무변경
측정 선단언: ①뒤 본부 훅이 1건 이상 · dept-chat-inject 포함(아니면 rc 2 — 초록으로 접지 않는다).
사용: `python3 <this> [--bin <javis_preflight.py 가 있는 폴더>]` · 0 초록 · 1 적색 · 2 측정 실패.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BIN = os.path.dirname(HERE)
REPO_PACK = os.path.dirname(DEFAULT_BIN)

RUNNER = r'''
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import javis_preflight as p
pf = p.Preflight(fix=True, skips=set(), mode="fix")
pf.c28_self_correction()
for r in getattr(pf, "results", []):
    print("RESULT", r)
'''


def hooks_of(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    out = set()
    for ev, arr in (d.get("hooks") or {}).items():
        for g in arr or []:
            for h in (g.get("hooks") or []):
                out.add((ev, g.get("matcher") or "", h.get("command", "")))
    return out


def run_c28(bin_dir, home, pack, acct):
    env = {"HOME": home, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "CYS_PACK_DIR": pack,
           "CYS_ACCOUNT_DIR": acct, "CYS_NO_AUTOSTART": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([sys.executable, "-c", RUNNER, bin_dir], env=env, capture_output=True,
                          text=True, timeout=120)


def main(argv):
    bin_dir = DEFAULT_BIN
    if len(argv) >= 2 and argv[0] == "--bin":
        bin_dir = argv[1]
    probe_root = os.path.join(os.path.dirname(REPO_PACK), ".probe")
    os.makedirs(probe_root, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=probe_root) as td:
        # ★임시팩 가드(`_path_under_tempdir`)가 /tmp·/var/folders 아래 팩의 등록을 막으므로 임시 HOME 을
        #   체크아웃 안(`<repo>/.probe/` · 미추적)에 만든다. 등록이 0 이면 측정 실패로 접는다(아래 선단언).
        home = os.path.join(td, "h")
        cys = os.path.join(home, ".cys")
        os.makedirs(cys)
        hq_pack = os.path.join(cys, "pack")
        dept_pack = os.path.join(cys, "pack-dept-dept-9")
        # ★(v115r4-dbg 통합 수정) 심링크 대신 사본 — 심링크면 `preflight --fix` 의 훅 실행비트 보강(chmod)이
        #   저장소 체크아웃 파일을 바꿔(pack-guard.sh·role-bootstrap-legacy.sh 100644→100755) 작업트리를
        #   오염시킨다. 판정 논리는 그대로(경로 모양 `/.cys/pack` · `/.cys/pack-dept-*` 동일).
        ign = shutil.ignore_patterns("tests", "__pycache__", "*.pyc")
        shutil.copytree(REPO_PACK, hq_pack, symlinks=True, ignore=ign)
        shutil.copytree(REPO_PACK, dept_pack, symlinks=True, ignore=ign)
        hq_acct = os.path.join(cys, "claude")
        os.makedirs(hq_acct)
        hq_settings = os.path.join(hq_acct, "settings.json")
        with open(hq_settings, "w", encoding="utf-8") as f:
            f.write("{}")
        r1 = run_c28(bin_dir, home, hq_pack, hq_acct)
        before = hooks_of(hq_settings)
        hq_dci = [h for h in before if h[2].endswith("/.cys/pack/hooks/dept-chat-inject.sh")]
        if not before or not hq_dci:
            print("MEASURE-FAIL: 본부 컨텍스트 등록이 0건이거나 dept-chat-inject 부재 — 시험이 대상에 안 닿았다")
            print(r1.stdout[-800:], r1.stderr[-800:])
            return 2
        hq_bytes = open(hq_settings, "rb").read()
        # ② 부서 컨텍스트 · 공유 계정(본부 프로필)
        r2 = run_c28(bin_dir, home, dept_pack, hq_acct)
        after = hooks_of(hq_settings)
        lost = sorted(before - after)
        okA = not lost
        okB = any(h[2].endswith("/.cys/pack/hooks/dept-chat-inject.sh") for h in after)
        print("[A] 본부 훅 %d건 중 부서 preflight 뒤 사라진 것 %d건 %s" % (len(before), len(lost),
              "PASS" if okA else "FAIL"))
        for x in lost[:6]:
            print("     - %s %s %s" % x)
        print("[B] 본부 dept-chat-inject 실재 %s" % ("PASS" if okB else "FAIL"))
        # ③ 회귀 — 부서 전용 계정(포크 모드)
        with open(hq_settings, "wb") as f:
            f.write(hq_bytes)
        fork_acct = os.path.join(cys, "claude-dept-9")
        os.makedirs(fork_acct)
        fork_settings = os.path.join(fork_acct, "settings.json")
        with open(fork_settings, "w", encoding="utf-8") as f:
            f.write("{}")
        r3 = run_c28(bin_dir, home, dept_pack, fork_acct)
        fork_hooks = hooks_of(fork_settings)
        okC = (open(hq_settings, "rb").read() == hq_bytes) and any(
            "/pack-dept-dept-9/hooks/" in h[2] for h in fork_hooks)
        print("[C] 포크 모드 = 부서 프로필 등록 %d건 · 본부 프로필 무변경 %s" % (len(fork_hooks),
              "PASS" if okC else "FAIL"))
        if not (okA and okB and okC):
            if not okC:
                print(r3.stdout[-600:], r3.stderr[-600:])
            print("FAIL(D11 재현)" if not (okA and okB) else "FAIL(포크 모드 회귀)")
            return 1
        print("PASS: 부서 preflight 가 공유(본부) 프로필의 본부 훅을 보존한다")
        return 0


if __name__ == "__main__":
    _rc = main(sys.argv[1:])
    try:  # 빈 `<repo>/.probe/` 잔재 정리(다른 실행이 쓰는 중이면 비어 있지 않아 그대로 둔다)
        os.rmdir(os.path.join(os.path.dirname(REPO_PACK), ".probe"))
    except OSError:
        pass
    sys.exit(_rc)
