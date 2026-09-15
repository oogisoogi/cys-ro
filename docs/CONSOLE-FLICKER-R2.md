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

## 7. 한계(정직)
- 윈도우에서 창이 실제로 안 뜨는지는 이 브랜치에서 재지 않았다(맥 작업트리). 박사님 샌드박스 A/B(CYS_NO_OFFICE_BRIDGE=1) 결과가 주체 확정의 정본이다.
- 게이트는 정적 계수다 — 기존 원시 스폰의 윈도 도달 여부는 표 2 의 수동 분류에 기댄다.
