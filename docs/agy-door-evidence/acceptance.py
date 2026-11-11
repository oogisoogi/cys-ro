#!/usr/bin/env python3
"""agy 좌석 문 — 합격 ①②③ 실측(TICKET=cysr-agy-policy-exposure). 격리 하네스 데몬 + **가짜** agy/claude/codex.

★실제 agy·claude·codex 는 한 번도 실행하지 않는다: HOME = 하네스 임시 홈(그 아래 ~/.local/bin 에 가짜 셋) · PATH 는
  가짜 폴더 + 이 트리 target/debug + 시스템 폴더만(실 사용자 ~/.local/bin 제외) · 시작·끝에 실 agy 실행 파일을 돌리는
  프로세스가 0 인지 ps 로 잰다. 가짜 agy 는 실행될 때마다 $HOME/AGY_RAN 에 한 줄을 남긴다 = 「agy 프로세스 생성」 계수.

순서: ⓪ 문 열림 → E1 launch-agent 로 reviewer-gemini 좌석을 실제로 세움(②: 종전대로 뜬다 · 기존 사용자의 topology 재현)
      → 문 닫음 → 그 좌석의 가짜 agy 프로세스만 죽여 「빈 좌석」을 만든다 → 아래 11 입구를 차례로 두드리며 계수(①)
      → ③ 사람처럼 셸 탭에서 `agy` 를 치면 뜬다 → 문 다시 열고 E5 cys restore 가 종전대로 띄우는지(②).
실행: python3 docs/agy-door-evidence/acceptance.py   (저장소 뿌리에서 · cargo build --bin cys --bin cysd 선행)
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN = os.path.join(REPO, "cysjavis-pack", "bin")
TD = os.environ.get("AGY_ACCEPT_BIN_DIR") or os.path.join(REPO, "target", "debug")   # 뮤턴트 실측 = 다른 빌드 폴더
REAL_AGY = os.path.join(os.path.expanduser("~"), ".local", "bin", "agy")
os.environ["TMPDIR"] = os.path.realpath(os.environ.get("TMPDIR", "/tmp")) + "/"
os.environ["PHOENIX_HARNESS_CYSD"] = os.path.join(TD, "cysd")
os.environ["PHOENIX_CYS"] = os.path.join(TD, "cys")
for k in [k for k in os.environ if k.startswith(("CYS_", "AITERM_"))]:
    os.environ.pop(k)
sys.path.insert(0, BIN)
import javis_phoenix_harness as h  # noqa: E402
h.CYS = h._resolve_cys()
h.CYSD = h._resolve_cysd()
h.guard_isolation()

HOME = h.HARN_HOME
SOCK = h.HARN_SOCK
FAKE = os.path.join(HOME, ".local", "bin")
os.makedirs(FAKE, exist_ok=True)
SAFE_PATH = os.pathsep.join([FAKE, TD, "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
# 데몬(과 그 pane 셸)이 물려받을 환경 — 하네스 _daemon_env 가 HOME 을 하네스 홈으로 바꾼다.
os.environ["PATH"] = SAFE_PATH
os.environ["SHELL"] = "/bin/zsh"
os.environ["CYS_NO_AUTORESTORE"] = "1"

FAKES = {
    "agy": "AGY_RAN",
    "claude": "CLAUDE_RAN",
    "codex": "CODEX_RAN",
}
for name, mark in FAKES.items():
    p = os.path.join(FAKE, name)
    with open(p, "w") as f:
        f.write("#!/bin/sh\necho \"$$ $(date +%%s) $*\" >> \"$HOME/%s\"\n" % mark
                + ("printf '? for shortcuts\\n> '\n" if name == "agy" else "printf '❯ '\n")
                + "exec sleep 900\n")
    os.chmod(p, 0o755)

ENV = {k: v for k, v in os.environ.items()}
ENV.update({"HOME": HOME, "AITERM_SOCKET": SOCK, "CYS_SOCKET": SOCK, "CYS_STATE_DIR": h.HARN_STATE,
            "CYS_PACK_DIR": os.path.join(HOME, ".cys", "pack"), "CYS_NO_AUTOSTART": "1", "PATH": SAFE_PATH})
DOOR = os.path.join(HOME, ".cys", "agy-seat-door.json")
results = []


def ran(name="agy"):
    try:
        with open(os.path.join(HOME, FAKES[name])) as f:
            return len([l for l in f if l.strip()])
    except FileNotFoundError:
        return 0


def real_agy_procs():
    r = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True)
    return [l.strip() for l in r.stdout.splitlines() if REAL_AGY in l]


def run(argv, timeout=150):
    try:
        r = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL, cwd=HOME)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        return 124, "TIMEOUT %s" % e


def cys(*a, timeout=150):
    return run([os.path.join(TD, "cys"), "--socket", SOCK, *a], timeout=timeout)


def door(open_):
    if open_:
        os.makedirs(os.path.dirname(DOOR), exist_ok=True)
        with open(DOOR, "w") as f:
            json.dump({"open": True, "ack": "agy-consumer-plan-warning-v1", "by": "acceptance-fixture"}, f)
    elif os.path.exists(DOOR):
        os.remove(DOOR)


def surfaces():
    rc, out = cys("list", "--json", timeout=20)
    try:
        d = json.loads(out[out.index("{"):] if "{" in out else out)
        return d.get("surfaces") or d.get("result", {}).get("surfaces") or []
    except Exception:
        rc2, out2 = cys("status", "--json", timeout=20)
        try:
            return json.loads(out2).get("surfaces", [])
        except Exception:
            return []


def record(eid, what, before, out, rc, expect_delta=0):
    after = ran()
    ok = (after - before) == expect_delta
    results.append({"id": eid, "entry": what, "rc": rc, "agy_runs_before": before, "agy_runs_after": after,
                    "expect_delta": expect_delta, "pass": ok, "tail": out.strip().splitlines()[-3:]})
    print("%s %-4s %-58s rc=%-4s agy %d→%d (기대 +%d)" % ("PASS" if ok else "FAIL", eid, what, rc, before, after, expect_delta))


def kill_fake_agy():
    with open(os.path.join(HOME, "AGY_RAN")) as f:
        pids = [int(l.split()[0]) for l in f if l.strip()]
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def main():
    assert not real_agy_procs(), "시작 전 실 agy 프로세스가 이미 있다 — 대조가 흐려지므로 중단"
    pid = h.start_daemon(wait=120)
    assert pid, "하네스 데몬 기동 실패"
    for _ in range(60):
        if os.path.isfile(os.path.join(HOME, ".cys", "pack", "agents.json")):
            break
        time.sleep(0.5)
    agents = json.load(open(os.path.join(HOME, ".cys", "pack", "agents.json")))
    assert agents["gemini"]["cmd"].startswith("~/.local/bin/agy"), agents["gemini"]["cmd"]
    print("하네스 홈 =", HOME, "· 데몬 pid", pid, "· gemini cmd =", agents["gemini"]["cmd"])

    # ⓪ 문 열림 — 기존 사용자 재현: reviewer-gemini 좌석을 세운다(② E1)
    door(True)
    b = ran(); rc, out = cys("launch-agent", "--role", "reviewer-gemini", "--agent", "gemini", timeout=180)
    record("②E1", "문 열림 · cys launch-agent --agent gemini (종전대로 뜸)", b, out, rc, expect_delta=1)
    time.sleep(2)
    door(False)
    kill_fake_agy()   # pane(셸)은 남기고 가짜 agy 만 → reviewer-gemini 를 쥔 빈 좌석
    time.sleep(6)     # 데몬 워치독이 agent_alive=false 를 보도록

    # ① 문 닫힘(기본) — 11 입구
    b = ran(); rc, out = cys("launch-agent", "--role", "reviewer-gemini", "--agent", "gemini")
    record("E1", "cys launch-agent --role reviewer-gemini --agent gemini", b, out, rc)
    b = ran(); rc, out = cys("node-recover", "--role", "reviewer-gemini")
    record("E2", "cys node-recover --role reviewer-gemini(빈 좌석 · boot_agent_on_surface)", b, out, rc)
    b = ran(); rc, out = cys("restore")
    record("E3", "cys restore(빈 좌석 = 좌석 내 재연결 갈래)", b, out, rc)
    b = ran(); rc, out = run([sys.executable, os.path.join(BIN, "javis_phoenix.py"), "--socket", SOCK, "restore"], timeout=300)
    record("E4", "javis_phoenix.py restore(앱 재시작·업데이트 복원기)", b, out, rc)
    # 좌석을 통째로 닫아 topology 에만 남긴다 → fresh 갈래
    for s in surfaces():
        if s.get("role") == "reviewer-gemini":
            cys("close-surface", s.get("surface_ref") or ("surface:%s" % s.get("surface_id")), "--reap")
    time.sleep(2)
    b = ran(); rc, out = cys("restore")
    record("E5", "cys restore(좌석 없음 · topology 만 = fresh 갈래)", b, out, rc)
    b = ran(); rc, out = run([sys.executable, os.path.join(BIN, "javis_orchestra.py"), "boot-reviewers", "--spawn"], timeout=400)
    record("E6", "javis_orchestra.py boot-reviewers --spawn(지휘자·토론 스킬 길)", b, out, rc)
    b = ran(); rc, out = run([sys.executable, os.path.join(BIN, "javis_boot_node.py"), "--role", "reviewer-gemini", "--agent", "gemini", "--json"], timeout=300)
    record("E7", "javis_boot_node.py --role reviewer-gemini --agent gemini", b, out, rc)
    b = ran(); rc, out = cys("boot", "--json", timeout=300)
    record("E8", "cys boot(기본 함대 · agy 행 없음)", b, out, rc)
    b = ran(); rc, out = cys("new-surface", "--cmd", "~/.local/bin/agy --dangerously-skip-permissions", "--agent", "gemini", "--role", "reviewer-gemini")
    time.sleep(4)
    record("E10", "cys new-surface --cmd agy --agent gemini(launch-agent 우회 길)", b, out, rc)
    b = ran(); rc, out = cys("new-surface", "--cmd", "agy")
    time.sleep(4)
    record("E11", "cys new-surface --cmd agy(어댑터 선언 없이)", b, out, rc)
    # E9 = 앱 팔레트 「재기동 → reviewer-gemini」·「부서 간 전출」 이 하는 일 — 빈 셸에 그 명령을 쳐 넣는다
    rc, out = cys("new-surface", "--cwd", HOME)
    ref = next((w for w in out.split() if w.startswith("surface:")), None)
    assert ref, "빈 셸 탭 생성 실패: rc=%s %s" % (rc, out[-300:])
    time.sleep(3)
    b = ran()
    line = "%s --socket %s launch-agent --role reviewer-gemini --agent gemini" % (os.path.join(TD, "cys"), SOCK)
    cys("send", "--surface", ref, line); cys("send-key", "--surface", ref, "Return")
    time.sleep(25)
    rc, out = cys("read-screen", "--surface", ref)
    record("E9", "앱 팔레트 재기동 명령을 셸 탭에 입력(UI 길)", b, out, rc)

    # ③ 사람이 셸 탭에서 직접 agy — 막지 않는다
    b = ran()
    cys("send", "--surface", ref, "agy"); cys("send-key", "--surface", ref, "Return")
    time.sleep(5)
    rc, out = cys("read-screen", "--surface", ref)
    record("③", "사람이 셸 탭에서 직접 `agy` 입력(허용)", b, out, rc, expect_delta=1)

    # ② 문 다시 열면 복원이 종전대로 띄운다
    door(True)
    b = ran(); rc, out = cys("restore")
    record("②E5", "문 열림 · cys restore(종전대로 다시 뜸)", b, out, rc, expect_delta=1)

    real = real_agy_procs()
    results.append({"id": "real-agy", "entry": "실 agy 실행 파일 프로세스", "pass": not real, "procs": real})
    print("%s 실 agy(%s) 프로세스 %d개" % ("PASS" if not real else "FAIL", REAL_AGY, len(real)))
    return results


if __name__ == "__main__":
    out_path = os.environ.get("AGY_ACCEPT_OUT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "acceptance-result.json")
    try:
        res = main()
    finally:
        try:
            h.teardown()
        except Exception as e:
            print("teardown:", e)
    ok = all(r["pass"] for r in res)
    with open(out_path, "w") as f:
        json.dump({"ok": ok, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "results": res}, f, ensure_ascii=False, indent=1)
    print("종합:", "PASS" if ok else "FAIL", "·", out_path)
    sys.exit(0 if ok else 1)
