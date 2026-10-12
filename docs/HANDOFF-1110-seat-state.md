# HANDOFF — cysd 좌석 판정: 뿌리가 에이전트 자신인 좌석이 유휴마다 「빈 좌석」 으로 읽히던 결함 (TICKET=cysr-1110-seat-state)

- **R4(2026-10-12 19:54~ · master#175bc660 · codex 3R 신규 MED 3건 · 마지막 라운드)의 정본은 §16** 다 — 지금 규칙의 최종 서술은 §16-2 다. §14·§15 의 규칙 서술 가운데 「비옵션 낱말 전부」 와 「내용으로 켜는 Windows 규약」 은 R4 에서 철회됐다.
- **R3(2026-10-12 19:16~ · master#f30628ff · codex 2R 신규 MED 3건)의 정본은 §15** 다 — 후보 기동 문자열의 셸 낱말 분해 · 인터프리터 옵션 값 · Windows 엔트리 규약. §14 의 규칙 서술 가운데 R3 로 바뀐 줄에는 「R3」 표시를 달았다.
- **R2(2026-10-12 18:28~ · master#40dad7fc · codex 1R 채택 3건)의 정본은 §14** 다 — 뿌리 존재 판정이 「어느 낱말이든」 에서 「자리(argv[0] · 인터프리터+엔트리)」 규칙으로 바뀌었고, §2 판정표·§3 줄 번호·§4 핑 줄·§8·§9 를 그에 맞춰 고쳤다.
- 발주 = master#06eeaab3(2026-10-12 17:25) · 범위 답 = master#6d32701a(1번 A안) · master#fe654723(2번 B안)
- 작업 트리 = `~/axdev/.wt/cys-1110-seat-state` · 가지 `fix/1110-seat-state` · 기준 `bb52b846`
- 작업자 = worker-seatstate(surface:1352 · Opus 5.5) · push 0 · 병합 0(둘 다 master 소관)

## 0. 한눈에

| 항목 | 내용 |
|---|---|
| 1번 커밋 | `fix(cysd)(1.1.9 좌석 판정 · master#06eeaab3)` — `src/bin/cysd/governance.rs` 1파일 + 이 문서 + 증거 폴더 |
| 2번 커밋 | `test(publish)(1.1.9 hdiutil 재시도 · master#06eeaab3)` — `scripts/tests/test_update_publish.py` 1파일 |
| R2 커밋 | `fix(cysd)(1.1.9 좌석 판정 R2 · master#40dad7fc)` — `governance.rs` + 이 문서 + 증거 폴더(§14) |
| R4 커밋 | `fix(cysd)(1.1.9 좌석 판정 R4 · master#175bc660)` — `governance.rs` + 이 문서 + 증거 폴더(§16) |
| R3 커밋 | `fix(cysd)(1.1.9 좌석 판정 R3 · master#f30628ff)` — `governance.rs` + `src/first_run_gates.rs`(분해기 공개 1낱말) + 이 문서 + 증거 폴더(§15) |
| 제품 거동이 바뀌는 좌석 | 뿌리 프로세스가 에이전트 자신(`cys new-surface --cmd '… claude …'`)이고, 팩 `agents.json` 에 **같은 실행 파일을 쓰는 에이전트가 둘 이상** 등록된 설치(이 맥 = claude · claude-fable · claude-sonnet) |
| 바뀌는 방향 | 그 좌석의 유휴 순간 판정 `empty` → `occupied` ⇒ 큐 배달 보류(`empty_seat`) 해소 · 빈 좌석 승계 대상에서 제외 |
| 안 바뀌는 것 | 뿌리가 셸인 좌석(맨 셸 = `empty` · 셸+에이전트 = `occupied`) · 종료 좌석 = `empty` · 프로세스 표에 없는 뿌리 = `unknown` · 에이전트 등록(정체) 규칙 · 데드맨 보조축 |

## 1. 결함 — 브리프의 가설과 실제 원인이 달랐다

### 1-1. 브리프의 가설
「`seat_state()` 가 자손 유무 한 가지로만 Empty 를 낸다. `cache_seat_verdict()` 에는 v113 보정(뿌리가 기지 에이전트면 Occupied)이 있지만 캐시 경로뿐이고, 큐 배달 쪽은 날 `seat_state()` 를 쓴다.」

### 1-2. 실측 — 큐 배달은 이미 보정된 캐시를 읽고 있었다
- 큐 배달이 「빈 좌석인가」 를 묻는 자리는 `role_seat_hold()` 한 곳이다(틱 배달 `deliver_queued` · 강제 배달 `force_deliver_entry` 둘 다 이 함수 · §4 표).
- `role_seat_hold()` 는 `s.seat_cache` 를 읽고, 그 캐시는 `refresh_seat_cache()` 가 `cache_seat_verdict()` 로 쓴다. 즉 **v113 보정이 얹힌 값**이다.
- 그런데도 실기(10-12 10:43 · surface 1348 · claude pid 생존)에서 `blocked_by=empty_seat` 가 났다. 보정이 있는데 왜 Empty 였는가가 진짜 질문이었다.

### 1-3. 실제 원인 — 「있는가」 를 「어느 것인가」 규칙으로 물었다
v113 보정의 호출 사슬(수리 전):

```
cache_seat_verdict → root_agent_cmd → seat_agent_observed → select_observed_agent
```

`select_observed_agent` 는 **등록용** 함수다. 「어느 에이전트인가」 를 정해야 하므로 서로 다른 에이전트가 동시에 맞으면 모호 = `None` 을 낸다(엉뚱한 CLI 를 부활시키는 것보다 기록하지 않는 편이 낫다는 계약 — 그 계약 자체는 옳다).

이 맥 설치 팩 `~/.cys/pack/agents.json` 의 후보(10-12 파일 실측):

| 에이전트 이름 | cmd | 실행 파일 이름 |
|---|---|---|
| claude | `claude --model claude-opus-5-5 --dangerously-skip-permissions` | claude |
| claude-fable | `claude --model claude-fable-5-1 --dangerously-skip-permissions` | claude |
| claude-sonnet | `claude --model claude-sonnet-5-5 --dangerously-skip-permissions` | claude |
| gemini | `~/.local/bin/agy --dangerously-skip-permissions` | agy |
| codex | `~/.npm-global/bin/codex --dangerously-bypass-approvals-and-sandbox` | codex |
| grok | `grok` | grok |

뿌리=claude 좌석의 뿌리 argv(10-12 `ps` 실측 · pid 17263·2552·96776 공통)는 `claude --dangerously-skip-permissions --model claude-opus-5-5 --effort high` 다. 이 명령줄은 위 세 claude 계열 후보에 **전부** 맞는다 → 이름이 서로 다른 에이전트 셋이 동시 매칭 → 모호 → `None` → 보정 미발화 → Empty → `empty_seat` 보류.

저장소 내장 `cysjavis-pack/agents.json` 은 claude 1종뿐이라(파일 실측) 원작자 환경과 기존 시험(`v113_root_agent_cmd_counts_pane_root_agent_only` = 후보 1개)에서는 드러나지 않았다.

### 1-4. 원인 확정 — 격리 실데몬 대조 3+1런(§6)
같은 검체(뿌리 = `claude 600` · 자손 0 · 역할 좌석)를 바이너리·팩만 바꿔 돌렸다.

| 데몬 바이너리 | 팩 후보 | 좌석 A(뿌리=claude) seat | 큐 1건 | 좌석 B(맨 셸) |
|---|---|---|---|---|
| 수리 전 — 설치본 cysr 1.1.8 | 이 맥 꼴(claude 계열 3) | empty · empty · empty | 보류 `empty_seat` · depth 1 | empty |
| 수리 전 — 이웃 트리 디버그 빌드(10-10) | 이 맥 꼴 | empty · empty · empty | 보류 `empty_seat` · depth 1 | empty |
| 수리 전 — 설치본 cysr 1.1.8 | 내장 claude 1종(원인 대조군) | occupied · occupied · occupied | 배달 · depth 0 | empty |
| **수리 후 — 이 트리 빌드** | 이 맥 꼴 | occupied · occupied · occupied | 배달 · depth 0 | empty |

셋째 줄이 원인을 가른다: 수리 전 바이너리도 후보가 1종이면 정상이다. 결함은 「뿌리 보정이 없어서」 가 아니라 「같은 실행 파일 후보가 여럿이면 보정이 꺼져서」 였다.

### 1-5. 그래서 브리프대로만 했다면
v113 블록을 `seat_state()` 안으로 옮기기만 하면 `root_agent_cmd` 가 계속 `None` 이라 **이 맥에서는 아무것도 고쳐지지 않는다.** 판정 자체를 「후보 가운데 하나라도 엄격 매칭이면 있다」 로 바꿔야 했다(master 답 = A안: 뿌리 경로만 · 자손 쪽 데드맨 보조축은 무접촉).

## 2. 수정 — `src/bin/cysd/governance.rs`

| 함수 | 종류 | 내용 |
|---|---|---|
| `seat_verdict(exited, root_in_table, descendants, root_cmd, specs)` | 신설 · 순수 | 좌석 1차 판정의 **단일 정의**. 판정표는 아래(R2: 마지막 인자가 뿌리 후보 목록으로 바뀜) |
| `known_agent_cmd(cmd, candidates)` | 신설 · 순수 | **존재** 판정 — 후보 가운데 하나라도 `cmdline_matches_agent_exec`(엄격 매처)에 맞으면 참. R2 뒤로는 `root_agent_cmd`(생존·데드맨 재료)만 쓴다 — 좌석 판정은 `root_cmd_is_agent` |
| `seat_state_of(sys, root, exited, specs)` | 신설 | 판정 재료 수집(프로세스 표 · 자손 수 · 자손 0 일 때만 뿌리 argv) → `seat_verdict` |
| `root_cmd_is_agent(root_cmd, specs)` · `RootAgentSpec` · `agent_root_specs_from_json` · `known_agent_root_specs` | **R2 신설** · 순수(로더 1 제외) | 뿌리 전용 존재 판정과 그 후보(실행 파일 + 엔트리) — §14 |
| `seat_state(sys, s)` | 본문 교체 | `seat_state_of(sys, s.pid, exited, &mut None)` — 시그니처 불변 |
| `cache_seat_verdict(sys, s, candidates)` | 본문 교체 | `seat_state_of(…, candidates)` — v113 블록은 `seat_verdict` 로 올라감 |
| `root_agent_cmd(sys, root, candidates)` | 1줄 | `seat_agent_observed(…)` → `known_agent_cmd(&cmd, candidates)` |
| `seat_claimable(sys, s)` | 본문 정리 | `seat_claimable_verdict(seat_state(sys, s), meta_blocks_seat(s), human_recent)` — 판정 결과 불변 |
| `seat_claimable_verdict(seat, meta_blocks, human_recent)` | 신설 · 순수 | 승계 가능 = Empty ∧ 살아 있는 meta 없음 ∧ 최근 사람 입력 없음 |

`seat_verdict` 판정표(위에서 아래로 첫 매치):

| 조건 | 결과 |
|---|---|
| 종료된 surface | Empty |
| 뿌리 pid 가 프로세스 표에 없음 | Unknown |
| 자손 1개 이상 | Occupied |
| 자손 0 ∧ 뿌리 argv 가 기지 에이전트의 **기동 꼴**(R2 · `root_cmd_is_agent` · §14-2) | Occupied ← 이번에 1차 사실로 올라간 줄 |
| 자손 0 ∧ 그 밖(맨 셸 · argv 미관측 · 후보 없음) | Empty |

무접촉으로 둔 것: `select_observed_agent`(등록 · 정체) · `seat_agent_observed`(무메타 좌석의 `seat_agent_cache` = 데드맨 `SeatVacantNoMeta` 보조축 · 부서 `seat_no_agent` 보류) · `cmdline_matches_agent_exec`(자손 쪽 매처) · `role_seat_hold` · handlers·alert_route·schedule 전부. (R2 에서 `agent_seat_vacant_now` 의 「뿌리가 에이전트인가」 2줄과 `refresh_seat_cache` 의 후보 지연 로드 칸 1개는 손댔다 — §14-3.)

비용: 뿌리 argv 는 종전(v113 블록)과 같이 「자손 0 인 살아 있는 좌석」 에서만 읽는다. 틱 경로의 호출 수는 그대로다. 즉시 프로브(`seat_claimable_now` · `agent_seat_vacant_now`)는 자손 0 일 때 `agents.json` 읽기 1회 + argv 읽기 1회가 늘었다(드문 경로).

## 3. 소비처 표 — 「이 좌석이 쓰이는 중인가」 를 묻는 모든 자리(제품 코드)

줄 번호는 **R4 커밋** 기준이다(라운드마다 governance.rs 가 밀려 다시 맞췄다 — 단 R3 에서 생겼다가 R4 에서 사라진 `interpreter_operands` :3913 · `entry_matches` :3955 · R3 의 `root_cmd_is_agent` :3991 은 §15 의 서술 그대로 둔 옛 줄이다. 지금 자리는 §16-3). 「전」 = 기준 bb52b846.

### 3-1. 판정을 **만드는** 자리(전부 `seat_verdict` 한 곳으로 모임)

| 자리 | 전 | 후 |
|---|---|---|
| `governance.rs:4024` `seat_state()` — 즉시 프로브의 입구 | 자손 유무만 · 뿌리 보정 없음 | `seat_state_of` → `seat_verdict` |
| `governance.rs:4078` `cache_seat_verdict()` — 틱(`refresh_seat_cache` :4206) · 생성 직후(`prime_seat_cache_at_create` :4098) | `seat_state()` + v113 블록(`root_agent_cmd` = 등록 규칙 → 후보가 겹치면 미발화) | `seat_state_of` → `seat_verdict`(같은 본체) |
| `governance.rs:4311` `seat_claimable()` ← `seat_claimable_now()` :4328 — 승계 게이트 | 날 `seat_state()`(뿌리 보정 없음) | `seat_state()`(같은 본체) → `seat_claimable_verdict` |
| `governance.rs:4444` `agent_seat_vacant_now()` — 빈 셸 가드 | 날 `seat_state()`(뿌리 보정 없음) + 「뿌리가 에이전트인가」 = `root_agent_cmd`(어느 낱말이든) | `seat_state()`(같은 본체) + 「뿌리가 에이전트인가」 = `root_cmd_is_agent`(R2 · :4457 · 좌석 판정과 같은 뿌리 규칙) |

### 3-2. 즉시 프로브를 **부르는** 자리(호출 코드는 무수정 · 받는 값이 달라진다)

| 자리 | 부르는 함수 | 뿌리=에이전트 유휴 좌석에서 전 → 후 |
|---|---|---|
| `handlers.rs:611` `close_if_empty` | `seat_claimable_now` | meta 없는 좌석이면 「승계 가능」 → 「불가」(닫기 후보에서 빠짐). meta 가 살아 있는 좌석은 전에도 meta 가 막았다 |
| `handlers.rs:1245` `reclaim_commit` | `seat_claimable_now` | 같음 |
| `handlers.rs:5776` `dispatch`(역할 선언 승계) | `seat_claimable_now` | 같음 |
| `handlers.rs:8287` `dispatch`(부트 선언 승계) | `seat_claimable_now` | 같음 |
| `handlers.rs:4566` `deliver_to_ceo` | `agent_seat_vacant_now` | false → false(전에도 뿌리가 셸이 아니라 false · 이제는 Occupied 에서 일찍 반환) |
| `handlers.rs:6456` `dispatch`(surface.send_text 빈 셸 가드) | `agent_seat_vacant_now` | 같음 |
| `schedule.rs:2654` `inject_on` | `agent_seat_vacant_now` | 같음 |

### 3-3. 캐시(`seat_cache`)를 **읽는** 자리(코드 무수정 · 캐시 값이 달라진다)

| 자리 | 무엇에 쓰나 | 뿌리=에이전트 유휴 좌석에서 전(후보 겹침 팩) → 후 |
|---|---|---|
| `governance.rs:4166` `role_seat_hold()` | **큐 배달 보류** | `empty_seat` 보류 → 통과 ← 이번 티켓의 목표 |
| `governance.rs:1434` 데드맨 틱 → `liveness_verdict` | meta 좌석의 `AgentNeverStarted` · 무메타 좌석의 `SeatVacantNoMeta` | Empty → Occupied(사망 후보에서 빠지는 방향) |
| `governance.rs:4669` `seat_takeover_recheck()` | 승계 직전 재검(캐시가 Occupied 면 취소) | 취소 사유 없음 → 「좌석 캐시가 Occupied」 로 취소 |
| `governance.rs:7894` `machine_hold_probe()` 의 `shell_evidence` | 기계 보류 판정의 「셸 증거」 축 | true → false |
| `alert_route.rs:1756` `seat_is_agent_backed()` | 경보·스케줄 push 의 대상 좌석 적격 | 부적격 → 적격 |
| `handlers.rs:4560` `deliver_to_ceo` | CEO 좌석 적격 | SeatEmpty → 통과 |
| `handlers.rs:1020` `reclaim_live_snapshot` · `:6164` · `:10513` · `:12074` · `governance.rs:13385` | status·topology·이벤트의 `seat` 문자열 노출 | `"empty"` → `"occupied"` |

### 3-4. `root_agent_cmd` 를 부르는 자리(존재 판정으로 바뀐 영향)

| 자리 | 후보 | 전 → 후 |
|---|---|---|
| `governance.rs:941` · `:971` 사망 감지 | 그 좌석 meta 1개 | 불변(후보 1개는 모호할 수 없다) |
| `governance.rs:4232` `refresh_seat_cache` 의 `seat_agent_cache` 재료 | 전체 후보 | 뿌리 argv 가 재료 목록에 **들어가기는** 한다. 그러나 바로 다음 줄 `seat_agent_observed` 가 종전 규칙이라 후보가 겹치면 여전히 미관측 = 결과 불변(A안이 남긴 자리 · §8) |
| `governance.rs:877` 2표본 확정 대기(주석상 unix 는 항상 no-op) | 전체 후보 | 뿌리가 후보 겹침 에이전트이고 **자손에 다른 종류 에이전트가 하나만** 있는 좌석: 전 = 자손 쪽으로 확정 · 후 = 모호 → 유보. Windows 한정 · 그 꼴의 좌석은 실측한 적 없음 |
| (R2 로 호출 삭제) `agent_seat_vacant_now` 의 `root_is_agent` | — | R2 에서 이 자리는 `root_agent_cmd` 를 부르지 않는다 — `root_cmd_is_agent`(:4457)로 바뀌었다(§14-3) |

## 4. 큐 배달 경로는 어느 함수로 「빈 좌석」 을 묻는가(브리프 2항 답)

| 경로 | Empty 를 묻는 코드 줄 | 읽는 값 |
|---|---|---|
| 틱 배달(조용해지면 자동 배달 · `cys send --queued`) | `governance.rs:13369` `deliver_queued` → `role_seat_hold(&s, now_epoch(), dept_grace)` | `seat_cache` |
| 강제 배달(`cys queue deliver`) | `governance.rs:12988` `force_deliver_entry` → `role_seat_hold(…)` | `seat_cache` |
| 직접 전송(`cys send` · surface.send_text) | `handlers.rs:6456` → `agent_seat_vacant_now` | 즉시 프로브. 빈 셸로 판정되면 본문을 큐로 돌린다(→ 위 두 줄의 게이트로) |
| 스케줄 push(정기 스캔 등 `[schedule …]`) | `schedule.rs:2654` `inject_on` → `agent_seat_vacant_now` · 대상 좌석 선정은 `alert_route.rs:1756` `seat_is_agent_backed` | 즉시 프로브 + `seat_cache` |
| 각성 핑(`cys reinject --check`) | `src/bin/cys.rs:24841` `run_reinject` → `inject_text_opts`(:4039): **직접 전송이 먼저다**(`surface.send_text` · authoritative) → 데몬의 `handlers.rs:6456` 빈 셸 가드(`agent_seat_vacant_now`)를 지난다. 그 요청이 타이핑 가드 오류로 거부되면(:4065) 같은 본문을 **큐로 1회 전환**한다(:4079 `queued: true` · from = `inject(typing_guard fallback)`) → 위 틱 배달 게이트(`role_seat_hold`). (R2 에서 코드 줄 확인 · codex 1R 보조 관측과 일치. R1 문서의 「추정」 을 이 사실로 교체) | 즉시 프로브 → (전환 시) `seat_cache` |
| master 큐 폴백(`master-send.sh` 의 queued 판정) | cys 저장소 밖 스크립트 — 큐에 들어간 뒤로는 위 틱 배달 게이트 | `seat_cache` |

10-12 사고와의 대응: 큐로 간 R4 브리프가 `empty_seat` 로 멈춘 것 = 첫 줄. 「직접 send + Return 은 통했다」 = 셋째 줄(뿌리가 셸이 아니라 빈 셸 가드가 발화하지 않음). 「reinject --check = 핑 큐 적재」 = 다섯째 줄의 큐 전환(그 좌석에 사람 입력 계수가 남아 타이핑 가드가 직접 전송을 거부 → 큐 → `empty_seat`).

## 5. 시험

### 5-1. 새 시험 4건(`governance.rs` 시험 모듈 · 이름 접두 `seat119_`)

| 브리프 번호 | 시험 | 재는 것 |
|---|---|---|
| ① | `seat119_root_agent_with_no_descendants_is_occupied_even_when_candidates_share_a_binary` | 이 맥 팩 꼴(claude 계열 3 + gemini·codex·grok) × 실측 뿌리 argv → `select_observed_agent` 는 여전히 None(등록 규칙 무접촉) · `known_agent_cmd` = 참 · `seat_verdict` = Occupied. 후보 1개 꼴·경로 붙은 뿌리도 Occupied |
| ②③④⑤ | `seat119_verdict_table_keeps_bare_shell_empty_and_dead_root_out` | ② 셸 뿌리 5종 · 비에이전트 뿌리 3종 · argv 미관측 · 후보 없음 = Empty ③ 자손 1 = Occupied ④ 종료 = Empty(자손·뿌리 무엇이든) ⑤ 표에 없는 뿌리 = Unknown |
| ⑥ + 실 프로세스 | `seat119_live_root_agent_seat_is_occupied_and_not_claimable`(unix) | 실제 `/bin/sleep 30` 을 뿌리로: 같은 실행 파일 후보 셋 → Occupied · `root_agent_cmd` = Some · 에이전트 아닌 후보 → Empty(대조군) · 종료 표시 → Empty · 죽인 뒤 → Unknown. 승계 판정표: 뿌리=에이전트 좌석 = 불가 · Empty = 가능 · meta·사람 입력·Unknown = 불가 |
| 배선 | `seat119_every_seat_probe_goes_through_the_single_verdict` | `seat_state`·`seat_claimable`·`agent_seat_vacant_now`·`root_agent_cmd` 가 같은 본체를 지남 · `fn seat_verdict(` 1개 · 옛 식 `collect_descendants(sys, s.pid).is_empty()` 0건 |

기존 시험 1건 재표적: `v113_root_agent_wired_into_seat_cache_and_liveness` — 「캐시 판정이 뿌리 관측을 쓴다」 는 단언 목적은 그대로, 찾는 자리만 `cache_seat_verdict` 본문 → `seat_state_of`·`seat_verdict` 본문으로 옮겼다. 후보 1개 꼴의 `v113_root_agent_cmd_counts_pane_root_agent_only` 는 무수정 유지.

### 5-2. 뮤턴트 9종 — 전부 잡음(한 번에 하나 · 끝나면 원본 복원 확인)

| # | 뮤턴트 | 적색이 된 시험 |
|---|---|---|
| M1 | 판정에서 뿌리 에이전트 절 삭제(= v113 블록 되돌림) | ① · 실 프로세스 · v113 배선 핀 |
| M2 | 존재 판정을 옛 「정확히 한 에이전트」 규칙으로(= **수리 전 재현**) | ① · 실 프로세스 |
| M3 | 승계 판정이 Unknown 을 통과 | 실 프로세스(⑥) |
| M4 | 승계 판정이 meta 를 안 봄 | 실 프로세스(⑥) |
| M5 | 판정이 종료를 안 봄 | ④ |
| M6 | 표에 없는 뿌리를 Empty 로 | ⑤ · 실 프로세스 |
| M7 | 승계 게이트가 옛 자손 유무 식으로 우회 | 배선 핀 |
| M8 | 본체가 뿌리 argv 를 판정에 안 넘김 | 실 프로세스 · v113 배선 핀 |
| M9 | 뿌리 관측(`root_agent_cmd`)을 옛 규칙으로 | 배선 핀 · 실 프로세스 |

M2 가 「수리 전 None/Empty · 수리 후 Occupied」 의 단위 층 증거다(같은 시험이 옛 규칙에서 적색 · 새 규칙에서 초록). 후보 1개 꼴의 기존 v113 시험은 M2 에서도 초록이다 — 그 시험만으로는 이 결함을 볼 수 없었다는 뜻이다.

## 6. 격리 실연 — `docs/seat-state-evidence-2026-10-12/`

- 검체 = `seat-root-agent-e2e.py`(실데몬 · 격리 HOME·소켓·상태·팩 · 트립와이어 · 종료는 기록한 pid 만).
- 좌석 A = 뿌리 `claude 600`(이름만 claude 인 `/bin/sleep` 심링크 · 자손 0 · 역할 worker-e2e) · 좌석 B = 맨 셸(역할 worker-shell).
- (R2 뒤) `e2e-after.txt` 는 R2 최종 빌드로 다시 돌린 것이고 `e2e-after-shell-candidates.txt` · `mutants-r2.py`·`mutants-r2.txt` 가 더해졌다. `mutants.py`·`mutants.txt` 는 R1 커밋 소스 기준 기록이다(R2 소스에는 일부 바늘이 맞지 않는다 — R2 는 `mutants-r2.py`).
- 결과 원문 4개: `e2e-after.txt` · `e2e-before-installed.txt` · `e2e-before-neighbor.txt` · `e2e-before-single.txt`(§1-4 표가 그 요약). 뮤턴트 스크립트·출력 = `mutants.py`·`mutants.txt`(Rust 9종) · `mutants-hdiutil.py`·`mutants-hdiutil.txt`(2번 5종).
- 네 런 모두: 좌석 B = empty 3/3 · 트립와이어 적중 0 · 강제 종료한 뿌리 0 · 끝난 뒤 남은 프로세스 0(ps 확인).

## 7. 게이트 수치(격리 HOME · 좌석 `CYS_*` env 제거 · 이 작업 트리)

| 게이트 | 결과 |
|---|---|
| `cargo test --bin cysd -- seat119 v113_ seat_agent_observed select_observed`(해당 묶음) | 12 passed / 0 failed(2600 filtered out) |
| `cargo test --bin cysd`(전체 · **최종 소스** · 17:58~18:06) | **2604 passed / 0 failed / 8 ignored** · 418.59s |
| 같은 전체 실행 1회 더(최종 소스 직전 = 시험 문자열 1곳·주석 1곳을 고치기 전 · 17:45~17:52) | 2604 passed / 0 failed / 8 ignored · 397.11s |
| `cargo test --lib` | 1077 passed / 0 failed / 2 ignored · 298.55s |
| `cargo clippy --bin cysd --tests --message-format=short` | rc 0 · error 0 · 파일 위치가 있는 경고 355줄(governance.rs 60) 가운데 **이번에 바꾼 줄 범위 안 = 0**(diff 의 14개 범위와 줄 번호 대조). 기준 트리의 clippy 총수는 따로 재지 않았다 — 「신규 0」 의 근거는 총수 비교가 아니라 이 줄 범위 대조다 |
| `python3 scripts/tests/test_update_publish.py` | 107 통과 / 0 실패(건너뜀 14) · 마운트 잔류 0 |
| `bash scripts/secret-scan.sh --all`(새 파일 스테이징 상태) | clean(1694 파일). 1차 실행은 적색 1건이었다 — 내가 쓴 시험 문자열의 홈 경로 견본. 홈이 아닌 경로(`/opt/agents/bin/claude …`)로 바꿔 해소 |
| 팩 계약(`test_pyseal_census.py` · `test_bootv2_doc_contract.py` · `test_content_pins_parity.py`) | `PYSEAL-CENSUS-OK` · `BOOTV2-DOC-CONTRACT-OK` · `OK` — 증거 폴더에 파이썬 3파일을 넣었으므로 확인 |
| ui · 팩 | 변경 0(시험하지 않음) |
| 격리 실연 4런 | §1-4 표 · 수리 후 런은 최종 소스 빌드로 다시 돌린 것 |

기준 대비: 기준 bb52b846 의 cysd 시험 수 = 2608(이번에 +4 = 2612 · 그중 8 은 기존 ignored). 전체 실행에서 실패가 0 이라 「기준과 같은 실패」 로 넘긴 것은 없다.

## 8. 남긴 것 — 별도 후보

### 8-1. B 후보: 자손 쪽 존재 판정(`seat_agent_observed`)에 같은 꼴이 남아 있다
- 자리 = `governance.rs:4067` `seat_agent_observed` → `select_observed_agent`. 쓰는 곳 = `refresh_seat_cache` :4233 → `seat_agent_cache`.
- 영향 = **무메타 좌석**에서만: 데드맨 보조축 `SeatVacantNoMeta` 의 무장(`liveness_verdict`) · 부서 좌석의 `seat_no_agent` 보류(`role_seat_hold` · 생성 뒤 180초 유예 안).
- 후보가 겹치는 팩에서는 claude 자손을 봐도 「미관측」 이라, 보조축이 조용히 꺼져 있고 부서 무메타 좌석은 유예 내내 보류된다(코드 판독 · 실측 아님).
- 같은 성질 하나 더(R2 · codex 1R MED 의 자손판): 자손 쪽 매처 `cmdline_matches_agent_exec` 는 명령줄의 **어느 낱말이든** 본다 — `tail -f /tmp/claude` 가 자손이면 에이전트 관측으로 센다. 뿌리는 R2 에서 자리 규칙으로 바꿨고 자손 쪽(등록·데드맨)은 master 지시로 무접촉이다. B 를 열 때 함께 잰다.
- 고치는 법 = `seat_agent_observed` 본문을 `cmds.iter().any(|c| known_agent_cmd(c, candidates))` 로(1줄). 거동 변화 = 이 맥에서 그 보조축이 처음으로 실제 무장된다 → 사망 경보 거동을 따로 재야 한다(그래서 이번 티켓에서 제외 · master 결정).
- B 티켓의 입력 — 이 맥 본부 데몬의 좌석별 meta 실측(2026-10-12 17:34 · `cys status --json`):

| surface | role | agent(meta) | seat | seat_agent |
|---|---|---|---|---|
| 1307 | worker-eduscan | claude-sonnet | occupied | false |
| 1314 | worker | claude | occupied | false |
| 1336 | worker-lms | claude | occupied | false |
| 1340 | worker-6 | claude | occupied | false |
| 1352 | worker-seatstate | claude | occupied | false |

  좌석 5 · **무메타 좌석 0**. `seat_agent` 는 무메타 좌석에서만 계산되므로 전부 false 다. 지금 이 맥 본부에서 B 를 고쳐도 당장 무장되는 좌석은 없다 — 무메타 에이전트 좌석(사람이 손으로 claude 를 띄우고 역할만 선언한 좌석 · 부서 좌석)이 생길 때 차이가 난다. 같은 시각 프로세스 표에는 자식이 0 인 `cysd` 가 9개 더 있었다(부서·시험 데몬인지 미확인 · 좌석 없음).

### 8-2. 그 밖의 관찰(수정 안 함)
- `SeatState::Occupied` 의 문서 주석에는 「자손이 없어도 뿌리 자신이 기지 에이전트면 여기」 를 한 줄 더했다. 그 위 설계 원칙 문단(「커널 사실 1차 = 셸 이외의 자손이 있는가」)과 `Empty` 주석(「셸 단독」)은 그대로 두었다 — 판정표의 정본은 `seat_verdict` 의 문서 주석이다.
- ~~셸이 실행 파일인 후보가 있으면 맨 셸 좌석이 Occupied~~ · ~~뿌리가 `vim claude` 처럼 인자에 이름을 든 비에이전트면 Occupied~~ — R1 은 이 둘을 「한계」 로 적고 넘겼다. codex 1R 이 각각 HIGH(빈 셸 가드 해제 = 회귀)·MED(승계 차단)로 재현했고 **R2 에서 고쳤다**(§14). R1 의 판단이 틀렸던 자리다: 캐시 경로에만 있던 한계를 즉시 프로브(빈 셸 가드·승계 게이트)로 넓힌 것은 한계의 승계가 아니라 새 회귀였다.
- R2 뒤에 남는 뿌리 규칙의 한계 = §14-6.

## 9. 운영 보조 처방(코드 변경 아님 · master 쪽 선택지) — R2 정정

R1 문서의 「`bash -lc '…'` 로 감싸면 수리 전 데몬에서도 늘 occupied」 는 **틀렸다**(codex 1R LOW · 내 실측으로 확인). bash 도 zsh 도 `-lc` 의 **마지막 명령을 exec 로 바꿔 친다** — 감싸도 뿌리는 그 명령 자신이 된다.

실측(2026-10-12 18:3x · 이 맥 · `[셸, "-lc", 본문]` 으로 띄우고 1.2초 뒤 같은 pid 의 argv 와 자식 수):

| 띄운 꼴 | 그 pid 의 argv | 자식 |
|---|---|---|
| `/bin/bash -lc '/bin/sleep 4'` | `/bin/sleep 4` | 0 |
| `/bin/zsh -lc '/bin/sleep 4'` | `/bin/sleep 4` | 0 |
| `/bin/bash -lc '/bin/sleep 4; exec /bin/bash'` | `/bin/bash -lc /bin/sleep 4; exec /bin/bash` | 1 |
| `/bin/zsh -lc '/bin/sleep 4; exec /bin/zsh'` | `/bin/zsh -lc /bin/sleep 4; exec /bin/zsh` | 1 |
| `/bin/bash -lc '/bin/sleep 4; wait'` · zsh 도 같음 | 셸 그대로 | 1 |

- 수리 전 데몬(1.1.8 까지)에서 쓰는 임시 처방은 **셸이 남도록 뒤에 명령을 하나 더 붙인 꼴**이어야 한다: `cys new-surface --cmd "bash -lc '… claude …; exec \$SHELL'"`(claude 가 끝나면 셸로 떨어짐) 또는 `…; wait`. 그러면 claude 가 셸의 자식으로 남아 좌석이 늘 occupied 다. spawn-worker 경로(뿌리 `zsh -l` 에 claude 를 타이핑)는 처음부터 이 꼴이다(1307·1314).
- 감싼 뒤에는 **반드시 `ps` 로 뿌리 argv 와 자식 수를 확인한다** — 「감쌌으니 됐다」 는 위 표 첫 두 줄처럼 틀릴 수 있다.
- 이 수정이 들어간 데몬(1.1.9)에서는 감싸지 않아도 된다.

## 10. 되돌리기
- 1번: `git revert <1번 커밋>` — `governance.rs` 1파일 + 문서. 스키마·저장 형식·RPC 무변경이라 데몬 재시작 외 후속 조치 없음.
- 2번: `git revert <2번 커밋>` — 시험 파일 1개.
- 부분 되돌리기(뿌리 관측만 옛 규칙으로) = `known_agent_cmd` 본문을 `seat_agent_observed(&[cmd.to_string()], candidates)` 로(뮤턴트 M2 와 같은 모양).

## 11. 2번 항목 — hdiutil 재시도(`scripts/tests/test_update_publish.py`)

- **이미 반이 되어 있었다**: 커밋 `061e041a`(TICKET=cysr-1110-backlog · master#1378f1c3)가 도우미 `hdiutil_retry`(1회 재시도 · rc·stderr 출력 · 반쪽 dmg 삭제)와 단위 3(`TestHdiutilRetry`)을 넣고, 10-07 run 37543589887 의 실패 자리(`TestOfflineRitual.setUp`)를 고쳤다. 도우미는 이번에 손대지 않았다.
- 이번에 닫은 남은 두 자리(master 답 B안):
  1. `setUpModule` 의 매체 전제 확인 — `media_probe_failures()` 로 끌어내 create·attach 를 `hdiutil_retry` 로. 2회 실패 = 종전처럼 `RuntimeError`(모듈 오류 · 건너뛰기 없음 · `REQUIRE_ALL` 계약 그대로).
  2. `second_media()` — `check_call` 2줄 → `hdiutil_retry` · 2회 실패 = `self.fail`(사유 2줄).
- 추가 시험 3(`TestHdiutilRetry` 안 · 가짜 runner · 플랫폼 무관):
  - `test_module_probe_survives_one_transient_create_failure` — create 첫 실패·둘째 성공 = 통과(create·create·attach·detach).
  - `test_module_probe_two_failures_stay_a_module_error` — 둘 다 실패 = 사유 실린 목록 → `setUpModule()` 이 `RuntimeError` · attach 미호출.
  - `test_every_create_and_attach_goes_through_the_retry_helper` — 배선 핀: 이 파일에 hdiutil create·attach 직접 호출 줄 0 · 도우미 실행 줄 1 · 도우미를 거치는 호출부 3.
  - master 답은 「추가 = 배선 핀 1」 이었다. 앞의 두 건은 브리프 2번이 적은 단위 2(첫 실패·둘째 성공 / 둘 다 실패 = 모듈 오류 유지)라 남겼다 — 도우미가 아니라 `setUpModule` 쪽 거동을 잰다. 빼라고 하면 그 두 메서드만 지우면 된다.
- 수치: `python3 scripts/tests/test_update_publish.py` = 107 통과 / 0 실패(건너뜀 14 = 기존 VERIFY_BIN·node 조건 · 수정 전 104) · 끝난 뒤 마운트 잔류 0.
- 음성 대조 5종 전부 잡음: P1 둘째 매체를 직접 호출로 되돌림 → 배선 핀 · P2 재시도 0 → 4건 · P3 전제 확인이 실패를 무시 → 모듈 오류 시험 · P4 `setUpModule` 이 실패 목록을 버림 → 모듈 오류 시험 · P5 전제 확인이 도우미를 안 거침 → 3건.

## 12. 함정·관찰
1. **「보정이 있다」 와 「보정이 발화한다」 는 다른 사실이다.** 브리프와 CSO 실측은 코드에 v113 블록이 있다는 데서 「캐시 경로는 안전」 으로 읽었다. 설치 팩의 후보 목록을 넣어 보기 전에는 그 블록이 한 번도 돌지 않는다는 것이 보이지 않았다. 판정 코드를 볼 때는 **그 설치의 실제 입력**(여기서는 `~/.cys/pack/agents.json`)을 같이 읽는다.
2. **존재를 정체 규칙으로 묻지 않는다.** 「있는가」 와 「어느 것인가」 는 모호할 때 답이 반대다(있다 / 기록 안 함).
3. 맥은 시스템 바이너리의 **사본** 실행을 막는다 — `/bin/sleep` 을 `claude` 로 복사하면 좌석이 즉시 종료된다. 이름만 바꾼 **심링크**는 되고 argv[0] 이 그 이름이 된다.
4. 실 프로세스 시험은 PTY 좌석을 쓰지 않았다. `create_surface(… "sleep 30")` 의 뿌리가 셸인지 sleep 인지는 로그인 셸의 exec 여부에 달려 비결정이다(09-10 · 09-23 기록). 그래서 본체를 pid 로 받는 `seat_state_of` 로 끌어내 `/bin/sleep` 자식을 직접 뿌리로 쟀다.
5. 뮤턴트와 cargo 는 겹쳐 돌리지 않았다. 뮤턴트가 도는 동안에는 Rust 소스를 건드리지 않고 파이썬 쪽(2번)만 진행했다.
6. 격리 실연 중 설치본 데몬은 `phoenix-embed` python 자식을 스스로 띄운다(격리 폴더 안). 정리는 데몬 pid 와 그 직계 자식 pid 로만 했고 끝난 뒤 잔류 0 을 확인했다.
7. 이종 검토(codex 1R)는 이 티켓 안에서 돌리지 않았다(브리프: master 가 스냅샷 재검 뒤). → master 가 돌렸고 결과가 §14 다.
8. (R2) **「전부터 있던 한계」 라고 적기 전에 그 한계의 소비처가 넓어졌는지 본다.** R1 은 「셸 실행 후보 → 맨 셸 Occupied」 를 v113 캐시 경로의 기존 한계로 적었다. 그 값을 즉시 프로브(빈 셸 가드·승계 게이트)가 새로 읽게 한 것이 이번 변경이었으므로, 같은 한계가 새 소비처에서는 회귀(가드 해제)였다. 판정을 한 곳으로 모을 때는 「모인 판정의 가장 느슨한 줄이 모든 소비처에 적용된다」 를 소비처마다 대조한다.
9. (R2) 뿌리와 자손은 같은 매처로 물을 수 없다. 자손은 「이 좌석 어딘가에 에이전트가 도는가」 라 낱말 매칭이 맞고, 뿌리는 「이 프로세스가 에이전트인가」 라 자리(argv[0]·엔트리)를 봐야 한다.
10. (R2) 실연 결과에 라벨을 붙이기 전에 **바이너리의 빌드 시각**을 본다. 셸 후보 팩 런을 「R1 커밋 빌드」 로 적어 저장했다가, `target/debug/cysd` 가 그 사이 R2 소스로 다시 빌드된 것(18:32)을 보고 그 파일을 버렸다. 그래서 R1 바이너리의 실데몬 재현 런은 없다(§14-5 에 그대로 적음).

## 13. 재현 명령

```sh
cd ~/axdev/.wt/cys-1110-seat-state
a=(); while IFS= read -r n; do a+=(-u "$n"); done < <(env | sed -n 's/^\(CYS_[A-Za-z0-9_]*\)=.*/\1/p')
ISO() { env "${a[@]}" -u CLAUDE_CONFIG_DIR HOME="$(mktemp -d)" CARGO_HOME="$HOME/.cargo" RUSTUP_HOME="$HOME/.rustup" \
      PATH="$HOME/.bun/bin:$HOME/.cargo/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin" "$@"; }   # bash 에서

ISO cargo test --bin cysd -- seat119 v113_ seat_agent_observed select_observed   # R1 = 12 / 0 · R2 = 15 / 0 · R3 = 20 / 0
ISO cargo test --bin cysd                                                        # §7
ISO cargo test --lib                                                             # §7
ISO cargo clippy --bin cysd --tests --message-format=short                       # §7
ISO python3 scripts/tests/test_update_publish.py                                 # 107 / 0(skip 14)

# 격리 실연(수리 후 / 수리 전 / 원인 대조군)
ISO cargo build --bin cysd
E=docs/seat-state-evidence-2026-10-12
python3 $E/seat-root-agent-e2e.py target/debug/cysd target/debug/cys "수리 후"
python3 $E/seat-root-agent-e2e.py /Applications/cys.app/Contents/MacOS/cysd target/debug/cys "수리 전(설치본)"
SEAT119_AGENTS=single python3 $E/seat-root-agent-e2e.py /Applications/cys.app/Contents/MacOS/cysd target/debug/cys "수리 전 · 후보 1종"
SEAT119_AGENTS=shell python3 $E/seat-root-agent-e2e.py target/debug/cysd target/debug/cys "수리 후 R2 · 셸 후보 2"   # 맨 셸 좌석 B = empty 여야 한다
python3 $E/mutants-r2.py <격리 실행 래퍼>                                         # R2 뮤턴트 8종(끝나면 원본 복원)
python3 $E/mutants-r4.py <격리 실행 래퍼>                                         # R4 뮤턴트 5종(현재 소스 기준) · mutants-r3.py·r2.py·mutants.py 는 각 라운드 커밋 소스 기준 기록
python3 $E/mutants-r3.py <격리 실행 래퍼>                                         # R3 뮤턴트 8종 · ONLY=Q4 처럼 접두로 하나만 · mutants-r2.py 는 R2 커밋 소스 기준 기록
```

## 14. R2 — codex 1R(이종 · 병합 차단 HIGH 1) 채택 3건 (TICKET=cysr-1110-seat-state-r2 · master#40dad7fc)

검토 원문 = `~/axdev/master/reports/seat-state-1012/REVIEW-codex-1r.md`(채택 3 / 기각 5). master 판정 = 3건 전부 채택.

### 14-1. 지적과 처방

| # | 지적(codex 가 실 프로세스로 재현) | R1 의 어디가 틀렸나 | R2 처방 |
|---|---|---|---|
| ① HIGH | `agents.json` 에 셸이 실행 파일인 후보가 둘(`bash /opt/agents/a.sh` · `b.sh`)이면 **맨 셸 뿌리 `/bin/bash -l`(자손 0)가 Occupied** → 빈 셸 가드 true → false → `surface.send_text` 의 큐 전환 분기가 사라져 지시문이 셸에 타이핑된다 | 뿌리에 자손용 매처(어느 낱말이든)를 그대로 썼다. R1 문서는 이를 「v113 때부터의 한계」 로 적었지만, 캐시 경로에만 있던 것을 즉시 프로브(빈 셸 가드)로 넓힌 순간 회귀가 됐다 | 후보 실행 파일이 셸·인터프리터면 **엔트리(스크립트)까지** 같아야 뿌리와 맞는다. 엔트리 없는 뿌리(맨 셸 · `-l` · `-lc`)는 어떤 후보에도 맞지 않는다. 빈 셸 가드의 「뿌리가 에이전트인가」 도 같은 규칙으로 |
| ② MED | 뿌리 `/usr/bin/tail -f /tmp/claude` · `vim claude` 가 Occupied → 승계 true → false(장기 실행 비에이전트 때문에 역할 좌석을 회수하지 못함) | 같은 원인 — 인자 어딘가의 낱말을 실행 증거로 셌다 | 뿌리는 **자리**로만: argv[0] 이 에이전트 실행 파일이거나, 뿌리가 인터프리터이고 그 **엔트리**가 에이전트일 때만 |
| ③ LOW | 「bash 로 감싸면 수리 전에도 늘 occupied」 는 틀림 — bash 도 `-lc` 마지막 명령을 exec 교체 | 실측 없이 썼다 | §9 를 실측 표와 함께 다시 썼다 |
| 보조 | 핑은 직접 전송 먼저 → 타이핑 가드 오류 시 큐 전환 | R1 은 「추정」 으로 남겼다 | §4 의 핑 줄을 코드 줄(`cys.rs:24841` → `:4039` · `:4065` · `:4079`)로 교체 |

### 14-2. 뿌리 존재 판정 `root_cmd_is_agent(root_cmd, specs)`(순수 · `governance.rs:3991`)

재료(R3 로 바뀜 · §15): 뿌리의 **argv 그대로**(인자 경계 보존)에서 argv[0] 과, argv[0] 이 셸·인터프리터일 때 그 뒤의 **비옵션 낱말 전부**(`interpreter_operands` :3913 — 값 받는 옵션의 값은 건너뜀)를 꺼낸다. R2 는 공백으로 나눈 명령줄의 「첫 비옵션 낱말 하나」 였다. 셸의 `-c` 묶음(`-c` · `-lc` · `-ic`) 뒤는 명령 문자열이라 아무것도 내지 않는다. 로그인 셸 접두 `-`(`-zsh`)는 떼고 본다.

| 후보의 실행 파일 | 뿌리가 맞는 조건 |
|---|---|
| ⓐ 셸·인터프리터가 **아님**(claude · agy · codex · grok) | argv[0] 이 그 실행 파일 **또는** 뿌리가 인터프리터이고 그 비옵션 낱말 가운데 하나가 그 실행 파일(R3 · shebang 스크립트 `node …/bin/codex` · npm 번들 `node …/claude-code/cli.js`). 낱말 하나의 판정은 기존 엄격 매처의 낱말 규칙 그대로다(basename 일치 · `.js` 번들 · `.js` 경로의 패키지 조각 · Windows 확장자 정규화) |
| ⓑ 셸·인터프리터(`bash /opt/agents/a.sh` · `node ~/agents/main.js` · `python3 -m aider`) | argv[0] 이 그 인터프리터 **이고** 비옵션 낱말 가운데 하나가 후보의 엔트리와 같을 때만(R3 · `entry_matches` :3955 — `~/…` 는 홈 뒤 꼬리 · 절대 경로는 그대로 · 상대 경로·모듈 이름은 같거나 경로 꼬리가 같음). 엔트리가 없는 후보(맨 `bash`)는 어떤 뿌리에도 맞지 않는다 |

- 셸·인터프리터 목록(`is_interpreter_name` :3877) = 기존 `is_shell_name` 의 셸들 + `node` · `nodejs` · `bun` · `deno` · `ruby` · `perl` · `php` · `python*`(대소문자 무시 · Windows 실행 확장자 제거 뒤).
- 후보가 여럿 맞아도 참이다(존재 판정 — R1 의 원인 수리는 그대로).
- 후보(`RootAgentSpec { bin_base, entry }`)는 `agent_root_specs_from_json`(:5421)이 낸다. 실행 파일은 종전 `agent_candidates_from_json` 의 결과를 그대로 쓰고 엔트리만 더한다. 디스크 팩 ∪ 내장 팩 합치기는 `known_agents_with`(:5400) 한 곳으로 모았다(`known_agent_candidates` 의 본문을 옮긴 것 · 규칙 불변).

### 14-3. R2 로 바뀐 코드(R1 커밋 대비 · `governance.rs` 1파일)

| 자리 | R1 | R2 |
|---|---|---|
| `seat_verdict` 의 뿌리 절(:3838) | `known_agent_cmd(c, candidates)`(어느 낱말이든) | `root_cmd_is_agent(c, specs)`(자리 규칙) |
| `seat_state_of`(:4030) · `cache_seat_verdict`(:4078) 의 지연 로드 칸 | `(이름, 실행 파일)` 목록 | `(이름, RootAgentSpec)` 목록 — `known_agent_root_specs`(:5395) |
| `refresh_seat_cache`(:4206) | 후보 칸 1개를 좌석 판정과 `seat_agent_cache` 가 같이 씀 | 뿌리 후보 칸 `root_specs` 를 따로 둠(자손 0 좌석이 있을 때만 읽음) · `seat_agent_cache` 쪽은 종전 칸 그대로 |
| `agent_seat_vacant_now` 의 `root_is_agent`(:4457) | `root_agent_cmd(…).is_some()`(어느 낱말이든) | 뿌리 argv 를 읽어 `root_cmd_is_agent` |
| `agent_candidates_from_json` | env 대입 판별이 함수 안 클로저 | 같은 식을 `is_env_assign_word`(:5325)로 꺼내 뿌리 후보 파생과 같이 씀(판별식 불변) |
| `root_agent_cmd`(:5118) · `known_agent_cmd`(:3862) · 자손 쪽 전부 | — | **R1 그대로**(생존 판정·2표본 확정·`seat_agent_cache` 의 재료 — master 지시 「자손 쪽 매처 무접촉」) |

귀결 하나(정직 고지): `root_agent_cmd` 는 여전히 「어느 낱말이든」 이다. 그것을 부르는 자리는 사망 감지(:941 · :971 — 그 좌석 meta 1개로 물음)·2표본 확정(:877)·`seat_agent_cache` 재료(:4232)뿐이고, 좌석 판정·빈 셸 가드·승계 게이트는 이제 부르지 않는다(배선 핀이 빈 셸 가드에 `root_agent_cmd(` 가 다시 들어오면 적색).

### 14-4. 실 후보 꼴 실측 — 새 뿌리 규칙에 그대로 맞는가

이 맥 설치 팩 `~/.cys/pack/agents.json` 과 저장소 내장 `cysjavis-pack/agents.json` 의 모든 후보(10-12 18:3x 실측):

| 팩 | 후보 | cmd 의 실행 파일 | 그 실행 파일의 실체(실측) | 뿌리로 뜰 때의 argv 꼴 | 맞는 규칙 | 시험 |
|---|---|---|---|---|---|---|
| 이 맥 | claude · claude-fable · claude-sonnet | `claude` | `~/.local/bin/claude` → `~/.local/share/claude/versions/2.1.296` · Mach-O arm64 | `claude --dangerously-skip-permissions --model … --effort high`(ps 실측 · cysd 직계 pid 17263·2552·96776) · `~/.local/bin/claude --settings …`(ps 실측 · cmux 좌석 78661·9346) | ⓐ argv[0] | 통과 |
| 이 맥 | gemini | `~/.local/bin/agy` | Mach-O arm64 | `…/.local/bin/agy --dangerously-skip-permissions`(파일 종류로 본 꼴 · 지금 뿌리로 떠 있는 것은 없어 ps 로는 못 봄) | ⓐ argv[0] | 통과 |
| 이 맥 | codex | `~/.npm-global/bin/codex` | `#!/usr/bin/env node` 스크립트 → `../lib/node_modules/@openai/codex/bin/codex.js` 심링크 | `node …/.npm-global/bin/codex …`(shebang 이라 커널이 인터프리터를 argv[0] 에 둔다 — 지금 떠 있는 것은 없어 ps 로는 못 봄 · 추정) · 번들 직접 꼴 `node …/@openai/codex/bin/codex.js …` | ⓐ 인터프리터 + 엔트리 | 두 꼴 모두 통과 |
| 이 맥 | grok | `grok` | 이 맥에 설치돼 있지 않다(미실측) | `grok`(네이티브라면) | ⓐ argv[0] | 통과(가정한 꼴) |
| 내장 | claude | `claude` | 위와 같음 | 위와 같음 | ⓐ argv[0] | 통과 |
| 내장 | gemini | `~/.local/bin/agy` | 위와 같음 | 위와 같음 | ⓐ argv[0] | 통과 |
| 내장 | codex | `codex` | (PATH 의 codex = 위 스크립트) | `node …/bin/codex …` 또는 `codex …` | ⓐ 인터프리터 + 엔트리 · argv[0] | 통과 |
| 내장 | grok | `grok` | 미설치(미실측) | `grok` | ⓐ argv[0] | 통과(가정한 꼴) |

- **두 팩 모두 셸·인터프리터 기동형 후보(ⓑ)는 0개다.** 내장 팩은 시험이 직접 읽어 「엔트리가 있는 후보 0」 을 단언한다(`seat119r2_root_matches_by_position_not_by_any_argument_word` — 내장 팩에 그런 후보가 생기면 그 시험이 알려 준다).
- 그 밖에 시험이 재는 실 기동 꼴: npm 번들 claude(`node …/@anthropic-ai/claude-code/cli.js`) · 옵션 낀 node(`node --max-old-space-size=4096 …/bin/claude`) · Windows(`C:\Tools\claude.exe …` · `node.exe C:\npm\…\claude-code\cli.js`).

### 14-5. R2 시험·뮤턴트·실연

- 새 시험 3건: `seat119r2_shell_exec_candidates_never_make_a_bare_shell_an_agent`(codex ① 입력 그대로 — 셸 후보 2 × 맨 셸 6꼴 = Empty · 빈 셸 가드 true · 양성 3꼴 = Occupied · 다른 스크립트·다른 인터프리터 = Empty · 엔트리 없는 셸 후보는 무엇과도 불일치 · 엔트리 표기 3종) / `seat119r2_root_matches_by_position_not_by_any_argument_word`(codex ② 입력 — `tail -f /tmp/claude` 등 5꼴이 자손 매처로는 맞지만 뿌리 규칙으로는 Empty · 승계 가능 · 실 기동 꼴 13종 = Occupied · 내장 팩 후보로도 같은 답) / `seat119r2_live_tail_and_bare_shell_roots_stay_empty`(unix · 실 프로세스: 실제 `tail -f …/claude` 뿌리 = Empty·승계 가능 · 셸 후보 2 앞의 실제 맨 `/bin/sh` 뿌리 = Empty·가드 유지 · 후보의 스크립트를 실제로 돌리는 `/bin/sh <스크립트>` 뿌리 = Occupied · 다른 스크립트 후보로 재면 Empty).
- R1 시험 4건은 새 후보 형으로 옮겼다(단언 목적 불변 · 후보는 이 맥 팩의 cmd 문자열에서 파생). 배선 핀에 「빈 셸 가드가 `root_cmd_is_agent` 를 쓰고 `root_agent_cmd(` 를 부르지 않는다」 를 더했다. v113 배선 핀의 틱 호출 문자열은 `&mut root_specs` 로 재표적.
- 뮤턴트 8/8 잡음(`mutants-r2.txt`): **R1 셸 후보 매칭 허용(엔트리 요구 삭제 = HIGH 되돌림)** → 2건 적 · **R2 임의 낱말 매칭 허용(= MED 되돌림)** → 4건 적 · R3 빈 셸 가드만 옛 규칙 → 배선 핀 · R4 셸 `-c` 뒤를 엔트리로 → 1 · R5 엔트리 비교가 늘 참 → 2 · R6 인터프리터+엔트리 꼴을 안 봄 → 1(codex·npm claude 기동 꼴) · R7 뿌리 절 삭제(R1 라운드 M1 재확인) → 6 · R8 엔트리 없는 셸 후보도 맞음 → 1.
- 격리 실데몬 2런(최종 소스 빌드): `e2e-after.txt`(이 맥 팩 꼴 — A occupied×3 · 큐 배달 · B empty×3 = R1 의 목표가 그대로 선다) · `e2e-after-shell-candidates.txt`(이 맥 팩 꼴 + 셸 후보 2 `zsh /opt/agents/a.sh`·`b.sh` — **맨 `/bin/zsh -l` 좌석 B 는 empty×3** · A occupied×3 · 큐 배달). R1 커밋 빌드로 같은 셸 후보 팩을 돌린 「수리 전」 실데몬 런은 **없다** — 그 바이너리를 다시 빌드해 두지 않았다. R1 의 회귀는 codex 의 프로세스 재현과 뮤턴트 R1·R2(같은 시험이 옛 규칙에서 적색)로 본 것이다.

### 14-6. R2 뒤에 남는 한계 → R3 로 닫힌 것과 남은 것
R2 때 적은 다섯 가운데 **1(공백 경로)·3(값 받는 옵션)** 은 codex 2R 이 회귀로 재현했고 R3 에서 닫았다(§15). 남은 것은 §15-6 에 다시 적었다.

### 14-7. R2 게이트 수치(격리 HOME · 좌석 `CYS_*` env 제거)

| 게이트 | 결과 |
|---|---|
| `cargo test --bin cysd -- seat119 v113_ seat_agent_observed select_observed`(해당 묶음) | 15 passed / 0 failed(R1 12 + R2 새 3) |
| `cargo test --bin cysd`(전체 · R2 최종 소스 · 18:44~18:51) | **2607 passed / 0 failed / 8 ignored** · 403.43s(R1 2604 + 3) |
| `cargo test --lib` 1차(18:51~18:57) | **1076 passed / 1 failed** / 2 ignored — 실패 = `pack::tests::h_conc_3_settings_writers_share_the_preflight_lock` · 사유 전문 = `시간 오라클 무효 — 락 없는 RMW 도 보유 창을 넘겼다(218.558791ms ≥ 150ms)`(`src/pack.rs:11295`) |
| 그 시험 단독 3회(18:57) | 1 passed ×3(0.24~0.36s) |
| `cargo test --lib` 2차(전체 · 18:57~19:03) | **1077 passed / 0 failed** / 2 ignored · 328.72s |
| `cargo clippy --bin cysd --tests --message-format=short` | rc 0 · error 0 · 파일 위치가 있는 경고 355줄(governance.rs 60 — R1 때와 같은 수) 가운데 **기준 bb52b846 대비 바꾼 줄 범위(26개) 안 = 0** |
| `bash scripts/secret-scan.sh --all`(스테이징 상태) | clean(1697 파일) |
| `test_pyseal_census.py` | `PYSEAL-CENSUS-OK` |
| 뮤턴트 | 8 / 8 잡음 |
| ui · 팩 · `scripts/tests/test_update_publish.py` | R2 변경 0(다시 돌리지 않음) |

lib 1차 실패에 대한 판단(실측과 해석을 가른다): **실측** = 실패한 시험은 `src/pack.rs` 의 벽시계 시험이고, 사유는 그 시험이 스스로 「시간 측정이 무효」 라고 선언한 문장이다(락 없는 대조 동작이 150ms 를 넘김). R2 가 바꾼 것은 `src/bin/cysd/governance.rs` 뿐이고 lib 크레이트 소스는 한 줄도 바뀌지 않았다(`git diff bb52b846 --stat -- src ':!src/bin'` = 0). 단독 3회와 전체 2차는 통과했다. **해석** = 그 순간의 기계 부하로 인한 일시 실패로 본다(직후 `uptime` 부하 평균 4.64). 「기준과 같은 실패」 라고 부르지는 않는다 — 기준 트리에서 같은 사유로 실패하는 것을 재지 않았다. 병합 판단에 쓰려면 master 스냅샷 재검의 lib 결과를 본다.

## 15. R3 — codex 2R(신규 한정 · 병합 차단 MED 3) 채택 3건 (TICKET=cysr-1110-seat-state-r3 · master#f30628ff)

검토 원문 = `~/axdev/master/reports/seat-state-1012/REVIEW-codex-2r.md`. 1R 세 건은 닫힘 3/3 확정. 신규 MED 3 = R2 가 새로 만든 회귀 2(실 프로세스 재현) + Windows 규약 1(순수 함수 재현 · 실좌석 영향은 추정).

### 15-1. 지적과 처방

| # | 지적(codex 재현) | R2 의 어디가 틀렸나 | R3 처방 |
|---|---|---|---|
| ① | 후보 `bash '/tmp/agent.sh'` × 관측 뿌리 `/bin/bash /tmp/agent.sh` → **R1 Occupied → R2 Empty** · 메타 좌석의 빈 셸 가드 false → true(실 bash) | 후보 cmd 를 공백으로만 나눠 따옴표가 엔트리에 남았다. 내가 한계로 적은 「공백 경로」 보다 넓었다 — 공백이 없어도 따옴표만 치면 걸린다 | 후보 기동 문자열을 **셸 낱말로 분해**한다(작은·큰따옴표를 벗김 · `\ ` = 공백). 저장소에 이미 있던 분해기 `cys::first_run_gates::split_shell_words` 를 그대로 쓴다(공개 표기 1낱말만 추가). 뿌리 쪽은 공백으로 이어 붙였다 다시 나누지 않고 **argv 그대로** 견준다(`argv_parts_snapshot` :5187) → 따옴표로 묶은 공백 경로도 한 낱말로 맞는다 |
| ② | 뿌리 `node --require /tmp/preload.js …/claude-code/cli.js` → 엔트리를 preload.js 로 오선택 → **R1 Occupied → R2 Empty**(실 node) · 역할 큐 `empty_seat` · 무메타면 승계 false → true | 「첫 비옵션 낱말 하나」 를 엔트리로 봤다. 값 받는 옵션의 값이 그 자리를 차지한다 | 둘 다: ⓐ 인터프리터별 **값 받는 옵션 표**(`interpreter_value_options` :3889)로 값을 건너뛴다 ⓑ 그 위에 **인터프리터 뿌리에 한해** 비옵션 낱말 **전부**를 엔트리 후보로 본다(`interpreter_operands` :3913) — 표가 모르는 옵션이 와도 진짜 엔트리를 놓치지 않는다. 인터프리터가 아닌 뿌리는 argv[0] 만(1R MED 유지) |
| ③ | 후보 `node C:\Agents\worker.js` × 뿌리 `node.exe c:\agents\worker.js` · 후보 `node tools\worker.js` × 뿌리 `node.exe C:\app\tools\worker.js` → **R1 Occupied → R2 Empty**(순수 함수) | 엔트리 비교가 대소문자를 가리고 상대 경로 꼬리에 `/` 만 썼다 | `entry_matches`(:3955): **어느 한쪽에 `\` 가 있거나 드라이브 글자 꼴(`C:`)이면** 양쪽의 구분자를 `/` 로 맞추고 소문자로 견준다. 그 밖(Unix)은 글자 그대로(`entry_matches_exact` :3967). 실행 파일의 `.exe` 접미는 기존 매처(`strip_win_exec_ext`)가 이미 벗긴다 — 재사용 |
| 보조 | 후보 칸은 `refresh_seat_cache` 의 함수 로컬 · 두 로더(`known_agent_candidates` · `known_agent_root_specs`)는 같은 합치기 함수를 쓰지만 **파일 읽기는 따로**라 팩을 고치는 순간에는 같은 스냅샷을 보장하지 않는다 | — | 변경 0(codex 도 그 경합의 장애를 재현하지 못했다). 팩 변경은 다음 틱의 지연 로드에서 반영되고 즉시 프로브는 매번 다시 읽는다 |

### 15-2. 값 받는 옵션 표(공백으로 띄운 꼴 · `--opt=값` 은 한 낱말이라 표가 필요 없다)

| 인터프리터 | 값을 받는 옵션 |
|---|---|
| node · nodejs · bun · deno | `-r` `--require` `--import` `--loader` `--experimental-loader` `--inspect-port` `-e` `--eval` `-p` `--print` `-C` `--conditions` `--env-file` |
| python* | `-W` `-X` `-c`(`-m 모듈` 은 값이 곧 엔트리라 표에 없다) |
| 셸(`is_shell_name`) | `-o` `+o` `--rcfile` `--init-file` · 단일 대시 묶음이 `o` 로 끝나면(`-eo pipefail`) 다음 낱말이 값 · 묶음에 `c` 가 있으면 뒤는 명령 문자열(낱말 0) |
| ruby / perl / php | `-e -r -I` / `-e -E -I` / `-r -c -d` |

표와 「비옵션 낱말 전부」 는 몫이 다르다: 전부 보기는 **엔트리를 놓치지 않는** 장치이고, 표는 **옵션 값에 든 이름**(`node --require /opt/pre/claude app.js`)을 엔트리로 세지 않는 장치다. 시험이 둘을 따로 고정한다(§15-4).

### 15-3. R3 로 바뀐 코드(R2 커밋 대비)

| 자리 | R2 | R3 |
|---|---|---|
| `root_cmd_is_agent`(:3991) 의 재료 | 공백으로 나눈 명령줄 문자열 · 엔트리 = 첫 비옵션 낱말 | argv 조각(`&[String]`) · 인터프리터 뿌리의 비옵션 낱말 전부 |
| `seat_verdict`(:3838) 넷째 인자 | `root_cmd: Option<&str>` | `root_argv: Option<&[String]>` |
| `seat_state_of`(:4030) · `agent_seat_vacant_now`(:4457) 의 뿌리 argv 읽기 | `argv_snapshot`(공백으로 이어 붙인 문자열) | `argv_parts_snapshot`(:5187 · 인자 경계 보존). `argv_snapshot`(:5179)은 그 위의 얇은 래퍼가 됐다(반환값 불변 · 다른 소비자 무접촉) |
| `agent_root_specs_from_json`(:5421) | cmd 를 공백으로 나눔 | `split_shell_words`(:5431) → 선두 env 대입을 건너뛴 뒤 `interpreter_operands` 의 첫째가 엔트리 |
| `exec_and_entry` | 있음 | 삭제(→ `interpreter_value_options` · `interpreter_operands`) |
| `entry_matches` | Unix 꼴만 | Windows 규약 분기 + `entry_matches_exact` |
| `src/first_run_gates.rs:166` `split_shell_words` | 비공개 | `pub`(한 낱말 · 본문 무수정 · lib 의 관문 판정과 같은 분해기를 쓴다) |

`root_agent_cmd`·`known_agent_cmd`·자손 쪽 매처·등록·데드맨은 R1·R2 그대로다.

### 15-4. R3 시험·뮤턴트·실연

- 새 시험 5건(이름 접두 `seat119r3_`):
  - `…quoted_candidate_entries_match_the_observed_argv` — codex ① 입력 그대로(`bash '/tmp/agent.sh'` · 큰따옴표 · 따옴표 없음 × argv `/bin/bash` `/tmp/agent.sh`) = 엔트리에 따옴표 없음 · Occupied · 빈 셸 가드 false / 공백 경로를 작은따옴표·큰따옴표·`\ ` 로 묶은 후보 × 인자 경계가 살아 있는 argv = 맞음 / **묶지 않은 공백 경로 후보 = 불일치(기대값 명시)** / 인자 경계가 사라진 argv 로는 묶은 후보와도 불일치 / env 대입·값 옵션 뒤의 따옴표 엔트리 · 따옴표로 묶은 Windows 경로(공백 포함)
  - `…interpreter_option_values_do_not_hide_the_entry` — codex ② 입력 그대로(`node --require /tmp/preload.js …/cli.js`) + `-r … --import …` · `--max-old-space-size=4096` · `--loader … --inspect-port 9229` = 맞음 / 인터프리터 후보(`python3 -m aider` · `python3 -X dev /srv/agent.py` · `bash -o pipefail /srv/run.sh`)도 맞음 / 비인터프리터 뿌리(`tail -f /tmp/claude` · `tail --require /tmp/x claude` 등) = 아님(1R MED 유지) / 맨 셸·`-c` 묶음 = 아님(1R HIGH 유지)
  - `…all_operands_catch_unknown_options_and_the_table_drops_option_values` — 표에 없는 값 옵션 뒤의 엔트리 = 맞음(전부 보기의 몫) / 표가 아는 옵션의 값에 든 에이전트 이름 = 아님(표의 몫)
  - `…windows_entries_ignore_separator_and_case_unix_entries_do_not` — codex ③ 입력 둘 = 맞음 · 구분자 섞임·대소문자 다름 = 맞음 · 다른 파일·다른 드라이브 = 아님 / **Unix 경로는 대소문자가 다르면 아님**(절대·상대 둘 다)
  - `…live_quoted_space_path_script_root_is_occupied`(unix · 실 프로세스) — 공백이 든 경로(`…/my agents/run a.sh`)의 스크립트를 실제로 돌리는 `/bin/sh` 뿌리: 따옴표로 묶은 후보 = Occupied · 묶지 않은 후보 = Empty
- **R2 시험에서 기대값이 뒤집힌 두 줄(정직 고지)**: `node /opt/app/server.js claude` · `python3 /opt/app/run.py --agent codex` 는 R2 에서 「아니다」 였고 R3 에서 「맞다」 다 — 인터프리터 뿌리의 비옵션 낱말 전부를 보기 때문이다(표가 모르는 옵션에서 엔트리를 놓치지 않으려는 안전 쪽 선택 · master 지시 ⓑ). 그 시험 줄을 지우지 않고 기대값과 까닭을 바꿔 남겼다. 옵션 꼴 낱말(`--claude`)과 이름이 다른 인자는 여전히 「아니다」.
- 나머지 R1·R2 시험은 문자열 명령줄을 argv 로 바꾸는 시험 도우미(`seat119_is_agent` · `seat119_verdict`)를 거치게 옮겼다(단언 목적 불변). 배선 핀 3줄은 새 문자열로 재표적.
- 뮤턴트 8/8 잡음(`mutants-r3.txt`):
  - Q1 후보를 공백으로만 나눔(= ① 되돌림) → 2건 적
  - Q2a 값 옵션 표 비움 → **의도한 갈림**: 엔트리 시험(`…do_not_hide_the_entry`)은 초록으로 남고(전부 보기가 받는다 = 그 장치의 존재 이유) 표의 몫을 재는 시험과 후보 엔트리 시험 2건만 적색
  - Q2b 표 비움 + 첫째 하나만(= ② 되돌림 = R2 거동) → 4건 적(엔트리 시험 포함)
  - Q2c 첫째 하나만(표 유지) → 2건 적
  - Q3 Windows 규약 끔(= ③ 되돌림) → 2건 적
  - Q4 뿌리 argv 의 인자 경계를 버림 → 2건 적(첫 실행은 내 뮤턴트 문장의 형 표기 누락으로 컴파일 실패 → 고쳐 단독 재실행)
  - S1 셸 후보 매칭 허용(1R HIGH 되돌림 재확인) → 6건 적 · S2 임의 낱말 매칭 허용(1R MED 되돌림 재확인) → 5건 적
- 격리 실데몬 2런(R3 최종 빌드): 이 맥 팩 꼴 = 뿌리 claude 좌석 occupied×3 · 큐 배달 · 맨 셸 좌석 empty×3 / 이 맥 팩 꼴 + 셸 후보 2 = 맨 `/bin/zsh -l` 좌석 empty×3 · 뿌리 claude 좌석 occupied×3 · 큐 배달. codex 2R 의 세 입력(따옴표 후보 · `--require` · Windows 경로)을 실데몬으로 돌린 런은 **없다** — 순수 함수와 실 프로세스 시험으로 쟀다.

### 15-5. 실 후보 꼴 표(§14-4)는 R3 에서도 그대로 선다
이 맥 팩·내장 팩의 후보는 따옴표·값 옵션·Windows 경로를 쓰지 않는다. §14-4 의 기동 꼴(실측 2 · 파일 종류로 본 꼴 1 · 추정 1 · 미설치 1)은 R3 시험에서도 전부 Occupied 다(`seat119r2_root_matches_by_position_not_by_any_argument_word` 가 같은 13꼴을 R3 규칙으로 잰다).

### 15-6. R3 뒤에 남는 한계 (→ R4 갱신: 2·4 는 뒤집혔고 6 은 닫혔다. 최종 목록 = §16-6)
1. **묶지 않은** 공백 경로 후보(`bash /opt/my agents/run.sh`)는 맞지 않는다 — 셸도 그 문자열을 두 낱말로 읽는다(기대값을 시험에 명시). 따옴표나 `\ ` 로 묶으면 맞는다.
2. 인터프리터 뿌리는 비옵션 낱말 전부를 보므로, **스크립트 인자에 에이전트 이름이 든** 인터프리터 프로세스(`node /opt/app/server.js claude`)는 에이전트로 읽힌다(Occupied = 보호 방향 · R3 에서 넓어진 자리). 인터프리터가 아닌 뿌리는 해당 없다.
3. 인터프리터의 엔트리 이름이 에이전트 이름과 같은 다른 스크립트(`python3 /tmp/claude`)는 에이전트로 읽힌다(R2 와 같음 · shebang 기동 꼴과 구별 불가).
4. 표가 아는 옵션의 값만 건너뛴다. 표에 없는 값 옵션의 **값**에 에이전트 이름이 들면 에이전트로 읽힌다(2 와 같은 방향).
5. 분해기는 `\ ` 만 이스케이프로 읽고 그 밖의 `\` 는 글자 그대로 둔다(Windows 경로 보존 — lib 관문 판정과 같은 선택). 그래서 `\"` · `\\` 같은 POSIX 이스케이프는 해석하지 않는다.
6. Windows 규약은 **어느 한쪽**이 Windows 꼴이면 켜진다. 경로에 `\` 글자가 실제로 든 Unix 파일 이름은 대소문자 무시로 견주게 된다(드문 꼴).
7. Windows 네이티브 좌석의 실제 뿌리 꼴과 큐·승계 영향은 여전히 재지 않았다(codex 도 추정). `/usr/bin/env node …` 를 cmd 로 적은 후보는 exec 뒤 `node …` 가 되어 맞지 않는다 — R1 부터 같다(codex 가 신규에서 제외).
8. 프레임워크 Python 처럼 argv[0] 이 바뀌는 인터프리터는 ⓑ 후보와 맞지 않는다(R2 와 같음).

### 15-7. R3 게이트 수치(격리 HOME · 좌석 `CYS_*` env 제거)

| 게이트 | 결과 |
|---|---|
| `cargo test --bin cysd -- seat119 v113_ seat_agent_observed select_observed`(해당 묶음) | 20 passed / 0 failed(R1 12 + R2 3 + R3 5) |
| `cargo test --bin cysd`(전체 · R3 최종 소스 · 19:29~19:36) | **2612 passed / 0 failed / 8 ignored** · 407.78s(R2 2607 + 5) |
| `cargo test --lib`(전체 · 19:36~19:42 · 이번에는 lib 소스가 1낱말 바뀌었다 = `split_shell_words` 공개) | **1077 passed / 0 failed** / 2 ignored · 327.00s — 1회로 초록(R2 1차에 흔들린 벽시계 시험도 통과) |
| `cargo clippy --bin cysd --tests --message-format=short` | rc 0 · error 0 · 파일 위치가 있는 경고 355줄(R1·R2 와 같은 수) 가운데 **기준 bb52b846 대비 바꾼 줄 범위 안 = 0**(governance.rs 30개 범위 · first_run_gates.rs 1개 범위) |
| `bash scripts/secret-scan.sh --all`(스테이징 상태) | clean(1699 파일) |
| `test_pyseal_census.py` | `PYSEAL-CENSUS-OK` |
| 뮤턴트 | 8 / 8 잡음(Q2a 는 의도한 갈림 · §15-4) |
| ui · 팩 · `scripts/tests/test_update_publish.py` | R3 변경 0(다시 돌리지 않음) |

## 16. R4 — codex 3R(신규 한정 · 마지막 이종 라운드) 채택 3건 (TICKET=cysr-1110-seat-state-r4 · master#175bc660)

검토 원문 = `~/axdev/master/reports/seat-state-1012/REVIEW-codex-3r.md`. 2R 세 건은 닫힘 3/3 확정. 신규 MED 3(전부 실 프로세스 재현). 이종 검토는 3R 로 상한 — R4 는 master 독립 재검 + 코드 정독으로 닫는다.

### 16-1. 지적과 처방

| # | 지적(codex 재현) | 어디가 틀렸나 | R4 처방 |
|---|---|---|---|
| ① | 뿌리 `python3 /tmp/backup.py --target claude` · `node /tmp/server.js --name claude`(생존 · 자손 0)가 **R2 Empty → R3 Occupied** · 무메타 승계 true → false = 1R MED 의 인터프리터 뿌리 재발 | R3 의 「인터프리터 뿌리는 비옵션 낱말 전부를 본다」(master 지시 ②ⓑ · master 가 오판으로 판정). 내가 「보호 방향」 이라 적은 것이 승계 계약에서는 복구 차단이다 | 철회 — 값 받는 옵션의 값을 건너뛴 **엔트리(첫 비옵션 낱말 하나 · `-m 모듈` 포함)만** 본다(`interpreter_entry` :3918). 스크립트 인자는 보지 않는다. R3 가 뒤집은 기대값 2줄은 「아니다」 로 되돌렸다 |
| ② | 후보 `bash /tmp/review/Agents/run.sh` × 실제 뿌리 argv `["/bin/bash", "/tmp/review/agents\run.sh"]`(다른 파일) → **Occupied** · 빈 셸 가드 true → false | R3 는 Windows 규약을 문자열 내용(`\` · 드라이브 글자)으로 켰다. Unix 파일 이름 안의 `\` 는 글자다 | 관측 플랫폼으로 켠다 — `entry_matches_on(windows, …)`(:3959) · 운영 값은 `root_cmd_is_agent`(:3989) 가 넘기는 `cfg!(windows)`. Unix 는 글자 그대로. 시험은 `root_cmd_is_agent_on`(:3994)으로 두 플랫폼의 입력을 한 기계에서 고정 |
| ③ | `python3 -W "" /tmp/review/worker` 가 프로세스 표에서 `[Python, -W, /tmp/review/worker]` 로 보인다(sysinfo 0.33.1 이 macOS·Linux 에서 **빈 인자를 버림**) → 엔트리를 `-W` 의 값으로 삼켜 **R2 Occupied → R3 Empty** · 무메타 승계 false → true | R3 가 값 받는 옵션 표를 들이면서, 재료(argv)가 빈 인자를 잃을 수 있다는 것을 보지 않았다 | 최소 가드: 값 자리의 낱말이 **어느 후보의 엔트리이고 그 뒤에 비옵션 낱말이 더 없으면** 값으로 삼키지 않고 엔트리로 본다. 뒤에 비옵션 낱말이 있으면 가드는 서지 않는다(`node --require /opt/pre/claude /opt/app/server.js` 는 여전히 Empty). 근본 수리는 별도 후보 **B-2**(§16-6) |

### 16-2. 뿌리 존재 판정 — 최종 규칙(R4 · `root_cmd_is_agent_on` :3994)

1. 재료 = 뿌리의 argv 그대로(인자 경계 보존 · `argv_parts_snapshot`).
2. 엔트리 = argv[0] 이 셸·인터프리터일 때만 있다: 값 받는 옵션(§15-2 표)의 값을 건너뛴 **첫 비옵션 낱말 하나**. 셸의 `-c` 묶음이 있으면 없다. 빈 인자 유실 가드(§16-1 ③) 한 가지 예외.
3. 후보 실행 파일이 셸·인터프리터가 **아니면**: argv[0] 이 그 실행 파일이거나 엔트리가 그 실행 파일(낱말 규칙 = 기존 엄격 매처의 낱말 판정).
4. 후보 실행 파일이 셸·인터프리터면: argv[0] 이 그 인터프리터이고 엔트리가 후보의 엔트리와 같을 때만(엔트리 없는 후보는 무엇과도 불일치).
5. 엔트리 경로 비교 = `~/…` 는 홈 뒤 꼬리 · 절대 경로는 그대로 · 상대 경로·모듈은 같거나 꼬리가 같음. Windows 에서만 구분자 통일 + 대소문자 무시.
6. 후보가 여럿 맞아도 참(존재 판정). 인터프리터가 아닌 뿌리는 argv[0] 만 본다.

### 16-3. R4 로 바뀐 코드(R3 커밋 대비 · `governance.rs` 1파일)

| 자리 | R3 | R4 |
|---|---|---|
| 엔트리 추출 | `interpreter_operands` — 비옵션 낱말 전부 | `interpreter_entry`(:3918) — 첫 비옵션 낱말 하나 + 빈 인자 유실 가드(후보 판정 클로저를 받는다) |
| `root_cmd_is_agent` | 인터프리터 뿌리의 낱말 「전부 중 하나」 | `root_cmd_is_agent_on(cfg!(windows), …)` 래퍼(:3989) · 본체(:3994)는 엔트리 하나만 견준다 |
| 엔트리 비교 | `entry_matches` — 내용이 Windows 꼴이면 정규화 | `entry_matches_on(windows, …)`(:3959) — 플랫폼 인자로만 |
| `agent_root_specs_from_json` 의 후보 엔트리 | `interpreter_operands(…).first()` | `interpreter_entry(…, 후보 판정 없음)` — 결과 같음 |

`seat_verdict` · `seat_state_of` · 빈 셸 가드 · `argv_parts_snapshot` · `split_shell_words` 재사용 · 값 받는 옵션 표 · `root_agent_cmd` · 자손 쪽 = R3 그대로.

### 16-4. R4 시험·뮤턴트·실연

- 새 시험 3건(`seat119r4_`): `…only_the_entry_counts_script_arguments_do_not`(codex ① 입력 그대로 2 + tsx 래퍼 꼴 등 5꼴 = Empty · 승계 가능 / 표가 아는 옵션의 값 = 엔트리 아님 3꼴 / **표에 없는 값 옵션 뒤의 엔트리는 놓친다 = 기대값 명시** / `--opt=값` 한 낱말이면 맞음) · `…windows_entry_rules_follow_the_platform_not_the_string`(Windows 모드: codex 2R 입력 둘 + 구분자·대소문자 변형 = 맞음 · 다른 파일·드라이브 = 아님 / Unix 모드: codex 3R 입력 그대로 = 불일치 · 같은 입력이 Windows 모드에서는 맞음(대조) · 대소문자 다르면 아님 · Windows 꼴 문자열도 글자가 다르면 아님 / 운영 래퍼 = 빌드 플랫폼) · `…lost_empty_option_value_does_not_swallow_the_entry`(codex ③ 입력 그대로 `[Python, -W, /tmp/review/worker]` = Occupied · 빈 인자가 보존된 argv 도 같은 답 · 뒤가 옵션 꼴뿐이어도 가드 · 인터프리터 후보도 같은 가드 / 음성: 값 뒤에 비옵션 낱말이 있으면 값 = `node --require /opt/pre/claude /opt/app/server.js` Empty · 값이 후보 엔트리가 아니면 값).
- 바뀐 기존 시험: R3 가 뒤집었던 두 줄(`node /opt/app/server.js claude` · `python3 /opt/app/run.py --agent codex`)을 「아니다」 로 원복 · R3 의 「전부 보기/표 분리」 시험과 Windows 시험은 위 R4 시험 둘로 교체 · R3 따옴표 시험의 Windows 경로 줄은 플랫폼을 명시(`_on(true)` 맞음 · `_on(false)` 아님). Windows CI 에서도 같은 기대값이 서도록 플랫폼에 달린 단언은 전부 `_on` 으로 부른다.
- 뮤턴트 5/5 잡음(`mutants-r4.txt`): **T1 인터프리터 뿌리가 비옵션 낱말 전부를 봄(= R3 ⓑ 복귀)** → 5건 적 · **T2 Windows 규약을 문자열 내용으로 켬(= R3 판별 복귀)** → 2건 적 · **T3 빈 인자 유실 가드 제거** → 1건 적 · T4 값 받는 옵션 표 비움 → 4건 적(R3 때는 엔트리 시험이 초록으로 남았으나 이제는 `seat119r3_interpreter_option_values_do_not_hide_the_entry` 도 적색 — 표가 유일한 방어) · T5 가드가 뒤따르는 비옵션 낱말을 안 봄 → 2건 적(`node --require /opt/pre/claude /opt/app/server.js` 가 Occupied 가 되는 것을 잡는다).
- 격리 실데몬 2런(R4 최종 빌드): 이 맥 팩 꼴 = 뿌리 claude 좌석 occupied×3 · 큐 배달 · 맨 셸 좌석 empty×3 / 이 맥 팩 꼴 + 셸 후보 2 = 맨 `/bin/zsh -l` 좌석 empty×3 · 뿌리 claude 좌석 occupied×3 · 큐 배달. codex 3R 의 세 입력을 실데몬으로 돌린 런은 없다(순수 함수 시험으로 쟀다 — 3R 입력의 실 프로세스판 시험도 이번에는 넣지 않았다).

### 16-5. codex 3R 의 나머지 확인(변경 0 · 기록)
- 분해기: JSON 디코딩 뒤 `node "C:\Program Files\x\a.js"` 는 두 낱말로 옳게 나뉜다. `\"`·`\\` 미해석은 R2 에서도 불일치라 신규로 세지 않았다. `pub` 외 본문 변경 없음 = 기존 호출자 거동 불변.
- argv: macOS·Linux 는 빈 인자를 보존하지 않는다(위 ③). Windows 는 `CommandLineToArgvW` 분해 — 네이티브 미검증. macOS 에서 70,000자 인자는 그대로 보존됐다.
- 도구 뿌리: argv[0] 이 글자 그대로 `npx`·`tsx`·`uv`·`poetry` 면 인터프리터 분기에 들어가지 않는다(argv[0] 만 본다). 각 도구의 실기동 꼴은 미측정.

### 16-6. 남는 한계 — 최종 목록(R4 뒤)
1. **B-2 후보(별도 티켓)**: 빈 인자 유실은 sysinfo 0.33.1 상류의 거동이다(macOS `process.rs:602` · Linux `process.rs:839` — codex 판독). 이번 가드는 「값 자리 낱말이 후보 엔트리 ∧ 뒤에 비옵션 낱말 없음」 한 꼴만 구한다. 스크립트 인자가 뒤따르는 꼴(`python3 -W "" worker job1`)은 여전히 엔트리를 값으로 삼킨다(Empty). 근본 수리 = argv 를 직접 읽는다(macOS `KERN_PROCARGS2` · Linux `/proc/<pid>/cmdline`) — 빈 인자까지 보존.
2. 표에 **없는** 값 받는 옵션이 오면 그 값을 엔트리로 고른다 → 진짜 엔트리를 놓친다(Empty = 큐 보류 쪽). 시험에 기대값을 명시했다. 표를 넓히는 것이 유일한 수리다(R3 의 「전부 보기」 는 ①로 철회).
3. 인터프리터의 엔트리 이름이 에이전트와 같은 다른 스크립트(`python3 /tmp/claude`)는 에이전트로 읽힌다(shebang 기동 꼴과 구별 불가).
4. 묶지 않은 공백 경로 후보는 맞지 않는다(셸도 두 낱말로 읽는다). 분해기는 `\ ` 만 이스케이프로 읽는다(`\"`·`\\` 미해석).
5. Windows 네이티브 좌석의 실제 뿌리 꼴과 큐·승계 영향은 재지 않았다. Windows 규약은 빌드 플랫폼으로 켜지므로 Windows 에서 대소문자·구분자만 다른 **다른 파일**은 같은 것으로 읽힌다(그 플랫폼의 파일 시스템 규약과 같다).
6. `/usr/bin/env node …` 를 cmd 로 적은 후보는 exec 뒤 `node …` 가 되어 맞지 않는다(R1 부터 같음). argv[0] 이 바뀌는 인터프리터(프레임워크 Python)는 인터프리터 **후보**와 맞지 않는다 — 다만 비인터프리터 후보(`worker`)는 엔트리로 맞는다(위 ③ 시험의 `Python` 꼴).
7. B 후보(자손 쪽 `seat_agent_observed` 의 같은 꼴 · §8-1)는 그대로 남아 있다.

### 16-7. R4 게이트 수치(격리 HOME · 좌석 `CYS_*` env 제거)

| 게이트 | 결과 |
|---|---|
| `cargo test --bin cysd -- seat119 v113_ seat_agent_observed select_observed`(해당 묶음) | 21 passed / 0 failed(전체 실행 출력에서 센 수 · seat119 14 = R1 4 + R2 3 + R3 4 + R4 3) |
| `cargo test --bin cysd`(전체 · R4 최종 소스 · 20:02~20:10) | **2613 passed / 0 failed / 8 ignored** · 415.41s(R3 2612 − 교체 2 + 새 3) |
| `cargo test --lib`(전체 · 20:10~20:15) | **1077 passed / 0 failed** / 2 ignored · 301.60s |
| `cargo clippy --bin cysd --tests --message-format=short` | rc 0 · error 0 · 파일 위치가 있는 경고 355줄(R1~R3 과 같은 수) 가운데 **기준 bb52b846 대비 바꾼 줄 범위 안 = 0**(governance.rs 30개 범위 · first_run_gates.rs 1개 범위) |
| `bash scripts/secret-scan.sh --all`(스테이징 상태) | clean(1701 파일) |
| `test_pyseal_census.py` | `PYSEAL-CENSUS-OK` |
| 뮤턴트 | 5 / 5 잡음 |
| ui · 팩 · lib 소스 · `scripts/tests/test_update_publish.py` | R4 변경 0 |
