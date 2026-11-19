# WORKER_TODO — TICKET=cysr-1116-seatkeep-1119 (worker-1116seatkeep · 가지 feat/1116-seatkeep ← dea2e1853)

- 이월: 없음(seatkeep T3 까지 편입됨 · T1 = feat/seatkeep-t1 【매듭】 r5c BLOCK 4 · 미편입)
- 비가역·비용 결정 목록: push · 태그 · CI · gh 쓰기 · 빌드 서명 · 발행 · 이 기기 앱 교체 · 실사용 데몬/좌석 = 워커 실행 금지(게이트) · 노브 기본 켬 = master 제안만

## 1단계 (문서만)
- [x] 브리프·디렉티브 읽기
- [x] dea2e1853 seatkeep 배선 실측(노브 기본 · cysd 경로 · 시험)
- [x] 차용 ②(OSC 7501)·③(가벼운 시작) 편입 여부 실측
- [x] 남은 것 목록 + 위험 → 【중간보고】

## 2단계 (master#7065425a = 범위 C 단계 매듭 · T4 → T5 · 상한 해제 · 노브 기본 끔 유지)
### T4 입양
- [x] 설계 메모 docs/seatkeep/T4-DESIGN.md(메타 영속 · 기동 순서 · 노브 · T1 대역 자리 한 곳)
- [x] 구현(노브 CYS_SEATKEEP_ADOPT · 기본 끔)
- [x] 격리 HOME 실물: cysd SIGKILL → 좌석 pid 생존 → 새 cysd 재부착 → read-screen/send
- [~] 기준선 대비 시험(cysd·seatkeep 끝 · 노브 켬 스크립트·ci-branch 팩 단계 = 남음) · 뮤턴트(2R 전 코드 6종 끝 · 최종 코드 재실행 남음)
- [~] codex T4 1R~4R BLOCK 처분 끝 · 5R = master 대기열 · 【확인요청】 T4(매듭)
### T5 좌석 토큰 이음
- [ ] 설계(좌석 세대 · seatkeep 보관 · 인계)
- [ ] 구현 · 토큰 왕복 시험(옛 토큰 재사용·탈취 거부)
- [ ] codex 1R(T5) · 커밋 · 【확인요청】 T5
### 목록만(HANDOFF 순서)
- T6 rotate·업데이터 · T7 윈 · D1 꼬리 유실 · 슬레이브 보유 탐침 · T1 = 다른 좌석 · ②③ = 다른 좌석
