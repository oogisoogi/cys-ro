# MERGE-0.14.44-48-PLAN — 원작자 v0.14.44~v0.14.48 편입 판정표 (1.1.10 · 1단계)

> TICKET=cysr-1110-upstream · 가지 int/1110-upstream @4f660dfb · 작성 worker-3(surface:1316) · 2026-10-10 · 정책 = `master/CYS-UPDATE-POLICY.md` §0·§0-1·§0-2
> 판정 기호: ⓐ 그대로 받음 · ⓑ 우리 유지(원작자 버림) · ⓒ 융합 · ⓓ 보안 경계 리뷰 · ⓔ 제외 후보(박사님 게이트). 덩어리별 원표 = 부록 `MERGE-0.14.44-48-HUNKS.md`.
> 표식: 【관측】 = 도구 출력 · 【추정】 = 판독만(미실행). 1단계에서 컴파일·시험은 **한 번도 돌리지 않았다** — 전부 merge-tree·3자 재현·소스 판독이다.

## 0. 실측 기준 【관측】

| 항목 | 값 | 출처 |
|---|---|---|
| 공통 조상 | v0.14.43 = 55d3d2d6 (`UPSTREAM_BASE` 와 일치) | `git merge-base HEAD v0.14.48` |
| 원작자 범위 | v0.14.43..v0.14.48 = **139 커밋**(44→44 · 45→44 · 46→5 · 47→4 · 48→42) · **85 파일**(신규 39) · +22,893/−808 | `git rev-list --count` · `git diff --shortstat` |
| 겹침 | 우리(v0.14.43..HEAD 1,313 커밋)와 함께 바꾼 파일 **44** (브리프 40 + 47·48 로 4: windows-build.yml · javis_phoenix.py · javis_state_snapshot.py · schedule.rs) | `comm -12` |
| 충돌 | `git merge-tree HEAD v0.14.48` = **28 파일 · 66 덩어리**(v0.14.44 만 20 · 46 까지 26) | merge-tree · 덩어리 수 = `^<<<<<<<` 계수 |
| 이미 우리에게 있음 | 8b8d7505·ea06f6bb(capgate 대체 출력) — patch-id 동일 | `git cherry HEAD v0.14.48` |
| 우리 자동 갱신 | `scripts/update/*` · `src/update/*` = 원작자 43..48 **무접촉**(diff 0줄) — 1.1.8 U4(인앱 updater 삭제)·우리 갱신 체계는 이번 편입의 충돌 대상이 아니다 | `git diff v0.14.43 v0.14.48 -- scripts/update src/update \| wc -l` = 0 |

**병합 방식 권고 = `git merge --no-ff v0.14.48` 한 번**(1.1.8 선례 c08489e7). 44→46→48 순차는 겹침 파일을 세 번 해소하고 중간 판(45·46)이 각자 녹이어야 해 비용만 늘고 얻는 것이 없다(46·47·48 은 덧붙임 위주). 병합 커밋 = 충돌 해소 + **컴파일·계수 핀 수리까지**(그래야 첫 커밋부터 녹) · 그 뒤 묶음별 적응 커밋.

## 1. 묶음별 판정 (139 커밋 전건 — 머지 커밋 8 포함)

| # | 묶음 | 커밋 | 판정 | 줄 |
|---|---|---|---|---|
| B1 | 승인 A1~A5 — 미승인 사유 6코드 · 서명이 command_text 를 같은 토크나이저로 · 대상 동사 7종 시간 한정 승인을 서명 데몬에 묶음(approval_cwd_neutral) · 상태 파일 원자 쓰기 | 30adb62e 0a0c6280 7f0ff67c 6726406e 87de86dd 62f040bb ce76b43f 90f28cdc | **ⓒ+ⓓ** | 토크나이저 본문이 lib `cys::approval_tokenize` 로 이동 — 원작자 재공개 채택 + 우리 golden 시험(⑲ `golden_tokenize_table_is_frozen`) 유지 · 녹이면 동치 확정, 적이면 ⑲ 본문을 lib 로 이식 |
| B2 | 승인 Feed C1~C3 — 닫힌 좌석 daemon- 승인 stale-cleared 쓸기 · waiter/publisher_alive · 부서 항목 같은 화면 · 정보성 확인 | e0c26eb2 77b1c118 634327a2 0427b6c7 7fae8e87 | **ⓒ+ⓓ** | UI: C2 두 분기·C3 채택, team-create 카드만 버림(D-TEAM 휴면 = 1.1.8 결정①). 데몬: 우리 `expire_orphan_feed`(이전 세대·요청자 사망 전부 만료)와 원작자 쓸기(닫힌 좌석 daemon- 만) **공존** — 정책 차이 📌3. 토큰 폴더 = 원작자 `operator_token_dir_for` 채택 + 우리 `daemon_state_dir_for` 위임 래퍼(두 계산 줄 단위 동일 대조) |
| B3 | 오피스 브리지 B1~B7 — 본부 데몬만 띄움 · 수명줄 · 건강 확인 감독(30분 3회) · 옛 브리지 교체 · office-boot.js 재시도·배너 · 앱 office_health/repair_office_assets · pack-heal --missing-only | 0b5cd8e1 db343970 0573ed90 8ce644e6 8a2c8710 a7c3ed1c 0ff1a7e7 5bdc456f 94c23e29 df701d8e bc4ca568 2e6c3698 68e27065 80ec7164 1b09395e | **ⓒ+ⓓ** | main.rs: 우리 윈 Job 결박 먼저 + 원작자 재기동 상한(원작자 office_bridge.rs 에 Job 0 → 버리면 윈 고아 브리지 재발). office-boot.js = ⓐ(원작자판 바이트 동일 · 우리 쪽은 개명뿐). 새 tauri 명령 3(feed_list_all·office_health·repair_office_assets) 자동 등재 · 오피스 iframe IPC 불가 유지 |
| B4 | 사용량 칸 D1/D2(보기 방식·제공자 묶음·상자별 리셋) + 46 「사용처:」 줄 제거 | 747da25d a40ebec9 97dc1802 f9858db0 6845f9ff b0a3c08a | **ⓑ(ⓔ 승계)** | 원작자 U1 사이드바 패널 위의 기능 — 우리는 U1 미수용·`wsusage.ts` 패널 절대(1.1.8 원장 #82). 받을 자리가 없다. 새 결정 아님(📌4 로 확인만) |
| B5 | 좌석 자손 세기 보정(pid 재사용 · 윈 전용 · 경보·중복·닫기 목록) | 61a94aa6 b7e754d7 e0250a83 | **ⓐ** | 충돌 = 시험 모듈 인접 추가뿐 · 우리 빈 좌석 가드 소스 핀과 무충돌 |
| B6 | agy — 윈 안내 문구(D3) · 윈 상태줄 자동 연결(.cmd + 쓰기 전 실연 검사) · 8.3 경로 | b02a4ca1 4e00d198 3a728d10 a754f0de b9151464 42daf7bb 39c477cf | **ⓒ+ⓓ** | 사용자 agy 설정 파일 쓰기(윈). accounts.rs 의 agy 귀속은 우리 휴면 스위치 유지(ⓑ) · 설명서 문면은 원작자 것을 cysr 로. lib `RAW_COMMAND_NEW_FROZEN` 에 `("src/agy_statusline.rs", 2)` 등재 필수 |
| B7 | vt100 0.15.2 벤더링 + 한글 폭 패닉 수리 + 흐림(SGR 2) | 1f6d899c 1e758593 ffa95a52 4f48c9a4 | **ⓐ** | `vendor/vt100/` 통째 + NOTICE 1행(우리 원문 복원 줄 무접촉) · 워크스페이스 exclude |
| B8 | 윈 claude 좌석 classic 고정(`claude_tui.rs` · settings.json `tui:"default"` · 원장·되돌림·doctor·완전 초기화) + settings_surgery 분리 + 휠 첫 억제 토스트 | d2c6c405 58d5c8e2 021a7f8a 1065d990 3a3ce219 3c02bfeb addf1b9b 8c7508dd 1f84793a 88fc80e9(격리 백업·링크 폴더 되돌림 거부·원장 잠금 = B8 · 반향 창 바닥 3초 = B9) | **ⓒ+ⓓ** | §2-(ii). Rust 쪽 ⓐ(cys.rs 기동 배선 = 우리 3줄 뒤) · UI 토스트·핸들러 = ⓑ(우리 altscroll 유지) — 📌1 |
| B9 | 큐 막힘 화면 재동기(높이 1줄 흔들기 · 반향 창 · stale_screen 14번째) + 0.14.47 screen_diag 키 4 | 4ef58353 769b4d9a 0b183994 e0c7bdda 87e4fa80 d11cbb65 531d7b3d 61e5eda6 4aabf4ad 61536014 c68c67f7(문서분) 5a9f7be8 e869349d(codex 2차 — 크기 관문·파서 패닉·선택기 행·시계 = B9 · 미루기 표식·정리 상한 = B6) | **ⓒ** | state/handlers 충돌 = 같은 락·같은 json 안 인접 추가 → 둘 다. rate_limited 식 표 안 리터럴·D-U3 출처 창 무접촉 |
| B10 | 좌석별 계정 account 키(surface.list·org.status) + 부서 카드 계정 줄 + 불신 기록 폴더·pending·불일치 | 86e043fc 11a9d4ca 19ccaec5 63dbc041 3dbca876 0ca5849c 66b29c91 6af49ab0 | **ⓒ** | §2-(i) |
| B11 | 0.14.48 A — phoenix 인코딩(utf-8 open 18 · stdout 재설정 · 하위 출력 바이트 디코딩 · manifest · manual_restore.sh LF) | 21cf532b 2b2fde84 9bc3001c 2d40f1df 780c40f2 4a7f6459 9a2d17d6 bee1c7c9 00ade0a8 f650373e d8a2dff5 121ab280 | **ⓒ** | 우리 1.1.9 수리(`_restore_config_dir`·`_validate_profile_dir`·fresh_expected 순서·"unobserved") 생존 확인. **함정 2**: 원작자 `_run_decoded` 가 `**NOWIN` 을 빠뜨림(헬퍼 안에만 넣는다 · creationflags 핀 1회) · 우리 `_ps_table` 의 `text=True` → `_run_decoded` 로(원작자 새 시험이 0곳 요구) |
| B12 | 0.14.48 D — 기다리면 풀리는 큐 경보 3종 = 회색 「대기 중」·구간당 1회 팝업(F1·F1-R·F1-T) | df00a25d 52393b3b 2e6d1205 c562d389 b19a9782 bb2e0acc 86efae67 7bcf1773 bfad3717 75d87c66 6c2f66d0 ce17460a 7c45c8cf | **ⓐ** | starvednotice 자동 병합 · 우리 seat_unknown·seat_no_agent 도 wait 쪽(의도 부합) · split 시험은 governance 문장 핀이라 cysd 해소 뒤 확인 |
| B13 | 0.14.48 B — 은퇴 시드 text_command = 승인 없음 확인 시만 건너뜀 + `schedule list note=` | afbe568b cd53400b 04d03410 216a3b16 4b3fd748 b592f87a 77143445 bf56ca64 ef0566f5 | **ⓐ+ⓓ** | 자동 병합 · 원작자 승인 저장소 경로 = 우리 approval.rs 와 일치 · BOM 파일은 종전 거부(안전 방향) |
| B14 | 판 번호 올림 ×5 | eab93e7d 3a80859d 668a77e1 1a3a9dda + c68c67f7(판번분) | **ⓑ** | 우리 1.1.8 유지(4곳·wxs 2 실측) · 1.1.10 올림 = 별도(통합 리드) |
| B15 | 릴리스 노트·설명서·RELEASE.md | fa9a4c97 4544eb3f 42d098cd 06ad0a06 30ae1340 cc3448d1 27a04038 0d09a361 320c7359 96268f46 ad9b0f90 2c3ffa25(검체 윈 더미 경로 = secret-scan 허용 꼴) | **ⓒ** | RELEASE_NOTES_0.14.44~48 = ⓐ(이력 보관 · 0.14.43 까지 선례). USER-MANUAL = 전 파일 cys→cysr·업데이트→갱신 패스(병합 시 맨 cys 49줄 유입 · 27줄은 충돌 밖 자동 병합) · `CYS_UPDATE_*` 행·「업데이트를 눌렀는데」 행 부활 금지 · 검사 = `bun test publicdocs` |
| B16 | CI 등재 | 16a312c7(우리 1f28503b 로 선반영) + 위 a754f0de·1f84793a·121ab280 | **ⓒ** | 구조만: 팩 시험 4종 × 5 루프 = 20 토큰 · windows-health 에 `agy_statusline::`·`claude_tui::` 필터(ci-branch 필수 표가 자동 병합으로 요구) · windows-build T5b · 우리 레인·U5 단계·시크릿 유지 |
| B17 | 이미 우리에게 있음 | 8b8d7505 ea06f6bb | ⓐ(무동작) | patch-id 동일 |
| — | 원작자 머지 커밋 | 2fefa58c 374dde2b 5bb7abc6 759118ed 55f73d81 46504761 8eadd82b + 0.14.47 판번 c68c67f7 | 해당 없음 | 내용은 위 묶음에 귀속 |

**ⓔ 새 제외 후보 = 0.** 승계 제외(이미 결정된 것의 재적용) = B4 D1/D2 · U2/U3 구멍 보류 · U17 deptcreate · team-create 카드(1.1.8 원장 #82·X1·#5·결정①).

## 2. 충돌 1순위 2건

### (i) 좌석별 계정 — 원작자 45-③ ↔ 우리 D-mac-1/D-mac-5
- **차이**: 같은 문제가 아니라 **다른 층**이다. 우리 = 권위(어느 폴더가 진짜인가): OS 관측 `CLAUDE_CONFIG_DIR`(맥 KERN_PROCARGS2·리눅스 /proc · 윈 = 안 읽음) > 기록값 → `authoritative_config_dir()` · topology `seat_profile` 영속 → 부활 승계. 원작자 = 표시(그 폴더가 맞는지 카드에 어떻게 보일까): 기록 폴더 × 관측 transcript 로 Verified/Mismatch/Pending/Unknown(`resolve_seat_folder_on`) · 경보 귀속은 기록이 이김(`alert_seat_folder`) · surface.list/org.status 에 `account` 칸.
- **택 = ⓒ 원작자 표시층을 우리 권위 입력 위에 얹는다.** 【관측】 git 자동 병합이 이미 그 꼴이다: 병합본 `collect_seat_rows` 가 `s.authoritative_config_dir()` 를 원작자 두 판정에 넘긴다(accounts.rs 충돌 3덩어리 = agy 휴면 분기 ⓑ · 설명서 단언 ⓒ · 시험 모듈 양쪽 다 ⓒ — 로직 충돌 0).
- **보정 1줄(병합 때 넣음)**: `trusted` 인자 = `s.config_dir_trusted || s.os_observed_config_dir().is_some()` — OS 관측은 사실이므로 transcript 가 아직 없을 때 「계정 확인 중(Pending)」이 아니라 확인됨이어야 한다. 원작자 판정을 그대로 두면 관측 전 좌석이 맥에서 늘 Pending 이 된다【추정 — 시험으로 확정】.
- **시험**: ① 기록 `~/.cys/claude`(trusted) + OS 관측 계정2 + transcript 없음 → `account.profile` = 계정2·Verified(뮤턴트: authoritative → 기록값 교체 시 적) ② 같은 좌석 + transcript 계정2 → Verified ③ OS 미관측(윈 꼴) → 원작자 표 그대로(기존 seat_account_0145 시험 녹) ④ 우리 D-mac-1·D-mac-5 시험 전건 녹 ⑤ 컴파일 수리: 원작자 검체 이음매 `create_surface_untrusted_config_dir` 가 9인자 → 우리 10인자(S3-D2 agent)로 `, None`.
- UI: 부서 카드 계정 줄이 `ccAccounts`(CC Live 탭 열 때만 채움)를 읽음 → 우리 15초 폴러 `accountsCache` 로 재료 교체 · `seatacct.ts` 사용자 문구 2곳 cys→cysr.

### (ii) 휠 — 원작자 45-① ↔ 우리 1.1.5 D5(altscroll)
- **차이**: 같은 증상(윈 claude fullscreen 에서 휠 무동작)의 두 처방. 우리 = 억제는 두되 휠을 PgUp/PgDn 으로 **번역**해 pty 에 씀(UI · 실기 10-02·10-09 휠 됨). 원작자 = 좌석 설정에 `tui:"default"` 를 넣어 **fullscreen 자체를 피함**(Rust · 억제 술어가 애초에 불충족) + 「휠 꺼짐」 토스트. 원작자는 번역을 **일부러 안 했다**: 【관측·원작자 정적 판독 인용 58d5c8e2】 Claude Code 2.1.291 fullscreen 에서 권한 확인 Select 가 떠 있고 내용이 화면에 들어가면 PgUp/PgDn 이 Select 로 가 **휠이 선택 항목을 움직이고, 이어서 Enter 가 다른 선택지를 승인**한다. 우리 altscroll 근거(2.1.280 판독)는 이 모달 경로를 다루지 않는다.
- **택(권고) = 둘 다**: Rust `claude_tui.rs` 수용(윈 좌석 classic 기본 on · 킬스위치 `CYS_WIN_TUI_CLASSIC_OFF` · 완전 초기화 되돌림) + UI 는 우리 핸들러 유지(main.ts #2~#5 ⓑ · 토스트 미배선 — D5 아래선 문안이 거짓). 결과: 우리 번역은 사용자가 `/tui fullscreen` 을 명시한 좌석에서만 발화 → 모달 노출 축소. wheelgate (e) 주석에 「cysr 은 D5 로 번역 · 위험 쟁점 = 이 문서」 단서 1줄.
- **시험**: lib `claude_tui::` 전건(윈 전용 2 포함 = windows-health 필터) · 기동 배선 소스 핀(우리 `d17_d25_launch_wiring_pins` = apply_seat_settings_arg < render_launch 충족) · altscroll/wheelgate bun 시험 녹 · 원작자 새 `wheelgate.test.ts` main.ts 배선 핀 = 우리 관례대로 itDormant(근거 주석) · **윈 실기 A/B 1회**(classic 좌석 휠 · `/tui fullscreen` 좌석 휠 · 모달 떠 있을 때 휠 굴림 → 선택 이동 여부) = canary 관문.

## 3. 겹침 44 파일 — 파일별 1줄 (충돌 = ✗ · 자동 = ○)

| 파일 | | 처리 |
|---|---|---|
| .github/workflows/ci-branch.yml | ✗4 | ⓒ 우리 루프 + 팩 시험 4종(g2·surrogate 중복 제외) |
| .github/workflows/pack-release.yml | ✗2 | ⓒ 같음 |
| .github/workflows/release.yml | ✗4 | ⓒ 같음(build·pack-artifacts) |
| .github/workflows/windows-health.yml | ✗1 | ⓒ 우리 update:: + U5 단계 유지 + agy_statusline::·claude_tui:: 필터 |
| .github/workflows/windows-build.yml | ○ | ⓐ T5b(PYTHONUTF8 없이 phoenix) — 쓰는 경로 전부 우리에 실재 |
| Cargo.toml · Cargo.lock · src-tauri/Cargo.toml | ✗1·✗2·✗1 | ⓑ 판번 1.1.8 · vt100 path 의존·exclude 는 자동 병합분 채택 |
| src-tauri/tauri.conf.json | ✗1 | ⓑ productName cysr · 1.1.8 · updater = pubkey 만(endpoints 부활 0 확인) |
| src-tauri/src/main.rs | ✗1 | ⓒ+ⓓ 토큰 폴더 함수 = 원작자 채택 + 우리 래퍼 · open_url·T4 웹뷰·updater 무접촉 |
| ui/package.json | ✗1 | ⓑ 1.1.8 |
| ui/src/main.ts | ✗9 | ⓒ import 융합(updatenotice·deptcreate 버림) · #2~#7·#9 ⓑ · #8 C2/C3 ⓒ |
| ui/src/style.css | ✗2 | #1 ⓑ(#wsbar-foot 미수용) · #2 ⓒ 합집합 |
| ui/src/usagebar.ts | ○ | ⓐ D1/D2 모델 함수(호출처 없음 = 무해) · cysr 문구 11 보존 |
| ui/src/wheelgate.ts | ○ | ⓐ (e) 주석 + 단서 1줄 · 술어 무변경 |
| ui/src/starvednotice.ts · .test.ts | ○·○ | ⓐ B12 |
| ui/src/feedclass.ts | ○ | ⓐ C2/C3 판정 함수 |
| ui/src/usagewiring.test.ts | ○ | ⓒ D1/D2 describe → itDormant(renderUsageBar 미수용) |
| ui/index.html | ○ | ⓐ 오피스 안내 id 2 · #ws-credit 부활 0 |
| src/bin/cysd/accounts.rs | ✗3 | §2-(i) |
| src/bin/cysd/approval.rs | ✗1 | B1 ⓒ+ⓓ |
| src/bin/cysd/governance.rs | ✗1 | ⓒ 시험 모듈 양쪽 다 · spawn_watchdog 쓸기 둘 공존(📌3) |
| src/bin/cysd/handlers.rs | ✗1 | ⓒ read_text 응답 json 에 scrollback_stale + repaint_echo_skipped |
| src/bin/cysd/main.rs | ✗3 | ⓒ mod 알파벳순 · Job 결박 먼저 + 재기동 상한 · 시험 mod 파일 끝(d6 꼬리 주석 금지) |
| src/bin/cysd/state.rs | ✗2 | ⓒ 같은 락 안 둘 다 · 시험 넷 다 · `, None` 컴파일 수리 |
| src/bin/cysd/alert_route.rs | ○ | ⓐ |
| src/bin/cysd/schedule.rs | ○ | ⓐ+ⓓ B13 |
| src/bin/cys.rs | ✗1 | ⓒ+ⓓ 우리 3줄 → claude_tui 기동 배선 · doctor 항목 인접 |
| src/lib.rs | ✗1 | ⓒ 시험 mod 둘 다 · bridge_probe_*·approval_tokenize 자동 병합 채택(앱 빌드 필수) · spawn 동결표 +agy 2 |
| src/pack.rs | ✗1 | ⓒ 시험 둘 다 |
| src/factory_reset.rs | ○ | ⓐ+ⓓ claude_tui 원장 되돌림 · 배열 길이 28/12/24/9 정합 |
| cysjavis-pack/bin/javis_phoenix.py | ✗13 | ⓒ 원작자 + NOWIN(헬퍼) · 수동 복구 틀 3덩어리 ⓐ · `_ps_table` 변환 |
| cysjavis-pack/bin/javis_state_snapshot.py | ✗3 | ⓐ |
| cysjavis-pack/bin/javis_hud_bridge.py | ○ | ⓐ B4 브리지 + 우리 Hub.watched 공존 |
| cysjavis-pack/hooks/role-capability-gate.sh | ○ | 무변화(우리 = 원작자 수리 선반영) |
| cysjavis-pack/bin/tests/test_capgate_surrogate_deny.py | ○ | 무변화(세 쪽 동일) |
| cysjavis-pack/bin/tests/test_pyseal_census.py | ✗1 | ⓒ REFERENCING_FILES 35 → 37(hud_bridge_0144_specimen · phoenix_encoding_default) |
| cysjavis-pack/web/office-boot.js | ✗1 | ⓐ |
| dist-win/cys.wxs · cys-x64.wxs | ✗1·✗1 | ⓑ 1.1.8 |
| USER-MANUAL.md | ✗8 | ⓒ 원작자 내용 + cysr·갱신 전 파일 패스 |
| docs/RELEASE.md | ○ | ⓒ 0.14.44 윈 실기 항목 = 우리 채널 문면으로 |
| NOTICE.md | ○ | ⓐ vt100 행 |

(44 = 위 행의 파일 합 · 비겹침 41 파일 = 원작자 신규 38 + 수정 3 → 전부 ⓐ【관측 `git diff --name-status`】: vendor/vt100 11(CYS-PATCHES.md 포함) · 새 Rust 8(claude_tui·settings_surgery·repaint·office_bridge·knobs + cysd 시험 3) + 수정 agy_statusline.rs · ui 10(새 ts 9 + 수정 wheelgate.test.ts — 배선 핀은 §5 처방) · 팩 6(시험 4 · hooks .cmd · 수정 hooks/README) · 릴리스 노트 5.)

## 4. 📌 master 판정 (master#60dc9ccf · 10-10 08:23 — ⑴~⑷ 전부 권고대로 · ⑴ canary 관문 = 윈 실기 A/B 통과 전 라이브 금지 · ⑷ 박사님 재상신 불요 = 같은 결정의 반복 적용)

1. **휠 = claude_tui 동반 수용(윈 classic 기본 on) + 우리 altscroll 유지** — 권고. 단점: 윈 claude 좌석 화면 모드가 바뀐다(fullscreen → classic) · 우리 윈 레인은 classic 휠을 실기로 본 적 없다(원작자도 「같은 기계 CSO·리뷰어 좌석이 classic 정상」이 근거) · 사용자 settings.json 쓰기(원장·백업·되돌림 있음). 대안 「claude_tui 미수용」은 모달 Select 이동 위험을 그대로 둔다(우리 실측 0 — 원작자 바이너리 정적 판독뿐).
2. **좌석 계정 trusted 보정 1줄** — §2-(i). 권고 = 넣는다(우리 범위 덧붙임 아님 · 융합의 일부). 단점: 원작자 판정 문면과 1줄 갈림(ledger 기록).
3. **승인 Feed 고아 정리 두 갈래 공존** — 우리 `expire_orphan_feed`(넓음 · 클라이언트 발행도 만료) + 원작자 쓸기(좁음). 권고 = 공존(1.1.9 까지 우리 정책 유지 · 원작자 것은 우리 것이 안 건드리는 닫힌 좌석 화면 감지 승인을 추가로 닫음). 단점: 원작자 C3 의 「데몬 이전 항목 = 모름(null)」 표시는 우리 쪽에서 실제로는 이미 만료돼 거의 안 보인다.
4. **승계 제외 4건(B4 D1/D2 · U2/U3 · U17 · team-create)** — 1.1.8 결정의 재적용이라 새 ⓔ 아님으로 분류했다. 박사님 게이트 재상신이 필요한지만 판정.

## 5. 빌드·시험 계획 (2단계 · 커밋마다 녹)

- **스냅샷 게이트 전건**(4f660dfb 기준선: lib 1029/0 · cys 600/0 · cysd 2475/0 · app 261/0 · 팩 python 3 OK · secret-scan clean): `cargo test --lib` · `--bin cys` · `--bin cysd` · `-p cys-app` · `cd ui && bun test && bunx tsc --noEmit` · 팩 python 전수(짧은 격리 HOME · `CYS_*` 접두 env 제거) · `scripts/secret-scan.sh --all` · 기준선 대조는 **사유 전문**으로(80자 잘림 금지).
- **적색 예상 → 처방 목록(병합 커밋 안에서)**: state.rs `, None` · lib spawn 동결표 +agy 2 · phoenix NOWIN·`_ps_table` · pyseal 37 · wheelgate/feedwiring-0144/usagewiring D1D2 → itDormant(근거 주석) · starvednotice-split 은 governance 문장 결과로 판정 · USER-MANUAL publicdocs.
- **새로 도는 시험**: 팩 4종(5 레인) · ts 7 파일(자동 발견) · cysd 시험 3 모듈(approval_a·feed_sweep·vt100_dim) · lib claude_tui·bridge_probe.
- **윈 영향 파일**: dist-win/cys.wxs · cys-x64.wxs(판번만) · windows-health.yml(필터 2 추가) · windows-build.yml(T5b) · javis_phoenix.py(manual_restore.sh LF · schtasks/taskkill 디코딩 · NOWIN) · javis_state_snapshot.py(cp949 옛 manifest) · hooks/cys-agy-statusline.cmd(신규) · javis_hud_bridge.py(_legacy_win) · src/claude_tui.rs · agy_statusline.rs(윈 자동 연결) · factory_reset.rs(윈 목록 24/9). 윈 동등성 근거 = windows-health·windows-build 미러 CI 런 + canary 실기 A/B(📌1).

## 6. 계수

- **1단계 실소요**: 08:04(접수) → 커밋 시각(아래 git log) · 서브 3기 병렬(판독 9~12분/기) · 브리프 상한 2h.
- **2단계 예상**: 같은 종류 실측 = 1.1.8 편입(`docs/merge/MERGE-RECORD-118.md` §2: 충돌 76 파일 · 해소 53분(서브 7) + 컴파일 6분 + 수리 2회 ≈2.5h + 측정 ≈50분). 이번은 충돌 28 파일·66 덩어리(×0.37)이나 적응 목록(§5)이 길다 → **해소+적응 ≈1.5h + 측정 1회 ≈50분 + 수리 1회 ≈1h = 워커 ≈3.5h**(서브 3~4 병렬) · 적대 검토(codex 1R + Fable 1R)·미러 CI 3런 포함 티켓 전체 = 1.1.8 리베이스 2~3일(10-01~03) 계수의 하한 쪽 — 이번 실측으로 2번째 표본 확보.
