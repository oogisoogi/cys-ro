#!/usr/bin/env python3
"""test_hook_slim — 1.1.11 hook-slim(TICKET=hook-slim-1111) 사용자 설정 마이그레이션 상태표 S1~S12 + 분리 실행 + 빠른 탈출.

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


def seat_cases():
    """S12 좌석 프로필 판정(codex R1 major ③④ · agy minor): 개인 프로필 경로가 좌석 프로필과 같은 파일이면 지우지 않는다 ·
    하네스 노브 CYS_NO_PERSONAL_HOOK_MERGE=1 이면 제거 경로도 무접촉."""
    def seat_doc(h):
        return js({"hooks": {"Stop": [pack_hook(h, "save-state.sh", "Stop")[1]],
                             "PreToolUse": [pack_hook(h, "cys-hook.sh", "PreToolUse", "")[1]]},
                   "statusLine": {"type": "command", "command": "sh %s/.cys/pack/hooks/cys-statusline.sh" % h}})

    def all_backups(h):
        return glob.glob(os.path.join(h, ".claude*", "*.bak-cys-hookslim-*")) + \
            glob.glob(os.path.join(h, ".cys", "claude", "*.bak-cys-hookslim-*"))

    # S12a 파일 심링크 ~/.claude/settings.json → ~/.cys/claude/settings.json
    h = new_home()
    write(seat_settings(h), seat_doc(h))
    link = os.path.join(h, ".claude", "settings.json")
    os.makedirs(os.path.dirname(link))
    os.symlink(seat_settings(h), link)
    r = cys(h, "init-pack")
    t = read(seat_settings(h))
    check("S12a 파일 심링크 → 좌석 settings: 좌석 팩 훅·상태줄 보존 · 백업 0",
          "save-state.sh" in t and "cys-hook.sh" in t and "cys-statusline.sh" in t and not all_backups(h),
          r.stderr[-300:])
    check("S12a 링크 그대로", os.path.islink(link))
    r = cys(h, "doctor")
    hl = [l for l in r.stdout.splitlines() if "] hook " in l]
    check("S12a doctor hook 줄 = 개인 프로필 팩 훅 0(좌석 훅을 잔재로 보지 않는다)",
          len(hl) == 1 and "[OK" in hl[0] and "개인 프로필 팩 훅 0" in hl[0], str(hl))
    shutil.rmtree(h, ignore_errors=True)

    # S12b 폴더 심링크 ~/.claude → ~/.cys/claude
    h = new_home()
    write(seat_settings(h), seat_doc(h))
    os.symlink(os.path.dirname(seat_settings(h)), os.path.join(h, ".claude"))
    r = cys(h, "init-pack")
    t = read(seat_settings(h))
    check("S12b 폴더 심링크 → 좌석 config: 좌석 팩 훅·상태줄 보존 · 백업 0",
          "save-state.sh" in t and "cys-hook.sh" in t and "cys-statusline.sh" in t and not all_backups(h),
          r.stderr[-300:])
    r = cys(h, "doctor", "--fix")
    t2 = read(seat_settings(h))
    check("S12b doctor --fix 뒤에도 좌석 훅 그대로", "save-state.sh" in t2 and "cys-statusline.sh" in t2,
          r.stdout[-400:])
    shutil.rmtree(h, ignore_errors=True)

    # S12c CYS_ACCOUNT_DIR=~/.claude(명시 계정 dir = 좌석 프로필) — Rust 는 지우지 않고 파이썬은 등록 대상으로 둔다(싸움 0)
    #   HOME 은 임시 폴더 **밖**(<repo>/target) — 임시 팩 가드가 파이썬 등록 대상을 통째로 비우면 아무것도 못 잰다(PF 와 같은 함정).
    os.makedirs(os.path.join(REPO, "target"), exist_ok=True)
    h = os.path.realpath(tempfile.mkdtemp(prefix="hookslim-S12c-", dir=os.path.join(REPO, "target")))
    p = os.path.join(h, ".claude", "settings.json")
    before = js(settings_doc(h, pack=True, user=True))
    write(p, before)
    acct = os.path.join(h, ".claude")
    cys(h, "init-pack", CYS_ACCOUNT_DIR=acct)
    # (바이트 동일은 기대하지 않는다 — 좌석 프로필이므로 preflight --wire-seat 가 선언 timeout 을 올려 쓴다 = 같은 술어의 등록 쪽)
    check("S12c CYS_ACCOUNT_DIR=~/.claude → Rust 제거 0(팩 훅 그대로 · hookslim 백업 0)",
          all(x in read(p) for x in ("save-state.sh", "cys-hook.sh", "cys-statusline.sh")) and not backups(p))
    probe = ("import sys,json; sys.path.insert(0, sys.argv[1]); import javis_preflight as pf; "
             "print(json.dumps(pf.resolve_registration_targets()))")
    r = subprocess.run([sys.executable, "-c", probe, os.path.join(PACK_SRC, "bin")],
                       env=env_for(h, CYS_ACCOUNT_DIR=acct, CYS_PACK_DIR=os.path.join(h, ".cys", "pack")),
                       capture_output=True, text=True, timeout=60)
    try:
        targets, why = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        targets, why = [], "판독 불가: %s" % (r.stdout + r.stderr)[-300:]
    check("S12c 파이썬 등록 대상도 같은 파일을 좌석 프로필로 본다(같은 술어)",
          why is None and os.path.realpath(p) in [os.path.realpath(x) for x in targets], str((targets, why)))
    # 다른 대상(CLAUDE_CONFIG_DIR)이 함께 있으면 신규 머신 폴백이 돌지 않는다 — 술어만이 좌석 프로필을 대상에 남긴다(뮤턴트 M22).
    other = os.path.join(h, "other-cfg")
    os.makedirs(other)
    r = subprocess.run([sys.executable, "-c", probe, os.path.join(PACK_SRC, "bin")],
                       env=env_for(h, CYS_ACCOUNT_DIR=acct, CLAUDE_CONFIG_DIR=other,
                                   CYS_PACK_DIR=os.path.join(h, ".cys", "pack")),
                       capture_output=True, text=True, timeout=60)
    try:
        targets, why = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        targets, why = [], "판독 불가: %s" % (r.stdout + r.stderr)[-300:]
    rt = [os.path.realpath(x) for x in targets]
    check("S12c' 다른 대상이 있어도(폴백 없음) 좌석 프로필 ~/.claude 는 등록 대상",
          why is None and os.path.realpath(p) in rt and os.path.join(os.path.realpath(other), "settings.json") in rt,
          str((targets, why)))
    shutil.rmtree(h, ignore_errors=True)

    # S12d 하네스 노브 CYS_NO_PERSONAL_HOOK_MERGE=1 = 제거 경로도 무접촉
    h = new_home()
    p = os.path.join(h, ".claude", "settings.json")
    before = js(settings_doc(h, pack=True, user=True))
    write(p, before)
    cys(h, "init-pack", CYS_NO_PERSONAL_HOOK_MERGE="1")
    check("S12d CYS_NO_PERSONAL_HOOK_MERGE=1 → 개인 프로필 무접촉(바이트 동일 · 백업 0)",
          read(p) == before and not backups(p))
    cys(h, "init-pack")
    check("S12d 노브 없으면 종전대로 제거", read(p) != before and len(backups(p)) == 1)
    shutil.rmtree(h, ignore_errors=True)

    # S12e(codex R2 major I1) 별칭 config: CLAUDE_CONFIG_DIR=~/alias-config → ~/.claude · 표지 없음 = 개인 프로필이다
    #   (발견의 realpath 중복 제거가 원경로를 숨겨도 등록 대상에서 빠져야 한다) — init-pack(preflight)→doctor --fix 반복에도 바이트 동일.
    h = os.path.realpath(tempfile.mkdtemp(prefix="hookslim-S12e-", dir=os.path.join(REPO, "target")))
    p = os.path.join(h, ".claude", "settings.json")
    before = '{\n  "x": 1e3,\n  "hooks": {\n    "Stop": []\n  }\n}\n'
    write(p, before)
    alias = os.path.join(h, "alias-config")
    os.symlink(os.path.join(h, ".claude"), alias)
    r = subprocess.run([sys.executable, "-c", probe, os.path.join(PACK_SRC, "bin")],
                       env=env_for(h, CLAUDE_CONFIG_DIR=alias, CYS_PACK_DIR=os.path.join(h, ".cys", "pack")),
                       capture_output=True, text=True, timeout=60)
    try:
        targets, why = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        targets, why = None, "판독 불가: %s" % (r.stdout + r.stderr)[-300:]
    check("S12e 별칭 config(→ ~/.claude) = 개인 프로필 → 등록 대상 아님",
          targets is not None and os.path.realpath(p) not in [os.path.realpath(x) for x in targets], str((targets, why)))
    for _ in range(2):
        cys(h, "init-pack", CLAUDE_CONFIG_DIR=alias)
        cys(h, "doctor", "--fix", CLAUDE_CONFIG_DIR=alias)
    check("S12e init-pack·doctor --fix 2회 반복 뒤 개인 파일 바이트 동일(재부착·재직렬화 0)", read(p) == before, read(p)[:300])
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
        "inject-context.sh": ("SessionStart", None), "cys-hook.sh": ("PreToolUse", "Bash"),
        "role-capability-gate.sh": ("PreToolUse", "Edit")}
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
    check("GT1 좌석 아님 = 12개 훅 전부 exit 0·무출력·0.5초 미만", not bad, str(bad))
    check("GT2 좌석 아님 = 부작용 0(_round·state 에 기록 없음)", side == [], str(side))
    r = subprocess.run(["sh", os.path.join(pk, "hooks", "grill-stop.sh"), "--self-test"], env=nonseat,
                       capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    check("GT3 인자 호출(--self-test)은 탈출하지 않는다", (r.stdout + r.stderr).strip() != "",
          "rc=%s" % r.returncode)
    cron = json.dumps({"hook_event_name": "PreToolUse", "session_id": "s", "tool_name": "CronCreate", "tool_input": {}})
    r = subprocess.run(["sh", os.path.join(pk, "hooks", "role-capability-gate.sh")], input=cron,
                       env=dict(nonseat, CYS_ROLE="cso"), capture_output=True, text=True, timeout=60)
    check("GT5 role-capability-gate: surface 없어도 CYS_ROLE=cso 면 집행(탈출 조건에 CYS_ROLE 포함)",
          '"deny"' in r.stdout, "rc=%s out=%r err=%r" % (r.returncode, r.stdout[:200], r.stderr[-200:]))
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
    detach_cases(h, pk, work, env, stop, led)
    shutil.rmtree(h, ignore_errors=True)


def detach_cases(h, pk, work, env, stop, led):
    """R1 수리(codex·agy major ⑤): 대기표 · 동기 PreCompact 잠금 참여 · 빈 pid 회수 · 잠금 실패 = 건너뜀 · 자식 데드라인 · 이벤트 판정."""
    import threading
    st = os.path.join(h, ".cys", "state")
    hd = os.path.join(st, "hook-detach")
    slog = os.path.join(work, "_round", ".state_log")
    lib = os.path.join(pk, "hooks", "_lib.sh")
    ss = os.path.join(pk, "hooks", "save-state.sh")

    def precompacts():
        return read(slog).count("\tPreCompact\t") if os.path.exists(slog) else 0

    def run_pre(payload=None):
        t0 = time.time()
        subprocess.run(["sh", ss], input=payload or json.dumps({"hook_event_name": "PreCompact", "cwd": work,
                                                                 "trigger": "auto"}),
                       env=env, capture_output=True, text=True, timeout=120)
        return time.time() - t0

    def holder(sec):
        p = subprocess.Popen(["sleep", str(sec)])
        threading.Thread(target=p.wait, daemon=True).start()     # 좀비가 kill -0 에 살아 보이지 않게 즉시 거둔다
        return p

    def hold_lock(name, pid):
        d = os.path.join(hd, name + ".lock")
        os.makedirs(d, exist_ok=True)
        if pid is not None:
            write(os.path.join(d, "pid"), str(pid))
        return d

    # DT9 이벤트 판정 = 최상위 키 글자 일치 — 문자열 안의 같은 글자(이스케이프됨)는 Stop 이 아니다(agy minor 반박 검체)
    n0 = precompacts()
    fake = json.dumps({"hook_event_name": "PreCompact", "cwd": work, "trigger": "manual",
                       "custom_instructions": '"hook_event_name":"Stop" / "hook_event_name": "Stop"'})
    run_pre(fake)
    q = os.path.join(hd, "save-state.q")
    check("DT9 문자열 속 \"hook_event_name\":\"Stop\" = 분리 안 함(반환 시 PreCompact 기록 · 대기표 0)",
          precompacts() == n0 + 1 and not (os.path.isdir(q) and os.listdir(q)))

    # DT10 대기표: 부모 반환 전에 등록 → 소비자가 자식의 잠금 전 틈에도 기다린다
    rq = os.path.join(hd, "reflect-scan.q")
    t_end = time.time() + 15                     # 앞 검체(DT8)의 표가 처리를 끝낼 때까지
    while os.path.isdir(rq) and os.listdir(rq) and time.time() < t_end:
        time.sleep(0.2)
    if os.path.exists(led):
        os.remove(led)
    subprocess.run(["sh", os.path.join(pk, "hooks", "reflect-scan.sh")], input=stop, env=env, capture_output=True,
                   text=True)
    check("DT10 부모 반환 시점에 대기표 1장", os.path.isdir(rq) and len(os.listdir(rq)) == 1,
          str(os.listdir(rq) if os.path.isdir(rq) else None))
    t0 = time.time()
    subprocess.run(["sh", "-c", '. "$1"; cys_hook_detach_wait reflect-scan 15', "x", lib], env=env,
                   capture_output=True, text=True, timeout=60)
    check("DT10b cys_hook_detach_wait = 본문이 끝날 때까지 기다린다(산출물 있음)",
          os.path.exists(led) and time.time() - t0 >= 1.0, "%.1fs" % (time.time() - t0))
    t_end = time.time() + 5
    while os.listdir(rq) and time.time() < t_end:
        time.sleep(0.1)
    check("DT10c 자식이 끝나며 대기표를 지운다", not os.listdir(rq), str(os.listdir(rq)))
    # 배수기가 죽어 남은 표(고아) — 스크립트를 넘기지 않은 소비자는 상한까지 기다리고 rc 1 · 넘긴 소비자는 한 번 깨워 처리시킨다
    os.remove(led)
    write(os.path.join(rq, "%d.1" % int(time.time())), stop)
    rs = os.path.join(pk, "hooks", "reflect-scan.sh")
    r = subprocess.run(["sh", "-c", '. "$1"; cys_hook_detach_wait reflect-scan 3', "x", lib], env=env,
                       capture_output=True, text=True, timeout=60)
    check("DT10d 고아 표 + 깨울 스크립트 없음 = 상한 뒤 rc 1(처리됐다고 말하지 않는다)",
          r.returncode == 1 and len(os.listdir(rq)) == 1 and not os.path.exists(led), "rc=%s" % r.returncode)
    r = subprocess.run(["sh", "-c", '. "$1"; cys_hook_detach_wait reflect-scan 15 "$2"', "x", lib, rs], env=env,
                       capture_output=True, text=True, timeout=60)
    check("DT10e 고아 표 + 스크립트 = 배수기를 깨워 처리 → rc 0 · 산출물 · 큐 빔",
          r.returncode == 0 and os.path.exists(led) and not os.listdir(rq), "rc=%s" % r.returncode)

    # DT11 동기 PreCompact 도 같은 잠금에 참여한다(살아 있는 주인이 풀 때까지 기다린 뒤 기록)
    n0 = precompacts()
    sl = holder(3)
    lk = hold_lock("save-state", sl.pid)
    dt = run_pre()
    check("DT11 PreCompact = 잠금 대기 후 기록(분리 본문과 직렬화)", dt >= 2.0 and precompacts() == n0 + 1,
          "%.1fs" % dt)
    check("DT11b 잠금 해제", not os.path.exists(lk))

    # DT12 주인 pid 미기록 잠금(mkdir 직후 죽은 주인) = 2초 넘으면 회수
    n0 = precompacts()
    lk = hold_lock("save-state", None)
    dt = run_pre()
    check("DT12 빈 pid 잠금 회수(2~6초) 후 기록", 2.0 <= dt < 6.0 and precompacts() == n0 + 1, "%.1fs" % dt)

    # DT13 잠금을 못 잡으면(동기 상한 20초) 무잠금 실행도 폐기도 아니다 — 입력을 큐에 넘기고 hook-errors 1줄(R2 codex I4)
    n0 = precompacts()
    sl = holder(40)
    lk = hold_lock("save-state", sl.pid)
    dt = run_pre()
    errs = read(os.path.join(st, "hook-errors.log")) if os.path.exists(os.path.join(st, "hook-errors.log")) else ""
    sq = os.path.join(hd, "save-state.q")
    check("DT13 잠금 대기 20초 초과 = 그 자리 실행 0 · 입력은 큐에 1장 · hook-errors rc=124 「큐에 넘김」",
          19 <= dt < 30 and precompacts() == n0 and os.path.isdir(sq) and len(os.listdir(sq)) == 1
          and "save-state" in errs and "rc=124" in errs and "큐에 넘김" in errs,
          "%.1fs · %s · %s" % (dt, os.listdir(sq) if os.path.isdir(sq) else None, errs[-200:]))
    sl.kill()
    r = subprocess.run(["sh", "-c", '. "$1"; cys_hook_detach_wait save-state 15 "$2"', "x", lib, ss], env=env,
                       capture_output=True, text=True, timeout=60)
    check("DT13b 주인이 죽은 뒤 넘긴 입력이 처리된다(유실 0 · 죽은 주인 잠금 회수)",
          r.returncode == 0 and precompacts() == n0 + 1 and not os.listdir(sq), "rc=%s" % r.returncode)
    shutil.rmtree(lk, ignore_errors=True)

    # DT14 자식 본문 데드라인: memory verify 가 멎어도 30초에 끊고 hook-errors 124 · 정합 경고(WARN:memory)는 쓰지 않는다
    mem = os.path.join(pk, "bin", "javis_memory.py")
    shutil.copyfile(mem, mem + ".orig")
    with open(mem, "w") as f:
        f.write("import time\ntime.sleep(45)\n")
    t0 = time.time()
    subprocess.run(["sh", os.path.join(pk, "hooks", "reflect-scan.sh")], input=stop,
                   env=dict(env, SLOW="0", CYS_HOOK_STOP_SYNC="1"), capture_output=True, text=True, timeout=120)
    dt = time.time() - t0
    errs = read(os.path.join(st, "hook-errors.log")) if os.path.exists(os.path.join(st, "hook-errors.log")) else ""
    check("DT14 memory verify 30초 데드라인 → 124 기록 · WARN:memory 없음",
          28 <= dt < 40 and "memory verify 30초" in errs and "WARN:memory" not in read(slog), "%.1fs" % dt)
    shutil.move(mem + ".orig", mem)
    detach_queue_cases(h, pk, work, env, stop, led)


def detach_queue_cases(h, pk, work, env, stop, led):
    """R2 수리(codex major I2·I3·I4): 영속 큐 + 배수기 하나 · 회수자 직렬화 · 소비자 세대 대조."""
    import threading
    st = os.path.join(h, ".cys", "state")
    hd = os.path.join(st, "hook-detach")
    lib = os.path.join(pk, "hooks", "_lib.sh")
    rs = os.path.join(pk, "hooks", "reflect-scan.sh")
    ss = os.path.join(pk, "hooks", "save-state.sh")
    slog = os.path.join(work, "_round", ".state_log")
    errf = os.path.join(st, "hook-errors.log")

    def errs():
        return read(errf) if os.path.exists(errf) else ""

    def lines():
        return read(led).splitlines() if os.path.exists(led) else []

    def until(pred, sec):
        end = time.time() + sec
        while time.time() < end and not pred():
            time.sleep(0.2)
        return pred()

    # DT15(I4) 긴 본문 중에 들어온 표는 버려지지 않는다 — 깨우기는 살아 있는 배수기에 물러나고, 그 배수기가 큐를 끝까지 돈다
    if os.path.exists(led):
        os.remove(led)
    e0 = errs().count("rc=124")
    tl = os.path.join(st, "hook-timing.log")
    t_0 = len(read(tl).splitlines()) if os.path.exists(tl) else 0
    for _ in range(3):
        subprocess.run(["sh", rs], input=stop, env=dict(env, SLOW="3"), capture_output=True, text=True, timeout=30)
    ok = until(lambda: len(lines()) == 3, 30)

    def drains():
        new_tl = read(tl).splitlines()[t_0:] if os.path.exists(tl) else []
        return [l for l in new_tl if "reflect-scan(drain)" in l]

    def long_drain():
        return [l for l in drains() if l.rsplit(" ", 1)[-1].rstrip("s").isdigit()
                and int(l.rsplit(" ", 1)[-1].rstrip("s")) >= 5]
    until(long_drain, 10)                        # 배수기의 계측 줄은 마지막 본문 뒤 해제·재확인을 마치고 남는다
    check("DT15 연속 Stop 3건(본문 3초) = 산출물 3줄 · 한 배수기가 뒤 표까지 돈다 · 잠금 대기 오류 0",
          ok and long_drain() and errs().count("rc=124") == e0, "%s · %s" % (lines(), drains()))

    # DT16(I2) 회수자 직렬화 — 다른 회수자가 안에 있는 동안(.reap) 죽은 주인 잠금을 지우지 않는다 · 3초 넘게 남은 .reap 만 치운다
    n0 = read(slog).count("\tPreCompact\t")
    lk = os.path.join(hd, "save-state.lock")
    os.makedirs(lk, exist_ok=True)
    write(os.path.join(lk, "pid"), "999999")
    os.makedirs(lk + ".reap", exist_ok=True)
    t0 = time.time()
    subprocess.run(["sh", ss], input=json.dumps({"hook_event_name": "PreCompact", "cwd": work, "trigger": "auto"}),
                   env=env, capture_output=True, text=True, timeout=60)
    dt = time.time() - t0
    check("DT16 회수 중인 회수자가 있으면 기다린다(3~8초) → 남은 .reap 치우고 회수 · 기록 1",
          3.0 <= dt < 8.0 and read(slog).count("\tPreCompact\t") == n0 + 1 and not os.path.exists(lk + ".reap"),
          "%.1fs" % dt)
    # 동시 진입 0 — 죽은 주인 잠금 하나를 8개가 동시에 회수·획득해도 보호 구간이 겹치지 않는다
    os.makedirs(lk, exist_ok=True)
    write(os.path.join(lk, "pid"), "999999")
    trace = os.path.join(h, "dt16.trace")
    body = ('. "$1"; cys_hook_detach_acquire save-state 30 || exit 3; echo "+ $$" >> "$2"; sleep 0.3; '
            'echo "- $$" >> "$2"; cys_hook_detach_release')
    ps = [subprocess.Popen(["sh", "-c", body, "x", lib, trace], env=env) for _ in range(8)]
    rcs = [p.wait(timeout=90) for p in ps]
    tr_lines = read(trace).splitlines() if os.path.exists(trace) else []
    paired = len(tr_lines) == 16 and all(tr_lines[i][0] == "+" and tr_lines[i + 1] == "-" + tr_lines[i][1:]
                                         for i in range(0, len(tr_lines), 2))
    check("DT16b 죽은 주인 잠금에 8개 동시 획득 = 보호 구간 겹침 0 · 전원 획득 · 잠금 해제",
          paired and rcs == [0] * 8 and not os.path.exists(lk), "%s %s" % (rcs, tr_lines[:6]))

    # DT17(I3) 소비자 세대 대조 — 시작 시각 이전 표가 처리 중이면(살아 있는 주인) 상한 뒤 rc 1 · inject-context 는 이전 스냅샷을 싣지 않는다
    sq = os.path.join(hd, "save-state.q")
    os.makedirs(sq, exist_ok=True)
    sl = subprocess.Popen(["sleep", "40"])
    threading.Thread(target=sl.wait, daemon=True).start()
    os.makedirs(lk, exist_ok=True)
    write(os.path.join(lk, "pid"), str(sl.pid))
    tk = os.path.join(sq, "%d.1" % (int(time.time()) - 1))
    write(tk, json.dumps({"hook_event_name": "Stop", "cwd": work, "session_id": "s"}))
    r = subprocess.run(["sh", "-c", '. "$1"; cys_hook_detach_wait save-state 3', "x", lib], env=env,
                       capture_output=True, text=True, timeout=60)
    check("DT17 처리 중인 이전 표 = 상한 뒤 rc 1", r.returncode == 1, "rc=%s" % r.returncode)
    write(os.path.join(work, "_round", "SESSION_STATE.md"), "# state\n")
    write(os.path.join(work, "_round", "BOOT_SNAPSHOT.md"), "OLD-SNAPSHOT-MARK\n")
    snp = os.path.join(pk, "bin", "javis_snapshot.py")
    shutil.copyfile(snp, snp + ".orig")
    with open(snp, "w") as f:
        f.write("import sys\nsys.exit(0)\n")
    ic = os.path.join(pk, "hooks", "inject-context.sh")
    ssn = json.dumps({"hook_event_name": "SessionStart", "cwd": work, "session_id": "s", "source": "clear"})
    t0 = time.time()
    r = subprocess.run(["sh", ic], input=ssn, env=env, capture_output=True, text=True, timeout=60)
    dt = time.time() - t0
    check("DT17b inject-context: save-state 가 12초 안에 안 끝나면 이전 스냅샷 생략 + 고지",
          "OLD-SNAPSHOT-MARK" not in r.stdout and "스냅샷 생략" in r.stdout and 11.0 <= dt < 25.0,
          "%.1fs · %s" % (dt, r.stdout[-300:]))
    sl.kill()
    sl.wait()
    os.remove(tk)
    r = subprocess.run(["sh", ic], input=ssn, env=env, capture_output=True, text=True, timeout=60)
    check("DT17c 큐가 비면 즉시 스냅샷 주입(종전대로)", "OLD-SNAPSHOT-MARK" in r.stdout, r.stdout[-300:])
    shutil.move(snp + ".orig", snp)
    os.remove(os.path.join(work, "_round", "SESSION_STATE.md"))
    shutil.rmtree(lk, ignore_errors=True)

    # DT18 동기 주인은 해제 뒤 큐를 다시 본다 — 동기 본문 중에 들어온 Stop 표(깨우기가 물러남)를 배수기를 깨워 처리시킨다
    if os.path.exists(led):
        os.remove(led)
    pa = subprocess.Popen(["sh", rs], stdin=subprocess.PIPE, env=dict(env, CYS_HOOK_STOP_SYNC="1", SLOW="3"),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    pa.stdin.write(stop)
    pa.stdin.close()
    time.sleep(1.0)
    subprocess.run(["sh", rs], input=stop, env=dict(env, SLOW="0"), capture_output=True, text=True, timeout=30)
    pa.wait(timeout=60)
    check("DT18 동기 본문 중 들어온 Stop 표 = 동기 주인이 해제 뒤 깨워 처리(산출물 2줄)",
          until(lambda: len(lines()) == 2, 15), str(lines()))

    # DT19 배수기는 해제 뒤 큐를 다시 본다 — 마지막 확인과 해제 사이에 들어온 표(그 깨우기는 잠금에 막혀 물러났다)를 줍는다
    fake = os.path.join(h, "fake-hook.sh")
    out = os.path.join(h, "dt19.out")
    write(fake, '#!/bin/sh\ncat >> "%s"; echo >> "%s"\n' % (out, out))
    harness = ('. "$1"; _n=0; '
               'cys_hook_detach_release() { [ -n "${_cys_hd_held:-}" ] && rm -rf "$_cys_hd_held"; _cys_hd_held=""; '
               'if [ "$_n" -eq 0 ]; then _n=1; cys_hook_detach_enqueue dt19 LATE >/dev/null; fi; }; '
               'cys_hook_detach_enqueue dt19 FIRST >/dev/null; cys_hook_detach_drain dt19 "$2"')
    r = subprocess.run(["sh", "-c", harness, "x", lib, fake], env=env, capture_output=True, text=True, timeout=60)
    got = read(out).split() if os.path.exists(out) else []
    check("DT19 해제 뒤 재확인 — 마지막 확인 뒤 들어온 표도 처리(FIRST·LATE)",
          got == ["FIRST", "LATE"], "%s · %s" % (got, r.stderr[-200:]))


def main():
    out = None
    if "--diff-out" in sys.argv:
        out = sys.argv[sys.argv.index("--diff-out") + 1]
    if not os.path.isfile(BIN):
        print("SKIP — cys 바이너리 없음(%s) · cargo build --bin cys 후 재실행" % BIN)
        return 0
    only = os.environ.get("HOOKSLIM_ONLY", "")       # 뮤턴트 실행용: "hooks" = 셸 훅 부분만 · "seat" = 좌석 프로필 상태표(S12)만
    if only == "seat":
        seat_cases()
    else:
        if only != "hooks":
            s_cases()
            seat_cases()
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
