# HANDOFF — TICKET=cysr-1116-integ-1120 (worker-1116integ · surface:2321)

- 브리프 = `~/axdev/master/briefs/1116-full/integ.md`(원장 spawn 13:29:41 · submitted true) + `_common.md`
- 가지 `integ/1116-r1120` ← `integ/1116` dea2e1853 · worktree `~/axdev/.wt/cys-1116-integ-1120` · push·태그·CI·gh 쓰기·서명·발행·앱 교체·실사용 데몬 접촉 = 0
- 통합 머리 = **bfb52cbd2(게이트 대상) + 이 HANDOFF 커밋** · 게이트 결과 폴더 = `~/axdev/.wt/cys-1116-integ-1120-gate/`
- master 판정 받음: 14:5x master#1e80c983 — 의미 충돌 ①~⑥ 처리 수용(④ = listenApp 유지 · defaultSlug 제거 · s2 시험 ① 좁힘)

## 0. 후임 c(worker-2 · surface:2336 · 11-20 21:42~22:2x · 브리프 = master/briefs/2026-11-20-successor-integ-1120c.md · 원장 spawn 21:41:53)

머리 = 1fc650bd4 + 이 문서 커밋. 이 좌석 커밋 2: 1fc650bd4(verifier 계약 블록 동기화) · 이 문서.

### 0c-1. g2 남은 붉음 1(L999 autopilot self-test 「javis_cycle_verifier.py 와 바이트 동일」) = **갈래 탓 debt-d** · 고침 완료
| 대조 | autopilot self-test |
|---|---|
| 기준선 dea2e1853 | PASS 343 / FAIL 0 |
| debt-d 머리 e5c0d229f | PASS 342 / FAIL 1(같은 검사) |
| 통합 ce52f5d8d | PASS 342 / FAIL 1(같은 검사) |
| 고친 뒤 1fc650bd4 | PASS 343 / FAIL 0 · verifier self-test 73/0 · test_wakeup_liveness 23 OK |
- 원인: debt-d e132ea232(V7 · U08 꼴)가 계약 블록 안 `kill_switch` 를 autopilot 쪽만 `exists → lstat(판독 불가 = 정지)` 로 바꿈 · verifier 는 그대로 → 두 블록 diff = 그 9줄뿐(scratch 추출 diff 실측). 범위 dea2e1853..HEAD 에서 두 파일을 바꾼 커밋 = e132ea232 하나.
- 고침 방향 = verifier 를 autopilot 문면으로 맞춤(V7 고침을 살림 · 되돌림 0).
- 우분투 L2108 이 초록이던 까닭: 이 self-test 는 ci-branch.yml 의 macos-rust-pack 잡에만 있음(ubuntu-pack-suite 잡 2074~2244 행에 cycle_autopilot·self-test 0건 · g2 L2108 로그에도 「self-test (」 0건). 맥 전용 도구 차이 아님.
- L999 묶음 단독 재실행 = `gate/g3-L999/` rc=0 · 1425s · 실패 단계 0.

### 0c-2. 부하성 단독 3회(§8 5종 · 머리 1fc650bd4 · load 2.2~5.0 · 결과 = `gate/flaky3{,b}.summary.txt` · 로그 `gate/flaky3{,b}/`)
| 시험 | 3회 |
|---|---|
| test_resource_gate_product_cpu T09TextCheckBounded.test_9b_hung_lookup | OK ×3(3.4~3.6s) · 파일 전체 43건 OK ×3 |
| test_dept_name_guard(전체 75건 · create_spawn_loser 포함) | OK ×3(84s 안팎) |
| test_phoenix_c6_reap | rc=0 · result passed · owned_residuals 0 ×3 |
| cysd seatkeep_input_ack_stall_ends_seat_when_consumer_never_resumes | ok ×3(10.6~11.5s) |
| cysd k17_refuse_mode_return_raises_settle_marker_but_cancel_key_does_not | ok ×3(0.9~1.1s) |
- 덧: c6_reap 를 TMPDIR=/var/folders(별칭 → /private/var)로 돌리면 통과 뒤 atexit teardown 에서 `_HarnessError: aliased_harness_root` 추적이 찍힘(rc 0 그대로) — 하네스가 모듈 적재 때 `tempfile.mkdtemp` 로 집을 잡기 때문. TMPDIR 정규 경로 1회 = 추적 0(`flaky3b/test_phoenix_c6_reap.tmpdir-canon.log`). 게이트는 TMPDIR 을 따로 주므로 g2·g3 로그엔 0건. 실행 환경 탓 · 고치지 않음.
- 첫 실행(flaky3)의 cysd 2종 rc=127 = 내 스크립트 PATH 에 cargo 없음(시험 미실행) → flaky3b 로 다시 돎.

### 0c-3. 손대지 않음
- 앞 좌석의 e2e-chat 허용 폭 판단(0017bbc91 · 제품 코드 무변경) = master 가 받음 · 그대로.
- push·태그·배포·공개 후보 확정 0.

## 0b. 후임 b(worker-2 · surface:2331 · 11-20 18:43~21:4x · 브리프 = master/briefs/2026-11-20-successor-integ-1120b.md · 상한 3h 도달로 매듭)

머리 = 932188962 + 이 문서 커밋. 이 좌석 커밋 6: 231159d5e(secret-scan·이름 정리) · aaac932e7(스킬 **NOWIN) · 0017bbc91(핀·검사 4종 + e2e-chat 허용 폭) · 88082ede2(seatkeep f244fc34d 병합 · master#4f490f50) · 932188962(스킬 stdin=DEVNULL) · 이 문서.

### 0-1. g1 붉음 분류(대조 기준 = 기준선 dea2e1853 · 갈래 머리 · 병합 직전·직후 — main 4b398dfd9 은 기준선의 조상이고 붉은 시험·핀이 아예 없어 대조 불가)
| 붉음 | 분류 | 근거 | 처분 |
|---|---|---|---|
| secret-scan 6 · H-SECRET-1 | 갈래 탓(b23·flaky·seatkeep 문서 · s6 team.rs) | 해당 줄 기준선에 없음 · team.rs 2줄 = s6 머리에서 처음 | 231159d5e · --all clean 2402파일 |
| ci nowin ×6(L999·L2108) | 갈래 탓 asset-skills | 머리 1ff82d08a FAILED 6 · 기준선 OK(실측) | aaac932e7 |
| lib d3_prime 「자동 기동 0」 | 병합 탓 debt-d × b23 | debt-d 머리 핀 문자열 1 · b23 이 같은 match 를 여러 줄로 | 0017bbc91 — Daemon 갈래 안 Prime 존재로 |
| cys-app c2 조작자 토큰 | 갈래 탓 s6(codex 1R B1 seat-group-pause --operator) | s6 머리 계수 2 · 핀 1 | 0017bbc91 — 정확히 두 자리 · 각 자리 if operator 안 |
| H-CONC-2 | 갈래 탓 b23 | 머리 33a72a906 정적 재현(루프 = in plan) | 0017bbc91 — plan 출처 BOOT_PLAN 확인 · 음성 대조 FAIL |
| H-SEAT-4AXIS | 갈래 탓 skt1 | 머리 b03d1cd70 정적 재현(session_lease 갈래 close 오독) | 0017bbc91 — 보류 갈래 끝 = 다음 match 갈래 · 음성 대조 FAIL |
| e2e-chat resize_surface 2 | 병합 탓 s2 × s79 | s79 머리·0e2aabefa PASS · e246dde26·HEAD FAIL(가짜 시계 재현) · 원인 = onWorkShown→render() 가 복귀 순간 좌석 한 바퀴 맞춤(크기 그대로) → 30초 창에 한 바퀴 더 | 0017bbc91 — 허용 폭 = 전환 순간 한 바퀴(그려진 좌석 수)까지 · ★지시 없이 내린 판단(제품 코드 무변경) |
| (g2a 에서 드러남) test_dept_tick_stdin 14 | 갈래 탓 asset-skills | 머리 1ff82d08a·f9ed0fcac FAILED · 기준선 OK · g1 은 L999 루프가 nowin 에서 멈춰 못 감 | 932188962 |
기준선 탓 0 · 부하·환경 0.

### 0-2. seatkeep 덧붙임(master#4f490f50) — 글자 충돌 1 = src/lib.rs 동결표 cys.rs 칸 주석(값 양쪽 16) → 갈래 주석 + 통합 사실 1줄. 의미 충돌 0(lib spawn_policy_tests·update::prime·update::realops 64 ok). census raw_command_new_census_is_frozen = g1 붉음 목록에 없었음(bfb52cbd2 가 이미 16) · 병합 뒤 초록.

### 0-3. 게이트 g2(머리 932188962 · 19:33~21:39 · 결과 = gate/g2/summary.txt · GATE_ONLY = 붉던 단계 + bin-cys·bin-seatkeep·it-*) — 30단계 중 29 초록
초록: secret-scan · lib 1324/0/5 · bin-cys 843/0/2 · bin-seatkeep 52/0 · it 6종 · health 170/0/1 · L2108 · cys-app 375/0/2 · e2e 15종 전부(g1 에서 못 돈 stty·nodept·restart·hidden_block 포함).
붉음 1: ci-macos-rust-pack-L999 = javis_cycle_autopilot self-test PASS 342 / FAIL 1 「javis_cycle_verifier.py 와 바이트 동일」(계약 블록 두 파일 동일성). ★원인 미확정 — 범위(dea2e1853..HEAD) 안에서 javis_cycle_autopilot.py 를 바꾼 커밋 = debt-d e132ea232(형제 정지 표지 판독 3곳 U08 꼴) 하나 · verifier 는 무변경 → 후보 = debt-d 갈래 탓(머리 e5c0d229f 단독 self-test 미실행). L2108 은 같은 시험이 초록이라 우분투 쪽 다른 경로인지도 미확인.
g2a-premerge = 병합 전 머리 부분 판(19:31 멈춤 · 보존).

### 0-4. 다음 첫 행동
1. L999 붉음: `cd cysjavis-pack/bin && python3 javis_cycle_autopilot.py` self-test 진입 방법 확인(--self-test 로는 출력 0) → e5c0d229f·dea2e1853 에서 같은 self-test 대조 → 계약 블록 diff(autopilot ↔ verifier) → 갈래 탓이면 verifier 쪽 동기화 1커밋 → L999 단독 재실행.
2. 부하성 단독 3회(§8 · load<15) = **안 함**(상한) — test_resource_gate_product_cpu test_9b · test_dept_name_guard · test_phoenix_c6_reap · cysd seatkeep_input_ack_stall · k17. 단 g2 의 L999·L2108·bin 묶음 안에서는 이번에 초록이었다.
3. 【확인요청】 뒤 master 독립 검증.

## 1. 병합 커밋 13(브리프 표 순서 그대로 · --no-ff · 스쿼시 0 · 모든 머리 = 브리프 커밋과 일치 확인)

| # | 갈래 | 수용 머리 | 병합 커밋 | 글자 충돌 |
|---|---|---|---|---|
| 1 | debt-u | e0953c7e0 | fdd071f57 | 0(트리 = 갈래 머리와 동일 확인) |
| 2 | flaky | 7dd80224e | b5a7563e6 | 0(test_dept_name_guard 자동 병합 · 75/75) |
| 3 | ccopen | 88def9658 | 9011a2521 | 0 |
| 4 | asset-skills | 1ff82d08a | c7599bf32 | 0 |
| 5 | skill-revisions | f9ed0fcac | f49f7b84f | 0(1ff82d08a ⊂ f9ed0fcac · 새로 든 커밋 4) |
| 6 | b23 | 33a72a906 | 8ab9abe27 | 0 |
| 7 | debt-d | e5c0d229f | 8c1c9397a | cys.rs 4 |
| 8 | skt1 | b03d1cd70 | ae4420458 | cys.rs 1 |
| 9 | s79 | f51261ee0 | 0e2aabefa | 0 |
| 10 | s2 | 06711fbc9 | e246dde26 | 5파일 |
| 11 | s5 | 305f08930 | 4ee8d2044 | 7파일 |
| 12 | s6 | 94ddcd1cf | 331ffce0a | 4파일 |
| 13 | seatkeep | 9b591371b | b7aeedf37 | 2파일 |

순서 변경 0. seatkeep 의 16:37 codex 마지막 1회 처분 커밋은 아직 없음(master 지시 때 덧붙임).

## 2. 글자 충돌 표(해결 = 양쪽 뜻 모두 살림 · 한쪽 버림 0 — 예외 = s5 의 defaultSlug 1줄, master 판정 ④)

| 병합 | 파일 | 충돌 | 해결 |
|---|---|---|---|
| 7 debt-d | src/bin/cys.rs ×4 | DaemonAction 갈래 목록(command_never_autostarts · run_daemon_cmd 머리 · launchd/schtasks 도달 불가 갈래 2) | b23 ExplainState·BootFleet + debt-d Prime 전부 · 머리 처리 블록 둘 차례로 |
| 8 skt1 | src/bin/cys.rs ×1 | 파일 끝 추가끼리 | b23 explain_state_tests·boot_fleet_tests 뒤에 skt1 session_lease_cli 모듈 |
| 10 s2 | views/work/adapter.ts ×3 | workView 3번째 인자: s79 WorkExtra{mount} vs s2 WorkHooks{shown,hidden} | 한 객체 `WorkHooks & Partial<WorkExtra>` · 순서 = 보이게 → shown → mount / 떼기 → 숨김 → hidden |
| 10 s2 | views/index.ts ×3 | BootDeps · workExtra/workShown · views 표 | 합집합 · `workView(…, { ...workExtra, shown, hidden })` |
| 10 s2 | main.ts ×1 | bootViews 인자 | focusSeat + onWorkShown |
| 10 s2 | views/core.ts ×1 | applyEarlyRefusal(HEAD) vs ingest(s2) | 둘 다 + 의미 충돌 ② 배선 |
| 10 s2 | roleactivity.test.ts ×1 | 파일 끝 describe | 둘 다 |
| 11 s5 | src/bin/cys.rs ×2 | EXIT 표 주석 · run_launch_agent_opts 결과 갈래 | skt1 임대 갈래 2 + s5 초안 보류 갈래 · 의미 충돌 ① |
| 11 s5 | src-tauri/src/viewcore.rs ×1 | 시험 모듈 끝 | s79 결과 열기 시험 + s5 if_quiet 닫기 시험 |
| 11 s5 | main.ts ×1 | bootViews 인자 | focusSeat · onWorkShown · openHelp · restoring |
| 11 s5 | views/index.ts ×2 | BootDeps · ChatCore deps | 합집합 · s5 listenApp·focusSeat·openHelp·restoring·workHint · ★defaultSlug 제거(판정 ④) |
| 11 s5 | views/core.ts ×3 | import · 필드·생성자 · chat_send 응답 | ResultBook·ReviveBook 둘 다 · request_id + human_input_stamp 둘 다 |
| 11 s5 | views/chat/index.ts ×2 | import · paint | 둘 다 |
| 11 s5 | views/views.css ×1 | 같은 자리 추가 | 둘 다(.cvr- 이름 겹침 0 확인) |
| 12 s6 | views/core.ts ×6 | import · 필드·생성자 · 구독·slug·poll·onTail | Result·Revive·Rail 셋 다 + 의미 충돌 ②③ |
| 12 s6 | views/chat/index.ts ×2 | import · 화면 조립 | revive 띠 + rail 감싸기 + 결과 칸(대화 위 그대로) |
| 12 s6 | views/views.css ×1 | 같은 자리 추가 | 둘 다 + 의미 충돌 ⑤ |
| 12 s6 | test_cso_directive_rev.py ×1 | 바이트 상한 | 합친 실측 MASTER 88,134 · CEO 103,620(주석 ⑧) |
| 13 seatkeep | src/bin/cysd/state.rs ×2 | 맵 넣기 전 · PTY 끝 | s2 mirror_screen_modes → seatkeep apply_record · b23 program_status.wipe → seatkeep forget_surface |
| 13 seatkeep | src/bin/cys.rs ×1 | rotate_rc_table 앞 시험 묶음 | debt-d + seatkeep 시험 둘 다 |

자동 병합된 데몬 원작자 파일(handlers.rs·governance.rs·main.rs·state.rs 나머지)은 글자 충돌 0 — 갈래 보고의 「같은 자리」 목록(lane-facts X1·X4)을 대조해 뜻 충돌만 따로 봤다(§3).

## 3. 의미 충돌(글자 충돌 없이 뜻이 갈린 곳) — 찾은 것 · 고친 것

| # | 어디 | 무엇 | 고침 | 시험·뮤턴트 |
|---|---|---|---|---|
| ① | cys launch-agent 종료 코드 | skt1 92 = EXIT_SESSION_WRITER_LIVE(소비처 javis_boot_node 1763-1768 · phoenix 사유 접두 · 앱 복원 집계) vs s5 92 = EXIT_REUSE_DRAFT_HELD(소비처 = 자기 핀만) | s5 값 → 94(첫 빈 번호) · 핀 = 94 + lease 두 값과 다름 단언 | bin cys reuse_draft 1 · exit 38 초록 |
| ② | 화면 사건 입구 | s2 가 views 의 listenDaemon·defaultSlug 를 걷어 사건이 ingest 로만 → s79 결과 장부·s6 메뉴바가 skill.run_finished·surface.group.changed·본부 slug 를 못 받음 | ingest 에서 results/rail.setHqSlug + (붙어 있을 때만) onEvent | ui/src/views/integ1120.test.ts 2 · 뮤턴트 3/3(onEvent 줄 · setHqSlug · attached 가드) |
| ③ | 작업 화면 살핌 | s6 rail.refresh(list_surfaces·list_depts)가 s79 watchOnly(V4 「조회 3종만」) 중에도 돎 | attached ∧ !watchOnly | (전용 시험 없음 — 📌) |
| ④ | views/index.ts | s5 가 defaultSlug(재조회)·listenApp(__TAURI__ 앱 사건)을 넣음 ↔ s2 시험 ① 금지어 | defaultSlug 제거 · listenApp 유지 · 시험 ① = 그 한 줄 빼고 금지어 0(daemon-event 추가) — master 판정 수용 | 뮤턴트(재조회 되살림) 붉음 |
| ⑤ | views.css | .cvr-card·.cvr-empty 를 s79(결과 카드)·s6(메뉴바)가 다른 모양으로 정의 | s6 규칙 7줄을 `.cv-rail` 안으로(이름·시험 불변) | bun·tsc 초록 · 화면 게이트(e2e) = 게이트 결과 |
| ⑥ | cysd surface.create | s5 재반환 역할 재부착(reattach_role_on_reuse)이 seatkeep 역할 부여 판정(role_grant_blocked)보다 먼저 → 노브 켜면 같은 대화 작성자 둘 | 재부착 앞에 판정 · 막히면 재부착만 안 함 + seat.adopt_reserved_denied(path=reuse_reattach) · 노브 끔 = 변화 0 | integ1120_reuse_reattach_respects_seat_adopt_reserve + 이웃 3 = 4/4 · 뮤턴트 붉음 |

점검했으나 고치지 않은 것(lane-facts X1·X2 · 근거 = 코드 읽기):
- s6 팀 정지 ↔ s5 HumanStampGuard: 팀 거절 조기 반환 때 Drop 이 표지를 되돌림(handlers.rs impl Drop) — 안전.
- s6 팀 정지(메모리) × seatkeep 좌석 생존(데몬 재시작 넘어 입양): 정지된 팀이 입양 뒤 조용히 풀릴 수 있음 [추론] — 노브 끔 기본 · 📌.
- 업데이터: seatkeep S6 adopt-check(새 cysd 첫 실행)가 debt-d prime(첫 실행 지연 흡수)보다 먼저 · seatkeep sibling_daemon_path canonicalize × debt-d 윈 작업 경로 비교 · skt1 거짓 93 × seatkeep rotate — 셋 다 [추론] · 실기(윈·맥 업데이트) 없이는 판정 불가 → 📌(윈 실기 단계).

## 4. 갈래 머리에서 이미 붉던 것(통합 탓 아님 · 통합에서 고침)

| 커밋 | 무엇 | 원인 갈래 |
|---|---|---|
| d9917a8ba | USER-MANUAL 523 `CYS_SESSION_LEASE=off cys restore` → `cysr restore`(publicdocs 「공식 명칭 = cysr」) | skt1 222206218 |
| 34cbf7adb | 원시 스폰 동결표 viewcore.rs 1 · session_lease_cli.rs 1 + s79 result_open_in 체인 spawn_policy(Attached)(consoleless census) | s79 · skt1 |
| bfb52cbd2 | 동결표 cys.rs 15→16 · team6b_codex_tests.rs 2 | seatkeep · s6 |

판정 근거 = 시험 입력 파일이 갈래 머리와 바이트 같음(USER-MANUAL·publicdocs.test.ts) 또는 스캔이 디렉터리 전수 + 그 갈래 머리 표에 칸 없음. ⚠갈래 머리에서 그 시험을 직접 돌리지는 않음(추론 · 확신도 상).

## 5. 전체 게이트 g1(bfb52cbd2 · 14:49~17:09 · load 3~7 · 결과 = ~/axdev/.wt/cys-1116-integ-1120-gate/g1/summary.txt · ★17:09 맥 재부팅 매듭 지시로 e2e 끝 4개 전에 끊음)

초록: gen-ceo · gen-hashes · pack-secrets · build · bin-cys 842/0/2 · bin-cysd 3472/0/17 · bin-seatkeep 52/0 · it 6종(rotate_autorestore_hold 11 · update_drainhold_e2e 4 · hidden_seat_screen 1 · seat_group 1 · win 2종 0) · portable-pty 9 · ci 팩 스텝 13 중 10 · unreg 21/21(+agora 건너뜀) · scripts 26/26 · ui-test 4038(0 fail) · ui-tsc · ui-build · e2e tickrec·confirm·cc_popover_z·restart_confirm·race·focus·seatrows·pillar·seatgroup.

붉음(★원인 미확정 — 판독 안 함 · 「갈래 탓/통합 탓」 미분리):
| 단계 | 실패 | 첫 짐작(검증 안 함) |
|---|---|---|
| secret-scan | 6건: HANDOFF.cysr-1116-borrow23-1119.md:101·138 · HANDOFF.cysr-1116-flaky-1120.md:3 · HANDOFF.cysr-1116-seatkeep-1119.md:3(로컬 경로) · src/bin/cysd/team.rs:810·811(시험 값의 사용자 이름 `a` — 더미 목록 밖) | 갈래 파일 그대로(b23·flaky·seatkeep·s6) — 경로를 `~/…`·`/home/a/site` 꼴로 |
| health(boot-health L1907) | H-SECRET-1 · H-CONC-2 · H-SEAT-4AXIS(pass 167 · fail 3 · skip 1) | H-SECRET-1 = 위 secret-scan 과 같은 뿌리 추정 · 나머지 둘 미판독 |
| lib | update::prime::tests::d3_prime_is_wired_right_after_the_swap_and_as_a_daemon_subverb(1317/1/4) | debt-d 핀 × seatkeep realops rotate 변경(의미 충돌 X2 후보) |
| cys-app | tests::c2_feed_reply_and_list_all_wiring(374/1/2) | debt-d 배선 핀 × 다른 갈래 main.rs 변경 |
| ci L999(맥 팩) · L2108(우분투 팩) | test_*nowin* NowinCapturedSpawns.test_every_captured_spawn_hides_its_window ×6: skills/narrated-motion/tools/s2m_cues.py · s2m_sync_check.py · skills/notebook-source-pack/scripts/pack_sources.py · skills/portrait-cutout/scripts/portrait_cutout.py · skills/ppt-styles/tools/check_pptx.py · skills/video-report-deck/bin/tts.py | asset-skills·skill-revisions 가 올린 스킬 스크립트의 subprocess 창 숨김(갈래 머리에서도 붉을 가능성 큼 · 미확인) |
| e2e-chat | 작업 화면 30초 invoke 허용 3종 밖 `resize_surface` 2 | s2 onWorkShown(retryFailedRuntimes·render) × s79 작업 화면 띠(높이 변경) 추정 — 의미 충돌 후보 |
| 안 돎 | e2e stty·nodept·restart·hidden_block | 매듭으로 끊음 |


## 6. 시험 숫자 전후(기준선 dea2e1853 = 이 좌석 실측 13:35~13:36 · 목록 계수 / 통합 = g1 실행 결과)

| 대상 | 기준선 | 통합 g1 |
|---|---|---|
| cargo lib | 1271 목록 | 1317 통과 · 1 실패 · 4 무시(= 1322) |
| bin cys | 798 목록 | 842/0/2(= 844) |
| bin cysd | 3351 목록 | 3472/0/17(= 3489) |
| bin cys-seatkeep | 49 목록 | 52/0 |
| it(6종) | 17 목록 | 17 통과 |
| cys-app | (정적 #[test] 350) | 374/1/2 |
| bun ui | 3747/88/0(3835 · 123 파일) | 4038 실행 · 0 fail(134 파일) |
| 팩 시험 파일 | 207 | (미계수) |
| scripts 시험 파일 | 23 | 26 실행 초록 |

⚠「새 시험 수 = 갈래 보고 합」 대조는 못 함(매듭) — 다음 세션: scratchpad lane-facts 의 갈래별 증분과 위 표 대조.


## 7. `git grep -c oogisoogi`(bfb52cbd2) = 152줄(s5 머리 144 · 기준선 154) — ★s5 예외 목록만이 아님

s5 목록 밖 새 줄 8: HANDOFF.cysr-1116-borrow23-1119.md:101·138 · HANDOFF.cysr-1116-flaky-1120.md:3 · HANDOFF.cysr-1116-seatkeep-1119.md:3(로컬 경로 = secret-scan 6건 중 4와 같은 줄) · HANDOFF.cysr-1116-debt-u-1119.md:151(금지어 나열 문장) · docs/SKILL-REVISIONS-1120.md:105(금지어 나열 문장) · HANDOFF.cysr-1116-debt-d-1119.md:15(`oogisoogi/cys-ro` 공개 저장소 = 허용 꼴) · WORKER_TODO.cysr-1116-integ-1120.md(이 좌석 메타 줄). 고침 = 다음 세션 첫 커밋.


## 8. 갈래별 남은 것 · 통합 때 볼 시험(고치지 않음 · 표 전문 = docs/integ-1116/remaining-1120.md · 250행 + 127행)

부하성 단독 3회(load<15 · resource_gate_product_cpu test_9b · dept_name_guard 경쟁 · c6_reap · seatkeep_input_ack_stall · s5 k17) = **안 함**(매듭).

## 다음 첫 행동(재부팅 뒤 · 이 worktree 에서)
1. `cd ~/axdev/.wt/cys-1116-integ-1120 && git log -1 --oneline` (이 HANDOFF 커밋 확인) → 위 §5 붉음 판독부터: `less ~/axdev/.wt/cys-1116-integ-1120-gate/g1/{lib,cys-app,e2e-chat,ci-boot-health-full-L1907}.log`
2. secret-scan·oogisoogi 정리 1커밋(§5·§7 줄) → `GATE_ONLY='secret-scan|ci-boot-health|lib|cys-app|ci-macos-rust-pack-L999|ci-ubuntu-pack-suite-L2108|e2e-' bash docs/integ-1116/gate-1116.sh ~/axdev/.wt/cys-1116-integ-1120-gate/g2`
3. 부하성 단독 3회(§8) → 【확인요청】(TICKET=cysr-1116-integ-1120).

크롬 좌석: 이 좌석은 크롬을 쓰지 않음(열린 탭·창 0).


## 다음 판 정리 후보
- (master 판정 ④) main.ts 가 앱 사건(boot-degraded·restore-progress)도 ingest 로 넘기고 views 의 listenApp 을 걷기.
- s79 결과 칸을 s6 rail 의 결과 자리로 옮기기(s79 주석 「통합 때 master 조정」) — 이 판 = 대화 위 그대로.
- ③ rail.refresh 살핌 중 차단의 행동 시험.
- (공개 후보 검증 N1 · master#a95eaa65) 자산 판정표 검사기·뮤턴트·시험(`scripts/asset_ledger_check.py:22-25` · `scripts/asset_ledger_mutants.py:22-23` · `scripts/tests/test_asset_ledger_check.py` 여러 줄)에 남은 두 번째 계정 폴더·「계정2」·본부 폴더 경로를 본부 판정표(.hq.md) 쪽 설정으로 옮기기 — main 에 같은 종류가 있어 1.1.16 차단 아님.
- (공개 후보 검증 N6 · master#a95eaa65) 제외 파일을 파일 이름만으로 가리키는 주석 4곳(`src/agy_door.rs:138` · `src/bin/cys.rs:21402` · `ui/src/views/judge/revive.ts:115` · `src/bin/cysd/send_settle_tests.rs:1895`)을 공개 트리에서 따라갈 수 있는 설명으로 바꾸기 — 주석이라 깨지는 것 0.
