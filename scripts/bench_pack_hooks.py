#!/usr/bin/env python3
"""팩 훅 실행 시간 실측(TICKET=hook-slim-1111) — 격리 HOME · 대표 stdin JSON · N회 p50/p95/max.

사용(맥): python3 -I scripts/bench_pack_hooks.py --pack cysjavis-pack --transcript <기록.jsonl> --out r.json [--n 20]
          [--scenario plain|seat] [--round] [--memory ~/.cys/pack/memory]
사용(윈 · Git Bash 의 bash 로 훅을 돌린다): py -3 -I scripts\bench_pack_hooks.py --shell bash --pack cysjavis-pack ...
· 격리 HOME = 임시 디렉터리(실 설정·실 state 무접촉). 팩은 그 안 ~/.cys/pack 에 복사한다.
· plain = 사용자의 개인 Claude 세션(좌석 env 없음 · 원작자 진단 대상). seat = cys 좌석 env(CYS_ROLE·CYS_SURFACE_ID).
· 각 훅은 settings 에 등록된 형태 그대로 `sh <hook>` 로 돈다.
"""
import argparse, json, os, platform, shutil, statistics, subprocess, sys, tempfile, time

# (스크립트, 이벤트, matcher 예 도구) — ~/.claude/settings.json 실측 등록 20행(10-27 00:1x)과 같은 집합
HOOKS = [
    ("cys-hook.sh", "PreToolUse", "Bash"),
    ("cys-hook.sh", "PostToolUse", "Bash"),
    ("cys-hook.sh", "PermissionRequest", "Bash"),
    ("directive-event-inject.sh", "PreToolUse", "Bash"),
    ("appbuild-gate.sh", "PreToolUse", "Edit"),
    ("grill-gate.sh", "PreToolUse", "Edit"),
    ("grill-arm.sh", "PreToolUse", "Skill"),
    ("commit-memory-nudge.sh", "PostToolUse", "Bash"),
    ("grill-count.sh", "PostToolUse", "AskUserQuestion"),
    ("pack-guard.sh", "PostToolUse", "Edit"),
    ("save-state.sh", "Stop", None),
    ("reflect-scan.sh", "Stop", None),
    ("grill-stop.sh", "Stop", None),
    ("save-state.sh", "PreCompact", None),
    ("reflect-scan.sh", "SessionEnd", None),
    ("session-start.sh", "SessionStart", None),
    ("inject-context.sh", "SessionStart", None),
    ("inject-background.sh", "SessionStart", None),
    ("role-bootstrap.sh", "UserPromptSubmit", None),
    ("dept-chat-inject.sh", "UserPromptSubmit", None),
]


def payload(event, tool, cwd, transcript):
    d = {"session_id": "bench-0000", "transcript_path": transcript, "cwd": cwd,
         "hook_event_name": event, "permission_mode": "default"}
    if event in ("PreToolUse", "PostToolUse", "PermissionRequest"):
        d["tool_name"] = tool
        if tool == "Bash":
            d["tool_input"] = {"command": "git status", "description": "status"}
        elif tool == "Edit":
            d["tool_input"] = {"file_path": os.path.join(cwd, "src", "app.py"),
                               "old_string": "a = 1", "new_string": "a = 2"}
        elif tool == "Skill":
            d["tool_input"] = {"skill": "simplify"}
        elif tool == "AskUserQuestion":
            d["tool_input"] = {"questions": [{"question": "q?", "header": "h", "options": []}]}
        if event == "PostToolUse":
            d["tool_response"] = {"stdout": "On branch main\n" * 40, "stderr": "", "interrupted": False}
    elif event == "Stop":
        d["stop_hook_active"] = False
    elif event == "PreCompact":
        d["trigger"] = "auto"; d["custom_instructions"] = ""
    elif event == "SessionEnd":
        d["reason"] = "prompt_input_exit"
    elif event == "SessionStart":
        d["source"] = "startup"
    elif event == "UserPromptSubmit":
        d["prompt"] = "이 함수의 버그를 찾아 고쳐 줘"
    return json.dumps(d, ensure_ascii=False)


def pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True)
    ap.add_argument("--memory", default="")
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--scenario", choices=["plain", "seat"], default="plain")
    ap.add_argument("--only", default="")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--shell", default="sh", help="훅을 돌릴 셸(윈 = Git Bash 의 bash)")
    ap.add_argument("--round", action="store_true", help="작업 폴더에 _round 를 둔다(팩 프로젝트 폴더)")
    a = ap.parse_args()

    home = tempfile.mkdtemp(prefix="hookbench-home-")
    pack = os.path.join(home, ".cys", "pack")
    shutil.copytree(a.pack, pack, symlinks=True,
                    ignore=shutil.ignore_patterns("tests", "__pycache__", ".pytest_cache"))
    if a.memory:
        shutil.rmtree(os.path.join(pack, "memory"), ignore_errors=True)
        shutil.copytree(a.memory, os.path.join(pack, "memory"))
    os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
    proj = os.path.join(home, "work", "myproj")
    os.makedirs(os.path.join(proj, "src"), exist_ok=True)
    if a.round:
        os.makedirs(os.path.join(proj, "_round"), exist_ok=True)
    tr = os.path.join(home, "transcript.jsonl")
    shutil.copyfile(a.transcript, tr)

    env = {"HOME": home, "USERPROFILE": home, "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""), "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "LANG": "ko_KR.UTF-8", "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
           "USER": os.environ.get("USER", "u"), "SHELL": "/bin/zsh", "CYS_NO_AUTOSTART": "1"}
    if a.scenario == "seat":
        env.update({"CYS_ROLE": "worker", "CYS_SURFACE_ID": "999", "CYS_PACK_DIR": pack,
                    "CLAUDE_CONFIG_DIR": os.path.join(home, ".cys", "claude")})
        os.makedirs(env["CLAUDE_CONFIG_DIR"], exist_ok=True)

    rows = []
    for script, event, tool in HOOKS:
        if a.only and script not in a.only.split(","):
            continue
        path = os.path.join(pack, "hooks", script)
        data = payload(event, tool, proj, tr).encode()
        xs, rcs, outlen = [], set(), 0
        for i in range(a.n + 1):          # 1회 예열(첫 회 버림 — 디스크 캐시 냉시작 분리)
            t0 = time.perf_counter()
            p = subprocess.run([a.shell, path], input=data, env=env, cwd=proj,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=700)
            dt = (time.perf_counter() - t0) * 1000
            if i == 0:
                cold = dt
                continue
            xs.append(dt); rcs.add(p.returncode); outlen = max(outlen, len(p.stdout))
        rows.append({"hook": script, "event": event, "tool": tool, "n": len(xs),
                     "cold_ms": round(cold, 1),
                     "p50_ms": round(statistics.median(xs), 1), "p95_ms": round(pct(xs, .95), 1),
                     "max_ms": round(max(xs), 1), "rc": sorted(rcs), "stdout_max_b": outlen})
        print("%-28s %-18s p50=%7.1f p95=%7.1f max=%7.1f cold=%7.1f rc=%s out=%d" % (
            script, event, rows[-1]["p50_ms"], rows[-1]["p95_ms"], rows[-1]["max_ms"],
            cold, sorted(rcs), outlen), flush=True)
    meta = {"scenario": a.scenario, "round": a.round, "n": a.n, "home": home,
            "transcript_bytes": os.path.getsize(tr), "python": sys.version.split()[0],
            "uname": platform.platform(), "shell": a.shell, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    json.dump({"meta": meta, "rows": rows}, open(a.out, "w"), ensure_ascii=False, indent=1)
    if not a.keep:
        shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    main()
