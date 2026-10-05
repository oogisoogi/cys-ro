#!/usr/bin/env python3
"""D13(1.1.8 · 윈 실측) — `javis_awaken.py status` 가 줄마다 레인을 싣고 호출 레인 줄에 표지를 붙인다."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "javis_awaken.py")
fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — %s" % (detail,)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


td = tempfile.mkdtemp(prefix="awl.", dir=os.environ.get("TMPDIR") or None)
st = os.path.join(td, "st", "awaken")
os.makedirs(st)
sock = "/tmp/x/cys-dept-dept-1/cys.sock"
for lane, sid in (("base", "surface:2"), (sock, "surface:9")):
    key = "%s__master" % lane
    import re
    key = re.sub(r"[^A-Za-z0-9_.-]", "_", key)[-150:]
    with open(os.path.join(st, key + ".json"), "w", encoding="utf-8") as f:
        json.dump({"role": "master", "surface": sid, "awaken": "confirmed", "at": "t"}, f)


def run(env_sock, *args):
    env = {"PATH": "/usr/bin:/bin", "HOME": td, "CYS_STATE_DIR": os.path.join(td, "st")}
    if env_sock:
        env["CYS_SOCKET"] = env_sock
    return subprocess.run([sys.executable, TOOL, "status"] + list(args), capture_output=True, text=True, env=env)


p = run(None)
lines = p.stdout.splitlines()
check("L1 머리줄 = 호출 레인(base)", lines and lines[0].startswith("# 호출 레인 = base"), p.stdout)
check("L2 base 레인 줄에만 표지", any("surface:2" in l and "이 레인" in l for l in lines)
      and not any("surface:9" in l and "이 레인" in l for l in lines), p.stdout)
p = run(sock, "--json")
rows = json.loads(p.stdout)
mine = [r["surface"] for r in rows if r.get("this_lane")]
check("L3 부서 소켓에서 부르면 부서 레인 줄이 이 레인(JSON this_lane)", mine == ["surface:9"], rows)
check("L4 JSON 각 행에 lane", all("lane" in r for r in rows), rows)
print("\n=== %s ===" % ("ALL PASS" if not fails else "FAIL %d: %s" % (len(fails), fails)))
sys.exit(1 if fails else 0)
