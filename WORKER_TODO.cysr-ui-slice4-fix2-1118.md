# WORKER_TODO — TICKET=cysr-ui-slice4-fix2-1118 (조각 4 codex 1R 고침 · surface:2166 · 가지 feat/ui-slice4 ← 26d4f29c)

브리프 = master/briefs/2026-11-18-cysr-ui-slice4-fix2.md (원장 kind=brief · spawn · surface:2166 · body_sha256 98229725 = 파일 끝 줄바꿈 뺀 sha 일치)
앞 좌석 TODO = WORKER_TODO.cysr-ui-slice4-1118.md (2158)

## 할 일
- [x] §0 읽기(HANDOFF §0·§3·§6·§7·§12 · codex-r1.json · VERIFY §C)
- [x] B blocking: 직접 허락 = 데몬 지문 표지 있을 때만 · 없으면 거절 + 작업 화면 보기 + 안내 · feed_reply 지문 인자 자리(대역 시험)
- [x] M1 생존 모름 + 사건 뒤 새 출력 = deadman 해제 · 모름 관측만으로 deadman 근거 안 씀
- [x] M2 versionKey 에 surface_id · 판 구성 요소 바뀌면 펼침 해제
- [x] M3 socket_slug 누락·null·빈 = 버림
- [x] M4 org 형식 깨짐(마스터 상태 undefined) = 중단 · 마스터 좌석 모르는 동안 직접 단추 숨김
- [x] M5 기록만 해소 vs actuated 구분 → 「작업 화면에서 확인해 주세요」
- [x] M6 해결 대조 원문 코드 포인트 · 20번째 공백 보존 · 팩 문장 별도 커밋
- [x] m1 uuid 없는 반복 레코드 = 위치로 겹침 · 못 가르면 다 훑음 확정 안 함
- [x] 재현 시험 붉음→초록(지적별)
- [x] 게이트(31800d54: bun 3628/0 · tsc 0 · confirm 37/0 · chat 40/0 · tickrec 308dd2b91f9a · cargo app 348/0 · 팩 4본 0 · 뮤턴트 56/56): bun · tsc · confirm_gate · chat_gate · tickrec_gate OFF(308dd2b91f9a) · 뮤턴트 39+새 · 팩 4본
- [x] codex 2R 1회 = REVISE(major 2 · minor 1) → 고침 31800d54 · 3R 안 돌림
- [x] HANDOFF §13 · 【확인요청】 · 📌 데몬 지문 계약

## 이월
- §C idle_secs 실측 못 함 · 0.5 M4~M8 측정 대기 · 팩 지침 별도 커밋 원칙
