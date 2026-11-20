# HANDOFF — TICKET=cysr-1116-asset-skills-1120 (2026-11-20 · worker-3 surface:2307)

- 가지 = `feat/1116-asset-skills` ← 기준판 1.1.16 `dea2e1853` · 작업트리 = `~/axdev/.wt/cys-1116-assetskills`
- 반영한 master 지시 = 브리프(원장 spawn 08:28:56) · master#0eae06c1(범위 확대) · master#5a3e7ccc(초보 유익 칸) · master#fda41d2f(D1~D3 기본값 · 이식 착수). 넷 다 원장 대조 완료.
- push·태그·CI·`~/.cys/pack` 라이브 설치 = 하지 않음.

## 끝난 것

1. **skill-fold 이식**(`feat/1112-skill-fold` 2커밋). 브리프는 이 가지가 없다고 했으나 실재했다(가지 이름이 `feat/1112-skill-fold`).
   - 충돌 1건: `computer-control/SKILL.md` 설명.
     - 기준판이 유휴 관문(javis_idle_gate) 뜻을 더했고, fold 는 설명을 줄였다.
     - 기준판 우선으로 처리했다. 짧은 설명에 유휴 관문 뜻을 넣었고, 「원 설명」 절에는 기준판 원문을 보존했다.
2. **asset-skills 이식**(`feat/asset-skills` 16커밋). 충돌 0. HANDOFF-asset-skills.md 의 이월 전부를 그대로 실었다.
3. **새 승격 3종**: `narrated-motion` · `style-guide-ab` · `notebook-source-pack`.
   - 개인 경로·호칭·교회 줄을 일반화했다.
   - 설명은 150자 이하로 줄이고, 원문은 「원 설명」 절에 보존했다.
   - narrated-motion 의 렌더 도구 경로는 형제 스킬 `<M>/tools/seek_render.js` 로 고쳤다(SR A12).
4. **motion-graphics-prompt 본부 최신 반영**(11-10·11-11 갱신분):
   - narrated-motion 갈래 안내 · CUE(문장 번호) · 시드 난수 · 캔버스 상태 초기화 · 헤드리스 시간 예측 · 레퍼런스 확인법
   - seek_render.js 새 페이지 재촬영 검사
5. **참고 자료 2장**(D1):
   - `appbuild-screen-spec/references/ui-terms-24.md`
   - `ppt-design-system/references/glance-test-checklist.md`
6. **배선**:
   - `OUTPUT_SKILLS` 21종(preflight C84) · pack.rs 임베드 불변식 21종 · test_output_skills `NEW_ASSET_SKILLS` 8종.
   - capability_catalog 재생성(verify OK · 124).
   - THIRD_PARTY 고지 1절 추가.
7. **판정표** `docs/ASSET-LEDGER.md`(140줄 · 초보 유익 칸 · D2 = 팩 밖. 이유: build.rs 가 팩 폴더 전 파일을 임베드한다).
8. **빠짐 방지 게이트**:
   - `scripts/asset_ledger_check.py` + 부트 건강성 검체 **H-ASSET-1**.
   - 시험 `scripts/tests/test_asset_ledger_check.py` 14건.
   - 뮤턴트 `scripts/asset_ledger_mutants.py` **11/11 KILLED**.
9. **이력 정리**: 이식한 DESIGN-asset-skills.md 의 개인 절대 경로 1줄을 이력 전체에서 `~` 로 바꿨다(filter-branch · 이 가지 로컬만 · push 전).

## 실측(재현 명령은 아래)

| 항목 | 결과 |
|---|---|
| 게이트 산 판정 | `✓ asset-ledger: 초록 — 원천 139개 전부 판정표에 있음 · 판정표 140줄` |
| H-ASSET-1 | PASS · 판정표 한 줄(skill:style-guide-ab)을 빼면 FAIL(되돌림 확인) |
| 뮤턴트 | 11/11 KILLED (M7·M11 은 1차 SURVIVED → 시험 2건 추가 후 KILLED) |
| test_output_skills | 18/18 OK |
| cargo pack 3종 | `pack_skills_embed_adopted_set_and_indexable` · `install_writes_core_and_skills_to_fresh_dir` · `skill_links_only_pack_targets_removed` ok |
| doc-contract 3줄 | gen_ceo_template --check GREEN · test_bootv2_doc_contract ALL PASS · test_event_inject ALL PASS |
| 팩 시험(스킬 관련) | test_idle_gate OK · test_review_prompt_verdict_path OK · test_vibecheck OK · test_v115_dept 93 OK · javis_registry verify OK |
| secret-scan | 가지 변경 파일 191개 clean · 이력 범위 개인 경로 0 |
| 격리 HOME 새 좌석 | `--wire-seat` C26·C27·C29·C84 FIXED · 링크 76 · 넣은 8종 + 참고 자료 2장 실재 · Claude Code 「Loaded 76 unique skills (user: 76)」 |

### 설명 예산(좌석 30,000자)

| 측정 | 스킬 수 | 자 |
|---|---|---|
| ① 지금 본부 좌석 `~/.cys/claude`(1.1.14 팩 · fold 없음) | 112 | **34,224 (초과)** |
| ② 같은 스킬 집합만 · 프로젝트 모드 | 87 | 31,979 |
| ③ 1.1.16 좌석 집합만 · 프로젝트 모드(같은 플러그인) | 48 | 13,417 |
| ④ 플러그인만 | 14 | 6,956 |

- ① 은 `claude -p --debug-file` 의 「Skill listing over budget」 줄이다.
- ②③④ 는 `--setting-sources project` + `skillListingBudgetFraction 0.0001` 로 쟀다. 예산을 일부러 아주 작게 해 언제나 합계가 찍히게 한 것이다.
- ①−② = 2,245 는 1.1.16 이 바꾸지 않는 몫이다(사용자 설정의 5번째 플러그인 + claude.ai 동기 이름).
- **1.1.16 좌석 ≈ ③ + 2,245 = 15,662자 / 30,000** — 예산 안이다.
- 확신도는 중상이다. 실좌석 프로필 자체를 1.1.16 으로 갈아 끼워 잰 값이 아니다. 같은 모드에서 두 집합을 잰 차이를 실측 ①에 더한 값이다.
- ⚠ 「이름 + 설명 + 5자」 공식은 한 줄당 숨은 몫(약 50~100자)을 설명하지 못해 쓰지 않았다(공식 추정 21,042).

## 미완·주의

- **판 대조**: 본부 좌석이 링크하는 팩 스킬 69 은 설치 팩 1.1.14 파일이다. 블롭이 전부 저장소 이력에 있어 본부 쪽이 더 새것인 것은 0 이다.
- **vendor-check BLOCK**(insane-search 4파일 드리프트)은 기준판 dea2e1853 에서도 같다 — 이 가지와 무관하며 기존 부채다.
- **notebook-source-pack 의 명령 정본 nlm-skill** 은 팩에 싣지 않았다(판정 = 링크). 좌석에 없으면 `nlm skill install claude-code` 를 한 번 돌린다(SKILL 0단계에 1줄).
- **본부 원본은 그대로다**: `~/.claude/skills` 의 실디렉토리와 `~/.cys/local` 링크는 그대로다. 다음 판 이후 좌석은 팩 판을 쓴다(팩 동명 우선 · C84).
- **D4(범위 밖 · master 처리)**: skill-revisions 제안 43건 미적용 · INDEX 「미반영」 2건 실제 반영됨 · 비밀 파일 deny 규칙 미적용 · INDEX `assets/…` 경로 2건.
- **게이트 원천은 이 맥에만 있다**: CI·사용자 기계에서 H-ASSET-1 은 「원천 없음」으로 판정 값·팩 실재만 본다. 본부 기계의 발행 전 로컬 게이트(run_bootstrap_health)에서 원천 대조가 발효한다.

## 재현

```bash
python3 scripts/asset_ledger_check.py                       # 게이트(본부 기계 = 원천 대조)
python3 scripts/tests/test_asset_ledger_check.py            # 14
python3 scripts/asset_ledger_mutants.py                     # 11/11 KILLED
python3 cysjavis-pack/bin/tests/run_bootstrap_health.py --only H-ASSET-1
cd cysjavis-pack/bin/tests && CYS_NO_AUTOSTART=1 python3 -m unittest test_output_skills
cargo test --lib -- pack_skills_embed_adopted_set_and_indexable install_writes_core_and_skills_to_fresh_dir skill_links_only_pack_targets_removed
# 예산: 좌석 실측
echo "reply OK" | env -u NODE_OPTIONS CLAUDE_CONFIG_DIR=$HOME/.cys/claude claude -p --settings '{"disableAllHooks":true}' --debug-file X
# 예산: 집합 비교(프로젝트 .claude/skills 에 집합 링크)
echo "reply OK" | env -u NODE_OPTIONS CLAUDE_CONFIG_DIR=$HOME/.cys/claude claude -p --setting-sources project --settings '{"disableAllHooks":true,"skillListingBudgetFraction":0.0001}' --debug-file X
# 격리 HOME 새 좌석(임시 폴더 밑이면 preflight 가 등록을 막는다 — 작업 폴더 밑에 만든다)
env -i HOME=$H PATH=… CYS_PACK_DIR=$H/.cys/pack CLAUDE_CONFIG_DIR=$H/.cys/claude python3 $H/.cys/pack/bin/javis_preflight.py --wire-seat
```
