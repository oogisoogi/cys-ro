# cysr 1.1.11 발행 집행 체크리스트

★**발행 = 2026-11-07(토)**(박사님 11-01 20:4x · master#6ac5d378) · 범위 = 현 1.1.11 + 수리 3(팩 교체 atomic_swap · node-recover ^U · 복원 뒤 워커 교체 원인) · 새 기능 0 · 판번 1.1.11 그대로. ⛔현 seq 5 봉투가 **11-06 22:14 KST 에 먼저 만료**된다 → 그 전에 재게시(§5-4 · master).

초안 · TICKET=cysr-1111-publish-prep · 2026-10-30 · worker-rel(surface:1752) · 집행 = master(비가역 줄 ⛔) · U 서명 = 박사님 USB · 카톡 발송 = 박사님
견본 = `docs/release-1110/CHECKLIST-1.1.10-publish-2026-10-25.md`(§1~§4 명령은 그 문서를 1.1.11·seq 6 으로 치환) + 1.1.10 실제 집행 기록(`~/axdev/master/SESSION_STATE.md` = SS:n).
정본 순서 = `docs/RELEASE.md` · 자동 갱신 = `docs/update/HANDOFF-U3.md` §1 ③ · 롤백 = `docs/RELEASE-ROLLBACK.md`.
게이트 = `~/axdev/master/briefs/2026-10-27-cysr-1111-release-gate.md` · 통합표 = `~/axdev/master/HANDOFF-cysr-1111-integrate-2026-10-30.md` · 문안 초안 = 같은 폴더 `RELEASE-NOTES-1.1.11.draft.md` · `KAKAO-1111.draft.md`.

★**1.1.10 12커밋 병합 누락 → 발행 준비에서 적발·복구**(2026-10-30 21:5x · master#e9af822d): int/1111 의 v1.1.10 공통 조상이 3ce93329 라 459d0cca 에는 공개 태그 12커밋이 없었다 → rel/1.1.11 = 459d0cca 위 `git merge --no-ff v1.1.10` = **6690f9a8** · 표 = §H.
★**수용·미편입 2가지 복구**(2026-10-30 23:0x · master#8fd148bb · 1753 적발): fix/1111-backlog-misc 5ebc8d14(130c8079) · fix/1111-fable-fixes caeaab38(dc9f1de7) · 고유 9커밋 조상 · 충돌 1(문서 1줄 `~`/`$HOME` · 뜻 같음 → rel 쪽 유지).

실측 출발점(2026-10-30 21:5x · 읽기만):
- 공개 latest = v1.1.10(2026-10-23T13:08:45Z) · 보관소 `releases/5.json` 200 · **`releases/6.json` 404** · 저장소 변수 `CYSR_RELEASE_SEQ` = 5(→ 6 = master · 1-3) · stable/next 봉투 feed_rev **4** · rollout 100 · halt false.
- 현 봉투 expires_at = stable 1793970858 · next 1793970970 = 2026-11-06 경(값 그대로 · 서명 유효 최대 14일 L13) → 발행이 그 뒤로 밀리면 그 전에 seq 5 봉투 재게시(§5).
- 판번 = 1.1.11(8곳 · version-check rc 0) · `UPSTREAM_BASE` = `v0.14.52` · 두 레인 팩 하한 = `'1.1.11'`(release.yml:1521 · pack-release.yml:97).
- origin/main = 502741c7(= v1.1.10) · `git merge-base --is-ancestor origin/main 6690f9a8` = **참**(3-5 앞으로 감기 가능 · 병합 전 459d0cca 는 거짓이었다).

---

## A. 이번 판 고유 단계

### A-1. 원작자 v0.14.52 편입 — 표기·고지

| # | 할 것 | 근거 | 상태 |
|---|---|---|---|
| A-1-1 | `UPSTREAM_BASE` = `v0.14.52` 확인(태그 트리에서 `git show v1.1.11:UPSTREAM_BASE`) | bad42c73 | 값 실재 |
| A-1-2 | 태그 메시지 표기 `cysr v1.1.11 (based on cys 0.14.52 · rel/1.1.11)` | CYS-UPDATE-POLICY §0-2 7 · 1.1.10 꼴 | 권고 |
| A-1-3 | About 화면 「based on cys」 = 여전히 없음(`git grep -i 'based on cys' -- src src-tauri ui docs/RELEASE.md` 0건) → 노트 끝 줄 + 태그 메시지로 갈음 · About = 다음 판 후보 | 1.1.10 A-1-3 판단 그대로 | 고지 |

### A-2. 번들 실림(윈 재실기·맥 빌드 공통)

| # | 할 것 | 확인 줄 | 상태 |
|---|---|---|---|
| A-2-2 | **맥 zip 2종 = 태그 커밋에서 로컬 빌드** — 빌드 작업트리의 `git rev-parse HEAD` = 태그 커밋 · `git status --porcelain` 빈 줄 | 빌드 직전 2줄 출력 기록 | 집행 때 |
| A-2-3 | 맥 번들 실림: `strings <cysr.app>/Contents/MacOS/cys-app \| grep -c confirmNonce` ≥1 · `… \| grep -c confirm_nonce` ≥1 · ★이번 판 추가 = 복구 12커밋 실림: `… \| grep -c '상담소 끄기'` ≥1(arm64·x64 각각) | 1.1.10 A-2-3 + §H | 집행 때 |
| A-2-6 | 윈 교차 타입체크(맥): `sh scripts/win-typecheck.sh` | §I · 6690f9a8 rc 0 | 1-2 에서 |

### A-5. 봉투 = release_seq 6

| 칸 | 값 | 근거 |
|---|---|---|
| `CYSR_RELEASE_SEQ` | 5 → **6** | 보관소 5 200 · 6 404(21:5x 실측) |
| 본문 `--release-seq` | **6** | 같음 |
| 열거 폭 | 6 − 1 + 1 = 6 ≤ 256 | `--min-from-release-seq 1` 일 때(§6) |
| 봉투 feed_rev | 라이브 4 → 이번 게시 **5**(추론) | 3-6 출력 그대로 기록 |
| 인텔 맥 | seq 6 본문에 macos-x64 행 필수 — ⛔없으면 발행 중지 | 1.1.10 A-5 · 생성기 필수는 arm64·win 뿐 |

### A-6. 배운 것 — L1~L13 = 1.1.10 체크리스트 A-6 같은 번호 · 1.1.10 집행에서 더한 것

| # | 일어난 일 | 출처 | 반영 |
|---|---|---|---|
| L14 | 판번 커밋이 `docs/index.html` 7줄을 안 고쳤다(version-check 8곳 밖 · 시험도 못 잡음) | 459d0cca stat · 이 준비 | 1-0 에 이 준비 커밋으로 해소 |
| L15 | 통합 가지가 발행 태그를 조상으로 안 가져 공개 12커밋이 빠진 채 CI 녹 · 윈 실기 통과까지 갔다 | §H | §J BACKLOG(pre-tag-ci-check 에 is-ancestor) · 1-2 에 수동 줄 추가 |
| L16 | 윈 ⓑ(옛 판 → 새 판 갱신)에서만 역할 미복귀가 났다(rotate rc=24 · ⓐ 때는 없음) | SS:758·770 | 윈 재실기가 설치만이면 갱신 경로를 못 본다 → 0-3 |
| L17 | `--stamp` 는 윈 ⓑ 통과 뒤(seq 보호) · 순서 = R4 → 윈 ⓑ → R5 | SS:744 | 2-4 앞 |
| L18 | 「1.1.10 으로」 조사를 1.1.11 로 그대로 옮기면 틀린다 — 「십일」 = ㄹ 받침 → **「로」** | 한국어 조사 규칙 | §6 notes-ko |
| L19 | `test_phoenix_*.py` 는 태그 레인(release.yml:444)에서만 돈다 → 브랜치 CI 녹이어도 태그에서 처음 적이 된다(0.14.52 태그 런 39747056302 선례 · 이번 c6) | §I | 1-2c · §J |
| L20 | phoenix 를 Python 3.9(/usr/bin/python3)로 돌리면 `test_phoenix_c6_reap` 이 8/8 거짓 적 — 3.9 에서 `socket.timeout` ≠ `TimeoutError` 라 `events()` 가 빈손이 된다. 태그 레인 = 3.12(release.yml:259-261) · 3.14 = 26/26 | §K | 1-2c 명령에 3.10 이상 PATH |
| L22 | ★맥 자동 갱신이 기본 설치에서 apply 불가였다(1.1.8 부터 · 관측 0 인 채 세 판 공지) — 첫 관측 준비로 VM `--check` 를 읽고서야 드러났다 | §K-7 | 공개 문장 전부 제거 · 1.1.12 첫 항목 |
| L21 | `pre-tag-ci-check` rc 0 이어도 비차단 주석이 남는다 — 1-1 의 「`trash::` 실패 이름 0」은 감독자 축이 30분 시간 초과로 끊겨 `trash::` 줄 자체가 0(통과 0·실패 0)이면 빈 판정이다 | §K | 1-1 확인 줄을 읽을 때 분모를 같이 본다 |

---

## 0. 착수 전 — 막히면 그 자리에서 멈춤

| # | 할 것 | 확인 줄 | 상태 |
|---|---|---|---|
| 0-1 | 머리 확정 = rel/1.1.11(이 문서 커밋 뒤 · master 재승인 push 뒤 CI 3런 같은 SHA) | `git log --oneline -3 rel/1.1.11` | 대기 |
| 0-2 | 윈 실기 = **459d0cca 시험 판으로 통과**(10-30 20:2x · SS:1729 · ⓐ~ⓔ) | 원문 = 윈 master 회신 표 | 통과(병합 전 바이트) |
| 0-3 | **윈 재실기** = r2 키트 7ccab38c windows-build 41066772814(wintest-v1.1.11-20261030b · 상담소 단추 · 첫 안내 · reap · 초기화 문구 + 실 크롬) · r3 키트 = 최종 머리 windows-build 런(바뀐 부분만 · master#10b2531d) · 발신 = master. ⚠그 레인은 release_seq 0 = 자동 갱신 대상 밖(1.1.10 0-3). ⚠갱신 경로(ⓑ)는 L16 대상 — 윈 1.1.10 → 1.1.11 은 어차피 수동 1회라 **설치기 경로로 올리는 1회**가 사용자 경로와 같다(태그 draft setup.exe) · 시행 여부 = master | 재실기 회신 표 | 대기 |
| 0-4 | **hold 사유 실측 기록용 VM** `jarvis-observe-1111`(공개 1.1.10 · 로그인 0 · 좌석 0 · 자격증명 복사 0)을 지우지 않고 유지한다(master#3e3039b5 · 목적 변경 = 「자동 받기 관측」 → 「hold 사유 실측 기록」) | `cysr --version` · `build-info --json` `release_seq` 5 · §K-7 | 준비됨 |
| 0-5 | `release.yml` 자동 본문 = 1.1.10 에서 수리 · ⚠**윈 1.1.10 수동 1회는 말하지 않는다** → 3-2 에서 노트의 본문 초안으로 교체 판단 | 3-2 | 판단 대기 |
| 0-6 | 발행 노트·공지·카톡 초안 확정 — 【발행 전 확인】 처리 = §8 | 박사님·master 확정 | 대기 |
| 0-7 | `USER-MANUAL.md` v1.1.10→HEAD 변경 = `CYS_MAX_ACTIVE_WORKERS` 1행뿐 · ⚠컴퓨터 통제권·크롬 켜기 설명 0건(`grep 통제권` 0) | 설명서 보강 = master 판단(다음 판 가능) | 고지 |
| 0-8 | 팩 하한 = 두 레인 `'1.1.11'` · 본문 칸 같은 값(§6) | 시험 핀 `u8_pack_min_binary_two_lanes_match_and_cover_ack_only` · §I cargo-cys | 해소 |
| 0-9 | ⚠윈 1.1.10 사용자 안내 경로 = 앱 안 경로는 상담소 1:1(가입 기기)·아고라 공지뿐 · 피드·봉투·notes_ko 경로 0(wintask HANDOFF) → **공지·카톡이 유일한 대중 경로** · 카톡에서 맨 앞에 뒀다 | KAKAO-1111.draft.md | master 확인 |

## 1. 태그 전(가역)

| # | 명령 | 확인 줄 | 롤백 |
|---|---|---|---|
| 1-0 | 판번 8곳 = 459d0cca · `docs/index.html` 7줄 = 이 준비 커밋(L14) | `PATH=/usr/bin:$PATH sh scripts/version-check.sh v1.1.11` rc 0 · `grep -c '1\.1\.10' docs/index.html` = 0 · `Cargo.lock` flate2 = 1.1.9 그대로(우리 판번 아님) | 커밋 되돌림 |
| 1-1 | 가지 push(미러) → CI **dispatch** 3런(`rel/**` 는 push 트리거 밖 — ci-branch `['feat/**','fix/**']` · windows-build `['feat/windows-x64-dist','fix/**']` · windows-health `['feat/**','fix/**']` + tags `v*`): `for w in ci-branch.yml windows-build.yml windows-health.yml; do gh workflow run "$w" -R oogisoogi/cys-ro --ref rel/1.1.11; done` ≈45분 · ⚠push 전 `bash scripts/secret-scan.sh --all` rc 0(RELEASE.md:10-21 「밀기 전 게이트 — 전 ref 공통」) | 3런 success(같은 SHA · 1.1.9 = 38910007412 · 38910011842 · 38910016488 꼴) · windows-health 「cysd 감독자 축」(:580)은 continue-on-error → 로그의 `trash::` 실패 이름 0 을 따로 확인(WIN-FIELD V9·V11) | 가지만 — 무해 |
| 1-2 | `PATH=/usr/bin:$PATH sh scripts/version-check.sh v1.1.11` · `sh scripts/win-typecheck.sh`(A-2-6) · `python3 scripts/pre-tag-ci-check.py --wait 70`(**dispatch 뒤에** · L12) · `bash scripts/scan-pack-secrets.sh` · `python3 cysjavis-pack/bin/tests/run_bootstrap_health.py --only H-SECRET-1`(통합 때 GREEN 853파일 · 메모리 release-cut-gate-run-health-specimens-locally) | 다섯 다 rc 0(pre-tag rc 2 = 판정 불가 ≠ 통과 · 「58초 태그 금지」 RELEASE.md:171-230) | — |
| 1-2b | ★(L15 · 도구 수리 전 손 검사) `git fetch origin && git merge-base --is-ancestor v1.1.10 <태그 커밋> && git merge-base --is-ancestor origin/main <태그 커밋> && echo ANC-OK` | ANC-OK · 안 나오면 태그 금지 | — |
| 1-2c | ★(L19) 태그 레인 전용: `cargo build --bin cys --bin cysd` 뒤 `test_phoenix_*.py` 전건(release.yml:428-447 꼴 · 격리 HOME·TMPDIR) | 전건 rc 0 · 060cb75b = 26/26(§K) · 최종 머리 재실행 = §K 명령 | — |
| 1-3 | `gh variable set CYSR_RELEASE_SEQ -R oogisoogi/cys-ro --body 6`(1.1.9 실제 꼴 · T1 23:37:22) | `gh variable list -R oogisoogi/cys-ro` = 6 | 다시 set |

## 2. 태그(절단) → draft → 자동 갱신 재료

| # | 명령 | 확인 줄 | 롤백 |
|---|---|---|---|
| 2-1 ⛔ | `git tag -a v1.1.11 <태그 커밋> -m "cysr v1.1.11 (based on cys 0.14.52 · rel/1.1.11)"; git push origin refs/tags/v1.1.11`(1.1.9 꼴 · A-1-2) | draft-guard 「✅ … draft 없음 — 진행」 · windows-health-gate 「✅」 · seq 정수 스텝 초록 · 1.1.9 실측 ≈70분(23:39 → 00:5x) · draft 자산 6 | draft 삭제 가능 · **실패 태그 번호 재사용·태그 삭제 금지**(RELEASE-ROLLBACK.md:20-24) · 재시도 = Re-run failed jobs |
| 2-2 | R3 재료 — ★**x64 를 R4 전에 반드시**(L1): `export CYSR_RELEASE_SEQ=6` → `bash scripts/build-macos-local.sh aarch64 dist-seq6` **+** `bash scripts/build-macos-local.sh x86_64 dist-seq6`(A-2-2 의 HEAD·porcelain 2줄 먼저) → `bash scripts/update/collect-inputs.sh mac <arm64 zip> macos-arm64 r3s6/inputs` **+** `bash scripts/update/collect-inputs.sh mac <x64 zip> macos-x64 r3s6/inputs` → `gh run download <태그 런> -R oogisoogi/cys-ro -n update-inputs-windows-x64 -D r3s6/inputs/` · x64 의 Rosetta 경고 = 정적 처리(`ditto -x -k` + `codesign -dvv` · T1 08:08 · H7:70) | build-info `release_seq` = 6(셋 다) · `ls r3s6/inputs` 에 **arm64·x64·windows 세 묶음** — ⛔**x64 묶음 0건이면 발행 중지**(A-5 · master#c5547f8b 경고 ①) · 윈 설치기 sha ≠ 1.1.9 · A-2-3 strings 3종 | 산출물 삭제 · ⛔본문 보관(2-5) 뒤에는 재빌드 금지(설치기 sha 고정 · 메모리 project_cysr-release-archived-body-forbids-tag-rebuild) |
| 2-3 | R4: `python3 scripts/update/make-release-json.py --component cysr --release-seq 6 --version 1.1.11 --min-from-release-seq 1 --state-migration none --notes-ko 'cysr 1.1.11 로 새로 갱신되었습니다.' --key-id <U 키> --requires-min-binary-for-pack 1.1.11 --release-dir r3s6/release --asset macos-arm64=… --asset macos-x64=cysr-macos-x64-v1.1.11.zip --asset windows-x64=… --build-info macos-arm64=… --build-info macos-x64=… --build-info windows-x64=… --cdhash macos-arm64=… --cdhash macos-x64=… --a2-sig windows-x64=…sig --payload-dir windows-x64=r3s6/inputs/payload-windows-x64 --out r3s6/body/cysr-release-6.json`(1.1.9 실제 명령 T1 07:57:55 + x64 3칸) → `(set -a; . ~/.config/cysr-update/r2.env; set +a; python3 scripts/update/release-gate.py body --body r3s6/body/cysr-release-6.json --keyring cysjavis-pack/trusted-keys.json --archive-r2 cysr-update --expect-seq 6)` | rc 0 · ★**본문 자산 행을 손으로 센다 = 3(macos-arm64·macos-x64·windows-x64)** — ⛔**`macos-x64` 행이 없으면 서명(2-4)으로 넘어가지 말고 발행 중지**(A-5): `python3 -c "import json;print(sorted(json.load(open('r3s6/body/cysr-release-6.json'))['assets']))"`(키 이름은 본문 구조에 맞춰 · 1.1.9 는 게이트 rc 0 인데 행 2 였다) · ★명령의 칸 6개(seq·min-from·state-migration·notes-ko·min-binary-for-pack·자산 행)를 §6 표와 **한 칸씩 대조**해 기록(L2) | 다시 생성 |
| 2-4 | R5(박사님 USB 「NO NAME」 + U 비밀번호): `~/axdev/master/sign1111.sh`(1.1.9 `sign119.sh` 꼴 · 내용 = `bash scripts/update/sign-release.sh --body r3s6/body/cysr-release-6.json --media "/Volumes/NO NAME" --key "/Volumes/NO NAME/u.key" --out-dir r3s6/signed` · seq·경로만 바꿔 미리 만들어 둠) → master `minisign -V -p ~/axdev/master/keys-118/u.pub -m r3s6/signed/cysr-release-6.json -x …minisig` → `release-gate.py body … --sig … --expect-seq 6 --stamp` | 「✅ U 의식 통과」 · trusted comment seq=6 · gate rc 0 | 다시 서명 |
| 2-5 ⛔ | R6 보관소: `python3 scripts/update/publish-site.py archive --r2 cysr-update --file r3s6/signed/cysr-release-6.json --dry-run` → 같은 명령 `--live-check https://jarvis.godmeyou.kr` (1.1.9 실제 = 발행 **뒤** 08:26 · L7 · 순서는 §3 표대로) | `curl -fsS https://jarvis.godmeyou.kr/update/cysr/releases/6.json \| shasum -a 256` = 로컬 sha · `.minisig` 200 · 「라이브 대조 일치」 | 라이브 어긋남 = 자동 되돌림 rc 4(실패 rc 5 = 인쇄된 restore 1줄) · **보관소 불변 — 같은 seq 다른 바이트 불가** |

## 3. draft 정비 → 발행 — 순서 = 1.1.9 실제 순서(L7)

| # | 명령 | 확인 줄 | 롤백 |
|---|---|---|---|
| 3-1 | ★**순서 고정**(L3): ① 손대기 전 draft 사본 `~/cys-release-backup/v1.1.11-draft-before-r7/`(1.1.9 는 이 사본이 없고 `v1.1.9-assets/` 만 있었다) ② 맥 zip 2종 `gh release upload v1.1.11 …` ③ **구판 레인 tarball**: `bash scripts/make-darwin-updater-tarball.sh --app <arm64 cysr.app> --arch aarch64` · `… --arch x64`(A2 키 환경변수) → `gh release upload v1.1.11 cysr_{aarch64,x64}.app.tar.gz{,.sig} --clobber`(4종) ④ `python3 scripts/make-darwin-update-row.py --target darwin-aarch64 … --merge latest.json` · `--target darwin-x86_64 …` → `gh release upload … latest.json --clobber` ⑤ `python3 scripts/release-postprocess.py v1.1.11` → `… --apply` | 자산 14(1.1.9 공개 자산 = arm64·x64 zip · setup.exe/.sig/.zip · tar.gz 2 + .sig 2 · latest.json · pack 3종 · SHA256SUMS.txt) · ⚠`make-update-manifest.sh` 금지(윈 행 소실 · HANDOFF-118-r7:81) · zsh 는 `"${VAR}:…"` 중괄호 | 사본에서 복원 |
| 3-2 | GitHub 본문 교체 — ★**교체 확정**(master#bcc9056f ④ · #3e3039b5): 자동 본문 「1.1.8 이상은 자비스가 쉬는 시간에 새 판을 알아서 받고」(release.yml:1326)는 틀린 문장이다 → 노트 초안의 「GitHub 릴리스 본문」 절(윈·맥 줄 · 원작 판 0.14.52 표기 · A-1-3)로 발행 **뒤** 편집(1.1.9 실제 = 발행 뒤 08:54 `gh release edit v1.1.9 -R oogisoogi/cys-ro --notes-file …` · draft 에서 `--tag` 동반 편집의 tag_name 영향 = 미확인) · 먼저 옛 본문 사본 `gh release view v1.1.11 -R oogisoogi/cys-ro --json body -q .body > r7/body-before.txt` | `gh release view v1.1.11 -R oogisoogi/cys-ro --json tagName,isDraft,body` = tagName v1.1.11 · body 에 「Update 버튼」 0 · 「윈도우 단독 배포」 0 · 「알아서 받」 0(교체 뒤) · 3-8 뒤 `releases/latest/download/latest.json` 의 notes 도 같은 두 낱말 0 | `gh release edit v1.1.11 -R oogisoogi/cys-ro --notes-file r7/body-before.txt` |
| 3-3 | 검증 = CI dry-run 의 verify 잡(1.1.9 실제 · 로컬 `release-verify.py`·`release-gate.py assets` 실행 기록 0) — 로컬로도 돌리면: `python3 scripts/release-verify.py --version 1.1.11 --release-dir r7/reviewed --prev-tauri-conf prev-conf.json --prev-pack-keyring prev-keys.json` · `python3 scripts/update/release-gate.py assets --release-dir r7/reviewed --pack-manifest r7/reviewed/pack-manifest.json` | 「릴리스 검증 통과 — 자산 13종(+SHA256SUMS.txt) · 업데이터 4행 전부 서명 일치 · 맥 자산 포함」 · 팩 replay 단조 위반 = E1 최소 재서명 → SUMS 재생성(RELEASE.md:98-117) | — |
| 3-4 | `shasum -a 256 SHA256SUMS.txt`(3-1 ⑤ **뒤** 최종본 · 1.1.9 = 첫 dry-run 10febe52… → 최종 403a8be0…) = **release_bundle_sha256** | 기록 | — |
| 3-7 | dry-run: `gh workflow run release-publish.yml -R oogisoogi/cys-ro --ref main -f tag=v1.1.11 -f release_bundle_sha256=<3-4> -f confirm=PUBLISH`(1.1.9 = `--ref main` 으로 통함 · 그때 main = 6fddbffe) — 지금 main = 502741c7(같은 계열 · dry_run 입력 있음 추정) · ⛔**422 가 나면 멈춤**(dry_run 을 빼고 다시 보내기 금지 · 메모리 reference_cys-release-publish-dryrun-needs-branch-ref) | 「SHA256SUMS.txt 다이제스트: … (입력과 일치)」 · 「맥 자산: 포함」 · 「✅ dry-run 완료 — … 발행은 하지 않았다」 | 바뀌는 것 없음 |
| 3-8 ⛔ | 발행: 3-7 명령 + `-f dry_run=false` → 런이 **승인 대기**(L4 · environment `release-production` · 1.1.9 확정) → `gh api repos/oogisoogi/cys-ro/actions/runs/<RUN>/pending_deployments`(env id 조회 · 1.1.9 = 21524450364) → `gh api -X POST repos/oogisoogi/cys-ro/actions/runs/<RUN>/pending_deployments -F 'environment_ids[]=<id>' -f state=approved -f comment='cysr 1.1.11 발행'` · watch 는 600초를 넘을 수 있다 → 백그라운드 | 로그 「✅ 공개 발행 완료 — tag_name=v1.1.11 · isDraft=false」 · 공개 SUMS 13줄 OK · `releases/latest/download/latest.json` version 1.1.11 · 행 4 · `setup.exe.sig` 200 | ★**`docs/RELEASE-ROLLBACK.md` 를 따른다**(ADV4 M2 · 1755 수리 · halt 봉투 먼저 · 수동 재설치) — 서명 봉투 갱신기는 `latest` 되돌림으로 유입이 멈추지 않는다 · draft 되돌림 명령은 그 문서 절차 안에서만 · 삭제 = 최후·오너 지시만 |
| 2-5 ⛔ | (발행 직후) 보관소 게시 — §2 의 2-5 명령 | 2-5 확인 줄 | 2-5 |
| 3-5 ⛔ | main 이동 — ★**이번엔 앞으로 감기**: `502741c7`(현 origin/main = v1.1.10)가 태그 후보의 조상(10-30 실측 `git merge-base --is-ancestor 502741c7 6690f9a8` = 참 · 복구 병합 덕) → cherry-pick·강제 push 불요. 집행 직전 재측: `git fetch origin && git merge-base --is-ancestor origin/main v1.1.11 && echo FF-OK` → 보존 가지 `git push origin 502741c7:refs/heads/archive/main-pre-1111-<발행일>` → `NEW=$(git rev-parse v1.1.11^{commit}); git push origin "${NEW}:refs/heads/main"`(강제 아님 · 중괄호 · L5) | 불변식 「main = 최신 발행 태그 커밋 + CI 전용 패치」 · `gh workflow list -R oogisoogi/cys-ro` 에 refresh-feed active · main 트리 `.github/workflows/refresh-feed.yml:66` `SITE: ${{ vars.CYS_FEED_FETCH_SITE \|\| …}}` 줄 | 보존 가지로: `git push --force-with-lease=main:${NEW} origin 502741c7:refs/heads/main` · FF-OK 가 안 나오면(누가 main 에 새 커밋) **멈춤** |
| 3-6 | 봉투 재료(보관소 6 선행): `for ch in stable next; do gh workflow run refresh-feed.yml -R oogisoogi/cys-ro --ref main -f component=cysr -f channel=$ch -f release_seq=6 -f rollout_pct=100 -f halt=false -f first=false; done`(1.1.9 실제 명령 원문 T1 08:27:20 · seq 만 5) → `gh run download <run> -R oogisoogi/cys-ro -D r3s6/env/<run>` | 「Verify the NEW envelope」 초록 · 아티팩트 `envelope-cysr-stable`·`-next` · **feed_rev 값을 출력 그대로 기록**(A-5 · 추론 4) | 게시 전 — 무해 |
| 3-9 ⛔ | 봉투 게시(stable·next 각각 · 먼저 `--dry-run`): `python3 scripts/update/publish-site.py envelope --r2 cysr-update --file r3s6/env/<run>/envelope-cysr-<ch>/env.json --cys <1.1.11 cys 바이너리> --dry-run` → 같은 명령 `--live-check https://jarvis.godmeyou.kr` | 「update-verify[…] 출발 seq 1,2,3,4,5,6 전부 허용 판정」 줄에 ★**macos-arm64 · macos-x64 · windows-x64 세 대상이 다 나오는지** — ⛔macos-x64 가 없으면 `--live-check` 로 넘어가지 말고 멈춤(1.1.9 는 macos-x64 가 없는데도 경고가 없었다 · L1) · 「라이브 대조 일치」 · `for f in cysr/stable.json cysr/stable.json.minisig cysr/next.json cysr/next.json.minisig; do printf '%s ' "$f"; curl -fsS "https://jarvis.godmeyou.kr/update/$f" \| shasum -a 256 \| cut -c1-64; done` = 아티팩트 sha 4 · VM `jarvis-observe-1111`(0-4)에서 `cysr self-update --check --json` = ★**`decision="hold"` 예상**(feed verdict = apply · 발견 정상 · `gates.first_hold` = N6(VM 전원) · N5·N4 동반 · §K-7) — 값을 그대로 기록한다 · ⚠hold 는 실패가 아니다 | live-check 어긋남 = 자동 되돌림 rc 4/5 · 같은 rev 다른 내용 재게시 금지 · 비상 = refresh-feed `-f halt=true` → 게시(선례 미확인) · 이미 받은 기기는 못 되돌림 = 더 높은 판으로만(폐기문 = 사건 때만 R-RITUAL.md) |

## 4. 발행 뒤(설치기·사이트·알림)

| # | 할 것 | 확인 줄 | 롤백 |
|---|---|---|---|
| 4-1 ⛔ | 설치기 핀 1.1.10 → 1.1.11(판·크기·sha256·CDHash 를 **발행 자산에서 다시 재서**) — 1.1.9 실제 = habitat `r8/publish-20261017` 143b821(설치기 0.3.40 → 0.3.41) · 라이브 핀 `bootstrap.sh:147` `CYS_FORK_VERSION="1.1.9"` · `bootstrap.ps1:141` `$CysVersion = '1.1.9'` → 공개 jarvis-install main 33447f8 → 16f67c4 · 이번 설치기 판 = **0.3.43** 차례(한 발행에 한 판 · H7:64-72) → `PUBLISH_CONFIRM=yes bash tools/publish-snapshot.sh --src . --dest ~/axdev/jarvis-install --push --terms-check tests/public-terms-check.sh --terms-list …` | 「SNAPSHOT-OK · 적중 0 · 삭제 (없음)」 · 핀 시험(맥·인텔·윈 · 1.1.9 = 17·0 / 11·0 / 12·0) · 함정(H7:64-72): 대상 clone origin = 공개 URL · 원격 git `PATH=/opt/homebrew/bin:$PATH` · x64 는 정적 검사만 · `.DS_Store` 지운 뒤 재실행 · 소요 1.1.9 = 기술 20분 + 라이브 5분 | 이전 핀 커밋으로 |
| 4-2 ⛔ | 사이트(ai-jarvis): 공지 `site/notice/<발행일>/` · 손댈 자리 7(1.1.9 SITE-119 꼴: ①새 공지 index.html ②`site/notice/index.html` 목록 맨 위 ③`site/index.html` 머리 띠 ④`site/get/index.html` 머리 띠 — **끝 문단 링크만** `#install` 꼴이라 같은 치환을 두 파일에 쓰면 한쪽 0건 ⑤`site/devlog/index.html` 새 항목 + 시기 머리 ⑥`site/test/check-render.py` PAGES 한 줄 ⑦「최신 판」 숫자 스윕 `grep -rnI '1\.1\.[0-9]' site \| grep -v '^site/install/'` ⑧★자동 갱신 문장 스윕 `grep -rnI '알아서 받\|쉬는 시간' site` — 대문·/get/ 「1.1.8이나 1.1.9를 쓰고 계시면 … 알아서 받아 둡니다」 교체 · 처분 §K-7) → `bash site/test/gate.sh` → `bash web/build-web.sh` → 실렌더 6조합(대문·설치하기·공지 × 390/1440) → `cd web && wrangler deploy` · `bash web-install/deploy.sh --go`(npm ci 먼저) · 세미나 묶음 f63bcd1 포함(§K-10) · ★**site/1111 가지를 site/hub 에 병합하고 push**(L11 — 안 하면 다음 배포가 옛 판으로 돌아감) | GATE=PASS · `/notice/<발행일>/` 200 · 띠 2곳 1.1.11 · 「최신 = 1.1.9」 잔존 0(첫 조회 엣지 HIT 가능 · 20초 뒤 재측) · 라이브↔빌드 대조 때 Cloudflare 주입 2조각 제외 · `/install/next` 404(실기 때 썼으면 삭제) · 공개 저장소 checks [사이트] 대조 붉은 창 0(H7:72) | 이전 커밋 재배포 |
| 4-3 | 카톡 문안 `docs/release-1111/KAKAO-1111.draft.md` → 라이브 공지와 대조 → 박사님 전달(발송 = 박사님) · ★보낸 **최종본을 그대로 파일로 커밋**(L10) | 링크 200 · 공지 앵커 | — |
| 4-4 | 자동 받기 관측 = **이번 판 해당 없음**(근거 `src/update/sched.rs:151-154`·`:217-229` · §K-7 · master#3e3039b5) · 공지·카톡에 자동 갱신 문장 0 | 3-9 의 hold 값 기록으로 갈음 | — |

## 5. 미확인 모음(집행 전 master 확정)

1. 관측용 맥 기기 지정(0-4). 2. 윈 재실기 범위 · 갱신 경로 1회 시행 여부(0-3). 3. 윈 1.1.9 기기의 복구기 문제 여부(노트 받는 방법 줄). 4. ⛔봉투 만료 11-06 22:14 KST · 발행 11-07 = 만료 뒤 → 만료 전에 seq 5 봉투 재게시 필요 · 집행 = master(10-19 주간 발화는 재료만 만들고 게시 안 함 · 10-26 09:20 launchd 주간 발화 = dispatch 만 · 게시는 사람 손). 5. `state_migration`(§6). 6. 캐너리(R8) 시행 여부. 7. 자동 본문 교체(0-5). 8. §G ⚠ 항목 처분. 9. ⛔`test_phoenix_c6_reap.py` 처분(§I) — 안 고치면 태그 레인 적 · 실패 태그 번호는 재사용 불가(RELEASE-ROLLBACK.md:20-24).

## 6. 본문 칸·팩 하한 1.1.11 권고표(2026-10-30 실측)

| 칸 | 1.1.10 실제 값 | 1.1.11 권고 | 근거 | 확신 |
|---|---|---|---|---|
| `--release-seq` | 5 | **6** | A-5 | High |
| `--min-from-release-seq` | 1(체크리스트 권고 · 실제 본문 대조 = R4 때) | **1** | 계약 `0 ≤ 값 < release_seq` · 열거 폭 6 ≤ 256 | Med |
| `--state-migration` | none | **none**(master#bcc9056f ①) | 전수 감사 = §K-1 · 개명·삭제·기존 타입 변경 0 · 새 파일·새 키 가산뿐(1.1.10 과 같은 기준) · 값 분기 코드 = `breaking` 하나뿐 | High(코드 판독 · VM 왕복 1회) |
| `--notes-ko` | `'cysr 1.1.10 으로 새로 갱신되었습니다.'` | **`'cysr 1.1.11 로 새로 갱신되었습니다.'`** | ≤80자 · 금지 어휘 0 · 조사 L18 | High |
| `--requires-min-binary-for-pack` | 1.1.10 | **1.1.11** | 두 레인과 같은 값 · 빈 값 = 발행 거부 · 본문↔매니페스트 대조 게이트 없음 → 2-3 손 대조 | High |
| `PACK_MIN_BINARY` = `PACK_MIN_BINARY_OVERRIDE` | 1.1.10 | **1.1.11**(459d0cca 에 있음) | release.yml:1521 · pack-release.yml:97 | High |
| 자산 행 | arm64 · x64 · win | **셋** — ⛔x64 없으면 발행 중지 | A-5 | High |

## 7. 맥 교체(발행 뒤 · master 집행 · 워커 무접촉)

꼴 = `~/axdev/master/reports/cysapp-1110-replace-2026-10-23/`(PLAN.md · COMPARE.md · atomic-swap.sh · canary.sh · rollback.sh · seats.py · staging 측정 · pack-plan dry) · 브리프 꼴 = `~/axdev/master/briefs/2026-10-23-cysapp-1110-replace-prep.md` · 정책 = `~/axdev/master/CYS-UPDATE-POLICY.md` §0(포크 빌드만 · 벤더 설치기·앱 안 Update 금지 · 백업 · ditto · canary).

| # | 할 것 | 확인 줄 |
|---|---|---|
| 7-1 | 재료 = **발행 자산 바이트 그대로**(`cysr-macos-arm64-v1.1.11.zip` · release_seq 6) · ⛔`~/cys-test-1111/mac` 시험 판 금지(seq 미배정 · 459d0cca = 복구 12커밋 없음) · ⛔재빌드 금지 | sha256 = 발행 SUMS · CDHash 기록 |
| 7-2 | prep 티켓: 1110 스크립트 3종 복사 → 상수 교체(OLD_VER 1.1.10 · PIN_VER 1.1.11 · PIN_SEQ 6 · PIN_CDHASH · ZIP·ZIP_SHA · OLD_KEEP) · diff = COMPARE.md | DRY=1 atomic-swap = PRE 전건 |
| 7-3 | staging 측정 + staging CLI `pack-plan`(쓰기 0) | staging-measure-1111.txt · pack-plan-1111-dry.txt |
| 7-4 | 실행 시각 = 작업 좌석 0 · 백업 · 교체 · canary(.pending-restore 없음 · .pack-version 1.1.11 · pack.prev 잔재 · 3역할+상주 부활 · 중복 cso 0) · 게이트 §3 맥 칸(~/.claude 팩 훅 0 · 개인 훅 10 보존은 hook-slim 제외로 해당 없음) | `cys --version` 1.1.11 · 번들 CDHash = 릴리스 zip CDHash · 1.1.10 교체 선례 canary 전건 |
| 7-5 | 롤백 1줄 = rollback.sh · 옛 번들 보존 | PLAN |

## 8. 【발행 전 확인】 남은 목록(2026-10-30)

| # | 자리 | 무엇을 보면 닫히나 | 언제·누가 | 지금 |
|---|---|---|---|---|
| N1 | 노트 받는 방법 첫 줄 · 카톡 ① | (닫힘) 윈·맥 통일 문장에 흡수 | master#3e3039b5 | ☑ |
| N2 · K② | 노트 받는 방법 맥 줄 | (닫힘) 자동 문장 제거 · 윈·맥 통일 | master#3e3039b5 | ☑ |
| N3 · K③ | 인텔 맥 | seq 6 x64 행(2-3) | R4 · master | ☐ |
| N4 · K④ | 컴퓨터 맡기기 절 | 실 크롬 실기(§G ⚠) = r7-0~7(§K-9) · 맥 = r7-4(master · 박사님 기기 앞) | master | ☐ |
| N5 | 윈도우 줄별 근거 | 1.1.11 윈 실기 표 칸 대조 | master | ☐ |
| K⑤ | 카톡 3줄 순서 | 라이브 공지 | 공지 배포 뒤 | ☐ |

## G. 발행 게이트 증거 대조표(게이트 브리프 §2~§5 · 2026-10-30 실측 · 있음/없음)

「기록 없음」 = 지정 문서·SESSION_STATE·TODO 에서 찾지 못했다는 뜻이다(수행되지 않았다는 증명이 아니다 · 검색어 함께 적음).

| 게이트 항목 | 판정 | 근거(커밋·런·파일) |
|---|---|---|
| 공통 — 정본 게이트 master 스냅샷 재실행 | **없음(6690f9a8 기준)** · 워커 로컬 전체 = §I | master msv 재실행 대기 |
| 공통 — 뮤턴트 | 묶음별 있음 · 복구 병합 자체는 새 코드 0 | cu 20/20 · precedent 119/119 · wintask WT1~5 |
| 공통 — 이종 적대 R1+ | 있음(묶음별) | 통합표: ⓐ 2R · ⓒ R3 · 675 R4 · 676 R11 ACCEPT · ⓑ = 치명 4군 밖 |
| vendor-01452 | 있음 | bad42c73 · HANDOFF-cysr-1111-vendor-01452 · r3 수용 · CI 포함 |
| test-hygiene · adv-fixes | 있음 | abc137c0 · HANDOFF-cysr-1111-adv-fixes |
| cu-1111 · cu-1111-win-fix | 있음 | ae41322c codex R3 · 6d8d4468 윈 r3 통과 |
| cu-1111-precedent — 코드·디렉티브 +≤400B | 있음 | 19655dd6 · 커밋 제목 +395B |
| cu-1111-precedent — **실 크롬 실기(맥·윈 · 크롬 꺼진 채/켜진 채)** | ⚠**기록 없음** · 새 설계 = r7-0~7(§K-9 · master#c110b17a) · 옛 탭 복원·경고 칸은 도구가 크롬을 닫지 않아 없어졌다 · 옛 r2 목록(master#1be35b1b)·r4·r5·r6 = 이력 | SS:1419 「§15 실기 = 절단 전 묶음으로 이월」 · TODO:235 ⑥ 미체크 · 윈 실기 ⓐ~ⓔ 에 크롬 칸 없음(검색어 chrome-enable · 크롬 재시작 · §15) |
| hook-slim 677 | **해당 없음(제외)** | 통합표 |
| 윈 복구기 675 | 있음 | 9cb4268d · R4 ACCEPT · 윈 실기 ⓐ 기준선 4·refusal 0 |
| master-send 배선 | 있음 · TODO:87 칸은 미체크 | SS:1166 격리 하네스 3/3·1/1 · 후속 판정기 SS:1178 |
| §3 맥 실기 | 발행 뒤(§7) | 재빌드 금지 판정 SS:1751 |
| §3 윈 실기 | 통과(459d0cca) · **병합 뒤 재확인 대기** | SS:1729 · 0-3 |
| §3 깨끗한 기기 새 설치 | **있음(060cb75b 시험 빌드 · 로그인 직전까지)** · 1.1.11 설치기 핀 판은 발행 뒤 | §K-4 |
| §4 통합 3자 적대 검토(전체 diff · codex·Fable·agy) | 있음 | `~/cys-terminal-src-wt/1111-adv4` 0c8b5ab2 ADV4-FINDINGS.md · blocking B1·B2 처분 = master |
| §4 발견 처분표 | 있음 | 같은 파일 |
| 태그 레인 전용 phoenix 시험 | **있음 — 060cb75b 26/26**(c6 수리 67cd1370 포함 · Python 3.14) · 최종 머리 재실행 대기 | §K |
| §5 절단 범위 동결 · 롤백 판(1.1.10 봉투 유지) | 집행 때 | 2-1 · 3-9 |
| 윈 이상 2(RunLevel 재등록 · preflight --fix 백업 없음) | 1.1.12 BACKLOG(§J) · 발행 차단 아님 = master 판정 | TODO:83 |

## H. 1.1.10 12커밋 복구 대조(master#e9af822d ② · 같은 grep 계수)

| 파일 | 지표 | v1.1.10 | 459d0cca | 6690f9a8 |
|---|---|---:|---:|---:|
| ui/src/counsel.ts | 상담소 켜기 | 2 | 0 | 2 |
| ui/src/counsel.ts | 지금은 보내지 않습니다 | 1 | 0 | 1 |
| ui/src/main.ts | 상담소 끄기 | 2 | 0 | 2 |
| src-tauri/src/counsel.rs | `fn ` | 73 | 65 | 73 |
| src-tauri/src/main.rs | counsel | 7 | 4 | 7 |
| cysjavis-pack/bin/javis_counsel.py | installer_version | 2 | 1 | 2 |
| cysjavis-pack/bin/javis_counsel.py | invalid_day | 2 | 0 | 2 |
| cysjavis-pack/bin/javis_counsel.py | refused | 19 | 18 | 19 |
| cysjavis-pack/bin/javis_counsel.py | notice_seen | 7 | 0 | 7 |
| cysjavis-pack/bin/javis_counsel.py | auto-set | 3 | 0 | 3 |
| cysjavis-pack/bin/cys-dept | TRASH-EXPIRE | 0 | 3 | 0 |
| ui/src/resetconfirm.ts | 저절로 지워지지 않습니다 | 1 | 0 | 1 |
| ui/src/resetconfirm.ts | 14일 | 1 | 2 | 1 |
| src/lib.rs | 14일 | 1 | 1 | 1 |
| src/bin/cys.rs | 저절로 정리 | 2 | 1 | 2 |
| USER-MANUAL.md | 상담소 끄기 | 2 | 0 | 2 |

파일 바이트: `javis_counsel.py` · `counsel.rs` · `counsel.ts` · `resetconfirm.ts` · `test_javis_counsel.py` = v1.1.10 과 동일(diff 0) · `cys-dept` 차이 = int 쪽 `boot_lock_winner` 추가 24줄(삭제 갈래 아님 · `rm -rf "$_td"` 0건).
3e89de97 핀 대조 = §I(cargo-lib · cysd · bun · test_pyseal_census).

## I. 로컬 정본 게이트(dc9f1de7)

실행 = 23:05~23:49 · 격리(가짜 HOME · `CYS_*` 해제 · 운영 파일 무접촉 · `JAVIS_ROOT`·`CYS_PROBE_RUNS` 시험별 · 태그 레인과 같은 PHOENIX 변수).

| 게이트 | 6690f9a8(1차) | dc9f1de7 |
|---|---|---|
| version-check · lane strict · lane self-test | rc 0 | rc 0 |
| scan-pack-secrets · secret-scan --all · H-SECRET-1 | rc 0 | rc 0(1895파일 clean) |
| test_release_trigger_split(draft-guard · test_24 포함) | — | 17 OK |
| ui bun test · tsc · win-typecheck | 3307 pass · 0 fail · rc 0 · rc 0 | 같음(0 fail · rc 0 · rc 0) |
| F1 `f1_cycle_idle_reads_physical_rows_of_a_wrapped_composer`(cys) | — | 1 passed |
| F2 `list_maps_a_live_and_a_dead_producer_pid_to_running_and_interrupted`(cysd) | — | 1 passed |
| cargo --lib | 1133/0 | 1133/0 |
| cargo --bin cys | 735/0 | 736/0(`--test-threads=1` = CI 형식 · F1 시험 1 추가분) |
| cargo --bin cysd 직렬 | 3222/0 | 3222/0 |
| cargo -p cys-app --bins 직렬 | 337/0 | 337/0 |
| 건강성 전체 | 167/2/1 | 167/2/1 · 적 ID·사유 1차와 diff 0 = H-CLT-1·2(이 맥 설치본 경로 · wintask HANDOFF 기록과 같음) |
| 팩 py 전수 199 | 환경 맞춘 뒤 c6 1 | 196 녹 · 적 3 = 환경 2(TMPDIR 을 홈 아래로 옮긴 탓 · 기본 TMPDIR 재실행 OK) + test_hook_r34(시간 경계 플레이크 · 부하 12 에서 2회 중 1회 · 1.1.10 통합 때도 기록) |
| 태그 레인 phoenix 27종 | c6 적 | 27 녹(c6 = 수리 시험 67cd1370 1/1 · 분포는 아래) |

- caeaab38 CI 적 2건 정체: windows-build secret-scan 2 = HANDOFF 2파일 개인 경로(int-winq2:25 · test-hygiene:38) · ci-branch boot-health-full = **H-SECRET-1 1건**(런 39834404344 · pass 167 fail 1 · 같은 뿌리) → rel 쪽은 26759e7b 에서 이미 고쳐져 dc9f1de7 = 0건 · 추가 수리 커밋 불필요. H-CLT-1·2 와는 다른 실패다.
- cargo --bin cys 를 `--test-threads=1` 없이 돌리면 `a3_strip_hook_digits…` 가 기본 2MB 스택을 넘친다(dc9f1de7 3/3 · 4MB 이상 통과 · wintask HANDOFF 기록과 같은 시험) · CI·태그 레인 형식(`--test-threads=1`)은 통과.

### 태그 레인 시험 `test_phoenix_c6_reap.py` — 수리 끝(TICKET=cysr-1111-c6-reap)

| 대상 | 결과 |
|---|---|
| 459d0cca · bad42c73 · 6690f9a8 원 시험 | 적 7/7 · line 147(`restored` 대기) |
| 원작자 v0.14.52 원 시험 | 13/13 통과(대조군 12 + 1) |
| 수리 시험(67cd1370 · 병렬 3묶음) | 9/12 · 적 3 = 전부 line 150(데몬 첫 응답 30초) · 묶음 B 와 같은 초에 동시 발생 |
| **수리 시험 직렬(10-31 00:0x)** | **13/13 통과**(36~48초) → line 150 = 병렬 산물 |
| 주차 대기 없는 변형(묶음 B · 병렬) | 9/12 · 같은 line 150 · 통과 9회 전부 순서 = queue.parked → surface.exited → 새 좌석 → queue.inherited · line 168 재현 0 |

판독: line 147 = 원작자 전제(`restored_queue`) ↔ 우리 D7⑵ 주차(`state.rs:8379` 주석 · 잠정 판정 S1). 수리 = 단언을 `queue.parked` + `queue.inherited` 로 교체. line 168 1회 적 = 미재현 · 후보 = `state.rs:8362` exited 표시 뒤 최대 1초 주차 지연(제품 경합 가능성 · 미입증). line 150 = 병렬 산물(직렬 13/13 · 두 묶음 동시 발생). 태그 전 1-2c 로 최종 머리에서 phoenix 전건 재확인.

## K. 태그 전 게이트 판정(TICKET=cysr-1111-relprep · 2026-10-31 · worker-relprep · 아래 표 = 0fde41c6 수치 · ⚠태그 머리 아님)

⛔「태그 = 0fde41c6 고정」(master#8d598191)은 윈 r4 1번 실패로 무효(master#c26704d3). 계획(master#415438c7) = rel/1.1.11 ← 57bce92e · 90a372d2 병합 끝(a431e8a3 · c79011b9) → 최종 머리에서 §K-9 재실행 · r7 실기 → 태그. 아래 표는 그 재실행의 대조 기준이다.

| 항목 | 결과 | 근거 |
|---|---|---|
| 1-2b | **ANC-OK**(v1.1.10 ∧ origin/main 둘 다 조상) | `git fetch` 뒤 0fde41c6 |
| 1-2c phoenix | **26/26 rc 0** · Python 3.14.7 · 내 시험 데몬 잔재 0 | e306568d(제품 코드 = 0fde41c6 · 문서 1파일 차이) · 격리 HOME·TMPDIR · CYS_* 해제 · 060cb75b 도 26/26 |
| pre-tag | **rc 0**(토큰 경로) · 비차단 주석 = §K-8 | 3런 41158073931 · 41158076438 · 41158078742 전부 success(060cb75b = 41103104106 · 41103108864 · 41103113724) |
| 로컬 게이트 | `cargo test --bin cys -- --test-threads=1` 736/0/1무시 · lib job_exit 6/0 · win-typecheck 오류 0 · lane-parity --strict rc 0 · secret-scan --all clean 1909파일 | 0fde41c6 · 게이트 기준 = CI·release.yml 형식(master#e6c18df7) |
| 윈 실 프로세스 | `tests/win_job_exit.rs` 6/0 | windows-health 41158078742 · 첫 실행 |
| release 스택 | 세 명령 `native-exit=0x00000000 overflow=no` · 060cb75b 런과 차이 0 · 수용(master#8d598191) | §K-8 · ⚠넘침 여부만 · 여유 미측정(§J) |
| §6 state-migration | **none 권고** | §K-1 |
| 깨끗한 기기(맥) | **통과**(로그인 직전까지) | §K-4 |

### K-1. `--state-migration` 감사(v1.1.10..060cb75b)

판정 = **none**(master#bcc9056f ① · 이 프로젝트 기준 「가산뿐이면 none」 · 브리프 · §6 · 1.1.10 선례). 글자 뜻으로는 `additive` 도 맞고, v1.1.8·1.1.9·1.1.10 클라이언트 모두 세 값을 받는다(`feed.rs` 대조). 그래도 none 인 까닭 = 값에 따라 갈리는 코드는 `breaking` 하나뿐이고(feed.rs:671), `additive` 는 공개된 적이 없는 값이라 얻는 것 없이 처음 쓰는 값이 된다.

| 분류 | 항목 | 옛 → 새 | 새 → 옛(1.1.10) | 위험 |
|---|---|---|---|---|
| 새 파일 | `queue-write-holds.json`(state.rs:1544) · `submit-held.json`(:1560) · `submit-held-undelivered.jsonl`(handlers.rs:4058) · `writer-journal.jsonl`(state.rs:1593) | 없으면 빈 값 | 무시 · 보류 항목은 `queue-state.json` 에 남아 처음부터 재배달될 수 있음 | 낮음~중(수동 내림만) |
| 새 파일 | `.kept-pane-records.jsonl`(cys.rs:1292) · `ready-withheld*.json`(javis_lane.py:156) · `win-task-refusal-*.json`(win_task.rs:330) · `round/_intake/*.json`(javis_intake.py:70) | 없으면 정상 | 무시 | 낮음 |
| 새 폴더 | `computer-control/`(팩) · 초기화 목록 28→29(factory_reset.rs:19) | 새 폴더 | 폴더는 무시되나 옛 팩에 원복 도구가 없다 | 중(켠 뒤 수동 내림) |
| 미배선 | `pending-requests.json`(schema 5 · deny_unknown_fields) | `PendingStore::open` 호출 = 시험뿐 | 파일이 안 생김 | 없음 |
| 새 키 | `.pack-reinject-pending.json` `unknown`(cys.rs:26840) · 갱신 state.json `restore_partial`·`session_unverified`(realops.rs:1270-1280) · 세대 manifest `canonical_cards` | 없으면 기본값 | 무시 · 옛 판이 다시 쓰면 `unknown` 소실 | 낮음 |
| 뜻 변경 | 워커 상한 기본 8→0(state.rs:3761 · 저장값 없음 · 명시 env 존중 · 파싱 불가 값은 8 → 무제한) · 훅 timeout 5→10(하한 판정) · 기본 배경색·글꼴(저장값 우선) · 세대 GC 레인 풀 · plist 사용자 env 보존 | 저장 형식 변경 없음 | 내리면 옛 기본으로 복귀 · plist env 재기록 때 소실 | 낮음 |
| 저널 | S3/S4 순서(journal.rs:82·118 · 구조체·상태 이름·crc 입력 동일) · 옛 저널이 QUIESCED·DRAINED 어디에 멈췄어도 새 판 = ReleaseAndDefer(journal.rs:453) | 재개 없이 보류 정리 | 복구 규칙 동일 · 정비 모드 없는 DRAINED 를 옛 `release` 가 무해하게 처리하는지 = **미확인** | 낮음 |
| 개명·삭제 | 0건 | — | — | — |

찾은 방법(재현용): serde derive 타입 전수 두 판 비교(v1.1.10 102개 변경 0·삭제 0·새 타입 66) · `deny_unknown_fields` 추가 26곳 = 전부 v1.1.10 에 없는 타입(대상 이름별 `git grep` 재측) · `git diff --diff-filter=DR` 0 · `ui/src` localStorage 호출 변경 0 · 파일명 문자열 두 판 비교.
실기(§K-4 VM): 1.1.10 → 1.1.11 교체 기동 정상 · 1.1.11 → 1.1.10 내림도 `submit-held.json` 을 안고 정상 기동. ⚠그 실기는 좌석 1개·큐 0 이다(보류 항목 재배달은 재지 않았다).
미확인: 윈도우 런타임 · `javis_computer_control` 기록 키 전수 · 큐가 찬 상태의 왕복.
곁가지 발견: `.kept-pane-records.jsonl` 은 `factory_reset.rs` 목록에 없어 공장 초기화 뒤에도 남는다(§J).

### K-2. 【발행 전 확인】 §8 판정

| # | 판정 | 무엇이 있어야 닫히나 |
|---|---|---|
| N1 | **닫힘** — `src/update/win_task.rs` blob 이 v1.1.8·v1.1.9·v1.1.10 동일(b13d35233a · 플래그 6) · 기기 실측 0 · 「1.1.8 이상」(master#bcc9056f ②)은 윈·맥 통일 문장에 흡수 | — |
| N2 · K② | **닫힘** — 자동 문장 제거(§K-7) | — |
| N3 · K③ | 불가 | seq 6 본문 자산 행 3(2-3) · 맥 x64 빌드 |
| N4 · K④ | 불가 | r7-0~7(§K-9) |
| N5 | 불가 | 윈 r3·r4 회신 표 칸 대조 |
| K⑤ | 불가 | 라이브 공지 배포 뒤 |

### K-3. 미확인 §5 판정

| # | 항목 | 판정 / 필요한 것 |
|---|---|---|
| 1 | 관측 VM | `jarvis-observe-1111` · 목적 = hold 사유 실측 기록(§K-7) · 자동 받기 관측 대상 없음 |
| 2 | 윈 재실기 범위 | r3 진행 중 · 윈 master 회신 필요 · 갱신 경로 1회 시행 = master |
| 3 | 윈 1.1.9 복구기 | K-2 N1 = 코드로 같음 |
| 4 | 봉투 만료 | 실측 stable expires_at 1793970858 = **2026-11-06 22:14 KST** · ⛔발행 11-07 이면 만료 뒤 → 그 전에 재게시(§5-4) |
| 5 | state_migration | **none 확정**(master#bcc9056f ①) |
| 6 | 캐너리(R8) | **미시행 · rollout 100 으로 바로**(master#bcc9056f · 근거 = halt 스위치·`docs/RELEASE-ROLLBACK.md` 준비됨 · 1.1.10 선례 · 자동 갱신이 게이트에서 보류라 봉투로 유입되는 기기도 없다) |
| 7 | 자동 본문 교체(0-5) | **교체 확정** — release.yml:1326 문장은 윈·맥 모두 틀렸다(§K-7) · 발행 뒤 3-2 절차 · 문장 = 노트 내부 본문 초안 |
| 8 | §G ⚠ | 깨끗한 기기·phoenix 해소 · 실 크롬 실기만 남음(N4) |
| 9 | `test_phoenix_c6_reap.py` | 해소(K 표) |

실측 재확인(06:4x): 보관소 `releases/6.json` 404 · `CYSR_RELEASE_SEQ` 5 · stable feed_rev 4 · rollout 100 · halt false · latest = v1.1.10.

### K-4. 깨끗한 기기(맥 · tart 복제본 relprep-1031-a · 원본 jarvis-clean-vanilla 불변 · 복제본 삭제 완료)

| 단계 | 결과 |
|---|---|
| 기준선 | macOS 26.6.2 arm64 · 앱 = Safari·Utilities · `~/.cys`·`~/.claude` 없음 · CLT 없음 · `CRED_ABSENT` · 키체인 claude/anthropic/cys/github 적중 0 |
| 설치 한 줄(공개 그대로 · 설치기 0.3.43 · 핀 1.1.10) | [1/10]·[2/10] 통과(클로드 2.1.308) · **21초에 [3/10] 로그인 입력 대기 도달**(06:36:33 → bootstrap.log 21:36:54Z) · 막힘 0 · 진단 코드 0 |
| 전송 레버 | `JARVIS_NO_PROGRESS=1` · `JARVIS_HELP_API_URL=http://127.0.0.1:9`(시험이 운영 기록·도움 사례로 안 나가게) |
| [5/10] 대역(로그인 뒤 단계라 손으로 같은 순서) | 공개 zip 14초 · 크기·sha256·CDHash = 핀 3개 일치 · ditto → xattr → codesign strict 통과 → 기동 |
| 1.1.10 기동 | 앱 · cysd · 첫 안내 · cysr 창 안 `claude` = 로그인 방법 선택 화면 |
| 1.1.11(060cb75b · cys-local · 시험 전용 · sha d8d4e0f0… 218,749,527B) 교체 | `cys --version` 1.1.11 · 데몬 build_id 060cb75b · 팩 1.1.10 → 1.1.11 · `init-pack` 신판 항목 1건 추가 · 로그인 방법 선택 화면 도달 · 로그인 0 |
| 1.1.10 내림 | 정상 기동 · 팩은 1.1.11 로 남는다(내림이 팩을 되돌리지 않음) |
| 뒷정리 | `CRED_ABSENT` 재확인 · 정상 종료 → 삭제 · 원본 disk.img mtime 9/6 그대로 |

⚠닫히지 않은 것: ① 이 실기는 **설치기가 1.1.11 을 받는 경로가 아니다**(핀 1.1.10 · 1.1.11 설치기 핀은 발행 뒤 4-1) ② [5/10] 이후는 로그인이 필요해 설치기 본체로는 재지 않았다 ③ 시험 빌드는 `-dirty`(문서 변경분) · seq 미배정 ④ 맥 전용 · 인텔 미측정.
관측 2: ⓐ 앱이 켜진 채 데몬만 바뀌면 상단 「엔진」 라벨이 옛 판을 유지한다 — 내 교체 스크립트가 데몬 작업을 내리지 않아 옛 데몬에 잠깐 붙은 것으로 추정(`left=3` · 앱만 다시 열면 맞다) · 발행 차단 아님 ⓑ 설치 안 된 CLT 안내가 첫 실행 경고로 뜨는 것은 설계대로.

### K-7. 맥 자동 갱신 = 기본 설치에서 apply 불가(master#3e3039b5 결정 A · 전문 = 인박스 155275줄 2026-10-31T07:42:16+0900 【경고】【결정필요】)

| 근거 | 내용 |
|---|---|
| `src/update/sched.rs:151-154` | `may_fire_within`: `every_minutes` 잡 = 무조건 true |
| `:217-229` | 표식 없음·bulk:true 주기 잡 → `bulk_within_48h` · bulk:false 주기 잡 → `nonbulk_within_60m` · publish:true/없음 주기 잡 → `publish_within_48h` |
| 기본 `schedule.json` | `agora-counsel` publish:true · every 30 / 내장 잡 대부분 표식 없음 / `self-update-check` 자신 = bulk:false · every 360 → N4 두 갈래·N5 ⓒ 상시 참 |
| `check.rs decide` | Verdict::Apply ∧ 게이트 불통과 = hold · 러너 진행 없음 |
| 판 범위 | v1.1.8·1.1.9·1.1.10·060cb75b 동일(세 파일 diff 0) → 이미 깔린 판은 1.1.11 을 자동으로 못 받는다 · 1.1.11 도 같은 코드 |
| 한계 | VM 에 후보 판이 없어 지금 decision = uptodate(hold 는 코드 판정 · 게이트 보류는 실측) · `schedule.json` 을 손으로 고친 기기는 예외일 수 있다 · 자동 갱신이 일어난 기록은 못 찾았다(일어나지 않았다는 증명은 아님) |

**이미 나간 문장(1.1.10 까지 · 정정 판단 = master)**: 라이브 `/notice/2026-10-23/` · 대문 「자비스가 쉬는 시간에 새 판을 알아서 받습니다」 · 대문·`/get/` 「1.1.8이나 1.1.9를 쓰고 계시면 … 알아서 받아 둡니다」 · 공지 목록 제목 「자비스 새 판 1.1.8 · 다음 판부터는 자비스가 알아서 받습니다」 · v1.1.10 GitHub 본문 「1.1.8 이상은 … 알아서 받고」 · 저장소 README·USER-MANUAL·`docs/index.html` 은 태그 전에 고쳤다(master#c8df5271 · README.en·ARCHITECTURE·RELEASE·`publicdocs.test.ts` 고정값 포함 · 다음 판에서 게이트를 고치면 되돌린다) · 옛 공지 = 그대로 · 대문·`/get/` = 4-2 ⑧ · `release.yml:1326` = 3-2 교체(다음 판에서 수리).

**VM `jarvis-observe-1111`**(새 복제본 · 공개 1.1.10 · sha·CDHash 핀 일치 · 로그인 0 · 자격증명 복사 0 · 앱 켜 둠 · 접속 admin 기본 계정): 점검 경로는 로그인 없이 돈다 — `self-update --auto --spawn` rc 0 · 러너 사본 기동 · 복구기 LaunchAgent 등록(N14 통과) · 주기 = 6시간 + 지터 0~45분 · `src/update/auto.rs`·`check.rs`·`gates.rs`·`feed.rs` 에 로그인 참조 0.
잡 자가 발화 기록 = `self-update-check` last_fired 1793400048(07:40:48 KST · 손 실행 07:42 보다 앞) · ⚠result 칸은 빈 값이라 그 발화가 끝까지 돌았는지는 미확인 · 손 실행 뒤 러너 종료 · `state.json` = `{}`(후보 없음).

| 시각(10-31) | 좌석 | os_idle | decision | 보류 게이트 |
|---|---|---|---|---|
| 07:40(첫 값) | 일반 pane 1 | 49초 | uptodate | N14 · N6 · N5 · N4 · N1 · N2 |
| 07:42(복구기 등록 뒤) | pane 1 | 194초 | uptodate | N6 · N5 · N4 · N1 · N2 |
| 07:58(좌석 0) | 0 | 1146초 | uptodate | N6 · N5 · N4 · N2 |
| 08:00(N2 창 지남) | 0 | 1238초 | uptodate | **N6 · N5 · N4** |

읽는 법: ⓐ N5·N4 = 모든 기본 설치 공통 · 영구 ⓑ N6 = VM 전용(`pmset -g adapter` = 「No adapter attached.」 · `pmset -g ps` 는 AC 라 읽지만 코드는 adapter 만 본다 · 배터리 없음) · 영구 ⓒ N1 = 일반 pane 은 자기신고가 없어 영구 보류 — 앱이 켜진 기기에서 pane 이 하나라도 있으면 막힌다(pane 을 닫아 0 으로 뒀다 · 재부팅·앱 재시작 때 pane 이 다시 생기면 N1 이 다시 나타난다). 발행 뒤 3-9 에서 feed verdict = apply 인데 decision = hold 가 나오는지 이 VM 으로 기록한다.

### K-5. CI 비차단 주석(060cb75b · rc 0 인데 남은 것)

| 주석 | 판정 |
|---|---|
| windows-build `T3-3 FAIL`(env 주입 스텁 · send rc=1) | 459d0cca · 7ccab38c 와 같음 · 이번 머리에서 생긴 것 아님 · 원인 미조사 |
| windows-health 감독자 축 30분 시간 초과 | 7ccab38c 와 같은 30분 |
| ⚠1-1 「`trash::` 실패 이름 0」 | 로그에 `trash::` 시험 줄 자체가 0 — 통과도 실패도 없는 **빈 판정**이다(L21) · 이 확인 줄만으로 윈 trash 시험이 돌았다고 말할 수 없다 |

### K-6. 최종 머리 재실행 묶음(`<SHA>` 만 넣는다 · 쓰기 0)

```
# 1-2b
git fetch origin && git merge-base --is-ancestor v1.1.10 <SHA> && git merge-base --is-ancestor origin/main <SHA> && echo ANC-OK
# 1-2c (bash · 머리 체크아웃 뒤 · 약 3분 · rc = 적 개수)
bash -c 'set -u; cd ~/cys-terminal-src-wt/rel-1111 || exit 9; for v in $(env | grep -oE "^(CYS|CMUX|JAVIS)_[A-Za-z0-9_]*"); do unset "$v"; done; rm -f target/debug/cys target/debug/cysd; PATH="$HOME/.cargo/bin:$PATH" cargo build --bin cys --bin cysd >/dev/null 2>&1 || exit 8; R=/private/tmp/rp$$; mkdir -p $R/h $R/t; export HOME=$R/h TMPDIR=$R/t PHOENIX_HARNESS_CYSD=$PWD/target/debug/cysd PHOENIX_CYS=$PWD/target/debug/cys PATH=$PWD/target/debug:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin; python3 --version; f=0; n=0; for t in cysjavis-pack/bin/tests/test_phoenix_*.py; do n=$((n+1)); CYS_PACK_DIR=$(mktemp -d $TMPDIR/p.XXXXXX) python3 $t >$R/$(basename $t).log 2>&1 || { f=$((f+1)); echo FAIL $t; }; done; echo "phoenix n=$n fail=$f logs=$R"; [ $f = 0 ] && rm -rf $R; exit $f'
# pre-tag (gh 토큰을 api.github.com 요청에만 붙인다 · 스크립트 무수정 · 익명 rc 2 회피)
python3 -c "import runpy,subprocess,sys,urllib.request as u;t=subprocess.check_output(['gh','auth','token'],text=True).strip();o=u.urlopen;u.urlopen=lambda r,*a,**k:(r.add_header('Authorization','Bearer '+t) if r.full_url.startswith('https://api.github.com/') else None,o(r,*a,**k))[1];sys.argv=['pre-tag-ci-check.py','<SHA>','--wait','70'];runpy.run_path('scripts/pre-tag-ci-check.py',run_name='__main__')"
```

⚠1-2c 는 `rm -f target/debug/cys target/debug/cysd` 뒤 재빌드한다(함정 ①) · 그 줄의 python3 = 3.10 이상이어야 한다(L20) · 판 빌드(`build-macos-local.sh`) 뒤에는 한 번 더 확인.

### K-8. 0fde41c6 CI 읽기(비차단 주석 · 스택 · 060cb75b 런 대조)

| 항목 | 0fde41c6 | 060cb75b | 읽기 |
|---|---|---|---|
| `[release-stack]` 세 명령 | `overflow=no` | `overflow=no` | 차이 0 · 여유는 미측정 |
| T3-3 FAIL(env주입 스텁 send rc=1) | 있음 | 같은 문구 | 전부터 |
| cysd 감독자 축 30분 시간 초과 | 30분 10초 | 30분 11초 | 전부터 · 비차단 |
| `trash::` | 통과 0 · 실패 0 | 같음 | **빈 판정(L21)** · CI 가 못 재는 축 → 밤 r4 휴지통 1줄(master#8d598191) |
| 감독자 축 패닉 | 146건 | 175건 | 대부분 윈 시험 좌석 `sleep 30` 10초 미기동 · 기준에만 32건 · 새 런에만 3건 |

새 런에만 있는 3건 = `governance::tests::deliver_head_locked_pops_by_id_and_reports_remaining` · `qa_bypass_disclaimer_window_blocks_queue_and_force` · `qa_permission_dialog_classic_blocks_as_approval_pending`(뒤 둘 = busy(출력 중)). 기준 런에서는 통과 · `governance.rs` 병합 변경 0 · 시간 초과로 끊긴 위치가 달라 두 집합을 온전히 비교할 수 없다 · 플레이크로 단정하지 않는다.

r4 키트 aac1b477 ↔ 0fde41c6 차이 = 10파일(문서 9 · `ui/src/publicdocs.test.ts` 시험 1) · 코드 변경 0. `USER-MANUAL.md` 의 `include_str!` 5곳은 전부 `mod tests` 안 · 번들 자원 아님.

맨 `cargo test --bin cys`(병렬 · 기본 스택) 넘침 집계 = 060cb75b 0/2 · 0fde41c6 2/2 · 4MB 736/0 · 원인 미상 · 발행 형식 밖(§J · master#7a17878b).

### K-9. 57bce92e(크롬 미리 켜기) · 90a372d2 병합 뒤 다시 돌릴 항목(master#415438c7 · 옛 b3f51379 C안 · r5 계획을 대체)

**r8 편입(master#fbb4cb14 · 로컬 가지 merge/1111-r8 · push = master)**:

| 병합 커밋 | 대상 | 내용 |
|---|---|---|
| 8893402d | fix/1111-atomic-swap 9fafe435 | 팩 교체 무손상(1cc1a8fd) · 끊긴 교체 복구 B1 고침(9fafe435 · 777·codex 반려분) · n1 내용 비교·n5 보존 폴더 격리(6d3155c2 · 786 재확인분) · `tests/win_pack_swap.rs` |
| 0a9cccfe | fix/1112-noderecover-ctrlu 751a379d | 윈 node-recover `^U`(17943406) · L1 cys restore 출력 전문을 phoenix-restore.log 에(1122d062 · 관측 전용) · R2 세션 핀 변경 즉시 topology 영속(751a379d · 759 대조 = native_publication 2건은 기준선도 실패 · 회귀 아님) |
| 5d3fccd5 | fix/1111-atomic-swap e60ec3bb | 끊긴 교체 복구 · 팩 복사가 FIFO 에서 멈추지 않는다(0835ad3d · 786 재검증 b2.4 · 양쪽 일반 파일 확인 · O_NONBLOCK + 핸들 stat) · 786 회귀 시험 3e561cef(원 d0515b97) |

수리 3 = ① 팩 교체 ② `^U` ③ 복원 뒤 워커 교체 원인 — L1·R2 까지다 · R3(claim 10분 잔류) = 1.1.12 라 좌석 교체 끊김이 다 없어지지는 않는다(751a379d 본문). 충돌 0 · 두 가지 겹침 파일 = 이 체크리스트뿐. 이 머리에서 아래 표 전체를 다시 돌리고 r8 키트로 r7 항목을 다시 본다.

**병합 대상(master#415438c7 · 끝)**:

| 병합 커밋 | 대상 | 근거 |
|---|---|---|
| a431e8a3 | fix/1111-win-chrome-job 57bce92e | 777 독립 재확인 PASS(b9ad43fc) + 마지막 작은 고침 · CI windows-build 41263079971 · windows-health 41263079972 · ci-branch 41263079920(1차 macos-rust-pack d7_prime_seat_cache 타이밍 1건 적 → 실패 잡 재실행 녹) |
| c79011b9 | docs/1111-seminar 90a372d2 | `cysjavis-pack/skills/grill-me/SKILL.md` 1줄(한글 그대로 쓰기) |

함께 들어간 rel 로컬 커밋 = 72f3c383(맥 부서 닫기 카드 `javis_dept_request.py:656` · 근거 `ui/src/resetconfirm.ts:12-13` · `cys-dept:3490` · 닫기 = `destroy --purge --purge-state`). 노트 충돌 1건 = 확정 37줄 + 「마스터 좌석에서만 크롬을 다루고, 일반 작업 좌석에는 켜지 않습니다」 1문장 · 759 문구 3종 미채택.

범위 재측정: `0fde41c6..c79011b9` 22파일 +1204 −2022 · 코드·표 10파일 = `src/pack.rs` · `src/lib.rs` · `src/bin/cys.rs` · `src/released_directive_hashes.rs` · `javis_computer_control.py` · `javis_dept_request.py` · 시험 3 · `RELEASED_MASTER_DIRECTIVE.sha256`. `src/bin/cysd` 0건. ★**Rust 변경 있음 · 맥도 바뀜 · MASTER_DIRECTIVE 문구 변경 + RELEASED 해시 표 재생성.** 로컬 문서 커밋(0fde41c6 위)도 함께 머리에 들어가므로 §K 의 「태그 뒤 push」 대신 최종 머리에 같이 올라간다.

| 재실행 | 항목 | 까닭 |
|---|---|---|
| ☐ 다시 | 0-1 머리 확정 · 1-1 `secret-scan --all` → push → **dispatch 3런** | 머리 의존 · `rel/**` push 트리거 밖 |
| ☐ 다시 | 1-2 version-check · win-typecheck · pre-tag(+§K-8 주석 읽기) · scan-pack-secrets · H-SECRET-1 | 머리 의존 · 팩 변경 = 비밀 스캔 대상 |
| ☐ 다시 | 1-2b ANC · 1-2c phoenix 전건 | 머리 의존(§K-6) |
| ☐ 다시 | 로컬 `cargo test --bin cys -- --test-threads=1` · lib 전체 · **cysd 전체** | `src/pack.rs` 변경 · cysd 전체는 크롬 가지 쪽 미실행 |
| ☐ 다시 | 병합 트리에서 `test_computer_control.py` · `mut_computer_control.py` · lane-parity --strict | 바뀐 시험이 합쳐진 트리에서도 그대로인지 |
| ☐ 다시 | 스택 대조 · win_job_exit 줄 = 새 windows-health 로그에서 읽기만 | Rust 변경 있음 → 값이 달라지면 master 판정 |
| ☐ 다시 | 깨끗한 기기 §K-4 보충: 새 설치에서 키 한 칸짜리 `.claude.json` 뒤 첫 시작 · 로그인 관문이 그대로인지 | 새 설치 때 이 파일이 생긴다 · §K-4 는 그 전 빌드(060cb75b) · 맥 첫 시작 영향 판단 근거 = 설계 §13-7 격리 실측뿐 |
| ☐ 다시 | **맥 빌드 게이트 SEAL-3**: 앱 안 pip.conf · codesign 전후 · 동봉 pip 설치 뒤 새 파일 0(아래 명령) | aa1c7cb6 이 빌드 산출물에 실린 것을 잰 기록 없음 · master#f35a4fd3 |
| ☐ 다시 | r7 키트 ↔ 최종 머리 파일 차이 1줄(§K-8 r4 문단 대체) | r7 결과를 태그 판정에 쓰는 근거 |
| ☐ 조건 | 노트 자리 표시(r7-2) · 노트 §G 칸 · 카톡 ④ | r7 결과 의존 |
| ☐ 조건 | §K-10 사이트 세미나 묶음 = 4-2 에 포함 | 발행 뒤 사이트 갱신 |
| ☐ 옮겨 적기 | **r7 결과 표에 휴지통 줄을 옮겨 적는다**: 윈 r4 15번 = 통과(비우기 꺼짐 · 되살리기 단추 없음 · 윈 master 22:0x 보고) | CI `trash::` 빈 판정의 대체 근거 · 휴지통 코드 변경 0(`060cb75b..57bce92e` 파일·diff 줄 0 · 재실측 · 72f3c383 은 카드 문장 1줄뿐) 이라 r4 결과 승계(master#5f91545d ④) · 최종 키트가 이 머리와 다르면 그 차이로 다시 확인 |
| ☑ 닫힘 | §K-1 `--state-migration` 판독을 57bce92e 까지 연장 | **none**(아래 연장 판독) · 병합 뒤 크롬 가지에 새 커밋이 더해지면 그 차이만 다시 |
| 그대로 | 1-0 판번 · §6 칸(none 은 위 연장 판독이 뒤집지 않는 한) · 0-8 팩 하한 · §K-7 | 변경이 닿지 않음 |

**r7 실기(master 키트 · 항목 정본 = `~/cys-terminal-src-wt/1111-winchrome/HANDOFF-1111-winchrome.md` 「r7 실기 항목」 · 결과 칸 = 실기 회신으로 채운다):**

| # | 항목(요약) | 닫는 것 | 결과 |
|---|---|---|---|
| r7-0 | 윈 노트북: r7 앞에 떠 있는 옛 `seat-restart-wait` 프로세스 유무(있으면 옛 코드로 rotate 할 수 있다) | 시험 전제 | ☐ |
| r7-1 | 업데이트(`--no-install-hook` 경로) → 좌석 시작 → 키 true · `.cys-chrome-preset` · 연결 파일(맥)/레지스트리(윈) · **크롬 도구 `mcp__claude-in-chrome__*` = 본부 master 좌석만 · 워커·CSO·리뷰어·부서 좌석(부서 master 포함) 0** · ledger 에 `seat_restart_scheduled`·`chrome_quit` 없음 | 노트 크롬 문장 · 「마스터 좌석에서만」 · §G · N4 | ☐ |
| r7-2 | 크롬 꺼진 채/켜진 채 각각: 업데이트 뒤 연결 · 안 되면 크롬을 다음에 켠 뒤 붙는지 · 시각 | 노트 자리 표시(「껐다 켤 일이 없습니다」) | ☐ |
| r7-3 | `/chrome` 으로 끈 false → 업데이트 → false 유지 · `chrome-disable` 로 키 없어진 경우 → 그대로 · 「크롬은 빼 줘」(장부 없음 · 키 true) → 키 꺼짐 · 다음 시작부터 도구 0 · adopt 가 다시 안 가져감 | 노트 「그대로 꺼져 있습니다」 · 「크롬은 빼 줘」 | ☐ |
| r7-4 | 맥 1회: r7-1 과 같음 · 처음 연결 파일이 생길 때 「다시 연결」 탭이 뜨는지 · 조직 복원 첫 시작의 탭 개수(master 만 켜므로 1개여야 한다) | N4 맥 쪽(맥 실기 기록 0 · 무인 교회 맥에서 박사님 로그인 크롬을 재시작하지 않는다 · master#5f91545d ⑤) | ☐ |
| r7-5 | 윈 새 설치: 첫 시작 로그인 뒤 다음 시작에서 연결(첫 시작은 OAuth 전이라 연동 미시작) | 새 설치 사용자 문장 | ☐ |
| r7-6 | 윈 크롬 꺼짐 + 첫 연결 파일 + 확장 설치됨: 다시 연결 탭 개수 · 탭이 크롬을 띄우면 그 크롬의 Job 소속(`in-caller-job`) · ↻ 뒤 생존 | 기록 · 1.1.12 rotate 관문(HANDOFF BACKLOG) · 발행 차단 여부 = master | ☐ |
| r7-7 | 좌석 재기동 경로: 워커를 node-recover·`cys restore`·rotate 복원으로 다시 띄운 뒤에도 크롬 도구 0(윈 = 기존 pane 재기동은 `--settings` 만 닿는다 · `~/.cys/seat-settings/<역할>.json` 의 env 확인) | 「일반 작업 좌석에는 켜지 않습니다」 | ☐ |

r8 추가 확인(키트 구성 = master): ① 업데이트 반복 — r7 6회차 재현 조건에서 팩 파일 수 불변 · rc 24 면 팩 무손상 · 재시도 성공 ② r7-7 재시험 — 윈 `^Uclaude` CommandNotFound 0 ③ 좌석 교체 시 phoenix-restore.log 에 cys restore 출력 전문 · topology session_id 유지.

**발행 뒤 첫 확인(master#9312bc1c ②):**

| 시점 | 항목 | 실패 시 | 결과 |
|---|---|---|---|
| ⛔발행 뒤 · 4-1 핀 1.1.11 라이브 확인 직후 | 태그 직후 윈 노트북에서 **공개 한 줄 설치 1회** = 발행 후 첫 확인: 설치 전 `.cys-chrome-preset` 없음 · `claudeInChromeDefaultEnabled` 키 없음 확인 → 한 줄 설치 → cysr 1.1.11 · 키 true · 표지 · 레지스트리 · 좌석에 크롬 도구 | 즉시 핫픽스 | ☐ |

- **한 줄 설치를 r7 에 못 넣는 근거**(9312bc1c 의 가정 「r7-7 = 한 줄 설치」는 쓰지 않았다 · 위 r7-7 = 크롬 가지 HANDOFF 의 좌석 재기동): 공개 한 줄 설치는 판 지정이 없다. 라이브 설치기 0.3.43 `bootstrap.ps1:42-45`(인자 = `-DetectOnly`·`-DryRun` 뿐) · `:143` `$CysVersion = '1.1.10'` · `:154` 파일 이름 고정, 맥 `bootstrap.sh:150` `CYS_FORK_VERSION="1.1.10"`. 판을 바꾸는 환경변수 0(라이브 두 파일 전수) · 받은 파일은 스크립트의 sha256 과 대조한다. 줄 번호는 라이브 기준이다(ai-jarvis 현재 작업트리 사본은 0.3.42 · origin/site/hub 사본이 0.3.43).
- **시점 주의**: 설치기 핀은 발행 뒤 4-1 에서 오른다. 태그 직후에 그대로 돌리면 공개 한 줄은 1.1.10 을 깐다. 그래서 4-1 라이브 확인 뒤에 돌린다.
- **기기 주의**: r7 판을 깐 노트북은 표지가 이미 있어 시드 경로를 안 지난다(`seed_chrome_default_at` = AlreadyDone). 표지·키가 없는 상태에서 돌려야 이 확인이 뜻이 있다.

✔판정(master#9312bc1c ①): 확장 설치·로그인 안내는 도구 쪽에 그대로 둔다(`javis_computer_control.py` ext · 「Chrome에 추가」 · 같은 계정 로그인). 공개 문장 = 노트 37줄로 확정. 확장 없는 사용자는 노트 문장대로 켜져도 연결되지 않고 자비스가 그때 안내한다. r7 항목은 전부 확장 있는 기기를 전제로 한다. 「크롬을 껐다 켤 일이 없습니다」는 r7-2 를 본 뒤 정한다.

**맥 빌드 게이트 SEAL-3(master#f35a4fd3 · 사용자 보고 fleet a738765c · `pip` 가 앱 묶음 안에 써서 봉인 2종 실패 → aa1c7cb6 이 `<runtime>/python/pip.conf` 를 심음):** 「빌드된 앱에 실제로 실리는지」 재본 기록이 없어 게이트로 둔다. 대상 = 최종 머리로 만든 맥 앱(§K-4 꼴 시험 빌드 또는 2-2 산출 zip). ⛔`/Applications` 의 라이브 앱에 돌리지 않는다 — 격리 폴더에 푼 사본이나 VM 복제본에서만. ① = arm64·x64 zip 각각 · ② = arm64 1회.

```bash
# 준비: 격리 폴더에 푼다(라이브 무접촉)
W=$(mktemp -d); ditto -x -k cysr-macos-arm64-v1.1.11.zip "$W"; APP="$W/cysr.app"
PY="$APP/Contents/Resources/runtime/python"

# ① pip.conf 실재 + 내용 — 기대: 경로 1줄(…/runtime/python/pip.conf) · 끝에 [install] 과 user = true
find "$APP" -name pip.conf -print
cat "$PY/pip.conf"

# ② 봉인 전후 + 동봉 pip 설치 뒤 묶음 안 새 파일 0건
#    기대: before rc=0 · pip rc=0 · new=0 · after rc=0 · six.py 가 격리 HOME 의 .local 아래
unset PIP_USER PIP_CONFIG_FILE PYTHONUSERBASE
codesign --verify --deep --strict "$APP"; echo "before rc=$?"
H=$(mktemp -d); M="$W/mark"; touch "$M"; sleep 1
HOME="$H" "$PY/bin/pip3" install --no-input --no-cache-dir --disable-pip-version-check six; echo "pip rc=$?"
echo "new=$(find "$APP" -newer "$M" | wc -l | tr -d ' ')"
codesign --verify --deep --strict "$APP"; echo "after rc=$?"
find "$H" -name six.py
```

- 리허설(2026-11-01 · 명령 흐름만 · ⚠빌드 산출물 아님): 라이브 앱의 격리 사본(558M)에 같은 pip.conf 를 넣고 ad-hoc 재서명 → before rc 0 · pip rc 0 · new=0 · after rc 0 · `six.py` = 격리 HOME `.local/lib/python3.12/site-packages`. 음성 대조 `--no-user` = new=35 · codesign rc 1 → 이 명령이 번들 쓰기를 잡는다. 사본 삭제. 라이브 설치본에는 pip.conf 가 없다(옛 판).
- 실패 시: ① 없음 = 실림 실패 · 태그 전이면 빌드 경로 수리 ② new≥1 또는 after rc≠0 = 봉인 깨짐 · master 판정. 알려진 잔여(aa1c7cb6): `--no-user` · `--target`/`--prefix` · `uv pip install --system` 은 여전히 번들에 쓴다.
- 결과 칸: ① arm64 ☐ · x64 ☐ · ② ☐

**§K-1 연장 판독(060cb75b..57bce92e · 크롬 가지 전체) = none.**

- 기존 상태의 개명·삭제·타입 변경 0. 새로 쓰는 것 = `<cfg>/.claude.json` 의 `claudeInChromeDefaultEnabled` 키 1칸(Claude Code 공식 토글 · 키 없을 때만 · 다른 칸 보존 · Claude 와 같은 잠금 · 심볼릭 링크면 거절) · 표지 `<cfg>/.cys-chrome-preset`. `~/.cys/computer-control/` 의 `chrome-enable.json` · `decisions.json`(「크롬은 빼 줘」 = `take:chrome` deny 항목)은 그 도구가 1.1.11 신규다. 옛 빚 키(`OLD_CHROME_STATE_KEYS`)는 읽어도 행동 0 · 만나면 지운다.
- 좌석 쪽 = 저장 상태 아님: `CLAUDE_CODE_ENABLE_CFC=false` 는 좌석 env 와 `~/.cys/seat-settings/<역할>.json` 의 `env` 칸으로만 간다(v1.1.10 도 있는 파일에 칸 추가 · 본부 master 좌석은 칸 없음). RELEASED 해시 표 = 판 내장 상수.
- **1.1.10 으로 내림**: `git grep` v1.1.10 `src`·`cysjavis-pack` = 키·표지·`CLAUDE_CODE_ENABLE_CFC` 0건 → cys 쪽은 읽지 않아 무해. ⚠단 키는 Claude Code 가 읽는다: 내리면 env 를 얹는 코드가 없어져 **키가 true 인 채 모든 좌석에 크롬 도구가 뜰 수 있다**(되돌리는 코드 0 · `/chrome` 으로 끌 수 있다 · 좌석 재기동 뒤 seat-settings 칸이 어떻게 되는지는 미측정). 저장 형식 문제는 아니고 동작 잔재다.
- **다시 올림**: 표지가 있으면 파일을 읽지 않는다 → 내린 동안 사용자가 끈 값·지운 키가 그대로 남는다. 표지 내용(판번)은 읽지 않고 존재만 본다.
- 팩 1.1.11 + 옛 바이너리: 팩의 `spawn-outside-job` 호출 0 이라 Job 이탈 의존이 없어졌다. 단 좌석 env 는 바이너리 몫이라 옛 바이너리면 좌석 차단도 없다(팩 하한 1.1.11 이 막는 조합).
- 초기화: `factory_reset` 목록에 `claude`(키·표지가 든 폴더) · `computer-control` · `pack.swap` 있음.
- r8 연장(93fb8e08..merge/1111-r8) = none: `pack.swap` 은 교체 중에만 있는 폴더 · R2 는 기존 topology `session_id` 칸의 영속 시점만 앞당긴다 · L1 은 로그 내용만 늘린다.
- ⚠근거 = 코드 판독. 이 키가 든 상태로 내림·올림을 왕복 실측한 적은 없다(§6 의 VM 왕복 1회는 이 가지 이전).

### K-10. 사이트 세미나 묶음(master#266c929d ② · 4-2 에 같이 올린다 · 배포 아직 아님)

- **대상**: ai-jarvis 가지 docs/1111-seminar f63bcd1(origin/site/hub f669aac 바로 위 · 작업트리 `~/axdev/.wt/ai-jarvis-seminar-docs`). `site/howto/dept.html` 9절 정정·닫는 길 표 · `site/howto/manual.html` 2줄 · `site/howto/first-screen.html` 입력칸 세 가지 · `docs/shots/` 그림 3장. 776 보고 = check-links·facts·tap PASS(이 좌석이 재지 않았다).
- **절차(기존 기록)**: 집행 = master(push · wrangler deploy · web-install deploy · 공지 = master · 카톡 = 박사님 · `docs/HANDOFF-site-119-prep-2026-10-16.md:4`). 순서 = 4-2 그대로: site/1111 에 f63bcd1 병합 → `bash site/test/gate.sh` → `bash web/build-web.sh` → 실렌더 → `cd web && wrangler deploy` **먼저** → `bash web-install/deploy.sh --go`(같은 문서 :16) → site/1111 을 site/hub 에 병합·push(L11).
- **주의**: site/1111 가지는 아직 없다(로컬·원격 `site/*` 실측). 4-1 설치 사본 동기 전에는 공지 판번과 핀이 달라 gate ⑧ 이 붉다(`check-release-pin.py` · 같은 문서 :38·:67 · 의도된 차단). 그래서 묶음 배포는 4-1 뒤다.

## J. 1.1.12 BACKLOG(이 준비에서 나온 것)

- [ ] ★**첫 항목 — 자동 갱신 게이트 수리 + 실기**: `may_fire_within` 주기 잡 판정 · 내장 잡 `bulk`·`publish` 표식 · `agora-counsel` publish 판정 + **S4 이후 전 구간 실기(맥 VM·윈)** — 이 경로는 공개 기기에서 한 번도 돈 기록이 없다 · 근거 전문 = 인박스 155275줄(2026-10-31T07:42:16+0900 · worker-relprep) · §K-7 · 수리 뒤 공개 문장을 다시 맞춘다: README(한/영) 「새 판 받기」 · `USER-MANUAL.md` §11 · `docs/index.html` 안내 · `ui/src/publicdocs.test.ts` 도움말 고정값 · release.yml:1326(이번 판에서 뺀 줄 포함 · 커밋 이력 참조).
- [ ] **int 가지가 발행 태그를 조상으로 갖는지 게이트** — `scripts/pre-tag-ci-check.py` 에 is-ancestor 검사(최신 공개 태그 ∧ origin/main 이 태그 후보의 조상이 아니면 태그 금지 · master#e9af822d). 근거 = §H · L15.
- [ ] 태그 레인 전용 시험(`test_phoenix_*.py`)을 태그 전에 돌리는 길 — 브랜치 CI 또는 pre-tag 수동 줄(L19).
- [ ] **수용된 가지 편입 원장** — 수용 ≠ 편입 · 태그 전 수용 가지 전수 is-ancestor 검사(master#8fd148bb · fix/1111-backlog-misc·fix/1111-fable-fixes 실증).
- [ ] 통합 검토 이월 = `~/cys-terminal-src-wt/1111-adv4/ADV4-FINDINGS.md`(0c8b5ab2) major M3·M4(실기 결과에 따라)·M6~M13 · minor N1~N10 · X1~X3.
- [ ] 병렬 기본 스택 `a3_strip_hook_digits…` 넘침 · 4MB 통과 · 시험 스레드 스택 고정 또는 무거운 시험 분리(master#7a17878b). 실측: 맨 `cargo test --bin cys`(--test-threads=1 없이) dc9f1de7 3/3 넘침 · 060cb75b 0/2 · 0fde41c6 2/2 · `RUST_MIN_STACK=4194304` 0fde41c6 736/0 · CI 형식 0fde41c6 736/0 · 단독·소묶음은 두 머리 모두 통과 · 병합의 파싱 경로 변경 0 · 원인 미상(master#75c7ef79).
- [ ] release `cys.exe` 스택 여유 측정 — `[release-stack]` 은 `--help` 세 명령의 넘침 여부만 본다 · 윈 주 스레드 1MB 에서 남은 여유·머리 간 증감은 미측정(0fde41c6 차이 0 은 넘침 0 뜻뿐 · master#8d598191).
- [ ] `dbg_r12_init_pack_wires_profile_skill_links` 는 저장소가 임시 폴더 아래면 결정적으로 실패한다 — 시험이 `CARGO_MANIFEST_DIR/target` 아래 팩을 쓰는데 `javis_preflight.py:1494` 임시 팩 가드가 등록을 거부(코드 판독 · /private/tmp 임시 worktree 060cb75b 4/4 적 · 정상 위치 0fde41c6 통과 · 제품 결함 아님 · master#7a17878b).
- [ ] atomic-swap 검증 이월(무손상 · master#6aa19b60 · 근거 = ~/axdev/master/reports/2026-11-01-cysr-1111-atomic-swap-verify.md · -b1-verify.md): m3 prev 가 잠겨 hold 가 남으면 다음 교체 rc 24 · m4 prev 일부 삭제 뒤 보관 실패면 반쯤 지워진 prev 가 pack-rollback 재료로 남음 · m5 교차 볼륨은 이제 실패 · m7 재시도 대기를 맥에서 지키는 시험 없음 · m8 `had_old` 시험 없음 · n2 동시 복구 둘이 prev 를 지울 수 있음 · n3 pack-update 채널·버전 판정이 복구 앞 · n4 새 팩 표지 1개 부재 시 활성 팩이 옛 팩으로 후퇴(새 팩은 보존 폴더) · n6 빈 `pack.swap` + 완전 팩이면 prev 가 빈 폴더가 됨 · n7 파일 `pack.swap` 은 교체가 매번 약 9초 뒤 실패 · n8 부분 팩 되돌리기 줄 시험 없음 · n9 보존 폴더가 스냅샷·`doctor --lanes`·pack-rollback 과 어긋남.
- [ ] rotate 겹침 — ② 새 데몬이 소켓을 연 직후 콜드부트 복원을 발화해(`cysd/main.rs:2310` · 표식 조건 없음) ④ init-pack 과 겹친다. 1.1.11 은 겹쳐도 팩이 지워지지 않게만 고쳤다(atomic_swap · 윈 r7 · master#85a5002d). 잠금이 안 풀리면 rc 24 로 끝난다. 복원을 ④ 뒤로 미루는 수리 = cysd·rotate.
- [ ] `cargo test --bin cysd native_publication::` 병렬 불안정 — 기본 병렬에서 2건 실패 · 단독과 `--test-threads=1` 은 통과 · 기준선도 같은 ID(759 대조 · master#e8ff936f · 회귀 아님). 시험 간 공유 자원을 찾아 고친다.
- [ ] cysd 전체 병렬 간헐 — 짝 10회(ccfcb9e7 · 93fb8e08) · 무실패 각 2회. 머리·기준 공통 = native_publication 2건 · settle_hold · v116(연쇄: 패닉이 PACK_ENV_LOCK 독살 → unwrap PoisonError). 한쪽 1회씩 = s4_1 · qstarved · rqfix2 · np_different_builtin · c8aftercare 2건 · c8protocol · k17 · refused_hand_off(s4_1·qstarved 표적 부하 반복 75회 양쪽 무재현). 전체 직렬 = 머리 3회 무실패 · 기준 2회 중 k17 1건. 머리 큐 경로 코드 변경 0. PACK_ENV_LOCK 잡은 시험의 `.unwrap()` 을 `unwrap_or_else(into_inner)` 로 바꿔 연쇄부터 끊고, 시한 경계를 넓힌다.
- [ ] `test_hook_r34` 시한 3.0s 경계 — 부하 3회 머리·기준 모두 적(RCF-3·RCF-4a·NZ-3·DL-1b · 3.02~3.83s) · 머리·기준 동시 8회 각 7회 적 · 혼자 돌면 통과. 경계를 넓히거나 직렬 칸으로 옮긴다.
- [ ] `test_dept_notice_lane` 1c — 전수 -P 3 에서 머리 1회 IndexError(fmlog 빈 줄 · 존재만 보고 읽음) · 머리·기준 동시 8회 각 무실패 · 시험·대상 코드 기준선 diff 0. 도우미가 내용까지 기다리게 고친다.
- [ ] `copy_dir_all` 검사~fs::copy 사이 FIFO 교체 틈 — tree_contained 는 O_NONBLOCK+핸들 stat 으로 닫았고 복사는 권한 보존 때문에 fs::copy 유지(0835ad3d). 같은 형태로 닫는다.
- [ ] 판번 검사(`version-check.sh`)가 `docs/index.html` 을 보지 않는다(L14).
- [ ] (윈 실기 이월 · TODO:83) `\cysd` 재등록이 LeastPrivilege 로 RunLevel Highest 를 덮음 · preflight --fix 가 `~/.claude/settings.json` 을 백업 없이 고침 · ConPTY 꽉 찬 줄 composer 사람 눈 1회 · self-update-check 새 데몬 뒤 첫 발화.
- [ ] (통합표) `d7_prime_seat_cache_never_overwrites_a_tick_value` 상한 5초 플레이크.
- [ ] 677 hook-slim(R3 REVISE) · 윈 휴지통 삭제.
- [ ] **윈 node-recover `^Uclaude`**(가지 fix/1112-noderecover-ctrlu · 커밋만 · 1.1.10 이전부터) — 현상 = 윈 PowerShell 창에 `^Uclaude …` 가 입력돼 CommandNotFound · 좌석이 빈 셸로 남음 · 데몬 자동 재기동도 같은 길. 원인 = `src/bin/cys.rs:25189` 선정리 C-u(0x15)를 프롬프트가 글자로 받음. 수리 = 윈 한정 C-u 뒤 Backspace 1회(관문 불변). 재시험 3종 = r7-7 3/3 · 초안 창 거부 유지 · claude.exe kill 뒤 데몬 자동 재기동.
- [ ] (relprep) `test_phoenix_c6_reap.py:101` `except TimeoutError` → Python 3.9 에서 거짓 적(L20) · `.kept-pane-records.jsonl` 공장 초기화 목록 누락 · windows-build T3-3 적 원인 · windows-health 감독자 축 30분 시간 초과로 `trash::` 줄 0(L21) · 앱이 켜진 채 데몬이 바뀌면 「엔진」 라벨 미갱신.
