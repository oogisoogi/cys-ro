# WORKER_TODO — TICKET=cysr-seatkeep-t3-r5 (master#523aa281 · 시작 2026-11-15 21:42 · 상한 23:25)
브리프 = ~/axdev/master/briefs/2026-11-15-cysr-seatkeep-t3-r5-fix.md · 판정문 = codex r4b(REVISE major 2)

- [x] #1 기동 잠금(LAUNCH): 첫 「마지막 확인」~자식 spawn~KEEP 두기 ↔ 감시 「상실 표시 + KEEP 확인」 상호 배제
  - [x] 디버그 훅: 마지막 확인과 spawn 사이 강제 틈 + 표시/spawn 순서 기록(트레이스) · release 빈 값 확인
  - [x] 붉은 시험(고치기 전 = 표시 뒤 spawn) → 초록 → 뮤턴트(잠금 끔)
  - [x] OnceLock AcqRel/Acquire 지적 = 잠금으로 닫히는지 1줄 · 잠금 순서 표 · 재현 50회 0
  - [x] 한계 = 커널 오류 반환 뒤 표시 전 창 → spawn 직후 상실과 같은 결과
- [x] #2 감시 실패 warn! 제거 · end_early 의 종료 앞 동기 출력 비차단화
  - [x] 붉은 시험(stderr = 가득 찬 파이프) → 초록 → 뮤턴트
  - [x] 같은 꼴 grep 전수 1줄
- [x] 회귀(HANDOFF 명령 그대로) · 흔들림 단독 재실행
- [x] 노브 기본값 파일:줄
- [x] HANDOFF r5 절 · 커밋 · readlink ~/.local/bin/claude 대조(처음 = versions/2.1.325)
- [x] 【확인요청】(22:05 인박스 발송)
