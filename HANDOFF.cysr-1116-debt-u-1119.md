# HANDOFF — TICKET=cysr-1116-debt-u-1119 (role worker-1116debt-u · 가지 feat/1116-debt-u · 기준 dea2e1853)

브리프 = master/briefs/1116-full/debt-u.md(master#b005ef0a) + 추가 항목(master#df87f946 · rc2 CI 판독). push·태그·CI·발행 0.

## 커밋

| 커밋 | 갈래 | 내용 |
|---|---|---|
| 31e81924c | A · I2 | `scripts/gen_released_directive_hashes.py --extra-ref <커밋>`(반복) + 시험 6 + 레인 예행 UNREGISTERED_OK 사유 |
| 58673e9f8 | B · 게이트 | `docs/integ-1116/ci_pack_steps.py`(새) · gate-1116.sh 팩 손 목록 21 → ci-branch 팩 스텝 13개 본문 그대로 + CI 0회 22개 |
| 609c45ec0 | C · r34 | test_hook_r34 시한 행 = 구조 판정(느린 자식이 끝나기 전에 돌아왔나) + 벽시계 안전선 7.0s |
| d7c14f67f | D · 공개 후보 | `docs/integ-1116/pubcand.sh`(새) — H → C · 관문 1 · recheck 호출 · push 없음 |
| 484cc63ad | E · 범주 3 | codex 1R 범주 3 지적 13줄(주석·doc 주석·시험 describe 이름) |
| dd08b345a | 추가 ① | d1·name_guard 경쟁 승자 픽스처 — 리눅스 = 이름이 cysd 인 셸 스크립트(ubuntu-26.04 uutils) |
| 06e3990f6 | 추가 ③ 고침(master#1519072c) | windows-health: S2 바로 앞 미리 빌드 스텝(`cargo test --bin cysd --no-run` · S2 와 같은 env · 시한 12분) + 핀 시험 1 |

원작자 파일(데몬 handlers.rs·state.rs 등) 변경 = 0. 바뀐 운영 코드 줄 = 0(E 의 .rs·.ts·Cargo.toml·config.toml 은 주석만 · main.ts 는 함수 안 주석 3줄).

## A. I2 — 해시 생성기 `--extra-ref`

- 쓰임: 직전 판이 기계에 나갔는데 그 판 태그가 아직 없을 때(태그 전 통합 가지) `--extra-ref <그 판 커밋>` → Rust 표 + 팩 sha256 목록에 그 커밋의 CEO_TEMPLATE·MASTER_DIRECTIVE 바이트가 듦.
- 규칙: 못 찾는 ref · 그 커밋에 지침 없음 · 값 빠짐 · **모르는 인자** = exit 2 + 표 무변경(⚠전에는 모르는 인자를 무시하고 *생성*으로 갔다 — 오타가 표를 덮어쓸 수 있었음) · 태그 0개 거부 exit 3 그대로 · `--check` 도 같은 `--extra-ref` 를 받아야 같은 표(같은 바이트 태그가 생기면 extra-ref 없이도 표류 0 — 시험 `test_tag_on_same_bytes_absorbs_extra_ref`).
- 실측: 이 트리 `--check` = OK · `--check --extra-ref v1.1.14` = OK(이미 태그) · `--check --extra-ref 3a095c4ee`(1.1.15 후보) = 표류 rc 1(그 바이트가 표에 없음 = 1.1.15 를 건너뛰었으니 넣지 않는 것이 맞음 · 재생성 안 함).
- 시험 `scripts/tests/test_gen_released_hashes_extra_ref.py` 6/6 · 뮤턴트 5/5 붉음(extra 무시 4 FAIL · 못 찾는 ref 건너뜀 1 · 파일 없는 커밋 건너뜀 1 · 팩 목록에 안 넘김 2 · 모르는 인자 무시 1).
- 레인: 생성기를 부르는 워크플로가 없어(소비 = 로컬 게이트 gen-hashes 뿐) CI 등재 대신 `lane-parity-rehearsal.sh` UNREGISTERED_OK 사유 등재 · `--strict`·`--self-test` 통과.

## B. 로컬 게이트 = ci-branch 팩 단계

- `ci_pack_steps.py`: ci-branch.yml 의 run 본문(주석 아닌 줄)이 `cysjavis-pack/bin/` 또는 `scripts/ci/phoenix-host-gate.sh` 를 부르는 스텝을 골라 **본문 그대로** 셸 파일로 뽑는다(잡/스텝 env 만 머리 export · `bash --noprofile --norc -eo pipefail`).
  - 판정 불가 exit 3: 고른 스텝 0 · 4잡(macos-rust-pack·ubuntu-pack-suite·phoenix-host-gate·boot-health-full) 중 0인 잡 · `${{ }}` · `if:` · `working-directory:` · bash 아닌 shell · **덮개**(안 고른 스텝이 실재 팩 시험 이름을 부름 = 규칙 낡음).
  - 실측: 고른 스텝 13 · 부르는 팩 시험 184(이름 토큰 + `test_phoenix_*.py` 글롭 + run_bootstrap_health.py 가 부르는 것) = 팩 시험 207 − 어디에도 없는 23 · 11-19 차집합 표와 **집합 정확히 같음**(빠짐 0 · 더함 0) · 옛 손 목록 19개 전부 포함.
  - `--self-test` 양성 1 · 음성 5.
- gate-1116.sh: `pack-*` 손 목록 → `ci_step` 13개 · 옛 `health` 단계 → CI boot-health 스텝 결과 JSON 재판독(같은 러너 · 두 번 안 돎) · CI 0회 22개 = `unreg-*` · CI 본문이 cwd 에 남기는 health-full.json 은 결과 폴더로 옮김 · 그 밖 작업트리 변화는 WARN 1줄.
- 무등재 23개 처분(격리 env 실측 · 이 맥):

| 처분 | 시험 | 근거 |
|---|---|---|
| 게이트 unreg-* 로 돎(20) | cli_probe · completion_guard_notice · contracts_ct · dept_creds_seed · dept_list_unregistered · dept_ticket_deficit_zero · dept_ticket_request · distill_fx · hud_bridge_master_idle · memory_desc_drift · mission_boot_command_filter · mission_harness_filter · orchestra_ticket_snapshot · orchestra_todo_path · org_audit · pack_syntax_warnings · preflight_nlm_pin · seat_revival · vibecheck · viberoute | CI 루프와 같은 격리(빈 HOME · CYS_PACK_DIR 임시)로 rc 0 |
| 게이트 unreg-* 로 돎 · env 필요(2) | preflight_phase1_checks(26) · verify_gate(9) | JAVIS_ROOT·CYS_PROBE_RUNS 없으면 시험 스스로 REFUSE rc 2(설계) · 주면 rc 0 → 게이트가 임시값을 준다 |
| 조건부(1) | agora_known_authentic | 제작 맥 전용(게시 zip 폴더 CYS_AGORA_ZIP_DIR · 없으면 FAIL 이 설계) → 그 env 가 있을 때만 돎 |

- ⚠차이(정직): 파이썬 = 이 맥 /usr/bin/python3 3.9(CI = 3.12) · 우분투 잡 본문도 이 맥에서 돈다(리눅스 아님 — 추가 ① 이 그 사각의 실례).

## C. test_hook_r34 시한 행

- 원인 실측: 런처 시한은 벽시계가 아니라 `sleep` 명목 합(1/100초 회계 · role-bootstrap.sh 343·262) → 맥은 외부 sleep ~14회 생성 비용이 붙어 시한 1s → 경과 2.38~3.12s · 부하(load 21~) 아래 4.12·4.20·5.17s. 11-19 레인 로그: RCF-3 3.12 · RCF-4a 3.07 · NZ-3 3.10 · DL-1b 3.11 붉음(문턱 3.0). 우분투 CI 는 1.03s(rc2 로그).
- 고침: 가짜 cys 의 slow 갈래가 끝나면 표지 → 시한 행 5개 주 판정 = `not slow_done`(런처가 돌아온 순간 자식이 아직 안 끝남 = 기다리지 않았음 · 부하 무관) · 자식 4→10s · 벽시계 상한 3.0→7.0s(시한 값이 몇 배 커진 회귀용 안전선 · 부하 최대 실측 5.17 위) · 하한 0.9s 그대로.
- 전후: 옛 판 3회 = 붉음 2회(RCF-3 3.08 · DL-1/WIN-2 4.20/4.21) · 새 판 3회 초록(2.45~2.96s · done=False) · 1차 수정(8s/5.0)은 load 21 에서 RCF-4a 5.17 붉음 1회 → 구조 판정으로 바꾼 까닭.
- 뮤턴트(런처): 맥 갈래 시한 ×10 = 5 FAIL(done=True · 10.4~10.8s) · ×6 = 5 FAIL · 윈 갈래 ×10 = WIN-2 FAIL(done=True) + WIN-0 핀.

## D. 공개 후보 도구 `docs/integ-1116/pubcand.sh`

- 사용: `PUB_EXCLUDE=<목록> PUB_MSG=<메시지> [PUB_BASE=origin/main] [PUB_REF=refs/heads/cand/1116-rc] bash docs/integ-1116/pubcand.sh <H>` → 끝 줄 `PUBCAND H= B= C= ref= gate1= recheck_rc= rc=`.
- 막는 것(rc 2): 목록 줄이 H 트리에 없음(낡은 목록) · **지킴 폴더 docs/integ-1116 의 H 파일이 목록에 없음**(내부 게이트 도구가 공개 트리에 실림) · 못 찾는 H/B · 있는 ref(PUB_FORCE=1 없이) · 관문 1 불일치 · C 부모 ≠ B. recheck rc 0/1/3 그대로 전달.
- `--self-test`: 임시 저장소 + 가짜 recheck · 양성 4 · 음성 5 · 집행 본문 push·tag·gh 명령 0 자기 검사(음성 대조 = 본문 끝에 push 한 줄 → BAD).
- 실데이터 재현: H=c75e0714a · B=270e3e21e · 11-19 목록 171 → C 트리 `27045f27…` = 11-19 후보 aebca3d9 트리와 같음(재현 ref 만들고 지움 · recheck 는 PUB_NO_RECHECK=1 로 건너뜀 — 민감 폴더·보고 파일에 쓰므로).
- 지금 머리로 돌리면: `docs/integ-1116/ci_pack_steps.py`(+ pubcand.sh) 가 목록에 없다고 rc 2 — **다음 공개 후보 때 목록에 docs/integ-1116 새 파일 2개를 더해야 한다**(도구가 정확히 그것을 잡는 것을 실측).

## E. codex 1R 범주 3 청소

- 고친 줄(처분표 BLOCK/SHOULD-FIX 중 주석·시험 머리): seatkeep main.rs:1-4 · Cargo.toml:26·139 · seat_proc.rs:1 · seatkeep-knob-on-tests.sh:5 · pillar_gate.py:2·5 · confirms.ts:115·277 · main.ts:9326-9327 · restartconfirm.test.ts:1-2 · .cargo/config.toml:13-14 · confirm.test.ts:407 · slice3fix.test.ts:400·455.
- 공개 문서 링크로 바꿀 대상이 공개 트리에 없어(설계·탐침 보고·HANDOFF 전부 제외 목록) **공개 파일·공개 시험 이름을 가리키거나 내용을 그 자리에 적는** 꼴로 바꿨다.
- 시험: bun 5파일 142/0 · secret-scan staged clean · 소스 핀 대조(include_str seat_proc.rs·Cargo.toml = 코드 본문만 읽음 · 영향 0).

## 추가 ① — rc2 ubuntu-pack-suite `test_d1_dept_ready_probe` 2건

- 대조군: 실패 런 2개(aebca 11-19 20:38 · rc2 22:42) 러너 이미지 = **ubuntu-26.04**(20261103.629 · 20261111.635) · 마지막 통과 런(11-09 · 247d571cc) = **ubuntu-24.04**(20261028.624). aebca 런은 r32 에서 먼저 멈춰 d1 까지 안 갔다.
- 구조 증거: 15개 중 붉은 2개(lost_win · lost_never) = 정확히 `sleep` 을 `cysd` 이름 심링크로 부르는 갈래. 심링크 없이 sleep 을 쓰는 lost_reused · lost_dead 는 초록.
- 바깥 근거: Ubuntu 26.04 기본 coreutils = uutils 다중 호출 실행 파일(유틸리티 = 하드 링크) · `sleep` 을 다른 argv0 로 부르면 「Security violation」 거부(Launchpad bug 2126689 · uutils/coreutils #10135).
- 판정: 산 승자가 즉사 → `boot_lock_winner` 가 산 cysd 를 못 봄 → 「기동 중 종료」. **픽스처의 러너 의존 · 제품(cys-dept·실 cysd) 결함 아님**(실 cysd 는 제 이름의 실행 파일). vendor F1 계열 아님. 러너에서 직접 재현은 못 함(이 맥 tart = macOS 이미지뿐) → 확신도 중상 · 확정은 다음 CI 우분투.
- 고침: 리눅스 = `#!/bin/sh` while-sleep 스크립트(리눅스 comm = 스크립트 이름) · 맥 = 종전 심링크(맥 실측: 스크립트 comm = `/bin/sh` 라 안 됨 · 심링크 comm = 경로). 같은 꼴 test_dept_name_guard.py:1576(맥 레인 전용 · 지금은 안 붉음)도 같이.
- 시험(맥): d1 15/15(128s) · name_guard 75/75(247s) · ⚠리눅스 갈래는 이 맥에서 실행 검증 불가(가짜 uname 음성 대조는 시험이 PATH 를 고정해 불성립).

## 추가 ② ③ — 판독만(고침 없음)

- ② macos-rust-pack·phoenix-host-gate·ui-check = runner not acquired(master 판독 그대로 · 판정 제외).
- ③ windows-health A-ID S2(시한 6분): aebca 런 S2 내부 = 21:28:22 시작 → 21:32:42 컴파일 끝(**260초 = cysd 시험 바이너리 컴파일** · 출력이 파일로 받아져 그동안 0줄) → 시험 13개 1초. rc2 런은 모든 스텝이 1.3~1.5배 느림(factory_reset 374→519 · U5 214→283 · D5 71→93 · win_std 92→125 · F10 77→100 · help 157→229) → 260×1.4 ≈ 365 > 360 = **시한 근접(걸림 아님)**. S2 추이 137(11-09) → 261 → 367초.
- 「cargo test --bin cysd 감독자 축」 = 세 런 모두 1807~1808초(continue-on-error · 시한 30분 · 통과 런 포함) = 이번에 생긴 일 아님 · 늘 시한에서 잘리는 비차단 스텝.

## 추가 ③ 고침 — S2 미리 빌드(master#1519072c · 워크플로 수정 허용)

- 놓은 곳 = S5 와 S2 **사이**(바로 앞). 까닭: aebca 런에서 바로 앞 S5 의 같은 `--bin cysd` 는 캐시 0.26초였는데 S2 첫 호출이 재컴파일 260초 · S2 둘째 호출 0.31초 → 오염은 S5 끝 ~ S2 시작 사이에 생긴다. 더 앞(예: 감독자 축 뒤)에 두면 그 사이 스텝이 다시 오염시킬 수 있다.
- env = S2 와 같은 `CYS_PACK_DIR`·`CYS_STATE_DIR`(env 가 원인인 경우까지 덮음). 원인 후보(build.rs `rerun-if-changed=cysjavis-pack`)는 이 맥에서 재현 못 함(로컬 팩 폴더에 `__pycache__` 없음) → 이름 안 붙임.
- 시한: 미리 빌드 12분(느린 러너 실측 367초 × 약 2) · S2 6분 그대로(시험 실행 ≈1초 + 목록). 시한 상향은 안 함.
- 대조 도구: C8 재고 `selects_cysd` 가 `--no-run` 을 실행으로 안 셈 · 레인 게이트 `FILTER_RUN_RE` 는 필터 뒤 `-- ` 가 있는 줄만 → 가드 불요. 「판정 결박 스텝 뒤 차단 스텝 금지」 시험 = S2 앞이라 통과.
- 시험: test_ci_branch_cysd_step 39/39(새 핀 `test_prebuild_step_immediately_precedes_s2_with_the_same_env` · 뮤턴트 3/3 붉음 = 순서 · env 하나 뺌 · `--bin cys`) · test_c8_ci_consumer 19/19 · test_release_windows_help_gate 11/11 · test_release_trigger_split 17/17(게이트 venv) · test_phoenix_host_gate_lane 8/8 · lane-parity-rehearsal --strict rc 0 · 팩 시험 test_win_dept_spawn·test_hook_launcher_split·test_pyseal_census·test_runtime_manifest_parity 초록.
- ⚠윈도 실측 없음 — 실제로 S2 안 컴파일 0 인지는 다음 windows-health 런의 S2 로그 「Finished … in 0.xs」 로 판정(해소 판정: S2 스텝 안 `Compiling cys-terminal` 0줄).

## 시험 숫자(전후)

- 기준선(dea2e1853 계열): 11-19 cifix 증거 레인 = mac 팩 스텝 rc 0(1452s) · ubuntu 팩 스텝 rc 0(1432s) · 그 전 판에서 r34 시한 행 간헐 붉음(위 C).
- 이 가지: 로컬 게이트(`GATE_ONLY='^(gen-|build$|ci-|unreg-|pubcand-|script-|ui-test$)'`) 결과 = 아래 「게이트 결과」 칸(완주 뒤 채움).

## 📌 덧붙임(실행 안 함 · 판단 = master)

1. (처리됨 06e3990f6 · master#1519072c) 윈 S2 미리 빌드 — 위 「추가 ③ 고침」.
2. 우분투 CI 이미지가 26.04 로 바뀐 것 자체 — 다른 시험·스크립트에 GNU coreutils 가정(argv0·옵션)이 더 있는지 훑기(이번엔 sleep 심링크 2곳만 찾음 · `exec -a` 는 src/agy_door.rs 견본 문자열뿐).
3. 범주 3 에서 안 고친 것(기능 줄·팩 지침): cysjavis-pack/agents.json:3·8 · MASTER_DIRECTIVE.md:462 · WORKER_DIRECTIVE.md:258 · skills/appbuild-plan-debate·computer-control SKILL.md — 팩 지침은 별도 커밋 + 합성기 + doc-contract 규약 · 내용 공개 여부는 제품 판단.
4. 같은 꼴 남은 자리(주석·문자열 · 처분표 밖이라 안 고침): src/bin/cys.rs:31486(주석)·31564(assert 문구) 의 docs/1115/CLI-STACK-PROBE 경로 · ui/src/drainverify.test.ts:156·192 의 운영자 서사 · ui/src/grouptabs.ts·grouptabs.test.ts 의 pillar-width-rule 지시서 이름 · windows-health.yml 의 rqfix_f10 · seatkeep-knob-on-tests.sh:2 의 master# 표식.
5. 다음 공개 후보 목록에 docs/integ-1116/ci_pack_steps.py · pubcand.sh 추가(pubcand.sh 가 rc 2 로 요구함).
6. gate-1116.sh 의 ci_step WARN 은 게이트 시작 전부터 있던 미추적 파일도 「변화」로 센다(이번엔 WORKER_TODO 1개) — 시작 시 상태와 비교하도록 다듬을 여지.

## 함정·재현

- 게이트는 실행 중 셸 스크립트를 읽어 가며 돈다 → 돌고 있는 동안 gate-1116.sh 를 고치지 말 것.
- r34 시한 측정은 부하에 민감 — 부하 낮을 때(uptime 1분 < 15) 단독 재실행으로 대조(11-20 운영 공지 ②).
- 새 작업트리는 형제 target 을 `cp -c -R` 로 복제(101G · 92초).
