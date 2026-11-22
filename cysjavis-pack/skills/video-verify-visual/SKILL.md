---
name: video-verify-visual
description: 완성 영상의 시각 품질을 프레임 단위 비전 검수로 판정하는 하위 스킬 — 화면 밖 이탈·요소 겹침·아바타 미노출·잘린 텍스트·미적 결함을 프레임에서 잡는다. video-verify 1관문. "시각 검수 / 프레임 QA / 화면 이탈 점검 / 레이아웃 검증" 맥락에서 발동.
disable-model-invocation: true
---

# video-verify-visual

> 수동 전용 하위 스킬(아래 `[[…]]` 중 Skill 목록에 없는 것 · disable-model-invocation)은 Skill 도구로 부르지 않는다 — 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read 해 따른다(사용자는 `/<이름>` 으로 직접 부를 수 있다).

추출된 프레임을 비전으로 읽어 "보기에 결함"을 잡는다. 사람 편집자라면 절대 안 내보낼
프레임을 골라낸다.

## 점검 항목 (프레임별)

- **경계 이탈**: 텍스트·그래픽·아바타가 세이프 영역을 벗어나거나 잘렸는가.
- **겹침/가림**: 자막이 아바타 입을 가리거나 그래픽끼리 충돌하는가.
- **아바타 가시**: 모든 프레임에 아바타가 보이는가(좌측 카드 또는 둥근 크롭). 사라진 구간 탐지.
- **둥근 크롭 일관**: 코너 반경·드롭섀도가 구간마다 일관한가.
- **미적**: 정렬·여백·대비·가독성이 프로페셔널한가. 깨진 폰트·저해상도 에셋·빈 화면 탐지.
- **[서사 모드 — 프로젝트 루트 `entity_registry.json` 존재 시만] 일관성**: 프레임을 registry와 대조 —
  ① 캐릭터: 등장 인물이 static_features(얼굴·체형·헤어)와 일치하고 씬 내 dynamic(의상)이
    유지되는가(씬 간 변경은 scene_overrides에 근거가 있는가).
  ② 공간: 동일 space의 프레임 간 구조·가구 배치·원근이 불변인가.
  ③ 다인물: 인물 간 특징(의상·헤어)이 뒤섞이지 않는가.

## 절차

1. **프레임 로드** → 검증: `video-verify`가 추출한 프레임셋(간격 + 전환 지점)을 읽는다.
2. **비전 검수** → 검증: 각 프레임을 위 항목으로 판정. 문제 프레임은 타임코드·사유·
   썸네일로 기록.
3. **집계** → 검증: 결함 0이면 GO. 하나라도 있으면 NO_GO + 원인 단계(보통 `[[video-stitch]]`)
   지목. 단 일관성 결함의 원인 단계는 해당 프레임을 만든 `[[media-gen-image]]`(키프레임)
   또는 `[[media-gen-video]]`(클립)로 지목한다 — 기존 NO_GO 회귀 규약 그대로, 지목 대상만 정확히.

## 출력 계약

`{gate: "visual", verdict: GO|NO_GO, issues: [{timecode, type, evidence}]}` — 일관성 결함의
`type`은 `consistency_character | consistency_space | consistency_identity_mix`(기존 값 무변경). 상위
`[[video-verify]]`로 반환. NO_GO면 문제 프레임 근거를 첨부해 회송한다.

**증거 규약 (영상/음성 매체)**: issue 항목의 `{timecode, type, evidence}`는 영상/음성 증거 3종을
실어야 한다 — `timecode`=① 타임코드 구간(`MM:SS-MM:SS`), `evidence`=② 프레임 캡처 경로 + ③ 결함
서술. verdict evidence 로 승격 시 위치 ref 규약 `경로.mp4#t=MM:SS-MM:SS`. 이 포맷은 형제 관문
(`[[video-verify-audio-sync]]` 등 `{timecode,type,evidence}` 공유)에도 동일 적용. 상세 =
`${CYS_PACK_DIR:-$HOME/.cys/pack}/round/EVIDENCE_CONVENTION.md`(§1 영상/음성).
