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


# ★재조준(TICKET=v110-integ 통합 병합 · 2026-09-20) — 옛 계약을 지우지 않고 아래에 적어 둔다.
#   옛 계약(restore-impl-A2-2 초판): master·worker 두 좌석 모두 resume 상한을 session-start.sh 의 T6 경로
#     (「복원(resume) 목차」 + 「원문 생략」)로 지킨다 · startup 은 master 도 전문 주입(상한 미적용).
#   무엇이 그것을 갈아치웠나: fix/v110-inject 의 injection-slim T2 가 master·CEO 좌석을 조립기
#     (hooks/core_inject.py)로 돌려 **source 무관** ≤9,000자를 보장한다. 그래서 master 는 T6 경로에
#     도달하지 않는다(상위 기제가 하위 기제를 흡수 — 해소 근거는 session-start.sh 의 병합 해소 주석).
#   축은 그대로다: 「대형 원문이 와도 출력이 10,000자를 안 넘고 · 보여야 하는 규범이 절단 표지보다 앞이고 ·
#     원문은 경로로 안내된다」. 재는 표지만 좌석별로 갈린다 —
#       master  = 「■ 자기 절단」(조립기 고지) · 부트 브리지 · 원문 경로
#       worker  = 「복원(resume) 목차」 + 「원문 생략」(T6 경로 · 옛 계약 그대로 유지)
#   ⛔ master 에 옛 표지(목차·원문 생략)를 다시 요구하면 T2 가 되돌려진 것이다 — 그때는 이 주석을 읽어라.
CUTMARK = {"master": "■ 자기 절단", "worker-1": "원문 생략"}
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
        cut = out.find(CUTMARK[role])
        check("F1 %s resume 대형 원문 → 출력 < 10,000자" % role, code == 0 and len(out) < 10000, len(out))
        check("F2 %s resume 대형 본문 미주입 · 절단 고지 + 원문 경로 안내" % role,
              cut >= 0 and dpath in out and out.count("가나다라마바사") == 0,
              (cut, dpath in out, out.count("가나다라마바사")))
        if role == "master":
            br = out.find("부트 브리지")
            check("F3 master 부트 브리지가 절단 고지보다 앞(보이는 구간 · 앞 2,000자 안)",
                  0 <= br < cut and br < 2000, (br, cut))
            check("F4 master 는 조립기 상한 안(≤9,000 · T2)", len(out) <= 9000, len(out))
        else:
            toc = out.find("복원(resume) 목차")
            ft = out.find("첫 턴 규율")
            check("F3 worker 목차가 잘릴 수 있는 블록(생략 표지)보다 앞", 0 <= toc < cut, (toc, cut))
            check("F4 worker 첫 턴 규율이 생략 표지보다 앞 · 앞 2,000자 안(T2a)",
                  0 <= ft < cut and ft < 2000, (ft, cut))
            check("F4b worker 디렉티브 본문 미주입(경로만)", "DIRECTIVE-BODY-" not in out, out[:120])
    # 작은 원문은 그대로 붙는다(경로 + 본문) — 두 좌석 각자의 기제로
    tmp2 = tempfile.mkdtemp(prefix="t6-f2-")
    try:
        env2, pack2 = ss_setup(tmp2, "짧은 본문")
        code, out, err = ss_run(env2, "master", hin_resume)
        check("F5 master resume 소형 원문 → 본문 포함 · 절단 고지 없음 · < 10,000자"
              " (soul 은 이 분기에서 미주입 — T2 가 배경층 훅으로 옮겼다)",
              "DIRECTIVE-BODY-MASTER" in out and "■ 자기 절단" not in out and len(out) < 10000, len(out))
        check("F6 master 소형도 부트 브리지 → 본문 순",
              0 <= out.find("부트 브리지") < out.find("DIRECTIVE-BODY-MASTER"),
              (out.find("부트 브리지"), out.find("DIRECTIVE-BODY-MASTER")))
        code, out, err = ss_run(env2, "worker-1", hin_resume)
        check("F5b worker resume 소형 원문 → 목차 + 본문 + soul 포함 · 생략 표지 없음 · < 10,000자",
              "DIRECTIVE-BODY-WORKER" in out and "SOUL-BODY" in out and "원문 생략" not in out
              and len(out) < 10000, len(out))
        check("F6b worker 소형도 목차 → 본문 순",
              0 <= out.find("복원(resume) 목차") < out.find("DIRECTIVE-BODY-WORKER"),
              (out.find("복원(resume) 목차"), out.find("DIRECTIVE-BODY-WORKER")))
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)
    # 비복원(startup) 대조
    hin_startup = json.dumps({"transcript_path": tp, "source": "startup"}) + "\n"
    # ★v116-seat D3-o 재조준 — 옛 F7(「startup 비-master = 전문 주입 · len > 10,000」)은 지운다. 그 전문은 10,000자를
    #   넘어 Claude Code 가 저장 파일 + 앞 2,000자 미리보기로 바꿨으므로 모델에 닿지 않았다(D3-pack.md D3-o · 실물 68,516B).
    #   새 계약 = startup 도 resume 과 같은 상한: 출력 < 10,000자 · 첫 턴 규율·각성 헤더가 앞 · 원문은 목차(경로) + 생략 고지.
    for src_name, hin in (("startup", hin_startup), ("source 미상", "")):
        code, out, err = ss_run(env, "worker-1", hin)
        cut = out.find("원문 생략")
        wpath = os.path.join(pack, "directives", "WORKER_DIRECTIVE.md")
        check("F7 %s 비-master 대형 원문 → 출력 < 10,000자 · 본문 미주입(D3-o)" % src_name,
              code == 0 and len(out) < 10000 and "DIRECTIVE-BODY-WORKER" not in out
              and out.count("가나다라마바사") == 0, len(out))
        check("F7c %s 첫 턴 규율·DRAIN·각성 헤더 → 원문 목차(경로) → 생략 고지 순" % src_name,
              0 <= out.find("첫 턴 규율") < out.find("■ CYSJavis 역할 각성") < out.find("■ 원문 목차") < cut
              and "[DRAIN]" in out[:2000] and wpath in out,
              (out.find("첫 턴 규율"), out.find("■ 원문 목차"), cut))
    tmp3 = tempfile.mkdtemp(prefix="t6-f7-")
    try:
        env3, _p3 = ss_setup(tmp3, "짧은 본문")
        code, out, err = ss_run(env3, "worker-1", hin_startup)
        check("F7d startup 소형 원문은 종전대로 본문·soul 포함 · 목차·생략 표지 없음",
              "DIRECTIVE-BODY-WORKER" in out and "SOUL-BODY" in out and "원문 생략" not in out
              and "■ 원문 목차" not in out, len(out))
    finally:
        shutil.rmtree(tmp3, ignore_errors=True)
    code, out, err = ss_run(env, "master", hin_startup)
    check("F7b master 는 startup 도 조립기 상한 안(T2 는 source 무관 — 옛 계약의 「전문 주입」을 대체)",
          code == 0 and len(out) <= 9000 and out.count("가나다라마바사") == 0, len(out))
    # ★v116-seat F7(D3-pack.md): master·CEO 좌석도 훅으로 DRAIN 규칙 줄을 받는다(조립기 상한 안 · 부트 브리지 유지).
    check("F7e master 훅 출력에 DRAIN 규칙 줄 · 조립기 상한 안 · 부트 브리지 유지",
          "■ 재시작 저장 지시: [DRAIN]" in out and len(out) <= 9000 and "부트 브리지" in out, len(out))
    code, out, err = ss_run(env, "master", "")
    check("F8 대조: stdin 없음(source 미상) = 조립기 경로 · 원문 절 주입", "DIRECTIVE-BODY-MASTER" in out and code == 0)
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
