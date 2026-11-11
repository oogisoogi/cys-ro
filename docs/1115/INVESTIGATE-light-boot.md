# 조사 ⑤ — 가벼운 시작(기본 부트가 띄우는 CSO·일꾼 좌석) · TICKET=cysr-1115-smalls

> 조사만(코드 수정 0) · 2026-11-11 · 기준 커밋 270e3e21(v1.1.14) · 근거는 모두 `파일:줄` · **관측** = 코드에서 확인 / **추정** = 코드 구조에서 미루어 본 것.
> 읽기 범위: `src/bin/cys.rs` · `src/bin/cysd/{boot_supervisor,schedule,alert_route,cycle_jobs,governance}.rs` · `cysjavis-pack/bin/{javis_bootstrap,javis_orchestra,javis_formation}.py` · 훅 `role-bootstrap*.sh`. 근거 수집은 읽기 전용 조사 에이전트 1기 + 핵심 줄 직접 대조(BOOT_PLAN·REQUIRED_ROLES).

## 1. 어디서 띄우나 (관측)
- **기본 함대 = master + CSO 1 + 일꾼 1**(리뷰어는 기본 0 · 2026-09-10 결정). 같은 표가 세 곳에 있다:
  Rust `BOOT_PLAN`(`src/bin/cys.rs:12569-12572`) · 파이썬 `REQUIRED_ROLES`(`javis_orchestra.py:138`)·`BOOT_PLAN`(`:167-170` · 두 언어 행 단위 대조 시험 H-PRED-7) · 편성기 `REQUIRED_ROLES`(`javis_formation.py:106`).
- **흐름**: 사용자가 마스터 선언 → 훅 `role-bootstrap.sh` → 레거시 본체가 `cys boot-intent`(`role-bootstrap-legacy.sh:965`) → 데몬 `boot_supervisor` 가 `javis_bootstrap.py` 실행(`boot_supervisor.rs:1792`) → 결손 판정(`javis_bootstrap.py:3911`) → `cys boot --json`(`:3942-3949`) 이 `BOOT_PLAN` 을 돌며 CSO·일꾼 기동(`cys.rs:14588·14646`) → `check` 로 생존 확인(`javis_bootstrap.py:4066`).
- **되살리는 층이 따로 있다**: 데몬 일정 `formation-heartbeat`(10분 · `schedule.rs:395-398`) 가 `javis_formation.py ensure` 로 master·CSO·일꾼을 다시 세운다(`javis_formation.py:2025-2060`).
- **이미 있는 노브**: `CYS_FORMATION_EXTERNAL_ROLES`(편성에서 역할 제외 · `javis_formation.py:423·431-436`) · `CYS_MAX_ACTIVE_WORKERS`(동시 상한 · 기본 무제한 · `state.rs:3787-3795`). **부트 구성 자체를 줄이는 노브는 없다**(검색: `no-cso`·`CYS_NO_CSO`·`WORKER_COUNT`·`CYS_BOOT_ROLES`·`CYS_BOOT_PLAN`·`CYS_FLEET` → 0건).

## 2. 끄면 무엇이 안 되나 (관측)
- **CSO**: ① `check` 가 CSO 를 의무로 요구 — 없으면 부트 실패(`javis_orchestra.py:1172-1260` · 부트 exit 4 `javis_bootstrap.py:3979-3981`) ② 경보가 「no_cso」로 **보류**된다(버리지 않고 CSO 착석 때 배달 · `alert_route.rs:1181-1189`) ③ 컨텍스트 순환(cycle-agent) 집행 주체가 CSO(`cycle_jobs.rs:3-4`) — 없으면 순환이 멈춘다(지침 「CSO 부재 시 clear 보류」 `MASTER_DIRECTIVE.md:660-661`) ④ 말로 부서 만들기 틱이 CSO 신원으로 돈다(`governance.rs:446-467` · `javis_org.py:114`).
- **일꾼**: 위임 티켓(`task-prompt`)의 생존 게이트가 막는다 — 일꾼이 없으면 티켓을 안 내고 「기동 후 재실행」 안내 + exit 1(`javis_orchestra.py:2078-2082`).
- **첫 지시 때 자동 기동은 없다**(관측) — 리뷰어 `--spawn`·`worker-fresh-*` 일정만 「필요할 때」 뜬다(`javis_orchestra.py:1375-1381·2068-2071`).

## 3. 비용 근거 (관측 + 공백)
- 브리프의 「회차당 0.6~1.4M 토큰」은 **저장소에 기록이 없다**(검색 `1.4M`·`0.6`·`부트 비용`·`토큰` → 부트 토큰 실측 0건 · `docs/117/PRECUT-117.md:102` 「토큰 소모 계수 = 실측 없음」). 저장소의 유일한 비용 근거 = 리뷰어 상시 점유 「86% weekly limit」 화면 관측 1건(`javis_orchestra.py:1369-1370`).
- ∴ 좌석별(CSO·일꾼) 몫은 **미측정**. 결정 전 1회 측정 권고: 같은 계정에서 부트 전후 `cys usage-accounts --json` 대조 + 좌석별 jsonl 의 첫 응답까지 usage 합.

## 4. 선택지
| | 내용 | 장점 | 단점 |
|---|---|---|---|
| A 기본 유지 | 지금 그대로 | 변경 0 · 첫 지시가 곧바로 일꾼에게 간다 | 일을 안 줘도 두 좌석 각성 비용(미측정)이 매 회차 든다 |
| B 첫 지시 때 지연 기동 | 부트는 master(+CSO)만 · 첫 `task-prompt` 때 일꾼을 띄운다 | 일 없는 회차의 일꾼 비용 0 | 바꿀 곳 4층(BOOT_PLAN 두 언어 · `check` 의무 · formation 10분 심박 · task-prompt 게이트) — 하나만 바꾸면 다른 층이 되살린다 · 첫 지시가 기동 시간(수십 초)만큼 늦다 |
| C 설정 노브 | 「가벼운 시작」 켜면 B, 기본은 A | 기존 사용자 무변화 · 되돌리기 쉬움 | 왕초보는 노브를 모른다 → 실효가 작다 · 갈래 2개를 시험해야 한다 |

## 5. 권고 (확신도 중)
**측정 1회 → B 를 일꾼에만 적용**(CSO 는 유지). 근거: CSO 는 경보·순환·부서 틱의 집행자라 빼면 「조용히 멈추는」 기능이 셋이고(2절), 일꾼은 빠져도 막히는 곳이 task-prompt 게이트 한 곳이라 그 자리에서 띄우면 된다. 단점: 측정 결과 CSO 몫이 크면 이 권고는 절감이 작다 — 그래서 측정이 먼저다.
**왕초보 화면 변화(B 적용 시)**: 마스터 선언 뒤 지금은 창이 셋(마스터·CSO·일꾼) 뜬다 → 둘(마스터·CSO)만 뜬다. 첫 일을 맡기면 「일꾼을 부르는 중입니다(30초쯤)」 한 줄 뒤 일꾼 창이 열린다.
