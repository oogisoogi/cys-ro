# HANDOFF — TICKET=cysr-1116-skt1-1119 (seatkeep T1 · 대화 작성자 하나 → 1.1.16 위로 · codex r5c BLOCK 4 고침)

## 0. 맨 앞 — T1 공개 함수(T4·T5 좌석 2267 이 갈아끼울 자리 · 같은 대화 작성자 하나 보장)

노브 = 환경 `CYS_SESSION_LEASE`(`off`·`0`·`false`·`no` = 끔 · **없으면 켬** = `sl::enabled_from(None) == true` · 원 T1 그대로 — 📌 아래 덧붙임 1).
`sl` = `cys::session_lease`(leaf · `src/session_lease.rs`) · CLI 접착 = `src/session_lease_cli.rs`(cys 바이너리 안 `pub(crate)`).

| 쓰임 | 이름·시그니처 | 뜻 |
|---|---|---|
| **복원 입구 관문(T4 입양이 부를 자리)** | `pub(crate) fn lease_gate(role: &str, sess: Option<&str>, surface_id: Option<u64>, cfg: Option<&str>, claim_dir: Option<&std::path::Path>) -> LeaseGate` | 좌석을 **만들기·잇기 전에** 그 대화의 임대를 잡는다. `LeaseGate::Off`(노브 끔·대화 없음 = 종전) · `Proceed(Option<sl::Guard>)`(진행 · None = 바깥이 이미 쥠) · `Refuse { rc: i32, line: String }`(rc 92 = 산 작성자 · 93 = 판정 불가 · 좌석 0 · 새 대화 폴백 0) |
| 마무리 | `lease_finish_by_rc(g: Option<sl::Guard>, rc: i32, made: Option<u64>, sess: &str)` · `lease_finish_ready(g, seat, sess)` · `lease_settle_after_error(g, seat, write_unknown)` | 기동 결과로 임대를 작성 중(held · 작성자 = 그 좌석 자손 argv) / 결과 불명(unknown@좌석) / 되돌림 |
| 잡기(leaf) | `pub fn acquire(store: &Store, id: &str, cx: &AcquireCtx) -> Decision` · `AcquireCtx { me: Holder, surface_id: Option<u64>, daemon_gen: Option<String>, cfg: Option<String>, world: &dyn World }` | `Decision::{Granted(Guard), AlreadyMine, Live{who}, Undecided{reason,next}}` — 잠금 안 판정 → 잡은 **뒤** 바깥 증거(데몬 live · argv) |
| 등록 따라가기 | `pub fn follow(store, id, writer: &Holder, surface_id: Option<u64>, daemon_gen: Option<String>, w: &dyn World) -> Follow` · CLI `lease_follow_on_register(surface_id: u64, transcript: &str)` | SessionStart 등록 뒤 임대를 작성자 신원으로 옮김(**좌석 최상위 훅으로 증명 안 된 것만 · 헬퍼·도구 셸 = 안 옮김** · 이번 고침) |
| **좌석의 현재 대화(이번 신설)** | `pub fn seat_bound_conversation(store: &Store, surface_id: u64, daemon_gen: &str, probe: &dyn Fn(&Holder) -> Liveness) -> Result<Option<String>, String>` · CLI `pub(crate) fn seat_conversation_now(sid: u64, gen: &str) -> Result<Option<String>, String>` | claude 좌석 = 산 작성자에게 묶인 작성 중 임대(등록 문자열 아님) · 그 밖 에이전트 = 데몬 관측(topology) · 모름 = Err |
| **대화가 산 작성자에게 있나(이번 신설 · 앱 「복원됨」)** | `pub fn held_by_live_writer(store: &Store, id: &str, probe: &dyn Fn(&Holder) -> Liveness) -> Result<Option<(u64, Option<String>)>, String>` | (좌석 · 데몬 세대) |
| 저장소 | `Store::open(&sl::default_root(&cys::home_dir(), cfg!(windows), LOCALAPPDATA))` · `pub fn probe_holder(h: &Holder) -> Liveness` | 임대 폴더 = `~/.local/state/cys/session-leases`(사용자 단위 · 데몬 여럿이 공유) |

⚠T4 가 알아야 할 전제(원 T1 HANDOFF 함정 그대로 · 지금 base 에 T3 이 들어와 있다): `CliWorld::seat` 는 「임대의 데몬 세대가 다르면 그 좌석은 데몬과 함께 내려갔다」를 전제한다(T1 = 좌석이 데몬과 함께 SIGHUP). **좌석 보유 장치(T3 `--controller-bound` · T4 입양)가 켜지면 이 전제가 깨진다** — 입양한 좌석이 이어 쓰는 대화는 **입양 시점에 그 대화 임대를 다시 확인**(`lease_gate` 또는 `acquire` 로 새 세대·새 좌석 번호를 적기)해야 한다(DESIGN-seatkeep-t1 T0 §3 단계 4). 지금 T3 노브(`CYS_SEATKEEP`)는 기본 끔이라 실제로 깨지는 길은 없다.

## 1. 커밋(feat/1116-skt1 · 기준 dea2e1853 · push 0)

| 커밋 | 내용 |
|---|---|
| `0eff2a6f1` | port — 원 가지 feat/seatkeep-t1 `270e3e21e..e2f2ae889`(67 커밋) 누적 diff 3-way 적용 · 충돌 해소(1.1.16 동작 우선 · 아래 §2) |
| `51c556a1c` | 팩 검체 `test_phoenix_seatkeep_t1_lease_hold` 3완전 레인 5루프 등재(ci-branch 2 · release 2 · pack-release 1) |
| `022af8b16` | r5c BLOCK 4 고침(§3) |
| `be40d9036` | r5c #1 e2e 재현 2 + 픽스처 수리(가짜 claude 가 시험 cys 를 부름 · 훅 이름 셸 아래 등록) |
| (다음) | boot_node 임대 거절 시험 · 뮤턴트 결과 · 이 HANDOFF |

## 2. 옮기기(port)에서 1.1.16 쪽과 맞춘 것

- **rc 93 겹침**: 1.1.16 조각 1(cysr-piece1-recover-1118)이 93 = `EXIT_RESUME_HELD`(저장 대화를 지키려고 멈춤 · 새 대화 0)로 먼저 썼고, T1 은 93 = `EXIT_SESSION_LIVENESS_UNKNOWN`(생존 판정 불가 · 좌석 0)이다. 둘 다 「멈춤 · 새 대화 0 · 파괴 회수로 올리지 않음」 이라 **같은 값을 공유**하고 주석을 고쳤다(`src/bin/cys.rs` EXIT 표). 가르는 곳은 줄 모양(임대 거절 줄 `· 역할: 대화 <id> … 띄우지 않음`)뿐이다.
- `run_launch_agent_resume_saved`: 조각 1 의 `RecoverPin` 구조를 그대로 두고 `Resume` 갈래에만 `lease_gate`/`lease_finish_by_rc`.
- `run_launch_agent_opts` 반환 = `(rc, 만든 좌석)` · agy 좌석 문이 첫 동작인 것 유지(`return (rc, None)` · agy 배선 핀 문자열 고침).
- `run_node_recover`: 조각 1 의 `resume_held`·핀 갈래 유지 + 임대 관문(대화 = 핀 또는 좌석 기록).
- `run_boot` 좌석 없는 기동(1.1.16 신규 = `--resume-saved` 경유): rc 92 도 `resume_held`(비파괴) — 종전엔 「failed」(치명)로 셌을 자리.
- `javis_boot_node.py`: 92 또는 93+임대 거절 줄 = `resume_refused`(사유 writer_live/liveness_unknown) · **끝 코드 93**(원 T1 은 1 이었음 → 1.1.16 의 「93 = 파괴 회수 안 함」 계약에 맞춤) · 그 밖 93 = 조각 1 `resume_held`.
- e2e RN 3번째 좌석: 조각 1 `launch_pin_verdict` 가 임대보다 먼저 「다른 좌석이 저장 대화를 잇고 있다」(93)로 멈춤 → 기대 rc = 92|93(불변식 = 새 좌석 0 · 작성자 1).
- 배선 핀 이름 유지를 위해 `RecoverPin::Resume { session: sid, .. }` 로 묶음.

## 3. r5c BLOCK 4 처분(판정문 `~/axdev/master/reviews/codex-queue-2026-11-13/r4/3-seatkeep-t1.r5c.verdict.md`)

| # | 판정문 요지 | 고침(파일) | 증거 |
|---|---|---|---|
| 1 blocking | 낡은·가짜·헬퍼 등록으로 unknown@W 풀림 → 둘째 작성자 | ① 풀림 판독 `CliWorld::seat_conversation` = `seat_conversation_now`(claude = **산 작성자 결속 임대** · 등록 문자열 아님) ② follow 가 「좌석 최상위 훅 아님」 증명 등록을 안 옮김(`follow_lineage_not_top` → leaf `lineage_proves_not_top_hook` = cysd 같은 표) ③ `.jsonl` 폴더 거름 | e2e **FR**(좌석 밖 `cys usage-register --surface W`) = rc 92 · **SR**(T 등록 → 에이전트 교체 → 훅 없는 claude) = rc 92 · leaf `seat_binding_is_the_live_writers_held_lease_only` · `registration_lineage_tells_top_hook_from_helpers` · 헬퍼 = 단위(계통 판정 표)+배선 핀(e2e 없음 — 아래 측정 대기) |
| 2 blocking | 등록 S 를 읽고도 #1 방어 통과 → W2 | `role_seat_verdict` 3값: 이 대화 신호(topology·데몬 등록·현재 증거 = S 하나라도) = 거절 · 「다른 대화」 = 현재 대화 증거만 · 그 밖 = 확인 못 함(93) · 재반환 판정(`lease_judge_reused_seat`)도 같은 원천 | 진리표 `role_seat_verdict_truth_table`(등록 S → ThisConversation) · 등록 직후 수집기 전 창의 실 e2e 는 없음(시간 창 · 결정론 재현 못 함) |
| 3 major | Tauri `restore_judge_two` 가 휴리스틱 핀 8자 접두로 첫 93 을 「복원됨」 | 「복원됨」 = `held_by_live_writer`(작성 중 · 작성자 생존) + 같은 데몬 세대(`system.identify`) + 그 역할 **점유** 좌석 · 거절 줄 대화 표기 = **전체 id**(`short()` = 전체 · phoenix·앱 판독 같은 꼴) | Tauri `seatkeep_r5_3_first_unknown_is_kept_until_that_conversation_is_seen`(휴리스틱 핀 재현 → unknown 1 유지 · 다른 세대·다른 역할·빈 좌석 = 유지 · 판정 층이 session_id·starts_with 를 안 읽는 핀) |
| 4 major | codex 좌석(등록 경로 없음) 93→92 고착 | 다른 에이전트 좌석 = 후보 아님 · 등록 경로 없는 에이전트 = 데몬 관측(topology) 기준(관측 T = 진행 · S = 거절 · 없음 = 93) · 93 안내 = 사유·에이전트별(「기다리면 풀림」은 등록 전 claude 좌석에서만) | 진리표(codex 관측 T = Clear · 다른 에이전트 = Clear) |

판정문의 「검토했지만 문제없다」·「확인하지 못한 것」 중 이번에 손대지 않은 것: ⓓ `run_sidecar_restore_judged` 안쪽 15초 대기 회차 확인(피해 미확인 · 그대로) · `worker`/`worker-N` 불일치 통과(이번 차이 무관).

## 4. 시험(숫자 · 2026-11-20 · 맥 부하 12~38 · CARGO_BUILD_JOBS=4)

| 묶음 | 전(port 직후 0eff2a6f1) | 후 |
|---|---|---|
| `cargo test --lib session_lease` | 22 ok | **24 ok**(새 2) |
| `cargo test --bin cys session_lease_cli_tests` | 25 ok · 1 붉음(배선 핀 이름 — port 고침) | **26 ok** |
| `cargo test --test session_lease_e2e`(SLE_ROUNDS=3) | 8 ok · 1 붉음(RN 3번째 = 조각 1 93) | **11 ok**(FR·SR 새 2) — 최종 전체 재실행 §6 |
| `cargo test -p cys-app --bins seatkeep` | 10 ok | 10 ok(r5_3 재작성) |
| 팩 `test_phoenix_seatkeep_t1_lease_hold.py` | OK | OK(R5 전체 id) |
| 팩 `test_v115_dept.V115r5T3BootNodeResumesSaved` | 25 | **26 ok**(임대 거절 시험 새 1) |
| 레인 대조(rehearsal · CI 스텝) | — | rc 0 · 비대칭 0 |

뮤턴트: §5. 전체 시험·CI 팩 단계 전/후: §6.

## 5. 뮤턴트(소스 변이 → 시험 → 되돌림 · 붉은 시험 이름까지)

| # | 변이 | 결과 | 붉은 시험 |
|---|---|---|---|
| M1 | 풀림 원천을 데몬 등록 문자열로 되돌림(r5b 꼴) | KILLED | e2e `an_outside_fake_registration_never_frees_the_saved_restore` · `a_stale_registration_after_an_agent_swap_never_frees_the_saved_restore` |
| M2 | follow 계통 거름 줄 삭제 | KILLED | `session_lease_cli_tests::role_seat_verdict_truth_table`(배선 핀) |
| M3 | #1 방어의 「데몬 등록 = S」 신호 삭제(r5c #2) | KILLED | `role_seat_verdict_truth_table` |
| M4 | 다른 에이전트 좌석 건너뜀 삭제(r5c #4) | KILLED | `role_seat_verdict_truth_table` |
| M5 | Tauri 「복원됨」 = topology 8자 접두(옛 꼴) | KILLED | cys-app `seatkeep_r5_3_first_unknown_is_kept_until_that_conversation_is_seen` |
| M6 | 결속 판독이 작성자 생존을 안 봄(낡은 결속) | KILLED | lib `session_lease::tests::seat_binding_is_the_live_writers_held_lease_only` |
| M7 | boot_node 임대 거절 갈래 끔(`if False`) | KILLED | 팩 `test_v115_dept…test_lease_refusals_stop_as_held_without_a_plain_launch` |

(M1 첫 실행은 cargo 필터 인자 2개 오류로 무효(rc 1 · 시험 0) → 필터 1개로 다시 돌린 결과다.)

## 6. 전체 시험(기준선 dea2e1853 대비)

(아래 채움)

## 7. 함정(이번에 새로 밝힌 것)

- **e2e 가짜 claude 의 `cys` = 설치본이었다**: 좌석 셸이 로그인 셸(zsh -l)이라 path_helper 가 PATH 를 재정렬 → 상자 PATH 앞의 시험 cys 가 아니라 `/usr/local/bin/cys`(설치본 · T1 없음)가 등록을 했다. 그래서 원 T1 의 e2e 등록 길은 **T1 follow 를 한 번도 안 거쳤다**(r5b RV 초록 = 데몬 등록 문자열 풀림 덕). 고침 = 픽스처 env `FAKE_CYS`(시험 cys 절대 경로). 설치본이 상자 소켓·상자 HOME 으로만 말해 실 데몬·실 HOME 영향은 없었다(env HOME=상자 · CYS_SOCKET=상자).
- 가짜 claude 의 미룬 등록(FAKE_REG_GATE)이 **같은 실행 파일의 fork 자식**에서 돌면 계통이 「에이전트 2개 = 헬퍼」 로 보여 follow 가 거른다 → 자식은 `sh`(이름 session-start.sh)로 exec.
- 좌석에 사람처럼 치기 = `surface.send_text` + `"human": true`(에이전트 쓰기 관문을 안 탐) · 줄 끝 `\r`.
- 시험 좌석 env 는 데몬 env 를 물려받는다(FAKE_* 는 Box_ cmd 에서 데몬에 실어야 좌석까지 간다).

## 8. 재현

```bash
cd ~/axdev/.wt/cys-1116-skt1
E="env -i RUSTUP_HOME=$HOME/.rustup CARGO_HOME=$HOME/.cargo CARGO_BUILD_JOBS=4 PATH=$HOME/.cargo/bin:/usr/bin:/bin:/usr/sbin:/sbin HOME=/tmp/sk1h TMPDIR=/tmp/sk1h USER=$USER LANG=en_US.UTF-8"
eval $E cargo test --lib session_lease -- --test-threads=4
eval $E cargo test --bin cys session_lease_cli_tests -- --test-threads=4
eval $E SLE_ROUNDS=3 cargo test --test session_lease_e2e -- --test-threads=4 --nocapture
eval $E CYS_PACK_DIR=/tmp/sk1h/pk cargo test -p cys-app --bins seatkeep -- --test-threads=1   # ui/dist·src-tauri/binaries 자리표시(CI 와 같게)
```
