#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_preflight_win_hook_launcher.py — git-bash 없는 Windows 의 셸 훅 안전 강등 (win-hooks-no-bash).

무엇을 막는가: 깨끗한 Windows(git-bash 없음)에서 preflight 가 훅을 `bash "<pack>/hooks/x.sh"` 로
등록했다. Claude Code 는 bash 를 못 찾으면 훅을 PowerShell 로 띄우고, 매 턴 훅마다 「bash 인식 불가」
오류가 사용자 화면에 찍히며 셸 훅 전부가 죽었다(샌드박스 실증 2026-09-16).

  A. nt + PATH 에 bash → 등록 문자열이 종전 `bash "<정슬래시>"` 와 **바이트 동일**
  B. nt + bash 어디에도 없음 → C08·C28·C33 이 셸 훅을 **0건 등록**, 기존 우리 훅은 --fix 에서 제거
     (사용자 훅 보존), 각 행에 강등 고지 1줄
  C. nt + PATH 에 없고 알려진 위치에 실재 → 그 절대경로로 등록(후보 순서·따옴표 규칙)
  M. 뮤턴트 3(게이트 제거 · 폴백 제거 · 고지 제거) — 각각 위 축 중 하나 이상이 적색이어야 한다
출력: PASS/FAIL 행 · 실패 시 exit 1 · 종료 토큰 PREFLIGHT-WIN-HOOK-LAUNCHER-OK.
실행 규약(CI 동형): CYS_PACK_DIR="$(mktemp -d)" python3 bin/tests/test_preflight_win_hook_launcher.py
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile

SELF = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(SELF)
PF_PATH = os.path.join(BIN, "javis_preflight.py")
fails = []
NOTE_HEAD = "bash 없음 → 셸 훅 "


def check(name, cond, detail="", sink=None):
    if sink is None:
        print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))
        if not cond:
            fails.append(name)
    elif not cond:
        sink.append(name)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@contextlib.contextmanager
def windows_like(PF, pack, home, cfg, which=None, localappdata=None, program_files=None, isfile=None):
    """os.name=nt 흉내 + env 격리. os.path 는 이미 posixpath 로 묶여 있어 경로 연산은 그대로다."""
    keys = ("CYS_PACK_DIR", "HOME", "CLAUDE_CONFIG_DIR", "CYS_ACCOUNT_DIR", "LOCALAPPDATA", "ProgramFiles")
    prev_env = {k: os.environ.get(k) for k in keys}
    prev_name, prev_which, prev_isfile = os.name, PF.shutil.which, os.path.isfile
    # ★임시 팩 가드 치환(run_bootstrap_health `_temp_guard_double` 과 같은 기법): 이 검체의
    #   샌드박스는 그 자체가 /var/folders 아래라 실 가드가 **모든** 팩을 임시 팩으로 보고 등록을
    #   금지한다 — 그러면 등록·제거 축을 아예 못 잰다. 가드 논리는 버리지 않고 판정 입력만
    #   마커로 바꾸고, 실 함수의 타당성(진짜 tmp 를 임시로 본다)은 여기서 1회 단언한다.
    prev_guard = PF._path_under_tempdir
    assert prev_guard(tempfile.gettempdir()) is True, "계측 타당성 실패: 실 임시 팩 가드가 tmp 를 임시로 안 본다"
    PF._path_under_tempdir = lambda path: "/__mark_temp_pack__" in (path or "")
    os.environ.update({"CYS_PACK_DIR": pack, "HOME": home, "CLAUDE_CONFIG_DIR": cfg})
    os.environ.pop("CYS_ACCOUNT_DIR", None)
    for k, v in (("LOCALAPPDATA", localappdata), ("ProgramFiles", program_files)):
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    PF.shutil.which = lambda n, *a, **k: which if n == "bash" else prev_which(n, *a, **k)
    if isfile is not None:
        os.path.isfile = lambda p: isfile(p) if "bash.exe" in p else prev_isfile(p)
    os.name = "nt"
    try:
        yield
    finally:
        os.name = prev_name
        PF.shutil.which = prev_which
        os.path.isfile = prev_isfile
        PF._path_under_tempdir = prev_guard
        for k, v in prev_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def build_pack(PF, pack):
    for script, _ in PF.SELFCORR_HOOKS:
        p = os.path.join(pack, "hooks", script)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8").write("#!/bin/sh\nexit 0\n")
    for extra in ("session-start.sh", PF.Preflight.EVENT_HOOK):
        io.open(os.path.join(pack, "hooks", extra), "w", encoding="utf-8").write("#!/bin/sh\nexit 0\n")
    for rel, _o in PF.HOOK_BODY_FILES:
        io.open(os.path.join(pack, rel), "w", encoding="utf-8").write("#!/bin/bash\nexit 0\n")
    os.makedirs(os.path.join(pack, "bin"), exist_ok=True)
    io.open(os.path.join(pack, "bin", "javis_reflect.py"), "w", encoding="utf-8").write("#\n")


def run_axes(PF, root, sink=None):
    """세 축을 돌린다. sink 가 주어지면 출력 없이 실패 이름만 모은다(뮤턴트 판정용)."""
    # ★팩은 **기본 자리**(HOME/.cys/pack)여야 한다 — 임시 팩 컨텍스트는 등록이 금지돼
    #   (resolve_registration_targets sentinel) 등록·제거 축이 통째로 성립하지 않는다.
    home = os.path.join(root, "home")
    pack = os.path.join(home, ".cys", "pack")
    cfg = os.path.join(root, "cfg")
    for d in (home, cfg):
        os.makedirs(d, exist_ok=True)
    build_pack(PF, pack)
    ss = os.path.join(pack, "hooks", "session-start.sh")

    # ── A. bash 가 PATH 에 있으면 종전 문자열과 바이트 동일
    with windows_like(PF, pack, home, cfg, which="C:\\Git\\usr\\bin\\bash.exe"):
        got = PF._cys_hook_cmd("session-start.sh")
        sup = PF.shell_hooks_supported()
    check("A1 nt+bash → 종전 `bash \"<정슬래시>\"` 바이트 동일", got == 'bash "%s"' % ss.replace("\\", "/"),
          repr(got), sink)
    check("A2 nt+bash → 셸 훅 지원", sup is True, repr(sup), sink)

    # ── C. 폴백 경로(후보 순서 · 따옴표 규칙)
    la, pf = "C:\\Users\\user\\AppData\\Local", "C:\\Program Files"
    cands = PF._win_bash_candidates(la, pf)
    check("C1 후보 순서(cys 동봉 → ProgramFiles Git → Programs Git → PortableGit)",
          cands == [la + "\\cys\\runtime\\git\\bin\\bash.exe", pf + "\\Git\\bin\\bash.exe",
                    la + "\\Programs\\Git\\bin\\bash.exe", la + "\\PortableGit\\bin\\bash.exe"],
          repr(cands), sink)
    with windows_like(PF, pack, home, cfg, which=None, localappdata=la, program_files=pf,
                      isfile=lambda p: p == la + "\\cys\\runtime\\git\\bin\\bash.exe"):
        got_c = PF._cys_hook_cmd("session-start.sh")
        sup_c = PF.shell_hooks_supported()
    check("C2 동봉 PortableGit 실재 → 맨 절대경로 런처(공백 없음 = 따옴표 없음)",
          got_c == 'C:/Users/user/AppData/Local/cys/runtime/git/bin/bash.exe "%s"' % ss, repr(got_c), sink)
    check("C3 폴백 실재 → 셸 훅 지원", sup_c is True, repr(sup_c), sink)
    with windows_like(PF, pack, home, cfg, which=None, localappdata=la, program_files=pf,
                      isfile=lambda p: p.startswith(pf)):
        got_q = PF._cys_hook_cmd("session-start.sh")
    check("C4 공백 경로(Program Files) → 따옴표 런처",
          got_q == '"C:/Program Files/Git/bin/bash.exe" "%s"' % ss, repr(got_q), sink)

    # ── B. bash 어디에도 없음 → 0건 등록 · 기존 우리 훅 제거 · 사용자 훅 보존 · 고지 1줄
    settings = os.path.join(cfg, "settings.json")
    ours = 'bash "%s"' % ss
    user = {"hooks": [{"type": "command", "command": "sh ~/myhooks/session-start.sh"}]}
    io.open(settings, "w", encoding="utf-8").write(json.dumps({"hooks": {
        "SessionStart": [{"hooks": [{"type": "command", "command": ours}]}, user]}}))
    with windows_like(PF, pack, home, cfg, which=None, localappdata=os.path.join(root, "noLA"),
                      program_files=os.path.join(root, "noPF"), isfile=lambda p: False):
        sup_b = PF.shell_hooks_supported()
        pf_obj = PF.Preflight(True, [])
        pf_obj.c08_hook_registered()
        pf_obj.c28_self_correction()
        pf_obj.c33_event_hooks()
    check("B1 nt+bash 없음 → 셸 훅 미지원", sup_b is False, repr(sup_b), sink)
    data = json.load(io.open(settings, encoding="utf-8"))
    cmds = [h.get("command", "") for arr in (data.get("hooks") or {}).values()
            for e in arr for h in e.get("hooks", [])]
    pack_fwd = pack.replace("\\", "/") + "/hooks/"
    check("B2 우리 팩 .sh 훅 등록 0건(기존 bash 엔트리도 --fix 에서 제거)",
          not [c for c in cmds if pack_fwd in c], repr(cmds), sink)
    check("B3 사용자 동명 훅 보존(G10)", "sh ~/myhooks/session-start.sh" in cmds, repr(cmds), sink)
    rows = {r["id"]: r for r in pf_obj.results}
    for cid in ("C08.hook-registered", "C28.self-correction", "C33.event-hooks"):
        r = rows.get(cid) or {}
        det = r.get("detail", "")
        check("B4 %s = WARN(FAIL 아님) + 강등 고지 정확히 1줄" % cid,
              r.get("status") == PF.WARN and det.count(NOTE_HEAD) == 1,
              repr((r.get("status"), det[:160])), sink)
        # ★고지는 개수만 적으면 안 된다 — 사용자가 **무엇을 잃는지**(각성 두 이벤트) 말해야 한다.
        check("B5 %s 고지가 잃는 기능(각성 SessionStart·UserPromptSubmit)을 명시" % cid,
              all(t in det for t in ("각성", "SessionStart", "UserPromptSubmit")),
              repr(det[:200]), sink)


def check_note_parity(PF):
    """★고지 문장은 python·Rust 두 곳에 사본으로 산다 — 한쪽만 고치면 사용자가 경로에 따라 다른
    설명을 받는다. Rust 원본이 이 레인에 있으면(=레포 체크아웃) 대조를 켠다(npm_prefix 선례)."""
    rs = os.path.join(os.path.dirname(os.path.dirname(BIN)), "src", "pack.rs")
    if not os.path.isfile(rs):
        print("SKIP 고지 파리티 — Rust 원본 없음(팩 단독 배포 레인)")
        return
    src = io.open(rs, encoding="utf-8").read()
    i = src.find("pub fn shell_hooks_degraded_note")
    body = src[i:src.find("\n}", i)] if i != -1 else ""
    j, k = body.find('"'), body.rfind('"')
    lit = body[j + 1:k] if -1 < j < k else ""
    # Rust 문자열의 `\`+개행+들여쓰기 이음을 풀고 `{n}` 을 python 서식으로 환원한다.
    joined = re.sub(r"\\\s*\n\s*", "", lit).replace("{n}", "%d")
    check("P1 강등 고지 python ⇔ Rust 바이트 동일(드리프트 0)",
          joined == PF.SHELL_HOOK_DEGRADED_NOTE, repr((joined[:90], PF.SHELL_HOOK_DEGRADED_NOTE[:90])))


root = tempfile.mkdtemp()
try:
    PF = load(PF_PATH, "_pf_winhook_live")
    run_axes(PF, os.path.join(root, "live"))
    check_note_parity(PF)

    src = io.open(PF_PATH, encoding="utf-8").read()
    mutants = [
        ("M1 게이트 제거", '    return os.name != "nt" or _win_hook_launcher() is not None',
         "    return True"),
        ("M2 폴백 제거", "    for c in candidates:\n        if isfile(c):",
         "    for c in []:\n        if isfile(c):"),
        ("M3 고지 제거", "        note = SHELL_HOOK_DEGRADED_NOTE % (len(pairs) + extra)",
         '        note = "강등"'),
    ]
    for i, (name, old, new) in enumerate(mutants):
        check("%s — 앵커 정확히 1곳(변이 적용 확인)" % name, src.count(old) == 1, str(src.count(old)))
        if src.count(old) != 1:
            continue
        mp = os.path.join(root, "pf_mut%d.py" % i)
        io.open(mp, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
        io.open(mp, encoding="utf-8").read().count(new) >= 1 or fails.append(name + " 미적용")
        sink = []
        try:
            run_axes(load(mp, "_pf_winhook_mut%d" % i), os.path.join(root, "mut%d" % i), sink)
        except Exception as e:  # noqa: BLE001 — 변이가 크래시를 내도 적색(= 잡힘)
            sink.append("크래시 %s" % type(e).__name__)
        check("%s → 적색(KILLED)" % name, bool(sink), repr(sink[:3]))
finally:
    shutil.rmtree(root, ignore_errors=True)

if fails:
    print("\n%d FAIL: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("\nALL PASS")
print("PREFLIGHT-WIN-HOOK-LAUNCHER-OK")
sys.exit(0)
