[리뷰 의뢰 — 엄격 제약 준수 · 지정 범위만 · 2R]
검토 범위: `git diff 6f4ebeccc..HEAD`(1R 이후 고침) 와 그 줄이 부르는 함수 — src/bin/cysd/handlers.rs · src/bin/cysd/state.rs · ui/src/views/revive.ts · ui/src/views/judge/revive.ts · ui/src/views/judge/gate.ts · ui/src/views/core.ts · ui/src/views/index.ts · ui/src/main.ts(bootViews 1줄). 그 밖 배회 금지 · 서버·데몬 기동 금지 · 파일 수정 금지 · git 쓰기 금지.
과업: 1R(BLOCK) 지적 처분이 맞게 됐는지 + 고침이 새 결함을 만들었는지 적대 검토.

1R 지적과 작성자 처분(믿지 말고 코드로 확인):
B1 조회 뒤 비원자 close_surface → 완화만: 다시 켜기 누름 안에서 org.status 를 다시 받고 곧바로 판정·닫기 · 닫기 조건에 「30초 안 사람 입력(human_idle_secs) · 입력 시각 모름」 추가(judge/revive.ts restartPlan draft). 데몬 조건부 닫기(원자) = 이 갈래 데몬 변경 허용 범위(응답 칸·사건 칸만) 밖이라 미적용 · master 결정으로 올림. → 이 완화가 남기는 창의 크기·현실성을 판정하라.
B2 저장소 번호 재사용으로 엉뚱한 좌석 닫기 → 정리 대상 = 신원(surface_id + 데몬이 매긴 created_at) 일치만(leftoverShell · seatIdOf · storedSeat). 등록 에이전트(meta) 좌석만.
M1 쓰기 0 갈래 되돌림 누락 → HumanStampGuard(drop 시 되돌림 · writer 인계 직후 commit). 
M2 seq-1 되돌림 ABA → 발급기 human_input_issued 단조 · 현재 번호 human_input_seq · 표지 human_input_stamp "<데몬 기동 ms>:<번호>" 를 응답·org.status 에 · 화면은 문자열 전체 비교.
M3 복원 잠금 누락 → main.ts briefGate(restoreStarted && !restoreFinished)를 deps.restoring 으로 · 장부가 restoring || deps.restoring() 로 잠금.
M4 관문 보류 뒤 연타 → gate_wait 단계(관문 좌석 또는 정상 보일 때까지 · 최대 30초) 동안 다시 켜기 잠금.
M5 등록 없는 빈 마스터 좌석(사건 없음) → vacantNoMetaEvidence(agent null ∧ seat empty ∧ agent_alive null) 90초 지속 ∧ (본 적 있음 ∨ 놓아짐 기록) → 꺼짐.
M6 같은 좌석 되살림 → restartSucceeded(before, m, beforeAlive): 같은 좌석은 다시 켜기 전 생존이 아니었을 때만 성공.
M7 표식 세대 결속 → SEEN_KEY 를 신원 JSON 으로(정리 근거) · 꺼짐 띠 판정은 그대로(표시만 · 파괴 없음) — 남은 위험 판정해 달라.
m1 깨움 거름 저장(cys-chat-wake-at) · m2 깨어남 판정 (idle_secs+1)*1000.
실물 실측 추가(격리 데몬): ⑴ 120초 안 같은 role+agent+cwd 다시 기동 = launch-agent 가 같은 좌석 멱등 재사용 + 기동 줄을 clear_first 없이 그 셸에 침 → 모든 축에서 옛 마스터 창에 사람 초안·30초 안 입력이면 다시 켜지 않게 함. ⑵ phoenix 자동 회생이 같은 좌석을 먼저 살려 start_master 가 claim_denied(seat_not_claimable) → 자동 1회 기다리는 중 마스터가 살아 보이면 기다림 거둠.

특히: guard 의 commit 위치가 「바이트가 나갈 수 있는 첫 지점」 앞뒤로 맞는가(commit 전 반환 중 실제로 바이트가 나간 갈래가 있는가 · commit 뒤 반환 중 바이트 0 인데 남는 갈래) · Drop 이 다른 락을 쥔 채 불려 교착 · 표지 문자열이 옛 화면(숫자 기대)과 맞물려 깨지는 곳 · gate_wait·retry_wait 해제 조건이 영영 안 풀리는 길 · 새 판정이 새 설치·정상 마스터에 거짓 꺼짐 띠를 띄우는 길.

출력: 아래 JSON 한 덩이만 stdout 에. verdict = ACCEPT|REVISE|BLOCK|ESCALATE · severity = blocking|major|minor · 1R 지적마다 closed/open 을 evidence 에.
{"verdict": "", "justification": "", "evidence": [{"claim": "", "ref": "file:line", "verified": true}], "issues": [{"severity": "", "where": "file:line", "what": "", "fix": ""}], "missing": [], "revision": "4f224a25b"}
