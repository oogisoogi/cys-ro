# HANDOFF — cysr 터미널 글자 렌더를 cmux 와 같게 (TICKET=cysr-cmux-render-parity · 2026-10-29)

브랜치 `fix/1111-render-parity` ← `int/1111` eb4ef98c. **push·병합·빌드·설치 안 함**(master 게이트).

## 박사님 원문(10-28 23:0x)
「폰트를 바꾸어도 얇기, 장평, 자간이 다르고 전체적으로 두껍고 뿌연 느낌이다. 터미널 배경색도 영향이 있을 것 …
최대한 cmux 환경과 비슷하게 구현하자. 배경색까지」

## 바뀐 기본값(전/후) — 맥·윈 공통(같은 `ui/dist` 묶음 · `tauri.windows.conf.json` 에 덮어쓰기 없음)

| 항목 | 전 | 후(= cmux 기본 테마 「Apple System Colors」) |
|---|---|---|
| 터미널 배경 | `#0d1117` | `#1e1e1e` |
| 터미널 글자 | `#c9d1d9`(회청색) | `#ffffff` |
| 밝은 배경일 때 글자 | `#1f2328` | `#000000`(「… Light」) |
| ANSI 16색 | xterm 내장 기본값 | cmux 값(검정 `#1a1a1a` · 빨강 `#cc372e` · … · 밝은 흰 `#ffffff`) |
| 선택 배경/글자 | xterm 기본(반투명 회색) | `#3f638b` / `#ffffff`(밝은 배경 `#abd8ff` / `#000000`) |
| 커서 | xterm 기본(흰색) | `#98989d`, 커서 위 글자 `#ffffff` |
| 칸 크기(JetBrains Mono 13 · 레티나) | 7.83 × 15 px(실은 Menlo 로 잰 값) | **8 × 17 px**(= Ghostty 계산) |
| 한글 크기 | 원래 크기(0.865em) — 두 칸 안에서 뒤에 4px 틈 | 1.214배(= Ghostty `ic_width` 맞춤) |
| 첫 화면 CSS `--bg`·`--canvas-text` | `#0d1117`·`#c9d1d9` | `#1e1e1e`·`#ffffff` |

- 사용자가 저장한 값(배경색·글꼴·크기·굵기)은 **덮지 않는다** — 배경은 저장값 그대로, 글자색·팔레트만 그 배경 밝기에 맞는 cmux 값.
- 근거: `/Applications/cmux.app/Contents/Resources/ghostty/themes/Apple System Colors`(+ ` Light`) 원값 · cmux 바이너리에 같은
  팔레트 내장(strings 실측) · 박사님 스크린샷 화소(배경 #1e1e1e · 글자 #ffffff)와 일치. 사용자 Ghostty 설정 파일은 비어 있음.

## 원인과 수리 — 「장평·자간이 다르다 · 뿌옇다」

1. **★주원인 — 칸을 엉뚱한 글꼴로 쟀다.** xterm 5.5 는 칸 크기를 OffscreenCanvas 로 잰다. WebKit 은 **문서에 안 붙은
   캔버스·OffscreenCanvas 에서 사용자가 설치한 글꼴(JetBrains Mono·D2Coding)을 못 보고 Menlo 로 잰다**(헤드리스 WebKit
   실측: 같은 `13px D2Coding` = 문서에 붙은 캔버스 6.5px ↔ 안 붙은 캔버스 7.83px). 그래서 칸은 Menlo 크기(7.83×15)인데
   글자는 고른 글꼴로 그려져 — D2Coding 은 글자 사이가 20% 벌어지고(가로 999px 이어야 할 줄이 1200px),
   JetBrains Mono 는 17px 짜리 글자가 15px 줄에 끼였다. **「글꼴을 바꿔도 장평·자간이 다르다」의 정체.**
   → `termrender.ts snapCellsToDevicePixels`: 문서에 붙인 숨김 span 으로 다시 재고(높이 = 글꼴 줄 높이), Ghostty 처럼
   장치 화소로 반올림(Ghostty `Metrics.zig calc` = `@round`).
2. **한글 틈** — Ghostty 는 대체 글꼴(한글)을 주 글꼴의 「水」 폭에 맞춰 키운다(`Collection.zig scaleFactor(.ic_width)` ·
   `default_fallback_adjustment = .ic_width`). xterm 은 원래 크기로 그려 한글마다 뒤에 틈.
   → `termFontStack`: 같은 배율의 `@font-face`(local Apple SD Gothic Neo / 맑은 고딕 / Noto Sans KR · 한글 범위만 ·
   `size-adjust`)를 등록해 글꼴 스택의 한글 대체 글꼴 앞에 끼운다. 고른 글꼴에 한글이 있으면(D2Coding) 걸지 않는다.
3. **뿌연 느낌** — 글자색 `#c9d1d9`(회청색)가 흰색보다 어둡다. 같은 문단의 잉크 총량이 기준의 0.79배(JetBrains)·0.85배(D2Coding).
   → 기본 글자 `#ffffff` 로 기준과 1.000배.
4. **두꺼운 느낌** — 헤드리스에서는 재현 안 됨: 수정 후 획 굵기(잉크 총량)가 Ghostty 재현본과 **1.000배**. 글자 다듬기는
   이미 `-webkit-font-smoothing: antialiased`(= Ghostty `font-thicken=false`). ⚠ 박사님 기기 저장값의 **글자 크기 22**
   (cmux 13) 가 「전체적으로 두껍다」의 가장 유력한 원인 — 아래 결정 항목.

## 검수(헤드리스 · 박사님 화면 안 씀)
- cmux 창 직접 캡처는 **화면 기록 권한이 없어 불가**(`screencapture -l` → could not create image). 그래서 기준 = **Ghostty 계산식을
  CoreText 로 그대로 재현한 그림**(실제 cmux 캡처 아님 · 셀·기준선·센터링·한글 배율·smoothing 끔을 원본 코드대로).
- 나란히 캡처: `~/.cys/pack/round/render-parity-2026-10-29/side-by-side-JetBrainsMono.png` · `side-by-side-D2Coding.png`
  (① 기준 ② 수정 후 ③ 수정 전).
- 수치(JetBrains Mono 13 · 2배): 배경 화소 (30,30,30) = 기준 일치 · 칸 8×17 = 기준 일치 · 4줄 가로 끝 위치 차 0~2px / 1300px ·
  잉크 비 1.000. D2Coding: 칸 폭 6.5 = 기준 일치 · 줄 가로 끝 999↔999 · 1217↔1216 · **높이 14 ↔ 기준 15(1px 차)**.
- 회귀 게이트: `PW_CORE=<playwright-core> node ui/e2e/render_parity/gate.mjs` → 5/5 PASS · 뮤턴트(칸 보정 끔) → 2 FAIL 검출.
- 시험: `cd ui && bun test` 3203 통과 0 실패 · `bunx tsc -p tsconfig.check.json` 0.

## 알려진 차이·함정
- **D2Coding 줄 높이 1px**: Ghostty 는 글꼴 hhea line gap(80/1000)을 넣고 WebKit 의 normal 줄 높이는 뺀다. 브라우저가 line gap 을
  알려주는 API 가 없어 남김(±1px 기준 안).
- **xterm 내부 의존**: `_core._charSizeService._measureStrategy`·`_core._renderService.handleCharSizeChanged` — 모양이 다르면
  아무것도 안 함(업그레이드 시 칸 보정만 조용히 빠진다 → 게이트로 확인).
- JetBrains Mono 미설치 기기는 Menlo(맥)/Cascadia Mono(윈)로 그려진다 — cmux 는 JetBrains Mono 를 내장. 글꼴 동봉은 범위 밖(결정 항목).
- 실제 앱(WKWebView · 윈 WebView2)에서의 OffscreenCanvas 동작은 헤드리스 WebKit 실측으로 추정 — 박사님 눈 확인 필요.
- `main.ts` 수정은 7줄(import 2 · 테마 2 · 글꼴 2 · open 뒤 1) — selection-drag 워커와 겹칠 자리 최소화.

## 박사님 기기 저장값(읽기 전용 실측 · localStorage 사본)
`cys-bg-color=#000000` · `cys-font-size=22` · `cys-term-weight=300` · `cys-font-face=D2Coding` · `cys-title-weight=600`.
→ 저장값을 덮지 않으므로 **새 판을 깔아도 박사님 화면은 배경 검정·글자 22 그대로**다(글자색·팔레트·칸·한글만 바뀜).
화면 설정 「기본값」 단추는 배경과 **글꼴도 함께** 초기화한다(D2Coding 해제).

## 재현
```
cd ui && bun install && bun test
PW_CORE=~/axdev/vendor-survey/stephen/pw/node_modules/playwright-core node ui/e2e/render_parity/gate.mjs /tmp/rp
```
