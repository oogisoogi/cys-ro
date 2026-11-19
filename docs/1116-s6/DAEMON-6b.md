# 조각 6b — 팀별 기계 장치(데몬) · TICKET=cysr-1116-s6-1119

설계 정본 = `cysr-ui-research/P2-DESIGN.md` §16-2 ⑦~⑩ · §11 6b 행 · PRD FR-L7. LLM 팀장 0(10-09 정책). NFR-F3 예외(브리프 「데몬 변경 허용」).

## 1. 무엇을 만들었나

| # | 장치 | 데몬 쪽 이름 | 기본값 | 발효 조건 |
|---|---|---|---|---|
| 공통 | 팀 판정 | `team::team_of` = 명시 묶음(`Surface.group = Some(Some(g))`) > 좌석 **생성** cwd 마지막 이름(앱 `seatrows.ts folderKey` 와 같은 규칙) · master*·cso* = 팀 아님 | — | — |
| ⑦ | 팀별 대기열 몫 | 마스터 좌석(role == "master") 큐에 **검증된 발신 좌석**이 넣을 때 그 팀 항목 수 ≥ 몫 → 그 요청만 `queue_full_team`(사건 `team.queue_full`) | env `CYS_TEAM_QUEUE_SHARE` = 30(0 = 끔) · 전체 100 그대로 | 살아 있는 팀 ≥ 2 |
| ⑧ | 팀별 도우미 수 상한 | `surface.create {role:"worker"}` — 새 좌석 팀(파라미터 `group` > `cwd` 폴더 > 홈 폴더) 의 살아 있는 worker 수 ≥ 상한 → `team_worker_limit_exceeded`(사건 `team.worker_limit_denied`) | env `CYS_MAX_TEAM_WORKERS` = 0(무제한) | 상한 > 0 |
| ⑨ | 팀 정지 스위치 | 새 메서드 `surface.group_pause {group, paused}`(호출자 = `surface.set_group` 과 같은 게이트) · 사건 `team.paused`/`team.resumed` · CLI `cys seat-group-pause <팀>` / `cys seat-group-resume <팀>` | 꺼짐 · 메모리 전용 | 늘 |
| ⑩ | 【진행】 보고 묶음 | 큐 보내기 파라미터 `kind:"progress"`(CLI `cys send --queued --progress`) 단 마스터 좌석 큐 항목 = 그 팀 가장 오래된 꼬리표 항목이 창을 채우면 그 팀 꼬리표 항목 전부를 **1건**(머리 `【진행 묶음】 <팀> N건` + `[i/N · 발신] 원문` 순서대로) | env `CYS_PROGRESS_BUNDLE_SECS` = 600(0 = 묶지 않음) | 팀 ≥ 2 ∧ 본문에 【확인요청】【질문】【결정필요】【경고】【막힘】 없음 |
| 읽기 | `team.stats` | `{teams:[{team, live_seats, live_workers, working, report_ts[]}], paused[], distinct, window_secs, volatile:true, note}` · CLI `cys team-stats`(JSON 한 줄 · 데몬 오류 = exit 1 + stderr) | 링 팀별 5000 · 7일 | 늘(읽기 · 호출자 제한 없음) |

### 배달 자리(⑨⑩) — 어떻게 「다른 팀을 막지 않게」 했나
- 꼬리표(팀 · progress)는 **넣을 때** 정하고 데몬 메모리 `Daemon.teams`(TeamBook · 대상 좌석 → 항목 id → 꼬리표)에 둔다. QueueEntry 구조체·WAL 꼴 = 무변경(직렬화 호환 걱정 0). 데몬이 다시 켜지면 꼬리표가 비어 그 항목은 **지금 동작(즉시)** 으로 나간다(안전 쪽).
- `deliver_head_locked` 앞(잠금 밖) `team_pre_delivery`:
  1) 대상 좌석의 팀이 정지 중이면 `Freeze` = 이번 배달 0(그 팀 좌석으로 가는 큐 동결).
  2) 머리가 **보류**(정지 팀이 넣음 · 안 풀린 【진행】)이고 뒤에 보낼 항목이 있으면 큐를 **안정 재배치**(보낼 것 먼저 · 각 무리 안 순서 유지) → 이번 틱은 거름(`drop_stale_launch_lines` 의 「머리가 바뀌면 이번 틱 거름」 규칙과 같음 · 준비 판정이 옛 머리로 내려졌으므로). 인계 예약(`inject_reserved`)·반쯤 쓴 머리(`queue_hold`)가 있으면 손대지 않는다. 재배치 뒤 `persist_queue_state`(잠금 밖).
- 임계영역 안: 머리가 보류면 배달 0 · 머리가 풀린 【진행】이면 그 팀 【진행】 묶음(`bundle_pick` · 상한 = 기존 다이제스트 항목 상한) · 같은 발신자 병합 후보에 보류 항목이 나오면 거기서 끊는다(연속 구간 규칙 유지).
- 운영자 강제 배달(`forced = true` · `queue.deliver`)은 팀 판정을 모두 건너뛴다(지목한 항목 1건이 그 명령의 계약).

## 2. 바뀐 원작자 파일 줄(NFR-F3 예외 보고 · 커밋 8c90f7860 기준 `git diff -U0 dea2e1853..8c90f7860`)

| 파일 | 줄(새 판) | 무엇 |
|---|---|---|
| src/bin/cysd/main.rs | 74~75 · 8205~8208 | `mod team;` · `#[cfg(test)] mod team6b_tests;`(파일 끝 규약) |
| src/bin/cysd/state.rs | 5081~5082 · 7142 | `Daemon.teams: TeamBook` 필드 + 초기값 1줄 |
| src/bin/cysd/handlers.rs | 4808~4833(4곳) | `enqueue_bound_body` — 계획(잠금 밖) · 몫 판정(같은 큐 잠금 안) · `queue_full_team` 응답 · 꼬리표 기록 |
| 〃 | 7469~7475 | `surface.create` ⑧ 게이트(기존 active-limit 뒤 · 인증 게이트 ⑤ 앞) |
| 〃 | 7995~8025(3곳) | `surface.send_text queued` — 계획 · 몫 판정 · 꼬리표 기록 |
| 〃 | 9553~9580 | 새 메서드 `surface.group_pause` · `team.stats` |
| src/bin/cysd/governance.rs | 13139~13184 | `TeamPre` · `team_pre_delivery`(정지 좌석 동결 · 재배치) |
| 〃 | 13216~13225 | `deliver_head_locked` — 팀 ≥ 2 판정(잠금 밖 1회) + `team_pre_delivery` 호출 |
| 〃 | 13307~13327 · 13341~13346 · 13361~13365 | 임계영역 — 보류 머리 거름 · 묶음 고르기 · 병합 끊기 · 묶음 본문 |
| src/bin/cys.rs | 99~101 | `cys send --progress` 플래그 |
| 〃 | 3417~3423 · 3444~3452 | `SeatGroupPauseArgs` · `VendorAuxCommand::{SeatGroupPause, SeatGroupResume, TeamStats}`(Args 구조체 · 단위 변형 = 스택 사고 회피 자리) |
| 〃 | 3721~3733 · 6460~6462 · 6499~6504 · 6679~6683 | `seat_group_pause` · send 의 `kind` 실기 2곳 · 새 동사 분기 |
| 〃 | 38657 · 38751 · 38823 · 38840 · 45464 | 소스 핀 시험 앵커 문자열(`Command::Send { … progress, … }`) 갱신 — 뜻 불변 |

- 새 파일(원작자 아님): `src/bin/cysd/team.rs`(판정·장부 · 단위 시험 7) · `src/bin/cysd/team6b_tests.rs`(RPC·배달 핀 10).

## 3. 시험

격리 = `env -i HOME=/tmp/s6h TMPDIR=/tmp/s6t PATH=/usr/bin:/bin:/usr/sbin:/sbin:~/.cargo/bin` · `CARGO_BUILD_JOBS=6→4`(master 부하 공지 뒤) · `--test-threads=4` · cargo 1건씩. 출력 원문 = `/tmp/s6o/{cysd,cys,lib}.txt`.

| 대상 | 기준선(브리프 「직전 통합 값」) | 이 가지(8c90f7860) | 차이 사유 |
|---|---|---|---|
| `cargo test --bin cysd team` | — | **47 / 0**(새 17 = team.rs 단위 7 + team6b_tests 10 · 나머지 30 = 이름에 team 이 든 기존 시험) | — |
| `cargo test --bin cysd`(전체) | 3308 · 0 · 17 ign | **3348 · 3 · 17 ign**(총 3368) → 붉음 3 = `seat_proc::tests::seatkeep_input_ack_stall_ends_seat_when_consumer_never_resumes` · `seatkeep_input_ack_waits_while_consumer_runs_and_stdin_unread` · `seatkeep_stalled_consumer_does_not_block_close` — 사유 전문 `seatkeep 이 접속을 거절: {"reason":"handshake_timeout"}`(seat_proc_tests.rs:384·307) · 실행 중 부하 15~19 · **단독 재실행(부하 14.8 · `seatkeep_` 5건 `--test-threads=1`) = 5 / 0** | 통합 인계서 §4-1 의 같은 시험 이름·같은 사유 문구(`handshake_timeout` 흔들림) · 이 가지는 seat_proc 무접촉 · 새 시험 17 + dea2e1853 이후 기준 수 변화는 이 좌석이 따로 재지 않음 |
| `cargo test --bin cys`(전체 · 스택 시험 포함) | 765 · 0 · 2 | **796 · 0 · 2** | `cli_parse_stack_need_stays_within_budget` · `cli_parse_fits_2mib_plus_64kib_stack_guard…` · `aid_s5_reap_due…` · `j3_*` 전부 ok — `--progress` 플래그(인라인 변형 필드 1)·새 동사 3(Args 구조체·단위 변형)이 스택 예산 안 · 수 차이(765→796) 는 dea2e1853 까지 들어온 시험(이 좌석 새 시험 0) |
| `cargo test --lib` | 1256 · 0 · 3 | **1268 · 0 · 3** | lib 무접촉(바뀐 파일 = bin 만) |

### 3-1. 뮤턴트(환경값 분기 1빌드 · `P1M=mN` · 끝나면 `git checkout` · 결과 원문 = 이 좌석 실행)

| 뮤턴트 | 무엇을 끄나 | 붉어진 시험(이름까지) |
|---|---|---|
| 없음 | — | 10 / 0 |
| m1 | ⑦ `share_over` 늘 false | `t7_share_rejects_only_the_flooding_team` |
| m2 | ⑧ `team_worker_gate` 늘 통과 | `t8_team_worker_limit_denies_only_that_team` |
| m3 | ⑨ 정지 팀 좌석 동결(`TeamPre::Freeze`) 무시 | `t9_pause_freezes_delivery_to_team_seats` |
| m4 | ⑨⑩ 보류 머리 거름 + 재배치 끔 | `t9_pause_holds_team_items_without_blocking_others` · `t10_progress_items_bundle_after_the_window` |
| m5 | ⑩ `bundle_pick` 늘 None | `t10_progress_items_bundle_after_the_window` |
| m6 | ⑦ 팀 1개에도 몫 발효 | `t7_share_inert_with_a_single_team` |
| m7 | ⑩ 급한 머리표 판정 끔 | `t10_progress_items_bundle_after_the_window` |

- 7 뮤턴트 전부 **의도한 시험**이 잡음(엉뚱한 시험이 붉어진 것 0).

## 4. 한계 · 남은 위험(정직)
- **데몬 메모리 전용**: 정지·꼬리표·보고 시각 = 데몬 재시작 때 비움. 정지는 풀린 채 돌아오고(사람이 다시 멈춰야 함), 보류였던 【진행】 항목은 꼬리표가 사라져 **즉시** 나간다(묶음 없이 · 유실 0) · team.stats `report_ts` 가 비어 promote-check 의 R·D 가 적게 셈(= 덜 묻는 쪽).
- **앱의 사람 묶음 기록**(localStorage `cys-seat-group`)은 데몬이 모른다 — 데몬 재시작 뒤 앱이 다시 정하기 전까지 그 좌석은 폴더 이름 팀으로 셈.
- ⑦ 은 **큐 경로만**: 직접 보내기(`cys send` 기본 · 큐 아님)는 몫과 무관(설계 §16-2 「마스터 좌석 대기열」). 큐 Return(`send-key --queued`)은 몫·꼬리표 밖(입력줄에 이미 쓴 글의 제출이라 거절·보류하면 입력줄에 글이 남는다).
- ⑨ 보류 항목이 오래 남으면 큐 머리 나이 기반 `queue.starved`(600초)가 정지 팀 항목으로 울릴 수 있다(전부 보류일 때만 · 정지는 사람이 건 것).
- ⑩ 묶음은 같은 팀 【진행】 사이에 끼어 있던 그 팀의 꼬리표 없는 항목보다 먼저 나갈 수 있다(창이 찬 시각 = 가장 오래된 【진행】 시각 기준).
- 다른 좌석으로 옮기는 큐(rehome) 뒤에는 꼬리표가 따라가지 않는다(옮긴 항목 = 즉시 · 안전 쪽).
- `surface.create` ⑧ 은 `role:"worker"` 요청만(기존 active-limit 과 같은 범위) — `launch-agent --role worker-3` 처럼 번호 붙은 역할 요청 경로가 이 문자열을 쓰는지는 기존 active-limit 과 같은 한계.

## 5. 검증 지적 고침(master#c4bc0244)

근거 = 독립 검증 `workers/cysr-1116-s6-verify-1119/VERDICT.md`(M1·M2·m3·m4·m5·m6·i7). 검증 좌석의 반례 시험 V1~V8b 를 `src/bin/cysd/team6b_verify_tests.rs` 정식 시험 모듈로 들였다(main.rs 끝 `mod team6b_verify_tests;` · 파일 끝 규약). B1·X2~X9(화면)·i8~i11 은 이 고침 범위 밖(lead 결정).

### 5-1. 항목별

| # | 바꾼 것 | 시험 | 뮤턴트(고침을 끄면) |
|---|---|---|---|
| M1 묶음 글자 상한 | `team::bundle_pick` 에 `sizes`(발신 라벨·원문 글자 수)·`max_chars` 인자 — 같은 발신자 병합(`plan_queue_merge` R1-major-4)과 같은 규칙: 후보를 더한 **최종 렌더**(`render_bundle`) 글자 수가 `queue_digest_max_chars` 를 넘으면 멈추고 남은 것은 다음 배달로 이월 · 머리 1건은 늘 배달. 호출 = `deliver_head_locked`(`queue_digest_max_chars()` 넘김) | `v2_bundle_respects_digest_char_cap`(1,500자 5건 → 묶음 2건 3,059자 · 3건 이월 · 큐에서 잘림 0) · `team::tests::hold_rotate_and_bundle`(상한 20자 = 머리만) | V2 · hold_rotate_and_bundle 붉음 |
| M2 팀 정지 TTL 크레딧 | `queue_expiry_pass` — `system.pause`·좌석 큐 정지와 **같은 식**(`paused_total_secs += delta.min(alive_for)`)을 팀 정지에도: 정지된 팀 **좌석의** 큐(⑨ 동결) = 전부 · 그 밖 좌석 = 정지 팀 꼬리표 항목만. 데몬·좌석 정지가 이미 크레딧을 준 틱은 겹쳐 주지 않음(`else if`) | `v8_team_pause_gets_ttl_credit`(7시간 팀 정지 → 만료 0 · 큐 1) · `v8b_system_pause_control_keeps_entry`(대조 · 그대로 초록) · `v8c_team_pause_credit_scope`(새 · 정지 팀 좌석 큐 = 크레딧 · 정지 안 된 팀 항목 = 종전대로 만료) | V8 · V8c 붉음 |
| m3 승계·이관 뒤 꼬리표 | `TeamBook.tags` 를 「대상 좌석 id → 항목 id」에서 **「항목 id → 꼬리표」**로(항목 id `q<시작 시각>.<번호>` = 데몬 한 실행 안에서 유일 · `migrate_seat_queue`·`inherit_parked_queue`·rehome·주차가 id 를 그대로 옮김) → 원작자 이관 함수 무접촉으로 꼬리표가 항목을 따라감. `tags_for(live)` = 읽기 전용. 청소 = 새 `team::sweep_daemon_tags`(큐 틱마다 `queue_expiry_pass` 끝 1회 · 좌석 활성·만료 큐 + `parked_queues` + `restored_queue` 의 id 를 잠금 하나씩 모음) → `TeamBook::sweep_tags` 가 **연속 2번** 안 보인 꼬리표만 지움(옮기는 도중·넣는 도중 한 번 빠진 것은 살림) | `v7_master_succession_keeps_team_tags_and_pause`(승계 뒤 보류 · 청소 2회 뒤에도 보류 · 재개 = 새 마스터 좌석에 1회 배달) · `team::tests::tags_follow_entry_id_and_sweep_needs_two_misses` | m3(이관된 id 의 꼬리표를 버림) = V7 붉음 · m3g(1번 안 보이면 지움) = 단위 시험 붉음 |
| m4 재시작 = 정지 소실 신호 | 정지 **이름 목록만** 상태 폴더 `team-paused.json` 에 원자 쓰기(`cys::atomic_write_json` · 빈 목록 = 파일 지움 · `surface.group_pause` 가 바뀌었을 때만 · 쓰기 직렬화 잠금 안에서 최신 목록을 다시 읽어 씀). `Daemon::new` 끝(버스가 선 뒤) `team::announce_lost_pauses` = 파일에 이름이 있으면 사건 `team.pause_lost {teams, reason:"daemon_restart", note:"팀 정지가 풀렸어요 …"}` **1건** + 파일 지움. 정지는 되살리지 않음(영속 = 1.1.17) | `v9_restart_announces_lost_pause_once`(새 · 정지 2팀 → 재시작 사건 1건 · teams = ["a","z"] · 정지 목록 빈 채 시작 · 파일 지움 · 다음 재시작 사건 0 · 정지→재개 = 파일 없음) | V9 붉음 |
| m5 이어진 구간만 | `bundle_pick` 이 큐 전체에서 같은 팀 【진행】을 건너뛰며 모으던 것을 **머리에서 이어진 구간**만(다른 항목을 만나면 멈춤 · codex R1-blocking-3 과 같은 규칙) | `v6_bundle_keeps_other_team_fifo`(바꿈: 첫 배달 = p1 만 · 둘째 = b1 · 셋째 = p2) · `hold_rotate_and_bundle`(p1·n1·p2 = [0] · p1·p2·n1 = [0,1]) | V6 · hold_rotate_and_bundle 붉음 |
| m6 급한 머리표 = 몫 밖 | `EnqueuePlan.urgent`(본문에 【확인요청】【질문】【결정필요】【경고】【막힘】) → `share_over`·`share_exceeded` 가 몫 판정을 건너뜀 · 전체 100 상한은 그대로 | `v10_urgent_item_exempt_from_team_share`(새 · 【진행】 30건으로 몫 참 → 보통 = `queue_full_team` · 머리표 5종 + 꼬리표 단 【막힘】 = 들어감) · `share_counts_only_that_team` | V10 · share_counts_only_that_team 붉음 |
| i7 ceo = 고정 좌석 | `is_fixed_role` 에 `ceo`·`ceo-*`(alert_route.rs `CLEAR_SIGNAL_ROLES = ["master","ceo"]` 와 같은 급) → 팀 아님 · 팀 정지로 얼지 않음. 리뷰어 좌석·역할 없는 셸 = 그대로(기록만 · V1·V1b 가 지금 동작을 핀) | `v5_ceo_role_seat_is_fixed_not_frozen_by_team_pause`(바꿈: 배달됨) · `team_of_explicit_then_folder_and_fixed_none` | V5 · team_of 단위 시험 붉음 |

- 시험 이름을 바꾼 것(결함 단언 → 고친 동작 단언): `v5_ceo_role_seat_can_be_frozen_by_team_pause` → `v5_ceo_role_seat_is_fixed_not_frozen_by_team_pause` · `v6_bundle_overtakes_other_team_fifo` → `v6_bundle_keeps_other_team_fifo` · `v7_master_succession_drops_team_tags_and_leaks_paused` → `v7_master_succession_keeps_team_tags_and_pause` · `v8_team_pause_gets_no_ttl_credit` → `v8_team_pause_gets_ttl_credit`. V2 는 이름 그대로 · 이월 단언 추가(이 검체의 `sleep` 좌석은 긴 본문 배달을 확정하지 않아 이어진 배달은 단위 시험이 핀). V7 은 재개 호출자를 새 마스터 좌석으로 다시 묶음(옛 좌석은 역할을 잃어 호출자 게이트 밖).
- 그대로 둔 것: V1 · V1b · V3 · V3b · V4 · V8b(기록된 동작·대조).

### 5-2. 뮤턴트(환경값 분기 1빌드 · `P1M=<이름>` · `cargo test --bin cysd team` · 끝나면 고침 전 사본으로 되돌림 · `git diff` 에 P1M 0)

| 뮤턴트 | 끄는 것 | 붉어진 시험(이름까지) |
|---|---|---|
| 없음 | — | 62 / 0 |
| M1 | 글자 상한 판정 | `v2_bundle_respects_digest_char_cap` · `team::tests::hold_rotate_and_bundle` |
| M2 | 팀 정지 크레딧 갈래 | `v8_team_pause_gets_ttl_credit` · `v8c_team_pause_credit_scope` |
| m3 | 이관(`drain_active_except_inflight`)된 id 의 꼬리표 무시 = 옛 좌석 묶음 동작 | `v7_master_succession_keeps_team_tags_and_pause` |
| m3g | 청소 2회 규칙 → 1회 | `team::tests::tags_follow_entry_id_and_sweep_needs_two_misses` |
| m4 | 재시작 알림 | `v9_restart_announces_lost_pause_once` |
| m5 | 이어진 구간 → 건너뛰기(옛 동작) | `v6_bundle_keeps_other_team_fifo` · `team::tests::hold_rotate_and_bundle` |
| m6 | 급한 머리표 몫 예외 | `v10_urgent_item_exempt_from_team_share` · `team::tests::share_counts_only_that_team` |
| i7 | ceo 고정 좌석 | `v5_ceo_role_seat_is_fixed_not_frozen_by_team_pause` · `team::tests::team_of_explicit_then_folder_and_fixed_none` |

- 9 회 전부 의도한 시험만 붉음(엉뚱한 시험 0).

### 5-3. 바뀐 원작자 파일 줄(이 고침 · `git diff -U0` 기준 새 판 줄)

| 파일 | 줄 | 무엇 |
|---|---|---|
| src/bin/cysd/governance.rs | 13160 · 13312 · 13320~13326 | `tags_for` 새 서명 2곳 · 묶음 고르기에 `sizes`·`queue_digest_max_chars()`(M1·m5) |
| 〃 | 14277~14278 · 14327~14331 · 14351~14365 | `queue_expiry_pass` 팀 정지 크레딧(M2) |
| 〃 | 14529~14530 | `queue_expiry_pass` 끝 꼬리표 청소 호출(m3) |
| src/bin/cysd/handlers.rs | 4815 · 4832 · 8006 · 8024 | `share_over`·`note_enqueued` 새 서명(좌석 id 인자 뺌 · m3) |
| 〃 | 9569~9570 | `surface.group_pause` — 바뀌었을 때 `persist_paused`(m4) |
| src/bin/cysd/state.rs | 7159~7160 | `Daemon::new` 끝 `announce_lost_pauses`(m4) |
| src/bin/cysd/main.rs | 8209~8212 | `mod team6b_verify_tests;`(파일 끝 규약) |

### 5-4. §4 한계 중 바뀐 줄
- 「데몬 메모리 전용 · 정지는 풀린 채 돌아오고」 → 정지는 여전히 풀린 채 돌아오지만(영속 = 1.1.17) 사건 `team.pause_lost` 1건이 난다. 꼬리표·보고 시각은 그대로 메모리 전용.
- 「rehome 뒤에는 꼬리표가 따라가지 않는다」 → 따라간다(항목 id 로 묶음 · 승계·주차 상속·rehome 공통).
- 「⑩ 묶음은 … 꼬리표 없는 항목보다 먼저 나갈 수 있다」 → 이어진 구간만 묶으므로 **머리에서** 묶음이 시작될 때만이다. 다만 ⑩ 재배치(보류 머리를 뒤로)가 창 안에서 그 팀 【진행】을 꼬리표 없는 항목 뒤로 보내는 것은 그대로(설계).

### 5-5. 남은 위험(정직)
- M2: 역할 주차(`parked_queues` · 좌석이 승계 전에 죽음)·복원 보존소 행에는 팀 정지 크레딧이 없다(주차 TTL 은 항목 `enqueued_at` 기준 별도 규칙) — 정지 팀 항목이 주차 TTL 을 넘기면 종전대로 버려짐(이벤트 `queue.dropped parked_expired` 는 남).
- M2: 크레딧은 틱(5초) 해상도 · 정지 전이 1회당 ≤1틱 오차(기존 `system.pause` 크레딧과 같은 잔여).
- m3: 꼬리표 청소는 큐 틱마다 모든 큐의 id 를 모은다(꼬리표 0 이면 비용 0). 꼬리표가 있는 동안 좌석 수 × 큐 길이(상한 100) 만큼 id 복사 — 지금 규모(좌석 수십)에서 무시할 크기로 보나 실측은 안 했다.
- m4: 파일 쓰기 실패(디스크) = 로그 1줄 · 그때는 재시작 사건이 빠질 수 있다(최선 노력). 데몬이 정지 목록을 쓴 직후 죽으면 사건 1건 · 쓰기 전에 죽으면 0건.
- m6: 급한 머리표 항목은 몫 밖이라, 한 팀이 머리표만 붙여 보내면 그 팀은 전체 100 까지 채울 수 있다(설계 ⑦ 의 「폭주 차단」이 머리표 항목엔 없음 · lead 결정).
- i7: 앱 seatrows 의 같은 규칙은 lead 가 따로 바꾼다(이 커밋은 데몬만) — 그 전까지 화면과 데몬의 ceo 판정이 다르다.

### 5-6. 시험(격리 `env -i HOME=/tmp/s6fh TMPDIR=/tmp/s6ft` · `CARGO_BUILD_JOBS=4` · `--test-threads=4` · cargo 1건씩)
| 대상 | 고침 전(이 가지 · §3) | 고침 뒤 | 차이 사유 |
|---|---|---|---|
| `cargo test --bin cysd team` | 47 / 0(검증 V 시험 미편입) | **62 / 0** | + V1~V8b 11 · 새 V8c·V9·V10 3 · 새 단위 1 |
| `cargo test --bin cysd`(전체) | 3348 · 3(seatkeep `handshake_timeout` 흔들림 · 단독 초록) · 17 ign | **3366 · 0 · 17 ign**(960초 · 끝 부하 18.7) | + 새 시험 15 · 이번엔 seatkeep 3건도 초록 |
| `cargo test --bin cys` | 796 · 0 · 2 | 안 돌림 | cys.rs 무접촉 |
