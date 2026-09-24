# opus 적대 3R — 대상 8ae720fc..afba077c(exitbanner.ts 만) · 판정 ACCEPT(MAJOR 0 · MINOR 0 · 새 NIT 1 + NIT-1 확장)
- MINOR-3 · agy 2R 사례(커서 빈 마지막 행) 닫힘 — 대체 화면은 커서 무시.
- 행 계산: last(0-기준) 다음 행 = last+1 → CUP 1-기준 = last+2 정확(exitbanner.ts:47) · 빈 대체 화면 last=-1 → CUP(1;1).
- 가득: CUP 마지막 행 + \r\n 1번 → 맨 윗줄 1줄 손실 = 최소(:46). 그 밖 대체 화면 손실 0.
- 앞 줄 줄넘김 대기: CUP 가 열 0 으로 보내며 해제(InputHandler._setCursor) — 무해.
- 주 화면 무변: bannerRow = lastContentRow(v, v.cursorY) · 출력 바이트 동일(:35-36,49).
- 미결(고치지 않음): NIT-5 창이 16열 미만이고 배너 행이 rows-1 이면 배너 글이 접혀 맨 윗줄 1줄 스크롤 소실 · 죽은 앱이 자동 줄넘김을 끈 경우(ESC[?7l) 배너가 잘림. NIT-1 확장: 배경색만 칠한 빈 줄을 빈 줄로 봄 — 배경 전체를 칠하는 TUI 면 대체 화면에서 배너가 그런 줄(중간)에 앉을 수 있음(글 덮어쓰기·줄 손실은 없음). 종료 2회 = 조건부(2R 그대로 · 실경로 1회라 NIT).
