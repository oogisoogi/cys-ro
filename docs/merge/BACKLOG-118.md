# BACKLOG-118 — 1.1.8 병합에서 다음 판으로 넘기는 것 (TICKET=cysr-118-merge-lead)

> 행마다: 무엇 · 왜 넘기나 · 근거(결정·커밋) · 다음 판에서 할 일. 판정 = master.

| # | 무엇 | 왜 넘기나 | 근거 | 다음 판에서 할 일 |
|---|---|---|---|---|
| B1 | **휴면-on CI 레인 = 1.1.9** — ui 의 휴면·미수용 기능 배선 시험 82건(usagewiring 34 · expertwiring 19 · updatewiring 10 · deptprogresswiring 8 · teamproposal 4 · confirmlayer 3 · feedbackwiring 3 · staleclaims 1)은 `CYS_UI_DORMANT_LANE=1` 일 때만 돈다(`itDormant`/`testDormant` = `it.if`/`test.if`). | 1.1.8 은 그 기능들을 배선하지 않는다(휴면/미수용 결정) — 기본 레인에서 돌리면 「배선돼 있다」를 단언하는 시험이라 늘 적색. 삭제·무조건 skip 은 금지. | master#c6a9de68 UNW ⓐ · DECISIONS-PENDING-118 「수리 1차에서 나온 결정 필요」 UNW 행 | ⚠**단점 = 기본 CI 에서 82건 미실행**(그 기능 쪽 회귀를 아무도 안 본다). 1.1.9 에서 휴면-on CI 레인(env 켠 잡)을 만들고, 기능을 켜기로 하면 배선 + 레인 초록 · 버리기로 하면 ⓔ(박사님 게이트)로 시험 동반 제외. 지금 레인을 켜면 82건 전부 적색이 정상(2026-10-06 실측: 켠 레인 실패 집합 = 격리 전 실패 집합 · 차이 0). |
| B2 | 휴면 스위치 env — 데몬·CLI `CYS_ENABLE_TEAM_FLOW` · `CYS_ENABLE_AGY_LANE`(기본 off · src/lib.rs `dormant`) | 원작자 팀 흐름·agy 사용량 갈래를 1.1.8 에서 켜지 않는다(제거 아님). | master#c6a9de68 B(b) · D-TEAM · C4 | 켤지·지울지(ⓔ) 결정 시 B1 레인과 함께. |
