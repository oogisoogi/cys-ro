---
name: audio-post-mix
description: 배경음악을 나레이션 아래로 덕킹하고 라우드니스를 정규화하는 하위 스킬 — 사이드체인 덕킹·구간 페이드·유튜브 라우드니스 타깃(약 -14 LUFS)으로 최종 믹스 사양을 만든다. audio-post 믹스 관문. "오디오 믹스 / 덕킹 / 라우드니스 정규화 / 페이드" 맥락에서 발동.
disable-model-invocation: true
---

# audio-post-mix

> 수동 전용 하위 스킬(아래 `[[…]]` 중 Skill 목록에 없는 것 · disable-model-invocation)은 Skill 도구로 부르지 않는다 — 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read 해 따른다(사용자는 `/<이름>` 으로 직접 부를 수 있다).

음악과 나레이션이 같은 크기로 싸우면 말이 안 들린다. 음악을 말 아래로 깔고 레벨을 고른다.

## 믹스 규칙

- **덕킹**: 나레이션이 있는 구간에서 음악을 자동으로 낮춘다(사이드체인 또는 타임스탬프 기반).
  말 없는 구간(인트로·전환)에선 음악을 올려 호흡을 준다.
- **레벨**: 나레이션이 항상 명료하게 위. 음악 베드는 보통 나레이션 대비 -12~-18 dB 영역.
- **페이드**: 시작·끝·구간 전환에 페이드 인/아웃(갑작스런 컷 금지).
- **라우드니스**: 최종 통합 라우드니스를 약 -14 LUFS, 실제 최고점(true peak) ≤ -1 dBTP 로
  정규화. 과압축·클리핑 방지.
  - -14 LUFS 는 유튜브 등 스트리밍의 **업계 관행값**이다 — 유튜브 공식 도움말에는 LUFS 숫자가 없다
    (「안정적인 볼륨」 설명뿐 · 2026-11 확인). 최고점 -1 dBTP 는 EBU R128 의 공식 상한이다.
    납품처가 다른 값을 정해 주면 그 값을 따른다.

## 절차

1. **타임라인 정렬** → 검증: 나레이션 타임스탬프로 발화/비발화 구간을 만들어 덕킹 곡선 산출.
2. **덕킹·레벨** → 검증: 음악을 구간별로 덕킹, 나레이션 명료도 확인(말이 음악에 묻히지 않게).
3. **페이드·정규화** → 검증: 페이드 적용, 통합 라우드니스·트루피크를 타깃으로 정규화.
   - 실행 = ffmpeg `loudnorm` 2회. 1회째는 재기만 한다:
     `ffmpeg -i mix.wav -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null -`
     → 출력 JSON 의 `input_i`·`input_tp`·`input_lra`·`input_thresh` 를 2회째의
     `measured_I`·`measured_TP`·`measured_LRA`·`measured_thresh` 에 넣고 `linear=true` 를 붙여 실제로 바꾼다.
     (zsh 에서는 변수 뒤에 `:` 가 오면 `${변수}` 로 감싼다 — `$th:linear` 는 `:l` 수식어로 깨진다.)
   - 확인 = 결과를 `ffmpeg -i out.wav -af ebur128=peak=true -f null -` 로 다시 재서 요약의 `I:`(통합 LUFS)·
     `Peak:`(실제 최고점)가 목표 안인지 **숫자로** 기록한다.
   - 덕킹(사이드체인) 예: `ffmpeg -i bgm.wav -i narr.wav -filter_complex "[1]asplit[n1][n2];[0][n1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[d];[d][n2]amix=inputs=2:normalize=0[m]" -map "[m]" mix.wav`
     (motion-graphics-prompt 와 같은 명령).

## 출력 계약

`audio/mix-spec.json`(덕킹 곡선·레벨·페이드·라우드니스 타깃) — `[[video-stitch]]` 마스터
렌더가 이 사양으로 음악·나레이션을 합친다. 상위 `[[audio-post]]`로 반환. 말이 묻히거나
라우드니스 미달이면 보고·수정. 최종 검증은 `[[video-verify-audio-sync]]`가 레벨을 본다.
