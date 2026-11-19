#!/usr/bin/env python3
"""바깥 크기 변경 뒤 PTY 크기 복구 게이트 — TICKET=cysr-tabs-sidebar-impl · 독립 검증 948 D5(master#07acca07 · 수동 실행 — CI 미배선).

원형 = 948 v_stty_bridge.py(헤드리스 UI 가 보낸 resize_surface 를 격리 cysd 실 PTY 에 그대로 재생 · 좌석 안 `stty size`).
이 게이트는 다리를 하나 더 놓는다: 격리 cysd 의 surface.list 「size」 칸(948 D5 로 더함)을 대역 목록에 그대로 싣는다.
장면: 좌석 W7 · 1920×1200 → 첫 맞춤 재생 → 바깥에서 `cys resize --surface <좌석 3> --rows 10 --cols 50` →
  12초 동안 0.5초마다 (앱이 보낸 resize 재생 + 실 크기를 대역 목록에 실음) → 좌석 3 의 `stty size` = 앱이 맞춘 크기로 돌아왔는가.
  같은 동안 다른 좌석으로 간 resize 수 = 0(같은 크기 재전송 0 유지).
격리: HOME·TMPDIR·소켓 = /tmp/cys-stg-<pid> · CYS_NO_AUTORESTORE=1 · 내가 띄운 데몬만 TERM→(10초)KILL · 끝에 남은 프로세스 0 확인.
실행: CHROME_PATH=<chrome-headless-shell> [GATE_DIST=<다른 번들>] cys run -- <playwright python3> ui/e2e/stty_gate.py
  (cargo build --bin cysd --bin cys 먼저 · target/debug 를 쓴다)
"""
import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("sbg", HERE / "statusboard_gate.py")
sbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbg)
DIST = Path(os.environ["GATE_DIST"]) if os.environ.get("GATE_DIST") else sbg.DIST
CYS = str(ROOT / "target/debug/cys")
CYSD = str(ROOT / "target/debug/cysd")
BASE = Path(f"/tmp/cys-stg-{os.getpid()}")
SOCK = BASE / "run/cysd.sock"

SPY = r"""
(() => {
  window.__calls = []; window.__SIZES = {};
  const orig = window.__TAURI__.core.invoke;
  window.__TAURI__.core.invoke = (cmd, args) => {
    if (cmd === 'resize_surface') window.__calls.push([args.surfaceId, args.cols, args.rows]);
    if (cmd === 'list_surfaces') return orig(cmd, args).then((r) => { for (const s of r.surfaces) { const z = window.__SIZES[s.surface_id]; if (z) s.size = { rows: z[1], cols: z[0] }; } return r; });
    return orig(cmd, args);
  };
})();
"""


def rpc(method, params=None):
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(10)
    s.connect(str(SOCK))
    s.sendall((json.dumps({"id": 1, "method": method, "params": params or {}}) + "\n").encode())
    got = b""
    while not got.endswith(b"\n"):
        c = s.recv(65536)
        if not c:
            break
        got += c
    s.close()
    v = json.loads(got)
    assert not v.get("error"), (method, v)
    return v["result"]


def main() -> int:
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    shutil.rmtree(BASE, ignore_errors=True)
    (BASE / "home").mkdir(parents=True)
    (BASE / "run").mkdir()
    env = {"PATH": os.environ["PATH"], "HOME": str(BASE / "home"), "TMPDIR": str(BASE), "CYS_SOCKET": str(SOCK), "CYS_NO_AUTORESTORE": "1"}
    d = subprocess.Popen([CYSD], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("번들:", DIST, "· 격리 데몬 pid", d.pid)
    try:
        t = time.time()
        while time.time() - t < 60:
            try:
                rpc("system.identify")
                break
            except (OSError, AssertionError):
                time.sleep(0.1)
        assert rpc("system.identify")["daemon_pid"] == d.pid
        seats = [dict(sock=s[0], sid=s[1], no=s[2], role=s[3], cwd=s[4], act=s[5], raw=s[6], approval=False, self=s[8], task=s[9], ctx=s[10]) for s in sbg.W7]
        real = {s["sid"]: rpc("surface.create", {"cwd": str(BASE / "home"), "rows": 35, "cols": 120})["surface_id"] for s in seats}
        back = {v: k for k, v in real.items()}
        time.sleep(1.0)
        n = [0]

        def stty(ui_sid):
            n[0] += 1
            f = BASE / f"sz-{n[0]}.txt"
            rpc("surface.send_text", {"surface_id": real[ui_sid], "text": f"stty size > {f}\r"})
            t0 = time.time()
            while time.time() - t0 < 10 and not (f.exists() and f.read_text().strip()):
                time.sleep(0.1)
            return f.read_text().strip() if f.exists() else None

        h = type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **kw: h(*a, directory=str(DIST), **kw))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1920, "height": 1200})
            pg = ctx.new_page()
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.add_init_script(sbg.SHIM.replace("__SEATS__", json.dumps(seats)).replace("__DEPTS__", "[]").replace("__BASE__", sbg.BASE))
            pg.add_init_script(SPY)
            pg.goto(f"http://127.0.0.1:{httpd.server_address[1]}/index.html")

            def bridge():
                calls = pg.evaluate("() => { const c = window.__calls; window.__calls = []; return c; }")
                for ui_sid, cols, rows in calls:
                    if ui_sid in real:
                        rpc("surface.resize", {"surface_id": real[ui_sid], "rows": rows, "cols": cols})
                sizes = {back[s["surface_id"]]: [s["size"]["cols"], s["size"]["rows"]] for s in rpc("surface.list")["surfaces"] if s["surface_id"] in back and s.get("size")}
                pg.evaluate(f"() => {{ window.__SIZES = {json.dumps(sizes)}; }}")
                return calls

            for _ in range(24):  # 12초 첫 화면(목록 4바퀴) — 첫 맞춤 재생
                bridge()
                pg.wait_for_timeout(500)
            app3 = stty(3)
            print("  첫 맞춤 뒤 좌석 3 stty =", app3)
            sbg.check(app3 is not None and app3 != "35 120", f"첫 맞춤이 실 PTY 에 닿음(좌석 3 = {app3})")
            r = subprocess.run([CYS, "resize", "--surface", f"surface:{real[3]}", "--rows", "10", "--cols", "50"], env=env, capture_output=True, text=True)
            sbg.check(r.returncode == 0, f"바깥 cys resize rc 0 ({r.stderr.strip()[:120]})")
            after_cli = stty(3)
            print("  바깥 변경 직후 좌석 3 stty =", after_cli)
            sbg.check(after_cli == "10 50", f"바깥 변경이 실제로 먹음 {after_cli}")
            sent = []
            for _ in range(24):  # 12초(목록 4바퀴) — 앱이 알아채고 되돌리는가
                sent += bridge()
                pg.wait_for_timeout(500)
            sent += bridge()
            final = stty(3)
            print("  12초 뒤 좌석 3 stty =", final, "· 그동안 보낸 resize", sent)
            sbg.check(final == app3, f"(D5) 좌석 3 PTY 가 앱 크기로 돌아옴 {final} = {app3}")
            sbg.check(all(c[0] == 3 for c in sent) and len(sent) <= 1, f"재전송 = 좌석 3 한 번뿐(같은 크기 재전송 0) {sent}")
            sbg.check(not errs, f"오류 0 {errs[:2]}")
            ctx.close()
            br.close()
        httpd.shutdown()
    finally:
        d.send_signal(signal.SIGTERM)
        try:
            d.wait(10)
        except subprocess.TimeoutExpired:
            d.kill()
            d.wait(5)
        time.sleep(1)
        left = subprocess.run(["pgrep", "-f", str(BASE)], capture_output=True, text=True).stdout.split()
        print("  데몬 종료", d.returncode, "· 남은 프로세스", left)
        sbg.check(not left, "남은 프로세스 0")
        shutil.rmtree(BASE, ignore_errors=True)
    print("\nRESULT:", "PASS" if not sbg.failures else f"FAIL ({len(sbg.failures)})")
    for f in sbg.failures:
        print("  FAIL:", f)
    return 0 if not sbg.failures else 1


if __name__ == "__main__":
    sys.exit(main())
