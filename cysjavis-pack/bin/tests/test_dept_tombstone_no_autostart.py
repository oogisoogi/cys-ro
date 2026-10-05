#!/usr/bin/env python3
"""D21(1.1.8 · 윈 실측 2026-10-05 18:13) — 닫힌 부서(묘비)에 읽기 명령을 보내도 부서 데몬을 다시 켜지 않는다.

결함: `cys-dept dept-1 -- cys list` 가 묘비 처리된(depts.json 에 없고 dept_tombstones.json 에 있는) 부서의 cysd 를
자동 기동했다 — passthrough 의 CYS_NO_AUTOSTART 조건이 「미등재 AND state 없음 AND pack 없음」 뿐이라 폴더가 남아 있으면 통과.
재는 법: 격리 HOME · passthrough 명령 = `env`(자식이 받은 CYS_NO_AUTOSTART 를 그대로 출력 — 하류 cys 의 자동 기동
스위치가 바로 이 값이다) · 실 데몬·실 팩 무접촉.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEPT = os.path.join(os.path.dirname(HERE), "cys-dept")
BASH = shutil.which("bash") or "/bin/bash"
fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — %s" % (detail,)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def run(home, name, registered=(), tombstones=None, leftovers=True):
    os.makedirs(os.path.join(home, ".cys"), exist_ok=True)
    with open(os.path.join(home, ".cys", "depts.json"), "w", encoding="utf-8") as f:
        json.dump({"depts": {n: {"socket": os.path.join(home, ".local/state/cys-dept-%s/cys.sock" % n),
                                 "pack_dir": os.path.join(home, ".cys/pack-dept-%s" % n)} for n in registered}}, f)
    st = os.path.join(home, ".local", "state", "cys")
    os.makedirs(st, exist_ok=True)
    tp = os.path.join(st, "dept_tombstones.json")
    if tombstones is None:
        if os.path.exists(tp):
            os.unlink(tp)
    else:
        with open(tp, "w", encoding="utf-8") as f:
            json.dump({"dept_tombstones": list(tombstones)}, f)
    if leftovers:
        os.makedirs(os.path.join(home, ".local", "state", "cys-dept-%s" % name), exist_ok=True)
        os.makedirs(os.path.join(home, ".cys", "pack-dept-%s" % name), exist_ok=True)
    env = {"HOME": home, "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C.UTF-8",
           "CYS_DEPTS_JSON": os.path.join(home, ".cys", "depts.json"), "TMPDIR": home}
    p = subprocess.run([BASH, DEPT, name, "--", "env"], capture_output=True, text=True, env=env, timeout=60)
    autostart_off = any(l == "CYS_NO_AUTOSTART=1" for l in p.stdout.splitlines())
    return p, autostart_off


def main():
    root = tempfile.mkdtemp(prefix="d21.", dir=os.environ.get("TMPDIR") or None)
    try:
        p, off = run(os.path.join(root, "a"), "dept-1", tombstones=["dept-1"])
        check("T1 묘비 부서(폴더 잔존) → 자동 기동 꺼짐", p.returncode == 0 and off, (p.returncode, p.stderr[-400:]))
        check("T2 닫힌 부서 안내 1줄", "닫힌 부서" in p.stderr, p.stderr[-400:])
        p, off = run(os.path.join(root, "b"), "dept-1", tombstones=["dept-10"])
        check("T3 다른 부서 묘비(dept-10)는 dept-1 을 막지 않는다(전문 일치)", not off and "닫힌 부서" not in p.stderr,
              p.stderr[-400:])
        p, off = run(os.path.join(root, "c"), "dept-1", registered=["dept-1"], tombstones=["dept-1"])
        check("T4 등재된 부서는 묘비 표기가 남아도 종전대로(재생성 직후 경합 무해)", not off, p.stderr[-400:])
        p, off = run(os.path.join(root, "d"), "dept-1", tombstones=None)
        check("T5 묘비 파일 없음 + 폴더 잔존 = 종전 동작", not off and "닫힌 부서" not in p.stderr, p.stderr[-400:])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("\n=== %s ===" % ("ALL PASS" if not fails else "FAIL %d: %s" % (len(fails), fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
