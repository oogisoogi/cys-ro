# HANDOFF — 1.1.11 윈 복구기 등록 거부 수리 (TICKET=win-selfupdate-recover · fix/1111-wintask)

| 칸 | 내용 |
|---|---|
| 가지 | `fix/1111-wintask` ← int/1111 `2d32a22d` · 커밋 `e280c76b`(수리) · `8b9cb1ec`(codex R1 반영) |
| 증상 | 1.1.10 윈: 잡 `self-update-check` = rc 4 `update.recover_agent_failed / update.win_task_refused` · `--check` = N14 「복구기 미등록·불일치」 ⇒ 자동 갱신·팩 자동 갱신 전면 정지(러너가 뜨지 않음) |
| 원인(윈 실측 2026-10-27 07:53 · 윈 11 26200 ko-KR · 표준 사용자 · probe-cysr-task.ps1) | `RegisterTask` 플래그 6 → 스케줄러가 작업 SD 의 보호 P 를 떼고 주체 `(A;;FR;;;나)` 를 덧붙임 → `sddl_exactly` 거부 → 작업 삭제. 플래그 0x16(`TASK_DONT_ADD_PRINCIPAL_ACE`) = `D:PAI(우리 SDDL)` 그대로 · Run OK · UserId=SID · 폴더 통과 |
| 수리 | `register_flags()`=0x16(복구기·러너 공통) · 등록 직전 같은 이름 작업 삭제(갱신 경로 회피) · 거부 사유 칸별(`judge`) · 읽기 오류/불일치 구분(`verify_detail`) · 지우기 전 증거 `win-task-refusal-<작업>.json`(소유자 전용 · 부분 읽기 원문 포함) |
| 시험 | probe 원문 픽스처(SID·PC 이름 가명화) 6=거부·0x16=통과 · 플래그 핀(뮤턴트 WT1 · u2-mutants 등재) · 호출 지점 소스 핀 · 부분 증거 — win_task 8/8 |
| 로컬 게이트(e280c76b) | lib 1122/0 · cys 735/0(16MB 스택 — 기본 스택은 `a3_strip_hook_digits…` 스택 넘침 · 기준선 3526bbf9 동일 · 이 티켓 무관) · cysd 직렬 3217/0 · 팩 143/143 · 건강성 167/2/1(H-CLT-1·2 = 기존) · secret-scan·scan-pack-secrets·lane-parity 녹 · u2-mutants 50/50 · 윈 타입체크 오류 0 |
| 델타 게이트(8b9cb1ec) | lib 1123/0 · win_task 8/8 · WT1 적 · 소스 핀 변조 적 · 윈 타입체크 오류 0 · secret-scan clean |
| codex R1 | REVISE(MAJOR 2·MINOR 3) → R1-01~04 반영 · R1-05 아래 BACKLOG · verdict = `~/.cys/pack/round/_reviews/win-selfupdate-recover-e280c76b-r1-codex.json` |
| 1.1.10 사용자 | 자동으로는 1.1.11 을 못 받는다(복구기 실패 = 피드 전 rc 4) → **수동 설치 1회**. 앱 안 안내 경로 = 상담소 1:1(가입 기기)·아고라 공지뿐(피드·봉투·notes_ko 경로 0) |

## 1.1.12 후보(BACKLOG 한 줄 — master TODO 에 옮겨 적을 것)

- **R1-05 COM 초기화 수명**: `src/update/win_task.rs` `com::service()` 가 호출마다 `CoInitializeEx` 를 부르고 `CoUninitialize` 로 상쇄하지 않는다(기존 결함 · 1.1.11 수리 무관) → 초기화 HRESULT 를 쥔 apartment 가드(S_OK·S_FALSE 만 해제 · RPC_E_CHANGED_MODE 는 해제 의무 없음)를 인터페이스 해제 뒤 Drop 하게. 윈 실기 회귀 시험 동반.
