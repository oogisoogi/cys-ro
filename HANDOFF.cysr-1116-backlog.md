# HANDOFF — TICKET=cysr-1116-backlog (worker-4 · surface:2150 · 2026-11-17 21:25~)

- 가지 `integ/1116-backlog` ← `integ/1115-r2` 3a095c4e · 작업트리 `~/axdev/.wt/cys-1116-backlog`
- 브리프 = `master/briefs/2026-11-17-cysr-1116-backlog.md`(원장 spawn 항목 · sha256 16042f43…) + 범위 추가 `master#4f5897d7`(원장 대조: surface:2150 · queued ∧ session_jsonl_nonce · 21:47)
- 다른 좌석(integ/1116-vendor) 파일 손댐 0: 이 가지의 변경 파일 = `src/lib.rs` · `src/bin/cysd/{governance,handlers,state,send_settle_tests}.rs` 뿐(pack.rs · javis_wakeup.py · cys.rs · 릴리스 스크립트 0)
- push · 서명 · 발행 · 설치 = 0

## 0. 커밋(3a095c4e 위 · 순서대로)

| 커밋 | 항목 | 무엇 |
|---|---|---|
| 1b98d057 | 2 | census `production_slice` 가 들여쓴 `#[cfg(test)]` 시험 **모듈**을 걷어 냄 · 동결표 seatkeep 10 → 0(칸 삭제) |
| 7368c2a3 | 1 | 큐 Return 재전송 × agy 문(재검사 틱이 기록을 닫음 · 쓰기 직전 거부 탐침) + 부기(인계 중 항목에 묘비 안 남김) |
| e4499d72 | 3 | 원자 `refuse_on_approval` 제출의 Enter 직전 승인 재판정(사람 길 = `WriteReq::InjectRefusing` · 기계 길 = `SubmitRefuse`) |
| e8c2e4e9 | codex 1R | major 3: 보류된 재전송 CR 의 agy 문맥 · 기동 줄 항목별 판정 · slicer 닫힘 꼴 |
| 5474ffd5 | codex 2R | 잔여 2: 같은 본문 일반 보류가 agy 문맥 유지 · slicer 를 중괄호 짝으로 |
| 9599765f | codex 3R | slicer 어휘: 이스케이프 문자 리터럴(`'\''`) |
| 6e14a9de | codex 4R | slicer 어휘: C raw 문자열(`cr#"…"#`) + 들여쓰기 이중 장치 |
| 51e1334f | (시험) | 이중 장치만 잡는 핀 |
| 892c2949 | codex 5R | 들여쓴 경로 판정을 파일 전체 어휘 상태로(주석·문자열 속 가짜 모듈 제외) |
| eca3394a | codex 6R | 속성 줄은 「속성만으로 된 줄」만 건너뜀(같은 줄 속성+항목) |
| 54011706 | codex 7R | 주석·문자 따옴표가 섞인 속성 줄은 순수 속성 아님 |
| 6770eff8 | (정형화) | 속성 줄·모듈 머리를 **정형 목록**으로(정형 밖 = 걷지 않음 = 운영으로 셈) |
| a2f2e451 | codex 8R | 리터럴 접미사(`""r`) 소비 |
| 16ad25ca | codex 9R | 식별자 글자 = 비ASCII 비공백 전부(결합 문자 접미사) |
| f712778d | codex 10R | raw 식별자 `r#이름` 한 토큰 |
| 44f27dc9 | (시험) | 전체 시험이 잡은 소스 핀 2건: h7 생산자 핀(패턴 속 `guard: None` 글자) · 윈 ignore 52건(b16_atomic 4건 ignore 제거 — 윈에서도 돈다 · 이 맥에선 윈 미확인) |

## 1. 항목 1 — 큐 Return 재전송 × agy 좌석 문(HANDOFF 1115-r2 §4-3 선택지 B)

- 규칙 = 배달 직전 재판정 `drop_agy_door_closed` 와 같게: **문 닫힘 ∧ 출처 ≠ `send_human` ∧ (닫힌 문의 agy 좌석 ∨ 실린 항목 중 agy 기동 줄)** 이면 데몬이 그 Return 을 다시 쓰지 않는다.
  - `SubmitCheck` 에 `origin`(머리 출처 — 병합 키가 출처라 배달 전체의 출처) · `agy_launch_line`(항목 **원문마다** 판정 `delivery_has_agy_launch_line` → `Delivered.agy_launch_line` 로 운반) 을 실음.
  - 재검사 틱 `recheck_queue_submit_one`: 해당하면 기록을 닫음(처분 `agy_door_closed` · 이벤트 0 · 쓰기 0).
  - 쓰기 직전 탐침 `queue_retry_cancel_probe`: 인계 뒤 문이 닫혔으면 그 CR 거부.
  - 보류 경로(codex 1R·2R): 재전송 CR 이 창에 보류되면 `WithheldSubmit.agy_launch_line` 이 문맥을 이어받고(같은 본문의 일반 보류도 지우지 않음 `note_withheld_keeping_agy`), 재제출 틱이 버림(`queue.submit_withheld_dropped` 사유 `agy_door_closed`) · 재제출 CR 에도 쓰기 직전 문 탐침.
  - 사람 자판 출처는 종전 그대로 재전송·재제출(시험으로 확인).
- 부기 「같은 항목에 묘비와 배달 둘 다」: `drop_agy_door_closed` 가 인계 중(`inject_reservation` ids) 항목은 빼지 않는다 → 결판이 처분(썼으면 배달 · 안 썼으면 큐에 남아 다음 재판정이 뺌).
- 재현(§4-3 관측 꼴 · 격리 HOME · 닫힌 문 · gemini=agy 어댑터 · 마커 `>` · 먹힌 Return): **고치기 전 붉음** = `step=resent` · PTY 쓰기 +1(관측 · 21:43 실행 로그) → 고친 뒤 처분 `agy_door_closed` · 쓰기 0.
- 시험(전부 `send_settle_tests`/`governance::tests`): `b16_agy_door_closed_machine_retry_is_not_written` · `b16_agy_door_closed_human_retry_still_written` · `b16_agy_launch_line_retry_follows_door_rule` · `b16_launch_line_is_judged_per_entry_not_on_digest` · `b16_agy_door_closing_mid_flight_cancels_machine_retry_cr`(전문가 몫 — 쓰는 중 닫힘 · 기계 0 / 사람 1) · `b16_withheld_queue_retry_cr_not_resubmitted_after_agy_door_closed` · `b16_resubmitted_cr_refused_when_agy_door_closes_mid_flight` · `b16_plain_withhold_keeps_agy_context_of_same_body` · `b16_agy_door_drop_skips_in_flight_entry`.
- ⚠시험 한계(정직): 문 파일은 `$HOME` 아래 프로세스 전역이라 시험 안에서 여닫지 않는다 — 「쓰는 중 닫힘」은 같은 판정(`agy_door_seat_closed`)을 좌석 메타가 agy 로 바뀌는 쪽으로 뒤집어 고정했다. `deliver_head_locked` 안의 `delivery_has_agy_launch_line(&merged)` 배선 한 줄은 닫힌 문에서 agy 기동 줄이 배달되지 않으므로 끝-끝 시험이 없다(함수 자체는 시험·뮤턴트로 고정).

## 2. 항목 2 — census 세는 쪽 사각(§12-2 B)

- `production_slice` 가 들여쓴 `#[cfg(test)]` 뒤 `mod x {`(가시성 무관) 머리를 시험 모듈로 걷어 낸다. 판정은 파일 전체 어휘 분석(`lex_rust_lines`: 줄·블록 주석 중첩 · 문자열 · raw/byte/C raw 문자열 · 문자 리터럴 · 수명 구분) 상태로만:
  - 속성 줄과 모듈 머리가 **코드에서 시작**해야 함(주석·문자열 속 가짜 제외).
  - 끝 = 머리 `{` 의 **중괄호 짝** · 그 줄이 같은 들여쓰기 `}` 한 줄이 아니면 실패(Err).
  - 이중 장치: 머리와 짝 사이의 비지 않은 줄이 모두 모듈보다 깊이 들여써야 함(아니면 Err) — 어휘 오인이 진짜 끝을 지나치면 형제 운영 줄에서 걸린다.
  - 모듈이 아닌 들여쓴 `#[cfg(test)]`(구조체 칸·식 문장·match 갈래 — realops.rs·update_hold.rs 등 80여 곳)는 손대지 않음: 그 머리는 `,` 로 끝나 일반 규칙으로 따라가면 운영 코드를 삼킨다(실측 realops.rs 111줄).
- 동결표: `src/bin/cys-seatkeep/main.rs` **10 → 0(칸 삭제)** — 브리프의 「10 → 2」 가 아니다: 1차 동결값 2 도 같은 들여쓴 시험 모듈 안 것이었다(`ps` 확인 1 · `/bin/sh` 검체 1). 2 로 두면 붉음(뮤턴트 M7 관측).
- **운영 계수 변화 목록**: seatkeep 1건뿐(10 → 0). 그 밖 모든 `src/**.rs`·`src-tauri/src/**.rs` 계수 불변(파이썬 모형으로 전수 측정 + lib census 시험 초록).
- 📌(범위 밖 · 기존 규칙): 열 0 `#[cfg(test)]` 경로는 v1.1.14 부터 「첫 열 0 `}` 까지」 규칙 그대로다 — codex 5R major 1: 비정형 꼴(`    }` 로 모듈을 닫고 뒤에 열 0 운영 함수)이면 Ok 인 채로 운영 코드를 걷는다. rustfmt 를 CI 가 강제하지 않는다(.github 에 fmt 0건 관측). 고치면 모든 파일 계수 판정이 바뀌는 공용 그물 변경이라 별건으로 올린다.

## 3. 항목 3(master#4f5897d7) — 원자 제출의 Enter 직전 승인 재판정

- 원자료 = 조각 0.5 실측 `SLICE-0.5-MEASURE-RESULT.md` M2-c(쓰는 도중 창 3/3 · Enter 까지 들어감 · 남는 창 0.73~0.84초) · M2-주(두 술어가 다르다).
- 사람 원자 제출(앱 send_input 꼴 · `human ∧ ¬machine_origin` → 종전 `WriteReq::Inject`): `refuse_on_approval` 이면 새 변형 **`WriteReq::InjectRefusing`** — 바이트·순서·지연은 Inject 와 같고 cr_delay **뒤** · CR **바로 앞**에 탐침. 참이면 CR 0(Ctrl-U·본문은 이미 썼고 지우거나 다시 치지 않음).
- 기계 원자 제출(OwnedClear 에이전트 작업): `SubmitRefuse` 증명이 Submit 단계를 거부(PartialExact · 사유 `submit_refused:approval_screen` · 보류 아님 = 재제출 없음).
- 탐침 `approval_enter_guard` = `seat_approval_pending`(쓰기 직전 화면 판정 ∨ 관문 항목) **∨ `approval_or_gate_pending`(feed 승인 항목 `daemon-…`)** · 처분은 기존 `approval_write_guard` 와 같음: 버스 `input.refused_at_write`(reason `approval_screen`) + 입력줄 계수 ≥1 복원(뒤 배달 이어붙기 방지). `approval_write_guard`·`send_key` 거부 모드는 바이트 하나 안 바꿈(소스 핀 그대로 초록).
- 재현 = 실측과 같은 꼴(응답 뒤 150ms 에 창/feed 항목 · writer 는 Ctrl-U 정착 중) → 고치기 전 Enter 1 붉음(배선 끈 뮤턴트 M8 = 고치기 전 동작 · 붉음 관측) → 고친 뒤 Enter 0 · 거부 흔적 1 · 계수 > 0.
- 시험: `b16_atomic_refuse_send_rechecks_approval_before_enter` · `b16_atomic_refuse_send_sees_feed_pending_before_enter` · `b16_atomic_refuse_machine_job_rechecks_approval_before_enter` · `b16_atomic_send_unchanged_without_dialog_or_refuse_flag`(창 없음 = Enter 1 · 계수 0 · 옵션 없는 원자 제출은 창이 떠도 종전대로 Enter).
- ⚠한계(정직): RPC 응답은 쓰기 전에 나가므로(실측 M1: 0.45~0.72ms) **거부 코드는 응답이 아니라 이벤트**(`input.refused_at_write`)로만 남는다 — 앱이 이 이벤트를 받아 「보내지 않음」을 보이게 하는 것은 화면 조각 몫.
- 📌(덧붙임 · 실행 안 함): ⑴ 창이 Ctrl-U 정착 중(0.15초)에 뜨면 **붙여넣기 본문은 여전히 그 창에 들어간다**(이번 고침은 브리프대로 Enter 만 막음) — 붙여넣기 앞에도 같은 재판정을 둘지 ⑵ 쓰기 **전** 판정(핸들러)도 feed 승인 항목을 볼지(M2-주 첫 견본: 가로줄 없는 화면은 쓰기 전 판정이 거짓) · ⑶ 큐 Return 재전송(1번)과 「Enter 직전 재판정」 모양은 같지만 기계가 달라(SafetyProbe on `SubmitAfterGap` vs agent_write Proof vs Inject arm) 공통 함수로 묶지 않았다.

## 4. 뮤턴트(각각 적용 → 해당 시험 → 커밋본으로 원복 · 전부 관측)

M1 재검사 닫기 끔 · M2 쓰기 직전 탐침 끔 · M3 인계 중 제외 끔 · M4 출처 무시 · M5 기동 줄 무시 · M6 들여쓴 모듈 규칙 끔 · M7 동결표 2 · M8 InjectRefusing 배선 끔(= 고치기 전) · M9 CR 앞 탐침 끔 · M10 feed 술어 끔 · M11 SubmitRefuse 배선 끔 · M12 재제출 틱 agy 끔 · M13 재전송 보류 문맥 None · M14 재제출 쓰기 직전 탐침 None · M15 닫힘 꼴 검사 끔 · M16 항목별 기동 줄 → 거짓 · M17 문맥 유지 끔 · M18 어휘 문자열 끔 · M19 정확한 닫힘 검사 끔 · M20 어휘 문자 끔 · M21 옛 이스케이프 처리 · M22 `cr` 접두 끔 · M23 이중 장치 끔 · M24+25 코드 시작 검사 둘 다 끔 · M26 블록 주석 줄 상태 끔 · M27 옛 속성 건너뛰기 · M28 속성 줄 주석 검사 끔 · M29 머리 정형 검사 끔 · M31 접미사 소비 끔 · M32 식별자 ASCII 만 · M33 raw 식별자 끔 — **전부 붉음(사망)**.
- 살아남은 것(정직): ⑴ M24·M25 를 **하나씩** 끄면 초록 — 주석 속 가짜에서는 속성 줄·머리 줄이 둘 다 주석 안이라 서로를 대신한다(둘 다 끄면 붉음). ⑵ M30(속성 글자 목록 검사 끔) 초록 — 그 검사만 결과를 가르는 입력을 못 만들었다(구조 판정 `#[`…`]` 반복이 같은 입력을 이미 거른다 · 중복 방어선).

## 5. codex(읽기 전용 · 판정 파일 = `~/.cys/pack/round/_reviews/cysr-1116-backlog-codex-r{1..6}.json`)

| 라운드 | 대상 | 판정 | 처분 |
|---|---|---|---|
| 1R | 7368c2a3·e4499d72·1b98d057 | REVISE · major 3 | e8c2e4e9 |
| 2R | e8c2e4e9 | REVISE · 잔여 major 2(1·3) · major 2 닫힘 | 5474ffd5 |
| 3R | 5474ffd5 | REVISE · major 1(`'\''`) · 잔여 둘 닫힘 | 9599765f |
| 4R | 9599765f | REVISE · major 1(`cr#"…"#`) | 6e14a9de + 51e1334f |
| 5R | 6e14a9de·51e1334f | REVISE · major 2(열 0 경로 = 기존 규칙 → 📌 · 주석 속 가짜 → 고침) | 892c2949 |
| 6R | 892c2949 | REVISE · major 1(같은 줄 속성+항목) · 5R 닫힘 | eca3394a |
| 7R | eca3394a | REVISE · major 1(속성 줄 주석 속 대괄호) | 54011706 + 6770eff8(정형 목록) |
| 8R | 54011706·6770eff8 | REVISE · major 1(리터럴 접미사 `""r`) · 7R 닫힘 | a2f2e451 |
| 9R | a2f2e451 | REVISE · major 1(결합 문자 접미사) | 16ad25ca |
| 10R | 16ad25ca | REVISE · major 1(raw 식별자 `r#r`) · 9R 닫힘 | f712778d(10R = 상한 · 이 고침은 리뷰 안 받음) |
- 1번·3번(데몬 동작 · `governance/handlers/state.rs`)은 **2R 이후 새 지적 0**(3R~10R 대상 범위 밖이 아니라 대상에 들지 않음 — 3R 부터는 그 고침만 냈다). 3R~10R 은 전부 census 어휘 분석기(시험 계측 도구 · `src/lib.rs` 시험 모듈).
- **【격차 보고 — 10R 상한 도달】** 라운드마다 codex 가 새 토큰 꼴(이스케이프 문자 · C raw · 접미사 · 결합 문자 · raw 식별자 · 주석 속 대괄호)로 「들여쓴 시험 모듈 밖 운영 줄을 Err 없이 걷는」 반례를 만들었다. 전부 고쳤지만 손으로 만든 어휘 분석기의 이 꼴 반례가 더 없다고 말할 근거는 없다. 결함이 나려면 ⓐ코드 위치의 정형 `#[cfg(test)]`+`mod x {` ⓑ그 안의 비정형 토큰(대개 매크로 입력 속) ⓒ오인이 진짜 끝을 지나 같은 들여쓰기 `}` 한 줄에 정확히 떨어짐 ⓓ그 사이 모든 줄이 모듈보다 깊음 — 넷이 함께 서야 한다(실물 저장소에 들여쓴 시험 모듈 = cys-seatkeep 1개). 결과 = census 가 운영 스폰을 덜 셈(거짓 초록 · 계측 도구 한정 · 제품 동작 무관).
  - 📌 대안(권고 · 실행 안 함): 손 분석기를 버리고 `proc-macro2`(span-locations) 토크나이저로 짝을 찾기 — 토큰 경계가 rustc 와 같아진다. 대가 = `[dev-dependencies]` 추가(Cargo.toml·Cargo.lock 변경 · 공급망 검토 대상). 또는 들여쓴 경로를 아예 「시험 모듈 자체에 `// census: test-module-end` 표지」 같은 명시 표지 방식으로.

## 6. 전체 시험(격리 env · HANDOFF 1115-r2 §7 틀 · PATH 에 /usr/sbin:/sbin · 기준선 = 3a095c4e 별도 작업트리 같은 명령 · 전부 관측)

- 스크립트 = `/private/tmp/claude-501/b16/suite.sh`(기준선 결과 `…/s-base/` · HEAD 결과 `…/s-head/`). HEAD 묶음은 9599765f 에서 돌았고, 그 뒤 커밋은 `src/lib.rs` 시험 모듈(f712778d 까지)과 cysd 시험·패턴 1줄(44f27dc9)뿐이라 **lib·cysd 만 최종 머리로 다시** 돌렸다.
- 두 기계 부하(기준선·HEAD 동시)로 느림 — cys 852초 · cysd 850~956초.

| 대상 | 기준선 3a095c4e | HEAD | 비고 |
|---|---|---|---|
| build `--bins` · `test --no-run --bins --lib --tests` | rc 0 · rc 0 | rc 0 · rc 0 | |
| lib | 1238 · 0 · 2 무시 | **1238 · 0 · 2**(f712778d) | 시험 수 같음(새 검체는 기존 시험 안 단언) |
| bin cys | 760 · **1**(`dbg_r12_init_pack_wires_profile_skill_links`) · 2 | **761 · 0** · 2 | 기준선만 붉음 = HANDOFF 1115 「기준선만 붉던 dbg_r12」 와 같은 꼴 |
| bin cysd | 3272 · **3** · 17(`dbg_r12_update_lane_restore_seat_gets_link_before_exec` · `dbg_r12_seat_profile_wired_before_agent_exec` · `pending_requests::…installed_uncertainty_latches_and_reopens_without_execution`) | **3287 · 1** · 17(44f27dc9 · `pending_requests::…installed_uncertainty_latches…`) | HEAD 의 1 = 흔들림: 단독 3/3 초록 · `pending_requests::` 모듈 99/0. 합계 3292 → 3305 = 새 시험 13(`b16_*` · 추가 `#[test]` 13 · 삭제 0) · 9599765f 판의 전체 실행에선 내 탓 핀 2건(h7 · r2f 52) 붉음 → 44f27dc9 로 고침 |
| bin cys-seatkeep | 49 · 0 | 49 · 0 | |
| tests/*.rs | hidden_seat_screen 1/0 · rotate_autorestore_hold 11/0 · seat_group 1/0 · update_drainhold_e2e 4/0 · win_job_exit 0 · win_pack_swap 0 | 같음 | |
| bun test(ui) | 3451 pass · 88 skip · 0 fail | 같음 | |
| tsc `--package typescript@7.0.2` | rc 0 | rc 0 | 음성 대조(기준선 작업트리에 타입 오류 1줄) = rc 1 · TS2322 · 원복 |
| 화면 게이트 7종 | race·focus·seatrows·pillar·seatgroup·rolereuse·stty 전부 `RESULT: PASS` | 같음 | ⚠playwright venv(`GlobalNews-Crawling-AgenticWorkflow/.venv`)가 사라져 첫 실행 rc 127 → 스크래치 venv(`/private/tmp/claude-501/b16/pw` · pip playwright 1.60 · 브라우저 다운로드 0 · CHROME_PATH = 기존 chromium_headless_shell-1248)로 두 쪽 다시 |
| agy 수용 `acceptance.py` | PASS 34 · FAIL 0 · 종합 PASS | 같음 | 실행 뒤 `git checkout -- docs/agy-door-evidence/` |
| 팩 파이썬 | computer_control 112 OK · agents_notes_personal_hooks OK · dept_chat_inject_timeout 3 OK · hook_fail_log 11 OK · hook_fail_timing 10 OK · javis_counsel 118 OK(skip 3) · agy_door 20 OK · agy_door_phoenix_loop OK | 같음 | |
| health `--json` | 167 pass · 2 fail(H-CLT-1·2) · 1 skip(H-WIN-11) | 같음 · 실패 사유 글자 같음(동봉 python 경로 = 이 기계 환경) | |
| secret-scan `--all` | ✓ clean(2049 파일) | ✓ clean(2049 파일) | 이 인계서 커밋 뒤 다시 잼(§9) |

- 새 적색(기준선 대비) = **0**(HEAD 의 cysd 1 = 기준선에도 있는 흔들림 계열 · 단독 초록).

## 7. master 가 다시 돌릴 명령

```sh
W=~/axdev/.wt/cys-1116-backlog; cd $W && git log --oneline 3a095c4e..HEAD
# 격리 env 틀 = HANDOFF 1115-r2 §7 (PATH 에 /usr/sbin:/sbin 포함 · HOME·TMPDIR 짧게)
cargo test --bin cysd -- b16_ qps_ integ_1115 u16_     # 항목 1·3 + 기존 큐 배달·거부 모드
cargo test --lib -- production_slice raw_command_new_census   # 항목 2
# 전체 = 스크립트 /private/tmp/claude-501/b16/suite.sh <작업트리> <이름> (결과 /private/tmp/claude-501/b16/s-<이름>/)
```

## 8. 함정

- 큐 배달 탐침 시험은 `$HOME` 의 agy 문 파일이 **닫힘**이어야 한다(열려 있으면 b16 agy 시험은 「건너뜀」 출력 후 통과) — 격리 HOME 에서 돌린다.
- `PaintAtSubmit`(에이전트 작업 좌석 증명)은 종전 `Inject` 길에서는 불리지 않는다 — 사람 원자 제출 재현은 시각 주입(응답 뒤 150ms)으로 했다(처음 그 증명으로 짠 시험은 거짓 붉음이었다 · 정직 기록).
- 같은 target 을 쓰는 전체 시험 도중 `src/lib.rs` 시험 모듈을 고치면 그 뒤 단계는 새 lib 로 다시 빌드된다(시험 모듈만 바뀌어 다른 대상 결과에는 영향 없음 · lib 단계는 따로 다시 돌림).

## 9. 마무리

- 최종 머리 = 44f27dc9(+ 이 인계서 커밋). 작업트리 깨끗(인계서 외 변경 0).
- 지운 것: 없음. 남긴 것: 기준선 작업트리 `/private/tmp/claude-501/b16/wtb`(detached 3a095c4e · 변경 0 · `target` 있음 — master 재검증에 쓸 수 있게 둠 · 지울 때 `git -C ~/axdev/.wt/cys-1116-backlog worktree remove --force /private/tmp/claude-501/b16/wtb`) · 스크래치 playwright venv `/private/tmp/claude-501/b16/pw` · 시험 로그 `/private/tmp/claude-501/b16/{s-base,s-head,lib-final.log,cysd-final.log}` · codex 프롬프트·원문 `/private/tmp/claude-501/b16/codex/`.
- 증류: 「손 어휘 분석기로 Rust 소스 경계를 정하는 계측은 적대 검토가 라운드마다 새 토큰 꼴 반례를 낸다 — 정형 목록 + 이중 장치(들여쓰기) + 보수 쪽 실패로 묶고, 끝내려면 실제 토크나이저」 · 「화면 게이트 playwright venv 경로가 사라질 수 있다 — 스크래치 venv + CHROME_PATH」.
