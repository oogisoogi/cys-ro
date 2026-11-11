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

## 4. 시험·측정 결과
(아래 §4 는 실행 뒤 채운다.)
