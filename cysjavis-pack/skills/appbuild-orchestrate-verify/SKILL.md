---
name: appbuild-orchestrate-verify
description: 만든 페인이 아닌 다른 페인이 완성물을 E2E로 직접 검증해 증거를 수집하는 하위 스킬 — 게이트 체크리스트를 들고 실행하고 문제는 고치지 말고 리포트만 한다(producer≠evaluator). appbuild-orchestrate 검증 관문. "E2E 검증 / 증거 검증 / 다른 페인 검증 / 체크리스트 실행" 맥락에서 발동.
disable-model-invocation: true
---

# appbuild-orchestrate-verify

> 수동 전용 하위 스킬(아래 `[[…]]` 중 Skill 목록에 없는 것 · disable-model-invocation)은 Skill 도구로 부르지 않는다 — 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read 해 따른다(사용자는 `/<이름>` 으로 직접 부를 수 있다).

**만든 에이전트가 아닌 다른 페인**(예: 코덱스)이 체크리스트를 들고 직접 실행해 검증한다 —
"다 됐다"는 말을 믿지 않고 증거를 만든다(`[[eval-driven-self-improvement]]`·
`[[verification-before-completion]]` 원칙).

## 절차

1. **체크리스트 로드** → 검증: `05-gate.md`의 기능별 수용·E2E 시나리오를 검증 항목으로.
2. **E2E 직접 실행** → 검증: 검증 페인이 브라우저/테스트를 직접 돌려(증거 생성) 각 수용 기준이
   실제로 충족되는지 확인. 언두·엣지·에러 시나리오 포함.
3. **리포트만(고치지 않음)** → 검증: 발견된 결함은 **직접 수정하지 않고** 리포트로 정리(모듈·
   증상·재현). 통과 항목은 게이트 행 증거 칸을 PASS 출력으로 채운다.
4. **메인에 보고** → 검증: 리포트를 메인 오케스트레이터에 전달(메인이 라우팅 판별).

## 철학

- **검증자≠생산자** — 객관성. 만든 페인이 자기 산출을 통과시키지 않게.
- **증거 기반** — 게이트 행은 실제 PASS 출력으로만 초록. 자기 주장 불인정.

## 출력 계약

findings 리포트(모듈·증상·재현) + 채워진 게이트 증거 칸. 상위 `[[appbuild-orchestrate]]`로
반환 → FAIL은 `[[appbuild-orchestrate-route]]`. 검증 페인이 직접 수정하면 규약 위반.

**증거 규약 (웹/앱 UI 매체 — 결함 지적 시 의무)**: 각 결함은 필수 증거 3종을 갖춘다 —
① 스크린샷 경로 · ② DOM ref · ③ 코드 추정 위치(**미상이면 '미상' 명시** — 침묵 금지).
verdict evidence 로 낼 때 위치 ref 규약은 `경로.png#ref_N`(스크린샷 경로 + DOM ref 앵커 융합),
코드 추정 위치는 별도 evidence 항목(`ref`=`파일:행` 또는 `미상`). 상세·예시 JSON =
`${CYS_PACK_DIR:-$HOME/.cys/pack}/round/EVIDENCE_CONVENTION.md`(§1 웹/앱 UI).
