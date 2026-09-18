# HANDOFF — TICKET=injection-slim-T2-T5 (worker-4 surface:811 → 후임)

- 작성: 2026-09-18 19:1x KST · master 매듭 지시 839ed5d3(CTX 52% · 정지선 60% 접근)
- 브랜치: `fix/v110-inject` (분기 = rebase/v1.0.2 54c148cc) · WIP 커밋 `af4cea38`
- 정본: `~/axdev/master/reports/master-injection-slim/DESIGN-v2.md`(v2.1) §4·§7 · `T0-PROBES.md` · `drafts/`
- master 판정: 5cdfbd54 — ①A 예고 목차 = 사실형(절 이름 + 원문 경로·줄 범위) · 배포 = T2+T3 묶음 ②A 등록 2행은 T3 이월 · Rust 무접촉 · 해시 불일치 시 CORE 나머지 전체를 불일치 절 원문으로 교체(승인)
- 범위 경계: 팩 소스만. 라이브 `~/.cys/pack` · `~/.claude/settings.json` · 가동 중 페인 = 무접촉(지켰다).

## 1. 끝난 것 (커밋 af4cea38 · 실측)

| 항목 | 파일 | 확인 |
|---|---|---|
| T1 CORE 배치 | `cysjavis-pack/directives/MASTER_CORE.md` · `CEO_CORE.md` · `CORE-MIN.md` | drafts 와 sha256 3쌍 일치 · 이름 규칙상 System 소유(`src/pack.rs:1907` is_constitution_file = `_DIRECTIVE.md` 접미만 User) · build.rs 가 git ls-files 로 자동 임베드(추가 등재 불요) |
| T2 조립기 | `cysjavis-pack/hooks/core_inject.py`(신규) | `session` · `background` · `verify` 하위 명령. 블록 조립·자기 절단(누적 ≤8,800 · 고지 포함 ≤9,000 · 글자 = UTF-16 길이) · 절 해시 대조(drafts/sections.py·check_core_pins.py 와 같은 규칙) |
| T2 훅 ① | `cysjavis-pack/hooks/session-start.sh` | master·CEO 분기 = CORE-MIN → 출처 고지 → 역할 재대조 고지 → 각성 헤더 → CORE 나머지(불일치면 원문 절 · 부재면 원문 절) → 부트 브리지 → 사실형 목차. 브리지 문안 무변경(함수 `emit_boot_bridge` 로 감쌈). 조립기 실패·5초 초과 = 셸 폴백(CORE-MIN + 브리지). 워커·CSO·리뷰어 분기 = 무변경 |
| T2 훅 ②' | `cysjavis-pack/hooks/inject-background.sh`(신규 · 미등록) | 첫 줄 역할 가드(master 외 exit 0) · 5초 상한 · fail-open. 우선순위 §11 → §9(clear·compact·resume·fork) → soul(clear·compact·fork) → 메모리 색인(≤4,000) → 오버레이(≤3,000) |
| T2a | `session-start.sh` 워커 첫 턴 규율 블록 | 출력 맨 앞으로 이동(문안 무변경) · `test_session_start_hook.py` 7b 를 「앞 · 2,000자 안」으로 재조준(옛 계약 주석 보존) |
| T5 | `cysjavis-pack/bin/javis_preflight.py` C82.core-injection | 판정 코어 `core_injection_problems(pack, sh, timeout, home)` — 이름 규칙 · CORE 실재 · CORE-MIN 동일성 · 절 해시 · 두 훅 × startup·compact 드라이런(≤9,000 · 맨 앞 CORE-MIN · rc 0) · 가짜 cys 호출로 격리 자기 증명. 전 축 WARN(READY 미차단) |
| 시험 | `cysjavis-pack/bin/tests/test_core_inject.py`(신규) | 시나리오 A~H·P·Pw 전건 PASS · `--mutants` 17/17(적색 15 + 귀속 확인 2) · `--table` 드라이런 표 |

### 지시 없이 내린 판단 (master 【진행】 19:03 보고분)
1. 원문 절 묶음 = SKIP 의미(안 들어가는 절만 건너뛰고 계속). 규칙 0 그대로면 §0-C(6,086자) 한 절이 부트 브리지까지 끌고 나가 CORE 부재 시 부트 안내가 0 이 된다(치명 ③).
2. CORE 부재 모드에서는 부트 브리지·목차를 원문 절보다 앞에 둔다.
3. 절 구조가 없는 디렉티브 = 원문 앞부분을 남은 자리만큼 줄 단위 절단(CUT) — 무지침 차단. (기존 시험 2a·4a·5a 가 이것을 요구했다.)
4. C82 전 축 WARN — 해시 불일치는 훅이 이미 원문으로 강등하고, 크기 초과는 T2 이전 상태보다 나빠지지 않는다. FAIL 은 4군 ④ 위험.

## 2. 미완

- [ ] **CI 레인 등재** — `test_core_inject` 를 3완전 레인에 대칭 등재할지 master 【질문】(19:03) 답 대기. A(권고) 이 티켓에서: `.github/workflows/ci-branch.yml`(팩 루프 `test_session_start_hook` 옆) · `release.yml` 양 루프(424·1122행 부근) · `pack-release.yml`(188행 부근). 레인 대조 스텝(ci-branch.yml:83~)이 세 목록 드리프트를 검사하므로 **네 곳 모두** 넣어야 한다. B = T3/릴리스로 이월. `.github` 는 브리프 「팩 소스만」 밖이라 답 없이 커밋하지 않았다.
- [ ] 【단계완료】 보고 + 「T3 착수 전제 목록」 절(master 5cdfbd54 요구) — 아래 §5 를 그대로 쓰면 된다.
- [ ] 선택: 이종 리뷰(agy/codex) 1R — 이 티켓에서는 돌리지 않았다(시간·CTX). 권고 대상 = `core_inject.py` assemble·SKIP/CUT 의미 · C82 격리 방식.

## 3. 함정

- **cargo 는 PATH 에 없다** → `export PATH="$HOME/.cargo/bin:$PATH"`. 없으면 rc 127 이 「실패」로 보인다.
- **build.rs 는 git ls-files 로 임베드** — 새 파일을 `git add` 하기 전의 cargo 통과는 새 파일이 빠진 판을 잰 것이다. 이 티켓의 cargo 508 은 add 후 재측정값이다. health `H-PACK-TRACK-1` 도 add 전엔 적색.
- **H-WIN-7** 은 cygpath 목이 모든 `-w` 인자를 `X:\Prog Files\javis_bootstrap.py` 로 바꾼다 → 조립기 경로도 망가져 **셸 폴백으로 통과**한다. 폴백 경로를 지우면 그 검체가 적색이 된다(설계상 정상).
- 최소 팩 픽스처(test_session_start_hook 등)는 팩에 core_inject.py 가 없어도 훅이 `$(dirname "$0")/core_inject.py` 로 **저장소 훅 폴더의 조립기**를 집는다 — 훅·조립기 버전 잠금 의도.
- 원본 훅의 잠재 결함(범위 밖 · 동작 보존): claim-role rc 6 이면 고지가 두 줄(rc6 전용 + 「데몬 미응답」) 찍힌다. 같은 절 주석은 두 번째 문구를 오진이라 적는다. ROLE_NOTICE 로 옮기면서 두 줄 그대로 보존했다.
- 최악 조합 compact 에서 **메모리 색인은 통째로 빠진다**(블록 단위 규칙 0). DESIGN §4-4 는 「색인 일부가 잘린다」고 적었으나 블록 단위 조립(§4-3 규칙 0)과 합치면 전부 빠지는 것이 맞다 — 이름은 절단 고지에 남는다.
- CEO 좌석은 CORE 나머지가 길어(요지 5,642자) 전형에서도 **목차가 빠진다**(7,371자 · 절단 고지 1줄).
- zsh 에서 `echo =====` 는 `=cmd` 확장으로 오류가 난다 — 구분선은 다른 문자로.

## 4. 재현 명령 · 기준선 수치

```bash
cd ~/axdev/.wt/cys-v110-inject
python3 cysjavis-pack/bin/tests/test_core_inject.py --table          # A~H·P·Pw + 드라이런 표 (~10s)
python3 cysjavis-pack/bin/tests/test_core_inject.py --mutants        # 뮤턴트 17종 (~1분)
CYS_PACK_DIR="$(mktemp -d)" python3 cysjavis-pack/bin/tests/test_session_start_hook.py   # 59 PASS
python3 cysjavis-pack/bin/tests/run_bootstrap_health.py --json > /tmp/h.json             # ~6.5분
export PATH="$HOME/.cargo/bin:$PATH"; CYS_PACK_DIR="$(mktemp -d)" cargo test --lib -- --test-threads=1   # ~4분
python3 scripts/gen_ceo_template.py --check
python3 -c "import sys;sys.path.insert(0,'cysjavis-pack/bin');import javis_preflight as p;print(p.core_injection_problems('cysjavis-pack'))"
```

| 스위트 | 변경 전(54c148cc) | 변경 후(af4cea38) |
|---|---|---|
| run_bootstrap_health | GREEN 149 pass · 0 fail · 1 skip(H-WIN-11) / 150 | add 전 148 pass · 1 fail(H-PACK-TRACK-1 = 미추적) → add 후 `--only H-PACK-TRACK-1` GREEN(추적 652 · 누락 0). **전건 재실행은 add 후 미실시** |
| cargo test --lib | 508 pass · 0 fail · 1 ignored | 508 pass · 0 fail · 1 ignored(add 후 재측정) |
| gen_ceo_template --check | GREEN | GREEN |
| test_session_start_hook | 59 PASS | 59 PASS(7b 재조준) |
| test_core_inject | (신규) | 전건 PASS · 뮤턴트 17/17 |

드라이런(워크트리 팩 · C82 코어): 훅① startup·compact 6,810자 · 훅②' startup 2,277 / compact 7,541.
최악 조합(test_core_inject E · soul 4,068자 · 색인 1,500줄 · 오버레이 900줄 · 재대조 고지):

| source | 훅① 글자 | 훅① 고지 | 훅②' 글자 | 훅②' 자기 절단 |
|---|---:|---|---:|---|
| startup | 7,078 | 재대조 고지 | 7,796 | 없음 |
| compact | 7,078 | 재대조 고지 | 7,966 | 메모리 색인 · 로컬 오버레이(이름 고지) |

E2E(격리 `claude -p` · 계정2 프로필 `~/.cys/claude` 읽기만 · `--setting-sources project` · 훅 2개만 `--settings` · 가짜 cys · 자격증명 복사 0):
- 세션 `8bf44182-d218-4edb-8723-5a6c377d3e29` · 기록 사본 = 스크래치 `e2e/transcript.jsonl`(원본은 계정2 프로필 `projects/…scratchpad-e2e-cwd/` — 부산물 폴더 1개 · 미삭제)
- jsonl 4행 훅① 첨부 6,974자 · CORE-MIN 으로 시작 · 저장 안내 없음 / 3행 훅②' 첨부 2,385자 · 저장 안내 없음
- 모델 응답: ①CORE-MIN 머리줄 글자 그대로 ②목차 끝줄 `· §14 ★자율주행 위임권 (Autonomous Pilot Manda… — 줄 636–686` 글자 그대로 ③저장 안내 받음 = 아니오

## 5. T3 착수 전제 목록 (master 5cdfbd54 요구)

1. **등록 2행을 한 번에**(DESIGN §4-4·§7 T3): ①`inject-background.sh` SessionStart ②`directive-event-inject.sh` PreToolUse(matcher Bash). 둘 다 `"timeout": 5` 명시. 손댈 곳 = `src/pack.rs` 소망상태 표(AWAKENING_HOOKS 계열 · 394행 부근) · `bin/javis_preflight.py` SELFCORR_HOOKS(366행 부근) 또는 C08 계열 + `HOOK_TIMEOUT_S` · `bin/tests/run_bootstrap_health.py` H-SEED-1(4-튜플 대조) · 윈 `bootstrap.ps1`. `--fix` 가 `~/.claude/settings.json` 에도 쓰는지(U7) 착수 전 확인.
2. **예고 목차 → 사건 주입 전환 지점**: 현재 목차 문안(`core_inject.py` `toc_block`)은 사실형 「필요하면 그 절의 줄 범위만 읽어라」다. T3 가 사건 주입을 켜면 이 머리줄과 CORE-MIN 6번(「해당 명령을 실행하면 원문이 자동으로 들어온다」)이 비로소 참이 된다 — T3 전까지 CORE-MIN 6번의 명령 쪽은 거짓이므로 **T2 는 T3 와 묶음으로만 배포**(master ①A).
3. 절 추출은 `core_inject.py` 의 `split_sections`·`keyed_sections`·`section_spaces`(CEO 본문 오프셋 포함)를 재사용하면 된다 — 사건 훅의 원문 추출과 규칙이 같아야 해시·줄 범위가 일치한다.
4. 원장 키 = `session_id` + (있으면) `agent_id`(T0-PROBES ⓒ) 또는 `agent_id` 있으면 즉시 종료 — T3 결정.
5. C82 는 현재 훅 ①·②' 만 드라이런한다 — T3 에서 사건 훅의 트리거 제목 실재 검사(§4-6-5)를 C82 또는 별도 축에 추가.
6. `inject-background.sh` 가 등록되기 전까지 master 의 soul·색인·오버레이는 훅 ①에서 빠진 상태다(현행도 81KB 저장이라 실제 도달량은 0 — 순손실은 「읽을 수 있던 저장 파일」뿐).
