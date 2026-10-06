# HANDOFF-U2 — 1.1.8 데몬 자동 갱신 U2(교체·롤백·러너·복구 · 데몬·CLI 쪽) · TICKET=cysr-118-u2-runner

> 브리프 = [master#71f53d34](파일 정본 `~/axdev/master/briefs/2026-10-06-cysr-118-u2-runner.md`) · 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md`(4판 · U1 편입).
> 가지 `u2/runner-118` off `e2515bb0` · 워커 = worker-2(계정2 · Opus) · 커밋 = `git log --oneline e2515bb0..HEAD`.

## §0-3 3판 델타(정본 브리프 = ~/axdev/master/briefs/2026-10-07-cysr-118-u2-3r.md · 01:01 발신은 잘림 → 01:0x 재발신 master#617b774e · 착수 01:02)
- **이월**: 2R = Fable(`docs/update/REVIEW-U2-fable-2r.md` · untracked · 커밋 제외) · BLOCK 3(N1~N3) · MAJOR 4(M1~M4) · MINOR 7(m1~m7). 📌 결정 = ⓔ U3 설치기 · ⓗ 러너 트랜잭션 안 팩 적용만.
- **끝난 것(커밋 · 0dd4fb55 위)**:
  - N1 bf59a37c = 위임 중첩 재진입(`CYS_UPDATE_TXN_DEPTH` · `lock::verify_delegated_at`) · 단위 시험 + 뮤턴트 U2-NEST · ★**u2-smoke ⑥ = 실 경로**(러너 잠금 소유 python → 실 `cys rotate --skip-drain --txn` → ④ `init-pack --txn` rc 0 · 음성 대조 = 깊이 전달 제거 빌드에서 rc 24 = ROTATE_RC_PACK 재현).
  - N2 40a69be7 = V2 = `realops::hq_daemon_count`(본부 소켓 `system.identify.daemon_pid` 1개) · 시험 = 가짜 cysd 이름 프로세스 2개 + 본부 pid(6a1da528 에서 3초 폴링으로 안정화).
  - N3 caaab5c7 = `realops::reconstruct_trees`(이번 시도 attempt.json txn 스냅샷만 · `snapshot::diff` 대조 → 일치 = 무변경 · 어긋남 = 데몬 정지 뒤 팩·사용자 트리만 · 상태 폴더·app-notify.json/.lock 무접촉 · 격리 키 reconstruct-<벽시계> = m4) · 시험 `reconstruct_compares_then_restores_only_mismatched_pack`(일치 무변경 · 어긋난 팩만 · 옛 시도 아님 · 정지 실패 = 복원 0).
  - M1 d19674a0 = `is_held` 공유 탐침 + 러너 acquire 순간 막힘 재시도 · 시험 `probe_is_shared_and_runner_rides_out_transient_probe`.
  - M2 c98fb2d9 = `prev_candidates` canonicalize 뒤 중복 제거 · 시험 `prev_candidates_dedupe_through_parent_symlink`.
  - M3 64c8795f = stop_seats = 표지만 · cysd `surface.create` 가 같은 설치판 seq 에서 새 좌석만 거부 · 부팅 가드에서 제거 · 시험 `stop_seats_marker_blocks_new_seats_only_for_revoked_installed_seq`.
  - m1·m2·m5 6a1da528(participate fail-open 축소 · build-info 실행 전 서명 핀 · realroots counsel/) · m4 = N3 커밋.
- **남은 것(후임 · 순서대로)**:
  1. **M4**(Fable 2R · 브리프 §2 「러너 트랜잭션 안 팩 적용 경로 1개를 실제로 구현」): 러너 S0 에서 팩 단독 판정(새 바이너리 없음 · 팩 매니페스트만 새것) → `realops::pack_txn_begin`(lib 에 있음 · 지금 호출부 = 시험뿐) → `pack-update --txn`(위임 · `RealOps::child` 가 --txn 붙임) → 성공 `pack_txn_end`(PACK_DONE) · 실패 = PACK_ROLLBACK → 복구 = `recover_pack(&j)`(사용자 트리 복원 포함 · 있음) + kill 행렬 2칸(PACK_APPLY 직전·직후). 팩 매니페스트 조회 = `cys pack-update --dry-run --json` 또는 피드의 팩 행(설계 §3-8 · `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md` 를 먼저 읽을 것).
  2. ~~m3·m6·m7~~ = 끝(m3 f790a91a · m6/m7 = §5 ⓘ · §2-14).
  3. §7-2 표 = 14행 있음 · M4 행만 채울 것(⟨M4⟩ 자리).
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

## §3 연결하지 않은 것 · 다음 티켓
- U4: 앱 알림(위 `state.json` 칸 · `seats_blocked` 고정 안내) · 앱 창 재열기 · `macupdate` 앱 쪽 집행 함수 삭제(lib 사본으로 대체).
- U3/master(비가역): 설치기 변경 0(이번 티켓 무변경 — ⓪-a 는 U3 판 그대로 소비) · 실키·피드 게시 0.
- §5 미결 ⓐ~ⓓ.

## §4 시험 결과(격리 래퍼 `/private/tmp/claude-501/s118/u2/isoenv.sh` = EVIDENCE-118 §8 꼴)
- ★2판 정정: 1판의 「실 `~/.cys`·실 LaunchAgents·실 counsel 쓰기 0 — 끝에 `ls` 로 확인」 은 **검증된 주장이 아니었다**(codex C17 · 끝 상태 한 점만 봄). 2판 = `scripts/tests/u2-realroots.sh` 로 전수 대조(아래 「2판 전수」 줄).
- **2판 전수**: `scripts/tests/u2-realroots.sh` 가 전체를 감쌈(22:35–22:57 · 1295s · 실 두 루트 + LaunchAgents 154,511 항목 전후 대조) — lib **975/0**(1 ignored · **기본 env = 기본 TMPDIR `/var/folders/…`** · 22:36–22:44 · master#3f846d60 요청분) · cys **585/0**(isoenv · 22:44–22:47 · lead 게이트의 dbg_r12 584/1 은 이 실행에선 초록 — 기록만) · cysd **2463/0**(7 ignored · isoenv · 22:47–22:54 · ★FAIL 이름 전건 = 없음 · master#23c2f094 의 `alert_route::drills::drill_edge_loop_clear_signals_are_never_held_by_the_hourly_cap` = **ok** → 「FAIL 이면 기반 e2515bb0 단독 대조」 조건 불성립이라 대조군 미실행 · census·hwmon·b6_lsof 도 초록) · u2-smoke **12/12** · u2-mutants **10/10**(U2-NOFOLLOW 포함) · cys-app **296/0**(1 ignored · `cargo test -p cys-app --bins`) · 윈 타입체크 오류 0(커밋마다) · ui tsc = 2판 ui 변경 0(`git diff --stat ad3d5eb5..HEAD -- ui` = 0) · 이 작업트리 node_modules·bun 없음 → 미실행(정직) · **real-roots 판정 = U2 이름공간 실 쓰기 0**(`~/.cys/update` 미생성 · 복구기 plist 0 · counsel/updates.jsonl 0) · 그 밖 변화 56 = `~/.local/state/cys` 14 · `~/.cys/secure-backups` 12 · `~/.cys/claude` 14 · `~/.cys/state` 9 · `~/.cys/pack/round`(이 워커 TODO) 등 — 살아 있는 데몬·다른 세션·내 TODO 쓰기로 보이나 프로세스 귀속은 못 함(판정 밖 · 목록 보존)
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
- ⓗ ★2판 · 📌 master 결정 필요: 팩 CLI(init-pack·pack-update)를 전역 저널 PACK_APPLY 에 묶는 배선(C14)을 a36892cd 에서 **철회** — 앱이 기동마다 `init-pack` 을 부르므로 그동안 부팅 가드가 데몬을 막고(rc 75) 설치기와도 겹친다. 남은 길 = ① 러너 트랜잭션 안의 팩 적용(S10 rotate→init-pack 위임)만 PACK_* 를 쓰게(권고 · 설계 §3-11 의 「PACK_*」 출처가 러너 경로라면 이것) ② CLI 도 쓰되 부팅 가드에서 PACK_* 를 「참가자 잠금이 쥐어져 있으면 허용」 으로 완화. 지금은 팩 저널(.pack-journal)이 CLI 도중 죽음을 맡고, 전역 PACK_* 복구는 사용자 트리 검증까지 한다.
- ⓘ ★3판(Fable 2R m6): 설계 §3-11 재구성 ①(윈 = 설치판 설치기 재실행 → 재대조) ②(맥 = `.cysr.app.old-*` 중 옛 판 일치본을 정식으로 승격) 미구현 — 지금은 정식 자리가 어느 판과도 안 맞으면 즉시 좌석 0(seats_blocked · fail-closed · 사람 필요). 다음 판.
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
| N1 | BLOCK | rotate(위임 · 자식 잠금 쥠) → init-pack --txn 자식 WouldBlock → S10·RB start_old 실패 | 채택 | bf59a37c | `CYS_UPDATE_TXN_DEPTH` 재진입 · `verify_delegated_at` · ★u2-smoke ⑥ 실 rotate→init-pack 왕복 rc 0(음성 대조 rc 24) · `nested_delegation_reenters_child_lock_but_siblings_still_exclude` · 뮤턴트 U2-NEST |
| N2 | BLOCK | V2 = 이 사용자 cysd 전수(부서 21개) → V2·RB_VERIFIED 결정론 실패 | 채택 | 40a69be7 · 6a1da528 | `hq_daemon_count`(본부 소켓 identify pid 1) · ★`v2_counts_only_the_hq_daemon_identified_by_socket`(가짜 cysd 2 + 본부 = 1) |
| N3 | BLOCK | 재구성 = 최근 스냅샷으로 상태 폴더까지 무대조·데몬 생존 중 덮음 | 채택 | caaab5c7 | `reconstruct_trees`·`snapshot::diff`·`reconstruct_protected` · ★`reconstruct_compares_then_restores_only_mismatched_pack`(일치 무변경 · 어긋난 팩만 · 옛 시도 스냅샷 아님 · app-notify 무접촉 · 정지 실패 = 복원 0) |
| M1 | MAJOR | is_held 배타 탐침 = 거짓 rc 26·거짓 busy·설치기 창 | 채택 | d19674a0 | 공유 탐침 + 재탐침 · 러너 acquire 순간 막힘 재시도 · `probe_is_shared_and_runner_rides_out_transient_probe` |
| M2 | MAJOR | prev 후보 문자열 중복 제거 → 부모 심링크에서 RB_FAILED | 채택 | c98fb2d9 | canonicalize 뒤 중복 제거 · `prev_candidates_dedupe_through_parent_symlink` |
| M3 | MAJOR | stop_seats = --skip-drain 전체 정지(설계 ③ 초과) | 채택 | 64c8795f | 표지만 · cysd `surface.create` 새 좌석만 거부 · 부팅·기존 좌석 유지 · `stop_seats_marker_blocks_new_seats_only_for_revoked_installed_seq` |
| M4 | MAJOR | PACK_* 생산 쓰기 경로 0(§3-8 미구현) | ⟨M4⟩ | ⟨M4SHA⟩ | ⟨M4TEST⟩ |
| m1 | MINOR | participate Ok(None) 범위 넓음(fail-open) | 채택 | 6a1da528 | 폴더 생성 불가만 Ok(None) · 그 밖 Err |
| m2 | MINOR | build-info 실행 전 서명 검증 없음(canonical·후보) | 채택 | 6a1da528 | `verify_signature_pin` 선행 · 실패 = 판독 불가/후보 제외 |
| m3 | MINOR | 윈 시한 뒤 종료 실패 = 무기한 대기 | 채택 | f790a91a | 종료 확인 상한 10분 · 초과 = RollbackBlocked → RB_FAILED 직행 · `installer_stuck_goes_straight_to_rb_failed_without_rerunning_installer` |
| m4 | MINOR | 재구성 격리 키 고정 | 채택 | caaab5c7 | `reconstruct-<벽시계>` |
| m5 | MINOR | realroots 정규식에 상담소 신호 경로 없음 | 채택 | 6a1da528 | `counsel/` 전체 U2 이름공간 |
| m6 | MINOR | §3-11 재구성 ①②(윈 설치기 재실행 · 맥 .old-* 승격) 미구현이 HANDOFF 에 없음 | 채택(문서) | 이 문서 | §5 ⓘ 명기 · 지금 = 불일치 즉시 좌석 0(fail-closed) |
| m7 | MINOR | S8b 가 N3~N5·세대 토큰 재판정 안 함 — 생략 근거 미기록 | 채택(문서) | 이 문서 | §2-14 명기 |
