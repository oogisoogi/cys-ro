# ★§0 델타 v4 (02:2x · master#eece9156 수리 2차 수용) — 「W 결함 묶음」 후임 입력 · 이 가지(merge/v0.14.43 · 머리 = 이 커밋) 위에서 바로 이어 갈 때 필요한 것만
1. **격리 래퍼**(실 ~/.cys·/Applications 쓰기 0 · EVIDENCE-118 §8): `docs/merge/work/isoenv-lead2.sh` 를 새 세션 스크래치패드로 복사하고 `SB=` 한 줄을 그 경로/sb 로 고쳐 쓴다. TMPDIR 은 짧게 유지(`/private/tmp/claude-501/s118/t` · 소켓 SUN_LEN 103). 팩 측정용은 HOME 도 짧아야 한다 → `/private/tmp/claude-501/s118/pk/isoenv.sh`(SB=/private/tmp/claude-501/s118/pk/sb) 를 쓰거나 같은 꼴로 만든다.
2. **빌드·시험 정확 명령**(cwd = 작업트리 루트 · W=래퍼 경로):
   - 빌드: `$W cargo build -q -p cys-terminal`
   - Rust 전체: `$W cargo test -p cys-terminal --lib --bins` (≈13분 · lib 763/0 · cys 577/0 · cysd 2449/1) · 필터: `$W cargo test -q -p cys-terminal --bin cysd -- <필터>`(lib = `--lib` · cys = `--bin cys`)
   - ui: `cd ui && $W /Users/oogisoogi/.bun/bin/bun test`(6초 · 2807/0 · 레인 81) · 타입: `$W /Users/oogisoogi/.bun/bin/bunx tsc -p tsconfig.check.json`(0) — ui/node_modules = ~/axdev/.wt/cys-117-lead/ui/node_modules 심볼릭 링크(커밋 금지)
   - 팩 전체: `python3 /private/tmp/claude-501/s118/pk/packtests.py <작업트리> "" -<태그>`(≈28분 · 결과 json 은 그 폴더) · 일부: 둘째 인자 = 시험 이름 목록 파일. ⚠측정 산출을 저장소 안(docs/merge/work 포함)에 두지 마라 — test_pyseal_census 스캔이 집어 적색이 된다.
   - 팩 단일: `$W env CYS_PACK_DIR=<빈 임시 폴더> python3 cysjavis-pack/bin/tests/<시험>.py`
3. **휴면-on 레인 켜는 법**(기본 CI 미실행 · BACKLOG B1·B4): ui `CYS_UI_DORMANT_LANE=1`(81건) · 팩 teamtoken D8·D11 `CYS_ENABLE_TEAM_FLOW=1` · 팩 session_start_hook 22·22b master `CYS_DORMANT_LANE=1` — 래퍼 뒤 `env <변수>=1` 로 붙인다. 지금 켜면 그 항목만 적색이 정상(실측).
4. **남은 흔들림 1**: cysd `return_absorb_tests::b_claimed_cross_socket_modal_pair_return_absorbed`(원작자 · 전체 실행 부하 때 `no_agent … bare shell` 전제 실패 · 직전 전체 실행·모듈 3회 초록). 같은 성질로 고친 선례 = state `inject_track_handoff_pending_until_an_arm_ends`(0fdbfa84 · 시간 창 여유). trust_seed(팩)도 전체 실행 때만 적색 1회.
5. **격리 HOME 디버그 데몬 정리법**: 원작자 test_dept_create_progress·test_dept_team_token 이 1회 8~16개를 남긴다. `pgrep -f cys-118-merge/target/debug/cysd` → 각 pid `ps -E -o command= -p <pid>` 에 `HOME=/private/tmp/claude-501/s118/` 가 있는 것만 kill(실 데몬 무접촉 확인 후) → 0 재확인.
6. **CSO 래칫 7B 주의**: CSO_DIRECTIVE.md 57,361B / 상한 57,368B(래칫 완화 금지). 다음 CSO 수정은 같은 절 압축이 먼저다 — 압축 전/후 대조표 docs/merge/work/x18-upstream-diff.md §6 · 디렉티브 수정 규율(합성기 확인 + doc-contract + 변경 줄범위 3줄).
7. **팩 환경 적색 8**(원작자 v0.14.43·우리 v1.1.7 기준판 모두 적색 · 손대지 않음): run_bootstrap_health(시간 초과) · test_bootstrap_chain · test_dept_doctrine_v1 · test_dept_ticket_deficit_zero · test_dept_ticket_request · test_lane_isolation_v1 · test_preflight_phase1_checks · test_verify_gate. 원작자 자체 4: test_dept_create_progress(시간 초과) · test_dept_name_guard · test_dept_team_token(시험 CLI 데몬 소켓 미기동 · 휴면 스위치 무관) · test_session_start_hook 18e.
8. 원장·결정: 리드 원장 docs/merge/work/ledger-fix2-lead.tsv · 결정 = DECISIONS-PENDING-118.md + DECISION-TABLE-118 §0(15행) · 판번 1.1.7 유지(TK-G) · push 0(master 집행).

# ★§0 델타 v3 (01:56 · CTX 48%) — master#114e0c71 결정 9 반영 중
1. 커밋: 0fdbfa84(inject_track 시험 여유) · 3747431a(결정 ②~⑨ 전부). 미커밋 = X18 서브 작업 중(CSO_DIRECTIVE.md · test_cso_directive_rev.py · x18-upstream-diff.md §6) + docs/merge/MERGE-RECORD-118.md(초안) · RESOLUTION-LEDGER-118.md(생성기 docs/merge/work/mkledger.py · 재실행 후 커밋) · BACKLOG-118 B3 행.
2. 현재 계수: Rust lib 763/0 · cys 577/0 · cysd 2449/1(원작자 return_absorb 부하 흔들림 · 모듈 3회 초록) · ui 2807/0 · 레인 81 · tsc 0.
3. 팩: 전체 재측정 진행 중 — /private/tmp/claude-501/s118/pk/run.log(짧은 HOME · packtests.py <WT> "" -full2 → packtests-full2.json). ⚠측정 도중 결정 반영 파일이 바뀌었다 → 끝나면 /private/tmp/claude-501/s118/pk/batch1.txt 7개 + test_cso_directive_rev 재실행(packtests.py <WT> <목록> -b1). 그 뒤 dept_team_token: 재빌드 + CYS_ENABLE_TEAM_FLOW=1.
4. 결정 필요로 올릴 것(새로 생김): ⑤ master 좌석 = 요지 조립기 설계라 「전문 끝까지 읽어라」 줄과 충돌(매 시작 ~9.5만 B Read) → master 22·22b 적색 유지 · 비master 만 적용.
5. 마무리 순서: X18 결과 반영·커밋 → 팩 재실행 → MERGE-RECORD §2 끝 시각·§4-1 기입 → mkledger.py 재생성 → 커밋 → 【확인요청】(머리 3줄 = 성찰·검증·디버깅).

# ★§0 델타 v2 — 후임 리드(수리 2차 후반) (01:2x · 좌석 계정2 · master#398d4463 재브리프)
1. **끝난 것(커밋)**: ff2fc8bd ui(DS-1 3석 결속 · X2-R 가드 · UNW 82 휴면-on 레인 · cysr 문구) · 542c6cf0 Rust(B(a) 창 밖만 강등 · submit_probe 열린 박스 `> ` 오독 수리 = drain_verify 흔들림 · r2f_dm 이음매 · BACKLOG-118).
   ui 기본 레인 = 2800 통과 · 82 레인(CYS_UI_DORMANT_LANE=1) · 적색 1 = X2-W(updatenotice 윈 문안 · master 결정 없음 → 목록) · tsc 0.
2. **진행 중**: Rust 전체(격리 · 스크래치패드 ctest4.log) · X18 서브(test_cso_directive_rev.py 만 조정 · 지침 무수정 · 산출 docs/merge/work/x18-upstream-diff.md · ledger-fix-x18.tsv).
3. **남은 일**: 팩 전체 재측정(packtests.py · 짧은 HOME) · dept_team_token 재빌드+CYS_ENABLE_TEAM_FLOW=1 재측정 · inject_track 흔들림 여부(단독·모듈 3회 초록) · b3_status = 원작자 결함 행 · RESOLUTION-LEDGER-118 · MERGE-RECORD-118 · 【확인요청】.
4. **master 결정 없음 → 목록으로 올릴 것**: X2-W(윈 설치 문안) · test_core_inject(MASTER_CORE/CEO_CORE 해시 재작성) · test_teamtoken D8/D11(휴면 지침 문면) · session_start_hook 22·22b(지침 전문 읽기 줄) · phoenix spawn timeout 90 · 우리 설치 재진입 안내 등급 feed(원작자 watchdog) · CC 게이지 windowView(UNW 레인에 넣음 · 행동 차이) · DS-1 정체/15분 안내가 3석에선 고장 신호에 가까움(문구 결정).
5. 도구: 격리 래퍼 사본 = docs/merge/work/isoenv-lead2.sh(SB 경로 = 이 세션 스크래치패드 · 새 세션이면 고쳐 쓸 것) · 원장 docs/merge/work/ledger-fix2-lead.tsv · ledger-fix-ds1-*.tsv.

# ★§0 델타 — 후임 리드(수리 2차)는 이것부터 (01:1x · master#c6a9de68 · 앞 좌석 CTX ≈58%에서 매듭)
1. **master 결정 6(수리 2차 입력)** — DECISIONS-PENDING-118.md 끝 절 [master#c6a9de68]:
   ① ★DS-1 의무 역할 출처를 우리 편성 정본(3석)에 결속 + 시험 기대값 동반(≈58) — **첫 항목** ② ★B(a) 사용량 = 창 밖 보고만 강등(501edcf2 의 전체 순위를 좁혀라 · D6-1 시험 그대로 초록이어야) ③ B(b) 휴면 스위치 env 유지 + 문서 1줄 ④ X2-R 우리 installingUpdate 가드를 SAC 사전 검사까지 ⑤ UNW ≈80 ui 시험 = 휴면 스위치 켠 상태에서만 도는 격리 묶음(삭제·skip 0) + BACKLOG 「휴면-on CI 레인 = 1.1.9」 1줄 ⑥ X18 = 우리 팩 지침 정본 우선 · 원작자 변경분은 diff 로 BACKLOG 행.
2. **남은 Rust 6**(ctest3.log · 격리 env): drain_verify 흔들림(→ src/submit_probe.rs 마커 오독 수리 후보) · approval r2f_dm(accounts 시험 이음매) · d6_1 2(②로 풀릴 것) · state inject_track_handoff_pending(새 · K17 거부 모드의 S21 표식 상승과 관련 추정) · b3_status = **원작자 결함 행**(원작자판도 적색 · 고치지 말고 분리 기록).
3. **갈래 D 결과(c0a66a3b)**: 대상 팩 32→10 — 결정 대기 3(test_cso_directive_rev = X18 · test_core_inject = MASTER_CORE/CEO_CORE 요약 해시 재작성 · test_teamtoken D8/D11 = 휴면 지침 문면) · 원작자판도 적색 4(dept_create_progress = X-WAIT · dept_name_guard = X-J4 · dept_team_token = 새 빌드 + CYS_ENABLE_TEAM_FLOW=1 로 재측정 필요 · session_start_hook = 「지침 전문 읽기」 줄) · 환경 3(phoenix c6_reap·e2e_replacement·w2_untomb — 격리 HOME 이 길어 소켓 104자 초과 → 짧은 HOME 이면 초록). ⚠팩 시험 전체 재측정은 아직(1회 ≈33분).
4. **함정**: ⓐ 서브에이전트 ≤3 동시(master) · 서브 Bash 에 rm·sh -c/bash -c 꼴 금지(D24 분류기 확인창 → 좌석 교착 → 재기동 · 22:2x 실사고) ⓑ 시험 env 에 CYS_CYS_BIN 이 새면 원작자 시험의 가짜 cys 대신 실 디버그 데몬이 떠 120초 정체 + 고아 데몬(앞 좌석 103+18 정리 · 전부 격리 HOME 확인 후 kill) — 측정 뒤 `pgrep -f cys-118-merge/target/debug/cysd` 로 고아 확인 ⓒ 격리 래퍼 TMPDIR/HOME 은 짧게(소켓 SUN_LEN 103) ⓓ 같은 파일 두 서브 동시 쓰기 금지(갈래 = 파일 소유로 나눔) ⓔ 서브는 git 쓰기 금지 · 리드가 갈래별 커밋 ⓕ 판번 1.1.7 유지(TK-G) · push 0.
5. **진행 판정 계수**: 해소 53분(서브 7기) · 컴파일 5분37초 · 수리 1차 = ui 23분 · Rust B 45분 · 데몬 A 52분 · 팩 D 55분(10분 조기 매듭).

# HANDOFF — 1.1.8 병합 리드 (surface:1275 · TICKET=cysr-118-merge-lead) · 갱신 2026-10-05 22:41:36

## 상태
- 가지 merge/v0.14.43 · `git merge --no-ff --no-commit up/v0.14.43` 진행 중(MERGE_HEAD=77e23215) · 아직 git add 0 · 커밋 0.
- 충돌 표기를 zdiff3 로 다시 꺼냄(`git checkout --conflict=zdiff3`) — 덩어리 수가 merge 기본 표기와 다르다(main.ts 80→85 · handlers 26→97 · cys.rs 46→140, histogram 재병합 55).
- 정책 = docs/merge/RESOLUTION-POLICY-118.md · 갈림·master 결정 = docs/merge/DECISIONS-PENDING-118.md([master#36f48cf7] 22:34 7건 결정 · X14~X17 새 갈림 미상신).
- 277 judge 결정표 = ~/axdev/master/reports/cysr-118-plan/DECISION-TABLE-118.md(📌1·2·5·6·7·8 master 결정 대기) · 보안 REVIEW-D-118.md.
- 서브 원장·보고 = 스크래치패드 /private/tmp/claude-501/-Users-oogisoogi-axdev--wt-cys-118-merge/54666fef-e7a9-4c12-8dda-5515d5d458d5/scratchpad/ledger-*.tsv · report-*.txt(handlers 는 report-handlers-rs.md) · 리드 직접 해소 = ledger-lead.tsv(+판번 파일 ours · .gitignore union · Cargo.lock ours · AA ui: droppoint/restartplan=원작자 · wsreconcile/feedback=우리 · UPSTREAM_BASE).
- 계수: main.ts 24m47s · cys.rs ~28m(중단 제외) · handlers 19m45s · ui 나머지 6파일 4m30s · 팩 27파일 ~28m · CI 10파일 26m.

## 남은 일(브리프 §2 순서)
1. 진행 중 서브 완료 확인: daemon(governance·state·approval) · rust-rest(accounts·schedule·usage·channels·cysd main·boot_supervisor·first_run_gates·lib·factory_reset) · tauri(src-tauri main.rs·feedback.rs) · pack(결정 반영 = 지침 선별·래칫 초록·EXIT12) · judge-audit(읽기 전용 대조 → report-judge-audit.txt).
2. 전 파일 표식 0 확인 → git add(해소 표시) → **측정만**: 격리 env(EVIDENCE-118 §8 env -i 목록) cargo build · cargo test · ui bun typecheck/test · 팩 python 시험 → 적색 목록(원인 3분류)+계수 【진행】 → 수리.
3. 이미 아는 수리 후보: feedbackmodal.ts 타입 실패(X17) · updateplan.ts 원작자 ✓ 배지 자동 병합(우리 updatebutton 시험 0) · wswiring X1/X16 .skip → 우리 동작 기준 수정 · H1 원작자 고정물 14~17 조정(원장 1줄씩) · lane-parity-rehearsal.sh:439 · windows-health.yml:334/366 cargo_filter_count · 시험 락 별칭 · test_phoenix_f1(X-INSEAT)·r4·v115_owner_token.
4. 원장 docs/merge/RESOLUTION-LEDGER-118.md(서브 원장 합본 + 부모별 순효과 2종) · MERGE-RECORD-118.md(정책 §0-2 6항) · 병합 커밋 1 → 【확인요청】.
## 함정
- 서브에이전트 Bash 에 rm·sh -c 꼴 금지(22:2x 분류기 확인창 → 좌석 교착 → 재기동 · master#bd7455b4).
- 실 ~/.cys/pack·/Applications/cys* 쓰기 금지 · 디버그 cys/cysd·cargo test 는 env -i 격리만(셸 env 에 CYS_PACK_DIR=실 팩 · CYS_SEAT_TOKEN 있음).

## 갱신 23:46
- 전 파일 해소·git add 완료(커밋 0) · 컴파일 0 오류(src-tauri 사이드카 제외) · 측정 = docs/merge/MEASURE-118.md · 【진행】【결정필요】 23:45 송신(X17 · 수리 4갈래 계획).
- 기준판 작업트리(측정용 · 스크래치패드): wt-up43(up/v0.14.43 · target 빌드됨) · wt-117(v1.1.7 · 미빌드) — 끝나면 `git worktree remove` 로 정리(rm 금지 아님 · 리드 직접).
- 격리 래퍼 = scratchpad isoenv.sh(TMPDIR 짧게) · 팩 시험기 = scratchpad packtests.py <WT> [이름목록] [태그].
- 분류표 = scratchpad rust-red-classified.tsv · ui-red-classified.txt · pack-red-classified.tsv.
- ui/node_modules = cys-117-lead 의 node_modules 심볼릭 링크(커밋 금지 · info/exclude 등록).

## 갱신 00:57 (수리 1차 · 리드 CTX ≈56%)
- 커밋 사슬: c08489e7 merge → 17f40a9c(C ui) → 501edcf2(B 사용량·CLI·팩 Rust) → 414dc2d4(리드 cfg 2) → 642a10af(A 데몬 입력 계층) → e7e2092f(리드 alert_route). push 0.
- Rust 전체(격리 · ctest3.log): lib 762/0 · cys 576/1 · cysd 2,445/5 = **128 → 6**. 남은 6:
  · tests::drain_verify_delivery_failed_on_wedge — 흔들림(TMPDIR·pid 길이로 마커 `>` 가 줄머리에 떨어져 프롬프트로 오독 · 실화면도 같은 오독 가능 → src/submit_probe.rs 후보)
  · approval r2f_dm — accounts.rs seed_known_ignores_antigravity_dir 가 HOME 만 돌림 → 이음매(with_store_root/test_home::set)로
  · d6_probe_tests d6_1_mixed_statusline… · d6_1_dead_statusline… — 갈래 B 📌5 「전체 순위(OAuth 우선)」 와 우리 D6-1 시험 충돌 · B 결정 필요 (a) 전체 순위 = 패널 최대 ~4분 지연 vs 창 밖 보고만 강등(1줄)
  · handlers b3_status_polling — 원작자판도 적색(손대지 않음)
  · state inject_track_handoff_pending_until_an_arm_ends — 새 적색(K17 거부 모드가 S21 표식을 올리게 바꾼 것과 관련 추정 · 미확인)
- ui(17f40a9c 뒤): tsc 0 · bun 91 실패 = 결정 필요 묶음(DECISIONS 「수리 1차」 절: DS-1 · X2-R · X2-W · UNW ≈80 · cysr 문구).
- 팩: 갈래 D(fix-pack) 진행 중 — 끝나면 커밋(파일 = cysjavis-pack/ · 지침 제외) · 미커밋 팩 변경이 작업트리에 있음.
- 결정 대기(master): X18 CSO 지침 3자 모순 · B(a) 사용량 순위 범위 · B(b) 휴면 스위치 env(CYS_ENABLE_TEAM_FLOW / CYS_ENABLE_AGY_LANE) 유지 · DS-1 · X2-R · UNW 처리 방식.
- 다음 리드가 할 일: D 결과 커밋 → 팩 전체 재측정(packtests.py) → 남은 Rust 6 · 위 결정 반영 → 원장 RESOLUTION-LEDGER-118.md(서브 원장 합본 + `git diff v1.1.7..HEAD --stat` · `git diff up/v0.14.43..HEAD --stat`) · MERGE-RECORD-118.md(정책 §0-2 6항: 소요·충돌 파일·리뷰·CI·회귀) → 【확인요청】.
- 정리 대상: 스크래치패드 기준판 작업트리 wt-up43 · wt-117 → `git worktree remove --force <경로>`(리드 직접 · 서브 금지).

## ★순환 대비(01:00): 스크래치패드는 세션마다 바뀐다 → 서브 원장·보고·분류표·도구 사본 = 작업트리 `docs/merge/work/`(커밋 안 함 · info/exclude · 개인 절대경로가 있어 secret-scan 위험 — 원장 합본 때 경로 지워 docs/merge/RESOLUTION-LEDGER-118.md 로).
- 도구: work/hk.py(덩어리 보기·적용) · work/isoenv.sh(격리 래퍼 — 안의 SB 경로를 새 세션 스크래치패드로 고쳐 쓸 것 · TMPDIR=/private/tmp/claude-501/s118/t 짧게 유지) · work/packtests.py <WT> [이름목록] [태그].
- ui/node_modules = ~/axdev/.wt/cys-117-lead/ui/node_modules 심볼릭 링크(커밋 금지).
