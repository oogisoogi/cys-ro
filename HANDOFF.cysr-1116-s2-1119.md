# HANDOFF — TICKET=cysr-1116-s2-1119 (화면 조각 2 · 3초 고리 분리 + 런타임 미룸 · 워커 worker-1116s2 · 2026-11-19~20)

- 브리프 [master#5340bbd4] `~/axdev/master/briefs/1116-full/s2.md` · 가지 `feat/1116-s2` ← `integ/1116` dea2e1853 · 데몬 변경 0 · 러스트 변경 0 · 팩 변경 0
- ★후임 회차(worker-1116s2b · codex 3R 처분 · §3-6): **데몬 변경 있음**(vendor/vt100 더하기 + cysd attach history_since · master#b4d5c092 승인) · Tauri 변경 있음 · 팩 변경 0
- 설계 = `~/axdev/cysr-ui-research/P2-DESIGN.md` §11 조각 2 행 · §2-1 ㉠ · §2-3 ㉢(F19·F20) · §2-4 ㉣ · §9-4 · §7 4군 ③④ · integ 인계 I3·S4-3(·S1-2 일부)

## 0. 한눈 요약

| 무엇 | 결과(관측) |
|---|---|
| 판정 분리(㉠) | 새 순수 파일 `ui/src/views/judge/tick.ts` — `decideSockPre`(유령 퇴거 · 옛 자리 쓸기 · 입양 후보 · 역할 우선순위 · 집 고르기) · `decidePlaceholders`(자리표 회수 · 조각 0 의 두 벌 접음) · `decideTick`(조각 0 덤프 한 칸 → 같은 판정 재생). main.ts 3초 고리 = 모으기 → 판정 호출 → 집행(detachPane·붙이기·런타임·closePane = 제자리 · §8-2 ③) → 그리기 |
| 같은 입력 → 같은 판정 | 견본 덤프(분리 **전** 코드 200틱) 재생 = 바이트 같음 · 두 번 넣어도 같음 · 음성 대조 성립 · 분리 **뒤** 번들이 e2e 에서 남긴 덤프(1,214틱 중 재생 가능 칸 전부) 재생 = 같음(`TICKREC_REPLAY`) |
| 런타임 미룸(㉢) | 작업 화면이 안 보이면 입양·시작 복원(F19)·빈 탭 충전(F19 · newSurface) = **모형만**(트리에 붙임 + `deferredRuntimes` 장부). 작업 화면이 보이면 `ensureSeatRuntimes` — 보이는 탭 = 즉시 전부 · 나머지 = 한 틱 4개 · 한 번 만든 런타임은 대화 화면으로 가도 부수지 않음 |
| 저장(§2-1 저장 시점) | 대화 화면이면 고리가 render() 대신 `saveLayout()` — 1시간 뒤 저장본에 12좌석(실측) |
| F20 | `ensureSeatRuntime` 실패 = `destroyPaneRuntime`(등록됐으면 파기) · 같은 좌석 재시도 3회 상한 · 기다린 사이 떼였으면 런타임만 파기 |
| I3·S4-3 | 공통층 자체 구독 둘(조각 3 `listen` · 조각 4 `listenDaemon`)과 `default_socket_slug` 재조회 = 걷음 → main.ts `onDaemonEvent` 둘째 줄 `viewsIngest(event, defaultSocketSlug);` 1줄 → `ChatCore.ingest` 가 두 처리기에 한 번씩 · 대화 화면을 열기 전 온 `master.deadman` 도 장부에 남음(시험) |
| 작업 화면 회귀 | 작업 화면(기본)에서는 종전 흐름 그대로(입양 = makePane 먼저 → 붙이기 · 같은 await 재확인) — `tickrec_gate` OFF 대조(기준 번들 dea2e1853 = 새 번들 invoke 열·저장소·화면 글자 바이트 같음) = §3 표 |

## 1. 바뀐 파일

| 파일 | 누구 | 변경 |
|---|---|---|
| `ui/src/views/judge/tick.ts` | 새(우리) | 순수 판정 3함수 + rolePri·homeWsOf |
| `ui/src/views/judge/tick.test.ts` | 새(우리) | 순수성 2 · 재생 3(견본 · 음성 대조 · TICKREC_REPLAY) · F18 4 · 입양 후보 4 |
| `ui/src/views/ingest.test.ts` | 새(우리) | I3·S4-3 정적 3 |
| `ui/e2e/runtime_defer_gate.py` | 새(우리) | 대화 화면 새 설치 장면(§0 표 · §3) |
| `ui/src/views/index.ts` · `views/work/adapter.ts` · `views/core.ts` | 우리 | `workRuntimeWanted()` · `viewsIngest()` · 작업 화면 보임/숨김 고리 · `ingest()` · 자체 구독 걷음 |
| `ui/src/views/confirm.test.ts` | 우리 | S4-3 행동 시험 1 |
| `ui/src/main.ts` | 원작자 + 우리 | §2 |
| 시험 핀·하네스 9파일(`wswiring` · `exitedsweep` · `formation` · `tickrec` · `roleactivity` · `deptprogresswiring` · `closecallbacks` · `kbrestore` · `b230scroll`) | 원작자 + 우리 | 판정이 옮긴 자리로 핀 이관(뜻 그대로 · 각 줄에 `(cysr-1116-s2)` 주석) · `with(scope)` 하네스 대역 목록에 새 이름 |

## 2. 원작자 파일 변경 — `ui/src/main.ts`

`git diff --numstat dea2e1853 HEAD -- ui/src/main.ts ui/index.html src-tauri/src/main.rs` = `main.ts +206/−81` 뿐(index.html·src-tauri 0). 덩어리 17. 설계 §8-1 목표값 +180/−140.

| 자리 | 바뀐 것 |
|---|---|
| import 묶음 | `views/index` import 에 `viewsIngest, workRuntimeWanted` · `views/judge/tick` import 1줄 |
| `refreshPaneTitles` 앞 | 보조 함수(우리): `tickWsModel` · `deferredRuntimes` · `DEFERRED_PER_TICK` · `seatAttached` · `seatInModel` · `deferSeatRuntime` · `ensureSeatRuntime` · `ensureSeatRuntimes` |
| 고리 — 유령·쓸기 | `advanceGhostStrikes`·`exitedSweepTargets` 직접 호출 → `decideSockPre(...)` 결과(`pre.evict` · `pre.sweepTargets`) 집행 · `sweepScopeFor` 줄은 그대로 |
| 고리 — 입양 | 후보 = `pre.adopt` 순서 · 집행 자리에서 같은 조건 재확인(낡은 판정 막이) · `!workRuntimeWanted()` 갈래 = 붙이기 + 장부 · 작업 화면 갈래 = 종전 본문 그대로 |
| 고리 — 자리표 | `shouldClosePlaceholder` 직접 호출 → `decidePlaceholders(...)` · 기록 줄 = `v.in`(한 벌) · 집행 전 장부·손댐·트리 재확인 + **닫기 직전 그 자리 재판정**(지금 화면 줄 수 · codex 1R blocking) |
| 고리 — 그리기 | 작업 화면 = 종전(render · 신호 · 포커스) · 대화 화면 = `saveLayout()` + 신호 · 끝에 미룬 런타임 한 틱 4개 |
| `destroyPaneRuntime` 첫 줄 | 미룬 장부 지우기 1줄 |
| `render()` | `renderWsTabs()` 뒤 미룬 런타임(보이는 탭) 1줄 |
| `newSurface` | `makePane` 을 `workRuntimeWanted()` 갈래로(F19) |
| `onDaemonEvent` 둘째 줄 | `viewsIngest(event, defaultSocketSlug);`(I3·S4-3 · 첫 문장 `const name` 은 그대로 = toastaxis 핀) |
| `start()` | `bootViews({... onWorkShown: () => { retryFailedRuntimes(); render(); } })` · 복원 입양 `makePane` 을 갈래로(F19) |

## 3. 시험 — 기준선(dea2e1853) 대비

격리 env(빈 HOME·TMPDIR · CYS_* 없음) · 맥 부하 평균 27~35(다른 좌석 9개 동시 빌드 · master#1fe5fc05 공지) 아래에서 잼.

| 대상 | 기준선 dea2e1853 | 이 가지 80747b11c | 판정 |
|---|---|---|---|
| `sh ui/build.sh` | rc 0 | rc 0 | 같음 |
| tsc `--package typescript@7.0.2 -p tsconfig.check.json` | rc 0 | rc 0 (음성 대조: 새 시험의 `toBeTruthy`·`skipIf`·`Bun` 미선언 = rc 1 로 잡혔다가 고침) | 같음 |
| bun test(ui) | 3747 · 88 skip · 0 fail | **3770 · 89 skip · 0 fail**(부하 6.0) — 부하 32 에서는 1 붉음 = `tickrec.test.ts` 「최악 장면」 시간 초과(15.9·12.2초 · 본문 무변경) · 부하 6 단독 1.58초 초록 | +23 새 시험(tick 12+1 skip · ingest 5 · runtimedefer 5 · confirm 1) |
| 화면 게이트 13종(race·focus·seatrows·pillar·seatgroup·rolereuse·stty·nodept·restart·hidden_block·tickrec·chat·confirm) | stty 외 12종 PASS(stty = 이 작업트리에 cysd 없음) | **13종 PASS** · 통과 줄 수 = 기준선과 같음(race 109 · focus 73 · seatrows 76 · pillar 78 · seatgroup 9 · rolereuse 12 · nodept 17 · restart 7 · hidden_block 19 · tickrec 34 · chat 59 · confirm 37) · stty 8 | 같음 |
| tickrec_gate OFF 대조(작업 화면 회귀 0) | — | 기준 번들 = 새 번들 바이트 같음(invoke 1088건 (명령·인자) 순서 · 저장소 3키 · 화면 글자 · pane 2 · 탭 sha256 `308dd2b91f9a…`) · 대조군 같음 · 음성 대조 다름 | 같음 |
| 새 `runtime_defer_gate.py` | — | PASS(아래) | — |
| 판정 재생(bun) | — | 견본 200틱(분리 전) = 같음 · 분리 뒤 e2e 덤프(`TICKREC_REPLAY`) = 13/0 | — |
| ci-branch.yml 팩 단계 4개(토큰·단계별 env 그대로 · 167건) | (팩 바이트 = 기준선과 같음 · 가지 변경 0) | §3-1 | 환경 |
| secret-scan `--all`(커밋 뒤) | — | 1차 1건(HANDOFF 개인 경로) → clean 2191 파일 | — |
| cargo | — | 러스트 변경 0 → 시험 생략 · stty 게이트용 `cargo build --bin cysd --bin cys`(CARGO_BUILD_JOBS=4) rc 0 | — |

**runtime_defer_gate(최종 번들)**: 대조군(작업 화면 시작) 흐름 13 · xterm 12 / 대화 화면 새 설치: ① 좌석 12 입양 → start_surface_stream 0 · attach_surface 0 ② 1시간(1,200틱) list_surfaces +1200 · 겹침 0 · 고리 오류 0 · 흐름 0 · 저장본 12/12 좌석 ③ 첫 진입 → 13/13 xterm(자리표 포함) · 「(없음)」 0 · 가짜 시계 0 ms(실시간 161 ms · 대역 하네스) · resize_surface 13건 = 보이는 좌석 × 1 · 흐름 13 ④ 전환 100회 → 다시 만들기 0 · 그 뒤 30초 +10 틱 · 자리표는 런타임이 선 뒤 회수(12좌석) · 페이지 오류 0.

**뮤턴트**(새 시험이 대상을 실제로 잡는가 · 붉어진 시험 이름까지 확인):

| 뮤턴트 | 붉어진 것 |
|---|---|
| tick M1 rolePri cso↔worker | tick.test ② 재생 · ② 음성 대조 · ④ 우선순위 |
| tick M2 「이미 붙음」 건너뛰기 뺌 | tick.test ④ 미룬 좌석 재선택 0 |
| tick M3 대기 중 탭을 집으로 | tick.test ④ 집 고르기 |
| tick M4 장부 걸러내기 뺌 | tick.test ② 재생 · ③ F18 4건 |
| tick M6 자리표 대기 중 탭 허용 | tick.test ③ 대기 중 탭 |
| tick M5·M7 사본 갱신 뺌 | **0 — 동치 → 그 코드를 걷음**(§4-4) |
| main MM1 대화 화면 미룸 끔 | runtime_defer ① ② |
| main MM2 대화 화면 저장 뺌 | runtime_defer ② 저장 1/12 |
| index MM3 작업 화면 보임 고리 뺌 | runtime_defer ③ 3건 |
| main 「만드는 동안 장부 지움」(옛 꼴) | runtimedefer.test ① · ③ |

### 3-1. 팩 단계(ci-branch.yml) — 측정 중/결과

토큰 = ci-branch.yml 「팩 검체 — release pack-artifacts 파이썬 루프 그대로」(154) + 맥 「레인·상태 격리군」(4 · 같은 env) + 「자원 게이트·함대CPU·역할 좌석」(5) + 「수용 검체 4종」(4 · `CYS_STATE_DIR`·`JAVIS_ROOT` 더함) = 167 · 파이썬 3.13(homebrew · CI = 3.12) · 빈 HOME · 시험마다 새 `CYS_PACK_DIR`.
**이 가지의 팩 바이트 = 기준선과 같음**(`git ls-files -s cysjavis-pack` 해시 두 작업트리 동일 · `git diff dea2e1853 -- cysjavis-pack` 빈칸).

| 결과 | 수 |
|---|---|
| 루프 1회(부하 25~35) | **163 통과 · 4 붉음** |

붉은 4건 — 운영 공지 master#1fe5fc05 ②대로 부하 낮을 때 단독 재실행 · 기준선 작업트리(cys-1116-integ = dea2e1853 · 깨끗함)와 대조:

| 시험 | 루프(부하 ~30) | 이 가지 단독 재실행(부하 · 결과) | 기준선 단독(부하 · 결과) | 판정 |
|---|---|---|---|---|
| test_hook_r34 | 붉음 WIN-2 「시한 초과 → 지연 고지」 3.05초 | 13.6 붉음 RCF-3(같은 시한 1초 계열 · 3.08초) → **7.5 초록** | 12.6 붉음 **RCF-3 · 3.32초(같은 사유)** | 부하성 시한 흔들림(기준선도 같은 사유로 붉음) |
| test_role_authority_shell | 붉음 K1·K2b-3(dept 거부 0 · 조회 0) | 11.0 **초록** | — | 1회 흔들림 |
| test_resource_gate_product_cpu | 붉음 9b·9c(`ps timeout 1.5 s` ↔ 기대 `deadline 3.0 s`) | 7.3 붉음(같은 사유) → 17.2 초록 → 11.1 초록 | 13.9 초록 · 16.4 초록 · 7.5 초록 | 시한 흔들림(ps 1.5초 문턱) |
| test_capgate_hook_shell | 붉음(캐시 파일 없음) | 12.5 붉음(fastpath·stale 캐시 · 데몬 조회 기록 빈칸) · 13.4 초록 · 12.5 붉음 · 10.6 붉음(90초 시한 초과 3건 · 다른 하위 시험) | 11.7 초록 · 16.2 초록 · 8.4 초록 | **원인 미확정** — 매번 다른 하위 시험 · 훅 안 `cys_timeout_run 2`(2초 시한) 갈래 · 시험 PATH 에 실 cys 없음 · 남은 프로세스 0 · 팩 바이트 같음 → 코드 원인은 아니라고 보나 이 작업트리 3/5 붉음 · 기준선 0/3 이라 「환경 탓 확정」이라 쓰지 않는다(독립 검증·CI 에서 확인 권함) |

## 3-2. codex 1R(적대 · gpt-5.6-sol high · 검토 대상 0125a8957 · 깨끗한 사본 폴더 · 개인정보 관문 통과)

판정 원문 = **BLOCK**(blocking 1 · major 3 · minor 2) · 원문 파일 = 스크래치 `s2/rev/codex-r1.out`. 처분:

| # | 지적 | 처분 | 근거 |
|---|---|---|---|
| B1 | 자리표 판정을 한 번에 내리고 closePane 을 차례로 기다려, 앞 자리 닫기를 기다리는 사이 뒤 자리에 생긴 출력을 못 보고 닫을 수 있다 | **수용 · 고침**(80747b11c) | 닫기 직전 그 자리를 지금 화면 줄 수·손댐·편성·트리로 `decidePlaceholders` 재판정 · 닫기 아니면 건너뜀 · 정적 핀(ingest.test 「닫기 직전 재판정」) |
| M2 | makePane 이 중간에 던지면 등록 전 xterm·리스너가 안 치워진다 | **수용 · 고치지 않음 → 📌** | 원작자 함수 본문의 종전 결함(작업 화면 3초 틱도 같은 꼴 — 종전은 틱마다 무제한 재시도 = 무제한 누수 · 미룬 길은 3회 상한). 고치면 makePane 본문(원작자 · ~670줄)을 바꿔야 함 |
| M3 | 3회 실패 뒤 좌석이 트리에만 남아 영구 「(없음)」 | **수용 · 고침** | 장부 유지(= 붙은 좌석 · 재입양 0) · 자동 재시도 상한 3 · 작업 화면 재진입 때 `retryFailedRuntimes` · runtimedefer.test ③ |
| M4 | bootViews 전 사건 · 본부 slug 모를 때 사건 유실 | **부분 수용** | boot 전 = 상한 32 버퍼 → boot 직후 1회 흘림(ingest.test ④) · slug 모름 = 종전에도 버림(그때는 대화 화면이 켜질 때마다 slug 재조회 · 지금은 main.ts 기존 재조회 길 하나) → 📌 |
| m5 | 첫 진입 뒤 키보드 포커스 없음 | **수용 · 고침** | ensureSeatRuntimes 가 보이는 좌석을 만든 뒤 종전 틱과 같은 포커스 회수 |
| m6 | 입양 후보를 먼저 정해, await 사이 새로 입양 가능해진 좌석은 한 틱 늦다 | **기록(고치지 않음)** | codex 도 「위험보다 최대 한 틱 지연」으로 봄 · 반대 방향(낡은 후보)은 집행 재확인이 막음 · 재생(await 없음) 결과 같음 |
| (missing) | 견본 덤프가 검토 폴더에 없어 재생 미검증 | 사실 | 검토 사본에 docs 를 안 넣었음 — 이 작업트리에서는 재생 시험 통과(§3) |

고친 뒤(80747b11c) codex 재검토 = **안 함**(2R 은 master 판단 · 고친 4건의 시험은 위 표).

## 3-3. codex 2R(master 편성 · 원문 `~/axdev/master/reports/verify/codex-1120/s2-r2.md` · BLOCK) 처분 — f49760ff0 · 고침 요청 [master#fc00501e]

| # | 지적 | 처분 | 시험 · 뮤턴트 |
|---|---|---|---|
| 2R-B | 미룬 좌석은 첫 붙기 때 데몬의 「지금 화면」만 받아, 대화 화면 동안 스크롤로 넘어간 출력이 작업 화면 기록에서 사라짐 | **고침 · 우월안 = 데몬이 이미 가진 기록 재생**: 데몬은 좌석마다 완성 줄 FIFO(스크롤백 · `SCROLLBACK_LINES` 10,000)와 단조 줄 커서를 이미 갖고 `surface.read_text {since_line}` 델타로 내준다 → **데몬 변경 0**. 미룰 때 목록의 `line_count`(커서)를 장부에 적고, 런타임을 만들 때 스트림을 붙이기 **직전** 새 Tauri 명령 `seat_history`(우리 파일 viewcore.rs · main.rs 등록 1줄)로 「커서 − 화면 행 수」부터 받아 xterm 에 먼저 쓴다(지금 화면에 다시 그려질 마지막 화면 행 수만큼은 빼서 겹침 방지 · 화면 행 수만큼 빈 줄로 스크롤백에 밀어 올림 · 상한 5,000줄 = xterm 스크롤백) → 그다음 데몬 스냅숏. **§9-4 「대화 화면 출력 흐름 0」 그대로**(대화 화면 동안 스트림·버퍼 0 · 첫 진입 때 좌석당 조회 1). 한계(정직): FIFO = **완성 줄 글자만**(색·굵기 없음 · 제자리 다시 그리기(TUI) 화면은 줄로 안 남음 · 10,000줄 넘게 지나가면 앞부분 잘림 · 화면 행 수 빼기는 줄바꿈 접힘 때문에 근사) | runtimedefer.test ①(조회 인자·쓰는 꼴·스트림보다 먼저) · ①-b(커서 모름 = 조회 0) · runtime_defer_gate ③ 「기록 조회 = 미룬 좌석마다 1회 · 스트림보다 먼저」 · cargo viewcore `seat_history_tests` · 뮤턴트 MX3(겹침 빼기 제거 → ① 붉음) |
| 2R-M1 | makePane 을 기다리는 사이 대화 화면으로 돌아가도 start_surface_stream 이 나감 | **고침**: makePane 선택 인자 `beforeStream`(듣기 등록 뒤 · 스트림 시작 직전) — `workRuntimeWanted()` 거짓이면 기록도 안 묻고 붙지 않음 → makePane 이 만든 것을 치우고 표지 오류 → 장부 유지 · 시도 횟수 안 셈 · 다음 작업 화면 진입 때 다시 | runtimedefer.test ② · 뮤턴트 MX1(첫 확인 뺌 → ② 붉음) · MX6(안 세기 뺌 → ② 붉음) |
| 2R-M2 | 재진입마다 재시도 횟수 초기화 = makePane 부분 생성 누수 무한 증폭 | **둘 다 고침**: ① 누수 자체 — makePane 붙기 구간(attach_surface → 듣기 등록 → beforeStream → start_surface_stream)이 던지면 `dropPartial`(듣기 2·cancelSendFail·xterm dispose·DOM 제거) 뒤 다시 던짐(작업 화면 입양·새 창의 같은 실패도 이제 안 샘 · 성공 경로 호출 순서 그대로) ② 상한을 실행 전체 기준으로 — 좌석당 시도 9회(`DEFERRED_TOTAL_MAX` · 재진입이 되돌리는 것은 3회 묶음뿐) | ingest.test 「makePane 부분 생성 정리」 정적 핀(순서 try < beforeStream < start < catch < panes.set) · runtimedefer.test ③ · 뮤턴트 MX4(정리 뺌 → 핀 붉음) · MX2(전체 상한 뺌 → ③ 붉음) |
| 2R-m | 첫 진입 포커스가 전체 트리 첫 좌석(묶음 탭·확대로 숨은 좌석일 수 있음) | **고침**: 보이는 보기 트리(`wsViewTree`) 첫 좌석 | ingest.test 정적 핀 · 뮤턴트 MX5 → 붉음 |

원작자 파일 바뀐 줄(2R 몫): `ui/src/main.ts` makePane — 머리(선택 인자 1 · 앞에 타입·표지 정의) · `dropPartial` 정의 · attach_surface 줄에 `.catch(dropPartial)` · `un1`/`un2` const → let · 듣기 등록 앞 `try {` · start_surface_stream 앞 `beforeStream` 1줄 · 뒤 `catch` · `unlisten` 배열 타입 단언. `src-tauri/src/main.rs` generate_handler 이름 1줄(`viewcore::seat_history`). 데몬 0.

## 3-4. 독립 검증 2270(REVISE 국소 1 · 원문 `~/axdev/workers/cysr-1116-s2-verify-1119/VERDICT.md`) 처분 — d56912914 · [master#2291dec4]

| # | 지적 | 처분 | 시험 · 뮤턴트 |
|---|---|---|---|
| F1 | 대화 화면 시작 + 저장 배치 복원 → 작업 화면 첫 진입 포커스 좌석 0(start() 끝 setFocus 가 런타임 없는 좌석에 불려 번호만 잡힘 → 회수 조건 건너뜀) | **고침**(codex 2R minor 와 한 고침): ensureSeatRuntimes 가 이번에 만든 좌석을 기억하고, 포커스 번호가 그 좌석이면 런타임을 만든 뒤 `setFocus` 를 다시 부름(표시·키보드 포커스) · 포커스가 이미 런타임 있던 좌석이면 건드리지 않음(탈취 0) | runtimedefer.test 「첫 진입 포커스」 3건(F1 · 보기 트리 첫 좌석 · 탈취 0) · 뮤턴트 MF1(다시 주기 뺌 → F1 붉음) · MX5(전체 트리 → 보기 트리 시험·핀 붉음) |
| F2 | B1(자리표 닫기 직전 재판정) 시험이 소스 핀뿐 | **행동 시험 추가**: roleactivity.test 하네스(실제 refreshPaneTitles 본문)로 자리표 2개 · 앞 자리 closePane 을 기다리는 사이 뒤 자리 화면 줄 1 → 12 → 뒤 자리 닫지 않고 장부에 남음 · 대조군(출력 없음) = 둘 다 닫음 | 뮤턴트 MF2(재판정 결과 무시) → 행동 시험·핀 둘 다 붉음 |
| F3·F4·F6 | 관찰(설계대로) | 기록 — F3(대화 화면만 쓰면 빈 탭 자리표 셸이 회수 안 되고 남음) 은 📌 | — |
| F5 · makePane 누수 | 검증 「진입 1회당 3건 상한」 · codex 「왕복마다 → 실행 전체 무한」 | **둘 다 닫음**(2R-M2): 누수 자체 정리 + 실행 전체 상한 9 | §3-3 |
| test_capgate_hook_shell | 검증 판정 = 환경성(훅 2초 마감 · 기준선도 2/5 붉음) | 이 갈래 고칠 것 아님(master) | — |

## 3-5. 2R·독립 검증 처분 뒤 시험(머리 d56912914 · 부하 4~16)

| 대상 | 결과 |
|---|---|
| bun test(ui) | **3781 · 89 skip · 0 fail**(1R 처분 뒤 3770 → +11 새 시험) |
| tsc | rc 0 |
| `cargo test -p cys-app --bins`(CI 단계와 같은 준비 · `--test-threads=1` · CARGO_BUILD_JOBS=4) | **349 통과 · 0 실패 · 2 ignored**(새 `viewcore::seat_history_tests` 포함 · 기준선 수 미측정) |
| 화면 게이트 14종(13 + runtime_defer) | **14종 PASS** · 통과 줄 수 기준선과 같음(race 109 · focus 73 · seatrows 76 · pillar 78 · seatgroup 9 · rolereuse 12 · nodept 17 · restart 7 · hidden_block 19 · tickrec 34 · chat 59 · confirm 37 · stty 8) · tickrec OFF 대조 = 기준 번들과 바이트 같음(invoke 1088 · sha `308dd2b91f9a`) · runtime_defer ③ 「기록 조회 = 미룬 좌석마다 1회 · 스트림보다 먼저(13건)」 |
| 뮤턴트(2R·검증 몫) | MX1~MX6 · MF1 · MF2 · MX5 = 전부 해당 시험 붉음 |

## 3-6. codex 3R(BLOCK · 원문 `~/axdev/master/reports/verify/codex-1120/s2-r3.md` 두 판) 처분 — 후임 worker-1116s2b · [master#cca94b88] · 덧붙임 [master#edc48c75] · 이음매 설계 승인 [master#b4d5c092]

**이음매를 결정론 커서로 — 단위를 화면 쪽으로 맞춤(데몬 변경 허용 범위 · master 승인).** 조사 결과 데몬 스트림 = 날 PTY 바이트 + attach 때 화면 스냅숏(물리 행) · `read_text` 커서 = 줄바꿈으로 자른 글자 FIFO(논리 줄) — 두 단위가 달라 순번을 달아도 FIFO 끝과 스냅숏 사이를 결정론으로 못 뺀다. 그래서 데몬 vt100 파서가 이미 갖고 있던 「화면 위로 밀려난 물리 행」(파서 스크롤백 10,000행)에 단조 행 커서를 달고, **같은 파서 락 안에서** 구독 · 커서 뒤 밀려난 행(색 포함) · 지금 화면 스냅숏을 한 번에 떠 한 스트림으로 차례로 쓴다. UI 쪽 버퍼·겹침 제거가 필요 없다(데몬 락이 이음매를 보장).

| # | 지적(3R) | 처분 | 시험 · 뮤턴트 |
|---|---|---|---|
| B1 | 기록 조회와 붙기가 원자 절단이 아님(그 사이 출력 손실) · `term.rows` 와 데몬 화면 높이 차로 빠짐·겹침 | **고침** — `surface.attach {history_since, history_rows}`: 데몬 한 락 = 구독 + 밀려난 행 + 스냅숏 · 받는 쪽 행 수만큼 줄 내림(H 행을 H−1 줄바꿈으로 잇고 R 줄 내림 = 정확히 H 행이 스크롤백으로 · 빈 줄 0) · 옛 `seat_history`(FIFO 글자 · 화면 행 수 빼기) 걷음 | cysd `attach_history_tests` ① 이음매(받는 쪽 행 수 24·35·60 · 색 · 접힘 · 커서 뒤 300줄 → 스크롤백 바이트 = 서버 밀려난 행 · 표지 빠짐·겹침 0) · ⑤ 실제 좌석(reader 스레드 · run_attach · 목록 커서 → 0..300 한 번씩) · 뮤턴트 RM1 행 커서 증가 뺌 · RM2 줄 내림 뺌 |
| B2 | 기록 실패·시한·빈·모르는 커서 = 조용히 넘어감 | **고침** — 결과 칸(ok · truncated · unknown_cursor · timeout · error · not_attached · unsupported · 커서 모름)으로 판정 → ok 아니면 좌석 화면 맨 위(제목 줄 아래) 「이전 출력 일부를 불러오지 못했어요」 + 사건 기록(`seatHistoryEvents` · console.warn). 일시 실패(timeout·error·not_attached)만 「다시 불러오기」(누르면 xterm 비우고 같은 커서로 다시 붙음 = Tauri 가 옛 손잡이 abort · 데몬이 다시 한 락으로) + 다음 작업 화면 진입 때 자동 재시도. 잘림·모르는 커서·구 데몬 = 다시 해도 같으므로 안내만 | runtimedefer.test ②(3R blocking) 2건 · 뮤턴트 UM4(다음 진입 재시도 뺌) · UM7(잘림 안내 0) · cysd ② 잘림(10,000 밖 · 상한) · ③ 모르는 커서(새 파서 · RIS · 앞선 커서) |
| M1(old) | start_surface_stream 을 기다린 **뒤** 화면 재판정 없음 | **고침** — makePane `afterStream`(start 반환 뒤 1회) · 거짓이면 `stop_surface_stream`(새 Tauri 명령 · 우리 파일 viewcore.rs) + 치움 + PANE_STREAM_UNWANTED(횟수 안 셈 · 장부 유지) | makepane.test ③ · runtimedefer.test ③ · 뮤턴트 UM3 |
| M2 | 9회 실패 뒤 total 영구 차단 · 장부 「붙음」 고착 | **고침** — 실행 전체 상한(total) 걷음 · 자동 재시도 = **작업 화면 진입당 3회** · 진입마다 retryFailedRuntimes 가 되돌림(영구 차단 0). 부분 생성 누수는 아래 M3 가 막으므로 상한은 누수 방어가 아니라 실패 폭주 억제 | runtimedefer.test ④(5번 진입 = 15번 시도 · 장부 유지) · 뮤턴트 UM6 |
| M3(new) | dropPartial 이 term.open 뒤 설정 끝에서야 설치 · 스트림 시작 뒤 panes.set 전(ResizeObserver) 실패 누수 | **고침** — makePane 첫 줄부터 되돌림 목록(`undo`) + 본문 전체 try/catch(역순 되돌림): DOM(첫 createElement 직후) · xterm(new Terminal 직후 · open 전) · 보내기 실패 타이머 · 듣기 2 · 스트림 정지(start 뒤 · 옛 시도면 안 얹음) · 관찰자+타이머 | makepane.test ①(실제 makePane 본문 · term.open 직후 던짐 · 스트림 뒤 ResizeObserver 던짐) · ingest.test 꼴 핀 · 뮤턴트 UM1 · UM9 |
| M4(old) | 좌석 파괴가 진행 중 makePane 을 못 막음 → 늦게 끝난 옛 시도가 새 런타임 덮기 · catch 가 새 런타임 파괴 | **고침** — 좌석별 세대(`paneGen` · destroyPaneRuntime 마다 올림) · makePane 은 시작 값을 쥐고 attach·스트림 전·스트림 뒤마다 대조 → 바뀌면 제 것만 치우고 PANE_STALE(같은 (소켓, 좌석) 스트림 손잡이는 새 시도의 것일 수 있어 멈추지 않음) · ensureSeatRuntime catch 에서 destroyPaneRuntime 걷음(makePane 이 스스로 치움) | makepane.test ②(attach·start 두 자리에서 멈춘 옛 시도) · runtimedefer.test ⑤(파괴 → 재입양 → 옛 시도 늦게 끝남) · 뮤턴트 UM2 · UM5 · UM8 |

**master 승인 조건(b4d5c092) 대조**

| 조건 | 결과 | 근거 |
|---|---|---|
| ① 인자 없는 소비자 ack·바이트 같음 시험 | 통과 | cysd `attach_without_history_is_byte_identical_to_before`(ack 본문 = `{id,ok,result:{attached}}` · 첫 바이트 = 스냅숏만) · `dispatch_parses_history_params_only_when_given`(인자 없음 = history None) · 뮤턴트 RM3 |
| ② vendor/vt100 = 더하기만 · 패치 장부 1줄 | 통과 | `git diff --numstat` vendor = +94/−0(장부 1줄 포함) · `vendor/vt100/CYS-PATCHES.md` 표 1행 |
| ③ 10,000줄 넘게 밀려남 = 잘림 → 안내 | 통과 | cysd ② · UI 잘림 = 안내 줄(다시 불러오기 없음) · 뮤턴트 RM5 · UM7 |
| ④ 파서 세대 바뀜 = 모르는 커서 → 안내 + 붙기 | 통과 | 세대 = 격자 생성마다 새 번호(파서 교체·RIS) · 데몬 재기동 = 프로세스 전역 번호 1부터 → 하위 13비트 일치 확률만 남음(아래 한계) · 모르는 커서 = 기록 없이 스냅숏으로 붙고 안내 · 뮤턴트 RM4 |
| ⑤ 락 안 작업 상한 · 윈 ConPTY 같은 파서인가 | 통과(측정값 아래) | 락 안 = 이 좌석 파서 락만(좌석마다 파서) · 락 안 작업 = 행 **사본**뿐(최대 `ATTACH_HISTORY_MAX_ROWS` 5,000행 = UI xterm 스크롤백) · 서식·쓰기는 락 밖(첫 판은 락 안 서식 = 디버그·부하 40 에서 5,000행×200칸 1.25초 실측 → 사본/서식 분리) · 시험 `attach_history_under_lock_is_capped_at_max_rows`(12,000행 → 5,000 · 잘림) · ConPTY = 같은 reader 스레드(`state.rs` reader 는 플랫폼 cfg 없음 · `process_chunk_isolated` + `mirror_screen_modes` 한 자리) — 정적 확인만(윈 실기 = 측정 대기) |

**원작자·데몬 파일 바뀐 줄**(데몬 변경 = 이 갈래 범위 확대 · 브리프 「데몬 변경 허용」)

| 파일 | 바뀐 것 |
|---|---|
| `vendor/vt100/src/grid.rs` | `NEXT_SCROLL_EPOCH` 전역 · 필드 `scroll_epoch`·`scrolled_rows` · `new` 에 두 값 · `scroll_cursor()` · `scrollback_rows_since()` · `scroll_up` 스크롤백 push 뒤 `self.scrolled_rows += 1;` 1줄 |
| `vendor/vt100/src/row.rs` | `width()`(pub(crate) · 기존 `cols()` 감쌈) |
| `vendor/vt100/src/screen.rs` · `lib.rs` | `scroll_cursor()` · `scrollback_snapshot_since()`(행 사본) · `scrollback_formatted_since()` · `ScrollbackSnapshot`(start·len·truncated·formatted) · lib.rs `pub use` 1줄 |
| `src/bin/cysd/state.rs` | `Surface.screen_cursor: AtomicU64` + 생성자 1줄 · 생성 직후 `mirror_screen_modes` 1회 · `mirror_screen_modes` 에 커서 미러 2줄 · `pack_screen_cursor`/`unpack_screen_cursor`(세대 하위 13비트 << 40 \| 행 40비트 · JS 정확 범위 안) |
| `src/bin/cysd/handlers.rs` | `Reply::Attach` 에 `history: Option<(u64,u16)>` · `surface.attach` 팔 = `history_since`·`history_rows` 선택 읽기 · `surface.list` 줄 `screen_cursor` 1칸 · `surface.create` 응답 `screen_cursor` 1칸 |
| `src/bin/cysd/main.rs` | `Reply::Attach` 분기 인자 1개 · `run_attach(.., history)` — 락 안에서 `attach_history_snapshot`(행 사본만) · 락 밖 `attach_history_format`(서식) · ack `result.history` 칸 · 기록 바이트 + 줄 내림을 스냅숏 앞에 · `ATTACH_HISTORY_MAX_ROWS` · `AttachHistory` · `attach_history_snapshot()`·`attach_history_format()` · 시험용 `attach_history()` · 시험 모듈 등록 1줄 |
| `src-tauri/src/main.rs` | `start_surface_stream` 선택 인자 `history_since`·`history_rows` · 반환 `Result<Value>`(인자 없음 = null = 종전 JSON 같음) · 인자 있으면 `viewcore::attach_with_history` 손잡기 → 성공 = `pump_surface_stream` · 실패 = 종전 길로 붙고 결과 칸 반환 · generate_handler `viewcore::stop_surface_stream` 1줄(옛 `viewcore::seat_history` 1줄 걷음) |
| `src-tauri/src/viewcore.rs`(우리) | `attach_with_history`(5초 시한) · `pump_surface_stream` · `stop_surface_stream` · 옛 `seat_history`·`seat_history_params`·그 시험 걷음 |
| `ui/src/main.ts` | 장부 꼴(total 걷음 · cursor = `screen_cursor`) · `DEFERRED_TRIES_MAX` · `seatHistoryArgs`·`seatHistoryVerdict`·`showSeatHistoryNotice`·`retrySeatHistory`·`seatHistoryEvents`·`seatHistoryRetry` · ensureSeatRuntime(afterStream · catch 에서 destroy 걷음) · retryFailedRuntimes(기록 재시도) · `PANE_STALE`·`paneGen`·`bumpPaneGen` · makePane(첫 줄 undo + try/catch · 세대 대조 3자리 · afterStream · start 인자 펼침) · destroyPaneRuntime 2줄 · 미룸 3자리 커서 = `screen_cursor` |
| `ui/src/style.css` | `.pane-history-gap` 2규칙 |

**시험(머리 = ac6d05d16·f2b3530a8 · 부하 7~179 · 다른 좌석 동시 빌드)**

| 대상 | 결과 |
|---|---|
| bun test(ui) | **3789 · 89 skip · 0 fail**(3R 전 3781 → +8 · 새 makepane.test 5 · runtimedefer 재작성 15) |
| tsc `--package typescript@7.0.2` | rc 0(음성 대조: 고치기 전 `rejects`·`expect.any` 타입 오류 5건 rc 1 로 잡힘) |
| cargo cysd `attach_history_tests` | **8 통과 · 0 실패** · 측정(디버그 · 부하 179): 5,000행×200칸 색 = **락 안 사본 40.5 ms** · 락 밖 서식 1.36 s · 985,004 바이트 · 뮤턴트 RM1~RM5 = 해당 시험 붉음 |
| cargo cysd 전체(`--test-threads=3` · nice 15 · 부하 80~179 · 30분) | **3336 통과 · 6 붉음 · 17 ignored** — 6건(`a_spawned_pty_child_does_not_inherit_the_lock_fd` · `reclaim_commit_aborts_on_every_race_without_partial_effect` · `v116_send_text_agent_launch_passes_vacant_seat_guard_only_for_seat_bin` · `seatkeep_input_ack_stall_ends_seat_when_consumer_never_resumes` · `seatkeep_input_ack_waits_while_consumer_runs_and_stdin_unread` · `k17_refuse_mode_return_raises_settle_marker_but_cancel_key_does_not`) **전부 단독(`--exact --test-threads=1` · 부하 53) 초록**. 6건 모두 시한·경합 성격(seat_proc 입력 확인 대기 · 락 fd 병렬 fork · 재입양 경합) · 바뀐 코드(attach 팔·list 1칸·create 1칸·mirror 2줄·vt100 더하기)와 경로가 닿지 않음 — 단 **기준선 전체 실행 대조는 안 함**(부하) → 「환경성 확정」 이라 쓰지 않는다 · 독립 검증·CI 에서 확인 권함 |
| cargo `-p cys-app --bins`(CI 준비 그대로) | **348 통과 · 0 실패 · 2 ignored**(옛 seat_history 시험 1 걷음 = 349 → 348) |
| 화면 게이트 14종 | **14종 PASS** · [PASS] 줄 수 기준선과 같음(race 108 · focus 72 · seatrows 75 · pillar 77 · seatgroup 8 · rolereuse 11 · nodept 16 · restart 6 · hidden_block 18 · stty 7 · RESULT 줄 제외 셈 = §3-5 의 수 − 1) · tickrec 34 · chat 59 · confirm 37 · runtime_defer 23 |
| tickrec OFF 대조(작업 화면 회귀 0) | 기준 번들(dea2e1853 을 이 회차에 다시 빌드) = 새 번들 바이트 같음 · invoke 1088 · sha `308dd2b91f9a`(§3-5 와 같은 값) · 대조군 같음 · 음성 대조 다름 |
| runtime_defer ③ | 붙기 = 미룬 좌석마다 화면 행 커서 인자(13건 · 커서 {0 새 셸, 7 대역}) · 안내 줄 0 · 따로 묻는 기록 조회 0 · 흐름 13 · ① 대화 화면 = start 0 · attach 0 그대로 |
| UI 뮤턴트 UM1~UM9 | 전부 해당 시험 붉음(§ 위 표) |

## 4. 내가 내린 판단(지시에 없던 것 · master 확인 후보)

1. **「작업 화면이 안 보임」 판정 = 작업 화면 어댑터의 mount/unmount** — 시작 값 = 고른 화면(pickView)이 작업 화면인가. 작업 화면으로 시작하는 기동(1.1.16 기본 = 모든 설치)은 처음부터 참이라 종전 흐름과 한 줄도 다르지 않다. 숨김 → 보임으로 바뀔 때만 main.ts `render()` 를 부른다(처음 판은 작업 화면 시작 때도 불러 render 가 한 번 더 돌았다 — 자기 검토에서 잡아 고침).
2. **작업 화면에서는 보이지 않는 탭 좌석도 종전처럼 즉시 런타임** — 설계 §2-3 「작업 화면으로 바꾸면 보이는 부서부터 · 나머지는 그 탭을 열 때」는 **대화 화면에서 미룬 좌석**에만 적용했다. 작업 화면 입양까지 미루면 작업 화면 동작(숨은 부서 좌석 출력 흐름 · hidden_block 게이트)이 바뀐다 — 「작업 화면 회귀 0」 우선.
3. **판정 순수 함수는 소켓 단위**(`decideSockPre` · `decidePlaceholders`) + 재생용 접기(`decideTick`) — 집행이 소켓마다 await 를 끼므로(입양 makePane · 자리표 closePane) 한 틱 전체를 미리 판정하면 종전 「그 순간 값」과 갈린다. 집행 자리 재확인(낡은 판정 막이)은 판정을 두 벌 만드는 것이 아니라 종전 반복문이 매 좌석 보던 값을 그 자리에서 다시 보는 것 — 재생(await 없음)에서는 같은 결과.
4. **decideSockPre 안 모형 사본 갱신을 걷음** — 뮤턴트 M5·M7(퇴거·입양을 사본에 반영 안 함)이 아무 시험도 안 붉혔다. 따져 보니 결과에 닿을 수 없는 코드(퇴거 = 목록에 없는 번호 · 쓸기 = 끝난 좌석 · 같은 소켓 목록 번호 = 겹침 없음) → 단순성.
5. **persist.ts(§5-3 판 번호 `v` 칸)는 만들지 않음** — 조각 2 행의 「persist 저장」 = §2-1 「저장 시점」(그리기와 무관하게 저장)으로 읽었다. 저장소 꼴 변경(`v` 칸 · 옛 꼴 변환)은 1.1.14 건너뛰기 실기가 걸린 조각 8 성격 → 📌.
6. **대화 화면에서 붙인 좌석의 열 몫** — 숨은 화면은 폭 0 이라 좌열 몫이 기본값(25%)으로 짜인다(formation.defaultLeftShare 폭 0 = 기본값 · 터짐 없음). 노트북 90칸 규칙은 작업 화면에서 다음 배치 때 적용 → 📌 관찰.

## 5. 치명 위험 4군 점검

| 군 | 이 조각 | 근거 |
|---|---|---|
| ① 폭주 큐 | 줄임 | 대화 화면 = attach_surface·start_surface_stream 0 · 새 RPC 0 · 새 타이머 0 · 구독 2 → 1 · default_socket_slug 재조회 0 |
| ② 무clear | 닿지 않음 | 좌석 입력줄·PTY 쓰기 경로 무접촉 |
| ③ 자가치유 전멸 | 막음 | 판정 재생 = 같음 · 고리 한 벌(화면과 무관 · setInterval 1 그대로) · 대화 화면 1시간 틱 1,200 · 겹침 0 · 저장 이어짐 · 전환 100회 뒤 틱 이어짐 |
| ④ 전 pane 사망 | 막음 | 첫 진입 = 보이는 탭 전부 xterm · 「(없음)」 0 · resize = 보이는 좌석 × 1 · 런타임 다시 만들기 0 |

## 6. 📌 덧붙임(실행 안 함)

- (독립 검증 F3) 대화 화면만 쓰는 동안 빈 탭 자리표(맨 셸 1개)가 데몬에 남는다(런타임 없음 = 화면 줄 수 모름 = 닫지 않음 규칙) — 데몬 쪽 출력 흔적(`line_count`)으로 판정할지 설계 판단.

- (codex 1R M4 나머지) 본부 slug 를 main.ts 가 기동 때 못 받으면 대화 화면 두 처리기가 사건을 버린다 — main.ts 재조회 길(eventSock 해석 실패 때)에 기댄다. 확실히 하려면 viewsIngest 에서 slug null 이면 1회 재조회(작업 화면 invoke 가 늘어 tickrec OFF 대조가 바뀜 — 판단 필요).
- (codex 1R m6) 입양 후보 선계산의 한 틱 지연 — 엄격 동치가 필요하면 await 뒤마다 다시 판정.

- ~~(codex 1R M2) F20 ①~~ → **2R 에서 고침(§3-3 2R-M2)** · 옛 기록: `makePane` 이 중간(attach_surface 등)에서 던지면 그 전에 만든 xterm·리스너는 `panes.set` 전이라 파기 대상에 안 잡힌다(원작자 함수 본문 · 종전부터 같은 꼴). 고치려면 makePane 본문에 정리 목록 — 원작자 함수 본문 변경이라 별 티켓 권함.
- 설계 §5-3 persist.ts(판 번호 · 단일 작성자 모듈) — 조각 8 과 함께.
- 숨은 화면에서 짠 좌열 몫(§4-6) — 작업 화면 첫 진입 때 한 번 다시 맞출지(사용자 배치 존중과 충돌 · 설계 판단).
- 실물 측정 대기: 좌석 12개 대화 → 작업 첫 진입 시간(맥·윈) · 웹뷰 메모리(대화 1시간 vs 작업 1시간) · 웹뷰 멈춤 주입 → 데몬 자가치유(§2-2 게이트⑤) · Tauri 박동 `views_tick_beat`(§2-2 장치 — 이 조각에서 안 만듦 · 러스트 변경 = 브리프 「데몬 변경 없음」 밖은 아니나 범위 판단 필요).

- **(3R 회차 · 한계 정직)** ① 파서 세대는 하위 13비트만 커서에 담는다 — 미룬 사이 파서가 정확히 8,192의 배수 번 갈리면(패닉 격리·RIS) 모르는 커서를 못 알아챈다(현실 0에 가까움 · 더 줄이려면 커서를 문자열로). ② 데몬 vt100 은 ED 3(`ESC[3J` = 스크롤백 지우기)을 처리하지 않는다(상류 그대로 · `screen.rs ed` 의 「unhandled」) → 대화 화면 동안 좌석이 스크롤백을 지웠어도 다시 그리기에는 지운 행이 나온다(실시간 xterm 은 지웠을 것). 고치려면 vt100 에 ED 3 = 스크롤백 비움(행 커서는 유지 → 「잘림」) — 파서 동작 변경이라 더하기만 조건 밖 → 판단 필요. ③ 밀려난 행은 행마다 `\r\n` 으로 이어 쓰므로 접힌 줄의 「이어짐」 표지가 xterm 에 안 남는다 — 같은 폭이면 보이는 꼴 같음 · 폭을 바꾸면 그 행들은 다시 접히지 않는다. ④ 다시 불러오기 = xterm 비우고 다시 붙기 — abort 된 옛 스트림이 이미 내보낸 사건이 웹뷰 큐에 남아 있으면 그 몇 바이트가 비운 화면 맨 앞에 끼일 수 있다(스트림 세대 표지가 없음 · 드묾). ⑤ 진입당 3회를 다 쓰면 그 진입 동안은 「(없음)」 칸 그대로 — 다음 진입 때 다시(느린 자동 재시도를 둘지 판단). ⑥ 「사건 기록」 = UI 안 고리(`seatHistoryEvents` · 64) + console.warn 뿐 — 영속 UI 사건 원장이 없다. ⑦ 윈 ConPTY = 같은 reader·파서(정적) · 실기 측정 대기.

## 7. 재현 명령

(3R 회차 더함) `cargo test --bin cysd attach_history -- --nocapture`(측정 줄) · `bun test src/views/makepane.test.ts src/views/runtimedefer.test.ts` · 게이트 파이썬 = `~/axdev/.wt/.gate-pw-venv/bin/python3` · 기준 번들 = `git archive dea2e1853 ui | tar -x` 뒤 `ui/node_modules` 심링크 + `sh build.sh` → `BASE_DIST=… tickrec_gate.py`

```sh
W=~/axdev/.wt/cys-1116-s2; cd $W/ui
bun install --frozen-lockfile && sh build.sh && bun test            # 기준 3747/88/0 → 이 가지 §3
bun x --package typescript@7.0.2 tsc -p tsconfig.check.json          # rc 0
bun test src/views/judge/tick.test.ts                                # 견본 재생
CHROME_PATH=<chrome-headless-shell> RUNTIME_DEFER_OUT=/tmp/rd.json <playwright python3> e2e/runtime_defer_gate.py   # RESULT: PASS
TICKREC_REPLAY=/tmp/rd.json bun test src/views/judge/tick.test.ts    # 분리 뒤 덤프 재생 13/0
CHROME_PATH=… BASE_DIST=<dea2e1853 번들> <python> e2e/tickrec_gate.py   # OFF 대조(기준 = 새)
```

## 8. 함정

- (3R 회차) `cargo check -p cys-app` 도 빌드 스크립트를 돌린다 → 빈 사이드카 스텁이 `target/debug/cysd`·`cys` 를 0바이트로 덮음(check 만 해도) · 끝나면 스텁 폴더 지우고 `cargo build --bin cysd --bin cys`.
- (3R 회차) 화면 게이트가 `docs/evidence-tabs-sidebar/` 에 사진을 남긴다(추적 밖) — 커밋 전 지움.
- (3R 회차) bun-env 타입에 `expect(..).rejects` · `expect.any` 없음 — tsc 붉음(bun test 는 초록) · 던진 글은 손으로 받는다(`errOf`).

- `with(scope)` 하네스(roleactivity·deptprogresswiring·closecallbacks·kbrestore·b230scroll)는 고리·render·destroyPaneRuntime 본문을 떼어 돌린다 — 그 함수에 새 자유 변수를 넣으면 대역 목록에도(관측: 넣기 전 51건 붉음).
- 소스 핀이 고리 본문의 **식별자까지** 잡는다(`await closePane(sid, ws.socket);`) — 집행 줄은 종전 이름(`sid`)을 쓰게 맞췄다.
- 이 작업트리엔 target/ 이 없어 stty 게이트(격리 cysd)가 기준선부터 못 돈다 — `cp -c -R ~/axdev/.wt/cys-1116-integ/target ./target` 뒤 `cargo build --bin cysd --bin cys`(3분 25초).
- ci-branch 팩 단계는 단계마다 env 가 다르다(우분투 루프·맥 격리군 = `CYS_PACK_DIR` 만 · 맥 자원·수용 = + `CYS_STATE_DIR`·`JAVIS_ROOT`) — 한 env 로 몰면 test_bootstrap_chain 이 `boot-last.json` 을 못 찾아 붉다(관측).
- **Tauri 빈 사이드카가 target/debug/cysd 를 덮는다**: CI 의 `cargo test -p cys-app` 준비(빈 `src-tauri/binaries/cysd-<triple>` touch)를 작업트리에서 그대로 하면 Tauri 빌드 스크립트가 그 빈 파일을 `target/debug/cysd`·`cys` 로 복사한다(0바이트 · 권한 없음) → 뒤이은 stty 게이트가 `Permission denied`(관측). cys-app 시험 뒤 빈 파일을 지우고 `cargo build --bin cysd --bin cys` 다시.
