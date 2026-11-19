# WORKER_TODO — TICKET=cysr-1116-flaky-1120 (팩 시험 간헐 붉음 2종)
- 이월: 이월 없음 (근거 = debt-u HANDOFF 📌7)
- 비가역·비용 결정 목록: _common.md 그대로 — push·태그·CI·gh 쓰기·발행·실사용 데몬 0 (워커 실행 금지)

- [x] 0. 대상 시험·훅 코드 읽기 · CI 실행 형태(ci-branch.yml) 확인
- [x] 1. 대조군: capgate 단독 N≥20 (부하 낮을 때) 실패율
- [x] 2. 대조군: role_authority_shell 단독 N≥20 실패율
- [x] 3. 부하 주입 재현율 + 실패 순간 원자료 계측
- [x] 4. 공유 자원 경합 표 (캐시 폴더·소켓 이름·시계)
- [x] 5. 원인 이름 붙이기 (대조군 뒤)
- [x] 6. 결정론 고침 (시험·훅 쪽만)
- [x] 7. 고친 뒤 N≥20 단독 + 부하 주입 0
- [x] 8. 뮤턴트로 시험이 대상 잡는지
- [x] 9. 동반 시험(role_authority·owner_desk·pyseal_negative·refl_inject·phoenix_c6_reap) 부하 판독
- [x] 10. 커밋 + HANDOFF.cysr-1116-flaky-1120.md + 【확인요청】

## 부하 주입 기록
- 주입 1: 04:34:45 ~ 04:49:15 KST (stress.py 첫 exec 폭주 2 + CPU nice10 4 · 1800s 예정 → master#3a0cce31 지시로 14.5분에 중단 · load 최고 27) — 규칙 위반(≤5분·≤2프로세스·nice 20) 인정, 이후 주입은 새 규칙으로만
