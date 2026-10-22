# HANDOFF — TICKET=cysr-1110-winseal (1.1.10 발행 차단 후보 · 윈 runtime-seal 「추가 28」)

- 가지: `fix/1110-winseal` (기준 `39189404` = rel/1.1.10 · CI 3 녹) · 좌석 560(surface:1559 · worker) · 2026-10-22 08:59 ~
- 지시: 브리프(원장 08:58:50) · 윈 실기 추가 원문 master#21d52c1d · 결정 master#da756888(1.1.10 = 최소안 · 나머지 1.1.11 이월).
- push·태그·판번·설치·발행·rel/1.1.10 쓰기 = 0. 이 노트북·맥 실설치본 무접촉(읽기만 — 아래 run_bootstrap_health 가 설치본 경로를 **읽는** 것뿐).

## 0. 한눈에

| # | 질문 | 판정 | 근거(파일:줄) | 확신 |
|---|---|---|---|---|
| 1 | 설치가 runtime 을 교체하나 덮어쓰나 | **덮어쓴다**(설치·재설치·자동 갱신 전부 같은 NSIS) | `src-tauri/nsis/installer.nsi:661-682` · `src-tauri/nsis-hooks.nsh:796-830,1082` · `src/update/win_install.rs:22` | 높음(코드 + 윈 실기 2) 일치) |
| 1' | 맥도 같은 꼴인가 | **아니다** | `scripts/prep-mac-runtime.sh:28,38-40`(PBS 고정 · pip 동봉) · `src/update/mac.rs:1-7`(앱 통째 RENAME_SWAP) | 높음(코드) |
| 1'' | 봉인은 무엇을 「추가」로 세나 | 디스크에 있고 새 매니페스트에 없는 항목 | `cysjavis-pack/bin/javis_runtime_seal.py` `classify` | 높음 |
| 2 | 1.1.9→1.1.10 런타임 판 변화 | **pip 26.2.1 → 26.2.2 하나뿐** | CI 로그 3런 · `git diff v1.1.9..HEAD` 런타임 준비 단계 0줄 | 높음(실측) |
| 3 | seal FAIL 의 기능 영향 | doctor FAIL · 상담소 거짓 고장 신호 · preflight C80 WARN · bootstrap minor · **자동 갱신 V4 는 지금 무영향(V4 자체가 눈멂 — 별건)** | 아래 §3 | 높음(코드) |
| 4 | 수리 | **집행: 두 Windows 레인 get-pip 를 `pip==26.2.1` 로 고정** + 정적 시험 · 근본안은 1.1.11 | 커밋 `17eb29d3` | 높음(정적) · 윈 실기 재확인 필요 |
| 5 | core_inject rc=2 | **경합** — rotate ④ init-pack 의 pack 폴더 교체 창에 ② 뒤 되살아난 master 의 첫 훅이 걸림 | 아래 §5 | 중상(코드 + 시각 대조 · 윈 1줄로 확정 가능) |
| 5' | claim_denied 08:48:21 | **정상 거부**(이미 열린 앱 안 master 보존) | 키트 `bootstrap.ps1:4522-4530` | 높음 |

## 1. 원인 — 설치기는 runtime 을 지우지 않고 덮어 펼친다

- **NSIS 템플릿 `Section Install`**(`src-tauri/nsis/installer.nsi:661-682`): `SetOutPath $INSTDIR` → 자원마다 `File /a "/oname=…"` — 파일 단위 추출(같은 이름은 덮어씀). runtime 폴더를 비우는 줄은 **없다**. 자원 목록 = `src-tauri/tauri.windows.conf.json` `"runtime/": "runtime/"`.
- **PREINSTALL 훅**(`src-tauri/nsis-hooks.nsh:796-830`)은 잠긴 실행 이미지(.exe/.dll/.pyd/.node)만 `<이름>.prev<난수>` 로 rename 하는 잠금 스윕이다 — 지우기 없음.
- runtime 통째 삭제는 **언인스톨에만** 있다(`src-tauri/nsis-hooks.nsh:1082` `RMDir /r "$INSTDIR\runtime"`).
- **자동 갱신**(`src/update/win_install.rs:8,22`)도 같은 설치기를 `/S /P /UPDATE /CYSTXN=… /D=…` 로 부른다 → 같은 덮어쓰기. bootstrap.ps1 재설치도 설치기를 부른다(윈 실기 3: 「/D」 줄과 「pin stamp」 줄 사이 0줄 = NSIS 가 펼침).
- 윈 실기 2)(runtime 뿌리·git·LICENSES·node = 10-03 · python 만 10-22)와 정확히 맞는다 — 폴더는 교체되지 않았다.
- **결과**: 판과 판 사이에 runtime 안 **파일 목록**이 바뀌면(이름이 사라지는 파일) 옛 파일이 그대로 남고, 봉인이 「추가」로 센다.

**맥은 같은 꼴이 아니다**: python 은 `scripts/prep-mac-runtime.sh:28,38-40` 의 python-build-standalone `PBS_TAG=20260623`(cpython 3.12.13 · pip 동봉 · 별도 pip 설치 줄 0)로 고정이고, 갱신은 `.app` 통째 교체(`src/update/mac.rs` RENAME_SWAP 1회 · 옛 집행 `src/update/macupdate.rs:412-421` 도 rename 2회)라 옛 파일이 남을 자리가 없다. ⇒ 맥 쪽 변경 0.

## 2. 방아쇠 — pip 만 고정이 아니었다

| 런타임 | 고정 여부(빌드 스크립트) |
|---|---|
| PortableGit 2.55.0 | 고정(URL 판번) |
| Python 3.12.10 embeddable | 고정 |
| uv 0.11.26 | 고정 |
| Node.js 22.17.1 | 고정 |
| **pip** | **미고정** — `https://bootstrap.pypa.io/get-pip.py` 를 받아 인자 없이 실행 = 그 순간 최신 pip |

CI 로그 실측(`gh run view <id> --log` 의 「Successfully installed pip-…」):

| 런 | 판 | pip |
|---|---|---|
| release 37756897270 | v1.1.8 | 26.2.1 |
| release 38917264564 | v1.1.9 | 26.2.1 |
| windows-build 39679438763 | rel/1.1.10(시험 키트 산출물) | **26.2.2** |

- `git diff v1.1.9..HEAD` 의 release.yml·windows-build.yml 에 런타임 준비 단계 변경 0줄 ⇒ **1.1.9→1.1.10 런타임 판 변화 = pip 하나뿐**.
- 윈 실기 1)(site-packages 의 dist-info = pip-26.2.1·pip-26.2.2 둘뿐 · pip 외 옛 dist-info 0)과 일치. 「추가 28」= 옛 `pip-26.2.1.dist-info/*` 28개.
- ⚠ 고정 전에는 **실제 발행 빌드(release.yml)도 그 순간의 최신 pip** 를 받았다 — 시험 키트(windows-build)와 발행 바이트의 pip 판이 갈릴 수 있었다.

## 3. 영향 — seal FAIL 을 누가 읽나(호출부 grep)

| 소비처 | 읽는 방식 | 영향 |
|---|---|---|
| `cys doctor` runtime-seal(`src/bin/cys.rs:10502` `diag_runtime_seal`) | 판정을 `javis_runtime_seal.py verify` 에 위임 | **FAIL** + 회복 문구 「재설치」 — 재설치도 덮어쓰기라 **재설치로 안 낫는다** |
| 상담소 `cysjavis-pack/bin/javis_counsel.py:408-431` `probe_doctor` | `doctor --json` 의 items 에서 FAIL 이름을 `fail_ids` 로 | 매일 상담 보고에 runtime-seal 거짓 고장 신호(업그레이드한 윈 사용자 전원) |
| preflight C80(`javis_preflight.py:7285` · 등재 주석 `:7468` 「읽기 전용·WARN-only」) | 같은 판독기 | WARN — 부트 비차단 |
| bootstrap.ps1 좌석 판정 | doctor 항목 | 윈 실기 3: `minor=runtime-seal` · 「고장이 아닙니다 — 설치에 영향 없음」 — 설치 흐름 비차단 |
| **자동 갱신 사후검증 V4**(`src/update/verify.rs:191-192` 「새 FAIL」 → `src/update/runner.rs:350-353` 실패 시 되감기) | `realops.rs:343-350` `doctor --json` 을 **`checks` 배열**로 읽음 | **지금은 무영향 — V4 자체가 눈멀어 있다**(§6-⑴). 고치는 순간 「옛 판 잔여 = 새 FAIL = 되감기」 |

## 4. 수리 — 집행분(1.1.10 · master#da756888 ①)

커밋 **`17eb29d3`** — 3파일 · +26/−2:

- `.github/workflows/release.yml` · `.github/workflows/windows-build.yml`: get-pip 실행 줄 끝에 `"pip==26.2.1"` + 근거 주석 1줄. 다른 런타임 핀(Git·Python·uv·node)과 같은 자리(런타임 준비 단계 안 · 판번 리터럴). **1.1.8·1.1.9 릴리스와 같은 판** ⇒ 1.1.8·1.1.9 → 1.1.10 업그레이드에서 pip 파일 목록이 같아 옛 잔여 0(판이 같으면 같은 wheel → 같은 파일 목록 · 바이트가 다른 `.pyc` 는 같은 이름이라 덮어써져 「변경」도 0).
- get-pip 고정 인자 실측: get-pip.py(`determine_pip_install_arguments` = 사용자 인자 + `"pip"` → `pip install --upgrade --force-reinstall pip==26.2.1 pip`)를 내려받아 `--target` 임시 폴더로 실행 → 「Successfully installed pip-26.2.1」 · dist-info 1개(26.2.1)뿐(맥 python 3.14 로 측정 — 해결기 동작은 같다 · 윈 embeddable 3.12 실측은 CI 로그로 확인할 것).
- 문구 변경 0 · 설치기·봉인 판독기·Rust 변경 0.

**정적 시험** — `cysjavis-pack/bin/tests/test_runtime_manifest_parity.py` ⑧ `test_both_windows_lanes_pin_the_same_pip`(이미 3완전 레인 ci-branch·release·pack-release 에 등재된 검체 — 레인 대조 게이트 등재 변경 불요):

| 단계 | 결과 |
|---|---|
| 적(수리 전) | FAILED — 「release.yml 의 get-pip 가 pip 판을 고정하지 않는다(최신을 받는다)」 |
| 녹(수리 후) | 파일 전체 11/11 OK |
| M1 windows-build 고정 제거 | FAILED |
| M2 release 판 갈림(26.2.2) | FAILED |
| M3 미고정 get-pip 줄 재등장(고정 줄은 그대로) | FAILED — 「…고정하지 않는다」(사유 확인) |
| M4 get-pip 실행 줄 삭제 | FAILED — 「실행 줄이 없다 — 배선이 사라졌다」 |

### 4-1. 윈 실기 재확인 필요 — 무엇을 재나
- 이 노트북은 이미 **26.2.2 키트**를 깔았다. 고정 판(26.2.1) 새 산출물을 그 위에 덮으면 이번엔 거꾸로 `pip-26.2.2.dist-info` 가 남는다(같은 덮어쓰기). ⇒ 실기 대조는 **1.1.9 깨끗한 상태 → 새 1.1.10** 경로로 재야 한다(언인스톨 후 1.1.9 설치 → 새 1.1.10). 기대: runtime-seal 「추가 0 · 변경 0 · 누락 0」(dlls-copied.exe 는 runtime_managed).
- CI 로그에서 두 레인 모두 「Successfully installed pip-26.2.1」 1줄 확인.

## 5. core_inject rc=2 — 「조립기 파일」= `hooks/core_inject.py` 자신 · 교체 창 경합

**rc=2 가 말하는 것**(`cysjavis-pack/hooks/session-start.sh:603-628`): `CI_RC` 기본값은 127(`:607`)이고 `[ -f "$CI" ]` 가 참일 때만 조립기를 **실행**해 rc 를 받는다(`:608-615`). rc=2 = **실행했다** = 실행 직전엔 파일이 있었다. 실패 사유 갈래에서 `[ ! -f "$CI" ]`(`:625`)가 참 = 끝난 뒤엔 없었다. python 은 스크립트를 못 열면 rc 2 를 낸다. ⇒ 실행 중에 파일이 사라졌다 = **교체 중**. 「조립기 파일」은 `hooks/core_inject.py` 자신이 맞다(`$CI` 의 두 후보 모두 그 이름 — `:605-606`).

**교체 순서**(`src/bin/cys.rs` `run_rotate:21831`): ① drain → ② 데몬 교체·새 데몬 확인(`:21875~` · `identify` = bootstrap 표지 2-daemon-up · 새 데몬의 콜드부트 복원이 좌석을 띄울 수 있다) → ④ `init-pack --no-install-hook`(`:21961-21966` · 표지 4-pack) → ⑤ `restore --include-master`(`:21979` · 표지 5-restore).
init-pack = `cys::pack::install_staged`(`src/bin/cys.rs:8160`) → staging 에 팩 전량 복사 → 반영·검증 → `atomic_swap`(`src/pack.rs:5000`) = `pack → pack.prev` rename, `staging → pack` rename. 두 rename 사이 pack 부재 창 — 코드 주석(`src/pack.rs:4995-4999` L6)이 「**데몬 미가동/init 시점 전제**」로 안전하다고 적었는데, rotate 는 ④를 **② 새 데몬 가동 뒤**에 부른다 = 전제 위반.

**시각 대조**(윈 실기 4): 4-pack 표지 08:49:54 · core_inject.py **Created 08:49:53**(= staging 복사 시각 · rename 은 Created 를 보존 → 지금 파일은 그 staging 이 rename 으로 들어온 것) · 오류 **08:50:06** · 5-restore 표지 08:50:08 ⇒ 오류 시각 = init-pack 끝 무렵 = 교체 시각. 「오류 시각이 파일 생성 뒤」는 모순이 아니다 — Created 는 staging 에서의 생성 시각이고 실제 자리(`~\.cys\pack`)에 들어온 것은 08:50:0x 의 rename 이다.

**미확정 1점**: 실행 전 있음 → 실행 후 없음은 창이 python 기동 시간(수십~수백 ms)보다 길었다는 뜻이다. 순수 rename 2회면 창은 ms 단위라 빠듯하다 — `pack → pack.prev` rename 이 윈 열린 핸들(데몬·훅이 팩 안 파일을 잡음)로 실패해 **복사+삭제 폴백**(`src/pack.rs:4983-4990` `rename_dir_or_move`)을 탔을 개연성. 확정 = 윈 실기 1줄: `~\.cys\pack.prev\hooks\core_inject.py` 의 Created(08:47:4x 근처면 rename · 08:50:0x 면 복사 폴백).

**사용자 영향**: 그 master 세션의 **첫 각성만** 폴백 — CORE-MIN + DRAIN 규칙 + 역할 고지 + 부트 브리지만 싣고(`session-start.sh:629-646`), 요지 조립기가 내는 CORE 나머지(요지 해시 대조 절·각성 헤더·원문 절 목차)가 빠진다. 훅은 exit 0(세션은 정상 기동) · 다음 세션부터 정상. hook-errors.log 1줄 = 다른 훅은 그 창을 안 밟았다.

**claim_denied 08:48:21**: 키트 `bootstrap.ps1:4500-4530` — `new-surface --role master` 실패 뒤 `Test-SeatClaimDenied` 갈래로 「자비스는 이미 열려 있는 cysr 앱 안에 있습니다 — 여기서 또 띄우지 않습니다」 + 앱 창만 앞으로. 살아 있는 master 를 지키는 **정상 거부**다. 사용자 영향 = 없음. 줄 머리 `new-surface failed:` 가 실패처럼 보이는 것만 문제(§6-⑶).

## 6. 1.1.11 이월 (master#da756888 ② — 이번에 고치지 않음)

### ⑴ 자동 갱신 사후검증 V4 눈멂 — 근본안(설치기 매니페스트 밖 정리)과 반드시 함께
- **재현 근거**: `src/update/realops.rs:343-350` `doctor_fail` 은 `doctor --json` 결과에서 `v["checks"].is_array()` 일 때만 판독하고 아니면 `{"doctor_unavailable"}` 를 돌려준다 · `:519-528` `doctor_fails` 는 `checks[].status|result` · `id|name` 을 읽는다. 그런데 `cys doctor --json`(`src/bin/cys.rs:11479-11498`)은 `{"fix","summary","items":[{"name","status","detail","action"}]}` — **`checks` 키가 없다**. ⇒ 기준선(`realops.rs:656`)·사후(`:912`) 모두 `{"doctor_unavailable"}` → `verify.rs:191` 차집합 0 → V4 **항상 통과**. 단위 시험(`realops.rs:1673-1675`)은 `checks` 꼴 가짜 JSON 이라 이 어긋남을 못 본다(상담소 `javis_counsel.py:425-431` 은 `items`·`name` 으로 맞게 읽는다 — 같은 출력의 두 소비자가 다른 계약).
- **연쇄 위험**: V4 만 고치면, 기준선 PASS(1.1.10 은 dlls-copied 면제로 PASS 가능) → 판 사이 runtime 파일 목록이 바뀐 갱신에서 사후 runtime-seal FAIL = **새 FAIL** → `runner.rs:350-353` 되감기 → 다음 시도도 같음 = **자동 갱신 영구 실패**.
- **수리안**: (a) V4 판독을 `items`·`name`·`FAIL` 로 맞추고 실 `doctor --json` 출력으로 시험(가짜 JSON 금지) + (b) 근본안 — 설치기 POSTINSTALL 에서 **새 runtime-manifest 밖 + runtime_managed 밖 + `.prev*` 밖** 파일만 정리(또는 새 runtime 을 옆 폴더에 펼친 뒤 원자 교체 — 단 라이브 셸이 runtime DLL 을 잡고 있어 폴더 rename 이 막히는 것이 윈 특성이라 위험 큼). 봉인 판독기는 「자동 삭제 0」 계약(`javis_runtime_seal.py` 머리 주석 · 명세 §2-10)이라 정리 주체는 설치기여야 한다.
- **윈 실기 필요**: 예 — (b) 는 NSIS 훅 변경 · 잠긴 파일·AV 경합 실측 필수. (a) 단독은 맥에서 시험 가능하나 (b) 없이 내보내면 안 된다.

### ⑵ init-pack atomic_swap 부재 창 × rotate(데몬 가동 뒤) 경합 → 첫 각성 CORE-MIN
- **재현 근거**: §5. `src/pack.rs:4995-4999` L6 전제(데몬 미가동) ↔ `src/bin/cys.rs:21875-21979` 순서(② 데몬 가동 → ④ init-pack).
- **수리안**: (a) 최소 — `session-start.sh` 조립기 실패가 「파일 없음」일 때 1초 뒤 1회 재시도(문구 변경 0 · 다른 사유는 그대로 폴백) · (b) 구조 — rotate ④ 를 ② 앞(옛 데몬 정지 뒤·새 데몬 기동 전)으로 옮기거나 새 데몬의 콜드부트 복원을 ④ 뒤로 미룸(rotate·데몬 기동 계약 변경 = 큰 변경) · (c) `rename_dir_or_move` 폴백 여부를 로그에 남겨 창 길이를 실측 가능하게.
- **윈 실기 필요**: (a) 는 맥 시험 가능(교체 창 모사) · 원인 확정(rename vs 복사 폴백)은 윈 1줄(§5 미확정 1점).

### ⑶ bootstrap 「new-surface failed」 줄 머리 (문구 = 보고만)
- **재현 근거**: 윈 실기 5) 08:48:21 `new-surface failed: rc=1 claim_denied: privileged role 'master' is held by a live surface` · 키트 `bootstrap.ps1:4522` 가 거부 판별(`:4525 Test-SeatClaimDenied`) **전에** 무조건 `new-surface failed:` 로 기록.
- **수리안**: 판별을 앞에 두고 거부면 `seat claim denied (normal): …` 한 줄만 · 실패면 종전 줄(jarvis-install 저장소 — 이 저장소 밖).
- **윈 실기 필요**: 아니오(문구 · 로그 판독만). 문구 변경이라 master 결정 대상.

## 7. 검증 숫자

| 시험 | 결과 |
|---|---|
| `cysjavis-pack/bin/tests/test_runtime_manifest_parity.py` | 11/11 OK(새 ⑧ 포함) · 적→녹 · 뮤턴트 4/4 적 |
| `test_runtime_seal.py` | 22/22 OK |
| `test_preflight_c80_runtime_seal.py` | 18/18 OK |
| `test_pyseal_negative_specimen.py` · `test_pyseal_census.py` | OK · OK |
| 워크플로를 읽는 scripts/tests: `test_release_trigger_split` 16 · `test_release_postprocess_gate` 82 · `test_release_verify` 140 · `test_check_no_ioreport_link` 12 · `test_update_publish` 112(skip 14) | 전부 OK |
| 워크플로를 읽는 팩 시험: `test_secret_scan_limit` 10 OK · `test_default_fleet_formation` · `test_phoenix_w5_windows` · `test_wp7_gate_triage` | 전부 rc 0 |
| ci-branch 「팩 스위트 레인 대조」 스텝 본문을 그대로 뽑아 실행 | 비대칭 0 · 부분 레인 계약 충족 |
| release.yml·windows-build.yml YAML 판독 | OK |
| `run_bootstrap_health.py` | 166 PASS / **2 FAIL**(H-CLT-1·H-CLT-2) / 1 SKIP — 기준 커밋 대조는 §7-1 |
| cargo · ui(tsc) · win-typecheck | **생략** — Rust·TS 변경 0(diff = 워크플로 2 · 팩 시험 1) |

### 7-1. run_bootstrap_health 적 2건
기준 커밋 `39189404` 를 임시 작업트리(detached · 대조 뒤 제거)로 떠 같은 기기에서 다시 잼: **166 PASS / 2 FAIL(H-CLT-1·H-CLT-2) / 1 SKIP — 적 목록 동일** ⇒ 이번 변경과 무관한 기존 적이다. 두 적 모두 이 맥에 설치된 `/Applications/cys.app` 의 동봉 python 을 프리루드가 고르는 호스트 의존 판정(H-CLT-2 문면: NEW=`…/cys.app/Contents/MacOS/../Resources/runtime/python/bin/python3` · OLD=`/opt/homebrew/bin/python3`)이다. 이번 수리 범위 밖 · 판정은 master.

## 8. 증류

- 메모리 후보 1건(master 판단): 「윈 NSIS 는 runtime 을 덮어 펼친다 — 런타임 안 파일 목록이 판 사이에 바뀌면 옛 파일이 봉인 『추가』로 남는다 · 빌드가 받는 런타임 구성요소는 전부 판 고정(get-pip 포함)」. 작성은 하지 않았다.
