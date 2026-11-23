# HANDOFF — TICKET=cysr-1118u-chat (cysr 1.1.18 긴급판 갈래 A = 대화 화면)
가지 feat/1118u-chat · 기점 9c46ff6d0(v1.1.17) · 브리프 = ~/axdev/master/briefs/2026-11-23-cysr-1118-urgent-lanes.md

## ① 대화 화면 토큰 한도 줄
- 박사님 원문: 「윈 cysr 대화 화면에는 토큰 사용 표시가 안 보인다.」(11-23)
- 원인: `ui/src/views/index.ts` registry `onShown` 이 작업 화면 밖 화면을 켜면 `bodyRow.style.display = "none"` — 한도 표시는 bodyRow 안 왼쪽 상황판(`paintBoard` 의 limit/accounts 줄)과 #ws-usage 에만 있었다 → 대화 화면엔 한도 표시 0.
- 설계: 대화 화면 머리(.cv-head)에 `.cv-limits` 한 덩이. 값 = `statusboard.chatLimitRows(accountsCache, now)` — 상황판과 **같은 판정**(계정 ≥2 = `accountLimitRows` 그대로 · ≤1 = `limitLine`/`limitTitle` 한 줄 · 7d 없음 = 줄 없음). 원천 = main.ts 의 15초 `usage_accounts_all` 캐시(3초 사이드바 틱이 화면과 무관하게 계속 돎) → **새 RPC·새 invoke 0**. 배선 = BootDeps.limits → ChatCore Deps.limits → `act.limits()`(없음·던짐 = [] · invoke 0). 대화 화면은 5초마다 들여다보고 값이 바뀔 때만 다시 그림(말 목록 다시 그리기와 분리 · 입력칸 무접촉). 이름 = accountShortLabel(별명·폴더 라벨) = 이메일 0. 60/80 문턱 색 = 상황판과 같음.
- 216px 잘림: 대화 화면 머리는 사이드바가 아니라 가운데 칸이다 — 계정마다 한 덩이(덩이 안 줄바꿈 0 · 덩이 사이 접힘 · 이름만 14em 말줄임) → 폭 420/700/1400 실측 잘림 0·화면 밖 0.
- 시험: `ui/src/chatlimits.test.ts` 9건 — 기점 붉음 0/9 → 고침 초록 9/9 · 전 UI 시험 3987 pass / 0 fail · tsc 0.
  게이트 `ui/e2e/chatlimit_gate.py`(실제 번들 + chat_gate 대역 + 계정 2개 이메일 라벨): 기점 번들 FAIL 3(「한도 줄 보임」 3폭) → 고침 번들 fails [] (상황판 계정 줄과 같은 글 · 이메일 0 · 잘림 0 · 콘솔 오류 0).
- 해소 판정 남은 몫: 「그 판 빌드(맥·윈) 대화 화면 캡처」 = 통합 뒤 rel 좌석(윈 실기).
