---
name: narrated-motion
description: 대본이나 주제 한 줄로 무료 내레이션·자막이 입혀진 설명 모션 영상(mp4)을 문장 단위 싱크까지 검사해 만든다. 「대본으로 영상 / 목소리 들어간 설명 영상」 요청 때.
---

# narrated-motion — 대본 → 내레이션 모션 영상(우리 판 script-to-motion)

명령의 `<정본>` = 이 스킬 폴더 · `<M>` = 형제 스킬 `motion-graphics-prompt` 폴더(같은 skills 폴더 안 · `<정본>/../motion-graphics-prompt`)
도구 = `tools/s2m_cues.py`(문장별 음성·시각표) · `<M>/tools/seek_render.js`(스틸·결정론·렌더 · motion-graphics-prompt 와 같은 도구) · `tools/s2m_frames_diff.py`(두 번 렌더 비교) · `tools/s2m_sync_check.py`(소리·그림 싱크 측정) · 틀 `template/index.html`
원작 = 코드깎는노인 `kstost/script-to-motion`(MIT · b791213 · 2026-11-10) — 무엇을 가져오고 무엇을 안 가져왔는지는 맨 아래 「원작과의 관계」.
견본 실측(「컨텍스트 순환이 무엇인가」 32.8초) = 아래 「확인하는 방법」.

## 언제 쓰나
- 사용자가 **대본**(또는 주제·기획서)을 주고 「목소리 들어간 설명 영상」을 원할 때 — 수업·설교 보조·도구 소개·개념 설명(30초~몇 분).
- 다른 스킬이 맞는 경우: 음성 없는 15~30초 인트로 = `motion-graphics-prompt` · 숫자·분석 보고를 카드로 = `video-report-deck` · 아바타·B-roll 유튜브 = `youtube-video-pipeline`(유료 경로 포함).

## 절차

### 1. 입력 판정 → 대본
- **대본을 받았으면 글자를 바꾸지 않는다.** 문장(큐)으로 나누기만 하고, 읽는 법만 `say` 칸에 따로 쓴다(숫자·단위·영어 → 한글 발음 · 「70%」 → 「칠십 퍼센트」). 화면·자막에는 `text`(원래 표기).
- **주제·기획서만 받았으면** `script-writer` 스킬로 조사·사실검증 후 대본(출처는 프로젝트 `research.md`). 기획서가 정한 것(꼭 넣을 말·대상·마지막 문장)은 그대로.
- **길이 목표를 두지 않는다**(원작 「Content first, never time」): 설명·연결 문장을 길이 때문에 빼거나 줄이지 않는다. 사용자가 길이를 정했는데 넘치면 내용을 지키고 「몇 초가 나왔고 왜」를 보고.

### 2. 처음 듣는 사람 관문(녹음 전 · 고칠 때마다)
대본은 **한 번, 순서대로, 소리로만** 듣는 사람 기준이다. 쓴 사람의 머릿속 맥락은 듣는 사람에게 없다.
1. 줄마다 5문: 누가·무엇을·언제가 그 줄 안에 있나 · 들은 적 없는 이름·용어가 있나(처음 나올 때 쉬운 말로 풀었나) · 「그래서·그다음·이렇게」가 바로 앞 줄을 가리키나 · 그림 없이 소리만으로 뜻이 서나 · 주장이 기록(출처·실측)에 있나.
2. **이음매마다 쿠션**: 주제가 바뀌는 곳은 「앞 주제 닫기 → 숨(앞 줄 뒤 쉼을 조금 길게 · `gapAfter`) → 어디로 가며 왜 지금인지」. 「다음은」 한 마디는 쿠션이 아니다.
3. **내부 이름 목록**: 큐 id·파일 이름·작업 별명 등 우리끼리만 아는 이름을 손으로 적고, 내레이션·화면 글자에서 찾아 없앤다.
4. **차가운 청자 검토**: 이 프로젝트를 본 적 없는 서브에이전트에게 `script.txt`(대본 글자만)만 주고 「무엇·어느 것·언제·누가·왜를 알 수 없는 줄과, 쿠션 없이 주제가 뛰는 곳을 전부」 받는다 → 고치고 그 구간만 다시 검토.
5. 문체: 말하는 한국어(~니다 위주 · ~요 섞음) · 한 문장 한 생각 · 한 문장 숫자 하나 · 괄호·기호는 `say` 에 넣지 않는다 · AI 말투(그럴듯하지만 무슨 뜻인지 멈춰서 생각하게 하는 말) 금지.

### 3. script.json → 무료 음성 · 시각표
```json
{ "title": "…", "voice": {"engine": "say", "name": "Yuna (Premium)", "rate": 185},
  "leadIn": 0.6, "tail": 1.2, "gapAfter": 0.3,
  "cues": [ {"id": "c01", "text": "화면·자막 표기", "say": "읽는 법(없으면 text)", "gapAfter": 0.45} ] }
```
```bash
python3 <정본>/tools/s2m_cues.py <프로젝트>      # audio/cues/*.wav · audio/narration.wav · cues.json · js/cues.js · narration.srt · script.txt · synth-manifest.json
```
- 시각은 **합성된 파일의 샘플 수**로만 정한다(LLM 이 듣고 적은 시각 금지 · 전사 불필요). 앞뒤 무음은 −45 dBFS 기준으로 잘라 「문장 시작 = 말 시작」.
- 목소리 = **macOS say(기기 밖으로 안 나감 · 무료)** 기본 · `Yuna (Premium)`/`Jian (Premium)` 등 한국어 Premium 목소리. `edge` 엔진은 설치돼 있을 때만(무료지만 문장이 외부 서버로 감 → 개인정보 대본 금지).
- ⛔ 유료 TTS(ElevenLabs·Fish Audio)는 이 도구가 부르지 않는다 — 사용자 목소리 복제가 필요하면 `voice-clone-elevenlabs` + `cost-preview-confirm`(사용자가 비용을 먼저 확인) 후 그 wav 들을 같은 큐 id 로 `audio/.cache` 대신 넣는 확장(초안 범위 밖).
- 문장 하나만 고치면 그 문장만 다시 합성된다(캐시 = 엔진·목소리·빠르기·발음 문자열의 해시).

### 4. 세계 한 장 + 큐별 장면표(storyboard.md)
- 맨 위 3줄: **세계**(이 영상이 벌어지는 한 장소·물건 — 예: 책상 위 유리 그릇) · **빛**(조명 하나·어디서) · **반복되는 물건**(처음부터 끝까지 변하며 따라가는 것). 주제마다 새로 고른다 — 지난 영상과 같은 배경·강조색·전환을 습관으로 반복하지 않는다.
- 표: 큐 | 문장 | 화면에 보일 것 | 무엇이 움직이나(문장 시작 + 몇 초 / 문장 안 진행률) | 큰 글자(그 문장에서 화면에 박히는 낱말 하나).
- ⛔ **슬라이드·상자 금지**: 제목 띠 + 내용 · 글을 담은 카드·패널 · 글머리표 목록 · 표 · 상자-화살표 그림. 움직임을 빼고 한 장으로 봤을 때 슬라이드나 문서처럼 보이면 다시 짠다. 허용되는 「상자」는 이야기 속 물건(종이·화면·간판)뿐.
- 큰 글자·숫자는 크게 · 화면 크기 3단계 이내 · 겹침·잘림 금지(기존 의뢰서 6칸 그대로).

### 5. 페이지(index.html)
- `template/index.html` 을 복사 · `fonts/` 에 OFL 글꼴 파일 + 라이선스(예: Pretendard · SIL OFL 1.1 · github.com/orioncactus/pretendard 에서 받은 woff2 + LICENSE) — 시스템 글꼴·웹 글꼴 링크 금지.
- 모든 값은 `window.seek(t)` 안에서 `t` 와 `window.CUES` 로만. 움직임은 **초가 아니라 문장에** 묶는다: `inCue(t, "c03", 0.4, 1.0)`(c03 시작 0.4초 뒤부터 1초 동안 0→1) · `frac(t, "c02")`(문장 안 진행률).
- **문장이 시작되는 그 프레임에 화면이 바뀌게** 한다(자막 교체 + 큰 글자·물건 등장) — 6·8단계가 이 바뀜을 잰다.
- 금지(결정론): CSS 애니메이션·transition · 타이머·rAF 루프 · `Math.random`·`Date`·`performance.now` · 네트워크 자원. 캔버스는 seek 첫머리에서 상태 초기화.

### 6. 스틸 먼저(영상 전에 반드시)
```bash
node <M>/tools/seek_render.js <프로젝트>/index.html --out <프로젝트>/stills --stills <큐마다 중간 시각,…>
```
- 줄마다 `결정론=OK` · `새페이지=OK` 아니면 고친 뒤 다시(rc 1 = 상태가 샌다 · rc 3 = seek 없음).
- 스틸을 **직접 열어 본다**: 겹침·잘림·고리/물건이 글자를 가림·슬라이드처럼 보임·한 장면에 같은 구도 반복. 고치면 다시 스틸.

### 7. 렌더
```bash
D=$(python3 -c "import json;print(json.load(open('<프로젝트>/cues.json'))['duration'])")
node <M>/tools/seek_render.js <프로젝트>/index.html --out <프로젝트>/renderA --duration $D --fps 30 --audio <프로젝트>/audio/narration.wav
```
- 결과 = `renderA/out.mp4` + ffprobe 줄. 영상 0초 = narration.wav 0초(`leadIn` 포함)라 따로 맞출 것이 없다.
- 시간 예측: 스틸 한 장 시간 × 프레임 수(견본 실측 = 프레임당 약 0.36초 · 아래).

### 8. 검사(넘기기 전 · 숫자로)
```bash
node <M>/tools/seek_render.js <프로젝트>/index.html --out <프로젝트>/renderB --duration $D --fps 30      # 두 번째 렌더(다른 브라우저 실행)
python3 <정본>/tools/s2m_frames_diff.py <프로젝트>/renderA/frames <프로젝트>/renderB/frames            # 전 프레임 sha 같음 = OK
python3 <정본>/tools/s2m_sync_check.py <프로젝트>/renderA/out.mp4 <프로젝트>/cues.json --json <프로젝트>/sync.json   # 큐마다 소리·그림 시작 오차 ±0.2초
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of compact <프로젝트>/renderA/out.mp4
```
- `s2m_sync_check` 는 결과 mp4 자체를 다시 잰다(오디오 −40 dBFS 첫 창 = 말 시작 · 160×90 회색 프레임 차이 = 그림 바뀜) · 0.4초 넘는 무음(dead air)도 함께 보고 — 말 사이 쉼이 길면 `gapAfter` 를 줄인다.
- 낱장 검수: `<M>/tools/ref_frames.sh <out.mp4> <폴더>/qc 2` 로 뽑아 직접 본다(`video-verify-visual` 관점).
- ⚠ 우리는 소리를 귀로 못 듣는다 — 숫자·영어·이름이 든 문장(say 발음 변환한 줄)을 사용자가 먼저 들어 볼 목록으로 넘긴다.

### 9. 넘기기
mp4 경로 · 길이·해상도·오디오(ffprobe) · 결정론(스틸·두 번 렌더) · 싱크 표(최대 오차) · dead air · `script.txt` · 먼저 들어 볼 문장 · 못 본 것(매끄러움·귀로 듣는 품질).

## 주의
- 렌더 도구(`<M>/tools/seek_render.js`)는 Playwright·헤드리스 크롬을 의존 폴더 `~/.cys/deps/motion-graphics-prompt`(또는 `CYS_SKILL_DEPS`)에서 찾는다 — 없으면 설치 명령 1줄을 보이고 코드 4로 멈춘다. node 실행 전 `unset NODE_OPTIONS`. say 는 macOS 전용이다.
- 실존 인물의 이름·사진·목소리가 들어가는 영상은 당사자 동의를 받고, 공개(유튜브 게시 등)는 사용자가 정한다. 외부 결제·가입 0.
- say 목소리는 「초안·내부용」 품질이다 — 대외 게시용 목소리(사용자 목소리 복제 등)는 비용 게이트를 거친 별도 결정.

## 확인하는 방법
- 견본 재현(2026-11-11 실측): `script.json` 만 새 폴더에 두고 `python3 tools/s2m_cues.py <폴더>` → 큐 5 · 전체 32.803s · narration_sha256 `6b9ba12980e814d6…`(캐시 없이 두 번 합성해 같음 · `js/cues.js` 바이트 동일) → 스틸 5장 `결정론=OK`·`새페이지=OK` → 렌더 984프레임(5분 56초 · 프레임당 약 0.36초) → `s2m_sync_check` FAIL 0/5 · 최대 오차 0.031초.
- 싱크 검사기 자체 시험(대조군): 오디오를 0.35초 늦춘 mp4 = FAIL 5/5 · 영상을 0.35초 늦춘 mp4 = FAIL 5/5 · 오디오 0.15초 늦춤 = 통과(오차 0.155) · 0.25초 늦춤 = FAIL(0.255). ⚠ 초판은 ① 앞 문장 꼬리를 말 시작으로 잡았고 ② mp4 의 오디오 시작 지연(편집 목록)을 버리고 읽어 늦춘 오디오를 못 잡았다 — 둘 다 고친 판이 이 파일.
- dead air: 견본 c02 뒤 `gapAfter 0.45` → 실제 무음 0.48초(앞뒤 여유 포함)로 원작 0.4초 규칙을 넘었다 — 주제가 바뀌는 숨이라도 `gapAfter` ≤ 0.35 를 기본으로.

## 원작과의 관계(script-to-motion · MIT)
- **가져온 것(규칙·관문)**: 처음 듣는 사람 5문 · 이음매 쿠션 · 내부 이름 목록 · 차가운 청자 서브에이전트 검토 · 길이 목표 없음 · text/say 분리 · 큐 = 문장 = 시각의 단위 · 잰 길이가 시각표 · 슬라이드·상자 금지와 「세계 한 장」 · 0.4초 dead air · 역순·새 실행 결정론 검사 · 소리를 못 들으니 사람에게 먼저 들을 줄 목록.
- **안 가져온 것(이유)**: Fish Audio 전용 TTS(유료·「다른 TTS 금지」 규칙 = 우리 무료 원칙과 충돌) · `.claude/settings.local.json` 에 영구 훅을 쓰는 화면 가드(작업 폴더 `.claude` 에 들어가 프레임 검수 스킬과 충돌) · cokacmotion 을 매일 main 에서 받아 실행(버전 고정 없음) · render.py 의 무고정 `pip install playwright` 와 `~/.cache` 가상환경 · GSAP·3D·Blender 묶음(필요 시 레퍼런스에서 꺼냄) · 「MP4 는 사용자가 만든다」(우리는 끝까지 mp4 까지).

## 원 설명 (목록 상주 설명 축소 전 원문 · 1.1.16 cysr-1116-asset-skills-1120)

대본(또는 주제 한 줄)을 받아 무료 내레이션이 입혀진 설명 모션그래픽 영상(1920×1080 mp4 · 자막 · 문장 단위 싱크)을 끝까지 만드는 스킬 — 우리 판 script-to-motion. 대본 → 처음 듣는 사람 관문 → 문장별 무료 음성(macOS say · 유료 API 0) → 잰 길이로 시각표 → window.seek(t) 페이지 → 스틸 먼저(결정론) → 렌더 → 두 번 렌더 비교·소리/그림 싱크 측정(±0.2초). "대본으로 영상 만들어 / 내레이션 영상 / 설명 영상 / 모션 영상에 목소리 / script to motion / 주제만 주고 영상" 요청 때 발동. 행사 인트로(음성 없음)는 motion-graphics-prompt, 숫자 보고 카드는 video-report-deck.
