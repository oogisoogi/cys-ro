#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seat-root-agent-e2e.py — 「뿌리가 에이전트 자신인 유휴 좌석」 의 좌석 판정·큐 보류를 격리 실데몬으로 실연한다
(TICKET=cysr-1110-seat-state · 수리 전/후 바이너리 대조용 · CI 레인 밖 · 손으로 돌리는 증거 검체).

무엇을 재는가
  A 좌석: 뿌리 프로세스 = `claude 600`(= /bin/sleep 을 claude 라는 이름의 심링크로 · 자손 0 · 유휴 claude 좌석의 프로세스 꼴)
  B 좌석: 맨 셸(명령 없음 · 자손 0) — 대조군. 어느 바이너리에서도 empty 여야 한다(맨 셸 = Empty 계약).
  팩 agents.json = 이 맥 설치 팩 꼴(claude · claude-fable · claude-sonnet 이 전부 실행 파일 claude).
  판독: 틱 3회에 걸친 status 의 seat · A 에 큐 1건을 넣은 뒤의 queue_depth · queue_blocked_by.

격리: HOME·CYS_SOCKET·CYS_STATE_DIR·CYS_PACK_DIR·CYS_CONFIG_DIR·CYS_PACK_CAPTURES_DIR 전부 mkdtemp ·
  CYS_NO_AUTOSTART=1 · 좌석 CYS_* env 제거 · PATH 앞에 트립와이어 cys·cysd(불리면 hits.log) ·
  종료는 기록한 pid 에만 SIGTERM → SIGKILL(이름 일치 종료 없음).

실행: python3 seat-root-agent-e2e.py <cysd 바이너리> <cys 클라이언트 바이너리> [라벨]
  SEAT119_AGENTS=single 을 주면 팩 agents.json 을 쓰지 않는다(= 저장소 내장 팩의 claude 1종만 · 원인 대조군).
  SEAT119_AGENTS=shell 을 주면 셸이 실행 파일인 후보 둘(`zsh /opt/agents/a.sh` · `b.sh`)을 더한다(R2 · codex 1R HIGH 의
  실데몬판: 좌석 B 의 맨 셸 뿌리 `/bin/zsh -l` 이 그 후보 때문에 occupied 로 읽히면 안 된다).
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

AGENTS = {
    "claude": {"cmd": "claude --model claude-opus-5-5 --dangerously-skip-permissions"},
    "claude-fable": {"cmd": "claude --model claude-fable-5-1 --dangerously-skip-permissions"},
    "claude-sonnet": {"cmd": "claude --model claude-sonnet-5-5 --dangerously-skip-permissions"},
    "gemini": {"cmd": "~/.local/bin/agy --dangerously-skip-permissions"},
    "codex": {"cmd": "codex --dangerously-bypass-approvals-and-sandbox"},
    "grok": {"cmd": "grok"},
}


def main():
    cysd, cys = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    label = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(os.path.dirname(cysd))
    box = tempfile.mkdtemp(prefix="seat119-")
    for d in ("home/.cys", "state", "pack", "config", "captures", "trip", "bin"):
        os.makedirs(os.path.join(box, d))
    hits = os.path.join(box, "trip", "hits.log")
    for name in ("cys", "cysd"):
        p = os.path.join(box, "trip", name)
        with open(p, "w") as f:
            f.write('#!/bin/sh\necho "TRIP $0 $*" >> "%s"\nexit 97\n' % hits)
        os.chmod(p, 0o755)
    mode = os.environ.get("SEAT119_AGENTS")
    if mode != "single":
        agents = dict(AGENTS)
        if mode == "shell":
            agents.update({"zsh-a": {"cmd": "zsh /opt/agents/a.sh"}, "zsh-b": {"cmd": "zsh /opt/agents/b.sh"}})
        with open(os.path.join(box, "pack", "agents.json"), "w") as f:
            json.dump(agents, f)
    with open(os.path.join(box, "pack", "acl.json"), "w") as f:
        f.write('{"default":"allow","rules":[]}')
    fake = os.path.join(box, "bin", "claude")
    os.symlink("/bin/sleep", fake)  # 사본은 맥이 실행을 막는다(시스템 바이너리 서명) — 이름만 claude 인 심링크면 argv[0] 이 claude 다
    env = {k: v for k, v in os.environ.items() if not k.startswith("CYS_") and k != "CLAUDE_CONFIG_DIR"}
    sock = os.path.join(box, "cysd.sock")
    env.update(HOME=os.path.join(box, "home"), CYS_SOCKET=sock, CYS_STATE_DIR=os.path.join(box, "state"),
               CYS_PACK_DIR=os.path.join(box, "pack"), CYS_CONFIG_DIR=os.path.join(box, "config"),
               CYS_PACK_CAPTURES_DIR=os.path.join(box, "captures"), CYS_NO_AUTOSTART="1",
               CYS_NO_OFFICE_BRIDGE="1", CYS_NO_PERSONAL_HOOK_MERGE="1",
               PATH=os.path.join(box, "trip") + os.pathsep + "/usr/bin:/bin:/usr/sbin:/sbin")

    def cli(*args, timeout=15):
        return subprocess.run([cys] + list(args), env=env, capture_output=True, text=True, timeout=timeout)

    def status():
        r = cli("status", "--json")
        if r.returncode != 0:
            return None
        d = json.loads(r.stdout)
        rows = d.get("surfaces") or d.get("nodes") or d
        return list(rows.values()) if isinstance(rows, dict) else rows

    def children(pid):
        out = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout
        rows = [l.split(None, 2) for l in out.splitlines()]
        return [(int(r[0]), r[2]) for r in rows if len(r) == 3 and int(r[1]) == pid]

    print("== %s · cysd=%s" % (label, cysd), flush=True)
    log = open(os.path.join(box, "cysd.log"), "wb")
    dp = subprocess.Popen([cysd], env=env, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    roots = []
    try:
        t0 = time.time()
        while status() is None:
            if dp.poll() is not None or time.time() - t0 > 60:
                raise SystemExit("FATAL 데몬 기동 실패 rc=%s — %s" % (dp.poll(), os.path.join(box, "cysd.log")))
            time.sleep(0.3)
        a = cli("new-surface", "--role", "worker-e2e", "--cmd", fake + " 600")
        b = cli("new-surface", "--role", "worker-shell")
        ref_a, ref_b = a.stdout.strip().split()[-1], b.stdout.strip().split()[-1]
        print("좌석 A(뿌리=claude)=%s rc=%d · 좌석 B(맨 셸)=%s rc=%d" % (ref_a, a.returncode, ref_b, b.returncode), flush=True)
        time.sleep(2.0)
        roots = children(dp.pid)
        for pid, cmd in roots:
            print("  뿌리 pid %d :: %s :: 자손 %d" % (pid, cmd.replace(box, "<box>")[:90], len(children(pid))), flush=True)
        seats = {ref_a: [], ref_b: []}
        for _ in range(3):
            time.sleep(6.0)  # 워치독 틱(5초) 1회 이상
            for s in status() or []:
                if s.get("surface_ref") in seats:
                    seats[s["surface_ref"]].append(s.get("seat"))
        print("틱 3회 seat — A %s · B %s" % (seats[ref_a], seats[ref_b]), flush=True)
        q = cli("send", "--queued", "--surface", ref_a, "seat119-e2e-ping")
        print("큐 적재 rc=%d %s" % (q.returncode, (q.stdout + q.stderr).strip().replace(box, "<box>")[:160]), flush=True)
        time.sleep(13.0)  # 틱 2회
        for s in status() or []:
            if s.get("surface_ref") == ref_a:
                print("A 최종 — seat=%s queue_depth=%s queue_blocked_by=%s agent=%s" % (
                    s.get("seat"), s.get("queue_depth"), s.get("queue_blocked_by"), s.get("agent")), flush=True)
        ql = cli("queue", "list")
        print("queue list rc=%d :: %s" % (ql.returncode, " / ".join((ql.stdout + ql.stderr).strip().splitlines())[:300]), flush=True)
        for pid, cmd in roots:
            print("  끝 뿌리 pid %d 자손 %d" % (pid, len(children(pid))), flush=True)
    finally:
        for pid in [dp.pid] + [p for p, _ in roots]:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            dp.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.kill(dp.pid, signal.SIGKILL)
            dp.wait(timeout=5)
        time.sleep(0.5)
        left = []
        for pid, _ in roots:
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
                left.append(pid)
            except ProcessLookupError:
                pass
        log.close()
        trips = open(hits).read().strip().splitlines() if os.path.exists(hits) else []
        print("정리 — 데몬 rc=%s · 강제 종료한 뿌리 %s · 트립와이어 적중 %d" % (dp.poll(), left, len(trips)), flush=True)
        shutil.rmtree(box, ignore_errors=True)


if __name__ == "__main__":
    main()
