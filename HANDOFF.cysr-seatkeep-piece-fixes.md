# HANDOFF — TICKET=cysr-seatkeep-piece-fixes · ⓐ seatkeep-t3 (원시 `Command::new` 계수 동결표)

- 좌석 = worker-4(surface:2015) · 2026-11-12 · 브리프 원장 = `.master-send-ledger.jsonl` 07:50:25 surface:2015 kind=brief(spawn-worker)
- 근거 = 통합 리허설 문서 `~/axdev/.wt/cys-1115-integ/docs/INTEG-1115-REHEARSAL.md` §6-3(t3 단독 판에서도 `spawn_policy_tests::raw_command_new_census_is_frozen` 붉음)
- 갈래 머리 = 고치기 전 a2aadf7f → 새 머리 = 이 문서와 함께 커밋한 것(`git log -1`)
- 짝 = ⓑ seatkeep-t1 새 머리 7e70cdf2(그 갈래의 `HANDOFF.cysr-seatkeep-piece-fixes.md`)

## 1. 이 시험이 왜 있는가(판독)
`src/lib.rs` 의 `RAW_COMMAND_NEW_FROZEN` 주석과 `hidden_command` 문서(TICKET=cysr-console-flicker-r2 · 2026-09-15):
콘솔 없는 프로세스(cysd·앱)가 콘솔 바이너리를 플래그 없이 낳으면 **윈도우에서 자식마다 콘솔 창이 번쩍인다**(1.0.0 참가자 기기 실측). 맥·리눅스·CI 에서는 무증상이라, 지점마다 기억해 붙이는 방식은 두 번 빠졌다. 그래서 「헬퍼 밖 원시 `Command::new`」를 **파일별 개수로 동결**해 새 원시 스폰이 생기는 순간 붉게 만들고, 쓰는 사람이 `hidden_command` 또는 `spawn_policy(<등급>)` 를 고르게 한다. 숫자를 늘릴 때의 규칙 = 「ⓐ윈에서 안 도는가 ⓑ등급을 체인에 달았는가를 먼저 적어라」. 기존 지점 가운데 맥 전용·시험 검체는 계수로만 묶는 것이 이 표의 선례다(예: `activity_bench_tests.rs` 등 원작자 시험 파일 · `launchd.rs`).

계수 방식: `production_slice` 가 **열 0 의 `#[cfg(test)]`** 항목만 걷어낸 뒤 `Command::new` 를 센다. 들여쓴 `#[cfg(test)] mod tests`(다른 모듈 안)와 `#[cfg(test)] mod x;` 로 붙는 별도 시험 파일은 걷히지 않고 세어진다(선례 파일들과 같은 처지).

## 2. 직접 센 개수 ↔ 시험 실측(리허설 숫자를 믿지 않고 대조)
`grep -rn 'Command::new' src/bin/cys-seatkeep/ src/bin/cysd/seat_*.rs` = 8줄 · 6파일. 고치기 전 시험이 낸 실측 표와 동결표의 차이 = 정확히 이 6파일(그 밖 파일 차이 0 · 스크립트로 두 표를 뺄셈해 확인).

## 3. 줄별 판단 표

| 파일:줄 | 무엇 | 어디서 도나 | 헬퍼로 바꾸면 | 판단 |
|---|---|---|---|---|
| `src/bin/cys-seatkeep/main.rs:1680` | `ps -o stat=` 생존 확인 | `#[cfg(unix)] mod imp` 안의 **들여쓴** `#[cfg(test)] mod tests`(1296행) — 시험 전용 · 윈은 이 바이너리가 `main` = 종료 2(40행) | 시험 코드라 의미 없음 | **동결표**(+2 중 1) |
| `src/bin/cys-seatkeep/main.rs:1689` | 그룹 리더 `/bin/sh` 검체(`process_group(0)`) | 같은 시험 모듈 | 같음 | **동결표**(+2 중 1) |
| `src/bin/cysd/seat_proc.rs:387` | 노브 켬 좌석의 보유 장치 기동 `Command::new(&self.exe)` — **실제 프로그램 경로** | `#[cfg(target_os = "macos")] mod seatkeep_mac`(304행) — **맥 전용 · 윈에서 컴파일 안 됨**(윈 = T7) | 맥에서 `hidden_command` = `Attached` 등급 = unix 에서 setsid 0 · stdio 분리 0(lib.rs `unix_setsid`·`detach_stdio`) → 동작은 같다. 그러나 「Attached」라는 **생사 등급을 소스에 적는 것**은 T4(입양 = 데몬보다 오래 사는 좌석)·T7(윈) 이 정할 결정을 앞당겨 적는 것이다. 좌석 프로세스 생성 = 고위험 경로 | **동결표 · 바꾸지 않음**(동작 변경 0 · 그래서 【결정필요】 불요). 이유를 표 주석에 적음 |
| `src/bin/cysd/seat_d7_tests.rs:79` | `ps -o stat=` | cysd main.rs 4218 `#[cfg(test)] mod seat_d7_tests;` — 시험 파일 | — | **동결표** |
| `src/bin/cysd/seat_flood_tests.rs:14` | `ps -o rss=` | 4220 `#[cfg(test)] mod` — 시험 파일 | — | **동결표** |
| `src/bin/cysd/seat_proc_tests.rs:124` | 복사본 seatkeep 기동 | seat_proc.rs 904~906 `#[cfg(test)] #[path] mod tests;` — 시험 파일 | — | **동결표** |
| `src/bin/cysd/seat_tail_tests.rs:53` | `ps -o stat=` | 4224 `#[cfg(test)] mod` — 시험 파일 | — | **동결표**(+2 중 1) |
| `src/bin/cysd/seat_tail_tests.rs:84` | 꼬리 시험 `/bin/cat` 검체 | 같은 시험 파일 | — | **동결표**(+2 중 1) |

(`seat_latency_tests.rs` 는 `Command::new` 0 — 표에 안 올림.)

## 4. 바뀐 것
`src/lib.rs` `RAW_COMMAND_NEW_FROZEN` 에 6줄 + 근거 주석(시험 상수만 · 제품 코드 무변경 · +15줄). 코드 경로가 바뀌지 않았으므로 노브 끔 무변화 장면(리허설 §8-2 ⓓ)은 「코드 무변경」으로 갈음.

## 5. 시험 출력(격리 HOME = 스크래치 폴더 · CYS_*/XDG_*/CMUX_*/NODE_OPTIONS 제거 확인 「left: 0」 · `CARGO_BUILD_JOBS=4`)
| 대상 | 결과 |
|---|---|
| `cargo test --lib raw_command_new_census_is_frozen`(고치기 전) | **FAILED** 0/1 — 실측 표에 위 6파일이 동결표보다 많음 |
| 같은 시험(고친 뒤) | **ok** 1/1 |
| `cargo test --lib -- --test-threads=4` | **1204 통과 · 0 실패 · 2 무시** — 실패 이름 0(리허설 §6-3 기준선 lib 실패 이름도 0) |
| `cargo test --bin cys-seatkeep` | **34 통과 · 0 실패** |
| `cargo test --bin cysd seat_ -- --test-threads=4` | **149 통과 · 0 실패 · 2 무시** |

## 6. 뮤턴트
동결표에서 방금 올린 `("src/bin/cysd/seat_proc.rs", 1)` 한 줄만 뺀 판 → `raw_command_new_census_is_frozen` **FAILED**(rc 101 · lib.rs:7366 단언) → 원본 복원(복사본으로 되돌림 · `git diff --stat` = lib.rs +15 만 남음 확인).

## 7. 하지 않은 것 · 정직 기록
- 좌석 생성·임대·잠금 동작 변경 0 · `seat_proc.rs` 무수정 · push·태그 0 · 리허설 가지 무접촉.
- 첫 전체 시험 실행은 내 명령 오류(zsh 가 따옴표 없는 변수를 낱말로 안 쪼갬 → cargo 가 안 돎)로 결과가 없었고, bash 스크립트로 다시 돌린 것이 위 표다.
- 다음 손이 알 것: T4(입양)·T7(윈) 에서 `seat_proc.rs` 의 보유 장치 기동에 등급을 정할 때 이 동결표 줄(`seat_proc.rs` 1)과 주석을 함께 고친다.
