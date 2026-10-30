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
- **cysd 감독자 축 윈 패닉 150+건 · 스텝 30분 절단 · 원인 미규명**: windows-health 「cargo test --bin cysd 감독자 축」(비차단) 스텝이 런마다 패닉 152~172건(40589719076 = 154 · 기준선 40413658930·40409222350·40401921561)을 내고 스텝 상한 30분에 절단된다 — 절단 지점이 런마다 달라 패닉 집합도 다르다. 대표 사유 = return_absorb_tests 「시험 좌석에 `sleep 30` 가 10s 안에 뜨지 않았다」(governance.rs:15050). 결함 후보 · 1.1.11 수리 무관(cysd 소스 win_task 참조 0).

## 정지 지점 (2026-10-28 09:5x · master#cba069d0 계정 94% 전 좌석 정지)

| 칸 | 내용 |
|---|---|
| 원격 `origin/fix/1111-wintask` | `29bc5f9e`(int/1111 `cb5dee6a` 위) · CI 3런 녹: ci-branch 40603430392 · windows-build 40603430418 · windows-health 40603430374(56분 4초 · 75분 상한 · UI 회귀 녹 · 스텝 16 은 여전히 30분) |
| windows-build win_task | 40599417017 에서 윈 실기 8/8 · 블록 93초(+2분 이내 → health 스텝 8 이전 안 함 · master#c709308c) |
| 로컬 (미push) | int/1111 `19655dd6` 위로 rebase 2 완료 · 충돌 0 · 내 변경 diff 동일 · int 15커밋과 파일 겹침 0 · 백업 `backup/1111-wintask-pre-rebase2-29bc5f9e` |
| 끊긴 것 | rebase 2 뒤 로컬 게이트(lib · secret-scan --all · 윈 타깃 check · u2-mutants) — lib 도중 정지 · **결과 없음** |
| 다음 첫 명령 | `cd ~/cys-terminal-src-wt/1111-wintask && git fetch origin int/1111 && git log --oneline -1 origin/int/1111` → int 가 또 움직였으면 rebase → 위 로컬 게이트 4종 녹 → master 에 강제 push 확인요청(`--force-with-lease=fix/1111-wintask:29bc5f9e`) |

## wintask-r2-fix (2026-10-30 · worker-7 surface:1736 · codex R2 REVISE major 2 → R3 REVISE major 2 → R4 진행)

| 칸 | 내용 |
|---|---|
| 가지 기준 | 원격 줄 위 빨리감기 — `29bc5f9e` → `cf1a941d`(3fb9ebc0 HANDOFF 문서 cherry-pick) → `ffa0772a`(R2 수리) → `cb29c3d1`(R3 수리) · rebase 2 줄 + R2 수리 = `backup/1111-wintask-rebase2-r2fix`(bb14a35a) · int 로 다시 얹기 = master/1731(int/1111 도 12커밋 전진 · fec48a8a) |
| push | `ffa0772a` 만(master#006f154d 재승인 · 원장 4요건) · `cb29c3d1` = 로컬 · 별도 재승인 필요 |
| 수리 | `install<S: Sched>`(순수 · 윈 = `com::ComSched` · 시험 = `Fake`): 옛 작업 읽기·지우기 = 없음(`HR_TASK_ABSENT` 0x80070002)만 정상 · 그 밖 = 중단(옛 작업 그대로) · 유효한(judge 통과) 옛 작업만 복원(새 등록 실패·재독 거부 · 거부 작업 지우기 실패여도 시도) · 복원 재독 거부 = 증거(`win-task-refusal-<작업>-restore.json` · stage 칸) 먼저 → 지움 |
| 시험·뮤턴트 | win_task 14(맥) + 윈 전용 1(`com_absent_task_hresult_is_file_not_found` · 루트 GetTask 읽기만) · WT2 무시 범위 넓히기 · WT3 복원 빼기 · WT4 지우기 실패 시 복원 빼기 · WT5 복원 거부 증거 빼기 — WT1~5 녹/적 손 확인 · u2-mutants 등재 · windows-build 이름 15건 |
| 로컬 게이트 | ffa0772a: lib 1127/0 · win-typecheck 0 · secret-scan clean · cb29c3d1: win_task 14/14 · win-typecheck 0 · secret-scan clean · u2-mutants·lib 전체 = 결과는 【확인요청】 참조 |
| 함정 | ① macOS 에 `timeout` 없음 → codex 는 `perl -e 'alarm shift; exec @ARGV' 1800 codex exec …` ② zsh `set -- $m` 은 단어 분리 안 함(뮤턴트 루프는 bash) ③ u2-mutants 도중 src 편집 금지(1차 실행이 내 편집으로 오염 → 녹=1 다수 · 중지·재실행) ④ 「없음」 HRESULT 는 MS 문서 미기재 — 윈 실기 시험이 유일 근거 |
| 미결 | codex R4 판정 · windows-build(ffa0772a) 윈 실기 결과 · cb29c3d1 push 재승인 · DeleteTask 없음 HRESULT 실측 0(흐름상 GetTask 없음이면 지우기 안 부름) |
| 재현 | `cargo test -q --lib update::win_task` · `bash -c` 로 `CYS_U1_MUTANT=WT<n> cargo test -q --lib update::win_task::tests::<시험> -- --exact` · `sh scripts/win-typecheck.sh` |
