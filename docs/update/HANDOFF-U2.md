# HANDOFF-U2 — 1.1.8 데몬 자동 갱신 U2(교체·롤백·러너·복구 · 데몬·CLI 쪽) · TICKET=cysr-118-u2-runner

> 브리프 = [master#71f53d34](파일 정본 `~/axdev/master/briefs/2026-10-06-cysr-118-u2-runner.md`) · 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md`(4판 · U1 편입).
> 가지 `u2/runner-118` off `e2515bb0` · 워커 = worker-2(계정2 · Opus) · 커밋 = `git log --oneline e2515bb0..HEAD`.

## §0 델타(다음 사람이 먼저 읽을 것)
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
5. **rotate 잠금 참가**: 토큰 없는 rotate 는 잠금 파일이 **있을 때만** 잡는다 — 갱신을 한 번도 안 한 기계에 잠금 파일을 새로 만들지 않으려고(그 기계엔 잠금을 쥔 러너가 있을 수 없으므로 의미 동일).
6. **S5 재검사**: 「drain 이 쓴 출력은 drain 기록과 대조해 제외」 대신 **drain 직후 토큰 T1 → 정착 창(기본 20초) → T2** 비교 — drain 출력은 T1 앞에 끝난다. 단점 = 정착 창만큼 느림.

## §3 연결하지 않은 것 · 다음 티켓
- U4: 앱 알림(위 `state.json` 칸 · `seats_blocked` 고정 안내) · 앱 창 재열기 · `macupdate` 앱 쪽 집행 함수 삭제(lib 사본으로 대체).
- U3/master(비가역): 설치기 변경 0(이번 티켓 무변경 — ⓪-a 는 U3 판 그대로 소비) · 실키·피드 게시 0.
- §5 미결 ⓐ~ⓓ.

## §4 시험 결과(격리 래퍼 `/private/tmp/claude-501/s118/u2/isoenv.sh` = EVIDENCE-118 §8 꼴 · 실 `~/.cys`·실 LaunchAgents·실 counsel 쓰기 0 — 끝에 `ls` 로 확인: `~/.cys/update` 없음 · plist 0 · updates.jsonl 없음)
- `update::` 188/0(lib 부분) · cysd 전수 **2462/0**(7 ignored · 정비 모드 배선 뒤 · 20:37–20:44) · 스케줄 묶음 102/0(내장 잡 추가 뒤) · 윈 타입체크(`scripts/win-typecheck.sh`) **오류 0**(2회차 · COM 포함).
- 전수 3묶음 + cys-app 재측정 = 아래 「전수」 줄(이 문서 커밋 직전 실행 · 환경 3 = census·hwmon·b6_lsof 분리 규칙).
- **전수(수리 뒤 재측정 · 격리)**: lib **961/0**(1 ignored · 21:21–21:28) · cys **585/0**(21:28–21:30) · cysd **2462/0**(7 ignored · 21:13–21:19 · 수리분 = lib 스폰 헬퍼 교체뿐이라 cysd 행동 무변경) · cys-app **296/0**(1 ignored · 21:21) · 윈 타입체크 3회차 오류 0(21:30–21:31) · `update::` 188/0 · u2-smoke 10/10 · u2-mutants 10/10. 환경 3(census·hwmon·b6_lsof) 이번 실행에선 전부 초록.
- **첫 전수에서 난 적색 4(전부 고침 · c6577bb1)**: 스폰 인구조사 3(원시 `Command::new` 동결표·콘솔 창 정책·python 직스폰 봉인) + rotate 디스패치 소스 핀 1. 교훈 = 새 lib 스폰은 `hidden_command`/`python_command`+등급 · 동결표 등재는 등급을 단 1곳만.
- cys-app 시험 환경 함정: 작업트리에 `src-tauri/binaries/`(cys·cysd 사이드카) · `src-tauri/resources/`(pack·manifest) · `src-tauri/runtime/` · `ui/dist/` 가 없으면 빌드 실패 — 전부 gitignore · U1 작업트리에서 복사(커밋 0).

## §5 미결 · 함정
- ⓐ `installed_revoked` ② 자동 롤백 미구현 — 지금은 판정 칸 + `state.json installed_revoked{stop_seats}` + 결정 `stop_seats` 로 교체 0. 구현 시 맥 = `/Applications/.cysr.app.old-<seq>` 를 자산 삼은 RB 경로 · 윈 = `installers\<seq>\` 설치기.
- ⓑ 러너 생존 R1(맥 Survivor · cysd 정지 중) = **실측 0** → VM M1.
- ⓒ 윈 COM vtable 칸 번호(taskschd.h 순서)·작업 XML 이 실제로 등록·재독되는지 = **실측 0**(타입체크만) → W1 ⑤ · W2 ⑦.
- ⓓ `pack::recover_pack_journal` 부팅 때 호출 경로는 복구기(`--recover`)에만 — cysd 부팅 자체는 부르지 않는다(부팅 가드가 PACK_* 를 막고 복구기가 종결).
- 함정: 시험 하네스가 잠금 파일을 0644 로 만들면 lock 모듈이 「권한 불일치」로 fail-closed(첫 종단 실행 BAD 2의 원인 · 제품 결함 아님 · 0600 으로 고침).
- 함정: 러너 판정은 pmset/ioreg 등으로 수 초 걸린다 — 종단 시험 대기 3초는 짧다(30초 폴링으로 고침).
- N7 공간식 계수(첫 회): 이 맥 기준 백업 예상 ≈0.27 GiB(상태) + 팩 ≈49 MiB + local 48 KiB · 예약 2 GiB — 자산 크기·max_unpacked 는 릴리스 본문 값.

## §6 재현
- `git log --oneline e2515bb0..HEAD` · `isoenv.sh cargo test --lib update::` · `isoenv.sh cargo test --bin cysd update_hold` ·
  `U1_ISO=<isoenv.sh> scripts/tests/u2-mutants.sh` · `cargo build --bin cys --bin cysd && scripts/tests/u2-smoke.sh` · `scripts/win-typecheck.sh`.
