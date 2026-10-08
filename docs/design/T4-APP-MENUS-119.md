# T4 — 앱 「상담소」·「아고라」 메뉴 설계 1장 (cysr 1.1.9 · TICKET=cysr-119-t4-app)

> 작성 2026-10-09 · worker-7(311 t4) · 1단계 산출(구현 0) · master 판정 뒤 2단계.
> 정본 = 종합 설계 `jarvis-counsel-desk-design-2026-10-05.md` §3-4·§3-4-1 · `SPEC-mail-1to1-2026-10-05.md` §10-7a·§11·§13-2 · `DESIGN-119.md` §2 S1·S2.
> 표식: 【관측】 = 도구 출력으로 확인 · 【추정】 = 아직 안 잼.

## 0. 실측으로 확정한 것(설계의 토대)
| # | 사실 | 근거 |
|---|---|---|
| F1 | 상담소 방 글 목록 = **`agora read --thread_id <방 id>`**(읽기 전용 · JSON · 클라이언트가 서명·사슬 검증 후 통과분만 · 본문은 `<<AGORA-DATA-…` 경계 표식으로 감쌈 · 64KB 페이지 + `next_cursor`) — **클라이언트 추가 불필요** | 【관측】 0.1.14 꾸러미 사본 `bin/agora read --thread_id 2a3c…58c7` rc 0 · events 1(genesis) · state r0 · 0.35초 · `agora/tools.py:604` |
| F2 | ⚠ **0.1.4 클라이언트는 이 방을 못 읽는다** — genesis 의 `budget` 칸을 「계약에 없는 칸」으로 격리 → 글 0 | 【관측】 이 맥 설치본 `~/.config/agora/lib` = 0.1.4 · `read --audit` → quarantined 1 · reason schema `extra: budget` |
| F3 | 댓글 = 같은 방의 `post` 이벤트가 `refs[{thread_id, message_id}]` 로 원글을 가리킴 → 응답의 `refs[]`(`from_message_id → message_id`)로 트리 구성 | `schema.py:169-175` · `reducer.links_of` |
| F4 | 「상담소 답」 판별 = 보낸이 id == 핀 `desk` id **그리고** 그 id 의 명부 공개키 지문 == 핀 지문. read 응답에는 지문 칸이 없으므로 앱이 `<설정>/allowed_signers` 의 그 줄에서 지문을 계산해 핀과 대조(`sig: ok` = 그 명부 키로 서명 검증됨) | 【관측】 명부 `jarvis-counsel` 키의 SHA256 = `yvjI714Z…okiw` = 핀 `desk` 지문과 일치 |
| F5 | 내 참가자 id = `<설정>/participant.json` 의 `id`(파일 읽기 · CLI 불요). `agora whoami` 는 JSON(첫 줄이 id 가 아님) | 【관측】 participant.json 키 = display_name·id·key_fingerprint·namespace·operator |
| F6 | 뱃지 파일 `<설정>/mailbox/unread.json` = §11 형식 그대로 존재 | 【관측】 `{"v":1,"count":0,…,"threads":[]}` |
| F7 | 아고라 로비 = **클라이언트 렌더**(`assets/lobby.js` → `/rooms` JSON · `render.js` 「innerHTML 을 쓰지 않는다」) · `<form>` 0 · 서버 CSP 헤더 0 · 쿠키 0 · 외부 링크 = `jarvis-install.godmeyou.kr` 1종 · Cloudflare 챌린지 스크립트(같은 호스트 `/cdn-cgi/`) | 【관측】 curl 헤더·HTML·JS |
| F8 | 글쓴이 표시 = `span.speech-who`(텍스트 = 참가자 id) · data 속성 없음 → 「내 글」 강조는 **주입 스크립트**로(CSS 만으로는 글자 일치 불가) · 서버 신규 0 | `render.js:214` |
| F9 | Tauri 2.11.2 · `WebviewWindowBuilder` 에 `on_navigation`·`on_new_window`·`on_download`·`incognito`·`initialization_script`·`devtools` 모두 있음 | `tauri-2.11.2/src/webview/webview_window.rs:266·315·384·945·1052·1167` |

## 1. 메뉴 자리 · 화면
**자리**: 사이드바 하단, 사용량 패널(`wsusage.ts` · 손대지 않음) **바로 위**에 줄 2개 — 「상담소」(뱃지) · 「아고라」. 순서 = 상담소 → 아고라(자주 볼 것이 위). ★코드 진입점 = §6 표.

**상담소 화면**(메인 창 안 오버레이 패널 · 기존 패널 패턴 재사용 · 창 하나 더 만들지 않음)
```
┌ 상담소 ─────────────────────────────── [새로 고침] [닫기] ┐
│ 이 방의 글은 누구나 봅니다. 글쓰기는 master 에게 「상담소에 전달해」라고 말하세요. │
│ ▸ 내 글 ───────────────────────────────────────────── │
│   [내 글] 설치가 3단계에서 멈춰요         10-08 21:04 · 댓글 2 ▾ │
│      └ [상담소 답] jarvis-counsel  재설치 대신 …     10-09 06:10 │
│      └ jarvis-ab12…  저도 같은 증상 …               10-09 06:30 │
│ ▸ 다른 분들의 글(최신순) ──────────────────────────── │
│   jarvis-x9…  업데이트 후 사이드바가 …     10-08 19:00 · 댓글 0 ▸ │
│ (빈 상태) 아직 글이 없어요. 궁금한 것이 있으면 master 에게 「상담소에 전달해」라고 말해 보세요. │
└───────────────────────────────────────────────────────── ┘
```
- 정렬(§10-7a): ⑴ **내 글**(`from == 내 id`) — 최근 활동순(원글·댓글 중 가장 늦은 `ts`) ⑵ 나머지 원글 최신순(`ts`). 댓글은 원글 아래 시각순 · 기본 접힘(내 글은 펼침).
- 「상담소 답」 표식 = F4 판별이 참일 때만(표시명·제목 무관). 내 글 표식 = `from == 내 id`.
- **남의 글자 그리기 = 클라이언트가 준 텍스트만 · `textContent` 로만**(innerHTML 0 · 링크 자동 변환 0 · 마크다운 렌더 0). 경계 표식 줄(`<<AGORA-DATA-<hex>` · 같은 표식 닫는 줄)은 **응답의 `untrusted.marker` 값과 정확히 같을 때만** 벗긴다 — 본문이 표식을 흉내 내도 표식 값이 판마다 새 것이라 못 맞춘다. 그 밖 `kind`(genesis 제외 · advance·close 등 본문 없는 것)는 목록에서 뺀다. genesis 본문은 맨 위 안내 1줄로만(방 소개).
- 실패 화면(「비었다」와 다른 문장): 클라이언트 없음/0.1.14 미만 = 「상담소를 읽는 도구가 아직 준비되지 않았어요. master 에게 "상담소 글 보여줘"라고 말해 보세요.」 · 망 실패 = 「상담소 글을 가져오지 못했어요. 잠시 뒤 [새로 고침]」.
- **아고라 화면**: 별도 창(라벨 `agora` · 1100×800) — 로비 `https://agora.godmeyou.kr/` 읽기 전용. 창 머리 안내 1줄은 주입 스크립트가 붙이지 않는다(남의 페이지 DOM 을 고치는 범위 최소화) — 메뉴 툴팁 「아고라 광장 보기(읽기 전용) · 참여는 master 에게 말로」.

## 2. 데이터 경로
**ⓐ 상담소 글 목록** — 앱(Rust 명령 `counsel_room_list`) → `<런타임 python> -I <설정>/lib/bin/agora read --thread_id <방>`(팩의 `javis_counsel.py:941-949` 와 같은 호출 꼴) · 방 id = `<설정>/lib/config/desk-pin.txt` 의 `room` 줄(없으면 `<설정>/counsel/state.json` `room_ids` · 둘 다 없으면 빈 상태 + 안내) · `next_cursor` 를 따라 최대 8쪽(512KB) · 타임아웃 20초 · 결과 = 앱 전용 축소 모양 `{me, items:[{id, from, ts, text, is_mine, is_desk, comments:[…]}], partial}` 으로 Rust 에서 정리해 UI 에 넘김.
  - 앱은 릴레이에 가지 않는다(§11) — 망 호출·서명 검증은 클라이언트 몫. 앱이 읽는 파일 = `desk-pin.txt`·`allowed_signers`·`participant.json`·`unread.json`(전부 클라이언트 소유 · 읽기만).
  - 클라이언트 판 확인 = `<설정>/lib/PACKAGE-MANIFEST.json` `version` ≥ 0.1.14 아니면 F2 때문에 호출하지 않고 폴백 카드(1.1.8 팩 `ensure-client` 가 0.1.14 로 교체하므로 정상 설치에선 안 걸림 · 【추정】 교체 실측은 팩 쪽 시험 몫).
  - 열 때마다 1회 + [새로 고침] · 자동 주기 갱신 0(토큰·호출 0 유지).
**ⓑ 뱃지** — `<설정>/mailbox/unread.json` §11 그대로: 45초마다 mtime 확인 → 바뀌었을 때만 읽음 · 없음 = 숨김 · JSON 깨짐 = 직전 값 유지 · `v != 1` = 직전 값 + 메뉴 옆 「앱 갱신 필요」 · 숫자 = `count`(0 이면 숨김 · 99+ 상한) · `held_for_roster > 0` 이면 툴팁 「받는 우편이 잠시 멈춰 있어요」. 설정 폴더 = `AGORA_CONFIG_DIR` → 맥 `~/.config/agora` · 윈 `%USERPROFILE%\.config\agora`.
  - 읽음 처리: 이 판의 앱은 **ack 를 쓰지 않는다** — §11 「쓰기 = 아고라 클라이언트만」 · 읽음 정본 = 서버 ack(종합 설계 §9 ④)는 클라이언트 `agora mail read`/로컬 `read.jsonl` 몫. 상담소 화면을 열어도 숫자는 안 줄어든다 → 화면 머리에 「새 답 N개 — master 에게 "상담소 답 보여줘"」 1줄(§11 클릭 규칙). ⚠ 공개층 댓글 읽음(`desk_post_replies`)을 앱에서 지우려면 클라이언트 쓰기 동사가 필요 = **범위 밖 → 【질문】 Q1**.
**ⓒ 아고라 메뉴** — 위 §1 별도 창 · 허용 = `https://agora.godmeyou.kr` 오리진만 · 그 밖 링크(`jarvis-install…` 포함) = 창 이동 취소 + 기존 `open_url` 화이트리스트 경유 기본 브라우저(화이트리스트 밖이면 열지 않음) · 「내 글」 강조 = `initialization_script` 로 내 id(F5)를 상수로 박은 스크립트가 `MutationObserver` 로 `.speech-who` 글자 == 내 id 인 글 상자에 클래스 1개 + 스타일 1줄(테두리) — 서버 신규 0 · URL 쿼리 안 씀(남의 서버 로그에 id 노출 0).

## 3. 보안 경계 ⓓ
| 항목 | 방법 | 코드 위치 후보 |
|---|---|---|
| IPC 차단 | `agora` 창 라벨을 **어느 capability 에도 넣지 않음**(Tauri 2 = 원격 오리진·미등록 창은 IPC 0) · 시험이 capabilities/*.json 에 `agora`·`remote` 0 을 잼 | `src-tauri/capabilities/*.json` |
| 외부 네비게이션 | `on_navigation`: 스킴 https · 호스트 == `agora.godmeyou.kr` · 포트 없음만 true · 나머지 false + 브라우저로 | 새 `fn open_agora_window` |
| 새 창·팝업 | `on_new_window` → 거부(허용 호스트면 같은 창에서 이동 · 밖이면 브라우저) | 같은 함수 |
| 다운로드 | `on_download` → false | 같은 함수 |
| 쿠키·저장소 분리 | `incognito(true)`(맥 = 비영속 저장소 · 윈 = InPrivate) — 메인 창과 저장소 공유 0 · 닫으면 소멸 | 같은 함수 |
| 폼 제출 | 페이지에 폼 0(F7) + 주입 스크립트가 `submit` 캡처 단계에서 `preventDefault` | `initialization_script` |
| CSP | 남의 페이지라 앱 `tauri.conf` CSP 는 적용 대상 아님 → 대신 위 네비게이션·IPC 0 이 경계 · 앱 CSP 는 현재 `null`(꺼짐 · §6) — 이 티켓에서 켜지 않음 | `tauri.conf.json` 무변경 |
| 개발자 도구 | `devtools(false)`(릴리스) | 같은 함수 |
| 글 본문 | 상담소 패널 = `textContent` 만 · 길이 상한(글 4,000자 · 넘으면 「…(나머지는 master 에게)」) | 새 `ui/src/counsel.ts` |

## 4. 시험 계획
- **ui 단위(bun test)**: `counsel.test.ts` — 정렬(내 글 최근 활동순 → 나머지 최신순 · 동시각 안정 정렬) · 댓글 트리(refs · 고아 댓글 = 원글 없음 → 맨 아래 「원글을 찾을 수 없는 댓글」) · 표식 벗기기(정확 일치만 · 흉내 표식 유지) · 상담소 답 판별(id 같고 지문 다름 = 거짓) · 빈/실패 문구 구분 · innerHTML 0(소스 grep 시험). `counselbadge.test.ts` — unread.json: 정상 · 없음(숨김) · 깨짐(직전 값) · `v:2`(직전 값 + 갱신 필요) · count 0/1/120(99+) · 부분 쓰기.
- **Rust 단위**: 핀 파서(주석·모르는 줄 버림) · 명부 지문 계산 · `on_navigation` 판정 표(https 허용 호스트 / http / 다른 호스트 / `agora.godmeyou.kr.evil.com` / 사용자정보 `@` / 포트) · 클라이언트 판 비교(0.1.4 < 0.1.14 · 0.1.9 vs 0.1.14 숫자 비교).
- **격리 하네스**: `AGORA_CONFIG_DIR=<임시>` + unread.json·desk-pin·allowed_signers·participant.json 픽스처 + 가짜 `lib/bin/agora`(고정 JSON 출력) → Rust 명령 왕복. 실 클라이언트 1회 = 0.1.14 사본으로 실 방 읽기(읽기만).
- **윈 동등성**: 설정 폴더 경로 해석(`%USERPROFILE%\.config\agora` · `AGORA_CONFIG_DIR` 우선) 단위 시험 · python 호출 = 기존 `python_command`+`hidden_command`(무콘솔) 재사용 · `incognito` = WebView2 InPrivate 【추정 · 윈 실기에서 1회 확인 = 10-16 키트 항목 추가】 · src-tauri 변경이므로 CI windows-build 녹 확인.
- **수동 1회(맥 실기)**: 상담소 패널(빈 방 상태 · 픽스처 글 3개 상태) · 뱃지 1/숨김 · 아고라 창에서 외부 링크 클릭 → 브라우저 · 캡처 = `docs/design/shots-119-t4/`.

## 5. 계수 · 2단계 예상
- 1단계 실소요: 1 화면 ≈10분 · 2 데이터 경로(실측 포함) ≈25분 · 3 보안 ≈10분 · 4 시험 ≈5분 = 【관측】 07:07 착수 → 07:13 문서 완성(date 출력) = 약 6분 · 위 항목별 분 = 【추정】 배분.
- 2단계 예상(같은 종류 = U4 앱 티켓 1판 2h · 10-07 실측): 메뉴 틀+상담소 패널+정렬 = U4 1판(2h) · 뱃지 = +0.5판 · 아고라 창(Rust 새 함수+시험) = +1판 · 합 **≈5h**(브리프 상한 4h 초과 → 【질문】 Q2 로 분할 여부 확인).

## 6. 코드 진입점(줄번호 = 9d8fff71 기준)
| 무엇 | 자리 | 할 일 |
|---|---|---|
| 사이드바 줄 2개 | `ui/index.html:51`(`#ws-tabs`) 과 `:54`(`#ws-usage`) 사이 | `#ws-counsel-row` 새 div · 버튼 `#btn-counsel`(+`<span class="badge" hidden>`) · `#btn-agora` · CSS = `ui/src/style.css:193·222` 옆(`[hidden]` 짝 규칙 = `hiddenpair.test.ts`) |
| 뱃지 그리기 선례 | `main.ts:4933-4940` `updatePendingBadges` · `index.html:28` `#cc-pending-badge` | 같은 꼴(`hidden = n===0` · `textContent`) |
| 상담소 패널 | `.modal-overlay` 꼴 = `main.ts:10372-10548` `openFeedbackModal`(재진입 가드 10371 · 닫기 10419 · `body.modal-open` 7790) | 새 순수 모듈 `ui/src/counsel.ts`(정렬·트리·표식 벗기기·문구) + 배선은 main.ts 한 함수 · ⚠ 피드백 모달은 `innerHTML` 로 틀을 짜지만 **남의 글은 textContent 로만** 넣는다 |
| 주기 폴링 | `main.ts:3082-3085`(사용량 패널 폴링 틱) | 45초 mtime 확인을 같은 틱에 얹음(새 타이머 0) |
| UI→Rust | `main.ts:289` `invoke` 래퍼 | `invoke("counsel_room_list")` · `invoke("counsel_unread")` · `invoke("open_agora_window")` |
| Rust 명령 등록 | `main.rs:7438` `generate_handler!` · 목록을 재는 시험 `:7959`·`:10241` | 3개 추가 + 두 시험 기대값 갱신 |
| python 호출 틀 | `main.rs:4618-4638` `resource_gate_check`(`python3` + `inject_runtime_path` 5219 + `no_console` 5164) | `counsel_room_list` 가 같은 꼴로 `<설정>/lib/bin/agora read …` · 비동기 = `spawn_blocking`(6670 선례) |
| 홈 경로 | `cys::home_dir()`(`main.rs:4506` 선례) | 설정 폴더 해석 함수 1개(`AGORA_CONFIG_DIR` → `home/.config/agora` · 윈 동일 식) |
| 외부 링크 | `main.rs:758-806` `url_host_allowed`·`host_in_allowlist`(ALLOW = notebooklm·github·cysinsight)·`open_url` | ⚠ `jarvis-install.godmeyou.kr`·`agora.godmeyou.kr` 가 ALLOW 밖 → 아고라 창의 「설치 안내」 링크가 **안 열린다**. 권고 = ALLOW 에 그 두 호스트 **정확 일치** 추가(하위 도메인 허용 꼴 `ends_with` 이므로 `godmeyou.kr` 통째 추가는 안 함) = 📌 Q4 |
| 아고라 창 | 없음(`WebviewWindowBuilder`·`on_navigation` 0 · `get_webview_window("main")` 7431 만) | 새 `fn open_agora_window`(이미 열려 있으면 `set_focus`) |
| capability | `src-tauri/capabilities/default.json` = `windows:["main"]` · `remote` 0 | **무변경**(이것이 IPC 경계) + 시험 1개가 그 사실을 잰다 |
| CSP | `tauri.conf.json:19-21` `"csp": null`(현재 꺼짐) | 이 티켓에서 켜지 않음(앱 전역 영향 · 범위 밖) — 상담소 패널 안전은 textContent 규율 + 소스 grep 시험으로 담보 · 아고라 창은 별개 웹뷰라 무관 |

## 7. 【질문】 · 범위 밖
- **Q1** 공개층 「내 글 새 댓글」 읽음을 앱에서 지우는 길이 없다(클라이언트 쓰기 동사 부재 · 앱 쓰기 금지 §11). 권고 = 1.1.9 앱은 읽음 처리 0(숫자는 master 경유로만 줄어듦) · 클라이언트 `agora counsel seen` 류는 다음 판.
- **Q2** 2단계 예상 ≈5h > 상한 4h. 권고 = 그대로 한 티켓(커밋 5개 단위라 중간 매듭 가능) · 아니면 아고라 창을 t4b 로 분리.
- **Q4** `open_url` ALLOW 에 `agora.godmeyou.kr`·`jarvis-install.godmeyou.kr` 정확 일치 2줄 추가(§6) — 없으면 아고라 창 안 외부 링크가 아무 반응 없음. 권고 = 추가(우리 도메인 · 하위 도메인 와일드카드 아님).
- **Q3** 이 맥(master 기기)의 클라이언트가 0.1.4 라 실기 캡처 전에 0.1.14 교체가 필요 — 교체는 팩 `ensure-client` 몫(이 티켓은 손대지 않음) · 캡처는 `AGORA_CONFIG_DIR=<임시 사본>` 으로 대신 가능.

### 7-1. ✅ master 판정(2026-10-09 07:13 · 설계 통과)
- **Q1 = 권고 채택**: 1.1.9 앱은 읽음 처리 0 · 패널 머리 「새 답이 N개 있어요 — 마스터에게 "상담소 답 보여줘"라고 말해 보세요.」 · 클라이언트 읽음 동사(seen 류) = **다음 판 백로그**.
- **Q2 = 한 티켓 유지** · 상한 5h · 커밋 단위마다 매듭(커밋 + HANDOFF §0) · CTX 60% 매듭 · 70% 전 순환.
- **Q3 = 채택**: 맥 실기 캡처는 `AGORA_CONFIG_DIR=<임시 사본(0.1.14)>` · 이 맥 설치본 교체는 손대지 않음.
- **Q4 = 채택**: `open_url` 허용 목록에 `agora.godmeyou.kr`·`jarvis-install.godmeyou.kr` **정확 일치 2줄**(하위 도메인 아님) · 시험에 위장 꼴(`….evil.com` · 하위 도메인 · 사용자정보 `@`) 포함.
- 추가: ⓐ 상담소 패널 문구 = 왕초보 말투 · 위협 표현 0(공개 문안 규칙) ⓑ 라벨·툴팁 = cysr 명명 정본(cys 는 코드 식별자만) — `counselwiring.test.ts` 가 잰다.
- 구현 메모(설계와 다른 점 · 이유): 문구의 「master」 → 화면 글자는 「마스터」(사이드바 기존 안내 「마스터에게 말로 부탁하세요」와 통일).
- 구현 메모 2(2단계 결과 · 상세 = `HANDOFF-T4-119.md` §2·§3): 뱃지 폴링 = 별도 45초 `setInterval`(설계 「사용량 틱에 얹기」 대신) · 창 정책 = `spawn_policy(Attached)` 직접(인구조사 판독) · `agora read` 는 `-I` 없이(PYTHONUTF8 보존) · 아고라 창 이동 허용에 `about:blank`·`about:srcdoc` · **실 앱 창 캡처는 미실시**(캡처 = 헤드리스 + 실 클라이언트 결과).
- 2판(codex 1R → master#6576ea7c): §2ⓒ 「그 밖 링크 = open_url 경유 기본 브라우저」 → **거부만 + 창 안 안내 1줄**(자동 전달 0) · §3 이동 허용에서 `about:` 제외 · python = `-I -B -X utf8` · 명부 = OpenSSH 패턴 의미론 — 상세 `HANDOFF-T4-119.md` §0-2.
