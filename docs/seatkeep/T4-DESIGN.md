# T4 좌석 입양 — 설계 메모 (TICKET=cysr-1116-seatkeep-1119 · master#7065425a)

- 근거 설계: `~/axdev/master/reports/2026-11-11-cysr-holder-design/DESIGN.md` §3-2 ③⑤ · §5(A1~A16) · §6 T4 행 · `T0-surface-state.md` §2·§3(입양 순서 11단계).
- 앞 단계: T2(seatkeep 단독) · T3(cysd 좌석 손잡이 · 노브 `CYS_SEATKEEP=1` · `--controller-bound`) — 둘 다 1.1.16 기준점(dea2e1853)에 들어 있음.
- 노브 = **`CYS_SEATKEEP_ADOPT=1`**(그리고 `CYS_SEATKEEP=1`) · **기본 끔**. 끔이면 이번 변경은 어떤 파일·소켓에도 닿지 않는다(아래 「끔 = 종전」 표).

## 1. 무엇이 바뀌나 (켬일 때만)

| 자리 | 바뀜 |
|---|---|
| seatkeep 기동 인자 | `--controller-bound` 대신 **`--adoptable`** (seat_proc.rs `SeatkeepPlan::spawn`) |
| seatkeep `--adoptable` | 종속 모드의 ⑵ 역압(조종자가 밀리면 PTY 를 안 읽음) · ⑶ 쓰기 기한 없음은 그대로. ⑴ 끊김 종료만 뺌 → cysd 가 죽어도 좌석이 산다. 조종자 없는 동안은 **끊긴 뒤 출력이 꼬리(1MiB 기본)를 넘기 전까지만** 읽고 그 뒤 역압(자식이 멈춤) → 새 조종자에 꼬리 재생 = 끊긴 뒤 출력 유실 0. 첫 조종자가 `FIRST_CONTROLLER_MAX` 안에 안 붙으면 종속 모드처럼 끝냄(아무도 모르는 좌석 방지). WELCOME 좌석 칸에 `disc_total`(끊긴 때 누적) 추가 |
| 좌석 기록 | seatkeep 상태 폴더 `<seatkeep id>.cysd.json` — 번호·보이는 번호·제목·역할·명령·폴더·만든 때·env 여부·크기·에이전트 메타·세션·계정 폴더(+신뢰)·전사 핀·재핀 앵커·세대 둘·각성 시각·지침 확인·팩 재주입·관문 보류. **좌석 토큰은 쓰지 않음**(비편입 계약 · T5). 쓰는 때 = 생성 직후 + `persist_topology` 마다(역할 claim·메타·세션 등록이 모두 지남) |
| 기동 순서(main.rs) | `Daemon::new`(시작 잠금은 그 앞에서 이미 쥠) → **`seat_adopt::adopt_on_boot`** → watchdog·부트 감독 → accept → `post_listen_boot`(자동 복원). T0 §3 의 0→1→2→3→9→10 순서 |
| 입양 판정 | 등록부 `<id>.json` 단계 `committed` ∧ pid 같음 ∧ 살아 있음 ∧ 출생 시각(µs) 같음 = 붙어 봄 · 그 밖 = **죽음 확인**(기록·등록부·잠금·소켓·종료 기록 삭제 · 교체 기록 `.log` 는 사후 적발 장치라 남김) · 읽기·해석·출생 시각 판독 불가 / 접속 거절 / 등록 실패 = **미결** |
| 붙기 | `seat_proc::adopt_connect` = 새 좌석과 같은 `greet`(소켓 상대 pid = WELCOME pid = 등록부 pid) · seatkeep 쪽은 T2 의 상호 확인(실행 파일 = 같은 cysd · 데몬 잠금 보유자 · 살아 있는 조종자 없음 · HELLO 뒤 재확인) 그대로 |
| 좌석 재등록 | `create_surface_with_env` = 감싸개 → **`create_surface_core(…, adopt)`** 의 입양 갈래: 같은 내부 번호(`next_id` 를 그 위로) · 같은 보이는 번호(`adopt_display` — 그 칸이 이 좌석이었거나 비었을 때만 · 남이 가졌으면 「—」+경보) · 대응표 행 다시 열기(`surface_numbers_reopen` — boot_orphan 만) · 자식 안 띄움 · `wire_seat_profile_before_exec` 안 함 · 토큰 없음(체인 폴백) · root_registration = 관측 없음(T0 §2-9 권고 ⓑ) · 약속 칸 되살림(`apply_record` — 세대 카운터는 올리지 않음 T0 §2-6) · 그 밖(쓰기 스레드·맵·역할·묘비·topology·`surface.created`·읽기 스레드)은 새 좌석과 같은 길 |
| 화면·전사 | 꼬리 재생을 둘로 나눔(`SeatLink::replay_split`): 앞 = 꼬리 시작 ~ 끊긴 때 → **화면만**(`replay_screen_only` · DSR 응답·화면 송출·OSC 알림·전사 안 함 = 옛 cysd 가 이미 함) · 뒤 = 끊긴 때 ~ WELCOME → 새 출력과 같이 전부 처리. 재생 뒤 300ms 에 크기 흔들기(`repaint::nudge_resize`) |
| 큐 | 입양 직후 3초 큐 멈춤(`queue_paused_until`) — 화면이 다시 그려진 뒤 기존 초안 관문(화면 판정)이 판단(T0 §2-4 의 최소 대역) |
| 자동 복원 | 입양된 역할 = accept 전에 `roles` 에 있음 → phoenix·`cys restore` 의 「가동 중」 판정이 건너뜀. **미결이 하나라도 있으면 그 기동의 자동 복원 보류**(`seat_adopt::restore_should_hold` · main.rs `spawn_auto_restore` 1곳) |
| 이벤트 | `seat.adopted` / `seat.adopt_skipped`(결과·사유) · `restore.held` |

## 2. 끔 = 종전 (노브 끔일 때 닿는 줄)

- `seat_adopt::record_surface`·`record_all`·`adopt_on_boot` = 첫 줄 `enabled()` 거짓 → 곧바로 반환(파일 0).
- `restore_should_hold` = 요약 없음 → None.
- `create_surface_core(adopt=None)` = 옛 본문과 같은 순서·같은 값(갈래마다 `None` 쪽이 옛 줄).
- 읽기 스레드 `screen_only_left` = 직접 PTY·새 seatkeep 좌석 모두 0 → 옛 길.
- seatkeep: 두 인자 다 없음 = T2 · `--controller-bound` = T3 그대로(`backpressure()` = bound ∨ adoptable 로 같은 갈래).

## 3. T1 이 들어오면 갈아끼울 자리 (한 곳)

`src/bin/cysd/seat_adopt.rs` `restore_should_hold()` — 지금은 「미결 있으면 그 기동 자동 복원 통째 보류」. T1(대화 소유 임대)이 오면 이 함수가 「미결 좌석의 대화 임대를 쥐고 그 역할만 복원 제외」로 바뀐다. 부르는 자리는 main.rs `spawn_auto_restore` 첫머리 1곳.

## 4. 하지 않은 것 (이 단계 밖 · 순서 = HANDOFF)

- **T5 좌석 토큰 이음**(다음 단계 · 같은 좌석): 지금 입양 좌석은 무토큰 = claim 은 체인 폴백.
- T6 rotate·업데이터(계획 교체 = 화면 저장 + 이어받기 · 사전 실행 · RELEASE · 판 처리) · T7 윈도우 · D1 꼬리 ≤1KiB 유실 · 슬레이브 보유 탐침.
- A7 관문 유지의 전부(`screen_exact` 승격 규칙) — 지금은 3초 큐 멈춤 + 크기 흔들기 대역뿐.
- A14 경계 순간 강제 종료(고장 주입 지점) · A15 동시 복원 경합(T1 몫).
- 기록 없는 살아 있는 seatkeep(생성 직후 기록 쓰기 전에 cysd 가 죽은 극히 짧은 창 · 기록 쓰기 실패) — 입양 못 함(좌석 번호를 모름). 기동 때 찾아 **미결**로 올려 자동 복원을 보류하고 `seat.adopt_skipped`(no_record_live_keeper)로 알린다. 좌석은 죽이지 않는다(산 좌석일 수 있음) — 정리 규칙은 T6(판 처리)에서.
