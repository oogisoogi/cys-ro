# HANDOFF · TICKET=cysr-1118-ui (2026-11-23 · worker-3 · 갈래 A = ui)

가지 `feat/1118-ui` · 기점 `f1fe7aa91`(fix/chat-held-win 확정 머리 · master#10cb05f1) · 발행·태그·main 0.

## ② 상황판 계정 줄 (🗣박사님 11-22 19:4x 「이상하다. 계정도 하나밖에 안 보인다.」)

### 원인(코드 판독 · 확신 높음)
- `ui/src/statusboard.ts` `top7d()` 가 모든 계정의 7d 창 가운데 **가장 높은 값 하나**만 골라 `limitLine` 한 줄로 그렸다(설계 = 1g 「가장 높은 한도」).
  두 계정 값은 `usage_accounts_all` 로 이미 수집된다(이 기기 11-23 실측 `cys usage-accounts --json` = claude 계정 2개 · 7d 43 / 38) → 결함이 아니라 표시 설계.

### 설계
- 새 순수 함수 `accountLimitRows(accounts, nowSecs)` = 계정마다 7d 최고 한 줄 `{name, pct, line, title}`.
  - 거르기 = `accountRates` 와 같음(관측 전 `updated_at` 없음 · 7d 없음 = 빠짐).
  - 이름 = `usagebar.accountShortLabel`(별명 > 현재 로그인 폴더 > 제공자 · **이메일 0** — 사용량 칸과 같은 이름).
  - 차례 = 이름순(값이 바뀌어도 줄이 자리를 바꾸지 않음) · 같은 이름 = 「이름 2」.
  - 짧은 줄 = `43% · 금 06:00`(「초기화」 낱말·남은 시간은 툴팁 `title`).
- `paintBoard` 옵션 `accounts` — **둘 이상일 때만** 한도 단추 안을 계정마다 한 줄로(이름 · 「% · 요일 시각」). 하나면 종전 한 줄(막대 + `86% · 금 06:00 초기화`) 그대로.
  - 계정 줄에는 막대를 두지 않는다 — 막대를 두면 216px 설정 폭(실폭 199px)에서 「claude-acct2」가 「claude…」로 밀려 잘렸다(실측 캡처). 높은 값은 글자 색(막대와 같은 60·80 문턱).
  - 「% · 요일 시각」은 줄이지 않는다(flex none · 중간 잘림 0) · 이름만 아주 길 때(별명 24자) 말줄임 + 전문 툴팁.
- `main.ts` 배선 1줄(`accounts: accountLimitRows(accountsCache, nowSecs)`) · 누르면 펼침(사용량 칸) 동작 그대로.

### 시험
- `ui/src/statusboard.test.ts` 계정별 3건 추가 — 고치기 전 3 fail(함수 없음) / 고친 뒤 10/10.
- 렌더(헤드리스 크롬 · 실제 번들 + 대역 · 1920·1280 × 계정 1·2·3(긴 별명)) = 6/6 PASS: 글자 잘림 0 · 가로 넘침 0 · 이메일 0 · 콘솔 오류 0 · 계정 1 = 종전 한 줄 정규식 그대로.
  하네스·캡처 = `~/axdev/workers/cysr-1118-ui/evidence/statusboard/`(run.cjs · mk.py = `ui/e2e/statusboard_gate.py` 의 대역·탐침을 그대로 빌려 계정만 바꿈 · 파이썬 playwright 가 이 기기에 없어 node playwright 로 돌림).
- `bun test` 전체 3970 pass · 89 skip · 0 fail · `bunx tsc -p tsconfig.check.json` 오류 0.
- 해소 판정 중 「빌드 상황판 캡처」 = 위 헤드리스 캡처(`two-1280.png`) · 실기 앱 캡처는 통합 빌드에서 master 몫.
