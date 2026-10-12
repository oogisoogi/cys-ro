# HANDOFF · TICKET=cysr-1110-screen-settings — 「테마」 → 「화면 설정」 개편

- 브리프 정본: `master/briefs/2026-10-12-cysr-1110-screen-settings.md`(master#69877399 · 2026-10-12 09:04)
- 가지: `feat/1110-screen-settings` ← `017e6d86`(int/1110-upstream 머리) · 작업 시각 09:04 ~ 09:3x(상한 12:17)
- 박사님 원문(2026-10-12 09:0x): 「1. 현재 "테마" 메뉴의 글자들이 너무 작다. 지금의 2배 이상 키워야 제대로 볼 수 있다. 2. "테마"처럼 메뉴도 선택할 수 있게 하자. 메뉴 목록을 보여주고 켜기/끄기 버튼을 두는 것이다. 순서로 마음대로 조정할 수 있도록 드래그드롭하든지 켜기/끄지 버튼 옆에 끌어옮기기 아이콘을 넣든지 3. 메뉴 커스텀 기능은 "테마"에 한꺼번에 넣어 구현하는 것은 어떤가?」 → 09:1x 「최적안대로 한다.」(기본 숨김 = A안 5개)
- push · int/1110-upstream 병합 · 발행 = master. 이 가지는 로컬 커밋만 있다(push 0).

## 0. 델타 — 커밋 4 + 이 문서

| # | 해시 | 내용 | 파일 |
|---|---|---|---|
| ① | `d13a6a8e` | 이름 「화면 설정」 · 팝오버 글자 20px × 메뉴 배율(한 축) · 구획 접기 | `ui/index.html` · `ui/src/style.css` · `ui/src/main.ts` |
| ② | `861eafc0` | 상단 단추 구획 — 켬끔 토글 · 순서(끌어 놓기 + ▲▼) · 저장 | `ui/src/topbarlayout.ts`(새 파일) · `ui/src/main.ts` · `ui/src/style.css` |
| ③ | `dd27573c` | 기본값 끔 5 · `v116-recut-newsplit` 주석 갱신 · 사용 설명서 안내 · 옛 헤드리스 c4a 기대값 | `ui/src/topbarlayout.ts` · `ui/index.html` · `USER-MANUAL.md` · `docs/v116-ui-evidence/v116-headless.ts` |
| ④ | `36e1fdeb` | bun 시험 2파일 58건 + 실렌더 증거 + 음성 대조 | `ui/src/topbarlayout.test.ts` · `ui/src/screensettings.test.ts` · `docs/screen-settings-evidence-2026-10-12/` |

Rust · 데몬 · 팩 변경 = 0(소스 무변경). 단 `USER-MANUAL.md` 는 `cys`·`cysd` 가 `include_str!` 로 품는 파일이라 바이너리에 실리는 글은 바뀐다(핀 시험 = §3 의 `manual_` 6건).

## 1. 무엇이 바뀌었나(화면 기준)

1. **이름·입구**: 상단 맨 끝 단추 「테마」 → **「화면 설정」**(title 「화면 설정 — 글자·배경·상단 단추」). id(`btn-theme`) · 자리 · 누르면 열리는 팝오버 id(`#theme-pop`)는 그대로다.
2. **팝오버 = 구획 3개**(제목 줄을 누르면 그 구획이 접힌다 · 앱이 켜져 있는 동안만 기억 · 저장 0)
   - ① **글자·배경** — 종전 항목 8개 그대로(배경색 · 폰트 · 제목 크기 · 제목 굵기 · 제목=역할색 · 본문 굵기 · 메뉴 굵기 · 메뉴 크기(%)) + 「이 구획만 기본값으로」
   - ② **상단 단추** — 줄 = `[≡ 끌기 손잡이] [이름] [▲] [▼] [켬/끔]` · 안내 2줄 · 「이 구획만 기본값으로」
   - ③ **기본값 복원** — 「모두 기본값으로 되돌리기」(①② 한 번에)
3. **글자 2배**: 팝오버 글자 = `calc(20px * var(--ui-chrome-scale))`. 기본 배율 1.25 → **25px**(종전 12px 고정의 2.08배) · 배율 1.0 → 20px. 안쪽 부품(선택 상자 · 색상 칸 · 입력 칸 · 체크 상자 · 단추 · 여백)은 전부 `em` 이라 같은 손잡이(「메뉴 크기(%)」) 하나로 함께 커진다. 팝오버 규칙 27개 가운데 `font-size` 선언은 뿌리 1줄뿐이다.
4. **작은 창**: 폭 상한 `100vw − 8px` · 높이 상한 = 단추 아래 남은 높이(main.ts `fitPop` 이 열 때 · 접을 때 · 메뉴 크기 바꿀 때 · 창 크기 바뀔 때 다시 넣는다) · 넘치는 몫은 팝오버 안 스크롤.
5. **상단 단추 켬끔·순서**: 대상 = `#topbar` 바로 아래의 id 달린 단추 전부(지금 11개). 누르는 즉시 상단에 반영하고 저장한다(재시작 불요 · 재시작 뒤 유지). **고정 2 = 「화면 설정」 · 「Control Center」** = 토글 비활성(순서만 바뀐다).
6. **기본값(박사님 확정 A안)**: 켬 = 피드백 · 정렬 · 파일 · Control Center · ↻ 재시작 · 화면 설정 / **끔 = + New · Split → · Split ↓ · 창 닫기 · 완전 초기화**. 기본 순서 = `index.html` 의 단추 순서.
7. **숨김 = `hidden` 속성만**. 요소 · 누름 처리기는 그대로라 단축키(⌘T · ⌘D · ⌘⇧D · ⌘W) · 팔레트 · 창 머리 × 는 숨겨도 동작한다.

## 2. 저장 형식

- 키: `localStorage` **`cys-topbar-layout`**(상수 `TOPBAR_LAYOUT_KEY` — 글자로 적은 곳은 `ui/src/topbarlayout.ts` 한 곳)
- 값(version 1): `{"version":1,"items":[{"id":"btn-feedback","on":true}, …]}` — `items` 의 순서가 곧 화면 순서(위 → 아래 = 상단의 왼쪽 → 오른쪽)
- 읽는 규칙(`parseTopbarLayout(raw, domIds)`)

| 저장 상태 | 결과 |
|---|---|
| 없음 · JSON 아님 · `version ≠ 1` · `items` 가 배열 아님 · 항목 모양 틀림(`id` 글자 아님 · `on` 참거짓 아님) · 아는 단추가 하나도 없음(빈 목록 포함) | **기본값**(끔 5 · html 순서) |
| 저장에는 있는데 화면에 없는 id(없어진 단추) | 버린다 |
| 같은 id 두 번 | 앞의 것만 |
| 화면에는 있는데 저장에 없는 id(나중에 생긴 단추) | **켠 채 맨 끝에** 붙인다(기본 끔 목록에 든 id 라도 켠다 — 새 단추가 조용히 숨지 않게) |
| 고정 단추가 끔으로 저장됨 | 켬으로 읽는다 |

- 쓰는 때: 토글 · ▲▼ · 끌어 놓기 = 그 자리에서 저장. 「이 구획만 기본값으로」 · 「모두 기본값으로」 = **키 삭제**(다음 판에서 기본값 집합이 바뀌면 그대로 따른다). 시작 시 복원은 저장을 다시 쓰지 않는다.
- 기본값 집합(`TOPBAR_DEFAULT_OFF`) · 고정 집합(`TOPBAR_PINNED`) · 이름(「화면 설정」)을 바꾸는 것 = 박사님 결정 사항.

## 3. 게이트 수치(격리 HOME · 좌석 `CYS_*` env 제거 · 이 작업 트리)

| 게이트 | 결과 |
|---|---|
| ui `bun test` 전체 | **2976 pass / 85 skip / 0 fail**(94 파일 · expect 202,734) — 기준(017e6d86) 2918 pass / 85 skip / 0 fail(92 파일) + 새 58 |
| 새 시험 2파일 | `topbarlayout.test.ts` 40 / 0 · `screensettings.test.ts` 18 / 0 |
| `bun x --package typescript@7.0.2 tsc -p tsconfig.check.json` | rc 0 · 음성 대조(타입 오류 1줄 심음) rc 1(`TS2322`) |
| `sh build.sh` | rc 0(`main.js` 0.61 MB) |
| doc-contract(`test_bootv2_doc_contract.py`) | rc 0(`BOOTV2-DOC-CONTRACT-OK`) |
| pins(`test_content_pins_parity.py`) | rc 0(10 OK) |
| `secret-scan.sh --all` | clean(1679 파일 · 새 파일을 스테이징한 상태에서) |
| `cargo test --bin cysd manual_`(사용 설명서 핀) | 6 passed / 0 failed(2602 filtered out) |
| pyseal census(`test_pyseal_census.py`) | rc 0(`PYSEAL-CENSUS-OK`) — 증거 폴더에 파이썬 2파일을 넣었으므로 확인 |
| boot-health `--only H-SH-PKILL-1,H-PY-PKILL-1,H-CI-COVER-1` | 3 PASS / 0 FAIL |
| 옛 헤드리스 `v116-headless.ts` `ONLY=c1,c4,c7,c19` | ALL PASS(c4a 는 새 기대값 · 나머지 칸은 재실행하지 않았다 — §6 ⑧) |
| cargo 전수 | 실행하지 않음(브리프: Rust 무변경이므로 불요) |

음성 대조
- `docs/screen-settings-evidence-2026-10-12/mutants.py`(실파일에 결함 심기 → bun 시험 2파일 → 복원) = **16종 전부 잡음** · 복원 뒤 58 / 0(`mutants-final.txt`)
- `mutants-headless.py`(결함을 심은 번들을 작업 트리 밖에 만들어 실렌더) = **6종 전부 그 칸 FAIL** · 복원 뒤 ALL PASS(`mutants-headless-final.txt`): 선택 상자만 12px → s2(min 12) · overflow 뺌 → s3 · 기본 끔에서 창 닫기 뺌 → s1 · display 규칙이 숨김을 풂 → s1 · 토글이 저장만 하고 화면에 안 바름 → s4 · 고정 비활성 뺌 → s5

## 4. 실렌더 증거(`docs/screen-settings-evidence-2026-10-12/`)

방식 = `docs/v116-ui-evidence/v116-headless.ts` 와 같음(`ui/dist` 실번들 + `v116-ui-evidence/shim.js` 흉내층 + chrome-headless-shell arm64 · CDP). 결과 전문 = `headless-final.txt` · 수치 = `shots/numbers.json` · 스크린샷 12장 = `shots/*.png`. **19칸 ALL PASS**.

| 칸 | 잰 것 | 수치 |
|---|---|---|
| s1 | 기본 화면(저장 0 · 1440×900)에 보이는 단추 | **6개** = 피드백 · 정렬 · 파일 · Control Center · ↻ 재시작 · 화면 설정 / 숨김 5개(`btn-new` · `btn-split-h` · `btn-split-v` · `btn-close` · `btn-factory-reset`) 폭 0 |
| s2a | 팝오버 글자 px(배율 1.25 = 기본) | 보이는 글자 114개 **최소 25 · 최대 25** |
| s2b | 팝오버 글자 px(배율 1.0) | 114개 **최소 20 · 최대 20** |
| s2c | 팝오버 안 「메뉴 크기」 100 → 150 | 팝오버 20 → 30px · 상단 단추 12 → 18px(같은 손잡이) |
| s3 | 화면 밖으로 안 나감 | 1440×900 = 439×859(위 37 · 아래 896) · 1280×800 = 439×759 · 1280×800 배율 250% = 868×732(왼쪽 412 · 오른쪽 1280) · 800×600 = 439×559 · 네 경우 모두 맨 아래 단추까지 스크롤로 닿음 |
| s4 | 끔 5개를 하나씩 켬 | 그 즉시 보임 + 저장(version 1) · 새로 고침 뒤 11개 유지 · 다시 끄면 그 즉시 숨김(요소 11개 유지) |
| s5 | 고정 2 | 토글 비활성 · 눌러도 켬 · 안내 줄 · 저장 0 |
| s6 | ▲▼ | 맨 위 ▲ · 맨 아래 ▼ 비활성 · 한 칸 이동 · 저장 · 초점 유지 · 팝오버가 옮겨 간 단추 아래 |
| s7 | 실제 마우스 끌기 | ↻ 재시작 → 피드백 아래 · 삽입선 보임(z 1200 > 팝오버 1000) · 놓은 뒤 삽입선 0 · 팝오버 열린 채 |
| s8 | 숨긴 채 단축키 | ⌘T = 창 2 → 3 · ⌘W = 「이 창을 닫을까요?」 |
| s9 | 기본값 복원 3종 | 상단 단추만 · 글자·배경만 · 모두(팝오버 25px 로 복귀) |
| s10 | 손상 저장 6종 · 부분 저장 | 6종 모두 기본값 · 저장에 없는 단추(파일) = 켠 채 맨 끝 · 고정 단추 끔 저장 = 켬 |
| s11 | 구획 접기 | 전체 높이 1570 → 763px · Esc 로 닫고 다시 열어도 접힌 채 |
| s12 | 상단바 한 줄 | 1440 · 1280폭 = 높이 38 · 가로 넘침 0 · 맨 끝 단추 「화면 설정」 화면 안 |

정직 고지: 이 수치는 **헤드리스 크롬(맥 arm64)** 의 계산값이다. 실제 앱의 웹뷰(맥 WKWebView · 윈 WebView2)에서 잰 것이 아니다 — 실기 확인은 master 재검 · 다음 실기 점검의 몫이다.

## 5. 함정(다음 사람이 같은 데서 넘어지지 않게)

1. **기본 순서는 손대기 전에 읽는다**: `TOPBAR_DOM_IDS` 를 읽는 줄이 `applyTopbarLayout(topbarLayout, false)` 보다 앞에 있어야 한다. 순서를 바꾸면 「기본 순서」 가 사용자 순서로 오염된다(`screensettings.test.ts` 가 줄 순서를 잰다).
2. **순서 적용 = 끝에 다시 붙이기**(`topbarEl.appendChild`). 상단 단추가 `#topbar` 의 **맨 끝 묶음**이라 성립한다. 단추 묶음 뒤에 다른 형제 요소를 넣으면 그 요소가 단추들 앞으로 밀린다 — 넣으려면 단추 묶음 앞(`.spacer` 앞)에 넣어라. 버전 스큐 배지는 `#daemon-info` 안쪽이라 무관하다.
3. **html 에 `hidden` 을 미리 박지 않는다**: 끔은 저장·기본값을 읽은 main.ts 가 정한다. html 에 박으면 켠 사람에게도 숨는 순간이 생기고 `closeguard.test.ts` 의 줄 전문 대조가 깨진다.
4. **`[hidden]` 짝 규칙**: `.sp-sec-body` 는 `display: flex` 라 짝(`#theme-pop .sp-sec-body[hidden]`)이 필수다. `#topbar > button[hidden]` 은 지금은 예방용이지만(상단 단추 공통 규칙에 `display` 없음) 실렌더 음성 대조(H4)로 display 규칙이 걸리면 숨김이 풀리는 것을 확인했다.
5. **팝오버 글자에 px 를 다시 넣지 않는다**: 한 부품만 px 로 고정하면 그 부품만 작게 남는다(M9 · H1 이 잡는다). 줄 폭을 인라인 `style.width` 로 박는 것도 같다(M10).
6. **실제 마우스 시험은 스크롤부터**: 1440×900 에서 팝오버 전체 높이(1570px)가 창보다 커서 아래쪽 줄은 화면 밖이다. 화면 밖 좌표에 마우스 누름을 보내면 「바깥 누름」 으로 읽혀 팝오버가 닫힌다(첫 s7 실패의 원인) → 구획 머리를 `scrollIntoView` 로 올린 뒤 좌표를 잰다.
7. **셸 종료 코드**: `명령 | tail; echo $?` 는 tail 의 종료 코드다. zsh 에서는 `${pipestatus[1]}` 을 쓴다.
8. **건수는 실행해서 센다**: 커밋 ④ 초판에 파일별 시험 건수를 41 / 17 로 적었다가 실행 결과(40 / 18 · 합 58 은 같음)로 고쳤다(미푸시 로컬 커밋의 메시지 수정).
9. **Rust 핀 시험을 따로 돌릴 때**: 같은 머리의 이웃 작업 트리에서 `cp -c -R <이웃>/target/debug target/debug`(APFS 복제) 뒤 `cargo test --bin cysd manual_` 이 웜으로 돈다. `target/` 은 추적 제외다(이 트리에 복제본이 남아 있다).

## 6. 관찰(범위 밖 · 무수정)

1. **시작 순간 깜빡임 — 미측정**: `main.js` 는 `type="module"` 이라 html 을 다 읽은 뒤 실행된다. 그 사이 첫 그림에 끔 5개 단추가 잠깐 보일 수 있다(반대로 html 에 `hidden` 을 박으면 켠 사람에게 반대 깜빡임). 헤드리스로는 첫 그림 시점을 재지 않았다. 실기에서 눈에 띄면 처방 후보 = 상단 단추 묶음을 적용 전까지 `visibility: hidden` 으로 두는 것 — 단 스크립트가 죽으면 단추가 영영 안 보이는 위험이 있어 넣지 않았다.
2. **팝오버가 길다**: 글자 2배의 귀결로 전체 높이 1570px(배율 1.25) — 1440×900 에서 859px 창 안 스크롤. 브리프대로 「스크롤 + 구획 접기」 로 받았다. 구획을 처음부터 접어 둘지(예: 「글자·배경」 접힌 채 시작)는 정하지 않았다 = 박사님 취향 사안.
3. **끌기 중 자동 스크롤 없음**: 목록이 창보다 길 때 화면 밖 줄까지 한 번에 끌 수는 없다(휠로 스크롤하며 끌거나 ▲▼).
4. **사용 설명서 §4.1 의 다른 낡은 서술**: 「왼쪽 그룹은 아이콘 버튼」 · 「× 아이콘」 · 「폴더 아이콘」 · 「아래에 새 창」 은 지금 화면(글자 단추 · 창 만들기 = 오른쪽 한 갈래)과 다르다. 이 티켓은 단추 이름과 상단 단추 안내만 고쳤다.
5. **`docs/117/WIN-CHECK-117.md:21`** 의 「테마」 = 1.1.7 점검표(그 판 기록)라 그대로 두었다. 다음 판 점검표를 만들 때 「화면 설정」 으로 적어야 한다.
6. **`docs/v116-ui-evidence/headless-final.txt`** 의 c4a 줄(「보임」)은 그날 실행 기록이라 그대로다. 하네스(`v116-headless.ts`) 기대값만 새 기본값으로 바꿨다(종전 기대값은 주석에 남김).
7. **윈도우**: 기본 끔으로 창 만들기 세 단추가 처음엔 안 보인다. 보이는 길 = 「화면 설정」 → 「상단 단추」 토글(index.html 주석 갱신). 윈 실기에서 그 길이 실제로 닿는지(팝오버가 WebView2 에서 열리고 토글이 듣는지)는 재지 않았다.
8. **옛 헤드리스 전 칸**: `v116-headless.ts` 는 c1 · c4 · c7 · c19 만 다시 돌렸다(c5 · c11 등 긴 대기 칸 포함 전수는 미실행).
9. **클릭 텔레메트리 0**: 어느 단추를 실제로 얼마나 누르는지의 실사용 계수가 없다 — 기본 끔 5개는 계수가 아니라 박사님 결정이다.
10. **localStorage 예외**: 저장소 접근이 던지는 환경(차단 · 용량)은 따로 받지 않았다 — 같은 파일의 기존 설정(`cys-menu-scale` 등)과 같은 수준이다.
11. **이종 검증 미수행**: agy · codex 1R 은 이 티켓 안에서 돌리지 않았다(브리프: master 재검 뒤 master 가 돌린다).

## 7. 재현 명령

```sh
cd <이 작업 트리>
a=(); while IFS= read -r n; do a+=(-u "$n"); done < <(env | sed -n 's/^\(CYS_[A-Za-z0-9_]*\)=.*/\1/p')
ISO() { env "${a[@]}" -u CLAUDE_CONFIG_DIR HOME="$(mktemp -d)" CARGO_HOME="$HOME/.cargo" RUSTUP_HOME="$HOME/.rustup" \
      PATH="$HOME/.bun/bin:$HOME/.cargo/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin" "$@"; }
CHS="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell"
E=docs/screen-settings-evidence-2026-10-12

( cd ui && ISO bun test )                                                        # 2976 pass / 85 skip / 0 fail
( cd ui && ISO bun test src/topbarlayout.test.ts src/screensettings.test.ts )    # 58 / 0
( cd ui && ISO bun x --package typescript@7.0.2 tsc -p tsconfig.check.json )     # rc 0
( cd ui && ISO sh build.sh )                                                     # ui/dist ready
ISO env DIST="$PWD/ui/dist" CHS="$CHS" OUT="$PWD/$E/shots" bun $E/screen-settings-headless.ts   # 19칸 ALL PASS
ISO env DIST="$PWD/ui/dist" CHS="$CHS" ONLY=c1,c4,c7,c19 bun docs/v116-ui-evidence/v116-headless.ts
python3 $E/mutants.py "$PWD/ui"                                                  # 16종 잡음 · 복원 뒤 58 / 0
python3 $E/mutants-headless.py "$PWD" "$CHS" "$(mktemp -d)"                      # 6종 잡음 · 복원 뒤 ALL PASS
( cd cysjavis-pack/bin/tests && ISO python3 test_bootv2_doc_contract.py && ISO python3 test_content_pins_parity.py && ISO python3 test_pyseal_census.py )
ISO bash scripts/secret-scan.sh --all                                            # clean
ISO cargo test --bin cysd manual_                                                # 6 / 0
```

손으로 볼 때: 앱 상단 맨 끝 「화면 설정」 → 「상단 단추」 에서 「+ New」 의 「끔」 을 누르면 그 자리에서 상단에 「+ New」 가 생긴다. 「기본값 복원」 → 「모두 기본값으로 되돌리기」 로 처음 화면(단추 6개)으로 돌아간다.
