# HANDOFF — TICKET=cysr-1116-integ-1120 (worker-1116integ · surface:2321)

- 브리프 = `~/axdev/master/briefs/1116-full/integ.md`(원장 spawn 13:29:41 · submitted true) + `_common.md`
- 가지 `integ/1116-r1120` ← `integ/1116` dea2e1853 · worktree `~/axdev/.wt/cys-1116-integ-1120` · push·태그·CI·gh 쓰기·서명·발행·앱 교체·실사용 데몬 접촉 = 0
- 통합 머리 = **bfb52cbd2(게이트 대상) + 이 HANDOFF 커밋** · 게이트 결과 폴더 = `~/axdev/.wt/cys-1116-integ-1120-gate/`
- master 판정 받음: 14:5x master#1e80c983 — 의미 충돌 ①~⑥ 처리 수용(④ = listenApp 유지 · defaultSlug 제거 · s2 시험 ① 좁힘)

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
