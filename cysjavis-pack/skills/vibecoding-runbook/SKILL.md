---
name: vibecoding-runbook
description: NLC 시행령(ruler/*.md) 10종을 상황에 맞춰 라우팅하는 런북 스킬. 코드 변경 유형(coding·refactor·hotfix·migration·test-only·doc-sync·state·security·integration·release)별로 Applicability→Mandatory Context→Output Contract→규칙→Verification→Checklist→Stop Conditions 골격의 실행 런북을 assets/runbooks/에서 고른다. "이 변경 어떻게 진행 / 리팩터 런북 / 핫픽스 절차 / 마이그레이션 규칙 / 이건 rules인가 ruler인가", 또는 [[vibecoding]] 구현 단계에서 작업 유형별 시행령이 필요할 때 발동.
disable-model-invocation: true
---

# vibecoding-runbook

NLC의 **시행령(@ruler/*.md · HOW-NOW)** 10종을 상황에 맞춰 고른다. 헌법(rules)이 "무엇이 깨지면
안 되는가"라면 런북은 "이번 작업을 **어떻게 수행하는가**"다 — 선택 적용이되, 착수한 뒤에는 그
런북의 Stop Conditions와 Non-Negotiable을 절대 위반하지 않는다.

> 런북 자산: `assets/runbooks/`(coding·refactor·hotfix·migration·test-only·doc-sync·state·
> security·integration·release, 10파일). 각 파일은 공통 7골격
> (Applicability→Mandatory Context→Output Contract→Rules→Verification→Checklist→Stop Conditions).
> `[[vibecoding]]`의 구현 단계에서 작업 유형이 정해지면 해당 런북을 로드해 집행한다.

## rules vs ruler 결정트리 (3문항 · 넣을 곳을 먼저 가른다)

새 규칙을 어디에 둘지부터 판단한다 — 헌법(rules.md)에 넣을지, 런북(ruler)에 넣을지.

1. **항상 지켜야 하는가?**
2. **작업 종류가 바뀌어도 유효한가?**
3. **위반 시 즉시 중단인가?**

→ YES가 2개 이상 = `rules.md`(헌법). NO가 2개 이상 = `ruler/*.md`(런북).
**@ruler 절대 금지**: 윤리·안전·품질 하한선·테스트 의무·권한 제한은 런북에 넣지 않는다("작전이
헌법을 무력화 금지"). `.ruler/`(엔진 기록실)와 `@ruler`(사람의 호출 스위치)는 다르다 — 규칙 내용은
`ruler/`에, `.ruler/`엔 넣지 않는다.

## 상황 → 런북 라우팅 표

| 상황 | 런북 | 핵심 Non-Negotiable |
|---|---|---|
| 일반 코드 변경(버그·기능·성능·chore) | `coding.md` | Breaking change는 정책 없이 금지 |
| 행동 불변 구조/결합도만 손봄 | `refactor.md` | Behavior Equivalence(확신 못하면 중단) |
| 비상 프로덕션 장애 대응 | `hotfix.md` | rollback plan 없는 hotfix = 실패 |
| 데이터/스키마/계약 비가역 이동 | `migration.md` | 백업·롤백 없이 파괴 금지 |
| 프로덕션 코드 미변경, 테스트만 | `test-only.md` | 프로덕션 수정·assertion 약화 금지 |
| 코드 변경에 문서 동반 갱신 | `doc-sync.md` | 문서 갱신 불가면 코드 변경도 미완 |
| 상태 도입·전이 규칙 집행 | `state.md` | Single SOT·No Shadow State·Unidirectional Flux |
| 로그인·DB·외부연동·민감정보 | `security.md` | 특권 연산 서버사이드 only·deny by default |
| 외부 API/SDK/Webhook | `integration.md` | 핵심 도메인을 외부에 직접 결합 금지(boundary 래핑) |
| 배포·CI/CD·버전·롤백 | `release.md` | 배포는 성공해도 롤백은 항상 가능 |

**종속 관계**: `integration`은 `security`에 종속, `release`는 `security`·`integration`에 종속.
보안·연동이 걸리면 그 런북을 먼저 집행한다.

## 라우팅 규칙

- **한 작업 = 한 Change Type**: 코드 변경이면 `coding.md`의 Change Type을 먼저 확정한다
  (bugfix|feature|refactor|performance|security|chore). refactor 의도인데 행동을 바꾸려 하면
  `coding.md`로 전환한다("이왕 고치는 김에 리팩토링"이 변경 범위 폭발·2차 장애의 출발).
- **state.md ≠ state-management.md**: 런북 `state.md`는 집행 매뉴얼(HOW, 시작 즉시 존재)이고,
  `/docs/state-management.md`는 설계 SOT(WHAT, spec 이후)다 — **대체 불가**.
- **migration은 개선이 아니라 이동**: 마이그레이션 런북엔 HOW가 아니라 **HOW를 판단하는 RULE만**
  담는다(구체 작업 지시를 넣으면 구조가 깨진다).
- 런북은 헌법·상위 문서를 상속만 하고 override하지 않는다(additive-only).

## 출력 계약

선택된 런북 1개(+종속 런북) 로드 · 그 런북의 Output Contract를 채운 산출물 · Verification의 pass/fail
신호 · Stop Conditions 미저촉 확인. `[[vibecoding]]`으로 반환 → vibecheck 증거 수집.
