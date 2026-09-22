#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
d1_pack_refresh_mutants.py — TICKET=v115r2-pack 뮤테이션 검산 (D1·D2·D3·D4)

무엇을 재는가: 이 라운드의 수리를 **되돌렸을 때 검사 축이 실제로 적색이 되는가.**
통과만 보고는 그 축이 무엇을 재는지 알 수 없다.

각 뮤턴트: 백업 → 정확히 한 곳 되돌리기(치환 건수 assert) → 검사 실행 → 종료코드 판정 →
          finally 원복(예외·중단에도).
어휘: KILLED=잡았다 · SURVIVED=그 축은 공허하다 · NOT-APPLIED=변이가 적용조차 안 됨(측정 실패).
exit: 0=전건 KILLED · 1=SURVIVED 있음 · 2=측정 실패.

★변이는 **실행 가능한 다른 동작**이어야 한다 — 문법을 깨거나 이름을 지우는 변이는 공짜 KILLED 다
  (mutant-that-breaks-syntax-is-a-free-kill).
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKRS = os.path.join(ROOT, "src", "pack.rs")
STATE = os.path.join(ROOT, "src", "bin", "cysd", "state.rs")
LIBSH = os.path.join(ROOT, "cysjavis-pack", "hooks", "_lib.sh")
PREFLIGHT = os.path.join(ROOT, "cysjavis-pack", "bin", "javis_preflight.py")
CARGO = os.environ.get("CARGO", os.path.expanduser("~/.cargo/bin/cargo"))

RUST_D1 = [CARGO, "test", "--lib", "d1_user_owned_refresh_merge_and_ceo_derivative"]
RUST_ACL = [CARGO, "test", "--lib", "install_force_preserves_user_acl_and_parks_vendor_new"]
RUST_D4 = [CARGO, "test", "--bin", "cysd", "d4_spawn_confluence"]
PY_D3 = [sys.executable, os.path.join(ROOT, "cysjavis-pack", "bin", "tests",
                                      "test_py_resolver_clt_stub.py")]
PY_D2 = [sys.executable, os.path.join(ROOT, "cysjavis-pack", "bin", "tests",
                                      "test_v115_dept.py")]

MUTANTS = [
    {
        "id": "D1-M1-미수정가지-제거",
        "why": "수리 본체를 되돌린다 — 사용자 미수정 user-owned 가 다시 `.new` 에 갇혀야 한다.",
        "file": PACKRS,
        "old": "                if manifest_hash == Some(content_hash(d).as_str()) {\n"
               "                    return FileAction::RefreshUser;",
        "new": "                if manifest_hash == Some(\"MUTANT-D1-M1\") {\n"
               "                    return FileAction::RefreshUser;",
        "checks": [("cargo test d1 시나리오4", RUST_D1)],
    },
    {
        "id": "D1-M2-해시비교-뒤집기",
        "why": "「미수정」 판정을 뒤집는다 — 사용자 **수정본**을 덮고 미수정은 동결해야 한다.",
        "file": PACKRS,
        "old": "                if manifest_hash == Some(content_hash(d).as_str()) {\n"
               "                    return FileAction::RefreshUser;",
        "new": "                if manifest_hash != Some(content_hash(d).as_str()) {\n"
               "                    return FileAction::RefreshUser;",
        "checks": [("cargo test d1 시나리오4", RUST_D1)],
    },
    {
        "id": "D1-M3-백업-생략",
        "why": "되돌릴 자리를 없앤다 — 갱신은 되지만 직전 사본이 사라져야 한다.",
        "file": PACKRS,
        "old": "                    let bak = dir.join(format!(\"{rel}.bak-{target_version}\"));\n"
               "                    if std::fs::read_to_string(&bak).ok().as_deref() != Some(d) {",
        "new": "                    let bak = dir.join(format!(\"{rel}.bak-MUTANT-D1-M3\"));\n"
               "                    if std::fs::read_to_string(&bak).ok().as_deref() != Some(d) {",
        "checks": [("cargo test d1 시나리오4", RUST_D1)],
    },
    {
        "id": "D1-M4-CEO파생-판정뒤집기",
        "why": "제품 파생본(CEO 승격 사본) 판정을 뒤집는다 — 승격 기계가 신판 CEO 대신 "
               "vendor MASTER 로 덮여 조용히 강등되거나 동결돼야 한다.",
        "file": PACKRS,
        "old": "    if manifest_ceo_hash != Some(dh.as_str()) {\n        return None;\n    }",
        "new": "    if manifest_ceo_hash == Some(dh.as_str()) {\n        return None;\n    }",
        "checks": [("cargo test d1 시나리오4", RUST_D1)],
    },
    {
        "id": "D1-M5-병합-제거",
        "why": "혼합 설정 병합을 끈다 — 사용자 수정본 schedule/acl 이 다시 `.new` 로 주차돼 "
               "vendor 신규 항목이 디스크에 도달하지 않아야 한다.",
        "file": PACKRS,
        "old": "                if is_user_mergeable(rel) {",
        "new": "                if false && is_user_mergeable(rel) {",
        "checks": [("cargo test d1 시나리오4", RUST_D1),
                   ("cargo test acl 계약", RUST_ACL)],
    },
    {
        "id": "D1-M6-순서함정-복귀(루프중 manifest 읽기)",
        "why": "파생본 판정 기준을 루프 전 스냅샷이 아니라 루프 중 manifest 에서 읽게 되돌린다 — "
               "사전순으로 CEO_TEMPLATE 이 먼저 갱신되므로 판정이 **한 번도 발화하지 않아야** 한다. "
               "(초판이 실제로 이 형상이었고, 픽스처 순서를 실제 PACK_ALL 과 다르게 둬서 숨어 있었다.)",
        "file": PACKRS,
        "old": "            ceo_manifest_before.as_deref(),",
        "new": "            manifest.get(CEO_TEMPLATE_PACK_REL).map(String::as_str),",
        "checks": [("cargo test d1 시나리오4", RUST_D1)],
    },
    {
        "id": "D1-M7-매니페스트에-치환본기록",
        "why": "CEO 치환분의 매니페스트·pristine 에 vendor 원본 대신 **치환본** 해시를 넣는다 — "
               "강등 백업(.pre-ceo)과 대조할 기준이 사라져 **두 번째 갱신부터** 백업이 낡아야 한다.",
        "file": PACKRS,
        "old": "        let record: &str = if ceo_ov.is_some() { vendor_embed } else { content };",
        "new": "        let record: &str = content;",
        "checks": [("cargo test d1 시나리오4", RUST_D1)],
    },
    {
        "id": "D2-SOT-좁은홈글로브-복귀",
        "why": "스킬 프로필 SOT 를 옛 `$HOME/.claude*` 자기 글로브로 되돌린다 — 좌석 프로필"
               "(~/.cys/claude*)이 다시 대상 밖이 돼야 한다.",
        "file": PREFLIGHT,
        "old": "    profs, seen = [], set()\n    for sp in discover_claude_settings():",
        "new": "    profs, seen = [], set()\n    for sp in []:",
        "checks": [("python test_v115_dept", PY_D2)],
    },
    {
        "id": "D3-첫해석판정-복귀",
        "why": "A5 게이트 술어를 옛 「PATH 어딘가에 진짜 파이썬이 있는가」로 되돌린다 — "
               "스텁이 앞에 있어도 비발동이 돼야 한다(914 S1 형상).",
        "file": LIBSH,
        "old": "  if ! _cys_shell_py3_is_stub; then printf '0'; return 0; fi",
        "new": "  if _cys_path_py_darwin >/dev/null 2>&1; then printf '0'; return 0; fi",
        "checks": [("python test_py_resolver_clt_stub", PY_D3)],
    },
    {
        "id": "D4-좌석configdir-제거",
        "why": "스폰 합류점의 좌석 env 주입을 지운다 — 인라인 접두를 타지 않은 claude 가 다시 "
               "개인 프로필을 읽는 형상으로 돌아가야 한다.",
        "file": STATE,
        "old": "        builder.env(\"CLAUDE_CONFIG_DIR\", cys::resolve_claude_config_dir());\n",
        "new": "",
        "checks": [("cargo test cysd d4", RUST_D4)],
    },
]


def run(cmd):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)[-600:]


def main():
    # 선행: 무변이 상태에서 전 검사가 초록이어야 한다 — 빨간 killer 는 공짜 KILLED 를 만든다.
    base_fail = []
    for name, cmd in [("cargo test d1 시나리오4", RUST_D1), ("cargo test acl 계약", RUST_ACL),
                      ("cargo test cysd d4", RUST_D4), ("python test_py_resolver_clt_stub", PY_D3),
                      ("python test_v115_dept", PY_D2)]:
        rc, tail = run(cmd)
        print("[baseline] %-34s rc=%d" % (name, rc))
        if rc != 0:
            base_fail.append(name)
            print(tail)
    if base_fail:
        print("측정 실패 — 무변이 기준선이 적색이다(빨간 killer 는 아무것도 증명하지 않는다): %s"
              % ", ".join(base_fail))
        return 2

    verdicts, measure_fail = [], False
    for m in MUTANTS:
        path = m["file"]
        orig = open(path, encoding="utf-8").read()
        cnt = orig.count(m["old"])
        if cnt != 1:
            print("NOT-APPLIED %s — 조준 문자열 %d건(1이어야 한다)" % (m["id"], cnt))
            verdicts.append((m["id"], "NOT-APPLIED"))
            measure_fail = True
            continue
        try:
            open(path, "w", encoding="utf-8").write(orig.replace(m["old"], m["new"]))
            killed_by = []
            for name, cmd in m["checks"]:
                rc, tail = run(cmd)
                if rc != 0:
                    killed_by.append(name)
            if killed_by:
                print("KILLED   %s — 잡은 축: %s" % (m["id"], ", ".join(killed_by)))
                verdicts.append((m["id"], "KILLED"))
            else:
                print("SURVIVED %s — %s" % (m["id"], m["why"]))
                verdicts.append((m["id"], "SURVIVED"))
        finally:
            open(path, "w", encoding="utf-8").write(orig)

    surv = [i for i, v in verdicts if v == "SURVIVED"]
    print("\n%d개 뮤턴트 · KILLED %d · SURVIVED %d · NOT-APPLIED %d"
          % (len(verdicts), sum(1 for _, v in verdicts if v == "KILLED"), len(surv),
             sum(1 for _, v in verdicts if v == "NOT-APPLIED")))
    if measure_fail:
        return 2
    return 1 if surv else 0


if __name__ == "__main__":
    sys.exit(main())
