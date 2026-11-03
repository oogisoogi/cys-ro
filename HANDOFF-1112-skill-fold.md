# HANDOFF — TICKET=cysr-1112-skill-fold (스킬 설명 상주 비용 접기)

작성: worker-1112skill-fold(surface:1802) · 2026-11-04 · 가지 feat/1112-skill-fold ← rel/1.1.11(10802555)

## 결과 한눈에
| 항목 | 전 | 후 | 근거 |
|---|---|---|---|
| 팩 전체 상주 설명 합(116개) | 26,358자 · 목록 115개 | **9,705자** · 목록 64개 | `python3 scripts/skill_desc_budget.py` |
| 좌석 프로필 실상주(C26·C27·C29 링크 55개) | 11,179자 · 55개 | **1,230자** · 12개 | 같은 스크립트 + preflight 목록 대조 |
| 발동 회귀(30문장 · claude-opus-5-5 · 2회) | 24/30 · 24/30 | **27/30 · 28/30** | `scripts/skill_trigger_regress.py` |
| 소비자 잔여(숨긴 스킬 [[링크]]인데 Read 안내 없는 .md) | — | **0** | 아래 「소비자 전수」 |

★사실 정정(브리프 전제): 「115개 설명 26,243자 = 모든 좌석에 늘 실림」은 정확하지 않았다. Claude Code 목록에 실리는 것은
preflight C26(영상 32)·C27(appbuild 20)·C29(하네스 3)가 프로필 `skills/`에 링크한 **55개(11,179자)** 뿐이고, 나머지 61개는
cys 디렉티브의 **이름만 색인**(1.1.6 F2 · 상한 3,000자)으로만 보인다. 이번 작업은 브리프 성공 기준(팩 전체 합 ≤10,000)으로
쟀고, 실좌석 수치도 함께 적었다(둘 다 충족).

## 무엇을 했나
1. **하위·공통 규약 51개 = `disable-model-invocation: true`**(목록에서 빠짐 · 사용자 `/이름`·`cys skill show` 그대로 · 파일 이동 0).
   폴더 안 참조 파일로 옮기는 안 대신 이것을 고른 이유: 설치기·pack 소유권·preflight 링크 목록·pack.rs 임베드 불변식·
   기존 설치의 낡은 링크 정리까지 건드리지 않는다(변경 = frontmatter 한 줄).
2. **목록에 남는 1st-party 31개 설명 = 「무엇 + 언제」 2문장**(한국어 발동 문구 유지 · 한 줄 `description:` 유지 —
   javis_registry·board_catalog·HUD·cysd 시험이 한 줄로 읽는다). 원래 설명은 각 SKILL.md 끝 「원 설명」 절에 **원문 그대로** 옮겼다
   (본문은 발동 때만 읽힘 · 내용 손실 0). harness-engineering 은 여러 줄 `description: |` 블록이었는데 한 줄로 바꿨다(원문은 같은 절로).
3. **부모·형제 54개 SKILL.md 머리에 안내 1줄**: 수동 전용 하위는 Skill 도구로 부르지 말고 같은 skills 폴더의 `<이름>/SKILL.md` 를 Read.
   기능 확인: 격리 프로젝트에서 「썸네일 만들어줘」 → `Skill(media-gen)` → `Read(.../media-gen-thumbnail/SKILL.md)` → 그 절차 1번 수행(실측).
4. **round/capability_catalog.json 재생성**(javis_registry build) — 설명을 담는 파생 카탈로그. ⚠HEAD 에서 이미 드리프트였다
   (스킬 18개 누락 · 98→116). 재생성으로 그것까지 해소됐다(verify OK).
5. 실측·시험 도구 3개 추가: `scripts/skill_desc_budget.py`(`--max N` 이면 초과 시 exit 1) · `scripts/skill_trigger_regress.py` · `scripts/skill_trigger_cases.json`.

### 숨긴 51개
appbuild-orchestrate · appbuild-orchestrate-delegate · appbuild-orchestrate-route · appbuild-orchestrate-verify · appbuild-plan · appbuild-plan-debate · appbuild-plan-interview · appbuild-plan-quick · appbuild-screen-spec · appbuild-screen-spec-detail · appbuild-screen-spec-flow · appbuild-supervisor · appbuild-supervisor-collect · appbuild-supervisor-fix · appbuild-supervisor-gate · appbuild-supervisor-verify · appbuild-tasks · appbuild-tasks-order · appbuild-tasks-slice · audio-post-mix · audio-post-music · cost-preview-confirm · heygen-avatar-render-api · heygen-avatar-render-gate · media-gen-edit · media-gen-image · media-gen-thumbnail · media-gen-upscale · media-gen-video · script-writer-factcheck · script-writer-research · script-writer-structure · script-writer-voice-prep · suite-runtime-keys · vibecoding-boundary · vibecoding-docs · vibecoding-eval · vibecoding-knowledge · vibecoding-runbook · vibecoding-state · vibecoding-tdd · vibecoding-verify · video-stitch-broll · video-stitch-captions · video-stitch-compositing · video-verify-audio-sync · video-verify-final-gate · video-verify-timing · video-verify-visual · voice-clone-elevenlabs-chunk · voice-clone-elevenlabs-synth-qc

### 설명을 줄인 31개(자수)
| 스킬 | 전 | 후 |
|---|---|---|
| appbuild | 255 | 120 |
| audio-post | 188 | 70 |
| caption-align | 350 | 87 |
| caption-correct | 434 | 77 |
| computer-control | 383 | 168 |
| dept-by-chat | 214 | 148 |
| design-system-propagate | 255 | 85 |
| design-token-system | 215 | 88 |
| eval-driven-self-improvement | 386 | 90 |
| grill-me | 136 | 88 |
| hallucination-guard | 140 | 86 |
| harness-creator | 310 | 92 |
| harness-engineering | 1361 | 147 |
| heygen-avatar-render | 227 | 74 |
| media-gen | 222 | 95 |
| org-provision | 180 | 93 |
| rsi-learning-loop | 464 | 94 |
| scene-cut | 370 | 69 |
| script-writer | 180 | 84 |
| self-correction-loops | 140 | 90 |
| sfx-place | 290 | 60 |
| skillscan-semantic | 446 | 101 |
| tdd | 206 | 155 |
| timesfm-forecasting | 357 | 85 |
| transcription | 317 | 86 |
| vibecoding | 375 | 96 |
| video-stitch | 215 | 74 |
| video-verify | 194 | 76 |
| voice-clone-elevenlabs | 215 | 84 |
| voice-local | 318 | 82 |
| youtube-video-pipeline | 268 | 90 |

### 손대지 않은 것 — 벤더 33개(6,718자 · 남은 상주의 69%)
k-skill 14 · superpowers 9 · mattpocock 9 · insane-search 1. 이유: 제품이 싣는 덮어쓰기 층이 없다(`~/.cys/local/skills` 는 사용자 영역)
→ 줄이려면 제자리 수정뿐이고 브리프 규칙상 【질문】 대상이다. 목표가 벤더 없이 달성돼 질문하지 않았다. insane-search 는
_VENDOR_MANIFEST sha256 핀 대상이라 손대면 vendor-check 가 막는다(오너 승인 스냅샷 갱신 필요).
더 줄이려면 = 벤더 설명 수정(오너 결정) — 단 벤더 스킬은 좌석 프로필에 링크되지 않아 실좌석 비용은 이미 0이다.

## 발동 회귀 시험 (30행)
- 격리: 시험 프로젝트 `.claude/skills` 에 팩 스킬 복사 · `--setting-sources project`(사용자 프로필의 55개 링크·훅·CLAUDE.md 안 읽음) ·
  `disableAllHooks` · `CYS_*` 환경변수 제거 · 허용 도구 Skill 뿐 · `--max-turns 2`.
- ⚠브리프의 「임시 CLAUDE_CONFIG_DIR」은 쓰지 못했다: 새 설정 폴더는 로그인이 없고(`--bare` 는 API 키 전용 · 키 없음),
  OAuth 토큰 복사는 갱신 토큰 회전으로 실좌석 로그인을 깰 수 있어 하지 않았다. 대신 위 플래그로 같은 격리를 만들었고
  프로브로 실측했다(목록 = 시험 프로젝트 스킬 + 내장뿐 · 훅 발화 0).
- 채점: 첫 Skill 호출 중 오류가 아닌 것 ∈ 정답 집합(하위 단계는 부모가 맡아도 같은 일 → 부모·하위 모두 정답 · 전/후 같은 집합).
- 비용: 회당 약 $0.06 · 총 120회 + 프로브.

| # | 요청 문장 | 정답 집합 | 전 1 | 전 2 | 후 1 | 후 2 |
|---|---|---|---|---|---|---|
| 1 | 쇼핑몰 웹사이트 하나 만들어줘. 코드부터 짜지 말고 기획부터 하자. | appbuild · vibecoding · appbuild-plan | O appbuild | O appbuild | O appbuild | O appbuild |
| 2 | 앱 기획 문서(PRD)를 인터뷰 방식으로 나랑 같이 만들어 보자. | appbuild-plan-interview · appbuild-plan · appbuild | O appbuild-plan | O appbuild-plan-interview | O appbuild | O appbuild |
| 3 | 이미 써 둔 기획 문서들(PRD·화면·작업목록)이 서로 안 맞는 데 없는지 감독관 검증 돌려줘. | appbuild-supervisor · appbuild-supervisor-verify · appbuild | O appbuild-supervisor | O appbuild-supervisor | O appbuild | O appbuild |
| 4 | 앱 화면 명세서 작성해줘. 화면 흐름이랑 빈 상태·에러 상태까지. | appbuild-screen-spec · appbuild-screen-spec-flow · appbuild-screen-spec-detail · appbuild | O appbuild-screen-spec | O appbuild-screen-spec | O appbuild | O appbuild |
| 5 | 주제 하나 줄 테니 유튜브 영상을 처음부터 끝까지 자동으로 만들어줘. 주제는 '양자컴퓨터 입문'. | youtube-video-pipeline | O youtube-video-pipeline | O youtube-video-pipeline | O youtube-video-pipeline | O youtube-video-pipeline |
| 6 | '블랙홀은 어떻게 생기나' 3분짜리 유튜브 나레이션 대본 써줘. | script-writer · script-writer-research · script-writer-structure | O script-writer | O script-writer | O script-writer | O script-writer |
| 7 | 이 글 맞춤법 검사 좀 해줘: 어의없게 됬다 정말. | korean-spell-check | X (호출 없음) | X (호출 없음) | X (호출 없음) | X (호출 없음) |
| 8 | 유튜브 썸네일 하나 만들어줘. 클릭하고 싶게. | media-gen-thumbnail · media-gen | O media-gen-thumbnail | O media-gen-thumbnail | X (호출 없음) | O media-gen |
| 9 | 이 저화질 영상 클립 화질 좀 올려줘. | media-gen-upscale · media-gen | X (호출 없음) | O media-gen-upscale | O media-gen | O media-gen |
| 10 | 이 앱 상태관리 설계해줘. 페이지별 상태 매핑까지. | vibecoding-state · vibecoding | X (호출 없음) | X (호출 없음) | O vibecoding | O vibecoding |
| 11 | 영상에 깔 배경음악 넣고 나레이션 나올 때는 음악 줄어들게 덕킹해줘. | audio-post · audio-post-mix · audio-post-music | O audio-post | O audio-post | O audio-post | O audio-post |
| 12 | 내 목소리 클론해서 이 대본을 일레븐랩스로 읽혀줘. | voice-clone-elevenlabs · voice-clone-elevenlabs-synth-qc · voice-clone-elevenlabs-chunk | O voice-clone-elevenlabs | O voice-clone-elevenlabs | O voice-clone-elevenlabs | O voice-clone-elevenlabs |
| 13 | 종량제 API 안 쓰고 내 컴퓨터에서 로컬로 한국어 나레이션 음성 합성해줘. | voice-local | O voice-local | O voice-local | O voice-local | O voice-local |
| 14 | 헤이젠 아바타로 이 나레이션 말하는 영상 렌더해줘. | heygen-avatar-render · heygen-avatar-render-api | O heygen-avatar-render | O heygen-avatar-render | O heygen-avatar-render | O heygen-avatar-render |
| 15 | 완성된 영상 업로드하기 전에 립싱크랑 화면 깨진 데 없는지 검수해줘. | video-verify · video-verify-visual · video-verify-audio-sync · video-verify-timing · video-verify-final-gate | O video-verify | O video-verify | O video-verify | O video-verify |
| 16 | 아바타 클립이랑 B-roll 합쳐서 한 영상으로 편집하고 자막까지 번인해줘. | video-stitch · video-stitch-captions · video-stitch-compositing · video-stitch-broll | O video-stitch | O video-stitch | O video-stitch | O video-stitch |
| 17 | 이 인터뷰 녹음 파일 받아쓰기 해줘. 타임스탬프 붙여서. | transcription | O transcription | X (호출 없음) | O transcription | O transcription |
| 18 | 영상에서 말 없는 구간 잘라내고 점프컷으로 편집점 잡아줘. | scene-cut | X (호출 없음) | X (호출 없음) | O scene-cut | O scene-cut |
| 19 | 전사 결과에 잘못 알아들은 단어들 원본 대본 기준으로 고쳐줘. 타임스탬프는 그대로 두고. | caption-correct | O caption-correct | O caption-correct | O caption-correct | O caption-correct |
| 20 | 자막 타이밍을 음성에 단어 단위로 맞춰서 SRT 큐 만들어줘. | caption-align | O caption-align | O caption-align | O caption-align | O caption-align |
| 21 | 영상 장면 넘어갈 때 휙 하는 효과음 넣어줘. | sfx-place | O sfx-place | O sfx-place | O sfx-place | O sfx-place |
| 22 | 교육 부서 하나 새로 만들어 줘. | dept-by-chat · org-provision | O dept-by-chat | O dept-by-chat | O dept-by-chat | O dept-by-chat |
| 23 | 크롬이랑 카톡을 네가 다뤄 줄 수 있어? 뭘 켜야 네가 할 수 있어? | computer-control | O computer-control | O computer-control | O computer-control | O computer-control |
| 24 | 이 보고서 내용 출처가 진짜 맞는지 팩트체크해줘. 환각 없이 근거까지. | hallucination-guard | X (호출 없음) | X (호출 없음) | X (호출 없음) | X (호출 없음) |
| 25 | 내가 뭘 원하는지 아직 애매해. 질문 계속 해서 의도 좀 같이 정리해줘. | grill-me | O grill-me | O grill-me | O grill-me | O grill-me |
| 26 | 이 매출 시계열 데이터로 다음 3개월 예측해줘. | timesfm-forecasting | X (호출 없음) | X (호출 없음) | O timesfm-forecasting | O timesfm-forecasting |
| 27 | 우리 고객상담 업무를 자동화하는 에이전트 팀 하네스 만들어줘. | harness-creator · harness-engineering | O harness-creator | O harness-creator | O harness-creator | O harness-creator |
| 28 | 재귀적 자기개선 학습 루프 돌려서 지금보다 나은 방법 공부해. | rsi-learning-loop · eval-driven-self-improvement | O rsi-learning-loop | O rsi-learning-loop | O rsi-learning-loop | O rsi-learning-loop |
| 29 | 다크모드까지 포함해서 디자인 토큰 시스템 구축해줘. | design-token-system | O design-token-system | O design-token-system | O design-token-system | O design-token-system |
| 30 | 바이브코딩으로 이 기능 만들고 싶은데 Level 판정부터 해줘. | vibecoding | O vibecoding | O vibecoding | O vibecoding | O vibecoding |
| | **일치** | | **24/30** | **24/30** | **27/30** | **28/30** |

불일치 해설(전/후 공통 · 설명 문제 아님): 7 = 모델이 맞춤법을 바로 고쳐 답함(벤더 korean-spell-check · 미수정) · 24 = 파일부터 탐색
(hallucination-guard) · 후1의 8 = 파일부터 탐색하다 턴 소진(후2 는 media-gen 일치). 떨어진 스킬 없음 → 설명 보강 대상 없음.
전에 비해 오른 것: 10(vibecoding 이 상태관리를 받음) · 18(scene-cut) · 26(timesfm) · 17(전2 흔들림 해소).

## 소비자 전수 (grep 실측)
| 소비자 | 영향 | 처리 |
|---|---|---|
| 부모 SKILL.md 의 `[[하위]]` (54개 파일) | 하위가 Skill 목록에서 빠짐 | 머리 안내 1줄 · 잔여 0(스크립트 검사) |
| directives·APPBUILD.md·VIDEO_CREATOR.md·README·docs | 「Skill 도구로 하위 호출」 문구 | grep 0건 — 무변경 |
| preflight C26/C27/C29 링크 목록(VIDEO/APPBUILD/HARNESS_SKILLS) | 링크는 그대로(사용자 /이름 호출 유지) | 무변경 |
| src/pack.rs 임베드 불변식(스킬 이름 목록 · 첫 10줄 name:) | 파일·이름 불변 · name 줄 위치 불변 | 무변경 · 시험 녹 |
| src/bin/cys.rs compose_directive 이름 색인(1.1.6 F2 · 3,000자 상한) | 이름만 · 설명 0 → 영향 없음 | 무변경 |
| src/bin/cysd/delivery.rs 합성 문안 핀 2개(설명 한 줄 재현) | 설명이 짧아짐 → 여유만 늘어남 | 무변경 · 시험 녹 |
| javis_registry(카탈로그 = 설명 보관) | 설명 바뀜 | build 재생성 · verify OK |
| javis_board_catalog · javis_hud_bridge(한 줄 description: 파서) | 한 줄 유지 | check = HEAD 와 같은 결과(기존 미설치 7개 경고 · 무관) |
| hooks: grill-arm(grill-me) · role-capability-gate(appbuild) | 둘 다 목록에 남음 | 무변경 |
| javis_cleanroom vendor-check | insane-search 무접촉 | ⚠HEAD 에서 이미 BLOCK(SKILL.md·engine 3개 해시 드리프트) — 이번 변경과 무관 · 미해결로 남김 |

## 시험
| 시험 | 결과 |
|---|---|
| `cargo test --lib -- pack::`(임베드 불변식 `pack_skills_embed_adopted_set_and_indexable` 포함) | 186 passed · 0 failed |
| `cargo test --bin cysd -- deployed_`(합성 문안 제출단위 핀 2개) | 2 passed |
| `cargo test --bin cys -- skill`(이름 색인 상한 · 오버레이 · init-pack 프로필 링크) | 3 passed |
| `bin/tests/test_review_prompt_verdict_path.py` · `test_v115_dept.py` · `tests/test_hud_office_cc_v13.py` | ALL PASS · OK · OK |
| `javis_registry.py verify` | OK(116 · 문제 0) — HEAD 는 NOT OK(18개 누락 드리프트) |
| `javis_board_catalog.py check` | HEAD 와 동일(기존 미설치 7개 경고 · 무관) |
| `javis_cleanroom.py vendor-check` | BLOCK — **HEAD 와 동일**(insane-search 해시 드리프트 4건 · 이번 변경 무관 · 미해결) |
| 숨긴 스킬 [[링크]] 안내 잔여 검사 | 0 |

## 재현
```bash
python3 scripts/skill_desc_budget.py --max 10000         # 상주 합 · 초과면 exit 1
git archive <전 커밋> cysjavis-pack/skills | tar -x -C /tmp/b
python3 scripts/skill_trigger_regress.py /tmp/b/cysjavis-pack/skills <out-전>
python3 scripts/skill_trigger_regress.py cysjavis-pack/skills <out-후>   # 각 결과 = <out>/result.json
```

## 함정·남은 것
- 새 스킬을 팩에 넣으면 상주 합이 다시 오른다 → 하위 단계는 `disable-model-invocation: true` + 부모 안내 1줄이 규약. `--max 10000` 을 릴리스 게이트에 넣을지는 master 판단(이번엔 넣지 않음 · 단순성).
- 수동 전용 스킬은 Claude Code 목록·자동 발동에서만 빠진다. `/이름` 직접 호출 · `cys skill show` · cys 이름 색인은 그대로다.
- 라이브 팩·`~/.claude/skills` 무접촉. 반영 = 다음 init-pack(설치 갱신) 때 pack/skills 가 바뀌고, 프로필 링크는 그대로 새 내용을 가리킨다.
- 증류: 라이브 팩 무접촉 규칙 때문에 `javis_memory.py add`(pack/memory) 대신 이 좌석 auto-memory 에 1건 기록(격리 claude -p 시험법). 팩 메모리 편입은 master 판단.
