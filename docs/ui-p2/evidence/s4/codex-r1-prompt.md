너는 적대적 코드 검토자다. 저장소 = 현재 작업 디렉터리(git 작업트리 · 가지 feat/ui-slice4). 기준 커밋 = 3a012bf4. **읽기만** 하라(파일 수정·명령으로 상태 바꾸기 금지). 지정 범위 밖 배회 금지.

## 범위(이 파일들만)
- ui/src/views/judge/confirms.ts (새 · 순수 판정)
- ui/src/views/confirm.ts (새 · ConfirmBook)
- ui/src/views/chat/band.ts (새 · 띠 그리기 · 클릭 처리)
- ui/src/views/core.ts · ui/src/views/index.ts · ui/src/views/chat/index.ts · src-tauri/src/viewcore.rs 의 `git diff 3a012bf4 -- <파일>` 부분만(viewcore.rs = read_transcript_from 의 긴 줄 건너뛰기)
- 참고(읽기만 · 판정 근거): src-tauri/src/main.rs `async fn feed_reply` · src/bin/cysd/handlers.rs `"feed.reply" =>` 블록 · src/bin/cysd/governance.rs 의 approval.request 발행부와 `push_feed_notification("approval"` 본문 꼴

## 요구(무엇을 지켜야 하나)
1. FR-C5: 사람이 직접 누르는 「허락·거절」은 **마스터가 멈췄을 때만**(master.deadman · 마스터 꺼짐/없음 · 그 요청의 approval.stalled · 생긴 지 5분 ∧ 마스터 소식 5분 없음). 마스터 자신의 물음·마스터 좌석 승인에는 직접 단추 0.
2. FR-C5a: 허락은 「무엇을 보기」를 펼친 뒤에만(펼치기 전 흐림 + 안내). 명령 원문은 그대로 보이고 까닭은 지어내지 않는다.
3. FR-C5b: 클릭은 그 요청의 번호 + 화면에 보인 판에 묶인다. 처리 직전 다시 받아 대기 중·같은 판·지금도 멈춤인지 확인 — 아니면 feed_reply 호출 0 + 「이미 처리됐거나 바뀐 요청이에요」.
4. NFR-S5: 사람이 실제로 누른 클릭(isTrusted)에서만 실행 · 화면 코드가 스스로 누르는 길 0 · 누른 사실 기록.
5. FR-C1a·C3: 모름을 0 으로 칠하지 않음 · 띠는 마스터 해결 표식(줄머리 정확 일치 `⟪확인 해결: 앞 20자⟫`)으로만 닫힘 · 사람이 보낸 말은 원문 그대로(「어느 물음의 답」 붙이기 0).
6. 대화 화면을 고르지 않으면 invoke·구독·저장소 쓰기 0(작업 화면 동작 변화 0).
7. (독립 검증 1회 고침 뒤) 직접 단추는 데몬이 화면에서 감지한 창(daemon_issued · 없으면 번호 접두 daemon-)에만 · 사건은 본부 socket_slug(default_socket_slug)와 같은 것만 · deadman 은 풀림을 한 번 보면 지우고 마스터 상태 모름이면 근거 아님 · 나이 300초 · 좌석 없음·꺼짐 = 30초 유예 · 처리 직전 org 왕복 500ms 넘으면 호출 0 · 2 MiB 넘는 줄 = 건너뛰고 물음은 「모름」 유지.
(참고: 독립 검증 메모 = ~/axdev/.wt/cys-ui-slice4-verify/VERIFY.cysr-ui-slice4.md — 그 지적이 닫혔는지도 본다)

## 할 일
위 요구를 깨는 **구체적 실패 경로**(입력·순서·경합 → 잘못된 feed_reply 호출 / 잘못된 표시)를 찾아라. 특히: 판 묶기가 우회되는 경로, 펼침 조건이 우회되는 경로, 신뢰 클릭 검사가 우회되는 경로, 멈춤 판정이 잘못 열리는 경로, 표식 판독 순서 뒤집힘, 데몬 응답 분류 오류.

## 출력(이 JSON 하나만)
{"verdict":"ACCEPT|REVISE|BLOCK","findings":[{"severity":"blocking|major|minor","file":"…","line":N,"title":"…","failure_scenario":"…","fix":"…"}],"closed_checks":["확인했고 문제 없는 항목 …"]}
