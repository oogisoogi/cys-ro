# HANDOFF — TICKET=cysr-tabs-sidebar-impl (가지 feat/tabs-sidebar · 기준 270e3e21 v1.1.14)

**다음 첫 행동 1줄**: `cargo test --bin cys` 전체 재실행 숫자 확인 → 【확인요청】 송신(2a·2c 독립 검증 좌석은 master 가 띄움) → 답 대기. 남은 것 = 실제 앱(Tauri) 격리 프로필 캡처 1건뿐(창이 박사님 화면에 뜨므로 master 판단).

(원래 첫 행동): 인박스에서 master 의 「두 줄 격자 기준」 답(A 40열 / B 80열 / C 격자 없음 · 10:06:45 【중간】 의 【결정필요】)을 확인하고, 답이 없으면 2c-2(아래)부터 착수한다.

설계 = `docs/DESIGN-tabs-sidebar.md`(승인 master#c9265847) · 상황판·컨트롤 센터 = `docs/STATUSBOARD-1d.md` · TODO = `WORKER_TODO.cysr-tabs-sidebar-impl.md`(worktree 안).

## 끝난 것(커밋 순 · 전부 로컬 · push 0)
| 조각 | 커밋 | 내용 |
|---|---|---|
| 설계 | 452bb757 · 1a6f5be6 | 설계 1쪽 + 승인 반영 |
| 1a | 08d97e3a | `ui/src/seatrows.ts` 좌석 줄 순수 판정 |
| 1b | b98bce33 | 부서 카드 아래 좌석 줄 · 페인 CTX 칸 합침 · 승인 창 좌석 · `ui/e2e/seatrows_gate.py` |
| 1c | 41754b7a | 이름 최소 6자(꼬리표 둘째 줄) · 역할 점과 판정 하나(`seatDot`) |
| 2a | 2693c9ab · 2348ea66 | `ui/src/grouptabs.ts` 탭 판정 · 노브 「묶음 탭」(기본 켬) · `ws.tabs` 저장 · render() = 보기 트리 · 좌석 줄 클릭 = 넓게 보기 |
| 1d | 39c5dc7d | `ui/src/statusboard.ts` 상황판 · 부서 1개면 본부 카드 대신 · `ui/e2e/statusboard_gate.py` |
| 1e | 745a431a · b9b4bdf6 | Control Center 단추 기본 숨김(topbarlayout.ts) · 상황판 「승인 대기 N」 · 화면 설정 「컨트롤 센터 열기」 · 감사 반영 · `ui/e2e/cc_button_gate.py` |
| 1f | b3b82ee0 | 계정 줄 제거 · 모양 = 역할 점 정본 · 수 크게 |
| 1g | 8c0f6fb0 | 상황판 = 상태 수 + 사용량(종전 #ws-usage 요소를 펼침 칸으로 옮김) · 위치 위/아래 |
| 2b-1 | ef176ecd | `ui/src/tabbar.ts` 탭 머리 줄 = 고정 기둥 오른쪽 위에만 · 고정 기둥 폭 탭 간 유지 |
| 2c-1 | c99378c6 | fitPane 같은 크기 재전송 0(탭 20회 왕복 resize 131 → 4 실측) |
| codex 1R | f79f175c · 5a334ab8 | REVISE 6건 처리 |
| 2d | cfbe352d | `cys seat-group --surface <좌석> <묶음>`("" = 해제) · `cys open-control-center` · 데몬 Surface.group(메모리) + RPC surface.set_group·ui.open_panel(호출자 = master 좌석 또는 좌석 밖) + 이벤트 · 앱 seatgroup.ts(열쇠 = 소켓+역할/폴더 · localStorage cys-seat-group) · `tests/seat_group.rs` · `ui/e2e/seatgroup_gate.py` |
| 2d codex 1R | 05ab8f1b | 호출자 판독 실패 = 거부 · group_set(해제 ≠ 모름) · 같은 열쇠 좌석은 앱 기록 안 씀 · 양방향 제어 문자 거부 · 원문 docs/CODEX-R1-2d-tabs-sidebar.txt |
| 2b-2 | 353fe297 | grouptabs.gridColumns·gridView(4개 이하 한 줄 · 5개부터 두 줄+ · 칸 최소 40열×12줄 · 못 지키면 가장 덜 모자란 격자) · 탭 화면에서만 · fitPane 이 글자 칸 기억(noteGridCell) · `ui/e2e/grid_gate.py` · 캡처 2b-2/ |
| 2c-2 남은 것 | (이 커밋) | 숨은 탭 막힘 표시 지연 실측 `ui/e2e/hidden_block_gate.py` — 화면 승인 창 0.7~2.8초(3초 목록 고리) · 승인 요청 이벤트 즉시 · 실측 중 찾은 결함 수리 = 탭 머리 표지가 그릴 때 한 번만 만들어져 숨은 탭 막힘이 안 뜨던 것(refreshSeatRows 가 제자리 교체) · 1.1.14 기준 대조 `ui/e2e/baseline_gate.py` |
| 남은 4번 | 95e6c6c9 · bf24c380 | 1.1.14 기준 대조 · 재실행(목록 전) 넓게 보기 기억 소실 수리 + restart_gate |
| 상황판 3 · 1h | 476e73e3 | 수 옆 글자 라벨 · 한도 줄 「86% · 금 06:00 초기화」(전문 = 툴팁) · 「승인 요청 N」 = 좌석 밖 요청만 · 부서 0개 = body.no-depts(.dept-only 숨김 · 팔레트 부서 항목 = 부서 있거나 전문가 모드만 · 「본부」→「새 화면」) · `ui/e2e/nodept_gate.py` |

시험: `cd ui && bun test` = 3387 통과 0 실패 · `bunx tsc -p tsconfig.check.json` 0. 게이트 3종 PASS(아래 재현).

## 미완(순서)
0. ✅ **1h 완료(476e73e3)** — 원 지시: (master#edd9d8a8 · 박사님 「권고대로」): 부서 0개(본부만) = 「부서」 말·단추·안내 화면 0 · 1개 이상 = 지금 그대로 · 판정 = 부서 수(list_depts·deptSeen) · 감사 흔적 4(index.html:59 안내 줄 · main.ts:9152 팔레트 「부서 워크스페이스 추가」 · 「본부」 이름 · index.html:188 작업 탭 설명문) 다시 세어 표 · 만드는 길(dept-by-chat · 전문가 모드 단추)·openNewlyRegisteredDepts 무변경 · 코드 삭제 0 · 데몬·팩 무수정 · 캡처 0개/1개 · e2e 1. 감사 = ~/axdev/master/reports/2026-11-11-control-center-audit/REPORT.md §7-4 ㉯ · 부록 E §4.
1. **2c-2**: ⓑ = **완료** — `tests/hidden_seat_screen.rs`(격리 데몬 · 구독 붙은 좌석 vs 없는 좌석 · read_text 같은 결과 줄 · 86b7bc83 + 정리 수리). 남은 것 = 막힘 표시 지연 실측 + codex 1R. (아래 원문은 이력)
   - 이력: ⓑ 숨은 탭 좌석 `cys send` → `cys read-screen` = 보이는 좌석과 같음 — 구조 근거만 있음(read-screen = 데몬 RPC `surface.read_text` handlers.rs:8763 · 숨김 = main.ts render() 의 `rt.el.remove()` DOM 떼기뿐 · 출력은 떼어진 xterm 에도 계속 씀). **격리 데몬 실측 시험이 아직 없다.** + 「승인 창이 숨은 탭에서 떴을 때 막힘 표시까지 걸린 시간」 실측 + codex 1R(숨은 탭 PTY·복원 조각 · `</dev/null` + timeout).
2. ✅ **2d 완료(cfbe352d) · codex 1R REVISE 4건 반영(05ab8f1b)** — 원 지시: `cys seat-group --surface <번호> <묶음>`(데몬 메모리 필드 + 이벤트 `surface.group.changed` · 호출자 = master 또는 사람 CLI · 같은 값이면 이벤트 없음) + 앱이 `seatGroup` 에 영속(열쇠 = 소켓+역할, 없으면 소켓+cwd) + 앱 시작 때 surface.list 의 group 읽어 영속 + **말로 컨트롤 센터 열기 통로**(같은 통로 · master#b1b8d7df) · codex 1R. 치명 4군 점검 = 설계 §5.
3. ✅ **2b-2 완료(353fe297)** · 【결정필요】 A안 세 조건 충돌(아래) — 원 지시: 한 묶음 다수 좌석 두 줄 격자 — 위 【결정필요】 답대로. 1280 폭 탭 이름 넘침 점검.
4. ✅(실앱 1건 제외) — 3·7·12 = 2b-2/ · 1280 = grid·seatrows·statusboard 게이트 · 워커 0·1 새 단추 0 = baseline_gate(95e6c6c9) · 재실행 배치 동일 = restart_gate(bf24c380 · 헤드리스) · ⛔남음 = 실제 빌드 앱 격리 프로필 캡처(박사님 화면에 창이 뜸 → master 판단). 원 지시: **캡처 3·7·12**(ⓐ) + 1280 + 워커 0·1 「새 단추 0 · 새 질문 0」 + 앱 종료→재실행 탭 배치 동일(ⓒ — 순수 시험 `grouptabs.test.ts` 「재부팅 뒤 번호 재발급」 은 있음 · 실앱 기록 없음) + 실제 빌드 앱 격리 프로필 캡처(박사님 화면 금지).

## 함정
- 소스를 문자열로 떼어 돌리는 시험이 많다(`roleactivity.test.ts` · `deptprogresswiring.test.ts` · `b230scroll.test.ts` 의 대역 목록). main.ts 함수에 새 자유 이름을 쓰면 그 대역에 이름을 더해야 한다(ReferenceError 로 실패).
- style.css 의 첫 `@media (prefers-reduced-motion` 앞까지를 읽는 시험이 있다(roleactivity.test.ts) — 새 @media 블록을 역할 점 규칙보다 앞에 두지 마라(기존 블록에 줄을 더한다).
- 시험 장치(e2e) 계정 목록이 비면 사용량 막대가 안 그려진다(accountRates 는 updated_at 없는 계정 무시) — 결함 아님.
- playwright = `/Users/oogisoogi/axdev/GlobalNews-Crawling-AgenticWorkflow/.venv/bin/python3`(읽기만) · 브라우저 판 불일치 → `CHROME_PATH=$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell`.
- 커밋 전에 `bunx tsc` 를 먼저(2693c9ab 를 한 번 바로잡았다).
- cargo 는 PATH 에 없다 → `export PATH=$HOME/.cargo/bin:$PATH` · `cargo test --test hidden_seat_screen`(≈15초 · 끝나고 `pgrep -fl cys-hss` = 0).
- 상황판 수를 읽는 e2e 는 `.ws-board-num` 만 읽는다(버튼엔 글자 라벨도 있다 · 476e73e3 에서 한 번 NaN).
- ★clap: `Command` 열거에 변형을 하나라도 더하면(별도 평탄화 열거로도) debug 시험 스레드(2 MiB) 스택이 넘친다 — 새 최상위 동사는 기존 `VendorAuxCommand` 안에 + 인자는 따로 둔 Args 구조체(cfbe352d 실측).
- `cargo test` 여러 대상을 한 번에 돌리면 첫 실패에서 멈춘다 → `--no-fail-fast`. `cargo test --bin cys` ≈ 13분(부하 시).
- 흔들린 시험(이 티켓에서 고치지 않음 · master#608306ca): cysd `native_publication::…np_windows_real_candidate_change_restarts_sample_confirmation` · `…np_native_same_pid_exec_is_changed_not_agent_death` · `send_settle_tests::settle_hold_denies_text_while_submit_cr_inflight_then_admits` — 전체 실행 중 load 7~9 에서 실패 · 단독 각 3/3 통과.
- 부하(load 5~7) 중엔 격리 데몬 시험이 20초 기동 대기를 넘길 수 있다(hidden_seat_screen 1회 · 단독 PASS) · cysd `np_windows_real_candidate_change_restarts_sample_confirmation` 도 부하 중 1회 실패 · 단독 3/3 PASS(이 티켓 무관 구역).
- dragdrop_gate.py 는 CHROME_PATH 를 안 받아 이 기계에서 브라우저 판 불일치로 못 돈다(환경 · 회귀 아님).

## 재현
```
cd ~/axdev/.wt/cys-tabs-sidebar/ui && bun install --silent && bun test && bunx tsc -p tsconfig.check.json
cd .. && sh ui/build.sh
export CHROME_PATH=$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell
for g in seatrows_gate statusboard_gate cc_button_gate nodept_gate seatgroup_gate; do cys run -- /Users/oogisoogi/axdev/GlobalNews-Crawling-AgenticWorkflow/.venv/bin/python3 ui/e2e/$g.py; done
```
캡처 = `docs/evidence-tabs-sidebar/{1b,1d,1e,1h}/`(커밋하지 않음).

## master 결정(master#fcbc46fb · #608306ca · 확정)
- 격자 = (가) 채택(master#608306ca): 4개 이하 한 줄 · 5개부터 40열×12줄 지키는 가장 적은 줄 · 못 지키면 가장 덜 모자란 격자 · 설계 §4 정정 1줄 반영 · 기둥 폭 규칙은 바꾸지 않는다.
- 두 줄 격자 = A안(칸 최소 폭 40열 · 좌석 3·4개 나란히 · 5개부터 두 줄 · 시안 #C 유지).
- 관찰 1 = 모양은 역할 점 정본 그대로 · 상황판 수 옆 글자 라벨(작업 중·대기) 항상 표시.
- 관찰 2 = 216px 에서 한도 한 줄 = 「퍼센트 먼저 · 초기화 요일·시각 다음」 · 글자 중간 잘림 0(전문 = 펼침·툴팁).
- 지시 없이 내린 판단 3건(사용량 칸 옮김 · 저장 배치 1회 끔 · 안내 문장 수정) = 수용.

## codex 1R(2c · 숨은 탭 PTY·복원) = REVISE → 6건 전부 처리(f79f175c · 5a334ab8) — 전문 docs/CODEX-R1-tabs-sidebar.txt
- [고침] 차단: 활성 부서 pending·모델 없음 → refreshSeatRows→render 무한 마이크로태스크 고리 → 예약 가드(main.ts refreshSeatRows) + 시험.
- [고침] 주요: refreshSeatRows 가 저장 tabs 를 정규화 없이 reconcileTabs 에 넘김 → normalizeTabState 적용.
- [고침 5a334ab8] zoom 이 sid 로 저장돼 재부팅 뒤 번호가 바뀌면 다른 좌석을 넓게 봄 → 안정 열쇠(소켓+역할, 없으면 소켓+cwd)로 저장하거나 복원 때 zoom 해제(active 유지).
- [고침 5a334ab8] tests/hidden_seat_screen.rs: spawn 직후부터 Child 소유 정리 가드 · KILL 뒤 wait · attach 성공 응답 확인 후 probe · 주장을 「구독 유무와 무관」으로 한정(DOM 숨김·PTY 크기 보존은 별도 — 2c-1 실측이 그 몫).
- [고침 5a334ab8] mountTabBar: 래퍼(area)가 split 직계 자식인데 경계 끌기 클로저는 안쪽 right 의 flex 를 바꾼다 → 끌기 중 폭 어긋남 · area 를 갱신하게.
- [논쟁 → 근거로 반박 · 시험 못박음 5a334ab8] lastSentSize: 같은 런타임에서 데몬·PTY 만 바뀌는 재부착 때 기억을 지우는 근거 없음 → 재부착 경로에서 lastSentSize.delete(rt) 확인.
