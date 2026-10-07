# HANDOFF-U2 — 1.1.8 데몬 자동 갱신 U2(교체·롤백·러너·복구 · 데몬·CLI 쪽) · TICKET=cysr-118-u2-runner

> 브리프 = [master#71f53d34](파일 정본 `~/axdev/master/briefs/2026-10-06-cysr-118-u2-runner.md`) · 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md`(4판 · U1 편입).
> 가지 `u2/runner-118` off `e2515bb0` · 워커 = worker-2(계정2 · Opus) · 커밋 = `git log --oneline e2515bb0..HEAD`.

## §0-8 후속 3판 델타(master#1bfaba79 · 원문 = `docs/update/REVIEW-U2F-{agy,opus}-2r.md`(ignored) · 착수 12:40 · 2판 게이트 c8666da4 = 유효 PASS(master#1a4f6b3c))
- **이월**: 2판 검수 = agy 2R(BLOCK 0 · MAJOR 0 · MINOR 1) · Opus 2R(BLOCK 0 · MAJOR 2 · MINOR 8) · codex = 한도 0 · master 채택 ①~⑨.
- **끝난 것(커밋 · 각 뮤턴트 녹/적 확인)**:
  | # | 지적 | 커밋 | 고친 곳 · 시험 · 뮤턴트 |
  |---|---|---|---|
  | ① M1 | 재구성 원천(사본·candidate) 무결성 없이 S9 승격(새 crc 세탁) · S9b 재실행 = 해시만 | 7a84de14 | `runner::verify_journal_copy`(crc · 계보 · 원점 · snapshot_dir · S9 이상) · `Journal::check` 공개 · `auto::verified_candidate`(candidate.json 의 U 서명 본문 재검증 → 본문 행으로 자산 재생성 · 실패 = 빈 후보) · (윈) 사본 stage 해시 = 후보 행 · `realops::verify_stage_installer`(S9b 재실행 전 stage_path = 원점 stage · 크기·sha256 = 후보 행 · A2 서명) · 시험 Sim 「tamper」 · `reconstruct_new_needs_restored_candidate_of_the_same_release`(파일 asset 칸 변조 무시 · 남의 키 = 빈 후보) · `win_s9b_rerun_reverifies_stage_installer_before_running_it` · U2-COPYCHECK · U2-CANDVERIFY · U2-STAGESIG · 음성 대조: 사본 값 변조 = **재구성 불가**(롤백 아님 — 롤백 칸도 그 사본에서 오므로) |
  | ④ m2 | 새 판 재구성에서 journal_corrupt 신호 소실 | 3e1fbdf8 | `Ops::signal`(결과 기록 밖 · RealOps = notify::signal) · Sim `signals == [JournalCorrupt]` + `records == [Ok]` · U2-RECONSIGNAL · **설계 §3-11 ④ 개정 제안 1줄**: 「새 판 재구성 = 즉시 신호 `update.journal_corrupt` 1통(상담소 신호) + 결과 기록은 정상 행의 ok/rollback 하나」 |
  | ⑤ m3 | 보조 사본 실패가 S9~S11 전진을 멈춤 | 3e1fbdf8 | `enter` 사본 실패 = 1줄 + 전진 · Fault `copy_fail` · `journal_copy_failure_is_recorded_but_never_stops_forward_progress` · U2-COPYSTOP |
  | ⑦ m5 | 링크 지문 = 대상 내용 없음 | 3e1fbdf8 | `L:<대상>:<따라간 내용 sha256 · 없음 - · 폴더 D>` · `pack::tests::plan_fingerprint_follows_symlink_target_content` · U2-LINKFP |
  | ⑧ m7 | 윈 RB_SWAPPED 자산 재받기 0 | 3e1fbdf8 | 재검증 실패 시 보관소 1회 재받기(실패 = 1줄 · 판정은 뒤 재검증) · `win_rollback_refills_missing_rollback_assets_from_archive` · U2-RBFILL |
  | ⑨ m8 | containment = remove_stage 뿐 | 01f7ce07 | `snapshot::remove_dir_within` 공용 문 · 아래 grep 목록 · `pack_backup_cleanup_deletes_only_inside_backup_root` · U2-WITHIN |
  | ⑥ m4 · agy | 메모 「위조 방지」 과장 · 보류 비가시 | d5b43276 | `cys doctor` `pack-auto-hold`(WARN + 사유 · 손상 WARN) · `doctor_shows_pack_auto_hold_with_reason` · 메모 = 정확한 입력 키(서명 매니페스트 바이트 + 지문)에만 적중 · 자기 sha256 = 손상 검사 · **HMAC 불요 근거**: 같은 계정이 쓰는 파일이라 비밀 키도 같은 계정 손에 있다(이득 0) — 위조의 최대 결과 = 자동 팩 갱신 보류 + doctor WARN(보이는 보류) |
  | ③ m6 | ⑫ S2 배선 증명 0 | 470d8639 | `win_s2_fetches_rollback_assets_before_candidate_download_and_daemon_stop`(후보 받기·rotate 전 · 자식 호출 0) · U2-S2FILL · `fill_installer_dir` seq 0 = Err(U5 규칙) |
  | ③ m1 | 새 판 재구성 성공 경로 RealOps 증명 0 | 9b045043 | `new_reconstruct_success_path_through_real_ops_reaches_done_with_s11`(실 recover · 서명 candidate 복원 · 실 rotate · 실 S11 installers/9·수용 기록 · DONE · last_result ok) · 주입 = 맥 codesign 정식 자리 판정 · V1~V9 두 곳(cfg(test)) |
- **⑨ 경로 재료 grep 목록**(`grep -n 'remove_dir_all\|remove_file' src/update/{runner,realops,snapshot}.rs`): 삭제 = `remove_stage`(stage/<origin>) · `pack_backup_cleanup`(저널 snapshot_dir 부모) · commit 세대 정리(backup_root 목록) · `pack_backup_sweep` · `pack_txn_end`(pack-<txn>) · `pack_user_snapshot`(pack-<txn>/user) → 전부 `remove_dir_within` · 쓰기 = S8 스냅샷 자리·`pack_user_snapshot` = `valid_txn` 토큰만 · `quarantine_dir` 열쇠 = 영숫자·`-` · 고정 이름(installers/<u64> · `.<seq>.tmp` · `.<seq>.fill.tmp` · mac staged_path(seq)) = 재료 안전.
- **② M2(U5 편입 뒤 · merge fb6fbf37 · 충돌 1 = check.rs N7 덩이 → U5 정본 채택)**: ⓐ **N7 윈 검사 존치**(U5 `rollback_assets_ok_at` + `installer_assets_ok` · 2판의 「자산 유무로 보류 안 함」 철회 → `--check` 의 N7 윈 = 실제 재검증 결과 = ③ 표기 수리) ⓑ 러너 S0 `auto::retry_after_n7_fill` — 윈 + 첫 보류 = N7(순서상 마지막 = 유일한 보류)이면 그 주기에서 `realops::fill_rollback_assets_net`(보관소) 1회 → 성공 = `run_check` 다시 · 실패 = 같은 보류 + `state.json last_defer.detail` 사유(다음 주기 재시도 · 영구 아님) · 시험 `n7_hold_on_windows_triggers_archive_fill_then_recheck_or_reasoned_hold` · U2-N7FILL ⓒ **받기 공용 1벌** = U5 `install_link.rs` 에 `fetch_archive_body`(보관소 본문·서명 → U 서명·서식·seq·기판 행 · seq 0 거부) + `place_installer_files`(멱등 = 재검증 + 본문 바이트 같음 · 소유자 전용 임시 폴더 → 내구 쓰기 → 재검증 → rename + fsync) 를 뽑고 `preserve_installer`(설치 링크 · 방금 깐 설치기 파일)와 `realops::fill_installer_dir`(러너 · 설치기를 본문 행 url 에서 받음)가 둘 다 이 두 함수를 쓴다 · 접점 4파일·`verify_installer_dir` 불변.
  | 세부 | U5 2판까지 `preserve_installer` | U2F 2판 `fill_installer_dir` | 3판 공용 |
  |---|---|---|---|
  | seq 0 | 거부(rc 3 seq_zero) | 없음 | 거부(공용 `fetch_archive_body`) |
  | installers 부모 | `ensure_private_dir` | 없음 | `ensure_private_dir` |
  | 멱등 | 재검증 + 본문 바이트 같음 | 재검증만 | 러너 = 재검증 통과면 받기 0 · 놓기 = 재검증 + 본문 바이트 같음 |
  | 임시 자리 | `.<seq>.tmp` | `.<seq>.fill.tmp` | `.<seq>.tmp` |
  | 설치기 출처 | 방금 깐 파일(sha256 = 행) | 행 url 받기(크기·sha256 = 행) | 그대로(호출자 몫) |
  | A2 서명 | 인자 파일 또는 행 a2_sig_url | 행 a2_sig_url | 그대로(호출자 몫) |
  | 오류 | `PreserveErr{rc, reason}` | 문자열 | 공용 = PreserveErr · 러너 = 「reason: detail」 문자열 |
  · 2판 S2 받기 · S8 재받기 · RB 재받기는 그대로(멱등 · N7 통과 뒤 사라진 경우의 방어).
- **남은 것(옛 줄 · ② 이전 기록)**: ② M2(N7 윈 존치 + 받기 공용 함수 한 벌 — **master 의 「U5 merge/v0.14.43 편입」 통지 뒤** rebase/merge · check.rs 접점 · U5 `preserve_installer` ↔ `fill_installer_dir` 갈린 세부 표 · HANDOFF 의 `u5-block.ps1:309` 인용 정정 = 이름 정본은 U5 `install_link.rs`) · ③ 의 `--check` N7 윈 실제 결과(②와 묶음) · 전수 · 미러 push 1회 · 【확인요청】.
- **CTX**: 12:5x ≈56%(jsonl 라이브).
- **시험 결과(격리 래퍼 · 전수 전체를 `u2-realroots.sh` 로 감쌈 · HEAD a97a8f8b · 13:50~14:23)**: lib **1020/0**(1 ignored) · cys **593/0** · cysd **2462/2**(★`schedule::tests::stale_schedule_lock_is_broken_and_live_lock_times_out` · `schedule_writers_serialize_under_the_lock_and_no_add_is_lost` = 잠금 시한 시험 · 이 가지의 cysd 변경 0(`git diff 8ba48f9e..HEAD -- src/bin/cysd` = 0) · 단독 ×3 = 녹 2/0 ×3 = 부하성 간헐 · 정직 기록) · smoke **18/18** · mutants **46/46** · cys-app **260/0** · 윈 타입체크 오류 **0** · real-roots U2 이름공간 **0**(rc 0 · 변화 2907 = 같은 시간 다른 세션 · 「그 밖」).

## §0-7 후속 2판 델타(master#147e7d04 · 원문 = `docs/update/REVIEW-U2F-{codex,agy}-1r.md`(ignored) · 착수 10:44 · 커밋 3143237c · f8d30969 · 9f86c38d)
- **이월**: 1판(§0-6) 검수 = master 게이트 PASS · codex 1R 수렴 아니오(BLOCK 2 · MAJOR 5 · MINOR 3) · agy 1R 수렴 아니오(BLOCK 2 · MAJOR 3 · MINOR 4) · master 채택 = 전건 + ⑫(예고분 · 러너 보관소 받기).
- **설계 한 줄(②③④⑥ 한 뿌리)**: 1판의 「새 판 재구성 = 별도 수용 갈래(accept_reconstructed) + S7 행 새 판 기동(recon 표지)」 를 **폐기**하고, `Runner::enter` 가 S8~S11 저널 칸 사본을 `attempt.json journal` 에 내구 기록 → 재구성이 새 판이면 그 사본(+원점)으로 **S9(SWAPPED) 를 다시 써 정상 복구 행**(맥 정식 자리 서명·판 재대조 / 윈 S9b 페이로드 전수·build-info 재대조 → S10 → V1~V9 → S11 → DONE 단일 `ok` · 어디서든 실패 = 롤백)으로 보낸다. 상태기계 밖 경로가 사라져 검증·롤백·결과 계약이 정상 실행과 같다.
- **채택/반박 표 19행(codex 10 + agy 9)** — 반박 0 · 부분 1(agy 7 의 「미추적 로컬 파일」 · 근거 칸):
  | # | 출처·등급 | 지적(요지) | 판정 | 커밋 | 고친 곳(파일:줄) · 증명 시험 · 뮤턴트 |
  |---|---|---|---|---|---|
  | c1 | codex BLOCK | attempt txn 무검증 → stage 결합 → `remove_dir_all` 경로 탈출 | 채택 | 3143237c | `journal.rs:192`(`origin_txn` 저널 칸) · `:496`(`valid_txn` 소문자 32-hex) · `realops.rs:250`(`stage_dir` → Option · 원점 없음 = 가장 0) · `:256`(`remove_stage` = 검증 원점 + `update/stage` 바로 아래 실 폴더만) · `runner.rs:706`(attempt 형식 밖 = Corrupt) · ★`stage_is_the_journal_origin_never_the_attempt_or_recovery_token`(`../..` 주입 · 밖 링크 = 삭제 0) · `malformed_attempt_tokens_are_never_a_source` · U2-STAGETXN · U2-TXNFORM |
  | c2 | codex BLOCK | 새 판 재구성 = PID 응답만 → 수용·ok | 채택(S9 행) | 3143237c | `runner.rs:571`(`reconstruct` 새 판 = `write_reconstructed(Swapped)` → `recover_from`) · `journal.rs:477` · `runner.rs:677`(사본 상태) · ★`new_reconstruct_routes_through_s9_row_v_checks_and_single_ok`(V 실패 = 롤백) · U2-RECONROUTE · U2-JCOPY |
  | c3 | codex MAJOR | 인수 = 저널 먼저·계보 실패 무시 | 채택 | 3143237c | `runner.rs:470`(계보 먼저 · `attempt_takeover → Result` · 실패 = JournalRefused · 저널 무변경) · 재구성 계보 실패 = 멈춤 · ★`takeover_writes_lineage_before_journal_token_and_stops_on_failure` · U2-TAKEORDER |
  | c4 | codex MAJOR | 윈 S7 재진입 = recon 표지만 믿고 실행 | 채택(갈래 폐기) | 3143237c | 새 판은 S7 행으로 오지 않음(`start_old` = 언제나 옛 판) · 실행 전 = 윈 S9b(`payload_ok` 페이로드 전수 + `bundle_ident_exe` build-info) · 실행 뒤 = V1(데몬 `system.identify` build_id) · 같은 시험 윈 갈래(S9b 실패 = 롤백 · 새 cys 기동 0) |
  | c5 | codex MAJOR | 수용 실패 = Deferred 종결·attempt·stage 삭제 | 채택 | 3143237c | 수용 = 정상 S11 `commit` · 실패 = 롤백(성공 전 `attempt_end`·`release` 0) · 같은 시험 「commit」 갈래 |
  | c6 | codex MAJOR | 기록 부재 → 복구기 토큰을 원점으로 가장 | 채택 | 3143237c | c1 과 같은 곳(원점 = 저널 칸 · 없음 = None) · 같은 시험 ⓒ |
  | c7 | codex MAJOR | 메모 rels·why 무인증 · 지문 오류 합침 | 채택 | f8d30969 | `cys.rs:24765`(판·자기 sha256·모르는 칸 거부·16 KiB · 항목 = 서명 매니페스트 files 재구성) · `:24803` · `pack.rs:2893`(A/F/D/L/O · 「없음」 밖 I/O 오류 = None) · ★`pack_auto_hold_memo_rejects_forged_unreadable_and_clears_on_manual_apply` · U2-MEMOCHECK |
  | c8 | codex MINOR | post_verify 원시 JSON 기준선 | 채택 | 3143237c | `realops.rs:834`(`attempt_for` · 종결 표지·남의 계보 = V0) · ★`post_verify_baseline_only_from_live_attempt_of_this_lineage` · U2-PVATTEMPT |
  | c9 | codex MINOR | n13 = 내부 함수 직접 연결 | 채택 | f8d30969 | `cys.rs:2762`(`process_args` · 시험 빌드에서만 `CYS_TEST_ARGV`) · `:2773`(`pack_keyring` · 시험 빌드에서만 `CYS_TEST_PACK_KEY`) · ★`pack_update_txn_glue_holds_in_a_real_process`(자식에서 진짜 `main()` → dispatch → 위임 참가(부모 러너 잠금 · 인자+env) → run_pack_update → rc 1 + `pack-auto-hold:` / 수동 rc 0 · 반영) · U2-TXNGLUE |
  | c10 | codex MINOR | realroots 에 새 메모 빠짐 | 채택 | f8d30969 | `scripts/tests/u2-namespace.txt`(계약 목록 · `.pack-auto-hold.json` · `.pack-journal`) → `u2-realroots.sh:45` 가 정규식 생성(목록 없음 = rc 2) · 합성 대조(U2 4 · round/ = 그 밖) |
  | a1 | agy BLOCK | 복구기 `cand` 비어 수용 항상 실패 | 채택(실측 = 반은 아님) | 3143237c | 실측: 후보는 `candidate.json` 에서 S11 재료째 복원(`auto.rs:147` `recovery_candidate` 분리) · 빈 후보 = 파일 없을 때만 → 새 판 판정 자체 불가 · 사본 판 ≠ 후보 = 재구성 불가(`realops.rs:1117`) · ★`reconstruct_new_needs_restored_candidate_of_the_same_release` · U2-CANDSEQ · **1판 시험이 못 잡은 이유** = 후보 칸을 손으로 채우고 판정을 주입(judge_is_old)해 복원 입구·후보 묶음을 둘 다 우회 |
  | a2 | agy BLOCK | 윈 S7 recon 맹신 실행 | 채택 | 3143237c | c4 와 같음 |
  | a3 | agy MAJOR | `let _ = attempt_write` 삼킴 | 채택 | 3143237c | c3 와 같음 |
  | a4 | agy MAJOR | origin 폴백 + 옛 stage 재검증 없음 | 채택 | 3143237c | c6 + 옛 stage 재사용 = S11 보존이 임시 자리 사본을 `verify_installer_dir`(설치기 sha256 = 본문 행 · A2 서명) 재검증 |
  | a5 | agy MAJOR | journal_corrupt→ok 2결과 경쟁 | 채택 | 3143237c | 새 판 = 정상 DONE 의 `ok` 하나(같은 시험 `records == [Ok]`) · 옛 판 = `journal_corrupt` 하나 |
  | a6 | agy MINOR | post_verify `ended` 무시 | 채택 | 3143237c | c8 과 같음 |
  | a7 | agy MINOR | 지문이 미추적 로컬 파일 무시 · 수동 성공 메모 잔존 | **부분**(근거) | f8d30969 | 수동 성공 = 메모 삭제(`cys.rs:25016` · U2-MEMOCLEAR) 채택 · 「미추적 파일」 = `plan_install` 이 읽지 않는 파일은 계획에 영향 0 · 보류 원인 파일은 꾸러미 항목이라 이미 지문 안(사용자가 그 파일을 지우면 지문이 바뀜 = 시험 ⓒ·n12 ⓒ) |
  | a8 | agy MINOR | n13 main 우회 | 채택 | f8d30969 | c9 와 같음 |
  | a9 | agy MINOR | smoke `$2 == b` 공백 경로 | 채택 | f8d30969 | `u2-smoke.sh:34`(pid 뒤 명령 머리 전체 · 「경로 + 공백」 또는 끝) · 합성 대조(공백 경로·접두 같은 이름·다른 소켓) |
- **⑫ 러너 보관소 받기(예고분 · 설계 §3-7 ② · §6-1)** 9f86c38d: `realops.rs:149` `fill_installer_dir` = 재검증 통과면 그대로(받기 0) · 아니면 보관소 `cysr/releases/<seq>.json(.minisig)` → U 서명·서식·seq → 본문 이 기판 행 url(설치기 · 크기·sha256) + `a2_sig_url` → `installers/.<seq>.fill.tmp` 에 접점 4파일(`release.json`·`release.json.minisig`·`setup.exe`·`setup.exe.sig` — ★3판 정정: 이름의 정본 = U5 `src/update/install_link.rs`(`realops::REL_BODY`·`REL_SIG`·`SETUP`·`SETUP_SIG` 공용 상수) · 2판의 `u5-block.ps1:309` 인용은 U5 스냅샷에서 다른 줄(J-UPD-03 문구)이었다) → `verify_installer_dir_with` → rename + fsync · `realops.rs:1205` 배선 = 윈 **S2**(데몬 정지 전) 받기 + S8 재검증 실패 시 1회 재받기 · 실패 = `update.no_rollback_asset`(일시 = 6·12·24·48h 백오프) + 「설치판 롤백 자산 받기(보관소): <사유>」 · `check.rs:565` N7(윈) = 설치판 자산 유무로 보류하지 않음(공간 식만) · ★`fill_installer_dir_from_archive_verifies_and_places_contract_files` · ★`win_s8_fills_missing_rollback_assets_from_archive_or_holds_with_reason`(실 RealOps · file 보관소) · U2-FILL. **방식 차이 1**: 브리프 「S8 에서 받기」 → 받기 = S2(실패해도 데몬 무중단) + S8 재검증·재받기.
- **계약 변화**: 저널 `origin_txn`(빈 값이면 직렬화 생략 = 옛 저널·smoke 손 저널 crc 무변화) · `attempt.json` `recon` 칸 폐기 → `journal`(저널 사본) · 시도 토큰 = 소문자 32-hex 만 · 새 판 재구성 결과 = 정상 DONE `ok` 하나(1판의 journal_corrupt→ok 폐기) · 메모 서식 v1(자기 sha256) · `u2-namespace.txt` · 시험 빌드 전용 env `CYS_TEST_ARGV`·`CYS_TEST_PACK_KEY`(출시·디버그 실행 바이너리 = `cfg!(test)` 거짓 = 무시) · N7(윈) 완화(받기 = 러너).
- **잔여(정직)**: ⑫ 실기(윈 실 네트워크 · 실 보관소 게시)는 267 relay 몫 — 검체 = `dir %LOCALAPPDATA%\cys-update\installers\<설치판 seq>` 을 지운 뒤 `cys self-update --run --json` → 4파일 재생성 + `bootstrap.log` 무관 · 실패 시 `state.json` 의 `last_result`(deferred · `update.no_rollback_asset`) detail 에 「보관소」 사유. 맥 = 롤백 자산이 정식 자리 옛 번들이라 받기 없음(종전).
- **시험 결과(격리 래퍼 · 전수 전체를 `u2-realroots.sh`(새 이름공간 목록)로 감쌈 · 11:06~11:38)**: lib **1007/0**(1 ignored) · cys **592/0** · cysd **2464/0**(7 ignored) · smoke **18/18** · mutants **36/36**(1판 29 − 폐기 2(RECONEXE·RECONACCEPT) + 2판 9: STAGETXN(새 시험)·RECONROUTE·JCOPY·TAKEORDER·TXNFORM·CANDSEQ·PVATTEMPT·FILL·MEMOCHECK·MEMOCLEAR) · cys-app **260/0** · real-roots 154,776→154,778 항목 · 변화 48 · **U2 이름공간 0**(rc 0) · 윈 타입체크 = 전수 때 **오류 1**(n13 시험의 `std::os::unix` · 맥 전용 시험에 `#[cfg(unix)]` 누락) → 고친 뒤 재실행 **오류 0**(11:38) — 그 고침은 시험 함수 속성 1줄(맥 전수 결과 무영향).

## §0-6 후속 델타(TICKET=cysr-118-u2-followup · 정본 브리프 = ~/axdev/master/briefs/2026-10-07-cysr-118-u2-followup.md · master#dce9c476 · 가지 `u2/followup-118` off `8ba48f9e` · 착수 07:59)
- **이월**: U2 = 병합 완료(merge/v0.14.43 `e664ec08` → U4 `8bcd39aa` → `8ba48f9e`) · Fable 5R = BLOCK 0 · MAJOR 0 · MINOR 8(n10~n17 · 「병합 뒤 별도 티켓」) + 5판 정직 고지 2 · 원문 = `docs/update/REVIEW-U2-fable-5r.md`(이제 .gitignore). 기준선 = `cargo test --lib update::` **223/0**(수정 0 · 08:00).
- **항목표(8 + 정직 고지 2 + 범위 밖 1) — 판정 = 전부 「발행 전 해소」**(발행 뒤로 미룬 것 0):
  | # | 지적(요지) | 판정 | 커밋 · 소요 | 고친 곳(파일:줄) | 증명 시험 · 뮤턴트(수리 끄면 적) |
  |---|---|---|---|---|---|
  | n10 | 재구성 저널 토큰이 attempt 계보 밖 → 재기동 실패 뒤 한 슬롯 더 손상 = Mismatch(사람 필요) | 해소 | a953c9f7 · 07:59→08:02 | `runner.rs:578`(`attempt_takeover(시도 txn → 재구성 토큰)`) | `realops::tests::reconstruct_lineage_survives_restart_failure_then_one_more_torn_slot`(실 RealOps · S7 유지 → journal.json 손상 = Degraded(남은 슬롯 = 재구성 Locked) → 다음 복구기 = 같은 시도로 재구성·재기동·종결) · U2-LINEAGE |
  | n16 | `attempt_end` 삭제 먼저 → 삭제 실패·fsync 전 죽음에 종결된 기록이 원천으로 남음 | 해소(잔여 창 = 표지 쓰기 + 삭제 둘 다 실패 · 1줄) | a953c9f7 | `runner.rs:755`(`attempt_end_by` = `ended` 내구 쓰기 → 삭제 + 폴더 fsync) | `runner::tests::attempt_end_marks_ended_before_removing`(삭제가 일어나는 순간 디스크 = ended 단언 · 삭제 실패 주입 = 표지 남음 = Missing) · U2-ENDFIRST |
  | n11 · 정직 고지 2 | 윈: 새 판 재구성 + 재기동 실패 → 다음 복구기 S7 행이 러너 사본(옛 cys)으로 기동 = 정식 새 판 + 옛 데몬 혼합 | 해소(맥 = 원래 정식 자리 · 무변화) | b46ebb7a · 08:02→08:09 | `realops.rs:1044`(판정 → `attempt.json recon`) · `realops.rs:878`(`start_old` = 윈 + 새 판 재구성 계보면 `install_dir/cys.exe`) · `runner.rs:728`(`attempt_note_recon`) | `realops::tests::win_s7_row_after_new_reconstruct_restart_failure_starts_canonical_new_cys`(모의 윈 · 정식 자리 cys.exe 의 기록 머리 = NEW) · U2-RECONEXE · 실기 = 아래 윈 검체 |
  | n17 | 재구성이 새 판으로 종결하면 S11 생략(수용 기록·윈 `installers/<seq>/` 0 → 다음 갱신 N7 보류) | 해소(러너 쪽 S11 몫 · 첫 설치 bootstrap = U5 몫 · §5 ⓔ) | b46ebb7a | `runner.rs:111`(`Ops::accept_reconstructed`) · `runner.rs:592`·`:361`(재구성 종결 · S7 행 종결 둘 다 · 종결 전) · `runner.rs:605`(`record_accepted` = ok · release_seq = 새 판) · `realops.rs:204`(`accept_release` = 보존·재검증 + 수용 기록 · commit 과 공용) · `realops.rs:1023` | `realops::tests::new_reconstruct_terminal_preserves_release_and_records_acceptance`(서명 시험 본문 · 재기동 성공 / 실패 → S7 행 두 갈래 · `installers/9` 재검증 · 수용 기록 설치 seq 9 · last_result ok) · U2-RECONACCEPT |
  | ★범위 밖 | (n17 실 경로에서 발견) `stage_dir`·S11 스냅샷 보호 이름이 **지금 저널 txn** — 복구기 인수 뒤엔 새 토큰이라 윈 S9~S11 중단 복구의 S11 보존이 없는 `stage/<새 토큰>/setup.exe` 를 찾아 실패 → **롤백**(전진 완료 불가) · stage 삭제 빗나감 | 해소 | b46ebb7a | `realops.rs:197`(`origin_txn` = 이번 시도 S1 txn · 기록 없으면 저널 txn) | `realops::tests::stage_after_takeover_is_this_attempts_s1_stage`(윈 setup.exe + A2 → `installers/9` 재검증) · U2-STAGETXN(= 종전 = 「No such file … stage/<새 토큰>/setup.exe」 적색 실측) |
  | n12 | `pack-auto-hold` 가 꾸러미 내려받기·전개 **뒤** → 보류 중 6h 틱마다 ≈49 MiB 재다운로드(치명 4군 「폭주」) | 해소 | efe53bb1 · 08:09→08:16 | `cys.rs:24909`(보류 때 메모 `.pack-auto-hold.json` · 허용 = 삭제) · `cys.rs:24752`(`pack_hold_memo_hit`) · `cys.rs:24762`(`pack_remote_source` = 매니페스트만 받은 뒤 메모 대조 → 꾸러미 받기 전 같은 보류) · `pack.rs:2891`(`plan_disk_fingerprint` = plan_install 의 디스크 입력 전부) | cys `pack_auto_hold_memo_skips_download_until_inputs_change`(원격 꾸러미를 치운 채 같은 보류 · 내려받기 0 · 판정 입력 밖 round/ 변화 = 적중 · 사용자 되돌림 = 다시 판정·허용·메모 삭제 · 수동 = 메모 무관) · U2-HOLDMEMO |
  | n13 | `pack-update --txn` 글루가 실 프로세스에서 유효 서명으로 지나는 시험 0 | 해소(잔여 1 · 아래) | efe53bb1 | `cys.rs:24727`(글루 무변경 · 스위치만) | cys `pack_update_txn_glue_holds_in_a_real_process`(시험 바이너리를 자식으로 다시 띄움 → 실 argv 분리 `rotate_ext_strip`(OnceLock 1회) → clap → 비-gated `pack_update_from_dir` → 시험 키 유효 서명 꾸러미 · `--txn` = 보류·반영 0 / 수동 = 반영) · U2-TXNGLUE |
  | n14 | smoke `own_daemons` 판별식 양성 대조 없음 → reap·「잔존 0」 공허 통과 가능 | 해소 | 77feabc7 · 08:16→08:29 | `u2-smoke.sh:160`(⑥ 데몬 생존 중 소켓이 밝힌 pid ∈ own_daemons) | smoke 18/18 · 손 뮤턴트(판별식 깨뜨림) = 양성 대조 BAD · **같은 실행의 「잔존 0」 은 거짓 통과 + 실제 고아 1**(지적이 실물로 재현 → 그 pid 만 정리 · 뒤 0) |
  | n15 · 정직 고지 1 | `u2-realroots.sh` 가 `U2_REALROOTS_OUT` 을 안 만듦 → 목록 0 · rc 1 · 판정 무효 | 해소 | 77feabc7 | `u2-realroots.sh:14`(`mkdir -p`) · 목록 부재 = 「판정 불가」 rc 2 | 없는 폴더를 지정해 재실행(아래 §0-6 결과) |
- **§7-4 잔여 대조**: codex 4R 8행 + Fable 4R 4행 + master 1행 = 전부 「채택 · 커밋」(보류·발행 뒤·미해소 표기 0 · 방식 차이 5 = §2-19~23 은 각 근거 있음) → **잔여 0**.
- **계약 변화(다른 티켓이 알아야 할 것)**:
  - `attempt.json` `recon`(`old`·`new` · 재구성 판정) — S7 행 기동 바이너리(윈)·종결 S11 몫의 근거.
  - 새 판 재구성 종결 = 결과 기록 `journal_corrupt`(재구성 성공) 다음 `ok`(release_seq = 새 판) — 앱 「갱신됨」 안내가 이 경우에도 뜬다.
  - stage·S11 스냅샷 보호 이름 = 이번 시도 S1 txn(복구기 인수 뒤에도).
  - 팩 상태 폴더(`~/.cys`) `.pack-auto-hold.json`(자동 보류 메모 · 수동 경로 무관 · 허용 판정 때 삭제) · 메모 적중 stderr = `pack-auto-hold: <사유> (보류 메모 · 꾸러미 내려받기 0)`.
  - `u2-realroots.sh` rc 2 = 판정 불가(종전 rc 1 과 섞이던 것) · `u2-mutants.sh` 줄 머리 `bin:` = `--bin cys` 시험.
- **잔여(정직)**:
  - n13 = 「실 cys 바이너리 + 실 서명」 은 불가 — 팩 키링(`packsig::embedded_keyring`)에 시험 키 덮어쓰기 경로가 없다(만들면 서명 계약 변화 → 안 만듦). 남은 차이 = `main` 의 `rotate_ext_strip` 호출 1줄(자식 시험이 같은 함수를 부름).
  - n16 = 표지 쓰기와 삭제가 **둘 다** 실패하는 창(같은 폴더 권한 사고 · 1줄) — 다음 S1 이 덮는다.
  - n17 = 윈 **첫 설치** 의 `installers\<seq>\` 는 U5(298 · 설치 링크) 몫 — 러너 쪽(S11 · 새 판 재구성)은 여기서 닫음.
- **윈 실기 검체(267 relay · n11 · 정직 고지 2 — W 요청문에 「재구성 뒤 재기동 실패」 항목으로)**: 전제 = 디버그 빌드 · 격리 `CYS_UPDATE_STATE_DIR`(아래 `%U%`) · 정식 자리 `%LOCALAPPDATA%\cys\cys.exe` 가 새 판인 상태에서 저널 두 슬롯 손상 + 재기동 실패 주입(`%U%\restart` 실패 = 새 판 cys.exe 를 잠시 다른 이름으로).
  1. 읽기: `type %U%\attempt.json` → `"recon": "new"` 줄이 있다.
  2. 읽기: `cys self-update --recover --json` 첫 회 → `recovered` 에 `SeatsBlocked` · `type %U%\journal.json` 의 `"state": "S7_STOPPED"`.
  3. 새 판 cys.exe 이름 복구 뒤 두 번째 `cys self-update --recover --json` → `Deferred`.
  4. 판정: `%LOCALAPPDATA%\cys\cys.exe identify` 의 데몬 판(버전·빌드) = 새 판 · 관측 기록 = `powershell -c "Get-CimInstance Win32_Process -Filter \"Name='cysd.exe'\" | Select ProcessId,ExecutablePath,CommandLine"`(러너 사본 `%LOCALAPPDATA%\cys-update\runner\cys.exe` 는 옆에 cysd.exe 가 없어 그 rotate 가 어느 cysd 를 띄우는지 **맥에서 미확인** — 데몬 판이 옛 판이면 5판 결함 재현 · 경로 줄은 판정 아닌 기록).
  5. 판정: `dir %U%\installers\<새 판 seq>` 에 `release.json`·서명·`setup.exe`·A2 서명 4개 · `self-update --check --json` 이 N7 보류 아님(n17).
- **시험 결과(격리 래퍼 · 전수 전체를 `u2-realroots.sh` 로 감쌈 = 5판 정직 고지 1 의 「다음 판 전수 한 번」 · 08:31~08:56)**: lib **1002/0**(1 ignored) · cys **591/0** · cysd **2464/0**(7 ignored) · smoke **18/18**(n14 양성 대조 포함) · mutants **29/29**(5판 22 + U2-LINEAGE·ENDFIRST·RECONEXE·RECONACCEPT·STAGETXN·HOLDMEMO·TXNGLUE) · cys-app **260/0**(기반 8ba48f9e 의 수 · 5판 296 은 옛 기반) · 윈 타입체크 오류 **0** · real-roots = 출력 폴더 미리 없음 → 목록 생성 · 155,951→155,954 항목 · 변화 47 · **U2 이름공간 0**(rc 0) · 앞선 묶음 재실행(update:: 228 · pack:: 138 · cys pack_ 42 · smoke 18) real-roots 도 U2 0.

## §0-5 5판 델타(마지막 수리 판 · 정본 브리프 = ~/axdev/master/briefs/2026-10-07-cysr-118-u2-5r.md · 순환 재개 줄 master#076fe54a · 추가 1줄 master#a589549f · 착수 05:12)
- **이월**: 4판 검수 = codex 4R(BLOCK 1 N3″ · MAJOR 3 M4/M6-원격·M8-pro·M5 · MINOR 4) · Fable 4R(BLOCK 0 · MAJOR 1 M9 · MINOR 3 n7~n9) · 원문 = `docs/update/REVIEW-U2-{codex,fable}-4r.md`(info/exclude · 커밋 불가).
- **끝난 것(커밋 · 431d5d66 위)**:
  - **N3″ · M5 · M8-pro · n8 · RecoverPack 결과** 599561ed = `current_attempt` → `AttemptView`(Ok·부재·손상·txn 불일치) — Ok 아니면 **재구성 0**(손상 저널 그대로 = 부팅 가드 유지 · seats_blocked · 「사람 필요」 1줄 · fail-closed) · 새 판인데 스냅샷 기록 없음 = Err · `attempt_end` = 삭제 + 폴더 fsync(실패 = `ended` 표지 원자 쓰기) · **M5** = 트리 단계 뒤 `write_reconstructed_pending`(손상 슬롯 보존 → Locked → **비종결 S7** · 호출자 잠금 토큰 그대로) → `daemon_alive`(본부 `system.identify` 실측)가 거짓이면 판정된 판으로 재기동 + 응답 폴링 → **그 뒤에만** Deferred 종결 · 재기동 실패 = S7 유지(부팅 가드) + seats_blocked · 다음 복구기 = S7 행(정식 자리 바이너리 기동 뒤 보류) · **M8-pro** = 팩 저널 **명시 커밋 기록**(`.pack-journal/commit.json` · 인덱스 `explicit_commit` · 있음 = 전진 완료 · 없음 = 롤백 · 옛 인덱스 = 종전 판정) + U2 판정 = (`.pack-version`, pro_revision) 튜플 · **n8** = 저널 없음·종결일 때만 `attempt_begin` · **codex MINOR 8** = RecoverPack 결과 기록(전진 = pack_ok · 되돌림 = deferred · 실패 = rollback_failed · to = 팩 판).
  - **M9** d4428aa3 = `UserTree.pristine`(디스크 해시 == 그 팩 설치 매니페스트 해시 = 사용자 미수정 · B0 에 기록 · 요약 해시 제외) · V5 = 수정본은 바이트 동일 · 미수정본은 바이트 동일 또는 갱신 뒤 새 매니페스트와 일치 · ★**실 경로에서 드러난 두 번째 결함**: 팩 안 `.pristine/**`(벤더 3-way 병합 기준 사본 · init-pack 이 매 신판으로 갱신)이 지침 이름이라 사용자 트리로 수집 → 지침이 바뀐 모든 릴리스에서 **수정 여부와 무관하게** V5 「.pristine/… 바뀜」 → 사용자 트리·`is_user_path` 에서 제외 · N3′ 새 판 재구성 = 기준선 pristine ∩ 지금 pristine 은 되돌리지 않음(`refreshed_user_files`).
  - **M4/M6-원격 · n9** 56eb36b9 = `pack_update_from_dir_gated(auto_plan)` — 위임 토큰이면 검증·전개된 **원격 꾸러미**로 `plan_install` → `pack_plan_auto_allowed` · 거부 = `pack-auto-hold: …`(dry-run·적용 공통 · 반영 0) · 러너 `pack_available`/`pack_apply` 가 그 줄을 보류 사유로 · 팩 단독 경로의 내장 팩 `pack-plan --auto` 호출 삭제 · smoke ⑦ 주석(n9).
  - **MINOR · 스모크** 5f186a02 = 팩 공간 사실(전개 × 2 + 사용자 사본 + 예약 2 GiB · `pack_space_verdict`) · 사본 정리 실패 1줄 + 다음 `pack_prepare` 재삭제(`pack_backup_sweep`) · smoke ⑥ 좌석 셸 env 단언(N4) · ★master#a589549f = smoke 가 실행마다 debug cysd 1개를 고아로 남김(4판 실행분 **7** 실측) → trap EXIT 로 **이 실행이 띄운 cysd 만**(시작 env 의 격리 소켓 + 이 작업트리 cysd 경로 · pkill 금지) 종료 + `/tmp/u2s.*` 삭제 + 「잔존 cysd 0」 단언 · 남아 있던 7개는 같은 판별식으로 그 pid 만 종료(뒤 실측 0).
- **종단 경로 시험(실 경로 · 브리프 §4)**:
  | 지적 | 시험 | 지나는 실 경로 |
  |---|---|---|
  | N3″ ×3 | `realops::tests::reconstruct_fails_closed_when_this_attempt_is_missing_corrupt_or_foreign`(뮤턴트 U2-ATTEMPTOPEN = 4판 fail-open 재현 적색) | 실 `Runner::run`(S8 실 스냅샷) → S9 kill → 기록 부재 / 손상 / 남은 슬롯 txn 불일치(Degraded) → **`Runner::recover`**(실 RealOps) → SeatsBlocked · 부팅 가드 `journal_*` 유지 · 실행층 호출 0 · 사용자 훼손 그대로 · state.json seats_blocked |
  | M5 ×2(+1) | `realops::tests::reconstruct_restarts_by_daemon_liveness_and_keeps_guard_until_restarted`(뮤턴트 U2-RESTART) | 트리 일치 + S7 에서 내린 데몬 → 정지 0 · 재기동 1 · 종결 / 재기동 실패 → SeatsBlocked · 저널 = 비종결 S7 · 부팅 가드 `recover_pending` → 다음 복구기 S7 행 = 기동·보류 / 데몬 살아 있음 → 호출 0 · 종결(데몬 = 가짜 `cys rotate` 가 만들고 지우는 표지 · RPC 가 그것을 봄) |
  | 원격 계획 | cys `pack_update_auto_gate_holds_remote_plan_outside_auto_policy` | 실 서명 원격 꾸러미 → 실 서명·digest 검증·전개 → 원격 `plan_install` → 사용자 수정 지침 + 원격 변경(`.new` 병치) = `pack-auto-hold:` · 반영 0 / 같은 꾸러미 수동 = 반영(대조군) / 미수정 = 허용·반영 |
  | pro revision 행렬 | `pack::tests::pro_revision_advance_kill_matrix_recovers_by_commit_record`(5지점) · `realops::tests::pack_recovery_pro_revision_advance_uses_commit_record_and_tuple`(뮤턴트 U2-PACKPRO 2 = 혼합 팩 재현) | 실 `apply_pack_transactional`(1.0.0/pro.1 → 1.0.0/pro.2 · `.pack-version` 전후 같음) 이 실 `.pack-journal` 을 남기고 journal·install·state(커밋 전) / commit·version(커밋 뒤)에서 죽음 → 실 `recover_pack_journal` = 롤백 / 전진 · U2 종단 = 실 `Runner::run_pack` → PACK_APPLY 뒤 실 트랜잭션 사망 → `Runner::recover` → 실 `recover_pack_at`(튜플) → 되돌림 + 사용자 트리 복원 · 결과 deferred / 전진 · 새 지침 유지 · 결과 pack_ok(to = 팩 판) |
  | V5 ×3 | `verify::tests::v5_allows_vendor_refresh_of_unmodified_directive_but_guards_user_edits`(뮤턴트 U2-V5PRISTINE) · `realops::tests::refreshed_user_files_is_baseline_pristine_still_matching_new_manifest` | 실 `pack::install_into`(init-pack 과 같은 함수 · RefreshUser D1)로 지침이 바뀐 릴리스: 미수정 교체 → 통과 · 수정본 보존(.new) → 통과 · 수정본 훼손 → V5 · 미수정본 변조 → V5 |
  | N4 좌석 | smoke ⑥ 셋째 줄 | 실 `rotate --txn` 이 띄운 데몬 → `new-surface` 좌석 셸 → `env` 에 `CYS_UPDATE_TXN*` 0(SEEN_SEAT = `CYS_SURFACE_ID` 판독 대조) |
- **계약 변화(다른 티켓이 알아야 할 것)**:
  - 팩 저널 `.pack-journal/index.json` 에 `explicit_commit: true` · 커밋 지점 = `.pack-journal/commit.json`(`{target_version, pro_revision}`) — **커밋 판정은 판 문자열이 아니라 이 기록**(옛 인덱스 = 종전). 팩 저널을 읽는 다른 코드는 이 규칙을 따를 것.
  - `pack-update`(위임 토큰 = 자동 경로)가 원격 계획 자동 허용 밖이면 `error: pack-auto-hold: <사유>`(rc 1) — 수동 경로 무변화.
  - `attempt.json` 에 `ended`(종결 표지 · 있으면 원천 아님). 재구성 저널 = `Locked → STOPPED`(비종결 · `write_reconstructed_pending` 전용 전이) → 재기동 확인 뒤 `DEFERRED`.
  - B0 `user.pristine`(경로 집합) · 사용자 트리에서 `.pristine/**` 제외.
- **남은 것**: 【확인요청】 · origin u2 push·병합 = master.

## §0-4 4판 델타(정본 브리프 = ~/axdev/master/briefs/2026-10-07-cysr-118-u2-4r.md · 순환 재개 줄 master#d02ef28b · 착수 03:01)
- **이월**: 3판 검수 = codex 3R(BLOCK 1 N3′ · MAJOR 1 M4 · MINOR 4) · Fable 3R(BLOCK 1 N4 · MAJOR 4 M5~M8 · MINOR 6 n1~n6) · 원문 = `docs/update/REVIEW-U2-{codex,fable}-3r.md`(git info/exclude · 커밋 불가). 3판 옛 sha 는 02:4x 이력 재작성으로 계보 밖 → 이 문서의 3판 sha 를 현 계보로 교체(n6 · 아래 표).
- **끝난 것(커밋 · c7df80f3 위 · 코드 끝 0ec3f0fc)**:
  - **N3′** 1404d196 = 「이번 시도」 = 저널 txn 계보에 묶은 `attempt.json`(S1 진입 때 저널보다 **먼저** 새로 씀 · S8 직후 스냅샷 자리 · 복구기 인수 = 계보 잇기 · 종결 전이 뒤 삭제 · Degraded 슬롯 txn 이 계보 밖 = 원천 0) · 정식 자리가 **새 판이어도** 사용자 트리(V5 정의)는 대조·복원(팩 본문 = 재기동 init-pack 몫) · **M5** 같은 커밋 = 종결 저널 뒤 판정된 판으로 `rotate --skip-drain` 재기동(실패 = seats_blocked) · n3(`diff_in`/`restore_in` 범위 = cys_filter) · n4(`.pack-download`·`.pack-staging`·`.pack-apply.lock` 스냅샷·대조 제외) · codex m4(`clock::unique_key` = ns+pid+순번).
  - **N4** a51a6dd2 = `txn_participate` set_var 2개 삭제 → 토큰·깊이는 참가 자식 Command 에만(`txn_child_env`) · `spawn_detached_daemon` + cys-dept cysd 스폰 5지점 + cysd 부팅 scrub 에서 `CYS_UPDATE_TXN`·`_DEPTH` 제거.
  - **nested 형제**(codex MINOR 승격) d60a88d6 = 깊이별 잠금 `txn.child.lock.<깊이>`(1..=4) · acquire 가 깊이별 잠금도 확인.
  - **M4/M6·M7·M8·n1·n2 + 잠복 결함** 23a6e57a = 러너 분기 `pack_gates`(evaluate_pack_only) · `pack-plan --auto`(rc 4 = 자동 허용 밖) · pack-update 매니페스트 먼저(`pack_precheck` → Apply 일 때만 꾸러미 · 자동 경로 D23 `pack_min_binary_gate` 실배선) · `recover_pack_at`(`.pack-version` ≠ 적용 전 판 = 전진 완료) · 팩 결과 to_version = 팩 판 · PACK_DONE 뒤 사본 정리 · ★**잠복 결함(1~3판 · 검토 2R·3R 미적발)**: S2(맥 stage)·S9b(윈)·팩 단독이 부르던 `pack-plan --json` 은 clap 이 거부(`--json` 은 pack-plan 인자가 아님 · rc 2) → **게이트가 늘 실패**(맥 = 매 시도 S2 보류 · 윈 = 매 시도 S9b 롤백 · 팩 = 매 틱 보류). smoke ⑦ 이 처음 드러냄 → `PACK_PLAN_GATE_ARGS = [pack-plan, --auto]` + 실 파서 핀 시험.
  - **N2 종단 · M3 dispatch · m1** e1505391 = §7-3 표.
- **종단 경로 시험(Sim 전용 아님 · 브리프 §4)**:
  | 지적 | 시험 | 지나는 실 경로 |
  |---|---|---|
  | N3′ | `realops::tests::corrupt_journal_recover_reconstructs_from_this_attempt_and_restarts_daemon`(옛·새 판 2갈래) · `stale_attempt_from_previous_txn_is_never_a_restore_source` | 실 `Runner::run`(S1→S8 실 스냅샷→S9 kill) → 저널 두 슬롯 손상 → **`Runner::recover`** → `current_attempt` → **`RealOps::reconstruct`**(판정만 `judge_is_old` 주입 — 맥 codesign 실물 = C13 시험) → `reconstruct_trees`(실 diff/restore) → 실 자식 `rotate --stop-only`·`rotate --skip-drain`(가짜 cys = 인자 기록) · stale = 새 시도 S3 kill → 복원 0·정지 0 · 뮤턴트 U2-ATTEMPT·U2-RESTART |
  | N4 | `scripts/tests/u2-smoke.sh` ⑥ 둘째 줄 · cys `p8_daemon_spawn_scrubs_every_seat_identity_env` 확장 | 실 `cys rotate --txn`(러너 env 상속) → 격리 데몬 자동 기동 → 그 데몬 pid 의 `ps -E` 시작 env 에 `CYS_UPDATE_TXN*` 0(SEEN_SOCKET 1 = 판독 성공 확인) · **음성 대조** = 스폰 제거만 끈 빌드 → BAD(DAEMON_ENV_TXN 1 · set_var 가 없어도 러너 env 상속으로 샌다 = 스폰 쪽 제거가 본 처방) |
  | M4/M6 | u2-smoke ⑦ · cys `pack_plan_gate_args_parse` · lib `auto::tests::pack_route_uses_pack_only_gate_subset`(뮤턴트 U2-PACKGATE) | 실 `cys self-update --pack-only`(디버그 입구) → `auto::pack_only` → 러너 잠금 → 러너 사본(=실 cys) `pack-plan --auto --txn` → `pack-update --dry-run --manifest-url file://… --txn` → 매니페스트만(꾸러미 0) → 서명 거부 = 보류·저널 0. 「반영 가능」 갈래는 내장 팩 키 서명을 만들 수 없어 lib 시험 몫(아래) |
  | M7 | cys `pack_precheck_reads_manifest_only_and_gates_before_tar_download` | 실 `fetch_remote_manifest`(file:// · curl) → 꾸러미 없는 출처에서도 판정 끝 · 같은 판 = UpToDate · 더 새 판 = Apply · min_binary 초과 = BinaryTooOld · 자동 경로 빈 min_binary = D23 거부 · replay = UpToDate |
  | M8 | `realops::tests::pack_recovery_keeps_committed_pack_and_restores_only_uncommitted`(뮤턴트 U2-PACKCOMMIT = 혼합 팩 재현) | 실 `Runner::run_pack` + 실 RealOps(pack_prepare 사본·pre-version · pack_apply 위임 자식 · `recover_pack_at`) · kill@PACK_DONE:before(커밋 뒤) → 복구 = 지침 새 판 유지 · kill@PACK_APPLY:after(미커밋 + 훼손) → 사용자 트리 복원 · 성공 = 사본 정리·to = 팩 판 |
  | N2 | `realops::tests::rb_verified_recovery_runs_real_post_verify_v2_against_hq_daemon_only` | RB_VERIFIED kill → `Runner::recover` → `start_old`(실 자식) → **실 `post_verify`**(system.identify RPC → `hq_daemon_count` → V2 · V1·V3~V9 실 관측) → RB_DONE · 본부 pid ≠ cysd → RB_FAILED(V2) · 가짜 cysd 3개(본부+부서 2) |
  | M3 | cysd `update_hold::tests::surface_create_dispatch_refuses_new_seat_under_stop_seats_marker` | 실 `handlers::dispatch` `surface.create` → `update.installed_revoked_stop_seats` · 새 좌석 0 |
- **계약 변화(다른 티켓이 알아야 할 것)**:
  - `attempt.json` = `{txn_id, lineage[], snapshot_dir?, baseline?}` — S1 생성(저널보다 먼저) · 종결 뒤 삭제(그 밖 프로세스는 읽지 말 것).
  - `cys pack-plan --auto`(clap 밖 · `--txn` 과 함께) rc **0** = 자동 허용 · **4** = 사람 몫(차단·강제 치유·3-way·.new 병치) · `--json` 은 pack-plan 인자가 아니다.
  - `cys pack-update --manifest-url` = 매니페스트·서명만 먼저 받음 → 이미 최신·replay 면 rc 0 「이미 최신 — 반영 0 (원격 매니페스트 <판> · 꾸러미 내려받기 0)」 · `--txn` 위임이면 빈 min_binary = 거부(`update.pack_min_binary_empty`).
  - `self-update --check --json` 출력에 `pack_gates`(팩 단독 부분열 결과) 가산.
  - 팩 결과(`pack_ok` · 팩 복구 실패 `rollback_failed`)의 `to_version` = 팩 판 문자열 · `release_seq` = 0(본체 판 아님 — U4 문구는 판 번호 대신 팩 판을 쓸 것).
  - 위임 깊이별 잠금 `txn.child.lock.<1..4>`(0600) · 깊이 > 4 = busy.
  - cysd 부팅 = `CYS_UPDATE_TXN`·`_DEPTH` 제거(stderr 1줄) · cys-dept cysd 스폰 `env -u` 7종.
  - `self-update --pack-only`(숨김 · **디버그 빌드 전용** · 출시 빌드 rc 2) = 시험 입구.
- **남은 것**: 【확인요청】 · origin u2 push·병합 = master.

## §0-3 3판 델타(정본 브리프 = ~/axdev/master/briefs/2026-10-07-cysr-118-u2-3r.md · 01:01 발신은 잘림 → 01:0x 재발신 master#617b774e · 착수 01:02)
- **이월**: 2R = Fable(`docs/update/REVIEW-U2-fable-2r.md` · untracked · 커밋 제외) · BLOCK 3(N1~N3) · MAJOR 4(M1~M4) · MINOR 7(m1~m7). 📌 결정 = ⓔ U3 설치기 · ⓗ 러너 트랜잭션 안 팩 적용만.
- **끝난 것(커밋 · 0dd4fb55 위)**:
  - N1 b2c59917 = 위임 중첩 재진입(`CYS_UPDATE_TXN_DEPTH` · `lock::verify_delegated_at`) · 단위 시험 + 뮤턴트 U2-NEST · ★**u2-smoke ⑥ = 실 경로**(러너 잠금 소유 python → 실 `cys rotate --skip-drain --txn` → ④ `init-pack --txn` rc 0 · 음성 대조 = 깊이 전달 제거 빌드에서 rc 24 = ROTATE_RC_PACK 재현).
  - N2 c077aaf2 = V2 = `realops::hq_daemon_count`(본부 소켓 `system.identify.daemon_pid` 1개) · 시험 = 가짜 cysd 이름 프로세스 2개 + 본부 pid(01fd8713 에서 3초 폴링으로 안정화).
  - N3 09c3d01d = `realops::reconstruct_trees`(이번 시도 attempt.json txn 스냅샷만 · `snapshot::diff` 대조 → 일치 = 무변경 · 어긋남 = 데몬 정지 뒤 팩·사용자 트리만 · 상태 폴더·app-notify.json/.lock 무접촉 · 격리 키 reconstruct-<벽시계> = m4) · 시험 `reconstruct_compares_then_restores_only_mismatched_pack`(일치 무변경 · 어긋난 팩만 · 옛 시도 아님 · 정지 실패 = 복원 0).
  - M1 b4f7f541 = `is_held` 공유 탐침 + 러너 acquire 순간 막힘 재시도 · 시험 `probe_is_shared_and_runner_rides_out_transient_probe`.
  - M2 0a607d3c = `prev_candidates` canonicalize 뒤 중복 제거 · 시험 `prev_candidates_dedupe_through_parent_symlink`.
  - M3 aac31cf0 = stop_seats = 표지만 · cysd `surface.create` 가 같은 설치판 seq 에서 새 좌석만 거부 · 부팅 가드에서 제거 · 시험 `stop_seats_marker_blocks_new_seats_only_for_revoked_installed_seq`.
  - m1·m2·m5 01fd8713(participate fail-open 축소 · build-info 실행 전 서명 핀 · realroots counsel/) · m4 = N3 커밋.
- **남은 것(후임 · 순서대로)**:
  1. ~~M4~~ = 끝(5ec9d922 · Runner::run_pack · kill 2칸). 아래는 당시 메모: 러너 S0 에서 팩 단독 판정(새 바이너리 없음 · 팩 매니페스트만 새것) → `realops::pack_txn_begin`(lib 에 있음 · 지금 호출부 = 시험뿐) → `pack-update --txn`(위임 · `RealOps::child` 가 --txn 붙임) → 성공 `pack_txn_end`(PACK_DONE) · 실패 = PACK_ROLLBACK → 복구 = `recover_pack(&j)`(사용자 트리 복원 포함 · 있음) + kill 행렬 2칸(PACK_APPLY 직전·직후). 팩 매니페스트 조회 = `cys pack-update --dry-run --json` 또는 피드의 팩 행(설계 §3-8 · `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md` 를 먼저 읽을 것).
  2. ~~m3·m6·m7~~ = 끝(m3 ce711126 · m6/m7 = §5 ⓘ · §2-14).
  3. §7-2 표 = 14행 완료.
  4. 전수: lib(기본 env) · cys/cysd/cys-app(`/private/tmp/claude-501/s118/u2/isoenv.sh` · app = `cargo test -p cys-app --bins`) · u2-smoke(13개 = ⑥ 포함) · u2-mutants(11 = U2-NEST 포함 · `U1_ISO=<isoenv.sh>`) · ★브리프는 **tsc·bun** 도 요구 — 이 트리엔 ui/node_modules·bun 없음 → lead 방식: `cp -cR ~/axdev/.wt/cys-118-u4/ui/node_modules ui/` · PATH 에 `$HOME/.bun/bin` · `(cd ui && bunx tsc -p tsconfig.check.json)` · `(cd ui && bun test)`(복사본 = 커밋 0). 전체를 `scripts/tests/u2-realroots.sh` 로 감싼다.
  5. push = `/usr/bin/git push origin HEAD:fix/u2-runner-118`(번들 git 은 https 헬퍼 없음) → 3런(windows-build·windows-health·ci-branch) success 번호 → HANDOFF §4 「3판 전수/CI」 줄 → 【확인요청】(브리프 §3 형식).
- **함정**: ① 새 시험이 부하(전수 병렬)에서 시각 의존이면 폴링으로(N2 실례). ② u2-smoke ⑥ 은 격리 데몬을 띄운다 — 끝에 `cys daemon stop` + pkill(스크립트에 있음). ③ `cargo` 는 PATH 에 없다 → `export PATH=$HOME/.cargo/bin:$PATH`.

## §0-2 2판 델타(master#4c87d585 · #23c2f094 · #3f846d60 · 2026-10-06 · 다음 사람이 **이것부터** 읽을 것)
- **범위**: 결정론 적색 3(윈 CI 2 + master 스냅샷 게이트 1) + codex 1R 18항(BLOCK 12 · MAJOR 5 · MINOR 1) + master 추가 지시 2건. 커밋 = `git log --oneline ad3d5eb5..HEAD`(17커밋 · 마지막 = 이 문서 · 코드 끝 = a36892cd).
- **결정론 적색 3 → 42cd1562**: ⓐ secret-scan WIN-PATH(`win_task` 시험 경로 → `C:\x\a b\…`) · ⓑ① `tree_sha` 시험 심링크 단언을 `#[cfg(unix)]` 안으로 · ⓑ② 윈 `u1_facts_never_pass_gates` = `gather_facts → recover_agent_ok → win_task::our_folder` 가 `state_dir()` 를 **다시** 구하던 것 → 갱신 폴더를 호출자에서 내려받음(시험 env 심기 0 · 읽기는 install_id 를 만들지 않음) · ⓒ mac swap 시험 = 원인 확정(lead 대조 3 + 내 재현 3: `TMPDIR=/var/folders/…`·`/tmp/` = FAIL · 심링크 없는 경로 = 통과) — `/tmp`·`/var` 경로 성분 심링크를 `RENAME_NOFOLLOW_ANY` 가 ELOOP 로 거부. 1판 961/0 은 격리 래퍼(isoenv.sh)의 TMPDIR 가 심링크 없는 경로였던 탓 = **기본 환경 결정론 실패**였다(정정).
- **master#3f846d60 처분 → ① 42cd1562(시험 폴더 canonicalize · Err 내용 panic 메시지) ② 8f085359(제품: `mac::real_path` = 부모 canonicalize + 마지막 성분 실 디렉터리 확인 · 링크 = `MacAppsNotWritable`「정식 경로가 링크」 · S2 에서 미리 판정 = 보류 · NOFOLLOW_ANY 유지)**. 기본 TMPDIR lib 결과 = §4 「2판 전수」 줄.
- **codex 1R 18항 = §7 표**(채택 14 · 부분 채택 4 · 반박 0). 부분 4 = C10(윈 신설치 bootstrap = 설치기 레인) · C12(완화 폐기 자동 RB) · C14(CLI→PACK_APPLY 배선 철회) · C16(부작용 내부 fault hook 일반화).
- **윈 CI T8 적색(37472105082 @ 333e8d81) → a36892cd**: 인자 없는 설치 TIMEOUT · 기반 e2515bb0·U4 가지 = 초록 → 2판 C1(CLI 배타 txn.lock) 을 원인으로 **추정**(윈 로그에 설치기 창 내용 없음 — 확정 아님) · CLI 참가 = 공유 잠금으로 개정(§2-13) · 결과 = §4 「2판 CI」.
- **부수 발견(1판 결함 · 고침)**: S2 A2 서명 검사가 `UpdateKeyring::key_ids()`(「용도:key_id」 **표시 문자열**)를 key_id 로 넘겨 **늘 실패**하던 것 → `verify_any`(caa33833). 데몬 `system.identify` 에 `build_id` 가 없어 V1 의 데몬 빌드 대조가 설치본 값으로 메워지던 것 → 가산 키(e0fcb525).
- **계약 변화(다른 티켓이 알아야 할 것 · 1판 §0 에 더해)**:
  - `rotate`·`init-pack`/`init-jarvis`·`pack-update`·`pack-plan` = 트랜잭션 참가(자동 갱신 중 토큰 없음 = rc **26**) — 토큰 없는 CLI 는 **공유** `txn.part.lock`(txn.lock·소유자 기록 무접촉) · `--txn` 을 clap 밖에서 받는다(`TXN_VERBS`) · 위임 자식엔 `--txn` 인자 + env 를 **함께**.
  - 새 잠금 파일 `<갱신 폴더>/txn.part.lock`(0600) — 러너·복구기 acquire 가 이것이 쥐어져 있으면 트랜잭션을 열지 않는다.
  - `installers/<seq>/` 보존 꼴 = `release.json`(U 서명 본문 원문) · `release.json.minisig` · (윈) `setup.exe` · `setup.exe.sig` — S11 이 만들고 **쓸 때마다 재검증**. ★윈 신설치(자동 갱신을 거치지 않은 첫 설치)에는 이 폴더가 없다 → N7 보류(fail-closed) — 설치기(U3)가 첫 설치 때 같은 꼴로 놓아야 풀린다(📌 master 결정 필요 · §5 ⓔ).
  - 수용 기록 `accepted-cysr-<channel>.json` = S11 에서도 씀(설치 seq = 새 판) — 실패 = 롤백.
  - `seats-stop.json{release_seq}` = 설치판 stop_seats 폐기 표지(그 seq 데몬 부팅 rc 75 · 새 판 자동 해제).
  - 스냅샷 매니페스트 줄 꼴 = `<sha>  <크기>  <f|l><8진 권한>  <경로>`(1판 꼴 = 거부 · 1판 백업은 실기 0 이라 이행 대상 없음).
  - `--auto --spawn` rc **4** = 복구기 등록 실패 · **5** = 러너 기동 실패.
  - `system.identify` 결과에 `build_id` 가산.
- **cysd 전수 FAIL 이름 · alert_route 대조군(master#23c2f094)** = §4 「2판 전수」 줄.

## §0 델타(1판 · 다음 사람이 먼저 읽을 것)
- **끝난 것**: 브리프 §2 1~8 의 코드 몫 전부(아래 §1 표) + 실기 문안(`docs/update/U2-FIELD-TESTS.md` = VM M1~M3 · 윈 W1~W4 요청문 · 윈 시험 설명서).
- **안 한 것(정직 · §5)**: ⓐ `installed_revoked` ② 갈래(폐기된 설치판 → 세대 백업의 옛 판으로 **자동** 롤백) — 판정·기록(③)만 · ⓑ `schedule.json` 이행 ①~⑤ 의 cysd 첫 기동 배선(U1 §3 · 설계 §8 비가역 ⑦ = 1.1.8 발행과 함께 · U2 행 밖) · ⓒ 잠금 참가자 중 `pack-update`·`pack-plan`·`init-pack` 의 잠금 배선(rotate·CLI 자동 기동·러너·복구기·데몬 RPC 만 함) · ⓓ 맥 앱 창 재열기(§3-6 ⑥ — U4 와 경계) · ⓔ 실 VM·윈 실기 0(문안만 · 브리프 지시).
- **계약 변화(다른 티켓이 알아야 할 것)**:
  - 보류 재생 커서 = `<갱신 폴더>/hold-cursor.json {delivered_hold_seq}`(U1 `--check` N3 가 읽던 이름 그대로 — 데몬이 이제 실제로 쓴다) · 재생 원장 `hold-delivery.jsonl` · 세션 `hold-session.json`.
  - ★**U4 접점(master#60227839 · 병합 때 이름 일치 필수)**: 러너가 `state.json` 에 쓰는 앱용 칸 = `last_result{result_id, kind ∈ ok|rollback_ok|rollback_failed|installed_revoked, release_seq, version?, notes_ko?(제어문자면 생략)}` · `seats_blocked{reason:"journal_unrecoverable", at}`. 앱 장부 `app-notify.json` = 러너 무접촉(시험 핀 · `notify::tests`). 보류·재구성 성공은 `last_result` 를 바꾸지 않는다. 설치판 폐기 = `result_id "installed_revoked:<설치판 seq>"`(결과당 1회). 그 밖 내부 칸(앱 비대상): `last_defer` · `failures` · `last_success` · `last_backup_bytes`.
  - 상담소 `updates.jsonl` 행 = `{"from":"<옛 판 문자열>","to":"<새 판 문자열>","result":"<kind>","at":<정수 초>}` · 7일·10줄.
  - cysd RPC 3개 `update.quiesce`·`update.seat_token`·`update.release`(인자 `txn` = 소유자 토큰) · cysd 부팅 rc **75** = 「갱신 복구 대기」.
  - `cys rotate` 의 clap 밖 인자 `--stop-only`·`--txn <txn:epoch>` · 새 rc **26** = 자동 갱신 잠금 경합(txn_busy · 재시도 0).
  - 내장 잡 `self-update-check`(6h · `base_only` · `bulk:false` · `publish:false` · `_builtin:"selfupdate"`) — **신규 id 라 `BUILTIN_JOBS_VERSION` 범프 0**(설계 문면 「3→4」 는 이미 4 인 판).

## §1 항목 × 파일 × 시험 × 소요(실측 — 소요 = 도구 `date`/커밋 시각 · 착수 20:18)
| 브리프 §2 | 설계 § | 파일(신규 ★) | 시험(맥 · 격리) | 커밋 |
|---|---|---|---|---|
| 0 상태 폴더 실측 | §3-5 | — | `du -sk` 이 맥 `~/.local/state/cys` 39항목 1,637,320 KiB → EXCLUDE 뒤 ≈0.27 GiB(transcripts.db 1.36 GiB 가 대부분) | 99456325 |
| 3 스냅샷 | §3-5 | ★`src/update/snapshot.rs` | 「전체 − 제외」·재독 검증·파일 단위 복원 표(같음·다름·보호·격리)·멱등·손상 백업 거부·심링크 0·세대 2·공간식 — 7 | 99456325 (20:18–20:27) |
| 5 S9b | §3-7 ⑥ | ★`src/update/payload.rs` | 전수 대조·구판 전용 삭제가 상태·제외 파일 무접촉·**수집기 python 파서와 제외 집합 일치**(U3 2R #18) — 4 | b21561e0 |
| 6 V1~V9 | §3-9 | ★`src/update/verify.rs` | 행별 위반(V3 같은 수 다른 좌석·V5 잡 소실·cmd·local 1바이트·V7·V9 독립 팩)·사용자 트리 수집 — 3 | b21561e0 |
| 6 상태기계·RB·복구기 | §3·§3-10·§3-11 | ★`src/update/runner.rs` · `journal.rs`(+`write_reconstructed`) | **강제 종료 행렬 78칸**(맥·윈 × 정상·롤백 × 전 상태 직전·직후 → 복구 → 구본/신본 하나·정비 해제·부팅 가드 풀림·재복구 멱등) · S9b 1회 재실행 상한 · RB_SWAPPED 2회 멱등 · 손상 저널 → 좌석 0/재구성 · PACK_* · 부팅 가드 — 10 | 8d792679 · ab35fa7b |
| 4 맥 교체 | §3-6 | ★`src/update/mac.rs` · ★`src/update/macupdate.rs`(앱 파일 바이트 사본 · `cys::`→`crate::` 2곳) | macupdate 시험 17 그대로 · DR 핀 이관 문법(이 맥 codesign 이 받아들이고 옛 `=designated` 는 문법 오류 — 실측 시험) · 항목·트리 검사 · 실물 판정 · **실 APFS RENAME_SWAP 왕복**(정식 이름 빈 순간 0 · RB 2회 멱등 · 심링크 성분 거부) — 21 | 83625555 (–20:29) |
| 2 정비 모드·보류·재생 | §3-3 | ★`src/update/quiesce.rs` · ★`src/bin/cysd/update_hold.rs` · cysd `handlers.rs`(RPC 3 · send_text/send_key 우회) · `governance.rs`(틱 재생 · 주입 표지 HoldMark) · `schedule.rs`(발화 정지) · `main.rs`(부팅 가드) | S5 재검사 9사례 · **B8 crash 행렬 6지점**(ACK 재독·정확히 한 번·최대 한 번) · 토큰(묘비 없는 죽은 소유자 거부) · 원장 찢긴 꼬리 · cysd 통합 1(토큰 없음 거부→보류→해제→재생 1회→delivering 남은 항목 재주입 0) | ab35fa7b · aaace456 · 267e5c75 |
| 2 rotate --stop-only/--txn | §3-2·§3 S7/S10 | `src/bin/cys.rs`(clap 앞 별도 파서 — j3 스택 · 잠금 참가 · 자식 토큰 env · CLI 자동 기동 거부) | `u2_rotate_ext_tests` 1 · 종단 ⑤ | ab35fa7b |
| 5 윈 교체 | §3-7 ③④⑤ | ★`src/update/win_install.rs` | 종료 코드 0/3/4/5/6/그 밖·시한 · 실패 토큰 · `/D` 마지막·따옴표 없음 — 2(맥) + **윈 타입체크 오류 0**(CREATE_SUSPENDED·FileIdInfo·최종 경로·뮤텍스) | 221f4976 |
| 실행층 | §3-1~§3-12 | ★`src/update/realops.rs` | 좌석 키(번호 무관)·doctor FAIL·`~/.cys` 범위·트리 해시 — 3 (전 단계 일괄 = VM/윈 몫) | 221f4976 |
| 7 결과 기록 | §3-12 · §3-10 | ★`src/update/notify.rs` | state.json 칸 보존 갱신·실패 분류(V5/V7 영구)·백오프·보류는 실패 아님·손상 state.json 안 덮음·updates.jsonl 7일·10줄 — 2 | 221f4976 |
| 1 러너·틱·복구기 등록 | §3-1·§3-11·N14 | ★`src/update/launch.rs` · ★`src/update/win_task.rs` · ★`src/update/auto.rs` · `cli.rs` · `check.rs`(N14·N7 사실) · cysd `schedule.rs`(내장 잡) · `Cargo.toml`(windows-sys Com·Variant) | 지터 고정·plist 왕복·**N14 등록→대조→삭제→보류→재등록**(격리) · 윈 인자 직렬화↔되파싱(공백·따옴표·역슬래시·MS 문서 예)·XML 왕복/변조 감지·SDDL 구조 대조 — 6 | 68ebc855 · aaace456 |
| 7 install_id 배선 | 2R M5 · B8 | `auto.rs`(잡 진입 원자 생성 · 손상 = rc 3) · `win_task.rs`(작업 폴더 이름) | 종단 ④ | 68ebc855 |
| 8 시험 | §7-1·§7-2 | ★`scripts/tests/u2-mutants.sh` · ★`scripts/tests/u2-smoke.sh` | 뮤테이션 **10/10 OK**(첫 실행 BAD 2 = 시험 빈틈 → 보강) · 종단 **10/10** | aaace456 · 267e5c75 · d8f57ebe (–21:04) |
| 8 문안 | §7-3 | ★`docs/update/U2-FIELD-TESTS.md` | — | (이 커밋) |

- 규모: `git diff --stat e2515bb0..HEAD` = 26 파일 · +6,438 / −20(문서 커밋 전).
- **소요(실측)**: 코드 몫 20:18 → 21:04(커밋 시각) + 전수 시험·문서 21:0x–(§4 · 이 문서 커밋 시각). 도구 `date` 가 보고한 값 그대로다 — U1 계수(1판 ≈31분 코딩 + 시험)와 비교하면 짧게 보이지만 **도구 출력만 사실**로 적는다.

## §2 설계와 다른 점(정직 · 각 1줄 사유)
1. **스냅샷 꼴**: 팩·사용자 트리도 tar(.tar.gz) 대신 상태 폴더와 같은 「파일 사본 + MANIFEST」 — 복원 규칙(§3-5 파일 단위)이 매니페스트 기반이라 풀기 단계 0 · 한 함수. 단점 = 파일 수만큼 inode(팩 ≈50 MB 규모라 무시 가능 · 실측 아님).
2. **`hold_ingested` 자리**: 큐 파일 머리 칸이 아니라 **재생 원장**(`hold-delivery.jsonl` · 주입 전 `delivering` fsync) + 커서 파일 — `queue-state.json` 은 JSON **배열**이고 옛 데몬(롤백 대상)이 배열로 읽어 머리 칸을 넣으면 롤백 판독 불능. 보장(정확히 한 번 · 최대 한 번)은 같고 B8 행렬 6지점 + 뮤테이션 2(U2-REPLAY·U2-ATMOST)로 증명.
3. **맥 S9 에서 교환 전 끊김**(정식 자리 = 옛 판): 설계 「S7 행으로(보류)」 대신 RB 경로로 종결 — 저널 전이표(U1)에 S9→DEFERRED 가 없고, RB 는 실물 판정이라 RB_SWAPPED = 무동작·복원 = 전부 Keep(부작용 0). 대가 = 결과 kind 가 `rollback`(알림 문구 「원래 판으로 돌려 두었어요」 — 사실과 어긋나지 않음).
4. **복구기 등록 시점**: 「1.1.8 첫 실행 때 데몬이 한 번」 대신 **잡 진입(`--auto --spawn`)마다 멱등 대조·등록** — cysd 기동 경로에 파일 쓰기를 더하지 않으려고. 첫 등록 = 부팅 뒤 첫 잡(≤6h · 지터와 무관) · 그 전 N14 = 보류(교체 0) = fail-closed.
5. ~~**rotate 잠금 참가**: 토큰 없는 rotate 는 잠금 파일이 **있을 때만** 잡는다~~ — ★2판 **철회**(codex C1 · 존재 검사와 잠금 사이 창). 지금 = 존재 검사 없이 원자 참가 · 잠금 파일을 만들 수조차 없을 때만 평소대로.
6. **S5 재검사**: 「drain 이 쓴 출력은 drain 기록과 대조해 제외」 대신 **drain 직후 토큰 T1 → 정착 창(기본 20초) → T2** 비교 — drain 출력은 T1 앞에 끝난다. 단점 = 정착 창만큼 느림.

**2판에서 더한 설계와 다른 점**
7. **정식 경로 실경로화**(master#3f846d60 ②): 교환 전 부모 canonicalize + 번들 자체 링크 거부(`MacAppsNotWritable` · S2 보류) — 설계 문면은 `RENAME_NOFOLLOW_ANY` 만. 단점 = `/Applications` 위쪽이 링크인 기계에서도 교환은 되되 푼 경로로 한다(같은 볼륨이라 의미 동일).
8. **prev_bundle**(C7): codex 처방 「교환 전 저널링」 대신 **교환 전에 이미 저널에 있던 값**(`stage_path` · `from_release_seq`)과 정식 경로로 후보를 정하고(old 자리 · stage 자리 · 기록) 신원 = 옛 판인 **유일한** 것을 고른다 — 저널 전이를 하나 더 두지 않으려고(S9 앞 새 전이 = U1 전이표 변경). 정식 자리 = 옛 판이면 prev 없이 즉시 끝.
9. **stop_seats 집행**(C12): 좌석 「즉시 차단」 = 지금 데몬을 내림(`rotate --stop-only`) + 같은 seq 부팅 가드 — 좌석 하나씩 닫는 데몬 RPC 를 새로 두지 않음. 단점 = 그 기계 좌석 전부가 한꺼번에 멈춘다(폐기 severity 의 뜻과 같음).
10. **PACK 저널 칸**(C14): 저널 스키마를 늘리지 않으려고 `stage_tree_sha256` = 사용자 트리 해시 · `snapshot_dir` = 사용자 트리 사본으로 **재사용**(PACK_* 상태에서만 그 뜻).
11. **좌석 키**(C9): org.status 에 재기동을 넘는 surface 고유 id 가 없어 `surface_uuid` 칸 = `role:<역할>`(UUID 인 척 0 · 주석 명시) · `session_id` 칸 = `<에이전트>|<등록 세션>`(에이전트 교체 = 다른 좌석).
13. **CLI 참가 = 공유 잠금**(C1 개정 · a36892cd): 설계 §3-2 는 참가자 모두 같은 `txn.lock` — 2판 첫 구현(854e0615)대로 CLI 가 배타 txn.lock 을 쥐자 윈 CI T8(사람 실행 설치기 = 화면 0)이 적색(앱 기동 `init-pack` 과 설치기 ⓪-a 가 겹치면 「갱신 중」 창). 지금 = 토큰 없는 CLI 는 `txn.part.lock` 공유 · 러너만 배타 txn.lock + 참가자 잠금 확인. 러너↔CLI 배타는 그대로(양방향 원자) · CLI 끼리는 서로 막지 않음(1판 전과 같음) · 설치기 ⓪-a 무영향. 단점 = 설치기와 CLI 팩 명령이 겹치는 것은 막지 않는다(기반 판과 같은 상태 — U3 설치기가 참가자 잠금을 보게 할지는 📌).
14. **S8b 재검사 범위**(Fable 2R m7): 설계 S8b 문면(3R MAJOR 2)의 N3·N4·N5 재판정·세대 토큰 무변화는 **재지 않는다** — S8b 는 데몬이 선 뒤(S7 이후)라 좌석·승인 게이트(N3~N5)를 잴 데몬이 없고, 세대 토큰은 정비 세션과 함께 데몬 쪽에 있다. 재는 것 = 피드 재확인(같은 결정) · 보류 로그 증가 · stage 트리 해시. 그 사이 위험은 S5 재검사(T1→정착→T2)와 정비 모드가 덮는다.
12. **codex 「설계 차이 6 판정」 응답**: ⑴ 파일 사본 = 링크·권한 보강(C5) ⑵ 별도 원장 = 다중 항목 선기록 수정(C4) ⑶ RB 종결 = 정식 자리 옛 판 즉시 no-op(C7) ⑸ 조건부 참가 = 철회(C1) · ⑷⑹ 수용 그대로.

**4판에서 더한 설계와 다른 점**
15. **재구성 · 새 판 판정**(N3′): 설계 §3-11 ③ 「확정한 판의 팩·사용자 트리를 대조」 중 새 판이면 **사용자 트리만**(V5 바이트 정의) 대조·복원하고 팩 본문은 재기동의 init-pack 이 새 판으로 다시 깐다 — S8 스냅샷은 옛 팩이라 새 판 팩의 대조 원천이 없다. 단점 = S10 뒤 사용자가 고친 `local/` 파일도 스냅샷과 다르면 되돌린다(격리 보존 · V5 와 같은 판정).
16. ~~**재구성 뒤 재기동 실패**(M5)~~ → ★5판 개정(codex 4R M5 · 아래 19): 처방 문면 「부팅 가드 유지」 대신 seats_blocked 기록 + 로그 1줄 — 재기동(rotate)이 띄우는 데몬 자체가 부팅 가드에 막히므로 종결 저널을 먼저 써야 한다(순서 = 대조·복원 → 종결 저널 → 재기동). 다음 앱 기동이 데몬을 띄운다.
17. ~~**팩 전용 게이트 2칸**~~ → ★5판 공간 칸 채택(아래 21)(Fable M6 ②: 공간 ≥ tar×4 · 팩 저널 잔여 0): 매니페스트에 꾸러미 크기 칸이 없어 공간 칸은 두지 않음(pack-update 가 전개 전 검증 · 실패 = PACK_ROLLBACK 복구) · 팩 저널 잔여는 pack-update 착수 때 `recover_pack_journal` 이 먼저 치유 — 부분 채택.
18. **`plan_restore`**: 보호 경로는 백업에 있어도 덮지 않는다(전엔 「백업에 없는 새 파일」에만 보호 적용) — 기존 호출자는 보호 경로를 백업에 담지 않으므로 행동 무변화 · 새 판 재구성(사용자 트리만)에 필요.

**5판에서 더한 설계와 다른 점**
19. **재구성 저널 = 비종결 S7 먼저**(M5): 전이표에 없는 `Locked → STOPPED` 를 `write_reconstructed_pending` **한 함수만** 쓴다 — 재기동 데몬이 부팅 가드를 지나려면 「잠금 소유자 토큰 == 비종결 저널 토큰」 이 필요하고(손상 저널 위에선 불가), 재기동 실패 시 가드가 남아야 하기 때문. S7 = 「교체 전·데몬 정지」 와 같은 뜻(재구성의 실물 판정이 S2~S6 을 대신). ⚠정직: 윈 + 정식 자리 = 새 판 + 재기동 실패 → 다음 복구기 S7 행의 `start_old` 는 러너 사본(옛 cys)으로 rotate 한다(맥은 정식 자리 cys) — 윈 실기 미실측(W 요청문 몫).
20. **n2 재시도 자리**: 처방 「정리 실패 = 비종결 유지」 대신 **다음 팩 갱신 시작(`pack_prepare`)이 지난 종결 트랜잭션 사본을 다시 지움** — PACK_DONE 전에 지우면 그 사이 사망 때 복구가 적용 전 튜플(`pre-version` · 같은 폴더)을 잃어 커밋된 팩의 사용자 트리를 되돌린다(혼합 팩). 단점 = 다음 팩 갱신까지 사본 1벌이 남는다.
21. **팩 공간식**: 매니페스트에 크기 칸이 없어 dry-run 이 전개한 `.pack-staging` 크기로 잰다(전개 × 2 + 사용자 사본 + 예약 2 GiB · N7 과 같은 예약). 단점 = 판정이 dry-run 뒤(꾸러미는 이미 받음 · 공간 부족 = 보류).
22. **원격 계획 보류 오류 코드**: 새 `ErrCode` 를 두지 않고 4판 내장 계획 보류와 같은 `BuildInfoMismatch`(단계 `PACK`/`PACK_APPLY` · 사유 = 「팩 자동 보류: …」) — 결과 표·U4 문구 표 변경 0. 단점 = 코드만으로는 「원격 계획 보류」 와 「판 불일치」 를 못 가른다(사유 문자열로 가름).
23. **V5 미수정본**: 처방 「새 매니페스트 해시와 일치 요구」 + **바이트 동일도 허용**(그 판이 그 지침을 안 바꾼 경우 = 매니페스트도 같은 해시라 동치 · 바이트 동일은 사용자 트리 무변화라 위반일 수 없음).

## §3 연결하지 않은 것 · 다음 티켓
- U4: 앱 알림(위 `state.json` 칸 · `seats_blocked` 고정 안내) · 앱 창 재열기 · `macupdate` 앱 쪽 집행 함수 삭제(lib 사본으로 대체).
- U3/master(비가역): 설치기 변경 0(이번 티켓 무변경 — ⓪-a 는 U3 판 그대로 소비) · 실키·피드 게시 0.
- §5 미결 ⓐ~ⓓ.

## §4 시험 결과(격리 래퍼 `/private/tmp/claude-501/s118/u2/isoenv.sh` = EVIDENCE-118 §8 꼴)
- ★2판 정정: 1판의 「실 `~/.cys`·실 LaunchAgents·실 counsel 쓰기 0 — 끝에 `ls` 로 확인」 은 **검증된 주장이 아니었다**(codex C17 · 끝 상태 한 점만 봄). 2판 = `scripts/tests/u2-realroots.sh` 로 전수 대조(아래 「2판 전수」 줄).
- **2판 전수**: `scripts/tests/u2-realroots.sh` 가 전체를 감쌈(22:35–22:57 · 1295s · 실 두 루트 + LaunchAgents 154,511 항목 전후 대조) — lib **975/0**(1 ignored · **기본 env = 기본 TMPDIR `/var/folders/…`** · 22:36–22:44 · master#3f846d60 요청분) · cys **585/0**(isoenv · 22:44–22:47 · lead 게이트의 dbg_r12 584/1 은 이 실행에선 초록 — 기록만) · cysd **2463/0**(7 ignored · isoenv · 22:47–22:54 · ★FAIL 이름 전건 = 없음 · master#23c2f094 의 `alert_route::drills::drill_edge_loop_clear_signals_are_never_held_by_the_hourly_cap` = **ok** → 「FAIL 이면 기반 e2515bb0 단독 대조」 조건 불성립이라 대조군 미실행 · census·hwmon·b6_lsof 도 초록) · u2-smoke **12/12** · u2-mutants **10/10**(U2-NOFOLLOW 포함) · cys-app **296/0**(1 ignored · `cargo test -p cys-app --bins`) · 윈 타입체크 오류 0(커밋마다) · ui tsc = 2판 ui 변경 0(`git diff --stat ad3d5eb5..HEAD -- ui` = 0) · 이 작업트리 node_modules·bun 없음 → 미실행(정직) · **real-roots 판정 = U2 이름공간 실 쓰기 0**(`~/.cys/update` 미생성 · 복구기 plist 0 · counsel/updates.jsonl 0) · 그 밖 변화 56 = `~/.local/state/cys` 14 · `~/.cys/secure-backups` 12 · `~/.cys/claude` 14 · `~/.cys/state` 9 · `~/.cys/pack/round`(이 워커 TODO) 등 — 살아 있는 데몬·다른 세션·내 TODO 쓰기로 보이나 프로세스 귀속은 못 함(판정 밖 · 목록 보존)
- **★5판 전수(5f186a02 · 05:40–06:02 · 1324s)**: lib **997/0**(1 ign · 기본 env·기본 TMPDIR) · cys **589/0**(isoenv) · cysd **2464/0**(7 ign · isoenv · FAIL 0) · u2-smoke **17 OK / BAD 0**(⑥ 좌석 셸 env · 끝 「잔존 cysd 0 · 폴더 삭제」 포함) · u2-mutants **22/22**(U2-ATTEMPTOPEN·U2-PACKPRO×2·U2-V5PRISTINE·U2-RESTART(M5) 추가) · cys-app **296/0**(1 ign) · 윈 타입체크 오류 0 · ui 변경 0(tsc·bun 미실행 = 4판 값 유효) · `test_dept_create_progress.py` 제외 유지. ⚠정직: 이 전수를 감싼 real-roots 는 출력 폴더를 미리 만들지 않아 **판정 무효**(목록 파일 없음 · rc 1) → 실 경로를 건드릴 수 있는 묶음(lib `update::` 223/0 · `pack::` 138/0 · smoke 17/17)만 다시 감싸 실행(06:03–06:09 · 376s) = **U2 이름공간 실 쓰기 0** · 그 밖 30(`~/.local/state/cys` 11 · `~/.cys/state/report_gate` 6 · `~/.cys/claude` 5 등 = 살아 있는 데몬·Claude 세션 · 팩 저널·팩 임시 경로 0). cys·cysd·cys-app 은 이번 대조 밖(4판 대조에서 U2 이름공간 0).
- **★5판 CI(미러 fix/u2-runner-118 · 2ef3a203 = 코드 끝 5f186a02 + HANDOFF)**: windows-build ✓ 37531057972 · windows-health ✓ 37531058014 · ci-branch ✓ 37531057965 = 3런 전부 success. 이 문서 커밋 = 문서만(로컬).
- **★4판 CI(미러 fix/u2-runner-118)**: ① c6fdd2bf = windows-build·windows-health 진행 중 대체 · ci-branch ✗ 37516323332(macos-rust-pack·ubuntu-pack-suite = 팩 검체 `test_trust_seed.DeptWiringStatic.test_6c` 가 cys-dept `env -u` 목록 문자열 핀 — N4 목록 확장으로 적색) → 0ec3f0fc 재핀 ② **0ec3f0fc = windows-build ✓ 37517662512 · windows-health ✓ 37517662513 · ci-branch ✓ 37517662448** = 3런 전부 success. 이 문서 커밋 = 문서만(로컬).
- **★4판 전수(e1505391 · `u2-realroots.sh` 감쌈 · 03:45–04:04 · 1189s)**: lib **990/0**(1 ign · 기본 env·기본 TMPDIR) · cys **588/0**(isoenv) · cysd **2464/0**(7 ign · isoenv · FAIL 0) · u2-smoke **15 OK / BAD 0**(⑥ N4 데몬 env · ⑦ 실 팩 단독 경로 포함) · u2-mutants **17/17**(U2-PRIVDIR·NESTSIB·ATTEMPT·PACKCOMMIT·PACKGATE·RESTART 추가) · cys-app **296/0**(1 ign) · ui tsc 오류 0 · ui `bun test` **2807 pass / 0 fail**(81 skip) · 윈 타입체크 오류 0 · real-roots = U2 이름공간(counsel/ 포함) 실 쓰기 **0** · 그 밖 54(데몬·다른 세션) · `test_dept_create_progress.py` 제외 유지.
- **★3판 전수(7630da0c = 재작성 전 · 트리 = 현 0f34f112 + 리뷰 원문 2 · `u2-realroots.sh` 감쌈 · 01:20–01:39 · 1139s)**: lib **983/0**(1 ign · 기본 env·기본 TMPDIR) · cys **585/0**(isoenv) · cysd **2463/0**(7 ign · isoenv · FAIL 0) · u2-smoke **13/13**(⑥ 실 위임 사슬 포함) · u2-mutants **11/11**(U2-NEST 포함) · cys-app **296/0**(1 ign) · ui tsc(7.0.2 · 212 파일) 오류 0 · ui `bun test` **2888 pass / 0 fail**(81 skip) · 윈 타입체크 0 · real-roots = U2 이름공간(counsel/ 포함) 실 쓰기 **0** · 그 밖 26(데몬·다른 세션 · changed.txt) · ui/node_modules = U4 트리 복사본(커밋 0).
- **★3판 CI(미러 fix/u2-runner-118)**: ① 7630da0c = windows-build ✗ 37494950300(secret-scan 19건 = 리뷰 원문 2개가 f422136a 의 `git add docs` 로 커밋됨) · ci-branch ✗ 37494950438(H-SECRET-1 같은 원인 + `test_dept_create_progress` 1건 = 목 스텁 경주 · 이 가지 Rust 미경유) · windows-health ✓ 37494950325 ② **a3f8d8b1(재작성 전 · 트리 = 현 9d053ce1 · 리뷰 원문 untrack) = windows-build ✓ 37500063755 · windows-health ✓ 37500063630 · ci-branch ✓ 37500063614** = 3런 전부 success(dept 시험도 이번엔 초록 = 경주 추정 뒷받침). 이 문서 커밋 = 문서만(로컬 · push 시 CI 재실행).
- **a36892cd 재측정(C1 공유 잠금 개정 뒤 · 23:27–23:40)**: `update::` 202/0(기본 env) · cys 585/0(isoenv) · cysd **2463/0**(7 ignored · isoenv · FAIL 0) · u2-smoke 12/12 · 윈 타입체크 오류 0. (lib 전수·mutants·cys-app 은 333e8d81 값 — a36892cd 의 변경은 `lock.rs`·`cys.rs` 참가 경로·주석뿐이고 그 경로의 시험은 위 묶음에 있다.)
- **2판 CI(미러 fix/u2-runner-118)**: ① 333e8d81 — windows-health ✓ 37472105085 · ci-branch ✓ 37472105099 · windows-build ✗ 37472105082(T8 인자 없는 설치 TIMEOUT · 위 §0-2) ② **a36892cd — windows-build ✓ 37479834798(31m · T8 포함) · windows-health ✓ 37479834600(37m) · ci-branch ✓ 37479834529(45m)** = 3런 전부 success. 1판 ci-branch 적색(37464122311)은 secret-scan·mac swap 두 원인 그대로였다(둘 다 42cd1562 에서 고침). 이 문서 커밋 = 문서만(push 하면 CI 3런이 다시 돈다 — 로컬 커밋으로 둠).
- `update::` 188/0(lib 부분) · cysd 전수 **2462/0**(7 ignored · 정비 모드 배선 뒤 · 20:37–20:44) · 스케줄 묶음 102/0(내장 잡 추가 뒤) · 윈 타입체크(`scripts/win-typecheck.sh`) **오류 0**(2회차 · COM 포함).
- 전수 3묶음 + cys-app 재측정 = 아래 「전수」 줄(이 문서 커밋 직전 실행 · 환경 3 = census·hwmon·b6_lsof 분리 규칙).
- **전수(수리 뒤 재측정 · 격리)**: lib **961/0**(1 ignored · 21:21–21:28) · cys **585/0**(21:28–21:30) · cysd **2462/0**(7 ignored · 21:13–21:19 · 수리분 = lib 스폰 헬퍼 교체뿐이라 cysd 행동 무변경) · cys-app **296/0**(1 ignored · 21:21) · 윈 타입체크 3회차 오류 0(21:30–21:31) · `update::` 188/0 · u2-smoke 10/10 · u2-mutants 10/10. 환경 3(census·hwmon·b6_lsof) 이번 실행에선 전부 초록.
- **첫 전수에서 난 적색 4(전부 고침 · c6577bb1)**: 스폰 인구조사 3(원시 `Command::new` 동결표·콘솔 창 정책·python 직스폰 봉인) + rotate 디스패치 소스 핀 1. 교훈 = 새 lib 스폰은 `hidden_command`/`python_command`+등급 · 동결표 등재는 등급을 단 1곳만.
- cys-app 시험 환경 함정: 작업트리에 `src-tauri/binaries/`(cys·cysd 사이드카) · `src-tauri/resources/`(pack·manifest) · `src-tauri/runtime/` · `ui/dist/` 가 없으면 빌드 실패 — 전부 gitignore · U1 작업트리에서 복사(커밋 0).

## §5 미결 · 함정
- ⓐ `installed_revoked` ② 자동 롤백 미구현 — 지금은 판정 칸 + `state.json installed_revoked{stop_seats}` + 결정 `stop_seats` 로 교체 0. 구현 시 맥 = `/Applications/.cysr.app.old-<seq>` 를 자산 삼은 RB 경로 · 윈 = `installers\<seq>\` 설치기.
- ⓑ 러너 생존 R1(맥 Survivor · cysd 정지 중) = **실측 0** → VM M1.
- ⓒ 윈 COM vtable 칸 번호(taskschd.h 순서)·작업 XML 이 실제로 등록·재독되는지 = **실측 0**(타입체크만) → W1 ⑤ · W2 ⑦.
- ⓔ ★2판 · 📌 master 결정 필요: 윈 신설치 bootstrap — `installers\<설치판 seq>\`(U 서명 본문·서명·setup.exe·A2 서명)를 첫 설치 때 놓는 경로가 없다(설치기 = U3 레인). 그 전까지 윈은 첫 자동 갱신이 N7 보류(fail-closed · 교체 0). 선택지 = ① U3 설치기가 같은 꼴로 복사(권고 · 설치기 1곳) ② 러너가 피드의 `prev_release`(봉투 칸)로 받아 검증 뒤 보존(피드 의존 · 옛 판이 피드에 남아 있어야 함).
- ⓕ ★2판: 완화(advisory) 폐기의 「수용된 최신 비폐기 세대로 자동 RB」 = 미구현(ⓐ 와 같음) · stop_seats 집행만 함(C12).
- ⓖ ★2판: 매 부작용 **안** fault hook 일반화 · 실 큐·원장 재기동 통합행렬 = 미착수(C16 부분 — 실 경계 시험 5종은 §7 C16 행).
- ⓗ ~~★2판 · 📌 master 결정 필요~~ → **결정 완료**(master#e3c44aac = ① 러너 트랜잭션 안 팩 적용만 PACK_*) · 구현 = 3판 M4(5ec9d922 · `Runner::run_pack`) + 4판 게이트·실배선(23a6e57a · M6 팩 부분열 게이트 · M7 매니페스트 먼저 · M8 커밋 표지 복구). CLI 팩 명령(init-pack·pack-update)은 전역 저널 무접촉 그대로(팩 저널 `.pack-journal` 이 CLI 도중 죽음을 맡음).
- ⓘ ★3판(Fable 2R m6): 설계 §3-11 재구성 ①(윈 = 설치판 설치기 재실행 → 재대조) ②(맥 = `.cysr.app.old-*` 중 옛 판 일치본을 정식으로 승격) 미구현 — 지금은 정식 자리가 어느 판과도 안 맞으면 즉시 좌석 0(seats_blocked · fail-closed · 사람 필요). 다음 판.
- ⓙ ★4판(Fable 3R n5): m2 의 realops 경로(정식·후보 번들 `verify_signature_pin` 실패 → 판독 불가·후보 제외)를 실 번들로 지나는 시험 0 — DR 핀 불일치 번들 = canonical Unknown = RB 불가(사람 필요). 실기 M1~M3 의 시험 키 서명 번들이 DR 핀 목록과 맞는지는 실기 몫.
- **전수 제외(master#5be892c7)**: `cysjavis-pack/bin/tests/test_dept_create_progress.py` = 제외 · 사유 = 하네스 누수(기반 결함 · 시험 cysd 고아). 3판 전수(§4)는 원래 이 파일을 돌리지 않았다(CI ci-branch 적색 재현 확인용으로 따로 3회 돌리다 02:2x 중단).
- **BACKLOG(U2 범위 밖 · 수정 금지 · master#8ed6defc)**: `cysjavis-pack/bin/tests/test_dept_create_progress.py` 가 케이스마다 설치본 cysd 를 띄우고 거두지 않는다(02:18 master 실측 = 시험 cysd 74개 · ≈4개/분 · 소켓 `$TMPDIR/gp-*`) — 팩 시험 하네스 teardown 결함 · 재현 = `python3 cysjavis-pack/bin/tests/test_dept_create_progress.py` 실행 중·뒤 `pgrep -fl 'T/gp-'`. (같은 파일의 `RestampFlow.test_restamp_failure_does_not_stop_creation` 이 CI 37494950438 에서 1회 적색 · a36892cd 에선 초록 — 목 스텁 경주로 추정 · 같은 하네스 문제일 수 있음.)
- ⓓ `pack::recover_pack_journal` 부팅 때 호출 경로는 복구기(`--recover`)에만 — cysd 부팅 자체는 부르지 않는다(부팅 가드가 PACK_* 를 막고 복구기가 종결).
- 함정: 시험 하네스가 잠금 파일을 0644 로 만들면 lock 모듈이 「권한 불일치」로 fail-closed(첫 종단 실행 BAD 2의 원인 · 제품 결함 아님 · 0600 으로 고침).
- 함정: 러너 판정은 pmset/ioreg 등으로 수 초 걸린다 — 종단 시험 대기 3초는 짧다(30초 폴링으로 고침).
- N7 공간식 계수(첫 회): 이 맥 기준 백업 예상 ≈0.27 GiB(상태) + 팩 ≈49 MiB + local 48 KiB · 예약 2 GiB — 자산 크기·max_unpacked 는 릴리스 본문 값.

## §6 재현
- `git log --oneline e2515bb0..HEAD` · `isoenv.sh cargo test --lib update::` · `isoenv.sh cargo test --bin cysd update_hold` ·
  `U1_ISO=<isoenv.sh> scripts/tests/u2-mutants.sh` · `cargo build --bin cys --bin cysd && scripts/tests/u2-smoke.sh` · `scripts/win-typecheck.sh`.

## §7 codex 1R(gpt-5.6-sol · high) 채택/반박 표 — 18행(★2판 · 원문 = `docs/update/REVIEW-U2-codex-1r.md` · untracked · 줄 번호 대신 함수명으로 대조)
| # | 등급 | 지적(요지) | 판정 | 커밋 | 고친 곳(함수) · 증명 시험 |
|---|---|---|---|---|---|
| C1 | BLOCK | init-pack·pack-update·pack-plan 잠금 미참가 · rotate `exists()` 뒤 무잠금 진행 · pack-plan env 만 | 채택(방식 개정 = §2-13) | 854e0615 · **a36892cd** | `lock::participate`(존재 검사 0 · 토큰 없는 CLI = 참가자 **공유** 잠금 `txn.part.lock` → txn.lock 확인) · `acquire`(러너·복구기 = 참가자 잠금 try_lock · 쥐어져 있으면 거부) · cys `txn_participate`·`TXN_VERBS` · `RealOps::child`·rotate→init-pack 에 `--txn`+env · `participate_is_atomic_without_exists_shortcut`(공유 2 · 러너 거부 · txn.lock 무접촉) · `rotate_ext_split` 팩 동사 |
| C2 | BLOCK | 복구기 새 토큰 ↔ Runner 옛 저널 토큰 ↔ RPC 새 토큰 → 정비 세션 TTL 까지 잔존 | 채택 | 4bca3724 | `journal::takeover` · `Runner::recover` · cysd `adopt_session` · `takeover_fences_old_owner_late_write` · 78칸 행렬 복구기 = 다른 토큰·세대 승계 단언 · `recovery_generation_adopts_and_releases_dead_runner_session` |
| C3 | BLOCK | 부팅 가드 = 아무 잠금 소유로 통과 | 채택 | e3d4109b | `runner::boot_blocked`(토큰·묘비·계보 runner/recover·pid 시작 시각) · `boot_blocked_allows_only_live_lock_holder_for_non_terminal_journal` · u2-smoke ① 잠금만 = rc 75 |
| C4 | BLOCK | 연속 hold 항목 전부 `delivering` 선기록 → 고르지 않은 둘째 건 unconfirmed 소실 | 채택 | 4bca3724 | `before_inject`(선기록 0) · `HoldMark::mark_delivering`(병합 뒤 실리는 것만) · governance `deliver_head_locked` · cysd 시험 2건 보류 → 첫 건 표지 뒤 죽음 → 둘째 건 주입 |
| C5 | BLOCK | 스냅샷 심링크 조용히 누락 · 모드·링크 미기록 · `set_permissions` 실패 무시 | 채택(소유권 = 같은 사용자 쓰기라 생략 · 근거 주석) | 0e73ad52 | `snapshot::list_entries`·`Entry{kind,mode}`·`observe`·`put_entry`·`durable_copy`(권한 실패 = Err) · `links_and_modes_survive_and_journal_digest_pins_backup` · 매니페스트 파서 |
| C6 | MAJOR | 저널 `snapshot_manifest_sha256` 미대조 | 채택 | 0e73ad52 | `rb_prepare`·`rb_restore` → `snapshot::digest_eq`(상수시간) · `restore(…, expect)` · 같은 시험(사본+매니페스트 동시 변조 = 거부) |
| C7 | BLOCK | S9 기록 뒤·prev_bundle 기록 전 죽음 = RB_FAILED/복구 불가 | 채택(방식 = §2-8) | 8f085359 | `realops::rb_swap`(정식 옛 판 = 즉시 끝 · `mac::prev_candidates`+`pick_unique_old`) · `rb_finds_prev_bundle_without_journal_record_after_swap_crash`(실 APFS) |
| C8 | BLOCK | 기존 뮤텍스 미소유 진행 · 시한 초과 = 설치기 생존 중 RB | 채택 | 4b6ca28b | `win_install::imp::hold_mutex`(WaitForSingleObject 0 = 실제 소유만) · `run_installer`(시한 = Terminate + 종료 확인) · 윈 타입체크 0 · 실행 = 윈 실기 W(맥 불가) |
| C9 | BLOCK | V1~V9 상수·복사 · 좌석 키 role/agent 오기 · doctor 실패 = FAIL 0 | 채택 | e0fcb525 | `post_verify`·`baseline`·`platform_mark`·`cysd_procs`·`forbidden_jobs`·`doctor_fail`·`seats_from_org` · cysd `system.identify` build_id · `observations_fail_closed` · seats dept/agent |
| C10 | BLOCK | 윈 N7 = 존재만 · 생성 경로 없음 · 임의 설치기 현장 해시 신뢰 | **부분 채택** | caa33833 | `verify_installer_dir`(U 본문 서명·seq·설치기 sha256·A2) 를 N7·S8·RB 직전·manifest 판독마다 · 생성 = S11 `preserve_release` · `installer_dir_is_reverified_on_every_use` · ✗**신설치 bootstrap = 설치기 레인(§5 ⓔ · 📌)** |
| C11 | BLOCK | S11 이 수용 기록·서명 본문·새 설치기 미보존 · commit 실패 무시 DONE | 채택 | caa33833 | `Candidate` 증거 칸 · `commit`(preserve_release + write_accepted · 실패 = Err) · `Runner` 2곳 commit 실패 = 롤백 · `commit_failure_is_not_done_and_rolls_back` |
| C12 | BLOCK | installed_revoked/stop_seats = 기록만 | **부분 채택** | 3692bd2f | `auto::enforce_stop_seats`(표지 + 지금 데몬 내림) · `boot_guard` seats-stop · `stop_seats_marker_blocks_boot_for_revoked_installed_seq_only` · ✗**완화 폐기 자동 RB 미구현(§5 ⓕ)** |
| C13 | BLOCK | 손상 저널 재구성 = 서명 검증 전 번들 실행 · 윈 무서명 본문 · 트리 대조 없이 종결 | 채택 | aa0c0419 | `realops::reconstruct`(real_path → `mac::verify_signature_pin` → 실행 · 새 판 = cdhash 까지 · 윈 = 서명 재검증 본문 · 옛 판 = `latest_verified_snapshot` 으로 `restore_trees`) · `unsigned_bundle_is_refused_before_execution` · `latest_verified_snapshot_skips_corrupt_and_other_seq` |
| C14 | MAJOR | PACK 복구 = 팩 저널만 · 생산 코드에 PACK 상태 쓰는 경로 0 | **부분 채택** | 210ec49e · a36892cd(CLI 배선 철회) | 유지 = `recover_pack(&저널)` 가 팩 저널 복구 + `pack_user_tree_restore`(사용자 트리 해시 대조·복원 성공해야 PACK_DONE) · lib `pack_txn_begin/end` · `pack_txn_pins_user_tree_and_recovery_restores_it` · ✗**생산 코드가 PACK_* 를 쓰는 배선 = 철회(§5 ⓗ · 📌)** |
| C15 | MAJOR | `--verify-payload` 가 남은 후보 우선(B→A 롤백 뒤 거짓 진단) | 채택 | 3f84f44b | `auto::pick_payload_manifest`(설치판 seq 일치만) · `verify_payload_uses_installed_release_manifest_only` |
| C16 | MAJOR | 78칸 = enter 앞뒤·Sim · 실 부작용 창·PACK·실 큐 재기동 없음 | **부분 채택** | 102c4cdd | 실 경계 시험 5 = 백업 복사 도중 죽음(`snapshot_interrupted_mid_copy_resumes_cleanly`) · RENAME_SWAP 직후(C7) · hold 2건 실 cysd(C4) · PACK 실파일(C14) · S11 commit 실패(C11) · ✗**부작용 내부 fault hook 일반화·실 큐 재기동 행렬 미착수(§5 ⓖ)** |
| C17 | MAJOR | 「실 ~/.cys 쓰기 0」 = 끝 한 점 확인뿐 | 채택 | 333e8d81 | `scripts/tests/u2-realroots.sh`(두 실 루트 + LaunchAgents 전후 전수 메타데이터) · 결과 = §4 「2판 전수」 |
| C18 | MINOR | 복구기 등록·spawn 실패도 rc 0 | 채택 | 3f84f44b | `auto_spawn` rc 4/5 · u2-smoke ④ LaunchAgents 자리 = 파일 → rc 4·러너 0 |
- 반박 0 — BLOCK 반박 조건(시험 1개로 증명)을 채울 항목이 없었다: 18항 모두 코드에서 지적 경로를 재확인했다.

### §7-2 Fable 2R 14행(★3판 · 원문 = `docs/update/REVIEW-U2-fable-2r.md` · untracked)
| # | 등급 | 지적(요지) | 판정 | 커밋 | 고친 곳 · 증명 시험(★ = BLOCK 경로를 실제로 지남) |
|---|---|---|---|---|---|
| N1 | BLOCK | rotate(위임 · 자식 잠금 쥠) → init-pack --txn 자식 WouldBlock → S10·RB start_old 실패 | 채택 | b2c59917 | `CYS_UPDATE_TXN_DEPTH` 재진입 · `verify_delegated_at` · ★u2-smoke ⑥ 실 rotate→init-pack 왕복 rc 0(음성 대조 rc 24) · `nested_delegation_reenters_child_lock_but_siblings_still_exclude` · 뮤턴트 U2-NEST |
| N2 | BLOCK | V2 = 이 사용자 cysd 전수(부서 21개) → V2·RB_VERIFIED 결정론 실패 | 채택 | c077aaf2 · 01fd8713 | `hq_daemon_count`(본부 소켓 identify pid 1) · `v2_counts_only_the_hq_daemon_identified_by_socket`(가짜 cysd 2 + 본부 = 1 · ⚠**함수 단위 — 3판 ★ 표기는 과장**(codex 3R) · 그 시험은 /bin/sleep 사본이 즉시 SIGKILL 된 좀비 이름으로 통과하던 경주 → 4판 e1505391 에서 ad-hoc 재서명 사본) · ★4판 종단 = `rb_verified_recovery_runs_real_post_verify_v2_against_hq_daemon_only` |
| N3 | BLOCK | 재구성 = 최근 스냅샷으로 상태 폴더까지 무대조·데몬 생존 중 덮음 | 채택 → **4판 N3′ 로 재수리** | 09c3d01d · 1404d196 | `reconstruct_trees`·`snapshot::diff`·`reconstruct_protected` · `reconstruct_compares_then_restores_only_mismatched_pack` = ⚠**복원 헬퍼 직접 호출 · 3판 ★ 표기는 과장**(codex 3R — attempt.json 을 미리 고정해 stale 반례를 가렸다) · ★4판 종단 = §7-3 N3′ 행 |
| M1 | MAJOR | is_held 배타 탐침 = 거짓 rc 26·거짓 busy·설치기 창 | 채택 | b4f7f541 | 공유 탐침 + 재탐침 · 러너 acquire 순간 막힘 재시도 · `probe_is_shared_and_runner_rides_out_transient_probe` |
| M2 | MAJOR | prev 후보 문자열 중복 제거 → 부모 심링크에서 RB_FAILED | 채택 | 0a607d3c | canonicalize 뒤 중복 제거 · `prev_candidates_dedupe_through_parent_symlink` |
| M3 | MAJOR | stop_seats = --skip-drain 전체 정지(설계 ③ 초과) | 채택 | aac31cf0 | 표지만 · cysd `surface.create` 새 좌석만 거부 · 부팅·기존 좌석 유지 · `stop_seats_marker_blocks_new_seats_only_for_revoked_installed_seq` |
| M4 | MAJOR | PACK_* 생산 쓰기 경로 0(§3-8 미구현) | 채택 | 5ec9d922 | `Runner::run_pack`·RealOps `pack_available/pack_prepare/pack_apply`·`auto::pack_only`(결정 uptodate + 게이트 통과) · `pack_only_update_journals_pack_states_and_recovers_from_kills`(kill@PACK_APPLY 2칸 포함) · `pack_dry_run_parse` · 실 피드 왕복 = 실기 몫 |
| m1 | MINOR | participate Ok(None) 범위 넓음(fail-open) | 채택 | 01fd8713 | 폴더 생성 불가만 Ok(None) · 그 밖 Err |
| m2 | MINOR | build-info 실행 전 서명 검증 없음(canonical·후보) | 채택 | 01fd8713 | `verify_signature_pin` 선행 · 실패 = 판독 불가/후보 제외 |
| m3 | MINOR | 윈 시한 뒤 종료 실패 = 무기한 대기 | 채택 | ce711126 | 종료 확인 상한 10분 · 초과 = RollbackBlocked → RB_FAILED 직행 · `installer_stuck_goes_straight_to_rb_failed_without_rerunning_installer` |
| m4 | MINOR | 재구성 격리 키 고정 | 채택 | 09c3d01d | `reconstruct-<벽시계>` |
| m5 | MINOR | realroots 정규식에 상담소 신호 경로 없음 | 채택 | 01fd8713 | `counsel/` 전체 U2 이름공간 |
| m6 | MINOR | §3-11 재구성 ①②(윈 설치기 재실행 · 맥 .old-* 승격) 미구현이 HANDOFF 에 없음 | 채택(문서) | 이 문서 | §5 ⓘ 명기 · 지금 = 불일치 즉시 좌석 0(fail-closed) |
| m7 | MINOR | S8b 가 N3~N5·세대 토큰 재판정 안 함 — 생략 근거 미기록 | 채택(문서) | 이 문서 | §2-14 명기 |

### §7-3 3R 채택/반박 표 — codex 6행 + Fable 11행(★4판 · 원문 = `docs/update/REVIEW-U2-{codex,fable}-3r.md` · info/exclude)
| # | 출처·등급 | 지적(요지) | 판정 | 커밋 | 고친 곳 · 증명 시험(★ = 지적 경로를 실제로 지남) |
|---|---|---|---|---|---|
| N3′ | codex BLOCK | attempt.json 미삭제·S5b 만 갱신 → 새 시도 S1~S5 손상 때 옛 txn 스냅샷 복원 · 새 판이면 트리 대조 통째 건너뜀 | 채택 | 1404d196 | `runner::{attempt_begin, attempt_takeover, attempt_note_snapshot, attempt_set_baseline, attempt_end, current_attempt}` · `RealOps::reconstruct(attempt)` · `reconstruct_protected_new` · ★`corrupt_journal_recover_reconstructs_from_this_attempt_and_restarts_daemon` · ★`stale_attempt_from_previous_txn_is_never_a_restore_source` · 뮤턴트 U2-ATTEMPT |
| M4 | codex MAJOR | evaluate_pack_only 미사용 · pack_min_binary_gate 호출 0 · pack-plan blocked 외 rc 0 | 채택 | 23a6e57a | Fable M6·M7 행과 같음 + `pack_precheck`(auto = D23) · ★smoke ⑦ · `pack_precheck_reads_manifest_only_and_gates_before_tar_download` |
| m1 | codex MINOR | ensure_private_dir 모든 오류 → Ok(None) | 채택 | e1505391 | `lock::participate`(이미 있는 폴더 = Err) · `participate_refuses_existing_dir_with_wrong_mode_but_passes_uncreatable` · 뮤턴트 U2-PRIVDIR |
| m4 | codex MINOR | 격리 키 초 단위 충돌 | 채택 | 1404d196 | `clock::unique_key`(ns+pid+순번) · `reconstruct_compares_then_restores_only_mismatched_pack`(같은 초 두 재구성 = 격리 자리 2) |
| NEST | codex MINOR(승격) | nested=true 면 자식 잠금 0 → 깊이 1 형제 동시 통과 | 채택 | d60a88d6 | `lock::child_lock_name`·`verify_delegated_at(depth)` · acquire 깊이별 확인 · `nested_siblings_at_same_depth_exclude_each_other` · 뮤턴트 U2-NESTSIB |
| DOC | codex MINOR | §7 N2·N3 ★ 과장 · §5 ⓗ 「결정 필요」 잔존 | 채택(문서) | 이 문서 | §7-2 N2·N3 행 정정 · §5 ⓗ 결정 완료 표기 |
| N4 | Fable BLOCK | 위임 env 가 rotate 가 띄운 데몬·좌석으로 상속 → 좌석의 팩·rotate 명령 rc 26 | 채택 | a51a6dd2 | `txn_participate`(set_var 0) · `txn_child_env` · `TXN_ENV_KEYS` env_remove · cys-dept 5지점 · cysd `scrub_update_txn_env` · ★smoke ⑥ 데몬 `ps -E` 0(음성 대조 BAD) · p8 핀 확장 |
| M5 | Fable MAJOR | 재구성 복원 뒤 재기동 0 | 채택(방식 = §2-16) | 1404d196 | `Runner::reconstruct` → `Ops::restart_after_reconstruct` · ★N3′ 종단 시험(정지 1 + 재기동 1) · 뮤턴트 U2-RESTART |
| M6 | Fable MAJOR | 팩 게이트 = 본체 전체 | 채택(공간·팩 저널 칸 = 부분 · §2-17) | 23a6e57a | `check::run_check` `pack_gates` · `auto::wants_pack_only` · `pack_route_uses_pack_only_gate_subset`(N6·N7·N14 보류 + uptodate = 팩) · 뮤턴트 U2-PACKGATE |
| M7 | Fable MAJOR | 매 틱 49 MiB pack.tar.gz 선다운로드 · .pack-download 스냅샷 복사 | 채택 | 23a6e57a · 1404d196 | `fetch_remote_manifest`/`pack_precheck`/`fetch_remote_tar` · `PACK_TRANSIENT` · ★`pack_precheck_reads_manifest_only_and_gates_before_tar_download` · ★smoke ⑦(꾸러미 0) |
| M8 | Fable MAJOR | kill@PACK_APPLY:after 복구가 커밋된 팩의 사용자 트리를 되돌림(혼합 팩) | 채택 | 23a6e57a | `recover_pack_at`·`pack_committed`·`PACK_PRE_VERSION` · ★`pack_recovery_keeps_committed_pack_and_restores_only_uncommitted`(실 RealOps · 뮤턴트 U2-PACKCOMMIT 가 혼합 팩 재현) |
| n1 | Fable MINOR | pack_ok kind 계약·`to:""` | 채택 | 23a6e57a | `record` to_version = 팩 판(`parse_pack_version`) · §0-4 계약 줄 · M8 시험(ok 갈래 updates.jsonl to = 1.1.0) |
| n2 | Fable MINOR | backup/pack-<txn>/user 미정리 | 채택 | 23a6e57a | `runner::pack_backup_cleanup`(PACK_DONE 뒤 3자리) · M8 시험(사본 0) |
| n3 | Fable MINOR | 재구성 diff 가 ~/.cys 전체 해시 | 채택 | 1404d196 | `snapshot::diff_in`/`restore_in`(범위 = cys_filter · rb_restore 의 cys 뿌리도) |
| n4 | Fable MINOR | .pack-download 대조 대상 | 채택 | 1404d196 | `RealOps::cys_filter` 가 `PACK_TRANSIENT` 제외 · `reconstruct_compares_…`(.pack-download 만 다름 = 어긋남 아님) |
| n5 | Fable MINOR | m2 realops 경로(서명 핀 → 후보 제외) 실 번들 시험 0 | 채택(문서 · 정직 고지) | 이 문서 | §5 ⓙ 1줄 |
| n6 | Fable MINOR | HANDOFF sha 가 리베이스 전 것 | 채택 | 이 문서 | §0-3·§7-2 현 계보 sha 로 교체(옛 → 새: bf59a37c→b2c59917 · 40a69be7→c077aaf2 · caaab5c7→09c3d01d · d19674a0→b4f7f541 · c98fb2d9→0a607d3c · 64c8795f→aac31cf0 · 6a1da528→01fd8713 · 3c9e585f→5ec9d922 · f790a91a→ce711126 · a3f8d8b1≡9d053ce1 · 9fe2af4c≡c7df80f3 · 7630da0c≡0f34f112+리뷰 원문 2 — 트리 diff 로 확인) |
- 반박 0. 부분 1(M6 의 팩 전용 공간 칸 · §2-17). 범위 밖 발견 2: ⑴ `pack-plan --json` 잠복 결함(§0-4) ⑵ 3판 V2 시험의 /bin/sleep 사본 = 좀비 이름 경주(e1505391).

### §7-4 4R 채택/반박 표 — codex 8행 + Fable 4행 + master 1행(★5판 · 원문 = `docs/update/REVIEW-U2-{codex,fable}-4r.md` · info/exclude)
| # | 출처·등급 | 지적(요지) | 판정 | 커밋 | 고친 곳 · 증명 시험(★ = 지적 경로를 실제로 지남) |
|---|---|---|---|---|---|
| N3″ | codex BLOCK | attempt 부재·손상 → None → reconstruct Ok(false) → 손상 저널 Deferred 종결·가드 해제 · 종결 삭제 오류 무시·fsync 없음 · 완전 Corrupt = 남은 아무 attempt | 채택 | 599561ed | `runner::{current_attempt → AttemptView, Runner::reconstruct, attempt_end}` · `RealOps::reconstruct(&Attempt)` · ★`reconstruct_fails_closed_when_this_attempt_is_missing_corrupt_or_foreign` · 뮤턴트 U2-ATTEMPTOPEN · (완전 Corrupt 수용 = 수명 보증 강화: 삭제+fsync · 실패 = `ended` 표지) |
| M4/M6-원격 | codex MAJOR | pack-plan --auto 가 내장 PACK_ALL 검사 · 원격 dry-run 은 pack_plan_auto_allowed 미호출 | 채택(오류 코드 = §2-22) | 56eb36b9 | `pack_update_from_dir_gated` · `PACK_AUTO_HOLD_TAG` · `realops::pack_auto_hold` · ★`pack_update_auto_gate_holds_remote_plan_outside_auto_policy`(실 서명 원격 꾸러미 · 수동 대조군) |
| M8-pro | codex MAJOR | 커밋 판정 = .pack-version 문자열 → 같은 base pro.1→pro.2 오인(양방향) | 채택 | 599561ed | `pack::{PACK_JOURNAL_COMMIT, JournalIndex.explicit_commit, recover_pack_journal, apply_pack_transactional ③b}` · `realops::{pack_commit_tuple, pack_committed}` · ★`pro_revision_advance_kill_matrix_recovers_by_commit_record` · ★`pack_recovery_pro_revision_advance_uses_commit_record_and_tuple` · 뮤턴트 U2-PACKPRO ×2 |
| M5 | codex MAJOR | 재기동 = 복원했을 때만 · terminal 먼저 → 실패 시 가드 해제 | 채택(방식 = §2-19) | 599561ed | `journal::write_reconstructed_pending` · `Ops::daemon_alive` · `restart_after_reconstruct` 응답 폴링 · ★`reconstruct_restarts_by_daemon_liveness_and_keeps_guard_until_restarted` · 뮤턴트 U2-RESTART |
| N4 좌석 | codex MINOR | smoke 는 데몬 env 만 · 좌석 셸 env 단언 없음 | 채택 | 5f186a02 | ★smoke ⑥ 셋째 줄(좌석 1 생성 → 셸 env) |
| M6 공간 | codex MINOR | 팩 공간 게이트 없음 | 채택(방식 = §2-21) | 5f186a02 | `pack_space_verdict` · `pack_prepare` · `pack_space_verdict_and_backup_sweep` |
| n2 | codex MINOR | 정리 실패를 영구히 삼킴 | 채택(방식 = §2-20) | 5f186a02 | `pack_backup_cleanup`(1줄) · `pack_backup_sweep`(다음 시작) · 같은 시험 |
| RecoverPack | codex MINOR | 복구 종결이 결과 계약(pack_ok/rollback_failed · to) 미기록 | 채택 | 599561ed | `Recovery::RecoverPack` record · `Ops::recover_pack → Result<bool>` · `RealOps::recover_pack`(pack_to = 지금 판) · ★pro revision U2 종단(결과 deferred / pack_ok · to = 팩 판) |
| M9 | Fable MAJOR | V5 바이트 동일 ↔ S10 RefreshUser → 지침 바뀐 릴리스 = 미수정 기계 매번 V5 → 영구 격리 | 채택(+ `.pristine/**` 결함 동반 수리 · §2-23) | d4428aa3 | `verify::{UserTree.pristine, collect_user_tree, v5, is_vendor_merge_base, is_user_path}` · `realops::refreshed_user_files` · ★`v5_allows_vendor_refresh_of_unmodified_directive_but_guards_user_edits`(실 install_into) · 뮤턴트 U2-V5PRISTINE |
| n7 | Fable MINOR | M8 커밋 판정 한 축(pro_revision) | 채택(= M8-pro) | 599561ed | M8-pro 행 |
| n8 | Fable MINOR | attempt_begin 이 advance 거부보다 먼저 지난 기록을 덮음 | 채택 | 599561ed | `Runner::enter` + `fresh_txn_allowed` |
| n9 | Fable MINOR | smoke ⑦ 주석 옛 인자 | 채택 | 56eb36b9 | smoke ⑦ 주석 · (`rotate_ext_split` 시험 입력의 `--json` 은 「--auto 만 떼어냄」 의도 그대로 · 무변경) |
| ORPHAN | master#a589549f(lead 실측) | smoke 실행마다 debug cysd 고아 1 | 채택 | 5f186a02 | smoke trap EXIT `reap`(격리 소켓 env + 작업트리 cysd 경로) · 「잔존 cysd 0 · 폴더 삭제」 단언 · 기존 7개 = 같은 판별식으로 종료(뒤 0) |
- 반박 0 · 부분 0(방식 차이 5 = §2-19~23). 범위 밖 발견 1: ★`.pristine/**` 가 V5 사용자 트리에 들어가 있던 결함(1판 기원 · M9 의 실 경로 시험이 처음 드러냄 — Sim·가짜 cys 시험은 init-pack 이 파일을 갈지 않아 못 봄).
