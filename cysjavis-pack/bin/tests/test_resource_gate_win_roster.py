#!/usr/bin/env python3
"""D3(1.1.8 · 윈 실측 2026-10-05) — resource_gate 가 윈에서 부서·본부 노드를 0 으로 세던 측정 공백.

①윈 부서 소켓 = named pipe 라 파일 glob 이 0건 → 등재(depts.json)의 socket 으로 묻는다.
②윈 MSYS ps 는 네이티브 claude·node 를 못 봐 nodes=0 → 좌석 집계(본부 비-exited + 부서 좌석)로 대신(errors 표기).
"""
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.dont_write_bytecode = True
import javis_resource_gate as G  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — %s" % (detail,)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


td = tempfile.mkdtemp(prefix="rgwin.", dir=os.environ.get("TMPDIR") or None)
reg = os.path.join(td, "depts.json")
with open(reg, "w", encoding="utf-8") as f:
    json.dump({"depts": {"dept-1": {"socket": r"\\.\pipe\cys-dept-dept-1"}, "dept-2": {"pack_dir": "x"}}}, f)
os.environ["CYS_DEPTS_JSON"] = reg
got = G._dept_sockets(windows=True)
check("W1 윈 = 등재 socket(named pipe)으로 부서 열거", got == [("dept-1", r"\\.\pipe\cys-dept-dept-1")], got)
os.environ["CYS_DEPTS_JSON"] = os.path.join(td, "없음.json")
check("W2 등재 판독 불가 = 빈 목록(조용한 가짜 부서 0)", G._dept_sockets(windows=True) == [])
check("W3 unix 는 종전 glob 경로", isinstance(G._dept_sockets(windows=False), list))

# ② nodes 대체: measure 의 윈 갈래를 결정론 대역으로 돌린다
calls = []
G._is_windows_host = lambda: True
G._base_live_seats = lambda: calls.append("base") or 3
G._dept_roster = lambda override=None, status_sink=None: {"active": 1, "seats": 3, "errors": [], "depts": []}
G._ps_lines = lambda: ["  PID COMMAND", "  10 /usr/bin/bash"]
import contextlib
import io
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = G.main(["check", "--json"])
out = buf.getvalue()
try:
    doc = json.loads(out[out.index("{"):])
except ValueError:
    doc = {}
blob = json.dumps(doc, ensure_ascii=False)
nodes = next((c.get("value") for c in doc.get("checks") or [] if c.get("metric") == "nodes"), None)
check("W4 윈 + ps 계수 0 → nodes = 본부 좌석 3 + 부서 좌석 3", nodes == 6, (rc, out[-600:]))
check("W5 대체 사실을 숨기지 않는다(errors 표기)", "ps 대신 좌석 집계" in blob, blob[-600:])
check("W6 본부 좌석 조회 1회", calls == ["base"], calls)
print("\n=== %s ===" % ("ALL PASS" if not fails else "FAIL %d: %s" % (len(fails), fails)))
sys.exit(1 if fails else 0)
