# WORKER_TODO — TICKET=cysr-1116-s2-1119 (조각 2 · 고리 분리 + 런타임 미룸 · 브리프 master#5340bbd4)
- 가지 feat/1116-s2 ← dea2e1853 · 상한 4h · 데몬 변경 0 · push·태그·CI·발행 금지

- [x] 브리프·지침·설계(§2-1·§2-3·§2-4·§3·§5-3·§7·§8·§9-4·§11) · 조각0 인계 · integ 인계 I3·S4-3 읽기
- [x] 기준선 측정(dea2e1853): bun test · tsc · 화면 게이트 7종 + nodept·restart·hidden_block · tickrec_gate
- [x] judge/tick.ts — 순수 판정(decideSockPre: 유령·쓸기·입양 후보 / decidePlaceholders: 자리표 회수 · decideTick = 소켓 접기)
- [x] tick.test.ts — 순수성 정적 검사 · 견본 덤프 200틱 재생 = 기록 판정 바이트 같음 · 2회 같음 · F18(화면 줄 없음 = 보류) fixture
- [x] main.ts 고리 = collect → decide → apply → paint (집행 함수 본문 제자리 · 자리표 두 벌 접기)
- [x] ensureRuntime + 미룬 좌석 장부 · 대화 화면이면 입양 = 모형만 · 작업 화면 보일 때 보이는 탭 즉시 + 나머지 한 틱 4개
- [x] F19 start() 복원 입양 · 빈 탭 충전도 ensureRuntime
- [x] F20 생성 실패 정리(ensureRuntime 실패 = 런타임 파기 · 재시도 상한)
- [x] persist 저장 = apply 단계(layoutChanged 면 화면과 무관하게 저장)
- [x] I3·S4-3 데몬 사건 구독 하나로(main.ts onDaemonEvent 머리 배선 1줄 · 대화 화면 꺼져도 장부가 받음)
- [x] 기존 핀·하네스 대역 목록 갱신
- [x] e2e: tickrec_gate OFF 대조(기준 번들 = 새 번들) · 새 덤프 재생 · 대화 화면 새 설치 = start_surface_stream 0 · 첫 진입 시간 · resize = 보이는 좌석 × 1 · 전환 100회 뒤 틱
- [x] 뮤턴트(새 시험이 대상을 잡는지)
- [x] 전체 게이트: bun · tsc · 화면 게이트 · ci-branch.yml 팩 단계 · secret-scan
- [x] codex 1R(고리 판정 = 좌석 입양·퇴거) · 처분
- [x] 커밋 + HANDOFF.cysr-1116-s2-1119.md + 【확인요청】
