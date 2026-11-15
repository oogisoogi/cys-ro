# 상담소 안내문을 실제로 보내는 칸에 맞춤 · TICKET=cysr-counsel-notice

> 2026-11-12 · worker-2(surface:2013) · 가지 `fix/1115-counsel-notice` ← `fix/1115-smalls` d604dd9d
> 박사님 결정 원문 = 「7번 권고대로 한다.」 → 안내를 사실대로 고친다 · **보내는 칸은 늘리지도 줄이지도 않았다**.
> 커밋 = ①~④ `8599d13b` · 보고서 · ② 「cysr를 켜 둔 시간」(master#2ba289f5 결정) · ⑤(뗄 수 있음 · **가지 맨 끝 커밋** · 해시는 인박스 【확인요청 2】). push·태그·발행 0 · 실제 전송 0(시험은 127.0.0.1 가짜 받는 곳).

## 0. 바뀐 안내문 (팩·화면·사용 설명서 같은 글자)

옛 글:
> cysr는 문제를 빨리 찾아 고치기 위해 하루 한 번 판번·운영체제·오류 횟수만 개발팀에 보냅니다(이름·파일·대화 내용은 보내지 않습니다). 끄려면 ‘상담소 끄기’를 누르세요.

새 글:
> cysr는 문제를 빨리 찾아 고치기 위해 하루 한 번 기기 상태(판 번호·운영체제·좌석 수와 종류·부서 수·cysr를 켜 둔 시간)와 오류 기록(횟수·종류·생긴 시각·점검 결과와 항목 이름)을 개발팀에 보냅니다. 기기를 구분하는 무작위 번호가 함께 갑니다(사람 이름·파일·대화 내용은 보내지 않습니다). 끄려면 ‘상담소 끄기’를 누르세요.

master 기본안에서 고친 곳 5군데와 그 근거(코드):

| 기본안 | 새 글 | 왜 고쳤나 (근거) |
|---|---|---|
| 좌석과 부서 수 | 좌석 수와 종류 · 부서 수 | 일일 보고에 좌석 **종류**(master·cso·worker·pack 범주)도 간다 — `probe_seats` 반환 `{"count", "roles"}` `javis_counsel.py:411` · 범주 접기 `:381-392` |
| 오류 기록(횟수·종류·점검 항목 이름) | 오류 기록(횟수·종류·**생긴 시각**·점검 **결과와** 항목 이름) | 신호마다 처음·마지막 시각이 간다(`first_seen`·`last_seen` `:1222-1225`) · 점검은 이름만이 아니라 통과·경고·실패·건너뜀 **개수**도 간다(`:432`) |
| (이름·파일·대화 내용은 보내지 않습니다) | (**사람** 이름·파일·대화 내용은 …) | 같은 글이 「점검 항목 **이름**」을 보낸다고 적으므로, 「이름은 안 보낸다」가 왕초보에게 모순으로 읽힌다. 실제로 막히는 것은 사람·계정 이름이다 |
| 켜 둔 시간 | **cysr를** 켜 둔 시간 | 재는 값은 컴퓨터가 아니라 cysr 데몬이 켜진 뒤의 시간이다(`probe_uptime` `:536-546` · 재료 `src/bin/cysd/delivery.rs:877`) — 컴퓨터 사용 시간으로 읽히지 않게(master#2ba289f5 결정 ②) |
| 판 번호 | 판 번호(그대로) | 앱 판(`version.host`)과 팩 판(`version.pack`) 둘 다 간다(`:373`·`:377`) — 둘 다 「판 번호」로 묶었다 |

「만」 같은 한정어는 쓰지 않았다(시험이 「만 」 글자를 막는다 — 아래 3절).

## 1. 보내는 칸 전수 표 (코드에서 다시 만듦)

보내는 곳 = `help_report` 하나(`javis_counsel.py:1298-1360`) · 받는 곳 `POST <CYS_FEEDBACK_BASE>/api/report` · 하루 최대 2통(신호 1 · 일일 1). 시험이 실제로 보낸 본문의 잎 칸을 모아 이 표(코드 `HELP_SENT_FIELDS` `:1080-1113`)와 **글자 그대로** 맞춘다.

### 1-a. 두 통 공통 칸 (`base` `:1319` · `kind` `:1325`·`:1345`)

| 칸 | 값 | 안내문 속 말 | 근거 |
|---|---|---|---|
| `kind` | `signal`·`daily` | (형식 칸 · 정보 아님) | `:1325`·`:1345` |
| `install_id` | 갱신기가 만든 무작위 16진 32자 | 기기를 구분하는 무작위 번호 | `read_install_id` `:1133` · 꼴 `INSTALL_ID_RE` `:1070` · 생성 `src/update/buildinfo.rs:172` `random_hex128()` |
| `day` | 보낸 날짜(KST 06:00 경계) | 하루 한 번 | `:1319` |
| `installer_version` | 앱 판 번호(없으면 null) | 판 번호 | `_host_version` `:1290` |
| `os` | `mac`·`win`·null | 운영체제 | `_help_os` `:1238` |

### 1-b. 신호 통 `payload.items[]` (`signal_items` `:1212-1226` · 줄 걸러내기 `_signal_rows` `:1202`)

| 칸 | 값 | 안내문 속 말 |
|---|---|---|
| `signature` | 아래 source·op·error_code·version 을 줄인 32자(`signal_signature` `:1179`) | 종류 |
| `count` | 그 묶음 횟수 | 횟수 |
| `source` | 범주 master·worker·cso·pack·update | 종류 |
| `op` | 동작 이름(예 `hook.session-start`) — 꼴 `OP_RE` `:55` | 종류 |
| `error_code` | 오류 이름(예 `hook.rc1`) — 꼴 `ERROR_CODE_RE` `:56` | 종류 |
| `version` | 팩 판 번호 — `VERSION_RE` `:57` | 판 번호 |
| `os` | `macos-15.1` 꼴 — `OS_RE` `:58` | 운영체제 |
| `first_seen`·`last_seen` | 처음·마지막 생긴 시각 | 생긴 시각 |

### 1-c. 일일 통 `payload` (`daily_body` `:1228-1235` ← facts `collect_facts` `:555-574`)

| 칸 | 값 | 안내문 속 말 | 재는 곳 |
|---|---|---|---|
| `version.host`·`version.pack` | 앱 판 · 팩 판 | 판 번호 | `probe_version` `:365-378` |
| `os` | `macos-15.1` 꼴 | 운영체제 | `os_tag` `:564` |
| `seats.count`·`seats.roles[]` | 켜진 좌석 수 · 범주(원 이름 아님) | 좌석 수와 종류 | `probe_seats` `:394-411` |
| `doctor.ok`·`warn`·`fail`·`skip` | 자가 점검 결과 개수 | 점검 결과와 항목 이름 | `probe_doctor` `:418-442` |
| `doctor.warn_ids[]`·`fail_ids[]` | 경고·실패 점검 이름(코드에 박힌 고정 이름 — `src/bin/cys.rs:9442` `name: &'static str`) | 점검 결과와 항목 이름 | `:438-441` |
| `depts.active`·`depts.tombstones` | 지금 부서 수 · 닫은 부서 수 | 부서 수 | `probe_depts` `:527-533` |
| `uptime.last_boot`·`uptime.uptime_s` | cysr 데몬이 켜진 시각 · 켜 둔 초 | cysr를 켜 둔 시간 | `probe_uptime` `:536-546`(재료 = 데몬 기동 표식 `src/bin/cysd/delivery.rs:877`) |
| `errors.tick_errors`·`errors.hook_rc_nonzero` | 오류 줄 수 | 횟수 | `probe_errors` `:495-502` |
| `errors.signatures[]` | 같은 날 보낸 신호 서명 | 종류 | `:1233-1234` |

facts 의 `cutoff`·`since`·`nonce` 는 **보내지 않는다**(`daily_body` 가 고르지 않음 · 기존 시험 `test_sends_signal_then_daily_with_closed_shape`).

### 1-d. 참가자 기기 경로 — **확인 못 함**
`participant.json` 이 있는 기기(아고라 가입)는 팩이 보내지 않고 아고라 클라이언트가 보낸다(`help_report` `:1306` 「agora」). 그 클라이언트 소스는 저장소에 압축본으로만 있어 칸·안내 게이트를 확인하지 않았다. 이 안내문은 팩 help 경로 기준이다.

### 1-e. 조사 문서(`INVESTIGATE-counsel-consent.md` ①)와 다른 점
조사 문서는 일일 보고의 추가 칸을 「좌석 수·부서 수·가동 시간·자가진단 경고 항목 이름」으로 적었다. 코드 대조 결과 그 밖에 **좌석 종류(범주)·점검 결과 개수·실패 항목 이름(경고만이 아님)·닫은 부서 수·팩 판 번호·데몬 켜진 시각·신호 서명 목록**이 더 있다. 신호 쪽 「훅/동작 이름·오류 코드·처음/마지막 시각」은 맞고, 그 밖에 **범주(source)·팩 판·운영체제 판·횟수·서명**이 더 있다. 조사 문서의 줄 번호는 이번 수정으로 밀렸다(예: `daily_body` 1187 → 1228).

## 2. 고친 자리 (저장소 안 · 형제 grep 전수)

`git grep` 「오류 횟수만」·「판번·운영체제」 결과 전부:

| 자리 | 처리 |
|---|---|
| `cysjavis-pack/bin/javis_counsel.py:1072` HELP_NOTICE | 고침 |
| `cysjavis-pack/bin/javis_counsel.py:20-22` 머리 도움말 | 고침(시험이 같은 문장인지 본다) |
| `ui/src/counsel.ts:40` REPORT_NOTICE | 고침 — 첫 안내 창(`main.ts:12313`)·상담소 창(`main.ts:12247`·`:12289`) 둘 다 이 값 |
| `USER-MANUAL.md:178` | 고침 |
| `docs/release-1110/RELEASE-NOTES-1.1.10.draft.md:53` | **안 고침** — 1.1.10 이 실제로 띄운 글의 기록이다. 고치면 과거 판이 무엇을 보였는지가 거짓이 된다. 1.1.15 릴리스 노트(아직 없음 · `docs/` 에 release-1115 없음)에 한 줄 넣을 것을 권함 |
| `docs/release-1110/evidence/MAC-VISUAL-1.1.10.md:27` | 안 고침 — 1.1.10 화면 증거 기록 |
| `docs/1115/INVESTIGATE-counsel-consent.md` | 안 고침 — 조사 당시 관측 기록(이 보고서 1-e 가 차이를 적음) |

영어·다른 언어 문구 자리: 없음(`README.en.md`·`README.md`·`ARCHITECTURE-AND-PHILOSOPHY.md`·팩 문서에 상담소 안내 문장 0 · 화면 문구는 한국어만).
팩 디렉티브: 해당 문장 없음 → 손대지 않음.

## 3. 시험 · 뮤턴트

### 3-a. 새 시험
- `test_notice_covers_every_sent_field_and_nothing_else`(`test_javis_counsel.py:2146`) — 가짜 받는 곳에 신호·일일 두 통을 실제로 보내게 하고 ① 보낸 본문의 잎 칸 전부 = `HELP_SENT_FIELDS` 열쇠(하나라도 더 보내거나 덜 보내면 적) ② 표의 말이 안내문에 글자로 있다 ③ 안내문 괄호 속 9항목 각각에 실제 칸이 있다(안 보내는 것을 보낸다고 쓰지 않는다) ④ 「만 」 한정어 없음.
- `test_names_files_and_talk_never_reach_the_wire`(`:2170`) — 좌석 이름(`worker-홍길동`·`hong-gildong-imac`)·좌석 줄 끝 경로·제목(`/Users/<지어낸 이름 hong-gildong>/secret.txt`·「안녕하세요 대화」)·점검 이름(경로·한글)·신호 칸 6가지(op 경로·한글 오류 코드·모르는 source·대화 판번·경로 os)를 심고 실제 `facts` 명령 → help 를 돌린다. 나간 본문에 심은 글자 0 · 좌석 = `{"count":3,"roles":["master","pack","worker"]}` · 점검 이름 = `["hook"]` 만 · 형식 안 신호 줄 1개만. (이 시험은 「막는다」의 증거이지 증명이 아니다 — 아래 5절.)
- 화면 쪽 `counselwiring.test.ts:120` — 팩 HELP_NOTICE 의 문자열 조각을 개수와 관계없이 모아(2 → 4조각) 화면 REPORT_NOTICE 와 글자 그대로 대조.
- ⑤ `test_old_notice_viewers_see_the_fixed_notice_once_without_pausing_sends`(`:2298`).

### 3-b. 뮤턴트 (각각 되돌림 확인 `cmp` 일치)
| # | 바꾼 것 | 결과 |
|---|---|---|
| M1 | `daily_body` 가 `since` 칸을 하나 더 보냄 | **적** — `AssertionError: Lists differ … 'payload.since'` (보낸 칸과 안내 대조표가 다르다) |
| M2 | 안내문에서 「생긴 시각」을 뺌 | **적** — `AssertionError: '생긴 시각' not found in '…'` (대조표의 말이 안내문에 없다) |
| M3 | 화면 REPORT_NOTICE 에 띄어쓰기 1칸 추가 | **적** — bun `(fail) 상담소 끄기/켜기 · 첫 안내 > 안내문 = 팩 HELP_NOTICE 와 글자 그대로…` · 19 pass 1 fail |
| M5a | ⑤ 보내기 게이트를 판에 묶음(`notice_seen_version < NOTICE_VERSION` 이면 notice-pending) | **적** — 다시 띄우기 전인데 보내기 게이트가 닫혔다 |
| M5b | ⑤ needs_notice 를 「안 본 기기」로만 | **적** — `needs_notice: False != True` |

### 3-c. 전체 실행 (종료 코드·건수 그대로)
- `python3 -m unittest tests.test_javis_counsel`(cysjavis-pack/bin) — ①~④ 커밋 뒤 `Ran 117 tests · OK (skipped=3)` · ⑤ 커밋 뒤 `Ran 118 tests · OK (skipped=3)` · rc 0. (pytest 는 이 기계 python3.14 에 없음 → unittest.)
- `bun test`(ui) — `3329 pass · 88 skip · 0 fail · 3417 tests / 105 files`.
- `bunx tsc -p tsconfig.check.json` — **rc 1 · 오류 8건 전부 `src/main.ts`**(TS2307 모듈 못 찾음 3 · 그 여파 TS7006 5). 이 작업트리에 `ui/node_modules` 가 없어서다(`ls ui/node_modules` = 없음). 이번에 고친 파일(`counsel.ts`·`counselwiring.test.ts`) 오류 0 · `main.ts` 는 이번 가지에서 안 고쳤다. ⚠node_modules 있는 곳에서의 깨끗한 tsc 는 **확인 못 함** — master 스냅샷 재검증 때 같이 봐 주시길.
- 팩 manifest·표식: `javis_counsel.py` 를 바꾼 과거 커밋들도 manifest 갱신이 없었고(`git log` 15건 대조) 저장소 안 json/manifest 에 이 파일 지문이 없음 → 해당 절차 없음으로 판단.

## 4. 화면 실측 (헤드리스 · 박사님 화면·앱 무접촉)

앱 `ui/src/style.css` + 실제 창 구조(첫 안내 = `confirmModal` · 상담소 창 = `openCounselPanel`)를 그대로 옮긴 정적 페이지를 헤드리스 크롬으로 3크기 렌더 · 글 칸의 `scrollHeight` 대 `clientHeight` 와 창이 화면 안에 드는지 잼.

| 창 | 1280×820(앱 기본 `tauri.conf.json`) | 800×600 | 480×400 |
|---|---|---|---|
| 첫 안내 | 잘림 없음(83/83px) · 화면 안 | 잘림 없음 · 화면 안 | 잘림 없음 · 화면 안 |
| 상담소 창 | 잘림 없음(54/54px) · 화면 안 | 잘림 없음 · 화면 안 | 잘림 없음(72/72px) · 화면 안 |

「cysr를」 3자를 넣은 뒤 다시 잼(2026-11-12 07:0x) — 6칸 모두 같은 값(첫 안내 83/83px · 상담소 창 54/54px · 480×400 상담소 창 72/72px) · 잘림 0 · 화면 안. 캡처는 다시 잰 판으로 바꿨다.
캡처: `docs/1115/counsel-notice-evidence/notice-confirm-1280x820.png` · `notice-confirm-480x400.png` · `notice-panel-480x400.png`. 첫 안내 글 칸은 `max-height:52vh` + 넘치면 스크롤이라 더 작은 창에서도 잘리지 않고 스크롤로 보인다(글이 사라지지는 않음). 윈도우 실기 글꼴로는 재지 않았다.

## 5. ⑤ 옛 안내를 본 기존 사용자에게 한 번 더 (별도 커밋 · 가지 맨 끝)

- `NOTICE_VERSION = 2`(`:1363`) · 표식 파일에 `notice_version` 칸 · 칸 없는 1.1.10 표식 = 1 · 꼴 밖 = 1(다시 띄우는 쪽).
- `auto-status` 의 `needs_notice` = 켬 ∧ 가입 없음 ∧ 본 판 < 2(`:1407`) → 앱의 기존 확인(시작 5초 뒤 · 30분마다 · `main.ts:12325-12326`)이 그대로 고친 안내를 띄운다. **화면 코드 무수정.**
- 다시 띄우는 동안 **보내기는 막지 않는다**(master 기본안) — 보내기 게이트 `notice-pending`(`:1307-1308`)은 「아무 판이든 본 적 있음」 그대로. 다르게 해야 할 이유는 코드에서 보지 못했다 → 【결정필요】 없음.
- 사용 설명서에 한 줄(`USER-MANUAL.md` 「안내 글이 바뀌면 … 한 번 더 뜹니다」) — 이 줄도 ⑤ 커밋에 넣어 함께 떼어진다.
- 떼기 확인: ⑤ 가 가지 맨 끝 커밋이라 `git revert <⑤>` 또는 `HEAD~1` 로 떼어진다 · `git show <⑤> | git apply -R --check` = 깨끗(다시 올린 뒤 재확인).

## 6. 저장소 밖 같은 문장 (고치지 않음 · 목록만)

`~/axdev` 읽기 전용 grep(「오류 횟수만」 · node_modules·.wt·.git·target 제외):

| 자리 | 성격 |
|---|---|
| `ai-jarvis/web-install/src/page.ts:97` | 설치 사이트 화면 문구(공개) |
| `ai-jarvis/web-install/test/fleet.test.ts:572` | 위 문구의 시험 기대값 |
| `ai-jarvis/web-install/docs/HELP-API.md:1036` | 받는 쪽 API 문서 |
| `ai-jarvis/web/dist/index.html:103` | 강의/소개 사이트 빌드본(공개) |
| `ai-jarvis/web/dist/devlog/index.html:109` · `ai-jarvis/site/devlog/index.html:134` | 개발 일지 |
| `ai-jarvis/web/dist/notice/2026-10-23/index.html:74` · `ai-jarvis/site/notice/2026-10-23/index.html:74` | 10-23 날짜 공지(과거 기록 성격) |
| `terminal-ide-survey/2026-11-bench/precheck/raw/pilot-rota-snapshot/pack*/…/javis_counsel.py` 4곳 | 옛 팩 스냅샷(조사 자료) |
| `master/…` 브리프·보고 7곳 | master 기록 |

설치본 `~/.cys/pack` 은 새 판 설치 때 바뀌므로 목록에서 뺐다.

## 7. 확인 못 한 것 · 한계

1. 참가자(아고라 가입) 기기의 보내는 칸·안내 — 1-d.
2. 「사람 이름·파일·대화 내용은 보내지 않습니다」의 근거는 **칸 꼴 제한**(ASCII 소문자·숫자·`.-_` · 경로 구분자 `/`·`\` 불가 · 한글 불가 · 좌석 이름은 범주로 접음 · 점검 이름은 코드 고정값)이다. 앞으로 누가 영문 소문자 사용자 이름을 `op`·`error_code` 로 넣는 코드를 쓰면 꼴은 통과한다 — 지금 그런 호출자는 확인하지 않았다(신호를 쓰는 호출자 전수 대조는 이번 범위 밖).
3. ~~「켜 둔 시간」의 대상~~ — 해소: master#2ba289f5 결정으로 「cysr를 켜 둔 시간」으로 좁혔다(컴퓨터가 아니라 cysr 데몬이 켜진 뒤의 시간).
4. node_modules 있는 환경의 tsc — 3-c.
5. 윈도우 실기 글꼴 렌더.

## 8. 1.1.15 릴리스 노트 한 줄 초안 (master#2ba289f5 ④)

> 상담소 안내 글을 실제로 보내는 내용에 맞게 고쳤습니다. 보내는 항목은 그대로이고, 안내 글만 사실대로 바꿨습니다 — 판 번호·운영체제·좌석 수와 종류·부서 수·cysr를 켜 둔 시간과 오류 기록(횟수·종류·생긴 시각·점검 결과와 항목 이름), 기기를 구분하는 무작위 번호를 하루 한 번 보냅니다(사람 이름·파일·대화 내용은 보내지 않습니다). 예전 안내를 보신 분께는 고친 안내가 한 번 더 뜹니다. 끄려면 상담소 창의 ‘상담소 끄기’를 누르세요.

(마지막 「한 번 더 뜹니다」 문장은 ⑤ 커밋에 기대는 말이다 — ⑤ 를 빼면 이 문장도 뺀다.)
