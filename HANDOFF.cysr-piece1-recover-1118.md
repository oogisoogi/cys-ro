# HANDOFF — TICKET=cysr-piece1-recover-1118 (조각 1 구현 첫 범위)

- 좌석 = worker-piece1 · surface:2240 · 가지 `feat/piece1-recover-1118` ← integ/1116(`b29cbdd89`)
- 브리프 = master#68a90f34 · 범위 결정 = master#9f7c835b(A: 핀 유지는 범위 밖)
- 구현 커밋 = `c03bccb80`
- 설계 판정 BLOCK 은 그대로다. 이 커밋은 그것을 풀지 않는다. 병합 조건 = X 실측 · 독립 검증 좌석 · 구현 diff codex 1R.

## 바뀐 것

| 내용 | 자리 |
|---|---|
| `node-recover` 가 좌석 역할의 저장 핀(세션·cwd·프로필·agent)으로 잇는다. 판정은 C-u 전 | `src/bin/cys.rs` `recover_pin_verdict` :25458 · `run_node_recover` :25530 |
| 역할 없는 좌석은 `system.topology` 를 부르지 않는다 | 같은 함수의 `pin_lookup` |
| 핀 경로만 `restore=true`(핀의 프로필을 명령줄에 싣는다 · 준비 대기 상한은 restore 와 같은 값) | 같은 함수 |
| 핀이 있는데 못 이으면 rc 93. 핀이 걸린 좌석의 뒤이은 일반 실패·`LaunchFailed` 도 93 | `EXIT_RESUME_HELD` :1730 · `recover_failure_exit` :25521 |
| 읽기 오류 = 격리 없이 저장 건너뜀 + `topology_dirty` + 경고 1건 | `src/bin/cysd/governance.rs` `persist_topology` :3335 |
| 다시 시도 = watchdog 틱 · 정상 종료 직전 | `persist_topology_if_dirty` :3513 · 틱 :191 · `main.rs` :1551 |
| 파싱 실패 · UTF-8 아님 = 지금처럼 격리 | `read_persisted_entries` |

rc 93 이 되는 경우: 다른 agent 의 핀 · 저장 cwd ≠ 좌석 cwd · 다른 좌석이 같은 대화 사용 중 · 한 역할에 서로 다른 핀 · 프로필을 믿을 수 없음 · 세션 파일 없음 · 재개 인자 없음 · 조회 실패 · 깨진 응답.

## 호출자별 rc

| 입구 | node-recover 결과를 어떻게 쓰나 | rc 93 일 때 | 근거 |
|---|---|---|---|
| `cys boot` 죽은 좌석 복구 | 0 복구 · 78 관문 보류 · 79 거부 · 91 결과 미상 · **1 만 회수** · 그 밖 = 비파괴 | `recover_unrecognised` · 회수·새 좌석·입력 0 · 팩은 withhold · boot 종료 코드 그대로 | `cys.rs` :15133 · :15491 · 시험 `p1_boot_treats_a_held_pin_as_non_destructive` |
| cysd watchdog 자동 재기동 | 종료 코드를 보지 않는다 · `CYS_AGENT_AUTORESTART=1` 일 때만(기본 끔) | 새 대화가 뜨지 않는다. 3회 뒤 `agent.exit_unrecoverable` + 좌석 원장 poison | `governance.rs` :1160 · 코드 읽기만 |
| 사람이 직접 실행 | 종료 코드 + stderr | stderr 에 사유 + `node-recover 보류` | 시험 |
| `docs/agy-door-evidence/acceptance.py` :418 · `docs/pending_input_e2e/run_recover_e2e.py` :291·:317 | 검증 스크립트 | 핀이 없는 좌석이면 영향 없음 | 코드 읽기만 · 돌리지 않음 |
| 팩 파이썬 · 앱 · 화면 | 호출 없음(문구·허용 목록뿐) | 해당 없음 | grep |

## 시험

- 먼저 붉음(고치기 전 코드): cys `p1_` 6건 중 4건 적 · 나머지 2건은 고치기 전에도 초록인 대조군 · cysd `topology_read_error_skips_the_save_and_loses_nothing` 적.
- 고친 뒤(영향 범위만): cys 41 통과 · 0 실패 · 1 무시 / cysd 36 통과 · 0 실패.
- 전체 수: cys 767 → 773 · cysd 3325 → 3331(둘 다 무시 포함 · 추가한 시험 수).
- 뮤턴트 18개 전부 붉음. 붉어진 시험 이름과 사유를 대조했다. 묶음 6벌은 서로 다른 시험에 걸리는 것만 묶었다.
- 보호 계수 syspolicyd 26 · fake 162 불변(시작 · 각 실행 · 끝).

## 남은 구멍

1. **복원 직후 세션 등록 전에 에이전트가 죽으면 여전히 새 대화다.** 새 역할 좌석이 생기는 순간 저장 핀이 지워진다(핀 유지 범위 · 격리 데몬 시험으로 실측).
2. **구현본 X 의 R0 는 가짜 에이전트가 세션을 등록하게 시험을 고쳐야 한다.** 이것은 xprobe 원형 재현과 다른 증거다. xprobe 원형을 그대로 돌리면 핀이 없어 새 대화로 나온다.
3. **그래서 이번 범위는 PLAN 의 「대화 사라짐」 전체를 닫지 않는다.**
4. topology 를 못 읽는 동안 `system.topology` 는 저장 목록을 빈 배열로 준다(`load_topology`). 그때 `node-recover` 는 「핀 없음」으로 보고 새 대화를 띄운다. 조회 오류 처리는 다음 범위다. 코드 읽기만.
5. 데몬이 topology 를 못 읽는 채로 시작하면 묘비를 빈 집합으로 읽고(`load_tombstones_from_disk`), 회복 뒤 저장이 파일의 묘비 목록을 비운다. 코드 읽기만.
6. 세션 파일이 정말 지워진 좌석은 rc 93 에 머문다(I8 은 다음 범위 · 되돌릴 수 있음).
7. boot 출력에서 93 은 아직 `recover_unrecognised` 로 보인다. `resume_held` 분류는 판정표 범위다.
8. 강제 종료는 밀린 저장을 잃는다(설계 L19).

## 돌리지 않은 것

전체 시험 묶음 · health · 윈도우 빌드 · 실제 claude · `cys boot` 전체 경로(가짜 데몬으로만) · X 실측 · codex.

## 다시 돌리기

새 작업트리는 형제 `target/debug` 를 `cp -c -R -p` 로 복제해 전체 빌드를 피했다. 시험 env 는 `env -i` + 짧은 `HOME`·`TMPDIR` + `CARGO_TARGET_DIR=<작업트리>/target`.

```bash
cargo test --bin cys -- p1_ --test-threads=4
cargo test --bin cysd -- topology_read_error persist_if_dirty topology_dirty non_utf8 dirty_topology_retry --test-threads=4
```

## 판단 기록

- `spawn-worker.sh:1291` 은 이번 범위에 필요 없다. `launch-agent` 판정을 바꾸지 않았기 때문이다. `launch-agent --role` 에 「핀 있으면 93」이 들어가는 범위에서 다시 본다.
- 라이브 소켓 접촉 금지에 따라 `cys set-status`·`cys todo-path` 를 쓰지 않았다. 같은 이유로 `~/.cys/pack` 장기기억 증류를 하지 않았다.
