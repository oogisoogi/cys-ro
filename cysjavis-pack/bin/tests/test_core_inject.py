#!/usr/bin/env python3
"""test_core_inject.py — master 요지 주입(injection-slim T2·T2a·T5) 회귀 하네스 (standalone).

무엇을 고정하나(DESIGN-v2.1 §4-1·§4-3·§4-4·§4-6·§7 · master 판정 5cdfbd54):
  A  master 정상: 훅 ① 출력 맨 앞 = CORE-MIN · ≤9,000자 · CORE 나머지·부트 브리지·목차 실재 · soul·색인 부재
  B  CEO 좌석(MASTER_DIRECTIVE = CEO 템플릿): CEO_CORE 로 요지 · CORE-MIN 맨 앞
  C  절 해시 불일치: 낡은 요지 미배포 + 원문 절 직접 주입 + 교체 고지
  D  CORE 부재(치명 ③ 자가치유): CORE-MIN.md 로 맨 앞 · 부트 브리지 생존 · 원문 절 · ≤9,000자
  E  최악 조합 드라이런(soul 4,068자 · 색인·오버레이 최대 · source=compact · 역할 재대조 고지):
     두 훅 절단 후 ≤9,000자 · 뒤 블록부터 빠짐 · 싣지 않은 블록 이름 고지 · CORE-MIN 맨 앞
  F  fail-open: 조립기 사망 → 셸 폴백(CORE-MIN·부트 브리지) · rc 0
  G  5초 상한(치명 ④): 조립기가 멈추면 5초 안팎에 폴백 · rc 0
  H  배경층 역할 가드: master 외 0바이트 · startup 이면 §11·§9·soul 미주입
  P  preflight C82 판정 코어: 정상 팩 PASS · 격리 증명(가짜 cys 호출)
실행:  python3 cysjavis-pack/bin/tests/test_core_inject.py [--mutants] [--table]
  --mutants  뮤턴트 배터리(사본 팩에 변이 → 지정 검사가 적색인지 · 변이 적용 먼저 단언)
  --table    E 의 드라이런 표를 마크다운으로 출력
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

SELF = os.path.dirname(os.path.abspath(__file__))
REPO_PACK = os.path.normpath(os.path.join(SELF, "..", ".."))
fails = []
TABLE = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))
    if not cond:
        fails.append(name)
    return cond


def ulen(s):
    return len(s) + sum(1 for c in s if ord(c) > 0xFFFF)


def make_pack(tmp, src=REPO_PACK, ceo=False, bootstrap=True):
    """사본 팩: hooks 전부 · directives 필요분 · bin(preflight·bootstrap 스텁) · soul · memory."""
    pack = os.path.join(tmp, "pack")
    shutil.copytree(os.path.join(src, "hooks"), os.path.join(pack, "hooks"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(os.path.join(pack, "directives"))
    for n in ("MASTER_CORE.md", "CEO_CORE.md", "CORE-MIN.md", "WORKER_DIRECTIVE.md", "CSO_DIRECTIVE.md"):
        shutil.copy(os.path.join(src, "directives", n), os.path.join(pack, "directives", n))
    md_src = "CEO_TEMPLATE.md" if ceo else "MASTER_DIRECTIVE.md"
    shutil.copy(os.path.join(src, "directives", md_src), os.path.join(pack, "directives", "MASTER_DIRECTIVE.md"))
    os.makedirs(os.path.join(pack, "bin"))
    shutil.copy(os.path.join(src, "bin", "javis_preflight.py"), os.path.join(pack, "bin", "javis_preflight.py"))
    if bootstrap:
        with open(os.path.join(pack, "bin", "javis_bootstrap.py"), "w", encoding="utf-8") as f:
            f.write("# stub\n")
    os.makedirs(os.path.join(pack, "memory"))
    with open(os.path.join(pack, "memory", "MEMORY.md"), "w", encoding="utf-8") as f:
        f.write("# MEMORY\n- [a](a.md) — 색인 한 줄\n")
    with open(os.path.join(pack, "soul.md"), "w", encoding="utf-8") as f:
        f.write("# soul\nSOUL-BODY-MARK\n")
    return pack


def env_for(tmp, pack, role="master", claim="ok", py=None):
    fb = os.path.join(tmp, "fakebin")
    os.makedirs(fb, exist_ok=True)
    body = {"ok": "exit 0", "dead": "echo 'connect error' >&2; exit 1"}[claim]
    with open(os.path.join(fb, "cys"), "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/sh\nprintf '%%s\\n' \"$*\" >> '%s/cys-calls.log'\ncase \"$1\" in claim-role) %s;; esac\nexit 0\n"
                % (tmp, body))
    os.chmod(os.path.join(fb, "cys"), 0o755)
    home = os.path.join(tmp, "home")
    os.makedirs(home, exist_ok=True)
    e = {k: v for k, v in os.environ.items() if not (k.startswith("CYS_") or k.startswith("CMUX_"))}
    e.update({"CYS_PACK_DIR": pack, "CYS_SURFACE_ID": "t-core", "HOME": home,
              "CYS_SOCKET": os.path.join(tmp, "absent.sock"),
              "PATH": fb + os.pathsep + os.environ.get("PATH", "")})
    if role:
        e["CYS_ROLE"] = role
    if py:
        e["CYS_PY"] = py
    return e


def run(pack, hook, env, source="startup", timeout=40):
    t0 = time.time()
    r = subprocess.run(["sh", os.path.join(pack, "hooks", hook)],
                       input=json.dumps({"hook_event_name": "SessionStart", "source": source}) + "\n",
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=timeout)
    return r.returncode, r.stdout, r.stderr, time.time() - t0


def core_min(pack):
    return open(os.path.join(pack, "directives", "CORE-MIN.md"), encoding="utf-8").read()


def load_pf(pack):
    spec = importlib.util.spec_from_file_location("pf_%d" % id(pack), os.path.join(pack, "bin", "javis_preflight.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def worst_home(tmp):
    """오버레이·색인 최대(캡의 수 배) — 홈 쪽 오버레이만 여기(색인·soul 은 팩 쪽)."""
    home = os.path.join(tmp, "home")
    od = os.path.join(home, ".cys", "local", "directives")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "MASTER_DIRECTIVE.local.md"), "w", encoding="utf-8") as f:
        f.write("".join("오버레이 규칙 %04d — 사용자 확장 지침 한 줄 가나다라마바사\n" % i for i in range(900)))
    return home


def worst_pack_files(pack):
    with open(os.path.join(pack, "soul.md"), "w", encoding="utf-8") as f:
        body = "# soul\n" + "".join("소울 헌장 문장 %03d — 박사님 정체·가치·문체 규율 서술\n" % i for i in range(200))
        f.write(body[:4068])   # 이 기계 soul = 4,068자(DESIGN-v2.1 §4-4)
    with open(os.path.join(pack, "memory", "MEMORY.md"), "w", encoding="utf-8") as f:
        f.write("# MEMORY\n" + "".join("- [m%04d](m%04d.md) — 장기기억 색인 한 줄 설명 가나다라\n" % (i, i) for i in range(1500)))


# ── 시나리오(각 함수는 pack 을 받아 적색이면 False) ────────────────────────────────
def t_A(pack, tmp):
    rc, out, _e, _t = run(pack, "session-start.sh", env_for(tmp, pack))
    ok = check("A1 master rc 0", rc == 0)
    ok &= check("A2 맨 앞 = CORE-MIN", out.startswith(core_min(pack)))
    ok &= check("A3 ≤9,000자", ulen(out) <= 9000, "%d자" % ulen(out))
    ok &= check("A4 CORE 나머지·부트 브리지·목차 실재",
                "■ MASTER CORE — 나머지 요지" in out and "부트 브리지" in out and "■ 원문 절 목차" in out)
    ok &= check("A5 soul·색인 미주입(배경층 몫)", "SOUL-BODY-MARK" not in out and "장기메모리 색인" not in out)
    ok &= check("A6 자기 절단 없음(전형)", "자기 절단" not in out)
    return ok


def t_B(pack, tmp):
    rc, out, _e, _t = run(pack, "session-start.sh", env_for(tmp, pack))
    ok = check("B1 CEO rc 0 · CORE-MIN 맨 앞", rc == 0 and out.startswith(core_min(pack)))
    ok &= check("B2 CEO 요지 실재", "■ CEO CORE" in out and "좌석=CEO" in out, out[-300:])
    ok &= check("B3 ≤9,000자", ulen(out) <= 9000, "%d자" % ulen(out))
    return ok


def t_C(pack, tmp):
    p = os.path.join(pack, "directives", "MASTER_DIRECTIVE.md")
    t = open(p, encoding="utf-8").read()
    old, new = "수기 티켓 위임은 금지다", "수기 티켓 위임은 금지이다"
    if not check("C0 변이 적용(원문 §2 한 글자)", t.count(old) == 1):
        return False
    open(p, "w", encoding="utf-8").write(t.replace(old, new))
    rc, out, _e, _t = run(pack, "session-start.sh", env_for(tmp, pack))
    ok = check("C1 교체 고지", "요지가 원문과 어긋나" in out and "§2" in out)
    ok &= check("C2 낡은 요지 미배포", "■ MASTER CORE — 나머지 요지" not in out)
    ok &= check("C3 원문 §2 직접 주입(변경분 포함)", new in out and "■ 원문 §2" in out)
    ok &= check("C4 CORE-MIN 맨 앞·≤9,000·rc 0", out.startswith(core_min(pack)) and ulen(out) <= 9000 and rc == 0)
    return ok


def t_D(pack, tmp):
    for n in ("MASTER_CORE.md", "CEO_CORE.md"):
        os.remove(os.path.join(pack, "directives", n))
    rc, out, _e, _t = run(pack, "session-start.sh", env_for(tmp, pack))
    ok = check("D1 CORE 부재: CORE-MIN.md 로 맨 앞", out.startswith(core_min(pack)))
    # 부재 모드는 부트 브리지·목차가 원문보다 앞이다 — 원문 절은 남은 자리를 채우는 최선 노력(SKIP)이라
    #   큰 절(§0-C 6,086자)은 건너뛰고 들어가는 절만 싣는다. 무엇을 뺐는지는 절단 고지가 이름으로 말한다.
    ok &= check("D2 부재 고지·원문 절 ≥1·건너뛴 절 이름 고지",
                "CORE 요지 파일(MASTER_CORE.md)이 없거나" in out and "■ 원문 §" in out
                and "자기 절단" in out and "원문 §0-C" in out.split("■ 자기 절단:", 1)[-1])
    ok &= check("D3 부트 브리지 생존(자가치유)", "부트 브리지" in out and "javis_bootstrap.py" in out)
    ok &= check("D4 ≤9,000자·rc 0", ulen(out) <= 9000 and rc == 0, "%d자" % ulen(out))
    return ok


def t_E(pack, tmp):
    worst_pack_files(pack)
    home = worst_home(tmp)
    ok = True
    for src in ("startup", "compact"):
        env = env_for(tmp, pack, claim="dead")
        env["HOME"] = home
        rc1, o1, _e, _t = run(pack, "session-start.sh", env, source=src)
        rc2, o2, _e, _t = run(pack, "inject-background.sh", env, source=src)
        n1, n2 = ulen(o1), ulen(o2)
        cut2 = o2.split("■ 자기 절단:", 1)[1].split("\n", 1)[0] if "■ 자기 절단:" in o2 else "(없음)"
        TABLE.append((src, n1, "재대조 고지" if "역할 재확인 불가" in o1 else "-", n2, cut2.strip()))
        ok &= check("E1 %s 훅① ≤9,000 · CORE-MIN 맨 앞 · 재대조 고지는 CORE-MIN 뒤" % src,
                    n1 <= 9000 and o1.startswith(core_min(pack)) and o1.index("역할 재확인 불가") > len(core_min(pack)),
                    "%d자" % n1)
        ok &= check("E2 %s 훅②' ≤9,000(절단 후)" % src, n2 <= 9000, "%d자" % n2)
        ok &= check("E3 %s rc 0 둘 다" % src, rc1 == 0 and rc2 == 0)
    # compact: 우선순위(§11 → §9 → soul → 색인 → 오버레이)대로 뒤에서부터 빠지고 이름이 고지된다
    ok &= check("E4 compact 앞 블록 생존(§11·§9)", "■ 원문 §11" in o2 and "■ 원문 §9" in o2)
    ok &= check("E5 compact 절단 고지에 오버레이 이름", "자기 절단" in o2 and "로컬 오버레이" in cut2, cut2)
    ok &= check("E6 뒤 블록부터 빠짐(오버레이 본문 미주입)", "오버레이 규칙 0000" not in o2)
    return ok


def t_F(pack, tmp):
    with open(os.path.join(pack, "hooks", "core_inject.py"), "w", encoding="utf-8") as f:
        f.write("raise SystemExit(3)\n")
    rc, out, err, _t = run(pack, "session-start.sh", env_for(tmp, pack))
    ok = check("F1 조립기 사망 → rc 0", rc == 0)
    ok &= check("F2 폴백 = CORE-MIN 맨 앞 + 부트 브리지", out.startswith(core_min(pack)) and "부트 브리지" in out)
    ok &= check("F3 stderr 1줄 고지", "요지 조립기 실패" in err)
    return ok


def t_G(pack, tmp):
    real = shutil.which("python3")
    wrap = os.path.join(tmp, "slowpy")
    with open(wrap, "w", encoding="utf-8", newline="\n") as f:
        f.write('#!/bin/sh\ncase "$1" in *core_inject.py) sleep 30;; esac\nexec "%s" "$@"\n' % real)
    os.chmod(wrap, 0o755)
    rc, out, _e, dt = run(pack, "session-start.sh", env_for(tmp, pack, py=wrap))
    ok = check("G1 조립기 정지 → 5초 상한 후 폴백", rc == 0 and "부트 브리지" in out and dt < 15, "%.1fs" % dt)
    ok &= check("G2 폴백도 CORE-MIN 맨 앞", out.startswith(core_min(pack)))
    return ok


def t_H(pack, tmp):
    ok = True
    for role in ("worker", "cso", "reviewer-codex", None):
        rc, out, _e, _t = run(pack, "inject-background.sh", env_for(tmp, pack, role=role), source="compact")
        ok &= check("H1 배경층 역할 가드 %s → 0바이트" % role, rc == 0 and out == "")
    rc, out, _e, _t = run(pack, "inject-background.sh", env_for(tmp, pack), source="startup")
    ok &= check("H2 startup: §11·§9·soul 미주입 · 색인 주입",
                "■ 원문 §11" not in out and "SOUL-BODY-MARK" not in out and "장기메모리 색인" in out)
    rc, out, _e, _t = run(pack, "inject-background.sh", env_for(tmp, pack), source="clear")
    ok &= check("H3 clear: §11 → §9 → soul 순서",
                0 <= out.find("■ 원문 §11") < out.find("■ 원문 §9") < out.find("SOUL-BODY-MARK"))
    return ok


def t_P(pack, tmp):
    pf = load_pf(pack)
    probs, notes = pf.core_injection_problems(pack, home=os.path.join(tmp, "home"))
    ok = check("P1 정상 팩 C82 문제 0", not probs, str(probs))
    ok &= check("P2 격리 증명 기록", any("가짜 cys 호출 확인" in n for n in notes), str(notes))
    return ok


def t_P_worst(pack, tmp):
    worst_pack_files(pack)
    pf = load_pf(pack)
    probs, notes = pf.core_injection_problems(pack, home=worst_home(tmp))
    return check("P3 최악 조합 팩 C82 문제 0(절단 후 상한 준수)", not probs, str(probs))


SCEN = {"A": (t_A, {}), "B": (t_B, {"ceo": True}), "C": (t_C, {}), "D": (t_D, {}), "E": (t_E, {}),
        "F": (t_F, {}), "G": (t_G, {}), "H": (t_H, {}), "P": (t_P, {}), "Pw": (t_P_worst, {})}


def scenario(key, mutate=None):
    fn, kw = SCEN[key]
    tmp = tempfile.mkdtemp(prefix="core-%s-" % key)
    try:
        pack = make_pack(tmp, **kw)
        if mutate:
            mutate(pack)
        return fn(pack, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 뮤턴트: (이름, 파일, 찾을 문자열, 바꿀 문자열, 적색이어야 할 시나리오) ─────────────
MUTANTS = [
    ("CORE 삭제(MASTER_CORE.md 제거) → C82", "directives/MASTER_CORE.md", None, None, "P"),
    ("해시 변조(머리 주석 §7 1자) → C82", "directives/MASTER_CORE.md",
     "§7=f399e48e162da7e0", "§7=f399e48e162da7e1", "P"),
    ("해시 변조 → 훅이 낡은 요지를 싣지 않는다(A 적색)", "directives/MASTER_CORE.md",
     "§7=f399e48e162da7e0", "§7=f399e48e162da7e1", "A"),
    ("크기 초과(조립 상한 8800→20000) → 최악 드라이런", "hooks/core_inject.py",
     "LIMIT = 8800\n", "LIMIT = 20000\n", "E"),
    ("크기 초과(조립 상한 8800→20000) → C82 최악 팩", "hooks/core_inject.py",
     "LIMIT = 8800\n", "LIMIT = 20000\n", "Pw"),
    ("순서 뒤집기(CORE-MIN 을 출처 고지 뒤로) → A", "hooks/core_inject.py",
     '    blocks.append(("CORE-MIN", core_min or "", True))\n    blocks.append(("출처 고지", "■ 출처: cys 팩 훅 hooks/session-start.sh · 정본 = %s(충돌하면 정본이 이긴다)" % d_path, False))\n',
     '    blocks.append(("출처 고지", "■ 출처: cys 팩 훅 hooks/session-start.sh · 정본 = %s(충돌하면 정본이 이긴다)" % d_path, False))\n    blocks.append(("CORE-MIN", core_min or "", True))\n', "A"),
    ("순서 뒤집기 → C82 맨 앞 축", "hooks/core_inject.py",
     '    blocks.append(("CORE-MIN", core_min or "", True))\n    blocks.append(("출처 고지", "■ 출처: cys 팩 훅 hooks/session-start.sh · 정본 = %s(충돌하면 정본이 이긴다)" % d_path, False))\n',
     '    blocks.append(("출처 고지", "■ 출처: cys 팩 훅 hooks/session-start.sh · 정본 = %s(충돌하면 정본이 이긴다)" % d_path, False))\n    blocks.append(("CORE-MIN", core_min or "", True))\n', "P"),
    ("CORE-MIN 보호 해제(True→False) → 최악 드라이런 E1", "hooks/core_inject.py",
     '    blocks.append(("CORE-MIN", core_min or "", True))\n', '    blocks.append(("CORE-MIN", "", True))\n', "E"),
    ("SKIP 의미 제거(원문 절이 뒤를 끌고 나감) → D 부트 브리지", "hooks/core_inject.py",
     "        if protected == SKIP and ulen(t) <= limit:\n            dropped.append(name)\n            continue\n",
     "", "D"),
    ("해시 대조 무력화(verify 항상 ok) → C", "hooks/core_inject.py",
     "    return (not mism, mism, n)\n", "    return (True, [], n)\n", "C"),
    ("배경층 역할 가드 제거 → H", "hooks/inject-background.sh",
     '[ "${CYS_ROLE:-}" = "master" ] || exit 0\n', "", "H"),
    ("배경층 우선순위 뒤집기(soul 을 §11 앞) → H3", "hooks/core_inject.py",
     "    if src in SOUL_SOURCES and a.soul and os.path.isfile(a.soul):\n",
     "    if False:\n", "H"),
    ("셸 폴백 제거(조립기 실패 시 무출력) → F", "hooks/session-start.sh",
     '  echo "[cys-hook] 요지 조립기 실패(rc=$CI_RC) — CORE-MIN·부트 브리지 폴백(session-start)" >&2\n',
     '  exit 0\n', "F"),
    ("5초 상한 제거(cys_timeout_run 5 → 60) → G", "hooks/session-start.sh",
     "cys_timeout_run 5 \"$CYS_PY\" \"$(cys_native_path \"$CI\")\" session",
     "cys_timeout_run 60 \"$CYS_PY\" \"$(cys_native_path \"$CI\")\" session", "G"),
    # ── 귀속(attribution) 뮤턴트 — 이름이 「귀속」으로 시작: 합성 변이로 적색을 만든 뒤 그 축만 끄면
    #   **초록으로 돌아가야** 한다(= 적색의 원인이 그 축이었다 · 같은 뮤테이션 두 그물 규율). 초록 = ATTRIBUTED.
    ("귀속 C82 크기 축(9000→10**9) × 조립 상한 해제 → Pw 초록이어야", "bin/javis_preflight.py",
     "CORE_INJECT_HARD = 9000 ", "CORE_INJECT_HARD = 10**9 ", "Pw"),
    ("C82 이름 규칙 축: 금지 이름 CORE 파일 추가 → P", "directives/MASTER_CORE_DIRECTIVE.md", "@ADD", None, "P"),
    ("귀속 C82 해시 축(ok 무시) × 머리 해시 변조 → P 초록이어야", "bin/javis_preflight.py",
     "        if not ok:\n            probs.append", "        if False:\n            probs.append", "P"),
]


def apply_mut(pack, rel, old, new, extra=None):
    p = os.path.join(pack, rel)
    if old is None:
        os.remove(p)
        assert not os.path.exists(p), "변이 미적용(삭제)"
        return
    if old == "@ADD":
        shutil.copy(os.path.join(pack, "directives", "MASTER_CORE.md"), p)
        assert os.path.exists(p)
        return
    t = open(p, encoding="utf-8").read()
    assert t.count(old) == 1, "변이 대상 %d건(1건이어야 함): %r" % (t.count(old), old[:60])
    open(p, "w", encoding="utf-8").write(t.replace(old, new))
    assert open(p, encoding="utf-8").read() != t, "변이 미적용"


def run_mutants():
    global fails
    killed, bad = 0, []
    # 전제: 변이 전 각 대상 시나리오가 초록이어야 KILLED 가 의미를 가진다(변이 전부터 빨간 검체 배제).
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
            if name.startswith("귀속 C82 해시 축"):   # 해시 변조와 합성 — 그 적색을 잡는 축이 해시 축뿐인가
                apply_mut(pack, "directives/MASTER_CORE.md", "§7=f399e48e162da7e0", "§7=f399e48e162da7e1")
            if name.startswith("귀속 C82 크기 축"):   # 조립 상한 해제와 합성 — 그 적색을 잡는 축이 크기 축뿐인가
                apply_mut(pack, "hooks/core_inject.py", "LIMIT = 8800\n", "LIMIT = 20000\n")
        try:
            green = scenario(target, mutate=mut)
        except AssertionError as e:
            fails = saved
            bad.append("%s (NOT-APPLIED: %s)" % (name, e))
            print("NOT-APPLIED %s — %s" % (name, e))
            continue
        fails = saved
        if name.startswith("귀속"):
            if green:
                killed += 1
                print("ATTRIBUTED %s" % name)
            else:
                bad.append(name + " (축을 꺼도 적색 — 다른 축이 잡거나 축이 공허)")
                print("UNATTRIBUTED %s" % name)
        elif green:
            bad.append(name)
            print("SURVIVED %s" % name)
        else:
            killed += 1
            print("KILLED   %s" % name)
    print("\nMUTANTS killed=%d / %d" % (killed, len(MUTANTS)))
    return bad


if __name__ == "__main__":
    for k in ("A", "B", "C", "D", "E", "F", "G", "H", "P", "Pw"):
        scenario(k)
    if "--table" in sys.argv:
        print("\n| source | 훅① 글자 | 훅① 고지 | 훅②' 글자 | 훅②' 자기 절단 고지 |\n|---|---:|---|---:|---|")
        for row in TABLE:
            print("| %s | %d | %s | %d | %s |" % row)
    mbad = run_mutants() if "--mutants" in sys.argv else []
    if fails or mbad:
        print("\nFAIL %s %s" % (fails, mbad))
        sys.exit(1)
    print("\nALL PASS")
