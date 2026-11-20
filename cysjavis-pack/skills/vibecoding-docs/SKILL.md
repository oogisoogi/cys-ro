---
name: vibecoding-docs
description: NLC "Spec/Doc driven 10단계" 28문서를 프로젝트에 인스턴스화하는 문서 파이프라인 스킬. assets/templates의 헌법(rules)~실행(implement) 28템플릿을 Level별 필수 세트로 깔고, 각 문서 생성 후 doc-critic(20년차 시니어 기준 확대해석·스코프크립 감사)을 거쳐, CLAUDE.md 브릿지 부트스트랩 설치와 세션 sanity check까지 수행한다. "문서 세트 만들어 / 헌법 문서 깔아줘 / spec 문서 생성 / 28문서 템플릿 / rules·root-sot 인스턴스화", 또는 [[vibecoding]] 2단계로 발동.
disable-model-invocation: true
---

# vibecoding-docs

NLC(자연어 코딩) "Spec/Doc driven 10단계"의 28문서를 프로젝트에 인스턴스화한다. 헌법(rules)부터
실행(implement)까지의 문서 계층을 한 벌로 깔고, 각 문서를 **적대적으로 감사**해 확대해석을 거른 뒤,
브릿지 부트스트랩으로 실제 작동시킨다. `[[vibecoding]]`의 2단계(문서 세트)를 담당한다.

> 자산: `assets/templates/`(28문서) · `assets/bootstrap/`(CLAUDE.md 브릿지·관제탑 AGENTS) ·
> `assets/agents/`(서브에이전트 6종) · `assets/design/`(시각 검증 토큰). 대응표·계약 골격은
> `assets/README.md`.
> 최상위 경고(NLC): **"md 문서를 만들어 놓는 것만으로는 아무 일도 자동으로 일어나지 않는다."**
> 반드시 브릿지 개조 + 규칙/설계 문서 변경 후 `ruler apply`를 해야 작동한다.

## Level별 필수 세트 (복잡도 라우팅 · 격상 허용·격하 금지)

Level은 `[[vibecoding]]`의 `javis_viberoute` 판정을 받는다. 여기서는 그 Level에 해당하는 템플릿만 깐다.

| Level | 필수 문서 | 성격 |
|---|---|---|
| L1-2 | 없음(헌법 계층은 선택) | 단순 요청은 문서 없이 직접 구현 |
| L3 | requirement(2-10) + spec(7) + test(9) | 무엇을 → 어떻게 작동 → 어떻게 검증 |
| L4 | L3 + state-management(8) + database(6) + external-integration(3) | 상태·데이터·외부 경계가 얽힐 때 |
| L5 | 풀 세트(28문서) | 헌법(1-1~2-4)+기획(2-5~2-10)+설계(3~8-2)+검증·실행(9~10-2) |

> 애매하면 상위 Level로 올린다(과소 발화가 안전). 격하는 금지(헌법 7조).

## 생성 순서 (헌법 계층 — 매우 중요)

```
AGENTS.md(WHO) → rules.md(WHAT MUST NEVER BREAK) → ruler/*.md(HOW) → _root-sot.md(WHY) → docs/rules/*.md(META)
```

**철학=Root SOT는 의도적으로 늦게 만든다.** @ruler보다 먼저 만들면 철학이 전술 규칙으로 오염된다
("전쟁관을 전투 전에 쓰는 군대는 반드시 망한다"). 설계 문서 파이프라인(3~10)은 경계 정의 순서를
따른다: requirement(무엇을 만들) → external-integration(무엇을 외부에서 · PRD 이전 필수) → prd →
fds·ui → userflow·ux → database → spec → state-management → page-state·visual → test → plan → implement.

## 인스턴스화 파이프라인

각 문서는 **생성 → doc-critic 감사 → (설계 문서면) ruler apply**의 3박자로 처리한다.

1. **인스턴스화**: 해당 Level 템플릿을 `assets/README.md` 대응표의 프로젝트 경로로 복사하고
   `[FILL: ...]` 앵커를 채운다. 각 템플릿의 YAML front-matter `sot`·`context`·`inheritance`
   (additive-only·override-prohibited·root-sot-priority·uepp/scdp/rcmp-auto)는 **수정 금지 영역**이다
   — 하위 문서는 상위를 override할 수 없고 추가만 한다.
2. **doc-critic 감사**(아래 §doc-critic): 방금 만든 문서가 상위 문서를 넘어 임의 기능을 부풀렸는지
   적대적으로 감사한다.
3. **ruler apply**: 규칙·헌법·설계 문서를 만들거나 고칠 때마다 실행한다. **코드·env 변경만으론
   불필요**(별개 층위).

## doc-critic 절차 (prd-critic의 일반화 · 20년차 시니어 기준)

NLC의 `prd-critic`(PRD가 requirement를 넘어 기능을 부풀렸는지 감사하는 별도 비판 문서)을 **모든 설계
문서에 일반화**한다. 각 문서 생성 직후, 이종모델(codex·agy) 1턴으로 상위 문서 대비 확대해석을 감사한다.

- **감사 렌즈(verbatim 원칙)**: "언급되지 않은 내용 확대해석 없는지 엄밀 검토 · 쓸데없이 추가 개발
  절대 금지 · **20년차 이상 최고급 시니어 관점으로 최대한 깐깐하게** · 빠른 프로젝트 완성 최우선."
- **checks**: `scope_diff`(상위 문서에 없는 범위 추가) · `missing_items`(상위가 요구했으나 누락) ·
  `mapping_error`(feature↔entity/state/test 매핑 붕괴) · `annotation_missing` · `techstack_mismatch` ·
  `env_gap`.
- **rules**: `add_nothing_unless_specified` · `no_feature_without_entity` ·
  `integration_follows_external_spec` · `techstack_must_match_requirement`.
- **output**: `{summary, findings[{id, type, where, description, severity(blocker|major|minor), fix}],
  patches, validation_result{ok, counts}}`. blocker/major finding이 남으면 그 문서는 미완이다.
- precision pruning: 불필요한 수식어·서사형·감성 문구를 제거한다("코드 오염=오류·할루시네이션 원천").

> 서브에이전트는 `assets/agents/`의 `usecase-writer`·`common-task-planner`·`plan-writer`·
> `design-agent`·`implementer`·`design-reviewer`를 프로젝트 에이전트 경로로 복사해 배치한다.

## 부트스트랩 (CLAUDE.md 브릿지 설치 · 필수 시행)

문서만으론 AI가 읽지 않는다("AI는 파일 시스템을 스스로 훑지 않는다"). 브릿지 개조가 없으면 지금까지
만든 모든 md 작업이 무의미하다.

1. **브릿지 로더**: `assets/bootstrap/CLAUDE.md.template`를 프로젝트 `./CLAUDE.md`로 두고 부트스트랩
   로더의 `@import`를 확인한다 — Agent Identity(@AGENT.md) → Global Rules(@rules.md) → Root
   SOT(@docs/_root-sot.md) → Meta-Constitution(@docs/rules/uepp·scdp·rcmp) → (선택) Always-On
   ruler. "항상 적용해도 되는 것만" Always-On 블록에 넣는다.
2. **관제탑 AGENTS.md**: `assets/bootstrap/AGENTS_MASTER_PROMPT.md`를 실행해 루트 `./AGENTS.md`
   (규칙 내용이 아니라 **규칙을 로드하는 절차**만 담는 Context Map)를 생성한다.
3. **시각 검증 토큰**: `assets/design/*.template`를 `context/`로 두고 `design-reviewer`가 대조하게 한다.
4. **ruler apply**: 부트스트랩 추가 직후 1회 실행. 이후 규칙·헌법·설계 문서 변경마다 재실행.

## 세션 sanity check (매 새 세션 첫 턴 · 필수)

브릿지가 실제로 로드됐는지 확인하는 의식(ritual)이다. **"자동"은 의미 자동이지 로딩 자동이 아니다** —
확인 없이 진행하면 '규칙 미적용 세션' 참사가 난다.

- 첫 턴에 **"지금 로드된 규칙/메모리 요약을 말해봐"** 로 로드 여부를 검증한다.
- 세션·문서·툴이 바뀌면 상위 문서(AGENT/rules/_root-sot/docs/rules)를 재주입한다.
- AI 판단이 이상하면 Root SOT 재주입, 구조가 헷갈리면 RCMP 재확인.

## 완료 게이트 — `javis_vibecheck docs`

문서 세트가 완성되면 `python3 $PACK/bin/javis_vibecheck.py docs`로 문서체인 무결성(존재·상속·
sot 골격)을 검증한다. 이 게이트는 **별도 완료 게이트가 아니라 `[[vibecoding]]`의 `javis_task`
단일 완료 게이트에 넣을 evidence 공급자**다.

## 출력 계약

인스턴스화된 Level별 문서 세트(프로젝트 경로) + doc-critic finding 0(blocker/major) +
설치된 CLAUDE.md 브릿지·관제탑 AGENTS.md + `ruler apply` 실행 확인 + sanity check 통과 +
`javis_vibecheck docs` 증거. `[[vibecoding]]`으로 반환 → 계획 리뷰 게이트.
