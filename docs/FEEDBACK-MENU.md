# 사이드바 「피드백 보내기」 — 구현 보고서

TICKET=cys-feedback-menu · 2026-09-15 · 브랜치 `feat/feedback-menu`(base `rebase/v0.14.37` = 61d3082) · 9/21 판 트레인 대상.
짝 티켓 = feedback-webform(도움 서버 `POST /api/feedback`). 이 문서는 앱 층만 다룬다. 데몬·팩은 건드리지 않았다.

## 1. 사용자가 보는 것

> ⚠ **위치·글자 변경(TICKET=v116-feedback-top · 박사님 2026-09-26 00:2x·00:3x)**: 단추는 이제 사이드바가 아니라 **상단 메뉴바 맨 앞(「정렬」 바로 왼쪽)** 에 있고 글자는 **「피드백」** 이다(파란 테두리·옅은 파란 바탕으로 강조 · 크기는 상단 단추와 같음). 누르면 여는 창(제목 「피드백 보내기」·칸·안내)은 아래 그대로다. 아래 사이드바 서술은 2026-09-15 첫 판 기록이다.

- 사이드바에서 사용량 패널 아래, 원작자 표기 줄 바로 위에 「피드백 보내기」 버튼이 있다. 원작자 줄은 계속 사이드바 맨 아래 한 줄이다(원작자 시험 120/120 통과).
- 버튼을 누르면 창이 열린다. 칸은 다음과 같다.
  - 제목(필수 · 120자까지)
  - 내용(필수 · 5000자까지)
  - 연락처(선택 · 200자까지)
  - 「지금 화면을 캡처해 함께 보내기」 체크(맥에서만 보인다)
  - 「사진·영상 붙이기」(사진 5장·한 장 5MB · 영상 1개·95MB · 화면 캡처도 사진 5장 안에서 센다)
  - 고지 문안(서버 정본과 같은 글자)
- 체크를 켜면 창을 잠깐 가린 뒤 지금 화면을 찍는다. 사용자가 보던 화면을 보내려는 것이지 이 창을 보내려는 것이 아니기 때문이다. 체크를 끄면 찍은 사진을 뺀다. 체크의 기본값은 꺼짐이다.
- 보내기 결과는 셋 중 하나다.
  - 보냄: 창이 닫히고 「피드백을 보냈습니다」와 서버가 준 번호를 보여 준다. 올리지 못한 첨부가 있으면 그 이름과 이유를 함께 적는다(숨기지 않는다).
  - 보관: 네트워크가 없거나 서버가 잠시 받지 못하면 이 컴퓨터에 두었다가 앱이 자동으로 다시 보낸다고 알린다.
  - 거절: 제목 길이처럼 고쳐야 하는 문제는 창을 닫지 않고 이유를 보여 준다. 적은 글과 첨부는 그대로 남는다.

## 2. 서버 계약과의 대조(정본 = 도움 서버 `docs/HELP-API.md` §11-1~11-9 · master 전달 18:10·18:23 · 박사님 결정 18:11)

| 계약 항목 | 앱 구현 | 자리 |
|---|---|---|
| ① `POST /api/feedback` JSON · title·body·contact(선택)·notice_shown=true·source=app·app_version·os·client_key | 칸 이름은 `post_body` 한 함수에만 있다. 빈 연락처는 칸째 뺀다. | `src-tauri/src/feedback.rs` `post_body` |
| 같은 client_key 재전송 = 같은 번호(200) + 새 upload_token · 60분 뒤면 `upload_token: null` (§11-2) | 보관함 meta 에 client_key 를 한 번 만들어 두고 재시도마다 같은 값을 보낸다. 토큰이 null 로 오면 남은 파일을 「올릴 수 있는 시간이 지났습니다」로 빼고 글만 보낸 것으로 끝낸다(재시도하지 않는다). | `seal` · `process` |
| ② `PUT /api/feedback/<id>/files?kind=&filename=` · 헤더 `x-feedback-upload` · content-length · 본문 = 파일 바이트 | `curl -T`(길이 자동)로 한 건씩 흘려 보낸다. 토큰은 argv 가 아니라 `-K` 설정 파일로 넘기고 바로 지운다. 파일 이름·kind 는 퍼센트 인코딩한다. | `Curl::put_file` · `put_url` |
| 접수 뒤 60분 창(410 upload_window_closed) | 처음 접수된 시각부터 센다. 창이 지난 파일은 시도하지 않고 「보내지 못한 첨부」로 알린다. 글은 그대로 보낸다. | `process` |
| 재시도 규칙 §11-8: 201·200 끝 / 400·401·404·409·410·411·413·415·429 file_cap·507 = 다시 안 보냄 / 429 rate_limited·5xx·네트워크 = 다시 보냄(POST 는 같은 client_key · PUT 은 그 파일 한 건만) | 표 그대로(시험이 상태 번호 전부를 잰다). 다만 본문이 읽히지 않는 429(앞단이 막은 경우)는 다시 보낸다 — 버리면 일시 제한 한 번에 피드백이 사라진다(판단 1건). | `classify` |
| 한도 §11-3: 사진 5,242,880바이트×5 · 영상 95,000,000바이트×1 · 딱 그 크기는 받는다 · 캡처는 사진 안 | 창(`feedback.ts`)과 보관함(`feedback.rs`) 두 곳이 서버와 같은 바이트 값으로 막는다(경계값 통과·1바이트 초과 거절을 시험이 잰다). 두 곳의 숫자는 시험 `limits_match_ui_module` 이 글자로 대조한다. | 두 파일 머리 상수 |
| 고지 정본(박사님 확정 · 보존 90일) | 상수 1곳 `FEEDBACK_NOTICE_TEXT`. 시험은 구현 상수를 import 하지 않고 정본 글을 따로 적어 대조한다. | `ui/src/feedback.ts` |

## 3. 구조

- `ui/src/feedback.ts`: 순수 로직(글자 수를 코드 포인트로 세기 · 형식 판별 · 한도 · 결과 문구 · 고지 상수). 시험 `ui/src/feedback.test.ts`.
- `ui/src/main.ts`: 창 DOM 배선만 한다. 기존 `.modal` 틀을 재사용했다. 켜고 30초 뒤 한 번, 그 뒤 10분마다 `feedback_flush` 로 보관함을 비운다.
- `ui/index.html` · `ui/src/style.css`: 버튼 한 줄과 창 스타일. 글자 크기 축은 사이드바 공통 `--wsbar-font` 를 따른다.
- `src-tauri/src/feedback.rs`(신규): Tauri 명령 7종(`feedback_new_draft`·`feedback_stage_file`·`feedback_unstage`·`feedback_discard`·`feedback_capture`·`feedback_submit`·`feedback_flush`), 보관함, curl 전송, 화면 캡처. `main.rs` 에는 `mod feedback;` 과 명령 등록 7줄만 더했다.
- 첨부 바이트는 JSON(base64)이 아닌 원시 본문 IPC(`tauri::ipc::Request` · `InvokeBody::Raw`)로 받는다. 95MB 영상이 base64 로 33% 부풀지 않게 하기 위해서다.
- 보관함 = `~/.cys/feedback-outbox/<번호>/`. `meta.json` 이 없으면 초안(첨부만 쌓임), 있으면 보낼 건이다. 보냄·거절이 확정되면 폴더를 지운다. 보낸 사진·화면 캡처를 이 컴퓨터에 남기지 않는다.
  - 다시 보내기 간격은 60초에서 두 배씩 늘고 6시간이 상한이다.
  - 30일 넘게 못 보낸 건은 지운다.
  - 하루 넘게 방치된 초안은 지운다.
- UI 가 넘기는 초안 번호는 폴더 이름이 되므로 16~40자 소문자 16진수만 받는다(`../` 같은 경로 조각 차단).
- 창에서 보내기와 뒤에서 다시 보내기는 한 줄로 세운다. 뒤쪽은 앞이 돌고 있으면 그 틱을 건너뛴다.
- HTTP 클라이언트 크레이트를 새로 넣지 않았다. 사용량 기능(74269d9)과 같은 관례로 `curl` 자식 프로세스를 쓴다. 윈도우는 `curl.exe`(윈도우 10 1803 이후 기본 포함)에 CREATE_NO_WINDOW 를 붙인다.

## 4. 검증 결과 (전부 실행해서 확인한 값 · 코드 커밋 2904cda)

| 게이트 | 결과 | 비고 |
|---|---|---|
| 기존 Rust 스위트 전건 | `cargo test --workspace` 종료코드 0 · 121 + 492 + 244 + 959 통과 · 실패 0 | 사진 한도 값·null 토큰 수리 **전** 판에서 전체를 돌렸다. 수리 뒤 판은 아래 뮤턴트 대조군(`feedback::` 15건 통과)과 스모크로 다시 쟀다. |
| 기존 UI 스위트 전건 | `bun test` 834 통과 · 실패 0 | 새 시험 포함 |
| UI typecheck | 신규 오류 0 | base 61d3082 을 `git archive` 로 뜬 사본과 오류 목록을 대조했다(양쪽 모두 기존 `updateplan.test.ts` toMatch 1건뿐). |
| 원작자 표기 시험 | `test_default_fleet_formation.py` 120/120 | `#ws-credit` 이 사이드바 맨 아래 그대로 |
| 새 시험 | Rust 15건(+ 로컬 스모크 1건 · 평소 무시) · UI 18건 | 목표 ≥5 |
| 뮤턴트 | UI 5/5 · Rust 6/6 잡힘 | 목표 ≥4. 변이마다 찾을 글이 정확히 1회인지 먼저 확인했고, 변이 없는 대조군이 초록인 것을 먼저 확인했다. 어느 시험이 잡았는지를 이름으로 귀속했다. Rust 는 제자리 변이 뒤 원문 sha 일치를 확인했다. |
| 실제 curl 왕복 | 통과 | 계약 흉내 로컬 서버(127.0.0.1)로: POST JSON 칸이 정확 · `x-feedback-upload` 토큰 일치 · 한글·`&`·공백 파일 이름이 서버에서 원문 그대로 복원 · 첫 PUT 을 503 으로 막으면 재시도로 떨어지고 다음 시도에서 같은 토큰으로 그 사진부터 이어 올린 뒤 영상까지 올림 · 끝나면 보관함 폴더 삭제. 시험 동안 실제 보관함 `~/.cys/feedback-outbox` 는 생기지 않았다. 흉내 서버는 끝난 뒤 프로세스 그룹째 내렸다. |
| agy 1R | verdict ACCEPT · 지적 0건 | 정본 = `~/.cys/pack/round/_reviews/cys_앱_사이드바_피드백_창_…-r1-reviewer1.json`(18:34 · 의뢰문 18:31 뒤). 대상 = 커밋 2904cda diff 전문을 의뢰문에 붙였다(팀 내부 코드 리뷰 형식 · 웹검색·스킬 금지). ⚠지적 0건이라 파일:라인 근거가 붙은 항목이 없다 — 「결함 없음」의 증거로는 약하다. 실제 결함 1건(null 토큰 무한 재시도)은 리뷰가 아니라 정본 계약 재독에서 잡혔다. 반박·토론이 필요한 항목이 없어 2R 은 열지 않았다. |
| 맥 로컬 빌드 | 성공 · `target/release/bundle/macos/cys.app`(0.14.37 · 1.0G) · `cys-local` 서명(앱·cysd 모두 Authority=cys-local) · `codesign --verify --deep --strict` 통과 | 저장소 루트에서 `precompile-bundled-python.sh` → `tauri build --bundles app`(업데이터 산출물 끔 · Apple 자격 env 해제). 서명 **전에** 새 코드가 실렸는지 대조했다: 번들 cysd = target/release/cysd = src-tauri/binaries 사이드카 sha 일치 · `ui/dist` 에 `ws-feedback`·`feedback_new_draft` 있음 · dist 가 앱 바이너리보다 먼저 만들어짐 · 앱 바이너리에 `feedback-outbox`·`x-feedback-upload` 글자 있음. 설치하지 않았다(`/Applications/cys.app` 수정 시각 09:01 그대로). 번들 파이썬 런타임은 내려받지 않고 같은 커밋의 원 체크아웃 사본을 APFS 복제로 썼다(외부 호출 0). |

뮤턴트 목록(무엇을 깨뜨렸고 무엇이 잡았나):

| 번호 | 변이 | 잡은 시험 |
|---|---|---|
| U1 | 고지 문안 90일 → 30일 | 서버 정본과 글자 그대로 같다 · 보존 기간 90일을 말한다 |
| U2 | 사진 장수 경계 `>=` → `>` | 화면 캡처를 포함해 사진 5장에서 막는다 |
| U3 | 글자 수를 UTF-16 길이로 | 이모지 한 개는 한 글자 |
| U4 | 거절을 성공으로(창이 닫힘) | 거절 = 창을 닫지 않는다 |
| U5 | 빠진 첨부를 보냄 글에서 숨김 | 보냄이어도 빠진 첨부는 숨기지 않는다 |
| R1 | 429 를 본문과 무관하게 전부 버림 | classify_follows_contract_retry_table · network_failure_keeps_folder_and_retry_reuses_client_key |
| R2 | 초안 번호 경로 검사 제거 | draft_id_rejects_path_pieces |
| R3 | 보낸 뒤 폴더를 안 지움 | sent_path_posts_then_puts_each_file_and_removes_folder · late_resend_with_null_token_finishes_without_files |
| R4 | 영상 한도를 Rust 쪽만 바꿈(드리프트) | limits_match_ui_module |
| R5 | 토큰이 있어도 매번 다시 접수 | network_failure_keeps_folder_and_retry_reuses_client_key · file_cap_and_window_drop_files_but_text_still_sends |
| R6 | null 토큰을 빈 토큰으로 받아 PUT 시도 | late_resend_with_null_token_finishes_without_files |

정본을 읽다 찾은 우리 결함 1건(수리함): 60분이 지난 뒤 같은 client_key 로 다시 접수하면 서버는 200 과 `upload_token: null` 을 준다. 초판은 이것을 「응답 이상」으로 보고 재시도해 같은 답을 영원히 받았을 것이다. 지금은 남은 파일을 「올릴 수 있는 시간이 지났습니다」로 빼고 글은 보낸 것으로 끝낸다(시험 late_resend_with_null_token_finishes_without_files · 뮤턴트 R6).

## 5. 한계와 미결

- 화면 캡처는 맥만 된다(`/usr/sbin/screencapture -x`, 주 모니터). 윈도우는 체크 칸을 숨긴다. 윈도우 캡처는 이 티켓 안에서 실행해 볼 수 없어 넣지 않았다.
- 맥에서 cys 앱에 화면 기록 권한이 없으면 macOS 가 권한을 묻는다. 거부된 상태에서는 바탕화면만 찍힐 수 있고, 앱은 그것을 구별하지 못한다. 첫 실기 확인이 필요하다.
- 고지 문안은 「앱이나 설치 도우미에서 보내면 설치 번호와 판본도 함께 갑니다」라고 말한다. 앱은 판본은 보내지만 설치 번호(install_id)는 보내지 않는다. 앱이 설치 번호를 어디서 읽어야 하는지 정해진 곳이 없어서다. 문안이 실제보다 조금 더 말하는 방향이다(덜 말하는 것이 아님). 설치 번호를 싣는다면 원천을 정하는 결정이 필요하다.
- 윈도우 판은 빌드·실행하지 않았다(티켓 범위 = 맥 로컬 빌드). 원시 본문 IPC · `curl.exe` 경로는 윈도우 실기 확인 전이다.
- 서버가 아직 배포 전이라 실서버 왕복은 하지 않았다. 대신 계약을 흉내 낸 로컬 서버로 실제 curl 왕복을 확인했다(4절).
