# PPT 스타일 카탈로그 — 11종

이 파일은 `tools/gen_catalog.js` 가 `styles/*.js` 에서 만든다(머리말만 `references/catalog.head.md`). 손으로 고치지 않는다.

## 쓰는 순서

1. 분위기를 말로 묘사한다 → `python3 tools/pick.py "묘사 문장"` → 상위 2개와 근거(일치한 낱말)가 나온다. 아는 낱말이 없으면 「일치어 없음」 이 나온다 — 그때는 아래 「한눈에 보기」 표에서 고른다.
2. 고른 스타일의 견본을 `bash run.sh samples <id>` 로 만들어 보여 준다(2개를 나란히).
3. 정해지면 내용을 그 스타일의 「입력 칸」 모양 JSON 으로 적어 `bash run.sh deck <내용.json> <결과.pptx>` 로 만든다. 세 장 모양(제목 · 카드 · 질문)으로 모자라면 `styles/<번호>-<id>.js` 의 `THEME` · `layouts()` · 세 함수와 `lib/kit.js` 의 `tx` · `box` · `runs` · `icon` 을 가져가 새 장을 코드로 더한다(끝에 `lib/theme.js` 의 `applyTheme(파일, THEME)`).

## 스타일과 무관하게 지키는 것

- 원문 용어는 그대로 쓴다. 본문은 24pt 를 기준으로 한다(카드·표 안은 16pt 이상). 견본도 이 기준으로 짰다 — 카드 안 글은 16~20pt, 질문은 24pt 이상.
- 줌 PPT 배경 모드로 쓸 때는 오른쪽 아래(가로 7.7인치 이후 · 세로 4.175인치 이후)를 비운다. 이 견본들은 줌 자리를 비우지 않은 일반 화면 기준이다.
- 아이콘은 전부 Phosphor(`react-icons/pi` · MIT)다 — 화면에 출처를 적을 의무가 없다. Font Awesome(`react-icons/fa`)은 CC BY 4.0 이라 쓰면 출처 표기가 필요하니 새 장에도 Phosphor 를 쓴다.
- 글꼴 파일은 이 스킬에 들어 있지 않다. 스타일이 지정한 글꼴(Apple SD Gothic Neo · 나눔글꼴 · 마루 부리 · JetBrains Mono)이 그 컴퓨터에 있으면 그대로 보이고, 없으면 파워포인트·키노트가 대체 글꼴로 보여 준다. `tools/check_pptx.py` 가 빠진 글꼴을 알려 준다.

## 확인한 것과 못 한 것

- 확인: 11종 견본을 빌드해 `tools/check_pptx.py`(zip · 필수 파일 · 장 수 · 글 넘침 추정 · 화면 밖 상자 · 글꼴 유무) 통과, LibreOffice 로 PDF 변환 뒤 장 수 일치.
- 못 함: 맥 PowerPoint · Keynote · 줌 실화면에서 열어 보지 않았다. 「NanumSquare Neo Heavy」 · 「NanumSquareRound ExtraBold」 · 「MaruBuriOTF」 처럼 굵기·OTF 이름으로 지정한 글꼴이 PowerPoint 에서 같은 굵기로 잡히는지는 미확인이다(LibreOffice 에서는 잡혔다).
- 6번 표지의 「故」 와 「○」 는 나눔명조에 글자가 없어 다른 글꼴로 대체돼 찍힌다.
- 견본 문구(행사 이름 · 수치 · 날짜)는 서식을 보이기 위한 예시다. 5번의 수치는 전부 지어낸 샘플이고 슬라이드에도 그렇게 적었다.
