# HANDOFF — TICKET=v111-restore (복원 흐름 3건 + 60%+ 순환 권유)

브랜치 `fix/v111-restore` (← `rebase/v1.1` e2ca5f66) · 워커 surface:886 · 2026-09-21

## 재현 = VM 실기로 이관 (★가장 먼저 읽을 줄)
격리 cysd 시험 인스턴스 재현(「임무 0 함대 3자리 재시작 → 3자리 · 주입 1건 · 전부 대기」)은
**이 브랜치에서 수행하지 않았다.** master 판정(2026-09-21)으로 **VM 재시작 실기(병합 뒤 S1/S2)**가
그 갈음이다. 즉 아래 「무엇을 고쳤나」는 전부 **코드 경로 + 단위 시험 + 뮤턴트**로 증명됐고,
**실기에서 그렇게 보인다**는 아직 미측정이다 — VM 실기에서 이 세 가지를 눈으로 확인하라:
1. 자리 수 = **3** (콜드 기동에서도 자리표가 회수된다)
2. 각 자리가 받은 깨움 글 = **1건** (같은 목적의 글이 겹치지 않는다)
3. 임무 0 이면 세 자리가 **한 줄 보고 후 ❯ 대기** (자기발의 티켓 0)

## 무엇을 고쳤나
### ① 복원 팝업이 묻지 않는다 + 임무 게이트가 판정 주체
- `ui/src/restorebrief.ts` — `continueLabel`/`continueText` 삭제. 버튼은 [닫기] 하나,
  이 카드에서 나가는 주입 경로 **0**. 제목도 질문이 아니다(물음표 0).
- `src/bin/cys.rs restore_directive(master)` — `javis_mission.py status` 의 **종료코드만**
  근거로 삼게 교체(0=임무 있음 → 이어서 / 1·2 → 한 줄 보고 후 대기 · 자율 착수 금지).
- 팩 디렉티브는 **건드리지 않았다**. `MASTER_DIRECTIVE §0-C` 가 이미 그 계약의 정본이라
  어긋나 있던 것은 restore 문구와 UI 팝업 둘뿐이었다(헌법 무접촉).

### ② 좌석당 복원 글 1회 — 단일 발신 + 멱등 표식
- 발신 지점 표(실측): `boot_agent_on_surface`([RESUME]) · `run_restore` 좌석내재연결([RESTORE]) ·
  `run_restore` fresh([RESTORE]) · `javis_phoenix.py`(launch-agent+reinject) ·
  `src-tauri run_sidecar_restore`(cys restore) · `cysd main` 콜드부트 auto-restore.
- 중복 원인 한 줄: 복원 경로는 **설계상 겹치고**, 저장소가 적어 둔 「run_restore 멱등이라
  겹쳐도 안전」이 보장한 것은 **좌석 중복 스폰 0** 까지였지 **주입 중복 0** 까지가 아니었다.
- 수리 2겹: `compose_boot_directive`(순수)가 한 문자열로 조립 → 전송 1회 ·
  `cys::restore_mark` 표식(create_new 원자 claim · TTL 300s).
  ★TTL 밖 재주입은 **일부러 막지 않는다** — 영구 표식은 좌석을 영영 말 없는 좌석으로 만든다.

### ③ 빈 자리표 회수 (master 판정 B + 무접촉 조건)
- 원인: `ui/src/main.ts start()` 의 충전 루프가 입양할 좌석이 없는 탭에 **역할 없는 맨 셸**을
  만든다 → 콜드 기동 4자리 / 재시작 복원 3자리(경로 의존).
  팩 정책 「role=master 빈 셸」(`javis_bootstrap.py`)과는 **다른 물건**이라 정책 충돌 0.
- 수리: `ui/src/placeholderclose.ts`(순수 판정) + `refreshPaneTitles` 회수 스윕.
  ⓐ **UI 가 만든 번호만** 대상(남의 페인은 번호가 없어 원리적으로 불가침) ·
  ⓑ 편성 좌석이 붙은 뒤 · 무접촉(입력 이력 0 ∧ 화면 줄 수 ≤ 3)일 때만 ·
  ⓒ 손댔으면 닫지 않고 **알림도 없다**. 모르는 값은 전부 false(fail-closed).
- ★승계안(A)을 쓰지 않은 이유: 박사님이 직접 연 터미널도 역할 없는 맨 셸이라 같은 그물에 걸린다.
  실패 방향이 「남의 작업창 탈취」인 안은 기각됐다.

### ④ 복원 직후 60%+ 순환 권유
`surface.list` 가 이미 싣는 `usage.ctx_pct` 재료(추가 RPC 0) → 알림 1줄. 자동 집행 0.
못 잰 자리(null·비숫자)는 넘었다고 말하지 않는다.

## 함정 (다음 사람이 밟기 쉬운 것)
- `ui` 의 `bun run typecheck` 는 `node_modules` 부재로 **기준선이 이미 12 오류**다.
  판정은 「신규 0」으로 하라(기준선은 `git stash` 로 내 변경만 빼고 재측정).
- 옛 계약을 고정하던 핀 3개를 갱신했다(지우지 않고 경위를 적었다):
  `injection_hold_is_never_discarded_silently_source_pin` 동결값 **5→3**(주입 지점이 접힌 것이지
  침묵이 아니다) · `wswiring` 의 「send_input 1곳」·「machineOrigin 표식」 → 「send_input **0곳**」.
  ⚠동결값을 다시 내리려면 「어느 주입이 어디로 접혔는가」를 함께 적어라. 못 적으면 그것이 침묵이다.
- `cys todo-path` 가 `~/.cys/pack/round/` 를 가리켜 **브리프의 라이브 무접촉 규율과 충돌**한다.
  이 티켓에서는 todo 파일을 쓰지 않았다(진행률 집계에 0% 로 보일 수 있다) — 우선순위 판정 필요.
