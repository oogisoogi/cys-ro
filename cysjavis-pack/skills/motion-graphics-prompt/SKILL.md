---
name: motion-graphics-prompt
description: 행사 인트로·오프닝 모션그래픽 영상(HTML·GSAP를 프레임 렌더해 mp4)의 의뢰서 작성과 제작. 「인트로 영상·모션그래픽 만들어」 때 쓰고, 아바타 유튜브 영상은 youtube-video-pipeline·숫자 보고 영상은 video-report-deck.
---

# motion-graphics-prompt

유료 영상·이미지 도구 없이 클로드가 **코드로 그린 움직임**으로 15~30초짜리 인트로 영상을 만든다.
핵심 = 영상 레퍼런스(움직임)와 이미지 레퍼런스(디자인)에 역할을 나눠 주는 의뢰서 + 렌더 전에 싼 스틸로 먼저 고치기.

스킬 폴더(아래 명령의 `$S`):

```bash
S="${CYS_PACK_DIR:-$HOME/.cys/pack}/skills/motion-graphics-prompt"
```

| 파일 | 하는 일 |
|---|---|
| `BRIEF-TEMPLATE.md` | 의뢰서 양식(8칸) |
| `tools/seek_render.js` | `window.seek(t)` 페이지 → 스틸(결정론 검사) · 프레임 → mp4 |
| `tools/ref_frames.sh` | 레퍼런스 영상 → 장면 낱장 + 모아보기(Prompt Motion 이면 원 프롬프트를 화면에만) |
| `examples/sample-seek.html` | seek 계약 견본(4초 · 가상 행사) |
| `references/heidi-motion-prompt.summary.md` | 의뢰서 뼈대가 된 헤이디 프롬프트의 칸 구성 요약(우리 말) |

## 언제 쓰나

- 행사·발표 시작 전에 화면에 한 번 트는 15~30초 영상, 키네틱 타이포·도형 변신 영상이 필요할 때.
- 내레이션(음성 + SRT)에 맞춰 그림이 움직이는 설명·이야기 영상도 이 스킬이다 — 의뢰서 8칸 「내레이션 기반」을 채운다(길이 = 내레이션 + 1초 · 장면 시작 = SRT 시각).
- 이 스킬이 아닌 것:
  - 실사 사진·키비주얼 질감을 그대로 살려야 하는 영상 → `media-gen`(fal.ai 종량제 · `cost-preview-confirm` 로 비용 먼저). 이 스킬은 그림을 코드로 다시 그리므로 질감이 사라진다.
  - 아바타가 말하는 유튜브 영상 → `youtube-video-pipeline`.
  - 숫자·분석을 내레이션과 함께 보이는 보고 영상 → `video-report-deck`.

## 순서

### 0. 준비(처음 한 번)
- `node`(18 이상)가 필요하다. 렌더 도구 의존은 사용자 기기의 의존 폴더에 한 번 설치한다(팩 폴더 안에는 두지 않는다 — 팩 갱신이 팩 폴더를 통째로 갈아 끼운다): `D="${CYS_SKILL_DEPS:-$HOME/.cys/deps/motion-graphics-prompt}"; mkdir -p "$D" && cp "$S/package.json" "$D/" && cd "$D" && npm i && npx playwright install chromium`.
- 영상(mp4)까지 만들려면 `ffmpeg`·`ffprobe`, 레퍼런스 낱장을 뽑으려면 `ffmpeg` + (주소에 따라) `curl`·`python3`·`yt-dlp`.
- 없으면 도구가 「없음 … — 설치 방법」 1~3줄을 찍고 코드 4로 끝난다. 그 안내를 사용자에게 그대로 전한다(자동 설치하지 않는다).

### A. 레퍼런스 정하기
1. 움직임 레퍼런스: 사용자가 준 영상, 또는 Prompt Motion 갤러리(https://prompt-motion.com/)에서 사용자와 함께 고른 한 편.
2. `bash "$S/tools/ref_frames.sh" <주소> <작업폴더>/ref [초당장수]` → `contact.png`(왼쪽 위부터 가로로 · k 번째 칸 = (k-1)/초당장수 초) · `f_*.png`. Prompt Motion 주소면 원 프롬프트가 화면에 찍힌다(파일로 저장하지 않는다). 그림을 실제로 열어 보고 「가져올 것 / 베끼지 말 것」을 적는다.
3. 디자인 레퍼런스: 이미지에 번호(레퍼런스1, 2 …)를 붙여 「레퍼런스2처럼 ~」으로 집어 말한다. 발표 자료와 한 벌이면 `ppt-design-system`·`ppt-styles` 스킬의 색·글꼴.

### B. 의뢰서
1. `$S/BRIEF-TEMPLATE.md` 를 읽고 칸을 채운다(행사 개요 · 목적 · 영상 레퍼런스 · 이미지 레퍼런스 · 비율·길이·소리 · 제작 규칙 · 관문 · 내레이션). 모르는 칸은 비우지 말고 「클로드가 정함」.
2. 칸의 의도가 헷갈리거나 처음 쓰는 사용자에게 뼈대를 설명해야 하면 `$S/references/heidi-motion-prompt.summary.md` 를 Read 한다(헤이디 프롬프트의 칸 구성을 우리 말로 정리한 요약 · 원문 주소와 지은이 표기가 그 파일 첫머리에 있다).
3. 6칸 A(도구 계약)는 바꾸지 않는다 — 도구가 찍으려면 `window.seek(t)` 계약이 필요하다.

### C. 스토리라인 + 스틸 2장(영상 전에 반드시)
1. 장면별 「몇 초~몇 초 · 무엇이 보이고 어떻게 움직이나」 한 줄씩.
2. HTML 한 파일을 만들고 `node "$S/tools/seek_render.js" <page.html> --out <폴더> --stills <초1>,<초2>`.
   - `결정론=OK` 가 아니면(FAIL · 코드 1) 상태가 프레임 사이로 새는 것 → 고친 뒤 다시. `window.seek` 가 없으면 코드 3(CSS 애니메이션·타이머로 만든 페이지).
   - 「경고 CSS/웹 애니메이션 N개」가 뜨면 seek 밖에서 움직이는 것을 없앤다.
3. 스틸 PNG 를 사용자에게 보이고 고친다(행간·겹침·잘림·과한 빛·강조 낱말). 고친 뒤 다시 스틸.

### D. 영상
1. `node "$S/tools/seek_render.js" <page.html> --out <폴더> --duration <초> [--fps 30] [--subframes 3] [--audio bgm.wav]` → `<폴더>/out.mp4` + ffprobe 줄(해상도·fps·길이).
2. 피드백은 「뜻 모를 모양」「갑자기 튀어나옴」처럼 보이는 그대로 받고, 「어떻게 개선할 수 있겠나」 개선안을 낸 뒤 **다시 C(스틸)부터** → 영상.
3. 배경음: 사용자가 준 파일을 `--audio` 로. 없으면 Web Audio(OfflineAudioContext)로 박자 소리를 코드로 만들어 WAV.
4. 내레이션 기반이면:
   - 음성은 `voice-local` 스킬(또는 맥의 `say`)로, 자막 시각은 문장별 합성 길이(또는 `transcription` 스킬)로 정한다 — 들은 느낌으로 시각을 적지 않는다.
   - 내레이션 + 배경음은 먼저 덕킹 믹스(말할 때 배경음이 내려간다)를 만든 뒤 `--audio mix.wav`:
     ```bash
     ffmpeg -i bgm.wav -i narr.wav -filter_complex "[1]asplit[n1][n2];[0][n1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[d];[d][n2]amix=inputs=2:normalize=0[m]" -map "[m]" mix.wav
     ```
     자세한 라우드니스 맞추기는 `audio-post-mix` 스킬.

### E. 검수(넘기기 전)
- `bash "$S/tools/ref_frames.sh" <폴더>/out.mp4 <폴더>/qc 2` 로 낱장을 뽑아 직접 본다 — 겹침·잘림·행간·마지막 장면 고정(사회자가 이어받는 자리) 확인. 관점은 `video-verify-visual` 와 같다.

## 주의할 점

- Prompt Motion 갤러리 영상·프롬프트는 **참고용**(사이트 조건 `use=reference · ai-train=no` · 「영상·프롬프트는 만든 사람 것」). `ref_frames.sh` 는 영상·페이지를 임시 폴더에서만 쓰고 지우며, 원 프롬프트는 화면에만 찍는다. 뽑은 낱장도 작업이 끝나면 지운다. 영상·프롬프트를 쌓아 두거나 다시 배포하지 않는다.
- 레퍼런스 영상은 움직임만 빌린다 — 장면 구성·문구를 그대로 베끼지 않는다(의뢰서 3칸 「베끼지 말 것」).
- 실존 인물의 이름·사진이 들어가는 영상은 당사자 동의를 받고, 공개 범위(행사장 스크린 1회 / 온라인 게시)를 먼저 정한다. 온라인 게시는 사용자가 정한다.
- 외부 결제·가입은 이 스킬에서 하지 않는다(필요하면 `media-gen` + `cost-preview-confirm`).
- 웹 글꼴 주소만 쓰면 오프라인·샌드박스에서 대체 글꼴로 찍힌다 — 글꼴 파일을 페이지 옆에 두고 `@font-face` 로 연결한다.
- `node_modules` 는 `~/.cys/deps/motion-graphics-prompt`(또는 `CYS_SKILL_DEPS`)에 둔다 — 스킬 폴더에 설치하면 다음 팩 갱신 때 사라진다.
- 영상 한 편 렌더는 길이·`--subframes` 에 비례해 오래 걸린다(4초 · 30fps · 서브프레임 3 = 프레임 360장). 그래서 스틸에서 먼저 고친다.

## 확인하는 방법

- 견본 스틸: `node "$S/tools/seek_render.js" "$S/examples/sample-seek.html" --out <임시폴더> --stills 0.6,3.5` → 두 줄 모두 `결정론=OK` · 코드 0.
- 견본 영상: 같은 견본 `--duration 4 --subframes 3` → ffprobe `1920,1080,30/1 | 4.000000`.
- 의존 안내: 의존 폴더에 playwright 가 없으면 「없음 playwright … 의존 폴더에 한 번 설치」와 설치 명령 1줄, 코드 4.
- 시험 입력 결과(2026-11-06 · 스크래치 폴더 · playwright 1.63.0 + 받아 둔 크롬):
  - 견본 스틸 0.6·3.5초 → `결정론=OK` 2줄 · 코드 0 / 견본 4초 영상(서브프레임 3) → 360장 · `1920,1080,30/1 | 4.000000` · 코드 0 · 약 50초.
  - 지저분한 입력: 상태가 새는 사본 → `결정론=FAIL` 2줄 코드 1 · seek 없는 페이지 → 코드 3 · `--stills 1,abc` → 입력 오류 코드 2 · `ref_frames.sh` 에 없는 파일·초당장수 `abc`/`0` → 코드 2.
  - `ref_frames.sh https://prompt-motion.com/tequilafunks-97f6c9` → 원 프롬프트 화면 출력 · 15.1초 · 낱장 15장 + 모아보기 · 출력폴더에 영상·페이지·프롬프트 파일 0 · 임시 폴더 지워짐. 의존 폴더에 playwright 없음 → 「없음 playwright … 의존 폴더에 한 번 설치」 코드 4 · 크롬 없음 → 「npx playwright install chromium」 코드 4 · PATH 를 비우면 「없음 ffmpeg」 코드 4.
- 의존 폴더 이관 재시험(2026-11-06 · 조정자): 스킬 폴더에 node_modules 없이 `CYS_SKILL_DEPS=<설치 폴더>` 로 `--stills 0.6,3.5` → 두 장 결정론=OK(sha 61859d694cc9 · 438701eb5fa2) · 의존 폴더 비었을 때 → 설치 명령 1줄 + 코드 4.
- codex 2R 결함 수정 재시험(2026-11-06 · 스크래치 · `CYS_SKILL_DEPS=<설치 폴더>`):
  - `--duration Infinity` · `--duration 601` → 「입력 오류 --duration 은 0초보다 크고 600초 이하인 수여야 한다」 코드 2(무한 렌더 차단).
  - 사용자 파일이 든 `frames/` 가 있는 폴더에서 `--out . --duration 1` → 「이 도구가 만들지 않은 파일이 있다(표지 .cys-render-tmp 없음) — 지우지 않고 멈춘다」 코드 2 · 파일 그대로 · `frames` 가 심볼릭 링크 → 코드 2 · 도구가 만든 `frames/`(표지 있음)는 재실행 때 다시 써서 1초 영상 `1920,1080,30/1 | 1.000000` 코드 0 · 견본 스틸 결정론=OK 그대로.
  - `ref_frames.sh` 에 화면 없는 소리 파일(a.wav) → 「실패 낱장을 뽑지 못했다 … 옛 낱장은 그대로 둔다」 코드 2 · 옛 f_001~004·contact 보존 / 출력폴더가 심볼릭 링크 → 코드 2 · 링크 대상에 0장 / 옛 `f_001.png` 가 바깥 파일을 가리키는 링크 → 링크만 새 파일로 바뀌고 바깥 파일 내용 그대로.
  - 4초 영상 초당 260장 → `낱장 1040장` · 파일 1040개(f_1000.png 이후 포함) · contact 1920×70200 / 같은 폴더에 초당 1장 재실행 → f_001~004 + contact 만 남음(옛 1000번대도 정리).
- codex 3R 재시험(2026-11-06 · 조정자): 출력폴더에 사용자 파일 f_001-original.png·f_2025-family.png 와 옛 f_001.png → 실행 뒤 사용자 두 파일 그대로 · 우리 낱장만 교체 rc=0 · 출력 `링크/`·`링크/.` → rc=2 · 링크 대상 그대로 · `out/../out` → rc=2.
