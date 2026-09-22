#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
d9_events_no_daemon_revival.py — TICKET=v115r2-daemon · D9 라이브 프로브(격리 전용)

묻는 것: **`cys events --reconnect` 구독이 소켓이 사라진 뒤 데몬을 되살리는가.**

실측 계보(09-22 VM): 행정부를 닫아 소켓을 지웠는데 부서 CSO 의 구독(pid 34937)이 cysd 40288 을
**자기 자식으로** 되살렸다 — depts.json 에서 제거된 부서의 좌석 0 고아 데몬. ↻ 때 교육부 데몬
45534·53833 도 부모가 구독이었다. 「자가치유」가 생명주기를 되돌려 고아를 만든 자리다.

측정 축 3개(전부 필요 — 하나만 재면 「안 쟀다」가 「없다」로 읽힌다):
  ①  구독이 데몬을 되살리지 않는다     → **cysd 프로세스 0**(+ 참고로 소켓 서비스 여부)
       ★계기 이력(중요): 1차 판본은 「소켓이 응답하는가」로만 재서 **뮤턴트에서 거짓 PASS** 를 냈다.
         M-D9-1(자격 복귀)이 실제로 cysd 를 낳았는데(pid 24711 · ppid 1 · 우리 tmp 소켓 env 로 확인)
         그 데몬은 tmp 가 지워진 뒤라 **서비스하지 못했고**, 그래서 「부활 0」으로 읽혔다.
         결함의 본체는 「서비스하는 데몬」이 아니라 **「존재하는 고아 프로세스」** 다(09-22 VM 의
         cysd 40288 도 좌석 0 이었다). ⇒ 축①의 정본 계기는 `ps -E` 로 센 프로세스 수다.
  ②  구독이 **정직하게 끝난다**         → 종료 + 「레지스트리에 없습니다」 사유
  ③★대조군: 하네스가 부활을 볼 수 있다 → autostart 가 허용된 명령(`cys identify`)은
       같은 자리에서 소켓을 되살린다. ③이 없으면 ①은 「측정이 대상에 안 닿았다」와 구별되지 않는다.

격리 계약(불변): 자기 임시 디렉터리 안에서만 산다 — 라이브 소켓·라이브 팩·~/.cys 무접촉.
  · CYS_SOCKET   = /tmp/d9-<pid>/cys-dept-probe/cys.sock  (부모 폴더 이름이 부서 이름 규약)
  · CYS_PACK_DIR = <tmp>/pack · CYS_DEPTS_JSON = <tmp>/depts.json
  · 짧은 /tmp 경로 — 긴 경로는 bind 가 SUN_LEN(104바이트) 초과로 패닉한다(실측 계보).
  · ⛔events 클라이언트에는 CYS_NO_AUTOSTART 를 **주지 않는다** — 그걸 주면 이 프로브는
    제품이 아니라 env 를 재는 셈이 된다(공허한 초록).
  · ★launchctl 껍데기(<tmp>/bin/launchctl → 항상 rc 1)를 PATH 맨 앞에 둔다. 【모의】 축 1개다.
    **왜 필요한가**: 맥에서 autostart 는 `launchd::should_delegate_autostart(is_loaded())` 가
    true 면 **`launchctl kickstart` 로 위임**한다. 그 판정은 **어느 소켓에 붙으려던 것인지를 보지
    않으므로**(`should_delegate_autostart(loaded) = loaded` — 실측), 격리 소켓의 연결 실패가
    **라이브 cysd 서비스**를 kickstart 한다. 껍데기를 두면 ⑴라이브 무접촉이 보장되고
    ⑵제품이 sibling spawn 경로(= 구독이 자기 자식으로 데몬을 낳던 그 경로)를 결정론으로 탄다.
    (이 소켓 무관 위임 자체는 이 티켓 범위 밖 관측이다 — 보고에 곁으로 올린다.)

실행: python3 scripts/d9_events_no_daemon_revival.py [--keep] [--wait N]
exit: 0=3축 전부 통과 · 1=축 실패(D9 미수리) · 2=하네스 자체 실패(관측 불가 — 결론 금지)
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYS = os.path.join(ROOT, "target", "debug", "cys")
CYSD = os.path.join(ROOT, "target", "debug", "cysd")
DEPT = "probe"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


def log(*a):
    print(*a, flush=True)


class Harness:
    def __init__(self, wait):
        self.wait = wait
        self.tmp = f"/tmp/d9-{os.getpid()}"
        self.sockdir = os.path.join(self.tmp, f"cys-dept-{DEPT}")
        self.sock = os.path.join(self.sockdir, "cys.sock")
        # ★autostart 에는 **레인↔팩 정합 게이트**가 이미 있다(`ensure_daemon_lane_pack`): 부서 소켓
        #   `cys-dept-<N>` 의 데몬은 팩이 `$HOME/.cys/pack-dept-<N>` 이어야 기동된다. 그래서 대조군을
        #   세우려면 HOME 까지 격리해야 한다(라이브 `~/.cys` 무접촉 + 게이트 충족). 1차 실행이 이
        #   게이트에 막혀 대조군이 거짓 FAIL 이었다 — 하네스 결함이었고 제품은 옳았다.
        self.pack = os.path.join(self.tmp, ".cys", f"pack-dept-{DEPT}")
        self.reg = os.path.join(self.tmp, "depts.json")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.sockdir, exist_ok=True)
        os.makedirs(self.pack, exist_ok=True)
        os.makedirs(self.bin, exist_ok=True)
        shim = os.path.join(self.bin, "launchctl")
        with open(shim, "w") as f:
            f.write("#!/bin/sh\n# D9 프로브 격리: launchd 위임을 끊어 라이브 cysd 무접촉 + sibling spawn 경로 강제\nexit 1\n")
        os.chmod(shim, 0o755)
        assert len(self.sock.encode()) < 100, f"소켓 경로가 SUN_LEN 에 가깝다: {self.sock}"
        self.daemon_pid = None
        self.cysd_log = os.path.join(self.tmp, "cysd.log")
        self.strays = []

    def env(self, autostart, **extra):
        e = dict(os.environ)
        e["CYS_SOCKET"] = self.sock
        e["CYS_PACK_DIR"] = self.pack
        e["CYS_DEPTS_JSON"] = self.reg
        e["PATH"] = self.bin + os.pathsep + e.get("PATH", "")
        e["HOME"] = self.tmp   # 라이브 ~/.cys 무접촉 + 레인↔팩 게이트 충족
        if not autostart:
            e["CYS_NO_AUTOSTART"] = "1"
        else:
            e.pop("CYS_NO_AUTOSTART", None)
        e.update(extra)
        return e

    def write_reg(self, present):
        depts = {DEPT: {"socket": self.sock, "cwd": self.tmp}} if present else {}
        with open(self.reg, "w") as f:
            json.dump({"depts": depts}, f)

    # ---------- 관측 ----------
    def cysd_procs(self):
        """우리 소켓을 env 로 든 cysd 프로세스 목록(pid). macOS `ps -E` 는 같은 uid 프로세스의
        환경변수를 함께 찍는다 — **존재**를 재는 유일한 결정론 계기다(소켓 응답은 파생 신호)."""
        # ★`-A` 필수 — 빠뜨리면 **내 세션 프로세스만** 나와 데몬을 놓친다(1차 판본이 그것으로
        #   대조군까지 거짓 FAIL 을 냈다). 그리고 판별은 **정확 소켓 일치 + 실행파일 이름**으로만
        #   한다: 같은 기계에 다른 워커의 격리 cysd(`/tmp/b1.sock` 등)와 라이브 앱 cysd 가 함께
        #   산다 — 패턴으로 죽이면 남의 것을 끈다(교차 사살 계보).
        try:
            r = subprocess.run(["ps", "-E", "-A", "-o", "pid=,command="],
                               capture_output=True, text=True, timeout=30)
        except Exception:
            return None            # 관측 실패 = None (0 과 구별한다)
        if r.returncode != 0:
            return None
        pids = []
        needle = f"CYS_SOCKET={self.sock}"
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line or needle not in line:
                continue
            head = line.split(None, 2)
            if len(head) < 2:
                continue
            exe = head[1]
            if not (exe.endswith("/cysd") or exe == "cysd"):
                continue
            try:
                pids.append(int(head[0]))
            except ValueError:
                pass
        return pids

    def identify(self, autostart):
        return subprocess.run([CYS, "identify"], env=self.env(autostart),
                              capture_output=True, text=True, timeout=30)

    def daemon_alive(self):
        """소켓이 응답하는가(= 데몬이 살아 있는가). autostart 금지로 물어 관측이 대상을 만들지 않게."""
        if not os.path.exists(self.sock):
            return None
        r = self.identify(autostart=False)
        if r.returncode != 0:
            return None
        try:
            return json.loads(r.stdout).get("daemon_pid")
        except Exception:
            return None

    # ---------- 생명주기 ----------
    def start_daemon(self):
        f = open(self.cysd_log, "ab")
        subprocess.Popen([CYSD], env=self.env(autostart=False), stdout=f, stderr=f,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        for _ in range(120):
            pid = self.daemon_alive()
            if pid:
                self.daemon_pid = pid
                self.reap_children()
                return pid
            time.sleep(0.25)
        raise SystemExit(2)

    @staticmethod
    def kill_pid(pid):
        """★pid 로 내린다(그룹 아님). cysd 는 자기를 데몬화해 **우리 직계 자식은 즉시 종료**한다 —
        그 자식은 좀비로 남고, macOS 는 좀비만 남은 그룹의 killpg 에 EPERM 을 돌려준다(실측:
        이 하네스 1차 실행이 정확히 그것으로 죽었다). 그래서 죽이는 대상은 **identify 가 알려준
        살아 있는 daemon_pid** 여야 하고, 우리 직계 자식은 waitpid 로 회수한다."""
        if not pid:
            return
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.kill(pid, sig)
            except (ProcessLookupError, PermissionError):
                return
            for _ in range(40):
                try:
                    os.kill(pid, 0)
                except (ProcessLookupError, PermissionError):
                    return
                time.sleep(0.1)

    def reap_children(self):
        """직계 자식 좀비 회수 — 안 하면 생존 판정이 좀비를 산 것으로 읽는다."""
        for _ in range(20):
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                return
            if pid == 0:
                return

    def cleanup(self, keep):
        self.kill_pid(self.daemon_pid)
        for pid in self.strays:
            self.kill_pid(pid)
        # ★전수 회수 — 「내가 아는 pid」만 지우면 프로브가 고아를 남긴다(1차 판본이 cysd 24711 을
        #   두 시간 남겼다). tmp 를 지우기 **전에** 소켓 env 로 전수 조회해 내린다.
        for _ in range(3):
            rest = self.cysd_procs()
            if not rest:
                break
            for pid in rest:
                self.kill_pid(pid)
        self.reap_children()
        if not keep:
            shutil.rmtree(self.tmp, ignore_errors=True)


def main():
    keep = "--keep" in sys.argv
    wait = 15
    if "--wait" in sys.argv:
        wait = int(sys.argv[sys.argv.index("--wait") + 1])
    for b in (CYS, CYSD):
        if not os.path.exists(b):
            log(f"[harness] 바이너리 없음: {b} — cargo build 먼저")
            return 2

    h = Harness(wait)
    verdicts = {}
    try:
        # ── 준비: 부서가 레지스트리에 있고 데몬이 살아 있다.
        h.write_reg(present=True)
        pid0 = h.start_daemon()
        log(f"[준비] 격리 데몬 기동 pid={pid0} socket={h.sock}")

        # ── 구독 시작(★autostart 허용 env — 제품이 스스로 거절해야 한다)
        ev_out = os.path.join(h.tmp, "events.out")
        ev_err = os.path.join(h.tmp, "events.err")
        with open(ev_out, "wb") as so, open(ev_err, "wb") as se:
            ev = subprocess.Popen([CYS, "events", "--category", "queue", "--reconnect"],
                                  env=h.env(autostart=True), stdout=so, stderr=se,
                                  stdin=subprocess.DEVNULL, start_new_session=True)
        time.sleep(2.0)
        if ev.poll() is not None:
            log(f"[harness] 구독이 시작 직후 죽었다(rc={ev.returncode}) — 관측 불가")
            log(open(ev_err, encoding="utf-8", errors="replace").read()[-800:])
            return 2
        log(f"[준비] 구독 가동 pid={ev.pid}")

        # ── 사건: 부서를 닫는다 = 데몬 정지 + 소켓 제거 + 레지스트리에서 삭제
        h.kill_pid(h.daemon_pid)
        h.daemon_pid = None
        if os.path.exists(h.sock):
            os.unlink(h.sock)
        h.write_reg(present=False)
        t0 = time.time()
        log(f"[사건] 부서 닫음 — 소켓 제거 · depts.json 에서 삭제(+{time.time()-t0:.1f}s)")

        # ── 축①②: N초 창 **전체**를 관측한다.
        #
        # ★1차 판본은 구독이 종료되면 관측을 멈췄다. 그게 구멍이었다 — 뮤턴트 M-D9-1(자격 복귀)에서
        #   구독은 4초에 죽고 **되살아난 cysd 는 그 뒤에 떠서** 축①이 거짓 PASS 를 냈다. 09-22 VM 의
        #   실제 고아(cysd 40288)도 낳은 쪽보다 오래 살았다. ⇒ 부활은 **창이 끝날 때까지** 센다.
        revived, revived_at, serving = None, None, None
        ev_exit_at = None
        while time.time() - t0 < wait:
            if revived is None:
                procs = h.cysd_procs()
                if procs is None:
                    verdicts["①cysd 프로세스 0"] = (False, "ps 관측 실패 — 측정 불능(결론 금지)")
                    break
                if procs:
                    revived, revived_at = procs, time.time() - t0
                    serving = h.daemon_alive()
            if ev_exit_at is None and ev.poll() is not None:
                ev_exit_at = time.time() - t0
            time.sleep(0.25)
        elapsed = time.time() - t0
        # 창이 끝난 뒤 한 번 더(막판 기동 포착)
        if revived is None:
            procs = h.cysd_procs() or []
            if procs:
                revived, revived_at = procs, elapsed
                serving = h.daemon_alive()
        if revived:
            h.strays.extend(revived)   # 프로브가 고아를 남기면 그것도 D9 다
        ev_rc = ev.poll()
        err_txt = open(ev_err, encoding="utf-8", errors="replace").read()

        verdicts.setdefault("①cysd 프로세스 0", (
            revived is None,
            f"cysd pid={revived or '없음'}"
            + (f"(+{revived_at:.1f}s · 서비스={'예' if serving else '아니오(좌석 0 고아)'})"
               if revived_at is not None else "")
            + f" · 창 {elapsed:.1f}s 전체 관측(ps -E)",
        ))
        verdicts["②구독 정직 종료"] = (
            ev_rc == 0 and "레지스트리" in err_txt,
            f"rc={ev_rc} · 사유문 {'있음' if '레지스트리' in err_txt else '없음'}"
            + (f" · 종료 +{ev_exit_at:.1f}s" if ev_exit_at is not None else " · 창 안에 미종료"),
        )
        if ev_rc is None:
            h.kill_pid(ev.pid)

        # ── 축③ 대조군: autostart 가 허용된 명령은 **같은 자리에서** 데몬을 되살린다.
        h.write_reg(present=True)
        r = h.identify(autostart=True)
        ctrl = []
        for _ in range(60):   # autostart 기동이 4s 를 넘겨 첫 identify 가 실패할 수 있다(실측)
            ctrl = h.cysd_procs() or []
            if ctrl:
                break
            time.sleep(0.25)
        h.strays.extend(ctrl)
        verdicts["③대조군 부활 관측"] = (
            bool(ctrl),
            f"cys identify(autostart 허용) → cysd pid={ctrl or '없음'} · rc={r.returncode}",
        )
    finally:
        h.cleanup(keep)

    log("")
    log("── D9 라이브 프로브 판정 ──")
    ok = True
    for k, (passed, detail) in verdicts.items():
        log(f"  {'PASS' if passed else 'FAIL'}  {k} — {detail}")
        ok = ok and passed
    log(f"판정: {'PASS(3/3)' if ok else 'FAIL'}")
    if keep:
        log(f"(--keep) 산출물: {h.tmp}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
