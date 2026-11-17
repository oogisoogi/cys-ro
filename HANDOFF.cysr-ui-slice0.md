# HANDOFF — TICKET=cysr-ui-slice0-1117 (cysr 화면 개편 구현 조각 0 · 워커 surface:2145 · 2026-11-17 18:5x~)

- 브리프 [master#52772539](원장 대조 성립) · 가지 `feat/ui-slice0` ← `integ/1115-r2` 36412afb(1.1.15 후보 머리) · ⛔이 조각은 1.1.15 에 넣지 않는다(다음 판 후보)
- 설계 = `~/axdev/cysr-ui-research/P2-DESIGN.md`(762fc10) §2-1 ㉠ 「시험 ① 특성 기록 먼저(조각 0)」 · §11 조각 0 줄
- 조각 0.5 = 실측 **계획서만**: `docs/ui-p2/SLICE-0.5-MEASURE-PLAN.md`(실행 0)

## 0. 한눈 요약

| 무엇 | 결과(관측) |
|---|---|
| 3초 고리(refreshPaneTitles) 입력·결과 기록기 + 카운터 | 새 파일 `ui/src/views/tickrec.ts` · 링 200칸 · 기본 꺼짐 · 스위치 = localStorage `cys-tickrec` === "1" 하나 |
| 동작 변화 0(꺼짐) | ① 정적 핀: main.ts 배선 17자리 전부 `tickRec?.…(…)`(null 이면 인자 식도 평가 안 함) ② 실행 대조: 같은 장면에서 **기준 번들(36412afb) = 새 번들** — invoke 1088건 (명령·인자) 순서 · 최종 localStorage 전부 · 화면 글자 · pane 수 · 탭 이름 sha256 같음 ③ 대조군(기준 두 번 같음) · 음성 대조(장면 1칸 바꾸면 다름) 성립 |
| 켜짐 = 200틱 기록 파일 | `ui/e2e/tickrec_gate.py` 가 200틱째 덤프를 파일로 씀(277,556 B ≤ 상한 2 MiB) · 견본 커밋 `docs/ui-p2/evidence/tickrec-200.sample.json` · 장면 원문(경로·제목·부서 이름) 0 · 켜짐도 invoke 열·저장소·화면 = 기준과 같음 |
| 원작자 파일 변경 | **끼워 넣기만 · 기존 줄 변경·삭제 0**: `ui/src/main.ts` +26/−0 · `ui/src/roleactivity.test.ts` +1/−0 · `ui/src/deptprogresswiring.test.ts` +1/−0 (§2 줄 목록) |
| 게이트 | §5 표 |

## 1. 바뀐 파일

| 파일 | 누구 파일 | 변경 |
|---|---|---|
| `ui/src/views/tickrec.ts` | 새 파일(우리) | 기록기 · 해시(cyrb53 + 기록기마다 새 소금 · 덤프에 소금 없음) · 상한(작업공간 64 · 소켓 32 · 좌석 128 · 목록 256 · 오류 16) · 기록기 예외는 안에서 삼킴(`recorderFault` 셈) |
| `ui/src/views/tickrec.test.ts` | 새 파일(우리) | 21건 — 스위치 · 한 칸 기록 · 회전 · 크기 · 개인정보 0 · 예외 삼킴 · **main.ts 배선 정적 핀 4건** · 기록기 파일 부작용 통로 0 |
| `ui/e2e/tickrec_gate.py` | 새 파일(우리) | 실제 번들 + `__TAURI__` 대역 + 가짜 시계(playwright clock · 멈춘 시계) · ON 판정 · OFF 기준 번들 대조 |
| `docs/ui-p2/SLICE-0.5-MEASURE-PLAN.md` | 새 파일(우리) | 조각 0.5 실측 계획서(실행 0) |
| `docs/ui-p2/evidence/tickrec-200.sample.json` | 새 파일(우리) | 200틱 기록 견본(조각 2 재생 원료 · 해시·길이·종류만) |
| `ui/src/main.ts` | 원작자 + 우리(섞임) | +26 끼워 넣기(§2) |
| `ui/src/roleactivity.test.ts` · `ui/src/deptprogresswiring.test.ts` | 원작자 + 우리(섞임) | 본문 떼어 돌리는 하네스의 자유 변수 대역 목록에 `tickRec: null` 1줄씩 |

`git diff --numstat 36412afb HEAD -- ui/src/main.ts ui/index.html src-tauri/src/main.rs`(설계 §8-1 측정 꼴) = `26 0 ui/src/main.ts` 뿐(index.html·src-tauri 0).

## 2. 원작자 파일 변경 줄 목록(이 가지 줄 번호 · 전부 끼워 넣은 줄)

`ui/src/main.ts`
| 줄 | 넣은 것 | 자리 |
|---|---|---|
| 326 | `import { TICKREC_KEY, tickRecFromSwitch, defaultTickRecSalt, type TickRecorder } from "./views/tickrec";` | import 묶음(placeholderclose 다음) |
| 3717~3723 | 주석 2줄 + `const tickRec … = tickRecFromSwitch({ read: () => localStorage.getItem(TICKREC_KEY), salt, expose })` | `let refreshing = false;` 바로 위 |
| 3781 | `tickRec?.gate(started, refreshing);` | `if (!started) return;` 바로 위 |
| 3792 | `tickRec?.begin(Date.now(), workspaces.map(…), ghostStrike, sweepArm !== null, placeholderSids, touchedPlaceholders);` | `refreshing = true;` 바로 아래 |
| 3813 | `tickRec?.deptsDone(workspaces.length);` | `openNewlyRegisteredDepts()` 줄 아래 |
| 3832 | `tickRec?.sock(sk ?? "", got?.value, (sid) => panes.has(paneKey(sid, sk)));` | `if (!got) continue;` 바로 위 |
| 3884 | `tickRec?.ghost(sk ?? "", sockSids, step.evict);` | `ghostStrike = step.next;` 아래 |
| 3896 | `tickRec?.sweep(sk ?? "", sweepHere, sweepSids);` | 쓸기 반복문 위 |
| 3899 | `tickRec?.sweepSid(sk ?? "", sid);` | 쓸기 반복문 안 `detachPane` 아래 |
| 3950 | `tickRec?.adoptAbort(sk ?? "", s.surface_id, !ws);` | 입양 포기 분기 `continue` 위 |
| 3958 | `tickRec?.adopt(sk ?? "", s.surface_id, s.role);` | `adopted = true;` 아래 |
| 3978~3979 | 주석 1줄 + `tickRec?.placeholderIn(sk ?? "", sid, { …shouldClosePlaceholder 인자와 같은 식… });` | 자리표 판정 `if (` 위 |
| 3993 | `tickRec?.placeholderClose(sk ?? "", sid);` | `placeholderSids.delete(sid);` 위 |
| 4002 | `tickRec?.placeholderClosed(sk ?? "", sid);` | `closePane` 성공 뒤 |
| 4026 | `tickRec?.error("sock");` | 소켓별 `catch {` 첫 줄 |
| 4038 | `tickRec?.render(adopted, layoutChanged);` | `if (adopted \|\| layoutChanged) {` 첫 줄 |
| 4048 | `tickRec?.error("tick");` | 바깥 `catch {` 첫 줄 |
| 4057 | `tickRec?.end(ghostStrike, exitedSweepArm !== null);` | finally 의 `settleSweep` 줄 아래 |
| 4075 | `tickRec?.notices(step.notices.length);` | `cwdBlockedSeen = step.seen;` 아래 |

`ui/src/roleactivity.test.ts:327` · `ui/src/deptprogresswiring.test.ts:2164` — `tickRec: null, // (cysr-ui-slice0) …` (하네스가 `with (scope)` 로 본문을 돌리므로 새 자유 변수를 대역 목록에 넣어야 ReferenceError 가 안 난다 — 1.1.11 편입 때 같은 꼴로 늘린 목록).

## 3. 내가 내린 판단(지시에 없던 것 · master 확인 후보)

1. **「기록 파일」은 시험 하네스가 쓴다** — 앱은 메모리 링 + 진단 손잡이 `window.__cysTickRec`(`dump()`·`dumpJson()`·`counters()`·`clear()`)만. 까닭: 웹뷰가 파일을 쓰려면 Tauri 명령(러스트) 신설이 필요하고 그 자리는 설계상 조각 1 의 새 파일 `viewcore.rs` 다 — 조각 0 에서 러스트·원작자 `src-tauri/src/main.rs` 를 건드리지 않으려고. localStorage 에 기록을 쌓지 않은 까닭 = 배치 저장(`cys-layout-v2`)과 같은 저장소 한도(약 5 MB)를 나눠 써 **켜짐 상태에서 배치 저장이 실패할 수 있다**(4군 ③ 쪽 위험). 실물 앱에서 덤프가 필요하면 개발자 도구에서 `copy(__cysTickRec.dumpJson())`.
2. **스위치 = localStorage `cys-tickrec` === "1"**(expertmode.ts 와 같은 「참 값 하나」 규칙). 읽기는 모듈 적재 때 1회 · 쓰기 0. 켜고 끄려면 앱 재시작(실행 중 전환 없음 — 틱 중간에 켜지는 반쪽 기록 방지).
3. **기존 줄을 바꾸지 않고 끼워 넣기만** — 소스 핀 시험(`wswiring.test.ts` W21 등)이 고리 본문 글자를 붙잡고 있어서다. 첫 판에서 쓸기 기록 줄을 반복문 첫 줄에 넣었다가 W21 이 붉어져 `detachPane` 아래로 옮겼다(관측).
4. **자리표 판정 입력은 두 벌**(기록 줄 · 실제 판정 인자 · 같은 식 · 둘 다 읽기 전용) — 판정 인자를 변수로 빼면 기존 줄이 바뀌어서. 두 벌이 갈리는 것은 정적 핀(`자리표 판정 입력 기록 = shouldClosePlaceholder 인자와 같은 식`)이 잡는다(뮤턴트로 확인 §4). 조각 2 가 하나로 접는다.
5. **`now` = begin 시점 `Date.now()` 1회** — 고리 안 `sweepScopeFor`·`settleSweep` 은 각자 `Date.now()` 를 따로 부른다(지금 코드 그대로). 조각 2 에서 `TickInput.now` 하나로 모을 때 이 차이(같은 틱 안 수 ms)를 fixture 에 적을 것.
6. **좌석 제목·그리기 결과는 기록하지 않음** — 입력(제목·폴더 해시·끝남·번호)으로 순수 함수 `paneTitleText` 가 다시 만든다. 「판정」 재생 대상만 남겼다.
7. **역할 이름**은 제품 어휘 꼴(`^[a-z][a-z0-9-]{0,31}$` · master·cso·worker-N·reviewer-x)일 때만 원문, 아니면 `#해시`.

## 4. 동작 변화 0 — 근거 3겹 + 뮤턴트

| 겹 | 무엇 | 결과(관측) |
|---|---|---|
| 정적 | `tickrec.test.ts` 「main.ts 배선 정적 핀」 4건: tickRec 낱말 = 선언 1 + `tickRec?.` 17 · 전부 고리 본문 안 · 배선 줄에 대입·await·return 없음 · 자리표 두 벌 식 같음 · 스위치 = 읽기만 | 21/21 통과 |
| 정적 뮤턴트 | ① `tickRec?.adopt` → `tickRec!.adopt` ② 자리표 기록의 `touched` 식 바꿈 ③ 배선 줄을 `const _g = tickRec?.gate(…)` 대입으로 | 셋 다 해당 핀 붉음(각 20/1) → 원복 |
| 실행 | `tickrec_gate.py` OFF: 기준 번들(36412afb 작업트리에서 빌드) vs 새 번들 · 같은 장면 · 멈춘 가짜 시계 | (명령·인자) invoke 1088건 · 저장소 3키 · 화면 글자 · pane 2 · 탭 [본부, zeta-team-name] sha256 `308dd2b91f9a…` 둘 다 같음 |
| 대조군 | 기준 번들 두 번 | 같음(하네스 결정론) |
| 음성 대조 | 장면에 좌석 1개 더 | 다름(비교기가 차이를 잡음) |
| 정보 | invoke 의 가짜 시각까지 같은가 | 두 번 중 한 번 같음 · 한 번은 14건이 1ms 어긋남(초기 적재 중 실시간 누수 — 순서·인자는 그때도 같음) → 시각은 판정에서 빼고 정보 줄로만 |
| tsc 음성 대조 | `views/tickrec.ts` 에 타입 오류 1줄 | rc 1 · `TS2322`(새 폴더도 검사 범위 안 확인) → 원복 rc 0 |

## 5. 게이트 결과(HANDOFF.cysr-1115-integ-r2 §7 기대값 대비)

격리 env = `env -i HOME=/tmp/claude-501/s0h TMPDIR=/tmp/claude-501/s0t PATH=~/.cargo/bin:~/.bun/bin:/usr/bin:/bin CARGO_HOME RUSTUP_HOME DISABLE_AUTOUPDATER=1`(§7 틀 그대로) · 작업트리 = 이 조각 변경 포함(커밋 전 같은 바이트) · 로그 = 스크래치 `g1/`.

| 대상 | 이 조각 | 기대값(integ-r2 §7) | 판정 |
|---|---|---|---|
| `cargo build --bins` · `test --no-run --bins --lib --tests` | rc 0 · rc 0 | rc 0 | 같음 |
| lib | **1238 · 0 · 2** | 1238/0 | 같음 |
| bin cys | **761 · 0 · 2** | 761/0 | 같음 |
| bin cysd | 3269 · **3** · 17 | 0 실패(흔들림 1 가능) | **환경 탓 확정** — 아래 |
| bin cys-seatkeep | 49 · 0 | 49/0 | 같음 |
| tests/*.rs | hidden_seat_screen 1/0 · rotate_autorestore_hold 11/0 · seat_group 1/0 · update_drainhold_e2e 4/0 · win_job_exit 0 · win_pack_swap 0 | 같은 수 | 같음 |
| `integ_1115_agy_door_drop` | 1/0 | 1/0 | 같음 |

| UI 번들 `sh ui/build.sh` | rc 0 | rc 0 | 같음 |
| tsc `bun x --package typescript@7.0.2 tsc -p tsconfig.check.json` | rc 0 · 음성 대조 rc 1 TS2322 | rc 0 | 같음 |
| bun test(ui) | **3472 · 88 skip · 0 fail** | 3451 · 88 · 0 | +21 = 새 tickrec 시험 |
| 화면 게이트 7종(§7) | race 108/0 · focus 72/0 · seatrows 75/0 · pillar 77/0 · seatgroup 8/0 · rolereuse 11/0 · stty 7/0 | 같은 수 | 같음 |
| 화면 게이트 더(설계 §2-1 ③ 이름) | nodept 16/0 · restart 6/0 · hidden_block 18/0 | — | PASS |
| 새 `tickrec_gate.py` | PASS(§4) | — | — |
| agy 수용 하네스 `acceptance.py` | 종합 PASS(실행 뒤 `git checkout -- docs/agy-door-evidence/`) | 34/34 | 같음 |
| 팩 파이썬 | computer_control 112 OK · agents_notes_personal_hooks rc 0 · hook_fail_log 11 OK · hook_fail_timing 10 OK · javis_counsel 118 OK(skip 3) · agy_door 20 OK · agy_door_phoenix_loop rc 0 · dept_chat_inject_timeout **1회 붉음 → 혼자 3/3 OK** | 전부 OK | 흔들림(아래) |
| 공개 secret-scan `scripts/secret-scan.sh --all`(커밋 뒤) | 1차 적발 1(시험 견본 경로) → 24d5d2d8 뒤 **clean 2055 파일** | clean | 같음 |
| health `run_bootstrap_health.py --json` | 167 PASS · 2 FAIL · 1 SKIP / 170 · FAIL = **H-CLT-1·H-CLT-2 뿐**(프리루드가 `/Applications/cys.app/…/python3` 를 고름) · H-SECRET-1 PASS · H-WIN-11 skip | FAIL = H-CLT-1/2 뿐 | 같음 |

- dept_chat_inject_timeout `test_b_hung_interpreter_still_cut_and_recorded` = 「15.02 not less than 12 : 안쪽 상한이 걸리지 않았다」 — 순서 실행 중 1회 · 같은 격리 env 로 혼자 3번 = 3/3 OK(14.0s) · 팩 파일이라 이 조각(웹뷰 TS)과 무관 → 부하 타이밍 흔들림으로 둔다.
- 화면 게이트들이 `docs/evidence-tabs-sidebar/`(1b·1h·2b-3·2d·948-focus·restart)에 캡처를 쓴다 → 커밋 전 스크래치로 옮김.
- **cysd 3건 = 격리 PATH 에 `/usr/sbin`·`/sbin` 이 없어서**(관측): `hwmon::tests::snapshot_has_all_sections`(gpu cores 0) · `pty_test_support::tests::census_reads_device_count_and_max` · `usage::tests::b6_lsof_resolver_reads_open_rollout_fd`(lsof 없음). 같은 3건을 같은 env 로 다시 = 3/3 붉음 · PATH 끝에 `:/usr/sbin:/sbin` 만 더하면 = **3/3 초록**. 이 조각의 러스트 변경 = 0줄(`git diff --stat` = `ui/`·`docs/`·HANDOFF 뿐)이라 cysd 바이트는 36412afb 와 같다. ⚠ **§7 격리 env 틀 자체의 함정** — master msv 때 PATH 에 `/usr/sbin:/sbin` 을 넣을 것(integ-r2 기록 3271/1 은 이 3건이 초록이었던 env 로 보임 〔추정〕).

## 6. 치명 위험 4군 점검

| 군 | 조각 0 이 닿는가 | 까닭(근거) |
|---|---|---|
| ① 폭주 큐 | **닿지 않음** | 기록기는 invoke·데몬·큐·타이머를 쓰지 않는다(정적: 기록기 파일 부작용 통로 0 시험 · 실행: 켜짐도 invoke 열 = 기준과 같음 1088건). 새 setInterval·setTimeout 0 · 새 RPC 0 |
| ② 무clear | **닿지 않음** | 좌석 입력줄·PTY 에 쓰는 길이 없다(send_input·send_text·send_key 호출 0 — 위와 같은 근거). 컨텍스트 순환·clear 경로 코드 무접촉 |
| ③ 자가치유 전멸 | **꺼짐 = 닿지 않음 · 켜짐 = 닿지 않게 막음** | 꺼짐: 고리가 평가하는 식·순서가 같다(정적 핀 + 실행 대조). 켜짐: 기록기 예외를 안에서 삼킴(`safe` · 시험 「adoptedHere 가 던져도 sock 은 던지지 않는다」) · 고리 흐름(return·continue·await)에 배선 줄이 끼지 않음(정적 핀) · 저장소 쓰기 0(배치 저장 한도 잠식 없음) · 메모리 상한(링 200 × 칸 상한 · 실제 장면 277 KB) · 켜짐 실행에서 `skippedBusy` 0 · 모든 칸이 end 까지 닿음 · 틱 seq 연속 |
| ④ 전 pane 사망 | **닿지 않음** | DOM·xterm·`render()`·`fitPane`·`resize_surface` 를 부르지 않는다(기록기 파일에 document·window 0 — 손잡이 걸기는 main.ts 가 주는 콜백). 꺼짐 실행에서 화면 글자·pane 수 = 기준과 같음 |
| (윈 설치) | **닿지 않음** | 설치기·NSIS·ps1·러스트 변경 0. 웹뷰 TS 만(맥·윈 같은 번들) — 윈 웹뷰(WebView2)에서 바뀌는 것은 선택적 호출(ES2020) 뿐이고 번들은 이미 같은 문법을 쓴다 |

## 7. 재현 명령

```sh
W=~/axdev/.wt/cys-ui-slice0; cd $W/ui
bun install --frozen-lockfile && sh build.sh && bun test                       # 기대 3472 pass · 88 skip · 0 fail(종전 3451 + tickrec 21)
bun x --package typescript@7.0.2 tsc -p tsconfig.check.json                     # 기대 rc 0
bun test src/views/tickrec.test.ts                                              # 기대 21/0
# 기준 번들: git -C $W worktree add --detach /tmp/s0base 36412afb && (cd /tmp/s0base/ui && bun install --frozen-lockfile && sh build.sh)
CHROME_PATH=<chrome-headless-shell> BASE_DIST=/tmp/s0base/ui/dist TICKREC_OUT=<덤프 경로> <playwright python3> e2e/tickrec_gate.py   # 기대 RESULT: PASS(약 20초)
# 끝나면: git -C $W worktree remove --force /tmp/s0base
```

## 8. 조각 2 에게

- 덤프 꼴 = `{schema:"cys-tickrec/1", ring, counters, entries[]}` · 칸 = `seq·now·ws[{id,sock,pending,deleting,sids}]·ghostIn·sweepArmed·placeholders·touched·socks[{sock,got,n,trunc,surf[{sid,role,ex,no,lc,tl,th,cl,ch,sz,cb,pane}]}]·ghost[{sock,tree,evict}]·sweep[{sock,here,scope,targets}]·adopt·adoptAbort·ph[{sock,sid,in,close,closed}]·wsAfterDepts·render·ghostOut·sweepArmedAfter·notices·err·done`.
- 소금은 기록기마다 새것 — 같은 덤프 안에서만 해시가 같다. 재생 대조는 **한 덤프 안의 구조 동일성**으로 한다(다른 덤프끼리 해시 비교 금지).
- 견본 덤프의 결정 수: 입양 6 · 유령 퇴거 1 · 옛 자리 쓸기 1 · 자리표 판정 5(회수 1 · 유지 4) · 부서 열기 1 · 소켓 건너뜀 11.
- **F18(관측값을 입력으로) 관찰**: 지금 코드는 자리표 좌석에 늘 런타임이 있어 견본의 자리표 입력 `lc` 는 전부 0(null 0건). 「런타임 없음 = 판정 보류」 fixture 는 조각 2 가 합성해야 한다(실제 기록에는 그 경우가 나올 수 없다 — 지금 코드에 런타임 없는 자리표가 없으므로).
- 아직 기록 안 하는 판정 입력: 입양 시 `homeOf()` 결과(작업공간 선택) · `rolePri` 정렬 결과 · `deptSeen` 집합 · `hqMasterSids`. 조각 2 에서 decideTick 경계를 그으며 필요하면 begin 칸을 늘린다(정적 핀의 17 도 함께).

## 9. 함정

- 본문을 떼어 `with (scope)` 로 돌리는 하네스(roleactivity·deptprogresswiring)가 있다 — 고리에 새 자유 변수를 넣으면 그 대역 목록에도 넣어야 한다(안 넣으면 16건 붉음 · 관측).
- `bun-env.d.ts` 는 손으로 적은 매처만 선언한다 — `toMatchObject`·`expect.stringMatching`·`toBeLessThanOrEqual` 을 쓰면 bun test 는 초록인데 **tsc 만 붉다**(관측 · 고쳐서 0).
- playwright 파이썬 `clock.install(time=<int>)` 는 초로 읽는다(ms 로 넣으면 서기 58000년) → `datetime` 으로 · `pause_at` 없이 두면 실시간이 새어 시각이 수 ms 갈린다.
- **health H-SECRET-1 은 커밋 전 새 파일을 보지 않는다** — 커밋 전 health 는 PASS 였는데, 커밋 뒤 `scripts/secret-scan.sh --all` 이 내 시험 견본 경로(`/Users/<이름>/…` 꼴) 1건을 적발(관측) → 24d5d2d8 로 0건. 새 파일이 있으면 **커밋 뒤 secret-scan 을 한 번 더**.
- HANDOFF.cysr-1115-integ-r2 §7 의 격리 env PATH(`/usr/bin:/bin`)로는 cysd 3건(hwmon·pty census·lsof)이 붉다 — `/usr/sbin:/sbin` 을 더할 것(§5).
- 시험 파이썬: 이 기기엔 playwright 가 깔린 파이썬이 없었다 → 스크래치 venv(`pip install playwright==1.58.0` · 브라우저는 기존 캐시 chromium_headless_shell-1248).
