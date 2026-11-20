---
name: ppt-styles
description: 스타일 11종 중 하나를 골라 발표 자료 .pptx 를 바로 만든다. 「PPT 만들어」「슬라이드 뽑아」 때 — 기존 덱 분석·우리 기준 수립은 ppt-design-system, 영상 보고는 video-report-deck.
---

# ppt-styles

스타일 11종(분위기·팔레트·글꼴·배치가 정해진 pptxgenjs 코드)에서 하나를 고르고, 내용을 JSON 으로 적어 `.pptx` 를 만든 뒤 기계 점검까지 한다.
스킬 폴더: `SK="${CYS_PACK_DIR:-$HOME/.cys/pack}/skills/ppt-styles"` · 스타일 목록·입력 칸 = `$SK/references/CATALOG.md`.

## ① 언제 쓰나

- 「PPT 만들어 줘」「이 내용으로 슬라이드 뽑아 줘」처럼 **내용은 있고 모양은 정해진 스타일에서 고르면 되는** 때.
- 분위기를 말로만 줄 때(「따뜻한 학부모 발표」「다크 테마 기술 해설」) → 선택기가 상위 2개를 고른다.
- 쓰지 않을 때: 사용자가 준 기존 덱들을 분석해 그 회사·팀만의 기준을 세우는 일 = `ppt-design-system` · 영상(mp4) 보고 = `video-report-deck` · 한글 문서(.hwp) = `hwp`.

## ② 순서

0. **처음 한 번 — 의존 설치**(node 18+ 필요 · 팩 폴더가 아니라 `~/.cys/deps/ppt-styles` 에 설치):
   `bash "$SK/run.sh" setup` → 찍힌 `cd … && npm ci` 한 줄을 실행(약 130MB). 다른 곳에 두려면 `PPT_STYLES_DEPS=<폴더>`.
1. **스타일 고르기**: `python3 "$SK/tools/pick.py" "<분위기 묘사>"` → 1·2순위와 근거 낱말. 「일치어 없음」이면 CATALOG 「한눈에 보기」 표에서 고른다.
   견본을 보여 주려면 `OUT=<폴더> bash "$SK/run.sh" samples <id1> <id2>` → `<id>.pptx`(+ LibreOffice·pdftoppm 이 있으면 `<id>-N.png` · `sheet-<id>.png`).
2. **내용 JSON 쓰기**: CATALOG 의 그 스타일 「입력 칸」 예(또는 `$SK/references/example-deck.json`)를 본떠 쓴다.
   `{ "style": "<id>", "title": "<파일 제목>", "footer": "…", "slides": [ {"kind":"title",…}, {"kind":"cards",…}, {"kind":"question",…} ] }`
   - `kind` 는 title · cards · question 세 가지. 같은 kind 를 여러 번 써도 된다(카드 장 여러 장 등).
   - 원문 용어·숫자는 사용자가 준 그대로. 견본 글을 남겨 두지 않는다(빈 칸은 빈 글로 나간다).
3. **만들기 + 점검**: `bash "$SK/run.sh" deck <내용.json> <결과.pptx>` — make_deck.js → `check_pptx.py`(LibreOffice 가 있으면 PDF 쪽 수 대조까지).
   - bash 가 없으면(윈도): `node "$SK/tools/make_deck.js" 내용.json 결과.pptx` 다음 `python "$SK/tools/check_pptx.py" 결과.pptx --slides <N> [--pdf]`.
4. **세 장 모양으로 모자랄 때**(표·타임라인 등): 새 build 스크립트에서 `styles/NN-<id>.js` 의 `THEME`·`layouts()`·세 함수와 `lib/kit.js`(tx·box·runs·icon)를 불러 장을 코드로 더하고, 끝에 `lib/theme.js` 의 `applyTheme(파일, THEME)` · 의존은 `require("$SK/lib/deps").setup()` 을 맨 앞에.
5. 결과 `.pptx` 경로와 점검 결과 줄(PASS/FAIL · 경고)을 사용자에게 그대로 보인다.

## ③ 주의할 점

- **자동 설치 안 함**: node·npm 패키지·python·LibreOffice 가 없으면 스크립트가 무엇이 없고 어떻게 설치하는지 찍고 코드 3 으로 끝난다. 설치 명령은 사용자가(또는 승인 뒤) 실행한다.
- **글꼴 파일은 들어 있지 않다.** 스타일 글꼴(Apple SD Gothic Neo · 나눔스퀘어 네오/라운드 · 나눔명조 · 나눔바른고딕 · 마루 부리 · JetBrains Mono)이 그 컴퓨터에 있으면 쓰고, 없으면 열 때 대체 글꼴로 보인다. `check_pptx.py` 가 「글꼴 없음 + 무료 설치처」를 알려 준다. Apple SD Gothic Neo 는 맥 전용이라 윈도에서는 맑은 고딕 등으로 바뀐다 — 받는 사람이 윈도면 나눔 계열 스타일(2·4·5·6·7·9번)이 안전하다.
- **글 넘침은 어림이다**: 「글 넘침 의심」은 글자 수·크기로 높이를 어림한 경고다(렌더가 아니다). 뜨면 제목을 줄이거나 장을 나눈다. 정확히 보려면 PDF/PNG 를 눈으로 본다.
- **카드 개수**: 스타일마다 한 장의 카드 자리가 정해져 있다(1번 2개 · 6번 6개 · 나머지 3개). 많으면 make_deck 이 「(계속)」 장으로 나누고, 고정 자리보다 적으면 빈 카드로 채우며 `[경고]` 줄을 찍는다.
- 5번(연구 발표) 차트의 세로축은 값에 맞춰 잡힌다. 눈금을 정하려면 `chart.max` · 숫자 모양은 `chart.format`(예 `"0.0"`).
- 아이콘은 Phosphor(`react-icons/pi` · MIT)만 쓴다. Font Awesome(`react-icons/fa`)은 CC BY 4.0 이라 쓰면 출처 표기가 필요하다.
- 1번 스타일 이름의 「교회」, 6번 「추모 예배」, 7번 「성경학교」 등은 **어울리는 용도 이름**이다. 견본 글은 서식 시연용 가상 예시다.
- 결과·견본은 사용자가 정한 폴더에 쓴다. 팩 폴더(`$SK`) 안에는 쓰지 않는다(`tools/gen_catalog.js` 만 예외 — 저장소에서 스타일을 고칠 때 CATALOG.md·styles.json 을 다시 만드는 유지보수 도구).
- 스타일을 더하거나 id 를 바꾸면 `tools/pick.py` 의 `LEX` 에도 같은 id 로 낱말을 넣는다(어긋나면 pick.py 가 멈춘다). 굵기를 글꼴 이름으로 고른 곳(Heavy · ExtraBold)에는 `bold: true` 를 겹치지 않는다.
- 외부 유래: `vendor/` = theme-factory(Apache-2.0) · frontend-slides(MIT) 원문과 LICENSE(`vendor/README.md`). npm 의존의 `image-size` 는 알려진 취약판이라 `overrides` 로 2.0.4 이상에 묶었다(pptxgenjs 는 실행 중 이 패키지를 부르지 않는다).

## ④ 확인하는 방법

- `run.sh deck` 마지막 줄이 `PASS <파일> 장 N …` 이고, `[pdf] … 쪽 N` 이 장 수와 같다.
- `[경고]` 줄이 있으면 하나씩 처리하거나, 처리하지 않은 이유를 사용자에게 적는다(글 넘침 · 화면 밖 상자 · 빈 장 · 없는 글꼴).
- 사진·글꼴이 중요한 덱은 PNG(`pdftoppm -png -r 80 결과.pdf 장`)를 전부 눈으로 보고, 받는 사람 기기(파워포인트/키노트)에서 한 번 열어 본다 — LibreOffice 렌더는 미리보기다.
- 시험 입력 결과(2026-11-06 · 맥 · node 22 · LibreOffice 있음): ① 보통 입력(modern-minimal 4장) → PASS 경고 0 · PDF 4쪽. ② 지저분한 입력(church-navy-gold · 150자 영한 혼합 제목 · 빈 목록 · 카드 1개/5개 · 질문 1개) → 6장으로 나눠 만들어지고 PASS + 「1장 글 넘침 의심」 경고 1(렌더에서도 제목이 화면 위로 넘침 확인). ③ 차트 입력(research-data · 값 350~428) → 세로축 0~500 으로 잡혀 PASS. node 를 PATH 에서 빼고 실행 → 설치 안내 2줄 + 코드 3 · 의존 폴더가 빈 채 실행 → `run.sh setup` 안내 + 코드 3. 견본 11종 → 전부 PASS 경고 0. 장 목록 대조 시험(2R 수정 · 1-normal 을 바꾼 pptx): 장 목록을 비우고 slide1~4.xml 을 남김 → FAIL 「장 목록에 없는 장 파일 4개 · 장 목록이 비어 있음」 · 목록엔 있는데 slide2.xml 없음 → FAIL · 목록 밖 slide9.xml 추가 → FAIL(셋 다 코드 1 · PASS 줄에 「장 목록↔파일 일치/불일치」 표시) · 위 3벌 재실행은 그대로 PASS. 그룹 도형 시험(2R 수정 · 중첩·확대 그룹 3사례): 바깥 그룹이 650pt 로 밀어 화면 밖이 된 글상자 → 「화면 밖」 경고(고치기 전엔 못 잡음) · 자식 좌표 x=900pt 이지만 chOff 로 화면 안 100pt 인 글상자 → 경고 없음(고치기 전엔 오탐) · 4배 확대 그룹 안 작은 글상자 → 넘침 경고 없음(고치기 전엔 오탐) · 3벌·견본 11종 재실행 경고 수 변화 없음. 스킬 없이 대조는 하지 않았다.
