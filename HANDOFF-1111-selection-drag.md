# HANDOFF — 선택 블록 잔류 (TICKET=cysr-stuck-selection-drag · 2026-10-29)

브랜치 `fix/1111-selection-drag` (← int/1111 eb4ef98c). **로컬 커밋만 — push·int/1111 병합·앱 빌드 설치는 master 게이트.**

| 커밋 | 내용 |
|---|---|
| 46b61753 | 수리 본체 — `ui/src/selectiondrag.ts`(판단) · `main.ts` 배선 10줄 · 단위 시험 7 · 재현 게이트 `ui/e2e/selection_drag_gate.py` |
| (이 문서) | HANDOFF |

## 증상 (박사님 영상 · ~/Downloads/KakaoTalk_Video_2026-10-28-22-53-07.mp4 · 25초)
클릭 없이 커서만 움직였는데 연보라 선택 블록이 커서를 따라 늘어난다. 커서가 위로 가면 화면이 스크롤되며 선택이 계속 커진다
(1초 간격 프레임 25장 확인).

## 원인 — 관측과 추정을 갈라 적는다

### 【관측】 기제 — xterm 5.5.0 의 선택 끌기는 mouseup 만 믿는다
- 출처: `ui/node_modules/@xterm/xterm/src/browser/services/SelectionService.ts`(판 5.5.0 = bun.lock 핀).
  · `handleMouseDown` → `_addMouseDownListeners`: **document** 에 mousemove·mouseup 처리기 + 끌기 스크롤 타이머(setInterval).
  · `_handleMouseMove`: `event.buttons` 를 **보지 않고** 선택 끝점을 커서 위치로 옮긴다. 커서가 화면 위·아래 밖이면 타이머가 스크롤까지 한다(영상의 스크롤).
  · 처리기를 떼는 곳은 `_handleMouseUp`(+ setSelection·dispose)뿐.
  · 덤: 뗌 없이 다시 누르면 `_dragScrollIntervalTimer` 를 덮어써 옛 타이머가 고아로 남는다.
- ⇒ **웹뷰가 mouseup 한 번을 못 받으면, 단추를 뗀 뒤의 모든 커서 이동이 선택을 늘린다** = 영상 증상과 일치.
- 헤드리스 재현(Playwright WebKit 27.2 · Chromium 156 · 진짜 입력 경로):
  | 칸 | 대조군(같은 판 순수 xterm 페이지) | 실제 앱 번들(ui/dist + Tauri 대역 · 수리 전) |
  |---|---|---|
  | A 정상 뗌 → 커서 이동 | 선택 불변 | 선택 불변 |
  | B 뗌 유실 → 커서 이동 | **선택이 커서를 따라 늘어남**(아래끝 153→357px) | **같음**(207→387 · 225→429) |
  | C 끄는 중 요소 재배치 + 정상 뗌 | 불변 | — |
  | D 끄는 중 휠 + 정상 뗌 | 불변 | 불변 |

### 【관측】 앱 JS 는 mouseup 을 삼키지 않는다
- A 칸: 앱 번들에서도 정상 뗌이면 잔류 0(WebKit·Chromium).
- 코드 판독: `main.ts` 의 창 capture mouseup 처리기(pane 끌기 4672 · ws 탭 5527 · 그룹 5576 · 상단바 6421 · 파일트리 7580 · 사이드바 폭 11631 부근) 전부 stopPropagation 없음 — master 1차 판독과 같음.

### 【관측】 master 이월 후보 ②③ 은 잔류를 만들지 않는다
- ② pane mousedown → setFocus: `setFocus`(main.ts 5149~)는 클래스 토글 + `term.focus()` 뿐 — **재렌더하지 않는다**(코드 판독). 끄는 중 터미널 요소를 DOM 에서 뗐다 붙여도(C 칸) xterm 처리기가 document 에 있어 뗌을 받는다.
- ③ 끄는 중 휠: D 칸 잔류 0.

### 【추정】 실기에서 mouseup 이 웹뷰에 안 오는 계기 — 미확정
- 후보 ① 창 밖에서 뗌 · 끄는 중 앱 전환(⌘Tab)·알림/다른 창이 앞에 뜸 · 미션컨트롤 등 시스템 제스처 · 비활성 창 첫 클릭. 헤드리스로는 OS 층 배달을 재현할 수 없어 어느 것인지 가리지 못했다.
- 정황(관측): 이 코드베이스는 같은 웹뷰에서 이미 「창 밖에서 떼면 mouseup 이 안 올 수 있다」를 전제로 방어해 왔다 — `main.ts` 상단바 끌기 `if (!(e.buttons & 1)) return cancel("blur")`(codex 2R·3R) · 사이드바 분할선 `window blur → dividerDragActive=false`(Fable 적대 3R ③). 터미널 선택 끌기에만 그 방어가 없었다.
- ⇒ 수리는 계기와 무관하게 「뗌을 놓쳤다는 증거」를 보고 끝내는 방식이라, 어느 계기든 막는다.

## 수리 (46b61753)
`ui/src/selectiondrag.ts` `armSelectionDragGuard` — 창 capture 로 듣는다(xterm 의 document 처리기보다 먼저):
- 터미널(`.xterm`) 위 왼쪽 단추 누름 → 지켜보기 시작(마지막으로 눌린 채 있던 좌표 기록).
- 다음 중 하나면 **뗌을 놓친 것**으로 보고 그 좌표에서 합성 mouseup 을 document 에 보낸다 → xterm 이 정상 뗌처럼 끝낸다(선택은 **지우지 않고** 그 자리에서 확정):
  1. 단추가 떼어진 채 이동(`!(e.buttons & 1)`) — 상단바 끌기와 같은 판단
  2. 창 blur(요소 blur 는 무시 — `e.target === window` 만)
  3. 뗌 없이 새 누름(→ xterm 고아 타이머도 막힘)
- 진짜 mouseup 이 오면 지켜보기만 끝낸다(끼어들지 않음). 합성 mouseup 이 다시 지나가도 되풀이 0.
- `main.ts` 배선 1회(pane lifecycle 머리) · **플랫폼 분기 없음 = 맥(WKWebView)·윈(WebView2) 같은 코드 경로.**
- 마우스 트래킹 중(Claude Code 등)의 누름도 지켜보는데, 그때 합성 mouseup 은 xterm 의 마우스 보고 처리기로 가 「떼기」 보고가 된다 — 놓친 떼기를 앱에 알리는 것이라 맞는 동작으로 판단(윈은 mousefilter 가 보고를 버림).

## 시험 — 재현 명령
```sh
cd ui && sh build.sh                     # dist 갱신(bun install 포함)
bun test src/selectiondrag.test.ts       # 7 pass
bun test                                 # 3278 tests · 0 fail (85 skip = 기존)
bunx tsc -p tsconfig.check.json          # 0
# 헤드리스 게이트(저장소 밖 venv 권장: pip install playwright && playwright install webkit chromium)
python3 ui/e2e/selection_drag_gate.py    # 36/36 PASS · exit 0
```
- 게이트 칸: A 정상 · B 뗌 유실(수리 후 불변 + 복사 텍스트가 뗀 자리 line03~line08 에서 끝남) · C 재배치(대조군) · D 휠 · E 뗌 유실 후 창 blur · F 회귀(끌기 선택 6행 그려짐 · 복사 = xterm copy 처리기 경로 line03~line08 · 더블클릭 단어 = 'alpha') · pageerror 0. 대상 = 대조군 + 앱 × WebKit + Chromium.
- 뗌 유실 흉내 = 페이지 스크립트보다 먼저 붙는 창 capture 처리기(init script)가 mouseup 을 삼킨다 → 앱·xterm 어떤 처리기도 못 본다(웹뷰 미배달과 같은 상태).
  ⚠함정(실제로 한 번 밟음): 흉내 처리기를 페이지 로드 **뒤에** 붙이면 수리 처리기가 뗌을 먼저 봐서 수리된 앱이 거짓 적색이 된다.
- **뮤테이션**: main.ts 의 `armSelectionDragGuard({` 를 `if (false) armSelectionDragGuard({` 로 바꿔 빌드 → 게이트 exit 1 · 적색 6칸(webkit·chromium × B 불변 · B 복사 · E blur). 복원 → exit 0.

## 박사님 실물 시험 필요 (헤드리스가 대신 못 하는 것)
설치본 교체는 master 게이트 — 아래는 이 수리가 든 빌드를 설치한 뒤.
1. 맥: 터미널 글을 끌어 선택 → **창 밖(바탕화면·다른 앱 위)에서 단추를 뗌** → 창 안으로 커서만 움직임 → 선택이 따라 늘지 않아야 한다(뗀 순간 범위로 고정).
2. 맥: 끌어 선택하는 도중 ⌘Tab 으로 다른 앱 → 돌아와 커서만 움직임 → 따라 늘지 않아야 한다.
3. 일반 회귀: 끌어 선택 → ⌘C → 붙여넣기 · 더블클릭 단어 · 세 번 클릭 줄 · Claude Code 가 떠 있는 pane 에서 Option+끌기 선택·복사 · 창 위·아래 밖으로 끌어 자동 스크롤 선택.
   ⚠이 항목이 잔여 위험의 검증이다: 실기 WKWebView 가 **눌린 채 끄는 중에 buttons=0 을 보내는 경우**가 있다면 끌기 선택이 일찍 끊긴다. 헤드리스 WebKit·Chromium 은 buttons 를 정상 보고했고, 같은 웹뷰의 상단바 끌기가 이미 같은 판단(`e.buttons & 1`)으로 출시돼 있다 — 그래도 실물 확인 전까지는 【추정】.
4. 윈도: 1~3 같은 순서.
5. 영상 상황(평소 사용 중 갑자기 선택이 커서를 따라옴)이 며칠간 재발하지 않는지 관찰.

## 남은 일 · 범위 밖
- 실기에서 mouseup 이 사라지는 정확한 계기(【추정】 칸)는 미확정 — 재발 시 그때 무엇을 했는지(창 밖 뗌·앱 전환·알림) 메모가 있으면 확정 가능.
- 같은 「mouseup 유실」 노출이 앱의 다른 끌기에도 있다(pane 머리 끌기 `main.ts` ≈4672 · ws 탭 ≈5527 · 그룹 ≈5576 · 파일트리 ≈7580 · 사이드바 폭 ≈11631 — 상단바 끌기만 방어됨). 이번 티켓 범위 밖이라 손대지 않음 — 필요하면 별도 티켓.
- 게이트는 CI 미배선(같은 폴더의 다른 e2e 게이트와 같은 수동 실행 관례).
- 이월 없음 → 다음 사람에게 넘길 함정 = 위 「뗌 유실 흉내 처리기는 init script 로」.
