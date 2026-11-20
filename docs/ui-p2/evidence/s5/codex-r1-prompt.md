[리뷰 의뢰 — 엄격 제약 준수 · 지정 범위만]
검토 범위(이 파일/범위만, 무관 파일·repo 배회 금지): `git diff dea2e1853..HEAD` 가 바꾼 다음 파일 — src/bin/cysd/handlers.rs · src/bin/cysd/state.rs · src-tauri/src/viewcore.rs · ui/src/views/revive.ts · ui/src/views/judge/revive.ts · ui/src/views/judge/gate.ts · ui/src/views/core.ts · ui/src/views/chat/reviveband.ts · ui/src/views/index.ts · ui/src/main.ts(1줄). 바뀐 줄과 그 줄이 부르는 함수까지만 읽어라.
과업: cysr 대화 화면 「조각 5 — 마스터 멈춤·깨우기·다시 켜기」 적대 검토(설계 = 마스터 좌석 수명). 결함을 찾는 것이 직무다.
엄격 제약: 지정 파일과 과업만 · 서버·데몬·장시간 프로세스 기동 금지 · 파일 수정 금지(의견만) · git 쓰기 금지.

무엇을 바꿨나(작성자 설명 — 믿지 말고 코드로 확인):
1. cysd `surface.send_text`: 사람 입력 시각을 찍을 때 `Surface.human_input_seq` 를 1 올리고(stamp_human_input) 응답에 `human_input_seq` 를 싣는다. `refuse_on_approval` 원자 제출이 쓰기 0 으로 끝나면(clear_first_unsupported · no_agent · approval_screen · try_write 의 write_stalled/write_failed) 찍기를 되돌린다(unstamp_human_input — 그 사이 다른 찍기가 있었으면 안 되돌림). org.status 행에 `human_input_seq`·`agent_seen` 가산. role.claim_denied 사건에 `seat_human_recent` 가산.
2. viewcore: `chat_send{kind:"auto"}` = 큐 · machine_origin · operator_token 0 · 결과 queued/failed/uncertain. `write_stalled`·`write_failed` 를 「쓰기 전 거부(바이트 0)」 목록에 넣어 화면이 「못 보냄 + 다시 보내기」를 보인다.
3. 화면 gate.ts: 행의 human_input_seq 가 이 화면 마지막 원자 제출의 차례와 같으면 「사람 입력 30초」 쉼을 걸지 않는다.
4. 화면 revive.ts(+judge/revive.ts): 축 6(surface_gone·surface_exited·shell_proc_dead·agent_dead·seat_vacant_no_meta·agent_never_started) + vacant(앱 저장소 cys-master-seen·cys-master-gone) + 관문 + 조용함 판정 → 띠. 다시 켜기 = 누름 1 → start_master ≤ 1 · never_started 는 옛 좌석 pending_input_human_bytes 0 ∧ 붙여넣기 닫힘 확인 뒤 close_surface → start_master · 거절(claim_denied)이면 role.claim_denied 사건으로 seat_not_claimable ∧ 사람 입력 아님일 때만 65초 뒤 1회 자동 · 복원 중(restore-progress) 잠금 · 성공 = 목록 마스터 좌석 id 바뀜 ∧ agent_alive true ∧ 관문 없음 · 성공 뒤 옛 빈 셸(역할 없음·meta 있음·Empty·사람 입력 0) close_surface. 깨우기 = chat_send{auto} 1건 · 5분 거름 · 사람 보내기 뒤 30초 묶임이면 그 뒤 · 120초 안에 안 깨어나면 실패 안내.

특히 봐 달라(각각 결함 있음/없음 + 근거 file:line):
A. 데몬 stamp/unstamp: 경합(동시 자판 입력·다른 send_text)에서 남의 찍기를 지우거나 잘못된 차례를 남기는 길 · 차례 되돌림(seq-1)으로 같은 번호가 다른 입력에 다시 쓰여 화면이 남의 입력을 「내 보내기」로 짝짓는 길 · 락 순서·교착 · 되돌림이 빠진 쓰기 0 갈래 · 되돌리면 안 되는데 되돌리는 갈래(바이트가 실제로 나간 경우).
B. 화면이 다시 켜기로 **기존 좌석의 입력줄에 쓰는** 길(사람 초안 손실) · 사람이 쓰는 창을 닫는 길 · 엉뚱한 좌석(CSO·워커·사용자 셸)을 닫는 길 · start_master 를 두 번 이상 부르는 길(연타·자동 재시도·사건 재생·관문) · 자동 재시도 고리.
C. 성공·실패 판정 오판(고장 난 빈 셸을 성공으로 · 관문을 실패로 · 다른 길로 켜진 마스터를 놓침) · 앱 새로 켬 + 마스터 이미 꺼짐 → 꺼짐 띠가 안 뜨는 길 · 새 설치에 꺼짐 띠가 뜨는 길.
D. write_stalled/write_failed 를 「바이트 0 확정」으로 본 근거가 사람 원자 제출 길(clear_first · refuse_on_approval · human)에서 정말 성립하는가(writer 에 일부라도 들어간 뒤 이 코드가 나오는 길이 있는가).
E. 깨움 말이 원장 무기록(오너 임무)으로 들어가는 길 · 큐 폭주.

출력: 아래 JSON 한 덩이만 stdout 에(설명 산문 금지). verdict enum = ACCEPT|REVISE|BLOCK|ESCALATE · severity = blocking|major|minor · 점수 금지.
{"verdict": "", "justification": "", "evidence": [{"claim": "", "ref": "file:line", "verified": true}], "issues": [{"severity": "", "where": "file:line", "what": "", "fix": ""}], "missing": [], "revision": "HEAD"}
