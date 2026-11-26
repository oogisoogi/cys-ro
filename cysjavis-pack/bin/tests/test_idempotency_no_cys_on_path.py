#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_idempotency_no_cys_on_path.py — preflight C53(javis_idempotency --self-test)이 **PATH 에 cys 가
없는 프로세스**에서도 통과하는가(1.1.20 · TICKET=user-reports-1126).

★왜: fleet 윈 사용자 기기 5대(1.1.16·1.1.18·1.1.19 · 판 이동 직후 다발)에서 C53 FAIL. 맥 재현 =
  v1.1.19 팩으로 PATH=/usr/bin:/bin 에서 self-test 를 돌리면 `AssertionError: cmd_check 가 cys status
  조차 호출하지 않음(spy 미작동 의심)`. spy 는 subprocess 만 가로채는데 cmd_check→cys_status 와
  C12.daemon 이 호출 **전에** shutil.which("cys") 로 찾고, 못 찾으면 아무것도 부르지 않기 때문이다.
  비멱등이 0 인데 preflight 가 NOT READY 가 됐다. 고침 = javis_idempotency._spy_which(spy 가 cys 위치도 정함).
★되돌리면 붉음: _spy_which 패치를 빼면 이 시험이 rc≠0 으로 실패한다(2026-11-26 실측).
★공허 방지: 고른 PATH 에서 정말 cys 가 안 보이는지 먼저 단언한다(보이면 이 시험은 아무것도 안 잰 것).
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "javis_idempotency.py")


def _path_without_cys():
    keep = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and shutil.which("cys", path=d) is None:
            keep.append(d)
    return os.pathsep.join(keep)


def main():
    path = _path_without_cys()
    assert shutil.which("cys", path=path) is None, "PATH 에서 cys 를 못 뺐다 — 시험이 공허함"
    env = dict(os.environ)
    env["PATH"] = path
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("CYS_CYS_BIN", None)
    r = subprocess.run([sys.executable, TOOL, "--self-test"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=60, env=env,
                       **({"creationflags": 0x08000000} if os.name == "nt" else {}))
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    if r.returncode != 0 or "self-test OK" not in out:
        print("FAIL: PATH 에 cys 가 없을 때 javis_idempotency --self-test rc=%s\n%s" % (r.returncode, out[-800:]))
        return 1
    print("PASS: PATH 에 cys 없음 → C53 self-test OK (spy 가 cys 위치까지 정함)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
