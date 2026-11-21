---
name: vibecoding-state
description: 상태관리(State Management)를 설계 전담하는 스킬 — State=기억(변수 아님) 판별·State=f(action) 원칙·Flux 단방향 규율·Context는 항상 마지막·페이지 상태 매핑. 핵심 명제 "AI는 상태의 경계를 정의하지 못한다"에 따라 상태 경계·전이 규칙 확정은 인간(doctor) DECISION block으로만 받고 에이전트는 전사만 한다. "상태관리 설계 / state management / 상태 경계 / Flux 설계 / 페이지 상태 매핑 / state-management.md 작성" 트리거, 또는 바이브코딩 파이프라인 layer 7(spec 직후) 단계로 발동.
disable-model-invocation: true
---

# vibecoding-state

> 수동 전용 하위 스킬(아래 `[[…]]` 중 Skill 목록에 없는 것 · disable-model-invocation)은 Skill 도구로 부르지 않는다 — 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read 해 따른다(사용자는 `/<이름>` 으로 직접 부를 수 있다).

바이브코딩 파이프라인의 **layer 7 — 상태관리 설계(필수 단계)**. spec 직후에 화면이
**언제(Trigger)·왜(Reason/guard)·어떻게(Transition)** 변하는지를 문서로 못박아, AI를
"즉흥 연주자"에서 "악보 읽는 연주자"로 바꾼다. 산출물 `/docs/state-management.md`(layer 7)
→ `/docs/page-state-mapping.md`(7.1) → `/docs/design/visual.md`(7.2).

> NLC 대원칙: **"AI는 상태 비슷한 코드는 만들지만, 상태의 경계는 정의하지 못한다."** 그래서
> 이 스킬은 코드를 짜지 않는다 — 인간이 고정할 경계·전이 규칙을 받아내고, 나머지 파생 설계만
> 자동화한다. 상태관리는 "AI가 하는 것"이 아니라 **"우리가 설계한 상태관리 위에서 AI가 연주하는 것"**이다.

---

## 1. 왜 상태관리가 필수인가 — State = A Component's Memory

- **State는 "변수"가 아니라 "기억"이다.** 기억은 곧 책임이며, 그 **책임의 경계**를 정하는 것이
  상태관리다. 변수는 값을 담지만, State는 "다음에 무슨 일이 일어나야 하는가"의 책임을 담는다.
- **State = f(User Action, System Process, Context).** 상태는 유스케이스(행동)의 함수다 —
  유스케이스=원인(cause), 상태관리=결과(effect). 그래서 상태관리는 **spec(유스케이스) 이후에만
  정확히 정의 가능**하다. spec 없이 상태를 먼저 잡으면 dead state가 생긴다.
- **상태관리가 없을 때의 5대 치명 문제**:
  1. 변경의 **이유를 모른다**(왜 이 값이 바뀌었는지 추적 불가).
  2. 기능 추가 시 **기존 기능이 랜덤하게 파손**된다(State 오염 — 가장 무서움).
  3. **디버깅이 불가능**하다 — '현상'만 있고 원인 경로가 없다.
  4. **AI가 멍청해진다** — 상태관리는 AI의 추론 좌표계다. 좌표계가 없으면 AI가 매번 헤맨다.
  5. 재사용이 아니라 **'재봉(매번 다시 꿰맴)'**이 된다.

## 2. State 판별법 — State vs Derived

**셋 중 하나라도 참이면 State, 계산으로 얻을 수 있으면 State가 아니다(derived).**

| 판별 질문 | 참이면 |
|---|---|
| 시간이 지나도 **유지**되어야 하는가? | State |
| 어떤 행동 **이후에도 남아** 있어야 하는가? | State |
| 다음 **렌더링에 영향**을 주는가? | State |
| 다른 값으로부터 **계산 가능**한가? | **derived (State 아님)** |

- derived 예: `totalPrice`(장바구니 항목의 합), `isMorning`(현재 시각의 함수),
  버튼 색(선택 상태의 함수). 이것들을 State로 잡으면 **파생/중복 진실**이 생겨 SOT가 깨진다.
- state_types는 `[persistent, derived]` 두 종만 존재한다(템플릿 계약). persistent만이 진짜
  기억이고 derived는 기억의 계산 결과다.

## 3. AI의 5대 상태관리 실패 (경계 문제) — 인간이 막아야 하는 것

AI는 상태 "코드"는 그럴듯하게 만들지만 아래 다섯 가지는 구조적으로 실패한다. 이것이 이 스킬이
인간 결정 게이트를 강제하는 이유다:

1. **경계(boundary) 정의 실패** — 어디까지가 이 컴포넌트의 기억인지 선을 못 긋는다.
2. **파생/중복 제거 실패** — derived로 충분한 값을 State로 이중 보관한다.
3. **비동기 레이스** — 동시 갱신·순서 의존을 통제하지 못한다.
4. **이벤트-상태 일관성 실패** — 이벤트가 상태를 남기는 규칙을 일관되게 유지 못한다.
5. **SOT 유지 실패** — props/local/context/API에 **중복된 진실을 동시에 허용**한다("하나로
   정리하려는 강박이 없다"). 진실의 원천이 여럿이면 어떤 게 참인지 아무도 모른다.

## 4. Flux — 기억의 법칙 (단방향 규율)

- **Flux = 단방향 흐름 `Action → Store → View`.** Store는 상태 변화가 일어나는 **유일한
  장소**이고, View는 **결과만 그린다(결정권 없음)**.
- Flux는 "패턴"이 아니라 **규율(rule)**이자 **"AI 통제 계약서"**다. AI 학습 데이터에는
  저품질 상태 코드가 많으므로, 단방향 규율은 **인간이 명령해야** 지켜진다.
- Store 인터페이스는 `{name, state, actions, scope}`로 명세한다(store_interface_required).
  각 action이 어떤 state를 어떤 조건(guard)에서 어떻게 전이시키는지 change table로 고정한다.

## 5. Context는 항상 마지막 — 기억의 배포망

- **Context = 상태 + Flux를 공유하는 메커니즘**(props drilling 제거·로직 중앙화) =
  "상태의 외부 배포 채널". 컴포넌트는 여전히 View만 담당한다.
- 단점: 단순 기능에는 오버엔지니어링. 복잡 화면(에디터·필터·채팅방)에는 반필수.
- **올바른 순서(불변)**: `1) spec → 2) State 정의 → 3) Flux(같은 문서) → 4) Context`.
  **Context는 항상 마지막이다.** 먼저 배포망부터 깔면 무엇을 배포할지 모른 채 구조만 커진다.
- 한 문장 요약: **State=기억의 내용, Flux=기억의 법칙, Context=기억의 배포망.**

## 6. 페이지 상태 매핑 (layer 7.1) — 어디서 일어나는가

- spec=**무엇을**, state-management=**어떻게 변하나**, page-state-mapping=**어디서 일어나나**.
- **핵심 명제: "Context Scope가 곧 Page Boundary."** 상태를 페이지·프로바이더 트리에 매핑하고
  scope를 분류한다. 논리상 state-management에 포함되나 시간상 동시 설계한다.
- rules: map_state_to_page · classify_scope · provider_tree_required ·
  state_dependency_required · page_implementation_boundary · **no_unmapped_state**(매핑 안 된
  상태 금지) · fds_alignment · ui_ux_alignment.

---

## 7. 인간 고정 영역 — 경계·전이 규칙은 DECISION block으로만 (헌법 6조)

> **이 스킬의 가장 중요한 게이트.** 상태 경계와 전이 규칙의 **결정권은 인간(doctor)에게**
> 있고, 에이전트는 **기록권(서기·scribe)만** 갖는다(헌법 6조 · §C11). 서기가 해석·보완·추론으로
> 결정 내용을 생성하면 silent hijacking(조용한 결정권 역도입)이며 6조 위반이다.

절차:

1. master는 상태 경계·전이 규칙의 **초안만 제안**한다(대행 불가 — 확정 권한 없음).
2. 인간(doctor)의 결정은 `[DECISION]` 라벨 메시지·issue form·커밋 trailer `Decision:` 중
   하나의 **DECISION block**으로만 서기에게 도달한다. 의무 필드: `decision_id`(DEC-YYYYMMDD-NNN)
   · `decider`(doctor) · `scope`(반영 대상 문서·조문) · `decision`(결정문 원문 verbatim) ·
   `effective_date`.
3. 서기는 결정 반영 **전에 반드시 검증**한다:
   ```
   python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_decision.py" validate --file <block> --record
   ```
   exit 0(통과)일 때만 `state-management.md`의 지정 scope에 결정문을 **그대로 전사**하고 출처
   (decision_id)를 병기한다. exit 2(의무 필드 결손·형식 위반)이면 **빈 필드를 추론으로 채우지
   말고 되물어야(grill)** 한다 — 응답이 없으면 "미반영+보고"가 폴백이지 "해석 반영"이 아니다.
4. 인간 결정 영역 문서(상태 명세)의 갱신은 **DECISION block 참조 없이는 불가**하다 — 참조 없는
   갱신 시도는 게이트가 차단한다(헌법 8조 doc-sync와 정합).

---

## 8. 절차 (layer 7 → 7.1 → 7.2)

1. **선행 확인** → 검증: `/docs/spec.md`(유스케이스)가 존재하는가. 없으면 상태 정의 불가 —
   spec부터. (State는 spec의 함수다.)
2. **State 정의** → 검증: 2절 판별법으로 persistent vs derived를 분류.
   `state_list{name, type, source, lifetime, storage}` 산출. **no_redundant_state**(derived를
   State로 이중 보관 금지) 위반 0.
3. **경계·전이 규칙 확정** → 검증: 7절 DECISION block 절차로 인간 결정 수령·`javis_decision.py
   validate` exit 0 · 전사 완료. change_table{trigger, condition/guard, effect} 고정.
4. **Flux 설계** → 검증: `Action→Store→View` 단방향 · `stores{name, state, actions, scope}`
   인터페이스 명세(store_interface_required). 역류(View가 상태 변경) 0.
5. **Context 배치(마지막)** → 검증: 복잡 화면에만 Context 도입 · 단순 기능 오버엔지니어링 회피.
6. **페이지 상태 매핑(7.1)** → 검증: provider tree + scope 분류 · **no_unmapped_state** ·
   "Context Scope = Page Boundary" 정합.
7. **Visual 반영(7.2)** → 검증: component_state_style_map — 각 상태가 어떤 시각 반응을 갖는지
   (state→style) 매핑, FDS 토큰 참조.

## 도구 연동

- `javis_decision.py validate` — 상태 경계·전이 규칙 인간 결정의 DECISION block 검증(§C11).
  의무 필드 결손 시 exit 2로 fail-closed 차단(추론 채우기 금지).
- `javis_vibecheck.py docs --level L4` — state-management.md의 존재 + YAML 계약 골격(SOT·layer·
  inheritance) 무결성을 evidence 게이트에 공급(상태·외부연동 작업은 최소 L4).
- 템플릿(수정 금지 계약 골격 상속): `assets/templates/8_state-management.md` ·
  `8-1_page-state-mapping.md` · `8-2_visual.md` — inheritance는 additive-only·override-prohibited.

## 출력 계약

`/docs/state-management.md` — `state_list · change_table · flux_diagrams · stores · mapping`.
`/docs/page-state-mapping.md` — provider tree · scope 분류. `/docs/design/visual.md` —
component_state_style_map · token_map. 모든 상태 경계·전이 규칙에는 근거 `decision_id` 병기.

## 연동 스킬

`[[vibecoding-tdd]]`(상태 변화 전후 테스트를 병행 정의) · `[[vibecoding-boundary]]`(외부 연동
상태의 경계) · `[[vibecoding-verify]]`(상태 오염 회귀 검증). 전 단계 spec은 appbuild/유스케이스
파이프라인 산출물.
