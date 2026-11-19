# T5 좌석 토큰 이음 — 설계 메모 (TICKET=cysr-1116-seatkeep-1119 · 1단계 = 문서만 · 코드 0)

- 근거 설계: `~/axdev/master/reports/2026-11-11-cysr-holder-design/DESIGN.md` §3-2 ④(토큰 잇기) · §5 A8ⓓ·ⓓ′ · §6 T5 행 · codex 설계 1R #4.
- 앞 단계: T4(`docs/seatkeep/T4-DESIGN.md`) — 입양 좌석은 지금 **무토큰**(state.rs `create_surface_core` 입양 갈래 `seat_token = None` · claim = 체인 폴백).
- 노브: T4 와 같은 `CYS_SEATKEEP_ADOPT=1`(+ `CYS_SEATKEEP=1`). 끔이면 이 단계의 변경도 어떤 프레임·파일에도 닿지 않는다.
- 비가역·비용: 없음(코드·시험만 · 격리 HOME). 보안 고위험(인증·비밀값) → codex 1R 필수(06:29 뒤 · master 대기열).

## 0. 지금 실측한 사실(dea2e1853 + T4 · 파일:줄 = b953e900a)

| 사실 | 근거 |
|---|---|
| 토큰 = `"{started_at 초 hex}-{cysd pid hex}.{128bit hex}"` · 세대 접두 = 앞 두 성분 | state.rs `seat_token_generation`·`mint_seat_token`(4005-4019) |
| `Surface.seat_token` = 생성 때 1회 발급 · 그 뒤 바꾸는 곳 없음(재발급·`/clear` 갱신 경로 0) | state.rs 생성 주입(8234~) · `seat_token` 쓰기 grep = 생성 1곳 |
| 토큰은 좌석 PTY env 로만 배달(`CYS_SEAT_TOKEN` · 호출자 env 의 같은 키는 버림) · topology·목록·이벤트에 안 실음(비편입 계약 + 회귀 핀 `seat_token_never_persisted_or_listed`) | handlers.rs 7480 · governance.rs 3218 · handlers.rs 25082 |
| seatkeep 은 cysd 가 준 env 를 **그대로** 받아 자식에 넘긴다 → seatkeep 자기 env 에 같은 토큰이 이미 있다 | seat_proc.rs `SeatkeepPlan::spawn`(`env_clear` + `envs(builder.iter_full_env_as_str())`) |
| 토큰을 읽는 곳 4: ① claim(handlers.rs 10030~ · 일치 = 인가 · 불일치+동세대 = 시끄러운 거절 · 불일치+다른 세대/형식 불명 = 체인 폴백) ② 발신자 해석 `find_surface_by_seat_token`(handlers.rs 2260 · 등식만) ③ 부트 감독 claim 릴레이(boot_supervisor.rs 1789 · 살아 있는 좌석의 토큰을 데몬 자식 env 로) ④ 세대 판정 `seat_token_same_generation`(state.rs 4037 · 부르는 곳 = ① 하나) | grep `seat_token` |
| seatkeep id = `"{cysd pid hex}-{started_at 초 hex}-{순번}"` — 토큰 세대 접두와 같은 두 성분(순서 반대) | seat_proc.rs 406 |

## 1. 목표(A8ⓓ′ 원문 그대로 4줄 + ⓓ)

1. 입양 뒤 옛 좌석 토큰(접두 `{옛 시작 시각}-{옛 cysd pid}`)으로 claim → **입양 세대로 이어진 그 좌석에서만 성공**.
2. 다른 좌석이 그 토큰을 쓰면 **거절**.
3. 입양되지 않은 옛 토큰(복원으로 새로 뜬 좌석 등)은 **토큰으로 인가되지 않음**(체인 경로는 종전대로).
4. 시작 시각만 같고 pid 다른 위조 접두 → **거절**.
5. (ⓓ) 입양이 끝나기 전 `claim-role master` → 실패(T4 예약 관문이 이미 막음 · 회귀 확인만).

## 2. 설계

### 2-1 토큰 보관·인계 — 권고 = ⓑ WELCOME 칸 (대안 ⓒ 와 비교)

| 안 | 내용 | 좋은 점 | 나쁜 점 |
|---|---|---|---|
| ⓐ 디스크(좌석 기록 `.cysd.json` 에 씀) | — | 가장 단순 | **비편입 계약 위반**(DESIGN §3-2 ④ 「디스크에 쓰지 않는다」) — 기각 |
| **ⓑ seatkeep 메모리 → WELCOME** | seatkeep 이 시작 때 자기 env 의 `CYS_SEAT_TOKEN` 을 메모리로 읽어 둠(입양 모드만) · 조종자 상호 확인(실행 파일 = 같은 cysd · 데몬 잠금 보유자 · 살아 있는 조종자 없음 · HELLO 뒤 재확인)을 통과한 연결의 WELCOME 좌석 칸에만 `seat_token` 을 싣는다 | 원 설계(「holder 보관 · 상호 확인 뒤 인계」)와 같음 · 프로토콜이라 T7 윈도우에도 같은 길 · 인계 시점 = 화면·입력 통제를 넘기는 바로 그 인증 | seatkeep 코드 변경(머리·WELCOME 1칸) · seatkeep 기록(등록부·`.log`)에 새지 않게 막아야 함(아래 2-4) |
| ⓒ cysd 가 seatkeep env 를 `KERN_PROCARGS2` 로 읽기 | T4 의 `process_env_var`(역할 판독) 재사용 | seatkeep 무변경 · 코드 최소 | 맥 전용(윈 = 길 없음) · 「상호 확인 뒤 인계」가 아니라 「같은 사용자면 누구나 읽는 값을 cysd 도 읽음」(노출은 자식 env 와 같은 수준이라 새 구멍은 아님) · 인계가 인증 연결과 분리돼 판정 순서가 둘로 갈림 |

→ **권고 ⓑ**(확신도 중상). 단점 1줄: seatkeep 과 cysd 두 실행 파일을 함께 바꿔야 하므로 「옛 seatkeep(T4 판) + 새 cysd」 조합에서는 칸이 없다 → 그 경우 = 종전(무토큰 · 체인 폴백)으로 접는다(칸 없음 = None · 실패 아님).

### 2-2 새 cysd 의 입양 순서에 끼우는 자리

`seat_adopt::adopt_on_boot` → `adopt_connect` → WELCOME → `create_surface_core(adopt=Some)` 입양 갈래의 `seat_token = None` 줄을 바꾼다:

1. WELCOME `seats[0].seat_token` 문자열을 꺼낸다(없거나 문자열 아님 = None).
2. **세대 정합**: 토큰 접두가 seatkeep id 의 두 성분(`{pid}-{start}`)을 뒤집은 `{start}-{pid}` 와 **정확히 같을 때만** 받는다 — 다르면 None + `seat.adopt_token_skipped{reason: generation_mismatch}`(목표 4의 위조 접두 · 다른 cysd 가 띄운 seatkeep 에 남의 토큰이 실린 경우 차단). 형식 = `<접두>.<32 hex>` 아니면 None(`malformed`).
3. 받으면 `Surface.seat_token = Some(옛 토큰)` — 같은 값이 그 좌석 자식 env 에 이미 있으므로 자식 쪽 변경 0.
4. **입양 세대 집합**(Daemon 새 필드 `adopted_token_gens: Mutex<HashSet<String>>` · 무영속)에 그 접두를 넣는다. 좌석이 끝나도 빼지 않는다(그 세대의 다른 좌석이 아직 살 수 있고, 빼면 같은 세대 위조가 조용한 폴백으로 바뀜 · 크기 = 옛 cysd 수).
5. 다단(cysd1 → cysd2 → cysd3): seatkeep env·메모리 값은 cysd1 세대 그대로 → 매 입양에서 같은 정합 규칙(seatkeep id 도 cysd1 것) — 추가 규칙 없음.

### 2-3 판정 넓히기 — claim 의 「불일치」 갈래만

- handlers.rs 10071 의 `seat_token_same_generation(&supplied, daemon.started_at)` 를 `daemon.seat_token_known_generation(&supplied)` = **현 세대 ∨ 입양 세대 집합에 접두가 있음** 으로 바꾼다. 일치 갈래(인가)·체인 충돌 거부권(ⓐ)·다른 세대 폴백(ⓑ)의 모양은 그대로.
- 효과: 목표 1 = 일치 갈래(토큰이 그 좌석 `seat_token` 과 같음) · 목표 2 = 그 토큰을 다른 좌석에 실으면 「불일치 + 알려진 세대」 → 시끄러운 거절(token_mismatch) · 목표 3 = 입양 안 된 옛 토큰은 어느 좌석 값과도 안 맞음 → 인가 안 됨(세대가 입양 집합에 있으면 시끄러운 거절 · 없으면 종전 체인 폴백) · 목표 4 = 2-2 ② 가 입양을 거부 + 집합에 없는 접두 → 종전 폴백(인가 안 됨).
- `seat_token_same_generation` 함수 자체(프로세스 내 pid 직접 읽기 · 주석 「mint 와 판독이 같은 프로세스」)는 **바꾸지 않는다** — 현 세대 판정은 여전히 이 프로세스 것이고, 입양 세대는 따로 든 집합이 출처다(DESIGN §3-2 ④ 「세대 출처를 명시」의 답).
- ② 발신자 해석·③ 부트 감독 릴레이 = 등식만 쓰므로 `Surface.seat_token` 이 차면 자동으로 이어진다(변경 0 · 시험으로 확인).

### 2-4 새지 않게(비편입 계약 확장)

- seatkeep: 토큰은 WELCOME 칸 하나로만 나간다 — 등록부 `<id>.json`·`.exit`·`.log`(교체 기록)·stderr 어디에도 안 씀. WELCOME 은 조종자 연결에만 가고 seatkeep `.log` 의 `accept` 줄은 피어만 적는다(지금 그대로 · 회귀 핀 추가).
- cysd: `seat.adopted` 이벤트·`seat_adopt` 기록 파일·eprintln 에 토큰·접두 외 값 안 씀(접두는 비밀 아님 — 지금도 토큰 문자열의 공개 부분). `.cysd.json` 에 안 씀(T4 그대로 · 핀 유지).
- 노브 끔(seatkeep `--controller-bound`·인자 없음): seatkeep 이 env 를 읽지도 않음 → WELCOME 칸 없음.

### 2-5 codex 설계 1R #4(원자 절차·폐기 기록)에 대한 답

- 「자식 기동~토큰 전달 사이 cysd 크래시」: 토큰은 cysd 가 **자식 기동 전** env 로 정해 seatkeep 에 넘기므로(같은 env 가 seatkeep·자식 둘에 동시에 들어감) 전달 단계가 따로 없다 — seatkeep 이 살아 있으면 토큰도 있다. 기록(`.cysd.json`)은 T4 가 이미 자식 기동 전에 임시본을 씀(못 쓰면 좌석 안 만듦).
- 「`/clear`·재발급으로 토큰이 바뀌었는데 holder 가 옛 값」: 지금 코드에 재발급 경로가 없다(§0 표 2행) → seatkeep 값 = `Surface.seat_token` 이 늘 같다. **재발급 경로를 나중에 만드는 변경은 seatkeep 갱신 프레임 없이는 들어오면 안 된다** — 소스 핀으로 막는다(재발급 = `seat_token` 대입이 생성 1곳 밖에 생기면 붉음).
- 폐기 기록: 좌석이 끝나면 seatkeep 이 끝나며 메모리 값도 사라진다 · cysd 쪽은 `Surface` 와 함께 사라진다(입양 세대 집합은 접두만 남김 — 비밀 아님).

## 3. 시험(수용 · 숫자는 구현 단계에서)

| 축 | 시험 | 종류 |
|---|---|---|
| 목표 1 | 입양 좌석 안에서 `cys claim-role` (env 토큰) → 성공 · 경로 = 토큰(체인 아님 — 이벤트/응답 표지) | e2e(`seatkeep-adopt-e2e.py` 새 모드 `token`) |
| 목표 2 | 입양 좌석 A 토큰을 다른 좌석 B 에서 claim → token_mismatch 거절 | e2e + handlers 단위(입양 세대 집합 주입) |
| 목표 3 | 입양 안 된 옛 토큰(같은 옛 세대·다른 난수) → 인가 안 됨 · 시끄러운 거절 / 집합 밖 세대 → 종전 폴백 | 단위 |
| 목표 4 | WELCOME 칸 접두 위조(시작 같고 pid 다름) → 입양은 되나 토큰 None + `adopt_token_skipped` · 그 토큰 claim 인가 안 됨 | 단위(`create_surface_core` 입양 갈래 판정 함수 분리) + e2e(`SKA_FORGE_TOKEN`) |
| ⓓ | 입양 전 claim master 실패 | T4 reserve 회귀 |
| 새지 않음 | seatkeep 기록 3종·cysd `seat.adopted`·`.cysd.json`·topology·목록에 토큰 문자열 0 | e2e 끝 grep + 기존 핀 |
| 노브 끔 | WELCOME 칸 없음 · 프레임·파일 무변 | seatkeep 단위 |
| 옛 seatkeep 조합 | 칸 없는 WELCOME → 무토큰 입양(종전) | 단위 |
| 뮤턴트 | ⓜ1 정합 검사 끔 → 목표 4 붉음 · ⓜ2 입양 세대 집합 안 넣음 → 목표 2 「조용한 폴백」으로 붉음 · ⓜ3 WELCOME 칸 늘 실음(노브 끔) → 노브 끔 시험 붉음 · ⓜ4 Surface 에 안 넣음 → 목표 1 붉음 | 러너 `mut.py` |

## 4. 바뀔 파일(예상)

- `src/bin/cys-seatkeep/main.rs`(입양 모드 env 1회 읽기 · WELCOME 칸) · `src/bin/cysd/state.rs`(입양 갈래 토큰 줄 · Daemon 필드 · 판정 함수) · `src/bin/cysd/handlers.rs`(10071 한 줄 → 메서드) · `src/bin/cysd/seat_adopt.rs`(WELCOME 칸 전달) · 시험·e2e. 원작자 파일(state.rs·handlers.rs) 변경 = 데몬 변경 허용 범위(브리프).

## 5. 하지 않는 것

- 노브 기본 켬(T1·T5·D1 닫힌 뒤 근거 숫자로 따로 판단) · T6 rotate(계획 교체 때 토큰 인계 = 같은 WELCOME 길로 될 것이나 T6 에서 확인) · 윈도우(T7).

## 6. 구현 결과(2단계 · master#9e1379e9 = A안 승인 · 커밋 7487a7126 · d2ca1de03)

- 설계 ①~⑤ 그대로. 차이·보탬:
  - ⓓ′-1(그 좌석에서만 성공)은 단위가 아니라 e2e `token` 모드로 잰다 — `Surface.seat_token` 은 생성 뒤 불변이고 좌석 Arc 를 읽기 스레드도 쥐어 시험에서 바꿔 끼울 수 없다. 일치 갈래 코드는 무변이라 입양 갈래가 옛 토큰을 넣는지만 보면 되고, 그것은 실물이 더 정확하다.
  - 고아 호출자 = 좌석 안에서 두 번 fork + setsid → ppid 1(조상 체인 없음) → 토큰만이 인가할 수 있는 호출자. 대조 = 같은 고아에서 토큰만 뺌 → rc 6(발신 pane 확정 못 함).
  - 실패 갈래 새지 않음(master 덧붙임): WELCOME 을 찍던 오류 문구(`좌석 pid 없음: {welcome}`)는 `welcome_without_tokens` 사본으로 · 정합 실패 처리 = `adopted_token_or_skip`(사건·로그 = skid·사유 낱말만) · e2e 훑기 = 진짜 토큰 + 난수 + 거절 갈래가 실어 보낸 바꾼 토큰.
  - `explain-state` 명령은 이 트리에 없다(grep 0) → 진단 표면 = `cys list` · `cys status --json` · topology · 격리 폴더 전체(상태·seatkeep·로그)를 훑는다.
- 뮤턴트(설계 ⓜ1~ⓜ4 + 3) = 결과는 HANDOFF T5 절.
- 📌 거절 문구 「동세대 발급분」(handlers.rs claim 불일치 갈래)은 입양 세대에도 같은 문구가 나간다 — 뜻은 맞으나(알려진 세대의 남의 토큰) 낱말이 좁다. 원작자 파일 문구라 소스 핀 위험이 있어 안 바꿈.
