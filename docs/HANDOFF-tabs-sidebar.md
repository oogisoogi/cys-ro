# HANDOFF — TICKET=cysr-tabs-sidebar-impl (가지 feat/tabs-sidebar · 기준 270e3e21 v1.1.14)

**다음 첫 행동 1줄**: (TICKET=cysr-tabs-codex-fix-r2 · 【확인요청】 뒤 대기) codex 3R(master 대기열) 판정이 오면 그 결함 표부터 — 그 전 새 조각 0.

(이전 첫 행동 · 끝남) (이 좌석 = 【매듭】 · master 스냅샷 재실행(b21d1326) 초록이면 좌석 닫힘) 이어받는 좌석은 아래 「남은 것」 의 사후 codex 판정이 오면 그 결함 표부터 — 그 전 새 조각 0.

(이전 첫 행동 · 끝남) 조각 2b-3 고정 기둥 폭 규칙(master#62758908 · 지시서 ~/axdev/master/briefs/2026-11-11-cysr-pillar-width-rule.md) → 완료(dc1401e1 · 0d8e0d31) · 독립 검증 948 결함 표 → 이 라운드에서 고침(master#07acca07).

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

| 2b-3 | dc1401e1 · 0d8e0d31 | 탭 화면 고정 기둥 = clamp(64, 영역 열×36%, 96)(grouptabs.pillarCols·tabPillarShare) · 격자 한 규칙(gridRowMax · 4개 이하 예외 폐지 · 줄마다 고르게) · 잰 몫 재사용(흔들림 0) · noteGridCell 여백 ≥200px 거부(2b-2 잠복 결함) · 경계 눌렀다 떼기 = 아무것도 안 씀 · `ui/e2e/pillar_gate.py` · 캡처 2b-3/ 9장 + CAPTIONS.md |
| 948 D1·D2·D3·D6 | 6a8840c5 · d5abef35 | 포커스 = 보기 트리 기준(visibleSids·seatVisible · 숨으면 그 탭 마지막/첫 좌석으로) · 탭 화면 새 좌석 = 지금 탭(createdInTab) · 끝난 좌석 묶음 기록 지움(seatgroup.forgetSeatGroup) · `ui/e2e/focus_gate.py`(⑧ 조합 중 탭 전환 포함) · `ui/e2e/rolereuse_gate.py` |
| 948 D4·D5·D7·D8·D9 | efc6bed2 | 호출자 조상 끝까지 읽기(ui_caller_verdict·ancestry_end_with) · surface.list size + 앱 noteSeatSize · 이름 NFKC+Cc/Cf/Zl/Zp 거부(데몬·앱 같은 규칙 · 새 의존 unicode-normalization) · ui_caller_tests·seat_group_name_tests · 기동 대기 60초 · `ui/e2e/stty_gate.py`(격리 cysd) |
| ChatGPT 대체 1R | d8eef9a3 | 묶음 옮김(사람 손 아님) = 좌석 따라가기(renderByUser · wsViewTree) · ⌘T/⌘D 생성 중 전환 = 누른 때 작업공간·탭(TabIntent) · 삽입 = 같은 소켓·보이는 좌석 · 끝난 기록 주인 규칙 + lastSeatRow · 이름 규칙 + Default_Ignorable(+JS Cs) · `ui/e2e/race_gate.py` · focus_gate ⑨⑩ |
시험: `cd ui && bun test` = 3387 통과 0 실패 · `bunx tsc -p tsconfig.check.json` 0. 게이트 3종 PASS(아래 재현).

## 미완(순서)
0. ✅ **1h 완료(476e73e3)** — 원 지시: (master#edd9d8a8 · 박사님 「권고대로」): 부서 0개(본부만) = 「부서」 말·단추·안내 화면 0 · 1개 이상 = 지금 그대로 · 판정 = 부서 수(list_depts·deptSeen) · 감사 흔적 4(index.html:59 안내 줄 · main.ts:9152 팔레트 「부서 워크스페이스 추가」 · 「본부」 이름 · index.html:188 작업 탭 설명문) 다시 세어 표 · 만드는 길(dept-by-chat · 전문가 모드 단추)·openNewlyRegisteredDepts 무변경 · 코드 삭제 0 · 데몬·팩 무수정 · 캡처 0개/1개 · e2e 1. 감사 = ~/axdev/master/reports/2026-11-11-control-center-audit/REPORT.md §7-4 ㉯ · 부록 E §4.
1. **2c-2**: ⓑ = **완료** — `tests/hidden_seat_screen.rs`(격리 데몬 · 구독 붙은 좌석 vs 없는 좌석 · read_text 같은 결과 줄 · 86b7bc83 + 정리 수리). 남은 것 = 막힘 표시 지연 실측 + codex 1R. (아래 원문은 이력)
   - 이력: ⓑ 숨은 탭 좌석 `cys send` → `cys read-screen` = 보이는 좌석과 같음 — 구조 근거만 있음(read-screen = 데몬 RPC `surface.read_text` handlers.rs:8763 · 숨김 = main.ts render() 의 `rt.el.remove()` DOM 떼기뿐 · 출력은 떼어진 xterm 에도 계속 씀). **격리 데몬 실측 시험이 아직 없다.** + 「승인 창이 숨은 탭에서 떴을 때 막힘 표시까지 걸린 시간」 실측 + codex 1R(숨은 탭 PTY·복원 조각 · `</dev/null` + timeout).
2. ✅ **2d 완료(cfbe352d) · codex 1R REVISE 4건 반영(05ab8f1b)** — 원 지시: `cys seat-group --surface <번호> <묶음>`(데몬 메모리 필드 + 이벤트 `surface.group.changed` · 호출자 = master 또는 사람 CLI · 같은 값이면 이벤트 없음) + 앱이 `seatGroup` 에 영속(열쇠 = 소켓+역할, 없으면 소켓+cwd) + 앱 시작 때 surface.list 의 group 읽어 영속 + **말로 컨트롤 센터 열기 통로**(같은 통로 · master#b1b8d7df) · codex 1R. 치명 4군 점검 = 설계 §5.
3. ✅ **2b-2 완료(353fe297)** · 【결정필요】 A안 세 조건 충돌(아래) — 원 지시: 한 묶음 다수 좌석 두 줄 격자 — 위 【결정필요】 답대로. 1280 폭 탭 이름 넘침 점검.
4. ✅(실앱 1건 제외) — 3·7·12 = 2b-2/ · 1280 = grid·seatrows·statusboard 게이트 · 워커 0·1 새 단추 0 = baseline_gate(95e6c6c9) · 재실행 배치 동일 = restart_gate(bf24c380 · 헤드리스) · ⛔남음 = 실제 빌드 앱 격리 프로필 캡처(박사님 화면에 창이 뜸 → master 판단). 원 지시: **캡처 3·7·12**(ⓐ) + 1280 + 워커 0·1 「새 단추 0 · 새 질문 0」 + 앱 종료→재실행 탭 배치 동일(ⓒ — 순수 시험 `grouptabs.test.ts` 「재부팅 뒤 번호 재발급」 은 있음 · 실앱 기록 없음) + 실제 빌드 앱 격리 프로필 캡처(박사님 화면 금지).

## 남은 것 (master#c961101e · 11-11 18:1x)
- **사후 codex** = 대상 efc6bed2..b21d1326(cysd handlers.rs·state.rs · ui main.ts·seatgroup.ts · Cargo.toml) · master 가 21:46 뒤 codex 전담 좌석 대기열에 넣음. 꼭 물을 것 3줄:
  ⑴ ui_caller_verdict + state::parent_any_user(SHORTBSDINFO unsafe 구조 배치·크기 검사)가 사람 터미널은 통과 · 워커 좌석·40단·판독 실패는 거부하는가
  ⑵ parse_seat_group(Rust)과 cleanGroupName(JS)이 모든 입력에서 같은 판정인가(NFKC → White_Space 자르기 → Cc/Cf/Zl/Zp/Default_Ignorable · JS 는 Cs 도)
  ⑶ 사람 손 아닌 보기 변화(묶음 이벤트·목록)에서 따라가기·포커스 비움이 「다른 좌석 입력 0」 을 지키는가
- **별 조각 후보**(이번에 고치지 않음): render() 가 창을 모두 떼었다 붙여 키보드 포커스가 BODY 로 빠진다(1.1.14 동작 · race_gate R2 실측 — ⌘D 생성 중 탭을 바꾼 뒤 3초 목록이 새 좌석을 데려와 다시 그리면 글자가 어디로도 안 감). 제안 = render 끝에 「보이는 포커스 좌석이 있고 모달이 없으면 키보드 포커스 복원」.

## 처분 표 — ChatGPT 대체 1R(8c6b13fc · BLOCK) + 1R 경고 + codex 1R(d8eef9a3 · BLOCK) · master#c961101e 수용
| 항목 | 처분 | 근거·시험 | 커밋 |
|---|---|---|---|
| 1R 경고(묶음 옮김 → 타이핑이 다른 좌석) | 성립·고침(master#1dc9bd83 따라가기) | 고치기 전 cd → send_input(3) · focus_gate ⑨ ⑩ | d8eef9a3 |
| 1R #1 재부모화 자식 우회 | 구현 안 함(master 판단) · 설계 §5 한계 + 최대 피해 | 남는 최대 피해 = 지금 탭이 바뀜 | d8eef9a3 |
| 1R #2 ⌘T 생성 중 작업공간 전환 | 성립·고침 | race_gate R1 붉음 → 초록 | d8eef9a3 |
| 1R #3 ⌘D 생성 중 탭 전환·대상 닫힘 | 성립·고침 | R2 붉음 → 초록 · R3 원래 초록 | d8eef9a3 · b21d1326 |
| 1R #4 삽입 소켓 | 경로상 성립(재현 없음)·방어 | 같은 소켓 ∧ 보이는 좌석 | d8eef9a3 |
| 1R #5 확인 뒤 작업공간 | 불성립(수용) | 확인 창이 그 좌석 이름을 보임 · 기존 ws !== current() 가지 | — |
| 1R #6 겹친 열쇠 기록 | 성립·고침 | 단위 시험 붉음 → 초록 · 주인 규칙 + lastSeatRow | d8eef9a3 · 956bbc3d |
| 1R #7 끝난 좌석 포커스 | 불성립(수용) | 뒤따르는 render 의 repairHiddenFocus | — |
| 1R #8 크기 재동기 반복 | 불성립(수용) | 좌석당 약 6초 1회 상한 · stty_gate 재전송 1 | — |
| 1R #9 보이지 않는 문자 | 성립·고침 | JS 시험 붉음 → 초록 · DI(+JS Cs) | d8eef9a3 |
| 1R #10 탭 기억 수명 | 불성립(수용) | detachPane 이 모든 제거 경로에서 지움 | — |
| 1R 추측(기둥 몫 기억 열쇠) | 불성립(수용) | 열쇠 = 영역 폭·글자 크기·글꼴 | — |
| codex #1 큐에 남은 입력 | 불성립(수용) | 보일 때 사람이 친 글자 = 그 좌석으로(버리면 유실) | — |
| codex #2 경로 삽입 비동기 | 불성립(수용) | 사람이 이름으로 고른 좌석 + 같은 소켓 ∧ 보이는 좌석 조건 | — |
| codex #3 목록에서 먼저 빠진 비주인 | 성립·고침 | 끝난 줄을 겹침 판정에 넣음 | 956bbc3d |

## codex 2R 처분 (TICKET=cysr-tabs-codex-fix-r2 · 범위 efc6bed2..b21d1326 · BLOCK blocking 2·major 2 · 판정문 ~/axdev/master/reports/2026-11-11-post-codex/codex-tabs-2r.md)
| 발견 | 처분(master) | 고침·시험 | 커밋 |
|---|---|---|---|
| #4 render 뒤 실제 키보드 포커스 BODY(글자 유실 · 게이트 거짓 초록) | 고침(먼저) | render 가 떼기 전 실제 포커스 좌석을 기억 → 다시 붙인 뒤 ⑴ 포커스가 BODY/없음 ⑵ 같은 런타임이 #root 에 붙어 있음 ⑶ 모달·팔레트·메뉴 없음 ⑷ 포커스 표시 좌석 = 그 좌석 일 때만 setFocus(xterm 포커스 단일 입구 유지) · race_gate R2 = document.activeElement 가 표시된 보이는 좌석 + 이어 친 글자 send_input 목적지 단언 · R3 = 키보드도 새 좌석 · 고치기 전 붉음 3 → 초록 | 472d14e2 |
| #3 새 좌석 응답 전 작업공간 삭제 → 화면 밖 고아 | 고침 | 응답 직후 `workspaces.includes(ws) && !ws.deleting` 재검사 → 실패 = 새 좌석 닫기(closePane · 데몬 확인 뒤 화면 기억도 지움) + 알림 「새 좌석 닫음」 · 닫기 거부 = 같은 데몬의 살아 있는 작업공간에 붙여 보이게 + 알림 · actionNew·actionSplit 공통 · race_gate R4(⌘T)·R5(⌘D) 붉음 → 초록 | f51c738a |
| #2 경로 넣기 확인 창 뒤 가시성 재검사 없음 | 고침 | 공통 전송 입구 injectRawToPane 첫 줄 = paneShownNow(같은 런타임 ∧ 지금 작업공간 소켓 ∧ 보기 트리에 보임) → 아니면 넣지 않고 알림 「그 좌석이 화면에 없어서 넣지 않았어요 — 좌석이 보일 때 다시 해 주세요.」(다른 좌석으로 바꾸지 않음) · 메뉴·cd·트리 끌기·OS 드롭 전부 · focus_gate ⑪(메뉴 + 대조: 전환 없으면 들어감)·⑫(OS 드롭) 붉음 5 → 초록 | fe235975 |
| #1 이미 친 글자의 남은 전송이 탭 전환 뒤에도 그 좌석으로 | 불성립(master 판단 · 확신도 중상) · 정의 고정 | 불변식 = 「숨은 좌석에 **새로 시작되는** 입력 0」(sendRaw 주석 · 설계 문서) · focus_gate ⑬ ⓑ send_input 0.4초 지연으로 줄 세운 「abcd」 → 탭 전환 → 4 에 끝까지·순서대로(b·c·d 가 숨은 뒤 나감 단언) · 다른 좌석 0 ⓒ 숨은 뒤 새 키 「xy」 → 4 로 0 · 보이는 6 으로 | 952e3ae2 |
| (전수 표) 빈 작업공간 「새 셸 열기」 = #3 과 같은 모양 | 고침(같은 도우미) | 응답 전 그 작업공간 삭제 → 새 좌석 닫기 · 그사이 다른 작업공간이면 포커스 안 빼앗음 · race_gate R6 붉음 2 → 초록 | 578a358f |

### await 뒤 캡처한 좌석·작업공간을 재검사 없이 쓰는 자리 — main.ts 전수(방법 = 「async 함수에서 첫 await 뒤 send_input·arrangeWs·setFocus·injectRaw/Paths·closePane·.tree= 를 부르는 곳」 기계 추출 15곳 + `invoke("send_input"` 실제 호출 6곳(sendRaw · 전출 3 · injectRawToPane · restartNode) 전부 눈으로)
| 자리 | 캡처 → await → 쓰기 | 판정 |
|---|---|---|
| actionNew · actionSplit | ws/target → newSurface → arrangeWs·setFocus | 고침(#3 · R4·R5) · 포커스는 이미 「ws===current ∧ 보임」 검사 |
| 빈 작업공간 「새 셸 열기」(renderIdleWorkspace) | ws → newSurface → ws.tree=·setFocus | 고침(R6) |
| injectPathsToPane → injectRawToPane | rt → list_dir·확인 창·list_surfaces → send_input | 고침(#2 · ⑪⑫) |
| sendRaw(sendChain) | sid(키 누른 순간) → 앞 전송 → send_input | 설계대로(#1 정의 · ⑬) |
| actionClose | sid → 확인 창 → closePane | 기존 재검사 있음(확인 뒤 seatVisible · 948 D1 ⓑ) |
| refreshPaneTitles 입양 | ws(!deleting 로 고름) → makePane → arrangeWs(ws) | **같은 모양 남음 · 안 고침** — makePane(WebSocket 붙이기) 사이 그 작업공간 삭제가 시작되면 입양 좌석이 삭제 스냅샷에서 빠질 수 있다(G4 주석이 말한 누수와 같은 결). 재현 안 함 = PLAUSIBLE(공통 규칙: CONFIRMED 만 고침) · 이번 차이 밖 · codex 3R 에 물을 것 ② |
| transferCrossDept | srcWs·destWs → 여러 데몬 왕복 → destWs.tree=·send_input(새 좌석) | 같은 모양 가능(전출 중 destWs 삭제) · 안 고침 — 자체 롤백이 있는 다단계 거래 · send_input 대상 = 방금 만든 좌석 신원(가시성 무관 기계 명령) · PLAUSIBLE |
| actionEqualize | ws → list_surfaces → arrangeWs(ws)·render | 무해 — 새 좌석 없음 · 지워진 ws 에 배치만(화면 영향 0) |
| restartNode | 역할 → (await 없이) jumpToSurface → send_input | 무해 — 사람이 역할 이름으로 고른 기계 명령 · 보내기 전에 그 좌석으로 화면을 옮긴다(launchCmd 는 전출 안의 문자열) |
| 부서 ▶부서장 단추 · 팔레트 목록 | ws/sock → invoke | 무해 — 알림·목록뿐 |
| addWorkspace · addDeptWorkspace | 새 ws 를 await 뒤에 만듦 | 무해 |
| start() 복원·입양(11.9k~12.0k 줄) | ws/current() → newSurface·makePane → .tree=·arrangeWs | 기동 복원 경로(사람 손 전) · 이번 범위 밖 · 안 고침 |

### 검증(23:5x 실측)
- bun test 3429 통과 / 0 실패 · tsc 0 · 번들 빌드 OK · 화면 게이트 race 36/0 · focus 50/0 · seatrows 75/0 · statusboard 264/0 · cc_button 12/0 · nodept 16/0 · seatgroup 8/0 · pillar 77/0 · restart 6/0 · baseline PASS(기준판 = git archive 270e3e21 로 새로 빌드)
- cysd: 이 티켓은 Rust 무변경(diff 6파일 = ui·문서) · 그래도 `cargo test --bin cysd group` 12/0 · `ui_caller` 4/0 · `seat_group` 2/0 · `--test hidden_seat_screen` 1/0(끝나고 cys-hss 0)
- 뮤턴트 10(원본 무접촉 · 변이 사본 번들을 GATE_DIST 로): 죽음 9 · 살아남음 1
  M1 되돌림 호출 삭제 = 죽음(3) · M3 actionNew 검사 삭제 = 죽음 · M4 actionSplit = 죽음 · M5 빈 작업공간 = 죽음 · M6 「삭제 중」 무시 = 처음엔 살아남음 → R4b(닫기를 늦춰 응답이 삭제 진행 중에 옴) 추가 뒤 죽음 · M7 전송 직전 재검사 삭제 = 죽음(5) · M8 가시성 무시 = 죽음(5) · M9 줄 선 글자를 지금 포커스 좌석으로 = 죽음(4) · M10 숨은 좌석의 줄 선 글자 버림 = 죽음(2)
  M2(되돌림 조건 ⑷ 「포커스 표시 좌석 = 그 창」 을 빼고 그 창에 바로 되돌림) = 살아남음 — ⑷ 는 표시·키보드를 어긋나게 두지 않으려는 보수 조건이고, 숨은 좌석 방어는 ⑵(지금 #root 에 붙은 같은 런타임)가 진다. 표시와 키보드가 이미 어긋난 상태를 만드는 사람 손 경로를 찾지 못해 시험이 그 갈래를 못 탄다(빈 통과 아님 — 도달 불가 방어).

### codex 3R(범위 513846b8..HEAD · ui·문서만) 꼭 물을 것 3줄
1. render 포커스 되돌림 ⑴~⑷ 가 다른 칸(탭·작업공간 이름 편집 contentEditable · 파일 트리 · 상황판)의 포커스를 빼앗거나, 숨은/다른 작업공간 좌석에 키보드를 주는 경로가 있는가.
2. refreshPaneTitles 입양(makePane await 뒤 ws 재검사 없음 · 위 전수 표 PLAUSIBLE)이 실제 도달·피해가 있는가 — 있으면 같은 도우미로 고칠 대상.
3. 지워진 작업공간의 새 좌석 = 닫기 처분이 맞는가(닫기 거부 시 같은 데몬 작업공간에 붙이기가 종료 중 부서 데몬에서 문제 되는가) · paneShownNow 가 정당한 경로 넣기(넓게 보기·상황판 위치)를 막는 경우가 있는가.

## codex 3R 처분 (TICKET=cysr-tabs-codex-fix-r3 · 범위 aa110891..머리 · BLOCK blocking 3·major 1 · 판정문 ~/axdev/master/reports/2026-11-11-post-codex/codex-tabs-3r.md)
| 발견 | 처분(master) | 고침·시험 | 커밋 |
|---|---|---|---|
| #1 blocking 좌석 이름 변경 중 render → 이름 글자·Enter 가 터미널로(이번 차이가 만든 것) | 고침(최우선) | ⑴ paneHoldingKeyboard = 그 좌석의 xterm 입력칸(`term.textarea`)일 때만 기억(main.ts:5510) ⑵ render = 화면에 붙은 좌석 제목이 편집 중이면 떼지 않고 미룸(paneTitleEditing · main.ts:5521·5541) · 제목 확정 처리기가 flushHeldRender 로 밀린 1회(사람 손이었으면 renderByUser · main.ts:4189) · focus_gate ⑭ 고치기 전 붉음 3 → 초록 · kbrestore.test.ts ①③ | ab1b1cf2 |
| #2 blocking refreshPaneTitles 입양 makePane 뒤 재검사 없음 | 고침 | 재검사 → 같은 데몬의 살아 있는 작업공간 다시 고름 · 없으면 런타임만 파기(외부 역할 좌석 = 닫지 않음 · panes 에서도 빠짐 → 다음 틱 재입양 가능 · main.ts:3930) · race_gate R7(다른 본부 작업공간으로) · R7b(런타임 파기) | 384fb51f |
| #3 blocking transferCrossDept newSurface 뒤·원본 닫기 직전 재검사 없음 | 고침 | newSurface 뒤 srcWs·destWs 재검사(셸 갈래는 이 자리 뒤 원본 닫기까지 await 없음 = 「닫기 직전」 과 같은 자리 · main.ts:5133) → 알림 「전출 중단」 + 원본 보존 + 새 좌석만 dropSeatOfGoneWs 로 거둠 · 보상 롤백도 지워진 목적지면 같은 처리(main.ts:5242) · 에이전트 갈래 원본 닫기 직전(awaitHandoffAck · main.ts:5365) 같은 재검사 → 보류(인수 대기 기록 유지 · 원본 보존) · race_gate R8 · closecallbacks 「(codex 3R #3) acknowledged handoff …」 | 384fb51f · 111d841a(시험) |
| #4 major dropSeatOfGoneWs 닫기 거부 = 「지금 붙일 곳 없음」 을 끝으로 | 고침 | 거부 뒤 삭제 결과 확정을 기다림(whenWsDeleteSettled ← 탭 닫기·그룹 삭제 finally 의 settleWsDelete) → ⑴ 보존된 그 작업공간 ⑵ 같은 데몬의 살아 있는 작업공간 ⑶ 부서 데몬 종료 확인(deptDaemonStopped) = 런타임 파기 ⑷ 다시 닫기 1회 → 그래도 거부면 새 작업공간을 열어 보이게(알림 새 문구 「…새 작업공간에 두었어요 — 직접 닫아 주세요.」 · 지시 없이 내린 판단) · race_gate R9a(다시 닫음)·R9b(새 작업공간)·R9c(데몬 종료 = 파기)·R9d(보존된 작업공간)·R9e(삭제 「진행 중」 이 끝내 성공) | 384fb51f · 111d841a(R9e) |
| 조건 ⑷(뮤턴트 M2 생존) | 유지 + 직접 시험 | kbrestore.test.ts ② held=A·focused=B·A 도 화면 = setFocus 0 · 대조 held=A·focused=A = setFocus(A) 1 | ab1b1cf2 |
| (전수 표 추가 발견) start() 기동 복원의 같은 모양 3곳 | 고침(같은 처분 · 재현 = CONFIRMED) | 기동 중 탭은 renderWsTabs 로 먼저 그려져 지울 수 있다 → ⑴ 복원 입양 makePane 뒤 = #2 와 같은 처분(main.ts:12085) ⑵ 빈 자리 좌석 newSurface 뒤 = dropSeatOfGoneWs(main.ts:12114) ⑶ 현재 작업공간 첫 좌석(`current().tree = { sid: await … }` 는 왼쪽을 await 전에 잡음) = putSeat(main.ts:12132) · race_gate R10·R10b(384fb51f 번들에서 붉음 → 초록) · 소스 핀 문자열 그대로 | 111d841a |

### 좌석(.pane) 안에서 글자를 받을 수 있는 요소 — 전수(방법 = makePane(main.ts:4104~) 의 createElement 7개 + xterm 5.5.0 lib/xterm.js 의 tabIndex 대입 2곳 + main.ts `screenReaderMode` grep 0건)
| 요소 | 글자를 받나 | render 되돌림 기억 | 근거 |
|---|---|---|---|
| xterm 입력칸 `term.textarea`(tabIndex 0) | 예 = 터미널 입력 | **유일한 기억 대상** | xterm.js `this.textarea.tabIndex=0` |
| 좌석 제목 `.pane-title-text` | 「이름 변경」 중만(contentEditable) | 제외 + 편집 중 render 미룸 | focus_gate ⑭ |
| xterm 접근성 줄(`role=listitem` · tabIndex −1) | 스크린리더 모드 때만 생김 — 우리 설정 0 | 제외(xterm 입력칸이 아님) | main.ts `screenReaderMode` 0건 |
| 역할 점·사용량·× (`span`) | 아니오(포커스 못 받는 span) | 해당 없음 | makePane createElement |
| 좌석 밖(사이드바 작업공간 이름 · 묶음 이름 · 파일 트리 · 상황판 · 설정·확인 창의 input/select/textarea 7개) | 예 | 좌석 밖 = 원래도 기억 안 함(rt.el 안이 아님) · 창은 조건 ⑶ | codex 3R 질문 1 확인 |

### await 뒤 작업공간·좌석 재검사 — main.ts 전수 갱신(방법 = 최상위 함수마다 첫 await 뒤에 `arrangeWs(`·`.tree =`·`setFocus(`·`"send_input"`·`closePane(`·`injectRaw`·`makePane(`·`workspaces.splice/push`·`destroyPaneRuntime`·`dropSeatOfGoneWs`·`.socket` 를 ws/destWs/srcWs/rt/home 과 같은 줄에 쓰는 곳 기계 추출 · await 줄 277(주석 제외) · 그런 함수 15개 + 함수 밖 클로저 10줄 + makePane 안 클로저 2개 전부 눈으로)
| 자리 | 캡처 → await → 쓰기 | 재검사 | 시험 |
|---|---|---|---|
| actionNew(7830) · actionSplit(7850) | ws/target → newSurface → arrangeWs·setFocus | 있음(r2) | race R4·R4b·R5 |
| renderIdleWorkspace 「새 셸 열기」(5713) | ws → newSurface → ws.tree=·setFocus | 있음(r2) | race R6 |
| injectPathsToPane → injectRawToPane(8344) | rt → list_dir·확인 창·list_surfaces → send_input | 있음(r2) | focus ⑪⑫ |
| sendRaw(4453) | sid(키 순간) → 앞 전송 → send_input | 설계(#1 정의) | focus ⑬ |
| actionClose(7880) | sid → 확인 창 → closePane | 있음(기존 seatVisible) | 948 D1 ⓑ |
| **refreshPaneTitles 입양(3930)** | ws → makePane → arrangeWs(ws) | **있음(이번)** | race R7·R7b |
| **transferCrossDept(5133·5242)** | srcWs·destWs → newSurface → destWs.tree=·closePane(원본) | **있음(이번)** | race R8 |
| **awaitHandoffAck(5365)** | srcWs·destWs → 인수 확인 폴링 → closePane(원본) | **있음(이번)** | closecallbacks (codex 3R #3) |
| **dropSeatOfGoneWs(7769)** | ws → closePane 거부 → arrangeWs(home) | **삭제 확정 뒤 판정(이번)** | race R9a~e |
| **start() 복원 입양(12085) · 빈 자리 좌석(12114) · 첫 좌석(12132)** | ws/current() → makePane·newSurface → arrangeWs·.tree= | **있음(이번)** | race R10·R10b(첫 좌석 = 같은 도우미 · 별도 장면 없음) |
| buildTab 삭제 · confirmDeleteGroup · purgeDept(10101) | 지우는 그 작업공간 → 닫기·종료 → splice | 거래 자신 · `indexOf(ws) < 0` 재검사 있음 | 기존(I2·F3) |
| addDeptWorkspace(7443) | 자리 탭 → allocate → ws.socket= | 있음(기존 `indexOf(ws) < 0`) · 대기 탭의 삭제는 확인 직후 await 없이 끝나 「진행 중」 창 0 | 기존 |
| addWorkspace(7415) · openNewlyRegisteredDepts(4069) | 새 ws 를 await **뒤에** 만듦 | 무해 | — |
| actionEqualize(5951) | ws → list_surfaces → arrangeWs(ws)·render | 무해 — 새 좌석 없음 · 지워진 ws 에 배치만 | — |
| restartNode(9499) · ▶부서장 단추(12439) · 팔레트·설치 창 클로저(12252~13034) | 역할·소켓 → invoke | 무해 — 좌석·트리를 안 만든다(알림·목록·기계 명령) | — |
| makePane 안 클로저(제목 확정 rename · × 닫기) | sid/socket → invoke → refresh·render | 무해 — 그 좌석 자신 · 트리 미변경 | — |
| **남김 PLAUSIBLE ①** renderIdleWorkspace 「지금 켜기」(5700) · start() 부서 재기동(11933) | ws → launch_dept_daemon → ws.socket= | 없음 · 좌석 고아는 아님(뒤 newSurface 는 R6 도우미가 거둠 · 기동은 다음 줄들이 재검사) · **켜진 부서 데몬이 탭 없이 남을 수 있음**(데몬 생명주기 · Rust launch 쪽) | 재현 안 함(공통 규칙: CONFIRMED 만 고침) |
| **남김 PLAUSIBLE ②** 사이드바 묶음(그룹) 이름 편집(6767~) | — | renderWsTabs 재렌더 거부가 `.ws-name` 만 봐서 10초 갱신이 묶음 이름 편집을 끊을 수 있음(글자 유실 · 터미널로 새지는 않음 = 이번 고침 뒤 기억 대상이 xterm 뿐) · 좌석 밖 · 이번 차이 밖 | 재현 안 함 |

### 검증(실측)
- bun test 3529 중 통과 3441 · 건너뜀 88 · 실패 0(머리 bf8aba33) · tsc 0 · 번들 OK
- 붉음 → 초록: focus_gate ⑭ 붉음 3(aa110891 번들) · race_gate R7~R9d 붉음 15(aa110891 번들) · R9e 붉음 2(aa110891) · R10·R10b 붉음 2(384fb51f 번들) → 모두 초록
- 화면 게이트(최종 머리): bf8aba33 · 04:03~04:19 · race 95/0 · focus 57/0 · seatrows 75/0 · pillar 77/0 · seatgroup 8/0 · rolereuse 11/0 · stty 7/0(cysd·cys debug 빌드 포함 · 끝나고 격리 데몬 0) · 전부 RESULT PASS
- Rust 무변경(aa110891..머리 diff = ui 7파일 · main.ts +135/−16)
- 뮤턴트(원본 무접촉 · 스크래치 사본 src + node_modules 연결 · 번들 GATE_DIST · 화면은 해당 항목만 잘라 실행): 14개 — 죽음 13 · 살아남음 1(동치)
  M1 되돌림 기억을 좌석 안 아무 요소로(옛 rt.el.contains) = 죽음(kbrestore ①) · M2 조건 ⑷ 빼고 held 로 되돌림 = 죽음(kbrestore ②) ·
  M3 제목 편집 중 render 미룸 제거 = 죽음(⑭ 2 · 단위 2) · M4 확정 처리기의 flushHeldRender 호출 제거 = 화면 ⑭ 는 살아남고 단위 배선 핀으로 죽음
  (관측: 이 장면에선 확정 뒤 #root 다시 그리기 0회인데 새 좌석 60 이 0.15초 안에 보인다 — render 아닌 다른 DOM 경로 · 원인 미규명 · 「미룬 render 가 반드시 한 번 돈다」 는 단위 시험만 고정) ·
  M5 입양 재검사 제거 = 죽음(R7·R7b 3) · M6 입양 런타임 파기 제거 = 죽음(R7b) · M7 전출 newSurface 뒤 재검사 제거 = 죽음(R8 4) ·
  M8 awaitHandoffAck 원본 닫기 직전 재검사 제거 = 죽음(closecallbacks) · M9 삭제 확정 기다림 제거 = 죽음(R9e 2) · M10 데몬 종료 갈래 제거 = 죽음(R9c) ·
  M11 다시 닫기 제거 = 죽음(R9a 2) · M12 「보존된 그 작업공간 우선」 제거 = 살아남음 — 동치(확정 뒤엔 그 작업공간이 「삭제 중」 이 아니어서 아래 같은 데몬 찾기가 그것을 고른다 · 차이 = 같은 데몬 작업공간 2개+ 일 때 어느 쪽인가뿐) ·
  M13 기동 복원 입양 재검사 제거 = 죽음(R10) · M14 기동 빈 자리 좌석 재검사 제거 = 죽음(R10b)

### 알려진 동작(릴리스 노트 초안 · 2R #1 잔여 · 코드 변경 없음)
- 좌석이 보일 때 친 글자와 Enter 는, 바로 탭을 바꿔 그 좌석이 숨더라도 그 좌석에 끝까지 전달돼요. 그래서 질문을 치고 Enter 를 누른 직후 탭을 바꾸면, 에이전트는 화면에 안 보이는 채로 그 질문을 실행할 수 있어요.
- 숨은 좌석에 **새로** 들어가는 글자는 없어요. 실행 결과는 그 탭으로 돌아오면 그대로 볼 수 있어요.

### codex/ChatGPT 닫힘 확인(범위 aa110891..머리 · ui·문서만) 꼭 물을 것 3줄
1. render 미룸(좌석 제목 편집 중)이 다른 사람 손 동작(탭 클릭·⌘키·좌석 닫힘 이벤트)과 겹칠 때 화면이 옛 상태로 남거나 미룬 render 가 사라지는 길이 있는가(편집이 blur 없이 끝나는 경우 포함).
2. dropSeatOfGoneWs 의 「삭제 확정 뒤 판정」 · 새 작업공간 열기 끝 갈래가 사용자가 방금 지운 작업공간을 사실상 되살리는 것으로 읽히는가 — 더 나은 끝 처분이 있는가.
3. start() 기동 복원 3곳·전출 2곳 재검사 뒤에도 await 뒤 지워진 작업공간에 좌석을 붙이는 자리가 main.ts 에 남았는가(위 전수 표의 「무해」·PLAUSIBLE 판정이 틀린 곳).

### 다음 첫 행동
- master 스냅샷 재검증 → ChatGPT 닫힘 확인 1R(위 3줄).

## ChatGPT 닫힘 확인 처분 (TICKET=cysr-tabs-codex-fix-r3 회차 2 · master#baa8e3f0 · 판정문 ~/axdev/chatgpt-desk/runs/2026-11-12/REVIEW-cysr-tabs-r3-774aed19.md · BLOCK blocking 1·major 8·minor 1 · 마지막 이종 왕복)
| 발견 | master 처분 | 결과 | 고침·시험 | 커밋 |
|---|---|---|---|---|
| F1 blocking 기동 복원 첫 좌석 폴백이 cw 를 잡고도 current() 를 다시 읽음 | 고친다 | 성립(재현 · 111d841a 가 만든 것 — 그 전 판은 양쪽 다 current() 라 어긋나지 않았다) | cw·cwSock 한 단위(main.ts:12168) · 첫 시도 cwSock(12179) · 폴백은 `!cwSock`(본부일 때만 · 12186) · 붙이기 직전 「만든 데몬 == 붙일 작업공간 데몬」 단언 → 다르면 그 새 좌석 거둠(12171) · race R11 붉음 3(774aed19 번들: 본부 좌석 50 이 LMS 트리에 · 본부#50 런타임 화면 밖) → 초록 · wswiring 핀을 cwSock 로 · 같은 꼴 grep: 이번 차이 + start() 안 current() 호출 = 12121 앞 판정 줄 · 12162 render 직후 동기 읽기뿐(섞어 쓰기 0) · 8262·8272·8341 의 cw = await 없는 동기 스냅숏 | 8c5e4878 |
| F2 major 닫기 두 번 거부 + 붙일 곳 없음 → 새 작업공간 | 고치지 않는다(설계 유지) | — | 알려진 동작 1줄 추가(아래) · 다음 판 후보 2줄(아래) | 이 문서 |
| F3 major 두 번째 closePane await 뒤 재판정 없음 | 고친다 | 성립(코드 판독) | settled()(main.ts:7808) = 판정+트리 편입 한 동기 구간 · 삭제 확정 뒤(7824)·두 번째 거부 뒤(7832) 둘 다 · closecallbacks 「(ChatGPT F3)」 두 갈래(그사이 같은 데몬 작업공간 생김 → 거기 · 데몬 꺼짐 → 런타임만 · 새 작업공간 0) — 고치기 전 main.ts 에서 붉음 | 70a9a501 |
| F4 major 편집 중 사람 손 render 까지 미룸 | 재현 먼저 | **⌘T 성립** · ⌘W·탭 클릭 불성립 | focus_gate ⑮(Chromium): 편집 중 ⌘T → 새 좌석이 안 보이고 편집도 열린 채(붉음 2 · 70a9a501) → 전역 단축키 손잡이가 처리하는 키(k·t·d·D·w·=·+·-·0·⌘G(제어판))면 endPaneTitleEdit()(5527 · 13124)로 먼저 확정 → 초록 · ⌘W = 확인 창이 포커스를 가져가 blur → 확정(초록) · 탭 클릭 = mousedown blur 가 click 보다 먼저 → 확정(화면·상태 어긋남 0) · 편집 칸 글자 단축키(⌘A·⌘C·⌘V·⌘Z)는 건드리지 않음 · 자동 render 미룸은 그대로 | 709884d4 |
| F5 minor 편집 대상이 확정 없이 사라지면 보류 표식 남음 | 고친다 | 성립(코드 판독) | 편집 없는 정상 render 가 밀린 표식을 소비(5558 · 사람 손이었으면 renderByUser) · 런타임 파기 뒤엔 그 호출자가 늘 render 한다(closePane·유령 수렴·끝남 = render) · kbrestore 「(ChatGPT F5)」 — 고치기 전 붉음 | 70a9a501 |
| F6 major panes.has() 거짓 = 데몬 좌석 끝 으로 읽음(2곳) | 판독 → 닿으면 고친다 | **닿는 길 1개 → 막음** | 판독: 런타임 파기 경로 = closePane(데몬 확인) · 유령 수렴(데몬이 모름 2연속) · 끝남 목록·이벤트 · 입양(방금 만든 역할 좌석 런타임) · 첫 좌석 단언(방금 만든 좌석) · 기동 복원(makePane 이 **이미 있던** 런타임을 돌려주면 남의 것을 지울 수 있었음 — 기동 중 ⌘T 로 만든 새 좌석이 기동 목록에 들고 그 작업공간이 지워지는 경우) → 기동 복원은 makePane 전에 있던 런타임을 지우지 않음(hadRuntime · 12121) · 나머지는 데몬 확인 또는 제가 만든 런타임뿐이라 「런타임 없음 = 끝남」 성립 · 시험 = 배선 핀(장면 재현 안 함 = 기동 중 ⌘T + 삭제 겹침) | 70a9a501 |
| F7 major(조건부) 종료 기록이 소켓 글자만 | 확인 먼저 | **성립**(기록을 지우는 곳 0 — 같은 소켓 경로로 다시 뜨면 남음) | noteDeptDaemonUp(7845) = 새 부서(allocate) · 「지금 켜기」 · 기동 재기동 · 켜진 동안 새 등재 4곳에서 그 소켓 기록 제거 · closecallbacks 「(ChatGPT F7)」(재기동 전 = 런타임만 지움 · 재기동 뒤 = 다시 닫기 → 보이게) + 배선 핀 — 고치기 전 붉음 | 70a9a501 |
| F8 major 검출기가 좌석 번호만 | 고친다 | 성립 | 출력 듣기 이름 = 소켓#좌석 · 화면 밖 = (소켓, 좌석) 이 그 소켓 트리에 없음 · R0 겹침 검체(본부 1 · LMS 1) 자가 시험 + 옛 검출기가 같은 검체를 놓침 대조 · R11 이 본부#50 화면 밖도 잡음 | 8c5e4878 |
| F9 major R8·R10b 새 좌석 회수 직접 단언 없음 | 고친다 | 성립 | `__made`(만든 좌석) · reclaimed() = 그 데몬에 close_surface ∧ 데몬 좌석 목록에서 빠짐 · R8·R10b 필수 단언 | 8c5e4878 |
| F10 major mid 값이 출력뿐 | 고친다 | 성립 | 명시 대기 지점: 닫기 붙잡기(__CLOSE_HOLD) → 응답 도착 표지(__attached·__made) → 「삭제 진행 중」(aria-busy) 필수 단언 → 풀기 · R7b·R9d·R9e | 8c5e4878 |

### 회차 2 검증(실측)
- bun test 3533 = 통과 3445 · 건너뜀 88 · 실패 0 · tsc 0 · 번들 OK
- 고치기 전 붉음: R11 3(774aed19 번들) · 단위 4(F3·F5·F7·F7/F6 배선 — 8c5e4878 main.ts) · ⑮ ⌘T 2(70a9a501 번들)
- 화면 게이트(최종 머리): 709884d4 · 05:05~05:22 · race 108/0 · focus 72/0 · seatrows 75/0 · pillar 77/0 · seatgroup 8/0 · rolereuse 11/0 · stty 7/0(cysd·cys 빌드 포함) · 전부 RESULT PASS (그 뒤 커밋 = 문서뿐)
- 뮤턴트(회차 2): 8개 — 죽음 6 · 홀로 살아남음 2(서로 덮는 두 겹)
  N2 두 번째 await 뒤 재판정 제거 = 죽음(closecallbacks F3) · N3 정상 render 의 표식 소비 제거 = 죽음(kbrestore F5) · N4 hadRuntime 무시 = 죽음(배선 핀) ·
  N5 noteDeptDaemonUp 본문 비움 = 죽음(closecallbacks F7) · N6 단축키 앞 편집 확정 제거 = 죽음(⑮ 2) ·
  N1 폴백 조건을 current().socket 로 되돌림 = 홀로 살아남음 — 붙이기 직전 소켓 단언이 그 좌석을 거둔다 · N1b 소켓 단언 제거 = 홀로 살아남음 — cwSock 폴백이 다른 데몬 좌석을 만들지 않는다 ·
  N1c 둘 다 제거 = 죽음(R11 붉음 3) → F1 은 두 겹 방어(한 겹만으로도 막힘 · 둘 다 빼야 뚫림)

### 알려진 동작 추가(릴리스 노트 초안 · F2)
- 좌석을 만드는 사이 그 작업공간을 지웠는데 그 좌석이 끝내 닫히지 않으면(드문 경우), 그 좌석을 잃지 않도록 새 작업공간에 담아 보여 줘요 — 알림이 함께 뜨니 직접 닫아 주세요.
- (실측 · 이 티켓 전부터 같음) 좌석 이름을 고치는 중에 위쪽 탭을 누르면, 첫 번째 누름은 이름만 확정되고 탭은 그대로예요. 한 번 더 누르면 바뀌어요.

### 다음 판 후보(F2 · 이번 범위 밖 = 박사님 C안 화면 구조 변경 0)
- 닫히지 않은 새 좌석을 일반 작업공간으로 되살리지 말고, 「회수 대기 좌석」 영역(좌석 번호·데몬·닫기 실패 사유 · 다시 닫기 단추)에 모아 보여 주는 안.
- 사람이 고를 때만 작업공간에 되돌림 — 새 화면 요소라 박사님 결정 뒤.

### 남김(정직)
- PLAUSIBLE ①② (3R 표 그대로) · ③ 탭 클릭 첫 누름 유실(위 알려진 동작 · 원인 추정 = 확정 처리 뒤 탭 머리 줄 교체로 클릭이 사라짐 · 미검증 · 이번 차이 밖)
- F6 장면 자체(기동 중 ⌘T + 그 작업공간 삭제 겹침)는 재현하지 않았다 — 막은 것은 판독으로 찾은 길이고 시험은 배선 핀뿐
- 「삭제 완료 알림」(settleWsDelete)은 탭 닫기·그룹 삭제 두 길만 · 다른 길(purgeDept·대기 탭 롤백)은 「삭제 중」 표지를 세우지 않아 기다림이 생기지 않는다(whenWsDeleteSettled 는 deleting 이 없으면 즉시 풀림)

## 원작자 병합 때 볼 것
- 새 의존 1 = unicode-normalization =0.1.26(D7 · master#cb40d4a3 · Cargo.lock 변화 = 그 크레이트 1 항목 · 그 의존 tinyvec 은 이미 있음 · 저장소에 cargo deny·라이선스 검사 장치 없음 확인 · 라이선스 (MIT OR Apache-2.0) AND Unicode-3.0).
- cysd surface.list 행에 size{rows,cols} 추가(순수 additive · D5).
- (D4-b · master#8258a495) state.rs 의 parent_any_user·proc_stat_fields = fix/1115-caller-check(950) caller_class.rs 와 글자 그대로 같은 사본(handlers.rs 에 두면 소스 핀 live_cwd_goes_through_single_helper 「handlers.rs 운영 구간 libproc 직접 호출 0」 이 붉다 → proc_brief 옆 state.rs) — 그 가지가 들어오면 이쪽 사본을 지우고 caller_class::parent_any_user 를 부른다(handlers.rs parent_pid_of 한 곳).
- handlers.rs 의 이 티켓 단위 시험 모듈(seat_group_name_tests·ui_caller_tests)은 파일 끝에 둔다 — 소스 핀 시험 여럿이 첫 #[cfg(test)] 앞을 운영 코드로 자른다(중간에 두면 14개가 붉다 · 실측).

## 함정
- ★명령을 `&&` 로 이을 때 bun test 결과를 보지 않고 커밋으로 넘어가지 마라 — 6a8840c5 가 1 실패로 커밋돼 d5abef35 로 바로잡았다(그 뒤 커밋은 「tsc 0 ∧ 0 fail 일 때만」 조건문).
- 소스 추출 시험 대역(closecallbacks·b230scroll·roleactivity·deptprogresswiring)에 새 자유 이름을 더해야 한다: seatVisible·createdInTab·forgetEndedSeatGroup·repairHiddenFocus·noteSeatSize·tabPillarMemo·gridCell·recomputeTabPillar·lastSeatRow.
- render 를 사람 손(탭 클릭·좌석 줄 넓게 보기·상황판 이동)에서 부를 땐 renderByUser() — 그냥 render() 면 숨은 포커스가 「사람 손 아님」 으로 처리돼 탭이 좌석을 따라가거나 「포커스 없음」 이 뜬다.
- closeguard 시험이 exited 판정 두 줄(`if (s.exited) exitedPaneKeys.add(...)` / `else exitedPaneKeys.delete(...)`)의 모양을 고정한다 — 그 줄을 블록으로 바꾸지 마라.
- json! 매크로 값 자리에 `{ … }` 블록을 쓰면 JSON 객체로 읽힌다 → 도우미 함수로(surface_size_wire).
- JS trim() 은 BOM(U+FEFF)까지 자르고 Rust str::trim 은 안 자른다 — 이름 규칙은 \p{White_Space} 로만 자른다(cleanGroupName).
- grid_gate 는 2b-2 캡처 폴더에 덮어쓴다 → 다시 돌릴 땐 캡처 폴더 인자를 스크래치로(2b-2 CAPTIONS.md 숫자 보존).
- 소스를 문자열로 떼어 돌리는 시험이 많다(`roleactivity.test.ts` · `deptprogresswiring.test.ts` · `b230scroll.test.ts` 의 대역 목록). main.ts 함수에 새 자유 이름을 쓰면 그 대역에 이름을 더해야 한다(ReferenceError 로 실패).
- style.css 의 첫 `@media (prefers-reduced-motion` 앞까지를 읽는 시험이 있다(roleactivity.test.ts) — 새 @media 블록을 역할 점 규칙보다 앞에 두지 마라(기존 블록에 줄을 더한다).
- 시험 장치(e2e) 계정 목록이 비면 사용량 막대가 안 그려진다(accountRates 는 updated_at 없는 계정 무시) — 결함 아님.
- playwright = `~/axdev/GlobalNews-Crawling-AgenticWorkflow/.venv/bin/python3`(읽기만) · 브라우저 판 불일치 → `CHROME_PATH=$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell`.
- 커밋 전에 `bunx tsc` 를 먼저(2693c9ab 를 한 번 바로잡았다).
- cargo 는 PATH 에 없다 → `export PATH=$HOME/.cargo/bin:$PATH` · `cargo test --test hidden_seat_screen`(≈15초 · 끝나고 `pgrep -fl cys-hss` = 0).
- 상황판 수를 읽는 e2e 는 `.ws-board-num` 만 읽는다(버튼엔 글자 라벨도 있다 · 476e73e3 에서 한 번 NaN).
- ★clap: `Command` 열거에 변형을 하나라도 더하면(별도 평탄화 열거로도) debug 시험 스레드(2 MiB) 스택이 넘친다 — 새 최상위 동사는 기존 `VendorAuxCommand` 안에 + 인자는 따로 둔 Args 구조체(cfbe352d 실측).
- ★clap 스택 여유 실측(12:1x · 시험 바이너리 RUST_MIN_STACK 이분): `tests::a3_strip_hook_digits_only_for_the_seven_target_verbs_when_the_rest_is_leftover_args` 통과 문턱 = 2d 전(a54b3b76) 2032~2040KiB · 지금 2040~2044KiB(2d 가 ≤8KiB 더함) · 시험 스레드 한도 2048KiB → 전체 실행 때 간헐 넘침(1회 재현 · 단독은 통과). 처리 = master 판단 대기(【확인요청】 에 올림).
- `cargo test` 여러 대상을 한 번에 돌리면 첫 실패에서 멈춘다 → `--no-fail-fast`. `cargo test --bin cys` ≈ 13분(부하 시).
- 흔들린 시험(이 티켓에서 고치지 않음 · master#608306ca): cysd `native_publication::…np_windows_real_candidate_change_restarts_sample_confirmation` · `…np_native_same_pid_exec_is_changed_not_agent_death` · `send_settle_tests::settle_hold_denies_text_while_submit_cr_inflight_then_admits` — 전체 실행 중 load 7~9 에서 실패 · 단독 각 3/3 통과.
- 부하(load 5~7) 중엔 격리 데몬 시험이 20초 기동 대기를 넘길 수 있다(hidden_seat_screen 1회 · 단독 PASS) · cysd `np_windows_real_candidate_change_restarts_sample_confirmation` 도 부하 중 1회 실패 · 단독 3/3 PASS(이 티켓 무관 구역).
- dragdrop_gate.py 는 CHROME_PATH 를 안 받아 이 기계에서 브라우저 판 불일치로 못 돈다(환경 · 회귀 아님).

## 재현
```
cd ~/axdev/.wt/cys-tabs-sidebar/ui && bun install --silent && bun test && bunx tsc -p tsconfig.check.json
cd .. && sh ui/build.sh
export CHROME_PATH=$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell
for g in seatrows_gate statusboard_gate cc_button_gate nodept_gate seatgroup_gate; do cys run -- ~/axdev/GlobalNews-Crawling-AgenticWorkflow/.venv/bin/python3 ui/e2e/$g.py; done
```
캡처 = `docs/evidence-tabs-sidebar/{1b,1d,1e,1h}/`(커밋하지 않음).

## canary 확인 항목 2 (master#9278e6ab · 1.1.15 묶음 빌드 canary 단계 · 동결 11-18 뒤 · master 집행 · 격리 프로필 실앱)
1. 재실행 탭 배치 동일 — 앱 종료 → 재실행(+ 데몬 재부팅으로 좌석 번호 재발급) 뒤 활성 탭·넓게 보기 좌석·옮긴 묶음·탭 순서가 같다(헤드리스 대역 = ui/e2e/restart_gate.py · 실앱 미확인).
2. 워커 0·1 새 단추 0 — v1.1.14 와 나란히 놓고 상단 막대 새 단추 0 · 질문 창 0(헤드리스 대역 = ui/e2e/baseline_gate.py · 실앱 미확인).
3. (948 · master#07acca07) 한글 조합 중 탭 전환 — 실앱(WKWebView)에서 조합 중이던 글자가 어디로 가는가(헤드리스 Chromium = 버려짐 · 숨은 좌석으로 0 · 다음 글자 = 보이는 좌석 = focus_gate ⑧). 숨은 좌석으로 가면 결함.
4. (948 D1·D6) 실앱에서 탭을 바꾼 뒤 ⌘W·⌘D·글자 입력이 보이는 좌석을 잡는가(헤드리스 대역 = focus_gate · WKWebView 포커스·키 이벤트 차이 확인).
5. (1R 경고 · master#1dc9bd83) 실앱에서 입력 중인 좌석을 `cys seat-group` 으로 다른 묶음에 옮기면 탭이 따라가고 이어 친 글자가 그 좌석으로만 가는가(헤드리스 대역 = focus_gate ⑨ ⑩).
6. (2b-3) 박사님 노트북(1371)·싱글(1920)·4K 프로필(2786) 실창에서 기둥 열 수 = 64·76·96 근처인가(헤드리스 대역 = pillar_gate · 캡처 2b-3/).

## 알려진 한계
- (948 D3) 앱이 꺼져 있는 동안 좌석이 끝나고 같은 역할명이 재배정되면 끝 신호를 못 봐 옛 묶음을 물려받는다(설계 §5 · 📌 데몬 정체 비교안).
- (948 D2) 탭 화면에서 만든 새 좌석의 「지금 탭」 소속은 앱이 켜져 있는 동안만 — 앱을 다시 켜면 생성 폴더 묶음으로.
- (948 D4) 좌석이 띄운 고아 자식·다른 데몬 좌석의 호출 = 좌석 밖 터미널과 구별 불가(영향 = 앱 배치·컨트롤 센터 열기뿐 · 기존 RPC 같은 근거 = master 별도 티켓).
- (2b-3) 1371 에서 좌석 4개 이상 = 40열×12줄을 함께 지킬 격자가 없어 36열 칸(가장 덜 모자란 격자 · 지시서 규칙대로).
- 역할·폴더가 둘 다 없는 좌석(외부 좌석)을 넓게 보다가 앱을 다시 켜면, 그 좌석의 정체를 끝내 알 수 없어 넓게 보기 저장값이 화면엔 안 보인 채 상태에만 남을 수 있다(화면 정상 · bf24c380 의 보존 규칙 탓 · master#9278e6ab 「알려진 한계」로 둠).

## master 결정(master#fcbc46fb · #608306ca · #9278e6ab · 확정)
- cys 시험 스택 = A + 감시 시험(master#9278e6ab): .cargo/config.toml [env] RUST_MIN_STACK 4MiB(force=false) + cys.rs `cli_parse_fits_2mib_plus_64kib_stack_guard_because_cargo_config_raises_test_stack`(자식 프로세스 · 예산 2MiB+64KiB — 정확히 2MiB 는 오늘 문턱 2040~2044KiB 라 들쭉날쭉 · 대조 = 예산 1900KiB 로 낮추면 이 시험만 FAILED 확인).
- 실앱 캡처 = 이 티켓에서 안 함 → 위 canary 확인 항목 2.
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
