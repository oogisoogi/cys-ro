#!/usr/bin/env python3
"""agy 좌석 문 — 합격 ①②③ 실측(TICKET=cysr-agy-policy-exposure). 격리 하네스 데몬 + **가짜** agy/claude/codex.

★실제 agy·claude·codex 는 한 번도 실행하지 않는다: HOME = 하네스 임시 홈(그 아래 ~/.local/bin 에 가짜 셋) · PATH 는
  가짜 폴더 + 이 트리 target/debug + 시스템 폴더만(실 사용자 ~/.local/bin 제외) · 시작·끝에 실 agy 실행 파일을 돌리는
  프로세스가 0 인지 ps 로 잰다. 가짜 agy 는 실행될 때마다 $HOME/AGY_RAN 에 한 줄을 남긴다 = 「agy 프로세스 생성」 계수.

판정(2R 강화): 입구마다 agy 실행 횟수 차이 + 기대 rc + 「문에 도달했다」는 사유 낱말을 함께 단언한다(record 주석).
순서: ⓪ 문 열림 → E1 launch-agent 로 reviewer-gemini 좌석을 실제로 세움(②: 종전대로 뜬다 · 기존 사용자의 topology 재현)
      → 문 닫음 → 그 좌석의 가짜 agy 프로세스만 죽여 「빈 좌석」을 만든다 → 아래 11 입구를 차례로 두드리며 계수(①)
      → ③ 사람처럼 셸 탭에서 `agy` 를 치면 뜬다 → 문 다시 열고 E5 cys restore 가 종전대로 띄우는지(②).
실행: python3 docs/agy-door-evidence/acceptance.py   (저장소 뿌리에서 · cargo build --bin cys --bin cysd 선행)

r5(TICKET=cysr-agy-door-r5 · codex 4R 발견 6): 결과 파일의 입구는 **전부 이 파일이 실행한다**(E12~E19 포함 · 앞 좌석이 커밋하지
않았던 E12~E16 코드를 이번에 커밋) · 묘비 명령마다 (rc, 출력) 저장·단언 · 결과에 소스 커밋·바이너리 sha256 결속 · E13 은 데몬
`schedule.error` 이벤트의 사유(agy_consumer_policy)까지 단언 · 동시 실행 원시 기록 = `run_concurrent.sh`.
"""
import hashlib
import getpass
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time


REDACT_KEYS = {"tail", "fails", "procs", "dirty_paths"}   # 출력 증거만 지운다 — 판정 낱말(expect_in·entry·id·checks)·키·불리언은 그대로(codex 2R)


def redact_text(text):
    """실행한 사람의 홈 경로·계정 이름·기기 이름을 지운다(scripts/secret-scan.sh 규칙 1·6 · 발행 차단 게이트 H-SECRET-1).
    셸 프롬프트 「user@host 경로 %」 는 길이와 무관하게 통째로 · 맨 낱말 계정·기기 이름은 4자 이상일 때 낱말 경계로만."""
    home = os.path.expanduser("~")
    text = text.replace(home, "~")
    text = re.sub(r"/Users/[A-Za-z0-9._-]+", "/Users/<user>", text)
    text = re.sub(r"[A-Za-z0-9._-]+@[A-Za-z0-9._-]+(?= \S* ?[%$#] )", "<user>@<host>", text)
    for word, tag in ((socket.gethostname().split(".")[0], "<host>"), (getpass.getuser(), "<user>")):
        if word and len(word) >= 4:
            text = re.sub(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(word), tag, text, flags=re.IGNORECASE)
    return text


def redact(obj, key=None):
    """결과 객체(JSON 구조)를 걸어 내려가며 REDACT_KEYS 아래 문자열만 지운다."""
    if isinstance(obj, dict):
        return {k: redact(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v, key) for v in obj]
    if isinstance(obj, str) and key in REDACT_KEYS:
        return redact_text(obj)
    return obj


if __name__ == "__main__" and sys.argv[1:2] == ["--redact-text"]:   # 원시 로그(글)를 제자리에서 지운다(하네스 기동 없음)
    for _p in sys.argv[2:]:
        with open(_p, encoding="utf-8", errors="replace") as _f:
            _t = _f.read()
        with open(_p, "w", encoding="utf-8") as _f:
            _f.write(redact_text(_t))
    sys.exit(0)

if __name__ == "__main__" and sys.argv[1:2] == ["--redact"]:   # 이미 쓴 결과 파일을 제자리에서 지운다(하네스 기동 없음)
    for _p in sys.argv[2:]:
        with open(_p, encoding="utf-8") as _f:
            _d = json.load(_f)
        with open(_p, "w", encoding="utf-8") as _f:
            json.dump(redact(_d), _f, ensure_ascii=False, indent=1)
    sys.exit(0)

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
LOGDIR = os.environ.get("AGY_ACCEPT_LOGDIR")   # 있으면 입구별 전체 출력을 남긴다(진단용 · 커밋 안 함)
if LOGDIR:
    os.makedirs(LOGDIR, exist_ok=True)
POLICY = "agy_consumer_policy"
SKIP_LINE = "건너뜀(agy_consumer_policy)"
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


def record(eid, what, before, out, rc, expect_delta=0, expect_rc=None, expect_in=(), expect_not_in=(), checks=()):
    """판정 = ⑴ agy 실행 횟수 차이 ⑵ 입구별 기대 rc ⑶ 그 입구가 문에 「도달」했다는 사유 낱말(expect_in) ⑷ 있으면 안 될
    낱말(expect_not_in) ⑸ 추가 단언(checks = (이름, 참/거짓)). codex 1R: ⑴만 보면 문과 무관한 이유(인자 오류·기동 실패)로
    agy 가 안 떠도 PASS 가 된다 — 그래서 각 입구가 **어디서 왜** 멈췄는지를 함께 단언한다."""
    after = ran()
    fails = []
    if (after - before) != expect_delta:
        fails.append("agy %d→%d (기대 +%d)" % (before, after, expect_delta))
    if expect_rc is not None and rc not in (expect_rc if isinstance(expect_rc, tuple) else (expect_rc,)):
        fails.append("rc=%s (기대 %s)" % (rc, expect_rc))
    for w in expect_in:
        if w not in out:
            fails.append("사유 없음: %r" % w)
    for w in expect_not_in:
        if w in out:
            fails.append("있으면 안 됨: %r" % w)
    for name, ok_ in checks:
        if not ok_:
            fails.append("단언 실패: %s" % name)
    ok = not fails
    results.append({"id": eid, "entry": what, "rc": rc, "expect_rc": expect_rc, "agy_runs_before": before,
                    "agy_runs_after": after, "expect_delta": expect_delta, "expect_in": list(expect_in),
                    "expect_not_in": list(expect_not_in), "checks": [n for n, _ in checks], "pass": ok,
                    "fails": fails, "tail": out.strip().splitlines()[-12:]})
    if LOGDIR:
        with open(os.path.join(LOGDIR, "%s.log" % eid), "w") as f:
            f.write("rc=%s\n%s" % (rc, out))
    print("%s %-4s %-58s rc=%-4s agy %d→%d (기대 +%d)%s" % ("PASS" if ok else "FAIL", eid, what, rc, before, after,
                                                         expect_delta, "" if ok else " · " + " · ".join(fails)))


def last_json(out):
    """출력 속 마지막 여러 줄 JSON 객체(phoenix 결과 = 줄머리 「{」 … 줄머리 「}」)를 읽는다 — 뒤에 로그 줄이 붙어도 된다.
    없으면 None."""
    lines = out.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if lines[i] != "{":
            continue
        for k in range(i + 1, len(lines)):
            if lines[k] == "}":
                try:
                    return json.loads("\n".join(lines[i:k + 1]))
                except ValueError:
                    break
    return None


def launch_blocks(out):
    """launch-agent 출력 → {role: 그 역할 블록 텍스트}. 블록 = 「[launch-agent] surface:N created (role=R)」 줄부터 다음 created 줄
    앞까지(codex 2R: ready·관문 보류·실패를 출력 아무 데서나 찾지 말고 역할에 결속한다)."""
    blocks, cur = {}, None
    for l in out.splitlines():
        m = re.search(r"\[launch-agent\] surface:\S+ created \(role=([^)]+)\)", l)
        if m:
            cur = m.group(1)
            blocks[cur] = ""
        if cur is not None:
            blocks[cur] += l + "\n"
    return blocks


def json_line(out, key):
    """한 줄 JSON 중 key 를 가진 마지막 것(cys boot --json 의 roles 줄) — 없으면 None."""
    for l in reversed(out.splitlines()):
        l = l.strip()
        if l.startswith("{") and key in l:
            try:
                return json.loads(l)
            except ValueError:
                continue
    return None


def raw_rpc(method, params, timeout=20):
    """데몬 소켓에 직접 한 줄 JSON 요청(앱 화면이 보내는 것과 같은 꼴 — E19 사람 자판 재현용)."""
    rid = "accept-%d" % time.monotonic_ns()
    sk = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sk.settimeout(timeout)
    try:
        sk.connect(SOCK)
        sk.sendall((json.dumps({"id": rid, "method": method, "params": params}) + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = sk.recv(65536)
            if not chunk:
                break
            data += chunk
    finally:
        sk.close()
    try:
        return json.loads(data.split(b"\n", 1)[0])
    except ValueError:
        return {"raw": data[:400].decode("utf-8", "replace")}


def ledger_lines():
    """하네스 데몬의 배달 원장 줄 전부(delivery-*.jsonl · 격리 상태 폴더)."""
    out = []
    for n in sorted(os.listdir(h.HARN_STATE)) if os.path.isdir(h.HARN_STATE) else []:
        if n.startswith("delivery-") and n.endswith(".jsonl"):
            with open(os.path.join(h.HARN_STATE, n), encoding="utf-8", errors="replace") as f:
                out += [l for l in f if l.strip()]
    return out


def sha256_of(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def provenance():
    """결과를 소스 커밋·바이너리에 결속한다(codex 4R 발견 6) — 결과 파일이 어느 코드로 만들어졌는지."""
    def git(*a):
        r = subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True)
        return r.stdout
    dirty = [l[3:] for l in git("status", "--porcelain").splitlines() if l.strip()]   # 앞 두 칸 = 상태 글자(strip 금지)
    return {"source_commit": git("rev-parse", "HEAD").strip(), "dirty_paths": dirty,
            "harness_sha256": sha256_of(os.path.abspath(__file__)),
            "cys_sha256": sha256_of(os.path.join(TD, "cys")), "cysd_sha256": sha256_of(os.path.join(TD, "cysd"))}


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
    record("②E1", "문 열림 · cys launch-agent --agent gemini (종전대로 뜸)", b, out, rc, expect_delta=1,
           expect_rc=0, expect_in=("[launch-agent] ready",), expect_not_in=(POLICY,))
    time.sleep(2)
    door(False)
    # E16(독립 검증 M3): 문을 닫은 뒤 떠 있는 agy 좌석으로 가는 자동 지시는 데몬이 거부(사람 자판 입력은 별개 · 좌석은 끄지 않음)
    gref = next((x.get("surface_ref") or "surface:%s" % x.get("surface_id") for x in surfaces() if x.get("role") == "reviewer-gemini"), None)
    b = ran(); rc, out = cys("send", "--surface", gref or "surface:0", "hello from automation", timeout=30)
    record("E16", "문 닫은 뒤 떠 있는 agy 좌석으로 cys send(자동 지시)", b, out, rc, expect_in=(POLICY,),
           checks=(("agy 좌석 찾음", bool(gref)), ("거부(rc≠0)", rc != 0)))
    # E19(codex 4R major 4): 같은 좌석에 사람 자판(앱 화면의 실키 = human ∧ 기계 출처 아님)이 운영자 토큰 없이 오면 통과 +
    #   원장 「토큰 미확인 통과」 — 구 GUI·토큰 판독 실패에서 사람 입력을 거부하지 않는다. 대조 = 같은 요청에 machine_origin → 거부.
    gsid = next((x.get("surface_id") for x in surfaces() if x.get("role") == "reviewer-gemini"), None)
    led0 = len(ledger_lines())
    b = ran(); r_h = raw_rpc("surface.send_text", {"surface_id": gsid, "text": "typed by a person", "human": True})
    r_m = raw_rpc("surface.send_text", {"surface_id": gsid, "text": "gui auto text", "human": True, "machine_origin": True})
    new_led = ledger_lines()[led0:]
    # 사람이 친 글은 입력줄 초안으로 남는다 — 사람처럼 줄을 비운다(Ctrl-U · 남기면 다음 입구 node-recover 가 「사람 초안」 보호로 거부(rc 79))
    r_clr = raw_rpc("surface.send_text", {"surface_id": gsid, "text": "\u0015", "human": True})
    time.sleep(1)
    record("E19", "문 닫힘 · agy 좌석에 사람 자판(토큰 없음) 통과 + 원장 표시 · 대조 machine_origin 거부", b,
           json.dumps({"human": r_h, "machine_origin": r_m}, ensure_ascii=False), 0,
           checks=(("agy 좌석 찾음", gsid is not None),
                   ("사람 자판 = ok", r_h.get("ok") is True),
                   ("사람 줄 비우기(Ctrl-U) = ok", r_clr.get("ok") is True),
                   ("원장에 「토큰 미확인 통과」", any('"agy_door"' in l and "토큰 미확인 통과" in l for l in new_led)),
                   ("대조: machine_origin = 거부(agy_consumer_policy)", r_m.get("ok") is not True
                    and POLICY in json.dumps(r_m, ensure_ascii=False))))
    kill_fake_agy()   # pane(셸)은 남기고 가짜 agy 만 → reviewer-gemini 를 쥔 빈 좌석
    time.sleep(6)     # 데몬 워치독이 agent_alive=false 를 보도록

    # ① 문 닫힘(기본) — 11 입구
    b = ran(); rc, out = cys("launch-agent", "--role", "reviewer-gemini", "--agent", "gemini")
    record("E1", "cys launch-agent --role reviewer-gemini --agent gemini", b, out, rc,
           expect_rc=76, expect_in=("[launch-agent] " + POLICY,))
    b = ran(); rc, out = cys("node-recover", "--role", "reviewer-gemini")
    # node-recover 는 하위 오류를 「error: <사유>」 + rc 1 로 낸다(76 을 따로 전파하지 않음) — 사유 낱말로 도달을 단언
    record("E2", "cys node-recover --role reviewer-gemini(빈 좌석 · boot_agent_on_surface)", b, out, rc,
           expect_rc=1, expect_in=("error: " + POLICY,))
    b = ran(); rc, out = cys("restore")
    record("E3", "cys restore(빈 좌석 = 좌석 내 재연결 갈래)", b, out, rc,
           expect_rc=0, expect_in=("reviewer-gemini: " + SKIP_LINE, "실패 0"))
    b = ran(); rc, out = run([sys.executable, os.path.join(BIN, "javis_phoenix.py"), "--socket", SOCK, "restore"], timeout=300)
    ph = last_json(out)
    record("E4", "javis_phoenix.py restore(앱 재시작·업데이트 복원기)", b, out, rc, expect_rc=0,
           expect_in=("agy 좌석 문 닫힘",),
           checks=(("결과 JSON 판독", ph is not None),
                   ("agy_policy_skipped_roles ∋ reviewer-gemini", "reviewer-gemini" in (ph or {}).get("agy_policy_skipped_roles", [])),
                   ("manual_seats ∌ reviewer-gemini(정책 건너뜀을 빈 좌석으로 재보고하지 않음)",
                    "reviewer-gemini" not in (ph or {}).get("manual_seats", ["reviewer-gemini"])),
                   ("incomplete_roles ∌ reviewer-gemini(부활 실패 아님)",
                    "reviewer-gemini" not in (ph or {}).get("incomplete_roles", ["reviewer-gemini"]))))
    # 좌석을 통째로 닫아 topology 에만 남긴다 → fresh 갈래
    for s in surfaces():
        if s.get("role") == "reviewer-gemini":
            cys("close-surface", s.get("surface_ref") or ("surface:%s" % s.get("surface_id")), "--reap")
    time.sleep(2)
    b = ran(); rc, out = cys("restore")
    record("E5", "cys restore(좌석 없음 · topology 만 = fresh 갈래)", b, out, rc,
           expect_rc=0, expect_in=("reviewer-gemini: " + SKIP_LINE, "실패 0"))
    b = ran(); bc = ran("claude")
    rc, out = run([sys.executable, os.path.join(BIN, "javis_orchestra.py"), "boot-reviewers", "--spawn"], timeout=400)
    # 문에 도달 = 오라클 사유로 gemini 슬롯이 Claude 대체(reviewer-claude-1)로 갔고 그 대체가 실제로 기동됐다(가짜 claude +1 이상).
    # rc 1 = 「리뷰어 2기 각성 미달」(가짜 에이전트는 각성 ack 를 못 낸다 — 문과 무관 · 아래 E6 주석 참조).
    record("E6", "javis_orchestra.py boot-reviewers --spawn(지휘자·토론 스킬 길)", b, out, rc, expect_rc=1,
           expect_in=("gemini 미감지(cys agent-detect: " + POLICY, "reviewer-claude-1(Claude) 대체 기동"),
           checks=(("Claude 대체가 실제로 기동됨(가짜 claude 실행 +1 이상)", ran("claude") > bc),))
    b = ran(); rc, out = run([sys.executable, os.path.join(BIN, "javis_boot_node.py"), "--role", "reviewer-gemini", "--agent", "gemini", "--json"], timeout=300)
    # boot_node 는 launch-agent 의 76 을 「launch_failed」로 묶어 rc 1 을 낸다 — 하위 rc=76 기록으로 문 도달을 단언
    record("E7", "javis_boot_node.py --role reviewer-gemini --agent gemini", b, out, rc, expect_rc=1,
           expect_in=("launch-agent rc=76", '"reason": "launch_failed"'))
    b = ran(); rc, out = cys("boot", "--json", timeout=300)
    # rc 78 = EXIT_GATE_PENDING — 가짜 claude 는 첫기동 관문을 못 넘는다(문과 무관). 단언 = 부트 대상 행에 agy 가 없다.
    # (출력의 「[alert] surface.exited … role=reviewer-gemini」 는 앞 단계에서 죽인 좌석의 이벤트 다이제스트라 판정에 안 쓴다)
    bj = json_line(out, '"roles"')
    rows = (bj or {}).get("roles") or []
    record("E8", "cys boot(기본 함대 · agy 행 없음)", b, out, rc, expect_rc=78, expect_not_in=(POLICY,),
           checks=(("boot --json roles 줄 판독", bool(rows)),
                   ("부트 대상 = cso·worker 뿐(claude)", sorted((r.get("role"), r.get("agent")) for r in rows)
                    == [("cso", "claude"), ("worker", "claude")])))
    b = ran(); rc, out = cys("new-surface", "--cmd", "~/.local/bin/agy --dangerously-skip-permissions", "--agent", "gemini", "--role", "reviewer-gemini")
    time.sleep(4)
    record("E10", "cys new-surface --cmd agy --agent gemini(launch-agent 우회 길)", b, out, rc,
           expect_rc=76, expect_in=("[new-surface] " + POLICY,))
    b = ran(); rc, out = cys("new-surface", "--cmd", "agy")
    time.sleep(4)
    record("E11", "cys new-surface --cmd agy(어댑터 선언 없이)", b, out, rc,
           expect_rc=76, expect_in=("[new-surface] " + POLICY,))
    # E12~E15(독립 검증 B1·B2): 셸 문을 실행하던 무판정 입구
    agy = os.path.join(FAKE, "agy")
    b = ran(); rc, out = cys("schedule", "add", "--id", "agyjob", "--in", "2s", "--command", agy + " -p review")
    record("E12", "cys schedule add --command agy(등록 때 판정)", b, out, rc, expect_rc=76, expect_in=("[schedule] " + POLICY,))
    b = ran(); rc, out = cys("channel", "start", "agych", "--cmd", agy + " -p bridge")
    record("E14", "cys channel start --cmd agy(채널 브리지)", b, out, rc, expect_rc=76, expect_in=("[channel] " + POLICY,))
    b = ran(); rc, out = run([sys.executable, os.path.join(BIN, "javis_orchestra.py"), "round-log", "--task", "agyt", "--round", "1",
                              "--evaluator", "machine", "--from-cmd", agy + " -p review"], timeout=60)
    record("E15", "javis_orchestra.py round-log --from-cmd agy", b, out, rc, expect_rc=76, expect_in=("[round-log] 거부", POLICY))
    # E17(r5 · 받아들인 거짓 양성): 기계 입구는 낱말만 있어도 거부 — 거부 글이 까닭과 푸는 법(낱말 바꾸기)을 말한다
    bc = ran("claude")
    b = ran(); rc, out = cys("schedule", "add", "--id", "agyword", "--in", "2s", "--command", "claude -p 'review agy door'")
    record("E17", "일정 --command 프롬프트 속 「agy」 낱말(받아들인 거짓 양성 · 안내 글)", b, out, rc, expect_rc=76,
           expect_in=("[schedule] " + POLICY, "낱말", "다른 말"), checks=(("가짜 claude 실행 0", ran("claude") == bc),))
    # E18(codex 4R blocking 2·3): 치환 괄호 속 따옴표 · 래퍼의 인용된 agy 경로 — 기계 입구 낱말 검사가 구조와 무관하게 거부
    b = ran(); rc, out = cys("schedule", "add", "--id", "agysub", "--in", "2s", "--command", "true $(printf ')'); \"%s\"" % agy)
    record("E18a", "일정 --command 'true $(printf \')\'); \"…/agy\"'(4R blocking 2)", b, out, rc, expect_rc=76,
           expect_in=("[schedule] " + POLICY,))
    b = ran(); rc, out = cys("channel", "start", "agywatch", "--cmd", "watch \"%s\"" % agy)
    record("E18b", "채널 --cmd 'watch \"…/agy\"'(4R blocking 3 · 인용된 래퍼 대상)", b, out, rc, expect_rc=76,
           expect_in=("[channel] " + POLICY,))
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
    record("E9", "앱 팔레트 재기동 명령을 셸 탭에 입력(UI 길)", b, out, rc, expect_rc=0,
           expect_in=("[launch-agent] " + POLICY,))

    # ③ 사람이 셸 탭에서 직접 agy — 막지 않는다
    b = ran()
    cys("send", "--surface", ref, "agy"); cys("send-key", "--surface", ref, "Return")
    time.sleep(5)
    rc, out = cys("read-screen", "--surface", ref)
    record("③", "사람이 셸 탭에서 직접 `agy` 입력(허용)", b, out, rc, expect_delta=1, expect_rc=0,
           expect_in=("? for shortcuts",))

    # E13(독립 검증 B1 · 발화 때 판정): 대조 = 문 열림에서 등록·발화 → agy +1 · 본 = 문 열림에서 등록 뒤 닫고 발화 → +0
    door(True)
    b = ran(); rc, out = cys("schedule", "add", "--id", "agyctl", "--in", "3s", "--command", agy + " -p ctl")
    for _ in range(40):
        if ran() > b:
            break
        time.sleep(1)
    record("E13c", "대조: 문 열림 · 일정 --command agy 발화(일정이 실제로 돈다)", b, out, rc, expect_delta=1, expect_rc=0)
    ev_path = os.path.join(HOME, "schedule-events.log")
    with open(ev_path, "w") as evf:
        evp = subprocess.Popen([os.path.join(TD, "cys"), "--socket", SOCK, "events", "--name", "schedule.error"], env=ENV,
                               stdout=evf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    time.sleep(2)
    b = ran(); rc, out = cys("schedule", "add", "--id", "agyfire", "--in", "8s", "--command", agy + " -p fire")
    door(False)
    time.sleep(30)
    evp.terminate()   # 이 하네스가 띄운 구독 프로세스 하나(pid 직접)
    try:
        evp.wait(timeout=10)
    except subprocess.TimeoutExpired:
        evp.kill()
    with open(ev_path, encoding="utf-8", errors="replace") as f:
        ev = f.read()
    ev_hit = [l for l in ev.splitlines() if "agyfire" in l]
    record("E13", "문 열림에서 등록한 일정 --command agy · 닫은 뒤 발화(발화 때 판정)", b, out + "\n[events]\n" + ev, rc, expect_rc=0,
           checks=(("데몬 schedule.error 에 agyfire", bool(ev_hit)),
                   ("그 사유 = agy_consumer_policy(codex 4R 발견 6)", any(POLICY in l for l in ev_hit))))
    # ② 문 다시 열면 복원이 종전대로 띄운다
    # ★결정성(master#a078504c · 스냅샷 재실행 적색): `cys restore` 에는 역할 필터가 없어 앞 입구가 남긴 좌석(E6 의 reviewer-codex·
    #   reviewer-claude-*, E8 의 cso·worker — 가짜 에이전트는 시간이 지나면 끝난다)까지 되살리려 들고, 그 성패가 부하에 따라
    #   달라졌다(실측 rc 1·0·0·1). 그래서 ②E5 직전에 reviewer-gemini 밖의 역할을 전부 묘비로 닫아 restore 대상을 gemini 하나로 만든다.
    _roles = {s.get("role") for s in surfaces()} | {"reviewer-codex", "reviewer-claude-1", "reviewer-claude-2", "cso", "worker"}
    for _tp in {os.path.join(os.path.dirname(SOCK), "topology.json"), os.path.join(h.HARN_STATE, "topology.json")}:
        try:
            with open(_tp, encoding="utf-8") as _f:
                _roles |= {e.get("role") for e in json.load(_f).get("entries", [])}
        except (OSError, ValueError):
            pass
    _tombed = sorted(r for r in _roles if r and r not in ("reviewer-gemini", "-", "master"))
    _tomb_rc, _tomb_out = {}, {}
    for _r in _tombed:
        _tomb_rc[_r], _tomb_out[_r] = cys("tombstone", _r, timeout=20)
    print("②E5 준비: 묘비로 닫은 역할 =", _tombed)
    # codex 4R 발견 6: 묘비 명령마다 (rc, 출력)을 저장하고 단언한다(전부 rc 0 · 출력에 오류 낱말 없음)
    results.append({"id": "②E5-tomb", "entry": "②E5 준비 묘비 명령별 (rc, 출력)",
                    "pass": bool(_tombed) and all(_tomb_rc[r] == 0 and "error" not in _tomb_out[r].lower() for r in _tombed),
                    "tombs": [{"role": r, "rc": _tomb_rc[r], "tail": _tomb_out[r].strip().splitlines()[-3:]} for r in _tombed]})
    print("%s ②E5-tomb 묘비 %d건 rc=%s" % ("PASS" if results[-1]["pass"] else "FAIL", len(_tombed), sorted(set(_tomb_rc.values()))))
    door(True)
    b = ran(); rc, out = cys("restore")
    # 판정은 역할 블록에 결속한다(codex 2R): restore 가 세운 좌석 = reviewer-gemini 하나 · 그 블록 = ready · 관문 보류·오류 없음 · rc 0.
    blk = launch_blocks(out)
    gem = blk.get("reviewer-gemini", "")
    record("②E5", "문 열림 · cys restore(종전대로 다시 뜸)", b, out, rc, expect_delta=1, expect_rc=0,
           expect_in=("실패 0",), expect_not_in=(SKIP_LINE, "· reviewer-gemini: 기동 실패"),
           checks=(("앞 입구 역할 묘비 처리 = 전부 rc 0(codex 3R: 반환 코드 단언)", bool(_tomb_rc) and all(v == 0 for v in _tomb_rc.values())),
                   ("restore 가 세운 좌석 = reviewer-gemini 뿐", sorted(blk) == ["reviewer-gemini"]),
                   ("reviewer-gemini 블록 = ready", "[launch-agent] ready" in gem),
                   ("reviewer-gemini 블록에 관문 보류·오류 없음", bool(gem) and "관문 보류" not in gem and "error" not in gem.lower())))

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
        json.dump(redact({"ok": ok, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "provenance": provenance(), "results": res}),
                  f, ensure_ascii=False, indent=1)
    print("종합:", "PASS" if ok else "FAIL", "·", out_path)
    sys.exit(0 if ok else 1)
