# MERGE-0.14.49-51-PLAN — 원작자 v0.14.49~51 편입 판정표 (1.1.10 · TICKET=cysr-1110-vendor)

> 가지 `rebase/v0.14.51` · 작업트리 `~/cys-terminal-src-wt/rebase-01451` · 워커 540(surface:1539) · 정본 규칙 = `~/axdev/master/CYS-UPDATE-POLICY.md` §0·§0-1·§0-2
> 기준 = 원작자 **발행 릴리스 태그** v0.14.50(`0a20e3ba`)·v0.14.51(`2deb095c`) — 로컬 태그 = `upstream` 태그와 커밋 일치 실측. `upstream/fix/0.14.52-integ` 등 가지는 기준 아님.
> 편입 전 `UPSTREAM_BASE` = v0.14.48(`ad9b0f90` · origin/main 과의 merge-base 와 일치) → 편입 후 **v0.14.51**.
> 방식 = `git merge --no-ff v0.14.51` 1회(직전 편입 cysr-1110-upstream 과 같은 방식). 가지 이름은 §0-2 2 의 `rebase/vX.Y.Z` 를 따랐으나, 우리 쪽 v0.14.48 이후 커밋이 1,378개(병합 포함)라 커밋별 rebase 는 하지 않았다 — 판정 단위는 아래 「변경 묶음」이다.
> push 0 · 태그 0 · 설치/교체 0.

## 0. 규모

| 항목 | 값 | 출처 |
|---|---|---|
| 원작자 커밋 | 176 (v0.14.48..v0.14.51) | `git log --oneline v0.14.48..v0.14.51 \| wc -l` |
| 원작자 변경 | 88 파일 · +17,899 / −855 | `git diff --stat v0.14.48 v0.14.51` |
| 병합 결과(우리 main 대비) | 81 파일 · +17,666 / −352 | `git diff --shortstat ba38b6aa^1 ba38b6aa` |
| 텍스트 충돌 | **26 파일 · 46 덩어리** | 병합 직후 `git diff --name-only --diff-filter=U` · 파일별 `<<<<<<<` 계수 |

## 1. 판정 기호

ⓐ 깨끗한 편입(자동 병합 · 손대지 않음) · ⓑ 충돌 해소(우리 커밋 우선 · 원작자 변경은 검토 편입) · ⓒ 재구현 · ⓓ 보안 경계 검토(네트워크·인증/OAuth·업데이터 키·팩 서명/소유권·상태 스키마·삭제 로직 → codex 1R) · ⓔ 제외(사유 + 박사님 게이트 — **이번 편입에서 0건**)

## 2. 변경 묶음별 판정

| # | 묶음 | 원작자 커밋 | 판정 | 내용 · 우리 쪽 처리 |
|---|---|---|---|---|
| G1 | 0.14.49 HUD 다리 — 윈 비UTF-8 로케일에서 구독 스레드 사망 수리 | 1791fc1a c8f611ec b78a58e9 2f40c8fa a3408d5f f4a9ccc1 4a8a867f 1b361169 fcf41fe0 bb9bb68a b1ef81d2 51b00d7a | ⓐ | javis_hud_bridge.py · 시험 · windows-build T5c · 릴리스 노트(docs/RELEASE_NOTES_0.14.49.md) 그대로 |
| G2 | F7 승인 저장소 단일 디코더 `decode_records_text` | 236f3d86 81f99cb5 | ⓑ ⓓ(상태 스키마 판독) | approval.rs 충돌 1 — 원작자 디코더 수용 + **우리 BOM 벗기기(1.1.7 A1-F1)를 디코더 안으로** 옮김 → 로더와 스케줄 은퇴 시드 검사가 같은 바이트를 같게 읽음 |
| G3 | F10-A/B hooks/ 드리프트 보고 · `pack-ownership` 안내 · `doctor --lanes` · pack-guard 안내 문장 | 48739eb0 edc3b722 1b1fa3aa a93d2ce9 82d94dbb c911ee21 1b5da27f | ⓐ ⓓ(팩 소유권) | 읽기 전용 보고(쓰기 0)·pack-guard.sh 안내 문장 +5줄. 자동 병합 |
| G4 | B-057 soul L0 이 `## ` 머리 전부 + 읽기 포인터 | a72cf169 1af015d1 764b7867 | ⓐ | inject-context.sh · 시험 |
| G5 | F5 제품 자체 %CPU 보고(보고 전용) | acad0348 488c499d 5950a210 9d1f8132 225f360f | ⓐ | javis_resource_gate.py · role-capability-gate.sh · 시험 하네스 |
| G6 | B-070 발행 파이프라인 한도(secret-scan `--all` 한도 실측 유도) | 7e3a1387 | ⓑ | run_bootstrap_health.py 충돌 2 — 원작자 한도 상수(624초) 수용 + **우리 「측정 실패 5형 exit 2」 검체와 H-BUNDLE-PERM-1 유지** · 결과 문장에 두 정보 모두 |
| G7 | 0.14.50 CI·문서(윈 F10 단계·스택 오버플로 측정·릴리스 노트) | ee920232 0a20e3ba 3a7f1b52 | ⓐ | windows-health/build 워크플로 · docs/RELEASE_NOTES_0.14.50.md |
| G8 | S1/S2 quiescing 표지(세대 결박·읽기만) | 21d51166 937248ab 5cd5e55c 61d531bb 8bcc2253 | ⓐ | governance.rs·handlers.rs 자동 병합 — **winqueue(541) 와 겹치는 파일** |
| G9 | **S8 휴지통** — 정리 작업이 지우지 않고 「오래됨」만 표시 · 삭제는 Control Center 휴지통에서 사람이 명령할 때만 · 미리보기 비동기 · 크기 캐시 원자 기록 · 윈 삭제는 `trash_win_validated` feature(기본 꺼짐) | 6cb142b5 e3b4898a 8290d3e3 7ed08ed6 f1c4afb6 48c8437b d2f83115 56ff0755 adc34ea0(→ 되돌림 9 → 복원 9: 9fc7b9ca…c4348987) 8211c199 3112e06c 4bb25d6b 875038f1 0b25c47e 8a457a37 9f2e19c9 da3f7612 27251d68 d8c0f1a1 72db4501 0656f8dc 5102506f eb8f7599 9bd04c66 f16cdc8c 0fdcd978 d6ce4660 650c2c5e aa4a8ac4 bc8439a6 6fb1b868 5f31073b ee67d72e 3510becf 8eb8518f 15be316f b6ef9f1f 729495ef 99adfc6c 66c6cc3c d518be11 6027a954 | ⓑ ⓓ(삭제 로직) | 충돌 4(index.html 완전 초기화 툴팁 · resetconfirm.ts · cys-dept reap 요약 · javis_org.py 2) — 툴팁·안내 = 원작자 문구(자동 소거 약속 삭제) + 우리 `cysr` 표기 · cys-dept = 우리 `HOLD=` 유지 + 원작자 `TRASH-OLD=` · javis_org = 우리 `expect_gen` 인자·rc=12 유지 + 원작자 `.producer` 표식·시험 · 휴지통 토스트 1곳은 우리 D4 #14(원문은 「자세히」 안쪽)로 고침 |
| G9-W | (발행 전 검토 · TICKET=cysr-1110-prerelease-review-b · master#4e61b71e Q1=B) S8 「reap 은 지우지 않는다」의 **윈도우 예외** | — | **ⓑ 우리 유지(원작자 계약 이탈)** | 사유 = 윈 회수 경로 0: 윈 1.1.10 은 `trash_win_validated` 꺼짐이라 앱 휴지통 삭제가 없고, S8 로 reap 의 14일 `rm -rf` 도 사라져 transcripts.db(부서당 최대 324MB)가 무한 누적된다. ⇒ 판정 정본 lib `trash_delete_supported`(데몬 `trash.rs delete_supported` 와 `cys build-info --json` 의 `trash_delete_supported` 가 같이 씀) · `cys-dept reap` = 윈도우 ∧ 그 칸이 true 아님(false·칸 없음 = 1.1.9 이하) 일 때만 옛 14일 정리(`TRASH-EXPIRE`) · 맥·리눅스·feature 켜진 윈 = S8 그대로(표시만). 화면·CLI·설명서·발행 노트 문장도 맥/윈 둘로(`TRASH_KEEP_NOTICE_WIN`). 시험 = `test_trash_old_marking.py` ⑤~⑧ · `build_info_shape` · `factory_reset_trash_notice_tests` · `resetconfirm.test.ts` |
| G10 | S5 carrier-B 생애(휴면 모듈 — 호출자 = 자기 시험뿐) | 43996144 e98b5de6 a596c424 c7d5294e fedcaf93(코드 주석 부분) 7a522ba7 1c3c3204 a857d075 | ⓐ | s5_escalation.rs 신설(경로 사용 0) |
| G11 | **S5 큐 막힘 경보 제거**(토스트·배너·알람 이력 · 억제 상태 삭제) + 설명서 서술 | 39442423 · a596c424/fedcaf93 의 USER-MANUAL 부분 | **ⓑ 우리 유지 · 표시 끄기는 G13 스위치** | master 결정(21:49 답 · A안): 원작자 제거는 받지 않는다 — 우리 starved 경보(1.1.8 X1 배치 · cys-117-exitedpane-b1) 보존. 큐 막힘 블록은 새 가드 싱크 `starvedNotice` 로 TOAST 축 스위치에 묶음. USER-MANUAL 은 우리 판 그대로(S5 서술 미수용) |
| G12 | S7 승인 결판 사유 기록 | 5f78378d … 96eb5f06 (17) | 해당 없음(순변화 0) | 원작자가 같은 태그 안에서 17커밋 전부 되돌림(61333c7b … 830d4424 · 17건) |
| G13 | **S10 TOAST 축** — 데몬 이벤트 출처의 사람 싱크(토스트·배너·사이드바 ⚠·탭 점·건수 배지·Feed 자동 전환·CC 푸터·부서 오류 행) + CLI 경보 산문 7곳을 끄는 스위치 | c9e84636 a708ba3d 3805fc94 e0661d8a e06477c3 1a4e4183 2deb095c | **ⓑ 구조 수용 · 스위치 false** | master 결정(A안): `alertquiet.ts` `ALERTS_QUIET=false` · `cys.rs` `ALERT_PROSE_QUIET=false`(원작자 true) = 우리 현재 화면 동작 유지. main.ts 충돌 10 — 우리 문구 함수(approvalRequestCopy 등) 유지 + 원작자 래퍼(daemonToast·daemonStickyToast·daemonOsBanner)로 호출 · 우리 데몬 출처 sticky 3곳(restore-retrying·role-takeover·perm-seat)도 래퍼로. 시험은 두 값 모두 녹(§4)  ★발행 전 검토(master#4e61b71e Q2=B): 원작자 R2 의 `--wait` 대기 항목 OS 배너(직접 호출)는 꺼진 토스트를 **대신하는** 면이라 `waitBannerReplacesToast()`(= `alertsQuiet("toast")`) 일 때만 — 우리 출하 값 false 에서는 1.1.9 와 같이 토스트만 |
| G14 | 지침·헌장 문서(주인님 조항 CEO 템플릿 상류화 · 생성기 fragment · 근거 주석 10블록 CHARTER-RATIONALE 이관 · delivery 조각 상한 · cso-rev 시험 · directives 제안 .new 파일) | bec69f49 a7bbe97a db397b8b 4e802ad9 6814a762 2652d84a 38d297d3 9247c0e3 83d32564 4bad39ca 8d3ebce4 b49da82f 2191f26b 62a9b792 89b6921d 3a7f0378 79fffa0b a94f16b9 (33288649 ↔ 0dd15b94 되돌림 쌍 = 순변화 0) | ⓑ | 충돌: CEO 머리(scripts/ceo_template_header.md) = 우리(말로 부서 만들기 · team-token 휴면 문장 없음) + 원작자 S8 reap 계약 문장(「오너 지시 2026-10-12」 → 「원작자 S8 · v0.14.51 편입」) → `gen_ceo_template.py` 재합성(`--check` GREEN · 99,423 B). `delivery.rs MAX_PARTS` = **우리 6000 유지**(우리 실측 1,006 단위 × 4 = 4,024 > 원작자 4,016). 지침 바이트 상한 = 원작자 재기준선(59,715/100,723/116,357 · 우리 실측 57,680/84,186/99,423 모두 이하). docs/proposals/directives-0.14.51/*.new 는 제안 문서일 뿐 적용 안 됨 |
| G15 | B-181 codex 어댑터 `--no-daemon` | 0b9bda64 | ⓐ | 팩 어댑터 |
| G16 | names 시험(jobId↔job_id 양쪽 소스 대조) | 26ed21d6 019f230e 8c413628 | ⓐ | src/job_name_binding_tests.rs |
| G17 | handlers b3 신원 캐시 검체 홈 이음매 | e9373a43 | ⓑ | 같은 `test_home::set` — 우리 주석(근거 수치) 유지 |
| G18 | 판번 올림 0.14.49·50·51 | 4aad8507 7690a2c1 3c29335a | 판번 규칙(§0-2 7) | 7파일 = 우리 1.1.9 유지 · productName `cysr` 유지 — 제외가 아니라 판번 규칙 적용 |
| G19 | S51 밀기 전 secret-scan 게이트(RELEASE.md) · CONTRIBUTING | (RELEASE.md 충돌 1) | ⓑ | 우리 「현행 정본」 절 유지 + 원작자 S51 게이트 문단을 그 절 머리에 인용(우리 발행에도 같은 규칙) |
| G20 | CI 목록(팩 시험 등재) | (ci-branch 3 · pack-release 2 · release 2 충돌) | ⓑ | 팩 시험 목록 = 합집합(원작자 test_secret_scan_limit·test_pack_guard_hooks_guidance·test_trash_old_marking·test_producer_marker + 우리 test_ctx_relay 외) · 우리 불사조 인코딩 스모크 유지(CEO 드리프트 게이트는 원작자가 옮긴 자리 하나만) · `PACK_MIN_BINARY` 1.1.8 유지 |

## 3. 충돌 26 파일 해소 원장

| 파일 | 덩어리 | 처리 |
|---|---|---|
| Cargo.toml · src-tauri/Cargo.toml · src-tauri/tauri.conf.json · ui/package.json · dist-win/cys.wxs · dist-win/cys-x64.wxs · Cargo.lock | 1·1·1·1·1·1·2 | 우리(1.1.9 · cysr) — G18. Cargo.toml 의 원작자 `[features] trash_win_validated`(기본 꺼짐)는 자동 병합으로 들어옴 |
| src/bin/cysd/approval.rs | 1 | G2 |
| src/bin/cysd/delivery.rs | 3 | 우리 6000 + 우리 주석 — G14 |
| src/bin/cysd/handlers.rs | 1 | 우리 — G17 |
| ui/src/main.ts | 10 | G13(1~10) · import 는 우리 + alertquiet 1줄(원작자 updatenotice·deptcreate import 는 우리가 지운 줄이라 미복원) · 작업중 계수 = 우리 `nodeWorking` + 원작자 `ccFailBadge` 가드 · 팀 만들기 안내 분기 = 우리(휴면) + 원작자 `--wait` 배너 1줄 |
| ui/src/style.css | 1 | 원작자(U2 칸 간격 · S8 미리보기 대기 줄) |
| ui/index.html · ui/src/resetconfirm.ts | 1·1 | G9(문구) · 화면 설정 단추 = 우리 |
| ui/src/starvednotice.test.ts | 1 | 우리(G11 — 두 starved 시험 파일 전체를 우리 판으로) |
| USER-MANUAL.md | 3 | 우리(G11 · 자동 병합된 S5 서술 7줄도 우리 판으로 되돌림) |
| docs/RELEASE.md | 1 | G19 |
| .github/workflows/ci-branch.yml · pack-release.yml · release.yml | 3·2·3 | G20 |
| cysjavis-pack/bin/cys-dept · javis_org.py | 1·2 | G9 |
| cysjavis-pack/bin/tests/run_bootstrap_health.py | 2 | G6 |
| cysjavis-pack/bin/tests/test_cso_directive_rev.py | 1 | 원작자 바이트 상한(G14) |
| scripts/ceo_template_header.md · cysjavis-pack/directives/CEO_TEMPLATE.md | 1·1 | G14(머리 해소 → 생성기 재합성) |

## 4. 병합 뒤 손본 것(시험 녹화 · 판정표 이행)

- `ui/src/alertquiet.ts`: 싱크 `starvedNotice` 추가(EXPECTED 1) · `ALERTS_QUIET=false`.
- `ui/src/main.ts`: queue.starved 블록·`dismissStarvedToast`/`forgetStarvedHead`/`focusStarvedSeat`·억제 맵 2개·종료 좌석 거둠 줄을 우리 판에서 복원(래퍼 경유) · 휴지통 토스트 원문 → raw.
- 시험: starvednotice 두 파일 샌드박스에 래퍼·가드 대역 추가 + 문자열 핀을 래퍼 이름으로 · alertcopy 핀 1 · toastaxis(원작자 862줄)를 우리 main.ts 에 맞춤(quiet 모드 = 원작자 값 true 주입 · 출하 값 false 핀 · 지문 재기준선).
- `src/bin/cys.rs`: `ALERT_PROSE_QUIET=false` + 출하 값 단언을 false 로.

## 5. ⓓ 보안 경계 — codex 1R 대상

G2(승인 저장소 판독) · G3(팩 소유권 보고) · G9(삭제 로직: trash.rs · factory_reset.rs · javis_org/cys-dept 격리 표식 · 앱 휴지통 명령 4종). 결과 = HANDOFF §codex.
