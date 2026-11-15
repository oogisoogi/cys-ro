# WORKER_TODO — TICKET=cysr-seatkeep-t3-fix1 (worker-8 · surface:2019 · 착수 08:31 KST)
- [ ] 0 기준선: 노브 끔/켬 전체 시험(fcc6896f) 실패 이름 수집
- [x] 1 major: controller_bound 부모 상실 → spawn 전 종료 · 감시 spawn 앞 시작 · 재현 시험(SIGSTOP→부모 종료→SIGCONT) 붉음→초록→뮤턴트
- [x] 4 minor: 종료 소유자 1명(compare_exchange) · 시험 seatkeep_exit 1줄 · 뮤턴트
- [x] 2 major: cysd demux 가 OUTPUT 큐에서 안 막힘 · 시험(소비자 정지 64조각 → close_surface 상한·입력 ACK) · 204MB 폭주 초록 · 뮤턴트
- [x] 3 minor: 게이트 구조분해·식별자 경계·중첩 호출 불허 · 남는 한계 주석
- [x] ③ D1 문서 정정 + XNU 소스 줄 주소 + T4 차단 조건 추가
- [ ] 회귀: 끔/켬 전체 · seatkeep · 게이트 · 꼬리 · 좌석 수명 · 폭주 · 생성 도중 · cwd 경합 · 반복 시험 10회
- [ ] HANDOFF 갱신 · 커밋 · 【확인요청】

## 매듭(2026-11-12 08:4x · master#4a52ad00 예산 정지 · 재개 = master 지시만)
- 읽은 것: 브리프 · 공통 규칙 · codex 1R 판정문 전문 · HANDOFF(T4·검증 고침·전체 시험 절) · seatkeep main.rs(run·supervise·end) · cysd seat_proc.rs(SeatLink 전부) · governance close 대기 · 게이트 시험 전문.
- 끝남: #1(부모 감시 kqueue · ppid1 = rc 8 · 기동 직전·직후 확인)·#4(종료 소유자 compare_exchange) = 커밋 d9f8f44a · seatkeep 단위 38/38 · 뮤턴트 5/5(M1-prefix-all·M1a·M1b·M1c·M4).
- 진행 중(WIP 커밋 · 미빌드·미시험): #2 = cysd 64조각 채널 → 바이트 대기열 OutSpool(평소 1MiB 역압 · 제어 답 기다림/닫는 중 5MiB · 닫는 중 넘침 버림 · 읽기 얼굴 Drop = 이후 버림) + 시험 seatkeep_stalled_consumer_does_not_block_ack_or_close(seat_proc_tests.rs 끝).
- 다음 첫 행동: 시험을 WIP 이전 seat_proc.rs 로 붉음 확인(git stash 금지 → 파일 단위 되돌림) → WIP 빌드·초록 → 뮤턴트(Awaiting 제거·mark_closing 제거) → 204MB 폭주(seat_flood_tests 켬) → #3 게이트 → D1 문서·XNU 줄 → 회귀 · HANDOFF.
- 기준선: base-full-off(fcc6896f) 은 정지로 중간 종료(결과 불완전) — 재개 때 다시 돌린다 · 켬 기준선 = 전임 full-on-v2(4638cefa) 실패 이름 참조. 실행기 = scratchpad run_tests.sh(먼저 cargo build --bin cys-seatkeep).

## 재개(16:51 · master#be9e91aa)
- #2 붉음(옛 seat_proc 둘 다 5초 초과)→초록·뮤턴트 3/3 · 204MB 켬 초록 · #3 게이트 고침·우회 3 심음(옛=놓침/새=붉음)·뮤턴트 3/3 · D1 문서·XNU 줄 · HANDOFF fix1 절 · 전체 회귀 사슬 돌림(17:1x~) · 다음 = 릴리스 빌드 → 시험대(t3life·midcreate·cwdrace·t3stopclose 10회) → 【확인요청】
