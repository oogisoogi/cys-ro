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
# 터짐(SKA_BURST=1 · M5 판별): 죽이기 전엔 짧은 줄(옛 cysd 가 따라잡아 seatkeep 읽기가 큐 자리 대기에 잠들지 않음) → SIGKILL 직후
# 터짐 파일을 만들면 그때부터 SKA_PAD 줄 — 조종자 없는 동안 역압(꼬리 상한)만이 끊긴 동안 출력을 막는다. (폭주만으로는 죽는 순간
# 읽기 스레드가 이미 큐 자리 대기라 그 줄에 닿지 않아 M5 를 못 가른다 — 11-20 실측.)
BURST = os.environ.get("SKA_BURST") == "1"
OUT = sys.argv[4] if len(sys.argv) > 4 else None
# reserve = 입양 실패 좌석(미결)의 역할 예약 시험(codex T4 1R #1): 두 번째 cysd 를 다른 경로(bin2)에서 띄워 상호 확인을 일부러 실패시킨다.
# exitaway = 데몬 없는 사이 좌석이 끝남 → seatkeep 이 .exit 를 남기고 끝남 → 새 cysd 가 그 기록을 소비(codex T4 1R #6 · A10).
# token = 입양 + 좌석 토큰 이음(T5 · A8ⓓ′): 입양 뒤 좌석 안에서 「조상 체인이 끊긴」 고아 프로세스로 claim — 자기 토큰 = 성공 · 토큰 없음 = 실패
#   (체인으로는 못 닿음 = 토큰 길이 실제로 쓰였다는 대조) · 같은 세대 난수만 바꾼 토큰 = token_mismatch 거절. 끝에 토큰 문자열 누출 훑기.
# rotate = 입양 + 실제 `cys rotate`(T6 A1): 격리(비기본 소켓) 레인 = 옛 cysd 에 kill -TERM → 다음 identify 가 형제 cysd 자동 기동(노브 env 그대로).
#   SIGKILL 이 아니라 정상 종료 길(scoped 정리)도 좌석을 안 끝내는가 · ⑤ 복원이 같은 역할을 또 띄우지 않는가(좌석 START 줄 = 1).
#   SKA_ROTATE_DRAIN=1 = --skip-drain 없이(① 저장 검증 포함).
# norecord = 기록 없는 산 seatkeep(T6 D2 · 시험이 기록을 지움) → 새 cysd 가 관리용 종료·정리 · 예약 없음(같은 역할 rc 0).
# foreign = 같은 폴더에 소켓 이름만 다른 데몬 둘(독립 검증 m1) → 남의 seatkeep 을 판정·예약·종료 기록 소비하지 않는다 · 주인 데몬만 소비.
# pending = 미결 재시도·해제(독립 검증 M2) · SKA_PENDING = recover(등록부 권한 0 → 재시도 중 되돌림 → 입양) · fail(끝내 못 읽음 → 관리용 종료 ·
#   예약 풀림) · unknown(역할 없는 좌석 + 다른 경로 cysd = 신원이 안 서 끝낼 수 없는 역할 모름 미결 → 상한 60초 뒤 역할 있는 생성 rc 0).
# precheck = rotate 사전 점검(T6a 2-2): 다른 폴더(bin2)의 cys 로 rotate = 그 옆 cysd 는 산 seatkeep 을 입양 못 함 → rc 27 · 옛 데몬·좌석 그대로 →
#   같은 폴더(bin)의 cys 로 rotate = 점검 통과 → 교체 · 좌석 생존.
# cap = holder 총수 상한(T6a 2-6): CYS_SEATKEEP_MAX_HOLDERS=1 → 둘째 좌석 = 직접 PTY(seatkeep 1개 · 사건 seat.seatkeep_capped) → 데몬 SIGKILL 뒤 첫 좌석만 산다.
# launchd = D4(master 허락 · F10): 시험 cysd 를 사용자 launchd 시험 작업(라벨 com.cysr.test.t6.<pid> · launchctl submit = 살려 두기)으로 띄워
#   좌석 → launchctl remove(작업 내림 = launchd 가 작업 프로세스 그룹에 신호) → seatkeep·좌석 생존? → 새 cysd 가 입양 · finally 로 remove + list 0 확인.
# claude = A4/D5(master 허락 · 토큰 소량): 진짜 claude 좌석(SKA_CLAUDE_CONFIG = 프로필 · --setting-sources project · --model haiku)에 암호어를 말한 뒤
#   실제 cys rotate 를 SKA_ROUNDS(기본 5)번 · 매 회 「암호어가 뭐였지?」(질문엔 암호어 없음) → 화면의 암호어 수가 늘어야 · claude pid 같음.
# cost = A13 비용 숫자(판정선 없음 · 보고만): 좌석 SKA_COST_N(기본 "1,5,20")개를 차례로 채우며 seatkeep RSS 합·평균 · cysd RSS · 10초 CPU% (좌석 = 50ms 마다 한 줄).
# update = T6b D1 ⓐ: 격리 번들 R/apps/cysr.app 의 cysd 로 좌석 → SIGKILL → 업데이터 S9 흉내(정식 → .cysr.app.old-1 rename · 새 번들 복사) → 정식 자리
#   새 cysd = 입양 · 그다음 옛 번들 삭제 + 재기동 = 실행 파일 못 읽음 → 미결(ⓒ · 좌석은 건드리지 않음).
# symlink · ustuck = 독립 검증 skt6(surface:2317 · evidence/e2e-v.py) 재현 모드 그대로 옮김(ustuck 은 rotate 1회로 줄임):
#   symlink = PATH 의 링크 cys 로 rotate(주요 3) · ustuck = 옛 번들이 지워진(SKA_USTUCK_MOVE=1 = 옮겨진) 뒤의 끝낼 수 없는 미결(주요 1).
assert MODE in ("adopt", "bound", "direct", "reserve", "exitaway", "token", "rotate", "norecord", "foreign", "pending", "precheck", "cap", "launchd", "claude", "cost", "update", "symlink", "ustuck"), MODE
R = f"/private/tmp/ska-{MODE[:3]}-{os.getpid() % 10000}"
shutil.rmtree(R, ignore_errors=True)
for d in ("home", "tmp", "s", "packstate", "pack", "bin", "bin2", "logs"):
    os.makedirs(f"{R}/{d}")
for b in ("cys", "cysd", "cys-seatkeep"):
    src = os.path.join(BIN, b)
    if os.path.exists(src):
        # APFS 복제(사본 실행 = 같은 바이트 · 원본 빌드 산출물은 건드리지 않는다)
        subprocess.run(["/bin/cp", "-c", src, f"{R}/bin/{b}"], check=True)
        subprocess.run(["/bin/cp", "-c", src, f"{R}/bin2/{b}"], check=True)
SEAT = f"{R}/bin/seat.py"
open(SEAT, "w").write(r'''#!/usr/bin/python3 -I
import os, select, signal, sys, time
log = open(sys.argv[1], "a", buffering=1)
gap = float(sys.argv[2]) / 1000
pad = "x" * int(sys.argv[3]) if len(sys.argv) > 3 else ""
burst = sys.argv[4] if len(sys.argv) > 4 else None
log.write(f"START pid={os.getpid()} ppid={os.getppid()} t={time.time():.3f}\n")
def die(s, _):
    log.write(f"SIGNAL {s} t={time.time():.3f}\n"); os._exit(128 + s)
for s in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
    signal.signal(s, die)
root = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[1])))
def orphan_claim(kind):
    # 두 번 fork + setsid → 손자는 launchd 아래(조상 체인에 이 좌석이 없음) — claim 이 토큰으로만 인가될 수 있는 호출자.
    import subprocess
    if os.fork():
        return
    os.setsid()
    if os.fork():
        os._exit(0)
    time.sleep(0.3)
    env = {k: v for k, v in os.environ.items()}
    tok = env.get("CYS_SEAT_TOKEN", "")
    open(f"{root}/logs/tok.txt", "w").write(tok)  # 누출 훑기의 찾을 값(시험 산출물 · 훑기에서 뺀다)
    if kind == "notoken":
        env.pop("CYS_SEAT_TOKEN", None)
    elif kind == "tamper" and "." in tok:
        g, r = tok.split(".", 1)
        env["CYS_SEAT_TOKEN"] = g + "." + ("f" * len(r) if r != "f" * len(r) else "e" * len(r))
    env["CYS_SOCKET"] = f"{root}/s/d.sock"
    role = env.get("CYS_ROLE", "")
    r = subprocess.run([f"{root}/bin/cys", "claim-role", role], env=env, capture_output=True, text=True, timeout=30)
    out = (r.stdout + r.stderr).replace("\n", " ")
    log.write(f"CLAIMRES {kind} rc={r.returncode} ppid={os.getppid()} has_tok={'CYS_SEAT_TOKEN' in env} {out[:400]}\n")
    os._exit(0)
n = 0
buf = b""
while True:
    n += 1
    out = f"SEQ {n:08d} {pad if burst is None or os.path.exists(burst) else ''}\r\n".encode()
    os.write(1, out)
    log.write(f"S {n} {time.time():.4f} {len(out)}\n")
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
                if line.startswith(b"CLAIM "):
                    orphan_claim(line.decode().split()[1])
''')
os.chmod(SEAT, 0o755)
ENV = {"HOME": f"{R}/home", "USER": os.environ["USER"], "LOGNAME": os.environ["USER"], "TMPDIR": f"{R}/tmp",
       "CYS_SOCKET": f"{R}/s/d.sock", "CYS_STATE_DIR": f"{R}/packstate", "CYS_PACK_DIR": f"{R}/pack",
       # CYS_NO_AUTOSTART: 데몬이 없는 틈에 `cys` 가 노브 없는 cysd 를 스스로 띄워 잠금을 먼저 잡는 경합 차단(시험 데몬은 이 스크립트만 띄운다)
       "CYS_NO_OFFICE_BRIDGE": "1", "CYS_NO_AUTORESTORE": "1", "CYS_NO_AUTOSTART": "1", "PATH": f"{R}/bin:/usr/bin:/bin",
       "TERM": "xterm-256color", "LANG": "en_US.UTF-8"}
DENV = dict(ENV)
if MODE in ("adopt", "bound", "reserve", "exitaway", "token", "rotate", "norecord", "foreign", "pending", "precheck", "cap", "launchd", "claude", "cost", "update", "symlink", "ustuck"):
    DENV["CYS_SEATKEEP"] = "1"
if MODE in ("adopt", "reserve", "exitaway", "token", "rotate", "norecord", "foreign", "pending", "precheck", "cap", "launchd", "claude", "cost", "update", "symlink", "ustuck"):
    if MODE == "cap":
        DENV["CYS_SEATKEEP_MAX_HOLDERS"] = "1"
    DENV["CYS_SEATKEEP_ADOPT"] = "1"


def cys(*a, timeout=30):
    try:
        return subprocess.run([f"{R}/bin/cys", *a], env=ENV, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # 부하 속 첫 기동 직후 RPC 가 시한을 넘김(관측됨) — 실패 결과로 돌려 부르는 쪽이 판정·재시도한다.
        return subprocess.CompletedProcess([*a], 124, "", f"timeout {timeout}s")


def cys_at(sock, *a, timeout=30):
    """다른 격리 소켓(foreign 모드의 둘째 데몬)에 — 붙는 소켓을 identify 로 단언한 뒤에만 쓰기 명령."""
    env = dict(ENV, CYS_SOCKET=sock)
    run = lambda *b: subprocess.run([f"{R}/bin/cys", *b], env=env, capture_output=True, text=True, timeout=timeout)
    try:
        if a[0] != "identify":
            z = run("identify")
            if z.returncode != 0 or json.loads(z.stdout).get("socket_path") != sock:
                raise SystemExit(f"소켓 단언 실패: {sock}")
        return run(*a)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess([*a], 124, "", f"timeout {timeout}s")


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class PidDaemon:
    """rotate 가 띄운(이 시험의 자식이 아닌) cysd — Popen 과 같은 손잡이 몇 개만(pid 로만 신호 · 이름 일치 종료 없음)."""
    def __init__(self, pid):
        self.pid = pid
    def poll(self):
        return None if alive(self.pid) else 0
    def send_signal(self, sig):
        try:
            os.kill(self.pid, sig)
        except OSError:
            pass
    def wait(self, timeout=None):
        t = time.time()
        while alive(self.pid):
            if timeout is not None and time.time() - t > timeout:
                raise subprocess.TimeoutExpired("cysd", timeout)
            time.sleep(0.05)
        return 0
    def kill(self):
        self.send_signal(signal.SIGKILL)


rotate_rc = []
daemons = []
first_rpc = []  # (cysd pid, 첫 RPC 성공 벽시계) — A16 「첫 RPC 수락 > 마지막 입양」 대조


def start_daemon(tag, bindir="bin", sock=None, knobs_off=False):
    err = open(f"{R}/logs/cysd-{tag}.err", "w")
    env = dict(DENV, CYS_SOCKET=sock) if sock else dict(DENV)
    if knobs_off:
        env.pop("CYS_SEATKEEP", None)
        env.pop("CYS_SEATKEEP_ADOPT", None)
    p = subprocess.Popen([f"{R}/{bindir}/cysd"], env=env, stdout=err, stderr=err, stdin=subprocess.DEVNULL, start_new_session=True)
    daemons.append(p)
    t0 = time.time()
    while time.time() - t0 < 90:  # 첫 기동은 팩 설치(약 500 파일)로 부하 속에서 30초를 넘길 수 있다
        z = cys_at(sock, "identify") if sock else cys("identify")
        if z.returncode == 0:
            idn = json.loads(z.stdout)
            if idn.get("daemon_pid") == p.pid:
                first_rpc.append((p.pid, time.time()))
                return p, round((time.time() - t0) * 1000)
        if p.poll() is not None:
            raise SystemExit(f"cysd {tag} 가 rc {p.returncode} 로 끝남 — {R}/logs/cysd-{tag}.err")
        time.sleep(0.05)
    raise SystemExit(f"cysd {tag} 가 90초 안에 응답 없음")


def keepers():
    """이 시험 폴더의 cys-seatkeep 프로세스 pid(명령 줄 = 시험 폴더 경로로 거른다 · 남의 seatkeep 은 세지 않는다)."""
    out = subprocess.run(["/bin/ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    return sorted(int(l.split()[0]) for l in out.splitlines() if f"{R}/bin/cys-seatkeep" in l)


def seat_lines(log):
    return open(log, errors="replace").read().splitlines()


if MODE == "exitaway":
    d, _ = start_daemon("0")
    log = f"{R}/logs/x0.log"
    x = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatx", "--cmd", f"{SEAT} {log} 50")
    t = time.time()
    while not (os.path.exists(log) and open(log).readline().startswith("START")) and time.time() - t < 10:
        time.sleep(0.05)
    seat_pid = int(re.search(r"pid=(\d+)", open(log).readline()).group(1))
    time.sleep(1.0)
    os.kill(d.pid, signal.SIGKILL)
    d.wait()
    os.kill(seat_pid, signal.SIGTERM)  # 데몬 없는 사이 좌석이 끝남(seat.py = rc 143)
    t = time.time()
    while keepers() and time.time() - t < 20:  # seatkeep: 조종자 없이 유예 뒤 .exit 를 남기고 끝남
        time.sleep(0.2)
    skdir = f"{R}/s/seatkeep"
    res = {"keepers_left": len(keepers()), "exit_files_before": sorted(n for n in os.listdir(skdir) if n.endswith(".exit"))}
    d, _ = start_daemon("1")
    time.sleep(1.0)
    errlog = open(f"{R}/logs/cysd-1.err").read()
    res["exit_files_after"] = sorted(n for n in os.listdir(skdir) if n.endswith(".exit"))
    res["record_files_after"] = sorted(n for n in os.listdir(skdir) if n.endswith(".cysd.json"))
    res["consumed_log"] = [l for l in errlog.splitlines() if "종료 기록 소비" in l or "좌석 입양 " in l][:3]
    res["listed"] = "seatx" in cys("list").stdout
    again = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatx", "--cmd", "sleep 30")
    res["same_role_after_rc"] = again.returncode
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    if again.stdout.strip():
        cys("close-surface", again.stdout.strip())
    d.send_signal(signal.SIGTERM)
    try:
        d.wait(timeout=10)
    except subprocess.TimeoutExpired:
        d.kill()
    sys.exit(0)

if MODE == "reserve":
    d, _ = start_daemon("0")
    log = f"{R}/logs/r0.log"
    x = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatr", "--cmd", f"{SEAT} {log} 50")
    sid = x.stdout.strip()
    t = time.time()
    while not (os.path.exists(log) and open(log).readline().startswith("START")) and time.time() - t < 10:
        time.sleep(0.05)
    seat_pid = int(re.search(r"pid=(\d+)", open(log).readline()).group(1))
    time.sleep(1.0)
    os.kill(d.pid, signal.SIGKILL)
    d.wait()
    if os.environ.get("SKA_FORGE_PID"):
        # codex 4R 차단 회귀: 기록의 seatkeep pid 를 죽은 값으로 바꾼다 → 기록 pid = 죽음 · 등록부 pid = 산 seatkeep → 미결 · 예약은 산 쪽 세대로.
        skd = f"{R}/s/seatkeep"
        for n in os.listdir(skd):
            if n.endswith(".cysd.json"):
                rj = json.load(open(f"{skd}/{n}"))
                rj["keeper_pid"], rj["keeper_start_us"] = 999999, 1
                json.dump(rj, open(f"{skd}/{n}", "w"))
        d, _ = start_daemon("1")
    else:
        d, _ = start_daemon("1", bindir="bin2")  # 다른 경로의 cysd = seatkeep·cysd 상호 확인 실패 → 미결
    time.sleep(1.0)
    res = {"seat_alive_after_failed_adopt": alive(seat_pid), "listed": "seatr" in cys("list").stdout}
    blocked = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatr", "--cmd", "sleep 30")
    res["same_role_create_rc"] = blocked.returncode
    res["same_role_refused_reason"] = "seat_adopt_reserved" in (blocked.stdout + blocked.stderr)
    other = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatq", "--cmd", "sleep 30")
    res["other_role_create_rc"] = other.returncode
    # 미결 seatkeep 을 끝낸다(이 시험이 띄운 그 pid 만) → 예약이 풀려야 한다.
    for k in keepers():
        os.kill(k, signal.SIGKILL)
    t = time.time()
    while alive(seat_pid) and time.time() - t < 10:
        time.sleep(0.1)
    res["seat_alive_after_keeper_kill"] = alive(seat_pid)
    again = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatr", "--cmd", "sleep 30")
    res["same_role_after_release_rc"] = again.returncode
    errlog = open(f"{R}/logs/cysd-1.err").read()
    res["adopt_log"] = [l for l in errlog.splitlines() if "좌석 입양" in l][:3]
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    for x2 in (other, again):
        ref = x2.stdout.strip()
        if ref:
            cys("close-surface", ref)
    d.send_signal(signal.SIGTERM)
    try:
        d.wait(timeout=10)
    except subprocess.TimeoutExpired:
        d.kill()
    if alive(seat_pid):
        os.kill(seat_pid, signal.SIGKILL)
    sys.exit(0)

def wait_start(log):
    t = time.time()
    while not (os.path.exists(log) and open(log).readline().startswith("START")) and time.time() - t < 10:
        time.sleep(0.05)
    return int(re.search(r"pid=(\d+)", open(log).readline()).group(1))


def stop_all():
    for p in daemons:
        if p.poll() is None:
            p.send_signal(signal.SIGTERM)
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    for k in keepers():
        os.kill(k, signal.SIGKILL)


if MODE == "norecord":
    skdir = f"{R}/s/seatkeep"
    d, _ = start_daemon("0")
    log = f"{R}/logs/n0.log"
    x = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatn", "--cmd", f"{SEAT} {log} 50")
    seat_pid = wait_start(log)
    time.sleep(1.0)
    os.kill(d.pid, signal.SIGKILL)
    d.wait()
    gone = [n for n in os.listdir(skdir) if n.endswith(".cysd.json")]
    for n in gone:
        os.remove(f"{skdir}/{n}")  # 기록 쓰기 실패 흉내(등록부·소켓·잠금은 그대로 · seatkeep·좌석은 산다)
    res = {"records_removed": len(gone), "keepers_before": len(keepers()), "seat_alive_before": alive(seat_pid)}
    d, _ = start_daemon("1")
    t = time.time()
    while alive(seat_pid) and time.time() - t < 10:
        time.sleep(0.1)
    res["keepers_after"] = len(keepers())
    res["seat_alive_after"] = alive(seat_pid)
    res["seat_end"] = [l for l in seat_lines(log) if l.startswith(("SIGNAL", "EOF"))][:2]
    res["files_after"] = sorted(os.listdir(skdir))
    errlog = open(f"{R}/logs/cysd-1.err").read()
    res["adopt_log"] = [l for l in errlog.splitlines() if "좌석 입양" in l][:3]
    again = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatn", "--cmd", "sleep 30")
    res["same_role_after_rc"] = again.returncode
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    if again.stdout.strip():
        cys("close-surface", again.stdout.strip())
    stop_all()
    if alive(seat_pid):
        os.kill(seat_pid, signal.SIGKILL)
    sys.exit(0)

if MODE == "foreign":
    skdir = f"{R}/s/seatkeep"
    sock_b = f"{R}/s/e.sock"  # 같은 폴더 · 다른 이름 = 같은 seatkeep 폴더 · 다른 시작 잠금(e.lock)
    # SKA_FOREIGN_B_OFF=1: 남의 데몬(b)을 노브 끔으로 — M1 의 노브 끔 고아 종료가 남의 산 seatkeep 을 끝내지 않는가(잠금 결박).
    b_off = os.environ.get("SKA_FOREIGN_B_OFF") == "1"
    a, _ = start_daemon("a")
    log = f"{R}/logs/f0.log"
    cys("new-surface", "--cwd", "/private/tmp", "--role", "seatf", "--cmd", f"{SEAT} {log} 50")
    seat_pid = wait_start(log)
    time.sleep(1.0)
    res = {}
    # ① 주인 데몬(a)이 산 채로 남의 데몬(b) 기동 — b 는 a 의 산 seatkeep 을 판정·예약하지 않는다.
    b, _ = start_daemon("b1", sock=sock_b, knobs_off=b_off)
    time.sleep(1.0)
    errb = open(f"{R}/logs/cysd-b1.err").read()
    res["b1_adopt_log"] = [l for l in errb.splitlines() if "좌석 입양" in l][:3]
    nb = cys_at(sock_b, "new-surface", "--cwd", "/private/tmp", "--role", "seatf", "--cmd", "sleep 30")
    res["b_same_role_rc"] = nb.returncode  # 예약이 없어야 rc 0(남의 좌석 역할을 예약하지 않음)
    if nb.stdout.strip():
        cys_at(sock_b, "close-surface", nb.stdout.strip())
    res["a_listed"] = "seatf" in cys("list").stdout
    res["seat_alive_1"] = alive(seat_pid)
    b.send_signal(signal.SIGTERM)
    b.wait(timeout=10)
    # ② 주인 데몬 강제 종료 → 데몬 없는 사이 좌석 끝남 → seatkeep 이 종료 기록을 남기고 끝남 → b 기동 = 소비하지 않음 → a 기동 = 소비.
    os.kill(a.pid, signal.SIGKILL)
    a.wait()
    os.kill(seat_pid, signal.SIGTERM)
    t = time.time()
    while keepers() and time.time() - t < 20:
        time.sleep(0.2)
    res["keepers_left"] = len(keepers())
    res["exit_before"] = sorted(n for n in os.listdir(skdir) if n.endswith(".exit"))
    b, _ = start_daemon("b2", sock=sock_b, knobs_off=b_off)
    time.sleep(1.0)
    errb = open(f"{R}/logs/cysd-b2.err").read()
    res["b2_adopt_log"] = [l for l in errb.splitlines() if "좌석 입양" in l][:3]
    res["b2_consumed"] = "종료 기록 소비" in errb
    res["exit_after_b"] = sorted(n for n in os.listdir(skdir) if n.endswith(".exit"))
    b.send_signal(signal.SIGTERM)
    b.wait(timeout=10)
    a, _ = start_daemon("a2")
    time.sleep(1.0)
    erra = open(f"{R}/logs/cysd-a2.err").read()
    res["a2_consumed"] = "종료 기록 소비" in erra
    res["exit_after_a"] = sorted(n for n in os.listdir(skdir) if n.endswith(".exit"))
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    stop_all()
    if alive(seat_pid):
        os.kill(seat_pid, signal.SIGKILL)
    sys.exit(0)

def adopt_status():
    z = cys("status", "--json")
    try:
        return json.loads(z.stdout)["daemon"].get("seat_adopt")
    except Exception:
        return {"error": (z.stdout + z.stderr)[:200]}


if MODE == "pending":
    kind = os.environ.get("SKA_PENDING", "recover")
    skdir = f"{R}/s/seatkeep"
    d, _ = start_daemon("0")
    log = f"{R}/logs/p0.log"
    role = None if kind == "unknown" else "seatp"
    args = ["new-surface", "--cwd", "/private/tmp", "--cmd", f"{SEAT} {log} 50"] + (["--role", role] if role else [])
    sid = cys(*args).stdout.strip()
    seat_pid = wait_start(log)
    time.sleep(1.0)
    os.kill(d.pid, signal.SIGKILL)
    d.wait()
    regs = [n for n in os.listdir(skdir) if n.endswith(".json") and not n.endswith(".cysd.json")]
    res = {"kind": kind, "regs": len(regs)}
    if kind in ("recover", "fail"):
        for n in regs:
            os.chmod(f"{skdir}/{n}", 0)  # 등록부 읽기 오류(registry_io) = 일시 실패 흉내(검증 탐침 고정물)
        d, _ = start_daemon("1")
    else:
        d, _ = start_daemon("1", bindir="bin2")  # 다른 경로 cysd = 연결 거절 · 관리용 종료도 신원(실행 파일)이 안 섬
    t1 = time.time()
    time.sleep(0.5)
    st0 = adopt_status()
    res["pending0"] = [(p["role"], p["reason"][:40], p["blocks_all"]) for p in (st0 or {}).get("pending", [])]
    probe = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatp" if role else "seatz", "--cmd", "sleep 30")
    res["blocked_rc0"] = probe.returncode
    if probe.stdout.strip():
        cys("close-surface", probe.stdout.strip())
    if kind == "recover":
        time.sleep(3.0)
        for n in regs:
            os.chmod(f"{skdir}/{n}", 0o600)
    deadline = {"recover": 20, "fail": 40, "unknown": 75}[kind]
    while time.time() - t1 < deadline:
        st = adopt_status() or {}
        if kind == "recover" and "seatp" in cys("list").stdout:
            break
        if kind == "fail" and not st.get("pending") and st.get("retry") == "done":
            break
        if kind == "unknown" and st.get("retry") == "done" and time.time() - t1 > 62:
            break
        time.sleep(1.0)
    res["secs"] = round(time.time() - t1, 1)
    st = adopt_status() or {}
    res["retry"] = st.get("retry")
    res["pending_end"] = [(p["role"], p["reason"][:60], p["blocks_all"]) for p in st.get("pending", [])]
    res["boot_end"] = [(o["result"], o["reason"][:60]) for o in st.get("boot", [])]
    res["listed"] = "seatp" in cys("list").stdout
    res["seat_alive"] = alive(seat_pid)
    res["seat_end"] = [l for l in seat_lines(log) if l.startswith(("SIGNAL", "EOF"))][:2]
    again = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatp" if role else "seatz", "--cmd", "sleep 30")
    res["role_create_rc_end"] = again.returncode
    if again.stdout.strip():
        cys("close-surface", again.stdout.strip())
    errlog = open(f"{R}/logs/cysd-1.err").read()
    res["adopt_log"] = [l for l in errlog.splitlines() if "좌석 입양" in l and "노브 켜짐" not in l][:4]
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    if kind != "recover" or not res["listed"]:
        stop_all()
    else:
        cys("close-surface", sid)
        time.sleep(1.0)
        stop_all()
    if alive(seat_pid):
        os.kill(seat_pid, signal.SIGKILL)
    sys.exit(0)

if MODE == "symlink":
    # 검증 좌석: PATH 의 cys 가 번들 cys 를 가리키는 심볼릭 링크(이 기계 /usr/local/bin/cys 와 같은 꼴)일 때 rotate 사전 점검.
    d, _ = start_daemon("0")
    log = f"{R}/logs/l0.log"
    cys("new-surface", "--cwd", "/private/tmp", "--role", "seatl", "--cmd", f"{SEAT} {log} 50")
    seat_pid = wait_start(log)
    time.sleep(1.0)
    os.makedirs(f"{R}/link"); os.symlink(f"{R}/bin/cys", f"{R}/link/cys")
    renv = dict(DENV); renv.pop("CYS_NO_AUTOSTART", None)
    z = cys("identify"); assert json.loads(z.stdout).get("socket_path") == f"{R}/s/d.sock", z.stdout
    old_pid = d.pid
    res = {}
    rr = subprocess.run([f"{R}/link/cys", "rotate", "--skip-depts", "--skip-drain"], env=renv, capture_output=True, text=True, timeout=400)
    res["via_symlink_rc"] = rr.returncode
    res["via_symlink_msg"] = [l[:240] for l in (rr.stdout + rr.stderr).splitlines() if "사전 점검" in l][:1]
    idn = cys("identify")
    res["daemon_same_after"] = idn.returncode == 0 and json.loads(idn.stdout).get("daemon_pid") == old_pid
    rr = subprocess.run([f"{R}/bin/cys", "rotate", "--skip-depts", "--skip-drain"], env=renv, capture_output=True, text=True, timeout=400)
    res["direct_rc"] = rr.returncode
    d.wait()
    idn = cys("identify")
    npid = json.loads(idn.stdout).get("daemon_pid") if idn.returncode == 0 else None
    if npid:
        daemons.append(PidDaemon(npid))
    time.sleep(1.0)
    res["seat_alive"] = alive(seat_pid)
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    stop_all()
    if alive(seat_pid):
        os.kill(seat_pid, signal.SIGKILL)
    sys.exit(0)

if MODE == "ustuck":
    # 검증 좌석(skt6-verify) 재현: 옛 번들(.cysr.app.old-1)이 지워진 뒤 그 번들의 seatkeep = 끝낼 수 없는 미결 → rotate·S7 점검이 계속 막히나.
    apps = f"{R}/apps"
    canon_app = f"{apps}/cysr.app"
    def make_bundle(dst):
        os.makedirs(f"{dst}/Contents/MacOS")
        for b in ("cys", "cysd", "cys-seatkeep"):
            subprocess.run(["/bin/cp", "-c", f"{R}/bin/{b}", f"{dst}/Contents/MacOS/{b}"], check=True)
    make_bundle(canon_app)
    mb = "apps/cysr.app/Contents/MacOS"
    res = {}
    d, _ = start_daemon("0", bindir=mb)
    log = f"{R}/logs/u0.log"
    sid = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatu", "--cmd", f"{SEAT} {log} 50").stdout.strip()
    seat_pid = wait_start(log)
    time.sleep(1.0)
    os.kill(d.pid, signal.SIGKILL); d.wait()
    os.rename(canon_app, f"{apps}/.cysr.app.old-1"); make_bundle(canon_app)
    d, _ = start_daemon("1", bindir=mb)
    time.sleep(1.5)
    res["listed_after_swap"] = "seatu" in cys("list").stdout
    os.kill(d.pid, signal.SIGKILL); d.wait()
    if os.environ.get("SKA_USTUCK_MOVE") == "1":
        os.makedirs(f"{R}/trash"); os.rename(f"{apps}/.cysr.app.old-1", f"{R}/trash/cysr.app")
    else:
        shutil.rmtree(f"{apps}/.cysr.app.old-1")
    d, _ = start_daemon("2", bindir=mb)
    time.sleep(16.0)  # M2 재시도 2초×5 + 끝내기 시도
    err = open(f"{R}/logs/cysd-2.err").read()
    res["d2_adopt_log"] = [l[:200] for l in err.splitlines() if "입양" in l and "노브" not in l][:6]
    st = cys("status", "--json")
    try:
        sa = json.loads(st.stdout)
        res["status_seat_adopt"] = json.dumps(sa.get("daemon", {}).get("seat_adopt") or sa.get("seat_adopt"), ensure_ascii=False)[:400]
    except Exception as e:
        res["status_seat_adopt"] = f"parse fail {e} {st.stdout[:200]}"
    res["seat_alive_d2"] = alive(seat_pid)
    renv = dict(DENV); renv.pop("CYS_NO_AUTOSTART", None)
    z = cys("identify"); assert json.loads(z.stdout).get("socket_path") == f"{R}/s/d.sock", z.stdout
    old_pid = d.pid
    res["rotates"] = []
    rr = subprocess.run([f"{R}/{mb}/cys", "rotate", "--skip-depts", "--skip-drain"], env=renv, capture_output=True, text=True, timeout=400)
    res["rotates"].append({"rc": rr.returncode, "msg": [l[:220] for l in (rr.stdout + rr.stderr).splitlines() if "사전 점검" in l][:1]})
    if rr.returncode == 0:
        d.wait() if isinstance(d, subprocess.Popen) else None
    idn = cys("identify")
    npid = json.loads(idn.stdout).get("daemon_pid") if idn.returncode == 0 else None
    if npid and npid != old_pid:
        daemons.append(PidDaemon(npid))
    res["daemon_same"] = npid == old_pid
    make_bundle(f"{apps}/.cysr.app.new-2")
    c = subprocess.run([f"{apps}/.cysr.app.new-2/Contents/MacOS/cysd", "--adopt-check", "--json", "--as-bundle", canon_app], env=DENV, capture_output=True, text=True, timeout=30)
    res["s7_precheck"] = {"rc": c.returncode, "out": c.stdout.strip()[:200]}
    c = subprocess.run([f"{R}/{mb}/cysd", "--adopt-check", "--json"], env=DENV, capture_output=True, text=True, timeout=30)
    res["old_cysd_precheck(start_old rotate 가 볼 것)"] = {"rc": c.returncode, "out": c.stdout.strip()[:200]}
    res["seat_alive_end"] = alive(seat_pid)
    res["seat_end"] = [l for l in seat_lines(log) if l.startswith(("SIGNAL", "EOF"))][:1]
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    stop_all()
    out = subprocess.run(["/bin/ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    for l in out.splitlines():
        if f"{R}/apps/" in l and "cys-seatkeep" in l:
            os.kill(int(l.split()[0]), signal.SIGKILL)
    if alive(seat_pid):
        os.kill(seat_pid, signal.SIGKILL)
    sys.exit(0)

if MODE == "update":
    apps = f"{R}/apps"
    canon_app = f"{apps}/cysr.app"
    def make_bundle(dst):
        os.makedirs(f"{dst}/Contents/MacOS")
        for b in ("cys", "cysd", "cys-seatkeep"):
            subprocess.run(["/bin/cp", "-c", f"{R}/bin/{b}", f"{dst}/Contents/MacOS/{b}"], check=True)
    make_bundle(canon_app)
    mb = "apps/cysr.app/Contents/MacOS"
    d, _ = start_daemon("0", bindir=mb)
    log = f"{R}/logs/u0.log"
    sid = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatu", "--cmd", f"{SEAT} {log} 50").stdout.strip()
    seat_pid = wait_start(log)
    time.sleep(1.0)
    res = {}
    os.kill(d.pid, signal.SIGKILL)
    d.wait()
    os.rename(canon_app, f"{apps}/.cysr.app.old-1")  # S9: 옛 번들 = 형제 .cysr.app.old-<seq>
    make_bundle(canon_app)                         # 새 판(같은 바이트 사본) = 정식 자리
    d, _ = start_daemon("1", bindir=mb)
    time.sleep(1.5)
    err = open(f"{R}/logs/cysd-1.err").read()
    res["adopt_log_after_swap"] = [l for l in err.splitlines() if "좌석 입양 " in l and "노브" not in l][:2]
    res["listed_after_swap"] = "seatu" in cys("list").stdout
    cys("send", "--surface", sid, "PINGUPD")
    cys("send-key", "--surface", sid, "Return")
    time.sleep(1.0)
    res["io_after_swap"] = any(l.startswith("IN PINGUPD") for l in seat_lines(log))
    res["seat_alive_after_swap"] = alive(seat_pid)
    # S7 앞 점검 흉내: 다음 판 스테이지 번들(.cysr.app.new-2)의 cysd — 그대로면 막힘(스테이지 옆 ≠) · --as-bundle 정식 = 통과.
    make_bundle(f"{apps}/.cysr.app.new-2")
    for tag, extra in (("staged_plain", []), ("staged_as_bundle", ["--as-bundle", canon_app])):
        c = subprocess.run([f"{apps}/.cysr.app.new-2/Contents/MacOS/cysd", "--adopt-check", "--json", *extra], env=DENV, capture_output=True, text=True, timeout=30)
        res[tag] = {"rc": c.returncode, "out": c.stdout.strip()[:160]}
    # 되감기 전 관리용 종료: 데몬이 살아 있으면 거절(rc 3).
    c = subprocess.run([f"{R}/{mb}/cysd", "--end-keepers", "--json"], env=DENV, capture_output=True, text=True, timeout=30)
    res["end_keepers_while_daemon"] = {"rc": c.returncode, "out": c.stdout.strip()[:120]}
    log2 = f"{R}/logs/u1.log"
    cys("new-surface", "--cwd", "/private/tmp", "--role", "seatu2", "--cmd", f"{SEAT} {log2} 50")
    seat2 = wait_start(log2)
    time.sleep(1.0)
    # ⓒ 옛 번들 삭제 뒤(지금 업데이터는 지우지 않음 — 다음 갱신 때 지운다는 주석뿐) = 실행 파일 못 읽음 → 미결 · 좌석 무접촉.
    os.kill(d.pid, signal.SIGKILL)
    d.wait()
    shutil.rmtree(f"{apps}/.cysr.app.old-1")
    d, _ = start_daemon("2", bindir=mb)
    time.sleep(1.5)
    err = open(f"{R}/logs/cysd-2.err").read()
    res["adopt_log_after_delete"] = [l for l in err.splitlines() if "좌석 입양 " in l and "노브" not in l][:2]
    res["seat_alive_after_delete"] = alive(seat_pid)
    # 데몬을 내린 뒤 --end-keepers: 정식 번들 seatkeep(seat2) = 끝냄 · 지워진 옛 번들 seatkeep(seat1) = 신원 불성립(ⓒ) 실패로 보고.
    d.send_signal(signal.SIGTERM)
    d.wait()
    c = subprocess.run([f"{R}/{mb}/cysd", "--end-keepers", "--json"], env=DENV, capture_output=True, text=True, timeout=60)
    res["end_keepers_no_daemon"] = {"rc": c.returncode, "out": c.stdout.strip()[:240]}
    time.sleep(0.5)
    res["seat2_alive_after_end"] = alive(seat2)
    res["seat2_end"] = [l for l in seat_lines(log2) if l.startswith(("SIGNAL", "EOF"))][:1]
    res["seat1_alive_after_end"] = alive(seat_pid)
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    stop_all()
    out = subprocess.run(["/bin/ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    for l in out.splitlines():
        if f"{R}/apps/" in l and "cys-seatkeep" in l:
            os.kill(int(l.split()[0]), signal.SIGKILL)
    for p in (seat_pid, seat2):
        if alive(p):
            os.kill(p, signal.SIGKILL)
    sys.exit(0)

if MODE == "cost":
    d, _ = start_daemon("0")
    def ps_of(pids):
        if not pids:
            return []
        out = subprocess.run(["/bin/ps", "-o", "rss=,time=", "-p", ",".join(map(str, pids))], capture_output=True, text=True).stdout
        return [l.split() for l in out.splitlines() if l.strip()]
    def cpu_secs(t):
        parts = t.split(":")
        return float(parts[-1]) + 60 * float(parts[-2]) + (3600 * float(parts[-3]) if len(parts) > 2 else 0)
    made = 0
    rows = []
    for n in [int(x) for x in os.environ.get("SKA_COST_N", "1,5,20").split(",")]:
        while made < n:
            log = f"{R}/logs/c{made}.log"
            cys("new-surface", "--cwd", "/private/tmp", "--role", f"cost{made}", "--cmd", f"{SEAT} {log} 50")
            wait_start(log)
            made += 1
        time.sleep(2.0)
        kp = keepers()
        a = ps_of(kp + [d.pid])
        time.sleep(10.0)
        b = ps_of(kp + [d.pid])
        rss = [int(x[0]) for x in b[:-1]]
        cpu = [(cpu_secs(y[1]) - cpu_secs(x[1])) / 10.0 * 100 for x, y in zip(a, b)]
        rows.append({"seats": n, "keepers": len(kp), "keeper_rss_kb_sum": sum(rss), "keeper_rss_kb_avg": round(sum(rss) / max(1, len(rss))),
                     "keeper_cpu_pct_sum": round(sum(cpu[:-1]), 2), "cysd_rss_kb": int(b[-1][0]), "cysd_cpu_pct": round(cpu[-1], 2)})
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps({"cost": rows}, ensure_ascii=False) + "\n")
    stop_all()
    sys.exit(0)

if MODE == "claude":
    word = "보라고래73"
    cfg = os.environ["SKA_CLAUDE_CONFIG"]
    real_home = os.environ["SKA_REAL_HOME"]
    claude = os.environ.get("SKA_CLAUDE_BIN", f"{real_home}/.local/bin/claude")
    cwd = f"{R}/proj"
    os.makedirs(cwd)
    d, _ = start_daemon("0")
    cmd = f"/usr/bin/env HOME={real_home} CLAUDE_CONFIG_DIR={cfg} {claude} --setting-sources project --model haiku"
    sid = cys("new-surface", "--cwd", cwd, "--role", "seatc5", "--cmd", cmd).stdout.strip()
    screen = lambda: cys("read-screen", "--surface", sid, "--lines", "400").stdout
    def wait_for(pred, secs):
        t = time.time()
        while time.time() - t < secs:
            sc = screen()
            if pred(sc):
                return sc
            time.sleep(1.0)
        return None
    def say(text):
        cys("send", "--surface", sid, text)
        time.sleep(0.5)
        cys("send-key", "--surface", sid, "Return")
    res = {"rounds": []}
    sc = wait_for(lambda x: "trust" in x.lower() or "❯" in x, 60)
    open(f"{R}/logs/claude-screen-0.txt", "w").write(sc or screen())
    if sc and "trust" in sc.lower():
        # 기본 선택 = 「No, exit」 — 아래로 한 칸(「Yes, I trust this folder」) 뒤 확정.
        cys("send-key", "--surface", sid, "Down")
        time.sleep(0.5)
        cys("send-key", "--surface", sid, "Return")
        wait_for(lambda x: "trust" not in x.lower(), 30)
    time.sleep(3.0)
    open(f"{R}/logs/claude-screen-1.txt", "w").write(screen())
    def pid_of():
        rows = [l for l in cys("list").stdout.splitlines() if "seatc5" in l]
        m = re.search(r"pid=(\d+)", rows[0]) if rows else None
        return m.group(1) if m else None
    res["claude_pid"] = pid_of()
    say(f"이 대화의 암호어는 {word} 이다. 기억해 둬. 지금은 OK 한 낱말로만 답해.")
    base = wait_for(lambda x: x.count(word) >= 1 and "OK" in x.split(word, 1)[-1], 120)
    res["told"] = base is not None
    count = (base or "").count(word)
    renv = dict(DENV)
    renv.pop("CYS_NO_AUTOSTART", None)
    for rnd in range(int(os.environ.get("SKA_ROUNDS", "5"))):
        old = json.loads(cys("identify").stdout).get("daemon_pid")
        rr = subprocess.run([f"{R}/bin/cys", "rotate", "--skip-depts", "--skip-drain"], env=renv, capture_output=True, text=True, timeout=400)
        t = time.time()
        while alive(old) and time.time() - t < 30:
            time.sleep(0.2)
        idn = cys("identify")
        npid = json.loads(idn.stdout).get("daemon_pid") if idn.returncode == 0 else None
        if npid:
            daemons.append(PidDaemon(npid))
        time.sleep(4.0)  # 입양 직후 큐 멈춤(3초) 뒤
        q = f"암호어가 뭐였지? 그 낱말 하나만 답해. ({rnd + 1}번째)"
        say(q)
        # 판정 = 이번 질문(회차 번호로 유일) 뒤에 암호어가 나왔는가 — 화면 전체 개수는 읽기 창에서 앞 줄이 밀려나면 안 늘어난다(11-20 실측).
        sc = wait_for(lambda x: q in x and word in x.rsplit(q, 1)[-1], 120)
        now = (sc or screen()).count(word)
        res["rounds"].append({"rotate_rc": rr.returncode, "new_daemon": bool(npid) and npid != old, "recalled": sc is not None,
                              "word_count": now, "same_pid": pid_of() == res["claude_pid"]})
        count = now
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    open(f"{R}/logs/claude-screen.txt", "w").write(screen())
    cys("close-surface", sid)
    time.sleep(2.0)
    stop_all()
    sys.exit(0)

if MODE == "launchd":
    label = f"com.cysr.test.t6.{os.getpid()}"
    lc = lambda *a: subprocess.run(["/bin/launchctl", *a], capture_output=True, text=True, timeout=30)
    res = {"label": label}
    seat_pid = None
    try:
        envargs = [f"{k}={v}" for k, v in DENV.items()]
        sub = lc("submit", "-l", label, "-o", f"{R}/logs/cysd-ld.err", "-e", f"{R}/logs/cysd-ld.err", "--", "/usr/bin/env", "-i", *envargs, f"{R}/bin/cysd")
        res["submit_rc"] = sub.returncode
        t = time.time()
        ld_pid = None
        while time.time() - t < 90:
            z = cys("identify")
            if z.returncode == 0:
                ld_pid = json.loads(z.stdout).get("daemon_pid")
                if json.loads(z.stdout).get("socket_path") != ENV["CYS_SOCKET"]:
                    raise SystemExit("소켓 단언 실패")
                break
            time.sleep(0.2)
        res["launchd_cysd_pid"] = ld_pid
        log = f"{R}/logs/l0.log"
        sid = cys("new-surface", "--cwd", "/private/tmp", "--role", "seatl", "--cmd", f"{SEAT} {log} 50").stdout.strip()
        seat_pid = wait_start(log)
        time.sleep(1.0)
        kp = keepers()
        res["pgid_cysd"] = os.getpgid(ld_pid) if ld_pid else None
        res["pgid_keepers"] = [os.getpgid(k) for k in kp]
        rm = lc("remove", label)
        res["remove_rc"] = rm.returncode
        t = time.time()
        while ld_pid and alive(ld_pid) and time.time() - t < 15:
            time.sleep(0.1)
        res["cysd_gone"] = not (ld_pid and alive(ld_pid))
        time.sleep(1.0)
        res["keepers_after_remove"] = len(keepers())
        res["seat_alive_after_remove"] = alive(seat_pid)
        res["seat_end"] = [l for l in seat_lines(log) if l.startswith(("SIGNAL", "EOF"))][:2]
        d, _ = start_daemon("1")
        time.sleep(1.5)
        res["listed_after"] = "seatl" in cys("list").stdout
        cys("send", "--surface", sid, "PINGLD")
        cys("send-key", "--surface", sid, "Return")
        time.sleep(1.0)
        res["io"] = any(l.startswith("IN PINGLD") for l in seat_lines(log))
    finally:
        lc("remove", label)
        res["launchctl_list_test_labels"] = sum(1 for l in lc("list").stdout.splitlines() if "com.cysr.test" in l)
        print(json.dumps(res, ensure_ascii=False), flush=True)
        if OUT:
            open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
        stop_all()
        if seat_pid and alive(seat_pid):
            os.kill(seat_pid, signal.SIGKILL)
    sys.exit(0)

if MODE == "cap":
    d, _ = start_daemon("0")
    l1, l2 = f"{R}/logs/k1.log", f"{R}/logs/k2.log"
    cys("new-surface", "--cwd", "/private/tmp", "--role", "seatk1", "--cmd", f"{SEAT} {l1} 50")
    p1 = wait_start(l1)
    cys("new-surface", "--cwd", "/private/tmp", "--role", "seatk2", "--cmd", f"{SEAT} {l2} 50")
    p2 = wait_start(l2)
    time.sleep(1.0)
    err = open(f"{R}/logs/cysd-0.err").read()
    res = {"keepers": len(keepers()), "capped_log": [l for l in err.splitlines() if "상한" in l and "seatkeep" in l][:1]}
    os.kill(d.pid, signal.SIGKILL)
    d.wait()
    t = time.time()
    while alive(p2) and time.time() - t < 5:
        time.sleep(0.1)
    res["first_alive"], res["second_alive"] = alive(p1), alive(p2)
    d, _ = start_daemon("1")
    time.sleep(1.0)
    lst = cys("list").stdout
    res["first_listed"], res["second_listed"] = "seatk1" in lst, "seatk2" in lst
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    stop_all()
    for p in (p1, p2):
        if alive(p):
            os.kill(p, signal.SIGKILL)
    sys.exit(0)

if MODE == "precheck":
    d, _ = start_daemon("0")
    log = f"{R}/logs/c0.log"
    cys("new-surface", "--cwd", "/private/tmp", "--role", "seatc", "--cmd", f"{SEAT} {log} 50")
    seat_pid = wait_start(log)
    time.sleep(1.0)
    renv = dict(DENV)
    renv.pop("CYS_NO_AUTOSTART", None)
    res = {}
    for tag, bd in (("bin2", "bin2"), ("bin", "bin")):
        c = subprocess.run([f"{R}/{bd}/cysd", "--adopt-check", "--json"], env=DENV, capture_output=True, text=True, timeout=30)
        res[f"check_{tag}"] = {"rc": c.returncode, "out": c.stdout.strip()[:200]}
    old_pid = d.pid
    rr = subprocess.run([f"{R}/bin2/cys", "rotate", "--skip-depts", "--skip-drain"], env=renv, capture_output=True, text=True, timeout=400)
    res["blocked_rotate_rc"] = rr.returncode
    res["blocked_msg"] = [l for l in (rr.stdout + rr.stderr).splitlines() if "사전 점검" in l][:1]
    idn = cys("identify")
    res["daemon_same_after_block"] = idn.returncode == 0 and json.loads(idn.stdout).get("daemon_pid") == old_pid
    res["seat_alive_after_block"] = alive(seat_pid)
    rr = subprocess.run([f"{R}/bin/cys", "rotate", "--skip-depts", "--skip-drain"], env=renv, capture_output=True, text=True, timeout=400)
    res["rotate_rc"] = rr.returncode
    open(f"{R}/logs/rotate-ok.txt", "w").write(rr.stdout + rr.stderr)
    d.wait()
    idn = cys("identify")
    npid = json.loads(idn.stdout).get("daemon_pid") if idn.returncode == 0 else None
    if npid:
        daemons.append(PidDaemon(npid))
    time.sleep(1.5)
    res["new_daemon"] = bool(npid) and npid != old_pid
    res["seat_alive_after_rotate"] = alive(seat_pid)
    res["listed_after_rotate"] = "seatc" in cys("list").stdout
    res["seat_end"] = [l for l in seat_lines(log) if l.startswith(("SIGNAL", "EOF"))][:2]
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(res, ensure_ascii=False) + "\n")
    stop_all()
    if alive(seat_pid):
        os.kill(seat_pid, signal.SIGKILL)
    sys.exit(0)

seats = []  # (surface ref, role, seat pid, log)
results = []
d, ms = start_daemon("0")
for rnd in range(ROUNDS):
    log = f"{R}/logs/s{rnd}.log"
    role = f"seat{rnd}"
    x = cys("new-surface", "--cwd", "/private/tmp", "--role", role, "--cmd", f"{SEAT} {log} {GAP_MS} {PAD}" + (f" {R}/burst" if BURST else ""))
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
    # ── 강제 종료(rotate 모드 = 실제 cys rotate) ──
    killed = d.pid
    t_kill = time.time()
    if MODE == "rotate":
        renv = dict(DENV)
        renv.pop("CYS_NO_AUTOSTART", None)  # 새 데몬 = rotate 의 identify 가 자동 기동(노브 env 를 그대로 넘김)
        args = ["rotate", "--skip-depts"] + ([] if os.environ.get("SKA_ROTATE_DRAIN") == "1" else ["--skip-drain"])
        rr = subprocess.run([f"{R}/bin/cys", *args], env=renv, capture_output=True, text=True, timeout=400)
        open(f"{R}/logs/rotate-{rnd}.txt", "w").write(rr.stdout + rr.stderr)
        if isinstance(d, subprocess.Popen):
            d.wait()
        alive_gap = {s[0]: alive(s[2]) for s in seats}
        t_restart = time.time()
        idn = cys("identify")
        npid = json.loads(idn.stdout).get("daemon_pid") if idn.returncode == 0 else None
        if not npid:
            raise SystemExit(f"rotate 뒤 새 데몬 없음 rc {rr.returncode}: {(rr.stdout + rr.stderr)[-400:]}")
        d = PidDaemon(npid)
        daemons.append(d)
        first_rpc.append((npid, t_restart))
        back_ms = round((t_restart - t_kill) * 1000)
        rotate_rc.append(rr.returncode)
    else:
        os.kill(killed, signal.SIGKILL)
        d.wait()
        if BURST:
            open(f"{R}/burst", "w").close()
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
        gap_rows = [l.split() for l in lines if l.startswith("S ") and t_kill <= float(l.split()[2]) < t_restart]
        gap_lines = len(gap_rows)
        # 줄마다 좌석이 적은 실제 바이트(4번째 칸) — 터짐 모드는 끊긴 뒤 줄 길이가 바뀐다
        gap_bytes = sum(int(r[3]) if len(r) > 3 else len(f"SEQ 00000000 {'x' * PAD}") + 2 for r in gap_rows)
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
            "gap_lines": gap_lines, "gap_bytes": gap_bytes, "line_bytes": len(f"SEQ 00000000 {'x' * PAD}") + 2,
            # 입양 모드 + 조종자 없음: 끊긴 뒤 자식 출력 ≤ 꼬리(1MiB) + PTY 커널 버퍼·읽기 조각 여유(256KiB) 여야 한다(역압 · M5 가 잡는다).
            "gap_bytes_ok": gap_bytes <= (1 << 20) + (256 << 10),
            "send_rc": (snd.returncode, sk.returncode), "input_logged": got_in, "echo_on_screen": got_echo,
            # 작성자 하나(A6 의 좌석 판정): 같은 좌석 기록에 START 가 1줄(복원이 같은 역할을 또 띄우면 같은 기록에 START 가 더 생김)
            "starts": sum(1 for l in lines if l.startswith("START")),
            "role_rows": sum(1 for l in lst.splitlines() if re.search(rf"\b{re.escape(s_role)}\b", l)),
        })
    ks = keepers()
    rec["keepers"] = len(ks)
    rec["live_seats"] = sum(1 for s in seats if alive(s[2]))
    results.append(rec)
    line = {"round": rnd, "alive": [x["alive"] for x in rec["seats"]], "listed": [x["role_listed"] for x in rec["seats"]],
            "screen_gt_before": [(x["screen_max_seq"] or 0) > x["produced_before_kill"] for x in rec["seats"]],
            "io": [x["input_logged"] and x["echo_on_screen"] for x in rec["seats"]],
            "seq_ok": [x["seq_missing"] == 0 and x["seq_dups"] == 0 for x in rec["seats"]],
            "gap_bytes_ok": [x["gap_bytes_ok"] for x in rec["seats"]],
            "keepers": rec["keepers"], "live_seats": rec["live_seats"], "back_ms": back_ms,
            "one_writer": [x["starts"] == 1 and x["role_rows"] == 1 for x in rec["seats"]],
            "rotate_rc": rotate_rc[-1] if rotate_rc else None}
    print(json.dumps(line, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")

# ── T5 token: 입양 뒤 고아 claim 3종 + 누출 훑기 ──
if MODE == "token":
    tk = {"claims": {}, "leaks": []}
    s_ref, s_role, s_pid, s_log = seats[0]
    for kind in ("own", "notoken", "tamper"):
        cys("send", "--surface", s_ref, f"CLAIM {kind}")
        cys("send-key", "--surface", s_ref, "Return")
        t = time.time()
        got = None
        while time.time() - t < 40 and got is None:
            got = next((l for l in seat_lines(s_log) if l.startswith(f"CLAIMRES {kind} ")), None)
            time.sleep(0.2)
        tk["claims"][kind] = got
    tok = open(f"{R}/logs/tok.txt").read().strip() if os.path.exists(f"{R}/logs/tok.txt") else ""
    tk["token_seen"] = bool(tok)
    # 진단 표면(목록·상태)도 훑기 대상에 넣는다
    open(f"{R}/logs/diag-list.txt", "w").write(cys("list").stdout)
    open(f"{R}/logs/diag-status.txt", "w").write(cys("status", "--json").stdout)
    if tok:
        # 찾을 값 = 진짜 토큰 + 그 난수 부분 + 거절 갈래(tamper)가 실어 보낸 바꾼 토큰(실패 응답·로그에도 0)
        g, r = tok.split(".", 1) if "." in tok else (tok, tok)
        tampered = g + "." + ("f" * len(r) if r != "f" * len(r) else "e" * len(r))
        needles = [tok.encode(), r.encode(), tampered.encode()]
        skip = {f"{R}/logs/tok.txt"} | {sl for (_, _, _, sl) in seats}
        for base, _dirs, files in os.walk(R):
            if base.startswith(f"{R}/bin") or base.startswith(f"{R}/home"):
                continue
            for fn in files:
                fp = os.path.join(base, fn)
                if fp in skip or not os.path.isfile(fp):
                    continue
                try:
                    data = open(fp, "rb").read()
                    if any(n in data for n in needles):
                        tk["leaks"].append(fp[len(R) + 1:])
                except OSError:
                    pass
        # 홈(격리)은 팩 설치 파일이 많아 크기 상한 안의 글 파일만
        for base, _dirs, files in os.walk(f"{R}/home"):
            for fn in files:
                fp = os.path.join(base, fn)
                try:
                    if os.path.getsize(fp) < (4 << 20) and any(n in open(fp, "rb").read() for n in needles):
                        tk["leaks"].append(fp[len(R) + 1:])
                except OSError:
                    pass
    c = tk["claims"]
    tk["ok"] = {
        "own_rc0": bool(c.get("own")) and " rc=0 " in c["own"],
        "notoken_refused": bool(c.get("notoken")) and " rc=0 " not in c["notoken"],
        "tamper_mismatch": bool(c.get("tamper")) and " rc=0 " not in c["tamper"] and "token_mismatch" in c["tamper"],
        "orphan": all(v and " ppid=1 " in v for v in c.values()),
        "no_leak": tk["token_seen"] and not tk["leaks"],
    }
    print(json.dumps({"token": tk["ok"], "leaks": tk["leaks"]}, ensure_ascii=False), flush=True)
    if OUT:
        open(OUT, "a").write(json.dumps({"token": tk}, ensure_ascii=False) + "\n")

# ── 전사(transcripts.db lines) 겹침: 입양 재생의 「옛 cysd 가 처리한」 앞부분이 다시 전사되면 같은 SEQ 가 두 번(M3·M7 이 잡는다) ──
time.sleep(2.0)  # 전사 쓰기 스레드 비움 대기
import sqlite3
tx = {"seats": []}
try:
    con = sqlite3.connect(f"file:{R}/s/transcripts.db?mode=ro", uri=True, timeout=10)
    for (s_ref, _, _, _) in seats:
        sid_n = int(s_ref.split(":")[-1])
        rows = [r[0] for r in con.execute("SELECT line FROM lines WHERE surface_id = ?", (sid_n,))]
        nums = [int(m) for l in rows for m in re.findall(r"SEQ (\d{8})", l)]
        tx["seats"].append({"surface": s_ref, "seq_rows": len(nums), "dups": len(nums) - len(set(nums)),
                            "missing": len(set(range(min(nums), max(nums) + 1)) - set(nums)) if nums else None})
    con.close()
except Exception as ex:
    tx["error"] = str(ex)
tx["dups_total"] = sum(x["dups"] for x in tx["seats"])
print(json.dumps({"transcript_dups_total": tx["dups_total"], "transcript_missing": [x["missing"] for x in tx["seats"]], "error": tx.get("error")}, ensure_ascii=False), flush=True)
if OUT:
    open(OUT, "a").write(json.dumps({"transcript": tx}, ensure_ascii=False) + "\n")

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
