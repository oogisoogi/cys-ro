---
name: video-verify-final-gate
description: 출고 직전 최종 관문 하위 스킬 — 화면 자막·텍스트의 사실성을 대본 사실대장과 재대조하고, 앞 3관문 결과를 종합해 업로드 go/no-go를 판정한다. video-verify 4관문·출고 게이트. "최종 검증 / 사실성 재확인 / 업로드 승인 / go no-go" 맥락에서 발동.
disable-model-invocation: true
---

# video-verify-final-gate

> 수동 전용 하위 스킬(아래 `[[…]]` 중 Skill 목록에 없는 것 · disable-model-invocation)은 Skill 도구로 부르지 않는다 — 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read 해 따른다(사용자는 `/<이름>` 으로 직접 부를 수 있다).

마지막 관문. 두 가지를 본다: (1) **화면에 뜬 글자**가 사실인가 (2) 4관문 종합 판정.
영상 자막·차트 수치는 음성과 별개로 화면에 박히므로, 여기서 사실성을 한 번 더 막는다.

## 점검 항목

- **화면 텍스트 사실성**: 자막·키네틱 텍스트·차트 수치·고유명사를 프레임에서 읽어
  `facts.md`(대본 사실대장)와 대조. 대장에 없는 단정·틀린 수치·오타 고유명사 탐지
  (`[[hallucination-guard]]` 기준 적용 (팩 스킬이라 Skill 목록에 없을 수 있다 — 없으면 `cys skill show hallucination-guard` 로 본문을 연다)). **무근거 화면 텍스트 = NO_GO.**
- **대본↔영상 일치**: 영상이 실제로 검증된 대본을 말하는가(누락·즉흥 추가 없음).
- **종합**: `[[video-verify-visual]]`·`[[video-verify-timing]]`·`[[video-verify-audio-sync]]`
  3관문이 전부 GO인가.
- **출고 서류**(공개 게시·상영 전): (a) 사용권 근거 — 목소리(macOS say = 공개본 불가 · ElevenLabs 무료 등급 = 비상업 공개 + 제목 출처 표기일 때만 · 상업 게시본은 유료 등급)·
  음악(`audio/music-license.json`)·글꼴·생성물(서비스 등급)마다 공개 사용을 허락하는 근거가 적혀 있나
  (b) 크기 — `[[video-verify-audio-sync]]` 의 통합 LUFS·최고점 숫자가 목표 안인가 (c) 유튜브 실시간 방송에
  쓸 영상이면 음악이 Content ID 미등록이거나 허용 목록 근거가 있나 (d) AI 공개 — 실제 같은 생성 장면·
  영상의 주된 초점인 AI 음악·실존 인물처럼 보이는 아바타가 있으면 업로드 때 공개 『예』(유튜브 도움말 14328491).
  하나라도 비면 NO_GO.

## 절차

1. **화면 텍스트 추출** → 검증: 텍스트가 있는 프레임에서 자막·수치·고유명사를 읽는다(OCR/비전).
2. **사실 재대조** → 검증: 각 화면 텍스트를 `facts.md`와 대조. 미검증·오류 항목 플래그.
3. **종합 판정** → 검증: 화면 사실성 통과 + 앞 3관문 전부 GO → **GO**. 하나라도 미달 → NO_GO.

## 출력 계약

`{gate: "final", verdict: GO|NO_GO, fact_issues: [...], release_docs: {license, loudness, live_music, ai_disclosure}, gates: {visual, timing, audio_sync}}`.
**GO일 때만** 상위 `[[video-verify]]`가 영상을 출고 승인. 화면 무근거 텍스트가 하나라도
남으면 NO_GO로 막고 원인 단계(자막=`[[video-stitch]]`, 내용=`[[script-writer]]`)로 회송한다.
