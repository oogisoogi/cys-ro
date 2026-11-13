# HANDOFF — TICKET=cysr-seatkeep-t3 (cysd 좌석 생성 경로 = 좌석 프로세스 손잡이 + seatkeep 경유 · 맥 · 노브 기본 끔)

- 가지 = `feat/seatkeep-t3`(← t2 `a48d36e1`) · push 0 · 설계 메모 = `docs/seatkeep/T3-DESIGN.md`
- master 지시: master#c125bc97(고칠 것 3: 잠금 2칸 = 노브 켬만 · `--end-on-controller-loss` · 출력 폭주 실측 / 답: rows·cols 수용 · 등록부 3파일 잔존 = T4) · master#fe07cc6a(D7 = 결정 B · SIGNAL target 칸)
- 시험대 = `~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t3/harness/`(t3life.py · t3a13.py · t3misc.py) · T2 시험대 사본 = `../t2copy/harness/`
- 격리 시험 실행기 = scratchpad `run_tests.sh <label> <cargo test 인자>`(CYS_* 제거 · HOME/XDG 임시 · CYS_SEATKEEP 만 통과)

## fix3 r4 = 좁은 codex r4 REVISE 마무리 2건(master#50be861b · 2026-11-13 12:57~13:1x · 판정문 = `~/axdev/master/reviews/codex-queue-2026-11-13/r4/4-seatkeep-t3.r4.verdict.md` · 커밋 f95cd5d4 · push 0 · codex 0)
- r4 판정: 3R #2·#3 닫힘 · #1 부분 → 아래 2건으로 닫으려 함(master 가 이 2건만 codex 마지막 확인).
- **#1 major(main.rs 옛 218~239) 고침**: 맥에서 Ready 뒤 `kevent()` 대기가 비-EINTR 로 실패하면 20ms 폴링으로 내려가던 갈래 제거 → `WATCH_LOST` 표시(140) · 감시 스레드 233~252: 표시 → `KEEP` 있으면 `end_for_controller_loss(watch_lost)`(부모 상실과 같은 길) · 없으면 false 로 돌아감 → 주 스레드 기동 확인 자리 `watch_lost_early`(273) = 자식 직전 785~787 · 직후 839~841 → `end_early(watch_lost, rc 9)`(949 · 옛 `end_early_parent_lost` 공통화 = 기록 1줄·소켓 삭제·등록부 ended_controller_lost — 자식 뒤면 프로세스 끝으로 마스터가 닫혀 SIGHUP) · Keep 두기 뒤 888~890 = `end_for_controller_loss(watch_lost)`. **갈래 1줄**: Keep 이 생기기 전(자식 전·자식 뒤 모두) = 주 스레드가 rc 9 로 끝냄(자식 전이면 spawned [] · 자식 뒤면 같은 정리 길) · Keep 뒤 = 감시가 부모 상실과 같은 길로 끝냄 — 감시 「표시 → Keep 확인」 · 주 「Keep 두기 → 표시 확인」(SeqCst) 이라 둘 중 하나는 반드시 끝냄. 폴링은 맥 밖 유닉스만(256 `#[cfg(not(target_os = "macos"))]` · 제품 경로 아님). cysd rc 9 문구 「기동 중 잃음」 추가(seat_proc.rs 449).
- **#2 minor(main.rs 옛 160~177·660~662) 고침**: `match watch_parent(..)`(690~) — Ready 만 진행 · Gone = 상태 폴더·잠금·장부·등록부 전에 rc 8 · Unavailable = rc 9.
- **디버그 훅**: `CYS_SEATKEEP_TEST_WATCH_FAIL` = `gone`(등록 ESRCH 흉내 · 208) · `kevent`(Ready 뒤 대기 실패 · 지연 `CYS_SEATKEEP_TEST_KEVENT_FAIL_DELAY_MS`) — 기존 `spawn`·`kqueue` 그대로 · 모두 `#[cfg(debug_assertions)]`(릴리스 = 빈 문자열).
- **시험(main.rs)**: 도우미 `run_sk_with` 2285(부모 = 시험 프로세스 생존 · rc·상태 파일 목록·seatkeep_exit 줄) · `bound_watch_gone_ends_before_any_file` 2342(rc 8 · 파일 0 · 자식 0) · `bound_watch_wait_failure_before_spawn_fails_closed` 2357(kevent 지연 0 + 자식 기동 지연 300ms → rc 9 · 자식 표식 0 · 기록 watch_lost spawned []) · `bound_watch_wait_failure_after_start_ends_like_parent_loss` 2372(kevent 지연 1.5초 = 좌석이 뜬 뒤 → 8초 안 끝 · 기록 watch_lost 1줄 · 좌석 자식 사라짐).
- **뮤턴트(되돌림 `cmp` 일치 · 뮤턴트마다 seatkeep 다시 빌드 · 끝에 원본 다시 빌드)**: M11a 대기 실패 → 폴링(고치기 전 꼴) = 대기 실패 시험 2개 붉음 · M11b Gone 진행(고치기 전 꼴) = gone 시험 붉음 · M11c 주 스레드 확인 자리 끔 = 자식 전 시험 붉음 · M11d 감시가 Keep 뒤 안 끝냄 = 좌석 뒤 시험 붉음.
- **msv(HEAD f95cd5d4 · 부하 load 28)**: seatkeep 단위 47/47(44 + 새 3) · 게이트 2/2 · `seatkeep_stalled` 2/2(스레드 1) · `seatkeep_input_ack` 2/2(스레드 1) · `seat_proc::` 20/20(스레드 2) · 노브 켬 `SEATKEEP_TEST_THREADS=1 scripts/seatkeep-knob-on-tests.sh accounts::` 158/158(79초).
- **알려진 동작(고침 아님 · r4 참고)**: 출력을 아주 조금씩 소비하면(조각 하나 넣을 때마다 HARD 막힘 시계가 None 으로 돌아감) A안 시계가 계속 리셋돼 입력 확인 기다림이 10초보다 훨씬 길어질 수 있다 — 「HARD 에서 내리 10초 막힘」이라는 A안 조건 안의 동작(소비가 도는 동안은 직접 PTY 처럼 기다림).

## fix3 #2 끝 = INPUT_ACK 조건부 상한(재개 master#7e06caa5 · 2026-11-13 12:18~ · 커밋 146d3ac3 · push 0 · codex 0 · 설치본·라이브 무접촉)
- **master 결정** = A안(상한 시계 = 「ACK 기다림 중 demux 가 HARD(5MiB)에서 막힌 순간」부터 10초 · 그 밖은 직접 PTY 처럼 기다림) + 만료 (나) · B(절대 상한) 버림.
- **고친 줄(seat_proc.rs · 모두 `mod seatkeep_mac` 안 = 노브 켬 전용 · 노브 끔 운영 줄 0)**: `ACK_STALL_LIMIT`·`ACK_STALL_POLL` 338~340 · `OutSpool.hard_stall_since` 579 · `SeatLink.sd`(shutdown 전용 연결 사본 · 쓰기 잠금 무관) 586 · `Awaiting` drop = `poke_out` 620(답 기다림이 끝나면 옛 막힘 시각을 거둠) · `push_output` 717~725(답 기다림 중 HARD 막힘 = 시각 기록 · 넣음 성공·평소 상한 막힘·닫는 중 = None) · `write_chunk` 817~851(시계 = max(막힌 시각, 보낸 시각) · 250ms 주기 · 10초 = 만료) · `abort_link` 856~(eprintln 1줄 → `sd.shutdown(Both)` → `mark_closing`).
- **만료 경로(실측)**: 호출자 `TimedOut` 10.04~10.10초 · seatkeep `controller_lost` 로 끝 · 좌석 프로세스 사라짐(= 막힌 입력이 나중에 적용될 곳 없음) · 연결 스레드는 닫는 중 표시로 HARD 막힘에서 풀려 끊김을 읽고 `exit = seatkeep_disconnected` · seatkeep 회수.
- **시험(seat_proc_tests.rs)**: 셸 좌석 도우미 `script_seat` 319 · `stty raw -echo` 로 256KiB 입력이 PTY 입력 버퍼에서 반드시 막힘(정규 모드는 찬 입력을 버릴 수 있음) → 옛 재현의 시간 의존(1/2) 제거.
  - ① `seatkeep_input_ack_stall_ends_seat_when_consumer_never_resumes` 346(`exec yes` · 소비자 끝내 재개 안 함): TimedOut · ≥10초 · 16초 안 · 5초 안 seatkeep·좌석 부재 · 종료 접힘.
  - ② `seatkeep_input_ack_waits_while_consumer_runs_and_stdin_unread` 387(`yes &` 출력 폭주 + 소비 정상 + 자식 16초 stdin 안 읽음 → `cat`): Ok · 12.2초(>10초 = 상한을 넘겨 기다림) · 좌석·seatkeep 생존 · 소비 출력 0.5~1.8GB.
  - 옛 `#[ignore]` 관측 시험 `seatkeep_known_limit_input_ack_behind_full_output_while_consumer_stalled` = 삭제(①이 결정화된 판으로 대체 · 그 시험의 「15초 동안 ACK 안 옴」 단언은 이제 거짓).
  - 뮤턴트(되돌림 확인 `cmp` 일치): M10a 상한 없음(고치기 전 꼴 · LIMIT 3600초) = ① 붉음(16초 안 안 돌아옴 · seatkeep·좌석 생존) · M10b 절대 상한(시계 = 보낸 시각) = ② 붉음(10.01초 TimedOut) · M10c 만료 때 `mark_closing` 안 함 = ① 붉음(seatkeep 회수 안 됨 · 종료 None) · M10d 만료 때 연결 안 끊음 = ① 붉음(좌석 생존).
- **msv(HEAD 146d3ac3 · 부하 load 10~17)**: seatkeep 단위 44/44(`--list` 실측 44 — 위 「지금 45」는 수 기재 오류로 보임) · 게이트 2/2 · `seatkeep_stalled` 2/2 · `seat_proc::` 20/20(`--test-threads=1`·`=2` 각 1회) · 노브 켬 `SEATKEEP_TEST_THREADS=1 scripts/seatkeep-knob-on-tests.sh accounts::` = 158/158(58초).
  - ⚠ `seat_proc::` 기본 병렬(4개 seatkeep 동시 기동) + 부하 15 = 4개 모두 `handshake_timeout` 거절로 실패(좌석 생성 단계 · 이 고침 전 코드에 닿기 전) — fix1 에 규명된 「디버그 시험 바이너리 상대 Security 조회 ×2 > 3초」 그대로. 이 묶음도 스레드 ≤2 로 돌린다.
- **알려진 한계 문구 고침**(아래 fix2 절의 「지연(유실 아님)」 → 정정): 노브 켬 + cysd 출력 소비 정지 + 입력 확인 기다림 = 소비가 10초 안에 재개되면 지연(유실 아님) · 10초 넘게 막히면 **좌석이 끝난다**(호출자 TimedOut · 입력 나중 적용 없음 · 일부 입력은 이미 PTY 에 들어갔을 수 있음). 직접 PTY 와의 차이 = 직접 PTY 는 출력 소비 정지와 무관하게 입력이 들어감.
- **T4 Ⓐ 후보(1줄)**: (가) seatkeep 입력 스레드 비차단·poll PTY 쓰기 + 취소 토큰 + 「일부만 씀」 ACK 의미 정의 = 만료에도 좌석을 살리는 길 → T4 흐름 제어(Ⓐ)와 함께 결정.

## fix3 = codex 3R REVISE(major 2 · minor 1) 처분(master#e7ca9e16 · 2026-11-13 12:11~ · 판정문 = `~/axdev/master/reviews/codex-queue-2026-11-13/r3/4-seatkeep-t3.r3.verdict.md`) — 【매듭 · CTX 58%】
- **끝남**:
  - #1 major = 08f6d1dd: `watch_parent` → `Watch::{Ready,Gone,Unavailable}`(main.rs 128~·147~·184~) · 감시 스레드 생성 실패·**맥 kqueue 실패 = fail-closed rc 9**(main.rs 123 · 660 · PTY·파일·자식 전) · 폴링 대체는 안전 보장으로 세지 않음(맥 밖 유닉스만 폴링 · 제품 경로 아님) · cysd 문구 rc 9. 시험 `bound_watch_unavailable_fails_closed`(디버그 훅 CYS_SEATKEEP_TEST_WATCH_FAIL=spawn|kqueue) · 뮤턴트 M8(못 세움 무시)·M8b(kqueue 실패→폴링) 붉음 · bound_ 10/10.
  - #3 minor = ac7d690d: `reject_timeout`(main.rs 1122 · 호출 1167) — 상태·기록 잠금 무관하게 REJECT 유한 쓰기(200ms) → shutdown → 기록(상태 try_lock). 시험 = 준비 중 상태 잠금 6초에도 첫 프레임 < 3초+1.5초 · 고치기 전 꼴 M9 = 7.33초 붉음 · handshake_timeout 3/3.
- **남은 것 = #2 major(INPUT_ACK 무기한 대기)** — 후임 몫. master 지시 = ACK 대기에 절대 상한 · 만료 처리 (가) 비차단·poll PTY 쓰기로 좌석 살리고 TimedOut / (나) controller 연결 끝내 쓰기 취소 + 오류 · 「cysd 만 기다림 끝내고 입력이 나중에 적용」 금지 · 「소비자를 끝내 재개하지 않음」 시험 필수.
  - 【반론 · master 회신 대기 · 2026-11-13 12:1x】 **「절대」 상한은 정상 좌석을 죽일 수 있다**: 자식이 stdin 을 한동안 안 읽기만 해도(긴 빌드 중 미리 친 입력 > PTY 입력 버퍼 등) seatkeep PTY 쓰기가 막혀 ACK 가 늦는다 — 직접 PTY 는 그때 cysd 쓰기가 막혀 기다릴 뿐 좌석이 살아 있다(차이 = 출력 소비와 무관). 교착은 「ACK 기다림 + demux 가 상한(5MiB)에서 막힘(= 출력 소비 정지)」이 겹칠 때만 생긴다. 제안 = 상한 시계를 **ACK 기다림 중 demux 가 HARD 에서 막힌 순간부터** 잰다(예 10초) — 그 조건 밖(소비가 도는데 자식이 stdin 만 안 읽음)은 직접 PTY 처럼 기다린다. master 가 「절대」를 유지하면 값은 크게(예 120초) + 문서에 「입력을 그만큼 안 읽는 프로그램 = 좌석 끝남」 명시.
  - 고른 안(후임 구현 권고) = **(나)**: 만료 → `self.wr` shutdown(Both) + `closed` 표시 → write_chunk `TimedOut` · 조종자 종속 seatkeep 은 연결 상실 → `end_for_controller_loss` → 프로세스 끝 → PTY 마스터 닫힘(입력 스레드의 막힌 쓰기도 프로세스와 함께 끝남 = 나중 적용 없음 · 일부 기록은 가능하나 좌석이 죽음). 까닭: 기존 연결 상실 경로 재사용 · 규약 변경 0 · 작음. 버린 안 (가): seatkeep 입력 스레드를 비차단+poll+취소 토큰으로 다시 쓰고 「일부만 씀」의 ACK 의미를 새로 정해야 함 — T4 흐름 제어(Ⓐ)와 함께.
  - 시험 설계: 기존 `#[ignore]` 재현을 바탕으로 소비자를 **끝내 재개하지 않는** 판 — 기대 = write 가 상한+여유 안에 `TimedOut` · seatkeep 끝남(controller_lost) · 좌석 pid 사라짐 · 뒤늦은 입력 적용 0(좌석이 없으니 관측 = 좌석 프로세스 부재). 재현이 시간 의존(1/2)이므로 입력 쓰기를 확실히 막는 꼴 = 자식이 `stty -icanon` 아래 stdin 을 안 읽음(또는 입력 > 입력 버퍼 + 원시 모드) 로 고정 — 미실측.
  - HANDOFF 「알려진 한계」의 「지연(유실 아님)」 문구는 codex 3R 지적대로 무기한 정지에선 미입증 — #2 고친 뒤 고쳐 쓴다.
- **2R #4 = 이번에 안 고침 · 다음 판 후보**: `Surface` 필드 비공개 래퍼(우회 꼴 = 공개 필드 직접 접근 · 매크로 생성 접근 · 타입 별칭 구조 분해 · 손잡이가 참조를 돌려줌) — 문자열 게이트로는 구조적 보장 불가.
- msv 재검증(후임이 #2 뒤 다시 돌릴 것): `cargo build --bin cys-seatkeep && cargo test --bin cys-seatkeep`(지금 45) · `cargo test --bin cysd seat_handle_gate seatkeep_stalled`(필터 하나씩) · `SEATKEEP_TEST_THREADS=1 scripts/seatkeep-knob-on-tests.sh accounts::` · 관측 `cargo test --bin cysd seatkeep_known_limit_input_ack -- --ignored --nocapture`.
- 뮤턴트 실행기 주의: 시험대 scratchpad `mut.py` 는 되돌린 뒤 seatkeep 을 다시 빌드한다(fix1 교훈) · cargo test 거르개는 1개만.

## fix2 = codex 2R REVISE(blocking 0 · major 2 · minor 2) 처분 · 고침(master#b8703879 · 2026-11-13 07:29~08:3x · 판정문 = `~/axdev/master/reviews/codex-queue-2026-11-13/4-seatkeep-t3.verdict.md`)
- 커밋: 08bc92d7(#1) → 8f86d2b0(#3 · #1 시험 결정화 · #2 재현 · T2 잠금 시험) → (이 HANDOFF 커밋). push 0 · codex 0 · 설치본·라이브 무접촉.

| # | 판정문 | 처분 | 한 것 | 붉음(고치기 전 꼴) | 고친 뒤 | 뮤턴트 |
|---|---|---|---|---|---|---|
| 1 major | 감시 등록 전 스케줄 틈 · 폴링 20ms 창 | 수용·고침 | `watch_parent` = 감시가 「등록 끝남·이미 상실·폴링 준비」를 채널로 알릴 때까지 주 스레드 대기 · `parent_gone_early` 가 표시 + `getppid() != parent` 직접 · 디버그 훅 WATCH_DELAY·GONE_DELAY·PARENT_SEEN_FILE(「부모를 잰 뒤」 표지로 창 결정화) | M6-prefix(장벽·직접 확인 둘 다 끔) 2/2 붉음 ×2회 | `bound_watcher_late_schedule_still_ends_at_once`(감시 3초 늦음 + 확정 중 사망 → 1.5초 안 끝) · `bound_parent_gone_seen_directly_before_flag`(상실 표시 4초 늦음 → 기동 확인 직접 getppid → 자식 0) | M6a(장벽 끔)=①만 · M6b(직접 끔)=②만 붉음 · 각 2회 |
| 2 major | 입력 ACK 가 PTY 쓰기 뒤에만 · 소비자 정지 + 출력 폭주 + stdin 안 읽음 = 영구 대기 | 수용(재현 = CONFIRMED) · **고침 = 【결정필요】(규약)** | 판정문 순서 재현 시험 `seatkeep_known_limit_input_ack_behind_full_output_while_consumer_stalled`(`#[ignore]` · 관측) — 1회차: 소비자 정지 15초 동안 ACK 안 옴 → 소비자 재개 즉시(15.04초) 옴(유실 아님 · 지연) · 2회차: PTY 입력이 안 막혀 ACK 28ms(재현 안 됨) → 시간 의존 1/2. 한 줄(FIFO) 위에서 메모리 상한 + 유실 0 + 소비자 무기한 정지를 함께 지키며 ACK 를 보장하는 길은 없다(출력 뒤에 선 ACK 에 닿으려면 상한 없이 읽어야 함) → 규약 변경 필요 | 위 1회차 | — | — |
| 3 minor | 수락 쪽이 준비 전에 끝맺음을 잡음 | 수용·고침 | 끝맺음 CAS = 조종자를 실제로 거는 자리(재생 프레임·accept 기록 뒤) · 준비 중 감시가 이기면 `accept_aborted handshake_timeout` 덧붙이고 물러남(A16 셈 일관) · 준비 전에 이미 시간 초과면 accept 를 쓰지 않고 조용히 물러남 · 준비 안의 거절 3곳도 reject_once · 디버그 훅 ACCEPT_DELAY · 핸드셰이크 시험 직렬화(Security 동시 조회가 시간 경계를 흔듦) · 조종자 6초 쥠(늦은 길이 붙은 채 끝나게) | M7-prefix(옛 자리 = 들머리 CAS) = 늦은 WELCOME → accept→disconnect→controller_lost | `handshake_timeout_during_accept_preparation_aborts_accept`(시나리오에 닿을 때까지 최대 3회) + 기존 둘 | M7a(준비 전 조기 확인 끔)=①붉음 · M5a/M5b/M5c 다시 돌려 모두 붉음 |
| 4 minor | 게이트 구조적 보장 없음(필드 pub) | 수용 · **부분 처분 유지(닫힘 아님)** | 고침 없음 — 정본 = `Surface` 필드 비공개 래퍼(시험 구역 약 86곳) · T4 이후. 게이트 머리 주석 「알려진 한계」 그대로 · 이 표에서 #3(1R) 은 「부분」으로 둔다 | — | — | — |

- **#2 【결정필요】 선택지**(master → 박사님/T4): Ⓐ 흐름 제어 프레임(조종자가 OUTPUT 소비 신용을 돌려줌 · seatkeep 은 신용 안에서만 OUTPUT · 제어 프레임은 늘 먼저) — 규약 판 올림 · 가장 정석 Ⓑ 제어 전용 두 번째 연결(seatkeep 조종자 자리 1개 규칙 변경) Ⓒ cysd 출력 대기열을 상한 넘으면 디스크로(메모리 상한 유지 · 디스크 상한 따로) Ⓓ 알려진 한계로 둠(직접 PTY 는 입력이 출력 소비와 무관 = 차이 1곳 · 소비자 무기한 정지는 cysd 결함 상황). 권고 = T4 에서 Ⓐ(입양을 켤 때 밀림 정책을 다시 정하는 일과 같은 자리) · 그 전까지 Ⓓ.
- **알려진 한계(master#1401eca4 결정 = Ⓓ · 2026-11-13 · ⚠fix3 #2 로 대체됨 — 위 「fix3 #2 끝」 절 정정 문구가 정본)**: 노브 켬 + cysd 출력 소비 정지 = 입력 확인(INPUT_ACK) 지연(유실 아님) · T4 에서 Ⓐ 흐름 제어 프레임으로 닫음(입양 밀림 정책 재결정과 같은 자리) · 관측 시험 `seatkeep_known_limit_input_ack_behind_full_output_while_consumer_stalled`(`#[ignore]`). 「준비 전 시간 초과 = accept 안 씀」 = master 수용 · 실행기 기본 스레드 = 안 바꿈(제안 기록만).
- **#1 판단(1R 처분 「부모 감시 = kqueue」 유지)**: 장벽 = 감시 준비까지 대기(감시 스레드를 못 띄우면 기다리지 않음 · 기동 확인의 직접 getppid 가 대신) · kqueue 등록 실패 → 폴링 시작 직전에 준비 알림.
- **시험(HEAD 8f86d2b0 · 부하 load 14~53 · 다른 좌석 작업)**: seatkeep 단위 43/43 ×3 · 게이트 2/2 · cysd `seatkeep_` 묶음(정지 소비자 입력·닫기 2) 초록 · 노브 켬 `accounts::` 실행기 = 스레드 4 → 15 실패 · 2 → 2 실패 · 1 → 0 실패(실패는 전부 새 동작 그대로 `seatkeep 이 접속을 거절: handshake_timeout` — 기록 없는 EOF 아님). ⚠「스레드 ≤4 면 0 실패」(fix1 18:54 = 3249/0)는 기계 부하가 낮을 때 값 — 부하가 크면 `SEATKEEP_TEST_THREADS=1`.
- **T2 시험 손댐 1곳**: `registry::tests::id_lock_is_exclusive` — 같은 시험 프로세스에서 다른 시험이 fork 하면 자식이 exec 전까지 잠금 fd 사본을 쥐어(같은 열린 파일 = 같은 flock) 「놓은 뒤 다시 잡기」가 잠깐 실패(부하에서 3회 중 1~2회 관측) → 다시 잡기 최대 2초. 운영 코드 무변경.
- **내가 덧붙인 것(지시 밖 판단)**: ① 준비 「전」 시간 초과의 조용한 물러남(조기 확인) — codex 고침 방향(「준비를 CAS 앞에」)을 따르면 생기는 「시간 초과 뒤 accept+accept_aborted」 줄을 막으려고 ② 핸드셰이크 시험 직렬화·6초 쥠·최대 3회 — 부하 의존 판정을 없애려고 ③ #2 재현 시험 `#[ignore]` — 1/2 재현이라 기본 실행에 두면 흔들림.

- **매듭(2026-11-12 21:09 · master#1e252546 주간 98% 정지)**: fix1 마지막 = 48a34208 · handshake-timeout = b5ee4392(【확인요청 3】 18:54 · 노브 켬 전체 스레드 4 = 3249/0) · 진행 중 고침 없음 · 재개 = 리셋(금 06:00) 뒤 master 지시 · 다음 = master 스냅샷 재검증 + codex 2R(fix1 차이 + handshake-timeout 차이).

## fix1 = codex 1R REVISE 4건 처분·고침(TICKET=cysr-seatkeep-t3-fix1 · worker-8 surface:2019 · 2026-11-12 08:31~08:43 · 예산 정지 · 16:51~ 재개 master#be9e91aa)
- 커밋: d9f8f44a(#1·#4) → 7cdb8c46(WIP #2) → 81745d7b(#2 시험) → 22a30875(#3) → 62d57b19(D1 문서) → (이 HANDOFF 커밋). push 0 · 라이브 무접촉 · codex 호출 0(master 가 2R 을 건다).
- **노브 끔 경로에서 바뀐 운영 코드 줄 = 0**: cysd 운영 변경은 전부 `seat_proc.rs` 의 `mod seatkeep_mac`(맥 · 노브 켬 전용) 안(`git diff fcc6896f..HEAD -U0 -- src/bin/cysd/seat_proc.rs` 의 덩이 머리가 모두 `mod seatkeep_mac`) · seatkeep 실행 파일은 노브 켬에서만 뜬다 · 나머지 = 시험·문서.

| # | 판정문 | 처분 | 한 것 | 고치기 전 붉음 | 고친 뒤 | 뮤턴트 |
|---|---|---|---|---|---|---|
| 1 major | 부모 상실 검사가 자식 기동 뒤 | 고침 | `--controller-bound` 이고 기동 때 ppid ≤ 1 이면 어떤 파일·PTY·자식도 만들기 전에 rc 8 · 아니면 부모 감시를 **자식 기동 앞에서** 시작(kqueue `EVFILT_PROC/NOTE_EXIT` — 고른 까닭: 죽는 순간 깨어 폴링 지연 0 · 잰 뒤 등록 전에 죽었으면 등록이 ESRCH 로 실패해 그 틈도 닫힘 · 감시 스레드 폴링은 주기만큼 늦음 → kqueue 를 못 쓰면 20ms 폴링으로 대신) · 자식 기동 직전·직후 확인(rc 8 · 기록 `seatkeep_exit parent_lost phase starting spawned [..]`) · Keep 이 생긴 뒤에는 감시가 바로 `end_for_controller_loss`(확정 중이라도) · cysd 문구에 8 추가 | 시험 3개 모두 붉음(M1-prefix-all = 고침 전체 끔 · 3/3 실패: 표식 생김·기록 없음·확정 지연 3초를 기다림) | seatkeep 단위 38/38 | M1a(ppid≤1 조기 종료 끔)·M1b(기동 직전 확인 끔)·M1c(감시가 끝내지 않음) 각 1 실패 = 3/3 |
| 4 minor | 종료 기록 2줄 가능 | 고침 | Keep `exit_owner: AtomicBool` · `claim_exit` = `compare_exchange(false,true)` · 진 쪽 `lose_exit`(park · 기록·등록부·소켓 무접촉) · supervise 정상 끝 2곳도 같은 소유권 | M4(늘 이김) = 「이긴 쪽 2명 [true,true]」 | 200회차 × 두 길 동시(장벽) = 매번 1명 · 기록 1줄 | M4 1/1 |
| 2 major | demux 가 출력 채널 송신에서 막혀 EXITED·ACK 영구 대기 | 고침 | 64조각 `sync_channel` → 바이트 대기열 `OutSpool`(FIFO · 순서 보존). 평소 상한 1MiB(차면 소켓을 안 읽음 = 역압 · 유실 0) · 제어 답(INPUT_ACK·FOREGROUND_IS)을 기다리는 동안 5MiB(출력 뒤에 줄 선 답에 닿게 — 조종자 종속 seatkeep 은 출력·제어를 한 줄로 보내고 256KiB(+16KiB · 첫 재생 ≤1MiB)에서 멈추므로 답 앞 출력은 그 이하 + 소켓 버퍼) · 닫는 중(kill·wait) = 막히지 않음(5MiB 넘는 출력은 버림 — 직접 PTY 를 닫으면 안 읽은 출력이 사라지는 것과 같음) · 읽기 얼굴 Drop = 이후 버림. 메모리 상한 = 좌석당 5MiB + 프레임 1 | 시험 2개 모두 붉음(옛 seat_proc.rs = d9f8f44a: 입력 확인 5초 초과 · 닫기 5초 초과) | 둘 다 초록(닫기 107ms · 전경 답 받음) · 204MB 폭주 켬 = 받은 204,000,011 · 구멍 0 · 순서 0 · 측정기 밀림 0(부하 11~13 · 131.6초) | M2a(기다림 표시 끔)=입력 확인 붉음 · M2b(닫는 중 표시 끔)=닫기 붉음 · M2c(평소 상한만)=입력 확인 붉음 = 3/3 |
| 3 minor | 게이트 우회(구조 분해·식별자 경계·중첩 호출) | 부분 고침(싼 것만) | `Surface { child/master … }` 구조 식 검출(만들기 허용 = state.rs `Arc::new(Surface {` 1곳) · 손잡이 머리 식별자 경계 · 손잡이 호출의 **직접 인자**(`&`/`&mut` + 식별자·점 경로)만 허용 · 남는 우회 = 게이트 머리 주석 「알려진 한계」(매크로 · 타입 별칭 · 다른 타입 경로 · 손잡이가 돌려주는 참조) · 필드 비공개화(86곳) 안 함 | 옛 게이트 + 운영 코드에 우회 3개 심음 = 초록(놓침) | 새 게이트 각각 붉음(M3d 구조 분해 · M3e evil_probe_child · M3f 중첩) · 운영 위반 0 | M3a(경계 끔)·M3b(직접 인자 규칙 끔)·M3c(구조 식 검사 끔) 3/3 |
| ③ D1 | 인과 설명 | 문서 정정 | T3-DESIGN §0 · `seat_tail_tests.rs` 머리 · 이 HANDOFF: 「첫 write 가 잠든 `ptcread` 를 깨워 그 덩이를 read 로 옮긴 뒤 나머지 t_outq 가 **마지막 슬레이브 close** 에서 버려진다」 + 공개 XNU 소스 줄(아래) | — | — | — |

- **회귀(HEAD 62d57b19 · 2026-11-12 17:1x~18:12 · 격리 HOME/XDG · 실행기 = scratchpad `run_tests.sh` · 결과 = scratchpad `runs/`)**:
  - 노브 끔 cysd 전체: **3246 통과 · 3 실패 · 17 무시**. 실패 이름 대조(기준선 = 4638cefa full-off-v2 — 이번 기준선 회차 base-full-off 는 예산 정지로 중간 종료): `np_windows_real_candidate_change_restarts_sample_confirmation`(기준선에도 있음) · `native_core_stages_privately_and_activates_only_after_matching_capability`(기준선에 없음 → HEAD 단독 2/2 통과 · 부하 중 단독 3/3 실패 사유 `Native(Ambiguous("71184,71227"))` = 후보 pid 2개 · 파일 무변경) · `u18_cwd_blocked_observed_under_sandbox_read_deny`(기준선에 없음 → HEAD 단독 3/3 통과 · 파일 무변경). 기준선의 `np_native_same_pid_exec…`·`settle_hold_denies…` 은 이번 회차 통과(settle_hold 단독 1/3 실패 = 기준선과 같은 흔들림). → 노브 끔 새 실패 0(흔들림 2건 = 단독 통과).
  - 노브 켬 cysd 전체: **3110 통과 · 139 실패** — 전부 `create surface: "seatkeep 이 HELLO 뒤 연결을 닫음"`(seatkeep 이 `spawned` 기록 뒤 아무 기록 없이 사라짐 · 등록부 committed 그대로 · 1561 기동 중 110). **이 변경과 무관함을 확인**: ⑴ 고치기 전 트리 fcc6896f(seatkeep·seat_proc 모두 옛 판)로 `accounts::` 묶음 = 28 실패 ×2(HEAD = 11~21 실패) · 옛 seatkeep + 새 cysd = 11·25 실패 ⑵ HEAD 에서 실패 139개를 `--test-threads=1` 로 = **139/139 통과** · `accounts::` 158/158 · `seat_` 151/151(새 시험 2 포함) ⑶ cysd 밖에서 seatkeep 30개 직접 = 8초 뒤 30/30 생존. → 같은 시험 프로세스 안 병렬 시험의 간섭(PLAUSIBLE: 어떤 시험이 시험 프로세스의 후손을 죽임 — 미규명). 05:04 의 전임 켬 회차(3246/1)에는 없던 현상 · 원인 = T4 전에 규명할 것(아래 「남은 것」).
  - seatkeep 단위 38/38 · 게이트 2/2 · 꼬리(seat_tail known_limit)는 `seat_` 묶음 안에서 켬 단일 스레드 통과 · 204MB 폭주 켬 = 위 표.
  - 시험대(릴리스 62d57b19 · 결과 = `~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t3/results/fix1/`): 좌석 수명 `t3life` 켬/끔 × SIGKILL/SIGTERM × 3 = 12/12(좌석·seatkeep 남음 0) · 생성 도중 cysd 사망 `verifycopy/life.py midcreate 0ms` 켬 3/3 = seatkeep stderr 「띄운 부모(조종자)가 기동 전에 사라짐(ppid 1) — 좌석을 만들지 않고 끝낸다」(#1 경로 · 좌석 안 뜸 · 잔존 0) · 끔 3/3(좌석 끝 · 잔존 0) · cwd 경합 `cwdrace` 켬 3/3 · 끔 3/3 생성 성공(ENOENT 0 · 잔존 0) · **폭주 + 조종자 SIGSTOP 15초 + 닫기 10회**(새 시험대 `harness/t3stopclose.py` · 격리 cysd 1개 · 노브 켬) = **10/10** · 닫기 최대 911.7ms · 남은 seatkeep 0 · 남은 좌석 0 · cysd FD 29(좌석 1개) → 27(모두 닫은 뒤) · 출력 구멍 0 · cysd 생존. (이 시험대는 고치기 전 판으로는 안 돌렸다 — 판별력은 단위 시험 2개가 맡는다.)
- **노브 켬 전체 139 실패 원인 규명(master#66885a8f · 18:13~18:22 · 진단 줄은 모두 되돌림 = 커밋 0줄)**:
  - **원인(대조군 통과 뒤 이름)**: seatkeep 핸드셰이크의 **절대 기한 HELLO_TIMEOUT 3초** 안에 `peer::authorize` 가 두 번 돈다. 그 안의 `exe_of_token`(맥 Security 프레임워크 `SecCodeCopyGuestWithAttributes`+`SecCodeCopyPath` 로 상대 실행 파일 경로 찾기)이 **상대 = 262MB 디버그 시험 바이너리**일 때 느리고 **동시 호출 수에 비례해 더 느려진다** → 기본 병렬(16 스레드)에서 두 번 합이 3초를 넘어 → 감시 스레드가 소켓을 `shutdown` → cysd 는 「HELLO 뒤 연결을 닫음」(EOF). seatkeep 은 그 뒤에도 핸드셰이크를 마저 해 `accept`(늦게)→`disconnect`→`seatkeep_exit controller_lost` 를 남기거나, 기록 전이면 cysd 의 정리 SIGTERM 으로 끝난다 — **거절(reject) 줄이 없는 까닭** = 기한 감시 스레드의 shutdown 은 기록을 남기지 않는다.
  - 대조군 표(가설 1개씩):
    | 가설 | 대조군 | 관측 | 판정 |
    |---|---|---|---|
    | 신호로 죽음 | EOF 순간 + 50ms 에 seatkeep `try_wait` | 13/13 살아 있음(None) | 기각 |
    | cysd 쪽 fd 가 남의 이중 close 로 바뀜 | EOF 순간 그 fd 의 `fstat`·`LOCAL_PEERPID` | 8/8 소켓 · 같은 seatkeep pid | 기각 |
    | 부모 감시 kqueue 가 시험 스레드 끝을 부모 사망으로 읽음 | 고치기 전 seatkeep(fcc6896f · kqueue 없음) | 같은 실패(accounts:: 11·25) · parent_lost 기록 1/1561 뿐 | 기각 |
    | 공유 임시 경로 충돌 | 원장: 실패 seatkeep 도 자기 id 파일에 3.25초 늦은 `accept` · id = pid-시작-순번 고유 | 충돌 흔적 0 | 기각 |
    | FD 한도 | EMFILE/os error 24 0건 · kern.num_files 11,075 / 491,520 | — | 기각 |
    | 핸드셰이크 기한 초과 | 단계별 시간(진단 줄) | authorize#1 1.4~1.9s · 끝 2.3~3.3s(>3s = 실패) | 성립 |
    | 느린 곳 = exe_of_token | `exe_of_token` vs `process_start_us` | start_us ≈ 0 · exe_of_token 이 전부 | 성립 |
    | 병렬도(이분) | accounts:: `--test-threads` 1·2·4·8 | p50 107·155·380·984ms · p90 118·205·523·1145ms · 최대 262·302·572·11,223ms · 실패 0·0·0·0 / 기본 16 = 13~30 실패 | 용량-반응 |
    | 상대 실행 파일 특성 | 릴리스 cysd(66MB) 를 상대로 좌석 5개 | 0.11~1.8ms | 디버그 시험 바이너리 특유(크기·서명 상태 중 무엇인지는 미분리) |
  - **최소 재현**: `cargo build --bin cys-seatkeep && CYS_SEATKEEP=1 cargo test --bin cysd accounts::`(기본 병렬 · 8~11초 · 실패 11~30) / 같은 명령 `-- --test-threads=4` = 0 실패. · 실행기 = `scripts/seatkeep-knob-on-tests.sh [거르개]`(스레드 4 상한).
  - **처분(master#5b9e1d26)**: 설계안 ⑵(기한 감시가 `reject handshake_timeout` 1줄 + 늦은 수락 차단) = **구현**(별 커밋 「handshake-timeout」) · ⑶(노브 켬 전체 = 스레드 4 이하) = **반영**(`scripts/seatkeep-knob-on-tests.sh` · T3-DESIGN §관례) · ⑴(두 번째 확인에서 실행 파일 재조회 생략) = **구현 안 함**(인증 판정 변경 = 고위험 → T4 에서 codex·독립 검증과 함께). ⑴ 판단 재료 3줄:
    - 【실측 2/2 · 2026-11-12 18:3x · 시험대 scratchpad `pvprobe/probe.py`】 같은 pid 가 `exec` 하면 감사 토큰의 pidversion 이 바뀐다(예: pid 60220 = 112826293 → 112826295 · pid 60225 = 112826308 → 112826314) → 「pid·pidversion·출생 시각이 같으면 같은 실행 이미지」라는 전제가 성립하는 쪽의 근거 1건(다른 맥 판·커널 소스 대조는 안 함).
    - 재사용 공격면: ⓐ pid 재사용 = 새 프로세스는 새 pidversion(전역 증가 값으로 관측됨)이라 걸러진다 · 단 pidversion 은 32비트 — 감김(wrap) 뒤 같은 pid·같은 pidversion 은 이론상 가능(실측 안 함) ⓑ 출생 시각 해상도 = µs(`proc_bsdinfo` pbi_start_tvsec/usec) — 같은 pid 가 같은 µs 에 다시 태어나는 경우만 셋 다 같아짐 ⓒ 토큰을 읽은 뒤 Security 조회 전 사이의 exec 경합은 지금 코드에도 있는 창이다(생략 여부와 무관).
    - 결론 보류: 위 ⓐ 의 감김·ⓒ 의 창을 codex·독립 검증이 같은 결론으로 닫기 전에는 재조회 생략을 넣지 않는다.
  - (이력) **고침 안 함**(원인 자리 = seatkeep 운영 코드의 핸드셰이크 시간 예산). **설계안**: 두 번째 `authorize` 는 상대 신원(pid·pidversion·출생 시각)이 첫 번째와 같으면 실행 파일 경로를 다시 찾지 않고 첫 결과를 쓴다(exec 하면 pidversion 이 바뀐다는 전제 — T4 에서 실측 확인) → Security 호출이 핸드셰이크당 1회로 준다 · 기한 감시가 소켓을 닫을 때 `reject handshake_timeout` 1줄을 남기고, 그 뒤 핸드셰이크가 이어져 `accept` 로 가지 않게 같은 `done` 깃발로 막는다(지금은 닫힌 소켓으로 수락해 조종자 종속 모드에서 곧바로 controller_lost 로 끝남) · 시험 설비는 노브 켬 전체를 돌릴 때 `--test-threads=4` 이하로 돌리거나(지금 권고), 시험 빌드에서만 seatkeep 동시 핸드셰이크 수를 묶는다. 제품(릴리스 cysd 상대 ~ms)에서는 재현 근거가 없다 — 단 기계가 Security 쪽으로 붐빌 때 같은 3초 벽이 있다는 점은 같다.
  - 05:04 전임 켬 회차(3246/1)에서 안 난 까닭 = 미규명(그때의 병렬 부하·Security 캐시 상태 미기록).
- **남은 것(fix1)**: ① (규명됨 · 위 절) 핸드셰이크 3초 예산 안의 Security 조회 ×2 — 설계안대로 T4 에서 고칠지 결정 · 노브 기본 켬 전 차단 후보 ② #3 남는 우회(게이트 머리 주석) · 필드 비공개화 = T4 이후 ③ #2 의 알려진 한계: 자식이 입력을 안 읽어 seatkeep 입력 스레드가 PTY 쓰기에서 막힌 채 출력 폭주 + 소비자 정지가 겹치면 INPUT_ACK 가 5MiB 상한 뒤에서 기다릴 수 있다(직접 PTY 도 입력 버퍼가 차면 쓰기가 막힘 · 미실측) ④ D1 「ttywait 가 바로 풀리는 까닭」【추정】.
- **XNU 소스 줄(apple-oss-distributions/xnu `f6217f891ac0` = xnu-12377.1.9 · 2025-10-16 · github main · 받아 본 파일 = scratchpad `xnu/`)**: `bsd/kern/tty_dev.c` — `ptcread` 642(`TS_ISOPEN` 일 때만) · 680(t_outq 있으면 복사로) · 685(연결 끊김 = EOF) · 691(`ttysleep` 대기) · 700(`q_to_b(&tp->t_outq …)` 복사) / `ptsclose` 350(`t_timeout = 60`) · 355(`l_close` = `ttylclose`) · 356(`ttyclose`) · 361(`ptsstop`). `bsd/kern/tty.c` — `ttylclose` 1993~1994(`ttywflush` 실패면 `ttyflush(FREAD|FWRITE)`) · `ttyclose` 418(무조건 `ttyflush(tp, FREAD | FWRITE)`) · `ttyflush` 1840(`FLUSHQ(&tp->t_outq)`) · `ttymalloc` 3269(`Z_ZERO` → `t_timeout` 처음 0). `bsd/kern/kern_exit.c` — 2287(세션 우두머리) · 2312(전경 그룹 SIGHUP) · 2330(`ttywait`) · 2336(`VNOP_REVOKE(ttyvp, REVOKEALL …)`).
  - 관측과 맞는 것【코드】: 슬레이브가 닫힌 뒤 마스터 read 는 t_outq 를 읽지 않는다(642 조건) · 닫기는 t_outq 를 비운다(418·1840) · 회수(wait)와 무관(close/revoke 가 회수보다 앞).
  - 확정 못 한 것【추정】: 끝나는 우두머리 안의 `ttywait`(PCATCH · `t_timeout` 0 = 무기한)가 멈춘 독자 아래서 곧바로 풀리는 까닭(직전 자기 그룹 SIGHUP 로 보류 신호가 있어 PCATCH 잠이 깨는 것으로 보이나 소스로 확인 안 함).

## 상태 = 【확인요청 2】(후임 surface:2004 · 검증 1회 고침 · 2026-11-12 05:xx) — 다음 = codex 1R(범위 a48d36e1..최종)
- 전임 = 【갈무리】(01:2x · CTX 60%) · 후임 브리프 = 원장 01:26:58(surface:2004 · kind brief).
- 코드 마지막 = f3252d15(조종자 종속 모드) · push 0 · 라이브 무접촉.
- A13 【결정필요】(02:38) = master#18c2e66e 결정 A 로 닫힘(판정선 = 물리 점유 합 ≤ 160MB) → 통과(아래 표).

## 다음 첫 행동(1줄)
독립 검증 좌석의 기록을 받으면 CONFIRMED 만 1회 고친다 → codex 1R(아래 「codex 1R 꼭 물을 것」)

## master 결정(구현됨 f3252d15 · 후임) — master#77162b13 원문 요지
- 출력 폭주 = 결정 **A 를 「조종자 종속 모드」 안으로**(B 흐름 제어 프레임 · C 꼬리 늘리기 안 함). 기동 인자 하나(예 `--controller-bound` · 지금 `--end-on-controller-loss` 를 넓힘)가 있으면 seatkeep 은 **직접 PTY 처럼 투명하게**:
  ⑴ 조종자 연결이 끊기면 PTY 마스터를 닫고 끝남(지금 구현됨 · `end_for_controller_loss`)
  ⑵ 조종자가 밀리면 **PTY 읽기를 멈춘다**(커널 역압 → 자식이 조종자 속도에 맞춰 멈춤 · 유실 0) — 지금은 4MiB 큐 → 「밀림」 → 꼬리 따라잡기(T2)
  ⑶ **write_stalled 로 내보내지 않는다** — 연결이 살아 있는 한 기다린다(멈춘 cysd 아래서 자식도 멈춰 삶 = 직접 PTY 와 같음)
  인자가 없으면 **T2 동작 그대로**(자식 안 멈춤 · 4MiB 큐 · 꼬리 따라잡기 · write_stalled 10초) — T2 시험 무수정 초록. ⚠(검증 반영) 「한 줄도 안 바뀜」은 과장 = 동작 같음 · 의도된 변경 3곳(SIGNAL child_pid ≤ 0 무신호 · 등록부 폴더 첫 만들기 경합 고침 · 시험 지연 변수 릴리스 무시 — T3-DESIGN §0).
- 시험(이 모드): ① 같은 204MB 폭주(`seat_flood_tests`) = 받은 바이트 204,000,011 · 구멍 0 · 순서 어긋남 0 · 시간·RSS 를 노브 끔과 나란히 ② 조종자(격리 cysd)를 SIGSTOP 15초 → SIGCONT = 좌석 생존 · 유실 0 · write_stalled 0 ③ 인자 없는 대조군 = 아래 표 「켬」 줄과 같은 동작(유실 있음 · 자식 안 멈춤) ④ 뮤턴트(역압 줄 · 내보내기 금지 줄 각각).
- 구현(f3252d15): `send_output` 의 밀림 갈래를 `!controller_bound` 로 막음 · `read_loop` 가 읽기 전에 `wait_for_room`(큐 ≥ `BOUND_QUEUE_BYTES` 256KiB 면 반 아래까지 기다림 · 첫 조종자 전 = 꼬리의 남은 칸만큼만 읽음) · 쓰기 스레드가 한 프레임 쓴 뒤 `wake_readers`(기다리는 수 > 0 이고 반 아래면 상태 잠금 잡고 깨움 — 「기다리는 쪽 = 수 올린 뒤 큐를 봄 / 깨우는 쪽 = 큐 내린 뒤 수를 봄」 SeqCst) · 조종자 종속이면 `set_write_timeout` 안 함. 제어 큐 상한은 그대로(master 답 = 끄지 않음 · 시험 ②에서 0 단언).
- (전임 추정 · 이력) 구현 자리(코드 판독 전 · 추정): seatkeep `main.rs` 의 출력 경로(`read_loop` → 조종자 큐에 넣는 함수 · 「밀림」 표시 `behind`) · 쓰기 스레드의 `CTL_WRITE_TIMEOUT` 설정(`write_half.set_write_timeout`) · 쓰기 스레드 오류 갈래의 `evict write_stalled`. 제어 큐 상한(1MiB · `evict_ctl_full`)은 결정에 언급 없음 — 그대로 둘지 master 에 1줄 확인 권고.

## T4 로 넘길 것(master#77162b13 지시 · 후임 확인함)
- ⛔**(fix1 · codex 1R ③ · 맨 위 차단 조건에 추가) 슬레이브 보유로 꼬리를 지키려면 「누가 마지막 슬레이브 참조를 쥐고 · 언제 마스터를 비우고(drain) · 언제 닫는지」를 먼저 검증한다.** 특히 좌석 자식이 **세션 우두머리**로 제어 터미널을 쥔 채 끝나면 커널이 `VNOP_REVOKE(REVOKEALL)`(kern_exit.c 2336)로 그 터미널의 **모든 열림**을 회수한다 — seatkeep 이 쥔 슬레이브 fd 도 회수 대상일 수 있다(【추정】 · 미실측). 그러면 A(슬레이브 보유)는 우두머리 종료에서 꼬리를 지키지 못한다 → T4 첫 탐침 = 「seatkeep 이 슬레이브를 쥔 채 우두머리가 쓰고 끝남 → seatkeep 의 슬레이브 fd 가 살아 있는가(revoke 뒤 read/write 가 EBADF/ENXIO 인가) · t_outq 가 남는가」.
- ⛔**노브 기본 켬의 차단 조건(D1 · master#6e60316b)**: 조종자 종속/입양 모드에서 역압 중 자식이 끝날 때 꼬리 ≤ 1KiB 유실 — A(seatkeep 이 슬레이브 fd 를 쥐고 있다가 회수 뒤 커널 버퍼를 비우고 닫기) 또는 역압 대기를 `read()` 안에서 하게 하는 다른 길로 닫기 전에는 **기본 켬 금지**. 시험 `seat_tail_known_limit_stalled_controller_child_exit` 의 노브 켬 갈래를 「모자람 0」으로 뒤집는 것이 닫힘의 증거.
  - 미완 탐침(관측 그대로): A 의 바탕(「다른 프로세스가 슬레이브를 쥐면 자식이 끝나도 꼬리가 남는가」) 파이썬 탐침이 **닫기(os.close)에서 멈춰** 60초 시간 초과 2회 — 결과 없음(`harness/ptyprobe/p5_holder_keeps_slave_UNFINISHED.py` · `results/ptyprobe/p5….out`). 손자가 PTY 를 쥔 꼴의 시험도 60초 안에 자식이 안 끝남(세션 우두머리 종료 = 손자 SIGHUP 추정 · 미확정).
  - 덤 확인(master#6e60316b 4 · 탐침 결과만 · 구현 안 함): 「역압 대기를 마스터 fd 의 블로킹 `read()` 안에서」 = **A 보다 싼 길이 못 된다** — `read()` 안에서 멈춘 독자가 있어도 커널 버퍼를 가득 채우고 끝나는 자식의 꼬리는 첫 줄 102바이트만 남고 1,024바이트를 잃었다(시험 노브 끔 비차단 자식 · 2/2) · 또 `read()` 안의 독자는 데이터가 있으면 바로 가져가므로 역압(안 읽기)과 함께 성립하지 않는다(논리).
- (fix1 · codex 1R #2 로 고침 — 아래 P1·P2 는 이력) P1·P2(검증 PLAUSIBLE): cysd 연결 스레드 하나가 OUTPUT·INPUT_ACK·FOREGROUND_IS 를 차례로 처리 → 출력 소비가 멎으면 입력 확인(기한 없음)·전경 질의(200ms 뒤 모름)도 멎음 · 약 2시간 막히면 전경 재질의가 seatkeep 제어 큐(1MiB)를 채워 control_queue_full → 조종자 종속이라 좌석 HUP. 고칠 방향 = 확인·전경 답을 OUTPUT 과 다른 대기열로.
- 처리 속도 켬 14~19% 느림(검증 2-5a · 원인 추정 = 바이트당 복사 3~4회 + 256KiB↔128KiB 문턱 잠·깨움 왕복 · 프로파일 미실측) · A13 cysd 증가분 noisy +15MB(검증 1회 · 나는 +6.8MB 1회 · 잡음 폭 모름 → T4 에서 3회 반복) · 첫 조종자 꼬리 재생이 상한과 무관하게 최대 1MiB 한 조각(cysd 쪽 64조각 큐 최악 약 1MiB+63×16KiB).
- 입양을 켤 때(T4) 「조종자가 붙어 있는 동안의 밀림 정책(역압 + 내보내기 vs 흐름 제어 프레임)」을 다시 정한다. 근거 표 = 아래 「출력 폭주」(T2 기본 동작 = 노브 켬 유실 95.3% · 194,422,979 / 204,000,011 바이트) + 「후임 실측」(조종자 종속 = 유실 0 · ^C 뒤 바이트 · 재개 지연).
- `--controller-bound` 를 빼는 자리 = `src/bin/cysd/seat_proc.rs` seatkeep 기동 인자(주석 있음 · f3252d15 에서 옛 `--end-on-controller-loss` 를 이 이름으로 바꿈). 빼면 ⑴ 끊김 종료 ⑵ 역압 ⑶ 쓰기 기한 없음 셋이 함께 빠진다 — 입양을 켜면서 ⑵만 남기려면 인자를 나눠야 한다.
- 끝난 좌석 등록부 3파일(.json·.log·.lock) 정리 · 죽은 pid 의 prepare/committed 무시(T2 인계 7).
- T2 인계 중 T4·T6·T7 몫(입양 규칙 · 번들·봉인·서명 · pkill 폴백 · 윈도우 컴파일) 그대로.

## 실측
### 커밋 · 시험 수
- 커밋: ① bda1f68e(손잡이 + 직접 PTY 옮기기) · ①' 98d03214(옮긴 자리 소스 핀 ⑦ · D7 시험기 좀비 · 선언) · ②③④ 942d6d7e · ba446e5d(Cargo.lock)
- 기준선(옮기기 전 a48d36e1 · 노브 없음): cysd 3224 통과 · 3 실패(native_publication 2 · pending_requests c8registry 1 = `Locked`) · 15 무시 · rc 101
- ① 트리 노브 끔: 3224 통과 · 6 실패 = native_publication 2(기준선과 같음) · pending_requests 1(`Locked` — 기준선과 다른 이름 · 같은 부류 흔들림) · 소스 핀 ⑦(옮긴 자리 · ①'에서 고침) · C8 핀(시험이 디스크 소스를 읽는 중에 ② 코드가 들어감 · 표 등재로 고침) · D7 시험기(좀비 = 산 것으로 셈 · ①'에서 고침)
- ② 트리 노브 끔(942d6d7e 직전 빌드): **3242 통과 · 2 실패(native_publication 2 = 기준선과 같음) · 16 무시** · rc 101
- seatkeep 단위: 30/30(T2 27 + 새 3: reap_marks_before_reaping · signal_target_leader_group_and_refusal · ensure_dir_is_race_safe_on_first_creation)

### 좌석 수명(master#c125bc97 ② · t3life.py · 릴리스 · results/t3life.jsonl)
| 노브 | cysd 내림 | 회차 | 좌석 SIGHUP 으로 끝남 | seatkeep 잔존 | 끝나기까지 ms | seatkeep 기록 사유 |
|---|---|---|---|---|---|---|
| 켬 | SIGKILL | 6 | 6/6 | 0 | 178~452 | controller_lost ×6 · 등록부 ended_controller_lost |
| 켬 | SIGTERM | 6 | 6/6 | 0 | 191~384 | controller_lost ×6 |
| 끔(직접 PTY) | SIGKILL | 6 | 6/6 | — | 74~200 | — |
| 끔(직접 PTY) | SIGTERM | 6 | 6/6 | — | 151~423 | — |
대조군(인자 없는 seatkeep = 자식 생존) = T2 `t2.py all` 의 조종자 SIGKILL 12회(아래 t2 재실행 줄).
- 노브 켬 전체(ba446e5d · CYS_SEATKEEP=1): **3239 통과 · 5 실패 · 17 무시** — native_publication 1(기준선 같음) · r1f 전경 전제(fd ≥ 0 가정) · 시험용 잠금이 쓰기 막힌 데몬 폴더에(unpreservable_queue_wal) · u18 샌드박스 검체 · v116(앞 시험 독 전파) → f4b9b6ab 에서 전제 2건 고친 뒤 그 5건 + D7 3건 재시험 **7/7(필터 합 8 중 7 + u18 포함) 초록**. 노브 켬 전체 재실행은 아직(다음 할 일 ①).
- D7(결정 B 반영 뒤 · 노브 켬): 3/3 초록 = 직접 PTY 표와 같음(o1 생존).

### 출력 폭주(master#c125bc97 ③ · seat_flood_tests · 204.0MB 최대 속도)
| 노브 | 받은 바이트 | 유실 | 순서 어긋남 | 시간 | cysd RSS 최고 | seatkeep RSS 최고 | write_stalled | 좌석 |
|---|---|---|---|---|---|---|---|---|
| 끔 | 204,000,011 | 0 | 0 | 56.6초 | 268.6MB | — | — | 생존 |
| 켬 | 9,577,032 | 194,422,979(95.3%) | 3 | 3.2초 | 116.3MB | 22.1MB | 0 | 생존 |
→ 【결정필요】 올림(01:23 · 선택지 A 권고 = 조종자 붙어 있는 동안 밀리면 PTY 읽기 멈춤 · 프레임 변경 0). 미결.

### 입력→화면 왕복(seat_latency_tests · `surface.send_text` RPC → 파서 화면에 반향 2회 · n=300)
| 노브 | p50 | p90 | p99 | 최대 | 입력 중 전경 질의 |
|---|---|---|---|---|---|
| 끔(옮긴 뒤) | 3.00ms | 3.50ms | 5.13ms | 34.2ms | — |
| 켬 | 2.89ms | 3.47ms | 5.69ms | 17.5ms | 0회 |
- 「옮기기 전」(a48d36e1) 값은 **미실측**(이 시험 파일이 그 커밋에 없음 · 옛 빌드에 시험을 얹어 다시 재야 함).
- 전경 질의 0회 = 이 좌석(`cat`)은 에이전트 그룹 표식이 0 이라 V2 지름길(시스템 콜·소켓 왕복 없음). 에이전트 좌석(표식 섬)에서는 입력 계수마다 FOREGROUND 왕복 1회가 낀다 — **그 경우 지연은 미실측**.

## 검증 1회 고침(후임 · master#8193a786 처분 · #a9e47c44 보강 · #6e60316b D1 결정 B · 04:02~)
| # | 처분 | 한 것 | 고치기 전 붉음 | 고친 뒤 | 시험 |
|---|---|---|---|---|---|
| D1 | 결정 B = 알려진 한계 | 고침 없음 · 관측 시험 + 탐침 보관 · T4 차단 조건 | 결정적 시험 79b727a2 노브 켬 3/3 정확히 1,024 모자람 · 기제 = 받는 쪽 아님(실험 1회 final_offset = 받은 바이트) | 켬 모자람 1,024(2/2) · 끔 자식 6초 막힘 + 모자람 0(2/2) | `seat_tail_known_limit_stalled_controller_child_exit` |
| D2 | 고침 | seatkeep 기동 때 부모 pid · supervise 100ms 마다 비교 · 기동 때 1 = 잃음 → `parent_lost` | life.py midcreate 0ms(검증 사본) = 1초·5초 시점 좌석·seatkeep 생존 · 끝 사유 no_first_controller | 0ms 2/2 · 1초 시점 둘 다 끝 · 좌석 HUP · `parent_lost` / 1초·5초 = controller_lost | 단위 `bound_parent_loss_is_seen_only_in_bound_mode` + 검증 사본 midcreate |
| D3 | 고침(시험) | attach 의 확인부를 `greet()` 로 떼고 시험 2 | (뮤턴트 MA·MA2 로 확인 — 아래 표) | 2/2 초록 | `greet_refuses_socket_whose_peer_is_not_the_launched_seatkeep` · `greet_refuses_welcome_from_other_pid` |
| D4 | 차선(타입 막기 = 시험 구역 약 86곳 · 30곳 상한 초과) | 게이트 = `.child`/`.master` 필드 참조 자체 · 넘기는 자리·이름 붙은 예외만 허용 · 대상 = cysd 하위 전체 + src/*.rs · 자기 시험에 별칭 검체 등 9개 | 검증 ME(별칭) = 초록(놓침) | 운영 코드 위반 0 · 자기 시험 초록 | `seat_handle_gate_*` 2 |
| D5 | 고침(시험) | 두 칸 잠금 관문 시험 | 검증 MF = 초록(놓침) | 초록 | `quiescent_gate_blocks_live_cysd_holder_two_field_lock` |
| D6 | 고침(문서) | `startup_lock_holder_pid` 를 BOM 문서 위로 | — | `strip_utf8_bom` 문서 복구 | — |
| D7 | 고침 | seatkeep 자식 작업 폴더 = `"."` 상속 · 그래도 실패 + 폴더 없음 = rc 7 · handlers 시험 make_surface 명시 cwd | cwdrace.py(검증 사본) 켬 3/3 생성 실패(rc 5) | 켬 0/3 실패 · 끔 0/3 | 검증 사본 cwdrace |
| 문구 2 | 고침 | T3-DESIGN §0(인자 없는 경로 = 동작 같음 · 의도된 변경 3곳 · 노브 켬 = 시험 전용 · 구별되는 곳 1) · 이 HANDOFF 21줄 | — | — | — |
- 뮤턴트 v2(`harness/t3mutants2.py` · `MUT_SET=v2` · 별도 git 작업트리 `/private/tmp/sk3mut-wt2` 4638cefa · 끝나고 제거 · 기준 회차 8종 전부 초록 확인 뒤 · 결과 `results/t3-mutants-v2.tsv`): **8/8 잡음**
  | 뮤턴트 | 되돌린 줄 | 잡은 시험 |
  |---|---|---|
  | MA(검증 · 같은 뜻으로 다시 씀) | greet 소켓 상대 pid 대조 끔 | `greet_refuses_socket…`(1 실패) |
  | MA2 | greet WELCOME pid 대조 끔 | `greet_refuses_welcome…`(1 실패) |
  | MD(검증) | governance 에 `surface.child.lock()` 직접 | 게이트(1 실패) |
  | ME(검증) | governance 에 별칭 `let ch = &surface.child; ch.lock()` | 게이트(1 실패 · 전: 놓침) |
  | MF(검증) | factory_reset 옛 판독기 `s.trim().parse::<u32>()` | `quiescent_gate_…two_field_lock`(1 실패 · 전: 놓침) |
  | MG | D2 부모 판정 끔 | 단위 `bound_parent_loss…` · 검증 사본 midcreate 0ms(1초·5초 시점 생존) |
  | MH | D7 작업 폴더 다시 찾기(옛 줄) | 검증 사본 cwdrace 켬 3/3 생성 실패 |
  | MI | 역압 대기 빼기 | known_limit 켬(자식이 안 막혀 60초 안에 안 끝남) |
  (1회차 뮤턴트 17/17 은 그대로 유효 — 이번 고침이 그 줄들을 바꾸지 않음.)
- 전체 시험(4638cefa · 뮤턴트 작업과 동시 실행 · 부하 있음): 노브 끔 cysd **3244 통과 · 3 실패 · 17 무시 · rc 101**(native_publication 2 = 기준선 · `settle_hold_denies…` = 검증 2-1c 에서 기준선 a48d36e1 노브 끔에서도 실패한 부하성) / 노브 켬 **3246 통과 · 1 실패 · 17 무시 · rc 101**(native_publication 1 = 기준선 · D7 흔들림 `b3_status_usage…` 재발 없음) · seat_ 묶음 켬 149/149 · 끔 149/149(2 무시) · seatkeep 단위 34/34 · lib factory_reset 49/49.
- 검증 시험대는 읽기만 하고 내 시험대로 복사(`harness/verifycopy/` · lib.py 의 SNAP/OUT/REL 만 바꿈 · `SK_REL` 로 뮤턴트 빌드 지정).

## 후임 실측(최종 코드 f3252d15 · 2026-11-12 01:3x~02:37)
### 고치기 전/후 — 출력 폭주(seat_flood_tests · 204,000,011 바이트 · 디버그 빌드)
| 회차 | 받은 바이트 | 유실 | 순서 어긋남 | 시간 | cysd RSS 최고 | seatkeep RSS 최고 | 좌석 |
|---|---|---|---|---|---|---|---|
| 켬 · 고치기 전(HEAD f4b9b6ab 코드) | 9,589,170 | 194,410,841 | 3 | 3.26초 | 116.6MB | 22.5MB | 생존 |
| 켬 · 큐 4MiB(첫 구현) | 204,000,011 | 0 | 0 | 73.06초 | 230.2MB | 18.8MB | 생존 |
| 켬 · 큐 256KiB(최종) | 204,000,011 | 0 | 0 | 73.72초 | 246.4MB | 13.3MB | 생존 |
| 끔(같은 날) | 204,000,011 | 0 | 0 | 56.89초 | 267.1MB | — | 생존 |
- 릴리스 실물 cysd(t3rate.py · 같은 204MB): 끔 4.83·5.11초(42.2·39.9MB/s) / 켬 5.61·5.81초(36.4·35.1MB/s) = 켬 약 14% 느림 · 4회 모두 화면 끝 2,000,000 + FLOODDONE · cysd 출력 구멍 줄 0 · cysd RSS 최고 끔 453~457MB / 켬 439~446MB · seatkeep 10~11MB.
### 시험 ②③ + 직접 PTY 대조(seatkeep 단독 t3bound.py · 실물 cysd t3stop.py · 릴리스)
| 경우 | 멈춘 동안 자식 | 유실 | 내보냄 | 재개 지연 | 끝까지 받음 |
|---|---|---|---|---|---|
| 실물 cysd SIGSTOP 15초 → SIGCONT(②) | 멈춤 | 0(구멍 줄 0 · 화면 끝 1,000,000) | 0(write_stalled·control_queue_full 0) | 13.3~18.3ms | 예 · 좌석·seatkeep·cysd 생존 |
| seatkeep 조종자 종속 · 조종자 15초 안 읽음 | 멈춤 | 0 | 0 | 7~20ms(4MiB 때 110ms) | 예 |
| 인자 없음(③ 대조군 = T2) | 안 멈춤 | 8.08~10.86MB | write_stalled | — | 아니오(내보내짐) |
| 직접 PTY(seatkeep 없음) | 멈춤 | 0 | — | 0.2~1.1ms | 예 |
| 첫 조종자 3초 늦게 · 조종자 종속 | 붙기 전 멈춤(진행 10,200 고정) | 0 | 0 | — | 예 |
| 첫 조종자 3초 늦게 · 인자 없음 | 안 멈춤 | 29.55MB(꼬리 1MiB 밖) | — | — | — |
- 역압 중 ^C(읽기 멈춘 채 INPUT ^C): 자식 끝나기까지 조종자 종속 607~637ms / 직접 PTY 612~644ms(같음 — 자식에 닿음). ^C 뒤 조종자에게 더 온 바이트: 직접 PTY 0(커널이 ^C 때 출력 큐 비움) / 조종자 종속 4MiB 큐 3.89~3.93MB → 256KiB 큐 250~252KB.
### 전체 시험(f3252d15)
- 노브 끔 cysd 전체: 3242 통과 · 2 실패(native_publication 2 = 기준선 a48d36e1 과 같음) · 17 무시 · rc 101(567.7초).
- 노브 켬 cysd 전체: 3240 통과 · 4 실패 · 17 무시 · rc 101 — native_publication 2(기준선) + b3_status_usage… · settle_hold_denies…(뮤턴트 작업과 동시 실행 회차 · 따로 3회 = 3/3 초록). b3 실패 사유 = 「seatkeep 이 붙기 전에 끝남 rc 5」 + seatkeep stderr `spawn: No such file or directory` — PLAUSIBLE: 같은 시험 프로세스의 다른 시험들이 HOME 을 프로세스 전체로 바꾸고 지움(handlers.rs set_var("HOME") 12곳) → 좌석 작업 폴더 경합. 직접 PTY 도 같은 부류 · 미확정이라 안 고침.
- seatkeep 단위 33/33(T2 27 + 전임 3 + 후임 3: bound_send_output_never_goes_behind · bound_reads_only_tail_room_before_first_controller · bound_reader_waits_at_cap_and_wakes_below_half).
- T2 `t2.py all`(인자 없는 seatkeep = T2 동작): 판정 48행 · 실패 0 · rc 0(전임 회차는 시험대 결과 폴더 부재로 rc 1 — 폴더 만들고 다시 돌림).
- M09 결정적 시험(reap_marks_before_reaping): 동시 빌드 부하(rustc 2~5 · load 약 11) 아래 10/10.
- 좌석 수명(t3life · 릴리스): 켬 SIGKILL 6/6(91~384ms) · SIGTERM 6/6(160~260ms) — 사유 controller_lost ×12 · 등록부 ended_controller_lost / 끔 SIGKILL 6/6 · SIGTERM 6/6 = 24/24.
- 좌석 100개 만들고 닫기(t3misc 고친 판 · 켬): 닫기 실패 0 · seatkeep 잔존 0 · 남는 파일 300(.json·.log·.lock 각 100) · 105,372 바이트 · .sock 0 · .exit 0 / 끔: 0. 40좌석 동시 생성·동시 닫기: 켬 1.25초/1.72초 · 끔 0.72초/1.10초 · 실패 0 · 시간 초과 0(교착 0).
- A13 = 아래 「A13」 표(판정선 개정 뒤 다시 잼).
### A13(master#18c2e66e 결정 A · 판정선 개정 02:38 — 「40좌석 RSS ≤ 320MB」 → **40좌석 seatkeep 물리 점유 합 ≤ 160MB** · 유휴 CPU ≤ 2% 불변 · 좌석당 RSS > 9MB = 경고(판정 아님))
- 측정 명령: `python3 ~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t3/harness/t3a13.py <target/release> <on|off> 1 5 20 40`(격리 cysd · 합성 좌석 seat.py · quiet = 좌석당 5초에 1줄 / noisy = 50ms 간격 약 215B).
- 물리 점유 = `proc_pid_rusage(pid, RUSAGE_INFO_V2)` 의 `ri_phys_footprint`(시험대 `t2copy/harness/a13.py` `footprint_mb` · 활성 상태 모니터 「메모리」 열과 같은 값) · seatkeep 칸 = 등록부 `seatkeep/*.json` 중 phase committed 이고 살아 있는 pid **전부(40좌석 = 40개)의 합** · 1초 표본 20초 창에서 그 합의 최댓값. RSS = `ps -o rss=` 같은 방식 합. cysd 칸 = cysd 1개의 같은 창 최댓값. CPU = 20초 창 누적 CPU 시간 차 ÷ 경과.
| 노브 · 부하 · 좌석 | seatkeep RSS 합 | seatkeep 물리 점유 합 | 좌석당 RSS / 물리 점유 | seatkeep CPU | 스레드 | cysd RSS | cysd 물리 점유 | cysd CPU |
|---|---|---|---|---|---|---|---|---|
| 켬 quiet 1 | 8.1 | 3.2 | 8.11 / 3.22 | 0.0% | 7 | 41.8 | 9.2 | 0.38% |
| 켬 quiet 5 | 40.4 | 16.0 | 8.08 / 3.20 | 0.0% | 35 | 43.5 | 10.9 | 0.30% |
| 켬 quiet 20 | 161.3 | 63.5 | 8.07 / 3.18 | 0.0% | 140 | 52.0 | 19.4 | 0.58% |
| **켬 quiet 40** | 324.4 | **127.6** | 8.11 / 3.19 | **0.0%** | 280 | 58.8 | 26.1 | 0.52% |
| 켬 noisy 1 | 8.2 | 3.3 | 8.22 / 3.28 | 0.0% | 7 | 44.4 | 11.8 | 0.34% |
| 켬 noisy 5 | 40.9 | 16.4 | 8.18 / 3.28 | 0.0% | 35 | 50.8 | 17.8 | 0.58% |
| 켬 noisy 20 | 163.8 | 66.0 | 8.19 / 3.30 | 0.20% | 140 | 79.2 | 42.6 | 1.57% |
| **켬 noisy 40** | 327.8 | **132.9** | 8.20 / 3.32 | 0.68% | 280 | 119.5 | 86.9 | 2.71% |
| 끔 quiet 1·5·20·40 | — | — | — | — | — | 42.2·43.7·49.9·56.4 | 9.6·11.1·17.3·**23.8** | 0.53·0.43·0.48·0.78% |
| 끔 noisy 1·5·20·40 | — | — | — | — | — | 43.4·49.3·75.6·112.7 | 10.7·16.0·42.7·**80.1** | 0.54·0.82·1.64·2.46% |
(단위 MB · 2026-11-12 02:39~02:50 · 릴리스 · 최종 코드 f3252d15)
- 판정: 40좌석 물리 점유 합 127.6MB(quiet) · 132.9MB(noisy) ≤ 160MB = **통과** · 유휴(quiet) CPU 0.0% ≤ 2% = **통과** · 좌석당 RSS 8.07~8.22MB < 9MB = 경고 없음.
- 비례(조건 ⑵): 좌석당 물리 점유 1→5→20→40 = quiet 3.22→3.20→3.18→3.19 · noisy 3.28→3.28→3.30→3.32MB — 좌석 수가 늘어도 좌석당 값이 늘지 않음(noisy 1→40 +0.04MB).
- cysd 쪽 증가분(조건 ⑷): 40좌석 cysd 물리 점유 켬 − 끔 = quiet 26.1 − 23.8 = **+2.3MB** · noisy 86.9 − 80.1 = **+6.8MB**(각 1회 · 잡음 폭 미측정). 노브 켬 40좌석 기기 부담 합(seatkeep + cysd 증가분) = quiet 약 129.9MB · noisy 약 139.7MB.
- 근거의 약한 곳(조건 ⑶): 「RSS 는 공용 라이브러리 페이지를 프로세스마다 다시 센다」의 직접 관측 = vmmap **표본 1**(seatkeep 1개 · 조종자 없음 · RSS 6.5MB 중 물리 점유 1.86MB · 스레드 5개 스택 상주 합 144KB). 40개 전부의 vmmap 은 안 함. 각 칸은 1회 측정(반복 없음).
- 이전 RSS 값(판정선 개정 전 같은 코드 02:22): quiet 40 = 323.7 · noisy 40 = 327.4(그때 판정선 320MB 초과 → 【결정필요】 02:38 → master#18c2e66e 결정 A).
### 뮤턴트(t3mutants2.py · 별도 git 작업트리 · 기준 회차 14종 전부 초록 확인 뒤)
| 뮤턴트 | 잡은 시험 | 놓친 시험 |
|---|---|---|
| T1~T9 · M09(전임 방어 줄 10) | 각 해당 시험(10/10 잡음) | — |
| M1 조종자 종속에서 밀림 갈래 다시 열기 | 단위 bound_send_output… | bound · flood_on(256KiB 역압이 큐를 4MiB 아래로 묶어 이 줄에 닿지 않음 = 겹 방어) |
| M2 역압 기다림 빼기 | bound(자식 안 멈춤 · 붙기 전 유실 10.79MB) · 실물 cysd stop(자식 안 멈춤) | flood_on(큐가 끝없이 커질 뿐 유실은 없음) |
| M3 조종자 종속에도 쓰기 기한 | bound(write_stalled) · stop(좌석 사망 · controller_lost) | — |
| M4 첫 조종자 전 꼬리 칸 제한 빼기 | 단위 · late_bound(유실 29.55MB) | — |
| M5 깨우기 빼기 | 단위 · bound(멈춘 채 135초 시간 초과) | — |
| M7 cysd 가 인자 안 줌 | stop(자식 안 멈춤 · write_stalled) · life(좌석 생존 = HUP 없음) | — |
| M8 끊김 종료 빼기 | life(좌석 생존) | — |
= 17/17 잡음(전임 표는 build.rs 「git 인덱스 부재」로 10/10 빌드 실패였음).

## 지시 없이 내린 판단
1. 손잡이 얼굴 = portable-pty `MasterPty`/`Child` 트레이트(필드 타입 불변 · 시험 구역 86곳 무수정) — 메모 §2(master 수용 c125bc97).
2. 운영 직접 접근 5곳(close_auth·handlers·repaint·governance·state)은 본문을 seat_proc 로 옮기고 옛 이름은 한 줄 위임으로 남김.
3. anyhow 직접 의존 승격(MasterPty 오류 타입 이름 필요 · Cargo.lock 1줄).
4. seatkeep 상태 폴더 동시 첫 만들기 경합 고침(T2 코드 · 노브 켬 시험에서 rc 3 재현 · 회귀 시험).
5. SIGNAL `target` 칸이 문자열이 아니거나 null 이면 모르는 값과 같이 거절 · `child_pid ≤ 0` 이면 어떤 신호도 안 보냄(T2 는 killpg(0) = 자기 그룹이 될 수 있었음).
6. cysd 는 RELEASE 를 쓰지 않음(그룹 SIGHUP = 결정 B 와 어긋남 · T6 판 내림 몫).
7. 시험 빌드 한정: seatkeep 상태 폴더 = 짧은 임시 폴더 `cskt-<pid>` · 조종자 잠금 = 그 안 `locks/<해시>.lock`(시험 데몬은 시작 잠금을 안 잡음 · 맥 소켓 104바이트) — 제품 경로(`state_dir` · `socket.with_extension("lock")`)와 다름.
8. 시험 환경 변수 `CYS_SEATKEEP_TEST_COMMIT_DELAY_MS` = `cfg(debug_assertions)`(릴리스 빌드에 문장 없음 · 제거 아님 — T2 시험대가 디버그 빌드로 씀).
9.(후임) 조종자 종속 모드 큐 상한 = `BOUND_QUEUE_BYTES` 256KiB(인자 없는 모드의 4MiB 와 따로) — 근거 = ^C 뒤 바이트 3.9MB→252KB · 재개 지연 110ms→7~20ms · 처리량 같음(위 표). 【중간】 01:46 에 알림.
10.(후임) 첫 조종자 전에도 역압: 꼬리의 남은 칸만큼만 읽고 꼬리가 차면 멈춤(cysd 기동~WELCOME 사이에 1MiB 넘게 쏟는 자식의 앞부분 유실 방지 · 시험 late-bound).
11.(후임) 붙을 때 따로 깨우는 줄은 넣지 않음 — 첫 프레임(WELCOME)을 쓴 쓰기 스레드의 `wake_readers` 가 깨움(넣었다가 뺌 · M5 가 깨우기 길 전체를 잡음).
12.(후임) 옛 인자 이름 `--end-on-controller-loss` 는 별칭으로 남기지 않음(바꿈 · 모르는 인자 = rc 2) — 쓰는 곳 cysd 1곳뿐(grep).
13.(후임) 전임 시험대 고침: t3misc 닫기 인자(`--surface N` → `surface:N` 위치 인자 · 시간 초과 셈) · t2copy/results 폴더 만듦 · 뮤턴트는 rsync 사본 대신 git 작업트리(`git worktree add --detach /private/tmp/sk3mut-wt` · 끝나고 제거함).
14.(후임 2회차) D1 시험 설계: 노브 켬 = 비차단 자식(「1초 진척 없음」까지 쓰고 끝남 · 띠 없음) · 노브 끔 = **막히는 256KiB 폭발 자식 + `read()` 안에서 SIGSTOP 한 cat 대역**(cysd 직접 읽기 스레드의 대역 · SIGCONT 뒤 그 대역이 EOF 까지 읽음). 까닭 = 비차단 자식은 직접 PTY 에서도 1,024 를 잃음(관측 2/2) → 차이는 「막히기 전까지 쓸 수 있는 양」이라 그것을 단언.
15.(후임 2회차) D2 부모 판정 = getppid 비교(kqueue 아님 · 간격 100ms = supervise 주기) · 기동 때 이미 1 이면 잃음으로 봄(0ms 시점에 첫 줄 전 cysd 가 죽어 놓친 것을 실측으로 찾음).
16.(후임 2회차) D7 새 끝 코드 rc 7(작업 폴더 사라짐) — cysd 문구 목록에 추가.
17.(후임 2회차) D3 = attach 를 `greet()` 로 쪼갬(검증 MA 패치 문자열은 바뀐 줄에 맞춰 같은 뜻으로 다시 씀 — 뮤턴트 표 「MA(검증)」).
18.(후임 2회차) D4 예외 = `state.rs` `spawned.child`/`spawned.master`(손잡이 결과를 Surface 로 옮기는 자리) · 넘기는 머리에 가져다 쓴 `probe_child(` 포함.
19.(후임 2회차) D1 기제 확인용 받는 쪽 실험 패치 1회(커밋 안 함 · 되돌림 확인).

## 확인 못 한 것 · 남은 것(후임 갱신 — 아래 전임 줄 중 다시 잰 것은 위 「후임 실측」이 정본)
- (fix1 · 이름이 바뀜: `OUT_QUEUE_CHUNKS` 64조각 → `OUT_SOFT_BYTES` 1MiB 바이트 대기열 · 답 기다림/닫는 중 5MiB) (후임) cysd 쪽 seatkeep 연결 채널(`OUT_QUEUE_CHUNKS` 64조각 × 최대 16KiB ≈ 1MiB)도 ^C 뒤 화면에 흐를 수 있음 — PLAUSIBLE · 미실측(seatkeep 쪽 252KB 만 잼).
- (후임) 켬이 끔보다 느림: 릴리스 약 14% · 디버그 약 28% — 원인 미규명(seatkeep 한 단계 더 · cysd demux→채널 복사 추정).
- (후임) 역압 중 FOREGROUND 질의는 출력 뒤에 줄 서므로 200ms 상한을 넘겨 「모름」이 될 수 있음(인자 없는 모드도 같음) · 입력 수신 확인도 그 뒤 — 미실측.
- (후임) 100좌석 시험의 남은 .json·.log·.lock 300개 = T4 몫(그대로).
- (후임) 이 맥에 T2 시험대(skt2-a13p5·p40)가 13시간 넘게 남긴 seatkeep 약 86개가 살아 있음(남의 것 · 안 건드림 · PTY 69개 사용 중 / 상한 511).
- 윈도우·리눅스 컴파일 = 미실측(그대로).
- (전임 줄 · 이력)
- 노브 켬 **전체** 재실행(f4b9b6ab 이후) · t2 `all`(대조군 = 인자 없는 seatkeep 자식 생존 포함) · A13 1·5·20·40 · 100좌석 잔존 파일 · 40좌석 동시 생성/닫기 · 뮤턴트 표 — 결과 파일 = `seatkeep-t3/results/{t2-all-t3.out,t3a13-on.out,t3misc.out,t3-mutants.tsv}`(돌리는 중 01:24~).
- M09 결정적 시험의 부하 아래 10/10(동시 빌드 중) — 미실행.
- 윈도우·리눅스 컴파일 점검 = 미실측(T2 관측 그대로 · `cfg` 로 가름: seatkeep 경로 = macos 만 · 그 밖 노브 켬 = 생성 실패 + 이유).
- 에이전트 좌석 입력 지연(전경 왕복 낌) 미실측.
- 끝난 좌석 등록부 3파일(.json·.log·.lock) 잔존 = T4 몫(수 측정은 t3misc).
