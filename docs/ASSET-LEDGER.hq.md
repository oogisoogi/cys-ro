# ASSET-LEDGER.hq — 본부 전용 판정표 (공개 트리 제외 파일)

> 공개 본문 = `docs/ASSET-LEDGER.md`. 이 파일은 본부 운영에만 쓰는 줄을 담는다 — 다계정 스킬 폴더, 본부 운영 폴더 경로, 개인 운영 도구, 바깥 자료의 원문 주소.
> 공개 후보를 만들 때 이 파일은 제외 목록에 들어간다(TICKET=cysr-1116-pubcand-1120 · master#9183812c D1 · master#9867870f D2).
> `scripts/asset_ledger_check.py` 는 공개 판정표 옆에 이 파일이 있으면 두 표를 합쳐 읽는다. 이 파일이 있을 때만 본부 전용 원천(영상 검토 산출물 폴더)을 훑는다.

## 3. 원천 (정확한 경로)

| 원천 | 만드는 키 |
|---|---|
| `~/.claude/skills` · `~/.claude-acct2/skills` · `~/.cys/local/skills` · `~/.cys/claude/skills` (합집합 · 점으로 시작하는 이름 제외) | `skill:<이름>` |
| `~/axdev/master/assets/` 의 맨 위 항목 | `asset:<이름>` |
| 도구 묶음 폴더(`motion-graphics-prompt` · `ppt-design-system` · `portrait-cutout` · `video-production`) 안의 맨 위 항목 — 묶음 자체는 키를 만들지 않는다 | `asset:<묶음>/<이름>` |
| `~/axdev/master/reports/video-reviews/assets/` 의 맨 위 항목 | `path:~/axdev/master/reports/video-reviews/assets/<이름>` |

## 4. 판정표 — 본부 전용 줄

| 항목 키 | 종류 | 있는 곳 | 출처·라이선스(재배포 근거) | 팩(dea2e1853) | 판정 | 초보 유익 | 근거 |
|---|---|---|---|---|---|---|---|
| `path:~/axdev/master/reports/video-reviews/assets/glance-test-checklist.md` | 점검표 | 검토 반영(IDX:41·86) | 우리 제작 · Duarte(원문 0)·unslop(CC-BY-4.0 · 방법만) | — | 넣음-자료 | 상 | PPT·문서가 3초에 읽히는가 — 초보도 표 그대로 씀 · 교회 양식 줄 일반화 → ppt-design-system/references/glance-test-checklist.md 로 동봉(master#fda41d2f D1) |
| `path:~/axdev/master/reports/video-reviews/assets/rea-*` | 지침·스킬 초안 | 검토 반영(IDX:39) | REA(MIT) · 원 영상 유료 거래 | — | 전용 | — | 미설치 초안 · 원 영상 비공개 거래 |
| `path:~/axdev/master/reports/video-reviews/2026-11-06-asset-refs` | 표 | 검토 반영(IDX:74) | ztd-charts(라이선스 미기재) | — | 전용 | — | 바깥 라이선스 불명 |
| `path:~/axdev/master/(docs·coaching·briefs·reports)` | 운영 문서 | 검토 반영 | master 운영 · 일부 실명·교회 | — | 전용 | — | 개인정보·master 운영 |
| `path:~/.claude/channels·~/Library/LaunchAgents·~/.claude/settings.json·~/axdev/gmail-brief·~/axdev/master/tools/kakao-room-send` | 운영 도구 | 검토 반영(IDX:69·75·101·105 · REF:114) | master 운영 · 개인 계정 | — | 전용 | — | master 운영 전용 · 개인 계정 |
| `path:~/axdev/(invest-study·video-study-*·workers/*/draft)` | 기록·초안 | 검토 반영(IDX:68·83·89·97·103) | 실험 기록 | — | 전용 | — | master 실험·견본 기록 |

## 5. 「있는 곳」 원문 (공개 본문은 「계정2」 표기를 뺐다)

공개 본문 §4 의 「있는 곳」 칸에서 「·계정2」·「·계정2↗」 를 지우기 전 원문이다. 두 칸짜리 표라 검사기는 판정 줄로 읽지 않는다.

| 항목 키 | 있는 곳(원문) |
|---|---|
| `skill:agents-sdk` | 본부·계정2 |
| `skill:agora-delegate` | 본부·계정2 |
| `skill:appbuild` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-orchestrate` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-orchestrate-delegate` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-orchestrate-route` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-orchestrate-verify` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-plan` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-plan-debate` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-plan-interview` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-plan-quick` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-screen-spec` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-screen-spec-detail` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-screen-spec-flow` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-supervisor` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-supervisor-collect` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-supervisor-fix` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-supervisor-gate` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-supervisor-verify` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-tasks` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-tasks-order` | 본부↗·계정2↗·좌석↗ |
| `skill:appbuild-tasks-slice` | 본부↗·계정2↗·좌석↗ |
| `skill:audio-post` | 본부↗·계정2↗·좌석↗ |
| `skill:audio-post-mix` | 본부↗·계정2↗·좌석↗ |
| `skill:audio-post-music` | 본부↗·계정2↗·좌석↗ |
| `skill:caption-align` | 본부↗·계정2↗·좌석↗ |
| `skill:caption-correct` | 본부↗·계정2↗·좌석↗ |
| `skill:cloudflare` | 본부·계정2 |
| `skill:cloudflare-email-service` | 본부·계정2 |
| `skill:cloudflare-one` | 본부·계정2 |
| `skill:cloudflare-one-migrations` | 본부·계정2 |
| `skill:computer-control` | 본부↗·계정2↗·좌석↗ |
| `skill:cost-preview-confirm` | 본부↗·계정2↗·좌석↗ |
| `skill:dept-by-chat` | 본부↗·계정2↗·좌석↗ |
| `skill:design-system-propagate` | 본부↗·계정2↗·좌석↗ |
| `skill:design-token-system` | 본부↗·계정2↗·좌석↗ |
| `skill:durable-objects` | 본부·계정2 |
| `skill:harness-engineering` | 본부↗·계정2↗·좌석↗ |
| `skill:heygen-avatar-render` | 본부↗·계정2↗·좌석↗ |
| `skill:heygen-avatar-render-api` | 본부↗·계정2↗·좌석↗ |
| `skill:heygen-avatar-render-gate` | 본부↗·계정2↗·좌석↗ |
| `skill:hwp` | 본부↗·계정2↗·좌석↗ |
| `skill:korean-character-count` | 본부↗·계정2↗·좌석↗ |
| `skill:korean-humanizer` | 본부↗·계정2↗·좌석↗ |
| `skill:korean-spell-check` | 본부↗·계정2↗·좌석↗ |
| `skill:media-gen` | 본부↗·계정2↗·좌석↗ |
| `skill:media-gen-edit` | 본부↗·계정2↗·좌석↗ |
| `skill:media-gen-image` | 본부↗·계정2↗·좌석↗ |
| `skill:media-gen-thumbnail` | 본부↗·계정2↗·좌석↗ |
| `skill:media-gen-upscale` | 본부↗·계정2↗·좌석↗ |
| `skill:media-gen-video` | 본부↗·계정2↗·좌석↗ |
| `skill:methodology-claim-audit` | 본부↗·계정2↗·로컬·좌석↗ |
| `skill:motion-graphics-prompt` | 본부·계정2·로컬↗·좌석↗ |
| `skill:narrated-motion` | 본부·계정2·로컬↗·좌석↗ |
| `skill:nlm-skill` | 본부·계정2 |
| `skill:notebook-source-pack` | 본부·계정2 |
| `skill:ppt-design-system` | 본부·계정2·로컬↗·좌석↗ |
| `skill:rhwp-edit` | 본부↗·계정2↗·좌석↗ |
| `skill:sandbox-sdk` | 본부·계정2 |
| `skill:scene-cut` | 본부↗·계정2↗·좌석↗ |
| `skill:script-writer` | 본부↗·계정2↗·좌석↗ |
| `skill:script-writer-factcheck` | 본부↗·계정2↗·좌석↗ |
| `skill:script-writer-research` | 본부↗·계정2↗·좌석↗ |
| `skill:script-writer-structure` | 본부↗·계정2↗·좌석↗ |
| `skill:script-writer-voice-prep` | 본부↗·계정2↗·좌석↗ |
| `skill:sfx-place` | 본부↗·계정2↗·좌석↗ |
| `skill:style-guide-ab` | 본부·계정2 |
| `skill:suite-runtime-keys` | 본부↗·계정2↗·좌석↗ |
| `skill:synced` | 본부·계정2·좌석 |
| `skill:transcription` | 본부↗·계정2↗·좌석↗ |
| `skill:turnstile-spin` | 본부·계정2 |
| `skill:video-report-deck` | 본부·계정2·로컬↗·좌석↗ |
| `skill:video-stitch` | 본부↗·계정2↗·좌석↗ |
| `skill:video-stitch-broll` | 본부↗·계정2↗·좌석↗ |
| `skill:video-stitch-captions` | 본부↗·계정2↗·좌석↗ |
| `skill:video-stitch-compositing` | 본부↗·계정2↗·좌석↗ |
| `skill:video-verify` | 본부↗·계정2↗·좌석↗ |
| `skill:video-verify-audio-sync` | 본부↗·계정2↗·좌석↗ |
| `skill:video-verify-final-gate` | 본부↗·계정2↗·좌석↗ |
| `skill:video-verify-timing` | 본부↗·계정2↗·좌석↗ |
| `skill:video-verify-visual` | 본부↗·계정2↗·좌석↗ |
| `skill:voice-clone-elevenlabs` | 본부↗·계정2↗·좌석↗ |
| `skill:voice-clone-elevenlabs-chunk` | 본부↗·계정2↗·좌석↗ |
| `skill:voice-clone-elevenlabs-synth-qc` | 본부↗·계정2↗·좌석↗ |
| `skill:voice-local` | 본부↗·계정2↗·좌석↗ |
| `skill:web-perf` | 본부·계정2 |
| `skill:workers-best-practices` | 본부·계정2 |
| `skill:wrangler` | 본부·계정2 |
| `skill:youtube-video-pipeline` | 본부↗·계정2↗·좌석↗ |

## 6. 바깥 자료 원문 주소 (공개 트리에서 뺀 것 · master#9867870f D2)

공개 낱말표가 노션 주소를 막으므로 공개 트리에는 지은이·제목·공개 영상만 적고, 원문 주소는 여기에만 둔다.

- 헤이디 「나만의 디자인 시스템 만들기 프로젝트 지침」 — https://app.notion.com/p/3f671a693e5480b2afeee6776d6ec9e2 (공개 노션 · 2026-11-06 08:13 KST 수신 · 2026-10-27 사본과 바이트 동일). 원문 사본 = 본부 자산 `ppt-design-system/SOURCE-heidi-guideline.md`. 팩 판(1.1.16 integ 3c740f492 까지)의 `references/heidi-guideline.md` 는 원문 동봉이었고, 11-20 에 우리 말 요약으로 바꿨다.
- 헤이디 「모션 그래픽 제작 프롬프트」 — https://app.notion.com/p/40371a693e5480bdaf3aec362419d8e0 (공개 노션 · 소개 영상 7xOcIYWGG0A).
