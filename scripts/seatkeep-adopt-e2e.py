#!/usr/bin/python3 -I
"""seatkeep 입양(T4) 실물 시험 — 격리 HOME·격리 소켓의 시험 cysd 만 다룬다(박사님 실사용 데몬·좌석 무접촉).

TICKET=cysr-1116-seatkeep-1119 · 설계 = docs/seatkeep/T4-DESIGN.md · 합격 기준 = holder DESIGN §5 A2(강제 종료 생존)·A5(출력)·A10(고아).

쓰임: scripts/seatkeep-adopt-e2e.py <bin 폴더(cys·cysd·cys-seatkeep)> <mode> <rounds> [out.jsonl]
  mode = adopt   : CYS_SEATKEEP=1 + CYS_SEATKEEP_ADOPT=1 (입양 켬)
         bound   : CYS_SEATKEEP=1 만(대조군 — 종속 모드 = 데몬이 죽으면 좌석도 죽어야 한다)
         direct  : 둘 다 끔(대조군 — 직접 PTY)
회차마다: 시험 cysd 기동 → 합성 좌석 1개 추가(앞 회차 좌석은 그대로 산다) → cysd SIGKILL → 1초(좌석은 계속 출력) → 새 cysd 기동 →
  ⑴ 전 좌석 pid 생존 · 좌석 기록에 SIGNAL/EOF 0 ⑵ `cys list` 에 같은 번호·역할 ⑶ read-screen 에 끊긴 동안 나온 줄까지 ⑷ 입력 왕복
  (send → 좌석 기록 IN · 화면 ECHO) ⑸ seatkeep 프로세스 수 = 산 좌석 수(고아 0).
끝: 마지막 cysd 를 SIGTERM · 좌석을 하나씩 close → seatkeep·좌석 0 확인.
"""
import json, os, re, shutil, signal, subprocess, sys, time

BIN, MODE, ROUNDS = sys.argv[1], sys.argv[2], int(sys.argv[3])
# 폭주 모드(A5 · 조종자 없는 동안 역압): SKA_PAD = 줄마다 덧붙일 바이트 · SKA_GAP_MS = 줄 사이 · SKA_LINES = read-screen 줄 수
PAD, GAP_MS, LINES = int(os.environ.get("SKA_PAD", "0")), os.environ.get("SKA_GAP_MS", "50"), os.environ.get("SKA_LINES", "200")
OUT = sys.argv[4] if len(sys.argv) > 4 else None
assert MODE in ("adopt", "bound", "direct"), MODE
R = f"/private/tmp/ska-{MODE[:3]}-{os.getpid() % 10000}"
shutil.rmtree(R, ignore_errors=True)
for d in ("home", "tmp", "s", "packstate", "pack", "bin", "logs"):
    os.makedirs(f"{R}/{d}")
for b in ("cys", "cysd", "cys-seatkeep"):
    src = os.path.join(BIN, b)
    if os.path.exists(src):
        # APFS 복제(사본 실행 = 같은 바이트 · 원본 빌드 산출물은 건드리지 않는다)
        subprocess.run(["/bin/cp", "-c", src, f"{R}/bin/{b}"], check=True)
SEAT = f"{R}/bin/seat.py"
open(SEAT, "w").write(r'''#!/usr/bin/python3 -I
import os, select, signal, sys, time
log = open(sys.argv[1], "a", buffering=1)
gap = float(sys.argv[2]) / 1000
pad = "x" * int(sys.argv[3]) if len(sys.argv) > 3 else ""
log.write(f"START pid={os.getpid()} ppid={os.getppid()} t={time.time():.3f}\n")
def die(s, _):
    log.write(f"SIGNAL {s} t={time.time():.3f}\n"); os._exit(128 + s)
for s in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
    signal.signal(s, die)
n = 0
buf = b""
while True:
    n += 1
    os.write(1, f"SEQ {n:08d} {pad}\r\n".encode())
    log.write(f"S {n} {time.time():.4f}\n")
    r, _, _ = select.select([0], [], [], gap)
    if r:
        b = os.read(0, 4096)
        if not b:
            log.write(f"EOF t={time.time():.3f}\n"); break
        buf += b
        while True:
            i = min([x for x in (buf.find(b"\r"), buf.find(b"\n")) if x >= 0], default=-1)
            if i < 0: break
            line, buf = buf[:i], buf[i+1:]
            if line:
                log.write(f"IN {line.decode('utf8','replace')} t={time.time():.4f}\n")
                os.write(1, b"ECHO " + line + b"\r\n")
''')
os.chmod(SEAT, 0o755)
ENV = {"HOME": f"{R}/home", "USER": os.environ["USER"], "LOGNAME": os.environ["USER"], "TMPDIR": f"{R}/tmp",
       "CYS_SOCKET": f"{R}/s/d.sock", "CYS_STATE_DIR": f"{R}/packstate", "CYS_PACK_DIR": f"{R}/pack",
       "CYS_NO_OFFICE_BRIDGE": "1", "CYS_NO_AUTORESTORE": "1", "PATH": f"{R}/bin:/usr/bin:/bin",
       "TERM": "xterm-256color", "LANG": "en_US.UTF-8"}
DENV = dict(ENV)
if MODE in ("adopt", "bound"):
    DENV["CYS_SEATKEEP"] = "1"
if MODE == "adopt":
    DENV["CYS_SEATKEEP_ADOPT"] = "1"


def cys(*a, timeout=30):
    return subprocess.run([f"{R}/bin/cys", *a], env=ENV, capture_output=True, text=True, timeout=timeout)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


daemons = []
first_rpc = []  # (cysd pid, 첫 RPC 성공 벽시계) — A16 「첫 RPC 수락 > 마지막 입양」 대조


def start_daemon(tag):
    err = open(f"{R}/logs/cysd-{tag}.err", "w")
    p = subprocess.Popen([f"{R}/bin/cysd"], env=DENV, stdout=err, stderr=err, stdin=subprocess.DEVNULL, start_new_session=True)
    daemons.append(p)
    t0 = time.time()
    while time.time() - t0 < 30:
        z = cys("identify")
        if z.returncode == 0:
            idn = json.loads(z.stdout)
            if idn.get("daemon_pid") == p.pid:
                first_rpc.append((p.pid, time.time()))
                return p, round((time.time() - t0) * 1000)
        if p.poll() is not None:
            raise SystemExit(f"cysd {tag} 가 rc {p.returncode} 로 끝남 — {R}/logs/cysd-{tag}.err")
        time.sleep(0.05)
    raise SystemExit(f"cysd {tag} 가 30초 안에 응답 없음")


def keepers():
    """이 시험 폴더의 cys-seatkeep 프로세스 pid(명령 줄 = 시험 폴더 경로로 거른다 · 남의 seatkeep 은 세지 않는다)."""
    out = subprocess.run(["/bin/ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    return sorted(int(l.split()[0]) for l in out.splitlines() if f"{R}/bin/cys-seatkeep" in l)


def seat_lines(log):
    return open(log, errors="replace").read().splitlines()


seats = []  # (surface ref, role, seat pid, log)
results = []
d, ms = start_daemon("0")
for rnd in range(ROUNDS):
    log = f"{R}/logs/s{rnd}.log"
    role = f"seat{rnd}"
    x = cys("new-surface", "--cwd", "/private/tmp", "--role", role, "--cmd", f"{SEAT} {log} {GAP_MS} {PAD}")
    sid = x.stdout.strip()
    if x.returncode != 0 or not sid:
        raise SystemExit(f"new-surface 실패 rc {x.returncode}: {x.stderr[:300]}")
    t = time.time()
    while not (os.path.exists(log) and open(log).readline().startswith("START")) and time.time() - t < 10:
        time.sleep(0.05)
    pid = int(re.search(r"pid=(\d+)", open(log).readline()).group(1))
    seats.append((sid, role, pid, log))
    time.sleep(1.0)
    produced_before = {s[0]: sum(1 for l in seat_lines(s[3]) if l.startswith("S ")) for s in seats}
    # ── 강제 종료 ──
    killed = d.pid
    t_kill = time.time()
    os.kill(killed, signal.SIGKILL)
    d.wait()
    time.sleep(1.0)  # 데몬 없는 1초 — 좌석은 계속 출력(입양 모드 = seatkeep 꼬리에 쌓임)
    alive_gap = {s[0]: alive(s[2]) for s in seats}
    t_restart = time.time()
    d, back_ms = start_daemon(str(rnd + 1))
    time.sleep(1.5)
    rec = {"mode": MODE, "round": rnd, "killed_daemon": killed, "new_daemon": d.pid, "daemon_back_ms": back_ms, "seats": []}
    lst = cys("list").stdout
    for (s_ref, s_role, s_pid, s_log) in seats:
        lines = seat_lines(s_log)
        ends = [l for l in lines if l.startswith(("SIGNAL", "EOF"))]
        nums = [int(l.split()[1]) for l in lines if l.startswith("S ")]
        r = cys("read-screen", "--surface", s_ref, "--lines", LINES)
        # 데몬 없는 동안 좌석이 낸 줄 수(입양 모드 + 폭주 = 꼬리 크기 근처에서 역압으로 멈춰야 한다)
        gap_lines = sum(1 for l in lines if l.startswith("S ") and t_kill <= float(l.split()[2]) < t_restart)
        seqs = [int(v) for v in re.findall(r"SEQ (\d{8})", r.stdout)]
        tag = f"hi{rnd}x{s_ref.split(':')[-1]}"
        snd = cys("send", "--surface", s_ref, tag)
        sk = cys("send-key", "--surface", s_ref, "Return")
        got_in, got_echo = False, False
        t = time.time()
        while time.time() - t < 5 and not (got_in and got_echo):
            got_in = any(l.startswith(f"IN {tag}") for l in seat_lines(s_log))
            got_echo = f"ECHO {tag}" in cys("read-screen", "--surface", s_ref, "--lines", "60").stdout
            time.sleep(0.1)
        row = [l for l in lst.splitlines() if re.search(rf"\b{re.escape(s_ref)}\b", l)]
        if os.environ.get("SKA_DUMP"):
            open(f"{R}/logs/screen-{rnd}-{s_ref.split(':')[-1]}.txt", "w").write(r.stdout)
        rec["seats"].append({
            "surface": s_ref, "role": s_role, "pid": s_pid,
            "alive_in_gap": alive_gap[s_ref], "alive": alive(s_pid), "end": ends,
            "listed": bool(row), "role_listed": bool(row) and s_role in row[0],
            "read_rc": r.returncode, "screen_max_seq": max(seqs) if seqs else None,
            # A5: 읽은 줄들의 순번이 이어지는가(빠짐 = 유실 · 겹침 = 재생 중복)
            "seq_missing": len(set(range(min(seqs), max(seqs) + 1)) - set(seqs)) if seqs else None,
            "seq_dups": len(seqs) - len(set(seqs)),
            "produced_before_kill": produced_before[s_ref], "produced_now": max(nums) if nums else 0,
            "gap_lines": gap_lines, "line_bytes": len(f"SEQ 00000000 {'x' * PAD}") + 2,
            "send_rc": (snd.returncode, sk.returncode), "input_logged": got_in, "echo_on_screen": got_echo,
        })
    ks = keepers()
    rec["keepers"] = len(ks)
    rec["live_seats"] = sum(1 for s in seats if alive(s[2]))
    results.append(rec)
    line = {"round": rnd, "alive": [x["alive"] for x in rec["seats"]], "listed": [x["role_listed"] for x in rec["seats"]],
            "screen_gt_before": [(x["screen_max_seq"] or 0) > x["produced_before_kill"] for x in rec["seats"]],
            "io": [x["input_logged"] and x["echo_on_screen"] for x in rec["seats"]],
            "seq_ok": [x["seq_missing"] == 0 and x["seq_dups"] == 0 for x in rec["seats"]],
            "keepers": rec["keepers"], "live_seats": rec["live_seats"], "back_ms": back_ms}
    print(json.dumps(line, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")

# ── A16: seatkeep 교체 기록(append-only .log)에서 공백 길이·교체 줄 수 · 첫 RPC 대조 ──
a16 = {"takeovers": 0, "expected_takeovers": 0, "gaps_ms": [], "rpc_before_adopt": 0, "per_seat": []}
skdir = f"{R}/s/seatkeep"
rpc_at = dict(first_rpc)
for i, (s_ref, _, s_pid, _) in enumerate(seats):
    a16["expected_takeovers"] += ROUNDS - i  # 좌석 i 는 회차 i..ROUNDS-1 의 강제 종료를 모두 겪었다
for name in sorted(os.listdir(skdir)) if os.path.isdir(skdir) else []:
    if not name.endswith(".log"):
        continue
    ev = [json.loads(l) for l in open(f"{skdir}/{name}") if l.strip()]
    tk = [e for e in ev if e.get("event") == "accept" and e.get("reason") == "takeover_after_disconnect"]
    a16["takeovers"] += len(tk)
    for e in tk:
        gap = (e["t"] - e["prev"]["disconnected_at"]) * 1000
        a16["gaps_ms"].append(round(gap))
        rpc = rpc_at.get(e["peer"]["pid"])
        if rpc is not None and rpc <= e["t"]:
            a16["rpc_before_adopt"] += 1
    a16["per_seat"].append({"log": name, "takeovers": len(tk)})
g = sorted(a16["gaps_ms"])
a16["gap_median_ms"] = g[len(g) // 2] if g else None
a16["gap_max_ms"] = g[-1] if g else None
print(json.dumps({k: a16[k] for k in ("takeovers", "expected_takeovers", "rpc_before_adopt", "gap_median_ms", "gap_max_ms")}, ensure_ascii=False), flush=True)
if OUT:
    open(OUT, "a").write(json.dumps({"a16": a16}, ensure_ascii=False) + "\n")

# ── 정리: 좌석 닫기 → seatkeep·좌석 0 ──
for (s_ref, _, _, _) in seats:
    cys("close-surface", s_ref)
t = time.time()
while time.time() - t < 10 and (keepers() or any(alive(s[2]) for s in seats)):
    time.sleep(0.2)
left = {"keepers_after_close": len(keepers()), "seats_after_close": sum(1 for s in seats if alive(s[2]))}
print(json.dumps(left, ensure_ascii=False), flush=True)
for p in daemons:
    if p.poll() is None:
        p.send_signal(signal.SIGTERM)
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
for s in seats:  # 남은 것이 있으면 이 시험이 띄운 좌석 pid 만 끝낸다(이름 일치 종료 금지)
    if alive(s[2]):
        os.kill(s[2], signal.SIGKILL)
for k in keepers():
    os.kill(k, signal.SIGKILL)
if OUT:
    open(OUT, "a").write(json.dumps({"final": left, "root": R}, ensure_ascii=False) + "\n")
