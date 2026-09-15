# 좌석별 폴더 · 기계유래 스폰 억제 폐지 — 구현 보고서 (TICKET=cys-seat-folders)

작성: worker-3(surface:729) · 2026-09-15 · 브랜치 `feat/seat-folders`(base `9cb4074`) · 다음 판(v0.14.38) 통합 대상

## 1. 무엇이 바뀌었나 (한 문단)

자비스 함대의 자식 좌석(CSO·워커)이 더 이상 마스터와 **한 폴더를 같이 쓰지 않는다**. 마스터는 설치기가 준 폴더(JarvisHome)에 그대로 있고, CSO 는 `JarvisHome/cso/`, 워커는 `JarvisHome/workers/w1/`(워커 N 은 `workers/wN/`)에서 뜬다. 좌석 폴더가 새로 만들어질 때 그 폴더에 역할을 알려 주는 짧은 `CLAUDE.md` 가 한 번 생기고(이미 있으면 건드리지 않는다), Claude Code 가 "이 폴더를 믿겠습니까" 창을 띄우지 않도록 프로필 설정에 그 폴더의 신뢰 표시를 남긴다(이미 값이 있으면 건드리지 않는다). 함께, 참가자 기계에서 `cys send` 로 들어온 "너는 마스터다" 선언이 기계 배달로 판정돼 **팀이 안 뜨던 억제**를 오너 결정대로 없앴다 — 판정과 기록은 그대로 남고, 기계 배달 선언은 팀은 띄우되 부서 자동 생성 권한은 받지 못한다.

## 2. 처리표 ⓐ~ⓔ

| 항목 | 처리 | 코드 위치 | 시험·실측 |
|---|---|---|---|
| ⓐ 좌석 폴더 | cso → `cso/` · worker·worker-1 → `workers/w1/` · worker-N → `workers/wN/` · master·리뷰어 무변경 · 기준이 홈·루트면 만들지 않음 | `cysjavis-pack/bin/javis_seat.py`(규칙·준비) · `src/seat.rs`(Rust 판본) · 골든 표 `cysjavis-pack/templates/seat-layout.json` · 배선 = `javis_formation._role_seat_cwd` · `javis_phoenix.seat_fresh_cwd` · `src/bin/cys.rs boot_seat_cwd` | test_seat_folders S1·S6 · Rust `seat::` · 스모크 `cys list` cwd 실물 |
| ⓑ 얇은 CLAUDE.md | `templates/seat-CLAUDE.md`(5줄 · 공식 표현) · 없을 때만 · 기존 파일 보존 | 같은 두 모듈의 CLAUDE.md 시드 | S2 · Rust `ensure_seat…idempotent` · 스모크 CLAUDE.md 2개 |
| ⓒ 신뢰 시드 | 상속 실측(git 루트에서 정지) + master 판정(f12093fe)으로 **상속 + 시드 이중** · 부재 키만 · 다른 키·기존 값(null·false 포함) 보존 · 설정 파일 없으면 미생성 · 교체 직전 재대조(원자 보장 아님) | `seed_trust`(두 모듈) · 계약 = `pack::plan_first_run_seed` | S3 · S4(실 claude: 시드 없는 git 좌석 = 창 뜸 · 시드된 git 좌석 = 창 0 + 다음 화면 도달) · 스모크 신뢰 키 3 |
| ⓓ 스폰 억제 폐지 | 억제 분기만 제거 · 판정·대장·진단 유지 · 기계 유래·판정 불가 선언은 선언 유래 보증 없음(부서 자동 생성 봉인 유지) · harness 알림·기동 명령문은 종전대로 무스폰 | 레거시 `role-bootstrap-legacy.sh` · Rust `declaration_spawn_origin` · `docs/THREAT-MODEL-mission-gate.md §4-10-A` | S5a~e · Rust `declaration_spawn_origin…` · health H-MISSION-1 ⓓ-1·ⓓ-2·ⓕ 계약 뒤집기 · hook P0-5 ⓑ·ⓕ |
| ⓔ 회귀 축 | 646 phoenix S3 콜드부트 master 복원 · 663 리뷰어 온디맨드 · 722 r3 reset-clean — **무접촉**(master 좌석·리뷰어 역할은 좌석 폴더 대상 아님 · 정상 복원 `cys restore` 경로 무변경) | — | health 전체 · cargo core · formation 42/42 |

## 2-A. 이종 검증 처리 (codex 1R REVISE 6건 · agy 1R ACCEPT)

| # | 지적 | 판정 | 처리 |
|---|---|---|---|
| 1 high | 신뢰 시드의 교체 직전 재대조가 원자적이지 않다(재대조~rename 사이 claude 저장 유실 · 결과는 seeded) | 수용(사실) | claude 가 잠금을 잡지 않아 코드로 닫을 수 없음 → 문서·이름을 "창 축소 · 원자 보장 아님"으로 정정 · 한계에 등재 · 기존 첫기동 시드도 같은 창 |
| 2 medium | python 이 `projects: null`·비객체 엔트리를 덮는다(Rust 는 거부·보존) | 수용 | python 키 부재/null 구분 · 시험 추가 |
| 3 medium | Rust 홈 판정이 `<HOME>/x/..` 를 홈으로 못 본다 | 수용 | `lexical_normalize` · 시험 추가 |
| 4 medium | 원장과 일치한 harness 알림 속 선언이 기계 유래로 먼저 접혀 스폰이 열린다 | 수용(설계 결함) | Rust·셸 둘 다 층0·층0-c 재확인 후에만 선언 경로 · 셸 3s(훅 예산 주석 갱신) · S5e · Rust 시험 |
| 5 medium | python 전체 NFD vs Rust 한글 전용 분해 | 수용 | python 을 Rust 산술 그대로 · 시험 추가 |
| 6 low | 실 claude 시험이 기동 실패도 통과시킬 수 있다 | 수용 | S4b 양성 표지 · S4c 판별력 |
| agy | ACCEPT · 지적 0 | 얕음 | 인용 줄번호 2개 중 1개가 무관 주석(레거시 :442) — 증거력 낮게 취급 |

### codex 2R (REVISE 7건 · 1R 처리의 부분 종료 지적)

| # | 지적 | 판정 | 처리 |
|---|---|---|---|
| 1 high | 원자성 문서가 "영향은 git 루트 좌석 한정"이라 과소 서술 — 교체 대상이 설정 전체라 다른 키도 유실 | 수용 | 두 모듈 문서 정정 · 한계에 등재(코드로 못 닫음) |
| 2 medium | python 되읽기 검증이 거부 형태를 '추가할 것 없음'으로 오판 | 수용 | rust 와 같이 거부도 확인 |
| 3 medium | Rust 정규화가 선행 `..` 를 지우고 루트의 `..` 를 남김 | 수용 | 이름만 pop · 루트 위 무시 · 선행 `..` 보존 |
| 4 medium | 셸 오너 경로(human)는 층0 재확인을 건너뛰어, 원장 밖 harness 알림 속 선언이 스폰 | **이관** | **이 티켓 이전부터 있던 셸·Rust 차이**(티켓 전 셸도 human harness 선언에 스폰했다 · Rust 는 대장 폴드가 막음). 오너 경로 동작 변경은 브리프 범위("억제 분기만 제거") 밖 → 【결정필요】로 master 에 상신 |
| 5 medium | 동등 한글 키가 여럿일 때 python 삽입 순서 vs rust 정렬 순서 | 수용 | python 정렬 순서 |
| 6 medium | S4c 가 첫 표지만 판별 | 수용 | 표지 전부 |
| 7 medium | python 임시 파일이 쓰기 후 chmod — 설정 전체가 잠시 0644 | 수용 | mkstemp(생성 시 0600) 후 원본 권한 |

부수 발견(자기 검수): ① 레거시 임무 미지정 주입문이 "여기 도달 = 오너 타이핑 판정"을 단언 — 억제 폐지로 거짓 → 판정값(MO_TOKEN) 관측 문안 ② 피닉스 fresh 경로에 그물이 없었다(뮤턴트 M10 생존) → `seat_fresh_cwd` 추출 + S6.

## 3. 설계 판단과 근거

### 3-1. 신뢰는 상속되는데 왜 시드까지 하나 — 실측
- 실측(Claude Code 2.1.272 · 격리 `CLAUDE_CONFIG_DIR`): 부모 폴더만 신뢰된 상태에서 `JH/workers/w1`·`JH/cso` 에서 띄우면 신뢰 창 없이 입력 화면에 도달한다. 대조군(신뢰 밖 폴더)은 창이 뜬다.
- 바이너리 판정 함수(jB): 현재 폴더에서 부모로 올라가며 `projects[조상].hasTrustDialogAccepted` 를 찾되 **git 저장소 루트에서 멈춘다**.
- 따라서 워커가 좌석 폴더에서 `git init` 하면 상속이 끊긴다 → master 판정(f12093fe)으로 상속 + 시드 이중. `test_seat_folders.py` S4 가 실 claude 로 이것을 잰다(시드 없는 git 좌석 = 창 뜸 · 시드된 git 좌석 = 창 0).

### 3-2. 두 구현 · 한 골든 표
- 편성·피닉스 경로는 python(`javis_seat.py`), `cys boot` 경로는 Rust(`src/seat.rs`)다. 규칙이 갈리면 경로마다 다른 폴더에서 좌석이 뜨므로 두 쪽 시험이 **같은 골든 표** `cysjavis-pack/templates/seat-layout.json` 을 읽는다.
- 신뢰 시드 계약은 기존 첫기동 시드(`pack::plan_first_run_seed`)를 그대로 쓴다: 부재 키만 · 다른 키 보존 · 모르는 형태 거부. 여기에 두 가지를 더했다: 교체 직전 파일 재대조(살아 있는 claude 세션과의 동시 쓰기) · 설정 파일이 없으면 만들지 않음.

### 3-3. master 좌석은 옮기지 않았다
설치기·신뢰 시드·피닉스 복원 경로가 전부 JarvisHome 을 가리킨다(브리프 판단 그대로).

### 3-4. `cys boot` 의 기준 폴더
부트는 데몬 감독자가 띄워 프로세스 cwd 가 마스터 폴더가 아닐 수 있다 → 기준 = `--cwd` → 살아 있는 master 좌석의 생성 cwd → 프로세스 cwd. 기준이 홈·루트면 좌석 폴더를 만들지 않는다(사용자 폴더 오염 방지 · 종전 동작).

### 3-5. 스폰 억제 폐지의 경계
- 레거시 셸: machine / 판정 불가 분기의 `exit 0`(무스폰)만 제거. 선언 유래 마커 `CYS_DECL_ORIGIN` 은 human 일 때만 export, 그 밖은 **unset**(상속값 누수 차단).
- Rust 훅: `declaration_spawn_origin` — 오너 선언 = `hook-human`, 기계 유래(`MachineOrigin`) 선언 = 빈 값, 층0·층0-c 는 종전대로 처리완료.
- 부서 자동 생성 봉인(2026-08-12 ⓑ)은 마커를 요구하므로 **유지된다**. 잔여 위험 = THREAT-MODEL §4-10-A.

## 4. 검증 (측정값)

측정 시각 2026-09-15 20:0x~20:3x · 이 작업 트리(`feat/seat-folders`). 커밋 직전 값이며, 괄호 안 "진행 중"은 【단계완료】 보고에서 확정한다.

| 축 | 결과 |
|---|---|
| `javis_seat.py self-test` | OK — 골든 16 · 신뢰 계획(null·비객체·한글 분해 키·비한글 분해형·정렬 순서) · 좌석 IO |
| 신설 `test_seat_folders.py` | PASS — S1 좌석 폴더·cwd · S2 CLAUDE.md · S3 신뢰 시드·실사용 프로필 무접촉 · S4 실 claude(git init 좌석: 시드 없음 = 신뢰 창 · 시드 = 창 0 + 다음 화면 표지) · S5a~e 억제 폐지·마커·층0 재확인 · S6 피닉스 fresh |
| Rust 신규 | `seat::` 6건 · `declaration_spawn_origin…` · `master_seat_cwd_from_rows…` 전건 ok |
| 기존 python | `test_formation.py` 42/42 · `test_role_bootstrap_hook.py` PASS · `test_pyseal_census.py` PYSEAL-CENSUS-OK |
| health | 1차 전체: 148 PASS / 1 FAIL / 1 SKIP — FAIL = H-PACK-TRACK-1(신규 팩 파일 미추적 → 명시 add 후 PASS) · SKIP = H-WIN-11(Windows CI 전용) · 2차 전체(codex 1R 수리 후): 148 PASS / 1 FAIL / 1 SKIP — FAIL = H-SECRET-1(Rust 시험 픽스처의 `/Users/…` 개인 경로 표기 8줄 → 중립 경로로 교체) · 최종 대상 재실행 H-SECRET-1·H-MISSION-1·H-PACK-TRACK-1 GREEN |
| cargo `-p cys-terminal` | 수리 전: lib 497 · cys 246 · cysd 959 · 실패 0 / 수리 후: lib 498 · cys 246 · cysd 959 · 실패 0 · 워크스페이스 전체는 `src-tauri` 빌드 스크립트가 `binaries/cysd-aarch64-apple-darwin` 리소스 부재로 시험 시작 전 실패(이 트리 환경 · 이 티켓 무관 패키지) |
| 뮤턴트(스냅샷 사본 · 라이브 트리 변이 0) | 1차 M1·M2·M5·M6·M7·M8·M9 KILLED · M3·M4 단독 SURVIVED(CLAUDE.md 보존 두 겹 — 겹침 M34 KILLED = 층 방어) · M10 1차 SURVIVED(그물 부재) → S6 신설 후 KILLED · M16(셸 층0 재확인 제거) KILLED · M11·M12·M14·M15(Rust) KILLED · M17(Rust 층0 재확인 제거) KILLED — 17종 중 생존은 M3·M4 단독(층 방어)뿐. ⚠마지막 스냅샷은 codex 2R 수리 **이전** 사본이다 — 2R 로 바뀐 줄(python 되읽기 검증·mkstemp·정렬 순서 · Rust 정규화)은 뮤턴트 재측정 대상에서 빠졌고, 해당 성질은 self-test·Rust 시험 단언으로만 잰다 |
| 이종 리뷰 | agy 1R ACCEPT(얕음) · codex 1R REVISE 6 → 전건 처리 · codex 2R REVISE 7 → 6 처리 · 1 이관(§2-A #4) |

### 4-x. 맥 로컬 흉내 스모크 (격리 데몬 · 2026-09-15 20:1x)
- 격리: 임시 HOME · 짧은 `/tmp/csf-<pid>.sock` · 임시 팩(저장소 `cysjavis-pack` 복제) · 임시 프로필 · `CYS_NO_AUTOSTART=1` · 이 작업 트리에서 빌드한 `cysd`/`cys`.
- 절차: 설치기 흉내로 master 좌석을 `cys new-surface --role master --cwd JarvisHome` 로 세우고 신뢰는 JarvisHome 에만 심음 → `cys boot`.
- 결과(`cys list` 실물):
  - `surface:1 role=master cwd=…/JarvisHome`
  - `surface:2 role=cso cwd=…/JarvisHome/cso`
  - `surface:3 role=worker cwd=…/JarvisHome/workers/w1`
- 트리: `JarvisHome/`(파일 0) · `JarvisHome/cso/CLAUDE.md` · `JarvisHome/workers/w1/CLAUDE.md` — 두 CLAUDE.md 가 역할(cso·worker)과 디렉티브(CSO_DIRECTIVE.md·WORKER_DIRECTIVE.md)를 채움.
- 신뢰 키: JarvisHome(설치기 흉내) + cso + workers/w1 셋 다 `true`.
- `cys boot` exit 78(첫기동 관문 보류): 좌석은 **폴더 신뢰 관문을 지나 그 다음 관문(Bypass 면책 창)** 에서 멈췄다 — 격리 프로필이라 면책 동의가 없어서다. 좌석 폴더에서 신뢰 창이 뜨지 않았다는 관측이다.
- 정리: 좌석 3 · 데몬 프로세스 그룹 종료 후 생존 0 · 소켓 제거. 실사용 프로필에 스모크 경로 문자열 0건(inode 변화는 살아 있는 claude 세션의 원자 쓰기 — 내용 대조로 확인).

## 5. 한계 · 잔여 (정직 고지)

- 피닉스 **정상 복원**(`cys restore` 전역 `--cwd`)은 좌석별 cwd 를 실을 수 없어 종전(master 폴더)대로 두었다. fresh 강등 경로만 좌석 폴더로 옮긴다. 새로 뜬 좌석은 좌석 폴더가 저장되므로 다음 복원부터는 저장 cwd 가 쓰인다.
- claude 가 먼저 그 폴더에서 떠서 `hasTrustDialogAccepted:false` 를 기록해 둔 경우, 시드는 기존 값을 보존하므로 덮지 않는다(그 폴더가 git 저장소가 되면 창이 뜬다).
- Windows 경로 표기(`/` 정규화 · `\\?\` 제거)는 코드상 처리했으나 **실기 미실측**.
- `worker` 와 `worker-1` 은 같은 폴더(`workers/w1/`)로 간다 — 두 역할이 동시에 있으면 폴더를 공유한다.
- agy 1R = ACCEPT · 지적 0 이지만 인용한 줄번호 2개 중 1개가 무관한 주석을 가리켰다 — 깊이가 얕은 판정으로 취급한다(증거력은 뮤턴트·실측이 진다).
