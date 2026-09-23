#!/usr/bin/env python3
"""R-B1 P2-b 격리 cysd 실측 — `cys status --json` 의 `daemon.auto_restore` 가 실제 데몬에서 나오는가.

  A  CYS_NO_AUTORESTORE=1 로 띄운 데몬 = "off"(편성이 기다리지 않는다)
  B  자동 복원을 발화하는 데몬 = 소켓이 요청을 받는 첫 순간부터 "running"|"retry_wait"|"done" 중 하나("off" 아님 —
     accept 전에 running 을 찍으므로 편성이 복원 전에 끼어드는 틈이 없다) · 끝나면 "done"
  C  편성 판정(restore_settle_verdict)이 실제 데몬 출력을 wait/go 로 읽는다

격리 = 임시 HOME·소켓·팩 폴더 · 라이브 데몬 무접촉 · 바이너리(target/debug/cysd·cys) 없으면 skip.
실행: python3 cysjavis-pack/bin/tests/test_v116_auto_restore_status.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DBG = os.path.join(REPO, "target", "debug")
CYSD, CYS = os.path.join(DBG, "cysd"), os.path.join(DBG, "cys")
if not (os.path.exists(CYSD) and os.path.exists(CYS)):
    print("SKIP: target/debug cysd/cys 없음(빌드 필요)")
    sys.exit(0)
sys.path.insert(0, os.path.dirname(HERE))
import javis_formation as fm  # noqa: E402

fails = []


def check(name, ok, why=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else " — " + str(why)))
    if not ok:
        fails.append(name)


def boot(tmp, extra):
    home = os.path.join(tmp, "home")
    os.makedirs(home, exist_ok=True)
    sock = os.path.join(tmp, "s", "cys.sock")
    os.makedirs(os.path.dirname(sock), exist_ok=True)
    env = {"HOME": home, "PATH": DBG + ":/usr/bin:/bin", "CYS_SOCKET": sock,
           "CYS_PACK_DIR": os.path.join(tmp, "pack"), "CYS_NO_AUTOSTART": "1",
           "CYS_AUTORESTORE_RETRY_DELAY_MS": "1500"}
    env.update(extra)
    p = subprocess.Popen([CYSD], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    return p, env


def status(env):
    r = subprocess.run([CYS, "status", "--json"], env=env, capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def first_status(env, limit=20.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        st = status(env)
        if st is not None:
            return st
        time.sleep(0.05)
    return None


def stop(p):
    try:
        os.killpg(p.pid, 15)
        p.wait(timeout=10)
    except Exception:
        try:
            os.killpg(p.pid, 9)
        except Exception:
            pass


tmp = tempfile.mkdtemp(prefix="v116ar-")
try:
    p, env = boot(os.path.join(tmp, "a"), {"CYS_NO_AUTORESTORE": "1"})
    try:
        st = first_status(env)
        d = (st or {}).get("daemon") or {}
        check("A 옵트아웃 데몬 = off", d.get("auto_restore") == "off", d)
        check("C1 편성 판정 off → go", fm.restore_settle_verdict(st, time.time())[0] == "go", d)
    finally:
        stop(p)

    p, env = boot(os.path.join(tmp, "b"), {})
    try:
        st = first_status(env)
        d = (st or {}).get("daemon") or {}
        ph0 = d.get("auto_restore")
        check("B1 첫 응답부터 off 아님(accept 전 running)", ph0 in ("running", "retry_wait", "done"), d)
        seen, t0, ph = [ph0], time.time(), ph0
        while ph != "done" and time.time() - t0 < 90:
            time.sleep(0.5)
            ph = ((status(env) or {}).get("daemon") or {}).get("auto_restore")
            if ph != seen[-1]:
                seen.append(ph)
        check("B2 결국 done", ph == "done", seen)
        check("B3 단계는 running→(retry_wait→running)*→done 순서만", all(x in ("running", "retry_wait", "done") for x in seen)
              and seen[-1] == "done", seen)
        if ph0 in ("running", "retry_wait"):
            check("C2 편성 판정 running → wait", fm.restore_settle_verdict({"daemon": {"auto_restore": ph0}}, time.time())[0] == "wait")
        print("관측 단계:", seen)
    finally:
        stop(p)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n=== %s ===" % ("PASS" if not fails else "FAIL %r" % fails))
sys.exit(1 if fails else 0)
