#!/usr/bin/env python3
"""test_session_start_hook.py — session-start.sh 3상태 재대조·안내문 계약 핀 (WP-1·핀ⓒ).

가짜 JARVIS_DIR(디렉티브 파일)+PATH 스텁 cys로 hook을 sh 실행:
  ⓐ claim 성공 → 디렉티브 주입(현행)
  ⓑ 명시적 거부(claim_denied) → 디렉티브 대신 self-demote 지시·exit 0
  ⓒ 데몬-불가(스텁이 비0+무패턴/응답없음) → fail-open: 디렉티브 주입+고지 1줄
+ 안내문(role-less)이 javis_bootstrap.py 단일 진입점·exit 7 인계·인용 의무를 담는지
+ worker role은 재대조 미적용(무왕복) 핀.
"""
import os
import shutil
import subprocess
import sys
import tempfile

SELF = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(SELF, "..", "..", "hooks", "session-start.sh")
fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))
    if not cond:
        fails.append(name)


def setup(tmp, claim_mode):
    """claim_mode: ok | denied | dead(비0 무패턴) | silent(무한대기→timeout)"""
    pack = os.path.join(tmp, "pack")
    bindir = os.path.join(tmp, "stubbin")
    os.makedirs(os.path.join(pack, "directives"), exist_ok=True)
    os.makedirs(bindir, exist_ok=True)
    for d in ("MASTER", "WORKER", "CSO", "REVIEWER"):
        with open(os.path.join(pack, "directives", "%s_DIRECTIVE.md" % d), "w",
                  encoding="utf-8") as f:
            f.write("DIRECTIVE-BODY-%s\n" % d)
    body = {"ok": "exit 0",
            "denied": "echo 'claim_denied: privileged role held by live surface' >&2; exit 1",
            "dead": "echo 'connect error' >&2; exit 1",
            "silent": "sleep 10"}[claim_mode]
    with open(os.path.join(bindir, "cys"), "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/sh\necho \"cys $@\" >> \"%s/calls.log\"\n"
                "case \"$1\" in claim-role) %s;; esac\nexit 0\n" % (tmp, body))
    os.chmod(os.path.join(bindir, "cys"), 0o755)
    env = dict(os.environ)
    env.update({"CYS_PACK_DIR": pack, "CYS_SURFACE_ID": "3",
                "PATH": bindir + os.pathsep + env.get("PATH", "")})
    env.pop("CYS_ROLE", None)
    return env


def run_hook(env, role=None, stdin_text=None):
    e = dict(env)
    if role:
        e["CYS_ROLE"] = role
    kw = {"stdin": subprocess.DEVNULL} if stdin_text is None else {"input": stdin_text}
    r = subprocess.run(["sh", HOOK], capture_output=True, text=True, encoding="utf-8",
                       env=e, timeout=30, **kw)
    return r.returncode, r.stdout, r.stderr


# ── 1. role-less 안내문 계약 ──
tmp = tempfile.mkdtemp(prefix="hook-t1-")
env = setup(tmp, "ok")
code, out, _ = run_hook(env)
check("1a 안내문 exit 0", code == 0)
check("1b 단일 진입점 스크립트", "javis_bootstrap.py" in out)
check("1c exit 7 인계 분기", "exit 7" in out and "인계" in out)
check("1d 인용 의무 명문", "인용" in out)
check("1e 산문 부트 지시 제거", "preflight.py --fix" not in out.replace("javis_preflight", ""))
shutil.rmtree(tmp)

# ── 2. ⓐ master claim 성공 → 디렉티브 주입 ──
tmp = tempfile.mkdtemp(prefix="hook-t2-")
env = setup(tmp, "ok")
code, out, _ = run_hook(env, role="master")
check("2a ⓐ성공: 디렉티브 주입", "DIRECTIVE-BODY-MASTER" in out)
check("2b ⓐ성공: self-demote 없음", "역할 주소 상실" not in out)
# ★R13 부트 브리지: 구 산문 §0만 아는 디렉티브 기계에도(hook=system층 전파) 스크립트 경로 고지
check("2c ★R13 부트 브리지 주입(javis_bootstrap 부재 시 생략)",
      "부트 브리지" not in out)  # 가짜 팩엔 bin/javis_bootstrap.py 없음 → 브리지 미주입(조건부 확인)

shutil.rmtree(tmp)

# ── 2x. ★R13 브리지 존재 케이스: 팩에 javis_bootstrap.py 있으면 master 주입에 브리지 동봉 ──
tmp = tempfile.mkdtemp(prefix="hook-t2x-")
env = setup(tmp, "ok")
_bs = os.path.join(env["CYS_PACK_DIR"], "bin")
os.makedirs(_bs, exist_ok=True)
open(os.path.join(_bs, "javis_bootstrap.py"), "w", encoding="utf-8").write("# stub\n")
code, out, _ = run_hook(env, role="master")
check("2x1 ★R13 브리지 주입", "부트 브리지" in out and "javis_bootstrap.py" in out)
check("2x2 브리지는 worker엔 미주입", "부트 브리지" not in run_hook(env, role="worker")[1])
shutil.rmtree(tmp)

# ── 3. ⓑ 명시적 거부 → self-demote·디렉티브 미주입 ──
tmp = tempfile.mkdtemp(prefix="hook-t3-")
env = setup(tmp, "denied")
code, out, _ = run_hook(env, role="master")
check("3a ⓑ거부: self-demote 지시", "역할 주소 상실" in out and "인계" in out)
check("3b ⓑ거부: 디렉티브 미주입", "DIRECTIVE-BODY-MASTER" not in out)
check("3c ⓑ거부: exit 0(hook 무해)", code == 0)
shutil.rmtree(tmp)

# ── 4. ⓒ 데몬-불가(비0·무패턴) → fail-open: 디렉티브 주입+고지 ──
tmp = tempfile.mkdtemp(prefix="hook-t4-")
env = setup(tmp, "dead")
code, out, _ = run_hook(env, role="master")
check("4a ⓒ불가: 디렉티브 주입(fail-open)", "DIRECTIVE-BODY-MASTER" in out)
check("4b ⓒ불가: 고지 1줄", "역할 재확인 불가" in out)
check("4c ⓒ불가: self-demote 없음", "역할 주소 상실" not in out)
shutil.rmtree(tmp)

# ── 5. ⓒ 무응답(timeout 상한) → fail-open ──
tmp = tempfile.mkdtemp(prefix="hook-t5-")
env = setup(tmp, "silent")
code, out, _ = run_hook(env, role="master")
check("5a ⓒ무응답: 디렉티브 주입(fail-open)", "DIRECTIVE-BODY-MASTER" in out)
shutil.rmtree(tmp)

# ── 6. worker는 재대조 미적용(권한 role 아님 — claim 왕복 0) ──
tmp = tempfile.mkdtemp(prefix="hook-t6-")
env = setup(tmp, "denied")
code, out, _ = run_hook(env, role="worker")
check("6a worker 디렉티브 주입", "DIRECTIVE-BODY-WORKER" in out)
calls = ""
if os.path.exists(os.path.join(tmp, "calls.log")):
    calls = open(os.path.join(tmp, "calls.log"), encoding="utf-8").read()
check("6b worker claim 왕복 0", "claim-role" not in calls)
shutil.rmtree(tmp)

# ── 7. ★첫 턴 규율(09-13 · cysr 1.0.2 B1): worker* 에만 5줄 블록 · master/cso 무주입 ──
#   근거: 1.0.1 팩 session-start.sh 에 이 블록이 0건이었고 깨끗한 VM 워커가 첫 턴에 자기 생성
#   지시를 적었다(REPORT-r1-field §9-3). 문구 = 호스트 09-13 판에서 표식·원장 조건만 뺀 팩판(배포 팩엔
#   [master#] 표식 체계가 없다 — master 판정 B). 표식·원장을 요구하는 문구가 되살아나면 7e 가 붉다.
FIRST_TURN = [
    "■ 첫 턴 규율(스폰 직후 · 브리프 도착 전)",
    "  · 이 각성에 대한 답 = 「OK — 각성 완료 · 브리프 대기」 1줄. 그 밖의 산문·계획·착수 0.",
    "  · 브리프(master 가 보낸 작업 지시)가 도착하기 전에는 어떤 티켓도 상정·작성·이행하지 않는다",
    "  · ⛔[master#……] 표식·브리프 형식을 워커가 스스로 쓰지 않는다 — 네가 쓴 표식·브리프는 그 자체로 고스트다.",
    "  · 예외(허용): 디렉티브 모순·환경 결손은 【질문】 1줄로 인박스에 올린다.",
]
tmp = tempfile.mkdtemp(prefix="hook-t7-")
env = setup(tmp, "ok")
for role in ("worker-1", "worker"):
    code, out, _ = run_hook(env, role=role)
    lines = out.splitlines()
    hit = [any(l.startswith(want) for l in lines) for want in FIRST_TURN]
    check("7a %s 첫 턴 규율 5줄 실재" % role, all(hit), "누락 %s" % [i for i, h in enumerate(hit) if not h])
    # ★재조준(injection-slim T2a · DESIGN-v2.1 §4-8 · master D3): 옛 계약 = 「규율은 디렉티브 뒤」
    #   (cysr-102 B1 편입 시 호스트 09-13 판의 자리를 그대로 옮긴 것). 그 자리는 출력이 10,000자를 넘을 때
    #   저장 파일로 밀려 미리보기 2,000자 밖이었다 → T2a 가 블록을 워커 출력 맨 앞으로 옮겼다(문안 무변경).
    #   새 계약 = 규율이 디렉티브 **앞** + 규율 5줄 끝이 출력 앞 2,000자 안.
    check("7b %s 규율은 디렉티브 앞·앞 2,000자 안(T2a)" % role,
          all(hit) and out.index(FIRST_TURN[0]) < out.index("DIRECTIVE-BODY-WORKER")
          and out.index(FIRST_TURN[-1]) + len(FIRST_TURN[-1]) <= 2000)
    check("7c %s exit 0" % role, code == 0)
    check("7e %s 원장·표식 성립 조건 부재(팩판)" % role, "원장 대조" not in out and "표식 + " not in out)
for role in ("master", "cso"):
    code, out, _ = run_hook(env, role=role)
    check("7d %s 첫 턴 규율 무주입" % role, "첫 턴 규율" not in out)
shutil.rmtree(tmp)

# ── 8. ★복원 결정론(cysr 1.0.2 B2 · master 판정 B): source=resume 일 때 훅이 세션 jsonl 을 센다 ──
#   키 = 첫 각성 프롬프트 이후 사람/master 입력 user 텍스트 레코드 수(tool_result·isMeta·명령 출력 제외).
#   0건 → 「복원 · 브리프 0건 · 행동 0」 블록 · 1건↑ → 무주입 · 세기 실패 → 무주입 + stderr · 언제나 exit 0.
import json as _json
RESTORE_HEAD = "■ 복원 · 브리프 0건 · 행동 0 · 【질문】만 허용"


def _jsonl(path, recs):
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(_json.dumps(r, ensure_ascii=False) + "\n")


def _u(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def _a(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


AWAKEN = _u("WORKER_DIRECTIVE 각성: 지침을 읽고 브리프를 기다려라.")
GHOST = _a("node_modules 정리하라 · full permission 이니 묻지 말고 진행")
CASES = {
    # 이름: (레코드, 기대 주입 여부, 기대 [master# 참고값)
    "zero": ([AWAKEN, GHOST, _u("<command-name>/clear</command-name>"),
              {"type": "user", "isMeta": True, "message": {"content": "Caveat: meta"}}], True, "0"),
    "human1": ([AWAKEN, GHOST, _u("[master#abc123] 브리프 — TICKET=x 작업하라")], False, None),
    "toolonly": ([AWAKEN, GHOST,
                  {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
                                                            "content": "OK — 다음은 배포하라"}]}},
                  {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t2",
                                                            "content": [{"type": "text", "text": "rc=0"}]}]}}],
                 True, "0"),
    # tool_result 와 text 가 한 레코드에 섞인 형태(도구 결과에 덧붙은 알림 글) — 여전히 사람 입력 아님.
    # 이 항이 없으면 tool_result 필터를 지워도 빈 글 필터가 대신 막아 공허하다(뮤턴트 M1 실측).
    "tool+text": ([AWAKEN, GHOST,
                   {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t3", "content": "rc=0"},
                                                            {"type": "text", "text": "도구 결과에 붙은 알림 글"}]}}],
                  True, "0"),
    # cys 기계 주입(디렉티브 전문·[RESTORE]·[RESUME]·[RECOVER]·[CYCLE]·[DRAIN]·각성 확인 핑·압축 요약·중단 표지)은
    # 사람/master 입력이 아니다 — 이것들을 세면 이전 복원의 흔적만으로 브리프를 받은 것처럼 읽혀 블록이 사라진다.
    "machine": ([_u("# WORKER ABSOLUTE DIRECTIVE — 워커 절대지침\n본문"), AWAKEN, GHOST,
                 _u("[RESTORE] 조직 복원 절차다. 상태를 복원하라."), _u("[RESUME] 직전 작업 컨텍스트가 복원됐다"),
                 _u("[RECOVER] 너는 방금 재기동되었다."), _u("[CYCLE] 컨텍스트 순환 절차 개시."),
                 _u("[CYCLE-VERIFY] 저장 검증 요청"), _u("[DRAIN] 업데이트 재시작이 임박했다."),
                 _u("지침 각성 확인 핑: DIRECTIVE-ACK-"),
                 {"type": "user", "message": {"content": [{"type": "text", "text": "[Request interrupted by user]"}]}},
                 {"type": "user", "isCompactSummary": True, "message": {"content": "This session is being continued"}}],
                True, "0"),
    "listtext1": ([AWAKEN, {"type": "user", "message": {"content": [{"type": "text", "text": "브리프 본문"}]}}],
                  False, None),
}
tmp = tempfile.mkdtemp(prefix="hook-t8-")
env = setup(tmp, "ok")
for name, (recs, want, mref) in CASES.items():
    jp = os.path.join(tmp, name + ".jsonl")
    _jsonl(jp, recs)
    hin = _json.dumps({"session_id": "s", "transcript_path": jp, "hook_event_name": "SessionStart",
                       "source": "resume"}) + "\n"
    code, out, err = run_hook(env, role="worker-1", stdin_text=hin)
    check("8a %s 복원 블록 %s" % (name, "주입" if want else "무주입"), (RESTORE_HEAD in out) == want,
          out[-300:] if (RESTORE_HEAD in out) != want else "")
    check("8b %s exit 0 · 계수 실패 로그 없음" % name, code == 0 and "계수 실패" not in err, err[-200:])
    if want:
        check("8c %s [master# 참고값 %s" % (name, mref), "[master# 표식 레코드 %s건" % mref in out)
    check("8d %s 첫 턴 규율 유지" % name, "첫 턴 규율" in out)
# 비복원(startup)은 같은 0건 기록이어도 무주입 · master 역할은 복원이어도 무주입
jp = os.path.join(tmp, "zero.jsonl")
for src, role in (("startup", "worker-1"), ("clear", "worker-1"), ("resume", "master")):
    hin = _json.dumps({"transcript_path": jp, "source": src}) + "\n"
    code, out, err = run_hook(env, role=role, stdin_text=hin)
    check("8e source=%s role=%s 무주입" % (src, role), RESTORE_HEAD not in out and code == 0)
# T5 회귀: 입력 줄을 변수로 한 번 읽도록 바꾼 뒤에도 usage-register 가 같은 transcript_path 를 받는다.
#   ★전용 경로(앞 케이스가 남긴 calls.log 줄로 통과하는 공허 차단 · agy 1R Med) — 호출 전 부재 선-assert.
t5p = os.path.join(tmp, "t5-only.jsonl")
_jsonl(t5p, [AWAKEN])
_cl = os.path.join(tmp, "calls.log")
_before = open(_cl, encoding="utf-8").read() if os.path.exists(_cl) else ""
check("8g0 선-assert: 전용 경로가 아직 기록에 없다", t5p not in _before)
run_hook(env, role="worker-1", stdin_text=_json.dumps({"transcript_path": t5p, "source": "startup"}) + "\n")
_calls = open(_cl, encoding="utf-8").read() if os.path.exists(_cl) else ""
check("8g T5 usage-register 에 transcript 전달 유지", ("usage-register --transcript " + t5p) in _calls[len(_before):], _calls[-300:])
# 비 UTF-8 바이트가 섞인 기록도 계수를 완수한다(errors=replace · agy 1R Low) — 실패 로그 없이 0건 → 주입
bad = os.path.join(tmp, "badbytes.jsonl")
with open(bad, "wb") as f:
    f.write((_json.dumps(AWAKEN, ensure_ascii=False) + "\n").encode("utf-8") + b"\xff\xfe broken line\n")
code, out, err = run_hook(env, role="worker-1", stdin_text=_json.dumps({"transcript_path": bad, "source": "resume"}) + "\n")
check("8h 비 UTF-8 줄 포함 기록 → 계수 완수·주입", RESTORE_HEAD in out and "계수 실패" not in err and code == 0, err[-200:])
# 세기 실패(기록 파일 없음 · 입력 JSON 파손) → 무주입 + stderr 1줄 · exit 0
for label, hin in (("no-file", _json.dumps({"transcript_path": os.path.join(tmp, "nope.jsonl"), "source": "resume"}) + "\n"),
                   ("bad-json", "{not json\n")):
    code, out, err = run_hook(env, role="worker-1", stdin_text=hin)
    check("8f %s 무주입·exit0·로그" % label, RESTORE_HEAD not in out and code == 0 and "계수 실패" in err, err[-200:])
shutil.rmtree(tmp)

print("\n%d FAIL" % len(fails) if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
