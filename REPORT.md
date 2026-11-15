# REPORT — 긴 큐 배달이 `[Pasted text]` 로 접혀 제출되지 않음 → 큐 막힘·6시간 뒤 유실

TICKET=cysr-queued-paste-submit · 작업 가지 `fix/cysr-queued-paste-submit`(worktree `~/axdev/.wt/cys-queued-paste`) · 작성 worker-2 · 2026-11-09

> ⚠ **기반 판단(지시 없이 내린 판단 1건)**: 브리프의 기반 커밋 `61d30826`(0.14.37 줄)은 cysr 1.1.14 를 **포함하지 않는다**
> (`git merge-base --is-ancestor 270e3e21 61d30826` = 아님). 결함 보고의 데몬 build_id `270e3e21e492` = `origin/main` 이고,
> 문제의 판정 어휘(`human_draft`·`remedy`)는 `origin/main` 에만 있다. 그래서 worktree 를 **`origin/main`(270e3e21 · Cargo 1.1.14)** 에서
> 다시 만들었다. 다음 cysr 판 편입 기준선과 같다.

## 1. 한눈에

| 항목 | 결과 |
|---|---|
| 맥 실 Claude Code(2.1.319) 재현 | **재현 안 됨** — 아래 표 14조건 전부 제출(대기·바쁨·69/200줄·8.9KB·배경 QoS·0ms 간격·30턴 이력) |
| 결함 모양 재현(모형) | **재현됨** — 붙여넣기 처리 900ms 중 Return 을 먹는 모형 좌석에서 설치본 1.1.14 가 현장과 같은 신호(미제출 · `input_pending` · `remedy=human_draft` · `queue.starved` · 뒤 항목 정지) |
| 원인 — 확정(코드 사실) | 큐 인계 = 본문 → 400ms → Return **1회**, 제출 확인·재시도 **없음**, 인계 순간 미제출 계수 0 → 잔여가 처방 3행 `human_draft` 로 읽힘 |
| 원인 — 후보(가장 유력) | 받는 Claude Code 의 붙여넣기 처리 지연(긴 다이제스트·긴 세션·느린 윈도)이 400ms 를 넘어 Return 이 빈 줄을 누름(벤더 #28137 과 같은 모양) — 윈 실기 확인 필요 |
| 수리 ⓐ | 큐 Return 을 쓴 뒤 **제출 확인 기록** → 입력줄이 그 본문 그대로면 Return 재전송(간격 2/4/8초 · 상한 3) → 그래도면 경보 1건 후 종전 동작 |
| 수리 ⓑ | 처방 3′행: 화면 글이 데몬의 마지막 배달 본문이면 `machine_residue`(사람 초안 아님) · 오너 초안(실례 ③)은 `human_draft` 그대로 |
| 수리 ⓒ | GUI: `queue.expired`(종전 화면 0) → 좌석당 1.5초 묶어 토스트 + OS 배너 1줄 |
| 시험 | Rust 신규 14 녹색 · 뮤테이션 3회 적색 확인 · UI 342 녹색 · 격리 데몬 A/B e2e(최종판 3런 + 1차 4런) · 전체 cysd 3240/3241(1 = 기존 결함) |
| 검증 편성 | codex 1R REVISE(5) → 2R REVISE(3) → 3R REVISE(시험 2) → **4R ACCEPT**(미달 0) = §7 |

## 2. 재현 (할 일 1)

### 2-1. 맥 · 실 Claude Code 2.1.319 · 격리 데몬(설치본 cysr 1.1.14 · 자기 소켓)

하네스: 스크래치 `repro/repro.py`(격리 데몬 + 실 claude 좌석 · 훅 끔) · `repro/race.py`·`race2.py`·`race3.py`(cys 없이 PTY 로 직접). 판정원 = **세션 jsonl 의 `type:user` 레코드**(화면 아님).

| # | 경로 | 좌석 상태 | 본문 | 조건 | 제출 | 비고 |
|---|---|---|---|---|---|---|
| 1 | cys `--queued` | 대기 | 1줄 61자 | 대조군 | ✅ 5.5s | 접힘 없음 |
| 2 | cys `--queued` | 대기 | 3줄 119자 | | ✅ 3.0s | 접힘 없음 |
| 3 | cys `--queued` | 대기 | 10줄 359자 | | ✅ 1.2s | 접힘 보임 |
| 4 | cys `--queued` | 대기 | 69줄 2,365자 | 현장 줄 수 | ✅ 4.7s | 접힘 보임 |
| 5 | cys `--queued` | 바쁨(생각 중 · esc to interrupt) | 69줄 | 로그인 좌석 | ✅ 6.7s | |
| 6 | cys `--queued` | 대기 · `taskpolicy -b`(배경 QoS) | 69줄 | 느린 좌석 흉내 | ✅ 4.7s | |
| 7 | cys `--queued` | 대기 · 배경 QoS | 200줄 8,911자 | | ✅ 7.3s | |
| 8 | cys `--queued` | 직후(도구 차단) · 배경 QoS | 69줄 | | ✅ 4.6s | |
| 9 | PTY 직접 · 괄호 붙여넣기 | 대기 | 69줄 6.4KB | 붙여넣기→CR **0ms** | ✅ | |
| 10 | 〃 | 대기 | 〃 | 20/60/150/400ms | ✅×4 | |
| 11 | PTY 직접 · **괄호 없음** | 대기 | 69줄 | 붙여넣기→CR **0ms** | ❌ → 두 번째 Return 에 ✅ | **CR 이 붙여넣기 덩이에 흡수** |
| 12 | 〃 | 대기 | 〃 | 20/60/150/400ms | ✅×4 | |
| 13 | PTY 직접 · 괄호 | 이력 30턴(기록 수 MB) | 69줄 | 400ms(큐와 같은 간격) | ✅×6 | 자리표시 그림 지연 7~27ms(늘지 않음) |
| 14 | 위 1~8 | — | — | — | — | 원장 「여러 행」 = 큐 다이제스트 병합(아래 2-3) |

결론: **맥에서는 현장 증상이 재현되지 않는다.** 단 11번이 보여 주듯, Return 이 붙여넣기 처리보다 먼저(같은 덩이로) 닿으면 Claude Code 는 그 Return 을 제출로 쓰지 않고, 사람이 Return 을 한 번 더 누르면 제출된다 — 현장 증상(「사람 Enter 로 풀림」)과 같은 모양이다.

### 2-2. 결함 모양 모형(swallow_tui) · 격리 데몬 A/B — `docs/queued_paste_e2e/`

모형 좌석 `swallow_tui.py`: 괄호 붙여넣기를 받으면 900ms 동안 처리 중이고 그 사이 Return 은 빈 줄 Enter(무동작), 처리 뒤 입력줄에 `[Pasted text #k +n lines]`. 근거 = 벤더 이슈 #28137 원문(아래 §3-2). 시나리오 = 69줄 항목 A + 1줄 항목 B 를 연달아 `--queued` · 기아 경보 임계 20초 · 45~90초 관측.

| 런 | 데몬 | Return 먹힘 | A 제출 | B 제출 | 큐 막힘 사유 / 처방 | 이벤트 |
|---|---|---|---|---|---|---|
| ① | **설치본 1.1.14**(270e3e21e492.20261106T0719Z) | 1 | ❌ | ❌ | `input_pending` / **`human_draft`** | delivered · starved(remedy=human_draft) |
| ② | 수리판 · `CYS_QUEUED_SUBMIT_RETRY=0` | 1 | ❌ | ❌ | `input_pending` / **`machine_residue`** | delivered · starved(remedy=machine_residue) |
| ③ | **수리판 기본** | 1 | ✅ | ✅ | (막힘 없음 · depth 0) | delivered · **submit_retried(try 1)** · **submit_recovered(basis=line_empty)** · delivered(B) |
| ④ | 수리판 기본 · 모형이 **모든** Return 을 먹음 | 4(원 1 + 재시도 3) | ❌ | ❌ | `input_pending` / `machine_residue` | submit_retried ×3(try 1·2·3) · starved · **submit_unconfirmed ×1(tries=3)** · 그 뒤 90초까지 쓰기 0 |

**최종판(7be38f56 빌드) 재실행**: 기본 = A 7.7초·B 13.3초 제출(재시도 1 · recovered line_empty) · 노브 0 = 막힘(`machine_residue`) · 모두 먹음 = 먹힘 4 · retried 3 · unconfirmed 1(런 `ab/run-210020`·`run-210127`·`run-210232`).

①이 현장 신호를 그대로 낸다(dept-1 11-09 09:47: 미제출 · `queue.starved … blocked_by=input_pending` · 뒤 지시 정지). 런 산출물: 스크래치 `ab/run-203150`(①) · `run-203303`(②) · `run-203426`(③) · `run-203555`(④).

### 2-3. 원장 「여러 행」의 뜻

큐는 같은 좌석으로 가는 연속 항목을 **한 다이제스트 본문으로 병합**해 한 번에 붙여넣는다(`governance.rs` `deliver_head_locked` 안 `plan_queue_merge` · `render_queue_digest` · 이벤트 `digest_parts[]`·`merged_ids`). 62→61 보고 여러 건이 **한 덩이 붙여넣기 + Return 1회**로 나갔다는 뜻이다 → 실제 붙여넣기는 단건보다 크다(처리 지연 쪽으로 불리).

## 3. 원인 (할 일 2) — 확정과 후보를 나눈다

### 3-1. 확정(우리 코드 · 줄 번호는 `origin/main` 270e3e21 기준)

1. **Return 1회 · 확인 없음**: 큐 인계는 `crate::agent_write::Plan::paste(&d.body).with_submit(400, 0)` — 본문 → 400ms → Return 한 번(`governance.rs:12665` · 수정 후 줄 이동). 결판(`settle_queue_write` · `T::WrittenSubmitted`)은 **Return 을 썼다는 사실**로 `queue.delivered` 를 내고 끝난다 — 받는 TUI 가 제출했는지 보지 않는다. 재시도 장치는 **보류한(쓰지 않은) Return** 용(`resubmit_withheld_one`)뿐이고, **쓴 뒤 먹힌 Return** 용은 없었다.
2. **계수 0 → 사람 초안 오판**: 인계 직전 `s.set_pending_input(0)`(`governance.rs:12620` 부근) — 줄이 제출됐다고 계상한다. Return 이 먹혀 화면에 본문이 남으면 처방 표가 3행(`입력줄 ∧ c == 0 ∧ dv == Some(true)` → `human_draft`, `queue_remedy`)으로 떨어진다. 화면 글이 데몬 자신의 마지막 배달 본문이라는 기록(`InjectTrack::last_body` · `MachineBody`)과 접힘 자리표시까지 맞추는 대조기(`composer_block_is_machine_body`)가 **이미 있었지만** 처방 3행은 그것을 보지 않았다.
3. **만료가 화면 0**: `queue.expired` 는 항목당 1회 발행되고(`queue_expiry_pass`) 같은 데몬 `surface:N` 발신자에게만 통지 항목을 넣는다. GUI 는 이 이벤트를 막힘 토스트 기억 정리에만 썼다(`ui/src/main.ts` `forgetStarvedHead`) — 오너 알림 0. 경보 라우팅(`alert_route::routable`)에도 없다.

이 셋은 **TUI 가 왜 Return 을 먹었는지와 무관하게** 현장 증상(막힘 · 사람 Enter 로만 풀림 · 6시간 뒤 조용한 소멸)을 만든다. 수리는 이 셋을 겨눈다.

### 3-2. 후보 — TUI 가 Return 을 먹는 이유(대조군 뒤 이름 · 확정 아님)

- **가장 유력: 붙여넣기 처리 지연 > 400ms.** 벤더 이슈 [anthropics/claude-code#28137](https://github.com/anthropics/claude-code/issues/28137)(2026-02-24 · CLOSED) 원문: 붙여넣기 처리에 지연이 있고 그 사이 Enter 가 오면 "the message is sent **without** the pasted content … The pasted text then appears in the input field **after** the message has already been sent", "Gets worse in longer sessions"(관련 #22650 세션 이력과 함께 느려지는 붙여넣기 · #21152 큰 붙여넣기 지연). 현장 61 좌석은 긴 master 세션 · 병합 다이제스트 · 윈 ConPTY 경로다. 맥에서 이력 30턴으로는 지연이 늘지 않았다(표 13) — 현장 크기(수 시간짜리 master 세션)와 윈 조건은 재현하지 못했다.
- 보조 근거: 맥 표 11(괄호 없는 붙여넣기에 같은 덩이로 붙은 Return 은 흡수 · 두 번째 Return 에 제출) · 벤더 [#91205](https://github.com/anthropics/claude-code/issues/91205)(2026-09-01 · CLOSED · 2.1.252 — "bracketed-paste block … followed by a plain key in the same stdin chunk … drops the pasted text" · 느린 링크에서 뒤 키가 같은 덩이로 합쳐질 때만 · 우리 맥 2.1.319 0ms 시험(표 9)은 재현 안 됨 = 이후 판에서 고쳐졌을 수 있음).
- 같은 계열 기지 사실: 부트 경로(`javis_awaken.py` 머리말 D6)는 윈 1.1.8 실측 "지침 2회 311·312초 멈춤 — 사람 Return 1회로 풀림"을 겪고 jsonl 확인 + Return 재시도를 넣었다 — 이번 큐 경로에 없던 것이 그것이다.
- **윈 실기로 확정할 것**: §8 표.

## 4. 수리 (할 일 3)

### ⓐ 먹힌 큐 Return 의 제출 확인 · 상한 있는 재시도

- 기록: `state.rs` `SubmitCheck`(본문 기록 시각 · 세운 시각 · 마지막 Return 시각 · 재시도 수 · 발신 · 항목 id · 대조 열쇠 · 세션 기록 경로와 그때 길이 · 에이전트/대화 세대) — `InjectTrack::submit_check`(leaf 락).
- 세움: `settle_queue_write` 의 `T::WrittenSubmitted` 끝(`arm_queue_submit_check`) — Return 을 **쓴** 큐 배달마다 1건(덮어쓰기). 노브 `CYS_QUEUED_SUBMIT_RETRY=0` 이면 세우지 않는다(즉시 종전).
- 확인: watchdog 틱(`resubmit_withheld_submits` 다음 · `deliver_queued` 앞) `recheck_queue_submits` → 좌석마다 순수 판정표 `submit_check_step`(14행 · 첫 일치):
  - 닫음(쓰기 0): 사람 손(사람 바이트 ∨ 본문 뒤 사람 입력) · 새 기계 본문 · 에이전트/대화 세대 바뀜(= 같은 pid·같은 대화만) · **세션 기록에 그 본문의 user 레코드**(판정원 = 기록 · 화면 아님) · 입력줄 빈 줄 ∧ 나이 ≥ 6초 · 입력줄이 남의 것 ∧ 나이 ≥ 600초.
  - 재전송: 입력줄 = **그 본문**(`submit_cr_verdict(..).own` — 접힘 자리표시 포함) ∧ 간격(2·4·8초) 충족 ∧ 창 없음(질문·선택 창 ∨ 승인 대기) ∧ 큐와 같은 프롬프트 경계 통과(그 블록을 빈 프롬프트로 본 화면 · 바쁨 표지 근처면 대기). 쓰기는 보류 재제출과 **같은 길**(`input_gate` 안 재확인 → `WriteReq::SubmitAfterGap` · 쓰기 직전 보류 탐침 `submit_cr_withhold_probe` — 그 사이 창이 뜨면 쓰지 않는다).
  - 포기: 재시도 3회 뒤 8초에도 그대로 ∨ 나이 600초 → `queue.submit_unconfirmed` **1건** 후 기록 닫음 → 종전 동작(입력줄 점유 보류 + 기아 경보 · 처방은 ⓑ 로 `machine_residue`).
  - 회복: 재시도 뒤 입력줄이 비거나 기록이 제출을 말하면 `queue.submit_recovered` 1건(재시도 0 이면 조용히 닫음 — 정상 배달은 이벤트 0).
- 세션 기록 대조: `Surface::registered_transcript`(사용량 등록이 알려 준 경로)의 **Return 을 쓴 순간 길이 뒤**에 붙은 `type:user` 레코드 중 본문 머리 48자(공백 제거)를 품은 것. 읽기는 재전송 직전에만(IO 최소) · 상한 8MB · 파일 없음/짧아짐 = 모름(화면 양성으로만 판단).

### ⓑ 처방 3′행 — 기계 잔여를 사람 초안과 가른다

- `QueueBlockDiag::composer_machine_body`(추가형 · `screen_diag` JSON 키 `composer_machine_body`): 커서가 든 입력 블록이 마지막 기계 본문으로 **완전히** 설명되고(접힘 자리표시 포함) 사람 바이트 0 · 본문 뒤 사람 입력 없음.
- `queue_remedy` 3′행: `입력줄 ∧ c == 0 ∧ dv == Some(true) ∧ composer_machine_body == Some(true)` → `machine_residue`("기계가 배달한 본문이 입력줄에 제출되지 않은 채 남았다(Return 이 먹힘 — cys 가 Return 을 최대 3회 다시 보낸다). 그래도 남아 있으면 사람이 …"). `Some(false)`·`None` 은 종전 3행 `human_draft`(실례 ③ 오너 초안 보존). code 어휘(14종 허용 목록)·게이트 판정은 불변 — **안내만** 바뀐다.

### ⓒ 만료(유실) 알림

- `ui/src/queueexpirednotice.ts`(순수): 알릴 만료인지(만료 통지 항목 자신은 제외 — 통지의 통지 연쇄 금지 · payload 타입 검사) · 문구("전달하지 못한 메시지 N건이 시간이 지나 대기열에서 빠졌습니다" / "<역할>(<좌석>) 창이 그동안 입력을 받지 못했습니다. 내용은 보관돼 있어 'cys queue list --expired' 로 볼 수 있습니다").
- `ui/src/main.ts` `noteQueueExpired`: (소켓, 좌석)마다 1.5초 묶음 → 데몬 출처 래퍼 `daemonToast` + `daemonOsBanner`(경보 숨김 스위치를 따른다).
- 보낸 쪽: 같은 데몬의 `surface:N` 발신자에게는 **종전부터** 만료 통지 항목이 간다(`queue_expiry_pass` → `render_expired_notice`). 다른 데몬(부서→본부) 발신자 통지는 이번 범위 밖(§9).

### 제안 3(긴 배달 자동 파일화) — 범위 밖 · 장단점만

| 장점 | 단점 |
|---|---|
| 붙여넣기 크기 자체가 줄어 처리 지연·접힘·삼킴의 원천이 준다 · 받는 쪽 컨텍스트에 전문이 필요할 때만 읽는다 | 받는 에이전트가 파일을 **읽어야** 내용이 전달된다(도구 호출 1회 · 읽지 않으면 조용한 유실의 새 경로) · 좌석 간 파일 경로 가시성(부서 데몬·윈 경로 표기·권한) · 원장 sha 대조가 파일 쪽으로 옮겨 가야 한다 · 다이제스트 병합과 겹치는 설계 · 현장 임시 규칙(600자·한 줄)으로 이미 운영 중 |

## 5. 치명 위험 4군 점검

| 군 | 해당 | 점검 · 증거 |
|---|---|---|
| **폭주** | 해당 | 배달 1건당 Return 재전송 **최대 3회** · 간격 2/4/8초(틱 5초 해상도 → 실측 ~5/10/20초) · 경보 `submit_unconfirmed` **항목당 1회**(기록 닫힘) · 정상 배달은 이벤트 0. 시험: `qps_swallowed_queue_return_retried_three_times_then_alerts_once`(쓰기 정확히 3 · 경보 1 · 이후 5틱 쓰기 0 · 경보 0) · e2e ④(먹힘 4 = 원 1 + 3 · retried 3 · unconfirmed 1 · 90초까지 추가 0) · 뮤테이션 M2(상한 완화) → 적색. GUI 만료 알림은 좌석당 1.5초 묶음(데몬 이벤트 자체가 항목당 1회 래치). |
| **무clear** | 해당 없음 | `/clear`·Ctrl-U·Esc 를 보내는 새 경로 없음 — 쓰는 것은 Return 한 바이트뿐. 사이클 창(quiescing)에서는 관측·쓰기 0(대기). 에이전트/대화 세대가 바뀌면(사이클·재기동) 닫음. |
| **자가치유** | 해당 | 장치가 꺼지거나 실패하면 **종전 동작으로 떨어진다**: 노브 0 → 기록 없음(e2e ②: 막힘 + 기아 경보 그대로) · 관측 불능(마커 없음·블록 없음) → 쓰기 0 · 600초 상한 닫음 · 3회 소진 → 경보 1건 후 닫음(e2e ④) · 인계 실패 → 쓰기 0. 재전송 쓰기는 writer 의 기존 보류 탐침을 그대로 거친다(패닉은 기존 `catch_unwind` 안). kill-switch pause 중 쓰기 0·기록 유지(`qps_yields_to_human_and_pause`). |
| **전 pane 사망** | 해당 없음 | 프로세스 종료·신호·좌석 닫기 경로 없음. 새 락은 leaf(`submit_check`) 하나 — 다른 락을 쥔 채 잡지 않는다(세움 = 결판에서 큐 락 해제 뒤 · 재전송 = `input_gate` 안 원자·leaf 판독뿐, 보류 재제출과 같은 순서). writer 스레드에서 도는 세움은 stat 1회뿐이다. |

추가 점검: **창 위 Return(오승인)** — 판정표 12행 창 대기 + 쓰기 직전 보류 탐침(기존) 이중. **사람 초안에 Return** — 사람 바이트·본문 뒤 사람 입력이면 닫음 + 입력줄이 우리 본문으로 **완전히** 설명될 때만 씀(사람 글자가 한 자라도 섞이면 꼬리 일치 실패).

## 6. 시험 · 뮤테이션

| 시험 | 내용 | 결과 |
|---|---|---|
| `governance::tests::qps_submit_check_step_table` | 판정표 14행 · 간격 3단 · 상한 · 창 · 경계 | ✅ |
| `governance::tests::qps_remedy_row3_splits_machine_body_from_human_draft` | 3′행 machine_residue · Some(false)/None → human_draft(실례 ③) · 계수>0 행 무변경 | ✅ |
| `governance::tests::qps_transcript_line_matching` | 문자열·조각 배열 content · 공백 무시 · offset 앞 무시 · 짧아짐/없음 = None | ✅ |
| `send_settle_tests::qps_swallowed_queue_return_retried_three_times_then_alerts_once` | 실 writer · 쓰기 3 · 간격 · 경보 1 · 이후 0 | ✅ |
| `send_settle_tests::qps_retry_recovers_when_line_empties` | 재시도 1 → 빈 줄 → recovered 1 | ✅ |
| `send_settle_tests::qps_normal_delivery_closes_silently_after_settle` | 정착 창 6초 · 조용히 닫음 · 이벤트 0 | ✅ |
| `send_settle_tests::qps_yields_to_human_and_pause` | pause 중 기록 유지 · 사람 손 = 쓰기 0 | ✅ |
| `send_settle_tests::qps_transcript_user_record_vetoes_resend` | 세션 기록 user 레코드 = 쓰기 0 | ✅ |
| `send_settle_tests::qps_queue_delivery_arms_submit_check` | 실제 큐 배달(강제 배달 = 같은 결판) → 기록 섬 | ✅ |
| `send_settle_tests::qps_giveup_checks_transcript_first` | (codex QPS-4) 포기 직전 기록 확인 → recovered | ✅ |
| `send_settle_tests::qps_retry_cancel_probe_refuses_on_each_broken_premise` | (codex QPS-3 · 2R) 거부 탐침 — pause·사람·에이전트/대화 세대·입력줄 바뀜·승인 대기·기록 닫힘/교체·새 본문을 하나씩 뒤집음 | ✅ |
| `send_settle_tests::qps_handed_retry_cr_not_written_after_record_closed` | (codex 2R·3R) **실 writer 결합 · 채널 장벽**: 인계 → writer 가 탐침에서 대기 → 기록 닫힘 → 재개 = CR 0 · 보류 기록 0 | ✅ |
| `send_settle_tests::qps_handed_retry_cr_not_written_after_approval_rose` | 〃 인계 뒤 승인 대기만 섬(화면은 우리 본문) = CR 0 · 보류 기록 0 | ✅ |
| `send_settle_tests::qps_handed_retry_cr_written_when_nothing_changed` | 같은 장벽 양성 대조 — 바뀐 것 없으면 CR 1 | ✅ |
| 뮤테이션 M1 | 결판의 세움 호출 제거 | 배선 시험 **적색** ✅ |
| 뮤테이션 M2 | 상한 `>=` → `>` | 판정표 · 3회 시험 **적색** ✅ |
| 뮤테이션 M3 | 거부 탐침의 기록 결속·승인 판정 제거 | 결합 검체 2건 **적색** · 양성 대조 녹색 ✅ |
| UI `queueexpirednotice.test.ts`(5) · `toastaxis.test.ts`(+1: expired → noteQueueExpired 1회 · revived 0) · `starvednotice-split` · `queuedropnotice` · `wswiring` | | 342 pass · 0 fail ✅ |
| 전체 `cargo test --bin cysd` | 회귀 | §6-1 |

신규 `send_settle_tests` 6건은 **윈도우에서도 돈다**(`cfg_attr(not(unix), ignore)` 없음 · 같은 좌석 픽스처를 쓰는 기존 20건이 윈 CI 에서 돈다 — 현장 결함이 윈이라 의도적). 윈 `ignore` 결정 집합(52건 · `r2f_dm_windows_ignore_attributes_are_exactly_the_decided_set_of_52`)은 불변.

### 6-1. 전체 회귀(`cargo test --bin cysd` · 3,2xx 건 · 맥)

| 런 | 대상 | 결과 | 실패 판정 |
|---|---|---|---|
| 1 | 74715992 | 3229 통과 · 7 실패 | **내 변경이 깬 핀 4건**(윈 `ignore` 결정 집합 52 · `screen_diag` 키 집합 2곳 · 입력 계수 호출처 census) → 커밋 dc6a8161 에서 정당하게 갱신(신규 qps 시험은 윈 ignore 를 빼 결정 집합 불변 · 키는 추가형 · apply 1→2 는 보류 재제출과 같은 꼴). 나머지 3건(`v116_send_text_agent_launch…` · `np_native_same_pid_exec…` · `settle_hold_denies_text…`)은 내 diff 와 무관 · 단독 실행 녹색 |
| 2 | 27e7c28a | 3236 통과 · 2 실패 | `native_publication::native_transition_tests` 2건(`np_native_same_pid_exec…` · `np_windows_real_candidate_change…`) — **기준선 확인**: 내 3파일을 `origin/main`(270e3e21)으로 되돌린 같은 target 에서도 모듈 실행 시 같은 2건 실패 · 단독 녹색 = **기존 순서·시간 민감 결함**(이 티켓 밖) |
| 3 | **ecabfdbd(최종)** | **3240 통과 · 1 실패** · 15 ignored | `np_native_same_pid_exec_is_changed_not_agent_death` 1건 = 런 2 의 기준선(origin/main 소스)에서도 모듈 실행 실패가 확인된 기존 결함 · 내 diff 의 생산·시험 코드는 이 모듈을 참조하지 않는다(grep 0) |

## 7. codex 검증

### 7-1. 1R (커밋 74715992) — **REVISE** · major 3 · minor 2 · 정본 `~/.cys/pack/round/_reviews/TICKET_cysr-queued-paste-submit_커밋_74715992_…-r1-reviewer1.json`

| # | 등급 | 지적(요지) | 판단 | 반영(커밋 3번째) | 검체 |
|---|---|---|---|---|---|
| QPS-1 | major | 세션 기록 기준점을 결판(Return **뒤**)에서 잡아, Return~결판 사이에 붙은 user 레코드를 놓친다 → 낡은 화면이면 제출된 본문에 Return 재전송 | 수용(맞다) | 기준점 = **인계 순간** 스냅숏(`HandoffStamp.transcript` · `transcript_snapshot`) — 이어 쓰기(resume)도 원 인계 스탬프를 든다 · writer 스레드 stat 0 | `qps_transcript_user_record_vetoes_resend`(레코드를 arm **전**에 붙임) |
| QPS-2 | major | 머리 48자 대조 — 같은 발신자의 연속 다이제스트(머리 공통)끼리 서로의 제출 증거가 된다 | 수용 | 대조 열쇠 = 공백 제거 **본문 전체** | `qps_transcript_line_matching`(머리 같고 꼬리 다른 A/B 음성) |
| QPS-3 | major | 인계 뒤 쓰기 전 pause·에이전트 사망·세대·사람 입력을 다시 보지 않는다(보류 탐침은 창만 본다) · 게이트 안 재확인도 부족 | 수용 | `queue_retry_cancel_probe`(writer `refuse` — 쓰지 않고 보류 기록도 없음): pause · 좌석 Off · 에이전트/대화 세대 · 새 기계 본문 · 사람 바이트/본문 뒤 사람 입력 · **입력줄이 더는 그 본문이 아님** + 게이트 안 재확인에 pause·세대·사람 추가 | `qps_retry_cancel_probe_refuses_on_each_broken_premise`(전제 7개를 하나씩 뒤집음) |
| QPS-4 | minor | 포기(GiveUp) 때 세션 기록을 보지 않아 마지막 재전송이 실제로 제출됐어도 unconfirmed | 수용 | 포기 직전에도 기록 확인 → 제출이면 `submit_recovered(basis=confirmed_transcript)` | `qps_giveup_checks_transcript_first` |
| QPS-5 | minor | 3′행 문장이 재전송이 꺼졌거나 끝난 뒤에도 「최대 3회 다시 보낸다」고 약속 | 수용 | `QueueBlockDiag::submit_retry_live`(진단 JSON 밖) — 살아 있으면 「다시 보내는 중(최대 3회)」 · 아니면 「끝났거나 꺼져 있다 — 사람이 …」 | `qps_remedy_row3_splits_machine_body_from_human_draft` 두 갈래 |

### 7-2. 2R (27e7c28a) — **REVISE** · major 3 — QPS-1·4·5 해소 확인

| # | 지적 | 반영(7be38f56) | 검체 |
|---|---|---|---|
| R2-1 | 본문 전체라도 **부분 문자열** 대조 — B 가 A 의 접두부·인용이면 A 의 늦은 레코드가 B 를 닫는다 | 공백 제거 **동일성** | 접두부·인용 음성 검체 · 꼬리 덧붙은 레코드를 참으로 기대하던 검체를 거짓으로 고침 |
| R2-2 | 거부 탐침이 **살아 있는 기록**에 묶이지 않아, 인계 뒤 writer 가 밀린 사이 포기·기록 확인으로 닫혀도 CR 을 쓴다 | 탐침이 같은 `armed_at` 기록이 살아 있을 때만 허가 | 탐침 단위 + 3R 결합 검체 |
| R2-3 | 인계 뒤 선 **승인·관문 대기**를 writer 가 다시 보지 않는다(보류 탐침은 화면 창만) | 탐침에 `approval_or_gate_pending`(`inject_safety_probe` ⓑ 와 같은 판독 · writer 스레드 poison 관용) | 〃 |

### 7-3. 3R (7be38f56) — **REVISE** · 런타임 결함 없음 · 시험 공백 2(요구한 결합 검체 미충족)

반영(ecabfdbd): 실제 탐침을 감싼 **채널 장벽**으로 「인계 → writer 가 탐침 직전 대기 → 기록 닫힘 / 승인 대기 → 재개」 순서를 sleep 없이 만든 실 writer 결합 검체 2건 + 같은 장벽의 양성 대조. 뮤테이션 M3 로 적색 확인.

### 7-4. 4R (ecabfdbd) — **ACCEPT** · 미달 0

정본 verdict 4건: `~/.cys/pack/round/_reviews/TICKET_cysr-queued-paste-submit_…-r1-reviewer1.json` · `…_R2_…-r2-reviewer1.json` · `…_R3_…-r3-reviewer1.json` · `…_R4_…-r4-reviewer1.json`.
codex 는 4 라운드 모두 정적 검토만 했다(cargo·cys 실행 금지 의뢰) — 실행 근거는 이 보고서 §2·§6 의 워커 실측이다.

## 8. 윈 실기 항목 (master → 윈-마스터 중계)

| # | 항목 | 방법 | 합격 |
|---|---|---|---|
| W1 | 현장 조건 재현(수리 전 판) | 윈 11 · cysr 1.1.14 · 긴 master 세션 좌석에 다른 좌석이 `cys send --queued` 로 60줄+ 여러 건(병합되게 연달아) | 입력줄 `[Pasted text #N +M lines]` 미제출 · `queue list` 사유 `input_pending` · 처방 `human_draft` 를 관측(재현 조건 기록: 세션 길이·줄 수·간격) |
| W2 | 수리판 같은 조건 | W1 과 같게 | `queue.submit_retried` 1~3건 뒤 제출(세션 jsonl user 레코드) · 뒤 항목 배달 · `queue.starved` 0 |
| W3 | 오너 초안 보존(실례 ③) | 오너가 그 좌석 입력줄에 직접 여러 줄을 붙여 두고 큐 항목 1건 | Return 재전송 0 · 처방 `human_draft` 그대로 · 큐 보류(종전) |
| W4 | 포기 경로 | (가능하면) 좌석을 오래 바쁘게 둔 채 W2 | 최대 3회 · `queue.submit_unconfirmed` 1건 · 그 뒤 쓰기 0 · 처방 `machine_residue` |
| W5 | 만료 알림 | `CYS_QUEUE_TTL_SECS` 를 짧게(예 120) 한 시험 데몬에서 막힌 좌석에 항목 2건 | GUI 토스트 + OS 배너 1줄("… 2건 …") |
| W6 | 윈 CI | 신규 `qps_*` 6건(윈 ignore 없음) | 녹색 |
| W7 | 모형 e2e(윈) | `docs/queued_paste_e2e/run_ab.py` 는 유닉스 소켓 경로 — 윈은 이식 필요(파이프 이름) · 선택 | — |

## 9. 남은 위험

1. **원인 후보 미확정** — 맥에서 실 Claude Code 로는 재현 못 했다. 수리는 「TUI 가 왜 먹든」 우리 쪽 결함 3개(확인 없음 · 오판 · 무알림)를 고치지만, 윈에서 지연이 **8초 이상 반복**되면 3회 재전송도 먹힐 수 있다(그때는 경보 1건 + 종전 보류 · W4).
2. **세션 기록 경로가 없는 좌석**(사용량 등록 전 · 다른 어댑터)은 화면 양성만으로 쓴다 — 화면 사본이 어긋나 우리 본문으로 **잘못** 보이면 빈 줄 Return 1~3회(빈 줄 Enter 는 Claude Code 에서 무동작 · 창이면 보류 탐침이 막음).
3. **바쁜 좌석**: 프롬프트 경계(바쁨 표지 근처)에서 기다리므로 긴 턴(>600초) 동안 먹힌 잔여는 상한 뒤 경보로 끝난다(재시도 없이) — 큐 틱과 같은 경계 규칙을 일부러 따랐다.
4. **부서→본부 교차 데몬 발신자에게 만료 통지 없음** — `from` 이 이 데몬의 `surface:N` 이 아니면 이벤트만 나간다(종전). 오너는 ⓒ 로 안다.
5. (해소 · codex QPS-1) 세션 기록 stat 은 인계 시점(`HandoffStamp::of` · 큐 틱 스레드)으로 옮겨 writer 스레드 IO 는 0 이다. 대신 큐 틱이 배달마다 stat 1회를 한다.
7. 거부 탐침의 사이클 창(quiescing) 재확인은 넣지 않았다 — writer 스레드에서 데몬 상태 락을 새로 잡지 않기 위해서다. 사이클은 대화 세대(`/clear`) 변화로 거부된다고 보았으나 세대가 오르는 시점과 quiescing 시작 사이 창은 측정하지 않았다.
6. 틱 5초 해상도라 실제 재시도 간격은 2/4/8초보다 길다(~5/10/20초).

## 10. 커밋 · 원격

가지 `fix/cysr-queued-paste-submit`(base `origin/main` 270e3e21): `74715992` 수리 · `dc6a8161` 핀 갱신 · `27e7c28a` codex 1R 반영 · `7be38f56` codex 2R 반영 · `ecabfdbd` codex 3R 결합 검체 · (이 보고서 커밋).
**원격 push 하지 않았다** — 워커 지침 §6-9 불변식 5(비가역 = 2단계 핸드셰이크). master 재승인이 오면 작업 가지만 push 한다. 판 올림·서명·릴리스·태그는 master 게이트.
