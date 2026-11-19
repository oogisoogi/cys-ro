# HANDOFF — TICKET=cysr-1116-s2-1119 (화면 조각 2 · 3초 고리 분리 + 런타임 미룸 · 워커 worker-1116s2 · 2026-11-19~20)

- 브리프 [master#5340bbd4] `/Users/oogisoogi/axdev/master/briefs/1116-full/s2.md` · 가지 `feat/1116-s2` ← `integ/1116` dea2e1853 · 데몬 변경 0 · 러스트 변경 0 · 팩 변경 0
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

`git diff --numstat dea2e1853 HEAD -- ui/src/main.ts ui/index.html src-tauri/src/main.rs` = `main.ts +180/−81` 뿐(index.html·src-tauri 0). 덩어리 17. 설계 §8-1 목표값 +180/−140.

| 자리 | 바뀐 것 |
|---|---|
| import 묶음 | `views/index` import 에 `viewsIngest, workRuntimeWanted` · `views/judge/tick` import 1줄 |
| `refreshPaneTitles` 앞 | 보조 함수(우리): `tickWsModel` · `deferredRuntimes` · `DEFERRED_PER_TICK` · `seatAttached` · `seatInModel` · `deferSeatRuntime` · `ensureSeatRuntime` · `ensureSeatRuntimes` |
| 고리 — 유령·쓸기 | `advanceGhostStrikes`·`exitedSweepTargets` 직접 호출 → `decideSockPre(...)` 결과(`pre.evict` · `pre.sweepTargets`) 집행 · `sweepScopeFor` 줄은 그대로 |
| 고리 — 입양 | 후보 = `pre.adopt` 순서 · 집행 자리에서 같은 조건 재확인(낡은 판정 막이) · `!workRuntimeWanted()` 갈래 = 붙이기 + 장부 · 작업 화면 갈래 = 종전 본문 그대로 |
| 고리 — 자리표 | `shouldClosePlaceholder` 직접 호출 → `decidePlaceholders(...)` · 기록 줄 = `v.in`(한 벌) · 집행 전 장부·손댐·트리 재확인 |
| 고리 — 그리기 | 작업 화면 = 종전(render · 신호 · 포커스) · 대화 화면 = `saveLayout()` + 신호 · 끝에 미룬 런타임 한 틱 4개 |
| `destroyPaneRuntime` 첫 줄 | 미룬 장부 지우기 1줄 |
| `render()` | `renderWsTabs()` 뒤 미룬 런타임(보이는 탭) 1줄 |
| `newSurface` | `makePane` 을 `workRuntimeWanted()` 갈래로(F19) |
| `onDaemonEvent` 둘째 줄 | `viewsIngest(event, defaultSocketSlug);`(I3·S4-3 · 첫 문장 `const name` 은 그대로 = toastaxis 핀) |
| `start()` | `bootViews({... onWorkShown: () => render() })` · 복원 입양 `makePane` 을 갈래로(F19) |

## 3. 시험 — 기준선(dea2e1853) 대비

(아래 표는 §7 재현 명령으로 채움 — 측정 끝난 칸만 숫자 · 나머지는 「측정 대기」)

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

- F20 ①: `makePane` 이 중간(attach_surface 등)에서 던지면 그 전에 만든 xterm·리스너는 `panes.set` 전이라 파기 대상에 안 잡힌다(원작자 함수 본문 · 종전부터 같은 꼴). 고치려면 makePane 본문에 정리 목록 — 원작자 함수 본문 변경이라 별 티켓 권함.
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
