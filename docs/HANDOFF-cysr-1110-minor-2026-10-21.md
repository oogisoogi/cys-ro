# HANDOFF — TICKET=cysr-1110-minor (1.1.10 소형 결함 묶음)

- 가지: `fix/1110-minor` (기준 `fb386c49` = origin/main · v1.1.9+1) · 좌석 542(surface:1541 · worker-4) · 2026-10-21 21:5x ~
- 원칙대로 항목 1개 = 커밋 1개(+시험). 실패 시험을 먼저 쓰고 수리 전 빨강을 실측한 뒤 수리했다.
- push·태그·설치·발행 = 0.
- 근거 보고서 `REPORT-dbg119.md` 는 남아 있지 않다(1461 scratchpad 정리됨 · 검색 3경로 실측 0건). 그래서 ①②③ 은
  `cys recall` 로 남은 dbg119 요지 + **코드 직접 판독**으로 재구성했다. ⑥⑦ 근거 = master `SESSION_STATE.md` 580·581행 ·
  `relay-acct1/win-reply-20261008-*.md` 의 윈 실측 원문.

## 0. 한눈에

| # | 항목 | 커밋 | 분류 | 결과 |
|---|---|---|---|---|
| ① | `bash --rcfile /tmp/claude` 맨 셸 Occupied | `5854b952` | **수리** | 빈 값 유실 가드(R4 ③)를 셸 밖으로 한정 · 시험 1(수리 전 빨강) |
| ② | preflight 선택 도구 INFO 범위 | `da647639` | **수리** | INFO = 부재 행만 · 구버전·불완전·판독불가 = WARN · DRYRUN·SAFE-GAP 그대로 |
| ③ | 윈 `powershell -Command` 엔트리 판정 | `55b0be0d` | **판정만 · 윈 실기 필요** | 비대칭 확인 · 실해 좁음 · 현행 판독을 시험으로 고정(코드 변경 0) |
| ④ | `seat_claimable` 뮤텍스 선행 lock | `d71878e7` | **수리** | 판정표 순서로 조기 반환 · 순수 판정표 그대로 · 시험 1(수리 전 패닉) |
| ⑤ | `hdiutil detach` rc 무시 | `52e17c04` | **수리** | 1회 재시도 · 2회 실패 = 사유 실린 모듈 오류 · fake runner 단위 1 |
| ⑥ | 윈 runtime-seal 「추가 1」 `dlls-copied.exe` | `2725d587` | **수리 · 윈 실기 필요** | 옛 잔여가 **아니다**(post-install 표지) → 정리 규칙이 아니라 분리 보고 · 내용 대조로 좁힘 |
| ⑦ | dept-awakening-seed WARN 지속 | `a2688514` | **수리 · 윈 실기 필요** | 닫힌 부서의 팩 잔재를 재고 있었다 → 레지스트리에 없는 부서는 판정 제외(잔재는 detail 에 표기) |

뮤턴트(브리프 지정 ①④⑤ + 추가 ②⑥⑦) — 전부 빨강:

| # | 뮤턴트 | 결과 |
|---|---|---|
| ① | 수리 전 코드(`!shell &&` 없음) = 기준 실행 | `seat1110_shell_option_value_is_never_the_entry` FAILED(「셸 옵션 값을 엔트리로 읽었다: bash --rcfile /tmp/claude」) |
| ④ | 조기 반환(`if seat != Empty`) 제거 | `seat1110_claimable_answers_without_human_lock_when_seat_not_empty` FAILED(poisoned unwrap 패닉) |
| ⑤ | detach 사유 검사를 `if False:` 로 | `test_module_probe_detach_failure_is_retried_then_a_module_error` FAILED |
| ② | `or "불완전" in d` 제거 | `test_grade_table_only_absence_is_info` FAILED |
| ⑥ | 내용 대조를 `return True` 로 | `test_1110_dlls_copied_name_with_foreign_body_still_counts` FAILED |
| ⑦ | 수리 전 코드 = 기준 실행 | `diag_dept_awakening_seed_skips_closed_dept_remnant` FAILED |

②에서 뮤턴트 1개는 **살아남았다** — 처음 넣은 「DRYRUN·SAFE-GAP·BLOCKED 통과」 줄은 일반 규칙이 이미 같은 답을 내서 군더더기였다.
그 줄을 지우고(커밋 전) 실제 판별자(「불완전」)로 뮤턴트를 다시 잡았다.

## 1. 항목별

### ① `--rcfile` 값이 엔트리로 읽힘 — 수리
- 위치: `src/bin/cysd/governance.rs` `interpreter_entry`(값 받는 옵션 처리 뒤 `lost_empty_value` 가드).
- 원인: R4 ③ 가드(「값 자리 낱말이 후보 엔트리이고 뒤에 비옵션 낱말이 없으면 엔트리」)가 셸에도 섰다. `bash --rcfile /tmp/claude`
  의 `/tmp/claude` 는 후보 `claude` 실행 파일 규칙에 맞고 뒤가 비어 있으므로 엔트리로 골라졌다 → 맨 대화형 셸이 Occupied
  (승계 차단 · 빈 셸 가드 해제).
- 수리: 가드를 `!shell &&` 로 한정. 셸 값 옵션(`--rcfile` · `--init-file` · `-o`)의 값은 읽어 들일 파일·옵션 이름이지 실행할 엔트리가 아니다.
- 남는 같은 꼴(범위 밖 · 관측만): 인터프리터 `node --require /opt/pre/claude`(뒤 엔트리 없음 = REPL)도 가드가 값을 엔트리로 집는다.
  R4 ③ 이 의도한 「빈 인자 유실」 과 구별할 재료가 argv 에 없다 — 손대지 않았다.

### ② `_optional_tool_grade` INFO 범위 — 수리
- 위치: `cysjavis-pack/bin/javis_preflight.py` `_optional_tool_grade` · `c24_korean_law_mcp` 의 `cur` 문구.
- 원인: 마지막 줄이 가족(C19·C21·C24) 안의 비-ok 행을 **전부** 「선택 · 없음」 INFO 로 덮었다. 실측 경로:
  C24 구버전(`ver < KLAW_MIN_VERSION` → FAIL 「korean-law 0.x — 미비」) · C21 불완전 클론(「… 미설치 (기존 … 불완전 …)」) ·
  C24 판독불가(cli 있음·버전 없음 — 문구가 「미설치/판독불가」 한 칸이라 부재와 갈리지 않았다) · dry/safe 모드의 DRYRUN·SAFE-GAP.
- 수리: 부재 문구 머리표 `OPTIONAL_ABSENT_HEADS`(C19 `pack/bin 누락` · C21 `harness-creator 툴체인 미설치` · C24 `korean-law 미설치` ·
  공통 `비가역 변경(` = 부재일 때만 서는 설치 보류 행)에 맞고 「불완전」 이 없을 때만 INFO. 그 밖 = FAIL→WARN(C19 자기검증 실패와
  같은 규칙) · 다른 상태는 그대로(DRYRUN·SAFE-GAP·BLOCKED 포함). C24 `cur` 를 `미설치` / `판독불가` 로 가름(C20 의 같은 줄은 무변경).
- 기존 시험 정정 2곳: 등급표의 DRYRUN 기대값 INFO → DRYRUN · 고정 문구 「미설치/판독불가」 → 「미설치」(코드가 더는 그 문구를 내지 않는다).

### ③ 윈 `powershell -Command` — 판정만 · 윈 실기 필요
- 사실(코드): 윈 좌석은 명령이 있으면 `powershell.exe -Command <명령 문자열>` 로 뜬다(`state.rs` `windows_exec_flag` · `-Command`).
  `interpreter_entry` 의 셸 규칙은 POSIX 묶음 꼴이다 — `-` 뒤 글자에 소문자 `c` 가 있으면 명령 문자열(엔트리 없음),
  `o` 로 끝나면 다음 낱말이 값.
- 판정: `-Command` 는 소문자 `c` 가 없어 묶음으로 안 읽히고 **명령 문자열이 엔트리**가 된다 → 문자열 안 어느 낱말이든 후보면 뿌리 = 에이전트.
  맥 `zsh -lc "claude …"` 는 뿌리 ≠ 에이전트(자손으로만 잰다) — **플랫폼 비대칭**. PowerShell 의 같은 뜻 줄임 `-c` 는 반대 답(엔트리 없음).
  `-NoLogo` 는 `o` 로 끝나 다음 낱말을 값으로 삼킨다 · `-ExecutionPolicy` 는 `c` 가 있어 뒤를 통째로 버린다(우연히 맞거나 틀린다).
- 실해는 좁다: `-Command`(‑NoExit 없음) 셸은 명령이 끝나면 함께 끝나고, 도는 동안은 에이전트가 자손이라 어차피 Occupied 다.
  답이 갈리는 곳 = 명령이 에이전트가 아닌데 문자열에 후보 이름이 든 경우(`-Command "echo claude"`) · `-NoExit` 좌석의 에이전트 종료 뒤.
- 시험 `seat1110_windows_shell_root_readings_are_pinned` = 위 판독을 **현행 기대값**으로 고정(값이 바뀌면 판정을 다시 하라는 표식).
- 윈 실기에서 볼 것: 윈 좌석 뿌리의 실제 argv(`Get-CimInstance Win32_Process … CommandLine`) — 특히 launch-agent 좌석이 `-Command`
  로 뜨는지, `-NoExit` 가 붙는지. 그 판독 뒤 PowerShell 매개변수 표(대소문자 무시·접두 줄임·`-File` = 엔트리·`-Command`/`-EncodedCommand`
  = 엔트리 없음)로 고칠지 정한다.

### ④ `seat_claimable` 뮤텍스 — 수리
- 위치: `governance.rs` `seat_claimable`.
- 원인: `last_human_input.lock().unwrap()` 을 좌석 판정 **전에** 불렀다(단락 평가 소실) → Occupied·Unknown 좌석마다 불필요한 lock ·
  뮤텍스가 poisoned 면 답이 이미 정해진 좌석에서도 패닉.
- 수리: 좌석 → meta → 사람 입력 순서로 조기 반환. 매 갈래가 `seat_claimable_verdict` 를 거쳐 답한다(순수 판정표 그대로).
  배선 핀(`seat119_every_seat_probe_goes_through_the_single_verdict`)을 새 본문 꼴로 갱신.
- 남은 것(범위 밖 · 관측만): Empty 좌석에서의 `lock().unwrap()` 은 그대로다(같은 파일 다른 곳은 `unwrap_or_else(|e| e.into_inner())` 꼴도 쓴다).

### ⑤ `hdiutil detach` rc — 수리
- 위치: `scripts/tests/test_update_publish.py` `media_probe_failures`.
- 수리: detach 도 `hdiutil_retry` 경유(1회 재시도 · 사유 stderr) · 2회 실패 = 「hdiutil 매체 분리 실패」 사유 목록 → `setUpModule` 의
  모듈 오류(기존 전이 경로). 정리용 detach(`tearDown`·`addCleanup`)는 종전대로 — 배선 핀 주석만 정정.

### ⑥ 윈 runtime-seal 「추가 1건」 — 수리 · 윈 실기 필요
- 윈 실측(10-08~10-17 · doctor 5회 동일): `C:\Users\oogis\AppData\Local\cys\runtime\git\mingw64\libexec\git-core\dlls-copied.exe` ·
  Authenticode 정상 · 서명자 Git for Windows 유지자 · 06-30 생성.
- 판독: 「옛 Git for Windows 잔여」 가설은 **근거가 없다** — 동봉 PortableGit 은 윈 첫 도입 커밋 `5454a2f9`(07-01)부터 줄곧 2.55.0
  (`git log -S` 실측). 대신 **같은 판의 post-install 이 만드는 표지**다:
  - PortableGit-2.55.0-64-bit.7z.exe(sha256 `dfa8cad3…e928`) 목록에 `dlls-copied` 는 없고 `etc/post-install/13-copy-dlls.post`(06-30) 가 있다.
  - upstream `git-for-windows/build-extra` `portable/root/etc/post-install/13-copy-dlls.post`: `ln "$prefix_path/bin/git.exe" "$exec_path/dlls-copied"`
    (실패 시 `touch`) — `mingw64/bin/git.exe` 하드링크라 서명·시각이 git.exe 그대로인 것과 정합. MSYS `ln` 이 `.exe` 를 붙인 것으로 본다(윈 실측 이름).
  - 1.1.8 D11-b 가 이미 같은 post-install 산출물(`git/etc/hosts` 등)을 「런타임 관리 자리」 로 분리했다 — 이 파일만 목록에서 빠져 있었다.
- 수리(`javis_runtime_seal.py` `classify`): `dlls-copied`·`dlls-copied.exe` 가 **추가**이고 내용이 봉인된 `git/mingw64/bin/git.exe` 와 같거나
  빈 파일(touch 폴백)일 때만 `runtime_managed` 로 분리 보고. 이름만 같고 내용이 다르면 종전대로 「추가」(파손) — 그 자리에 놓인 임의
  실행 파일이 숨지 않는다. 그래서 「정리 규칙(지우기)」 은 만들지 않았다(지우면 다음 post-install 이 다시 만든다 · 비가역 삭제 경계).
- 윈 실기에서 볼 것: 새 설치 doctor runtime-seal = OK 이고 runtime_managed 목록에 그 파일이 뜨는지 · 실제 파일 sha256 = `mingw64\bin\git.exe` sha256.

### ⑦ dept-awakening-seed WARN — 수리 · 윈 실기 필요
- 윈 실측 원문: `pack-dept-dept-1: acctdir(C:\Users\oogis\.cys\claude) 각성 훅 미시드 — SessionStart←session-start.sh+UserPromptSubmit←role-bootstrap.sh`
  · 같은 기계 `depts.json` = `{}`(GUI 로 시험부를 닫음) · `~/.cys/pack-dept-dept-1` 잔존(닫기 때 무접촉).
- 원인(코드): `cys-dept down`(`down_dept`)은 묘비 + `cys hooks-prune --pack-dir <부서 팩>` + 레지스트리 제거만 하고 **팩 폴더는 남긴다**.
  `diag_dept_awakening_seed` 는 상태 폴더의 `pack-dept-*` 이름만으로 대상을 고른다(문서 주석은 「등록된 부서 팩」). 그래서 hooks-prune 이
  지운 바로 그 각성 훅을 닫힌 부서에 대해 「미시드」 로 매번 다시 올린다 — 고칠 방법이 없는 영구 WARN.
- 수리(`src/bin/cys.rs` `diag_dept_awakening_seed`): 레지스트리(`${CYS_DEPTS_JSON:-<상태 폴더>/depts.json}` · cys-dept `REG` 와 같은 자리)를
  **읽었고** 그 이름이 `depts` 에 없으면 판정 제외 — detail 에 「닫힌 부서 팩 잔재 N(판정 제외): …」 로 남긴다(침묵 아님).
  레지스트리를 못 읽으면(부재·파손) 종전대로 잰다(`DeptRegistration::Unknown` 과 같은 원칙 — 판정 불가는 닫힘의 근거가 아니다).
- 범위 밖으로 둔 결정(master): 닫을 때 팩 폴더를 남기는 것이 의도(격리 보관)인지 정리 누락인지(윈 보고 D19 후보) — 이 수리는 어느 쪽이든 맞다.
- 윈 실기에서 볼 것: 같은 기계 doctor 에서 dept-awakening-seed = OK · detail 에 `pack-dept-dept-1` 잔재 표기.

## 2. 시험 결과(이 가지 HEAD · 맥 · 2026-10-21 실측)

| 묶음 | 결과 |
|---|---|
| `cargo test -p cys-terminal` lib | **1077 / 0**(ignored 2) |
| 같은 실행 `--bin cys` | **613 / 0** |
| 같은 실행 `--bin cysd` | 2615 / **1** (ignored 8) — 아래 ⚠ |
| `test_update_publish`(전 모듈) | 108 OK · skip 14(맥 매체·REQUIRE_ALL 조건 = 기존) |
| `test_javis_counsel` | 76 OK |
| preflight 시험 15모듈(`test_preflight_*` · `test_boot_preflight_degraded`) | 전부 녹(`test_preflight_phase1_checks` 는 격리 env `JAVIS_ROOT`·`CYS_PROBE_RUNS` 를 주고 실행) |
| `test_runtime_seal` 22 · `test_preflight_c80_runtime_seal` 18 · `test_runtime_manifest_parity` 10 · pyseal census·specimen | 전부 녹 |
| `git diff fb386c49 --check` | 공백 오류 0 |

⚠ `--bin cysd` 의 1건 = `alert_route::drills::drill_edge_loop_clear_signals_are_never_held_by_the_hourly_cap`
(`alert_route.rs:4506` 「clear 개시 신호가 시간당 상한으로 보류됐다」). 이 가지는 `alert_route.rs` 를 건드리지 않았다(`git diff fb386c49 --stat` 0) ·
같은 시험 단독 3회 = 3/3 녹(17.5s·16.4s·11.0s). 전체 실행 때 기계 부하가 컸다(같은 lib 시험이 앞선 실행 390s → 이 실행 890s ·
동시 워커 빌드 2개). 부하 의존 흔들림으로 보지만 **원인 판독은 하지 않았다** — 기준 커밋에서의 부하 재현은 미실시.
`cargo test --workspace` 는 Tauri 앱(`cys-app`)의 빌드 스크립트가 프론트 산출물을 요구해 이 작업트리에서 돌지 않는다(시험 대상 아님).

Windows 실기 0 — ③⑥⑦ 은 윈 실기에서 각 절 「윈 실기에서 볼 것」 을 확인해야 해소다.

## 4. 겹침 목록(동시 티켓 cysr-1110-vendor · cysr-1110-winqueue 와 병합 시 확인)

- `src/bin/cysd/governance.rs`: `interpreter_entry` 1줄(가드 조건) · `seat_claimable` 본문 · 시험 모듈 `mod tests` 에 시험 3개 추가
  (`seat119r4_lost_empty_option_value_does_not_swallow_the_entry` 뒤) · 배선 핀 `seat119_every_seat_probe_goes_through_the_single_verdict` 의
  `seat_claimable` 단언 1개.
- `src/bin/cys.rs`: `diag_dept_awakening_seed` 본문 · 시험 1개(`diag_dept_awakening_seed_flags_unseeded_dept` 뒤).
- `cysjavis-pack/bin/javis_preflight.py`(`_optional_tool_grade` · C24 `cur` 1줄) · `cysjavis-pack/bin/javis_runtime_seal.py`(`classify` · 표지 상수) ·
  `scripts/tests/test_update_publish.py` · `cysjavis-pack/bin/tests/test_javis_counsel.py` · `cysjavis-pack/bin/tests/test_runtime_seal.py`.
