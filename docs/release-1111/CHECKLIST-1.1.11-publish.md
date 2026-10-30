# cysr 1.1.11 발행 집행 체크리스트

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
| 4-2 ⛔ | 사이트(ai-jarvis): 공지 `site/notice/<발행일>/` · 손댈 자리 7(1.1.9 SITE-119 꼴: ①새 공지 index.html ②`site/notice/index.html` 목록 맨 위 ③`site/index.html` 머리 띠 ④`site/get/index.html` 머리 띠 — **끝 문단 링크만** `#install` 꼴이라 같은 치환을 두 파일에 쓰면 한쪽 0건 ⑤`site/devlog/index.html` 새 항목 + 시기 머리 ⑥`site/test/check-render.py` PAGES 한 줄 ⑦「최신 판」 숫자 스윕 `grep -rnI '1\.1\.[0-9]' site \| grep -v '^site/install/'` ⑧★자동 갱신 문장 스윕 `grep -rnI '알아서 받\|쉬는 시간' site` — 대문·/get/ 「1.1.8이나 1.1.9를 쓰고 계시면 … 알아서 받아 둡니다」 교체 · 처분 §K-7) → `bash site/test/gate.sh` → `bash web/build-web.sh` → 실렌더 6조합(대문·설치하기·공지 × 390/1440) → `cd web && wrangler deploy` · `bash web-install/deploy.sh --go`(npm ci 먼저) · ★**site/1111 가지를 site/hub 에 병합하고 push**(L11 — 안 하면 다음 배포가 옛 판으로 돌아감) | GATE=PASS · `/notice/<발행일>/` 200 · 띠 2곳 1.1.11 · 「최신 = 1.1.9」 잔존 0(첫 조회 엣지 HIT 가능 · 20초 뒤 재측) · 라이브↔빌드 대조 때 Cloudflare 주입 2조각 제외 · `/install/next` 404(실기 때 썼으면 삭제) · 공개 저장소 checks [사이트] 대조 붉은 창 0(H7:72) | 이전 커밋 재배포 |
| 4-3 | 카톡 문안 `docs/release-1111/KAKAO-1111.draft.md` → 라이브 공지와 대조 → 박사님 전달(발송 = 박사님) · ★보낸 **최종본을 그대로 파일로 커밋**(L10) | 링크 200 · 공지 앵커 | — |
| 4-4 | 자동 받기 관측 = **이번 판 해당 없음**(근거 `src/update/sched.rs:151-154`·`:217-229` · §K-7 · master#3e3039b5) · 공지·카톡에 자동 갱신 문장 0 | 3-9 의 hold 값 기록으로 갈음 | — |

## 5. 미확인 모음(집행 전 master 확정)

1. 관측용 맥 기기 지정(0-4). 2. 윈 재실기 범위 · 갱신 경로 1회 시행 여부(0-3). 3. 윈 1.1.9 기기의 복구기 문제 여부(노트 받는 방법 줄). 4. 봉투 만료 ≈11-06 전 발행 여부 — 밀리면 seq 5 봉투 재게시(10-19 주간 발화는 재료만 만들고 게시 안 함 · 10-26 09:20 launchd 주간 발화 = dispatch 만 · 게시는 사람 손). 5. `state_migration`(§6). 6. 캐너리(R8) 시행 여부. 7. 자동 본문 교체(0-5). 8. §G ⚠ 항목 처분. 9. ⛔`test_phoenix_c6_reap.py` 처분(§I) — 안 고치면 태그 레인 적 · 실패 태그 번호는 재사용 불가(RELEASE-ROLLBACK.md:20-24).

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
| N4 · K④ | 컴퓨터 맡기기 절 | 실 크롬 실기(§G ⚠) | master | ☐ |
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
| cu-1111-precedent — **실 크롬 실기(맥·윈 · 켜짐/꺼짐 · 탭 복원 · 경고)** | ⚠**기록 없음** · 윈 = r2 목록(master#1be35b1b) · 맥 = 발행 바이트 뒤 | SS:1419 「§15 실기 = 절단 전 묶음으로 이월」 · TODO:235 ⑥ 미체크 · 윈 실기 ⓐ~ⓔ 에 크롬 칸 없음(검색어 chrome-enable · 크롬 재시작 · §15) |
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

## K. 태그 전 게이트 판정(TICKET=cysr-1111-relprep · 2026-10-31 · worker-relprep · 기준 = 060cb75b)

머리와 무관한 것은 여기서 닫혔고, 머리 의존 3가지(1-2b · 1-2c · pre-tag)는 §K-6 명령을 최종 머리에서 다시 돌리면 된다.

| 항목 | 결과 | 근거 |
|---|---|---|
| 1-2b | **ANC-OK**(v1.1.10 ∧ origin/main = 502741c7 둘 다 조상) | `git fetch` 뒤 060cb75b |
| 1-2c phoenix | **26/26 rc 0** · Python 3.14.7 · c6 추가 직렬 5/5 · 내 시험 데몬 잔재 0 | 격리 HOME·TMPDIR · CYS_* 해제 |
| pre-tag | **rc 0**(토큰 경로 · API 소모 4) | 3런 41103104106 · 41103108864 · 41103113724 |
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
| N4 · K④ | 불가 | 윈 = 크롬 수리 병합 뒤 r4 · 맥 실 크롬 실기 기록 |
| N5 | 불가 | 윈 r3·r4 회신 표 칸 대조 |
| K⑤ | 불가 | 라이브 공지 배포 뒤 |

### K-3. 미확인 §5 판정

| # | 항목 | 판정 / 필요한 것 |
|---|---|---|
| 1 | 관측 VM | `jarvis-observe-1111` · 목적 = hold 사유 실측 기록(§K-7) · 자동 받기 관측 대상 없음 |
| 2 | 윈 재실기 범위 | r3 진행 중 · 윈 master 회신 필요 · 갱신 경로 1회 시행 = master |
| 3 | 윈 1.1.9 복구기 | K-2 N1 = 코드로 같음 |
| 4 | 봉투 만료 | 실측 stable expires_at 1793970858 = **2026-11-06 22:14 KST** · 오늘 발행이면 무관 |
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

**이미 나간 문장(1.1.10 까지 · 정정 판단 = master)**: 라이브 `/notice/2026-10-23/` · 대문 「자비스가 쉬는 시간에 새 판을 알아서 받습니다」 · 대문·`/get/` 「1.1.8이나 1.1.9를 쓰고 계시면 … 알아서 받아 둡니다」 · 공지 목록 제목 「자비스 새 판 1.1.8 · 다음 판부터는 자비스가 알아서 받습니다」 · v1.1.10 GitHub 본문 「1.1.8 이상은 … 알아서 받고」 · 저장소 `README.md:464` · `USER-MANUAL.md:1454·1457` · `docs/index.html:62`(이 셋은 rel/1.1.11 에도 있다 · 이 티켓에서 안 고침).

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

## J. 1.1.12 BACKLOG(이 준비에서 나온 것)

- [ ] ★**첫 항목 — 자동 갱신 게이트 수리 + 실기**: `may_fire_within` 주기 잡 판정 · 내장 잡 `bulk`·`publish` 표식 · `agora-counsel` publish 판정 + **S4 이후 전 구간 실기(맥 VM·윈)** — 이 경로는 공개 기기에서 한 번도 돈 기록이 없다 · 근거 전문 = 인박스 155275줄(2026-10-31T07:42:16+0900 · worker-relprep) · §K-7 · 공개 문장 `README.md:464`·`USER-MANUAL.md:1454·1457`·`docs/index.html:62`·release.yml:1326 을 함께 맞춘다.
- [ ] **int 가지가 발행 태그를 조상으로 갖는지 게이트** — `scripts/pre-tag-ci-check.py` 에 is-ancestor 검사(최신 공개 태그 ∧ origin/main 이 태그 후보의 조상이 아니면 태그 금지 · master#e9af822d). 근거 = §H · L15.
- [ ] 태그 레인 전용 시험(`test_phoenix_*.py`)을 태그 전에 돌리는 길 — 브랜치 CI 또는 pre-tag 수동 줄(L19).
- [ ] **수용된 가지 편입 원장** — 수용 ≠ 편입 · 태그 전 수용 가지 전수 is-ancestor 검사(master#8fd148bb · fix/1111-backlog-misc·fix/1111-fable-fixes 실증).
- [ ] 통합 검토 이월 = `~/cys-terminal-src-wt/1111-adv4/ADV4-FINDINGS.md`(0c8b5ab2) major M3·M4(실기 결과에 따라)·M6~M13 · minor N1~N10 · X1~X3.
- [ ] `cargo test --bin cys`(--test-threads=1 없이) `a3_strip_hook_digits…` 기본 2MB 스택 경계 이동(dc9f1de7 3/3 넘침 · 4MB 이상 통과 · CI 형식은 통과 · master#75c7ef79).
- [ ] 판번 검사(`version-check.sh`)가 `docs/index.html` 을 보지 않는다(L14).
- [ ] (윈 실기 이월 · TODO:83) `\cysd` 재등록이 LeastPrivilege 로 RunLevel Highest 를 덮음 · preflight --fix 가 `~/.claude/settings.json` 을 백업 없이 고침 · ConPTY 꽉 찬 줄 composer 사람 눈 1회 · self-update-check 새 데몬 뒤 첫 발화.
- [ ] (통합표) `d7_prime_seat_cache_never_overwrites_a_tick_value` 상한 5초 플레이크.
- [ ] 677 hook-slim(R3 REVISE) · 윈 휴지통 삭제.
- [ ] (relprep) `test_phoenix_c6_reap.py:101` `except TimeoutError` → Python 3.9 에서 거짓 적(L20) · `.kept-pane-records.jsonl` 공장 초기화 목록 누락 · windows-build T3-3 적 원인 · windows-health 감독자 축 30분 시간 초과로 `trash::` 줄 0(L21) · 앱이 켜진 채 데몬이 바뀌면 「엔진」 라벨 미갱신.
