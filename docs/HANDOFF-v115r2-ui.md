# HANDOFF — cysr 1.1.5 6차 트랙 UI · D5(윈도우 대체 화면 스크롤 불가) · 2026-09-23

TICKET=v115r2-ui · 브랜치 `fix/v115r2-ui`(← 848b3f69 = v1.1.5) · 워커 surface:917 · 발주 master.
⛔판번 bump 없음 · push 0건(master 재승인 대기) · 우리 맥 라이브 cysr 무접촉(코드 + 로컬 pty 만).

---

## 0. 한 줄

윈도우에서 「휠이 아무것도 안 한다」던 것은 **우리 가드가 휠을 버리고 있었기 때문**이고(경로 실측),
이제 버리지 않고 **PgUp/PgDn 으로 번역해 앱에 보낸다**(게이트 1키로 커서 키 전환 가능).

## 1. 결함의 실제 경로 — 【관측】 (브리프의 원인 추정과 갈린 지점)

브리프는 D5 의 원인을 「`mousefilter` 가 휠을 앱으로 forward → 앱이 트래킹 미요청이라 무반응」으로
적었고 수리 자리를 `mousefilter.routeOnData` 로 지목했다. **코드를 읽어 보니 그 자리는 윈도우에서
도달하지 않는다.** 실제 사슬은 이렇다:

1. `trackfilter` 는 윈도우 인스턴스를 `consume=false` 로 만들고 MOUSE_PARAMS 8종(9·1000·1002·
   1003·1005·1006·1015·1016)을 **출력에서 전부 스트리핑**한다(ConPTY 결함 1호 차단).
   ⇒ xterm 은 윈도우에서 마우스 트래킹에 **결코 진입하지 않는다**(`mouseTrackingMode` 상수 "none").
   ⇒ xterm 이 마우스 보고를 만들지 않으므로 **`routeOnData` 의 wheel 갈래는 윈도우에서 도달 불가**다.
   (거기 수리를 넣었으면 시험은 초록인데 실기는 그대로인 죽은 코드가 됐다.)
2. 그 대신 xterm 은 **대체 화면(스크롤백 없음)의 휠을 방향키로 스스로 합성**한다 —
   벤더 번들 `@xterm/xterm 5.5 lib/xterm.js` 의 "wheel" 리스너 실측:
   `if (customWheelEventHandler && false === customWheelEventHandler(e)) return false;`
   → `if (!buffer.hasScrollback) { t = viewport.getLinesScrolled(e); ... ESC + (DECCKM?"O":"[") + (deltaY<0?"A":"B") ×|t| → triggerDataEvent }`
3. Claude Code fullscreen 은 1003 을 켜므로 `shouldSuppressWheelWin` 이 충족되고, 우리 핸들러가
   `false` 를 돌려주면서 **2의 합성까지 함께 죽었다** ⇒ 휠 무동작 = D5.
   이것은 `wheelgate.ts` (b) 가 「과잉 억제의 관측 형태」로 **예고해 둔 바로 그 현상**이다
   (다만 1003 오판이 아니라 **정상 충족**으로 일어났다).

## 2. 수리 — 억제는 유지, 처분을 바꾼다

- 새 순수 모듈 `ui/src/altscroll.ts` — 억제 술어(무수정)를 **불러** 판정하고, 억제되는 휠을
  키 시퀀스로 번역한다: `pass`(xterm 기본 처리) / `consume`(보낼 것 없음) / `translate`(pty 전송).
- 배선 = `main.ts` 의 win 휠 핸들러 한 곳. mac 경로·`wheelgate.ts` 술어·16/32조합 진리표는 **무수정**.
- 줄 수 소유권을 우리가 가져왔다: `deltaMode=DOM_DELTA_PAGE` 에서도 **rows 를 곱하지 않고**
  이벤트당 `MAX_LINES_PER_EVENT=12` 로 자른다(벤더 경로에 있던 증폭 — wheelgate (c) 가 남긴 우려 —
  이 구조에서는 불가능).
- 안내(B1 ② 확장): 대체 화면엔 `viewportY` 축이 없으므로 「위로 연속 + 첫 행 지문 무변화」가
  문턱(3)에 닿으면 앱 세션당 1회 「더 위는 Ctrl+O」 토스트.

## 3. ★기본 동작을 브리프와 다르게 정했다 — 근거와 되돌리는 법

브리프: 「기본 = 커서 키 번역, 폴백(기본 off) = PgUp/PgDn」.
구현: **기본 = PgUp/PgDn**, 게이트 1키로 커서 키. 바꾼 이유는 실측 둘이다.

| 실측 | 방법 | 결과 |
|---|---|---|
| Claude Code 2.1.280 · inline · 프롬프트에 글자 있음 + `ESC[A` | 로컬 pty(80x24) | 화면에 **History 5/5** · 입력줄이 과거 입력으로 **교체** = 프롬프트 히스토리 오염 |
| 같은 상태 + `ESC[5~`(PgUp) / `ESC OA`(SS3) | 로컬 pty | 무반응(17·16 바이트, 화면 무변) |
| 번들 정적 판독(2.1.280 단일 실행파일 내장 JS) | `grep -abo` + 오프셋 슬라이싱 | `Chat: { up:"history:previous", down:"history:next" }`(@177,028,660) · **Scroll 컨텍스트에 up/down 바인딩 없음** · 입력창이 방향키를 **항상 소비**(@185,158,314) |
| 같은 판독 | | `case "pageup": if (fullscreen \|\| ctrl) return;`(@185,160,212) ⇒ **fullscreen 에서만** 입력창이 흘려보내 `scroll:pageUp` 이 뷰포트 ½ 스크롤(@196,489,302) |
| 같은 판독 | | 앱이 이 오용을 **탐지해 경고**한다: "Scroll wheel is sending arrow keys · use PgUp/PgDn to scroll"(@196,493,995) + 100ms 내 동일 방향키 8개 버스트 텔레메트리(@183,091,950) |

⇒ 번역이 실제로 가 닿는 앱군(1003 을 켜는 fullscreen 앱 = Claude Code 계열)에서 **커서 키는
transcript 를 굴리지 못하고 프롬프트만 오염시킨다.** PgUp 은 최악이라도 **지금과 같은 무동작**이다.
「나빠질 수 없는 쪽」을 기본으로 둔다. ★이 판단은 master 【확인요청】 대상이고, 뒤집기는 아래 1키다.

- 커서 키로 전환: `CYS_ALT_SCROLL_CURSOR=1` 또는 `~/.cys/alt-scroll-cursor` 파일
  (PowerShell: `New-Item -ItemType File -Force $HOME\.cys\alt-scroll-cursor`) ·
  개발자용 localStorage `cysAltScrollCursor="1"`.
- 번역 자체를 끄고 **종전(무동작)** 으로: `CYS_WIN_WHEEL_GUARD_OFF=1` 또는 `~/.cys/win-wheel-guard-off`
  (핸들러 미등록 = xterm 기본 합성 = 방향키가 그대로 나간다 — 오염 위험은 그쪽이 더 크다).

## 4. 로컬 pty 실측 표(번역 시퀀스가 실제로 굴리는가) — 【관측】

| 대상 | 대체 화면 | `ESC[A/B`(CSI) | `ESC OA/OB`(SS3) | `ESC[5~/6~`(PgUp/Dn) |
|---|---|---|---|---|
| less 634 | `?1049h` 진입 · **DECCKM `?1h` 켬** | **무시 + BEL**(상태줄에 `ESC[B` 표시) | **1줄씩 스크롤**(L0024·L0025·L0026) | **한 화면씩**(23줄) |
| vim (`-u NONE`) | `?1049h` 진입 | 커서 이동 → 화면 경계에서 스크롤 | (미측정) | **한 화면씩** |
| Claude Code 2.1.280 | **inline**(우리 맥에서 fullscreen 강제 실패) | **히스토리 오염**(History 5/5) | 무반응 | 무반응(inline 이라 정상 — §3 참조) |

- less 가 CSI 를 무시하고 SS3 만 먹는 것이 **DECCKM 분기가 장식이 아님을 증명**한다(우리도 벤더와
  동일하게 `term.modes.applicationCursorKeysMode` 로 가른다). 단 less/vim 은 애초에 번역 경로를
  타지 않는다(억제 술어 불충족 = `pass`) — 이 표는 **번역 시퀀스의 유효성** 검증이다.
- 【미측정】 Claude Code **fullscreen**: settings `tui` 키를 줘도 `?1049h` 미발화(롤아웃 게이트).
  박사님 윈도우 실기가 최종 판정이다.

## 5. 시험·게이트 실측

| 항목 | 결과 |
|---|---|
| `bun test`(ui 전건) | **1098 pass · 0 fail · 39 files**(신규 `altscroll.test.ts` 26건 포함) |
| 뮤테이션 6종 | **전건 KILLED**(아래) · 기준선 초록 · 복원 후 sha256 일치 |
| `bunx tsc -p tsconfig.check.json` | 오류 7건 = **전부 선재**(headerlabels·restorebrief·updateplan 시험 파일 · 내 파일 0건) |
| `sh ui/build.sh` | `main.js 0.51 MB` · dist 생성 |
| `bash scripts/secret-scan.sh --all` | **clean · rc=0**(1073 파일) |
| `cargo test --bin cys-app` | **162 passed · 0 failed · 1 ignored**(현 트리 재실행) |

뮤턴트(전건 적용 확인 후 실행 · NOT-APPLIED 0):
`M1 번역 제거(translate→consume)` · `M2 방향 뒤집기(A↔B)` · `M3 PAGE 증폭 재도입(×24)` ·
`M4 배선 절단(sendRaw 제거)` · `M5 pass→false(less/vim 회귀)` · `M6 DECCKM 무시(항상 CSI)` — 6/6 KILLED.

## 6. 남은 것 · 다음 사람에게

- 🔴**박사님 윈도우 실기 판정 절차**(순서대로, 한 단계마다 되돌릴 수 있다):
  ① 새 빌드에서 Claude Code 전체화면 pane 에 휠을 굴린다 → **화면이 반 쪽씩 오르내리면 성공**.
  ② 아무 일도 없으면 `~/.cys/alt-scroll-cursor` 를 만들고 cysr 재시작 → 다시 굴린다.
     이때 **프롬프트가 과거 입력으로 바뀌면 즉시 그 파일을 지워라**(오염 = 원 결함 재현).
  ③ 둘 다 실패면 `~/.cys/win-wheel-guard-off` 로 가드 전체를 내리고 master 에 보고 —
     그 경우 남는 길은 아래 「더 나은 정공법」(휠 보고 전달 복구)뿐이다.
- ★**더 나은 정공법(범위 밖 · master 판정)**: 번들 판독상 앱은 SGR 휠 보고를 스스로
  `wheelup → scroll:lineUp`(가속 포함)으로 처리한다(@183,025,692). 즉 윈도우에서 **휠 보고만
  앱에 전달되면 번역이 아예 불필요**하다. 막고 있는 것은 ConPTY 결함 1호 대응(트래킹 DECSET
  전량 스트리핑)이고, 재개방은 **윈도우 실기 계측**(휠 보고만 통과시켰을 때 리터럴 타이핑이
  재발하는지)이 선행 조건이다. 이번 티켓에서는 손대지 않았다.
- 【미측정】 안내 토스트의 「화면 무변화」 근사는 **첫 행 지문 한 줄**이다. 첫 행이 매 프레임 바뀌는
  앱(시계·스피너)에서는 연속이 끊겨 **안내가 뜨지 않는다**(오발보다 미발을 택한 방향).
- 【미측정】 `arrow-burst` 경고(100ms/8키)가 실제로 뜨는 노치 수 — 커서 키 모드를 쓸 때만 관련.

## 7. 4군 점검 (cys 개발자 ANCHOR — 내 변경이 각 군에 닿는가)

- **① 폭주 큐** — **닿는다(늘리는 쪽 · 상한 있음)**. 종전에는 억제된 휠이 **아무것도 보내지 않았는데**,
  이제 휠 이벤트 1건당 `send_input` invoke 가 1회 생긴다. 상한은 코드가 쥔다 —
  이벤트당 페이지 ≤3(= `ESC[5~` 3개) 또는 줄 ≤12, `deltaY=0`·shift·가로 휠은 `consume`(0건).
  발화원이 **사람 손가락뿐**이고 자동·타이머 경로가 없어 폭주 축(재시도·팬아웃)과는 성격이 다르다.
- **② 무clear 100%+** — **해당 없음**. 각성 주입 문자 수·`core_inject`·resume 상한에 닿는 변경이 0줄이다
  (이 티켓은 브라우저 층 휠 처리와 Tauri 게이트 커맨드 1개뿐).
- **③ 자가치유 전멸** — **해당 없음**. `javis_phoenix.py`·`schedule.rs`·topology·respawn-cap 무접촉
  (`git diff --stat` 이 근거 — 변경 파일 5개 전부 ui/src·src-tauri/src/main.rs·docs).
- **④ 전 pane 사망** — **해당 없음**. `wsreconcile.ts`·pane 생존 판정·입양 경로 무접촉. 최악의 사고 반경은
  **휠 핸들러 1개**이고, 그 안에서 예외가 나더라도 xterm 리스너 한 건의 실패라 pane 의 입출력(onData·
  write)은 별 경로로 살아 있다. 되돌림은 게이트 1키(§3)로 코드 재배포 없이 가능하다.

## 8. 변경 파일

| 파일 | 성격 |
|---|---|
| `ui/src/altscroll.ts` | 신규 · 순수 판정/번역 + 대체 화면 안내 상태기 |
| `ui/src/altscroll.test.ts` | 신규 · 26 단언(계약 4종 + 호출부 계수) |
| `ui/src/main.ts` | win 휠 핸들러 번역 배선 · 게이트 1키 판독 · 낡은 (d) 주석 정정 |
| `ui/src/wheelgate.ts` | **주석만**(예고가 실현됐음을 박제) · 술어·진리표 무수정 |
| `src-tauri/src/main.rs` | `alt_scroll_cursor_mode` 게이트 커맨드 추가(형제 게이트 3종과 동형) |
