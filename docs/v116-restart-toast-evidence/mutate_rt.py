"""v116-restart-toast 뮤턴트 — 한 줄씩 부수고 단위 시험 + 헤드리스(실번들)가 잡는지 잰다.

usage: CHS=<chrome-headless-shell> python3 mutate_rt.py [M1 M2 ...]
KILLED = 단위 시험 또는 헤드리스 중 하나라도 실패 · SURVIVED = 둘 다 통과(시험 구멍).
각 뮤턴트 뒤 원문을 되돌리고(finally) 마지막에 원문 일치를 확인한다.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
UI = os.path.join(ROOT, "ui")
HL = os.path.join(ROOT, "docs", "v116-ui-evidence", "v116-headless.ts")
BUN = os.path.expanduser("~/.bun/bin/bun")
env = dict(os.environ, PATH=os.path.expanduser("~/.bun/bin") + ":" + os.environ["PATH"])

# (id, 파일, 원문, 뮤턴트, 헤드리스 칸)
M = [
    ("M1 대기 기억 줄 제거", "src/main.ts", "  restartPendingVersion = version;\n  paintRestartPending();", "  paintRestartPending();", "c17"),
    ("M2 단추 분기 뒤집기(대기인데 확인·설치)", "src/main.ts", 'if (updateButtonAction(restartPendingVersion) === "restart") return', 'if (updateButtonAction(restartPendingVersion) === "check") return', "c17"),
    ("M3 확인 머리 가드 무력화", "src/main.ts", "  if (restartPendingVersion !== null) {\n    paintRestartPending();\n    return;\n  }\n  // 1)", "  if (restartPendingVersion !== null) {\n    paintRestartPending();\n  }\n  // 1)", "c17"),
    ("M4 재진입 플래그 안 세움", "src/main.ts", "  restartingAfterUpdate = true;\n  try {\n    await restartAfterUpdateOnce", "  try {\n    await restartAfterUpdateOnce", "c17"),
    ("M5 재진입 플래그 안 풂(finally 제거)", "src/main.ts", "  } finally {\n    restartingAfterUpdate = false;\n  }", "  } finally {\n  }", "c17"),
    ("M6 설치 직전 가드 제거", "src/main.ts", "  if (restartPendingVersion !== null) return restartAfterUpdate(restartPendingVersion);\n", "", "c17x"),
    ("M7 판번 짝 무효화 제거(decode)", "src/restartpending.ts", "  if (appVersion !== currentAppVersion) return null;\n", "", "c17"),
    ("M8 새 판 == 지금 판 무효화 제거(decode)", "src/restartpending.ts", "  if (version === currentAppVersion) return null;\n", "", "c17"),
    ("M9 ⌘R 사본 저장 안 함", "src/main.ts", "      if (appVer) sessionStorage.setItem(RESTART_PENDING_KEY, encodeRestartPending(version, appVer, buildId));\n", "", "c17"),
    ("M10 복원이 메모리 값을 덮음", "src/main.ts", "    if (restartPendingVersion === null) restartPendingVersion = v;", "    restartPendingVersion = v;", "c17x"),
    ("M12 build_id 짝 무시(같은 판 재빌드 = 옛 판번 규칙으로 무효)", "src/restartpending.ts", "  if (knownBuild(buildId) && knownBuild(currentBuildId)) return buildId.trim() === currentBuildId.trim() ? version : null;\n", "", "c17x"),
    ("M13 build_id 달라도 유효(새 앱에서 거짓 대기)", "src/restartpending.ts", "buildId.trim() === currentBuildId.trim() ? version : null;", "version;", "c17x"),
    ("M14 확인 응답 뒤 재확인 제거", "src/main.ts", "  // 확인을 기다리는 사이 교체가 끝났으면(이벤트) 설치 안내·설치 확인 창으로 덮지 않는다(클로드 적대 1R #2).\n  if (restartPendingVersion !== null) {\n    paintRestartPending();\n    return;\n  }\n", "", "c17x"),
    ("M15 단추가 복원을 안 기다림", "src/main.ts", "  await restoreRestartPending();\n  if (updateButtonAction", "  if (updateButtonAction", "c17x"),
    ("M16 팩 적용 완료 뒤 다시 칠하기 제거", "src/main.ts", "    paintRestartPending(); // 맥 교체 뒤 다시 켜기 대기면", "    // 맥 교체 뒤 다시 켜기 대기면", "c17x"),
    ("M17 배지 칠하기 제거", "src/main.ts", "  badge.hidden = false;\n  badge.textContent = \"!\";\n  badge.classList.remove(\"ok\");\n", "", "c17"),
    ("M18 무효 기억 칸 삭제 안 함", "src/main.ts", "        sessionStorage.removeItem(RESTART_PENDING_KEY);\n", "", "c17"),
    ("M11 판번 조회 실패에도 기억 삭제(agy 1R #2 되돌림)", "src/main.ts", "    if (!appVer) return;\n    const buildId", "    const buildId", "c17x"),
]


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=900)
    return p.returncode, (p.stdout + p.stderr)


def main():
    only = set(sys.argv[1:])
    results = []
    originals = {}
    for mid, rel, old, new, cells in M:
        if only and mid.split()[0] not in only:
            continue
        path = os.path.join(UI, rel)
        src = open(path, encoding="utf-8").read()
        originals.setdefault(path, src)
        n = src.count(old)
        if n != 1:
            results.append((mid, f"INVALID(원문 {n}회)", "", ""))
            continue
        try:
            open(path, "w", encoding="utf-8").write(src.replace(old, new))
            urc, uout = run([BUN, "test", "src/restartpending.test.ts", "src/updatebutton.test.ts"], UI)
            brc, bout = run(["sh", "build.sh"], UI)
            if brc != 0:
                results.append((mid, "KILLED(빌드)", "", bout[-300:]))
                continue
            henv = dict(env, DIST=os.path.join(UI, "dist"), ONLY=cells)
            p = subprocess.run([BUN, HL], cwd=os.path.dirname(HL), env=henv, capture_output=True, text=True, timeout=900)
            hrc, hout = p.returncode, p.stdout + p.stderr
            hfails = [l.split()[1] for l in hout.splitlines() if l.startswith("FAIL c")]
            ufail = [l.strip() for l in uout.splitlines() if l.strip().startswith("(fail)")]
            killed = urc != 0 or hrc != 0
            results.append((mid, "KILLED" if killed else "SURVIVED", f"단위 실패 {len(ufail)}", "헤드리스 실패 " + (" · ".join(hfails) or "0")))
        finally:
            open(path, "w", encoding="utf-8").write(src)
    for path, src in originals.items():
        assert open(path, encoding="utf-8").read() == src, f"원문 복원 실패: {path}"
    run(["sh", "build.sh"], UI)  # dist 를 원문으로 되돌린다
    for r in results:
        print(" | ".join(r))
    k = sum(1 for r in results if r[1].startswith("KILLED"))
    print(f"KILLED {k}/{len(results)}")
    return 0 if k == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
