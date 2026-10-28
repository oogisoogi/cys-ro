# HANDOFF — TICKET=cysd-worker-cap-unlimited (1.1.11 · 2026-10-29)

브랜치 `fix/1111-worker-cap` ← int/1111 `eb4ef98c`. 좌석 surface:1710(711 · cys-1111-workercap).
범위 = Rust 데몬·CLI 쪽만(ui 무접촉 — fix/1111-render-parity 와 겹치지 않음).

## 1. 무엇이 바뀌었나

| 항목 | 종전 | 지금 | 자리 |
|---|---|---|---|
| 워커 동시 상한 기본값 | 8(원작자 코드) | **0 = 무제한** (`DEFAULT_MAX_ACTIVE_WORKERS`) | `src/bin/cysd/state.rs` `Config::from_env` · `max_active_workers_from` |
| `CYS_MAX_ACTIVE_WORKERS=<N>` | N 존중 | N 존중(그대로) · `0`·숫자 아님·부재 = 무제한 (종전엔 숫자 아님 → 8) | 같은 곳 |
| 상한 초과 거절 문구 | `… (max_active_workers)` | `… (max_active_workers · CYS_MAX_ACTIVE_WORKERS 로 명시한 상한 · 기본은 무제한)` — 오류 코드 `worker_limit_exceeded` 불변 | `src/bin/cysd/handlers.rs` surface.create ② |
| launchd plist 재기록(stale 판정·`cys daemon install`) | 본문을 PATH 하나로 새로 써서 **사용자 env 소실** | 기존 plist `EnvironmentVariables` 의 **PATH 밖 키를 읽어 다시 싣는다** · PATH 는 cys 관리 값으로 갱신 · 첫 등록은 종전과 같은 바이트 | `src/launchd.rs` `write_plist_at`·`render_plist_preserving`·`extract_user_env` · `src/bin/cys.rs` daemon install 이 같은 함수 사용 |
| 문서 | 표 기본값 8 | 0(무제한) + plist 보존 1줄 | `USER-MANUAL.md` · `ARCHITECTURE-AND-PHILOSOPHY.md` §4 한 줄 |

「꽉 찼다」류 문구 전수 grep(src·src-tauri·ui/src·cysjavis-pack · `꽉|worker_limit|limit_exceeded|좌석이 없|빈 좌석…`):
워커 상한 거절은 위 한 곳뿐. 나머지 「꽉」 출현은 디스크·화면 너비·예산 문맥(무관). 「빈 좌석」은 역할 승계 개념(상한 무관).

## 2. 실측 사실(이 맥 · 읽기만 · 무변경)

- 실제 plist `~/Library/LaunchAgents/com.cysjavis.cysd.plist` mtime **10-28 10:21** — 10-28 06:47 에 넣은 64 가 **이미 다시 지워져 있다**(`grep -c MAX_ACTIVE` = 0). 백업 `.bak-20261028`·`.bak-20261022-maxworkers` 도 0(편집 전 백업).
- 지금 64 가 살아 있는 이유 = **`launchctl getenv CYS_MAX_ACTIVE_WORKERS` = 64**(gui 도메인 setenv · `launchctl print` 의 inherited environment). 가동 데몬 pid 9824(`/usr/local/bin/cysd` · 10-28 09:58 기동) 환경에 `CYS_MAX_ACTIVE_WORKERS=64` 실측. setenv 는 재부팅 휘발 — 이 패치가 설치되면 env 없이도 무제한.
- 10:21 재기록 주체는 확정 못 함(cysd.log 에 launchd 줄 없음). 후보 = 앱 `register_if_absent`(stale 판정) 또는 `cys daemon install` — 두 경로 모두 이번에 보존 경로로 바뀌었다.

## 3. 윈 대조

- 상한 코드(`Config`·surface.create 게이트)는 OS 공용 — 기본 무제한이 윈에도 그대로 적용.
- 윈 등록 경로 = `cys daemon install` → 작업 스케줄러 XML(`cysd_task_xml` · `src/bin/cys.rs`). XML 에 env 블록이 **없다** — 데몬은 사용자 환경(레지스트리 사용자 변수)을 상속한다. 재등록(`/Create /F`)이 env 를 지우는 경로가 없으므로 맥의 소실 결함은 윈에 해당 없음. `setx CYS_MAX_ACTIVE_WORKERS N` 이 윈의 상한 손잡이(재등록 무관하게 유지).
- ⇒ 맥·윈 동일 정책: 기본 무제한 · env 숫자 존중 · 재등록에도 env 유지.
- 윈 실기 미검증(이 맥에서 컴파일 대상 아님 — 바뀐 윈 코드 0줄).

## 4. 시험

- 새 시험 5
  - `state::dedup_tests::max_active_workers_default_unlimited_and_env_number_respected`
  - `handlers::tests::worker_default_limit_allows_ninth_and_beyond`(8 채운 뒤 9·10번째 RPC 기동 통과)
  - `launchd::tests::rewrite_preserves_user_env_and_refreshes_managed_keys`(임시 경로 · 옛 경로·옛 PATH·사용자 env 2개 → 재기록 → env 보존 · 경로·PATH 갱신 · 2회째 멱등 · `plutil -lint` + `plutil -extract` = 64)
  - `launchd::tests::first_write_equals_plain_render`
  - `launchd::tests::extract_user_env_reads_reformatted_plist_and_skips_non_strings`
- 뮤턴트 2/2 사망: M1 기본값 0→8 → 2건 실패 · M2 보존 제거(render_plist 직기록) → 보존 시험 실패.
- ⚠ 이 맥 셸은 `CYS_MAX_ACTIVE_WORKERS=64` 를 상속한다 — 시험은 `unset CYS_MAX_ACTIVE_WORKERS` 로 돌렸고, 새 시험은 프로세스 env 를 읽지 않게 순수 함수로 고정.
- 전체 크레이트 `cargo test --no-fail-fast`(루트 크레이트 · env unset): lib 1104 통과(무시 2) · cys 628 통과 · cysd 2711 통과(무시 9) · **실패 0** · rc=0. src-tauri 크레이트는 무변경(그쪽 `render_plist` 사용 시험은 함수 서명 불변이라 영향 없음 — 별도 실행은 안 함).

## 5. 함정·남은 것

- plist 판독은 XML 텍스트 한정(바이너리 plist 면 보존 목록 빈 값 = 종전 동작). 사용자가 `plutil -convert binary1` 로 바꾸면 보존 안 됨 — 지금까지 실물은 전부 XML.
- `plist_path_matches`(fresh 판정)는 사용자 키를 보지 않는다(종전 그대로) → 사용자 키 추가만으로 재기록이 일어나지는 않는다.
- 비가역(워커 미실행 · master 게이트): push · int/1111 병합 · 빌드 설치 · launchctl bootout/bootstrap · cysd 재기동. 설치 뒤 확인법 = 새 cysd 를 env 없이 띄운 상태에서 `worker` 9기 이상 기동 성공 · `cys daemon install` 뒤 plist 에 사용자 키 잔존.
