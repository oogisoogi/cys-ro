#!/usr/bin/env python3
"""격리 데몬 A/B E2E — 먹힌 큐 Return(TICKET=cysr-queued-paste-submit).

자기 소켓만 쓴다(라이브 소켓 0). 좌석 = swallow_tui.py(첫 붙여넣기 처리 900ms 동안 Return 을 먹는 모형).
시나리오: 69줄 항목 A 와 1줄 항목 B 를 연달아 --queued 로 넣고 45초 관측 — A·B 제출 여부·시각, 큐 막힘 사유·처방 code,
이벤트(queue.delivered · queue.submit_retried · queue.submit_recovered · queue.submit_unconfirmed · queue.starved).

실행: python3 run_ab.py <cysd 경로> <OUT 디렉터리> <짧은 심링크 경로> [KEY=VAL ...(데몬 env 추가)]
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time

CYSD, OUT, SHORT = sys.argv[1], sys.argv[2], sys.argv[3]
EXTRA = dict(a.split("=", 1) for a in sys.argv[4:])
HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(OUT, "run-" + time.strftime("%H%M%S"))
T0 = time.time()


def log(sec, **kw):
    rec = dict(t=round(time.time() - T0, 2), sec=sec, **kw)
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def rpc(sock, method, params):
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(15)
    s.connect(sock)
    s.sendall((json.dumps({"id": 1, "method": method, "params": params}) + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        c = s.recv(65536)
        if not c:
            break
        buf += c
    s.close()
    return json.loads(buf.decode())


def recorder(sock, path, stop):
    s = socket.socket(socket.AF_UNIX)
    s.connect(sock)
    s.sendall((json.dumps({"id": 1, "method": "events.stream", "params": {"after_seq": 0}}) + "\n").encode())
    s.settimeout(1.0)
    with open(path, "wb") as f:
        while not stop.is_set():
            try:
                c = s.recv(65536)
            except socket.timeout:
                continue
            if not c:
                break
            f.write(c)
            f.flush()


def main():
    for d in ("home", "s", "config", "captures", "state", "pack", "shim"):
        os.makedirs(os.path.join(RUN, d), exist_ok=True)
    for name in ("launchctl", "curl", "lsof"):
        p = os.path.join(RUN, "shim", name)
        open(p, "w").write("#!/bin/sh\nexit 0\n")
        os.chmod(p, 0o755)
    if os.path.islink(SHORT):
        os.unlink(SHORT)
    os.symlink(RUN, SHORT)
    sock = os.path.join(SHORT, "s", "cys.sock")
    env = {
        "HOME": os.path.join(RUN, "home"), "PATH": os.path.join(RUN, "shim") + ":/usr/bin:/bin", "LANG": "en_US.UTF-8",
        "CYS_SOCKET": sock, "CYS_PACK_DIR": os.path.join(RUN, "pack"), "CYS_CONFIG_DIR": os.path.join(RUN, "config"),
        "CYS_PACK_CAPTURES_DIR": os.path.join(RUN, "captures"), "CYS_STATE_DIR": os.path.join(RUN, "state"),
        "CYS_NO_PERSONAL_HOOK_MERGE": "1", "CYS_NO_OFFICE_BRIDGE": "1", "CYS_NO_AUTORESTORE": "1",
        "CYS_BOOT_SUPERVISOR": "0", "CYS_ALERT_ROUTE": "0", "CYS_NO_AUTOSTART": "1",
        "PHOENIX_LAUNCHCTL": os.path.join(RUN, "shim", "launchctl"),
        "CYS_QUEUE_STARVE_ALERT_SECS": "20",
    }
    env.update(EXTRA)
    lf = open(os.path.join(RUN, "cysd.log"), "wb")
    proc = subprocess.Popen([CYSD], env=env, stdout=lf, stderr=lf, cwd=RUN, stdin=subprocess.DEVNULL)
    stop = threading.Event()
    sid = None
    try:
        for _ in range(600):
            if os.path.exists(sock):
                try:
                    rpc(sock, "system.ping", {})
                    break
                except Exception:
                    pass
            time.sleep(0.1)
        ident = rpc(sock, "system.identify", {}).get("result", {})
        log("daemon", cysd=CYSD, version=ident.get("version"), build=ident.get("build_id"), extra=EXTRA)
        threading.Thread(target=recorder, args=(sock, os.path.join(RUN, "events.jsonl"), stop), daemon=True).start()
        rx, subs = os.path.join(RUN, "rx.jsonl"), os.path.join(RUN, "submits.jsonl")
        cmd = ("SWALLOW_EAT_ALL=1 " if os.environ.get("E2E_EAT_ALL") == "1" else "") + "SWALLOW_LAG_MS=900 SWALLOW_FIRST_ONLY=1 FAKE_RXLOG=%s FAKE_SUBMITS=%s /usr/bin/python3 -u %s" % (
            rx, subs, os.path.join(HERE, "swallow_tui.py"))
        r = rpc(sock, "surface.create", {"cmd": cmd, "rows": 30, "cols": 100})
        sid = r.get("result", r).get("surface_id")
        rpc(sock, "surface.set_meta", {"surface_id": sid, "agent": "claude"})
        time.sleep(7)  # 좌석 판정 틱(5s) 1회 이상
        a = "\n".join(["[E2E-A] 69줄 보고 머리"] + ["%02d 본문 줄 %s" % (i, "가" * 20) for i in range(1, 69)])
        b = "[E2E-B] 두 번째 지시 한 줄"
        for text, frm in ((a, "surface:99"), (b, "surface:98")):
            e = rpc(sock, "surface.send_text", {"surface_id": sid, "text": text, "queued": True, "from": frm})
            log("enqueue", head=text[:12], resp=e.get("result", e))
        t_enq = time.time()
        seen = {}
        last_q = None
        while time.time() - t_enq < float(os.environ.get("E2E_WINDOW", "45")):
            time.sleep(1)
            subs_rows = [json.loads(x) for x in open(subs)] if os.path.exists(subs) else []
            for row in subs_rows:
                h = row["message"]["content"][:7]
                seen.setdefault(h, round(row["t"] - t_enq, 1))
            q = rpc(sock, "queue.list", {"surface_id": sid}).get("result", {})
            ents = q.get("entries", [])
            h0 = ents[0] if ents else {}
            snap = (len(ents), h0.get("blocked_by"), h0.get("remedy_code"))
            if snap != last_q:
                log("queue", depth=len(ents), blocked_by=snap[1], remedy=snap[2])
                last_q = snap
        evs = []
        for ln in open(os.path.join(RUN, "events.jsonl"), "rb").read().decode("utf-8", "replace").splitlines():
            try:
                j = json.loads(ln)
            except Exception:
                continue
            ev = j.get("result", j)
            n = ev.get("name") if isinstance(ev, dict) else None
            if n and n.startswith("queue."):
                p = ev.get("payload", {})
                evs.append({"name": n, "try": p.get("try"), "tries": p.get("tries"), "basis": p.get("basis"),
                            "remedy": p.get("remedy_code"), "blocked_by": (p.get("blocked_by") or "")[:24]})
        eaten = sum(1 for x in open(rx) if "CR_EATEN" in x) if os.path.exists(rx) else 0
        log("result", A_submitted_at=seen.get("[E2E-A]"), B_submitted_at=seen.get("[E2E-B]"), cr_eaten=eaten,
            final_depth=last_q[0] if last_q else None, events=evs)
        open(os.path.join(RUN, "final-screen.txt"), "w").write(
            rpc(sock, "surface.read_text", {"surface_id": sid}).get("result", {}).get("text", ""))
    finally:
        try:
            if sid is not None:
                rpc(sock, "surface.close", {"surface_id": sid})
        except Exception:
            pass
        stop.set()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
        log("done", run=RUN)


if __name__ == "__main__":
    main()
