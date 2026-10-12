# HANDOFF · TICKET=cysr-1110-screen-settings — 「테마」 → 「화면 설정」 개편

- 브리프 정본: `master/briefs/2026-10-12-cysr-1110-screen-settings.md`(master#69877399 · 2026-10-12 09:04)
- 가지: `feat/1110-screen-settings` ← `017e6d86`(int/1110-upstream 머리) · 작업 시각 09:04 ~ 09:3x(상한 12:17)
- 박사님 원문(2026-10-12 09:0x): 「1. 현재 "테마" 메뉴의 글자들이 너무 작다. 지금의 2배 이상 키워야 제대로 볼 수 있다. 2. "테마"처럼 메뉴도 선택할 수 있게 하자. 메뉴 목록을 보여주고 켜기/끄기 버튼을 두는 것이다. 순서로 마음대로 조정할 수 있도록 드래그드롭하든지 켜기/끄지 버튼 옆에 끌어옮기기 아이콘을 넣든지 3. 메뉴 커스텀 기능은 "테마"에 한꺼번에 넣어 구현하는 것은 어떤가?」 → 09:1x 「최적안대로 한다.」(기본 숨김 = A안 5개)
- push · int/1110-upstream 병합 · 발행 = master. 이 가지는 로컬 커밋만 있다(push 0).
- **R2(2026-10-12 09:38 · master#01c6e170 · TICKET=cysr-1110-screen-settings-r2)**: codex 1R(이종 적대검토 · 8축) = MED 3 · LOW 1 · 기각 0 → 4건 모두 수정(§8). 아래 §1~§7 은 R1 시점 기록이고, R2 로 달라진 수치·동작은 §8 이 정본이다.
- **R3(2026-10-12 10:07 · master#5b0a479f · TICKET=cysr-1110-screen-settings-r3)**: codex 2R = 1R 4건 가운데 닫힘 3 · 부분 1(MED-3 잔여 2곳) + 신규 2(MED · LOW) → master 가 4건 전부 채택 → 수정(§9). **지금 수치·동작의 정본은 §9** 다(§8 의 s13 판정·「가로 스크롤」 서술 · 익명 한 번짜리 처리기 서술은 R3 로 바뀌었다).

## 0. 델타 — 커밋 4 + 이 문서

| # | 해시 | 내용 | 파일 |
|---|---|---|---|
| ① | `d13a6a8e` | 이름 「화면 설정」 · 팝오버 글자 20px × 메뉴 배율(한 축) · 구획 접기 | `ui/index.html` · `ui/src/style.css` · `ui/src/main.ts` |
| ② | `861eafc0` | 상단 단추 구획 — 켬끔 토글 · 순서(끌어 놓기 + ▲▼) · 저장 | `ui/src/topbarlayout.ts`(새 파일) · `ui/src/main.ts` · `ui/src/style.css` |
| ③ | `dd27573c` | 기본값 끔 5 · `v116-recut-newsplit` 주석 갱신 · 사용 설명서 안내 · 옛 헤드리스 c4a 기대값 | `ui/src/topbarlayout.ts` · `ui/index.html` · `USER-MANUAL.md` · `docs/v116-ui-evidence/v116-headless.ts` |
| ④ | `36e1fdeb` | bun 시험 2파일 58건 + 실렌더 증거 + 음성 대조 | `ui/src/topbarlayout.test.ts` · `ui/src/screensettings.test.ts` · `docs/screen-settings-evidence-2026-10-12/` |
| R2 | `62ae9d13` | codex 1R 채택 4건 수정 + 시험 9건 | `ui/src/main.ts` · `ui/src/style.css` · `ui/src/screensettings.test.ts` · `USER-MANUAL.md` · `docs/GUIDE-clean-reset-KR.md` · `src/bin/cys.rs`(문자열 1줄) |
| R2 증거 | `34cafdc4` | 실렌더 새 6칸 · 스크린샷 3장 · 뮤턴트 10 + 5 추가 | `docs/screen-settings-evidence-2026-10-12/` |
| R3 | `b27f27c7` | codex 2R 채택 4건 수정 + 시험 4건 | `ui/src/main.ts` · `ui/src/style.css` · `ui/src/screensettings.test.ts` · `src/bin/cys.rs`(문자열 1줄) · `cysjavis-pack/hooks/guard.sh`(문자열 1줄) · `docs/GUIDE-clean-reset-KR.md` |
| R3 증거 | (이 문서와 같은 커밋) | 실렌더 s13 판정 교체 + 새 4칸 · 스크린샷 1장 추가 · 뮤턴트 12 + 7 추가 | `docs/screen-settings-evidence-2026-10-12/` |

Rust · 데몬 · 팩 변경 = R1 은 0(소스 무변경) · R2 는 `src/bin/cys.rs` 안내 문자열 1줄 · R3 는 `src/bin/cys.rs` 문자열 1줄 더 + 팩 `cysjavis-pack/hooks/guard.sh` 문자열 1줄(모두 master 허용 범위 · 로직 무변경). 단 `USER-MANUAL.md` 는 `cys`·`cysd` 가 `include_str!` 로 품는 파일이라 바이너리에 실리는 글은 바뀐다(핀 시험 = §3 의 `manual_` 6건).

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

( cd ui && ISO bun test )                                                        # 2989 pass / 85 skip / 0 fail(R3)
( cd ui && ISO bun test src/topbarlayout.test.ts src/screensettings.test.ts )    # 71 / 0(R3)
( cd ui && ISO bun x --package typescript@7.0.2 tsc -p tsconfig.check.json )     # rc 0
( cd ui && ISO sh build.sh )                                                     # ui/dist ready
ISO env DIST="$PWD/ui/dist" CHS="$CHS" OUT="$PWD/$E/shots" bun $E/screen-settings-headless.ts   # 29칸 ALL PASS(R3)
ISO env DIST="$PWD/ui/dist" CHS="$CHS" ONLY=c1,c4,c7,c19 bun docs/v116-ui-evidence/v116-headless.ts
python3 $E/mutants.py "$PWD/ui"                                                  # 38종 잡음 · 복원 뒤 71 / 0(R3)
python3 $E/mutants-headless.py "$PWD" "$CHS" "$(mktemp -d)"                      # 18종 잡음 · 복원 뒤 ALL PASS(R3)
( cd cysjavis-pack/bin/tests && ISO python3 test_bootv2_doc_contract.py && ISO python3 test_content_pins_parity.py && ISO python3 test_pyseal_census.py )
ISO bash scripts/secret-scan.sh --all                                            # clean
ISO cargo test --bin cysd manual_                                                # 6 / 0
ISO cargo check --bin cys                                                        # rc 0(R2 — cys.rs 문자열 1줄)
```

손으로 볼 때: 앱 상단 맨 끝 「화면 설정」 → 「상단 단추」 에서 「+ New」 의 「끔」 을 누르면 그 자리에서 상단에 「+ New」 가 생긴다. 「기본값 복원」 → 「모두 기본값으로 되돌리기」 로 처음 화면(단추 6개)으로 돌아간다.

## 8. R2 — codex 1R 채택 4건(MED 3 · LOW 1 · 기각 0)

보고서 전문 = `master/reports/screen-settings-1012/REVIEW-codex-1r.md`. 수정 커밋 = `62ae9d13`.

| # | 지적 | 수정 | 소스 시험(`screensettings.test.ts`) | 실렌더 칸 |
|---|---|---|---|---|
| MED-1 | 배율 250% + 좁은 창(500px)에서 팝오버 최소 폭 640px 이 `fitPop` 왼쪽 하한 4px 과 충돌 → 오른쪽 144px 화면 밖 | `#theme-pop` `min-width: min(calc(256px * var(--ui-chrome-scale)), calc(100vw - 8px))` — 최소 폭도 창 안으로 접는다. 넘치는 내용은 팝오버 안 가로 스크롤(`overflow: auto` 는 종전 그대로) | 최소 폭 clamp 핀 · 창 폭을 모르는 맨 최소 폭 0 | **s13**: 500×600·250% 에서 바로 열기 = 왼쪽 4 · 오른쪽 496 · 폭 492 · 높이 532(위 65 · 아래 596) / 1440×900 에서 연 뒤(폭 868) 500×600 으로 줄이기 = 왼쪽 4 · 오른쪽 496 · 폭 492 / 두 경우 모두 첫 줄 토글·맨 아래 단추가 팝오버 안 스크롤로 닿음(내용 폭 691 > 보이는 폭 490) |
| MED-2 | 끄는 도중 Esc 로 팝오버를 닫아도 mouseup 처리기가 살아 있어 놓는 순간 순서 저장 | `startTopbarRowDrag` 에 끝내기 공통 `teardown`(처리기 3개 · 삽입선 · `body.ws-reordering` · `tb-dragging` · 취소 손잡이) + `cancel`(commit 을 부르지 않음). 모듈 변수 `cancelTopbarDrag` 를 팝오버 `close()` 첫 줄이 부른다(Esc 도 close 를 지난다) · `window` `blur` 처리기 · 닫힘으로 취소됐을 때만 다음 mouseup 뒤 click 1회 삼킴 | 취소 본문 commit 0 · teardown 7항 · 세 경로 배선 | **s14a** 끄는 도중 Esc → 팝오버 닫힘 · 삽입선·전역 표시 0 → 놓아도 순서 = 처음 · 저장 없음 · 다시 열어도 처음 순서 / **s14b** 창이 초점을 잃음 → 끌기 버림(팝오버 열린 채) → 놓아도 불변 → 그 뒤 실제 누름(+ New 토글)은 정상 반영 / **s14c** 취소 뒤 다시 끌어 놓기 = 정상 |
| MED-3 | 기본으로 숨긴 「완전 초기화」 를 앱·문서가 「상단바에서 누르라」 고 안내 | 켜는 길을 함께 적었다(화면 설정 → 상단 단추 → 완전 초기화 켬 → 상단의 완전 초기화): `ui/src/main.ts` 「새로 시작 확인 창을 아직 열지 않았습니다」 토스트 · `USER-MANUAL.md` 2곳(§ 완전 초기화 · 문제 해결 표) · `docs/GUIDE-clean-reset-KR.md` 머리말 · `src/bin/cys.rs` factory-reset 의 GUI 실행 중 거부 안내 1줄. 기본 표시로 되돌리지 않았다(박사님 A안) | 4파일 5곳에 「화면 설정 → 상단 단추 → 완전 초기화」 순서 · 옛 문구 0 | (글자 안내 — 실렌더 칸 없음) |
| LOW | `localStorage.setItem` 예외에서 상단바는 바뀌고 토글 글자는 그대로 | `applyTopbarLayout` 이 저장을 `try` 로 감싸 성공 여부를 돌려준다. **화면에는 끝까지 바른다(되돌리지 않는다)** — 저장소가 막힌 기기에서도 단추를 켤 수 있어야 한다. `commitTb` 가 목록을 다시 그리고 「⚠ 저장되지 않았습니다 — 지금 화면에는 반영됐지만, 앱을 다시 켜면 이전 상태로 돌아갑니다.」 1줄을 보인다(저장이 되면 숨김). 시작 시 읽기 예외 = 저장 없음(기본값) | 저장 try/false · 읽기 예외 · 알림 줄 동기 순서 · 알림 줄에 display 0 | **s15a** 저장이 던짐(QuotaExceeded 흉내) → 상단 반영 · 토글 글자 켬 · 알림 줄 보임(25px) · 기본값 복원(삭제도 던짐) = 화면은 기본 6개 · 알림 유지 → 저장이 되면 알림 사라짐 · 페이지 예외 0 / **s15b** 읽기가 던져도 앱은 기본 6개로 선다 |

지시의 「롤백 또는 끝까지 동기화」 가운데 **끝까지 동기화 + 알림**을 골랐다(되돌리면 저장소가 막힌 기기에서 단추를 켤 길이 없어진다 — 윈에서 창 만들기의 보이는 길이 이 토글이다).

### R2 게이트 수치(격리 HOME · 좌석 `CYS_*` env 제거 · 이 작업 트리)

| 게이트 | 결과 |
|---|---|
| ui `bun test` 전체 | **2985 pass / 85 skip / 0 fail**(94 파일 · R1 2976 + 9) |
| 새 시험 2파일 | `topbarlayout.test.ts` 40 / 0 · `screensettings.test.ts` 27 / 0 |
| tsc(`typescript@7.0.2`) · `sh build.sh` | rc 0 · rc 0 |
| 실렌더 `screen-settings-headless.ts` | **25칸 ALL PASS**(R1 19 + 새 6 = s13 · s14a · s14b · s14c · s15a · s15b) · 스크린샷 15장 |
| 옛 헤드리스 `v116-headless.ts` `ONLY=c1,c4,c7,c19` | ALL PASS |
| `cargo check --bin cys` | rc 0 — 그 문구를 재는 cys 시험은 없다(`cargo test --bin cys factory` = 0건 일치 · 612 filtered out) |
| `cargo test --bin cysd manual_` | 6 / 0 |
| doc-contract · pins · pyseal census · `gen_ceo_template.py --check` | 모두 rc 0 |
| boot-health 전량 | 165 PASS / 2 FAIL(`H-CLT-1`·`H-CLT-2`) / 1 SKIP · 431.6초 — `docs/HANDOFF-1110-docs-d.md` §4 에 적힌 기준(017e6d86)과 같은 합계·같은 두 id. FAIL 사유 글 전문을 이 티켓 이전 실행과 나란히 놓고 대조하지는 않았다(사유 = 이 맥의 파이썬 해소 경로 · 이 티켓이 건드린 파일과 무관) |
| `secret-scan.sh --all` | clean(1683 파일 · 새 스크린샷 3장을 스테이징한 상태에서) |

음성 대조(R1 것 포함 전체 재실행)
- `mutants.py` = **26종 전부 잡음**(R1 16 + R2 10: 최소 폭 clamp 뺌 · 닫힘이 끌기를 취소하지 않음 · 취소가 순서를 저장 · 초점 잃음 처리기 뺌 · 저장 예외 미포착 · 알림을 켜지 않음 · 토스트 옛 문구 · 깨끗이 지우기 안내에서 켜는 길 뺌 · CLI 안내 옛 문구 · 사용 설명서 표에서 켜는 길 뺌) · 복원 뒤 67 / 0
- `mutants-headless.py` = **11종 전부 그 칸 FAIL**(R1 6 + R2 5: clamp 뺌 → s13 · 닫힘이 취소하지 않음 → s14a · 초점 잃음 처리기 뺌 → s14b · 저장 예외 미포착 → s15 · 알림을 켜지 않음 → s15a) · 복원 뒤 ALL PASS

### R2 함정·관찰

1. **뮤턴트와 cargo 를 겹쳐 돌리지 않는다**: `mutants.py` 의 M25·M26 은 `src/bin/cys.rs`·`USER-MANUAL.md` 를 잠깐 바꾼다. 그 사이 배경에서 돌던 cargo 는 바뀐 글을 컴파일했을 수 있어, 뮤턴트가 끝난 뒤 cargo 를 다시 돌렸다(위 수치는 다시 돌린 것).
2. **boot-health 전량은 작업 트리에 찌꺼기를 남긴다**: `cysjavis-pack/bin/tests/` 아래에 윈도우 경로 모양 이름의 폴더(`hook-errors.log` 1개)가 생겼다(추적 제외 아님 → `git status` 에 뜬다). 내용을 보고 지웠다. 전량을 돌린 뒤에는 `git status` 를 확인해야 한다.
3. **「완전 초기화」 를 가리키는 다른 글(무수정)**: `src/bin/cys.rs:10958`(「GUI '완전 초기화' 버튼에서 실행하라」 — Rust 는 한 줄만 허용) · `cysjavis-pack/hooks/guard.sh:298`(팩 = 범위 밖) · `docs/DESIGN-factory-reset.md:139`(설계 기록) · `docs/GUIDE-clean-reset-KR.md` 의 비교 문장 4곳(33 · 108 · 352 · 455 — 「누르라」 가 아니라 버튼과 이 문서의 차이를 말하는 글). 앞의 둘은 숨긴 단추를 켜는 길 없이 가리키므로 다음 티켓 후보다.
4. **좁은 창 + 큰 배율의 가로 스크롤**: 500px 창 · 250% 에서 줄(이름 + ▲▼ + 토글)이 팝오버보다 넓어 가로로 밀어야 토글이 보인다. 줄바꿈·말줄임으로 바꾸는 길은 넓은 창의 팝오버 폭 계산(내용 폭에 맞춤)을 함께 건드려 이번에는 넣지 않았다.
5. **Esc 는 끌기만이 아니라 팝오버를 닫는다**(종전 동작 그대로 · 닫히면서 끌기를 버린다).
6. §6 ⑩(localStorage 예외)은 상단 단추 저장에 한해 풀렸다. 「글자·배경」 쪽 설정(`cys-menu-scale` 등)의 저장 예외는 종전 그대로다.
7. 이종 2R(수렴 판정)은 master 가 돌린다.

## 9. R3 — codex 2R 채택 4건(MED 2 · LOW 1 · 시험 1)

보고서 전문 = `master/reports/screen-settings-1012/REVIEW-codex-2r.md`. 수정 커밋 = `b27f27c7`.

| # | 지적 | 수정 | 소스 시험(`screensettings.test.ts`) | 실렌더 칸 |
|---|---|---|---|---|
| ① MED | 1R MED-3 잔여 2곳 — 기본으로 숨긴 「완전 초기화」 를 켜는 길 없이 가리킴: `src/bin/cys.rs` CLI 자기살해 가드(「GUI '완전 초기화' 버튼에서 실행하라」) · 팩 `cysjavis-pack/hooks/guard.sh` 의 완전 초기화 거부 안내 | 두 문자열에 「(상단에 안 보이면 '화면 설정' → '상단 단추'에서 '완전 초기화'를 켠다)」 를 넣었다(각 1줄 · 로직 무변경). 저장소를 훑다가 찾은 한 곳 더 = `docs/GUIDE-clean-reset-KR.md` 본문(「맨 위의 완전 초기화 버튼을 쓰세요」 — 보고서 밖 · 같은 꼴) | 아래 ④ 의 저장소 전체 훑기 | (글자 안내) |
| ② MED | 250%·500px 에서 ▲▼·켬/끔이 초기 화면(scrollLeft 0) 밖 201px — R2 는 가로 스크롤로 받았고 시험이 `scrollIntoView` 로 가렸다 | 좁으면 **줄을 두 줄로 접는다**: `.tb-row` `flex-wrap: wrap` — 윗줄 = `[≡][이름]` · 아랫줄 = 조작 묶음(`.tb-ctl` = ▲ ▼ 켬/끔 · 오른쪽 정렬 · 안에서는 접히지 않음). ① 구획 줄(`.theme-pop-row`)도 접힌다(이름 / 입력 부품). 팝오버 폭 = `width: max-content`(접지 않은 내용 폭) + 상한 `100vw − 8px` — 안내 줄(`.sp-note`)은 `width: 0; min-width: 100%` 로 그 계산에서 뺐다. 전부 em(px 재유입 0) | 접힘·묶음·이름 기준 폭·팝오버 폭 계산·안내 줄 제외 | **s13a**(판정 교체): 500×600·250% 에서 **scrollLeft 0 그대로** — 조작·입력 부품 55개 가운데 보이는 폭 밖 0 · 가로 넘침 0(내용 폭 490 = 보이는 폭 490) · 11줄 모두 두 줄 · 맨 아래 단추는 세로 스크롤로 닿음(바로 열기 · 넓게 연 뒤 줄이기) / **s13b**: 넓은 창 4종은 접힌 줄 0 · 전체 높이 = R1 과 같은 값(1570 · 배율 250% = 3089) |
| ③ LOW | 닫힘 취소 뒤 한 번짜리 mouseup 처리기가 mouseup 을 영영 놓치면 무기한 남아 돌아와서 누른 무관한 click 을 삼킴 | `armTbCancelSwallow()` — 기다림이 스스로 걷힌다: mouseup(제 할 일) · **새 mousedown**(놓쳤다는 뜻) · 창이 초점을 잃음 · **1초 경과**(`TB_CANCEL_SWALLOW_MS`) · 다시 무장하면 앞의 것부터 걷음(쌓이지 않음). 덧붙여 **mouseup 을 놓친 끌기 자체**도 버린다 — 끄는 중 단추가 떼어진 채 움직이면(`e.buttons` 에 왼쪽 단추 없음) 취소 | 걷히는 길 넷 + 다시 무장(구현 모양 아님) · 끌기 처리기 안 `once: true` 0 · 떼어진 움직임 취소 | **s14d** mouseup 이 안 온 채 Esc → 돌아와서 곧바로 누른 「화면 설정」 = 삼키지 않음(팝오버 열림) / **s14e** 1.3초 뒤 늦은 mouseup 직후의 click = 삼키지 않음 / **s14f** 단추가 떼어진 채 움직이면 끌기 버림(삽입선·전역 표시 0 · 팝오버 열린 채) → 그 뒤 실제 누름 정상 |
| ④ 시험 | 문서 시험이 고친 자리만 열거 — 다른 사용자 노출 문구를 못 찾는다 | **저장소 전체 훑기**로 바꿨다: 제품 소스(`src` · `src-tauri/src` · `ui/src` · `ui/index.html`) · 팩(`cysjavis-pack` — 시험 폴더 제외) · `USER-MANUAL.md` · `README*.md` · `docs/*.md`(그날 기록 = HANDOFF · REVIEW · DESIGN · RELEASE_NOTES · rebase 보고 · PLAN 제외) 약 740 파일에서 「완전 초기화」 단추를 가리키는 줄(뒤에 버튼/단추 · 또는 앞에 툴바/상단/GUI)은 그 줄이나 바로 아래 2줄 안에 「화면 설정」 을 적어야 한다. 예외 = 코드 주석 줄 · 견주는 글(「버튼이라면」 · 「버튼보다」 · 「버튼과」). 규칙이 헐거워져 0건을 0건으로 통과하지 않게, 아는 자리 8곳(cys.rs 2 · guard.sh 1 · main.ts 1 · USER-MANUAL 2 · GUIDE 2)이 실제로 잡히는지도 함께 잰다 | (이 시험 자체) | — |

### R3 에서 지시 밖으로 정한 것(보고에 올림)

1. **넓은 창 팝오버 폭이 4px 줄었다(439 → 435 · 배율 250% 868 → 864)**. 줄의 배치·높이는 그대로다(전체 높이 1570 · 3089 = R1 과 같은 값). R1 의 4px 은 내용이 아니라 자리 잡기의 부산물이었다 — 폭이 「남은 폭에 맞춤」 이라, `fitPop` 이 오른쪽 여백 4px 을 두려고 왼쪽으로 당기면 그 4px 만큼 팝오버가 다시 늘어 오른쪽 끝이 창 끝에 붙었다(R1 수치 「오른쪽 1440」). 지금은 폭 = 내용 폭 고정이라 여백 4px 이 실제로 남는다(오른쪽 = 창 − 4). 줄을 접게 하려면 폭을 내용 폭에 고정해야 했고(접힘을 허용하면 「남은 폭에 맞춤」 이 넓은 창에서도 줄을 접는다 — H13 이 재현), 그 귀결이다.
2. **mouseup 을 놓친 끌기를 움직임에서 버린다**(③ 의 덧붙임). 지적은 「놓친 뒤 Esc」 의 뒷처리였지만, 놓친 순간부터 끌기가 살아 있어 떼지 않은 손을 삽입선이 따라다니는 것이 뿌리라 함께 닫았다.
3. **`docs/GUIDE-clean-reset-KR.md` 본문 1곳**(보고서 밖)을 같은 꼴이라 함께 고쳤다 — ④ 의 훑기가 찾았다.

### R3 게이트 수치(격리 HOME · 좌석 `CYS_*` env 제거 · 이 작업 트리)

| 게이트 | 결과 |
|---|---|
| ui `bun test` 전체 | **2989 pass / 85 skip / 0 fail**(94 파일 · R2 2985 + 4) |
| 새 시험 2파일 | `topbarlayout.test.ts` 40 / 0 · `screensettings.test.ts` 31 / 0 |
| tsc(`typescript@7.0.2`) · `sh build.sh` | rc 0 · rc 0 |
| 실렌더 `screen-settings-headless.ts` | **29칸 ALL PASS**(R2 25 − s13 1 + s13a·s13b 2 + s14d·e·f 3) · 스크린샷 16장 |
| 옛 헤드리스 `v116-headless.ts` `ONLY=c1,c4,c7,c19` | ALL PASS |
| `cargo check --bin cys` | rc 0(그 문구를 재는 cys 시험 없음 — `cargo test --bin cys factory` = 0건 일치 · 612 filtered out) |
| `cargo test --bin cysd manual_` | 6 / 0 |
| 팩 시험(guard.sh 를 읽는 것 5종 + 계약 3종) | `test_completion_guard_notice` rc 0 · `test_dbg_d3_d11_shared_profile_hooks` rc 0 · `test_py_resolver_clt_stub` rc 0 · `test_trust_seed_reflect` rc 0 · `test_preflight_phase1_checks` rc 0(격리 env `JAVIS_ROOT`·`CYS_PROBE_RUNS` 를 준 실행 — 안 주면 시험이 스스로 거부 rc 2) · doc-contract rc 0 · pins rc 0 · pyseal census rc 0 · `gen_ceo_template.py --check` rc 0 · `bash -n guard.sh` rc 0 |
| boot-health 전량 | 165 PASS / 2 FAIL(`H-CLT-1`·`H-CLT-2`) / 1 SKIP · 470.8초 — R2 실행과 FAIL 사유 줄이 글자까지 같고(두 실행의 사유 줄 diff 0), `docs/HANDOFF-1110-docs-d.md` §4 에 적힌 기준(017e6d86)과 같은 합계·같은 두 id. 이 티켓 **이전** 실행의 사유 전문과는 여전히 대조하지 않았다 |
| `secret-scan.sh --all` | clean(1684 파일 · 새 스크린샷 1장을 스테이징한 상태에서) |

음성 대조(전체 재실행 · 뮤턴트가 끝난 뒤 cargo·팩 시험을 돌렸다)
- `mutants.py` = **38종 전부 잡음**(R2 26 + R3 12: 팩 가드 옛 문구 · CLI 자기살해 가드 옛 문구 · 가이드 본문에서 켜는 길 뺌 · 제품 소스에 없는 단추만 가리키는 새 줄 추가 · 새 mousedown 걷기 뺌 · 시간 경과 걷기 뺌 · 한 번짜리 처리기로 되돌림 · 떼어진 움직임을 버리지 않음 · 줄 접힘 뺌 · 이름 기준 폭 0 · 안내 줄이 폭 계산에 낌 · 폭 고정 뺌) · 복원 뒤 71 / 0
- `mutants-headless.py` = **18종 전부 그 칸 FAIL**(R2 11 + R3 7: 줄 접힘 뺌 → s13a · 폭 고정 뺌 → s13b · 안내 줄이 폭 계산에 낌 → s13b · **R2 의 한 번짜리 처리기로 되돌림 → s14d·s14e**(codex 지적의 재현) · 새 mousedown 걷기 뺌 → s14d · 시간 경과 걷기 뺌 → s14e · 떼어진 움직임을 버리지 않음 → s14f) · 복원 뒤 ALL PASS

### R3 함정·관찰

1. **「화면 밖 0」 과 「처음부터 보임」 은 다른 계약이다**: R2 의 s13 은 팝오버 상자가 창 안에 있는지만 봤고, 조작부는 `scrollIntoView` 로 밀어 놓고 「닿음」 이라 했다. 판정에 밀기·당기기를 넣으면 초기 가시성을 가린다 — 지금은 scrollLeft 0 그대로 잰다.
2. **줄을 접게 하면 팝오버 폭 계산이 바뀐다**: 위치 고정 요소의 폭은 「남은 폭에 맞춤」 이라, 접힘을 허용하는 순간 넓은 창에서도 줄이 접힌다(R1 은 줄이 안 접혀서 우연히 성립). 폭을 내용 폭(`max-content`)에 고정하고, 길게 한 줄로 늘어나는 안내 줄은 그 계산에서 빼야 한다(안 빼면 팝오버가 창 폭까지 벌어진다 — H14).
3. **CDP 로 「단추가 떼어진 움직임」 을 보내려면** `button: "none"` 이어야 한다. `button: "left"` 면 `buttons: 0` 을 줘도 눌린 것으로 간다(첫 s14f 실패의 원인).
4. **고친 자리를 세지 말고 훑어라**: R2 에서 5곳을 고치고 「남은 2곳은 범위 밖」 으로 적었지만, 사용자에게 닿는 같은 결함이라 닫은 것이 아니었다(codex 2R). 훑기 시험은 그 뒤 한 곳(GUIDE 본문)을 더 찾았다.
5. **훑기 규칙의 한계**: 「단추를 가리키는 꼴」 을 낱말 모양으로 잡는다(뒤에 버튼/단추 · 앞에 툴바/상단/GUI). 그 모양을 벗어난 안내(예: 「맨 오른쪽 초기화 메뉴」)는 못 잡는다. 견주는 글 예외도 낱말 셋(「이라면」 · 「보다」 · 「과」)이다.
6. 좁은 창 + 큰 배율에서 팝오버는 세로로 길다(500×600·250% 에서 줄마다 두 줄). 세로 스크롤과 구획 접기로 받는다.
7. R2 함정 2(뮤턴트와 cargo 를 겹쳐 돌리지 않기 · boot-health 전량의 찌꺼기 폴더)는 이번에도 그대로 지켰다 — 뮤턴트(bun 38 · 실렌더 18)가 전부 끝난 뒤 cargo·팩 시험·boot-health 를 돌렸고, boot-health 가 다시 남긴 찌꺼기 폴더(로그 1개)는 내용을 보고 지웠다(커밋에 섞이지 않음).
8. 실렌더는 여전히 헤드리스 크롬 계산값이다(웹뷰 실기 아님). `e.buttons` 판정은 맥 WKWebView · 윈 WebView2 실기에서 재지 않았다(둘 다 표준 속성을 지원하나 이 저장소에서의 실측은 없다).

