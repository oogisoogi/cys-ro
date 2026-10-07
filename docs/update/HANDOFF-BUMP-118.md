# HANDOFF — TICKET=cysr-118-version-bump (판번 1.1.7 → 1.1.8 · 절단 준비)

좌석 = surface:1296(297) · cwd = ~/axdev/.wt/cys-118-bump(이 좌석이 만듦 · `git worktree add -b release/bump-118 … 5040a3e9`) · 발주 master#5753c3b2(원장 일치 20:07) · 상한 1h
미러 push = `fix/bump-118` 만(이 티켓 한정 허락) · 태그·release.yml·draft·merge/v0.14.43 push = master 게이트(실행 0)

## TODO
- [x] 1. 직전 판 올림 커밋 찾기 → 범위 대조표
      해소 판정: 아래 §1 표 = dfcfe2e8 파일 목록과 이 커밋 파일 목록 일치
- [x] 2. SOT 8곳 1.1.7 → 1.1.8(수동 6 + `cargo update --workspace --offline` 로 Cargo.lock 2패키지)
      해소 판정: `sh scripts/version-check.sh` rc 0 · `v1.1.8` 인자 rc 0
- [x] 3. 검증 — test_version_sot_mutation · `cargo build --workspace --locked` · 판 문자열 핀 · bun
      해소 판정: 각 수치(§2)
- [ ] 4. 커밋 → 미러 fix/bump-118 push 1회 → 3런 success → 【확인요청】
      해소 판정: gh run list 3런

## §1 범위 대조표 — 직전 판 올림 = `dfcfe2e8`(2026-09-30 · 「판번 1.1.6 → 1.1.7 — 버전 SOT 8곳 · 1.1.6 범프 f243e04a 와 같은 자리」)
| 자리 | dfcfe2e8(1.1.6→1.1.7) | 이 커밋(1.1.7→1.1.8) |
|---|---|---|
| Cargo.toml `version` | ✓ | ✓ |
| src-tauri/Cargo.toml `version` | ✓ | ✓ |
| src-tauri/tauri.conf.json `"version"` | ✓ | ✓ |
| ui/package.json `"version"` | ✓ | ✓ |
| dist-win/cys.wxs `Product … Version` | ✓ | ✓ |
| dist-win/cys-x64.wxs `Product … Version` | ✓ | ✓ |
| Cargo.lock [cys-terminal] · [cys-app] | ✓(2줄) | ✓(2줄 · `cargo update --workspace --offline` = 작업공간 2패키지만 · 의존 변화 0) |
| 그 밖 | 0 | 0 |

**올림 관례 밖으로 판단한 1.1.7 표기(손대지 않음 · 근거)**:
- `docs/index.html` `<b id="ver">v1.1.7</b>` = 다운로드 페이지 **최신 발행 판** 표시 — 절단 커밋이 아니라 U4 6판 `3e6d3a9f`(10-07)가 넣었고, 1.1.8 이 발행되기 전에 v1.1.8 로 올리면 없는 자산을 가리킨다(publicdocs 「다운로드 버튼 폴백 = 표시 판의 실 자산」 시험이 태그·파일명을 그 판에 결속).
- `release.yml PACK_MIN_BINARY: '1.1.7'` · `pack-release.yml PACK_MIN_BINARY_OVERRIDE: '1.1.7'` = 팩 레인 최소 바이너리 정책(1.1.7 신설 표면 기준) — 판 올림과 독립(dfcfe2e8 도 무변경).
- 워크플로·cys-dept 주석의 「1.1.7 …」 = 이력 서술 · USER-MANUAL:1372 「1.1.7 이하에서 1.1.8 로 올 때」 = 갱신 경로 안내(현행).
- 시험 고정값의 "1.1.8"(test_javis_counsel·test_update_publish·cys.rs pack_precheck) = 픽스처 판 · 패키지 판과 무관.

## §2 검증 실측(2026-10-07 20:1x)
- `sh scripts/version-check.sh` = 8곳 일치 1.1.8 · rc 0.
- `sh scripts/version-check.sh v1.1.8` = 기대 판 일치 · 벤더 태그 동명 충돌 없음 · **rc 0(PATH 앞에 /usr/bin/git)**. ⚠좌석 PATH 의 첫 git = 앱 번들 git(https 헬퍼 없음)이면 「벤더 태그 조회 불가 → 실패」 rc 1 — 판 문제 아님 · 도구 문제(메모리 git-push-bundled-git-no-https 같은 원인). CI 러너는 시스템 git.
- `python3 scripts/tests/test_version_sot_mutation.py` = 양성 1 + 음성 8 + 추출 실패 2 + 벤더 5 = 16건 기대대로.
- `cargo build --workspace --locked` rc 0 — cys-app 빌드 스크립트는 사이드카 `src-tauri/binaries/cysd-<triple>` 실재를 요구 → ci-branch.yml:1552 와 같은 자리표시(touch · .gitignore 대상)로 섰다. `--locked` 통과 = Cargo.lock 이 판 올림과 맞다.
- `cys --version` = `cysr 1.1.8`.
- 판 문자열 핀: 패키지 판을 고정한 시험 없음(grep — 시험의 "1.1.8" 은 전부 픽스처 판) · ui bun 2674 pass / 71 skip / 0 fail.
