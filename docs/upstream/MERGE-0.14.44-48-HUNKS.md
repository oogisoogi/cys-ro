# MERGE-0.14.44-48 부록 — 충돌 덩어리 전수 판독표 (서브 3기 산출 · 검증 = 리드 표본 대조)

> 본문 = `MERGE-0.14.44-48-PLAN.md`. 이 부록은 근거 원표다. `scratchpad/` = 판독 작업 폴더(저장소 밖 · 미커밋) — merge-tree 충돌본 `mt/` · 3자 재현 `mf/`·`am/`.
> 리드 표본 대조(실측): create_surface_with_env 인자 10개(state.rs:7092) · expire_orphan_feed 실재(governance.rs:1237) · phoenix text=True 10곳(HEAD) ↔ 원작자 시험 「0곳」 요구(test_phoenix_encoding_default.py:456) · wheelgate (e) 모달 근거 원문(58d5c8e2) — 4/4 일치.

## agentA — Rust daemon/lib/CLI 충돌 판독 (HEAD int/1110-upstream × v0.14.48 · base v0.14.43)

근거 파일: `scratchpad/mt/<path>` (merge-tree 충돌본) · 자동병합 3파일은 `scratchpad/mf/*.merged`(git merge-file 3자 · 충돌 0) 로 재현.
판정 기호: ⓐ theirs · ⓑ ours · ⓒ 융합 · ⓓ 보안경계 검토 · ⓔ 제외 후보.

## 1. 충돌 덩어리 전수 (11 덩어리 / 8 파일)

| 파일 | # | ours (1줄) | theirs (1줄 · 커밋) | 판정 | 위험 |
|---|---|---|---|---|---|
| src/bin/cysd/approval.rs | 1 (L393-466) | `pub fn tokenize` 본문 = ⑲ cysr-117 재작성(Mode 열거형 · golden 시험 `golden_tokenize_table_is_frozen` approval.rs:1173) | 본문을 `cys::approval_tokenize`(src/lib.rs:3333 in mt)로 이동 · 여기는 `pub use cys::approval_tokenize as tokenize;` (6726406e · 62f040bb) | ⓐ+ⓓ: theirs 재공개 채택 + 우리 golden 시험 유지(재공개 이름 `tokenize` 로 그대로 컴파일). 판독상 두 본문은 같은 진리표(작은따옴표 리터럴 · 큰따옴표 `"\\$\`` 만 이스케이프 · 따옴표 열면 낱말 생성 · 미닫힘 None · 맨끝 `\` 버림) — golden 시험이 녹이면 동치 확정. 대안: ⑲ 본문을 lib.rs `approval_tokenize` 에 이식(단일 정의 유지 · lib 판의 `chars.next().unwrap()` 제거 효과) | 승인 접두 비교의 재료 — 동치 아니면 승인 우회/오거부. CLI `approval check` 숫자 토큰 떼기(6726406e)와 데몬이 같은 코드를 써야 하므로 ⓑ(우리 본문만 존치)는 이중 정의 드리프트 |
| src/bin/cysd/main.rs | 1 (L47-54) | `mod named; mod panetitle; mod rc_guard;` | `mod knobs; mod office_bridge;` (77b1c118 · a7c3ed1c) | ⓒ 둘 다 · 알파벳순(knobs, named, office_bridge, panetitle, rc_guard) | 없음 — 서로 다른 모듈 추가(1.1.8 ledger lib.rs #1·main.rs #1 과 같은 꼴) |
| src/bin/cysd/main.rs | 2 (L2197-2215) | spawn 직후 `#[cfg(windows)] winjob::assign_child(pid)` — 브리지 python 을 데몬 Job 에 결박(841c945c 계열 · P3 2026-09-10 실측) | `let born = Instant::now(); if managed { limiter.record(..) }` — B3 재기동 상한·수명 측정(a7c3ed1c) | ⓒ+ⓓ: ours 블록 먼저(닫는 `}` 보강) → theirs `born`/`limiter.record` 뒤. 둘이 공유하는 꼬리 `}` 는 theirs `if managed {` 를 닫음 | 프로세스 수명/종료 경계. upstream office_bridge.rs 에 Job 처리 0(grep 결과 0) → ours 버리면 윈도 고아 브리지 재발. theirs `supervise_managed_child` 가 자식 kill 해도 Job 과 충돌 없음【추정】 |
| src/bin/cysd/main.rs | 3 (L8020-8038) | 파일 끝 `mod d6_probe_tests;`(꼬리 주석 금지 규약) | `approval_a_tests`(0a0c6280) · `feed_sweep_tests`(77b1c118) · `vt100_dim_tests`(4f48c9a4) | ⓒ 둘 다 · 파일 끝 유지 · d6 선언 줄 꼬리 주석 금지 지킴 | 낮음 — ledger-118 main.rs #2(L463) 선례 그대로 |
| src/bin/cysd/state.rs | 1 (L8088-8099) | scrollback 락 안 `*surface.last_line_at = Some(now)` (read_text 신선도 · e6c0d1af) | 같은 락 안 `if echo { repaint::echo_record_lines(..) }` + `let before =` (d11cbb65) | ⓒ 둘 다(순서 무관 · 둘 다 scrollback 락 안) — `before` 는 auto-merge 로 이미 `let before =` | 낮음 — 락 순서 scrollback→repaint_echo(leaf) · last_line_at 별도 Mutex |
| src/bin/cysd/state.rs | 2 (L11259-11380) | 시험 `d_u3_quote_window_blocks_restatement_after_injection` · `d_u3_wide_detection_..`(D-U3 출처 창 · 3c82470d) | 시험 `repaint_echo_window_mutes_health_rules_and_recall_then_expires`(e0c7bdda) · `repaint_echo_window_follows_long_replay_then_closes_on_quiet`(d11cbb65) | ⓒ 네 시험 전부 · 두 마지막 시험 사이 `}` 보강 | 낮음 — run_health_rules 는 auto-merge 로 둘 다 실림(mt state.rs:8186-8215: repaint 조기 반환 + `in_quote_window` discourse). rate_limited 식은 표 안 리터럴 유지(mt state.rs:9030-9040 · 9063) |
| src/bin/cysd/handlers.rs | 1 (L7524-7529) | read_text since_line 응답 `"source":"scrollback","scrollback_stale":stale` (e6c0d1af) | `"repaint_echo_skipped": skipped` (d11cbb65) | ⓒ 한 json 에 셋 다: `"source","scrollback_stale","repaint_echo_skipped","quiet_secs"` | 낮음 — `stale` 은 L7484 `scrollback_stale_now`(ours) · `skipped` 은 theirs auto-merge 줄에 실재. `line_count` 가 theirs 로 `kept.len()` 이 됨(반향 없으면 동일) |
| src/bin/cysd/governance.rs | 1 (L13543-14112) | tests 모듈 앞머리 ours 시험 ~10건(q2 pause 재확인 · v114/v115/v116 빈좌석 가드 소스 핀 등 · 791b600c 외) | 자손 세기 보정 시험 ~20건 + 헬퍼 `descendants_from_table`·`report_shape_table` (61a94aa6 · e0250a83) | ⓒ 둘 다 · ours 먼저 · 사이 `}` 보강 | 낮음 — theirs `super::descendants_report`(mt governance.rs:4740) 실재. 소스 핀 `wh_guarded_collectors_called_only_from_two_sites` 는 handlers.rs/usage.rs 에 `_guarded(` 금지 — HEAD 두 파일 0건 확인 |
| src/lib.rs | 1 (L8952-9122) | 파일 끝 `#[cfg(all(test,windows))] mod win_std_inherit_tests` (9c23f7e5) | 파일 끝 `#[cfg(test)] mod bridge_probe_tests` (8a2c8710) | ⓒ 둘 다 | 없음 — ledger-118 #825(첫 cfg(test) 절단 소스 핀)와 무관(둘 다 파일 끝) |
| src/pack.rs | 1 (L11322-11405) | 시험 `t3_agora_counsel_job_flags_survive_merge_and_refresh` (829403e6 · U1 validate_job/migrate) | 시험 `agy_statusline_reconcile_is_deferred_and_consumed_once` (b9151464) | ⓒ 둘 다 · 사이 `}` 보강 | 낮음 — theirs 시험은 프로세스 전역 원자(AGY_PROBE_DEFERRED/PENDING) 사용. 같은 프로세스에서 `reconcile_agy_statusline_at_install` 을 부르는 곳은 setup_isolated_config_dir(mt pack.rs:1526→1570)뿐이라 병렬 플레이크 위험 낮음【추정】 |
| src/bin/cys.rs | 1 (L15967-15996) | boot_agent_on_surface: `inject_claude_prompt_suggestion_default` · `inject_claude_effort_env` · `apply_seat_settings_arg(&mut cmd, role, agent)`(D25) | 윈도 좌석 `claude_tui::reconcile_for_launch(dir)` — 좌석 config dir 의 settings.json 에 `tui` 없을 때만 `"default"` 기록(d2c6c405) | ⓒ+ⓓ: ours 세 줄 먼저 → theirs 블록 → `render_launch`. 소스 핀 `d17_d25_launch_wiring_pins`(HEAD cys.rs:48183)는 apply_seat_settings_arg < render_launch 만 요구 → 충족 | 파일 쓰기(사용자 Claude 설정) — 윈도 한정 게이트·킬스위치 `CYS_WIN_TUI_CLASSIC_OFF`. 대상 dir = spec env 의 CLAUDE_CONFIG_DIR(`seat_claude_config_dir` mt cys.rs:15295) — D-mac-1 의 데몬측 `authoritative_config_dir`(OS 관측) 과는 다른 축(CLI 기동 직전 spec 값). 복원 좌석에서 spec≠OS 관측이면 엉뚱한 프로필에 tui 기록 가능【추정·윈도 한정】 |

참고: accounts.rs(3 덩어리)는 범위 밖. 범위 내 state/governance 덩어리 중 seat account/seat_profile/authoritative_config_dir/account_id 를 건드리는 덩어리는 **없음**.

## 2. 컴파일 적응 필요 (upstream 새 코드 → 우리가 바꾼 시그니처)

| 위치(병합본) | 내용 | 조치 |
|---|---|---|
| src/bin/cysd/state.rs:7228 (auto-merged · 충돌 표식 없음) | upstream `create_surface_untrusted_config_dir`(#[cfg(test)] · 66b29c91)가 `create_surface_with_env(None, cmd, None, role, 24, 80, &[], Some(config_dir))` — 인자 9개. HEAD 시그니처는 10개(S3-D2 `agent` 추가 · HEAD state.rs:7092-7110) | 끝에 `, None` 추가(E0061). accounts.rs:8005(mt) 가 이 이음매 사용 — accounts 담당과 공유. H-AUTH-SELFLOOP: 호출 파일 = state.rs 라 허용 범위 유지 |
| src/lib.rs `RAW_COMMAND_NEW_FROZEN`(HEAD lib.rs:6723 · ours 전용 동결 계수) | upstream `src/agy_statusline.rs` 프로덕션 `Command::new` +2(v0.14.48 agy_statusline.rs:738 실연 검사 · :799 taskkill — 둘 다 `spawn_policy(Attached)` 체인) | 표에 `("src/agy_statusline.rs", 2)` + 근거 주석 추가(안 하면 `raw_command_new_census_is_frozen` 적색). office_bridge/knobs/repaint/claude_tui/settings_surgery 프로덕션 스폰 = 0(확인) |

기계 검사: 함수 인자 수 base→HEAD 변화 × upstream 추가 줄 호출 교차(scratchpad/sigdiff.py) → 실히트 1건(위 state.rs:7228)뿐. 역방향(우리 새 호출 × upstream 시그니처 변경) 실히트 0(tokenize 는 재공개라 무해). 우리가 필드 추가한 구조체의 upstream 리터럴 = `Job`(schedule) 1건 — serde 생성이라 무해(mf schedule.rs.merged:6675). 우리가 변형 추가한 열거형(ForceDeliverDenied·FileAction 등)에 대한 upstream 새 match 0건.

## 3. 자동병합 의미 위험 (같은 함수를 양쪽이 수정)

| 파일·함수 | ours | theirs | 판정·위험 |
|---|---|---|---|
| governance.rs `spawn_watchdog` (base L215-222) | `expire_orphan_feed`(v112-wake ⑥ · mt :1239) — pending 중 ⑴이전 데몬 세대 ⑵wait 요청자 pid 사망 → `expired`(모든 kind · 클라이언트 발행 포함) | `sweep_orphan_daemon_approvals`(C1 · mt :2295 · 77b1c118) — `daemon-` 접두 approval/first_run_gate 중 닫힌 좌석 것만 → `stale-cleared` | ⓒ+ⓓ 둘 다 존치(대상·결정 문자열 다름 · 둘째는 pending 아니면 no-op). **정책 충돌**: theirs 는 "클라이언트 발행 항목은 건드리지 않는다"·C3 `publisher_alive=null`(데몬 이전 항목 = 모름) 설계인데 ours 는 이전 세대 항목을 일괄 만료. ours 는 `resolve_feed_item` 아닌 직접 상태 변경(waiter 깨우기 경로 우회 — 요청자 부재 전제라 실害 낮음【추정】). 결재 상태 전이 경계라 검토 권고 |
| schedule.rs `fire` · `ensure_builtin_jobs_locked` · `spawn_scheduler` · `status` | U2 정비 동결(`update_hold::schedule_frozen` · scheduler_tick/run_now) · BUILTIN v4(phoenix push→command · K49 retire) · `text_command_allowed` = `try_load_records` fail-closed | 0.14.48 은퇴 시드 text_command 조용히 건너뜀(`retired_text_command_confirmed_unapproved` · 두 승인 저장소 원자료 이중 판독) · `text_command_notes` 경고 · status 칸 | ⓒ 자동병합 그대로(mf 충돌 0). theirs 의 `approval_store_raw_paths`(~/.cys/approvals-ttl.json · approvals.json)는 우리 approval.rs `store_root/records_path/ttl_records_path`(mt approval.rs:541-552 · 799)와 일치. 우리 BOM 벗기기 오버레이(ledger approval #4)와 달리 raw `from_utf8+serde` 판독 → BOM 파일이면 Err → false = 종전 거부 경로(안전 방향). ⓓ(승인 게이트 관련) 경미 |
| main.rs `spawn_office_bridge` (base L1933-1987) | pythonw.exe 우선(cysr-console-flicker-r2) · UTF-8 env 쌍(S2) · Job 결박 | 시그니처 `(state_dir, socket_path)` · managed/legacy 계획 · 재기동 상한 · 옛 브리지 교체(`replace_old_bridge` = 신호 전송) | ⓒ 자동병합 OK(호출처 mt main.rs:1457 이미 2인자). ⓓ: `replace_old_bridge` 는 포트 점유 프로세스에 종료 신호 — 맥 한정·주인 판별 실패 시 미교체(main.rs 2093-2120). 윈도 legacy 기본이라 pythonw+stdin null 경로 = 종전 |
| handlers.rs read_text since_line (base L6612-6621) | `scrollback_stale` 칸 | 반향 줄 제외 · `repaint_echo_skipped` | 위 충돌 #1 로 해소 · 나머지 auto 정합 |
| state.rs ingest_output (base L6824-6827) | last_line_at | echo_record_lines | 위 충돌 #1 로 해소 |
| cys.rs `run_doctor_diagnostics` | `diag_pack_auto_hold` | `diag_claude_tui` | 인접 추가 · 자동병합 · 무위험 |
| alert_route.rs | `routable` 에 `queue.persist_blocked` | remedy 14종 주석 · 시험에 `QueueBlockDiag::default()` · screen_diag 키 비유출 단언 | 다른 함수 · mt governance QUEUE_REMEDY_CODES=14(:9769) 정합 · 무위험 |
| factory_reset.rs | `dept-requests`(EXACT 28) · ResetRoots `claude_config_dir`/`defaults_domain` · 시험 리터럴 갱신 | claude_tui 원장 되돌림(build_plan · execute_quarantine) · EXACT2 12 · WIN_STATE 24/ATOMIC 9(approval-lane) | ⓒ 자동병합 · 배열 길이/원소 수 일치(28/12/24/9 — 스크립트 실측). upstream 새 시험은 `fake_roots`/`seed_practice_tree`(ours 갱신본) 경유 → 리터럴 누락 0. ⓓ: 완전 초기화가 사용자 settings.json 의 `tui` 키를 지움(값 정확히 "default" 일 때만) |

## 4. 고정 항목 대조 (덮어쓰기 금지 목록)

- D-U3 출처 창·rate_limited 표 안 리터럴: 충돌 state #2 융합으로 시험 보존 · 프로덕션은 auto-merge 로 무변경(upstream state.rs 에 rate_limited 변경 0).
- H-AUTH-SELFLOOP(create_surface_with_env 소비 파일 = handlers.rs·state.rs): upstream 새 호출은 state.rs 안(검체 이음매) → 유지. 단 §2 인자 수 수리 필요.
- D-mac-1 authoritative_config_dir: 범위 내 충돌 덩어리 무접촉. upstream surface.list/org.status `account` 칸(handlers mt :6118 · :10434 `seat_account_map`)은 accounts.rs `seat_identity_view_at` 가 공급 — HEAD accounts.rs:2344 는 `authoritative_config_dir()` 사용 → accounts 담당이 그 경로 보존해야 함(교차 확인 요청).
- 자체 자동갱신(src/update/*): 범위 내 충돌 없음. upstream pack.rs 주석의 "GUI 인앱 업데이트" 언급은 우리 삭제분(앱 updater)을 가리키는 문구일 뿐 코드 경로 아님.
- 1.1.8 ledger: main.rs #2(시험 모듈 끝·d6 꼬리 주석 금지) · approval ⑲(golden 고정) 선례와 위 판정 합치.

## Agent B — UI + Tauri 범위 병합 판정 (HEAD int/1110-upstream ↔ v0.14.48 · base v0.14.43)

근거: `scratchpad/mt/*`(merge-tree 산출) · `git show HEAD|v0.14.43|v0.14.48` · 자동 병합분은 `git merge-file` 로 scratchpad(`am/`)에 재현(저장소 무접촉).
HEAD 판 번호 = **1.1.8**(ui/package.json · tauri.conf.json · src-tauri/Cargo.toml · Cargo.toml 전부 실측). 1.1.10 으로 올릴지는 리드 TK-G 결정(이 표 범위 밖).

## 1. 충돌 덩어리 판정

| 파일 | # | ours(1줄) | theirs 추가(1줄 · 커밋) | 판정 | 위험 |
|---|---|---|---|---|---|
| ui/src/main.ts | 1 (L200-217) | usagebar `windowView` import + `./updateresult`(1.1.8 U4 결과 알림 · c70631b5) | `accountCardLabels`·`AcctRow`·U1 타입 3종 · `./seatacct`(11a9d4ca) · `./officetab`(0573ed90) · starvednotice `starvedShouldPop/KeyHasHead/PopAgeMs`(52393b3b·75d87c66·7c45c8cf) · `./updatenotice` · `./deptcreate` | ⓒ fuse: ours 두 줄 유지 + `accountCardLabels, type AcctRow` + seatacct·officetab import + starvednotice 확장 import 채택. **버림**: `UsagePrimary/UsageLine/UsageViewMode`(U1 패널 전용) · `./updatenotice`(우리 HEAD 에 파일 없음 = U4 제거 · 넣으면 모듈 없음 tsc/번들 실패) · `./deptcreate`(U17 미수용 · 레저 118 #5). 덩어리 **위 자동 병합 4줄**(`sanitizeUsageMode, nextUsageMode, sanitizeFoldKeys, USAGE_MODE_LABEL`)도 사용처 0 → 지움 권고 | 자동 병합된 office(1406-1463)·좌석 계정(5421-5440)·기아 경보(9493·9662) 코드가 이 import 들을 부른다 — ours 만 취하면 tsc 미해결 이름 8+ |
| ui/src/main.ts | 2 (L251-257) | wheelgate import 에 추가 없음 | `shouldSuppressWheelWin, WinWheelNoticeGate, WIN_WHEEL_NOTICE_TEXT/TITLE`(3a3ce219) | ⓑ keep ours (D5 · 아래 §4) | 넣고 #4 를 ours 로 두면 미사용 import 만 남음(무해) |
| ui/src/main.ts | 3 (L2588-2598) | `exitedPaneKeys` 집합(v116 닫기 보호 · c926328f) | `const winWheelNotice = new WinWheelNoticeGate()`(3a3ce219) | ⓑ keep ours (theirs 줄 버림) | exitedPaneKeys 빠지면 closeguard 배선(3084·3085·6565) 컴파일 실패 |
| ui/src/main.ts | 4 (L3873-3931) | Windows 휠 = `altWheelAction` → PgUp/PgDn `sendRaw` + 접기 안내(614f5c51 D5) | 억제 시 `return !suppressed` + 첫 억제 1회 토스트 「휠 스크롤 꺼짐 — /tui default」(3a3ce219) | ⓑ keep ours (§4 · 단 ⓓ급 안전 쟁점 상신) | 둘 다 붙이면 xterm 은 마지막 `attachCustomWheelEventHandler` 하나만 쓴다 — 융합 불가 · 토스트 문안은 D5 아래서 거짓 |
| ui/src/main.ts | 5 (L3983-3987) | `exitedPaneKeys.delete(paneKey)` | `winWheelNotice.forget(paneKey)`(3a3ce219) | ⓑ keep ours | — |
| ui/src/main.ts | 6 (L5080-5403) | (없음 — 원작자 U1 사이드바 배선 미수용 · 레저 118 #82 「사용량 패널 절대」) | U1 사이드바 패널 전체 + D1/D2 보기 방식·묶음·상자별 리셋/소진(747da25d) · `refreshAccountsShared`·`renderUsageBar` | ⓑ keep ours (ⓔ 사유: wsusage.ts 패널 절대) | 덩어리 뒤 `}` 는 ours 쪽 refreshSidebarStatus 를 닫는다(정합 확인). **부작용**: 자동 병합된 0.14.45 부서 카드 계정 줄 `wsAcctIndex()` 가 `ccAccounts` 를 읽는데 ours 는 CC Live 탭이 열려야만 채운다 → 카드 이름이 「계정 미확인」으로 떨어짐. 처방: `wsAcctIndex` 재료를 우리 사이드바 15초 폴러 `accountsCache`(ours main.ts:532-547 · 같은 usage_accounts_all 모양)로 — 【추정: 형 호환은 AcctRow 캐스팅으로 충분】 |
| ui/src/main.ts | 7 (L6638-6693) | (없음 — U2·U3 구멍 보류 미수용 · 레저 X1) | `holdRolePane/reanchorAuto/forgetDaemonEpoch/pruneHoleUntil` 본문 + `seatAccts.delete`(11a9d4ca) | ⓑ keep ours | 좌석 계정 캐시 정리는 자동 병합된 removeDeadPane 쪽(merged 6259-6260)에 이미 있음 — 유실 없음 |
| ui/src/main.ts | 8 (L7541-7626) | cycle-verify 분기 뒤 바로 일반 pending | C2 본부 전용 종류→「그 부서로 이동」· 응답 불가 부서(`!origin.replyable`) · U16 team-create 카드 · C3 정보성 「확인」(e0c26eb2) | ⓒ fuse: **C2 두 분기 + C3 분기 채택 · team-create 카드 분기만 버림**(D-TEAM 휴면 · 레저 118 결정①). 필요한 이름(isHeadOnlyProcedureKind·isConfirmableNotice·NOTICE_CONFIRM_LABEL·jumpToDeptSurface·FeedOrigin)은 자동 병합으로 이미 존재 | feedwiring-0144.test.ts 「iHead < iTeam」 핀은 team-create 분기가 없으면 iTeam=-1 로 적색 → itDormant 또는 단언 수정 |
| ui/src/main.ts | 9 (L11188-11196) | 글자 배율 → `renderSidebarUsage(...)`(우리 wsusage · a587202b) | `renderUsageBar()`(747da25d) | ⓑ keep ours | theirs 채택 시 미정의 함수(U1 블록 버렸으므로) |
| ui/src/style.css | 1 (L432-547) | 주석 2줄(원작자 #wsbar-foot 미수용) | `#wsbar-foot`·`#wsbar-usage …`·D1 `.usage-headrow/.usage-mode/.usage-group-head`·U17 `#wsbar-expert`(747da25d 등) | ⓑ keep ours (레저 118 style #2 와 동일) | `.modal p{overflow-wrap}` 는 ours 쪽 주석 바로 아래에 이미 있음 — 확인됨 |
| ui/src/style.css | 2 (L1356-1392) | `#restore-brief` 카드 규칙(ffcb8500) | `#cc-office-repair` 3줄(0573ed90) + Feed C2/C3 `.feed-dept-head/.feed-bulk/.fi-ended-mark`(e0c26eb2) | ⓒ union(ours 먼저 + theirs 전부) | 없음 — 셀렉터 겹침 0 |
| ui/package.json | 1 | `"version": "1.1.8"` | `0.14.48`(1a3a9dda) | ⓑ keep ours | — |
| src-tauri/tauri.conf.json | 1 | `productName "cysr"` · `1.1.8` | `"cys"` · `0.14.48` | ⓑ keep ours | productName 되돌리면 cysr.app 브랜딩 붕괴. updater 블록은 양쪽 무변경(pubkey 만 · endpoints 없음 유지) |
| src-tauri/Cargo.toml | 1 | `1.1.8` | `0.14.48` | ⓑ keep ours | — |
| Cargo.toml | 1 | `1.1.8` | `0.14.48` | ⓑ keep ours | 자동 병합분: `exclude += vendor/vt100` · `vt100 = { path = "vendor/vt100" }`(1f6d899c · vendor/vt100 트리 신규 추가) — 수용 시 vendor 트리도 함께 들어와야 빌드됨 |
| Cargo.lock | 1·2 | cys-app·cys-terminal `1.1.8` | `0.14.48` | ⓑ keep ours | vt100 항목은 이미 path 형(source·checksum 없음)으로 자동 병합 — 해소 후 `cargo metadata --offline` 로 정합 재확인 |
| src-tauri/src/main.rs | 1 (L4879-4917) | `read_operator_token_for` → 우리 `daemon_state_dir_for`(451d7861 · phoenix 원장 7528 도 사용) | 같은 계산을 `operator_token_dir_for` + 순수 `windows_token_dir` 로 추출(e0c26eb2 · C2 응답 허용 판정이 사용) | ⓒ fuse + ⓓ: theirs 본문 채택(`operator_token_dir_for`) · ours `daemon_state_dir_for` 는 `operator_token_dir_for` 로 위임하는 1줄 래퍼로 남기거나 7528 호출처 이름 교체 | 두 계산은 줄 단위 동일(Windows: LOCALAPPDATA\cys + 슬러그 · 비-Windows: 소켓 부모) — 실측 대조. 토큰 경로 = 보안 경계(feed_reply 허용 판정)이므로 ⓓ 표기 |

## 2. 자동 병합 겹침 파일 — 의미 위험

| 파일 | ours 변경 | theirs 변경 | 같은 함수? | 판정/위험 |
|---|---|---|---|---|
| ui/src/usagebar.ts | 문자열 cys→cysr 11곳(d1ac126b) | D1/D2 모드·묶음·상자(185/40) | 아니오(문구 함수 ↔ 모델 함수) | 안전 · cysr 11/11 보존 실측 · 새 UI 문자열에 `cys` 0 |
| ui/src/wheelgate.ts | (d) 절에 「D5 실현」 주석 5줄 | (e) 절 「억제된 휠을 PgUp/PgDn 으로 안 보내는 이유」 + `WinWheelNoticeGate` 클래스(58d5c8e2·3a3ce219) | 아니오(주석·신규 export) | 술어 무변경. **(e) 주석이 우리 D5 동작과 정면 모순**으로 남는다 → 주석에 「cysr 은 D5 로 번역함 · 모달 위험 쟁점 = §4」 단서 추가 권고. 클래스는 미사용 export 로 무해 |
| ui/src/starvednotice.ts | wait 집합에 `seat_unknown`·`seat_no_agent`(17f40a9c) | 0.14.48 D 대기/막힘 분리 · `stale_screen` 사람 손 코드 · 구간당 1회 팝업 | 아니오 | 우리 두 코드는 `starvedCalmKind` → "wait" = 회색 「⏳ 배달 대기 중」— 의도와 부합. 단 `stale_screen` 은 데몬(governance.rs) 쪽 수용 여부에 종속(cysd 범위) |
| ui/src/starvednotice.test.ts | 앵커 재조준(우리 eventSock) | 기대값 갱신 | 부분 | 우리 앵커 줄 보존 실측(merge-file 0 충돌) — 실행 확인 필요 |
| ui/src/feedclass.ts | 문구 cysr 1곳 | C2/C3 판정 함수 77줄 추가 | 아니오 | 안전 |
| ui/src/usagewiring.test.ts | U1 시험 itDormant 격리(UNW · 17f40a9c·ff2fc8bd·3747431a) | 0.14.44 D1/D2 describe 2개(일반 `it`) · 앵커 `const boxEl =` | 예(같은 renderUsageBar 핀) | **적색 확정**: 새 describe 는 ours 에 없는 `renderUsageBar`·`USAGE_MODE_KEY` 를 핀 → `itDormant` 로 전환(우리 관례). 기존 #336 「최상위 renderUsageBar 호출 없음」은 keep-ours 와 정합 |
| ui/index.html | 51/22(T4 상담소·아고라 · #ws-credit 삭제 319f3526 · cysr 문구) | 오피스 안내를 `#cc-office-hint-text` + `#cc-office-repair` 단추로 | 아니오 | 안전 · #ws-credit 부활 없음 · main.ts office 배선이 찾는 id 2개 공급 |

## 3. 새 Tauri 명령 · 교차 의존

- invoke_handler 신규 3: **`feed_list_all` · `office_health` · `repair_office_assets`** — 자동 병합으로 merged 목록에 이미 등재(ours 명령 전건 보존 · 누락 0 실측). 추가 작업 불필요.
- ⓓ 보안 검토 요점:
  - `feed_reply(socket)`: 부서 소켓 응답은 `feed_reply_socket_allowed_with`(등록부 ∧ `cys-dept-*` 이름 ∧ 토큰 폴더 ≠ 본부 ∧ 파이프 슬러그 완전일치)로만 · 토큰은 백엔드만 다룸 · 시험 `c2_reply_socket_allowed_*`.
  - `office_health`: 127.0.0.1:8642 GET /health 탐침(lib `cys::bridge_probe_get` · 64KB 상한).
  - `repair_office_assets`: 사이드카 `cys pack-heal --missing-only <rel>` 10초 상한 · `.pack-version == CARGO_PKG_VERSION` 일 때만 · 병합 대기 원장 항목은 건너뜀 · Windows 단추 꺼짐 · 맥 자동 1회. 우리 팩 판 번호가 앱 판(1.1.8)과 다르면 늘 `version_mismatch`(무동작 · 안전 쪽) 【추정: 팩 판 체계 미실측】.
  - 오피스 iframe 은 IPC 불가: capabilities `default.json` = `windows:["main"]` · remote 없음 · 시험 `office_iframe_has_no_ipc_path_and_commands_registered`. 우리 아고라 창(counsel::open_agora_window)은 capabilities 밖 = IPC 없음 → 이 시험의 `windows==["main"]` 단언과 정합.
  - open_url 화이트리스트·T4 webview·updater: upstream v43..48 diff 에 해당 변경 0(main.rs @@ 4785·4845·4859·7777·15532 뿐).
- **컴파일 교차 의존(다른 에이전트 범위)**: tauri main.rs 자동 병합분이 `cys::{bridge_parse_head, bridge_probe_get, BridgeProbeError, BridgeProbeReply, BRIDGE_PROBE_BODY_CAP, OFFICE_BRIDGE_PORT}`(HEAD src/lib.rs 에 **없음** · v0.14.48 lib.rs 에 있음) 와 `cys pack-heal --missing-only`(HEAD src/bin/cys.rs 에 **없음**)를 요구 → lib.rs·cys.rs 해소에서 반드시 수용해야 app 빌드 녹.
- **TS 미해결 위험(keep-ours 만 할 때)**: `planOfficeTab, repairOutcomeOf, OfficeCtx, accountCardLabels, buildAcctIndex, buildWsAccountGroups, SeatAcctSig, AcctIndex, AcctRow, starvedShouldPop, starvedKeyHasHead, starvedPopAgeMs` — 전부 #1 fuse 로 해결.
- **브랜딩**: 신규 파일 `ui/src/seatacct.ts` 사용자 문자열 2곳에 `cys`(L53 「이 에이전트의 계정은 cys 가 확인할 수 없습니다」 · L230 「이메일은 cys 가 읽지 않습니다」) → cysr 로 교정(ⓒ). officetab.ts·WIN_WHEEL 문안·main.ts 신규 문자열에는 `cys` 0.
- **적색 예상 시험(수정 대상)**: `wheelgate.test.ts` 신규 「배선 핀(main.ts)」(winWheelNotice·`return !suppressed` 요구) · `feedwiring-0144.test.ts` 「iHead < iTeam」 · `usagewiring.test.ts` D1/D2 describe · `starvednotice-split.test.ts` 의 governance.rs 문장 머리 핀(데몬 v0.14.47 문장 — cysd 해소 결과에 종속).

## 4. 휠 상호작용 (D5 altscroll ↔ upstream wheelgate)

- upstream 의 휠 변경은 **억제 층을 하나도 더하지 않는다**: `shouldSuppressWheelWin` 술어 무변경, 추가된 것은 (e) 주석 + `WinWheelNoticeGate`(토스트 1회 판정) + main.ts 배선(#2·#3·#4·#5)뿐. 우리 `altWheelAction` 은 내부에서 같은 술어를 부르고(altscroll.ts:38) 억제 시 PgUp/PgDn 을 직접 보내므로, upstream 이 우리 핸들러보다 **먼저** 휠을 삼키는 경로는 없다 — 다만 #4 를 theirs 로 받으면 우리 번역이 통째로 사라지고 「휠 스크롤 꺼짐」 토스트(health)가 뜬다.
- ⚠ upstream (e) 의 근거는 우리 D5 에 대한 **실질 반론**이다: Claude Code 2.1.291 fullscreen 에서 권한 확인 Select 모달이 떠 있고 내용이 화면에 들어가면 Scroll 처리기가 페이지 키를 양보(`yieldsPageKeysWhenContentFits: modalSlotActive`) → PgUp/PgDn 이 `select:pageUp/pageDown` 으로 가 **휠이 선택 항목을 움직이고**, 그 뒤 Enter 는 다른 선택지를 승인한다. 우리 altscroll.ts 근거 주석(52-89)은 2.1.280 판독으로 이 모달 경로를 다루지 않는다(검색 「modal/select」 0건).
- upstream 의 본 처방은 UI 가 아니라 Rust `src/claude_tui.rs`(신규 · d2c6c405 외): Windows 좌석 settings.json 에 `tui` 가 없으면 `"default"`(classic) 기록 → 억제 술어 자체가 불충족(alt 아님) → 휠은 xterm 정상 스크롤. 이를 수용하면 우리 D5 번역은 사용자가 fullscreen 을 명시한 좌석에서만 발화해 모달 위험 노출이 줄어든다(상보적) — Rust 범위 결정.
- 권고: main.ts #2~#5 = ⓑ keep ours(D5 유지 · 토스트 미배선 · 문안이 D5 아래서 거짓). 동시에 📌 상신: 「D5 PgUp 번역 × 모달 Select 이동」 위험을 master 판정 사안으로(선택지: claude_tui.rs 동반 수용 / cursor 기본 전환은 히스토리 오염이라 불가 / 모달 감지 전까지 현행 유지) — 실기 미검증 【추정 아님: 근거는 upstream 정적 판독 인용 · 우리 쪽 실측 0】.
- 이름 충돌 주의: upstream 「D5」 = lib.rs `d5_gate_for_os`(env 옵트인) — 우리 「1.1.5 D5」(휠 번역)와 무관한 동명이다.

## Agent C — pack python · CI · installers · docs (HEAD int/1110-upstream ⟵ v0.14.48 · base v0.14.43)

Evidence = merge-tree extract `scratchpad/mt/` (hunk line numbers refer to those files) + `git merge-file` re-runs in `scratchpad/am/` (read-only, repo untouched). 【추정】 = not measured.

## 0. Cross-cutting findings (read first)

1. **phoenix: `_run_decoded` drops `**NOWIN`** — upstream helper body `subprocess.run(cmd, capture_output=True, **kw)` (mt javis_phoenix.py ≈L1090) and hunk 3 `subprocess.run(cmd, capture_output=True, timeout=8)` fail our X-NOWIN rule (`test_nowin_captured_spawns.py` scan of theirs-resolved file → missing lines [1080, 917]). Fuse = `subprocess.run(cmd, capture_output=True, **NOWIN, **kw)` inside `_run_decoded` **only** (no caller passes NOWIN → avoids duplicate-kwarg TypeError on nt) + `**NOWIN` on hunk 3. Do not use `kw.setdefault("creationflags")` — `run_bootstrap_health.py:4906` pins `"javis_phoenix.py": 1` creationflags literal. Pack captured-call total 249 → ≈241 (floor 200 ok).
2. **phoenix: ours-only `_ps_table()` keeps `text=True`** (43a4e73f A3 ps axis; theirs-resolved L2036). Upstream `test_phoenix_encoding_default.t_source_pins` requires **0** `text=`/`universal_newlines` kwargs in the file → must convert to `_run_decoded(["ps","-axo","pid=,ppid=,args="], _dec_any, timeout=10)`. Otherwise the new test is red in all 5 lanes + windows T5b.
3. Other upstream pins already satisfied after taking theirs: `_force_utf8_stdio()` before `"--selftest" in sys.argv` in `main()` (offsets 32 < 338); both manual-template `json.load(open(..., encoding='utf-8'))` pins present; no encoding-less text `open()` left (AST scan). Our module-level `_pin_utf8_stream` (229df16e) stays alongside upstream `_force_utf8_stdio` (idempotent duplicate). Whether our import-time reconfigure disturbs the test's shim scenarios is 【추정 — must run `test_phoenix_encoding_default.py` + `javis_phoenix_encoding_smoke.py`】.
4. Ours D-mac-1 / a44a6747 preserved: `_restore_config_dir`, `_validate_profile_dir`, `_operator_token_for` exist only in ours and survive; `fresh_expected` length identical to HEAD (1427 chars) → ours order kept; `"unobserved"` 5 occurrences = HEAD.
5. **windows-health coupling**: auto-merged ci-branch `FILTERED_CARGO_REQUIRED["windows-health"]` (mt ci-branch.yml:244-249) now **requires** `--lib agy_statusline::` and `--lib claude_tui::` run lines → the windows-health hunk must be fused (not ours-only), and `src/claude_tui.rs` + `mod claude_tui` must be adopted by the Rust agent, else `cargo_filter_count` red. If claude_tui is excluded, drop the dict entry too.
6. **USER-MANUAL naming/update gates** (`ui/src/publicdocs.test.ts`): manifest includes USER-MANUAL.md, NOTICE.md, docs/RELEASE.md, office-boot.js (:98-104); rules = 0 `CYSJavis`, 0 bare `cys` outside code, inline code head `cys <lower>` red (:120-125), **0 「업데이트」/「Update」** (:310-313), GONE list incl. `CYS_UPDATE_VERIFY`, `CYS_UPDATE_CHECKED_LAUNCH` (:72-84). Upstream manual diff adds 251 lines, 49 with bare `cys`, 2 「업데이트」; ~27 bare-`cys` lines land **outside hunks via auto-merge** (rough regex: ours 10 → merged 37 lines). ⇒ whole-file pass `cys`→`cysr` (prose + human command heads), 업데이트→갱신, verify with `cd ui && bun test publicdocs`.
7. pyseal census fused `REFERENCING_FILES` = HEAD 35 + {`test_hud_bridge_0144_specimen.py`, `test_phoenix_encoding_default.py`} = **37** (count = `len(want)`, pinned as set-equality vs grep, test_pyseal_census.py:374-406). Order key=str: `…test_hook_launcher_split.py`, `…test_hud_bridge_0144_specimen.py`, `…test_javis_counsel.py`, `…test_lane_redirect.py`. RUST_SPAWN_PIN / BUNDLED_RESOLVER_FILES unchanged by upstream (new Rust files have no needle/bundled_python) — re-run after Rust agent resolves src-tauri/main.rs.

## 1. Conflict hunks

| file | # | ours | theirs (commit) | verdict | risk |
|---|---|---|---|---|---|
| .github/workflows/ci-branch.yml (mac loop) | 1 (L1037) | `fresh_honest f1_production_path \` / `r32_restore_budget \` (g2_ack_only already at L1014) | + `test_phoenix_g2_ack_only` + `test_phoenix_encoding_default` (121ab280) | ⓒ ours lines + append ` test_phoenix_encoding_default` to r32 line; **skip g2** (dup at L1014) | low — dup name runs twice / parity gate ok either way |
| ci-branch.yml (mac loop) | 2 (L1053) | 2 long lines of our 34 extra tests ending `test_javis_counsel; do` | `test_capgate_surrogate_deny test_hud_bridge_0144_{bootjs,specimen,unit}; do` (16a312c7) | ⓒ ours + `\` then `test_hud_bridge_0144_bootjs test_hud_bridge_0144_specimen test_hud_bridge_0144_unit; do`; **skip surrogate_deny** (ours L1020, file identical to upstream) | low |
| ci-branch.yml (ubuntu-pack-suite) | 3 (L1877) | same as #1 | same | ⓒ same as #1 (g2 at L1853) | low |
| ci-branch.yml (ubuntu) | 4 (L1893) | same as #2 | same | ⓒ same as #2 (surrogate at L1859) | low |
| .github/workflows/pack-release.yml | 1 (L339) | as ci #1 (g2 at L315) | as ci #1 | ⓒ as ci #1 | low |
| pack-release.yml | 2 (L355) | as ci #2 (surrogate at L321) | as ci #2 | ⓒ as ci #2 | low |
| .github/workflows/release.yml (build) | 1 (L627) | as ci #1 (g2 L603) | as ci #1 | ⓒ as ci #1 | low |
| release.yml (build) | 2 (L643) | as ci #2 (surrogate L609) | as ci #2 | ⓒ as ci #2 | low |
| release.yml (pack-artifacts) | 3 (L1668) | as ci #1 (g2 L1644) | as ci #1 | ⓒ as ci #1 | low |
| release.yml (pack-artifacts) | 4 (L1684) | as ci #2 (surrogate L1650) | as ci #2 | ⓒ as ci #2 | low |
| .github/workflows/windows-health.yml | 1 (L289) | `update::` filtered run (1.1.8 U1, L290-295) **+ new step** U5 install-link lock contract (L297-359, curl jarvis.godmeyou.kr, PowerShell 5.1/7) | `agy_statusline::` + `claude_tui::` filtered runs (1f84793a) | ⓒ keep ours L290-295, insert theirs L361-374 right after L295 (same step, before blank + U5 step); renumber ordinals (update=여섯째 → agy=일곱째, claude_tui=여덟째); keep U5 step untouched. ⓓ note: U5 step does network fetch (ours, unchanged) | med — required by ci-branch FILTERED_CARGO_REQUIRED; depends on claude_tui.rs adoption |
| cysjavis-pack/bin/javis_phoenix.py | 1 (L705 `_cys_self_identity`) | `subprocess.run(..., text=True, encoding="utf-8", errors="replace", timeout=10, **NOWIN)` | `_run_decoded([...], timeout=10)` (9bc3001c) | ⓒ theirs; NOWIN via `_run_decoded` (see §0-1) | low |
| javis_phoenix.py | 2 (L726 `_daemon_identity`) | same pattern, timeout=12 | `_run_decoded(cmd, timeout=12)` (9bc3001c) | ⓒ theirs + NOWIN-in-helper | low |
| javis_phoenix.py | 3 (L927 `_emit_evt`) | utf-8 text + NOWIN | `subprocess.run(cmd, capture_output=True, timeout=8)` bytes, rc only (9bc3001c) | ⓒ theirs + `**NOWIN` (test_nowin_captured_spawns red otherwise) | med if NOWIN forgotten (Windows console flicker regression) |
| javis_phoenix.py | 4 (L1207 `cys()`) | utf-8 text + env + NOWIN | `_run_decoded(cmd, timeout=timeout, env=env)` (9bc3001c) | ⓒ theirs + NOWIN-in-helper; same decode semantics (`_decode_captured` = utf-8/replace); owner-token code outside hunk unaffected | low |
| javis_phoenix.py | 5 (L2313 `rollback_proposal`) | snapshot `list` utf-8 text + NOWIN | `_run_decoded([...], _dec_any, timeout=15)` (9bc3001c) | ⓒ theirs + NOWIN-in-helper | low |
| javis_phoenix.py | 6 (L4292 manual_restore template) | `python3 -c "import json;… open('$TOPO', encoding='utf-8')…"` | + `sys.stdout.reconfigure(errors='backslashreplace')` (4a7f6459) | ⓐ theirs (keeps the utf-8 pin string) | low |
| javis_phoenix.py | 7 (L4301 template heredoc) | (nothing) | `sys.stdout.reconfigure(errors='backslashreplace')` (4a7f6459) | ⓐ theirs | low |
| javis_phoenix.py | 8 (L4325 `cmd_gen_manual`) | `open(sp, "w", encoding="utf-8")` | + `newline="\n"` — manual_restore.sh LF on Windows (f650373e) | ⓐ theirs (Windows) — ⓓ file write, benign | low |
| javis_phoenix.py | 9 (L4411 `_launchctl`) | `text=True` (locale, strict) + NOWIN | `_run_decoded(..., _dec_any, ...)` (9bc3001c) | ⓒ theirs + NOWIN-in-helper (improves on 229df16e's "leave native tools" — `text=True` strict could raise) | low |
| javis_phoenix.py | 10 (L4494 `_schtasks`) | `text=True` + NOWIN | `_run_decoded(["schtasks"…], _dec_any, …)` (9bc3001c) | ⓒ same (Windows) | low |
| javis_phoenix.py | 11 (L4591 `_win_restart_daemon` taskkill) | `text=True` + NOWIN | `_run_decoded([...taskkill...], _dec_any, timeout=15)` (9bc3001c) | ⓒ same (Windows) | low |
| javis_phoenix.py | 12 (L4833 `_deploy_restart`) | `shell=True … text=True … **NOWIN` | `_run_decoded(restart_hook, _dec_any, shell=True, …)` (9bc3001c) | ⓒ theirs + NOWIN-in-helper; ⓓ shell=True user hook — semantics unchanged (decode only) | low |
| javis_phoenix.py | 13 (L5034 `cmd_deploy` apply_cmd) | `shell=True … text=True … timeout=600, **NOWIN` | `_run_decoded(apply_cmd, _dec_any, shell=True, timeout=600)` (9bc3001c) | ⓒ same as #12 | low |
| javis_phoenix.py | (outside hunks) `_ps_table` | ours-only `text=True` (43a4e73f) | — | ⓒ convert to `_run_decoded(..., _dec_any, timeout=10)` (§0-2) | **high** — new test red |
| cysjavis-pack/bin/javis_state_snapshot.py | 1 (L435) | `open(mpath,"w",encoding="utf-8")` | identical + comment (2d40f1df) | ⓐ theirs (comment only) | none |
| javis_state_snapshot.py | 2 (L562 `do_verify`) | read manifest utf-8 only; `except (OSError, json.JSONDecodeError)` | try utf-8 then locale default, pick candidate whose stored files all exist; `except (OSError, ValueError)` (4a7f6459) | ⓐ theirs — superset; ours writes UTF-8 since 229df16e (2026-09-08), older cp949 generations possible on Korean Windows | low |
| javis_state_snapshot.py | 3 (L726 self-test) | `json.load(open(..., encoding="utf-8"))` | identical + comment (4a7f6459) | ⓐ theirs | none |
| cysjavis-pack/bin/tests/test_pyseal_census.py | 1 (L284) | `test_javis_counsel.py` (T3 2026-10-06) | `test_hud_bridge_0144_specimen.py` (0ff1a7e7) | ⓒ union, sorted: hud_bridge_0144_specimen **before** javis_counsel; total 37 (§0-7) | low (ⓑ sort check) |
| cysjavis-pack/web/office-boot.js | 1 (L23) | `MSG = "… 터미널에서  cysr init-pack --force …"` (our rename only) | B5 rewrite: `MSG_RETRYING/MSG_GAVE_UP/RETRY_DELAYS/…` (db343970) | ⓐ theirs — theirs-resolved file == v0.14.48 byte-for-byte; `MSG` no longer referenced (ours would leave MSG_RETRYING undefined); upstream removed the terminal command (naming gate trivially clean: 0 `cys`/CYSJavis); `test_hud_bridge_0144_bootjs` asserts banner has no terminal command | low |
| dist-win/cys.wxs | 1 (L3) | `Version="1.1.8"` | `Version="0.14.48"` (1a3a9dda) | ⓑ ours (Cargo.toml/tauri.conf.json/ui package.json all 1.1.8; bump is a separate ticket) | none |
| dist-win/cys-x64.wxs | 1 (L3) | `Version="1.1.8"` | `Version="0.14.48"` (1a3a9dda) | ⓑ ours | none |
| USER-MANUAL.md | 1 (L329) | agy auto-link mac/Linux, `cysr`, 「갱신」 | + Windows v0.14.45 auto-link paragraph, `cys`, 「업데이트」 (3a728d10) | ⓒ theirs content, adapt `cys`→`cysr`, 업데이트→갱신; depends on Rust agy_statusline adoption (else ⓔ) | med (gate) |
| USER-MANUAL.md | 2 (L366) | "Windows 는 자동으로 연결하지 않습니다…" (base text, cysr) | Windows `cmd /c` + `.cmd` wrapper block (3a728d10) | ⓒ theirs content adapted (`cys doctor`→`cysr doctor`, prose `cys`→`cysr`; paths `.cys\pack\hooks\cys-agy-statusline.cmd` stay) | med (gate) |
| USER-MANUAL.md | 3 (L1111) | toast single title `cysr queue list` | two classes red/grey (0.14.48) (2e6d1205) | ⓒ theirs adapted (`cysr`) — depends on UI main.ts 0.14.48 queue-notice adoption | med |
| USER-MANUAL.md | 4 (L1362) | Windows v0.14.43 note, 「갱신 뒤 `cysr approval sign`」 | + `--cwd` sentence (30adb62e) + v0.14.44 approval reasons table + cwd-neutral daemon binding (42d098cd) + same note w/ `cys`/업데이트 | ⓒ theirs new paragraphs adapted (`cys approval check`→`cysr …`, "cys 명령"→"cysr 명령"), keep ours final note; depends on approval.rs adoption | med |
| USER-MANUAL.md | 5 (L1911) | `CYS_QUEUE_QUIESCE_HOLD_SECS` row (`cysr`) | + `CYS_SCREEN_REPAINT_NUDGE` row (769b4d9a) + same row w/ `cys` | ⓒ ours row + theirs new row (no bare cys in it) — depends on repaint.rs | low |
| USER-MANUAL.md | 6 (L1945) | AGY/OUTSIDE rows (`cysr`, 갱신); **CYS_UPDATE_VERIFY / CYS_UPDATE_CHECKED_LAUNCH rows deleted** | AGY row + Windows (3a728d10) + base UPDATE rows | ⓒ take only theirs AGY-row delta (adapted); **do not re-add UPDATE rows** (publicdocs GONE list) | med |
| USER-MANUAL.md | 7 (L1961) | ALT_SCREEN rows (`cysr`) | + `CYS_WIN_TUI_CLASSIC_OFF` row (021a7f8a) | ⓒ ours rows + theirs new row adapted (`cys`→`cysr`) — depends on claude_tui.rs | med |
| USER-MANUAL.md | 8 (L2254) | troubleshooting table (`cysr`, 갱신, no in-app update row) | queue row grey/red 0.14.48 (2e6d1205) + base 「업데이트를 눌렀는데…」 row | ⓒ ours table + replace queue row with theirs adapted; **drop 「업데이트를 눌렀는데」 row** (in-app update removed, 업데이트 gate) | med |

## 2. Auto-merged overlap files — semantic check

| file | result | risk / action |
|---|---|---|
| .github/workflows/windows-build.yml | clean; T5b step (encoding test, no PYTHONUTF8) lands between T5 (L1186) and T6 (L1266); uses `CYS_INSTALL_DIR`, `CYS_INSTALL_VER`, `cys-installed-version.txt`, `runtime\python\python3.exe` — all exist in ours (L254-260, 499) | low — Windows lane; file already in pyseal list (`PYTHONDONTWRITEBYTECODE` line ok) |
| cysjavis-pack/bin/javis_hud_bridge.py | clean, parses; ours `Hub.watched` + `fleet_loop` gate (console-flicker-r2) + upstream B4 (_legacy_win, /health, lifeline, SIGTERM, `_nostdin()`) coexist. `_shutdown` uses `os._exit` so blocking `watched.wait()` doesn't stall exit. Upstream unit pins (`creationflags` count 1, every spawn has `_nostdin()`, no `os.kill(`/getppid) hold — ours added no spawns | low |
| cysjavis-pack/hooks/role-capability-gate.sh | merged == ours byte-identical (ours already carries 8b8d7505/ea06f6bb via 613b12a4/9eb9f2b0) | none — ⓓ security gate unchanged |
| cysjavis-pack/bin/tests/test_capgate_surrogate_deny.py | merged == ours == upstream | none (already registered in all 5 lists) |
| docs/RELEASE.md | clean; inserts upstream "★0.14.44 윈도우 실기 확인" checklist after our L420 (our RELEASE.md = our channel; upstream lane text was moved to docs/legacy/RELEASE-upstream.md by 29c29859). Inserted text has no bare `cys`/업데이트 | low — ⓒ consider rewording to our channel (1.1.10, release-note § refs point to upstream 0.14.44 notes) |
| NOTICE.md | clean; adds `vt100 0.15.2 (patched) | vendor/vt100/ | doy/vt100-rust (Jesse Luehrs) | MIT` row; our credit lines (29c29859 원문 복원) untouched; row has no `cys`/CYSJavis | low — valid only if Rust agent adopts `vendor/vt100/` (else ⓔ drop row) |
| cysjavis-pack/hooks/README.md + new hooks/cys-agy-statusline.cmd | clean; .cmd body `@echo off / set NoDefaultCurrentDirectoryInExePath=1 / cys usage-report-stdin --agy 2>nul / exit /b 0`; `.gitattributes` `cysjavis-pack/hooks/** text eol=lf` keeps LF (upstream intends LF) | low — ⓓ Windows exec wrapper (hardened against CWD exe hijack); binary name `cys` = machine call (allowed) |
| docs/RELEASE_NOTES_0.14.44..48.md (new) | add as history (ours keeps 0.14.5–0.14.43 notes); not in NAME_MANIFEST, no pyseal needle | none |

## 3. New upstream test files → our CI lanes

| test | kind | where to register | slots |
|---|---|---|---|
| test_phoenix_encoding_default.py | py | 5 pack loops: ci-branch mac (L1037 hunk) · ci-branch ubuntu (L1877) · pack-release (L339) · release build (L627) · release pack-artifacts (L1668) + windows-build T5b (auto-merged) | 5 + 1 |
| test_hud_bridge_0144_bootjs.py (skips w/o node) | py | same 5 loops (hunks #2/#4) | 5 |
| test_hud_bridge_0144_specimen.py | py | same 5 loops | 5 |
| test_hud_bridge_0144_unit.py | py | same 5 loops | 5 |
| test_capgate_surrogate_deny.py | py | **already present** in all 5 (ours) — do not duplicate | 0 |
| ui/src/{feedclass-0144,feedwiring-0144,officetab,officewiring,seatacct,starvednotice-split,usagebar-modes}.test.ts | ts | auto-discovered by `cd ui && bun test` (ci-branch ui-check · release) — no list | 0 |
| src/bin/cysd/{approval_a_tests,feed_sweep_tests,vt100_dim_tests}.rs | rust | via `mod` in cysd main.rs → `cargo test --bin cysd` (Rust agent) | 0 |
| `--lib agy_statusline::` / `--lib claude_tui::` filtered runs | rust (Windows) | windows-health (hunk) — required by FILTERED_CARGO_REQUIRED | 2 |
| vendor/vt100 crate tests | rust | workspace-excluded upstream (1f6d899c) → not run anywhere | 0 |

Total python list edits: 4 names × 5 loops = 20 tokens; parity gate stays symmetric.

## 4. Windows-impacting files

dist-win/cys.wxs, cys-x64.wxs (version only → ours 1.1.8) · windows-health.yml (agy_statusline + claude_tui filtered tests, U5 kept) · windows-build.yml (T5b cp1252-native encoding run) · javis_phoenix.py (manual_restore.sh LF, schtasks/taskkill decode, NOWIN on every captured spawn) · javis_state_snapshot.py (cp949 legacy manifest read) · hooks/cys-agy-statusline.cmd (new, LF, `cmd /c`) · javis_hud_bridge.py (`_legacy_win`, `HUD_WIN_NEW`) · office-boot.js (Windows asset repair off per manual).

## 5. Exclusion candidates (ⓔ)

None in this scope by itself. Conditional: USER-MANUAL hunks 1/2/6 (agy Windows), 5 (repaint), 7 (claude_tui), 3/8 (0.14.48 queue toast), 4 (approval reasons) and NOTICE vt100 row must be dropped if the corresponding Rust/UI features are excluded by other agents.

