# HANDOFF — TICKET=skill-revisions-1120 (2026-11-20 · worker-3 surface:2311)

- 가지 = `feat/skill-revisions-1120` ← 기점 `1ff82d08a`(2307 asset-skills 머리) · 작업트리 `~/axdev/.wt/cys-skill-rev-1120`
- 브리프 = master 원장 spawn 09:30:05(surface:2311 · brief_file sha256 = 원장 body_sha256 · 끝 줄바꿈 1자 차)
- push·병합·설치 팩(`~/.cys/pack`)·`~/.claude/skills` 제자리 수정 = 하지 않음

## 끝난 것
1. 43건 전수 처분 → `docs/SKILL-REVISIONS-1120.md`(반영 21 · 일부 반영 2 · 이미 해소 4 · 안 함 8 · 새 기능 📌 4 · 박사님께 4)
2. 반영 = 커밋 `1d11445d5` — 26개 SKILL.md **본문만**(설명 frontmatter 변경 0)
3. 처분표에 고치기 전/뒤 한 쌍(diff 기계 추출) · 스킬 밖 항목(기억 카드 2 = master 몫 · tools 기본값 = 제안만)

## 시험(재현)
```bash
python3 scripts/asset_ledger_check.py                                   # 초록 139/140
python3 scripts/tests/test_asset_ledger_check.py                        # OK
python3 cysjavis-pack/bin/tests/run_bootstrap_health.py --only H-ASSET-1 # GREEN
cd cysjavis-pack/bin/tests && CYS_NO_AUTOSTART=1 python3 -m unittest test_output_skills   # 18 OK
PATH=$HOME/.cargo/bin:$PATH cargo test --lib -- pack_skills_embed_adopted_set_and_indexable install_writes_core_and_skills_to_fresh_dir skill_links_only_pack_targets_removed  # 3 passed
python3 cysjavis-pack/bin/javis_registry.py --root cysjavis-pack verify  # OK 124
git diff 1ff82d08a -- cysjavis-pack/skills | grep -c '^[-+]description:'  # 0
```

## 함정
- `javis_registry.py verify` 를 `CYS_PACK_DIR=<저장소 팩>` 으로만 돌리면 「드리프트 · 손편집 의심」 FAIL 이 난다(같은 순간 `--root cysjavis-pack verify` = OK · build 해도 카탈로그 diff 0). 반드시 `--root` 로 잰다.
- 이 셸(zsh)에서 `"…measured_thresh=$th:linear=true"` 는 `$th:l` 이 소문자 수식어로 먹혀 ffmpeg 가 「Invalid chars 'inear=true'」로 실패한다 → `${th}`. 스킬(audio-post-mix)에 1줄로 넣었다.
- `ffmpeg … showinfo` 를 `-v error` 로 돌리면 showinfo 줄이 안 나와 장면 검출이 「0건」처럼 보인다 — 양성 대조(빨강→파랑) 없이 재면 오판한다(이번에 1회 밟고 고쳐 잼).
- `cargo` 는 PATH 에 없다(`~/.cargo/bin`).
- korean-humanizer 앞머리가 `yaml.safe_load` 에 실패한다 — 이 가지와 무관한 기존 상태.

## 미완 · master 몫
- 📌 B5(`s2m_cues.py` 에 `engine: file`) = A1·A3 로 say 를 공개본에서 막았으니 **공개본을 만들 도구 길이 비어 있다** → 다음 티켓 1순위 권고. B6·B7·B8 = master 결정.
- 박사님께: B1~B4(돈·새 길).
- 기억 카드 숫자 2건(License.html 67줄 · Supertonic 6파일) = master 몫.
- tools 기본값: 브리프는 −1 dBTP, `workflow-checklist.md` 납품 기준은 **−2 dBTP** — 어느 값으로 맞출지 확인 필요(권고 −2).
- 검증 편성: 독립 검증 좌석 + codex 1R 은 master 가 붙인다. 이 좌석은 지적 1회 고침 대기.
