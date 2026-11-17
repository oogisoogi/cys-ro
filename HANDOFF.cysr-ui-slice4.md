# HANDOFF — TICKET=cysr-ui-slice4-1118 (cysr 화면 개편 조각 4 「확인 대기」 · 워커 surface:2158 · 2026-11-17 23:4x ~ 11-18)

- 브리프 = `master/briefs/2026-11-18-cysr-ui-slice4.md`(원장 kind=brief · spawn 경로 · surface:2158 · submitted true) · 가지 `feat/ui-slice4` ← `feat/ui-slice1` **3a012bf4**
- 설계 = `~/axdev/cysr-ui-research/P2-DESIGN.md`(7ba74f3) §11 조각 4 · §5-4 · §5-1 · §2-7 · PRD FR-C1~C6(C1a·C5a·C5b) · NFR-S5 · NG6
- 비가역 0: push · 서명 · 발행 · 이 기기 앱 교체 = 안 함 · **데몬(handlers.rs·state.rs·governance.rs) 변경 0** · 원작자 화면 파일(main.ts·index.html·build.sh·main.rs) 변경 0
- 조각 3 경계: 보낸 말 단계·다시 보내기·30초 묶음 = 손대지 않음. 공용 파일(core.ts·chat/index.ts·index.ts)은 덧붙이기만(§1)

## 0. 한눈 요약

| 무엇 | 결과(관측) |
|---|---|
| 확인 대기 띠 | 대화 화면 맨 위 · **한 번에 하나**(「다음」으로 넘김 · `1 / N`) · 머리 「확인이 필요해요 N」 · 모르면 「확인할 것 살펴보는 중」 · 0건 확정이면 숨김 · 최소 계약 칸 `[data-min=confirms]` = 같은 값 |
| 마스터 물음 표식 | 마스터 답(assistant 레코드) 글의 **줄머리 정확 일치** `⟪확인 요청: …⟫` 만 · 해결 = `⟪확인 해결: <앞 20자>⟫`(실린 글 전부가 물음 앞부분과 같아야) · 줄 중간·들여쓰기·코드 울타리 안·사람 글·곁가지 = 0 · **표식 없으면 띠 0(꾸미지 않음)** |
| 대화를 열기 전 물음 | 결속 세션 기록을 처음부터 3초마다 한 토막(2 MiB)씩 훑음 — 다 훑기 전 = 「살펴보는 중」 |
| 대화에서 답하기 | 누르면 그 물음이 있는 마스터 말풍선으로 스크롤·테두리 + 입력칸 포커스 + 입력칸 위 「답하는 물음: …」 줄 · **입력칸 글은 건드리지 않음 · 보낸 말 = 원문 그대로**(물음 글·꼬리표 0) · 띠는 마스터 해결 표식으로만 닫힘 |
| 도우미 허락(feed approval) | 평소 「도우미가 허락을 기다려요 — 마스터가 확인하는 중」(단추 0 · FR-C6) |
| 마스터 멈춤 때만 직접 허락 | 멈춤 = master.deadman(그 뒤 같은 마스터가 출력했거나 새 마스터가 서면 풀림) · 마스터 꺼짐/없음 · 그 요청의 approval.stalled · 생긴 지 5분 ∧ 마스터 소식 5분 없음 → 「무엇을 보기」(명령 원문 그대로 · 기계 추정 · 「왜는 도우미 화면에 없어요 · 마스터를 깨워 물어보세요」 · 12행/600자 닿으면 잘림 안내 + 작업 화면에서 보기) → 허락(펼치기 전 흐림 + 안내)·거절 |
| 신뢰 클릭 · 판 묶기 | `e.isTrusted` 아니면 아무것도 안 함 · 단추 = 그리기 순간의 판(번호·시각·본문·좌석) · 누르면 **처리 직전 feed·org 다시 받기** → 같은 판 ∧ 대기 중 ∧ 지금도 멈춤 ∧ 지금 마스터 좌석 것 아님 → feed_reply 1회 / 아니면 호출 0 + 「이미 처리됐거나 바뀐 요청이에요」 · 누른 기록 `cys-chat-decisions`(번호·결정·시각·결과 · 명령 원문 0자) |
| 마스터 좌석 자신의 승인 | 「마스터 창에 확인할 것이 떠 있어요 — 작업 화면에서 답해 주세요」 + 「작업 화면에서 보기」(직접 단추 0) |
| 작업 화면 동작 변화 0 | tickrec_gate OFF = 기준 번들(3a012bf4) 같음 · sha `308dd2b91f9a` · invoke 1088 |
| 실제 데몬 | 격리 HOME 데몬 + 대역 도우미: 허락 1클릭 → `feed.reply` → `{"ok":true,"result":{"actuated":"return"}}` · 도우미 좌석 **0x0d 1바이트** · 같은 판 재클릭 = feed.reply **0** |

## 1. 바뀐 파일(`git diff --numstat 3a012bf4 HEAD`)

| 파일 | 누구 | +/− | 변경 |
|---|---|---|---|
| `ui/src/views/judge/confirms.ts` | 새 | 256/0 | 순수 판정: 표식 판독 · 해결 대조 · feed 승인 본문 → 명령 원문 · 멈춤 판정 · 띠 · 허락 준비 · 처리 직전 재확인 · 오류 글 |
| `ui/src/views/confirm.ts` | 새 | 285/0 | ConfirmBook: 앞 기록 훑기 + 뒤 기록 표식 · feed/org 원문 받기 · 사건(deadman·stalled) · decide · 누른 기록 |
| `ui/src/views/chat/band.ts` | 새 | 207/0 | 띠 그리기 · 대화에서 답하기 · 펼침 · 신뢰 클릭 |
| `ui/src/views/core.ts` | 조각 1(우리) | 28/4 | 덧붙이기: ConfirmBook 필드 · `listen`·`goView` 의존 · fetchFresh 가 feed·org 원문을 같이 넘김 · 세션 시작/바뀜/잘림/새 레코드를 장부에 알림 · poll 마다 앞 훑기 1토막 · **마스터가 쉬게 된 틱이면 기다리는 말이 없어도 세션 1회 읽기**(스스로 낸 물음) |
| `ui/src/views/index.ts` | 조각 1 | 16/0 | `listen`(daemon-event · core 가 대화 화면 attach~detach 동안만 부름) · `goView` |
| `ui/src/views/chat/index.ts` | 조각 1 | 13/6 | 띠·답하는 물음 줄 끼우기 · 마스터 말풍선 `data-uuid` · 머리 확인 칸 = 띠 값 |
| `ui/src/views/views.css` | 조각 1 | 21/0 | 띠 스타일(글 18px 이상 · 누를 면 44px) |
| `ui/src/views/{judge/confirms,confirm}.test.ts` | 새 | 188 · 342 | bun 시험 |
| `ui/e2e/confirm_gate.py` | 새 | 222/0 | 실제 번들 + 대역 + **playwright 실제 마우스** e2e(A~G) |
| `docs/ui-p2/evidence/s4/` | 새 | — | 실제 데몬 증거 · 뮤턴트 도구 · 대역 도우미 · 데몬 구동 스크립트 |
| **팩(별도 커밋 4d20d25a)** `cysjavis-pack/directives/MASTER_DIRECTIVE.md` +9 · `CEO_TEMPLATE.md` +9(합성기 출력) · `RELEASED_MASTER_DIRECTIVE.sha256` 3/1 · `src/released_directive_hashes.rs` 6/2(생성기 출력) | | | §5 |

## 2. 원작자 파일 변경 줄

**0줄** — main.ts·index.html·build.sh·main.rs·handlers.rs·state.rs·governance.rs 무변경(`git diff --stat 3a012bf4 HEAD -- ui/src/main.ts ui/index.html ui/build.sh src-tauri src/bin` = 빈 출력). 사건 구독은 main.ts 배선 대신 `views/index.ts` 가 `__TAURI__.event.listen("daemon-event")` 를 대화 화면이 켜진 동안만 부른다(§6 판단 1).
팩 지침(원 출처 = 팩)은 별도 커밋 4d20d25a 한 개 — MASTER_DIRECTIVE **파일 끝에 덧붙임**(기존 줄 변경·이동 0).

## 3. 수용 기준 표(§11 조각 4 · 브리프 「시험」)

| # | 기준 | 판정 | 근거(시험 이름 · 출력) |
|---|---|---|---|
| FR-C1 | 결정·확인 필요 → 맨 위 「확인이 필요해요 N」 띠 한 줄 | **통과** | judge 「띠」 2건 · confirm_gate B 「물음 → 띠 1」·C · 「최소 계약 칸 = 띠와 같은 값」 |
| FR-C1a | 모르면 「확인할 것 살펴보는 중」(0 으로 칠하지 않음) | **통과** | judge 「모르면 … 0건 확정이면 숨김」 · 장부 「앞 기록 훑는 동안 모름」 · (codex 탐침) 꼴 깨진 승인 = 모름 |
| FR-C2 | 누르면 그 물음 자리 + 입력칸 준비 | **통과** | confirm_gate B 「그 물음 자리 표시 · 입력칸 포커스 · 입력칸 글 불변 · 답하는 물음 줄」 |
| FR-C3 | 해결 표식까지 안 사라짐 · 사람 말 원문 그대로 · 화면이 잇지 않음 | **통과** | 장부 「★물음이 열려 있어도 보낸 말은 원문 그대로」 · confirm_gate B 「★보낸 말 = 원문 그대로」·「사람 답만으로는 띠가 닫히지 않음」·「해결 표식 → 띠 숨김」 · judge 열린 물음 4건 |
| §5-4 | 줄머리 정확 일치 · 표식 없으면 띠 0 | **통과** | judge 「줄 중간·들여쓰기·끝 표시 없음·빈 물음 = 0」·「사람 글·곁가지·코드 울타리 = 0」 · 장부 「표식 없는 마스터 = 띠 0」 · confirm_gate A |
| FR-C5 | 마스터 멈춤 때만 직접 허락·거절 · 마스터 물음엔 직접 단추 0 | **통과** | judge 멈춤 판정 6건 · 장부 「평소 = 직접 단추 없음 · 억지로 불러도 호출 0」·deadman·stalled·5분·꺼짐 · confirm_gate C(단추 0)·D |
| FR-C5 5분 | 설계 목표값 · 상수 한 곳 · 측정 대기 표지 | **측정 대기** | `CONFIRM_STALL_MS = 300_000` · `CONFIRM_STALL_MEASURED = false`(judge 핀) · deadman 경로 U1 미실측 |
| FR-C5a | 펼친 뒤에만 허락 · 명령 원문 그대로 · 까닭 지어내지 않음 | **통과** | judge 「펼치기 전 허락 = 흐림 안내」 · confirm_gate D 「★펼치기 전 허락(진짜 클릭) → 호출 0 + 흐린 허락 안내」·「펼침 → 명령 원문 그대로」·「왜 = 자료 없음 정직 표시」 |
| FR-C5b | 번호+판 묶기 · 처리 직전 재확인 · 아니면 호출 0 + 안내 | **통과** | judge recheck 6갈래 · 장부 판 묶기 7건 · confirm_gate E 「★이미 처리된 요청 → 호출 0 + 안내」·F 「★판 바뀜(시각 주입) → 호출 0」 |
| FR-C6 | 도우미 허락 = 「마스터가 확인하는 중」 · 300초 방치 → FR-C5 | **통과** | confirm_gate C · 장부 「approval.stalled(그 요청) → 직접」 |
| NFR-S5 ①② | 신뢰 클릭에서만 · 화면이 스스로 누르는 길 0 | **통과** | confirm_gate D 「★대본 클릭(isTrusted=false) 2종 → 호출 0」(`element.click()` · `dispatchEvent`) · 진짜 클릭 = playwright 실제 마우스 |
| NFR-S5 ③ | 누른 사실 기록 | **통과** | 장부 「누른 기록(명령 원문 0자)」 · confirm_gate D 「누른 기록」 |
| 브리프 | 흐린 허락 안내 | **통과** | 위 FR-C5a |
| 브리프 | 이미 처리된 요청 = 호출 0 + 안내 | **통과** | 위 FR-C5b + **실제 데몬**(§5 · 재클릭 feed.reply 0) |
| 브리프 | 기존 bun·tsc·화면 게이트 · chat_gate·tickrec_gate PASS 유지 · 작업 화면 동작 변화 0 | **통과** | §5 |
| 브리프 | 뮤턴트(멈춤 판정·펼침 조건·판 묶기 하나씩 빼면 붉음) | **통과** | §4 |
| 브리프(전문가) | 「펼친 뒤 판이 바뀜(같은 번호 · 다른 command)」 시각 주입 고정 시험 | **통과** | confirm_gate F(그리기와 클릭 사이에 데몬 쪽 판 바꿈 → 호출 0 · 다음 그리기 = 접힌 채 새 명령) · 장부 「★펼친 뒤 판이 바뀜」 |
| 실물 | 진짜 마스터 답에 표식이 찍히는지 | **측정 대기** | 0.5 M4~M8(진짜 Claude 로그인) 이월 · 팩 지침(4d20d25a)이 들어가야 마스터가 표식을 냄 |

## 4. 뮤턴트(`docs/ui-p2/evidence/s4/tools/mutants.py` · 바꿈 → bun `src/views` → (표시된 것) build + confirm_gate → git 원복 · 원복 확인)

최종 = aa6a80d7 소스 · **21 / 21 붉음 · 원복 확인 True 전부**(전체 실행 19 + 앵커를 aa6a80d7 뒤 글로 맞춘 2종 `MUT_ONLY` 재실행 · 4694bcba).

| 뮤턴트 | bun `src/views` 붉음 | confirm_gate 붉음 |
|---|---|---|
| 멈춤: 마스터 좌석 없음 무시 | 2 | — |
| 멈춤: 꺼짐 무시 | 3 | — |
| 멈춤: deadman 무시 | 5 | 2 |
| 멈춤: deadman 풀림 판정 없음(한 번이면 영원히) | 2 | — |
| 멈춤: approval.stalled 무시 | 3 | — |
| 멈춤: 5분 규칙에서 마스터 소식 조건 뺌 | 1 | — |
| 멈춤: 늘 멈춤(평소에도 직접 단추) | 11 | 2 |
| 펼침: 허락 펼침 조건 뺌(판정) | 1 | 2 |
| 펼침: 멈춤 아닌 항목도 준비됨 | 1 | — |
| 펼침: 그리기가 펼침 여부 대신 늘 펼침으로 넘김 | 0 | **2**(e2e 만 잡음 — 그리기 층) |
| 펼침: 판 열쇠에서 본문·시각 뺌(같은 번호면 펼침 이어짐) | 1 | 2 |
| 판 묶기: 본문 대조 뺌 | 2 | 3 |
| 판 묶기: 시각 대조 뺌 | 2 | — |
| 판 묶기: 이미 처리됨(목록 없음) 통과 | 2 | 2 |
| 판 묶기: 재확인 때 멈춤 다시 보기 뺌 | 4 | — |
| 판 묶기: 처리 직전 재조회 대신 그리기 때 값 | 8 | 4 |
| 판 묶기: 연타 막기 뺌 | 1 | — |
| 신뢰 클릭: isTrusted 검사 뺌 | 0 | **2**(e2e 만 잡음 — DOM 이벤트) |
| 표식: 줄머리 대신 줄 어디든 | 1 | — |
| 표식: 사람(user) 글도 표식 | 2 | — |
| 표식: 앞 훑기 뒤 기록에서 멈춤 뺌 | 1 | — |

- 「—」 = e2e 를 돌리지 않은 뮤턴트(bun 이 이미 붉음). 첫 실행(3caee818 전)의 「판이 바뀌어도 펼침 유지(정리 줄 뺌)」는 **등가 뮤턴트**였다(펼침 열쇠가 본문을 담아 정리 없이도 새 판은 접힘 · bun 0 · e2e 0) → 보호 지점인 「판 열쇠에서 본문·시각 뺌」으로 바꿈(붉음).

## 5. 게이트 결과(기준선 = 3a012bf4 · 같은 기기 · 최종 소스 aa6a80d7 번들)

| 대상 | 이 조각 | 기준선 3a012bf4 | 판정 |
|---|---|---|---|
| bun test(ui 전체) | **3601 pass · 88 skip · 0 fail**(3689 · 119 파일) | 3554 · 88 · 0 | +47 = judge/confirms 24 + 장부 23 |
| `bun test src/views` | **150 / 0** | 103 / 0 | — |
| tsc `bun x --package typescript@7.0.2 tsc -p tsconfig.check.json` | **rc 0** | rc 0 | 같음 |
| `confirm_gate.py`(새) | **PASS · ok 27 / FAIL 0** | — | 새 게이트 |
| `chat_gate.py`(조각 1) | **PASS · ok 40 / FAIL 0** | PASS 40 / 0 | 같음 |
| `tickrec_gate.py` OFF | 새 = 기준 · invoke **1088** = 1088 · 저장 키 3 · sha **308dd2b91f9a** = 308dd2b91f9a | 308dd2b91f9a | **작업 화면 동작 변화 0** |
| 뮤턴트 | **21 / 21 붉음** | — | §4 |
| 팩 `scripts/gen_ceo_template.py --check` | **exit 0**(GREEN · 101878 B) | — | 팩 커밋 4d20d25a |
| 팩 `scripts/gen_released_directive_hashes.py --check` | **exit 0** | — | 〃 |
| 팩 `test_bootv2_doc_contract.py` | **exit 0**(ALL PASS · BOOTV2-DOC-CONTRACT-OK) | — | 〃 |
| 팩 `test_event_inject.py` | **exit 0**(PASS 106 · FAIL 0) — 절을 파일 **끝**에 넣어 줄 범위 상수 무변경 | — | 〃 |
| cargo `-p cys-terminal --lib released` | **3 / 0**(released_tables_cover_current_embed · released_master_hash_pack_file_matches_table · +1) | — | 〃 |
| 공개 secret-scan `scripts/secret-scan.sh --all` | **clean**(2112 파일) | clean | 같음 |
| 실제 데몬 1회(이 기기 · 격리 HOME/소켓/팩 · 본 데몬·마스터 무접촉 · 끝나고 좌석 닫고 데몬 멈춤) | 허락 1클릭 → `feed.reply` 1요청 → `{"ok":true,"result":{"actuated":"return","decision":"allow",…}}`(122 B) · 대역 도우미 좌석 **0x0d 1바이트** · 같은 판 재클릭 = 처리 직전 재조회 `gone` → **feed.reply 0** + 「이미 처리됐거나 바뀐 요청이에요」 · 1회차(대역 커서가 선택 줄 밖) = 데몬 `approval_screen_gone`(키 0) → 화면 「도우미 창의 확인이 이미 사라졌어요」 | — | 증거 `docs/ui-p2/evidence/s4/real-daemon.txt` |
| cargo 앱(`-p cys-app`) | **안 돌림** — Tauri·Rust 변경 0(viewcore.rs·main.rs 무변경) | — | 해당 없음 |

## 5-b. codex 적대 검토

| 회 | 판정 | 내용 |
|---|---|---|
| 1R(00:0x · e6f03924~3caee818) | **판정문 없음 — 사용 한도 소진**(로그 끝 「You've hit your usage limit … try again at 2:50 AM」) | 멈추기 전 로그에 남은 **탐침 4건**(codex 가 node 로 직접 돌려 보던 실패 경우)만 읽어 타당 판단 → 전부 고침(aa6a80d7): ① uuid 없는 레코드를 앞 훑기·뒤 읽기가 두 번 셈 → 역할·시각·글 신원 ② 앞 20자만 같고 뒷말이 다른 해결이 닫음 → 실린 글 전부 대조 ③ 꼴 깨진 대기 승인 = 0건 확정 → 모름 ④ 처리 직전 그 요청이 지금 마스터 좌석 것이어도 approval.stalled 로 통과 → 호출 0 · 시험 +4 |
| 1R 재시도(02:51 · master#121b7ff6) | (결과로 채움) | — |

## 6. 내가 내린 판단(지시에 없던 것 · master 확인 후보)

1. **사건 구독 = views/index.ts 에서 직접**(main.ts onDaemonEvent 머리 1줄 배선 대신) — 원작자 파일 0줄 · 대화 화면이 켜진 동안만 구독(작업 화면만 쓰면 구독 0). 대가: 대화 화면을 끈 동안 온 deadman·stalled 는 모름 → 켠 뒤엔 org.status(꺼짐·좌석 없음)와 5분 규칙만으로 판정(직접 단추가 덜 열리는 쪽).
2. **feed 는 조각 1 이 이미 받는 `feed_list(pending)` 원문을 그대로 씀**(새 주기 조회 0) — 데몬 승인 본문(`… — 명령 원문: … — 읽기 전용 판정 …`)에서 명령 원문을 뽑는다(꼴이 다르면 전부 excerpt 로 · 실제 데몬 본문과 같은 꼴 확인 §5).
3. **띠에 올리는 feed = kind `approval`(도구 허락 창)만** — `cys feed push --wait` 류(permission·question)는 마스터 몫이라 넣지 않음 📌.
4. **멈춤 갈래에 「마스터 꺼짐 확정(agent_alive false)·마스터 좌석 없음」 추가** — deadman 은 데몬 `roles["master"]` 가 있어야 나오는데(§5-5 ③), 같은 사실을 org.status 로 직접 보면 같은 판정. 모름(null)은 멈춤 아님.
5. **5분 규칙 = 「생긴 지 5분 ∧ 마스터 출력 뒤 5분」**(「생긴 뒤 소식 5분 없음」의 넓은 읽기 — 생긴 뒤 1분에 한 줄 내고 10분 조용한 마스터도 멈춤으로 봄).
6. **거절은 펼침 없이 됨**(Esc = 하지 않음 · 되돌릴 수 없는 쪽이 아님) · 허락만 펼침 필수(읽기 전용 추정이어도 — 브리프 「펼침 필수」).
7. **처리 직전 재확인에 「지금 마스터 좌석 것이면 아님」**(codex 탐침 ④) · **연타 = 처리 중 두 번째 누름 무시**.
8. **「대화에서 답하기」 = 입력칸 글 불변** — 「입력칸 준비」를 포커스 + 「답하는 물음」 줄 + 자리표시 글로 함(FR-C2 와 브리프 「붙이기 0」을 함께 지키는 꼴). 그 물음 말풍선이 화면에 없으면(대화 화면을 열기 전 물음) 맨 아래로.
9. **해결 하나 = 가장 오래된 하나만 닫음 · 같은 글 물음 다시 묻기 = 1건** · 해결은 「실린 글 전부가 물음 앞부분과 같고 길이 ≥ 앞 20자(짧은 물음은 전체)」.
10. **「마지막 답」 = 마스터 답 글(assistant 레코드) 전부**로 읽음 — 도구 사이 중간 글의 표식도 받음(사람에게 보이는 글이라서) · 코드 울타리(```) 안은 받지 않음(지침 인용·예시 오판 방지).
11. **마스터가 쉬게 된 틱 = 세션 1회 읽기**(조각 1 은 기다리는 말이 있을 때만) — 마스터가 스스로 낸 물음을 받으려고. 새 주기 조회 0(활동이 바뀐 틱만).

## 7. 알려진 남은 위험 · 한계(정직)

- **도우미 창 A→B 바뀜(같은 요청 번호)**: 데몬 승인 감지는 대기 항목이 있으면 본문을 다시 쓰지 않는다(§2-7 F16) → feed 본문이 A 인 채 창이 B 로 바뀌면 화면 판 대조도 같다고 본다. 남는 방어 = 데몬의 「선택 줄이 1. Yes 일 때만 키」 · 데몬 변경 후보 ⑤(집행 때 현재 명령 해시 대조) 이월.
- **명령 원문은 화면 긁기**(12행·600자) — 그 너머는 「작업 화면에서 보기」.
- **5분·멈춤 경로 실측 없음**(U1) · deadman 은 `roles["master"]` 가 있는 기기에서만.
- **실제 데몬 증거는 대역 도우미 화면**(Claude 허락 창 모양을 그린 파이썬) — 진짜 Claude 창에서의 1회는 0.5 재개(로그인) 때. 1회차는 대역 커서가 선택 줄 밖이라 데몬이 `approval_screen_gone`(키 0) — 원문 그대로 증거에 남김.
- **앞 기록 훑기 비용**: 긴 세션(수십 MB)이면 3초에 2 MiB 씩 → 그동안 「살펴보는 중」(예: 50 MB ≈ 75초) 〔추정 · 실측 없음〕.
- **표식 준수율**(U15′): 팩 지침(4d20d25a)이 들어가도 마스터가 지킬지는 실물 대화 계수 몫.
- **누른 기록은 앱 저장소**(`cys-chat-decisions` 최근 50) — 데몬 쪽 감사 기록(resolve_feed_item_audited)이 정본.

## 8. 재현 명령

```sh
W=~/axdev/.wt/cys-ui-slice4; cd $W/ui
bun install --frozen-lockfile && sh build.sh && bun test                      # §5
bun x --package typescript@7.0.2 tsc -p tsconfig.check.json                    # rc 0
cd $W && CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/confirm_gate.py
CHROME_PATH=<…> cys run -- <…> ui/e2e/chat_gate.py
CHROME_PATH=<…> BASE_DIST=<3a012bf4 번들 dist> cys run -- <…> ui/e2e/tickrec_gate.py
PY=<playwright python3> CHROME_PATH=<…> python3 docs/ui-p2/evidence/s4/tools/mutants.py   # 작업트리 커밋 상태에서
# 팩: python3 scripts/gen_ceo_template.py --check · python3 scripts/gen_released_directive_hashes.py --check
#     python3 cysjavis-pack/bin/tests/test_bootv2_doc_contract.py · python3 cysjavis-pack/bin/tests/test_event_inject.py
#     cargo test -p cys-terminal --lib released
# 실제 데몬: 격리 HOME 에서 cysd(CYS_SOCKET·CYS_PACK_DIR 격리) → cys new-surface --agent claude --cmd "python3 fake_approval_agent.py <기록>"
#     → 승인 항목 생기면 CYS_SOCKET=<격리 소켓> bun run docs/ui-p2/evidence/s4/tools/real_daemon_drive.ts
```

## 9. 함정

- **untracked 파일 뮤턴트는 `git checkout --` 로 원복되지 않는다** — 첫 수동 뮤턴트에서 confirm.ts 가 그대로 남아 백업으로 되돌림(확인함). 뮤턴트 전 반드시 커밋(기억 [[mutant-restore-via-git-not-shell-var]] 과 같은 계열).
- 순수 판정 파일 정적 핀(`registry.test` — judge/*.ts 에 `window` 글자 금지)이 **식별자 `master_window`** 에 걸림 → `master_screen` 으로.
- playwright 는 `aria-disabled="true"` 단추를 「안 켜짐」으로 보고 클릭을 기다리다 30초 넘김 → 흐린 허락 클릭은 `force=True`(실제 마우스 이벤트 그대로 · 대기 검사만 건너뜀).
- 데몬 허락 집행은 **가로줄 없는 화면이면 커서 행이 「❯ 1. Yes」일 때만** 창으로 봄(approval_in_prompt_tail) — 대역 화면이 커서를 다른 데 두면 `approval_screen_gone` + 항목 stale-cleared.
- 이 좌석 PATH 에 `cargo`·`timeout` 없음 → `~/.cargo/bin/cargo` · `perl -e 'alarm …; exec …'`.
- `codex exec` 사용 한도(00:1x 소진 · 02:50 해제).
- 팩 해시표 생성기는 **이 기기 git 태그** 기준 — 이번 판 해시 말고 태그 유래 항목 증감도 함께 나옴(4d20d25a 에 그대로 · 통합 때 재생성 권장).

## 10. 커밋 목록(3a012bf4 위)

| 커밋 | 내용 |
|---|---|
| e6f03924 | 조각 4 본체(judge/confirms · confirm · chat/band · 덧붙이기 · 시험 judge 23 + 장부 20) |
| 697fb534 | confirm_gate e2e + 쉬게 된 틱 세션 읽기 시험 |
| 3caee818 | 뮤턴트 도구 · 실제 데몬 증거 |
| aa6a80d7 | codex 1R 탐침 4건 반영(시험 +4) |
| **4d20d25a** | **팩 지침 별도 커밋** — MASTER_DIRECTIVE 끝 「대화 화면 표식」 절(표식 4줄) + CEO_TEMPLATE 재합성 + 발행 해시표 재생성 |
| 4694bcba | 뮤턴트 앵커 2종을 aa6a80d7 뒤 글로 · `MUT_ONLY` |
| (이 HANDOFF) | HANDOFF · TODO |

## 11. 📌 덧붙임(브리프에 없던 것 — master 판단 후보 · 실행 안 함)

1. 📌 **FR-C4(OS 알림·앱 배지)** — 조각 4 범위 밖이라 안 함.
2. 📌 **`cys feed push --wait`(permission·question) 항목을 띠에 올릴지** — 지금은 도구 허락 창(approval)만.
3. 📌 **사건 구독을 main.ts 배선 1줄로 옮길지**(대화 화면을 끈 동안 온 deadman 도 알게) — 원작자 파일 1줄 대가.
4. 📌 **데몬 변경 후보 ⑤(집행 때 현재 명령 해시 대조)** — §7 첫 줄의 남은 창을 닫는 유일한 길.
5. 📌 **도우미 지침(팩)에 「되돌릴 수 없는 명령 전에 까닭 한 줄」** — 「왜」 자료의 원천(§2-7 · 사람 승인 대상).
6. 📌 **팩 지침 D7 문장(「갈래 셋 이상이면 시작 전에 ⟪팀 제안⟫」)** — 조각 6 몫이라 표식 4줄만 넣음.
