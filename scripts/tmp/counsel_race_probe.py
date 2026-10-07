"""임시 프로브(TICKET=cysr-118-counsel-race · 병합 전 제거) — CrossLockRace.test_writers_vs_mover 와 같은 판을 R 회 돌리며
쓰는 쪽마다 write_signals 반환값·대기 시간을, 옮기는 쪽은 move_sent 보유 시간을 잰다. 누락 줄을 「버린 쓰기(반환 0)」 와
「쓴 뒤 사라진 줄(반환 1)」 로 가른다. 사용: python counsel_race_probe.py <rounds> <wait_s|default> <dump_dir>"""
import json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(os.path.dirname(os.path.dirname(HERE)), "cysjavis-pack", "bin")
sys.path.insert(0, BIN)
import javis_counsel as jc  # noqa: E402

N, WAVE = 60, 20
WRITER = r'''
import json, sys, time
t0 = time.monotonic(); w0 = time.time()
sys.path.insert(0, sys.argv[1])
import javis_counsel as jc
op, wait = sys.argv[2], sys.argv[3]
kw = {} if wait == "default" else {"wait_s": float(wait)}
t1 = time.monotonic()
n = jc.write_signals("worker", [(op, "race.e1")], **kw)
t2 = time.monotonic()
print(json.dumps({"op": op, "n": n, "import_s": round(t1 - t0, 3), "write_s": round(t2 - t1, 3), "w0": w0}))
'''
MOVER = r'''
import json, os, sys, time
sys.dont_write_bytecode = True
client, cfg, stop = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, client)
from agora import collector
path = os.path.join(cfg, "counsel", "signals.jsonl")
rounds = moved = 0; holds = []
while True:
    done = os.path.exists(stop)
    lines = collector._signal_lines(path)
    if lines:
        t = time.monotonic(); moved += collector.move_sent(cfg, lines); holds.append(time.monotonic() - t)
    rounds += 1
    if done:
        break
    time.sleep(0.002)
holds.sort()
print(json.dumps({"rounds": rounds, "moved": moved, "moves": len(holds), "hold_max": round(holds[-1], 4) if holds else 0,
                  "hold_p50": round(holds[len(holds) // 2], 4) if holds else 0, "hold_sum": round(sum(holds), 3)}))
'''


def one(k, wait, dump):
    tmp = tempfile.mkdtemp(prefix="crp-")
    try:
        cfg, pack = os.path.join(tmp, "cfg"), os.path.join(tmp, "pack")
        os.makedirs(os.path.join(cfg, "counsel")); os.makedirs(pack)
        with open(os.path.join(pack, ".pack-version"), "w") as f:
            f.write("1.1.8\n")
        pin = jc._read_pin(os.path.dirname(BIN))
        client = os.path.join(tmp, "client")
        jc._extract(jc._blob_bytes(os.path.join(os.path.dirname(BIN), "install", "agora-client-%s.zip.b64" % pin["ver"]), pin), client)
        wpy, mpy, stop = os.path.join(tmp, "w.py"), os.path.join(tmp, "m.py"), os.path.join(tmp, "stop")
        open(wpy, "w").write(WRITER); open(mpy, "w").write(MOVER)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AGORA_CONFIG_DIR=cfg, CYS_PACK_DIR=pack)
        mover = subprocess.Popen([sys.executable, mpy, client, cfg, stop], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        ops = ["race.w%03d" % i for i in range(N)]
        recs = []
        try:
            for j in range(0, N, WAVE):
                ps = [subprocess.Popen([sys.executable, wpy, BIN, op, wait], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                      for op in ops[j:j + WAVE]]
                for p in ps:
                    o, e = p.communicate(timeout=120)
                    recs.append(json.loads(o) if o.strip() else {"op": "?", "err": e.decode("utf-8", "replace")[-300:]})
        finally:
            open(stop, "w").close()
            mo, me = mover.communicate(timeout=120)
        mstat = json.loads(mo) if mo.strip() else {"err": me.decode("utf-8", "replace")[-300:]}
        c = os.path.join(cfg, "counsel")
        raw = b""
        for n_ in ("signals.jsonl", "signals-sent.jsonl"):
            p_ = os.path.join(c, n_)
            if os.path.exists(p_):
                raw += open(p_, "rb").read()
        got = [json.loads(x)["op"] for x in raw.decode("utf-8").split("\n") if x]
        missing = sorted(set(ops) - set(got))
        dup = sorted({o for o in got if got.count(o) > 1})
        by = {r.get("op"): r for r in recs}
        dropped = [o for o in missing if by.get(o, {}).get("n") == 0]
        lost = [o for o in missing if by.get(o, {}).get("n") == 1]
        unknown = [o for o in missing if o not in dropped and o not in lost]
        ws = sorted(r.get("write_s", 0) for r in recs)
        out = {"round": k, "missing": len(missing), "dropped_n0": len(dropped), "LOST_after_write": lost, "unknown": unknown,
               "dup": dup, "write_s_max": ws[-1], "write_s_p50": ws[len(ws) // 2],
               "n0_write_s_min": min([by[o]["write_s"] for o in dropped], default=None), "mover": mstat}
        if missing or dup:
            d = os.path.join(dump, "round-%03d" % k)
            os.makedirs(d, exist_ok=True)
            for n_ in os.listdir(c):
                shutil.copy(os.path.join(c, n_), d)
            json.dump({"summary": out, "writers": recs}, open(os.path.join(d, "probe.json"), "w"), indent=1)
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    R, wait, dump = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    os.makedirs(dump, exist_ok=True)
    red = lost = 0
    for k in range(R):
        s = one(k, wait, dump)
        red += bool(s["missing"] or s["dup"]); lost += len(s["LOST_after_write"]) + len(s["dup"])
        print(json.dumps(s), flush=True)
    print("PROBE-SUMMARY wait=%s rounds=%d red=%d lost_after_write_or_dup=%d" % (wait, R, red, lost), flush=True)
