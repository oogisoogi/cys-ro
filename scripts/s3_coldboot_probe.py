#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s3_coldboot_probe.py — TICKET=cys-phoenix-s3-master-persist S3-1 원인 규명 프로브(격리 전용)

묻는 것: **재부팅(비정상 종료) 뒤 topology.json 에서 master 가 사라지는 자리가 어디인가.**

격리 계약(불변): 자기 임시 디렉터리 안에서만 산다 — 라이브 소켓·라이브 팩·~/.cys·~/.claude 무접촉.
  · CYS_SOCKET  = <tmp>/cysd.sock      (라이브 소켓 아님)
  · CYS_PACK_DIR= <tmp>/pack           (라이브 팩 아님)
  · 데몬은 start_new_session 으로 띄우고 PGID 를 기록해 그룹째 내린다(고아 0).

실행: python3 scripts/s3_coldboot_probe.py [--keep]
exit: 0=관측 완료(판정은 출력이 진다) · 2=하네스 자체 실패(관측 불가 — 결론 금지)
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYS = os.path.join(ROOT, "target", "debug", "cys")
CYSD = os.path.join(ROOT, "target", "debug", "cysd")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


class Harness:
    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="s3-coldboot-")
        self.sock = os.path.join(self.tmp, "cysd.sock")
        self.pack = os.path.join(self.tmp, "pack")
        os.makedirs(self.pack, exist_ok=True)
        self.pgid = None
        self.log = os.path.join(self.tmp, "cysd.log")

    def env(self, **extra):
        e = dict(os.environ)
        e["CYS_SOCKET"] = self.sock
        e["CYS_PACK_DIR"] = self.pack
        e["CYS_NO_AUTOSTART"] = "1"     # cys CLI 가 죽은 소켓에 데몬을 자동 기동하지 않게
        e.update(extra)
        return e

    # ---------- 데몬 생명주기 ----------
    def start_daemon(self, **extra):
        f = open(self.log, "ab")
        p = subprocess.Popen([CYSD], env=self.env(**extra), stdout=f, stderr=f,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        self.pgid = os.getpgid(p.pid)
        with open(os.path.join(self.tmp, "cysd.pgid"), "w") as g:
            g.write(str(self.pgid))
        for _ in range(80):                       # 소켓 등장까지 폴링(고정 sleep 금지)
            if os.path.exists(self.sock) and self.cys("identify").returncode == 0:
                return p
            time.sleep(0.25)
        raise SystemExit(2)

    def kill_daemon_hard(self):
        """재부팅 근사 = SIGKILL(정상 종료 훅 없음). 그룹째 내려 PTY 자식도 함께 정리한다."""
        if self.pgid is None:
            return
        try:
            os.killpg(self.pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        for _ in range(40):
            if self.cys("identify").returncode != 0:
                break
            time.sleep(0.25)
        self.pgid = None

    def cys(self, *args, timeout=30):
        return subprocess.run([CYS, *args], env=self.env(), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout)

    # ---------- 관측 ----------
    def topo_path(self):
        return os.path.join(self.tmp, "topology.json")

    def topo(self):
        p = self.topo_path()
        if not os.path.exists(p):
            return None
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception as e:
            return {"_parse_error": str(e)}

    def roles_on_disk(self):
        t = self.topo()
        if not t or "entries" not in t:
            return None
        return [(e.get("role"), e.get("agent")) for e in t["entries"]]

    def cleanup(self, keep=False):
        self.kill_daemon_hard()
        if keep:
            print("[probe] 보존: %s" % self.tmp)
        else:
            shutil.rmtree(self.tmp, ignore_errors=True)


VERDICT_FAIL = False


def show(tag, h):
    r = h.roles_on_disk()
    t = h.topo() or {}
    print("  %-34s roles=%s tombstones=%s updated_at=%s"
          % (tag, r, t.get("tombstones"), t.get("updated_at")))
    return r


def main():
    keep = "--keep" in sys.argv
    for b in (CYS, CYSD):
        if not os.path.exists(b):
            print("[probe] 바이너리 없음: %s — cargo build --bin cys --bin cysd 먼저" % b)
            return 2
    h = Harness()
    print("[probe] 격리 tmp = %s" % h.tmp)
    try:
        # ── 1) 함대 구성: 오너 기계와 같은 모양으로 만든다 ──────────────────────
        #    master 는 설치기처럼 `new-surface --role master --cmd …`(agent 미등록),
        #    부서 노드는 같은 방식으로 4개. 실 에이전트는 띄우지 않는다(sleep 좌석).
        h.start_daemon(CYS_NO_AUTORESTORE="1")
        for role in ("master", "cso", "reviewer-claude-1", "reviewer-claude-2", "worker"):
            r = h.cys("new-surface", "--role", role, "--cmd", "sleep 300")
            if r.returncode != 0:
                print("[probe] new-surface %s 실패: %s" % (role, (r.stderr or r.stdout)[:200]))
                return 2
        print("\n[1] 구성 직후 — 설치기 경로(new-surface --role) 재현")
        before = show("생성 후", h)

        # ── 2) 재부팅 근사: SIGKILL(정상 종료 훅 없음) ────────────────────────
        h.kill_daemon_hard()
        print("\n[2] SIGKILL 직후 — 디스크 상태(데몬 없음)")
        after_kill = show("kill -9 후", h)

        # ── 3) 콜드부트: 같은 상태 디렉터리로 데몬 재기동(auto-restore 끔) ─────
        #    이 단계가 묻는 것 = **데몬 자신이 부팅하면서 topology 를 다시 쓰는가.**
        h.start_daemon(CYS_NO_AUTORESTORE="1")
        time.sleep(12)      # 오너 기계의 +9초 창을 덮는다(부팅 직후 기록을 놓치지 않게)
        print("\n[3] 콜드부트 +12s (auto-restore OFF) — 데몬 단독 부팅이 topology 를 건드리는가")
        after_boot = show("재기동 후", h)

        # ── 4) 판정 재료 요약 ────────────────────────────────────────────────
        print("\n[판정 재료]")
        print("  · 생성 후    : %s" % (before,))
        print("  · kill -9 후 : %s" % (after_kill,))
        print("  · 재기동 후  : %s" % (after_boot,))
        if after_boot == after_kill:
            print("  ⇒ 데몬 단독 부팅은 topology 를 **바꾸지 않는다**(파일 그대로).")
            print("    ⇒ 오너 기계의 '부팅 +9초 재기록'은 데몬 자신이 아니라 **그 창에서 도는 다른 것**이다.")
        elif after_boot == []:
            print("  ⇒ 데몬 단독 부팅이 topology 를 **비운다**(살아있는 좌석 0을 그대로 영속).")
        else:
            print("  ⇒ 데몬 단독 부팅이 topology 를 **부분 변경**했다 — 위 세 줄을 그대로 읽어라.")
        # ── 4) ★핵심 실험: 콜드부트 뒤 좌석 **하나**가 생기면 나머지는 어떻게 되는가 ──
        #    topology 는 actual-state 다(살아 있고 역할을 쥔 좌석만 조립). 부팅 직후 좌석 0에서
        #    누가 하나라도 만들어지면 그 순간 영속이 돌고, 살아있지 않은 나머지는 파일에서 사라진다.
        h.kill_daemon_hard()
        planted = {"schema_version": 1, "tombstones_rev": 0, "tombstones": [], "updated_at": 1.0,
                   "entries": [{"role": "master", "agent": None, "cwd": "/x"},
                               {"role": "cso", "agent": "fakeagent", "cwd": "/x"},
                               {"role": "reviewer-claude-1", "agent": "fakeagent", "cwd": "/x"},
                               {"role": "reviewer-claude-2", "agent": "fakeagent", "cwd": "/x"},
                               {"role": "worker", "agent": "fakeagent", "cwd": "/x"}]}
        with open(h.topo_path(), "w", encoding="utf-8") as f:
            json.dump(planted, f, ensure_ascii=False)
        h.start_daemon(CYS_NO_AUTORESTORE="1")
        print("\n[4] 오너 기계 모양으로 심은 뒤 콜드부트 — 좌석 0 상태")
        show("심은 직후", h)
        r = h.cys("new-surface", "--role", "cso", "--cmd", "sleep 300")
        assert r.returncode == 0, r.stderr
        print("    ↓ 좌석 **하나**(cso)만 생성했다")
        after_one = show("cso 좌석 1개 생성 후", h)
        kept = [r for r, _ in (after_one or [])]
        survived = "master" in kept
        print("\n  ⇒ 판정 축: 살아있지 않은 master 기록이 **살아남았는가** → %s"
              % ("PASS(살아남음)" if survived else "FAIL(사라짐 — 다음 부팅엔 되살릴 근거가 없다)"))
        global VERDICT_FAIL
        if not survived:
            VERDICT_FAIL = True
        # 묘비는 그대로 이겨야 한다(1급 원칙 무손상) — 폐역 역할은 보존 대상이 아니다.
        rt = h.cys("tombstone", "reviewer-claude-2")   # 의도적 폐역(데몬이 묘비 유일 작성자)
        h.cys("new-surface", "--role", "worker", "--cmd", "sleep 300")
        kept2 = [r for r, _ in (h.roles_on_disk() or [])]
        if rt.returncode == 0:
            ok_tomb = "reviewer-claude-2" not in kept2
            print("  ⇒ 묘비 축: 폐역 역할이 제거되는가 → %s (disk=%s)"
                  % ("PASS" if ok_tomb else "FAIL", kept2))
            if not ok_tomb:
                VERDICT_FAIL = True
        else:
            print("  ⚠ 묘비 축 미측정 — CLI 진입점 미해석(%s). 이 축은 rust 시험이 진다."
                  % (rt.stderr or rt.stdout or "")[:80].replace(chr(10), " "))

        # ── 5) restore 가 master 를 어떻게 다루는가(판정문 그대로) ──────────────
        h.kill_daemon_hard()
        with open(h.topo_path(), "w", encoding="utf-8") as f:
            json.dump(planted, f, ensure_ascii=False)
        h.start_daemon(CYS_NO_AUTORESTORE="1")
        for flag in ([], ["--include-master"]):
            rr = h.cys("restore", *flag, timeout=90)
            print("\n[5] cys restore %s → rc=%s" % (" ".join(flag) or "(플래그 없음)", rr.returncode))
            for line in (rr.stdout or "").splitlines():
                if line.strip():
                    print("      | %s" % line[:160])
            with open(h.topo_path(), "w", encoding="utf-8") as f:
                json.dump(planted, f, ensure_ascii=False)   # 다음 회차를 위해 원상 복구
        if VERDICT_FAIL:
            print("\n[probe] FAIL — S3 보존 불변식이 깨졌다")
            return 1
        print("\n[probe] PASS — 콜드부트 뒤 좌석이 생겨도 살아있지 않은 기록이 유지된다")
        return 0
    finally:
        h.cleanup(keep=keep)


if __name__ == "__main__":
    sys.exit(main())
