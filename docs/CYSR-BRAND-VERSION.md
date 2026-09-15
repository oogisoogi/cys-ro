# cysr 표시명 · 판번 1.0.0 · 이중 게이트 · 윈도우 깜빡임 — 구현 보고서

TICKET=cysr-brand-version · 2026-09-15 · 브랜치 `feat/cysr-brand`(base 9cb4074) · CI 미러 `fix/cysr-brand-version`

## 1. 무엇을 바꿨나 (처리표)

| 항목 | 한 일 | 커밋 |
|---|---|---|
| ⓐ 표시명 cysr | 창 제목(tauri.conf) · 문서 제목 · 좌상단 이름 · Control Center 아래 안내 · 설치본 손상 안내 · 릴리스 이름과 본문 첫 줄 | b392c33 |
| ⓑ 판번 1.0.0 | 버전 SOT 8곳 + Cargo.lock 재생성 · `version-check.sh` 통과 | b392c33 |
| ⓑ-2 build_id 이중 게이트 | 빌드 식별자 굽기 · 앱 판번 동일 분기 · release-verify 9단계 · CI build_id 병기 · pack-manifest build_id | 334aeec |
| ⓒ 윈도우 콘솔 창 깜빡임 | 주기 잡 python 6파일 27호출 창 숨김 · cysd 계정 어댑터 cmd 스폰 창 숨김 · 회귀 시험 | 9501dd6 |
| ⓓ 릴리스 노트 초안 | `docs/RELEASE_NOTES_1.0.0.md`(참가자용 · 내부 용어 0) | 5c5ba3b |
| ⓔ CC 헤더 경보 배지 제거 | 요소 · CSS · 갱신 코드 제거 · 시험 | 94dd866 |

## 2. 설계 결정과 근거

### 2-1. 개명은 표시명만 (master 결정)
바꾸지 않은 것과 이유 — 기존 설치본이 **제자리 업데이트**로 새 판을 받아야 한다.

| 그대로 둔 것 | 위치 | 이유 |
|---|---|---|
| productName `cys` · identifier `com.cysjavis.terminal` | `src-tauri/tauri.conf.json:3,5` | 번들 이름·설치 경로·NSIS 제품 ID 가 여기서 파생된다. 바꾸면 중복 설치·업데이트 단절 |
| WiX 제품 이름 `cys (CYSJavis Terminal)` | `dist-win/cys.wxs:3` | 레거시 MSI(현행은 NSIS) · 판번만 올림 |
| 실행파일 리소스 ProductName `cys` | `build.rs:260` | 파일 속성 식별자 |
| 맥 권한 안내 「…에서 cys를 허용」 | `ui/src/main.ts:6990` | 시스템 설정 목록에 실제로 보이는 이름이 번들명 cys — 바꾸면 거짓 안내 |
| 원작자 표기 블록 | `ui/index.html:42` · `release.yml` releaseBody | 원작자 허락 조건 · 무접촉 |
| 명령어 `cys` | 전역 | 명령 이름 변경은 범위 밖 |

### 2-2. 판번 비교 — 0.14.x 가 1.0.0 을 받는 근거
tauri-plugin-updater 2.10.1 `updater.rs:530-532`: 비교 함수를 지정하지 않으면 `release.version > self.current_version`(semver). 1.0.0 > 0.14.37 · 1.0.0 > 0.14.36 이므로 기존 설치본은 판번 비교만으로 새 판을 받는다. 벤더·우리 원격 모두 `v1.*` 태그 없음(`git ls-remote` 실측) — 이름 충돌 없음.

### 2-3. build_id 이중 게이트 (master 결정 3c3bf910 · cb42d0f5)
- **형식** `<커밋 12자>[-dirty].<UTC yyyymmddTHHMMZ>`. `build.rs` 가 `CYSR_BUILD_ID` 가 있으면 그 값, 없으면 git 과 현재 시각으로 만든다. 날짜 변환 산식은 파이썬 datetime 과 20,010건 대조 불일치 0.
- **CI 는 커밋 시각을 쓴다(지시 없이 내린 판단 1건)** — 매트릭스 3레그·pack-artifacts·stamp 잡이 각자 빌드 시각을 찍으면 같은 발행 안에서 build_id 가 갈린다. 같은 커밋이면 같은 값이 나오는 커밋 시각 산식으로 잡 사이 전달을 없앴다.
- **앱(2순위 판정)** 판번 비교가 「없음」이면 latest.json 을 따로 받아 판정한다(플러그인 `RemoteRelease` 가 추가 칸을 버리므로 — `updater.rs:92-101`). 같은 판 · 다른 build_id → 받음 / 같은 build_id → 건너뜀 / 원격 build_id 없음(구판) → 건너뜀 / 내 build_id 모름 → 건너뜀 / 조회·파싱 실패 → 건너뜀 + 로그.
- **발행 게이트(1순위 방어선)** `release-verify.py` 9단계 — 공개판 latest.json 과 비교해 판번 역행 거부 · 같은 판인데 build_id 가 다르거나 직전판에 없으면 거부 · build_id 형식 fullmatch(`-dirty`·개행 거부). 직전판 조회 실패 = 실패(모르는 채 발행하지 않는다).
- **팩 판번은 독립 증가 유지**(master 결정 cb42d0f5 (나)) — 이번만 앱·팩 1.0.0, 이후 팩-온리 무중단 레인 보존.
- ⚠ **순서 계약**: `release-postprocess.py`(SHA256SUMS.txt 생성)는 `stamp-latest-build-id` 잡 **뒤**에 돌아야 한다. 앞이면 SUMS 의 latest.json 해시가 병기 전 값이라 release-verify 5단계에서 체크섬 불일치로 멈춘다(fail-closed · 발행 사고는 아님).

### 2-4. 윈도우 콘솔 창 깜빡임
사슬: cysd(콘솔 없음) → 동봉 bash(창 숨김) → 스케줄 잡 python → **숨김 없는** `cys.exe`·`powershell`·`python` 스폰 → 새 콘솔 창. `cycle-autopilot-tick` 은 매분 돌며 틱마다 `cys.exe` 를 2회 이상 부른다. 같은 계열 실사고가 `javis_hud_bridge.py:41-44`(2026-07-11)에 기록돼 있었고 처방이 그 파일에만 있었다. 같은 처방(`NOWIN`)을 builtin 주기 잡이 실행하는 python 6파일에 적용했다. cysd 쪽은 스폰 규약에서 유일하게 빠져 있던 `accounts.rs` 계정 어댑터 `cmd /C` 에 `hide_console` 을 붙였다.
사거리(정직): 정적 검사로만 증명했다. 윈도우에서 창이 실제로 안 뜨는지는 이 로컬에서 재지 못한다. 동봉 bash 가 네이티브 python 을 띄울 때 창을 만드는지(MSYS 층)는 미검증이다. bash 스크립트(`cys-dept`) 내부 스폰은 python 처방 밖이다.

## 3. 검증

| 게이트 | 결과 |
|---|---|
| `version-check.sh` | ✅ 8곳 일치 1.0.0 |
| cargo test(루트) | lib 492 · cys 244 · cysd 959 통과 · 실패 0 (base 보고서 수치와 같음) |
| cargo test(cys-app) · accounts 핀 | cys-app 124 통과 · 실패 0(새 시험 `same_version_verdict_updates_only_on_a_different_build_id` · `latest_json_url_is_the_updater_endpoint` 포함) · `accounts::tests::periodic_cmd_adapter_spawn_hides_console` 통과 |
| release-postprocess 스위트 | 45 통과(+5: build_id 병기 확인 — agy 1R 반영) |
| bun test | 841 통과 · 실패 0 (+7) |
| UI typecheck | 신규 0 (기존 `updateplan.test.ts` toMatch 1건) |
| release-verify 스위트 | 94 통과 (+10: 9단계 8 · CLI 2) |
| 팩 스위트 | test_nowin 2/2 · test_formation 42/42 · test_default_fleet_formation 120/120 · test_import_guard 136/136 · autopilot selftest 194/0 · verifier selftest 73/0 |
| 뮤턴트 python/UI | 12/12 잡힘(대조군 초록 확인 · 변이 적용 단언 · sha 복원 단언) |
| 뮤턴트 Rust | 5/5 잡힘(대조군 초록 · 제자리 변이 뒤 sha 복원 단언) — R1 같은 build_id 비교 뒤집기 · R2 원격 build_id 부재를 업데이트로 · R3 판번 다름 분기 제거 · R4 내 build_id unknown 가드 제거 → `same_version_verdict_updates_only_on_a_different_build_id` · R5 accounts `hide_console` 제거 → `periodic_cmd_adapter_spawn_hides_console` |
| test_version_sot_mutation | 로컬 14/14 — CI 첫 실행에서 적색이었던 결함 수리 뒤(§4-2) |
| 맥 로컬 빌드 | 성공 rc 0 · `target/release/bundle/macos/cys.app`(빌드 대상 커밋 5c5ba3b) · 저장소 루트에서 `bundle-prep.sh` → `precompile-bundled-python.sh` → `tauri build --bundles app`(업데이터 산출물 끔 · Apple 자격 env 해제 · 서명 없음 — `cys-local` 신원이 이 키체인에 없어 서명 단계 생략) · 번들 파이썬 런타임은 원 체크아웃 사본을 APFS 복제 |
| 번들 자산 대조 | Info.plist `CFBundleShortVersionString`=1.0.0 · `CFBundleName`=cys · `CFBundleIdentifier`=com.cysjavis.terminal · `cys-app` 바이너리에 `cysr — CYSJavis Terminal` 바이트 2건 · 옛 제목 0건 · `ui/dist/index.html` 제목·brand = cysr · 경보 배지 0건 · dist(20:03:32)가 앱 바이너리(20:06:19)보다 먼저 만들어짐 |
| build_id 스탬프 | cysd·cys = `5c5ba3ba86f2.20260915T1103Z` · cys-app = `5c5ba3ba86f2.20260915T1104Z` — 로컬(CYSR_BUILD_ID 없음)에서는 앱과 사이드카가 빌드 스크립트를 따로 돌려 분 단위로 갈릴 수 있다(CI 는 레그 공통 값을 넘겨 갈리지 않는다 · §5) |
| CI | ci-branch 34961327054 · windows-build 34961327090 · windows-health 34961327169 (진행 중) |
| agy 1R | (진행 중) |

뮤턴트(python/UI):

| 번호 | 변이 | 잡은 시험 |
|---|---|---|
| M1 | autopilot `run()` 의 `**NOWIN` 제거 | test_nowin_periodic_spawns |
| M2 | formation NOWIN flag 0 | test_nowin_periodic_spawns |
| M3 | fleet_report send 호출 NOWIN 제거 | test_nowin_periodic_spawns |
| M4 | 판번 미증가 게이트 무력화 | test_exit_1_when_version_not_bumped 외 |
| M5 | build_id fullmatch → match | test_96 |
| M6 | 판번 역행 비교 뒤집기 | test_exit_0_on_pass 외 |
| M7 | 직전판 조회 실패를 빈 객체로 삼킴 | test_exit_1_when_previous_latest_unreadable 외 |
| M8 | verify 9단계 호출 제거 | test_exit_1_when_version_not_bumped 외 |
| U1 | 헤더 배지 요소 되살림 | brandbadge 「헤더 배지 요소·스타일·갱신 코드가 어디에도 없다」 |
| U2 | 창 제목 cys 로 | brandbadge 「창 제목·문서 제목·좌상단 이름이 cysr 다」 |
| U3 | 좌상단 brand cys 로 | 같은 시험 |
| U4 | 렌더 함수에 배지 갱신 되살림 | brandbadge 「렌더 함수는 스트립만 채운다」 |

## 4. 사고 기록 — 저장소 팩 폴더 오염(복구 완료)
19:53 팩 스위트 실행 중 이 워크트리의 `cysjavis-pack` 이 설치 동작으로 덮어써졌다. 미커밋 NOWIN 편집 6파일이 base 내용으로 되돌아가고(편집본은 `.user` 로 보존) 79파일 모드 644→755 · `schedule.json` 키 재정렬 · `.pristine/`·`.pack-version`·`.merge-pending.json` · 저장소 루트 `claude/` 가 생겼다. 그 결과 첫 커밋 묶음의 깜빡임 커밋에 수리 없이 시험만 담겼다(stat 0줄로 발견).
근거: `tests/test_formation.py:27` · `tests/test_default_fleet_formation.py:23` 이 `CYS_PACK_DIR` 를 저장소 `cysjavis-pack` 자신으로 둔다. 어느 호출이 치유를 수행했는지는 특정하지 못했다(확신도 Med). 라이브 `~/.cys/pack` 은 무접촉(파일 수정 시각 실측).
복구: `.user` 백업 → `git checkout -- cysjavis-pack` → 산출물 삭제 → NOWIN 재적용(백업과 cmp 동일 6/6) → 커밋 2~5 재구성 → 트리 clean. 두 스위트를 임시 팩 사본에서 돌리게 고치는 일은 이 티켓 범위 밖이라 손대지 않았다.

### 4-2. CI 첫 실행 적색 — 판번 1.0.0 이 드러낸 시험 결함(수리 완료)
ci-branch run 34961327054 의 `macos-rust-pack` 잡이 `scripts/tests/test_version_sot_mutation.py` 에서 16건 어긋남으로 멈췄다(`boot-health-full`·`nsis-hook-harness` 는 초록). 출력 첫 줄이 `NEW=1.0.0 OLD=1.0.0` 이었다. 원인: 「이전 판」을 만드는 `older()` 가 패치 자리만 `max(0, patch-1)` 로 내려서 patch 가 0 인 1.0.0 에서는 같은 값이 나왔다 → 8종 변조가 전부 무변조가 되어 「단일 변조 아님 · 게이트 통과」로 적색. 로컬에서 이 시험을 커밋 전에 돌리지 않았다(발견이 CI 로 밀린 이유). 수리: 0 이 아닌 가장 낮은 자리를 내린다(1.0.0→0.0.0 · 0.14.0→0.13.0 · 0.0.0→`-old`) · 같은 값이면 fail-closed. 로컬 14/14.

## 5. 한계
- 윈도우 깜빡임 수리의 실기 효과는 미측정(§2-4 사거리).
- 앱 판번 동일 분기는 latest.json 을 두 번 받는다(플러그인 조회 + 자체 조회). 그 사이에 발행이 바뀌면 자체 조회 판정과 플러그인 재확인이 다른 판을 볼 수 있다 — 재확인 비교 함수는 `release.version >= current` 라 같은 판의 다른 build_id 를 구별하지 못한다. 발행 게이트가 「같은 판 · 다른 build_id」 발행 자체를 막으므로 정상 경로에서는 도달하지 않는다.
- 맥 실행 창 제목은 앱을 띄워 재지 않았다(라이브 데몬·팩과 충돌 위험) — 번들 자산으로만 대조.
- 로컬 빌드(CYSR_BUILD_ID 없음)는 앱과 사이드카의 build_id 시각이 분 단위로 갈릴 수 있다(실측 1103Z/1104Z). 판번 동일 분기는 앱 자신의 build_id 만 쓰므로 판정에는 영향이 없고, 발행 빌드는 CI 공통 값이라 갈리지 않는다.

## 6. agy 판정 이력

| 라운드 | 판정 | 지적 | 처리 |
|---|---|---|---|
| 1R | BLOCK | `release.yml:1361` — release-postprocess 를 돌리는 잡에 `needs: [stamp-latest-build-id]` 가 없어 SUMS 가 병기 전 해시를 박제한다 | **전제 반박**: 워크플로 어디에도 release-postprocess.py 를 돌리는 잡이 없다(등장은 주석 2곳뿐 — `ci-branch.yml:151` · `release.yml:1371`). 사람이 부르는 단계라 `needs:` 로 걸 대상이 없다. **위험은 수용**: 사람이 stamp 잡 전에 돌리면 같은 사고가 난다 → `release-postprocess.py` 1-b 단계에서 build_id 병기를 fullmatch 로 확인하기 전에는 SUMS 를 만들지 않게 했다(ba9770d · 시험 5건). |
| 2R | REVISE | `release-postprocess.py:160` — 형식만 보므로 남아 있던 옛 latest.json(다른 판·다른 커밋)이 통과한다. 1R 전제 반박은 「타당」 판정 | **수용**: 가드를 이 발행에 결박 — latest.json version == 태그 판 · build_id 앞 12자 == `git rev-parse --short=12 <tag>^{commit}` · 태그 커밋 확인 불가 = 차단 · latest.json 은 다운로드 캐시를 쓰지 않는다(크기가 우연히 같은 옛 파일 방지). 시험 10건. |
