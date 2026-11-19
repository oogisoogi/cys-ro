# HANDOFF — TICKET=cysr-1116-s2-1119 (화면 조각 2 · 3초 고리 분리 + 런타임 미룸 · 워커 worker-1116s2 · 2026-11-19~20)

- 브리프 [master#5340bbd4] `~/axdev/master/briefs/1116-full/s2.md` · 가지 `feat/1116-s2` ← `integ/1116` dea2e1853 · 데몬 변경 0 · 러스트 변경 0 · 팩 변경 0
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

- (codex 1R M4 나머지) 본부 slug 를 main.ts 가 기동 때 못 받으면 대화 화면 두 처리기가 사건을 버린다 — main.ts 재조회 길(eventSock 해석 실패 때)에 기댄다. 확실히 하려면 viewsIngest 에서 slug null 이면 1회 재조회(작업 화면 invoke 가 늘어 tickrec OFF 대조가 바뀜 — 판단 필요).
- (codex 1R m6) 입양 후보 선계산의 한 틱 지연 — 엄격 동치가 필요하면 await 뒤마다 다시 판정.

- (codex 1R M2) F20 ①: `makePane` 이 중간(attach_surface 등)에서 던지면 그 전에 만든 xterm·리스너는 `panes.set` 전이라 파기 대상에 안 잡힌다(원작자 함수 본문 · 종전부터 같은 꼴). 고치려면 makePane 본문에 정리 목록 — 원작자 함수 본문 변경이라 별 티켓 권함.
- 설계 §5-3 persist.ts(판 번호 · 단일 작성자 모듈) — 조각 8 과 함께.
- 숨은 화면에서 짠 좌열 몫(§4-6) — 작업 화면 첫 진입 때 한 번 다시 맞출지(사용자 배치 존중과 충돌 · 설계 판단).
- 실물 측정 대기: 좌석 12개 대화 → 작업 첫 진입 시간(맥·윈) · 웹뷰 메모리(대화 1시간 vs 작업 1시간) · 웹뷰 멈춤 주입 → 데몬 자가치유(§2-2 게이트⑤) · Tauri 박동 `views_tick_beat`(§2-2 장치 — 이 조각에서 안 만듦 · 러스트 변경 = 브리프 「데몬 변경 없음」 밖은 아니나 범위 판단 필요).

## 7. 재현 명령

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

- `with(scope)` 하네스(roleactivity·deptprogresswiring·closecallbacks·kbrestore·b230scroll)는 고리·render·destroyPaneRuntime 본문을 떼어 돌린다 — 그 함수에 새 자유 변수를 넣으면 대역 목록에도(관측: 넣기 전 51건 붉음).
- 소스 핀이 고리 본문의 **식별자까지** 잡는다(`await closePane(sid, ws.socket);`) — 집행 줄은 종전 이름(`sid`)을 쓰게 맞췄다.
- 이 작업트리엔 target/ 이 없어 stty 게이트(격리 cysd)가 기준선부터 못 돈다 — `cp -c -R ~/axdev/.wt/cys-1116-integ/target ./target` 뒤 `cargo build --bin cysd --bin cys`(3분 25초).
- ci-branch 팩 단계는 단계마다 env 가 다르다(우분투 루프·맥 격리군 = `CYS_PACK_DIR` 만 · 맥 자원·수용 = + `CYS_STATE_DIR`·`JAVIS_ROOT`) — 한 env 로 몰면 test_bootstrap_chain 이 `boot-last.json` 을 못 찾아 붉다(관측).
