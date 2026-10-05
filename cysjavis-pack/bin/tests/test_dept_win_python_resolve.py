#!/usr/bin/env python3
"""D4·D9-b(1.1.8 · 윈 실측 2026-10-05) — 윈 셸에서 `cys-dept`·훅 프리루드가 `python3` 이름에 기대지 않는다.

결함: 윈 Git Bash 에 `python3` 가 없거나 Microsoft Store 별칭(WindowsApps · 실행 = 스토어 안내 + rc 9009)뿐이면
`cys-dept list` 가 실패해 본부가 부서를 독립 검증할 길이 없었고(D4), 훅 해석기 해소도 별칭을 먼저 집었다(D9-b).
재는 법(맥에서 윈 셸 흉내): 가짜 `uname`(MINGW64_NT) · WindowsApps 폴더의 가짜 python3(실행되면 표지 파일을 남기고
rc 9009) · 다른 폴더의 `python`(= 진짜 해석기로 넘김). 실 데몬·실 팩 무접촉.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(os.path.dirname(HERE))
DEPT = os.path.join(PACK, "bin", "cys-dept")
LIB = os.path.join(PACK, "hooks", "_lib.sh")
BASH = shutil.which("bash") or "/bin/bash"
fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — %s" % (detail,)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def exe(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    os.chmod(path, 0o755)


def fixture(root, with_real=True):
    fake = os.path.join(root, "fakebin")
    exe(os.path.join(fake, "uname"), "#!/bin/sh\necho MINGW64_NT-10.0-26100\n")
    marker = os.path.join(root, "store-ran")
    exe(os.path.join(root, "WindowsApps", "python3"), "#!/bin/sh\necho stub > '%s'\nexit 9009\n" % marker)
    if with_real:
        exe(os.path.join(root, "realpy", "python"), "#!/bin/sh\nexec '%s' \"$@\"\n" % sys.executable)
    path = os.pathsep.join([fake, os.path.join(root, "WindowsApps"), os.path.join(root, "realpy"), "/usr/bin", "/bin"])
    home = os.path.join(root, "home")
    os.makedirs(os.path.join(home, ".cys"), exist_ok=True)
    with open(os.path.join(home, ".cys", "depts.json"), "w", encoding="utf-8") as f:
        json.dump({"depts": {}}, f)
    env = {"HOME": home, "PATH": path, "LANG": "C.UTF-8", "TMPDIR": root,
           "CYS_DEPTS_JSON": os.path.join(home, ".cys", "depts.json")}
    return env, marker


def main():
    root = tempfile.mkdtemp(prefix="winpy.", dir=os.environ.get("TMPDIR") or None)
    try:
        env, marker = fixture(os.path.join(root, "a"))
        p = subprocess.run([BASH, DEPT, "list"], capture_output=True, text=True, env=env, timeout=60)
        check("W1 cys-dept list 가 별칭 python3 대신 python 으로 돈다", p.returncode == 0, (p.returncode, p.stderr[-500:]))
        check("W2 Store 별칭은 한 번도 실행되지 않았다", not os.path.exists(marker))
        q = subprocess.run([BASH, "-c", '. "$1" >/dev/null 2>&1; unset CYS_PY; cys_resolve_py; printf %s "$CYS_PY"',
                            "_", LIB], capture_output=True, text=True, env=dict(env, CYS_PY=""), timeout=30)
        check("W3 _lib.sh cys_resolve_py = WindowsApps 밖 후보 우선",
              q.stdout.endswith(os.path.join("realpy", "python")), (q.stdout, q.stderr[-300:]))
        env2, _m = fixture(os.path.join(root, "b"), with_real=False)
        q2 = subprocess.run([BASH, "-c", '. "$1" >/dev/null 2>&1; unset CYS_PY; cys_resolve_py; printf %s "$CYS_PY"',
                             "_", LIB], capture_output=True, text=True,
                            env=dict(env2, PATH=env2["PATH"].replace(os.pathsep + "/usr/bin" + os.pathsep + "/bin", "")),
                            timeout=30)
        check("W4 별칭뿐이면 별칭으로 폴백(빈 값 아님 · 종전과 같은 가용성)", "WindowsApps" in q2.stdout, q2.stdout)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("\n=== %s ===" % ("ALL PASS" if not fails else "FAIL %d: %s" % (len(fails), fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
