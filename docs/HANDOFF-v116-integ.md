# HANDOFF — cysr 1.1.6 1차 통합(T-REL · T-GATE · T-APP · T-UI) · TICKET=v116-integ-1

- 브리프 = `~/axdev/master/briefs/2026-09-24-v116-integ.md`(맨 아래 「master 결정」 절 우선) · worktree `~/axdev/.wt/cys-v116-integ` · 브랜치 `fix/v116-integ` ← 526325bf(v1.1.5 태그 커밋)
- 좌석 = worker-38(surface:1086) · 모델 Opus 5.5 · effort high(세션 jsonl 실측) · 착수 10:38 KST
- ⛔ git push · 태그 · 드래프트 · 설치본 교체 0(전부 master 게이트) · 판번 bump 0(1.1.5 그대로)
- 작업 도구·로그(저장소 밖) = `~/axdev/.wt/integ-v116-work/` — `extract_gates.py`(ci-branch.yml 에서 게이트 목록 추출) · `run_gates.sh`(같은 러너로 기준선·통합 실행) · `lock_audit.py`(X-7 락 정적 감사) · `mutants_integ.py` · `gates-<라벨>/SUMMARY.tsv·*.log` · `agy/`(의뢰문·판정 원문) · `headless*/`(worktree 밖 사본 빌드)

## 0. 한눈에

| 항목 | 결과 |
|---|---|
| 병합 | 4회 `--no-ff` · 문자 충돌 0 · 최종 병합 트리 = 사전 `merge-tree` 연쇄 트리 9fab15f2 동일 |
| 통합 게이트(병합 직후 e097b5a0) | 기준선 대비 **새 실패 3** — 전부 **묶음 단독 결함**(통합이 만든 것 아님 · 각 묶음 HEAD 단독에서 같은 실패 실측) |
| 통합 수리 | master 판정 뒤 커밋 4개(시험·증거 3 + 제품 문자열 2곳 1) |
| 최종 게이트(1ec6c75f 전량 + f5edeb4c 영향분) | 기준선 대비 새 실패 **0** |
| X-7 | 병렬 cysd 7회 PoisonError **0/7** · 6/7 전건 초록 · 7회째 = PTY 고갈(openpty ENXIO) 7건(다른 계열 · 추가 8회째 초록) |
| 뮤턴트 | 묶음 대표 5 + 수리 검증 4 = **9/9 KILLED** |
| 검증 | agy 1R REJECT → 2R ACCEPT · 3R REJECT → 4R ACCEPT / Fable 1R ACCEPT · 2R ACCEPT → **두 검증자 dry** |
| 맥 arm64 로컬 서명 빌드 | §7 |

## 1. 성찰(9단계)

### 1-1. 병합 설계 직후(10:5x · 병합 전)
| 단계 | 적용 | 이유 1줄 |
|---|---|---|
| 1 철학·원칙 | 적용 | 통합 = 「묶음 단독 초록이 합쳐져도 참」을 증명 · 기준 = 기준선 대비 새 실패 0 + 묶음 시험 재실행 + 뮤턴트 재사살. |
| 2 구체 설계 | 적용 | 순서 = 브리프 제안(T-REL → T-GATE → T-APP → T-UI) 유지 — T-REL 의 시험 락 규약이 먼저 깔려야 T-GATE 병합 직후가 곧 「의미 충돌 후보」 판정 지점 · T-UI 가 가장 커서 main.ts 자동 병합을 마지막 1회로 몰아 원인 국소화. 병합마다 그 묶음 시험 · 4병합 뒤 게이트 전량. |
| 3 의도·영향·변경 | 적용 | 의도 = 「4묶음의 제품 변경을 한 트리에 모으되 어느 묶음의 계약도 바뀌지 않았음을 게이트·시험·뮤턴트로 보인다」 · 교차점 = 자동 병합 4파일(cys.rs · governance.rs · handlers.rs · ui/src/main.ts). |
| 4 설계 결함 재조사 | 적용 · 결함 1 편입 | **T-GATE(2a525e59)는 526325bf 의 후손이 아니다**(분기점 f29bb0a5 · v1.1.5 끝 10커밋 이전) → T-GATE 단독 초록은 그 10커밋과 함께 돈 적 없음 → 병합 직후 T-GATE 시험 재실행 필수. 겹침 파일 = cys.rs 1개 · hunk 영역 비겹침 실측. |
| 5 결정론 치환 | 적용 | 게이트 목록을 손으로 적지 않고 ci-branch.yml 에서 스크립트 추출 · 기준선/통합 같은 러너 · 「새 실패」 = SUMMARY.tsv 대조 · 락 규약 = 스크립트 감사 + 병렬 7회. |
| 6 적대 성찰 | 적용 | 「문자 충돌 0 = 안전」 방어 불가 → 경계 3영역 정밀 디버깅 · 「기준선 적색은 기존」 방어 불가 → 목록 단위 대조(개수 금지 · tsc 7→14 선례) · 병렬 1회 초록은 우연일 수 있음 → 7회. |
| 7 운영자(VM 좌석) 관점 | 적용 | VM 좌석은 이 파일만 읽는다 → 빌드 표는 스크립트 출력 그대로 · 체크리스트에 출처 절 번호. |
| 8 개선점 최종 점검 | 적용 | 넣지 않는 것: 7bfc3ea1(master 제외) · feat/v116-ui-effort · usage-oauth · 가동 중 T-SEAT/T-PACK/T-USAGE/T-NUM · 통합 수리(필요 시 멈추고 【질문】). |
| 9 저장 후 구현 | 적용 | `integ-v116-work/reflect-design.md` 저장 후 병합. |

### 1-2. 완료 전(13:1x)
| 단계 | 적용 | 이유 1줄(바뀐 것) |
|---|---|---|
| 1 | 적용 | 「통합이 만든 결함 0」과 「통합 게이트 초록」은 다른 명제였다 — 묶음 단독 결함 3건이 통합 게이트에서 처음 보였다(각 묶음이 자기 영역 시험만 돌림). **바뀐 것 1**: 보고 명제를 둘로 분리해 적는다. |
| 2·3 | 적용 | 수리는 master 판정 뒤에만 · 커밋 분리(시험 전용 3 · 제품 문자열 1) · 제품 변경 = 역할 승계 고지 문자열 2곳뿐. |
| 4 | 적용 | 치환이 뜻을 잃은 곳 1건을 검증자가 적발(headerlabels 금지어 헛돎) → f5edeb4c. **바뀐 것 2**: 치환 뒤 「입력에서 사라진 토큰을 여전히 금지어로 보는 단언」을 전수 grep. |
| 5 | 적용 | 교차 핀을 파일 전체 contains → 함수 본문 body 줄 정확 일치로(결정론 강화). |
| 6 | 적용 | 방어 불가였던 것: 복제 target 의 빌드 스크립트 산출이 다른 worktree 절대경로를 가리킴(환경 적색 1) · 라이브 좌석 env 가 시험에 새어 고아 데몬 7 → 러너가 env 를 정화. **바뀐 것 3**: 러너 env 정화 · target 오염 9패키지 clean. |
| 7 | 적용 | VM 합본 체크리스트 §10 · 빌드 표 §7. |
| 8 | 적용 | 넣지 않은 것 = §11 곁 항목(perm-warning 옛 문구 · perm-guide 60초 수명 · 첫 실행 판정 이원 · 낡은 주석) — 전부 기록만. |
| 9 | 적용 | 이 파일. |

## 2. 병합 표

| 순 | 묶음 | 브랜치 · HEAD | 병합 커밋 | ACCEPT 근거 | 자동 병합 파일 | 병합 직후 묶음 시험 |
|---|---|---|---|---|---|---|
| 1 | T-REL | fix/v116-rel · e24e2126 | **b3248f1a** | SESSION_STATE.md:306 | — | release gate 76 OK · gen_ceo_template --check GREEN |
| 2 | T-GATE | fix/v116-queue-approval · 2a525e59(526325bf 비후손 · 분기점 f29bb0a5) | **dfca79da** | SESSION_STATE.md:338 | cys.rs · governance.rs · handlers.rs | cysd `qa_`·`force_deliver` 23/0 · cys `trust_`·`queue_deliver_gate` 6/0 · lib `folder_trust`·`agents_json_trust` 4/0 |
| 3 | T-APP | fix/v116-app · eabad70d | **68bce638** | SESSION_STATE.md:472 | — | cys-app `v116_` 7/0 · permtoast 11/0 |
| 4 | T-UI | fix/v116-ui · 3bc73856 | **e097b5a0** | SESSION_STATE.md:425 | ui/src/main.ts | 헤드리스 c1~c16 30/30(통합 번들) |

### 2-1. 통합 수리 커밋(전부 master 판정 뒤)
| 커밋 | 판정 | 내용 | 제품 코드 |
|---|---|---|---|
| **96f3ebe4** | master#10242917 A | H-SECRET-1 — T-UI 시험·증거의 더미 경로 44곳을 스캐너 더미 이름으로(u → user · someone → x · 윈 판 u → x · panetitle 홈 폴더 이름 기대값 동반) + `mutate.py` 실계정 경로 → env `V116_UI_DIR`(기본 = 스크립트 기준 상대) | 0 |
| **aac85f77** | master#3aa7b026 ⑵ | permtoast.test.ts `toMatch` 3곳 → `RegExp.test`(tsc TS2339 신규 3 제거) | 0 |
| **1ec6c75f** | master#3aa7b026 ⑴ + #24673176 | 역할 승계 고지 — 데몬 화면(handlers.rs `seat_takeover_notice`)과 GUI 토스트(alertcopy.ts `roleTakeoverCopy`)가 같은 꼬리 문장 묶음 「이 역할을 새 창으로 옮겨 붙였습니다. 옛 창은 곧 정리됩니다. 전할 말이 남아 있으면 그대로 둡니다.」 · 괄호 0 · cysd 교차 핀 include 대상 main.ts → alertcopy.ts | **문자열 2곳** |
| **f5edeb4c** | agy 3R #2·#3 + Fable 2R ①② 반영 | 교차 핀을 roleTakeoverCopy 함수 본문 body 줄 정확 일치로 · UI 쪽 대칭 핀 · headerlabels 계정명 누출 단언 복원(입력·금지어 = youruser) | 0 |

- ⚠ **증거 사후 경로 중립화(master 조건 ③)**: `docs/v116-ui-evidence/agy-3r.prompt.txt`(치환 전 sha256 `a8b7c243f0f1d991fefb4044695312e41f73690022d7d789ea3613f88aa36a38`) · `docs/v116-ui-evidence/headless-final.txt`(치환 전 `673aed6a037de18e968cd19c0ab4825c9e93cf4f559b1f23977893a92d052138`) — 경로 문자열만 바뀌었고 판정 줄은 동일(원본 = 3bc73856 트리).

## 3. 게이트 — 기준선 대비

게이트 목록 = `.github/workflows/ci-branch.yml` 3잡(macos-rust-pack · boot-health-full · nsis-hook-harness)의 run 단계를 스크립트로 추출(19단계 · 13번 = 실패 판독 전용 → 제외 · 17번 = `brew install nsis` 대신 `makensis -VERSION`) + 보강 3종(X1 `cargo test --bin cysd -- --test-threads=1` · X2 `bun test` · X3 `bunx tsc -p tsconfig.check.json`). 환경 = CYS_* 전부·CLAUDE_CONFIG_DIR 제거 + `CYS_NO_AUTOSTART=1` · `CARGO_TARGET_DIR` = worktree 전용.

| 게이트 | 기준선 526325bf | 병합 직후 e097b5a0 | 수리 뒤 1ec6c75f(전량) | 최종 f5edeb4c(영향분) |
|---|---|---|---|---|
| 01 팩 스위트 레인 대조 | 0 | 0 | 0 | — |
| 02 report_gate N=5 | 0 | 0 | 0 | — |
| 03 선언 파서 파리티 | 0 | 0 | 0 | — |
| 04 팩 시험 묶음(45종 · set -e) | 0 | 0 | 0 | — |
| 05 IG-35 격리군 | 0 | 0 | 0 | — |
| 06~11 (verify_win_crt · 버전 SOT · 릴리스 게이트 그물 · 스캔 파리티 · 불사조 · CEO --check) | 0 | 0 | 0 | — |
| 12 cargo test --bin cys | 285/0 | 288/0 | 288/0 | — |
| 14 cargo test --lib | 534/0 | 538/0 | 538/0 | — |
| 15 cargo test -p cys-app --bins | 165/0 ※ | 172/0 | 172/0 | — |
| 16 boot-health-full | GREEN 149/0/1 | **RED 148/1/1 (H-SECRET-1)** | GREEN 149/0/1 | secret-scan --all clean |
| 18·19 NSIS | 0 · 0 | 0 · 0 | 0 · 0 | — |
| X1 cysd 직렬 | 1044/0 | **1060/1** (v115_seat_takeover…) | 1061/0 | **1061/0** |
| X2 bun | 1112/0 | 1246/0 | 1246/0 | **1246/0** |
| X3 tsc | 오류 7(기존) | **10(+3 permtoast toMatch)** | 7(목록 = 기준선 동일) | **7(동일)** |
- ※ 기준선 15 는 첫 실행이 **환경 적색**(복제 target 의 tauri 계열 빌드 스크립트 산출이 다른 worktree `cys-v115r4-dbg` 등의 절대경로를 가리켜 `app_hide.toml` 부재) → 오염 9패키지(`tauri` · `tauri-plugin-{updater,process,notification}` · `mac-notification-sys` · `ring` · `objc2-exception-helper` · `libsqlite3-sys` · `cys-app`) `cargo clean -p` 뒤 재실행 165/0. release 프로필도 같은 9패키지 `cargo clean --release -p` 뒤 빌드.
- 병합 직후 새 실패 3건이 묶음 단독 결함인 근거(실측): H-SECRET-1 = T-UI worktree(3bc73856)에서 `secret-scan --all` 같은 35건 · X1 = 3bc73856 main.ts 에 핀 문장 0건(cysd 핀은 526325bf 판) · X3 = eabad70d permtoast.test.ts 에 `toMatch` 3건.
- ⚠ 1차 기준선(10:4x)은 **무효** — 좌석 env(CYS_CYS_BIN·CYS_CYSD_BIN 등)가 시험에 새어 test_dept_name_guard 가 설치본 cys·cysd 를 불러 임시 HOME 고아 데몬 7 생성(master#fb0b2e67 A 로 정리 · 7 소멸 · 라이브 데몬 생존 · 16좌석 실측). 이 밀폐 결함은 T-PACK 8f439373 에서 이미 수리됨 — **이 기반(8f439373 미편입)에서 재현한 것**이다. **T-PACK 편입 뒤 기준선 재실행 시 고아 0 을 실측 1줄로 남길 것**(아래 §10 다음 편입 항목).

## 4. 묶음별 신규 시험 · X-7 · 건강 검체

- T-UI 헤드리스 c1~c16: e097b5a0 = 30/30 · 1ec6c75f = 30/30(판정 줄 = headless-final 과 동일) — worktree 밖 사본(`git archive` + node_modules 복제 + `build.sh`)에서 실번들 · chrome-headless-shell 154 · 끝난 뒤 내 크롬 잔존 0 실측.
- T-APP `cargo test -p cys-app v116_` 7/0 · `bun test src/permtoast.test.ts` 11/0.
- T-GATE `cargo test --bin cysd qa_ force_deliver -- --test-threads=1` 23/0(dfca79da 직후).
- T-REL `python3 scripts/tests/test_release_postprocess_gate.py` 76 OK.
- **X-7 판정(병렬 기본 `cargo test --bin cysd` · 1ec6c75f)**:

| 회 | 결과 | PoisonError | 소요 |
|---|---|---|---|
| 1 | 1061/0 | 0 | 77s |
| 2 | 1061/0 | 0 | 79s |
| 3 | 1061/0 | 0 | 75s |
| 4 | 1061/0 | 0 | 74s |
| 5 | 1061/0 | 0 | 65s |
| 6 | 1061/0 | 0 | 60s |
| 7 | 1054/**7** | 0 | 60s |
| 8(f5edeb4c · 추가) | 1061/0 | 0 | 66s |
  - 7회째 7건 = 전부 `openpty failed: Device not configured`(PTY 고갈 · watch_wake 5 · usage 2) — X-7(환경 변수 락 경합)과 다른 계열 · 두 파일 통합 무변경 · 기기 `kern.tty.ptmx_max` 511 · 사후 /dev/ttys 32~34개 · 다른 워커 cargo 시험 동시 가동 중이었음【관측】→ 【추정】 순간 PTY 고갈. 8회째 재현 0.
  - 정적 감사(`lock_audit.py`): 통합 트리 cysd 에서 CYS_PACK_DIR 을 바꾸는 함수 91개 전부 단일 락(`PACK_DIR_ENV_LOCK` · 별칭 QUEUE_/ACL_) 보유 또는 락 보유 호출자만 가짐(헬퍼 2단 추적 — daemon_with_acl ← daemon_auto ← 호출자 20 전부 락). T-GATE 신규 qa_ 13곳 = QUEUE_ENV_LOCK(= 별칭). cys.rs(별도 바이너리 · 락 ENV_LOCK) 33함수 = 락 29 · 락 없음 4 = 자식 Command env 설정 2(프로세스 전역 아님) + 픽스처 2(호출자 21 전부 락).
- 건강 검체(H-CONC-3 포함 전량): §3 16번 행.
- `gen_ceo_template.py --check` GREEN · 팩 시험 = §3 01~11.

## 5. 뮤턴트(통합 뒤에도 시험이 살아 있는가)

| 뮤턴트 | 묶음 | 변경 | 결과 | 죽인 시험 |
|---|---|---|---|---|
| MU-UI | T-UI | `needsCloseConfirm` → 항상 false | KILLED | 닫기 확인 판정 진리표 |
| MU-APP-1 | T-APP | `first_measure_wins` → 매번 다시 잼 | KILLED | v116_snapshot_first_measure_wins |
| MU-APP-2 | T-APP | `prior_install_evidence` 가 온보딩 마커 무시 | KILLED | v116_firstrun_restore_truth_table · v116_prior_install_evidence_units |
| MU-GATE(M1) | T-GATE | approval_pending 에서 화면 축 제거 | KILLED | qa_ 5건(folder_trust · permission_dialog_cursor_drift 등) |
| MU-REL | T-REL | zip 속 exe 판독 불가(None) → 일치로 접음 | KILLED | test_65_crosscheck_unit_contract |
| MU-FIX-1 | aac85f77 | main.ts finally 의 `dismissToast("perm-guide")` 제거 | KILLED | permtoast 「권한 창이 끝나면 안내를 내린다」 |
| MU-FIX-2 | 1ec6c75f | GUI 꼬리 한 구절 변경 | KILLED | cysd v115_seat_takeover… |
| MU-FIX-3a | f5edeb4c | 옛 문장을 주석으로 남기고 body 만 변경 | KILLED | cysd v115_seat_takeover…(종전 contains 핀이면 생존했을 형태) |
| MU-FIX-3b | f5edeb4c | 같은 변경 | KILLED | bun alertcopy 2건 |
- 하네스 = `integ-v116-work/mutants_integ.py`(파일 원본 복원 + 복원 대조 · 끝난 뒤 git status clean 실측).

## 6. 정밀 디버깅(통합 경계 3영역)

| 영역 | 방법 | 결과 |
|---|---|---|
| ① 첫 실행 — T-APP 권한 안내 토스트 ↔ T-UI 알림 층·복원 카드 | 코드 대조(start() · stickyToast/toastTimerPlan · briefTiming/isFirstLaunch · 백엔드 폴백) + **헤드리스 변형 3칸**(shim 에 `folder_access_guide_needed`·`request_folder_access` 흉내 추가 · 저장소 밖 · b1-firstrun.ts) | B1 진짜 첫 실행 = 안내 먼저(맨 위·화면 안) → 권한 확인 1회 → 끝나면 안내 내려감 · 복원 카드 0 **PASS** / B2 어긋남(백엔드 = 첫 실행 · UI 저장본 있음) = 카드와 안내가 함께 떠도 안내가 맨 위 **PASS** / B3 첫 실행 아님 = 안내 0 · 권한 확인 호출 0 **PASS** · P3 기록 3(§11) |
| ② 의미 충돌 후보(T-GATE 신규 시험 ↔ T-REL 시험 락) | 정적 감사(§4) + 병렬 7(+1)회 | 결함 0 |
| ③ 용어 — T-UI 「엔진」·alertcopy ↔ T-APP 권한 안내 | T-APP 사용자 문자열 전수(Info.plist 2키 · perm-guide 본문 · eprintln/emit) grep | 데몬·daemon·팩 0 · 충돌 0 · P3 기록 1(거절 뒤 perm-warning 옛 문구 · §11) |
- 「어디까지 뒤졌나」: 파일 정독 14(ui/src/main.ts 3구간 · restorebrief.ts · toastttl.ts · alertcopy.ts · closeguard.ts · src-tauri/src/main.rs 4구간 · handlers.rs 3구간 · governance.rs 2구간 · cys.rs 2구간 · secret-scan.sh · ci-branch.yml · release.yml · 헤드리스 하네스·shim) · 경로 11(진짜 첫 실행 · 어긋남 2방향 · 재실행 · rAF 정지 → 60초 폴백 · 거절 → perm-warning · 권한 창 60초+ 대기 · 승계 고지 데몬/GUI · CYS_PACK_DIR 설정 91함수 · cys.rs 33함수 · 자동 병합 hunk 4파일) · 명령 ≈ 60회(grep·git diff/show·python 감사·헤드리스 4회·게이트 3회) · 검증자 2종 6라운드.

## 7. 맥 arm64 로컬 서명 빌드(T-APP HANDOFF §7-1 절차 그대로)

- 명령(요지): worktree 루트에서 CYS_* 제거 + `CYS_NO_AUTOSTART=1` · 서명 키 = §7-1 방식 env(`TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/cys-updater-A2.key)"` · 비밀번호 빈 값 · 키 파일 복사·출력 0 · 빌드 로그에 키 문자열 0건 실측) → `scripts/build-macos-local.sh aarch64 ~/axdev/.wt/out-mac-v116-integ/` · rc 0 · 13:03~13:07.
- 빌드 트리 = **f5edeb4c**(수리·보정 포함 최종 HEAD · 이 HANDOFF 커밋 직전) · 판번 1.1.5 그대로 · 업로드 0.
- 사전 조치: release 프로필 복제 target 오염 9패키지 `cargo clean --release -p`(§11 ⑥).
- 스크립트 끝 표(그대로):

| 파일 | 크기(B) | sha256 | CDHash |
|---|---|---|---|
| cysr-macos-arm64-v1.1.5.zip | 207857241 | 2dcca007c137cdb343a9914f72e92d568d24c3e0b192af61403d205e98d8b682 | d615fe2cacf9d180e95bc0666c81e04d0fd5d986 |

- 확인: 빌드 로그 「== 동봉 런타임 준비(aarch64-apple-darwin) ==」 1줄 · zip 속 `Resources/pack.tar.gz` 2942335B · `pack-manifest.json` 53455B · `codesign --verify --deep --strict` 통과(cys-local 자체서명 · 공증 없음) · runtime-manifest digest eb911d0e09a0cf18.
- ⚠ 이 HANDOFF 커밋(문서만)으로 HEAD 가 한 칸 전진한다 — 제품 트리는 빌드 트리와 같다(`git diff f5edeb4c HEAD --stat` = docs 1파일).

## 8. 검증

| 라운드 | 대상 | 판정 | 처리 |
|---|---|---|---|
| agy 1R | e097b5a0(병합 표 · 자동 병합 hunk · main.ts 경계 · 게이트 목록 전문 · 락 감사) | REJECT 4 | #1 숨김 창 rAF → 기각(IIFE 비대기 · 60초 백엔드 폴백 · T-APP 수용 한계 ⑶) · #2 deliver_queued 의미 충돌 → 기각(T-REL governance 변경 = cfg(test)뿐) · #3 게이트 공백 → 사실 부분 수용(ci-branch 에 cysd·bun·tsc·헤드리스 없음 · release.yml 에 cysd·bun 있음) · 로컬 보강으로 메움 · #4 감사 범위 → cys.rs 로 확장 · 결함 0 |
| agy 2R | 위 판정표 | **ACCEPT**(4건 철회) | — |
| Fable 1R | e097b5a0(읽기 전용) | **ACCEPT** · 게이트 공백 P2 1 · P3 3 | 전부 §11 기록 |
| agy 3R | 수리 3커밋 | REJECT 3 | #1 증거 사후 수정 → 기각(master 판정 · sha256 기록 · 원본 3bc73856) · #2 headerlabels 헛토큰 → 수용 · #3 파일 전체 contains 핀 → 수용 (f5edeb4c) |
| Fable 2R | 수리 3커밋(읽기 전용) | **ACCEPT** · P3 2(#2 와 같은 헛토큰 · UI 쪽 꼬리 핀 부재) | 수용(f5edeb4c) |
| agy 4R | f5edeb4c + #1 반박 | **ACCEPT**(3건 철회 · 신규 0) | — |
- 수렴 = 서로 다른 검증자 둘 다 마지막 라운드 ACCEPT · 신규 지적 0. 정직 고지: Fable 은 f5edeb4c(자기 P3 제안의 반영)를 따로 보지 않았다 — agy 4R 이 그 diff 를 봤다.

## 9. 4군 점검
- ①폭주 큐: T-GATE 관문·배달 변경 뒤 큐 보류/방출 계약 = 통합에서도 그대로 — qa_·force_deliver 23/0(병합 직후) · cysd 전건 직렬 1061/0 · 병렬 8회 PoisonError 0 · 뮤턴트 M1(화면 축 제거) KILLED(qa_ 5건).
- ②무clear 100%+: 이 통합에 좌석 출생 CTX 를 바꾸는 변경 없음(T-SEAT 미편입 · 4묶음·수리 커밋 diff 에 좌석 출생·CTX 경로 0).
- ③자가치유 전멸: T-APP 갱신 레인 Apply 대조군(진리표 행 3·4 = 「갱신(스탬프 = 구판)」·「갱신(인앱 마커)」 → Apply) = v116_firstrun_restore_truth_table 초록 · 뮤턴트 MU-APP-2 KILLED · 복원 경로 = cysd 전건 · 헤드리스 c5·c11(복원 카드) 초록.
- ④전 pane 사망: T-UI 닫기 확인·exited 청소 술어 = 「exited 확정만」 불변(헤드리스 c1e·c2·c3 · 뮤턴트 MU-UI KILLED) · 산 창을 닫는 새 경로 0(수리 커밋은 문자열·시험만). 윈 설치파일 = T-APP 맥 전용 cfg · 이 기기에 윈 툴체인 없음 → 윈 빌드는 push 뒤 CI(windows-build 가 fix/** 트리거 · push = master 게이트).

## 10. 다음 편입 순서 · VM 합본 체크리스트 초안

### 10-1. 다음 편입(master 10:03 판정 · SESSION_STATE.md:228) = **T-USAGE → T-PACK → T-NUM** · T-SEAT 자리 = master 지정
- 편입마다: 같은 러너(`run_gates.sh`)로 게이트 전량 + `secret-scan --all`(master 참고: T-NUM `fix/v116-num-ui` 42596ebf 는 fix/v116-ui 위라 **옛 더미 경로를 물려받는다** — panetitle.test.ts 에서 충돌 가능 · 이 브랜치의 치환 규칙 u → user · someone → youruser/x 로 맞출 것).
- **T-PACK 편입 뒤**: 기준선 재실행에서 고아 데몬 0 실측 1줄(8f439373 의 시험 밀폐 · §3 ⚠).
- 7bfc3ea1(사용량 거짓 흐림) = master 제외 결정 · T-USAGE 평가 뒤 2차 통합.

### 10-2. VM 합본 체크리스트 초안(이 빌드 = §7 산출물로)
- **T-APP §7-3 S1~S6**(출처 = `~/axdev/.wt/cys-v116-app/docs/HANDOFF-v116-app-firstrun.md` §7): S1 설치 직후 첫 실행 = 「직원 복귀」 토스트 0 · 복원 카드 0 · `cys restore --include-master` 0 · 스탬프·온보딩 마커 = 1.1.5 · `.pending-restore` 없음 / S2 권한 창 = 안내 토스트 먼저 → 약 1.5초 뒤 데스크탑 창 → 문서 창 · 창 안 문장 · 답하면 안내 사라짐 · 「백엔드 폴백 nudge」 로그 없음 / S3 [허용 안 함] clone = perm-warning 원인 토스트 · 좌석 생존 / S4 재실행 = 안내·권한 창·복원 0 / S5 대조군 `echo 1.1.4 > ~/.cys/.last-app-version` → 「직원 복귀 중 → 완료」 · 스탬프 전진 / S6 Cmd+R 안내 재등장 0.
  - (이 통합이 더한 관찰 1) S3 에서 거절 뒤 뜨는 perm-warning 문구가 「pane · EPERM · cysr」 옛 원문임을 캡처로 확인(§11 ⑴ — 고칠지 master 판정).
  - (관찰 2) S2 에서 첫 권한 창을 60초 넘게 둔 뒤 둘째 창 때 안내 토스트가 이미 사라졌는지(§11 ⑵).
- **T-UI X-1**: 창 2개 중 1개 종료 → 남은 창의 cols = 창 전체 폭(`stty size` 로 실측 · 헤드리스 흉내 = 66 → 134).
- **역할 승계 고지(이 통합 1ec6c75f)**: 좌석 승계가 일어나면 옛 창 화면 = 「[cys] 이 좌석이 쥐고 있던 '<역할>' 역할 안내: 옛 창이 비어 있어 이 역할을 새 창으로 옮겨 붙였습니다. 옛 창은 곧 정리됩니다. 전할 말이 남아 있으면 그대로 둡니다.」 · GUI 토스트 = 「<N번 창>이 비어 있어 …」 같은 꼬리.
- **T-PACK §6 10항목**(T-PACK 편입 뒤 · 출처 = `~/axdev/.wt/cys-v116-pack/HANDOFF-v116-pack.md` §6): ① 새 clone · 부서 3 · 저부하/고부하 재부팅 각 1 ② 부서 소켓 `cys status --json` = 역할별 1자리 · worker-2 0 · 홈 cwd 좌석 0 · claude 12 ③ evrec 데몬 기동 뒤 surface.created 는 복원 caller 에서만 · claude 좌석 claim_denied 0 ④ daemon.auto_restore running → done · 편성 partial:restoring → 다음 틱 complete ⑤ 미뤄진 부서는 cys-dept launch 로 켜짐 ⑥ 부서장 ping 즉시 도착 · queue.held empty_seat 0 ⑦ 되살림 사람 말 1줄 · 이상 알림 0 ⑧ 워커 kill -9 → 데드맨 회수 → 새 워커 → 옛 빈 셸 회수 + 「빈 창 정리」 1 · 다른 좌석 닫힘 0 ⑨ 재부팅 2회째 여분 누적 0 ⑩ 복원 진행 중 close-surface → 그 역할 재기동 0 · 묘비 유지 · tombstoned_mid_run_roles.
- 빈칸(정직): x64 = VM 실기 불가 · 윈 = push 뒤 CI 아티팩트(미서명 setup.exe)로만.

## 11. 정직 고지 · 미결 · 곁 항목(전부 기록만 · 수리 0)
1. (P3 · 용어) 첫 실행에서 폴더 권한을 거절하면 친절한 안내(perm-guide) 뒤에 526325bf 원문 perm-warning 토스트(「pane 안의 claude 등이 EPERM으로 꺼질 수 있습니다 … cysr을 허용한 뒤 …」)가 뜬다 — T-UI 사람 말 정비(c14 7종) 범위 밖 · permtoast.test.ts 가 그 원문을 핀. 고치면 핀도 함께.
2. (P3 · 수명) perm-guide 스티키 토스트는 `PROGRESS_STICKY_IDS` 밖이라 60초 뒤 사라진다(toastttl.ts STICKY_TTL_MS) — 첫 권한 창을 60초 넘게 두면 둘째 창 때 안내가 없다.
3. (P3 · 판정 이원) 「첫 실행」 사실이 둘(백엔드 = GUI 온보딩 마커 + 부서 레지스트리 · UI = 화면 배치 저장본). ⒜ `~/.cys` 만 지운 기기 = 백엔드 첫 실행 + UI 카드 「다시 켜졌어요」(T-APP 수용 · 헤드리스 B2 로 겹침 무해 확인) ⒝ 역방향(마커 있음 · 웹 저장소 비움) = 복원은 도는데 카드 0 — 어느 문서도 안 다룸.
4. (P3 · 낡은 주석) `ui/src/restorebrief.ts` isFirstLaunch 머리 주석 「새 설치도 백엔드는 … 갱신으로 보고 복원을 돌리므로」 — T-APP 편입으로 사실이 아니게 됨.
5. (P2 · 게이트 공백 · 구조) ci-branch.yml 에 `cargo test --bin cysd`·bun·tsc·헤드리스가 없다(release.yml 에 cysd·bun 있음 · tsc·헤드리스는 어느 워크플로에도 없음). 이번 결함 3건 중 2건(cysd 승계 핀 · tsc)이 이 공백 탓에 묶음 단계에서 안 보였다 【추정 · 강】. 레인 확장은 범위 밖 제안.
6. (환경) 복제 target(`cp -c -R`)은 빌드 스크립트 산출에 원본 worktree 의 절대경로를 품는다 — 원본 worktree 의 target 이 정리되면 tauri 계열 빌드가 깨진다. 복제 뒤 `grep -r --include=output '/axdev/.wt/'` 로 다른 worktree 경로를 가리키는 패키지를 `cargo clean -p`(debug·release 각각) 할 것.
7. (환경) 좌석 셸의 CYS_* env 가 시험에 새면 설치본 바이너리를 부른다 — 게이트는 CYS_* 전부 제거 + `CYS_NO_AUTOSTART=1` 로(T-PACK 8f439373 편입 뒤엔 시험 자체가 격리).
8. R1a = 읽기 경로만(생산자 0 = 사용자 효과 0) — 「완료 아님」 유지(T-UI).
9. `handlers.rs` announce_seat_takeover 위 문서 주석 「②구 좌석 화면의 셸 주석 1줄」은 v115 이전 서술로 이미 낡음(Fable 부기 · 이번 소관 아님).
10. master#3aa7b026 은 원장 제출 판정 = queued(12:22:16) — 입력줄 도착은 확인 · 뒤이은 #24673176 이 같은 결정을 확정.

## 12. 재현
```bash
W=~/axdev/.wt/integ-v116-work
$W/run_gates.sh <라벨>                        # ci-branch 3잡 + 보강 3 · 결과 = $W/gates-<라벨>/SUMMARY.tsv
python3 $W/lock_audit.py .                    # X-7 규약 정적 감사(worktree 루트)
python3 $W/mutants_integ.py                   # 뮤턴트 5(묶음 대표)
bash scripts/secret-scan.sh --all             # H-SECRET-1 사전 확인
```

---

## 13. git push 기록(master#46d1d297 · 불변식 5 2단계)
- ① master#a7483471(ACCEPT + push 지시) → ② 【실행직전확인요청】 13:42:43 → ③ master#4eed87a8 = 원장 제출 판정 queued 라 **실행 보류·질의** → master#46d1d297 재발신(submitted yes · 13:44:46) → ④ 실행.
- 명령(정확히 1개): `/usr/bin/git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push origin adf50d44ea3f3a5e23aef433ba70972d04f485c1:refs/heads/fix/v116-integ` → rc 0 · [new branch].
- 사후 실측: ls-remote `fix/v116-integ` = adf50d44(일치) · main 무접촉 · 키체인 github.com 항목 수 전 1 = 후 1 · 저장소·전역 credential.helper 무변경.
- 발화 런(headSha adf50d44): ci-branch 35956973252 · windows-build (feasibility) 35956973262 · windows-health (H-WIN 실기) 35956973266 — 결과는 【진행】 보고.

## 14. D 제안 글 끄기 편입(master#4d497471 · 1.1.6 범위 추가 = master 판정)
- cherry-pick -x(feat/chat-ui-v1): c644c448 → **d7ec7b9b**(cysjavis-pack/agents.json 클로드 어댑터 env 에 `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false`) · 99dcbbfd → **9fdf06a0**(cys.rs 핀 `claude_adapter_env_disables_prompt_suggestion` — 임베드 팩 env 에 그 쌍 + CLAUDE_CONFIG_DIR 유지). 충돌 0.
- 성찰(짧게) = `integ-v116-work/reflect-D.md`(9단계 · 도달 범위 고지 1).
- 영향 게이트(9fdf06a0 · 같은 러너 ONLY): ci-branch 01~11 전부 rc0 · cargo test --bin cys 289/0(288 + 새 핀 1) · cargo test --lib 538/0 · boot-health-full GREEN 149/0/1 · secret-scan --all clean(1187).
- 뮤턴트: agents.json 에서 env 쌍 제거 → 핀 적색(KILLED) · 원복 clean.
- agy D 1R REJECT 2 → 2R ACCEPT: #2 env 순서 비결정 = 기각(`agent_env_pairs` 가 정렬 뒤 조립) · #1 수정 사용자 미배달 = 도달 한계는 사실(아래 고지) · 「큐 영구 보류」는 2차 방어(`input_line_state` 가 커서 뒤 고스트를 빈 입력으로 판정 · b4fdfc95)로 일어나지 않음.
- **도달 범위(코드 근거)**: agents.json = 사용자 소유 파일. ⑴ 새 설치 = 적용 ⑵ 업데이트 + agents.json 미수정(디스크 해시 = 설치 manifest 해시) = 적용(1.1.5 D1 `RefreshUser` · `.bak-<판번>` 백업 · GUI 인앱 업데이트 `init-pack --no-install-hook` 도 `install_staged` 를 먼저 돈다) ⑶ 사용자가 agents.json 을 고친 기계 = **미적용**(`.new` 병치만 · `load_agent_spec` 은 디스크 정의 우선 · `fill_missing_fields` 계층 3키에 env 없음) — 이 경우는 1.1.5 와 같다(퇴행 아님 · 제안 글 생성만 남음).
- 📌 결정 후보(master): governance.rs:5163 주석이 「근본 방어」로 적은 **키 부재 시 런타임 주입**(lib.rs `inject_claude_alt_screen_default_for` 와 같은 불가침 3계약 · 사용자 값 불가침)을 더하면 ⑶ 도 덮는다 — 새 제품 코드라 이 티켓에서 하지 않음.
- **1.1.6 릴리스 노트 1줄(초안)**: 「이제 cys 가 띄우는 모든 Claude 세션(대화 화면과 터미널 탭 모두)에서 답변 뒤 입력창에 뜨던 회색 제안 글을 끕니다 — 불필요한 추가 요청을 줄이고, 제안 글 때문에 전달이 늦어지던 일을 막습니다. agents.json 을 직접 고쳐 쓰신 경우에는 옆에 생기는 agents.json.new 를 병합(cys pack-merge --file agents.json)해야 적용됩니다.」
- VM 체크 1줄: 클로드 좌석에서 답 뒤 입력창 회색 제안 글 0(대화 화면 · 터미널 탭 각 1).

## 15. 곁 항목 추가 — 설치본 cys 런타임 git 의 https 원격 불가(13:4x 실측 · 판 배정 = master)
- 대상: 설치본 cysr 1.1.5 의 `Contents/Resources/runtime/git/bin/git`(git 2.53.0 · 좌석 PATH 1순위).
- 증상: `--exec-path` 가 번들 기준이 아니라 `//libexec/git-core` 로 풀려 `git ls-remote https://…` = 「git: 'remote-https' is not a git command」 — https fetch/push 불가. 도우미 파일(`runtime/git/libexec/git-core/git-remote-https`)은 번들에 있다.
- 우회 실측: `GIT_EXEC_PATH=<runtime>/git/libexec/git-core` 를 주면 정상.
- 재현 1줄: `/Applications/cys.app/Contents/Resources/runtime/git/bin/git --exec-path; /Applications/cys.app/Contents/Resources/runtime/git/bin/git ls-remote https://github.com/oogisoogi/cys-ro.git HEAD`
- 【추정】 원인 후보: 빌드의 「runtime/git dedup(git-core 빌트인 → git 심볼릭링크)」 또는 RUNTIME_PREFIX 재배치 판정 — 미규명.
