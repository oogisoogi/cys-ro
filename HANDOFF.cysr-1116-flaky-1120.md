# HANDOFF — TICKET=cysr-1116-flaky-1120 (팩 시험 간헐 붉음 원인 규명·결정론 고침)

- 가지 `feat/1116-flaky` ← dea2e1853 · cwd `/Users/oogisoogi/axdev/.wt/cys-1116-flaky` · 커밋 55e7e7e99(시험) + 이 문서 커밋
- 바뀐 것 = **시험 파일 5개만**(+135줄 · 제품 코드·훅·데몬·워크플로·팩 지침 변경 0) · push·태그·CI·발행 0 · codex 호출 0(브리프: 시험 전용)

## 1. 원인

macOS 는 **새로 만든 실행 파일의 첫 실행**에 정책 검사를 붙여 0.3~3.6초를 쓴다. 시험들은 케이스마다 가짜 `cys` 셸 스텁을 새로 쓰고, 훅·해소기는 그 스텁 호출을 **2초 시한**(`cys_timeout_run 2` · 파이썬 `QUERY_TIMEOUT_S = 2.0` · owner 는 발송 시간 상한 1.6초)으로 감싼다. 첫 실행 검사가 그 시한 안에 걸리면 스텁이 호출 기록을 남기기 전에 시한 종료(rc 124)로 죽고, 시험은 「데몬에 묻지 않았다 / 해소 결과 none / 발송 0건」으로 붉었다. 어느 스텁의 첫 실행이 2초를 넘느냐가 그때그때 달라서 **매번 다른 시험**이 붉었다.

- 확신도: 기제(첫 실행 지연 × 2초 시한) = **High**(아래 2절 원자료 4종 · 뮤턴트 아닌 대조 실측) · 검사 주체가 syspolicyd 라는 것 = **Med**(CPU 증가 정황뿐 · 커널 로그 미확인).
- 부하(load)는 2차 요인이다: load 9.7 에서도 첫 실행 상위 10% 가 2.12초였고 refl_inject 는 load 6.4 에서 붉었다. 「새 실행 파일을 많이 만드는 다른 시험이 동시에 도는가」가 더 직접적인 변수로 보인다(검사 대기열 공유 — 추정 · 측정은 아래 표 1행).
- 리눅스(우분투 CI)에는 이 검사가 없어 CI 에서는 초록이었다(debt-u HANDOFF 기록과 일치).

## 2. 근거 (원자료 · 전부 이 맥 2026-11-20 03:3x~04:4x KST · macOS 26.6.2 · 16코어)

| # | 무엇을 쟀나 | 결과 | 출처(스크래치) |
|---|---|---|---|
| E1 | 고치기 전 판에 계측(시한 래퍼가 호출마다 경과·rc 기록)을 넣고 capgate 를 6회 | 6회 전부 붉음 · `cys surface-role` 호출 15건 중앙값 **2.005s** · rc 124(시한 종료) 3건 = **2.115·2.145·2.037s**(load 10.6~11.7) · 같은 훅 안의 `dd` 판독은 0.009s | `runs/inst-timing.log` · `runs/test_capgate_hook_shell.inst/` |
| E2 | 새 셸 스텁 첫 실행 vs 재실행(30회 · load 12~14) | 첫 실행 중앙값 **1.648s** · 상위 10% **2.236s** · 최대 3.315s / 재실행 0.004s / `/bin/sh -c true` 0.004s | `firstexec.py` |
| E3 | 조건 가르기(15회) | 같은 경로 덮어쓰기(새 본문) 0.007s · `/bin/sh 파일` 로 읽기만 0.006s · 그 뒤 exec 하면 다시 0.32s · `xattr -c` 뒤 0.34s(무효) · 같은 내용 다른 파일 0.53s(다시 느림) | `fe2.py` |
| E4 | 자리표시 예열 → 같은 경로에 진짜 본문(50회 · **load 9.7**) | 예열 첫 실행 중앙값 1.599s · 상위 10% 2.124s / 그 뒤 진짜 본문 실행 **최대 0.227s** / 새 파일 대조 1.611s | `fe3.py` |
| E5 | 새 파일 40개 첫 실행 vs 같은 파일 40회 | 28.72s vs 1.31s · 그동안 syspolicyd CPU 84:05.17 → 84:06.94(+1.77s) | 인라인 |
| E6 | 부하 주입 중 같은 측정(20회) | 예열 첫 실행 상위 10% **2.952s** · 최대 3.644s / 진짜 본문 최대 0.078s | `fe3.py` |

- 이 맥에는 `timeout`·`gtimeout` 이 없다 → `cys_timeout_run` 은 ③ python 폴백(새 세션 Popen + `wait(timeout=2)`)으로 돈다. 시한은 Popen 뒤부터라 python 기동 시간은 안 들어간다 — 남는 것은 스텁 exec 자체의 지연뿐이다.
- 대조군 실패 문구(고치기 전 · 전부 같은 꼴): capgate `'surface-role' not found in ''` · `0 not greater than or equal to 1 : 첫 호출은 조회해야 한다` · 캐시 파일 FileNotFoundError / role_authority_shell `expected '0\ncso\ndaemon\nunset\n', got '0\n\nnone\nunset\n'` / refl `3a ★CYS_BIN 이 지정한 실행파일로 물었다 — []` / owner `test_app_flush_per_item_budget_and_request_id: 0 != 1` / role_authority `8i-2 … rc=0 out='master (surface matches mission ledger)'`.
- 대조군에서 붉어진 시험 이름 빈도(capgate 40회): colliding_socket_slugs 4 · legacy_two_field 3 · gated_cache_never_fastpath 3 · failed_query_backs_off 3 · hostile_boot_epoch 3 · cache_lives_in_shared_0700 3 · stale_cache_requeried 2 · role_query_never_spawns 2 · named_pipe_endpoint 2 · gated_surface_role_hint 1 — 모두 「가짜 cys 를 써 놓고 훅이 그것을 부르기를 기대하는」 시험이다(cys 가 필요 없는 시험은 0회).

## 3. 고침 (커밋 55e7e7e99)

각 파일에 같은 헬퍼 `prime_exec(path)` 를 두고, 스텁의 **진짜 본문을 쓰기 직전에** 부른다. 헬퍼는 그 경로에 자리표시(`#!/bin/sh\nexit 0`)를 써서 한 번 실행한다(시한 없음 · 60초 안전 상한 · 실패는 삼킴). 이어서 호출측이 같은 경로에 진짜 본문을 덮어쓴다 — E3·E4 대로 첫 실행 검사는 다시 붙지 않는다.

- 자리표시만 실행하므로 스텁 본문의 부작용(호출 로그 append · `rm -f "$2"` 등)이 일어나지 않는다 → 호출 횟수를 세는 단언에 영향 0(고친 판 반복에서 호출 수 단언 전부 초록).
- 시한(2초)·훅·해소기·데몬은 건드리지 않았다(제품 계약 · M3 「CYS_ROLE_QUERY_TIMEOUT cannot extend the 2s deadline」 시험 그대로 초록).
- 붙인 자리:
  - `test_capgate_hook_shell.py` — `fake_cys` · `_break_cygpath` · `_destroy_input`
  - `test_role_authority_shell.py` — `Sandbox.__init__` 의 cys 스텁 · `_no_mktemp` 스텁 (+`import os` — 이 파일엔 없었다)
  - `test_role_authority.py` — `stub_dir` 의 cys 스텁 · `cys-dept-stub`
  - `test_owner_desk.py` — `fake-cys`
  - `test_refl_inject_context_role_canon.py` — `_write_exec`(ps·lsof·cys 스텁 전부)
- 공용 모듈로 빼지 않은 까닭: 이 폴더 시험은 파일마다 자기완결이고 공용 import 관례가 없다(비-test_ 모듈은 하네스·뮤턴트뿐). 5곳 같은 문면 = 의도.
- 윈도·리눅스: 윈도에서 확장자 없는 스크립트 exec 는 OSError → 삼킴(종전 동작). 리눅스는 첫 실행 비용이 없어 스텁당 수 ms 만 더 든다.
- 1차안(같은 스텁 본문을 로그 env 를 /dev/null 로 돌려 실행)은 버렸다 — 로그 경로를 본문에 박아 둔 스텁(role_authority·owner)에서 호출 기록을 오염시키기 때문. 1차안 부분 결과(capgate 9/9 · role_shell 3/3 초록)는 참고만.

## 4. 전후 실패율 (단독 반복 · 회마다 새 격리 HOME/TMPDIR/CYS_PACK_DIR · `env -i` · CI 팩 루프와 같은 실행 꼴)

| 시험 | python | 고치기 전 붉음 | 고친 뒤 붉음 | 비고 |
|---|---|---|---|---|
| test_capgate_hook_shell | Apple 3.9 | **13/20** | **0/20** | 같은 시간대(load 7~22) |
| test_capgate_hook_shell | brew 3.14 | **10/20** | **0/20** | |
| test_role_authority_shell | Apple 3.9 | **11/20** | **0/20** | |
| test_refl_inject_context_role_canon | Apple 3.9 | 10/10 | 0/10 | 동반 · N=10 |
| test_owner_desk | Apple 3.9 | 9/10 | 0/10 | 동반 · N=10 |
| test_role_authority | Apple 3.9 | 7/10 | 0/10 | 동반 · N=10 · 마지막 일부 회차는 부하 주입과 겹침 |
| test_pyseal_negative_specimen | Apple 3.9 | 0/1 | (안 바꿈) | 단독 1회 초록 · 스텁 첫 실행이 시한 안에 들지 않는 구조(run_py timeout 120) |
| **부하 주입 중** capgate | Apple 3.9 | **5/10** | **0/10** | 주입 1(04:34:45~04:49:15) 동안·직후 |
| **부하 주입 중** role_authority_shell | Apple 3.9 | 4/6 | 0/6 | 주입 중단 뒤 반복 중단(부분) |

- 수용 기준 대조: 「고친 뒤 같은 조건 N≥20회 붉음 0」 = capgate(Apple·brew)·role_authority_shell **통과**. 「부하 주입에서도 0」 = **통과**(capgate 10 · role_shell 6). 동반 3종은 N=10(20 아님) — 📌.
- ⚠고치기 전 대조군을 「load<10 단독」 조건으로 돌리지는 못했다: 같은 시간에 다른 좌석들이 돌아 load 가 7~22 였다. 그 대신 고치기 전·고친 뒤를 **같은 시간대에 나란히** 돌려 주변 부하를 같게 맞췄다. 또한 E4 는 load 9.7 에서 첫 실행 상위 10% 2.12초 = 부하 낮을 때도 시한을 넘는다.
- ⚠CI 팩 단계 **전체**(mac 루프 151개 · 1450초)는 돌리지 않았다 — 바뀐 5파일을 CI 와 같은 꼴(`CYS_PACK_DIR=$(mktemp -d)` + `python3 파일`)로 위 횟수만큼 돌렸고, 다른 파일은 손대지 않았다. 정적 점검: `test_pyseal_census` PYSEAL-CENSUS-OK · `scripts/secret-scan.sh` 5파일 clean · 5파일 py_compile OK.

## 5. 뮤턴트 (고친 시험이 여전히 대상을 잡는가 · 고친 사본에 제품 쪽 결함을 심어 1회씩)

| 뮤턴트 | 심은 결함 | 결과 |
|---|---|---|
| MA | capgate 훅이 데몬 조회를 아예 안 함(`_cg_skip_query=1` 고정) | capgate **11건 붉음** — 흔들리던 바로 그 시험들(stale_cache·gated_cache·legacy·colliding·named_pipe·role_query_never_spawns·failed_query_backs_off·cache_lives·hostile_boot_epoch·gated_surface_role_hint·authoritative_none) |
| MC | capgate 훅의 `CYS_NO_AUTOSTART=1` 봉인 제거 | `test_role_query_never_spawns_a_daemon` 붉음 |
| MB | `_lib.sh cys_resolve_role` 의 NO_AUTOSTART 봉인 제거 | role_authority_shell **29건 붉음**(`expected ['1\tsurface-role'], got ['unset\tsurface-role']`) |
| MF | 같은 MB 를 refl 시험으로 | `5b ★모든 조회에 CYS_NO_AUTOSTART=1 — ['<unset>']` 붉음 |
| ME | `javis_role.py` 자식 env NO_AUTOSTART 를 "0" 으로 | role_authority `9a` 붉음 |
| MD | owner 발송 시간 상한 검사 무력화(`remaining < 1.0` → `< -99`) | `test_flush_starts_nothing_when_budget_short` 붉음 |
| MD3 | owner 발송에서 `--request-id` 제거 | 흔들리던 `test_app_flush_per_item_budget_and_request_id` 붉음 |

7/7 붉음. 뮤턴트 사본은 스크래치(`mut/`)에만 있고 저장소는 무접촉.

## 6. 공유 자원 경합 표 (시험끼리·시험과 기계 사이)

| 자원 | 누가 같이 쓰나 | 격리 상태 | 이번 붉음 원인? |
|---|---|---|---|
| macOS 첫 실행 검사(syspolicyd 추정) | 기계 전체 — 새 실행 파일을 만드는 모든 시험·좌석 | **격리 불가**(시스템 데몬) | **예 — 주원인**. 고침 = 비용을 시한 밖으로 |
| 역할 캐시 폴더 `cys-role-authority.d` | 같은 TMPDIR 의 훅·해소기 | 시험마다 새 TMPDIR(capgate `_HookEnv`·role_shell 케이스마다 새 root·role_authority 케이스마다 새 TMPDIR) | 아니오(실패 시 캐시 파일 「없음」은 조회가 죽은 결과) |
| 소켓 이름·기본 신원 `default:<XDG>:<HOME>` | 캐시 키 | HOME 이 시험마다 새것 · 가짜 cys 라 실제 소켓 접속 0 | 아니오 |
| 시계(`date +%s` 초 단위 · TTL 15/60초 · 백오프 5/30초) | 캐시·백오프 판정 | 시험이 age 999/61/31 같은 큰 여유로 심음 | 이번 실패 0건. **남는 위험**: capgate `test_failed_query_backs_off` = 첫 호출 뒤 훅 3회가 **5초 백오프 창 안**에 끝나야 함(예열 뒤 1회 ≈0.3~1s 라 여유 있으나 극부하 땐 이론상 가능 · 고친 판 70회에서 0건) |
| 발송 시간 상한(owner 1.6초 · 느린 데몬 흉내 1초) | `test_app_flush_per_item…` | — | 첫 실행이 원인이었음(고침). **남는 여유** = 1.6 − 1.0 − python 기동 ≈ 0.3~0.5초 · 고친 판 10회 0건 |
| `/tmp/cys-to-inst.log` 등 | 내 계측 전용 | 스크래치 사본에만 있음(저장소 무관) | — |

## 7. 남은 것·📌 (실행 안 함 · 판단 = master)

1. 동반 3종(refl·owner·role_authority)은 N=10 씩만 잼(20 아님) — 필요하면 같은 반복기로 10회씩 추가(회당 43·80·160초).
2. `test_phoenix_c6_reap` 단독 시한 초과는 **다루지 않았다** — 스텁을 만들지 않고 실제 cysd 를 띄우는 다른 꼴이다(브리프대로 조각 5 좌석 결과를 받아 씀). 단, 새로 빌드한 cysd 첫 실행에도 같은 검사가 붙을 수 있으니(추정 · 미측정) 그 좌석에 「첫 실행 지연」 대조를 권함.
3. 같은 꼴(새 스텁 + 시한)이 이 5개 밖 팩 시험에도 있을 수 있다 — 이번엔 브리프 대상만 고침. 저장소 훑기 후보: `rg -l "chmod\(.*0o7" cysjavis-pack/bin/tests` 중 시한 안에서 스텁을 부르는 것(이번 대조군에 안 잡힌 것은 증거 없음).
4. 제품 쪽 관찰(고치지 않음): 실제 설치 직후·판 올림 직후 **첫 `cys` 실행**도 같은 검사를 받으면 해소기 2초 시한에 걸려 env 폴백으로 강등될 수 있다(설계된 강등이라 위험은 낮음 · 미측정).
5. 부하 주입 1회(04:34:45~04:49:15 · 4+2 프로세스 · load 최고 27)가 다른 좌석 시간 문턱 시험을 거짓 붉음으로 만들었다(master#3a0cce31 지적 · 즉시 중단). 그 시간대 다른 좌석의 붉음은 재대조가 필요하다.

## 8. 함정·재현

- 반복기: 스크래치 `rep.sh <시험> <N> <python> <태그>`(회마다 `/tmp/fk.XXXXXX` 새 격리 · `env -i` HOME·PATH·TMPDIR·LANG + CYS_PACK_DIR) · `W=<팩 사본 루트>` 로 다른 사본 지정. PATH 에 `/usr/local/bin`(설치본 cys) 넣지 않음.
- 대조군이 작업트리 파일을 읽는 동안 작업트리를 고치지 말 것 — 이번엔 고침을 스크래치 사본(`fix/`)에서 만들고 대조군이 끝난 뒤 옮겼다.
- 다른 판끼리 비교할 땐 같은 시간대에 나란히 돌릴 것(주변 부하가 회차마다 7~27 로 흔들림).
- 첫 실행 비용은 「경로(vnode)」 단위 — 같은 경로 덮어쓰기는 다시 안 느리지만, 파일을 지우고 새로 만들면(새 vnode) 다시 느리다. 그래서 헬퍼는 `open(path, "w")`(제자리 덮어쓰기)를 전제로 한다 — 호출측이 `os.replace`·삭제 후 생성으로 바꾸면 예열이 무효가 된다.
- 반복기를 kill 할 때 시험 python 이 고아(ppid 1)로 남아 cys-dept 자식을 붙잡는다 — 끝에 `ps … | grep fk.` 로 내 고아 확인 후 pid 로만 종료(이번에 2건 정리).

---

# 2차 (master#ee9f8ce2 · 부하 주입 없음 · 커밋 c9ccfc026)

## ② 같은 꼴 저장소 훑기

- 방법(결정론): 시한 래퍼에 계측을 심은 스크래치 사본(`inst2/` · 저장소 무관)으로 **CI mac 팩 루프 151개 전부**를 1회 실행. 셸 `cys_timeout_run` ③ 폴백 + python `subprocess.run(timeout≤5)` 를 기록(경과·rc·실행 파일 나이). 판정 = 「나이 600초 미만 실행 파일의 **첫 호출**이 시한 ≤5초 안에서 0.25초 이상」. 한계: python `Popen.wait/communicate` 시한·Rust 쪽 시한은 계측 밖 · 사본에 `src/` 가 없어 Rust 소스를 읽는 시험 11개는 붉음(판정 대상 아님 · 호출 기록만 봄).
- 1차에서 고친 5파일 = 첫 호출 느림 **0**(capgate 0/14 · refl 0/7 · role_authority 0/93 · role_authority_shell 1 = 의도된 M3 시한 초과 시험).

| 시험 | 시한 | 첫 호출 느림 / 새 실행 파일 | 고치기 전 붉음(5회) | 고친 뒤 붉음(5회) |
|---|---|---|---|---|
| test_inject_context_role_seat | 2s(sh) | 20/20 | **2/5** | **0/5** |
| test_role_authority_triage | 2s(sh) | 1/1 | 0/5 | 0/5 |
| test_resource_gate_product_cpu | ps 1.5s · cys 5s(py) | 10/12 | 0/5 (훑기 1회에서 `test_9b_hung_lookup` 실붉음 = 「ps timeout 1.5 s」가 「deadline 3.0 s」보다 먼저) | 0/5 |
| test_dept_name_guard | 3s(py) | 8/9 | 0/5 | 1/5 ※ |
| test_dept_team_token | 3s(py) | 3/14(최대 2.55s) | 0/5 | 0/5 |
| test_team_create_u16 | 3s(py) | 10/10(1건 3.00s 시한 종료) | 0/5 | 0/5 |
| test_dept_create_progress | 3s(py) | 44/44 | 0/5 | 0/5 |
| test_teamtoken_hook | 3s(sh · CYS_PY 래퍼 pylog) | 4/30(1건 3.12s rc 124) | 0/5 | 0/5 |
| test_core_inject | 5s(sh) | 10/10 | 0/5 | 0/5 |
| test_event_inject | 5s(sh) | 1/1 | 0/5 | 0/5 |
| test_resource_gate_boot_anchor | 5s(py) | 1/1 | 0/5 | 0/5 |
| test_session_start_hook | 5s(sh) | 37/38 | **1/5** | **0/5** |
| test_session_start_r31 | 5s(sh) | 11/55 | 0/5 | 0/5 |
| test_dept_request | 5s(py) | 1/35 | 0/5 | 0/5 |

- ※ dept_name_guard 고친 뒤 1/5 = `test_create_spawn_loser_preserves_live_winner`(경쟁 스폰 승자 응답 대기 · load 18.2). 제 `_write_exec` 예열은 경쟁 시작 **전** 준비 단계에서만 불린다. 그 시험 묶음(PostSpawnRegistryFailure)만 단독 20회: 고치기 전 0/20 · 고친 뒤 0/20 → **미재현 · 원인 이름 안 붙임**(📌).
- 3~5초 시한 시험은 5회에서 고치기 전 붉음이 거의 없다 — 첫 실행 0.3~2.5초가 시한 안에 대부분 들기 때문. 고침의 근거는 붉음 횟수가 아니라 계측(첫 호출이 시한의 최대 85%까지 씀 · 시한 종료 2건 관측)이다.
- 제외: test_preflight_fresh_full_json 의 해당 스텁은 **제품 preflight(C82)가 스스로 만든다** → 시험 고침 대상 아님(0.61s / 5s · 기록만). owner_desk 의 3건 = 의도된 「느린 데몬」(sleep 1) 갈래.
- 고침 모양 = 1차와 같은 `prime_exec`(각 파일 자기완결 사본) · 붙인 자리 = 각 파일의 스텁 작성 함수(`_write_exec`·`_exe`·`w(mode&0o111)`) 또는 스텁 쓰기 직전 · event_inject 는 시스템 명령 대역 22개 전부(시험당 ≈+20s).
- 뮤턴트(고친 사본에 제품 결함): `_lib.sh` 해소기 조회 생략 → inject_context_role_seat 9건 붉음 · role_authority_triage `T3g` 붉음 / session-start `CYS_NO_AUTOSTART` 제거 → session_start_hook `18b` 붉음 / cys-dept 생존 판정 무력화 → dept_create_progress 붉음(dept_name_guard 는 이 결함의 대상 시험이 아님 = 초록).
- 정적: 14파일 py_compile OK · secret-scan clean · pyseal_census OK.

## ① test_phoenix_c6_reap — 사실만

- dea2e1853 빌드물(`cys-1116-integ/target/debug`)을 새 파일로 복사(차가움) vs 복사 후 `--version` 1회(데움)로 각 1~2회: **둘 다 같은 자리**(`queue.parked` 관측 `until` 8초 창)에서 붉음 · daemon_ready True · 잔재 0 → **첫 실행 탓 아님**. 원인 추적 = 조각 5 좌석 몫(여기선 안 함).
- 함정: 저장소 루트가 `/tmp/…` 면 `aliased_harness_root` 로 죽는다 → `/private/tmp/…` 로.

## ③ 제품 영향(코드 고침 0 · master#64fd3812 결정 = A안 → debt-d 이관 · B안 안 함)

- 새로 복사한 바이너리 첫 실행: integ 빌드 cys 중앙값 1.51s 최대 2.96s · cysd 2.26~2.44s / 설치본(서명) 사본 cys 1.30s 최대 2.29s · cysd 1.57s / 재실행 0.005~0.016s.
- 격리 데몬 + 역할 `cso-p3probe` 좌석 + 낡은 `CYS_ROLE=master`: 해소기(2s) 차가움 20회 중 **1회 env 폴백(master)** · 데움 20/20 데몬 권위 / capgate 훅 차가움 20/20 거부 유지(지연 +1.3~1.5s). 실사용 `cys list` 시험 좌석 0 · 잔재 프로세스 0.

## ④ 동반 3종 N=20

- 고친 판: refl_inject 20/20 · role_authority 20/20 · owner_desk 20/20 초록(유효 회차 기준 — 아래 사고 1회 제외 후 1회 추가).

## 2차 사고·함정

- 05:00 훑기 재시작 때 내 `rm -rf /tmp/fk.*` 가 ④ owner_desk 3회차의 임시 폴더를 지움(FileNotFoundError) → 무효 처리 · 1회 추가. 공용 접두 glob 삭제 금지 — 반복기마다 고유 접두(`fk.`·`ng1.`·`c6r.`·`p3.`)를 쓰고 자기 것만 지울 것.
- 첫 계측 사본은 셸 `'…'` 안에 파이썬 `repr` 의 홑따옴표가 들어가 래퍼가 SyntaxError(전 호출 rc 1) → 훑기 1회분 버리고 다시. 셸 홑따옴표 안 코드에 넣는 문자열은 큰따옴표로.
- zsh 에서 `$F`(여러 줄) = 한 인자 → `${=F}`.

## 📌 (2차)

1. dept_name_guard `test_create_spawn_loser_preserves_live_winner` 전체 파일 실행 중 1회 붉음(load 18.2) · 단독 묶음 40회 미재현 — 부하 때 경쟁 시험의 시간 여유 문제일 수 있음(추정 · 미측정).
2. python `Popen.wait/communicate` 시한·Rust 시험 쪽 스텁은 이번 계측 밖 — 같은 꼴이 남았을 수 있음.
3. 제품 preflight C82 가 만드는 cys 스텁도 첫 실행 비용을 시한 안에서 치른다(0.61s/5s · 여유 큼).
