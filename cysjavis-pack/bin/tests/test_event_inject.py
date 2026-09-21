#!/usr/bin/env python3
"""test_event_inject.py — master·CEO 사건 적시 주입 ⓓ(injection-slim T3) 회귀 하네스 (standalone).

대상: hooks/directive-event-inject.sh(PreToolUse Bash) + hooks/core_inject.py event(트리거 사전 EVENT_TRIGGERS).
정본: DESIGN-v2.1 §4-5·§4-6-5·§7 T3 · master 판정 6255b46b(PreToolUse) · b286f358(D10 = javis_mission.py set 1회 거부).

무엇을 고정하나:
  T  트리거 사전 행렬: 표의 모든 행이 제 절로 걸린다(CEO 전용 행은 master 좌석에서 안 걸린다)
  N  오탐 음성 대조: grep 패턴 · 인용 heredoc 보고문 · 문서 인용(echo "…") · 커밋 메시지 · 주석 · 무관 명령 → 0건
  X  실행 경로 양성: || · $(…) · 큰따옴표 안 $(…) · 백틱 · sh -c · 셸이 받는 heredoc · 비인용 heredoc 본문의 $(…) · env/timeout 접두 · cys --socket · sudo/xargs 값 옵션 · 훅 경로(cys --surface … feed · 다중 공백)
  R  훅 가드: 역할(worker·cso·reviewer·미지정) · surface 없음 · 서브에이전트(agent_id) → 0바이트 · 원장 파일 0
  O  세션당 절별 1회: 두 번째 같은 트리거 = 무출력 · 다른 세션 = 다시 주입
  D  §14 거부(D10): 첫 mission set = deny + §14 원문 · 재실행 = 허용 + §0-C 원문 · 원장 판독 불가·쓰기 불가 = 거부 안 함(fail-open)
  F  총량 울타리: 누적이 24,000자에 닿으면 원문 대신 「주입 상한 도달」 + 줄 범위
  S  출력 상한: gate-status(§0-C + §7 = 11,000자+) → ≤9,000자 · 못 실은 §7 은 원장에 안 남아 다음에 실린다
  M  제목 삭제: 디렉티브에서 「## 2.」 제목을 지우면 「찾지 못했다」 고지 + preflight C82 적색
  P  파싱 실패: 닫히지 않은 따옴표 → 무출력 · 원장 parse_fail
  L  락: 죽은 pid 의 낡은 락 회수 · 살아 있는 락이면 주입은 하고 lock_fail 기록 · _unlock 은 내 락만 푼다
  Z  비일치 경로 외부 프로세스 0: PATH = 기록용 가짜 명령 폴더 · 비트리거 → 가짜 기록·stderr·stdout 0(대조군: 트리거면 같은 측정기에 호출이 잡힌다)
  C  CEO 좌석: cys-dept → [부서 수명주기] 원문 · 본문 § 절 줄 번호 = CEO 템플릿 기준
  Q  목차 표지: 트리거 사전의 모든 절 키가 목차에서 「⇐」 표시를 받는다(사전에서 파생)
  W  지연 실측(맥): 비일치·일치 경로 각 5회 중앙값 — 보고용(판정 아님)
실행:  python3 cysjavis-pack/bin/tests/test_event_inject.py [--mutants]
"""
import importlib.util
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

SELF = os.path.dirname(os.path.abspath(__file__))
REPO_PACK = os.path.normpath(os.path.join(SELF, "..", ".."))
_spec = importlib.util.spec_from_file_location("_tci", os.path.join(SELF, "test_core_inject.py"))
_tci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tci)
make_pack, env_for, load_pf = _tci.make_pack, _tci.env_for, _tci.load_pf

fails = []
NOTES = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))
    if not cond:
        fails.append(name)
    return cond


def ci_mod(pack):
    spec = importlib.util.spec_from_file_location("ci_%d" % id(pack), os.path.join(pack, "hooks", "core_inject.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def hook_in(cmd, sid="s1", extra=None):
    d = {"session_id": sid, "hook_event_name": "PreToolUse", "tool_name": "Bash",
         "tool_input": {"command": cmd}, "cwd": "/tmp", "transcript_path": "/tmp/x.jsonl"}
    if extra:
        d.update(extra)
    return json.dumps(d, ensure_ascii=False) + "\n"


def fire(pack, tmp, cmd, sid="s1", env=None, extra=None, raw=None):
    e = env or env_for(tmp, pack)
    e.setdefault("CYS_STATE_DIR", os.path.join(tmp, "state"))
    t0 = time.time()
    r = subprocess.run(["sh", os.path.join(pack, "hooks", "directive-event-inject.sh")],
                       input=raw if raw is not None else hook_in(cmd, sid, extra),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=e, timeout=30)
    out = None
    if r.stdout.strip():
        try:
            out = json.loads(r.stdout)["hookSpecificOutput"]
        except (ValueError, KeyError):
            out = {"_raw": r.stdout}
    return r.returncode, out, r.stderr, time.time() - t0


def ctx(out):
    return (out or {}).get("additionalContext") or ""


def ledger_rows(tmp, sid="s1"):
    p = os.path.join(tmp, "state", "directive-event", sid + ".jsonl")
    if not os.path.isfile(p):
        return []
    return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]


# ── 시나리오 ────────────────────────────────────────────────────────────────────
def s_T(pack, tmp):
    ci = ci_mod(pack)
    ok = True
    for tk, tn, ts, keys, act, seat, _b in ci.EVENT_TRIGGERS:
        if tk == "py":
            cmd = 'python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/%s"%s --x' % (tn, (" " + ts) if ts else " status")
        elif tk == "cys":
            cmd = "cys %s --role worker" % tn
        else:
            cmd = "%s create d1" % tn
        for kind in ("master", "ceo"):
            hits = {(k, a) for k, a, _b2, _l in ci.trigger_hits(cmd, kind)}
            want = seat == "all" or kind == "ceo"
            got = all((k, act) in hits for k in keys)
            ok &= check("T 트리거 %s %s [%s] → %s(%s)" % (tn, ts or "", kind, "·".join(keys), act),
                        got == want, "hits=%s" % sorted(hits))
    return ok


NEG = [
    ("grep 패턴", "grep -n 'cys launch-agent' MASTER_DIRECTIVE.md"),
    ("grep -E 큰따옴표 패턴", 'grep -E "javis_mission.py set|gate-status" -r .'),
    ("인용 heredoc 보고문", "~/.claude/channels/inbox-append.sh w@1 <<'EOF'\n【진행】 cys launch-agent 로 워커 기동 · python3 bin/javis_mission.py set x\nEOF"),
    ("문서 인용 echo", 'echo "다음 단계: cys feed push --wait 로 승인"'),
    ("커밋 메시지", 'git commit -m "fix: javis_orchestra.py next-action 문구"'),
    ("주석 줄", "# cys launch-agent --role worker\nls"),
    ("sed 로 문서 읽기", "sed -n '288,330p' directives/MASTER_DIRECTIVE.md # §2 launch-agent"),
    ("cat 인용 heredoc 파일 쓰기", "cat > note.md <<'EOF'\n$(cys launch-agent)\nEOF"),
    ("무관 명령", "ls -la && git status"),
]
POS = [
    ("|| 뒤", "echo x || cys launch-agent --role w", "§2"),
    ("$(…)", "X=$(cys launch-agent --role w)", "§2"),
    ("큰따옴표 안 $(…)", 'echo "$(cys feed push --wait --title t)"', "§4"),
    ("백틱", "echo `python3 bin/javis_orchestra.py next-action`", "§0-C"),
    ("sh -c", "sh -c 'cys feed push'", "§4"),
    ("셸이 받는 heredoc", "bash <<'EOF'\ncys launch-agent --role w\nEOF", "§2"),
    ("비인용 heredoc 본문 $(…)", "cat > f <<EOF\n$(python3 bin/javis_orchestra.py review-prompt --task t)\nEOF", "§7"),
    ("env·timeout 접두", 'CYS_X=1 env -u A timeout 5 python3 -u /p/bin/javis_resource_gate.py check', "§8"),
    ("cys --socket", "cys --socket a.sock launch-agent --role w", "§2"),
    ("파이프 뒤", "true | python3 bin/javis_orchestra.py task-prompt --task t", "§1-A"),
    ("서브셸 그룹", "(cd x && cys feed list)", "§4"),
    ("sudo 값 옵션(-u root)", "sudo -u root python3 bin/javis_mission.py set x", "§14"),
    ("xargs 값 옵션(-I {})", "echo a | xargs -I {} cys feed push", "§4"),
]
# 훅(셸 1차 거름) 경로 양성 — 파이썬 판정기가 잡는 것을 셸이 먼저 거르지 않는가(agy 1R F4)
POS_HOOK = [
    ("cys --surface 뒤 feed", "cys --surface S1 feed push --wait", "§4"),
    ("cys 와 feed 사이 공백 2개", "cys  feed list", "§4"),
]


def s_N(pack, tmp):
    ci = ci_mod(pack)
    ok = True
    for name, cmd in NEG:
        ok &= check("N 음성 %s" % name, ci.trigger_hits(cmd, "master") == [], str(ci.trigger_hits(cmd, "master")))
    # 훅 경로로도 1건(인용 heredoc 보고문 — 적대 검증이 1인칭으로 실증한 오탐 경로)
    rc, out, _e, _t = fire(pack, tmp, NEG[2][1])
    ok &= check("N 훅 경로: 인용 heredoc 보고문 → 무출력 · 원장 0", rc == 0 and out is None and not ledger_rows(tmp))
    return ok


def s_X(pack, tmp):
    ci = ci_mod(pack)
    ok = True
    for name, cmd, key in POS:
        keys = [k for k, _a, _b, _l in ci.trigger_hits(cmd, "master")]
        ok &= check("X 양성 %s → %s" % (name, key), key in keys, str(keys))
    for i, (name, cmd, key) in enumerate(POS_HOOK):
        rc, out, _e, _t = fire(pack, tmp, cmd, sid="xh%d" % i)
        ok &= check("X 훅 경로 양성 %s → %s 원문" % (name, key), rc == 0 and ("■ 원문 %s (줄" % key) in ctx(out))
    return ok


def s_R(pack, tmp):
    ok = True
    cmd = "cys launch-agent --role w"
    for role in ("worker", "worker-4", "cso", "reviewer-codex", None):
        rc, out, err, _t = fire(pack, tmp, cmd, env=env_for(tmp, pack, role=role))
        ok &= check("R 역할 가드 %s → 0바이트" % role, rc == 0 and out is None and not err)
    e = env_for(tmp, pack)
    e.pop("CYS_SURFACE_ID", None)
    rc, out, _e, _t = fire(pack, tmp, cmd, env=e)
    ok &= check("R surface 없음 → 0바이트", rc == 0 and out is None)
    rc, out, _e, _t = fire(pack, tmp, cmd, extra={"agent_id": "a0123", "agent_type": "general-purpose"})
    ok &= check("R 서브에이전트(agent_id) → 0바이트", rc == 0 and out is None)
    ok &= check("R 가드 경로에서 원장 0", not os.path.isdir(os.path.join(tmp, "state", "directive-event")))
    return ok


def s_O(pack, tmp):
    ok = True
    rc, out, _e, _t = fire(pack, tmp, "cys launch-agent --role w")
    c = ctx(out)
    ok &= check("O 첫 발화 = §1-A·§2 원문", rc == 0 and "■ 원문 §2 (줄" in c and "■ 원문 §1-A (줄" in c)
    ok &= check("O 출력 ≤9,000자", _tci.ulen(c) <= 9000, "%d" % _tci.ulen(c))
    rc, out, _e, _t = fire(pack, tmp, "cys launch-agent --role w2")
    ok &= check("O 같은 세션 두 번째 = 무출력", rc == 0 and out is None)
    rc, out, _e, _t = fire(pack, tmp, "cys launch-agent --role w3", sid="s2")
    ok &= check("O 다른 세션 = 다시 주입", "■ 원문 §2 (줄" in ctx(out))
    rows = ledger_rows(tmp)
    ok &= check("O 원장 = inject 2줄(§1-A·§2)", sorted((r["mode"], r["key"]) for r in rows)
                == [("inject", "§1-A"), ("inject", "§2")], str(rows))
    return ok


def s_D(pack, tmp):
    ok = True
    cmd = 'python3 "$CYS_PACK_DIR/bin/javis_mission.py" set "릴리스 1.1"'
    rc, out, _e, _t = fire(pack, tmp, cmd)
    reason = (out or {}).get("permissionDecisionReason") or ""
    ok &= check("D 첫 실행 = deny", rc == 0 and (out or {}).get("permissionDecision") == "deny")
    ok &= check("D 사유 = 사실 고지 + §14 원문", "다시 실행하십시오" in reason and "■ 원문 §14 (줄" in reason
                and "## 14." in reason)
    ok &= check("D 거부 사유 ≤9,000자", _tci.ulen(reason) <= 9000, "%d" % _tci.ulen(reason))
    ok &= check("D 거부 때는 §0-C 를 원장에 안 남긴다(재실행 때 실린다)",
                [r["key"] for r in ledger_rows(tmp)] == ["§14"])
    rc, out, _e, _t = fire(pack, tmp, cmd)
    ok &= check("D 재실행 = 허용(결정 없음) + §0-C 원문", (out or {}).get("permissionDecision") is None
                and "■ 원문 §0-C (줄" in ctx(out))
    rc, out, _e, _t = fire(pack, tmp, cmd)
    ok &= check("D 세 번째 = 무출력", out is None)
    # 원장 판독 불가(파일 자리에 폴더) → 거부 안 함(fail-open)
    t2 = os.path.join(tmp, "unreadable")
    os.makedirs(os.path.join(t2, "state", "directive-event", "s9.jsonl"))
    e = env_for(tmp, pack)
    e["CYS_STATE_DIR"] = os.path.join(t2, "state")
    rc, out, _e, _t = fire(pack, tmp, cmd, sid="s9", env=e)
    ok &= check("D 원장 판독 불가 → 거부하지 않는다", rc == 0 and (out or {}).get("permissionDecision") != "deny")
    # 읽기만 불가(깨진 UTF-8)·쓰기는 됨 — 위 폴더 판은 쓰기도 실패해 F3 방어층이 함께 막는다. 판독 축만 따로 잰다
    t4 = os.path.join(tmp, "badutf8")
    os.makedirs(os.path.join(t4, "state", "directive-event"))
    with open(os.path.join(t4, "state", "directive-event", "s7.jsonl"), "wb") as f:
        f.write(b"\xff\xfe\xfd\n")
    e = env_for(tmp, pack)
    e["CYS_STATE_DIR"] = os.path.join(t4, "state")
    rc, out, _e, _t = fire(pack, tmp, cmd, sid="s7", env=e)
    ok &= check("D 원장 판독 불가(깨진 UTF-8 · 쓰기 가능) → 거부하지 않는다",
                rc == 0 and (out or {}).get("permissionDecision") != "deny")
    # 원장 폴더 쓰기 불가 → 거부하지 않는다(agy 1R F3 — 못 쓰면 매번 첫 실행으로 읽혀 영구 거부가 된다)
    t3 = os.path.join(tmp, "unwritable")
    ro = os.path.join(t3, "state", "directive-event")
    os.makedirs(ro)
    os.chmod(ro, 0o500)
    try:
        e = env_for(tmp, pack)
        e["CYS_STATE_DIR"] = os.path.join(t3, "state")
        dec = []
        for _i in range(2):
            rc, out, _e, _t = fire(pack, tmp, cmd, sid="s8", env=e)
            dec.append((rc, (out or {}).get("permissionDecision")))
        ok &= check("D 원장 쓰기 불가 → 두 번 다 거부하지 않는다(fail-open)",
                    all(r == 0 and d != "deny" for r, d in dec), str(dec))
    finally:
        os.chmod(ro, 0o700)
    # mission status 는 거부 대상이 아니다
    rc, out, _e, _t = fire(pack, tmp, 'python3 bin/javis_mission.py status', sid="s3")
    ok &= check("D mission status = 거부 없음 · §0-C 주입", (out or {}).get("permissionDecision") is None
                and "■ 원문 §0-C" in ctx(out))
    return ok


def s_F(pack, tmp):
    d = os.path.join(tmp, "state", "directive-event")
    os.makedirs(d)
    with open(os.path.join(d, "s1.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"mode": "inject", "key": "§X", "act": "ctx", "chars": 21000}) + "\n")
    rc, out, _e, _t = fire(pack, tmp, "cys launch-agent --role w")
    c = ctx(out)
    ok = check("F 울타리: §1-A(844)는 들어가고 §2 는 「주입 상한 도달」+ 줄 범위",
               "■ 원문 §1-A" in c and "■ 원문 §2 " not in c and "주입 상한 도달 — §2 원문 생략" in c
               and "줄 324–366" in c, c[-300:])
    rows = [r for r in ledger_rows(tmp) if r.get("key") == "§2"]
    ok &= check("F 울타리 기록 1줄(fence)", [r["mode"] for r in rows] == ["fence"])
    rc, out, _e, _t = fire(pack, tmp, "cys launch-agent --role w")
    ok &= check("F 울타리 고지도 세션당 1회", out is None)
    return ok


def s_S(pack, tmp):
    rc, out, _e, _t = fire(pack, tmp, "python3 bin/javis_orchestra.py gate-status --task T")
    c = ctx(out)
    ok = check("S gate-status 출력 ≤9,000자", 0 < _tci.ulen(c) <= 9000, "%d" % _tci.ulen(c))
    ok &= check("S §0-C 실림 · §7 은 이름 고지로 빠짐", "■ 원문 §0-C" in c and "■ 원문 §7 " not in c
                and "싣지 않은 블록 = §7" in c, c[-200:])
    ok &= check("S 원장에 §7 없음(다음에 실릴 수 있게)", [r["key"] for r in ledger_rows(tmp)] == ["§0-C"])
    rc, out, _e, _t = fire(pack, tmp, "python3 bin/javis_orchestra.py gate-status --task T")
    ok &= check("S 두 번째 gate-status = §7 원문", "■ 원문 §7 (줄" in ctx(out))
    return ok


def s_M(pack, tmp):
    p = os.path.join(pack, "directives", "MASTER_DIRECTIVE.md")
    t = open(p, encoding="utf-8").read()
    old = "## 2. 노드 생성·각성"
    assert t.count(old) == 1, "제목 삭제 변이 대상 %d건" % t.count(old)
    open(p, "w", encoding="utf-8").write(t.replace(old, "노드 생성·각성(제목 줄 삭제됨)"))
    rc, out, _e, _t = fire(pack, tmp, "cys launch-agent --role w")
    ok = check("M 제목 삭제 → 「절 §2 를 찾지 못했다」 고지", "절 §2 를 찾지 못했다(제목 변경?)" in ctx(out), ctx(out)[-200:])
    probs, _n = load_pf(pack).core_injection_problems(pack, home=os.path.join(tmp, "home"))
    ok &= check("M 제목 삭제 → C82 적색(트리거 절 실재 축)", any("트리거 절 §2" in x for x in probs), str(probs)[:300])
    return ok


def s_P(pack, tmp):
    rc, out, _e, _t = fire(pack, tmp, "echo 'cys launch-agent")
    rows = ledger_rows(tmp)
    return check("P 파싱 실패 → 무출력 · 원장 parse_fail", rc == 0 and out is None
                 and [r["mode"] for r in rows] == ["parse_fail"], str(rows))


def s_L(pack, tmp):
    d = os.path.join(tmp, "state", "directive-event")
    lock = os.path.join(d, "s1.jsonl.lock")
    os.makedirs(lock)
    with open(os.path.join(lock, "owner"), "w") as f:
        f.write("999999 %f\n" % time.time())          # 죽은 pid · 방금 시각
    rc, out, _e, _t = fire(pack, tmp, "cys launch-agent --role w")
    ok = check("L 죽은 pid 락 회수 → 주입 · 락 해제", "■ 원문 §2" in ctx(out) and not os.path.exists(lock)
               and "lock_fail" not in [r["mode"] for r in ledger_rows(tmp)])
    os.makedirs(os.path.join(d, "s4.jsonl.lock"))
    with open(os.path.join(d, "s4.jsonl.lock", "owner"), "w") as f:
        f.write("%d %f\n" % (os.getpid(), time.time()))  # 살아 있는 pid · 신선
    rc, out, _e, _t = fire(pack, tmp, "cys feed push", sid="s4")
    ok &= check("L 살아 있는 락 → 주입은 한다 + lock_fail 기록", "■ 원문 §4" in ctx(out)
                and "lock_fail" in [r["mode"] for r in ledger_rows(tmp, "s4")])
    ok &= check("L 남의 락은 건드리지 않는다", os.path.isdir(os.path.join(d, "s4.jsonl.lock")))
    # 늦게 깨어난 옛 소유자의 _unlock 이 회수자의 새 락을 지우지 않는다(agy 1R F2)
    ci = ci_mod(pack)
    l5 = os.path.join(d, "s5.jsonl.lock")
    got = ci._lock(l5)
    with open(os.path.join(l5, "owner"), "w") as f:
        f.write("%d %f\n" % (os.getppid(), time.time()))   # 회수자(다른 pid)가 새로 잡은 락
    ci._unlock(l5)
    kept = os.path.isdir(l5)
    ok &= check("L _unlock = 내 락일 때만 푼다(남의 owner 면 그대로)", got and kept)
    if kept:
        with open(os.path.join(l5, "owner"), "w") as f:
            f.write("%d %f\n" % (os.getpid(), time.time()))
        ci._unlock(l5)
        ok &= check("L _unlock 대조군: 내 owner 면 푼다", not os.path.exists(l5))
    return ok


def s_Z(pack, tmp):
    """PATH = 기록용 가짜 명령만 있는 폴더. 비일치 경로가 외부 명령을 하나라도 부르면 가짜가 기록하거나
    (목록에 있는 이름) 셸이 command not found 를 stderr 로 낸다(목록 밖 이름 · 이 경로엔 stderr 억제가 없다)."""
    shim = os.path.join(tmp, "shimbin")
    os.makedirs(shim)
    log = os.path.join(tmp, "ext-calls.log")
    for n in ("uname", "cat", "dirname", "basename", "python3", "python", "sed", "grep", "tr", "readlink",
              "locale", "timeout", "gtimeout", "head", "tail", "date", "mkdir", "env", "cys", "wc", "printf", "sh"):
        with open(os.path.join(shim, n), "w") as f:
            f.write("#!/bin/sh\necho %s >> '%s'\nexit 0\n" % (n, log))
        os.chmod(os.path.join(shim, n), 0o755)
    e = env_for(tmp, pack)
    e["PATH"] = shim
    e.pop("CYS_PY", None)
    sh = shutil.which("sh")
    ok = True
    for cmd in ("ls -la && git status", "grep -n launch x", "echo hello", "cat ~/cys-data/feed.log"):
        r = subprocess.run([sh, os.path.join(pack, "hooks", "directive-event-inject.sh")], input=hook_in(cmd),
                           capture_output=True, text=True, env=e, timeout=20)
        calls = open(log).read() if os.path.isfile(log) else ""
        ok &= check("Z 비일치 %r: 외부 명령 0(가짜 기록 0 · stderr 0) · 무출력 · rc 0" % cmd,
                    r.returncode == 0 and r.stdout == "" and r.stderr == "" and calls == "", (calls + r.stderr)[:200])
    # 대조군: 트리거면 프리루드·인터프리터 해소가 외부 명령을 부른다 — 같은 측정기가 그걸 본다
    r = subprocess.run([sh, os.path.join(pack, "hooks", "directive-event-inject.sh")],
                       input=hook_in("cys launch-agent --role w"), capture_output=True, text=True, env=e, timeout=20)
    calls = open(log).read() if os.path.isfile(log) else ""
    ok &= check("Z 대조군(트리거): 같은 측정기에 외부 명령 호출이 잡힌다 · rc 0", r.returncode == 0 and calls != "",
                calls.replace("\n", " ")[:160])
    return ok


def s_C(pack, tmp):
    rc, out, _e, _t = fire(pack, tmp, "cys-dept create d1")
    c = ctx(out)
    ok = check("C CEO: cys-dept → [부서 수명주기] 원문", "[부서 수명주기" in c and "■ 원문 [부서 수명주기]" in c, c[:200])
    rc, out, _e, _t = fire(pack, tmp, "cys launch-agent --role w", sid="s2")
    ok &= check("C CEO: §2 줄 번호 = CEO 템플릿 기준(406–448)", "■ 원문 §2 (줄 406–448)" in ctx(out), ctx(out)[:160])
    return ok


def s_Q(pack, tmp):
    ci = ci_mod(pack)
    ok = True
    for fn, kind in (("MASTER_DIRECTIVE.md", "master"),):
        t = ci.read(os.path.join(pack, "directives", fn))
        toc = ci.toc_block(t, kind, "P")
        for tk, tn, ts, keys, act, seat, _b in ci.EVENT_TRIGGERS:
            if seat == "ceo":
                continue
            for k in keys:
                line = next((x for x in toc.split("\n") if x.startswith("· %s " % k)), "")
                ok &= check("Q 목차 %s 에 ⇐ 표지" % k, "⇐" in line, line[:80])
    return ok


def s_W(pack, tmp):
    def med(cmd):
        ts = []
        for i in range(5):
            _rc, _o, _e, t = fire(pack, tmp, cmd, sid="w%d" % i)
            ts.append(t)
        return statistics.median(ts)
    a, b = med("ls -la"), med("cys launch-agent --role w")
    NOTES.append("지연(맥 · 5회 중앙값 · 하네스 subprocess 포함): 비일치 %.3fs · 일치(첫 주입) %.3fs" % (a, b))
    return check("W 지연 실측 기록", True, NOTES[-1])


SCEN = {"T": (s_T, {}), "N": (s_N, {}), "X": (s_X, {}), "R": (s_R, {}), "O": (s_O, {}), "D": (s_D, {}),
        "F": (s_F, {}), "S": (s_S, {}), "M": (s_M, {}), "P": (s_P, {}), "L": (s_L, {}), "Z": (s_Z, {}),
        "C": (s_C, {"ceo": True}), "Q": (s_Q, {}), "W": (s_W, {})}


def scenario(key, mutate=None):
    fn, kw = SCEN[key]
    tmp = tempfile.mkdtemp(prefix="ev-%s-" % key)
    try:
        pack = make_pack(tmp, **kw)
        if mutate:
            mutate(pack)
        return fn(pack, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 뮤턴트: (이름, 파일, 찾을 문자열, 바꿀 문자열, 적색이어야 할 시나리오) — 변이 적용을 먼저 단언한다 ─────
MUTANTS = [
    ("서브에이전트 가드 제거(셸) × 파이썬 가드 제거 → R", "hooks/directive-event-inject.sh",
     "  *'\"agent_id\"'*) exit 0 ;;\n", "", "R"),
    ("역할 가드 제거 → R", "hooks/directive-event-inject.sh", '[ "${CYS_ROLE:-}" = "master" ] || exit 0\n', "", "R"),
    ("세션당 1회 무력화(done 무시) → O", "hooks/core_inject.py",
     "            if (key, act) in done:\n                continue\n", "", "O"),
    ("총량 울타리 무력화(24000→10**9) → F", "hooks/core_inject.py",
     "EVENT_TOTAL_CAP = 24000 ", "EVENT_TOTAL_CAP = 10**9 ", "F"),
    ("§14 거부 → 추가 문맥 격하(deny 행 act=ctx) → D", "hooks/core_inject.py",
     '("§14",), "deny", "all"', '("§14",), "ctx", "all"', "D"),
    ("판독 불가 fail-open 제거(not readable 조건 삭제) → D", "hooks/core_inject.py",
     "                if not readable or sec is None:\n", "                if sec is None:\n", "D"),
    ("인용 heredoc 본문을 대조(오탐) → N", "hooks/core_inject.py",
     "                if not quoted:\n                    nested.extend(", "                if True:\n                    nested.extend(", "N"),
    ("셸이 받는 heredoc 재귀 제거 → X", "hooks/core_inject.py",
     "                for b in bodies:\n                    out.extend(split_commands(b, depth + 1))\n",
     "                pass\n", "X"),
    ("명령 치환 재귀 제거 → X", "hooks/core_inject.py",
     "    for sub in nested:\n        out.extend(split_commands(sub, depth + 1))\n", "", "X"),
    ("출력 조립 상한 해제(assemble 우회 — 전부 싣기) → S", "hooks/core_inject.py",
     "            body, dropped, partial = assemble(blocks, dpath)\n",
     '            body, dropped, partial = "".join(t for _n, t, _p in blocks), [], None\n', "S"),
    ("못 실은 블록도 원장에 기록 → S", "hooks/core_inject.py",
     '            rows = [r for r in rows if r.get("key") not in dropped]\n', "", "S"),
    ("낡은 락 회수 제거(rename 회수 → 항상 실패) → L", "hooks/core_inject.py",
     "            os.rename(lockdir, grave)     # 회수 권리는 rename 성공자 한 명뿐\n",
     "            raise OSError('회수 금지')\n", "L"),
    ("1차 거름 무력화(모든 입력 통과) → Z", "hooks/directive-event-inject.sh",
     "  *) exit 0 ;;\nesac\n\n_H=", "  *) ;;\nesac\n\n_H=", "Z"),
    ("래퍼 값 옵션 무시(sudo -u root 의 root 를 실행 파일로) → X", "hooks/core_inject.py",
     "                k += 2 if t[k] in WRAPPER_ARGOPTS.get(b, ()) else 1\n", "                k += 1\n", "X"),
    ("_unlock 소유자 대조 제거 → L", "hooks/core_inject.py",
     "            if int(f.read().split()[0]) != os.getpid():\n                return\n",
     "            pass\n", "L"),
    ("거부 전 원장 기록 확인 제거(쓰기 실패해도 거부) → D", "hooks/core_inject.py",
     "            except OSError:\n                deny = None\n",
     "            except OSError:\n                out = {\"hookSpecificOutput\": {\"hookEventName\": \"PreToolUse\", "
     "\"permissionDecision\": \"deny\", \"permissionDecisionReason\": deny}}\n", "D"),
    ("셸 거름 feed 를 옛 고정 문자열로 → X", "hooks/directive-event-inject.sh",
     "|*cys*[[:space:]]feed*|", "|*'cys feed'*|", "X"),
    ("CEO 전용 행을 master 좌석에도 → T", "hooks/core_inject.py",
     '                if seat == "ceo" and kind != "ceo":\n                    continue\n                if tk != ek',
     '                if tk != ek', "T"),
    ("C82 트리거 제목 축 제거 → M", "bin/javis_preflight.py",
     "                    if ci.find_section(_secs, _key) is None:\n", "                    if False:\n", "M"),
]


def apply_mut(pack, rel, old, new):
    p = os.path.join(pack, rel)
    t = open(p, encoding="utf-8").read()
    assert t.count(old) == 1, "변이 대상 %d건(1건이어야 함): %r" % (t.count(old), old[:60])
    open(p, "w", encoding="utf-8").write(t.replace(old, new))
    assert open(p, encoding="utf-8").read() != t, "변이 미적용"


def run_mutants():
    global fails
    killed, bad = 0, []
    base_fail = {}
    for k in sorted({m[4] for m in MUTANTS}):
        saved = list(fails)
        base_fail[k] = not scenario(k)
        fails = saved
    for name, rel, old, new, target in MUTANTS:
        if base_fail[target]:
            bad.append(name + " (대상 %s 가 변이 전부터 적색 — 측정 무효)" % target)
            print("INVALID  %s" % name)
            continue
        saved = list(fails)

        def mut(pack, rel=rel, old=old, new=new, name=name):
            apply_mut(pack, rel, old, new)
            if name.startswith("서브에이전트 가드 제거"):     # 셸·파이썬 두 겹 — 둘 다 벗겨야 그물이 보인다
                apply_mut(pack, "hooks/core_inject.py",
                          '    if not isinstance(h, dict) or "agent_id" in h:', '    if not isinstance(h, dict):')
        try:
            green = scenario(target, mutate=mut)
        except AssertionError as e:
            fails = saved
            bad.append("%s (NOT-APPLIED: %s)" % (name, e))
            print("NOT-APPLIED %s — %s" % (name, e))
            continue
        except Exception as e:   # noqa: BLE001 — 변이가 문법·임포트를 깨뜨리면 그 적색은 공짜다(측정 무효)
            fails = saved
            bad.append("%s (CRASH — 변이가 모듈을 깨뜨림: %s: %s)" % (name, type(e).__name__, e))
            print("CRASH    %s — %s" % (name, e))
            continue
        fails = saved
        if green:
            bad.append(name)
            print("SURVIVED %s" % name)
        else:
            killed += 1
            print("KILLED   %s" % name)
    print("\nMUTANTS killed=%d / %d" % (killed, len(MUTANTS)))
    return bad


if __name__ == "__main__":
    for k in ("T", "N", "X", "R", "O", "D", "F", "S", "M", "P", "L", "Z", "C", "Q", "W"):
        scenario(k)
    for n in NOTES:
        print("NOTE " + n)
    mbad = run_mutants() if "--mutants" in sys.argv else []
    if fails or mbad:
        print("\nFAIL %s %s" % (fails, mbad))
        sys.exit(1)
    print("\nALL PASS")
