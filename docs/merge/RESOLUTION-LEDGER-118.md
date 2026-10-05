# RESOLUTION-LEDGER-118 — 1.1.8 병합(원작자 v0.14.43 전체 편입) 해소·수리 원장

> 생성 = docs/merge/work/mkledger.py(서브 원장 합본 · 개인 경로 제거). 판정 열 = ours(우리) / theirs(원작자) / synth(합성). 결정 근거 = DECISIONS-PENDING-118.md · DECISION-TABLE-118.md.

## 0. 부모별 순효과(머리 기준)

- 첫 부모 v1.1.7(75d2407b) → HEAD: `375 files changed, 259799 insertions(+), 47340 deletions(-)`
- 둘째 부모 원작자 v0.14.43(55d3d2d6) → HEAD: `627 files changed, 101929 insertions(+), 6621 deletions(-)`
- 파일별 전체 = 아래 부록 A·B(`git diff --stat`).

## 1. 충돌 파일 전수(76 · conf43.tsv · zdiff3 이전 merge 기본 표기 덩어리 수)

| 덩어리 | 상태 | 파일 | 해소 원장 행 수 |
|---|---|---|---|
| 80 | UU | `ui/src/main.ts` | 93 |
| 46 | UU | `src/bin/cys.rs` | 76 |
| 29 | UU | `cysjavis-pack/bin/cys-dept` | 37 |
| 26 | UU | `src/bin/cysd/handlers.rs` | 105 |
| 21 | UU | `src/bin/cysd/governance.rs` | 49 |
| 19 | UU | `src/bin/cysd/state.rs` | 22 |
| 17 | UU | `src-tauri/src/main.rs` | 23 |
| 15 | UU | `src/bin/cysd/accounts.rs` | 25 |
| 15 | UU | `cysjavis-pack/bin/javis_phoenix.py` | 20 |
| 10 | UU | `src/bin/cysd/schedule.rs` | 18 |
| 7 | UU | `ui/src/style.css` | 9 |
| 7 | AA | `ui/src/wswiring.test.ts` | 7 |
| 6 | UU | `src/bin/cysd/approval.rs` | 12 |
| 6 | UU | `cysjavis-pack/bin/javis_preflight.py` | 7 |
| 6 | UU | `cysjavis-pack/bin/javis_formation.py` | 8 |
| 6 | UU | `.github/workflows/release.yml` | 6 |
| 5 | UU | `src/bin/cysd/usage.rs` | 6 |
| 5 | UU | `cysjavis-pack/bin/javis_bootstrap.py` | 5 |
| 4 | UU | `scripts/secret-scan.sh` | 8 |
| 4 | UU | `.github/workflows/ci-branch.yml` | 4 |
| 4 | AA | `src-tauri/src/feedback.rs` | 2 |
| 3 | UU | `cysjavis-pack/hooks/session-start.sh` | 6 |
| 3 | UU | `cysjavis-pack/bin/tests/test_dept_name_guard.py` | 3 |
| 3 | UU | `.github/workflows/pack-release.yml` | 3 |
| 3 | AA | `ui/src/wsreconcile.ts` | 1 |
| 2 | UU | `USER-MANUAL.md` | 2 |
| 2 | UU | `ui/src/drainverify.test.ts` | 2 |
| 2 | UU | `ui/index.html` | 5 |
| 2 | UU | `src/first_run_gates.rs` | 2 |
| 2 | UU | `src/bin/cysd/main.rs` | 2 |
| 2 | UU | `src/bin/cysd/channels.rs` | 2 |
| 2 | UU | `scripts/verify-release-remote.py` | 2 |
| 2 | UU | `scripts/release-gate-gatekeeper.sh` | 2 |
| 2 | UU | `cysjavis-pack/hooks/_lib.sh` | 3 |
| 2 | UU | `cysjavis-pack/directives/CEO_TEMPLATE.md` | 3 |
| 2 | UU | `cysjavis-pack/bin/tests/run_bootstrap_health.py` | 2 |
| 2 | UU | `cysjavis-pack/bin/javis_cycle_autopilot.py` | 2 |
| 2 | UU | `Cargo.lock` | 1 |
| 2 | AA | `ui/src/wsreconcile.test.ts` | 1 |
| 2 | AA | `ui/src/droppoint.test.ts` | 1 |
| 1 | UU | `ui/src/drainverify.ts` | 1 |
| 1 | UU | `ui/src/deptlabel.ts` | 2 |
| 1 | UU | `ui/package.json` | 1 |
| 1 | UU | `src/lib.rs` | 5 |
| 1 | UU | `src/factory_reset.rs` | 3 |
| 1 | UU | `src/bin/cysd/boot_supervisor.rs` | 1 |
| 1 | UU | `src-tauri/tauri.conf.json` | 1 |
| 1 | UU | `src-tauri/Cargo.toml` | 1 |
| 1 | UU | `scripts/tests/test_version_sot_mutation.py` | 1 |
| 1 | UU | `scripts/tests/test_release_postprocess_gate.py` | 1 |
| 1 | UU | `scripts/ceo_template_header.md` | 1 |
| 1 | UU | `docs/RELEASE.md` | 1 |
| 1 | UU | `dist-win/cys.wxs` | 1 |
| 1 | UU | `dist-win/cys-x64.wxs` | 1 |
| 1 | UU | `cysjavis-pack/memory/feedback_autonomous-pilot-mandate.md` | 2 |
| 1 | UU | `cysjavis-pack/hooks/save-state.sh` | 1 |
| 1 | UU | `cysjavis-pack/hooks/reflect-scan.sh` | 1 |
| 1 | UU | `cysjavis-pack/hooks/guard.sh` | 1 |
| 1 | UU | `cysjavis-pack/hooks/grill-stop.sh` | 1 |
| 1 | UU | `cysjavis-pack/hooks/actprobe-kill-gate.sh` | 1 |
| 1 | UU | `cysjavis-pack/directives/MASTER_DIRECTIVE.md` | 8 |
| 1 | UU | `cysjavis-pack/directives/CSO_DIRECTIVE.md` | 13 |
| 1 | UU | `cysjavis-pack/bin/tests/test_pyseal_census.py` | 3 |
| 1 | UU | `cysjavis-pack/bin/javis_state_snapshot.py` | 1 |
| 1 | UU | `cysjavis-pack/bin/javis_org.py` | 1 |
| 1 | UU | `cysjavis-pack/bin/javis_event.py` | 1 |
| 1 | UU | `cysjavis-pack/bin/javis_cycle_verifier.py` | 1 |
| 1 | UU | `cysjavis-pack/bin/javis_checklist.py` | 1 |
| 1 | UU | `Cargo.toml` | 1 |
| 1 | UU | `.gitignore` | 1 |
| 1 | AA | `ui/src/restartplan.ts` | 1 |
| 1 | AA | `ui/src/restartplan.test.ts` | 1 |
| 1 | AA | `ui/src/feedback.ts` | 1 |
| 1 | AA | `ui/src/feedback.test.ts` | 1 |
| 1 | AA | `ui/src/droppoint.ts` | 1 |
| 1 | AA | `cysjavis-pack/bin/tests/test_phoenix_g2_ack_only.py` | 1 |

## ① 병합 해소(c08489e7 · 76파일)

### ledger-main-ts (90행)

| 파일 | 원 덩어리 | 원 줄 범위 | 판정 | 근거 | 관련 | 잠정 |
|---|---|---|---|---|---|---|
| ui/src/main.ts | 1 | L10-50 | synth | import: 우리 formation·updateplan·restartpending 유지 + 원작자 ftdrop 경로판정·droppoint·transfer(WP-4)·restartplan 신 API · updatestate(U9) 미수용 | C-01 C-06 · X2 | P |
| ui/src/main.ts | 2 | L56-91 | synth | import: 우리 drainverify 4종+헤더라벨 등 유지 + DrainUnreachable 타입 + feedCreatedToastTitle(U10) · teamproposal(U16) 미수용 | §2-B 팀승인 | P |
| ui/src/main.ts | 3 | L98-108 | union | deptlabel: 우리 deptNameFromSocket + 원작자 K2-05·F3·G1 이름해소·종료판정 함수 | §2-B ①(원작자 추가분 수용) |  |
| ui/src/main.ts | 4 | L119-153 | ours | wsreconcile 우리 newlyRegisteredDepts 유지 · seatlayout(U2·U3) import 미수용 | X1 · §2-C B-10 | P |
| ui/src/main.ts | 5 | L169-276 | synth | 우리 wsbar·appearance·wsusage·feedback import 유지 + ctxpick·seatsig·probefail·starvednotice·updatenotice·deptprogress 수용 · usagebar 는 CC 계정 표용만 · deptcreate(U17) 미수용 | X3 X6 X7 · 사용량 패널 절대 | P |
| ui/src/main.ts | 6 | L329-351 | synth | 우리 panetitle·alertcopy·restorebrief·scrollfollow·placeholderclose 유지 + folderaccess(U14/U18)·modalguard 수용 · feedbackmodal 미수용 · droppoint import 는 #1 로 이동 | X4 X8 · D-19 | P |
| ui/src/main.ts | 7 | L398-427 | synth | 우리 foldHint + 원작자 T_STOP(F3) · ROLE_SLOT_GRACE(U2) 제외 | 1b40379c(F3) · X1 | P |
| ui/src/main.ts | 8 | L445-458 | ours | Node 타입 = 우리(leftAuto) · LNode(seatlayout) 미수용 | X1 | P |
| ui/src/main.ts | 9 | L476-506 | synth | Workspace 필드: 원작자 deleting/stopFailed(G4·G5)·GU 표시필드 수용 · layoutManual/daemonEpoch(U2·U3) 제외 | X1 · GU(8820fc74) | P |
| ui/src/main.ts | 10 | L1055-1082 | theirs | ccAggRate = 원작자 aggSeatRates(UI2) — 우리 D4#18 미관측 거름을 포함하는 상위 판(리셋 지남·경보 부적격도 제외) | 8bdb1cf3 · 우리 38e276ce |  |
| ui/src/main.ts | 11 | L1147-1196 | ours | CC 계정 게이지 = 우리 판(5h·7d + 모델 스코프 7d·모델 + stale 사유) — 원작자 windowView 게이지 미수용 | §2-B 사용량 패널 절대 |  |
| ui/src/main.ts | 12 | L1209-1220 | synth | CC 계정 행: 우리 allDead 흐림 + 원작자 old/숨김 흐림·숨기기 단추(R1F-UB) 합성 | c36a28e7 · 정책 CC 행 합성 |  |
| ui/src/main.ts | 13 | L1458-1505 | synth | renderAlerts: 원작자 probefail 추적기(unknown '조회 불가' 행) 수용 · 헤더 개수 배지는 계속 미표시(박사님 09-15 ⓔ) | X7 · 94dd866b | P |
| ui/src/main.ts | 14 | L1794-1806 | ours | CC 작업 탭 부서 머리 '작업중' 계수 = 우리 nodeWorking(원작자 taskSeatView 판정과 의미 중복) | X6 · 62cb7a8b | P |
| ui/src/main.ts | 15 | L2731-2738 | synth | NodeSig = SeatSig(원작자 U12) & { working }(우리 역할점 깜빡임) | X6 |  |
| ui/src/main.ts | 16 | L3050-3131 | union | 우리 자리표 장부·스윕 무장·deptSeen + 공통 in-flight 가드 + 원작자 cwdBlockedSeen(U18) | v111-restore · U18 |  |
| ui/src/main.ts | 17 | L3138-3148 | synth | refreshPaneTitles 지역변수: 우리 layoutChanged 이름 유지 + 원작자 blockedTick(U18)·seatRolesTick(GU) · roleMemoChanged(U2) 제외 | X1 · f117aebb |  |
| ui/src/main.ts | 18 | L3158-3169 | ours | 빈 탭 복구 뒤 우리 openNewlyRegisteredDepts(A1-3 M7①) 유지 | 2309a692 |  |
| ui/src/main.ts | 19 | L3179-3399 | synth | 소켓 루프 본문 = 우리(유령 수렴·B17 스윕·표시번호·제목) + 원작자 cwd_blocked 수집·seatRolesTick 기록 이식 · 구멍 보류·annotateRoles·adoptSeat·tidyHoles 미수용 | X1 · U18 · GU | P |
| ui/src/main.ts | 20 | L3401-3444 | synth | 자동 입양 = 우리 arrangeWs(autoArrange) + 원작자 G4 `!w.deleting` 입양 금지 가드 | X1 · G4 |  |
| ui/src/main.ts | 21 | L3512-3522 | ours | render 조건 = 우리 layoutChanged · 구멍 만료 재정렬(U2) 미수용 | X1 | P |
| ui/src/main.ts | 22 | L3846-3862 | theirs | send_input 사유 표기 주석 — 원작자 정정판(rpc_full · restartInvokeFailureReason) | 51654319 |  |
| ui/src/main.ts | 23 | L4702-4719 | synth | 전출 보상 롤백 catch = 원작자 WP-4·J2 문구 + 우리 D4#14 원문 「자세히」 칸(5번째 인자) | 3f8654dc · 9f1584f3 |  |
| ui/src/main.ts | 24 | L4728-4822 | synth | 전출 바깥 catch·awaitHandoffAck(WP-4) 수용 + D4#14 원문 칸 | 02264d4c · 085041a9 |  |
| ui/src/main.ts | 25 | L4906-4946 | theirs | deferPaneFocusUntilModalsClose(modalguard) 수용 · 드롭 환산 주석 원작자판 | X4 · 정책 C-01 | P |
| ui/src/main.ts | 26 | L4948-4958 | theirs | paneAtPointStrict = 원작자 dropPointToCss(pos,dpr,DROP_PLATFORM) | 정책 2-A C-01 |  |
| ui/src/main.ts | 27 | L4984-5003 | synth | render: 우리 X-1 flex 리셋 유지 + renderDeptPending(ws)(GU) · nodeShown(U2) 미수용 | X1 · GU |  |
| ui/src/main.ts | 28 | L5488-5516 | ours | 정렬 머리말 = 우리 가로 균등(formation) | X1 · D-07 | P |
| ui/src/main.ts | 29 | L5518-5561 | ours | evenComb/roleLayout 삭제 상태 유지(우리 formation 으로 이관) | X1 | P |
| ui/src/main.ts | 30 | L5578-5586 | ours | actionEqualize = 우리 arrangeWs standard · roleLayout+layoutManual(U3) 미수용 | X1 | P |
| ui/src/main.ts | 31 | L5627-5635 | union | nodeSig 갱신: 우리 working + 원작자 hollow·unregistered·at(U12) | X6 |  |
| ui/src/main.ts | 32 | L6041-6090 | synth | 탭 삭제: 원작자 G4·I2 deleting 선세움·G3-b 해소이름 묘비 수용 + 우리 D4#14 사람말 묘비 실패 토스트 | 1b40379c 계열 · §2-B ① |  |
| ui/src/main.ts | 33 | L6154-6205 | theirs | 탭 삭제 본체는 원작자 F3(종료 확인 뒤 splice·deptCloseAfterStop)로 대체 — 우리 쪽 블록 제거 | F3 · §2-B ① stop 결과 처리 |  |
| ui/src/main.ts | 34 | L6393-6445 | theirs | 그룹 삭제 = 원작자 I2·G3-b·F3(그룹당 1회 레지스트리 조회) | F3 |  |
| ui/src/main.ts | 35 | L7051-7061 | ours | 새 창 = 우리 arrangeWs · placeSeatSafe(U3) 미수용 | X1 | P |
| ui/src/main.ts | 36 | L7096-7133 | ours | actionClose = 우리 닫기 확인(closeguard) · markClosing(U2 F3 보조) 미수용 | X1 · c926328f | P |
| ui/src/main.ts | 37 | L7170-7190 | ours | removeDeadPane = 우리(구멍 보류 hold 인자 미수용) | X1 | P |
| ui/src/main.ts | 38 | L8094-8249 | ours | 업데이트 상태 = 우리 updateAvailable·packUpdateAvailable·restartpending · 원작자 updState(U9) 미수용 | X2 | P |
| ui/src/main.ts | 39 | L8251-8267 | ours | checkForUpdate 본체 = 우리(D4#14 원문 칸) | X2 | P |
| ui/src/main.ts | 40 | L8276-8436 | ours | checkForUpdate 판정 = 우리 updatePlan | X2 | P |
| ui/src/main.ts | 41 | L8438-8581 | ours | 배지·분기 = 우리 updatePlan 4분기 | X2 | P |
| ui/src/main.ts | 42 | L8604-8623 | ours | promptBinaryPatch 가드 = 우리 installingUpdate | X2 | P |
| ui/src/main.ts | 43 | L8626-8662 | ours | 설치 확인 창 = 우리 문안 + (nc 이식) J2 스마트 앱 컨트롤 고지 문단 | X2 · f7f3dbf7 | P |
| ui/src/main.ts | 44 | L8664-8772 | ours | 설치·재시작 = 우리 restartAfterUpdate + (nc 이식) WU installerLaunchFailure 지속 알림 | X2 · aa0b1adb | P |
| ui/src/main.ts | 45 | L8882-8900 | ours | detectSkew 부서 열거 = 우리 readDeptRegistry(① 못 읽음 = 무변경) · 원작자 D5-c 미수용 | §2-B ① |  |
| ui/src/main.ts | 46 | L9008-9061 | ours | drainVerifyReportText 삭제 상태 유지(우리 drainVerifyNotice 경로) — 원작자 U4-B2② 미응답 줄은 drainverify.ts 쪽 합성 대상 | f5614919 · 9e04b85c | P |
| ui/src/main.ts | 47 | L9071-9089 | ours | restartAllDaemons 부서 열거 = 우리 readDeptRegistry | §2-B ① |  |
| ui/src/main.ts | 48 | L9312-9329 | ours | Update 버튼 머리말 = 우리 f19dbadd | X2 · D-08 | P |
| ui/src/main.ts | 49 | L9331-9344 | ours | onUpdateButton = 우리(restartpending → checkForUpdate) | X2 | P |
| ui/src/main.ts | 50 | L9465-9514 | synth | restartNode = 원작자 planRestartInject·restartInvokeFailureReason + D4#14 원문 칸 · 우리 restartRetryPlan 폐기 | 정책 2-A C-06 · 3426508d |  |
| ui/src/main.ts | 51 | L9721-9732 | ours | 팔레트 act:dept = 우리 launchDept(확인 창 단일 문) · 원작자 openTeamCreateFlow(U17) 미수용 | X3 | P |
| ui/src/main.ts | 52 | L10315-10327 | synth | 완전 초기화 실패: 우리 D4#14 문구 + 원작자 isBootGateRefusal 분기(W-2 · D4#14 형) | accf0bcd 계열 |  |
| ui/src/main.ts | 53 | L10631-10646 | ours | stickyToast 서명 = 우리(raw 칸) — 원작자 onClick 은 이미 포함 | 9f1584f3 |  |
| ui/src/main.ts | 54 | L10664-10676 | ours | stickyToast onclick = 우리(setToastRaw + 대입식 onclick) | 9f1584f3 |  |
| ui/src/main.ts | 55 | L10814-10830 | synth | context.threshold = 우리 alertcopy 문구 + 원작자 WP6-2 숫자 아닐 때 배너 없음 | 3914eaa6 · f48d6053 |  |
| ui/src/main.ts | 56 | L10981-10999 | ours | 종료 이벤트 = 우리 eventSock(본부 slug 해석·출처 소켓) · 원작자 hold/isClosingSid(U2) 미수용 | 8700c36c · X1 | P |
| ui/src/main.ts | 57 | L11316-11370 | synth | start 데몬 상태 = 우리 rpcT·daemonInfoLabel + 원작자 W-2 재설치 심문·startRestoringSince·startHaltedByReset · identBySock(U2) 제외 | accf0bcd·5abc93b0·22b59fff · X1 |  |
| ui/src/main.ts | 58 | L11381-11393 | union | 우리 daemon-reconnected 리스너 + 원작자 dept-create-progress(GU) | d2829108 · 8820fc74 |  |
| ui/src/main.ts | 59 | L11503-11514 | ours | pack-updated 배지 = 우리 전역 · updState(U9) 미수용 (nc 의 reinject_skipped 갈래는 수용·문구 우리 말투) | X2 · 9e04b85c | P |
| ui/src/main.ts | 60 | L11566-11642 | synth | perm-warning = 원작자 folderaccess SOT·당김·설정 열기 + 우리 v116 첫 실행 폴더 권한 안내 블록 | X8 · b5dd7100 | P |
| ui/src/main.ts | 61 | L11652-11666 | union | restore-progress payload 타입: 우리 hq_note·depts_unreadable + 원작자 dept | §2-B ① · D5-b |  |
| ui/src/main.ts | 62 | L11718-11730 | union | 복원 error = 우리(본부 확인 필요·부서 판독 실패 알림) + 원작자 skip 전건 보류 알림(D5-b) | §2-B ① |  |
| ui/src/main.ts | 63 | L11822-11845 | ours | 업데이트 확인 주기 = 우리 벽시계 6h + 포커스 확인(v112-wake ④) | X2 · 9937b657 | P |
| ui/src/main.ts | 64 | L11955-12008 | synth | missingKnownWorkspaces 이름 해소 = 원작자 deptLaunchName(C1·K2-05) + 우리 deptSeen 시드 | 1b40379c · 2309a692 |  |
| ui/src/main.ts | 65 | L12035-12045 | theirs | 복원 계수기 = 원작자 unnamed·tombUnknown·tombReapErr·failedLaunch(우리 tombUnknownLaunch 포함) | K2-05 · D2 · G1 · C4-b |  |
| ui/src/main.ts | 66 | L12098-12105 | ours | daemon_status 상한 = 우리 rpcT · identBySock(U2) 미수용 | X1 |  |
| ui/src/main.ts | 67 | L12125-12184 | theirs | 복원 launch 판정 = 원작자 restoreLaunchDecision(우리 묘비 미상 보류와 같은 효과 + K2-05·W-3-b) | ffcb8500 ↔ 1b40379c |  |
| ui/src/main.ts | 68 | L12191-12197 | theirs | launch 이름 = decision.launch(K2-05) | K2-05 |  |
| ui/src/main.ts | 69 | L12229-12268 | synth | 복원 고지: 원작자 unnamed·failedLaunch 토스트(실패 원문은 D4#14 칸) + 묘비 미상은 우리 토스트(우리 tomb-unknown 스티키와 이중 id 방지) | §4 · C4-a/b | P |
| ui/src/main.ts | 70 | L12276-12288 | ours | liveBySock 타입 = 우리(roles 맵은 U2·U3 전용) | X1 |  |
| ui/src/main.ts | 71 | L12294-12299 | ours | liveBySock 시드 = 우리 | X1 |  |
| ui/src/main.ts | 72 | L12303-12314 | ours | 복원 list_surfaces = 우리(rpcT + role 칸) | X1 |  |
| ui/src/main.ts | 73 | L12317-12329 | ours | liveBySock 기록 = 우리 rememberRoles(formation) | X1 |  |
| ui/src/main.ts | 74 | L12370-12390 | ours | 죽은 칸 정리 = 우리 arrangeWs remove | X1 · 2cc1ea36 |  |
| ui/src/main.ts | 75 | L12431-12454 | synth | 복원 병합 = 우리 arrangeWs 입양 + 원작자 W-3-b 매 pane startHaltedByReset | X1 · 22b59fff |  |
| ui/src/main.ts | 76 | L12456-12472 | ours | 병합 붙이기 = 우리 · adoptSeat(U2·U3) 미수용 | X1 | P |
| ui/src/main.ts | 77 | L12514-12537 | synth | 빈 탭 충전 = 우리 자리표 장부 + 원작자 W-3-b 재확인 | v111-restore ③ · W-3-b |  |
| ui/src/main.ts | 78 | L12550-12555 | theirs | 활성 탭 충전 전 startHaltedByReset(W-3-b) | W-3-b |  |
| ui/src/main.ts | 79 | L12557-12564 | ours | 활성 탭 셸 = 우리 pane 직접 · placeSeatSafe 미수용 | X1 |  |
| ui/src/main.ts | 80 | L12566-12586 | synth | 폴백 = 원작자 F2(본부 탭에만 기본 데몬 폴백)·W-3-b + 우리 pane 직접 | F2(8라운드) |  |
| ui/src/main.ts | 81 | L12595-12603 | ours | 복원 브리핑 카드 타이머(우리 v115 B5) 유지 | 76d33b4d |  |
| ui/src/main.ts | 82 | L12985-13289 | ours | 우리 전문가 모드·피드백 창(2단계 업로드)·＋부서 단추 유지 · 원작자 U17 전문가 칸·renderUsageBar 초기 렌더 미수용 | X3 · D-19 · 사용량 패널 절대 | P |
| ui/src/main.ts | 83 | L13291-13351 | ours | launchDept = 우리(deptLaunching 락·확인 창 단일 문·DEPT_LEGACY_RETRY) | X3 · aaf5ba7b | P |
| ui/src/main.ts | 84 | L13379-13428 | ours | launchDept finally·카탈로그 메뉴 = 우리 | X3 | P |
| ui/src/main.ts | 85 | L13630-13639 | theirs | start().finally → startRestoringSince = null (W-2) | accf0bcd 계열 |  |
| ui/src/main.ts | 결정① | nc(addDeptWorkspace 앞·actions 앞) | synth | D-TEAM 휴면: runTeamProposalFlow 함수 복원(export · 배선 0 · 공유 가드 teamFlowBusy/deptBtnEl/deptLaunchInFlight → 우리 deptLaunching/deptBtn 로 적응) + addDeptWorkspace teamSpec 인자·invoke 인자 복원 + teamproposal import · team-create 카드 분기/[확인 창 열기]·feed.item.created TEAM_CREATE_KIND 분기는 끊은 채 | master#36f48cf7 · 6cca7420 |  |
| ui/src/main.ts | 결정①-시험 | — | (기록) | 휴면 연동 적색 후보: teamproposal.test.ts(카드 안내문 R10·무음 0 §5-4·카드 버튼 예외 4건) · deptprogresswiring.test 「main.ts 배선 핀」 중 카드/teamFlowBusy/openTeamCreateFlow 공유 가드·allow 순서 단언 · onDaemonEvent team-create 안내 분기 — 지우지 않음 | master#36f48cf7 |  |
| ui/src/main.ts | 결정② | renderSidebarUsage · CC 계정 행 · 숨기기 클릭 | synth | X9 되돌림: 사이드바 입력 = accountsCache 종전 그대로 · CC 숨기기 단추·KPI 후보 제외 유지 · 툴팁에서 「사이드바 사용량 패널과」 삭제 · 클릭 시 사이드바 재그리기 삭제 · usageHidden 머리 주석 정정 | master#36f48cf7 X9 |  |
| ui/src/main.ts | 결정③ | — | (기록) | X1 우리 균등 배치 확정 — wswiring 의 .skip(X1 U2+U3 · X16 tomb-unknown)은 「수리 단계에서 우리 동작 기준으로 고침」 대상(지금은 .skip 유지) | master#36f48cf7 X1 |  |
| ui/src/main.ts | 결정④ | 주석 3곳(+deptlabel.ts 1곳) | ours | 판독 실패 종료코드 = 우리 12 — ui 에 10 을 판독 실패로 **해석하는 코드는 없음**(전부 비0=Err 로 받음) · 원작자 주석의 「rc 10」만 「우리 판 rc 12」로 정정 | §2-B ① · master#36f48cf7 |  |

### ledger-cys-rs (62행)

| src/bin/cys.rs | 1 | L310-317 | synth | reinject --ack-only doc: 원작자 문면 + 우리 「옛 바이너리 clap rc2 → 주입 0」 한 줄 | 정책 §2-A ③ · U8 P0-M2 · 우리 f7ab5a1f |  |
|---|---|---|---|---|---|---|
| src/bin/cys.rs | 2 | L1774-1782 | union | GATE_CODES 6→9: 원작자 prompt_gate·delivery_interval + 우리 approval_pending | WP-5 · 우리 4c86a5d0(dbg-queue-approval) |  |
| src/bin/cys.rs | 3 | L1789-1796 | union | 게이트 코드 목록 항목(위와 한 쌍) | 동상 |  |
| src/bin/cys.rs | 4 | L2937-2961 | theirs | 우리 is_input_guard_refusal(④ rc79) 버림 — 원작자 C-05(recover_refusal_from_input_guard·로컬 EXIT_RECOVER_REFUSED) 채택 · 원작자 is_modal_draft_gate_err·is_clear_first_unsupported_err | 정책 §2-A ④·C-05 · 우리 3426508d |  |
| src/bin/cys.rs | 5 | L3964-3985 | synth | inject_text_opts: 원작자 authoritative_paste_settled+inject_params_with_sender(J3) 위에 우리 with_owner_token(D10)·refusing_on_approval(⑯) 감쌈 | 정책 §2-B ⑯ · §3-1 · 우리 c5888582·4da83236 |  |
| src/bin/cys.rs | 6 | L4191-4241 | synth | 원작자 task_user_id(한글 whoami cp949) 채택 + whoami 스폰은 우리 cys::hidden_command(콘솔 깜빡임) 유지 | 정책 §2-B 부서(한글 whoami 받음) · 우리 a587c7eb |  |
| src/bin/cys.rs | 7 | L4520-4558 | synth | spawn 문서: 우리 breakaway(2R codex #8) 문단 + 원작자 SEAT_IDENTITY_ENV_KEYS const | 원작자 성찰 P8 · 우리 4c4f09e4 |  |
| src/bin/cys.rs | 8 | L4561-4608 | synth | 우리 breakaway 재시도 build 클로저 안에 원작자 좌석 신원 env 5종 제거 루프 | 동상 |  |
| src/bin/cys.rs | 9 | L5407-5464 | theirs | cys send: 원작자 S21 정착 재시도 채택 · 우리 ⑵ 타이핑가드 6초 대기 루프 버림(send_guard_wait_secs 함께 삭제) | 정책 §2-A 입력 계층(⑮ 자동응답 면제 대체) · 결정대기 C2 | P |
| src/bin/cys.rs | 10 | L6636-6692 | ours | 원작자 team-token CLI(run_team_token·team_token_outcome) 받지 않음 · 우리 ⑲ 재작성 doc 유지 | 정책 §2-B 팀 승인(T2 토큰 제외) |  |
| src/bin/cys.rs | 11 | L7618-7642 | synth | ⑰ read_schedule_for_update 유지(문면에 원작자 「덮어쓰지 않는다」 병기) · write_schedule 삭제 · 원작자 schedule_file_transaction doc | 정책 §3-13 · 우리 4fca9226 · 원작자 성찰 C10 · 결정대기 C3 | P |
| src/bin/cys.rs | 12 | L7715-7743 | theirs | schedule add: 우리 락·판독 블록 → 원작자 트랜잭션(트랜잭션 본체에 우리 flock+판독 합성 · 덩어리 밖 편집) | 동상 | P |
| src/bin/cys.rs | 13 | L7781-7807 | theirs | schedule add 저장 = 원작자 트랜잭션(via_queue 정규형 접기) | 동상 | P |
| src/bin/cys.rs | 14 | L7854-7890 | theirs | schedule remove = 원작자 트랜잭션 | 동상 | P |
| src/bin/cys.rs | 15 | L7892-7898 | theirs | 우리 write_schedule 호출 제거(트랜잭션이 저장) | 동상 | P |
| src/bin/cys.rs | 16 | L13634-13663 | theirs | run_boot rc79 분기: 원작자 C-05 판(recover_refused 라벨) 채택 | 정책 §2-A C-05 · 우리 3426508d |  |
| src/bin/cys.rs | 17 | L14056-14179 | union | 우리 폴더신뢰 포커스 확인(trust_focus_confirm)·R16 inherit_claude_gate_envelope + 원작자 load_agent_spec doc(D-04) | 우리 4c86a5d0·f845c2d8 · 원작자 D-04 |  |
| src/bin/cys.rs | 18 | L14202-14211 | union | load_agent_spec(디스크 히트): 우리 inherit_claude_gate_envelope + 원작자 promote_stale_vendor_defaults | 동상 |  |
| src/bin/cys.rs | 19 | L14228-14237 | union | load_agent_spec(임베드 폴백): 위와 같음 | 동상 |  |
| src/bin/cys.rs | 20 | L15513-15525 | synth | 부트 영역 재작성: 우리 compose_full_directive·compose_cycle_directive·RECOVER_NOTE·boot_directive_with_note·compose_boot_directive·compose_agent_cmd 삭제 · set_meta_denied_is_same_meta 유지 · 신설 resume_guard_yields_to_followup · boot_agent_on_surface 서명 = 원작자(followup) | 정책 §2-A ③(U8 P0-M1) · 원작자 F-1 핀 · 결정대기 C1 | P |
| src/bin/cys.rs | 21 | L15548-15589 | synth | boot 본체: 원작자 F-1 requested/effective_resume 인라인 + 우리 N-4 주석 | 원작자 WP-1 F-1 · 우리 4463ad91 |  |
| src/bin/cys.rs | 22 | L15594-15623 | synth | 디렉티브 = 원작자 boot_directive_for + 우리 오버레이(이어받은 좌석에 followup 있으면 [RESUME] 생략) | 결정대기 C1 · 우리 v111-restore ② | P |
| src/bin/cys.rs | 23 | L15673-15692 | synth | 기동 줄 send: 원작자 authoritative_paste_settled + 우리 AGENT_LAUNCH_KEY 표지 | 우리 6206050f(X-4) · 원작자 0.14.42 통합 |  |
| src/bin/cys.rs | 24 | L15712-15734 | synth | 우리 set_meta 같은 메타 무해 판정 + 원작자 max_wait 1지점(C12) | 우리 12157cce · 원작자 성찰 C12 |  |
| src/bin/cys.rs | 25 | L15820-15847 | union | 우리 trust_nav 변수 + 원작자 버전 래치(H2-B) | 우리 dbg-queue-approval · 원작자 H2-B |  |
| src/bin/cys.rs | 26 | L19268-19274 | theirs | launch-agent 부트 호출: restore 면 followup=restore_directive | 원작자 리뷰 R2 · U8 P0-M1 |  |
| src/bin/cys.rs | 27 | L20077-20164 | synth | statusline push: 원작자 총예산 무 autostart 구조(agy 갈래 포함 휴면 유지) · 창 밖 분기 = 우리 usage.report_named(원작자 report_account 제외) | JT-PART-TEAM-USAGE U3(제외)·9c5a1354(정기) · 결정대기 C4 | P |
| src/bin/cys.rs | 28 | L20168-20181 | synth | 사람용 줄: 원작자 writeln!(닫힌 stdout panic 0) + 우리 빈 줄 미출력 | 동상 · 우리 d5a1b235 |  |
| src/bin/cys.rs | 29 | L20603-20638 | synth | inject_text_on: 원작자 paste_fence·정착 재시도·발신 라벨 + 우리 owner_token_on(D10)·refusing_on_approval(⑯) | 정책 §2-B ⑯ · 우리 4da83236·cb4c8cb0 |  |
| src/bin/cys.rs | 30 | L21639-21645 | synth | drain --verify: 원작자 (대상, 도달불가) + 우리 --only/--hq-only 필터를 도달불가 목록에도 같은 범위로 | 우리 5b147597·a5c6c1b6 · 원작자 U4-B2② |  |
| src/bin/cys.rs | 31 | L22797-22813 | theirs | 순환 함수 = 원작자 clear 가드 v3 판 전체 + ⑯ 오버레이(함수 통째 교체 · 아래 32~36 포함) · 우리 ⑤ 사전검사 블록 버림(원작자 결재6ⓑ 82/83 동일) | 정책 §2-A ⑤·clear 가드 v3 · §2-B ⑯ · 우리 4680f0db·c5888582 |  |
| src/bin/cys.rs | 32 | L22869-22888 | synth | 검증자 주입: 원작자 InjectLock + 우리 inject_text_opts(..,true) | 동상 |  |
| src/bin/cys.rs | 33 | L22970-23005 | synth | clear 단계: 원작자 원자 clear_first + refuse_on_approval(원자·3분할 폴백 4입력) | 동상 |  |
| src/bin/cys.rs | 34 | L23007-23075 | synth | 동상(3분할 폴백 갈래) | 동상 |  |
| src/bin/cys.rs | 35 | L23077-23197 | synth | 재주입: 원작자 실효 확인·cycle_reinject_payload 한 제출 + inject_text_opts(..,true) 3갈래 · 승인창 거부(approval_screen)도 not_cleared 로 접기 | 동상 |  |
| src/bin/cys.rs | 36 | L23212-23290 | theirs | 우리 cycle_agent_exit·EXIT_VERIFIER_*·verifier_precheck 사본 삭제(원작자 판이 82/83 포함 상위집합) | 정책 §2-A ⑤ |  |
| src/bin/cys.rs | 37 | L23360-23380 | theirs | node-recover: 원작자 recover_directive followup + recover_refusal_from_input_guard 접기 | 정책 §2-A ③·C-05 |  |
| src/bin/cys.rs | 38 | L23382-23387 | theirs | node-recover Ready 팔 두 번째 제출 0(원작자) | 동상 |  |
| src/bin/cys.rs | 39 | L23416-23429 | theirs | node-recover 안전 거부 = 원작자 is_recover_refusal → 79 | 정책 §2-A C-05 |  |
| src/bin/cys.rs | 40 | L23669-23674 | theirs | restore in-seat: followup=Some(restore_directive) · restore 인자 true(A2-07 C5 원작자 수정 받음) | 원작자 성찰 C5 · 리드 지시 A2-07 |  |
| src/bin/cys.rs | 41 | L23678-23698 | theirs | restore in-seat Ready 주석 = 원작자(한 제출) | 원작자 U8 P0-M1 |  |
| src/bin/cys.rs | 42 | L23747-23765 | synth | restore fresh 주석: 원작자 + 우리 v112 「표식은 기동 전에」 한 줄 (우리 restore_inject_claim·restore_target_cwd·role_held_by_live_seat 는 자동 병합으로 유지 확인) | 우리 ededc48a·50f8d96c |  |
| src/bin/cys.rs | 43 | L23811-24167 | union | 우리 reinject 폭주 가드 헬퍼(epoch_secs_now·reinject_guard_load/save·REINJECT_ACK_LINE) + 원작자 핑 운명 판정 기계(PingFate·reinject_check_*) | 정책 §2-A ③ · 우리 9937b657·8533f71b |  |
| src/bin/cys.rs | 44 | L24174-24178 | theirs | run_reinject = 원작자 P0-M2 판 + 우리 오버레이(함수 통째 교체 · 44~46 포함): v112-wake 가드·awake ACK 줄·record_ack(화면·세션기록 ACK 둘 다)·⑯ inject_text_opts | 정책 §2-A ③(우리 추가분 오버레이) |  |
| src/bin/cys.rs | 45 | L24230-24238 | theirs | 동상 | 동상 |  |
| src/bin/cys.rs | 46 | L24328-24339 | theirs | 동상 | 동상 |  |
| src/bin/cys.rs | 47 | L27625-28416 | synth | tests: 우리 시험 유지·개작 + 원작자 시험 · 버림 = c4(④ 우리 판)·u8_cycle_and_recover(우리 note/compose_cycle)·full_directive_only(compose_full_directive) · 개작 = restore_boot_directive_is_one_message(새 술어)·u8_reinject_ack_only(원작자 팔 앵커)·e5 두 건(원작자 본체 앵커)·u16(원작자 7단계 구조)·schedule 두 건(트랜잭션) | §1-4 · 각 우리 커밋 |  |
| src/bin/cys.rs | 48 | L32753-32983 | union | tests: 우리 제안글 끄기 핀 + 원작자 D-06 핀(사이에 닫는 괄호 보충) | 우리 cafba326 · 원작자 D-06 |  |
| src/bin/cys.rs | 49 | L34117-34135 | synth | injection_hold 핀 = 우리 판(계수 3 = inject_text+inject_text_opts) + 원작자 restore 이사 핀 · 49~53 영역 재구성 | 원작자 U8 P0-M1 · 우리 v111-restore |  |
| src/bin/cys.rs | 50 | L34137-34146 | synth | 동상 | 동상 |  |
| src/bin/cys.rs | 51 | L34150-34158 | synth | 동상 | 동상 |  |
| src/bin/cys.rs | 52 | L34160-34223 | synth | 동상 + 원작자 gate_corpus·unreadable_adapter·action_policy·version_drift 시험 원문 복원 | 원작자 H-2 등 |  |
| src/bin/cys.rs | 53 | L34230-34572 | synth | 동상 | 동상 |  |
| src/bin/cys.rs | 54 | L37151-37164 | union | FakeScenario: 우리 OverwriteNamedFile·LateSaverBusy/Idle + 원작자 DraftRefused | 우리 V111-F2/F3 · 원작자 0.14.42 |  |
| src/bin/cys.rs | 55 | L41215-47124 | synth | 파일 끝 tests: 우리 꼬리(v116_compose_agent_cmd 개작) + 원작자 꼬리 + 우리 mod 3 + 원작자 mod(d06·u10·usage_accounts) · 원작자 team_propose_tests·team_token_cli_tests 버림 | 정책 §2-B 팀 승인 |  |
| src/bin/cys.rs | X1 | (자동병합 영역) | drop | 원작자 team-propose/team-token CLI 제거: Command::TeamPropose·TeamToken · TeamTokenAction enum · 디스패치 2팔 · run_team_propose · feed reply --team-token 인자·파라미터(우리 판 문면으로) · claim-role 안내문(team-propose 언급 → 우리/base 문면) | 정책 §2-B 팀 승인(D-17·T2 받지 않음) |  |
| src/bin/cys.rs | X2 | (자동병합 영역) | synth | schedule_file_transaction 본체: 원작자 디렉터리 잠금 뒤 우리 acquire_settings_lock + read_schedule_for_update 판독 | ⑰ · 결정대기 C3 | P |
| src/bin/cys.rs | X3 | (자동병합 영역) | synth | adoption_payload: 빈 디렉티브면 지시 한 장만 · gate_pending_adopt 도 resume_guard_yields_to_followup 경유(+로그 문구) | 결정대기 C1 | P |
| src/bin/cys.rs | X4 | (자동병합 영역) | drop | send_guard_wait_secs 삭제(유일 사용처 9번 덩어리에서 사라짐) | 결정대기 C2 | P |
| src/bin/cys.rs | X5 | (자동병합 영역 · 원작자 시험) | synth | 원작자 시험 6건 앵커를 우리 ⑯ 형태로 개작: t3_precheck(저장 지시 inject_text_opts) · u10_closer(검증자 inject_text_opts) · u8_m2_wraps_both(재주입 inject_text_opts) · item_body inject_text→inject_text_opts(J3 라벨 핀) · c_inject_text_paths(paste_fence 핀) · cycle hooks 소비처·ok_arm 계수 · usage_report_account 핀(U3 제외 → report_named 단언) / 우리 시험 2건 drain 필터 앵커(targets) | §1-4 원작자 시험 유지(앵커만 개작) |  |
| src/bin/cys.rs | D1 | (X1 되돌림 · 자동병합 영역) | synth | D-TEAM 휴면 통일(master#36f48cf7): run_team_propose·run_team_token·team_token_outcome·TeamTokenAction 원작자 판 복원 + #[allow(dead_code)] + 휴면 주석 · Command::TeamPropose/TeamToken 변형·디스패치 팔·feed reply --team-token 인자는 미등록 유지(노출 0) · claim-role 안내문은 우리 문면 유지 | master#36f48cf7 · 정책 §2-B |  |
| src/bin/cys.rs | D2 | (55번 덩어리 · 시험) | theirs | team_propose_tests·team_token_cli_tests 복원(원작자 판). 휴면 연동 적색 후보: team_propose_subcommand_parses(team-propose 파싱 단언) · team_token_subcommands_parse_and_stay_hidden(team-token 파싱 단언) · feed_reply_carries_optional_team_token(Reply.team_token 필드 부재로 컴파일 불가 → #[cfg(any())] 로 컴파일에서만 제외 · 삭제 아님). 나머지 2건(team_propose_output_points_to_conversation_ask_source_pin·team_token_outcome_keeps_daemon_refusal_code)은 통과 예상 | master#36f48cf7 | 휴면 연동 적색 후보 |
| src/bin/cys.rs | D3 | (27번 덩어리 후속) | synth | C4 agy 갈래 휴면: const AGY_STATUSLINE_BRANCH_ENABLED=false · agy 페이로드(--agy 또는 판별)면 push 0·출력 0(claude 경로 오판 송신도 안 함) · 원작자 agy 갈래 코드는 else-if 로 그대로 남김 | master#36f48cf7 · JT U2 제외 |  |

### ledger-handlers-rs (101행)

| src/bin/cysd/handlers.rs | 1 | 847-898 | synth | 우리 A3 화면 출력(display_notice) 유지 + 원작자 H6 skip_pane 조기 반환 수용(이벤트 pane_notice 값과 동작 일치) · 원작자 주입(guard:None) 경로는 버림 | H2 · 우리 f2fd9782(A3) · 원작자 H6 | P |
|---|---|---|---|---|---|---|
| src/bin/cysd/handlers.rs | 2 | 1739-1767 | ours | npm 고지 = 화면 줄(npm_prefix_pane_notice_line) — 원작자 변경은 삭제된 _req 함수의 guard 필드 추가뿐 | H2 · f2fd9782 | P |
| src/bin/cysd/handlers.rs | 3 | 6293-6372 | synth | 우리 빈 좌석 가드(X-4 agent_launch·hold_for_vacant_seat · 오버레이 5) + ⑯ refuse_on_approval(오버레이 1 · 바이트 0) 앞에 두고 원작자 machine_origin·exempt 정의 뒤따름 | JT-DELIVERY §5-2 오버레이 1·5 · c5888582 · 6206050f |  |
| src/bin/cysd/handlers.rs | 4 | 6400-6498 | synth | 원작자 D-12+S21(paused 재시도·분리 보류) 채택 · 게이트 kind 를 human_trusted(pane 무귀속∨오퍼레이터 토큰)로 + 권위 면제도 사람 초안 축(CancelKey 팔) 거부 오버레이 | H1 · 오버레이 6 · d17dec40(Fable F1·F2) | P |
| src/bin/cysd/handlers.rs | 5 | 6602-6669 | synth | 원작자 게이트 안 재판정(D-12·S21) 채택 + 권위 면제 사람 초안 재판정 오버레이 | H1 · d17dec40 | P |
| src/bin/cysd/handlers.rs | 6 | 6683-6696 | theirs | 계수 = 원작자 상태기계(clear_pending_input/apply_pending_input) · ⑮ 자동응답 제외는 원작자 pending_input_step 이 같은 술어로 수행(우리 ⑮ 대체) | 정책 2-A · 40b7567e→원작자 C-03 |  |
| src/bin/cysd/handlers.rs | 7 | 6698-6753 | theirs | 원작자 InputOrigin(자기신고 human∧¬machine_origin)·A2 소유 각인·R3SH-1 · 우리 human_pending_after·input_gen·F4(GUI 삽입=사람 몫) 버림 | 정책 2-A · H4 · 19928670·3426508d |  |
| src/bin/cysd/handlers.rs | 8 | 7067-7112 | synth | 원작자 send_key D-12(생성 바이트 축·별칭 처방) 채택 + 권위 면제 사람 초안 축 오버레이(F2) · 우리 EditKey 축 버림 | H1·H4 · d17dec40 | P |
| src/bin/cysd/handlers.rs | 9 | 7125-7139 | synth | refuse_on_approval 이면 SubmitGuarded(writer 직전 재판정·계수 복원 · 오버레이 2) 먼저 · 그 밖 SubmitAfterGap{withhold:None}(원작자 F1) | 오버레이 2 · 7b0ab491·9f8709b6·0be2f7f0 |  |
| src/bin/cysd/handlers.rs | 10 | 7142-7306 | synth | 원작자 A2 게이트 루프·F1 탐침·S21 인계 표식 채택 + 루프 안 권위 면제 사람 초안 재판정 오버레이 | H1 · 원작자 A2/F1/S21 | P |
| src/bin/cysd/handlers.rs | 11 | 7308-7379 | theirs | 원작자 쓰기 뒤 짝 Return 표 정산·absorbed 응답 · 우리 원자 계수 갱신(human_pending_after·input_gen) 버림 | 정책 2-A |  |
| src/bin/cysd/handlers.rs | 12 | 7393-7428 | synth | 원작자 g1(output_gen) 관측 + 우리 ⑴ scrollback_stale(판독은 새 헬퍼 scrollback_stale_now 로 — 원작자 핀 「arm 안 .last_output 금지」 준수) | 우리 e6c0d1af · 원작자 WP-1 H-1 |  |
| src/bin/cysd/handlers.rs | 13 | 7435-7470 | theirs | 델타 경로 스냅샷 블록화+quiet(원작자) · 우리 설명 주석 1문단은 반환 앞에 복원 | 원작자 R1 codex BLOCK |  |
| src/bin/cysd/handlers.rs | 14 | 7477-7483 | union | 델타 응답에 source·scrollback_stale(우리)+quiet_secs(원작자) | e6c0d1af |  |
| src/bin/cysd/handlers.rs | 15 | 7535-7541 | union | 전체 응답에 source·scrollback_stale(우리)+quiet_secs(원작자) | e6c0d1af |  |
| src/bin/cysd/handlers.rs | 16 | 8442-8595 | synth | 원작자 finalize_agent_meta_after_role_change(base 메타 로직의 단일 함수화 · 우리 무변경 구간) + 우리 D7⑵ inherit_parked_queue | acf4cdd5(D7⑵) |  |
| src/bin/cysd/handlers.rs | 17 | 10264-10276 | theirs | 원작자 agy 상태줄 귀속 블록 · claude 귀속은 원작자가 앞(B3·fatal-fix 프로필 경계)으로 옮김 — 그 블록 조건을 우리 D6-2 cys::is_claude_agent 로 바꿈(덩어리 밖 1줄) | H5 · 75fdf2e2·f554bf6a(D6-2) · ⓓ | P |
| src/bin/cysd/handlers.rs | 18 | 10286-10301 | union | 우리 제목 모델 조각 추종(retitle_with_model) + 원작자 agy_unchanged 조기 반환(제목 갱신 뒤) | d5a1b235 계열 |  |
| src/bin/cysd/handlers.rs | 19 | 10751-10759 | union | org.status daemon: 우리 auto_restore + 원작자 paused | eb5f9e34 · RQFIX F3 |  |
| src/bin/cysd/handlers.rs | 20 | 11247-11557 | synth | 원작자 cycle_claim·inject_lock·cycle_detach RPC + PauseInfo·set_paused·still_writing 채택 · 우리 ⑩ 저장 실패 = persist_failed 응답 유지(pause·resume) | 791b600c(⑩) · 원작자 clear 가드 v3/--detach ⓓ |  |
| src/bin/cysd/handlers.rs | 21 | 12053-12062 | synth | 원작자 drain_active_except_inflight(인계 중 항목 보존) + 우리 queue_blocked 해제 | 02ffad23(agy 2R #3) |  |
| src/bin/cysd/handlers.rs | 22 | 12293-12386 | synth | 원작자 mutate_records 트랜잭션(TTL·인덱스 재서명·판독 실패=None 거부) 채택 + 우리 ⑨ 프로세스 밖 파일 잠금(lock_records) 오버레이 | H3 · 64519b13·47944bbc(⑨/A1) · 원작자 A1-09/10 | P |
| src/bin/cysd/handlers.rs | 23 | 12545-12580 | synth | approval.sign 도 원작자 mutate_records + 우리 lock_records · 판독 실패 코드 records_unreadable→원작자 persist_failed(무저장 의미 동일) | H3 · 47944bbc | P |
| src/bin/cysd/handlers.rs | 24 | 12611-12827 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[pause_resume_report_persist_failure_instead_of_ok,v115_reject_log_line_carries_caller_lineage,v114_dept_run_args_whitelist,v114_dept_run_denies_pane_callers_and_non_base_daemon,v114_run_dept_tool_capped_runs_child_and_enforces_timeout] · 원작자 유지[live_cwd_goes_through_single_helper,live_cwds_equals_sysinfo_observation] | - |  |
| src/bin/cysd/handlers.rs | 25 | 13556-13568 | synth | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[use crate::governance::PACK_ENV_LOCK as ACL_ENV_LOCK;] · 버림[use crate::governance::PACK_DIR_ENV_LOCK as ACL_ENV_LOCK;=drop(원작자 PACK_ENV_LOCK 단일화)] | - |  |
| src/bin/cysd/handlers.rs | 26 | 16900-17306 | synth | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[terminal_autoreply_does_not_count_as_pending_input,d12_machine_never_appends_submits_or_clears_a_human_draft,d12_screen_occupied_blocks_text_when_counter_is_zero,u16_refuse_on_approval_writes_nothing_on_permission_dialog] · 원작자 유지[v7_send_human,v7_send_key,v7_pane] · 버림[d12_machine_flows_still_reach_the_pane=drop(ours ④ 구현 시험 · F4 소실)] · 적응[d12_machine_never_appends_submits_or_clears_a_human_draft,u16_refuse_on_approval_writes_nothing_on_permission_dialog — 사람 계수를 원작자 pending_input.human 으로 · EditKey 단계 제거] | H1/H4 | P |
| src/bin/cysd/handlers.rs | 27 | 17399-17430 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[v7_split_paste_handler_call_boundary_must_not_change_count] | - |  |
| src/bin/cysd/handlers.rs | 28 | 17478-17590 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[c_clear_first_text_sanitized_before_ledger] | - |  |
| src/bin/cysd/handlers.rs | 29 | 17877-17928 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[d12_direct_send_text_denied_when_human_draft_pending] | - |  |
| src/bin/cysd/handlers.rs | 30 | 18093-18147 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[make_surface] · 원작자 유지[d12_gui_assembled_submit_payload_denied_when_human_draft_pending] | - |  |
| src/bin/cysd/handlers.rs | 31 | 18404-18436 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 32 | 19304-19611 | synth | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[scrollback_text,v115_seat_takeover_notice_is_screen_output_not_shell_input] · 원작자 유지[c5_paint_prompt,c5_agent_seat,c5_last_denied_payload,c5_direct_send_denial_appends_ctrl_u_only_for_ghost_count,c5_ghost_suffix_keeps_cli_fallback_and_settle_parsers_working,c5_queue_list_adds_remedy_and_diag_keys_per_seat] · 버림[npm_prefix_notice_reaches_the_pane_on_windows_shells_too=drop(우리 A3 삭제 · 원작자 기계적 수정만)] | H2 | P |
| src/bin/cysd/handlers.rs | 33 | 19613-19662 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 34 | 19686-19742 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 35 | 19745-19764 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 36 | 19766-19992 | synth | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[v115_npm_prefix_notice_is_screen_output_not_shell_input] · 원작자 유지[rqfix_i6_settle_proof_seen_before_the_pause_filter_blocks_the_ghost_prescription,rqfix_f3_paused_seat_without_recorded_reason_reports_paused_in_queue_list_and_org_status,c5_queue_list_diag_is_once_per_seat_before_the_queue_lock,c5_org_status_adds_queue_blocked_keys_and_pending_input_model] · 버림[seat_takeover_notice_reaches_the_pane_on_windows_shells_too=drop(우리 A3 삭제 · 원작자 기계적 수정만)] | H2 | P |
| src/bin/cysd/handlers.rs | 37 | 20002-20075 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[c5_org_status_remedy_is_computed_after_the_surfaces_guard_is_dropped] | - |  |
| src/bin/cysd/handlers.rs | 38 | 20078-20110 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[write_req_name] · 원작자 유지[d12_clear_first_passes_machine_residue_but_denies_human_draft] | - |  |
| src/bin/cysd/handlers.rs | 39 | 20332-20401 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[make_frozen_scrollback_pane] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 40 | 20403-20412 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[read_text] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 41 | 20414-20423 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 42 | 20425-20431 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 43 | 20434-20448 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 44 | 20450-20499 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[read_text_lines_serves_grid_when_scrollback_frozen] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 45 | 20504-20814 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[read_text_lines_keeps_scrollback_when_fresh,read_text_delta_flags_frozen_scrollback,read_text_matches_approval_detector_source,rejected_send_publishes_reason,v116_send_text_agent_launch_passes_vacant_seat_guard_only_for_seat_bin] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 46 | 21244-21296 | synth | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[create_surface_rpc] · 원작자 유지[-] · 버림[npm_prefix_notice_reaches_the_pane_on_windows_shells_too=drop(우리 A3 삭제 · 원작자 기계적 수정만)] | H2 | P |
| src/bin/cysd/handlers.rs | 47 | 21298-21365 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[create_surface_rpc_idem] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 48 | 22009-22137 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[caller_in_map_still_records_caller_start,legacy_walk_light_refresh_keeps_parent_and_start_time,fast_and_legacy_walks_agree_on_real_tree,resolve_hit_path_releases_cache_lock_before_start_probe] | - |  |
| src/bin/cysd/handlers.rs | 49 | 22152-22162 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 50 | 22166-22211 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 51 | 22213-22293 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 52 | 22326-22336 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 53 | 22385-22437 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 54 | 22457-22467 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 55 | 22497-22507 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 56 | 22531-22547 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 57 | 23223-23264 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 58 | 23266-23281 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 59 | 23550-24171 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[d7_create_arc_primes_seat_cache_before_reply,d7_prime_seat_cache_never_overwrites_a_tick_value,d7_surface_creator_is_observable_for_pane_and_orphan_callers,d7_surface_create_failure_publish_is_wired_and_silent_on_success,d7_claim_denied_labels_why_takeover_did_not_happen,d7_role_seat_queue_is_parked_on_self_exit_and_inherited_by_successor,d7_worker_parked_key_matches_successor_role_via_dead_slot_reuse] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 60 | 24173-24179 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[d7_roleless_seat_queue_still_dropped_on_self_exit] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 61 | 24181-24203 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 62 | 24205-24236 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 63 | 24239-24253 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 64 | 24255-24261 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[d7_other_roles_expired_parking_is_published_when_someone_else_parks] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 65 | 24263-24297 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 66 | 24299-24338 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 67 | 24342-24359 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 68 | 24361-24369 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[d7_parked_expiry_is_per_entry_so_fresh_merges_survive_aging_batches] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 69 | 24371-24407 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 70 | 24409-24500 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[d7_expired_parked_queue_is_dropped_with_reason_not_inherited] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 71 | 24502-24545 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 72 | 24548-24581 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 73 | 24634-24682 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 74 | 24718-24855 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 75 | 25014-25099 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[v116_surface_list_exposes_agent_bin_from_meta] · 원작자 유지[r3_1_pin] | - |  |
| src/bin/cysd/handlers.rs | 76 | 31537-31544 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 77 | 31557-31586 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 78 | 31635-31642 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 79 | 31685-31725 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 80 | 31970-32043 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 81 | 32056-32077 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 82 | 32109-32138 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 83 | 32149-32193 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 84 | 32199-32248 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 85 | 32255-32306 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 86 | 32314-32347 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 87 | 32371-32443 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 88 | 32451-32567 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[wp5_queue_list_hides_expired_unless_requested] | - |  |
| src/bin/cysd/handlers.rs | 89 | 32572-32711 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[wp5_queue_revive_moves_to_tail_and_is_idempotent] | - |  |
| src/bin/cysd/handlers.rs | 90 | 32716-32804 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[wp5_queue_revive_refuses_when_active_queue_full] | - |  |
| src/bin/cysd/handlers.rs | 91 | 32809-32918 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[wp5_queue_drop_writes_tombstone_before_removal] | - |  |
| src/bin/cysd/handlers.rs | 92 | 32929-33034 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 93 | 33074-33185 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[wp5_queue_drop_acl_matches_clear_threat_model] | - |  |
| src/bin/cysd/handlers.rs | 94 | 33775-33842 | ours | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[usage_report_named_persists_across_restart] · 원작자 유지[-] | - |  |
| src/bin/cysd/handlers.rs | 95 | 34205-34245 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[reconcile_reports_a_commit_that_landed_before_the_cancel] | - |  |
| src/bin/cysd/handlers.rs | 96 | 34390-34451 | theirs | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[-] · 원작자 유지[reclaim_binds_across_two_representations_of_one_directory] | - |  |
| src/bin/cysd/handlers.rs | 97 | 34630-34700 | union | 시험 모듈 항목 단위 3자 병합(재구성) — 우리 유지[create_rpc] · 원작자 유지[reclaim_master_rearms_the_sign_cooldown] | - |  |
| src/bin/cysd/handlers.rs | 비덩어리-a | (자동병합 2587-2623) | drop | 자동 병합이 남긴 우리 draft_gate_denied_response(7인자·EditKey·pending_input_human_bytes) 중복 정의 제거 — 원작자 8인자 판(settle·C5 진단) 단일 | 정책 2-A · 3426508d |  |
| src/bin/cysd/handlers.rs | 비덩어리-b | (신규 헬퍼 · quiet_secs_consistent 앞) | synth | scrollback_stale_now 헬퍼 추가 — 우리 ⑴ 판독을 read_text arm 밖으로(원작자 소스 핀 read_text arm 의 .last_output 금지) | e6c0d1af · 원작자 R1 codex BLOCK 핀 |  |
| src/bin/cysd/handlers.rs | 비덩어리-c | (usage.report claude 귀속 블록 조건) | synth | agent == "claude" → cys::is_claude_agent(&agent) (우리 D6-2 파생 에이전트 귀속을 원작자 B3 블록에 이식) | H5 · 75fdf2e2·f554bf6a | P |
| src/bin/cysd/handlers.rs | 비덩어리-d | (deliver_to_ceo · 자동병합) | drop | 우리 governance::note_line_submitted 호출 1줄 제거 — 우리 갈래2 R3 계수 기록(입력 계층) · 원작자 deliver_to_ceo 는 H4 하드축+H0 기계 소유 판정으로 대신함 | H6 · 7e7efefb · 정책 2-A | P |
| src/bin/cysd/handlers.rs | 비덩어리-e | (시험 모듈) | synth | 항목 단위 3자 병합 결과: theirs-added 257 · same 221 · ours-added 38 · theirs 11 · automerge 8 · ours 7 · 버림 5(ACL 별칭 use 1 · base 시험 2(A3) · d12_machine_flows 1 · both-deleted static 1) · 적응 2(d12_machine_never·u16) | H1·H2·H4 | P |

### ledger-governance-rs (45행)

| src/bin/cysd/governance.rs | 1 | 201-217 | synth | spawn_watchdog: 원작자 resubmit_withheld_submits + deliver_queued 4인자 채택 + 우리 v112-wake watch_wake::tick_probes 유지 | v112-wake 9937b657 · 원작자 F1 |  |
|---|---|---|---|---|---|---|
| src/bin/cysd/governance.rs | 2 | 738-815 | union | 우리 ⑶ role 회수(ROLE_RELEASE_GRACE_SECS·role_release_due·release_role_after_agent_death) + 원작자 check_agent_death 문서(RQFIX B-1) — 원작자가 본체를 check_agent_death_with_model 로 옮겨 우리 변경을 그 본체로 이식(항목 단위) | ⑶ · 원작자 R1F-IN |  |
| src/bin/cysd/governance.rs | 3 | 935-956 | synth | check_agent_death_with_model: 원작자 descendants(pid 보존) + 우리 v113-restore root_agent_cmd 증거 추가 | v113-restore |  |
| src/bin/cysd/governance.rs | 4 | 1016-1031 | synth | 에이전트 사망 시 미제출 계수 비우기(우리 Fable F2)를 원작자 API(clear_pending_input · input_gate 안)로 옮김 + 원작자 release_quiescing(R3SH-4) | G2 · d17dec40 | P |
| src/bin/cysd/governance.rs | 5 | 3052-3071 | theirs | persist_topology 직렬화 락 = 원작자 topology_write(R3-1c) — 우리 topology_persist_lock(S3)과 같은 효과 → 정책 2-A 원작자 이름 하나 | 정책 2-A R3-1c · 우리 S3 |  |
| src/bin/cysd/governance.rs | 6 | 6217-6580 | synth | 입력 계층 원작자 채택(DirectSendKind·DraftGateDenied·direct_send_text_gate_kind) · 우리 ④⑭ 판(stale_pending_contradiction·human_pending_after·impl DirectSendKind·EditKey) 버림 · 우리 prompt_boundary_verdict 문서 갱신은 유지 | 정책 2-A ④⑭ · 3426508d·19928670 |  |
| src/bin/cysd/governance.rs | 7 | 6604-7053 | synth | 원작자 observe_prompt(PromptObs)·모달 축·composer 판독 채택 · 우리 observe_screen 버림(소비자 소멸) · 우리 오버레이 4(is_rule_row·approval_in_prompt_tail·is_choice_dialog_footer·is_numbered_choice_row·gate_corpus_cached·approval_screen_now·seat_approval_pending) 유지 + merged_ready_marker 복원(원작자 삭제 · 우리 approval_screen_now 가 씀) | 오버레이 4 · dbg-queue-approval · precut ㉮ |  |
| src/bin/cysd/governance.rs | 8 | 7056-7098 | union | 우리 mark_queue_blocked(bool 반환 — queue.held 1회 판정) + 원작자 composer 보조 함수 | D7⑴ c1c5b8a3 |  |
| src/bin/cysd/governance.rs | 9 | 7441-7510 | synth | diff3 오정렬 자리(우리 deliver_head_locked 인자 ↔ 원작자 resubmit_withheld) — 항목 단위로 원작자 deliver_head_locked 8인자 + resubmit_withheld_one 채택 | 원작자 F1 |  |
| src/bin/cysd/governance.rs | 10 | 7605-7660 | synth | 오정렬 자리(우리 pop/Delivered ↔ 원작자 resubmit 계수) — 원작자 판 + 우리 v112-wake note_delivered 를 pop 블록 뒤(큐 락 밖)에 이식 | v112-wake |  |
| src/bin/cysd/governance.rs | 11 | 7675-7765 | union | 우리 ForceDeliverDenied(ApprovalPending 포함 · 자동병합) + 원작자 MachineHold(H 하드축) | dbg-queue-approval · 원작자 H |  |
| src/bin/cysd/governance.rs | 12 | 7772-7799 | union | ForceDeliverDenied::code(자동병합) + 원작자 MachineHold 축 이름 | - |  |
| src/bin/cysd/governance.rs | 13 | 7920-7987 | union | ForceDeliverDenied::message(자동병합) + 원작자 MachineInjector 이름 | - |  |
| src/bin/cysd/governance.rs | 14 | 8090-8162 | synth | force_deliver_entry: 우리 게이트③ role_seat_hold·게이트⑦ approval_screen_now 유지 + 원작자 프롬프트 게이트(prompt_gate_input) · 원작자 machine_direct_hold_masked | 오버레이 4 · D7⑴ |  |
| src/bin/cysd/governance.rs | 15 | 8178-8231 | union | 오정렬(우리 queue_paused 판독 ↔ 원작자 quiescing 판독) — 항목 단위 원작자 effective_quiescing_since + 우리 force 게이트 | - |  |
| src/bin/cysd/governance.rs | 16 | 8385-8459 | synth | deliver_queued 머리: 원작자 4인자·quiesce_hold·base_min_interval + 우리 dept_grace(D7⑴ r2) 틱당 1회 · 원작자 draft_machine_owned/note_machine_residue 수용 | D7⑴ · 원작자 H1 |  |
| src/bin/cysd/governance.rs | 17 | 8461-8604 | theirs | 오정렬(우리 큐 스냅샷 ↔ 원작자 seat_approval_live) — 원작자 seat_approval_live 채택(우리 seat_approval_pending 은 별도 유지) | 오버레이 1 · 원작자 A2-F1 |  |
| src/bin/cysd/governance.rs | 18 | 8606-8827 | synth | deliver_queued 마커 경로: 원작자 observe_prompt·maybe_reset_stale_pending_input(⑭ 대체)·prompt_gate_verdict 채택 · 우리 승인 화면 판독은 prompt_gate_input 승인 축에 OR(approval_screen_now) 로 이식 | G1 · 오버레이 4 · 정책 2-A ⑭ | P |
| src/bin/cysd/governance.rs | 19 | 8843-8940 | synth | SEAT 게이트: 원작자가 앞당긴 자리에 우리 role_seat_hold(빈 좌석·seat_unknown·부서 유예)+queue.held 1회+사유 해제 이식 · 원작자 draft_gate_verdict 6인자 | D7⑴⑵ · 02ffad23 |  |
| src/bin/cysd/governance.rs | 20 | 8942-9024 | synth | 배달 직전 ⑩ Q2 pause 재확인(우리 · 원작자 writer 탐침 ⓐ 와 겹치는 무해 방어) + 원작자 deliver_head_locked 8인자 · 원작자 draft_gate(모달 축) 채택 | G3 · ⑩ Q2 | P |
| src/bin/cysd/governance.rs | 21 | 9066-9110 | synth | 시험 락: 우리 PACK_DIR_ENV_LOCK = 원작자 PACK_ENV_LOCK 의 별칭(static 1개 · 리드 지시) + 원작자 InputOwner 등 | X-7 · 원작자 WP-5 |  |
| src/bin/cysd/governance.rs | 22 | 9132-9198 | union | 우리 test_wait_seat_runs(cfg test) + 원작자 InputOrigin | d17dec40 |  |
| src/bin/cysd/governance.rs | 23 | 9200-9495 | union | 시험 모듈 머리: 우리 시험(q2·v114·v116 등) + 원작자 PASTE_OPEN_TTL_SECS 등 — 항목 단위 병합 · q2 소스 핀 앵커를 원작자 다줄 호출로 적응 | ⑩ Q2 |  |
| src/bin/cysd/governance.rs | 24 | 20968-21026 | theirs | 시험 모듈 항목 단위 3자 병합 — 우리[] · 원작자[fn wp5_codex_idle_composer_delivers_via_prompt_marker] | - |  |
| src/bin/cysd/governance.rs | 25 | 21028-21141 | union | 시험 모듈 항목 단위 3자 병합 — 우리[fn v113_root_agent_cmd_counts_pane_root_agent_only, fn v113_root_agent_wired_into_seat_cache_and_liveness, fn wrapper_delegates_to_the_promoted_collector_source_pin] · 원작자[fn wp5_r1_codex_busy_frame_is_refused_measured_20260907] | - |  |
| src/bin/cysd/governance.rs | 26 | 22291-22441 | ours | 시험 모듈 항목 단위 3자 병합 — 우리[fn role_release_requires_sustained_death, fn revival_resets_the_grace_window, fn release_role_clears_both_registries_and_is_idempotent, fn releasing_master_clears_claim_timestamp, fn release_does_not_steal_role_taken_over_by_another_seat] · 원작자[] | - |  |
| src/bin/cysd/governance.rs | 27 | 24309-24342 | synth | 우리 r2_agent_death_clears_pending_input_counters 적응(사람 계수 = pending_input.human) | G2 |  |
| src/bin/cysd/governance.rs | 28 | 24899-24924 | theirs | 시험 모듈 항목 단위 3자 병합 — 우리[] · 원작자[] | - |  |
| src/bin/cysd/governance.rs | 29 | 25269-25388 | ours | 시험 모듈 항목 단위 3자 병합 — 우리[fn d7_empty_role_seat_hold_emits_queue_held_once, fn paint_alt_seat, fn run_alt_seat, fn v113_alt_screen_framed_claude_input_box_delivers, fn v113_alt_screen_unframed_row_blocks_with_true_reason…] · 원작자[] | - |  |
| src/bin/cysd/governance.rs | 30 | 25492-25726 | synth | 우리 ④⑭ 시험 4건(d12_human_pending_after_table·d12_gate_kind_tables·d12_draft_gate_verdict_truth_table·u14_*) 버림(구현 대체) · 원작자 시험 유지 | 정책 2-A |  |
| src/bin/cysd/governance.rs | 31 | 25788-26641 | ours | 시험 모듈 항목 단위 3자 병합 — 우리[const QA_PERMISSION_CLASSIC, const QA_PERMISSION_FULLSCREEN, const QA_READY_AFTER_ESC, const QA_PERMISSION_10ROWS, const QA_FOLDER_TRUST…] · 원작자[] | - |  |
| src/bin/cysd/governance.rs | 32 | 27123-27205 | union | 시험 모듈 항목 단위 3자 병합 — 우리[fn queue_head_wait_clamps_to_boot_and_surface_uptime, struct QueueEnvGuard] · 원작자[fn deadman_agent_never_started_socket_rebuts] | - |  |
| src/bin/cysd/governance.rs | 33 | 27438-27592 | ours | 시험 모듈 항목 단위 3자 병합 — 우리[fn v116_deliver_drops_stale_launch_line_instead_of_delivering, fn v116_deliver_stale_drop_keeps_prose_and_skips_tick_delivery] · 원작자[] | - |  |
| src/bin/cysd/governance.rs | 34 | 27612-27655 | drop | 우리 force_deliver_rig 는 우리 쪽이 지운 base 시험 도우미 — 원작자 무변경이라 삭제 유지 | - |  |
| src/bin/cysd/governance.rs | 35 | 27826-28041 | union | 시험 모듈 항목 단위 3자 병합 — 우리[fn force_deliver_empty_seat_refused_unknown_passes, fn d7_role_seat_hold_table_unknown_only_inside_creation_window, fn d7_dept_role_seat_without_observed_agent_tick_holds, fn d7_empty_queue_tick_clears_stale_blocked_reason, fn d7_released_seat_hold_clears_only_seat_reason_before_delivery…] · 원작자[fn scan_caches_are_keyed_by_full_input_and_pruned] | - |  |
| src/bin/cysd/governance.rs | 36 | 28153-28175 | theirs | 시험 모듈 항목 단위 3자 병합 — 우리[] · 원작자[] | - |  |
| src/bin/cysd/governance.rs | 37 | 28177-28190 | synth | 우리 r3_every_production_submit_point_notes_line_submitted(⑭/R3 입력 계층 핀) 버림 · 원작자 시험 유지 | 정책 2-A · 7e7efefb |  |
| src/bin/cysd/governance.rs | 38 | 28192-28208 | theirs | 시험 모듈 항목 단위 3자 병합 — 우리[] · 원작자[] | - |  |
| src/bin/cysd/governance.rs | 39 | 28482-28761 | ours | 시험 모듈 항목 단위 3자 병합 — 우리[fn orphan_feed_pending_expires_only_when_requester_is_gone_or_generation_changed, fn spawn_role_surface, fn agent_death_keeps_the_role_in_persisted_topology_and_only_tombstone_removes_it, fn corrupt_topology_is_isolated_not_silently_swallowed, fn preserved_entries_are_unique_per_role_even_if_the_previous_file_had_duplicates…] · 원작자[] | - |  |
| src/bin/cysd/governance.rs | 40 | 32903-33002 | union | 시험 모듈 항목 단위 3자 병합 — 우리[fn d7_sweep_publishes_expired_parking_without_any_parking_or_inheriting, fn d7_sweep_is_wired_into_the_watchdog_tick, fn watchdog_tick_survives_both_poisoned_todo_locks] · 원작자[fn set_state] | - |  |
| src/bin/cysd/governance.rs | 비덩어리-a | (H7 허용목록) | synth | 원작자 시험 조정(삭제 아님): h7_guard_none_producers_allowlist 에서 handlers::announce_seat_takeover·handlers::npm_prefix_pane_notice_req 2줄 빼고 governance::seat_inject_guarded 추가(우리 A3 화면 출력·오버레이 5 의 guard:None 생산자) | H2 · 리드 지시 | P |
| src/bin/cysd/governance.rs | 비덩어리-b | (seat_inject_guarded) | synth | WriteReq::Inject 에 원작자 필드 guard: None 추가 · note_line_submitted 본문 = clear_pending_input(원작자 상태기계) | 오버레이 5 |  |
| src/bin/cysd/governance.rs | 비덩어리-c | (seat_input_line) | synth | 우리 check_idle 좌석 입력줄 판독을 원작자 surface_prompt_marker·observe_prompt(PromptObs) 로 이식 | v113-restore |  |
| src/bin/cysd/governance.rs | 비덩어리-d | (prompt_gate_input) | synth | 승인 축 = 원작자 approval_or_gate_pending ∨ 우리 approval_screen_now(화면 꼬리 판독) | G1 · 오버레이 4 | P |
| src/bin/cysd/governance.rs | 비덩어리-e | (시험 deliver_head_locked 호출 10곳) | synth | 우리 시험의 6인자 호출에 원작자 신 인자(expect_output_gen·recheck)=None 추가 | - |  |
| src/bin/cysd/governance.rs | 비덩어리-f | (rename 이식) | synth | 항목 단위 병합 도구 결과: 원작자 추가 512 · 동일 343 · 우리 추가 127 · 원작자 판 38 · 우리 판 12 · 자동병합 4 · 충돌 14(전부 수동 해소) · 버림 = 우리 입력 계층 함수 5 + 시험 9 + observe_screen | - |  |

### ledger-state-rs (21행)

| src/bin/cysd/state.rs | 1 | 1181-1299 | synth | 오정렬 자리(우리 queue_parked_payload ↔ 원작자 InjectGuard) — 원작자 InjectGuard 등 채택 · 이름이 겹친 queue.parked payload 는 원작자 4인자 판 + 우리 3인자 판을 queue_role_parked_payload 로 개명해 공존 | S1 · acf4cdd5(D7⑵) · 원작자 Q7 | P |
|---|---|---|---|---|---|---|
| src/bin/cysd/state.rs | 2 | 2102-2165 | theirs | Surface 입력 필드 = 원작자 상태기계(pending_input·lone_key_exempt·pty_master_fd·agent_fg_pgid·esc_exempt_pgid·input_gen · pending_input_stale 는 원작자 자리) · 우리 input_gen·pending_input_human_bytes·pending_input_stale 중복 정의 버림 | 정책 2-A ④⑭ |  |
| src/bin/cysd/state.rs | 3 | 2396-2623 | union | Surface: 우리 display_no·numbers_row_owned(v116-num) + 원작자 cwd_blocked(U18) | v116-num |  |
| src/bin/cysd/state.rs | 4 | 4213-4276 | synth | Daemon: 우리 ⑧ queue_wal_write_blocked·queue_wal_block_reported 유지 + 원작자 큐 WAL 필드(만료 영속·dirty·blocked 사유·restore_incomplete·unpreserved) · 우리 topology_persist_lock 버림(원작자 topology_write) | S2 · ⑧ · R3-1c | P |
| src/bin/cysd/state.rs | 5 | 4280-4291 | union | Daemon: 우리 auto_restore_phase + 원작자 started_instant | eb5f9e34 |  |
| src/bin/cysd/state.rs | 6 | 4306-4321 | union | Daemon: 우리 named(이름 보고자 ctx) + 원작자 seat_ident_cache·alert_stale_held | 345f1ca8 · 원작자 B3 |  |
| src/bin/cysd/state.rs | 7 | 6112-6168 | theirs | 부팅 pause 복원 = 원작자 PauseInfo + 손상·판독 실패 fail-closed(우리 ⑩ restore_pause_state 와 같은 의미) — 우리 restore_pause_state·그 시험 버림 | ⑩ 791b600c |  |
| src/bin/cysd/state.rs | 8 | 6189-6274 | union | 부팅 큐 WAL: 우리 ⑧ guard_unreadable_queue_wal(원본 보존 사본·쓰기 금지) + 원작자 QueueWalRead·두 파일 보존·dedup — 우리 옛 load_queue_state 1줄 제거 | S2 · ⑧ | P |
| src/bin/cysd/state.rs | 9 | 6350-6365 | synth | Daemon 초기화: 우리 ⑧ 필드 + 원작자 필드 · topology_persist_lock 초기화 제거 | S2 |  |
| src/bin/cysd/state.rs | 10 | 6370-6375 | union | 초기화: 우리 auto_restore_phase + 원작자 started_instant | - |  |
| src/bin/cysd/state.rs | 11 | 6381-6391 | union | 초기화: 우리 named(디스크 복원) + 원작자 seat_ident_cache·alert_stale_held | - |  |
| src/bin/cysd/state.rs | 12 | 7167-7204 | synth | create_surface_with_env: 우리 v116-num 번호 할당(DisplaySpawnGuard · id=grant.id) + 원작자 config_dir 출처 확정 — 원작자 next_id 줄은 우리 할당기가 대신 | v116-num 8b8e90d1 |  |
| src/bin/cysd/state.rs | 13 | 7321-7353 | union | 스폰 전: 우리 wire_seat_profile_before_exec(dbg-D2 R12) + 원작자 cwd_probe(U18) | dbg-D2 R12 |  |
| src/bin/cysd/state.rs | 14 | 7518-7535 | theirs | Surface 초기화 입력 필드 = 원작자(우리 ⑭④ 필드 버림) | 정책 2-A |  |
| src/bin/cysd/state.rs | 15 | 7580-7587 | union | Surface 초기화: 우리 display_no·numbers_row_owned + 원작자 cwd_blocked | - |  |
| src/bin/cysd/state.rs | 16 | 7828-7933 | synth | 자력 종료(EOF) 큐 처분: 잠정 우리 D7⑵ 역할 주차(parked_queues → claim_role 상속) + 원작자 drain_active_except_inflight·record_active_drain·만료 큐 처분(discard_expired_queue·park_expired_to_restored) · 원작자 Q7 park_active_to_restored 는 이 자리에서 쓰지 않음(reap 경로엔 남음) | S1 | P |
| src/bin/cysd/state.rs | 17 | 8265-8280 | synth | persist_pause = 원작자 pause_persist_lock + 원자 교체 위에 우리 ⑩ Result 반환 | ⑩ · 리드 지시 |  |
| src/bin/cysd/state.rs | 18 | 8295-8303 | synth | write_json_atomic 결과를 map_err 로 돌려준다(stderr 1줄은 원작자 그대로) | ⑩ |  |
| src/bin/cysd/state.rs | 19 | 9044-9121 | theirs | run_writer_loop = 원작자 run_writer_loop_tracked 위임 · 우리 SubmitGuarded arm 은 tracked 루프에 이식(H7: 표식 무접촉) | precut ㉮ · H7 |  |
| src/bin/cysd/state.rs | 20 | 12607-15946 | union | 시험 모듈: 항목 단위 병합(우리 dbg_r12·r12·v116_num_tests·d7·⑧ WAL 시험 등 + 원작자 c5 등) · 우리 pause_restore_fails_closed_on_unreadable_or_corrupt_state 버림(restore_pause_state 소멸 · 원작자 부팅 판이 같은 의미) | ⑩ |  |
| src/bin/cysd/state.rs | 비덩어리-a | (run_writer_loop_tracked) | synth | WriteReq::SubmitGuarded arm 을 원작자 추적 writer 루프에 추가(최소 간격 대기 뒤 refuse_now → 쓰지 않음 · inject_track 무접촉) | H7 · 7b0ab491 | P |
| src/bin/cysd/state.rs | 비덩어리-b | (항목 단위 병합 통계) | synth | 원작자 추가 132 · 동일 205 · 우리 추가 47 · 원작자 판 33 · 우리 판 9 · 자동병합 4(WriteReq 포함 — Inject{guard}·SubmitAfterGap{withhold}·SubmitGuarded 공존) · 충돌 7(전부 수동) | - |  |

### ledger-approval-rs (11행)

| src/bin/cysd/approval.rs | 1 | 188-227 | ours | signing_payload: 우리 ⑲ 재작성(7줄 표 · 원문 바이트 불변 — golden 시험 고정) | ⑲ cysr-117 |  |
|---|---|---|---|---|---|---|
| src/bin/cysd/approval.rs | 2 | 229-252 | synth | 우리 이음 루프 끝에 원작자 TTL 말미 한 줄(\nexpiresAt=<f64> · None 이면 무변경)을 같은 바이트로 얹음 | 원작자 B-3 |  |
| src/bin/cysd/approval.rs | 3 | 560-606 | ours | signing_secret = 우리 signing_secret_at(키 부재일 때만 생성·잠금·0바이트 복구 · 64519b13·47944bbc) — 원작자(판독 실패=None·0바이트 재생성)의 상위집합 | A2 · ⑨ | P |
| src/bin/cysd/approval.rs | 4 | 802-857 | synth | 오정렬 자리 — 원작자 ttl_records_path·load_records_from(두 저장소) 채택 + BOM 벗기기 오버레이 · 우리 load_records_at 은 시험 판으로 유지 | A1 · A1-F1 | P |
| src/bin/cysd/approval.rs | 5 | 859-874 | theirs | load_records_from 본문(원작자) | - |  |
| src/bin/cysd/approval.rs | 6 | 878-889 | theirs | load_records_from 본문(원작자) | - |  |
| src/bin/cysd/approval.rs | 7 | 894-925 | theirs | load_records() -> Vec = 원작자(try_load_records().unwrap_or_default()) — 핸들러·원작자 시험 기준(H3) | H3 · A1 | P |
| src/bin/cysd/approval.rs | 8 | 929-941 | theirs | save_records = 원작자 두 저장소 분할 저장(save_records_to) · 우리 save_records_at 은 시험 판으로 유지 | A1 | P |
| src/bin/cysd/approval.rs | 9 | 947-963 | union | 우리 SAVE_SEQ(호출마다 다른 tmp) 유지(save_records_at 이 씀) + 원작자 save_records_to | A1 |  |
| src/bin/cysd/approval.rs | 10 | 966-985 | union | 우리 save_records_at 본문 + 원작자 mutate_records 등 | A1 |  |
| src/bin/cysd/approval.rs | 11 | 1194-1762 | union | 시험 모듈 항목 단위 병합 — 우리 golden·signing_secret·load/save 시험 전부 + 원작자 TTL·mutate 시험 전부 | - |  |
| src/bin/cysd/approval.rs | 비덩어리-a | (load_records_at·save_records_at·touch_best_match) | synth | 운영 미사용이 된 우리 경로 판 3개에 cfg_attr(not(test), allow(dead_code)) + 사유 문서 — 우리 시험 판으로 남김 | A1 |  |

### ledger-rust-rest (38행)

| src/lib.rs | 1 | L54-58 | union | 우리 mod 4(reinject_guard·restore_mark·seat·submit_probe)+원작자 agent_markers 서로 다른 모듈 추가 | - |  |
|---|---|---|---|---|---|---|
| src/factory_reset.rs | 1 | L25 | synth | 인벤토리 배열 길이만 충돌: 원작자 27(.install-identity·.gui-onboard-attempts)+우리 dept-requests = 28(본문은 자동 병합) | 095de5ba·4ccfdc75 |  |
| src/bin/cysd/boot_supervisor.rs | 1 | L2178-2248 | synth | 원작자 H5 하드축 보류·R3SH-3 미룸 구조 채택 + pane_notice_line 몸통을 우리 A3 단일 입구 seat_inject_guarded 로(자동 병합된 우리 핀 ledger_record_precedes_the_action 이 요구) | v115-restore A3·0.14.42 H5 |  |
| src/bin/cysd/channels.rs | 1 | L1640-1646 | synth | 인자 = surface(원작자 inject_master_confirmed 가 &Arc<Surface> 를 받음) | A3 |  |
| src/bin/cysd/channels.rs | 2 | L1651-1728 | synth | 원작자 H3 inject_master_confirmed+인계 표식(note_handoff)을 우리 seat_inject_guarded 앞에 찍고 미인계(WriterUnavailable·HeldVacant)면 undo_handoff · 큐 포화 channel.dropped 유지 · 원작자 note_inbox_write_failed·inbox_stalled_due·InboxDelivery 수용 | A3·v115-review 6·0.14.42 H3 |  |
| src/bin/cysd/main.rs | 1 | L58-68 | union | 우리 mod watch_wake + 원작자 U16 주석(시험 모듈 선언은 파일 끝) | - |  |
| src/bin/cysd/main.rs | 2 | L7698-7831 | union | 원작자 cysd_args_tests·team_gate/team_token/return_absorb/send_settle 시험 모듈 + 우리 d6_probe_tests(끝 · 꼬리 주석 없음) | 정책 2-B 팀 갈림 M1 | P |
| src/first_run_gates.rs | 1 | L2324-2386 | synth | 우리 options 판독(1.1.6 Gate.options) + 원작자 default_index 0 허용·명시 null 지움(0.14.31 R1) | f8dc91b0 |  |
| src/first_run_gates.rs | 2-3 | L3093-5608(myers) | union | 시험 모듈 양쪽 신규 시험(우리 R16·focus_plan / 원작자 override·banner) — myers 정렬이 얽혀 histogram 3-way(git merge-file --diff-algorithm=histogram)로 재병합해 2덩어리로 풀고 ours+닫는 괄호+theirs · fn 목록 대조 117 일치 | f845c2d8·cc326b2f |  |
| src/bin/cysd/usage.rs | 1 | L1566-1580 | synth | 우리 T2 reattach_tail(파일별 유예 기억) + 원작자 clear 가드 v3 주석 · ctx_threshold_armed 재무장 줄은 버림(원작자 v3 가 필드 제거 · handlers 해소본 핀이 부재 단언) | T2 v116-usage·clear 가드 v3 |  |
| src/bin/cysd/usage.rs | 2 | L1659-1666 | union | 원작자 B3 carried_rate(rate·관측 시각·귀속 계정 이월) + 우리 T2 window_estimated | 0.14.43 B3·T2 |  |
| src/bin/cysd/usage.rs | 3 | L3977-7711 | union | 시험 모듈 끝 양쪽 신규 시험(base 빈칸): 우리 dbg-D2·T2·B1·B2 + 원작자 clear 가드 성질 시험 · 닫는 괄호 보정 · 우리 시험 ObservedUsage 문자 3곳에 원작자 신설 필드 rate_observed_at·rate_account 기본값 추가 · fn 목록 대조 294 일치 | dbg-D2·T2·B3 |  |
| src/bin/cysd/schedule.rs | 1 | L418-485 | union | builtin 잡 목록: 우리 dept-request-tick·ctx-relay-base + 원작자 cso-alert-inbox-check-60m(서로 다른 신규 id · 버전 범프 없음) · JSON 객체 닫힘 보정 | 095de5ba·ef6d3ab5·WP-3 B |  |
| src/bin/cysd/schedule.rs | 2 | L841-865 | synth | 원작자 ensure_builtin_jobs_at/_locked(디렉터리 잠금 A11) + 그 뒤 우리 공유 락 acquire_settings_lock(⑰) — CLI 해소본 schedule_file_transaction 과 같은 순서 | 4fca9226·A11 | P |
| src/bin/cysd/schedule.rs | 3 | L891-914 | synth | 원작자 X8 정규화·(changed,preempted,edited_action) + 우리 apply_dept_lane_jobs 소급(changed 를 mut) | bec4c7e2(M6)·X8/X13 |  |
| src/bin/cysd/schedule.rs | 4 | L1555-1577 | synth | 원작자 remove_job_from_file_at(디렉터리 잠금) + 우리 공유 락 · 함수 이름은 원작자 것(우리 시험 2곳 호출 remove_job_at→remove_job_from_file_at 개명) | 4fca9226·A11 | P |
| src/bin/cysd/schedule.rs | 5 | L1583-1623 | synth | 원작자 drop_job_and_canonicalize+write_schedule_atomic(원자) + 우리 ⑰ 변화 없으면 쓰지 않음(root 비교) · 원작자 requeue_oneshot_after_frozen 머리 수용 | 4fca9226·R3SH-5 |  |
| src/bin/cysd/schedule.rs | 6 | L1625-1660 | synth | 원작자 R3SH-5② 동결 원샷 되돌리기 + 우리 ⑰: 판독·파싱 실패·jobs 비배열 = 쓰기 금지(원작자 원판은 빈 스케줄로 접어 덮음) · 공유 락 · 실패 문구에 판독 추가 | 4fca9226 ⑰·정책 §3-13 |  |
| src/bin/cysd/schedule.rs | 7 | L2083-2158 | theirs | 우리 fn inject(A3 seat_inject_guarded) 버림 — 원작자가 inject 를 inject_on(C8 계상)으로 대체 · A3 빈 좌석 보류는 덩어리 밖 inject_on 머리에 agent_seat_vacant_now→hold_for_vacant_seat 로 이식(+큐 포화 schedule.warning) | A3·v115-review 6·0.14.43 C8 | P |
| src/bin/cysd/schedule.rs | 8 | L3036-3047 | synth | 시험 계수 주석 11개 + 원작자 3-튜플 | - |  |
| src/bin/cysd/schedule.rs | 9 | L3073-3079 | synth | jobs.len 12(사용자1+built-in11) | - |  |
| src/bin/cysd/schedule.rs | 10 | L3096-3143 | union | 우리 deptreq·ctxrelay 계약 핀 + 원작자 alert 60분 핀 | - |  |
| src/bin/cysd/schedule.rs | 11 | L3225-3231 | synth | jobs.len 12 유지 | - |  |
| src/bin/cysd/schedule.rs | (밖) | load_jobs_at·시험 | synth | HotReload 쓰기 모드에 우리 공유 락 추가(디렉터리 잠금 뒤) · 우리 시험 builtin_dept_request_tick_conflict_when_id_preempted 의 2-튜플 → 3-튜플 | 4fca9226 | P |
| src/bin/cysd/accounts.rs | h1 | L57-64(histogram) | theirs | use 줄: 원작자 {ObservedUsage, RateWindow} (Daemon 중복 import 제거는 양쪽 같음) | - |  |
| src/bin/cysd/accounts.rs | h2 | L120-128 | union | AccountView 필드: 우리 scoped(모델 스코프 게이지 · 패널) + 원작자 source_error | d7b890f3·agy-rpc |  |
| src/bin/cysd/accounts.rs | h3 | L521-545 | theirs | fixed_resolution 의 claude 팔 — 원작자가 claude_resolution/note_rate_at_resolved 로 옮김 · 우리 D6-2(is_claude_agent)는 덩어리 밖 원작자 claude 판정 3곳(note_rate_at_resolved·agent_is_claude·assemble_seat_view)에 이식 | 75fdf2e2·f554bf6a |  |
| src/bin/cysd/accounts.rs | h4 | L552-571 | ours | agy(antigravity) 귀속 = None(usage-noagy 박사님 결정) — 원작자 RC1 agy 행 부활과 정면 · 결정대기 U1 · _home 로 미사용 인자 표기 | 1bb646de | P |
| src/bin/cysd/accounts.rs | h5,h8,h9,h11 | (4곳) | union | AccountView 리터럴에 scoped+source_error 둘 다 | - |  |
| src/bin/cysd/accounts.rs | h6 | L767-810 | synth | note_resolved: 우리 merge_rate_windows(창 라벨 단위 표시 병합·기각 창 비영속) + 원작자 source_error 지움·note_alert_input(B3 경보 입력)·alert_src 스냅샷 이중 스로틀 | 57f6a92d·4f18c032·B3 |  |
| src/bin/cysd/accounts.rs | h7 | L862-951 | theirs | seed_known 시드 = 원작자 discover_at/apply_discovered(R4-F3 락 밖 IO) · 덩어리 밖 apply_discovered 에 scoped 추가 + agy 시드 제거(usage-noagy · found.agy 무시) · apply_agy_error 의 agy 행 신설 삭제 | 1bb646de·R4-F3 | P |
| src/bin/cysd/accounts.rs | h10 | L1202-1208 | theirs | 콘솔 숨김 주석 — 원작자 U5 주석 채택(코드 줄은 공통으로 hide_console) | 9501dd66·U5 |  |
| src/bin/cysd/accounts.rs | h12 | L2137-2146 | synth | local_json rate: 원작자 rate 벡터(alert_eligible) 채택 + 그 원소 생성을 우리 rate_window_json(stale·stale_reason)으로 교체(덩어리 밖 map) | 61d30826·B3 |  |
| src/bin/cysd/accounts.rs | h13 | L2154-2187 | union | local_json 행: 우리 scoped 게이지 + 원작자 source_error·in_use·rate_observed_at·alias·current_profiles | d7b890f3·f0f60242·B1·B3 |  |
| src/bin/cysd/accounts.rs | h14 | L2306-2458 | synth | 우리 merge_rate_windows 유지 + 원작자 B3 신선도 규칙·좌석 신원 표 블록 · 우리 alert_rates(D6-1 죽은 창 필터) 버림 → 원작자 alert_rates(alert_rates_with · rate_window_live+in_use+1800s)가 같은 판정을 대체 | 75fdf2e2·B3 | P |
| src/bin/cysd/accounts.rs | h15 | L3568-7637 | union | 시험: 원작자 mod tests 신규 3442줄 + 우리 noagy·stale·fresh_limit 시험 + 우리 mod acceptance_v116(닫는 괄호 보정) · fn 목록 대조 300 일치(view 는 모듈 다름) | a6370a4b |  |
| src/bin/cysd/accounts.rs | (밖) | probe_targets·current_targets·claude_identity_at | synth | 우리 OAuth 프로브 신원 해석을 원작자 정본(identity_config_file · 기본 프로필 홈 직하 폴백)으로 · current_targets 는 데몬 락 없이 빈 지역 상태(R4-F2 규율) · claude_identity_at 의 cfg(test) 해제 | d7b890f3·R4-F2 |  |
| src/bin/cysd/accounts.rs | (밖) | note_oauth | synth | oauth 관측도 원작자 경보 입력(note_alert_input)에 싣는다(종전 우리 경보 = 표시 rate 기반 보존) + source_error 필드 | d7b890f3·B3 | P |
| src/bin/cysd/accounts.rs | (밖) | 시험 리터럴 | synth | 원작자 시험 old_declared_views 의 AccountView 리터럴에 scoped 추가(컴파일) | - |  |

### ledger-tauri (23행)

| 파일 | 원 덩어리 번호 | 원 줄 범위 | 판정 | 근거 1줄 | 관련 판정표 번호·커밋 | 잠정 |
|---|---|---|---|---|---|---|
| src-tauri/src/main.rs | H1 | 14-25 | ours | mod feedback 은 양쪽 같은 모듈 선언 — 우리 주석 + macupdate(B7) 유지 · 모듈 본문은 feedback.rs 합성이 정한다 | 2904cda6 · 97d43425 · 42dd2bf3 |  |
| src-tauri/src/main.rs | H2 | 601-639 | synth | send_input: 성공 = 원작자 C1(resp["result"] 그대로 · Result<Value> 서명은 자동 병합된 원작자 것) · 실패 = 우리 send_input_error_text(코드 없으면 message 만) — 우리 d12 핀·원작자 restartplan rpc_full 핀 둘 다 충족 | 3426508d ④ · 원작자 0.14.31 C1 · 51654319 | P(T3) |
| src-tauri/src/main.rs | H3 | 4558-4566 | synth | probe_folder_permissions(우리 v116 A-3 분리 함수)에서 원작자 U14 push_perm_warning(쌓고 쏜다) + 우리 denied_folders.push | b5dd7100 · 8c7bc34d(U14) |  |
| src-tauri/src/main.rs | H4 | 4656-4668 | synth | spawn_org_restore 함수 단위 합성(H4~H7 한 몸): 우리 판(DeptRestoreAction·run_sidecar_restore_judged·restore_note·depts_unreadable) + 원작자 W-2 BootWorkGuard 무장 — 묘비 주석은 우리 판(UI 두 경로 정렬 서술) | ffcb8500 · 76d4ccf3 · 원작자 89d41130+3baa488b(우리가 합본 재구현) · 22b59fff(W-2) |  |
| src-tauri/src/main.rs | H5 | 4681-4700 | ours | 묘비 미상 skip emit — 원작자 tomb_unknown 판과 같은 동작, 우리 dept_restore_action(tombs.as_ref()) 경로 유지(우리 t2_spawn_org_restore 핀) | ffcb8500 · 3baa488b |  |
| src-tauri/src/main.rs | H6 | 4704-4732 | synth | 레지스트리 판독 실패: 원작자 D5-b 꼴 `match list_depts()` + 「전건 보류」 skip emit + 우리 depts_unreadable 을 done/error 알림에 싣기 — 원작자 k2_03_d1_d5b 핀과 우리 Fable R1#3/R2 A 동작 둘 다 충족 | 8813fae0 ① · 원작자 1b40379c(D5-b) |  |
| src-tauri/src/main.rs | H7 | 4786-4809 | ours | HoldRelaunch/SidecarRestore = 우리 판정 함수 경로(원작자 `!alive && tomb_unknown` 과 같은 결과) + run_sidecar_restore_judged · 덩어리 밖 원작자 D1 stop_err(teardown Err 를 detail 에) 수용 | ffcb8500 · 451d7861 · 원작자 1b40379c(D1) |  |
| src-tauri/src/main.rs | H8 | 5131-5149 | union | merge_account_rows(원작자 추출 함수)에 우리 scoped 자기 시각 경쟁(keep_scoped) + 원작자 T1 current_profiles·in_use·alias·source_error — 사이드바 패널 백엔드에 숨김 거름 없음(master ②) | d5a1b235 · 74269d94 · 원작자 314dd77a(T1) · 2e8b2e8a |  |
| src-tauri/src/main.rs | H9 | 5945-6046 | synth | allocate_dept_daemon: 서명 = 원작자(team_spec·progress_id — UI {catalogKey,teamSpec,progressId}) · 팀 제안 검증 = 원작자(휴면 · master ①) · 실행 = 우리 run_dept_tool(맥 dept.run 대행 · v114 핀) · 단계 표지는 끝난 뒤 stderr 에서 읽어 spawned 근거 + 실패문에서 strip_stage_lines · 실시간 dept-create-progress 미배선 | 06d3aaa8 · fbf8d191(v114) · 원작자 8820fc74(GU) · da03cbb6(R2F-UI) · 6cca7420(U16) | P(T1) |
| src-tauri/src/main.rs | H10 | 6050-6059 | synth | 실패 코드 판정: 원작자 조건(catalog_key \|\| team_spec) + 우리 DeptToolOut.code | 원작자 6cca7420 · 우리 fbf8d191 | P(T1) |
| src-tauri/src/main.rs | H11 | 6440-6500 | synth | list_depts = 원작자 단일 판독기 read_json_or_empty + fill_canonical_dept_sockets(D4) · 우리 dept_count_or_unreadable 유지 · 우리 list_depts_at 은 같은 판독기로(정책 불변: 없음=빈 목록·BOM=읽음·오류=Err) — 우리 시험 단언 「읽기 실패」→「판독 실패」 문면만 갱신 | 8813fae0 ① · 원작자 K2-03/C2 · D4 |  |
| src-tauri/src/main.rs | H12 | 7322-7344 | synth | factory_reset_preview: 원작자 W-1-b live_sessions_known + 우리 dept_count_or_unreadable(부서 수 미상=null + 사유) — 반환 JSON 은 양쪽 키 모두 이미 자동 병합 | 8813fae0 · 원작자 W-1-b |  |
| src-tauri/src/main.rs | H13 | 9157-9165 | union | invoke_handler: 우리 restart_after_update(B7) + 원작자 J2 update_attempt_report·smart_app_control·update_checked_launch_enabled(main.ts 가 부름 · X2 J2/WU 이식) | 97d43425 · 원작자 f7f3dbf7 · aa0b1adb |  |
| src-tauri/src/main.rs | H14 | 9210-9218 | union | setup 부팅 태스크: 원작자 `let _boot_guard = boot_guard;` 먼저 + 우리 v116 gui_onboarded_before_boot 스냅숏 | b5dd7100 · 원작자 22b59fff |  |
| src-tauri/src/main.rs | H15 | 9602-10708 | union | 시험 add/add(base 빈칸) — 우리 시험 171줄 + 닫는 `}` + 원작자 시험 932줄(K2-03 등) · 중복 시험 이름 0(실측) | — |  |
| src-tauri/src/main.rs | H16 | 11910-12897 | union | 시험 add/add — 우리 v116 진리표 181줄 + 닫는 `}` + 원작자 J2 시험 803줄 | — |  |
| src-tauri/src/main.rs | H17 | 17432-17847 | union | 시험 add/add — 우리 T2·X-1 190줄 + 원작자 U7·T1 병합 시험 222줄 | — |  |
| src-tauri/src/main.rs | nc-1 | (덩어리 밖) invoke_handler 원작자 U6 블록 12줄 | drop | 원작자 U6 피드백 명령 12개 등록 제거 — feedback_submit·feedback_discard 이름이 우리 명령과 겹치고(중복 등록) UI feedbackmodal 미배선 · 코드는 feedback.rs u6_local_bundle 에 휴면 보존 | D-19 · 원작자 42dd2bf3 | P(T2) |
| src-tauri/src/main.rs | nc-2 | (덩어리 밖) run_dept_teardown·stop_dept_daemon 주석 | synth | 종료코드 재번호: 「rc 10 = 레지스트리 판독 실패」 → rc 12(우리 번호 · 원작자 원판 10) — master#36f48cf7 ③ | 8813fae0 ① · 원작자 1b40379c(D1) |  |
| src-tauri/src/main.rs | nc-3 | (덩어리 밖) 시험 k2_03_d1_stop_dept_daemon_nonzero_rc_is_err_not_silent_ok | synth | 원작자 시험의 목 cys-dept `exit 10` → `exit 12` · 단언 rc=10 → rc=12(판독 실패 번호를 우리 12 로 — master ③) · 시험 삭제 아님 | master#36f48cf7 ③ |  |
| src-tauri/src/main.rs | nc-4 | (덩어리 밖) 우리 시험 list_depts_unreadable_is_error_not_zero_depts | synth | 단언 문면 「읽기 실패」→「판독 실패」(H11 판독기 통일 결과 · 정책 불변) | 8813fae0 ① |  |
| src-tauri/src/main.rs | nc-5 | (덩어리 밖) spawn_org_restore 머리 주석 | synth | 「★W-2 결정 A:」→「★W-2 (결정 A):」 — 우리 시험 v113 의 `org[..1400]` 바이트 자르기가 한글 글자 중간에 걸려 패닉하던 것을 피함(실측 경계 확인) | — |  |
| src-tauri/src/feedback.rs | H1 | 1-2557(전체 add/add) | synth | 본체 = 우리 판(2단계 업로드·보관함 재시도·화면 캡처 · D-19 동등=우리) + 원작자 FB_LOCK 취지 STAGE_LOCK(첨부·캡처·빼기·버리기 직렬화) · 원작자 U6 판은 하위 모듈 u6_local_bundle 로 통째 보존(명령 표지 주석 · use super→crate::no_console · 시험 보존 · 미등록) · 진단 동의·크기 상한·.part 원자 쓰기는 우리 흐름에 이미 있거나(상한·원자 쓰기) 해당 없음(진단 미전송) | 2904cda6 · 원작자 42dd2bf3 · e6003c76 | P(T2) |

### ledger-ui-rest (23행)

| 파일 | 원 덩어리 | 원 줄 범위 | 판정 | 근거 | 관련 | 잠정 |
|---|---|---|---|---|---|---|
| ui/src/deptlabel.ts | 1 | L113-355 | theirs | 우리 쪽 추가 0 — 원작자 K2-05 deptLaunchName·C1 restoreLaunchDecision·E3 resolveDeptLaunchName·F3 deptCloseAfterStop·I1 tombReapErrorToast 수용(우리 deptNameFromSocket 은 공통부에 그대로) | §2-B ①(원작자 추가분 수용) · 1b40379c |  |
| ui/src/drainverify.ts | 1 | L34-143 | union | 우리 drainVerifyNotice·continuityNotice·restoringRetryKeys·mergeRetry(V111-F4·v115r5·v113 B3) + 원작자 DrainUnreachable 타입·drainVerifyUnresponsiveLines(U4-B2②) — 미응답 줄을 우리 알림에 싣는 배선은 하지 않음 | f5614919 · 9e04b85c | P |
| ui/src/drainverify.test.ts | 1 | L6-20 | union | import 합집합(우리 6 + 원작자 drainVerifyUnresponsiveLines) | — |  |
| ui/src/drainverify.test.ts | 2 | L55-248 | union | 우리 사후 알림·이어짐·B3 핀 + 원작자 미응답 줄 시험(양쪽 describe 를 각각 닫아 이음) | — |  |
| ui/index.html | 1 | L15-46 | ours | 상단바 = 우리(피드백 맨 앞·한국어 「창 닫기」「파일」·+New/Split 글자 1.1.5 모습 — 박사님 09-25/09-26 결정) · 원작자 icon-btn 아이콘화 미수용(정책 §2-B ① 문구와 충돌 → X15) | d395ffe8 · 76d2b5e9 · 06664be3 ↔ dde33c26 | P |
| ui/index.html | 2 | L48-54 | ours | 업데이트 단추 「업데이트」·배지 "!"(우리 X2 · 원작자 U9 「…」 미수용) | X2 | P |
| ui/index.html | 3 | L61-80 | ours | 사이드바 머리 = 우리(＋부서는 #ws-expert 전문가 모드 칸) · 원작자 U17 문구 미수용 | X3 · aaf5ba7b | P |
| ui/index.html | 4 | L82-97 | ours | 우리 #ws-usage(사용량 패널 절대)·#ws-credit(출발지 표기) · 원작자 #wsbar-foot(U1 사용량·U6 피드백 슬롯·U17 전문가용) 미수용 | §2-B 사용량 패널 · X3 · D-19 | P |
| ui/src/style.css | 1 | L93-101 | ours | .badge[hidden] 짝 규칙(D4 #3) + 배지 "0" 주석(X2) | X2 | P |
| ui/src/style.css | 2 | L403-513 | synth | 우리 그룹 머리 주석 유지 + 원작자 `.modal p { overflow-wrap: anywhere; }` 1줄 수용 · #wsbar-foot/#wsbar-usage/#wsbar-expert/#btn-ws-dept(전문가 칸) 규칙 미수용 | U1·U17 미수용 | P |
| ui/src/style.css | 3 | L769-785 | ours | 헤더 경보 배지 규칙 제거 유지(박사님 09-15) + 주석 1줄 — 스트립 .cc-alert-row.unknown 은 비충돌부에 이미 있음 | X7 · 94dd866b | P |
| ui/src/style.css | 4 | L922-933 | synth | #toasts: 원작자 층서 토큰 z-index var(--z-toast) + 우리 max-height 40vh(복원 카드와 짝) | team-confirm T1(정책: z-index 수용) · v116 Fable 2R |  |
| ui/src/style.css | 5 | L1231-1253 | synth | 원작자 .dept-pending-stage(GU) + 공통 .dept-idle-btn · .role-slot(U2) 규칙 제외 | GU · X1 |  |
| ui/src/style.css | 6 | L1288-1299 | union | 우리 .cc-tbar.dead/.cc-acct-row.dead(stale) + 원작자 .cc-acct-badge.on/.cc-acct-row.dim/.cc-acct-hide(CC 계정 행 합성) | 정책 CC 행 합성 |  |
| ui/src/wswiring.test.ts | 1(추가·추가) | L14-1669 | synth | 양쪽이 따로 더한 파일 합본: 우리 핀 16 describe 전부 + 원작자 22 describe(같은 본문 5개는 1회만 · 다른 본문 3개는 「(원작자 0.14.43 판)」 접미로 둘 다) · import 합집합 · 공용 도우미 1벌(stripComments) | ffcb8500(우리 A2-2) ↔ f3493e93~a28dd1aa(원작자) | P |
| ui/src/wswiring.test.ts | 1-a | 우리 A2-2 it 2건 | synth | 우리 재구현 줄 핀 2건(묘비 null 드롭 금지·묘비 미상 보류 위치)을 main.ts 의 원작자 대체물(restoreLaunchDecision·decision.reason "tombstone-unknown")로 재조준 — 계약 동일 | main.ts #67·#68 |  |
| ui/src/wswiring.test.ts | 1-b | 원작자 D2 tomb-unknown sticky it | theirs(.skip) | 결정대기 연동 X16 — main.ts #69 가 우리 토스트를 잠정 유지 | X16 | P |
| ui/src/wswiring.test.ts | 1-c | 원작자 F2 묘비 조회 1회 it | synth | 계수 범위를 start() 로 좁힘 — 우리 M7① 의 새 부서 감지용 묘비 조회(3초 틱 · claimFlight)가 정당한 두 번째 호출 | 2309a692 |  |
| ui/src/wswiring.test.ts | 1-d | 원작자 G4/I2 탭 닫기 it | synth | 앵커 `const wsName = ws.name \|\| UNTITLED;` → `const wsName = `(우리 D4#4 wsLabel) | f695ff14 계열 |  |
| ui/src/wswiring.test.ts | 1-e | 원작자 U2+U3 좌석 배치 배선 describe(29 it) | theirs(.skip) | 결정대기 연동 X1 — seatlayout.ts 순수성 핀 describe 는 그대로 실행 | X1 | P |
| ui/src/main.ts | (후속) | ctxGroupLabel · onDaemonEvent ap | synth | deptNameFromSocket(x) 호출 2곳 → deptLaunchName(x, null)(동작 동일 · 원작자 C1 census 「main.ts 는 파서를 직접 부르지 않는다」 충족) | 1b40379c C1 |  |
| ui/src/wswiring.test.ts | 결정③ | it.skip(X16)·describe.skip(X1) | (기록) | 수리 단계에서 우리 동작 기준으로 고침(삭제 금지 · 지금은 .skip 유지) | master#36f48cf7 | P |
| ui/src/deptlabel.ts | 결정④ | 주석 275행 | ours | 「rc 10」→ 원작자 원판 rc 10 · 우리 판 rc 12 병기(코드 해석 없음) | master#36f48cf7 |  |

### ledger-pack (127행)

| 파일 | 원번호 | 원줄범위 | 판정 | 근거 | 관련 | 잠정 |
|---|---|---|---|---|---|---|
| cysjavis-pack/bin/cys-dept | 1 | L20-43 | synth | 우리 PATH 말미 append(dbg-D3 #F1) + 원작자 U15 CYS_PY 번들 표식 앞붙임 블록(원작자 첫 줄=base prepend 는 버림) | 80aaf6e6 · 25beb0c6 |  |
| cysjavis-pack/bin/cys-dept | 2 | L230-254 | theirs | 원작자 formation_lane_pack·_cys_fm_python·--cwd·onboard + 리다이렉트 서브셸 바깥(55d259aa)이 우리 dbg-D1 #2 와 같은 효과 | 0a2b6bdb · 55d259aa · U10 |  |
| cysjavis-pack/bin/cys-dept | 3 | L531-604 | ours | 레지스트리 판독 = 우리 ①(exit 12 · 0바이트 재판정 · 형식 검사) — 원작자 K2-03 판(exit 10)은 같은 결함 다른 구현 | 정책 §2-B · 8813fae0 · 47944bbc |  |
| cysjavis-pack/bin/cys-dept | 4 | L613-628 | ours | reg_names 우리 공용 판독(exit 12) | 정책 §2-B |  |
| cysjavis-pack/bin/cys-dept | 5 | L670-689 | ours | reg_upsert 잠금 안 판독 = 우리 12 | 정책 §2-B |  |
| cysjavis-pack/bin/cys-dept | 6 | L716-735 | ours | reg_remove 판독 = 우리 12 | 정책 §2-B |  |
| cysjavis-pack/bin/cys-dept | 7 | L739-821 | ours | 우리 B11 reg_fence_close·self_os_pid(원작자 측 빈 덩어리) | 64669e21 · 3d2db202 |  |
| cysjavis-pack/bin/cys-dept | 8 | L844-863 | ours | reg_set_meta 판독 = 우리 12 | 정책 §2-B |  |
| cysjavis-pack/bin/cys-dept | 9 | L1056-1068 | synth | reg_get_field = 원작자 fail-closed 구조(호출부 rc 전파 J5) + 우리 판독(BOM·0바이트·형식)·번호 12 | 정책 §2-B · J5 M2 |  |
| cysjavis-pack/bin/cys-dept | 10 | L1101-1120 | ours | reg_set_field 판독 = 우리 12 | 정책 §2-B |  |
| cysjavis-pack/bin/cys-dept | 11 | L1249-1259 | theirs | seed_schedule = 원작자 javis_dept_schedule(덮어쓰기→owner 스코프만 거름) · ctx-relay-tick 은 cysd apply_dept_lane_jobs(우리 schedule.rs)가 부트 때 넣고 필터가 보존 | e8e5f6dd · a98889f8 |  |
| cysjavis-pack/bin/cys-dept | 12 | L1769-1851 | union | 우리 v116 ceo_receipt_matches·ceo_md_is_standard·pre_ceo_* + 원작자 U10 ceo_notices_close | v116 · U10 |  |
| cysjavis-pack/bin/cys-dept | 13 | L1856-1870 | synth | 원작자 ceo_notices_close(상시 경로) + 우리 pre_ceo_valid 게이트 | U10 리뷰1 M1 · v116 ⓕ |  |
| cysjavis-pack/bin/cys-dept | 14 | L2592-2599 | synth | launch 스폰 뒤 대기 = 우리 boot_wait/boot_fail_teardown + 원작자 K2-07 sock_len_diag(원작자 ready_wait·노브·ready_fail_note 는 안 씀) | dbg-D10 · 0.14.43 GP | P(X-WAIT) |
| cysjavis-pack/bin/cys-dept | 15 | L2741-2760 | ours | allocate 예약 판독 = 우리 12 | 정책 §2-B |  |
| cysjavis-pack/bin/cys-dept | 16 | L2797-2807 | union | 예약 엔트리에 원작자 reserved_at + 팀 제안 메타 + 우리 gen(B11) | R2F-PK S4 m3 · B11 |  |
| cysjavis-pack/bin/cys-dept | 17 | L2874-2881 | synth | 원작자 dept_stage probe 표지 + 우리 사전 검사 alive(핑 1회) | dbg-D1 #1 · 0.14.43 GP | P(X-PROBE) |
| cysjavis-pack/bin/cys-dept | 18 | L2886-2906 | synth | 원작자 스폰(env -u 역할 env 5종·토큰 경로 setsid·_dept_spawn_pid·stage wait) + 우리 boot_wait/boot_fail_teardown + sock_len_diag · 즉시 disown 제거(원작자 말미 disown) | dbg-D10 · WP-4 · 0.14.43 GP | P(X-WAIT) |
| cysjavis-pack/bin/cys-dept | 19 | L2939-2948 | theirs | 빈 셸 cwd = 원작자 dept_cwd(resolve_dept_cwd · 시드·편성과 같은 값) — 우리 dept_seat_cwd 와 같은 결과(allocate 는 방금 cwd 등재) | WP-2 R1 · v114 |  |
| cysjavis-pack/bin/cys-dept | 20 | L3077-3088 | union | 카탈로그 \r 제거 주석 양쪽(코드 줄은 양쪽 동일 `\| tr -d '\r'`) | 75d2407b · K3 |  |
| cysjavis-pack/bin/cys-dept | 21 | L3155-3174 | ours | create 예약 판독 = 우리 12 | 정책 §2-B |  |
| cysjavis-pack/bin/cys-dept | 22 | L3235-3242 | synth | 원작자 dept_stage probe + 우리 alive | dbg-D1 #1 | P(X-PROBE) |
| cysjavis-pack/bin/cys-dept | 23 | L3247-3263 | synth | 원작자 env -u 스폰 + _dept_spawn_pid + stage wait + 우리 boot_wait(_rr: NEW 만 원복) + sock_len_diag | dbg-D10 | P(X-WAIT) |
| cysjavis-pack/bin/cys-dept | 24 | L3305-3390 | synth | down = 원작자 down_dept 함수(토큰 경로 in-process 재사용) + 함수 본체에 우리 B11 울타리 이식(reg_count 판독 확인 뒤) | R4-N1 · B11 |  |
| cysjavis-pack/bin/cys-dept | 25 | L3431-3449 | synth | down-sock 꼬리 = 우리 목록 정리 보류(_rrc · A1-F3) + 원작자 reg_count 실패 전파(CEO 거짓 강등 방지) | A1-F3 · P1 |  |
| cysjavis-pack/bin/cys-dept | 26 | L3460-3469 | theirs | rotate 사전 게이트 = 원작자 `_reg_names=$(reg_names) \|\| exit $?`(우리 reg_names 가 12 를 내므로 같은 효과 + pipefail SIGPIPE 회피) | ① |  |
| cysjavis-pack/bin/cys-dept | 27 | L3568-3587 | ours | reap 스냅샷 판독 = 우리 12 | 정책 §2-B |  |
| cysjavis-pack/bin/cys-dept | 28 | L3592-3598 | ours | reap 스냅샷 실패 = 우리 11·12 전달 | A1-F3 codex 4R |  |
| cysjavis-pack/bin/cys-dept | 29 | L3600-3609 | synth | 우리 HOLD 계수 nh + 원작자 reap 부팅 유예(_reap_resg) | R2F-PK S4 m3 · A1-F3 |  |
| cysjavis-pack/bin/cys-dept | 30 | L3630-3639 | ours | reap IDLE 회수 보류 계수(우리) — 판독 실패는 말미 reg_count 가 12 로 낸다 | A1-F3 codex 4R |  |
| cysjavis-pack/bin/cys-dept | 31 | L3658-3665 | synth | 원작자 reg_count 실패 전파 + 우리 HOLD 출력 | P1 · A1-F3 |  |
| cysjavis-pack/bin/cys-dept | (덩어리 밖) | 전역 | synth | 원작자 쪽 판독 실패 전파 rc 10 → 우리 12 로 재번호(dept_creation_failed·rot_reg_degraded·reg_set_field·allocate/create/rotate/cwd 호출부·down-sock 역인덱스 판독기·usage 범례·주석) | 정책 §2-B(우리 번호) |  |
| cysjavis-pack/bin/cys-dept | (덩어리 밖) | reg_restamp | synth | 원작자 새 쓰기 도우미의 윈 잠금 실패 `pass` → LOCKFAIL(무잠금 쓰기 금지 · 재기록만 생략) 오버레이 | A1-F3 · e116d48b |  |
| cysjavis-pack/bin/cys-dept | (덩어리 밖) | launch_dept | drop | 원작자 dept_ready_knob_warn 호출 1줄 제거(우리 boot_wait 는 그 노브를 안 읽어 경고가 거짓이 됨) | X-WAIT | P(X-WAIT) |
| cysjavis-pack/bin/javis_org.py | 1 | L703-734 | synth | destroy 격리 중단 rc = 우리 울타리(9·10·11) + 원작자(2·7) + 판독 실패 우리 12(원작자 10) · self-test 목 rc 10→12 | B11 · P6 R1 |  |
| cysjavis-pack/bin/javis_state_snapshot.py | 1 | L133-139 | theirs | utf-8-sig(BOM 허용 · 우리 utf-8 의 상위집합) | K2-03 |  |
| cysjavis-pack/bin/javis_event.py | 1 | L94-100 | theirs | utf-8-sig | K2-03 |  |
| cysjavis-pack/bin/javis_cycle_verifier.py | 1 | L218-224 | ours | run() 창 정책 = 우리 **NOWIN(test_nowin_periodic_spawns) ↔ 원작자 _CAPTURE_SPAWN_KW={}(H-WIN-16) | 9501dd66 · U5 | P(X-NOWIN) |
| cysjavis-pack/bin/javis_checklist.py | 1 | L48-57 | synth | 원작자 shell=isinstance(cmd,str) + 우리 **NOWIN | 6411cdd4 | P(X-NOWIN) |
| cysjavis-pack/bin/javis_cycle_autopilot.py | 1 | L214-220 | ours | **NOWIN(값은 원작자 _CAPTURE_SPAWN_KW 와 같음) | 9501dd66 · U5 | P(X-NOWIN) |
| cysjavis-pack/bin/javis_cycle_autopilot.py | 2 | L497-504 | ours | run_wakeup **NOWIN | 9501dd66 · U5 | P(X-NOWIN) |
| cysjavis-pack/bin/javis_bootstrap.py | 1 | L1327-1338 | ours | DEPT_FB 문구 = 우리(CAP 제거 반영 · 원작자 문구는 cys team-propose 를 가리킴 — 받지 않는 기계) | 정책 §2-B 팀 승인 |  |
| cysjavis-pack/bin/javis_bootstrap.py | 2 | L2542-2669 | theirs | 자원 게이트 재확인 = 원작자 U11(fleet_cpu·벽시계·master 결속 재확인) — 우리 load_ratio 재측정은 합병 게이트에 load hard 가 없어(None) 사문 | fe974e5c·61caca7f ↔ U11 |  |
| cysjavis-pack/bin/javis_bootstrap.py | 3 | L2681-2827 | theirs | U11 _resource_wait·_fleet_hard_prescription·_post_wait_master_check·_run_resource_gate | U11 |  |
| cysjavis-pack/bin/javis_bootstrap.py | 4 | L2829-2853 | theirs | U11 재확인 진입(우리 재측정 루프 버림) | U11 |  |
| cysjavis-pack/bin/javis_formation.py | 1 | L155-161 | synth | 원작자 env=env + 우리 **NOWIN | R2 · 9501dd66 | P(X-NOWIN) |
| cysjavis-pack/bin/javis_formation.py | 2 | L914-986 | synth | 원작자 유계 write-lock·_replace_state_obj + 우리 _write_state(revive=) | WP6 · v116-pack P1′ |  |
| cysjavis-pack/bin/javis_formation.py | 3 | L1025-1033 | synth | 우리 revive 기록(원작자 원자 교체로 tmp 줄 제거) | v116-pack P1′ |  |
| cysjavis-pack/bin/javis_formation.py | 4 | L2013-2021 | synth | 우리 _surface(detail=완결 본문) + 원작자 _onboard_notify(무장된 팀만) | A2 · f043c942 |  |
| cysjavis-pack/bin/javis_formation.py | 5 | L2109-2127 | synth | 우리 _surface(detail) + 원작자 갱신 주석 | A2 |  |
| cysjavis-pack/bin/javis_formation.py | 6 | L2518-2526 | union | 우리 NO_AUTOSTART env + 원작자 onboard_arm | v116-pack P1 · 0.14.42 |  |
| cysjavis-pack/bin/javis_formation.py | (덩어리 밖) | _cys_bytes | synth | 원작자 새 스폰 1곳에 **NOWIN 오버레이(우리 시험 test_nowin_periodic_spawns) | X-NOWIN | P(X-NOWIN) |
| cysjavis-pack/bin/javis_preflight.py | 1 | L713-726 | union | 훅 timeout 표: 우리 3행 + 원작자 role-capability-gate 15s | injection-slim T3 · WP-3 A |  |
| cysjavis-pack/bin/javis_preflight.py | 2 | L1653-1659 | synth | Preflight(wire_only=…, only=…) 둘 다 | dbg-D2 R12 · U4 C2 |  |
| cysjavis-pack/bin/javis_preflight.py | 3 | L5163-5177 | synth | 원작자 능력 게이트 상태 문구 + 우리 8종 훅 목록 | WP-3 A · injection-slim |  |
| cysjavis-pack/bin/javis_preflight.py | 4 | L7417-7430 | union | run() 배선: 우리 C82.core-injection·C83.recap-default + 원작자 C82.gate-corpus-drift·C83.lane-guard-tripped(번호 충돌 — 전체 id 는 접미가 달라 공존) | T5 · v115 B2 · WP-1 H-2 | P(X-CNUM) |
| cysjavis-pack/bin/javis_preflight.py | 5 | L10987-11036 | union | 우리 wire_seat + 원작자 _only_usage_exit | dbg-D2 R12 · U4 |  |
| cysjavis-pack/bin/javis_preflight.py | 6 | L11044-11054 | union | --wire-seat + --seed-trust 가로채기 | R12 · WP-2 |  |
| cysjavis-pack/bin/javis_phoenix.py | 1 | L939-1049 | synth | 우리 _operator_token_for + 원작자 _decode_captured·_run_capture_progress·_CYS_STALL_S · cys(owner=None) | v115 A1 · F1·W4 |  |
| cysjavis-pack/bin/javis_phoenix.py | 2 | L1056-1074 | synth | 우리 owner 토큰 부착(호출부 키워드 대신 `reinject` 동사로 판정 — 원작자 검체 고정 서명 보호) + 원작자 무출력 상한 실행기 | v115 A1 · F1·W4 | P(X-OWNER) |
| cysjavis-pack/bin/javis_phoenix.py | 3 | L1701-1707 | theirs | utf-8-sig | K2-03 |  |
| cysjavis-pack/bin/javis_phoenix.py | 4 | L2155-2355 | synth | 원작자 R3-2 단위 비례 상한 함수군 + spawn_production(cwd=우리, units·hang_suspected=원작자) | 정책 §2-A R3-2 · 1R#2 |  |
| cysjavis-pack/bin/javis_phoenix.py | 5 | L2359-2391 | synth | 우리 --cwd 인자 + 원작자 예산·하트비트·무출력 상한(우리 고정 90s 버림) | 정책 §2-A R3-2 |  |
| cysjavis-pack/bin/javis_phoenix.py | 6 | L2827-2838 | theirs | stage_reinject kind= 증거(owner 는 cys() 가 동사로 판정) | F-1 R1 · v115 A1 |  |
| cysjavis-pack/bin/javis_phoenix.py | 7 | L2858-2873 | synth | G2 docstring = 원작자 U8 P0-M2 + 우리 ③ 추가분(기록 ACK 줄·owner·팩 하한) | ③ · U8 P0-M2 |  |
| cysjavis-pack/bin/javis_phoenix.py | 8 | L2876-2888 | theirs | G2 = 원작자 인자 순서·classify_reinject_result=="ack"(우리 「(ACK 기록 · 」 줄 수용은 정규식 통합으로 오버레이) | 정책 §2-A ③ · 6a090055 |  |
| cysjavis-pack/bin/javis_phoenix.py | 9 | L2915-2924 | synth | 원작자 lease 이름 일반화(P10) + 우리 encoding=utf-8 | P10 |  |
| cysjavis-pack/bin/javis_phoenix.py | 10 | L3282-3318 | union | 원작자 F-1 저널 이관 → 우리 R4-2 세대 재스폰 상한(BREAKER_OPEN) | F-1 R1 · R4-2 |  |
| cysjavis-pack/bin/javis_phoenix.py | 11 | L3429-3461 | synth | 원작자 F-1 스폰 전 재고·_restore_units_now + spawn_production(cwd=restore_cwd, units, hang_suspected) | F-1 · R3-2 · 1R#2 |  |
| cysjavis-pack/bin/javis_phoenix.py | 12 | L3476-3486 | union | 우리 A4 정착 재관측 루프 → 원작자 _units_view=live2 | v115 A4 · R3-2 |  |
| cysjavis-pack/bin/javis_phoenix.py | 13 | L3624-3630 | union | 우리 force_fresh 해제 + 원작자 fresh_reason=poison | A3 · F-1 |  |
| cysjavis-pack/bin/javis_phoenix.py | 14 | L3663-3843 | synth | 원작자 F-1 재검증 pass 루프 + 우리 I-4 ACK 핑 관문(루프 안) + g2 의 not _no_ping · F-1 fresh 예상 역할은 I-4 관문 제외 | F-1 R2 · I-4 | P(X-I4F1) |
| cysjavis-pack/bin/javis_phoenix.py | 15 | L3868-3925 | synth | 원작자 legacy_verify_outcome·재관측 continue + 우리 A3 ps 축(에이전트 부재면 fresh 경로) | R3b · cysr-102 A3 |  |
| cysjavis-pack/bin/javis_phoenix.py | 16 | L3996-4007 | synth | 우리 런 도중 묘비 고지 + 원작자 poison_roles 고지 | v116-pack · F-1 |  |
| cysjavis-pack/bin/javis_phoenix.py | 17 | L4036-4051 | union | 결과 JSON: 우리 liveness_unknown·tombstoned_mid_run + 원작자 fresh_* 키 | R4-4 · v116 · F-1 |  |
| cysjavis-pack/bin/javis_phoenix.py | (덩어리 밖) | _REINJECT_ACK_LINE_RE | synth | 같은 이름 두 정의 → 원작자 분류기 자리 하나로 · 정규식 = 우리 판(수신)\|(기록 · ) — 나중 재정의 제거 | ③ Fable F5 |  |
| cysjavis-pack/bin/tests/test_phoenix_g2_ack_only.py | AA | 전체 | synth | 추가·추가: 원작자 판(up/v0.14.43 U8 P0-M2 · main) + 우리 판(1.1.7 ③ · ours_suite 함수로 감쌈) 둘 다 실행 · 우리 M2 뮤턴트 대상 = 원작자 인자 순서로 적응 · 실측 28/28 + 우리 판 OK | 6a090055 · cysr-117-impl-input |  |
| cysjavis-pack/bin/tests/test_dept_name_guard.py | 1 | L37-43 | union | import shutil + re·shlex | — |  |
| cysjavis-pack/bin/tests/test_dept_name_guard.py | 2 | L373-1104 | union | 우리 WinLock·RegistryUnreadable 등 + 원작자 RotatePostKill(J4)·J5PyShim · 원작자 쪽 rc 10→12·문면 단언 우리 문면으로 적응 | 정책 §2-B | P(X-J4: RotatePostKillRegistryCorruption 은 우리 동작에서 적색 예상) |
| cysjavis-pack/bin/tests/test_dept_name_guard.py | 3 | L1308-1895 | union | 우리 DaemonLeakGuard + 원작자 SockLenDiag·CrlfHygiene·PostSpawnRegistryFailure·RegistryBom · rc 10→12 · 문면 · census(reg_read_py 셸 변수 풀기·바이트 판독+decode utf-8-sig 인정) · rmw-pin reg_init 여러 줄 정규식 적응 | 정책 §2-B |  |
| cysjavis-pack/bin/tests/run_bootstrap_health.py | 1 | L13863-13895 | synth | 원작자 R3SH-3(pane_notice_line 몸통을 잼) + 우리 두 형상(직접 주입/seat_inject_guarded 단일 입구) 판정 | f2fd9782 · R3SH-3 |  |
| cysjavis-pack/bin/tests/run_bootstrap_health.py | 2 | L13998-14008 | synth | 원작자 _absent + 우리 gov 인자 | U-23 |  |
| cysjavis-pack/bin/tests/test_pyseal_census.py | 1 | L247-271 | union | 등재 3건(우리 encoding_smoke + 원작자 autopilot·javis_role) | SEAL-1 |  |
| cysjavis-pack/hooks/session-start.sh | 1 | L49-85 | synth | 우리 HOOK_IN 1회 판독 + 원작자 R3-1 source\|transcript 파싱·clear 재핀·WIN-1 \r(입력은 HOOK_IN) | cysr 1.0.2 B2 · R3-1 · d99c6f92 |  |
| cysjavis-pack/hooks/session-start.sh | 2 | L526-569 | synth | 원작자 U18 작업 폴더 막힘 고지 + U4 C2 지침 판독 게이트 수용 · 원작자 각성 머리/미리보기 안내/cat 은 우리 9,000자 조립이 대신 | 정책 §2-B 훅 9,000자 |  |
| cysjavis-pack/hooks/session-start.sh | 3 | L807-861 | synth | 우리 HEAD/BULK 9,000자 상한+목차 + 원작자 U16 TEAM.md 블록(함수화 · 상한 안에서만 · BEGIN/END 사이 = 계산만) | 정책 §2-B · U16 |  |
| cysjavis-pack/hooks/_lib.sh | 1 | L137-270 | union | 우리 CLT 스텁 배제 함수군 + 원작자 U15 주석 | cysr-102-pack-c · U15 | P(X-CLT) |
| cysjavis-pack/hooks/_lib.sh | 2 | L274-281 | synth | CYS_PY 사전값: 우리 cys_is_clt_stub ∧ 원작자 _cys_py_preset_is_shim 둘 다 거름 | X-CLT | P(X-CLT) |
| cysjavis-pack/hooks/_lib.sh | 3 | L287-298 | synth | 우리 맥 해소(번들→PATH 스캔) + 원작자 _cys_py_avoid_shim(이중 안전) | X-CLT | P(X-CLT) |
| cysjavis-pack/hooks/save-state.sh | 1 | L14-19 | union | 원작자 cys_lane_redirect 먼저(exec 전환) → 우리 cys_hook_timing | v113 Q1 · lane |  |
| cysjavis-pack/hooks/reflect-scan.sh | 1 | L13-18 | union | 동일(to) | v113 Q1 · lane |  |
| cysjavis-pack/hooks/grill-stop.sh | 1 | L15-20 | union | 동일(to) | v113 Q1 · lane |  |
| cysjavis-pack/hooks/guard.sh | 1 | L70-96 | ours | cys_resolve_pybin(우리 공용 해소기 · 스텁 배제) ↔ 원작자 U15 인라인 루프 | cysr-102-pack-c · U15 | P(X-CLT) |
| cysjavis-pack/hooks/actprobe-kill-gate.sh | 1 | L26-51 | ours | 동일 | cysr-102-pack-c · U15 | P(X-CLT) |
| cysjavis-pack/directives/MASTER_DIRECTIVE.md | 1 | L718-724 | ours | 우리 문면(--verifier worker · exit 82) — 원작자는 같은 문장을 고침 | master 22:28 지침 규칙 |  |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 1 | L348-358 | synth | 우리 문장 그대로 + 원작자가 새로 더한 4행(검증자 금지 두 이유 · ② feed reply 없음) | master 22:28 지침 규칙 |  |
| cysjavis-pack/memory/feedback_autonomous-pilot-mandate.md | 1 | L22-32 | synth | 우리 문장 + 원작자 추가 4행 | master 22:28 지침 규칙 |  |
| scripts/ceo_template_header.md | 1 | L48-58 | ours | 머리글 = 우리 판 전체(덩어리 + 덩어리 밖 원작자 팀 토큰 문면 4곳 — team-propose bash 블록·「CSO 위임 금지」 항·--team-token 예외·합성 서문 꼬리 — 되돌림) | 정책 §2-B 팀 토큰 받지 않음 | P(X-TEAMDOC) |
| cysjavis-pack/directives/CEO_TEMPLATE.md | 1 | L48-58 | ours | 생성물 — scripts/gen_ceo_template.py 재합성(머리글 우리 판 + 병합된 MASTER) | gen_ceo_template |  |
| cysjavis-pack/directives/CEO_TEMPLATE.md | 2 | L808-814 | ours | 생성물 — MASTER 덩어리 1 과 같은 판정(재합성으로 일치) | gen_ceo_template |  |
| cysjavis-pack/directives/MASTER_DIRECTIVE.md | 결정반영①② | merged L409-451 | drop | §4-A 「팀 만들기 — 말로 부탁(cys team-propose · --team-token)」 + kind=team-create-request 항(21,248B) = 휴면 기능 절 제외 · P-TEAMDOC 해소(머리글 우리 판과 일치) | master#36f48cf7 ② D-TEAM |  |
| cysjavis-pack/directives/MASTER_DIRECTIVE.md | 결정반영① | H2 L367-370 | theirs | queue.starved 기본 600s·remedy= 전달·자동 조치 금지 — 근거 src/bin/cysd/schedule.rs:2269 · governance.rs:5748 · alert_route.rs:1487 | master#36f48cf7 ① 편입 |  |
| cysjavis-pack/directives/MASTER_DIRECTIVE.md | 결정반영① | H4·H5 L538-540·L668-677 | theirs | stopped_stagnation 종결·백로그 인계 — 근거 cysjavis-pack/bin/javis_orchestra.py:56·60(round-status stop_reason) | master#36f48cf7 ① 편입 |  |
| cysjavis-pack/directives/MASTER_DIRECTIVE.md | 결정반영① | H6·H7·H8 L699-727 | theirs | cycle-agent --fire·--detach(rc 87/88/89) 절차 — 근거 src/bin/cys.rs:262(fire)·268(detach)·1113(EXIT_CYCLE_SKIPPED=87)·1527(EXIT_CYCLE_DETACHED=89) | master#36f48cf7 ① 편입 |  |
| cysjavis-pack/directives/MASTER_DIRECTIVE.md | 결정반영① | H9 L732-738 | theirs | cycle-agent 저장 기준선(호출 시점 재기준선 · 손실0 단언 금지) — clear 가드 v3 문면 | master#36f48cf7 ① 편입 |  |
| cysjavis-pack/directives/MASTER_DIRECTIVE.md | 결정반영① | H1 L365 | theirs | 「수신 시 해당」→「수신 시」 원작자 문면(H2 와 한 문장) | master#36f48cf7 ① |  |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 편입 | H1-H5 핵심·H6·H7·H10-H17·H19·H21-H24 | theirs | 경보 inbox 라우팅(alert_route.rs) · 능력 게이트 §1-1(hooks/role-capability-gate.sh · tool_calls BUDGET_WARN=1500 :820) · §1-2 승인 주체 고장(approval sign/--require-ttl = cys.rs:2389 · master_unstable) · §1-2 ⑦ 사이클 경계·--fire/--detach(cys.rs:262·268·1527) · queue.starved(governance.rs:5748) | master#36f48cf7 ① 편입 |  |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 제외1 | H5 개정근거 HTML 주석 3줄 | drop | 출처 메모뿐(동작 0) · −389B · 우선순위 최하 | master#36f48cf7 ① 래칫 | P(핀 영향 없음) |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 제외2 | H13 「큐 항목 TTL 인지」 | drop | 「데몬이 지원하면」 조건부 서술 · −396B | master#36f48cf7 ① 래칫 | P(핀 TTL 인지 적색) |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 제외3 | H5 「구판 프로젝트 메모리보다 이 지침이 이긴다」 | drop | 문서 간 우선 해설 · −491B | master#36f48cf7 ① 래칫 | P(핀 적색) |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 제외4 | H5 「전이 상태 고지」 | drop | 부분 배포 전이 해설 · −468B | master#36f48cf7 ① 래칫 | P(핀 적색) |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 제외5 | H5 「구 데몬 폴백」 | drop | 구 데몬(alert_route 키 부재) 폴백 — 병합본 데몬엔 해당 없음 · −980B | master#36f48cf7 ① 래칫 | P(핀 적색) |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 제외6 | H8 「탐지의 한계(각성 경로 0)」 | ours | 한계 해설 단락 제외 · 우리 2줄 문면 복원 · −962B | master#36f48cf7 ① 래칫 | P(핀 적색) |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 제외7 | H9 카운터 상세 | ours | ISO 시각 상세 제외 · 우리 1줄 복원 · −615B | master#36f48cf7 ① 래칫 | P(핀 적색) |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 제외8 | H18 3-2 머리 | ours | 머리·한계 문장 제외 · 우리 3줄 복원 · −311B | master#36f48cf7 ① 래칫 | P |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① 제외9 | H20 「선조치의 범위」 | drop | §1-1 규칙 재진술 · −384B | master#36f48cf7 ① 래칫 | P(핀 선조치 범위 적색) |
| cysjavis-pack/directives/CEO_TEMPLATE.md | 결정반영① | 전체 | ours | gen_ceo_template.py 재합성(머리글 우리 판 + 선별된 MASTER) · 95,167B | master#36f48cf7 ① |  |
| cysjavis-pack/bin/cys-dept | 결정반영② 확인 | L2093·L2343·L2788·L3106 | — | T2 코드 존치 · 우리 경로 미실행 확인: dept-by-chat 집행 = javis_org.py:829 `cys-dept create <키>`(카탈로그 · --team-token 아님) → team_token_gate(:2343) 미진입 · _CYS_TT_* 는 진입부 unset(:2093) → _cys_detach_ok 거짓 · formation onboard 무장은 allocate --team-spec-b64 만(:2788 4번째 인자 · create 는 :3106 3인자 호출) | master#36f48cf7 ② |  |
| cysjavis-pack/bin/javis_formation.py | 결정반영② 확인 | L2461-2504 | — | --onboard-spec-b64 없으면 onboard_arm 미호출(우리 경로는 넘기지 않음) | master#36f48cf7 ② |  |
| cysjavis-pack/bin/javis_bootstrap.py | 결정반영② 확인 | L1319·1888·2065·3307 | — | `cys team-propose` 는 안내 문구 4곳뿐(실행 0) — 사용자 노출은 남음(코드 존치 지시) | master#36f48cf7 ② | P(노출 잔존) |
| cysjavis-pack/bin/tests/test_role_authority.py | 결정반영③ | L621 | synth | destroy 반파괴 핀의 판독 실패 rc 10 → 12(우리 번호) | master#36f48cf7 ③ P-EXIT12 |  |
| cysjavis-pack/bin/tests/test_role_authority.py | 결정반영③ | L638 | synth | `if rc_in == 10` → 12(종료 완료 미확인 문구 단언 갈래) | master#36f48cf7 ③ P-EXIT12 |  |
| cysjavis-pack/bin/tests/test_role_authority_shell.py | 결정반영③ 확인 | L504(K8) | — | 판독 실패 rc 기대 없음(K8 은 rc=2 이름 검증) — 재번호 대상 0 | master#36f48cf7 ③ |  |
| cysjavis-pack/bin/tests/(팩 전체) | 결정반영③ 확인 | git grep | — | 나머지 10 기대는 다른 뜻: 부트 session_error exit 10(test_bootstrap_chain·run_bootstrap_health:1851·golden) · 닫기 울타리 「닫는 중」 10(test_dept_b11_lock:94·97) — 재번호하지 않음 | master#36f48cf7 ③ |  |
| cysjavis-pack/directives/MASTER_DIRECTIVE.md | 결정반영① clear v3 | L675 | synth | 우리 문장의 cycle-agent 호출 예에 `--fire <경보의 fire=> --detach` 삽입(clear 가드 v3 — cys.rs:262·268 · 시험 ClearGuardFireWiring.test_every_role_call_example_carries_fire) | master#36f48cf7 ① |  |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 결정반영① clear v3 | L312 | theirs | 호출 예 = 원작자 문면(`… --fire <경보의 fire=> --detach`로 주인) · 우리 괄호(검증자 금지·exit 82)는 바로 뒤 원작자 추가 단락과 중복이라 뺌(시험 음성 대조 앵커 일치) | master#36f48cf7 ① |  |
| cysjavis-pack/memory/feedback_autonomous-pilot-mandate.md | 결정반영① clear v3 | L22 | synth | 같은 호출 예에 --fire/--detach 삽입(지침과 일치) | master#36f48cf7 ① |  |

### ledger-ci (30행)

| .github/workflows/release.yml | 1 | L158-187 | union | 우리 build_id 스탬프 스텝 + 원작자 python 3.12 고정 스텝 — 서로 다른 기능 | cysr-brand-version · 원작자 E-4② |
|---|---|---|---|---|---|
| .github/workflows/release.yml | 2 | L462-530 | union | 등재 설명 주석 블록 양쪽 이력 합침 | B-9 · v115r4-dbg |
| .github/workflows/release.yml | 3 | L545-580 | union | build 잡 팩 루프 시험 목록 합집합(test_phoenix_g2_ack_only 는 위 문맥에 이미 있어 원작자 쪽 중복 제거) | A2-20 · 원작자 등재 커밋군 |
| .github/workflows/release.yml | 4 | L1270-1330 | synth | PACK_MIN_BINARY 값 = 우리 '1.1.7' 유지 + 원작자 0.14.31→0.14.42 상향 근거를 1.1.8 편입 주석으로 요약(R2) | be2be68d · be1a6035 · f7ab5a1f |
| .github/workflows/release.yml | 5 | L1334-1363 | union | pack-artifacts 잡 build_id 스탬프 + python 3.12 고정 | cysr-brand-version · E-4② |
| .github/workflows/release.yml | 6 | L1465-1533 | union | 등재 설명 주석 블록 합침 | B-9 |
| .github/workflows/release.yml | 7 | L1548-1583 | union | pack-artifacts 팩 루프 시험 목록 합집합(#3 과 같은 목록 · g2 중복 제거) | A2-20 |
| .github/workflows/ci-branch.yml | 1 | L860-949 | union | 등재 설명 주석 블록 합침(R3-2·R3-4·R3-1 추가 등재 설명 포함) | B-9 |
| .github/workflows/ci-branch.yml | 2 | L964-996 | union | mac 팩 루프 시험 목록 합집합(sandbox 줄은 원래 ci-branch 에 없음 · g2 중복 제거) | A2-20 |
| .github/workflows/ci-branch.yml | 3 | L1019-1045 | synth | 우리 CYS_TMP 격리 detect self-test 줄 + 원작자 사이클 autopilot·verifier self-test 루프 | 57c7345a · WP-D |
| .github/workflows/ci-branch.yml | 4 | L1681-1840 | synth | 우리 NSIS 템플릿 대조 스텝 + 원작자 새 잡 ubuntu-pack-suite·ui-check — 우분투 루프는 release pack-artifacts 루프를 문면 그대로 복사(우리 CYS_TMP·EXIT trap 포함 · 토큰 108종 일치 실측) | A2-20(22fad7c4) · C4-⑧ · 1.1.7 E3·E2 |
| .github/workflows/pack-release.yml | 1 | L73-103 | synth | PACK_MIN_BINARY_OVERRIDE 우리 '1.1.7' 유지 + 원작자 상향 이력 요약 주석(R2) | be2be68d · be1a6035 |
| .github/workflows/pack-release.yml | 2 | L244-312 | union | 등재 설명 주석 합침 | B-9 |
| .github/workflows/pack-release.yml | 3 | L328-363 | union | pack-only 팩 루프 목록 합집합(release 와 같은 목록) | A2-20 |
| scripts/secret-scan.sh | 1 | L14-50 | synth | 우리 배치화·⑥ 머리 주석 유지 + 원작자 U4 C4-⑤ 주석 + 편입 합성 설명 | D-12 · e8bde9ad · bc41de4b · 7e363c59 |
| scripts/secret-scan.sh | 2 | L53-68 | synth | 원작자 저장소 가드 문형 + 우리 grep_rc_ok + 임시 폴더 tmp·list_file 을 여기로 당김 | D-12 · 7e363c59 |
| scripts/secret-scan.sh | 3 | L83-93 | theirs | 목록을 list_file 로 받기(git 실패 = exit 2 · staged 의 git diff 실패 틈을 닫는 원작자 잔여) | 7e363c59 |
| scripts/secret-scan.sh | 4 | L98-105 | ours | --all 0건 exit 2 문구(효과 동일) | bc41de4b |
| scripts/secret-scan.sh | 5 | L140-177 | ours | 규칙 변수·배치 구조 유지(윈 300s 타임아웃 수리) · tmp 생성은 #2 로 이동 | e8bde9ad · v110-secret-scan |
| scripts/secret-scan.sh | 6 | L179-189 | ours | 대상 목록 확정(배치) | e8bde9ad |
| scripts/secret-scan.sh | 7 | L191-217 | synth | 우리 부재 = exit 2 유지 + 원작자 910cef8d 이메일 파일 단위 면제 제거를 배치 구조에 이식(email_allow_re 사용 제거) | 910cef8d · bc41de4b |
| scripts/secret-scan.sh | 8 | L219-369 | synth | 우리 배치 스캔 유지 · 이메일 규칙도 scan_files 전체 · 원작자 「--all 인데 연 파일 0건 = exit 2」 이식 · 원작자 파일 루프·꼬리(grep_errs·missing_args) 제거 | 910cef8d · 7e363c59 · e8bde9ad |
| scripts/verify-release-remote.py | 1 | L400-414 | synth | 원작자 parse_args 반환 언팩 + 우리 cysr_ 자산 이름 | a36c1118 · 1aa247ab |
| scripts/verify-release-remote.py | 2 | L499-513 | synth | 원작자 sums_coverage_verdict 채택 + VERSIONED_ASSETS·OLD_VERSIONED_RE·자기시험 픽스처를 cysr_(옛 cys_ 도 구버전) 로 · ⑥ⓓ' 시험 1건 추가 — ⑥ⓖ 는 우리 발행 형상과 어긋나 적색(R3) | 870d2f7d · 1aa247ab |
| scripts/release-gate-gatekeeper.sh | 1 | L144-156 | union | 우리 LANE·SKIP_N + 원작자 GKTOOL_ONLY | 2f7c1556 · 6a9e3353 |
| scripts/release-gate-gatekeeper.sh | 2 | L966-980 | synth | 레인 줄 + GKTOOL_AXIS 요약 + 우리 SKIP 계수 판정 줄 · 별도로 ⑨ 를 자체서명 레인에서 skipped(계수)로 만드는 분기 추가(덩어리 밖 · 의미 충돌 해소) | 2f7c1556 · 6a9e3353 |
| scripts/tests/test_version_sot_mutation.py | 1 | L268-277 | synth | 요약 줄에 추출 실패 E1·E2 수 반영 · 원작자 E 블록의 run() 호출을 우리 시그니처(벤더 원격 인자)로 맞춤(덩어리 밖) | f696bf74 · 0bbdc28b |
| scripts/tests/test_release_postprocess_gate.py | 1 | L725-1012 | union | 우리 LaneAxisTests + 원작자 GktoolAxisTests · test_50·53 을 ⑨ 자체서명 SKIP(SKIP=3)에 맞게 갱신 | 2f7c1556 · 6a9e3353 |
| docs/RELEASE.md | 1 | L50-56 | ours | §0-A 2단계 현행 하한 리터럴 = 1.1.7(우리 두 레인 값과 동일) · 원작자 신설 절은 덩어리 밖 자동 병합으로 들어옴 + 우리 포크 주석 3곳 추가(⑨ SKIP · ⑥ 13종 · 공증 DMG 항목) | f7ab5a1f |
| USER-MANUAL.md | 1 | L167-178 | synth | 원작자 상단바 아이콘화(정책 2-B 수용) + 우리 동작(창 만들기 상단 없음 · 창 닫기 확인 1회 · 「업데이트」 · (끝남)) | B-12 상단바 아이콘화 |
| USER-MANUAL.md | 2 | L675-681 | theirs | 파일 트리 = 폴더 아이콘(아이콘화 수용과 일관) | B-12 |

### ledger-lead (6행)

| ui/src/folderaccess.ts | - | L18 | synth | 브랜드 오버레이: PRIVACY_APP_NAME "cys"→"cysr"(원작자 시험이 productName 과 같기를 단언 · 우리 productName=cysr) | X8 |  |
|---|---|---|---|---|---|---|
| ui/src/updatenotice.ts | - | L120 | synth | 원작자 설치 안내 URL(cysinsight) → 우리 설치 사이트 | X2·정책 §0 |  |
| ui/src/updatenotice.test.ts | - | L72 | synth | 원작자 시험 상수를 우리 URL 로 조정(삭제 아님 · 단언 뜻 불변) | X2 |  |
| src/lib.rs | - | ~L906 | drop | 우리 ④ DRAFT_GATE_TAG·MSG_DRAFT_GATE_CANCEL_KEY 중복 정의 삭제(원작자 D-12 판 유지 · 정책 2-A · 빌드 E0428) | H4 |  |
| src/factory_reset.rs | - | L3681·L3771 | synth | 우리 시험의 ResetRoots 초기화에 원작자 새 필드 claude_config_dir·defaults_domain=None(빌드 E0063) | D-03 |  |
| src/factory_reset.rs | - | ~L1745 | synth | defaults delete 를 #[cfg(target_os=macos)] 로 가둠(원작자 spawn_policy 점검 · 원작자 판도 같은 자리 cfg) | 수리 |  |
| src-tauri/src/feedback.rs | - | capture_into | synth | screencapture 함수를 OS 로 가름(맥 = 종전 · 그 밖 = capture_unsupported) · 원작자 spawn_policy 점검 | 수리 |  |

### ledger-lead-extra (16행)

| 파일 | 원 덩어리 | 원 줄 범위 | 판정 | 근거 | 관련 | 잠정 |
|---|---|---|---|---|---|---|
| ui/src/wsreconcile.ts | AA 3 | 전체 | ours | 추가·추가 같은 이름 다른 내용 — 우리 wsreconcile(1.1.7 재구현) 유지 · 병합 커밋 blob = v1.1.7 blob(실측) | JT 동등 · 리드 |  |
| ui/src/wsreconcile.test.ts | AA 2 | 전체 | ours | 위와 짝 · blob = v1.1.7(실측) | 리드 |  |
| ui/src/feedback.ts | AA | 전체 | ours | 우리 2단계 피드백 본체 유지 · 원작자 U6 판은 수리 1차에서 feedback_u6.ts 로 휴면 복원(X17 ⓐ) · blob = v1.1.7(실측) | X17 · T2 |  |
| ui/src/feedback.test.ts | AA | 전체 | ours | 위와 짝 · 원작자 시험은 feedback_u6.test.ts 로 복원(21 초록) · blob = v1.1.7(실측) | X17 |  |
| ui/src/droppoint.ts | AA | 전체 | theirs | 원작자 ftdrop 경로 판정 채택(우리 동등 구현 폐기) · blob = 원작자 v0.14.43(실측) | C-01 · JT 원작자 채택 |  |
| ui/src/droppoint.test.ts | AA 2 | 전체 | theirs | 위와 짝 · blob = 원작자(실측) | C-01 |  |
| ui/src/restartplan.ts | AA | 전체 | theirs | 원작자 planRestartInject 채택(우리 restartRetryPlan 폐기) · blob = 원작자(실측) — 재시도 오버레이는 judge 대기 K07 | K07 | P |
| ui/src/restartplan.test.ts | AA | 전체 | theirs | 위와 짝 · blob = 원작자(실측) | K07 | P |
| Cargo.toml | UU 1 | 의존·주석 | synth | 우리 판 기준 + 원작자 portable-pty 주석 정정(CREATE_NO_WINDOW 금지 근거) · 판 번호 우리 1.1.7 유지(TK-G) | TK-G |  |
| Cargo.lock | UU 2 | — | synth | 우리 판 기준 · Cargo.toml 의존 정리 결과(−46줄) · 판 번호 우리 | TK-G |  |
| src-tauri/Cargo.toml | UU 1 | version | ours | 판 번호 우리 1.1.7 유지(판번 = 통합 리드 TK-G) · blob = v1.1.7(실측) | TK-G |  |
| src-tauri/tauri.conf.json | UU 1 | version·productName | ours | 판 번호·productName(cysr) 우리 유지 · blob = v1.1.7(실측) | TK-G · X8 |  |
| ui/package.json | UU 1 | version | ours | 판 번호 우리 · blob = v1.1.7(실측) | TK-G |  |
| dist-win/cys.wxs | UU 1 | Version | ours | 판 번호 우리 · blob = v1.1.7(실측) | TK-G |  |
| dist-win/cys-x64.wxs | UU 1 | Version | ours | 판 번호 우리 · blob = v1.1.7(실측) | TK-G |  |
| .gitignore | UU 1 | 꼬리 | synth | 합집합 — 원작자 .d16-*.sock 추가 + 우리 cysjavis-pack/state/*.jsonl(09-17 감사) 유지 | 리드 |  |

### ledger-compile (17행)

| 파일 | 줄(수정 후) | 무엇을 | 왜 | 근거 |
|---|---|---|---|---|
| src/bin/cys.rs | 15997 | settle_gate_pending 4인자 → 6인자(followup, directive_held 추가) | 본체 · 원작자 0.14.31 C6 가 6인자로 바꿨고 우리 v112-restore ① 「입력창 미실측 보류」 호출부만 옛 4인자 · 의미 불변 | 같은 함수 안 원작자 보류 호출 2곳 cys.rs:16024·16048(현 16031·16055)이 같은 상황(미주입 보류)에 followup, directive_held 를 넘긴다 |
| src/bin/cysd/accounts.rs | 1554 | note_oauth 의 record_rate_snapshot 에 source="oauth" 추가 | 본체 · 원작자 analytics.rs:92 가 9번째 인자 source 를 추가 · 우리 OAuth 프로브(2-B 사이드바 커스텀) 호출부만 옛 8인자 | 같은 함수가 v.source="oauth"·note_alert_input(...,"oauth") 를 쓴다(accounts.rs:1527·1533) · 원작자 statusline 경로 accounts.rs:770 은 source 를 그대로 넘김 · 우리 오버레이 U3(OAuth 관측 → 경보 입력)와 일치(feeds_alerts("oauth")=참) |
| src/bin/cysd/accounts.rs | 6840,6843 | 우리 시험 seed_known_drops_antigravity_snapshot_rows 의 record_rate_snapshot 에 "statusline" 추가 | 우리 시험 · 새 인자 · 시험 뜻(antigravity 행 복원 차단)과 무관 | 원작자 시험 analytics.rs:1975-1978 이 같은 자리에 "statusline" 을 넘긴다 |
| src/bin/cysd/schedule.rs | 1736 | approval::load_records() → approval::try_load_records() (.map_err 유지) | 본체 · 원작자가 load_records 를 Vec 반환(실패=빈 목록)으로 바꿔 우리 .map_err 가 깨짐 · 우리 1.1.7 「판독 실패를 사유와 함께 거부」 의미 보존 | approval.rs:800(load_records = try_load_records().unwrap_or_default) · approval.rs:837 try_load_records(Result) = 원작자 API · 둘 다 fail-closed · 부수: approval::load_records 가 본체 미사용 경고(오류 아님) |
| src/bin/cysd/approval.rs | 1123,1144 | 우리 골든 서명 시험 레코드 2개에 expires_at: None 추가 | 우리 시험 · 원작자 ApprovalRecord.expires_at 새 필드 · None = 무기한 = 종전 계약 | signing_payload 에 expires_at 가 들어가지 않음(grep 0) → 골든 바이트·서명 불변 |
| src/bin/cysd/governance.rs | 24246 | QUEUE_ENV_LOCK 이중 import 중 우리 `use super::PACK_DIR_ENV_LOCK as QUEUE_ENV_LOCK` 제거 · 원작자 `use super::PACK_ENV_LOCK as QUEUE_ENV_LOCK` 유지 | E0252 · 두 이름이 같은 락 | governance.rs:12557 `pub(crate) use PACK_ENV_LOCK as PACK_DIR_ENV_LOCK`(별칭) → 효과 동일 |
| src/bin/cysd/governance.rs | 19045-19047,19079-19080,19121-19122,19358-19359,24880-24889,24902-24903,24952-24963 | 우리 D7·alt 시험 11호출 deliver_queued 3인자 → 4인자(&mut stale) · 같은 함수 안 let 에 stale 맵 추가(연속 틱이 같은 맵 공유) | 우리 시험 · 원작자 0.14.31 quiesce_stale 인자 추가 | 원작자 검체 공용 틱 governance.rs:30866 `deliver_queued(daemon,&mut depth,&mut starve,&mut stale)` 과 같은 꼴 · 연속 호출은 틱 간 상태 유지가 운영과 같음(governance.rs:204 운영 호출도 맵 하나를 틱마다 넘김) |
| src/bin/cysd/governance.rs | 29315-29527(18곳) | 우리 accept_v116 S1~S4 시험 deliver_head_locked 6인자 → 8인자(None, None) | 우리 시험 · 원작자 expect_output_gen·recheck 인자 추가 · None = 세대·재판정 검사 없음 = 이 시험들이 재는 것(옛 기동 줄 폐기)과 무관 | 원작자 시험 governance.rs:23477·24503·24570 등이 같은 자리에 None, None |
| src/bin/cysd/watch_wake.rs | 557 | 우리 시험 delivery_is_noted_so_the_submit_probe_runs deliver_head_locked 6→8인자(None, None) | 우리 시험 · 위와 같음 | 위와 같음 |
| src/bin/cysd/governance.rs | 22912 | 원작자 시험 wp5_r1_no_marker_quiet_fallback_refuses_pending_approval FeedItem 에 wait: false 추가 | 원작자 시험 · 우리 오버레이 필드 FeedItem.wait(v112-wake ⑥) 누락 · false = 발사 후 망각 = 원작자 판 의미 | state.rs:3100 `#[serde(default)] pub wait: bool` (기본 false · up/v0.14.43 state.rs 에 wait 없음) |
| src/bin/cysd/handlers.rs | 28451 | 원작자 시험 c_ceo_injection_sanitized_before_ledger FeedItem 에 wait: false | 원작자 시험 · 우리 오버레이 필드 | 위와 같음 |
| src/bin/cysd/handlers.rs | 28512 | 원작자 시험 도우미 h4_item FeedItem 에 wait: false | 원작자 시험 · 우리 오버레이 필드 | 위와 같음 |
| src/bin/cysd/return_absorb_tests.rs | 771,945 | 원작자 시험 도우미 push_daemon_approval·push_gate_feed FeedItem 에 wait: false | 원작자 시험 · 우리 오버레이 필드 | 위와 같음 |
| src/bin/cysd/handlers.rs | 23161 | 원작자 시험 fatal_fix_restored_seat_still_feeds_account_alerts_from_its_own_profile create_surface_with_env 에 agent=None 추가 | 원작자 시험 · 우리 오버레이 인자(S3-D2 · 2-B topology S3 보존) · None = 「종전 동작 완전 동일」 | state.rs:7044-7051 인자 주석 · state.rs:7027 create_surface 가 None 을 넘김 |
| src/bin/cysd/handlers.rs | 30957,30991,31220,31593,31759 | 원작자 시험(reclaim_seat·reclaim_caller·reclaim_auto_uses_daemon_known_axes_not_reported_ones·reported_cwd_cannot_widen_past_the_live_cwd·caller_env_that_redirects_the_account_dir_clears_the_trust_flag) create_surface_with_env 에 agent=None | 원작자 시험 · 우리 오버레이 인자 | 위와 같음 |
| src/bin/cysd/state.rs | 12192-12197 | 우리 시험 d7_parked_cap_split_evicts_oldest_on_both_axes QueueEntry 에 원작자 TTL 6필드 기본값 추가 | 우리 시험(D7 주차 상한) · 원작자 0.14.31 WP-5 M 새 필드 | 원작자 시험 도우미 state.rs:12145 w2b_entry 와 같은 기본값(None·0.0·None·None·false·false) |
| src/bin/cysd/usage.rs | 4430-4666(이동) | 원작자 0.14.42 RC2·fatal-fix agy 시험 묶음(agy_lsof_args… ~ fatal_fix_agy_collector_points…, 함수 13개(시험 10 · 도우미 3) 236줄)을 우리 mod acceptance_v116 끝에서 원작자 mod tests 끝으로 옮김(내용 무변경) | 병합 해소가 원작자 mod tests 의 꼬리를 우리 모듈 안에 붙여 `use super::*` 가 없어 E0425/E0422/E0433·json! 미정의 27건 | up/v0.14.43 usage.rs:3844-4081 = mod tests(3194) 안 · mod tests 는 `use super::*`(usage.rs:3637) |

## ② 수리 1차(17f40a9c·501edcf2·414dc2d4·642a10af·e7e2092f·c0a66a3b)

### ledger-fix-ui (37행)

| 파일 | 줄 | 무엇을 | 왜 | K#/결정 | 적색 시험 |
|---|---|---|---|---|---|
| ui/src/feedback_u6.ts | (신규) | 원작자 0.14.43 feedback.ts 원문을 별도 이름으로(머리 주석 2줄만 추가) | feedbackmodal.ts(원작자 U6 휴면 작성 창)가 원작자 API 전제 — 우리 feedback.ts 와 이름 충돌 → tsc 13 | X17 ⓐ · master#9d77552e | tsc 13건(feedbackmodal.ts) |
| ui/src/feedbackmodal.ts | 31 | import "./feedback" → "./feedback_u6" | 위와 같음 | X17 ⓐ | tsc 13건 |
| ui/src/feedback_u6.test.ts | (신규) | 원작자 0.14.43 feedback.test.ts 원문 복원(import 대상만 ./feedback_u6) — 21 pass | 병합에서 원작자 feedback.test.ts 가 우리 판에 통째로 덮여 사라짐(원작자 시험 삭제 0 계약 복원) | X17 · 삭제 0 | (사라졌던 시험 21) |
| ui/src/style.css | :root 8 · #restore-brief 1203 | --z-restore-brief:900 토큰 신설 · #restore-brief z-index 900 → var(--z-restore-brief)(값 동일 · 화면 무변화) | 원작자 stacking.test 「문서 루트 층은 전부 토큰 참조」 — 우리 복원 카드만 숫자 리터럴 | 원작자 층서 수용(style.css #4 synth) | stacking.test 「문서 루트 층…토큰 참조다」 |
| ui/src/style.css | #toasts 머리 주석 | 옛 계약 문장(「확인 창·CC·팔레트보다 아래 그대로」)을 현행 사실로 정정(주석만) | 병합 뒤 거짓 주석 | 원작자 층서 수용 | — |
| ui/src/alertlayer.test.ts(우리) | 14-20 · 34-41 | z() 가 var(--z-*) 를 :root 값으로 해석 · 둘째 it 「확인 창·CC 보다 아래」→ 원작자 회피 계약(확인 창 밖 창이 떠 있으면 --z-toast-under-modal < modal · > cc-panel) 단언 | 병합에서 #toasts 가 원작자 토큰(1800)을 받아 숫자 정규식이 NaN · 옛 층 계약은 원작자 09-23 수리로 대체됨 — 목적(조작부 가로채기 금지)은 유지 | 원작자 층서 수용 · team-confirm T1 | alertlayer 2 |
| ui/src/sendfailwiring.test.ts(원작자) | 71 | catch 토스트 핀을 우리 D4#14 꼴(사람 말 본문 + 원문 String(e) 를 5번째 raw 인자)로 | 우리 injectRawToPane 가 사람 말 + 원문 칸 — 원작자 옛 문자열 핀 | X13 = 우리 | sendfailwiring N7 ② |
| ui/src/starvednotice.test.ts(원작자) | 745-750 | 조기 return·제거 앵커를 우리 줄(if (!src.ok) { · removeDeadPane(Number(sid), src.socket);)로 재조준 + 앵커 존재 단언 추가 | 원작자 isClosingSid·sock 앵커는 원작자 배치(seatlayout) 배선 — 우리 eventSock 판정(cys-117-exitedpane-b1) | X1 = 우리 | starvednotice surface.exited |
| ui/src/permtoast.test.ts(우리) | 1-4 · 15-31 | 리스너 문구 핀 → showPermWarning→permWarningToast 배선 + PRIVACY_APP_NAME="cysr" + 3 폴더 본문에 「cysr」(「cys」 아님) 행동 단언 | 병합에서 리스너 문구가 원작자 folderaccess.permWarningToast 로 이동(「앱을 재시작하세요」 문장은 원작자 문안에 없음 — X8 합성 결과) | X8 합성 | permtoast |
| ui/src/wsusage-null.test.ts(우리) | 4 · 55-70 | ccAggRate 문자열 핀 → aggSeatRates 위임 핀 + null/undefined 창 행동 단언 | ccAggRate 가 원작자 aggSeatRates 로 교체 | X11 = 원작자 | wsusage-null 55행 |
| ui/src/deptprogresswiring.test.ts(원작자) | ~303 | setInterval 총수 10 → 11 + 우리 feedback_flush 타이머 존재 핀 | 우리 피드백 2단계 보관함 재시도 타이머 1곳(cys-feedback-menu) — 팀원 안내 타이머 아님(정규식 핀은 그대로) | X3(GU 수용) · 우리 피드백 | setInterval 1개뿐 |
| ui/src/deptprogresswiring.test.ts(원작자) | ~335 · ~340 | 루프 안 앵커 pruneHoleUntil() → 우리 socketRows 캐시 갱신 줄 · invoke 수 1 → 2(우리 자리표 회수 close_surface 1곳 핀) | 원작자 U2 구멍 정리 없음(X1) · 우리 v111-restore ③ 회수 | X1 | B1 완료 판정 입력 |
| ui/src/deptprogresswiring.test.ts(원작자) | ~1215 | collectSids 구멍(음수 sid) 단언 → 우리 배치 기준(구멍 없음 · 칸 수 그대로 · main.ts 에 음수 sid 생성 0) | 원작자 U2 역할 칸 구멍은 우리 균등 배치에 없음 | X1 = 우리(master#36f48cf7 ④) | collectSids 구멍 |
| ui/src/deptprogresswiring.test.ts(원작자) | S4 B1 setup | refreshPaneTitles 실제 본문 대역에 우리 자유 변수 22개 무동작 대역 추가(B17 스윕·M7①·rememberRoles·자리표 회수·표시번호·본부 판정·사이드바 사용량) + rt.titleEl style/dataset | 원인: 원작자 대역이 원작자 판 함수 본문 전제 → 우리 판 본문의 이름(exitedSweepArm 등)이 ReferenceError(시험 머리 주석이 「새 외부 이름 → 대역 갱신」을 지시) | X1 · X3(GU 수용) | S4 B1 7건 |
| ui/src/deptprogresswiring.test.ts(원작자) | S4 m3 setup | 실제 본문 목록에 우리 setToastRaw 추가 | 우리 stickyToast 가 D4#14 원문 칸(setToastRaw)을 부름 → ReferenceError | D4#14 우리 | S4 m3 4건 |
| ui/src/deptprogresswiring.test.ts(원작자) | ~2549 | stickyToast 핀 recordAlarm(…, id) → recordAlarm(…, id, raw) | 우리 D4#14 원문 칸이 이력에도 실림(같은 id 합침 목적 동일) | D4#14 우리 | S4 n1 「지속 알림이 하는 일」 |
| ui/src/updateplan.ts | 69-75 | 「없음」 배지 ✓ → 0 복원(주석 교체) | 원작자 U9 ✓ 가 자동 병합으로 우리 updateplan.ts 에 들어옴 — X2 = 우리 업데이트 UX | X2 = 우리 | updatebutton 「같은 판…배지 0」 |
| ui/src/updateplan.test.ts(공유 · 원작자 변경분) | 59-64 | 원작자가 고친 ✓ 단언을 우리 0 으로 되돌림(이름·주석 갱신) | 위 복원과 짝(원작자 U9 계약 변경 미수용) | X2 | (복원 뒤 적색 예방) |
| ui/index.html | 29 | Update 배지 초기 마크업 class="badge" hidden>! → class="badge ok" hidden>…(숨김 상태라 화면 무변화 · 보일 때는 updatePlan/paintRestartPending 이 글자·ok 를 항상 다시 칠함) | 원작자 hiddenpair 「확인 전 초기 마크업은 중립」 — 숨김 짝 규칙이 깨져도 ! 가 보이지 않게(방어) | X2(화면 무변화) | hiddenpair Update 배지 초기 마크업 |
| ui/src/probefail.test.ts(원작자) | 472-478 | .cc-alert-badge.unknown·[hidden] 단언 → 배지 규칙 0 + .cc-alert-row.unknown 존재 | 헤더 경보 배지는 박사님 09-15 결정으로 없음(우리 brandbadge.test 가 .cc-alert-badge 부재 핀) — 정면 모순 | X7 | probefail style.css |
| ui/src/style.css | 918-930 | 원작자 U6 사이드바 단추 규칙 4개 셀렉터를 #wsbar-feedback-slot #btn-feedback 로 좁힘 | ★실결함: 같은 id 의 우리 상단바 「피드백」 단추에 width calc(100% - 16px)·margin·display:flex 가 걸려 상단바 폭으로 늘어남(HEAD 실측 = 맨 #btn-feedback 셀렉터 존재) | X17 휴면 · v116-feedback-top | feedbacktop 「크기를 줄이는 규칙 0」 |
| ui/src/feedbacktop.test.ts(우리) | 37-43 | 원작자 슬롯 안 규칙은 제외하고 상단바에 닿는 규칙만 셈 + 슬롯이 우리 DOM 에 없음 + 맨 #btn-feedback 셀렉터 0(회귀 핀 — HEAD 에서 적색 확인) | 위 수리와 짝 | X17 | feedbacktop |
| ui/src/feedbackwiring.test.ts(원작자) | 14 · 209 | pureSrc = ./feedback_u6.ts(원작자 U6 순수 모듈) | X17 별도 이름 | X17 | — |
| ui/src/feedbackwiring.test.ts(원작자) | ② 드롭 가드 | 첫 문장 가드 단언 → 우리 배선(드롭 목적지 = paneAtPointStrict elementFromPoint→.pane · 덮개 .modal-overlay fixed inset 0 · 우리 피드백 창도 그 덮개) | 우리 피드백 창은 드롭 첨부가 없고 덮개가 pane 을 가려 오배달이 구조적으로 없음(같은 목적) | X17 · U6 휴면 | ② pane 드롭 리스너 첫 줄 가드 |
| ui/src/feedbackwiring.test.ts(원작자) | ⑥ 3건 | feedback.rs 를 우리 본체 / u6_local_bundle 로 갈라 — 우리 명령 7 전부 등재 · u6 명령 미등재(T2) · 창 정책: 우리 = spawn_policy 또는 맥 전용 screencapture · u6 = no_console(원 단언) · 전송 없음 = u6 에만(우리는 2단계 업로드가 설계) | 병합에서 원작자 feedback.rs 가 u6_local_bundle 하위 모듈로 들어감(T2) — 원 단언이 우리 2단계 curl·우리 명령까지 셈 | T2 · X17 | ⑥ 3건 |
| ui/src/autoarrange.test.ts(우리) | 737-751 | replaceNode 허용 목록에 awaitHandoffAck 추가 + 실재 핀 | 전출 확인 대기가 원작자 WP-4 새 함수로 분리 | X12 = 원작자 | autoarrange 737행 |
| ui/src/seatsig.test.ts(원작자) | 476-480 | 부서 머리 작업중 계수 단언 taskSeatIsWorking → 우리 nodeWorking(…) + 두 판정 혼재 0 | 겹침 = 우리(appearance.nodeWorking) | X6 | seatsig CC Tasks·부서 머리 |
| ui/src/updatestate.test.ts(원작자) | 139 | silentToast 문구 「무중단 적용(재시작 없음)」→ 우리 updatePlan 문안 「재시작 없이 적용됩니다」 | 단언 목적 = 「종전 문구(updatePlan)」 — 우리 updatePlan 문안(D4#13) | X2 | updatestate 본체+팩 동시 |
| ui/src/updatenotice.test.ts(원작자) | ~472 확인 창 본문 핀 | 본문 조각을 우리 판(제목 「새 앱 v 설치」 · 맥 방법 절 · 설치 사이트 줄 · const tail = IS_MACOS)으로 · 윈도우 방법 절은 핀하지 않음(X2 사실 대조 대기) | 우리 설치 확인 창 유지(X2) + J2 덧붙임 식·if (!ok) return; 핀은 그대로 | X2 | 확인 창 본문 핀 |
| ui/src/updatenotice.test.ts(원작자) | makePrompt 대역(~731-860) | 실행 대역을 우리 판 promptBinaryPatch 자유 변수로(updateAvailable·checkForUpdate·IS_MACOS·installingUpdate·INSTALL_BUSY_*·restartPending*·app_version 조회) · notifyBinaryPatchBusy 동반 로드 제거 · 기준 본문 OUR_BODY/OUR_TITLE/OUR_FAIL_TOAST 추가(원작자 BASE_BODY/WIN_BODY 는 S3 note 14 검체용으로 보존) | 원인: 원작자 판 함수 전제(notifyBinaryPatchBusy 부재 → makePrompt 전체 적색 15) | X2 = 우리 + J2/WU 이식 | J2 4 · 거절 · 차단/본체없음 · 설치실패 · 표식 내림 · WU 4 |
| ui/src/updatenotice.test.ts(원작자) | WU 핀 2건(~1344 · ~1370) | catch 핀을 우리 판(cur = app_version 조회 · 사람 말 실패 토스트+원문 칸 · v = updateAvailable.version) · 자동 테스트 경로 문구 우리 D4#14 | 우리 판 문안(D4#14)·현재 버전 출처 | X2 · D4#14 | WU catch · 자동 테스트 경로 |
| ui/src/wswiring.test.ts(합본 · 원작자 D2) | ~889 | it.skip 해제(X16) — 우리 고지 방식(새 탭 미생성 sticky tomb-unknown 1 · 자동 launch 보류 = 루프 뒤 토스트 1회 「부서 N곳은 이번에 켜지 않았습니다」)으로 단언 · 목적(사유 1회·루프 안 0) 유지 | master K10/X16 「.skip 해제·우리 기준 수정」 | X16 | (skip 1 → 실행) |
| ui/src/wswiring.test.ts(합본 · 원작자 U2+U3) | ~1311-1460 | describe.skip 해제(X1) — 원작자 검체 29개를 1:1 로 두고 각 목적을 우리 formation autoArrange 배선으로 단언(arrangeWs 한 곳·역할 우선 입양·죽은 칸 제거 순서·effective 가드·백지 금지·규칙 한 곳) + 원작자 장치 20종(구멍·보류 기한·세대·수동 표식·markClosing 등) main.ts 부재 핀 | master#36f48cf7 ④ 「원작자 배치 시험은 우리 동작 기준으로 수정(삭제 금지)」 | X1 | (skip 29 → 실행) |
| ui/src/wswiring.test.ts(우리 ⓒ) | 447-460 | addDeptWorkspace 호출자 1 핀에서 휴면 runTeamProposalFlow 내부 호출 제외 + 그 함수 호출처 0 핀 | D-TEAM 휴면(코드 유지 · 배선 0) — 살아 있는 문은 launchDept 하나 그대로 | D-TEAM 휴면 | wswiring ⓒ addDeptWorkspace 호출자 |
| ui/src/starvednotice.ts | 62-75 · 머리 주석 | STARVED_LEGACY_CALM_PREFIXES 에 seat_unknown·seat_no_agent 추가(주석 7→9종) | 다른 갈래(governance.rs · 미커밋)가 데몬 REMEDY_WAIT_PREFIXES 에 우리 좌석 보류 2종을 wait 로 더함 → 소스를 읽는 어휘 핀이 적색(수리 도중 새로 생긴 적색) — 표는 데몬을 따라간다(시험 머리 규칙) | governance.rs C5 수리 연동 | starvednotice 데몬 어휘 핀 |
| ui/src/starvednotice.test.ts(원작자) | 179-181 | 접두 목록 정확히 9 → 11(우리 2 포함) | 위와 짝 | 같음 | starvednotice 접두 목록 9개 |
| ui/src/usagewiring.test.ts(원작자) | CC 계정 표 핀 5건 | kpiCandidates 호출식(as any[]) · 행 클래스(.dead 선행 + 흐림 조건 동일) · 클릭 위임에 renderUsageBar 부재(X9) · 숨기기/보이기 툴팁 우리 문구(사이드바 언급 0 · X9) · usageHidden TDZ 기준을 우리 첫 최상위 사용(ccAcctHost)으로 | CC 계정 표 = 원작자 UI1 + 우리 합성(stale 게이지) · X9 사이드바는 숨김 무관 | X9 · 합성 | UI1 KPI 후보 · 행 흐림 · 클릭 위임 · R1F-UB 툴팁 2 · TDZ |

### ledger-fix-rustb (32행)

| 파일 | 줄 | 무엇을 | 왜 | K#/결정 | 적색 시험 |
|---|---|---|---|---|---|
| src/released_directive_hashes.rs · cysjavis-pack/directives/RELEASED_MASTER_DIRECTIVE.sha256 | 전체(생성물) | scripts/gen_released_directive_hashes.py 재실행 — CEO +5(현 임베드 1 + 신규 태그 v0.14.38~43 계열) −1(b3fb5895) · MASTER +5 −1(d9cee685) | 지침이 병합으로 바뀌어 현 임베드 해시가 표에 없음. 빠진 2개는 어느 발행 태그에도 없는 4680f0db 시점 작업트리 해시(v1.1.7 태그 바이트 = 2dd58…/a13c… 는 표에 잔존) — 생성기 정의(태그+현 작업트리)대로. 표 의미(정책 §2-B RefreshUser = 발행 바이트 등가) 무변경 · --check OK | P-BYTES 종속(팩 서브가 MASTER/CEO 를 더 고치면 재실행 필요) | pack::tests::released_tables_cover_current_embed |
| src/pack.rs | d04 시험(≈6250) | 단언 조정: 미수정 옛 vendor agents.json = RefreshUser 갱신 + .bak-<판번> 보존 · 원작자 「보존+.new+new-pending」 단언은 사용자 수정본 시나리오로 옮겨 그대로 검사 · 마커 승격 단언 유지 | 우리 D1 RefreshUser(정책 §2-B)가 미수정 user-owned 를 갱신함 — 원작자 단언은 우리 판에서 사용자 수정본에만 성립. 이 시험이 PACK_ENV_LOCK 을 쥔 채 panic → 52 연쇄 PoisonError 의 뿌리 | §2-B RefreshUser | pack::tests::d04_… (+ 연쇄 52) |
| src/lib.rs | RAW_COMMAND_NEW_FROZEN | 동결 계수 갱신 feedback.rs 2→6 · src-tauri main.rs 37→38 · cycle_jobs.rs 신규 1 (각 지점 창 정책/ cfg 확인 주석) | 원작자 편입분: U6 휴면 하위 모듈(opener no_console · Mail open macOS cfg) · open_privacy_settings(macOS cfg)·reg.exe(no_console) · cycle_jobs start(spawn_policy Attached) | T2 · K12류 편입 | spawn_policy_tests::raw_command_new_census_is_frozen |
| src/lib.rs | daemon_state_dir_tests mod | 우리 시험 mod 위치만 이동(daemon_state_dir_for 뒤 → claude_effort_tests 앞) · 내용 무변경 | 원작자 소스 핀이 lib.rs 를 첫 cfg(test) 속성에서 잘라 프로덕션 구간으로 보는데 우리 mod(622)가 spawn_env_pairs(1993) 앞에 있어 「소실」 오판 | 원작자 시험 무변경 | macos_devtools::tests::spawn_env_pairs_wires_seventh_verdict_through_single_source_source_pin |
| src/lib.rs | pub mod dormant(≈2671)·dormant_switch_tests | 휴면 스위치 모듈 신설 — team_flow·agy_lane 2개(기본 꺼짐 · 운영 = 데몬/CLI env CYS_ENABLE_TEAM_FLOW=1·CYS_ENABLE_AGY_LANE=1 · 프로세스 수명 고정) + 시험 이음매 force_for_thread(스레드 한정 덮기 · 가드 drop 복원) + 거부 코드 team_flow_dormant | judge 집행 조건 ① 「D-TEAM 휴면 = 데몬 스위치 1개(기본 off)」 · C4 agy 갈래 휴면 「같은 방식」 · 스레드 한정이라 우리 usage-noagy 회귀 시험(꺼짐)과 원작자 agy 시험(켬)이 병렬로 공존 | D-TEAM · C4 · [master#cd9e534c] | (신규) dormant_switch_tests |
| src/bin/cys.rs | Command::TeamPropose/TeamToken · FeedAction::Reply.team_token · 디스패치 · team_flow_dormant_refusal | 원작자 동사·인자를 **숨김(hide)** 으로 재등록(파싱만) · 휴면 스위치 꺼짐이면 실행 거부(team-propose exit 3 · team-token / reply --team-token exit 1 · stdout {ok:false,code:team_flow_dormant}) · run_team_propose/run_team_token/team_token_outcome 의 dead_code 허용 제거 · feed_reply_carries_optional_team_token 의 cfg(any()) 컴파일 제외 해제(보이지 않는 삭제 원복) | master D-TEAM 휴면 = CLI 노출만 끊음(제거 아님) · 「제거」 해소를 「휴면」으로 되돌림 | D-TEAM · R8 · M1 | team_propose_tests::team_propose_subcommand_parses · team_token_cli_tests::team_token_subcommands_parse_and_stay_hidden (+ feed_reply_carries_optional_team_token 복원) |
| src/bin/cys.rs | team_flow_dormant_cli_tests(신규) | 숨김·꺼짐 거부·디스패치가 스위치를 보는지 핀 | 휴면 스위치 배선 회귀 방지 | D-TEAM | (신규) |
| src/bin/cysd/accounts.rs | fixed_resolution · 부트 복원 · apply_discovered · apply_agy_error | 원작자 0.14.43 agy 갈래(gemini/agy 귀속 · 스냅샷 복원 · 데이터 폴더 시드 · 오류 행 생성)를 휴면 스위치 agy_lane 켜짐일 때만 되살림 — 꺼짐 = usage-noagy(박사님 09-19) 그대로 | C4 「agy 갈래 휴면(cfg off · 삭제 아님)」 | C4 · U1 · K01/K02 | accounts::tests agy 7종(antigravity_observation… · agy_error_creates_row… · agy_error_annotates… · agy_statusline_becomes… · fatal_fix_alternating_agy… · fatal_fix_windows_past_their_reset… · seed_discovers… · source_error_is_exposed…) |
| src/bin/cysd/accounts.rs | 원작자 agy 시험 9개 머리 | `let _agy_on = force_for_thread(AgyLane, true)` 1줄씩 — 단언 무변경 | 원작자 시험은 시험 안에서 스위치를 켜고 원래 단언 그대로(삭제 0) | C4 | 위 + agy_error_without_any_agy_trace_creates_no_account_row |
| src/bin/cysd/accounts.rs | periodic_cmd_adapter_spawn_hides_console(우리) | 프로덕션 구간 경계를 첫 cfg(test) 속성 → `#[cfg(test)]\nmod tests {` 로 | 원작자 판이 프로덕션 구간에 cfg(test) 시험 이음매 fn 을 둬서 경계가 앞당겨짐(cmd 스폰 0개로 오판) | 병합 부작용 | accounts::tests::periodic_cmd_adapter_spawn_hides_console |
| src/bin/cysd/usage.rs | fatal_fix_agy_collector_points…(원작자) 머리 | agy 휴면 스위치 켬 1줄(current_thread 런타임 = 같은 스레드) | C4 | C4 | usage::tests::fatal_fix_agy_collector_points_to_the_statusline_where_rpc_cannot_work |
| src/bin/cysd/usage.rs | t2_grace_memo_per_file(우리) | 배선 핀의 프로덕션 경계를 줄머리 첫 cfg(test) 속성으로(들여쓴 함수 안 cfg(test) 블록 제외) | 원작자 판이 함수 본문 안(843·901)에 cfg(test) 블록을 둬 경계가 앞당겨짐 | 병합 부작용 | usage::tests::t2_grace_memo_per_file |
| src/bin/cysd/schedule.rs | BUILTIN_JOBS_VERSION 3→4 · builtin_jobs() ctx-relay-base 제거 · RETIRED_BUILTIN_JOBS·retire_builtin_jobs 신설 · apply_dept_lane_jobs(소급 추가) 제거 · ensure 배선 교체 | K49: 원작자 경보 라우터 채택 + 우리 javis_ctx_relay 중계 폐기(본부 마커 잡 · 부서 seed 잡 — 우리가 심은 바이트 그대로일 때만 걷음 · 운영자 편집 무접촉) · 버전 4(우리 3·원작자 2 보다 큼) | 두 소비자 공존 = 같은 넘김에 통보 2벌 | K49 · K66 | (목적) 이중 통보 차단 |
| src/bin/cysd/schedule.rs | v113_dept_lane_ctx_relay_backfill(우리) → k49_ctx_relay_jobs_are_retired_only_when_ours | 우리 시험 교체 — 버린 구현(부서 소급 추가)의 핀을 청소 핀으로 | K49 정책상 우리 구현 폐기(원장 근거 = 이 줄 + DECISION-TABLE-118 K49 행) | K49 | schedule::tests::v113_dept_lane_ctx_relay_backfill |
| src/bin/cysd/schedule.rs | builtin_jobs_ensure_idempotent_and_versioned(우리) | 계수 11→10 / 12→11 · ctx-relay-base 단언 → 부재 단언 · 버전 핀 3→4 | K49 | K49 | (연동) |
| src/bin/cysd/schedule.rs | 원작자 시험 4곳 `assert_eq!(BUILTIN_JOBS_VERSION, 2, …)` | 기대값 2 → 4(우리 판 값) · 단언 목적(이 변경이 전역 버전을 올리지 않았다) 유지 · 주석 | 우리 v3(v113) + K49 v4 가 원작자 v2 위에 있다 | K49 | merge_residue_tests::heartbeat_fix… · merge_residue_tests::migration_upgrades… · tests::alert_inbox_job… · tests::stored_legacy_push… |
| src/bin/cysd/schedule.rs | c8_push_counts_submit_tests::rig_cmd(원작자 고정물) | 좌석 seat_cache = Occupied 로 둠 | 우리 v115r3-d7 role_seat_hold 가 생성 직후 seat=Unknown 역할 좌석을 seat_unknown 으로 보류 — 고정물은 에이전트가 앉은 master 좌석 | 고정물 조정(H1 계열 규칙) | c8_push_clears_ghost_count_then_queue_tick_delivers_without_input_pending |
| src/bin/cysd/accounts.rs | display_rank·display_outranked 신설 · note_resolved 표시 갱신 조건 | 📌5 표시 우선순위 OAuth(3) > 좌석·rollout·어댑터(2) > 창 밖(1) > 예열(0) — 높은 순위가 신선(fresh_limit_secs)한 동안 낮은 순위는 표시 못 바꿈 · 경보 입력·스냅샷 영속 무관 | master 결정 📌5 「표시 우선순위 데몬 편입 = 1.1.8」 · 사이드바 패널·usage-accounts --json 게이트에 창 밖 값 혼입 차단 | 📌5 · K01 · K02 · REVIEW-D ⓒ | (신규) display_priority_oauth_over_seat_over_outside |
| src/bin/cysd/accounts.rs | alert_input_keeps_the_seat_value_when_an_outside_report_is_newer(원작자) | 「표시는 최신 승자(창 밖 5%)」 단언 → 「신선한 좌석 97% 유지」 · 경보 입력 단언 무변경 | 📌5 결정으로 표시 규칙이 바뀜(시험 목적 = 경보 입력 보존은 그대로) | 📌5 | (조정) |
| src/bin/cysd/analytics.rs | rate_series SQL · RATE_SERIES_EXCLUDED_SOURCE | 소진 예측 표본에서 statusline-outside 제외(NULL 구 행은 신뢰) | R1 codex F1·agy F4 필수 오버레이 — exhaust_at(master 토큰 게이트) 오염 차단 | 📌5 · K01 | (신규) rate_series_excludes_outside_reports_from_the_exhaust_sample |
| src/bin/cys.rs | enum DormantTeamCommand + Command::DormantTeam(#[command(flatten)]) | team-propose·team-token 을 별도 열거로 평탄화(최상위 동사 그대로 파싱) | Command 에 변형 2개를 직접 넣자 clap 조립 함수 프레임이 커져 시험 스레드(2MB)에서 rqfix_f10_queue_list_long_help… 가 stack overflow(SIGABRT · --bin cys 전체 중단) — 평탄화로 별도 프레임 | D-TEAM | queue_list_row_tests::rqfix_f10_… (회귀 차단) |
| src/bin/cys.rs | send_settle_budget_ms | `windows` 단락 제거(인자는 배선 핀용으로 유지) — 윈도우도 S21 정착 재시도 켬 | 📌1 master 결정 「원작자가 윈에서 끈 입력 안전장치를 윈에서도 켬」 | 📌1 · K18 | tests::s21_send_settle_budget(원작자 단언 「윈도우 0」 → 「윈도우도 기본 예산」 조정) |
| src/bin/cys.rs | send_guard_wait_retry·SEND_GUARD_RETRY_STEP_MS·send_guard_wait_secs 신설 · Command::Send 배선(direct 클로저 1곳 공유 · 윈도우 한정) | 우리 1.1.7 700ms·6초 타이핑 가드 대기 재시도를 **윈도우 한정** 안전망으로 복원(정착 재시도 뒤 · --queued 1회 전환 앞) | 📌1 「윈 실기 전까지 윈 한정 우리 6초 재시도 유지」 — 원작자 판 그대로면 윈은 재시도 0 + 정착 0 = 1.1.7 대비 후퇴 | 📌1 · C2 | (신규) tests::pin1_windows_guard_wait_retry_net · s21_send_settle_wired_on_first_direct_request_only(「직접 요청 한 곳」 핀 유지 확인) |
| src/bin/cys.rs | inject_text_on 의 ★D10·⑯ 주석 2개 | 인자 사이 → 호출 위로 이동(코드 무변경) | 원작자 소스 핀이 권위 붙여넣기 앞 6줄에서 authoritative_paste_settled( 를 찾는데 우리 주석 4줄이 끼어 10줄로 벌어짐 | 원작자 시험 무변경 | tests::authoritative_direct_pastes_all_go_through_the_settle_helper_source_pin |
| src/bin/cys.rs | u8_reinject_ack_only_never_submits_full_directive(우리) | phoenix 핀을 인자 인접(`"--check", "--ack-only"`) → 「reinject --check 호출 줄에 --ack-only」 로 | phoenix 가 원작자 U8 P0-M2 판(--ack-only 를 뒤에)으로 병합됨 — 목적(G2 확인 전용) 동일 | 병합 부작용 | tests::u8_reinject_ack_only_never_submits_full_directive |
| src/bin/cys.rs | v114_inject_carries_owner_token_only_when_given(우리) | 바늘 `with_owner_token(json!(` → `with_owner_token(` | 첫 직접 요청이 원작자 J3 inject_params_with_sender(json!(…)) 를 감싸 토큰 실림은 4곳 그대로(바늘만 어긋남) | P-OWNER | tests::v114_inject_carries_owner_token_only_when_given |
| src/bin/cys.rs | reinject_fake_daemon(원작자 고정물) | 가짜 소켓을 /tmp 바로 아래 → /tmp/.d16r-<pid>-<n>/s.sock(전용 폴더 · stop 때 제거) | 우리 1.1.7 ③ reinject 가드 기록이 소켓 부모(/tmp)/reinject-guard/7.json 에 남아 시험 간·실행 간 공유 → backoff skip 으로 핑 0회(실측 잔존 파일 확인) | 고정물 조정 | tests::u8_m2_run_reinject_busy_submits_zero_directives · u8_m2_run_reinject_drift_reinjects_once_then_idempotent_zero |
| src/bin/cys.rs | u10_dept_socket_launch_agent_composes_dept_pack_directive(원작자) 고정물 | MEMORY.md 고정물을 색인 항목 줄(`- [..](m.md)`) 형식으로 — 단언 무변경 | 우리 v116-seat F2 capped_memory_index 는 `- [` 항목 줄만 싣는다 | 고정물 조정 | u10_notice_lane::u10_dept_socket_launch_agent_composes_dept_pack_directive |
| src/bin/cys.rs | boot_agent_on_surface 기동 줄 json! | 우리 v116 X-4 표지 (cys::AGENT_LAUNCH_KEY) 를 같은 줄·authoritative 앞으로(키 순서만 · 값 무변경) | 원작자 소스 핀이 `"authoritative": true})` 로 끝나는 text 줄을 세는데 우리 표지 줄바꿈으로 3곳 중 1곳을 놓침(n=2) | 원작자 시험 무변경 | tests::authoritative_direct_pastes_all_go_through_the_settle_helper_source_pin |
| src/bin/cys.rs | Command::Send direct 클로저 | `\|settle_retry: bool\|` → `\|settle_retry\|`(타입 표기만 제거) | 원작자 배선 핀이 `\|settle_retry\|` 문자열을 찾는다 | 원작자 시험 무변경 | tests::fv1_settle_retry_flag_and_pause_stop |
| src/bin/cys.rs | u8_m2_run_reinject_drift_reinjects_once_then_idempotent_zero(원작자) 두 호출 사이 | reinject 가드 기록 파일만 지움(간격 경과 모사) · 단언 무변경 | 우리 1.1.7 ③ 가드 backoff 가 두 번째 호출의 핑 자체를 막음 — 이 검체의 목적은 원작자 멱등 키 소진 | 고정물 조정 | tests::u8_m2_run_reinject_drift_reinjects_once_then_idempotent_zero |
| (측정만) | tests::drain_verify_delivery_failed_on_wedge | 수정 없음 — 흔들림 확정: 같은 바이너리로 TMPDIR 길이만 바꾸면 초록(t2x·t3xx 2/2) · 격리 TMPDIR(…/s118/t)에선 적색 재현(3/3) | 가짜 wedge 화면이 지시문을 40열로 접는데, 체크포인트 경로 길이(TMPDIR·pid·판별자)에 따라 마커 꼬리 `-->` 의 `>` 가 줄머리에 오면 submit_probe 의 `\n> ` 프롬프트 앵커가 nonce 뒤에 잡혀 Submitted(→Timeout) 판정 | (보고) 실기 화면에서도 같은 위치 의존 오판 가능 — src/submit_probe.rs 범위 밖 | tests::drain_verify_delivery_failed_on_wedge |

### ledger-fix-daemon (46행)

| 파일 | 줄 | 무엇을 | 왜 | K#/결정 | 적색 시험 |
|---|---|---|---|---|---|
| state.rs | 1886 | WriteReq::SubmitGuarded 폐지 → SubmitAfterGap 에 refuse: Option<SafetyProbe> 필드(거부 모드) 추가 · writer arm: 간격 뒤 refuse 탐침 먼저(적중 = 바이트 0·기준점 0·재제출 기록 0) · S21 표식은 CR/LF 실은 요청만 소비 | 결정표 K17 권고(SubmitAfterGap 의 refuse 모드) · judge 집행 조건 ② · H7 틈 | K17·H7 | (새 단언) submit_guarded_rechecks_dialog_right_before_writing_cr |
| state.rs | 9770 | 우리 시험 submit_guarded_rechecks_dialog_right_before_writing_cr 를 refuse 모드로 재작성 + 간격 없는 C-u(종전 Data 경로) 바이트 0 · 재제출 기록 0 · S21 표식 소비 단언 추가(삭제 0) | 기능 동치 시험(승인 창 위 바이트 0) | K17 | - |
| state.rs | 9822~10090 | SubmitAfterGap 생성자 7곳에 refuse: None | 필드 추가 컴파일 | K17 | - |
| governance.rs | 6817 | 재제출 SubmitAfterGap 에 refuse: None | 필드 추가 컴파일(재제출은 거부 요청 아님) | K17 | - |
| handlers.rs | 2525 | approval_write_guard 반환형 Box<dyn Fn> → SafetyProbe(Arc) · Weak 잡기 · catch_unwind(패닉·소멸 = 거부) | refuse 모드에 싣기 · 보류 탐침과 같은 규율(writer 패닉 차단) | K17 | - |
| handlers.rs | 6990 | send_key: refuse_on_approval 이면 키·간격 무관 SubmitAfterGap{refuse:Some(approval_write_guard)} · 보류 탐침(cr_guard_ctx) 제외 · submit_handed 조건 = SubmitAfterGap ∧ CR/LF 포함(거부 모드 Return 도 S21 표식) | K17 이식 + H7 틈 닫기 | K17·H7 | - |
| handlers.rs | 16669 | u16_refuse_on_approval 소스 핀 갱신(SubmitGuarded → SubmitAfterGap 거부 모드 + refuse 탐침 실림 단언 추가) · write_req_name 의 SubmitGuarded 팔 제거 | 변형 폐지 반영(단언 목적 불변) | K17·C5 | - |
| send_settle_tests.rs | 1333 | 새 시험 k17_refuse_mode_return_raises_settle_marker_but_cancel_key_does_not(거부 모드 Return → S21 분리 보류 · C-u 는 표식 밖) | H7 틈 닫힘 증명 | K17·H7 | (신설) |
| handlers.rs | 16699 | 고정물 v7_send_human: 발신 pid 를 pane 무귀속 GUI pid(V7_GUI_PID=999998)로 — pane 귀속 pid 로 보내던 원작자 고정물 조정 | H1 ⓐ 우리 human_trusted 유지(GUI=pane 무귀속) · 원장 1줄 | H1·K19 | v7_probe_handler_observed_counts · v7_split_paste_handler_call_boundary_must_not_change_count |
| handlers.rs | 17531 | d12_gui_pure_insertion_…: 발신자를 GUI pid 로(고정물 조정) | H1 ⓐ · 원장 1줄 | H1 | d12_gui_pure_insertion_without_newline_passes_into_own_draft |
| handlers.rs | 17556 | d12_real_human_return_…: 발신자를 GUI pid 로(고정물 조정) + 음성 대조 새 시험 d12_pane_bound_forged_human_return_is_denied_on_human_draft | H1 ⓐ(F1 위조 차단 단언) | H1 | d12_real_human_return_without_machine_origin_passes |
| handlers.rs | 17603 | d12_authoritative_caller_cancel_key_exempt: 사람 초안 위 권위 C-u = 거부·보존(우리 F2)로 단언 조정 + 면제 실효를 타이핑 가드 축(기계 잔여)으로 단언 | H1 ⓐ(권위 면제도 사람 초안 못 덮음) · 원장 1줄 | H1 | d12_authoritative_caller_cancel_key_exempt |
| handlers.rs | 17663 | d12_detached_…: master 권위 C-u 도 사람 초안 거부로 조정 · role 판별 대조를 타이핑 가드 축(worker 거부/master 면제)으로 이동 | H1 ⓐ · 원장 1줄 | H1 | d12_detached_caller_authoritative_cancel_key_is_still_denied |
| handlers.rs | 18459 | d12_authoritative_caller_exempt: 사람 초안 위 권위 본문 = human_draft 거부·(11,11,11) 보존으로 조정 + 기계 잔여 위 면제 단언(비권위 거부 · 권위 (12,12,0)) | H1 ⓐ · 원장 1줄 | H1 | d12_authoritative_caller_exempt |
| handlers.rs | 19977 | h6_takeover_notice_skipped_on_pending_input: 원장 계수 1·2 단언 → 원장 0 + 화면(scrollback) 고지 유무로 조정(생략 규칙 단언 불변) | H2 잠정 수용(우리 display_notice 화면 출력) | H2 | h6_takeover_notice_skipped_on_pending_input |
| send_settle_tests.rs | 323 | clear_first_and_human_keys_are_not_held: 사람 키 발신을 좌석 자신 pid → None(GUI pane 무귀속) | H1 ⓐ · 원장 1줄 | H1 | clear_first_and_human_keys_are_not_held |
| return_absorb_tests.rs | 517 | a2_human_key_invalidates_owner_no_compensation: GUI 포커스 보고 발신을 좌석 pid → None(pane 무귀속) | H1 ⓐ · 원장 1줄 | H1 | a2_human_key_invalidates_owner_no_compensation |
| handlers.rs | 7222 | read_text arm 주석의 `.last_output` 문자열을 「출력 스탬프 `last_output`」로(병합 때 넣은 주석이 원작자 소스 핀에 걸림 · 코드 무변경) | 원작자 소스 핀 output_generation_bracket_source_pin 의 !contains(".last_output") | - | output_generation_bracket_source_pin |
| governance.rs | 12794 | v115 배선 핀 재표적: channels inject_master → inject_master_confirmed · boot_supervisor notify_no_spawn → pane_notice_line · schedule inject → inject_on(입구 대신 같은 술어 agent_seat_vacant_now+hold_for_vacant_seat 가 write_tx 앞인지) | 원작자 함수 분할(이름 변경) · SC2 합성 | SC2·A3 | v115_seat_inject_guarded_holds_vacant_agent_seat |
| governance.rs | 31527 | h7 허용목록: channels::inject_master_confirmed·boot_supervisor::pane_notice_line 제거(seat_inject_guarded 경유라 guard:None 생산자 아님) · 순서 핀 pane_notice_line(record_audited→write_tx) → pane_notice_line 이 seat_inject_guarded 경유 + seat_inject_guarded 안 record_audited→write_tx | H2 잠정 수용(원작자 시험 허용목록 2줄 조정) | H2 | h7_guard_none_producers_allowlist |
| governance.rs | 13819 | v113 핀 재표적 check_agent_death → check_agent_death_with_model(원작자 래퍼/본체 분할) | 함수 분할 | - | v113_root_agent_wired_into_seat_cache_and_liveness |
| governance.rs | 29458 | accept_v116_s1_prose…: 연속 배달 사이 last_queue_delivery_at=None(원작자 최소 간격 10초가 연속 호출을 막음 · 단언 불변) | 원작자 배달 최소 간격 · 같은 파일 관례 | K44 계열 | accept_v116_s1_prose_and_other_agent_delivered_on_claude_seat |
| governance.rs | 24620 | v116_deliver_stale_drop…: 강제 배달 직전 간격 기준점 비움(같은 사유) | 원작자 배달 최소 간격 | - | v116_deliver_stale_drop_keeps_prose_and_skips_tick_delivery |
| governance.rs | 30128 | q7_process_exit…: EOF 경로 보존소 단언을 restored_queue → 우리 parked_queues(role 키 · 순서) + queue.parked 발행으로 조정 | S1 잠정 해소 유지(셸 종료 = 우리 주차 · reap = 원작자) · master 「우리 결정 동작 단언」 | S1 | q7_process_exit_of_a_role_seat_parks_instead_of_dropping |
| governance.rs | 27828 | c5_force_deliver_refusal…ⓒ: 번호 선택지 창 거부 = ApprovalPending(우리 게이트 ⑦ 선행) + 유령 처방 미부착 단언으로 조정 | G1 OR 합성 잠정 유지 · 우리 결정 동작 단언 | G1 | c5_force_deliver_refusal_appends_ctrl_u_only_for_ghost_count |
| governance.rs | 21536 | wp5_force_deliver…②: 모달 거부 사유 PromptGate(modal) → ApprovalPending | G1 | G1 | wp5_force_deliver_respects_interval_and_prompt_gate |
| governance.rs | 20927 | wp5_counterexamples…: modal_pending 기대 행은 approval_pending 도 허용(틱 승인 축에 우리 화면 판독 OR · 거부 단언 불변) | G1 | G1 | wp5_counterexamples_all_refused |
| governance.rs | 9100 | REMEDY_WAIT_PREFIXES 7→9: seat_unknown·seat_no_agent(우리 SEAT 게이트 사유)를 wait 행에(종전 처방 표 밖 = unknown) — 운영 코드 | 병합판 처방 표 누락(시험이 적발) | v115r3-d7 합성 | c5_blocked_by_reasons_map_to_the_documented_rows |
| governance.rs | 27402 | c5_blocked_by…: 리터럴 가드를 우리 SEAT 사유 표(let label = match hold)까지 확장 — 표 리터럴 3종이 처방 표 행(≠unknown)에 드는지 · 변수 label 허용 | 원작자 리터럴 자리에 우리 SEAT 게이트 표 | v115r3-d7 | c5_blocked_by_reasons_map_to_the_documented_rows |
| governance.rs | 18523 | r1f census: governance clear_pending_input 1→3(우리 G2 사망 리셋 · note_line_submitted A3) 사유 주석 | G2 우리 의미+원작자 API · A3 | G2 | r1f_in_reset_path_census_source_pin |
| governance.rs | 1004 | G2 사망 리셋을 계수>0 일 때만(계수 0 이면 clear 가 잠정 Esc 면제 표식을 지워 원작자 틱 되돌리기 재료 소실 · 빈 프로세스 표 결손 틱) — 운영 코드 | G2 ↔ 원작자 R1F-IN 정합(우리 r2_agent_death_clears 시험 초록 유지) | G2 | r1f_in_tick_blank_process_table_with_unchanged_foreground_creates_no_phantom_count |
| governance.rs | 17740 | rqfix2_broad_only…: 전제 안정화 — 안쪽 sh argv 완전 일치까지 test_wait_seat_runs 대기(부하 시 path_helper 만 잡힘 · 단독 3/3 초록) | 부하 의존 플레이크(단언 무변경) | - | rqfix2_broad_only_descendant_never_raises_the_tick_flag |
| state.rs | 6113 | Daemon::new: 원작자 rename 보존이 성공하면 우리 ⑧ copy 실패로 선 쓰기 막음을 푼다(둘 다 실패면 막음 유지) — 운영 코드 | S2 「보존 2회 시도」 합성의 결함(rename 성공 뒤에도 실행 내내 WAL 미영속) | S2·K40 | unpreservable_queue_wal_blocks_persist_and_keeps_original_bytes |
| state.rs | 11849 | unpreservable_queue_wal…: 전제 복원 — WAL 디렉터리 0o555(두 보존 모두 실패) · CSO 수신 핀을 cys events 구독 줄 → alert_route::routable 로 재표적(원작자 CSO 지침 교체) | 원작자 rename 보존 · CSO 수신 경로 교체 | S2·K40 | (같은 시험 — 아직 적색: alert_route 허용 목록에 queue.persist_blocked 없음) |
| state.rs | 11812 | 새 짝 시험 s2_unreadable_wal_moved_aside_by_rename_unblocks_persist(rename 보존 성공 → 막음 해제 · 보존 사본 바이트 동일 · 새 WAL 영속) | S2 합성 증명 | S2 | (신설) |
| delivery.rs | 2814 | f1_unregistered_text…: 최장 행 길이 고정(583) → 실측 문턱 ≥583(원작자가 CEO_TEMPLATE 에 절 추가 · 최장 829) | P-BYTES(팩 선별은 팩 갈래) · 단언 목적 불변 | P-BYTES | f1_unregistered_text_keeps_substring_detection |
| d6_probe_tests.rs | 206 | d6_1_true_alarm_inside_boundaries: 경계 안쪽 관측 나이 23h → 원작자 B3 상한(CYS_ACCOUNT_ALERT_STALE_SECS 기본 1800) −60s | U2 원작자 경보 로직 채택 | U2 | d6_1_true_alarm_inside_boundaries_still_alerts |
| boot_supervisor.rs | 6214 | h5_clean_pane_bytes_identical: 기준 문안을 우리 v112-wake ③ 문안(병합 유지판)으로 | 우리 문안 유지 · 단언 목적(H5 가 바이트 불변) 동일 | - | h5_clean_pane_bytes_identical |
| approval.rs | 1520 | recovered_key…: 소스 핀 touch_best_match(우리) → approval.check 팔의 best_match_index_at + records.get_mut(*matched_idx)(원작자 같은 보장) | A1·H3 원작자 판 운영 경로 | A1·H3 | recovered_key_never_approves_or_resigns_old_records |
| approval.rs | 1566 | save_records_tmp_name…: 운영부 경계 앵커 mod tests → pub(crate) mod tests(원작자가 검체 모듈 공개) | 앵커 조정 | - | save_records_tmp_name_is_unique_per_call |
| handlers.rs | 4987 | team.token.* RPC: cys::dormant::team_flow_enabled() 거짓이면 DORMANT_TEAM_FLOW_CODE 로 거부(토큰 모듈 미도달) | 리드 지시 ⑴ · D-TEAM 휴면 데몬 스위치 | D-TEAM·judge ① | - |
| handlers.rs | 8840 | feed 응답 team_token 경로는 팀 흐름 스위치 on 일 때만(off = 종전 owner_gui_required 판정) | 리드 지시 ⑵ | D-TEAM·judge ① | - |
| handlers.rs | 23190 | agy 시험 2건(usage_report_agy_statusline_… · fatal_fix_node_rate_alerts_skip_agy_…) 첫머리에 AgyLane force_for_thread(true) | 리드 지시 ⑷ · C4 agy 휴면 | C4 | usage_report_agy_statusline_attributes_antigravity_on_gemini_seats · fatal_fix_node_rate_alerts_skip_agy_seats_and_reset_windows |
| handlers.rs | 20027 | 새 시험 dormant_team_flow_switch_gates_team_token_rpc(off = 휴면 거부 · on = 토큰 모듈 응답) | 휴면 스위치 증명 | D-TEAM·judge ① | (신설) |
| team_gate_tests.rs | 각 #[test] 첫머리(8) | TeamFlow force_for_thread(true) 1줄 | 리드 지시 ⑶(맡은 파일 밖 — 리드 명시 지시로 수행) | D-TEAM | - |
| team_token_tests.rs | 각 #[test] 첫머리(11) | TeamFlow force_for_thread(true) 1줄 | 리드 지시 ⑶(맡은 파일 밖 — 리드 명시 지시로 수행) | D-TEAM | - |

### ledger-fix-pack (43행)

| 파일 | 줄 | 무엇을 | 왜 | K#/결정 | 적색 시험 |
|---|---|---|---|---|---|
| cysjavis-pack/bin/tests/test_dept_b11_lock.py | 137-141 | down 울타리 핀이 `down)` 갈래 + down_dept() 함수 본문까지 본다 | 원작자가 갈래 본문을 down_dept 함수로 뺌(병합) — 핀 목적(down 이 reg_fence_close 를 거친다) 불변 | 병합 구조 적응(우리 시험) | test_dept_b11_lock |
| cysjavis-pack/bin/tests/test_dept_notice_lane.py | 44-47 | _SCRUB 에 CYS_CYS_BIN·CYS_CYSD_BIN 추가 | 우리 dbg-D3 #F1(cys-dept 가 CYS_CYS_BIN 1순위) — 러너/좌석 env 누출 시 스텁 대신 실 cys → 가짜 HOME 데몬·120s 대기(TIMEOUT · 9 FAIL). test_dept_b11_lock:45 선례 | dbg-D3 F1 유지(우리) · 원작자 시험 env 위생 조정 | test_dept_notice_lane |
| cysjavis-pack/bin/javis_dept_request.py | 2240 | `mach is not True` → `mach is False`(판독 불가 None 을 사람 답으로 기록하지 않음) | 보안 리뷰 S3 — 배달 원장 판독 실패 때 기계 입력이 사람 답으로 기록되는 fail-open | 📌7ⓐ(master 1.1.8 범위 확정 · DECISION-TABLE §0 12행) | (적색 시험 없음 · 행동 변경) |
| cysjavis-pack/bin/cys-dept | 3248·3291·(reap 판독)3286 | 변경 없음 — 확인만 | judge 집행 조건 ④: 원작자 :2877(rotate)·:2908(reap 판독 sys.exit)·:2913(reap 전달) 이 병합본에서 모두 12(·11) 로 재번호돼 있음 실측 | P-EXIT12 · judge ④ | (없음) |
| cysjavis-pack/bin/tests/test_formation_tick_visibility.py | 104-106 | 기대 detail 의 「5역할」 → 「%d역할」 % len(REQUIRED_ROLES) | 우리 기본 함대 3석(master·cso·worker) — 원작자 5석 고정 문자열이 3b·4b·4c 바이트 비교를 깨뜨림(코드 결함 아님) | 09-10 기본 함대 3석 · DS-1 | test_formation_tick_visibility |
| cysjavis-pack/bin/javis_wakeup.py | 713 | 캡처 호출 subprocess.run 에 **NOWIN | 원작자 병합분 캡처 호출 창 숨김 누락(윈 콘솔 깜빡임) — 우리 규칙(test_nowin_captured_spawns) | X-NOWIN = 우리(P-NOWIN 잠정 수용) | test_nowin_captured_spawns |
| cysjavis-pack/bin/javis_resource_gate.py | 857 | ps 캡처 호출에 **NOWIN | 동(원작자 U11 fleet_cpu ps 측정 추가분) | X-NOWIN = 우리 | test_nowin_captured_spawns |
| cysjavis-pack/bin/javis_preflight.py | 4818·5938·5978·7846 | cys status·gate-corpus·claude --version·러너 캡처 호출 4곳에 **NOWIN | 동(원작자 0.14.41~43 추가분) | X-NOWIN = 우리 | test_nowin_captured_spawns |
| cysjavis-pack/bin/javis_guard_register.py | 83-84·244 | NOWIN 정본 정의 1줄 + cys status 캡처 호출에 **NOWIN | 동 · 정의 없는 파일이라 정본 모양 정의 추가(규칙 ②) | X-NOWIN = 우리 | test_nowin_captured_spawns |
| cysjavis-pack/bin/javis_role.py | 95-96·630 | NOWIN 정본 정의 1줄 + surface-role 캡처 호출에 **NOWIN | 동(원작자 0.14.31 역할 해소 모듈) | X-NOWIN = 우리 ⚠원작자 run_bootstrap_health U5 creationflags 동결표(H-WIN-16)에 두 파일이 늘어남 — 그 시험은 환경 적색 목록이고 우리 NOWIN 정책과 원래 상충(P-NOWIN) | test_nowin_captured_spawns |
| cysjavis-pack/bin/tests/test_pyseal_census.py | REFERENCING_FILES | javis_cycle_autopilot.py 항목(주석 포함)을 javis_phoenix_encoding_smoke.py 앞으로 이동(key=str 정렬) | 병합이 두 쪽 등재를 붙이며 정렬 깨짐(ⓑ 핀 목록 정렬·중복 없음) — 내용 무변경 | 병합 정렬 수리(양쪽 시험) | test_pyseal_census |
| cysjavis-pack/bin/tests/test_pyseal_census.py | BUNDLED_RESOLVER_FILES | src/bin/cysd/state.rs 등재 + 봉인 점검 주석 | 우리 1.1.7 좌석 배선(--wire-seat)이 bundled_python3 를 해소 → python_command 팩토리로 띄움(봉인 확인) · 원작자 ⓒ(v) census 가 우리 판을 처음 봄 | 병합 등재(양쪽 시험) | test_pyseal_census |
| cysjavis-pack/bin/javis_dept_request.py | 40 | sys.dont_write_bytecode = True(SEAL-1 층4) | 첫 형제 import(javis_lock :315) 전 봉인 누락 — 원작자 ⓒ(iv) census 가 우리 파일을 처음 봄 | SEAL-1 층4(양쪽 시험) | test_pyseal_census |
| cysjavis-pack/bin/javis_phoenix_encoding_smoke.py | 30 | sys.dont_write_bytecode = True(SEAL-1 층4) | 첫 형제 import(spec_from_file_location :73) 전 봉인 누락 — 동 | SEAL-1 층4(양쪽 시험) | test_pyseal_census |
| cysjavis-pack/bin/tests/test_resource_gate_notify_rule.py | 14-21·177-300 | A2 축 ⑧⑨⑩⑪·M1·M2 를 우리 cysr-102 A2(load·RECHECKS 6) 대신 원작자 U11(fleet_cpu 단독 hard · TOTAL 180/INTERVAL 30) 기준으로 재작성 — 가짜 시계(_FakeTime)로 실 대기 0 · 알림 횟수 목적·뮤턴트 2(재확인 진입 제거·축 좁힘 제거) KILLED 유지 | 우리 재측정 구현 폐기(K53 원작자 채택)로 RESOURCE_GATE_RECHECKS 등 속성 부재 AttributeError — 시험 삭제 대신 같은 목적을 채택 구현으로 재조준 | K53 원작자 채택 · 정책 §1-4 | test_resource_gate_notify_rule |
| cysjavis-pack/bin/tests/fixtures/dormant_team_flow_master_4a.md | (신규) | 원작자 v0.14.43 MASTER_DIRECTIVE :340(team-create-request 항)·:342-382(§4-A) 원문 무수정 + 출처 주석 | D-TEAM 휴면으로 제품 지침에서 §4-A 노출을 끊음(P-BYTES 선별) → javis_teamtoken ask 게이트가 directive_stale 로 전 경로 거부(시험 111 적색). 스위치를 켜 되살릴 때 넣을 문면을 시험 고정물로 보존 | D-TEAM 휴면(master#36f48cf7 ①) · judge ① | test_teamtoken |
| cysjavis-pack/bin/tests/test_teamtoken.py | 94-107·1381 | 라이브 지침에 §4-A-2 앵커가 없을 때만 고정물을 덧붙여 기본 팩·D 스위트를 구성(_with_dormant_4a) — 단언 무수정 | 휴면 기계의 원작자 단언(질문 게이트·문구 표 정합)을 그대로 재기 위함 · 111→2 적색(남은 D8·D11 = 출하 지침·CEO 서문 직접 핀 → 결정 필요) | D-TEAM 휴면 | test_teamtoken |
| cysjavis-pack/schedule.json | 35·45 | learn 내장 잡 2개 "_builtin_version": 3 → 4 | 데몬 BUILTIN_JOBS_VERSION 3→4(갈래 B 501edcf2 · K49) — cysd pack_seed_marked_jobs_match_builtin_defs 초록 조건(실측 ok) | K49 · 리드 지시 | (Rust) schedule::tests::pack_seed_marked_jobs_match_builtin_defs |
| cysjavis-pack/bin/javis_phoenix.py | 988 | cys 호출 Popen(stdout/stderr 파일 캡처)에 **NOWIN | 원작자 R3-2 무출력 상한 러너(병합분) 캡처 스폰 창 숨김 누락 — ph 포크 종료 뒤 처리 | X-NOWIN = 우리 | test_nowin_captured_spawns |
| cysjavis-pack/bin/tests/test_v113_review_fix.py | 162-165 | allocate 잠금 블록 탐색 시작점을 allocate_dept() 함수 머리로(없으면 종전 `allocate)`) | 원작자가 갈래 본문을 함수로 뺌 → section_end 미발견 ValueError — 핀 목적(윈 잠금 실패 = exit 11) 불변 | 병합 구조 적응(우리 시험) | test_v113_review_fix |
| cysjavis-pack/bin/tests/test_trust_seed.py | 2258-2262 | DeptLaunchWiring.env 제거 목록에 CYS_CYS_BIN·CYS_CYSD_BIN | 우리 dbg-D3 F1 — 러너 env 누출로 실 cys 가 불려 가짜 HOME 데몬(실측 14개 고아 · 제거함)·launch 120s → TIMEOUT. 스텁 의도 복원 | dbg-D3 F1 유지(우리) · 원작자 시험 env 위생 | test_trust_seed |
| cysjavis-pack/bin/cys-dept | 3434-3437 | cwd verb: reg_names(reg_init 경유) 대신 reg_read_py 직접 판독(초기화 0) + \r 제거 | 우리 reg_names 는 부재 레지스트리를 만든다 → 원작자 읽기 전용 계약(t5_absent·6g·r6) 위반. list 등 다른 동사의 「부재면 생성」(우리 test_absent_registry_created_silently)은 그대로 | codex R3 읽기 전용 계약(원작자) × 우리 reg_init 합성 | test_trust_seed |
| cysjavis-pack/bin/tests/test_capgate_hook_shell.py | 350-357 | python 부재 검체 env 에 CYS_TEST_SYSROOT=<빈 트리> 추가(단언 불변) | 우리 맥 해소기(_cys_bundle_py·cys_resolve_pybin)가 PATH 밖 /Applications/cysr.app 번들 파이썬을 찾아 "python 부재"가 재현되지 않았다(실 기계 의존) — 고정 경로 접두만 빈 트리로 옮김 | P-CLT(우리 유지) | test_capgate_hook_shell(HookDegradation.test_python_missing_asymmetry) |
| cysjavis-pack/hooks/dept-chat-inject.sh | 54 | 프리루드 직후 레인 redirect 1줄 추가 | 원작자 레인 격리(R-8 census): 우리 훅 3개에만 redirect 줄이 없어 부서 레인에서 상위 팩 사본이 돌거나 R-10 표식+exit 0 으로 침묵 강등 | 원작자 레인 격리 수용(잠정 해소 37) | test_lane_redirect(R-8) |
| cysjavis-pack/hooks/directive-event-inject.sh | 39 | 같음 | 같음 | 같음 | test_lane_redirect(R-8) |
| cysjavis-pack/hooks/inject-background.sh | 23 | 같음 | 같음 | 같음 | test_lane_redirect(R-8) |
| cysjavis-pack/bin/tests/test_hook_timing.py | 51-58·70 | cys-hook 계측 2시험이 빈 Stop.d 오버레이로 종전 경로를 타게 함(_legacy_path) | 원작자 0.14.42 R3-4 빠른 길(오버레이 0 = JSON 미판독)이 Stop 계측 분기보다 앞서 exit — 운영상 cys-hook.sh 는 C33 등록상 Pre/PostToolUse·PermissionRequest 전용이라 Stop 계측 본체는 save-state·reflect-scan·grill-stop 쪽(그 3시험 초록 유지) | 원작자 빠른 길 수용 · 우리 v113 Q1 계측 의미 유지(윈·오버레이 경로) | test_hook_timing(2) |
| cysjavis-pack/bin/tests/test_t6_injection_policy.py | 57-61 | E 절 검체 좌석을 CYS_ROLE=master(lead)로 | 원작자 U13: 역할 미상 좌석은 착수 게이트 문안 — T6 정책 문안의 주인은 lead 좌석(문안·단언 불변) | U13 수용 + T6 I-2(오너 확정) 유지 | test_t6_injection_policy(E2~E5 ×7) |
| cysjavis-pack/bin/tests/test_inject_context_role_seat.py | 133-142 | 12a LEGACY_STARTUP 핀 → 우리 T6 I-2 lead 문안 | lead startup 문안은 우리 오너 확정 정책이 대체(병합 훅 실물·t6 시험과 같은 문자열) | T6 I-2(오너 확정) 우선 | test_inject_context_role_seat(12a ×3) |
| cysjavis-pack/bin/tests/test_inject_context_role_seat.py | 148-150·247-270 | 12c 기준 커밋 126cfdd0 유지 + 기준 훅의 lead startup\|resume 한 줄만 현 훅 T6 줄로 치환(t6_overlay · 정확히 1:1 일치 때만 · 아니면 원본=정직 적색) | "U13 이 lead 출력을 바꾸지 않았다" 단언 유지 — 75d2407b(우리 1.1.7) 기준은 원작자 동일 cwd ℹ줄 등 U13 밖 차이로 17케이스 전부 갈려 부적합(실측) | T6 I-2 · U13 수용 | test_inject_context_role_seat(12c) |
| cysjavis-pack/hooks/session-start.sh | 797-848 | 본문 출력(상한 미만=본문 · 이상=목차+원문 생략 고지)을 U16 BEGIN 앞으로, 팀 소개 출력 분기를 블록 안으로 — END 뒤 = exit 0 만 | 원작자 B6(블록=파일 끝 exit 0 직전) · 우리 9,000자 상한 조립 출력 순서·바이트 불변(B1·B2·B4·B5 + test_session_start_hook 실패 집합 불변 실측) | 훅 9,000자 상한(우리) 유지 · U16 배치 수용 · D-TEAM 휴면 | test_team_create_u16(B6) |
| cysjavis-pack/bin/tests/test_team_create_u16.py | 108-111 | make_env 에서 CYS_CYS_BIN·CYS_CYSD_BIN 제거 | 우리 cys-dept dbg-D3 F1 은 두 env 를 PATH 스텁보다 먼저 쓴다 — 러너 env 누출로 실 cysd 가 가짜 HOME 에 뜨고 스텁 spawn 계수 0(158s→8s) | 우리 dbg-D3 F1 유지(본체 알림 패턴) | test_team_create_u16(A3) |
| cysjavis-pack/bin/tests/test_teamtoken_hook.py | 74-86·179-184 | 실험실 지침 사본에 원작자 §4-A 고정물(fixtures/dormant_team_flow_master_4a.md · 본체 소유)을 앵커 부재 때만 덧붙임 | D-TEAM 휴면으로 배포 지침에 §4-A-2 앵커가 없어 ask 가 directive_stale(휴면의 정상 fail-closed) — 이 검체는 스위치 켠 상태의 훅 배선을 잰다 | D-TEAM 휴면(master 결정 1) | test_teamtoken_hook(P·C·V·O·F·R·Z 37) |
| cysjavis-pack/bin/tests/test_phoenix_a3_ps_axis.py | 94 | spawn_production 대역 lambda 에 **_kw | 병합 run_restore 가 원작자 R3-2 로 units=·hang_suspected= 를 넘긴다(대역 TypeError) | R3-2 수용(잠정 해소 수용) | test_phoenix_a3_ps_axis |
| cysjavis-pack/bin/tests/test_phoenix_r4_restore.py | 98·88 | _restore 대역 **_kw + harness 에 fresh_expected=(False,"")·resume_arg_effect=("effective","") 대역 | ①units TypeError ②원작자 F-1(0.14.31)이 세션 파일 없는 claude 역할을 fresh 예상으로 돌려 좌석결속 관측(실 grace sleep 6×1.5s×재검증)으로 보냄 → 시험 시간 초과·이 축과 무관 ③임시 팩에 agents.json 없음 → resume_mode unknown → 원작자 R3b 가 VERIFIED 를 막음. 우리 시나리오 전제(세션핀 재개 가능 S1)를 대역으로 명시 — F-1 자체는 원작자 test_phoenix_f1_* 가 잰다 | F-1·R3b 수용(잠정 해소 수용) | test_phoenix_r4_restore |
| cysjavis-pack/bin/tests/test_phoenix_v115_spawn_settle.py | 73·71 | _restore 대역 **_kw + fresh_expected·resume_arg_effect 대역(같은 이유) | 위와 같음 | F-1·R3b 수용 | test_phoenix_v115_spawn_settle |
| cysjavis-pack/bin/tests/test_v116_phoenix_midrun_tomb.py | 79·77 | _restore 대역 **_kw + fresh_expected·resume_arg_effect 대역(같은 이유) | 위와 같음 | F-1·R3b 수용 | test_v116_phoenix_midrun_tomb |
| cysjavis-pack/bin/tests/test_phoenix_v115_owner_token.py | 13·104~110 | M2 변이 대상을 「stage_reinject 의 owner=True 키워드」→「cys() 의 reinject 동사 판정 줄(owner=False 로)」로 교체 | 병합(X-OWNER)으로 호출부 owner=True 가 사라지고 cys() 가 owner 미지정 시 reinject 동사로 판정 — 변이 대상 문자열 소멸(선-assert count=0). 새 변이는 S1·S2(실 주입 경로) 를 적색으로 만든다 = KILLED · 뮤턴트 목적 유지 | P-OWNER(잠정 = 우리 키워드 존치 + 동사 판정) | test_phoenix_v115_owner_token |
| cysjavis-pack/bin/tests/test_phoenix_r32_restore_budget.py | fake_cys(restore 분기 앞) | `restore --help` 를 스폰 상한 기록에서 제외(읽기 전용 응답) | 우리 1.1.7 restore_supports_per_entry_cwd 탐침(timeout 10)이 restore_calls 첫 원소로 섞여 ⑥ 2건 적색([10,547]) | 우리 per-entry cwd 탐침 유지(잠정) | test_phoenix_r32_restore_budget |
| cysjavis-pack/bin/tests/test_phoenix_r32_restore_budget.py | partial 시나리오 2회차 | 2회차 restore 결과로 w7 빈 좌석도 occupied 로 모델 | 우리 v115 A4/905 A2 「빈 좌석(seat=empty)은 부활 아님」 → 원작자 대본(w7 empty 유지)이 재시도·빈좌석 재사용(close-surface --reap) 경로로 번져 미모델 CLI 예외. 축의 목적(2회차 상한 = 침식 topology 2단위) 불변 · 기대값 [o(8), o(2)] 그대로 | 우리 빈좌석 판정 유지(v115) | test_phoenix_r32_restore_budget |
| cysjavis-pack/bin/tests/test_phoenix_r32_restore_budget.py | t_source_pins cbody | cys() 몸통 절단 기준을 서명 접두 `def cys(*args, socket=None, timeout=25` 로 | cys() 서명에 선택 키워드 owner=None 이 붙어 정확 문자열 index 실패(ValueError). 핀 내용(무출력 실행기 조건) 불변 | P-OWNER | test_phoenix_r32_restore_budget |
| cysjavis-pack/bin/tests/test_phoenix_f1_production_path.py | fake_cys·verbs·2단언 | `restore --help` 응답 모델 · 「exactly one restore」를 스폰 restore(인자 없음) 1회로 · CLI protocol 에 읽기 전용 `list` 허용 · 순서 단언은 스폰 restore 기준 | 원인은 X-INSEAT 가 아니었다(실측): 우리 1.1.7 읽기 전용 관측 2개 — restore --help(항목별 cwd 능력 탐침) · list(A3 ps 축 좌석 셸 pid). 파괴 동사 금지 단언(non-destructive)은 그대로 | 우리 per-entry 탐침·A3 ps 축 유지 | test_phoenix_f1_production_path |
| (코드 무변경) | — | test_phoenix_c6_reap · e2e_replacement · w2_untomb_fullcycle = 환경 적색 | isoenv HOME(스크래치패드 긴 경로)/.cys/state-harness/cys.sock 이 SUN_LEN(104) 초과 → cysd bind panic(main.rs:1681). 기준판 up43·117 은 바이너리 미발견 SKIP(rc 0)이라 비교 불가였을 뿐. HOME=<임시> 로 돌리면 6/6·6/6·8/8 PASS | 환경 | test_phoenix_c6_reap·test_phoenix_e2e_replacement·test_phoenix_w2_untomb_fullcycle |

### ledger-fix-pack-hk (11행)

| 파일 | 줄 | 무엇을 | 왜 | K#/결정 | 적색 시험 |
|---|---|---|---|---|---|
| cysjavis-pack/bin/tests/test_capgate_hook_shell.py | 350-357 | python 부재 검체 env 에 CYS_TEST_SYSROOT=<빈 트리> 추가(단언 불변) | 우리 맥 해소기(_cys_bundle_py·cys_resolve_pybin)가 PATH 밖 /Applications/cysr.app 번들 파이썬을 찾아 "python 부재"가 재현되지 않았다(실 기계 의존) — 고정 경로 접두만 빈 트리로 옮김 | P-CLT(우리 유지) | test_capgate_hook_shell(HookDegradation.test_python_missing_asymmetry) |
| cysjavis-pack/hooks/dept-chat-inject.sh | 54 | 프리루드 직후 레인 redirect 1줄 추가 | 원작자 레인 격리(R-8 census): 우리 훅 3개에만 redirect 줄이 없어 부서 레인에서 상위 팩 사본이 돌거나 R-10 표식+exit 0 으로 침묵 강등 | 원작자 레인 격리 수용(잠정 해소 37) | test_lane_redirect(R-8) |
| cysjavis-pack/hooks/directive-event-inject.sh | 39 | 같음 | 같음 | 같음 | test_lane_redirect(R-8) |
| cysjavis-pack/hooks/inject-background.sh | 23 | 같음 | 같음 | 같음 | test_lane_redirect(R-8) |
| cysjavis-pack/bin/tests/test_hook_timing.py | 51-58·70 | cys-hook 계측 2시험이 빈 Stop.d 오버레이로 종전 경로를 타게 함(_legacy_path) | 원작자 0.14.42 R3-4 빠른 길(오버레이 0 = JSON 미판독)이 Stop 계측 분기보다 앞서 exit — 운영상 cys-hook.sh 는 C33 등록상 Pre/PostToolUse·PermissionRequest 전용이라 Stop 계측 본체는 save-state·reflect-scan·grill-stop 쪽(그 3시험 초록 유지) | 원작자 빠른 길 수용 · 우리 v113 Q1 계측 의미 유지(윈·오버레이 경로) | test_hook_timing(2) |
| cysjavis-pack/bin/tests/test_t6_injection_policy.py | 57-61 | E 절 검체 좌석을 CYS_ROLE=master(lead)로 | 원작자 U13: 역할 미상 좌석은 착수 게이트 문안 — T6 정책 문안의 주인은 lead 좌석(문안·단언 불변) | U13 수용 + T6 I-2(오너 확정) 유지 | test_t6_injection_policy(E2~E5 ×7) |
| cysjavis-pack/bin/tests/test_inject_context_role_seat.py | 133-142 | 12a LEGACY_STARTUP 핀 → 우리 T6 I-2 lead 문안 | lead startup 문안은 우리 오너 확정 정책이 대체(병합 훅 실물·t6 시험과 같은 문자열) | T6 I-2(오너 확정) 우선 | test_inject_context_role_seat(12a ×3) |
| cysjavis-pack/bin/tests/test_inject_context_role_seat.py | 148-150·247-270 | 12c 기준 커밋 126cfdd0 유지 + 기준 훅의 lead startup\|resume 한 줄만 현 훅 T6 줄로 치환(t6_overlay · 정확히 1:1 일치 때만 · 아니면 원본=정직 적색) | "U13 이 lead 출력을 바꾸지 않았다" 단언 유지 — 75d2407b(우리 1.1.7) 기준은 원작자 동일 cwd ℹ줄 등 U13 밖 차이로 17케이스 전부 갈려 부적합(실측) | T6 I-2 · U13 수용 | test_inject_context_role_seat(12c) |
| cysjavis-pack/hooks/session-start.sh | 797-848 | 본문 출력(상한 미만=본문 · 이상=목차+원문 생략 고지)을 U16 BEGIN 앞으로, 팀 소개 출력 분기를 블록 안으로 — END 뒤 = exit 0 만 | 원작자 B6(블록=파일 끝 exit 0 직전) · 우리 9,000자 상한 조립 출력 순서·바이트 불변(B1·B2·B4·B5 + test_session_start_hook 실패 집합 불변 실측) | 훅 9,000자 상한(우리) 유지 · U16 배치 수용 · D-TEAM 휴면 | test_team_create_u16(B6) |
| cysjavis-pack/bin/tests/test_team_create_u16.py | 108-111 | make_env 에서 CYS_CYS_BIN·CYS_CYSD_BIN 제거 | 우리 cys-dept dbg-D3 F1 은 두 env 를 PATH 스텁보다 먼저 쓴다 — 러너 env 누출로 실 cysd 가 가짜 HOME 에 뜨고 스텁 spawn 계수 0(158s→8s) | 우리 dbg-D3 F1 유지(본체 알림 패턴) | test_team_create_u16(A3) |
| cysjavis-pack/bin/tests/test_teamtoken_hook.py | 74-86·179-184 | 실험실 지침 사본에 원작자 §4-A 고정물(fixtures/dormant_team_flow_master_4a.md · 본체 소유)을 앵커 부재 때만 덧붙임 | D-TEAM 휴면으로 배포 지침에 §4-A-2 앵커가 없어 ask 가 directive_stale(휴면의 정상 fail-closed) — 이 검체는 스위치 켠 상태의 훅 배선을 잰다 | D-TEAM 휴면(master 결정 1) | test_teamtoken_hook(P·C·V·O·F·R·Z 37) |

### ledger-fix-pack-ph (10행)

| 파일 | 줄 | 무엇을 | 왜 | K#/결정 | 적색 시험 |
|---|---|---|---|---|---|
| cysjavis-pack/bin/tests/test_phoenix_a3_ps_axis.py | 94 | spawn_production 대역 lambda 에 **_kw | 병합 run_restore 가 원작자 R3-2 로 units=·hang_suspected= 를 넘긴다(대역 TypeError) | R3-2 수용(잠정 해소 수용) | test_phoenix_a3_ps_axis |
| cysjavis-pack/bin/tests/test_phoenix_r4_restore.py | 98·88 | _restore 대역 **_kw + harness 에 fresh_expected=(False,"")·resume_arg_effect=("effective","") 대역 | ①units TypeError ②원작자 F-1(0.14.31)이 세션 파일 없는 claude 역할을 fresh 예상으로 돌려 좌석결속 관측(실 grace sleep 6×1.5s×재검증)으로 보냄 → 시험 시간 초과·이 축과 무관 ③임시 팩에 agents.json 없음 → resume_mode unknown → 원작자 R3b 가 VERIFIED 를 막음. 우리 시나리오 전제(세션핀 재개 가능 S1)를 대역으로 명시 — F-1 자체는 원작자 test_phoenix_f1_* 가 잰다 | F-1·R3b 수용(잠정 해소 수용) | test_phoenix_r4_restore |
| cysjavis-pack/bin/tests/test_phoenix_v115_spawn_settle.py | 73·71 | _restore 대역 **_kw + fresh_expected·resume_arg_effect 대역(같은 이유) | 위와 같음 | F-1·R3b 수용 | test_phoenix_v115_spawn_settle |
| cysjavis-pack/bin/tests/test_v116_phoenix_midrun_tomb.py | 79·77 | _restore 대역 **_kw + fresh_expected·resume_arg_effect 대역(같은 이유) | 위와 같음 | F-1·R3b 수용 | test_v116_phoenix_midrun_tomb |
| cysjavis-pack/bin/tests/test_phoenix_v115_owner_token.py | 13·104~110 | M2 변이 대상을 「stage_reinject 의 owner=True 키워드」→「cys() 의 reinject 동사 판정 줄(owner=False 로)」로 교체 | 병합(X-OWNER)으로 호출부 owner=True 가 사라지고 cys() 가 owner 미지정 시 reinject 동사로 판정 — 변이 대상 문자열 소멸(선-assert count=0). 새 변이는 S1·S2(실 주입 경로) 를 적색으로 만든다 = KILLED · 뮤턴트 목적 유지 | P-OWNER(잠정 = 우리 키워드 존치 + 동사 판정) | test_phoenix_v115_owner_token |
| cysjavis-pack/bin/tests/test_phoenix_r32_restore_budget.py | fake_cys(restore 분기 앞) | `restore --help` 를 스폰 상한 기록에서 제외(읽기 전용 응답) | 우리 1.1.7 restore_supports_per_entry_cwd 탐침(timeout 10)이 restore_calls 첫 원소로 섞여 ⑥ 2건 적색([10,547]) | 우리 per-entry cwd 탐침 유지(잠정) | test_phoenix_r32_restore_budget |
| cysjavis-pack/bin/tests/test_phoenix_r32_restore_budget.py | partial 시나리오 2회차 | 2회차 restore 결과로 w7 빈 좌석도 occupied 로 모델 | 우리 v115 A4/905 A2 「빈 좌석(seat=empty)은 부활 아님」 → 원작자 대본(w7 empty 유지)이 재시도·빈좌석 재사용(close-surface --reap) 경로로 번져 미모델 CLI 예외. 축의 목적(2회차 상한 = 침식 topology 2단위) 불변 · 기대값 [o(8), o(2)] 그대로 | 우리 빈좌석 판정 유지(v115) | test_phoenix_r32_restore_budget |
| cysjavis-pack/bin/tests/test_phoenix_r32_restore_budget.py | t_source_pins cbody | cys() 몸통 절단 기준을 서명 접두 `def cys(*args, socket=None, timeout=25` 로 | cys() 서명에 선택 키워드 owner=None 이 붙어 정확 문자열 index 실패(ValueError). 핀 내용(무출력 실행기 조건) 불변 | P-OWNER | test_phoenix_r32_restore_budget |
| cysjavis-pack/bin/tests/test_phoenix_f1_production_path.py | fake_cys·verbs·2단언 | `restore --help` 응답 모델 · 「exactly one restore」를 스폰 restore(인자 없음) 1회로 · CLI protocol 에 읽기 전용 `list` 허용 · 순서 단언은 스폰 restore 기준 | 원인은 X-INSEAT 가 아니었다(실측): 우리 1.1.7 읽기 전용 관측 2개 — restore --help(항목별 cwd 능력 탐침) · list(A3 ps 축 좌석 셸 pid). 파괴 동사 금지 단언(non-destructive)은 그대로 | 우리 per-entry 탐침·A3 ps 축 유지 | test_phoenix_f1_production_path |
| (코드 무변경) | — | test_phoenix_c6_reap · e2e_replacement · w2_untomb_fullcycle = 환경 적색 | isoenv HOME(스크래치패드 긴 경로)/.cys/state-harness/cys.sock 이 SUN_LEN(104) 초과 → cysd bind panic(main.rs:1681). 기준판 up43·117 은 바이너리 미발견 SKIP(rc 0)이라 비교 불가였을 뿐. HOME=<임시> 로 돌리면 6/6·6/6·8/8 PASS | 환경 | test_phoenix_c6_reap·test_phoenix_e2e_replacement·test_phoenix_w2_untomb_fullcycle |

## ③ 수리 2차(ff2fc8bd·542c6cf0·이후)

### ledger-fix2-lead (24행)

| 파일 | 자리 | 무엇을 | 왜 | 결정 | 적색 시험 |
|---|---|---|---|---|---|
| ui/src/deptcreate.ts | DEPT_SEAT_ROLES · SEATS_LINE · 머리 주석 | 5석 → 우리 편성 정본 3석(master·cso·worker) · 확인 창 문구 「팀원 최대 2(CSO·워커)」「필요한 프로그램(claude)」 | javis_formation.py REQUIRED_ROLES(박사님 09-10 기본 함대)와 결속 — 5석이면 「모두 붙었습니다」 영영 안 뜨고 3분 뒤 정체 오보 | DS-1 master#c6a9de68 | deptcreate 드리프트 핀 · deptprogressseats 출처 핀 + DS-1 영향 55 |
| ui/src/deptprogress.ts | booting·check·stall 본문 · 주석 | 「(claude·agy·codex)」 → 「(claude)」 3곳 · 「다섯」 → 「전부」 주석 | 3석 결속의 사실 정합(리더 덧붙임 — 문구 사실 정합만) | DS-1 파생 | deptprogress* 문구 단언 |
| ui/src/deptprogress*.test.ts · deptcreate.test.ts | 서브 2기 원장 참조 | 5석 기대값 → 3석 | DS-1 | DS-1 | ledger-fix-ds1-unit.tsv(19) · ledger-fix-ds1-wiring.tsv(19) |
| src/bin/cysd/accounts.rs | display_outranked · display_rank 삭제 | 전체 순위(OAuth3>좌석2>창밖1>예열0) → 창 밖 보고만 강등(창 밖이 아닌 신선 표시값을 창 밖 보고가 못 덮음) | 501edcf2 의 전체 순위를 좁힘 — D6-1 최신 승자 복원 | B(a) master#c6a9de68 | d6_1_mixed… · d6_1_dead… (초록) |
| src/bin/cysd/accounts.rs | display_priority_oauth_over_seat_over_outside → display_priority_outside_report_demoted_only | 우리 신규 시험(501edcf2)을 B(a) 동작 기준으로 재작성(OAuth↔좌석 최신 승자 단언 추가) | B(a) | B(a) | (우리 시험) |
| src/bin/cysd/accounts.rs | seed_known_ignores_antigravity_dir · seed_known_drops_antigravity_snapshot_rows | test_home::set 이음매 추가(HOME 은 유지) | 원작자 R2F-DM 소스 핀 — HOME 만 돌리는 검체 금지(윈 dirs::home_dir 은 HOME 안 봄) | 원작자 핀 준수 | approval r2f_dm_no_daemon_test_turns_only_the_home_env_without_a_seam |
| src/submit_probe.rs | input_region_anchored | 열린 입력 박스(╭ 뒤 ╰ 없음) 안 줄머리 `> ` 는 앵커 아님(내용) · 단위 시험 1(비동어반복 — 수정 전 적색) | drain_verify_delivery_failed_on_wedge 흔들림 = 주입문 40자 접힘에서 `> ` 가 줄머리에 떨어지면(경로·pid 길이 의존) 앞의 잔류 입력을 잘라 미제출을 제출로 오독 · 실화면도 같은 오독 가능 | HANDOFF 수리 후보 | tests::drain_verify_delivery_failed_on_wedge |
| ui/src/main.ts | promptBinaryPatch | installingUpdate 를 스마트 앱 컨트롤 사전 조회 앞에서 세움 · 조회·확인 창·설치 전부 try/finally · 확인 뒤 두 번째 표식 확인 제거(이제 자기 표식이라) | SAC 검사 중 재클릭 → 조회 3회·확인 창 중첩(우리 판) 차단 | X2-R master#c6a9de68 | updatenotice 재진입 2 · 머리 핀 1 · 안내 문안 1 · 같은 방식 1 |
| ui/src/updatenotice.test.ts | 진행 중 표식 핀 · BUSY_TOAST · 재진입 2 · 안내 문안 · 같은 방식 | 원작자 이름(promptBinaryPatchBusy·notifyBinaryPatchBusy·watchdog 문안) → 우리 이름(installingUpdate·INSTALL_BUSY feed 문안) · 목적(진입 즉시 확인→안내·올린 뒤 전부 try·finally 내림·안내 1줄) 유지 · 「같은 방식」 비교 대상 = 팀 흐름 안내(watchdog) → 업데이트 흐름 재진입 안내(restartAfterUpdate · feed) | X2-R = 우리 가드 유지 결정 | X2-R | (조정 5) |
| src-tauri/src/main.rs | 데몬 실패 문구 9136 | 「cys」 → 「cysr」 | X8 브랜드 · ui PRIVACY_APP_NAME="cysr" 교차 파리티 | X8 · cysr 문구 | folderaccess Rust 데몬 실패 문구 파리티 |
| ui/src/{usagewiring,expertwiring,updatewiring,deptprogresswiring,teamproposal,confirmlayer,feedbackwiring,staleclaims}.test.ts | 실패 중이던 82건 | it(/test( → itDormant(/testDormant( = it.if/test.if(CYS_UI_DORMANT_LANE=="1") · 파일마다 정의 2줄 | 휴면·미수용 기능 배선 시험 격리 레인(삭제·무조건 skip 0) · 켠 레인 실패 집합 = 격리 전 집합(차이 0 실측) | UNW ⓐ master#c6a9de68 | 82 |
| ui/src/bun-env.d.ts | TestFn | if(condition) 선언 1 | tsc 앰비언트(설치 아닌 선언 추가 계약) | UNW | tsc 0 |
| src/lib.rs | dormant 문서 | B(b) 확정 1줄 | B(b) 문서 1줄 | B(b) | — |
| docs/merge/BACKLOG-118.md | 신규 | B1 휴면-on CI 레인 = 1.1.9(단점 명시) · B2 휴면 env | UNW · B(b) | master#c6a9de68 | — |
| ui/src/main.ts | promptBinaryPatch tail | 윈도우 분기 = 원작자 R1F-UA(S3 note 14) 문면(「미저장분」만 D4#14 쉬운 말) · 맥·그 밖(리눅스) = 우리 종전 | 실측: 우리 윈 경로 drain·핸드오프 없음 = src-tauri/src/main.rs install_update_checked_windows(8415~8476: 받기→설치기→cleanup_before_exit→process::exit(0)) · 대체 경로도 플러그인이 설치 중 종료(8338~8340 주석) → 8380 drain 미도달 | X2-W master#114e0c71 ② | updatenotice R1F-UA(S3 note 14) |
| ui/src/updatenotice.test.ts | S3 note 14 시험 · 대역 deps | 우리 제목·틀 + 윈 원작자 방법 절로 기대값 · IS_WINDOWS 대역 추가 | X2-W | X2-W | (조정) |
| cysjavis-pack/directives/MASTER_CORE.md | 머리 주석 sections | §2 dfcf85999b203f7d→534a7bf740273f12 · §7 f399e48e162da7e0→145904d9638d9092 · §9 40baf0bd68f51654→d6e45d9ae1aa13d0 · §11 6bf5a0d974de8f67→49ff1a49be7a6744(값 = hooks/core_inject.py verify 출력) | MASTER_DIRECTIVE §2·§7·§9·§11 병합 변경 · 계약 시험 갱신 | test_core_inject 해시 4 master#114e0c71 ③ | test_core_inject P1·P3·A4·A6 |
| cysjavis-pack/directives/CEO_CORE.md | 머리 주석 body_sections | 같은 4절·같은 값(CEO_TEMPLATE 본문 = MASTER_DIRECTIVE 글자 동일 · 같은 절 해시 규칙) | 같은 해시 4개의 사본 | ③ | test_core_inject B2 |
| cysjavis-pack/bin/tests/test_teamtoken.py | check_dormant 신설 · D8·D11 | CYS_ENABLE_TEAM_FLOW=1 레인에서만 판정(꺼진 레인 = [LANE] 1줄 · 계수 안 함) · 켠 레인에서 D8·D11 적색 실측(정상) | D-TEAM 휴면 지침 문면 핀 | ④ ⓑ 휴면-on 레인 | D8 · D11 |
| cysjavis-pack/hooks/session-start.sh | _ss_read_guide · _SS_HEAD | 원작자 「지침 전문 읽기 안내」 1줄을 각성 헤더 바로 뒤(비master · resume·비resume) — 우리 머리 줄은 모두 그 앞 = 창 안 손실 0 | R2NC-F2 | ⑤ | session_start_hook 22·22b worker 초록 · master 22·22b 적색(설계 충돌 — 결정 필요) |
| cysjavis-pack/bin/javis_phoenix.py | spawn_in_seat_production · 호출부 | timeout=90 → restore_spawn_timeout_s(units) · 호출부 units=len(need) · 반환에 timeout_s·timeout_why | R3-2 파생값 유지(원작자 고정 90 미채택) | ⑥ | (신규) r32 ⑩ 3검 |
| cysjavis-pack/bin/tests/test_phoenix_r32_restore_budget.py | t_in_seat_derived | 파생값 시험 1(3검 · 수정 전 적색 = 고정 90) | ⑥ 「시험 없음」 해소 | ⑥ | — |
| cysjavis-pack/bin/tests/{test_phoenix_r4_restore,test_v116_phoenix_midrun_tomb,test_phoenix_v115_spawn_settle}.py | spawn_in_seat_production 대역 | units=None 인자 수용 | 호출부 키워드 추가 | ⑥ | — |
| cysjavis-pack/bin/tests/test_session_start_hook.py | 22·22b | master 케이스만 CYS_DORMANT_LANE=1 레인(꺼짐 = [LANE] 1줄 · 켠 레인 master 22·22b 적색 실측) · worker 기본 레인 그대로 | 설계 충돌 — master 는 요지 조립기 경로 | ⑤ master#f0e81041 · DECISION-TABLE §0 15행 | 22·22b master |

### ledger-fix-ds1-unit (18행)

| 파일 | 줄 | 무엇을 | 왜 | 시험 이름 |
|---|---|---|---|---|
| ui/src/deptprogress.test.ts | 8,15-17 | 머리 주석 다섯/M<5 → 셋/M<3 | DS-1 의무 역할 3석 | (주석) |
| ui/src/deptprogress.test.ts | 333-338 | BOOT·CHECK·STALL 기대 문구 (claude·agy·codex)→(claude) · 최대 5자리→최대 3자리 | DS-1 deptprogress.ts 문구 변경(소스 실제 문구 대조) | deptFormationText — 5상태 describe 전체(booting·check·stall·모르는 상태·이상한 입력) |
| ui/src/deptprogress.test.ts | 341-344 | booting 제목 문구 + seats 3/5 예시 → 1/2(3=모두 붙음이라 booting 에 부적합) | DS-1 | booting(기본) — 제목 「팀원을 켜는 중」… |
| ui/src/deptprogress.test.ts | 357-360,414 | seated 본문 「자리 5개」→「자리 3개」 · seats 5→3 | DS-1 DEPT_SEAT_ROLES.length=3 | seated — 제목 「팀 자리가 모두 붙었습니다」… / 자리 수·경과가 이상해도… |
| ui/src/deptprogress.test.ts | 362-363 | check 제목 문구 + seats 3→2(3 이면 seated) | DS-1 | ★check(설치 여부를 모르는 15분 상한)… |
| ui/src/deptprogress.test.ts | 376-379 | stall 제목 문구 + seats 3·4→2(정체 후보는 1~2) | DS-1 | ★stall(자리가 3분 동안 더 붙지 않음)… |
| ui/src/deptprogress.test.ts | 488,494,497-503 | 정체 경계 루프 [1..4]→[1,2] · 「방금 늘었다」 3→2 · 자리 수 조건 3(모두)·4·5 는 false · 1~2 만 true · 제목 다섯→셋 | DS-1 stall 은 1≤M<3 | ★경계 — 179.999초… / ★자리 수 조건… |
| ui/src/deptprogress.test.ts | 510-512 | 모르는 입력 검체의 seated 3→2(3 은 이제 모두 붙음이라 시각과 무관하게 false — 시각 방어를 못 재는 공허 단언이 됨) | DS-1 단언 목적 유지 | 모르는 입력(자리 수·기준 시각·지금이…)으로 정체를 지어내지 않는다 |
| ui/src/deptprogressseats.test.ts | 7-8 | DS-1 머리 주석 추가 | DS-1 | (주석) |
| ui/src/deptprogressseats.test.ts | 60-66 | FIVE/five() → ROSTER(3석)·ONDEMAND(리뷰어 2)·WITH_REVIEWERS·fullRows() | DS-1 의무 3석 · 리뷰어=온디맨드 | (픽스처) |
| ui/src/deptprogressseats.test.ts | 69-74 | 출처 검체 기대값 FIVE→ROSTER · 제목 다섯→세 역할 | DS-1 REQUIRED_ROLES=(master,cso,worker) | 세 역할 · 순서까지 편성 로스터와 같다… |
| ui/src/deptprogressseats.test.ts | 87-93 | deptLiveRoles 실제 꼴 다섯 줄 = 의무 셋 + 리뷰어 둘(기대값 불변) | 픽스처 이름 변경 추종 | ★실제 꼴 다섯 줄(의무 셋 + 온디맨드 리뷰어 둘)… |
| ui/src/deptprogressseats.test.ts | 115-125 | deptSeatedCount 셋이면 3·빠지면 2 + 새 핀(리뷰어는 의무 자리로 세지 않음) | DS-1 새 동작 핀 | 셋이면 3 · 하나씩 빠질 때마다 2 · 비면 0 / ★DS-1: 온디맨드 리뷰어… |
| ui/src/deptprogressseats.test.ts | 144-170 | verdict seated 3(리뷰어 섞여도 3) · wait/check 2(리뷰어가 빈 의무 자리 못 메움) · 실제 꼴 종료 마스터 → 2 | DS-1 | 세 역할이 모두 붙었으면 seated… / ★셋이 안 됐고… / ★셋이 안 됐는데 상한… / ★실제 꼴 입력… |
| ui/src/deptprogressseats.test.ts | 172-200 | seated 「자리 3개」 · check/stall seats 3→2 · 문구 (claude) | DS-1 문구 변경 | seated — … / check(설치 여부를 모르는…) / stall(자리가 3분 동안…) |
| ui/src/deptcreate.test.ts | 4,20 | 머리 주석·describe 5석→3석 | DS-1 | 자리 역할 드리프트 핀 — 편성 도구와 같은 3석(1.1.8 DS-1) |
| ui/src/deptcreate.test.ts | 54-59 | 「최대 5개」→「최대 3개」 + SEATS_LINE 새 문구 핀 「팀원 최대 2(CSO·워커)」·「필요한 프로그램(claude)」 | DS-1 SEATS_LINE 변경 | 본문: 이름 · 자리 최대 3개 · 작업 폴더 · 첫 로그인 가능성 |
| ui/src/deptcreate.test.ts | 91 | REUSE 본문 「최대 5개」→「최대 3개」 | DS-1 | 등재 이름과 '꺼져 있으면 다시 켜고 자리를 다시 띄운다' |

### ledger-fix-ds1-wiring (19행)

| 파일 | 줄 | 무엇을 | 왜 | 시험 이름 |
|---|---|---|---|---|
| ui/src/deptprogresswiring.test.ts | 전역(1236·1267·1289·1517·1518·1690·1691·2201·2215·2244 등) | 기대 문구 「설치된 프로그램(claude·agy·codex)…(최대 5자리」→「(claude)…(최대 3자리」 · 「설치하지 않은 프로그램(claude·agy·codex)」→「(claude)」 · 「자리 5개가 모두 붙었습니다」→「자리 3개가 …」 | DS-1 deptprogress.ts booting·check·stall·seated 문구 변경(소스 실제 문구 Read 대조) | 성공 직후 첫 안내 · 값(열쇠)이 바뀔 때만 · R2F-UI 60초 공백 2건 · M=0 정체 아님 · 그 밖 문구 단언 전부 |
| ui/src/deptprogresswiring.test.ts | 1174·2071 | 픽스처 로스터 FIVE(5역할)→ROSTER ["master","cso","worker"] · seatsOf 가 3석에서 자른다 | DS-1 DEPT_SEAT_ROLES 3석(javis_formation REQUIRED_ROLES 결속) | 팀원 부팅 안내 describe · ★S4 B1 실제 3초 틱 describe 전체 |
| ui/src/deptprogresswiring.test.ts | 전역 | seatsOf(5)(=모두 붙음)→seatsOf(3) | DS-1 완료 = 의무 역할 3석 | 모두 붙음을 쓰는 검체 전부(완료·본부 목록·삭제 중 대조·× 뒤 최종 안내 등) |
| ui/src/deptprogresswiring.test.ts | 1292-1309 | 5분 100틱 좌석 순서 0→1→2→3→4 를 0→1→2(130초부터 2)로 · 마지막 「붙은 자리 4」→「2」 · 제목 (다섯 전에는)→(셋이 다 붙기 전에는) | DS-1: 3이면 seated 로 접혀 켜는 중 갱신 검체가 무너짐 · 한 값 체류 <180초로 정체 미개입 | ★5분(3초 틱 100번)을 돌려도 호출은 한 자릿수~십여 회 |
| ui/src/deptprogresswiring.test.ts | 1349-1418 | describe 제목 「의무 역할 다섯」→「의무 역할 셋(1.1.8 DS-1 · 우리 편성 3석)」 · 붙는 순서 1·2·3·4→1·2 · 미완 팀 seatsOf(3)→(2) · 제목 다섯→셋 | DS-1 | ★다섯 역할이 모두 붙으면(→★의무 역할 셋이 모두 붙으면) · ★실제 꼴: 두 팀이 동시에 · ★종료한 좌석·변형 역할(제목만) |
| ui/src/deptprogresswiring.test.ts | 1447-1475 | 15분 상한 미완 seatsOf(3)→(2) · 「붙은 자리 3개」→「2개」 · 제목 다섯→셋 | DS-1: 3 은 이제 모두 붙음(seated) | ★15분(900초)에 닿았는데 다섯 역할이(→의무 역할 셋이) · 상한 틱에 다섯이(→셋이) 모두 붙어 있으면 |
| ui/src/deptprogresswiring.test.ts | 1591-1629 | 무응답 뒤 판정 seatsOf(4)/CHECK(4)→(2) · 상한 틱 1틱 결손 seatsOf(3)/CHECK(3)→(2) · 삭제 중 탭 상한 seatsOf(3)→(2) · 주석 네 자리/셋→두 자리/둘 | DS-1 | ★15분 상한인데 최근 60초 안에 받은 목록이 없으면 · 상한 틱에 목록을 이번 틱만 못 받았을 뿐 · ★삭제 중·종료 실패 탭(제목 다섯→셋) |
| ui/src/deptprogresswiring.test.ts | 1660-1679 | '모름' 사례: [3,"claude 만 설치"]→[2,"2자리에서 멈춤(워커 자리가 뜨지 않은 PC)"] · 모두 붙음 대조를 「claude 만 설치(문서대로 설치한 PC) — 3석 모두」로 · 변수 five→full · 제목 갱신 | DS-1: 우리 3석은 모두 claude 라 claude 만 깐 PC 는 미완이 아니라 완료(취지 = 미완은 경고 아닌 15분 경과 · 자리 수 그대로 — 유지) | ★'모름' 상태의 사례 둘 |
| ui/src/deptprogresswiring.test.ts | 1682-1705 | 정체 describe 규칙 주석 M<5→M<의무 역할 수(3) · 도우미 claudeOnly()(1·2·3, 마지막 증가 100초)→stuckAt(top=2: 10초 1·100초 2 \| top=1: 100초 1) — 마지막 증가 100초 불변 | DS-1: 3자리 정체 사례가 이제 seated 로 끝남 → 셋 미만 정체로 | 정체 describe 전체 |
| ui/src/deptprogresswiring.test.ts | 1706-1970 | 정체 검체 seatsOf(3)→(2) · STALL(3,)→STALL(2,) · CHECK(3)→CHECK(2) · 완료 seatsOf(5)→(3) · 제목·주석 3자리→2자리 · 5자리→3자리(모두) | DS-1 | ★3자리(→2자리)에서 180초 정체 · ★정체 알림 뒤 15분 상한 · ★179초는 아직 · ★목록을 못 받은 틱은 정체를 · ★처음 목록을 받은 틱이 기준 · ★× 로 닫았어도 정체 알림 · 정체 알림 뒤 목록이 끊겨 · 삭제 중 탭 정체(제목) · ★목록이 한참 끊겼다가 · 정체 알림 등급·열쇠 |
| ui/src/deptprogresswiring.test.ts | 1768 | 대조 팀 [[100,1],[800,3]]→[[100,1],[800,2]] | DS-1: 3 이면 seated | ★정체 알림 뒤 15분 상한에 닿아도 |
| ui/src/deptprogresswiring.test.ts | 1789-1802 | 늘어남 검체 stuckAt(1) · 1자리→2자리(250초) · STALL(4,)→STALL(2,) · 제목 3→4자리 → 1→2자리 | DS-1: 3→4 늘어남이 3석에선 불가(3=완료) | ★자리 수가 늘면 기준 시각이 밀린다 |
| ui/src/deptprogresswiring.test.ts | 1805-1825 | 줄어듦 검체 3→2/2→3 을 2→1/1→2 로 · STALL(2,)→STALL(1,) · 제목·주석 | DS-1 | 줄어드는 것은 기준을 밀지 않는다 |
| ui/src/deptprogresswiring.test.ts | 1920-1928 | stuckAt(1) · 정체 후 1→2 늘어남 · 제목 (3→4)→(1→2) | DS-1 | 정체 알림 뒤 자리가 늘어도 |
| ui/src/deptprogresswiring.test.ts | 1992-1993 | 수명 만료 되풀이 [[200,2],[330,3],[460,4]]→[[200,2],[300,2],[370,2]] · 주석 보강 | DS-1: 3 이면 완료로 접혀 되풀이 검체가 4회로 줄어듦 · 정체 180초 안에 두어 정체 미개입 | ★토스트가 수명(60초)으로 사라졌고 |
| ui/src/deptprogresswiring.test.ts | 2010-2017 | × 닫은 팀 1 목록 2→3 을 1→2 로 · 주석 | DS-1: 3 이면 seated 최종 안내(× 무관)가 나서 「호출 0」 단언 목적과 섞임 | ★× 로 닫았으면(표식 → dismissToast) 되살리지 않는다 |
| ui/src/deptprogresswiring.test.ts | 2149-2304 | 실제 3초 틱: 붙는 순서 1·2·3·4→1·2 · 1·2·3→1·2(마지막 증가 90초 불변) · 미완 seatsOf(3)/(4)→(2) · 「붙은 자리 3개/4개」→「2개」 · 종료한 master 줄 다섯→세 줄 · 제목·주석 | DS-1 | ★다섯 역할이 붙은 틱(→의무 역할 셋이 모두 붙은 틱) · ★본부 데몬의 좌석 목록이 다섯이어도(→모두 붙어 있어도) · ★그 소켓의 좌석 목록을 못 받은 틱 · ★15분 상한에 다섯이(→셋이 다) 안 붙었으면 · ★(정체 판정) 3자리가(→2자리가) · ★(정체 판정) 정체 알림 뒤 15분 · ★(정체 판정) 목록을 못 받은 틱 |
| ui/src/deptprogresswiring.test.ts | 2440-2450 | roles 5→["master","cso","worker"] · 제목 (다섯이 붙음)→(셋이 모두 붙음) | DS-1 | × 로 닫은 뒤에도 최종 안내(셋이 모두 붙음)는 한 번 난다 |
| ui/src/deptprogresswiring.test.ts | 15·22·404 | 머리 주석·핀 주석 다섯→셋 | DS-1 | (주석) |

### ledger-fix-x18 (3행)

| 파일 | 줄 | 무엇을 | 왜 | 분류 | 적색 시험 |
|---|---|---|---|---|---|
| cysjavis-pack/bin/tests/test_cso_directive_rev.py | 1755-1771 | section_body() 가 코드 펜스(```) 안의 `## ` 줄을 절 경계로 세지 않게 함 | 우리 MASTER §9 「오너용 3절(복원 카드)」 예시 펜스(## 완료·## 진행 중·## 결정 필요)에서 절이 잘려, 같은 §9 안에 1회 있는 WP-6 인계 문장(SYNC)을 절 밖으로 읽은 거짓 적색. 시험 목적(문장이 정확 1회 · 올바른 절) 불변 — 판정 함수가 '펜스 안 제목 없음' 을 전제했다 | (b) 시험 도구 | test_sync_sentence_once_in_correct_sections (MASTER_DIRECTIVE.md) |
| cysjavis-pack/bin/tests/test_cso_directive_rev.py | 390-395 | SAFETY_CLAUSES「선조치 범위」 기대 문면을 원작자 §4 문단 → 우리 §1 표 머리 문장(「접두 목록 밖 명령은 **보류 + master 에 TTL 승인 요청 + 기록**이다(대체 명령·재시도로 우회 금지 · … §1-2 의 오너 채널이 유일한 출구다).」)으로 재핀 | 원작자 문단(384B)은 래칫 때문에 미수용. 같은 안전 의미(목록 밖 = 보류+승인 · 우회 금지 · master 고장 시 §1-2 유일 출구)가 우리 문면에 정확 1회 존재. 잔여: '시스템 위기라도' 한정어는 §5-1 정지 경계에만 있음(diff 문서 기재) | (a) 다른 문면으로 기대값 이동 | test_safety_clauses_are_present_verbatim 외 연쇄(라벨 '선조치 범위' 결측 해소) |
| cysjavis-pack/directives/CSO_DIRECTIVE.md | 12-21·54-56·66-68·80-87·97-101·107-108·298·302-306·355-356·376-377·389-393 | 우리 고유 절(드레인·부서장 좌석 회수·임무 0·5-0·§2 함대 괄호) 설명·사례 압축 + 원작자 (c) 안전 문면 최소 수용(#5·#6·#9 각성 경로 0/탐지 보장 아님 · #7 점검 완료 시각 · #2·#3 구 데몬 폴백·전이 상태 고지 · #1 구판 프로젝트 메모리 · #8 TTL 인지) | master#114e0c71 1번 ⓐ — 래칫 57,368B 안(57,080→57,361B) · 규범 손실 0(대조표 = x18-upstream-diff.md §6) | (c) 수용 | test_cso_directive_rev 22 적색 → 0(73/73 OK) |

## 부록 A — `git diff --stat c08489e7^1 HEAD`(v1.1.7 대비)

```
 .github/workflows/ci-branch.yml                                                         |   786 +-
 .github/workflows/pack-release.yml                                                      |   203 +-
 .github/workflows/release-postprocess.yml                                               |   231 +
 .github/workflows/release.yml                                                           |   388 +-
 .github/workflows/windows-build.yml                                                     |    55 +-
 .github/workflows/windows-health.yml                                                    |   413 +-
 .gitignore                                                                              |     4 +
 1                                                                                       |     8 +
 CLAUDE.md                                                                               |    17 +-
 CONTRIBUTING.md                                                                         |    13 +-
 Cargo.lock                                                                              |    46 -
 Cargo.toml                                                                              |    18 +-
 UPSTREAM_BASE                                                                           |     1 +
 USER-MANUAL.md                                                                          |  1175 +-
 cysjavis-pack/CLAUDE.md.template                                                        |    17 +-
 cysjavis-pack/agents.json                                                               |     7 +-
 cysjavis-pack/bin/cys-dept                                                              |  1651 ++-
 cysjavis-pack/bin/javis_actprobe.py                                                     |    40 +-
 cysjavis-pack/bin/javis_approval_queue.py                                               |     1 +
 cysjavis-pack/bin/javis_boot_node.py                                                    |     1 +
 cysjavis-pack/bin/javis_bootstrap.py                                                    |   574 +-
 cysjavis-pack/bin/javis_briefing.py                                                     |     1 +
 cysjavis-pack/bin/javis_budget.py                                                       |   102 +
 cysjavis-pack/bin/javis_checklist.py                                                    |    11 +-
 cysjavis-pack/bin/javis_compete.py                                                      |     1 +
 cysjavis-pack/bin/javis_completion_guard.py                                             |    55 +-
 cysjavis-pack/bin/javis_cycle_autopilot.py                                              |  1061 +-
 cysjavis-pack/bin/javis_cycle_verifier.py                                               |    14 +-
 cysjavis-pack/bin/javis_dept_migrate.py                                                 |     1 +
 cysjavis-pack/bin/javis_dept_request.py                                                 |     3 +-
 cysjavis-pack/bin/javis_dept_schedule.py                                                |   124 +
 cysjavis-pack/bin/javis_detect.py                                                       |     2 +-
 cysjavis-pack/bin/javis_event.py                                                        |     3 +-
 cysjavis-pack/bin/javis_formation.py                                                    |   814 +-
 cysjavis-pack/bin/javis_guard_register.py                                               |   359 +-
 cysjavis-pack/bin/javis_hud_bridge.py                                                   |   128 +-
 cysjavis-pack/bin/javis_idempotency.py                                                  |    98 +-
 cysjavis-pack/bin/javis_learn.py                                                        |    68 +-
 cysjavis-pack/bin/javis_memory.py                                                       |     1 +
 cysjavis-pack/bin/javis_memory_inject.py                                                |     1 +
 cysjavis-pack/bin/javis_mission.py                                                      |    19 +-
 cysjavis-pack/bin/javis_orchestra.py                                                    |  2323 +++-
 cysjavis-pack/bin/javis_org.py                                                          |   262 +-
 cysjavis-pack/bin/javis_phoenix.py                                                      |  1305 +-
 cysjavis-pack/bin/javis_phoenix_encoding_smoke.py                                       |     1 +
 cysjavis-pack/bin/javis_phoenix_harness.py                                              |     1 +
 cysjavis-pack/bin/javis_phoenix_win_smoke.py                                            |     1 +
 cysjavis-pack/bin/javis_preflight.py                                                    |  5022 +++++++-
 cysjavis-pack/bin/javis_purge_verify.py                                                 |     1 +
 cysjavis-pack/bin/javis_radio.py                                                        |     1 +
 cysjavis-pack/bin/javis_replay.py                                                       |     1 +
 cysjavis-pack/bin/javis_report.py                                                       |   130 +-
 cysjavis-pack/bin/javis_report_gate.py                                                  |   342 +-
 cysjavis-pack/bin/javis_resource_gate.py                                                |  2952 ++++-
 cysjavis-pack/bin/javis_role.py                                                         |  1006 ++
 cysjavis-pack/bin/javis_rsi.py                                                          |  1074 +-
 cysjavis-pack/bin/javis_snapshot.py                                                     |   163 +-
 cysjavis-pack/bin/javis_state_ledger.py                                                 |     1 +
 cysjavis-pack/bin/javis_state_rotate.py                                                 |   192 +
 cysjavis-pack/bin/javis_state_snapshot.py                                               |   115 +-
 cysjavis-pack/bin/javis_task.py                                                         |     1 +
 cysjavis-pack/bin/javis_teamtoken.py                                                    |  1761 +++
 cysjavis-pack/bin/javis_todo_stamp.py                                                   |     1 +
 cysjavis-pack/bin/javis_verdict.py                                                      |    96 +-
 cysjavis-pack/bin/javis_wakeup.py                                                       |   203 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-declined.json                   |     2 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-dept_fallback.json              |     2 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-dept_fallback_failed.json       |     2 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-dept_fallback_gate_pending.json |     2 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-failed-check.json               |     2 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-failed-resource-gate.json       |     2 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-session_error.json              |     2 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-session_error_latched.json      |     2 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-solo_awakening.json             |     2 +-
 cysjavis-pack/bin/tests/fixtures/boot-last-golden/state-team_complete.json              |     2 +-
 cysjavis-pack/bin/tests/fixtures/dormant_team_flow_master_4a.md                         |    49 +
 cysjavis-pack/bin/tests/run_bootstrap_health.py                                         |  2221 +++-
 cysjavis-pack/bin/tests/test_bootstrap_resource_recheck.py                              |   474 +
 cysjavis-pack/bin/tests/test_bootv2_doc_contract.py                                     |    70 +
 cysjavis-pack/bin/tests/test_capgate_hook_shell.py                                      |  1247 ++
 cysjavis-pack/bin/tests/test_capgate_registration.py                                    |  1058 ++
 cysjavis-pack/bin/tests/test_capgate_remeasure_order.py                                 |   125 +
 cysjavis-pack/bin/tests/test_carry_unproven_scope.py                                    |   159 +
 cysjavis-pack/bin/tests/test_content_pins_parity.py                                     |    68 +-
 cysjavis-pack/bin/tests/test_cso_directive_rev.py                                       |  3347 +++++
 cysjavis-pack/bin/tests/test_ctx_divergence.py                                          |   434 +
 cysjavis-pack/bin/tests/test_cysd_accept_emfile.py                                      |   484 +
 cysjavis-pack/bin/tests/test_dept_b11_lock.py                                           |     7 +-
 cysjavis-pack/bin/tests/test_dept_create_progress.py                                    |  1690 +++
 cysjavis-pack/bin/tests/test_dept_name_guard.py                                         |  1055 ++
 cysjavis-pack/bin/tests/test_dept_notice_lane.py                                        |   395 +
 cysjavis-pack/bin/tests/test_dept_schedule_seed.py                                      |    51 +
 cysjavis-pack/bin/tests/test_dept_team_token.py                                         |   584 +
 cysjavis-pack/bin/tests/test_dept_teardown_atomicity.py                                 |    32 +-
 cysjavis-pack/bin/tests/test_formation.py                                               |   746 ++
 cysjavis-pack/bin/tests/test_formation_gate_label.py                                    |    33 +
 cysjavis-pack/bin/tests/test_formation_tick_visibility.py                               |   248 +
 cysjavis-pack/bin/tests/test_hook_launcher_split.py                                     |     7 +-
 cysjavis-pack/bin/tests/test_hook_r34.py                                                |   500 +
 cysjavis-pack/bin/tests/test_hook_timing.py                                             |    10 +
 cysjavis-pack/bin/tests/test_hud_bridge_backoff.py                                      |   213 +
 cysjavis-pack/bin/tests/test_hud_bridge_skew.py                                         |   157 +
 cysjavis-pack/bin/tests/test_inject_context_role_seat.py                                |   497 +
 cysjavis-pack/bin/tests/test_lane_redirect.py                                           |   659 +
 cysjavis-pack/bin/tests/test_phoenix_a3_ps_axis.py                                      |     2 +-
 cysjavis-pack/bin/tests/test_phoenix_f1_production_path.py                              |   221 +
 cysjavis-pack/bin/tests/test_phoenix_fresh_honest.py                                    |   615 +
 cysjavis-pack/bin/tests/test_phoenix_g2_ack_only.py                                     |   329 +-
 cysjavis-pack/bin/tests/test_phoenix_p10_lease_split.py                                 |   273 +
 cysjavis-pack/bin/tests/test_phoenix_r32_restore_budget.py                              |   545 +
 cysjavis-pack/bin/tests/test_phoenix_r4_restore.py                                      |     9 +-
 cysjavis-pack/bin/tests/test_phoenix_v115_owner_token.py                                |     9 +-
 cysjavis-pack/bin/tests/test_phoenix_v115_spawn_settle.py                               |     9 +-
 cysjavis-pack/bin/tests/test_phoenix_w5_windows.py                                      |    38 +
 cysjavis-pack/bin/tests/test_preflight_only_dispatch.py                                 |   143 +
 cysjavis-pack/bin/tests/test_preflight_settings_fifo.py                                 |    98 +
 cysjavis-pack/bin/tests/test_pyseal_census.py                                           |   166 +-
 cysjavis-pack/bin/tests/test_pyseal_negative_specimen.py                                |   646 +
 cysjavis-pack/bin/tests/test_refl_axis_labels.py                                        |   137 +
 cysjavis-pack/bin/tests/test_refl_fleet_argv_owner.py                                   |   117 +
 cysjavis-pack/bin/tests/test_refl_fleet_latch_gen.py                                    |   297 +
 cysjavis-pack/bin/tests/test_refl_inject_context_role_canon.py                          |   167 +
 cysjavis-pack/bin/tests/test_refl_round_lock_ownership.py                               |   318 +
 cysjavis-pack/bin/tests/test_refl_rsi_state_ownership.py                                |   411 +
 cysjavis-pack/bin/tests/test_refl_stagnation_budget_ledger.py                           |   209 +
 cysjavis-pack/bin/tests/test_refl_wakeup_expiry_attribution.py                          |   194 +
 cysjavis-pack/bin/tests/test_report_ctx_axis.py                                         |   290 +
 cysjavis-pack/bin/tests/test_report_gate.py                                             |   224 +
 cysjavis-pack/{ => bin}/tests/test_resource_gate.py                                     |   200 +-
 cysjavis-pack/bin/tests/test_resource_gate_boot_anchor.py                               |   395 +
 cysjavis-pack/bin/tests/test_resource_gate_fleet_cpu.py                                 |   249 +
 cysjavis-pack/bin/tests/test_resource_gate_notify_rule.py                               |   141 +-
 cysjavis-pack/bin/tests/test_review_prompt_verdict_path.py                              |   109 +-
 cysjavis-pack/bin/tests/test_role_authority.py                                          |  1286 ++
 cysjavis-pack/bin/tests/test_role_authority_shell.py                                    |   741 ++
 cysjavis-pack/bin/tests/test_role_authority_triage.py                                   |   408 +
 cysjavis-pack/bin/tests/test_round_stop_reason.py                                       |  1594 +++
 cysjavis-pack/bin/tests/test_session_start_hook.py                                      |   531 +-
 cysjavis-pack/bin/tests/test_session_start_r31.py                                       |   200 +
 cysjavis-pack/bin/tests/test_silentpass_pack_c2.py                                      |   356 +
 cysjavis-pack/bin/tests/test_snapshot.py                                                |    89 +-
 cysjavis-pack/bin/tests/test_state_rotate.py                                            |    44 +
 cysjavis-pack/bin/tests/test_state_snapshot_root.py                                     |   214 +-
 cysjavis-pack/bin/tests/test_t6_injection_policy.py                                     |     4 +
 cysjavis-pack/bin/tests/test_team_create_u16.py                                         |   500 +
 cysjavis-pack/bin/tests/test_teamtoken.py                                               |  1665 +++
 cysjavis-pack/bin/tests/test_teamtoken_hook.py                                          |   948 ++
 cysjavis-pack/bin/tests/test_trust_seed.py                                              |  6260 ++++++++++
 cysjavis-pack/bin/tests/test_trust_seed_reflect.py                                      |   445 +
 cysjavis-pack/bin/tests/test_v113_review_fix.py                                         |     4 +-
 cysjavis-pack/bin/tests/test_v116_phoenix_midrun_tomb.py                                |     9 +-
 cysjavis-pack/bin/tests/test_wakeup_durable_receipt.py                                  |   168 +
 cysjavis-pack/bin/tests/test_wakeup_park_failure.py                                     |   195 +
 cysjavis-pack/bin/tests/test_wp7_gate_triage.py                                         |   302 +
 cysjavis-pack/directives/CEO_CORE.md                                                    |     2 +-
 cysjavis-pack/directives/CEO_TEMPLATE.md                                                |    47 +-
 cysjavis-pack/directives/CSO_DIRECTIVE.md                                               |   345 +-
 cysjavis-pack/directives/MASTER_CORE.md                                                 |     2 +-
 cysjavis-pack/directives/MASTER_DIRECTIVE.md                                            |    47 +-
 cysjavis-pack/directives/RELEASED_MASTER_DIRECTIVE.sha256                               |     6 +-
 cysjavis-pack/directives/REVIEWER_DIRECTIVE.md                                          |    29 +-
 cysjavis-pack/directives/WORKER_DIRECTIVE.md                                            |    43 +-
 cysjavis-pack/hooks/README.md                                                           |    36 +-
 cysjavis-pack/hooks/_lib.sh                                                             |   758 +-
 cysjavis-pack/hooks/actprobe-kill-gate.sh                                               |     1 +
 cysjavis-pack/hooks/appbuild-gate.sh                                                    |     1 +
 cysjavis-pack/hooks/brief-lint-warn.sh                                                  |     1 +
 cysjavis-pack/hooks/commit-memory-nudge.sh                                              |     1 +
 cysjavis-pack/hooks/completion-guard.sh                                                 |     1 +
 cysjavis-pack/hooks/cys-agy-statusline.sh                                               |    16 +
 cysjavis-pack/hooks/cys-hook.sh                                                         |    21 +
 cysjavis-pack/hooks/cys-statusline.sh                                                   |     3 +
 cysjavis-pack/hooks/dept-chat-inject.sh                                                 |     1 +
 cysjavis-pack/hooks/directive-event-inject.sh                                           |     1 +
 cysjavis-pack/hooks/fullauto/50-state-ledger.sh                                         |     7 +-
 cysjavis-pack/hooks/fullauto/owner-active.sh                                            |     1 +
 cysjavis-pack/hooks/fullauto/state-ledger-inject.sh                                     |     1 +
 cysjavis-pack/hooks/fullauto/state-staleness.sh                                         |     1 +
 cysjavis-pack/hooks/grill-arm.sh                                                        |     1 +
 cysjavis-pack/hooks/grill-count.sh                                                      |     1 +
 cysjavis-pack/hooks/grill-gate.sh                                                       |     1 +
 cysjavis-pack/hooks/grill-stop.sh                                                       |     1 +
 cysjavis-pack/hooks/guard.sh                                                            |     1 +
 cysjavis-pack/hooks/inject-background.sh                                                |     1 +
 cysjavis-pack/hooks/inject-context.sh                                                   |   121 +-
 cysjavis-pack/hooks/memory-trigger-inject.sh                                            |     1 +
 cysjavis-pack/hooks/pack-guard.sh                                                       |     1 +
 cysjavis-pack/hooks/pre-dispatch.sh                                                     |     1 +
 cysjavis-pack/hooks/reflect-scan.sh                                                     |     1 +
 cysjavis-pack/hooks/role-bootstrap-legacy.sh                                            |    13 +
 cysjavis-pack/hooks/role-bootstrap.sh                                                   |   269 +-
 cysjavis-pack/hooks/role-capability-gate.sh                                             |  4019 +++++-
 cysjavis-pack/hooks/save-state.sh                                                       |     5 +-
 cysjavis-pack/hooks/serena-nudge.sh                                                     |     1 +
 cysjavis-pack/hooks/session-start.sh                                                    |   408 +-
 cysjavis-pack/hooks/teamtoken-issue.sh                                                  |   304 +
 cysjavis-pack/hooks/test_pre_dispatch.sh                                                |     1 +
 cysjavis-pack/hooks/verify-reminder.sh                                                  |     1 +
 cysjavis-pack/hooks/vibecoding/vibe-distill-nudge.sh                                    |     1 +
 cysjavis-pack/hooks/vibecoding/vibe-doc-sync.sh                                         |     1 +
 cysjavis-pack/hooks/vibecoding/vibe-regression.sh                                       |     1 +
 cysjavis-pack/memory/feedback_autonomous-pilot-mandate.md                               |     6 +-
 cysjavis-pack/round/REVIEWER_VERDICT_CONTRACT.md                                        |    63 +
 cysjavis-pack/schedule.json                                                             |     4 +-
 cysjavis-pack/schemas/verdict_schema.json                                               |     3 +-
 cysjavis-pack/skills/skillscan-semantic/SKILL.md                                        |     2 +-
 cysjavis-pack/skills/vibecoding/SKILL.md                                                |     2 +-
 cysjavis-pack/state/hook-targets.json.example                                           |    29 +-
 docs/CONTROL_CENTER_DESIGN.md                                                           |     2 +-
 docs/DESIGN-factory-reset.md                                                            |    14 +-
 docs/DESIGN-noshutdown-pack-update.md                                                   |    20 +
 docs/GUIDE-empty-surface-KR.md                                                          |     6 +-
 docs/GUIDE-fullauto-cycle-KR.md                                                         |    18 +-
 docs/INSTALL-Windows-KR.md                                                              |     2 +-
 docs/INSTALL.md                                                                         |    29 +-
 docs/RELEASE.md                                                                         |   160 +
 docs/RELEASE_NOTES_0.14.33.md                                                           |   884 ++
 docs/RELEASE_NOTES_0.14.36.md                                                           |   496 +
 docs/RELEASE_NOTES_0.14.37.md                                                           |   177 +
 docs/RELEASE_NOTES_0.14.38.md                                                           |   433 +
 docs/RELEASE_NOTES_0.14.40.md                                                           |   623 +
 docs/RELEASE_NOTES_0.14.41.md                                                           |   612 +
 docs/RELEASE_NOTES_0.14.42.md                                                           |  1070 ++
 docs/RELEASE_NOTES_0.14.43.md                                                           |   754 ++
 docs/WDSI_SUBMISSION.md                                                                 |    64 +
 docs/merge/BACKLOG-118.md                                                               |    10 +
 docs/merge/DECISIONS-PENDING-118.md                                                     |   127 +
 docs/merge/HANDOFF-118-lead.md                                                          |    66 +
 docs/merge/MEASURE-118.md                                                               |    30 +
 docs/merge/RESOLUTION-POLICY-118.md                                                     |    34 +
 docs/noshutdown_verify.py                                                               |    43 +-
 docs/pending_input_e2e/fake_tui.py                                                      |   171 +
 docs/pending_input_e2e/run_e2e.py                                                       |   373 +
 docs/pending_input_e2e/run_recover_e2e.py                                               |   375 +
 scripts/check-no-ioreport-link.sh                                                       |    78 +
 scripts/gen_ceo_template.py                                                             |    41 +-
 scripts/lane-parity-rehearsal.sh                                                        |   743 ++
 scripts/pre-tag-ci-check.py                                                             |   315 +
 scripts/queue_remeasure.py                                                              |   580 +
 scripts/release-gate-gatekeeper.sh                                                      |   132 +-
 scripts/secret-scan.sh                                                                  |    65 +-
 scripts/tests/test_check_no_ioreport_link.py                                            |   147 +
 scripts/tests/test_ci_branch_cysd_step.py                                               |   449 +
 scripts/tests/test_cysd_dispatch_storm_e2e.py                                           |   405 +
 scripts/tests/test_cysd_nofile_e2e.py                                                   |   483 +
 scripts/tests/test_release_postprocess_gate.py                                          |   170 +-
 scripts/tests/test_version_sot_mutation.py                                              |    52 +-
 scripts/verify-release-remote.py                                                        |   201 +-
 scripts/version-check.sh                                                                |    43 +-
 scripts/win-typecheck.sh                                                                |   171 +
 src-tauri/src/feedback.rs                                                               |  1476 ++-
 src-tauri/src/main.rs                                                                   |  6549 +++++++++-
 src/agent_markers.rs                                                                    |   411 +
 src/agy_statusline.rs                                                                   |  1264 ++
 src/bin/cys.rs                                                                          | 68190 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----------------------------------------
 src/bin/cysd/accounts.rs                                                                |  5849 ++++++++-
 src/bin/cysd/alert_route.rs                                                             |  9075 ++++++++++++++
 src/bin/cysd/alerts.rs                                                                  |   286 +-
 src/bin/cysd/analytics.rs                                                               |    95 +-
 src/bin/cysd/approval.rs                                                                |  1328 +-
 src/bin/cysd/boot_supervisor.rs                                                         |   387 +-
 src/bin/cysd/caps.rs                                                                    |    15 +
 src/bin/cysd/channels.rs                                                                |  1096 +-
 src/bin/cysd/cwd_probe.rs                                                               |   341 +
 src/bin/cysd/cycle_jobs.rs                                                              |   793 ++
 src/bin/cysd/d6_probe_tests.rs                                                          |     7 +-
 src/bin/cysd/deadman.rs                                                                 |    83 +-
 src/bin/cysd/delivery.rs                                                                |   908 +-
 src/bin/cysd/events.rs                                                                  |    13 +-
 src/bin/cysd/fdlimit.rs                                                                 |   508 +
 src/bin/cysd/governance.rs                                                              | 34565 ++++++++++++++++++++++++++++++++++++++--------------
 src/bin/cysd/handlers.rs                                                                | 27457 ++++++++++++++++++++++++++++++-----------
 src/bin/cysd/hwmon.rs                                                                   |   461 +-
 src/bin/cysd/main.rs                                                                    |  2109 +++-
 src/bin/cysd/reclaim.rs                                                                 |  1332 ++
 src/bin/cysd/return_absorb_tests.rs                                                     |  1333 ++
 src/bin/cysd/schedule.rs                                                                |  4200 ++++++-
 src/bin/cysd/send_settle_tests.rs                                                       |  1366 +++
 src/bin/cysd/state.rs                                                                   |  7266 ++++++++++-
 src/bin/cysd/team_gate_tests.rs                                                         |   364 +
 src/bin/cysd/team_token_tests.rs                                                        |   454 +
 src/bin/cysd/teamtoken.rs                                                               |   563 +
 src/bin/cysd/usage.rs                                                                   |  4814 +++++++-
 src/bin/cysd/watch_wake.rs                                                              |     2 +-
 src/factory_reset.rs                                                                    |   471 +-
 src/first_run_gates.rs                                                                  |  2479 +++-
 src/inject_guard.rs                                                                     |  1503 ++-
 src/lib.rs                                                                              |  1989 ++-
 src/macos_devtools.rs                                                                   |   781 ++
 src/pack.rs                                                                             |   756 +-
 src/paste_fence.rs                                                                      |   322 +
 src/profile_gate.rs                                                                     |    83 +-
 src/readiness.rs                                                                        |  5655 +++++++--
 src/released_directive_hashes.rs                                                        |    12 +-
 src/submit_probe.rs                                                                     |    17 +
 src/team_spec.rs                                                                        |   566 +
 src/update_launch.rs                                                                    |   717 ++
 src/wire.rs                                                                             |   301 +-
 ui/e2e/dragdrop_gate.py                                                                 |   329 +
 ui/e2e/wsbar_gate.py                                                                    |    30 +
 ui/index.html                                                                           |     2 +-
 ui/src/alertlayer.test.ts                                                               |    18 +-
 ui/src/autoarrange.test.ts                                                              |     7 +-
 ui/src/bun-env.d.ts                                                                     |    11 +
 ui/src/confirmlayer.test.ts                                                             |   149 +
 ui/src/ctxpick.test.ts                                                                  |    73 +
 ui/src/ctxpick.ts                                                                       |    56 +
 ui/src/deptcreate.test.ts                                                               |   141 +
 ui/src/deptcreate.ts                                                                    |   162 +
 ui/src/deptlabel.test.ts                                                                |   345 +
 ui/src/deptlabel.ts                                                                     |   241 +
 ui/src/deptprogress.test.ts                                                             |   631 +
 ui/src/deptprogress.ts                                                                  |   357 +
 ui/src/deptprogressseats.test.ts                                                        |   209 +
 ui/src/deptprogresswiring.test.ts                                                       |  2569 ++++
 ui/src/drainverify.test.ts                                                              |    21 +
 ui/src/drainverify.ts                                                                   |    18 +
 ui/src/droppoint.test.ts                                                                |   207 +-
 ui/src/droppoint.ts                                                                     |    47 +-
 ui/src/expertwiring.test.ts                                                             |   198 +
 ui/src/feedback_u6.test.ts                                                              |   202 +
 ui/src/feedback_u6.ts                                                                   |   146 +
 ui/src/feedbackflow.test.ts                                                             |   279 +
 ui/src/feedbackflow.ts                                                                  |   150 +
 ui/src/feedbackmodal.ts                                                                 |   585 +
 ui/src/feedbacktop.test.ts                                                              |     6 +-
 ui/src/feedbackwiring.test.ts                                                           |   349 +
 ui/src/feedclass.test.ts                                                                |    55 +
 ui/src/feedclass.ts                                                                     |    41 +-
 ui/src/folderaccess.test.ts                                                             |   236 +
 ui/src/folderaccess.ts                                                                  |   210 +
 ui/src/ftdrop.ts                                                                        |    21 +
 ui/src/hiddenpair.test.ts                                                               |   270 +
 ui/src/main.ts                                                                          |  2305 +++-
 ui/src/modalguard.test.ts                                                               |   218 +
 ui/src/modalguard.ts                                                                    |   122 +
 ui/src/permtoast.test.ts                                                                |    16 +-
 ui/src/permwiring.test.ts                                                               |   131 +
 ui/src/probefail.test.ts                                                                |   479 +
 ui/src/probefail.ts                                                                     |   203 +
 ui/src/resetconfirm.test.ts                                                             |    68 +
 ui/src/resetconfirm.ts                                                                  |    51 +
 ui/src/restartplan.test.ts                                                              |   388 +-
 ui/src/restartplan.ts                                                                   |   100 +-
 ui/src/seatbind.test.ts                                                                 |   520 +
 ui/src/seatlayout.test.ts                                                               |   564 +
 ui/src/seatlayout.ts                                                                    |   777 ++
 ui/src/seatsig.test.ts                                                                  |   493 +
 ui/src/seatsig.ts                                                                       |   323 +
 ui/src/sendfailwiring.test.ts                                                           |   116 +
 ui/src/stacking.test.ts                                                                 |   221 +
 ui/src/staleclaims.test.ts                                                              |   114 +
 ui/src/starvednotice.test.ts                                                            |   920 ++
 ui/src/starvednotice.ts                                                                 |   222 +
 ui/src/style.css                                                                        |   192 +-
 ui/src/teamproposal.test.ts                                                             |   215 +
 ui/src/teamproposal.ts                                                                  |   118 +
 ui/src/toastttl.test.ts                                                                 |   113 +-
 ui/src/toastttl.ts                                                                      |    30 +-
 ui/src/transfer.test.ts                                                                 |   332 +
 ui/src/transfer.ts                                                                      |   251 +
 ui/src/uiids.test.ts                                                                    |    35 +
 ui/src/updatenotice.test.ts                                                             |  1483 +++
 ui/src/updatenotice.ts                                                                  |   238 +
 ui/src/updateplan.test.ts                                                               |     4 +-
 ui/src/updateplan.ts                                                                    |     2 +
 ui/src/updatestate.test.ts                                                              |   275 +
 ui/src/updatestate.ts                                                                   |   400 +
 ui/src/updatewiring.test.ts                                                             |   123 +
 ui/src/usagebar.test.ts                                                                 |  1601 +++
 ui/src/usagebar.ts                                                                      |   877 ++
 ui/src/usagewiring.test.ts                                                              |   554 +
 ui/src/wsbar.ts                                                                         |     5 +-
 ui/src/wsusage-null.test.ts                                                             |    14 +-
 ui/src/wswiring.test.ts                                                                 |  1005 +-
 375 files changed, 259799 insertions(+), 47340 deletions(-)
```

## 부록 B — `git diff --stat c08489e7^2 HEAD`(원작자 v0.14.43 대비)

```
 .github/workflows/ci-branch.yml                                               |  166 +++-
 .github/workflows/pack-release.yml                                            |  112 ++-
 .github/workflows/release-publish.yml                                         |  131 ++-
 .github/workflows/release.yml                                                 |  392 ++++++--
 .github/workflows/windows-build.yml                                           |  162 +++-
 .github/workflows/windows-health.yml                                          |   68 ++
 .gitignore                                                                    |    4 +
 CLAUDE.md                                                                     |    7 +-
 Cargo.lock                                                                    |    5 +-
 Cargo.toml                                                                    |    2 +-
 HANDOFF-T2.md                                                                 |   85 ++
 HANDOFF-T3.md                                                                 |  102 ++
 HANDOFF-v112-wake.md                                                          |   76 ++
 HANDOFF-v116-pack.md                                                          |  199 ++++
 README.en.md                                                                  |   18 +-
 README.md                                                                     |   15 +-
 UPSTREAM_BASE                                                                 |    1 +
 USER-MANUAL.md                                                                |   24 +-
 build.rs                                                                      |  109 ++-
 cysjavis-pack/CLAUDE.md.template                                              |    7 +-
 cysjavis-pack/agents.json                                                     |    4 +-
 cysjavis-pack/bin/check_timeline.py                                           |    9 +-
 cysjavis-pack/bin/cys-dept                                                    |  680 ++++++++++---
 cysjavis-pack/bin/grill_gate.py                                               |    8 +-
 cysjavis-pack/bin/javis_actprobe.py                                           |   18 +-
 cysjavis-pack/bin/javis_approval_queue.py                                     |   18 +-
 cysjavis-pack/bin/javis_awaken.py                                             |  400 ++++++++
 cysjavis-pack/bin/javis_backup.py                                             |   72 +-
 cysjavis-pack/bin/javis_boot_node.py                                          |  518 +++++++++-
 cysjavis-pack/bin/javis_bootstrap.py                                          |  130 ++-
 cysjavis-pack/bin/javis_briefing.py                                           |    8 +-
 cysjavis-pack/bin/javis_channel_watch.py                                      |    8 +-
 cysjavis-pack/bin/javis_channels.py                                           |    8 +-
 cysjavis-pack/bin/javis_checklist.py                                          |    8 +-
 cysjavis-pack/bin/javis_cli_probe.py                                          |   12 +-
 cysjavis-pack/bin/javis_compete.py                                            |    8 +-
 cysjavis-pack/bin/javis_completion_guard.py                                   |   50 +-
 cysjavis-pack/bin/javis_ctx_relay.py                                          |  184 ++++
 cysjavis-pack/bin/javis_cycle_autopilot.py                                    |   14 +-
 cysjavis-pack/bin/javis_cycle_verifier.py                                     |    7 +-
 cysjavis-pack/bin/javis_dept_request.py                                       | 2367 +++++++++++++++++++++++++++++++++++++++++++++
 cysjavis-pack/bin/javis_distill.py                                            |    8 +-
 cysjavis-pack/bin/javis_docsdiff.py                                           |   14 +-
 cysjavis-pack/bin/javis_event.py                                              |   38 +-
 cysjavis-pack/bin/javis_fleet_report.py                                       |   13 +-
 cysjavis-pack/bin/javis_formation.py                                          |  503 +++++++++-
 cysjavis-pack/bin/javis_guard_register.py                                     |    4 +-
 cysjavis-pack/bin/javis_hud_bridge.py                                         |   16 +
 cysjavis-pack/bin/javis_idempotency.py                                        |    8 +-
 cysjavis-pack/bin/javis_idle_audit.py                                         |   10 +-
 cysjavis-pack/bin/javis_learn.py                                              |   11 +-
 cysjavis-pack/bin/javis_lock.py                                               |   12 +-
 cysjavis-pack/bin/javis_merge_check.py                                        |    9 +-
 cysjavis-pack/bin/javis_mission.py                                            |   10 +-
 cysjavis-pack/bin/javis_orchestra.py                                          |  291 ++++--
 cysjavis-pack/bin/javis_org.py                                                |  119 ++-
 cysjavis-pack/bin/javis_orient_log.py                                         |    8 +-
 cysjavis-pack/bin/javis_phoenix.py                                            |  902 ++++++++++++++++-
 cysjavis-pack/bin/javis_phoenix_encoding_smoke.py                             |  206 ++++
 cysjavis-pack/bin/javis_phoenix_harness.py                                    |   98 +-
 cysjavis-pack/bin/javis_phoenix_win_smoke.py                                  |  103 +-
 cysjavis-pack/bin/javis_preflight.py                                          |  769 +++++++++++++--
 cysjavis-pack/bin/javis_radio.py                                              |   12 +-
 cysjavis-pack/bin/javis_reap_exited.py                                        |    8 +-
 cysjavis-pack/bin/javis_report.py                                             |    8 +-
 cysjavis-pack/bin/javis_report_gate.py                                        |   18 +-
 cysjavis-pack/bin/javis_resource_gate.py                                      |  155 ++-
 cysjavis-pack/bin/javis_role.py                                               |    5 +-
 cysjavis-pack/bin/javis_rsi.py                                                |    8 +-
 cysjavis-pack/bin/javis_seat.py                                               |  482 +++++++++
 cysjavis-pack/bin/javis_serena_probe.py                                       |    8 +-
 cysjavis-pack/bin/javis_snapshot.py                                           |    8 +-
 cysjavis-pack/bin/javis_state_snapshot.py                                     |   42 +-
 cysjavis-pack/bin/javis_task.py                                               |   16 +-
 cysjavis-pack/bin/javis_txindex.py                                            |    8 +-
 cysjavis-pack/bin/javis_vibecheck.py                                          |    8 +-
 cysjavis-pack/bin/javis_wakeup.py                                             |   10 +-
 cysjavis-pack/bin/tests/fixtures/ceo_directive_shapes.json                    |  821 ++++++++++++++++
 cysjavis-pack/bin/tests/fixtures/dormant_team_flow_master_4a.md               |   49 +
 cysjavis-pack/bin/tests/mut_dept_request.py                                   |  306 ++++++
 cysjavis-pack/bin/tests/run_bootstrap_health.py                               |  370 +++++--
 cysjavis-pack/bin/tests/test_awaken_enter.py                                  |  412 ++++++++
 cysjavis-pack/bin/tests/test_capgate_hook_shell.py                            |    7 +-
 cysjavis-pack/bin/tests/test_ceo_pending_gate.py                              |  364 ++++++-
 cysjavis-pack/bin/tests/test_core_inject.py                                   |  388 ++++++++
 cysjavis-pack/bin/tests/test_cso_directive_rev.py                             |   24 +-
 cysjavis-pack/bin/tests/test_ctx_relay.py                                     |  150 +++
 cysjavis-pack/bin/tests/test_d1_4_orphan_reap.py                              |  280 ++++++
 cysjavis-pack/bin/tests/test_d1_dept_ready_probe.py                           |  287 ++++++
 cysjavis-pack/bin/tests/test_dbg_d3_d11_shared_profile_hooks.py               |  136 +++
 cysjavis-pack/bin/tests/test_dbg_d3_dept_path_precedence.py                   |  138 +++
 cysjavis-pack/bin/tests/test_dbg_d3_f4_answer_classifier.py                   |   75 ++
 cysjavis-pack/bin/tests/test_dbg_d3_f5_dept_intent.py                         |   90 ++
 cysjavis-pack/bin/tests/test_default_fleet_formation.py                       |  829 ++++++++++++++++
 cysjavis-pack/bin/tests/test_dept_b11_lock.py                                 |  250 +++++
 cysjavis-pack/bin/tests/test_dept_creds_seed.py                               |   10 +-
 cysjavis-pack/bin/tests/test_dept_doctrine_v1.py                              |    8 +
 cysjavis-pack/bin/tests/test_dept_name_guard.py                               |  484 +++++++++-
 cysjavis-pack/bin/tests/test_dept_notice_lane.py                              |    5 +-
 cysjavis-pack/bin/tests/test_dept_request.py                                  | 1701 ++++++++++++++++++++++++++++++++
 cysjavis-pack/bin/tests/test_dept_teardown_atomicity.py                       |   12 +-
 cysjavis-pack/bin/tests/test_event_inject.py                                  |  534 ++++++++++
 cysjavis-pack/bin/tests/test_formation.py                                     |  120 ++-
 cysjavis-pack/bin/tests/test_formation_tick_visibility.py                     |    4 +-
 cysjavis-pack/bin/tests/test_hook_timing.py                                   |   82 ++
 cysjavis-pack/bin/tests/test_hud_bridge_unwatched_no_spawn.py                 |  110 +++
 cysjavis-pack/bin/tests/test_inject_context_role_seat.py                      |   32 +-
 cysjavis-pack/bin/tests/test_nowin_captured_spawns.py                         |  137 +++
 cysjavis-pack/bin/tests/test_nowin_periodic_spawns.py                         |  110 +++
 cysjavis-pack/bin/tests/test_phoenix_a3_ps_axis.py                            |  188 ++++
 cysjavis-pack/bin/tests/test_phoenix_c6_reap.py                               |   39 +-
 cysjavis-pack/bin/tests/test_phoenix_e2e_replacement.py                       |  101 +-
 cysjavis-pack/bin/tests/test_phoenix_f1_production_path.py                    |   15 +-
 cysjavis-pack/bin/tests/test_phoenix_g2_ack_only.py                           |  129 ++-
 cysjavis-pack/bin/tests/test_phoenix_r32_restore_budget.py                    |   38 +-
 cysjavis-pack/bin/tests/test_phoenix_r4_restore.py                            |  363 +++++++
 cysjavis-pack/bin/tests/test_phoenix_v115_owner_token.py                      |  128 +++
 cysjavis-pack/bin/tests/test_phoenix_v115_spawn_settle.py                     |  149 +++
 cysjavis-pack/bin/tests/test_phoenix_w2_untomb_fullcycle.py                   |   23 +-
 cysjavis-pack/bin/tests/test_phoenix_w5_windows.py                            |   19 +-
 cysjavis-pack/bin/tests/test_preflight_phase1_checks.py                       |   34 +
 cysjavis-pack/bin/tests/test_preflight_win_hook_launcher.py                   |  241 +++++
 cysjavis-pack/bin/tests/test_py_resolver_clt_stub.py                          |  561 +++++++++++
 cysjavis-pack/bin/tests/test_pyseal_census.py                                 |   17 +
 cysjavis-pack/bin/tests/test_resource_gate_notify_rule.py                     |  319 ++++++
 cysjavis-pack/bin/tests/test_role_authority.py                                |    4 +-
 cysjavis-pack/bin/tests/test_role_bootstrap_hook.py                           |   46 +-
 cysjavis-pack/bin/tests/test_runtime_manifest_parity.py                       |   66 +-
 cysjavis-pack/bin/tests/test_seat_folders.py                                  |  352 +++++++
 cysjavis-pack/bin/tests/test_session_start_hook.py                            |  139 ++-
 cysjavis-pack/bin/tests/test_t6_injection_policy.py                           |  249 +++++
 cysjavis-pack/bin/tests/test_team_create_u16.py                               |    5 +-
 cysjavis-pack/bin/tests/test_teamtoken.py                                     |   34 +-
 cysjavis-pack/bin/tests/test_teamtoken_hook.py                                |   21 +-
 cysjavis-pack/bin/tests/test_trust_seed.py                                    |    5 +-
 cysjavis-pack/bin/tests/test_v113_review_fix.py                               |  172 ++++
 cysjavis-pack/bin/tests/test_v115_dept.py                                     |  762 +++++++++++++++
 cysjavis-pack/bin/tests/test_v116_auto_restore_status.py                      |  119 +++
 cysjavis-pack/bin/tests/test_v116_num_cys_list_compat.py                      |  120 +++
 cysjavis-pack/bin/tests/test_v116_phoenix_midrun_tomb.py                      |  181 ++++
 cysjavis-pack/bin/tests/test_v116_rb1_formation.py                            |  308 ++++++
 cysjavis-pack/bin/tests/test_win_dept_spawn.py                                |  238 +++++
 cysjavis-pack/directives/CEO_CORE.md                                          |   34 +
 cysjavis-pack/directives/CEO_TEMPLATE.md                                      |  192 ++--
 cysjavis-pack/directives/CORE-MIN.md                                          |    7 +
 cysjavis-pack/directives/CSO_DIRECTIVE.md                                     |   83 +-
 cysjavis-pack/directives/MASTER_CORE.md                                       |   28 +
 cysjavis-pack/directives/MASTER_DIRECTIVE.md                                  |  177 ++--
 cysjavis-pack/directives/RELEASED_MASTER_DIRECTIVE.sha256                     |   34 +
 cysjavis-pack/directives/REVIEWER_DIRECTIVE.md                                |    2 +-
 cysjavis-pack/directives/WORKER_DIRECTIVE.md                                  |   29 +
 cysjavis-pack/hooks/_lib.sh                                                   |  218 ++++-
 cysjavis-pack/hooks/actprobe-kill-gate.sh                                     |   17 +-
 cysjavis-pack/hooks/core_inject.py                                            | 1102 +++++++++++++++++++++
 cysjavis-pack/hooks/cys-hook.sh                                               |   10 +
 cysjavis-pack/hooks/dept-chat-inject.sh                                       |   67 ++
 cysjavis-pack/hooks/directive-event-inject.sh                                 |   56 ++
 cysjavis-pack/hooks/fullauto/50-state-ledger.sh                               |    8 +-
 cysjavis-pack/hooks/grill-stop.sh                                             |    1 +
 cysjavis-pack/hooks/guard.sh                                                  |   19 +-
 cysjavis-pack/hooks/inject-background.sh                                      |   58 ++
 cysjavis-pack/hooks/inject-context.sh                                         |    5 +-
 cysjavis-pack/hooks/reflect-scan.sh                                           |    1 +
 cysjavis-pack/hooks/role-bootstrap-legacy.sh                                  |  114 +--
 cysjavis-pack/hooks/save-state.sh                                             |    1 +
 cysjavis-pack/hooks/session-start.sh                                          |  270 +++++-
 cysjavis-pack/hooks/vibecoding/vibe-doc-sync.sh                               |    8 +-
 cysjavis-pack/memory/feedback_autonomous-pilot-mandate.md                     |    2 +-
 cysjavis-pack/round/SESSION_STATE.md                                          |    3 +
 cysjavis-pack/schedule.json                                                   |    4 +-
 cysjavis-pack/skills/dept-by-chat/SKILL.md                                    |   62 ++
 cysjavis-pack/skills/insane-search/engine/executor.py                         |    8 +-
 cysjavis-pack/skills/insane-search/engine/phase0.py                           |   11 +-
 cysjavis-pack/skills/timesfm-forecasting/scripts/check_timesfm.py             |    8 +-
 cysjavis-pack/skills/timesfm-forecasting/scripts/holdout_eval.py              |    8 +-
 cysjavis-pack/skills/transcription/bin/transcribe_channel.py                  |    8 +-
 cysjavis-pack/templates/seat-CLAUDE.md                                        |    6 +
 cysjavis-pack/templates/seat-layout.json                                      |   21 +
 cysjavis-pack/trusted-keys.json                                               |   13 +-
 dist-win/cys-x64.wxs                                                          |    2 +-
 dist-win/cys.wxs                                                              |    2 +-
 docs/117/A1-DESIGN-117.md                                                     |   92 ++
 docs/117/E1-VERSION-CONSUMERS.md                                              |   33 +
 docs/117/HANDOFF-brand.md                                                     |   36 +
 docs/117/HANDOFF-input.md                                                     |  119 +++
 docs/117/HANDOFF-lead.md                                                      |  147 +++
 docs/117/PRECUT-117.md                                                        |  120 +++
 docs/117/SPLIT-117.md                                                         |  118 +++
 docs/117/WIN-CHECK-117.md                                                     |   77 ++
 docs/CONSOLE-FLICKER-R2.md                                                    |  122 +++
 docs/CYSR-BRAND-VERSION.md                                                    |  102 ++
 docs/DARWIN-UPDATER-LEGACY-LANE.md                                            |  117 +++
 docs/DESIGN-dept-by-conversation.md                                           |  175 ++++
 docs/DESIGN-noshutdown-pack-update.md                                         |    5 +
 docs/DESIGN-v116-ceo-directive-hold.md                                        |  181 ++++
 docs/FEEDBACK-MENU.md                                                         |   89 ++
 docs/HANDOFF-A1-2.md                                                          |   96 ++
 docs/HANDOFF-A1-2b.md                                                         |   39 +
 docs/HANDOFF-A1-2c.md                                                         |   77 ++
 docs/HANDOFF-usage-noagy.md                                                   |   79 ++
 docs/HANDOFF-usage-two-accounts.md                                            |  148 +++
 docs/HANDOFF-v110-darwin-update.md                                            |  108 +++
 docs/HANDOFF-v110-integ.md                                                    |  326 +++++++
 docs/HANDOFF-v110-panetitle.md                                                |  310 ++++++
 docs/HANDOFF-v111-drain.md                                                    |   33 +
 docs/HANDOFF-v111-restore.md                                                  |   56 ++
 docs/HANDOFF-v112-restore.md                                                  |   72 ++
 docs/HANDOFF-v113-dept.md                                                     |   84 ++
 docs/HANDOFF-v113-restore.md                                                  |   79 ++
 docs/HANDOFF-v114-dept-fd.md                                                  |   43 +
 docs/HANDOFF-v115-dept.md                                                     |   33 +
 docs/HANDOFF-v115-restore.md                                                  |   88 ++
 docs/HANDOFF-v115r2-daemon.md                                                 |  186 ++++
 docs/HANDOFF-v115r2-pack.md                                                   |  188 ++++
 docs/HANDOFF-v115r2-ui.md                                                     |  157 +++
 docs/HANDOFF-v115r3-d7.md                                                     |  296 ++++++
 docs/HANDOFF-v115r4-dbg.md                                                    |  175 ++++
 docs/HANDOFF-v115r5-t1.md                                                     |   94 ++
 docs/HANDOFF-v115r5-t4f1.md                                                   |  103 ++
 docs/HANDOFF-v116-app-firstrun.md                                             |  183 ++++
 docs/HANDOFF-v116-auto-equalize.md                                            |    7 +
 docs/HANDOFF-v116-ceo-directive-hold.md                                       |  210 ++++
 docs/HANDOFF-v116-exited-banner.md                                            |  157 +++
 docs/HANDOFF-v116-flake-pty.md                                                |  194 ++++
 docs/HANDOFF-v116-integ.md                                                    |  695 +++++++++++++
 docs/HANDOFF-v116-phoenix-e2e.md                                              |  172 ++++
 docs/HANDOFF-v116-rel.md                                                      |  217 +++++
 docs/HANDOFF-v116-restart-toast.md                                            |   86 ++
 docs/HANDOFF-v116-restore-card-producer.md                                    |  162 ++++
 docs/HANDOFF-v116-seat.md                                                     |  202 ++++
 docs/HANDOFF-v116-ui-close.md                                                 |  206 ++++
 docs/HANDOFF-v116-usage.md                                                    |  259 +++++
 docs/INSTALL.md                                                               |   12 +-
 docs/KEY-ROTATION.md                                                          |   94 ++
 docs/RELEASE-ROLLBACK.md                                                      |  143 +++
 docs/RELEASE.md                                                               |   56 +-
 docs/RELEASE_NOTES_1.0.0.md                                                   |   50 +
 docs/RELEASE_NOTES_1.0.1.md                                                   |   67 ++
 docs/RELEASE_NOTES_1.0.2.md                                                   |   53 +
 docs/REVIEW-TRIAGE-A1-2.md                                                    |   92 ++
 docs/SEAT-FOLDERS.md                                                          |  100 ++
 docs/THREAT-MODEL-mission-gate.md                                             |   34 +
 docs/WINTEST-v116-bundle-draft.md                                             |  203 ++++
 docs/agy-verdicts-phoenix-korean-windows-2026-09-08.md                        |   57 ++
 docs/agy-verdicts-phoenix-s3-master-persist-2026-09-08.md                     |  130 +++
 docs/backlog-exited-surface-auto-reap-2026-07-13.md                           |   35 +
 docs/design-layout-persistence-2026-07-20.md                                  |  183 ++++
 docs/design/HANDOFF-v116-num.md                                               |   38 +
 docs/design/surface-display-number.md                                         |  445 +++++++++
 docs/design/surface-display-number.reviews/agy-1R-2026-09-24.md               |    9 +
 docs/design/surface-display-number.reviews/agy-2R-2026-09-24.md               |    4 +
 docs/design/surface-display-number.reviews/agy-4R-2026-09-24.md               |    6 +
 docs/design/surface-display-number.reviews/agy-5R-2026-09-24.md               |    5 +
 docs/design/surface-display-number.reviews/agy-code-1R-2026-09-24.md          |   10 +
 docs/design/surface-display-number.reviews/agy-code-2R-2026-09-24.md          |    7 +
 docs/design/surface-display-number.reviews/agy-ui-1R-2026-09-24.md            |    9 +
 docs/design/surface-display-number.reviews/e2e-cli-2026-09-24.txt             |   39 +
 docs/design/surface-display-number.reviews/e2e-t5-t11-2026-09-24.txt          |   13 +
 docs/design/surface-display-number.reviews/fable-adversarial-1R-2026-09-24.md |   40 +
 docs/design/surface-display-number.reviews/fable-adversarial-2R-2026-09-24.md |   23 +
 docs/design/surface-display-number.reviews/fable-adversarial-3R-2026-09-24.md |   27 +
 docs/design/surface-display-number.reviews/fable-adversarial-4R-2026-09-24.md |   24 +
 docs/design/surface-display-number.reviews/fable-adversarial-5R-2026-09-24.md |   24 +
 docs/design/surface-display-number.reviews/fable-code-1R-2026-09-24.md        |   68 ++
 docs/design/surface-display-number.reviews/fable-code-2R-2026-09-24.md        |   54 ++
 docs/design/surface-display-number.reviews/mutants-daemon-r1-2026-09-24.txt   |   30 +
 docs/design/surface-display-number.reviews/mutants-r2-2026-09-24.txt          |   17 +
 docs/design/surface-display-number.reviews/regression-final-2026-09-24.txt    |   17 +
 docs/design/surface-display-number.reviews/shell-hash-probe-2026-09-24.txt    |   38 +
 docs/diag/win-flicker-probe.ps1                                               |   41 +
 docs/fix-dock-ghost-tile-2026-07-20.md                                        |   61 ++
 docs/impl-pane-title-numbering-2026-07-27.md                                  |  242 +++++
 docs/installer-remedy-proposal-pythonutf8-2026-09-08.md                       |   98 ++
 docs/merge/BACKLOG-118.md                                                     |   10 +
 docs/merge/DECISIONS-PENDING-118.md                                           |  127 +++
 docs/merge/HANDOFF-118-lead.md                                                |   66 ++
 docs/merge/MEASURE-118.md                                                     |   30 +
 docs/merge/RESOLUTION-POLICY-118.md                                           |   34 +
 docs/participant-formation-findings-2026-09-10.md                             |  111 +++
 docs/r2-wip-934.patch                                                         |  101 ++
 docs/rebase-v0.14.10-report-2026-08-02.md                                     |  253 +++++
 docs/rebase-v0.14.27-report-2026-08-28.md                                     |  382 ++++++++
 docs/rebase-v0.14.30-report-2026-09-08.md                                     |  442 +++++++++
 docs/report-cys-release-first-publish-2026-09-09.md                           |  163 ++++
 docs/s3-master-role-not-persisted-findings-2026-09-08.md                      |   91 ++
 docs/s6-windows-autostart-env-capability-2026-09-08.md                        |  111 +++
 docs/upstream-pr-draft-phoenix-korean-windows-2026-09-08.md                   |  302 ++++++
 docs/v116-auto-equalize/DESIGN-v2.md                                          |  103 ++
 docs/v116-auto-equalize/DESIGN.md                                             |   69 ++
 docs/v116-auto-equalize/HANDOFF-v2.md                                         |   59 ++
 docs/v116-auto-equalize/agy-r1.md                                             |    7 +
 docs/v116-auto-equalize/debugpass-v2.test.ts                                  |   86 ++
 docs/v116-auto-equalize/headless-baseline-c4b-c18.txt                         |   10 +
 docs/v116-auto-equalize/headless-c18-v2.txt                                   |   24 +
 docs/v116-auto-equalize/headless-final-v2.txt                                 |   99 ++
 docs/v116-auto-equalize/headless-final.txt                                    |   64 ++
 docs/v116-auto-equalize/mutants-v2.py                                         |   62 ++
 docs/v116-auto-equalize/mutants-v2.txt                                        |   41 +
 docs/v116-auto-equalize/mutants.txt                                           |   31 +
 docs/v116-auto-equalize/mutate.py                                             |   59 ++
 docs/v116-auto-equalize/opus-review/probe.ts                                  |   47 +
 docs/v116-auto-equalize/opus-review/probe2.ts                                 |   28 +
 docs/v116-auto-equalize/replay/replay-run3.txt                                |   12 +
 docs/v116-auto-equalize/replay/replay.ts                                      |   78 ++
 docs/v116-auto-equalize/replay/s1.png                                         |  Bin 0 -> 44323 bytes
 docs/v116-auto-equalize/replay/s4.png                                         |  Bin 0 -> 42432 bytes
 docs/v116-auto-equalize/repro-R1-R3.txt                                       |   14 +
 docs/v116-restart-toast-evidence/DESIGN.md                                    |   69 ++
 docs/v116-restart-toast-evidence/agy-1r.err                                   |    1 +
 docs/v116-restart-toast-evidence/agy-1r.md                                    |   21 +
 docs/v116-restart-toast-evidence/agy-1r.prompt.txt                            |  853 ++++++++++++++++
 docs/v116-restart-toast-evidence/agy-2r.err                                   |    1 +
 docs/v116-restart-toast-evidence/agy-2r.md                                    |   23 +
 docs/v116-restart-toast-evidence/agy-2r.prompt.txt                            |  635 ++++++++++++
 docs/v116-restart-toast-evidence/c17-baseline-adf50d44.txt                    |   10 +
 docs/v116-restart-toast-evidence/c17r-baseline-fd5bf305.txt                   |   13 +
 docs/v116-restart-toast-evidence/gate-9c41830d-summary.tsv                    |   99 ++
 docs/v116-restart-toast-evidence/headless-c17r-fix.txt                        |   22 +
 docs/v116-restart-toast-evidence/headless-c17x-final.txt                      |   13 +
 docs/v116-restart-toast-evidence/headless-c17x-r.txt                          |   14 +
 docs/v116-restart-toast-evidence/headless-final.txt                           |   52 +
 docs/v116-restart-toast-evidence/mutants-result.txt                           |   22 +
 docs/v116-restart-toast-evidence/mutate_rt.py                                 |   86 ++
 docs/v116-ui-evidence/agy-1r.md                                               |   29 +
 docs/v116-ui-evidence/agy-1r.prompt.txt                                       |  448 +++++++++
 docs/v116-ui-evidence/agy-2r.md                                               |    5 +
 docs/v116-ui-evidence/agy-2r.prompt.txt                                       |  291 ++++++
 docs/v116-ui-evidence/agy-3r.err                                              |    0
 docs/v116-ui-evidence/agy-3r.md                                               |    4 +
 docs/v116-ui-evidence/agy-3r.prompt.txt                                       |  420 ++++++++
 docs/v116-ui-evidence/agy-4r.err                                              |    0
 docs/v116-ui-evidence/agy-4r.md                                               |   16 +
 docs/v116-ui-evidence/agy-4r.prompt.txt                                       |  718 ++++++++++++++
 docs/v116-ui-evidence/agy-5r.err                                              |    0
 docs/v116-ui-evidence/agy-5r.md                                               |    7 +
 docs/v116-ui-evidence/agy-5r.prompt.txt                                       |   16 +
 docs/v116-ui-evidence/exited-banner/agy-1r.md                                 |   17 +
 docs/v116-ui-evidence/exited-banner/agy-1r.prompt.txt                         |   97 ++
 docs/v116-ui-evidence/exited-banner/agy-2r.md                                 |   15 +
 docs/v116-ui-evidence/exited-banner/agy-2r.prompt.txt                         |  173 ++++
 docs/v116-ui-evidence/exited-banner/agy-3r.err                                |    0
 docs/v116-ui-evidence/exited-banner/agy-3r.md                                 |    1 +
 docs/v116-ui-evidence/exited-banner/agy-3r.prompt.txt                         |   63 ++
 docs/v116-ui-evidence/exited-banner/c17-baseline-3bc73856.txt                 |   23 +
 docs/v116-ui-evidence/exited-banner/c18-boundary-base-3bc73856.txt            |    9 +
 docs/v116-ui-evidence/exited-banner/c18-boundary-fix.txt                      |    8 +
 docs/v116-ui-evidence/exited-banner/gate/B01-boot-health-verdicts.txt         |  301 ++++++
 docs/v116-ui-evidence/exited-banner/gate/base-3bc73856-D07c-single.txt        |   12 +
 docs/v116-ui-evidence/exited-banner/gate/summary-139ca0d1.tsv                 |   99 ++
 docs/v116-ui-evidence/exited-banner/headless-final-c1-c18.txt                 |   63 ++
 docs/v116-ui-evidence/exited-banner/mutate-exited.txt                         |   17 +
 docs/v116-ui-evidence/exited-banner/mutate-tui-91-rerun.txt                   |  198 ++++
 docs/v116-ui-evidence/exited-banner/opus-adv-1r.md                            |   12 +
 docs/v116-ui-evidence/exited-banner/opus-adv-2r.md                            |    6 +
 docs/v116-ui-evidence/exited-banner/opus-adv-3r.md                            |    7 +
 docs/v116-ui-evidence/exited-banner/shots/base-c17a-1280.png                  |  Bin 0 -> 82882 bytes
 docs/v116-ui-evidence/exited-banner/shots/base-c17a-800.png                   |  Bin 0 -> 80413 bytes
 docs/v116-ui-evidence/exited-banner/shots/base-c17b-1280.png                  |  Bin 0 -> 67231 bytes
 docs/v116-ui-evidence/exited-banner/shots/base-c17e-1280.png                  |  Bin 0 -> 82025 bytes
 docs/v116-ui-evidence/exited-banner/shots/base-c17f-1280.png                  |  Bin 0 -> 51117 bytes
 docs/v116-ui-evidence/exited-banner/shots/base-c18n-420.png                   |  Bin 0 -> 41252 bytes
 docs/v116-ui-evidence/exited-banner/shots/fix-c17a-1280.png                   |  Bin 0 -> 85057 bytes
 docs/v116-ui-evidence/exited-banner/shots/fix-c17a-800.png                    |  Bin 0 -> 82522 bytes
 docs/v116-ui-evidence/exited-banner/shots/fix-c17b-1280.png                   |  Bin 0 -> 71311 bytes
 docs/v116-ui-evidence/exited-banner/shots/fix-c17b2-1280.png                  |  Bin 0 -> 79934 bytes
 docs/v116-ui-evidence/exited-banner/shots/fix-c17b3-1280.png                  |  Bin 0 -> 80943 bytes
 docs/v116-ui-evidence/exited-banner/shots/fix-c17b4-1280.png                  |  Bin 0 -> 57716 bytes
 docs/v116-ui-evidence/exited-banner/shots/fix-c17e-1280.png                   |  Bin 0 -> 84597 bytes
 docs/v116-ui-evidence/exited-banner/shots/fix-c17f-1280.png                   |  Bin 0 -> 54564 bytes
 docs/v116-ui-evidence/exited-banner/shots/fix-c18n-420.png                    |  Bin 0 -> 42425 bytes
 docs/v116-ui-evidence/headless-final.txt                                      |   32 +
 docs/v116-ui-evidence/mutate-exited.py                                        |   78 ++
 docs/v116-ui-evidence/mutate.py                                               |  115 +++
 docs/v116-ui-evidence/shim.js                                                 |  117 +++
 docs/v116-ui-evidence/shots/base-c3-remaining-width.png                       |  Bin 0 -> 50265 bytes
 docs/v116-ui-evidence/shots/base-c4a-beginner.png                             |  Bin 0 -> 53750 bytes
 docs/v116-ui-evidence/shots/c1-close-confirm.png                              |  Bin 0 -> 56695 bytes
 docs/v116-ui-evidence/shots/c3-remaining-width.png                            |  Bin 0 -> 44745 bytes
 docs/v116-ui-evidence/shots/c4a-beginner.png                                  |  Bin 0 -> 48044 bytes
 docs/v116-ui-evidence/shots/c4b-expert-create.png                             |  Bin 0 -> 55953 bytes
 docs/v116-ui-evidence/shots/c6-alert-over-card.png                            |  Bin 0 -> 87705 bytes
 docs/v116-ui-evidence/shots/c8-hq-tab.png                                     |  Bin 0 -> 51508 bytes
 docs/v116-ui-evidence/v116-headless.ts                                        |  996 +++++++++++++++++++
 docs/verdict-pane-title-numbering-2026-07-27.md                               |  275 ++++++
 scripts/build-macos-local.sh                                                  |  106 ++
 scripts/build-macos-signed.sh                                                 |  165 +---
 scripts/bundle-prep.sh                                                        |   16 +-
 scripts/ceo_template_header.md                                                |   15 +-
 scripts/d1_pack_refresh_mutants.py                                            |  193 ++++
 scripts/d9_events_no_daemon_revival.py                                        |  335 +++++++
 scripts/deploy-homepage.py                                                    |    8 +-
 scripts/gen_ceo_template.py                                                   |    4 +-
 scripts/gen_released_directive_hashes.py                                      |  117 +++
 scripts/key-bridge-install.py                                                 |  139 +++
 scripts/lib/mac-bundle-common.sh                                              |  219 +++++
 scripts/lib/place-sidecar.sh                                                  |   19 +
 scripts/make-darwin-update-row.py                                             |  174 ++++
 scripts/make-darwin-updater-tarball.sh                                        |   87 ++
 scripts/make-update-manifest.sh                                               |  115 ++-
 scripts/phoenix_encoding_mutants.py                                           |  132 +++
 scripts/release-gate-gatekeeper.sh                                            |  117 ++-
 scripts/release-postprocess.py                                                |  389 +++++++-
 scripts/release-verify.py                                                     |  673 ++++++++++++-
 scripts/s3_coldboot_probe.py                                                  |  281 ++++++
 scripts/s3_topology_mutants.py                                                |  159 +++
 scripts/secret-scan.sh                                                        |  236 +++--
 scripts/tests/mutants-darwin-update.py                                        |  143 +++
 scripts/tests/nsis-hook-compile/harness.nsi                                   |   12 +-
 scripts/tests/nsis-hook-compile/run.sh                                        |   47 +
 scripts/tests/nsis-hook-model/model.py                                        |   27 +-
 scripts/tests/nsis-template/check.py                                          |  208 ++++
 scripts/tests/test_darwin_asset_name_alignment.py                             |  113 +++
 scripts/tests/test_darwin_update_row.py                                       |  165 ++++
 scripts/tests/test_darwin_updater_tarball.py                                  |   83 ++
 scripts/tests/test_key_bridge_install.py                                      |  120 +++
 scripts/tests/test_mac_cli_alias_link.py                                      |  105 ++
 scripts/tests/test_release_postprocess_gate.py                                |  856 +++++++++++++++-
 scripts/tests/test_release_trigger_split.py                                   |  170 ++++
 scripts/tests/test_release_verify.py                                          | 1288 +++++++++++++++++++++++--
 scripts/tests/test_version_sot_mutation.py                                    |  103 +-
 scripts/v115r4_dbg_mutants.py                                                 |  175 ++++
 scripts/v116_num_e2e.py                                                       |  323 +++++++
 scripts/v116_num_mutants.py                                                   |  230 +++++
 scripts/verify-gatekeeper-user-path.sh                                        |    2 +-
 scripts/verify-release-remote.py                                              |   32 +-
 scripts/version-check.sh                                                      |   32 +
 src-tauri/Cargo.toml                                                          |    6 +-
 src-tauri/Info.plist                                                          |    6 +
 src-tauri/nsis-hooks.nsh                                                      |  113 ++-
 src-tauri/nsis/installer.nsi                                                  | 1011 +++++++++++++++++++
 src-tauri/nsis/tauri-cli-2.11.4-installer.nsi                                 |  977 +++++++++++++++++++
 src-tauri/src/feedback.rs                                                     | 1179 +++++++++++++++++++++-
 src-tauri/src/macupdate.rs                                                    |  674 +++++++++++++
 src-tauri/src/main.rs                                                         | 2503 +++++++++++++++++++++++++++++++++++++++++++----
 src-tauri/tauri.conf.json                                                     |   10 +-
 src-tauri/tauri.dev.conf.json                                                 |    5 +
 src-tauri/tauri.windows.conf.json                                             |    2 +-
 src/bin/cys.rs                                                                | 6010 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--------
 src/bin/cysd/accounts.rs                                                      | 1706 +++++++++++++++++++++++++++++++-
 src/bin/cysd/alert_route.rs                                                   |    3 +
 src/bin/cysd/analytics.rs                                                     |   22 +-
 src/bin/cysd/approval.rs                                                      | 1021 +++++++++++++++++---
 src/bin/cysd/boot_supervisor.rs                                               |  109 ++-
 src/bin/cysd/channels.rs                                                      |   48 +-
 src/bin/cysd/classifier.rs                                                    |  310 +++---
 src/bin/cysd/d6_probe_tests.rs                                                |  327 +++++++
 src/bin/cysd/delivery.rs                                                      |  171 +++-
 src/bin/cysd/governance.rs                                                    | 4100 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 src/bin/cysd/handlers.rs                                                      | 3772 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----------
 src/bin/cysd/main.rs                                                          |  230 ++++-
 src/bin/cysd/named.rs                                                         |  502 ++++++++++
 src/bin/cysd/panetitle.rs                                                     |  723 ++++++++++++++
 src/bin/cysd/pty_test_support.rs                                              |  337 +++++++
 src/bin/cysd/recall.rs                                                        |  289 +++++-
 src/bin/cysd/return_absorb_tests.rs                                           |    6 +-
 src/bin/cysd/schedule.rs                                                      |  349 ++++++-
 src/bin/cysd/send_settle_tests.rs                                             |   45 +-
 src/bin/cysd/state.rs                                                         | 2427 ++++++++++++++++++++++++++++++++++++++++++++--
 src/bin/cysd/team_gate_tests.rs                                               |    8 +
 src/bin/cysd/team_token_tests.rs                                              |   11 +
 src/bin/cysd/testdata/claude_2_1_280_first_run_login_14rows.raw               |   31 +
 src/bin/cysd/testdata/claude_2_1_280_first_run_login_40rows.raw               |   38 +
 src/bin/cysd/testdata/claude_2_1_280_first_run_oauth_14rows.raw               |   60 ++
 src/bin/cysd/testdata/claude_2_1_280_first_run_oauth_40rows.raw               |   67 ++
 src/bin/cysd/testdata/claude_2_1_280_first_run_theme_14rows.raw               |   22 +
 src/bin/cysd/testdata/claude_2_1_280_first_run_theme_40rows.raw               |   38 +
 src/bin/cysd/testdata/claude_2_1_280_folder_trust.raw                         |   19 +
 src/bin/cysd/testdata/claude_2_1_280_permission_classic.raw                   |  134 +++
 src/bin/cysd/testdata/claude_2_1_280_permission_classic_10rows.raw            |  120 +++
 src/bin/cysd/testdata/claude_2_1_280_permission_fullscreen.raw                |    1 +
 src/bin/cysd/testdata/claude_2_1_280_ready_after_esc_classic.raw              |  134 +++
 src/bin/cysd/testdata/claude_askuserquestion_vm_r1001.txt                     |   21 +
 src/bin/cysd/testdata/claude_askuserquestion_vm_r1001_2.txt                   |   12 +
 src/bin/cysd/testdata/fleet_normal_screens/s1021-r1.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1021-r2.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1021-r3.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1021-r4.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1021-r5.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1021-r6.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1023-r1.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1023-r2.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1023-r3.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1023-r4.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1023-r5.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1023-r6.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1025-r1.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1025-r2.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1025-r3.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1025-r4.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1025-r5.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1025-r6.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1027-r1.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1027-r2.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1027-r3.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1027-r4.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1027-r5.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1027-r6.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1028-r1.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1028-r2.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1028-r3.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1028-r4.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1028-r5.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1028-r6.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1029-r1.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1029-r2.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1029-r3.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1029-r4.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1029-r5.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1029-r6.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1030-r1.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1030-r2.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1030-r3.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1030-r4.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1030-r5.txt                       |   68 ++
 src/bin/cysd/testdata/fleet_normal_screens/s1030-r6.txt                       |   68 ++
 src/bin/cysd/testdata/oauth_usage_account_a.json                              |    1 +
 src/bin/cysd/testdata/oauth_usage_account_b.json                              |    1 +
 src/bin/cysd/usage.rs                                                         | 1088 ++++++++++++++++++++-
 src/bin/cysd/watch_wake.rs                                                    |  562 +++++++++++
 src/factory_reset.rs                                                          |  109 ++-
 src/first_run_gates.rs                                                        |  543 ++++++++++-
 src/lib.rs                                                                    | 1121 ++++++++++++++++++++-
 src/pack.rs                                                                   |  973 ++++++++++++++++++-
 src/packsig.rs                                                                |  176 +++-
 src/reinject_guard.rs                                                         |  144 +++
 src/released_directive_hashes.rs                                              |   66 ++
 src/restore_mark.rs                                                           |   95 ++
 src/seat.rs                                                                   |  504 ++++++++++
 src/submit_probe.rs                                                           |  152 +++
 ui/index.html                                                                 |   69 +-
 ui/package.json                                                               |    2 +-
 ui/src/adoptlayout.test.ts                                                    |   76 ++
 ui/src/adoptlayout.ts                                                         |   44 +
 ui/src/alertcopy.test.ts                                                      |  152 +++
 ui/src/alertcopy.ts                                                           |  150 +++
 ui/src/alertlayer.test.ts                                                     |   50 +
 ui/src/altscroll.test.ts                                                      |  231 +++++
 ui/src/altscroll.ts                                                           |  232 +++++
 ui/src/appearance.test.ts                                                     |   81 +-
 ui/src/appearance.ts                                                          |   46 +-
 ui/src/autoarrange.test.ts                                                    |  851 ++++++++++++++++
 ui/src/brandbadge.test.ts                                                     |   71 ++
 ui/src/bun-env.d.ts                                                           |   11 +
 ui/src/clipath.ts                                                             |    4 +-
 ui/src/closeguard.test.ts                                                     |  199 ++++
 ui/src/closeguard.ts                                                          |   51 +
 ui/src/confirmlabel.test.ts                                                   |   22 +
 ui/src/confirmlayer.test.ts                                                   |    8 +-
 ui/src/ctxgroup.test.ts                                                       |   39 +
 ui/src/deptconfirm.test.ts                                                    |   47 +
 ui/src/deptconfirm.ts                                                         |   39 +
 ui/src/deptcreate.test.ts                                                     |   12 +-
 ui/src/deptcreate.ts                                                          |   11 +-
 ui/src/deptlabel.ts                                                           |    2 +-
 ui/src/deptprogress.test.ts                                                   |  104 +-
 ui/src/deptprogress.ts                                                        |   55 +-
 ui/src/deptprogressseats.test.ts                                              |   95 +-
 ui/src/deptprogresswiring.test.ts                                             |  475 ++++-----
 ui/src/deptreg.test.ts                                                        |   29 +
 ui/src/deptreg.ts                                                             |   26 +
 ui/src/drainverify.test.ts                                                    |  191 +++-
 ui/src/drainverify.ts                                                         |   96 +-
 ui/src/evsock.test.ts                                                         |   93 ++
 ui/src/evsock.ts                                                              |   39 +
 ui/src/exitbanner.test.ts                                                     |  147 +++
 ui/src/exitbanner.ts                                                          |   76 ++
 ui/src/exitedsweep.test.ts                                                    |  207 ++++
 ui/src/exitedsweep.ts                                                         |   97 ++
 ui/src/expertmode.test.ts                                                     |   34 +
 ui/src/expertmode.ts                                                          |   28 +
 ui/src/expertwiring.test.ts                                                   |   40 +-
 ui/src/feedback.test.ts                                                       |  271 ++----
 ui/src/feedback.ts                                                            |  228 ++---
 ui/src/feedback_u6.test.ts                                                    |  202 ++++
 ui/src/feedback_u6.ts                                                         |  146 +++
 ui/src/feedbackmodal.ts                                                       |    2 +-
 ui/src/feedbacktop.test.ts                                                    |   47 +
 ui/src/feedbackwiring.test.ts                                                 |   57 +-
 ui/src/folderaccess.ts                                                        |    2 +-
 ui/src/formation.test.ts                                                      |  126 +++
 ui/src/formation.ts                                                           |  419 ++++++++
 ui/src/headerlabels.test.ts                                                   |  140 +++
 ui/src/headerlabels.ts                                                        |   44 +
 ui/src/main.ts                                                                | 4206 ++++++++++++++++++++++++++++++++++++++++++++++++-------------------------------
 ui/src/panetitle.test.ts                                                      |  111 +++
 ui/src/panetitle.ts                                                           |   82 ++
 ui/src/permtoast.test.ts                                                      |   98 ++
 ui/src/placeholderclose.test.ts                                               |   74 ++
 ui/src/placeholderclose.ts                                                    |   57 ++
 ui/src/probefail.test.ts                                                      |    8 +-
 ui/src/restartpending.test.ts                                                 |  207 ++++
 ui/src/restartpending.ts                                                      |   78 ++
 ui/src/restorebrief.producer.test.ts                                          |  247 +++++
 ui/src/restorebrief.test.ts                                                   |  384 ++++++++
 ui/src/restorebrief.ts                                                        |  349 +++++++
 ui/src/scrollfollow.test.ts                                                   |   65 ++
 ui/src/scrollfollow.ts                                                        |   46 +
 ui/src/seatsig.test.ts                                                        |    5 +-
 ui/src/selfdiag.test.ts                                                       |   61 +-
 ui/src/selfdiag.ts                                                            |   50 +
 ui/src/sendfailwiring.test.ts                                                 |    3 +-
 ui/src/staleclaims.test.ts                                                    |    4 +-
 ui/src/starvednotice.test.ts                                                  |   12 +-
 ui/src/starvednotice.ts                                                       |    5 +-
 ui/src/style.css                                                              |  458 ++++++---
 ui/src/teamproposal.test.ts                                                   |   10 +-
 ui/src/toastraw.test.ts                                                       |   58 ++
 ui/src/topbarlabels.test.ts                                                   |   55 ++
 ui/src/updatebutton.test.ts                                                   |   52 +
 ui/src/updatenotice.test.ts                                                   |  211 ++--
 ui/src/updatenotice.ts                                                        |    2 +-
 ui/src/updateplan.test.ts                                                     |   38 +-
 ui/src/updateplan.ts                                                          |   26 +-
 ui/src/updatestate.test.ts                                                    |    3 +-
 ui/src/updatewiring.test.ts                                                   |   22 +-
 ui/src/usagewiring.test.ts                                                    |  150 ++-
 ui/src/wheelgate.ts                                                           |    5 +
 ui/src/wsbar.test.ts                                                          |  396 ++++++++
 ui/src/wsbar.ts                                                               |   54 ++
 ui/src/wsname.test.ts                                                         |   82 ++
 ui/src/wsname.ts                                                              |   52 +
 ui/src/wsreconcile.test.ts                                                    |   80 ++
 ui/src/wsreconcile.ts                                                         |   60 +-
 ui/src/wsusage-null.test.ts                                                   |   78 ++
 ui/src/wsusage.test.ts                                                        |  943 ++++++++++++++++++
 ui/src/wsusage.ts                                                             |  645 +++++++++++++
 ui/src/wswiring.test.ts                                                       |  907 ++++++++++++-----
 627 files changed, 101929 insertions(+), 6621 deletions(-)
```
