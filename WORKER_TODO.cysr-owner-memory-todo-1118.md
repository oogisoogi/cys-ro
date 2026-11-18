# WORKER_TODO — cysr-owner-memory-todo-1118 (worker-ownermem · surface:2185)
브리프 = master/briefs/2026-11-18-cysr-owner-memory-todo.md (원장 sha 대조 성립 · 10:03:25)
이월: 없음 · 비가역: push·태그·서명·발행 0 · 새 외부 서비스/과금/로그인 대행 = 【결정필요】

- [x] 0 조사: 기억 주입 경로 · 훅 배선 · 좌석 기동 인자 · 알림 길 전수 · CC 공식 문서(memory·hooks·effort)
- [x] 1 지속 지시 저장(javis_memory 재사용) + 안전망(턴 끝 자기 점검) + 지우기/목록
- [x] 2 오너 할 일 원장 + 아침 밀린 일 보고(결정론) + 사흘 넘은 일 질문 + 여러 일 순서 1줄
- [x] 3 끝나면 알림 = 장치 (알림 길 표 → 선택 → 일 끝 사건에서 1회)
- [x] 4 effort 기본 high (사용자 설정 존중) + 실측
- [x] 5 디렉티브 수정 시 합성기·doc-contract·줄범위
- [x] 6 재현 시험 ⑴~⑸ 붉음→초록 · 뮤턴트 · 전 스위트
- [x] 7 【중간보고】 1시간
- [ ] 8 codex 1R(→2R)
- [x] 9 실좌석 실사격(격리) 또는 한계 표기
- [ ] 10 HANDOFF + 【확인요청】

## 복원 메모(13:54 [RESTORE] 수신 · 재개 금지 · master 지시 대기)
- 커밋 머리 4ce6a80c(codex 2R 수리) · 작업트리 미커밋 = codex 3R 수리 중(javis_owner.py · javis_preflight.py PreToolUse 행 · owner-desk.sh pretool) — 시험 미초록(C28 등록 시험이 4사건 기대 · flush 시간 상한 시험 조정 필요 · 기계 부하로 전체 실행 지연)
- 3R 판정 REVISE(5 MAJOR·1 MINOR): compact 정산 해제 · 끝 (#번호)만 · 실제 발송 중복 거절(PreToolUse) · flush 데드라인 · 아침 보고 날짜 · 포기 뒤 늦은 성공 — 코드 수리는 작업트리에 있음
- 남은 것: 3R 수리 시험 정리·커밋 → 뮤턴트(45+) → HANDOFF 갱신(초안 = HANDOFF.cysr-owner-memory-todo-1118.md 미커밋) → 【확인요청】

## 복원 메모 2(15:41 [RESTORE] 수신 · surface:2223 · 재개 금지 · master 지시 대기)
- 커밋 머리 3a40e5c6(codex 3R 수리 · 시험 41/41 · 3R 6건 직전 머리 6/6 붉음)
- 작업트리 미커밋 = codex 4R 수리(MAJOR 2: 보내는 중 유예 동안 안내 횟수·포기 소진 금지 · 아침 보고 확인 날짜 후퇴 금지) + 시험 R10 2건 + 뮤턴트 하네스 시간 초과 처리 — 전체 시험 실행이 세션 종료로 끊겨 결과 미확인
- 남은 것: 미커밋분 시험 재실행 → 커밋 → 뮤턴트(53) 단독 실행 → test_dept_chat_inject_timeout 단독 재확인(부하 중 붉음 1) → HANDOFF 갱신(codex 1R~4R 원문은 재부팅으로 스크래치 소실 — 대화 기록에서 요지 재구성) → 【확인요청】

## 후임 좌석(surface:2229 · 계정2 · 11-18 18:5x · master#26302103)
- [x] test_owner_desk 1회 = 43/43 초록(46초) · R10 2건 = 수리 전 코드 2/2 붉음
- [x] codex 4R 수리 fix 커밋 · codex 5R 판단 = 불요(비밀값·데이터 비가역 무접촉)
- [x] 팩 14본 · javis_memory --self-test = master 통제 실행 전부 rc 0(adfcb006)
- [x] 뮤턴트 생존·NO-MATCH 처분 → 5a1de515 에서 시험 45/45 · MUTANTS ALL-KILLED 53/53 · HANDOFF §1·§3·§4 갱신
