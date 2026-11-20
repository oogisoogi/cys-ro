# HANDOFF — TICKET=cysr-1116-skt1-1119

> ★후임(worker-1116skt1b) 델타 = **§12**(codex 1R BLOCK 6 + 독립 검증 V1·V2·V3·V5·V6 + 고아 0 · 공개 함수 바뀐 것 §12-0) · 아래 §0~§11 은 앞 좌석 기록(§11-2 설계는 §12 로 집행됨)
> codex 1R = **master 대기열**(master#5a93bd10 · codex 5h 한도 소진 · 리셋 06:29 · 호출 0회) · 질문지 = `CODEX-1R-PROMPT.cysr-1116-skt1-1119.md`
 (seatkeep T1 · 대화 작성자 하나 → 1.1.16 위로 · codex r5c BLOCK 4 고침)

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
| `5eb2e306f` | boot_node 임대 거절 시험 + HANDOFF 초판 |
| `78b90a2e8` | 조각 1 p1 하네스 = 임대 노브 끔(9 붉음 → 0) + 노브 켬·임대 조회 불통 = 비파괴 보류 시험 |
| (이 커밋) | HANDOFF 시험 숫자 · 한계 · 📌 · codex 질문지 · TODO |

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

## 6. 전체 시험(기준선 dea2e1853 대비 · 같은 조건 = env -i · 격리 HOME · CARGO_BUILD_JOBS=4 · 아래 스레드)

기준선 = 작업트리 `~/axdev/.wt/cys-1116-skt1-base`(detached dea2e1853 · target = 형제 복제). 두 판을 같은 시각대에 나란히 돌림(00:57~02:44 · 부하 12~38).

| 묶음(CI ci-branch 맥 레인과 같은 명령) | 기준선 dea2e1853 | HEAD | 비고 |
|---|---|---|---|
| `cargo test --lib`(스레드 4) | 1268 ok · 0 붉음 | **1292 ok** · 0 | +24 = session_lease leaf 시험 |
| `cargo test --bin cys`(스레드 4) | 796 ok · 0 | 1차 813 ok · **9 붉음**(조각 1 `b360_tests::p1_*`) → 고침 `78b90a2e8` 뒤 p1 묶음 33/33 ×2(1회 차 새 시험 1 붉음 · 로그 미포착 → 사유 단언 일반화) · 전체 재실행 = 아래 줄 | 붉음 원인 = p1 가짜 데몬이 임대 조회(`system.identify`)에 빈 값 → 임대 93(비파괴 보류) · 운영 결함 아님 · 하네스에서 노브 끔 + 노브 켬 비파괴 시험 1 |
| `cargo test --bin cysd`(스레드 4 · CI 와 같은 skip) | 3330 ok · **3 붉음**(`seat_proc::tests::seatkeep_*` handshake_timeout) → 부하 8 단독 재실행 **5/5 초록** | **3333 ok** · 0 | 데몬 소스 변경 0줄(`git diff dea2e1853 -- src/bin/cysd` 빈 값) · 기준선 붉음 = 시간 문턱 · 부하성 |
| `cargo test --test update_drainhold_e2e`(스레드 1) | 4 ok | 4 ok | 가짜 claude 픽스처 바뀜 → 회귀 없음 |
| `cargo test --test rotate_autorestore_hold`(스레드 1 · ⚠CI 레인 밖 = 로컬 추가 측정 · §12-2 V3 정정) | 11 ok | 11 ok | 같음 |
| `cargo test -p cys-app --bins`(스레드 1 · CI 자리표시) | 348 ok | **358 ok** · 0 | +10 = T1 앱 시험 |
| `cd ui && bun test` | 3835 · 0 fail · 123 파일 | **3840 · 0 fail** · 124 파일 | +5 = restoredone.test.ts |
| `bunx -p typescript@7.0.2 tsc -p tsconfig.check.json` | rc 0 | rc 0 | 음성 대조(일부러 TS2322) = rc 1 확인 |
| 팩 단계(ci-branch 맥 레인 스텝 그대로 떼어 실행 · `set -e` 만 풀어 검체마다 rc 기록 · env -i · PATH=/usr/bin:/bin:/usr/sbin:/sbin · 격리 HOME) | 검체 152 · rc≠0 = 5(`test_hook_r34` · `test_pyseal_negative_specimen` 미측정 · `test_role_authority` · `test_v116_auto_restore_status` · `test_owner_desk`) | 검체 **153**(+T1 phoenix 검체 = OK) · rc≠0 = 4(`test_session_start_hook` · `test_hook_r34` · `test_pyseal_negative_specimen` 미측정 · `test_owner_desk`) | 판별 아래 ▼ |
| `cargo test --test session_lease_e2e`(CI 레인 밖 · SLE_ROUNDS=3 · 스레드 4) | 해당 없음(T1 없음) | **11 ok** · 0(최종 HEAD 재실행 · 277s) | 📌 CI 레인에 없음 |
| `cargo test --bin cys`(스레드 4) **전체 재실행**(78b90a2e8 뒤) | 796 ok | **823 ok · 0 붉음** | +27 = T1 CLI 시험 + p1 새 1 |

▼ 팩 rc≠0 판별(공지 master#eff2a4ce·c75895ba: 시간 문턱 붉음 = 부하 낮을 때 단독 재실행 대조 · 새로 쓴 실행 파일 첫 exec 지연 의심):
- `test_pyseal_negative_specimen` = **두 판 같은 사유 원문**: 「ⓒ 음성 대조 인터프리터 해소 — in-tree 로 쓰는 비번들 python 이 없다(Xcode·/usr/bin python3 = pycache_prefix 격리 HOME)」 = 러너 환경(UNMEASURED · rc 2) · CI 러너엔 비번들 python 있음.
- `test_owner_desk` = 두 판 같은 사유(`R8Codex2R.test_app_flush_per_item_budget_and_request_id` · 예산 시간 문턱) · 단독 재실행도 두 판 붉음(부하 8~9).
- `test_hook_r34` = 두 판 모두 시한 사례(HEAD = WIN-2 3.00s · 기준선 = RCF-3·RCF-4a 1s 시한) — 시한 축만 붉음 · 대상 훅 파일 이 좌석 변경 0.
- `test_session_start_hook`(HEAD 만 팩 회차에서 붉음) → 단독 재실행 두 판 **초록** · 기준선도 첫 팩 회차(set -e)에서 11x-a~c 붉었음 = 흔들림.
- `test_role_authority`(기준선만 팩 회차 붉음 · HEAD 단독 2회 붉음) → **번갈아 4회씩**: HEAD 초록·붉음·붉음·초록 / 기준선 초록·붉음(3건)·초록·… — 두 판 공통 흔들림 · 붉은 사례가 매번 다름(8a·8f·15e·8n·G10-7c · 모두 스텁 cys 첫 실행) · 대상 파일(javis_role·org·snapshot) 이 좌석 변경 0.
- `test_v116_auto_restore_status`(기준선만) → 단독 재실행 기준선 붉음 2/2(PermissionError: 기준선 target/debug/cysd) · HEAD 초록 2/2 — 기준선 작업트리 환경 · HEAD 영향 아님.
- 결론: HEAD 가 새로 붉힌 팩 검체 = **0**(측정 근거 위 · 「기준과 같다」 = 사유 원문·사례 대조).

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

## 9. 남는 한계(숨기지 않음 · codex 1R 물음 2 에 같은 목록)

1. **등록 실패 창**: 같은 claude 프로세스가 좌석 안 `/resume S` 를 했는데 그 SessionStart 훅의 `cys usage-register` 가 실패하면(데몬 불통 등) 결속이 옛 T 로 남아 「W = T」로 읽힌다 → S 새 좌석이 열릴 수 있다. 종전(데몬 등록 문자열)도 같은 창이었고, 데몬 등록이 실패하면 follow 도 안 돈다(둘 다 낡음). 막으려면 에이전트 자신의 현재 대화를 읽는 길(claude 세션 파일 열람 fd 등)이 필요 — 이번 범위 밖.
2. **계통 판독 불가(None) = 옮김**: argv 를 못 읽은 사슬(윈도우 MSYS 조상 단절 등)은 헬퍼 증명이 아니라 종전처럼 follow 한다(데몬 재핀 기준과 같은 실패 방향). 그 경우 헬퍼 등록이 결속을 덮는 길이 남는다.
3. **비-claude(codex 등) = 데몬 관측 기준**: 등록 경로가 없어 topology `session_id`(lsof 직독 · 실패 시 휴리스틱 폴백)를 「다른 대화」 증거로 쓴다 — 데몬 세션 파일 결정이 등록을 우선하는 길(usage.rs)로 좌석 밖 가짜 등록이 관측을 덮을 수 있다. claude 처럼 결속하려면 codex 쪽 신원 결속 장치가 따로 필요.
4. **훅 없는 claude 좌석**: 결속이 생기지 않으므로 같은 역할 S 복원 옆에서 언제나 93(→ 그 좌석이 사는 동안 92). 수용된 보수 처분(r5c 질문 5(b)) 그대로 · 안내 문구는 「기다려도 안 풀림 → read-screen·닫기」로 고쳤다.
5. 등록 직후·수집기 핀 전 창(r5c #2)의 **실 e2e 없음** — 시간 창이라 결정론 재현 못 함 · 진리표(순수)로만 잰다.
6. 헬퍼(`claude -p`) 등록의 **실 e2e 없음** — 계통 판정 표(leaf 단위)·배선 핀·뮤턴트 M2 로만 잰다.

## 10. 📌 덧붙임(브리프 밖 · master 판단)

1. **노브 기본값** → master#e08a16c0 ① = **켬 유지**(독립 검증의 거짓 거절 빈도 실측이 근거 · 나쁘면 다시 판단) · ③ rc 93 공유 = 유지. 옛 서술: `CYS_SESSION_LEASE` 는 **없으면 켬**(원 T1 그대로). 1.1.15 는 T1 을 「끔으로만」 싣기로 했었고(원 HANDOFF 매듭 절) 1.1.16 은 전 구성 탑재 방침 — 켬 그대로 낼지 끔 기본으로 낼지 master 결정. 끔이면 CLI 임대 길은 종전과 같고, 멱등 키 접미 1줄·앱 쪽 복원 알림 묶음은 노브와 무관(원 HANDOFF 「노브 끔 ≟ 1.1.14」 절).
2. ~~`tests/session_lease_e2e.rs` 는 CI 레인에 없다~~ → **master#e08a16c0 ② = 등재함**(ci-branch 맥 레인 · 스텝 「cargo test --test session_lease_e2e」 · 스레드 2 · 시한 20분 · 근거 = 로컬 실측 시험 422s·빌드 포함 472s · 부하 12~17 · CI 러너 실측은 첫 회차) · 옛 서술:(ci-branch 의 cargo 레인 = --lib · --bin cys · --bin cysd · update_drainhold_e2e · cys-app). T1 의 실 데몬 증거(FR·SR·RV·UW·RN 등 11개)가 CI 에서 안 돈다 — 레인 편입은 CI 설계 결정이라 손대지 않음.
3. **rc 93 공유**(§2): 조각 1 `EXIT_RESUME_HELD` 와 임대 `EXIT_SESSION_LIVENESS_UNKNOWN` 이 같은 값 — 소비자는 「멈춤 · 새 대화 0」 으로 같게 읽는다. 따로 가르려면 새 rc(94) 배정 = 계약 변경.
4. 기존 e2e 의 「설치본 cys 로 등록」 사실(§7)은 원 T1 의 r5b RV 판정 근거를 약하게 만든다 — 이번 고침 뒤 RV 는 시험 cys 로 초록(결속 경로).

---

## 11. 【매듭 델타】 codex 1R(8114319c4) = BLOCK(blocking 4 · major 2) — master#bea6fddc 「전부 고친다」 · 이 좌석은 CTX 52%(07:0x)라 고치지 않고 설계·판정 축만 남김

- 판정문 원문 = `~/axdev/master/reports/verify/codex-1120/skt1-r1.md`(표 (a)~(e) 포함) — 후임 첫 행동 = 이 절 + 그 원문 Read.
- 상한 3h(master#bea6fddc) · CTX 60% 매듭 · codex 2R = master 대기열(직접 호출 금지).

### 11-1. ★판정 축 표 — 「이 경로는 lease 없이(1.1.15)도 작성자 둘인가 / lease 가 새로 만든 것인가」(master 가 기본 켬 유지를 이 표로 다시 정함)

근거 = 코드 대입(실행 실측 아님 · 확신도 중상). 1.1.15 = 임대 없음 → `cys restore`·`--resume-saved` 는 topology live 에 S 가 **보일 때만** 겹침을 막는다(`restore_claim_for_launch` live 집합 · 조각 1 `launch_pin_verdict` 「다른 좌석이 잇고 있다」). 좌석 W 가 좌석 안 `/resume S` 로 S 를 쓰는데 topology 가 T/없음이면 1.1.15 는 언제나 W2 를 만든다.

| codex 1R # | 결과(판정문) | lease 없이(1.1.15)도? | lease 가 새로 만든 것? | 피해 종류 |
|---|---|---|---|---|
| 1 계통 None 에서 헬퍼 등록이 결속을 옮김 | rc 0 · 작성자 2 | **예** — 같은 장면(W 가 S · topology T/없음)에서 1.1.15 는 아무 검사 없이 W2 | 아니오(lease 가 대부분 순서를 막고 None 갈래만 남김) · 단 「같은 writer 의 held S 를 지움」은 lease 고유 동작 | 데이터 비가역(작성자 둘) |
| 2A 방어 판독 뒤 정상 S 등록 도착(경합) | rc 0 · 작성자 2 | **예**(1.1.15 는 판독 자체가 없음) | 아니오 | 데이터 비가역 |
| 2B 같은 프로세스 /resume S · 등록 실패 | rc 0 · 작성자 2 | **예** | 아니오(옛 T 결속이 「다른 대화」 증거가 되는 것은 lease 고유이나, 1.1.15 는 그 증거 없이도 W2) | 데이터 비가역 |
| 3 비-Claude topology 가 좌석 밖 가짜 등록으로 덮임 | rc 0 · 작성자 2 | **예**(1.1.15 는 topology T 면 그냥 W2) | 아니오(같은 결함을 새 증거 원천이 물려받음) | 데이터 비가역 |
| 4 Tauri held→topology TOCTOU 로 첫 93 지움 | 앱 성공 · S 작성자 0 | 결과 종류는 **예**(1.1.15 는 93 자체가 없고 역할 skip = 성공 표시 · r4 #3 원 결함) | 경합 자체는 **예**(새 다단계 증거) | 복원 누락 숨김(데이터 손실 아님) |
| 5 헬퍼/낡은 등록 S 가 실제 결속 T 를 이김 | rc 93 반복 · 작성자 0 | 아니오(1.1.15 는 막지 않음) | **예** | 거짓 막힘(가용성) |
| 6 시험이 위 순서를 안 잡음 | — | — | — | 증거 공백 |

⇒ 요지(확신도 중상): **lease 켬은 1.1.15 대비 작성자 둘 경로를 새로 만들지 않는다**(1·2A·2B·3 은 1.1.15 에도 있고 lease 는 그중 대부분 순서를 막은 뒤 남은 것). lease 가 새로 만든 것 = **거짓 막힘(5)** · **앱 성공 오접힘의 새 경합(4 · 결과 종류는 1.1.15 와 같음)**. ⚠예외 후보 1줄: 1 의 「follow 가 같은 writer 의 기존 held S 를 지움」 은 lease 에만 있는 동작 — 다만 그 뒤 W2 가 생기는 것은 1.1.15 와 같은 귀결이라 「새 작성자 둘」은 아님.

### 11-2. 고침 설계(후임 · master 처분 1~6 순서)

1. **계통 3값**: leaf `lineage_proves_not_top_hook` → `enum Lineage { ProvenTop, NotTop, Unknown }`(argv 하나라도 못 읽음 = Unknown). `lease_follow_on_register` 는 **ProvenTop 에서만** follow(같은 writer 의 옛 임대 지우기도 그 안). 귀결 = 계통이 안 읽히는 좌석(윈도우 MSYS 등)은 결속이 안 생겨 같은 역할 S 복원 옆에서 93(거짓 막힘 · 안전 쪽) — HANDOFF·안내 문구에 적을 것. 시험 = leaf 표 Unknown 행 + 배선 핀 `== Lineage::ProvenTop` + 뮤턴트(Unknown 허용).
2. **스냅샷 뒤 등록·등록 실패**(2A·2B):
   - (권고) **S 대화 파일 신선도 관문**: #1 방어·unknown 풀림·재반환 판정 모두에서 저장 대화 S 의 jsonl(claude = `<cfg>/projects/<slug>/<S>.jsonl` · codex = rollout)의 mtime 이 「결속 at」 또는 「복원 시작 − N초」보다 새것이면 = 누군가 S 를 쓰는 중 → 92. 좌석 안 /resume S 가 실제로 쓰기 시작한 뒤의 2A·2B·1·3 을 모두 기계적으로 막는다(등록 경로 무관). 남는 창 = resume 직후 첫 쓰기 전 — 그것은 아래 재확인으로 좁힌다. 파일 경로는 조각 1 핀 판정(`launch_pin_verdict`)이 이미 쓰는 세션 파일 해소를 재사용.
   - **생성 직후·기동 글 직전 재확인**: `run_launch_agent_opts` 에서 surface.create 뒤 `boot_agent_on_surface` 가 기동 글을 보내기 직전에 `lease_role_seat_verdict` + 임대 토큰 대조(`lease_resume_unheld` 자리)를 한 번 더 — 다르면 빈 좌석 닫고 93.
   - **검증된 S 등록이 살아 있는 launching 복원보다 우선**(codex 방향): follow(S) 가 ProvenTop 이고 S 임대가 Launching(복원기 생존 · 기동 글 아직 안 보냄)이면 승계 → 복원기는 위 재확인에서 토큰 불일치로 멈춤. 복원기가 기동 글을 이미 보냈으면(LAUNCHED) 승계하지 않고 사건만(그때는 이미 둘 — 신선도 관문이 앞에서 막아야 함).
3. **비-Claude topology**(데몬 변경 · 허용): cysd 가 세션 파일 결정 출처를 기록(`lsof` · `registered` · `heuristic`)하고 org.status/topology 에 `session_source` 로 노출 · `caller_sid=None` 의 타 좌석 등록은 사용량 귀속만 하고 **수집기 파일 선택·영속 핀 입력으로 쓰지 않음**(handlers usage.register · usage.rs 1494 근처). 클라이언트 `seat_conversation_now` 비-Claude 갈래는 `session_source == "lsof"` 일 때만 현재 대화 증거(그 밖 = Ok(None) → 93). 데몬 바뀐 줄 보고 의무.
4. **Tauri TOCTOU**: `held_by_live_writer` 가 (좌석 · 세대 · fence · token · writer) 를 돌려주고, `run_sidecar_restore_judged` 는 topology 판독 **뒤** 같은 임대를 다시 읽어 다섯 값이 같고 writer 생존일 때만 「복원됨」. 가능하면 writer 가 그 좌석 뿌리(surface.list pid)의 자손인지도 확인(좌석의 현재 에이전트 = writer).
5. **양성 S 신호의 출처**: #1 방어의 「등록 = S」 를 데몬 raw `registered_session_id` 대신 **최상위 훅 등록 기준**(데몬 기존 `repin_anchor` = 헬퍼로 증명된 등록은 안 옮김)으로 — org.status 에 `anchor_session_id` 노출(데몬 1~2줄). topology S(휴리스틱 1회 핀)는 양성 신호에서 빼고 신선도 관문(2)으로 대체할지 후임 판단(빼면 5 의 92 고착도 풀림).
6. **순서 주입 결정론 시험 + 뮤턴트**: cys 에 시험 전용 정지점(env `CYS_TEST_LEASE_PAUSE=<지점>:<파일>` · `cfg!(debug_assertions)` 에서만 · 운영 빌드 무동작 핀) — 지점 = ①#1 방어 판독 뒤 surface.create 앞 ②Tauri 쪽은 순수 함수에 판독 순서 클로저 주입. e2e: (2A) 정지점에서 W 의 진짜 등록 S(가짜 claude 에 좌석 안 대화 전환 명령 추가 — 받은 줄이 `/resume <id>` 면 그 id 로 등록) → 재개 → rc ≠ 0 · W2 0 · (2B) 가짜 claude 가 전환하되 등록 실패(FAKE_CYS 를 없는 경로로) + S jsonl 에 1줄 쓰기 → 신선도 관문 92 · (1) 계통 Unknown = 단위(argv None 주입) · (3) 데몬 단위(caller None 등록이 핀을 안 바꿈) · (5) 헬퍼 등록(같은 좌석 자손 `claude` 이름 2단 + 훅 셸)으로 raw 등록만 S → 진행. 뮤턴트 = 각 고침 1개씩 되돌림 · 붉은 시험 이름까지.

### 11-3. 지금 상태

- HEAD = `8114319c4`(+ 이 HANDOFF 커밋) · push 0 · 작업트리 clean(이 커밋 뒤) · 기준선 작업트리 `~/axdev/.wt/cys-1116-skt1-base`(dea2e1853 · 측정용 · 지워도 됨).
- 고친 것 0(이 절은 설계만). 시험 숫자 §4·§6 은 8114319c4 기준 그대로 유효.

---

## 12. 【후임 델타 · worker-1116skt1b】 codex 1R BLOCK 6 + 독립 검증(2288) V1~V6 고침 (master#f7698dc5 · master#8daa09dd)

### 12-0. T1 공개 함수 표(§0) 바뀐 것 — T4·T5 좌석(2267)이 알아야 할 것

| 쓰임 | 이름·시그니처 | 바뀐 뜻 |
|---|---|---|
| 계통 3값(신설) | `pub enum Lineage { ProvenTop, NotTop, Unknown }` · `pub fn lineage_of(cmds: &[Option<String>], bin_base: &str) -> Lineage` | 결속을 옮기는 것 = ProvenTop(최상위 에이전트 1 + 그 아래 SessionStart 훅)뿐 · argv 판독 불가·에이전트 0 = Unknown = 옮기지 않음 |
| 기동 글 직전 확정(신설) | `pub fn mark_launch_sent(store: &Store, norm: &str, recheck: &mut dyn FnMut() -> Result<(), String>) -> Result<(), String>` · CLI `pub(crate) fn lease_commit_launch(role, agent, sess: Option<&str>, seat: u64) -> Result<(), String>` | 잠금 안 = 임대가 아직 내 것 + 재확인 Clear 일 때만 `Lease.launch_sent = true` · Err(`lease:taken` 등) = 기동 글 0 · **T4 입양이 저장 대화를 잇는 기동 글을 직접 친다면 이 확정을 먼저 부를 것** |
| 등록 앞 결속 해제(신설) | `pub fn transition_unbind(store, new_id: &str, is_my_writer: &dyn Fn(&Holder) -> bool) -> usize` · CLI `pub(crate) fn lease_transition_before_register(surface_id: u64, transcript: &str)` | `cys usage-register` 가 데몬 등록 **앞**에 부름 — 최상위 작성자의 다른 대화 결속 = 결과 불명(좌석 유지 · 작성자 없음) |
| 앱 「복원됨」 증거(신설) | `pub struct HeldProof { surface_id, daemon_gen, fence, token, writer }` · `pub fn held_proof(store, id, probe) -> Result<Option<HeldProof>, String>` · `pub fn held_proof_stable(before, after) -> Option<HeldProof>` | `held_by_live_writer` 는 그대로(이것의 얇은 껍질) |
| 임대 기록 칸(신설) | `Lease.launch_sent: bool`(`#[serde(default)]` = 옛 기록 false) | 확정 전 기동 중 임대 = 다른 좌석 최상위 훅의 검증된 follow 가 이어받음 · `Guard::hold` 도 true 로 적음 |
| #1 방어 | `role_seat_verdict(live, role, agent, sess, exclude: Option<u64>, alive, seat_agent, current)` · `lease_role_seat_verdict(role, agent, sess, exclude)` | `registered` 인자 삭제 · topology 핀·등록 문자열 신호 삭제 · 원천 = 현재 대화 증거 하나 |
| 비-Claude 현재 대화 | `pub(crate) fn seat_agent_open_rollout(root: u32, bin: &str) -> Result<Option<String>, String>` | 좌석 뿌리 자손 에이전트가 **연** rollout(lsof) · 윈 = Err(93) |
| 삭제 | `registered_session_in` · `follow_lineage_not_top` | — |

### 12-1. codex 1R 처분(판정문 `~/axdev/master/reports/verify/codex-1120/skt1-r1.md`)

| # | 판정문 요지 | 고침(파일) | 시험 |
|---|---|---|---|
| 1 blocking | 계통 `None` 이면 헬퍼 등록이 결속을 옮김 → rc 0 · 작성자 2 | leaf `Lineage`·`lineage_of`(에이전트 정확히 1 + 그 아래 훅 = ProvenTop · 판독 불가·에이전트 0·이름 모름 = Unknown) · CLI `lease_follow_on_register` = `!= ProvenTop` 이면 return(같은 작성자의 옛 임대 지우기도 그 안이라 함께 막힘) | leaf `lineage_moves_only_a_proven_top_hook`(Unknown 행) · CLI 배선 핀 · e2e HR(헬퍼) |
| 2A blocking | #1 방어 판독 뒤 좌석 안 `/resume S` 등록 도착 → W2 | ① `Lease.launch_sent`(확정 표식 · serde default) ② `boot_agent_on_surface` 가 저장 대화 잇는 기동 글 **직전** `lease_commit_launch` → leaf `mark_launch_sent`(잠금 안: fence·token 가 아직 내 것 + #1 방어 재확인(기동 좌석 제외) Clear 일 때만 확정 · 아니면 기동 글 0 → 빈 좌석 닫고 93) ③ `follow`: 작성자 없는 기동 중 임대가 **확정 전**이면 다른 좌석 최상위 훅의 검증된 등록이 이어받음(같은 잠금 = 둘 중 하나만 이김) · 확정 뒤면 종전(충돌 사건) · `Guard::hold` 도 확정 적음 | leaf `a_verified_registration_beats_an_uncommitted_restore_and_the_restorer_stops`(순서 주입: 확정 전 follow → 확정 `lease:taken` · 재확인 실패 → 확정 0 · 확정 뒤 follow = 충돌) · CLI 배선 핀(확정이 기동 글 앞) |
| 2B blocking | 같은 프로세스 `/resume S` · 등록 실패 → 옛 T 결속이 「다른 대화」 증거 | `cys usage-register` 가 데몬 요청 **앞**에 `lease_transition_before_register` → leaf `transition_unbind`: 이 발신의 조상 중 결속 임대의 작성자이고 계통(발신 부모→그 작성자)이 ProvenTop 이면 그 작성자의 **다른 대화** 작성 중 임대 = 결과 불명(좌석 유지 · 작성자 없음 · fence+1·새 token) · 데몬 없이 판정(에이전트 이름 = 좌석 목록 · 못 읽으면 claude) · 등록 성공 → follow 가 새 결속 · 옛 대화 임대는 judge 가 「그 좌석 현재 대화 다름」으로 풂 | leaf `a_conversation_switch_unbinds_the_old_conversation_before_registering` · CLI 배선 핀(해제가 등록 앞) |
| 3 blocking | 비-Claude topology 가 좌석 밖 가짜 등록으로 덮임 | ① 클라이언트 `seat_conversation_now` 비-claude = `seat_agent_open_rollout`(좌석 뿌리 자손 에이전트 프로세스가 **지금 연** rollout · `/usr/sbin/lsof -p -Fn` · 첫 줄 payload.id · 둘 이상 다름 = Err · 윈 = Err) ② **데몬** `usage.rs collect_for` 1줄: 비-claude 좌석의 `registered_transcript` 는 세션 파일 결정·대화 핀(topology 영속) 입력 아님(등록 경로 = claude SessionStart 훅뿐 · git grep 확인) | cysd `skt1_codex_seat_registration_never_pins_the_conversation`(대조 = claude 핀 잡음) · CLI 진리표(codex topology T 핀 < 연 파일 S) |
| 4 blocking | Tauri held→topology TOCTOU 로 첫 93 지움 | `run_sidecar_restore_judged`: 결속 판독(앞) → topology → 결속 판독(뒤) → `restore_held_stable`(leaf `held_proof_stable` = 좌석·세대·fence·token·작성자 전부 같을 때만) | cys-app `skt1_restored_proof_must_survive_the_topology_read`(사이에 소멸·작성자 교체·다시 잡힘 = 유지 · 배선 순서 핀) · leaf `held_proof_must_be_the_same_on_both_sides_of_the_topology_read` |
| 5 major | 헬퍼/낡은 등록 S 가 실제 결속 T 를 이김(거짓 막힘) | `role_seat_verdict` 원천 = 현재 대화 증거 하나 — topology 핀·데몬 등록 문자열 신호 삭제(`registered` 인자·`registered_session_in` 삭제 · `lease_role_seat_verdict` 의 org.status 조회 삭제) · r5c #2(등록 직후 결속 전 창)는 2B 의 등록 앞 결속 해제가 맡음(그 사이 좌석 = 결속 없음 = 93) | CLI 진리표(topology S + 결속 T = Clear) · 배선 핀(org.status 0) |
| 6 major | 시험이 순서를 안 잡음 | 위 순서 주입 시험(leaf 2 · Tauri 1) + e2e HR + 뮤턴트 §12-4 | — |

(c)(d) 판정문 「문제없음/직접 피해 미확인」 = 손대지 않음. (d) 「follow 가 새 결속을 쓴 뒤 옛 결속 삭제 전 죽으면 둘」 은 2B 로 순서가 바뀌어(옛 결속 해제 → 등록 → 새 결속) 창이 줄었다(측정 없음).

### 12-2. 독립 검증(2288 · `~/axdev/workers/cysr-1116-skt1-verify-1120/VERDICT.md`) 처분

| # | 처분 |
|---|---|
| V1 헬퍼 거름 행동 시험 0(MV5 생존) | e2e **HR** `a_helper_registration_inside_the_seat_never_moves_the_binding` 신설(가짜 claude `FAKE_HELPER_GATE` = 좌석 안에서 자기를 `claude -p` 헬퍼로 다시 띄워 새 대화 H 를 훅 이름 셸에서 등록 · 결속 = T 그대로 단언) · MV5(계통 수집 줄 제거)는 새 코드에서 계통 = Unknown = follow 0 → RV·HR 붉음 방향(아래 뮤턴트 MI 는 「계통 관문 삭제」로 HR 을 잰다) · session_lease_e2e 는 이미 ci-branch 맥 레인 등재(8114319c4) |
| V5 p1 시험 공유 HOME | `p1_lease_knob` = 켬이면 자식 HOME = 상자 안 고유 폴더 · 단언 = `작성자 생존 판정 불가(daemon:gen-unreadable)`(V6 고침이 만드는 결정론 사유) · 새 임대 폴더(`rm -rf` 뒤)에서 p1 묶음 33/33 초록 |
| V6 세대 없는 임대 = 영구 93 | `lease_gate` 가 `current_gen()` None 이면 임대를 만들지 않고 93(`daemon:gen-unreadable` · 다음 회차 그대로 풀림) · 이미 남은 세대 없는 임대 = `next_action` 「그 임대 파일 확인 후 삭제 · 급하면 노브 off」 |
| V2 phoenix 거짓 보류 | 92(writer_live) 인데 그 역할 좌석이 섰으면(`_revived_seat` · 이번 회차 기동 실패 줄 없음) 보류로 세지 않고 생존 판정으로 · 93 은 그대로 보류 · 팩 검체 L3·L4 + 뮤턴트 M2 KILLED |
| V3 HANDOFF 표기 | **정정**: §6 표의 `cargo test --test rotate_autorestore_hold` 는 ci-branch 레인에 **없다**(CI `cargo test --test` = update_drainhold_e2e·win_job_exit·win_pack_swap + session_lease_e2e(8114319c4)) — 「CI 와 같은 명령」 묶음이 아니라 로컬 추가 측정이었다 |
| 📌 끔 안내 | USER-MANUAL 1줄: `CYS_SESSION_LEASE=off cys restore`(그 명령 환경에만 걸림 · 앱 자동 복원엔 안 걸림 · 끄면 작성자 둘 못 막음) · 파일 스위치(앱·phoenix 일괄)는 기능 추가라 📌 그대로 |

### 12-3. ★판정 축 표(갱신 · master 의 기본 켬 재판정용) — 고친 뒤 각 경로

근거 = 코드 대입 + 위 시험(확신도 중상 · 실 claude 의 좌석 안 `/resume` 타이밍은 실측 없음).

| 경로 | lease 없이(1.1.15)도 작성자 둘? | lease 가 새로 만든 것? | 고친 뒤 결과 | 남는 창 |
|---|---|---|---|---|
| 1 계통 None 헬퍼 등록 | 예 | 아니오 | follow 0(Unknown) → 결속 없음 → 같은 역할 S 복원 93 | 없음(대신 계통 못 읽는 기계 = 거짓 93 · 아래 ⓐ) |
| 2A 판독 뒤 좌석 안 `/resume S` 등록 | 예 | 아니오 | 등록이 **확정 전**: follow 가 이어받고 복원기 확정 `lease:taken` = 기동 글 0 · 93 / 결속 해제가 재확인 전: 재확인 Unverified = 기동 글 0 | 등록(훅의 cys 실행)이 **확정 뒤**에 닿는 경우 = 두 쪽이 정말 동시에 S 를 잇기로 한 것(1.1.15 와 같음 · 충돌 사건만 남음) |
| 2B 같은 프로세스 `/resume S` · 등록 실패 | 예 | 아니오 | 등록 앞 결속 해제 → 좌석 결속 없음 → 93 | 훅의 `cys` 자체가 안 돈 경우(CYS_PY 없음·cys 실행 파일 못 찾음 등) = 옛 결속 T 가 남음(1.1.15 와 같음) |
| 3 비-Claude 가짜 등록 | 예 | 아니오(새 증거 원천이 물려받았던 것) | 현재 대화 = 연 rollout(lsof) · 데몬 핀은 비-claude 등록을 안 받음 → 가짜 T 무력 | 윈도우 codex 좌석 = lsof 없음 = 같은 역할 S 복원 93(거짓 막힘 · 안전 쪽) |
| 4 Tauri TOCTOU | 결과 종류 예(1.1.15 는 93 자체가 없음) | 경합은 예 | 앞뒤 판독 같을 때만 「복원됨」 | 두 번째 판독 뒤 바뀜(그 뒤 일은 다음 복원이 다시 잰다 · 데이터 손실 아님) |
| 5 헬퍼/낡은 등록 S 가 결속 T 를 이김 | 아니오 | 예(거짓 막힘) | 등록 문자열·topology 핀 신호 삭제 → 결속 T = 진행 | 없음 |

⇒ 요지(확신도 중상): **고친 뒤 lease 켬이 1.1.15 보다 작성자 둘을 늘리는 경로는 없다**(§11-1 결론 유지). 1.1.15 에도 있던 작성자 둘 경로 1·2A·2B·3 은 「훅의 cys 가 아예 안 돈 경우」와 「확정 뒤 진짜 동시」만 남았다. lease 가 새로 만든 것 = 거짓 막힘뿐: ⓐ 계통 argv 를 못 읽는 기계(윈 MSYS 등 · 결속이 안 생겨 같은 역할 S 복원 93) ⓑ 윈 codex 좌석(lsof 없음) ⓒ 훅 없는 claude(종전) — 모두 93 · 사유 줄 · 끔 안내(USER-MANUAL) 있음. 독립 검증 실측(정상 복원 ≈70회 거짓 거절 0 · 39e35832e 기준)은 ⓐⓑ 를 지나지 않는 맥 상자라 이번 변경 뒤 맥 수치는 아래 §12-4 e2e 로만 다시 잰다.

### 12-4. 시험(2026-11-20 · env -i · 격리 HOME=/tmp/sk1b · CARGO_BUILD_JOBS=4 · 공유 기계 부하 100~143 = 다른 좌석 빌드 · 이 좌석 부하 주입 0)

| 묶음 | 전(8114319c4 · §4·§6 · 독립 검증 재측) | 후(9fdf1990e) |
|---|---|---|
| `cargo test --lib session_lease` | 24 ok | **28 ok**(새 4: 확정·승계 순서 · 전환 해제 · 계통 3값 · 앞뒤 판독) |
| `cargo test --bin cys session_lease_cli_tests` | 26 ok | **26 ok**(진리표·배선 핀 고쳐 씀) |
| `cargo test --bin cys b360_tests::p1_`(임대 폴더 지운 새 상태) | 독립 검증: 새 폴더 2/2 붉음(V5) | **33 ok** |
| `cargo test --bin cysd usage::tests` | — | **55 ok**(새 1 skt1_codex…) |
| `cargo test -p cys-app --bins seatkeep` / `skt1_` | 10 ok / — | **10 ok / 1 ok** |
| `cargo test --test session_lease_e2e`(SLE_ROUNDS=3 · 스레드 4) | 11 ok | 1회차(옛 하네스 · 07:56~08:11 · 부하 118~143) **10 ok · 2 붉음**(R1·DD 의 「정상 조건 rc 93 = 0」 단언 · 사유 줄 미포착) → 같은 두 시험 단독 재실행 **2/2 초록** → 하네스 고친 뒤 전체 재실행(08:16~08:25 · 부하 104~142) **12 ok · 0**(새 HR 포함) |
| 팩 `test_phoenix_seatkeep_t1_lease_hold.py` | OK | OK(L3·L4 새 · M1·M2 KILLED) |
| e2e 고아(시험 뒤 `ps -E` 로 HOME=/tmp/cys-sle-* 프로세스 수) | 1회차 뒤 **1**(cysd · ppid 1 · FR 대기 셸의 늦은 autostart · 실측 08:11 · 내 pid 로 정리) | 하네스 고친 뒤 **0**(08:25 · 09:12 뮤턴트 뒤도 0) |

⚠1회차 R1·DD 붉음(93) 은 사유 줄을 못 잡았다 — 후보 = 이번에 늘어난 판독(관문의 세대 판독 V6 · 기동 글 직전 재확인의 topology·surface.list·결속 판독)이 부하 118~143 에서 시한을 넘긴 것(rc 93 = 안전 쪽 · 다음 회차에 풀림) · 확정 아님. 독립 검증의 「정상 복원 거짓 거절 0/70」(부하 ≤32)과 같은 조건 재측은 하지 않았다 — 📌.

뮤턴트(소스 변이 → 시험 → git checkout · 붉은 시험 이름):

| # | 변이 | 결과 | 붉은 시험 |
|---|---|---|---|
| MA | follow 의 「확정 전 기동 중 임대 승계」 갈래 삭제 | KILLED | lib `a_verified_registration_beats_an_uncommitted_restore_and_the_restorer_stops` |
| MB | 확정의 소유 검사 `false && fence ≠ … \|\| token ≠ …` | 생존 = **변이 불량**(우선순위로 token 검사가 남음 · token 은 획득마다 새 값이라 그것만으로도 가른다) → MB2 로 다시 |
| MB2 | 확정의 소유 검사 전체 끔(`false && (…)`) | KILLED | lib `a_verified_registration_beats_an_uncommitted_restore_and_the_restorer_stops` |
| MC | 계통 Unknown(에이전트 0·판독 불가) = ProvenTop | KILLED | lib `lineage_moves_only_a_proven_top_hook` |
| MD | 전환 해제가 같은 대화(compact)도 풂 | KILLED | lib `a_conversation_switch_unbinds_the_old_conversation_before_registering` |
| ME | #1 방어 topology 신호 복원 | KILLED | CLI `role_seat_verdict_truth_table` |
| MF | 관문 세대 검사 무력화(V6) | KILLED | cys `b360_tests::p1_lease_on_with_an_unanswering_daemon_holds_without_a_new_seat` |
| MG | Tauri 뒤 판독 무시(앞 판독만) | KILLED | cys-app `skt1_restored_proof_must_survive_the_topology_read` |
| MH | 데몬 비-claude 등록 거름 삭제 | KILLED | cysd `usage::tests::skt1_codex_seat_registration_never_pins_the_conversation` |
| MI | follow 계통 관문 삭제(헬퍼 등록도 옮김) | KILLED | e2e `a_helper_registration_inside_the_seat_never_moves_the_binding`(V1) |
| M2(팩) | phoenix V2 예외 삭제 | KILLED | 팩 L3 |

팩 phoenix 관련 검체(직접 실행 · env -i · 격리 HOME · 09:13~09:16): `test_phoenix_*` 28 + `test_agy_door_phoenix_loop` + `test_awaken_enter` = 31 중 rc 0 = 28 · rc≠0 = 3 → `test_phoenix_w2_untomb_fullcycle`·`test_phoenix_e2e_replacement` = 사유 `aliased_harness_root`(TMPDIR=/tmp 가 /private/tmp 별칭 = 러너 환경) → 별칭 없는 TMPDIR 로 다시 = **8/8 · 7/7 PASS** · `test_phoenix_c6_reap` = `S5 bounded observation timed out` **3/3 붉음**(09:16·09:19·09:28 · 마지막은 MI 뮤턴트가 남긴 target/debug/cys 를 깨끗이 다시 빌드한 뒤 · 부하 32~50 · cysd 큐 주차·exited 관측 8초 시한 · 코드 읽기로는 임대·phoenix 복원 갈래와 만나지 않음 = **관계 미확정 · 측정 대기**) · 기준선(dea2e1853 작업트리)은 `target/debug/cysd` PermissionError 로 실행 불가(앞 좌석 §6 과 같은 사유) — 세 검체 모두 ci-branch 팩 단계 목록 밖. ⚠CI 팩 단계 전체(검체 153)는 이번 회차에 다시 돌리지 않았다(시간 상한) — 이번 팩 변경 = javis_phoenix.py 1곳(V2) + 그 검체뿐.

### 12-5. 남는 한계(숨기지 않음)

1. 훅의 `cys` 가 **아예 안 돈** 좌석 안 대화 전환(CYS_PY·cys 실행 파일 못 찾음 · 훅 JSON 깨짐) = 옛 결속이 남아 「이 좌석 = 옛 대화」 → 같은 역할 그 대화 복원이 새 좌석을 열 수 있다(1.1.15 와 같음).
2. 좌석 안 `/resume S` 의 등록이 복원기 **확정 뒤**에 닿는 진짜 동시 = 둘 다 S(1.1.15 와 같음 · 임대엔 conflict_live 사건).
3. 거짓 막힘(93 · 안전 쪽): 계통 argv 를 못 읽는 기계 · 윈 codex 좌석(lsof 없음) · 훅 없는 claude(종전) · 부하 큰 기계의 판독 시한(1회차 R1·DD 후보 · 미확정).
4. 옛 판 cys(launch_sent 칸을 모름)가 같은 임대 폴더를 쓰면 그 판의 기동 중 임대는 확정 표식이 없어 다른 좌석 등록이 이어받을 수 있다(1.1.16 안에서는 모든 cys 가 같은 판).
5. Tauri 「복원됨」 증거는 결속 작성자가 그 좌석 뿌리의 자손인지까지는 보지 않는다(codex 판정문 「가능하면」 · 좌석·세대·역할 점유 + 앞뒤 같음까지).
6. 데몬: claude 좌석의 좌석 밖 등록(caller 없음)은 종전대로 핀을 움직인다(윈 호출자 해소 실패와 가를 수 없어 손대지 않음 · 결속은 claude 쪽에서 등록 문자열을 안 쓰므로 작성자 둘로는 안 이어짐 · 복원 대상 핀만 영향).

### 12-6. 데몬(원작자 파일) 바뀐 줄

- `src/bin/cysd/usage.rs` `collect_for` 첫 줄: `let registered = s.registered_transcript.lock().unwrap().clone();` → `….clone().filter(|_| agent == "claude");`(+ 주석 3줄) · 시험 모듈에 `skt1_codex_seat_registration_never_pins_the_conversation` 1개. handlers.rs·state.rs 변경 0.

### 12-7. 📌 덧붙임(master 판단)

1. 기본 켬: 위 §12-3 = 1.1.15 대비 작성자 둘 경로를 늘리지 않음 · 새 것은 거짓 막힘(93)뿐 → 켬 유지 쪽(확신도 중상) · 단점 = 부하 큰 기계에서 판독 시한 93 이 늘 수 있음(1회 관측 · 사유 미확정) → 독립 검증의 「정상 복원 ≈70회」 재측을 같은 조건으로 붙이면 판단 근거가 된다.
2. 현장 끔 스위치 = 여전히 환경변수뿐(USER-MANUAL 1줄 추가) — 파일 스위치(앱·phoenix 일괄)는 기능 추가라 📌.
3. codex 2R 질문 후보: 확정(`mark_launch_sent`)과 follow 승계의 같은 잠금 직렬화 · 등록 앞 결속 해제의 계통 판정(데몬 없이) · 비-claude lsof 증거 · Tauri 앞뒤 판독.
