# HANDOFF — TICKET=cysr-1118u-chat (cysr 1.1.18 긴급판 갈래 A = 대화 화면)
가지 feat/1118u-chat · 기점 9c46ff6d0(v1.1.17) · 브리프 = ~/axdev/master/briefs/2026-11-23-cysr-1118-urgent-lanes.md

## ① 대화 화면 토큰 한도 줄
- 박사님 원문: 「윈 cysr 대화 화면에는 토큰 사용 표시가 안 보인다.」(11-23)
- 원인: `ui/src/views/index.ts` registry `onShown` 이 작업 화면 밖 화면을 켜면 `bodyRow.style.display = "none"` — 한도 표시는 bodyRow 안 왼쪽 상황판(`paintBoard` 의 limit/accounts 줄)과 #ws-usage 에만 있었다 → 대화 화면엔 한도 표시 0.
- 설계: 대화 화면 머리(.cv-head)에 `.cv-limits` 한 덩이. 값 = `statusboard.chatLimitRows(accountsCache, now)` — 상황판과 **같은 판정**(계정 ≥2 = `accountLimitRows` 그대로 · ≤1 = `limitLine`/`limitTitle` 한 줄 · 7d 없음 = 줄 없음). 원천 = main.ts 의 15초 `usage_accounts_all` 캐시(3초 사이드바 틱이 화면과 무관하게 계속 돎) → **새 RPC·새 invoke 0**. 배선 = BootDeps.limits → ChatCore Deps.limits → `act.limits()`(없음·던짐 = [] · invoke 0). 대화 화면은 5초마다 들여다보고 값이 바뀔 때만 다시 그림(말 목록 다시 그리기와 분리 · 입력칸 무접촉). 이름 = accountShortLabel(별명·폴더 라벨) = 이메일 0. 60/80 문턱 색 = 상황판과 같음.
- 216px 잘림: 대화 화면 머리는 사이드바가 아니라 가운데 칸이다 — 계정마다 한 덩이(덩이 안 줄바꿈 0 · 덩이 사이 접힘 · 이름만 14em 말줄임) → 폭 420/700/1400 실측 잘림 0·화면 밖 0.
- 시험: `ui/src/chatlimits.test.ts` 9건 — 기점 붉음 0/9 → 고침 초록 9/9 · 전 UI 시험 3987 pass / 0 fail · tsc 0.
  게이트 `ui/e2e/chatlimit_gate.py`(실제 번들 + chat_gate 대역 + 계정 2개 이메일 라벨): 기점 번들 FAIL 3(「한도 줄 보임」 3폭) → 고침 번들 fails [] (상황판 계정 줄과 같은 글 · 이메일 0 · 잘림 0 · 콘솔 오류 0).
- 해소 판정 남은 몫: 「그 판 빌드(맥·윈) 대화 화면 캡처」 = 통합 뒤 rel 좌석(윈 실기).

## ② 대화 화면 전달 3초 조회 틱 → 붙잡은 말 1초
- 근거: 윈 1.1.17 v2 실측(2374 05:56 · HANDOFF.cysr-1117-hotfix 윈 실기 줄) — 쉬는 중 도착 2.6~3.5s / 5.4~5.8s 양분 · 도착 초 mod 3 = 1 · K1 6/10 ≤5초 · K2(앞 답 끝 → 뒤 말 도착) 15.7s. 「도착」 = 마스터 jsonl user 레코드 시각 − 보낸 시각(win-chat-1117-v2.ps1:201) = 화면 탐지가 아니라 **실제 전달** 시각.
- 원인: 보낸 말이 문턱(답하는 중 · chatWorking = 자기 신고 없으면 출력 10초 정적)에 걸리면 붙잡히고, 다시 문턱에 거는 길은 대화 화면 `ctx.timers.every(POLL_MS=3000, poll)` 하나뿐 → 문턱이 열린 뒤 0~3초(초 mod 3 정렬) 늦게 나감. 열림은 시간(출력 정적)으로 정해져 알릴 데몬 사건이 없다 → 사건 구동 대신 박자.
- 설계: 대화 화면 시계 = 1초 `act.pollTick()`. ⑴ 온전한 조회(poll)는 POLL_MS 박자 그대로(100ms 흔들림 여유) ⑵ 그 사이엔 **자동으로 나갈 붙잡은 말**(가장 오래된 하나 · 쉼 notBefore 끝 · 쓰는 중 아님 · 살핌 중 아님)이 있을 때만 `heldPoll()` = 상태 조회(feed_list·org_status) → 단계 갱신 → 문턱 → 통과면 그 1건 deliver(쓰기 직전 재조회 그대로). 메뉴바·결과·표식 훑기·세션 기록 읽기 0 · lastWorking/lastPollAt 무접촉(기록 읽기 계기 그대로). ⑶ 상태 확인 늦음 계열(status_timeout·status_stale = 느린 윈 연결)은 1초로 올리지 않음(직렬 풀에 조회를 쌓지 않게). 작업 화면 띠의 POLL_MS poll 무변경.
- 시험 `ui/src/views/heldtick.test.ts` 6건: 대조군(종전 3초 poll) 문턱 열림 → 쓰기 지연 30위상 최대 2990ms(> 1초 = 원인 재현) · 고친 꼴 최대 990ms · 쓰기 정확히 1 · 붙잡은 말 없으면 30초 조회 수·종류 = 종전과 같음 · 붙잡힌 동안 org_status ≈1/초 · 다른 조회 종류 수 같음 · status_timeout 붙잡힘 = 9초에 조회 ≤3. 측정(시뮬 30위상): 종전 min 90 / 중앙 1590 / 최대 2990 / 평균 1540ms → 고침 min 90 / 중앙 590 / 최대 990 / 평균 540ms.
  기점 = 이 시험 파일 모듈 오류(FAST_POLL_MS·pollTick 없음 = 붉음) → 고침 6/6 · 전 UI 3993 pass / 0 fail · tsc 0.
  e2e chat_gate.py(patchright 주 세계 대역): 기점 번들 FAIL 6 = 고친 번들 FAIL 6 **같은 6항**(작업 화면 30초 조회 상한 3 · 진행 줄 단추 3 — 1.1.17 진행 줄(cysr-1118-ui ①) 이후 게이트 단언이 낡음 · 이 갈래와 무관) · 새 FAIL 0.
- 기대 효과(윈): 쉬는 중 도착 = 문턱 열림 + ≤1초(종전 ≤3초) · K2 = 15.7s 에서 최대 2초 줄어드는 몫(나머지는 출력 10초 정적 문턱 = 판정 정책 · 이 갈래 밖 📌). 확인 = 통합 판 윈 실기 v2 재실행.

## ③ 중계(RC) 메시지로 시작한 턴의 진행 줄이 앞 사람 말 밑에 붙음
- 관찰: 윈 실기 1.1.17(2374 05:56) — 사람 말이 아닌 중계 메시지로 시작한 턴의 진행 줄이 앞 사람 말 밑에 「답하는 중」.
- 채록(맥 master 세션 기록 · Claude Code 2.1.329 · 윈 좌석도 같은 CLI): 중계로 **시작한** 턴의 첫 레코드 = `type:"user" · isMeta:true · turnOrigin:"peer" · origin.kind:"peer"(from "bridge:session_…") · content = 문자열 "Another Claude session sent a message:\n<cross-session-message …>"` → 파서(viewcore.rs content_text) = role user · text 있음. 턴 **중에** 온 중계 = `attachment · queued_command`(고리 · 표본 11건 전부 도구 결과 뒤). 실측 분류(최근 250 기록): 턴 시작 user 의 가장 가까운 앞 레코드 = assistant end_turn/stop_sequence · 도구 결과 바로 뒤 글 있는 user = 그림 안내(isMeta) 86 · 스킬 본문 11 · 중단 표지 10.
- 원인: 레코드 사슬은 msgstep `applyRecords` :205(글 있는 user = 새 차례 → 사슬 닫기)에서 제대로 닫힌다(실기록 9구간 재생 = 중계 턴 도구 0건이 앞 말 과정에 붙음 · 답 = stray). 그러나 **앞 말의 단계는 그대로** → `settleSteps` 가 새 턴의 마스터 활동으로 delivered → 「답하는 중」을 다시 칠하고(답 글 없던 말), replying 인 말은 앞 턴 끝과 중계 턴 시작 사이에 조회가 「쉼」을 못 보면 그대로 남아 `liveMsg` 가 진행 줄(경과 초)을 계속 단다.
  (함께 드러난 같은 줄 결함) 도구 결과 바로 뒤의 글 있는 user(그림 안내·스킬 본문)도 「새 차례」로 보고 사슬을 끊었다 → 그 뒤 도구가 앞 말 과정에서 빠짐. 이 판에서 닫힘 조건을 고치며 함께 바로잡음.
- 설계: ⑴ Msg.tail = 사슬에 마지막으로 이은 레코드 종류(고리 제외 · assistant/result). 글 있는 user 가 tail=result 인 말의 사슬 끝에 오면 = 턴 안 덧붙임 → 고리로 잇고(tail 비움) 닫지 않음 ⑵ 그 밖(앞 턴 끝 뒤)이면 종전처럼 사슬을 닫고 + `turnClosed` = 전달됨 이상 말의 턴 끝 표지 · replying → 답 있으면 답함 / 없으면 전달됨 ⑶ settleSteps: turnClosed 말은 활동으로 칠하지 않음 ⑷ liveMsg: turnClosed 말엔 진행 줄 안 닮(「과정 N단계」 접힌 줄은 그대로).
- 시험 `ui/src/views/rcturn.test.ts` 6건(채록 모양 fixture): 기점 1 pass / 5 fail → 고침 6/6 · 전 UI 3999 pass / 0 fail · tsc 0. 원본 세션 기록은 개인 대화라 저장소에 넣지 않음(재생 스크립트는 작업 폴더 밖 · 모양만 fixture 로).
- 남은 확인: 통합 판 윈 실기에서 맥 master → 윈 master 중계 1회 뒤 앞 말 진행 줄 0.
