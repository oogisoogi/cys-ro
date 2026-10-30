# HANDOFF — cysr-1111-integrate (2026-10-30 · worker-2@surface:1731)

브리프 = `~/axdev/master/briefs/2026-10-30-cysr-1111-integrate.md`.

## 통합표 (int/1111)

| 후보 | 가지 머리 | 가지 CI 3종 | codex | int/1111 병합 | 남은 일 |
|---|---|---|---|---|---|
| ⓐ ctx-home-ancestor | 7f1ad03d | 녹(40974447919 · 40974448061 · 40974447927) | 2R ACCEPT | ecf29516 | 윈 실기 |
| ⓑ dept-chat-timeout | 6b12bc1a | 녹(40974451945 · 40974451904 · 40974451853) | 해당 없음(치명 4군 밖) | 6e4b6388 | 윈 실기 |
| ⓒ doctor-fleet | 1f6ca66d | 녹(40974453691 · 40974453756 · 40974453692) | R3 ACCEPT | 64128827 | T1-W 윈 번들 파이썬 설치 위치 |
| 675 wintask | 9cb4268d | 녹(40978986469 · 40978986523 · 40978986488) | R4 ACCEPT | 0e40368d | 박사님 노트북 실기(10-30 저녁) |
| 676 precedent | 19655dd6 | — | R11 ACCEPT | 이미 포함 | — |
| ①-b qstarved-ctrl | 91664b1b | — | — | 이미 포함 | — |
| ①-c worker-cap | 901d9542 | — | — | 이미 포함 | — |
| 677 hookslim | — | 적 | R3 REVISE | **제외**(1.1.11 밖 · 다음 판 후보) | — |

판번 커밋 = `459d0cca` chore(release) 1.1.10 → 1.1.11(8곳 · master#01649184 ②) — 게시 자리 실측: cys-ro 릴리스·초안·태그 1.1.11 없음 · 사이트 피드 stable·next = 1.1.10(release_seq 5).

## int/1111 CI

- 64128827: 녹 3종(40988376199 · 40988379035 · 40988382125).
- 0e40368d: windows-build 40995428941 녹 · windows-health 40995432362 녹 · ci-branch 40995426058 **적 1**(macos-rust-pack · cysd 3220/1 · `d7_prime_seat_cache_never_overwrites_a_tick_value` 측정 전제 대기 5초 초과 · 같은 cysd 코드의 64128827 런 ok · 로컬 5/5 ok).
- **459d0cca(최종): 녹 3종** — ci-branch 41001289944(5잡 녹 · cysd 3221/0 · d7_prime ok → 0e40368d 적 = 일시 적 확정) · windows-build 41001292926(아티팩트 cys-windows-x64-nsis 153,591,960 B · 만료 2027-01-28) · windows-health 41001295814 · 14:14 확인.

## 1.1.11 시험 판 산출물 (master#06d9f710 A·B · 설치·노트북 전달 = master)

| 판 | 경로 | 크기(B) | sha256 | 서명 |
|---|---|---|---|---|
| 윈 x64 NSIS | `~/cys-test-1111/win/cysr_1.1.11_x64-setup.exe` | 153,564,284 | `b588cd0655aed195f86f21d2b775b7e87aee51a7750069b7c3b10cc52472c3a7` | Authenticode 미서명 · windows-build 41001292926 아티팩트 cys-windows-x64-nsis(459d0cca) |
| 맥 arm64 zip | `~/cys-test-1111/mac/cysr-macos-arm64-v1.1.11.zip` | 218,681,547 | `35b060792623c43b8d269a055e13190f321a194bcf66eb64db0858a6663d906d` | cys-local 자체서명 · 공증 없음 · CDHash ac0a179160c4b5ab623ebefca34229497a1b6f73 |

- 각 폴더 `SHA256SUMS.txt`(`shasum -a 256 -c` OK).
- 맥 zip 풀어 실측: `codesign -dv` = Identifier com.cysjavis.terminal · arm64 thin · TeamIdentifier not set · Sealed Resources files=7982 · `-dvv` Authority=cys-local · `codesign --verify --deep --strict` OK · Info.plist 1.1.11 · 내장 빌드 id 459d0ccaa66f.20261030T0516Z.
- 맥 빌드 = `scripts/build-macos-local.sh aarch64 ~/cys-test-1111/mac/`(1111-int · 459d0cca · rc0 · 업데이터 서명키 cys-updater-A2 로 .app.tar.gz.sig 로컬 생성만 · 업로드 0).

## 1.1.12 후보 백로그

- [ ] `src/bin/cysd/handlers.rs` `d7_prime_seat_cache_never_overwrites_a_tick_value` — 대조군 좌석 「자손 0」 전제 대기 상한 5초가 CI 러너 부하에서 모자라 적(0e40368d ci-branch 40995426058 · 1회) — 상한·대기 방식 수리(master#7183a8ea).

## 로컬 환경 메모

- 이 맥에서 cysd `np_native_same_pid_exec…`(383:20) · `np_windows_real_candidate…`(475) 는 기준선에서도 적(CI 녹) — 환경 사유.
- `scripts/lane-parity-rehearsal.sh --self-test` 는 `sh` 로 돌리면 rc1(깨끗한 0e40368d 도 같다) · CI 처럼 `bash` 로 돌려야 한다.
