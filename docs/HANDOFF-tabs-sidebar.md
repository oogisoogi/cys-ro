# HANDOFF — TICKET=cysr-tabs-sidebar-impl (가지 feat/tabs-sidebar · 기준 270e3e21 v1.1.14)

**다음 첫 행동 1줄**: 인박스에서 master 의 「두 줄 격자 기준」 답(A 40열 / B 80열 / C 격자 없음 · 10:06:45 【중간】 의 【결정필요】)을 확인하고, 답이 없으면 2c-2(아래)부터 착수한다.

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

시험: `cd ui && bun test` = 3387 통과 0 실패 · `bunx tsc -p tsconfig.check.json` 0. 게이트 3종 PASS(아래 재현).

## 미완(순서)
1. **2c-2**: ⓑ = **완료** — `tests/hidden_seat_screen.rs`(격리 데몬 · 구독 붙은 좌석 vs 없는 좌석 · read_text 같은 결과 줄 · 86b7bc83 + 정리 수리). 남은 것 = 막힘 표시 지연 실측 + codex 1R. (아래 원문은 이력)
   - 이력: ⓑ 숨은 탭 좌석 `cys send` → `cys read-screen` = 보이는 좌석과 같음 — 구조 근거만 있음(read-screen = 데몬 RPC `surface.read_text` handlers.rs:8763 · 숨김 = main.ts render() 의 `rt.el.remove()` DOM 떼기뿐 · 출력은 떼어진 xterm 에도 계속 씀). **격리 데몬 실측 시험이 아직 없다.** + 「승인 창이 숨은 탭에서 떴을 때 막힘 표시까지 걸린 시간」 실측 + codex 1R(숨은 탭 PTY·복원 조각 · `</dev/null` + timeout).
2. **2d**: `cys seat-group --surface <번호> <묶음>`(데몬 메모리 필드 + 이벤트 `surface.group.changed` · 호출자 = master 또는 사람 CLI · 같은 값이면 이벤트 없음) + 앱이 `seatGroup` 에 영속(열쇠 = 소켓+역할, 없으면 소켓+cwd) + 앱 시작 때 surface.list 의 group 읽어 영속 + **말로 컨트롤 센터 열기 통로**(같은 통로 · master#b1b8d7df) · codex 1R. 치명 4군 점검 = 설계 §5.
3. **2b-2**: 한 묶음 다수 좌석 두 줄 격자 — 위 【결정필요】 답대로. 1280 폭 탭 이름 넘침 점검.
4. **캡처 3·7·12**(ⓐ) + 1280 + 워커 0·1 「새 단추 0 · 새 질문 0」 + 앱 종료→재실행 탭 배치 동일(ⓒ — 순수 시험 `grouptabs.test.ts` 「재부팅 뒤 번호 재발급」 은 있음 · 실앱 기록 없음) + 실제 빌드 앱 격리 프로필 캡처(박사님 화면 금지).

## 함정
- 소스를 문자열로 떼어 돌리는 시험이 많다(`roleactivity.test.ts` · `deptprogresswiring.test.ts` · `b230scroll.test.ts` 의 대역 목록). main.ts 함수에 새 자유 이름을 쓰면 그 대역에 이름을 더해야 한다(ReferenceError 로 실패).
- style.css 의 첫 `@media (prefers-reduced-motion` 앞까지를 읽는 시험이 있다(roleactivity.test.ts) — 새 @media 블록을 역할 점 규칙보다 앞에 두지 마라(기존 블록에 줄을 더한다).
- 시험 장치(e2e) 계정 목록이 비면 사용량 막대가 안 그려진다(accountRates 는 updated_at 없는 계정 무시) — 결함 아님.
- playwright = `/Users/oogisoogi/axdev/GlobalNews-Crawling-AgenticWorkflow/.venv/bin/python3`(읽기만) · 브라우저 판 불일치 → `CHROME_PATH=$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell`.
- 커밋 전에 `bunx tsc` 를 먼저(2693c9ab 를 한 번 바로잡았다).

## 재현
```
cd ~/axdev/.wt/cys-tabs-sidebar/ui && bun install --silent && bun test && bunx tsc -p tsconfig.check.json
cd .. && sh ui/build.sh
export CHROME_PATH=$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell
for g in seatrows_gate statusboard_gate cc_button_gate; do cys run -- /Users/oogisoogi/axdev/GlobalNews-Crawling-AgenticWorkflow/.venv/bin/python3 ui/e2e/$g.py; done
```
캡처 = `docs/evidence-tabs-sidebar/{1b,1d,1e}/`(커밋하지 않음).

## 결정 대기(master/박사님)
- 두 줄 격자 기준(A/B/C) — 10:06:45 【중간】.
- 📌 상황판에서 「작업 중」·「대기」 가 둘 다 채운 원(작업 중만 깜박) — 정지 화면 구별 약함.
- 📌 기본 폭 216px 에서 한도 한 줄 잘림(「…초기화까지 2…」).
