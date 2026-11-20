# 영상 계열 스킬 개정안 43건 처분표 (TICKET=skill-revisions-1120)

- 만든 날 2026-11-20 · worker-3(surface:2311) · 가지 `feat/skill-revisions-1120`(기점 1ff82d08a) · 반영 커밋 `1d11445d5`
- 원문 = `~/axdev/master/assets/video-production/skill-revisions.md`(11-14 · A1~A35 + B1~B8 = 43건)
- 판정 기준(박사님 규칙): **반영 = 확신도 상 ∧ 유익이 결정적인 것만.** 각 건에 ① 팩(cysr 업데이트) 반영 여부 ② 초보 사용자 유익.
- 「지금도 맞는가」는 **저장소 팩 원본**(`cysjavis-pack/skills/…`)을 기준으로 다시 쟀다. 11-14 점검은 설치본(`~/.cys/pack` 1.1.14)을 읽었고, 그 뒤 skill-fold(설명 축소 · 「원 설명」 절 보존)와 2307 asset-skills(narrated-motion 승격 · motion-graphics-prompt 최신화)가 들어와 **줄 번호가 밀렸다** — 아래 줄 번호는 지금 저장소 기준이다.
- 팩은 우리 기기만이 아니라 **모든 cysr 사용자에게 간다** → 반영문은 개인 경로·교회·호칭을 빼고 일반화했다(예: 「예배 중 상영」 → 「유튜브 실시간 방송」 · 「이 맥」 → 「설치돼 있을 때만」).
- **설명(frontmatter description)은 한 줄도 바꾸지 않았다**(`git diff | grep -c '^[-+]description:'` = 0) → 설명 예산(≈15,662/30,000)·발동 낱말 회귀 없음. 설명을 바꾸자는 제안(A1 :3 · A3 :3 · A5 설명 · A8 · A33)은 본문만 고치거나 「안 함」으로 처리했다.

## 한눈에

| 처분 | 건수 | 번호 |
|---|---|---|
| 반영(전부) | 21 | A1 A3 A4 A5 A6 A7 A10 A11 A14 A15 A16 A17 A18 A20 A22 A26 A27 A28 A31 A32 A34 |
| 반영(일부) | 2 | A9 · A29 |
| 안 함 — 이미 해소됨(지금 파일에 문제 없음) | 4 | A8 A12 A13 A21 |
| 안 함 — 기준 미달·팩 부적합 | 8 | A2 A19 A23 A24 A25 A30 A33 A35 |
| 안 함 — 새 기능(이 티켓 범위 밖 · master 결정 📌) | 4 | B5 B6 B7 B8 |
| 박사님께(돈·새 길) | 4 | B1 B2 B3 B4 |
| **합계** | **43** | |

바깥 근거(이번에 직접 확인 · 2026-11-20):
- macOS 사용권 §2F = 기기 파일 `/Library/Documentation/License.lpdf/Contents/Resources/English.lproj/License.html` **67줄** 「use the system voices … to create your own original content and projects for your personal, non-commercial use … No other creation or use of the System Voices … is permitted」(신뢰도 상 · 1차 원문).
- 유튜브 AI 공개 = 도움말 14328491 「Disclosing use of altered or synthetic content」 — 실존 인물이 하지 않은 말·행동, 실제 장소·사건 변형, 실제 같은 장면 생성은 공개 대상 · 비실사 애니메이션·제작 보조(대본·아이디어)는 제외 · C2PA 로 자동 라벨 가능 · 공개만으로 시청자층·수익 자격 영향 없음(신뢰도 상).
- 유튜브 실시간 방송 = 도움말 3367684 「Copyright issues with live streams」 — 사용권이 있어도 권리자 Content ID 허용 목록에 채널이 없으면 방송이 중단될 수 있음(신뢰도 상).
- ElevenLabs = 도움말 「Can I publish the content I generate on the platform?」·요금 문서 — 무료 등급 결과물 = 비상업 + 출처 표기(신뢰도 상 · 음악(Eleven Music) 약관 표는 서로 엇갈려 스킬에 숫자·등급을 박지 않음).
- 유튜브 LUFS 숫자 = 공식 도움말에 없음(11-14 상업 기준 조사 `sources/commercial-standards.md` §0-3·§3-3 · 「Stable volume」 문장뿐) → −14 는 **3자 관행** 표기. 실제 최고점 −1 dBTP = EBU R128 공식 상한.

## 처분표 (43건)

말 풀이: **①** = 팩(cysr 업데이트) 반영 여부 · **②** = 초보 사용자 유익 · **확신도** = 이 좌석이 다시 잰 뒤의 값(원 제안의 확신도와 다를 수 있음).

| # | 스킬 | 제안 요지 | 지금도 맞는가(실측 명령 → 결과) | 처분 | 이유 | ① 팩 | ② 초보 유익 | 확신도 |
|---|---|---|---|---|---|---|---|---|
| A1 | narrated-motion | say 목소리 = 사용권상 공개본 불가 명시 | `grep -n say narrated-motion/SKILL.md` → :42 「macOS say … 무료 기본」 · :90 「초안·내부용 품질」 = 사용권 언급 0 · License.html 67줄 원문 확인 | **반영** | 기본 엔진이 say 라 초보가 그대로 게시·상영할 수 있음. 1차 원문으로 확인됨 | 반영(:42 다음 1줄 · :90 문구) · 설명(:3)은 안 바꿈 | **결정적** — 모르고 약관 위반 게시를 막음 | 상 |
| A2 | narrated-motion | edge 엔진 = 비공식 · 약관 위험 · 403 | :42 개인정보 경고만 있음(지적 자체는 맞음) | 안 함 | 「약관상 위험」·「2024-10 403」은 우리 조사 판정·3자 기록이고 이번에 1차 원문 미확인. edge 는 「설치돼 있을 때만」 쓰는 선택 엔진. A1 반영문이 「공개본은 사람 녹음이나 사용권 확인한 목소리」로 이미 공개본을 막음 | 안 함 | 보통(선택 엔진) | 중상 |
| A3 | video-report-deck | say·ElevenLabs 무료 = 공개본 불가 | :40 「맥 전용 대체 수단」만 · 사용권 0 · ElevenLabs 도움말 확인 | **반영** | 발표장 상영·게시가 이 스킬의 주 용도 | 반영(:40 다음 1줄) · 설명 안 바꿈 | **결정적** | 상 |
| A4 | voice-clone-elevenlabs | 무료=비상업 · 클론 동의 · 출처 표시 유지 · 자기 목소리 예외 | `grep 동의` = 0건 | **반영(①②)** | 남의 목소리 무단 복제는 법·약관 양쪽 위험. ③(출처 표시 삭제 금지 §10)은 이번에 원문 미확인이라 뺐고, ④(유튜브 「자기 목소리 복제 = 공개 불필요」)도 원문 미확인이라 뺐다 | 반영(「키·도구」 끝 ①②) | **결정적** | 상 |
| A5 | audio-post · audio-post-mix | −14 LUFS 를 「유튜브 타깃」(공식처럼) 적음 → 근거 표기 · 목적지별 분리 | audio-post :24 · mix :19 「유튜브 타깃(약 -14 LUFS …)」 그대로 | **반영(근거 표기만)** | 값은 유지(납품 기준과 같음) · 「업계 관행값 · 유튜브 공식 숫자 없음」 + 「−1 dBTP = EBU R128 공식」 표기. ⚠ 원 제안의 「예배당 −23 따로」는 master 결정(11-14 · nonce cac7d9e2 · 한 마스터 −14)으로 대체 → 목적지별 분리 안 함. mix 설명(frontmatter)의 「유튜브 라우드니스 타깃」 문구는 설명 예산 보호로 안 바꿈 | 반영 | 큼(근거를 잘못 믿지 않게) | 상 |
| A6 | audio-post-mix | 정규화 실행법 없음 → loudnorm 2회 + ebur128 확인 + 덕킹 명령 | `grep loudnorm` = 0건 · 실측: 사인파 −47.85 LUFS → loudnorm 2회 → `ebur128` **−13.9 LUFS** | **반영** | 수치만 있고 할 줄 모르면 초보는 못 함. 명령을 직접 돌려 확인. zsh 에서 `$th:linear` 가 `:l` 수식어로 깨지는 함정을 실제로 밟아 한 줄 덧붙임 | 반영(절차 3 아래) | **결정적** | 상 |
| A7 | video-verify-audio-sync | 목표 크기 검사 빠짐(믹스는 검증에 미루고 검증은 급변만 봄) | :16 「레벨 일관」만 · `grep ebur128` = 0 | **반영** | 두 스킬 사이 빈칸 — 아무도 목표 수치를 안 봄 | 반영(점검 항목 1개) | 큼 | 상 |
| A8 | audio-post | 설명에 「효과음」 → sfx-place 와 충돌 | 지금 목록 설명(:3) = 「영상 배경음악을 마련하고 …」 — **효과음 없음**(skill-fold 가 축소). 「효과음」은 :34 「원 설명」 보존 절에만 | 안 함(이미 해소) | 발동에 쓰이는 목록 설명에서 이미 빠짐. 보존 절은 원문 기록이라 손대지 않음 | — | — | 상 |
| A9 | audio-post-music | 소스 우선순위 재배열 · Content ID · 생성 음악 등급 · 장부 칸 | `grep "Content ID"` = 0건 · 우선순위 1 = 생성 음악 그대로 | **반영(일부)** | 반영 = ⚠ 실시간 방송 중단 위험(도움말 3367684) · 생성 서비스 등급별 상업 허락 확인(ElevenLabs 무료 예) · `music-license.json` 칸 `content_id_registered`·`ai_generated`. 안 함 = 우선순위 재배열·「오디오 보관함 CC BY = claim 안 걸림」·「Pixabay 방패」·「Incompetech 전곡 등록」(이번 원문 미확인) · 생성 음악 순위 = B1(돈) | 반영(⚠ 1문단 + 계약 칸) | **결정적**(라이브 중단은 되돌릴 수 없음) | 상(반영분) |
| A10 | sfx-place | `sfx_local` 「항상 가용」 = 실물 없음 | 카탈로그 `sfx_local` = 경로·probe 없음(`supports: {}`) · 팩에 음원 파일 0(`find … -iname '*.wav' …`) · `javis_select` 는 그래도 sfx_local 을 고름 | **반영** | 「항상 가용」을 믿고 시작하면 음원이 없어 막힘. 대안(권리 있는 폴더 지정 · ffmpeg `sine`·`anoisesrc`·`afade` 합성 — 필터 3개 실재 확인) | 반영 | **결정적** | 상 |
| A11 | motion-graphics-prompt | 받은 음원의 Content ID 확인(라이브 중계) | :62 배경음 줄에 경고 0 | **반영(일반화)** | 「예배 중 상영」 → 「유튜브 실시간 방송(행사 중계 등)에 실리면」. 근거 도움말 3367684 | 반영 | 큼 | 상 |
| A12 | narrated-motion | `../tools/seek_render.js` 없음 | 지금 :9·:60·:68·:75·:81·:88 = `<M>/tools/…`(형제 스킬 motion-graphics-prompt) · `ls motion-graphics-prompt/tools` = seek_render.js·ref_frames.sh 실재 | 안 함(이미 해소) | 2307 승격 때 고쳐짐(HANDOFF-1116 3번) | — | — | 상 |
| A13 | motion-graphics-prompt | `../ppt-design-system/COMMON.md` 상대 경로 | `grep COMMON.md` = 0건 · :45 는 「`ppt-design-system`·`ppt-styles` 스킬의 색·글꼴」(스킬 이름) | 안 함(이미 해소) | 팩 판은 경로 대신 스킬 이름으로 가리킴 | — | — | 상 |
| A14 | sfx-place · scene-cut · transcription · caption-align · caption-correct · video-stitch · video-stitch-compositing · video-verify-timing | `javis_select`·`javis_params`·`caption_shape.py`·`check_timeline.py` = PATH 명령 아님 | `which javis_select javis_params` = not found · 팩 `bin/` 에 4파일 실재 · 하위 명령 `--help` 확인(rank / validate-defs·defaults·coerce / shape / validate·fps·check·boundaries) | **반영** | 그대로 치면 실패. 모두 `python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/<도구>.py"` 로. video-stitch 스키마 경로도 전체 경로(`schemas/edit_decisions.schema.json` 실재). **고친 명령을 스킬 본문에서 그대로 떼어 실행** → scene-cut·sfx-place rank 정상 출력 · check_timeline usage 출력 | 반영(8파일 12곳) | **결정적** | 상 |
| A15 | transcription · caption-align | whisperx 「항상 가용」 = 미설치면 미가용 · whisper-cli 길 없음 | `python3 -c "import whisperx"` = ModuleNotFoundError · `javis_select.py rank --capability transcription` = 「[미가용] transcriber_whisperx … 미설치」 · `which whisper-cli` = /opt/homebrew/bin/whisper-cli | **반영(일반화)** | 「이 맥」이 아니라 「whisperx 가 설치돼 있을 때만 가용 · 없으면 whisper.cpp(`whisper-cli`)를 직접(카탈로그 미등록 · 수동 · 단어 시각은 따로 확인)」. 카탈로그 등록은 B6 | 반영 | 큼 | 상 |
| A16 | transcription | `$(dirname "$0")` 경로 · 로컬 파일 = NotImplementedError | :53 그대로 · `bin/transcribe_channel.py` 159~162줄 `raise NotImplementedError` · 207줄에서 잡아 코드 1 | **반영** | 문서 안 `$0` 은 아무것도 안 가리킴 → 팩 전체 경로. 로컬 파일·자막 없는 URL 은 글루가 전사 안 하고 코드 1로 끝남을 명시 | 반영 | **결정적** | 상 |
| A17 | caption-correct | `correct_align_local` 실행 파일 없음 | `grep -rln correct_align_local cysjavis-pack/bin cysjavis-pack/skills` = SKILL.md 1건뿐 · 카탈로그 항목에 probe 없음 | **반영** | 「항상 가용」을 믿으면 없는 도구를 찾음 → difflib 스크립트를 작업 폴더에 남겨 돌리라고 명시 | 반영 | 큼 | 상 |
| A18 | voice-local · media-gen-image | 없는 문서 3곳을 가리킴 | voice-local :13 `[[voicebox-upgrade-research]]`·`_research/Voicebox_박사급…` · media-gen-image :44 `_work/vimax-w0/…/BESTOF2_GATE_DESIGN.md` — 팩에 셋 다 없음 | **반영** | 팩 사용자 기기에는 절대 없는 경로 → 「팩에 없다」로 표기 | 반영 | 보통(헛걸음 방지) | 상 |
| A19 | voice-local | 실제 설치·측정 기록(작업 폴더 venv) 가리키기 | 지적은 맞음(폴더 = SKILL.md 1장) | 안 함 | 가리킬 곳이 우리 작업 폴더(`~/axdev/workers/…`) — 팩 사용자에겐 없음 · 팩 부적합 | 안 함 | 없음(팩 사용자) | 상 |
| A20 | video-stitch-captions | 이 ffmpeg 엔 굽기 필터 없음 · 무료 시각 원천 없음 | `ffmpeg -hide_banner -filters \| grep -cE " (subtitles\|ass\|drawtext) "` = **0** · :15 원천 = ElevenLabs 하나 · video-report-deck `bin/build.py` 에 `mov_text` 실재 | **반영(일반화)** | 「빌드에 따라 없다 → 먼저 확인 명령 → 없으면 HTML 장면에서 그리기 / mov_text 트랙」 + 원천에 `captions.json`·`cues.json` 추가 | 반영 | **결정적**(굽기 단계에서 막힘) | 상 |
| A21 | motion-graphics-prompt | 「이 스킬」↔「narrated-motion」 정반대 | 지금 :28 「내레이션이 **이미 있고** … 이 스킬」 · :29 「대본·주제만 받아 **처음부터** … narrated-motion」 = 서로 맞음 | 안 함(이미 해소) | 2307 최신화로 갈래가 정리됨. 덧붙여 :64 의 「맥의 say」에 사용권 괄호 1개만 넣음(A1 연동) | (A1 연동 1곳) | — | 상 |
| A22 | script-writer | 「≤60초」 구식 기준 잔존 | :19·:35 「≤60초」 · voice-prep :12 「"60초"는 구식」 | **반영** | 대표 스킬만 옛 기준 — 하위 스킬과 모순. voice-prep 산출(`prev_text`/`next_text`) 기준으로 맞춤 | 반영 | 큼 | 상 |
| A23 | caption-align | 역할 설명이 틀림(video-stitch-captions 는 검사만이 아님) | 지적은 맞음(captions :15 「단어 그룹 경계를 만든다」) · 그 문장은 :92 「원 설명」 보존 절에만 있음 · 목록 설명엔 없음 | 안 함 | 발동에 안 쓰이는 보존 원문 · 유익이 결정적이지 않음 | 안 함 | 작음 | 상 |
| A24 | voice-local | 한국어 4종 측정·사용권 칸·「여러 번 뽑아 고르기」 | :17 「미수행」 그대로 · `grep Supertonic` = 0 | 안 함 | 측정 = 짧은 2문장 · 한 기기 · 귀 평가 아님 → 팩 전체에 엔진 표로 굳히기엔 근거 얕음. 「매번 다르게 나온다」는 같은 스킬의 「시드·설정 잠금」 서술과 충돌 → 시드를 잠근 조건에서 다시 재야 함. 엔진 선택은 B4(돈) 결정 뒤 | 안 함 | 보통 | 중 |
| A25 | media-gen-video | 기본 모델 문구 낡음(순위) · Kling 약관 | :20-21 그대로 | 안 함 | 순위는 날마다 변함(11-14 한 번 조회) · fal 경유 Kling 약관 미확인 · 창구 결정 B2 와 묶임 | 안 함 | 보통 | 중 |
| A26 | media-gen | AI 공개(변경·합성 콘텐츠) · C2PA 자동 라벨 | `grep -E "C2PA\|합성 콘텐츠"` = 0건 · 도움말 14328491 확인 | **반영** | 실사 같은 생성 장면 게시는 공개 의무 · 미공개 반복 시 제재 가능(도움말). 원 제안의 「썸네일 = 예외」는 원문 미확인이라 「대본·아이디어 같은 제작 보조」로 바꿔 적음 | 반영(공통 운영 기법 1줄) | **결정적** | 상 |
| A27 | media-gen-edit | 실존 인물 얼굴 사진 업로드 막음 | `grep 실존` = 0건 · :16 업로드 절차만 | **반영(일반화)** | 「교인·박사님 게이트」 → 「남의 얼굴 실존 인물 사진은 그 사람 동의 기록 없이 외부 서비스에 올리지 않음」(0단계) | 반영 | **결정적**(남의 개인정보) | 상 |
| A28 | video-verify-final-gate | 출고 서류 4종(사용권·크기·라이브 음악·AI 공개) 없음 | `grep -E "사용권\|LUFS"` = 0건 | **반영** | 마지막 관문이 사실성만 봄 → 사용권·크기·라이브 음악·AI 공개 중 하나라도 비면 NO_GO. 출력 계약에 `release_docs` 칸 | 반영 | **결정적** | 상 |
| A29 | youtube-video-pipeline · heygen-avatar-render | 업로드 설정 7단계 · 디지털 트윈 동의 | pipeline 업로드 단계 0 · heygen :26 동의 0 | **반영(일부)** | 반영 = heygen 「디지털 트윈은 동의 기록이 있을 때만 · 하지 않은 말을 하는 영상 = AI 공개 대상(도움말 14328491)」. 안 함 = pipeline 7단계 신설(파이프라인 구조 변경 · 같은 검사를 A28 final-gate 출고 서류가 이미 함) | 반영(heygen 1줄) | 큼 | 상(반영분) |
| A30 | video-stitch-captions | 글꼴 사용권(맥 내장 글꼴 §2E) · 투사 최소 글자 크기 | 지적 자체는 맞음(:19 폰트 사용권 0) | 안 함 | §2E 가 영상에 **래스터로 찍힌 글자**까지 막는지는 해석이 갈림(임베딩 조항 해석) · 최소 글자 크기 「×1.5 와 56px」은 우리 가정값 | 안 함 | 보통 | 중 |
| A31 | scene-cut | 검은 배경 영상에서 장면 전환 0건 함정 · PySceneDetect 미설치 | 실측(스크래치): 빨강→파랑 전체 색 컷 = 최고 점수 **0.40**(>0.3 검출 1건 · 양성 대조) · 검은 배경 위 흰 상자 위치 컷 = 최고 **0.09**(검출 0건) · `import scenedetect` = ModuleNotFoundError | **반영** | 다시 재서 확신도 상으로 올림. 대안(160×90 회색 프레임 차이) = 팩 안 `narrated-motion/tools/s2m_sync_check.py` 와 같은 방식 → 팩 안 경로만 가리킴 | 반영 | 큼(모션그래픽 편집점 0건 오판 방지) | 상 |
| A32 | cost-preview-confirm | 구독 크레딧 차감도 비용 규약에 | `grep 크레딧` = 0건 · 규약 = 종량제만 | **반영** | 「구독이니 공짜」로 착각해 다시 뽑기로 크레딧을 태우는 것을 막음. 상한 숫자는 박지 않고 `run-cost.json` `budget` 칸으로 | 반영(규약 6번 · 적용 대상) | **결정적**(돈) | 상 |
| A33 | voice-clone-elevenlabs | 설명에 「종량제·키 필요」 | 목록 설명은 skill-fold 로 이미 바뀜(「대본을 ElevenLabs 클론 음성으로 … 「보이스 클론 / 일레븐랩스 / 나레이션 음성 합성」」) · 「종량제」 없음 | 안 함 | 키가 없으면 deny-by-default 로 멈추고, 있어도 `cost-preview-confirm` 이 돈 전에 막음 → 유익이 결정적이지 않음. 설명 변경 = 예산·발동 회귀 비용 | 안 함 | 작음 | 중상 |
| A34 | script-writer-factcheck · video-verify-final-gate · script-writer · caption-correct | `[[hallucination-guard]]` = Skill 목록에 없음 | `ls ~/.claude/skills/hallucination-guard`·`~/.cys/claude/skills/hallucination-guard` = 없음 · preflight `WORK_SKILLS` 는 실재만 검사하고 링크 안 함(C22) · `cys skill show hallucination-guard` = 본문 출력 확인 | **반영** | 검증 엔진을 못 열면 사실 관문이 빈다 → 「`cys skill show hallucination-guard` 로 연다」 병기. 링크를 새로 거는 것은 팩 배선 변경이라 안 함 | 반영(4파일) | 큼 | 상 |
| A35 | video-verify · script-writer-factcheck | 「800k 채널」 원본 맥락 잔재 | :10 · :9 그대로 | 안 함 | 동작 무관 문구(원 제안 확신도 하) — 대원칙 「표현·문구 고치기가 아니다」 | 안 함 | 없음 | 상(사실) |
| B1 | audio-post-music | 생성 음악(Suno·ElevenLabs Music)을 1순위로 둘지 | — | **박사님께** | 돈(유료 구독·단체 등급) | 결정 뒤 | — | 중 |
| B2 | media-gen · media-gen-video · cost-preview-confirm | 생성 영상 창구 확장(힉스필드 구독) | — | **박사님께** | 돈 + 새 길(「fal 하나」 원칙과 다름) | 결정 뒤 | — | 중 |
| B3 | media-gen | Firefly 크레딧 길 추가 | — | **박사님께** | 새 길 · 크레딧 추가 구매 = 돈 | 결정 뒤 | — | 중상 |
| B4 | voice-clone-elevenlabs · voice-local · narrated-motion | 공개본 목소리 = 유료(타입캐스트·ElevenLabs) vs 사람 녹음·로컬 | — | **박사님께** | 돈. 그 전까지 스킬엔 「공개본 = 사람 녹음 또는 사용권 확인한 목소리」만(A1·A3 반영문) | 결정 뒤 | — | 중 |
| B5 | narrated-motion(tools/s2m_cues.py) | 큐마다 바깥 wav 를 넣는 `engine: file` | `s2m_cues.py:53` 「엔진은 say \| edge 만」 그대로 | 안 함 → 📌 master 결정 | 새 기능(돈 0) — 이 티켓은 「문서 반영」 범위. A1 로 공개본을 막았으니 **공개본을 만들 도구 길이 비어 있음** → 다음 티켓 1순위 권고 | 결정 뒤 | 큼 | 중상 |
| B6 | transcription · caption-align(카탈로그) | whisper.cpp 를 카탈로그 공급자로 | `javis_select … transcription` = whisperx 미가용 → ytdlp_subs | 안 함 → 📌 master 결정 | 새 기능 · 팩 카탈로그 = 고위험 편성 | 결정 뒤 | 큼 | 중 |
| B7 | video-verify · narrated-motion · motion-graphics-prompt | 보고서 폴더의 검사 도구 5종을 스킬 자산으로 | 도구는 `master/reports/…/stack-samples/tools/` | 안 함 → 📌 master 결정 | 새 기능 · 도구가 master 자산 쪽 · 알려진 한계(검은 화면 FAIL 미판정 등) | 결정 뒤 | 보통 | 중 |
| B8 | video-report-deck | JetBrains Mono 글꼴 동봉 | `tokens.css:29` `--mono: "JetBrains Mono", "SF Mono", …` · 팩에 woff2 0 | 안 함 → 📌 master 결정 | 라이선스 원문(OFL 1.1 로 알려짐) 미확인 · 팩 크기 증가 · 다른 기기 SF Mono 폴백 | 결정 뒤 | 작음 | 중 |

## 스킬 밖 항목 (브리프 5·6번 · 원문 §6·§3)

| 항목 | 처분 | 내용 |
|---|---|---|
| 기억 카드 `reference_macos-system-voices-no-public-use` 「License.html 40줄 §2F」 | **master 몫**(기억 쓰기) | 이번 실측 = **67줄**(`sed -n 67p …/License.html` = 「F. Voices; Live Captions …」) |
| 기억 카드 `reference_korean-local-tts-mac-measured-2026-11` 「Supertonic3 글자틀림 0/8」 | **master 몫** | 독립 검증 V2:85 = **6파일**(이 좌석은 다시 재지 않음 · 원문 인용) |
| `tools/screening_master.sh`(기본 −1.5 dBTP)·`screening_qc.sh`(기본 −16 LUFS · −1 dBTP) 기본값 | **제안만**(master/assets 쪽 · 이 가지에서 안 고침) | 기본값을 납품 기준으로 바꾸기 권고. ⚠ **기준값 확인 필요**: 브리프는 「−14 LUFS · **−1** dBTP」라 적었으나 `workflow-checklist.md` 42~43·61줄 납품 기준은 「−14 LUFS ±1 · **−2** dBTP 이하(ATSC −2 · EBU −1 둘 다 만족)」 → −2 로 맞추는 것이 권고. 스킬(A5 반영문)은 팩 일반 사용자용이라 「−1 dBTP = EBU 공식 상한 · 납품처 값이 있으면 그 값」으로 두었다 |
| 팩 카탈로그 `pixabay_music` 「royalty-free commercial · no key」 | 안 함 | Content ID 방패 곡·계정 필요 여부 미확인(원문 §6-3) · 카탈로그 = 팩 배선 |
| D3 video-stitch 「자막」 발동어 좁히기 | 안 함 | 설명 변경 · 동작 시험 없음(원문 확신도 중) |
| D6 싱크 허용폭 ±0.3 ↔ ±0.2 | 안 함 | 원문도 「모순 아님 · 고치지 않음」 |
| §3 참고 관찰(목록에서 설명이 빠진 스킬 14개) | 안 함(이 티켓 밖) | skill-fold(1.1.12)가 설명을 줄이고 하위 스킬을 수동 전용으로 바꿔 지금 구조가 다름 · 1.1.16 좌석 실측은 HANDOFF-1116 예산표 참고 |

## 시험 결과 (반영 커밋 1d11445d5 위)

| 시험 | 결과 |
|---|---|
| `python3 scripts/asset_ledger_check.py` | ✓ 초록 — 원천 139개 전부 판정표에 있음 · 판정표 140줄 |
| `python3 scripts/tests/test_asset_ledger_check.py` | OK |
| `python3 cysjavis-pack/bin/tests/run_bootstrap_health.py --only H-ASSET-1` | GREEN 1 PASS / 0 FAIL |
| `cd cysjavis-pack/bin/tests && CYS_NO_AUTOSTART=1 python3 -m unittest test_output_skills` | 18 tests OK |
| `cargo test --lib -- pack_skills_embed_adopted_set_and_indexable install_writes_core_and_skills_to_fresh_dir skill_links_only_pack_targets_removed` | 3 passed |
| `python3 cysjavis-pack/bin/javis_registry.py --root cysjavis-pack build` → `verify` | build 124 · problem 0 · 카탈로그 diff 0 · verify OK 124 |
| 설명 변경 | `git diff 1ff82d08a -- cysjavis-pack/skills \| grep -c '^[-+]description:'` = **0** → 예산(≈15,662/30,000)·발동 낱말 불변 |
| 앞머리 YAML | 고친 26개 전부 정상. (korean-humanizer 1개가 `yaml.safe_load` 실패 — 이 가지가 안 건드린 기존 상태 · `git diff --quiet` 확인) |
| 고친 명령 실행 | scene-cut·sfx-place 의 rank 명령을 본문에서 그대로 떼어 실행 → 정상 출력 · `check_timeline.py --help` 정상 |
| 스킬 문구를 고정한 시험 | 고친 문구(「항상 가용」·「≤60초」·「유튜브 타깃」 등)를 잡는 시험 0건(`grep -rnE` · py/rs/sh) |
| 개인 정보 | 추가 줄에 `axdev`·`박사님`·`oogisoogi`·`교회`·`예배` 0건 |

## 고치기 전/뒤 (스킬별 · `git diff -U0 1ff82d08a 1d11445d5` 에서 기계 추출)


### audio-post-mix


`-19 +19`

- 전: - **라우드니스**: 최종 통합 라우드니스를 유튜브 타깃(약 -14 LUFS, true peak ≤ -1 dBTP)으로
- 뒤: - **라우드니스**: 최종 통합 라우드니스를 약 -14 LUFS, 실제 최고점(true peak) ≤ -1 dBTP 로

`-20,0 +21,3`

- 뒤: - -14 LUFS 는 유튜브 등 스트리밍의 **업계 관행값**이다 — 유튜브 공식 도움말에는 LUFS 숫자가 없다
- 뒤: (「안정적인 볼륨」 설명뿐 · 2026-11 확인). 최고점 -1 dBTP 는 EBU R128 의 공식 상한이다.
- 뒤: 납품처가 다른 값을 정해 주면 그 값을 따른다.

`-26,0 +30,9`

- 뒤: - 실행 = ffmpeg `loudnorm` 2회. 1회째는 재기만 한다:
- 뒤: `ffmpeg -i mix.wav -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null -`
- 뒤: → 출력 JSON 의 `input_i`·`input_tp`·`input_lra`·`input_thresh` 를 2회째의
- 뒤: `measured_I`·`measured_TP`·`measured_LRA`·`measured_thresh` 에 넣고 `linear=true` 를 붙여 실제로 바꾼다.
- 뒤: (zsh 에서는 변수 뒤에 `:` 가 오면 `${변수}` 로 감싼다 — `$th:linear` 는 `:l` 수식어로 깨진다.)
- 뒤: - 확인 = 결과를 `ffmpeg -i out.wav -af ebur128=peak=true -f null -` 로 다시 재서 요약의 `I:`(통합 LUFS)·
- 뒤: `Peak:`(실제 최고점)가 목표 안인지 **숫자로** 기록한다.
- 뒤: - 덕킹(사이드체인) 예: `ffmpeg -i bgm.wav -i narr.wav -filter_complex "[1]asplit[n1][n2];[0][n1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[d];[d][n2]amix=inputs=2:normalize=0[m]" -map "[m]" mix.wav`
- 뒤: (motion-graphics-prompt 와 같은 명령).

### audio-post-music


`-20,0 +21,6`

- 뒤: ⚠ **사용권이 있어도 막힐 수 있다**: 유튜브 실시간 방송(라이브)은 Content ID 에 등록된 곡이면
- 뒤: 사용권을 가졌어도, 권리자가 그 채널을 허용 목록(allowlist)에 올리지 않았을 때 방송이 중단될 수 있다
- 뒤: (유튜브 도움말 3367684 「Copyright issues with live streams」). 올린 영상도 자동 클레임이 걸릴 수 있다.
- 뒤: → 곡마다 Content ID 등록 여부를 확인해 기록한다. 생성 음악·음성 서비스는 등급마다 상업 사용 허락이
- 뒤: 다르다(예: ElevenLabs 무료 등급 = 비상업 · 출처 표기) → 쓰는 등급의 약관을 확인해 기록한다.
- 뒤: 

`-30 +36,2`

- 전: `audio/music-bed.mp3` + `audio/music-license.json`(소스·라이선스·프롬프트). 상위
- 뒤: `audio/music-bed.mp3` + `audio/music-license.json`(소스·라이선스·프롬프트·`content_id_registered`(예/아니오/모름)·
- 뒤: `ai_generated`). 상위

### audio-post


`-24 +24`

- 전: 유튜브 라우드니스 타깃(약 -14 LUFS 통합) 정규화.
- 뒤: 라우드니스 목표(약 -14 LUFS 통합 — 스트리밍 업계 관행값 · 유튜브 공식 도움말에는 LUFS 숫자가 없다) 정규화.

### caption-align


`-28 +28`

- 전: javis_select rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \
- 뒤: python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_select.py" rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \

`-33 +33`

- 전: 모델 재사용). 키가 없어도 항상 가용 — 자막 정렬은 키 없이 동작한다.
- 뒤: 모델 재사용). 키는 필요 없지만 파이썬 `whisperx` 가 설치돼 있을 때만 가용(없으면 javis_select 가 미가용으로 건너뛴다).

`-65 +65`

- 전: python3 caption_shape.py shape --input transcript.json --out captions.json \
- 뒤: python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/caption_shape.py" shape --input transcript.json --out captions.json \

`-72 +72`

- 전: - 파라미터는 frontmatter `cys.params`(ParamDefinition)로 선언 — 호출 전 `javis_params coerce`로
- 뒤: - 파라미터는 frontmatter `cys.params`(ParamDefinition)로 선언 — 호출 전 `python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_params.py" coerce`로

### caption-correct


`-29 +29`

- 전: javis_select rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \
- 뒤: python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_select.py" rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \

`-34 +34,3`

- 전: ASR 토큰을 정렬해 대본 철자를 ASR 타이밍 위로 전사(轉寫)한다. 키 없이 항상 가용. **토큰 소비 0
- 뒤: ASR 토큰을 정렬해 대본 철자를 ASR 타이밍 위로 전사(轉寫)한다. 키는 필요 없다.
- 뒤: ⚠ 단 팩에는 이 항목의 실행 파일이 없다(카탈로그 항목뿐 · 2026-11 확인) → python `difflib` 정렬 스크립트를
- 뒤: 작업 폴더에 파일로 남겨 돌린다(같은 입력 → 같은 결과 · 정정 전후 타임스탬프 diff 0 확인도 그 스크립트로). **토큰 소비 0

`-70 +72`

- 전: - **추측 교정 금지**: 동음이의가 대본에 없으면 ASR 원문 유지. `hallucination-guard`로 정정 근거를
- 뒤: - **추측 교정 금지**: 동음이의가 대본에 없으면 ASR 원문 유지. `hallucination-guard`(`cys skill show hallucination-guard`)로 정정 근거를

### cost-preview-confirm


`-27,0 +28,4`

- 뒤: 6. **구독 크레딧도 같다** → 검증: 월 구독이라도 호출(다시 뽑기 포함)마다 크레딧이 빠지는 서비스는 돈이
- 뒤: 나가는 호출로 친다. 호출 전 『남은 크레딧 · 이번 차감 · 상한』을 한 줄로 보이고 상한을 넘으면 멈춘다.
- 뒤: 자동 충전이 꺼져 있는지 처음 한 번 확인. 상한 숫자는 이 문서에 박지 않고 `run-cost.json` 의 `budget`
- 뒤: 칸으로 받는다(사용자가 정한 값).

`-32 +36`

- 전: `[[media-gen]]` 계열(장/초당) · `[[audio-post]]`(생성 음악) · 업스케일 등 모든 유료 단계.
- 뒤: `[[media-gen]]` 계열(장/초당) · `[[audio-post]]`(생성 음악) · 업스케일 · 크레딧 차감형 구독 서비스 등 모든 유료 단계.

### heygen-avatar-render


`-26,0 +27,2`

- 뒤: - ⚠ 실제 사람의 디지털 트윈(얼굴·목소리)은 **그 사람의 동의 기록이 있을 때만** 만든다. 실존 인물이 하지 않은
- 뒤: 말을 하는 것처럼 보이는 영상은 유튜브 AI 공개 대상이다(도움말 14328491 「real person … say or do」).

### media-gen-edit


`-15,0 +16,2`

- 뒤: 0. ⛔ **실존 인물 사진** → 검증: 남의 얼굴이 나온 실존 인물 사진은 그 사람의 동의 기록 없이 외부 서비스에
- 뒤: 올리지 않는다(올린 사진이 서비스 쪽에 남는다). 참조는 가상 인물·사물·직접 만든 그림·동의받은 사진만.

### media-gen-image


`-44 +44`

- 전: append. N=2 고정(3장 이상 금지 — 선택 노이즈). 상세 설계=`_work/vimax-w0/b4_bestof2/BESTOF2_GATE_DESIGN.md`.
- 뒤: append. N=2 고정(3장 이상 금지 — 선택 노이즈). (상세 설계 문서는 팩에 없다 — 위 규칙이 전부다.)

### media-gen


`-45,0 +46,5`

- 뒤: - **AI 공개(유튜브)**: 실제 사람·장소·사건처럼 보이는 생성 장면을 유튜브에 올리면 업로드 때 「변경되거나
- 뒤: 합성된 콘텐츠」 질문에 『예』로 답한다(유튜브 도움말 14328491 · 공개만으로 시청자층·수익 창출 자격에
- 뒤: 영향 없음). 만화·완전한 애니메이션처럼 실제 같지 않은 그림과 대본·아이디어 같은 제작 보조는 대상이 아니다.
- 뒤: 파일에 C2PA(출처 표시) 정보가 있으면 유튜브가 라벨을 자동으로 붙일 수 있다. `media/manifest.jsonl`
- 뒤: 기록에 `realistic: true/false` 를 남겨 업로드 판단에 쓴다.

### motion-graphics-prompt


`-62,0 +63`

- 뒤: - ⚠ 이 영상이 유튜브 실시간 방송(행사 중계 등)에 실리면: 받은 음원이 Content ID 에 등록돼 있으면 사용권이 있어도 권리자 허용 목록에 채널이 없을 때 방송이 중단될 수 있다(유튜브 도움말 3367684). → 음원 출처·등록 여부를 묻고 `audio-post-music` 기준으로 확인한다. 코드로 만든 소리는 이 위험이 없다.

`-64 +65`

- 전: - 음성은 `voice-local` 스킬(또는 맥의 `say`)로, 자막 시각은 문장별 합성 길이(또는 `transcription` 스킬)로 정한다 — 들은 느낌으로 시각을 적지 않는다.
- 뒤: - 음성은 `voice-local` 스킬(또는 맥의 `say` — 사용권 §2F 상 개인·비상업 시안 전용 · 공개본은 다른 목소리)로, 자막 시각은 문장별 합성 길이(또는 `transcription` 스킬)로 정한다 — 들은 느낌으로 시각을 적지 않는다.

### narrated-motion


`-42,0 +43`

- 뒤: - ⚠ **say 목소리는 공개본에 쓰지 않는다(사용권)**: macOS 사용권 계약 §2F 는 시스템 음성을 「개인적·비상업적」 작품에만 허락한다(`/Library/Documentation/License.lpdf/Contents/Resources/English.lproj/License.html` 67줄 「for your personal, non-commercial use」 · 「No other creation or use of the System Voices … is permitted」). → 유튜브 게시·행사 상영 같은 공개본은 사람 녹음이나 사용권을 확인한 목소리로 바꾼다. say 는 만드는 사람의 작업 시안까지.

`-90 +91`

- 전: - say 목소리는 「초안·내부용」 품질이다 — 대외 게시용 목소리(사용자 목소리 복제 등)는 비용 게이트를 거친 별도 결정.
- 뒤: - say 목소리는 「초안·내부용」이다(품질 + 사용권 §2F 두 가지 이유 · 위 「음성」 절) — 대외 게시용 목소리(사람 녹음 · 사용자 목소리 복제 등)는 비용 게이트를 거친 별도 결정.

### scene-cut


`-30 +30`

- 전: javis_select rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \
- 뒤: python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_select.py" rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \

`-36 +36,6`

- 전: - 콘텐츠 인지 shot-detect가 필요하면 `scenecut_pyscenedetect`(threshold/adaptive·로컬·무키).
- 뒤: - 콘텐츠 인지 shot-detect가 필요하면 `scenecut_pyscenedetect`(threshold/adaptive·로컬·무키 · 파이썬
- 뒤: `scenedetect` 가 설치돼 있을 때만 가용).
- 뒤: - ⚠ 함정: 배경이 대부분 검은 영상(모션그래픽 등)은 ffmpeg 장면 점수(`select='gt(scene,0.3)'`)가 작아
- 뒤: 전환을 0건 잡는다(실측 2026-11: 검은 배경 위 작은 흰 상자 위치가 바뀌는 컷 = 최고 0.09 · 빨강→파랑
- 뒤: 전체 색 컷 = 0.40). 이때는 160×90 회색 프레임의 이웃 차이가 문턱을 처음 넘는 프레임을 전환으로 본다
- 뒤: (같은 방식 = `narrated-motion/tools/s2m_sync_check.py`).

### script-writer-factcheck


`-12 +12`

- 전: 전담 검증 엔진은 `[[hallucination-guard]]`다. 이 스킬은 그 4문을 대본 문장 단위로 돌린다.
- 뒤: 전담 검증 엔진은 `[[hallucination-guard]]`다(팩 스킬이라 Skill 목록에 없을 수 있다 — 없으면 `cys skill show hallucination-guard` 로 본문을 연다). 이 스킬은 그 4문을 대본 문장 단위로 돌린다.

### script-writer


`-18,2 +18,3`

- 전: 3. `[[script-writer-factcheck]]` — 모든 단정 문장을 출처 대조로 검증한다(`hallucination-guard` 연결).
- 전: 4. `[[script-writer-voice-prep]]` — 대본을 ≤60초 음성 청크 경계로 분절한다.
- 뒤: 3. `[[script-writer-factcheck]]` — 모든 단정 문장을 출처 대조로 검증한다(`hallucination-guard` 연결 — `cys skill show hallucination-guard`).
- 뒤: 4. `[[script-writer-voice-prep]]` — 대본을 문장 경계 음성 청크로 분절한다(시간 상한 없음 — 「60초」는
- 뒤: 구식 기준 · 글자수 한도는 음성 단계가 본다).

`-35 +36`

- 전: ≤60초이고 자연스러운 경계(문장·구)에서 끊기는가.
- 뒤: 자연스러운 경계(문장·구)에서 끊기고 연속성 메타(prev/next)를 갖는가(시간 상한 없음 · voice-prep 기준).

### sfx-place


`-23 +23`

- 전: javis_select rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \
- 뒤: python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_select.py" rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \

`-27,2 +27,4`

- 전: - **무료·로컬 바닥**: `sfx_local`(로컬 SFX 라이브러리·무키·결정론). 키가 없어도 항상 가용 —
- 전: 효과음 배치는 키 없이 동작한다.
- 뒤: - **무료·로컬 바닥**: `sfx_local`(로컬 SFX 라이브러리·무키·결정론). 키는 필요 없다.
- 뒤: ⚠ 단 팩에는 효과음 음원 폴더가 없다(카탈로그 항목뿐 · 경로·검사 없음 · 2026-11 확인) → 쓰기 전에 권리를
- 뒤: 가진 음원 폴더를 지정하거나, ffmpeg 로 직접 합성한 효과음(`sine`·`anoisesrc` + `afade` 등)을 쓴다 —
- 뒤: 남의 저작물이 0 이라 사용권·Content ID 걱정이 없다.

### transcription


`-30 +30`

- 전: javis_select rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \
- 뒤: python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_select.py" rank --catalog "${CYS_PACK_DIR:-$HOME/.cys/pack}/round/video_provider_catalog.json" \

`-35 +35,3`

- 전: 키가 없어도 항상 가용(deny-by-default 통과) — 그래서 전사는 키 없이도 동작한다.
- 뒤: 키는 필요 없지만 **파이썬 `whisperx` 가 설치돼 있을 때만 가용**이다 — 없으면 javis_select 가
- 뒤: 「[미가용] … 'whisperx' 미설치」로 건너뛴다(2026-11 확인). 그때 기기에 whisper.cpp(`whisper-cli` +
- 뒤: ggml 모델)가 있으면 그것을 직접 돌려 전사할 수 있다(카탈로그 미등록 · 수동 · 단어 시각 출력은 따로 확인).

`-53 +55`

- 전: python3 "$(dirname "$0")/transcribe_channel.py" run \
- 뒤: python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/skills/transcription/bin/transcribe_channel.py" run \

`-64,0 +67,3`

- 뒤: - ⚠ 자막이 없는 URL·로컬 파일은 이 글루가 전사하지 않는다 — whisperx 가 배선돼 있지 않아 안내
- 뒤: (NotImplementedError 문구)를 찍고 코드 1로 끝난다(`bin/transcribe_channel.py` 159~162줄). 그때는 아래
- 뒤: 레시피(또는 whisper-cli)를 직접 돌린다.

### video-report-deck


`-40,0 +41`

- 뒤: - ⚠ 사용권: say 목소리는 macOS 사용권 §2F 상 「개인적·비상업적」 사용만 허락된다(기기의 `License.html` 67줄) → say 로 만든 영상은 만든 사람의 확인용까지. 발표장 상영·유튜브 게시 같은 공개본은 다른 목소리로 바꾼다. ElevenLabs 도 **무료 등급 결과물은 비상업 전용 + 출처 표기**다(ElevenLabs 도움말) → 공개본은 상업 사용이 허락된 유료 등급 키일 때만.

### video-stitch-captions


`-16 +16,2`

- 전: 단어 그룹 경계를 만든다(문자→단어 묶음).
- 뒤: 단어 그룹 경계를 만든다(문자→단어 묶음). ElevenLabs 를 안 쓴 경로면 `captions.json`
- 뒤: (`caption-align` · 단어 단위) 또는 `cues.json`(`narrated-motion` · 문장 단위)을 시각 원천으로 쓴다.

`-23,0 +25,4`

- 뒤: - ⚠ ffmpeg 빌드에 따라 굽기 필터(`subtitles`·`ass`·`drawtext`)가 없다(libass·freetype 없이 만든 판 ·
- 뒤: 예: 2026-11 맥 brew ffmpeg 9.0.1 = 셋 다 없음). 먼저 `ffmpeg -hide_banner -filters \| grep -E " (subtitles\|ass\|drawtext) "`
- 뒤: 로 확인한다. 없으면 ① HTML 장면 안에서 자막을 그려 렌더하거나(narrated-motion 방식) ② 별도 자막
- 뒤: 트랙(mp4 `mov_text` · video-report-deck 방식)으로 넣는다.

### video-stitch-compositing


`-49 +49`

- 전: 상수로 두고, 수치는 `javis_params`(W1-2)로 coerce해 범위-밖 차단.
- 뒤: 상수로 두고, 수치는 `javis_params`(팩 `bin/javis_params.py` · PATH 명령 아님 · W1-2)로 coerce해 범위-밖 차단.

### video-stitch


`-29 +29`

- 전: 실행 가능한 필드만 — GPU 전용(blend_mode·mask·shader uniform) 금지. `python3 check_timeline.py
- 뒤: 실행 가능한 필드만 — GPU 전용(blend_mode·mask·shader uniform) 금지. `python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/check_timeline.py"

`-46 +46`

- 전: **정전 입력** `edit_decisions.json`(에이전트 저작 IR — `schemas/edit_decisions.schema.json` 준수)을
- 뒤: **정전 입력** `edit_decisions.json`(에이전트 저작 IR — `${CYS_PACK_DIR:-$HOME/.cys/pack}/schemas/edit_decisions.schema.json` 준수)을

### video-verify-audio-sync


`-16,0 +17,3`

- 뒤: - **목표 크기**: 최종 파일을 `ffmpeg -i final/video.mp4 -af ebur128=peak=true -f null -` 로 재서 요약의
- 뒤: `I:`(통합 LUFS)·`Peak:`(실제 최고점)가 `[[audio-post-mix]]` 목표 안인가. 숫자를 evidence 에 남긴다
- 뒤: (믹스 스킬이 「레벨은 이 관문이 본다」고 넘기므로, 급변만 보고 목표 수치를 빠뜨리지 않는다).

### video-verify-final-gate


`-18 +18`

- 전: (`[[hallucination-guard]]` 기준 적용). **무근거 화면 텍스트 = NO_GO.**
- 뒤: (`[[hallucination-guard]]` 기준 적용 (팩 스킬이라 Skill 목록에 없을 수 있다 — 없으면 `cys skill show hallucination-guard` 로 본문을 연다)). **무근거 화면 텍스트 = NO_GO.**

`-21,0 +22,6`

- 뒤: - **출고 서류**(공개 게시·상영 전): (a) 사용권 근거 — 목소리(macOS say·무료 등급 결과물은 공개본 불가)·
- 뒤: 음악(`audio/music-license.json`)·글꼴·생성물(서비스 등급)마다 공개 사용을 허락하는 근거가 적혀 있나
- 뒤: (b) 크기 — `[[video-verify-audio-sync]]` 의 통합 LUFS·최고점 숫자가 목표 안인가 (c) 유튜브 실시간 방송에
- 뒤: 쓸 영상이면 음악이 Content ID 미등록이거나 허용 목록 근거가 있나 (d) AI 공개 — 실제 같은 생성 장면·
- 뒤: AI 음악·실존 인물처럼 보이는 아바타가 있으면 업로드 때 공개 『예』(유튜브 도움말 14328491).
- 뒤: 하나라도 비면 NO_GO.

`-31 +37`

- 전: `{gate: "final", verdict: GO\|NO_GO, fact_issues: [...], gates: {visual, timing, audio_sync}}`.
- 뒤: `{gate: "final", verdict: GO\|NO_GO, fact_issues: [...], release_docs: {license, loudness, live_music, ai_disclosure}, gates: {visual, timing, audio_sync}}`.

### video-verify-timing


`-23 +23`

- 전: `python3 check_timeline.py check final/timeline.json --probe final/video.mp4 [--fps N] --json`.
- 뒤: `python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/check_timeline.py" check final/timeline.json --probe final/video.mp4 [--fps N] --json`.

`-42 +42`

- 전: python3 check_timeline.py boundaries --input boundaries.json --fps <N> --tolerance-frames 1
- 뒤: python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/check_timeline.py" boundaries --input boundaries.json --fps <N> --tolerance-frames 1

### voice-clone-elevenlabs


`-24,0 +25,3`

- 뒤: - ⚠ 사용 조건(쓰기 전에 확인):
- 뒤: ① 무료 등급 결과물 = 비상업 전용 + 출처 표기(ElevenLabs 도움말 「Can I publish the content I generate」) → 공개·상업 게시본은 유료 등급에서만.
- 뒤: ② 클론은 **목소리 주인의 동의를 받은 기록**이 있을 때만(ElevenLabs 금지 사용 정책 — 남의 목소리를 동의 없이 복제 금지).

### voice-local


`-13 +13`

- 전: [[voicebox-upgrade-research]], 보고서 `_research/Voicebox_박사급_연구보고서.md`).
- 뒤: 보고서는 팩에 없다 — 원 작업 폴더 문서 · 아래 근거 줄 번호는 Voicebox 저장소 코드 기준).
