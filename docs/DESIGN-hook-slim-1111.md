# hook-slim-1111 — 팩 훅이 사용자의 모든 Claude 작업을 느리게 하는 문제 (1.1.11)

> 작성 worker-2(677) · 2026-10-27 · 가지 `fix/1111-hookslim`(기준 int/1111 eb4ef98c)
> 결정 이력: master 5ea965af(A 옵트인 + Rust 포함) → 발행 게이트 8ecd9037(§2 hook-slim 증거 목록) → 재결정 02da1acc(B1 + 범위 확대)
> 계약 요약: **개인 프로필(`~/.claude*`)에는 표지가 있을 때만 팩 훅을 건다 · 좌석 아닌 세션에서 팩 훅은 아무것도 하지 않는다 ·
> 답 뒤(Stop) 관측 훅은 사용자를 기다리게 하지 않는다 · 모든 팩 훅에 짧은 시간 제한 · 사용자 settings 는 바뀐 멤버 외 바이트 그대로.**

## 1. 원작자 진단과 대조
| 원작자 진단(카톡) | 실측 판정 | 근거 |
|---|---|---|
| 설치 시 `~/.claude/settings.json` 에 훅 18개 | 맞다 — 우리 맥 20개(팩) + 상태줄 1 | §2-1 |
| 다수가 도구 호출마다 | 맞다 — Pre/Post/PermissionRequest 10행(matcher '' 3행 = 모든 도구) | §2-1 |
| 시간 제한 2개뿐 | 맞다 — 선언 4/20, 나머지는 하네스 기본 600초 | §2-1 |
| 답 뒤 훅 = 「답은 했는데 계속 작업 중」 | 맞다 — Stop 훅 3개 동기. 실기 최장 818초 · 1,059초 취소 사례 | §2-3 · §2-4 |
| 개인 작업은 CLAUDE_CONFIG_DIR 분리 권장 | 근본 수리는 우리 쪽 — 좌석은 이미 `~/.cys/claude` 를 쓰는데 팩이 개인 프로필까지 등록했다 | §3 |
| (추가 발견) | 좌석 아닌 세션에 **cys 정체 헌장·「대기로 자기보고」 주입**(inject-context) — 속도보다 큰 문제 | §2-4 |

## 2. 실측(변경 전)

### 2-1. 등록 현황(우리 맥 · 읽기 전용 · 10-27 00:0x)
- `~/.claude/settings.json`: 훅 30 = 팩 20 + 사용자 10(`~/.claude/channels/*`) · 팩 statusLine 1 · 팩 훅 timeout 선언 4/20.
- `~/.cys/claude/settings.json`(좌석 프로필): 팩 훅 20 + 사용자 1(canon-guard) · 같은 팩 statusLine.

### 2-2. 훅별 실행 시간 — 격리 HOME · 대표 stdin JSON · 각 20회(첫 회 예열 제외) · 맥(M 시리즈 · Darwin 25.6)
하네스 = `scripts/bench_pack_hooks.py`. 원자료 json = 작업 폴더 scratchpad(보고에 첨부 경로).
같은 이벤트의 훅은 Claude Code 가 **병렬**로 돌리므로 체감 지연 = 그 이벤트 훅들의 최댓값.

| 훅 | 이벤트 | 좌석 아님 p50 / p95 (ms) | 좌석 + `_round` p50 / p95 (ms) | 비고 |
|---|---|---|---|---|
| cys-hook.sh | PreToolUse('') | 7.7 / 9.3 | 8.0 / 8.6 | 모든 도구 호출 |
| cys-hook.sh | PostToolUse('') | 7.7 / 8.6 | 8.2 / 8.4 | 모든 도구 호출 |
| cys-hook.sh | PermissionRequest('') | 7.3 / 7.8 | 8.0 / 8.3 | |
| directive-event-inject.sh | PreToolUse(Bash) | 3.0 / 3.7 | 3.3 / 3.4 | 역할 가드 |
| appbuild-gate.sh | PreToolUse(Edit…) | 28.2 / 31.9 | 30.0 / 31.6 | |
| grill-gate.sh | PreToolUse(Edit…) | 37.4 / 40.9 | 40.4 / 41.5 | |
| grill-arm.sh | PreToolUse(Skill) | 31.5 / 34.5 | 33.1 / 34.4 | |
| commit-memory-nudge.sh | PostToolUse(Bash) | 31.5 / 32.7 | 31.1 / 33.7 | |
| grill-count.sh | PostToolUse(AskUserQuestion) | 36.7 / 38.4 | 36.7 / 38.7 | |
| pack-guard.sh | PostToolUse(Write…) | 33.4 / 34.6 | 32.5 / 34.2 | |
| save-state.sh | Stop | 67.4 / 71.8 | 149.3 / 197.9 | 답 뒤 |
| reflect-scan.sh | Stop | 65.7 / 71.9 | 270.2 / 286.8 | 답 뒤 |
| grill-stop.sh | Stop | 50.1 / 55.2 | 48.2 / 50.2 | 답 뒤 · GATE |
| save-state.sh | PreCompact | 68.8 / 71.0 | 154.3 / 215.3 | |
| reflect-scan.sh | SessionEnd | 70.8 / 76.4 | 282.8 / 298.1 | |
| session-start.sh | SessionStart | 13.8 / 15.3 | 117.6 / 123.1 | 좌석 가드 |
| inject-context.sh | SessionStart | 151.1 / 160.8 (**+1,461B 주입**) | 191.2 / 202.5 | 좌석 아닌 세션에도 주입 |
| inject-background.sh | SessionStart | 3.1 / 3.7 | 3.5 / 3.9 | |
| role-bootstrap.sh | UserPromptSubmit | 3.3 / 3.7 | 158.7 / 179.2 | |
| dept-chat-inject.sh | UserPromptSubmit | 3.6 / 4.1 | 3.6 / 3.9 | |

- 기록 크기 영향(reflect-scan Stop · `_round` 있음 · 5회): 2.0MB 273/292ms · 7.0MB 273/295ms · 34MB 303/313ms — 크기에 둔감.
- 비용 분해(20회 p50): 빈 셸 4.0ms · 공용 프리루드 `_lib.sh` 10.5ms · + 계측 줄 20.4ms · `python3 -c 1` 18.9ms · `cys --version` 7.5ms
  → 도구 훅 1개 ≈ 프리루드 10 + 계측 10 + 파이썬 19 = 30~40ms.
- 실기 로그 `~/.cys/state/hook-timing.log`(10-22~10-27 · 정수 초): reflect-scan n=1,720 · 1초 이상 810 · 10초 이상 19 · **최장 818초**(10-24
  worker-lead) · save-state 최장 4초 · grill-stop 최장 3초. 10초 이상 19건은 워커 다수 동시 가동일(10-22·10-23)에 몰림 — 합성 실측(최악 0.31초)과의
  차이는 부하 경합으로 **추정**(원인 미확정).

### 2-3. 실 Claude Code 로 잰 「답 뒤 대기」(2.1.310 · 격리 팩 사본 · 사용자 설정 원천 제외 · 8초 걸리는 reflect 대역)
| 모드 | 1회 | 2회 | 산출물 |
|---|---|---|---|
| 동기(종전 = `CYS_HOOK_STOP_SYNC=1`) | 10.1초 | 10.2초 | 반환 전 기록 |
| 분리(신규 기본) | 3.3초 | 2.6초 | claude 종료 **뒤** 8초에 기록 · 4/4 실재 |
→ 차이 ≈ 꼬리 8초 전부. 분리 자식은 `claude -p` 종료 뒤에도 살아서 산출물을 남겼다(00:23:27 기록 = 종료 00:23:19 + 8초).

### 2-4. 개인 프로필 기록 14일 집계(`~/.claude`·`~/.claude-acct2` · 첨부물 command·stdout·exitCode·durationMs · 읽기 전용)
스크립트 = scratchpad `scan_cmux_split.py`. 파일 단위로 「session-start 각성 주입이 실제로 들어간 세션 = 좌석」, 나머지 = 좌석 아님.
- **좌석 세션 156개**(10-13~10-27 · 최근 10-26 workers-paperdl·youthnet·workers-demolib · 10-27 paperdl) = 「원 계정 좌석」(master 가
  CLAUDE_CONFIG_DIR 없이 띄움 · 의도된 예외). → 우리 맥은 `~/.claude` 팩 훅이 필요하다 = **표지 대상**(§3-1).
- 좌석 아닌 세션 86개(axdev = cmux master 68 · axdev-cso 12 · Claude 데스크톱 앱 scratch-workspaces 2 · 기타)에서 팩 훅이 한 일:

| 훅 | 기록 근거 | 판정 |
|---|---|---|
| inject-context | 주입 112회(cys 정체 헌장 · 「지시가 없으면 대기로 자기보고하고 턴을 끝낸다」) · 데스크톱 앱 세션 2개에도 | 해로움 |
| commit-memory-nudge | 주입 298회(git commit 뒤 기억 증류 권고) · 본문에 `git commit` 문자열만 있어도 오발화(이 티켓 중 실례 3회) | 기능 의존 0 |
| appbuild-gate | 차단 0(blocking 첨부물 0 · 출력 0) | 이득 0 |
| grill 4종 | 출력 0 · `grill_gate.py:18` 좌석 env 없으면 마커 미생성·통과 | 이득 0 |
| save-state·reflect-scan | master 폴더 `~/axdev`·cso 폴더에 `_round` 없음 = 산출물 0 · ★cso 에서 Stop 2개 **1,059초** 후 취소 1건 | 비용만 |
| cys-hook | 좌석 env 없으면 RPC 0(`cys.rs target_surface`) · ★cso 에서 PreToolUse **866초** 후 취소 1건 | 비용만 |
| 나머지 6(가드 있음) | 출력 0 | — |

### 2-5. 1,059초·866초 사례 원인 추적(master 요청 · 대조군 뒤 명명)
- **866초(10-17 · cso · 1f9b64d5)**: 직전 기록 = `API Error: Your computer went to sleep mid-response`. 같은 PreToolUse 의 **사용자 개인 훅 3개
  (cmux 훅·master-live-tree-verify-guard·cmux-layout-guard)도 865.9초로 함께 취소**(대조군 = 같은 이벤트의 남의 훅이 같은 시간) → 원인 = **맥 잠자기**.
  팩 훅 고유 결함 아님.
- **1,059초(10-12 · cso · 21274475)**: 같은 Stop 의 cmux 훅 2개는 50ms 에 끝났는데 팩 훅 2개만 17.6분 붙어 있다가 다음 입력(작업 알림)에 취소.
  cso 폴더엔 `_round` 가 없어 두 훅 모두 「프리루드 → 파이썬 1~2회 → 즉시 종료」 경로다. 대조 실험 1회(변경 **전** 훅 · 같은 조건 = 좌석 아님 ·
  `_round` 없는 cso 모양 폴더 · 같은 6.8MB 기록 사본 · 5회): save-state 68~78ms · reflect-scan 68~73ms → **재현 안 됨 · 원인 미확정**.
  전원 로그(`pmset -g log`)는 10-20 부터만 남아 그 시각(KST 10-13 00:19~00:36) 잠자기 여부 확인 불가. 후보(근거 없음 · 단정 금지): 턴 끝 유휴 중
  잠자기 · 파이썬 런타임 일시 정체. 어느 쪽이든 B1(좌석 아니면 프리루드 전 탈출)·10초 상한·Stop 분리가 이 계열을 끊는다.

### 2-6. 변경 후 실측(같은 하네스 · 같은 기록 2.0MB · 각 20회 · 10-27 01:09 · load 3.4)
| 훅 | 이벤트 | 좌석 아님 전 → 후 p95 (ms) | 좌석 + `_round` 전 → 후 p95 (ms) |
|---|---|---|---|
| cys-hook.sh | PreToolUse | 9.3 → **5.1** | 8.6 → 9.7(본문 불변 · 오차) |
| cys-hook.sh | PostToolUse | 8.6 → **5.3** | 8.4 → 9.3 |
| cys-hook.sh | PermissionRequest | 7.8 → **5.2** | 8.3 → 8.9 |
| appbuild-gate.sh | PreToolUse | 31.9 → **5.0** | 31.6 → 31.8 |
| grill-gate.sh | PreToolUse | 40.9 → **5.2** | 41.5 → 43.1 |
| grill-arm.sh | PreToolUse | 34.5 → **5.3** | 34.4 → 35.7 |
| commit-memory-nudge.sh | PostToolUse | 32.7 → **5.6** | 33.7 → 32.8 |
| grill-count.sh | PostToolUse | 38.4 → **5.2** | 38.7 → 40.8 |
| pack-guard.sh | PostToolUse | 34.6 → **5.3** | 34.2 → 37.8 |
| save-state.sh | Stop | 71.8 → **5.1** | 197.9 → **30.8**(분리 · 본문은 자식) |
| reflect-scan.sh | Stop | 71.9 → **5.4** | 286.8 → **30.7**(분리) |
| grill-stop.sh | Stop | 55.2 → **5.7** | 50.2 → 57.7(GATE · 동기 유지) |
| save-state.sh | PreCompact | 71.0 → **6.1** | 215.3 → 243.9(동기 유지 · 오차) |
| reflect-scan.sh | SessionEnd | 76.4 → **6.0** | 298.1 → **32.1**(분리) |
| inject-context.sh | SessionStart | 160.8(+1,461B) → **5.9(주입 0)** | 202.5 → 263.4(본문 불변 · 오차) |
| session-start·inject-background·role-bootstrap·dept-chat-inject·directive-event-inject | — | 변화 없음(이미 가드) | 변화 없음 |
- 좌석 아닌 세션: 팩 훅 20개 전부 셸 기동 수준(p95 ≤ 6.1ms · 출력 0 · 부작용 0 — GT1·GT2). 도구 호출 1회당 팩 훅 체감 지연 ≈ 41ms → ≈ 5ms.
- 좌석 「후」의 본문 불변 훅 증감(±20%)은 같은 기계 부하 변동(측정 중 load 3.4~5.8)이다 — 코드 변경 없음.

## 3. 수리

### 3-1. 등록 조건 — 옵트인 표지(A) · 표지 없으면 개인 프로필의 팩 등록 제거
- 표지 = `~/.cys/local/hooks-personal-profiles`(파일 · 내용 무관) 또는 env `CYS_HOOKS_PERSONAL=1`. 3값: 있음·증명된 부재·판독 불가(=쓰지 않음).
  Rust `pack::personal_profile_hooks_opted_in_from` · 파이썬 미러 `javis_preflight.personal_profile_hooks_opted_in_from`(같은 표).
- 개인 프로필 = 홈 직하 `.claude`·`.claude-*`(Rust `personal_profile_dirs_under` 와 같은 이름 규칙) — `CLAUDE_CONFIG_DIR` 이 그쪽을 가리켜도 개인.
  ★R1 수리: 단 실파일·부모 심링크를 풀어 **좌석 프로필과 같은 파일**이면 좌석 프로필이다(지우지도 잔재로 보지도 않는다) — 좌석 프로필 =
  설치 표적 `config_dir_for`(CYS_CONFIG_DIR · 부서면 CYS_ACCOUNT_DIR · 아니면 `<팩 부모>/claude`) ∪ 실소비 `${CYS_ACCOUNT_DIR:-~/.cys/claude}`.
  `~/.claude/settings.json → ~/.cys/claude/settings.json` 파일 링크 · `~/.claude → ~/.cys/claude` 폴더 링크 · `CYS_ACCOUNT_DIR=~/.claude` 셋 다
  여기 든다. Rust `pack::is_seat_profile_settings`(제거 경로·doctor) = 파이썬 `_is_personal_profile_settings`(등록 대상) 같은 술어 → 한쪽이 붙이고
  다른 쪽이 떼는 싸움 0. 한계: 데몬과 preflight 의 `CYS_ACCOUNT_DIR` env 가 다르면 두 쪽 판정이 갈린다(env 일치는 좌석 기동 계약).
- 경로 4개 모두 같은 술어:
  ① 데몬 기동·init-pack 공통 `pack::setup_isolated_config_dir` — 표지 없음이면 `strip_pack_registrations_from_personal_profiles`(★`--no-install-hook`
     = GUI 인앱 업데이트 갈래에서도 돈다 — 업데이트로 올라온 사용자에게 닿는 유일한 길) · 표지 있음이면 종전 각성 훅 병합.
     하네스 노브 `CYS_NO_PERSONAL_HOOK_MERGE=1` 이면 제거도 무동작(병합과 같은 「개인 설정 무접촉」 약속 · agy R1).
  ② `cys init-pack`(cys.rs) — 표지 없으면 대상 = 이 팩의 격리 config 하나(신규 머신 폴백도 `~/.claude` 아님).
  ③ `cys doctor --fix`(cys.rs `diag_hook_personal`) — 표지 없으면 「미등록 = 정상」 · 잔재가 결손 · --fix = 제거.
  ④ 파이썬 `resolve_registration_targets` — 표지 없으면 개인 프로필을 등록 대상에서 뺀다(C08·C27·C28·C32·C33·C41·C55 전부 이 한 점 경유).
- 제거 엔진 = Rust 단일(`factory_reset::strip_pack_registrations_from_personal_profile`) — 기존 `hooks-prune`·factory reset 과 같은 소유 판정
  (`command_points_into_pack_root`: 팩 루트 경계 일치 · `pack-dept-*`·`~/.cys/local` 은 팩 아님) + 팩 statusLine(`CYS_PREV_STATUSLINE` 체인이면 원복).
- **우리 맥**: 원 계정 좌석이 `~/.claude` 를 쓰므로 표지를 둔다 — 설치는 master 가 병합 뒤 맥 실기 때(B1).

### 3-2. 좌석 아닌 세션 즉시 탈출(B1 · master 02da1acc)
- 가드 없던 팩 훅 10개(save-state·reflect-scan·grill-gate·grill-arm·grill-count·grill-stop·appbuild-gate·pack-guard·commit-memory-nudge·
  inject-context)의 **프리루드 앞** 한 줄: 좌석 env 3키(`CYS_/JAVIS_/AITERM_SURFACE_ID` · Rust `env_compat` 와 같은 '비어 있지 않음' 규칙)가 없으면
  stdin 소진 후 exit 0. 인자 호출(`--self-test`)은 제외.
- cys-hook.sh: 탈출을 **맨 앞**(오버레이 판정보다 앞)으로. ⚠동작 변화 = 사용자 로컬 오버레이 `~/.cys/local/hooks/<이벤트>.d` 는 이제 좌석 세션에서만 돈다.
- ⚠계약 변경 = 「신원·env 없는 세션에도 중립 문안 + 본부 작업기억(복원 생명선)」(test_inject_context_role_seat 11a/11b) 폐기 — 근거 §2-4(실사용 0).
- 표지가 있는 기계(우리 맥)에서도 cmux master·cso·데스크톱 앱 세션은 주입 0 · 대기 0.
- role-capability-gate(R1 agy minor): 같은 한 줄이되 조건에 `CYS_ROLE` 도 넣는다 — 이 GATE 는 surface 없이도 `CYS_ROLE` 폴백으로 집행한다
  (`env-cys-role` · 검체 test_env_role_denies_without_daemon · GT5). 넷 다 비면 해소 역할이 언제나 빈 값(= 통과)이라 동작 동일 · 파이썬 기동만 준다.
  `cys_have_surface` 등 2키 검사 훅(session-start·role-bootstrap 등)은 기존 동작이라 범위 밖.

### 3-3. 답 뒤(Stop·SessionEnd) 관측 훅 분리 실행 — `_lib.sh` 5-a″ `cys_hook_detach`
- save-state(Stop)·reflect-scan(Stop·SessionEnd): stdin 을 다 읽은 뒤 같은 스크립트를 `CYS_HOOK_DETACHED=1` 로 다시 띄우고 즉시 exit 0. 분리 묶음
  전체(입력을 넘기는 printf 포함) stdout·stderr = /dev/null → Claude Code 가 기다릴 파이프 0. nohup 있으면 HUP 무시.
- 같은 훅 본문끼리 `<state>/hook-detach/<이름>.lock`(mkdir 원자 · 주인 pid)으로 한 번에 하나 — 종전 턴 경계가 하던 직렬화. ★R1 수리(codex·agy major):
  ① 대기표 `<이름>.q/<epoch>.<부모 pid>` 를 부모가 **반환 전에** 만들고(내용 = 띄운 묶음 pid) 자식이 끝나며 지운다 — 소비자는 대기표+잠금을 본다
     (자식이 잠금을 잡기 전 틈 · 윈 프로세스 생성 지연) · 죽은 주인·주인 미기록 2초 초과 대기표는 소비자가 지운다.
  ② 동기 본문(save-state PreCompact · 롤백 · 분리 실패)도 같은 잠금(대기 상한 20초 — PreCompact 선언 30초 안) → .state_log 회전·BOOT_SNAPSHOT 경합 0.
  ③ 죽은 주인 회수(다시 읽어 같은 주인일 때만) · 주인 pid 2초 넘게 비면 회수(mkdir 직후 죽은 주인 — 종전 120초씩 영구 정체).
  ④ 잠금 실패(자식 120초 · 동기 20초) = **본문 건너뜀** + hook-errors.log rc=124 1줄 — 무잠금 실행 폐지.
  ⑤ 순서(FIFO)는 보장하지 않는다 — 정정: 각 본문이 자기 시각을 쓰고 reflect 는 멱등이라 순서가 바뀌어도 잃는 줄이 없다(종전 「순서 보장」 서술은 과장).
  ⑥ 본문 상한: reflect-scan scan 60초 · memory verify 30초 · save-state 스냅샷 10초(`cys_timeout_run` = 프로세스 그룹 종료 · 초과 rc=124 기록 ·
     verify 시간 초과는 정합 경고로 쓰지 않는다). 파이썬 기동 자체가 멎는 경우는 래퍼도 같이 멎으므로 대상 아님.
- 계측: 부모 `save-state 0s` + 자식 `save-state(bg) Ns` 두 줄.
- 동기 유지: save-state PreCompact(압축 직전 기록) · grill-stop(GATE — exit 2 로 턴 종료를 막는 훅).
- 소비자 정합: inject-context(SessionStart)는 BOOT_SNAPSHOT 을 읽기 전 진행 중 save-state 자식을 최대 5초 기다린다(스냅샷 쓰기는 원자 교체).
- 롤백: `CYS_HOOK_STOP_SYNC=1`(분리만 끈다 · 잠금 참여는 그대로).
- 이벤트 판정 = 페이로드의 `"hook_event_name":"<이벤트>"` 글자 일치(agy minor 반박) — JSON 문자열 안의 같은 글자는 `\"` 로 이스케이프돼 불일치(DT9).

### 3-4. 시간 제한 선언(U-21 표 `HOOK_TIMEOUT_S` 14행 추가)
cys-hook(Pre·Post·PermissionRequest)·appbuild-gate·grill 4·commit-memory-nudge·pack-guard·save-state Stop·reflect-scan(Stop·SessionEnd) = **10초** ·
save-state PreCompact = **30초**(동기 · 안의 스냅샷 데드라인 10초 + 앞뒤). 근거 = p95 최댓값 0.31초 + 윈 인터프리터 냉시작 여유. 훅 안 블로킹 지점(:737 원칙):
cys-hook 의 데몬 RPC 상한 40초(`RPC_IDLE_TIMEOUT_SECS`)는 이 선언이 10초로 자른다(관측 훅 · 출력 없음 → 무해) · GATE 훅은 초과 시 출력 폐기 = 통과
(fail-open) · Stop 관측 훅은 분리라 부모가 수 ms. 등록자 3곳(C33 cys-hook · C27 appbuild · C55 grill)이 이제 같은 표를 본다(기존 엔트리는 timeout 키만
올림 · 사용자 큰 값은 안 내림). Rust 미러: Rust 가 쓰는 훅은 각성 2개뿐이라 새 행은 파이썬 전용(기존 비각성 4행과 같은 선례 · H-SEED-1 대조 집합 불변).

### 3-5. 사용자 settings 바이트 보존 — 제거 엔진 개편(`factory_reset.rs`)
- 종전: serde_json `Value`(이 크레이트는 preserve_order 미사용 = 사전순 Map)로 통째 재직렬화 → 훅 한 줄을 지워도 **파일 전체 키 순서가 뒤섞였다**
  (실 파일은 `JSON.stringify(값, null, 2)` 형식 · 10-27 실측).
- 신규(R1 수리 반영): **중첩 외과 삭제** — 팩 hook 객체와 그 때문에 비게 된 entry·이벤트·hooks 멤버의 원문 구간만 걷어내고 남는 이웃은 원래
  구분자로 다시 잇는다(`rejoin`) → 남는 사용자 훅의 이스케이프·숫자 표기·들여쓰기·줄바꿈까지 원문 그대로. statusLine 원복 값만 새로 쓴다.
  BOM 유지 · 결과 재판독 값 ≠ 순서 보존 기대값(`OJ`)이면 **무변경 거부**(전체 재직렬화 폴백 폐지) · 손댈 자리 중복 키 = 거부.
  개인 프로필 제거는 엄격 소유 판정(`personal_pack_command`: 런처 + `<팩>/hooks/` 스크립트 하나 · MSYS 드라이브 정규화)을 쓴다.
  ★R2(agy): 판정 범위(`hooks`·`statusLine` 하위) 안 중복 키 = 계획 단계 거부(JSON.parse 와 판정이 갈릴 수 있다 · `OJ` 는 중복을 모두 보존) ·
  이전 상태줄 원복(`CYS_PREV_STATUSLINE`)은 같은 셸 낱말 분해로 값을 꺼낸다(윈 형식·역슬래시 런처·값 안의 ` sh ` 에서 삭제되던 결함 수리).
- 개인 프로필 경로만: **읽기 전용 파일 존중**(고칠 것이 있어도 쓰지 않고 사유 1줄) · 사전 백업 `.bak-cys-hookslim-<unix초>`(반복해도 첫 원본 보존).
- 공유 엔진이라 factory reset·hooks-prune 도 순서 보존의 덕을 본다(읽기 전용 존중은 그쪽엔 적용하지 않음 — 종전 계약 유지).

## 4. 상태표 S1~S12(발행 게이트 §2) — `cysjavis-pack/bin/tests/test_hook_slim.py` · 실 바이너리 · 격리 HOME
전후 diff 전문 = 보고 첨부 `hookslim_diffs.md`. 판정 = 기대값(원본 dict 에서 팩 등록만 뺀 것의 `JSON.stringify(…, null, 2)` 모양)과 **바이트 일치**.

| 상태 | 결과 |
|---|---|
| S1 새 설치(파일 없음) | `~/.claude` 생성 안 함 · 좌석 프로필에 각성 훅 2 |
| S2 1.1.10 설치본(팩 훅 20 + 팩 상태줄) | 팩 등록 전부 제거 · hooks 키 통째 제거 · 다른 키 바이트 보존 · 사전 백업 1 = 원본 바이트 · 로그 1줄 |
| S3 팩 + 사용자 훅 섞임(우리 맥 모양) | 사용자 훅 3행 순서·바이트 보존 · 팩 20행 제거 |
| S4 사용자 훅만 | 바이트 동일 · 백업 0 |
| S5 깨진 JSON | 원본 무변경 · 백업 0 · 설치 계속(rc 0) · 건너뜀 1줄 |
| S6 읽기 전용 | 원본·권한(0444) 무변경 · 백업 0 · 사유 1줄 · doctor 가 잔재 경고 |
| S7 다중 프로필(`~/.claude`·`~/.claude-acct2`·`CLAUDE_CONFIG_DIR=~/.claude-acct2`) | 둘 다 정리 · **좌석 프로필(`~/.cys/claude`) 팩 훅·상태줄 보존** |
| S8 표지 있음(파일·env) | 개인 프로필 팩 훅 보존(제거 0 · 백업 0) |
| S9 윈 모양(BOM·CRLF·역슬래시 따옴표 명령 · cp949 파일) | BOM·CRLF 유지 · 역슬래시 팩 명령 제거 · 나머지 바이트 보존 / cp949 = 원본 무변경 |
| S10 두 번 실행 · doctor --fix | 무쓰기(바이트 동일 · 백업 추가 0) · 재부착 0 |
| S11 되돌리기 | `cp <백업> settings.json` 1줄 = 원본 바이트 복원 |
| S12 좌석 프로필 판정(R1) | 파일 링크·폴더 링크 → 좌석 settings: 좌석 팩 훅·상태줄 보존 · 백업 0 · doctor hook 줄 「팩 훅 0」· `--fix` 무접촉 / `CYS_ACCOUNT_DIR=~/.claude` → Rust 제거 0 · 파이썬 등록 대상에 같은 파일(같은 술어) / `CYS_NO_PERSONAL_HOOK_MERGE=1` → 무접촉 |
| PF preflight --fix(임시 폴더 밖 HOME) | 개인 프로필 바이트 동일(파이썬 경로 재부착 0) · 좌석 프로필에 선언 timeout 10초 기록 |

## 5. 되돌리기
- 사용자 파일: `cp ~/.claude/settings.json.bak-cys-hookslim-<초> ~/.claude/settings.json`(윈 `copy`).
- 개인 프로필 등록을 원하면: `touch ~/.cys/local/hooks-personal-profiles` → 데몬 재기동 또는 `cys doctor --fix`/preflight `--fix`.
- Stop 분리 끄기: `CYS_HOOK_STOP_SYNC=1` · 선언 timeout 끄기: `CYS_HOOK_TIMEOUT_V1=1`(기존 U-21 축 · 마스터 `CYS_BOOT_GATES=0`).

## 6. 남은 것·한계(정직 목록)
- 1,059초 사례 원인 미확정(§2-5) · 실기 log 의 10초 이상 꼬리 원인 미확정(부하 추정).
- 잠금 파일 `settings.json.cys-lock` 은 사용자 폴더에 남는다(기존 엔진·파이썬 등록기 공통 동작 · 우리 맥엔 이미 있음).
- 리뷰 R1 수리 2차(⏳ 5건) 완료 — 처분표·검증 = HANDOFF.
- 윈도우 실측 미수행 → 의뢰문 `docs/hook-slim-1111-win-measure-request.md`.
- B2(좌석 settings 로 팩 훅 이동 · `~/.claude` 완전 무팩)는 1.1.12 BACKLOG(HANDOFF).
