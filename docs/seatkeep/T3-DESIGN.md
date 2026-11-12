# T3 설계 메모 — 좌석 프로세스 손잡이 · seatkeep 경유 구현 (TICKET=cysr-seatkeep-t3)

- 작성 = worker(surface:2001) · 2026-11-12 00:3x KST · 기준 커밋 `a48d36e1`(가지 `feat/seatkeep-t3`) · 줄 번호는 이 커밋 기준.
- 상위 = DESIGN.md §3-2 · §6 T3 · §7(master 판단) · T0-surface-state.md · HANDOFF-seatkeep-t2.md(「알려진 결함」 15 · 「T3 로 넘길 것」 10).
- 표기: 【코드】 소스 판독 · 【실측】 이 좌석이 돌린 것 · 【추정】 근거는 있으나 안 잼.

## 0. 전제와 정직한 범위(독립 검증 1회 고침 반영 · master#8193a786 · #6e60316b · 2026-11-12 05:0x)
- **노브 켬 = 이 판에서 시험 전용.** 옛 판 독자는 두 칸 잠금(`"<pid> <출생시각>"`)에서 산 cysd 를 못 본다(독립 검증 REPORT 2-2': 기준선 lib 판독기 = 잠금 줄 통과 · 옛 cys doctor = 죽은 데몬 잔재의 stale pid 를 못 봄). 노브 기본 켬은 T4 차단 조건(HANDOFF 「T4 로 넘길 것」 맨 위)을 닫은 뒤에만.
- **인자 없는 경로(T2 동작) = 동작 같음 · 의도된 변경 3곳**: ① SIGNAL `child_pid ≤ 0` 이면 신호를 보내지 않음(전: `killpg(0)` 이 될 수 있었음) ② 등록부 폴더 동시 첫 만들기 경합 고침(`registry.rs` `AlreadyExists` → 다시 검사) ③ `CYS_SEATKEEP_TEST_COMMIT_DELAY_MS` 가 릴리스 빌드에서 무시됨(`cfg(debug_assertions)`). (전 문구 「한 줄도 안 바뀜」은 과장이었다.)
- **노브 켬 vs 직접 PTY = 구별되는 곳 1(D1 · 알려진 한계)**: 멈춘 조종자(cysd) 아래에서 seatkeep 의 역압은 자식이 큐 문턱(256KiB)+앞 단계만큼 앞서 쓰고 끝나게 하고, 그때 커널 PTY 버퍼에 남은 꼬리(≤ 1,024바이트)를 커널이 버린다. 직접 PTY 에서는 같은 폭발의 자식이 커널 버퍼(약 1KiB)에서 막혀 끝나지 못하므로 잃지 않는다. 시험 = `seat_tail_tests::seat_tail_known_limit_stalled_controller_child_exit`(켬 = 모자람 1..=1024 · 끔 = 자식이 6초 동안 막힌 채 · 모자람 0).
  - **맥 커널 동작 = 관측(탐침 각 2/2) + 공개 XNU 소스 대조(codex 1R ③ 표현으로 정정 · fix1)**: 마스터에서 `read()` 안에 잠든 독자가 있으면 자식의 **첫 write 가 이미 잠든 독자(`ptcread`)를 깨워 그 덩이를 read 로 옮긴 뒤, 나머지 출력 큐(t_outq)가 마지막 슬레이브 참조 close 에서 버려진다**(500바이트 한 번 쓰기 = 501/500 은 커널 큐에 보존된 것이 아니라 이미 진행 중인 read 가 가져간 것). `read()` 밖이면 0/500 · 자식 회수·`waitid WNOWAIT` 와 무관(0/500 ×5 — 회수보다 앞선 fd close/TTY 정리에서 정해짐) · 커널 버퍼를 가득 채우고 끝나는 자식은 `read()` 안의 멈춘 독자가 있어도 첫 줄(102바이트)만 남고 1,024바이트를 잃는다(시험 노브 끔 비차단 자식 2/2). **조건 = 「세션 우두머리 종료」가 아니라 「마지막 슬레이브 close」**. 다만 세션 우두머리가 제어 터미널을 쥔 채 끝나면 커널이 터미널을 `REVOKEALL` 로 회수한다(다른 프로세스가 쥔 슬레이브 열림 포함 — T4 슬레이브 보유 안의 첫 검증 대상). 탐침 = 시험대 `harness/ptyprobe/` · 원 출력 = `results/ptyprobe/`.
    - 소스 줄(apple-oss-distributions/xnu `f6217f891ac0` = xnu-12377.1.9 · 2025-10-16): `bsd/kern/tty_dev.c` `ptcread` 642·680·685·691·700 · `ptsclose` 350·355·356·361 · `bsd/kern/tty.c` `ttylclose` 1993~1994 · `ttyclose` 418 · `ttyflush` 1840 · `bsd/kern/kern_exit.c` 2287·2312·2330·2336. 【추정 · 미실측】 끝나는 우두머리 안의 `ttywait`(PCATCH · `t_timeout` 0)가 바로 깨지는 까닭은 소스로 확정 못 함.
  - 받는 쪽(cysd 가 output_open EXITED 뒤 OUTPUT 을 버림)은 D1 의 기제가 아니다 — 받는 쪽을 열어 둔 실험 1회에서 EXITED final_offset(1,299,276) = cysd 가 받은 바이트(1,299,276) · EXITED 뒤 OUTPUT 0. 그래서 받는 쪽은 바꾸지 않았다(master#6e60316b C 안 함).
- **D2(생성 도중 cysd 사망)**: `--controller-bound` seatkeep 은 기동 때 부모 pid 를 재고 supervise(100ms)마다 바뀌었는지 본다 — 바뀌었거나 기동 때 이미 1(launchd)이면 `parent_lost` 로 끝남(전: 첫 조종자 상한 15초까지 무감독).
- **D7(작업 폴더·HOME 이 생성 직후 사라짐)**: seatkeep 은 자식 작업 폴더를 다시 찾지 않고 `"."`(cysd 가 확인하고 seatkeep 을 띄운 그 폴더)로 상속 · 그래도 실패하고 폴더가 없으면 rc 7(「작업 폴더가 사라짐」).
- **D4(직접 접근 게이트)**: 타입으로 막는 길(Surface `child`·`master` 를 손잡이 모듈 비공개 새 타입으로)은 시험 구역 약 86곳이 바뀌어(30곳 상한 초과) 차선 — 게이트가 `.child`·`.master` 필드 참조 자체를 보고, 손잡이로 넘기는 자리(`seat_proc::…(&x.child)` · 가져다 쓴 `probe_child(`)와 이름 붙은 예외(`declaration.rs` 어휘 · `governance.rs` 후손 기록 · `state.rs` 의 `spawned.*` = 손잡이 결과를 Surface 로 옮기는 자리)만 허용 · 대상 = `src/bin/cysd/` 하위 전체 + `src/*.rs`.

## 1. 직접 접근 자리 전수 표 (cysd 운영 코드)

계수 방법 = `src/**/*.rs` 중 `*_tests.rs`·`pty_test_support.rs`·`cys-seatkeep/` 를 빼고, `#[cfg(test)]` 가 붙은 `mod`/`fn`/`impl` 블록(중괄호 짝 맞춤 · 문자열·주석 제외)을 「시험 구역」으로 나눠 셌다(스크립트 = §8). 여러 줄로 이어진 `.master\n.lock()` 도 잡는다.
DESIGN §6 의 「`child.lock` 89 · `pty_master_fd` 14 · `master.lock` 2」는 **시험 구역을 포함한 수**였다 — 운영 구역만 세면 아래 13곳이다. 【실측 grep】

| # | 파일:줄 | 무엇을 하나 | 손잡이의 어느 동작으로 |
|---|---|---|---|
| 1 | `state.rs:7745-7753` | `native_pty_system().openpty(..)` | **생성** |
| 2 | `state.rs:7918-7931` | `pair.slave.spawn_command(builder)` · `process_id()` · `drop(pair.slave)` | **생성** |
| 3 | `state.rs:7935` | `root_registration::observe(child.as_mut(), pid)` | 생성 직후 관측 — 손잡이의 `Child` 얼굴을 받는다(변경 없음) |
| 4 | `state.rs:7937-7944` | `try_clone_reader()` · `take_writer()` | **생성**(출력 읽기 얼굴 · 입력 쓰기 얼굴) |
| 5 | `state.rs:7969` | `pair.master.as_raw_fd()` 캐시 | **전경 질의** 준비 |
| 6 | `state.rs:8025-8026` | `master: Mutex::new(pair.master)` · `child: Mutex::new(child)` | 손잡이 보관(필드 타입 그대로) |
| 7 | `state.rs:8067` | `pty_master_fd: AtomicI32::new(..)` | **전경 질의** 준비 |
| 8 | `state.rs:3096` | `foreground_pgid_now` = `tcgetpgrp(캐시 fd)` | **전경 질의** |
| 9 | `state.rs:8398` | 읽기 스레드 EOF 뒤 `child.try_wait()`(1초 뒤 한 번 더) | **종료 감지·회수** |
| 10 | `governance.rs:6489` | 닫기: 후손 SIGKILL 뒤 `child.kill()` + `child.wait()` | **닫기**(신호 + 회수) |
| 11 | `handlers.rs:3867` | `owned_submit_root_live`: `child.try_lock()` + `process_id()` (+윈 `try_wait`) | **생존 질의** |
| 12 | `close_auth.rs:106` | `probe_child(&s.exited, &s.child)` → `try_wait` | **종료 감지**(닫기 인가 탐침) |
| 13 | `repaint.rs:517` | `resize_pty`: `s.master.lock().resize(..)` | **크기** |

- 입력 쓰기 경로 `write_tx`(운영 14곳)는 PTY 에 직접 닿지 않는다 — 전부 `writer_gate` 채널에 넣고, PTY 쓰기는 좌석별 writer 스레드 하나(`state.rs:7962` `run_writer_loop_tracked(writer, ..)`)가 #4 의 쓰기 얼굴로 한다. → 손잡이 앞단 · **변경 없음**.
- 신호: 운영 cysd 가 좌석에 보내는 신호는 #10 하나(`child.kill()` = portable-pty: `kill(pid, SIGHUP)` → 50ms×4 회수 확인 → `kill(pid, SIGKILL)` · `vendor/portable-pty/src/lib.rs:340-370`)와 그 앞의 후손 `kill_pid`(sysinfo 후손 트리 · pid 단위 SIGKILL · `governance.rs:6482-6485`)다. 후손 처치는 cysd 가 pid 로 하므로 손잡이 밖에 그대로 둔다(seatkeep 경유에서도 같은 코드가 같은 후손을 친다 — 좌석 루트 pid = 자식 pid 계약 · T0 #8).
- 시험 구역의 직접 접근(`child.lock` 86 · `pty_master_fd` 8 · `master.lock` 1 · `write_tx` 10)은 **손대지 않는다** — 이들은 `Box<dyn Child>`/`Box<dyn MasterPty>` 얼굴을 통해 부르므로 노브 켬에서는 seatkeep 구현으로 간다(차이를 좁게 · 브리프 §3).

## 2. 손잡이 인터페이스

새 모듈 `src/bin/cysd/seat_proc.rs`(「좌석 프로세스 손잡이」). **손잡이 = portable-pty 의 두 얼굴(`MasterPty`·`Child`) + 읽기·쓰기 + 전경 질의**를 한 번에 만들어 주는 생성 함수와, 운영 코드가 그 얼굴에 닿는 함수 몇 개.

```rust
pub(crate) enum Backend { Direct, Seatkeep }           // 노브(§3)
pub(crate) struct Spawned {
    pub master: Box<dyn MasterPty + Send>,  // 크기(resize·get_size)
    pub child: Box<dyn Child + Send + Sync>, // 종료 감지(try_wait) · 회수(wait) · 신호(kill) · pid
    pub reader: Box<dyn Read + Send>,        // 출력
    pub writer: Box<dyn Write + Send>,       // 입력(seatkeep = INPUT id + 수신 확인까지 기다림)
    pub pid: u32,
    pub fg_fd: i32,                          // 직접 = master fd · seatkeep = FG_VIA_LINK(-2)
    pub link: Option<Arc<SeatLink>>,         // seatkeep 연결(전경 질의용 · 락 없는 경로)
}
pub(crate) fn spawn(ctx, size, builder) -> Result<Spawned, String>   // #1 #2 #4 #5
pub(crate) fn foreground_pgid(fd: &AtomicI32, link: Option<&SeatLink>) -> Option<i32>   // #8
pub(crate) fn reap_after_eof(child: &Mutex<..>)                       // #9
pub(crate) fn kill_and_reap(child: &Mutex<..>)                        // #10
pub(crate) fn owned_root_live(..) / probe_child(..)                   // #11 #12 (본문 이동만)
pub(crate) fn resize(master: &Mutex<..>, rows, cols)                  // #13
```

- **Surface 필드 타입은 그대로**(`master`·`child`·`pty_master_fd`) — 시험 구역 86곳이 그대로 컴파일·동작한다. 새 필드 1개: `#[cfg(unix)] seat_link: Option<Arc<SeatLink>>`(전경 질의가 `master` 뮤텍스를 잡지 않는 계약 `state.rs:2403` 유지).
- **직접 PTY 구현** = 지금 코드를 그대로 옮긴다(논리 변경 0).
- **seatkeep 경유 구현**(맥 · `cfg(target_os="macos")` · 그 밖 유닉스 = 노브 켜면 생성 실패 + 이유):
  1. 실행 파일 = `current_exe()` 와 같은 폴더의 `cys-seatkeep`(브리프 §1-1 · 시험 빌드는 `target/<p>/deps/` 이면 한 단계 위). 없거나 실행 불가 = **생성 실패 + 이유**(직접 PTY 로 내려가지 않음 · §1-2).
  2. 기동 = `cys-seatkeep --dir <상태폴더> --id <pid hex>-<시작 hex>-<순번> --controller-exe <감사 토큰이 보일 경로(§5)> --lock <데몬 잠금 파일> --rows R --cols C -- <argv…>` · 환경 = builder 의 전체 환경(env_clear 뒤 그대로) · 작업 폴더 = builder 와 같은 규칙(폴더가 없으면 HOME — portable-pty `as_command` 와 같음) · stdin/stdout = null · stderr = cysd 것 상속.
  3. 붙기 = 등록부 `committed` 또는 소켓이 생길 때까지(상한 5초 · 그사이 seatkeep 이 끝나면 rc 와 함께 실패) → 소켓 피어 pid = 내가 띄운 seatkeep pid 확인(DESIGN §3-2 「반대 방향」) → HELLO(`core:1`) → WELCOME(좌석 0 의 `child_pid`) 또는 REJECT(이유 그대로 실패 문구에).
  4. 연결 스레드 1개가 프레임을 나눈다: OUTPUT → 읽기 얼굴(오프셋 연속 확인 · 구멍이면 로그) · INPUT_ACK → 쓰기 대기자 깨움 · FOREGROUND_IS → 전경 대기자 · EXITED → 종료 상태 기록 + 읽기 EOF + **즉시 EXIT_ACK** · 연결 끊김 = 종료로 접음(`seatkeep_disconnected` — seatkeep 이 죽으면 마스터가 닫혀 자식도 SIGHUP 으로 끝난다 【코드 DESIGN §1-2】).
  5. 쓰기 = 256KiB 조각마다 INPUT(id = `시작 시각<<32 | 순번`) → INPUT_ACK 까지 기다림(직접 PTY 의 「write 가 돌아오면 PTY 에 들어감」과 같은 뜻 · 조각 상한 덕에 seatkeep 입력 대기 1MiB 를 넘지 않음) · 끊김·종료 = 오류.
  6. 크기 = RESIZE(확인 프레임 없음 · `get_size` = 마지막으로 보낸 값) · 전경 = FOREGROUND 왕복(상한 200ms · 넘으면 `None` = V2 종전 경로) · 신호/닫기(`Child::kill`) = **SIGNAL `{"sig":1,"target":"leader"}`** → 50ms×4 EXITED 확인 → SIGNAL `{"sig":9,"target":"leader"}`(직접 PTY 와 같은 대상 · §6 결정 B) · `wait` = EXITED 까지(끊김 = 오류로 끝). RELEASE(그룹 SIGHUP)는 결정 B 와 어긋나 T3 에서 쓰지 않는다(판 내림 = T6).
  6-1. **좌석 수명 = 직접 PTY 와 같게**(master#c125bc97 ②): cysd 는 seatkeep 을 늘 `--controller-bound`(옛 `--end-on-controller-loss` 를 master#77162b13 로 넓힘 — 아래 6-1') 로 띄운다 → 조종자(cysd) 연결이 끊기면(또는 기동 뒤 15초 안에 아무도 안 붙으면) seatkeep 이 기록 1줄 · 등록부 `ended_controller_lost` 를 남기고 스스로 끝난다 = 커널이 PTY 마스터를 닫아 좌석에 SIGHUP(cysd 가 마스터를 쥐던 지금과 같은 경로). 인자 없으면 T2 동작 그대로. ⚠T4 가 입양을 켤 때 이 인자를 뺀다(`seat_proc.rs` 그 자리 주석). 그래서 위험 1(조종자 없이 사는 좌석)은 T3 에서 없다.
  6-1'. **출력 폭주 = 조종자 종속 모드**(master#77162b13 · 후임 구현 f3252d15): 같은 인자가 있으면 ⑵ 조종자 큐가 `BOUND_QUEUE_BYTES`(256KiB)에 닿으면 seatkeep 이 PTY 읽기를 멈추고 반 아래에서 다시 읽는다(커널 역압 → 자식이 cysd 속도에 맞춰 멈춤 · 유실 0 · 첫 조종자 전에는 꼬리의 남은 칸만큼만 읽음) ⑶ 쓰기 기한 없음(`write_stalled` 없음 — 멈춘 cysd 아래서 자식도 멈춰 산다). 제어 큐 상한(`control_queue_full`)은 그대로. 상한을 4MiB 가 아니라 256KiB 로 둔 까닭 = ^C 뒤 흐르는 바이트·재개 지연 실측(HANDOFF 표).
  6-2. **출력 큐 상한**(master#c125bc97 ③): 연결 스레드 → 읽기 얼굴 큐 = 조각 64개(`sync_channel`) · 차면 연결 스레드가 기다린다 → seatkeep 쪽 밀림(꼬리)로 넘어간다. 상한 없는 큐를 두지 않는다. 폭주 실측 표 = HANDOFF.
  7. seatkeep 프로세스는 cysd 의 자식이다 → 연결 스레드가 끝날 때 `wait()`(좀비 방지). cysd 가 먼저 죽으면 launchd 로 넘어간다(설계 의도).

## 3. 노브

- 관례 = `knobs.rs`(환경변수 · 순수 판정 함수 + 얇은 읽기 껍질 · **켜는 값은 정책 파일에서 받지 않는다**). → `CYS_SEATKEEP=1` 만 켬 · 그 밖(없음·0·빈 값·다른 값) = 끔 · 정책 파일 키 없음.
- **데몬 단위**: 첫 좌석 생성 때 한 번 읽어 고정(`OnceLock`) — 같은 데몬 안에서 좌석마다 갈리지 않는다. 노브 켬 전체 시험 = `CYS_SEATKEEP=1 cargo test --bin cysd`(시험 프로세스 하나 = 한 값).

## 4. 잠금 파일(`cys.lock` = `socket_path.with_extension("lock")`) 형식 바꿈과 독자 표

쓰는 곳 = `deadman::claim_lock`(`deadman.rs:93-101` · 지금 = `"{pid}"`). 바꿈 = **노브 켬일 때만**(master#c125bc97 ① — 독자 먼저·작성자 나중 · 노브 끔 = 바이트까지 그대로 · 시험 `claim_lock_bytes_follow_knob`) `"{pid} {출생 시각 µs}"`(출생 시각 = `proc_pidinfo` PROC_PIDTBSDINFO `pbi_start_tvsec*1e6 + pbi_start_tvusec` — seatkeep `registry::process_start_us` 와 같은 식 · 못 읽으면 한 칸 그대로).

| 독자 | 파일:줄 | 지금 읽는 식 | 두 칸이면 | 처리 |
|---|---|---|---|---|
| deadman 홀더 pid | `src/bin/cysd/deadman.rs:83-90` | `s.trim().parse::<u32>()` | **None(= 구 락파일 · fail-closed) → 행 걸린 데몬 회수가 영영 안 됨** | 첫 칸만 읽게 고침 + 시험 |
| cys doctor | `src/bin/cys.rs:10453-10459` | 같음 | None → doctor 의 stale 판정 무력 | 같음 |
| factory_reset 격리 관문 | `src/factory_reset.rs:1503-1513` | `s.trim().parse::<u32>()` 실패면 **건너뜀** | **살아 있는 cysd 를 못 보고 리셋 진행**(안전 관문 우회) | 같음 · 시험 |
| GUI 갱신 로그 | `src-tauri/src/main.rs:8360-8366` | `trim().parse::<u32>()` | None(로그에 pid 빠짐) | 같음(첫 칸) |
| seatkeep 피어 | `src/bin/cys-seatkeep/peer.rs:208-230` | 첫 칸 pid · 둘째 칸 출생 시각(있으면 짝 대조) | 짝 대조 켜짐(의도) | 변경 없음 |
| 팩·스크립트 | `cysjavis-pack/bin/cys-dept:1273` · `javis_phoenix_harness.py:18,972,1110,1416` · `tests/test_dept_name_guard.py:131-136` · `test_d1_dept_ready_probe.py:51` · `scripts/tests/u2-smoke.sh:59` | 경로·존재만(내용 파싱 0) | 영향 없음 | — |

검색 = `grep -rn 'cys\.lock\|read_holder_pid\|lock_file_pid\|doctor_read_holder_pid'` (src · src-tauri · cysjavis-pack · scripts · update-worker · ui).

## 5. 감사 토큰 경로 규칙(인계 4)

seatkeep 은 조종자 경로를 `SecCodeCopyGuestWithAttributes(audit)` → 코드 경로로 얻는다. **앱 번들의 주 실행 파일이면 번들 경로**가 나온다(T2 실측: Homebrew 파이썬 = `…/Python.app`). cysd 는 `--controller-exe` 에 「seatkeep 이 나를 그렇게 볼 경로」를 넘겨야 한다 → 규칙: `<X>.app/Contents/MacOS/<이름>` 이고 `<X>.app/Contents/Info.plist` 의 `CFBundleExecutable` = `<이름>` 이면 `<X>.app`, 아니면 실행 파일 경로 그대로. 시험 = 임시 `Fake.app/Contents/{MacOS/<복사한 실행 파일>, Info.plist}` 를 띄워 **실제 Security 프레임워크가 보는 경로**(pid 로 조회)와 규칙 함수 결과가 같은지 + 번들 밖 복사본(대조군)도 같은지.

## 6. 직접 PTY 의 닫기 / 리더 종료 관측 표 (§1-3 · D7)

시험 = `src/bin/cysd/seat_d7_tests.rs`(좌석 = `sh 스크립트` · 같은 그룹의 손자 4종: g0 자식·HUP 기본 / g1 자식·HUP 무시 / o0 고아·HUP 기본 / o1 고아·HUP 무시). 【실측 00:39 · 커밋 ① 트리(직접 PTY 논리 무변경) · `cargo test --bin cysd seat_d7_tests -- --nocapture --test-threads=1` 3/3 · 결과 = 산 것 ○ / 죽은 것 ×】

| 경우 | g0 | g1 | o0 | o1 | 리더 | 왜(코드) |
|---|---|---|---|---|---|---|
| ⓐ 닫기 · 리더 HUP 기본 | × | × | × | **○** | × | g0·g1 = 후손 SIGKILL(`governance.rs:6482-6485`) · 리더 = SIGHUP · o0 = 리더(제어 프로세스)가 끝날 때 커널이 전경 그룹에 SIGHUP · o1 = 후손이 아니라 SIGKILL 을 안 받고 HUP 은 무시 |
| ⓐ' 닫기 · 리더 HUP 무시 | × | × | × | **○** | × | 리더 = SIGHUP 무시 → 유예 뒤 **리더 pid 에만** SIGKILL · 나머지 같음 |
| ⓑ 리더만 끝남 · 직후 | × | **○** | × | **○** | × | 커널의 전경 그룹 SIGHUP 만 · HUP 무시 손자는 산다 |
| ⓑ 그 뒤 닫기 | × | **○** | × | **○** | × | 리더가 이미 없어 후손 목록이 비고, `kill()` 은 이미 회수된 자식이라 신호 없음 |

**노브 켬 실측(00:5x)** = ⓐ·ⓑ 같음 · **ⓐ' 만 다름**(o1 = 직접 ○ / seatkeep ×). → 【결정필요】 → **master 결정 B**(master#fe07cc6a): SIGNAL 에 선택 칸 `target`(`"leader"` = 리더 pid 에만 · `"group"`/없음 = 그룹 · 모르는 값 = 거절) + `target` 이 있는 요청에만 SIGNAL_RESULT 답 · 회수 표시 잠금 안에서만 · 발행 전 확장이라 핵심 판 번호 그대로(proto.rs 머리 프레임 설명). cysd `Child::kill` 은 leader 로 보낸다.

**처음 적었던 예측(이력) 【코드 · 추정】**: 직접 PTY 의 `kill()` 은 **리더 pid 하나**에 SIGHUP→SIGKILL 이고, seatkeep 의 SIGNAL·RELEASE 는 **그룹 전체(killpg)** 다(`cys-seatkeep/main.rs:1045-1066`). 닫기는 앞에서 후손을 pid 로 다 치므로 보통 같지만, **리더가 HUP 을 무시하고 + 리더의 후손이 아닌 같은 그룹 고아(o1)** 가 있으면 직접 = o1 생존 · seatkeep = SIGKILL killpg 로 o1 사망. 같게 하려면 「리더 pid 에만」 보내는 SIGNAL 이 필요 = **T2 프로토콜 변경**(브리프 §9 ③) → 실측으로 확인되면 【결정필요】.

## 7. 위험 3줄 + 결정 거리

1. **노브 켬 + 입양 없음(T4 전)**: cysd 가 죽거나 내려가면 좌석이 **조종자 없이 산다**(seatkeep 의 존재 이유) — 그런데 아무도 입양하지 않아 phoenix 가 같은 대화를 새로 띄우면 **같은 대화에 작성자 둘**(㉙ · T1 선행 조건). → 노브 켬은 시험 좌석 전용으로만 · cysd 정상 종료 때 RELEASE 를 보낼지(= 지금처럼 죽게)는 T6(판 내림 RELEASE) 몫으로 두되, 【결정필요】 후보로 올린다.
2. **전경 질의가 입력 관문 안에서 소켓 왕복**: 직접 = 시스템 콜 1회 · seatkeep = FOREGROUND 왕복(상한 200ms). seatkeep 이 느리면 입력 계수 경로가 그만큼 늦는다(모르면 `None` = V2 종전 경로라 판정 방향은 안전).
3. **출력 역압이 사라진다**: 직접 = cysd 읽기 스레드가 멈추면 커널 버퍼가 차 자식이 멈춤 · seatkeep = 자식은 안 멈추고(T2 설계) cysd 쪽 연결 스레드가 받은 출력을 큐에 쌓는다(멈춘 동안 메모리 증가 · 64MiB 넘으면 경고 1줄). 연결 스레드가 10초 넘게 안 읽으면 seatkeep 이 조종자를 내보낸다(`write_stalled`) — 그래서 연결 스레드는 출력 때문에 막히지 않게 한다.

결정 거리(진행은 막지 않음 · 각자 기본값으로 진행): ⓐ §6 killpg 차이(실측 뒤) ⓑ 위험 1 의 정상 종료 RELEASE ⓒ seatkeep 에 `--rows/--cols` 인자 추가(프레임 프로토콜 무변경 · 기동 직후 120×35 로 뜨는 것 방지 — 기본값 = 추가하고 【지시 없이 내린 판단】으로 보고) ⓓ 좌석이 끝난 뒤 `seatkeep/<id>.{json,log,lock}` 3파일이 남음(등록부 정리 = T4 고아 정리 몫 · 기록 `.log` 은 사후 적발용이라 지우지 않음).

## 8. 재현

- 전수 표 계수 = scratchpad `regions.py`·`sites.py`·`fields.py`(커밋 ④ 에서 시험 안의 grep 게이트로 옮긴다).
- 잠금 파일 독자 = §4 검색 줄.

## A13 판정선 개정(master#18c2e66e · 2026-11-12 02:38)
- 「40좌석 seatkeep 합 RSS ≤ 320MB」 → **40좌석 seatkeep 물리 점유(phys_footprint) 합 ≤ 160MB**(좌석당 4MB) · 유휴 CPU ≤ 2%(불변) · RSS 는 함께 적고 좌석당 RSS > 9MB 면 경고(회귀 감시 · 판정 아님).
- 까닭(master) = 이 선의 목적은 사용자 기기의 메모리 부담 · RSS 는 공용 라이브러리 페이지를 프로세스마다 다시 셈(vmmap 표본 1: seatkeep RSS 6.5MB 중 물리 점유 1.86MB).
- 측정 방법·표(1·5·20·40좌석 RSS·물리 점유 · cysd 쪽 증가분) = `HANDOFF-seatkeep-t3.md` 「A13」.
