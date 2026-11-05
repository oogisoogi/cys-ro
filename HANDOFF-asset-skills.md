★병합 순서(master#7bdbbeb4 K1⑴ · 반드시): 1.1.13 묶음에서 `feat/1112-skill-fold`(a13450ae 계열)를 **먼저** 병합하고 그 뒤에 이 가지 `feat/asset-skills`를 병합한다 — 두 가지는 충돌 0(`git merge-tree` rc 0)이지만, 이 순서여야 좌석 스킬 설명 예산(30,000자) 안에 들어온다.

# HANDOFF — TICKET=asset-skills-for-seats (2026-11-06 · worker-assetskills surface:1822)

- 가지 = `feat/asset-skills` ← 10802555 · 작업 폴더 = `~/axdev/.wt/cys-asset-skills`
- 설계·결과 정본 = `DESIGN-asset-skills.md`(§1 실측 · §2 자산 전수표 · §3 설계 · §4 결과)
- push·태그·릴리스·`~/.cys/pack` 덮어쓰기 = 하지 않음(master 몫)

## 끝난 것
1. **좌석 배선(C84 · `cysjavis-pack/bin/javis_preflight.py`)**
   - `OUTPUT_SKILLS` 18개를 좌석 프로필에 링크한다: 자산 승격 5(motion-graphics-prompt · video-report-deck · ppt-design-system · ppt-styles · portrait-cutout) + 기존 산출물 13.
   - 사용자 오버레이 `~/.cys/local/skills/*`도 링크한다(D4).
     - 팩 동명은 생략한다(팩 우선).
     - 끊긴 로컬 링크는 걷어 낸다.
     - 같은 이름의 사용자 링크·실디렉토리는 불가침이다.
     - 「우리 링크」 = 이 팩·오버레이·형제 `pack*/skills` 아래만.
   - cys 좌석 프로필(`~/.cys/claude*`)의 claude.ai 동기 스킬을 `skillOverrides: name-only`로 둔다(K1⑵).
     - 사용자 값과 다른 키는 보존한다.
     - 개인 `~/.claude`는 불가침이다.
   - 부르는 곳 3곳이 같은 코드를 쓴다: 좌석 기동 직전(`--wire-seat`) · `cys init-pack` · 각성 `--fix`.
2. **factory_reset `--purge-local`**: 로컬 스킬 링크를 경로 구성요소 비교로 걷는다(`src/factory_reset.rs remove_local_skill_links`).
3. **pack.rs 임베드 불변식**: 산출물 18종을 추가했다.
4. **THIRD_PARTY.md**: 헤이디 PPT 지침(⑴ 동봉 근거 문장) · theme-factory(Apache-2.0) · frontend-slides(MIT)를 고지했다.
5. **skill-writing**:
   - 시험 입력 2~3개 + 스킬 없이 대조 1회(master#f7f0e7bc).
   - 「남의 자료에서 스킬 만들 때」 4줄.
6. **이 맥 배선**: master 원본 3개를 `~/.cys/local/skills`에 링크했다. 저장소 판 `--wire-seat`로 HQ·dept-1을 배선했다. 동기 스킬 이름만은 HQ 22개.

## 좌석별 설명 합계 / 예산(`claude -p --debug-file` 의 「Skill listing over budget」 실측)
| 좌석 | 프로필 | 자수 / 30,000 |
|---|---|---|
| 본부 master · worker · cso | `~/.cys/claude`(셋이 같은 프로필) | 전 38,707(92) → 배선 뒤 45,159(109) → 동기 이름만 뒤 **32,691(109)** |
| dept-1 | `~/.cys/claude-default-dept-1` | **미측정**(OAuth 만료 · 초과 경고 없음 · init 88개 · 동기 스킬 0) |

- 남은 초과 2,691자는 skill-fold 선병합으로 없어진다고 추정한다. 우리 몫 설명이 약 11,870자 준다(설명 글자 기준 · 실측 아님). 그러면 약 20,800자다.
- **병합 뒤 할 일**: 같은 명령으로 다시 재서 확인한다.

## 미완·주의(함정)
- **다음 판에 들어가는 스킬**: ppt-styles · portrait-cutout은 설치 팩에 없다. 이 맥 좌석에는 다음 판(init-pack)에서 들어온다. C84 WARN 「pack 스킬 미설치(5)」는 그때 사라진다.
- **스킬 의존 위치**: `~/.cys/deps/<스킬>`(`CYS_SKILL_DEPS` · ppt-styles 는 `PPT_STYLES_DEPS`).
  - 팩 폴더 안에 설치하면 안 된다. 팩 갱신이 팩 폴더를 통째로 교체한다.
  - 팩은 `include_str!` 임베드라 바이너리(글꼴·그림)를 실을 수 없다.
- **팩 판과 원본**: 이 맥의 master 원본 3개는 실디렉토리(master 프로필)와 로컬 링크(좌석)로 남는다. 다음 판 이후 좌석은 팩 판을 쓴다(팩 동명 우선 규칙).
- **원문 받기 도구**: `javis_asset_fetch.py`는 팩에서 뺐다(⑵ 원문 0건). 코드는 9100fb07에 있다. 되살릴 때 codex 1R 지적 5건(리다이렉트 · 응답 구조 검증 · 요약 심링크 탈출 · 누적 크기 · 캐시 쌍 원자성)을 먼저 고친다.
- **윈도**: 실기 0회. 정적 시험만 했다(접두·대소문자 정규화).
- **skillScan**: ppt-styles가 BLOCK이다. HIGH = check_pptx.py 의 subprocess · 기존 insane-search·transcription 과 같은 등급이다.

## 재현
- 시험:
  - `cd cysjavis-pack/bin/tests && CYS_NO_AUTOSTART=1 python3 -m unittest test_output_skills` → 18/18
  - `cargo test --lib -- pack_skills_embed_adopted_set_and_indexable install_writes_core_and_skills_to_fresh_dir skill_links_only_pack_targets_removed`
  - `cargo test --bin cys dbg_r12_init_pack`
- 예산:
  - `echo "reply OK" | env -u NODE_OPTIONS CLAUDE_CONFIG_DIR=$HOME/.cys/claude claude -p --settings '{"disableAllHooks":true}' --debug-file X --output-format stream-json --verbose`
  - X 에서 `Skill listing over budget`
- 발동: 격리 프로젝트 `.claude/skills` 에 좌석 집합 + `claude -p --setting-sources project`(skill-fold 가지 `scripts/skill_trigger_regress.py`) → 10/10.
- 검증 이력: codex 1R REVISE 8 → 2R 12 → 3R 2 → 4R ACCEPT(미해소 0) · K1 구현분은 단위 시험 + 실측만(codex 미의뢰).
