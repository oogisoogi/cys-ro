# WORKER_TODO — TICKET=cysr-seatkeep-t3-fix1 (worker-8 · surface:2019 · 착수 08:31 KST)
- [ ] 0 기준선: 노브 끔/켬 전체 시험(fcc6896f) 실패 이름 수집
- [ ] 1 major: controller_bound 부모 상실 → spawn 전 종료 · 감시 spawn 앞 시작 · 재현 시험(SIGSTOP→부모 종료→SIGCONT) 붉음→초록→뮤턴트
- [ ] 4 minor: 종료 소유자 1명(compare_exchange) · 시험 seatkeep_exit 1줄 · 뮤턴트
- [ ] 2 major: cysd demux 가 OUTPUT 큐에서 안 막힘 · 시험(소비자 정지 64조각 → close_surface 상한·입력 ACK) · 204MB 폭주 초록 · 뮤턴트
- [ ] 3 minor: 게이트 구조분해·식별자 경계·중첩 호출 불허 · 남는 한계 주석
- [ ] ③ D1 문서 정정 + XNU 소스 줄 주소 + T4 차단 조건 추가
- [ ] 회귀: 끔/켬 전체 · seatkeep · 게이트 · 꼬리 · 좌석 수명 · 폭주 · 생성 도중 · cwd 경합 · 반복 시험 10회
- [ ] HANDOFF 갱신 · 커밋 · 【확인요청】
