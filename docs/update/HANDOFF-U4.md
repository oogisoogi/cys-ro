# HANDOFF-U4 — 1.1.8 자동 갱신 U4(앱 쪽 T4-0 집행 · 알림 표시 · 옛 updater 경로 삭제)

- TICKET = `cysr-118-u4-app` · 브리프 [master#41c66e92] · 워커 297(surface:1296 · 계정2 · Opus) · 가지 `u4/app-118`(off `e2515bb0`)
- 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md`(4판) §5-1·§5-2·§5-3·§5-4·§3-12·📌18
- 결정(전부 master-send 원장 대조 성립): [#9c13ffdb] plugins.updater = pubkey 만 존치(A) · [#971bdf3c] 앱 장부 = `app-notify.json`(A) + 접점 칸 정의 채택 · [#9e9cd4ec] 📌18 문구 = 설계 §3-12 그대로 · [#79d67f2b] TODO 자리 · role 재등록(worker-4)
- 커밋(로컬 · push 0): `a30daec0` 앱 Rust 삭제 + 알림 백엔드 · `c70631b5` UI 삭제 + 알림 화면 · `91d09e0b` 도움말·스크립트 · `36e353cc` lib 시험 재조준 2건 · (이 문서·뮤턴트 스크립트 커밋)
- ⚠U2 겹침: `src/update/win.rs` 의 시험 1건(`same_rules_as_app_original`)과 `src/lib.rs` 인구조사 1줄을 고쳤다(제품 코드 0) — U2 가 같은 파일을 고치면 병합 때 이 두 곳을 본다.
- 표식: 【관측】 = 명령 출력으로 확인 · 【추정】 = 근거 있는 추론.

## §0-4판 델타(master#741101b5 · Fable 3R = BLOCK 0 · MAJOR 1 · MINOR 2 → 3건 전부 채택 · 원문 = docs/update/REVIEW-U4-fable-3r.md · untracked)
4판 커밋 `9de28606`(MAJOR-1 SECURITY.md:13 「Tauri updater signatures」 → 배포본 서명 + 우리 피드 minisign 두 겹을 데몬 자동 갱신이 설치 전 확인 · MINOR-1 INSTALL-Windows-KR.md:102 · GUIDE-clean-reset-KR.md:156·161 「업데이트」 → 「갱신」 · ★게이트 구조 = 화이트리스트 6종 폐기 → **README(한/영)가 링크하는 모든 .md 자동 수집**(현재 10) + docs/index.html · 공허 방지 = 알려진 6개 포함 단언 + 파일별 300자 하한 · 음성: 세 파일 각각 옛 판으로 되돌리면 2·1·1 fail) · `99030fcf`(MINOR-2 잠금 핀 결정론화 — 탐침이 300ms 유예 대신 시험의 `.cs-go` **신호**를 기다리고, 시험은 참가자가 서 있는 동안 `ACK_MUTEX.try_lock` · 새 fd `File::try_lock` **비차단 시도**로 두 잠금 보유를 직접 잰다 · 두 프로세스 시험은 부모 프로세스에서 자식이 쥔 `app-notify.lock` 을 시도 → WouldBlock 이어야 함 · `with_ack_lock` 의 시험 훅 `arrive` 삭제 · 주석 「반드시」 삭제 → §9-2 의 「300ms 유예」·「arrive」 서술은 3판 기록으로만 남는다) · `d278832d`(수집 경로 정규화 = URL 해석 · `node:path` 타입 부재 tsc 1건). 실측(격리 env · 01:11–01:13): cys-app **277/0/1** · updnotice 17/0 ×3(0.4s · 3판 2s) · M11(3 FAILED)·M11a(2)·M11b(3) 각 2회 적색 · 뮤턴트 **16/16 생존 0** · bun **2663/71/0** · tsc 0 · 윈 타입체크 오류 0(`File::try_lock` 포함) 【관측】. lib·cys·cysd 는 이 판 변경 0(`src/` 무접촉)이라 3판 측정값 유지.

## §0-3판 델타(브리프 2026-10-07-cysr-118-u4-3r · codex 2R = BLOCK 0 · MAJOR 2 · MINOR 1 → 3건 전부 채택 · 표 = §9-2)
- 3판 커밋: `f2c3b0b1`(① 시험 결정론화 · 뮤턴트 M11a·M11b) · `cd29acf3`(② 공개 문서 6종) · (이 문서 — ③ §1 접점 표 ≤80자·한 줄 · §5 ⑦ 갱신 · §9-2).
- ① 병렬 시험 2건(배리어 = `take_at` 직전) → **임계 구역 탐침**(`#[cfg(test)] cs_probe` · 장부 읽은 뒤·쓰기 전) 위 결정론 시험 3건 + 자식 진입점 1: 스레드 take×2(표시 정확히 2) · take→done(정확히 1 · 0 = 적색) · **두 프로세스**(시험 바이너리 `current_exe()` 재호출 · `U4_CS_CHILD_DIR`). updnotice 15 → **17**.
- 뮤테이션 **16/16 적색 · 생존 0**(2판 14 + M11a 뮤텍스만 제거 · M11b `lf.lock()` 만 제거 — 각 단독 적색 · M11 문자열은 탐침 줄에 맞춰 갱신) 【관측】.
- 맥 전수(격리 env · HEAD `cd29acf3` · 00:19–00:56): **lib 899/0/1 · cys 584/0 · cysd 2461/0/7 · cys-app 277/0/1**(2판 275 − 병렬 2 + 결정론 3 + 자식 진입점 1) · updnotice **17/0** · bun **2663 pass / 71 skip / 0 fail**(publicdocs 4 = 6종 대상) · tsc 0 · `scripts/win-typecheck.sh` 오류 0 · 측정 뒤 u4 잔존 시험 프로세스 0 【관측】.
- ★측정 사고(정직): 새 좌석의 격리 래퍼가 `TMPDIR` 를 긴 scratchpad 경로로 바꿔 1회차에 cys 4 · cysd 6 · cys-app 2 가 **SUN_LEN(유닉스 소켓 경로 104바이트) 초과**로 적색(`path must be shorter than SUN_LEN` · cysd deadman.rs:276 예산 단언) — 이 가지의 `src/` 변경 0(`git diff a8abfa44 -- src/` 빈 출력) · 래퍼에서 TMPDIR 를 빼고 재측정한 값이 위 줄.

## §0-2판 델타(master#f69113b1 · codex 1R = BLOCK 1 · MAJOR 3 · MINOR 2 → 6건 전부 채택)
- 2판 커밋: `084f45a7`(① 장부 경쟁 직렬화 · ⑤ release_seq · ⑥ notes_ko 80자 한 줄 · ③ 조건부 핀) · `c31138f0`(② 고정 안내 자동 소거 · ⑥ 화면 한 줄) · `2e39b8cd`(④ 공개 문서 현행만 + 게이트 시험) · (이 문서·뮤턴트 확장 커밋).
- 뮤테이션 1판 10 + 2판 4(M11 잠금 없음 · M12 release_seq 무검사 · M13 역순 응답 적용 · M14 폴링 없음) = **14/14 적색**. 2판 잠금이 생기면서 1판 M7(기록 실패해도 표시)이 한 번 생존 → 「잠금은 잡히고 장부 쓰기만 실패」 반례 시험 추가 뒤 적색.
- 표 6행 = §9.
- 2판 맥 전수(23:04–23:19 · 격리 env · 코드·문서 최종본): **lib 899/0/1 · cys 584/0 · cysd 2461/0/7 · cys-app 275/0/1**(1판 270 + 신규 5 = release_seq · 병렬 2 · 장부 쓰기 실패 · macupdate 핀) · updnotice 15/0 · bun **2663 pass / 71 skip / 0 fail**(+ publicdocs 4 · updateresult 신규 4) · tsc 0 · 측정 뒤 u4 잔존 프로세스 0 【관측】.

## §0 한 문단 요약
1.1.8 앱에서 「업데이트」 단추·배지·확인 창·6시간 폴링·updater 플러그인·팩 앱 입구·원작자 J2/WU(윈 시도 기록·확인 실행·스마트 앱 컨트롤 사전 검사)를 지웠다 — 앱이 갱신을 결정·집행하는 코드는 0이다(§5-1). 대신 데몬 러너(U2)가 `state.json` 에 남긴 결과를 **다음 앱 창에서 토스트 1개**로 알리고(§3-12 순서 ①~④ · 결과당 1회 · 중복 ≤1 · 롤백 실패만 하루 1회), 저널을 되살리지 못해 좌석이 0인 상태면 창 아래에 **닫히지 않는 안내 1줄**을 둔다(📌18). 앱은 `state.json` 을 읽기만 하고, 몇 번 보여 줬는지는 같은 폴더의 앱 전용 `app-notify.json` 에만 쓴다(파일당 쓰는 이 하나). 도움말 1줄(§5-4)을 매뉴얼·README·다운로드 페이지에 넣었다.

## §1 U2 접점(병합 때 이름 일치 — master 가 296 에 같은 정의 전달 · [#971bdf3c])
| 파일 | 쓰는 이 | 칸 | 앱의 읽기 규칙 |
|---|---|---|---|
| `<상태 폴더>/state.json` | 러너(U2) **만** | `last_result{result_id, kind, release_seq, version?, notes_ko?}` | `result_id` = 1~64자 `[A-Za-z0-9._:-]` · `kind` ∈ `ok` · `rollback_ok` · `rollback_failed` · `installed_revoked`(그 밖 = 무음) · `version` = 숫자 마디 1~4개(아니면 괄호째 생략) · `notes_ko` = 제어문자·줄 나눔(U+2028/9)·방향 바꿈(U+200E/F·U+061C·U+202A–E·U+2066–9) 하나라도 있으면 통째 거부 · **≤80자**(설계 §6-1 L505 · 검사 = `cys::update::feed::check_notes_ko` 한 벌 · 금지 어휘 5 포함) · 알림 **한 줄**(본문 같은 줄에 「달라진 점: …」 로 잇기 · 설계 §3-12 L339) |
| 같은 파일 | 러너 | `seats_blocked{reason}` | `reason == "journal_unrecoverable"` 일 때만 📌18 고정 안내 · 그 밖·판독 불가 = 안내 없음 |
| `<상태 폴더>/app-notify.json` | 앱 **만** | `pending_notification{result_id, shown_count}` · `last_notified_result_id` · `rollback_failed_last_shown_at`(유닉스 초) | 원자 쓰기 = 임시 파일 → fsync → rename → (유닉스) 폴더 fsync · 깨지면 빈 장부로 읽고 다음 쓰기가 통째로 바꾼다 |
- **병합 때 삭제할 것(③ · 집행 = U2 병합 통합 커밋 master)**: ⑴ 파일 `src-tauri/src/macupdate.rs`(674줄 · 앱 쪽 옛 판정·교체 부품 — 라이브러리 `src/update/mac.rs`·`src/update/macupdate.rs` 가 대신함) ⑵ `src-tauri/src/main.rs` 19-22행 4줄(@`084f45a7` 실측 · 주석 2줄 `// ★(1.1.8 U4 · 설계 §5-1 「옮긴다」) …` · `//   U2 가 데몬 쪽(…)으로 옮긴다. …` · `#[allow(dead_code)]` · `mod macupdate;` — 18행은 앞 모듈의 주석이라 남긴다). 핀 `macupdate_lives_only_in_the_library_after_u2_merge`(main.rs 시험)가 라이브러리 `src/update/mac.rs` 실재 시 ⑴⑵ 부재를 요구하므로, 지우지 않고 병합하면 cys-app 시험이 적색이 된다(의도).
- 앱 장부 잠금 파일 `app-notify.lock`(같은 상태 폴더 · 앱만 쓴다 · 내용 없음) — U2 가 상태 폴더 「전체 − 명시 제외」 스냅샷(§3-5)을 뜰 때 `app-notify.json`·`app-notify.lock` 을 사용자 파일로 볼지 제외할지 U2 판단(앱 장부라 롤백해도 무해 — 되돌아가면 알림이 최대 1번 더 뜰 뿐).
  - ★결정(master#3108fbd1): `app-notify.json`·`app-notify.lock` = 갱신 상태 폴더 소속 · **U2 스냅샷·복원 제외 + `.lock` 은 어떤 경우에도 복원 금지**(갱신 결과를 알리는 파일을 롤백이 되돌리면 안내가 거짓이 된다) — U2 병합 때 master 가 296 쪽 제외 목록에 넣는다.
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
- ④ `macupdate.rs` 는 호출부 0 인 채 남았다(U2 가 데몬 쪽으로 옮기는 중) — 2판: 병합 때 거두지 않으면 핀 `macupdate_lives_only_in_the_library_after_u2_merge` 가 적색이 된다(삭제 줄 = §1).
- ⑤ `packsig.rs` 재현 시험 겨눔 변경 = U2 러너 A2 검증이 생길 때(§2 표 끝 행).
- ⑦ (2판 → 3판) 공개 문서 밖 옛 서술: `ARCHITECTURE-AND-PHILOSOPHY.md`·`docs/INSTALL.md` 는 **3판에서 공개 문서로 편입·정리**(master 번복 · `cd29acf3` · 게이트 6종). 남은 2곳 = 내부 문서·시험 — `docs/DESIGN-factory-reset.md:60`(`.update-attempt.json`) · `cysjavis-pack/bin/tests/run_bootstrap_health.py`(옛 「GUI 인앱 업데이트」 서술) = master 백로그(범위 밖 그대로).
- ⑧ (2판) 📌18 폴링 = 60초 간격이라 seats_blocked 가 풀린 뒤 안내가 사라지기까지 최대 60초 · 상태 변경 이벤트가 생기면(U2) 그쪽으로 바꾸는 것이 낫다.
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
- [x] 3판(브리프 2026-10-07-cysr-118-u4-3r): ① 시험 결정론화 + M11a·M11b · ② 공개 문서 6종 · ③ §1 접점 표 → 맥 전수·뮤턴트 16·윈 타입체크 → 미러 3런 → 【확인요청】
- 배선 사건: 스폰 때 role=worker-3 이 293(lms)과 겹쳐 `cys todo-path` 가 293 의 TODO 를 가리켰다 → 293 파일은 건드리지 않았고(읽기만) 내 TODO 는 별도 파일 → master 지시로 `cys claim-role worker-4` 재등록(21:25 · `cys list` surface:1296 role=worker-4).

## §9 codex 1R 6건 처리표(채택 / 반박 — 근거 = 코드 줄 + 시험)
| # | 등급 · 지적 | 판정 | 수정 sha · 코드 줄 | 시험(뮤턴트) |
|---|---|---|---|---|
| ① | BLOCK · 병렬 두 호출이 shown_count=0 을 함께 읽고 고정 PID 임시 파일을 서로 truncate → 합계 >2 | **채택** | `084f45a7` · `updnotice.rs:286` `with_ack_lock`(프로세스 안 뮤텍스 + `app-notify.lock` `File::lock`) · `take_at`·`done_at` 이 그 안에서 읽기→판정→쓰기 · `write_ack` 임시 파일 = pid·일련·나노초 + `create_new` | `parallel_takes_never_show_more_than_twice_and_keep_the_ledger_valid` · `parallel_take_and_done_keep_the_total_at_most_two` · `no_show_when_only_the_ledger_write_fails`(M11 · M7 적색) |
| ② | MAJOR · 포커스 유지 중 seats_blocked 가 풀려도 안내가 남음 · 역순 응답이 덮어씀 | **채택** | `c31138f0` · `updateresult.ts:59` `latestOnly`(세대 번호) · `:55` `SEATS_NOTE_POLL_MS=60_000` · `main.ts:9114` setInterval · `applySeatsBlockedNote` | 「역순 응답 폐기」 · 「던진 조회 무변경」 · ★「포커스 유지 중 복구」 · 폴링 배선·하한 30초(M13 · M14 적색) |
| ③ | MAJOR · 앱 macupdate 잔존 → 정상 병합이 두 구현을 남김 | **채택 · 집행 = U2 병합 통합 커밋(master)** | `084f45a7` · `main.rs` 시험 `macupdate_lives_only_in_the_library_after_u2_merge`(라이브러리 `src/update/mac.rs` 실재 시 앱 파일·선언 부재 요구 · 아니면 호출부 0) · 삭제 줄 = §1 | 두 조건 실측: 임시 `src/update/mac.rs` 생성 = 적색 · 제거 = 초록(#[ignore] 아님) |
| ④ | MAJOR · 도움말 잔재(Tauri updater · 지운 env 2 · 지운 RPC · 없는 단추 · 「업데이트」 재사용) | **채택**(버전 기록 격리 아님 · 삭제) | `2e39b8cd` · README.md:53·466·509 · README.en.md:62·453·500 · USER-MANUAL 전반(env 2행·앱 명령 4항·증상 1행·실기 블록·한계 1항 삭제 · 나머지 「업데이트」→「갱신」) | `ui/src/publicdocs.test.ts` 4건(문서 4종 「업데이트」·「Update」 0 · 지운 이름 17종 0 · 도움말 1줄 존재 · 공허 방지) |
| ⑤ | MINOR · release_seq 미검사 | **채택** | `084f45a7` · `updnotice.rs:193`(정수 ≥1 아니면 알림 0) | `release_seq_must_be_a_positive_integer`(누락·0·음수·문자열·소수·null)(M12 적색) |
| ⑥ | MINOR · notes_ko 300자·둘째 줄 = 설계 이탈 | **채택** — 설계 §6-1 505행 「`notes_ko` 문자열 ≤80자 · 알림 1줄(제어문자 0 · 금지 어휘 0)」 | `084f45a7` · `updnotice.rs:152`(`cys::update::feed::check_notes_ko` 한 벌 재사용 + 화면용 줄 나눔·방향 바꿈 거부) · `:168` 같은 줄 잇기 · `c31138f0` 화면도 본문 줄바꿈 거부 | `notes_with_control_chars_are_refused_whole`(80 통과 · 81 거부 · 금지 어휘 5 · 줄바꿈 0 · 상한 = lib 상수 대조)(M5 적색) |

## §9-2 codex 2R 3건 처리표(BLOCK 0 · MAJOR 2 · MINOR 1 · 브리프 2026-10-07-cysr-118-u4-3r §1 · 전부 채택)
| # | 등급 · 지적 | 판정 | 수정 sha · 코드 줄 | 시험(뮤턴트) |
|---|---|---|---|---|
| 2R-① | MAJOR · M11 이 두 잠금을 한꺼번에 제거 → 각 잠금 단독 회귀핀 없음 · 배리어가 `take_at` 직전뿐(순차 완주 반례 못 막음) · take/done 시험이 합계 0 도 통과 | **채택** | `f2c3b0b1` · `updnotice.rs` `cs_probe`(#[cfg(test)] · 장부 읽은 뒤·쓰기 전 탐침 · 겹침 시 먼저 들어온 쪽이 나중 기록을 덮게 해 잃어버린 갱신을 결정론화 · `arrive` = 프로세스 뮤텍스 통과 뒤 자동 표기) · `ACK_MUTEX` 모듈 수준으로 | `threads_take_one_at_a_time_inside_the_ledger_section`(정확히 2 · 장부 2 · 세 번째 0) · `take_then_done_inside_the_section_shows_exactly_once`(정확히 1) · `two_processes_take_one_at_a_time_through_the_lock_file`(`current_exe()` 재호출 · `U4_CS_CHILD_DIR`) — M11a(뮤텍스만) · M11b(`lf.lock()` 만) · M11(둘 다) **각 단독 적색** |
| 2R-② | MAJOR · 공개 문서 게이트 4종만 — README 가 링크하는 `docs/INSTALL.md` · `ARCHITECTURE-AND-PHILOSOPHY.md` 에 옛 인앱 갱신 서술 잔존 | **채택**(master 번복) | `cd29acf3` · INSTALL env 2행 삭제 · ARCH §5.6 표 현행화 · 공급망 문장 · 「업데이트」→「갱신」 | `publicdocs.test.ts` DOCS 6종 · 음성: 각 파일 옛 판으로 되돌리면 2 fail |
| 2R-③ | MINOR · HANDOFF §1 접점 표 「300자·둘째 줄」 ↔ §9 「80자·한 줄」 자기모순 | **채택** | (이 문서 커밋) §1 표 = ≤80자 · 한 줄(설계 §3-12 L339 · §6-1 L505) | — |
- 정직(M11a): 맥(flock · 【관측】 M11a 에서 겹침 0)·윈(LockFileEx · 【추정】 핸들 단위 — 윈 실기 미측정) 파일 잠금은 열린 파일 단위라 같은 프로세스의 스레드끼리도 막는다 → 뮤텍스만 빼도 **겹침은 생기지 않는다**. 그래서 M11a 의 적색은 행동(경쟁)이 아니라 탐침의 「임계 구역 안에서 프로세스 뮤텍스가 잡혀 있어야 한다」(`.cs-mutex-free`) 단언에서 나온다(구조 핀). 뮤텍스의 실제 몫 = fcntl 식 프로세스 단위 잠금 플랫폼 대비 이중 방어.
- 1회차 실측 사고(고침): 자식 프로세스 시험이 처음엔 M11b 에서 **생존** — 부모가 다른 병렬 시험 때문에 자기 프로세스 뮤텍스에서 기다리는 동안 자식의 300ms 유예가 흘러 순차가 됐다. → 프로세스 시험은 「도착」을 뮤텍스 **통과 뒤** 코드가 적게 바꿈(`arrive`) → 2회 연속 적색.
