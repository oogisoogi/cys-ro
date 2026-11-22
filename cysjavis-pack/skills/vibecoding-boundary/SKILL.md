---
name: vibecoding-boundary
description: 경계의 정의(Boundary Definition) 전담 스킬 — requirement 직후·PRD 전 필수 타이밍(4가지 이유)·SDK/API/Webhook 분류·인증/보안 선설계·/docs/external/서비스.md 산출·공식문서 우선+최근 3개월 블로그 교차검증. 핵심 명제 "requirement는 내가 할 일, external-integration은 내가 하지 않을 일(외부 의존)을 정의한다". "경계 정의 / 외부 연동 / external integration / SDK 연동 / API 경계 / 웹훅 / 인증 설계" 트리거, 또는 바이브코딩 파이프라인 requirement→PRD 사이 단계로 발동.
disable-model-invocation: true
---

# vibecoding-boundary

> 수동 전용 하위 스킬(아래 `[[…]]` 중 Skill 목록에 없는 것 · disable-model-invocation)은 Skill 도구로 부르지 않는다 — 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read 해 따른다(사용자는 `/<이름>` 으로 직접 부를 수 있다).

바이브코딩 파이프라인에서 **requirement 확정 직후·PRD 작성 전**에 외부 서비스 연동의 경계를
못박는 "환경·연동 정의 단계". 산출물 `/docs/external/서비스이름.md`.

> NLC 핵심 명제: **"설계에서 가장 중요한 것은 경계(boundary) — 내부(내가 만들 영역)와 외부
> (가져올 영역)를 나누는 선이다. requirement는 '내가 할 일'을 정의하고, external-integration은
> '내가 하지 않을 일(외부 의존)'을 정의한다. 이 둘이 모두 있어야 PRD가 과도하게 확장되지 않고
> 현실적 범위를 가진다."**

---

## 1. 타이밍이 왜 필수인가 — requirement 직후, PRD 전 (4가지 이유)

경계 정의를 PRD **이전**에 확정해야 하는 이유(verbatim):

1. **설계 왜곡 방지** — 결제를 직접 구현했다가 나중에 SDK가 필요해지면 중복 작업이 된다. 무엇을
   외부에 맡길지 먼저 정해야 안쪽을 헛설계하지 않는다.
2. **입출력 인터페이스(Interface Contract)를 미리 결정** — Userflow와 DB의 입출력 계약이 외부
   연동의 형태에 달려 있다. 경계가 없으면 이 계약을 확정할 수 없다.
3. **보안·인증을 가장 먼저 설계** — API Key / OAuth / Webhook secret / JWT는 **맨 처음** 설계해야
   한다. PRD 이후에 추가하면 **전체 재설계**가 된다.
4. **후속 5문서의 기술적 기반 SOT** — userflow · database · spec · state-management · test가 모두
   이 경계 정의를 기반으로 삼는다. "②단계(경계)가 늦어지면 userflow·DB 모두 재작업 = 현장에서
   가장 비싼 실수."

## 2. 3단계 경계표

| 단계 | 문서 | 답하는 질문 | 경계의 역할 |
|---|---|---|---|
| ① | `requirement.md` | 무엇을 만들 것인가? | 경계의 **필요성** |
| ② | `external-integration.md` | 무엇을 외부에서 가져올 것인가? | 경계의 **위치·형태** |
| ③ | `prd.md` 이후 | 안쪽을 어떻게 설계할 것인가? | 경계 **내부 구조** |

- requirement가 "내가 할 일"을, external-integration이 "내가 하지 않을 일"을 정의하고, 그 다음에야
  PRD가 경계 안쪽을 채운다. 이 순서가 PRD의 과잉 확장(스코프 크립)을 구조적으로 막는다.

## 3. SDK / API / Webhook 분류

외부 의존을 세 종류로 분류하고 각각의 계약을 명세한다(classify_sdk_api_webhook):

- **SDK** — 라이브러리로 코드에 임베드(예: 결제 SDK·분석 SDK). 버전·초기화·에러 표면을 계약화.
- **API** — 원격 호출(REST/GraphQL 등). "소유가 아니라 호출, 복사가 아니라 위임"이 API의 본질 —
  엔드포인트·인증·요청/응답 스키마·rate limit·실패 처리를 계약화.
- **Webhook** — 외부가 우리 쪽으로 밀어 넣는 이벤트. secret 검증·재시도·멱등성·수신 엔드포인트
  보안을 계약화.

## 4. 인증·보안 선설계

- **가장 먼저** 인증 방식을 확정한다: API Key / OAuth / Webhook secret / JWT 중 무엇을, 어떻게
  저장·회전·검증하는가(security_first_design).
- secret은 코드·문서에 하드코딩 금지 — env 템플릿(`/docs/environment/.env.template.md`)의 SOT로
  선언하고, 실제 값은 배급하지 않는다. (헌법 9조 인프라 강제와 정합: 에이전트 환경에 prod 쓰기
  자격증명 자체를 주지 않는다.)
- Interface Contract 필수(interface_contract_required): 각 외부 연동의 입력·출력·에러·타임아웃을
  계약으로 고정해 안쪽(userflow/DB/spec)이 이 계약에만 의존하게 한다.

## 5. 조사 규율 — 공식문서 우선 + 최근 3개월 블로그 교차검증

- 외부 서비스 연동 명세는 **딥리서치 + 출처 교차검증**으로 작성한다.
- **공식 문서를 1순위**로 삼고, 블로그·써드파티 자료는 **최근 3개월 이내**만 보조로 쓴다(오래된
  자료는 breaking change로 틀릴 위험). 공식 문서와 블로그가 충돌하면 공식 문서가 이긴다.
- 검색 먼저·회의적 교차검증·공통분모·대립 비교·결론 순서를 따른다(환각 0 — 근거 없는 단정 금지).

## 6. Level 라우팅과의 관계 (§C4)

- 외부 연동의 존재는 route-contract의 `external_integration` 신호를 **true**로 만든다 → 최소
  **L4**(판정표 행2). 배포 노출까지 겹치면 L5로 격상된다.
- 그래서 경계 정의는 단순히 문서 하나가 아니라 **Level 판정의 입력**이다 — 이 단계를 건너뛰면
  external_integration 신호가 unknown이 되고, unknown은 보수적으로 true(격상)로 간주된다(§C4.3).

## 절차

1. **경계 식별** → 검증: requirement.md가 확정됐는가(선행 필수). "내가 할 일 vs 외부에서 가져올
   일"을 목록화 · 외부 의존 후보 열거.
2. **분류** → 검증: 각 외부 의존을 SDK/API/Webhook으로 분류(classify_sdk_api_webhook).
3. **인증·보안 설계** → 검증: 인증 방식 확정 · secret은 env 템플릿 SOT로만 · Interface Contract
   (입출력·에러·타임아웃) 명세.
4. **딥리서치** → 검증: 공식 문서 1순위 + 최근 3개월 블로그 교차검증 · 출처 병기 · 충돌 시 공식
   우선.
5. **문서 산출** → 검증: `/docs/external/서비스이름.md` — 3_external-integration 템플릿의 계약
   골격(SOT·layer 2.95·inheritance) 상속 · goal=define_boundary_between_internal_and_external.
6. **Level 재판정** → 검증: external_integration=true 반영 → §C4 route-contract로 최소 L4 산출
   확인.

## 도구 연동

- `javis_vibecheck.py docs --level L4` — external-integration.md 존재 + YAML 계약 골격 무결성을
  evidence 게이트에 공급(외부 연동 작업은 최소 L4).
- `javis_vibecheck.py security` — 보안 Tier 1(secrets 스캔·.env가 .gitignore에 있는지)로 경계
  인증 설계의 누출을 검출.
- 템플릿: `assets/templates/3_external-integration.md`(parent=requirement.md, next=prd.md ·
  inheritance additive-only·override-prohibited 상속).

## 출력 계약

`/docs/external/서비스이름.md`(외부 의존 1건당 1문서) — SDK/API/Webhook 분류 · 인증 방식 ·
Interface Contract(입출력·에러·타임아웃) · secret의 env 템플릿 참조 · 출처(공식 문서 우선). 이
문서가 후속 5문서(userflow·database·spec·state-management·test)의 경계 SOT가 된다.

## 연동 스킬

`[[vibecoding-state]]`(외부 연동에서 오는 상태의 경계) · `[[vibecoding-tdd]]`(외부 연동 계약의
E2E 테스트) · `[[vibecoding-verify]]`(연동 실패·인증 우회 negative test). 전 단계 requirement,
다음 단계 PRD는 appbuild/기획 파이프라인 산출물.
