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
| 1R 재시도(02:51 · master#121b7ff6) | **미실행 · 사유 한도 · 02:51 재시도 예약**(master#b8ec5732: 【확인요청】 먼저 · 결과는 【codex 추가】 로 따로) | 예약 = 02:51 에 `codex exec --sandbox read-only` 1회(`</dev/null` · 480초 상한) · 범위 = 위 1R 과 같은 파일 · REVISE 면 고칠 목록만 보내고 고치기는 독립 검증 지적과 묶어 1회 |

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

## 12. 델타 — 독립 검증(2160 · VERIFY.cysr-ui-slice4.md) 1회 고침 (master#21ce865b · 2026-11-18 00:56~)

| 지적 | 심각도 | 처분 | 무엇을 · 시험 |
|---|---|---|---|
| F0 좌석이 올린 approval 을 도구 허락 창처럼 | 높음 | **고침**(7afab438) | `FeedApproval.screen` = `daemon_issued === true`(칸이 없으면 번호 접두 `daemon-`) · `itemStall` 첫 줄 `!screen → null` = 띠 「마스터가 확인하는 중」 · 직접 단추 0 · 처리 직전 재확인도 같은 길(호출 0) · judge 「F0」 · e2e F0 장면 · 뮤턴트 2 |
| F1 실제 앱 사건 전부 버림(본부에도 slug) | 높음 | **고침** | 대화 화면 켤 때 `default_socket_slug` 1회 → 사건 slug 가 그것과 같으면 받음 · 다르거나 아직 모르면 버림(단추가 덜 열리는 쪽) · e2e 대역 사건 = 앱 꼴(slug `base` = 대역 default_socket_slug) + 부서 slug 사건 버림 장면(D0) · 장부 「F1」 · 뮤턴트 2 |
| F2 모름을 멈춤으로(deadman 안 지워짐) | 중간 | **고침** | 걸쇠 = 풀림(생존 확정 ∧ (새 좌석 ∨ 사건 뒤 출력))을 한 번 보면 deadman 지움 · `masterSid undefined` = deadman 근거 안 씀 · 나이 상한 `DEADMAN_MAX_AGE_MS = 300_000`(데몬 재알림 300초) · **V3**(풀림에서 생존 확정 조건 뺌) 붉게 하는 시험 = judge 「생존 모름(null) 출력만으로는 안 풀림」 · 장부 「F2 ⓐ·ⓑ」 · 뮤턴트 4 |
| F3 2 MiB 넘는 한 줄 | 중간 | **고침**(Tauri `viewcore.rs` + 화면) | `read_transcript_from`: 한도를 채운 줄 끝 없는 토막 = 다음 줄 끝까지 건너뜀(내용 안 읽음) + `skipped_bytes` · 줄 끝이 아직 없으면 그대로 + `long_line_open` → 뒤 읽기도 더는 안 멈춤 · 화면: 못 나아가면 「다 훑음」 확정 안 함(모름 유지 · 다음 틱 다시) · 건너뛰었으면 물음은 보이되 「더 살펴보는 중」 · cargo `over_long_line_is_skipped_to_next_line_end_and_reported` · 장부 「F3」 · **W26** 뮤턴트 붉게 |
| F4 20번째 글자 공백 | 중간 | **고침** | 해결 대조 = 공백 정규화(연속 공백 한 칸 · 앞뒤 깎음) 뒤 앞부분 일치 · 길이 기준 = 정규화한 물음 앞 20자 · judge 「F4」(20번째 글자가 띄어쓰기인 견본 · 공백 두 칸 해결도 닫힘 · 짧은 해결은 안 닫힘) · 뮤턴트 1 |
| F5 좌석 없음·꺼짐 유예 0 | 낮음~중간 | **고침** | `ABSENT_GRACE_MS = 30_000`(설계 목표값) — 그 상태가 끊김 없이 30초 이어져야 멈춤 · judge·장부 「F5」 · 뮤턴트 1 |
| F6 처리 직전 org 낡음 검사 없음 | 낮음 | **고침** | org 왕복 > 500ms(`ORG_MAX_MS` = core OBS_MAX_MS 와 같은 값) 또는 실패 = 호출 0 + 「마스터 상태를 확인하지 못해…」 · 장부 「F6」 · 뮤턴트 1 |
| F7 닫히지 않는 물음 치울 길 없음 | 낮음 | **📌 만(지시)** | 고치지 않음 |
| F8 ~~~ · 들여쓴 ``` · 긴 울타리 | 낮음 | **고침** | 울타리 = 줄 앞 공백 뒤 ``` 또는 ~~~ 3개 이상 · 닫는 줄 = 같은 글자·같거나 더 긴 줄(CommonMark) · judge 「F8」 · 뮤턴트 1 |
| F9 uuid·시각 없는 레코드 다시 물음 버림 | 낮음 | **고침** | 뒤 읽기 안에서는 같은 신원도 다 셈 · 앞 훑기가 「끝을 넘는 토막」에서 가져간 것만 개수만큼 한 번씩 건너뜀 · 끝 전 토막은 겹침 검사 안 함 · 장부 「F9」 |
| F10 띠 한 번에 하나 → 다른 항목에 거절 | 낮음 | **📌 만(지시)** | 고치지 않음 |
| V14 · V17 · V18 시험 구멍 | — | **시험 추가** | judge 번호·시각 칸 깨짐 = 모름 · 장부 「V17」(역할만 신원이면 앞 기록 물음 잃음) · 「V18」(겹침 거르기 빼면 해결 하나가 물음 둘을 닫음) · 뮤턴트 4 |
| §C 도우미 좌석 idle_secs 로 A→B 좁히기 | — | **넣지 않음 · 실측 못 함** | 지시 = 「허락 창이 떠 있는 동안 좌석이 주기 출력을 내는지 격리 실측 1회 뒤」 — 이 기기 본 데몬에 지금 대기 승인 창 0(01:02 `cys feed list --status pending` = 사이클 경보 3건뿐) · 격리 데몬에는 로그인된 Claude 가 없어 진짜 허락 창이 안 뜸(대역 화면은 Claude 의 다시 그리기를 흉내 내지 못해 실측 근거가 안 됨) → **숫자 없음 · 코드 안 넣음** · 0.5 재개(로그인) 때 같이 재면 됨 📌 |
| D 팩 지침 문장 | — | **고침(별도 커밋 e1cd0f76)** | 「표식 줄은 반드시 `⟫` 로 끝나야 한다」 · 「사람의 결정이 필요 없는 답에는 표식을 쓰지 않는다」 2문장(파일 끝 +2) · 「앞 20자」 문면은 그대로(코드가 공백 정규화로 맞춤) |
| D 해시표 직전 판 1쌍(793e143f·1a9ebfb5) | — | **📌 만(지시)** | 통합 때 master 판단 |

### 12-1. 시험 수(1회 고침 전 e2914ee1 → 뒤)

| 대상 | 전(e2914ee1) | 뒤(dd654ea2) |
|---|---|---|
| bun ui 전체 | 3601 · 88 skip · 0 | **3613 · 88 skip · 0**(3701 · 2회 연속) — ⚠ 게이트·뮤턴트와 겹친 1회는 1 fail(부하 흔들림 · 조각 1 §9 와 같은 현상 · 혼자 다시 0) |
| `bun test src/views` | 150 / 0 | **162 / 0** |
| tsc | rc 0 | **rc 0** |
| cargo `-p cys-app --bin cys-app viewcore` | 7 / 0 | **8 / 0**(+ 긴 줄 건너뛰기) |
| cargo `-p cys-terminal --lib released` | 3 / 0 | **3 / 0** |
| `confirm_gate.py` | 27 / 0 | **29 / 0**(+ D0 부서 slug 버림 · F0 좌석이 올린 approval 단추 0 · 사건 = 앱 꼴 slug) |
| `chat_gate.py` | 40 / 0 | **40 / 0** |
| `tickrec_gate.py` OFF | 새 = 기준 308dd2b91f9a | **같음** · invoke 1088 = 1088 · 작업 화면 동작 변화 0 |
| 뮤턴트 | 21 / 21 | **39 / 39 붉음**(첫 실행 38/39 — 「deadman 걸쇠 뺌」 생존 → dd654ea2 시험 강화로 붉음 2) · **V3 = 붉음 1** · W26 = 붉음 1 · 원복 전부 True |
| 팩 4본 | exit 0 ×4 | **exit 0 ×4**(event_inject PASS 106 · FAIL 0) |
| codex 1R | 미실행(한도) | 02:51 이 머리 대상 1회 재시도 예약 → 【codex 추가】 |

### 12-2. 커밋(e2914ee1 위)

| 커밋 | 내용 |
|---|---|
| 7afab438 | 검증 1회 고침 F0·F1·F2·F3·F4·F5·F6·F8·F9 + 시험 구멍 + viewcore.rs 긴 줄 + e2e D0·F0 + 뮤턴트 39 |
| **e1cd0f76** | **팩 지침 별도 커밋** — 2문장(줄이 ⟫ 로 끝나야 · 결정 필요 없는 답엔 안 씀) + 재합성 + 해시표 |
| dd654ea2 | 걸쇠 시험 강화 |

### 12-3. 원작자 파일 변경 줄(검증 고침 뒤)

여전히 **0줄** — 이번에 바뀐 Rust 는 `src-tauri/src/viewcore.rs`(조각 1 새 파일 · 우리) 하나. 데몬 변경 0.

## 13. 델타 — codex 1R(BLOCK) 고침 · TICKET=cysr-ui-slice4-fix2-1118 (워커 surface:2166 · 2026-11-18 03:0x~ · 앞 좌석 2158 이어받음)

- 브리프 = `master/briefs/2026-11-18-cysr-ui-slice4-fix2.md`(원장 kind=brief · spawn 경로 · surface:2166 · body_sha256 98229725 = 파일 끝 줄바꿈 뺀 sha 일치 — 대조함)
- 1R 원문 = `docs/ui-p2/evidence/s4/codex-r1.json`(e62e1fb0 대상 · BLOCK · blocking 1 · major 6 · minor 1)
- 비가역 0: push·서명·발행·앱 교체 안 함 · **데몬(src/bin) 변경 0** · 원작자 `main.rs` = `generate_handler!` 이름 **1줄**(`viewcore::confirm_reply` — 조각 1 이 넣은 두 줄과 같은 꼴 · 원작자 `feed_reply` 본문 무변경)

### 13-1. codex 지적별 처분

| # | 지적 | 처분 | 무엇을(파일) | 재현 시험(붉음 → 초록) |
|---|---|---|---|---|
| blocking | 승인 창 A→B 가 판 재검증을 통과 | **master 결정대로 고침**(b00800df) | 직접 「허락」 = 데몬 지문 표지(feed 항목 `screen_fingerprint` · 비어 있지 않은 글)가 있는 판만(`canAllowDirect`) · 지금 데몬엔 그 칸이 없음 = 늘 닫힘 → 멈춤 때 직접 단추 = **「거절」 + 「작업 화면에서 그 창 보기」 + 안내 「마스터가 멈췄어요. 허락은 작업 화면의 그 도우미 창에서 직접 눌러 주세요.」**(band.ts · 「무엇을 보기」도 안 냄) · 세 겹: 그리기(단추 없음) · `allowReady`(허락 거부) · `decide`(지문 null 이면 feed·org 재조회도 안 하고 호출 0) · 지문은 판 열쇠·`Bound`·`recheck`(지문 다르면 changed)에 들어가고 `confirm_reply` 가 `screen_fingerprint` 로 실어 보냄(자리만 · 시험은 대역) · 데몬 거부 코드 `approval_fingerprint_mismatch` 안내 글 준비 | judge 「지문 표지 = screen_fingerprint 만」·「지문 표지 없는 판 = 펼쳐도 허락 0」·recheck 지문 2건 · 장부 「blocking — 지금 데몬 … 허락 = 호출 0(재조회도 0) · 거절 = 1회(지문 null)」·「펼친 뒤 지문이 바뀜 = 호출 0」 · e2e **D1** · 뮤턴트 4(§13-3) |
| major 1 | 생존 null 마스터의 새 출력이 deadman 을 못 풂 | **고침** | `deadmanRevived` = 꺼짐 확정(false)이 아닌 마스터 ∧ (새 좌석 ∨ 사건 뒤 출력) — 생존 null 이어도 풀림 · 장부 걸쇠가 지움 · `masterSilenced` = 좌석이 있고 생존 null 이면 deadman 근거 안 씀 | judge deadman 판정(풀림 4 · 근거 아님 2) · 장부 「codex 1R major 1 재현 — 생존 null · idle 0 = 풀림 · 뒤에 생존 확정이 와도 되살아나지 않음 · 호출 0」·「F2 ⓑ · 생존 모름 관측만 = 단추 0 · 호출 0」 · 뮤턴트 2 |
| major 2 | 좌석이 바뀌어도 펼침 승계 | **고침** | `versionKey` = `JSON.stringify([번호, 시각, 본문, 좌석, 지문])`(Bound 칸 전부) — band.ts 정리 줄이 새 열쇠의 펼침을 지움 | judge 「판 열쇠 = Bound 칸 전부 — 어느 하나만 바뀌어도 다른 열쇠」(Bound 칸 목록 고정 + 칸마다 바꿔 봄) · e2e **F2**(펼친 뒤 좌석만 바뀜 → 접힘 · 흐린 허락 진짜 클릭 = 호출 0) · 뮤턴트 2 |
| major 3 | slug 없는 사건 수용 | **고침** | `onEvent` = 본부 slug 확정 ∧ `typeof socket_slug === "string"` ∧ 비지 않음 ∧ 같음 일 때만 | 장부 「major 3 — slug 없음·null·빈 글 사건 = 버림(approval.stalled · deadman) · 호출 0」 · 뮤턴트 1 |
| major 4 | 꼴 깨진 org 응답이 재확인 통과 | **고침** | `decide` = `masterOf(org) === undefined` 이면 처리 중단(`org_unknown`) · `itemStall` 첫머리 = 마스터 좌석 모름이면 null(직접 단추 0 · stalled·5분 규칙도 안 씀) | judge 「마스터 좌석 모르는 동안 stalled·5분 있어도 직접 단추 0」 · 장부 「major 4 — {surfaces:null} = 호출 0 · 그 뒤 띠 항목 단추 0」 · 뮤턴트 2 |
| major 5 | 기록만 해소된 거절을 성공으로 표시 | **고침**(Tauri + 화면) | 새 Tauri 명령 **`viewcore::confirm_reply`**(우리 파일) = 원작자 `feed_reply` 와 같은 operator token 첨부·1회 재시도이되 **데몬 `result` 를 그대로 돌려줌** · 화면 `actuatedOf` = `actuated` 가 비지 않은 글일 때만 「허락했어요/거절했어요」 · null·없음 = **「기록만 됐고 도우미 창은 눌리지 않았어요 — 작업 화면에서 확인해 주세요.」** · 기록 outcome `recorded_only` · 대화 화면의 원작자 `feed_reply` 호출 = 0(e2e 핀) | cargo `confirm_reply_params_and_outcome_keep_actuated` · judge actuatedOf 5 · 장부 「major 5 — allow·deny · actuated 칸 없음」 · e2e **G2** · 뮤턴트 1 |
| major 6 | 공백 정규화가 정확 일치를 깸 | **고침**(코드 b00800df + **팩 별도 커밋 12e8bc95**) | `resolves` = 원문 코드 포인트 그대로(정규화 0 · 앞 고침 F4 되돌림) · `markersOf` 가 해결 글을 깎지 않음(20번째 공백 보존) · 팩 문장 `⟪확인 해결: <같은 물음 앞부분을 글자 그대로(띄어쓰기 포함) 20자>⟫` | judge 「codex 1R major 6」(① 「…t  X」를 「…t X」가 못 닫음 ② 두 칸 물음의 정확한 앞 20자는 닫음 ③ 한 칸으로 줄인 해결 안 닫힘) · 「F4 · 20번째 공백 보존」 · 뮤턴트 2 |
| minor | uuid 없는 반복 레코드가 앞 기록 해결을 놓침 | **고침**(Tauri + 화면) | viewcore 레코드에 **`at` = 줄 시작 파일 바이트**(깨진 줄을 건너뛰어도 위치 계산은 이어짐) · 앞 훑기의 끝을 넘는 토막 = `at < 시작 오프셋` 만 앞 기록 · 하나라도 `at` 이 없으면 「다 훑음」 확정 안 함 · 글 신원 장부(`priorTaken`·`tailSeen`·`recId`) 삭제 — 뒤 읽기는 전부 셈 | cargo `records_carry_file_line_start_position` · 장부 「minor — X → Q(무신원) → 해결 X · 뒤에 같은 Q 먼저 = Q 하나만」·「위치 모르는 레코드 = 모름 유지」 · V17·V18 = 위치로 다시 씀 · 뮤턴트 2 |

### 13-2. 내가 내린 판단(지시에 없던 것 · master 확인 후보)

1. **지문 표지 = feed 항목 칸 `screen_fingerprint` 하나**(기능 목록 칸 대신) — 표지와 보낼 값이 같은 칸이라 「표지는 있는데 값이 없음」 꼴이 생기지 않는다. 비어 있지 않은 글만 표지로 본다(빈 글·숫자 = 없음).
2. **지문 없는 판 = 「무엇을 보기」도 안 냄** — 브리프 「직접 단추 = 거절 + 작업 화면에서 그 창 보기만」을 글자대로. 펼친 명령이 지금 창(B)과 다를 수 있어 거절 판단에도 오도할 수 있음.
3. **actuated 를 받으려고 원작자 `feed_reply` 를 바꾸지 않고 우리 명령 `confirm_reply` 를 새로 둠** — `main.rs` 는 이름 1줄(조각 1 선례). `feed_reply` 는 작업 화면이 쓰므로 반환형을 바꾸면 작업 화면 동작이 바뀐다. 대가: 같은 재시도 규칙이 두 군데(viewcore.rs 주석에 출처).
4. **`decide` 의 지문 가드는 재조회 전에** — 지문 없는 허락은 feed·org 도 다시 받지 않는다(호출 0 · 조회 0). 그리기 뒤 판이 지문 없는 판으로 바뀐 경우는 recheck 의 지문 대조(changed)가 막는다 — 따로 두 번째 가드를 두면 등가 뮤턴트가 되어 뺐다.
5. **`at` 은 Tauri 쪽에서 실음**(데몬 아님 · viewcore.rs 우리 파일) — 위치를 화면이 추측하지 않는다.
6. **생존 false + deadman 은 여전히 근거**(꺼짐 확정 = 죽음이 맞음) — 「생존 모름 관측만으로는 근거 안 씀」을 null 에 한정.

### 13-3. 시험 수(고침 전 26d4f29c → 뒤)

| 대상 | 전(26d4f29c) | 뒤(31800d54) |
|---|---|---|
| bun ui 전체 | 3613 · 88 skip · 0 | **3628 · 88 skip · 0**(3716 · 119 파일) |
| `bun test src/views` | 162 / 0 | **177 / 0** |
| tsc(typescript@7.0.2 · tsconfig.check) | rc 0 | **rc 0** |
| cargo `-p cys-app --bin cys-app` 전체 | (345 = 뒤 348 − 이번에 더한 3 · 따로 재지 않음) | **348 / 0 · 2 ignored** |
| cargo `… viewcore` | 8 / 0 | **11 / 0**(+ 레코드 위치 · confirm_reply 매개변수·결과 · from_end 시작점) |
| cargo `-p cys-terminal --lib released` | 3 / 0 | **3 / 0**(팩 커밋 12e8bc95 뒤) |
| `confirm_gate.py` | 29 / 0 | **37 / 0 · PASS**(+ D1 지문 없음 · F2 좌석만 바뀜 2 · G 거절 안내 · G2 기록만 · 원작자 feed_reply 0) |
| `chat_gate.py` | 40 / 0 | **40 / 0 · PASS** |
| `tickrec_gate.py` OFF(기준 = 3a012bf4 번들) | 308dd2b91f9a | **308dd2b91f9a = 308dd2b91f9a** · invoke 1088 = 1088 · 어긋난 호출 0(한가할 때 · 뮤턴트와 겹친 1회는 「가짜 시각 어긋남 14건 · 최대 1ms」 정보 줄만 · 판정 PASS) |
| 팩 4본 | exit 0 ×4 | **exit 0 ×4**(ceo --check · hashes --check · bootv2_doc_contract OK · event_inject PASS 106 / FAIL 0) |
| secret-scan `--all` | clean | **clean**(2117 파일) |
| 뮤턴트(별도 작업트리 `~/axdev/.wt/cys-ui-slice4-mut` · /tmp 사본 아님 = 기억 「임시 폴더 사본 고정 붉음」 회피) | 39 / 39 | ee510b85 = **51 / 52**(생존 1 = 「F2 마스터 모름이어도 deadman 근거」 — 아래) → 31800d54 = **56 / 56 붉음 · 원복 전부 True**(생존 0 · 증거 `docs/ui-p2/evidence/s4/mutants-fix2.txt`) |
| codex | 1R BLOCK | **2R = REVISE**(major 2 · minor 1 · `codex-r2.json`) → 3건 고침(31800d54) · **3R 안 돌림**(브리프 「2R 1회」) |

- 뮤턴트 생존 1(ee510b85): `masterSilenced` 의 「좌석 모름 = null」 줄 — 이번 고침으로 `itemStall` 이 좌석 모름을 먼저 거르고, 장부는 좌석 모름일 때 생존을 늘 null 로 두어(새 null 줄이 같은 일을 함) 장부 층에서는 등가. 순수 함수 계약으로 핀 1줄(좌석 모름 ∧ 생존 true ∧ deadman → null) 추가 → 31800d54 판에서 붉음 1 확인.
- 「재현 시험 붉음 → 초록」 = 지적마다 「고침 되돌림」 뮤턴트(blocking 4 · major 1~6 각 1~2 · minor 2 · 2R 4)가 붉어지는 것으로 보였다(옛 동작으로 되돌리면 그 지적의 재현 시험이 붉음 · 고친 코드에서 초록).

### 13-4. codex 2R(6bbaae53 의뢰문 · 코드 머리 ee510b85) 지적과 처분 — 31800d54

| 2R 지적 | 처분 | 시험 |
|---|---|---|
| major: 살아 있는 마스터 행의 좌석 번호가 깨진(「"7"」) 응답을 「마스터 없음」으로 확정 → 마스터가 그 좌석으로 옮겨도 stalled 로 거절 호출 | **고침** — `masterOf` = 살아 있는 마스터 행 중 번호가 안전한 정수가 아닌 것이 있으면 undefined(모름) · 끝난 행·행 없음만 null · 주기 관측(`observe`)도 org 원문을 같은 함수로 대조해 깨졌으면 모름 | 장부 「2R major — "7" 행 = 모름 · 처리 직전 호출 0 · 주기 관측 단추 0」 · 뮤턴트 2 |
| major: from_end 가 줄 중간을 시작점으로 → 앞 훑기·뒤 읽기가 같은 줄을 다른 위치로 받아 해결 두 번 | **고침**(viewcore.rs) — from_end 시작점 = `last_line_end`(마지막 `\n` 바로 뒤 · 미완 줄은 뒤 읽기가 그 줄 처음부터 · 뒤에서 64 KiB 씩) | cargo `from_end_start_is_last_complete_line_end`(끝 줄바꿈 · 미완 공백 1바이트 · 줄바꿈 없음 · 200 KB 미완 줄 · codex 재현 꼴 = 완성된 줄 위치 = 시작점) · ⚠ `chat_transcript` 의 배선 한 줄(`let start = last_line_end(…)`) 자체는 비동기·데몬 필요라 시험 밖(코드 읽기로만) |
| minor: 물음 글만 깎아 원문 그대로의 해결을 놓침(20번째 = 끝 공백 · 앞 공백) | **고침** — 물음 글·`resolveKey` 도 원문 그대로(빈 물음만 거름) | judge 「codex 2R minor」 3단 · 뮤턴트 2 |

### 13-5. 커밋(26d4f29c 위)

| 커밋 | 내용 |
|---|---|
| b00800df | codex 1R 고침 — blocking · major 1~6 · minor(코드 · 시험 · e2e · viewcore confirm_reply·레코드 위치 · main.rs 이름 1줄) |
| **12e8bc95** | **팩 지침 별도 커밋** — 해결 표식 문장 「앞부분을 글자 그대로(띄어쓰기 포함) 20자」 + CEO_TEMPLATE 재합성 + 발행 해시표 재생성(직전 판 해시 1쌍 → 이 판 · 태그 유래 같음) |
| ee510b85 | 뮤턴트 도구 — 옛 앵커 갱신 + 1R 되돌림 13(52종) |
| 6bbaae53 | codex 2R 의뢰문 |
| 8f3badab | codex 2R 원문(REVISE) |
| 31800d54 | codex 2R 고침 — major 2 · minor 1 + 핀 1줄 + 2R 되돌림 뮤턴트 4(56종) |
| (이 HANDOFF) | §13 · TODO |

### 13-6. 알려진 남은 위험 · 한계(정직)

- **직접 허락은 지금 데몬에서 늘 닫힘**(지문 표지 없음) — 마스터가 멈추면 사람은 작업 화면의 도우미 창에서 직접 눌러야 한다. 거절은 여전히 대화 화면에서 됨(되돌릴 수 없는 쪽 아님 · 단 A→B 바뀜이면 B 를 거절할 수 있다 = 브리프 결정대로 둠).
- **지문 경로는 대역 시험뿐** — 데몬이 `screen_fingerprint` 를 내고 대조하기 전에는 실물 왕복이 없다(아래 📌).
- **`actuated` 실물 확인은 앞 좌석의 실제 데몬 1회(`actuated:"return"`)뿐** — 이번 `confirm_reply` 로 실제 데몬 재실행은 안 함(도구 `real_daemon_drive.ts` 는 새 명령 꼴로 고쳐 둠 · 지금 데몬엔 지문이 없어 허락 길은 호출 0 이 정상).
- §C idle_secs 실측 못 함(이월 그대로) · 0.5 M4~M8 측정 대기 · FR-C5 5분 = 설계 목표값.
- `main.rs` 이름 1줄 = 원작자 파일 변경 1줄(조각 1 선례 꼴) — 「원작자 파일 0줄」이던 조각 4 의 성질이 깨짐 · 통합 때 편입 충돌 지점 1곳.

### 13-7. 📌 데몬 지문 계약(데몬 티켓 후보 · master 가 냄 — 이 좌석은 데몬 안 건드림)

데몬이 화면에서 감지한 승인 항목(`daemon_issued`)에 대해:
① `feed.list` 항목에 **`screen_fingerprint`**(비어 있지 않은 글 · 예: 그 창의 명령 블록 + 선택지 줄을 정규화한 sha256 앞 16자)를 싣는다 — **이 칸이 있다 = 「집행 직전 지문 대조 지원」 표지**(화면은 이 칸이 있는 판에만 직접 허락을 낸다). 창 내용이 바뀌면 지문도 바뀌어야 한다(같은 번호여도 · 지금 F16 「대기 항목 본문 안 다시 씀」과 별개로 지문은 다시 계산).
② `feed.reply` 는 `screen_fingerprint` 매개변수를 받아, **키를 넣기 직전 지금 좌석 화면에서 같은 방식으로 다시 계산한 지문**과 비교한다 — 다르면 키 0 + 오류 코드 **`approval_fingerprint_mismatch`**(화면 안내 글 준비됨 · 항목은 대기 유지 또는 stale-cleared — 데몬이 정함).
③ 데몬 감지 항목에 대한 operator-token allow 인데 `screen_fingerprint` 가 없으면 거부(지원 데몬에서는 지문 없는 허락 = 옛 화면 · 구멍).
④ 결과 `actuated` 는 지금처럼 유지(「기록만」 구분은 화면이 이미 함).
