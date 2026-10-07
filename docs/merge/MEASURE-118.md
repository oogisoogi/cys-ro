# MEASURE-118 — 병합본 첫 측정(수리 전) · 2026-10-05 22:50~23:4x · 격리 env(EVIDENCE-118 §8 + TMPDIR=/private/tmp/claude-501/s118/t)

## 1. 빌드
- 1차 cargo build --workspace --all-targets: lib 4 오류(중복 상수 2 · 시험 초기화 새 필드 2) → 리드 수리.
- 2차(keep-going): 83 오류(cysd 시험 76 · cysd 2 · cys 1 · cys 시험 1 · src-tauri 빌드 스크립트 1 = 사이드카 `binaries/cysd-aarch64-apple-darwin` 부재 · 병합 무관)
- 컴파일 수리 서브 22:52:47→22:58:24(5분37초) → `cargo build --bin cys --bin cysd --tests` 오류 0 · 시험 삭제 0(usage.rs 원작자 agy 시험 13개 블록이 우리 mod 안으로 잘못 들어간 것을 원위치) · 원장 scratchpad ledger-compile.tsv.
- src-tauri: 미측정(사이드카 필요 · 다음 단계).

## 2. cargo test -p cys-terminal (no-fail-fast · 1회 ≈10~12분)
| 바이너리 | 통과 | 실패 |
|---|---|---|
| lib | 704 | 57 (잠금 오염 연쇄 52 · 근본 5) |
| cys | 565 | 9 |
| cysd | 2,391 | 53 |
- 근본 67(짧은 TMPDIR 재측정 기준 · 긴 TMPDIR 1차 근본 75 중 10 = SUN_LEN 환경 적색 · 동시 실행 흔들림 4).
- 원작자 기준판(up/v0.14.43 · 같은 격리 env): lib 702/0 · cys 464/0 · cysd 2,126/2 ⇒ 원작자 판은 사실상 초록. 병합본 근본 67 중 **원작자판에서도 적색 = 1**(b3_status_polling_does_not_restat_the_identity_file).
  - 정정 10-08: 이 시험의 적·녹은 부하가 아니라 실행 기계 $HOME 의 프로필 폴더 수로 결정된다(빈 홈 = 통과 · 1개 = left 1 · 2개 = left 2 · v0.14.43 도 같음) — 시험에 accounts::test_home 이음매 1줄로 수리 · TICKET=cysr-118-r2-b3status
- 출처: 원작자 시험 49 · 우리 시험 18. 원인 갈래(대표): H1 사람 신뢰 축 오버레이(d12_*·v7_*·send_settle·return_absorb a2 ≈10 = 결정 ② 고정물 조정 대상) · agy 휴면(U1/C4 · accounts·usage·handlers ≈11) · D-TEAM 휴면(team_propose·team_token 파싱 2) · schedule 버전·이관(K49 4) · G1 승인 축 OR(c5·wp5 ApprovalPending↔PromptGate 3) · H2 허용목록 · S1 보존소 · 소스 핀(census·settle helper·output_generation·macos_devtools 등) · 우리 결합 시험(v115 seat_inject_guarded 함수명 · v114 owner token · u8 ack-only · d6_1 · delivery f1 583↔829 · released_tables CEO_TEMPLATE 해시 → 생성기 재실행 필요 = 잠금 오염 52 의 뿌리 후보).
- 전 목록 = scratchpad rust-red-classified.tsv.

## 3. ui (bun · tsc)
- tsc: 13 오류 = 전부 `feedbackmodal.ts`(X17 · 원작자 U6 작성 창이 우리 feedback.ts API 와 불일치).
- bun test: 2,684 통과 · 30 skip · 147 실패 — 원작자 시험 파일 138 · 우리 8 · 추가·추가 1. 원작자 몫 ≈104 = 배선하지 않기로 한 기능의 배선 시험(usagewiring 40 · deptprogresswiring 24 · expertwiring 19 · updatewiring 10 · feedbackwiring 7 · teamproposal 4) + updatenotice 21(J2/WU 를 우리 업데이트 흐름에 이식 → 원작자 배선 문면 핀).

## 4. 팩 python 시험(163 · 시험마다 새 CYS_PACK_DIR · 1,991초)
- 실패 42(시간 초과 2 포함) → 기준판 재실행(원작자 0.14.43 · 우리 1.1.7)으로 분류:
  - 환경 적색(두 기준판 모두 적색) 8: run_bootstrap_health · test_bootstrap_chain · test_dept_doctrine_v1 · test_dept_ticket_deficit_zero · test_dept_ticket_request · test_lane_isolation_v1 · test_preflight_phase1_checks · test_verify_gate
  - 원작자 자체 적색(원작자판 적색·우리판 초록/부재) 4: test_dept_create_progress · test_dept_name_guard(원작자 시간 초과) · test_dept_team_token(시간 초과) · test_session_start_hook
  - 원작자 시험·병합으로 적색 14 · 우리 시험·병합으로 적색 12 · 양쪽 시험·병합으로 적색 4
- 전 목록 = scratchpad pack-red-classified.tsv.
- 실 팩 쓰기 0: `find ~/.cys ~/.local/state/cys -newer <시작 표지>` 에 ~/.cys/pack 0건(나머지 = 라이브 데몬·훅 정상 기록: topology·event.seq·schedule_state·named_reporters·heartbeat·cysd.log·.claude.json·ctx-relay-base·hook-timing·dept-requests tick).
