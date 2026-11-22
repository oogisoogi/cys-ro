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
- 고침(★1365534b1 ci-branch 적색 뒤 판): 부팅 요지 `MASTER_CORE.md`·`CEO_CORE.md` 의 대화 화면 표식 줄 바로 아래 1줄 —
  「먼저 한 줄(대화 화면 · 1.1.17): 도구를 여럿 쓸 일이면 쓰기 전에 무엇을 할지 한 줄을 먼저 쓴다(예 …)」. 마스터·CEO 좌석이 **부팅 때 실제로 읽는** 자리다.
- ⚠원문 `MASTER_DIRECTIVE.md` 에는 넣지 않는다: c5d16c6fd 판은 원문 「★ 대화 화면 표식」 절 끝에도 1줄(+291 B)을 넣었는데, 원문은 **바이트 상한 핀**
  (`test_cso_directive_rev.py::test_directive_byte_budget_ratchet` · 88,134 B · 「늘리지 말고 줄여라」)에 이미 꽉 차 있어 ci-branch(macOS·ubuntu 두 잡)가 붉었다
  (88,425 > 88,134 · run 45043208432 · macOS C8 두 단계 exit 2 = 앞 단계 중단으로 cysd-mac.log 미생성 뒤따름).
  원문 다른 글을 깎아 자리를 내는 것은 남의 규칙 뜻을 바꿀 위험 → 원문·CEO_TEMPLATE·발행 해시 표 3종을 기점(f1fe7aa91)과 바이트 일치로 되돌림.
  📌 원문에도 꼭 있어야 한다면 = 원문 어느 글을 줄일지 master 판정 필요.
- ★절은 요지 절 해시 대상 밖 → `test_core_inject` 절 해시 15절 대조 통과.
- 시험: `test_cso_directive_rev`·`test_bootv2_doc_contract`·`test_event_inject`·`test_core_inject`·`test_ceo_pending_gate` rc 0 · `gen_ceo_template.py --check` GREEN · `gen_released_directive_hashes.py --check` 0.
  로컬 팩 전체 루프 209종 중 10종 실패 = 기점 요지 파일로도 같은 10종 실패(크롬·phoenix·preflight 등 이 기기 HOME·데몬 상태를 타는 시험 · CI 우분투 레인에선 통과) = 환경성 · 내 변경 무관.

## ①-4 윈에서도 진행 줄 — 윈 open_bound 구현(판정 = 구현 포함)

### 원인(코드 판독 · 확신 높음)
- 진행 줄·「전달됨」·마스터 답 말풍선의 재료는 전부 결속 세션 기록인데, 윈은 `viewcore.rs open_bound` 가 `#[cfg(not(unix))] → Err("unsupported_platform")` 라 **한 번도 읽지 않았다**
  (codex 4R major 「경로 재탐색 대조는 바꿔치기를 못 막음」 때문에 미뤄 둔 조각 10). 그래서 윈 대화 화면은 「전달 확인 중 → 오래 걸려요」에 머물고 답도 안 보였다.
- 진행 줄만 윈에서 따로 만드는 길(데몬 화면 글 훑기 등)은 재료가 부정확해 버림 → 기록을 안전하게 여는 것이 유일한 길.

### 판정 = 구현 포함 · 설계(src/bound_open.rs · 본체 leaf) — ★codex 1R 뒤 판(아래 대조표)
- 방법 = **유닉스 판과 같은 결속(핸들 기준 상대 열기)**: ① 뿌리(설정 폴더 · 데몬 값 · 따라감 = 유닉스 판과 같음)를 폴더 핸들로 열어 끝까지 쥔다
  ② 상대 요소마다 `NtCreateFile(OBJECT_ATTRIBUTES.RootDirectory = 앞 핸들 · ObjectName = 그 요소 하나)` + `FILE_OPEN_REPARSE_POINT`(링크·접합 안 따름) ·
  중간 = `FILE_DIRECTORY_FILE` · 마지막 = `FILE_NON_DIRECTORY_FILE` ③ 연 요소마다 핸들 속성: reparse point = `symlinked_path`. 최종 경로 문자열 비교는 쓰지 않는다.
  공유 모드 = 읽기·쓰기·삭제(Claude Code 쓰기 안 막음). 상대 요소 검사 = 보통 이름만 · `:`·구분자·끝 점·공백 거부. NTSTATUS → 사유 = 유닉스 errno 대응과 같은 낱말
  (없음 = no_file · 중간이 파일 = symlinked_path(ENOTDIR) · 마지막이 폴더 = not_a_file).
- windows-sys 기능 2개 추가(`Wdk_Foundation` · `Wdk_Storage_FileSystem` · 같은 0.59 · Cargo.lock 무변). 본체에 둔 이유 = 윈 실기 레인(windows-health)은 본체 크레이트 시험만 돈다(cys-app 시험 0) → 윈도우 전용 검체를 실기로 돌리려면 본체여야 함.
- 배선: `viewcore.rs` `#[cfg(windows)] open_bound → cys::bound_open::open_file_under` · `transcript_supported() = cfg!(any(unix, windows))`(빠른 길 unsupported 는 그 밖 플랫폼만) ·
  윈 canonicalize 의 `\\?\` 접두를 걷어 두 번째 슬러그 후보를 만든다(`strip_verbatim`).
- transcriptNone 정합: 뜻 = 「이 좌석 기록을 못 연다는 사실」 그대로(30초 재조회) — 1.1.17 윈은 보통 ok(맥 꼴)라 거의 안 쓰이고, 세션 미등록·파일 없음·링크 거부 좌석과 1.1.16 윈에만 쓰인다(주석 갱신).
  heldwin.test 「win」 모형 = 기록 못 여는 좌석 회귀 시험으로 유지(초록).
- 윈 실기 시험 단계: `windows-health.yml` 에 `cargo_filter_count --lib bound_open::` + 실행(0건 = 적색 규율 그대로).
  윈도우 전용 검체 4 = 정상 파일 읽기·대소문자 다른 철자·사유 코드·쓰는 중 열기 · 중간 접합(mklink /J) 거부(경로로는 읽힘 = 대조군) · 파일 심볼릭 링크 거부(못 만들면 적색) ·
  **뿌리 바꿔치기**(뿌리 핸들을 쥔 뒤 이름 바꾸고 다른 폴더를 그 이름에 → 쥔 핸들로 연 파일 = 옛 뿌리 것). `win_tests::` 개수를 따로 세고(순수 시험이 0건을 가리지 않게)
  ci-branch FILTERED_CARGO_REQUIRED 에 `--lib bound_open::` 등재(실행 줄을 지우면 적색) · 로컬 레인 대조 스텝 재현 rc 0(필수 필터 13/13).

### 시험(맥)
- `cargo test --lib bound_open::` 2 passed(순수부 — 상대 요소·최종 경로 대조) · `cargo test -p cys-app --bin cys-app viewcore` 28 passed(strip_verbatim·transcript_supported 정합 포함)
- `scripts/win-typecheck.sh` = 오류 0(내 파일 경고 0) · ui `bun test` 3976 pass 0 fail · heldwin+progress 24/24 · tsc 0.
- **윈 실기 판정은 이 가지 push 의 windows-health 런에서** — 결과 sha·run 은 【확인요청】에 적는다.

### 정직한 한계 · 바깥 증거 요청
- 가정(확신 중상): 윈 Claude Code 프로젝트 폴더 이름 = 우리 슬러그(`C:\Users\x\p` → `C--Users-x-p`). 읽기 전용 측정(윈 마스터에게):
  `Get-ChildItem "$env:USERPROFILE\.claude\projects" -Directory | Select-Object -First 5 Name` → 이름이 `C--Users-…` 꼴이면 확정.
- 윈에서 기록 읽기가 살아나면 맥처럼 읽기마다 데몬 RPC 2개(surface.list·org.status)가 직렬 풀에 선다 — 상한은 chat-held-win ⓐ(관측 기반 500~2000ms)가 흡수 · 윈 실기 대화 화면 왕복 10회 전달률은 통합 빌드 시험 몫.
- 하드 링크는 유닉스 판과 같이 막지 않는다(유닉스 O_NOFOLLOW 도 못 막는 같은 축 · 같은 볼륨·그 파일 쓰기 권한 필요) — 📌 수용 여부 = master 판정(codex missing ④).
  ✅ master 판정(master#fe364353 · 11-23): **수용** — 읽기 전용 기록 읽기 · 하드 링크를 만들려면 이미 그 사용자 폴더에 쓰기 권한이 있어야 함 = 새 위험 경계 아님 · 두 OS 같은 축 유지.

## codex 1R(갈래 끝 1회 · d93c0b3cc 대상) — verdict BLOCK · 대조표
원문 = `~/axdev/workers/cysr-1118-ui/evidence/codex-1r-verdict.json`.

| # | 등급 | 지적 | 처리 | 근거·시험 |
|---|---|---|---|---|
| 1 | blocking | bound_open:87 뿌리 핸들을 닫고 경로로 다시 열어 뿌리 이름 바꿔치기 틈 | **고침** — 뿌리 핸들을 쥐고 요소마다 NtCreateFile(RootDirectory) | 윈 검체 `root_swapped_after_open_still_reads_old_root`(쥔 뒤 바꿔치기 → 옛 뿌리 파일) |
| 2 | blocking | bound_open:43 ASCII 대소문자 무시 최종 경로 비교가 대소문자 구분 형제 뿌리를 같다고 봄 | **고침** — 문자열 비교 제거(핸들 결속 · 찾기는 쥔 폴더 안에서만) | final_path_is 삭제 · 윈 검체 대소문자 다른 철자 = 같은 파일(쥔 뿌리 안) |
| 3 | major | 대상이 폴더면 BACKUP_SEMANTICS 없어 no_file(시험 기대 not_a_file 와 충돌) · 중간 파일 사유 불일치 | **고침** — NtCreateFile 상태 → 사유(FILE_IS_A_DIRECTORY = not_a_file · NOT_A_DIRECTORY = symlinked_path) | `status_reasons_match_unix_words`(맥) · 윈 검체 폴더·중간 파일 |
| 4 | major | viewcore:298 설명 없는 명령 원문 60자 노출 | **고침** — 설명만 · 없으면 단계 이름만 | Rust 시험 `TOKEN=secret run` → None · 명령 원문 0 |
| 5 | major | viewcore:301 URL 사용자·비밀번호 노출 | **고침** — url_host = 호스트 이름만(사용자·비번·포트·경로 0 · 꼴 아님 = 없음) | Rust 시험 `alice:secret@Example.com:8443` → example.com |
| 6 | major | progress:89 새 말 답함 뒤 옛 미응답 말이 다시 live | **고침** — 보낸 시각 가장 늦은 말이 기다릴 때만 live | progress.test 새 1건 — 고치기 전 판 1 fail → 고친 뒤 7/7 |
| 7 | major | bound_open:212 파일 링크 못 만들면 조용한 초록 · 순수 시험이 개수 채움 | **고침** — 못 만들면 적색 · `win_tests::` 개수 따로 · REQUIRED 등재 | windows-health 2줄 · 레인 대조 로컬 rc 0 |
| 8 | minor | chat/index:121 펼침 상태 집합 무한 증가 | **고침** — paint 때 없는 말 id 제거 | — |
| m1 | missing | 윈 실기 증거 | 이 커밋 push 의 windows-health 런 | 【확인요청】에 run·결과 |
| m2 | missing | accountShortLabel·acctKey 범위 밖 | 렌더 하네스 캡처·이메일 0 단언으로 대신(범위 밖 함수 무변) | evidence/statusboard |
| m3 | missing | 216px 렌더·타이머 해제 실측 | 216px = 헤드리스 6/6 · 타이머 = ctx.timers(화면 해제 때 함께 해제 = 기존 계약) | — |
| m4 | missing | 하드 링크 허용 근거 | 유닉스 판과 같은 축 · ✅ master 수용(master#fe364353) | 위 한계 절 |
