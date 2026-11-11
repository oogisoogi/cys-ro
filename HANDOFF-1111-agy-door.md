# HANDOFF · TICKET=cysr-agy-policy-exposure — agy 좌석 문(2단계 구현)

- 지시: master#aba34fa5(11-11 10:49 · 원장 대조 성립) · 1단계 설계 = `DESIGN-agy-policy-exposure.md`(813f3291)
- 가지 `fix/agy-policy-exposure` ← v1.1.14 `270e3e21` · 로컬 커밋만(push 0)
- 작업 = worker-10(surface:1942)

## 끝난 것(커밋)

| 커밋 | 내용 |
|---|---|
| 33236d7f | leaf `src/agy_door.rs`(판정·문 파일·문안·76) · launch-agent/boot_agent_on_surface/restore 1줄씩 · agent-detect `apply_agy_door` · src-tauri `agy_seat_door_get/warning/set` · ui 팔레트 「Antigravity(agy) 좌석 열기/닫기」(열 때만 확인 창) |
| c67fe476 | phoenix `agy_door_split`(오라클이 agy_consumer_policy 면 부활 대상 제외 · claude 만이면 호출 0) · guard.sh `[AGY-DOOR]` · `test_agy_door.py` 12 · CI 5 루프 등재 |
| 62b1f8d2 | MASTER §7 머리 2줄(바이트 래칫 때문에 같은 파일 이력 괄호·§13 중복 문단 삭제 → 순 −6B · 상한 낮춤) · CEO 재합성 · CORE §7·§13 해시+요지 · WORKER §11 · 토론 스킬 · README/설명서 |
| d82dc75b | new-surface 우회 길 차단 · `agy_door_wiring_tests` 3 · 발행 해시 표 · H-SEAT-4AXIS 창 경계 수정 · `docs/agy-door-evidence/acceptance.py`+결과 |

## 결정(지시 없이 내린 것)
- 문 = **앱 화면(명령 팔레트 확인 창) → `~/.cys/agy-seat-door.json`**. 환경 변수 안 씀: Claude 가 명령 앞 한 줄로 열 수 있고(⑤ 불가) 여는 순간 사람에게 경고를 보일 자리가 없다.
- 어댑터 판정 = 키 `gemini` **또는** cmd 실행 파일 `agy`/`antigravity`(키 개명 우회 차단). ⚠ API 열쇠로 gemini 키를 쓰는 사용자도 막힘 → 그 사람은 문을 열면 된다.
- 종료 코드 76(저장소 미사용 값).

## 실측(합격)
- `python3 docs/agy-door-evidence/acceptance.py`(cargo build --bin cys --bin cysd 선행 · 약 10분): 격리 하네스 데몬 + 가짜 agy/claude/codex · 실 agy 실행 0 → **14/14 PASS**(문 닫힘 11 입구 agy 생성 0 · 사람 직접 agy +1 · 문 열림 launch/restore 종전대로)
- 뮤턴트: M1(launch-agent 줄 삭제)·M2(boot_agent_on_surface 줄 삭제) → 각각 배선 핀 적색. M1 은 실측에선 2중 방어(boot_agent_on_surface)가 agy 를 막아 rig 초록(핀이 잡음).

## 함정
- 팩 훅 시험은 `CYS_PACK_DIR` 가 있으면 설치본 훅으로 위임된다 → `env -u CYS_PACK_DIR` 또는 `CYS_HOOK_LANE_GUARD=0`.
- phoenix 하네스 시험 2개(e2e_replacement·w2_untomb)는 TMPDIR 별칭에서 `aliased_harness_root` → `bash scripts/ci/phoenix-host-gate.sh <시험>` 로 돌린다.
- MASTER 바이트 래칫(test_cso_directive_rev) — 지침에 글을 더하면 같은 파일에서 그만큼 줄여야 한다. 고치면 `gen_ceo_template.py` · `core_inject.py verify` · `gen_released_directive_hashes.py` 셋 다.
- run_bootstrap_health 의 H-CLT-1/2 는 셸의 `CYS_*` env 누출로 붉을 수 있다(확인 중 — 아래 미완).

## 미완
- M2 rig 결과 · 전체 cargo 재실행(d82dc75b 뒤) · health 재실행(깨끗한 env) · codex 1R(실행 중 · scratchpad codex/verdict.json) → 수정 → 【확인요청】
