# HANDOFF — TICKET=cysr-1116-borrow23-1119 (차용 ② 상태 판정 OSC 7501 + ③ 가벼운 시작)

- 좌석 worker-1116borrow23(surface:2269) · 가지 `feat/1116-borrow23` ← `integ/1116` dea2e1853 · 브리프 `master/briefs/1116-full/borrow23.md`
- push·태그·CI·발행·앱 교체·실사용 데몬 접촉 = 0(시험은 격리 HOME·임시 PTY·CYS_* 제거 env).

## 0. 먼저 실측 — 진짜 Claude Code 가 7501 을 내는가

격리 PTY(사용자 설정 미적재 `--setting-sources project` · CYS_*/CMUX_*/CLAUDE_CODE_* 제거 · 임시 폴더 · Haiku)에서 Claude Code **2.1.328** 을 3갈래로 띄웠다.
원자료(경로 가림) = `docs/evidence/borrow23-1119/claude-2.1.328-osc7501-probe.jsonl` · 하네스 = `docs/evidence/borrow23-1119/probe7501.py`.

| 갈래 | 질의 응답 | 받은 7501 보고 | 제목 OSC 0 |
|---|---|---|---|
| A | 안 함(오늘까지의 cysd) | **0건**(시작 때 `ESC]7501;?BEL` 질의 1건뿐) | 6건(◐◑✳ 표지 포함) |
| B | 함 | `blocked:kind=permission:msg="trust this folder"` → `clear` → `idle` → `working` → `working:msg="Writing probe.txt"` → `done` → (/exit) `clear`×2 | 3건(표지 없음 · 대화 주제로 바뀜) |
| C | 함 + 권한 기본 모드 | … `working` → `blocked:kind=permission:msg="approve Write: …/probe.txt"` → Esc → `idle` → `clear`×2 | 3건 |

결론: **답하지 않으면 보고가 없고, 답하는 순간 Claude 는 제목 표지를 그리지 않는다** → 기존 화면 문법(`ClaudeR1`)이 그 좌석을 더는 분류 못 한다. 그래서 응답과 소비를 한 묶음으로 넣었다(응답만 넣으면 오히려 퇴보).
덤: 크롬 확장 안내 창은 7501 blocked 로 오지 않았다(B 갈래 — 창이 닫힌 뒤 idle).

## 1. 바뀐 것

### ② 상태 판정(데몬 · UI · CLI)
- `src/bin/cysd/program_status.rs`(새 · 원작자 파일 아님): 규격(Rex Program Status rev 0.2~0.4 공개 문서 · 코드 차용 0) 버림 규칙 파서 — 시퀀스 4096 · 키 16 · app 32 · id 128/세그먼트 32/깊이 8 · title 256/192 · msg 2732/2048 · 엄격 base64(정규형) · 해독 글 제어 문자 0 · 방향 바꿈/폭 0 문자 제거 · **쌍마다** 한도 검사. 청크 경계 스캐너(7501 · OSC 133;A 프롬프트 시작 · RIS · CAN/SUB · 유계 4096). 좌석 저장소(id 계층 · clear 하위 포함 · 상한 64 · 급한 순 blocked>error>working>done>idle · app 조상 상속 · 판 계수 `version`). 덧씌움(done/error 는 그 뒤 사람 입력이 있으면 「봄」). 진단 wire.
- 질의 응답 = DSR 응답과 같은 데몬 쓰기 `WriteReq::Data`(사람 입력 계수·타이핑 가드·입력 원장 무접촉 — 실 PTY 시험이 `last_human_input`·`pending_input_bytes` 무변화를 단언). 응답 바이트 = 고정 `ESC]7501;?` + 질의와 같은 종결자(보고 내용을 되쓰지 않음).
- 응답 관문 = `CYS_PROGRAM_STATUS≠0` ∧ `CYS_DISPLAY_ACTIVITY≠0` ∧ **화면 관측기 스레드가 실제로 도는 중**(`activity.running` · 죽으면 Drop 가드가 내림). 답하지 않은 질의는 `unanswered` 로 센다.
- `activity.rs`: `Effective::Done`("done") · `Raw` 에 auth·blocked·done·error · 모든 출력에 `meaning`(상태 이름의 뜻) · `source`(screen|program_status) · `program_status`(근거). `wire_with` 가 신원·화면 재검증을 거친 뒤 상태·사유·안정 나이만 덧씌운다(같은 세대). 순번 = 관측 순번 + 판×2 + 봄 — 같은 세대 안 단조(`overlay_seq`).
- 지움(⒟): 에이전트 종료 래치(governance) · PTY 프로세스 종료(state reader EOF) · 셸 프롬프트(133;A = working/blocked) · RIS · Claude 자신의 clear.
- 진단(⒞): `surface.list` 에 `program_status_diag` · `cys daemon explain-state --surface N [--json]`(상태·뜻·출처·사유·프로그램이 적은 말·질의 응답/보고/버림 계수·마지막 원문·지운 까닭 · 자동 기동 금지 목록 등재).
- UI: `roleactivity.ts` 파서(done·새 raw·meaning·source·program_status · 1.1.15 데몬 꼴도 그대로 받음 · done 은 프로그램 보고에서만 · 꼴 틀리면 Unknown) · 투영(done 점 = `act-done` 과녁 모양 · 접근 문구에 「프로그램 보고(app) — msg」) · `seatrows.ts` done = 대기 + 「확인」 꼬리표 · 교차 핀 열쇠 12 → 15.

### ③ 가벼운 시작(노브 · 기본값 = 현행)
- 손잡이 `boot_fleet`: env `CYS_BOOT_FLEET` (full|light) > `~/.cys/policy.json` 의 `boot_fleet`(**full 만** 받음 — 좌석도 쓰는 파일이라 함대를 줄이는 값은 받지 않는다 · knobs.rs 규칙) > 기본값 **full**(= 1.1.15 동작).
- light = `cys boot` 빈 편성 + 안내 1줄 · `javis_orchestra.effective_required_roles` = [] · `_shared_verdict_deficit`·`_required_roles_from_orchestra` 가 빈 요구를 결손 0 으로 · `javis_formation` = master 만 · `team_roster_note` 파생. `BOOT_PLAN`·`REQUIRED_ROLES` 상수는 그대로(H-PRED-7 파리티 유지).
- 팩 지침(별도 커밋 59e9d13f1): MASTER ④ 문단을 줄여 쓰고 손잡이 1구절(433 → 501 B · 상한 +68 B: MASTER 86,693 · CEO 102,179) · CEO_TEMPLATE 재합성 · 발행 해시 표 재생성 · MASTER_CORE/CEO_CORE §0-B 해시 + 노드 요지 1구절(`core_inject verify` 둘 다 ok).

## 2. 커밋
| 커밋 | 내용 |
|---|---|
| d56c4dd3f | ② 7501 응답·수신 · done · 뜻·출처·근거 · 종료 지움 · explain-state · UI |
| c28dd55c8 | ② codex 1R 4건 수리 |
| b20efc150 | ③ 손잡이 boot_fleet(Rust·orchestra·formation) |
| 59e9d13f1 | ③ 팩 지침 별도 커밋(MASTER ④ · CEO 재합성 · 해시 표 · CORE 해시·요지 · 상한 +68 B) |
| d8854d9ce | ② 2R · ③ 1R 수리 |
| b97964353 | ③ codex 3R MINOR(주석) |


## 3. 원작자 파일 변경 줄(NFR-F3 예외 · 브리프 「데몬 변경 허용」)
`git diff -U0 dea2e1853` 머리 기준(+시작줄(줄 수)). 전부 **추가**이고 기존 줄의 뜻을 바꾼 곳은 아래 ★ 2곳뿐이다.
- `src/bin/cysd/state.rs`: +2733(3) Surface 필드 2 · +8351(2) 생성자 · +8447(2) 좌석별 켬 판독 · +8626(18) reader 7501 스캔·응답(osc 알림 스캔 뒤 · `ingest_output` 앞) · +8651(5) EOF 지움.
- `src/bin/cysd/handlers.rs`: +7810(2) `surface.list` 의 `program_status_diag` 1키.
- `src/bin/cysd/governance.rs`: +1075(6) 에이전트 종료 래치 첫 통지 직후 7501 기록 지움.
- `src/bin/cysd/activity.rs`: +233·+250·+267·+282 열거 값 추가 · +1380(6)·+1399(7) ★`spawn_observer` 의 끔 판독을 `observer_enabled()` 로 추출(뜻 동일) + 관측기 Drop 가드(`running` 내림) · +1487(85) `wire` → `wire_with` 덧씌움(★`wire` 의 반환이 7501 기록이 있을 때만 바뀐다 · 없으면 `observation_seq` 에 판 계수 0 → 종전과 바이트 동일) · +1605(3) `wire_at` json 에 meaning·source·program_status(null) 3키.
- `src/bin/cysd/main.rs`: +58 `mod program_status;`.
- `src/bin/cys.rs`: +992(9) `DaemonAction::ExplainState` · +3659 자동 기동 금지 목록 · +12735(44) boot_fleet · +14865~14930 run_boot 편성 선택·light 안내 · +21171(90) explain-state · +59591(75) 시험 2모듈.
- 새 파일(원작자 파일 아님): `src/bin/cysd/program_status.rs` · `program_status_tests.rs`.


## 4. 시험
기준선 = dea2e1853. 전체 기준선 실행은 하지 않았다 — 개수는 diff 로 산출(이 가지가 더한 `#[test]` 24 · 지운 것 0 · UI `it(` 6). 붉은 것은 전부 **단독 재실행 + 기준 트리 대조**로 판정했다(공지 ② · 부하 표기).

| 대상 | 최종 결과(b97964353 / d8854d9ce) | 비고 |
|---|---|---|
| `cargo test --bin cysd`(전체 · threads 4) | **3352 통과 · 1 실패 · 17 무시**(d8854d9ce) — 기준 산출 3351 = 3370 − 새 19 | 실패 = `trash::tests::test_gui_input_latency_during_slow_preview`(지연 3배 문턱 · 290ms vs 기준 55ms) → 단독 재실행 **통과 2회**(19.4s 부하 13 · 22.0s 부하 10) · 1회차(d56c4dd3f)도 같은 시험 1건만 |
| `cargo test --bin cys`(전체) | **801 통과 · 0 실패 · 2 무시**(b97964353) | 1회차(혼합 트리) 800/1 = `dbg_r12_init_pack_wires_profile_skill_links` → 최종 트리 단독 통과 · 전체 2회차 0 실패 |
| 새 Rust 시험 | cysd `program_status` **19/19** · cys `boot_fleet` 3/3 · `explain_state` 2/2 | |
| UI `bun test`(전체 123파일) | 1회차 3752 통과 · 1 실패(시간 문턱 5,000ms 에 5,432ms) → 2회차 **3753 통과 · 0 실패** · 88 skip | |
| `tsc`(typescript@7.0.2 고정) | rc 0 · 음성 대조(타입 오류 주입) rc 1 | 거짓 초록 아님 |
| self-test | orchestra · bootstrap · formation OK | |
| `core_inject verify` | MASTER ok(15절) · CEO ok(26절) | |
| CI 팩 단계(ci-branch.yml 본문 그대로 · CYS_* 제거 env) | CEO 재합성 게이트 rc 0 · 레인·상태 격리군 rc 0 · 자원 게이트 rc 0 · 수용 검체 4종 rc 0 · **mac 본 단계**: `set -e` 판 3회 모두 서로 다른 시간 문턱 항목에서 멈춤 → 멈추지 않는 사본(`-e` 제거 · 묶음별 rc 기록 · 그 밖 바이트 동일)으로 **151묶음 중 147 rc 0 · 4 rc 1** | 4 = `test_hook_r34`(시한 1s·3.0s 상한에 3.1~3.4s) · `test_role_authority`(backoff.log 미생성) · `test_role_authority_shell`(같은 묶음 단독 즉시 통과) · `test_owner_desk`(병렬 flush 경합) — 넷 다 이 가지가 바꾼 파일을 **참조하지 않음**(grep 0) · hooks 폴더 무변경 · 최종 트리·기준 트리 각 2회 단독 **전부 rc 0**(부하 6.5) |
| 뮤턴트(환경값 분기 1빌드 · 사본 폴더) | **9/9 잡힘** — M1 응답 제거 → `live_seat…` · M2 순번에서 판 제거 → `version_moves…` · M3 쌍마다 한도 끔 → `duplicate_key…` · M4 봄 끔 → `overlay_seen…` · M5 관측기 관문 끔 → `no_answer…` · M6 policy light 받음 → `env_beats_policy…` · python light 결손 분기 끔 → orchestra self-test · UI done 꼬리표 제거 → `seat row: done…` · UI done 출처 검사 제거 → `malformed overlays…` | 각 뮤턴트가 **그 시험 하나만** 붉힘 · 되돌림 확인(`P1M` 0건) |
- 시험 사각(정직 고지): governance 에이전트 종료 래치의 「지움」 호출 자체를 붉히는 시험은 없다(저장소 `wipe` 는 단위 시험 있음 · 호출 1줄).


## 5. codex
| 회차 | 대상 | 판정 | 처분 |
|---|---|---|---|
| ② 1R | d56c4dd3f | NOT_CONVERGED · MAJOR 2(관측기 끈 데몬 응답 · 같은 순번 거부) · MINOR 2(중복 키 한도 우회 · app 상속) | 4건 수리 c28dd55c8 |
| ② 2R | c28dd55c8 | NOT_CONVERGED · MAJOR 2: ⓐ 관측기 스레드 실패/사망 시 응답 → 수리(running 관문 + Drop 가드) · ⓑ 세대 넘는 순번 비단조 → **설계대로**(UI 순번 대조는 세대 안 · 관측기 자신이 세대마다 0) — 3R 이 「by design verified」로 확인 | d8854d9ce |
| ③ 1R | b20efc150·59e9d13f1 | NOT_CONVERGED · BLOCKER 1(좌석이 policy.json 으로 light) · MAJOR 1(bootstrap 이 빈 요구를 손상으로 읽음) · MINOR 3(self-test 밀폐 · 안내 문구 · 정규화) | 5건 수리 d8854d9ce |
| 재검(② 3R · ③ 2R) | d8854d9ce | 앞선 7건 **전부 CLOSED** · 새 BLOCKER/MAJOR 0 · MINOR 1(python 주석) → NOT_CONVERGED | 주석 수리 b97964353 |
| 최종 | b97964353 | **CONVERGED**(주석만 · 실행 줄 변경 0 확인) | |
- 01:0x 1회 = codex 사용 한도 오류(실패로 세지 않음 · 공지대로 01:31 뒤 재시도 · 사용량 5h 6% 확인 후 호출).
- 범위 밖으로 판단해 올리지 않은 것: 2R ⓑ(세대 넘는 순번) — 근거 위 표. 그 밖 없음.


## 6. 함정·한계(정직 고지)
- Windows: 허더 주석에 「Windows 기본 ConPTY 가 7501 응답을 삼킨다」(재지 않음 · 11-01 보고서). 우리 윈 좌석에서 질의 전달·응답 전달 여부는 **미측정** — VM·윈 실기 단계에서 `cys daemon explain-state` 의 질의 응답/보고 계수로 바로 판별된다(응답 0·보고 0 이면 종전 화면 판정과 같다 = 퇴보 없음 · 응답했는데 보고 0 이면 제목 표지만 잃는 퇴보 → 그때 윈은 끄는 분기 필요).
- 배달·승인·순환 판정은 **바꾸지 않았다**(표시 전용 · 그림자 단계). 「blocked 면 입력 거절 · done 이면 배달 간격 단축」은 후속 판단.
- 이미 떠 있는 Claude 좌석은 새 데몬으로 바뀌어도 시작 질의를 다시 하지 않는다(시작 때 1회) — 새로 뜬 좌석부터 적용된다.
- ③ 기본값 근거의 한계: 표준 벤치 4회차 · 「기본 자산 전체」 켬/끔 비교라 부트만 떼어 잰 값이 아니다.

## 7. 재현
- 7501 실측: `python3 docs/evidence/borrow23-1119/probe7501.py reply <out>` (PROBE_EXTRA="--permission-mode default --no-chrome" 로 권한 창 갈래).
- 시험: `cargo test --bin cysd program_status` · `cargo test --bin cys boot_fleet` · `cargo test --bin cys explain_state` · `cd ui && bun test src/roleactivity.test.ts` · `python3 cysjavis-pack/bin/javis_orchestra.py --self-test`.

---

## 8. 델타 — 독립 검증 REVISE 고침 1회(master#afc55645 · 2026-11-20)

검증 원문 = `/Users/oogisoogi/axdev/workers/cysr-1116-borrow23-verify-1119/VERDICT.md`. 처분과 고침:

| # | master 처분 | 고침 | 시험 |
|---|---|---|---|
| V-1 MAJOR | (가) 질의에 답한 생애의 보고만 | `Store.life_answered`(질의 응답 때 true · 전부 지움 = 에이전트 종료·PTY 종료·RIS 때 false) · 묻지 않은 보고 = `unsolicited` 계수만 · `program_status_diag.unsolicited_reports` · explain-state 「묻지 않고 스스로 보고(받지 않음 — 화면 판정 사용 · 예: codex)」 분기 · 「화면 판정만 쓴다」 줄은 응답 0 ∧ 무질의 0 일 때만 | `codex_unsolicited_reports_are_ignored_byte_for_byte`(검증 좌석 codex 0.167 실측 바이트 그대로 → 덧씌움 0 · unsolicited 4) · `answered_life_ends_on_total_wipe` |
| V-2 | (가)로 닫힘 확인 | 위와 같음 | `shell_spoof_without_query_changes_nothing` · `live_shell_seat_printf_spoof_is_ignored`(실 PTY 셸 좌석 printf → 기록 0) |
| V-3 | 지침 1~2줄 + CSO 여는 명령 | MASTER ④: light 때 빠지는 것(①순환 집행자 ②`cycle-agent --verifier worker` 검증자 ③데몬 경보 CSO 큐 적재 ④죽은 좌석 회수·원장 고아 정리) + `cys launch-agent --role cso --agent claude` · 진실원 = 데몬 · 틀린 안내 「`CYS_BOOT_FLEET=full cys boot`」 제거(V-4 뒤로는 cys boot 가 자기 env 를 안 씀) · 238 → 500 B · 상한 MASTER 86,955 · CEO 102,441 · CEO 재합성 · 해시 표 · CORE §0-B 해시 + 요지 | gen --check GREEN · 해시 --check OK · core_inject verify 둘 다 ok |
| V-4 | 진실원 한 곳 = 데몬 | lib `boot_fleet_decide`(데몬 결정 · 순수) · `boot_fleet_resolve`(소비자 해소 · 순수 · 내 env 는 어떤 경우에도 안 씀 · 다르면 경고) · cysd `knobs::boot_fleet()` 기동 때 고정(로그 `[cysd] boot_fleet=…`) · RPC `system.boot_fleet` · 좌석 env 빌더가 호출자 env **뒤**에 `CYS_BOOT_FLEET`·`CYS_BOOT_FLEET_DAEMON` 도장 · 부트 감독자 자식도 도장 · `cys boot` = RPC(없으면 도장 → 기본 full) · python = 도장만 | Rust `half_light_seat_env_is_ignored_and_warned` · python self-test 반쪽 light 단언 · 실측: 좌석 env 만 light → `('full','no-daemon')` + 경고 · 요구 역할 cso·worker 유지 |
| V-5 | 주석 고침 | explain-state 주석 = 자동 기동 안 함 | — |
| V-6~V-9 | 기록 | 아래 | — |

기록(V-6~V-9 · 미고침): V-6 Claude `clear` 직후 다음 보고까지 정직한 unknown 틈(실측 0.68s~7s) · V-7 done 의 「봄」은 사람 입력만(원격 운영 좌석엔 「확인」이 남을 수 있음) · V-8 윈 ConPTY 플래그에 PASSTHROUGH 없음 · conpty.dll 사이드로드 없음 → 실기 판별 대기 · V-9 질의 응답은 질의를 낸 어떤 좌석에도 간다(셸에서 질의 바이트를 먼저 내고 보고를 내면 받는다 — DSR 와 같은 계급 · 남는 위조 길 정직 고지). (다) 「화면 입력 대기가 7501 idle/working 을 이김」 = 1.1.17 기록. Claude 좌석 안 도구 출력 ESC 흐름 = 미측정.
검증 좌석이 알린 부작용(codex 관리형 데몬이 0.170 을 스스로 받음) = master 판단 사안(이 좌석은 손대지 않음).

### 8-1. 고침 회차 커밋 · 시험

| 커밋 | 내용 |
|---|---|
| bde08cc76 | V-1·V-2·V-4·V-5 코드 |
| 2784a586f | V-3 팩 지침(별도) |
| (다음) | V-4 배선 시험 — python `boot_fleet()` 도장만 · Rust `boot_fleet_wire` 순수화 |
| (다음) | V-3 후속 — ④ 문단 줄 수를 기준과 같게(§2 줄 번호 핀 · 상한 래칫 MASTER 86,949 · CEO 102,435) |

| 대상 | 결과 |
|---|---|
| `cargo test --bin cysd` 전체(bde08cc76) | **3357 통과 · 0 실패 · 17 무시**(새 시험 23) |
| `cargo test --bin cys` 전체(bde08cc76) | **802 통과 · 0 실패 · 2 무시** · 배선 시험 추가 뒤 `boot_fleet` 5/5 |
| cysd `program_status` | 23/23 |
| CI 팩 단계(본문 그대로 · CYS_* 제거) | CEO 재합성 rc0 · 격리군 rc0 · 수용 4종 rc0 · 자원 게이트 rc1 = `test_resource_gate_product_cpu`(`ps timeout 1.5 s` 시간 문턱) → 단독 rc0 · mac(멈추지 않는 사본) 151 중 149 rc0 · 2 rc1: ⑴ `test_event_inject` = **이 가지 원인**(④ 문단 4→5줄로 §2 줄 번호가 밀림) → 줄 수 복구 뒤 단독 rc0 ⑵ `test_hook_r34`(시한 1s 항목) = 같은 시각 기준 트리도 붉음(FAIL 4 대 3 · 부하 30 · hooks·시험 파일 무변경) — master 공지의 「새 실행 파일 첫 exec 검사」 계열 |
| 지침 수정 뒤 단독 | `test_event_inject`·`test_cso_directive_rev`·`test_bootv2_doc_contract`·`test_core_inject`·`test_default_fleet_formation` rc0 · self-test 3종 OK · core_inject verify 둘 다 ok · gen --check GREEN · 해시 --check OK |
| 뮤턴트(이번 회차) | python `boot_fleet()` 이 좌석 env 를 먼저 읽기 → 처음엔 **안 잡혔다**(순수 함수만 시험) → 배선 단언 추가 뒤 잡힘(self-test FAIL) · Rust 배선은 `boot_fleet_wire` 순수화 + 시험 |
- codex 2R(②③ 고침분) = master 대기열(06:29 뒤 · 이 좌석은 호출 안 함).
