#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v116_num_e2e.py — TICKET=v116-num 설계 §9 T5(격리 cysd 1,000+ 좌석 모의) · T11(두 소켓) E2E

묻는 것: 제품 바이너리(target/debug/cysd) 그대로, 좌석을 1,050개 만들고 닫으면
  ⑴ 내부 번호 1~999 좌석은 보이는 번호 = 내부 번호
  ⑵ 1,000번째 좌석부터 「—」(display_no=null) + surface.numbers_alarm{kind:"exhausted"} 정확히 1건
  ⑶ 좌석 생성이 한 번도 막히지 않는다(4군 ③)
  ⑷ 내부 번호는 단조 증가
  ⑸ 처음부터 끝까지 살려 둔 대조군 좌석이 한 번도 닫히지 않는다(4군 ④ — 산 좌석 닫힘 0)
  ⑹(T11) 두 번째 격리 데몬(부서 역할)이 같은 #1 을 자기 좌석으로 풀고, 본부의 닫기·다 참이 영향 0
W 는 기본 24시간 그대로다(제품 바이너리에 시험 손잡이 없음) — 닫은 번호가 모두 막혀 999 에서 다 찬다.

격리 계약(불변): 자기 /tmp 짧은 경로 안에서만 산다(SUN_LEN) — 라이브 소켓·라이브 팩·~/.cys 무접촉.
  · 상속 CYS_* 변수는 목록째 끊는다 · HOME·CYS_PACK_DIR 격리 · CYS_NO_OFFICE_BRIDGE=1 · CYS_BOOT_GATES=0
  · CYS_NO_AUTORESTORE=1 · SHELL=/bin/sh(좌석마다 로그인 셸 프로필을 태우지 않게)
  · 데몬은 start_new_session 으로 띄우고 PGID 째 내린다(고아 0) · 끝나면 /tmp 폴더 삭제(--keep 이면 보존)

실행: python3 scripts/v116_num_e2e.py [--keep] [--n 1050]
exit: 0=전 항목 PASS · 1=FAIL(출력이 판정) · 2=하네스 자체 실패(관측 불가 — 결론 금지)
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYSD = os.path.join(ROOT, "target", "debug", "cysd")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


class Daemon:
    def __init__(self, tag):
        self.tmp = tempfile.mkdtemp(prefix=f"v116{tag}.", dir="/tmp")
        self.sock = os.path.join(self.tmp, "cys.sock")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, "pack"), exist_ok=True)
        self.log = os.path.join(self.tmp, "cysd.log")
        self.pgid = None
        self.alarms = []
        self._stream = None

    def env(self):
        e = {k: v for k, v in os.environ.items() if not k.startswith(("CYS_", "JAVIS_", "AITERM_"))}
        e.update({
            "HOME": self.home,
            "CYS_SOCKET": self.sock,
            "CYS_PACK_DIR": os.path.join(self.home, "pack"),
            "CYS_NO_AUTOSTART": "1",
            "CYS_NO_OFFICE_BRIDGE": "1",
            "CYS_BOOT_GATES": "0",
            "CYS_NO_AUTORESTORE": "1",
            "SHELL": "/bin/sh",
        })
        return e

    def start(self):
        f = open(self.log, "ab")
        p = subprocess.Popen([CYSD], env=self.env(), stdout=f, stderr=f,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        self.pgid = os.getpgid(p.pid)
        for _ in range(1200):  # 디버그 빌드 기동 대기 최대 60초
            if os.path.exists(self.sock):
                try:
                    self.rpc("system.ping", {})
                    break
                except OSError:
                    pass
            time.sleep(0.05)
        else:
            raise RuntimeError(f"데몬 기동 실패 — {self.log}")
        # 경보 구독(좌석을 만들기 전에)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(self.sock)
        s.sendall((json.dumps({"id": 1, "method": "events.stream",
                               "params": {"names": ["surface.numbers_alarm"]}}) + "\n").encode())
        self._stream = s
        threading.Thread(target=self._read_stream, daemon=True).start()
        time.sleep(0.2)

    def _read_stream(self):
        buf = b""
        while True:
            try:
                chunk = self._stream.recv(65536)
            except OSError:
                return
            if not chunk:
                return
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("name") == "surface.numbers_alarm":
                    self.alarms.append(ev.get("payload"))

    def rpc(self, method, params):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(30)
        s.connect(self.sock)
        s.sendall((json.dumps({"id": 1, "method": method, "params": params}) + "\n").encode())
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        s.close()
        return json.loads(buf.split(b"\n", 1)[0])

    def stop(self, keep):
        if self._stream:
            try:
                self._stream.close()
            except OSError:
                pass
        if self.pgid:
            try:
                os.killpg(self.pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if not keep:
            shutil.rmtree(self.tmp, ignore_errors=True)


def create(d, cmd="sleep 3600"):
    r = d.rpc("surface.create", {"cmd": cmd, "rows": 24, "cols": 80})
    if not r.get("ok"):
        raise RuntimeError(f"surface.create 실패: {r}")
    return r["result"]


def main():
    keep = "--keep" in sys.argv
    n = 1050
    if "--n" in sys.argv:
        n = int(sys.argv[sys.argv.index("--n") + 1])
    if not os.path.exists(CYSD):
        print(f"하네스 실패: {CYSD} 없음 — cargo build --bin cysd 먼저")
        return 2
    hq, dept = Daemon("hq"), Daemon("dept")
    results = []
    fails = []

    def check(name, ok, detail=""):
        results.append((name, ok, detail))
        if not ok:
            fails.append(name)

    try:
        hq.start()
        dept.start()
        t0 = time.time()
        control = create(hq)
        dept_seat = create(dept)
        seats = []  # (surface_id, display_no)
        create_fail = 0
        for i in range(n):
            try:
                r = create(hq)
            except RuntimeError as e:
                create_fail += 1
                print(f"  생성 실패 {i}: {e}")
                continue
            seats.append((r["surface_id"], r["display_no"]))
            c = hq.rpc("surface.close", {"surface_id": r["surface_id"]})
            if not c.get("ok"):
                raise RuntimeError(f"surface.close 실패: {c}")
        elapsed = time.time() - t0
        time.sleep(0.5)  # 마지막 경보가 구독자에 닿을 시간

        ids = [control["surface_id"]] + [s for s, _ in seats]
        disp = {control["surface_id"]: control["display_no"], **dict(seats)}
        small = [(s, disp[s]) for s in ids if s <= 999]
        big = [(s, disp[s]) for s in ids if s >= 1000]
        check("⑴ 내부 1~999 좌석은 보이는 번호 = 내부 번호",
              all(dn == s for s, dn in small) and len(small) == 999,
              f"좌석 {len(small)}개 · 어긋남 {[x for x in small if x[0] != x[1]][:5]}")
        check("⑵ 1,000번째부터 「—」",
              len(big) == n + 1 - 999 and all(dn is None for _, dn in big),
              f"좌석 {len(big)}개 · 번호 있음 {[x for x in big if x[1] is not None][:5]}")
        exhausted = [a for a in hq.alarms if a.get("kind") == "exhausted"]
        check("⑵ exhausted 경보 정확히 1건", len(exhausted) == 1,
              f"exhausted {len(exhausted)} · 전체 경보 {[a.get('kind') for a in hq.alarms]}")
        check("⑶ 좌석 생성이 한 번도 막히지 않음", create_fail == 0 and len(seats) == n,
              f"실패 {create_fail} · 성공 {len(seats)}/{n}")
        check("⑷ 내부 번호 단조 증가", all(a < b for a, b in zip(ids, ids[1:])),
              f"첫 {ids[:3]} · 끝 {ids[-3:]}")
        lst = hq.rpc("surface.list", {})["result"]["surfaces"]
        ctl = [x for x in lst if x["surface_id"] == control["surface_id"]]
        alive = bool(ctl) and not ctl[0]["exited"]
        try:
            os.kill(ctl[0]["pid"], 0) if ctl else None
        except ProcessLookupError:
            alive = False
        check("⑸ 대조군 좌석 생존(산 좌석 닫힘 0)", alive and len(lst) == 1,
              f"목록 {len(lst)}개 · 대조군 {ctl[:1]}")
        res = hq.rpc("surface.resolve_display", {"display_no": 1})
        check("⑸ #1 → 대조군", res.get("ok") and res["result"]["surface_id"] == control["surface_id"], str(res)[:200])
        # T11 — 부서 데몬
        dres = dept.rpc("surface.resolve_display", {"display_no": 1})
        check("⑹ 부서 #1 → 부서 좌석(본부와 다른 좌석)",
              dres.get("ok") and dres["result"]["surface_id"] == dept_seat["surface_id"]
              and dres["result"]["socket"] == dept.sock and res["result"]["socket"] == hq.sock,
              str(dres)[:200])
        check("⑹ 부서는 본부 경보·다 참의 영향 0",
              dept.alarms == [] and dept_seat["display_no"] == 1
              and create(dept)["display_no"] == 2, f"부서 경보 {dept.alarms}")
        # 본부 데몬 로그에도 경보 1줄
        with open(hq.log, encoding="utf-8", errors="replace") as f:
            log_lines = [l for l in f if "surface.numbers_alarm kind=exhausted" in l]
        check("⑵ 데몬 로그 exhausted 1줄", len(log_lines) == 1, f"{len(log_lines)}줄")
        print(f"좌석 {n + 1}개 생성·{n}개 닫기 {elapsed:.1f}초")
    except Exception as e:  # 하네스 자체 실패 — 결론 금지
        print(f"하네스 실패: {e!r}")
        hq.stop(keep)
        dept.stop(keep)
        return 2
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name} — {detail}")
    hq.stop(keep)
    dept.stop(keep)
    if keep:
        print(f"보존: {hq.tmp} · {dept.tmp}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
