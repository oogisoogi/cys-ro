#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_t6_injection_policy.py — 복원 주입 정책(TICKET=restore-impl-A2-2 · T6).

오너 확정 정책: 「대화는 자동 복원한다 · 이어서 하라는 지시는 주입하지 않는다 · 일은 사용자의 말 뒤에만」.

  E. inject-context.sh — startup/resume 신호에 「재개」 지시가 없다 · 상태만 복원하고 대기 · 임무 게이트 문구 유지
     (대조: clear/compact 신호는 종전 그대로)
  F. session-start.sh — resume 주입 상한: 대형 원문 → 경로만(출력 < 10,000자) · 목차·부트 브리지가 잘릴 수 있는
     블록보다 앞 · 작은 원문은 그대로 · 비복원(startup)은 종전(전문 주입)
  G. session-start.sh — 「Continue from where you left off.」 = 기계 문구(사람 입력으로 세지 않는다)

전 과정 임시 디렉터리(HOME·CYS_PACK_DIR·CYS_LOCAL_DIR 격리 · cys 는 가짜 스텁).
실행: python3 cysjavis-pack/bin/tests/test_t6_injection_policy.py → 종료 토큰 T6-INJECTION-POLICY-OK
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.normpath(os.path.join(HERE, "..", "..", "hooks"))
INJECT = os.path.join(HOOKS, "inject-context.sh")
SSTART = os.path.join(HOOKS, "session-start.sh")
BASH = shutil.which("bash") or "bash"
fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + str(detail)) if detail else ""))
    if not cond:
        fails.append(name)


def base_env(tmp):
    home = os.path.join(tmp, "home")
    os.makedirs(home, exist_ok=True)
    stub = os.path.join(tmp, "stubbin")
    os.makedirs(stub, exist_ok=True)
    with open(os.path.join(stub, "cys"), "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(os.path.join(stub, "cys"), 0o755)
    env = dict(os.environ)
    for k in ("CYS_ROLE", "CYS_SOUL", "CYS_ROOT", "CYS_STATE_DIR"):
        env.pop(k, None)
    env.update({"HOME": home, "CYS_LOCAL_DIR": os.path.join(tmp, "local"), "CYS_SURFACE_ID": "3",
                "PATH": stub + os.pathsep + env.get("PATH", "")})
    return env


# ── E. inject-context.sh ──
tmp = tempfile.mkdtemp(prefix="t6-e-")
try:
    env = base_env(tmp)
    env["CYS_PACK_DIR"] = os.path.join(tmp, "nopack")
    proj = os.path.join(tmp, "proj")
    os.makedirs(proj, exist_ok=True)
    outs = {}
    for src in ("startup", "resume", "clear", "compact"):
        r = subprocess.run([BASH, INJECT], input=json.dumps({"source": src, "cwd": proj}), capture_output=True,
                           text=True, encoding="utf-8", env=env, timeout=120)
        outs[src] = (r.returncode, r.stdout)
    for src in ("startup", "resume"):
        code, out = outs[src]
        line = next((l for l in out.splitlines() if l.startswith("▶ 복원 모드(source=%s)" % src)), "")
        check("E1 %s: 복원 신호 존재 · exit 0" % src, code == 0 and bool(line), line[:80])
        check("E2 %s: 「재개」 지시 없음" % src, "재개" not in line and "미해결 게이트부터" not in line, line)
        check("E3 %s: 상태만 복원하고 대기 · 사용자(또는 임무 게이트) 지시 뒤" % src,
              "상태만 복원하고 대기" in line and "사용자(또는 임무 게이트)의 지시 뒤에" in line, line[:120])
        check("E4 %s: 임무 게이트 유지(exit 0=임무 지정 좌석은 이어감 · exit 3=보고 후 멈춤)" % src,
              "exit 0" in line and "exit 3" in line, line[-160:])
    check("E5 대조: clear 신호 종전 그대로", "▶ 작업 계속(source=clear)" in outs["clear"][1])
    check("E6 대조: compact 신호 종전 그대로", "▶ 압축 직후(source=compact)" in outs["compact"][1])
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# ── F/G. session-start.sh ──
def ss_setup(tmp, directive_body):
    env = base_env(tmp)
    pack = os.path.join(tmp, "pack")
    os.makedirs(os.path.join(pack, "directives"), exist_ok=True)
    os.makedirs(os.path.join(pack, "bin"), exist_ok=True)
    for d in ("MASTER", "WORKER"):
        with open(os.path.join(pack, "directives", "%s_DIRECTIVE.md" % d), "w", encoding="utf-8") as f:
            f.write("DIRECTIVE-BODY-%s\n%s\n" % (d, directive_body))
    with open(os.path.join(pack, "bin", "javis_bootstrap.py"), "w", encoding="utf-8") as f:
        f.write("# stub\n")
    with open(os.path.join(pack, "soul.md"), "w", encoding="utf-8") as f:
        f.write("SOUL-BODY\n")
    env["CYS_PACK_DIR"] = pack
    return env, pack


def ss_run(env, role, hook_in):
    e = dict(env)
    e["CYS_ROLE"] = role
    r = subprocess.run(["sh", SSTART], input=hook_in, capture_output=True, text=True, encoding="utf-8",
                       env=e, timeout=60)
    return r.returncode, r.stdout, r.stderr


tmp = tempfile.mkdtemp(prefix="t6-f-")
try:
    big = "가나다라마바사 " * 6000  # ≈ 48,000자 — Claude Code 10,000자 미리보기 한계를 훌쩍 넘는다
    env, pack = ss_setup(tmp, big)
    tp = os.path.join(tmp, "t.jsonl")
    open(tp, "w", encoding="utf-8").write("")
    hin_resume = json.dumps({"transcript_path": tp, "source": "resume"}) + "\n"
    for role in ("master", "worker-1"):
        code, out, err = ss_run(env, role, hin_resume)
        dpath = os.path.join(pack, "directives", "%s_DIRECTIVE.md" % ("MASTER" if role == "master" else "WORKER"))
        check("F1 %s resume 대형 원문 → 출력 < 10,000자" % role, code == 0 and len(out) < 10000, len(out))
        check("F2 %s resume 원문 대신 경로(디렉티브 본문 미주입 · 경로 표기)" % role,
              "DIRECTIVE-BODY-" not in out and dpath in out and "원문 생략" in out, out[-200:])
        toc = out.find("복원(resume) 목차")
        cut = out.find("원문 생략")
        check("F3 %s 목차가 잘릴 수 있는 블록(생략 표지)보다 앞" % role, 0 <= toc < cut, (toc, cut))
        if role == "master":
            br = out.find("부트 브리지")
            check("F4 master 부트 브리지가 생략 표지보다 앞(보이는 구간)", 0 <= br < cut and br < 2000, (br, cut))
        else:
            ft = out.find("첫 턴 규율")
            check("F4 worker 첫 턴 규율이 생략 표지보다 앞", 0 <= ft < cut, (ft, cut))
    # 작은 원문은 그대로 붙는다(경로 + 본문)
    tmp2 = tempfile.mkdtemp(prefix="t6-f2-")
    try:
        env2, pack2 = ss_setup(tmp2, "짧은 본문")
        code, out, err = ss_run(env2, "master", hin_resume)
        check("F5 resume 소형 원문 → 본문 포함(상한 미만) · < 10,000자",
              "DIRECTIVE-BODY-MASTER" in out and "SOUL-BODY" in out and "원문 생략" not in out and len(out) < 10000,
              len(out))
        check("F6 resume 소형도 목차 → 브리지 → 본문 순", out.find("복원(resume) 목차") < out.find("부트 브리지")
              < out.find("DIRECTIVE-BODY-MASTER"), (out.find("복원(resume) 목차"), out.find("부트 브리지"),
                                                   out.find("DIRECTIVE-BODY-MASTER")))
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)
    # 비복원(startup) = 종전(전문 주입 · 헤더 → 본문 → 브리지 순)
    code, out, err = ss_run(env, "master", json.dumps({"transcript_path": tp, "source": "startup"}) + "\n")
    check("F7 대조: startup 은 종전대로 전문 주입(상한 미적용)",
          "DIRECTIVE-BODY-MASTER" in out and "원문 생략" not in out and len(out) > 10000
          and out.find("DIRECTIVE-BODY-MASTER") < out.find("부트 브리지"), len(out))
    code, out, err = ss_run(env, "master", "")
    check("F8 대조: stdin 없음(source 미상) = 종전 전문 주입", "DIRECTIVE-BODY-MASTER" in out and code == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ── G. 기계 문구 제외 목록 ──
src = open(SSTART, encoding="utf-8").read()
check("G1 제외 목록 튜플에 「Continue from where you left off.」", '"Continue from where you left off."))' in src)
tmp = tempfile.mkdtemp(prefix="t6-g-")
try:
    env, pack = ss_setup(tmp, "본문")

    def _u(t):
        return {"type": "user", "message": {"role": "user", "content": t}}
    HEAD = "■ 복원 · 브리프 0건 · 행동 0 · 【질문】만 허용"
    for name, recs, want in (
            ("machine", [_u("WORKER_DIRECTIVE 각성: 브리프를 기다려라."), _u("Continue from where you left off.")], True),
            ("human", [_u("WORKER_DIRECTIVE 각성: 브리프를 기다려라."), _u("브리프: 이 작업을 하라")], False)):
        jp = os.path.join(tmp, name + ".jsonl")
        with open(jp, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        code, out, err = ss_run(env, "worker-1", json.dumps({"transcript_path": jp, "source": "resume"}) + "\n")
        check("G2 %s: 복원 0건 블록 %s" % (name, "주입(사람 입력 0건)" if want else "무주입(사람 입력 1건)"),
              (HEAD in out) == want and code == 0, out[:200] if (HEAD in out) != want else "")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAIL: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("\nALL PASS")
print("T6-INJECTION-POLICY-OK")
sys.exit(0)
