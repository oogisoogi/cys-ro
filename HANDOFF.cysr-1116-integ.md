# HANDOFF — 1.1.16 통합 가지 조립 (TICKET=cysr-1116-integ-1118)

> ⚠【경고 · 발행 전 필수】 팩 해시표(`src/released_directive_hashes.rs` · `cysjavis-pack/directives/RELEASED_MASTER_DIRECTIVE.sha256`)에 **1.1.15 지침 바이트가 없다**(MASTER `793e143f…` · CEO `1a9ebfb5…` = 3a095c4e 의 바이트). 원인 = 이 기기에 `v1.1.15` 태그가 아직 없고, 생성기는 「발행 계열 태그 + 지금 작업 트리」만 읽으며 추가 입력 옵션이 없다. → **1.1.15 태그(11-21 예정)를 만든 뒤 이 가지에서 `python3 scripts/gen_released_directive_hashes.py` 재생성 · 커밋**해야 1.1.16 설치기가 손대지 않은 1.1.15 사본을 알아본다(§3).

- 좌석 worker-2(surface:2168 → 06:53 재시작 뒤 surface:2171) · 브리프 = spawn 경로(원장 2026-11-18T05:40:24 · `master/briefs/2026-11-18-cysr-1116-integ.md` · body_sha256 `ff359b9d…` = 파일 끝 줄바꿈 뺀 값과 일치) · 추가 지시 master#a55416cb(R1 갈래 표지) · master#b9752e56(재개 + fix/cc-popover-z 합침) · master#e28c3581(재시작 고아 정리) · master#eaa2b355(fix/restart-confirm 합침) — 넷 다 원장 대조 성립(대상·submitted yes·session_jsonl_nonce)
- 작업트리 `~/axdev/.wt/cys-1116-integ` · 가지 `integ/1116` ← 3a095c4e(1.1.15 후보 integ/1115-r2 머리)
- push · 서명 · 발행 · 설치 · 이 기기 앱 교체 · 실사용 데몬/마스터 접촉 = 0(시험 = `env -i` 격리 HOME/TMPDIR · cargo 1건씩 · `CARGO_BUILD_JOBS=6` · `--test-threads=4`)

## 1. merge 커밋 목록(순서대로 · 전부 `--no-ff`)

| merge 커밋 | 원 가지 · 머리 | 충돌 |
|---|---|---|
| 963c36e2 | `integ/1116-vendor` 1c4c07f6 | 없음 |
| 668c7aed | `integ/1116-backlog` 8bdd08ad | 없음 |
| 75dc2640 | `feat/ui-slice3` 43b44ea4(조각 1 3a012bf4 포함) | 없음 |
| d858abb3 | `feat/ui-slice4` fa400dda(팩 지침 4d20d25a·e1cd0f76·12e8bc95 포함) | **6파일**(§2) |
| 1ccfd1d2 | `fix/cc-popover-z` d8210ab4(master#b9752e56) | 없음 |
| 79a56603 | `fix/restart-confirm` 7df374bc(master#eaa2b355 · 「↻ 재시작」 진입 확인 1회 · 데몬/Rust 변경 0) | 없음 |

- 남은 것: backlog 재검(2167) 새 지적 R1~R3 고침(2169→2172 · `integ/1116-backlog` 8bdd08ad 위 새 커밋) — master 지시 뒤 추가 병합(master#a55416cb).

## 2. 충돌 해결 표(d858abb3 · 두 쪽 동작 모두 살림 · 한쪽 버리기 0)

`git show --remerge-diff d858abb3` = 자동 병합 대비 해결 차이 6파일(사본 `docs/integ-1116/codex-r1-prompt.md` 끝). 단순 나열이 아닌 덩어리만 줄마다:

| 파일:줄(d858abb3) | 무엇을 살렸나 |
|---|---|
| `ui/src/views/core.ts:14~16` import | 단순 나열 — 조각 3(msgstep 새 이름들·autostep) + 조각 4(ConfirmBook) |
| `ui/src/views/core.ts:101~104` Deps | ★두 조각이 **같은 이름 `listen` 을 다른 꼴로** 넣음(조각 3 = `listen(name, handler) → Promise<해제>` · 조각 4 = `listen(fn) → 해제`) → 조각 4 것을 `listenDaemon(fn)` 으로 이름만 바꿈. 두 구독 모두 대화 화면 attach~detach 동안 산다 |
| `ui/src/views/core.ts:177~189` 필드 · `:222~250` attach/detach | ★자동 병합(충돌 표시 없음)이 두 조각의 구독 해제 필드를 **한 필드 `unlisten` 으로 합쳐** 조각 4 구독이 먼저 그 칸을 채우면 조각 3 `startListening` 이 `if (this.unlisten) return` 으로 **시작조차 안 하는** 숨은 결함 → 조각 4 칸을 `unlistenConfirm` 으로 가름 · detach 가 둘 다 푼다 |
| `ui/src/views/core.ts:645~650` poll 세션 읽기 조건 | 합집합: `(활동 바뀜 ∧ (기다리는 말 ∨ 쉬게 됨[조각 4 · 마스터가 스스로 낸 물음])) ∨ (기다리는 말 ∧ 조회 사이 새 출력[조각 3 seed 370])` |
| `ui/src/views/core.ts:676~695` initOffset | 조각 3 의 상한·세대·`ok/none/stale` 구조 유지 + ok 갈래에 조각 4 `confirm.startSession(…)` |
| `ui/src/views/core.ts:734~740` 파일 줄어듦(reset) 갈래 | 단순 나열 — `pendingUser = []`(조각 3) + `confirm.resetSession()`(조각 4) |
| `ui/src/views/core.ts:393` freshBounded 반환형 | `feed?`·`org?` 칸 추가(실행 값은 원래도 그대로 실려 조각 4 `confirm.observe` 에 감 · 형만 정직하게) |
| `ui/src/views/chat/index.ts:126·150~160` | 조각 3 logOrder 고리(안 묶인 답 시각순) 안 두 곳에 조각 4 `masterBubble(text, uuid)` uuid 인자 · 조각 3 autos 줄 뒤 조각 4 `band.paint()` |
| `ui/src/views/index.ts:45~63` | 조각 3 `listen` + 조각 4 `listenDaemon`·`goView`·`defaultSlug` · `confirm.test.ts:61` 대역 키 `listenDaemon` |
| `ui/src/views/views.css:71~` | 단순 나열 — 조각 3 `.cv-auto` + 조각 4 띠 스타일 |
| `src-tauri/src/viewcore.rs:199~203` 문서 주석 · `:234~237` | ★**의미 충돌 고침**: 조각 3 이 새로 넘기는 「글 없는 고리」(`role:"link"` · attachment·system 등)에 조각 4 의 줄 위치 `at` 이 없었다 → 조각 4 앞 훑기(`confirm.ts:151` scanStep)는 끝을 넘는 토막에 `at` 없는 레코드가 하나라도 있으면 「다 훑음」을 확정하지 않으므로, 실제 기록(훅 글 등 고리가 흔함)에서 확인 띠가 「확인할 것 살펴보는 중」에 머문다 → 고리에도 `at`(바이트 수 · 글 0자 · NFR-S3 그대로) · 시험 `chunk_parser_reads_whole_lines_only_and_keeps_text` 에 단언 1줄 |

- 시험: `bun test ./src/views` = **286 / 0**(= 조각 3 212 + 조각 4 177 − 공통 조각 1 103 · 정확히 합) · tsc rc 0 · cargo viewcore(§4).
- **codex 1R(gpt-5.6-sol high · 읽기 전용 깨끗한 작업트리 · `</dev/null` · 대상 = remerge diff + 닿는 곳) = ACCEPT · issues 0**(원문 `docs/integ-1116/codex-r1.json` · 사본 `~/.cys/pack/round/_reviews/cysr-1116-integ-1118-r1-codex.json`). 확인 항목: 두 구독 수명·경합(listenGen · dead 표지) · poll 조건 = 정확한 합집합 · initOffset/reset · link+at 이 msgstep(applyRecords)·confirms(markersOf) 에서 의미를 바꾸지 않음 · uuid 전달 · band.paint 위치.
  - 첫 호출은 개인정보 관문(`codex-pii-gate`)이 작업트리의 미추적 Tauri 런타임 사본(src-tauri/runtime 등 · 빌드용 복제)을 걸어 **codex 미호출(rc 5)** → 깨끗한 작업트리(detached d858abb3)에서 다시 = 통과.

## 3. 팩 해시표 처분

- `scripts/gen_released_directive_hashes.py --check` = **OK**(표류 0) · `gen_ceo_template.py --check` = GREEN — 합친 뒤 재생성할 것 없음(커밋 0).
- 3a095c4e(1.1.15) 바이트 직접 잼: `MASTER_DIRECTIVE.md` = `793e143f659714bd…` · `CEO_TEMPLATE.md` = `1a9ebfb520fd7665…` → **지금 표에 둘 다 없음**(조각 4 재생성 12e8bc95 가 「생성 시점 작업 트리」 항목으로 들어 있던 이 1쌍을 새 판으로 바꿨다).
- 넣는 방법을 찾음: 생성기 = 태그 패턴(`v*`·`pack-v*`·`vendor-v*`·`upstream/v*`) + 작업 트리만 · 옵션은 `--check` 하나(전문 읽음) → **추가 입력 길 없음**. 로컬 태그 `v1.1.15` 를 3a095c4e 에 다는 길은 하지 않음 — 11-21 실제 발행 태그와 이름이 부딪히고(발행 커밋이 다를 수 있음) 태그는 모든 작업트리가 공유한다.
- 결론 = 맨 위 경고: **1.1.15 태그 뒤 재생성 필요**. 그때 `--check` 가 표류로 잡는다(태그가 생기면 생성기 출력이 바뀌므로) — 발행 절차에 `--check` 가 있으면 놓치지 않는다.
- 참고(표에 새로 든 4개의 출처 · 정상): MASTER `33d2ab85…`·`bba13992…` · CEO `7cb5542f…`·`15c72552…` = 원작자 태그 v0.15.0/v0.15.1 · v0.14.55/v0.14.56(이 기기에 나중에 받은 태그 · 바이트 등가 표라 넓어져도 오판 0).

## 4. 시험 — 기준선 3a095c4e(임시 폴더 밖) 대비 · 새 적색 0

- 틀 = 스크래치 `runall.sh`(`env -i` · HOME/TMPDIR = `/tmp/i16XXXX` · `CARGO_BUILD_JOBS=6` · `--test-threads=4` · cargo 1건씩 · PATH 에 /usr/sbin:/sbin). 화면 게이트 = `gates.sh`(실제 번들 + 대역 · `cys run --` · playwright 1.60 venv · chromium_headless_shell-1248).
- 기준선 = 3a095c4e 를 임시 폴더 **밖** `~/axdev/.wt/cys-1116-base-1118` 에 둔 사본의 값(vendor 좌석 §10-6 실행 = lib·cys·cysd · 그 밖 대상은 vendor 좌석 첫 실행 `out-base` · 같은 커밋). 이번에 기준선 전체를 다시 돌리지는 않았다(시간 상한) — 대신 HEAD 에 붉음이 나오면 그 시험을 기준선에서 단독으로 돌려 대조하는 방식(이번 최종 실행엔 붉음 없음).
- 대상 머리: 전체 묶음 = 1ccfd1d2(cc-popover-z 까지 · 06:57~) · ui/app 단계는 79a56603(restart-confirm · Rust 변경 0)을 읽음 · 화면 게이트 = 79a56603 번들 · backlog 새 머리 병합(26a41fe1 · 바뀐 Rust = `src/bin/cysd` 만 + `agents.json`) 뒤 = cysd 묶음 다시.

| 대상 | 기준선 3a095c4e | HEAD | 차이 사유 |
|---|---|---|---|
| cargo build --bins --tests | rc 0 | rc 0 | — |
| lib | 1238 · 0 · 2 ign | **1256 · 0 · 3 ign** | +18 = vendor 저널 시험(vendor 1256 와 같음 · backlog lib 수 변화 0) |
| bin cys | 761 · 0 · 2 | **765 · 0 · 2** | +4 = vendor(7d 2 · doctor 2) |
| bin cysd(1ccfd1d2) | 3274 · 1(흔들림 · Locked) · 17 ign | **3303 · 0 · 17** | +28 = backlog 시험(b16·b16fix) · vendor +0(핀 이동) |
| bin cysd(26a41fe1 · backlog 새 머리 뒤) | 3274 · 1(흔들림) · 17 | **3305 · 1 · 17** → 붉음 1 = `pending_requests::c8attempt_persisted_progress_and_chain_are_checked_against_actual_plan`(「persisted impossible progress accepted」) · **단독 3/3 초록**(`out-final/c8-solo.txt`) · 어느 가지도 `pending_requests.rs` 무접촉(3a095c4e..HEAD diff 0줄) = 부하 흔들림 계열(기준선·앞 좌석들의 pending_requests 흔들림과 같은 모듈) | +2 = backlog fix2 시험(`b16_fix2_tests.rs` · 재검 R1·R2 붉음→초록) |
| cys-seatkeep | 49 · 0 | **49 · 0** | — |
| tests/*.rs | hidden 1 · rotate 11 · seat_group 1 · drainhold 4 · win 2종 0 | **같음**(1 · 11 · 1 · 4 · 0 · 0 · 전부 0 실패) | — |
| bun test(ui 전체) | 3451 pass · 0 fail | **3746 pass · 0 fail**(3834 · 123 파일) | + 조각 1·3·4 views 시험 · popover · restart-confirm 시험 |
| `bun test ./src/views` | — | **286 / 0**(합친 직후) | 조각 3 212 + 조각 4 177 − 공통 103 |
| tsc(typescript@7.0.2 · tsconfig.check) | rc 0 | **rc 0** | — |
| cargo `-p cys-app --bin cys-app`(viewcore 포함) | (조각 1 기준 344) | **348 · 0 · 2 ign** | 조각 4 HANDOFF 348 과 같음(고리 at 단언은 기존 시험 안 1줄) |
| 팩 파이썬(wakeup 4종 · radio 297 · computer_control 112 · hook_fail 11/10 · counsel 118 skip3 · agy_door 20 · notes_personal_hooks · dept_chat 3 · phoenix_loop · phoenix_fresh_honest) | 전부 rc 0 · liveness 13 | **전부 rc 0** · liveness 20 | vendor U08 +7 |
| doc-contract(test_bootv2_doc_contract) · test_event_inject | (조각 4 OK · PASS 106) | **rc 0 · rc 0** | — |
| 합성기 `gen_ceo_template.py --check` · `gen_released_directive_hashes.py --check` | — | **GREEN · OK** | §3 |
| scripts/tests/test_*.py | OK 21 · FAIL 1(test_release_trigger_split) | **OK 22 · FAIL 1(같은 것)** | +1 = check_macho_arch · 같은 FAIL = 기준선부터 |
| health run_bootstrap_health.py | 167 pass · 2 fail(H-CLT-1·2) · 1 skip | 전체 실행 165 · **4 fail** · 1 skip → 새 2건 처분 뒤 **H-CLT-1·2 만 남음**(기준선과 같은 ID · 이 기계 설치본 python 선택 환경) | 새 2 = H-SECRET-1(아래 secret 과 같은 줄 · 고침) · H-DETECT-7(검체 크래시 `OSError: Directory not empty: <TMPDIR>/tmp…` = 전체 실행 중 임시 폴더 정리 경합) → 고친 뒤 `--only H-DETECT-7,H-SECRET-1` 단독 = **2 PASS / 0 FAIL** |
| secret-scan --all | clean 2049 | 전체 실행 **1건**(`WORKER_TODO.cysr-cc-popover-z-1118.md:2` 의 홈 절대 경로 — fix/cc-popover-z 가 들여온 줄) → 그 줄의 경로를 「작업트리 cys-cc-popover-z」 로 바꾼 커밋 뒤 **clean 2158** | 통합 좌석 고침 1줄(문서 · 동작 무관) |

화면 게이트(79a56603 번들 · 기준 번들 = 3a095c4e `ui/dist`):

| 게이트 | 결과 | 앞 좌석 값 |
|---|---|---|
| tickrec_gate OFF | **PASS · 새 = 기준 sha `308dd2b91f9a`**(invoke 열·저장소·화면 글자 · 켜짐도 같음) | 308dd2b91f9a(조각 0·1·3·4) — **같음**. 기준을 조각 0 이전 3a095c4e(1.1.15 작업 화면 그대로)로 잡아도 같은 값 · 정보 줄 「가짜 시각 어긋남 14건 · 최대 1ms」 = 조각 4 §13-3 부하 때 본 것과 같은 꼴(판정 밖) |
| chat_gate | **PASS · ok 59 / 0** | 조각 3 59 |
| confirm_gate | **PASS · ok 37 / 0** | 조각 4 37 |
| cc_popover_z_gate(새) | **PASS 4 / 0** | — |
| restart_confirm_gate(새) | **PASS 13 / 0** | — |
| race · focus · seatrows · pillar · seatgroup · rolereuse · stty · nodept · restart · hidden_block | **108 · 72 · 75 · 77 · 8 · 11 · 7 · 16 · 6 · 18 — 전부 0 FAIL** | 앞 좌석들과 같은 수 |

- 1ccfd1d2 번들에서도 같은 15종 PASS(같은 수 · `gates-1ccf/`). 게이트 실행이 커밋된 캡처 PNG 2개(`docs/evidence-cc-popover-z/…` · `docs/evidence-restart-confirm/…`)를 덮어써서 `git checkout --` 으로 되돌렸고, 작업트리에 남긴 `docs/evidence-tabs-sidebar/` 캡처는 스크래치로 옮김(📌 I4).

### 4-1. 06:53 끊긴 첫 실행과 마무리 값

- 첫 실행(d858abb3 · 05:49~)은 06:53 데몬 재시작으로 `tests/*.rs` 중간에 끊김(`out-run1/`): lib 1256/0 · cys 765/0 · seatkeep 49/0 · **cysd 3297 · 6 실패**(seat_proc seatkeep 4 = `handshake_timeout` · `pending_requests::c8attempt_restart…` = `Locked` · `u18_cwd_blocked_observed_under_sandbox_read_deny` = 안쪽 샌드박스 검체 실패). → 처음부터 다시 돈 실행(1ccfd1d2)에서 **cysd 3303 · 0** — 6건 다 재현 안 됨(부하 흔들림 계열 · seatkeep `handshake_timeout`·`Locked` 는 앞 인계서들의 흔들림 꼴).
- 끊긴 실행이 남긴 고아 = 이 작업트리 `target/debug/cysd` 2기(11291 · 22128 · ppid 1) + 그 시험 데몬의 phoenix 파이썬 1기(13554 · ppid 1 · 이 작업트리 `target/debug/runtime/python` · 죽은 시험 소켓) → `ps -o args` 로 경로 확인 뒤 pid 지정 종료(master#e28c3581 · 셋째는 같은 시험의 잔여라 함께 · pkill 0).

## 5. 경합 재측정 — 「쓰는 도중 뜬 승인 창」 8점(조각 1 이월 6 · 브리프 4)

### 5-1. 왜 chat_gate G 만으로는 못 재는가
- `chat_gate.py` G 장면은 **JS 대역 데몬**이다: 거부를 `chat_send` 를 부르는 순간(쓰기 전) 한 번만 판정하고(`refused: C.screen`), 「샘」 = 창이 [쓰기 시각, 쓰기 + 836ms] 안에 뜸으로 센다. 데몬의 Enter·붙여넣기 직전 재판정은 대역에 없다 → 합친 번들에서 다시 돌려도 **lag0 = 화면 문턱 16 · 데몬 거부 0 · 샘 8 · 겹침 없음 7 / lag1000 = 6 · 10 · 8 · 7 — 조각 1 기록과 같은 숫자**(`gates-head/chat-gate-race.json` · 대역 모형 값 · 화면 문턱 동작이 그대로라는 뜻뿐).
- 그래서 **실제 데몬 코드**로 같은 8점을 잼: 측정 전용 시험(커밋 안 함 · 작업트리 `~/axdev/.wt/cys-1116-integ-race` 의 `send_settle_tests.rs` 끝 `integ1116_race_sweep`·`integ1116_r1_feed_only` · `#[ignore]`) — 점마다 새 좌석 → 빈 입력줄 → **앱 대화 화면과 같은 사람 표지 원자 제출**(`surface.send_text` · human · clear_first · refuse_on_approval · machine_origin false = `viewcore::human_send_params` 와 같은 칸) → 응답 뒤 +d ms 에 승인 창을 그림 → 그 순간 Enter 가 이미 쓰였는지 · 거부 사건 단계 · 최종 Enter.
- 실행 = 1ccfd1d2 트리(backlog 8bdd08ad 고침 포함 · backlog 새 머리 f55e6470 은 아직 안 듦) · 격리 env · 2회 반복 · `--test-threads=1`(원문 스크래치 `race-pre.log`).

### 5-2. 8점 × 2회 — 사람 표지 원자 제출

| 창이 뜬 때(응답 뒤) | refuse_on_approval 켬(앱 대화 화면 · 합친 빌드) 1회 / 2회 | 끔(= Enter 직전 재판정 없음 · 고치기 전 등가) 1회 / 2회 |
|---|---|---|
| +0.1초 | Enter 앞 거부 / **붙여넣기 앞 거부** | 창 위 Enter / 창 위 Enter |
| +0.2초 | Enter 앞 거부 / Enter 앞 거부 | 창 위 Enter / 창 위 Enter |
| +0.3초 | Enter 앞 거부 / Enter 앞 거부 | 창 위 Enter / 창 위 Enter |
| +0.4초 | Enter 앞 거부 / Enter 앞 거부 | 창 위 Enter / 창 위 Enter |
| +0.5초 | Enter 앞 거부 / Enter 앞 거부 | 창 위 Enter / 창 위 Enter |
| +0.6초 | Enter 가 먼저(겹침 없음) / Enter 앞 거부 | Enter 가 먼저 / 창 위 Enter |
| +0.7초 | Enter 가 먼저 / Enter 가 먼저 | Enter 가 먼저 / Enter 가 먼저 |
| +0.8초 | Enter 가 먼저 / Enter 가 먼저 | Enter 가 먼저 / Enter 가 먼저 |
| **합계** | **창 위 Enter 0 / 16** · 거부 11(붙여넣기 앞 1 · Enter 앞 10) · 겹침 없음 5 | **창 위 Enter 11 / 16** · 겹침 없음 5 |

- 읽는 법: 「Enter 가 먼저」 = 창이 뜨기 전에 이미 Enter 가 들어가 말이 제출됨(창의 「1. Yes」 를 누른 것이 아님 · 오승인 아님). 이 측정 좌석에서 Enter 는 응답 뒤 약 0.52~0.67초에 들어갔다(조각 0.5 VM 실측 +0.54초와 같은 범위). 조각 1 표의 「+0.6~+0.8초 샘」 은 대역이 원자 제출 길이를 836ms 로 가정한 값이라, 실제로 Enter 뒤에 뜬 창까지 샘으로 셌던 것이다.
- **결론: 쓰는 도중 뜬 창(Enter 전에 뜬 창) = 합친 빌드에서 전부 데몬이 막음(11/11) · 고치기 전 등가 동작은 11/11 샘.**
- ⚠한계(정직): 시험은 창을 데몬 화면 해석기에 **바로** 그린다(실제 Claude 의 그리기 → PTY → 해석 지연 0). 실제로는 「창이 PTY 에 나왔지만 데몬이 아직 해석 못 한」 짧은 틈과 「마지막 탐침 ~ CR 바이트」(1ms 미만) 틈이 남는다 — 진짜 Claude 걷기(0.5 재개 조건)에서 잴 몫. 「끔」 열은 같은 HEAD 에서 옵션만 끈 것(옛 판 바이너리 아님 · 응답 뒤에 뜨는 창이라 핸들러의 쓰기 전 판정은 두 열에서 같음).

### 5-3. ⚠R1 갈래 — 「backlog 고침 전」(master#a55416cb · 1ccfd1d2 = backlog 8bdd08ad 까지)

창은 없고 feed 승인 대기 항목만 **보내기 전부터** 있는 좌석 · raw `cat` 기록기 좌석으로 PTY 에 실제로 간 바이트를 봄 · 3회씩.

| 입력줄 | 응답 | PTY 에 간 바이트 | 거부 단계 | 데몬 계수(입력줄·사람 몫) | 뜻 |
|---|---|---|---|---|---|
| 빈 줄 ×3 | `sent:true` | `15`(Ctrl-U 1바이트)뿐 | 붙여넣기 앞 | (0, 0) | 쓰기 전 판정이 feed 를 안 봐 통과 → Ctrl-U 를 쓴 뒤 거부 · 빈 줄이라 해는 없음 |
| 사람 초안 「사람 초안」 ×3 | `sent:true` | `15`뿐 | 붙여넣기 앞 | (13, 13) | **Ctrl-U 가 실제 화면의 사람 초안을 지웠는데 데몬은 초안이 그대로 있다고 셈**(계수 복원) = R1 그대로 재현 |

- backlog 새 머리 f55e6470(28b74eaf 「원자 제출 쓰기 전 판정 = feed 합집합」)이 이 갈래를 **쓰기 전 거부(바이트 0)** 로 바꾼다 — 그 좌석의 붉음→초록 시험(`b16_fix2_tests.rs`)은 합친 머리 26a41fe1 의 cysd 묶음에 들어 있다(§4). 같은 측정 시험을 26a41fe1 에서 다시 돌리는 것은 시간 상한(08:45) 안에 못 했다 — 고친 뒤 동작의 근거는 지금 그 좌석 시험(26a41fe1 cysd 묶음에서 초록)뿐 · 측정 작업트리를 26a41fe1 로 옮겨 `cargo test --bin cysd integ1116_r1_feed_only -- --ignored --nocapture` 1회면 표가 채워진다(📌).
- 대화 화면 쪽: 화면 문턱도 feed 승인 항목(마스터 좌석)을 보고 붙잡지만(조각 1 수용 브2) 그 조회와 쓰기 사이 틈·마스터 아닌 좌석 대상 원자 제출에는 데몬 판정이 유일한 방어였다.

## 6. 📌 모음 — 각 가지의 덧붙임(실행 안 함 · 판단 = master)

「원 좌석 표기」 = 그 인계서가 직접 적은 판(없으면 「—」). 「통합 좌석 제안」 = 내가 붙인 가름(근거 1줄) — **판단은 master**. 「1.1.16 전」 = 1.1.16 발행 전에 손이 필요한 성격, 「1.1.17」 = 미뤄도 1.1.15 보다 나빠지지 않는다고 원 좌석·codex 가 적은 것, 「설계/측정」 = 코드 아님.

### 6-1. 이 티켓(통합)에서 생긴 것

| # | 내용 | 통합 좌석 제안 |
|---|---|---|
| I1 | ★1.1.15 태그 뒤 해시표 재생성(맨 위 경고 · §3) | 1.1.16 전(발행 차단 성격) |
| I2 | 해시 생성기에 「추가 git ref 입력」(예 `--extra-ref <커밋>`) — 태그 전 통합 가지에서도 직전 판 바이트를 넣을 길 | 1.1.17(도구) |
| I3 | 대화 화면 데몬 사건 구독이 둘(조각 3 `listen` · 조각 4 `listenDaemon`) — 같은 `daemon-event` 를 두 번 구독 · `default_socket_slug` 도 두 번 부름. 한 구독으로 합쳐 두 처리기에 나눠 주기(동작 같음 · 조각 2 「고리 한 벌」 과 같은 성격) | 1.1.17 |
| I4 | 화면 게이트가 작업트리에 `docs/evidence-tabs-sidebar/` 캡처를 남긴다(이번엔 스크래치로 옮김) — 게이트 출력 경로를 TMPDIR 로 | 1.1.17(시험 위생) |
| I5 | codex 개인정보 관문이 빌드용 미추적 Tauri 런타임 복제(`src-tauri/runtime` 등)를 막는다 — 리뷰는 깨끗한 작업트리에서(이번 대응) · 관문 안내문에 그 길을 적을지 | 운영(도구) |

### 6-2. `integ/1116-vendor`(HANDOFF.cysr-1116-vendor-import.md 📌 · §8 · §10)

| # | 내용 | 원 좌석 표기 | 통합 좌석 제안 |
|---|---|---|---|
| V1 | 저널 묶음 전까지 부서 있는 기기에서 팩 단독 자동 업데이트를 멈출지(판정표 §6 결정 1) — 이 가지가 1.1.16 으로 나가면 그 게이트의 근거가 사라짐 | — | 1.1.16 전(결정만) |
| V2 | codex 5R minor 1(링크 되살리기 재중단 창) · 2(write_journal nofollow 판독) · 3(부트 설치의 팩 밖 시드를 잠금 밖으로) · 4(비 UTF-8 링크 = 적용 거부 · 안전) · `.user.tmp-<pid>` 잔여 | 1.1.17 후보 | 1.1.17 |
| V3 | 윈도우 실기 끊김 재현 1회(레인 저널 · LockFileEx · 링크 거부) | — | 측정 |
| V4 | F4 값싼 가름(옛 저널 백업 해시가 본부와 한 건도 안 맞으면 옮기지 않고 안내) | 1.1.17 후보 | 1.1.17 |
| V5 | F3 · F2(나) · codex 1R minor ①②(1.1.15 부서 수동 쓰는 이 ↔ 부서 데몬 · 의도 줄 뒤 사용자 권한만 되돌림) | 기록(나빠지지 않음) | 1.1.17 |
| V6 | 공장 초기화가 `.pack-journal.d` 를 옮길 때 열린 레인 잠금(유닉스 inode 갈림 · 윈도우 이동 실패) — 초기화가 데몬을 먼저 멈추는지 미확인 | — | 1.1.17(확인 1회) |
| V7 | F7 ①(`javis_formation.py:207`·`javis_cycle_autopilot.py:230` 정지 표지 `os.path.exists` = U08 과 같은 꼴) · `javis_radio.py paused_now()` 같은 꼴 | — | 1.1.17 |
| V8 | F7 ④ 1.1.16 → 1.1.15 되돌림 절차에 「레인 저널 남았는지 확인」 한 줄 | — | 1.1.16 전(문서 1줄) |
| V9 | codex 2R minor: 공용 잠금 실패 뒤 옛 저널 부재 검사가 원자적이지 않음(제한 재시도 또는 세대·레인 표식) · F2 권한만 되돌린 사용자 시험 | — | 1.1.17 |
| V10 | U05 업데이터 tarball(`make-darwin-updater-tarball.sh`) 칩 검사 미배선 · LSMinimumSystemVersion 10.13 vs 진입점 11.0 경고 | — | 1.1.17 |
| V11 | 러너 `realops.rs` recover_pack_at 의 사용자 트리 복원과 팩 되돌림 상호작용 미측정 | — | 측정 |
| V12 | 1.1.15 옛 공유 저널 올림 = 보수 규칙(kept/ 보관 후 되돌림 · 권한 못 되살림) — 끊긴 사이 예약 작업은 사람이 kept/ 에서 다시 넣어야 할 수 있음 | 한계 기록 | 1.1.16 발행 노트 1줄 |

### 6-3. `integ/1116-backlog`(HANDOFF.cysr-1116-backlog.md §2·§3·§5·§10-7)

| # | 내용 | 원 좌석 표기 | 통합 좌석 제안 |
|---|---|---|---|
| B1 | census 손 어휘 분석기 → `proc-macro2` 토크나이저(dev-dependency · 공급망 검토) 또는 시험 모듈 끝 명시 표지(10R 상한 격차) | 1.1.17 후보 | 1.1.17 |
| B2 | 열 0 `#[cfg(test)]` 경로의 기존 규칙(비정형 꼴이면 운영 코드를 걷음 · codex 5R major 1) — 공용 그물 변경이라 별건 | 범위 밖 | 1.1.17 |
| B3 | 쓰기 **전** 판정(핸들러)도 feed 승인 항목을 볼지(M2-주 첫 견본) — ★master#a55416cb R1 과 같은 자리(§5 R1 줄) | — | 재검 R1 고침(2169)에 포함 여부 확인 |
| B4 | 원작자에게 돌려줄 수정: claude 어댑터 `approval_patterns` 에 Write 창·계획 승인 창 문구 + 번호 선택 행 + `scope` | — | 원작자 환류 |
| B5 | CLI 순환(`cys.rs` cycle 5/7 원자 clear)·DRAIN 이 새 응답 칸 `submitted:false`·`refused_stage` 를 읽어 즉시 `not_cleared` | — | 1.1.17 |
| B6 | 종전 `tool-permission` 패턴이 scope 없이 화면 전량(답 본문 인용에 승인 스캔 반응 · 디스크 동명 우선이라 고치려면 새 이름 + scope) | 기존 동작 | 1.1.17 |
| B7 | h7 핀에 `InjectRefusing` 생산자 목록 핀 · `watch_wake.rs:313` 각성 Return 의 문·승인 재판정(대상 = master 좌석) | 범위 밖 | 1.1.17 |
| B8 | `b16_atomic` 윈 ignore 제거 — 윈 CI 다음 실행에서 확인 | 그대로 | 측정(윈 CI) |
| B9 | 큐 Return 재전송·Enter 직전 재판정을 공통 함수로 묶지 않음(기계가 다름) | 기록 | — |
| B10 | 재검(2167) R1~R3 고침 = 2169 진행 중 | master 지시 | 1.1.16 전(추가 병합) |

### 6-4. `feat/ui-slice1`(HANDOFF.cysr-ui-slice1.md §11 · §12)

| # | 내용 | 원 좌석 표기 | 통합 좌석 제안 |
|---|---|---|---|
| S1-1 | 전환 단추 접근성(상단바 28px·13px · 설계 §9-2 미달) | 조각 10 걷기 | 조각 10 |
| S1-2 | 대화 화면 3초 조회를 작업 화면 고리와 한 벌로 | 조각 2 | 조각 2(I3 과 같은 성격) |
| S1-3 | 첫 글자 `#`(Claude Code 메모 단축 추정 · 판별 실측 없음) | — | 측정(U21 때) |
| S1-4 | 다시 켠 뒤 붙잡은 말 = 사람 확인(설계 §2-5 를 같은 실행 안으로 좁힘) | 설계 개정 후보 | 설계 |
| S1-5 | 사람 입력 30초 = 내 보내기 포함 → 데몬이 「이 사람 입력은 이 요청」을 응답에 실어 주면 짝짓기 정확 | 데몬 후보 | 1.1.17 |
| S1-6 | 데몬 고침 뒤 chat_gate G 재측정 | 이월 | **이 티켓 §5 에서 함** |
| S1-7 | 설계 문서 개정(§5-1 세션 경로 꼴 · §2-5 400ms → 실측 0.47~0.55초) | 설계 | 설계 |
| S1-8 | 지적 4ⓒ `write_stalled`·`write_failed`(쓰기 0 확정)를 「못 보냄 + 다시 보내기」로 옮길지 | master 판단 | 1.1.17 |
| S1-9 | 지적 6 「화면이 Enter 거부를 모른 채 확인 중」 + 미제출 계수 복원으로 뒷말이 「쓰다 만 글」로 붙잡힘 — 통합 실측 | 통합 때 | §5 참고 · 화면 쪽 짝짓기(S3-1) |
| S1-10 | 지적 7 데몬 승인 창 거부도 사람 입력 시각을 찍음(화면 15초 쉼 실효 없음) | 데몬 후보 | 1.1.17 |
| S1-11 | 지적 10 문턱~쓰기 사이 마스터 죽음 → 빈 셸 실행(데몬 빈 셸 가드가 `!human` 조건) — 사람 표지여도 `refuse_on_approval` 요청이면 빈 셸 거부 | 데몬 후보 | 1.1.16 전 검토(대화 화면이 1.1.16 기본 노출이면) |
| S1-12 | 지적 11 등록 없는 좌석을 대화 화면 대상으로 다룰지 | — | 설계 |

### 6-5. `feat/ui-slice3`(HANDOFF.cysr-ui-slice3.md §11 · §12-6)

| # | 내용 | 원 좌석 표기 | 통합 좌석 제안 |
|---|---|---|---|
| S3-1 | `input.refused_at_write` 에 요청 번호 — ★backlog 고침(§10-2 지적 5)이 사람 길 사건에 `request_id` 를 실음 → **데몬 쪽은 이 통합에 들어옴** · 화면(core.onDaemonEvent)은 아직 좌석·5초 창으로 짝지음 | 데몬 몫 | 1.1.16 전 또는 1.1.17(화면 짝짓기를 request_id 로) |
| S3-2 | viewcore.rs 세션 경로: 심볼릭 링크 cwd(실제 경로로 풀어 슬러그 · codex 재검토 필요) | — | 1.1.17 |
| S3-3 | 조각 5 에 넘길 것: `chat_send{kind:auto}` · `trackAuto` · 적재 전 사건 유실 · 화면 내림 동안 사건 유실 · `queue.expired_parked` | 조각 5 | 조각 5 |
| S3-4 | 같은 말 겹침 막기의 다시 켬 너머 유지(원문 해시만 저장 — NFR-S3 판단) | — | 설계 |
| S3-5 | 설계 문서 개정 후보(세션 읽기 계기 · 답하는 중 · 확인 중 · 겹침 · write_released · expired) | 설계 | 설계 |
| S3-6 | 통합 재측정(= S1-6) | 이월 | **§5** |
| S3-7 | 하네스 uuid 없는 꼴 짝 검사 보강 | — | 1.1.17(시험) |
| S3-8 | 감싼 붙여넣기 안쪽 태그 바뀜(`<\pasted_content`) 되돌려 맞출지 | — | 측정 |
| S3-9 | 둘째 줄 `!` 막기 유지 여부 | U21 때 | 측정 |
| S3-10 | 조각 4 장부가 `role:"link"`·`Reply.at` 을 쓸지 — ★통합에서 link 에 줄 위치 `at` 을 실음(§2) · `Reply.at`(기록 시각)과 `Rec.at`(바이트 위치)은 이름만 같고 다른 칸 | — | 기록 |
| S3-11 | codex 2R 고침분(동률 · 감싼 꼴 분기 · 시작점 세대·stale) codex 미검토 | master 판단 | 1.1.16 전 이종 1회 권함(통합 codex 1R 은 충돌 덩어리만 봄) |

### 6-6. `feat/ui-slice4`(HANDOFF.cysr-ui-slice4.md §11 · §12 · §13)

| # | 내용 | 원 좌석 표기 | 통합 좌석 제안 |
|---|---|---|---|
| S4-1 | FR-C4 OS 알림·앱 배지 | 범위 밖 | 다음 조각 |
| S4-2 | `cys feed push --wait`(permission·question) 항목을 띠에 올릴지 | — | 설계 |
| S4-3 | 사건 구독을 main.ts 배선 1줄로(대화 화면을 끈 동안 온 deadman 도) — 원작자 파일 1줄 대가 | — | 1.1.17(I3 과 함께) |
| S4-4 | ★데몬 지문 계약(§13-7 ①~④ `screen_fingerprint` · `approval_fingerprint_mismatch`) — 지금 데몬엔 지문이 없어 대화 화면 「직접 허락」은 늘 닫힘 | 데몬 티켓 후보 | 1.1.17(데몬) |
| S4-5 | 도우미 지침(팩)에 「되돌릴 수 없는 명령 전에 까닭 한 줄」(사람 승인 대상) | — | 팩 지침(박사님 승인) |
| S4-6 | 팩 지침 D7(⟪팀 제안⟫) | 조각 6 | 조각 6 |
| S4-7 | F7 닫히지 않는 물음 치울 길 · F10 띠 한 번에 하나 → 다른 항목에 거절 | 지시로 📌 만 | 1.1.17 |
| S4-8 | §C 허락 창이 떠 있는 동안 도우미 좌석 주기 출력(idle_secs)으로 A→B 좁히기 — 실측 0 | 측정 대기 | 측정(0.5 재개) |
| S4-9 | `main.rs` 이름 1줄(`viewcore::confirm_reply`) = 원작자 파일 변경 1줄 → 다음 원작자 편입 때 충돌 지점 | 기록 | 편입 때 |
| S4-10 | 해시표 직전 판 1쌍(793e143f·1a9ebfb5) | 통합 때 | **§3 처분**(I1) |

### 6-7. `fix/cc-popover-z` · `fix/restart-confirm`

- 덧붙임 없음(커밋 메시지·TODO 확인). 게이트 `cc_popover_z_gate.py` 는 「수동 실행 · CI 미배선」(파일 머리) — CI 배선 여부만 📌(1.1.17).

### 6-8. 측정 대기(코드 아님 · 진짜 Claude 로그인 필요 — 조각 0.5 M4~M8 재개 조건)

- 대화 화면 수용 8(「안녕」 → 마스터 답) · uuid/parentUuid 사슬(M8) · 긴 붙여넣기 기록 꼴(U20) · 둘째 줄 `/`(U21) · 바쁜 중 붙여넣기(U25) · 답하는 중 실물 · 표식 준수율(U15′) · FR-C5 5분·멈춤 경로(U1) · 윈도 결속 세션 파일(조각 10).

## 7. 증거 경로

- 스크래치(재부팅 시 사라질 수 있음) = `/private/tmp/claude-501/-Users-oogisoogi-axdev--wt-cys-1116-integ/f735c79c-f628-4381-8653-1eb57b0995c2/scratchpad/`: `runall.sh`(시험 틀) · `out-head/`(최종 시험) · `out-run1/`(06:53 재시작으로 끊긴 첫 실행) · `gates.sh`·`gates-head/`(화면 게이트) · `remerge.diff` · `codex-r1-*`
- 저장소 안: `docs/integ-1116/codex-r1-prompt.md` · `codex-r1.json`
- 측정 작업트리 `~/axdev/.wt/cys-1116-integ-race`(미커밋 측정 시험 2개 · 지울 때 `git worktree remove --force`) · codex 사본 작업트리 = 스크래치 `cx/`
- 기준선 작업트리 `~/axdev/.wt/cys-1116-base-1118`(detached 3a095c4e · 이번에 `ui/node_modules`·`ui/dist` 생김 = git 무시 대상)

---

## 8. 델타 — master 판정 후속 4건(master#eff65cb2 · 2026-11-18 09:20~ · surface:2171)

- master msv 973459e2 = 통과(bins 미빌드로 났던 seatkeep/seat_proc 붉음은 빌드 뒤 0). §6 처분 = I1 master TODO · V8·S3-11·S1-11 지금 · V1 결정 메모.

### 8-1. 커밋(973459e2 위)

| 커밋 | 무엇 |
|---|---|
| bb0a73e0 | ③ S3-11 — 조각 3 codex 2R 고침(43b44ea4) 이종 1R 의 REVISE major 고침: 시작점 조회 **거절** = none(예전처럼 보냄) · 시간 초과·세대 밀림만 stale |
| eca3b956 | ④ S1-11 — 사람 표지여도 `refuse_on_approval` 요청은 빈 셸 좌석에 쓰지 않음(no_agent · 큐 0) |
| e3cffabc | ② V8 — `docs/RELEASE-ROLLBACK.md` §2-b 에 1-b(1.1.16 → 1.1.15 되돌림 전 레인 저널 확인 · 명령) |
| (이 절) | HANDOFF 델타 · TODO |

### 8-2. ③ S3-11 — 조각 3 codex 2R 고침분 이종 검토

| 회 | 대상 | 판정 | 처분 |
|---|---|---|---|
| 1R | 43b44ea4(동률 짝 안 함 · 감싼 꼴 속 글 비교 · 시작점 상한+세대·stale) | **REVISE** · major 1 — 2R 지적 ①②③ 은 닫힘 · 새 결함: `bounded()` 가 `chat_transcript` 거절도 TIMED_OUT 으로 합쳐 initOffset 이 stale → 기록 조회만 계속 실패하고 보내기는 되는 좌석에서 말이 status_timeout 붙잡음에 굳음 | bb0a73e0: `invoke(…).catch(() => null)` 을 bounded 안에 — 거절 = null → 세대 같으면 none(보냄) · 다르면 stale. 시험 1(slice3fix 「시작점 조회가 거절되면 … 쓰기 1」) · 고침 되돌리면 그 시험 붉음(34/1) 확인 · views 287/0 · tsc 0 |
| 2R | bb0a73e0 | **ACCEPT** · issues 0 — 「1R major 닫힘 · 거절은 bounded 앞에서 null 로 정상화돼 같은 세대면 none · 세대 검사가 offset 갱신보다 먼저라 늦은 거절은 stale(새 offset 을 덮지 않음) · 실제 시간 초과는 계속 stale·쓰기 0 · 2R ①②③ 유지」 | 원문 `docs/integ-1116/codex-s3-r2.json` |

원문 = `docs/integ-1116/codex-s3-r1.json` · 사본 `~/.cys/pack/round/_reviews/cysr-1116-integ-1118-s3-r1-codex.json`.

### 8-3. ④ S1-11 — 빈 셸 가드(사람 표지 + refuse_on_approval)

- 자리: `src/bin/cysd/handlers.rs` `surface.send_text` — 기존 빈 셸 가드(`!human && agent_seat_vacant_now`) 바로 앞에 갈래 1개: `human ∧ params.refuse_on_approval ∧ agent_seat_vacant_now(좌석)` → `no_agent` 오류 · **타이핑 0 · 큐 0**. 큐 코드(`hold_for_vacant_seat`·governance)·승인 판정·원자 제출 writer 무접촉 → 【결정필요】 아님으로 판단(변경 = 조건 1개 + 오류 응답).
- 큐에 넣지 않는 이유: 사람 말은 화면이 붙잡고 사람이 다시 보낸다 — 큐에 두면 뒤에 뜬 에이전트에게 저절로 배달돼 두 번 갈 수 있다.
- 옵션 없는 사람 입력(터미널에서 직접 치는 길)은 종전 그대로(빈 셸에 사람이 치는 것은 정상) — 시험의 대조 갈래.
- 시험 `handlers::tests::integ1116_human_refuse_send_not_typed_into_bare_shell`(유닉스 · X-4 시험과 같은 `exec /bin/sh -i` 좌석 · 메타 claude): 사람 표지 + clear_first + refuse_on_approval = `no_agent` · PTY 쓰기 0 · 큐 0 / 옵션 없는 사람 입력 = `sent:true`. **고친 뒤 1/0 · 가드 끈 뮤턴트(`if false && human …`) = 붉음**(응답 `{"ok":true,"result":{"sent":true}}` = 고치기 전 동작 그대로 재현) · 원복 확인(diff = 추가분만).
- 한계·📌: ⑴ 앱(viewcore `PRE_WRITE_REFUSALS`)은 `no_agent` 를 목록 밖 = 「확인 중」(다시 보내기 0)으로 본다 — 안전한 쪽. 사람 표지 + refuse 길에선 이제 바이트 0·큐 0 이 보장되므로 그 목록에 `no_agent` 를 넣으면 「못 보냄 + 다시 보내기」로 정확해진다(화면 1줄 · 이번 범위 밖). ⑵ 판정은 기존 가드와 같은 `agent_seat_vacant_now`(프로세스 표 1회 갱신) — 사람 표지 + refuse 요청마다 1회 비용 추가. ⑶ 「문턱 판정 ~ 이 가드」 사이에 죽는 틈은 남음(가드 ~ 쓰기 사이 ms 단위).

### 8-4. ② V8

`docs/RELEASE-ROLLBACK.md` §2-b 「1-b」: `ls -d ~/.cys/.pack-journal.d/*/active 2>/dev/null`(윈 `%USERPROFILE%\.cys\.pack-journal.d\*\active` · `CYS_PACK_DIR` 기기 = 팩 폴더 부모) 가 비어야 내림 · 나오면 1.1.16 데몬을 한 번 다시 켜 기동 복구 → `cys doctor` pack-state 줄 확인 · `kept/` 는 지우지 않음. 근거 = 1.1.15 는 레인 저널(`src/pack.rs` `PACK_JOURNAL_ROOT = ".pack-journal.d"` · 경로 `home_default_pack_dir` = `~/.cys/pack` 의 부모)을 모름(vendor HANDOFF §10-4 F7 ④).

### 8-5. ⑤ V1 — 결정 메모(master 가 정함)

- 무엇: 1.1.15(11-21) ~ 1.1.16 사이, 부서 있는 기기의 「팩 단독 자동 업데이트」를 멈출지(근거 `~/axdev/workers/cysr-vendor-0151-judge-1117/JUDGE-v0.14.54-v0.15.1.md` §6 결정 1 · 저널 결함 = 1.1.15 에 그대로 · 고침 = 이 가지 vendor 묶음).
- 사실: 팩 단독 업데이트는 `pack-v*` 태그 → `pack-release.yml` 레인으로만 나간다(`docs/RELEASE-ROLLBACK.md:50` · 승인 게이트 없음) · 기기 쪽은 `src/update/realops.rs` 팩 경로 · 이 저장소 마지막 `pack-v*` = pack-v0.12.92(47855532 · 2026-07-18 — 4달 쓰지 않은 레인).
- 권고 = A(멈춤)를 **코드 0 · 발행 쪽 운영 게이트**로: 11-21 ~ 1.1.16 발행 전까지 `pack-v*` 태그를 만들지 않는다(1.1.15 동결판·기기 무접촉 · 1.1.16 이 12-05 전이라 창 ≈2주).
- 단점 1줄: 그 사이 팩 수정은 프로그램 업데이트(1.1.16)로만 나간다 — 급한 팩 수정이 생기면 1.1.16 을 앞당기거나 그 1건만 위험을 받아들여야 한다.

### 8-6. 시험(e3cffabc · 같은 격리 틀 · cargo 1건씩)

| 대상 | 직전(26a41fe1/973459e2) | 이번 |
|---|---|---|
| lib | 1256 · 0 · 3 | **1256 · 0 · 3** |
| bin cysd | 3305 · 1(흔들림 · 단독 초록) · 17 | **3307 · 0 · 17**(+1 = S1-11 시험 · 앞 흔들림 1건 초록) |
| `bun test ./src/views` · tsc | 286/0 · 0 | **287 / 0 · 0**(+1 = S3-11 시험) |
| chat_gate · confirm_gate · tickrec OFF(새 번들) | 59 · 37 · 308dd2b91f9a | **PASS 59 · PASS 37 · PASS 308dd2b91f9a** |
| secret-scan --all | clean 2162 | **clean**(커밋 뒤 다시 잼) |
| codex | — | S3-11 1R REVISE → 고침 → 2R ACCEPT |

- 돌리지 않은 것: cys·seatkeep·tests/*.rs·팩 파이썬·health·나머지 화면 게이트 — 이번 변경 = `handlers.rs`(cysd) · `views/core.ts`+시험 · 문서뿐이라 그 대상의 입력이 안 바뀜(직전 전체 실행 값 그대로).
- CTX 실측 43.7%(jsonl 라이브 · 09:21).

### 8-7. ④ 📌 반영(master#f7e14a93) — 앱 `no_agent` = 못 보냄

- `src-tauri/src/viewcore.rs` `PRE_WRITE_REFUSALS` 에 `"no_agent"` — 사람 표지 + refuse_on_approval 요청(앱 대화 화면 유일 꼴 · `human_send_params`)의 `no_agent` 는 이제 쓰기 0 · 큐 0(cysd eca3b956)이라 「확인 중」 대신 「못 보냄 + 다시 보내기」(`classify_send` → failed → 화면 `canRetry`).
- 시험: `viewcore::tests::classify_covers_the_four_outcomes` 에 `err("no_agent") → failed` 단언 1줄 — **넣기 전 붉음**(`left: "uncertain"`) → 넣은 뒤 cys-app 전체 **348 / 0 · 2 ign**.
- V1 = master 결정 A(pack-v* 태그 0 · master 원장) — 이 가지 할 일 없음.

### 8-8. 지침 바이트 예산 래칫(master#41422dd8)

- 붉음: `cysjavis-pack/bin/tests/test_cso_directive_rev.py` `test_directive_byte_budget_ratchet` — MASTER 86,642 > 85,365(CEO 도 102,128 > 100,851). 원인 = 조각 4 팩 커밋 4d20d25a·e1cd0f76·12e8bc95 의 「대화 화면 표식」 절 +1,277 B(3a095c4e = 상한과 같은 85,365).
- ⑴ 줄이기: 그 절을 뜻 불변으로 1,276 → 940 B(−336) · 표식 꼴 4줄은 화면 판정(`ui/src/views/judge/confirms.ts`)과 글자 그대로 맞아야 해서 손대지 않음 · 그 밖 조항은 이 티켓 밖(옛 조항 문구 핀 다수 · 지침 개정).
- ⑵ 남는 +941 B = 상한 상향: MASTER 86,306 · CEO 101,792 — 시험 역사 주석 ⑤ 에 근거 1줄(10-26 선례 ④ 와 같은 꼴).
- 생성물 재생성: CEO_TEMPLATE(gen --check GREEN 101,792) · 해시표(지금 판 1개 교체 · --check OK) — ⚠ §3 경고(1.1.15 태그 뒤 재생성)는 그대로 유효.
- 시험: test_cso_directive_rev 75/0 · event_inject ALL PASS · bootv2_doc_contract OK · `cargo test --lib released` 3/0 · scripts/tests 23개 = OK 22 + `test_release_trigger_split`(시스템 python3 에 PyYAML 없음 — `ModuleNotFoundError: yaml` · 기준선부터 같은 환경 사유) → PyYAML 넣은 `uv run --with pyyaml` 로 **17/0**.

### 8-9. cysd `pending_requests` 재open `Locked` 흔들림(master#c3198344) — 제품 고침

- 관측(master 게이트 81112a46): `c8registry_explicit_recovery_retirement_prevents_restart_capacity_leak` · `loaded_id_bookkeeping_is_reclaimed_with_the_row` · `persisted_sequence_survives_eviction_and_same_instance_reopen` — 셋 다 같은 scratch 에 store 를 닫고 곧바로 다시 여는 줄의 unwrap · **Err 원문 = `called \`Result::unwrap()\` on an \`Err\` value: Locked`** · 이 파일은 어느 병합 가지도 안 건드림(3a095c4e..HEAD diff 0) = 기준선부터의 흔들림(vendor·backlog 인계서의 pending_requests `Locked` 흔들림과 같은 것).
- 가설 판정(측정 전용 시험 `integ1116_reopen_vs_fork_probe` · 미커밋 · 측정 작업트리 `~/axdev/.wt/cys-1116-integ-race`): 새 scratch 마다 open → drop → 날 `try_lock` 1회(원시 결과) → reopen, 300 주기.
  | 조건 | 원시 `try_lock` = `WouldBlock` | `PendingStore::open` = `Err(Locked)` |
  |---|---|---|
  | fork 스레드 0 | 0 / 300 | 0 / 300 |
  | fork 스레드 4(`Command` + `pre_exec` = fork+exec 길) · 고치기 전 · 50회 | **225 / 15,000**(1차) · **431 / 15,000**(재부팅 뒤 2차) | **147 / 15,000**(fork 2,998) · **339 / 15,000**(fork 15,830) |
  | 같은 조건 · 고친 뒤 · 50회 | **0 / 15,000**(1차) · **0 / 15,000**(2차) | **0 / 15,000**(fork 8,372) · **0 / 15,000**(fork 7,621) |
  - 13:46 재부팅으로 스크래치(/tmp) 기록이 사라져 2차를 다시 잼 — 2차 원문은 `~/axdev/.wt/cys-1116-integ-race/evidence-d5/probe-{pre,post}50.txt`(측정 작업트리 · 임시 폴더 밖 · 미커밋). fork 0 조건은 두 차례 모두 0.
  - master 가설 「앞 store 의 drop 이 늦게 놓음(배경 스레드·Arc)」 = **기각**: fork 없으면 0 · store 는 잠금 `File` 을 필드로 직접 들고(`_process_lock`) 다른 곳과 공유하지 않아 drop 이 곧 close.
  - 실제 원인 = flock 은 open file description 에 붙는다 → 같은 프로세스의 다른 스레드가 fork 하면 자식이 exec(또는 portable-pty 의 fd 정리) 전까지 그 description 을 복제해 쥔다 → close 만으로는 안 풀림. cysd 시험 바이너리는 다른 시험이 좌석을 fork 로 스폰하므로 부하가 클수록 그 창이 길어진다.
- 판정 = **제품 쪽**: 시험만의 문제가 아니라 `PendingStore` 의 「닫으면 잠금이 풀린다」 가 fork 하는 프로세스(데몬 = 좌석을 스폰함)에서 성립하지 않는 결함. 지금 데몬은 `PendingStore` 를 시험 밖에서 열지 않지만(grep 0) 같은 프로세스 재open 이 생기는 순간 같은 결함이 난다. 같은 저장소의 다른 파일 잠금(`src/pack.rs` 레인·공용 apply-lock)은 이미 명시 `unlock()` 을 한다 — `PendingStore` 만 close 에 기댔다.
- 고침(fd9f0cc7 · sleep·재시도 0): `impl Drop for PendingStore { let _ = self._process_lock.unlock(); }` — flock 해제는 description 의 모든 복제본에 대해 푼다.
- 시험(결정론 · 붉음 먼저): `pending_requests::tests::reopen_succeeds_while_a_duplicate_of_the_closed_lock_fd_is_alive` — fork 자식의 복제본 대신 `try_clone`(같은 description)을 쥔 채 drop → reopen. **고치기 전 `Some(Locked)` 로 붉음 → 고친 뒤 초록** · 배타(살아 있는 store 가 있으면 두 번째 open = Locked)는 그대로 단언. `pending_requests::` 모듈 **100 / 0**.
- 부하 증거(master 통제 실행 · 머리 ff9448fc · 19:03:57~19:26:43 · gate_rc 0 · 로그 `master/logs-integ-forkprobe-ff9448fc.log`): 처음 계획한 `pending_requests::` 반복 50회는 fork 가 없어 결함을 못 가르므로(§10-2) fork probe 로 바꿨다. `PROBE_N=15000` · fork 스레드 4:
  | 판 | fork 수 | 원시 `WouldBlock` | `open` = `Err(Locked)` |
  |---|---|---|---|
  | 고친 판 | 6,841 | **0 / 15,000** | **0 / 15,000** |
  | 음성 대조(`impl Drop` 제거) | 6,733 | **311 / 15,000** | **268 / 15,000**(sample `Locked`) |
  - fork 스레드 0 = 두 판 모두 0 · 0. `pending_requests:: seat_proc::` `--test-threads=8` × 29회 = **실패 0 / 29**(매회 120 passed · 앞 기록 11 / 29 실패) · syspolicyd 26 · fake 162 처음~끝 불변.
  - 한계: `seat_proc` `handshake_timeout` 은 「재발 안 함」 까지만 말할 수 있다. Gatekeeper 수정이 그 원인이었다는 증명은 아니다.

---

## 9. 인계 델타(master#feca26ce · 2026-11-18 18:5x · 계정2 새 좌석에게)

### 9-1. 중단 직전 하던 일
- 티켓 = master#c3198344(cysd `pending_requests` 재open `Locked` 흔들림). **고침은 끝나 커밋됨**: fd9f0cc7(`impl Drop for PendingStore { unlock }` + 결정론 시험 `reopen_succeeds_while_a_duplicate_of_the_closed_lock_fd_is_alive` · 고치기 전 붉음 → 뒤 초록 · `pending_requests::` 100/0). 원인 판정·probe 표 = §8-9(8b3d0b8b 의 WIP 커밋이 §8-9 를 커밋함 · 미검증 표기는 「확인요청 5 미발송」 뜻).
- 남은 일 = ⑴ 부하 반복 50회 증거 ⑵ 【확인요청 5】 발송. ⑴ 이 13:46 재부팅 · 15:3x 세션 재시작으로 두 번 끊김.

### 9-2. 끊긴 시험과 결과
- 부하 반복(고친 cysd 시험 바이너리 직접 실행 · `pending_requests:: seat_proc:: --test-threads=8` × 50): 2차 실행이 **29회에서 끊김**. 29회 중 **pending_requests 실패 0** · **11회에서 `seat_proc` seatkeep 4건 실패 = `handshake_timeout`(seatkeep 소켓 10초 안에 못 붙음)** — APFS 복제 target 의 deps 자리 직접 실행에서 잦다는 기억(`cysd-test-binary-direct-run-and-cloned-target-seatkeep-timeouts`)과 같은 꼴로 보이나 **확인 안 함**(pending_requests 고침과 무관해 보임 · 가설). 로그 사본 `~/axdev/.wt/cys-1116-integ-race/evidence-d5/load-partial/`.
- probe 2차(fork 부하 측정 · 고치기 전/뒤 각 50회) 원문 = `~/axdev/.wt/cys-1116-integ-race/evidence-d5/probe-{pre,post}50.txt`(측정 작업트리 · 미커밋 시험 `integ1116_reopen_vs_fork_probe` 포함 · 지금 그 트리 소스 = 고친 판).
- ⚠ 시험 재실행 규칙(master#feca26ce): cysd·cys 시험은 고정 자리 방식 · **부하 반복(같은 시험 수십 번)은 사람 맥에서 금지** → 부하 50회는 **master 통제 실행(tools/gk-guard 방식)으로 요청**한다. 다시 돌릴 명령(통제 실행 안에서): `cargo test --bin cysd pending_requests:: -- --test-threads=8` 반복(seat_proc 은 빼거나 따로 — 위 handshake_timeout 판별을 섞지 않게) · probe = 측정 작업트리에서 `cargo test --bin cysd integ1116_reopen_vs_fork_probe -- --ignored --nocapture`.

### 9-3. 미결 · master 결정 대기
- 부하 50회 증거를 어떤 방식(통제 실행)으로 받을지 — master.
- `seat_proc` seatkeep `handshake_timeout`(직접 실행 · 복제 target)이 별개 흔들림인지 판별할지 — master(이 티켓 범위 밖으로 봄).
- 【확인요청 5】 미발송(내용 = §8-9 + 이 절).

### 9-4. 다음 첫 행동 3줄
1. `git -C ~/axdev/.wt/cys-1116-integ log --oneline -3` 로 머리 확인(이 절 커밋) · HANDOFF §8-9·§9 읽기.
2. master 에 부하 50회 통제 실행 요청(위 명령 · pending_requests 만) → 결과 0 붉음이면 §8-9 끝 줄 채움.
3. 【확인요청 5】(새 머리 · Err 원문 `Locked` · 제품 판정 근거 = §8-9) 발송.

---

## 10. 델타 — gatekeeper 수정 병합 · 부하 시험 판별력 점검(master#5d954b24 · 2026-11-18 18:5x~ · surface:2227 · 계정2)

### 10-1. 병합
- `1a59b5a9` = `fix/test-gatekeeper-crash`(4a343a63 · 7커밋) `--no-ff` 병합 · 충돌 0 · 4a343a63 과의 차이 = 이 HANDOFF 파일뿐.
- 합친 머리 확인(가벼운 것만): `cargo test --bin cysd --no-run` rc 0 · `cargo build --bin cys-seatkeep` 성공 · `reopen_succeeds_while_a_duplicate_of_the_closed_lock_fd_is_alive` 1/0 · 보호 계수 syspolicyd 26 · fake 162 불변.

### 10-2. ⚠ §9-2·§9-4 의 부하 명령은 이 결함을 못 가른다
- `pending_requests::` 시험과 `pending_attempts.rs` 에는 프로세스를 띄우는 코드가 없다(스레드만). 결함은 다른 스레드의 fork 가 있어야 나므로(§8-9 표 · fork 0 = 0건), `pending_requests::` 단독 50회는 고치기 전이어도 초록이 나온다.
- `seat_proc::` 를 섞은 29회도 약한 증거다. fork 원천이 seatkeep 시험 4건 + `/bin/sleep` 1회뿐이고, 실패한 11회는 그 4건이 좌석을 못 띄웠다. 고치기 전 바이너리로 이 부하를 돌려 붉어진 기록도 없다.
- `master/tools/gk-guard/run-filtered.sh` 도 이 측정에 안 맞는다: `--test-threads=1` 고정 · `--ignored`·`--nocapture` 를 넘기지 않고 `PROBE` 줄을 걸러 낸다.

### 10-3. 판별되는 측정 = fork probe 를 합친 머리에 얹기(소스 커밋 안 함)
- 패치(측정 작업트리 · 미커밋 · 임시 폴더 밖): `~/axdev/.wt/cys-1116-integ-race/evidence-d5/probe-only.patch` · `…/negative-control-remove-drop.patch`(`impl Drop for PendingStore` 3줄 제거).
- 1회씩 실측(`PROBE_N=300` · 원문 `…/evidence-d5/merged-1a59b5a9-probe300.txt` · 끝난 뒤 소스 복원 · 변경 0):

  | 판 | fork 스레드 | fork 수 | 원시 `WouldBlock` | `open` = `Err(Locked)` |
  |---|---|---|---|---|
  | 합친 머리(고친 판) | 0 | 0 | 0 / 300 | 0 / 300 |
  | 합친 머리(고친 판) | 4 | 154 | 0 / 300 | 0 / 300 |
  | 음성 대조(Drop 제거) | 0 | 0 | 0 / 300 | 0 / 300 |
  | 음성 대조(Drop 제거) | 4 | 142 | **10 / 300** | **9 / 300** |
- 시험 본체 0.41~0.42초 · 시험 실행 파일을 반복하지 않고 `PROBE_N` 만 키우면 된다(15,000 주기 = 1회 실행).

### 10-4. `seat_proc` `handshake_timeout` 가설(미확인 · 신뢰도 낮음)
- 실패 11회의 번호 = 8·10~13(5회 · `접속을 거절 handshake_timeout`) · 22·24·26~29(6회 · `소켓에 10초 안에 못 붙음`). 회차마다 4건이 **같은 사유로 함께** 실패한다. 같은 자리의 같은 바이너리가 나머지 18회는 초록이므로 「복제 target 자리」 만으로는 설명이 안 된다.
- 가설 1줄: 시험별 코드 결함보다, 그 시간대에 기계 전체가 느려져(seatkeep 실행·서명 조회가 보안 검사를 기다림) 10초를 넘겼을 가능성. 판정 = master 통제 실행.

### 10-5. 다음
- 【확인요청 5】 발송 뒤 master 통제 실행 결과 대기. 결과가 오면 §8-9 끝 줄을 채운다. → 채움(master#cb38b613).

---

## 11. 1.1.16 후보 확정 전 전체 게이트(master#cb38b613 · 2026-11-18 19:3x · surface:2227)

### 11-1. 들어올 순서
- **① 2228 nohands2 `feat/no-hands-gui-1118` → ② 2229 ownermem2 `feat/owner-memory-todo-1118` → 그 머리에서 전체 게이트 1회.** 각 가지의 티켓 검수가 끝난 뒤 들인다. 끝점 acda833a·adfcb006 기준 모의 병합은 두 순서 모두 충돌 0 · 결과 트리가 같고 고친 파일이 겹치지 않는다. ①을 먼저 두는 이유 = 이미 ff9448fc 를 품었고 지침 해시를 바꾸는 쪽이라 해시 확인이 먼저 끝난다.
- ① 완료(master#428436e7) = `b3cb2721`(38ef248a `--no-ff` · 충돌 0 · 트리 = 38ef248a 와 같음). 병합 뒤 `secret-scan --all` clean 2176 파일 · `gen_ceo_template --check` · `gen_released_directive_hashes --check` rc 0 · `test_cso_directive_rev` 75 OK. ② = master 지시 2/2 대기.
- 2228 이 이월한 다음 판 3건 = `HANDOFF.cysr-no-hands-gui-1118.md` §7 끝 줄(이번에 안 고침).

### 11-2. 실행
- 스크립트 = `docs/integ-1116/gate-1116.sh`(스냅샷 뿌리에서 `bash docs/integ-1116/gate-1116.sh <결과 폴더>` · 요약 = `<결과 폴더>/summary.txt`). 단계 82개(dry-run 계수 · §12 에서 `cys-app-inputs` 추가) · **모든 대상 1회 · 자동 재시도 없음** · 격리 env(`env -i` · 짧은 TMPDIR) · 단계 실행 중 5초마다 syspolicyd·fake 계수를 대조해 늘면 그 단계 프로세스 그룹을 끊고 rc 3 로 중단.
- 이 좌석에서 스크립트로 돌린 것 = 문법 · dry-run · gen 2 · secret 2 · `test_cso_directive_rev` 75 OK · `test_idle_gate` 49 OK · `test_check_macho_arch` 62 OK · `test_ci_branch_cysd_step` 38 OK · `test_unix_pty_results` 9 OK · `test_release_trigger_split` 17 OK · `ui-build` · `pw-venv`(playwright 1.60.0 · PyYAML 6.0.2 · `~/axdev/.wt/.gate-pw-venv`) · `e2e-chat` PASS 59 · 보호 계수 증가 흉내(가짜 계수기 → `secret-scan` rc 125 · 전체 rc 3). **Rust 묶음 · 나머지 팩 묶음 · health · 나머지 화면 게이트는 스크립트로 돌려 보지 않았다.**
- 맥에서 빼는 것 = `scripts/tests/test_release_postprocess_gate.py`(갓 만든 번들을 spctl·gktool 에 넘김) → CI 몫. `integ/1116` 은 ci-branch 의 push 대상(`feat/**`·`fix/**`) 밖이라 CI 는 별도 발화가 필요하다(push = master 게이트).

### 11-3. 판정 기준(앞 값 = §4·§8-6 · 더 늘면 사유 대조 · 붉음은 자동 재실행 말고 사유 전문 대조)
> **판독 결과 = 합격선 통과(§12-5 · master#971f9848 · 머리 7869bbf6b).**
| 대상 | 기대 |
|---|---|
| lib · bin cys · cys-seatkeep | 1256 · 0 · 3 ign · 765 · 0 · 2 ign · 49 · 0 |
| bin cysd | **3308 · 0 · 17 ign**(§8-6 3307 + fd9f0cc7 시험 1) |
| tests/*.rs | hidden 1 · rotate 11 · seat_group 1 · drainhold 4 · win 2종 0 · 전부 0 실패 |
| cys-app | 348 · 0 · 2 ign |
| bun test · tsc | 0 fail · rc 0 |
| 팩 파이썬 · doc-contract · event_inject · gen 2 · secret 2 | 전부 rc 0 |
| scripts/tests(맥 제외 1건 뺀 22) | **전부 rc 0** — 기준선부터 붉던 `test_release_trigger_split` 의 원인 = `/usr/bin/python3` 에 PyYAML 없음 → 게이트 전용 venv 로 실행(17 OK) |
| health | fail = **H-CLT-1·2 만**(기준선부터 · 이 기계 환경) |
| 화면 게이트 15종 | 전부 PASS · chat 59 · confirm 37 · tickrec OFF sha `308dd2b91f9a` · 나머지 수는 §4 |

2228 이 못 끝낸 3줄의 처리(master#428436e7):

| 항목 | 처리 |
|---|---|
| `run_bootstrap_health` (420초 상한에 걸려 결과 없음) | **게이트에서 돌림** — `health` 단계 · 상한 3600초 · 합격선 = 위 표 |
| `test_ci_branch_cysd_step` (「PyYAML 없음」 으로 미실행) | **게이트에서 돌림** — 이 시험은 PyYAML 이 필요 없다. `b3cb2721` 에서 `/usr/bin/python3` 로 38 OK(92초). PyYAML 이 필요한 것은 `test_release_trigger_split` |
| 우분투 레인의 새 등재 시험(`test_idle_gate`·`test_agents_notes_personal_hooks`·`test_hook_fail_timing`) | 맥 실행 = **게이트에서 돌림** · **우분투 실행 = CI 몫**(integ push 는 후보 확정 뒤 master 게이트 · `integ/1116` 은 push 자동 발화 대상이 아니라 `workflow_dispatch` 또는 `feat/**`·`fix/**` 가지 필요) |

### 11-4. 게이트가 먼저 잡은 것
- `secret-scan --all` 적색 1건 = 병합으로 들어온 `WORKER_TODO.cysr-test-gatekeeper-crash-1118.md:2` 의 홈 절대 경로 → 「작업트리 cys-1116-gkfix」 로 고침(문서 · 동작 무관).
- 같은 꼴이 `feat/no-hands-gui-1118` 의 HANDOFF·WORKER_TODO 에도 있었으나 그 좌석이 고쳐 38ef248a 병합 뒤 `secret-scan` clean.
- 📌 워크플로 미등재 팩 시험 44개(03c11f36 기준) = 범위 밖 기록 · 1.1.17 후보(master#48c83aeb). `test_owner_desk` 의 등재 여부는 ② 병합 때 다시 본다.

---

## 12. 전체 게이트 1차 판독(master#190297c9 · 머리 ea9812306 · 결과 `master/logs-gate-1116-ea9812306/` · gate_rc 1)

rc 0 = 64단계 · 붉음 = 17단계(`cys-app` 1 · `health` 1 · `e2e-*` 15) · syspolicyd 26 · fake 162 불변. 대조군 원문 = `~/axdev/.wt/cys-1116-integ-race/evidence-d5/gatefix-control{,2,3}.txt` · 기준선 대조는 이 절 표의 값.

### 12-1. 붉은 단계
| 단계 | 사유 원문 | 구분 | 근거 |
|---|---|---|---|
| `cys-app` rc 101 | `resource path binaries/cysd-aarch64-apple-darwin doesn't exist` | **게이트 실행 환경(대조군 확인)** | 같은 커밋 · 깨끗한 target: 입력 없음 = 같은 문구 rc 101 → `cys-app-inputs` 입력 있음 = `--no-run` rc 0(1분 26초). 시험 자체는 아직 안 돌았다 |
| `health` · **H-WIN-16** | `팩 creationflags 사용이 동결표를 벗어났다` · 동결 57파일 vs 실측 59파일 · 추가 = `javis_idle_gate.py`:1 · `javis_owner.py`:1 | **이번 병합의 실제 결함(대조군 확인)** — 고치지 않음 | 기준선 3a095c4e 같은 검체 = pass. 03c11f36 57 → 47170c00(2228) 58 → ea981230(2229) 59. 새 사용은 전부 캡처 스폰(`javis_idle_gate.py:140` · `javis_owner.py:288·548` = `capture_output` + `stdin=DEVNULL` + `**NOWIN`) |
| `health` · H-CLT-1 | `CLT 없는 맥에서 프리루드가 동봉 python 이 아닌 '/Applications/cys.app/…/python3' 를 골랐다(사전설정 미설정)` | **이번 변경 무관(대조군 확인)** · 제품/환경 구분은 추정(이 기계의 설치본) | 기준선 3a095c4e = fail · 사유 전문 일치 |
| `health` · H-CLT-2 | `호스트(OSTYPE=darwin25)에서 해소값이 종전 규칙과 다르다: NEW='/Applications/cys.app/…/python3' OLD='/usr/bin/python3'` | 위와 같음 | 기준선 = fail · 사유 전문 일치 |
| `e2e-*` 15종 rc 1 | `ledger.register failed — scoped group killed … acl_denied: capability denied: external lacks 'write-shell' for ledger.register (deny-by-default)` | **게이트 실행 환경(대조군 확인)** · 화면 판정은 아직 없음 | `cys run -- /bin/echo`: 좌석 안 = 성공 · 좌석 밖(이중 fork + setsid · ppid 1) = 같은 문구 rc 1 |

- `H-WIN-11` skip = 윈도우 실기(정상) · health 합계 166 pass · 3 fail · 1 skip / 170.

### 12-2. 합격선과 맞는 단계
lib 1256·0·3 · cys 765·0·2 · cysd 3308·0·17 · seatkeep 49·0 · hidden 1 · rotate 11 · seat_group 1 · drainhold 4 · win 0·0 · portable-pty 9·0 · 팩 파이썬 21 · scripts/tests 22(`test_release_trigger_split` 17 OK 포함) · gen 2 · secret 2 · bun 3747 pass · 88 skip · 0 fail · tsc rc 0(7.0.2 · `ui/src` 218파일 대상 확인).

### 12-3. `gate-1116.sh` 고침(환경 2건)
- `cys-app` 을 화면 번들 뒤로 옮기고 `cys-app-inputs` 추가: binaries = `target/debug` 의 APFS 복제(0바이트 금지 · 실행·삭제 없음) · resources·runtime = 자리표시자.
- 화면 게이트에서 `cys run` 제거: 좌석 밖 실행이 거부되므로 `guarded` 가 프로세스 그룹을 맡고, 정상 종료 뒤에도 남은 자식을 정리한다(대조: 배경 `sleep` 정리 확인).
- 대조용 작업트리 `~/axdev/.wt/cys-1116-gatefix` 는 지우지 않고 남겼다(새 실행 파일을 지우지 않기 위함).

### 12-4. H-WIN-16 처분안(미적용 · master 결정)
`cysjavis-pack/bin/tests/run_bootstrap_health.py` `_U5_PACK_CREATIONFLAGS` 에 사유와 함께 2줄: `"javis_idle_gate.py": 1`(대기 게이트 캡처 스폰 NOWIN 정의) · `"javis_owner.py": 1`(오너 책상 캡처 스폰 NOWIN 정의).

### 12-5. 최종 판독(master#971f9848 · 합격선 §11-3 통과)
| 묶음 | 대상 | 결과 |
|---|---|---|
| 1차 64단계 | `master/logs-gate-1116-ea9812306/` | 전부 rc 0 · 값 = §12-2 |
| 환경 수정 19단계 | `master/logs-gate-1116-ea9812306-r2/`(스크립트 291928673 · 22:57:19 끝) | gate_rc 0 · `cys-app` 348 · 0 · 2 ign · 화면 15종 RESULT PASS · tickrec OFF `308dd2b91f9a` = 기준 · invoke 1088 = 1088 |
| health | `master/logs-gate-1116-7869bbf6b-health/`(새 스냅샷 7869bbf6b · 23:09:41 끝) | 167 pass · **fail = H-CLT-1·2 만** · skip 1(H-WIN-11) · H-WIN-16 pass · 스크립트 gate_rc 1 은 이 허용된 fail 2건 때문 |
| 보호 계수 | 세 실행 모두 | syspolicyd 26 · fake 162 불변 |

- 맥에서 뺀 `test_release_postprocess_gate.py` 와 우분투 실행은 아직 안 돌았다(CI 몫 · §12-6).

### 12-6. `test_owner_desk` CI 등재 · dispatch 준비(push·dispatch = master)
- `92fcae3e3`: `ci-branch.yml` 2 · `release.yml` 2 · `pack-release.yml` 1 루프에 등재. `lane-parity-rehearsal.sh` 고치기 전 `--strict` rc 1(`미등재 test_owner_desk`) → 고친 뒤 기본 · `--strict` · `--self-test` 모두 rc 0.
- 맥 1회(CI 꼴 · `CYS_PACK_DIR` 임시 · python 3.12.13): 52 OK · 53.6초 · 계수 불변. 우분투 실행은 미확인.
- §11-4 의 「미등재 44개」 는 낱말 대조 값이다. lane 도구 기준으로는 미등재가 모두 사유 있는 항목이고 사유 없는 미등재는 0이다.
- 명령(저장소 `oogisoogi/cys-ro` = **공개** · push 하면 `integ/1116` 이 공개된다 · `workflow_dispatch` 는 잡을 고를 수 없어 맥·우분투·UI 잡이 다 돈다):
```bash
cd ~/axdev/.wt/cys-1116-integ; H=$(git rev-parse integ/1116); R=oogisoogi/cys-ro
/usr/bin/git push origin integ/1116
gh workflow run ci-branch.yml --repo "$R" --ref integ/1116
gh run list --repo "$R" --workflow ci-branch.yml --branch integ/1116 --event workflow_dispatch --limit 1 --json databaseId,headSha,status,url   # headSha = $H 확인 뒤 다음 줄
RID=<위 databaseId>; gh run watch "$RID" --repo "$R" --exit-status
JID=$(gh run view "$RID" --repo "$R" --json jobs --jq '.jobs[] | select(.name=="ubuntu-pack-suite") | .databaseId')
gh run view --repo "$R" --job "$JID" --log | grep -E '== \[pack\] declared-state test: (test_idle_gate|test_agents_notes_personal_hooks|test_hook_fail_timing|test_owner_desk) =='   # 기대 4줄
```
