---
name: video-stitch-captions
description: 나레이션 타임스탬프 기반으로 동기 자막을 영상에 번인하는 하위 스킬 — ElevenLabs 문자 정렬(timestamps.json)로 단어 단위 동기, 가독성·세이프영역·아바타 비가림을 보장한다. video-stitch 자막 관문. "자막 번인 / 동기 캡션 / 서브타이틀 / synced captions" 맥락에서 발동.
disable-model-invocation: true
---

# video-stitch-captions

> 수동 전용 하위 스킬(아래 `[[…]]` 중 Skill 목록에 없는 것 · disable-model-invocation)은 Skill 도구로 부르지 않는다 — 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read 해 따른다(사용자는 `/<이름>` 으로 직접 부를 수 있다).

말과 정확히 맞는 자막을 굽는다. 자막은 리텐션·접근성에 크고, 어긋나면 즉시 티가 난다.

## 절차

1. **타임스탬프 로드** → 검증: `audio/timestamps.json`(ElevenLabs 문자 단위 alignment)에서
   단어 그룹 경계를 만든다(문자→단어 묶음). ElevenLabs 를 안 쓴 경로면 `captions.json`
   (`caption-align` · 단어 단위) 또는 `cues.json`(`narrated-motion` · 문장 단위)을 시각 원천으로 쓴다.
2. **자막 청크** → 검증: 한 화면에 1~2줄, 너무 길지 않게 분절. 각 자막의 표시 시각을 해당
   발화 구간에 동기(±작은 오차).
3. **스타일·배치** → 검증: 가독성 높은 폰트·외곽선/배경, 세이프영역 안, **아바타·핵심
   그래픽을 가리지 않는 위치**. 색·크기 일관.
4. **사실성 주의** → 검증: 자막 텍스트는 검증 대본과 일치해야 한다 — 자막은 화면 텍스트라
   `[[video-verify-final-gate]]`의 사실성 대상이다. 대본에 없는 문구 임의 추가 금지.
5. **번인** → 검증: 자막을 영상에 합성(번인 또는 별도 트랙 정책에 따라). 동기·가독·비가림 확인.
   - ⚠ ffmpeg 빌드에 따라 굽기 필터(`subtitles`·`ass`·`drawtext`)가 없다(libass·freetype 없이 만든 판 ·
     예: 2026-11 맥 brew ffmpeg 9.0.1 = 셋 다 없음). 먼저 `ffmpeg -hide_banner -filters | grep -E " (subtitles|ass|drawtext) "`
     로 확인한다. 없으면 ① HTML 장면 안에서 자막을 그려 렌더하거나(narrated-motion 방식) ② 별도 자막
     트랙(mp4 `mov_text` · video-report-deck 방식)으로 넣는다.

## 출력 계약

자막이 적용된 트랙 + `final/captions.srt`(또는 동등) + `final/timeline.json`에 자막 in/out 기록.
상위 `[[video-stitch]]`로 반환. 비동기·가림·대본 불일치는 보고·수정.
