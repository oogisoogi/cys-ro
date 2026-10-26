#!/usr/bin/env python3
"""test_hook_slim — 1.1.11 hook-slim(TICKET=hook-slim-1111) 사용자 설정 마이그레이션 상태표 S1~S11 + 분리 실행 + 빠른 탈출.

실 경로를 탄다: 저장소에서 빌드한 `cys`(기본 <repo>/target/debug/cys · env CYS_TEST_BIN 로 바꿈)를 **격리 HOME** 에서
`init-pack`(= 데몬 기동과 같은 `pack::setup_isolated_config_dir` 경로)·`doctor --fix` 로 돌리고, 개인 프로필 settings 의
전후를 바이트로 대조한다. 실 사용자 설정 파일은 읽지도 쓰지도 않는다.
판정: 사용자 훅·다른 키 바이트 보존(기대값 = 원본 dict 에서 팩 등록만 뺀 것을 `JSON.stringify(값, null, 2)` 모양으로) ·
백업 = 원본 바이트 · 실패 시 원본 무변경 · 두 번째 실행 무쓰기 · 되돌리기 1줄(cp 백업) · 좌석 프로필(~/.cys/claude) 보존.
--diff-out <파일> 이면 각 상태의 전후 diff 를 사람이 읽는 기록으로 남긴다.

    python3 cysjavis-pack/bin/tests/test_hook_slim.py [--diff-out <path>]
"""
import difflib
import glob
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PACK_SRC = os.path.dirname(os.path.dirname(HERE))           # cysjavis-pack
REPO = os.path.dirname(PACK_SRC)
HOOKS_SRC = os.path.join(PACK_SRC, "hooks")
BIN = os.environ.get("CYS_TEST_BIN") or os.path.join(REPO, "target", "debug", "cys")

PASS, FAIL, LOG = [], [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — %s" % detail) if detail and not cond else ""))


def js(d):
    """JSON.stringify(d, null, 2) 와 같은 모양(실 ~/.claude/settings.json 형식 · 10-27 실측)."""
    return json.dumps(d, indent=2, ensure_ascii=False)


def pack_hook(home, script, event, matcher=None, timeout=None):
    h = {"type": "command", "command": "sh %s/.cys/pack/hooks/%s" % (home, script)}
    if timeout:
        h["timeout"] = timeout
    e = {"hooks": [h]}
    if matcher is not None:
        e["matcher"] = matcher
    return event, e


# 1.1.10 설치본이 개인 프로필에 거는 팩 훅 20행(실측 10-27 ~/.claude/settings.json 과 같은 집합) + 팩 상태줄
PACK20 = [("cys-hook.sh", "PermissionRequest", ""), ("cys-hook.sh", "PostToolUse", ""),
          ("commit-memory-nudge.sh", "PostToolUse", "Bash"), ("grill-count.sh", "PostToolUse", "AskUserQuestion"),
          ("pack-guard.sh", "PostToolUse", "Write|Edit|MultiEdit"), ("save-state.sh", "PreCompact", None),
          ("cys-hook.sh", "PreToolUse", ""), ("appbuild-gate.sh", "PreToolUse", "Edit|Write|NotebookEdit"),
          ("grill-gate.sh", "PreToolUse", "Edit|Write|NotebookEdit"), ("grill-arm.sh", "PreToolUse", "Skill"),
          ("directive-event-inject.sh", "PreToolUse", "Bash"), ("reflect-scan.sh", "SessionEnd", None),
          ("session-start.sh", "SessionStart", None), ("inject-context.sh", "SessionStart", None),
          ("inject-background.sh", "SessionStart", None), ("save-state.sh", "Stop", None),
          ("reflect-scan.sh", "Stop", None), ("grill-stop.sh", "Stop", ""),
          ("role-bootstrap.sh", "UserPromptSubmit", None), ("dept-chat-inject.sh", "UserPromptSubmit", None)]

USER_HOOKS = [("PostToolUse", {"matcher": "Bash|Read", "hooks": [
                  {"type": "command", "command": "python3 /u/.claude/channels/utc-kst-hook.py", "timeout": 5}]}),
              ("PreToolUse", {"matcher": "Bash", "hooks": [
                  {"type": "command", "command": "sh /u/.claude/channels/cmux-layout-guard.sh", "timeout": 10}]}),
              ("Stop", {"matcher": "", "hooks": [
                  {"type": "command", "command": "python3 /u/.claude/channels/hooks/korean-reply-guard.py"}]})]


def settings_doc(home, pack=True, user=True, statusline=True):
    hooks = {}
    if pack:
        for script, ev, m in PACK20:
            e, entry = pack_hook(home, script, ev, m)
            hooks.setdefault(e, []).append(entry)
    if user:
        for ev, entry in USER_HOOKS:
            hooks.setdefault(ev, []).append(json.loads(json.dumps(entry)))
    d = {"env": {"CLAUDE_CODE_NO_FLICKER": "1", "LANG": "ko_KR.UTF-8"}, "permissions": {"allow": ["Bash(ls:*)"]},
         "model": "opus", "hooks": hooks}
    if statusline:
        d["statusLine"] = {"type": "command", "command": "sh %s/.cys/pack/hooks/cys-statusline.sh" % home}
    d.update({"language": "한국어", "theme": "dark", "voiceEnabled": False, "modelSettings": {"x": 1.5}})
    return d


def strip_expected(d, home):
    """원본 dict 에서 팩 등록만 뺀 기대값(엔진 계약: 빈 entry·빈 이벤트·빈 hooks 제거 · 순서 보존)."""
    d = json.loads(json.dumps(d))
    pref = "%s/.cys/pack/" % home
    if "hooks" in d:
        for ev in list(d["hooks"]):
            arr = d["hooks"][ev]
            for e in arr:
                e["hooks"] = [h for h in e["hooks"] if pref not in h.get("command", "")]
            d["hooks"][ev] = [e for e in arr if e["hooks"]]
            if not d["hooks"][ev]:
                del d["hooks"][ev]
        if not d["hooks"]:
            del d["hooks"]
    if pref in (d.get("statusLine") or {}).get("command", ""):
        del d["statusLine"]
    return d


def new_home():
    home = tempfile.mkdtemp(prefix="hookslim-S-")
    return os.path.realpath(home)


def env_for(home, **extra):
    e = {"HOME": home, "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "ko_KR.UTF-8", "CYS_NO_AUTOSTART": "1",
         "TMPDIR": os.environ.get("TMPDIR", "/tmp")}
    e.update({k: v for k, v in extra.items() if v is not None})
    return e


def cys(home, *args, **extra):
    return subprocess.run([BIN] + list(args), env=env_for(home, **extra), capture_output=True, text=True,
                          timeout=300)


def backups(path):
    return sorted(glob.glob(path + ".bak-cys-hookslim-*"))


def record(case, path, before, after):
    LOG.append("### %s · %s\n" % (case, path))
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), "전", "후", lineterm="", n=1))
    LOG.append("```diff\n%s\n```\n" % ("\n".join(diff) if diff else "(무변경 — 바이트 동일)"))


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    if mode is not None:
        os.chmod(path, mode)


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def seat_settings(home):
    return os.path.join(home, ".cys", "claude", "settings.json")


def awakening_in(path):
    try:
        t = read(path)
    except OSError:
        return False
    return "session-start.sh" in t and "role-bootstrap.sh" in t


def s_cases():
    # ── S1 새 설치(개인 프로필 없음) ──
    h = new_home()
    r = cys(h, "init-pack")
    check("S1 init-pack rc 0", r.returncode == 0, r.stderr[-300:])
    check("S1 ~/.claude 를 만들지 않는다", not os.path.exists(os.path.join(h, ".claude")))
    check("S1 좌석 프로필에 각성 훅", awakening_in(seat_settings(h)))
    LOG.append("### S1 새 설치\n~/.claude 생성 안 함 · ~/.cys/claude/settings.json 각성 훅 2(SessionStart·UserPromptSubmit)\n")
    shutil.rmtree(h, ignore_errors=True)

    # ── S2 1.1.10 설치본(팩 훅 20 + 팩 상태줄 · 사용자 훅 없음) · S10 멱등 · S11 되돌리기 ──
    h = new_home()
    p = os.path.join(h, ".claude", "settings.json")
    d = settings_doc(h, pack=True, user=False)
    before = js(d)
    write(p, before)
    r = cys(h, "init-pack")
    after = read(p)
    record("S2 1.1.10 설치본(팩 훅만)", "~/.claude/settings.json", before, after)
    check("S2 팩 훅·팩 상태줄 제거 · 다른 키 바이트 보존", after == js(strip_expected(d, h)), after[:200])
    check("S2 hooks 키 통째 제거(빈 hooks 남기지 않음)", "\"hooks\"" not in after)
    bk = backups(p)
    check("S2 사전 백업 1개 = 원본 바이트", len(bk) == 1 and read(bk[0]) == before, str(bk))
    check("S2 로그 1줄", "개인 프로필 팩 등록 제거" in r.stderr, r.stderr[-300:])
    r2 = cys(h, "init-pack")
    check("S10 두 번째 실행 = 무쓰기(바이트 동일 · 백업 추가 0)", read(p) == after and len(backups(p)) == 1)
    r3 = cys(h, "doctor", "--fix")
    check("S10 doctor --fix 뒤에도 재부착 0", read(p) == after, r3.stdout[-300:])
    shutil.copyfile(bk[0], p)          # S11 되돌리기 1줄: cp <백업> settings.json
    check("S11 되돌리기 1줄(cp 백업) = 원본 바이트 복원", read(p) == before)
    LOG.append("### S11 되돌리기\n`cp ~/.claude/settings.json.bak-cys-hookslim-<초> ~/.claude/settings.json` → 원본 바이트 일치\n")
    shutil.rmtree(h, ignore_errors=True)

    # ── S3 팩 훅 + 사용자 훅 섞임(우리 맥 모양: 같은 이벤트 배열에 공존) ──
    h = new_home()
    p = os.path.join(h, ".claude", "settings.json")
    d = settings_doc(h, pack=True, user=True)
    before = js(d)
    write(p, before)
    cys(h, "init-pack")
    after = read(p)
    record("S3 섞임", "~/.claude/settings.json", before, after)
    check("S3 사용자 훅 3행 순서·바이트 보존 · 팩 20행 제거", after == js(strip_expected(d, h)), after[:300])
    check("S3 사용자 훅 개수 3", sum(len(e["hooks"]) for v in json.loads(after)["hooks"].values() for e in v) == 3)
    shutil.rmtree(h, ignore_errors=True)

    # ── S4 사용자 훅만 ──
    h = new_home()
    p = os.path.join(h, ".claude", "settings.json")
    before = js(settings_doc(h, pack=False, user=True, statusline=False))
    write(p, before)
    cys(h, "init-pack")
    check("S4 사용자 훅만 = 바이트 동일 · 백업 0", read(p) == before and not backups(p))
    record("S4 사용자 훅만", "~/.claude/settings.json", before, read(p))
    shutil.rmtree(h, ignore_errors=True)

    # ── S5 깨진 JSON ──
    h = new_home()
    p = os.path.join(h, ".claude", "settings.json")
    before = '{\n  "hooks": { "Stop": [ ' + json.dumps(pack_hook(h, "save-state.sh", "Stop")[1]) + '\n'   # 닫힘 없음
    write(p, before)
    r = cys(h, "init-pack")
    check("S5 깨진 JSON = 원본 무변경 · 백업 0", read(p) == before and not backups(p))
    check("S5 설치는 계속(rc 0) · 건너뜀 1줄", r.returncode == 0 and "개인 프로필 팩 등록 제거 건너뜀" in r.stderr,
          r.stderr[-300:])
    record("S5 깨진 JSON", "~/.claude/settings.json", before, read(p))
    shutil.rmtree(h, ignore_errors=True)

    # ── S6 읽기 전용(사용자가 잠근 파일) ──
    h = new_home()
    p = os.path.join(h, ".claude", "settings.json")
    before = js(settings_doc(h, pack=True, user=True))
    write(p, before, mode=0o444)
    r = cys(h, "init-pack")
    check("S6 읽기 전용 = 원본 무변경 · 권한 그대로 · 백업 0",
          read(p) == before and stat.S_IMODE(os.stat(p).st_mode) == 0o444 and not backups(p))
    check("S6 건너뜀 사유 1줄", "읽기 전용" in r.stderr, r.stderr[-300:])
    rd = cys(h, "doctor")
    check("S6 doctor 가 잔재를 경고로 보인다", "팩 훅 잔재" in rd.stdout, rd.stdout[-400:])
    os.chmod(p, 0o644)
    record("S6 읽기 전용", "~/.claude/settings.json", before, read(p))
    shutil.rmtree(h, ignore_errors=True)

    # ── S7 다중 프로필(~/.claude · ~/.claude-acct2) + 좌석 프로필(~/.cys/claude) 보존 ──
    h = new_home()
    p1 = os.path.join(h, ".claude", "settings.json")
    p2 = os.path.join(h, ".claude-acct2", "settings.json")
    d = settings_doc(h, pack=True, user=True)
    for p in (p1, p2):
        write(p, js(d))
    seat_before = js({"hooks": {"SessionStart": [pack_hook(h, "session-start.sh", "SessionStart")[1]],
                                "PreToolUse": [pack_hook(h, "cys-hook.sh", "PreToolUse", "")[1]]},
                      "statusLine": {"type": "command", "command": "sh %s/.cys/pack/hooks/cys-statusline.sh" % h}})
    write(seat_settings(h), seat_before)
    cys(h, "init-pack", CLAUDE_CONFIG_DIR=os.path.join(h, ".claude-acct2"))
    want = js(strip_expected(d, h))
    check("S7 ~/.claude 정리", read(p1) == want)
    check("S7 ~/.claude-acct2 정리(CLAUDE_CONFIG_DIR 로 지정돼 있어도 개인 프로필)", read(p2) == want)
    seat_after = read(seat_settings(h))
    check("S7 좌석 프로필 팩 훅·상태줄 보존(cys-hook·statusLine 그대로 + 각성 훅)",
          "cys-hook.sh" in seat_after and "cys-statusline.sh" in seat_after and awakening_in(seat_settings(h)))
    record("S7 다중 프로필 — ~/.claude-acct2", "~/.claude-acct2/settings.json", js(d), read(p2))
    record("S7 좌석 프로필", "~/.cys/claude/settings.json", seat_before, seat_after)
    shutil.rmtree(h, ignore_errors=True)

    # ── S8 옵트인 표지 있음(파일) · env ──
    for how in ("file", "env"):
        h = new_home()
        p = os.path.join(h, ".claude", "settings.json")
        before = js(settings_doc(h, pack=True, user=True))
        write(p, before)
        extra = {}
        if how == "file":
            write(os.path.join(h, ".cys", "local", "hooks-personal-profiles"), "")
        else:
            extra["CYS_HOOKS_PERSONAL"] = "1"
        cys(h, "init-pack", **extra)
        check("S8(%s) 표지 있음 = 개인 프로필 팩 훅 보존(제거 0 · 백업 0)" % how,
              "save-state.sh" in read(p) and not backups(p))
        record("S8 옵트인(%s)" % how, "~/.claude/settings.json", before, read(p))
        shutil.rmtree(h, ignore_errors=True)

    # ── S9 윈 모양: BOM + CRLF + 역슬래시·따옴표 런처 명령 + 비UTF-8(cp949) 파일 ──
    h = new_home()
    p = os.path.join(h, ".claude", "settings.json")
    winpack = ("%s/.cys/pack" % h).replace("/", "\\")
    d = settings_doc(h, pack=False, user=True, statusline=False)
    d["hooks"]["Stop"].insert(0, {"hooks": [{"type": "command",
                                             "command": 'bash "%s\\hooks\\save-state.sh"' % winpack}]})
    body = js(d).replace("\n", "\r\n")
    write(p, "\ufeff" + body)
    cys(h, "init-pack")
    after = read(p)
    d2 = json.loads(json.dumps(d))
    del d2["hooks"]["Stop"][0]
    check("S9 BOM·CRLF 유지 · 역슬래시 팩 명령 제거 · 나머지 바이트 보존",
          after == "\ufeff" + js(d2).replace("\n", "\r\n"), repr(after[:120]))
    record("S9 윈 모양(BOM·CRLF·역슬래시)", "~/.claude/settings.json", "\ufeff" + body, after)
    raw = ("{\"note\": \"한글\", \"hooks\": {\"Stop\": [%s]}}" % json.dumps(pack_hook(h, "save-state.sh", "Stop")[1],
                                                                          ensure_ascii=False)).encode("cp949")
    with open(p, "wb") as f:
        f.write(raw)
    r = cys(h, "init-pack")
    with open(p, "rb") as f:
        check("S9 비UTF-8(cp949) 파일 = 원본 무변경 · 건너뜀 1줄",
              f.read() == raw and "건너뜀" in r.stderr, r.stderr[-200:])
    shutil.rmtree(h, ignore_errors=True)


def preflight_case():
    """파이썬 등록 경로(preflight --fix)도 표지 없이는 개인 프로필에 다시 붙이지 않는다(데몬·preflight 양쪽 재부착 0).
    ★HOME 은 임시 폴더 **밖**(<repo>/target 아래)에 둔다 — 팩이 임시 폴더 아래면 preflight 의 임시 팩 가드가 등록을
    통째로 끄므로(_path_under_tempdir) 그 안에서는 「재부착 0」이 아무것도 재지 못한다(10-27 첫 판 실측)."""
    os.makedirs(os.path.join(REPO, "target"), exist_ok=True)
    h = os.path.realpath(tempfile.mkdtemp(prefix="hookslim-PF-", dir=os.path.join(REPO, "target")))
    p = os.path.join(h, ".claude", "settings.json")
    before = js(settings_doc(h, pack=False, user=True, statusline=False))
    write(p, before)
    cys(h, "init-pack")
    pf = os.path.join(h, ".cys", "pack", "bin", "javis_preflight.py")
    env = env_for(h, PATH="%s:%s" % (os.path.dirname(BIN), "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"),
                  CYS_PACK_DIR=os.path.join(h, ".cys", "pack"))
    t0 = time.time()
    r = subprocess.run([sys.executable, pf, "--fix"], env=env, capture_output=True, text=True, timeout=600)
    check("PF preflight 가 임시 팩 가드에 걸리지 않았다(실측 유효성)", "임시 팩 컨텍스트" not in r.stdout,
          r.stdout[-300:])
    check("PF preflight --fix 뒤 개인 프로필 바이트 동일(재부착 0)", read(p) == before,
          "rc=%s %s" % (r.returncode, read(p)[:200]))
    seat = read(seat_settings(h))
    want = [("cys-hook.sh", "PreToolUse"), ("save-state.sh", "Stop"), ("grill-stop.sh", "Stop"),
            ("appbuild-gate.sh", "PreToolUse"), ("reflect-scan.sh", "SessionEnd")]
    sd = json.loads(seat)
    def to_of(script, ev):
        for e in sd.get("hooks", {}).get(ev, []):
            for hh in e.get("hooks", []):
                if hh.get("command", "").endswith("/hooks/" + script):
                    return hh.get("timeout")
        return "미등록"
    got = {"%s/%s" % w: to_of(*w) for w in want}
    check("PF 좌석 프로필에 선언 timeout 기록(10초)", all(v == 10 for v in got.values()), str(got))
    LOG.append("### PF preflight --fix (%.0f초)\n개인 프로필 바이트 동일 · 좌석 timeout %s\n" % (time.time() - t0, got))
    shutil.rmtree(h, ignore_errors=True)


def hook_cases():
    """빠른 탈출·분리 실행(셸 단위)."""
    h = new_home()
    pk = os.path.join(h, ".cys", "pack")
    shutil.copytree(PACK_SRC, pk, ignore=shutil.ignore_patterns("tests", "__pycache__"))
    fake = os.path.join(h, "fakebin")
    os.makedirs(fake)
    with open(os.path.join(fake, "cys"), "w") as f:
        f.write("#!/bin/sh\necho \"$@\" >> \"$HOME/cys.calls\"\ncat >/dev/null\n")
    os.chmod(os.path.join(fake, "cys"), 0o755)
    ev = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}})
    base = env_for(h, PATH="%s:/usr/bin:/bin" % fake)
    r = subprocess.run(["sh", os.path.join(pk, "hooks", "cys-hook.sh")], input=ev, env=base, capture_output=True,
                       text=True)
    check("FX1 좌석 아님 = cys 미기동 · exit 0 · stdout 0",
          r.returncode == 0 and r.stdout == "" and not os.path.exists(os.path.join(h, "cys.calls")))
    for k in ("CYS_SURFACE_ID", "JAVIS_SURFACE_ID", "AITERM_SURFACE_ID"):
        e = dict(base, **{k: "9"})
        subprocess.run(["sh", os.path.join(pk, "hooks", "cys-hook.sh")], input=ev, env=e, capture_output=True, text=True)
    calls = read(os.path.join(h, "cys.calls")).splitlines() if os.path.exists(os.path.join(h, "cys.calls")) else []
    check("FX2 좌석 env 3키 각각 = cys 사용량 1건씩(env_compat 동일 규칙)", len(calls) == 3, str(calls))
    os.makedirs(os.path.join(h, ".cys", "local", "hooks", "PreToolUse.d"))
    with open(os.path.join(h, ".cys", "local", "hooks", "PreToolUse.d", "o.sh"), "w") as f:
        f.write("cat > \"$HOME/overlay.in\"\n")
    subprocess.run(["sh", os.path.join(pk, "hooks", "cys-hook.sh")], input=ev, env=base, capture_output=True, text=True)
    check("FX3 B1: 좌석 아니면 오버레이도 돌지 않는다(탈출이 맨 앞)", not os.path.exists(os.path.join(h, "overlay.in")))
    subprocess.run(["sh", os.path.join(pk, "hooks", "cys-hook.sh")], input=ev, env=dict(base, CYS_SURFACE_ID="9"),
                   capture_output=True, text=True)
    check("FX3b 좌석이면 오버레이가 입력 전문을 받는다(확장점 불변)",
          os.path.exists(os.path.join(h, "overlay.in")) and read(os.path.join(h, "overlay.in")) == ev)

    tr = os.path.join(h, "t.jsonl")
    write(tr, "{}\n")
    # B1: 가드 없던 팩 훅 10개 + cys-hook — 좌석 아닌 세션이면 무출력·exit 0·부작용 0(_round·state 에 아무것도 안 쓴다)
    gw = os.path.join(h, "gw")
    os.makedirs(os.path.join(gw, "_round"))
    os.makedirs(os.path.join(gw, ".appbuild"))
    payloads = {
        "save-state.sh": ("Stop", None), "reflect-scan.sh": ("Stop", None), "grill-stop.sh": ("Stop", None),
        "grill-gate.sh": ("PreToolUse", "Edit"), "grill-arm.sh": ("PreToolUse", "Skill"),
        "grill-count.sh": ("PostToolUse", "AskUserQuestion"), "appbuild-gate.sh": ("PreToolUse", "Edit"),
        "pack-guard.sh": ("PostToolUse", "Edit"), "commit-memory-nudge.sh": ("PostToolUse", "Bash"),
        "inject-context.sh": ("SessionStart", None), "cys-hook.sh": ("PreToolUse", "Bash")}
    nonseat = env_for(h, PATH="%s:/usr/bin:/bin:/opt/homebrew/bin" % fake, CYS_PACK_DIR=pk)
    st_dir = os.path.join(h, ".cys", "state")
    shutil.rmtree(st_dir, ignore_errors=True)
    bad = []
    for sc, (evn, tool) in payloads.items():
        d = {"hook_event_name": evn, "cwd": gw, "session_id": "s", "transcript_path": tr, "source": "startup"}
        if tool:
            d.update({"tool_name": tool, "tool_input": {"command": "git commit -m x",
                                                        "file_path": os.path.join(pk, "hooks", "x.sh")}})
        t0 = time.time()
        r = subprocess.run(["sh", os.path.join(pk, "hooks", sc)], input=json.dumps(d), env=nonseat,
                           capture_output=True, text=True, timeout=30)
        dt = time.time() - t0
        if r.returncode != 0 or r.stdout or dt > 0.5:
            bad.append((sc, r.returncode, r.stdout[:60], round(dt, 2)))
    side = sorted(os.listdir(os.path.join(gw, "_round"))) + (sorted(os.listdir(st_dir)) if os.path.isdir(st_dir) else [])
    check("GT1 좌석 아님 = 11개 훅 전부 exit 0·무출력·0.5초 미만", not bad, str(bad))
    check("GT2 좌석 아님 = 부작용 0(_round·state 에 기록 없음)", side == [], str(side))
    r = subprocess.run(["sh", os.path.join(pk, "hooks", "grill-stop.sh"), "--self-test"], env=nonseat,
                       capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    check("GT3 인자 호출(--self-test)은 탈출하지 않는다", (r.stdout + r.stderr).strip() != "",
          "rc=%s" % r.returncode)
    seat = dict(nonseat, CYS_SURFACE_ID="9")
    d = {"hook_event_name": "SessionStart", "cwd": gw, "session_id": "s", "source": "startup"}
    r = subprocess.run(["sh", os.path.join(pk, "hooks", "inject-context.sh")], input=json.dumps(d), env=seat,
                       capture_output=True, text=True, timeout=60)
    check("GT4 좌석이면 inject-context 종전대로 주입", r.stdout.strip() != "", r.stderr[-200:])

    # 분리 실행: 느린 reflect 대역 → 부모 즉시 반환 · 자식 산출물 실재 · 직렬화 · 롤백 노브 = 동기
    with open(os.path.join(pk, "bin", "javis_reflect.py"), "w") as f:
        f.write("import sys,time,os\ntime.sleep(float(os.environ.get('SLOW','2')))\n"
                "a=sys.argv;open(a[a.index('--ledger')+1],'a').write('done %d\\n'%os.getpid())\n")
    work = os.path.join(h, "w")
    os.makedirs(os.path.join(work, "_round"))
    tr = os.path.join(h, "t.jsonl")
    write(tr, "{}\n")
    stop = json.dumps({"hook_event_name": "Stop", "cwd": work, "transcript_path": tr, "session_id": "s"})
    env = env_for(h, PATH="/usr/bin:/bin:/opt/homebrew/bin", CYS_PACK_DIR=pk, SLOW="2", CYS_SURFACE_ID="9")
    led = os.path.join(work, "_round", "RSI_LEDGER.md")
    ts = []
    for _ in range(2):
        t0 = time.time()
        r = subprocess.run(["sh", os.path.join(pk, "hooks", "reflect-scan.sh")], input=stop, env=env,
                           capture_output=True, text=True)
        ts.append(time.time() - t0)
    check("DT1 Stop 부모 즉시 반환(<1초 · 본문 2초)", max(ts) < 1.0, str(ts))
    check("DT2 반환 직후 산출물 아직 없음(진짜 분리)", not os.path.exists(led))
    deadline = time.time() + 20
    while time.time() < deadline and (not os.path.exists(led) or len(read(led).splitlines()) < 2):
        time.sleep(0.2)
    lines = read(led).splitlines() if os.path.exists(led) else []
    check("DT3 결과 손실 0(2회분 산출물 2줄)", len(lines) == 2, str(lines))
    lockd = os.path.join(h, ".cys", "state", "hook-detach", "reflect-scan.lock")
    t_end = time.time() + 5
    while os.path.exists(lockd) and time.time() < t_end:
        time.sleep(0.1)
    check("DT4 잠금 해제", not os.path.exists(lockd))
    tl = read(os.path.join(h, ".cys", "state", "hook-timing.log"))
    check("DT5 계측 줄에 (bg) 2건", tl.count("reflect-scan(bg)") == 2, tl[-300:])
    os.remove(led)
    t0 = time.time()
    subprocess.run(["sh", os.path.join(pk, "hooks", "reflect-scan.sh")], input=stop,
                   env=dict(env, CYS_HOOK_STOP_SYNC="1"), capture_output=True, text=True)
    check("DT6 롤백 노브 CYS_HOOK_STOP_SYNC=1 = 동기(반환 시 산출물 있음)",
          time.time() - t0 >= 1.5 and os.path.exists(led))
    os.remove(led)
    pre = json.dumps({"hook_event_name": "PreCompact", "cwd": work, "trigger": "auto"})
    subprocess.run(["sh", os.path.join(pk, "hooks", "save-state.sh")], input=pre, env=env, capture_output=True, text=True)
    check("DT7 save-state PreCompact 는 동기(반환 시 .state_log 에 PreCompact)",
          "PreCompact" in read(os.path.join(work, "_round", ".state_log")))
    # 죽은 주인 잠금 회수
    os.makedirs(lockd)
    write(os.path.join(lockd, "pid"), "999999")
    subprocess.run(["sh", os.path.join(pk, "hooks", "reflect-scan.sh")], input=stop, env=env, capture_output=True, text=True)
    deadline = time.time() + 15
    while time.time() < deadline and not os.path.exists(led):
        time.sleep(0.2)
    check("DT8 죽은 주인 잠금 회수 후 진행", os.path.exists(led))
    shutil.rmtree(h, ignore_errors=True)


def main():
    out = None
    if "--diff-out" in sys.argv:
        out = sys.argv[sys.argv.index("--diff-out") + 1]
    if not os.path.isfile(BIN):
        print("SKIP — cys 바이너리 없음(%s) · cargo build --bin cys 후 재실행" % BIN)
        return 0
    only = os.environ.get("HOOKSLIM_ONLY", "")       # 뮤턴트 실행용: "hooks" 면 셸 훅 부분만
    if only != "hooks":
        s_cases()
        preflight_case()
    hook_cases()
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write("# hook-slim 상태표 전후 diff (격리 HOME · %s)\n\n" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
            f.write("\n".join(LOG))
    print("\n=== %d PASS / %d FAIL ===" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAIL:", FAIL)
        return 1
    print("HOOK-SLIM-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
