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

## ⑤ e2e chat_gate 기점 FAIL → 0 (master#ac1fa52a)
- ⚠정정: ② 보고의 「기점 FAIL 6 = 고침 FAIL 6」은 **patchright 대역**(python playwright 미설치라 patchright 를 별칭으로 씀)의 수치였다. 진짜 playwright 1.65.2(작업 폴더 밖 임시 venv · chrome-headless-shell 1248)로 다시 잼:
  | 번들 | 결과 |
  |---|---|
  | 1.1.16(bc8156865) | PASS (63 ok) |
  | 1.1.17 기점(9c46ff6d0) | FAIL 3 |
  | 이 가지 | FAIL 3 (같은 3항) |
  patchright 에서만 난 3항(작업 화면 30초 조회 상한 org_status·feed_list 12~13 · 응답 없이 3초 단계)은 대역 차이 = 코드 결함 아님(진짜 playwright 에선 1.1.16·1.1.17·이 가지 모두 통과).
- 항목별 판정(3항 = 「응답 없이 3초 → 확인 중 · 단추 0」 · 「쓰기 직전 거부 사건 → 확인 중 · 다시 보내기 0」 · 「120초 → 오래 걸려요 · 다시 보내기 0」): **낡은 단언**. 실측 btns = ['•확인 중 · 3초'] 등 = 1.1.17 진행 줄(cysr-1118-ui ①)의 머리 `button.cv-prog-head`(「과정 보기」 펼침 · 단계 없으면 disabled · 누르면 openProg 만 바꿈 = chat/index.ts prog()) — 단언의 뜻(다시 보내기·보내기 단추 0)과 무관. 1.1.16 = 진행 줄 없음 → 통과했던 것.
- 고침(게이트만 · 앱 코드 0): bubble() 두 곳(I·J 절)의 단추 셈에서 `.cv-prog-head` 제외 + 따로 `prog` 수 · 새 단언 「진행 줄 머리 1개 = 펼침 전용(눌러도 쓰기 0)」(뺀 것이 보내기 단추가 아님을 시험으로 묶음).
- 결과: 1.1.17 기점 PASS(64 ok) · 이 가지 PASS(64 ok) · 1.1.16 = 새 단언만 FAIL(진행 줄 없는 판 · 예상대로) — 진짜 퇴행 0.

## ④ 복원 카드 「다시 켜졌어요」 옛 SESSION_STATE — master 판정 A(원장 9c2bfbb3 · 11:24)
- 원인(코드 실측): 카드는 정본 `~/.cys/pack/round/SESSION_STATE.md` + 마스터 작업 폴더의 가장 가까운 `_round/SESSION_STATE.md`(재시작 [DRAIN-VERIFY] 가 「_round/SESSION_STATE.md 에 저장」으로 쓰는 곳 · src/bin/cys.rs:22973)를 읽고 `pickBriefText` 로 고른다 — ①3절 있는 파일만 ②3절 안 「기록」 줄 있는 파일이 시각 무관하게 먼저 ③같은 줄이면 늦은 쪽. 정본을 마스터가 계속 고쳤어도 3절 기록 줄이 없거나 3절이 없으면 옛 재시작 저장분(기록 줄 있음)이 계약대로 뽑힌다 — 계약 시험(판정 B 후속 「반대 방향」 등)이 이 모양을 의도로 박아 둠. 윈 측정은 윈 master offline 으로 미실시(A 는 경로 무관하게 성립).
- 시도·기각(B): 「다른 파일에 늦은 손길 → 그 3절 안 고름」 = 계약 시험 5건 붉음(검토 합의 뒤집기) → 되돌림 · master 기각.
- 설계(A): 고르기 계약 그대로 · `briefNewerElsewhere(found, text, now)` = 고른 3절 시각(recordedAt)보다 **다른 후보 파일**의 가장 늦은 「YYYY-MM-DD HH:MM」(`latestStamp` · 지금 이후 = 예정은 뺌)이 늦으면 참 · 고른 요약 시각 모르면 거짓. 참이면 카드 요약 바로 앞 절 「알려 드려요」 = 「이 요약은 <시각> 기준이라 그 뒤 일은 빠졌을 수 있어요.」(내부 용어 0 · 물음표 0). 종전 꼬리말(흐린 12px · 늘 나옴)은 그대로.
- 시험 `ui/src/restorebrief.stale.test.ts` 8건(나옴 2 · 안 나옴 4 · 문구·배선 2): 기점 = 모듈 오류(붉음) → 8/8 · 계약 시험 restorebrief(.producer).test.ts 80건 무변경 전부 통과 · 전 UI 4007 pass / 0 fail · tsc 0.
- 216px: 카드 폭 216(창 248)에서 알림 줄 3줄 접힘 · 잘림 0 · 넘침 0 / 1280 = 1줄(정적 렌더 · 진짜 playwright).
- 📌 C(다음 판 · 구현 0) 설계 3줄:
  1. [DRAIN]·[DRAIN-VERIFY] 문안(src/bin/cys.rs:6961 · :22973)의 「_round/SESSION_STATE.md」 → 「`${CYS_PACK_DIR:-~/.cys/pack}/round/SESSION_STATE.md`(정본) 맨 위 3절 + `기록 <date '+%F %H:%M'>` 줄을 고쳐 써라」로 못박아 재시작 저장이 카드가 먼저 보는 정본을 새로 쓰게 한다.
  2. 문안 바뀜 = 문안 고정 시험(cys.rs:33482 등)·inject_guard 표지 대조를 같이 고치고, 팩 디렉티브 §9 와 문구를 맞춘다(디렉티브를 고치면 합성기 재실행 + doc-contract + 줄범위 3줄).
  3. 옛 작업 폴더 `_round` 사슬 읽기는 한 판 더 남겨(옛 설치 호환) 정본 기록 줄이 있으면 늘 이기게 되면서 A 알림은 드물게만 뜬다 → 그다음 판에서 사슬 읽기 걷기 검토.

### ④ 재검(master#bcc58fe0 · 윈 실측 회신) — 가설 정정 · 같은 파일 안 고침
- 윈 실측: 정본 = 3절 머리(3 「## 완료」 · 7 「## 진행 중」 · 9 「기록 2026-11-23 06:01」) 뒤에 「## [날짜 DRAIN-VERIFY …]」 절이 최신순(11 06:01 · 19 05:38 · 26 11-22 11:04 …) · 작업 폴더 _round = 3절 없음(후보 탈락). → 앞 가설(작업 폴더 _round 가 계약 ②로 이김) **틀림**.
- 재현(그 모양 픽스처 · 기점 코드): `parseBriefSections`·기록 줄 판정이 **파일 전체의** 3절 제목을 모았다 → 아래 날짜 절 안의 「## 완료/## 진행 중」 항목(옛 11-22 일·재시작 대기)이 카드에 섞이고, 3절 기록 시각도 아래 절의 기록 줄(05:38)까지 비교했다. 또 맨 위 3절이 멈춘 채(관찰 05:56 = 9행 기록 줄이 06:01 로 바뀌기 전) 같은 파일 아래 절에 새 일이 쌓여도, A(다른 파일만 봄)는 알림을 안 냈다.
- 고침(계약 시험 80건 무변경 통과): ⑴ `briefBlock` = 파일에서 처음 나오는 3절 묶음 하나만(첫 3절 제목 ~ 3절 아닌 제목 앞) — 지침 §9 「맨 위 세 절」 그대로 · 항목·기록 줄 모두 이 묶음에서만 ⑵ `briefNewerElsewhere` 가 고른 파일 **자신**의 가장 늦은 시각도 본다(카드 시각·고르기는 그대로 = 판정 B 계약 · 알림만).
- 시험 +3(윈 모양 05:56 = 맨 위 3절만 · 시각 11-22 11:04 · 알림 / 06:01 = 알림 없음 / 같은 파일 대장만 늦음 = 알림): 직전 커밋 3 fail → 11/11 · 전 UI 4010 pass / 0 fail · tsc 0.
- 남은 불확실: 05:56 당시 파일의 정확한 내용은 모름(회신은 06:01 이후 상태) — 어느 경우(맨 위 3절 낡음 · 아래 절 항목 섞임)든 이 고침으로 「낡은 요약을 지금 것처럼」은 안 남는다. 근본(마스터가 맨 위 3절을 안 고치고 날짜 절만 쌓음)은 C(생산자 문안) 📌.

## codex 1R(갈래 끝 1회 · 287db655b 기준 · read-only · REVISE major 2 / minor 1) → 3건 모두 받아 고침
- codex 원문 판정 = REVISE(정본 verdict JSON 은 codex 세션 read-only 로 저장 못 함 · cys send 도 소켓 권한으로 실패 — 판정문은 실행 출력 원문). 세 건 모두 코드로 내가 다시 확인 → 타당.
  1. major core.ts heldPoll — 답하는 중으로 붙잡힌 뒤 연결이 멈추면 가벼운 조회가 매초 끝나지 않는 org_status 를 쌓음(9초 3 → 9). 고침 = freshBounded 가 시간 상한을 넘기면 `lastFreshTimedOut` → fastWanted 거짓(3초 박자) · 다음 조회가 제때 끝나면 풀림. 시험 2(멈춤 9초 = 종전 3 + 첫 감지 1 이하 · 회복 뒤 ≤1초 쓰기).
  2. major msgstep — 결속이 풀렸다 다시 묶일 때 turnClosed 이월(잘못 결속 → 닫힘 → 늦은 held(mergeOutcome :313) → 재전송 결속 = 「전달됨」·진행 줄 0 으로 굳음). 고침 = mergeOutcome 결속 풀기·applyRecords 새 결속·rematchPending 새 결속 셋 다 turnClosed·tail 비움. 시험 2(codex 재현 순서 그대로 · rematchPending).
  3. minor chat_gate — 새 「펼침 전용」 단언이 disabled 단추를 눌러 저절로 통과. 고침 = I 절은 「disabled · 쓰기 0」으로 정직하게 · B 절(과정 있는 말)에서 실제 누름 → aria-expanded true · 과정 1줄 → 다시 누름 → 접힘 · 쓰기 0.
- 결과: 새 시험 기점(e1874513e) 3 fail → 16/16 · 전 UI 4014 pass / 0 fail · tsc 0 · 진짜 playwright chat_gate 기점·이 가지 65 ok PASS · s79 46 · tickrec 28 · runtime_defer 23 · confirm 37 전부 PASS.
- codex 2R 은 돌리지 않음(브리프 「codex 호출 = 갈래 끝에 1회」) — 재검토 필요 여부는 master 판단.

## CI 45101212903(e1874513e) 붉음 → 고침 0b44cad72
- boot-health-full: 171 중 FAIL 1 = H-SECRET-1 secret-scan WIN-PATH — 내가 restorebrief.stale.test.ts:80 주석에 실측 회신의 실제 윈 사용자 경로를 옮겨 적음(공개 저장소 · 계정 이름 1개 노출 · e1874513e·ec7132214 에 들어감). 고침 = ~ · 픽스처 폴더 이름 더미 · secret-scan --all clean(2170 파일).
- macos-rust-pack cancelled = 「The run was canceled by @oogisoogi」(03:02Z) → 뒤 C8 두 단계 exit 2 는 취소 여파(시험 실패 아님).
- 이력 처리 = master 결정 대기(권고 A: 빨리감기 고침 + 통합 때 squash 로 main 에서 제외 + 통합 뒤 가지 삭제).
