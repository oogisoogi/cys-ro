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

---

# 이어서 — JetBrains Mono 동봉 (TICKET=cysr-bundle-jetbrains-mono · 2026-10-29)

박사님 원문(10-29 07:4x): 「권고대로 글꼴을 넣는다.」 · 같은 브랜치 `fix/1111-render-parity` 위 커밋. **push·병합·빌드 설치 안 함**.

## 무엇을 넣었나
| 파일(`ui/fonts/`) | 원본(릴리스 zip 안 경로) | 바이트 | sha256 |
|---|---|---|---|
| `JetBrainsMono-wght.ttf` | `fonts/variable/JetBrainsMono[wght].ttf` | 303,144 | `662a196d58f1183bf2d77428b6d5283fe3f45161ab021bea4036bc98e5cac016` |
| `JetBrainsMono-Italic-wght.ttf` | `fonts/variable/JetBrainsMono-Italic[wght].ttf` | 308,888 | `f115aaa12113718c02ce72864fe6823b87241bc23d3e44cf1220155f861063f2` |
| `OFL.txt` | `OFL.txt` | 4,399 | `30f0c136e3c88e422d0791acd97238870f9054a9729bc34cf2ff0d4ed8cac4ad` |

- 출처 = 공식 `github.com/JetBrains/JetBrainsMono` **최신 릴리스 v2.304**(2023-01-14 게시 · GitHub API 실측) ·
  `JetBrainsMono-2.304.zip` 5,622,857 B · sha256 `6f6376c6ed2960ea8a963cd7387ec9d76e3f629125bc33d1fdcd7eb7012f7bbf`.
  빈 새 폴더(스크래치패드 `jbm-dl/`)에 받아 풀기만 했고 실행한 것 없음. 바이트는 원본 그대로(파일 이름의 `[wght]` 만 `-wght` 로).
- 이 기기에 설치된 `~/Library/Fonts/JetBrainsMono[wght].ttf` 와 **sha256 동일**(같은 2.304).
- 라이선스 = SIL OFL 1.1(무료 · 재배포 시 라이선스 동봉 의무 → `dist/fonts/OFL.txt` 로 앱에 함께 실림 · `NOTICE.md` 에 행 추가).
- ★**woff2 대신 가변 TTF 를 고른 이유**: 화면 설정 「본문 굵기」 가 100~800 여덟 단계를 고르게 하고(박사님 저장값 = 300),
  기울임은 Claude Code 의 생각 글 등에 쓰인다. 공식 릴리스의 woff2 는 **고정 굵기 낱개뿐**(가변 woff2 없음)이라 8 굵기 × 정자·기울임 =
  16 파일 ≈ 1.5 MB. 가변 TTF 2개 = 0.6 MB 로 전 구간을 덮는다. woff2 로 바꾸면 원본 sha256 추적이 끊겨 바꾸지 않았다.

## 어떻게 붙였나
- `appearance.ts`: `BUNDLED_FONT_FAMILY = "cys JetBrains Mono"` — **설치 글꼴과 겹치지 않는 별명**. 기본 스택 맨 앞에 넣었다
  (`'cys JetBrains Mono', 'JetBrains Mono', Menlo, 'SF Mono', 'Cascadia Mono', Consolas, 한글 대체…`).
  사용자가 고른 글꼴(저장값 `cys-font-face`)은 종전처럼 그 앞에 붙으므로 **저장값이 우선**. 맥·윈 같은 묶음이라 윈도 기본 = 동봉 글꼴.
  한글은 동봉 글꼴에 없으므로 종전대로 시스템 대체 글꼴(+ 앞 티켓의 1.214배 맞춤) — cmux 와 같다.
- `termrender.ts loadBundledFont()`: `FontFace` 로 정자·기울임 2개를 굵기 `100 800` 으로 문서 글꼴 목록에 한 번만 올림.
  못 올라오면(파일 없음) false → 스택 다음 글꼴(설치된 JetBrains Mono → Menlo/Cascadia)로 그려진다.
- `main.ts`(9줄): 모듈 시작 때 `loadBundledFont().then(...)` — 그 전에 만든 창은 한글 배율을 다시 계산하고 `remeasureCells`
  (칸 재측정 + 글자 폭 캐시 비움) 후 `fitPane`.
- `build.sh`: `ui/fonts` 의 3 파일을 `dist/fonts/` 로 복사.

## ★OffscreenCanvas 가 동봉 글꼴을 보는가 (브리프 3)
헤드리스 WebKit(playwright-core 1.63 · webkit-2359) 실측 — `FontFace` 로 문서에 올린 글꼴은
**OffscreenCanvas(메인 스레드 · 로드 전에 만든 것·뒤에 만든 것 모두)·문서에 안 붙은 캔버스·붙은 캔버스·span 모두가 본다**
(「W」 100px = 60.000 = JetBrains 600/1000 · 대체 글꼴은 60.0098). 즉 앞 티켓 원인 ①(사용자 **설치** 글꼴을 못 봄)과 달리
**문서에 올린 웹 글꼴은 xterm 원래 측정 경로로도 맞게 잰다**(span 측정 감싸기는 그대로 둠 — 사용자가 고른 설치 글꼴용).
- 「워커 쪽」: 이 UI·xterm 5.5 는 Web Worker 를 쓰지 않는다(`new Worker` 0건 — src·xterm 원본 grep). 참고로 워커에서
  `url()` 글꼴을 file:// 로 읽으면 NetworkError(헤드리스 실측) — 앞으로 워커를 쓰게 되면 ArrayBuffer 로 넘겨야 한다.

## 시험
- render_parity 게이트(`PW_CORE=… node ui/e2e/render_parity/gate.mjs <폴더>`) **9/9 PASS** — 종전 5 + 새 4:
  - 「미설치 환경」(`new:@nosys` = 스택에서 설치 글꼴 이름 `'JetBrains Mono'` 를 빼 동봉 글꼴만 남김):
    동봉 정자·기울임 loaded · **칸 8×17** · 한글 맞춤 1.214(동봉 글꼴 기준으로 다시 잼).
  - 「글리프 = 동봉」: 미설치 그림 ↔ 설치 글꼴만 쓴 그림(`new:@sysonly`)의 글자 줄 0~4 **화소 완전 일치**.
- 뮤턴트 ①(`GATE_MUTANT=nofonts` = 글꼴 파일 빼기) → **4 FAIL 검출**(적재 error · 칸 8×15 = Menlo · 배율 1.219 · 화소 불일치) · exit 1.
- 뮤턴트 ②(하네스에서 `remeasureCells` 호출 제거) → **살아남음(검출 못 함)** — 정직 고지: 로드 뒤 한글 배율 이름이
  1219→1214 로 바뀌어 그 자체로 xterm 이 다시 재기 때문. `remeasureCells` 는 「배율 이름이 우연히 같을 때」의 백스톱이며
  단위 시험(호출 순서 measure→widths→refresh · 모양 다르면 무동작)으로만 잠갔다.
- `cd ui && bun test` **3209 통과 · 0 실패**(85 skip 은 종전 그대로) · `bunx tsc -p tsconfig.check.json` **0**
  (단위 시험이 쓰는 `node:crypto`·바이트 `readFileSync` 만 `src/bun-env.d.ts` 에 좁게 선언).
- 실제 빌드 묶음 확인: `sh ui/build.sh` 뒤 `dist/index.html` 을 헤드리스 WebKit 에 가짜 출처로 물려(서버 없이 route) 열면
  `./fonts/` 두 파일을 요청하고 두 글꼴 모두 loaded · 페이지 오류 0.

## 앱 용량 증가
- `ui/dist` 날 바이트 **+616,431 B(≈0.59 MiB)** = 글꼴 612,032 + OFL 4,399.
- Tauri 는 묶음 자산을 brotli 로 압축해 실행 파일에 넣는다(`tauri-codegen` 2.6.2 가 brotli 의존 · tauri 기본 기능) —
  brotli q11 실측 합 **261,797 B(≈0.25 MiB)**(정자 124,982 · 기울임 135,390 · OFL 1,425). 실제 .app/.msi 증가는 빌드로 확인 안 함(빌드 = master 게이트).

## 알려진 차이·함정
- **상자 문자(─ ╭ ╮) 이음매**: 같은 바이트인데도 웹 글꼴로 그리면 칸 이음매 화소가 설치 글꼴보다 밝다(65 화소 · 최대 48/255 ·
  5~6 줄만). WebKit 이 웹 글꼴·설치 글꼴의 칸 밖 잉크를 다르게 겹치는 것으로 보임(원인 미확정). 그래서 화소 일치 판정은 글자 줄만.
- 실제 앱(WKWebView `tauri://` · WebView2 `https://tauri.localhost`)에서 `./fonts/` 상대 경로 읽기는 헤드리스 가짜 출처로만 확인 —
  박사님 기기·윈 실기 확인 필요.
- 박사님 기기는 저장값 `cys-font-face=D2Coding` 이라 **이 변경으로 화면이 바뀌지 않는다**(저장값 우선). 기본값으로 되돌리면 동봉 글꼴.
