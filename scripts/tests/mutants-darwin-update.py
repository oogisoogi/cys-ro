#!/usr/bin/env python3
"""뮤턴트 배터리 — 맥 업데이트(B7)·데몬 교체 안내(B15)·옛 자리 정리(B17)의 새 검사 축이
**실제로 잡는지**를 잰다. TICKET=v110-darwin-update.

규율(저장소 선례를 따른다):
  · 변이는 **의미를 바꾸는 실행 가능한 코드**여야 한다 — 문법을 깨는 변이의 적색은 공짜 KILLED 다.
  · 변이 적용을 먼저 단언한다(치환 0건이면 NOT-APPLIED = 측정 실패이지 통과가 아니다).
  · 복원은 finally 에서 한다 — 도중에 죽어도 트리에 변이가 남지 않는다.
  · 기대 적색이 안 나오면 그 축은 **그물이 없는 것**이므로 rc≠0 으로 끝낸다.

사용: python3 scripts/tests/mutants-darwin-update.py [--only <id>]
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARGO = os.path.expanduser("~/.cargo/bin/cargo")

MAC = "src-tauri/src/macupdate.rs"
MAIN = "src-tauri/src/main.rs"
SWEEP = "ui/src/exitedsweep.ts"
LABELS = "ui/src/headerlabels.ts"
ROWGEN = "scripts/make-darwin-update-row.py"

RUST = [CARGO, "test", "-p", "cys-app"]
BUN = ["bun", "test", "ui/src"]
PYROW = [sys.executable, "scripts/tests/test_darwin_update_row.py"]

# (id, 파일, 찾을 것, 바꿀 것, 돌릴 명령, 이 변이가 죽어야 하는 축)
MUTANTS = [
    ("m1-size", MAC,
     "    if actual == expected {\n        Ok(())",
     "    if true {\n        Ok(())",
     RUST + ["macupdate"], "크기 검증"),
    ("m2-sha", MAC,
     "    let e = expected.trim().to_lowercase();\n    if a == e {",
     "    let e = expected.trim().to_lowercase();\n    if true || a == e {",
     RUST + ["macupdate"], "sha256 검증"),
    ("m3-cdhash-missing", MAC,
     "        None => Err(UpdateFail::CdHash {\n            expected,\n            actual: \"(읽지 못함)\".to_string(),\n        }),",
     "        None => Ok(()),",
     RUST + ["macupdate"], "CDHash 를 못 읽었을 때(측정 불능≠통과)"),
    ("m4-codesign", MAC,
     "pub fn classify_codesign(success: bool, stderr: &str) -> Result<(), UpdateFail> {\n    if success {",
     "pub fn classify_codesign(success: bool, stderr: &str) -> Result<(), UpdateFail> {\n    if true {",
     RUST + ["macupdate"], "codesign 봉인 검증"),
    ("m5-interrupt", MAC,
     "        Some(c) => Err(UpdateFail::Interrupted(format!(",
     "        Some(_c) if false => Err(UpdateFail::Interrupted(format!(",
     RUST + ["macupdate"], "다운로드 중단"),
    ("m6-field-failclosed", MAC,
     "        .ok_or_else(|| UpdateFail::Field(key.to_string()))",
     "        .or(Some(String::new()))\n        .ok_or_else(|| UpdateFail::Field(key.to_string()))",
     RUST + ["macupdate"], "검증 칸 결손의 fail-closed"),
    ("m7-w3-seal", MAIN,
     "    let _ = tokio::task::spawn_blocking(|| sealed_sidecar_cys(&[\"drain\"]).status()).await;\n    let _ = app.emit(\"update-progress\", json!({\"phase\": \"handoff\"}));\n    let _ = std::fs::write(pending_restore_path(), \"\");\n    stop_running_daemon().await;\n    app.restart();",
     "    let _ = tokio::task::spawn_blocking(|| std::process::Command::new(resolve_sidecar(\"cys\")).arg(\"drain\").status()).await;\n    let _ = app.emit(\"update-progress\", json!({\"phase\": \"handoff\"}));\n    let _ = std::fs::write(pending_restore_path(), \"\");\n    stop_running_daemon().await;\n    app.restart();",
     RUST + ["gui_spec_w3"], "재시작 경로의 봉인 조립점(조준 이사 뒤에도 무는가)"),
    ("m8-sweep-armed", SWEEP,
     "  if (!armed) return [];",
     "  if (false) return [];",
     BUN, "복원 직후 1회 무장(평시 스윕 금지)"),
    # ★m9 개정(2026-09-20): 초판은 `surfaces.length === 0` 가드를 겨눴는데 SURVIVED 였다 —
    #   그 줄이 **아무것도 지키지 않는 줄**이었기 때문이다(빈 목록에서는 고를 것이 원리적으로 없다).
    #   줄을 걷어내고, 그 성질을 실제로 떠받치는 것(술어의 방향)을 겨눈다.
    ("m9-sweep-direction", SWEEP,
     "  return treeSids.filter((sid) => exited.has(sid));",
     "  return treeSids.filter((sid) => !exited.has(sid));",
     BUN, "빈 목록 = 판정 보류 · 「있고 exited 인 것만」 방향"),
    ("m10-daemon-ver", LABELS,
     "  const v = ver ? `v${ver} ` : \"\";",
     "  const v = \"\";",
     BUN, "데몬 판번 상시 표시"),
    ("m11-row-signature", ROWGEN,
     "        \"signature\": \"\",",
     "        # signature 칸을 뺀다(윈도 업데이트를 죽이는 그 결손)\n",
     PYROW, "latest.json 행의 signature 키 존재"),
]


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    a = ap.parse_args()
    rows = [m for m in MUTANTS if not a.only or m[0] == a.only]
    failures = []
    for mid, rel, old, new, cmd, axis in rows:
        path = os.path.join(ROOT, rel)
        src = open(path, encoding="utf-8").read()
        n = src.count(old)
        if n != 1:
            print(f"[{mid}] NOT-APPLIED — 앵커가 {n} 곳({rel}). 측정 실패다(통과 아님).")
            failures.append((mid, "NOT-APPLIED"))
            continue
        try:
            open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
            # 변이가 실제로 들어갔는지 먼저 단언한다.
            assert open(path, encoding="utf-8").read() != src
            p = run(cmd)
            killed = p.returncode != 0
            print(f"[{mid}] {'KILLED' if killed else 'SURVIVED'} — {axis}")
            if not killed:
                failures.append((mid, "SURVIVED"))
                print((p.stdout or "")[-600:])
        finally:
            open(path, "w", encoding="utf-8").write(src)
    # 복원 실측 — 트리에 변이가 남지 않았음을 스스로 확인한다.
    dirty = run(["git", "status", "--porcelain"]).stdout
    print("\n== 변이 복원 후 작업트리 ==\n" + (dirty or "(변경 없음)"))
    if failures:
        print(f"\n실패 {len(failures)}건: {failures}")
        return 1
    print(f"\n전건 KILLED ({len(rows)}건) — 새 검사 축이 전부 문다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
