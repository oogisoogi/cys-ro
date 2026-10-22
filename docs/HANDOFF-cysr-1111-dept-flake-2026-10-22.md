# HANDOFF · TICKET=cysr-1111-dept-flake · 2026-10-22 · worker-3(surface:1577)

가지 `fix/1111-dept-flake` ← `8a37d3e2` · worktree `~/cys-terminal-src-wt/1111-deptflake`.
바뀐 파일 = **시험 1개**(`cysjavis-pack/bin/tests/test_dept_create_progress.py`) · 운영 코드(`cys-dept`·Rust) 변경 0.

## 1. 증상 (CI 원문)

- ci-branch run `39707938057` **1회차**(attempt 1) · job `macos-rust-pack`(id 119592276555) 적 · 2회차 녹(같은 sha `3ce93329`).
- `test_dept_create_progress` 의 `AllocateStages.test_new_spawn_order_and_contract` 1건만 FAIL(105건 중):

```
[cys-dept] @stage spawn
[cys-dept] @stage wait
[cys-dept] 부서 데몬(pid 78153)이 기동 중 종료했다 — 진행 신호: lock=0 files=1 ver=0 sock=0
[cys-dept] ERROR: dept-1 데몬 기동 실패
```

- 시각: 시험 모듈 시작 02:04:22.11 → 이 건 FAIL 22.77 = 시작 0.65초 안에 판정(관측).
- 원문 전체: `gh run view 39707938057 --attempt 1 --log-failed`(8791줄 · 작업 중 scratch 에 저장해 읽었다).

## 2. 원인 (확정 — 강제 재현 + 대조군)

**한 줄**: 시험의 목 cysd 가 소켓 파일을 만들자마자 끝나는데, 우리 `boot_wait` 는 한 반복에서 「핑 → `kill -0 pid`」 순으로 두 번 본다. 목의 「소켓 생성 → 종료」가
그 두 관측 사이에 끼면(핑은 생성 전 · `kill -0` 은 종료 후) 성공해야 할 경로가 「기동 중 종료」로 뒤집힌다.

- `cys-dept:1284` `boot_wait`: `alive "$s" && return 0` → `kill -0 "$pid"` 실패면 「기동 중 종료」.
- 시험의 목 cysd(수리 전): `mkdir` → `touch "$CYS_SOCKET"` → `exit 0`. 목 cys 의 `ping` 은 「소켓 파일 실존」으로 성공한다.
  `STUB_PING_OK_FROM=130`(UP_AT_PING) 은 옛 `ready_wait`(120회) 시절의 설계라, `boot_wait` 아래에서는 성공이 사실상 **소켓 파일 실존**으로만 온다.
- 실측 타임라인(계측 하네스 · 1회 · 녹이었던 실행): 스폰 뒤 첫 핑 898.960 시작 → 899.620 「소켓 없음」 판정 / 목 cysd 899.411 시작 → 899.618 대기 끝 → 소켓 생성 → 899.695 종료.
  핑의 「없음」 관측과 목의 종료 사이 간격 = **75ms**. 이번엔 `kill -0` 이 그 안에 들어가 녹이었다 — 부하·느린 러너에서는 순서가 뒤집힐 수 있다.
- 운영 코드 결함이 아닌 근거: 실 cysd 는 준비(소켓 응답) 뒤 스스로 끝나지 않는다 — Rust 코드에 `fork`·`daemon(` 0건(`git grep -E "libc::fork|nix::unistd::fork|daemon\("` = 무관한 함수 이름만) ·
  스폰은 `nohup cysd`(또는 setsid 파이썬 → exec) = pid 불변. 실 데몬이 준비 직후 죽으면 「실패」 보고가 맞다.
- 부기(관측): macOS 에서 좀비 프로세스에도 `kill -0` 은 성공한다(실측 `kill0=ok` · `ps stat=Z`). `boot_wait` 의 사망 감지는 부모 bash 가 자식을 거둔 뒤에야 보인다 — 이번 원인과 별개 · 동작 무해.

### 강제 재현 (핸드셰이크 · 고정 지연 없음)

하네스 = 시험 모듈을 import 해 목 문자열만 바꾸고 대상 1건을 돈다(시험 파일 무수정). 주입 지점은 수리 전후 공통 줄(`  ping)` 머리 · 목 cysd 의 `mkdir` 줄)뿐.

- 목 cysd(주입): 자기 pid 를 남기고, 핑이 「소켓 없음」 을 확인했다는 표식이 생길 때까지 소켓을 안 만든다.
- 목 cys ping(주입 · 첫 1회): 소켓이 없고 목이 떠 있으면 표식을 세우고, 그 목이 끝날(좀비/사라짐) 때까지 기다린 뒤 실패를 반환 = 「이 핑의 관측은 소켓 생성 전이었다」.

| 실행 | 결과 |
|---|---|
| 수리 전 · 주입 | **5/5 적** — 문구가 CI 원문과 같다: `진행 신호: lock=0 files=1 ver=0 sock=0` |
| 수리 전 · 대조군(주입 없음) | 5/5 녹 |
| 수리 후 · 주입 | **5/5 녹** |
| 수리 후 · 대조군 | 3/3 녹 |
| 뮤턴트(수리본에서 목 cysd 의 「응답 관측까지 대기」 1줄만 삭제) · 주입 | **5/5 적**(같은 문구) |

- 고정 지연(목 0.1초 · 핑 실패 0.5초)으로는 재현되지 않았다(3/3 녹) — 목의 기동 자체가 0.4초+ 늦어 순서가 안 뒤집혔다. 그래서 핸드셰이크로 바꿨다.
- ⚠ 계측 중 내 실수 2회: 목의 `exit 0` 을 통째 치환해 `dead` 판정 줄까지 바뀌어 목이 무조건 즉시 끝났다(소켓·pid 파일 0이 증거) — 그 두 결과는 버렸고 위 표에 없다.

### 자연 재현 시도 (부하)

- CPU 부하(코어 수 16개 바쁜 루프 · load ≈22) 아래 대상 1건 30회 → **적 0**. 이 맥에서는 부하만으로 안 뒤집혔다(관측 · 러너 조건은 재현 못 함).
- 부하 생성기는 30회 뒤 스스로 끝남(자기 자식 pid 로 SIGKILL) · **부하 생성기 잔존 0** 실측(`while True: pass` 프로세스 0 · load 22 → 5.9).

## 3. 수리 (시험 파일만)

`test_dept_create_progress.py` 목 2개:

- **목 cysd**(`#!/bin/sh` → `#!/bin/bash`): 소켓 파일을 만든 뒤 **핑 목이 응답 성공을 알릴 때까지**(`@STATE@/answered.<소켓키>`) 살아 있다(상한 1000회 × 0.01초 ·
  `command -p sleep` = PATH 선두의 no-op `sleep` 목을 비켜 간다). 시작 때 자기 pid 를 `@STATE@/cysd.<소켓키>` 에 남기고 묵은 `answered` 표식을 지운다(번호 재사용 시 즉시 종료 재발 차단).
- **목 cys**: 핑 성공 두 갈래(`STUB_PING_OK_FROM` 도달 · 소켓 파일 실존)가 `answered` 를 거친다 — 표식을 세우고, 그 소켓의 목 cysd 가 끝날(좀비 또는 사라짐) 때까지 기다린 뒤(상한 500회 · 정상 1~3회 — 실측 진입→반환 57ms) `exit 0`.
  목 cysd 가 없는 성공(사전 검사의 재사용 갈래 등)은 기다리지 않는다.
- 결과: 「소켓 생성」과 「목 종료」 사이에 반드시 「핑 성공 관측」이 끼므로 `boot_wait` 는 성공 경로에서 `kill -0` 사망을 볼 수 없다. 핑이 목 종료 뒤에 성공을 돌려주므로 케이스 끝
  잔존 프로세스 검사(`Sandbox.cleanup` 의 「남으면 적」)와도 경주하지 않는다.
- 시험 약화 0: 단언·대상 시험·`dead` 모드(실패 시나리오) 무변경 · 재시도 0.
- 소켓키 = 핑 목이 이미 쓰는 꼴(`${CYS_SOCKET//\//_}`) — 그래서 목 cysd 를 bash 로 바꿨다. 이 시험을 도는 레인 = 맥(`macos-rust-pack`)·우분투(`ubuntu-pack-suite`)뿐(ci-branch.yml:1061·1880 · release.yml:650·1699 · pack-release.yml:356) — 윈 레인 없음.

## 4. 검증

| 항목 | 결과 |
|---|---|
| 기준선(수리 전) 대상 모듈 1회 | 105건 OK · 75초 |
| 대상 케이스 단건 30회(수리 후) | **30/30 녹** |
| 대상 모듈 전체 30회(수리 후 · 6개 동시 = 부하 중) | **30/30 rc 0** · 매회 `Ran 105 tests` · OK · 1회 211~234초(동시 6 · 단독은 61~75초) · 끝난 뒤 남은 시험 프로세스 0 |
| 팩 py 전건 189종(직렬 1회 · 격리 HOME · `CYS_*` 제거 · `CYS_UPDATE_STATE_DIR` 격리 · `CYS_FEEDBACK_BASE=127.0.0.1:9` · 27분) | **186 rc 0** · 적 3 = 전부 기준선 ↓ |

팩 전건 적 3의 판정:
- `test_agora_known_authentic` — `CYS_AGORA_ZIP_DIR 없음 — 게시 zip 폴더를 지정하라(skip 금지 · 제작 맥 전용 시험)` = 브리프의 기준선 적 그대로.
- `test_preflight_phase1_checks` · `test_verify_gate` — rc 2 · 0초 · `REFUSE(hard assert): 격리 env 미설정 ['JAVIS_ROOT', 'CYS_PROBE_RUNS']`(시험 자신의 라이브 오염 차단 장치).
  `JAVIS_ROOT=<임시> CYS_PROBE_RUNS=<임시>/probe_runs.jsonl` 로 다시 돌려 **26 OK · 9 OK**. 앞선 HANDOFF(next·installer)와 같은 판정.
- 참고: `test_dept_team_token` 은 전건 안에서 rc 0(23초) · `test_dept_create_progress` rc 0(61초).
- 실행 상한 사고 1건(정직 고지): 30회 반복 스크립트가 내가 건 15분 상한(SIGALRM · exit 142)에 걸려 18회 뒤 끊겼다 — 그때 돌던 6회(19~24)는 그대로 끝나게 두고 25~30회를 이어 돌려 30회를 채웠다(위 결과).
  첫 시도는 macOS 에 `timeout` 이 없어 exit 127 로 시작조차 안 됐다(perl `alarm` 으로 대체).
| win-typecheck | 해당 없음 — 러스트 변경 0 |

## 5. 【결정필요】 형제 시험의 같은 꼴 (범위 밖 · 고치지 않음)

같은 「소켓 파일 생성 → 즉시 종료」 목 cysd 가 세 파일에 더 있다. 같은 `boot_wait` 성공 경로를 탄다면 같은 잠재 플레이크다(**추정 — 강제 재현 안 함**):

- `test_dept_name_guard.py:164`(목 cysd 공통) · `:1071`(env 덤프 목)
- `test_dept_team_token.py:111`
- `test_team_create_u16.py:92`

선택지: A) 같은 꼴 수리를 후속 티켓으로(권고 — 파일마다 목 구조가 달라 각각 강제 재현 → 수리 → 뮤턴트가 필요) · B) 이 가지에 덧붙임 · C) 두고 본다(CI 재발 시 처리).

## 6. 남긴 것

- 커밋: `b5ed5fbc` test — 목 cysd 수리(시험 파일 1개 · +19 −3 · 주석 2줄 보정 포함) · 이 문서 = 다음 docs 커밋.
- push·태그·CI 재실행 = 하지 않았다(master 몫).
- 장기기억 증류 1건: `feedback_cysd-dept-mock-exit-races-boot-wait`(원인·핸드셰이크 재현법·계측 함정).
- 강제 재현 하네스는 scratch 에만 있다(저장소에 안 넣음) — 필요하면 이 문서 §2 의 설계 그대로 다시 만든다.

---

# 덧붙임 · TICKET=cysr-1111-dept-mock-siblings · 2026-10-22 17:23~ · worker-3

지시 = master#e518da57(결정 A) · 마감 결정 = master#9b238c76(C: 형제 목 수리까지로 닫는다 · name_guard 30회는 별건 1건 제외 집계 병기).
커밋 = `f6fe2692`(시험 3파일 + 공용 조각 `cysjavis-pack/bin/tests/dept_mock_hold.py`) · 운영 코드 변경 0.

## S1. 강제 재현 → 수리 → 뮤턴트 (파일별 · 모듈 전체 실행)

하네스 = 모듈의 `_write_exec` 를 감싸 목 cys/cysd 내용만 바꾼다(시험 파일 무수정) · 주입 = §2 와 같은 핸드셰이크
(목 cysd 는 `touch` 직전에 「핑이 소켓 없음을 확인」 표식을 기다리고 · 그 핑은 목 cysd 가 끝난 뒤 실패 반환) · 주입 지점 = `  ping) ` 머리 · `touch "$CYS_SOCKET"` 줄(수리 전후 공통).
뮤턴트 = 수리본에서 목 cysd 의 「관측 신호까지 대기」 줄(`while [ ! -e …answered`) 1줄 삭제 + 같은 주입.

| 파일 | 대조군(수리 전) | 수리 전 · 주입 | 수리 후 · 주입 | 뮤턴트 · 주입 |
|---|---|---|---|---|
| `test_team_create_u16`(목 `:92`) | 19 중 적 0 | **적 4**(A1·A3·A4·A5 — 전부 「기동 중 종료/기동 실패」) | 적 0 | 적 4(같은 4건) |
| `test_dept_team_token`(목 `:111`) | 23 중 적 0 | **적 12**(T5·T6·T7·T8·T9·T16·T17·T18·T19×2·T20×2) | 적 0 | 적 12(같은 12건) |
| `test_dept_name_guard`(목 `:164` 공용 make_home) | 75 중 적 0 | **적 4**(CreateGate happy · J5 m1 · RotatePostKill relaunch · SockLenDiag mkdtemp) + 별건 1 ↓ | 적 0 | 적 4(같은 4건) |

- `T16`·`T9` 처럼 원래 실패를 다루는 케이스도 원문 확인: 스폰 뒤 시드 실패(rc 6)·생성 성공(rc 0)을 기대하는데 그 앞 기동 단계에서 「기동 중 종료」(rc 1)로 꺾였다 = 같은 경주.
- 뮤턴트 실행의 name_guard 「OTHER」 9건은 **내 하네스 결함** — 뮤턴트 모드가 자기 목을 쓰는 케이스(대상 줄 없음)에서 `뮤턴트 대상 줄이 정확히 1줄이 아니다` 단언을 냈다(원문 확인). 시험 결과 아님.

## S2. `name_guard:1071`(j6 env 덤프 목) = 경로가 다름 → 수리 안 함

- 주입이 그 목에도 걸렸는데(목 적중 75회 중) `test_j6_marker_is_not_inherited_by_the_spawned_daemon` 은 녹.
- 근거: 이 시험은 `rotate` 의 rc 를 단언하지 않고 「스폰된 자식 cysd 의 env 덤프」만 판정한다 — boot_wait 성패가 결과를 못 바꾼다.
- 같은 파일의 다른 목: `:1319`(누수 검사 · `exec sleep 600` = 스스로 안 끝남) · `:1399`(`exit 0` 만 = 실패 시나리오) · `PostSpawnRegistryFailure` 의 파이썬 목 = 이 경주와 무관.

## S3. 수리

- `dept_mock_hold.py`(신규 · 시험 폴더) = sh 조각 3개: `ping_answered(st)`(핑 성공 갈래 전체 — 관측 신호 → 그 소켓 목 cysd 가 끝날 때(좀비 포함)까지 대기 → `exit 0`) ·
  `cysd_before_touch(st)`(묵은 신호 삭제 · 자기 pid 기록) · `cysd_after_touch(st)`(신호까지 생존 · 상한 1000×0.01초). 상태 폴더 = 케이스 임시 폴더의 `mockhold/`(소켓 폴더 무접촉).
  조각에 `%` 가 없다 → 세 파일의 서로 다른 목 꼴(`%` 서식 · `%%` 이스케이프 템플릿 · 즉석 목)에 **값**으로 끼운다. POSIX sh 만(목이 `#!/bin/sh`).
- 세 파일: import 2줄(`sys.path.insert(0, SELF)` + `import dept_mock_hold`) + 목 2개의 ping 갈래·touch 앞뒤. 목의 나머지 꼴(셔뱅 · 호출 기록 · pgid 기록 · env 덤프)은 그대로.
- `test_dept_create_progress` 는 b5ed5fbc 의 bash·@STATE@ 꼴을 유지(이 모듈을 쓰지 않음 — 무리한 통합 금지).
- 세 파일이 도는 레인 = 맥(`macos-rust-pack`)·우분투(`ubuntu-pack-suite`)·release 의 aarch64-apple-darwin 스텝(`if: matrix.target == 'aarch64-apple-darwin'`) — 윈도 번들 파이썬(스크립트 폴더가 sys.path 에 안 들어온다 · test_import_guard 배경) 레인 없음.
- 케이스별 시간: name_guard 수리본 92초(기준 90초) · 가장 느린 케이스 5초 — 관측 신호를 안 주는 케이스별 cys 목(`:694`·`:763`·`:832`·`:1005`)과 짝지어도 늘지 않았다(`--durations` 실측).

## S4. 검증

| 항목 | 결과 |
|---|---|
| `test_team_create_u16` 30회(동시 3) | **30/30 rc 0** · 매회 19 OK |
| `test_dept_team_token` 30회(동시 3) | **30/30 rc 0** · 매회 23 OK |
| `test_dept_name_guard` 30회(동시 5 · 15×2 묶음) | **29/30 rc 0** · 적 1회 = 별건 1건(`test_create_spawn_loser_preserves_live_winner`)만 · 그 회차의 다른 적 0 → **별건 제외 30/30** |
| 팩 py 전건(`f6fe2692` 별도 작업트리 · 동시 4 · 격리 env 같은 꼴 · 약 12분) | **184 rc 0** · 적 5 = 기준선 3 + 실행 조건 산물 2 ↓ |

전건 적 5의 판정:
- `test_agora_known_authentic`(CYS_AGORA_ZIP_DIR 없음) · `test_preflight_phase1_checks`·`test_verify_gate`(격리 가드 거부 → 요구 env 로 재실행 **26 OK · 9 OK**) = 기준선.
- `test_session_start_hook` rc 1 · 「4 FAIL」(18c·18d·18e reclaim-role 계측 · 20j 강등 문안) — **동시 4 실행에서만** · 같은 작업트리 직렬 재실행 **ALL PASS**. 이 수리는 훅·cys-dept 무접촉.
- `test_dbg_d3_d11_shared_profile_hooks` rc 2 · `MEASURE-FAIL: 본부 컨텍스트 등록이 0건` — 작업트리가 `/private/tmp` 아래라 C28 이 「임시 팩 컨텍스트 — 등록 금지」로 판정해 측정 전제가 무너졌다(위치 산물 · 직렬 재실행도 rc 2).
  본 작업트리(`~/cys-terminal-src-wt/1111-deptflake` · 이 수리 포함)에서는 **rc 0 · PASS**.
- 별도 작업트리를 쓴 이유: 다음 티켓의 cys-dept 수리를 본 작업트리에서 병행하려고(이 전건은 `f6fe2692` 그대로를 재야 한다).

## S5. 별건(이 티켓 밖) — 경쟁 승자 플레이크

`test_dept_name_guard` `PostSpawnRegistryFailure.test_create_spawn_loser_preserves_live_winner` — HEAD 사본 **단독 10회 중 5회 적**(수리본 2/10 · 이 케이스는 cys·cysd 를 자기 파이썬 목으로 갈아 끼워 이 수리와 무관).
증상 = rc 12 는 맞는데 「후행 ready가 경쟁 승자의 응답을 못 받음」(핑 4~8회 · pong 0). 원인과 수리 = 다음 티켓 `cysr-1111-bootwait-lock-winner`(아래 덧붙임).

---

# 덧붙임 · TICKET=cysr-1111-bootwait-lock-winner · 2026-10-22 17:42~ · worker-3

지시 = master#9b238c76(권고 A · 운영 코드 변경 허용). 바뀐 파일 = `cys-dept`(운영 · +19 −2) · `test_d1_dept_ready_probe.py`(새 행위 시험 3 + 가짜 cysd 모드 3) · `test_dept_name_guard.py`(경쟁 승자 픽스처 = 락 먼저).

## W1. 원인 (확정 — 강제 재현 + 운영 진리표 + 실 바이너리)

- `boot_wait` 는 우리가 띄운 cysd 의 pid 가 죽으면 즉시 「기동 중 종료」로 실패했다(dbg-D10). 그런데 그 cysd 가 **싱글턴 경쟁 패자**면 소켓은 승자가 연다.
- 실 cysd 의 패자 판정(`src/bin/cysd/deadman.rs:167` `judge_holder`): `Some(_) if responded => Healthy` · **`Some(_) if !hb_stale => Healthy`** — 승자가 **아직 응답하지 않아도** 하트비트만 신선하면
  패자는 「건강한 홀더」로 보고 exit(1) 한다. 승자는 락을 잡는 즉시 pid 를 적고 하트비트를 찍는다(`deadman::claim_lock` · `src/bin/cysd/main.rs:1773` `acquire_startup_lock`).
  ∴ 「락에 산 승자 pid · 소켓 무응답 · 패자 이미 종료」 창이 운영에 실재 → 그 창에서 boot_wait 가 살아 있는 승자를 버린다.
- 시험 픽스처(`PostSpawnRegistryFailure` 경쟁 승자)는 패자 사망 **뒤에** 락·소켓을 함께 공개했다 → 그 사이 boot_wait 가 사망을 먼저 보면 적(HEAD 단독 5/10).
  이 순서는 실 cysd 와 다르다(실 패자는 승자가 락을 **이미** 쥐었기 때문에 진다).

### 강제 재현 (시험 파일 무수정 하네스 · 모듈 전역 `open` 을 감싸 픽스처 도우미 기록 순간만 바꿈)

주입 = 승자가 「패자 사망 → 사망 뒤 첫 핑 → +1초」 뒤에야 공개(앵커 = 승자 갈래 `    corrupt()` + `sock = Path(...)` 두 줄 · 수리 전후 공통).

| 실행 | 결과 |
|---|---|
| 수리 전(HEAD cys-dept + 락-먼저 픽스처) · 주입 10회 | **10/10 적** — 전부 `1 != 12 : 스폰 이후 판독 실패가 exit12로 전파되지 않음`(사망을 먼저 보고 회수 → rc 1) · 주입 적중 10/10 |
| 수리 전 HEAD 사본 · 주입 없음 · 단독 10회 | 5/10 적(기존 플레이크 그대로) |
| 수리 후 · 주입 10회 | **0/10 적** |
| 수리 후 · 대조군(주입 없음) 10회 | 0/10 적 |

- 하네스 결함 1건(정직 고지): 처음엔 회차마다 스위트를 따로 돌려 모듈 정리(`tearDownModule`)가 매번 RUN_ROOT 를 지웠다 → 2회차부터 `FileNotFoundError`. 10회를 한 스위트에 담아 다시 쟀다(위 표).

## W2. 수리

- 운영 `cys-dept`: `boot_lock_winner(sock, pid)` 신설 — `${sock%.sock}.lock` 첫 줄이 숫자뿐 · 0 아님 · 우리 pid 아님 · `kill -0` 성공일 때만 0.
  `boot_wait` 는 pid 사망 시 이것이 0 이면 안내 1줄(「부서 데몬(pid N)은 끝났지만 시작 락을 다른 산 데몬이 쥐고 있다 — 그 데몬의 응답을 기다린다」 · 1회만)을 내고 **기존 정지(`CYS_DEPT_BOOT_STALL_S`)·상한(`CYS_DEPT_BOOT_MAX_S`) 검사 그대로** 계속 돈다.
  아니면 종전과 같은 「기동 중 종료」 조기 실패(dbg-D10 유지). 판정은 매 반복 다시 한다 — 기다리던 승자마저 죽으면 다음 반복에서 조기 실패.
  예산 초과 = 기존 문구(「기동 진행이 N초 멈췄다」/「기동 상한 N초 초과」) + 「데몬 기동 실패」.
- 윈도: 소켓이 named pipe 이름(`\\.\pipe\cys-dept-<이름>` · `cys-dept:dept_sock`)이라 `.lock` 파일이 없다 · 윈 cysd 는 시작 락을 `#[cfg(unix)]` 갈래에서만 만든다 → 항상 1 = 동작 무변경. Rust 변경 0 → win-typecheck 해당 없음.
- 시험 `test_dept_name_guard` 경쟁 승자 픽스처: 승자가 **시작하자마자** 락(자기 pid)을 쥔다(실 cysd 순서). 끝의 락·소켓 공개 줄과 모든 단언은 그대로.
- 시험 `test_d1_dept_ready_probe` `DeptFirstBootWait` 에 3건(가짜 cysd `D10_MODE` = `lost_win`·`lost_dead`·`lost_never`):
  ① 산 승자가 락을 쥐고 2초 뒤 응답 → rc 0 · 안내 줄 · 「데몬 기동 실패」 없음 ② 락에 죽은 pid → 10초 안 조기 실패 + 「기동 중 종료」 + 고아·등록 회수
  ③ 산 승자가 끝내 무응답 · 정지 예산 3초 → 25초 안에 「기동 진행이 3초 멈췄다」 + 「데몬 기동 실패」 + 등록 원복. 기존 `die`(빈 락 → 조기 실패) 핀이 「락 pid 없음」 갈래를 그대로 지킨다.

## W3. 뮤턴트 · 수리 전 적

| 변이 | 대상 시험 | 결과 |
|---|---|---|
| 수리 전(HEAD cys-dept) | ① lost_win | **적** — 「락을 쥔 산 승자를 버리고 실패했다」 |
| 뮤턴트 A: 산 pid 검사(`kill -0 "$h"`) 삭제 | ② lost_dead | **적** — 31.4초 헛대기 → 「조기 실패가 아니다」 |
| 뮤턴트 B: 승자 대기 중 정지·상한 검사 무시(2줄) | ③ lost_never | **적** — 40초 시간 초과(`TimeoutExpired`) |

뮤턴트는 스크립트가 심고 끝나면 수리본으로 복원(바이트 동일 확인 `cmp`).

## W4. 실 cysd 동시 기동 2개 (격리 HOME · `/tmp` 짧은 경로 — scratch 경로는 sun_path 104B 초과)

1) 맨 cysd 2개 같은 소켓: 락 = 승자 pid · 패자 `error: another cysd holds the startup lock … reason=healthy-holder` · 승자 `pong`.
2) `cys-dept launch` 경유(이 수리): 승자 cysd 를 먼저 띄워 락 pid 기록(0.03초) → 직전 승자 응답 rc 1(아직 무응답 = 창 안) → `launch` 가 띄운 cysd = 패자(`healthy-holder`) →
   boot_wait 안내 줄 「…시작 락을 다른 산 데몬이 쥐고 있다 — 그 데몬의 응답을 기다린다」 → **rc 0 · 51.6초**(승자 첫 기동의 팩 설치) · 승자 생존 · 락 = 승자 pid · 소켓 응답 rc 0 · 소켓 파일 1개.
- ⚠ 하네스 정리 누락 1건(정직 고지): `cys-dept` 가 `CYS_SOCKET` 없이 `cys` 를 부를 때 `cys` 가 격리 HOME 의 **기본** 데몬(`.local/state/cys/cys.sock`)을 자동 기동했고, 그 데몬은 독립 세션이라
  내 프로세스 그룹 정리에서 빠졌다 — lsof 로 내 격리 HOME 파일을 쥔 것을 확인하고 그 pid 하나만 종료(잔존 0 실측). 다음 실행은 `CYS_NO_AUTOSTART=1` 또는 격리 HOME 소켓 보유자 회수가 필요.

## W5. 검증

| 항목 | 결과 |
|---|---|
| `test_d1_dept_ready_probe` 전체 | 14 OK · 98초 |
| `test_dept_create_progress` 전체(boot_wait 문면 census · bash 3.2/MSYS 문법 census 포함) | 105 OK |
| `test_win_dept_spawn` · `test_dept_win_python_resolve` · `test_dbg_d3_dept_path_precedence` | 11 OK(skip 2 = 윈 실기 전용) · rc 0 · rc 0 |
| `test_dept_name_guard` 30회(수리본 · 동시 5 · 15×2) | **30/30 rc 0** · 매회 75 OK — 별건이던 `test_create_spawn_loser_preserves_live_winner` 포함 적 0 · 끝난 뒤 남은 시험 프로세스 0 |
| 팩 py 전건(수리본 · 본 작업트리 · 동시 4 · 격리 env 같은 꼴) | **185 rc 0** · 적 4 = 기준선 3 + 부하 시한 1 ↓ |

전건 적 4의 판정:
- `test_agora_known_authentic` · `test_preflight_phase1_checks`·`test_verify_gate`(요구 env 재실행 **26 OK · 9 OK**) = 기준선.
- `test_d1_dept_ready_probe` rc 1 — 새 시험이 아니라 **기존 `die` 핀**(`test_daemon_death_during_boot_fails_fast_and_unregisters`)이 동시 4 실행에서 14.2초로 「10초 안」 문턱을 넘었다.
  판정 근거(실측): 이 케이스 직렬 3회 소요 = 수리본 4.7·1.7·1.7초 / 수리 전(HEAD cys-dept) 4.4·1.6·1.6초 — 같다(빈 락 → `boot_lock_winner` 는 `read` 빈 값으로 즉시 1).
  당시 맥 부하 평균 17~23(다른 좌석 작업 겹침). 모듈 직렬 재실행 **14 OK**. → 부하 시한 · 수리 무관.
- 이번 전건에선 `test_session_start_hook` · `test_dbg_d3_d11_shared_profile_hooks` 둘 다 rc 0(형제 전건의 두 산물은 동시 실행·/tmp 작업트리 조건 탓이라는 판정과 맞다).
