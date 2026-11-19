#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_agents_notes_personal_hooks.py — agents.json claude.notes 가 개인 프로필 훅 등록 사실과 맞는가
(TICKET=cysr-1115-smalls ①).

무엇을 막는가: notes 가 「사용자 ~/.claude 와 격리(읽지도 지우지도 않음)」라고 적고 있었는데, 실제로는
  · 데몬 팩 설치(src/pack.rs merge_awakening_hooks_into_personal_profiles)가 기동마다 각성 훅 2개
    (AWAKENING_HOOKS)를 ~/.claude*/settings.json 에 추가 병합하고(옵트아웃 CYS_NO_PERSONAL_HOOK_MERGE=1),
  · 부트 프리플라이트(--fix · discover_claude_settings 의 home-glob)가 같은 파일에 훅을 더 등록한다.
문서가 코드와 반대를 말하면 사용자·검토자가 「우리 설정은 안 건드린다」고 믿게 된다.

  ① notes 에 「읽지도 지우지도 않음」 단언이 없다
  ② notes 가 각성 훅 스크립트 2개(파이썬 AWAKENING_HOOKS = Rust AWAKENING_HOOKS 파리티 대상)를 이름으로 적는다
  ③ notes 가 옵트아웃 노브 이름을 적고, 그 이름이 src/pack.rs 에 실재한다(지어낸 노브 금지)
  ④ notes 가 프리플라이트 추가 등록과 statusLine 을 언급한다(2개가 전부라고 오해하지 않게)
출력: PASS/FAIL 행 · 실패 시 exit 1 · 종료 토큰 AGENTS-NOTES-PERSONAL-HOOKS-OK.
실행: python3 cysjavis-pack/bin/tests/test_agents_notes_personal_hooks.py
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(os.path.dirname(HERE))
REPO = os.path.dirname(PACK)

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else " — " + detail))
    if not ok:
        fails.append(name)


with open(os.path.join(PACK, "agents.json"), encoding="utf-8") as f:
    notes = json.load(f)["claude"]["notes"]

spec = importlib.util.spec_from_file_location("javis_preflight", os.path.join(PACK, "bin", "javis_preflight.py"))
pf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf)

check("① 격리 단언(읽지도 지우지도 않음) 부재", "읽지도 지우지도 않음" not in notes,
      "notes 가 여전히 개인 프로필 무접촉을 단언한다")
for script, _ in pf.AWAKENING_HOOKS:
    check("② 각성 훅 이름 %s" % script, script in notes, "notes 에 %s 없음" % script)

KNOB = "CYS_NO_PERSONAL_HOOK_MERGE"
with open(os.path.join(REPO, "src", "pack.rs"), encoding="utf-8") as f:
    pack_rs = f.read()
check("③ 옵트아웃 노브 이름 표기", KNOB in notes, "notes 에 %s 없음" % KNOB)
check("③ 옵트아웃 노브 실재(src/pack.rs)", KNOB in pack_rs, "src/pack.rs 에 %s 없음" % KNOB)
check("④ 프리플라이트 추가 등록 언급", "프리플라이트" in notes, "notes 에 프리플라이트 언급 없음")
check("④ statusLine 언급", "statusLine" in notes, "notes 에 statusLine 언급 없음")

if fails:
    print("FAIL %d" % len(fails))
    sys.exit(1)
print("AGENTS-NOTES-PERSONAL-HOOKS-OK")
