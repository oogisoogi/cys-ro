# HANDOFF — TICKET=cysr-dev-opt1-stack-budget

- 발주 = cmux master `[master#dd7821a1]` 2026-11-12 08:33 · 작성 worker-3(surface:2014)
- 가지 `fix/1115-dev-opt1-stack-budget` ← v1.1.14 `270e3e21`(caller 가지 위가 아님 — 1.1.15 통합에 독립 조각)
- 근거 = `docs/1115/CLI-STACK-PROBE/REPORT.md`(조사 가지 `probe/1115-cli-stack` 6a735ae1 의 사본)

## 1. 바뀐 것
1. **A** — `Cargo.toml` 끝 `[profile.dev.package.cys-terminal] opt-level = 1`. dev·test 프로필에서 이 패키지(lib `cys` · bin `cys` · bin `cysd`)만 최적화 1단. 릴리스 프로필·의존 크레이트 무변.
   - 같은 패키지를 path 의존으로 쓰는 `src-tauri`(cys-app)의 디버그 빌드에서도 lib `cys` 가 최적화 1단이 된다(cys-app 크레이트 자체는 그대로).
2. **D** — `src/bin/cys.rs` `cli_stack_budget_tests::cli_parse_stack_need_stays_within_budget`(상시 · `#[cfg(all(test, target_os = "macos"))]`). 16 MiB 측정 스레드에서 스택 칠하기로 `Cli::try_parse_from` 5종의 필요 스택 최댓값을 재 `≤ 1 MiB` 단언 · 하한 32 KiB(계기 확인).

## 2. 이번에 지우지 않은 같은 까닭의 우회(목록만 · 윈 실측 없이 걷지 않는다)
| 자리(이 가지 줄 번호) | 무엇 |
|---|---|
| `src/bin/cys.rs` 44715~44720 | j3 시험: 파싱 + `run` 을 8 MiB 스레드에서(`stack_size(8 << 20)`) |
| (caller r3 가지 `feat/1115-caller-r3` d5824332 cys.rs 42979) | `--operator` 떼기 시험의 파싱을 8 MiB 스레드에서 — 이 가지(270e3e21)에는 없음 |
| `.github/workflows/windows-health.yml` 1472 | A-ID S5 `cargo test --bin cys aid_s5_cli_tests::` 에 `RUST_MIN_STACK=8388608` |
| `.github/workflows/windows-health.yml` 1677~1717 | 「스택 넘침 측정 — 맨 뒤」 디버그 `cys.exe --help` 종료 코드 측정(비차단) |
| `.github/workflows/windows-health.yml` 1386~1440 · `release.yml` 1336~ · `windows-build.yml` 217 | 릴리스 `cys.exe --help` 기본 스택 측정·W-GATE(차단) — 이것은 우회가 아니라 제품 판정이므로 유지가 맞다 |
| `src/bin/cys.rs` 19 · 467~468 · 982~983 · 3498 · 3518 · 3533 · 22591 | 「최상위 `Command` 에 변형·인자를 더하면 j3 시험이 2 MiB 시험 스레드에서 넘친다」 → 동사를 clap 밖에서 처리한 자리의 주석(갱신 3동사 · spawn-outside-job · rotate 확장 · `--operator` · pack-plan · 0.14.52 두 변형 · dept-status) |

걷어 낼 조건(제안): ① 윈도 러너에서 opt-level 1 디버그 `cys.exe --help` 3종이 기본 스택(1 MB)에서 0 으로 끝나는 것을 실측 ② `aid_s5_cli_tests::` 를 `RUST_MIN_STACK` 없이 윈도 러너에서 통과. 그 전에는 위 목록을 건드리지 않는다.

## 3. 뒤에 남길 구조 해법 — B(이번에 안 함)
큰 변형의 인자를 `#[derive(Args)]` 구조체로 떼거나(`Kill { .. }` → `Kill(KillArgs)`) 최상위 열거형을 `#[command(flatten)]` 하위 열거형 K개로 묶으면, 인자 만드는 코드가 변형·묶음마다 따로 함수(따로 틀)로 빠져 `Command::augment_subcommands` 틀(디버그 opt0 1,766,848 · opt1 177,120 바이트)이 줄어든다[추정: 묶음 K개면 최대 틀 ≈ 1/K · 미측정]. CLI 표면은 같게 만들 수 있으나 도움말 하위 명령 순서 확인 필요 · `run()`·시험의 `Command::X { .. }` 패턴 전수 변경이라 큰 변경. **발동 조건**: 예산 시험이 opt-level 1 에서도 붉어질 때(필요 스택 > 1 MiB — 지금 ≈229 KB 라 약 4.5배 여유).

## 4. 시험·측정 결과 [관측 · 2026-11-12 · 맥 arm64 · 커밋 7e9c2405 vs 기준선 270e3e21]

### 4-1. debug-assertions · overflow-checks
- `cargo rustc --bin cys -v -- --print cfg`: cys 바이너리 rustc 명령줄 = `-C opt-level=1 … -C debug-assertions=on` · 출력 cfg 에 `debug_assertions` 있음.
- overflow-checks 는 cargo 가 명시하지 않는다 → rustc 규칙 「If not specified, overflow checks are enabled if debug-assertions are enabled, disabled otherwise.」(https://doc.rust-lang.org/rustc/codegen-options/index.html) — debug-assertions=on 이므로 켜짐.

### 4-2. 전체 시험 1회씩(--test-threads=8 · 기준선과 고침을 같은 시각대에 나란히)
| 묶음 | 기준선 270e3e21(opt0) | 고침 7e9c2405(opt1) |
|---|---|---|
| `--lib` | 1203 통과 · 0 실패 · 2 무시(564.51초) | 1203 통과 · 0 실패 · 2 무시(553.43초) |
| `--bin cys` | 755 통과 · **1 실패** · 1 무시(761.58초) | **757 통과**(예산 시험 +1) · 0 실패 · 1 무시(762.57초) |
| `--bin cysd` | 3225 통과 · **2 실패** · 15 무시(631.05초) | 3225 통과 · **2 실패** · 15 무시(602.55초) |

실패 이름 대조(수가 같아도 이름이 다르다):
| 실패 | 어디 | 판정 |
|---|---|---|
| `tests::dbg_r12_init_pack_wires_profile_skill_links` | 기준선만 | **폴더 위치 탓** — 기준선 폴더(scratchpad `/private/tmp/…/wt-base`)에서 단독 2/2 실패 · 고침 폴더(`~/axdev/.wt/…`) 단독 2/2 통과 · opt-level 0 빌드도 `~/axdev/.wt/cys-stack-probe` 에서 단독 통과 → opt-level 무관[관측] |
| `state::tests::dbg_r12_seat_profile_wired_before_agent_exec` · `state::tests::dbg_r12_update_lane_restore_seat_gets_link_before_exec` | 기준선만(cysd) | 같은 dbg_r12 계열 · 같은 폴더 위치 탓으로 본다[추정 — 단독 재실행 안 함] |
| `native_publication::tests::native_core_stages_privately_and_activates_only_after_matching_capability` | 고침만(cysd) | `Native(Ambiguous("96897,22650"))` — 후보 pid 2개 · 그때 기준선 cysd 전체 시험이 같은 기계에서 함께 돌고 있었음 · 고침 폴더 단독 3/3 통과 → 동시 실행 간섭[추정] |
| `handlers::tests::u18_cwd_blocked_observed_under_sandbox_read_deny`(+ 자식 `u18_inner_sandboxed_cwd_probe`) | 고침만(cysd) | 브리프가 범위 밖으로 둔 흔들리는 시험(u18) · 고침 폴더 단독 2/2 통과 |

### 4-3. 뮤턴트 2
| 뮤턴트 | 결과 |
|---|---|
| Cargo.toml `[profile.dev.package.cys-terminal] opt-level = 1` 두 줄 제거 | **붉음** — 「Cli 풀이 필요 스택 2101151 바이트 > 예산 1048576 (최악 argv: cys channel --help)」 |
| `BUDGET` 을 `100 * 1024` 로 | **붉음** — 「Cli 풀이 필요 스택 229351 바이트 > 예산 102400」 |
(둘 다 되돌린 뒤 정상 판 단독 통과 · 측정값 2,101,151 · 229,351 은 조사 가지 탐침 값과 바이트까지 같다)

### 4-4. 부하 재현(진짜 a3 시험 + 할당 부하 짝 · 기본 2 MiB 시험 스레드 · 150회)
- 방법: 이 가지에 커밋하지 않는 임시 사본으로 `docs/1115/CLI-STACK-PROBE/stack_probe.rs` 를 `mod tests` 에 붙여 opt1 빌드 → `STACK_PROBE_STORM_SECS=1 <bin> --exact tests::a3_strip_hook_… tests::stack_probe::stack_probe_storm_only --include-ignored --test-threads=2` 150회 → `git checkout -- src/bin/cys.rs`(되돌림 확인 · 커밋 무관).
- 결과: **넘침 0/150 · 실패 0/150**(09:21~09:23 · 부하 평균 15.62 9.78 7.12) · 마지막 회 출력 「running 2 tests … 2 passed」 = 짝이 실제로 함께 돎.
- 대조: 조사 때 같은 방법으로 opt0 d5824332 = 넘침 11/150.

### 4-5. 디버그 깨끗한 빌드 시간(`cargo test --no-run --bin cys --bin cysd --lib` · 빈 target · CARGO_BUILD_JOBS=4 · sccache 없음)
| | real | user | sys | 부하 평균(앞→뒤) |
|---|---|---|---|---|
| 기준선 270e3e21(opt0) · 08:33 | 105.02 초 | 237.47 초 | 9.41 | 12.99 → 11.26 |
| 고침 7e9c2405(opt1) · 08:35 | 299.96 초 | 798.92 초 | 17.75 | 10.21 → **40.59**(다른 좌석 부하가 빌드 중 상승) |
- real 은 빌드 중 기계 부하가 4배로 올라 부풀었다 · 부하에 덜 민감한 user 시간으로도 **≈3.4배**(+561 초) — 비용이 크다. 이 패키지만 다시 짓는 경우(뮤턴트 때 관측 · 참고값): opt0 lib+cys 시험 67.9 초 user · opt1 lib+cys 시험 99.0 초 user(+46%).
- 단점 정리: 이 패키지 깨끗한 디버그 빌드 비용 ≈3.4배(user) · 디버거에서 지역 변수 일부 optimized out.

### 4-6. 윈도 디버그 주 스레드(1 MB)
- 맥 arm64 opt1 실측: 풀이 229,351 + run 틀(opt1 미측정 · opt0 27,488 이하로 본다) ≈ 0.26 MB → 1 MB 의 약 1/4. **맥 환산 · 윈 실기 미확인**(x86_64 MSVC 기계어로 잰 값이 아니다).

## 5. master 재현 명령
```bash
cd ~/axdev/.wt/cys-dev-opt1-budget   # 또는 스냅샷 7e9c2405 이후 머리
cargo test --bin cys cli_stack_budget                        # 통과(필요 229,351 ≤ 1,048,576)
# 뮤턴트 1: Cargo.toml 끝 [profile.dev.package.cys-terminal] / opt-level = 1 두 줄 지우고 같은 명령 → 「2101151 바이트 > 예산 1048576」 붉음
# 뮤턴트 2: cys.rs `const BUDGET: usize = 1 << 20;` → `100 * 1024` → 「229351 바이트 > 예산 102400」 붉음
cargo rustc --bin cys -v -- --print cfg 2>&1 | grep -E "^debug_assertions$|opt-level=1"   # 디버그 단언 켜짐
```
부하 재현은 탐침이 필요하다 → 조사 가지 `probe/1115-cli-stack` 6a735ae1 에 `--config 'profile.dev.package.cys-terminal.opt-level=1'` 로.

## 6. 남은 것
- 윈도 러너 실측(opt1 디버그 `cys.exe --help` 3종 기본 스택 · `aid_s5_cli_tests::` RUST_MIN_STACK 없이) — §2 우회 걷어 내기의 전제.
- cys-app(src-tauri) 디버그 빌드·시험은 이 설정에서 돌리지 않았다(lib `cys` 가 opt1 로 바뀜).
- 기준선 cysd `dbg_r12_*` 2건의 폴더 위치 탓 판정은 단독 재실행 없이 추정.
