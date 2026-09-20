# HANDOFF — cysr 1.1 통합 브랜치 rebase/v1.1 (TICKET=v110-integ · 2026-09-20)

워크트리 `~/axdev/.wt/cys-v110-integ` · 브랜치 `rebase/v1.1` ← `rebase/v1.0.2`(54c148cc) · 워커 surface:870.
이 티켓은 **통합 창구**다 — 다른 워커 브랜치(fix/v110-mac-x64 · fix/v110-darwin-update · fix/v110-panetitle ·
fix/v110-sidebar)가 【단계완료】되면 master 가 순서대로 넘기고, 그때마다 병합·게이트를 재실행한다.

비가역은 이 티켓에 없다: 태그·릴리스·main 병합·앱 교체 = master 게이트. 이 티켓은 `git push origin rebase/v1.1` 까지.

---

## 1. 병합 표 (브리프 순서 그대로 · 전부 --no-ff)

| 순서 | 브랜치 | 넘겨받은 HEAD | 병합 커밋 | 충돌 | 해소 근거 1줄 |
|---|---|---|---|---|---|
| M1 | fix/v110-restore | 76d4ccf3 | 3b427e40 | 0 | 기준 54c148cc 의 직계라 그대로 얹혔다 |
| M2 | fix/v110-app | d22f7f6a | 58606497 | 0 | restore 를 이미 품은 브랜치 — 델타(ui/index.html·wsbar 등)만 들어왔다 |
| M3 | fix/v110-dept | 079abc88 | 99a3b26b | 0 | 겹치는 파일이 워크플로 3개뿐이고 서로 다른 행이라 자동 병합됐다 |
| M4 | fix/v110-inject | fdeda06c | 8e4ef435 | **1** | 아래 §2-① |
| M5 | fix/v110-misc | 9303316f | a0f59b57 | 0 | `src/bin/cys.rs` 는 서로 다른 구역(자동 병합) |
| M6 | fix/v110-usage-noagy | f14261b4 | 2124c2eb | **1**(3헌크) | 아래 §2-② |
| V | (판번) | — | d7f05490 | — | §3 |
| M7 | fix/v110-sidebar (인계 1) | 37ea055f | fca737dc | 0 | `ui/` 만 건드리는 브랜치 · 이미 병합한 d22f7f6a 위 2커밋 |
| M8 | fix/v110-darwin-update (인계 2·3) | c7b96f12 | 9111cfec | 0 | panetitle 516d39d8 을 **흡수한** 브랜치(조상 실측 확인) — master 지시대로 panetitle 단독 병합은 건너뜀. 팩 파일은 restore 계보분이라 델타 0 |
| M9 | fix/v110-mac-x64 (인계 4) | 14964bf2 | 1cf61c70 | 0 | `release.yml` 이 dept 변경분과 다른 행이라 자동 병합 |

---

## 2. 충돌 해소 2건 — 무엇이 부딪혔고 왜 이렇게 풀었나

### ① `cysjavis-pack/hooks/session-start.sh` (M4 · restore × inject)

두 브랜치가 **같은 자리를 각자 재구조화**했다. 텍스트 충돌이 아니라 계약 충돌이다.

- restore **T6 I-5**: 각성 출력을 `_ss_rules()`(첫 턴 규율 + 부트 브리지) / `_ss_bulk()`(로컬 오버레이 ·
  soul · 메모리 색인)로 갈라, `source=resume` 일 때만 합계가 9,000자 미만이어야 원문을 싣는다.
- inject **T2/T2a**: master·CEO 좌석을 조립기 `hooks/core_inject.py` 로 빼서 **source 무관** ≤9,000자를
  보장하고(soul·색인은 배경층 훅 `inject-background.sh` 몫), 첫 턴 규율 블록을 워커 출력 **맨 앞**으로 옮겼다.

**해소(3줄 · 같은 내용을 파일 안 주석에도 박았다)**

1. master·CEO 좌석은 T2 조립기가 **같은 10,000자 절단을 source 무관으로 이미 막는다** → 그 좌석에 T6
   상한을 중복 적용하지 않는다(상위 기제가 하위 기제를 흡수). T2 분기가 T6 디스패처보다 앞에 온다.
2. master 를 제외한 좌석(worker·cso)은 여전히 디렉티브 전문을 싣는다 → **그 좌석에 한해** T6 경로를 유지.
3. 첫 턴 규율은 resume·비resume **양 경로에서 가장 먼저** 낸다(T2a 계약. T6 초판은 resume 머리에서 목차
   뒤였다 — 순서만 T2a 쪽으로 맞췄고 두 브랜치의 **문안은 어느 쪽도 바꾸지 않았다**).

부기 — **유실 1건을 되살렸다**: theirs(inject) 채택 구간에 restore 의 G축(기계 문구
`Continue from where you left off.` 를 사람 입력 계수에서 제외) 1줄이 없었다. 되살려 넣고, ours/theirs 고유줄을
전수 대조해 **잔여 유실 0**을 확인했다(의도한 순서 변경 1줄만 차이).

**시험 재조준 1건**: `cysjavis-pack/bin/tests/test_t6_injection_policy.py` F계열의 master 행 5건은 T2 로
도달 불가가 됐다. 축(출력<10,000 · 보여야 하는 규범이 절단 표지보다 앞 · 원문은 경로 안내)은 그대로 두고
**재는 표지만 좌석별로 갈랐다** — master = 「■ 자기 절단」·부트 브리지 / worker = 「복원(resume) 목차」·「원문 생략」.
옛 계약과 무엇이 그것을 갈아치웠는지를 그 파일 주석에 남겼다(되돌림 감시용 — master 에 옛 표지를 다시
요구하는 수정이 들어오면 T2 가 되돌려진 것이다).

### ② `src/bin/cysd/accounts.rs` (M6 · misc × usage-noagy · 3헌크)

misc **B4** 와 usage **two-accounts** 가 **같은 결함**(OAuth 프로브가 기본 프로필 `~/.claude` 하나만 봐서
계정2가 통째로 빠짐)을 각자 고쳤다. 겹치는 것은 기능이 아니라 사본이라 한쪽을 골라야 했다.

| 축 | misc 판 | usage 판 |
|---|---|---|
| 서비스명 판정 | `keychain_service_for(dir, home)` | `keychain_service_for(home, dir)` (인자 순서 반대) |
| 대상 계획 | `plan_oauth_probe_targets` — 계정당 dir **하나로 축약**(나머지 버림) | `probe_targets` — 계정당 후보 dir 을 `candidates` 로 **쌓아 둠**(앞 후보 401 이면 다음 후보로) |
| 실행 | `oauth_probe_once` 안에서 순회 · 전부 실패 시에만 Err | `probe_account`/`probe_round`/`current_targets`/`live_fetch` — 계정별 백오프·실패 격리·실패 시 값 유지 |

**해소**: usage 판이 misc 판의 **초집합**이므로 usage 전문을 채택했다(`git checkout --theirs`). misc 고유 심볼
2개(`plan_oauth_probe_targets`·`keychain_service_for(dir,home)`)는 `accounts.rs` 밖에서 참조 0건이라 호출처
수리가 필요 없었고, misc 의 남은 변경분(`cys.rs` B2 pack-merge 거부 원장 · `permtoast.test.ts` B3 회귀핀)은 무접촉이다.

**사라진 misc 시험 2건의 축이 usage 그물에 남아 있다 — 단정하지 않고 뮤테이션으로 증명했다**

| 뮤턴트 | 내용 | 결과 |
|---|---|---|
| M-A | `keychain_service_for` 를 접미 없는 이름 하드코딩으로 되돌림(= misc B4 뮤턴트 동형) | KILLED · 적색 3 (`keychain_service_names_match_measured_formula` · `probe_round_fills_both_accounts` · `probe_round_isolates_account_failure`) |
| M-B | 프로브 대상을 기본 dir 하나로 좁힘(= misc `plan_` 뮤턴트 동형 · 종전 결함 재현) | KILLED · 적색 3 (`probe_targets_one_per_account_default_first` · `probe_round_isolates_account_failure` · `probe_round_fills_both_accounts`) |

`ui/src/main.ts` 는 두 브랜치가 동시에 고쳤으나 자동 병합됐다(bun 전건으로 확인 — §4).

---

## 3. 판번 1.0.2 → 1.1.0 (커밋 d7f05490)

브리프의 「tauri.conf.json = 0.14.37」 서술은 **공유 트리 HEAD(fix/usage-stale-rate-v0.14.37)를 읽은 오류**다
(master [master#2e798fbb] 로 폐기 확인). 이 포크는 벤더 판번과 제품 판번이 갈려 있지 않고 **단일 버전선**이다.

강제 게이트 `scripts/version-check.sh:41-64` 가 다음 8곳의 `sort -u` 동일성을 요구한다(하나만 빠져도 rc 1).
⚠[master#2e798fbb] 보충은 「두 파일 + latest.json 생성기 입력」이라 적었지만, **2곳만 고치면 게이트가 죽는다** —
실측 게이트 쪽으로 8곳 전부 올렸다.

| # | 자리 | 값 |
|---|---|---|
| 1 | `Cargo.toml:8` | `version = "1.1.0"` — 데몬·CLI `env!("CARGO_PKG_VERSION")` 의 원천 |
| 2 | `src-tauri/Cargo.toml:3` | `version = "1.1.0"` — 앱 · `build.rs:271` Windows PE VERSIONINFO |
| 3 | `src-tauri/tauri.conf.json:4` | `"version": "1.1.0"` — 자산 이름·latest.json·VERSIONINFO 게이트의 원천 |
| 4 | `ui/package.json:4` | `"version": "1.1.0"` |
| 5 | `dist-win/cys.wxs:3` | `Version="1.1.0"` — legacy MSI(문서상 폐기지만 게이트가 여전히 강제) |
| 6 | `dist-win/cys-x64.wxs:3` | `Version="1.1.0"` |
| 7 | `Cargo.lock [cys-terminal]` | `1.1.0` ← `cargo update -w -p cys-terminal -p cys-app` (손편집 0) |
| 8 | `Cargo.lock [cys-app]` | `1.1.0` ← 같은 명령 |

**파생이라 안 고친 곳**(고치면 오히려 이원화): 릴리스 이름 `cysr vX.Y.Z`(release.yml:944 · 태그 파생 —
리터럴 `cysr_1.0.2` 는 코드에 0건) · 자산 이름 `cysr_X.Y.Z_*`(release.yml:639 · `scripts/build-macos-signed.sh:21`
이 tauri.conf.json 의 version 을 grep) · `latest.json` version(release.yml:928 tauri-action 이 같은 값) ·
데몬·앱 `identify` version · `.pack-version` · pack-manifest `pack_version`.

**master 결정 대기 1건** — 팩 `min_binary_version`(`release.yml:1014` `PACK_MIN_BINARY` ·
`pack-release.yml:61` `PACK_MIN_BINARY_OVERRIDE` · 둘 다 `'1.0.0'` · **동시 상향 계약**)은 릴리스마다
올리는 값이 **아니다**(정책 = 팩이 의존하는 가장 새로운 바이너리 표면이 생긴 판. 0.14.3~0.14.17 열다섯
릴리스가 0.14.2 를 유지한 선례). 1.1 팩 신규물(`core_inject.py`·`directive-event-inject.sh`·
`inject-background.sh`)이 1.1.0 에서 처음 생기는 바이너리 표면에 의존하는지는 이 티켓에서 판정하지 않았다.

**미작성(권고 · 범위 밖)**: `docs/RELEASE_NOTES_1.1.0.md` — 1.0.0/1.0.1/1.0.2 는 전부 존재한다.

---

## 4. 게이트 실측 (전부 **9병합 완료 + 판번 1.1.0** 트리에서 · 도구 출력)

| 게이트 | 값 | 기준 대비 |
|---|---|---|
| `cargo test --lib` | 508 passed / 0 failed / 1 ignored | 기준 508 — 무변 |
| `cargo test --bin cys` | 249 passed / 0 failed | misc 248 + restore 1 |
| `cargo test --bin cysd` | **983 passed / 0 failed / 1 ignored** | misc 962 · usage 970 → 6병합 971 → panetitle `panetitle.rs`+`handlers.rs` 로 983 |
| `cargo test --bin cysd accounts::` | 20 passed / 0 failed | usage 20 — 무변 |
| `cd ui && bun test` | **1019 passed / 0 failed** (36파일) | app 969 → sidebar·darwin-update 신규 포함 |
| `ui` typecheck | head 4건 = 기준선 4건 · 줄번호 정규화 diff **IDENTICAL** | **신규 0** (기준선 = `rebase/v1.0.2` git archive 사본에서 같은 방식) |
| `sh scripts/version-check.sh` | ✅ 8곳 일치 1.1.0 | 9병합 뒤에도 무변 |
| `sh scripts/version-check.sh v1.1.0` | ✅ 기대 일치 + ✅ 벤더 태그 `v1.1.0` 동명 충돌 없음 | — |
| `scripts/tests/test_version_sot_mutation.py` | 양성 1 + 음성 8 + 벤더 5 = 14건 전건 기대대로 | — |
| `bash scripts/release-lane-check.sh` | rc 0 · 본체(BINARY) 레인 · 버전 충돌 가드 충족(1.1.0 > pack-v0.12.92) | — |
| 팩 `test_session_start_hook` | ALL PASS | — |
| 팩 `test_t6_injection_policy` | `T6-INJECTION-POLICY-OK` | 재조준 반영본 |
| 팩 `test_core_inject` / `test_event_inject` | ALL PASS / ALL PASS | — |
| 팩 `test_phoenix_r4_restore` / `test_phoenix_e2_schedule` | `PHOENIX-R4-RESTORE-OK` / 10/10 PASS | — |
| 팩 `test_pyseal_census` | `PYSEAL-CENSUS-OK` | — |
| 팩 `test_preflight_phase1_checks` | OK (격리 env 필요 — `JAVIS_ROOT`·`CYS_PROBE_RUNS`) | — |
| 팩 `test_verify_gate` | rc 1 · `test_04_brief_paths` 1건 FAIL | ⚠**선재 결함** — `rebase/v1.0.2` 사본에서 **같은 시험·같은 단언·같은 메시지**로 실패(`'additionalContext' not found in ''`). 신규 적색 0 |
| 팩 `test_dept_request` (unittest) | Ran 59 tests · OK | dept 59 — 무변 |
| `javis_dept_request.py self-test` | `SELF-TEST PASS (0 fail)` | — |
| `javis_preflight.core_injection_problems('cysjavis-pack')` | 문제 0 | — |
| `scripts/tests/test_darwin_update_row.py` | rc 0 | darwin-update 자체 |
| `scripts/tests/test_darwin_updater_tarball.py` | rc 0 | darwin-update 자체 |
| `scripts/tests/test_release_postprocess_gate.py` | rc 0 | mac-x64 가 행 추가 |

### 4-A. 브랜치별 대표 뮤턴트 재실행 (병합 뒤에도 그물이 산다 · 변이 적용·원복 실측 · 전부 KILLED)

| 브랜치 | 뮤턴트 | 기대 적색 지점 | 결과 |
|---|---|---|---|
| restore | UM12 묘비 미상(`deptTombs === null`) 재기동 보류 게이트 무력화 | 복원 배선 P1-A 순서 핀 | KILLED · 적색 1 |
| restore | UM13 `ghostSids` → 빈 목록 | `ghostSids` 2 + `advanceGhostStrikes` 1 | KILLED · 적색 3 |
| app | AM-r2 묘비 in-flight 가드를 `rpcT` 래핑에 걸기 | 「생 invoke promise 에 걸린다」 계약 | KILLED · 적색 1 |
| inject | MX1 규율을 디렉티브 뒤로 / MX2 resume 머리 규율 제거 / MX3 T6 상한 무력화 / MX4 기계문구 제외 제거 / MX5 master 조립기 분기 제거 | 7b / F4·G2 / F1~F4 / G1·G2 / F2·F3·F6·F7b·2x1 | 5/5 KILLED |
| misc·usage | M-A 서비스명 하드코딩 되돌림 / M-B 대상을 기본 dir 로 좁힘 | §2-② 표 | 2/2 KILLED · 각 적색 3 |
| (통합 자체) | 내 HANDOFF §8 의 `ln -sfn` 레시피 | `clipath.test.ts` MINOR-5 배포문서 파괴명령 핀 | **적색 → 문서를 비파괴 형태로 고쳐 초록**(핀을 끄지 않았다) |

미실행 1건: `cysjavis-pack/bin/tests/mut_dept_request.py`(47종) — §9 함정의 덮어쓰기 사고 구간에 걸쳐 돌아
결과를 폐기했고, 그 뒤 **push 를 위해 트리를 깨끗하게 유지**해야 해서 push 뒤로 미뤘다. dept 브랜치 자체
라운드에서 45 KILLED + M7a·M30 층 방어 생존으로 확인된 하네스이고, 이 통합에서 `javis_dept_request.py` 는
**한 줄도 바뀌지 않았다**(`git diff rebase/v1.0.2..HEAD -- cysjavis-pack/bin/javis_dept_request.py` 가
dept 브랜치의 추가분과 동일) — 그래도 「안 쟀다」는 「초록」이 아니므로 미실행으로 적는다.

## 5. 이월 ISSUES B9·B10·B11 — dept 079abc88 반영 여부 (구현 금지 · 표기만)

| # | 항목 | 반영 | 근거(파일:라인) |
|---|---|---|---|
| B9 | A1-2e 좌석 컨텍스트 정지선(부서 1개 = 좌석 +3 · 워커 CTX 60% 정지·자동 매듭) | **미반영 · 1.1 위험** | `docs/HANDOFF-A1-2.md:82` 「A1-2e(좌석 컨텍스트 정지선) 선결 전 배포 금지 — 이 티켓으로 안 닫힌다」 · `docs/DESIGN-dept-by-conversation.md:174` 동문 · dept diff 13파일에 CTX 축 변경 0 · 시험 이름에 그 축 0건 |
| B10 | 헌법 문서 3곳 「재개」 → 「상태만 복원·대기」 통일(티켓 A2-3) | **미반영 · 1.1 위험** | 통합 트리 실측 잔존 3/3 — `cysjavis-pack/directives/MASTER_DIRECTIVE.md:538` · `cysjavis-pack/directives/CEO_TEMPLATE.md:619` · `cysjavis-pack/round/RECOVERY.md:14` (해소 판정 「3곳 grep 「재개」 0」 미충족) · dept diff 에 directives·RECOVERY 무접촉 |
| B11 | 부서 레지스트리·편성 원장 쓰기 측 공통 잠금(세대 검증) | **미반영(의도적 이관) · 1.1 위험** | `docs/HANDOFF-A1-2b.md:30` 「범위 밖 → ISSUES B11」 + 이관 5건(1R F13 · 2R F6·F7·F10·F14) · `docs/HANDOFF-A1-2c.md:66` 「이번 라운드 무접촉」 · 부분 완화만 = `docs/HANDOFF-A1-2.md:83` 「이동 직전 레지스트리 재독으로 창을 좁힘 · **닫지는 못함**」 |

부기 — `~/axdev/master/reports/cysr-110/ISSUES.md` 는 09-18 22:50 시점 그대로다(dept A1-2c 수정 5건 이후
진척이 원장에 미기재). ISSUES **B2 행도 낡았다**: misc 커밋 9303316f 본문이 「근본원인은 `.promote.lock` 이
**아니었다**」고 적어 ISSUES:13 의 promote.lock 가설을 뒤집는다.

---

## 6. 브리프 전제 정정 3건(작업은 실측 쪽으로 진행)

1. 판번 — §3 (master 폐기 확인 완료).
2. HANDOFF 경로 — restore 의 `reports/cysr-110/HANDOFF-restore-impl-A2-2.md` 와 app 의
   `reports/jarvis-dept-redesign-2026-09-17/HANDOFF-A1-3.md` 는 **브랜치에 없고** master 보고서 트리(git 밖)에 있다.
   inject 는 `docs/HANDOFF-T3.md` 가 아니라 **저장소 루트** `HANDOFF-T3.md` 다.
3. usage-noagy HANDOFF 는 커밋 f14261b4 메시지 **본문에 없다**(제목 한 줄뿐). 실물 =
   `docs/HANDOFF-usage-noagy.md` + `docs/HANDOFF-usage-two-accounts.md` 두 파일(후자가 최신).

---

## 7. 4군 점검 칸 (cys 개발자 ANCHOR · 내 변경이 각 군에 닿는가)

「내 변경」 = 병합 해소 2건 + 판번 8곳 + 내 문서 1개다(기능 코드는 브랜치들이 썼다). 두 층으로 적는다.

- **① 폭주 큐** — **내 해소가 닿는다(줄이는 쪽)**. `accounts.rs` 를 usage 판으로 채택한 것이 OAuth 프로브
  호출량을 정한다: 계정별 백오프 + 실패 격리 + 후보 순차(앞 후보 401 이면 다음)로, misc 판(전부 실패 시에만
  Err)보다 재시도 폭주 면이 좁다. 근거 = `probe_failure_keeps_previous_values_and_backs_off` ·
  `probe_round_isolates_account_failure`. 병합 전체로는 `src/bin/cysd/schedule.rs:194` 의 소켓키
  싱글플라이트+시도 원장(역할당 MAX 3·쿨다운)과 `ui/src/main.ts` 팬아웃 상한이 이 축의 방어다.
- **② 무clear 100%+** — **정면으로 닿는다.** 해소 ①이 「각성 때 모델에 몇 자를 넣는가」를 정한다:
  master·CEO = 조립기 `core_inject.py`(LIMIT 8800 / HARD 9000) · 그 밖 좌석 resume = T6 상한 9,000자 ·
  그 밖 좌석 startup = 종전 전문. 실측 = `test_t6_injection_policy` F계열(대형 원문 48,000자 →
  master 1,909자 · worker 1,030자) · 드라이런 최악 7,355자. 이 축을 잘못 풀면 각성 한 번이 컨텍스트를
  통째로 먹는다 — 그래서 뮤턴트 5종으로 상한·순서·표지를 전부 겨눴다.
- **③ 자가치유 전멸** — **내 해소는 안 닿는다**(`javis_phoenix.py`·`schedule.rs` 무접촉 — 두 파일은
  자동 병합됐고 내가 한 줄도 손대지 않았다). 병합 전체로는 닿는다: restore 의 R4 재스폰 상한은
  **한 번 걸리면 그 부트 세대가 끝날 때까지 모든 역할의 자동 부활이 멈춘다**(해제 = 데몬 재기동 또는
  `respawn-cap.json` 삭제 · restore HANDOFF §91). 이 성질은 이 티켓이 만든 것이 아니고 바꾸지도 않았으나,
  1.1 배포 판정에서 ③ 축으로 읽어야 하는 값이다. 실측 = `test_phoenix_r4_restore` OK ·
  `test_phoenix_e2_schedule` 10/10.
- **④ 전 pane 사망** — **내 해소는 안 닿는다.** 병합 전체로는 restore·app 의 `ui/src/wsreconcile.ts` 가
  이 축이고, 방어는 「2연속 관측일 때만 집행」(`advanceGhostStrikes`)과 복원/틱의 술어 분리
  (`deadLiveSids` vs `ghostSids`)다. 내가 잰 것 = UM13 뮤턴트가 그 둘을 적색으로 만든다(그물 생존 확인).

## 8. 재현 명령 (통합 트리에서 · cwd 명시)

```bash
W=~/axdev/.wt/cys-v110-integ
export PATH="$HOME/.cargo/bin:$PATH"

# 판번
cd $W && sh scripts/version-check.sh && sh scripts/version-check.sh v1.1.0
python3 scripts/tests/test_version_sot_mutation.py
bash scripts/release-lane-check.sh

# Rust
cd $W && cargo test --lib && cargo test --bin cys && cargo test --bin cysd
cargo test --bin cysd accounts::

# UI (이 워크트리엔 node_modules 가 없다 — 공유 트리 것을 빌려서 잰다)
cd $W/ui && bun test
# ★맨 `ln -sf` 금지(clipath.test.ts MINOR-5 핀): 그 자리에 남의 실체가 있어도 묻지 않고 갈아끼운다.
#   ①비어 있을 때만 만들고 ②우리가 만든 링크일 때만 걷는다(가드 = [ -L ] + readlink).
NM="$W/ui/node_modules"; SRC="$HOME/cys-terminal-src/ui/node_modules"
[ -e "$NM" ] || ln -s "$SRC" "$NM"
( cd "$W/ui" && bunx tsc -p tsconfig.check.json )   # 기준선 = rebase/v1.0.2 git archive 사본에서 같은 방식으로
if [ -L "$NM" ] && [ "$(readlink "$NM")" = "$SRC" ]; then rm "$NM"; fi

# 팩
cd $W/cysjavis-pack/bin && python3 -W ignore -m unittest tests.test_dept_request
python3 tests/mut_dept_request.py            # 백그라운드 필수(약 6분 · 포그라운드 10분 상한)
python3 javis_dept_request.py self-test
cd $W && python3 cysjavis-pack/bin/tests/test_core_inject.py --mutants
python3 cysjavis-pack/bin/tests/test_event_inject.py --mutants
python3 cysjavis-pack/bin/tests/test_session_start_hook.py
python3 cysjavis-pack/bin/tests/test_t6_injection_policy.py
python3 -c "import sys;sys.path.insert(0,'cysjavis-pack/bin');import javis_preflight as p;print(p.core_injection_problems('cysjavis-pack'))"
```

## 9. 함정 (이 트리를 이어받는 사람에게)

- ★★**팩 전수 루프(`cysjavis-pack/bin/tests/test_*.py` 93건)를 그대로 돌리면 자기 워크트리의 팩이 덮인다.**
  그 안에 `CYS_PACK_DIR` 를 저장소 자신의 `cysjavis-pack` 으로 두고 설치·치유를 하는 시험이 있어(후보 =
  `test_formation.py`·`run_bootstrap_health.py`·`test_preflight_c03_states.py`·`test_pyseal_census.py`·
  `test_settings_torn_write.py` 가 그 문자열을 갖고 있다) 팩 파일 약 85개가 임베드 base 로 되돌려지고
  내 편집본이 `<파일>.user` 로 병치됐다(`.pristine/`·`.pack-version`·`.merge-pending.json` 도 생겼다).
  **귀결이 고약하다** — 그 뒤 같은 루프가 실행한 `test_session_start_hook`(2 FAIL) ·
  `test_t6_injection_policy`(20 FAIL) · `test_phoenix_r4_restore`(28 FAIL) · `test_phoenix_e2_schedule`(8/10)
  가 전부 적색이 됐고, 단독 재실행에서는 **넷 다 초록**이었다. 즉 **덮어쓰기가 「내 변경이 깼다」로 보인다.**
  회복 = 산출물 격리 이동 + `git restore --source=HEAD -- cysjavis-pack`(커밋본이 정본). 라이브 팩
  `~/.cys/pack` 은 무접촉이었다(세션 착수 이후 mtime 변경 14건 전부 `round/`·`state/probe_runs.jsonl`·
  `memory/` — 팩 코드·훅·directives 0건).
- 그러므로 **팩 전수 루프와 뮤턴트 하네스를 겹쳐 돌리지 마라.** 이번 라운드는 겹쳐 돌려
  `mut_dept_request.py`(47종) 결과를 폐기하고 하네스를 정지시켰다(정지 뒤 변이 잔존 0 실측).
- **내 문서가 배포문서 파괴명령 핀에 걸렸다**(`ui/src/clipath.test.ts` MINOR-5). 이 핀은 `docs/` 전체와
  리포 루트 `.md` 를 **디렉터리 열거로** 훑으므로 **새 문서를 만드는 순간 조준이 넓어진다.** 셸 코드블록에
  맨 `ln -sf`/`ln -sfn`, 절대경로 `rm`, `-n` 없는 절대경로 `mv`, PowerShell `Remove-Item -Recurse -Force`
  를 쓰지 마라. 인정되는 가드 형태 = 같은 블록에 `[ -L ` 와 `readlink` 가 함께 있는 것(§8 UI 레시피가 그 형태다).

- **팩 전수 루프와 dept 뮤턴트 하네스를 동시에 돌리지 마라.** 하네스가 `javis_dept_request.py` 를 변이하는
  동안 루프가 `tests/test_dept_request.py` 를 실행하면 그 1건이 남의 변이 탓으로 적색이 된다(이번 라운드에
  실제로 겹쳐 돌렸고, 끝난 뒤 그 1건만 단독 재실행해 값을 갈았다).
- **Rust 뮤턴트와 `cargo test` 백그라운드를 같은 트리에서 겹치지 마라**(같은 target 을 공유한다).
- `cargo test -p cys-app` 은 Tauri 빌드 스크립트를 거친다 — `ui/dist` 빌드 + `src-tauri/binaries/` ·
  `src-tauri/resources/` 자리표 + `src-tauri/runtime/` 폴더가 있어야 빌드된다(전부 gitignore ·
  `scripts/bundle-prep.sh` 또는 같은 판본 트리 사본으로 채운다).
- `ui` typecheck 은 `node_modules` 가 없으면 12건, 공유 트리 것을 연결하면 4건이다 — **절대 건수가 아니라
  같은 방식으로 잰 기준선과의 diff(신규 0)** 로 판정하라.
- 이 워크트리 편집 중에 다른 조사 도구가 같은 파일의 줄번호를 읽으면 어긋난다(병합 중 실제로 발생).
