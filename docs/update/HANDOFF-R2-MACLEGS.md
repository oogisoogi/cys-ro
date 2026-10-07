# HANDOFF — TICKET=cysr-118-r2-maclegs-gate (R2 리허설 37642949667 맥·윈 레그 게이트)

좌석 = surface:1296(297) · cwd = ~/axdev/.wt/cys-118-maclegs · 가지 `fix/r2-maclegs` off `74476bbd` · 발주 master#8b64bf63 · 결정 #39a7a1e9(A · 좁힘) · #d2bdc18f(VERSIONINFO A)
비가역(실행 0): v1.1.8 태그 · merge/main push · draft · 시험 ref(만들지 않음 · 전체 리허설 미실행 = master 재태그 런을 실측 장으로)

## R2 런 37642949667 실측(태그 v1.1.8 → 74476bbd)
| 잡 | 결론 | 원인 | 처분 |
|---|---|---|---|
| build x86_64-apple-darwin | failure 15:21Z | IOReport 산출물 게이트(L970)가 macsign 게이트 없이 돌아 번들 없는 레그에서 「파일이 없다 · exit 2」 | 51bb4436 |
| build windows | failure 15:42Z | VERSIONINFO 게이트 「전부 .0」 기대 ↔ U1 R7 이 cys·cysd 4번째 마디 = release_seq(1) → 1.1.8.1 ≠ 1.1.8.0 | 8267b605 |
| build aarch64-apple-darwin | failure 15:37Z | phoenix 게이트 안 cysd 시험 1건 b3_status_polling_does_not_restat_the_identity_file(16회 폴링 실판독 1) — release.yml 밖 | 298 TICKET=cysr-118-r2-b3status(손대지 않음) |
| windows-health-gate | success | — | — |
| pack-artifacts · stamp | skipped(needs: build) | — | — |
- 산출물: `update-inputs-windows-x64`(295,668,018 B) 업로드됨(재료 수집 스텝 = VERSIONINFO 앞).

## 51bb4436 — IOReport 게이트 = 서명 레그에만 + 레인 게이트 토큰 전용 허용
- release.yml L970 `if: matrix.platform == 'macos-latest' && steps.macsign.outputs.enabled == 'true'`(번들 스텝 L903·Gatekeeper L1019 와 같은 게이트).
- ci-branch.yml 「팩 스위트 레인 대조」: 그 실행 줄은 MUST_RUN_TOKENS['release'] 필수 명령 → 조건 허용 필요. **ALLOWED_STEP_CONDITIONS 는 레인 전체에 걸린다**(조건 문자열만 대조) — 뮤턴트: 레인 전체 항목 + UI 회귀 스텝(`cd ui && bun test` · 필수 명령)에 같은 조건 = 게이트 rc 0(조용히 꺼짐 허용). ⇒ **MUST_RUN_TOKEN_CONDITIONS**(토큰 1 → 조건 1) 신설 · 필수 명령 루프가 그 토큰 스텝에만 허용 · 묵은 등재 경고 · 표의 토큰이 MUST_RUN 에 없으면 적색.
- 실측: 레인 게이트 rc 0 · lane-parity --strict 0 · --self-test 0 · 뮤턴트 3 적색(UI 필수 스텝에 같은 조건 · IOReport `if: false` · 다른 macsign 꼴 `!= 'false'`).

### 형제 스윕(build 잡 · 맥 전용 조건 · macsign 게이트 없음) — 판정 근거 1줄씩
| 줄 | 스텝 | 번들 산출물 읽음 | 판정 |
|---|---|---|---|
| 219 | src 모듈 선언 ↔ 추적 파일 | 아니오(저장소 파일) | 그대로 |
| 370 | phoenix host-level 게이트 | 아니오(cargo test · 소스) | 그대로 |
| 411 | todo 선언·유령집계 | 아니오(팩 시험) | 그대로 |
| 623 | CEO_TEMPLATE 재합성 | 아니오(gen --check) | 그대로 |
| 653·696 | 팩 검체 | 아니오(팩 시험) | 그대로 |
| 789 | 동봉 런타임 준비 | 아니오(번들 **입력**을 만든다) | 그대로 |
| 856 | 맥 번들 명령 별칭 시험 | 아니오(scripts/tests 파이썬) | 그대로 |
| 868·883 | 업데이터 자산 생성기·U3 스크립트 | 아니오(scripts/tests) | 그대로 |
| **970** | **IOReport 산출물 게이트** | **예(`$SRC/macos/cysr.app/Contents/MacOS/cysd`)** | **수리** |
| 1010 | 릴리스 게이트 회귀 그물 | 아니오(합성 픽스처 · 브리프 지정 유지) | 그대로 |
| 1221 | 릴리스 본문 설치 안내 | 아니오(macsign enabled 로 판정) | 그대로 |
| 1288 | 키체인 정리 | 아니오(`|| true`) | 그대로 |
- 윈도우 단독 배포 설계(L125-134 주석 · L813 프리플라이트 「맥 서명·공증·게이트·업로드를 건너뛴다 · 윈도우 단독 배포로 발행 가능」 · L1251 업로드 조건)와 일치 — 맥 레그는 시험만 돌고 산출물 게이트·업로드는 꺼진다.

## 8267b605 — Windows VERSIONINFO 게이트 = R7 반영
- 계약 원문: DESIGN-AUTOUPDATE-118.md:685 「R7 | 같은 판 번호 재빌드 · 윈 VERSIONINFO 같음 → NSIS 오라클 단락 | … VERSIONINFO 4번째 마디 = `release_seq` 안 U1 실측」 · build.rs:51 「윈 VERSIONINFO 4번째 마디(u16)에도 같은 값을 싣는다(아래 · R7)」 · build.rs:282 「VERSIONINFO 숫자 판 4번째 마디 = `release_seq`」 · HANDOFF-U1.md:51 ② 「VERSIONINFO 4번째 마디(스크래치 실측 포함)」.
- 기대: cys·cysd = `$v.$CYSR_RELEASE_SEQ`(정수 ≥1 재확인) · cys-app = `$v.0`(src-tauri/build.rs 4번째 마디 지정 없음 · NSIS 오라클 nsis-hooks.nsh:90-91 은 cys·cysd 만 읽음).
- 검증(pwsh · 게이트 스크립트 원문 + Get-Item 대역): R2 실값(seq 1 · .1/.1/.0) 통과 · 옛 .0 전부 적색 · seq 불일치(변수 2) 적색 · app 에 seq 적색.

### 「.0 전제」 형제 게이트 grep(VERSIONINFO·FilePrivatePart·FileVersion·getdllversion · workflows·scripts·nsh·build.rs)
| 자리 | 4번째 마디 비교 | seq 주입 | 판정 |
|---|---|---|---|
| release.yml:1190 VERSIONINFO 게이트 | 예 | 예(최상위 env CYSR_RELEASE_SEQ) | **수리 8267b605** |
| windows-build.yml:202 VERSIONINFO 게이트 | 예(`"$v.0"`) | **아니오**(이 워크플로에 CYSR_RELEASE_SEQ 없음 → 빌드 seq = 0 → 산출물 .0) | 지금 정합 · 잠복(이 워크플로에 seq 를 주입하는 날 적색) — 손대지 않음(release.yml 밖 · 필요 시 같은 꼴로) |
| windows-build.yml:922·1049 오라클 스탠드인 | 문자열 FileVersion 표시만(비교 아님) | — | 무관 |
| src-tauri/nsis-hooks.nsh:90-91 `!getdllversion /packed` ↔ 런타임 GetDLLVersion | 같은 원본에서 뽑은 상수와 비교(형식 자기정합) | — | 무관(build.rs:285 주석과 같은 판단) |
| scripts/tests/nsis-hook-compile/* | 합성 PE(임의 4마디) | — | 무관 |
| release-verify.py · scripts/update/* | VERSIONINFO 읽는 곳 0(grep) | — | 무관 |
