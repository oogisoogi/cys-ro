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

## codex 1R(12:10~12:20 · BLOCK) 처리
- 반영(f2f5536e · 그 뒤 커밋): blocking 2 = `cys run -- agy` 우회 차단 · cmd 해석을 셸 문법으로(인용·대입·env 래퍼·sh -c·.bat · 대입 값 속 agy 오판 해소) / major = 실행 프로그램이 정본·키 gemini 추정은 cmd 없을 때만 · guard 읽기 허용에서 git 제외 · bash 백스톱에도 [AGY-DOOR] · phoenix 가 fresh rc 76 을 정책 건너뜀으로 소비(재시도·실패 계상 밖) / minor = Write 거부를 실제 문 파일명으로
- **미반영(2R 몫)**: ① acceptance.py 판정이 agy 실행 횟수 차이만 봄 → 입구별 기대 rc·사유 단언 추가 필요(E6 rc=1·E7 launch_failed·E8 rc=78 이 PASS 로 기록됨 — 차단은 맞으나 「도달」 증명이 약함) ② phoenix 최종 결과의 manual_seats 에 정책 제외 역할이 「빈 좌석·사람이 실행」으로 다시 들어감(codex minor · javis_phoenix.py:3410 부근) ③ guard 가 `sed -n 1p <문 파일>`·`python3 -m json.tool` 같은 읽기도 막음(codex minor · 거짓 양성 · 안전 쪽)
- verdict 원문 = 세션 scratchpad `codex/verdict.json`(커밋 안 함)

## 미완
- 위 2R 몫 3건 · 전체 cargo 재실행(f2f5536e 뒤) · health 재실행(깨끗한 env · H-CLT-1/2 원인 확정) · acceptance 재실행(f2f5536e 뒤) · codex 2R
