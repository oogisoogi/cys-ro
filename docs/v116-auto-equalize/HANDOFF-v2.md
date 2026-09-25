# HANDOFF — v116-equalize-v2 (워커 기둥 폭만 균등 · 사람 위아래 나눔 보존)

- 가지 `fix/v116-equalize-v2` · 기점 2db641e8(4차 통합 머리) · 작업트리 `~/axdev/.wt/v116-equalize-v2` · push·병합 = master 게이트(워커 미실행).
- 설계 = `DESIGN-v2.md`(master#88533ed8 승인 · Q1 = ⌘⇧D 는 actionSplit("col") 그대로 = 진짜 세로 분할) + 「박사님 결정 14:5x」 절
  (좌열 폭 = 균등 정렬 제외 · 기본 = 창의 25% · 노트북 90칸 · 상한 50% · master#db159bcf · master#73a7390d).

## 끝난 것
| 항목 | 위치 | 증거 |
|---|---|---|
| autoArrange v2(기둥 · 무정렬 최소 변경 · 규칙 5 기둥 수) | ui/src/formation.ts | bun 전체 초록 · 뮤턴트 18/18 |
| actionSplit 방향 전달 · 팔레트 「세로 분할」 복원 · ⌘⇧D 주석 | ui/src/main.ts(3곳) | autoarrange.test 「v2 — 팔레트」 절 · 헤드리스 c18i |
| 시험 신설 16 · 교체 9 | ui/src/autoarrange.test.ts | 아래 「바꾼 시험」 |
| 헤드리스 c18i 교체 · c18v 신설 | docs/v116-ui-evidence/v116-headless.ts | 새 번들 c18 전건 PASS · 옛 번들(2db641e8) c18i·c18v FAIL · c18a~h PASS |
| 좌열 기본 폭(defaultLeftShare · leftAuto 표지 · 창 크기 변경 재측정 · 옛 1/2·1/3 이동) | formation.ts · main.ts · adoptlayout.ts | bun · 헤드리스 c18D·h·w·o |
| Fable 적대 1R 봉합 R1~R3 | formation.ts(pil 잘라 보기 · had 우선 · heal) | 「Fable 적대 1R 봉합」 절 · M29~M31 |
| 뮤턴트 하네스 | mutants-v2.py · mutants-v2.txt | 스냅샷 기준선 162/0 → 30/30 KILLED |
| 디버깅 정밀 패스 | debugpass-v2.test.ts(증거 · 스위트 밖) | 14,183걸음(창 크기 4종 · 끌기 3,055 · 재측정 177) · 사람 폭 유지 7,504 · 기본 폭 1,237 대조 · 위반 0 |

## 바꾼 옛 시험(이유 = 박사님 결정 09-25 14:1x 「사용자가 세로로 정렬한 것 유지 · 워커 좌우폭만」)
1. 「사람이 위아래로 나눈 워커 칸 → 한 줄로 편다」 → 「그대로 · 기둥끼리 균등(v2)」 — v1 사양 자체가 뒤집혔다.
2~5. 「좌열 이상 위치 → 표준 배치로 폴백」 4건 → 무정렬(루트 오른쪽 1/(기둥+1) · 그 자리 접힘) — 표준 폴백은 사람 위아래 나눔을 지운다(처리표 4행).
   (5번째 「master·cso 좌우 나란함 → 표준」은 기대값 그대로 통과 — 처리표 3행: 좌열만 표준 · 워커 칸 하나라 결과 동일.)
6. 속성 시험 3000 트리: 「좌열 밖 세로 분할 0 · 좌열 아닌 칸 전부 같은 가로 몫」 → standard 모드에만 유지 · auto 는
   「손 안 댄 입력 워커 기둥 = 같은 객체」 + 「맞춘 모양이면 워커 기둥 폭 균등」 + 「기둥 폭 합 = 1」 · add 에 dir col 섞음.
7. 「master 판정 ⓒ — 팔레트 세로 분할 0 · ⌘⇧D 이름 없이 유지」 2건 → 「v2 — 팔레트 세로 분할 복원 · ⌘⇧D = col · 방향 전달」 3건.
8. 호출부 핀 「분할」 = `{ sid, after: target }` → `{ sid, after: target, dir }` · arrangeWs 핀에 `currentDefaultLeftShare()` 인자.
10~15. (박사님 결정 14:5x) 옛 D1 = C 절 전체(첫 부팅 1/2→1/3 · 규칙값 경계 4 · 닫기 규칙값 따라감) → 「좌열 가로 폭은 균등 정렬에서 뺀다」 절
   (defaultLeftShare 3440·1512·900 · 0→1→2→5 내내 25% · 창 크기 변경 · 사람 0.40 · 정렬 단추 · 옛 1/2·1/3 ±0.009 이동 / ±0.015 보존) ·
   F1 잔재 몫 기대값(0.25→0.125 · 1/6→0.125) · 처리표 3행 기대값(표지) · 규칙 5 시험 2건(기둥 수 기준 폐기) → 삭제 대신 기본 폭 불변 시험으로 흡수 ·
   formation.test 「좌열 1/3 수렴」 → 25% · 「master+worker 1 = 1/2」 → 25% · adoptlayout.test master 1/3·1/2 → 25% · 헤드리스 c18a~e·i·v·h 의 1/3 → D.
9. 헤드리스 c18i(세로 분할 0 단언) → 세로 분할 복원·⌘⇧D = 대상 아래 단언.

## 남은 것 · 보류
- (해소) 좌열 가로 폭 보류 → 박사님 결정 14:5x 로 구현.
- 잔여: 창 크기 변경 재측정은 window resize 에만 걸려 있다 — 파일 트리 패널 열기/닫기처럼 창은 그대로인데 배치 영역(#root)만 좁아지는 경우는
  다음 열기·닫기 때까지 옛 기본 폭(좁아진 만큼 90칸 미만일 수 있다). 글꼴 크기 변경도 같다.
- 잔여(수용): 손으로 정확히 1/2·1/3(±0.01)에 맞춘 사용자는 옛 기본값으로 읽혀 새 기본 폭으로 옮겨진다.
- 무접촉(범위 밖): 전문가 칸 「창 만들기」 메뉴는 여전히 「오른쪽에 새 창」 한 갈래(v1 D2 · closeguard.test 핀). 「아래에 새 창」 복원은 지시 없음.
- 무정렬 모양은 자동 경로가 스스로 만들지 않는다(디버깅 패스 unfit 0) — 창 옮기기(movePane)·옛 저장 배치·역할 변경으로만 생긴다.

## 함정
- ui/node_modules = 심볼릭 링크(→ cys-v116-integ) · `.gitignore` 의 `node_modules/` 는 링크를 못 걸러 untracked 로 보인다 — `git add -A` 금지.
- 뮤턴트는 스냅샷(스크래치 git archive)에서만 — 작업트리에서 돌리지 마라.
- leftColumnShare(2) = leftColumnShare(3) = 1/3 — 규칙 5(기둥 수 vs 좌석 수) 시험은 1↔2 경계로만 갈린다(M9 생존 → 시험 추가로 봉합).

## 재현
```
cd ui && bun test                                   # 전체
DIST=ui/dist CHS=<chrome-headless-shell> ONLY=c18 bun docs/v116-ui-evidence/v116-headless.ts
python3 docs/v116-auto-equalize/mutants-v2.py <git archive 스냅샷>   # 스냅샷/ui/node_modules 링크 필요
```
