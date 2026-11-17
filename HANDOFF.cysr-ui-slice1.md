# HANDOFF — TICKET=cysr-ui-slice1-1117 (cysr 화면 개편 조각 1 · 워커 surface:2152 · 2026-11-17 21:48~23:0x)

- 브리프 = `master/briefs/2026-11-17-cysr-ui-slice1.md`(원장 kind=brief · spawn 경로 · body_sha256 `9af8f025…` = 파일 sha 대조 성립) · 가지 `feat/ui-slice1` ← `feat/ui-slice0` 03592395
- 설계 = `~/axdev/cysr-ui-research/P2-DESIGN.md`(7ba74f3) §11 조각 1 · §2-5 · §5-1·§5-2 · §9-3 · §10(1.1.16 = 새·기존 모두 작업 화면) · 0.5 결과 = `docs/ui-p2/SLICE-0.5-MEASURE-RESULT.md`
- 비가역 0: push·서명·발행·이 기기 앱 교체 = 안 함 · 데몬(원작자 handlers.rs·state.rs 등) 변경 0

## 0. 한눈 요약

| 무엇 | 결과(관측) |
|---|---|
| 전환 단추 「대화 화면 \| 작업 화면」 + registry | 상단바 `#view-switch`(div 안 — 상단 단추 켬끔 목록 밖) · 직렬 전환 · 새 화면이 선 뒤 옛 화면 내림 · 띄우기/그리기 예외 → 작업 화면으로 물러남 + 띠 · 3회면 흐림 · 사람이 고른 화면만 `cys-view` 기억 |
| 기본 화면 | **작업 화면**(새·기존 모두 · §10 개정) — 대화 화면을 안 고르면 invoke 0 · 저장소 쓰기 0 · 타이머 0 |
| 대화 화면 최소판 | 입력칸 → composeOutbound → **쓰기 직전 재조회 1회**(org.status + feed) → 문턱 → `chat_send{human}`(원자 1요청) → 「전달 확인 중」 → 결속 세션 전문 일치 = 「전달됨」 → 사슬 위 assistant 글 = 마스터 답 말풍선 → 쉬면 「답함」 · 붙잡음(cys-chat-hold) · 초안 보존(전환 왕복) |
| Tauri 새 파일 `viewcore.rs` | `chat_send`(human 만 · `refuse_on_approval`·`clear_first` · operator·owner 표지 · 분류 보존 응답 5갈래) · `chat_transcript`(경로 재료는 데몬에서 · 결속 세션 1파일 · 오프셋 이어 읽기 · 잘림 없음 · `from_end`) |
| 작업 화면 동작 변화 0 | `tickrec_gate.py` OFF: 새 번들 = 기준 번들(03592395) — invoke 1088건·저장소·화면 글자(전환 단추 글자만 뺌) sha `308dd2b91f9a` = 조각 0 HANDOFF 와 같은 값 |
| 원작자 파일 | 끼워 넣기만 · 기존 줄 변경·삭제 0 (§2) |

## 1. 바뀐 파일

| 파일 | 누구 | 변경 |
|---|---|---|
| `src-tauri/src/viewcore.rs` | 새(우리) | chat_send · chat_transcript · 순수 도우미(human_send_params · classify_send · transcript_slug · transcript_path · parse_transcript_chunk) + cargo 시험 6 |
| `ui/src/views/contract.ts` | 새 | 등록 계약 타입 |
| `ui/src/views/registry.ts` | 새 | 전환·물러남·누수 0 |
| `ui/src/views/core.ts` | 새 | 공통층 상태 + 행동(쓰기 직전 재조회 · 문턱 · 원자 제출 · 붙잡음 · 세션 읽기) |
| `ui/src/views/judge/{outbound,gate,msgstep,viewpick}.ts` | 새 | 순수 판정(document·window·localStorage·__TAURI__·Date.now·setTimeout 0 — 정적 핀) |
| `ui/src/views/chat/index.ts` · `work/adapter.ts` · `index.ts` · `views.css` | 새 | 그리기 · 작업 화면 감싸개 · 입구 · 스타일 |
| `ui/src/views/{judge/judge,core,registry}.test.ts` | 새 | bun 시험 |
| `ui/e2e/chat_gate.py` | 새 | 실제 번들 + 대역 e2e(A~G) |
| `ui/e2e/tickrec_gate.py` | 우리(조각 0) | SNAP 화면 글자에서 `#view-switch` 만 뺌(기준 번들엔 그 자리가 없음) +3/−1 |
| `docs/ui-p2/evidence/s1/` | 새 | VM 실제 데몬 원자 제출 바이트 · 경합 기록 |

## 2. 원작자 파일 변경 줄(전부 끼워 넣기 · `git diff --numstat 03592395 HEAD`)

| 파일 | +/− | 줄 |
|---|---|---|
| `src-tauri/src/main.rs` | 3/0 | :17 `mod viewcore;` · :8460~8461 `viewcore::chat_send,` `viewcore::chat_transcript,`(generate_handler 머리) |
| `ui/src/main.ts` | 2/0 | :327 `import { bootViews } from "./views/index";` · :11813 `bootViews({ invoke, working: … nodeWorking … })`(`layoutLoaded = true;` 바로 다음 줄) |
| `ui/index.html` | 5/0 | :8 `views.css` 링크 · :16~17 주석 + `<div id="view-switch"></div>`(spacer 다음) · :47~48 주석 + `<div id="view-host" hidden></div>`(`#body-row` 앞) |
| `ui/build.sh` | 1/0 | :10 `cp src/views/views.css dist/views.css` |

## 3. 수용 기준 표(§11 조각 1 + 브리프 「0.5 결과에서 반드시 넣을 수용 기준」)

| # | 기준 | 판정 | 근거(시험 이름 · 출력) |
|---|---|---|---|
| 1 | 보내기 1 → 쓰기 1(원자) | **통과** | core.test 「문턱 통과 = chat_send 1건 · kind human · 마스터 좌석 · 앞서 org_status + feed_list」 · chat_gate B 「쓰기 1 · kind human · 마스터 좌석」 · VM 실제 데몬 바이트(§5) |
| 2 | 문턱 실패 → 쓰기 0 | **통과** | core.test 문턱 9갈래(초안·feed 대기·feed 모름·org 모름·마스터 없음·죽음·관문·30초·바쁨) 각각 쓰기 0 · 뮤턴트 10 전부 붉음(§4) |
| 3 | 승인 창 → 데몬 거부 = 붙잡음 | **통과** | core.test 「승인 창 → 데몬 거부 = 붙잡음 · 쉼 동안 재시도 0 · 쉼 뒤 1회」 · chat_gate D · cargo `classify_covers_the_four_outcomes`(approval_screen → held) |
| 4 | 불명 응답 → 「확인 중」 · 다시 보내기 0 | **통과** | core.test 「불명 → 확인 중 · 폴 20번에도 재전송 0」·「Tauri 다리 예외도 확인 중」 · chat_gate D(단추 0 · 30초 재전송 0) · 뮤턴트 「불명→failed」 붉음 |
| 5 | 전환 왕복 초안 같음 | **통과** | chat_gate E 「초안 왕복 같음 · 쓰기 0」 |
| 6 | 최소 계약 5칸 | **통과** | chat_gate B 「최소 계약 4칸 + 공통 전환 단추」(`[data-min=confirms|lastSendStep|masterHealth|errors]` + `#view-switch`) |
| 7 | 새 설치·마스터 꺼짐 → 대화 화면 흐림 0 · 긍정 신호만 불가 | **통과** | chat_gate F 3장면 · judge.test 「§9-3 긍정 신호만 불가」 |
| 8 | 실물: 「안녕」 → 마스터 답 보임 + 마스터 좌석 안 `javis_mission.py status` exit 0 | **측정 대기** | 진짜 Claude 로그인 필요(0.5 M4 와 같은 재개 조건) · 대신: VM 실제 데몬 원자 제출 바이트 1회 + 세션 경로 규칙 대조(§5) |
| 브1 | ★마스터 입력줄에 사람 초안 → 쓰기 0(붙잡음 + 안내) | **통과** | gate `draft`(pending 두 칸 > 0 ∨ 붙여넣기 열림 · 모름 = input_unknown) · core.test 「★수용 1 사람 초안 12바이트」 · chat_gate C 「★수용1 … 3틱 지나도 쓰기 0 → 비면 1건」 |
| 브2 | ★화면 문턱 = 쓰기 직전 판정 + feed 승인 대기 항목 둘 다 | **통과** | 쓰기 직전 재조회(org.status + feed.list) 뒤 gate `approval`/`approval_unknown` · 데몬 쪽은 같은 요청의 `refuse_on_approval` · core.test 「★수용 2」 · chat_gate C |
| 브3 | ★시간 상수 = 실측값 | **통과** | `ATOMIC_SUBMIT_MS {728,768,836}`(0.5 M1) · 첫 세션 읽기 1000ms ≥ 836 핀 · `MEASURED_QUEUE_HOLD_AFTER_HUMAN_SECS 31.2`(0.5 M10) · 문턱 30초 = 데몬 기본 `CYS_QUEUE_HUMAN_QUIET_SECS` — judge.test 핀 |
| 브4 | ★세션 경로 = `<좌석 claude_config_dir>/projects/<cwd 슬러그>/<id>.jsonl` | **통과** | cargo `slug_and_path_follow_measured_layout` · VM 실제 데몬 좌석 재료로 경로 실재 확인(§5) · `~/.claude*` 가정 0(설정 폴더 없으면 「모름」) |
| — | 작업 화면 동작 변화 0 | **통과** | tickrec_gate OFF = 기준 번들 같음(§5) |
| — | 뮤턴트(문턱 조건 하나씩 빼면 붉음) | **통과** | §4 14개 전부 붉음 |
| — | U20(긴 붙여넣기 기록 꼴) · U21(둘째 줄 `/`) · U25(바쁜 중 붙여넣기) · M8(uuid 사슬) | **측정 대기 · 보수 기본값** | 상수 4개(`U20_PASTE_RECORD_FORM`·`U21_LATER_LINE_SLASH_SAFE=false`·`U25_BUSY_PASTE_OK=false`·`M8_UUID_CHAIN`) — 값이 오면 상수만 바꾸면 됨 · 지금 = 전문 일치만 / 둘째 줄 `/` 막음 / 바쁘면 붙잡음 / uuid 없으면 답을 그 말에 묶지 않음(「마스터」 일반 말풍선) |

## 4. 뮤턴트(소스를 하나씩 바꿔 bun 시험이 붉어지는지 · 매번 원복 확인 `True True True`)

| 뮤턴트 | 붉은 시험 수 |
|---|---|
| gate `status_unknown` 줄 주석 | 2 |
| gate `no_master` | 3 |
| gate `agent_dead` | 2 |
| gate `gate_pending` | 2 |
| gate `approval_unknown` | 2 |
| gate `approval` | 3 |
| gate `input_unknown` | 1 |
| gate `draft` | 2 |
| gate `human_recent` | 2 |
| gate `busy` | 2 |
| core 문턱 거부 분기 제거(`if (!g.ok)` → `if (false)`) | 11 |
| core 쓰기 직전 재조회 대신 들고 있던 값 | 8 |
| core 불명도 다시 보내기 허용(uncertain → failed) | 2 |
| viewcore.rs `refuse_on_approval: false` | 1(bun 정적 핀) · cargo `human_params_are_one_atomic_request_with_both_tokens` 도 같은 키를 잰다 |
| (codex 1R 뒤) core 복원 말 자동 제출 허용 | 2 |
| (codex 1R 뒤) core 「보내는 중」 영속 실패 무시하고 씀 | 1 |
| (codex 1R 뒤) core reset 무시 | 1 |

| (codex 2R 뒤) core 관측 유효시간 검사 제거 | 1 |
| (codex 2R 뒤) core 세션 소비 집합 대신 빈 집합 | 1(첫 시험은 이 뮤턴트를 못 잡아 — 말 목록 정리 장면 시험을 더해 붉게 함) |
| (codex 2R 뒤) core 복원 말 내부 id 대신 저장소 id | 2 |

| (codex 3R 뒤) core 쓰기 직전 관측 나이 재검사 제거 | 1 |

재실행(19c14ad7 · `python3 docs/ui-p2/evidence/s1/tools/mutants.py`): **21개 전부 붉음** · 원복 확인 True ×3.

## 5. 게이트 결과(기준선 = 03592395 · 같은 기기 · 부하 load 23~34)

| 대상 | 이 조각(최종 b50fce4b 소스) | 기준선 03592395 | 판정 |
|---|---|---|---|
| bun test(ui) | **3548 pass · 88 skip · 0 fail**(19c14ad7) | 3472 · 88 · 0 | +76 = 새 views 시험(judge·core·registry) |
| `bun test src/views` | **97 / 0**(조각 1 76 + tickrec 21) | 21 / 0 | — |
| tsc `bun x --package typescript@7.0.2 tsc -p tsconfig.check.json` | **rc 0** | rc 0 | 같음 |
| cargo `-p cys-app --bin cys-app` | **344 pass · 0 · 2 ignored**(최종 · viewcore 7/0) | (+새 viewcore 시험만 늘어남 〔기준선 미실행 — 추정 337〕) | 실패 0 |
| `cargo build --bins` | rc 0 | rc 0 | 같음 |
| 화면 게이트 10종(4539d591 번들 · 작업 화면 코드는 그 뒤 무변경 — 바뀐 것 = views/ 대화 화면 길뿐) | race 108/0 · focus 72/0 · seatrows 75/0 · pillar 77/0 · seatgroup 8/0 · rolereuse 11/0 · stty 7/0 · nodept 16/0 · restart 6/0 · hidden_block 18/0 | 조각 0 HANDOFF §5 와 같은 수 | 같음 |
| `tickrec_gate.py` OFF(b50fce4b 번들 · 94d0884f 에서도 같음) | 새 = 기준 · invoke 1088 · 저장 키 3 · 화면 글자(전환 단추 뺌) · sha `308dd2b91f9a` | `308dd2b91f9a`(조각 0) | **작업 화면 동작 변화 0** |
| `chat_gate.py`(19c14ad7 번들) | **PASS · ok 36 / FAIL 0** | — | 새 게이트 |
| 뮤턴트 | **21 / 21 붉음**(§4) | — | — |
| 공개 secret-scan `scripts/secret-scan.sh --all`(커밋 뒤) | 1차 적발 2(VM 홈 경로 · 시험 견본 맥 홈 꼴 경로) → 고친 뒤 clean · HANDOFF 커밋 뒤 이 줄 자체 1건 → 고친 뒤 **clean** | clean | 같음 |
| 실제 데몬 1회(VM 격리) | 원자 제출 바이트 `0x15` → +198ms 울타리 51B → +540ms `0x0d` · `{"sent":true}` · 세션 경로 실재 | — | §5 바깥 증거 = `docs/ui-p2/evidence/s1/vm-atomic.txt` |

- 흔들림: 조각 0 `tickrec.test.ts` 최악 장면 시험이 화면 게이트·codex 와 겹친 부하에서 5초 상한 초과로 2회 붉음 → 혼자 다시 21/21 · 기준 작업트리도 같은 시험 2.3~2.7초(§9).
- 화면 게이트 캡처(`docs/evidence-tabs-sidebar/`)는 커밋 전 스크래치로 옮김.

## 5-b. codex 적대 검토

| 회 | 대상 | 판정 | 내용 |
|---|---|---|---|
| 1R | 4539d591 | **BLOCK**(blocking 3 · major 5) · 원문 `docs/ui-p2/evidence/s1/codex-r1.json` | ① 붙잡은 말 저장소 지우기 실패 + 불명 → 다시 켤 때 재제출 ② 문턱 통과 뒤 세션 시작점 RPC 대기(초안 지울 틈) ③ 저장소 글이 사람 표지로 자동 제출 ④ 2초 오차 자기 입력 면제가 다른 사람 입력도 면제 ⑤ 코드 없는/모르는 거부를 failed(다시 보내기 열림) ⑥ 다른 프로젝트 폴더 같은 이름 파일 읽기 ⑦ 심볼릭 링크 탈출 ⑧ reset 재읽기로 한 uuid 두 말 배정 — **8건 전부 타당 판단 · 전부 고침(94d0884f)** · 고친 곳마다 시험 + 뮤턴트 3 추가 |
| 2R | 94d0884f | **BLOCK**(1R 8건 중 닫힘 3 · 부분 5 · blocking 2 · major 3) · 원문 `codex-r2.json` | 잔존: ① feed·org 병렬 조회 = 마지막 입력줄 관측 뒤에 느린 feed 를 기다림(관측 유효시간 없음) ② 저장소 id 신뢰 → 새 말 id 와 겹치면 복원 `/clear` 가 선택됨 ③ 링크 경계가 `projects` 전체 · 확인 뒤 다시 열기 ④ 소비 uuid 를 말 목록에서 재구성(정리되면 잊음) ⑤ 새 교착: 복원 20개면 「이 말 보내기」가 상한에 막힘 — **전부 고침(b50fce4b)** · 시험 6 + 뮤턴트 3 추가 |
| 3R | b50fce4b | **BLOCK**(13건 중 닫힘 11 · 부분 2) · 원문 `codex-r3.json` | 잔존: ① 마지막 관측 뒤 영속·그리기가 늦으면 낡은 빈칸 판정으로 씀(쓰기 직전 나이 재검사 없음) ② 핸들 inode 대조로는 중간 폴더 바꿔치기를 못 막음 — **둘 다 고침(19c14ad7)**: chat_send 바로 앞 관측 나이 재검사 · 설정 폴더 핸들에서 경로 요소마다 `openat`+`O_NOFOLLOW` |
| 4R | 19c14ad7 | **REVISE**(15건 중 닫힘 11 · 부분 4 · major 1) · 원문 `codex-r4.json` | 3R 두 건 유닉스에서 닫힘 · 잔존 = 비유닉스 open_bound 가 경로를 다시 찾음(바꿔치기) · 허용 목록 「쓰기 0」 근거 줄 미명시 — **고침(1ec9aafc)**: 윈도는 결속 파일을 읽지 않음(`unsupported_platform` → 화면 「모름」 · 조각 10) · 코드마다 handlers.rs 줄 근거 주석(전부 `surface.send_text` 분기 안 쓰기 전 반환 확인) |
| 5R | 1ec9aafc | **ESCALATE**(새 결함 0 · 4R major·비유닉스 부분 3건 닫힘 · R1-5 만 「범위 밖 도우미 응답을 그대로 돌려주는 길이 있어 확정 불가」) · 원문 `codex-r5.json` | **내가 닫음(근거)**: 그 도우미 = handlers.rs:8244 `hand_off_direct_job`(:4475) → `try_write`(:386) 오류는 `write_stalled`·`write_failed` 둘뿐 — 둘 다 허용 목록 밖이라 이미 `uncertain`(다시 보내기 0). 즉 허용 목록 코드는 전부 쓰기 전 반환에서만 나온다. ⚠codex 가 이 줄을 직접 확인한 것은 아니다 — master 독립 검증 좌석이 이 한 줄을 대조하면 수렴. |

## 6. 내가 내린 판단(지시에 없던 것 · master 확인 후보)

1. **대화 화면이 켜져 있을 때만** org.status + feed.list 를 3초마다 따로 부른다(작업 화면 3초 고리와 별도 · 대화 화면 RPC = 작업 화면 + 2/3초). 고리 한 벌 합치기는 조각 2(설계 §2-1) — 지금 고리 본문에 줄을 넣으면 조각 0 정적 핀·편입 충돌면이 커져서.
2. **데몬이 승인 창으로 거부한 말 = 15초 쉼 뒤 재시도**(`HELD_REFUSED_BACKOFF_MS` 설계 목표값) — feed 항목 없이 창만 떠 있으면(0.5 숫자 3 술어 차이) 3초마다 두드리는 것을 막으려고(4군 ①).
3. **앞 말을 쓰는 중 받은 말 = 붙잡았다가 앞 말 뒤 1건씩**(`after_prev`) — 첫 판은 그 말을 버렸다(자기 검증에서 찾음).
4. **첫 보내기의 세션 시작점(from_end) RPC 뒤 org.status·feed 를 한 번 더** 받고 곧바로 쓴다 — 시작점 RPC 가 문턱 판정과 쓰기 사이에 끼면 경합 창이 그만큼 넓어져서(자기 검증에서 찾음 · core.test 핀).
5. **막힌 말(`/clear` 등)은 입력칸에 남긴다** — 첫 판은 비워서 사람이 친 글을 잃었다(자기 검증).
6. **「답함」은 세션 읽기에서 칠하지 않고 다음 조회의 새 활동 관측으로만** — 들고 있던 활동 값이 그 답보다 옛 관측일 수 있어서(시험이 잡음).
7. **사람 입력 30초 = 내 보내기도 포함해 붙잡음**(codex 1R ④ 뒤) — 첫 판의 「2초 오차로 내 보내기 짝짓기」는 다른 사람 입력도 면제해서 없앴다. 그래서 대화 화면에서 **연달아 보낸 둘째 말은 첫 말 뒤 30초 + 마스터가 쉴 때** 나간다(붙잡음 → 자동 1건). 설계 R3(사람 보내기마다 30초 큐 묶임)와 같은 박자.
12. **조회 순서 = feed 먼저 · org.status(입력줄) 마지막 · org.status 왕복 500ms 넘으면 낡은 관측**(`OBS_MAX_MS` 설계 목표값 · codex 2R ①) — 대역 경합 모형에서 쓰기가 한 홉(20ms) 늦어져 새는 점 7 → 8(§7).
11. **다시 켠 뒤 붙잡은 말 = 자동 제출 0**(codex 1R ③ 뒤) — 설계 §2-5 「문턱 재통과 때 오래된 것부터 1건씩」은 **같은 실행 안**에서만. 저장소에서 읽은 말은 「이 말 보내기」 신뢰 클릭 + 다듬기부터 다시.
8. **`chat_send{kind:"auto"}`(기계 문안 큐)는 만들지 않고 거부** — 조각 1 범위 = 사람 말. 깨움·1회 안내는 조각 5·8.
9. **세션 파일 = 슬러그 경로 하나뿐**(codex 1R ⑥ 뒤 대비 길 없앰) · 링크를 푼 실제 경로가 `<cfg>/projects` 아래 보통 파일이어야 함. 긴 cwd 를 Claude Code 가 줄인 슬러그로 쓰면 「모름」(전달 확인 중 → 오래 걸려요)으로 남는다 〔줄임 규칙 실측 없음〕.
10. **tickrec_gate SNAP**: 화면 글자 대조에서 `#view-switch` 만 뺀다(기준 번들엔 그 자리가 없음). invoke 열·저장소는 그대로 바이트 대조.

## 7. 알려진 남은 위험 · 한계(정직)

- **쓰는 도중 승인 창**(0.5 숫자 2): 화면 문턱으로는 못 막는다 — 대역 시각 주입 기록(`docs/ui-p2/evidence/s1/chat-gate-race.json` · b50fce4b): 승인 창이 누름 −1.5~+1.5초(100ms 간격 31점) 중 한 시각에 뜰 때, 쓰기와 겹치는 24점 중 **막힘 66.7%**(feed 지연 0ms = 전부 화면 문턱 · feed 지연 1000ms = 화면 문턱 25.0% + 데몬 거부 41.7%) · **새는 8점(33.3%) = 쓰기 시작 뒤 0.77초 창 안**(데몬 Enter 직전 재판정 없음 가정 = 0.5 M2-c). (처음 판 4539d591 = 23점 중 7점 샘 · 69.6% — 조회를 직렬로 바꾼 뒤 쓰기가 대역 한 홉 늦어짐.) 데몬 고침(2150 좌석)이 들어오면 그 7점이 데몬 거부로 바뀌어야 한다(같은 하네스로 재측정 가능). ⚠이 %는 대역 모형 값(가짜 시계 · fetch 지연 20ms 가정 · 균등 격자)이지 실측 빈도가 아니다.
- **목록 늦음**: 문턱은 쓰기 직전 재조회 값으로 본다. 그 조회와 쓰기 사이(웹뷰→Tauri→데몬 · 0.5 M12 데몬 몫 < 1ms · 웹뷰 구간 미측정)에 사람이 다른 길로 치면 Ctrl-U 가 지운다 — 설계 「단점(정직)」 그대로.
- **접근성**: 전환 단추가 상단바 안이라 높이 28px · 글자 13px(설계 §9-2 「누를 면 44×44 · 18px 미만 0」 미달) — 상단바 높이를 바꾸지 않으려고 둔 것. 조각 10(배포 게이트) 걷기에서 판정 📌.
- 실물(진짜 Claude) 걷기 0 — 수용 8 측정 대기.
- **윈도**: 결속 세션 파일을 읽지 않는다(codex 4R) — 윈에서 대화 화면은 보내기·붙잡음은 되고 「전달됨」·마스터 답 말풍선은 안 뜸(「전달 확인 중 → 오래 걸려요」). 윈 교차 컴파일 확인은 이 기기에서 불가(`cargo check --target x86_64-pc-windows-msvc` = libsqlite3-sys C 빌드 실패 · viewcore 무관).

## 8. 재현 명령

```sh
W=~/axdev/.wt/cys-ui-slice1; cd $W/ui
bun install --frozen-lockfile && sh build.sh && bun test                         # 기대 = §5 표
bun x --package typescript@7.0.2 tsc -p tsconfig.check.json                       # 기대 rc 0
bun test src/views                                                                # 기대 86/0(조각 1 시험 65 + tickrec 21)
cd $W && cargo test -p cys-app --bin cys-app viewcore                             # 기대 6/0 (ui/dist 가 있어야 컴파일됨 — 먼저 build.sh)
# 기준 번들: git -C $W worktree add --detach /tmp/claude-501/s1base 03592395 && (cd /tmp/claude-501/s1base/ui && bun install --frozen-lockfile && sh build.sh)
CHROME_PATH=<chrome-headless-shell> BASE_DIST=/tmp/claude-501/s1base/ui/dist cys run -- <playwright python3> ui/e2e/tickrec_gate.py   # 기대 RESULT: PASS · 308dd2b91f9a
CHROME_PATH=<chrome-headless-shell> cys run -- <playwright python3> ui/e2e/chat_gate.py                                            # 기대 RESULT: PASS
```

## 9. 함정

- `cargo test -p cys-app` 는 `ui/dist` 가 없으면 `generate_context!` 가 패닉(frontendDist 없음) — 새 작업트리는 먼저 `sh ui/build.sh`.
- 새 작업트리에 `target/`·`src-tauri/{runtime,binaries,resources,gen}` 이 없으면 처음부터 빌드 — 다른 작업트리에서 `cp -cR`(APFS 복제 · 8초)로 가져옴.
- `#body-row` 는 CSS `display:flex` 라 `[hidden]` 이 안 먹는다 → 작업 화면 어댑터는 `style.display` 로 숨김.
- 숨은 요소엔 포커스가 안 들어간다 — 대화 화면 mount 때 `#view-host` 는 아직 숨김(옛 화면을 내리며 같은 전환 안에서 보임) → 포커스는 microtask 로 미룸(첫 판은 포커스가 body 로 감 · chat_gate 가 잡음).
- 대역 org.status 의 `idle_secs: 1` 은 `nodeWorking` 에서 「답하는 중」 → U25 보수 기본값이 모든 보내기를 붙잡는다(첫 게이트 실행에서 관측) — 대역 장면은 `idle_secs` 를 크게.
- 이 기기 부하(load 25~34)에서 조각 0 `tickrec.test.ts` 의 최악 장면 시험이 5초 상한을 넘어 1회 붉음 → 혼자 다시 = 21/21 · 기준 작업트리(03592395)도 같은 시험 2.3~2.7초 — 부하 흔들림.
- `cys run -- …` 을 `( … &)` 로 떼어 띄우면 좌석 귀속을 잃어 `ledger.register` 가 ACL 로 거부되고(external lacks write-shell) 프로세스가 바로 죽는다 — 백그라운드는 도구의 백그라운드 실행으로.
- codex 는 `codex exec --sandbox read-only -o <파일> -` 로 판정 JSON 만 받음(NODE_OPTIONS 비움 서브셸).

## 10. 커밋 목록(03592395 위)

| 커밋 | 내용 |
|---|---|
| 4539d591 | 조각 1 본체(viewcore.rs · views/ · 배선 · 시험 · 게이트 · VM 증거) |
| 94d0884f | codex 1R(BLOCK) 8건 + 자기 검증 3건 |
| b50fce4b | codex 2R(BLOCK) 잔여 5건 |
| 19c14ad7 | codex 3R(BLOCK) 잔여 2건 |
| (secret-scan) | VM 증거 홈 경로 · 시험 견본 경로 → 공개 secret-scan clean |
| 1ec9aafc | codex 4R(REVISE) — 윈도 결속 파일 읽기 거부 · 거부 코드 근거 줄 |
| (이 커밋) | HANDOFF · codex 5R 원문 |

## 11. 📌 덧붙임(브리프에 없던 것 — master 판단 후보 · 실행 안 한 것 포함)

1. 📌 **전환 단추 접근성**: 상단바 안 28px·13px(설계 §9-2 미달) — 조각 10 걷기에서 판정.
2. 📌 **대화 화면 3초 조회를 작업 화면 고리와 한 벌로**(조각 2) — 지금은 대화 화면이 켜져 있을 때 org.status·feed.list 를 따로 부름.
3. 📌 **첫 글자 `#`**(Claude Code 메모 단축으로 읽힐 수 있음 〔추정 · 판별 실측 없음〕) — 막지 않았다(설계에 없음). U21 측정 때 같이 재면 쌈.
4. 📌 **다시 켠 뒤 붙잡은 말 = 사람 확인**(codex 1R ③ 반영으로 설계 §2-5 「재통과 때 자동 1건」을 같은 실행 안으로 좁힘) — 설계 문서 개정 후보.
5. 📌 **사람 입력 30초 = 내 보내기 포함**(codex 1R ④ 반영) — 연달아 보낸 둘째 말이 30초+쉼 뒤에 나감. 데몬이 「이 사람 입력은 이 요청(원자 제출)」을 응답에 실어 주면 짝짓기가 정확해짐(데몬 변경 후보 · NFR-F3).
6. 📌 **데몬 고침(2150 · Enter 직전 승인 재판정) 들어온 뒤** `chat_gate.py` G 를 다시 돌려 새는 8점이 데몬 거부로 바뀌는지 확인(대역에 「Enter 직전 재판정」 모드 1줄 추가 필요).
7. 📌 **설계 문서 개정 후보**: §5-1 세션 경로 꼴(`~/.claude*` → 좌석 `claude_config_dir`) · §2-5 「400ms 뒤 Enter」 → 실측 0.47~0.55초.
