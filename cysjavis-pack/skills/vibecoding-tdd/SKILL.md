---
name: vibecoding-tdd
description: 바이브코딩 TDD 전담 스킬 — 위치론(spec 후·plan 전 3대 논리)·문서 체인 5종(test-e2e→test-report→test-setup-orchestrator→tdd.md 법전→test.md→test-plan.md)·Red-Green-Refactor·FIRST·AAA·Test Pyramid 70/20/10·Smoke Test·integrity gate 연동. "TDD 설계 / 테스트 우선 / test.md 작성 / test-plan / 테스트 문서 체인 / 테스트 피라미드" 트리거, 또는 바이브코딩 파이프라인 layer 8~9(spec 직후) 단계로 발동.
disable-model-invocation: true
---

# vibecoding-tdd

> 수동 전용 하위 스킬(아래 `[[…]]` 중 Skill 목록에 없는 것 · disable-model-invocation)은 Skill 도구로 부르지 않는다 — 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read 해 따른다(사용자는 `/<이름>` 으로 직접 부를 수 있다).

바이브코딩 파이프라인의 **layer 8~9 — TDD 설계 단계**. 코드가 존재하기 **전에** "무엇이
올바른 동작인가(=테스트 조건)"를 먼저 문서화한다. 테스트는 검사가 아니라 **설계의 일부
(test-first)**다. 산출물: 문서 체인 5종 + `/docs/rules/tdd.md`(법전).

> NLC 명제: 테스트가 없으면 "돌아간다"는 말은 **증명이 아니라 느낌**이다. Regression Testing은
> "선택이 아니라 생명줄"이며, AI 수정이 의도치 않은 변화(특히 State 오염)를 일으키지 않았는지
> 자동 검증하는 안전장치다.

---

## 1. 위치론 — "Why after spec, before plan" (3대 논리)

- **공식 시점**: `spec.md` **직후** + `state-management.md` 병행 구간. 즉 "기능 정의 직후
  (what & how가 명확해진 시점)" + "구현 시작 전(before plan.md)".
- **3대 논리(verbatim)**:
  1. **spec 이후여야 한다** — 검증 기준은 spec에서 나온다. spec이 없으면 **무엇을 검증할지
     정의할 수 없다**.
  2. **plan 이전이어야 한다** — 테스트 없이 작업을 나누면(plan) **검증 불가능한 구조**가 만들어진다.
  3. **병행 효율성** — 상태 변화 전후의 테스트를 상태관리 설계와 **동시에 정의**할 수 있다.
- 본질: 코드 존재 전에 "올바르게 동작한다고 판단하는 기준"을 먼저 못박는다. 기준은 `spec.md`에서
  시작해 `test.md`로 확장된다.

## 2. 문서 체인 5종 (+법전 tdd.md)

파이프라인 순서대로:

1. **test-e2e.md** (layer 8, test-e2e) — parent=spec, next=test. rules: scenario_required ·
   **gwt_structure_required(Given-When-Then)** · coverage_required · ci_config_reference_only ·
   **no_code_inclusion**(코드 금지, 시나리오만).
2. **test-report.md** (layer 8.1, e2e-verification · Codex GPT-5 coder) — inputs=
   repomix-output.xml + package.json. rules: compare_structure/dependencies ·
   detect_missing/extra_folders · no_framework_assumption · no_example_code. 구조·의존성 대조로
   누락/잉여 폴더를 탐지.
3. **test-setup-orchestrator.md** (layer 8.0 · Codex GPT-5 coder) — ③단계(폴더·샘플 작성)
   직전까지 자동 설계·준비하는 런처. rules: select_runner_from_techstack · create_runner_config ·
   generate_sample_unit_test · generate_sample_e2e_test · summary_required ·
   reviewer_prompt_required · no_extra_frameworks.
4. **/docs/rules/tdd.md** — **"테스트 루프의 법전(Constitution)"**. 0-규칙 계층으로
   `/docs/rules/`에 UEPP/SCDP/RCMP와 함께 **전역 상속**된다. 아래 3~6절의 규범이 여기 담긴다.
   생성 시점은 Smoke Test 이전 또는 test.md 직전.
5. **test.md** (layer 8, tdd-root-spec · Codex GPT-5 coder) — TDD 중심 문서. "무엇을 어떻게
   테스트?". `unit_scenarios` · `e2e_scenarios` · `qa_plan{coverage, commands, failure_policy,
   report_path}`. = **검증 목표 정의서**.
6. **test-plan.md** (layer 8.1, test-plan) — "테스트 통과를 위해 무엇을 어떻게 구현?" =
   **구현 계획서(Implementation Bridge)**. rules: task_minimal_unit · apply_rgr_cycle.

- **대비**: test.md=검증 목표 정의서 / test-plan.md=목표 달성 구현 계획서. **실제 TDD 구현은
  이후 '구현 계획 도출(layer 9)'에서 실시**한다(문서화 단계에서 코드를 짜지 않는다).

## 3. Red → Green → Refactor (tdd.md 법전 핵심)

1. **Red** — 실패하는 테스트를 먼저 쓴다(아직 구현 없음 → 반드시 실패).
2. **Green** — 그 테스트를 통과시키는 **최소 코드**만 작성한다.
3. **Refactor** — 테스트가 초록인 채로 내부 구조를 정리한다(동작 불변).

## 4. FIRST — 좋은 테스트의 5속성

- **F**ast(빠름) · **I**ndependent(독립 — 테스트 간 순서 의존 0) · **R**epeatable(재현 가능 —
  어디서 돌려도 같은 결과) · **S**elf-validating(자기 검증 — pass/fail을 스스로 판정) ·
  **T**imely(제때 — 코드 전에 작성).

## 5. AAA · Test Pyramid · Outside-In

- **AAA(Arrange-Act-Assert)** — 준비 → 실행 → 단언의 3단 구조로 각 테스트를 작성.
- **Test Pyramid 70/20/10** — Unit **70%** · Integration **20%** · Acceptance(E2E) **10%**.
  아래가 넓고 위가 좁아야 빠르고 안정적이다(역피라미드=느리고 깨지기 쉬움).
- **Outside-In vs Inside-Out** — E2E 시나리오에서 안으로 파고들지, 단위에서 밖으로 조립할지
  선택. 안티패턴(테스트가 구현에 결합, 우연한 통과 등) 회피.
- 창시자: **Kent Beck**(TDD 원류).

## 6. Smoke Test — "실행되어 보고를 남기느냐"

- Smoke Test의 핵심은 성공/실패 자체가 아니라 **"실행되어 보고를 남길 수 있느냐"**다. 즉
  테스트 하네스가 살아 있어(runnable) 리포트를 뱉는지가 첫 관문이다.
- 환경 6단계: ①Playwright 설치 → ②config 생성 → ③`/tests/e2e`·`unit` 폴더 + Smoke Test →
  ④`npx playwright test` → ⑤test-report.md 기록 → ⑥TDD 루트(test.md).
- repomix: 테스트 실행 전 외부 AI에게 프로젝트를 이해시키는 정적 스냅샷(repomix-output.xml).
  `npx repomix --ignore "./**/*.md"`. Claude Code/Codex CLI가 폴더를 직접 열람 가능하면 불필요.

---

## 7. §C7.4 integrity gate 연동 — pre-run → gate 순서 (strict flow)

> 테스트가 "물지 않으면" 모든 게이트가 false-green이 된다. integrity gate는 테스트 스위트 자체가
> 실행 중에 변조(assertion 삭제·skip 삽입·self-mock)되지 않았는지를 **순서 강제**로 지킨다.

집행 순서(변경 시 계약 위반):

1. **pre-run 기록**(구현 run **전**) — 테스트 파일 git hash + assertion 정적 센서스(assert 수·
   skip 마커 수)를 기록한다:
   ```
   python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_vibecheck.py" integrity pre-run --project <dir>
   ```
2. 구현 run 실행.
3. **integrity gate**(기능 테스트보다 **먼저**) — 기록 대비 파일 변동·assertion 감소·skip 증가·
   self-mock 삽입을 검출한다. 검출 시 그 run은 **즉시 폐기·검역(결과 미계상)** — 기능 테스트로
   진행하지 않는다(fail-closed). **pre-run 기록 없이 gate 호출 시 exit 2(hard) fail-closed**:
   ```
   python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_vibecheck.py" integrity gate --project <dir>
   ```
4. integrity 통과 후에만 **기능 테스트** 실행.
5. 기능 테스트 후 **mutation 검산**(→ `[[vibecoding-verify]]` §C10.2).
6. 마지막으로 auditor trajectory 감사(derived-fix 분류).

exit code가 사실이다: 0 pass · 1 soft · 2 hard-fail. done 전이는 `javis_task set-status <id>
done --evidence "javis_vibecheck.py integrity gate → pass(exit 0)"` 형태로 인용된다(vibecheck는
독자 done 게이트가 아니라 evidence 공급자).

## 8. 절차

1. **선행 확인** → 검증: `/docs/spec.md` 존재(검증 기준의 원천). 없으면 TDD 착수 불가(1절 논리①).
2. **E2E 시나리오** → 검증: test-e2e.md — Given-When-Then 구조 · 코드 미포함.
3. **하네스 준비** → 검증: test-setup-orchestrator + test-report.md로 러너 선정·구조 대조 ·
   Smoke Test가 "실행되어 보고를 남기는지" 확인.
4. **법전 고정** → 검증: `/docs/rules/tdd.md`에 Red-Green-Refactor·FIRST·AAA·Pyramid 70/20/10
   규범 명문화 · 전역 상속.
5. **test.md(검증 목표)** → 검증: unit/e2e 시나리오 + qa_plan(coverage·commands·failure_policy).
6. **test-plan.md(구현 계획)** → 검증: task_minimal_unit · apply_rgr_cycle. (실제 구현은 layer 9.)
7. **integrity 배선** → 검증: 7절 pre-run→gate 순서를 CI에 상설 배치 · pre-run 없는 gate가
   hard-fail하는지 실측.

## 도구 연동

- `javis_vibecheck.py integrity pre-run|gate` — §C7.4 test-suite integrity strict flow(순서 강제).
- `javis_vibecheck.py docs --level L3` — test 문서 체인 존재 + YAML 계약 골격 무결성 evidence.
- 템플릿: `assets/templates/9_test.md` · `9-1_test-plan.md`(inheritance additive-only·
  override-prohibited 상속).

## 출력 계약

문서 체인 5종(test-e2e·test-report·test-setup-orchestrator·test·test-plan) + `/docs/rules/tdd.md`
법전. test.md=검증 목표 정의서, test-plan.md=구현 계획서로 역할 분리 유지. 각 테스트는 FIRST·AAA
준수, 분포는 Pyramid 70/20/10.

## 연동 스킬

`[[tdd]]`(Red-Green-Refactor 실전 구현 루프) · `[[verify]]`·`[[vibecoding-verify]]`(mutation 검산·
fresh verifier로 검증기 무결성 확보) · `[[vibecoding-state]]`(상태 변화 전후 테스트 병행 정의).
