#!/usr/bin/env python3
"""test_ceo_pending_gate.py — cys-dept CEO 부트 게이트·PENDING 상태 기계 핀 (WP-2).

가짜 HOME(팩 directives·registry)+스텁 cys($HOME/.local/bin — cys-dept PATH prepend 1순위)로
실 데몬 무접촉 검증:
  1) 마커 無 + 승격 시도 → PENDING·디렉티브 무교체(사고 R2 봉쇄) + truthful exit 5
     (af6fcb6 D-2 post-verify: 미승격인데 exit 0이면 GUI가 "승격 완료"로 오보 — 부서 흐름
     불파괴는 내부 ceo_promote의 return 0이 담당, 지명 서브커맨드는 진실 보고)
  2) 마커 생성 후 promote-if-pending(대기형) → 자동 승격(제품 기본 정책)·PENDING 해소·비대기 고지
  3) --request-only → 무변조·알림만·exit 0 (부트 ⑦ 비대기 계약)
  4) 단일소유 가드: master 세션 대기형=exit 7 / --request-only=허용
  5) 이미 승격 상태에서 재호출 → stale PENDING 청소·멱등
  6) 조건 미충족(부서 0) → no-op
  7) ★T10(DCE-3): CEO_TEMPLATE 이 MASTER_DIRECTIVE 상위집합이 아니면(스텁 주입) 승격 보류 —
     무교체·PENDING 유지·loud (반쪽마스터 재발 차단 — 스왑 직전 런타임 검사)
  8) ★MF-1(P3 수정 라운드): 교차버전 형상(팩 업데이트 md=v2·낡은 .pre-ceo=v1) — OR-포함
     (ceo ⊇ md)로 승격 통과·.pre-ceo 무접촉 / 스텁은 여전히 보류(차단 강도 불변)
  8′) ★R3-CEO-2: 기승격 기계의 **실제** 업그레이드 후 3파일 형상(md=구 CEO 사본·.pre-ceo=구
     표준·ceo=신 CEO·.new=vendor 신 표준) — `.new` ref 로 통과(영구 보류 루프 소멸) /
     같은 형상의 스텁은 3-ref 전부 미포함이라 여전히 보류
  9) ★SF-1: 오너 지명(consented) 경로의 superset 보류는 PENDING 신규 생성 금지
     (지명 1회성 실패가 상시 자동승격 예약으로 확폭되는 것 차단 — 기존 PENDING 유지는 7c)
 10) ★SF-2: CRLF 개행 드리프트만으로 false hold 금지(정규화 후 포함 판정=통과)
(ceo_demote의 PENDING 청소는 down 경로 통합시험 영역 — 본 파일은 승격 축만.)

★픽스처 계약(T10): CEO 템플릿은 합성 계약(gen_ceo_template: 머리글+구분선+MASTER 전문 verbatim
연접)과 동형으로 **MASTER 본문을 포함**해야 승격이 통과한다 — 종전 무관 문자열("CEO-TEMPLATE")
픽스처는 DCE-3 검사에 걸리므로 상위집합 형태(CEO_BODY ⊇ MASTER_BODY)로 갱신(핀 약화 아님 —
승격 시 교체 단언은 동일하게 유지·검사 대상만 실계약 동형화).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SELF = os.path.dirname(os.path.abspath(__file__))
DEPT = os.path.join(SELF, "..", "cys-dept")
MASTER_BODY = "STANDARD-MASTER\n"
# 합성 계약 구분선(scripts/gen_ceo_template.py SEPARATOR 와 같은 바이트 · 시험 13 이 cys-dept 사본과 대조)
SEP = "\n---\n\n# [본문 — 표준 MASTER 운영 계약 전문]\n\n"
CEO_BODY = "CEO-HEADER" + SEP + MASTER_BODY   # 상위집합(합성 계약 동형: 머리글+구분선+전문)
fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))
    if not cond:
        fails.append(name)


def setup(tmp, ndepts=1):
    home = os.path.join(tmp, "home")
    pack = os.path.join(home, ".cys", "pack", "directives")
    bindir = os.path.join(home, ".local", "bin")  # cys-dept PATH prepend 1순위
    os.makedirs(pack, exist_ok=True)
    os.makedirs(bindir, exist_ok=True)
    with open(os.path.join(pack, "MASTER_DIRECTIVE.md"), "w", encoding="utf-8") as f:
        f.write(MASTER_BODY)
    with open(os.path.join(pack, "CEO_TEMPLATE.md"), "w", encoding="utf-8") as f:
        f.write(CEO_BODY)
    reg = os.path.join(home, ".cys", "depts.json")
    with open(reg, "w", encoding="utf-8") as f:
        json.dump({"depts": {("d%d" % i): {} for i in range(ndepts)}}, f)
    # 스텁 cys: feed push=승인(exit 0)·status=실패(reinject skip 경로)·전 호출 기록
    stub = os.path.join(bindir, "cys")
    with open(stub, "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/sh\necho \"cys $@\" >> \"%s/calls.log\"\n"
                "case \"$1\" in status) exit 1;; esac\nexit 0\n" % tmp)
    os.chmod(stub, 0o755)
    env = dict(os.environ)
    env.update({"HOME": home, "CYS_DEPTS_JSON": reg,
                "PATH": bindir + os.pathsep + env.get("PATH", "")})
    # ★좌석 env 누출 차단(v116-ceo-directive-hold 실측 2026-09-24): 좌석 셸에서 돌리면 CYS_CYS_BIN 이
    #   남아 cys-dept 가 스텁 대신 **설치본 cys** 를 부르고(cys-dept:35 1순위), 그 cys 가 가짜 HOME 에
    #   데몬을 띄워 고아 cysd 가 남았다. CYS_* 전부 제거 + 자동 기동 금지.
    for k in [k for k in env if k.startswith("CYS_")]:
        env.pop(k, None)
    env["CYS_NO_AUTOSTART"] = "1"
    return env, home


def run(env, *args, role=None):
    e = dict(env)
    if role:
        e["CYS_ROLE"] = role
    r = subprocess.run(["bash", DEPT] + list(args), capture_output=True, text=True,
                       encoding="utf-8", env=e, timeout=60)
    return r.returncode, r.stdout + r.stderr


def paths(home):
    d = os.path.join(home, ".cys", "pack", "directives", "MASTER_DIRECTIVE.md")
    return (d, d + ".pre-ceo",
            os.path.join(home, ".cys", "state", "ceo-pending"),
            os.path.join(home, ".cys", ".master-bootstrapped"))


def md(home):
    return open(paths(home)[0], encoding="utf-8").read()


# ── 1. 마커 無 → PENDING·무교체 (실사고 R2 봉쇄) ──
tmp = tempfile.mkdtemp(prefix="ceo-t1-")
env, home = setup(tmp)
code, out = run(env, "promote-ceo")
mdp, pre, pend, marker = paths(home)
check("1a 승격 시도 truthful exit 5(미승격 오보 차단·D-2 post-verify)", code == 5,
      "exit=%d %s" % (code, out[-150:]))
check("1b PENDING 기록", os.path.exists(pend))
check("1c 디렉티브 무교체", md(home) == MASTER_BODY)
check("1d .pre-ceo 미생성", not os.path.exists(pre))
check("1e fail-visible(feed 알림)", "feed push" in open(os.path.join(tmp, "calls.log"), encoding="utf-8").read())

# ── 2. 마커 생성 → promote-if-pending(대기형) → 자동 승격·PENDING 해소 ──
with open(marker, "w", encoding="utf-8") as f:
    json.dump({"orchestra_check": "exit 0"}, f)
code, out = run(env, "promote-if-pending")
check("2a 대기형 exit 0", code == 0, out[-150:])
check("2b 승격됨(CEO 템플릿)", md(home) == CEO_BODY)
check("2c .pre-ceo 보존 헌법", os.path.exists(pre) and open(pre, encoding="utf-8").read() == MASTER_BODY)
check("2d PENDING 해소", not os.path.exists(pend))
calls = open(os.path.join(tmp, "calls.log"), encoding="utf-8").read()
# ★자동 승격 정책 전환(2026-07·v4 A14 재정의): 종전 feed --wait 동의 게이트는 소스에서 폐지 —
#   현행 계약 = PENDING(부트 마커) 게이트가 유일 관문(1a~1d에서 핀)이고, 승격 자체는 자동이며
#   완료를 **비대기** feed로 고지한다. --wait 동의 대기는 어디에도 없어야 한다(정책 역회귀 핀).
check("2e 자동 승격 고지(비대기 feed·--wait 동의 게이트 폐지)",
      "feed push --title CEO 승격 완료(자동)" in calls and "--wait" not in calls,
      calls[-200:])

# ── 5. 이미 승격 + stale PENDING → 재호출이 청소·멱등 ──
with open(pend, "w", encoding="utf-8") as f:
    f.write("stale\n")
code, out = run(env, "promote-ceo")
check("5a 멱등 exit 0", code == 0)
check("5b stale PENDING 청소", not os.path.exists(pend))
check("5c 디렉티브 불변", md(home) == CEO_BODY)
shutil.rmtree(tmp)

# ── 3. --request-only: 무변조·알림만 (부트 ⑦ 계약) ──
tmp = tempfile.mkdtemp(prefix="ceo-t3-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
run(env, "promote-ceo")                     # PENDING 상태 만들기(마커 無)
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
code, out = run(env, "promote-if-pending", "--request-only", role="master")
check("3a request-only exit 0(master 세션 허용)", code == 0, out[-150:])
check("3b 무변조(디렉티브 표준 유지)", md(home) == MASTER_BODY)
check("3c PENDING 유지(해소는 대기형/lifecycle)", os.path.exists(pend))
calls = open(os.path.join(tmp, "calls.log"), encoding="utf-8").read()
check("3d 비대기(--wait 없는 알림)", "CEO 승격 대기" in out or "feed push --title CEO 승격 대기" in calls)

# ── 4. 단일소유 가드: master 대기형=차단 / CSO·role-less=허용 ──
code, out = run(env, "promote-if-pending", role="master")
check("4a master 대기형 exit 7", code == 7, "exit=%d" % code)
check("4b 차단 시 무변조", md(home) == MASTER_BODY)
code, out = run(env, "promote-if-pending", role="cso")
check("4c cso 대기형 허용·승격", code == 0 and md(home) == CEO_BODY)
shutil.rmtree(tmp)

# ── 6. 조건 미충족(부서 0·마커 有) → no-op ──
tmp = tempfile.mkdtemp(prefix="ceo-t6-")
env, home = setup(tmp, ndepts=0)
mdp, pre, pend, marker = paths(home)
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
os.makedirs(os.path.dirname(pend), exist_ok=True)
with open(pend, "w", encoding="utf-8") as f:
    f.write("pending\n")
code, out = run(env, "promote-if-pending")
check("6a 부서 0 no-op", code == 0 and "no-op" in out)
check("6b 무교체", md(home) == MASTER_BODY)
shutil.rmtree(tmp)

# ── 7. ★T10(DCE-3): 스텁 템플릿 주입 → 승격 보류(무교체·PENDING 유지·loud) ──
# 반쪽마스터 실사고 재현: CEO_TEMPLATE 이 MASTER 전문을 포함하지 않는 스텁으로 배포/회귀된
# 상태에서 승격 조건 3중이 전부 충족돼도 스왑 직전 상위집합 런타임 검사가 승격을 보류한다.
tmp = tempfile.mkdtemp(prefix="ceo-t7-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
with open(os.path.join(home, ".cys", "pack", "directives", "CEO_TEMPLATE.md"),
          "w", encoding="utf-8") as f:
    f.write("CEO-STUB\n")                       # MASTER_BODY 미포함 = 상위집합 아님
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
os.makedirs(os.path.dirname(pend), exist_ok=True)
with open(pend, "w", encoding="utf-8") as f:
    f.write("pending\n")
code, out = run(env, "promote-if-pending")      # 대기형(role-less) — 조건 3중 전부 충족
check("7a 대기형 exit 0(lifecycle 불파괴)", code == 0, "exit=%d %s" % (code, out[-200:]))
check("7b 무교체(표준 디렉티브 유지 — 스텁 replace 차단)", md(home) == MASTER_BODY)
check("7c PENDING 유지(보류)", os.path.exists(pend))
check("7d .pre-ceo 미생성(스왑 자체 미실행)", not os.path.exists(pre))
check("7e 영수증 미기록", not os.path.exists(
    os.path.join(home, ".cys", "pack", "directives", ".ceo-template-applied")))
check("7f loud(상위집합 보류 stderr)", "상위집합" in out and "보류" in out, out[-250:])
calls = open(os.path.join(tmp, "calls.log"), encoding="utf-8").read()
check("7g 보류 feed 고지(비대기)", "CEO 승격 보류(템플릿 상위집합 검사 실패)" in calls,
      calls[-200:])
# 지명(promote-ceo) 경로도 같은 보류 — D-2 post-verify 가 truthful exit 5 를 낸다.
code, out = run(env, "promote-ceo")
check("7h 지명 경로 truthful exit 5(승격 미완 보고)", code == 5, "exit=%d" % code)
check("7i 지명 경로도 무교체", md(home) == MASTER_BODY)
shutil.rmtree(tmp)

# ── 8. ★MF-1(P3 수정 라운드): 교차버전 형상 — md=v2·낡은 .pre-ceo=v1 → OR-포함으로 승격 통과 ──
# 반쪽마스터 실사고의 수복 자기봉쇄 재현: 팩 업데이트가 md 를 새 표준(v2)으로 갱신했고 .pre-ceo 엔
# 구 표준(v1)이 잔존. 종전 단일 ref 결박(.pre-ceo 존재=무조건 .pre-ceo 기준)이면 정상 v2 템플릿도
# CEO(v2) ⊉ .pre-ceo(v1) 로 영구 보류됐다 — OR-포함(ceo ⊇ md)이 이 형상만 해소한다.
tmp = tempfile.mkdtemp(prefix="ceo-t8-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
V2_BODY = "STANDARD-MASTER-V2\n"
CEO_V2 = "CEO-HEADER" + SEP + V2_BODY
_dirs = os.path.join(home, ".cys", "pack", "directives")
with open(mdp, "w", encoding="utf-8") as f:
    f.write(V2_BODY)                                # 팩 업데이트: md=새 표준 v2
with open(pre, "w", encoding="utf-8") as f:
    f.write(MASTER_BODY)                            # 낡은 백업: .pre-ceo=구 표준 v1
with open(os.path.join(_dirs, "CEO_TEMPLATE.md"), "w", encoding="utf-8") as f:
    f.write(CEO_V2)                                 # 정상 템플릿(v2 합성)
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
os.makedirs(os.path.dirname(pend), exist_ok=True)
with open(pend, "w", encoding="utf-8") as f:
    f.write("pending\n")
code, out = run(env, "promote-if-pending")
check("8a 교차버전 승격 통과(OR-포함: ceo ⊇ md)", code == 0 and md(home) == CEO_V2,
      "exit=%d md=%r %s" % (code, md(home)[:40], out[-200:]))
# ★v116-ceo-directive-hold(master 판정 ⑶ 2026-09-24): 옛 기대 「낡은 .pre-ceo 무접촉」은 결함을 의도로
#   박은 것이었다(md 가 현행 표준 원본인데 옛 백업이 남으면 강등이 옛 판을 되살림 — 1098 실측). 새 기대 =
#   md(현행 표준 v2)가 새 백업이 되고 옛 백업(v1)은 지우지 않고 .stale- 로 보존.
_st8 = [n for n in os.listdir(_dirs) if n.startswith("MASTER_DIRECTIVE.md.pre-ceo.stale-")]
check("8b 낡은 .pre-ceo → 현행 표준(md)이 새 백업 · 옛 백업은 .stale- 로 보존",
      open(pre, encoding="utf-8").read() == V2_BODY and len(_st8) == 1
      and open(os.path.join(_dirs, _st8[0]), encoding="utf-8").read() == MASTER_BODY,
      "pre=%r stale=%r" % (open(pre, encoding="utf-8").read()[:30], _st8))
check("8c PENDING 해소", not os.path.exists(pend))
# 차단 강도 불변: 같은 교차버전 형상에서 스텁은 md·.pre-ceo 둘 다 미포함 = 여전히 보류.
with open(mdp, "w", encoding="utf-8") as f:
    f.write(V2_BODY)
with open(os.path.join(_dirs, "CEO_TEMPLATE.md"), "w", encoding="utf-8") as f:
    f.write("CEO-STUB\n")
with open(pend, "w", encoding="utf-8") as f:
    f.write("pending\n")
code, out = run(env, "promote-if-pending")
check("8d 스텁은 여전히 보류(차단 강도 불변)",
      code == 0 and md(home) == V2_BODY and os.path.exists(pend),
      "exit=%d %s" % (code, out[-200:]))
shutil.rmtree(tmp)

# ── 8′. ★R3-CEO-2: **기승격 기계의 업그레이드 후 3파일 형상** — md=구 CEO 사본 / .pre-ceo=구
#   표준 v1 / ceo=신 CEO(v2) / .new=vendor 신 표준 v2. `directives/*_DIRECTIVE.md` 는 pack.rs
#   ownership() 상 User 라 팩 갱신이 md 를 절대 덮지 않으므로(신본은 `.new` 병치만) MF-1 이
#   상정한 구제 형상(md=v2)은 실제 업데이트 경로에서 발생하지 않는다 — MASTER_DIRECTIVE 본문을
#   한 줄만 고쳐도 ceo⊇md·ceo⊇.pre-ceo 가 둘 다 거짓이 되어 전 기승격 함대가 rc 3 영구 보류 +
#   10분 틱 무한 재판정에 빠졌다. `.new` ref 추가가 이 형상만 해소한다(스텁 차단 강도 불변).
tmp = tempfile.mkdtemp(prefix="ceo-t8b-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
V2_BODY = "STANDARD-MASTER-V2\n"
CEO_V1 = "CEO-HEADER" + SEP + MASTER_BODY          # 승격 당시 적용된 구 CEO 템플릿
CEO_V2 = "CEO-HEADER" + SEP + V2_BODY              # 팩 갱신이 치유한 신 CEO 템플릿(System 등급)
_dirs = os.path.join(home, ".cys", "pack", "directives")
with open(mdp, "w", encoding="utf-8") as f:
    f.write(CEO_V1)                                 # md = 구 CEO 사본(User 소유 — 갱신 불가)
with open(pre, "w", encoding="utf-8") as f:
    f.write(MASTER_BODY)                            # .pre-ceo = 승격 시점 구 표준 v1
with open(os.path.join(_dirs, "CEO_TEMPLATE.md"), "w", encoding="utf-8") as f:
    f.write(CEO_V2)
with open(mdp + ".new", "w", encoding="utf-8") as f:
    f.write(V2_BODY)                                # vendor 신본 병치(pack.rs new_pending)
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
os.makedirs(os.path.dirname(pend), exist_ok=True)
with open(pend, "w", encoding="utf-8") as f:
    f.write("pending\n")
code, out = run(env, "promote-if-pending")
check("8′a 기승격+팩업데이트 3파일 형상 통과(ref=.new)", code == 0 and md(home) == CEO_V2,
      "exit=%d md=%r %s" % (code, md(home)[:40], out[-300:]))
check("8′b 낡은 .pre-ceo 무접촉", open(pre, encoding="utf-8").read() == MASTER_BODY)
check("8′c PENDING 해소(영구 보류 루프 소멸)", not os.path.exists(pend))
# 차단 강도 불변: 같은 3파일 형상에서 스텁 템플릿은 md·.new·.pre-ceo 셋 다 미포함 = 보류.
with open(mdp, "w", encoding="utf-8") as f:
    f.write(CEO_V1)
with open(os.path.join(_dirs, "CEO_TEMPLATE.md"), "w", encoding="utf-8") as f:
    f.write("CEO-STUB\n")
with open(pend, "w", encoding="utf-8") as f:
    f.write("pending\n")
code, out = run(env, "promote-if-pending")
check("8′d 3-ref 전부 미포함 스텁은 여전히 보류(차단 강도 불변)",
      code == 0 and md(home) == CEO_V1 and os.path.exists(pend),
      "exit=%d %s" % (code, out[-200:]))
check("8′e 보류 문안이 교차버전 갈래를 안내(.new 언급)", ".new" in out, out[-300:])
shutil.rmtree(tmp)

# ── 9. ★SF-1: 지명(consented) 경로의 superset 보류 = PENDING 신규 생성 금지 ──
# 계약 문면은 'PENDING 유지'다 — 오너 지명 1회성 경로의 보류가 상시 자동승격 예약(집행 틱이
# 템플릿 수리 후 무제스처 승격)을 '신설'하면 확폭이다. 기존 PENDING 유지는 7c 가 핀.
tmp = tempfile.mkdtemp(prefix="ceo-t9-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
with open(os.path.join(home, ".cys", "pack", "directives", "CEO_TEMPLATE.md"),
          "w", encoding="utf-8") as f:
    f.write("CEO-STUB\n")
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
code, out = run(env, "promote-ceo")                 # PENDING 부재 상태에서 지명 → 보류
check("9a 지명 보류 truthful exit 5", code == 5, "exit=%d" % code)
check("9b PENDING 신규 생성 금지(자동승격 예약 확폭 차단)", not os.path.exists(pend))
check("9c 무교체", md(home) == MASTER_BODY)
shutil.rmtree(tmp)

# ── 10. ★SF-2: CRLF 개행 드리프트 = false hold 아님(정규화 후 포함 판정) ──
tmp = tempfile.mkdtemp(prefix="ceo-t10-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
CEO_CRLF = "CEO-HEADER\r\n---\r\n" + MASTER_BODY.replace("\n", "\r\n")
with open(os.path.join(home, ".cys", "pack", "directives", "CEO_TEMPLATE.md"),
          "w", encoding="utf-8", newline="") as f:
    f.write(CEO_CRLF)                               # Windows 체크아웃/에디터 변환 재현
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
os.makedirs(os.path.dirname(pend), exist_ok=True)
with open(pend, "w", encoding="utf-8") as f:
    f.write("pending\n")
code, out = run(env, "promote-if-pending")
_md_raw = open(mdp, "rb").read()
check("10a CRLF 드리프트 통과(정규화 후 ⊇ = 승격)",
      code == 0 and _md_raw == CEO_CRLF.encode("utf-8"),
      "exit=%d md=%r %s" % (code, _md_raw[:40], out[-200:]))
check("10b PENDING 해소", not os.path.exists(pend))
shutil.rmtree(tmp)

# ── 11. ★v116-ceo-directive-hold 경로 2(1098 교회 부서 시범 실측): **미승격** 기계에 옛 승격의
#   낡은 .pre-ceo 가 남음(md = 현행 표준 · 영수증 없음). 종전: 승격이 현행 md 를 백업하지 않고
#   (`[ -f .pre-ceo ] || cp`) 자동 승격 알림도 끈 채(`_auto` = .pre-ceo 부재 조건) 교체 → 부서를 다
#   닫으면 강등이 **옛 판을 되살린다**(격리 재현 scratch/repro2.sh). 기대: 승격 직전 현행 md 가 새
#   백업이 되고 옛 백업은 지우지 않고 `.pre-ceo.stale-*` 로 보존 · 강등 뒤 md = 현행 표준.
#   (8b 는 같은 형상의 종전 동작 「.pre-ceo 무접촉」을 고정한다 — 이 시험과 동시에 초록일 수 없다.)
tmp = tempfile.mkdtemp(prefix="ceo-t11-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
OLD_STD = "STANDARD-MASTER-OLD\n"                   # 옛 판 표준(1098 = v0.14.27 발행본)
with open(pre, "w", encoding="utf-8") as f:
    f.write(OLD_STD)
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
code, out = run(env, "promote-ceo")
_dirs = os.path.join(home, ".cys", "pack", "directives")
_stale = [n for n in os.listdir(_dirs) if n.startswith("MASTER_DIRECTIVE.md.pre-ceo.stale-")]
check("11a 승격 통과", code == 0 and md(home) == CEO_BODY, "exit=%d %s" % (code, out[-200:]))
check("11b 승격 직전 현행 md 가 새 백업(.pre-ceo)이 된다",
      open(pre, encoding="utf-8").read() == MASTER_BODY, repr(open(pre, encoding="utf-8").read()[:40]))
check("11c 옛 백업은 지우지 않고 .stale- 로 보존",
      len(_stale) == 1 and open(os.path.join(_dirs, _stale[0]), encoding="utf-8").read() == OLD_STD,
      repr(_stale))
code, out = run(env, "down", "d0")
check("11d 부서 0개 → 강등 = 현행 표준 복귀(옛 판 부활 금지)",
      md(home) == MASTER_BODY, "exit=%d md=%r %s" % (code, md(home)[:40], out[-200:]))
shutil.rmtree(tmp)

# ── 11g. ★자동 승격 알림 복구(뮤턴트 B5 생존 보강): 낡은 백업 형상에서 대기형 자동 승격(promote-if-pending
#   = 부서 생성·10분 틱 경로)은 「CEO 승격 완료(자동)」 알림을 내야 한다 — 종전엔 `.pre-ceo` 존재만으로
#   _auto=0 이라 사용자가 역할 교체를 통지받지 못했다(1098 R3).
tmp = tempfile.mkdtemp(prefix="ceo-t11g-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
with open(pre, "w", encoding="utf-8") as f:
    f.write("STANDARD-MASTER-OLD\n")
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
os.makedirs(os.path.dirname(pend), exist_ok=True)
with open(pend, "w", encoding="utf-8") as f:
    f.write("pending\n")
code, out = run(env, "promote-if-pending")
_calls = open(os.path.join(tmp, "calls.log"), encoding="utf-8").read() if os.path.exists(os.path.join(tmp, "calls.log")) else ""
check("11g 낡은 백업 형상의 자동 승격 = 「CEO 승격 완료(자동)」 알림",
      code == 0 and md(home) == CEO_BODY and "CEO 승격 완료(자동)" in _calls,
      "exit=%d calls=%r" % (code, _calls[-200:]))
shutil.rmtree(tmp)

# ── 11h. ★보존본 중복 금지·임시 파일 정리(Opus 적대 F3·F7 · 뮤턴트 B7 보강): md 교체(rename)가 계속 실패하는
#   기계(윈 파일 잠금 등 — 맥은 chflags uchg 로 재현)에서 10분 틱이 돌 때마다 「덮기 전 보존본」이 하나씩
#   쌓이거나 md.tmp.* 가 남으면 안 된다. 맥 전용(chflags) — 다른 OS 는 건너뜀.
if sys.platform == "darwin":
    tmp = tempfile.mkdtemp(prefix="ceo-t11h-")
    env, home = setup(tmp)
    mdp, pre, pend, marker = paths(home)
    _dirs = os.path.dirname(mdp)
    with open(pre, "w", encoding="utf-8") as f:
        f.write(MASTER_BODY)
    with open(mdp, "w", encoding="utf-8") as f:
        f.write(CEO_BODY + "MY-NOTE\n")            # 손본 CEO 사본(영수증 없음 → 덮기 전 보존 대상)
    with open(marker, "w", encoding="utf-8") as f:
        f.write("{}")
    subprocess.run(["chflags", "uchg", mdp], check=True)
    try:
        for _ in range(3):
            run(env, "promote-ceo")
        _eb = [n for n in os.listdir(_dirs) if n.startswith("MASTER_DIRECTIVE.md.pre-ceo-")]
        _tm = [n for n in os.listdir(_dirs) if ".tmp" in n]
        check("11h 교체 실패 3회 — 보존본 1개 · 임시 파일 0", len(_eb) == 1 and not _tm, "backups=%r tmp=%r" % (_eb, _tm))
    finally:
        subprocess.run(["chflags", "nouchg", mdp], check=False)
    shutil.rmtree(tmp)
else:
    check("11h (건너뜀: chflags 없는 OS)", True)

# ── 11e. ★가드(agy B R1 반례 ①): **승격 중** 사용자가 CEO 사본을 손봐 표지 핀까지 지움 → 두 번째
#   부서(재승격). md 가 「현행 표준 원본」이라는 긍정 증거(CEO ⊇ md)가 없으므로 .pre-ceo(진짜 표준
#   백업)는 무접촉이어야 한다 — 낡은 백업으로 오판해 밀어내면 강등이 손수정 사본을 복원한다.
tmp = tempfile.mkdtemp(prefix="ceo-t11e-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
with open(pre, "w", encoding="utf-8") as f:
    f.write(MASTER_BODY)                            # 승격 때 만든 진짜 표준 백업
with open(mdp, "w", encoding="utf-8") as f:
    f.write("CEO-HEADER-EDITED-BY-OWNER\n---\n" + MASTER_BODY + "MY-NOTE\n")  # 손수정 CEO 사본(핀 없음)
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
code, out = run(env, "promote-ceo")
_dirs = os.path.join(home, ".cys", "pack", "directives")
check("11e 손수정 CEO 사본 재승격 — 진짜 표준 백업 무접촉 · .stale- 0개",
      open(pre, encoding="utf-8").read() == MASTER_BODY
      and not [n for n in os.listdir(_dirs) if ".pre-ceo.stale-" in n],
      "exit=%d pre=%r %s" % (code, open(pre, encoding="utf-8").read()[:30], out[-200:]))
shutil.rmtree(tmp)

# ── 11f. ★가드(agy B R1 반례 ③): 락을 못 잡은 경로(윈 PortableGit = flock 없음 + mkdir 락 선점)는
#   무락으로 _swap 을 강행한다(종전 결함). 그 창에서 .pre-ceo 를 옮기면 동시 승격이 백업을 서로
#   덮으므로 낡은 백업 처리(새 동작)는 **락 보유 시에만** — 무락이면 종전 동작(백업 무접촉).
tmp = tempfile.mkdtemp(prefix="ceo-t11f-")
env, home = setup(tmp)
mdp, pre, pend, marker = paths(home)
with open(pre, "w", encoding="utf-8") as f:
    f.write(OLD_STD)
with open(marker, "w", encoding="utf-8") as f:
    f.write("{}")
os.makedirs(mdp + ".promote.lock.d")                 # 다른 승격이 락을 쥔 상태
env_nf = dict(env)
env_nf["PATH"] = os.path.join(home, ".local", "bin") + os.pathsep + "/usr/bin:/bin"  # flock 없는 PATH
_has_flock = subprocess.run(["bash", "-c", "command -v flock"], env=env_nf,
                            capture_output=True).returncode == 0
if _has_flock:
    check("11f (건너뜀: 이 기계 /usr/bin·/bin 에 flock 이 있어 mkdir 락 경로 재현 불가)", True)
else:
    code, out = run(env_nf, "promote-ceo")
    _dirs = os.path.join(home, ".cys", "pack", "directives")
    check("11f 무락 강행 경로 — 낡은 백업 처리 생략(백업 무접촉 · .stale- 0개)",
          open(pre, encoding="utf-8").read() == OLD_STD
          and not [n for n in os.listdir(_dirs) if ".pre-ceo.stale-" in n],
          "exit=%d %s" % (code, out[-200:]))
shutil.rmtree(tmp)

# ── 12. ★v116-ceo-directive-hold(master 판정 ⑴): 형상 표 한 파일(fixtures/ceo_directive_shapes.json)을
#   Rust 설치기 시험(src/pack.rs ceo_directive_shapes_installer)과 **같이 읽는다** — 「제품이 쓴 파일인가」
#   판정이 두 곳(설치기 = 해시 집합 · cys-dept = 표준 원본 긍정 증거)에 있으므로, 한쪽만 고치면 다른 쪽이 적색.
import hashlib
with open(os.path.join(SELF, "fixtures", "ceo_directive_shapes.json"), encoding="utf-8") as f:
    SHAPES = json.load(f)
_T = SHAPES["texts"]
_tx = lambda k: None if k is None else _T[k]
_ran12 = 0
for s in SHAPES["shapes"]:
    exp = s.get("dept")
    if not exp:
        continue
    sid = s["id"]
    tmp = tempfile.mkdtemp(prefix="ceo-t12-")
    env, home = setup(tmp)
    mdp, pre, pend, marker = paths(home)
    _dirs = os.path.dirname(mdp)
    for pth, val in ((mdp, _tx(s["md"])), (pre, _tx(s["pre_ceo"])), (mdp + ".new", _tx(s["new"]))):
        if val is not None:
            with open(pth, "w", encoding="utf-8", newline="") as f:
                f.write(val)
    _md_bytes = None
    if s.get("md_encoding"):
        _md_bytes = _T[s["md"]].encode(s["md_encoding"], errors="replace")
        with open(mdp, "wb") as f:
            f.write(_md_bytes)
    if s["receipt"] is not None:
        with open(os.path.join(_dirs, ".ceo-template-applied"), "w", encoding="utf-8") as f:
            f.write(hashlib.sha256(_T[s["receipt"]].encode("utf-8")).hexdigest() + "\n")
    with open(os.path.join(_dirs, "CEO_TEMPLATE.md"), "w", encoding="utf-8", newline="") as f:
        f.write(_T["C2"])
    if exp.get("boot_marker", True):
        with open(marker, "w", encoding="utf-8") as f:
            f.write("{}")
    _rd = lambda p: open(p, encoding="utf-8", errors="replace", newline="").read() if os.path.exists(p) else None  # 줄끝 무변환(CRLF) · 비UTF-8(CP949) 도 판정 가능
    _bak = lambda kind: sorted(n for n in os.listdir(_dirs) if n.startswith("MASTER_DIRECTIVE.md" + kind))
    for rnd in (() if exp.get("skip_promote") else ("1회", "2회(멱등)")):
        code, out = run(env, "promote-ceo")
        stale, edit = _bak(".pre-ceo.stale-"), _bak(".pre-ceo-")
        check("12 [%s · %s] md" % (sid, rnd), _rd(mdp) == _tx(exp["expect_md"]),
              "exit=%d md=%r %s" % (code, (_rd(mdp) or "")[:40], out[-160:]))
        check("12 [%s · %s] .pre-ceo" % (sid, rnd), _rd(pre) == _tx(exp["expect_pre_ceo"]),
              repr((_rd(pre) or "")[:40]))
        want_stale = [] if exp["expect_stale"] is None else [_T[exp["expect_stale"]]]
        check("12 [%s · %s] .pre-ceo.stale-*" % (sid, rnd),
              [_rd(os.path.join(_dirs, n)) for n in stale] == want_stale, repr(stale))
        want_edit = [] if exp["expect_edit_backup"] is None else [_T[exp["expect_edit_backup"]]]
        check("12 [%s · %s] 덮기 전 보존(.pre-ceo-<시각>)" % (sid, rnd),
              [_rd(os.path.join(_dirs, n)) for n in edit] == want_edit, repr(edit))
    if exp.get("expect_after_down"):
        code, out = run(env, "down", "d0")
        check("12 [%s] 부서 0개 강등 뒤 md" % sid, _rd(mdp) == _T[exp["expect_after_down"]],
              "exit=%d md=%r %s" % (code, (_rd(mdp) or "")[:40], out[-160:]))
        if "expect_edit_backup_after_down" in exp:
            _eb = [open(os.path.join(_dirs, n), "rb").read() for n in _bak(".pre-ceo-")]
            _want = exp["expect_edit_backup_after_down"]
            _wb = _md_bytes if _want == "__MD_BYTES__" else _T[_want].encode("utf-8")
            check("12 [%s] 강등 덮기 전 보존(.pre-ceo-<시각>)" % sid, _eb == [_wb], "n=%d" % len(_eb))
        if "expect_stale_after_down" in exp:
            _sd = [_rd(os.path.join(_dirs, n)) for n in _bak(".pre-ceo.stale-")]
            check("12 [%s] 강등 뒤 .pre-ceo.stale-*" % sid, _sd == [_T[k] for k in exp["expect_stale_after_down"]], repr(_sd))
    shutil.rmtree(tmp)
    _ran12 += 1
check("12 형상 표 dept 칸 13개 이상 실행", _ran12 >= 13, "ran=%d" % _ran12)

# ── 13. 구분선 계약: cys-dept 가 판정에 쓰는 구분선 = 합성기(gen_ceo_template.SEPARATOR) 바이트.
#   합성기 구분선이 바뀌면 cys-dept ⓕ·강등의 「구분선 뒤 본문 == md」 판정이 조용히 전부 거짓이 된다.
sys.path.insert(0, os.path.join(SELF, "..", "..", "..", "scripts"))
try:
    import gen_ceo_template as _g
    _sep_src = _g.SEPARATOR.decode("utf-8")
    _dept_src = open(DEPT, encoding="utf-8").read()
    _esc = _sep_src.encode("unicode_escape").decode("ascii")
    check("13 cys-dept 구분선 = gen_ceo_template.SEPARATOR", SEP == _sep_src and _esc in _dept_src,
          "esc=%r" % _esc)
except ImportError:
    check("13 (건너뜀: 팩 설치본에서 실행 — scripts/ 없음)", True)

# ── 13b. 강등 표지 계약(Opus 적대 R2 N1): cys-dept 강등 판정의 ASCII 표지 'master of master' 는 CEO_TEMPLATE 에는
#   있고 표준 MASTER_DIRECTIVE 에는 없어야 한다 — 표준본에 들어가면 미승격 기계를 승격 사본으로 오인해 강등이
#   옛 백업을 덮어쓴다.
_dd = os.path.join(SELF, "..", "..", "directives")
_mt = open(os.path.join(_dd, "MASTER_DIRECTIVE.md"), encoding="utf-8").read()
_ct = open(os.path.join(_dd, "CEO_TEMPLATE.md"), encoding="utf-8").read()
check("13b 강등 표지 'master of master' = CEO 에만(표준 MASTER 0회)",
      "master of master" not in _mt and "master of master" in _ct)

print("\n%d FAIL" % len(fails) if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
