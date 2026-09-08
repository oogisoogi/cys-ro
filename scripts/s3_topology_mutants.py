#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s3_topology_mutants.py — TICKET=cys-phoenix-s3-master-persist 뮤테이션 검산

무엇을 재는가: S3 수리(persist_topology 의 「살아있지 않다고 지우지 않는다」)를 되돌렸을 때
  검사 축이 **실제로 적색이 되는가.** 통과만 보고는 그 축이 무엇을 재는지 알 수 없다.

각 뮤턴트: 백업 → 정확히 한 곳 되돌리기(치환 건수 assert) → 검사 실행 → 종료코드 판정 →
          finally 원복(예외·중단에도).
어휘: KILLED=잡았다 · SURVIVED=그 축은 공허하다 · NOT-APPLIED=변이가 적용조차 안 됨(측정 실패).
exit: 0=전건 KILLED · 1=SURVIVED 있음 · 2=측정 실패.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOV = os.path.join(ROOT, "src", "bin", "cysd", "governance.rs")
CARGO = os.environ.get("CARGO", os.path.expanduser("~/.cargo/bin/cargo"))
BUILD = [CARGO, "build", "--bin", "cysd", "--bin", "cys"]
# ★프로브는 target/debug 바이너리를 돌린다 — 변이를 **빌드해 넣지 않으면** 옛 바이너리를 재고
#   그 축은 상시 초록이 된다(초판이 정확히 그랬다: M1·M2 를 프로브가 하나도 못 잡았고, 잡은 것은
#   스스로 재빌드하는 cargo test 뿐이었다). 그래서 프로브 축은 빌드를 자기 앞에 달고 다닌다.
PROBE = [sys.executable, os.path.join(ROOT, "scripts", "s3_coldboot_probe.py")]
RUST = [CARGO, "test", "--bin", "cysd", "agent_death_keeps"]

MUTANTS = [
    {
        "id": "S3-M1-보존-제거",
        "why": "수리 자체를 되돌린다 — 살아있지 않은 기록이 다시 쓸려나가야 한다.",
        "old": "        entries.push(prev.clone());\n",
        "new": "        let _ = prev;  // MUTANT S3-M1\n",
        "checks": [("격리 콜드부트 프로브", PROBE), ("cargo test agent_death_keeps", RUST)],
    },
    {
        "id": "S3-M2-묘비-무시",
        "why": "묘비 조건을 지운다 — 폐역 역할까지 보존돼 좀비 부활 구멍이 열려야 한다.",
        "old": "        if live_roles.contains(role) || tomb_set.contains(role) {",
        "new": "        if live_roles.contains(role) {  // MUTANT S3-M2",
        "checks": [("격리 콜드부트 프로브", PROBE), ("cargo test agent_death_keeps", RUST)],
    },
    {
        "id": "S3-M3-live-중복",
        "why": "live 중복 제거를 지운다 — 같은 역할이 두 줄이 돼 restore 이중 스폰으로 샌다.",
        "old": "        if live_roles.contains(role) || tomb_set.contains(role) {",
        "new": "        if tomb_set.contains(role) {  // MUTANT S3-M3",
        "checks": [("cargo test agent_death_keeps", RUST)],
    },
]


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=2400)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    print("[s3-mutants] 기준선 — 뮤턴트 없이 전 검사가 초록이어야 한다")
    for name, cmd in MUTANTS[0]["checks"]:
        rc, _ = run(cmd)
        if rc != 0:
            print("  [기준선 적색] %s (rc=%d) — 뮤테이션 판정 불가" % (name, rc))
            return 2
        print("  기준선 초록: %s" % name)

    verdicts = []
    for m in MUTANTS:
        orig = open(GOV, encoding="utf-8").read()
        applied = False
        try:
            if orig.count(m["old"]) != 1:
                verdicts.append((m["id"], "NOT-APPLIED",
                                 "치환 대상 %d건(예상 1) — 소스가 이동했다" % orig.count(m["old"])))
                continue
            open(GOV, "w", encoding="utf-8").write(orig.replace(m["old"], m["new"], 1))
            applied = True
            assert m["new"] in open(GOV, encoding="utf-8").read(), "변이가 디스크에 없다"
            brc, bout = run(BUILD)          # 변이를 바이너리에 실어야 프로브 축이 대상에 닿는다
            if brc != 0:
                verdicts.append((m["id"], "NOT-APPLIED",
                                 "변이 빌드 실패(컴파일 불가) — 프로브가 옛 바이너리를 잴 뻔했다:\n"
                                 + "\n".join(bout.strip().splitlines()[-3:])))
                continue
            killed_by = []
            for name, cmd in m["checks"]:
                rc, _ = run(cmd)
                if rc != 0:
                    killed_by.append(name)
            if killed_by:
                verdicts.append((m["id"], "KILLED", "잡은 축: " + " · ".join(killed_by)))
            else:
                verdicts.append((m["id"], "SURVIVED",
                                 "어느 축도 못 잡았다: " + " · ".join(n for n, _ in m["checks"])))
        finally:
            if applied:
                open(GOV, "w", encoding="utf-8").write(orig)
                run(BUILD)   # 바이너리도 원복 — 안 하면 다음 축이 남의 변이를 잰다

    print("\n[s3-mutants] 판정")
    bad = 0
    for mid, v, detail in verdicts:
        print("  [%-11s] %-18s %s" % (v, mid, detail))
        if v != "KILLED":
            bad += 1
    print("[s3-mutants] 총 %d · KILLED %d · 미달 %d" % (len(verdicts), len(verdicts) - bad, bad))
    if any(v == "NOT-APPLIED" for _, v, _ in verdicts):
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
