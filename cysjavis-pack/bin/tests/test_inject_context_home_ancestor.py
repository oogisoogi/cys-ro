#!/usr/bin/env python3
"""ctx-home-ancestor(1.1.11 · master 실측 2026-10-30) — 작업기억 상향탐색이 루트($HOME·CYS_ROOT) 자신에 오르지 않는다.

실측 결함: master(cmux · cwd ~/axdev · 자기 _round 없음)의 복원에 `~/_round/SESSION_STATE.md`(본부 좌석 699 의 기억)가
「작업기억(L2)」으로 실렸다. 같은 경로로 $HOME 아래 _round 없는 모든 프로젝트 세션이 본부 기억을 받았고, lead master 가
그런 cwd 에서 뜨면 javis_session adopt 가 그 본문을 자기 정본(팩 round/)으로 **복사**했다(영속 오염).

잠그는 것(좌석 형상 × 실린 STATE)
  H1 본부 좌석 cwd == $HOME → $HOME/_round (자기 기억 · 종전 그대로)
  H2 $HOME/projA (_round 있음) → projA/_round
  H3 $HOME/projA/sub → projA/_round (루트 아래 프로젝트 안 상향 발견은 그대로)
  H4 $HOME/projB (_round 없음) → 본부 기억 0 · 「미발견」
  H5 cys 밖 claude(역할·surface 없음) · cwd $HOME/axdev → 본부 기억 0
  H6 CYS_ROOT=<r> · cwd <r>/projC → <r>/_round 0
  H7 lead master · cwd $HOME/projB · 정본 골격 → 본부 기억 주입 0 · 정본에 복사 0
  H8 루트 밖 cwd(/outside/x/sub, 상위에 _round) → 종전 그대로 상향 발견
  H9 ACTIVE_PROJECT 폴백(명시 포인터)은 그대로 산다
  P1~P3 python 쌍둥이 legacy_candidates 같은 경계
  K1~K3 _ic_pkey: MSYS 에서만 `C:\\…`·`C:/…`·`/c/…`·`/d/…` 를 같은 키로 · POSIX 는 대소문자 보존(codex 1R)
  P4~P5 root_key(python 쌍둥이 키) 같은 규칙(codex 1R major)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(HERE)
PACK_SRC = os.path.dirname(BIN)
HOOKS = os.path.join(PACK_SRC, "hooks")
HOOK = os.path.join(HOOKS, "inject-context.sh")
sys.path.insert(0, BIN)
import javis_session as JS  # noqa: E402

BASH = shutil.which("bash") or "/bin/bash"
PY = sys.executable
fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + str(detail)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


SKEL = read(os.path.join(PACK_SRC, "round", "SESSION_STATE.md"))
HQ = "# HOME-HQ-STATE 본부 좌석 기억\n"


def main():
    root = os.path.realpath(tempfile.mkdtemp(prefix="icha.", dir=os.environ.get("TMPDIR") or None))
    H = os.path.join(root, "home")
    PK = os.path.join(H, ".cys", "pack")
    os.makedirs(os.path.join(PK, "bin"))
    shutil.copy2(os.path.join(BIN, "javis_session.py"), os.path.join(PK, "bin", "javis_session.py"))
    canon = os.path.join(PK, "round", "SESSION_STATE.md")
    write(canon, SKEL)
    write(os.path.join(H, "_round", "SESSION_STATE.md"), HQ)
    write(os.path.join(H, "projA", "_round", "SESSION_STATE.md"), "# PROJA-STATE\n")
    for d in (("projA", "sub"), ("projB",), ("axdev",)):
        os.makedirs(os.path.join(H, *d))
    CR = os.path.join(root, "croot")
    write(os.path.join(CR, "_round", "SESSION_STATE.md"), "# CROOT-STATE\n")
    os.makedirs(os.path.join(CR, "projC"))
    OUT = os.path.join(root, "outside", "x")
    write(os.path.join(OUT, "_round", "SESSION_STATE.md"), "# OUTSIDE-STATE\n")
    os.makedirs(os.path.join(OUT, "sub"))

    def run(cwd, role="worker", surface="7", extra=None):
        env = {"PATH": "/usr/bin:/bin", "HOME": H, "TMPDIR": root, "CYS_PY": PY, "LANG": "C.UTF-8",
               "CYS_BIN": os.path.join(root, "no-cys"), "CYS_NO_AUTOSTART": "1", "CYS_PACK_DIR": PK}
        if role is not None:
            env["CYS_ROLE"] = role
        if surface is not None:
            env["CYS_SURFACE_ID"] = surface
        env.update(extra or {})
        r = subprocess.run([BASH, HOOK], input=json.dumps({"source": "startup", "cwd": cwd}),
                           capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
        m = re.search(r"\(출처: ([^)]*)\)", r.stdout)
        return (m.group(1) if m else ""), r.stdout

    src, o = run(H)
    check("H1 본부 좌석 cwd==$HOME → 자기 기억", src == os.path.join(H, "_round", "SESSION_STATE.md")
          and "HOME-HQ-STATE" in o, o[-800:])
    src, o = run(os.path.join(H, "projA"))
    check("H2 프로젝트 _round", src == os.path.join(H, "projA", "_round", "SESSION_STATE.md"), o[-800:])
    src, o = run(os.path.join(H, "projA", "sub"))
    check("H3 프로젝트 하위 폴더 → 프로젝트 _round(상향 발견 유지)",
          src == os.path.join(H, "projA", "_round", "SESSION_STATE.md"), o[-800:])
    src, o = run(os.path.join(H, "projB"))
    check("H4 _round 없는 프로젝트 → 본부 기억 0", src == "" and "HOME-HQ-STATE" not in o, src)
    check("H4b 「미발견」 안내", "작업기억 미발견" in o, o[-800:])
    src, o = run(os.path.join(H, "axdev"), role=None, surface=None)
    check("H5 cys 밖 claude 세션 → 본부 기억 0", src == "" and "HOME-HQ-STATE" not in o, src)
    src, o = run(os.path.join(CR, "projC"), extra={"CYS_ROOT": CR})
    check("H6 CYS_ROOT 하위 → 루트 _round 0", src == "" and "CROOT-STATE" not in o, src)
    write(canon, SKEL)
    src, o = run(os.path.join(H, "projB"), role="master")
    check("H7 lead master(타 프로젝트) → 본부 기억 주입 0", "HOME-HQ-STATE" not in o, o[-800:])
    check("H7b lead master → 정본에 본부 기억 복사 0", read(canon) == SKEL)
    src, o = run(os.path.join(OUT, "sub"))
    check("H8 루트 밖 cwd 는 종전 상향탐색", src == os.path.join(OUT, "_round", "SESSION_STATE.md"), o[-800:])
    write(os.path.join(H, "_round", "ACTIVE_PROJECT"), os.path.join(H, "projA") + "\n")
    src, o = run(os.path.join(H, "projB"))
    check("H9 ACTIVE_PROJECT 폴백 유지", src == os.path.join(H, "projA", "_round", "SESSION_STATE.md")
          and "ACTIVE_PROJECT fallback" in o, o[-800:])
    os.remove(os.path.join(H, "_round", "ACTIVE_PROJECT"))

    # ── python 쌍둥이 ──
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = H
    try:
        check("P1 legacy_candidates: _round 없는 프로젝트 → 본부 후보 0",
              JS.legacy_candidates(os.path.join(H, "projB"), H) == [])
        check("P2 legacy_candidates: cwd==HOME 은 자기 _round",
              JS.legacy_candidates(H, H) == [os.path.join(H, "_round", "SESSION_STATE.md")])
        check("P3 legacy_candidates: root 경계(CYS_ROOT)",
              JS.legacy_candidates(os.path.join(CR, "projC"), CR) == []
              and JS.legacy_candidates(os.path.join(H, "projA", "sub"), H)
              == [os.path.join(H, "projA", "_round", "SESSION_STATE.md")])
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home

    # ── 키 함수(훅 본문에서 그대로 떼어 실행 — 사본을 만들지 않는다) ──
    src_txt = read(HOOK)
    m = re.search(r"^  _ic_pkey\(\) \{\n.*?^  \}\n", src_txt, re.S | re.M)
    check("K0 훅에 _ic_pkey 정의 실재", bool(m))
    check("K0b 훅이 MSYS 판별(cygpath)로 키 규칙을 가른다", '_IC_MSYS=""; command -v cygpath' in src_txt)
    if m:
        def keys(msys, *paths):
            probe = '_IC_MSYS="%s"\n' % msys + m.group(0) + 'for p in "$@"; do printf "%s|" "$(_ic_pkey "$p")"; done'
            r = subprocess.run([BASH, "-c", probe, "_"] + list(paths), capture_output=True, text=True, timeout=30)
            return r.stdout.split("|")[:len(paths)]
        got = keys("1", "C:\\Users\\X", "C:/Users/X/", "/c/Users/X", "/d/CYS", "D:/CYS")
        check("K1 MSYS: Windows 세 표기 같은 키", got[0] == got[1] == got[2] == "c:/users/x", got)
        check("K1b MSYS: /d/CYS == D:/CYS (codex 1R 재현)", got[3] == got[4] == "d:/cys", got)
        got = keys("", "/Users/x/", "/", "/a/Person", "/A/Person")
        check("K2 POSIX: 꼬리 / 만 제거 · 루트 / 는 빈 키", got[0] == "/Users/x" and got[1] == "", got)
        check("K3 POSIX: 대소문자 보존 — /a/Person != /A/Person (codex 1R 재현)",
              got[2] == "/a/Person" and got[3] == "/A/Person", got)

    # ── python 쌍둥이 키(root_key) — 같은 규칙 ──
    check("P4 root_key(nt): /d/CYS == D:/CYS == D:\\CYS\\ (codex 1R major 재현)",
          JS.root_key("/d/CYS", nt=True) == JS.root_key("D:/CYS", nt=True) == JS.root_key("D:\\CYS\\", nt=True))
    check("P5 root_key(posix): 대소문자 보존 · 꼬리 / 제거",
          JS.root_key("/a/Person", nt=False) != JS.root_key("/A/Person", nt=False)
          and JS.root_key("/a/Person/", nt=False) == "/a/Person")

    shutil.rmtree(root, ignore_errors=True)
    print("\n=== %s ===" % ("ALL PASS" if not fails else "FAIL %d: %s" % (len(fails), fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
