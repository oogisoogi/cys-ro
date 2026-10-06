# HANDOFF-U4 — 1.1.8 자동 갱신 U4(앱 쪽 T4-0 집행 · 알림 표시 · 옛 updater 경로 삭제)

- TICKET = `cysr-118-u4-app` · 브리프 [master#41c66e92] · 워커 297(surface:1296 · 계정2 · Opus) · 가지 `u4/app-118`(off `e2515bb0`)
- 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md`(4판) §5-1·§5-2·§5-3·§5-4·§3-12·📌18
- 결정(전부 master-send 원장 대조 성립): [#9c13ffdb] plugins.updater = pubkey 만 존치(A) · [#971bdf3c] 앱 장부 = `app-notify.json`(A) + 접점 칸 정의 채택 · [#9e9cd4ec] 📌18 문구 = 설계 §3-12 그대로 · [#79d67f2b] TODO 자리 · role 재등록(worker-4)
- 커밋(로컬 · push 0): `a30daec0` 앱 Rust 삭제 + 알림 백엔드 · `c70631b5` UI 삭제 + 알림 화면 · `91d09e0b` 도움말·스크립트 · `36e353cc` lib 시험 재조준 2건 · (이 문서·뮤턴트 스크립트 커밋)
- ⚠U2 겹침: `src/update/win.rs` 의 시험 1건(`same_rules_as_app_original`)과 `src/lib.rs` 인구조사 1줄을 고쳤다(제품 코드 0) — U2 가 같은 파일을 고치면 병합 때 이 두 곳을 본다.
- 표식: 【관측】 = 명령 출력으로 확인 · 【추정】 = 근거 있는 추론.

## §0 한 문단 요약
1.1.8 앱에서 「업데이트」 단추·배지·확인 창·6시간 폴링·updater 플러그인·팩 앱 입구·원작자 J2/WU(윈 시도 기록·확인 실행·스마트 앱 컨트롤 사전 검사)를 지웠다 — 앱이 갱신을 결정·집행하는 코드는 0이다(§5-1). 대신 데몬 러너(U2)가 `state.json` 에 남긴 결과를 **다음 앱 창에서 토스트 1개**로 알리고(§3-12 순서 ①~④ · 결과당 1회 · 중복 ≤1 · 롤백 실패만 하루 1회), 저널을 되살리지 못해 좌석이 0인 상태면 창 아래에 **닫히지 않는 안내 1줄**을 둔다(📌18). 앱은 `state.json` 을 읽기만 하고, 몇 번 보여 줬는지는 같은 폴더의 앱 전용 `app-notify.json` 에만 쓴다(파일당 쓰는 이 하나). 도움말 1줄(§5-4)을 매뉴얼·README·다운로드 페이지에 넣었다.

## §1 U2 접점(병합 때 이름 일치 — master 가 296 에 같은 정의 전달 · [#971bdf3c])
| 파일 | 쓰는 이 | 칸 | 앱의 읽기 규칙 |
|---|---|---|---|
| `<상태 폴더>/state.json` | 러너(U2) **만** | `last_result{result_id, kind, release_seq, version?, notes_ko?}` | `result_id` = 1~64자 `[A-Za-z0-9._:-]` · `kind` ∈ `ok` · `rollback_ok` · `rollback_failed` · `installed_revoked`(그 밖 = 무음) · `version` = 숫자 마디 1~4개(아니면 괄호째 생략) · `notes_ko` = 제어문자·줄 나눔(U+2028/9)·방향 바꿈(U+200E/F·U+061C·U+202A–E·U+2066–9) 하나라도 있으면 통째 거부 · 300자 상한 · 성공 알림에만 둘째 줄 |
| 같은 파일 | 러너 | `seats_blocked{reason}` | `reason == "journal_unrecoverable"` 일 때만 📌18 고정 안내 · 그 밖·판독 불가 = 안내 없음 |
| `<상태 폴더>/app-notify.json` | 앱 **만** | `pending_notification{result_id, shown_count}` · `last_notified_result_id` · `rollback_failed_last_shown_at`(유닉스 초) | 원자 쓰기 = 임시 파일 → fsync → rename → (유닉스) 폴더 fsync · 깨지면 빈 장부로 읽고 다음 쓰기가 통째로 바꾼다 |
- 상태 폴더 = `cys::update::buildinfo::state_dir()`(U1 · 맥 `~/.cys/update` · 윈 `%LOCALAPPDATA%\cys-update` · 디버그 빌드만 `CYS_UPDATE_STATE_DIR`).
- `state.json` 을 못 읽으면(손상·권한) 앱은 아무것도 보여 주지 않는다(추측 금지) · 앱 장부 쓰기가 실패하면 토스트도 없다(② 없이 ③ 금지).
- 📌18 의 「cysd 복구 대기 rc」 읽기(설계 §3-12 판정 줄)는 하지 않았다 — 앱은 `seats_blocked` 하나로 고른다(rc 는 U2 부팅 가드의 몫 · U2 가 복구 대기 때 `seats_blocked` 를 반드시 적어야 안내가 뜬다 = U2 확인 항목).

## §2 삭제표(설계 §5-2 v1.1.7 줄 → e2515bb0 실측 줄 · 시험 · 커밋)
| 구분 | e2515bb0 자리(실측) | 처리 | 시험 |
|---|---|---|---|
| 플러그인 의존·등록 | `src-tauri/Cargo.toml:14` · `main.rs:11` · `main.rs:8894` · `capabilities/default.json:6` | 삭제 · Cargo.lock −328줄 | cys-app 빌드·시험 초록 |
| 설정 | `tauri.conf.json:47-54` | **endpoints 만 삭제 · pubkey 존치**([#9c13ffdb] — tauri-cli 2.11.4 `interface/rust.rs:855-874` 가 `createUpdaterArtifacts` 켜짐이면 `plugins.updater.pubkey` 필수) · `createUpdaterArtifacts`(`:25` · `tauri.windows.conf.json:4`) 유지 | 앱이 이 칸을 읽는 코드 0(grep) |
| J2·WU 도우미·명령 | `main.rs:3359-3391` · `:3398-3631`(`knob_turned_off` 3392-3397 만 남김) | 삭제(DECISION-TABLE §0 14 각주) | 시험 j2_* 9 · wu_* 4 · r1fua_* 6 · j2 배선 2 삭제 |
| Rust 명령(업데이트) | `main.rs:7481-8280`(build_updater* ~ pack_binary_too_old) · `:8294-8484`(install_update · install_update_plugin · install_update_checked_windows) | 삭제 · 맥 집행 함수 = **U2 로 이동**(`macupdate.rs` 는 `#[allow(dead_code)]` 로 남김 · 병합 때 거둠) | — |
| 팩 채널 앱 입구 | `main.rs:8585-8824`(install_pack_update ~ parse_reinject_counts) · check_pack_update 계열은 위 범위 안 | 삭제(§3-8 · 📌4) | parse_reinject_* 2 · install_pack_update_warns 1 · pack_binary_too_old_gate 1 · u9_* 9 삭제 |
| 핸들러 | `main.rs:8964-8976`(10개) | 삭제 · 새 3개 등록 | — |
| ★cys-app 핀 4건(U4 추가 10-06 07:2x) | `j2_install_update_records…`(`:12181`) · `r1fua_checked_launch_command…`(`:12487`) · `r1fua_windows_branch_restamps…`(`:12584`) · `wu_install_update_has_a_checked_windows_branch…`(`:12290`) | 경로와 함께 삭제 | — |
| 시험(endpoint) | `main.rs:9429-9578`(4건) | 삭제(앱이 latest.json·endpoint 를 읽지 않음) | — |
| 시험(재조준) | `wu_update_launch_module…`(`:12407`) · `gui_spec_w3…` · `r2fui_app_knob…` | 재조준(플러그인 고정 단언 · 지운 두 지점 → 음성 단언 · 남은 노브 1) | 초록 |
| UI | `ui/index.html:29` · `main.ts:26-27,173`(import) · `:6909-7225`(자동 업데이트 블록 · X2-W 윈 문안 · `T_SAC`/SAC 사전 검사 `:7112·7151`) · `:7635-7675`(promptPackInstall·onUpdateButton) · `:9467-9470`(J2 pull) · `:9647-9766`(듣개 6) · `:9990-10022`(폴링·자동 시험) · `:10512-10531`(J2 pull 정의) · `:10717`(배선) | 삭제 | — |
| UI 파일 통째 | `updateplan.ts` · `restartpending.ts` · `updatenotice.ts` · `updatestate.ts`(+ 각 시험) · `updatewiring.test.ts` · `updatebutton.test.ts` | 삭제 | — |
| UI 시험 재조준 | `topbarlabels:29-30,45` · `brandbadge:68` · `toastraw:42,46-58` · `toastttl:6,25,33,46,64,77,100,112-199,235-244` · `staleclaims ④` · `deptprogresswiring`(setInterval 11→10) · `hiddenpair`(배지→고정 안내) | 재조준 | bun 초록 |
| 문구 | `toastttl.ts:52-53`(upd-bin·upd-pack) · 남은 「업데이트」 사용자 문구 4곳(자기승인 · 스큐 배지 · update-error 제목/본문) | 삭제 · 「새 판」 말투(동작 무변경) | grep 0 |
| 정리 | `scripts/build-macos-signed.sh:243` | `idoforgod cys-terminal` → `oogisoogi cys-ro` | — |
| 퇴역 | `scripts/tests/mutants-darwin-update.py` m7(restart_after_update 겨눔) | 주석 퇴역 | — |
| **하지 않음** | `src/packsig.rs:565-618`(플러그인 minisign 재현 · `updater_bridge_old_signed…`) | **그대로 둠** — 설계는 「러너 A2 검증 시험으로 겨눔 변경」이나 러너 A2 검증 함수가 아직 없다(U2). 현 시험은 §5-3 다리 기간 동안 1.1.7 이하 앱(플러그인)의 판정 재현으로 여전히 유효 · 플러그인 크레이트 의존 0 | lib 초록 |

## §3 시험(전부 격리 env · 실 `~/.cys` 쓰기 0)
- cys-app: 기준선 296 → 삭제 37 → **270 passed / 0 failed / 1 ignored**(`updnotice` 11 신규) 【관측】.
- 뮤테이션 `scripts/tests/u4-mutants.py` **10/10 적색 · 생존 0**: M1 ② 표시 전 기록 생략(순서 바꿈) · M2 shown_count 미증가 · M3 중복 무제한 · M4 롤백 실패 하루 1회→매번 · M5 notes 제어문자 통과 · M6 좌석 0 사유 무시 · M7 기록 실패해도 표시 · M8 UI ③④ 뒤바꿈 · M9 UI 고정 안내 innerHTML · M10 UI 모르는 토스트 id 통과 【관측】.
- UI: 기준선 2807 pass / 81 skip / 0 fail → **2655 pass / 71 skip / 0 fail**(삭제 파일 6개분 · 휴면 레인 skip 10 함께 삭제) · `tsc -p tsconfig.check.json` 오류 0 【관측】.
- 윈 타입체크 `scripts/win-typecheck.sh`: **오류 0** · cys-app 경고 = 기준선 휴면 dept 함수 7 + `knob_turned_off` 1(남은 유일 소비자 `dept_create_stream_from_env` 가 e2515bb0 에서도 호출부 0 — 실측) 【관측】.
- Rust 3묶음(`cargo test -p cys-terminal --lib --bins --no-fail-fast` · 격리 env) 【관측】:
  - 1차(21:46–22:07): lib 897/**2** · cys 584/0 · cysd 2460/**1**. lib 2 = 이 티켓이 지운 앱 코드를 겨누던 시험(`spawn_policy_tests::raw_command_new_census_is_frozen` — main.rs 원시 Command 38→34 · `update::win::tests::same_rules_as_app_original` — 앱 SAC 판독기 삭제) → `36e353cc` 로 재조준. cysd 1 = `alert_route::drills::drill_edge_loop_clear_signals_are_never_held_by_the_hourly_cap` — **이 가지의 `src/bin` 변경 0**(`git diff e2515bb0 -- src/bin` 빈 출력) · 단독 1회 + 훈련 묶음 46/46 × 3회 초록 · 당시 부하 평균 5.9~7.5(U2 296 병행 빌드·시험) → 환경(부하) 의존 적색으로 분리.
  - 2차(22:10–22:26 · 재조준 뒤): **lib 899/0/1 ignored · cys 584/0 · cysd 2461/0/7 ignored** · 뒤이어 cys-app 270/0/1 · 측정 뒤 u4 잔존 프로세스 0.
- 문구 grep(앱 UI · 주석 제외 · 문자열만): 「업데이트/Update」 **0건**. 「설치」 남은 것 = 전부 갱신과 무관(완전 초기화 「설치 초기 상태」 · 안전모드 「설치 위치」 · 설치본 손상 「재설치」 · 셸 CLI 설치 · 첫 설치 온보딩) + §3-12 알림 표 문구(롤백 실패 · 📌18 — 설계 문면 그대로 · [#9e9cd4ec]). 앱 Rust 사용자 문자열 「업데이트」 0(남은 것 = 식별자 `PendingUpdatePlan` · 시험 자료).

## §4 master 정정 몫(문면 · 코드 아님)
1. 설계 §5-2 「plugins.updater 블록 통째 삭제」 → 「endpoints 삭제 · pubkey 존치(빌드 도구 전용 칸)」([#9c13ffdb]).
2. 설계 §3-12 「state.json 의 pending_notification·last_notified_result_id」 → 「같은 상태 폴더의 앱 전용 `app-notify.json`」(+ `rollback_failed_last_shown_at`)([#971bdf3c]).
3. 브리프 §4 「📌18 안내는 다시 설치로 유도하지 않는다」 = master 오기 → 설계 §3-12 문구 그대로([#9e9cd4ec]).

## §5 남은 위험·이월(정직)
- ① 실기 미확인: 토스트·고정 안내는 코드·단위 시험·소스 핀으로만 확인했다(실 앱 창에서 띄워 보지 않음 — 러너가 아직 `state.json` 을 쓰지 않는다 · U2 병합 뒤 실기 1회 권고).
- ② 1.1.7 이하 → 1.1.8 길: 옛 앱의 「업데이트」 단추가 `latest.json`(§5-3 다리)을 읽는다 — 이 티켓은 앱 쪽 읽기만 지웠고 발행 쪽 다리(release.yml·pack-release.yml)는 무접촉(U3).
- ③ H⑬(build-info `features` 정본 ID · V7): 앱은 features 를 읽지 않는다(갱신 결정 0) → 이 티켓 코드 0. 정본 ID 목록은 U2·master.
- ④ `macupdate.rs` 는 호출부 0 인 채 남았다(U2 가 데몬 쪽으로 옮기는 중) — 병합 때 `mod macupdate;` 와 파일을 거두지 않으면 죽은 코드가 계속 남는다.
- ⑤ `packsig.rs` 재현 시험 겨눔 변경 = U2 러너 A2 검증이 생길 때(§2 표 끝 행).
- ⑥ 롤백 실패 「하루 1회」는 벽시계 24시간 간격이다(시계가 하루 넘게 뒤로 간 기록은 믿지 않고 다시 보여 준다 · 그보다 작은 뒤로 감은 기다린다).

## §6 소요 · 계수(실측)
| 기준점(실측 · 출처) | 시각 |
|---|---|
| 브리프 도착(원장 `ts`) | 21:21:01 |
| 첫 【결정필요】 발신(plugins.updater · 인박스 append 출력) | 21:24:13 |
| 【질문】 app-notify.json 발신(Rust 삭제·cys-app 1차 초록 259/0 뒤) | 21:29:53 |
| 【결정필요】 📌18 문구 발신(UI 삭제 tsc 0 뒤 · 알림 모듈 착수 전) | 21:31:29 |
| 뮤테이션 10/10 · 윈 타입체크 · 문서 반영 뒤 `date` | 21:46 |
| Rust 3묶음 시작(로그 `start`) | 21:46:01 |
- 단계별 분할은 위 기준점 사이 보간이다(【추정】) — 합계(브리프 도착 → 커밋 3개) ≈ 27분은 실측.
- 계수: U4 1판 = 삭제 ≈4,000줄 + 신규 ≈700줄 · 코드·시험 몫 ≈27분(1판 상한 4h 대비) — 삭제 위주 티켓의 계수로 쓸 것(Rust 3묶음 재측정 시간 별도).

## §7 재현
```
# 격리 래퍼(예: scratchpad isoenv.sh — HOME·CYS_* 를 시험 폴더로) 아래에서
cargo test -p cys-app                      # 270/0/1
cargo test -p cys-app updnotice            # 11/0
U4_ISOENV=<래퍼> python3 scripts/tests/u4-mutants.py   # 10/10 적색
(cd ui && bun test && bunx tsc -p tsconfig.check.json)
sh scripts/win-typecheck.sh                # 오류 0
```
- cys-app 빌드 전제(git 제외 · 로컬만): `src-tauri/binaries/{cys,cysd}-aarch64-apple-darwin`(이 작업트리 디버그 빌드 사본) · `src-tauri/resources/{pack.tar.gz(빈), pack-manifest.json("{}")}` · `src-tauri/runtime/` · `ui/dist/index.html` 자리표시.

## §8 작업 목록(옛 docs/update/TODO-U4.md 를 합침 · master#79d67f2b — git 제외 대상이 아니라 여기에 합치고 파일은 지움)
- [x] 0. 브리프 원장 대조(41c66e92 · submitted=yes) · 설계 §3-12·§5 · TICKETS U4 · DT §0 14 각주 정독
- [x] 1. §5-2 삭제 목록 — 현 코드 위치 실측(e2515bb0 줄 · §2 표) · 1a 플러그인·설정 · 1b Rust 명령·J2·WU·팩 입구·핸들러 · 1c UI · 1d 시험(삭제·재조준)
- [x] 2. §5-3 latest.json 다리 = 앱 읽기 0(앱 쪽 latest_json_url·fetch_latest_json·same_version 분기 삭제 · 발행 쪽 무접촉)
- [x] 3. §3-12 알림(①~④ · 중복 ≤1 · 롤백 실패 하루 1회 · text node · notes_ko 제어문자 거부)
- [x] 4. 📌18 좌석 0 고정 안내
- [x] 5. §5-4 도움말 1줄
- [x] 6. 시험: 단위 + 뮤테이션 + ui tsc/bun + 윈 타입체크 + 문구 grep · Rust 3묶음 = §3·§6
- [x] 7. 커밋 묶음 · HANDOFF-U4 · 【확인요청】
- 배선 사건: 스폰 때 role=worker-3 이 293(lms)과 겹쳐 `cys todo-path` 가 293 의 TODO 를 가리켰다 → 293 파일은 건드리지 않았고(읽기만) 내 TODO 는 별도 파일 → master 지시로 `cys claim-role worker-4` 재등록(21:25 · `cys list` surface:1296 role=worker-4).
