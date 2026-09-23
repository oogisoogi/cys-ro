# HANDOFF — cysr 1.1.6 T-APP · 새 설치 첫 실행이 「갱신 복원」으로 도는 것 + 첫 실행 폴더 권한 창 · TICKET=v116-app-firstrun

- 브랜치 `fix/v116-app` ← 526325bf(1.1.5 11차 통합) · 작업 좌석 surface:1026(worker-10)
- 입력: 브리프 `~/axdev/master/briefs/2026-09-23-v116-app-firstrun.md` · PLAN-1.1.6 §1-3(D4 #9 · D4 #16/X-2) · §5-1 A-3
- master 판정: master#7eb220fb(A-3 = A 채택 — UI 덩어리(ui/src/main.ts perm-warning 옆 한 덩어리)도 이 티켓 · 수리 설계 ⑴ 채택 · 「~/.cys 만 지워진 기기」 행 진리표 편입) · master#cefef297(허용 파일 확장 = src-tauri/Info.plist 1개 · 공개 안내 말투)
- 커밋: b5dd7100(수리 ⑴⑵ + 시험) · 368fe884(Info.plist 두 키 + 문구) · 6a7e5127(검증 1R 반영) · 57da54ac(맥 밖 dead_code 허용) · 4baff0e1(디버깅 패스 반영) · 이 문서
- ⛔판번 bump 0 · git push 0 · 태그 0 · 라이브 `~/.cys`·설치 앱·가동 데몬 접촉 0 · tccutil·[허용 안 함] 재현 0(VM 전용)

## 1. 원인표

| 결함 | 원인(파일:행 · 기준 526325bf) | 등급 |
|---|---|---|
| 새 설치 첫 실행이 복원을 돈다 | `src-tauri/src/main.rs:3361-3375` decide_pending_update 의 「기존 설치 증거」 = `:3397` `~/.cys/pack/.pack-version` 존재. 이 파일은 **새 설치에서도 판정 전에 반드시 생긴다** — ① 설치기 [8/10] `cys init-pack`(jarvis-habitat `install-master/bootstrap.sh:3426`) 뒤에 `open -a`(`:3459`·`:4193`) ② setup 의 ensure_daemon 이 띄운 cysd 첫 부팅 스윕(`src/bin/cysd/main.rs:1259` `pack_current_for` 거짓 → `pack::install`) ③ 판정 호출(`main.rs:7013`) 바로 앞 줄의 GUI 온보딩 init-pack(`:7011` maybe_macos_onboard). ⇒ 스탬프 없음 + 팩 있음 = Apply → `init-pack --no-install-hook` 재실행 + spawn_org_restore → 빈 topology 복원(`cys restore` 「토폴로지 스냅샷 없음」 · rc 0) → restore-progress start/done → 「직원 복귀 중/완료(부서 0)」. RecordStampOnly 갈래는 실사용에서 도달 불가였다 | 【관측·코드】 (T4 HANDOFF §6 의 【추정】을 코드로 확정 · 알림 실물 캡처는 VM 대기) |
| 첫 실행 폴더 권한 창 2개가 설명 없이 뜬다 | `main.rs:3541-3558` nudge_folder_permissions — setup 끝(`:7016`)에서 GUI 프로세스가 `~/Desktop` → `~/Documents` 순으로 read_dir(미결정이면 macOS 권한 창). VM 의 「데스크탑 → 문서 2개 연속」 순서와 일치. setup 에서 그보다 먼저 두 폴더를 읽는 앱 경로는 없다(grep `"Desktop"`·`Desktop/`·`CYSjavis` — main.rs 는 이 함수와 주석뿐) | 【관측·코드】 |
| (참고) 거절 시 부서 좌석 사망 | 1.1.5 에서 이미 줄었다: 맥 부서 기동 = 본부 데몬 대행(`main.rs:4638` run_dept_tool → `dept.run`) + 데몬 원인 알림 `seat.folder_denied`(`src/bin/cysd/governance.rs:3405~` · UI `ui/src/main.ts:7286`). 앱이 책임 주체인 사슬로 남은 것 = 대행 실패 시 직접 실행 폴백 1곳 | 【관측·코드】 · 이 티켓 무수정 |

## 2. 수리

### ⑴ 새 설치 = 복원 안 돎 (`src-tauri/src/main.rs`)
- 「기존 설치 증거」를 `prior_install_evidence(gui_onboarded_before_boot(), &list_depts())` 로 교체.
  - `gui_onboarded_before_boot()` = `~/.cys/.gui-onboarded` 존재를 **setup 첫머리(어떤 await 보다 먼저 · 온보딩이 마커를 쓰기 전)** 에 한 번 재서 `OnceLock` 에 캐시. `.gui-onboarded` 의 writer 는 GUI 온보딩 성공 경로뿐이다(설치기·데몬·CLI 는 쓰지 않음 — grep). UI 명령이 setup 보다 먼저 불러도 그 시점은 온보딩 전이라 값이 같다.
  - 부서 레지스트리(`depts.json`)에 부서 ≥1 이면 증거 있음(마커 이전 판에서 올라온 기기의 부서 재기동 보존). 레지스트리가 있는데 해석이 안 되면(Err) = 모름 = 증거 있음(복원은 멱등 · 거짓 부재가 더 위험).
- `decide_pending_update` 자체와 스탬프·마커 갈래는 **무변경** — 진짜 갱신(스탬프 ≠ 현재판 · 인앱 마커)은 증거와 무관하게 종전대로 Apply(자가치유 대조군).
- UI 의 `isFirstLaunch`(localStorage `cys-layout-v2` 부재 · restorebrief.ts)와 같은 질문(「이 GUI 가 이 기기에서 전에 떴는가」)의 백엔드 판본이다. 백엔드가 WebKit/WebView2 저장소 파일을 직독하는 안은 OS별 취약으로 기각. 두 사실이 어긋나는 방향 = 「~/.cys 만 지워진 기기」 → 복원 0 + 카드 「다시 켜졌어요」(거짓 복원 알림은 생기지 않는 쪽 · 진리표 행 10).

### ⑵ 폴더 권한 창 = 안내 먼저 (📌 A-3 = A · `main.rs` + `ui/src/main.ts` 한 덩어리)
- 백엔드: 확인 본체를 `probe_folder_permissions`(거부 폴더마다 perm-warning · 거부 목록 반환)로 떼고, 명령 2개 추가 — `folder_access_guide_needed`(맥 새 설치 첫 실행이면 true · 같은 스냅숏) · `request_folder_access`(UI 가 안내를 그린 **뒤** 부르는 권한 확인 · 사용자가 고를 때까지 기다림).
- setup: `if !ui_drives_folder_access(true, gui_onboarded_before, false) { nudge_folder_permissions(&handle); } else { 60초 폴백 }` — 첫 실행이면 부르지 않고 UI 가 이끈다. 재실행·갱신(서명 교체 뒤 재허용 유도)은 종전대로.
- UI(`ui/src/main.ts` perm-warning 리스너 바로 뒤): `folder_access_guide_needed` 가 true 면 sticky 안내 토스트(「📁 곧 macOS 가 폴더 접근을 여쭙니다」 — 왜 필요한지 · 허용을 눌러 달라 · 거절해도 앱은 켜져 있고 바꾸는 곳) → 프레임 + 1.5초 → `request_folder_access` → finally 안내 내림. await 없이 띄워 뒤 리스너 등록을 막지 않는다. 거절 원인 문장은 기존 perm-warning 토스트가 낸다.
- 플랫폼 분기는 함수 본문 안(`cfg!`) — 최상위 `#[cfg]` 신규 아이템 금지 핀(blockb_no_new_file_level_cfg_gated_items) 준수.
- 검증 1R 로 더한 것(6a7e5127):
  - `first_measure_wins(cell, measure)` — 스냅숏 「첫 값이 이긴다」 불변식을 행동시험 가능한 한 함수로(opus B-1 · 캐시를 지우면 새 설치 Apply 가 되살아나는데 종전 시험이 못 잡았다).
  - 첫 실행 백엔드 폴백 — UI 가 60초 안에 `request_folder_access` 를 **시작**하지 않으면(`FOLDER_ACCESS_STARTED`) 종전 nudge 로 권한 창을 띄운다(opus B-2 · 화면 초기화가 중간에 끊겨도 권한 창 0 이 되지 않게 · 안내 없는 창이 창이 아예 없는 것보다 낫다).
  - `FOLDER_ACCESS_ASKED` — 같은 프로세스에서 한 번 물었으면 웹뷰 새로고침에 안내를 다시 띄우지 않는다(agy ①).
  - `boot_path_is_canonical()` — 안전모드(비정규 실행 위치)면 UI 안내·권한 창도 없음. setup 조기 반환 레인과 같은 방향(Fable ②).
  - UI `catch` — 권한 확인 실패가 처리 안 된 거부로 새지 않게(opus B-4).
- 권한 창 자체의 설명(368fe884 · master#cefef297): `src-tauri/Info.plist` 에 `NSDesktopFolderUsageDescription`「AI 직원들이 데스크탑의 CYSjavis 폴더에서 일할 수 있도록 허용을 눌러 주세요.」 · `NSDocumentsFolderUsageDescription`「AI 직원들이 문서 폴더에 있는 작업도 도울 수 있도록 허용을 눌러 주세요.」. 앱 안내 토스트도 같은 규칙(괄호·전문 용어 0 · 「~해 주세요」). 한국어 단일(기존 마이크 키와 같은 방식 · 현지화 파일 없음).

## 3. 진리표 (시험 `v116_firstrun_restore_truth_table` · 판정 입력 = 판정 시점 디스크 사실 전부)

| # | 상황 | 마커 | 스탬프 | 팩(종전 증거) | 이 기동 전 온보딩 마커 | 부서 | 기준선(종전 증거) | 수리본 |
|---|---|---|---|---|---|---|---|---|
| 1 | 새 설치(설치기·데몬·온보딩이 팩을 먼저 깜) | 없음 | 없음 | 있음 | 없음 | 0 | **Apply ✗** | RecordStampOnly |
| 2 | 새 설치(팩도 아직 없음) | 없음 | 없음 | 없음 | 없음 | 0 | RecordStampOnly | RecordStampOnly |
| 3 | 갱신(스탬프 = 구판) | 없음 | 1.1.4 | 있음 | 있음 | 0 | Apply | Apply |
| 4 | 갱신(인앱 마커) | 있음 | 1.1.5 | 있음 | 있음 | 0 | Apply | Apply |
| 5 | 스탬프만 없음(전에 온보딩 끝남) | 없음 | 없음 | 있음 | 있음 | 0 | Apply | Apply |
| 6 | 스탬프·온보딩 마커 없음 + 부서 ≥1(마커 이전 판) | 없음 | 없음 | 있음 | 없음 | 1 | Apply | Apply |
| 7 | 부서 레지스트리 해석 불가 | 없음 | 없음 | 있음 | 없음 | Err | Apply | Apply |
| 8 | 팩만 없음(스탬프 = 현재판) | 없음 | 1.1.6 | 없음 | 있음 | 0 | Skip | Skip |
| 9 | 팩만 없음 + 스탬프 없음(온보딩 이력 있음) | 없음 | 없음 | 없음 | 있음 | 0 | **RecordStampOnly ✗**(복원 누락) | Apply |
| 10 | ~/.cys 만 지워진 기기(UI 배치 저장본은 남음) — master 지정 행 | 없음 | 없음 | 있음(데몬이 다시 깜) | 없음 | 0 | **Apply ✗** | RecordStampOnly → 복원 0 · 「직원 복귀」 알림 0 · UI 카드 = 기록 없는 「다시 켜졌어요」 1장 |
| 11 | 마커·스탬프 이전 판(≤0.12.50) + 부서 0 — **수용 한계**(agy ④ · Fable ①) | 없음 | 없음 | 있음 | 없음 | 0 | Apply | RecordStampOnly — 새 설치와 디스크 사실이 같아 가를 수 없다. 팩은 같은 기동의 GUI 온보딩(마커 없음 → init-pack)과 cysd 스윕이 반영 · 본부 좌석은 cysd 콜드부트 auto-restore(`src/bin/cysd/main.rs:1596` · `javis_phoenix.py:2771` include_master)가 덮고 · 구 데몬이 살아 있던 갱신은 UI 스큐 감지 → rotate_daemon → 마커 → Apply. 빠지는 것 = 그 1회의 앱 복원 알림·카드뿐 |
| 12 | 동일판 재실행 | 없음 | 1.1.6 | 있음 | 있음 | 0 | Skip | Skip |

기준선 측정 = 같은 표를 종전 증거(팩 열)로 판정 → **정확히 4행 어긋남**(1 · 9 · 10 · 11) — 커밋된 시험 `v116_baseline_pack_evidence_differs_exactly` 가 이 집합을 단언한다(opus B-5). 결함 행 = 1 · 10(새 설치가 복원으로 돎) · 9(종전 누락이 고쳐짐) · 11(수용 한계). 수리본 12/12 초록.

A-3 판정(`v116_ui_drives_folder_access_only_on_mac_first_run`): 맥 + 새 설치 = UI 가 이끎 · 맥 + 재실행/갱신 = setup 자동(종전) · 맥 밖 = 없음(2행) · 같은 프로세스에서 이미 물음 = 재안내 없음 · (명령 쪽) 안전모드 = 없음.

| 첫 실행 권한 창 상황 | 결과 |
|---|---|
| 정상(UI 가 안내 → 요청) | 안내 토스트 → 1.5초 → 권한 창(창 안에 Info.plist 문장) → 끝나면 안내 내림 · 거절 폴더마다 perm-warning 원인 토스트 |
| UI 가 60초 안에 요청을 시작 못 함 | 백엔드 폴백 nudge — 권한 창은 뜬다(안내 토스트 없음 · 창 안 문장은 있음) |
| 웹뷰 새로고침(이미 물음) | 재안내 없음 |
| 웹뷰 새로고침(권한 창 대기 중) | 두 번째 요청도 같은 창의 답을 기다림 · 폴백은 STARTED 로 안 뜸 |
| 안전모드(비정규 위치) | 안내·권한 창 0(setup 조기 반환과 같은 방향) |
| 재실행·갱신 | 종전 setup nudge |

## 4. 시험·기준선·뮤턴트

| 축 | 시험 | 기준선(526325bf 동작) | 수리본 |
|---|---|---|---|
| 복원 판정 | `v116_firstrun_restore_truth_table`(12행) · `v116_baseline_pack_evidence_differs_exactly` · `v116_prior_install_evidence_units` · `v116_snapshot_first_measure_wins` | 종전 증거로 판정 = 4행 어긋남(1·9·10·11 · 결함 2행 + 종전 누락 1행 + 수용 한계 1행) | 초록 |
| 권한 창 주체 | `v116_ui_drives_folder_access_only_on_mac_first_run` · `v116_folder_access_fallback_only_when_ui_silent` | 기준선에 함수 없음(첫 실행에도 setup 이 무조건 nudge) | 초록 |
| 배선 | `v116_firstrun_wiring`(복원 판정 = 새 증거 · `.pack-version` 부재 · 스냅숏이 첫 await·마커 쓰기·복원 판정보다 앞 · 첫 실행 가드 안 nudge 1곳 · 폴백은 else 갈래 · 명령 2개 등록 · 명령 본체 형태 · 시작/물었음 표시 순서 · 스냅숏 = 첫 값 고정 셀 · 확인 본체 맥 전용) | 적색(새 증거·가드 없음) | 초록 |
| UI | `ui/src/permtoast.test.ts` 「첫 실행 폴더 권한 안내(A-3)」 9건(판정 출처 · 안내→대기→요청 순서 · 문구 · finally 내림 · perm-warning 먼저 등록 · await 없이 띄움 · 정확한 판정/대기 형태 · 안내 본문 괄호 0 · Info.plist 두 키 문구) | 적색(덩어리 없음) | 11/11 |

뮤턴트(복제 트리 `cp -c -R` 에서 실행 · 원본 무접촉) — **32종 전부 KILLED**(N3 은 핀 강화 뒤 · D-M1~3 은 디버깅 패스가 찾은 생존분을 핀 강화 뒤 KILLED):

| # | 뮤턴트 | 결과 | 잡은 시험 |
|---|---|---|---|
| R-M1 | 증거 상시 true(=종전 동작) | KILLED | units · 진리표 |
| R-M2 | 레지스트리 해석 불가 → false | KILLED | units · 진리표 |
| R-M3 | 부서 ≥1 검사 삭제 | KILLED | units · 진리표 |
| R-M4 | 판정이 `.pack-version` 복귀 | KILLED | 배선 |
| R-M5 | 스냅숏을 온보딩 뒤로 | KILLED | 배선 |
| T-M1 | nudge 가드 반전 | KILLED | 배선 |
| T-M2 | UI 주도 판정이 첫 실행 무시 | KILLED | A-3 판정 |
| T-M3 | request_folder_access 미등록 | KILLED | 배선 |
| U-M1 | UI 조건 반전 | KILLED | UI 판정 출처 |
| U-M2 | 권한 창을 안내보다 먼저 | KILLED | UI 순서 |
| U-M3 | 안내 내리기 삭제 | KILLED | UI finally |
| U-M4 | 지연 삭제 | KILLED | UI 순서 |
| P-M1 | Info.plist 문서 폴더 키 삭제 | KILLED | Info.plist 핀 |
| P-M2 | Info.plist 문구 괄호·다른 말 | KILLED | Info.plist 핀 |
| N1 | 스냅숏 캐시 우회(매번 재측정) | KILLED | 배선 |
| N2 | 첫 값 고정 셀이 매번 측정 | KILLED | 첫 값 행동시험 |
| N3 | 안내 여부 상시 false | 첫 판 **SURVIVED** → 본체 형태 핀으로 KILLED | 배선 |
| N4 | 권한 확인이 윈도에서만 | KILLED | 배선 |
| N5 | 가드 밖 무조건 nudge 추가 | KILLED | 배선(1곳 계수) |
| N6 | 폴백 상시 발동 | KILLED | 폴백 판정 |
| N7 | 시작 표시 삭제 | KILLED | 배선 |
| N8 | UI 지연 await 삭제 | KILLED | UI 정확한 형태 |
| N9 | UI 판정 반전(!== true) | KILLED | UI 정확한 형태 |
| N10 | UI 지연 0 | KILLED | UI 정확한 형태 |
| N11 | 정규 위치 게이트 삭제 | KILLED | 배선 |
| N12 | 이미 물었음 무시 | KILLED | 배선 |
| D-M1 | 폴백이 STARTED 대신 ASKED 를 읽음 | 디버깅 패스 **SURVIVED** → KILLED | 배선(폴백 형태) |
| D-M2 | 폴백 60초 대기 삭제 | 디버깅 패스 **SURVIVED** → KILLED | 배선(폴백 형태) |
| D-M3 | 정규 위치 판정 반전 | 디버깅 패스 **SURVIVED** → KILLED | 배선(판정기 핀) |
| D-M4 | 폴백 대기 1초 | KILLED | 배선(대기 ≥30초) |
| D-M5 | 폴백이 물었음 안 세움 | KILLED | 배선(폴백 순서) |

전체 회귀(최종 HEAD · CYS_NO_AUTOSTART=1): `cargo test -p cys-app --bins` 172 통과 · 0 실패 · 1 ignored(신규 적색 0) · `cargo build -p cys-app` 경고 0 · `bun test`(ui) 1121 통과 · 0 실패.

시험 환경 준비(작업트리 한정 · 저장소 무변경 · .gitignore 대상): `cargo build -p cys-terminal --bins` 실바이너리를 `src-tauri/binaries/{cys,cysd}-aarch64-apple-darwin` 로 복사(빈 자리표가 target 을 덮은 v115r4 사고 회피) · `src-tauri/resources/pack.tar.gz`(빈 파일)·`pack-manifest.json`(`{}`)·`src-tauri/runtime/.keep` · `ui/dist` = `bun run build`.

격리 재현【모의】: 가짜 HOME(scratchpad) 에서 설치기와 같은 `cys init-pack` 1회 → `.cys/pack/.pack-version`=1.1.5 **있음** · `.cys/.gui-onboarded`·`.cys/depts.json`·`.cys/.last-app-version` **없음** ⇒ 종전 증거 = Apply · 새 증거 = RecordStampOnly. 라이브 무접촉.

## 5. 검증(이종 적대 · 서브에이전트)

| 검토자 | 판정 | 지적 → 처리 |
|---|---|---|
| agy 1R(파일 권한 없음 · diff + 주변 코드 전문 붙임 · 판정문 `~/axdev/master/reports/cysr-116-2026-09-23/hetero-agy-v116-app-firstrun.md`) | **VERDICT: ACCEPT** | ① 새로고침 재안내(P3) → 반영(ASKED) · ② 권한 대기 중 토키오 스레드 막힘(P2) → **기각**(read_dir 은 이미 `spawn_blocking` 안 — diff 에 보임) · ③ 명령 본체 미고정(P3) → 반영(본체 형태 핀) · ④ 마커 이전 판 + 부서 0 행 누락(P3) → 반영(진리표 11행 · 수용 한계) |
| Fable 적대 1R(고위험 = 자가치유 전멸 축 · 읽기 전용) | **VERDICT: ACCEPT** — 「자가치유 전멸 미검출」 | ① 마커 이전 판 갱신 = 앱 복원 알림 상실 · 좌석은 cysd 가 덮음(P3) → 수용 한계로 문서화 · ② 안전모드·데몬 실패 레인에서도 UI 가 권한 창을 띄움(P3) → 안전모드 반영(boot_path_is_canonical) · 데몬 실패 레인은 유지(권한 창은 자기경로 부수효과가 아님) · ③ 온보딩이 계속 실패하는 기기 = 매 기동 첫 실행 안내(P3) → 수용(§8 미결) |
| opus 정밀 디버깅 패스(완료 뒤 · §10) | 제품 P1·P2 결함 0 · P3 4 | P3-1 생존 뮤턴트 3 → 핀 강화 반영 · P3-4 폴백 물었음 → 반영 · P3-2·P3-3 → 수용(§9) |
| opus 성찰·코드검토 1R | 결함 표 B-1~B-10 | B-1(P2) 스냅숏 불변식 무시험 → 반영 · B-2(P2) 첫 세션 권한 창이 UI 하나에 달림 → 반영(60초 폴백) · B-3 rAF 창 가림 지연(P3) → 수용(영구 정지 아님 · 폴백이 60초에 덮음) · B-4 catch → 반영 · B-5 기준선 재현 → 반영 · B-6 → 진리표 11행 · B-7 알람 이력 1건(P3) → 수용 · B-9 서식 결합 핀(P3) → 수용(저장소 관례 · 거짓 적색은 안전 방향) · B-10 ui/src 범위 위반(P2) → **기각**(master#7eb220fb 가 A 로 승인한 범위) |

## 6. 4군 점검
- ① 폭주 큐: 해당 없음 — 복원 판정은 기동당 1회 · 권한 확인은 UI 1회(ASKED) + 폴백 최대 1회(STARTED 로 겹침 차단) · 큐·주입 경로 무접촉.
- ② 무clear 100%+: 해당 없음(컨텍스트·순환 경로 무접촉).
- ③ **자가치유 전멸(핵심 대조군)**: 진짜 갱신 레인(스탬프 ≠ 현재판 · 인앱/rotate 마커)은 `decide_pending_update` 무변경이라 종전대로 Apply → init-pack + spawn_org_restore(진리표 3·4 · 기준선과 동일 판정). 판정이 바뀐 입력은 「스탬프 없음 + 이 기동 전 온보딩 마커 없음 + 부서 0」 하나뿐 — 새 설치 · `~/.cys` 만 지워진 기기 · 마커 이전 판(≤0.12.50) 기기. 마지막 경우도 본부 좌석은 cysd 콜드부트 auto-restore 가, 구 데몬 생존 갱신은 rotate 마커가 덮는다(Fable 1R 확인 · 코드 경로 대조 · 실행 대조는 VM). 종전 누락 1건(팩·스탬프 없음 + 온보딩 이력)은 이번에 복원이 돌도록 고쳐졌다.
- ④ 전 pane 사망: 해당 없음(좌석 생성·종료 경로 무접촉 · 권한 거절 시 부서 좌석 사망 경로는 1.1.5 대행 + seat.folder_denied 그대로).

## 7. 재현 절차 · VM 체크리스트(master 배정 뒤 1회)
- 단위: `cargo test -p cys-app v116_` · `cd ui && bun test src/permtoast.test.ts`(시험 환경 준비 = §4 끝).
- VM(새 clone · 이 브랜치 빌드 설치):
  1. 설치 직후 첫 실행 — 앱 stderr/로그에 `init-pack` 이 온보딩 1회만(업데이트 반영 `--no-install-hook` 호출 0) · `~/.cys/.last-app-version` = 현재판 · `~/.cys/.pending-restore` 없음 · 「직원 복귀 중/완료」 토스트 0 · 복원 카드 0(T4).
  2. 첫 화면에 안내 토스트 「📁 곧 macOS 가 폴더 접근을 여쭙니다」 → 약 1.5초 뒤 데스크탑 권한 창 → 이어서 문서 권한 창 — **창 안에 Info.plist 문장**이 보이는지 캡처 2장 · 답한 뒤 안내 토스트가 사라지는지.
  3. [허용 안 함] 을 누른 VM 에서 — perm-warning 원인 토스트 · 부서 하나 만들어 좌석이 fd 오도 오류로 죽지 않는지(1.1.5 대행 · seat.folder_denied 문장).
  4. 앱 종료 → 재실행 — 안내 토스트 0 · 권한 창 0(이미 결정) · 복원 0(Skip).
  5. 대조군(자가치유): 스탬프를 옛 판으로 바꾸고(`echo 1.1.4 > ~/.cys/.last-app-version`) 재실행 → 「직원 복귀」 진행·완료 알림 · 좌석 복원 실행(종전 동작 유지).
  6. (선택) 웹뷰 새로고침(Cmd+R) — 안내 재등장 0.
- 윈 실기 체크리스트 1줄(X-3 이월 · 이 티켓 범위 밖): phoenix 원장 위치 실측.

## 8. 성찰(착수 전 · 완료 전)
- 착수 전 설계 성찰: 9단계 원문을 opus 서브에이전트에 필요성 판단부로 적용(설계 1·2·3·4·5·6·8 · 코드 1·3 적용/부분 · 설계 7·코드 2 = 해당 없음 — 저장소 관례가 한국어 주석). ⚠정직: 첫 구현(b5dd7100)이 성찰보다 먼저 들어갔고 성찰은 그 커밋을 대상으로 돌았다(작고 되돌리기 쉬운 변경이라 병행) — 성찰이 낸 수정은 6a7e5127 에 전부 반영.
- 완료 전 성찰(핵심 수정): ⑴ 「첫 실행」 사실을 하나로 — 복원 판정·권한 안내·폴백이 같은 스냅숏을 읽는다(둘이 따로 재면 카드·복원·안내가 서로 다른 말) ⑵ 스냅숏 불변식을 행동시험으로(문자열 핀만으로는 캐시 제거 뮤턴트가 살았다) ⑶ 권한 창이 UI 하나에 달리지 않게 백엔드 폴백 ⑷ 기준선 적색을 커밋된 시험으로(말이 아니라 시험이 증명).

## 9. 정직 고지 · 미결
- 윈도 빌드 【미측정】 — 이 기기에 윈도 대상 툴체인 없음(`rustup target list --installed` = aarch64/x86_64-apple-darwin). 새 코드는 최상위 `#[cfg]` 신규 아이템 0(blockb 핀 초록) · 함수 본문 `cfg!`/`#[cfg]` 블록 · 맥 전용 사용처 2개에 저장소 관례 `cfg_attr(not(target_os = "macos"), allow(dead_code))`. 윈 CI 로 확인 필요.
- VM 실물 【미측정】: 알림 0 · 권한 창 문장 · 거절 시 좌석 생존은 §7 VM 1회로만 닫힌다.
- 수용 한계(P3): ⑴ 마커 이전 판 + 부서 0 = 앱 복원 알림 1회 상실(좌석은 cysd 가 덮음) ⑵ 온보딩이 계속 실패하는 기기(맥 init-pack 실패 · 윈 schtasks 차단)는 매 기동 「첫 실행」 — 안내 토스트가 뜨고(권한은 이미 결정이라 창은 안 뜸) 곧 내려간다 ⑶ 창이 가려져 rAF 가 멈추면 안내→요청이 늦어지고 60초 폴백이 먼저 권한 창을 띄울 수 있다(안내 토스트는 이미 그려져 있음).
- 범위 밖 발견(보고만): ⑴ `.pending-restore` 가 남은 새 설치(설치기·CLI `cys rotate` ④ 실패)는 마커 우선으로 여전히 Apply — 설치기 0.3.36 이 새 설치에서 rotate 를 부르는지 로컬 트리(0.3.27)로는 【미확인】 ⑵ 온보딩 사이드카가 ~/Desktop 을 먼저 읽어 설명 없는 창을 띄우는지 【추정 · 가능성 낮음】 — VM §7-2 캡처로 확인.
- 증류: 「새 설치 판정의 증거는 설치기·데몬·온보딩이 판정 전에 만들지 않는 사실이어야 한다」 — 장기기억 후보(작성은 master 판단).

## 10. 정밀 디버깅 패스(완료 뒤 · opus 서브에이전트 · 범위 526325bf..57da54ac)
- 결과: **제품 코드 P1·P2 결함 0**. P3 4건 — P3-1 시험 구멍(뮤턴트 3 생존 → 반영 · D-M1~3) · P3-2 권한이 이미 결정된 기기의 「첫 실행」 안내 1.5초 헛표시(온보딩 반복 실패 · 공장 초기화 · `~/.cys` 삭제 · 같은 서명 재설치 → 수용 · 기능 손실 0) · P3-3 권한 창 대기 중 새로고침 = 안내 재등장 + 같은 창을 두 스레드가 기다림(tccd 가 한 창으로 묶는지 【미측정】 → 수용) · P3-4 폴백이 물었음 미표시(→ 반영).
- 경계 경로 11개 대조: UI 명령 선측정 · 안전모드 조기 반환 · 데몬 실패 반환 · 맥/윈 온보딩 실패 · 공장 초기화 · rotate_daemon · 대기 중 새로고침 · 폴백·UI 겹침 · 무응답 · 윈/리눅스 컴파일(교차 컴파일 불가 → 조건부 컴파일 모사 조각 `rustc -D warnings` 통과) · `CYS_DEPTS_JSON`.
- 어디까지 뒤졌나: 파일 7개 정독(main.rs 12구간 · main.ts start() 7544-7850 · factory_reset.rs · cys-dept · tauri.conf.json · Info.plist · permtoast.test.ts) · grep 약 14회 · 경로 11개 · 뮤턴트 3개 × 2범위 = 시험 6회 + 모사 컴파일 1회. 반영 뒤 내 쪽 뮤턴트 5종(D-M1~5) 전부 KILLED · 전체 회귀 재실행 초록.
- VM 재현 주의(디버깅 패스 제안): 권한 창 실험은 앱을 Finder 또는 `open -a` 로 열 것 — 터미널에서 바이너리를 직접 실행하면 권한 창의 주인이 터미널로 잡혀 실험이 무효【추정】.
