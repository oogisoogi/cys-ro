---
name: vibecoding-verify
description: 구현 검증 전담 스킬 — 6단계 검증 체크리스트(UX·Test·App·Stress·Code·Implementation)·fresh verifier 서브에이전트(구현자≠검증자·blackbox)·시각 self-loop 6단계(수정→실행→스크린샷→디자인문서 대조→불일치·콘솔에러→재검증)·design-reviewer 에이전트·mutation 검산(operator 5종 N=5, vacuous pass 시 검증기 수리). "검증 / verify / 시각 검증 / 디자인 리뷰 / mutation 테스트 / 검증기 무결성 / 회귀 검증" 트리거, 또는 구현 done 전 검증 게이트로 발동.
disable-model-invocation: true
---

# vibecoding-verify

> 수동 전용 하위 스킬(아래 `[[…]]` 중 Skill 목록에 없는 것 · disable-model-invocation)은 Skill 도구로 부르지 않는다 — 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read 해 따른다(사용자는 `/<이름>` 으로 직접 부를 수 있다).

구현이 "실제로 요구대로 동작하는가"를 **구현자와 분리된 검증자**가 확인하는 게이트. 코드가
초록불이어도 검증기 자체가 공허 통과(vacuous pass)하면 모든 게이트가 false-green이 된다 —
이 스킬은 그 검증기 자체의 무결성까지 검산한다.

> 헌법 2조: **"검증 불가 = 미완."** 헌법 3조: **구현자 ≠ 검증자**(자기채점 금지).
> producer≠evaluator를 지키지 못하면 "최고"는 측정 없는 주장일 뿐이다.

---

## 1. 6단계 검증 체크리스트 (Claude Code 6 dimension)

구현 결과를 여섯 축으로 훑는다(어느 하나도 생략 불가):

1. **UX** — 사용자 흐름이 의도대로 작동하는가. 실제 시나리오를 끝까지 밟았는가(단위 테스트가
   아니라 흐름).
2. **Test** — 테스트가 존재하고 통과하는가. 그리고 그 테스트가 **의미 있는 것을 검증**하는가
   (→ 5절 mutation 검산으로 확인).
3. **App** — 앱이 실제로 뜨고 핵심 기능이 살아 있는가(`npm run dev` → 핵심 경로 구동).
4. **Stress** — 경계·부하·엣지 케이스에서 무너지지 않는가(빈 입력·대량 입력·동시 요청·오류 주입).
5. **Code** — 코드 품질: 의존성/결합도/변경 파급(Ripple Effect), 데드코드, 오류 밀도, 역호환.
6. **Implementation** — 구현이 spec·plan·test 문서와 **100% 일치**하는가(수행 안 한 것은 주석
   처리되어 있고, 문서와 코드 사이 표류가 0인가).

## 2. fresh verifier 서브에이전트 규율 (구현자 ≠ 검증자)

- 검증자는 구현자와 **다른 노드**여야 한다(자기채점 편향 차단). 자비스에서 실행=워커 일원화,
  검증=이종모델(agy/Gemini·codex/GPT)로 **모델 분담**한다.
- **전체 히스토리 없이 blackbox 검증**: 검증자에게 구현 과정의 대화·근거를 통째로 주지 않는다.
  "무엇을 만들었어야 하는가(spec·test)"와 "무엇이 나왔는가(산출물)"만 주고 판정하게 한다 —
  구현자의 자기변호 서사가 검증자를 오염시키는 것을 막는다.
- verdict 타입 계약: 검증자 판정은 산문 점수가 아니라 `ACCEPT | REVISE | BLOCK | ESCALATE` +
  `evidence:file:line`로 출력한다(score 0-100 금지 — 다수결·reward-hack 차단). 불일치는 다수결이
  아니라 **master 독립 재유도**로 판정한다.

## 3. 시각 self-loop 6단계 (UI 구현 검증)

UI를 건드린 변경은 스크린샷으로 눈으로 확인하는 자율 루프를 돈다:

1. **수정** — 코드 변경 반영.
2. **실행** — 대상 라우트로 navigate(앱 구동).
3. **스크린샷** — 다중 viewport(mobile/tablet/desktop) 캡처.
4. **디자인 문서 대조** — `context/design-principles.md` · `context/style-guide.md`
   (+ `/docs/rules/fds.md` · `/docs/design/visual.md`)와 비교.
5. **불일치·콘솔에러 식별** — 레이아웃 깨짐·접근성 위반(WCAG 2.1 AA)·콘솔 error/warning 수집.
6. **수정·재검증** — 발견 항목 교정 후 1~5 재수행.

- **도구 선택**: Playwright MCP(~30도구 토큰 비용)보다 **skill + CLI 스크립트 우선**. MCP는
  꼭 필요할 때만.

## 4. design-reviewer 에이전트 호출

시각 검증은 전담 서브에이전트로 위임할 수 있다:

- 정의 파일: `assets/agents/design-reviewer.md`(model: sonnet). 위 3절 6단계 루프를 자율 수행하고
  등급 리포트를 낸다.
- 리포트 스키마: `verdict: PASS|REVISE|BLOCK` + `findings[{id, category(layout|accessibility|
  console|token), viewport, severity, evidence, fix}]` + `grade: A|B|C|D`.
- rules: **reviewer_not_implementer**(코드를 직접 고치지 않고 리포트만 — 수정은 implementer 재위임)
  · **evidence_required**(모든 finding에 스크린샷/콘솔 근거) · **no_score_only**(산문 점수 금지).

---

## 5. mutation 검산 — 검증기 자체가 무는지 (§C10.2)

> **C10.1 문제**: 검증기가 물지 않으면(vacuous pass) 모든 게이트가 false-green이다. mutation
> 테스트는 "일부러 코드를 망가뜨렸을 때 테스트가 잡아내는가"로 **검증기의 유효성**을 검산한다.

- 기능 테스트 pass **후**, 검증 대상 핵심 경로에 mutation **N=5**개를 주입한다. **테스트 스위트가
  최소 1개 이상 fail해야 검증기 유효**로 판정한다. **전 mutation 생존(테스트 전부 pass) =
  검증기 무효(공허 통과)** → 해당 검증 결과 **전체 기각 + 검증기 수리 티켓 발행**.
- **mutation operator 최소 지원 셋(사전등록 고정 — 임의 조작 방지)**: 아래 5종. 사전등록 record
  **`PR-MUTOPS-001`**에 봉인되어 있고, N개 주입은 무작위가 아니라 **사전등록된 분배**로
  선택·기록한다(재현 가능):
  1. **비교 연산자 반전** (`>`↔`<` · `>=`↔`<=` · `==`↔`!=`)
  2. **산술 연산자 교체** (`+`↔`-` · `*`↔`/`)
  3. **논리 연산자 교체** (`and`↔`or`)
  4. **경계값 ±1** (off-by-one 주입)
  5. **반환값 상수화** (함수 반환을 고정 상수로 치환)
- operator 셋 확장은 계약 개정으로만 가능하다. 사전등록 record 무결성 확인:
  ```
  python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_prereg.py" verify PR-MUTOPS-001
  ```
  exit 0(봉인 해시 일치)일 때만 그 operator 분배가 유효하다 — 변조 시 exit 1(비교 불가).
- **negative test 의무**: 각 게이트는 "막아야 할 입력을 실제로 막는지"의 **적대 입력 케이스를
  최소 1개** 동반한다(막을 대상이 없는 게이트 = 미완).

## 6. 전체 검증 실행 순서 (§C7.4 strict flow와 접합)

`[[vibecoding-tdd]]`의 integrity strict flow에 이어:

1. integrity gate 통과(테스트 스위트 무변조 확인) — `javis_vibecheck.py integrity gate`.
2. **기능 테스트** 실행(6단계 체크리스트 2·3축).
3. **mutation 검산**(5절 · N=5) — 검증기 유효 판정. 무효 시 여기서 중단·수리 티켓.
4. **시각 self-loop / design-reviewer**(UI 변경 시 · 3·4절).
5. **auditor trajectory 감사** — derived-fix(검색된 답 복제) 분리 측정.
6. fresh verifier(이종모델)의 verdict(ACCEPT/REVISE/BLOCK/ESCALATE) 수령.

## 절차

1. **검증 계획** → 검증: 6단계 체크리스트 중 이 변경에 해당하는 축 식별(UI 변경이면 시각 루프
   포함, 로직 변경이면 mutation 검산 필수).
2. **fresh verifier 준비** → 검증: 구현자와 다른 노드 · blackbox 입력(spec+산출물만) 구성.
3. **기능 검증** → 검증: 테스트 통과 + 앱 실제 구동(App/UX/Stress).
4. **mutation 검산** → 검증: `javis_prereg.py verify PR-MUTOPS-001` exit 0 · N=5 주입 · 최소 1
   fail 확인. 전 생존 시 검증기 수리 티켓 발행 후 중단.
5. **시각 검증** → 검증: design-reviewer 리포트 verdict + evidence(스크린샷) · 콘솔 에러 0.
6. **verdict 집계** → 검증: 이종모델 판정을 evidence와 함께 보존 · 불일치는 master 독립 재유도.

## 도구 연동

- `javis_prereg.py verify PR-MUTOPS-001` — mutation operator 5종 사전등록 record 무결성 대조.
- `javis_vibecheck.py integrity gate` — 검증 실행 전 테스트 스위트 무변조 확인(선행 게이트).
- `assets/agents/design-reviewer.md` — 시각 검증 서브에이전트.
- 시각 문서: `context/design-principles.md` · `context/style-guide.md`(`assets/design/*.template`
  에서 인스턴스화).

## 출력 계약

검증 리포트: 6단계 축별 결과 + mutation 검산 결과(operator 분배·생존/사망 수·검증기 유효 여부) +
시각 리포트(verdict·grade·findings) + 이종모델 verdict(ACCEPT/REVISE/BLOCK/ESCALATE + evidence).
done 전이는 이 산출물을 `javis_task ... done --evidence`로 인용한다(검증 불가=미완).

## 연동 스킬

`[[verify]]`(범용 end-to-end 검증 루프) · `[[eval-driven-self-improvement]]`(producer≠evaluator·
LOCKED ref launcher 원칙) · `[[vibecoding-tdd]]`(integrity strict flow 선행) ·
`[[vibecoding-state]]`(상태 오염 회귀 검증).
