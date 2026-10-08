#!/usr/bin/env python3
"""D14(1.1.8 · 윈 결함 보고 2026-10-05) — SESSION_STATE 정본 경로 단일 해소 회귀 잠금.

실측 결함: orchestra next-action·gate-status 는 `<pack>/round/SESSION_STATE.md`(설치 골격 · 10일 미갱신)를,
복원 주입 훅은 cwd 상향탐색 `<install-jarvis>/_round/SESSION_STATE.md`(master 가 실제로 쓰던 파일)를
보여 줘 큐 판정이 실제 큐와 무관하게 늘 「빈 큐」로 나왔다.

잠그는 것
  A  python 정본 함수(javis_session.session_state_path) — 키 순서·첫 값·HOME 폴백
  B  셸 쌍둥이(_lib.sh cys_session_state_path) 와 같은 값(여러 env 형상)
  C  orchestra·preflight(C61)·state_snapshot 이 같은 함수를 지난다
  D  옛 자리 이관 판정·집행(정본 골격일 때만 복사 · 백업 · 옛 파일 무접촉 · retire 는 개명)
  E  inject-context: lead(master) 좌석 = 정본 주입 + 옛 기록 이관 1줄 / member 좌석 = 종전(프로젝트 _round)
  F  save-state: lead 좌석의 .state_log 가 정본 round/ 에 쌓인다
  G  ★cso-round(1.1.8 재빌드 · 윈 실기 D-U1/D-U4): 정본 이관·주입은 master 좌석만 — CSO 는 자기 `<cwd>/_round`(1.1.7)를
     싣고 정본을 건드리지 않는다(두 좌석 이중 adopt 0) · 통지 문구 = 실제 동작(복사 · 옛 파일 그대로 · 손실 지시 0)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(HERE)
PACK_SRC = os.path.dirname(BIN)
HOOKS = os.path.join(PACK_SRC, "hooks")
sys.path.insert(0, BIN)
import javis_session as JS  # noqa: E402

BASH = shutil.which("bash") or "/bin/bash"
PY = sys.executable
fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + str(detail)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def shell_path(env):
    e = {"PATH": "/usr/bin:/bin"}
    e.update(env)
    r = subprocess.run([BASH, "-c", '. "$1" >/dev/null 2>&1; cys_session_state_path',
                        "_", os.path.join(HOOKS, "_lib.sh")],
                       capture_output=True, text=True, env=e, timeout=30)
    return r.stdout


def write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


SKEL = read(os.path.join(PACK_SRC, "round", "SESSION_STATE.md"))
REAL = "# SESSION_STATE.md — master 기록\n## 현재 위치\n- 진행 중 작업: 부서 개설\n## 다음 액션 큐\n1. 보고서 정리\n"


def main():
    root = tempfile.mkdtemp(prefix="ssc.", dir=os.environ.get("TMPDIR") or None)
    home = os.path.join(root, "home")
    os.makedirs(home)

    # ── A python 정본 함수 ──
    check("A1 CYS_PACK_DIR 첫 값", JS.session_state_path({"CYS_PACK_DIR": "/p1", "JAVIS_PACK_DIR": "/p2",
                                                          "HOME": home})
          == os.path.join("/p1", "round", "SESSION_STATE.md"))
    check("A2 앞 키가 비면 다음 키", JS.session_state_path({"CYS_PACK_DIR": "", "JAVIS_PACK_DIR": "/p2",
                                                         "HOME": home})
          == os.path.join("/p2", "round", "SESSION_STATE.md"))
    check("A3 키가 없으면 HOME/.cys/pack", JS.session_state_path({"HOME": home})
          == os.path.join(home, ".cys", "pack", "round", "SESSION_STATE.md"))
    check("A4 pack 명시가 env 보다 우선", JS.session_state_path({"CYS_PACK_DIR": "/p1"}, pack="/q")
          == os.path.join("/q", "round", "SESSION_STATE.md"))

    # ── B 셸 쌍둥이 ──
    for name, env in (("pack", {"CYS_PACK_DIR": "/p1", "HOME": home}),
                      ("2nd-key", {"AITERM_PACK_DIR": "/p3", "HOME": home}),
                      ("trailing-slash", {"CYS_PACK_DIR": "/p1/", "HOME": home}),
                      ("home", {"HOME": home})):
        want = os.path.normpath(JS.session_state_path(env))
        got = shell_path(env)
        check("B %s 셸 = python" % name, os.path.normpath(got) == want, "%r vs %r" % (got, want))

    # ── C 소비처가 같은 함수를 지난다 ──
    pack = os.path.join(root, "pack")
    os.makedirs(os.path.join(pack, "round"))
    env_keep = {k: os.environ.get(k) for k in JS.PACK_DIR_ENV_KEYS}
    try:
        for k in JS.PACK_DIR_ENV_KEYS:
            os.environ.pop(k, None)
        os.environ["CYS_PACK_DIR"] = pack
        import javis_orchestra as ORC
        check("C1 orchestra.session_state_path = 정본", ORC.session_state_path() == JS.session_state_path())
        src = read(os.path.join(BIN, "javis_orchestra.py"))
        check("C2 orchestra 에 손조립 SESSION_STATE 경로 0",
              'os.path.join(pack_dir(), "round", "SESSION_STATE.md")' not in src)
        pf = read(os.path.join(BIN, "javis_preflight.py"))
        check("C3 preflight C61 이 정본 함수를 쓴다",
              '"_round", "SESSION_STATE.md"' not in pf and "_jsess.session_state_path(pack=pack_dir())" in pf)
        import javis_state_snapshot as SS
        write(JS.session_state_path(), REAL)
        srcs = SS.default_sources(home=home, state_root=os.path.join(root, "st"),
                                  depts_json=os.path.join(root, "depts.json"), windows=False)
        check("C4 스냅샷 소스에 정본 포함", JS.session_state_path() in srcs, srcs[-6:])
    finally:
        for k, v in env_keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    # ── D 이관 판정·집행 ──
    d = os.path.join(root, "d")
    leg = os.path.join(d, "proj", "_round", "SESSION_STATE.md")
    canon = os.path.join(d, "pack", "round", "SESSION_STATE.md")
    write(leg, REAL)
    check("D1 정본 부재 → adopt", JS.adopt_plan(leg, canon)["action"] == "adopt")
    write(canon, SKEL)
    check("D2 정본 = 설치 골격 → adopt", JS.adopt_plan(leg, canon) == {"action": "adopt",
                                                                       "reason": "canonical-skeleton"})
    check("D3 설치 골격 판정", JS.is_skeleton(SKEL) and not JS.is_skeleton(REAL))
    r = JS.adopt(leg, canon, now=0)
    check("D4 집행: 정본 = 옛 내용", read(canon) == REAL)
    check("D5 집행: 골격 백업", os.path.isfile(r.get("backup", "")) and read(r["backup"]) == SKEL, r)
    check("D6 집행: 옛 파일 무접촉(retire 없음)", os.path.isfile(leg) and read(leg) == REAL and "moved" not in r)
    check("D7 내용 같음 → same", JS.adopt_plan(leg, canon)["action"] == "same")
    r2 = JS.adopt(leg, canon, retire=True, now=0)
    check("D8 retire: 옛 파일 개명(삭제 0)", not os.path.exists(leg)
          and os.path.isfile(r2.get("moved", "")) and read(r2["moved"]) == REAL, r2)
    write(leg, REAL + "- 다른 기록\n")
    write(canon, REAL + "- 정본 기록\n")
    check("D9 정본에 기록 있음 → keep(사람 판단)", JS.adopt_plan(leg, canon) == {"action": "keep",
                                                                              "reason": "canonical-written"})
    before = read(canon)
    JS.adopt(leg, canon, retire=True)
    check("D10 keep 은 아무것도 쓰지 않는다", read(canon) == before and os.path.isfile(leg))
    check("D11 legacy_candidates = cwd 상향 첫 _round",
          JS.legacy_candidates(os.path.join(d, "proj", "sub")) == [leg])

    # ── E inject-context ──
    def fixture(tag):
        base = os.path.join(root, tag)
        pk = os.path.join(base, "pack")
        os.makedirs(os.path.join(pk, "bin"))
        shutil.copy2(os.path.join(BIN, "javis_session.py"), os.path.join(pk, "bin", "javis_session.py"))
        write(os.path.join(pk, "round", "SESSION_STATE.md"), SKEL)
        work = os.path.join(base, "install-jarvis")
        write(os.path.join(work, "_round", "SESSION_STATE.md"), REAL)
        h = os.path.join(base, "home")
        os.makedirs(h)
        return base, pk, work, h

    def run_hook(hook, base, pk, work, h, role, payload=None):
        env = {"PATH": "/usr/bin:/bin", "HOME": h, "CYS_PACK_DIR": pk, "CYS_ROOT": h,
               "TMPDIR": base, "CYS_ROLE": role, "CYS_SURFACE_ID": "7", "CYS_PY": PY,
               "LANG": "C.UTF-8"}
        payload = payload or json.dumps({"source": "startup", "cwd": work})
        return subprocess.run([BASH, os.path.join(HOOKS, hook)], input=payload, capture_output=True,
                              text=True, encoding="utf-8", env=env, timeout=120)

    base, pk, work, h = fixture("e-lead")
    r = run_hook("inject-context.sh", base, pk, work, h, "master")
    out = r.stdout
    canon_e = os.path.join(pk, "round", "SESSION_STATE.md")
    check("E1 lead 출처 = 정본", ("출처: %s" % canon_e) in out, out[-1500:])
    check("E2 lead 옛 자리 이관 1줄", "작업기억 이관(D14)" in out, out[-1500:])
    check("E3 이관 뒤 정본 = 옛 기록", read(canon_e) == REAL)
    check("E4 옛 파일 무접촉", read(os.path.join(work, "_round", "SESSION_STATE.md")) == REAL)
    check("E5 lead 에 「현재 폴더에 _round 만들 것」 안내 0", "_round/SESSION_STATE.md를 먼저 만들 것" not in out)

    base, pk, work, h = fixture("e-member")
    r = run_hook("inject-context.sh", base, pk, work, h, "worker")
    out = r.stdout
    check("E6 member 는 종전(프로젝트 _round)", ("출처: %s" % os.path.join(work, "_round", "SESSION_STATE.md"))
          in out, out[-1500:])
    check("E7 member 는 정본을 건드리지 않는다", read(os.path.join(pk, "round", "SESSION_STATE.md")) == SKEL)

    base, pk, work, h = fixture("e-nocanon")
    os.remove(os.path.join(pk, "round", "SESSION_STATE.md"))
    os.remove(os.path.join(work, "_round", "SESSION_STATE.md"))
    r = run_hook("inject-context.sh", base, pk, work, h, "master")
    check("E8 lead 정본 부재 = 정본 경로를 알려 준다",
          "정본 %s 없음" % os.path.join(pk, "round", "SESSION_STATE.md") in r.stdout, r.stdout[-800:])

    # ── F save-state ──
    base, pk, work, h = fixture("f-lead")
    r = run_hook("save-state.sh", base, pk, work, h, "master",
                 json.dumps({"cwd": work, "hook_event_name": "Stop"}))
    check("F1 lead .state_log = 정본 round/", os.path.isfile(os.path.join(pk, "round", ".state_log"))
          and not os.path.exists(os.path.join(work, "_round", ".state_log")), r.stderr[-400:])
    base, pk, work, h = fixture("f-member")
    run_hook("save-state.sh", base, pk, work, h, "worker", json.dumps({"cwd": work, "hook_event_name": "Stop"}))
    check("F2 member .state_log = 종전 자리", os.path.isfile(os.path.join(work, "_round", ".state_log")))

    # ── G cso-round ──
    CSO_REAL = "# SESSION_STATE\n- CSO 누적 기록(감시 로그 9508B 대역)\n"
    for role in ("cso", "cso-2"):
        base, pk, work, h = fixture("g-" + role)
        cso_cwd = os.path.join(work, "cso")
        write(os.path.join(cso_cwd, "_round", "SESSION_STATE.md"), CSO_REAL)
        r = run_hook("inject-context.sh", base, pk, cso_cwd, h, role,
                     json.dumps({"source": "startup", "cwd": cso_cwd}))
        out = r.stdout
        check("G1 %s 출처 = 자기 <cwd>/_round(1.1.7)" % role,
              ("출처: %s" % os.path.join(cso_cwd, "_round", "SESSION_STATE.md")) in out, out[-1500:])
        check("G2 %s 는 이관하지 않는다(통지 0)" % role, "작업기억 이관" not in out and "옛 위치" not in out, out[-1500:])
        check("G3 %s 는 정본을 건드리지 않는다" % role, read(os.path.join(pk, "round", "SESSION_STATE.md")) == SKEL)
    # 두 좌석 순서(master 먼저 → CSO): 정본 = master 기록 그대로 · CSO 는 자기 파일
    base, pk, work, h = fixture("g-two")
    cso_cwd = os.path.join(work, "cso")
    write(os.path.join(cso_cwd, "_round", "SESSION_STATE.md"), CSO_REAL)
    run_hook("inject-context.sh", base, pk, work, h, "master")
    r = run_hook("inject-context.sh", base, pk, cso_cwd, h, "cso", json.dumps({"source": "startup", "cwd": cso_cwd}))
    canon_g = os.path.join(pk, "round", "SESSION_STATE.md")
    check("G4 두 좌석: 정본 = master 이관분 그대로(CSO 가 덮지 않음)", read(canon_g) == REAL)
    check("G5 두 좌석: CSO 파일 무접촉", read(os.path.join(cso_cwd, "_round", "SESSION_STATE.md")) == CSO_REAL)
    check("G6 두 좌석: 정본 백업 1개(이중 adopt 0)",
          len([n for n in os.listdir(os.path.dirname(canon_g)) if n.startswith("SESSION_STATE.md.bak-")]) == 1)
    # save-state: CSO 는 자기 <cwd>/_round
    base, pk, work, h = fixture("g-save")
    cso_cwd = os.path.join(work, "cso")
    write(os.path.join(cso_cwd, "_round", "SESSION_STATE.md"), CSO_REAL)
    run_hook("save-state.sh", base, pk, cso_cwd, h, "cso", json.dumps({"cwd": cso_cwd, "hook_event_name": "Stop"}))
    check("G7 CSO .state_log = 자기 <cwd>/_round(정본 round/ 0)",
          os.path.isfile(os.path.join(cso_cwd, "_round", ".state_log"))
          and not os.path.exists(os.path.join(pk, "round", ".state_log")))
    # 통지 문구 = 실제 동작
    ad = JS.say_line({"action": "adopt", "legacy": "/L", "canonical": "/C", "backup": "/C.bak-1", "bytes": 123})
    kp = JS.say_line({"action": "keep", "reason": "canonical-written", "legacy": "/L", "canonical": "/C"})
    check("G8 adopt 통지 = 복사 · 바이트 · 백업 이름 · 옛 파일 그대로",
          "복사했다" in ad and "123바이트" in ad and "/C.bak-1" in ad and "옮겼다" not in ad and "그대로" in ad, ad)
    check("G9 keep 통지 = 손실 지시 0(정리·「아무도 읽지 않는다」 없음 · 덮어쓰기·삭제 금지 명시)",
          "정리하라" not in kp and "아무도 읽지 않는다" not in kp and "지우지 마라" in kp and "덮어쓰거나" in kp, kp)
    r = JS.adopt(os.path.join(root, "d", "proj", "_round", "SESSION_STATE.md"), os.path.join(root, "g-b", "C.md"), now=0)
    check("G10 adopt 결과에 실제 복사 바이트", r.get("bytes") == len(read(os.path.join(root, "g-b", "C.md")).encode("utf-8")), r)

    shutil.rmtree(root, ignore_errors=True)
    print("\n=== %s ===" % ("ALL PASS" if not fails else "FAIL %d: %s" % (len(fails), fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
