# HANDOFF — cysr 1.1.6 T-USAGE(계정 경보 참말화 + ↻ 본부 cso 닫힘) · TICKET=v116-usage · 2026-09-24

브랜치 `fix/v116-usage`(base = 태그 v1.1.5 `526325bf`) · worktree `~/axdev/.wt/cys-v116-tusage` · 워커 surface:1048 → 재개 후 surface:1060(worker-30) · Opus 5.5 · effort high(세션 jsonl 실측).
검증 산출물 폴더 = `~/axdev/master/reports/cysr-116-plan/v116-usage/`(diff · agy 프롬프트·판정문 1R~7R · opus 판정문 1R~5R).

## ★REVISE 델타(2026-09-24 11:5x~ · master#a80ae6d8 · 근거 = master 재검수 `~/axdev/master/reports/cysr-116-plan/v116-usage/MASTER-REVERIFY-07eafc1d.md`)
- **무엇이 틀렸나(워커 성찰)**: 07eafc1d 【확인요청】은 cysd·cys 두 바이너리 시험만 돌렸다 — 정본 게이트(`cargo test --lib` · `run_bootstrap_health.py` 전량 · `secret-scan.sh --all`)를 안 돌려 이 브랜치가 새로 빨갛게 만든 4결함을 못 봤다. 기능 시험 초록 ≠ 게이트 초록.
- **수리(제품 동작 무변경)**: ①② `f554bf6a` 에이전트 이름 접두 판정을 lib 공용 `cys::is_claude_agent` 로 — accounts.rs 에 `"claude-"` 리터럴 0(폴더 열거 규칙 재구현 핀·H-AUTH-PARSE 가 오탐하던 것 · 게이트 무변경) · 시험 `4919f439` · ③ `ec30a48c` main.rs `#[cfg(test)] mod d6_probe_tests;` → 파일 끝(첫 `#[cfg(test)]` 뒤를 자르는 H-TICK-ALIVE 절단) · ④ `c9fb33e9` 시험 픽스처 `admin` → `runner` · 부록 A 경로 → `$HOME`.
- **편입**: `7bfc3ea1`(feat/v116-usage-oauth · 원천별 신선 한도 statusline 120 / oauth 240 + UI 흐림 한도·출처 배지) → **편입 `f0f60242`**(cherry-pick -x). 근거 = 이 브랜치 base 에 그 결함이 그대로(OAuth 탐침 주기 180s > UI stale 120s → oauth 로만 채워지는 계정이 주기마다 거짓 흐림) · 같은 T-USAGE 계기 참말화 · accounts.rs 충돌 = 시험 모듈 끝 두 시험 병존 · `"claude-"` 재도입 0. UI 무접촉 원칙은 이 편입으로 깨졌다(ui/src 5파일 · bun 1112 → 1123).
- **정본 게이트 1차(4919f439 · 11:59~12:33)에서 워커가 만든 결함 1 발견·수리**: ③ 이동 때 선언 줄 꼬리 주석(`mod d6_probe_tests; // …`)을 달고 파일 끝에 두자, `spawn_policy_tests::production_slice` 가 항목 머리를 `;` 로 안 끝나 「분류 불가」 hard fail → lib 4건 적색(A13·D07d). 종전 35행 자리에선 다음 줄 `use …;` 까지 머리를 따라가 우연히 통과했었다. 수리 `cd428b05` = 주석을 윗줄로. 같은 회차 phoenix `w2_untomb_fullcycle` 1건 rc1(roster=[] · master 두 회차 모두 초록 · 이 브랜치 변경이 roster 경로 무접촉) → 2차 전량 재실행에서 재판정.
- **⏸ 예산 정지(14:1x · master#f75407d7)**: 정본 게이트 2차(d24228db · 13:41 병렬 착수 · `~/msv-scratch/w30/res-d24228db/`)를 **A13(cargo test --lib) 진행 중 14:1x 에 중단** — 완료 74스텝 전부 rc0(적색 0) · 남은 = A13·A14·B01·C01·C02·D01~D11·D07a~e·E01·X01 등 24스텝. 스냅샷 제거 · 잔존 프로세스 0 실측. **재개 = d24228db 로 게이트 전량 재실행**(러너 = `scratchpad/gate/run2.sh` 형 · 대기 없음) → 결과 원문 + PTY 표본(`ttys-d24228db.log`) → 【확인요청】.
- **수리 델타 검증(agy · 델타만 · `hetero-agy-v116-usage-revise.*`)**: REVISE 1건 = ⓓ「편입 시험 `".claude-acct2"` 가 `"claude-"` 탐지에 걸린다」 → **사실 오류로 기각**: 그 문자열은 `claude-` 앞 글자가 따옴표가 아니라 `.` 이라 탐지식(`'"claude-"' in acc` · `.starts_with(".claude-")`)에 안 걸린다 — 실측 python 둘 다 False · 적색이던 lib 핀이 HEAD 에서 초록. ⓐ 동작 동치 · ⓑ 픽스처 의미 보존 · ⓒ D6-1 병합과 충돌 없음(채택 0 이면 source 미갱신) = agy 판정 그대로.
- **정본 게이트**: master 러너(`reverify-tools/gate_runner.py` · 워크플로 run 블록 원문)를 분리 스냅샷에서 HEAD 로 직렬 1회 — 결과 = 【확인요청】 본문(원문 요약) · 로그 = `~/msv-scratch/w30/res-<sha>/`.

## ★재개 델타(2026-09-24 09:3x~ · master#d487cc46 TICKET=resume-after-cysr115-0924 · 좌석 surface:1060)
- **HEAD 대조**: 재개 시 HEAD = `deba443e` = 파킹 보고 sha(인박스 09:01:09 [정정 보충]) → 일치 확인 후 착수.
- **이번 재개에서 한 일**: agy 4R 후보 2 판정(ⓐ 채택 · ⓑ 실측 기각) → 생성 시각 판별(`cb797df1`) → opus 4R 이 그 판의 새 결함(새 파일 연속 → 원 세션 참 경보 영구 보류) 발견 → **파일별 유예 기억으로 재설계(`67fb31c9`)** → opus 5R 시험 공백 보강(`4cfd185d`). 상세 = §6 표 「파킹 → 재개」 아래 행.
- **수렴**: 마지막 제품 커밋 `67fb31c9` 이후 **opus 적대 5R ACCEPT · agy 7R ACCEPT**(6R REVISE 3건 = 수용 1 · 기각 2 → 7R 이 셋 다 타당 판정) → **수렴**. 남는 low = §7-10·11.
- **시험·뮤턴트**: §4-1(최종 HEAD) · 재개분 표적 뮤턴트 = 생성 시각 판 5/5(코드 대체로 소멸) + 파일별 기억 판 10/10(M1~M7 · M9~M11) · 1건(옛 경로 중복 제거)은 **죽은 코드**라 삭제.
- **다음 = 【확인요청】**(master 판단 대기) · push 안 함.

<details><summary>(이력) 파킹 델타 원문</summary>

### 파킹 델타(2026-09-24 08:5x · master#109d9094 TICKET=park-for-cysr115-0924 — 우리 맥 1.1.5 업데이트)
- **어디까지 했나**: 할 일 1(D6-1·D6-2 patch · 적색→초록 · 뮤턴트) ✅ · 할 일 2(T2 원인 파일:행 + 수리 + 시험) ✅ · 격리 실좌석 대조 ✅ · 검증 라운드 agy 1R~3R · opus 1R~2R 전부 반영 커밋(57f6a92d/d31f1358) ✅ · cysd/cys 직렬 전건 = §4-1.
- **진행 중이던 검증 라운드(수렴 확인)**: agy 4R(`hetero-agy-v116-usage-r4.*` — 파킹 시점 판정문 유무는 §6 표) · opus 적대 3R(파킹 때 중단 가능 · 판정 없으면 재개 때 재실행). 둘 다 **dry(새 결함 0)이면 수렴** — 아니면 반영 1회 더.
- **다음 할 일(재개 순서)**: ①§6 의 agy 4R 판정문 읽기 · opus 3R 재실행(대상 = `v116-usage-final-diff.patch` · 2R 판정문과 대조) ②발견 반영 시 제품·시험 분리 커밋 + 뮤턴트 ③cysd·cys 직렬 전건 재실행 ④【확인요청】(머리 3줄 성찰·검증·디버깅 + sha + 시험 표 + 4군 4줄).
- **함정**: 격리 실좌석 소켓은 경로 길이 제한 때문에 `/private/tmp/claude-501/v116<판>.sock` 에 둔다(스크래치 사본은 파킹 때 삭제 — 스크립트 전문은 부록 A) · 격리 데몬의 내장 예약 작업이 좌석을 먼저 닫는 오염이 있다(대조군은 PATH 조회 실패로) · 뮤턴트 돌리는 동안 다른 검증자가 작업본을 읽으면 뮤턴트 상태를 본다(opus 2R 이 「상수 1」을 봄 — 실제 값 2).

</details>

## 0. 한눈에

| 항목 | 원인(파일:행 · base 기준) | 최종 수리 커밋 | 수리 전 → 후 |
|---|---|---|---|
| D6-1 죽은 창으로 계정 경보 | `accounts.rs:1087-1099` `alert_rates` 가 `updated_at==0` 만 거름 ↔ `:1028` `rate_window_stale_reason` 은 계기 JSON 에만 | `75fdf2e2` + 부작용 차단 `4f18c032` → `57f6a92d`(창 라벨 단위 병합) | 검출 2 적색 → 초록 |
| D6-2 claude 파생 에이전트 계정 0건 | `accounts.rs:155` `"claude" =>` · `handlers.rs:6530` `agent == "claude"` | `75fdf2e2` | 검출 2 적색 → 초록 |
| T2a ↻ 뒤 threshold 오산(200k 창 77%) | `usage.rs:315` 관측 경로가 statusline 창 도착 전 `claude_ctx_window()`(`usage.rs:1083` · `[1m]` 없으면 200k)로 % → `usage.rs:472` 발화 | `24a72e90` → `b080056b`(빈 줄 틱 재평가) → `3361b4f8` → `57f6a92d`(유예 = 등록 부착 시각 · 휴리스틱 승계 · 보류 % 기억) → `cb797df1`(생성 시각 판별 · 대체됨) → **`67fb31c9`(유예 상태 파일별 기억 `reattach_tail`)** | 재현 1 적색 → 초록 |
| T2b ↻ 뒤 본부 cso 3초 닫힘 | `cys.rs:10737` 준비 폴링 ① 기동 실패 분기가 신규 출현분(= `--resume` 이 다시 그린 옛 대화)의 오류 문면(`cys.rs:10038`)만으로 `LaunchFailed` → 롤백 close(`cys.rs:13257`) | `7d0e58bb` → `3361b4f8`(에코 아래 · 꼬리 3줄) → `57f6a92d`(연속 두 틱 · 접힌 에코) | 격리 실좌석: 닫힘 → 생존 |

커밋 순서(시험·제품 분리): `43233e26`(검출 시험 이식) · `75fdf2e2`/`10694b0b`(D6) · `24a72e90`/`64b2cfdc`(T2a) · `7d0e58bb`/`d8589f10`/`30852809`(T2b) · `b080056b`/`6bf38aea`(agy 1R 반영) · `3361b4f8`/`2340b757`(opus 1R 반영 — b080056b 의 T2b 부분을 **되돌린 재설계**) · `4f18c032`/`426dea71`(D6-1 부작용 차단) · `57f6a92d`/`d31f1358`(agy 3R·opus 2R 반영) · [파킹·재개] `cb797df1`/`0f91f4cc`(agy 4R ⓐ 생성 시각 판별 · ⓑ 기각 핀) · `67fb31c9`/`edc4e885`(opus 4R 반영 = 파일별 기억 · cb797df1 대체) · `4cfd185d`(opus 5R 시험 보강) · 이 문서.

제품 변경 = `accounts.rs`(귀속 접두 · 경보 필터 · 죽은 묶음 가드 + 순수 함수 1) · `handlers.rs` 1줄 · `usage.rs`(상수 2 · 필드 3 · 타입 별칭 1 · 순수 함수 1 · 재부착 함수 1 · 판정 함수 1 · 발화 2자리) · `cys.rs`(판정 함수 2 · 상수 1 · 호출부 1). UI·팩·설치기 무접촉.

옛 브랜치 `feat/v116-usage-oauth`(9537a961 · base 27e4627e) = **겹침 없음 → cherry-pick 안 함**: UI 흐림 한도(`fresh_limit_secs` 120/240초)를 더할 뿐 `rate_window_stale_reason`·`alert_rates` 무접촉(`git diff 27e4627e 7bfc3ea1 -- src/bin/cysd/accounts.rs` 실측). 채택 여부는 master 판단.

## 1. D6-1 · D6-2

- patch(`D6-patches/D6-1-2-alert-stale-and-claude-variant.patch` 49줄)가 현 base 에 줄 번호 그대로 적용(`git apply --check`). 검출 시험 원본 = `~/axdev/.wt/dbg-telemetry` `166be5e6` → `43233e26`. 수리 뒤 `#[ignore]` 4건 해제(회귀 가드).
- ★오너 조준 「참 경보가 새로 침묵하는가」:
  - 【관측】 「한 창 안에서 %는 줄지 않으니 무관측 창의 옛 값은 하한」은 **라이브에서 반증**: 계정2 7d 78%(관측 09-22 02:54 · resets_at 09-24 17:00 미래)인데 서버 진실 17%(09-23 16:57)·18%(17:14) — `D6-evidence/usage-accounts-1657.json`.
  - 수리는 「못 쟀다」만 뺀다. 계정을 쓰는 순간 statusline(매 assistant 메시지) 또는 OAuth 프로브(부팅 직후 1회 즉시 → 180초 주기 · `main.rs:1312→1316` · 루프 = 조회 후 대기)가 창을 채우고 경보 복귀(`d6_1_true_alarm_rearms_on_fresh_observation`).
  - 형제 창 · 다른 계정 · 경계 안쪽 · `resets_at` 미상 → 경보 유지(`d6_1_true_alarm_*` 5건).
  - `resets_at` 단위: statusline(epoch 초 · `cys.rs:13541`) · OAuth(ISO→epoch 초 · `accounts.rs:519`) · codex(epoch 초) 전부 초.
  - 부작용 차단(opus 1R low → 2R C): idle 좌석 statusline 이 리셋 지난 캐시 창을 더 새 시각으로 보고하면 최신 승자 규칙이 신선한 OAuth 묶음을 덮어, D6-1 필터 때문에 경보 키가 사라졌다 다음 프로브에 돌아오며 매번 재발화(수리 전엔 두 값 모두 경보라 키 유지). 1차(`4f18c032` 「전부 리셋 지난 묶음만」)는 실제 묶음 [5h 지남, 7d 살아 있음]에 우회돼 → 최종 `merge_rate_windows`(`57f6a92d`): **창 라벨 단위**로 리셋 지난 새 창은 같은 라벨의 살아 있는 기존 창을 대체 못 함 · 채택 0 이면 갱신 생략(출처·관측 시각 거짓 갱신 0) · 기각 창은 스냅샷 비영속(재부팅 예열이 죽은 행을 올리지 않게).
  - 남는 지연(문서화 · 코드 무변경): 재부팅 예열 스냅샷은 값이 바뀔 때만 기록돼 `updated_at` = 「마지막 변화」 시각 → 24시간 넘게 값이 그대로였던 창은 부팅 직후 첫 라이브 관측 전까지 경보에서 빠진다. OAuth 프로브 가능 계정은 수 초, 불가 계정(Windows·Linux = `security` macOS 전용 · 키체인 토큰 만료)은 그 계정을 쓰는 순간까지. 계기 JSON 은 같은 창을 stale 로 표시(일치).
- D6-2 접두는 `claude-`(대시 포함)만 — `claudex` 비귀속(`d6_2_prefix_is_dash_delimited`). `handlers.rs` 는 `note_rate` 에 `"claude"` 를 넘기지만 계정 키 = 세션 파일의 프로필 신원(accountUuid)이라 동치(agy 1R #1 기각 근거 · agy 2R 「기각 타당」).

## 2. T2 — ↻ 뒤 본부 cso 새 자리 3초 닫힘 + threshold 오산

### 2-1. 시간선(VM `col-s2-axis3/events-cys.jsonl` · UTC)
| 시각 | 사건 |
|---|---|
| 11:46:48.402 | 본부 cysd 새로 뜸(pid 31750) |
| 11:46:49.948 | surface:9(cso) 생성 · caller_pid **32011** |
| 11:46:52.138 · .218 | 옛 세션 b8bb4651 등록 · cso claim |
| 11:46:52.418 | usage.updated **ctx_window 200000 · 77%**(transcript) → context.threshold(observed · 임계 60) |
| 11:46:53.474 | statusline: ctx_window 1,000,000 · 15%(TUI 이미 그려짐) |
| 11:46:55.238 | **surface.closed(descendants_killed 1)** — 원인 칸 없음 |
| 11:46:55.471 | surface:10(worker) 생성 · 같은 caller_pid 32011 |
| 11:47:11.961 | role.claim_denied(master · caller 32011 · surface.create · takeover_requested) |
| 11:47:27 | surface:12(cso) — phoenix `cys restore` 가 `claude --continue` 로 재기동(저널 `cys restore → surface:12`) |

### 2-2. 닫은 주체 — 파일:행
- **32011 = ↻ 뒤 앱 사이드카 `cys restore --include-master`**: `ui/src/main.ts:6130` → `rotate_daemon`(`src-tauri/src/main.rs:6547-6552`) → `maybe_apply_pending_update` → `spawn_org_restore`(`main.rs:3597`) → `run_sidecar_restore_judged`(`main.rs:3460-3461`). 한 프로세스가 `run_restore`(`cys.rs:15819·15949`) 안에서 역할마다 `run_launch_agent_opts` 를 함수로 불러 세 좌석을 같은 pid 로 만든다. **stderr = `Stdio::null()`(`main.rs:3478`)** — `error: agent … failed to start`·`failed surface … closed` 가 어디에도 안 남은 이유(탐색 서브에이전트 보고 · 인용 대조함).
- 닫기 = `cys.rs:13250-13257` 롤백(`LaunchFailed | Err` → `surface.close{cause:"reap"}`). `LaunchFailed` = `cys.rs:10737` ① 기동 실패 분기: 틱 2.5초마다 기동 send 이후 **신규 출현분 전량**(개행 완성 줄)을 문면 술어에 넣고, 한 틱 안에서 준비 판정보다 **먼저** 돈다. `--resume` 이 다시 그린 옛 대화(옛 도구 출력 포함)는 개행으로 신규 출현분에 실린다. 생성 49.95 + 2틱 ≈ 55.0 + RPC ≈ 관측 55.238.
- worker(surface:10)는 같은 코드 경로 — 차이는 데이터뿐【추정】.
- 【정직】 VM 옛 세션 `b8bb4651.jsonl` 에 그 문면이 실제로 있었는지는 VM 무접촉이라 미확인. 기전은 격리 실좌석으로 재현(§2-4).

### 2-3. 최종 수리
- **T2b** — `launch_failure_confirmed(screen, launch_line, alive)`: 신규 출현분에 실패 문면이 보인 틱에만 확증을 한 번 더 묻는다.
  - ★확증은 **연속 두 틱**(`LAUNCH_FAILURE_CONFIRM_TICKS=2` · agy 3R #1 · opus 2R B): 재출력 **도중**(하단 영역 그리기 전) 틱과 그리드→delta 읽기 순서 역전은 한 틱짜리 거짓 확증이라 다음 틱에 풀린다. 확증 후보 틱은 `continue` 로 준비 판정·신뢰 창 전송을 건너뛴다(맨 셸 주입 방지). 진짜 실패 닫힘은 2.5초 늦어진다.
  - 거부권 ① `alive == Some(true)`(데몬이 커널 프로세스 표에서 에이전트 관측) — 절대. 근거 = 이 저장소의 오살 비대칭 원칙(`readiness_timeout_verdict` 표 `Some(true) → 보류`). 래퍼만 잠깐 사는 틱은 신규 출현분이 누적이라 다음 틱 재판정.
  - 한 틱의 확증 = 화면 꼬리 **3줄**(`LAUNCH_FAILURE_TAIL_LINES` — 실제 claude 하단 영역 비공백 4줄보다 좁게)에 실패 문면 **또는** 화면 그리드 중 **기동 명령 에코(보낸 줄 앞 16자 · 줄바꿈 무시 탐색 — 긴 프롬프트로 접힌 에코) 마지막 출현 아래**(`grid_after_launch_echo` · 에코 없으면 그리드 전체)에 TUI 렌더 증거 없음.
  - TUI 증거를 신규 출현분에서 보지 않는 이유(opus 1R #1 · 실측 확증): 신규 출현분은 개행 완성 줄만 담는데 claude 하단 영역은 제자리 그리기라 거기 없다(08-07 실측 surface:386 line_count=2). 그리드 전체가 아니라 에코 아래를 보는 이유(agy 1R #3-①): 재사용 좌석 옛 TUI 잔상은 에코 위다.
  - 남는 틈: 재출력 도중 상태가 **두 틱(5초) 넘게** 이어지고 그동안 생존 관측도 없을 때만(시험 박제 · 단일 틱 판정식 자체는 그 틱에 참).
- **T2a** — 관측 경로에서 창이 추정(statusline 서버 창 미수신 · `CYS_CLAUDE_CTX_WINDOW` 없음)이고 유예 기준 시각 뒤 60초(`ESTIMATED_WINDOW_GRACE_SECS`) 안이면 발화만 보류(배지·에지 무장 무변경). 유예 기준(`reattach_tail` · agy 3R #3 · opus 2R A · agy 4R ⓐ · opus 4R) = 등록 경로 부착(SessionStart 훅이 세션 명시 = 이 좌석에 새로 뜬 에이전트)은 **부착 시각**(좌석 생성 시각 기준이면 순차 restore 4번째 이후·node-recover 좌석이 유예 없이 오발) · 휴리스틱 재발견 재부착은 **파일별 기억**: 전에 본 파일로 돌아오면 그 파일의 (기준 시각 · 보류 · 보류 %)를 되찾고, 처음 보는 파일은 부착 시각(동시 세션 오가기 무한 재시작 없음 · 새 세션이 옛 세션의 끝난 유예·보류 %를 물려받지 않음 · 새 파일이 잇달아 생겨도 원 세션 참 경보 보존) · 좌석당 16개 · 넘치면 가장 오래전에 떠난 것부터 잊음. 보류한 추정 %를 기억(`deferred_pct`)해 창 없는 statusline 이 관측을 덮은 뒤에도 재평가 발화. 보류를 기억(`threshold_deferred`)해 새 줄 없는 틱에서도 유예가 끝나면 현재 관측 %로 공유 에지 게이트 발화(agy 1R #2). statusline 이 신선하고 ctx % 를 줬을 때만 보류를 버린다(opus 1R low). 창이 확정된 좌석은 즉시 발화 · statusline 없는 좌석은 유예 뒤 추정치 발화(무clear 100%+ 안전망).

### 2-4. 격리 실좌석(설치된 데몬 무접촉) 【관측】
- 격리 HOME·소켓(`/private/tmp/claude-501/v116<판>.sock` — 소켓 경로 길이 제한) · 팩 APFS 복제 · agents.json 에 가짜 에이전트 추가 · cysd = 수리본 · cys 만 판별로 교체. 스크립트 = 부록 A.
- 가짜 claude v2 = 1초 뒤 옛 대화 재출력(개행 · 옛 도구 출력 `No such file or directory`) + 하단 4줄(구분선·`❯`·구분선·모드 줄)을 `ESC[2K`+줄+`ESC[1B\r` 로 **개행 없이 제자리** 그리고 살아 있음.

| cys 판 | 가짜 claude v2(재출력) | 진짜 실패(`claude-bogus-notinpath`) |
|---|---|---|
| 수리 전(526325bf) | `failed to start (command error in new output)` → surface 닫힘 · rc 1 (VM 동형) | 즉시 닫힘 · rc 1 |
| b080056b(TUI 증거 = 신규 출현분) | **닫힘 · rc 1**(opus #1 확증) | — |
| 3361b4f8(에코 아래 · 한 틱 확증) | 생존 | 즉시 닫힘 |
| 최종(57f6a92d~) | `ready(화면 마커 + 시간 폴백)` · closed 0 · rc 0 | 닫힘 · rc 1(2.5초 늦게) |

가짜 claude v3(재출력 1초 → 2.2초 쉼 → 하단 영역 · 첫 폴링 틱 2.5초가 「재출력 도중」): 수리 전 = 닫힘 · 3361b4f8 = **닫힘** · 최종 = 생존(ready).

- 뒷정리: 매 회차 잔존 cysd·가짜 프로세스 0 · 소켓·락 0(실측).
- 곁 관측: 절대경로 cmd(`/nonexistent/claude-bogus`)는 zsh 가 **소문자** `no such file or directory` 를 찍는데 술어는 대문자 `No…` 만 봐서 수리 전·후 모두 못 잡고 준비 시간초과로 간다(기존 틈 · §7-7).

## 3. 진리표

`launch_failure_confirmed(screen, launch_line, alive)` — 앞단 = 신규 출현분에 실패 문면.
| alive | 꼬리 3줄에 실패 문면 | 에코 아래 TUI 증거 | 확증 | 사례 |
|---|---|---|---|---|
| Some(true) | 무관 | 무관 | 아니오 | 살아 있는 에이전트 |
| None/Some(false) | 예 | 무관 | 예 | zsh·bash·p10k·cmd.exe · 재사용 좌석(잔상 + 꼬리 오류) |
| None/Some(false) | 아니오 | 없음 | 예 | PowerShell 긴 오류(새 좌석·재사용 좌석) · 재출력 도중 틱(남는 틈) |
| None/Some(false) | 아니오 | 있음 | 아니오 | `--resume` 재출력(VM T2) · 에코가 밀린 긴 재출력 |

호출부: 위 표가 참인 틱이 **연속 2번**이어야 닫는다 · 참인 틱은 준비 판정을 건너뛴다.

`defer_estimated_threshold(window_estimated, age)`: 추정 ∧ age < 60 → 보류 · 그 밖 발화(경계 60.0 = 발화). `reattach_tail(…, path, heuristic, now)`(구 `reattach_grace_from` 대체 · 67fb31c9): 등록 경로 → now · 휴리스틱 ∧ 그 경로를 전에 떠난 적 있음 → 그 경로의 (기준 시각·보류·보류 %) 복원 · 처음 보는 경로 → now · 기억 = 다른 파일 16개(가장 오래전 떠난 것부터 방출).
`merge_rate_windows(old, old_at, new, now)`: 새 창이 리셋 지남(resets_at < now) ∧ 같은 라벨 기존 창 살아 있음 → 기존 유지(기각) · 그 밖 채택 · 채택 0 이면 갱신 생략.

## 4. 시험 · 기준선 · 뮤턴트

| 묶음 | 시험 | 수리 전 | 최종 | 표적 뮤턴트(사살/전체) |
|---|---|---|---|---|
| D6 `d6_probe_tests`(cysd) | 14(이식 6 + 참 경보 5 + 접두 1 + 죽은 묶음 2) | 검출 4 적색 · 대조 2 초록 | 14/14 | 10/10(필터 제거 · 계정째 끄기 · resets 미상=stale · 핸들러 원복 · resolve 원복 · 대시 없는 접두 · resets_passed 만 · 죽은 묶음 가드 제거 · all→any · 경계 <=) |
| T2a `usage::tests::t2_*`(cysd) | 9(재개 +1 `t2_grace_memo_per_file` · 생성 시각 판 시험은 대체) | 재현 1 적색(77% · observed · cso · 임계 60 = VM 동일) · 빈 줄 틱 1 적색 · 재개: 종전 좌석 단일 승계(M2) = 새 시험 적색 | 9/9 | 9/9(보류 없음 · 추정 여부 무시 · 유예 무시 · 경계 <= · 빈 줄 재평가 제거 · 보류 표식 안 세움 · 유예 기준=재부착 · 창 없는 statusline 보류 해제 ×2) |
| T2b `tests::t2_*`(cys) | 5 | 전제 단언 = 옛 문면 술어가 재출력에 참 · 옛 5줄 창이 마지막 대화 줄을 담음 | 5/5 | 13/13 = 최종 판정식 6/6(TUI 증거 delta · 그리드 전체 · 꼬리 5줄 · 에코 첫 출현 · 생존 거부권 제거 · 호출부 원복) + 이전 설계 회차 7/7(호출부 원복 · 생존 거부권 제거 · 꼬리 OR 제거 · TUI 거부권 제거 · 미관측도 거부 · TUI 증거 화면 전체 · TUI 거부권 무력화) |
| cysd 직렬 전건 | — | 1056 통과(D6 적용 직후) | §4-1 | — |
| cys 직렬 전건 | — | — | §4-1 | — |

뮤턴트 누계 **42/42**(표의 32 + agy 3R·opus 2R 반영분 10 = 연속 틱 1 · 후보 틱 건너뜀 제거 · 에코 줄바꿈 민감 · 등록 재부착 승계 · 휴리스틱 새 유예 · 보류 % 대체 없음 · 살아 있는 창 유지 제거 · 기각 창 영속 · 채택 0 갱신 · 미상 창 지남 → D6 14 · T2a 12 · T2b 16 — 회차별 스크립트 = scratchpad `mut*.py` · 판정 = 대상 시험만 적색). ※ 08:34 【진행】의 「33」은 MS3 재실행을 두 번 센 오기 — 정정. **재개분 +10**(파일별 기억 판 · M1 기억 무시 · M2 종전 좌석 단일 승계 · M3 등록도 기억 사용 · M4 보류 복원 제거 · M5 상한 제거 · M6 옛 tail 기억 안 함 · M7 호출부 우회 · M9 최신 쪽 방출 · M10 기억 전부 버림 · M11 remove→clone) → 누계 **52/52**(생성 시각 판 5/5 는 코드 대체로 제외 · M8 = 죽은 코드 삭제) · 스크립트 = 이 세션 scratchpad `mut5.py`·`mut6.py`·`mut7.py`.
실행: `env -u CYS_SURFACE_ID -u CYS_ROLE -u CYS_PACK_DIR -u CLAUDE_CONFIG_DIR -u CYS_SOCKET -u CYS_CLAUDE_CTX_WINDOW HOME=<격리> CYS_NO_AUTOSTART=1 target/debug/deps/<bin>-<hash> [필터] --test-threads=1`.

### 4-1. 전건 결과(최종 HEAD 4cfd185d · 제품 67fb31c9 · 격리 HOME · --test-threads=1 · 재개 09:5x)
- cysd: **1069 통과 · 0 실패 · 1 ignore**(기존 ignore) · cys: **291 통과 · 0 실패**. (파킹 전 d31f1358 = 1068/291 · 재개 중 edc4e885 = 1069/291 — 전부 실패 0.)
- (이력) 파킹 전 최종 d31f1358: cysd 1068 통과 · 0 실패 · 1 ignore · cys 291 통과 · 0 실패. (중간 회차: 1056 → 1060 → 1065 / 289 → 290 — 시험 추가분만큼 증가 · 실패 0 유지.)

## 5. 4군 점검
1. **폭주 큐** — 큐 경로 무접촉. D6-1 이 새로 열 뻔한 경보 깜빡임 재발화(키 소멸↔복귀)는 `4f18c032` 로 차단. T2a 보류→재평가는 공유 에지 게이트(`ctx_threshold_armed`)라 중복 발화 0. T2b 확증 조회는 실패 문면이 보인 틱에만 `surface.list` 1회.
2. **무clear 100%+(threshold 오산을 고치다 진짜 CTX 경보를 늦추지 않는가)** — 보류는 「창 미확정 ∧ 좌석 생성 60초 안」 관측 경로 발화만. statusline 경로 발화 무변경(에이전트 무관) · 창 확정 좌석 즉시 · 유예 뒤 빈 줄 틱에서도 재평가 · 재부착이 유예를 리셋 안 함 · 창 없는 statusline 이 보류를 못 지움 → 최악 지연 = 새 좌석 60초 + 폴링 주기(시험 7건 · 뮤턴트 9/9). ★재개(파일별 기억): 휴리스틱이 원 세션으로 돌아오면 원 세션의 끝난 유예를 되찾아 즉시 재평가 — 새 파일이 잇달아 생겨도 참 경보 영구 보류 없음(opus 4R 반례 = 시험 `t2_grace_memo_per_file` back2) · 남는 칸 = 17개+ 새 파일 순회 방출(곁 #10ⓐ). 기존 틈(곁 #5): claude-fable·sonnet 좌석은 관측 폴백 자체가 없다(수리 전부터).
3. **자가치유 전멸(T2 수리가 ↻ 복원을 막지 않는가)** — 막지 않는다: 사이드카가 살아 있는 claude 를 닫고 phoenix 가 `--continue` 로 다시 세우던 사슬을 끊을 뿐. 진짜 기동 실패는 수리 전·후 모두 즉시 닫힘(격리 실측 · rc 1) → 롤백·재기동 경로 유지. 확증 거부 시 = 폴링 계속 → Ready 또는 시간초과(`alive==Some(false)` → 닫힘 · 그 밖 좌석 보존). 남는 칸: 래퍼가 계속 사는 진짜 실패 = 좌석 보존(사람 처방) — 기존 시간초과 표의 같은 칸.
4. **전 pane 사망 + 윈 설치파일** — cys 판정은 OS 공통(cmd.exe · PowerShell 새/재사용 좌석 시험 포함) · 설치기·UI·팩 무접촉 · 윈 설치파일 영향 0. Windows 실기 미검증(정직 — VM 좌석 몫).

## 6. 검증 라운드
| 회차 | 검증자 | 판정 | 처리 |
|---|---|---|---|
| 1R | agy(이종 · diff 전문) | BLOCK 4건 | #2(빈 줄 틱 재평가 누락) 채택 · #3-①(재사용 좌석 잔상) 채택 · #1(note_rate "claude" 고정) 기각 = 계정 키는 프로필 신원 · #3-②(래퍼 생존 거부) 기각 = 오살 비대칭 원칙 · #4(예열 스냅샷) 부분 채택(문서화) |
| 2R | agy | ACCEPT | ★그러나 2R 이 승인한 「TUI 증거를 신규 출현분에서」(b080056b)는 실제 claude 에서 틀렸다 — 아래 opus 1R · 격리 실측으로 확증 · 판정문보다 실측을 따름 |
| 1R | opus 적대 서브에이전트(「참 경보 침묵」 조준) | REVISE 7건 | high #1 채택(재설계 3361b4f8 · 실측 확증) · med #2 채택(꼬리 3줄) · low 3건 채택(창 없는 statusline · 재부착 리셋 · 죽은 묶음 깜빡임) · low 2건 곁 항목(스냅샷 심장박동 · D6-2 절반) |
| 3R | agy | BLOCK 5건 | #1(재출력 도중 틱)·#2(접힌 에코)·#3(좌석 생성 시각 기준 회귀)·#4(창 없는 statusline 뒤 침묵) 채택 → 57f6a92d · #5(빈 묶음 덮어쓰기) 기각 = 유일 호출부 비어 있지 않을 때만 |
| 2R | opus | REVISE(A·B·C + low) | 전부 채택 → 57f6a92d(C = 창 라벨 단위 병합) · PS7 문면 = 곁 항목 |
| 4R | agy | BLOCK — #1·#2·#4 닫힘 · #5 기각 타당 · **새 결함 후보 2**: ⓐ[high] 휴리스틱 좌석의 새 세션이 끝난 유예를 승계(usage.rs `reattach_grace_from`) ⓑ[med·추정] 기존 창 resets_at 미상이면 리셋 지난 정당 관측이 기각(accounts.rs `merge_rate_windows`) | **파킹으로 미처리** — 재개 때 판정·반영. 1차 평가: ⓐ = opus 3R low 와 같은 지점(훅 없는 좌석 한정 · 종전보다 오발이 최대 60초 앞당겨지는 크기) · ⓑ = 미상 창을 「살아 있음」으로 보는 현 규약의 귀결 — 반례 입력(리셋 직후 과거 resets_at 을 주는 API)의 실재 여부부터 확인 필요 |
| 3R | opus | **ACCEPT** | 참고 low 2(휴리스틱 재부착 때 보류 필드 승계 · 휴리스틱 전용 좌석 새 세션 유예 0초) = agy 4R ⓐ 와 같은 지점 · 잔여 = 느린 VM 에서 재출력→하단 2.5초 초과 + 생존 미관측이면 여전히 닫힘(실물 claude 미실측) |

| — | (파킹 → 재개 09:3x · master#d487cc46) | | |
| 4R 처리 | 워커 | ⓐ 채택 · ⓑ 기각 | ⓐ = agy 처방(「need_reset 이면 무조건 부착 시각」)은 기각 — 1R high(동시 세션 오가기 무한 재시작) 재개. 대신 생성 시각 판별 `cb797df1`(유예 시작 뒤 태어난 파일 = 새 세션) · 뮤턴트 5/5. ⓑ = **실측 기각**: 이 기계 `analytics.db rate_snapshots` 의 resets_at NULL 42행(5h 40 · 7d 2) 전부 used_pct 0.0 = OAuth 「창 미개시」 → 죽은 창 %로 덮을 이유 없음 · 경보 결과 동일 · 핀 = `d6_1_merge_rate_windows_table` 끝 행 |
| 5R | agy | ACCEPT(생성 시각 판) | 그러나 아래 opus 4R 이 그 판의 새 결함을 찾음 — 판정문보다 반례를 따름 |
| 4R | opus 적대 | REVISE | **[medium] 채택**: 휴리스틱 = 프로젝트 폴더 mtime 최신 .jsonl 이라 같은 cwd 에 새 파일(`claude -p` 등)이 60초 안쪽으로 잇달아 생기면 좌석 단일 기준 시각이 매번 재시작 → 원 세션 참 경보 영구 보류(cb797df1 이 연 경로) → **재설계 `67fb31c9` = 유예 상태 파일별 기억**(재방문 = 그 파일 상태 복원 · 처음 보는 파일만 부착 시각 · 좌석당 16 · 등록 경로 불변) — 생성 시각 의존 제거로 low(파일시스템 미지원·시계 차이)도 소멸. [medium] 배선 공백 채택 → 재부착 블록을 `reattach_tail` 로 빼 순서 시험 + 배선 소스 핀. low(동일 파일 --resume) = 곁 항목 |
| 6R | agy | REVISE 3 | #1 [low] 17개+ 순회 방출 = 알려진 한계(opus 5R 동일) · #2 [medium] 같은 경로 등록 부착이 재시작 우회 = **기각**(종전 동작 · 그 파일은 휴리스틱 첫 부착 때 이미 부착 시각 유예 · 처방 `\|\| !heuristic` 은 등록 좌석을 매 틱 재부착 → 유예 영구 → 추정 임계 영구 침묵) · #3 [high] 기억된 보류 % 오발 = **등급 기각**(그 파일 자신의 추정치 · 붙어 있었어도 유예 뒤 안전망으로 같은 값 발화 · statusline CTX 신선하면 발화 없이 지움 · 종전은 남의 파일 보류 %를 넘겨받음) |
| 5R | opus 적대 | **ACCEPT** | low 5: 상한 방출(=6R #1) · 되찾은 보류를 다른 파일의 관측 %로 판정(일시적 · 종전보다 좁음) · 경로 전환마다 에지 재무장(종전) · 동일 파일 재개 유예 없음(종전) · **시험 공백(살아남는 뮤턴트 3) → 채택 `4cfd185d`**(재방문 최신 상태 · 오래전 떠난 것부터 방출 · 기억 수 = 상한) → 3/3 사살 |
| 7R | agy | **ACCEPT** | 6R 처리 #1 수용 타당 · #2 기각 타당(처방 적용 시 매 틱 재부착 → 영구 침묵 확인) · #3 기각 타당 |

수렴 상태: 마지막 제품 커밋 `67fb31c9` 이후 opus 5R ACCEPT · agy 7R ACCEPT → **수렴**.

판정문 원문: `hetero-agy-v116-usage.md`(1R) · `-r2.md` · `-r3.md` · `-r4.md` · `adversarial-opus-v116-usage-r1.md` · `-r2.md` · `-r3.md`.

## 7. 곁 항목(이 티켓 밖 · 수리 안 함)
1. **ctx relay 노출 창**: `javis_ctx_relay.py` 는 2분마다 좌석 CTX(관측·자기보고 중 신선한 큰 값 · cso 제외)를 읽는다. T2a 는 threshold **이벤트**만 보류하므로 추정치(예 77%)가 배지·`observed_usage` 에 statusline 도착까지(VM 실측 약 1초) 남는다 — 그 1초에 relay 틱이 걸리면 비-cso 좌석에 `[ctx-threshold]` 가 배달될 수 있다. 처방 후보 = 유예 중 추정 `ctx_pct` 를 비워 「못 쟀다」로(배지 변화 동반 → master 판단).
2. `server_ctx_window` 「한 번 잡히면 세션 내 고정」(`usage.rs:300`) — `/model` 로 1M→200k 로 바꾸면 statusline 이 끊긴 뒤 폴백 %가 5배 과소(진짜 CTX 경보 지연 방향). 관찰만.
3. `surface.closed` 에 닫힘 사유 없음(`governance.rs:4964-4968`) · 사이드카 stderr 폐기(`main.rs:3478`) — T2 가 원인 칸을 코드에서 역추적해야 했던 이유. 처방 후보 = 이벤트 cause 필드 · 사이드카 stderr 로그 파일.
4. phoenix 재기동이 `--continue` 폴백으로 떴다(같은 cwd 최신 세션이 b8bb4651 이라 우연히 맞음 · 저널 verified). 롤백 close 가 사라지면 이 사슬은 시작 안 되지만 `--continue` 폴백 자체는 더 최신 세션이 있으면 다른 대화를 잇는다.
5. **D6-2 절반(opus 1R)**: `usage.rs:177-181` collect_tick · `:574` collect_external · `:203` statusline_fresh · `:159` 소비 수집이 `"claude"` 완전일치 → claude-fable·claude-sonnet 좌석은 트랜스크립트 폴백·관측 경로 CTX 임계(4군 ② 안전망 — statusline 경로 발화는 에이전트 무관이라 살아 있음)·세션 핀·소비 적재가 없다(수리 전부터).
6. 재부팅 예열 스냅샷 심장박동 없음(§1 남는 지연) — 처방 후보 = 값이 그대로여도 N시간마다 스냅샷 1회.
7. zsh 절대경로 실패 문면 소문자 `no such file or directory` 미탐(`cys.rs:10042` 대문자만) — 기존 틈 · 절대경로 cmd 에서만(기본 팩 cmd 는 PATH 조회 = `command not found` 로 잡힘).
9. PowerShell 7 문면 「is not recognized as **a** name of a cmdlet」 미탐(opus 2R·3R) — 기동 실패가 시간초과 → 좌석 보존으로 흘러 죽은 좌석이 역할을 쥔다(기존 · 다음 티켓 권고).
8. 노드 단위 `rate_limit` 경보 임계 90(`alerts.rs:131`) — 계정 경고 80~90 구간은 노드 경보가 받치지 못한다(opus 1R 관찰).
10. **(재개 라운드 · opus 4R·5R · agy 6R) 파일별 유예 기억의 남는 한계** — ⓐ 좌석이 원 세션을 떠난 사이 서로 다른 새 파일 17개 이상이 붙었다 떠나면 원 세션 기억이 방출돼 돌아올 때 유예를 한 번 새로 받는다(반복되면 원 세션이 매번 60초 미만 체류 시 침묵 · 성립 = 8분+ 원 세션이 최신이 아님 · 처방 후보 = 개수 대신 사라진/낡은 파일만 방출). ⓑ 휴리스틱 좌석에서 같은 옛 파일을 `--resume`/`-c` 로 이어 쓰면 그 파일의 끝난 유예를 되찾아 추정 창으로 곧 발화 가능(원 T2 사고는 새 좌석 = 기억 비어 있음이라 해당 없음 · 종전부터). ⓒ 되찾은 보류를 빈 줄 틱에서 판정할 때 현재 관측(`cur`)이 다른 파일의 것일 수 있다(처방 후보 = `cur.session_file == state.path` 일 때만 `cur`). ⓓ 같은 경로 등록 부착은 재시작하지 않는다(종전 · 휴리스틱 첫 부착이 이미 부착 시각).
11. **경로 전환마다 `ctx_threshold_armed` 재무장**(`usage.rs` need_reset 블록 · 수리 전부터): 임계 위 두 파일을 오가면 복귀마다 context.threshold 가 다시 난다(cycle-agent 중복 집행 위험 · opus 4R info·5R low). 처방 후보 = 기억에 없는 새 파일일 때만 재무장.

## 8. 다음 VM 좌석 확인 체크리스트(T2 · 이 티켓은 VM 무접촉)
1. ↻(부서 3 · 본부 3 좌석 · 1M 세션 · 세션 CTX 120k 토큰 이상 · 옛 대화에 오류 출력이 있는 세션 포함) 뒤 본부 이벤트에서 **생성 30초 안 `surface.closed` 0**(대화가 이어지던 좌석).
2. `context.threshold` 중 ctx_window 200000 추정으로 계산된 것 0(usage.updated source=transcript·200000 이 보여도 threshold 0).
3. `ps` claude 인자: 사이드카가 세운 좌석은 `--resume <id>` · `--continue` 0.
4. phoenix 저널 cso `spawn` 이 사이드카 좌석을 재사용(새 surface 재기동 0) · per_role_outcome verified.
5. 진짜 기동 실패 대조: agents.json 에 없는 바이너리(PATH 조회)로 `cys launch-agent` → 좌석 닫힘 · rc 1.
6. 계정 경보: 계정 하나를 idle 로 5h 리셋을 넘긴 뒤 그 좌석 TUI 를 다시 그리게 해(창 크기 변경) `alert.account_rate` 재발화 0.

## 9. 9단계 성찰(원문 `~/axdev/9단계성찰프롬프트/9단계성찰프롬프트.md` · 항목마다 적용 여부 · 이유)

### 9-1. 설계 성찰(착수 직후 1회 · 07:5x)
1. 철학·원칙(로컬·Max 구독·품질 우선) — 적용: 계정 사용량 API 실호출 0(모의 `note_rate` 만) · 설치된 데몬 무접촉 · 품질 기준을 「거짓 경보 제거」가 아니라 「참 경보 생존」까지로 잡음.
2. 구체 설계안 — 적용: patch 그대로 이식 + 반대쪽 경계 시험(참 경보 5) 추가 · T2 는 원인 조사 먼저(두 갈래: threshold 오산 · 닫힘 주체).
3. 시니어 아키텍트 영향 범위 — 적용: `alert_rates` 소비처 3(alerts.rs:425 → governance 에지 · handlers control.alerts · UI) · `resolve` 호출처 · 임계 발화 3경로 공유 에지 · launch 롤백 호출부(launch·node-recover·restore 모두 같은 준비 폴링 경유)를 확인하고 판정은 한 함수로.
4. 설계 결함 재조사(SOT·철학 보존) — 적용: 계기와 경보가 **같은 판정 함수**(rate_window_stale_reason)를 쓰게 해 두 벌 판정을 만들지 않음(단일 정본).
5. 할루시네이션 위험·결정론 치환 — 적용: 모든 판정을 순수 함수 + 진리표 시험으로(결정론) · 미확인 사실(b8bb4651 내용)은 【추정】 표시.
6. 적대 A/B/C — 적용: agy 이종 + opus 적대(「참 경보 침묵」 조준)를 처음부터 계획.
7. 언어 원칙 — 적용: 주석·오류 문안·시험 메시지 한국어(주변 코드 스타일 동일).
8. 필요성 최종 성찰 — 적용: 관련 결함(relay 노출 · `--continue` 폴백 · 사유 칸 부재 등)은 구현하지 않고 곁 항목으로(범위 준수 · 박사님 원칙 4-2).
9. 설계 저장 후 구현 — 적용: TODO(`WORKER_30_TODO.md`) 영속 · 마디마다 커밋.

### 9-2. 완료 전 성찰(코드 성찰 9단계 · 08:4x)
1. 시니어 관점 코드 전수 — 적용: 최종 diff 936줄 재독. 파급: `TailState::attach` 시그니처 변경 → 호출 2곳(좌석 · 외부 세션 = `now`) 모두 갱신 · `launch_failure_confirmed` 는 호출부 1곳 · `note_rate` 가드는 statusline·codex·cmd 어댑터 공통 경로(OAuth 는 `note_oauth` 별도 · 서버 창이라 죽은 묶음 아님).
2. 언어 원칙 전수 — 적용: 사용자 대면 문안 추가 0(stderr 문구 무변경) · 주석 한국어.
3. 절대 목표 대비 미구현 — 적용: PLAN 완료 기준 = `d6_probe_tests` 초록(14/14) · ↻ 뒤 본부 closed 0(격리 실좌석 모의로 확인 · VM 은 §8 체크리스트) · threshold 오산 0(모의 재현 적색→초록).
4. 코드 구조 재검수·context — 적용: CTX 43.6%(08:34 jsonl) · 60% 매듭선 전 완료 · 판단 근거는 전부 디스크(HANDOFF·판정문·스크립트)에.
5. 할루시네이션 재점검 — 적용: ★내 가짜 에이전트 v1 이 모든 줄을 개행으로 찍어 「제자리 그리기」 현실을 못 담았다 → opus 지적 후 v2 로 재실측해 b080056b 판 결함을 확증(실측이 판정문을 이긴 사례 · agy 2R ACCEPT 가 틀렸다).
6. 적대 재점검 — 적용: opus 2R · agy 3R(§6).
7. 결과 재성찰(치명 오류) — 적용: b080056b 가 원 사고를 다시 연 치명 오류를 되돌림(3361b4f8) · 뮤턴트 계수 오기(33→32) 정정.
8. 설계 대비 전수 — 적용: 브리프 할 일 1(patch · 적색→초록 · 뮤턴트) ✅ · 2(T2 원인 파일:행 · 수리 · 시험) ✅ · 옛 브랜치 판정 ✅ · 4군 4줄 ✅(§5).
9. 재시험 — 적용: cysd·cys 직렬 전건(§4-1) · 격리 실좌석 3판 × 2사례(§2-4).

### 9-3. 정밀 디버깅 패스(완료 뒤 1회) — 어디까지 뒤졌나
- 재현: VM 시간선을 격리 실좌석으로 재현(수리 전 닫힘 · descendants_killed 1) · threshold 오산을 단위 재현(77% · observed · 임계 60 — VM 이벤트와 같은 값).
- 경계: 유예 60.0 정확히 = 발화 · resets_at == now = 신선 · 꼬리 창 3/5줄 · 에코 없음/마지막 줄/두 번 출현.
- 실패 경로: 진짜 기동 실패 PATH 조회(닫힘 유지) · 절대경로 실패(소문자 문면 — 기존 미탐 발견 · §7-7) · 데몬 예약 작업이 끼어드는 격리 환경 오염(대조군을 PATH 조회로 바꿔 분리).
- 표적 뮤테이션: 32/32(§4).
- 계수: 읽은 경로 = accounts(resolve·note_rate·note_oauth·seed_known·alert_rates·probe 루프) · alerts evaluate · usage collect_tick/collect_for/빈 줄 분기/claude_ctx_window · handlers usage.report/maybe_fire_context_threshold · cys 준비 폴링 전체(boot_agent_on_surface)·롤백·readiness_timeout_verdict·맨 셸 판별 · state ingest(개행 규칙)·scrollback 정지 판정 · 앱 사이드카 경로(src-tauri main.rs 3416-3597·6547) · VM 이벤트 138줄 · phoenix 로그·저널.

## 부록 A. 격리 실좌석 스크립트
`<E>` = 세션 scratchpad `e2e/` · `bin-old`(526325bf cys) · `bin-b08`(6bf38aea cys) · `bin-fixed`(최종 cys·cysd) · `pack` = `~/.cys/pack` APFS 복제 + agents.json 에 `fakeclaude`(cmd=`<E>/fake/fakeclaude` · ready_marker `❯` · inject_delay 1) · `bogusagent`(cmd=`claude-bogus-notinpath --resume x`).
사용: `AGENT=<fakeclaude|bogusagent> <E>/run.sh <old|b08|fixed>`.

```bash
#!/bin/bash
# 사용: run.sh <old|fixed>  — 격리 cysd 기동 → launch-agent(fakeclaude) → 좌석 생존 판정 → 데몬 정리
E="$(cd "$(dirname "$0")" && pwd)"; V="$1"
R="$E/r-$V"; rm -rf "${R:?}"; mkdir -p "$R/home"
SK="/private/tmp/claude-501/-Users-oogisoogi-axdev--wt-cys-v116-tusage/4fd59ca0-1979-4a2f-92f5-d8b96321c5a6/scratchpad/s/$V.sock"; SKL="/private/tmp/claude-501/v116$V.sock"; rm -f "$SKL"; export HOME="$R/home" CYS_SOCKET="$SKL" CYS_PACK_DIR="$E/pack" CYS_NO_AUTOSTART=1
unset CYS_SURFACE_ID CYS_ROLE CLAUDE_CONFIG_DIR
"$E/bin-fixed/cysd" >"$R/cysd.out" 2>&1 &
DPID=$!
trap 'kill $DPID 2>/dev/null; sleep 0.5; kill -9 $DPID 2>/dev/null; rm -f "$SKL"' EXIT
for i in $(seq 1 40); do [ -S "$CYS_SOCKET" ] && break; sleep 0.25; done
"$E/bin-$V/cys" ping >/dev/null 2>&1 || { echo "daemon not up"; cat "$R/cysd.out" | tail -5; exit 2; }
"$E/bin-$V/cys" events --reconnect >"$R/events.jsonl" 2>/dev/null &
EPID=$!
perl -e 'alarm 60; exec @ARGV' "$E/bin-$V/cys" launch-agent --role worker --agent "${AGENT:-fakeclaude}" --cwd "$R/home" >"$R/launch.out" 2>"$R/launch.err"
RC=$?
sleep 1
kill $EPID 2>/dev/null
echo "[$V] launch rc=$RC"
echo "[$V] stdout: $(tail -1 "$R/launch.out")"
grep -E "failed|closed|ready|관문|보류|확증" "$R/launch.err" | head -5 | sed "s/^/[$V] err: /"
echo "[$V] list:"; "$E/bin-$V/cys" list 2>&1 | head -5
echo "[$V] closed events: $(grep -c '"surface.closed"' "$R/events.jsonl")"
```

가짜 claude v2(`<E>/fake/fakeclaude`):
```sh
#!/bin/sh
# 가짜 claude v2 — 실제 claude 처럼: 옛 대화 재출력은 개행(scrollback 에 실림) · 하단 영역은 개행 없이 제자리 그리기.
sleep 1
printf '%s\n' '> 설치 폴더 점검해 줘' '● Bash(ls $HOME/install-jarvis/old)' '  ⎿  ls: $HOME/install-jarvis/old: No such file or directory' ''
# 하단 영역: 줄마다 지우고 쓰고 커서 한 줄 아래 + 행 처음(개행 문자 없음)
for l in '────────────────────────────────────────────────────────────' '❯ ' '────────────────────────────────────────────────────────────' '  ⏵⏵ bypass permissions on (shift+tab to cycle)'; do
  printf '\033[2K%s\033[1B\r' "$l"
done
exec cat >/dev/null
```
