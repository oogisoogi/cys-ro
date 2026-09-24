# opus 적대 2R — 대상 802ca149..8ae720fc(MINOR-1 수리) · 판정 ACCEPT(새 MINOR 1 · NIT 1)
- MINOR-1 닫힘: 가득(대상=rows-1)이면 스크롤 1번 = 맨 윗줄 1줄 손실 = 최소(대안은 상태 줄 덮어쓰기 = 같은 양 손실).
- MINOR-3(신규 · 802ca149 부터 있었고 1R 에서 놓침): 대체 화면 · 마지막 행 빔 · 내용이 rows-2 까지 → 전체 배너의 뒤 \r\n 이 스크롤 → 윗줄 1줄 손실(0 가능). 권고: 대체 화면이면 뒤 \r\n 을 늘 뺀다.
- buf.type: xterm 5.5 는 'normal' | 'alternate' 뿐(common/public/BufferApiView.ts:14 · BufferNamespaceApi.ts:21-22) — 비교 정확. 주 화면 무변 · 판독 실패 강등 = EXITED_BANNER 그대로.
- NIT 종료 2회 1배너는 조건부: 대기열 [reset1, reset2, banner1, banner2] 에서 두 콜백이 같은 화면을 읽어 같은 글을 쓰므로 스크롤이 없을 때만 1개. 대상이 바닥 근처(주 화면 target ≥ rows-2 · 대체 화면 가득)거나 두 번째가 첫 배너 해석 뒤면 2개가 잇달아 선다(내용 아래). 실경로 = Rust 가 태스크당 1회(main.rs:4122-4159) → NIT. c18m 은 유리한 모양만 잰다 → 「조건부」로 기록.
- 1R 항목: MINOR-3 은 지금 수리 · MINOR-2(시험 충실도 — c18 로 일부 덮음)·NIT-1~4·종료 2회 = 기록만.
