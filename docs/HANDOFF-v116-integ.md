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

## 16. B — 제안 글 끄기 env 의 키 부재 시 런타임 주입(master#70442818 판정 B · #d98da256 재개 · 새 검증 규칙 ①~⑥ 적용)
- 커밋 **cafba326**(src/lib.rs `ENV_CLAUDE_PROMPT_SUGGESTION` + `inject_claude_prompt_suggestion_default` · src/bin/cys.rs 호출 2곳 + 시험 3).
- 계약(D5 `inject_claude_alt_screen_default_for` 와 같은 불가침 3계약): ⑴ 키 부재 시에만 끝에 `"false"` 1쌍 ⑵ 사용자 값 불가침(무엇이든 있으면 손대지 않음) ⑶ 재정렬 금지. 대상 = `claude` 만 · OS 게이트 없음(D 가 이미 전 OS · 기능 끄기뿐).
- 조립 지점 = 운영 코드의 `agent_env_pairs` 호출 전부(2곳): `boot_agent_on_surface`(인라인 재조립) · `run_launch_agent_opts`(surface.create env 맵 = Windows 도달 경로) — 둘 다 D5 호출 바로 뒤. cysd·src-tauri 는 에이전트 env 를 조립하지 않는다(grep 0).
- 도달 경로 3(시험 `prompt_suggestion_reaches_all_three_install_paths`): P1 새 설치 · P2 미수정 업데이트(`RefreshUser`) · P3 수정본(보존 · 디스크 env 에 키 없음 → 주입이 채움) · P3′ 사용자 `"true"` 불가침.
- 디버깅 순서(규칙 ④): 시험 먼저 → 헬퍼 빈 몸통(스텁)에서 빨강 3건(계약 · 배선 · 도달) · 도달 시험의 빨강 자리 = P3 단언(조립 결과 `[CLAUDE_CONFIG_DIR, CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1]` · 제안 글 키 없음 = 증상 그대로) → 구현 → 초록.
- 뮤턴트 7/7 KILLED(몸통 no-op · 사용자 값 가드 제거 · 대상 한정 제거 · 값 false→0 · 호출 1 삭제 · 호출 2 삭제 · 호출 1 을 D5 앞으로).
- 타사 검토(agy · 규칙 ⑥ 설계·코드 둘 다): 설계 1R ACCEPT(구현 전) · 코드 1R REVISE 3(설치 경로별 인라인 env 순서 차이 · Windows env_injected · 제3 조립 경로) → 근거 제시(순서 의존 소비자 0 · 제안 수정으로도 순서 동일 불가 · 기본 팩 env 에 CLAUDE_CONFIG_DIR 상존 · 운영 호출처 2곳뿐) → 코드 2R **ACCEPT**(3건 철회 · cafba326 에 묶임).
- 블라인드 합격 시험(규칙 ⑤): 구현을 보지 않은 Opus 서브에이전트가 명세·인터페이스만 보고 4개 작성(`integ-v116-work/blind-B-tests.rs`) → 결과 = 아래 §16-1. 정직 고지: 작성자가 grep 줄 번호로 호출 지점에 3줄이 끼었다는 것만 봤고 본문은 읽지 않았다고 자진 고지.
- 영향 게이트(cafba326): 아래 §16-1.
- 검증 모델 실측(규칙 ①): 블라인드 서브에이전트 = 부모 상속(Opus 5.5) — jsonl model 필드는 §16-1.

### 1.1.6 공개 릴리스 노트 1줄(master#70442818 문안 · §14 초안 대체 · `cys pack-merge` 안내 삭제)
「이제 자비스가 띄우는 모든 Claude 창에서 답변 뒤 입력칸에 뜨던 회색 제안 글이 나오지 않습니다. 필요 없는 추가 요청이 줄고, 제안 글 때문에 지시 전달이 늦어지던 일이 사라집니다.」
- 기술 설명(내부용 · 공개 금지): 기본 팩 agents.json 값(D) + 조립 지점 키 부재 시 주입(B) — agents.json 을 고친 기계도 덮는다 · 사용자가 이 키를 직접 적어 두었으면 그 값을 따른다 · 되돌리기 = agents.json 클로드 env 에 `"CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION": "true"`.
- ⚠ §14 의 릴리스 노트 초안(수정본 예외 문장 + pack-merge 안내)은 **폐기** — 이 절이 대체한다.
- 규칙 ⑦(master#3dd0fad5 · 15:45) 정직 고지: 이 티켓 10:5x 1차 기준선 중단 때 `pkill -f 'integ-v116-work/run_gates.sh'`(이름 패턴 · 자기 작업 폴더 경로로 좁힘) 1회 사용 — 그 뒤 남은 자식 2개는 cwd 실측(=이 worktree) 후 pid 로 kill. 규칙 발효(15:45) 이후 이름 패턴 kill 0.

### 16-1. B 결과(cafba326)
- 영향 게이트(같은 러너 · ONLY 01~12·14·16 + secret-scan): ci-branch 01~11 전부 rc0 · cargo test --bin cys **291/0**(289 + B 2) · cargo test --lib **539/0**(538 + B 1) · boot-health-full **GREEN 149/0/1** · secret-scan --all clean(1187).
- 블라인드 합격 시험 4(구현 미열람 Opus 서브에이전트 작성 · 시험 모듈에 임시로 붙여 실행 · 커밋 안 함 · 원복 clean): `blind_b_prompt_suggestion_contract_table` · `…_three_install_paths`(P1 Write · P2 RefreshUser · P3/P3′ Keep 판정까지 단언) · `…_rendered_send_string_unix`(인라인 문자열에 `="false"` 정확히 1번 · P3′ 는 true) · `…_wired_after_alt_screen_before_render` → **4/4 통과**. 원문 = `integ-v116-work/blind-B-tests.rs` · 실행 로그 = `blind-B-run.log`.
- 검증 모델 실측(규칙 ①): 블라인드 서브에이전트 jsonl(`subagents/agent-a9fc4f80….jsonl`) `"model":"claude-opus-5-5"` 26건 · 그 밖 모델 0.
- 수렴(규칙 ③) 현황: 결정론 게이트 초록 · 풀리지 않은 반례 0(agy 코드 2R 에서 3건 전부 철회) · 타사 ACCEPT = agy 코드 2R(cafba326) · **master 독립 재실행 = 대기**.

---

## 17. 2차 통합(ACCEPT 묶음 편입 · TICKET=v116-integ-2 · master#07b7abe5 · #e0de3a95)

- 브리프 = `~/axdev/master/briefs/2026-09-25-v116-integ-2.md` · 좌석 = worker-38(surface:1086) · Opus 5.5 · 착수 03:53 KST · 기점 91aa600d(= origin)
- 규칙: 적대 검토 3라운드 상한 · push/태그/발행 = master 게이트(이 절 전 구간 push 0 · 태그 0).
- 도구·로그(저장소 밖) = `~/axdev/.wt/integ-v116-work/r2/`(qt.sh 빠른 확인 래퍼 · qt-*.log · t14x.py · mut_bpin.sh/txt) · 헤드리스 = `integ-v116-work/headless4/` · 정본 게이트 = `~/msv-scratch/v116-integ2/results/<sha8>/`(master 러너 gate_runner.py v2 · 스냅샷 · 기준 = master 결과 `~/msv-scratch/v116rv/results/91aa600d`)

### 17-1. 병합 표(순서 = 브리프 1→5 + master#e0de3a95 ⑥)
| 순 | 가지 · 결속 해시 | 병합 커밋 | 문자 충돌 | 빠른 확인(병합 직후 · 좌석 env 제거) |
|---|---|---|---|---|
| 1 | 1092 flake-pty @9f62f1a4(가지 끝 90a85ca4 = 문서 5커밋 · master 지시로 제외) | **af7d1026** | 0 | cysd `pty_` 32/0(1 ignored) · test_phoenix_c6_reap 3/3(6/6 PASS ×3) |
| 2 | 1078 tusage @2efaf0a7 | **c99a7af1** | 3(lib.rs · wsusage.ts · wsusage.test.ts) | bun wsusage+wsbar 129/0 · tsc 7(기준 동일) · cysd accounts/usage/d6 119/0 · cys 325/0 · lib 540/0 · 뮤턴트 2/2 |
| 3 | 1083 seat @0e5f4bb0 | **e7d1fbfc** | 2(cys.rs 2곳 · lib.rs) | cysd v116_/accept_v116/governance 244/0 · cys 336/0 · lib 545/0 · test_t6_injection_policy OK · 뮤턴트 2/2 |
| 4 | 1089 restore-card-producer @113a36f8(코드 51fca96b) | **b7d0fd88** | 0 | bun 1282/0 · tsc 7 · test_core_inject/bootv2_doc_contract/event_inject ALL PASS · gen_ceo_template --check GREEN · CEO 주입 여유 344자 불변(아래) |
| 5 | 1091 restart-toast @1ef56746(코드 f5ee9415) | **37069ddf** | 0(main.ts 자동) | bun 1306/0 · tsc 7 · secret-scan --all clean(1213) · 헤드리스 c1~c17 **ALL PASS 49줄** |
| 6 | 1077 num @4285e910(코드 17cc0a68 + 경로 수리 27570e9e) | **e60d0539** | 0 | (7 과 함께) |
| 7 | num-ui 42596ebf cherry-pick -x | **f089fac9** | 0(panetitle.test.ts 자동) | bun 1313/0 · tsc 7 · secret-scan --all clean(1238) · T14 2/2 |
- git rerere 가 켜져 있어 충돌 해결이 기록됨(`Recorded resolution` — 같은 충돌 재발 시 자동 재적용 · 결과는 반드시 재확인할 것).

### 17-2. 충돌 해결 목록(두 의도 보존 · 의미 판단 표기)
1. **c99a7af1 src/lib.rs** — B `inject_claude_prompt_suggestion_default` 와 T-USAGE `is_claude_agent` 가 같은 자리에 새로 붙음 = 인접 충돌 → 둘 다 유지(의미 판단 없음).
2. **c99a7af1 ui/src/wsusage.ts** 【의미 판단 · master#f0d58fa9 = 현행 확정(근거: 문턱은 생산자 주기 짝 · 옛 데몬 게이지 생산자 = oauth 뿐 · 대가 = 멈춘 값이 최대 4분 새것으로 보임 · 확신도 중상)】 — T-UI D4 #11 은 `7d·<모델>` 게이지 문턱을 클라이언트 상수 `SCOPED_STALE_SECS`=240 으로, T-USAGE 는 판정을 데몬으로 옮겨 `fresh_limit_secs`(statusline 120 · oauth 240)를 싣고 필드 부재(옛 판본 데몬) 폴백 = `USAGE_STALE_SECS`(120)로 했다. 해결 = `obsFreshLimit(v, fallback = USAGE_STALE_SECS)` · 게이지만 `obsFreshLimit(g.fresh_limit_secs, SCOPED_STALE_SECS)` → **필드가 오면 데몬 값(T-USAGE) · 필드 부재 게이지만 240(T-UI)** · 계정 행 폴백 120 그대로. 근거: 1.1.5 데몬의 게이지 생산자는 oauth 하나뿐(526325bf accounts.rs 시험 `scoped[0].source == "oauth"`)이라 옛 데몬 게이지에 240 은 추정이 아니라 원천 한도와 같은 값. T-USAGE 주석에 예외 1곳을 적음.
3. **c99a7af1 ui/src/wsusage.test.ts** — 두 describe 모두 유지 + 합류 핀 1(데몬 `FRESH_LIMIT_OAUTH_SECS = OAUTH_PROBE_INTERVAL_SECS + 60` 식을 읽어 `== SCOPED_STALE_SECS` · 필드 부재 200초 = 초록 · 필드 120 = 흐림 · 필드 300 = 초록). 뮤턴트: 게이지 폴백 제거(120) → 3 fail KILLED · 데몬 필드 무시(상수 240 고정) → 1 fail KILLED.
4. **e7d1fbfc src/lib.rs** — B·is_claude_agent 와 seat `CLAUDE_SEAT_EFFORT`/`inject_claude_effort_env` 인접 → 모두 유지 · B doc 의 Windows 도달 자리 표기 = `launch_create_env_pairs`.
5. **e7d1fbfc src/bin/cys.rs boot_agent_on_surface** — D5 → B → effort 순 셋 다 유지.
6. **e7d1fbfc src/bin/cys.rs run_launch_agent_opts** 【구조 이동 · 의미 불변】 — seat 가 surface.create env 조립을 `launch_create_env_pairs(spec, agent)` 로 옮김 → seat 쪽 호출을 채택하고 **B 주입을 그 함수 안 D5 뒤·effort 앞**에 넣음(기동 줄과 같은 순서) · 함수 doc 갱신.
7. **e7d1fbfc B 배선 핀 이전**(시험 변경 · 명시) — `prompt_suggestion_injection_wired_in_both_consumers` 가 run_launch_agent_opts 본문의 D5 호출을 찾던 것이 seat 이동으로 무너짐 → ⑴ boot_agent_on_surface·launch_create_env_pairs 안 D5<B ⑵ run_launch_agent_opts 가 `launch_create_env_pairs(&spec, agent)` 를 render_launch 앞에서 부름 ⑶ 조립 결과 실행 단언(false 정확히 1쌍 · 사용자 "true" 불가침 · codex 0). 뮤턴트(`r2/mut_bpin.sh`): 조립 함수 B 삭제 KILLED · B 를 D5 앞으로 KILLED · 원본 3/3.

### 17-3. `cys list` 파싱 지점 대조표(master#e0de3a95 통합 점검 1)
- 방법: 통합 트리(f089fac9)에서 `cys list` 호출·파싱 지점 전수 grep(파이썬·셸·PowerShell·Rust·TS · 문서 제외) → 526325bf(T14 기점) 결과와 comm 대조 → T14 목록과 대조 → T14 밖 지점을 no= 칸 든 픽스처(T14 의 OLD/NEW 그대로)로 1회 실행(`r2/t14x.py`).

| 지점 | 읽는 칸 | T14 | 이번 통합에서 새로? | no= 픽스처 |
|---|---|---|---|---|
| javis_awaken.surface_row | 설계 §4-1 ※(1077 실측 · 0~3칸 · 마지막 칸만) | ✅ | 아니오 | T14 2/2 |
| javis_bootstrap (2152 · 2193) | 설계 §4-1 ※(1077 실측 · 0~3칸 · 마지막 칸만) | ✅ | 아니오 | T14 |
| javis_boot_node.parse_list_rows | 설계 §4-1 ※(1077 실측 · 0~3칸 · 마지막 칸만) | ✅ | 아니오 | T14 |
| javis_cycle_autopilot (684) | 설계 §4-1 ※(1077 실측 · 0~3칸 · 마지막 칸만) | ✅ | 아니오 | T14 |
| javis_formation (472) | 설계 §4-1 ※(1077 실측 · 0~3칸 · 마지막 칸만) | ✅ | 아니오 | T14 |
| javis_orchestra guard-master-claim (2841) | 설계 §4-1 ※(1077 실측 · 0~3칸 · 마지막 칸만) | ✅ | 아니오 | T14 |
| javis_wakeup (195) | 설계 §4-1 ※(1077 실측 · 0~3칸 · 마지막 칸만) | ✅ | 아니오 | T14 |
| cys-dept dept_live_roles | 설계 §4-1 ※(1077 실측 · 0~3칸 · 마지막 칸만) | ✅ | 아니오 | T14 |
| hooks/guard.sh cys_live_pids | 정규식 `pid=` `exited=` · 첫 낱말 | ✗ | 아니오(526325bf 에 있음) | **같음** |
| javis_idle_audit.parse_cys_list | 낱말 `surface:` `pid=` | ✗ | 아니오 | **같음** |
| javis_phoenix_harness.live_surfaces | 줄 머리 `surface:` 개수 | ✗ | 아니오(1092 가 같은 파일 수정 · 이 함수 무변경) | **같음** |
| tests/test_phoenix_c6_reap.py (89 · 95 · 117) | 0칸 · 부분 문자열 `exited=true` | ✗ | **예(1092 ⑴ 줄 이동·추가)** | **같음** |
| .github/workflows/windows-build.yml T4 | 부분 문자열 `role=master` | ✗ | 아니오 | **같음** |
| javis_phoenix live_role_surfaces(1249 · known 드리프트 판정) · _surface_shell_pids(1379) | 머리 고정 정규식 `surface:N role= pid= exited=`(뒤 칸 무시) | ✗ | 아니오 | **같음**(Opus 1R 부기로 추가 · 정규식은 소스에서 떼어 실행 · known 참 유지) |
| javis_phoenix_harness 기타(389·495·594·611·2011·2062) · windows-build 451·649·733 | 줄 머리 `surface:` · 종료 코드만 | ✗ | 아니오 | Opus 1R 가 같은 픽스처로 확인(전=후) |
| javis_orchestra 역할 레지스트리(1019) | surface.list JSON(텍스트 아님) | — | 아니오 | 해당 없음 |
| Rust·TS | 파서 0(cys.rs 3060 = 생산자) | — | — | 해당 없음 |
- 결론: T14 밖 지점(내 grep 5곳 + Opus 1R 추가 phoenix 2함수) 전부 픽스처 결과 **전 = 후**(T14X ALL SAME) · 새로 들어온 파싱 지점 = 1092 의 c6 시험 줄뿐이고 0칸·부분 문자열만 쓴다. T14 9곳 파일은 4285e910 대비 통합에서 무변경(phoenix_harness 만 1092 로 바뀜 · 파서 함수 무변경).

### 17-4. CEO 주입 여유(1089 ⚠)
- `core_inject.py session` 출력 길이(격리 HOME · 같은 측정 경로): 91aa600d master 6,313 / CEO 8,273 → f089fac9 master 6,518 / CEO 8,478 = **+205(1089 HANDOFF §6 값과 같음)** → 1083·1091·1077 의 주입 증가 0 · **CEO 남은 여유 344자 그대로**(상한 8,800 · 러너 오프셋 +22 는 두 판 공통).

### 17-5. 1.1.6 공개 릴리스 노트 초안(§16 한 줄에 이어 붙임 · 최종 문안 = master)
**공지 한 줄(master 확정 문구 · 맨 위):**
「업데이트가 끝나면 '눌러서 재시작' 알림이 나옵니다. 알림이 보이면 바로 눌러 주세요.」

**바뀐 점:**
- 이제 자비스가 띄우는 모든 Claude 창에서 답변 뒤 입력칸에 뜨던 회색 제안 글이 나오지 않습니다. 필요 없는 추가 요청이 줄고, 제안 글 때문에 지시 전달이 늦어지던 일이 사라집니다.(§16 문안 그대로)
- 업데이트를 받은 뒤 알림을 놓쳐도, 맥에서는 머리줄의 「업데이트」 단추가 「다시 켜기」로 바뀌어 누르면 바로 새 판으로 다시 켜집니다(같은 파일을 다시 받지 않습니다). ※ 이 동작은 1.1.6 에서 다음 판으로 갈 때부터 적용됩니다.(1091)
- 앱이 다시 켜지면 복원 카드에 「끝난 일 · 하던 일 · 정하셔야 할 일」이 쉬운 말로 나오고, 언제 적힌 내용인지 시각이 함께 보입니다.(1089)
- 창마다 1~999 사이의 짧은 번호가 붙어, 창 머리와 알림에 같은 번호가 보입니다.(1077)
- 사이드바 사용량 게이지가 정상인데도 몇 분마다 흐려지던 일이 없어지고, 값이 어디서 온 것인지 표시가 붙습니다.(1078)
- 새로 뜨는 Claude 좌석이 늘 높은 사고 수준(effort high)으로 켜지고, 빈 좌석에 옛 기동 명령이 뒤늦게 글자로 들어가던 일이 막혔습니다.(1083)

**내부용(공개 금지):** 1092 = 시험 하네스 수리(PTY 고갈 재시도 · c6 준비 대기 · CI 임시 팩 폴더 정리) — 제품 동작 무변경 · 릴리스 노트 대상 아님.

### 17-6. 적대 검토(3라운드 상한 · 1라운드에서 두 검증자 dry)
- 의뢰문 = `integ-v116-work/agy/prompt-i2-r1.txt`(R1 wsusage 합류 · R2 B 주입 이전·핀 재작성 · R3 cys list 대조 + remerge-diff 원문).
- **agy 1R = ACCEPT**(`agy-i2-r1.md` · blocking 0 · 요약형 — 칭찬 문구는 판정 근거로 쓰지 않음).
- **Opus 5.5 서브에이전트 1R = ACCEPT**(읽기 전용 · 전사 model = `claude-opus-5-5` 84건 실측) · blocking 0 · 부기 4(전부 비차단 · 제품 결함 0 · **이 통합에서 코드 무수정 · 기록만**):
  1. cys list 소비자 추가 발견 = javis_phoenix live_role_surfaces·_surface_shell_pids 등 → 픽스처로 전=후 같음(위 표 반영 · `r2/t14x.py` 확장). 제안: T14 results() 에 phoenix 2함수 편입(M25 음성 대조가 함께 지키게) — 1.1.7 후보 · master 판정.
  2. B 순서 핀은 D5<B 만 잰다 — B 를 effort 뒤로 옮기는 뮤턴트는 산다(키가 달라 현재 실패 0). 조립 함수 doc 의 「같은 순서」 표현보다 핀이 약함 → 핀에 `b < effort` 1줄 추가 또는 doc 표현 완화 = 1줄 후속(게이트 머리 보존 위해 보류 · master 판정).
  3. `prompt_suggestion_reaches_all_three_install_paths` 의 compose 는 D5+B 를 손으로 조립(effort 없음) — `launch_create_env_pairs` 로 바꾸면 조립 경로 단일화(후속 후보).
  4. 여러 팩 시험 모의 `cys list` 행이 옛 형식(no= 없음) — 파서가 호환이라 초록 · 새 형식 미행사(선택 후속).
- 줄 유실 점검(Opus): 충돌 5파일 양쪽 추가 줄 대비 병합 결과 — 빠진 줄은 전부 의도된 대체(SCOPED 줄 → obsFreshLimit 폴백 · 수동 조립 → 조립 함수 호출 · doc 2줄 재작성).

### 17-7. 정본 게이트 — 최종 머리 ce6c2779(코드 기준 · 이 문서 커밋은 문서만 더함)
- 러너 = master `reverify-tools/gate_runner.py`(v2 2형태 · 워크플로 run 블록 원문) · `master-verify-snapshot.sh`(분리 스냅샷 · `--deps ui` · MSV_NOTIFY=0) · 격리 HOME/TMPDIR · 정제 PATH `~/msv-scratch/v116rv/bin` · 04:33:08 → 05:10:05 · load 7.2 → 8.5 · 스냅샷 추적 변경 0 · 결과 `~/msv-scratch/v116-integ2/results/ce6c2779/` · 대조 `cmp-ce6c2779-vs-91aa600d.json`.
- **compare_runs(대상 ce6c2779 · 기준 master 91aa600d 결과) = 대상 실패 0 · 기준 실패 3 · 신규 0 · 해소 3**(해소 = D07b test_phoenix_c6_reap 과 그 하위 판정 2 — 1092 편입 효과).
- ⚠ f089fac9 로 먼저 띄운 게이트는 1101 편입으로 머리가 바뀌어 **내가 띄운 pid 74012 만 TERM** 중단(04:32:44 · 스냅샷 제거·잔존 0 실측 · 부분 결과 = `results/f089fac9-aborted`). 첫 시도는 러너가 미리 만든 HOME 폴더를 거부(FileExistsError · 명령 미실행)해 폴더 삭제 후 재기동.

| 스텝 | 결과(ce6c2779) | 기준 91aa600d |
|---|---|---|
| 전체 | 98스텝 rc≠0 **0** | rc≠0 1(D07b c6) |
| A12 / D07e `cargo test --bin cys` | 340/0 | — |
| A13 / D07d `cargo test --lib` | 546/0(1 ignored) | — |
| A14 `-p cys-app --bins` | 172/0 | — |
| B01 boot-health-full | **GREEN 149/0/1**(406s) | GREEN |
| D02 secret-scan --all | clean 1239 파일 | clean |
| D06 `bun test` | 1313/0 | — |
| D07c `cargo test --bin cysd --test-threads=1` | 1192/0(2 ignored) | — |
| X01 hwmon | 2/0 | — |
| **D07b test_phoenix_e2e_replacement**(③ 포함) | **6/6 PASS** rc 0(44.1s) | 초록 |
| **D07b test_phoenix_w2_untomb_fullcycle** | **8/8 PASS** rc 0(37.0s) — 1083 ACCEPT 조건(w2 초록) 해소 근거 | 초록 |
| D07b test_phoenix_c6_reap | rc 0(37.6s) | **적색** → 해소 |
- 기준 표의 세부 수는 master 결과 폴더 원문 그대로 비교하지 않았다(대조는 compare_runs 판정만 근거) — 「—」 칸은 기준 수를 따로 옮기지 않은 것.
- 빈칸(정직): T-PACK(8f439373)은 이번 편입 대상 아님 → §10-1 「T-PACK 편입 뒤 고아 데몬 0 실측」은 여전히 미결. 윈 설치파일 = 이 기기 툴체인 없음 → push 뒤 CI(push = master 게이트).

### 17-8. 4군 점검
- ①폭주 큐: 1083 이 배달 경로를 바꿈(표지 붙은 기동 줄이 좌석 에이전트와 안 맞으면 큐에 넣지 않고 거부 · 낡은 기동 줄은 배달 대신 폐기) → cysd 직렬 전건 1192/0 · 1083 수용 시험(accept_v116 S1~S5) 초록 · 1092 PTY 재시도는 시험 전용 모듈(제품 무접촉).
- ②무clear 100%+: 좌석 출생 CTX 경로 변경 0(1083 effort env = 기동 env 1키 · 1089 = 지침 문구 +205자 · CEO 주입 여유 344자 불변 §17-4).
- ③자가치유 전멸: phoenix 게이트 D07b 전건 초록(c6 해소 · e2e_replacement 6/6 · w2_untomb 8/8) · 1091 = 대기 중 install_update 재호출 0(헤드리스 c17b·c17c·c17h·c17n) · 1089 = 복원 카드 읽기/쓰기(헤드리스 c5·c11 초록).
- ④전 pane 사망: 헤드리스 c1~c17 ALL PASS(닫기 확인·exited 청소 술어 불변) · B·effort env 는 키 부재 시 추가만(사용자 값 불가침 · 재정렬 0 · 단언 실행) · Windows 에서 pane env 로 닿는 경로 = launch_create_env_pairs 하나(구조 불변). 윈 설치파일 = push 뒤 CI.
- 프로세스 정리: 내가 띄운 것 잔존 0(헤드리스 크롬 · 게이트 스냅샷 · cargo) 실측 · 이름 패턴 kill 0.

---

## 18. 3차 통합(TICKET=v116-integ-3 · master#b7e65821 · 정정 #f73e8693)
- 규칙: 이번 단계는 **빠른 확인까지만** — 정본 게이트 전체는 1090·v116-auto-equalize 합류 뒤 한 번에(master 큐 CPU 경합 회피). push/태그 = master 게이트. 1.1.6 발행 = 늦어도 09-28(월) · 정렬 기능 편입(박사님 결정).

### 18-1. ① 1088 exited-banner @5ec32038(기점 T-UI 3bc73856 · 통합에 이미 있음) → 병합 **af8cf0df**
- 충돌 1 = `docs/v116-ui-evidence/v116-headless.ts`(헤드리스 하네스 · 제품 코드 아님): 1091 과 1088 이 **같은 블록 열쇠 「c17」 을 따로** 썼다(1091 = 재시작 대기 c17a…c17r · c17x · c17w / 1088 = 종료 배너 c17a@1280 처럼 폭 붙은 판정 · c18).
  - 해결: 판정 이름이 겹치지 않으므로 열쇠 「c17」 을 공유하고 블록 둘 다 유지. 순서 = **1088 c17 → 1091 c17·c17x·c17w → 1088 c18**(1088 은 자기 가지처럼 c16 바로 뒤·기본 UA에서 · 1091 c17 은 맥 UA 를 세우고 되돌리지 않으므로 뒤로 · 1091 은 자기 load 로 새로 시작). 기본 ONLY = 두 목록 합집합(c17,c17x,c17w,c18).
  - 영향: 1088 `mutate-exited.py`(ONLY=c17 · `FAIL c17` 접두)는 그대로 동작하나 1091 의 c17 판정도 함께 돈다(exitbanner 뮤턴트와 무관 · 시간만 늘어남).
- 증거 파일 치환: master 정정(#f73e8693) 그대로 — `exited-banner/headless-final-c1-c18.txt` 의 `/Users/u` = **0줄**(1088 139ca0d1 에서 이미 `/Users/user/`) · 치환 커밋 없음.
- 빠른 확인(af8cf0df): `bun test` **1332/0** · `exitbanner.test.ts` 19/0 · tsc 7(기준 목록 동일) · `secret-scan --all` **clean 1277 파일** · 헤드리스(worktree 밖 사본 실번들 · chrome-headless-shell 154) 전체 = **ALL PASS 79줄**(c1~c16 + 1088 c17 + 1091 c17/c17x/c17w + c18) · ONLY=c17(1088 뮤턴트 스크립트 경로) = **ALL PASS 29줄** · 내 크롬 잔존 0.

### 17-9. git push 기록(2차 통합 0133dcd4 · 불변식 5 2단계)
- ① master#ce998f62(ACCEPT + push 승인 · 원장 대조 성립 05:59:31) → ② 【실행직전확인요청】 05:59:57 → ③ master#aca6f088 재승인(원장: surface:1086 · submitted yes · 06:00:09 · 유효 범위 = 이 push 1건) → ④ 실행 06:00:22.
- 명령(정확히 1개): `/usr/bin/git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push origin 0133dcd4278d49f627e5acacacdff9a9571d5713:refs/heads/fix/v116-integ` → rc 0 · `91aa600d..0133dcd4`(빨리감기).
- 사후 실측: ls-remote fix/v116-integ = 0133dcd4(일치) · main = 721bc990(무접촉) · 키체인 github.com 항목 전 1 = 후 1 · 저장소·전역 credential.helper 미설정(무변경) · 로컬 3차 머리 27d80ff0 미전송 · 태그 0.
- 발화 런(headSha 0133dcd4): ci-branch 36058650072 · windows-build (feasibility) 36058649809 · windows-health (H-WIN 실기) 36058649606.
- 결과: **ci-branch = success**(macos-rust-pack · nsis-hook-harness · boot-health-full 전부 success) · **windows-health = success** · **windows-build = failure**(아티팩트 cys-windows-x64-nsis 140,786,742B 는 생성됨).
- windows-build 적색 원인 분류(수리 0 · 보고만):
  - 실패 스텝 = 18 「T5 피닉스 Windows 패리티 스모크」 · 판정 50여 개 중 **1개만 적색 = 「③ taskkill 수행(rc0)」**. 같은 ③ 의 뒤 판정(파이프 해제 관측 · schtasks /Run 재기동 · pong 복귀 · boot-epoch 새 세대)은 전부 PASS → **데몬 종료·재기동 자체는 성공**.
  - 【관측】 taskkill /PID <cysd> /T /F 출력 = 「SUCCESS: … PID 8272 … terminated」 + 「ERROR: The process with PID 5836 (child process of PID 2492) could not be terminated. Reason: The operation attempted is not supported」 → 트리 안 손자 1개를 못 죽여 rc≠0. 기준 런(91aa600d · 35973475472)의 같은 줄 = cysd 1개만 종료(자식 트리 없음).
  - 【관측】 91aa600d..0133dcd4 에서 `javis_phoenix.py`·`javis_phoenix_win_smoke.py`·windows-build.yml 무변경 · cysd/lib 의 새 프로세스 생성 = pty_test_support.rs(cfg(test) 시험 전용) 1곳뿐 → **이번 편입이 데몬에 새 자식 프로세스를 들이지 않았다.**
  - 【추정 · 중상】 kill 순간 데몬에 자식 트리가 살아 있었던 타이밍 경합(기동 직후 cysd 가 스스로 띄우는 auto-restore 등 기존 자식 · 끝나기 전에 kill) + 종료 불가 손자(「not supported」 = 콘솔 호스트류 추정)로 rc≠0. 제품 결함 아님 · 하네스 판정(rc0 엄격)의 부하 의존 흔들림 쪽. windows-build 최근 40런 중 이 판정 적색 = 이번 1회(다른 1회 = v113 가지 · 다른 원인 미확인).
  - 재실행(master#3f6b62d2 승인 · 원장 06:38:22 · `gh run rerun 36058649809 --failed` 1회 06:38:33) → **attempt 2 = success**(build success · 07:03 KST · win_smoke_pass true · ③ taskkill = cysd PID 4416 만 종료 · 손자 트리 없음) ⇒ **플레이크 확정**(재현 0/1).
  - 1.1.7 하네스 후보(master 기록): ③ 에서 대상 데몬 종료가 확인되면(파이프 해제·새 세대) 트리 손자 종료 실패는 적색이 아니라 경고로.

### 18-2. ③ 1102 auto-equalize @3656840e(0133dcd4 위 14커밋 · master#e3e6c762) → 병합 **27968f82**(^2 = 3656840e 실측)
- 충돌 1 = 헤드리스 하네스 — 1088 과 1102 가 같은 블록 열쇠 「c18」 을 따로 씀(1088 = c18g-scrollback-full·c18h-burst-then-exit·c18i-carry-flush…c18n-narrow-420 / 1102 = c18a…c18i 공백 뒤 설명). c17 과 같은 처리: 열쇠 공유 · 블록 둘 다 유지 · 순서 = 1088 c18 → 1102 c18(자기 load 로 시작 · 창 크기 스스로 복원) · 판정 이름 무변경(두 가지 증거 파일과 대응 유지). ⚠ 앞머리가 겹치는 이름(c18g·c18h·c18i)은 판정 줄 전문으로 가른다.
- 의미 충돌 점검(main.ts 자동 병합 · 기호 계수 = 도구 출력): 1077 `display_no|displayNo` 6 = 27d80ff0 과 같음(유지) · 1088 `writeExitedBanner` 2(유지) · 1102 `relayoutWs` = 주석 2뿐(3656840e 와 같음 · 틱 끝 일괄 배치 제거) · `arrangeWs` 14(3656840e 와 같음) · `split-col` 0(팔레트 세로 분할 제거 반영). 1102 가 가장 크게 바꾼 refreshPaneTitles 는 1077 num-ui 가 고친 함수이나 겹친 줄 없음(자동 병합 · 두 쪽 기호 보존). `formation.ts` = 1102 단독(526325bf 이후 다른 가지 무접촉). 헤드리스 c4b 기대값 변경(오너 09-25)은 자동 병합으로 반영.
- 부기(master): b5d4bd52 = 알려진 적색 커밋(시험 · d207034f 정정) → bisect 때 건너뜀.
- 빠른 확인(27968f82): `bun test` **1409/0** · tsc 7(기준 목록 동일) · `secret-scan --all` **clean 1292** · 헤드리스 실번들 전체(c1~c18 · 1088·1091·1102 블록 전부) = **ALL PASS 89줄**(부하 16~21 하에서 · 약 14분) · 크롬 잔존 0.
