# HANDOFF-U1 — 1.1.8 데몬 자동 갱신 U1(피드·검증·판정·공용 모듈) · TICKET=cysr-118-u1-autoupdate

- 좌석 = worker surface:1290(291 118u1) · 계정2 · Opus · 가지 `u1/autoupdate-118`(off `7e7aa5da` = 1.1.8 병합 완료판) · **push 0**
- 브리프 = [master#2b976211] 2026-10-06 08:11 · 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md` 4판
- 이 문서의 시각·수는 전부 도구 출력(git 커밋 시각 · `date` · 시험 결과 줄)에서 옮겼다.

## §0 델타(다음 사람이 먼저 읽을 것)
- ★★★★★**4판 끝(13:1x · 지시 = [master#9112a952] 12:47 · 3R 원문 = `~/axdev/master/reports/cysr-118-plan/REVIEW-U1-fable-3r.md` · 수렴 예 · BLOCK 0)** — 산출 = 【확인요청】 4판(4R 없음 · master 정독+게이트) · 반영표 = §9-2 · BACKLOG F5~F11 = §6:
  - **커밋**: 40fa1e9c(F1 trusted 잠금 · F2 첫 판 탐침 · F3 windows-health update:: 스텝 · F4 복원) · 192262f0(F1 결정론 뮤테이션 시험) · 이 문서 커밋. push 0.
  - **시험(격리)**: 40fa1e9c 기준 lib **897/0**(1 ignored · 302초) · 192262f0 뒤 `update::` **126/0** · `scripts/tests/u1-mutants.sh` **35/35 OK**(13:03–13:09 · 가드 31 + 소스 변이 patch 4) · 윈 타입체크 오류 0(12:56–13:01). cys·cysd·cys-app = 4판이 `src/update/{check,cli,feed,lock}.rs` 안만 바꿔 3판 수치 유지(재실행 0 — 정직).
  - **정직 1**: 첫 F1 시험(4스레드 경합)은 뮤테이션 1회차에서 가드를 끈 채 녹이 나왔다(경합 확률적) → 결정론 배타 시험으로 교체 · 경합 시험은 부하 시험으로 남김.
  - **다음**: master push → 윈 러너 windows-health `update::` 126건 초록 = 머지 조건 → merge/v0.14.43 머지.
- ★★★★**3판 끝(12:3x · 지시 = [master#2dc1891f] 11:42 + 추가 1항 [master#450449c8] 12:02 · 2R 원문 = `~/axdev/master/reports/cysr-118-plan/REVIEW-U1-codex-2r.md` · 기준 502c9fe2)** — 산출 = 【확인요청】 3판 · 반영표 = §9:
  - **커밋**: bcc3c457(B6·B7·M3) · 59bdd263(B5·N4·N5·M4·M5·N2·N3·N6·B9) · e1034052(뮤테이션 저장소 편입 + 소스 변이 patch 4) · bbff9184(첫 판 seq 1 = SEQ1) · 이 문서 커밋. push 0.
  - **시험(격리)**: e1034052 기준 lib **893/0** · cys **582/0** · cysd **2460/0** · cys-app **296/0** · bbff9184(cli.rs 1함수 변경) 뒤 lib+cys 재측정 = §4 · `scripts/tests/u1-mutants.sh` = §4 · 로컬 윈 타입체크(`scripts/win-typecheck.sh`) 오류 0.
  - **다른 티켓이 알아야 할 계약 변화** = §9 끝 단락(열거 행 `outcome` 아래로 · 결정 `stop_seats` · cysr any 금지 · 신뢰 기록 `trusted/` 배치 · seq 1 첫 판 통과).
  - **남은 것(지시대로 코드 0)**: B8 = U2 · H⑬ = U4 · N1 = U3 3판 · N9 윈 러너 = master push 뒤 ci-branch · 정본 문서 편입 = master.
- ★★★**2판 끝(11:2x · 재개 [master#113a3975] 10:52 · 소요 10:52–11:25 ≈ 33분)** — 산출 = 【확인요청】 2판:
  - **커밋**: `0ea0381a`(cli.rs 6오류 · B1 호출부 · B3 CLI · B4 · 종단 시험 agora-client 로 재작성) · `0fb4d824`(U3 이관 4 ⑴~⑷ + M8 + mach 경고 제거) · 이 문서 커밋(MINOR help/actions · §7 1R 반영표 · §8 schema 부록). push 0.
  - **시험(격리 · §4)**: Rust lib **878/0**(1 ignored) · cys **582/0**(j3 포함 — after_help 1줄로 스택 영향 없음) · cysd **2460/0**(7 ignored) · cys-app **296/0**(1 ignored) · `update::` 106/0 · **뮤테이션 22쌍 전건 적/녹 OK**(§7).
  - **남은 것(U1 범위 밖 · 기록)**: B8·install_id = U2 · 설계 문서 편입(§8 schema · H⑦ 상태명 · §5-1 경로) = master · 윈 전용 새 코드 컴파일 = 윈 CI 런 필요(아래 정직 줄 그대로).
  - ★**교차 영향(U3)**: B4 뒤 cysr 에 `--installed-release-seq` = rc 2 → U3 `release-gate.py` 는 cysr 열거를 `--enumerate-installed` 로 바꿔야 한다(§7 끝 단락).
  - 【결정필요】 ③ MINOR IDNA = 비 ASCII 호스트 전량 거부 **유지** 권고(§7 · 단점 1줄 = 설계 문면 「IDNA 정규화 뒤 대조」와 다름 → 설계 한 줄 정정 필요).
- (이력) 아래 「2판 진행 중 매듭」 줄은 09:3x 순환 직전 기록 — 위 줄로 대체됨.
- ★★**2판 진행 중 매듭(09:3x · [master#8b1000e9] CTX 65% · 2판 지시 = [master#9f66c96f] · 1R 원문 = `~/axdev/master/reports/cysr-118-plan/REVIEW-U1-codex-1r.md`)** — 후임은 이 줄부터:
  - **상태**: WIP 커밋(이 커밋) = **lib 컴파일 실패 6건, 전부 `src/update/cli.rs`**(호출부가 바뀐 API 를 아직 안 따름: `buildinfo::state_dir()` 가 이제 `Result` · `check::bump_trusted(dir, signed_at)` 인자 2개 · `AcceptedFeed` 칸 = `{feed_rev, envelope_sha256, feed_release_seq, installed_release_seq, signed_at, at}`). 그 밖 모듈은 컴파일된다(`cargo build --lib` 오류가 cli.rs 뿐). **시험은 아직 한 번도 안 돌렸다**(새 뮤테이션 시험 포함).
  - **증명 장치**: `update::mutant("<번호>")` = 시험 빌드에서만 `CYS_U1_MUTANT=<번호>` 일 때 그 수리 가드 1곳을 끈다. 증명 = 각 시험을 `CYS_U1_MUTANT=<번호>` 로 돌려 적색 · 없이 돌려 초록(격리 래퍼 `/private/tmp/claude-501/s118/u1/isoenv.sh` · 예: `isoenv.sh env CYS_U1_MUTANT=B2 cargo test --lib update::feed::tests::b2_`). 번호 ↔ 시험: B1 `b1_release_ignores_env…`(buildinfo) · B2 `b2_same_feed_rev…`(feed) · B3 `b3_installed_stop_seats…`(feed) + `b3_revocations_copy…`(check) · B5 `b5_second_anchor…` · M9 `m9_common_required_fields` · SM `sm_breaking_release_is_feed_reject` · M6 `accepted_record_roundtrip…`(끝 2줄) · B6 `b6_arg_must_equal_env` + `b6_handover_race…`(lock) · M3 `m3_private_permissions`(lock) · B7 `b7_post_side_effect…`(journal) · M7 `m7_readonly_last_seq…`(hold) · M1 `m1_structure_damage…`(sched) · M2 `m2_only_file_not_found…`(win) + gates `each_gate_true_false` 의 N12 "garbage" 행 · M4 `m4_every_response_date…`(clock).
  - **끝난 번호(코드 + 시험 작성 · 미실행)**: B1(state_dir 출시 빌드 env 무시·`.` 후퇴 0 · `resolve_state_dir`) · B2(수용 기록 봉투 sha256 · 같은 rev 다른 봉투 = replay) · B3 피드 쪽(R 검증 직후 설치판 폐기·stop_seats·폐기문을 모든 뒤 실패 결과에 실음) + 기록 쪽 함수(`check::record_revocations` 원문·서명·sha·rev·수용 Stamp 내구 기록 · `load_accepted_revocations` 30일·sha 대조 · `--check` 폐기문 미도달 시 대체) · B5(맥 cdhash·dr_pin_id 40hex · 윈 a2_sig_url 필수 · ⓖ) · B6(묘비 후 해제 · ⓪ 인자=env · ①′ 이중 읽기 · ③′ pid 시작 시각 · `acquire_or_delegate(dir, owner, arg, env)`) · B7(A/B 슬롯 generation · 최신본 안 덮음 · 한 슬롯 손상 = `Degraded` → 재구성 · 쓰기 거부) · M1(schedule 구조 계약 · 손상 = None·이행 쓰기 0) · M2(SAC = `RegGetValueW` 3갈래 · 값 없음만 absent · 게이트 N12 통과 = off/absent/n/a 만) · M3(갱신 폴더 0700 재검증 · 잠금·소유자·보류 로그·저널·수용·신뢰 파일 0600 · 윈 보호 DACL) · M4(맥 `mach_continuous_time` · 모든 응답 Date) · M6(손상 기록 덮지 않음 · feed/설치 seq 분리) · M7(읽기 전용 판독 해시·단조) · M9(build_id·features 칸 전 부품 필수 · cysr bundled_pack digest 64hex · sha256 소문자) · SM(breaking = 피드 ⓛ 거부 · 게이트 배열 정본 14칸).
  - **남은 번호**: ⓐ `cli.rs` 마무리 = B1 호출부(`state_dir()?` → Err 면 rc 3) · **B3 CLI**(`--record`: `o.revocations.is_some()` 이면 판정과 무관하게 `record_revocations(입력 폐기문 바이트)` + `bump_trusted(o.trusted_signed_at)` · uptodate 면 `write_accepted{feed_rev, envelope_sha256: o.envelope_sha256, feed_release_seq: o.release_seq, installed_release_seq: installed,…}` · 기록 실패 = rc 3 · 가드 `mutant("B3r")` + 종단 시험) · **B4**(`--component cysr` 에 `--installed-release-seq` = 거부 rc 2 · agora-client 만 허용 · 가드 `mutant("B4")` + 종단 시험 — 기존 종단 시험 `update_verify_end_to_end_with_record` 는 cysr 에 그 인자를 쓰므로 agora-client 로 바꾸거나 내장 seq 로 다시 짜야 함) ⓑ **M8**(좌석 사실 파서를 lib `gates::seat_fact_from(node, org, prompt_ready) -> Option<SeatFact>` 로 · 필수 계기 하나라도 없으면 None · cys.rs `update_seat_facts` 가 사용 · 가드 `mutant("M8")`) ⓒ MINOR help/actions(`Cli` `after_help` 1줄 + `Command::Actions` 가 `update::cli` 파서 하위 명령도 싣기 · 전체 `--bin cys` 로 j3 확인) ⓓ HANDOFF 부록 「폐기문·위임·폐기 항목·kind JSON schema 문면」(B9 · master 가 설계 §4-1·§6-1 편입 · dr_pin_id = 인증서 leaf sha1 40hex · cdhash 40hex · delegation pubkey = minisign 공개키 raw 키라인 base64(42바이트) 또는 .pub 전체 base64 · key_id = 공개키 keynum 리틀엔디언 → 대문자 16진 16자 = `packsig::pubkey_key_id`) ⓔ HANDOFF §「1R 반영표」(번호별 처방 1줄 · 뮤테이션 적/녹 실측) ⓕ 뮤테이션 적/녹 전건 실행 → 격리 Rust 3 + cys-app 재측정 → 커밋 → 【확인요청】 2판.
  - **U2 이관(기록만)**: B8(보류 로그 원자 커밋·ACK 재독·crash 행렬) · MAJOR install_id 운영 생성 배선.
  - **정직**: 윈 전용 새 코드(`ensure_private_dir` 윈 갈래 SetFileSecurityW · `read_sac_registry` RegGetValueW)는 이 맥에 윈 타깃이 없어 **컴파일 미확인**(심볼은 windows-sys 0.59 소스에서 실재 확인 · 윈 CI 런 필요). 1판의 윈 갈래(GetTickCount64 등)도 같다.
  - **다음 한 줄**: `cargo build --lib` 로 cli.rs 6오류부터 고친다(ⓐ) → `cargo test --lib update::` 초록 → 뮤테이션 적/녹 → ⓑⓒⓓⓔ.
- ★**최종(09:0x · [master#226f0314])**: 산출 = 수용 후보(master 독립 게이트 스냅샷 + codex 적대 1R 뒤 확정) · 【결정필요】 ① = **A 확정**(그 자리 + `update::launch_win` 재노출 · 설계 §5-1 경로 1줄 정정 = master) · ② = **채택**(cutover 2026-11-01T00:00Z 상수 유지 · U3 발행 게이트 「min_binary 빈 값 = 발행 거부」 = master 추가) · 팩 메모리 등재 = master 보류 · U2 상한 = 코드 몫(이 계수) / 실기 몫(실측 없음) 둘로 · **CYCLE-SAVED · 새 작업 0 · 대기**.
- 끝난 것: `src/update/` 17파일(5.6천 줄 · 시험 82) + build.rs · packsig · cysd org.status 가산 키 1 · cys.rs main 앞단 배선. 커밋 9개(아래 §1).
- 시험: Rust lib 852/0 · cys 582/0 · cysd 2460/0(격리 env · 실패 0 · 환경 3 census·hwmon·b6_lsof 도 이번 실행에선 초록) · cys-app 296/0(§4).
- **U1 판의 `cys self-update --check` 결정은 언제나 `hold`** 다 — N14(복구기 등록 = U2)·N7(롤백 자산 공간식 = U2 스냅샷 실측 뒤)이 사실상 「없음」이기 때문이고, 교체 경로가 없는 판에서 그것이 올바른 답이다.
- 실키 0 — 내장 키링에 갱신 용도 키가 0개라 실 피드 검증은 전부 「알 수 없는 key_id」로 거부된다(자리표시 = fail-closed). U3 가 R·U·F 공개키를 `cysjavis-pack/trusted-keys.json` 에 `purpose` 칸과 함께 넣으면 열린다.
- 【결정필요】 2건 = §2 ①·②.

## §1 모듈 × 파일 × 시험 × 소요(실측 — 소요 = 그 묶음을 쓰기 시작해서 커밋까지의 벽시계)
| 묶음 | 파일 | 시험 수 | 커밋 | 소요 |
|---|---|---|---|---|
| 설계 정독 + 코드 지도 | — | — | — | 08:11–08:17 · 6분 |
| ① 오류 사전 · 키링 purpose·폐기문 · 두 겹 피드 `verify_feed` ⓐ~ⓝ · URL 규칙·홉 · 시계 · packsig 팩 용도 거르기 | errors.rs · keys.rs · feed.rs · url.rs · clock.rs · packsig.rs | 5+8+17+3+5 · +1 | 258905c1 08:24 | 08:17–08:24 · 8분 |
| ② build-info · `CYSR_RELEASE_SEQ` · VERSIONINFO 4번째 마디(스크래치 실측 포함) · install_id · 상태 폴더 | buildinfo.rs · build.rs | 5 | 46c98072 | 08:25–08:29 · 5분 |
| ③ 게이트 N1~N14 · bulk·publish 스키마·이행 ①~⑤ · org.status `human_idle_secs` | gates.rs · sched.rs · cysd handlers.rs | 5+5 | a29d0f73 | 08:29–08:32 · 4분 |
| ④ 잠금+위임 토큰 · 저널 · 보류 로그 | lock.rs · journal.rs · hold.rs | 4+5+4 | c4be5b56 | 08:32–08:34 · 3분 |
| ⑤ 📌15 원작자 편입(update_launch 재노출 · SAC 이식) | win.rs · mod.rs | 3 | 59c675a5 | 08:34–08:36 · 2분 |
| ⑥ D23 cutover + 자동 경로 게이트 | packsig.rs · packgate.rs | 1+1 | a1af46a2 | 08:36–08:37 · 1분 |
| ⑦ CLI 3동사 + 네트워크 sink + `--check` 사실 모으기 + 종단 시험 | cli.rs · check.rs · net.rs · cys.rs | 3+3+4 | 0ed04173 08:43 | 08:37–08:43 · 6분 |
| ⑧ 전체 재측정(Rust 3묶음) | — | — | — | 08:43–08:58 · 15분(실행 260+137+407초) |
| ⑨ 실패 분류 MA7(§7-1 대조 중 발견한 빈칸) | failures.rs | 2 | 328b8c35 | 08:58–09:00 · 2분 |
| ⑩ cys-app 재측정 · 이 문서 · 보고 | — | — | — | 09:00– |

**U2·U3 계수로 쓸 때의 주의(정직)**: 위 소요는 「순수 함수 + 단위 시험」 코드 쓰기 속도다(≈5.6천 줄 / 코딩 ≈31분). U2 는 실 교체·VM M1~M3·윈 실기 대기·강제 종료 행렬이 시간을 지배하므로 줄 수 비례로 옮기면 과소다 — U2 의 코드 쓰기 몫에만 이 계수를 쓰고, VM·실기 몫은 「실측 없음 · 첫 실행으로 확보」로 적어야 한다.

## §2 설계와 다른 점 · 설계에 없던 것을 보충한 점(정직)
- ① 【결정필요】 **원작자 `update_launch.rs` 위치**: 설계 §5-1 「`src/update/launch_win.rs` 로 옮긴다」 ↔ 실제 = 파일은 `src/update_launch.rs` 그대로 두고 `update::launch_win` 으로 재노출. 이유 = 옮기면 ⓐ 윈 실기 레인 `windows-health.yml` 시험 필터 `update_launch::` ⓑ 앱 핀 시험 `include_str!("../../src/update_launch.rs")` 가 깨진다(CI 워크플로 변경 = master 게이트). 바이트 동일성은 유지(`git hash-object` = `96f1fd1b…` = `up/v0.14.43:src/update_launch.rs`). 권고 = 그대로 둠 · 단점 1줄 = 설계 문서의 파일 경로 표기와 실물이 다르다(설계 §5-1 한 줄 정정 필요).
- ② 【결정필요】 **D23 cutover 시각 = `MIN_BINARY_REQUIRED_EPOCH = 1_793_491_200`(2026-11-01T00:00:00Z)** — 설계·📌9 에 값이 없어 내가 정했다. 근거 = 서명 두 레인(release.yml `PACK_MIN_BINARY='1.1.7'` · pack-release.yml 정책 파생)은 이미 값을 채우므로 정상 발행은 막히지 않는다. 단점 1줄 = 그 시각 뒤 어느 레인이든 빈 값으로 서명하면 1.1.8+ 기기 전부가 그 팩을 거부한다(의도된 fail-closed 지만 발행 쪽 실수가 곧 전량 거부).
- ③ 폐기문 `revoked_releases[]` 항목에 **`component` 필수**(설계 표에 없음) — `release_seq` 는 부품별 번호라 cysr 7 과 agora-client 7 이 겹친다.
- ④ 위임 항목 `delegations[]` 에 **`pubkey` 필수**(설계 표에 `{key_id, purpose, not_after}` 만) — 공개키 없는 위임은 검증에 쓸 수 없다. 위임 key_id ≠ 공개키 파생 key_id = 거부.
- ⑤ 폐기문 서식 표지 `kind = "update-revocations"` 추가(§4-6 교차 사용 원칙을 폐기문에도).
- ⑥ 잠금 소유자 내용을 `txn.lock` 이 아니라 **`txn.owner.json`**(원자 쓰기)에 둔다 — 윈 `LockFileEx` 는 잠긴 범위를 다른 핸들이 읽지도 못하게 막아 「자식이 소유자 내용을 읽는다」(위임 ①)와 충돌. 낡은 기록은 위임 ②(잠금 실재)가 거른다.
- ⑦ 저널 종결 표지 **`DONE`·`DEFERRED`·`PACK_DONE`** 추가 — 설계 상태 = 「들어가는 단계」라 끝난 뒤 이름이 없고, 복구기·부팅 가드가 「비종결」을 가르려면 필요. 정식 이름(S1_LOCKED … RB_FAILED · PACK_APPLY/PACK_ROLLBACK)은 설계 철자 그대로. 저널마다 `crc`(본문 sha256) — 파싱은 되나 값이 바뀐 손상도 손상으로 읽는다.
- ⑧ CLI 3동사 **배치**: 최상위 `Command` 가 아니라 `main` 의 `Cli::parse()` 앞 별도 파서(`update::cli::dispatch`) — 최상위 clap 열거형을 늘리면 j3 시험 스택 넘침(1.1.8 W1 실측). 철자는 설계 그대로. 대가였던 「`cys --help`·`cys actions` 목록에 안 보인다」 = 2판에서 정적 1줄 + actions 편입으로 닫음(§7 MINOR help).
- ⑨ `update-verify` 보충 인자 `--installed-release-seq`(**agora-client 전용** · 필수 — 2판 B4: cysr 에 주면 rc 2) · `--target` · `--record`(2판 B3: R 검증을 통과한 폐기문은 판정과 무관하게 원문째 기록 + 신뢰 시각 상향 · uptodate 면 수용 기록 · 기록 실패 = rc 3 — §6-3) · `--enumerate-installed`(2판 · 출발 seq 열거 · §7 ⑷) · 디버그 빌드 전용 `CYS_UPDATE_NOW`.
- ⑩ 오류코드 매핑(사전에 「서식 오류」 낱말이 없음): 봉투 계층 서식·키·서명 = `feed_sig_bad` · 본문 계층 = `release_sig_bad` · ⓛⓜ 계약 위반 = `verify_failed`(URL = `url_refused` · cysr `requires.min_binary_for_pack` = `pack_min_binary_empty`) — 단계는 `step` 칸(ⓐ~ⓝ).
- ⑪ 상태 폴더 작은 기록의 이름·서식 = `config.json{auto, channel}`(N9 · 부재 = auto ON · stable) · `holds.json{holds[{until,reason}]}` · `state.json{last_success, failures}` · `trusted/CURRENT`(세대 번호) → `trusted/gen-<N>/{trusted.json{revocations_rev, revocations_sha256, revocations_accepted_at(Stamp), last_trusted_time}, revocations.accepted.json, .minisig}`(2판 B3 · H⑪ · 3판 N6 = 세 파일 한 세대 커밋) · `hold-cursor.json{delivered_hold_seq}` — 설계는 `state.json`·`holds.json` 이름만 줬다.
- ⑫ N12: 윈에서 SAC 값 없음(윈10 · `reg` 비 0 종료) = `"absent"` = 통과(SAC 가 없으면 4551 차단도 없다 · 실제로 막히면 원작자 `classify_launch_error` 가 잡는다).
- ⑬ build-info `features` = 빈 목록(V7 정본 ID 목록은 U2·U4 — 근거 없는 ID 를 지어 넣지 않음).

## §3 연결하지 않은 것(U2·U3·U4 · master 게이트)
- schedule.json 이행의 실 파일 배선(cysd 첫 기동) · 적재 거부(`cys schedule add`·로드) · 내장 잡 `bulk:false`·`publish:false` 명시 — 설계 §8 비가역 ⑦(1.1.8 발행과 함께).
- 잠금 참가자 배선(rotate·pack-update·pack-plan·init-pack·데몬 자동 기동·설치 링크·NSIS ⓪-a) · `rotate --stop-only/--skip-drain --txn` — U2·U3.
- 정비 모드 RPC · 보류 로그 → `queue-state.json` 원자 이관(`hold_ingested`) · `delivering` 표지 — U2(모듈과 계획 함수 `plan_ingest` 는 있음).
- `cys config set update.auto off` · `cys update hold --hours` 설정 명령 — 읽기 쪽만 있음(N9·N5 ⓐ).
- 복구기 등록(N14) · 롤백 자산 공간식(N7) · `run_installer_wait` · 교체·롤백·사후 검증 V1~V9 · 알림 — U2·U4.
- 실키 기입·피드 게시·설치기 변경 — U3(비가역 · master).
- 동봉 팩 매니페스트 빈 `min_binary` 의 원인(보고만 · 수정 0): `scripts/bundle-prep.sh:55` 가 `cys pack-manifest` 를 `--min-binary-version` 없이 불러 `src-tauri/resources/pack-manifest.json`(앱 번들 동봉 · **서명 없는** 사본)을 만든다(`cys pack-manifest` 기본값 = 빈 문자열 · cys.rs 시험 핀 「min_binary_version 기본 빈문자열」). 윈 설치 폴더의 `%LOCALAPPDATA%\cys\pack-manifest.json` 이 그 사본. 서명 레인 manifest 는 값이 있다.

## §4 시험 결과(격리 env · 래퍼 `/private/tmp/claude-501/s118/u1/isoenv.sh` = EVIDENCE-118 §8 꼴 · 실 ~/.cys 쓰기 0)
- ★★**3판 재측정**: e1034052 기준(11:58–12:17) `cargo test -p cys-terminal --lib --bins --no-fail-fast` = lib **893 passed / 0 failed / 1 ignored**(295초) · cys **582/0**(157초) · cysd **2460/0 / 7 ignored**(415초) · `cargo test -p cys-app` = **296/0 / 1 ignored**(사이드카 사본 = 같은 빌드) · 측정 뒤 격리 디버그 cysd 잔존 0. 윈 타입체크(11:57–12:00) = 오류 0 · 경고 56(전부 기존 · `src/update` 0). bbff9184 뒤(12:18–12:30) = `scripts/tests/u1-mutants.sh` **33/33 OK**(가드 29 + 소스 변이 patch 4 · 되돌림 뒤 작업트리 깨끗) · lib **894/0**(1 ignored · 264초) · cys **582/0**(138초) · cysd·cys-app 은 bbff9184 가 `update/cli.rs` 함수 1개만 바꿔 e1034052 수치 유지(재실행 0 — 정직).
- ★**2판 재측정(11:07–11:23)**: `cargo test -p cys-terminal --lib --bins --no-fail-fast` = lib **878 passed / 0 failed / 1 ignored**(270초) · cys **582/0**(139초) · cysd **2460/0 / 7 ignored**(404초) · `cargo test -p cys-app` = **296/0 / 1 ignored**(사이드카 사본 = 11:09 디버그 빌드로 갱신). 측정 뒤 격리 디버그 cysd 잔존 0(`pgrep` 빈 출력). 뮤테이션 = `mutants.sh` 22쌍(11:03–11:06) 전건 OK. CLI 실측 = `cys --help` 끝 줄 · `cys actions` 81개(갱신 3동사 포함 · `update-verify` 인자에 `enumerate-installed`).
- (1판 기록 — 아래 줄들은 08:43–09:0x 측정)
- Rust 전체(`cargo test -p cys-terminal --lib --bins --no-fail-fast` · 08:43–08:58): **lib 852 passed / 0 failed / 1 ignored · cys 582/0 · cysd 2460/0 / 7 ignored**. 실패 0 이라 환경 3(census·hwmon·b6_lsof) 분리 보고 대상 없음. (이 실행은 failures.rs 등록 전 — 그 2시험은 `cargo test --lib update::` 82/0 으로 따로 확인.)
- cys-app(`cargo test -p cys-app` · 09:0x): **296 passed / 0 failed / 1 ignored**(W3 수치 296/0 과 같음). 빌드 전제(전부 git 제외 · 로컬만): `src-tauri/binaries/{cys,cysd}-aarch64-apple-darwin` = 이 작업트리 디버그 빌드 사본 · `src-tauri/resources/{pack.tar.gz(빈 파일), pack-manifest.json("{}")}` · `src-tauri/runtime/` 빈 폴더 · `ui/dist/index.html` 자리표시(앱 시험은 번들 자원을 읽지 않는다 — 없으면 tauri 빌드 스크립트·`generate_context!` 가 컴파일 단계에서 멈춘다).
- 격리 확인: 측정 뒤 격리 HOME 디버그 cysd 잔존 0(`pgrep -fl cys-118-u1/target/debug/cysd` 빈 출력). 표지 뒤 실 `~/.cys`·`~/.local/state/cys` 변경 = 라이브 데몬·다른 좌석 자기 기록(heartbeat·event.seq·schedule_state·다른 워커 TODO)뿐 · 갱신 경로(`~/.cys/update`) 0.
- CLI 실측(격리): `build-info --json` = `{"build_id":"a1af46a2956d-dirty…","release_seq":0,"target":"macos-arm64",…}` rc 0 · `self-update` = rc 2 + 안내 · `self-update --check --json`(피드 없음) = `decision=unreachable` rc 3 · 격리 상태 폴더 쓰기 0개 · `update-verify`(파일 없음) = `undetermined` rc 3.
- §7-1 대조(교체 무관분): 검증 함수 전 항목 · 판 문자열 순서 · 게이트 각 칸 참/거짓·순서·unknown·bulk 48h·holds 만료 · 저널 전이표·write-ahead·복구표 · 실패 분류·백오프 · 출시 빌드 env 무시(키링·피드 URL) · notes_ko · 위임 3조건·토큰 없는 재잠금 · 보류 로그(fsync 전 ACK 0·정확히 한 번·재기동 중복 0) · 저널 사본 2 손상 → Corrupt·재구성 판정 · installed_revoked 3갈래(판정) · boot_id 바뀜 경과 · bulk·publish 적재 거부·이행 true · URL 거부 사례 · 원작자 update_launch 시험(lib 안 그대로). **U2 몫으로 남은 §7-1 항목**: 정비 모드 TTL · V1~V9 · 압축 항목 · 맥 교체 부품 · `run_installer_wait` · RB 실물 재실행 멱등 · B0 시점 · S9b · 신판 전용 경로 삭제 · 작업 정의 재독 · 알림 중복 ≤1 · 강제 종료 행렬 · NSIS ⓪-a · 발행 스크립트 행 누락(U3).
- 뮤테이션 6축(전부 거부/판정 불가 확인): 서명 깨짐(봉투·본문·폐기문 각 1바이트 · rc 2) · 순번 역행(feed_rev·폐기문 rev · rc 2) · 폐기 판(rc 2 `update.revoked`) · 만료(유효창 밖 · 키 만료 · rc 2) · URL 밖(자산·A2 sig url · rc 2 `update.url_refused`) · 시계 의심(rc 3 `update.clock_suspect`).

## §5 함정
- `cargo test` 는 반드시 격리 래퍼로(셸 env 에 실 CYS_PACK_DIR·좌석 토큰). `update::state_dir()` 는 시험 빌드에서 `CYS_UPDATE_STATE_DIR` 없으면 panic(봉인).
- 갱신 시험 중 env 를 바꾸는 시험은 `update::TEST_ENV_LOCK` 으로 직렬화.
- 맥 `ioreg -c IOHIDSystem` 의 HIDIdleTime 줄은 트리 접두(`| |`)가 붙는다 — 줄머리 비교 금지(실측으로 고침).
- 전원 판정에 `pmset -g batt`·`-g ps` 금지(80% 유지 앱 아래 거짓 「배터리 사용 중」) — `-g adapter` + ioreg 용량.
- 새 CLI 동사를 최상위 `Command` 에 넣지 말 것(j3 스택 넘침).

## §6 재현
- ★**다음 판 BACKLOG(적대 3R MINOR · [master#9112a952] 지정 · 코드 0)**: F5 stop_seats 우선 판정 때 후보의 not_in_rollout 사실이 detail 문자열에만(JSON 칸 없음 — U2 「stop_seats 탈출 = 후보 적용」 이 rollout 을 무시할 길) · F6 F·U·위임 키 만료 판정이 `now`(R 만 신뢰 시각) — 비대칭(되감기 창 ≤5분) · F7 trusted/ 세대 정리가 gen-(next−2) 하나뿐 — CURRENT 쓰기와 정리 사이 죽음마다 폴더 1개 누수 · F8/F9 install_id(손상 복구 경로·생성 경합) · F10 `--record --json` 출력 = render_outcome 의 superset(recorded 칸) — 바이트 동일 아님 · F11 u1-mutants.sh 「적 = rc≠0」 이 컴파일 실패(101)도 적으로 셈 → `test result: FAILED` 판정으로. 원문 = `~/axdev/master/reports/cysr-118-plan/REVIEW-U1-fable-3r.md`.
- `git log --oneline 7e7aa5da..HEAD` · `cargo test --lib update::`(격리 래퍼 안) · VERSIONINFO 실측 = 스크래치 크레이트(winresource =0.1.31 · env HOST/TARGET/CARGO_MANIFEST_DIR/CARGO_PKG_* 지정)에서 `write_resource_file` 로 .rc 생성 → `FILEVERSION 1, 1, 8, 0`(기본) vs `1, 1, 8, 42`(set_version_info).

## §7 1R 반영표(2판 · [master#9f66c96f] · [master#113a3975] · 1R 원문 = `~/axdev/master/reports/cysr-118-plan/REVIEW-U1-codex-1r.md`)
적/녹 = `/private/tmp/claude-501/s118/u1/mutants.sh` 실측(11:03–11:06 · 22쌍 전건 「가드 켜면 녹(0) · `CYS_U1_MUTANT=<번호>` 로 가드 끄면 적(101)」). 가드 = `update::mutant("<번호>")`(시험 빌드에서만 켜짐 — `cfg!(test)` 거짓이면 분기째 지워짐).

| 번호 | 처방(1줄) | 가드 · 시험 | 적/녹 |
|---|---|---|---|
| B1 | 출시 빌드 = `CYS_UPDATE_STATE_DIR` 무시 · HOME/LOCALAPPDATA 없음·상대 경로 = Err(`.` 후퇴 0) · CLI 두 호출부 Err = rc 3 | B1 · `buildinfo::b1_release_ignores_env…` | OK |
| B2 | 수용 기록에 봉투 sha256 · 같은 feed_rev 다른 봉투 = replay | B2 · `feed::b2_same_feed_rev…` | OK |
| B3 | R 검증 직후 설치판 폐기·stop_seats·폐기문을 모든 뒤 실패 결과에 · 원문·서명·sha·rev·수용 Stamp 내구 기록 · 30일 대체본 | B3 · `feed::b3_installed_stop_seats…` + `check::b3_revocations_copy…` | OK |
| B3(CLI) | `--record` = 폐기문은 판정과 무관하게 기록 + 신뢰 시각 상향 · uptodate 면 수용 기록(feed seq·설치 seq 분리) · 기록 실패 = rc 3 | B3r · `cli::b3r_record_revocations…` | OK |
| B4 | cysr 에 `--installed-release-seq` = rc 2(내장 seq 만) · agora-client 만 외부 seq | B4 · `cli::b4_cysr_refuses_caller_installed_seq` | OK |
| B5 | cysr 맥 행 cdhash·dr_pin_id 40 hex · 윈 행 a2_sig_url(github 1홉) 필수(ⓖ) | B5 · `feed::b5_second_anchor…` | OK |
| B6 | 묘비 뒤 해제 · ⓪ 인자 = env · ①′ 소유자 기록 이중 읽기 · ③′ pid 시작 시각 | B6 · `lock::b6_arg_must_equal_env` + `lock::b6_handover_race…` | OK |
| B7 | 저널 A/B 슬롯 generation · 최신본 안 덮음 · 한 슬롯 손상 = Degraded(재구성 · 쓰기 거부) | B7 · `journal::b7_post_side_effect…` | OK |
| B8 | 보류 로그 원자 커밋·ACK 재독·crash 행렬 | — | **U2 이관**(기록만) |
| B9 · H③④⑤ · H⑩ | schema 문면 = 아래 §8(설계 §4-1·§6-1 편입 = master) | — | 문서 |
| MAJOR schedule | 루트 객체·jobs 배열·job 객체 필수 · 구조 불명 = None(이행 쓰기 0) | M1 · `sched::m1_structure_damage…` | OK |
| MAJOR SAC · H⑫ | `RegGetValueW` 3갈래 · 값 없음만 absent · 게이트 N12 통과 = off/absent/n/a | M2 · `win::m2_only_file_not_found…` + `gates::each_gate_true_false` | OK |
| MAJOR 권한 | 갱신 폴더 0700 재검증 · 기록 파일 0600 · 윈 보호 DACL(소유자·SYSTEM) | M3 · `lock::m3_private_permissions` | OK(윈 갈래 컴파일 미확인 — 아래 정직) |
| MAJOR 시계 | 맥 `mach_continuous_time` · 모든 응답 Date 대조 | M4 · `clock::m4_every_response_date…` | OK |
| MAJOR install_id | 운영 생성 배선 | — | **U2 이관**(기록만) |
| MAJOR 수용 기록 · H⑪ | 손상 = 쓰지 않음 · feed seq/설치 seq 분리 · `trusted.json` = rev·sha256·수용 Stamp·신뢰 시각 | M6 · `feed::accepted_record_roundtrip…` | OK |
| MAJOR N3 | 읽기 전용 판독도 해시·엄격 단조 | M7 · `hold::m7_readonly_last_seq…` | OK |
| MAJOR 좌석 사실(M8) | `gates::seat_fact_from` — 필수 계기(노드 surface_id·state·idle_secs · 행 human_idle_secs 키·pending_input_bytes·queue_depth) 하나라도 없거나 타입 어긋남 = None → 좌석 사실 전체 None(보류) · cys.rs 가 사용 · 데몬 두 RPC 가 칸을 실제로 낸다(handlers.rs 실측) | M8 · `gates::m8_seat_fact_requires_every_instrument` | OK |
| MAJOR 필수 칸 | build_id·features 전 부품 · cysr bundled_pack{version, digest 64hex} | M9 · `feed::m9_common_required_fields` | OK |
| MINOR SM | breaking = 피드 ⓛ 거부 · 게이트 배열 = 정본 순서 | SM · `feed::sm_breaking_release…` | OK |
| MINOR IDNA | **유지(비 ASCII 호스트 전량 거부)** — 허용 호스트가 전부 ASCII 라 정규화 결과가 목록과 같아지는 경우는 전각·호환 문자 같은 「다르게 보이는 입력」뿐이고, 생산자(U3 `url_ok`)도 비정규형을 거부한다. 정규화 수용은 공격면만 넓힌다 | — | 【결정필요】 ③ |
| MINOR help | `cys --help` 끝 1줄(after_help) · `cys actions` 가 `update::cli::command()` 하위 명령도 싣기(81개 · 실측) | — | 실측 |
| 뮤테이션 공백 | 위 22쌍 | — | OK |
| H① | 위치 유지 + `update::launch_win` 재노출 | — | master 결정 A(설계 §5-1 한 줄 = master) |
| H② | cutover 상수 유지 · 두 발행 레인 빈 값 거부 핀 | — | U3 몫(master 추가) |
| H⑥ | 잠금 파일 ↔ 소유자 기록 분리는 유지(윈 LockFileEx 가 잠긴 범위 읽기를 막음) · 결박은 B6 의 ⓪·①′·③′ 로 | B6 | OK(구조 결박이 아니라 검증 결박 — 정직) |
| H⑦ | generation + 손상 = 재구성(B7) · 새 상태명(DONE·DEFERRED·PACK_DONE) 정본 전이표 편입 | B7 | 편입 = master(설계) |
| H⑧ | 별도 파서 유지 + 정적 도움말 | — | 위 MINOR help |
| H⑨ | 부품별 인자 권한(B4) · record 실패 rc 3(B3r) · `--enumerate-installed` 는 `--installed-release-seq`·`--record` 와 배타 | B4 · B3r | OK |
| H⑬ | features 빈 목록 = U2/U4 전 미완료 표지 유지 | — | U2/U4 |

**U3 1R 에서 넘어온 4(2판 포함 · [master#113a3975])**

| 번호 | 처방 | 가드 · 시험 | 적/녹 |
|---|---|---|---|
| ⑴ payload_manifest | `Asset.payload_manifest: [{path, size, sha256}]` — cysr 윈 행 **필수**(부재·빈 목록 = ⓖ 거부) · 경로 = 상대(`/` 시작·`\`·`:`·제어문자·빈/`.`/`..` 성분 거부) · sha256 소문자 64 hex · 대소문자 무시 중복 거부 · 다른 행에 실렸으면 같은 검사 · 검증 반환 JSON `asset` 에 그대로 | PM · `feed::pm_payload_manifest_required_on_windows_rows` | OK |
| ⑵ URL 벡터 공유 | 행 URL 규칙을 `feed::row_url_check(component, field, url)` 하나로(ⓖ a2_sig·ⓜ 자산·a2_sig 모두) — U3 `update_common.url_ok_for` 와 1:1(cysr = github 1홉 · agora-client 자산 = 사이트 · a2_sig = cysr 만) · 시험이 `scripts/update/url-vectors.json` 을 `include_str!` 로 읽음 — U3 가지 ca4c7b6a 의 **같은 바이트 사본**(sha256 `a419b604…`) · U3 머지 때 같은 경로라 충돌 0 · 갈리면 시험 적색 | `feed::url_vectors_shared_with_u3_publisher` | 녹 |
| ⑶ R signed_at 미래 | `verify_revocations(…, now, last_trusted)` — `signed_at > max(now, 신뢰 시각)` = `update.feed_expired`(ⓐ) · `FeedInput.last_trusted_time` 칸 추가(check·cli 가 `trusted.json` 값을 넘김) | RF · `keys::rf_future_signed_revocations_rejected` | OK |
| ⑷ 출발 seq 열거 | `feed::verify_feed_enumerate(inp) -> Result<Enumerated, FeedOutcome>` — 서명 단계(ⓐ~ⓘ) 1회 + 판정(ⓙ~ⓝ)을 `max(min_from,1)..=release_seq` 각각(같은 함수 — 단일 판정과 바이트 같은 JSON 실측) · `inp.installed_release_seq` 안 씀 · CLI = `cys update-verify … --enumerate-installed --json` → `{mode:"enumerate", verdict: ok|reject|undetermined, release_seq, min_from_release_seq, problems[], results[{installed_release_seq, …판정}]}` · rc = 가장 나쁜 것(3 > 2 > 0) · 허용 출발 seq 없음·후보 자신이 uptodate 아님 = 2 · `--installed-release-seq`·`--record` 동반 = 2 · 쓰기 0 | `feed::enumerate_judges_each_allowed_start_seq` · `cli::enumerate_installed_cli_rc` | 녹 |

★**U3 에 넘길 것(교차 영향 · master 전달)**: B4 로 **cysr 에 `--installed-release-seq` 를 주면 이제 rc 2** 다. U3 `release-gate.py _run_verify` 는 cysr 에도 그 인자를 늘 붙이므로(ca4c7b6a 기준) U1 머지 뒤 cysr 레인이 전부 거부로 바뀐다 → U3 는 `--installed-release-seq` 미지정 경로를 `--enumerate-installed` 1회 호출로 바꾸고(명시값 경로는 agora-client 만), `ROW_FIELDS_PENDING_U1 = ("payload_manifest",)` 를 비워 행 전체 대조에 넣으면 된다.

## §8 부록 — 피드·폐기문·키링 schema 문면(B9 · H③④⑤ · H⑩ · 설계 §4-1·§6-1 편입 재료 · 코드 = 정본)
모든 정수 시각 = Unix 초(i64). 「필수」 = 칸 부재·형식 위반 = 거부. 서명 = minisign(서명 대상 = 파일 바이트 전체 · 검증 = `packsig::verify_minisign`).

**폐기문 `revocations.json`**(R 서명 · 내장 R 키만 · 위임 불가)
```
{ "kind": "update-revocations",                 필수 · 고정(교차 사용 차단)
  "rev": u64,                                    필수 · 수용 rev 미만 = update.feed_replay
  "key_id": "<16 hex 대문자>",                    필수 · 내장 키링의 purpose=root 키
  "signed_at": i64,                              필수 · > max(now, 신뢰 시각) = update.feed_expired(ⓐ · 2판) · R 키 만료도 같은 기준(3판 N5)
  "delegations": [                               선택(기본 [])
     { "key_id": "<16 hex>",                     = pubkey_key_id(pubkey) 이어야 함
       "purpose": "release" | "feed" | "win-asset",   root·pack = 거부
       "pubkey": "<base64>",                     아래 「공개키 인코딩」
       "not_after": i64 } ],                     ★키링(RFC3339 문자열)과 달리 정수 초
  "revoked_key_ids": ["<16 hex>"],               선택
  "revoked_releases": [                          선택
     { "component": "cysr" | "agora-client",     필수(seq 는 부품별 번호 — cysr 7 ≠ agora 7)
       "release_seq": u64,                       필수
       "severity": "advisory" | "stop_seats",    선택 · 부재 = advisory · 미지 값 = advisory + unknown_severity 신호
       "reason_code": "<str>" } ],               선택
  "dr_pins": { "add": ["<40 hex>"], "revoke": ["<40 hex>"] } }   선택
```

**봉투 `<component>/<channel>.json`**(F 서명)
```
{ "kind": "component-update-feed", "component": "cysr"|"agora-client", "channel": "stable"|"next",
  "feed_rev": u64(단조 · 같은 rev = 봉투 sha256 같을 때만), "key_id": F, "signed_at": i64, "expires_at": i64(≤ signed_at + 14일),
  "rollout_pct": 0..100, "halt": bool,
  "release": base64(본문 파일 바이트), "release_sig": base64(본문 .minisig 파일 바이트),
  "prev_release"?: base64, "prev_release_sig"?: base64 }
```

**릴리스 본문**(U 서명)
```
{ "kind": "component-release", "component", "release_seq": ≥1, "version": 비지 않음, "key_id": U, "signed_at": i64,
  "min_from_release_seq": u64(★3판 N3: 값 < release_seq 필수 = ⓖ · 열거 출발 = max(값,1) · 열거 폭 ≤ 256),
  "requires": { cysr: "min_binary_for_pack" = semver 필수 · agora-client: "min_cysr_release_seq" = u64 + "python" 비지 않음 ·
                모든 값 null·빈 문자열 = 거부 },
  "state_migration": "none"|"additive"|"breaking"(breaking = ⓛ 거부 · 링크 재설치 전용),
  "assets": { "<target>": 행 } 비지 않음(target ∈ macos-arm64·macos-x64·windows-x64·any · ★3판 B5: cysr 은 any 금지),
  "notes_ko": ≤80자 · 제어문자 0 · 금지 어휘(오류·실패·위험·손상·경고) 0 }
```
행: `url`(부품별 홉 규칙 · §7 ⑵) · `size`>0 · `sha256`(소문자 64 hex) · `max_unpacked`>0 · `target`(= 키) · `build_id`(비지 않음) · `release_seq`(= 본문) · `features`(배열 · 칸 필수 · 빈 배열 허용) · cysr: `bundled_pack{version 비지 않음, digest 소문자 64 hex}` 필수 · cysr 맥: `cdhash`(40 hex) · `dr_pin_id`(인증서 leaf sha1 40 hex) 필수 · cysr 윈: `a2_sig_url`(github 1홉) · `payload_manifest[{path, size, sha256}]` 필수.

**키링 `cysjavis-pack/trusted-keys.json`**(바이너리 내장 · TOFU 0)
```
{ "keys": [ { "key_id": "<16 hex 대문자>", "pubkey": "<base64>", "not_after": "<RFC3339>",
              "purpose": "root"|"release"|"feed"|"win-asset"|"pack" } ],   purpose 부재 = pack(하위 호환) · 미지 값 = 키링 오류
  "revoked_key_ids": [] }
```
**공개키 인코딩 · key_id 산식**(`packsig::pubkey_key_id`): `pubkey` = minisign 공개키 **raw 키라인**(2바이트 알고리즘 `Ed` + 8바이트 keynum + 32바이트 공개키 = 42바이트)의 base64, 또는 `.pub` 파일 **전체 텍스트**의 base64(주석 줄 뒤 마지막 키라인을 읽는다). `key_id` = keynum 8바이트를 **리틀엔디언으로 뒤집어** 대문자 16진 16자(minisign `{:016X}` 표기와 같음).

**오류코드 매핑(H⑩ · 고정 사전 §3-12 안에서 · 단계는 `step` 칸)**
| 단계 | 실패 | 코드 | rc |
|---|---|---|---|
| input | 파일 읽기·상태 폴더 못 정함·키링 | `update.verify_failed` | 3 |
| input | cysr 외부 seq · 열거 모드 배타 위반 | `update.verify_failed` | 2 |
| ⓐ | 폐기문 서식·kind·R 키·서명·위임 | `update.feed_sig_bad` | 2 |
| ⓐ | rev 후퇴 | `update.feed_replay` | 2 |
| ⓐ | signed_at 미래(2판) | `update.feed_expired` | 2 |
| ⓑⓒⓓ | 봉투 서식·F 키·서명 | `update.feed_sig_bad` | 2 |
| ⓔ | 시계 의심 | `update.clock_suspect` | 3 |
| ⓔ | 유효창 밖 | `update.feed_expired` | 2 |
| ⓕ | feed_rev 후퇴·같은 rev 다른 봉투 | `update.feed_replay` | 2 |
| ⓕ | 수용 기록 손상 | `update.verify_failed` | 3 |
| ⓖⓗⓘ | 본문 서식·필수 칸·U 키·서명 | `update.release_sig_bad` | 2 |
| ⓙ | 후보 폐기 | `update.revoked` | 2 |
| ⓚ | 후보 ≤ 설치(판정) · 설치판 폐기 | `update.ok` · `update.installed_revoked` | 0 |
| ⓛ | 출발 판 하한·breaking·requires(cysr min_binary = `update.pack_min_binary_empty`) | `update.verify_failed` | 2 |
| ⓜ | 기판 행 없음 · URL 규칙 밖 | `update.verify_failed` · `update.url_refused` | 2 |
| ⓝ | apply·halt·not_in_rollout(표시) | `update.ok` | 0 |
| `--record` | 기록 실패(2판) | 판정 코드 유지 + `record_error` 칸 | 3 |

## §9 2R 반영표(3판 · [master#2dc1891f] · 2R 원문 = `~/axdev/master/reports/cysr-118-plan/REVIEW-U1-codex-2r.md`)
증명 도구 = **저장소 안** `scripts/tests/u1-mutants.sh`(`U1_ISO=<격리 래퍼>` · ① 가드 29쌍(SEQ1 포함) + ② 실제 소스 변이 patch 4 = `scripts/tests/u1-mutants/*.patch` 를 `git apply` → 시험 적색 → `git apply -R`) · 실측 11:53–11:57 32/32 · bbff9184 뒤 12:18–12:23 **33/33 OK**(녹 0 · 적 101) · 되돌림 뒤 작업트리 깨끗.

| 2R 번호 | 처방(구현) | 증명 | 결과 |
|---|---|---|---|
| B5 · N7 | cysr 본문 `any` 행 = ⓖ 거부 · 기판별 둘째 닻+페이로드 검사를 `check_row_anchors(component, key, row)` 하나로 — ⓖ(행 키 기준)와 ⓜ(**실제 `inp.target` 기준**) 두 곳에서 같은 함수 | patch `b5-any` · `feed::b5_cysr_any_row_rejected` | OK |
| B6 · H⑥ | 위임 자식 잠금 `txn.child.lock` — `verify_delegated` 가 `DelegatedGuard`(자식 잠금 쥠)를 돌려줌 · `acquire` 는 새 소유자 기록을 **먼저** 쓰고 자식 잠금을 확인 → 쥐어져 있으면 직전 기록 복원 + `txn_busy`(부모가 죽어 `txn.lock` 이 풀려도 잠금 세대 유지) · 자식은 한 번에 하나 · 검증 실패 = 자식 잠금 즉시 놓음 | 가드 B6g · `lock::b6g_delegated_guard_holds_generation_after_parent_death` | OK |
| B7 · H⑦ | generation ≥2 단일 슬롯(상대 슬롯 **부재**) = `Degraded` → `Reconstruct`(generation 1 단일 = 정상) | patch `b7-single-slot` · `journal::b7_single_slot_with_missing_peer_is_degraded` | OK |
| N4 | 설치판 `stop_seats` 폐기 = `installed_revoked` **우선 판정**(apply·halt·not_in_rollout·uptodate 위 · 후보 행·판 정보 유지) · `check::decide` = `stop_seats` 강제 결정(거부·판정 불가여도 · apply/hold 로 접지 않음) · advisory 폐기 + 더 새 후보 = apply 유지 | 가드 N4 · `feed::revoked_releases_and_installed_revoked`(기대치 수정) · 가드 N4c · `check::n4c_stop_seats_is_forced_decision` | OK |
| N5 | R 키 만료 = `trusted_now = max(now, last_trusted)` 기준(signed_at 미래 거부와 같은 기준) · 시계 의심(ⓔ · CLI = `clock_suspect(now, last_trusted)`) `--record` = 폐기문 원문은 기록 · 신뢰 시각 상향 0(`record_revocations(.., bump_trust=false)` + `bump_trusted` 생략) | 가드 N5 · `keys::n5_r_key_expiry_uses_trusted_time` · 가드 N5r · `check::n5r_suspect_record_keeps_trusted_time` | OK |
| M3 | 기존 잠금·보류 파일 = `check_private_file`(유닉스 = 일반 파일 · uid 나 · 그룹·기타 비트 0 · 아니면 Err = 판정 불가 — 보류 로그 읽기 전용 판독은 None) · 윈 = `CreateDirectoryW` + `SECURITY_ATTRIBUTES` 보호 DACL(생성 시 · 사후 적용 삭제) · 폴더·파일 DACL read-back(`GetFileSecurityW` → SDDL → `dacl_is_private`: ACE 전부 「허용·FA·OW/SY」 + 보호 또는 전부 상속) · `install_id` 도 0600(`write_private`) | 가드 M3 · `lock::m3_existing_wide_lock_file_rejected` · `mod::dacl_private_rule`(순수 판정) | OK |
| M4 | `fetch_and_verify_with(.., get)` — 네 요청 **각각** 성공 응답 Date 누적(짝 실패·미도달과 무관 · 미도달이어도 dates 반환 → N13 재료) | patch `m4-partial-fetch` · `check::m4_partial_fetch_keeps_every_success_date` | OK |
| M5 | `run_check` 진입 = `ensure_install_id`(없으면 원자 생성 · 손상 = `undetermined` rc 3 · 피드 받기 전) · 버킷은 그 id 로 | `check::m5_corrupt_install_id_is_undetermined` | 녹 |
| N2 | 공통 직렬화 `feed::render_outcome`(단일 `--json` 출력 = 이것) · 열거 행 = `render_enum_row` = `{"installed_release_seq":N,"outcome":<render_outcome 바이트 그대로>}`(출발 seq = 바깥 칸) · 시험 = **문자열 바이트** 포함 비교 | patch `enum-json` · `cli::n2_enumerate_rows_are_single_verdict_bytes` · `feed::enumerate_judges…`(render 바이트 비교로 수정) | OK |
| N3 | 본문 `min_from_release_seq < release_seq` 필수(ⓖ) · 열거 폭 상한 `ENUMERATE_MAX = 256`(초과 = `undetermined` rc 3 · step `enumerate`) · 256 = 허용 | `feed::n3_min_from_bound_and_enumerate_width_cap` | 녹(음성 2) |
| N6 | 신뢰 기록 = `trusted/gen-<N>/` 세 파일 + `trusted/CURRENT` 원자 교체(폴더 fsync 두 번) · 중간 죽음 = 고아 세대(안 읽힘 · 다음 커밋이 치움) · 포인터가 없는 세대 = 손상(Err) · 두 세대 전 정리 · 신뢰 시각만 바뀐 세대도 원문 동반 | `check::n6_trusted_generation_commit_is_atomic` | 녹 |
| B9(코드) | 폐기 항목 `component` ∈ {cysr, agora-client} · `dr_pins.add/revoke` = 소문자 40 hex(아니면 `feed_sig_bad` ⓐ) · golden 왕복 = `src/update/testdata/golden-revocations.json`(§8 문면 그대로 · 자리표시 = 시험 키)이 서명·검증 뒤 모든 칸 그 값 | `keys::b9_revocation_field_domains` · `keys::b9_golden_revocations_roundtrip` | 녹 |
| M10 · N8 | 위 스크립트 저장소 편입 + 소스 변이 patch 4 | — | 32/32 |
| N9 | 로컬 윈 타입체크 = `scripts/win-typecheck.sh`(x86_64-pc-windows-msvc · cys lib normal+test 포함) **오류 0**(11:57–12:00 · `src/update` 경고 0) — 윈 러너 `cargo test --lib update::` = master push 뒤 ci-branch(머지 조건) | 실측 | 타입체크 통과 · 러너 = master |
| SEQ1(추가 · [master#450449c8] · U3 Fable 3R MAJOR-2) | 첫 판(release_seq 1 · min_from 0 → 허용 출발 seq 없음) = 열거 「후보 uptodate 1행」 이면 통과(rc 0 · verdict ok) · 단일 판정(설치 1) = 같은 uptodate · 같은 바이트 · seq ≥2 는 종전(min_from ≥ seq = ⓖ 거부) | 가드 SEQ1 · `cli::seq1_first_release_enumerates_as_single_uptodate_row` | §4 |
| B8 · H⑬ · N1 | B8 = U2(머지 게이트) · H⑬ = U4 뒤 발행 게이트 · N1 = U3 3판 | — | 이관(master 지시) |
| IDNA | 비 ASCII 전량 거부 유지(master 채택 · 설계 문면 「ASCII authority 만」 = master 편입) | — | 결정됨 |

**계약 변화(다른 티켓이 알아야 할 것)**: ① 열거 JSON 행 모양 = `results[{installed_release_seq, outcome:{…}}]`(2판 `results[{installed_release_seq, …판정 칸}]` 에서 바뀜 — U3 release-gate 열거 분기는 `outcome` 아래를 읽을 것) ② `--check` 결정에 `stop_seats` 추가 ③ cysr 본문 any 행 금지 · min_from < release_seq(U3 발행 게이트 `0 ≤ min_from < seq` 와 같음) ④ 신뢰 기록 파일 배치(`trusted/…`) — U2 가 읽는다면 `check::read_trusted`·`trusted_current_dir` 로 ⑤ 첫 판 seq 1 봉투 = 열거 uptodate 1행 통과(U3 `u1verify.py` 는 294 가 같은 규칙).

## §9-2 3R 반영표(4판 · [master#9112a952] · 3R 원문 = `~/axdev/master/reports/cysr-118-plan/REVIEW-U1-fable-3r.md` · 수렴 예 · BLOCK 0)
| 3R 번호 | 처방(구현) | 증명 | 결과 |
|---|---|---|---|
| F1(MAJOR) | `check::with_trusted_lock` — `trusted/.lock`(0600 · 기존 파일 재검증) 배타 잠금(차단 대기) 안에서 `record_revocations`·`bump_trusted` 의 읽기 → 세대 번호 → `commit_trusted` 전부 · 동시 두 주체(러너·T3)에도 CURRENT 늘 실재 세대 · rev·신뢰 시각 후퇴(늦은 쓰기 덮음) 0 | 가드 F1 · `check::f1_trusted_lock_excludes_second_writer`(결정론 — 잠금 쥔 동안 둘째 커밋은 해제 뒤에야 끝남) + 부하 시험 `check::f1_concurrent_trusted_commits_keep_current_valid`(4스레드 × 15회 · 경합 확률적이라 뮤테이션 목록 밖 — 첫 실행에서 가드 끈 채 녹 1회 관측 → 결정론 시험으로 교체) | OK |
| F2(MAJOR) | `verify_feed_enumerate` — `lo == release_seq`(첫 판)이면 설치 0 탐침 `judge(.., 0)` 1건으로 ⓛ requires·ⓜ 자산/a2 URL 평가 · 거부·판정 불가면 열거 전체 = 그 결과(판정 행은 uptodate 유지) | 가드 F2 · `cli::f2_first_release_still_checks_requires_and_urls`(URL 밖 = url_refused rc 2 · min_binary 빈 값 = ⓛ rc 2) | OK |
| F3(MAJOR · 게이트) | `.github/workflows/windows-health.yml` — `update_launch::` 다음에 `cargo_filter_count --lib update::` + `cargo test --lib update:: -- --test-threads=1`(0매치·실패 = 적색 · `if:` 없음) · 필터 실측 = 126건(4판) 전부 `update::` 하위(`update_launch::` 와 안 겹침) · YAML 파싱 확인 | 윈 러너 = master push 뒤 | 워크플로 커밋 |
| F4(MINOR) | `acquire` 거절 분기 하나로 — 자식 잠금 파일 열기 실패(권한 불일치 등)도 직전 소유자 기록 복원 + 잠금 놓음 | `lock::f4_child_lock_open_failure_restores_owner` | 녹 |
| F5~F11 | 다음 판 BACKLOG(§6 1줄) | — | 지시대로 0 |
| F12 | 정본 편입 = master | — | — |

