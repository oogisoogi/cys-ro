#!/usr/bin/env python3
"""v115r4_dbg_mutants.py — TICKET=v115r4-dbg(10차 통합) 수리 3건의 뮤테이션 검산.

대상: D1 #1(부서 사전확인 alive) · D1 #2(편성 서브셸 fd 절단) · D2 R2(등록 경로 resume 핀 추종) ·
      R12(좌석 exec 전 프로필 배선).
각 뮤턴트: 정확히 1곳 치환(건수 assert) → 그 결함의 시험 명령 → **종료코드**로 판정 → finally 원복.
어휘: KILLED=적색(잡음 · 실패한 시험 이름 병기) · SURVIVED=공허 · NOT-APPLIED=변이 미적용 ·
      CRASH=컴파일·문법 실패(측정 무효 — 실패와 같은 급).
exit: 0=대조군 초록 ∧ 전 뮤턴트 KILLED · 1=SURVIVED 있음 · 2=측정 실패.
사용: python3 scripts/v115r4_dbg_mutants.py [뮤턴트 이름 접두 …]   (인자 없으면 전부)
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARGO = os.environ.get("CARGO", os.path.expanduser("~/.cargo/bin/cargo"))
DEPT = "cysjavis-pack/bin/cys-dept"
USAGE = "src/bin/cysd/usage.rs"
STATE = "src/bin/cysd/state.rs"
PF = "cysjavis-pack/bin/javis_preflight.py"
PY_D1 = [sys.executable, "cysjavis-pack/bin/tests/test_d1_dept_ready_probe.py"]
CG_D2 = [CARGO, "test", "--bin", "cysd", "dbg_d2"]
CG_R12 = [CARGO, "test", "--bin", "cysd", "dbg_r12"]

MUTANTS = [
    # (이름, 파일, 찾을 문자열(정확히 1곳), 바꿀 문자열, 시험 명령)
    ("D1-1a-launch-사전확인을-ready로", DEPT,
     '    if alive "$sock"; then\n      echo "[cys-dept] $name 이미 가동 중 — 재사용"\n',
     '    if ready "$sock"; then\n      echo "[cys-dept] $name 이미 가동 중 — 재사용"\n', PY_D1),
    ("D1-1b-create-사전확인을-ready로", DEPT,
     '    if alive "$sock"; then echo "[cys-dept] $name 이미 가동 — 재사용" >&2; _spawned=0\n',
     '    if ready "$sock"; then echo "[cys-dept] $name 이미 가동 — 재사용" >&2; _spawned=0\n', PY_D1),
    ("D1-2-편성-서브셸-fd-상속-복귀", DEPT,
     ' ) </dev/null >/dev/null 2>&1 &\n', ' ) &\n', PY_D1),
    ("D2-1-등록경로-추종-제거", USAGE,
     "        if pin.is_none() || !heuristic {\n", "        if pin.is_none() {\n", CG_D2),
    ("D2-2-교체-쓰기-무력화", USAGE,
     "                if pin.as_deref() != Some(sid.as_str()) {\n",
     "                if pin.is_none() {\n", CG_D2),
    ("R12-1-exec-전-배선-호출-제거", STATE,
     "        wire_seat_profile_before_exec(self, &builder, id, env);\n",
     "        let _ = (&builder, env); // 뮤턴트: 선실행 제거\n", CG_R12),
    ("R12-2-좌석-config-dir-미생성", PF,
     "    if ccd and not os.path.isdir(ccd) and _discover_isolation_block()[0] is None:\n",
     "    if False:\n", CG_R12),
    ("R12-3-C29(dept-by-chat)-배선-누락", PF,
     "    for fn in (pf.c26_video_creator, pf.c27_appbuild, pf.c29_harness_engineering):\n",
     "    for fn in (pf.c26_video_creator, pf.c27_appbuild):\n", CG_R12),
]


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, errors="replace")
    return r.returncode, r.stdout + r.stderr


# 컴파일·문법 실패는 「시험이 잡았다」가 아니다 — 측정 무효(CRASH)로 따로 센다(공짜 KILLED 배제).
CRASH_MARKS = ("could not compile", "error[E", "SyntaxError", "IndentationError")


def evidence(out):
    """적색 귀속 근거 1줄 — 실패한 시험 이름(cargo) 또는 FAIL/ERROR 줄(unittest)."""
    for ln in out.splitlines():
        t = ln.strip()
        if (t.startswith("test ") and t.endswith("FAILED")) or t.startswith(("FAIL:", "ERROR:")):
            return t[:160]
    return "(근거 줄 없음)"


def main():
    sel = sys.argv[1:]
    todo = [m for m in MUTANTS if not sel or any(m[0].startswith(s) for s in sel)]
    # 대조군: 쓰이는 시험 명령마다 적용본 초록이어야 한다(아니면 측정 실패).
    for cmd in {tuple(m[4]) for m in todo}:
        rc, _ = run(list(cmd))
        print("CONTROL %s rc=%d → %s" % (" ".join(cmd[-2:]), rc, "GREEN" if rc == 0 else "RED(측정 실패)"),
              flush=True)
        if rc != 0:
            return 2
    bad = 0
    for name, rel, old, new, cmd in todo:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as f:
            orig = f.read()
        n = orig.count(old)
        if n != 1:
            print("%s: NOT-APPLIED(count=%d)" % (name, n), flush=True)
            bad = 2
            continue
        mode = os.stat(path).st_mode
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(orig.replace(old, new))
            with open(path, encoding="utf-8") as f:
                assert f.read().count(new) >= 1, "변이 적용 확인 실패"
            rc, out = run(cmd)
            if rc != 0 and any(m in out for m in CRASH_MARKS):
                v = "CRASH(측정 무효)"
                bad = 2
            else:
                v = "KILLED" if rc != 0 else "SURVIVED"
                if v == "SURVIVED" and bad == 0:
                    bad = 1
            print("%s: rc=%d %s · %s" % (name, rc, v, evidence(out) if rc else "-"), flush=True)
        finally:
            with open(path, "w", encoding="utf-8") as f:
                f.write(orig)
            os.chmod(path, mode)
        with open(path, encoding="utf-8") as f:
            assert f.read() == orig, "원복 실패: " + rel
    print("원복 확인: 대상 파일 바이트 동일", flush=True)
    return bad


if __name__ == "__main__":
    sys.exit(main())
