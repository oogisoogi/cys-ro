# HANDOFF-U1 — 1.1.8 데몬 자동 갱신 U1(피드·검증·판정·공용 모듈) · TICKET=cysr-118-u1-autoupdate

- 좌석 = worker surface:1290(291 118u1) · 계정2 · Opus · 가지 `u1/autoupdate-118`(off `7e7aa5da` = 1.1.8 병합 완료판) · **push 0**
- 브리프 = [master#2b976211] 2026-10-06 08:11 · 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md` 4판
- 이 문서의 시각·수는 전부 도구 출력(git 커밋 시각 · `date` · 시험 결과 줄)에서 옮겼다.

## §0 델타(다음 사람이 먼저 읽을 것)
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
- ⑧ CLI 3동사 **배치**: 최상위 `Command` 가 아니라 `main` 의 `Cli::parse()` 앞 별도 파서(`update::cli::dispatch`) — 최상위 clap 열거형을 늘리면 j3 시험 스택 넘침(1.1.8 W1 실측). 철자는 설계 그대로. 대가 = `cys --help`·`cys actions` 목록에 안 보인다.
- ⑨ `update-verify` 보충 인자 `--installed-release-seq`(agora-client 필수) · `--target` · `--record`(서명 전부 통과 때만 단조 앵커 = 폐기문 rev·신뢰 시각 상향 · uptodate 면 수용 기록 feed_rev — §6-3) · 디버그 빌드 전용 `CYS_UPDATE_NOW`.
- ⑩ 오류코드 매핑(사전에 「서식 오류」 낱말이 없음): 봉투 계층 서식·키·서명 = `feed_sig_bad` · 본문 계층 = `release_sig_bad` · ⓛⓜ 계약 위반 = `verify_failed`(URL = `url_refused` · cysr `requires.min_binary_for_pack` = `pack_min_binary_empty`) — 단계는 `step` 칸(ⓐ~ⓝ).
- ⑪ 상태 폴더 작은 기록의 이름·서식 = `config.json{auto, channel}`(N9 · 부재 = auto ON · stable) · `holds.json{holds[{until,reason}]}` · `state.json{last_success, failures}` · `trusted.json{revocations_rev, last_trusted_time}` · `hold-cursor.json{delivered_hold_seq}` — 설계는 `state.json`·`holds.json` 이름만 줬다.
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
- `git log --oneline 7e7aa5da..HEAD` · `cargo test --lib update::`(격리 래퍼 안) · VERSIONINFO 실측 = 스크래치 크레이트(winresource =0.1.31 · env HOST/TARGET/CARGO_MANIFEST_DIR/CARGO_PKG_* 지정)에서 `write_resource_file` 로 .rc 생성 → `FILEVERSION 1, 1, 8, 0`(기본) vs `1, 1, 8, 42`(set_version_info).
