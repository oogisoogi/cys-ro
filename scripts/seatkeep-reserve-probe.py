#!/usr/bin/python3 -I
# 출처: 독립 검증 좌석 탐침(TICKET=cysr-1116-seatkeep-verify-1120 · evidence/probe.py) 그대로 — T4 차단(예약이 surface.create 입구에만) 회귀용. 본문 무변.
"""독립 검증 탐침(기록만 · TICKET=cysr-1116-seatkeep-verify-1120) — 격리 HOME·격리 소켓 시험 cysd 만.

쓰임: probe.py <bin 폴더> <case> <out.jsonl>
  claim    : 미결(예약) 역할을 claim-role 로 새 좌석이 가져가는가(예약 관문 = surface.create 한 곳뿐인지)
  dedup    : 미결 worker-2 예약을 「worker」 요청 + dedup 이 가져가는가
  knoboff  : 입양 켬 데몬이 띄운 좌석 → 강제 종료 → 입양 끔 데몬 기동 = 고아 seatkeep · 같은 역할 새 좌석
"""
import json, os, re, shutil, signal, subprocess, sys, time

BIN, CASE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
R = f"/private/tmp/skv-{CASE[:4]}-{os.getpid() % 10000}"
SOCK = f"{R}/s/d.sock"
shutil.rmtree(R, ignore_errors=True)
for d in ("home", "tmp", "s", "packstate", "pack", "bin", "bin2", "logs"):
    os.makedirs(f"{R}/{d}")
for b in ("cys", "cysd", "cys-seatkeep"):
    for bd in ("bin", "bin2"):
        subprocess.run(["/bin/cp", "-c", os.path.join(BIN, b), f"{R}/{bd}/{b}"], check=True)
HOLD = f"{R}/bin/hold.py"
open(HOLD, "w").write(r'''#!/usr/bin/python3 -I
import os, sys, time, subprocess
log = open(sys.argv[1], "a", buffering=1)
log.write(f"START pid={os.getpid()} role={os.environ.get('CYS_ROLE','')}\n")
if len(sys.argv) > 2 and sys.argv[2] == "claim":
    r = subprocess.run([os.path.dirname(os.path.abspath(__file__)) + "/cys", "claim-role", sys.argv[3]], capture_output=True, text=True, timeout=30)
    log.write(f"CLAIMRES rc={r.returncode} sock={os.environ.get('CYS_SOCKET','')} {(r.stdout + r.stderr).replace(chr(10), ' ')[:400]}\n")
while True:
    time.sleep(1)
''')
os.chmod(HOLD, 0o755)
ENV = {"HOME": f"{R}/home", "USER": os.environ["USER"], "LOGNAME": os.environ["USER"], "TMPDIR": f"{R}/tmp",
       "CYS_SOCKET": SOCK, "CYS_STATE_DIR": f"{R}/packstate", "CYS_PACK_DIR": f"{R}/pack",
       "CYS_NO_OFFICE_BRIDGE": "1", "CYS_NO_AUTORESTORE": "1", "CYS_NO_AUTOSTART": "1", "PATH": f"{R}/bin:/usr/bin:/bin",
       "TERM": "xterm-256color", "LANG": "en_US.UTF-8"}
ON = dict(ENV, CYS_SEATKEEP="1", CYS_SEATKEEP_ADOPT="1")
OFF = dict(ENV)


def raw(*a, timeout=30):
    try:
        return subprocess.run([f"{R}/bin/cys", *a], env=ENV, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess([*a], 124, "", "timeout")


def cys(*a, timeout=30):
    """쓰기 명령 직전 소켓 단언 — 붙는 데몬의 소켓이 격리 경로가 아니면 즉시 끝낸다."""
    idn = raw("identify")
    sp = json.loads(idn.stdout).get("socket_path") if idn.returncode == 0 else None
    if sp != SOCK:
        raise SystemExit(f"소켓 단언 실패: {sp!r} ≠ {SOCK}")
    return raw(*a, timeout=timeout)


daemons = []


def start(tag, env, bindir="bin"):
    err = open(f"{R}/logs/cysd-{tag}.err", "w")
    p = subprocess.Popen([f"{R}/{bindir}/cysd"], env=env, stdout=err, stderr=err, stdin=subprocess.DEVNULL, start_new_session=True)
    daemons.append(p)
    t0 = time.time()
    while time.time() - t0 < 90:
        z = raw("identify")
        if z.returncode == 0 and json.loads(z.stdout).get("daemon_pid") == p.pid:
            assert json.loads(z.stdout).get("socket_path") == SOCK
            return p
        if p.poll() is not None:
            raise SystemExit(f"cysd {tag} rc {p.returncode}")
        time.sleep(0.05)
    raise SystemExit("cysd 무응답")


def mine():
    out = subprocess.run(["/bin/ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    return [(int(l.split()[0]), l.split(None, 1)[1]) for l in out.splitlines() if R in l]


def keepers():
    return [p for p, c in mine() if f"{R}/bin/cys-seatkeep" in c or f"{R}/bin2/cys-seatkeep" in c]


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def seat(role, log, *extra):
    args = ["new-surface", "--cwd", "/private/tmp", "--cmd", f"{HOLD} {log} {' '.join(extra)}".strip()]
    if role:
        args += ["--role", role]
    x = cys(*args)
    t = time.time()
    while not (os.path.exists(log) and open(log).read().startswith("START")) and time.time() - t < 15:
        time.sleep(0.05)
    pid = int(re.search(r"pid=(\d+)", open(log).readline()).group(1)) if os.path.exists(log) else None
    return x, pid


def kill_daemon(p, sig=signal.SIGKILL):
    os.kill(p.pid, sig)
    p.wait()


res = {"case": CASE, "R": R, "t": time.strftime("%H:%M:%S")}
try:
    if CASE in ("claim", "dedup"):
        d = start("0", ON)
        if CASE == "claim":
            x, p_old = seat("seatr", f"{R}/logs/old.log")
            res["old_create_rc"] = x.returncode
        else:
            x1, p_w1 = seat("worker", f"{R}/logs/w1.log")
            x2, p_old = seat("worker", f"{R}/logs/w2.log")
            res["roles_before"] = re.findall(r"worker[-\d]*", cys("list").stdout)
        time.sleep(1.0)
        kill_daemon(d)
        if CASE == "claim":
            d = start("1", ON, bindir="bin2")  # 다른 경로 cysd = 상호 확인 실패 → 미결 · 예약
        else:
            # worker-2 좌석만 미결로(시험 고정물: 그 좌석 등록부를 읽기 불가로 = registry_io) · worker 는 입양.
            skd = f"{R}/s/seatkeep"
            for n in os.listdir(skd):
                if n.endswith(".cysd.json") and json.load(open(f"{skd}/{n}")).get("role") == "worker-2":
                    os.chmod(f"{skd}/{n[:-len('.cysd.json')]}.json", 0)
            d = start("1", ON)
        time.sleep(1.0)
        err = open(f"{R}/logs/cysd-1.err").read()
        res["adopt_log"] = [l for l in err.splitlines() if "좌석 입양" in l][:4]
        res["old_seat_alive"] = alive(p_old)
        res["list_before"] = cys("list").stdout.strip().splitlines()[:6]
        if CASE == "claim":
            g = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatr", "--cmd", "sleep 1")
            res["gate_same_role_rc"] = g.returncode
            res["gate_reason"] = "seat_adopt_reserved" in (g.stdout + g.stderr)
            x, p_new = seat(None, f"{R}/logs/new.log", "claim", "seatr")
            t = time.time()
            while "CLAIMRES" not in open(f"{R}/logs/new.log").read() and time.time() - t < 30:
                time.sleep(0.1)
            res["claim_line"] = [l for l in open(f"{R}/logs/new.log").read().splitlines() if l.startswith("CLAIMRES")]
        else:
            x, p_new = seat("worker", f"{R}/logs/new.log")
            res["new_create_rc"] = x.returncode
        time.sleep(0.5)
        res["list_after"] = cys("list").stdout.strip().splitlines()[:8]
        res["old_seat_alive_after"] = alive(p_old)
    elif CASE in ("term", "updmv", "updrm"):
        # term = 정상 종료(SIGTERM) 뒤 재기동 · updmv = 강제 종료 뒤 실행 파일 3개를 rename 으로 갈아끼움(같은 바이트 새 inode) ·
        # updrm = 지우고 새로 복사(경로가 잠시 비는 교체) — 「교체」 뒤 입양이 서는가.
        d = start("0", ON)
        x, p_old = seat("seatu", f"{R}/logs/old.log")
        time.sleep(1.0)
        kill_daemon(d, signal.SIGTERM if CASE == "term" else signal.SIGKILL)
        if CASE != "term":
            for b in ("cys", "cysd", "cys-seatkeep"):
                dst = f"{R}/bin/{b}"
                if CASE == "updmv":
                    subprocess.run(["/bin/cp", "-c", os.path.join(BIN, b), dst + ".new"], check=True)
                    os.rename(dst + ".new", dst)
                else:
                    os.remove(dst)
                    time.sleep(0.2)
                    subprocess.run(["/bin/cp", "-c", os.path.join(BIN, b), dst], check=True)
        res["old_alive_gap"] = alive(p_old)
        d = start("1", ON)
        time.sleep(1.0)
        err = open(f"{R}/logs/cysd-1.err").read()
        res["adopt_log"] = [l for l in err.splitlines() if "좌석 입양" in l][:3]
        res["listed"] = "seatu" in cys("list").stdout
        res["old_alive"] = alive(p_old)
        g = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatu", "--cmd", "sleep 1")
        res["same_role_rc"] = g.returncode
    elif CASE == "knoboff":
        d = start("0", ON)
        x, p_old = seat("seatk", f"{R}/logs/old.log")
        time.sleep(1.0)
        kill_daemon(d)
        d = start("1", OFF)  # 같은 소켓 · 입양 노브 없이(롤백 · CLI 자동 기동 · 노브 빠진 기동 경로)
        time.sleep(1.0)
        res["list"] = cys("list").stdout.strip().splitlines()[:6]
        g = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatk", "--cmd", f"{HOLD} {R}/logs/dup.log")
        res["same_role_create_rc"] = g.returncode
        time.sleep(20)  # 고아가 스스로 끝나는가(첫 조종자 상한 15초보다 길게)
        res["keepers_after_20s"] = len(keepers())
        res["old_seat_alive_after_20s"] = alive(p_old)
        res["list_after"] = cys("list").stdout.strip().splitlines()[:6]
        res["seatkeep_files"] = sorted(os.listdir(f"{R}/s/seatkeep")) if os.path.isdir(f"{R}/s/seatkeep") else []
finally:
    for p in daemons:
        if p.poll() is None:
            p.send_signal(signal.SIGTERM)
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    for pid, _ in mine():
        if pid != os.getpid():
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    time.sleep(0.5)
    res["left_procs"] = len([p for p, _ in mine() if p != os.getpid()])
    print(json.dumps(res, ensure_ascii=False), flush=True)
    open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
