#!/usr/bin/env python3
"""test_py_resolver_clt_stub.py — 훅 프리루드 파이썬 해소기의 macOS CLT 스텁 배제 핀 (cysr-102-pack-c).

결함(1.0.2 VM 실기 적발): 개발자 도구(CLT)가 없는 맥에서 `/usr/bin/python3` 는 실체 없는 스텁이다.
실행하면 설치 창을 띄우고 rc 1·무출력으로 끝난다. 종전 `cys_resolve_py` 는 `command -v python3`
첫 후보를 그대로 채택해, 에이전트 PATH 에서 /usr/bin 이 앞이면 스텁을 골랐고 CYS_PY 를 쓰는 훅이
전부 조용히 실패했다. guard.sh·actprobe-kill-gate.sh 는 각자 같은 후보 루프를 갖고 있었다.

하네스: 가짜 루트(CYS_TEST_SYSROOT)에 `usr/bin/python3` 스텁(**실행되면 표식 파일을 남긴다**) ·
`usr/bin/xcode-select`(CLT 유무 흉내) · 앱 번들 파이썬을 두고, PATH 앞에 가짜 `uname` 을 둬
Darwin/Linux 를 흉내 낸다. 실제 /usr/bin 은 PATH 에 넣지 않는다(호스트 실파이썬 오채택 차단).
축:
  ⓐ 스텁은 해소 과정에서 **한 번도 실행되지 않는다**(전 케이스 공통 단언)
  ⓑ 맥: 앱 번들 파이썬 > PATH 후보 · PATH 의 cys 실체가 든 번들 > 고정 설치 위치
  ⓒ 맥: 스텁은 PATH·CYS_PY·절대경로 꼬리 어디서 와도 제외 · CLT 가 있으면 /usr/bin/python3 는 정상 후보
  ⓓ 유효한 CYS_PY 는 존중(번들이 있어도)
  ⓔ 전부 부재 = 빈 값·rc 1(각 훅의 기존 부재 분기 그대로)
  ⓕ 비맥: 해소 결과가 수정 전 해소기(base 판 원문)와 문자열까지 같다(번들·스텁 판정 무관)
  ⓖ guard.sh: 스텁만 있으면 STRICT deny·LOOSE 백스톱(종전 스텁-크래시와 같은 결말) · 번들 있으면 파서 판정
  ⓗ actprobe-kill-gate.sh: 스텁만 있으면 fail-open WARN(exit 0)
  ⓘ git 도 같은 판별(r2): _lib cys_have_git · 부트 경로 훅(vibe-doc-sync·50-state-ledger) ·
     javis_preflight.usable_git — 스텁은 부재로 접고 **실행 0회**, 스텁 뒤의 진짜 git 은 찾는다
뮤테이션 검산: PYRES_HOOKS_DIR 로 훅 폴더를 바꿔 끼워 변이 사본을 잰다(하네스는 이 파일 그대로).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SELF = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.environ.get("PYRES_HOOKS_DIR") or os.path.normpath(os.path.join(SELF, "..", "..", "hooks"))
LIB = os.path.join(HOOKS, "_lib.sh")
fails = []

# 수정 전(base de3b2c8) 해소기 원문 — 비맥 무회귀 대조의 기준. 복사본이지만 대조 대상은 실행 결과다.
OLD_RESOLVER = r'''
cys_resolve_py_old() {
  if [ -n "${CYS_PY:-}" ]; then
    if [ -x "${CYS_PY}" ] || command -v "${CYS_PY}" >/dev/null 2>&1; then
      export CYS_PY
      return 0
    fi
  fi
  CYS_PY="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || command -v py 2>/dev/null || printf '%s' '')"
  export CYS_PY
  [ -n "${CYS_PY:-}" ]
}
'''


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))
    if not cond:
        fails.append(name)


def _w(path, body, mode=0o755):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    os.chmod(path, mode)


class Box:
    """가짜 루트 하나. marks/ 에 실행 표식이 쌓인다."""

    def __init__(self, os_name="Darwin", clt=False, xcode_select=True):
        self.t = tempfile.mkdtemp(prefix="pyres-")
        self.root = os.path.join(self.t, "root")
        self.marks = os.path.join(self.t, "marks")
        self.stubbin = os.path.join(self.t, "stubbin")
        self.home = os.path.join(self.t, "home")
        os.makedirs(self.marks)
        os.makedirs(self.home)
        # 가짜 uname
        _w(os.path.join(self.stubbin, "uname"), "#!/bin/sh\necho %s\n" % os_name)
        # 해소기가 쓰는 외부 도구(readlink)만 링크 — /usr/bin 자체는 PATH 에 넣지 않는다
        for tool in ("readlink",):
            real = shutil.which(tool, path="/usr/bin:/bin")
            if real:
                os.symlink(real, os.path.join(self.stubbin, tool))
        # CLT 스텁: 실행되면 표식을 남기고 rc 1
        self.stub = self.fake_py(os.path.join(self.root, "usr", "bin", "python3"), "STUB", real=False)
        if xcode_select:
            _w(os.path.join(self.root, "usr", "bin", "xcode-select"),
               "#!/bin/sh\n%s\n" % ("echo /Library/Developer/CommandLineTools; exit 0" if clt
                                    else "echo 'xcode-select: error' >&2; exit 2"))

    def toolbin(self):
        """훅 통합 실행용 — /usr/bin·/bin 의 도구를 링크하되 파이썬·xcode-select 는 뺀다
        (호스트 실파이썬이 끼면 스텁 판정 시험이 무의미해진다)."""
        tb = os.path.join(self.t, "toolbin")
        if not os.path.isdir(tb):
            os.makedirs(tb)
            for d in ("/usr/bin", "/bin"):
                for n in sorted(os.listdir(d)):
                    if n.startswith(("python", "pydoc", "xcode-select", "uname")):
                        continue
                    dst = os.path.join(tb, n)
                    if not os.path.lexists(dst):
                        os.symlink(os.path.join(d, n), dst)
            # jq 는 guard 백스톱이 쓴다 — 호스트에 있으면 연결(없어도 백스톱은 동작)
            jq = shutil.which("jq")
            if jq and not os.path.lexists(os.path.join(tb, "jq")):
                os.symlink(jq, os.path.join(tb, "jq"))
        return tb

    def fake_py(self, path, tag, real=True):
        body = "#!/bin/sh\necho x >> '%s/%s'\n" % (self.marks, tag)
        body += ('exec "%s" "$@"\n' % sys.executable) if real else "exit 1\n"
        _w(path, body)
        return path

    def bundle(self, app, tag):
        return self.fake_py(os.path.join(app, "Contents", "Resources", "runtime", "python", "bin", "python3"), tag)

    def env(self, path_dirs, extra=None):
        e = {"PATH": ":".join([self.stubbin] + path_dirs), "HOME": self.home,
             "CYS_TEST_SYSROOT": self.root, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"}
        if extra:
            e.update(extra)
        return e

    def executed(self):
        return sorted(os.listdir(self.marks))

    def close(self):
        shutil.rmtree(self.t, ignore_errors=True)


def resolve(box, path_dirs, extra=None, old=False):
    """프리루드 source 후 (CYS_PY, rc, CYS_PYBIN) — 실행 표식은 이 호출 직전에 비운다."""
    for m in os.listdir(box.marks):
        os.remove(os.path.join(box.marks, m))
    script = (". '%s'\n" % LIB) + OLD_RESOLVER + (
        "unset CYS_PY\n[ -n \"${PRE_CYS_PY:-}\" ] && CYS_PY=\"$PRE_CYS_PY\"\n"
        "%s; rc=$?\nprintf 'PY=%%s\\n' \"$CYS_PY\"; printf 'RC=%%s\\n' \"$rc\"\n"
        "cys_resolve_pybin; printf 'BIN=%%s\\n' \"$CYS_PYBIN\"\n"
        % ("cys_resolve_py_old" if old else "cys_resolve_py"))
    e = box.env(path_dirs, extra)
    r = subprocess.run(["/bin/sh", "-c", script], capture_output=True, text=True, env=e, timeout=30)
    out = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)
    return out.get("PY", "<none>"), out.get("RC", "<none>"), out.get("BIN", "<none>"), r


def norm(p):
    return os.path.realpath(p) if p else p


def main():
    if not os.path.isfile(LIB):
        print("FAIL _lib.sh 부재: %s" % LIB)
        return 1

    # ── 케이스 1: 맥·CLT 없음·번들 없음 · PATH 에 스텁이 먼저, 진짜 파이썬이 뒤 ──
    b = Box()
    try:
        brew = b.fake_py(os.path.join(b.t, "brew", "bin", "python3"), "BREW")
        py, rc, pybin, r = resolve(b, [os.path.join(b.root, "usr", "bin"), os.path.dirname(brew)])
        check("c1 스텁 뒤 PATH 후보 채택", py == brew, "py=%r stderr=%r" % (py, r.stderr[-300:]))
        check("c1 스텁 미실행", "STUB" not in b.executed(), repr(b.executed()))
        check("c1 해소 중 어떤 후보도 실행 안 함", b.executed() == [], repr(b.executed()))
        check("c1 pybin 동일", pybin == brew, repr(pybin))
    finally:
        b.close()

    # ── 케이스 2: 맥·번들(고정 위치 cysr.app) + PATH 에 스텁·다른 파이썬 → 번들 우선 ──
    b = Box()
    try:
        bun = b.bundle(os.path.join(b.root, "Applications", "cysr.app"), "BUNDLE")
        brew = b.fake_py(os.path.join(b.t, "brew", "bin", "python3"), "BREW")
        py, rc, pybin, r = resolve(b, [os.path.dirname(brew), os.path.join(b.root, "usr", "bin")])
        check("c2 번들 파이썬 우선(PATH 진짜 파이썬보다 앞)", py == bun, "py=%r" % py)
        check("c2 스텁 미실행", "STUB" not in b.executed(), repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 2b: 구 이름 cys.app 만 설치 ──
    b = Box()
    try:
        bun = b.bundle(os.path.join(b.root, "Applications", "cys.app"), "BUNDLE")
        py, rc, pybin, r = resolve(b, [os.path.join(b.root, "usr", "bin")])
        check("c2b 구 이름 cys.app 번들", py == bun, "py=%r" % py)
        check("c2b 스텁 미실행", b.executed() == [], repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 2c: 사용자 ~/Applications/cysr.app ──
    b = Box()
    try:
        bun = b.bundle(os.path.join(b.home, "Applications", "cysr.app"), "BUNDLE")
        py, rc, pybin, r = resolve(b, [os.path.join(b.root, "usr", "bin")])
        check("c2c 사용자 Applications 번들", py == bun, "py=%r" % py)
    finally:
        b.close()

    # ── 케이스 3: PATH 의 cys(심링크)가 가리키는 번들 > 고정 위치 번들 ──
    b = Box()
    try:
        fixed = b.bundle(os.path.join(b.root, "Applications", "cysr.app"), "FIXED")
        other_app = os.path.join(b.t, "elsewhere", "cysr.app")
        cli_bun = b.bundle(other_app, "CLI")
        real_cys = os.path.join(other_app, "Contents", "MacOS", "cys")
        _w(real_cys, "#!/bin/sh\necho x >> '%s/CYS'\nexit 0\n" % b.marks)
        clibin = os.path.join(b.t, "clibin")
        os.makedirs(clibin)
        os.symlink(os.path.relpath(real_cys, clibin), os.path.join(clibin, "cys"))  # 상대 심링크
        py, rc, pybin, r = resolve(b, [clibin, os.path.join(b.root, "usr", "bin")])
        check("c3 PATH 의 cys 실체 번들 우선", norm(py) == norm(cli_bun), "py=%r" % py)
        check("c3 cys 도 파이썬도 실행 안 함", b.executed() == [], repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 4: CYS_PY 지정 — 스텁이면 무시, 유효하면 번들보다 존중 ──
    b = Box()
    try:
        bun = b.bundle(os.path.join(b.root, "Applications", "cysr.app"), "BUNDLE")
        mine = b.fake_py(os.path.join(b.t, "mine", "python3"), "MINE")
        py, rc, pybin, r = resolve(b, [], {"PRE_CYS_PY": b.stub})
        check("c4a CYS_PY=스텁 → 무시하고 번들", py == bun, "py=%r" % py)
        check("c4a 스텁 미실행", b.executed() == [], repr(b.executed()))
        py, rc, pybin, r = resolve(b, [os.path.join(b.root, "usr", "bin")], {"PRE_CYS_PY": "python3"})
        check("c4b CYS_PY=python3(이름·스텁으로 해소) → 무시하고 번들", py == bun, "py=%r" % py)
        py, rc, pybin, r = resolve(b, [], {"PRE_CYS_PY": mine})
        check("c4c 유효한 CYS_PY 존중(번들 있어도)", py == mine, "py=%r" % py)
        check("c4 전 구간 실행 0", b.executed() == [], repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 5: 맥·스텁만(번들·다른 파이썬 없음) → 빈 값·rc 1 · 절대경로 꼬리도 스텁 제외 ──
    b = Box()
    try:
        py, rc, pybin, r = resolve(b, [os.path.join(b.root, "usr", "bin")])
        check("c5 전부 부재 = 빈 CYS_PY", py == "", "py=%r" % py)
        check("c5 rc 1", rc == "1", "rc=%r" % rc)
        check("c5 pybin 꼬리(/usr/bin/python3)도 스텁 제외 = 빈 값", pybin == "", "bin=%r" % pybin)
        check("c5 스텁 미실행", b.executed() == [], repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 5b: 꼬리의 정상 후보(homebrew 절대경로)는 PATH 에 없어도 잡는다(PATH 빈곤) ──
    b = Box()
    try:
        hb = b.fake_py(os.path.join(b.root, "opt", "homebrew", "bin", "python3"), "HB")
        py, rc, pybin, r = resolve(b, [])
        check("c5b 해소기 빈 값(PATH 빈곤)", py == "", "py=%r" % py)
        check("c5b pybin 꼬리 homebrew 채택", pybin == hb, "bin=%r" % pybin)
    finally:
        b.close()

    # ── 케이스 6: 맥·CLT 설치됨 → /usr/bin/python3 는 정상 후보(단, 해소 중 실행은 여전히 0) ──
    b = Box(clt=True)
    try:
        py, rc, pybin, r = resolve(b, [os.path.join(b.root, "usr", "bin")])
        check("c6 CLT 있으면 /usr/bin/python3 채택", py == b.stub, "py=%r" % py)
        check("c6 해소 중 실행 0", b.executed() == [], repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 7: 맥·xcode-select 자체 부재 → 스텁으로 본다(모르는 쪽을 실행하지 않음) ──
    b = Box(xcode_select=False)
    try:
        py, rc, pybin, r = resolve(b, [os.path.join(b.root, "usr", "bin")])
        check("c7 판별기 부재 = 스텁 취급 → 빈 값", py == "" and pybin == "", "py=%r bin=%r" % (py, pybin))
        check("c7 스텁 미실행", b.executed() == [], repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 8: 비맥(Linux·윈도 Git sh 흉내) — 수정 전 해소기와 결과 문자열 동일 ──
    for os_name in ("Linux", "MINGW64_NT-10.0-19045"):
        b = Box(os_name=os_name)
        try:
            b.bundle(os.path.join(b.root, "Applications", "cysr.app"), "BUNDLE")  # 비맥은 번들 무시여야
            usrbin = os.path.join(b.root, "usr", "bin")
            brew = b.fake_py(os.path.join(b.t, "brew", "bin", "python3"), "BREW")
            ponly = b.fake_py(os.path.join(b.t, "ponly", "python"), "P")
            pyl = b.fake_py(os.path.join(b.t, "pyl", "py"), "PY")
            layouts = [
                ("usrbin-first", [usrbin, os.path.dirname(brew)], None),
                ("brew-first", [os.path.dirname(brew), usrbin], None),
                ("python-only", [os.path.dirname(ponly)], None),
                ("py-only(윈도 런처)", [os.path.dirname(pyl)], None),
                ("none", [], None),
                ("CYS_PY=stub-path", [], {"PRE_CYS_PY": b.stub}),
                ("CYS_PY=invalid", [os.path.dirname(pyl)], {"PRE_CYS_PY": "/nope/python3"}),
            ]
            for label, dirs, extra in layouts:
                new = resolve(b, dirs, extra)
                old = resolve(b, dirs, extra, old=True)
                check("c8 %s %s 새=옛" % (os_name, label), new[0] == old[0] and new[1] == old[1],
                      "new=%r old=%r" % (new[:2], old[:2]))
            check("c8 %s usrbin-first 는 /usr/bin 후보 그대로(스텁 판정 비적용)" % os_name,
                  resolve(b, [usrbin, os.path.dirname(brew)])[0] == b.stub)
        finally:
            b.close()

    # ── 케이스 9: guard.sh 의미 보존 ──
    guard = os.path.join(HOOKS, "guard.sh")
    inp = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})

    def run_guard(box, dirs, active):
        for m in os.listdir(box.marks):
            os.remove(os.path.join(box.marks, m))
        af = os.path.join(box.t, "AUTOPILOT_ACTIVE")
        pf = os.path.join(box.t, "AUTOPILOT_PAUSED")
        if active:
            open(af, "w").close()
        elif os.path.exists(af):
            os.remove(af)
        e = box.env(dirs + [box.toolbin()], {"GUARD_TEST_MODE": "1", "AUTOPILOT_ACTIVE_FILE": af,
                                      "AUTOPILOT_PAUSED_FILE": pf, "CYS_NO_AUTOSTART": "1"})
        return subprocess.run(["/bin/bash", guard], input=inp, capture_output=True, text=True,
                              env=e, timeout=60)

    b = Box()
    try:
        usrbin = [os.path.join(b.root, "usr", "bin")]
        r = run_guard(b, usrbin, active=True)
        check("c9 선행: guard 프리루드 적재(소실 강등 아님)", "_lib.sh 소실" not in r.stderr, repr(r.stderr[-300:]))
        check("c9a guard STRICT·스텁만 → fail-closed deny(exit 2)", r.returncode == 2 and "python3 미가용" in r.stderr,
              "rc=%s err=%r" % (r.returncode, r.stderr[-300:]))
        check("c9a guard 스텁 미실행", "STUB" not in b.executed(), repr(b.executed()))
        r = run_guard(b, usrbin, active=False)
        check("c9b guard LOOSE·스텁만 → 백스톱 강등(exit 0)", r.returncode == 0 and "LOOSE degraded" in r.stderr,
              "rc=%s err=%r" % (r.returncode, r.stderr[-300:]))
        check("c9b guard 스텁 미실행", "STUB" not in b.executed(), repr(b.executed()))
        b.bundle(os.path.join(b.root, "Applications", "cysr.app"), "BUNDLE")
        r = run_guard(b, usrbin, active=True)
        check("c9c guard STRICT·번들 → 파서 판정(ls 허용 exit 0 · 부재 문구 없음)",
              r.returncode == 0 and "python3 미가용" not in r.stderr and "parser 크래시" not in r.stderr
              and "_lib.sh 소실" not in r.stderr,
              "rc=%s err=%r" % (r.returncode, r.stderr[-300:]))
        check("c9c guard 가 번들 파이썬으로 파서 실행 · 스텁 0", "BUNDLE" in b.executed() and "STUB" not in b.executed(),
              repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 10: actprobe-kill-gate.sh — 스텁만 → fail-open WARN ──
    gate = os.path.join(HOOKS, "actprobe-kill-gate.sh")
    b = Box()
    try:
        e = b.env([os.path.join(b.root, "usr", "bin"), b.toolbin()])
        r = subprocess.run(["/bin/bash", gate], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "kill 1"}}),
                           capture_output=True, text=True, env=e, timeout=60)
        check("c10 선행: kill-gate 프리루드 적재(소실 강등 아님)", "_lib.sh 소실" not in r.stderr, repr(r.stderr[-300:]))
        check("c10 kill-gate 스텁만 → 파이썬 부재 fail-open(exit 0)", r.returncode == 0 and "부재" in r.stderr,
              "rc=%s err=%r" % (r.returncode, r.stderr[-300:]))
        check("c10 kill-gate 스텁 미실행", b.executed() == [], repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 11: git 해소(_lib cys_have_git) — 스텁 배제·뒤 후보 탐색·CLT 있으면 채택 ──
    def have_git(box, dirs, extra=None):
        for m in os.listdir(box.marks):
            os.remove(os.path.join(box.marks, m))
        script = (". '%s'\ncys_have_git; printf 'RC=%%s\\n' \"$?\"; printf 'GIT=%%s\\n' \"$CYS_GIT\"\n" % LIB)
        r = subprocess.run(["/bin/sh", "-c", script], capture_output=True, text=True,
                           env=box.env(dirs, extra), timeout=30)
        out = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)
        return out.get("GIT", "<none>"), out.get("RC", "<none>")

    b = Box()
    try:
        stub_git = b.fake_py(os.path.join(b.root, "usr", "bin", "git"), "STUBGIT", real=False)
        g, rc = have_git(b, [os.path.join(b.root, "usr", "bin")])
        check("c11a 스텁 git 만 → 부재(rc 1·빈 값)", g == "" and rc == "1", "git=%r rc=%r" % (g, rc))
        check("c11a 스텁 git 미실행", b.executed() == [], repr(b.executed()))
        real_git = b.fake_py(os.path.join(b.t, "rg", "git"), "REALGIT")
        g, rc = have_git(b, [os.path.join(b.root, "usr", "bin"), os.path.dirname(real_git)])
        check("c11b 스텁 뒤의 진짜 git 채택", g == real_git and rc == "0", "git=%r" % g)
        check("c11b 스텁 git 미실행", "STUBGIT" not in b.executed(), repr(b.executed()))
    finally:
        b.close()
    b = Box(clt=True)
    try:
        stub_git = b.fake_py(os.path.join(b.root, "usr", "bin", "git"), "STUBGIT", real=False)
        g, rc = have_git(b, [os.path.join(b.root, "usr", "bin")])
        check("c11c CLT 있으면 /usr/bin/git 채택", g == stub_git and rc == "0", "git=%r" % g)
        check("c11c 해소 중 실행 0", b.executed() == [], repr(b.executed()))
    finally:
        b.close()
    b = Box(os_name="Linux")
    try:
        sys_git = b.fake_py(os.path.join(b.root, "usr", "bin", "git"), "STUBGIT", real=False)
        g, rc = have_git(b, [os.path.join(b.root, "usr", "bin")])
        check("c11d 비맥은 스텁 판정 비적용(종전대로 채택)", g == sys_git and rc == "0", "git=%r" % g)
    finally:
        b.close()

    # ── 케이스 12: 부트 경로 훅 — vibe-doc-sync.sh 가 스텁 git 을 실행하지 않는다 ──
    doc_sync = os.path.join(HOOKS, "vibecoding", "vibe-doc-sync.sh")
    b = Box()
    try:
        bun = b.bundle(os.path.join(b.root, "Applications", "cysr.app"), "BUNDLE")
        b.fake_py(os.path.join(b.root, "usr", "bin", "git"), "STUBGIT", real=False)
        code_file = os.path.join(b.t, "proj", "a.py")
        _w(code_file, "x = 1\n", 0o644)
        e = b.env([os.path.join(b.root, "usr", "bin"), b.toolbin()])
        r = subprocess.run(["/bin/bash", doc_sync],
                           input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": code_file}}),
                           capture_output=True, text=True, env=e, timeout=60)
        check("c12 선행: doc-sync 프리루드 적재·번들 파이썬 사용", "_lib.sh 소실" not in r.stderr and "BUNDLE" in b.executed(),
              "err=%r exec=%r" % (r.stderr[-200:], b.executed()))
        check("c12 doc-sync 가 스텁 git 을 실행하지 않는다(exit 0)", r.returncode == 0 and "STUBGIT" not in b.executed(),
              "rc=%s exec=%r" % (r.returncode, b.executed()))
    finally:
        b.close()

    # ── 케이스 13: javis_preflight.usable_git — 스텁은 부재·뒤 후보는 채택(실행 0) ──
    pf = os.path.join(SELF, "..", "javis_preflight.py")
    b = Box()
    try:
        b.fake_py(os.path.join(b.root, "usr", "bin", "git"), "STUBGIT", real=False)
        probe = ("import sys, os\n"
                 "sys.path.insert(0, %r)\n"
                 "import javis_preflight as P\n"
                 "print('GIT=%%s' %% (P.usable_git() or ''))\n" % os.path.dirname(os.path.abspath(pf)))
        e = dict(b.env([os.path.join(b.root, "usr", "bin")]))
        r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=e, timeout=120)
        got = [l for l in r.stdout.splitlines() if l.startswith("GIT=")]
        check("c13a preflight usable_git: 스텁만 → None", got == ["GIT="], "out=%r err=%r" % (r.stdout[-300:], r.stderr[-300:]))
        check("c13a 스텁 git 미실행", b.executed() == [], repr(b.executed()))
        real_git = b.fake_py(os.path.join(b.t, "rg", "git"), "REALGIT")
        e = dict(b.env([os.path.join(b.root, "usr", "bin"), os.path.dirname(real_git)]))
        r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=e, timeout=120)
        got = [l for l in r.stdout.splitlines() if l.startswith("GIT=")]
        check("c13b preflight usable_git: 스텁 뒤의 진짜 git 채택", got == ["GIT=" + real_git],
              "out=%r" % r.stdout[-300:])
        check("c13b 스텁 git 미실행", "STUBGIT" not in b.executed(), repr(b.executed()))
    finally:
        b.close()

    # ── 케이스 14: 부트 경로 훅 — 50-state-ledger.sh(git commit 감지) ──
    ledger = os.path.join(HOOKS, "fullauto", "50-state-ledger.sh")

    def run_ledger(box, dirs, extra=None):
        for m in os.listdir(box.marks):
            os.remove(os.path.join(box.marks, m))
        binf = os.path.join(box.t, "javis_state_ledger.py")
        _w(binf, "import sys\n", 0o644)
        e = box.env(dirs + [box.toolbin()], dict(extra or {}, CYS_STATE_LEDGER_BIN=binf))
        return subprocess.run(["/bin/sh", ledger],
                              input=json.dumps({"tool_name": "Bash", "cwd": box.t,
                                                "tool_input": {"command": "git commit -m x"}}),
                              capture_output=True, text=True, env=e, timeout=60)

    b = Box()
    try:
        b.bundle(os.path.join(b.root, "Applications", "cysr.app"), "BUNDLE")
        b.fake_py(os.path.join(b.root, "usr", "bin", "git"), "STUBGIT", real=False)
        r = run_ledger(b, [os.path.join(b.root, "usr", "bin")])
        check("c14a 선행: state-ledger 프리루드 적재·번들 파이썬 사용",
              "_lib.sh 소실" not in r.stderr and "BUNDLE" in b.executed(),
              "err=%r exec=%r" % (r.stderr[-200:], b.executed()))
        check("c14a state-ledger 가 스텁 git 을 실행하지 않는다(exit 0)",
              r.returncode == 0 and "STUBGIT" not in b.executed(), "rc=%s exec=%r" % (r.returncode, b.executed()))
        # 대조군: 진짜 git 이 PATH 에 있으면 그 자리에서 git 을 실제로 부른다(가드가 경로 위에 있음을 증명)
        real_git = b.fake_py(os.path.join(b.t, "rg", "git"), "REALGIT")
        r = run_ledger(b, [os.path.join(b.root, "usr", "bin"), os.path.dirname(real_git)])
        check("c14b 대조군: 진짜 git 은 그대로 호출된다", "REALGIT" in b.executed(), repr(b.executed()))
    finally:
        b.close()

    print("\n%s (%d FAIL)" % ("ALL PASS" if not fails else "FAILED", len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
