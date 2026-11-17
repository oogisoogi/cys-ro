너는 적대적 코드 검토자다. 저장소 = 현재 작업 디렉터리(git 작업트리 · 가지 feat/ui-slice4 · 머리 ee510b85). **읽기만** 하라(파일 수정·명령으로 상태 바꾸기 금지). 지정 범위 밖 배회 금지.
이것은 2R 이다 — 1R 판정문 = docs/ui-p2/evidence/s4/codex-r1.json(BLOCK · blocking 1 · major 6 · minor 1 · 대상 e62e1fb0). 고침 커밋 = b00800df(코드) · 12e8bc95(팩 문장) · ee510b85(뮤턴트 도구). 1R 지적 8건이 닫혔는지와, 고침이 새로 연 구멍을 본다.

## 범위(이 파일들만)
- `git diff 26d4f29c ee510b85 -- ui/src/views/judge/confirms.ts ui/src/views/confirm.ts ui/src/views/chat/band.ts ui/src/views/judge/msgstep.ts src-tauri/src/viewcore.rs src-tauri/src/main.rs cysjavis-pack/directives/MASTER_DIRECTIVE.md` 와 그 파일들의 현재 내용
- 시험(읽기): ui/src/views/judge/confirms.test.ts · ui/src/views/confirm.test.ts · ui/e2e/confirm_gate.py
- 참고(읽기만 · 판정 근거): src-tauri/src/main.rs `async fn feed_reply` · src/bin/cysd/handlers.rs `"feed.reply" =>` 블록(actuated) · src/bin/cysd/governance.rs approval 감지(대기 항목 본문 재기록 안 함)

## master 결정(1R blocking 처분 — 이 결정 자체가 아니라 구현이 이 결정을 지키는지 본다)
화면만으로는 「지금 도우미 창이 펼친 그 명령인가」를 증명할 길이 없다. 그래서 직접 「허락」은 데몬이 「집행 직전 승인 창 지문 대조」를 지원한다는 표지(feed.list 항목 `screen_fingerprint` · 지금 데몬에는 없음 = 늘 닫힘)가 있을 때만 연다. 없으면 멈춤 때 직접 단추 = 「거절」 + 「작업 화면에서 그 창 보기」만(안내: 「마스터가 멈췄어요. 허락은 작업 화면의 그 도우미 창에서 직접 눌러 주세요.」). 지문 지원 자리(confirm_reply 의 screen_fingerprint 인자)는 만들어 두되 실제 켜짐은 데몬 쪽 계약이 생길 때. 거절은 펼침 없이 그대로.

## 1R 지적별 고침(확인 대상)
1. major 1: 생존 모름 + 사건 뒤 새 출력 = deadman 해제(걸쇠) · 생존 모름 관측만으로는 deadman 근거로 안 씀.
2. major 2: 펼침·항목 식별 versionKey 에 surface_id(+지문) · 판 구성 요소가 바뀌면 펼침 해제.
3. major 3: socket_slug 누락·null·빈 문자열 사건 = 버림(hqSlug 확정 ∧ 같을 때만).
4. major 4: org 응답 꼴 깨짐(마스터 상태 undefined) = 처리 중단 · 마스터 좌석 모르는 동안 직접 단추 숨김.
5. major 5: 새 Tauri 명령 viewcore::confirm_reply = 데몬 결과(actuated) 그대로 · null·없음 = 「기록만」 안내(「했어요」 아님).
6. major 6: 해결 대조 = 원문 코드 포인트 그대로(공백 정규화 되돌림) · 20번째 공백도 파싱에서 보존 · 팩 문장 「앞부분을 글자 그대로(띄어쓰기 포함) 20자」.
7. minor: 앞 훑기·뒤 읽기 겹침 = 레코드 위치(viewcore 레코드 `at` = 줄 시작 파일 바이트) · 위치 모르면 「다 훑음」 확정 안 함.

## 할 일
위 고침이 지적을 실제로 닫는지, 그리고 고침이 새로 연 **구체적 실패 경로**(입력·순서·경합 → 잘못된 confirm_reply 호출 / 지문 없는 판에 허락 / 잘못된 표시 / 표식 판독 순서 뒤집힘·이중 계수)를 찾아라. 특히: 지문 표지가 없는데 허락이 나가는 길, confirm_reply 결과 분류 오류, `at` 위치 계산 오류(깨진 줄·빈 줄·CRLF·여러 토막), Tauri 인자 이름(camelCase) 불일치.

## 출력(이 JSON 하나만)
{"verdict":"ACCEPT|REVISE|BLOCK","findings":[{"severity":"blocking|major|minor","file":"…","line":N,"title":"…","failure_scenario":"…","fix":"…"}],"closed_checks":["확인했고 문제 없는 항목 …"]}
