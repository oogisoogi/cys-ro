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
