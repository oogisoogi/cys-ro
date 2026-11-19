# WORKER_TODO — TICKET=cysr-1116-s5-1119 (조각 5 멈춤·깨우기·다시 켜기·물러남)

- 가지 feat/1116-s5 ← integ/1116 dea2e1853 · 브리프 master/briefs/1116-full/s5.md · 상한 4h
- 비가역 0: push·태그·CI·gh 쓰기·서명·발행·앱 교체·실사용 데몬 = 안 함

## 할 일
- [ ] 1 데몬 가산(허용 범위): org.status `agent_seen`·`human_input_seq` · send_text 사람 원자 제출 응답 `human_input_seq`(S1-5) · 쓰기 0 거부면 사람 입력 시각 되돌림(S1-10) · role.claim_denied `seat_human_recent`
- [ ] 2 viewcore: chat_send{kind:auto}(큐 · machine_origin) · write_stalled/write_failed = 못 보냄(S1-8)
- [ ] 3 gate/core: 내 보내기 짝짓기(human_input_seq 같으면 30초 면제)
- [ ] 4 judge/revive.ts(순수) — 축 6 + vacant + never_started + 관문 + 띠 판정 + 성공 판정
- [ ] 5 revive.ts(장부) — 깨우기(5분 거름·120초·R3 30초 뒤) · 다시 켜기(축별 길 · 65초 1회 · 복원 중 잠금 · 연타 잠금 · boot-degraded · vacant 정리)
- [ ] 6 띠 그리기(chat) + 작업 화면 관문 안내 + main.ts 배선 1줄(focusSeat·openHelp)
- [ ] 7 bun 시험(축 6 · vacant · never_started 닫기 · 사람 입력 사유 · 거절 3 → ≤1 · 좌석 수 · 사람 입력줄 바이트 0 · 앱 새로 켬) + 뮤턴트
- [ ] 8 cargo 시험(바뀐 크레이트) + tsc + ui 게이트 + CI 팩 단계
- [ ] 9 codex 1R
- [ ] 10 HANDOFF.cysr-1116-s5-1119.md + 커밋 + 【확인요청】
