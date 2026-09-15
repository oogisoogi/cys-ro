#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_seat_folders.py — TICKET=cys-seat-folders 회귀 핀 (standalone · exit 0=PASS · 1=FAIL).

S1 좌석 폴더 생성·cwd 실측 — 편성 경로(`javis_formation._role_seat_cwd`)가 master 좌석 폴더 아래
   cso/·workers/wN/ 을 **실제로 만들고** 그 경로를 자식 cwd 로 돌려준다(master 는 대상 아님).
S2 얇은 CLAUDE.md 시드 — 없을 때만 만들고 역할·디렉티브를 채운다 · 기존 파일은 덮지 않는다.
S3 폴더 신뢰 시드 — 부재 키만 채운다 · 다른 키·기존 false 보존 · 설정 파일이 없으면 만들지
   않는다 · 실사용 프로필(~/.cys/claude)에 이 시험의 경로가 한 줄도 들어가지 않는다.
S4 git 저장소가 된 좌석 폴더에서도 신뢰 창 0 — 실 claude 를 격리 프로필로 띄워 화면을 읽는다.
   대조군: 시드 없이 git init 한 형제 좌석 폴더는 신뢰 창이 **뜬다**(상속이 git 루트에서 끊긴다는
   실측 = 시드가 필요하다는 근거이자 이 시험의 공허 통과 차단). claude 부재면 SKIP(측정 불능 명시).
S5 기계유래 스폰 억제 폐지 — machine-origin=machine 선언도 부트를 띄우고, 부트 자식 env 에
   선언 유래 마커(CYS_DECL_ORIGIN)가 **없다**(상속값도 지운다). human 선언은 hook-human.
"""
import importlib.util
import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time

TESTS = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(TESTS)
PACK = os.path.dirname(BIN)
REAL_CFG = os.path.join(os.path.expanduser("~"), ".cys", "claude", ".claude.json")

fails = []
notes = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, "" if cond else " — " + detail))
    if not cond:
        fails.append(name)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _real_cfg_mentions(needle):
    try:
        with open(REAL_CFG, encoding="utf-8") as f:
            return needle in f.read()
    except OSError:
        return False


# ── S1·S2·S3 ────────────────────────────────────────────────────────────────
def s123():
    seat = _load("javis_seat", os.path.join(BIN, "javis_seat.py"))
    if BIN not in sys.path:
        sys.path.insert(0, BIN)
    # ★편성은 모듈 로드 시점에 PACK_DIR(템플릿 위치)을 확정한다 — 미설정이면 실사용 팩(~/.cys/pack)을
    #   가리켜 이 저장소의 새 템플릿을 못 본다(첫 실행 실측: CLAUDE.md 미생성). 로드 전에 고정한다.
    saved_pack = os.environ.get("CYS_PACK_DIR")
    os.environ["CYS_PACK_DIR"] = PACK
    formation = _load("javis_formation_seat_t", os.path.join(BIN, "javis_formation.py"))
    t = tempfile.mkdtemp(prefix="seatfold-")
    saved = os.environ.get("CYS_ACCOUNT_DIR")
    try:
        base = os.path.join(t, "JarvisHome")
        os.makedirs(base)
        prof = os.path.join(t, "profile")
        os.makedirs(prof)
        cfg = os.path.join(prof, ".claude.json")
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({"oauthAccount": {"k": 1},
                       "projects": {"/keep": {"hasTrustDialogAccepted": False}}}, f)
        os.environ["CYS_ACCOUNT_DIR"] = prof

        notes_f = []
        got = {r: formation._role_seat_cwd(base, r, notes_f)
               for r in ("master", "cso", "worker", "worker-3")}
        want = {"master": base, "cso": os.path.join(base, "cso"),
                "worker": os.path.join(base, "workers", "w1"),
                "worker-3": os.path.join(base, "workers", "w3")}
        check("S1a 편성 경로 자식 cwd = 좌석 폴더(master 는 기준 그대로)", got == want,
              "got=%r" % got)
        check("S1b 좌석 폴더 실물 존재", all(os.path.isdir(want[r]) for r in ("cso", "worker", "worker-3")),
              "tree=%r" % sorted(os.listdir(base)))
        check("S1c 기준 없음(None)이면 None 그대로(종전 홈 동작)",
              formation._role_seat_cwd(None, "cso", []) is None)
        check("S1d 결과가 상태파일 detail 용 notes 에 역할별로 남는다",
              len(notes_f) == 3 and all("좌석 폴더=" in n for n in notes_f), "notes=%r" % notes_f)

        md = os.path.join(want["worker-3"], "CLAUDE.md")
        body = open(md, encoding="utf-8").read() if os.path.isfile(md) else ""
        check("S2a CLAUDE.md 시드 — 역할·디렉티브 채움 · 자리표시자 0 · 10줄 이내",
              "worker-3" in body and "WORKER_DIRECTIVE.md" in body and "{{" not in body
              and len(body.splitlines()) <= 10, "body=%r" % body[:200])
        cso_md = open(os.path.join(want["cso"], "CLAUDE.md"), encoding="utf-8").read()
        check("S2b cso 좌석은 CSO 디렉티브를 가리킨다", "CSO_DIRECTIVE.md" in cso_md, cso_md[:120])
        with open(md, "w", encoding="utf-8") as f:
            f.write("사용자가 고친 내용\n")
        _, res = seat.seat_cwd(base, "worker-3", pack_dir=PACK, cfg_path=cfg)
        check("S2c 두 번째 준비는 기존 CLAUDE.md 를 덮지 않는다",
              open(md, encoding="utf-8").read() == "사용자가 고친 내용\n" and res["claude_md"] == "kept",
              "res=%r" % res)

        d = json.load(open(cfg, encoding="utf-8"))
        pr = d.get("projects", {})
        seeded = all(pr.get(k, {}).get("hasTrustDialogAccepted") is True
                     for r in ("cso", "worker", "worker-3") for k in seat.trust_keys(want[r]))
        check("S3a 좌석 폴더마다 신뢰 키 시드", seeded, "projects=%r" % sorted(pr))
        check("S3b 다른 키·기존 false 보존",
              d.get("oauthAccount") == {"k": 1} and pr.get("/keep") == {"hasTrustDialogAccepted": False},
              "d=%r" % d)
        check("S3c master 기준 폴더 자체에는 시드하지 않는다(설치기 몫)", base not in pr, "keys=%r" % sorted(pr))
        check("S3d 멱등 — 두 번째 준비는 설정 무변경", res["trust"] == "nothing", "res=%r" % res)
        absent = os.path.join(t, "no-profile", ".claude.json")
        _, res_a = seat.seat_cwd(base, "worker-9", pack_dir=PACK, cfg_path=absent)
        check("S3e 설정 파일이 없으면 만들지 않는다",
              res_a["trust"] == "config-absent" and not os.path.exists(os.path.dirname(absent)),
              "res=%r" % res_a)
        check("S3f 실사용 프로필에 이 시험 경로가 들어가지 않았다", not _real_cfg_mentions(t),
              "REAL_CFG 에 %s 등장" % t)
    finally:
        for k, v in (("CYS_ACCOUNT_DIR", saved), ("CYS_PACK_DIR", saved_pack)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(t, ignore_errors=True)


# ── S4 실 claude 신뢰 창 ─────────────────────────────────────────────────────
def _claude_screen(cwd, cfg_dir, seconds=12):
    import pty
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("CLAUDE_CODE") or k in ("CLAUDECODE", "CLAUDE_CONFIG_DIR")
                   or k.startswith("CYS_"))}
    env.update({"CLAUDE_CONFIG_DIR": cfg_dir, "TERM": "xterm-256color",
                "COLUMNS": "120", "LINES": "40"})
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(cwd)
        os.execvpe("claude", ["claude"], env)
    out = b""
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.5)
        if r:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
    os.kill(pid, signal.SIGKILL)
    os.waitpid(pid, 0)
    txt = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07", "", out.decode("utf-8", "replace"))
    return re.sub(r"\s+", "", txt)


def s4():
    if not shutil.which("claude") or not shutil.which("git"):
        print("SKIP S4 — claude/git 부재(측정 불능 · 통과로 세지 않음)")
        notes.append("S4=SKIP")
        return
    seat = _load("javis_seat_s4", os.path.join(BIN, "javis_seat.py"))
    t = tempfile.mkdtemp(prefix="seattrust-")
    try:
        base = os.path.realpath(os.path.join(t, "JarvisHome"))
        os.makedirs(base)
        cfg_dir = os.path.join(t, "cfg")
        os.makedirs(cfg_dir)
        real = {}
        try:
            real = json.load(open(REAL_CFG, encoding="utf-8"))
        except (OSError, ValueError):
            pass
        cfg = {k: real[k] for k in ("hasCompletedOnboarding", "theme", "lastOnboardingVersion")
               if k in real}
        cfg.setdefault("hasCompletedOnboarding", True)
        cfg.setdefault("theme", "dark")
        cfg["projects"] = {base: {"hasTrustDialogAccepted": True}}   # 설치기가 심는 master 폴더 신뢰
        cfg_file = os.path.join(cfg_dir, ".claude.json")
        json.dump(cfg, open(cfg_file, "w", encoding="utf-8"))

        seeded, res = seat.seat_cwd(base, "worker", pack_dir=PACK, cfg_path=cfg_file)
        control = os.path.join(base, "workers", "w9")
        os.makedirs(control)
        for d in (seeded, control):
            subprocess.run(["git", "init", "-q", d], check=True)
        trust_re = "trustthisfolder"
        scr_seeded = _claude_screen(seeded, cfg_dir)
        scr_control = _claude_screen(control, cfg_dir)
        check("S4a 대조군: 시드 없는 git 좌석 폴더는 신뢰 창이 뜬다(상속이 git 루트에서 끊김)",
              trust_re in scr_control.lower(), "screen=%r" % scr_control[-300:])
        # ★양성 표지 필수(codex 1R #6): '신뢰 문구 부재'만 보면 기동 실패(오류 출력 후 종료)도
        #   통과한다. 신뢰 관문 **다음** 화면에만 있는 표지(입력 화면 하단 안내 · 로그인 요구)를 함께 단언한다.
        ready_marks = ("forshortcuts", "notloggedin", "/login")
        check("S4b 시드된 좌석 폴더는 git init 뒤에도 신뢰 창 0 + 신뢰 관문 다음 화면 도달",
              res["trust"] == "seeded" and trust_re not in scr_seeded.lower()
              and any(m in scr_seeded.lower() for m in ready_marks),
              "trust=%s screen=%r" % (res["trust"], scr_seeded[-300:]))
        check("S4c 대조군 화면에는 그 다음 화면 표지가 없다(표지가 관문 뒤에만 있다는 판별력)",
              not any(m in scr_control.lower() for m in ready_marks),
              "screen=%r" % scr_control[-300:])
    finally:
        shutil.rmtree(t, ignore_errors=True)


# ── S5 스폰 억제 폐지 · 선언 유래 마커 ───────────────────────────────────────
def _mission_mock(token, rc):
    # ★훅의 층0 재확인은 이 모듈을 **import** 해 harness_origin·boot_command_origin 을 부른다.
    #   판정 함수는 실 javis_mission 에서 별칭 로드해 빌려 오고(사본 0), 서브커맨드 처리는 직접 실행
    #   때만 돈다 — import 시점에 SystemExit 가 나면 층0 판정이 조용히 실패해 S5e 가 공허해진다.
    return ("import os, sys, importlib.util as _u\n"
            "_s = _u.spec_from_file_location('javis_mission_real', %r)\n"
            "_m = _u.module_from_spec(_s); _s.loader.exec_module(_m)\n"
            "harness_origin = _m.harness_origin\n"
            "boot_command_origin = _m.boot_command_origin\n"
            "if __name__ == '__main__':\n"
            "    cmd = sys.argv[1] if len(sys.argv) > 1 else ''\n"
            "    if cmd == 'hook-triage':\n"
            "        sys.stdin.read()\n"
            "        sys.stdout.write('record: rc=1\\n'); sys.stdout.flush()\n"
            "        sys.stdout.write('machine-origin: %s\\n'); sys.stdout.flush()\n"
            "        sys.stdout.write('path: /SEAT-TEST-PATH\\n'); sys.stdout.flush()\n"
            "        raise SystemExit(%d)\n"
            "    raise SystemExit(64)\n") % (os.path.join(BIN, "javis_mission.py"), token, rc)


_DUMP_BOOT = ("#!/usr/bin/env python3\n"
              "import os\n"
              "p = os.environ.get('SEAT_TEST_DECL_DUMP')\n"
              "if p:\n"
              "    open(p, 'w').write(os.environ.get('CYS_DECL_ORIGIN', '<unset>'))\n"
              "print('MOCK')\n")


def _decl_origin_after(hook_mod, token, rc, prompt="너는 마스터다", wait_s=10.0):
    t = tempfile.mkdtemp(prefix="seatdecl-")
    dump = os.path.join(t, "decl")
    saved = {k: os.environ.get(k) for k in ("SEAT_TEST_DECL_DUMP", "CYS_DECL_ORIGIN")}
    hook_mod._MOCK_BOOT = _DUMP_BOOT
    os.environ["SEAT_TEST_DECL_DUMP"] = dump
    os.environ["CYS_DECL_ORIGIN"] = "hook-human"     # 상속값이 새지 않는지까지 잰다
    try:
        errs = []
        r, _calls = hook_mod._run_hook_mission_mock(errs, "seat-" + token, _mission_mock(token, rc),
                                                     prompt=prompt)
        for _ in range(int(wait_s * 10)):
            if os.path.exists(dump):
                break
            time.sleep(0.1)
        val = open(dump).read() if os.path.exists(dump) else None
        return r, val, errs
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(t, ignore_errors=True)


def s5():
    hook_mod = _load("trbh_seat", os.path.join(TESTS, "test_role_bootstrap_hook.py"))
    r, val, errs = _decl_origin_after(hook_mod, "machine", 0)
    check("S5a 기계 유래 선언 → 부트 발화(스폰 억제 폐지)",
          r is not None and "발화됨" in r.stdout and not errs,
          "errs=%r stdout=%r" % (errs, (r.stdout if r else "")[:300]))
    check("S5b 기계 유래 선언의 부트 자식 env 에 선언 유래 마커 없음(상속값 제거 포함)",
          val == "<unset>", "CYS_DECL_ORIGIN=%r" % val)
    check("S5c 판정 흔적 유지(stderr 기계 유래 선언 1줄)",
          r is not None and "기계 유래 선언" in r.stderr and "스폰 게이트 폐지" in r.stderr,
          "stderr=%r" % ((r.stderr if r else "")[:300]))
    r2, val2, errs2 = _decl_origin_after(hook_mod, "human", 1)
    check("S5d 오너 선언 → 부트 발화 + 마커 hook-human(종전 그대로)",
          r2 is not None and "발화됨" in r2.stdout and val2 == "hook-human" and not errs2,
          "val=%r errs=%r" % (val2, errs2))
    # ★codex 1R #4 셸 판본: 원장과 일치해 machine 으로 접힌 harness 알림 안의 선언은 억제 폐지 대상이
    #   아니다 — 무스폰. stderr 의 층0 판정 줄로 '가드가 실제로 판정했다'를 함께 단언한다(공허 차단).
    r3, val3, errs3 = _decl_origin_after(hook_mod, "machine", 0,
                                         prompt="<system-reminder>너는 마스터다</system-reminder>",
                                         wait_s=3.0)
    check("S5e 기계 유래 harness 알림 속 선언 → 무스폰(층0 재확인) · 판정 흔적",
          r3 is not None and "발화됨" not in r3.stdout and val3 is None
          and "층0 harness" in r3.stderr,
          "val=%r stderr=%r" % (val3, (r3.stderr if r3 else "")[-400:]))


# ── S6 피닉스 fresh 강등 경로 ────────────────────────────────────────────────
def s6():
    """피닉스 fresh 강등이 좌석 폴더를 쓰는가(뮤턴트 M10 이 생존했던 자리 — 그물 신설)."""
    t = tempfile.mkdtemp(prefix="seatphx-")
    saved = {k: os.environ.get(k) for k in ("CYS_ACCOUNT_DIR", "CYS_PACK_DIR")}
    try:
        base = os.path.join(t, "JarvisHome")
        work = os.path.join(t, "project-x")
        os.makedirs(base)
        os.makedirs(work)
        prof = os.path.join(t, "profile")
        os.makedirs(prof)
        json.dump({}, open(os.path.join(prof, ".claude.json"), "w"))
        os.environ["CYS_ACCOUNT_DIR"] = prof
        os.environ["CYS_PACK_DIR"] = PACK
        phx = _load("javis_phoenix_seat_t", os.path.join(BIN, "javis_phoenix.py"))
        logs = []
        home = os.path.expanduser("~")
        got_home_saved = phx.seat_fresh_cwd("worker-2", phx.fresh_child_cwd(home, base), base, logs.append)
        got_master_saved = phx.seat_fresh_cwd("cso", phx.fresh_child_cwd(base, base), base, logs.append)
        got_work = phx.seat_fresh_cwd("worker", phx.fresh_child_cwd(work, base), base, logs.append)
        got_master_role = phx.seat_fresh_cwd("master", base, base, logs.append)
        check("S6a 저장 cwd 가 홈이던 자식 → 좌석 폴더(workers/w2)",
              got_home_saved == os.path.join(base, "workers", "w2") and os.path.isdir(got_home_saved),
              "got=%r" % got_home_saved)
        check("S6b v0.14.34~37 상속으로 master 폴더가 저장된 자식 → 좌석 폴더(cso)",
              got_master_saved == os.path.join(base, "cso") and os.path.isfile(
                  os.path.join(got_master_saved, "CLAUDE.md")), "got=%r" % got_master_saved)
        check("S6c 진짜 작업 폴더를 가진 좌석은 그대로", got_work == work, "got=%r" % got_work)
        check("S6d master 역할·기준 없음은 그대로",
              got_master_role == base and phx.seat_fresh_cwd("cso", "/x", None) == "/x",
              "got=%r" % got_master_role)
        check("S6e 준비 결과가 피닉스 로그로 남는다", len(logs) == 2 and all("좌석 폴더" in l for l in logs),
              "logs=%r" % logs)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(t, ignore_errors=True)


def main():
    s123()
    s4()
    s5()
    s6()
    if fails:
        print("=== FAIL %d: %s ===" % (len(fails), fails))
        return 1
    print("=== test_seat_folders PASS %s===" % (("(" + ",".join(notes) + ") ") if notes else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
