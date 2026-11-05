# DESIGN — 자산을 좌석 스킬로 (TICKET=asset-skills-for-seats · 【중간보고】 2026-11-06)

작성 = worker-assetskills(surface:1822) · 가지 feat/asset-skills ← 10802555
반영한 master 지시 = 브리프(원장 spawn 07:57:54) · 보강 master#f369eb9e · 덧붙임 master#f7f0e7bc(커밋 3fdb4b96) · 기준 개정 master#7a471ca4 — 넷 다 원장 대조 완료.

---

## 1. 실측 — 좌석은 스킬을 어디서 찾나

### 1-1. Claude Code가 스킬을 읽는 자리 (공식 문서 + 이 좌석 실측)

- 개인 스킬 폴더는 `$CLAUDE_CONFIG_DIR/skills`입니다. `~/.claude/skills`를 **대신하는** 자리입니다.
  - 근거 문서: code.claude.com/docs/en/claude-directory("If you set `CLAUDE_CONFIG_DIR`, every `~/.claude` path on this page lives under that directory instead"), env-vars.
  - 이 좌석에서 확인: `CLAUDE_CONFIG_DIR=~/.cys/claude`입니다. `~/.claude/skills`에만 있는 16개(cloudflare 등)는 이 좌석 스킬 목록에 나오지 않습니다.
- 심링크로 걸린 스킬 폴더도 읽습니다(skills 문서: "can be a symlink to a directory elsewhere on disk").
- 같은 이름이 여러 곳에 있으면 enterprise > personal > project 순으로 이깁니다. 플러그인 스킬은 `/플러그인:스킬` 이름공간으로 따로 붙습니다.
- ★**목록 예산**: 스킬 설명은 모두 합쳐 「컨텍스트의 1%」 안에 들어가야 합니다.
  - 설정값: `skillListingBudgetFraction` 0.01. 환경변수 폴백은 8,000자입니다.
  - 넘치면 「덜 부른 스킬부터 설명을 지웁니다」.
  - 스킬 하나의 설명은 1,536자에서 잘립니다.
- 스킬 폴더 안의 SKILL.md를 고치면 세션 중에도 반영됩니다. 다만 세션 시작 때 없던 skills 폴더를 새로 만들면 `/reload-skills`가 필요합니다.
- 로컬 Claude Code 판은 2.1.318입니다.

### 1-2. 좌석 프로필에 링크를 거는 코드 (하나뿐)

- **정해진 목록만 링크합니다.** `cysjavis-pack/bin/javis_preflight.py`의 세 검사가 각자 목록을 들고 있고, 그 목록만 프로필 `skills/`에 심링크합니다(`:4794`, `:5278`의 `os.symlink`).
  - C26 VIDEO_SKILLS 32개(`:340`)
  - C27 APPBUILD_SKILLS 20개(`:366`)
  - C29 HARNESS_SKILLS 3개(`:818`)
  - 「팩 스킬 전부」 같은 일반 규칙은 없습니다.
- **링크를 걸 프로필**은 `discover_skill_profiles()`(`:1569`)가 정합니다. 이 함수는 `discover_claude_settings()`(`:1510`)를 부릅니다.
  - 찾는 순서: CLAUDE_CONFIG_DIR(최우선) → `~/.claude*` → CYS_ACCOUNT_DIR.
  - 부서 팩 안에서 돌 때는 자기 계정 폴더 하나로 좁힙니다(`_discover_isolation_block`).
- **링크를 부르는 곳은 세 군데**입니다.
  - ① cysd가 좌석을 띄우기 직전: `src/bin/cysd/state.rs:6212` `wire_seat_profile_before_exec` → `javis_preflight.py --wire-seat`(`:11046`, C26·C27·C29만 실행)
  - ② `cys init-pack`(앱 갱신 경로 포함): `cys.rs` `init_pack_wire_profile_skills`
  - ③ 각성 절차의 `preflight --fix`
- **링크를 지우는 곳**: `src/factory_reset.rs:2636` `remove_pack_skill_links`. 대상이 팩인 링크만 지웁니다.
- **사용자 오버레이** `~/.cys/local/skills`는 `cys skill list/show`(`cys.rs:8235`)만 읽습니다. 프로필 링크로는 **걸리지 않습니다**. 그래서 네이티브 Skill 도구에는 보이지 않습니다.

### 1-3. 좌석 종류별 실측표

| 좌석 | 읽는 프로필 | 네이티브로 보이는 우리 스킬 | 근거 |
|---|---|---|---|
| 본부 worker·cso (cys 좌석) | `~/.cys/claude` | 55개 = VIDEO 32 + APPBUILD 20 + HARNESS 중 설치판에 있는 2개, 그리고 `synced`(claude.ai 동기 폴더 · 우리 것 아님) | `ls ~/.cys/claude/skills`, 이 좌석 `CLAUDE_CONFIG_DIR` |
| 본부 master (cmux · 박사님 좌석) | `~/.claude` | 70개 = 같은 링크 55개 + master 전용 실디렉토리 15개 + `synced` | `ls ~/.claude/skills` |
| 부서 좌석 | `~/.cys/claude-<부서>` | 지금은 0개. `claude-default-dept-1`에 skills 폴더가 없습니다. 마지막 사용이 09-20이고, 좌석 기동 직전 배선 코드는 09-23에 들어왔습니다 → **다음 부서 좌석 기동 때 자기 프로필만 링크됩니다** | 격리 env로 `discover_skill_profiles()`를 돌린 결과 = `[claude-default-dept-1]` |
| 부서 팩 5개 (`pack-dept-*`) | — | skills 118개. dept-by-chat이 없는 8/1·9/20 시점 사본입니다. 부서 데몬이 새 판으로 뜨면 `cysd main.rs:1406` `pack::install`이 임베드 팩으로 갱신합니다(`pack_current_for` 게이트) | `diff` 실측 |
| 사용자 새 설치 (맥) | `~/.cys/claude` | 앱에 임베드된 PACK_ALL → cysd 첫 부트 때 install → 첫 좌석 기동 전 `--wire-seat` → 55개 | 코드 경로 |
| 사용자 새 설치 (윈) | 같음 | 같은 코드(`os.symlink`)입니다. **이 맥에서는 실측할 수 없습니다.** 개발자 모드가 아니면 심링크 실패 시 WARN이 납니다(미확인) | 코드 |

### 1-4. 「65개가 빠진다」의 정체 — 결함인가 의도인가

- 정확한 수부터 바로잡습니다.
  - 설치 팩은 스킬 폴더 115개 + 파일 4개(`ls` 하면 119)입니다. 링크된 것은 55개, **링크 안 된 것은 60개**입니다.
  - 작업트리 팩은 116개입니다(1.1.11 신규 computer-control 포함).
- **판정: 결함이라기보다 「가족별 손 목록」 설계입니다.** 그런데 이 설계는 같은 결함을 되풀이하는 구조입니다.
  - dept-by-chat(09-22)과 computer-control(1.1.11)이 모두 「목록에서 빠짐 → Unknown skill」을 겪은 뒤에야 목록에 들어갔습니다.
  - 근거: `:810-817` 주석.
- 링크 안 된 60개도 아주 안 보이는 것은 아닙니다. `cys skill list/show`와 각성 훅의 색인(이름 116개)으로는 닿습니다. 정확히 말하면 **「네이티브 Skill 도구 목록에 안 뜬다」**입니다.
- ★**「전부 링크」를 하지 않는 이유 — 예산 실측**
  - 설명 글자 수 합계(1,536자 잘림 적용): 링크된 54개 = 10,804자 · 팩 전체 116개 = 26,604자 · `~/.claude/skills` 70개 = 16,612자.
  - 이 좌석(1822) 스킬 목록에서 `anthropic-skills:*` 십여 개가 **이미 이름만 남고 설명이 빠져 있습니다.** 예산 경계에 이미 닿아 있다는 관측 증거입니다.
  - 그래서 116개를 다 걸면 덜 쓰는 우리 스킬부터 설명이 사라지고, 발동이 오히려 나빠집니다.

---

## 2. 자산 전수표 (개정 기준 master#7a471ca4의 ⑴⑵⑶)

판정 기준 3가지:
- **⑴ 원문 동봉** = 오픈 라이선스이거나, 원문에 「자유 사용·복사해 쓰세요」 같은 문장이 있는 것
- **⑵ 런타임 참조** = 원문이 없으면 결과가 확실히 떨어지는 것. 첫 사용 때 1회 받아 `~/.cys` 캐시에 두고 7일마다 새로 받습니다
- **⑶ 우리 말 요약**

접근 실측 = curl 200 실측(08:1x). 노션 페이지는 로그인 없이 `notion.so/api/v3/loadPageChunk`로 본문 블록이 받아지는지까지 확인했습니다.

### 2-1. 자산별 판정 (주된 판정 · 문서/차트/영상/PPT 용도 · 스킬 상태)

| 자산 | 지금 상태 | 용도 | 교회·개인 자료 | 우리 코드·절차 판정 | 제3자 원문 판정 |
|---|---|---|---|---|---|
| motion-graphics-prompt | 스킬 있음(`~/.claude/skills` 실디렉토리 · 팩에 없음) + 도구 2개(`seek_render.js`, `ref_frames.sh`) | 영상 | README:76 교인 이름·사진 규칙 → 일반 문구로 바꿈 | **팩 승격.** 경로 고정 `~/axdev` 제거, playwright를 다른 스킬 폴더에서 빌려 쓰던 것을 끊고 의존 안내, 맥 arm64 크롬 고정 → 탐색 | 헤이디 노션 = **⑵ 후보(경계)** · Prompt Motion = **⑶**(아래 2-2) |
| ppt-design-system | 스킬 있음(실디렉토리 · 팩에 없음) + 추출 도구(표준 라이브러리만) | PPT·문서 | 당회 세미나 원고 76KB · 교회 덱 · samples 3벌 → **0 반입** | **일부 팩 승격.** 추출 도구 + 절차(§0 이야기 층 먼저) + 빈 COMMON 양식 | 헤이디 PPT 지침 = **⑴**(근거 문장 아래) |
| video-report-deck | 스킬 있음(실디렉토리 · 팩에 없음) · 코드 30파일 + node_modules 13MB | 영상(보고 영상) | `~/.config/godmeyou/elevenlabs.env` 키 경로 → suite-runtime-keys 방식으로 교체 | **팩 승격.** package.json만, node_modules 제외, macOS `say` = 맥 전용 대체 수단이라고 명시 | 커리어해커 영상 aoq12W8Q1Qg은 「모양 문법」 실측값만 → **⑶** |
| ppt-styles | 도구(스타일 11종 · `pick.py` · `kit.js` · 빌드) + 카탈로그 | PPT | 1번 스타일 견본 글 = 바이블칼리지 강의 실물 → 교체 | **팩 승격(정리 후).** node_modules 129MB 빼고 package.json만 · 11번 careerhacker 이름은 바꾸거나 제외 · run.sh가 쓰는 Anthropic pptx `validate.py`(재배포 불가) 의존 끊기 · Apple SD Gothic 파일은 반입 금지(사용만) · npm audit high 2건(image-size) 해소 | theme-factory(Apache-2.0) · frontend-slides(MIT) = **⑴**(LICENSE 동봉되어 있음) |
| portrait-cutout | 도구만(py + swift · macOS Vision) | 문서·PPT(웹 히어로 사진) | `examples/` 4장 = 실존 인물 얼굴(담임목사)·다른 교회 캡처 → **0 반입** | **도구만 팩 승격.** 맥 전용 가드(윈은 친절한 안내 후 중단) | 해당 없음 |
| careerhacker-alex-style | 참고 + 도구 2개(`measure_palette.py`, `grab_frames.sh`) · 191MB | 영상·PPT | 없음 | **이 맥 전용**(README「외부 게시·배포 금지」). `measure_palette.py`만 팩 도구 후보 — 필요한지는 불확실, 이번에는 넣지 않음 권고 | motion-kit 172 = **⑶ 또는 ⑵ 경계**(아래 2-2) · 프레임 17장 = **⑶** |
| ui-terms-24 | 참고 + 모션 시범작 · 76MB | 문서·영상 | 영상 메타 info.json에 **댓글 43개의 작성자 이름·아이디** → 0 반입 | **참고만**(말로 시키면 되는 용어 사전 = say-it-to-master 규칙) | 치트시트 화면·원본 영상 = **⑶** |
| video-knowledge | 참고 3편 | 문서(업무 설계) | 교인 개인정보 경계 메모 | **참고만** | **⑶** |
| glance-test-checklist | 참고(점검표) | 문서·PPT·차트 | §5 = 이 맥 사이트 경로·교회 홈 | **참고만.** 스스로 「master에게 말로 시키기」 칸이라고 밝힘 | Duarte 원문은 가져오지 않음 = **⑶** |
| 메모리 dataviz 원칙 | 메모리(원칙 5개) | 차트 | 교구 출석·헌금 예시 | **참고만**(아래 3-5 대안) | 어니언 BI 영상 = **⑶** |
| REFERENCE-TOOLS / CHANNELS | 운영 장부 | 전부 | 박사님·교회 언급 26줄 | **참고만**(이 맥) | — |
| cloudflare 11종 · nlm-skill · agora-delegate (master 전용) | 남이 만든 것으로 추정(LICENSE 0) / 우리 것이지만 agora 의존 | — | — | **팩에 넣지 않음.** cloudflare·nlm은 출처·라이선스 불명. agora는 제품 구성 여부 불명 | — |

### 2-2. 제3자 원문 출처표 (⑴ 근거 문장 · 접근 실측)

| 원문 | 주소 | 접근 실측 | 근거 문장 / 라이선스 | 판정 |
|---|---|---|---|---|
| 헤이디 「나만의 디자인 시스템 만들기 프로젝트 지침」(노션) | app.notion.com/p/3f671a693e5480b2afeee6776d6ec9e2 | 200 · API 블록 17개 · 2,338자 | 영상 nbs8JtlY27s 원문: 「이 지침은 제가 다 드릴 겁니다 … 직접 작성하실 필요 없이 제가 공유드릴테니까 **그냥 복사 붙여 넣기만 진행하시면 됩니다**」(로컬 `ppt-design-system/source-video-transcript-nbs8JtlY27s.txt`) | **⑴ 원문 동봉** + 출처 표기 |
| 헤이디 「모션 그래픽 제작 프롬프트」(노션) | app.notion.com/p/40371a693e5480bdaf3aec362419d8e0 | 200 · API 블록 33개 · 1,225자 | 영상 7xOcIYWGG0A 「정착한 프롬프트까지 **다 공유해 드릴게요**」(timed 00:00:31) + 노션 「아래 프롬프트는 예시입니다. 여러분이 원하는 영상에 맞춰 **다시 작성해 보세요!**」 — 「자유 사용·복사」 문장은 없음 | **⑴ 아님(엄격 해석) → ⑵ 후보.** 비교 실측 뒤 확정 · master 판단 요청 |
| Prompt Motion 템플릿·갤러리 | prompt-motion.com/ · /tequilafunks-97f6c9 · /templates/showreel | 200 셋 다 | robots Content-Signal `search=yes, ai-train=no, use=reference` · 「Videos and prompts belong to their creators」 | **⑶**(재배포 근거 없음). 런타임에 매번 긁는 기존 `ref_frames.sh` 동작은 「use=reference」 범위로 유지 가능 — 판단 요청 |
| 커리어해커 모션 키트 172 | careerhackeralex.com/sharings/cha-motion-kit | 200 | 「영상과 프롬프트는 **개인 학습·제작에** 자유롭게 쓰세요」 + GSAP 표준 라이선스(zip) | **⑴ 아님**(「개인」 범위 한정 = 제품 동봉은 범위 밖). ⑵는 「사용자 기기가 자기 제작에 받아 씀」이라 범위 안으로 읽을 여지가 있으나 **경계** → 기본 **⑶**, 판단 요청 |
| 헤이디 html-deck 영상 | youtube uI5gwDMugn0 | 200 | 없음 | ⑶ |
| 커리어해커 영상들 | youtube 1mZ8dNoWLhI 외 · aoq12W8Q1Qg | 200 | 없음 | ⑶ |
| 코드깎는노인 용어 24 | youtu.be/mlhKEy-2bgI | 200 | 없음(메타 license None) | ⑶ |
| 어니언 BI 시각화 5 | youtu.be/Q6wp_MtKZZ8 | 200 | 없음 | ⑶ |
| Nodi 글랜스 · Duarte | youtu.be/IW8txpcoZGU · duarte.com/resources/slide-glance-test/ | 200 · 200 | 없음 · Duarte 상표(Glance Test™) | ⑶ |
| theme-factory | github.com/anthropics/skills/…/theme-factory | 200 | Apache-2.0(LICENSE 동봉) | ⑴ |
| frontend-slides | github.com/zarazhangrui/frontend-slides | 200 | MIT(LICENSE 동봉) | ⑴ |
| Anthropic pptx `validate.py` | github.com/anthropics/skills/…/pptx | 200 | 공개돼 있지만 오픈소스 아님(재배포 불가로 읽힘) | **의존 끊기**(동봉도 참조도 안 함) |
| Pretendard | github.com/orioncactus/pretendard | 200 | SIL OFL 1.1 | ⑴(글꼴 파일 + LICENSE 동봉 가능) |
| 오빠두엑셀 노션 프롬프트 모음 | (신청 안 함) | — | 조건부(좋아요·댓글) 자료 | **⑶** (master#0a47f970 분류) |

> 원본 시점 고정(master#0a47f970): 팩판은 08:1x 갱신본을 원본으로 한다 — `~/.claude/skills/motion-graphics-prompt/SKILL.md`(내레이션 기반 갈래 · 덕킹 믹스 명령) · `assets/motion-graphics-prompt/BRIEF-TEMPLATE.md`(6칸 GSAP seek · 4칸 글꼴 동봉 · 8칸 내레이션 신설) · `assets/portrait-cutout/README.md`(AI 그림 초록 바탕 오리기 절). 제작 착수 때 mtime·해시를 다시 재서 그 시점본을 쓴다.

---

## 3. 설계 (1쪽)

### 3-1. 네이티브로 거는 범위 — 「산출물 가족」 한 목록 추가

- preflight에 `OUTPUT_SKILLS` 목록 하나와 검사 하나(C29와 같은 규약, 새 C 번호)를 더합니다. `wire_seat()`의 튜플에 그 검사를 넣습니다.
  - 그러면 좌석 기동 직전·init-pack·각성 `--fix` 세 경로를 **같은 코드로** 탑니다(손 링크 0).
- 목록 = ⓐ 이번에 새로 승격하는 자산 스킬 + ⓑ 팩에 이미 있지만 링크 안 된 산출물 스킬.
  - ⓐ 새 자산 스킬: motion-graphics-prompt · ppt-design-system · video-report-deck · ppt-styles · portrait-cutout(5개)
  - ⓑ 기존 산출물 스킬: hwp · rhwp-edit · korean-humanizer · korean-spell-check · korean-character-count · design-token-system · design-system-propagate · transcription · scene-cut · caption-align · caption-correct · sfx-place · voice-local(13개)
  - 설명 실측 합계: ⓑ 13개 = 3,135자 · ⓐ 기존 설명 3개 = 915자.
  - writing-* 3개(1,061자)는 「글 다듬기 대화」 성격이라 제외를 권고합니다.
- **예산 가드(전문가 칸 — 충돌·오발동 점검표를 시험으로)**
  - ① 링크 대상 설명 합계 상한 시험: 현재 + 약 4,500자. 숫자는 시험에 박고, 넘으면 실패합니다.
  - ② 새 스킬 설명 300자 이하, 핵심 용도를 맨 앞에 둡니다.
  - ③ 발동 문구 겹침 점검: 설명끼리 핵심 명사 겹침표를 시험이 출력하고, 같은 일을 두 스킬이 주장하면 실패합니다. 예: 「PPT」를 ppt-design-system과 ppt-styles가 함께 주장하는 경우 → 역할을 「기준 수립」 / 「스타일로 바로 생성」으로 갈라 씁니다.
  - ④ pack.rs 임베드 불변식 시험(`pack_skills_embed_adopted_set_and_indexable`)에 새 목록을 넣습니다.

### 3-2. 원문 처리 — ⑴ 동봉 / ⑵ 런타임 캐시 / ⑶ 요약

- **⑴** 스킬 폴더 `references/` 안에 원문 + `SOURCE.md`(주소 · 근거 문장 · 받은 날 · 표기 문구)를 둡니다. THIRD_PARTY.md에 한 줄 추가합니다.
- **⑵ 결과(2026-11-06 실측 뒤 갱신)**: ⑵ 후보였던 헤이디 모션 프롬프트는 같은 요청 1건 비교(원문 vs 요약 · codex 블라인드)에서 **요약이 근소 우위(slight)** → ⑵ 조건 「원문 없으면 확실히 떨어진다」 불충족 → **⑶ 강등**. ⑵ 에 해당하는 원문이 0건이 되어, 아래 공용 도구는 **팩에서 뺐다**(쓰는 곳 0 · 네트워크 받기 도구의 codex 1R 지적 5건을 안고 실을 이유 없음). 코드·시험은 커밋 9100fb07 에 남아 있어, 첫 ⑵ 원문이 생기면 1R 지적을 고쳐 되살린다.
- **⑵(설계 · 현재 미탑재)** 팩 공용 도구 `bin/javis_asset_fetch.py` 하나를 둡니다(표준 라이브러리만).
  - 스킬 폴더 `sources.json`에 원문 목록을 적습니다(id · 주소 · 종류 notion/http · 요약 파일).
  - 원문을 찾는 순서:
    - ① **이 맥 원문 사본**: `~/.cys/local/assets/<id>`. 박사님 좌석 = 지금 사본 그대로 쓰도록 이 자리에 링크합니다.
    - ② 캐시 `~/.cys/asset-cache/<id>`. 7일이 지나지 않았으면 그대로 씁니다.
    - ③ 공개 주소에서 받기 → 캐시에 저장
    - ④ 받기에 실패하면 7일이 지났어도 캐시를 씁니다.
    - ⑤ 그래도 없으면 우리 요약을 쓰고, 「원문을 못 받아 요약으로 진행합니다(사유)」를 1줄로 알립니다.
  - 노션은 공개 페이지 블록 API로 받습니다(로그인 0). 이 길은 **비공식 API라 바뀔 수 있습니다** → ④⑤가 그때의 안전판입니다.
  - 저장소·설치본에 원문 사본은 0입니다.
- **⑶** 스킬에는 우리 말 요약 + 출처 주소만 둡니다.

### 3-3. 이 맥 좌석

- 우리 스킬은 팩 판으로 갑니다. master 전용 실디렉토리 3개는 **팩 판이 들어온 뒤에도 그대로 둡니다.** master 프로필에서는 실디렉토리가 이기고, 링크기는 실디렉토리를 덮지 않습니다(`:4790` 규약).
  - 차이가 있으면 팩 판으로 맞출지 master가 결정합니다.
- 이 맥 전용(careerhacker 등)과 사용자 자기 스킬은 `~/.cys/local/skills`에 둡니다. 그 폴더도 **프로필 링크 대상에 넣는 것**을 제안합니다.
  - 제품 기능으로서도 맞습니다. 사용자가 `cys skill new`로 만든 스킬이 지금은 네이티브로 안 보입니다.
  - 단점: 사용자 스킬 수만큼 예산을 먹습니다 → 시험 ①의 합계 경고에 포함합니다.

### 3-4. 새 자산 → 스킬 승격 절차 (재귀 학습 경로 · skill-writing에 1절)

1. 영상 검토 보고서의 「우리 자산 개선」에서 자산이 생깁니다(video-review-registry).
2. 판정 4칸을 채웁니다: 말로 시키면 되는가(되면 끝) · 도구·절차가 있는가 · ⑴⑵⑶ · 교회·개인 자료.
3. 팩 스킬 형식으로 만듭니다(skill-writing 2-1 시험 입력 2~3개 + 스킬 없이 대조 1회).
4. `OUTPUT_SKILLS`와 임베드 불변식에 올리고, 예산·겹침 시험을 통과해야 합니다.

### 3-5. 넣지 않기로 한 것과 이유

- ui-terms-24 · glance 점검표 · video-knowledge · dataviz 원칙: 말로 시키면 되는 일입니다(say-it-to-master).
  - 다만 glance 점검표(§5 제외)와 dataviz 원칙 5개는 **기존 승격 스킬의 references에 한 장씩** 붙이는 정도는 가치가 있습니다. 넣을지는 master 판단입니다.
- cloudflare·nlm·agora: 출처·라이선스·제품 구성이 불명합니다.
- careerhacker 본체: 「외부 배포 금지」입니다.

### 3-6. 시험 계획 (보고 2)

- 새 좌석 3종에서 「PPT 만들어」「인트로 영상」「차트」 요청에 해당 스킬이 목록에 뜨는지 실측합니다.
  - 좌석 3종: 본부 worker · 부서 격리 env · 격리 HOME 새 설치 흉내
  - 방법: `claude -p` 격리 실행(메모리 reference_isolated-claude-p-skill-test 규약)
- 팩 시험 + 부트 건강 게이트(`cargo test` 관련 + preflight `--wire-seat` 격리 HOME)를 돌립니다.
- 스킬 안 스크립트를 스크래치에서 1회씩 돌립니다(의존 없으면 안내 후 중단까지).
- **⑵ 비교 1건**: 헤이디 모션 프롬프트로 같은 요청 1건을 「원문 받아 씀」과 「요약만」으로 각각 돌려 결과 차이를 실측합니다 → ⑵ 확정 또는 ⑶ 강등.
- 사용자에게 실리는 스크립트(`javis_asset_fetch.py`, 도구 이관분)는 codex 1R(`</dev/null` + timeout)을 받습니다.
- 윈: 같은 코드라 정적 시험만 합니다. 실기는 relprep 계열 윈 VM 몫입니다(이 맥 실측 불가라고 명시).

### 3-7. 비가역·비용

- 팩 덮어쓰기·push·릴리스 = 0입니다.
- 이 맥 프로필 배선(①)은 **이 설계를 승인받은 뒤** 집행합니다. 방법은 저장소 판 preflight `--wire-seat` + `~/.cys/local/assets` 링크입니다.
- 유료 API 0 · 제3자 원문 재배포 = ⑴ 근거가 있는 것만입니다.

---

## 4. 결과 (보고 2 · 2026-11-06 09:2x)

### 4-1. 좌석별 실측표

| 좌석 | 프로필 | 산출물 스킬 링크(18 중) | 비고 |
|---|---|---|---|
| 본부 master(cmux) | `~/.claude` | 13 팩 링크 + 원본 실디렉토리 3(motion·ppt-design-system·video-report-deck) = 16 | ppt-styles·portrait-cutout = 다음 판(설치 팩에 아직 없음) |
| 본부 worker·cso | `~/.cys/claude` | 13 팩 링크 + 로컬 3(→ master 원본) = 16 | 이 세션(1822)에서 재시작 없이 목록에 뜸(핫 리로드 실측) |
| 부서(dept-1) | `~/.cys/claude-default-dept-1` | 16(+ C26·C27 링크 첫 생성) | 부서 팩 데몬 미기동 · 저장소 `--wire-seat` 로 배선 |
| 새 설치(맥) | 임베드 팩 → 첫 좌석 기동 전 `--wire-seat` | 18 | cargo `pack_skills_embed_adopted_set_and_indexable`·`install_writes_core_and_skills_to_fresh_dir`·`dbg_r12_init_pack_*` 통과 |
| 새 설치(윈) | 같은 코드 | 18(예상) | 이 맥 실측 불가 · 윈 접두·대소문자 정규화는 정적 시험만 |

### 4-2. 설명 예산(좌석당 30,000자 · `claude -p --debug-file` 실측)

| 좌석 | 전 | 후 |
|---|---|---|
| 본부 worker(`~/.cys/claude`) | 92개 38,707자(이미 초과) | 109개 45,159자 |
| master(`~/.claude`) | — | 100개 36,324자(로그인 없는 측정 · 목록 줄은 찍힘) |
| 부서 dept-1 | — | 측정 불가(OAuth 만료) |

- 본부 좌석 설명 구성(설명 글자만): 팩 링크 67개 14,288 · claude.ai 동기 22개 11,850 · 로컬 5개 1,001.
- 1.1.12 skill-fold 병합 뒤 추정(설명 글자 기준 · 추정): 우리 몫 15,298 → 약 3,430 → 본부 약 33,300(여전히 초과) · 동기 스킬 이름만 표시까지 하면 약 21,400.
- 이 가지와 `feat/1112-skill-fold` 는 충돌 없이 합쳐진다(`git merge-tree` rc 0).

### 4-3. 발동 시험(격리 claude -p · 새 좌석이 보는 우리 스킬 73개)
- 10/10 일치(PPT 바로 생성 · 기준 수립 · 인트로 모션 · 보고 영상 · 배경 지우기 · hwp · 다듬기 · 받아쓰기 · 아바타 유튜브 · 지저분한 「ppt 만들어줘 빨리 ㅇㅇ」) · 「차트」 = 내장 dataviz 스킬로 감(우리 차트 스킬 없음 = 의도).
- hwp·다듬기 첫 시도 불일치 2건 = 입력(파일·글) 없이 물어서 모델이 먼저 되물음 → 입력을 넣어 재시험 2/2.

### 4-4. 검증 라운드(codex · 이종)
- 1R REVISE 8 → 수정(C84 소유권·상대 링크 · factory_reset 경로 비교) + 원문 받기 도구 제외(⑵ 0건)
- 2R REVISE 12 → 전부 수정(사용자 지정 팩 경로 · 작업 폴더 삭제 · 상대 경로 · 캐시 키 · 무한 길이 · 장 목록 대조 · 그룹 좌표 ×2 · 임시 파일 · 윈 접두)
- 3R REVISE 2(ref_frames.sh 링크 표기 우회 · 넓어진 삭제 패턴) → 수정
- 4R ACCEPT · 미해소 0
