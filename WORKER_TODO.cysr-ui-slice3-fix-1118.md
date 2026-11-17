# WORKER_TODO — TICKET=cysr-ui-slice3-fix-1118 (조각 3 검증 1회 고침 · surface:2164)

- 브리프 = master/briefs/2026-11-18-cysr-ui-slice3-fix.md (원장 kind=brief · spawn 경로 · body_sha256 c39f5a47… = 파일 strip sha 일치)
- 기준 = fc36e805 · 상한 ≈03:55 · 60% 매듭

- [x] 0 §0 읽기(HANDOFF·VERIFY·조각1 §7·§9) + 재현 시험 옮기기(V1·V2·V3·V7·V8·V9) 붉음 확인
- [x] A 감싼 붙여넣기(pasted_content) 속 글 = 원문 전문 일치
- [x] B viewcore.rs 다른 종류 레코드 = 글 없는 고리 · 화면 사슬 잇기 · 안 묶인 답 시각순
- [x] C 짝 후보에 sending · 짝 없는 사람 레코드 소비 안 함
- [x] D O11·O14·O13 붉게 만드는 시험
- [x] E 보이지 않는 글자 떼고 첫 글자 / ! 막기 · 둘째 줄 같은 규칙 · 줄 나눔 확대
- [x] F 쓰기 직전 org 재조회 500ms 상한 · 실패=쓰기 0 붙잡음+안내 · 보내는 중 굳음 0
- [x] G HANDOFF 하네스 숫자 정정
- [x] H 같은 글 다른 말 전달됨 이상 → X 다시 보내기 거둠 + 안내
- [x] 시험: bun · tsc · chat_gate · tickrec_gate OFF · M2·M3 하네스(+다른 씨앗 3) · 뮤턴트(41+새) · cargo viewcore
- [x] codex 1R(e8ddaf65 BLOCK → 고침 1회 60185fe2)
- [x] HANDOFF 델타 · 커밋 · 【확인요청】
