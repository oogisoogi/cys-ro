# WORKER_TODO — TICKET=cysr-no-hands-gui-1118 (사용자가 일하는 동안 자비스가 손을 빌리지 않게)

- 브리프 = ~/axdev/master/briefs/2026-11-18-cysr-no-hands-gui.md (원장 surface:2186 · sha 7282c932… 일치 확인)
- 가지 feat/no-hands-gui-1118 ← 7d25c38e · push·태그·서명·발행 0 · 박사님 화면 GUI 조작 0

## 할 일
- [x] 0 브리프 원장 대조 · 기준선(MASTER_DIRECTIVE 예산 핀 기준선 = 이미 붉음 86,642 > 85,365)
- [x] 1 화면·앱 조작 길 전수 조사표(맥/윈 · 입력을 건드리는가)
- [x] 2 유휴 관문 도구 bin/javis_idle_gate.py(idle·wait·mark·check·end·pending · 맥 ioreg · 윈 GetLastInputInfo · 가짜 시계)
- [x] 3 시험 bin/tests/test_idle_gate.py(20초 전 0 · 도중 입력 멈춤 · 시간 초과 미룸 · 윈 단위 · 손 떼기 요청 문장 0)
- [x] 4 뮤턴트 bin/tests/mut_idle_gate.py(관문 끄면 붉음)
- [x] 5 스킬 computer-control 절 + 도구 hwp 문구 · 한글 작업 길 표
- [x] 6 MASTER_DIRECTIVE 짧은 한 절 → CEO_TEMPLATE 재합성 · 해시표 재생성
- [x] 7 팩 파이썬·doc-contract·합성기 재실행(재부팅 뒤 13:5x · computer_control 112 · doc_contract·event_inject·cu_audit·import_guard·pyseal rc 0 · 합성기 GREEN·OK · cso_directive_rev = 기준선부터 붉은 예산 핀 1건)
- [x] 8 codex 1R(REVISE → c4b4ffe1) · 2R(REVISE · 결정 master#18af38d1→#16466ff6 = 일반 앱 Q=0 · 카톡·메일·한글 Q=20)
- [x] 9 2R 고침 검증 — 66dfd324 기준 test_idle_gate 38 OK · mut_idle_gate 27/27 KILLED
- [x] 10 지침 절 축소(469 → 319 B · 「한 번에」 삭제 · master#30990c7b A)
- [x] 11 integ/1116 로컬 병합(충돌 해소 · push 0) → 상한 +축소분 → cso_directive_rev·doc-contract·합성기 초록
- [x] 12 codex 재검토 1회(BLOCK 7건 고침 · 시험 49 · 뮤턴트 37) → HANDOFF §4·§7·§9 → 【확인요청】
- [x] 13 codex 4R ACCEPT(다음 판 3건 = HANDOFF §7) · lane-parity 미등재 3건 등재 · 홈 절대 경로 제거
- 복원 메모(11-18 두 번째 [RESTORE] · 좌석 2212): 재부팅 뒤 [RESUME] 로 다시 돌린 관문 시험+뮤턴트가 또 끊김(결과 없음) · 이전 메모: 재개 금지 · master 지시 대기 · 다음 첫 행동 = `python3 cysjavis-pack/bin/tests/mut_idle_gate.py`(백그라운드) 결과 확인

## 이월
이월 없음.

## 비가역·비용 결정 목록
해당 없음(발행·push = master).
