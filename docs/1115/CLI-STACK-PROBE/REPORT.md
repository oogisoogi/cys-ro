# cys 전체 시험의 스택 넘침(a3_strip_hook) 원인 조사 — REPORT

- TICKET=cysr-cli-stack-probe · 작성 worker-3(surface:2014) · 2026-11-12
- 가지 `probe/1115-cli-stack` ← `feat/1115-caller-r3` d5824332 · 브리프 `~/axdev/master/briefs/2026-11-12-cysr-cli-stack-overflow-probe.md`
- 표식: **[관측]** = 이 좌석이 명령을 돌려 얻은 값 · **[추정]** = 관측에서 이끈 판단(확인 안 됨) · **[바깥]** = 외부 원문
- ⚠ 이 사본은 `fix/1115-dev-opt1-stack-budget` 가지의 근거 문서다 — 여기서는 `stack_probe.rs` 가 컴파일에 붙어 있지 않다(문서로만). 탐침을 돌리려면 `probe/1115-cli-stack` 6a735ae1. 상시 예산 시험 = cys.rs `cli_stack_budget_tests`.
- 기계: macOS 26(Darwin 25.6) arm64 · 쪽(page) 16,384 바이트 · rustc 1.97.0 · clap 4.6.1 / clap_builder 4.6.0

## 0. 한 줄 요약

a3 시험은 **판이 바뀌어서 넘친 것이 아니다.** `Cli` 를 한 번 풀 때 디버그 빌드는 스택을 **약 2.10 MB** 쓰는데(clap derive 가 만든 함수 `Command::augment_subcommands` 한 개의 틀만 **1,766,848 바이트**), 시험 스레드는 2 MiB 라서 **남는 여유가 96~191 바이트**뿐이다. 이 여유는 세 판(270e3e21·6e2d29b7·d5824332) 모두 같다(틀 크기가 바이트까지 같음). 전체 실행에서는 다른 시험들이 동시에 메모리를 할당해 **맥 할당기가 가끔 느린 경로(+216 바이트)** 를 타고, 그때 넘친다 — 할당 부하를 붙이면 진짜 a3 시험이 **150회 중 11회** 넘쳤다(혼자 돌려도 기계 전체가 바쁠 때(부하 평균 40) 150회 중 6회 넘침). 같은 넘침은 11-11 충돌 보고서에 a3 말고도 **Cli 를 푸는 시험 6종에서 31건** 있다. 릴리스 빌드는 같은 풀이에 **약 111 KB**(디버그의 1/19)만 쓴다 — 맥 주 스레드(8 MiB)는 넉넉하고, 윈도 주 스레드(1 MB) 대비는 약 11%(맥 arm64 측정값으로 환산 · 윈도 실측 아님). 고침 안은 §6 — 1순위 = 이 크레이트만 디버그 최적화 1단(동작 무변 · 실측 필요 스택 −89%).

## 1. 필요 스택 — RUST_MIN_STACK 이분법 (브리프 2-1)

방법: `docs/1115/CLI-STACK-PROBE/bisect.sh <시험 바이너리> <시험 이름>` — 64 KiB~8 MiB 를 4 KiB 해상도로 이분, 통과 = rc 0. 시험 바이너리 = 각 판 `cargo test --bin cys --no-run`(디버그, 같은 target 폴더 · 바이너리 복사 보관).

**계기 확인 [관측]**: d5824332 에서 RUST_MIN_STACK=65,536 → 넘침 · 262,144 → 넘침 · 2,097,152 → 통과. 계기가 대상을 만난다.

| 판 | 시험 수 | 1회차 | 2회차 | 3회차 |
|---|---|---|---|---|
| 270e3e21(기준) | 757 | 넘침 2,077,216 / 통과 2,081,280 | 같음 | 같음 |
| 6e2d29b7(caller r3 머리) | 762 | 같음 | 같음 | 같음 |
| d5824332(창 관문 병합 머리) | 762 | 같음 | 같음 | 같음 |

- 경계는 흔들리지 않는다(9회 모두 같은 값) **[관측]**.
- 이 값은 쪽 단위로 반올림된다: 2,077,216 → 127쪽(2,080,768) · 2,081,280 → 128쪽(2,097,152 = 2 MiB). 즉 「127쪽이면 넘치고 128쪽(기본값)이면 통과」 — 판 차이가 이 해상도(16 KiB)에서는 보이지 않는다 **[관측]**.
- 실제 스레드 크기(`pthread_get_stacksize_np`): 기본 시험 스레드 **2,109,440**(= 2 MiB + 12,288) · RUST_MIN_STACK=16 MiB 일 때 16,789,504(= 16 MiB + 12,288) **[관측 · 탐침 `stack_probe_thread_facts`]**.

### 1-1. 바이트 단위 여유 — 칠하기(painting) 탐침

쪽 단위로는 판 차이·여유가 안 보여서 스택 칠하기 탐침을 붙였다(`docs/1115/CLI-STACK-PROBE/stack_probe.rs` · cys.rs `mod tests` 안 `mod stack_probe { include!(..) }` · 전부 `#[ignore]`). 원리: 지금 틀 아래 6 MiB 를 0xA5 로 칠함 → 일감 실행 → 아래부터 훑어 처음 지워진 바이트 = 최저 수위. 큰 틀의 머리말 탐침(`str xzr, [sp]` 쪽마다)이 0 을 쓰므로 넘침 판정과 같은 지점을 잡는다.

| 일감(디버그 d5824332 · 스레드 16 MiB) | 일감이 쓴 스택(바이트) **[관측]** |
|---|---|
| `Cli::command()` 만 | 2,100,751 |
| `Cli::try_parse_from` (7개 동사·오류 꼴 모두 같은 값) | 2,101,151 |
| a3 시험 본문 전체 | 2,106,887 |

**진짜 a3 시험의 여유 [관측 + 산술]** — `stack_probe_a3_margin`: 기본 시험 스레드보다 정확히 한 쪽 큰 스레드(2,125,824)에서 96 바이트 틀을 n 단 쌓고 a3 본문을 부름 → n=162 통과 · 163 넘침(조용할 때·부하 아래 둘 다). 탐침 경로가 진짜 시험보다 더 쓰는 틀(탐침 시험 함수 800 + `pad(0)` 96 + 클로저 32 = 928)을 빼면, **기본 2 MiB 시험 스레드에서 진짜 a3 시험의 남는 스택 = 96 이상 192 미만 바이트**(시험 감싸개 틀 차이 ±32 바이트 오차). 틀 크기는 §2 표의 도구로 잰 값.

### 1-2. 판 기울기

| 판(날짜) | `Command` 변형 수 | `Command::augment_subcommands` 틀 | `ChannelAction::…` 틀 |
|---|---|---|---|
| v1.1.10(10-23) | 77 | 1,765,408 | 309,520 |
| 270e3e21(11-06) | 78 | 1,766,848 | 309,520 |
| 6e2d29b7(11-12) | 78 | 1,766,848 | 309,520 |
| d5824332(11-12) | 78 | 1,766,848 | 309,520 |

- 20일 동안 +1,440 바이트(변형 1개 추가분) · 270e3e21 → d5824332 는 **0 바이트** **[관측]**.
- 변형 수는 v0.14.50(10-11) 77 · v0.14.52 79 · v1.1.10 77 · 그 뒤 78 로 거의 늘지 않았다 — 저장소 주석(`cys.rs` 3597·3617·3632행 · 984행)대로 1.1.8 부터 「최상위 열거형에 변형을 더하면 j3 시험이 2 MB 시험 스레드에서 넘친다」 는 실측 때문에 새 동사를 clap 밖에서 처리해 왔다 **[관측: 소스 · 변형 수는 `enum Command {` 블록의 4칸 들여쓴 대문자 줄 셈]**.
- **다음 판에서 터질지 [추정 · 근거 = 위 숫자]**: 여유가 96~191 바이트이므로 `Command`·`ChannelAction` 같은 큰 열거형에 **인자 하나만 더해도**(이번 20일 동안 변형 1개 = +1,440 바이트) 2 MiB 시험 스레드에서 Cli 를 푸는 모든 시험이 **매번** 넘치는 상태로 바뀐다. 지금의 「가끔」 은 「항상」 직전이다.

## 2. 넘치는 순간의 호출 사슬 (브리프 2-2)

**lldb 는 쓰지 못했다 [관측]**: 이 맥은 `DevToolsSecurity -status` = 「Developer mode is currently disabled」 — `lldb -b … process launch` 가 디버그 권한 승인을 기다리며 300초 동안 멈췄다(권한 창이 화면에 떴을 수 있음 · 내가 띄운 debugserver pid 74457 1개를 끔). 대신 **맥 충돌 보고서(`~/Library/Logs/DiagnosticReports/*.ips`)** 의 넘친 스레드 틀 목록과 **기계어 머리말의 정적 틀 크기**(`docs/1115/CLI-STACK-PROBE/frame_size.py` — `stp …[sp,#-N]!` + 탐침 고리 `sub x9, sp, #P, lsl #12` + `sub sp, sp, #M`)로 대신했다.

backtrace 원문 = `evidence/crash-d582-2077216.backtrace.txt`(RUST_MIN_STACK=2,077,216 · d5824332 · 07:43) · `evidence/crash-a3-fullrun-2026-11-11-182606.backtrace.txt`(다른 좌석 전체 실행의 a3 넘침) · `evidence/crash-probe-margin-2026-11-12-075221.backtrace.txt`.

| 깊이 | 함수(디버그 d5824332) | 틀(바이트) **[관측]** |
|---|---|---|
| 0 | libtest → 시험 감싸개 · 스레드 시작 | 시험 함수 진입 깊이 ≈2.6 KB(탐침 관측) |
| 1 | `tests::a3_strip_hook_…` | 4,864 |
| 2 | `<Cli as Parser>::try_parse_from` | 1,488 |
| 3 | `<Cli as CommandFactory>::command` | 1,488 |
| 4 | `<Cli as Args>::augment_args` | 15,872 |
| 5 | **`<Command as Subcommand>::augment_subcommands`** (cys.rs:44 derive) | **1,766,848** |
| 6 | `<ChannelAction as Subcommand>::augment_subcommands` | 309,520 |
| 7~ | clap_builder `MKeyMap::push` → `Vec` 늘리기 → `realloc` → 맥 할당기 `_xzm_xzone_malloc_freelist_outlined` | 합 ≈6.8 KB |

- 재귀 없음 · 우리가 손으로 쓴 큰 match 팔(run)도 아니다 — **clap derive 가 우리 크레이트 안에 만든 함수 하나**가 2 MiB 의 84% 를 쓴다 **[관측]**. 디버그(opt-level 0)는 `Arg::new(..).long(..)…` 빌더 사슬의 임시값마다 따로 스택 칸을 잡아 틀이 변형·인자 수에 비례해 커진다 **[추정 · 근거: 최적화 1단에서 같은 함수가 177,120 바이트로 1/10 이 됨(§6)]**.
- 큰 틀 순위(디버그 · 상위 8): Command 1,766,848 · ChannelAction 309,520 · ScheduleAction 120,960 · QueueAction 109,504 · FeedAction 108,480 · SkillAction 84,464 · TeamTokenAction 58,992 · ApprovalAction 55,648 **[관측]**.
- 충돌 보고서의 맨 끝(넘친 순간)은 할당기다: 11-11 18:26 a3 넘침 = `_xzm_xzone_malloc_freelist_outlined ← xzm_realloc ← _malloc_zone_realloc ← realloc ← RawVecInner::finish_grow …` · 오늘 07:52 탐침 넘침도 같은 함수 **[관측]**.

## 3. 전체 실행에서만 넘치는 까닭 (브리프 2-3)

여유가 96~191 바이트로 0 에 붙어 있으므로(1-1), 「무엇이 수백 바이트를 메우나」 를 찾았다.

1. **같은 일감의 최저 수위 분포 [관측 · 탐침 `stack_probe_a3_quiet` / `stack_probe_a3_alloc_storm`]**: a3 본문 200회씩.
   - 조용할 때: 200/200 같은 값.
   - 다른 스레드 12개가 크기 16 B~300 KB 를 계속 할당·해제할 때: 198회는 같은 값, **2회(1%)는 +216 바이트 더 깊음**.
   - (주의: 두 탐침 시험 함수의 틀 차 336 바이트(352−16)는 교란이라 빼고 본 값이다.)
2. **진짜 a3 시험으로 재현 [관측]** — 탐침 경로 없이 기본 2 MiB 시험 스레드, 한 프로세스에 a3 + 부하만 내는 탐침(`stack_probe_storm_only`)을 `--test-threads=2` 로 나란히:
   - 부하와 함께: **150회 중 11회 넘침**(has overflowed its stack · rc 134)
   - a3 혼자: 150회 중 1회 실패(07:5x · 종류 미보관) · 08:2x 다시 150회 = **6회, 6회 모두 넘침**(그때 기계 부하 평균 40.8 / 22.5 / 14.3 — 다른 좌석 빌드·시험이 함께 돌던 중). 같은 프로세스 안 부하가 없어도 기계 전체가 바쁘면 넘친다 → 할당기 느린 경로를 부르는 조건이 「같은 프로세스의 동시 할당」 만은 아니다[추정 · 스레드가 CPU 를 옮겨 다닐 때의 할당기 캐시 경로일 수 있으나 확인 안 함]
3. **결론 [관측 + 추정]**: 전체 실행(시험 762개 · 기본 동시 16)에서는 Cli 를 푸는 시험이 다른 시험들의 할당과 겹칠 때 맥 할당기(xzone malloc)가 느린 경로를 타 수백 바이트를 더 쓰고, 여유 96~191 바이트를 넘는다. 「시험 수·순서가 바뀌어 첫 풀이 스레드가 바뀌었다」(좌석 12 추정)는 틀렸다 — 스레드는 모두 같은 크기이고, 차이는 동시 부하에 따른 할당기 경로다.
4. **a3 고유 문제가 아니다 [관측 · 충돌 보고서 집계]** — 11-11 하루의 cys 시험 바이너리 스택 넘침 보고서(보고서 생성기의 하루 상한 때문에 하한값):

| 시험 | 건수 |
|---|---|
| `aid_s5_cli_tests::aid_s5_reap_due_is_explicit_and_json_is_va…` | 16 |
| `tests::a3_strip_hook_digits_only_…` | 7 |
| `team_token_cli_tests::a3_approval_hook_subcommand_parses` | 2 |
| `b360_tests::b360_r2c_child…` | 2 |
| `team_token_cli_tests::d24_feed_reply_operator_flag_is_opt_in` | 1 |
| `tests::agy_autolink_cli_flag_and_wrapper_contract` | 1 |
| (이름 없는 스레드) | 1 |

   전부 `Cli` 를 푼다. 저장소에는 이미 같은 까닭의 우회가 있다 — `cys.rs` 42979·45021행 시험은 풀이를 8 MiB 스레드에서 돌리고(주석: 「int/1111 에서 이미 2048 KiB 경계」·「실측 2060 KiB 통과」), windows-health 의 A-ID S5 는 `RUST_MIN_STACK=8388608` 로 돈다 **[관측: 소스]**.

전체 실행을 디버거 아래 돌리는 3단계 후반은 하지 않았다 — 여유가 0 에 붙어 있어(「가까우면」 갈래) 필요 없고, lldb 가 이 기계에서 권한 창 없이 붙지 않는다.

## 4. 실제 프로그램의 여유 (브리프 2-4)

**릴리스 측정 [관측 · `cargo test --release --bin cys` 의 같은 탐침 · 맥 arm64]**

| 일감 | 디버그 | 릴리스 | 비 |
|---|---|---|---|
| `Cli::command()` | 2,100,751 | 111,115 | 18.9 |
| `Cli::try_parse_from` | 2,101,151 | 111,463 | 18.9 |
| a3 본문 | 2,106,887 | 113,191 | 18.6 |
| 부하 아래 a3 200회 분포 | 1% +216 | 200/200 같은 값 | — |

**제품에서 Cli 를 푸는 곳 = 전부 주 스레드 [관측: grep]**: `main`(3634행 `Cli::parse_from`) · `run()` 의 `Command::Actions`(6348행 `Cli::command()`) · `approval check` → `approval_strip_hook_digits`(6109·6130행 `Cli::try_parse_from` — `run()` 틀 위에서 **한 번 더** 푼다 = 제품의 최심 경로). `std::thread::spawn` 8곳(5844·6307·6739·18971·21496·23487·23775·30607행)은 풀이를 하지 않는다.

**최심 경로 합 [관측 틀 + 산술]**

| | 디버그 | 릴리스(맥 arm64) |
|---|---|---|
| `main` 틀 | 1,424 | 1,264 |
| `run` 틀 | 27,488 | 2,304 |
| `approval_strip_hook_digits` 틀 | 1,456 | 1,360 |
| 풀이 | ≈2,101,151 | ≈111,463 |
| 합(프로세스 시작 틀 제외) | **≈2.13 MB** | **≈116 KB** |

**주 스레드 크기**
- 맥: 8 MiB(브리프) — 디버그·릴리스 모두 여유 큼.
- 윈도: 저장소에 `/STACK`·`STACKSIZE`·스택 링커 인자 없음 **[관측: `build.rs`·`Cargo.toml`·`.cargo/config.toml`(rustflags 는 `+crt-static` 뿐)·`src-tauri/` grep 0건]** → MSVC 기본값 **1 MB [바깥: Microsoft Learn /STACK — 「For ARM64, x86, and x64 machines, the default stack size is 1 MB.」 https://learn.microsoft.com/en-us/cpp/build/reference/stack-stack-allocations]**. RUST_MIN_STACK 은 주 스레드에 무관 **[바깥: Rust std::thread — 「Currently, it is 2 MiB on all Tier-1 platforms.」·「the stack size of the main thread is not determined by Rust.」 https://doc.rust-lang.org/std/thread/index.html]**.
- **비율**: 릴리스 116 KB ÷ 1 MB ≈ **11%**(여유 ≈ 900 KB) · 디버그 2.13 MB ÷ 1 MB ≈ **2.0배 = 반드시 넘침**. ⚠ 윈도 x86_64 MSVC 기계어로 잰 값이 아니다 — 맥 arm64 값의 환산이다(윈도 실기 없음).
- 저장소 이력과 맞는다 **[관측: 소스]**: windows-health.yml 주석 = 「The DEBUG cys.exe overflows its main-thread stack on --help on this runner (… native exit 0xC00000FD at v0.14.51, 345b996d and 4ed79fdd)」 · release.yml W-GATE(0.14.52) = 포장된 릴리스 `cys.exe` 를 기본 스택에서 `--help`·`queue --help`·`queue list --help` 로 돌려 0 이 아니면 **차단**. 단 W-GATE 는 「넘치는가」 만 보고 **여유가 얼마인가는 재지 않는다** · 제품 최심 경로(`approval check` 의 두 번째 풀이)는 `--help` 보다 run 틀(릴리스 2,304) 만큼 더 깊다.

## 5. 동작 확인용 산출물
- `docs/1115/CLI-STACK-PROBE/bisect.sh` — RUST_MIN_STACK 이분법
- `docs/1115/CLI-STACK-PROBE/frame_size.py` — arm64 머리말 정적 틀 크기
- `docs/1115/CLI-STACK-PROBE/stack_probe.rs` — 칠하기 탐침(`#[ignore]` 7개) · cys.rs `mod tests` 에 `include!` 3줄
  - 실행: `RUST_MIN_STACK=16777216 cargo test --bin cys stack_probe_cli_parse -- --ignored --nocapture`
  - 여유: `RUST_MIN_STACK=2113536 STACK_PROBE_PAD=<n> cargo test --bin cys stack_probe_a3_margin -- --ignored --exact`
- `docs/1115/CLI-STACK-PROBE/evidence/` — 충돌 보고서의 넘친 스레드 틀(원본 .ips 는 기계 식별자가 있어 커밋하지 않음 · 틀만 텍스트로) · 11-11 집계 · 탐침 출력 원문(`probe-outputs.txt`) · opt-level 1 전체 시험 꼬리

## 6. 고침 안 (보고만 · 구현은 master 답 뒤)

RUST_MIN_STACK·시험 스레드 스택만 키우는 안은 내지 않는다(브리프).

| 안 | 무엇을 바꾸나 | 실제 프로그램 동작 | 필요 스택(디버그 풀이) | 비용·단점 |
|---|---|---|---|---|
| **A(권고 1순위)** 이 크레이트만 디버그 최적화 1단 | `Cargo.toml` 에 `[profile.dev.package.cys-terminal] opt-level = 1` 한 덩이(의존 크레이트·릴리스 프로필 무변) | 릴리스·배포물 **무변**. 디버그 바이너리는 같은 코드가 더 빨리 돈다(디버그 단언·넘침 검사는 그대로 켜짐 — 별도 설정) | **실측**: 2,101,151 → **229,351**(−89%) · `Command::augment_subcommands` 틀 1,766,848 → 177,120 · `ChannelAction` 309,520 → 39,312 → 2 MiB 시험 스레드 여유 ≈0.1 KB → **≈1.87 MB** · 윈도 디버그 주 스레드(1 MB)도 들어감[추정 · 맥 값 환산] | 디버거에서 지역 변수 일부가 「optimized out」 · cys 크레이트 디버그 컴파일이 느려짐(같은 기계 1m16s → 1m56s, 캐시 상태가 같지 않아 참고값) · 전체 시험 결과 = §6-1 |
| B 큰 변형의 인자를 `#[derive(Args)]` 구조체로 떼기(또는 `#[command(flatten)]` 하위 열거형으로 묶기) | 예: `Kill { .. }` → `Kill(KillArgs)` — 인자 만드는 코드가 변형마다 따로 함수(따로 틀)로 빠져 `augment_subcommands` 틀이 줄어든다 | CLI 표면(동사·옵션 철자·도움말 내용) **같게 만들 수 있음** — 단 도움말의 하위 명령 순서는 묶음 방식에 따라 바뀔 수 있어 확인 필요 | 미측정[추정: 묶음 K개면 최대 틀 ≈ 1/K] | `run()`·시험의 `Command::X { .. }` 패턴을 전부 고쳐야 함(변형 78 · 매치 자리 다수) — 큰 변경, 호출자 판정·창 관문 조각과 같은 파일이라 충돌 위험 |
| C CLI 전체를 넉넉한 스택의 스레드에서 돌리기 | `main` 이 8 MiB 스레드를 띄워 그 안에서 `parse` + `run` 후 종료 코드를 넘김 | **바뀜**(주 스레드 → 작업 스레드 · 신호 처리기·`process::exit` 는 프로세스 전역이라 동작은 같을 것[추정]) | 시험은 **그대로 넘침**(시험은 `main` 을 안 지나 libtest 스레드에서 직접 푼다) | 시험 문제를 못 고친다 — 윈도 디버그 `cys.exe` 용 보조안일 뿐 · 릴리스는 이미 여유 ≈89%라 필요 낮음 |
| D(A·B 와 함께) 예산 시험 | 칠하기 탐침을 상시 시험으로: 「디버그 풀이 필요량 ≤ 예산(예: 1 MiB)」 을 단언 | 무변 | — | 넘침이 「가끔 SIGABRT」 대신 **늘어난 순간 결정론적으로 붉어진다** · 맥 전용 API(`pthread_get_stackaddr_np`) — 리눅스·윈도 판은 따로 |

**권고**: A 를 먼저(한 덩이 · 동작 무변 · 실측 −89%) + D 로 다시 깎아 먹히는 것을 숫자로 막는다. B 는 A 뒤에도 틀이 다시 커질 때의 구조적 해법으로 남긴다. 단점(A): 디버그 바이너리의 디버거 경험이 나빠지고, 「디버그에서만 드러나는 버그」(최적화가 감추는 미정의 동작) 탐지가 조금 약해질 수 있다[추정]. 확신도: A 의 효과 = 높음(실측) · A 의 부작용 범위 = 중간(§6-1 전체 시험 1회).

### 6-1. A 안 전체 시험 1회

- 명령: `cargo --config 'profile.dev.package.cys-terminal.opt-level=1' test --bin cys -- --test-threads=8`(d5824332 + 탐침 · 이 가지 작업 폴더)
- 결과 **[관측]**: `test result: ok. 761 passed; 0 failed; 7 ignored`(무시 7 = 이 탐침) · 796.52초 · rc 0 · 원문 = `evidence/full-opt1.tail.txt`
- 같은 부하 재현(§3-2 와 같은 방법 · opt-level 1 바이너리): **150회 중 0회** 넘침 — 기준 디버그는 같은 방법 11/150.
- 한계: 1회 실행이다. 시간·경합에 민감한 시험(브리프가 범위 밖으로 둔 send_settle·pending_requests·u18)이 이 1회에 안 흔들렸다는 것뿐 — 「영향 없음」 의 증명은 아니다. cysd·cys-app 은 이 설정에서 돌리지 않았다(같은 패키지인 cysd 도 opt-level 1 이 된다 — 적용 전에 `cargo test --bin cysd` 전체 1회 필요).

## 7. 확인 못 한 것
- 윈도 x86_64 MSVC 빌드의 실제 필요 스택(실기 없음 · 이 좌석에서 윈도 대상 컴파일도 안 함).
- lldb 실시간 backtrace(개발자 모드 꺼짐) — 충돌 보고서·정적 틀로 대체.
- 첫 「혼자 150회 중 1회 실패」 의 종류 — 출력 미보관(재측정 6/150 은 전부 넘침).
- 충돌 보고서 집계는 하루 상한이 있어 하한값이다 — 11-12 전체 실행(msv-caller5)의 넘침은 보고서 목록에 안 잡혔다.
- 할당기 느린 경로가 정확히 어느 조건에서 +216 바이트를 쓰는지(xzone malloc 내부) — 바깥 원문 미조사.
