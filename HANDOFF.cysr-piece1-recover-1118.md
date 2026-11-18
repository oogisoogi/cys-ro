# HANDOFF — TICKET=cysr-piece1-recover-1118 (조각 1 구현 첫 범위)

- 좌석 = worker-piece1 · surface:2240 · 가지 `feat/piece1-recover-1118` ← integ/1116(`b29cbdd89`)
- 브리프 = master#68a90f34 · 범위 결정 = master#9f7c835b(A: 핀 유지는 범위 밖)
- 구현 커밋 = `c03bccb80` · 1회 고침(master#267c6b97) = `59d755d9d` · `--resume-saved`(master#fbfe2389) = `94aeb1a4f` · codex 1R 고침(master#91f7d69b) = `fee25fbae` · codex 2R 고침(master#556f6d21 · 후임 좌석 surface:2245) = `153629ec9` · 독립 검증 지적 고침(master#e414b44b · 후임 좌석 surface:2248) = `7c3994a7f` `e518c01e1` `a9cbd0189`
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

rc 93 이 되는 경우: 다른 agent 의 핀 · 저장 cwd ≠ 좌석 cwd · 다른 좌석이 같은 대화 사용 중 · 한 역할에 서로 다른 핀 · 프로필을 믿을 수 없음 · 세션 파일 없음 · 재개 인자 없음 · 조회 실패 · 깨진 응답 · `saved_unreadable=true`.

### 1회 고침(`59d755d9d`)

| 불변식 | 구현 |
|---|---|
| 읽지 못한 묘비를 지우지 않는다 | 시작 때 파일 부재만 fresh. 그 밖의 읽기 오류면 `tombstones_unread=Some(해제 기록)`. 읽히게 된 첫 저장이 (디스크 − 해제 기록)을 메모리에 합친다(`adopt_unread_tombstones`). UTF-8 아님은 손상으로 격리 |
| 그동안 해제한 묘비는 되살리지 않는다 | 해제 입구를 `Daemon::remove_tombstone` 하나로 모음(`tombstone.set` · `claim_role` · 역할 좌석 생성). `tombstones` 락 아래에서 해제 기록과 합치기가 줄을 선다 |
| rev 는 줄지 않는다 | `tombstones_rev = max(메모리, 디스크)`. 직전 영속본을 디스크 묘비로 맞춰, 집합이 그대로면 rev 도 그대로이고 바뀌면 +1 |
| 합치기를 놓치지 않는다 | `persist_topology_if_dirty` 는 밀린 저장이 없어도 못 읽은 묘비가 있으면 돈다(watchdog 틱 · 종료 직전) |
| 못 읽은 목록을 「핀 없음」으로 읽지 않는다 | `system.topology` 에 `saved_unreadable`(읽기 오류·손상 = true · 부재 = false). 역할 좌석 `node-recover` 는 true 면 rc 93. 표시 없는 옛 데몬 응답은 지금과 같고, 역할 없는 좌석은 조회하지 않는다 |

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
- 1회 고침: 먼저 붉음 3건(`tombstones_unread_at_start_survive_the_first_readable_save` · `system_topology_marks_a_saved_list_it_could_not_read` · `p1_a_pin_that_cannot_be_resumed…` 의 「저장 목록을 못 읽음」) → 영향 범위 cys 41 통과 · 0 실패 · 1 무시 / cysd 102 통과 · 0 실패. 전체 수 cys 773 그대로(기존 시험에 사례 추가) · cysd 3331 → 3337.
- 1회 고침 뮤턴트 15개 전부 붉음(이름·사유 대조 · 빌드 6벌). 누적 33개.

## `--resume-saved` 고침(`94aeb1a4f`)

`launch-agent --resume-saved` 는 `saved_unreadable=true` 또는 조회 실패면 새 좌석을 만들지 않고 rc 93 으로 멈춘다. 표시 없는 응답의 빈 목록은 지금처럼 새 기동이다.

호출자 전수(`--resume-saved` 를 직접 쓰는 곳은 `javis_boot_node` 하나 · 저장소와 `~/.claude/channels/*.sh` 검색):

| 호출자 | 파일:줄 | rc 93 을 받으면 | 재시도 | 문구 | 새 대화 fallback |
|---|---|---|---|---|---|
| `javis_boot_node` | `cysjavis-pack/bin/javis_boot_node.py:1734~1738` | 바로 `resume_held` · 같은 코드 93 으로 끝남 | 없음 | stderr 마지막 줄 | **없음**(고침 전: 일반 실패로 흘러 `no_surface`·`takeover_failed` · rc 1) |
| 같은 파일의 옛 cys 재시도 | `:1730` | 해당 없음(rc 2 전용) | clap 문구일 때만 1회 | `cys 가 --resume-saved 를 모름` | **닫음**(고침 전: 프로필 불신 rc 2 도 플래그를 빼고 다시 띄웠다) |
| 편성 `_boot_node` | `javis_formation.py:847` · 기록 `:2063` · 시도 상한 `:2046` | 실패로 기록 | 다음 편성 심박 · 시도 원장 상한까지 | `기동실패=<역할>:resume_held/<사유>` | 없음 |
| 편성 master 자리 | `javis_formation.py:896~904` | 위와 같음 | 위와 같음 | 위와 같음 | **아래 경고** |
| 리뷰어 `_boot_one_node` · `cmd_boot_reviewers` | `javis_orchestra.py:1367` · `:1446~1458` | exit 93 = 영구 분류 | 없음 | `저장 대화를 잇지 못해 멈춤(exit 93)` | **닫음**(고침 전: transient 로 분류해 Claude 대체 리뷰어를 띄웠다) |

⚠ master 좌석이 없을 때 편성은 먼저 `new-surface --role master` 로 빈 좌석을 만든다(`:896`). 이 좌석이 저장되는 순간 핀이 지워지므로(핀 유지 범위), 목록이 다시 읽히면 다음 심박의 `--resume-saved` 는 「저장 대화 없음」으로 새 대화를 띄울 수 있다. rc 93 은 읽지 못하는 동안만 막는다. 코드 읽기까지다.

시험: 먼저 붉음 = cys `p1_resume_saved_holds_when_the_saved_list_is_unknown` · 팩 3건. 고친 뒤 cys `p1_` 9 통과 · 관련 소스 핀 3 통과 · `test_v115_dept` 68 OK · 관련 팩 시험 9파일 rc 0. 뮤턴트 7개 전부 붉음(누적 40개).

## codex 1R 고침(`fee25fbae` · master#91f7d69b)

codex = BLOCK(`~/axdev/master/reports/verify/piece1-recover-1118/codex-r1.verdict.md`). master 판정:

| 지적 | 처분 |
|---|---|
| #3 rev 역행 | **고침** · `load_start_tombstones` 한 번의 읽기로 묘비·rev·직전 영속본·못 읽음 표시를 시드(격리 때는 복구한 묘비 기준) · 정상 저장마다 직전 파일 rev 와 `fetch_max` |
| #1 시작 때 손상 격리 | blocker 아님 · 격리 때 피드 경고 1건만(문구 + 격리 파일 이름). 세대 스냅샷에서 핀 복구는 다음 범위 |
| #4 rc 79·91 | 그대로(새 대화 없이 멈추는 기존 계약) |
| #2 | 핀 유지 범위 · 1.1.16 조건표 |
| #5 | TODO |

시험: 먼저 붉음 2건(`a_save_never_moves_the_tombstone_rev_backwards` · `isolating_a_corrupt_topology_at_start_warns_once_with_the_file_name`) → 영향 범위 cysd 105 통과 · 0 실패. cysd 시험 수 3337 → 3340. 뮤턴트 4개 전부 붉음(누적 44개).

## codex 2R 고침(`153629ec9` · master#556f6d21)

codex = BLOCK(`~/axdev/master/reports/verify/piece1-recover-1118/codex-r2.verdict.md`). 범위 5건만 고쳤다.

| 항목 | 바뀐 것 | 먼저 붉은 시험 |
|---|---|---|
| 1 쓰기 실패 | `write_json_atomic` 실패면 `topology_dirty=true` · 성공해야 내린다 | `topology_dirty_is_set_by_a_failed_write_and_the_retry_lands`(표시를 미리 세우지 않음 · 옛 `topology_dirty_survives_a_failed_write` 를 대체) |
| 2 boot-node 선회수 | reap-launch 의 `close-surface --reap` 직전 `cys daemon resume-check --role <역할>`. 0 이 아니면 회수·기동 없이 `resume_held`·93. `unrecognized subcommand 'resume-check'`(옛 cys)만 종전대로 | 팩 `ReapLaunchChecksSavedListFirst` 2건 |
| 3 깨진 성공 응답 | `--resume-saved` 가 node-recover 와 같은 `recover_saved_pins` 로 판정. `saved` 부재·비배열 = 93 | `p1_resume_saved_holds_when_the_saved_list_is_unknown` |
| 4 핀 충돌 | `saved_pins_conflict` = 세션·cwd·프로필·agent 묶음 비교. 한쪽만 값이 없어도 충돌 | `p1_saved_pins_that_differ_on_any_axis_hold_with_rc_93` |
| 5 윈도우 cwd | `pin_path_key(경로, windows)` · 윈도우만 `claude_tui::normalize_profile_path` 로 접음 · 유닉스 값은 그대로 | `p1_pin_paths_fold_windows_spelling_only_on_windows` · `p1_windows_cwd_spelling_reaches_both_pin_checks` |

- 새 동사 `cys daemon resume-check` = 숨김 · 읽기 전용 · `system.topology` 만 부른다. 최상위 `Command` 인자는 j3 스택 넘침 전례가 있어 하위 동사로 달았다.
- **지시 없이 내린 판단**: 4번을 node-recover 뿐 아니라 `--resume-saved`·`resume-check` 에도 적용했다. 안 그러면 회수 전 확인은 통과하고 첫 항목을 임의로 잇는다.
- `같은 꼴` 훑기: `run_restore` 는 깨진 `saved` 를 빈 목록으로 읽지만 아무것도 띄우지 않고 끝난다(새 대화 없음). `run_pack_reinject` 계열은 표지 조회뿐이다. 둘 다 고치지 않았다.

남은 구멍(이번 범위 밖 · 고치지 않음):
- reap-launch 확인은 저장 목록·핀 충돌만 본다. 프로필을 믿을 수 없는 핀은 지금처럼 회수 뒤 `launch-agent` 가 rc 2 로 멈춘다(새 대화는 없지만 빈 좌석은 회수됨).
- `saved_resume_pin` 은 그 역할의 첫 항목만 본다. 첫 항목의 세션 칸이 비고 둘째에 세션이 있으면 지금처럼 「저장 대화 없음」이다.
- phoenix 의 빈 좌석 회수(`javis_phoenix.py:3848`)는 복원 시도 뒤의 다른 경로라 건드리지 않았고 판정도 하지 않았다.

시험(복구된 최종 코드):
- cys 51 통과 · 0 실패(`p1_` · `v115r5_restore_and_resume_saved_wiring` · `j3_cys_send_carries` · `aid_s5_reap_due` · `daemon` · `dept_status` 필터). cysd 34 통과 · 0 실패(`topology_dirty` · `topology_read_error` · `persist_if_dirty` · `non_utf8` · `dirty_topology_retry` · `tombstone` · `system_topology` 필터).
- 팩 `test_v115_dept` 93 OK · 관련 팩 시험 11파일 rc 0. `cargo check --bin cys --bin cysd` 통과.
- 전체 수: cys 781(+6) · cysd 3340(교체 1건이라 그대로).
- 뮤턴트 17개 전부 붉음(Rust 10 · 빌드 5벌 · 팩 7). 붉어진 시험 이름과 사유를 대조했다. 누적 61개.
- 보호 계수: 시작 syspolicyd 26 · fake 162 → 끝 24 · 147(늘지 않음).

## 독립 검증 지적 고침(`7c3994a7f` · `e518c01e1` · `a9cbd0189` · master#e414b44b)

VERIFY = `~/axdev/master/reports/verify/piece1-recover-1118/VERIFY.md`. B1·R1·R2·R3 을 고쳤다. R4·O2·O3·O4 는 범위 밖이라 그대로다.

| 항목 | 바뀐 것 |
|---|---|
| B1 데몬 | `Daemon::released_roles`(역할 → 거둔 좌석 · 메모리 전용). 회수 때 기록하고, `roles` 에 넣는 세 곳(claim · 재결합 · 좌석 생성)이 `note_role_held` 로 지운다. `surface.list` 의 `released_role` 로 내준다 |
| B1 되돌리기 | 새 RPC `role.restore_released {surface_id, role, session_id}`. 좌석이 같은 대화를 들고 있고, 묘비가 아니고, 표시가 그 좌석일 때만 역할을 돌려준다. 사망 시각을 지우고 저장한다. 역할을 쥔 읽기 전용 좌석은 거절 |
| B1 node-recover | `--surface`·`--role` 모두 거둔 역할로 핀을 판정한다. 이을 때만 C-u 전에 역할을 되돌린다. 핀 없음·묘비는 지금처럼 새 대화이고 역할을 되돌리지 않는다 |
| B1 boot | 거둔 좌석에 핀이 걸려 있으면 복구 경로. 좌석이 없으면 `--resume-saved` 판정. 93 이면 outcome `resume_held`(새 좌석 0 · 치명 아님 · boot rc 0 · bootstrap 표 = withhold) |
| R1 | `--resume-saved`·`resume-check --agent` = `launch_pin_verdict`(node-recover 와 같은 `recover_pin_verdict`). 저장 폴더가 있으면 거기서 잇는다. 세션 파일이 지워진 핀만 새 대화 |
| R2 | 역할 이름을 받았으면 핀 유무를 알기 전 실패는 rc 93. 좌석도 핀도 없을 때만 rc 1 |
| R3 | `resume-check` 는 자동 기동 금지 목록에 있다(`command_never_autostarts`) |

입구별 rc:

| 입구 | 상태 | 결과 |
|---|---|---|
| `node-recover --surface` · 거둔 좌석 | 이을 수 있는 핀 | 0 · `--resume` · 역할 되찾음 |
| 같음 | 못 잇는 핀 · 저장 목록 모름 · 역할 되돌리기 거절 | 93 · 입력 0 |
| 같음 | 핀 없음 · 묘비 | 0 · 새 대화 · 역할 없음(지금과 같음) |
| `node-recover --role` | 역할 좌석 없음 · 거둔 좌석 있음 | 위와 같음 |
| 같음 | 좌석 없음 · 핀 있음 또는 모름 | 93 |
| 같음 | 좌석 없음 · 핀 없음 | 1(지금과 같음) |
| 같음 | `resolve_role`·`surface.list` RPC 실패 | 93 |
| `node-recover --surface` · 역할 이름 없음 | `surface.list` 실패 | 1(지금과 같음) |
| `cys boot` | 거둔 좌석 + 핀 | `recovered` · 새 좌석 0 |
| 같음 | 거둔 좌석 없음 + 이을 수 있는 핀 | `launched` · `--resume` · 저장 폴더 |
| 같음 | 못 잇는 핀 · 저장 목록 모름 | `resume_held` · 새 좌석 0 · boot rc 0 |
| 같음 | 핀 없음 · 묘비 · 첫 설치 | `launched` · 새 대화(지금과 같음) |
| `--resume-saved` | 이을 수 있음 | 0 · 저장 폴더에서 잇는다 |
| 같음 | 다른 agent · 저장 폴더 소실 · 프로필 불신 · 다른 좌석 사용 중 | 93(프로필 불신은 전에 rc 2) |
| 같음 | 세션 파일 삭제 · 핀 없음 | 0 · 새 대화 |
| `resume-check --agent` | `--resume-saved` 와 같은 판정 | 0 또는 93 |
| `resume-check`(`--agent` 없음) | 저장 목록만 본다 | 0 또는 93 |
| `resume-check` · 데몬 없음 | 자동 기동 없음 | 93 |

시험·뮤턴트:
- 먼저 붉음 = cys 14건 · cysd 6건(의도한 사유 대조).
- 고친 뒤: cysd 66 통과 · cys 117 통과(영향 범위 필터) · 팩 10파일 rc 0. 전체 수 cys 781 → 796(+16 · `v115r5_saved_resume_pin_table` 삭제 −1) · cysd 3340 → 3348.
- 뮤턴트 43개: 42개 붉음(cysd 20 · cys 21 · 팩 1). 살아남은 cysd 1개(회수 때의 중복 정리)는 코드를 지웠다. cys C19 는 처음에 살아남아 시험을 보강한 뒤 붉음을 확인했다.
- `run_bootstrap_health.py` 는 400초 안에 끝나지 않아 **결과가 없다**.

확인 결과:
- seatkeep: 지금은 `--controller-bound` 라 데몬이 끝나면 좌석도 끝나고 입양이 없다. 거둔 역할은 메모리에만 있어 재시작을 넘을 일이 없다. **T4(입양)를 켜면** 좌석은 살고 표시는 사라져 B1 이 되살아난다(조건표 후보). 코드 읽기까지다.
- `role.reclaim_auto`: 복구된 좌석 자신이 부르면 역할·핀이 그대로다(시험). 다른 역할 없는 좌석은 복구 좌석의 `seat` 가 아직 `empty` 인 동안(다음 watchdog 틱까지 · 계정·폴더가 같고 비특권 역할일 때) 역할을 가져갈 수 있고, 그 좌석의 세션이 저장되면 핀이 덮인다. 사망 후 60초 안의 좌석과 같은 창이다. 고치지 않았다(조건표 후보 · 코드 읽기).
- 역할로 좌석을 찾는 다른 입구: `cycle-agent`·`reinject --role` 은 복구가 아니라 지금처럼 실패한다. `javis_boot_node` 는 `--resume-saved` 로 간다. watchdog 자동 재기동은 `node-recover --surface` 라 이번 수리를 받는다. phoenix `spawn_fresh_production` 은 핀 없는 `launch-agent`(독약 대체 경로)로 범위 밖이다.

X: `xprobe_impl.py` 에 `r0-late`·`boot-late` 추가. 문법 컴파일만 했고 **실행하지 않았다**. 직전 sha256 앞 16자 `6da957a895d21109` → `117eb32d62e15fe8` · diff = `piece1/x/xprobe_impl.delta-late.diff`.

## X 상태

- `0720c4097` 구현본에서 r0 fixed(끝 0) · r1 fixed(끝 0) · tomb fixed(끝 4 · 주기 잡 pid 칸 · master 수용) · unreadable 사전 점검 끝 2(미측정). 요약 = `piece1/x/RESULTS-impl.md`.
- ⚠ 위 X 와 master 의 `0904da71e` 통과는 codex 2R 고침 **이전** 코드다.
- 코드가 바뀌었으므로 **최종 커밋에서 네 시나리오를 각 1회 다시 돌린다.** master 의 「X 시작」 전에는 돌리지 않는다.
- 판독 규칙: 끝 코드 4 라도 어긋남이 `com.jarvis.cso-resource-sentinel` pid 칸 하나뿐이고 그 종료 코드가 0 이면 verdict 사용 가능. 그 밖의 어긋남은 즉시 정지.
- 사본 B 적용: 라이브 팩 대조에서 `state/evt_spool.jsonl` 만 제외. 직전 사본 대비 diff = `piece1/x/xprobe_impl.delta-r2.diff`.

## X 실측 준비(실행 안 함 · master 의 「X 시작」 대기)

- 원형 `xprobe.py` 는 바꾸지 않았다. 사본 = `~/axdev/workers/cysr-blocked5-redesign-1116/piece1/x/xprobe_impl.py` · diff = 같은 폴더 `xprobe_impl.diff`.
- 시나리오 = `r0`(세션이 등록된 좌석) · `r1` · `tomb`(①) · `unreadable`(② · `node-recover` + `--resume-saved`). 결과 폴더 = `out-impl`.
- 문법 확인만 했다. 사본은 한 번도 돌리지 않았으므로 시나리오 자체의 결함이 있을 수 있다.
- 실행 전 필요한 것: 구현본 빌드(`cargo build --bin cys --bin cysd --bin cys-seatkeep` · 새 Mach-O 3개 · master 통제) · 환경값 `CYS_X_START=master` · `CYS_X_IMPL_BIN=<폴더>` · `CYS_X_IMPL_COMMIT=<빌드 때 HEAD>`.
- 가짜 에이전트는 `/bin/sh` 가 아니라 기존 파이썬(`CYS_X_FAKE_INTERP` · 기본 `/opt/homebrew/bin/python3`)으로 돈다. `/bin/sh` 는 맥이 환경값을 숨겨 프로필이 `unobserved` 가 되고, 그러면 `r0` 이 다른 이유로 rc 93 이 된다(R0 원자료의 `config_dir_authority=unobserved` 로 확인).

## 남은 구멍

1. **복원 직후 세션 등록 전에 에이전트가 죽으면 여전히 새 대화다.** 새 역할 좌석이 생기는 순간 저장 핀이 지워진다(핀 유지 범위 · 격리 데몬 시험으로 실측).
2. **구현본 X 의 R0 는 가짜 에이전트가 세션을 등록하게 시험을 고쳐야 한다.** 이것은 xprobe 원형 재현과 다른 증거다. xprobe 원형을 그대로 돌리면 핀이 없어 새 대화로 나온다.
3. **그래서 이번 범위는 PLAN 의 「대화 사라짐」 전체를 닫지 않는다.**
4. 세션 파일이 정말 지워진 좌석은 rc 93 에 머문다(I8 은 다음 범위 · 되돌릴 수 있음).
5. boot 출력에서 93 은 아직 `recover_unrecognised` 로 보인다. `resume_held` 분류는 판정표 범위다.
6. 강제 종료는 밀린 저장을 잃는다(설계 L19).
7. 묘비를 아직 못 읽은 동안에는 메모리 묘비가 비어 있다. 그 사이 폐역 역할을 다시 띄우면 명시 재기동으로 치고 묘비가 풀린다(지금의 「역할 좌석 생성 = 묘비 해제」 규칙과 같다).

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
