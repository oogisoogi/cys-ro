import json, os, socket, time, statistics, sys
sock = os.path.expanduser("~/.local/state/cys/cys.sock")
def call(m, p):
    s = socket.socket(socket.AF_UNIX); s.connect(sock)
    t0 = time.perf_counter(); s.sendall((json.dumps({"id": 1, "method": m, "params": p}) + "\n").encode())
    line = s.makefile().readline(); dt = (time.perf_counter() - t0) * 1000; s.close()
    return dt, json.loads(line)
def bench(tag):
    xs = []; n = None
    for _ in range(100):
        dt, r = call("surface.list", {}); xs.append(dt); n = len(r["result"]["surfaces"])
    xs.sort()
    print(json.dumps({"scene": tag, "seats": n, "p50_ms": round(statistics.median(xs), 2), "p95_ms": round(xs[94], 2), "max_ms": round(xs[-1], 2), "bytes_last": len(json.dumps(r))}))
bench("now")
made = []
for i in range(10):
    _, r = call("surface.create", {"cwd": os.path.expanduser("~"), "rows": 35, "cols": 120})
    if r.get("ok"): made.append(r["result"]["surface_id"])
    else: print("create fail", r.get("error")); break
time.sleep(3)
bench("plus-shells")
for sid in made: call("surface.close", {"surface_id": sid})
print("created", made)
