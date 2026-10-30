# HANDOFF — TICKET=cysr-1111-winchrome

가지 fix/1111-win-chrome-job · 기준 060cb75b · 설계 = DESIGN-winchrome.md

## 끝난 것
- 데몬 Job 은 평소처럼 이탈 불가. 크롬·재시작 대기만 데몬이 스폰 1회 동안 이탈을 허용해 띄운다(`src/job_exit.rs` · RPC `system.spawn_outside_job` · 숨은 CLI `cys spawn-outside-job`).
- 재시작 대기가 Job 밖이라 그 자식 rotate 도 밖이다 → rc·ledger·빚 정리까지 간다.
- M3: 윈은 창 1개일 때만 닫는다. 창 수는 최상위 창 전수. 실패 문장을 사실별로 분리.

## 함정
- ⚠ BREAKAWAY_OK 를 상시로 켜지 말 것 — 동봉 Git Bash 가 모든 자식에 이탈 flag 를 붙인다(소스 핀 `breakaway_bit_stays_inside_this_module`).
- 윈 실 프로세스 시험 `tests/win_job_exit.rs` 는 맥에서 0건이다. 컴파일은 win-typecheck 로 확인했고 **실행은 CI windows-health 가 처음이다**.
- 팩만 새것이고 데몬이 옛것이면 `--probe` 가 실패해 크롬을 닫지 않고 안내한다(rotate 뒤 정상).

## 윈 실기 항목(r4)
1. R5 A: 좌석에서 띄운 크롬 + chrome-enable → 좌석 재시작. 크롬 생존(창·탭) · 새 cysd · 좌석 복원 · ledger `seat_restart_rotate` rc ∈ {0,21,25} · pending_seat_restart 없음.
2. R5 B: 크롬 꺼 둠 + chrome-enable. 크롬이 떴다면 재시작 때 닫히는지 기록(설계 §4 · 미수리).
3. R5 C: 작업 스케줄러로 띄운 크롬 대조 — 생존 유지.
4. R5b: 창 2개 → 닫지 않음 · 「크롬 창이 2개」 문장. 창 1개 → 닫고 다시 켬. 최소화·다른 데스크톱 창도 세는지.
5. 백그라운드 실행 켠 크롬 창 1개 → 「크롬 창은 닫혔지만」 문장.
6. rotate rc·ledger: `~/.cys/computer-control/ledger.jsonl` 의 seat_restart_scheduled → seat_restart_rotate 순서.
7. 관리자 좌석에서 대기가 뜨는지(`cys spawn-outside-job --probe` rc 0) · 크롬·대기가 cysd Job 밖인지.
8. 재시작 대기가 CYS_BIN·CLAUDE_CONFIG_DIR 로 턴 종료를 읽는지(busy 로 900초 끝나지 않는지).
9. R5c: 크롬이 켜졌다 곧 꺼지는 경우 → failed · 다음 호출 60초 안 = 다시 안 켬 · 3회 뒤 「그만두었습니다」 · 창이 반복해서 뜨지 않음. 곧 꺼질 때까지 걸린 시간 기록(안정 창 5초 조정 근거).
10. CI 로그 `[measure]` 줄: BREAKAWAY_OK 상시 + Git Bash 자식 결과.

## 공개 노트 문장(윈 · 1안)
**크롬 연결을 켤 때 크롬이 함께 꺼지던 문제를 고쳤습니다.** 이제 cysr 가 잠깐 다시 시작해도 크롬은 그대로 켜져 있습니다. 크롬 창이 여러 개 열려 있을 때는 탭을 잃지 않도록 cysr 가 크롬을 닫지 않습니다. 그럴 때는 안내에 따라 크롬 오른쪽 위 ⋮ 메뉴의 「종료」로 닫았다가 다시 켜 주세요.

증류: memory `win-job-breakaway-msys-auto` · `chrome-window-close-session-loss`.
