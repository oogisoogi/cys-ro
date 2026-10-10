# HANDOFF-1110 — 1.1.10 원작자 v0.14.44~48 편입 (2단계 · 병합)

> TICKET=cysr-1110-upstream · 가지 int/1110-upstream · worker-3(surface:1316) · 판정표 = `MERGE-0.14.44-48-PLAN.md`(master#60dc9ccf 통과) · 덩어리 원표 = `MERGE-0.14.44-48-HUNKS.md`
> push 0 · 태그 0 · CI 트리거 0 · 설치본 교체 0.

## 0. 델타 (다음 사람이 이것만 읽어도 이어갈 수 있게)

- **최신(10-10 · §7·§8)**: 병합 f711373a → Fable 1R 반영 9fdf38c6 → codex 1R 반영 abec4fb7(§7 · 설명서에서 휴면 기능 서술 제거) → **agy 상태줄 자동 연결 휴면(§8 · TICKET=cysr-1110-agy-link-dormant)**. agy 갈래 = 한 술어 `cys::dormant::agy_lane_enabled`(컴파일 상수 `AGY_LANE_COMPILED=false` 가 권위 · env 는 그 아래) — 값 push·출력 · 표 귀속 · 자동 연결(설치·갱신·`doctor --fix`)이 전부 이 술어를 본다 → 이 판은 사용자 agy 설정 파일에 쓰지 않는다(끄기 노브로 예전 연결 빼기만 유지). 설명서 §4 「Antigravity(agy)」 8줄 ↔ 코드 일치. → codex 2R 반영(§9 · 설명서 계정 규칙의 Antigravity 잔여 9곳 · 시험 덮기 = 디버그 빌드 전용). 남은 것 = master 미러 push + codex 3R · 윈 실기 W-1~W-6(10-16) · 후보 티켓 = `test-util` feature(§9).
- **★1.1.10 선 확정 = 73a86f1e(10-10 12:57 · master#08c19f62)**: 4차 CI 3런(38019849041·067·121) 전부 success · origin int/1110-upstream = 73a86f1e · 티켓 cysr-1110-upstream(r1~r4)·cysr-1110-agy-link-dormant 종결. **다음 = 318 병합(fix/1110-backlog) · 윈 실기 W-1~W-6 = 10-16**(통과 전 라이브 금지 — §1).
- **codex 3R(393d2a49 · 10-10 12:2x · master#349fde7d) = 수렴 예 · BLOCK 0 · WARN 6** — 잔여 WARN 3건(publicdocs 줄 규칙의 범위 = 낱말·같은 줄만 보고 뜻은 안 봄 · 이 문서 §9 「기록만」 줄의 2R 경고 번호 이관 오기 · USER-MANUAL §17 가산분의 agy RPC 현재형 서술)은 **318 병합 티켓으로 이관**(이 가지에서는 손대지 않는다) · 정본 = `~/axdev/master/reports/upstream-1110/REVIEW-1110-codex-3r.md` · origin + 미러 = 393d2a49 push 완료(master 12:14) · 4차 CI 3런 대기.
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
| W-5 | agy 상태줄 = 연결 안 함(휴면 · **확정**) | 사용자 agy 설정 파일 바이트 동일 · 실연 검사 호출 0 · `state\agy-statusline-*` 새 기록 0 · doctor `agy-statusline` = 「휴면 · 점검 안 함」(경고 아님) · 예전 판이 넣은 표지 달린 연결은 끄기 노브 + `doctor --fix`(또는 다음 설치·갱신)로만 빠짐 | §8 · master#0541bc63 · master#c116db17 · 원작자 3a728d10 은 휴면(코드·시험 유지) |
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

## 7. codex 1R 반영 (r3 · TICKET=cysr-1110-upstream-r3 · worker-3 surface:1322 · master#8840bc86)

- **BLOCK 2(team-propose/team-create 휴면)**: USER-MANUAL 에서 「⚠cysr 1.1.8 주의」 경고 + 「말로 팀 만들기」 절 전체(48줄) · 승인 Feed 절의 「팀 만들기 제안」 문단(3줄) · CLI 표 `team-propose` 행 삭제 + 잔여 3곳(「대표가 대화 승인(`cys-dept create --team-token`)으로 만든 팀」 꼴 — 팀 진행 표지 · 첫 자리 문구 · 팀원 안내)의 그 구절 삭제. 확인 = `grep -c 'team-propose\|team-create\|말로 팀 만들기\|팀 만들기 제안\|--team-token\|대화 승인' USER-MANUAL.md` → 0. 맨 낱말 「팀 만들기」 는 살아 있는 「팀 직접 만들기」 진행 안내(`cys-dept create` 오류 문구 · 예약 유예 노브 · 가산분 머리)에 5곳 남는다 — 금지어 아님(검사 주석에 사유).
- **BLOCK 1(Antigravity)** — 브리프 전제 「agy 전부 휴면」 은 실측과 달랐다: 휴면 = 사용량 값(cys.rs `AGY_STATUSLINE_BRANCH_ENABLED=false` · accounts.rs `agy_lane_enabled`)뿐이고 **자동 연결(사용자 설정 쓰기)은 운영 경로**(`src/pack.rs` `agy::ensure_linked` · doctor `--fix`)다 → 【결정필요】 → master#ea18bd95 B. 이어서 교차 결함 발견: 윈 자동 연결의 쓰기 전 실연 검사(`src/agy_statusline.rs` `PROBE_EXPECT` = 마지막 줄 `cys`)는 우리 휴면 분기의 「출력 0」 과 맞물려 **구조상 통과할 수 없다**(코드 판독 · 윈 실행 0) → 【경고】 → **master#0541bc63 결정 ⓐ = 자동 연결까지 휴면(다음 티켓 `cysr-1110-agy-link-dormant` · 같은 가지)**.
  - 설명서(ⓐ 전제): 「Antigravity(agy) 값」 문단 87줄 → **휴면 고지 + 끄기 노브 둘** 8줄(「이 판에는 들어 있지 않습니다(휴면)」 · 값 받지 않음 · 자동 연결 안 함 · 예전 판이 넣은 `--cys-autolink` 연결을 빼는 길) · 표시 대상의 Antigravity 줄(2줄) 삭제 · `관측 실패` 예시의 「agy 상태줄 연결 필요」 삭제 · 「관측 전 N계정」 예시의 제공자 이름 → 「(계정 이름들)」 · env 표 2행(롤백 노브 표 · §16) = 「휴면 · 끄기」 문면.
  - ⚠**이 커밋 시점 설명서는 코드보다 한 걸음 앞선다**: 맥·리눅스 자동 연결은 아직 돈다(코드 변경 0 — 이 티켓 = 문서). `cysr-1110-agy-link-dormant` 가 들어가기 전에는 태그·발행하지 않는다. 그 티켓의 구현자는 설명서가 약속한 것 — ⓐ 새 연결 0 ⓑ 끄기 노브(`CYS_AGY_STATUSLINE=0` · `~/.cys/agy-statusline-off`) + `doctor --fix`·다음 설치가 표지 달린 연결만 뺌 ⓒ factory-reset 도 뺌 — 을 그대로 지켜야 한다(지금 코드의 unlink 경로 = 그대로 유지).
  - cysd 시험 2건(`accounts.rs` `manual_gives_a_windows_agy_statusline_example` · `manual_documents_the_agy_statusline_autolink_contract` — 원작자가 그 문단을 글자로 핀) = 이름 유지 · 본문을 휴면 사실 핀으로 재작성(휴면 고지 있음 · 코드가 만드는 연결 명령 맥/윈/JSON 꼴이 설명서에 없음 · 값 서술 5종 없음 · 노브 2 + 표지 + `doctor --fix` 있음 · §16 행에 「휴면」). agy 갈래를 다시 켜면 원작자 단언(v0.14.48 이력)으로 되돌린다.
  - `WIN-GATE-1110.md` W-5 = 「연결 안 함(휴면) · 설정 파일 바이트 동일 · doctor 경고 0」 으로 정정(위 §1 표 · `docs/RELEASE.md` 윈 실기 항목도 「켜진 것」 → 「끈 채로 낸 것」).
- **WARN 1**: 전체화면 좌석 진단 문구 3곳 = 「마우스 휠을 PgUp/PgDn 키로 바꿔 보냅니다/보낸다」(`src/claude_tui.rs` `fullscreen_already_set_line` · `src/bin/cys.rs` doctor `claude-tui-fullscreen` · 주석 3) + 문구 핀 2(「꺼집니다/꺼진다」 부재 단언 포함). 동작 변경 0(doctor 판정 Warn 그대로).
- **WARN 5**: `docs/RELEASE_NOTES_0.14.41·44·45.md` 제목 아래 고지 1줄(본문 무수정). **WARN 7**: `src-tauri/src/main.rs` 시험 문서 주석 = 「조작자 토큰을 싣는 자리는 `feed reply --operator` 한 곳뿐」.
- **publicdocs 검사 +1(16 → 17)**: 「휴면 기능 서술 0」 — 금지어 13(팀 6 · agy 7 — 값 보기·연결 명령 꼴) + 휴면 고지 문단 머리 있음 + 판정기 반례(잡을 꼴 5 · 지나갈 꼴 5). 음성 대조: 수정 전(09651d87) 설명서 = 13종 전부 적중(1~8건).
- **기록만(브리프)**: WARN 2(feed_sweep 400바이트 창 — §5 원작자 제안) · WARN 3(schedule 검체 같은 id — 주석 있음) · WARN 4(휴면 코드 잔존 = 판정표상 의도) · WARN 6(윈 컴파일·W-1~W-6 = 10-16 윈 실기) · WARN 8(팩 flaky = CI).
- **남긴 것(범위 밖 · master 판단 감 — ① 은 §9 에서 닫음)**: ① 설명서의 계정 규칙에 Codex 와 나란히 적힌 「Antigravity」 9곳(10줄 · 이름 규칙 · 「사용 중」 정의 · 요약 글자 `A=Antigravity` · 좌석 계정 예시 `Antigravity rv-gemini` · 한계 · 경보 절 2 · RPC `in_use`) — 사용량 표에 Antigravity 줄이 생기지 않으므로 그 규칙이 적용될 일은 없지만 문면은 남아 있다(좌석 계정 줄의 제공자 이름은 지금도 antigravity 를 말한다 — `seat_account_0145` 시험) ② §17 가산분의 `usage.report` `reporter:"agy"` · `source` `agy-statusline` · `agy_csrf_required` · `usage.report_account`(우리는 1.1.8 U3 로 CLI 가 보내지 않는다) = 프로토콜 이력 서술 ③ 휴면 스위치를 env(`CYS_ENABLE_AGY_LANE=1`)로 켜도 cys.rs 상수는 그대로 false 라 값은 오지 않는다(두 스위치가 따로 — 다음 티켓에서 함께 볼 것 → **§8 에서 한 술어로 닫음**).
- **게이트(이 커밋 · 맥 · 자기 트리 · `CYS_*` env 제거 · 순차 · 추적되는 백그라운드 1회)**: cysd 설명서 핀 `cargo test --bin cysd manual_` 6/0 · cys 609/0(182초) · lib 1073/0(무시 2 · 324초) · app 302/0(무시 2 · 10초) · cysd 전수 2600/0(무시 8 · 471초) · ui bun 2917 pass / 85 skip / 0 fail(3002 시험 · 92 파일) · tsc 오류 0 · publicdocs 17/0 · 팩 `test_bootv2_doc_contract` OK(새 HOME·CYS_PACK_DIR) · secret-scan `--all` clean. 팩 전수·윈 = 실행하지 않음(브리프 범위 밖 · CI·윈 실기). 이 작업트리 debug 프로세스 잔존 0.
- **계수**: 착수 10:33 → 편집 끝 10:40(문서 3 · 코드 문자열 3 · 시험 4 · 중간 【결정필요】·【경고】 2회 왕복 포함) → 게이트 10:40~10:58(Rust 순차 ≈17분이 대부분) → 커밋.

## 8. agy 상태줄 자동 연결 휴면 (TICKET=cysr-1110-agy-link-dormant · worker-3 surface:1322 · master#c116db17)

- **왜**: r3(§7)에서 찾은 교차 결함 — 우리 판의 agy 상태줄 명령은 아무것도 보내지 않고 아무 줄도 내지 않는데(1.1.8 휴면 분기), 자동 연결은 그 명령을 사용자 `~/.gemini/antigravity-cli/settings.json` 에 계속 넣고 있었고(맥·리눅스), 윈도우는 쓰기 전 실연 검사가 마지막 줄 `cys` 를 기대해 구조상 늘 실패(파일 무변경 + 실패 기록 + doctor 경고 24시간마다)할 꼴이었다. master 결정 ⓐ = 자동 연결까지 휴면.
- **① 스위치 단일화**(`src/lib.rs` `dormant`): `AGY_LANE_COMPILED: bool = false`(권위) + 순수 판정 `agy_lane_process_default(compiled, env_on) = compiled && env_on` → `agy_lane_enabled()` 의 프로세스 기본값. `src/bin/cys.rs` 에 따로 있던 상수 `AGY_STATUSLINE_BRANCH_ENABLED` 는 없애고 같은 술어를 본다. **동작 변화 1**: 종전에는 데몬 env `CYS_ENABLE_AGY_LANE=1` 만으로 표 귀속이 켜졌다(값은 CLI 상수 때문에 안 옴 = 반쪽) → 이제 env 만으로는 아무것도 켜지지 않는다(상수 true 빌드 + env 둘 다 필요). 시험의 스레드 덮기(`force_for_thread`)는 그대로 켠다. `docs/merge/BACKLOG-118.md` B2 의 「env 로 켠다」 서술은 1.1.8 시점 기록 — agy 는 이 절이 현행.
- **② 게이트 3곳**: ⓐ `src/agy_statusline.rs` `ensure_linked`(운영의 모든 연결 쓰기가 지나는 한 곳) 머리 = 꺼짐이면 `Outcome::Dormant`(새 변형 · 판독·실연 검사·기록 0 · `describe` = 무언) ⓑ `src/pack.rs` 설치·갱신 경로 = 끄기 노브 빼기 다음, 실패 기록 판독·연결 **앞**에서 끝냄(「다시 검사하지 않았습니다」 안내도 0) ⓒ `src/bin/cys.rs` doctor: `--fix` 가 연결·실패 기록 지움을 하지 않고, 항목은 `휴면 · 점검 안 함(이 판은 Antigravity 상태줄을 연결하지 않는다)`(건너뜀 · 경고 아님) + 빼는 방법 안내.
- **③ 유지한 것(설명서 §4 「Antigravity(agy)」 8줄과 일치)**: 끄기 노브 둘(`CYS_AGY_STATUSLINE=0` · `~/.cys/agy-statusline-off`) → 설치·갱신과 `doctor --fix` 가 표지(`--cys-autolink`) 달린 연결만 뺀다(`unlink` = 게이트 밖) · 노브를 켰는데 표지 연결이 남아 있으면 doctor 가 종전처럼 알린다 · factory-reset 의 연결 빼기 무변경. **하지 않은 것**: 이미 들어가 있는 예전 연결의 자동 제거(설명서대로 사용자가 노브로 뺀다 — 남아 있어도 그 줄은 아무것도 내지 않는다).
- **④ 시험**: 원작자 연결 시험 = 이름·단언 그대로 두고 그 스레드에서만 갈래를 켠다(`agy_on()` — lib `agy_statusline::tests` 5자리(공용 헬퍼 1 + 직접 호출 4) · cys doctor 시험 2). 우리 시험 5: lib `cysr_dormant_ensure_linked_leaves_user_settings_untouched`(force 두 값 · 설정 바이트·폴더 목록·기록 무변경 + 대조 = 켜면 연결) · `cysr_dormant_windows_branch_never_runs_the_live_probe`(검사 호출 0 + 대조 = 켜면 1) · `cysr_dormant_unlink_of_our_marked_link_still_works` · `cysr_dormant_install_path_gates_before_probe_record_and_link`(pack.rs 순서 핀 — 그 함수는 시험 빌드에서 실 HOME 보호로 곧장 돌아가 동작 시험 불가) · cys `cysr_dormant_doctor_agy_statusline_skips_and_fix_writes_nothing`(격리 홈 · 빈 칸/사용자 칸 × fix 두 값 = 건너뜀·무변경·실패 기록 무접촉 · 끄기 파일 + `--fix` 로만 빠짐) + lib `dormant_switch_tests` 에 상수 권위 단언.
- **뮤턴트 5(전부 적)**: M1 `ensure_linked` 게이트 제거 → 무변경·검사 0 시험 2 적 · M2 pack.rs 게이트 `false` → 순서 핀 적 · M3 doctor 건너뜀 갈래 제거 → doctor 시험 적 · M4 `--fix` 휴면 갈래 제거(실패 기록이 지워짐) → doctor 시험 적 · M5 술어를 env 단독으로 → `dormant_switch_tests` 적. (`unlink` 유지 시험은 M1~M5 에서 녹 — 게이트와 무관함의 대조.)
- **함정 1**: 기존 `#[test] fn X` 앞에 새 시험을 끼워 넣을 때 원래 `#[test]` 줄이 새 시험 위에 남으면 속성이 둘이 되어 **같은 시험이 두 번 등록·동시 실행**된다(같은 임시 폴더를 서로 덮어 무작위 적 — `running 2 tests` 로 드러남).
- **문서**: `WIN-GATE-1110.md` W-5 = 확정 문면(근거 = 맥 단위 시험·뮤턴트 · 윈 실행 0) · 위 §1 표 · 팩 `hooks/README.md` 래퍼 설명에 휴면 1구절. 설명서(USER-MANUAL)는 abec4fb7 그대로(코드가 따라왔다).
- **게이트(이 커밋 · 맥 · 자기 트리 · `CYS_*` env 제거 · 순차 · 추적되는 백그라운드 1회)**: cys 610/0(188초 · +1) · lib 1077/0(무시 2 · 342초 · +4) · app 302/0(무시 2 · 12초) · cysd 전수 2600/0(무시 8 · 451초) · ui bun 2917 pass / 85 skip / 0 fail · tsc 오류 0 · publicdocs 17/0 · 팩 `test_completion_guard_notice`(hooks/README 판독) OK · secret-scan `--all` clean. 팩 전수·윈 = 실행하지 않음(CI·윈 실기 W-5). debug 프로세스 잔존 0.
- **계수**: 착수 11:00 → 코드·시험 11:07 → 뮤턴트 5 11:08 → 게이트 11:09~11:26(Rust 순차 ≈17분) → 커밋. ≈27분(코드 티켓 · r3 와 같은 크기 — 대부분이 Rust 전수 대기).

## 9. codex 2R 반영 (r4 · TICKET=cysr-1110-upstream-r4 · worker-3 surface:1322 · master#33517c6d)

- **codex 2R(3bd8da5d)** = 수렴 아니오 · BLOCK 1 · WARN 7. 닫힌 것: BLOCK 2(팀 제안 경로) · 휴면 게이트·설명서 8줄 문단 = 코드와 일치 · 새 dead code 0. 남은 BLOCK 1 = §7 「남긴 것 ①」 그대로(사용량 계정 규칙 절에 Antigravity 가 현행 참여자처럼 남은 문장).
- **BLOCK 1 잔여 9곳(10줄) 전수 처리**(USER-MANUAL):
  - 삭제 6(사용량 계정 표에 Antigravity 줄이 없으므로 규칙 자체가 성립하지 않는 문장): 이름 규칙의 제공자 이름 예시 · 별명 키(이름표 `Antigravity (agy)` · 「Codex·Antigravity·직접 선언」) · `● 사용 중` 판정 · 접힌 요약 글자 `A=Antigravity` · 한도 경보 「사용 중」 정의 · RPC `in_use` 설명.
  - 휴면 표기로 바꿈 3(살아 있는 표시라 지우면 거짓이 되는 문장): 부서 탭 **노드별 계정 줄** 예시 `… · Antigravity rv-gemini`(좌석 계정 = `seat_account_json` 이 agy 좌석에 provider antigravity · state known 을 주고 화면은 제공자 이름으로 부른다 — 사용량과 별개의 살아 있는 표시) · 그 절의 「한계」 · 경보 절 「재확인 경로」 의 Antigravity 좌석 문장(「계정 경보가 대신합니다」 = 이 판에서 거짓 → 삭제하고 휴면 표기).
  - 결과: 설명서에서 「Antigravity」 가 나오는 줄 = 6(휴면 고지 문단 머리 · 노드 표시 예시 · 한계 · 재확인 경로 · 끄기 노브 표 2행) — **전부 같은 줄에 「휴면」**.
- **WARN 1(publicdocs)**: 금지어 +4(`A=Antigravity` · `Codex·Antigravity` · `` `Codex`·`Antigravity` `` · `Antigravity (agy)`) + **줄 규칙 1**(「Antigravity 가 나오는 줄은 같은 줄에 휴면」 — 아는 꼴 목록이 놓치는 새 현행형 문장을 잡는다) + 반례 5. 음성 대조: 수정 전(3bd8da5d) 설명서 = 금지어 적중으로 적 · 줄 규칙도 10줄(341·358·368·383·410·427·428·1368·1388·2002) 적중.
- **WARN 2(시험 이음매)**: `dormant::enabled` 가 스레드 덮기를 **디버그 빌드에서만** 읽는다(순수 판정 `dormant::resolve(debug_build, thread_override, process)` · 릴리스 = 덮기 무시 → 운영 바이너리에서는 누가 `force_for_thread` 를 불러도 상수·env 판정만). master#641d3ec0 A 채택 — `#[cfg(test)]` 는 불가(cys·cysd 바이너리 시험이 비시험 빌드 lib 에 링크 · lib.rs 첫 `cfg(test)` 경계를 앞당겨 소스 핀을 깸) · feature 는 시험 명령 130곳·윈 레인 영향이라 **별도 티켓 후보(B: `test-util` feature 정식 도입)**. 팀 흐름 스위치도 같은 함수라 함께 좁혀졌다. 프로덕션 호출 0 = `force_for_thread(` 호출 40곳 전부 시험 구역(파일의 첫 `#[cfg(test)]` 뒤 또는 `*_tests.rs`). ⚠**시험을 `--release` 로 돌리면 덮기가 무효라 원작자 agy·팀 시험이 붉어진다**(지금 워크플로·스크립트에 `cargo test --release` 0건 · `dormant_switch_tests` 가 디버그 프로필 전제를 단언).
- **WARN 3**: `src/lib.rs` dormant 문서 주석의 「켜는 법 = env」 를 팀 흐름/agy 로 갈라 정정(agy = 상수 권위 · env 단독 불가 · docs/merge 의 1.1.8 기록은 그 시점 서술). `docs/merge/BACKLOG-118.md`·`RESOLUTION-LEDGER-118.md` 는 이력 문서라 무수정.
- **기록만**: WARN 4(feed_sweep 400바이트 창) · WARN 5(schedule 검체 id) · WARN 6(윈 컴파일·W-1~W-6 = 윈 실기) · WARN 7(팩 flaky = CI).
- **3R 이관 기록 대조(codex 3R WARN 2 · 병합 티켓 cysr-1110-backlog-merge C2 · master#aac63fe1)**: 위 「기록만」 줄은 2R 보고서 실물(`REVIEW-1110-codex-2r.md` WARN 4~7 = feed_sweep · schedule · Windows · flaky pack)과 **일치한다 — 고치지 않는다**. 3R 이 「Round 2 결과」 로 받은 이관 목록은 「휴면 코드 · Windows · pack flaky · agy RPC 이력」 이었고(3R 프롬프트 6번째 줄), 3R 은 그 넷을 WARN 3~6 으로 유지·미확인 판정했다. 3R WARN 2(「HANDOFF 의 이관 기록이 실제 판정과 다르다」)의 원인 = **master 의 3R 프롬프트 요약 오기**(2R 실물과 다른 목록을 건넸다 · agy RPC 이력 경고는 1R·2R WARN 목록에 없다 · 휴면 코드는 1R WARN 4 → 2R 「확인됨」 에서 설계 부합). 2R WARN 4·5(feed_sweep 400바이트 창 · schedule 검체 id)는 3R 이관 목록에서 빠졌을 뿐 **닫힌 것이 아니다 = 기록 유지**. 3R 의 「agy RPC 이력」(설명서 RPC 가산분 3줄)은 같은 티켓 C3 에서 이력·휴면 표기 + 공개문서 줄 규칙 2 로 닫았다.
- **뮤턴트 1(적)**: `resolve` 가 릴리스에서도 덮기를 읽게(`Some(v) => v`) → `dormant_switch_tests` 적.
- **게이트(이 커밋 · 맥 · 자기 트리 · `CYS_*` env 제거 · 순차 · 추적되는 백그라운드 1회)**: cys 610/0(195초) · lib 1077/0(무시 2 · 365초) · app 302/0(무시 2 · 11초) · cysd 전수 2600/0(무시 8 · 404초) · ui bun 2917 pass / 85 skip / 0 fail · tsc 오류 0 · publicdocs 17/0 · secret-scan `--all` clean. 팩 전수·윈 = 실행하지 않음. debug 프로세스 잔존 0.
- **계수**: 착수 11:33 → 편집 11:37(【결정필요】 왕복 1 포함) → 게이트 11:37~11:53 → 커밋. ≈21분.
