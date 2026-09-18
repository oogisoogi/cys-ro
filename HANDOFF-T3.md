# HANDOFF — TICKET=injection-slim-T3 (worker-4 surface:812 → 후임)

- 작성: 2026-09-18 19:3x KST · master 매듭 지시 383ded1a(CTX 47.9% · 1.3%p/분)
- 브랜치: `fix/v110-inject` · 커밋 `24384392`(CI 레인 T2 잔여) → `cf865f9d`(T3 WIP) · **origin push 완료**(ls-remote = cf865f9d)
- master 판정(원장 대조 완료): 6255b46b = 사건 훅은 **PreToolUse(Bash)**(브리프 「PostToolUse」는 오기) · b286f358 = D10 **A**(§14 거부 트리거 = `javis_mission.py set` · 세션당 1회 · 재실행 허용 · §0-C 는 추가 문맥 · C 기각) + 트리거 사전 승인(표 머리 「데이터 표 · 수정 = 1줄」 + 행마다 근거 — 반영함)

## 0. 후임이 읽을 최소 범위

- **이 파일 + `HANDOFF-T2.md` 만.** 재정독 금지: DESIGN-v2.md 전문 · T0-PROBES.md 전문 · MASTER_DIRECTIVE.md 전문 · WORKER_DIRECTIVE(각성 때 읽음).
- 코드는 필요한 곳만: `cysjavis-pack/hooks/core_inject.py` 의 `# ── 사건 주입 ⓓ` 절(EVENT_TRIGGERS ~ cmd_event) · `hooks/directive-event-inject.sh`(62줄) · `bin/tests/test_event_inject.py` 머리 docstring.

## 1. 끝난 것 (실측)

| 항목 | 파일 | 확인 |
|---|---|---|
| T2 잔여 ① health 전건(add 후) | — | 79b0e909 기준 GREEN 149 pass · 0 fail · 1 skip(H-WIN-11) · 393.6s |
| T2 잔여 ② 계정2 부산물 폴더 삭제 | `~/.cys/claude/projects/…-9ecec625-…-scratchpad-e2e-cwd/` | 경로 보고(19:18:45) → 사본 sha256 1898f7c8 일치 확인 후 삭제. 사본 = 내 스크래치 `t2-evidence/transcript.jsonl` |
| T2 잔여 ③ CI 등재 | `.github/workflows/{ci-branch,release(양 루프),pack-release}.yml` | test_core_inject(24384392) · test_event_inject(cf865f9d) 대칭 등재 · 레인 대조 게이트 로컬 실행 비대칭 0 · **CI 미러 push 는 master 게이트(미실행)** |
| 사건 훅 | `hooks/directive-event-inject.sh`(신규) | 역할 가드 → surface → stdin 셸 내장 판독 → `agent_id` 즉시 종료 → 트리거 낱말 `case` 거름 — 여기까지 **외부 프로세스 0**(시험 Z · 기록용 가짜 명령 대조군 포함). 일치 시에만 `_lib.sh`·`core_inject.py event`(cys_timeout_run 5) · fail-open |
| 판정·조립 | `hooks/core_inject.py` `event` | 트리거 사전 `EVENT_TRIGGERS`(11행) · 세그먼트 파서 `split_commands` · 원장 `$CYS_STATE_DIR/directive-event/<session_id>.jsonl`(mkdir 락 + rename 회수 · lock_fail · parse_fail · fence · miss) · §14 deny · `assemble` 로 ≤9,000 · 못 실은 절은 원장에 안 남김(다음에 실림) |
| 목차 전환 | `toc_block` + `auto_marks` | 사실형 → 「⇐ 표시 절은 계기에 원문이 자동으로 들어온다」 · ⇐ 표지는 사전에서 파생(사본 0) |
| CORE-MIN 6번 | `directives/CORE-MIN.md` · `MASTER_CORE.md` · `CEO_CORE.md` | 3파일 동일 문안 · **1,599자**(상한 1,600 — 여유 1자. 더 쓰면 C82 적색) · 계기 이름 나열 + 「원문은 결과와 함께 오니 첫 실행은 요지를 따른다」 + mission set 1회 보류 |
| 등록 2행 | `bin/javis_preflight.py` | `SELFCORR_HOOKS` += inject-background(SessionStart) · directive-event-inject(PreToolUse, "Bash") · `HOOK_TIMEOUT_S` 두 행 5초 · C28 문구 8종 · health `_fake_pack_with_hooks` 2파일 추가 |
| C82 축 추가 | `core_injection_problems` | ⑤ 트리거 절 실재(설치 디렉티브 + 팩 CEO_TEMPLATE) ⑥ CORE-MIN 이 사전 계기 이름을 전부 말하는가(문안 드리프트) ⑦ 사건 훅 드라이런(트리거 = 원문 JSON ≤9,000 · 비트리거 = 무출력 · 원장 격리 폴더) |
| 시험 | `bin/tests/test_event_inject.py`(신규) | 15시나리오(T·N·X·R·O·D·F·S·M·P·L·Z·C·Q·W) ALL PASS · `--mutants` **15/15 KILLED**(크래시·미적용은 무효 처리) |

### 지시 없이 내린 판단 (【단계완료】에 명기할 것)
1. **Rust 무변경.** 브리프는 「pack.rs AWAKENING/HOOK 표」를 적었으나 `AWAKENING_HOOKS` 는 「없으면 부트가 안 나는」 각성 티어이고 H-SEED-1 ⓐ 가 이벤트 집합을 {SessionStart, UserPromptSubmit} 로 못박는다. 비각성 훅(inject-context·save-state …)은 전부 preflight C28 단독 등록이 선례 → 그 표에 넣었다. 부트가 preflight `--fix` 를 돌리므로 등록 경로는 같다. master 가 Rust 등재를 원하면 H-SEED-1 ⓐ 개정이 함께 필요하다.
2. **CEO 전용 행 1개**: `cys-dept` → `[부서 수명주기]`(master 승인 표에 「CEO 전용 추가」로 들어 있던 행).
3. §14 거부 때는 같은 명령의 §0-C 를 원장에 안 남긴다 → 재실행(허용) 때 §0-C 가 추가 문맥으로 실린다(master 「§0-C 는 추가 문맥」과 정합).
4. 비인용 heredoc 본문의 `$(…)`·백틱은 실행되므로 대조한다(인용 heredoc·작은따옴표는 제외). 셸(sh·bash·zsh·dash·ksh)이 받는 heredoc 은 본문 전체를 재귀한다.
5. 훅 1차 거름에서 `feed` 는 `'cys feed'`·`'cys --socket'`·`'cys -s '` 로 좁혔다(cwd·경로의 「feed」 낱말로 파이썬이 뜨지 않게).

## 2. 미완 (후임 순서)

- [ ] **E2E(격리 `claude -p` · 계정2 · 자격증명 복사 0)** — T0 방식 그대로: `--setting-sources project` · `--settings` 로 사건 훅 1개만 PreToolUse(matcher Bash, timeout 5) · 스크래치 cwd · 가짜 팩(`CYS_PACK_DIR`) · `CYS_ROLE=master CYS_SURFACE_ID=x CYS_STATE_DIR=<스크래치>`. 트리거별: 모델에게 `cys launch-agent …`(가짜 cys 를 PATH 앞에) 실행 후 「추가 문맥에서 `■ 원문 §2 (줄` 줄을 그대로 적어라」 → 되말하기로 판정. §14: `python3 <가짜팩>/bin/javis_mission.py set x`(가짜 스크립트) → 첫 호출 거부 사유가 모델에 보이고 재실행 허용되는지. 서브에이전트 1건(Agent 도구로 트리거 실행 → 무주입 · 원장 0). 끝나면 **계정2 프로필의 스크래치 cwd 기록 폴더 1개**를 경로 보고 후 삭제(T2 선례). 재현 스크립트 = 전임 스크래치 `…/9ecec625-…/scratchpad/e2e/run-inject-background.sh` 가 T2 판 견본(없으면 T0 `probes/run-claude.sh`).
- [ ] **스위트**: health 전건(`--json` · 약 6.5분 · 백그라운드) · `cargo test --lib`(Rust 무변경이라 기준선 508 pass 재확인만 · PATH 에 `~/.cargo/bin`) · `scripts/gen_ceo_template.py --check`.
- [ ] **agy 1R**(`unset NODE_OPTIONS` 서브셸 · `-p` 인자에 본문 · `--print-timeout 15m`) 대상: `core_inject.py` 사건 절(파서 우회 반례·락 회수·원장 판정) + `directive-event-inject.sh` → 수용/기각 표.
- [ ] 【단계완료】: 커밋 · E2E jsonl · 스위트 수치 · agy 표 · 4군 · 배포 전제 체크리스트(아래 §5).

## 3. 함정

- CORE-MIN 은 **1,599/1,600자**. 트리거 행을 늘리면 C82 ⑥ 이 CORE-MIN 에 그 계기 이름을 요구한다 → 문안을 줄여 자리를 만들어야 한다(3파일 동일 · C82 동일성 축).
- `test_core_inject.py` 의 `make_pack` 은 CEO_TEMPLATE 을 복사하지 않는다 → C82 ⑤ 가 사본 팩에서 13건(master 만) · 레포 팩에서 27건. 둘 다 정상.
- 사건 훅은 `~/.claude/settings.json`(cmux 페인)에도 등록된다(U7 · base 레인 home-glob). **역할 가드가 유일한 방어** — 첫 줄을 옮기거나 지우면 cmux master 의 모든 Bash 앞에서 돈다(시험 R + 뮤턴트가 잡는다).
- 뮤턴트 하네스: 변이가 문법을 깨면 이제 CRASH(무효)로 센다 — 종전처럼 KILLED 로 세지 않는다.
- PostToolUse 커밋 넛지(「방금 git commit 했다」)는 heredoc 본문에 commit 낱말만 있어도 뜬다(기지 오발 · 무시).
- drafts(`~/axdev/master/reports/master-injection-slim/drafts/`)의 CORE 3파일은 **CORE-MIN 6번 이전 문안**이다 — 팩이 정본이 됐다. T2 의 「drafts 와 sha256 3쌍 일치」는 이제 거짓이다(drafts 는 건드리지 않았다).

## 4. 재현 명령 · 기준선

```bash
cd ~/axdev/.wt/cys-v110-inject
python3 cysjavis-pack/bin/tests/test_event_inject.py [--mutants]      # ~4s · 뮤턴트 ~1분
python3 cysjavis-pack/bin/tests/test_core_inject.py --mutants          # T2 17/17 유지 확인
python3 -c "import sys;sys.path.insert(0,'cysjavis-pack/bin');import javis_preflight as p;print(p.core_injection_problems('cysjavis-pack'))"
```

| 측정 | 값 |
|---|---|
| test_event_inject | ALL PASS · 뮤턴트 15/15 |
| test_core_inject | ALL PASS · 뮤턴트 17/17(CORE-MIN·목차 변경 후 재측정) |
| test_session_start_hook · test_preflight_hook_body · test_preflight_win_hook_launcher · test_todo_shared_constants | 전부 통과 |
| health H-SEED-1 단건 | GREEN(전건은 미실행 — §2) |
| C82 레포 팩 | 문제 0 · 드라이런 session-start 7,355 · inject-background 2,301/7,565 · event/launch-agent 4,008 |
| 최악 조합(test_core_inject E) | 훅① 7,587 · 훅②' startup 7,796 / compact 7,966 |
| 지연(맥 · 하네스 포함 5회 중앙값) | 비일치 0.004s · 일치(첫 주입) 0.052s |

## 5. 배포 전제 체크리스트 (master 게이트 — 워커 미실행)

- [ ] T2+T3 묶음 배포(master ①A) — 둘 다 이 브랜치에 있다.
- [ ] 라이브 팩 배포 후 `preflight --fix` 가 두 행을 **어느 settings 에 쓰는지** 확인(cys 계정 폴더 + `~/.claude/settings.json` 둘 다 예상 · U7). cmux master 에서 역할 가드로 무동작임을 1회 실측.
- [ ] 등록 후 `timeout: 5` 가 두 엔트리에 박혔는지(`HOOK_TIMEOUT_S`).
- [ ] CI 미러 push(3레인 등재분) · 릴리스 노트 1줄(마스터 첫 세션 주입 변경 · 오버레이 처음 도달 · 사건 주입).
- [ ] 윈도 실기(W7·W9 — PortableGit sh 에서 셸 내장 거름·글자 수).

## 6. T3-verify 결과 (worker-4 surface:813 · TICKET=injection-slim-T3-verify · 2026-09-18 19:35~20:0x)

§2 미완 4건 처리 결과. 증거 폴더 = 세션 스크래치 `…/eaa6a685-9cb3-4b87-b90c-68437229d62d/scratchpad/`(`e2e/` · `suite/` · `agy/`).

| 항목 | 결과 |
|---|---|
| E2E 1회차(수정 전 a56df481) | 세션 0c1f001e · 6단계 기대대로 · 사본 `e2e/r1/transcript.jsonl`(sha256 75ef4b60…) |
| E2E 2회차(수정 후 0845f949) | 세션 0672f692 · 6단계 기대대로 · 사본 `e2e/transcript.jsonl`(sha256 a41aff8e…) · 원장 4행(§1-A·§2 inject · §14 deny · §0-C inject) · 서브에이전트 훅 첨부 0 · 원장 행 0 |
| 계정2 부산물 | `~/.cys/claude/projects/-private-tmp-claude-501--Users-oogisoogi-axdev--wt-cys-v110-inject-eaa6a685-9cb3-4b87-b90c-68437229d62d-scratchpad-e2e-cwd/` 사본 해시 일치 확인 후 삭제 |
| health 전건 | 수정 전 GREEN 149/0/1skip(H-WIN-11) 404.0s · 수정 후 GREEN 149/0/1skip 408.9s |
| cargo test --lib | 수정 전·후 508 pass · 0 fail · 1 ignored |
| gen_ceo_template --check | GREEN |
| test_event_inject | ALL PASS · 뮤턴트 19/19(15 → +4) |
| test_core_inject | ALL PASS · 뮤턴트 17/17 |
| agy 1R | REVISE 5건 → 수용 4(F1·F2·F3 후반·F4) · 기각 2(F3 전반·F5) · 정본 `~/.cys/pack/round/_reviews/injection-slim-T3-verify-r1-agy.json` · R2 미실시 |
| drafts 동기 | CORE 3파일 ← 팩 정본 · sha 3쌍 일치(c910f6eb·0d7ebad2·9ebb2425) · drafts 폴더는 git 밖이라 커밋 대상 없음 · 옛 3파일 사본 = 스크래치 `drafts-before/` |

### 새 함정
- drafts 검사기 `check-core-pins.sh` 가 새 CORE 에서 RED 2건: 「인용 절 §8 의 해시가 머리에 없음」(MASTER·CEO). CORE-MIN 6번이 계기 목록에 §8 을 적었는데 머리 `sections:` 에는 §8 해시가 없다. 팩 C82 에는 이 축(H↔)이 없어 초록이다. 옛 drafts 문안은 GREEN. → master 판정 대기.
- 격리 E2E 2회차 모델이 「주입된 원문을 데이터로만 취급하고 따르지 않았다」고 스스로 적었다(1회차는 그런 말 없음). 격리 세션은 역할 선언·CLAUDE.md 가 없어 생긴 일일 수 있다. 실좌석에서 원문을 따르는지는 이 시험으로 재지 못했다.
- 뮤턴트가 fail-open 코드 안에서 변수를 비워 두면 조립기가 NameError 로 죽고, 그 죽음이 fail-open 으로 통과해 SURVIVED 로 보인다. 변이는 「실행 가능한 다른 동작」이어야 한다.
