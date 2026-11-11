# WORKER_TODO · TICKET=cysr-agy-door-r5 (surface:1994 · 착수 2026-11-11 22:29 KST)

브리프 = ~/axdev/master/briefs/2026-11-11-cysr-agy-door-r5.md (원장 22:28:59 spawn 브리프 · 대상 surface:1994 · submitted=true)
보충 = master#7f3602d7(원장 22:29:07 · 대상 1994) — 미커밋 acceptance.py 변경 = E12~E16 + 묘비 rc 단언 → 검토 후 커밋 포함

- [x] 원자료 읽기(4R 판정문 · HANDOFF · agy_door.rs · 호출부)
- [x] 미커밋 acceptance.py 확인 — E12~E16 실행 코드 + 묘비 rc 단언이 들어 있음(발견 6 원인 = 커밋 누락)
- [ ] 1. 판정 방식 분리: 기계 입구 = 낱말 검사(+바이트 상한) · guard/cys run = 실행 자리 검사(발견 5 거짓 양성 고침 · 치환 수 상한)
- [ ] 1b. agy-door-check --machine · round-log 폴백 = 같은 낱말 검사(python)
- [ ] 1c. 변이 생성 시험(인용·치환·래퍼·대소문자·확장자) — 이름이 글자로 든 꼴 통과 0
- [ ] 1d. 입구 ↔ 판정 방식 표 문서 + 입구별 시험
- [ ] 2. 발견 1: phoenix 정책 전용 실행에서 차단기 읽기·쓰기 0 · 오라클 성공/실패 시험
- [ ] 3. 발견 4: 사람 표시 ∧ 기계 출처 아님 → 토큰 미확인이어도 통과 + 원장 「토큰 미확인 통과」
- [ ] 4. 발견 6: acceptance 하네스 커밋(E12~E16 · 묘비 (rc,출력) · 커밋·바이너리 결속 · E13 데몬 사유 단언 · 동시 5회 원시 기록)
- [ ] 5. 발견 7·8: 문 열기/닫기 직렬화 + 고유 tmp + 경합 시험 · 판정 입력 상한
- [ ] 6. 4R 「문제없다고 본 것」 회귀
- [ ] 7. 시험: 빌드 · lib agy_door · acceptance · 팩 · 뮤턴트 · 실 agy 0
- [ ] 8. 문서(알려진 한계 · 경계 표) · HANDOFF 갱신 · 【확인요청】
