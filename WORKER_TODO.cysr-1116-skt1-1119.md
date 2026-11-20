# WORKER TODO — TICKET=cysr-1116-skt1-1119 (T1 r5c BLOCK 4 고침 → 1.1.16 위로)
- 브리프 = ~/axdev/master/briefs/1116-full/skt1.md (master#f7e5dd26) · 가지 feat/1116-skt1 ← dea2e1853
- [x] 1. T1(270e3e21e..e2f2ae889) 을 dea2e1853 위로 옮김(충돌 = 1.1.16 쪽 동작 우선)
- [x] 2. 옮긴 뒤 빌드·원 시험 초록(기준선 숫자 전후)
- [x] 3. r5c #1 낡은·가짜·헬퍼 등록으로 unknown@W 풀림 고침
- [x] 4. r5c #2 등록 S 읽고 #1 방어 통과 고침
- [x] 5. r5c #3 Tauri restore_judge_two 휴리스틱 8자 접두 「복원됨」 고침
- [x] 6. r5c #4 Codex 좌석 93→92 고착 고침
- [x] 7. 시험(원 시험 + 새 e2e + 뮤턴트) · ci-branch 팩 단계
- [ ] 8. codex 1R(고친 4건 재판정) · 처분 — ⏸ codex 한도 소진(master#5a93bd10 · 리셋 06:29) = master 대기열 · 질문지 CODEX-1R-PROMPT.cysr-1116-skt1-1119.md
- [x] 9. HANDOFF.cysr-1116-skt1-1119.md(맨 앞 = T1 공개 함수 이름·시그니처) · 【확인요청】

## codex 1R BLOCK(master#bea6fddc · 전부 고침 · 상한 3h) — 후임 몫(이 좌석 = 설계만 · HANDOFF §11)
- [x] R1-1 계통 3값 · follow = ProvenTop 만
- [x] R1-2 S 대화 파일 신선도 관문 + 기동 글 직전 재확인 + 검증된 S 등록 우선 승계
- [x] R1-3 데몬 session_source · caller None 등록 = 핀 입력 아님 · 비-Claude = lsof 만
- [x] R1-4 Tauri held 증거 fence·token·writer 재검증
- [x] R1-5 양성 S 신호 = anchor_session_id(최상위 훅)
- [x] R1-6 순서 주입 결정론 시험 + 뮤턴트 · codex 2R = master 대기열
- [x] 판정 축 표(lease 없이도 작성자 둘인가) = HANDOFF §11-1

## 후임(worker-1116skt1b · master#f7698dc5 · #8daa09dd · #4199fa4f) — HANDOFF §12
- [x] codex 1R 6건 고침(222206218) · R1-3 은 session_source 노출 대신 클라이언트 lsof + 데몬 비-claude 등록 거름(§12-1)
- [x] 독립 검증 V1(HR e2e) · V2(phoenix) · V3(표기) · V5(p1 HOME) · V6(관문 세대) · 끔 안내 1줄
- [x] e2e 고아 0(9fdf1990e · 원인 = 늦은 등록 autostart)
- [x] 시험 묶음 · e2e 12/12 · 뮤턴트 10 KILLED(MB 변이 불량 → MB2)
- [ ] CI 팩 단계 전체 재실행(시간 상한으로 미실행 · phoenix 관련 31 검체만)
- [ ] codex 2R = master 대기열
