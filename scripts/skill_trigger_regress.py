#!/usr/bin/env python3
"""스킬 발동 회귀 시험 (TICKET=cysr-1112-skill-fold).

대표 한국어 요청 문장(skill_trigger_cases.json)을 격리 프로젝트에서 `claude -p` 로 돌려
모델이 처음 성공적으로 부른 Skill 이름을 정답 집합과 대조한다.

격리:
  · 시험 프로젝트 = <out>/proj · 스킬 = <skills 폴더> 를 proj/.claude/skills 로 복사
  · --setting-sources project → 사용자 프로필의 스킬 링크·훅·CLAUDE.md 를 읽지 않는다
  · disableAllHooks · CYS_* 환경변수 제거(좌석 훅·역할 등록이 돌지 않게)
  · 허용 도구 = Skill 뿐(파일·명령 부작용 0)
  · 로그인은 실행 좌석의 CLAUDE_CONFIG_DIR 그대로(새 설정 폴더는 로그인이 없다 —
    토큰 복사는 갱신 토큰 회전으로 실좌석 로그인을 깰 수 있어 하지 않는다)

채점: 첫 Skill 호출 중 오류가 아닌 것의 이름 ∈ ok 이면 일치. 오류(예: 수동 전용 스킬을
      모델이 부름)는 불일치로 센다.

쓰임:
  python3 scripts/skill_trigger_regress.py <skills 폴더> <out 폴더> [--model M] [--jobs N] [--ids 1,2]
"""
import concurrent.futures as cf
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def prepare(skills: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    proj = out / "proj"
    if proj.exists():
        shutil.rmtree(proj)
    (proj / ".claude").mkdir(parents=True)
    shutil.copytree(skills, proj / ".claude" / "skills",
                    ignore=shutil.ignore_patterns("_*", "*.md.bak"))
    (proj / ".claude" / "settings.json").write_text('{"disableAllHooks": true}\n')
    subprocess.run(["git", "init", "-q"], cwd=proj, check=False)
    return proj


def run_case(proj: pathlib.Path, out: pathlib.Path, case: dict, model: str) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("CYS_") and k != "NODE_OPTIONS"}
    cmd = ["claude", "-p", "--setting-sources", "project",
           "--settings", '{"disableAllHooks":true}',
           "--model", model, "--output-format", "stream-json", "--verbose",
           "--max-turns", "2", "--allowedTools", "Skill"]  # 문장은 stdin(가변 인자 흡수 방지)
    log = out / f"case{case['id']:02d}.jsonl"
    with open(log, "w") as fh, open(log.with_suffix(".err"), "w") as eh:
        subprocess.run(cmd, cwd=proj, env=env, stdout=fh, stderr=eh,
                       input=case["text"], text=True, timeout=600)
    calls, errors = [], {}
    for line in log.read_text().splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        msg = d.get("message") if isinstance(d.get("message"), dict) else {}
        for c in msg.get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use" and c.get("name") == "Skill":
                name = str((c.get("input") or {}).get("skill", "")).split(":")[-1].lstrip("/")
                calls.append((c.get("id"), name))
            if c.get("type") == "tool_result" and c.get("is_error"):
                errors[c.get("tool_use_id")] = True
    first = next((n for i, n in calls if not errors.get(i)), None)
    return {"id": case["id"], "text": case["text"], "ok": case["ok"],
            "calls": [n + (" (오류)" if errors.get(i) else "") for i, n in calls],
            "first": first, "match": first in case["ok"]}


def main(argv: list) -> int:
    skills, out = pathlib.Path(argv[0]).resolve(), pathlib.Path(argv[1]).resolve()
    model = argv[argv.index("--model") + 1] if "--model" in argv else "claude-opus-5-5"
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 5
    cases = json.loads((HERE / "skill_trigger_cases.json").read_text())["cases"]
    if "--ids" in argv:
        want = {int(x) for x in argv[argv.index("--ids") + 1].split(",")}
        cases = [c for c in cases if c["id"] in want]
    out.mkdir(parents=True, exist_ok=True)
    proj = prepare(skills, out)
    with cf.ThreadPoolExecutor(jobs) as ex:
        rows = sorted(ex.map(lambda c: run_case(proj, out, c, model), cases),
                      key=lambda r: r["id"])
    hit = sum(r["match"] for r in rows)
    (out / "result.json").write_text(json.dumps(
        {"model": model, "skills": str(skills), "match": hit, "total": len(rows),
         "rows": rows}, ensure_ascii=False, indent=1))
    for r in rows:
        print(f'{r["id"]:2d} {"O" if r["match"] else "X"} {r["first"]!s:32} {r["calls"]}')
    print(f"일치 {hit}/{len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
