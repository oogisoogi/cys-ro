# 윈도우 콘솔 창 깜빡임 2차 — 스폰 주체 추적과 처방 (TICKET=cysr-console-flicker-r2)

작성 2026-09-15 · 브랜치 fix/console-flicker-r2 · base 8876204(cysr 1.0.0)

## 0. 증상과 이월
박사님 샌드박스(클린 Win11 · cysr 1.0.0 · 좌석 3자리 각성)에서 2분 폴링: `C:\Users\<u>\AppData\Local\cys\cys.exe` 가
약 2초 간격으로 새 pid 로 생성되고 매번 `conhost.exe` 가 함께 생겼다(23:14:04~23:16:00 약 50회 · powershell/python 새 프로세스 0).
부모 pid 는 샌드박스 WMI 차단으로 못 잡았다 — 그래서 이 문서의 주체 특정은 **코드 추적**이다.

## 1. 스폰 지점 전수 — cys.exe 를 낳는 곳 (코드 추적 · 맥에서 윈도 실행 불가)

| 호출자 | 대상 | 주기 | 1.0.0 숨김 플래그 | 비고 |
|---|---|---|---|---|
| 팩 `javis_hud_bridge.py` `fleet_loop` (cysd 가 자동 기동하는 오피스 브리지) | `cys fleet --json` + `cys status --json` | **2.0초**(FLEET_POLL_SECS) · 틱당 2회 · 접속 클라이언트 0 이어도 상시 | NOWIN(CREATE_NO_WINDOW) 있음 | **주기가 관측과 일치하는 유일한 경로** |
| 같은 파일 `SubscriptionSupervisor._reader` | `cys events --reconnect` | 장수 1회(죽으면 2→4→…60초 지수 백오프) | NOWIN 있음 | 상주 자식 |
| 같은 파일 `read_screen`·조작 지시 | `cys read-screen`·`send` | 요청 시 | NOWIN 있음 | |
| cysd `governance.rs` 노드 자동 재기동 | `cys node-recover` | 노드 비정상 종료 시(최대 3회) | hide_console | |
| cysd `schedule.rs::launch_via_cli` | `cys launch-agent` | 부재 역할 기동 시 | spawn_policy(Attached) | |
| cysd `main.rs` office-bridge 기동 | `python.exe javis_hud_bridge.py` | 60초 재확인·사망 시 | hide_console | 브리지 python 자체는 숨김 |
| 팩 주기 잡 6파일(9501dd6 처방) | cys.exe 등 | 매분·10분·일·주 | NOWIN(9501dd6) | 분 단위라 2초 주기 아님 |
| cys-app(Tauri) 사이드카 11곳(restore·skill run·onboard·drain·pack-update·launch-agent 등) | cys.exe | 사용자 조작·기동 1회 | no_console | 주기 폴링은 전부 RPC(스폰 없음) — UI 2초 타이머 `refreshHw` 는 `control.hw` RPC |

## 2. 숨김 없는 윈도 도달 스폰 (cys.exe 아님) — 1.0.1 에서 헬퍼로 편입

| 파일:함수 | 대상 | 주기 | 처방 |
|---|---|---|---|
| cysd `accounts.rs::run_capture` | curl(OAuth 사용량 프로브) | **주기**(콘솔 없는 cysd) | `cys::hidden_tokio_command` |
| cys `current_user_id` | whoami | `cys daemon install` | `cys::hidden_command` |
| cys `task_has_restart_on_failure` + daemon install/uninstall/status | schtasks ×4 | 설치·상태 조회 | `cys::hidden_command` |
| cys `pidfile_holder_dead` | tasklist | 부트 락 회수 판정 | `cys::hidden_command` |
| cys `which_in_path` | where | doctor·진단 | `cys::hidden_command` |
| cys-app `no_console`·`feedback.rs` | (원시 0x0800_0000 직접 적용) | — | 등급표 `ChildLifetime::Attached` 경유로 정의처 1곳화 |

## 3. 처방
1. **브리지 폴링 게이팅**(master#772c5ca1 범위 편입): `Hub.watched` 신호 — 접속 클라이언트 0 이면 `fleet_loop` 가 cys 를 **0회** 스폰하고 접속을 기다린다. 접속 즉시 한 바퀴 돌아 화면을 채우고, 마지막 접속이 끊기면 멈춘다.
2. **공통 헬퍼** `cys::hidden_command` / `cys::hidden_tokio_command`(lib.rs) — `Command::new` + `spawn_policy(ChildLifetime::Attached)`. flag word 의 정의처는 여전히 `ChildLifetime::win_creation_flags` 하나다.
3. **게이트**: `raw_command_new_census_is_frozen`(src/ + src-tauri/src 프로덕션 구간의 원시 `Command::new(` 파일별 동결 계수 — 새 원시 스폰이 생기면 적색) · `tauri_has_no_raw_creation_flags` · `hidden_command_helpers_and_windows_sites_are_wired`.

## 4. master 질의 ② 코드 확인 결과
- 브리지의 모든 스폰은 인자 배열 직접 실행이다 — `shell=True`·`cmd /c`·`os.system` 0건(grep 실측).
- 브리지 python 은 cysd 가 `hide_console()`(CREATE_NO_WINDOW)로 띄운다(main.rs spawn_office_bridge). 콘솔 서브시스템 python.exe 이지만 숨김 콘솔로 뜬다.
- pythonw.exe 로 바꾸는 안은 **채택하지 않았다**: pythonw 는 콘솔이 아예 없어, NOWIN 이 빠진 손자 스폰이 하나라도 생기면 오히려 그 자식마다 보이는 콘솔이 새로 할당된다(숨김 콘솔 상속이라는 현재의 한 겹 방어가 사라진다). 확신도 Med(윈도 실측 아님).
- ⇒ 코드상 「NOWIN 이 붙었는데 창이 뜨는」 기제는 찾지 못했다. 게이팅은 기제와 무관하게 2초 스폰 자체를 없앤다.

## 5. 판단 두 줄
- ⓒ cys 바이너리를 windows_subsystem="windows"+AttachConsole(ATTACH_PARENT_PROCESS) 로: 부모 콘솔 있는 터미널에서는 출력이 붙지만, 셸이 프롬프트를 먼저 돌려받아 출력이 프롬프트 뒤에 섞이고 `cys ... > file`·파이프 리다이렉션이 조용히 끊기는 알려진 위험이 있다(cys 는 스크립트·훅이 stdout 을 파싱하는 CLI) — 규모 = CLI 전 출력 경로 재검증 · 위험 높음 · 이번 판 실행 안 함.
- ⓓ 2초 주기 자체: 보는 사람이 있을 때의 오피스 화면 신선도에만 필요하다. 변화는 events 구독이 즉시 poke 로 밀어 주므로 2초는 보조다 — 게이팅으로 무인 스폰은 0이 됐고, 주기 5초 상향은 화면 품질 판단이라 이번에 바꾸지 않았다.

## 6. 검증
- Rust `cargo test --lib spawn_policy_tests` — 15 passed · 0 failed(신설 3건 포함). 첫 실행에서 신설 게이트 2건이 적색이었고
  (동결표 비어 있음 · 내가 쓴 주석의 원시 flag 리터럴 `0x0800_0000` 1건 적발) 두 가지를 고친 뒤 초록 — 게이트가 대상에 닿는다는 실측.
- 동결 계수 실측표(프로덕션 구간 원시 `Command::new(`): feedback.rs 2 · src-tauri main.rs 39 · app_bundle.rs 4 · cys.rs 15 ·
  accounts.rs 2 · boot_supervisor.rs 1 · channels.rs 2 · governance.rs 2 · hwmon.rs 3 · cysd main.rs 1 · schedule.rs 3 ·
  state.rs 3 · usage.rs 3 · factory_reset.rs 7 · launchd.rs 4 · lib.rs 6
  (agy 1R ③ 반영으로 검색어를 괄호 없는 `Command::new` 로 넓힌 뒤 재동결 — lib.rs 만 4→6, 헬퍼 설명 주석 2곳이 새로 잡힘. 주석도 세는 과탐 쪽 설계).
- 파이썬: 신규 `test_hud_bridge_unwatched_no_spawn` 3건 OK · 기존 `test_hud_bridge_backoff`(11)·`skew`(16)·`master_idle`(10)·`test_nowin_periodic_spawns`(2) 전부 OK.
- 파이썬 뮤턴트 4/4 KILLED(사본 트리에서 실행 · 원본 무접촉): M1 게이트 제거 · M2 detach 가 신호를 안 끔 · M3 attach 가 신호를 안 켬 · M4 클라이언트가 남아도 끔.
- CI 등재: 신규 파이썬 시험을 ci-branch·pack-release·release(2곳) 목록에 추가.
- 전체 `cargo test`(agy 1R 반영 전 트리) — lib 506 passed/1 ignored · cys 246 passed · cysd 960 passed/1 ignored · **실패 0**(FULL_RC=0).
- 재동결 후 `spawn_policy_tests` 15/15 초록.
- Rust 뮤턴트 5/5 KILLED(적용 선확인 → 기대 시험 적중 귀속 → 원복 sha256 대조 → 원복 후 15/15 재초록):
  R1 cys.rs whoami 를 원시 스폰으로 되돌림(wired+census 적중) · R2 헬퍼가 Attached 등급을 안 실음(wired) ·
  R3 feedback.rs 원시 creation_flags 복귀(tauri 원시 flag) · R4 accounts.rs 원시 tokio 스폰 복귀(census+wired) ·
  R5 Tauri no_console 이 아무 등급도 안 실음(tauri 원시 flag 시험의 등급 경유 핀).

### agy 1R — BLOCK (evidence 2) · 처리
| 지적 | 판정 | 처리 |
|---|---|---|
| ① 클라이언트 0 이면 fleet_loop 정지 → 구독 슈퍼바이저가 새 부서를 못 본다 | **반박(설계 유지)** | 구독 이벤트의 소비자는 SSE 클라이언트뿐이다 — 보는 사람이 없을 때 새 부서 구독이 늦는 것은 손실이 아니다. 접속 즉시 fleet_loop 가 한 바퀴 돌고 슈퍼바이저 reconcile(2초)이 따라온다. 「느린 백그라운드 폴링 유지」 안은 윈도에서 주기 cys.exe 스폰을 되살려 이 티켓의 목적(무인 스폰 0 · master#772c5ca1)과 정면 충돌한다. `main` 구독은 fleet 과 무관해 계속 돈다. 잔여 손실 = 무인 구간의 전광판 히트 누적 공백(화면 연출). |
| ② tauri_scan_files 단일 깊이 | 수용(예방) | 현재 src-tauri/src 하위 폴더 0 · 파일 2(실측)라 오늘의 공백은 아니나 재귀 수집으로 교체. |
| ③ `Command::new (` 공백 우회 | 부분 수용 | 검색어를 괄호 없는 `Command::new` 로 넓혀 재동결. `use … as C; C::new(` 같은 별칭 우회는 정적 계수의 천장으로 한계 §7 에 적는다. |
| 논쟁 — 둘째 클라이언트 접속 시 첫 프레임 지연 | 기각 | 첫 SSE 프레임은 현재 world 스냅샷을 즉시 보낸다(`_sse`) — 빈 화면이 아니다. |
| 논쟁 — 포그라운드 `cys daemon install` 의 whoami/schtasks 숨김 | 기각 | 전부 `.output()` 캡처라 사용자 출력 경로가 아니고, CREATE_NO_WINDOW 는 권한 상승(UAC)과 무관하다. |

## 6-2. master#1330e449 반영 — 결정적 증거(박사님 노트북 WMI 1분) 이후
- 확정 주체 ①: `cys.exe fleet --json`/`status --json` · 부모 = python3.exe(오피스 브리지) · 2~6초 간격.
  처방 = ⓐ 무인 게이팅(위 3-1) ⓑ cysd 가 브리지를 동봉 **pythonw.exe** 로 우선 스폰(`bundled_pythonw` · 없으면 종전 python3) —
  `cargo check --bin cysd` 통과. ⓒ 브리지의 subprocess 5곳은 NOWIN 유지(`test_nowin_periodic_spawns` 핀).
- 확정 주체 ②: 아고라 참가자 클라이언트(pythonw) → `powershell Get-Acl` — 별도 저장소(jarvis-agora-board) 별 커밋.
- 팩 전수: 「출력을 캡처하는 subprocess 호출은 창을 숨긴다」 규칙으로 213건 중 누락 188건(46파일)에 `**NOWIN` 편입.
  출력을 터미널로 흘리는 7건은 제외(숨기면 출력이 사라지고 pane 자식은 ConPTY 에서 떨어진다).
  ★편입 중 발견·수정: `javis_completion_guard._popen_group` 은 이미 `creationflags=CREATE_NEW_PROCESS_GROUP` 을 싣고 있어
  `**NOWIN` 병기가 윈도에서만 키 중복 TypeError 가 됐을 것 → 같은 칸에 OR 로 합쳤다.
- 규칙 게이트 `test_nowin_captured_spawns`(팩 전체 · 계수 하한 · `from subprocess import` 별칭 금지 · 셀프테스트) — CI 4목록 등재.
  뮤턴트 4/4 KILLED(사본 트리): P1 NOWIN 1곳 제거 · P2 정의 flag 값 변조 · P3 별칭 import 추가 · P4 숨김 없는 powershell check_output 추가.
- Tauri 크레이트 `cargo check` 통과(이 워크트리에 없는 ui/dist·사이드카·runtime 을 TAURI_CONFIG 덮어쓰기로 우회 — 코드 컴파일만 검증).
- 팩 시험 전수(83파일) 대조: 1차 기준선은 `cysjavis-pack` 만 떠낸 사본이라 저장소 전체를 읽는 시험 7건이 환경 탓으로
  적색이었다 → **대조 무효로 판정하고 폐기**. 편집 트리에서 적색이 남은 3건만 따로 쟀다:
  · `test_phoenix_e2e_replacement` — 단독 재실행 5/5 PASS(두 전수 실행이 동시에 돌던 간섭).
  · `test_preflight_phase1_checks` · `test_verify_gate` — 격리 env(JAVIS_ROOT·CYS_PROBE_RUNS) 부재로 거부(rc 2) →
    격리 env 로 재실행: 전자 24/24 OK(편집 트리·a587c7e 전체 사본 동일) · 후자 1/9 실패(`test_04_brief_paths` ·
    `'additionalContext' not found in ''`) — **a587c7e 전체 사본에서도 같은 케이스·같은 단언으로 실패 = 이 변경 이전부터**.
  ⇒ 이 변경으로 새로 생긴 팩 시험 실패 0.
- `javis_completion_guard --self-test`(격리 env) OK — 창 숨김 병합 뒤 그룹 스폰·taskkill 경로 포함.

### agy 2R — REVISE (evidence 3) · 처리
| 지적 | 판정 | 처리·근거 |
|---|---|---|
| ① `test_hud_bridge_unwatched_no_spawn` 가 attach 후 detach 누락 → tearDown 이 원본 run_json 을 되돌린 뒤 남은 daemon 스레드가 진짜 `cys` 를 스폰 | **수용** | tearDown 이 원본 복구 **전에** 모든 클라이언트를 떼고 watched 꺼짐을 단언 · 재실행 3/3 OK |
| ② pythonw 부재 시 python3 폴백이 숨김을 안 탄다 | 반박 | 폴백이든 아니든 같은 빌더다 — `main.rs:1677` `Command::new(&python)` 뒤 `main.rs:1699` `cmd.hide_console()` 가 무조건 걸린다(인터프리터 선택과 무관) |
| ③ `javis_preflight.py:2267` `start_new_session=True` 가 윈도에서 ValueError | 반박 | CPython 윈도 `_execute_child` 는 그 인자를 `unused_start_new_session` 으로 받아 **무시**한다(로컬 3.13 `subprocess.py:1461` · 3.14 `:1460` 실측). 동봉 3.12 소스는 이 기계에 없어 미실측(같은 서명으로 추정 · 확신 Med). 이 인자는 이번 변경 전부터 있었다 |
| 논쟁 — R1 반박(무인 스폰 0) 타당성 | 리뷰어 동의 | agy 2R 가 「R1 의 느린 폴링 요구는 기각이 맞다」고 판정 |

## 6-3. 주체 ② — 아고라 참가자 클라이언트의 PowerShell `Get-Acl` (별도 저장소 jarvis-agora)
- 작업 트리 ~/axdev/.wt/agora-acl-nowin2 · 브랜치 fix/acl-nowin-r2 · base 4582cb6(master#f15e8288·#d574408f 지정).
  (먼저 받은 board 트리 75d4fb8 에는 이 코드가 없어 재지정을 요청했다.)
- 왜 주기적인가: `participant.load()` 가 한 번 불릴 때마다 `_require_mode` → `_windows_acl_sids` 로 PowerShell 을
  **두 번**(설정 폴더·participant.json) 띄운다. `load()` 는 MCP 도구 호출(`tools.py`)·상주 방문(`resident` · 기본 10분 StartInterval)
  마다 돈다 — WMI 의 「23:38:02 2건」이 한 번의 load 와 맞는다.
- 처방(최소): `participant._hidden_window_kwargs()` — 윈도우에서만 `creationflags=CREATE_NO_WINDOW` +
  `STARTUPINFO(STARTF_USESHOWWINDOW · SW_HIDE)` · 타 OS 빈 dict. `Get-Acl` 의 `subprocess.run` 에 전개.
- 시험: selftest 케이스 「윈도우: Get-Acl 자식 창 숨김」(윈도 흉내로 실제 넘어간 인자를 잡아 flag·SW_HIDE 단언 · 비윈도 무변경 단언).
  뮤턴트: A1 flag 제거 · A2 SW_HIDE 제거 · A3 전개 제거 → 각 기대 단언으로 KILLED · A4 비윈도에서도 flag 부착 →
  단언 도달 전 AttributeError(비윈도 파이썬에 STARTUPINFO 없음)로 적색 — 크래시 킬(속성 위반이 맥에서 즉사로 드러남).
  ★첫 뮤턴트 실행에서 원본 케이스 자체가 적색이었다(헬퍼만 만들고 호출에 전개를 빠뜨림) — 원본 선확인 덕에 공허 킬을 버리고 수정 후 재측정.
- 같은 부류로 남은 아고라 스폰(이번 최소 처방 밖 · master 판단): `ssh-keygen`(sign.py·signer.py·keygen.py·roster.py) ·
  `git`/`gh`(store_github.py) · selfcheck.py — 출력 캡처형이며 pythonw 아래에서 불리면 같은 깜빡임이 날 수 있다.

## 7. 한계(정직)
- 기계적 편입은 맥에서 NOWIN 이 빈 dict 라 행동 무변경이고, 윈도 실행 검증은 없다 — 윈도에서 `**kw` 류 동적 전개와의 키 중복은 정적으로 1건만 찾았다(수정). 동적으로 creationflags 를 싣는 다른 경로가 있으면 윈도 CI 팩 시험이 잡는다.
- 윈도우에서 창이 실제로 안 뜨는지는 이 브랜치에서 재지 않았다(맥 작업트리). 박사님 샌드박스 A/B(CYS_NO_OFFICE_BRIDGE=1) 결과가 주체 확정의 정본이다.
- 게이트는 정적 계수다 — 기존 원시 스폰의 윈도 도달 여부는 표 2 의 수동 분류에 기댄다.
