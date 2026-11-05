---
name: video-report-deck
description: 분석·조사 결과를 슬라이드형 보고 영상(mp4·내레이션·자막)으로 만든다. 「보고 영상·분석을 영상으로」 때 쓰고, PPT 파일(.pptx)은 ppt-styles·행사 인트로 모션은 motion-graphics-prompt.
---

# video-report-deck

글 대신 **보면서 듣는 보고**를 만든다. 화면은 숫자·명사구·결론만, 설명은 내레이션이 맡는다.
장면 JSON 한 개 → 문장별 목소리 → HTML 장면을 프레임으로 찍기 → ffmpeg 합성 → `report.mp4`(1920×1080 · H.264 · AAC · 한국어 자막 트랙) + `report.srt`.

스킬 폴더(아래 명령의 `$S`):

```bash
S="${CYS_PACK_DIR:-$HOME/.cys/pack}/skills/video-report-deck"
```

| 파일 | 하는 일 |
|---|---|
| `bin/build.py` | 빌더(장면 JSON 검사 → 목소리 → 프레임 계획 → 렌더 → 합성) |
| `bin/tts.py` | 목소리 어댑터(ElevenLabs = 환경변수 키 · `say` = 맥 전용 대체) |
| `bin/render.js` | `deck.html` 을 프레임마다 PNG 로 찍는다(playwright) |
| `deck.html` · `templates/*.js` · `tokens.css` | 장면 화면 · 유형 12개 · 색·크기 정본 |
| `STYLE.md` | 모양 문법·수치의 근거(관찰값) |
| `example/deck.example.json` | 예시 덱(가상 팀 주간 보고) |

## 언제 쓰나

- 분석 결과(숫자·표·목록)를 사람이 **영상으로** 받아야 할 때(읽기보다 듣기가 빠른 보고).
- 숫자 근거(분석 출력)가 이미 있을 때 — 이 스킬은 **숫자를 만들지 않는다.** 장면 JSON 의 숫자는 분석 출력에서 코드로 꺼내 넣는다.
- 이 스킬이 아닌 것: PPT 파일(.pptx)이 필요하면 `ppt-styles` · 행사 인트로·오프닝 모션 영상은 `motion-graphics-prompt` · 아바타가 말하는 유튜브 영상은 `youtube-video-pipeline`.

## 순서

### 0. 준비(처음 한 번)
1. 필요한 것: `python3` + Pillow(`python3 -m pip install Pillow`) · `node` 18 이상 · `ffmpeg`·`ffprobe`.
2. 렌더 의존은 사용자 기기의 의존 폴더에 한 번 설치한다(팩 폴더 안에는 두지 않는다 — 팩 갱신이 팩 폴더를 통째로 갈아 끼운다): `D="${CYS_SKILL_DEPS:-$HOME/.cys/deps/video-report-deck}"; mkdir -p "$D" && cp "$S/package.json" "$D/" && cd "$D" && npm i && npx playwright install chromium`.
3. 글꼴(선택): 팩에는 글꼴 파일이 없다. Pretendard 를 쓰려면 https://github.com/orioncactus/pretendard/releases/tag/v1.3.9 에서 `Pretendard-1.3.9.zip` 을 받아 `web/static/woff2/` 의 Regular·Medium·SemiBold·Bold·ExtraBold·Black 6개를 `"$S/fonts/"` 에 둔다(SIL OFL 1.1 · https://github.com/orioncactus/pretendard/blob/main/LICENSE). 기기에 설치돼 있어도 된다. 없으면 시스템 고딕으로 찍고 렌더러가 받는 곳을 알린다.
4. 목소리(둘 중 하나):
   - ElevenLabs: `export ELEVENLABS_API_KEY=<당신의 키> ELEVENLABS_VOICE_ID=<목소리 id>`(선택 `ELEVENLABS_MODEL_ID` · 기본 `eleven_multilingual_v2`). 키는 환경변수로만 받는다 — 팩 규약 `suite-runtime-keys`.
   - 맥의 `say`(한국어 Yuna · 속도 190): **맥 전용 대체 수단**이다. 윈도·리눅스에서는 ElevenLabs 키가 있어야 한다.
5. 무엇이 없으면 빌더가 「없음 … — 설치 방법」을 찍고 코드 4로 끝난다. 그 안내를 사용자에게 그대로 전한다(자동 설치하지 않는다).

### 1. 장면 JSON 만들기

```json
{
  "deck": { "brand": "이름 *강조 부분*", "source": "기본 출처 줄" },
  "scenes": [
    { "type": "numbered",            // 아래 유형 중 하나
      "chip": ["장", "세부"],         // 우상단 칩(둘째 조각은 연두)
      "source": "출처 · … · 날짜",     // 맨 아래 출처 줄(없으면 deck.source)
      "data": { … 유형별 … },
      "lines": [                      // 내레이션 = 자막. 문장 하나가 한 줄
        { "say": "첫째, …", "step": 0 },   // step = 이 문장에서 켜질 요소 번호(0부터)
        "둘째, …"                          // 문자열만 쓰면 step = 문장 순번
      ] }
  ]
}
```

- **`*…*` = 연두 강조**(화면 글자 어디서나). 자막은 숫자·「」 를 자동 연두.
- `step` 규칙: 번호가 step 보다 작으면 밝음, 같으면 지금 켜짐(0.4초 등장), 크면 흐림. 처음에 전부 흐리게 깔고 싶으면 첫 문장 `step: -1`.
- 표·막대를 한꺼번에 보이려면 `data.reveal: false`.

| 유형 | data | 쓰는 곳 |
|---|---|---|
| `cover` | kicker, line1, line2(연두), date, sub, label, slots[] | 표지 · 목차 예고 |
| `statement` | kicker, lines[], note, size | 장 여는 한 문장 · 결론 한 줄 |
| `numbered` | title, items[{main, sub}] | 핵심 N개 |
| `kpi` | title, items[{v, unit, l}] (1~4) | 큰 숫자 카드 |
| `bars` | title, unit, items[{l, v, hl}], reveal, note, values | 가로 막대 비교 |
| `columns` | title, s1[], s2[], legend[], hl[], xstep, xunit | 시간대·날짜별 세로 막대 |
| `heat` | title, grid[행][열], rows | 요일×시간 히트맵 |
| `ring` | value, total, center, center_sub, lines[] | 전체 중 일부(도넛) |
| `table` | title, head[], rows[{c[], hl}], num[] | 근거 표 · 후보 순위 |
| `quote` | tag, tag_acc, lines[] | 인용(메일 제목 등) |
| `checklist` | title, items[] | 다음 행동 |
| `cards` | title, items[{title, body, foot}] | 대표 사례 N장 |

새 유형 = `templates/<이름>.js` 에 `TYPES.<이름> = (d, step) => html` 하나 + `deck.html` 에 script 한 줄. 색·크기는 `tokens.css` 변수만 쓴다.

### 2. 빌드

```bash
python3 "$S/bin/build.py" --deck <deck.json> --out <report.mp4> [--work <작업폴더>] [--tts auto|say|elevenlabs]
# 예시 덱
python3 "$S/bin/build.py" --deck "$S/example/deck.example.json" --out <임시폴더>/x.mp4
```

- `--tts auto` = ElevenLabs 키가 있으면 ElevenLabs, 없으면 맥에서만 `say`. 같은 문장은 다시 합성하지 않는다(작업폴더 `audio/` 캐시).
- 장면 JSON 이 틀리면(유형 이름 · 빈 문장 · scenes 없음) 렌더 전에 어느 장면이 왜 틀렸는지 찍고 코드 2.
- 마지막 줄 JSON = `engine · lines · scenes · frames · seconds · mp4 · srt`.

### 3. 확인
- 결과 mp4 에서 낱장을 뽑아 본다(`video-verify-visual` 관점) — 넘침 경고(`경고 OVERFLOW`)가 찍힌 장면은 둘로 나눈다.

## 화면 규칙(지킬 것)

1. 강조색은 연두 하나. 비교 대상은 회색(`--mute`).
2. 숫자·라벨·출처는 고정폭(`--mono`).
3. 글자 크기: 본문 40px 이상 · 가장 작은 글자 24px(1080 기준). 넘치면 렌더러가 0.8배까지만 줄이고 경고를 찍는다 — 경고가 나오면 장면을 둘로 나눈다.
4. 화면 글자는 짧게(제목 ≈15자 · 항목 ≈25자). 설명은 내레이션으로.
5. 모든 장면에 출처 줄. 숫자는 관찰값이라는 것을 첫 장면 내레이션에서 밝힌다.
6. **들리는 숫자 = 보이는 숫자**: 내레이션이 말하는 숫자는 그 장면 화면에 있어야 한다. 가로 막대에서 강조 막대가 아닌 값을 말하면 `values: "all"`.

## 주의할 점

- ⛔ 참고 영상(다른 채널)의 얼굴·로고·채널명·문구 복제. 가져오는 것은 모양·문법뿐(`STYLE.md`).
- ⛔ 장면 JSON 에 손으로 숫자 적기(분석 출력에서 코드로 끼운다).
- ⛔ 키를 파일·로그·화면에 쓰기. ElevenLabs 가입·결제를 이 스킬이 시도하지 않는다. ElevenLabs 는 글자 수 종량제라, 긴 덱은 `cost-preview-confirm` 규약으로 먼저 확인한다.
- ⛔ 개인 원자료가 들어간 덱·영상을 공개 경로·저장소에 두는 것.
- `node_modules` 는 `~/.cys/deps/video-report-deck`(또는 `CYS_SKILL_DEPS`)에 둔다 — 스킬 폴더에 설치하면 다음 팩 갱신 때 사라진다. 글꼴은 기기에 설치하는 것이 안전하다(스킬 폴더 `fonts/` 도 같은 이유로 갱신 때 사라질 수 있다).
- 소요(실측 2026-10-20 · 맥 · say): 69문장 · 8분 38초 영상 = 처음 약 3분 30초(목소리 합성 포함) · 문장 그대로 재렌더 약 3~4분.
- 아직 안 되는 것:
  - 자막의 「말하는 낱말만 밝게」(가라오케)는 낱말 시각이 필요하다 — 지금은 2~4어절 조각을 글자 수 비례로 나눠 보인다(소리와 ±0.5초 어긋날 수 있음 · ElevenLabs with-timestamps 연결은 미구현).
  - 선 그래프 · 파이 · 점 격자 · 문서 캡처+강조 상자 등은 유형이 아직 없다(`STYLE.md` 4절).
  - 요소 켜짐은 문장 단위다 — 한 문장 안에서 여러 요소가 차례로 켜지는 박자는 못 낸다.
  - 다섯 줄 이상의 `numbered` 는 넘침 축소가 걸려 글씨가 작아진다 — 장면을 나누는 편이 낫다.

## 확인하는 방법

- 예시 덱 빌드 → 마지막 줄 JSON 의 `scenes 5` · mp4 와 srt 가 생기고 `ffprobe` 로 1920×1080 · 자막 트랙(mov_text) 확인.
- 장면 JSON 을 일부러 틀리게(모르는 type) → 코드 2와 「scenes[i] 의 type … 를 모른다」.
- 의존 안내: PATH 를 비우고 돌리면 「없음 ffmpeg / ffprobe / node」와 코드 4 · 맥이 아닌 기기에서 키 없이 돌리면 「say 목소리는 맥 전용입니다」와 코드 4.
- 시험 입력 결과(2026-11-06 · 스크래치 폴더 · 맥 · say · playwright 1.63.0 · Pretendard 없음):
  - 예시 덱 → `{"engine": "say", "lines": 10, "scenes": 5, "frames": 125, … "seconds": 31.1}` 코드 0 · 약 12초 · ffprobe `h264 1920×1080 · aac · mov_text`. 가상 상점 2장면 덱 → `seconds 9.4` 코드 0 · 표 장면 낱장에서 강조 행 연두·흐린 행 확인. 두 번 다 「알림 Pretendard 글꼴이 없어 시스템 고딕으로 찍는다」 + 받는 곳 안내.
  - 지저분한 입력: 모르는 type `piechart` · 공백뿐인 문장 · 깨진 JSON · 없는 파일 → 각각 「입력 오류 …」 코드 2 · `--tts robot` → argparse 코드 2.
  - 의존 안내: 의존 폴더에 playwright 없음 → 「없음 playwright … 의존 폴더에 한 번 설치」 코드 4 · PATH 를 비우면 「없음 ffmpeg / ffprobe / node」 코드 4 · `--tts elevenlabs` 키 없음 → 「ElevenLabs API 키 미설정」 코드 4 · 맥이 아닌 기기 흉내(`sys.platform=linux`)에서 auto·키 없음 → 「say 목소리는 맥 전용입니다」 코드 4. ElevenLabs 실제 호출은 건너뜀(키·과금).
- 의존 폴더 이관 재시험(2026-11-06 · 조정자): 스킬 폴더에 node_modules 없이 `CYS_SKILL_DEPS=<설치 폴더>` 로 예시 덱(say) → 31.1초 mp4(1,161,315바이트).
