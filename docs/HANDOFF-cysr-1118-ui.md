# HANDOFF · TICKET=cysr-1118-ui (2026-11-23 · worker-3 · 갈래 A = ui)

가지 `feat/1118-ui` · 기점 `f1fe7aa91`(fix/chat-held-win 확정 머리 · master#10cb05f1) · 발행·태그·main 0.

## ② 상황판 계정 줄 (🗣박사님 11-22 19:4x 「이상하다. 계정도 하나밖에 안 보인다.」)

### 원인(코드 판독 · 확신 높음)
- `ui/src/statusboard.ts` `top7d()` 가 모든 계정의 7d 창 가운데 **가장 높은 값 하나**만 골라 `limitLine` 한 줄로 그렸다(설계 = 1g 「가장 높은 한도」).
  두 계정 값은 `usage_accounts_all` 로 이미 수집된다(이 기기 11-23 실측 `cys usage-accounts --json` = claude 계정 2개 · 7d 43 / 38) → 결함이 아니라 표시 설계.

### 설계
- 새 순수 함수 `accountLimitRows(accounts, nowSecs)` = 계정마다 7d 최고 한 줄 `{name, pct, line, title}`.
  - 거르기 = `accountRates` 와 같음(관측 전 `updated_at` 없음 · 7d 없음 = 빠짐).
  - 이름 = `usagebar.accountShortLabel`(별명 > 현재 로그인 폴더 > 제공자 · **이메일 0** — 사용량 칸과 같은 이름).
  - 차례 = 이름순(값이 바뀌어도 줄이 자리를 바꾸지 않음) · 같은 이름 = 「이름 2」.
  - 짧은 줄 = `43% · 금 06:00`(「초기화」 낱말·남은 시간은 툴팁 `title`).
- `paintBoard` 옵션 `accounts` — **둘 이상일 때만** 한도 단추 안을 계정마다 한 줄로(이름 · 「% · 요일 시각」). 하나면 종전 한 줄(막대 + `86% · 금 06:00 초기화`) 그대로.
  - 계정 줄에는 막대를 두지 않는다 — 막대를 두면 216px 설정 폭(실폭 199px)에서 「claude-acct2」가 「claude…」로 밀려 잘렸다(실측 캡처). 높은 값은 글자 색(막대와 같은 60·80 문턱).
  - 「% · 요일 시각」은 줄이지 않는다(flex none · 중간 잘림 0) · 이름만 아주 길 때(별명 24자) 말줄임 + 전문 툴팁.
- `main.ts` 배선 1줄(`accounts: accountLimitRows(accountsCache, nowSecs)`) · 누르면 펼침(사용량 칸) 동작 그대로.

### 시험
- `ui/src/statusboard.test.ts` 계정별 3건 추가 — 고치기 전 3 fail(함수 없음) / 고친 뒤 10/10.
- 렌더(헤드리스 크롬 · 실제 번들 + 대역 · 1920·1280 × 계정 1·2·3(긴 별명)) = 6/6 PASS: 글자 잘림 0 · 가로 넘침 0 · 이메일 0 · 콘솔 오류 0 · 계정 1 = 종전 한 줄 정규식 그대로.
  하네스·캡처 = `~/axdev/workers/cysr-1118-ui/evidence/statusboard/`(run.cjs · mk.py = `ui/e2e/statusboard_gate.py` 의 대역·탐침을 그대로 빌려 계정만 바꿈 · 파이썬 playwright 가 이 기기에 없어 node playwright 로 돌림).
- `bun test` 전체 3970 pass · 89 skip · 0 fail · `bunx tsc -p tsconfig.check.json` 오류 0.
- 해소 판정 중 「빌드 상황판 캡처」 = 위 헤드리스 캡처(`two-1280.png`) · 실기 앱 캡처는 통합 빌드에서 master 몫.

## ①-1·①-3 대화 화면 진행 줄 + 경과 시간 (🗣박사님 11-22 10:1x 「기다리는데 답답함」 · 10:2x 「요즘 LLM 처럼 생각 과정 · 실제 과정은 선택」)

### 원인(코드 판독 · 확신 높음)
- 대화 화면은 보낸 말의 **단계 이름**(전달 확인 중 · 전달됨 · 답하는 중 · 답함)만 그렸다. 마스터가 그 사이 무엇을 하는지(파일 읽기·명령·검색)는 세션 기록에 있는데
  `viewcore.rs parse_transcript_chunk` 가 글(`type:"text"`)만 뽑고 `tool_use` 는 버렸다 → 화면에 재료가 없었다. 경과 시간 표시도 없었다.

### 설계
- **Rust(viewcore.rs)**: assistant 레코드에 `tools: [{name, hint}]` · `thinking: bool` 추가(`tool_steps`·`tool_hint`). **입력 전문은 넘기지 않는다** —
  파일 = 마지막 이름 · 명령 = description 우선(없으면 첫 줄 60자) · Grep/Glob = 찾는 말 · 웹 = 검색어/호스트 · 도우미 = 설명 · 모르는 도구 = 이름만. user 레코드(도구 결과)엔 없음.
- **판정(judge/progress.ts · 순수)**: 레코드 → 단계(진행형 한 줄 · 단서 · 시각) · `applyRecords` 가 그 말의 사슬 위 마스터 레코드만 `msg.steps` 에 잇는다(상한 200 · 메모리만 = NFR-S3 · 저장소 0 시험).
  접힌 한 줄 = 「<마지막 단계> · <단서> · <경과>」(예 「파일 읽는 중 · core.ts · 12초」) · 단계가 아직 없으면 「<단계 이름> · <경과>」(예 「답하는 중 · 3초」) · 답 뒤엔 「과정 N단계」(접힘).
  생각 내용은 기록에 빈 칸이라 「생각하는 중」 표지만(11-22 실측 10/10 빈 칸).
- **화면(chat/index.ts)**: 보낸 말 말풍선 아래 진행 줄 · 누르면 「과정 보기」 목록(시각 HH:MM:SS · 단계 · 단서) · 경과 초는 1초 시계가 그 글만 바꿈(목록 다시 그리기 0 · 입력칸 보존).
- 갱신 박자 = 기존 세션 기록 읽기(보낸 뒤 +1·+3·+7초 · 일하는 동안 3초 조회마다 새 출력이 있으면) — 새 조회 0. 한 3초 창에 도구가 둘이면 머리줄은 뒤 것만(목록엔 둘 다).

### 시험
- `ui/src/views/progress.test.ts` 6건: 가짜 세션 기록 tool_use 3건 → 진행 줄 머리 3번 바뀜(「파일 읽는 중 · core.ts」→「찾는 중 · open_bound」→「명령 실행 중 · 시험 돌리기」) · 경과 초 1초마다 증가 · 답 뒤 「과정 4단계」 · 저장소에 단서 0.
  **대조군** = 같은 기록을 도구 칸 없는 옛 파서 꼴로(toolsField:false) → 도구 머리줄 0(고치기 전 동작). 기록을 못 읽는 자리(unknown)에서도 「전달 확인 중 · N초」.
- Rust `assistant_tool_use_becomes_short_steps_without_full_input` — 단서만 · 입력 전문(경로 앞부분·old_string·토큰·프롬프트) 0 · 윈 경로 마지막 이름 · `cargo test -p cys-app --bin cys-app viewcore` 27 passed.
- `bun test` 전체 3976 pass · 89 skip · 0 fail · tsc 0.

## ①-2 마스터 먼저 한 줄(팩 디렉티브)

- 원인: 진행 줄은 도구 단계를 보여 주지만 「무엇을 하려는지」는 마스터가 말해야 안다 · 지침에 그 규칙이 없었다.
- 고침: `MASTER_DIRECTIVE.md` 「★ 대화 화면 표식」 절 끝에 1줄 — 「도구를 여럿 쓸 일이면 도구를 쓰기 전에 무엇을 할지 한 줄을 먼저 쓴다(예 …)」.
  ★같은 뜻 1줄을 부팅 요지 `MASTER_CORE.md`·`CEO_CORE.md` 의 대화 화면 표식 줄 바로 아래에도 넣었다 — 그 절은 요지만 부팅 때 실리고 원문은 표식을 쓸 때만 읽으므로,
  원문에만 넣으면 매 답에 쓰일 규칙이 대부분 안 읽힌다(판단 · 범위 = 같은 1줄의 거울).
- 해시: ★절은 요지 절 해시 대상(§0-A~§14) 밖 → `test_core_inject` 절 해시 15절 대조 통과(요지 그대로 실림).
- 의무 3줄(메모리 pack-directive-edit-requires-regen-and-doc-contract): ⓐ `python3 scripts/gen_ceo_template.py` 재합성 + `--check` GREEN(103911 B) ⓑ `test_bootv2_doc_contract.py` rc 0 ⓒ `test_event_inject.py` rc 0(줄 범위 상수 무변 — 파일 끝에 붙여 줄 이동 0).
- 추가: `scripts/gen_released_directive_hashes.py` 재생성 + `--check` 0(안 하면 `released_tables_cover_current_embed` 적색) · `cargo test --lib pack::` 224 passed · `test_core_inject.py`·`test_ceo_pending_gate.py` rc 0.
- ⚠통합 주의: 생성물 2종(CEO_TEMPLATE.md · released 해시 표)은 다른 갈래가 디렉티브를 고치면 병합 뒤 다시 생성해야 한다(손 병합 금지).

## ①-4 윈에서도 진행 줄 — 윈 open_bound 구현(판정 = 구현 포함)

### 원인(코드 판독 · 확신 높음)
- 진행 줄·「전달됨」·마스터 답 말풍선의 재료는 전부 결속 세션 기록인데, 윈은 `viewcore.rs open_bound` 가 `#[cfg(not(unix))] → Err("unsupported_platform")` 라 **한 번도 읽지 않았다**
  (codex 4R major 「경로 재탐색 대조는 바꿔치기를 못 막음」 때문에 미뤄 둔 조각 10). 그래서 윈 대화 화면은 「전달 확인 중 → 오래 걸려요」에 머물고 답도 안 보였다.
- 진행 줄만 윈에서 따로 만드는 길(데몬 화면 글 훑기 등)은 재료가 부정확해 버림 → 기록을 안전하게 여는 것이 유일한 길.

### 판정 = 구현 포함 · 설계(src/bound_open.rs · 본체 leaf)
- 방법 = **연 핸들 자체를 대조**(경로 재탐색 0 → 확인·열기 사이 틈 0): ① 뿌리(설정 폴더 · 데몬 값 · 따라감 = 유닉스 판과 같음) 최종 경로
  ② 대상 파일을 `FILE_FLAG_OPEN_REPARSE_POINT` 로 열기(마지막 요소 링크·접합 안 따름) ③ 연 핸들 속성: reparse point = `symlinked_path` · 폴더 = `not_a_file`
  ④ 연 핸들 `GetFinalPathNameByHandleW` = 「뿌리 최종 경로 + 상대 요소」(ASCII 대소문자 무시) 아니면 `symlinked_path`(중간 접합·링크). 공유 모드 = 읽기·쓰기·삭제(Claude Code 쓰기 안 막음).
  상대 요소 검사 = 보통 이름만 · `:`(대체 스트림)·구분자·끝 점·공백 거부. 사유 코드 = 유닉스 판과 같은 낱말.
- 같은 방식 선례 = `src/update/win_install.rs`(최종 경로 대조). 본체에 둔 이유 = 윈 실기 레인(windows-health)은 본체 크레이트 시험만 돈다(cys-app 시험 0) → 윈도우 전용 검체를 실기로 돌리려면 본체여야 함.
- 배선: `viewcore.rs` `#[cfg(windows)] open_bound → cys::bound_open::open_file_under` · `transcript_supported() = cfg!(any(unix, windows))`(빠른 길 unsupported 는 그 밖 플랫폼만) ·
  윈 canonicalize 의 `\\?\` 접두를 걷어 두 번째 슬러그 후보를 만든다(`strip_verbatim`).
- transcriptNone 정합: 뜻 = 「이 좌석 기록을 못 연다는 사실」 그대로(30초 재조회) — 1.1.17 윈은 보통 ok(맥 꼴)라 거의 안 쓰이고, 세션 미등록·파일 없음·링크 거부 좌석과 1.1.16 윈에만 쓰인다(주석 갱신).
  heldwin.test 「win」 모형 = 기록 못 여는 좌석 회귀 시험으로 유지(초록).
- 윈 실기 시험 단계: `windows-health.yml` 에 `cargo_filter_count --lib bound_open::` + 실행(0건 = 적색 규율 그대로).
  윈도우 전용 검체 = 정상 파일 읽기 · 쓰는 중 열기(상대 쓰기 허용) · 중간 접합(mklink /J) 거부(경로로는 읽힘 = 대조군) · 파일 심볼릭 링크 거부(권한 있을 때 · 없으면 판정 불가 표시).

### 시험(맥)
- `cargo test --lib bound_open::` 2 passed(순수부 — 상대 요소·최종 경로 대조) · `cargo test -p cys-app --bin cys-app viewcore` 28 passed(strip_verbatim·transcript_supported 정합 포함)
- `scripts/win-typecheck.sh` = 오류 0(내 파일 경고 0) · ui `bun test` 3976 pass 0 fail · heldwin+progress 24/24 · tsc 0.
- **윈 실기 판정은 이 가지 push 의 windows-health 런에서** — 결과 sha·run 은 【확인요청】에 적는다.

### 정직한 한계 · 바깥 증거 요청
- 가정(확신 중상): 윈 Claude Code 프로젝트 폴더 이름 = 우리 슬러그(`C:\Users\x\p` → `C--Users-x-p`). 읽기 전용 측정(윈 마스터에게):
  `Get-ChildItem "$env:USERPROFILE\.claude\projects" -Directory | Select-Object -First 5 Name` → 이름이 `C--Users-…` 꼴이면 확정.
- 윈에서 기록 읽기가 살아나면 맥처럼 읽기마다 데몬 RPC 2개(surface.list·org.status)가 직렬 풀에 선다 — 상한은 chat-held-win ⓐ(관측 기반 500~2000ms)가 흡수 · 윈 실기 대화 화면 왕복 10회 전달률은 통합 빌드 시험 몫.
- 하드 링크는 유닉스 판과 같이 막지 않는다(최종 경로가 다른 이름으로 나오면 거부 = 안전 쪽).
