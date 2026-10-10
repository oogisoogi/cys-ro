# HANDOFF-1110 — 1.1.10 원작자 v0.14.44~48 편입 (2단계 · 병합)

> TICKET=cysr-1110-upstream · 가지 int/1110-upstream · worker-3(surface:1316) · 판정표 = `MERGE-0.14.44-48-PLAN.md`(master#60dc9ccf 통과) · 덩어리 원표 = `MERGE-0.14.44-48-HUNKS.md`
> push 0 · 태그 0 · CI 트리거 0 · 설치본 교체 0.

## 0. 델타 (다음 사람이 이것만 읽어도 이어갈 수 있게)

- **한 일**: `git merge --no-ff v0.14.48` 1회(공통 조상 v0.14.43 · 139 커밋) — 충돌 28 파일 66 덩어리를 판정표대로 해소 + 필수 수리 6 + 📌1~3 반영. `UPSTREAM_BASE` = v0.14.48.
- **필수 수리 6(판독 예고 → 실측 확인)**: ① state.rs 원작자 검체 이음매 9→10 인자(`, None`) ② lib `RAW_COMMAND_NEW_FROZEN` + `("src/agy_statusline.rs", 2)` ③ phoenix `_run_decoded` 에 `**NOWIN`(헬퍼 한 곳) + `_emit_evt` NOWIN ④ phoenix `_ps_table` `text=True` → `_run_decoded(…, _dec_any)` ⑤ pyseal `REFERENCING_FILES` 35→37 ⑥ windows-health 에 `agy_statusline::`·`claude_tui::` 필터(일곱째·여덟째).
- **📌 반영**: ⑴ `claude_tui.rs` 수용(윈 classic 기본 on) + UI altscroll 유지 · 토스트 미배선 · wheelgate (e) 끝 단서 1줄 ⑵ accounts `collect_seat_rows` trusted = `config_dir_trusted || os_observed` + 시험 `cysr_os_observed_folder_confirms_untrusted_seat_before_transcript` ⑶ governance watchdog 두 쓸기 공존 주석 1줄(null 의미 차이) ⑷ 승계 제외 4건 = 시험 휴면화(아래 §2).
- **병합 중 발견해 고친 것(판정표에 없던 것)**: ⓐ 원작자 `mod seat_account_0145` 가 git 해소 위치 탓에 우리 최상위 `mod acceptance_v116` 안에 들어감(컴파일 30 오류) → 원작자 위치(`mod tests` 끝)로 이동 ⓑ 판정표 부록 문서가 봉인 env 이름을 인용해 pyseal 참조 집합 38로 셈(작업물 오염 · 1.1.8 선례와 같은 꼴) → 문구 바꿈 ⓒ 부서 카드 계정 줄 재료를 우리 15초 폴러 `accountsCache` 로(원작자 `ccAccounts` 는 CC Live 탭을 열 때만 채움) ⓓ `seatacct.ts` 사용자 문구 2곳 cys→cysr.
- **함정(재현)**: zsh 는 `$VAR` 를 단어로 쪼개지 않는다 — 명령을 변수에 담아 부르면 「no such file」(함수로 감싼다). app 시험 빌드는 `src-tauri/binaries/{cys,cysd}-<triple>` · `src-tauri/runtime` · `src-tauri/resources/pack.tar.gz·pack-manifest.json` · `ui/dist` 가 있어야 build script 가 통과한다(전부 gitignore — 이 작업트리는 binaries = 이 트리 debug 빌드 복사 · runtime = 1.1.9 트리 심링크 · resources = 1.1.9 트리 복사 · dist = `sh ui/build.sh`).

## 1. 1.1.10 윈 실기 관문 (master#60dc9ccf — 통과 전 라이브 금지)

> 실행 명령·기대값 표 = `WIN-GATE-1110.md`(윈 master 가 그대로 실행 · 기대값 출처 = 코드 판독 · 윈 실행 0). 아래는 요약이다.

| # | 항목 | 통과 기준 | 근거 |
|---|---|---|---|
| W-1 | classic 좌석 휠 | 새로 띄운 claude 좌석(윈 · `tui` 키 없던 설정 폴더)에 `"tui": "default"` 가 기록되고 휠로 대화가 올라간다 | 원작자 0.14.45 §1 · PLAN §2-(ii) |
| W-2 | `/tui fullscreen` 좌석 휠 | 사용자가 fullscreen 으로 바꾼 좌석에서 우리 altscroll 이 PgUp/PgDn 으로 번역해 대화가 올라간다(설정 값 덮지 않음) | 1.1.5 D5 |
| W-3 | 모달 떠 있을 때 휠 | fullscreen 좌석에서 권한 확인 선택 창이 떠 있을 때 휠을 굴려도 **선택 항목이 움직이지 않는다** — 움직이면 적(라이브 금지 유지 · master 판단) | 원작자 58d5c8e2 정적 판독(우리 실측 0) |
| W-4 | 킬스위치·되돌림 | `CYS_WIN_TUI_CLASSIC_OFF=1`(또는 `~/.cys/win-tui-classic-off`) 뒤 다음 기동에서 원장 폴더의 `"default"` 만 빠진다 · 완전 초기화도 같은 원장으로 되돌린다 | 원작자 addf1b9b·88fc80e9 |
| W-5 | agy 상태줄 윈 자동 연결 | 쓰기 전 실연 검사 통과 시에만 기록 · 실패 = 파일 무변경 + doctor 사유 | 원작자 3a728d10 · 보안 경계 ⓓ(사용자 설정 쓰기) |
| W-6 | phoenix 자동 복원(윈) | cp949/cp1252 기본 코드페이지에서 복원이 끝까지 돈다 · manual_restore.sh LF | 원작자 0.14.48 A · windows-build T5b |

## 2. 휴면화·조정한 시험 (승계 제외의 시험 쪽 결과)

- `ui/src/usagewiring.test.ts` 0.14.44 D1·D2 두 묶음 13건 → `itDormant`(원작자 U1 패널 위 기능 · 1.1.8 원장 #82).
- `ui/src/wheelgate.test.ts` 「배선 핀(main.ts)」 1건 → `itDormant`(토스트 미배선 · 📌1).
- `ui/src/seatacct.test.ts` 「좌석 제거 시 계정 캐시도 지운다」 2→1(두 번째 자리 = U2/U3 구멍 보류 본문 · 미수용 X1).
- `ui/src/feedwiring-0144.test.ts` 「본부 전용 분기 < team-create」 → team-create 분기 없음(-1)을 함께 단언(D-TEAM 휴면 · 결정①).

## 3. 게이트 (이 병합 커밋 기준 · 기준선 = 4f660dfb 「lib 1029/0 · cys 600/0 · cysd 2475/0 · app 261/0 · 팩 python 3 OK · secret-scan clean」)

(측정 결과는 아래 §3-1 에 커밋 직전 실측으로 채운다.)

### 3-1. 실측

| 묶음 | 기준선(4f660dfb) | 이 병합 | 비고 |
|---|---|---|---|
| Rust lib (`cargo test --lib`) | 1029 / 0 | **1073 / 0**(무시 2) | 326초 · 원작자 새 모듈(claude_tui·bridge_probe·settings_surgery·agy 윈) 포함 |
| Rust cys (`--bin cys`) | 600 / 0 | **609 / 0** | 163초 |
| Rust cysd (`--bin cysd`) | 2475 / 0 | **2600 / 0**(무시 8) | 1회차 2596/4 → 수리 뒤 전수 재실행 436초 = 녹 |
| app (`-p cys-app`) | 261 / 0 | **302 / 0**(무시 2) | 1회차 301/1 → 수리 뒤 전수 재실행 = 녹 |
| ui bun (`cd ui && bun test`) | — | **2915 pass · 85 skip(휴면 레인) · 0 fail** | 3000 시험 · 92 파일 |
| ui tsc(typescript 7.0.2 · `tsc -p tsconfig.check.json`) | — | **오류 0** | |
| 팩 python(ci-branch 맥 루프 131종 · CYS_* 제거 · 시험마다 새 HOME·CYS_PACK_DIR) | — | **128 / 3** | 1,560초 · 아래 분류 |
| secret-scan `--all` | clean | **clean**(1,652 파일) | |
| publicdocs(공식 명칭·갱신 게이트) | — | 15 / 0 | USER-MANUAL 전 파일 패스 뒤 |

- **cysd 1회차 적 4 · app 1회차 적 1 = 전부 시험 쪽 조정으로 닫음(프로덕션 변경 0)**:
  - `seat_account_0145::c2_agent_provider_table…` — 원작자 단언은 agy 사용량 귀속을 요구 · 우리는 usage-noagy 휴면(1.1.8 C4) → 휴면 스위치가 꺼져 있을 때의 기대를 분기로 추가(켜면 원작자 단언 그대로).
  - `approval::tests::recovered_key_never…`(우리 시험) — 소스 핀이 원작자 옛 이름 `best_match_index_at(` 를 찾음 → 0.14.44 A3 의 `best_match_index_ctx(` 로 재조준(「검증한 그 인덱스만 갱신」 핀 `records.get_mut(*matched_idx)` 는 그대로).
  - `feed_sweep_tests::c1_sweep_is_a_separate…`(원작자) — 내가 넣은 한글 주석이 원작자 시험의 400바이트 창 끝을 글자 중간에 걸리게 함 → 주석을 우리 `expire_orphan_feed` 호출 자리로 옮김(시험 무접촉).
  - `schedule::b_textcmd_retired_gate::text_command_notes_classifies_raw_jobs`(원작자) — 검체가 text_command 내장 잡 4개를 가정 · 우리는 2개(BUILTIN v4) → 검체를 앞 두 정의의 사본으로 채움(분류 기대값 불변).
  - app `c2_feed_reply_and_list_all_wiring`(원작자) — 「cys CLI 에 조작자 토큰 0건」 불변식 · 우리는 1.1.8 W D24ⓐⓑ 로 `feed reply --operator` 한 갈래에 싣는다 → 핀을 「그 한 자리(1곳) 밖으로 번지지 않는다」 로 좁힘.
- **📌2 시험·뮤턴트**: `cysr_os_observed_folder_confirms_untrusted_seat_before_transcript` 녹 · 뮤턴트(`|| os_observed` 제거) = 적(`state: pending` · 기대 `known`) → 판정표 【추정】 「관측 전 Pending」 = 실측 확정.
- **팩 적 3 분류**:
  - `test_pyseal_negative_specimen` rc=2 UNMEASURED(「in-tree 로 쓰는 비번들 python 이 없다」) · `test_hook_fail_log` 1건(`test_session_start_fallback_records_reason`) — **기준선 트리(fix/119-prep dc680696 · 같은 러너·같은 env)와 정규화 전문 diff 0** = 이 맥·격리 HOME 고유(병합 무관 · 두 시험과 그 대상 훅은 원작자 43..48 무접촉).
  - `test_refl_inject_context_role_canon` — 전수 실행 중 1회 적(29초) · 단독 재실행 3/3 녹(8·14·9초) = 부하성 흔들림【추정 — 원인 미규명 · 기준선도 단독 녹】.
- 실 팩·실 설치본 쓰기 0(시험 = 임시 HOME·임시 CYS_PACK_DIR) · 이 작업트리 debug 데몬 잔존 0(`pgrep -f cys-1110-upstream/target/debug/cysd` = 0). ⚠1회 실수: 측정 스크립트를 nohup 으로 띄웠다가 감시가 끊겨 같은 cysd 전수를 한 번 더 띄움 → 고아 실행(ppid 1) 1개를 직접 종료(그 실행의 결과는 쓰지 않았다 · 위 수치 = 뒤 실행분).

## 4. 계수 (정책 §0-2 6항 · 2번째 표본)

| 단계 | 시각(10-10) | 소요 | 병렬 |
|---|---|---|---|
| 1단계 판정표 | 08:04 → 08:21 | 17분 | 서브 3기(판독 9~12분/기) |
| 충돌 해소(28 파일 · 66 덩어리) + 필수 수리 6 + 📌 반영 | 08:24 → 08:36 | 12분 | 리드 단독(덩어리 정책 스크립트) |
| 컴파일 수리(모듈 위치 1건) + 시험 빌드 준비물 | 08:36 → 08:38 | 2분(+빌드 대기) | — |
| ui 수리(휴면화 14 · 조정 2) | 08:33 → 08:37 | 4분 | — |
| Rust 전수 1회 | 08:38 → 08:53 | 15분(lib 326 · cys 163 · cysd 401 · app 9초) | 순차 |
| Rust 적 5 수리 + 뮤턴트 | 08:53 → 08:58 | 5분 | — |
| 최종 재측정(cysd·app) + 팩 전수 | 09:00 → 09:34 | 34분(cysd 436초 · 팩 1,560초) | 순차 |
| 기준선 대조·문서·커밋 | 09:34 → 커밋 시각 | git log | — |

- 한 줄 계수: 원작자 139 커밋 · 충돌 28 파일 편입 = **워커 ≈1시간 15분**(해소 12분 + 수리 ≈15분 + 측정 2회 ≈50분) — 1단계 예상 3.5시간보다 짧았다(덩어리 대부분이 인접 추가 · 적색이 전부 시험 쪽).

## 5. 남은 것 (2단계 뒤)

- master 적대 검토(codex 1R + Fable 1R) → 반영 → 미러 CI 3런·병합 = master. 윈 실기 관문 §1(W-1~W-6) = 라이브 전 필수.
- 판 번호: 지금 4곳·wxs 2 = 1.1.8 그대로(원작자 0.14.4x 올림은 버림) — 1.1.10 올림은 통합 리드 몫.
- 설명서: 원작자 0.14.44~48 문면을 cysr·갱신으로 옮겼다(40줄) — 문면 자체의 사실 대조(우리 화면과 다른 기능 서술: 사용량 칸 보기 방식 D1/D2 · 「사용처」 등 우리가 받지 않은 것)는 **하지 않았다** → 공개 문서 다듬기 티켓에서 걸러야 한다【미확인】.
- 원작자 미수리 고지: 윈 오피스 HUD 실시간 표시 멈춤(0.14.49 예정) — 이번 범위 밖.
- **다음 편입 때 원작자에 제안(W2 · Fable 1R)**: `src/bin/cysd/feed_sweep_tests.rs` 「틱 배선」 핀이 `prod[tick..tick + 400]` 바이트 창이다 — 창 안에 비ASCII 주석이 한 줄만 들어가도 글자 중간에서 잘려 패닉한다(이번 병합에서 우리 주석으로 1회 재현 · 주석을 창 밖으로 옮겨 닫음). 줄 기준 핀(호출 줄 다음 N줄 안에 쓸기 호출)으로 바꾸자고 제안한다.
- **Fable 적대 1R(master#e41288ea) 반영 = 뒤 커밋**: USER-MANUAL 사실 대조(미수용 기능 서술 삭제 · 원작자 판번 → 우리 판 어휘 · publicdocs 「원작자 판번 0.14.44 이상 0」 검사) · schedule 검체 사본 주석 · `docs/RELEASE.md` 윈 실기 항목을 우리 채널 문면으로(판정표 §3 에 적어 놓고 병합 커밋에서 빠뜨린 것 — 여기서 집행) · `WIN-GATE-1110.md` 편입.
- 미수리 발견(문안): 원작자 기동 로그·doctor `claude-tui-fullscreen` 의 「전체화면 좌석은 휠 스크롤이 꺼진다」(`src/claude_tui.rs` · `src/bin/cys.rs`)는 cysr(휠 번역 유지)에서 사실과 다를 수 있다 — W-2 실기 뒤 정정 여부 판정(설명서 쪽은 이번에 맞췄다).

## 6. 순환 인계 (10-10 10:3x · 전임 worker-3 → 후임 · master#ec818c78 매듭 지시)

- **상태**: 머리 = 이 문서를 담은 커밋(바로 아래 = 9fdf38c6 Fable 1R 반영 · 그 아래 = f711373a 병합) · 작업 트리 깨끗 · origin push 는 master 가 9fdf38c6 까지 완료 · 미러 재push·CI = master.
- **codex 1R 수신(후임 착수분)**: 수렴 아니오 · BLOCK 2 · WARN 8 — BLOCK = USER-MANUAL 이 휴면 기능 2종(Antigravity 사용량 · team-create)을 활성처럼 서술 · WARN 1 = 전체화면 휠 진단 문구(기동 로그 `src/claude_tui.rs` `fullscreen_already_set_line` · doctor `claude-tui-fullscreen` in `src/bin/cys.rs` · 문구 핀 시험 동반)가 우리 동작(휠 → PgUp/PgDn 번역)과 반대. 코드·보안 경계 해소는 판정표와 일치(재작업 없음). 세부 = 후임 브리프 `master/briefs/brief-upstream-1110-codex1r-2026-10-10.md`.
- **전임이 이미 아는 관련 사실(재탐색 줄이기)**:
  - 설명서의 Antigravity 서술 = §4 「Antigravity(agy) 값」 문단과 env 표 `CYS_AGY_STATUSLINE` 행 — 상태줄 **연결**은 우리도 한다(맥 종전 · 윈 = 이번 편입). **사용량 표 귀속**만 휴면이다(`cys::dormant::agy_lane_enabled` 기본 꺼짐 · `src/bin/cysd/accounts.rs` `fixed_resolution`). 그 문단은 cysd 시험이 글자로 핀한다(`accounts.rs` 의 `include_str!("…USER-MANUAL.md")` 단언들 — 「이제 Windows 도 자동으로 연결합니다」·「쓰기 전 시험 실행」·「파일을 한 바이트도 바꾸지 않고」·「다시 넣지 않습니다」·`cysr doctor --fix`) → 문단을 고치면 그 단언도 같이 본다.
  - team-create: 설명서 병합 전 줄(「말로 팀 만들기」 절 · 그 위 「⚠cysr(우리 판) 1.1.8 주의」 잠정 표기 · 승인 Feed 절 「팀 만들기 제안(kind=team-create-request)」)은 1.1.8 부터 있던 서술이다 — 이번 병합이 더한 줄에는 0건(9fdf38c6 에서 1곳 제거). UI 쪽 team-create 카드 분기는 병합에서 받지 않았다(`ui/src/main.ts` 주석 「원작자 U16 team-create 카드 분기는 받지 않는다」).
  - 공개 문서 게이트 = `cd ui && bun test src/publicdocs.test.ts`(16건 · 맨 낱말 cys 0 · 「업데이트」 0 · 원작자 판번 0.14.44 이상 0). 설명서에 새 줄을 쓸 때 코드 꼴 밖 `cys` → `cysr`.
- **게이트 재현(이 작업 트리 · 맥)**: PATH 에 `$HOME/.cargo/bin`·`$HOME/.bun/bin` · 실행 전 `CYS_*` env 전부 unset · `cargo test --lib` → `--bin cys` → `--bin cysd` → `-p cys-app`(순차 ≈17분) · `cd ui && bun test && bunx -p typescript@7.0.2 tsc -p tsconfig.check.json` · 팩 = ci-branch 맥 루프 131종을 시험마다 새 `HOME`·`CYS_PACK_DIR` 로(≈26분) · `bash scripts/secret-scan.sh --all`. app 시험 빌드 준비물(gitignore)은 이 트리에 이미 있다: `src-tauri/binaries/{cys,cysd}-aarch64-apple-darwin`(이 트리 debug 빌드 사본 — 소스가 바뀌어도 시험에는 무관) · `src-tauri/runtime`(1.1.9 트리 심링크) · `src-tauri/resources/pack*`(1.1.9 트리 사본) · `ui/dist`.
- **함정**: 측정 스크립트를 셸에서 떼어(nohup) 띄우지 말 것 — 감시가 끊겨 중복 기동했다(추적되는 백그라운드 작업으로). 운영 코드 주석에 `creationflags`·`text=True`·`함수이름(`·한글(원작자 바이트 창 시험 근처)을 넣으면 소스 핀이 깨진다(§3-1). 저장소 루트의 미추적 메모 4파일(`overlap.txt` · `up-commits.txt` · `up-files.txt` · `up-files-47-48.txt`)은 master 가 둔 1단계 재료 — 커밋하지 않는다.
