# cysr 1.1.11 발행 집행 체크리스트

초안 · TICKET=cysr-1111-publish-prep · 2026-10-30 · worker-rel(surface:1752) · 집행 = master(비가역 줄 ⛔) · U 서명 = 박사님 USB · 카톡 발송 = 박사님
견본 = `docs/release-1110/CHECKLIST-1.1.10-publish-2026-10-25.md`(§1~§4 명령은 그 문서를 1.1.11·seq 6 으로 치환) + 1.1.10 실제 집행 기록(`~/axdev/master/SESSION_STATE.md` = SS:n).
정본 순서 = `docs/RELEASE.md` · 자동 갱신 = `docs/update/HANDOFF-U3.md` §1 ③ · 롤백 = `docs/RELEASE-ROLLBACK.md`.
게이트 = `~/axdev/master/briefs/2026-10-27-cysr-1111-release-gate.md` · 통합표 = `~/axdev/master/HANDOFF-cysr-1111-integrate-2026-10-30.md` · 문안 초안 = 같은 폴더 `RELEASE-NOTES-1.1.11.draft.md` · `KAKAO-1111.draft.md`.

★**1.1.10 12커밋 병합 누락 → 발행 준비에서 적발·복구**(2026-10-30 21:5x · master#e9af822d): int/1111 의 v1.1.10 공통 조상이 3ce93329 라 459d0cca 에는 공개 태그 12커밋이 없었다 → rel/1.1.11 = 459d0cca 위 `git merge --no-ff v1.1.10` = **6690f9a8** · 표 = §H.

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

---

## 0. 착수 전 — 막히면 그 자리에서 멈춤

| # | 할 것 | 확인 줄 | 상태 |
|---|---|---|---|
| 0-1 | 머리 확정 = rel/1.1.11(이 문서 커밋 뒤 · master 재승인 push 뒤 CI 3런 같은 SHA) | `git log --oneline -3 rel/1.1.11` | 대기 |
| 0-2 | 윈 실기 = **459d0cca 시험 판으로 통과**(10-30 20:2x · SS:1729 · ⓐ~ⓔ) | 원문 = 윈 master 회신 표 | 통과(병합 전 바이트) |
| 0-3 | **윈 재실기(병합 뒤 변경분)** = 상담소 단추 · 첫 안내 · reap · 초기화 문구 짧은 확인(master#e9af822d · master 가 윈 master 에 발신) · 키트 = 새 windows-build 런 산출. ⚠그 레인은 release_seq 0 = 자동 갱신 대상 밖(1.1.10 0-3). ⚠갱신 경로(ⓑ)는 L16 대상 — 윈 1.1.10 → 1.1.11 은 어차피 수동 1회라 **설치기 경로로 올리는 1회**가 사용자 경로와 같다(태그 draft setup.exe) · 시행 여부 = master | 재실기 회신 표 | 대기 |
| 0-4 | 자동 받기 **관측용 맥 1.1.10 기기 1대**를 손대지 않고 남긴다(L9) — 이 맥은 발행 뒤 손 교체 대상이라 관측 불가 · 어느 기기 = master · 윈은 수동 1회라 관측 대상 아님 | `cysr --version` · `build-info --json` `release_seq` 5 | 대기 |
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
| 1-2c | ★(L19) 태그 레인 전용: `cargo build --bin cys --bin cysd` 뒤 `test_phoenix_*.py` 전건(release.yml:428-447 꼴 · 격리 HOME·TMPDIR) | 전건 rc 0 · 지금 = c6 적(§I) | — |
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
| 3-2 | GitHub 본문 확인 — 0-5 수리로 자동 본문 설치 안내가 이제 사실대로 나온다(「cysr 터미널 v1.1.11. Windows는 -setup.exe, 맥은 cysr-macos-arm64(애플 실리콘)·cysr-macos-x64(인텔) zip을 … 앱 안 업데이트 단추는 없습니다 …」 + 출발지 줄) → **손 수정 불요가 기본**. 노트 초안의 「GitHub 릴리스 본문」 절(원작 판 0.14.51 표기 · A-1-3)로 바꾸고 싶으면 발행 **뒤** 편집(1.1.9 실제 = 발행 뒤 08:54 `gh release edit v1.1.9 -R oogisoogi/cys-ro --notes-file …` · draft 에서 `--tag` 동반 편집의 tag_name 영향 = 미확인) · 먼저 옛 본문 사본 `gh release view v1.1.11 -R oogisoogi/cys-ro --json body -q .body > r7/body-before.txt` | `gh release view v1.1.11 -R oogisoogi/cys-ro --json tagName,isDraft,body` = tagName v1.1.11 · body 에 「Update 버튼」 0 · 「윈도우 단독 배포」 0 · 3-8 뒤 `releases/latest/download/latest.json` 의 notes 도 같은 두 낱말 0 | `gh release edit v1.1.11 -R oogisoogi/cys-ro --notes-file r7/body-before.txt` |
| 3-3 | 검증 = CI dry-run 의 verify 잡(1.1.9 실제 · 로컬 `release-verify.py`·`release-gate.py assets` 실행 기록 0) — 로컬로도 돌리면: `python3 scripts/release-verify.py --version 1.1.11 --release-dir r7/reviewed --prev-tauri-conf prev-conf.json --prev-pack-keyring prev-keys.json` · `python3 scripts/update/release-gate.py assets --release-dir r7/reviewed --pack-manifest r7/reviewed/pack-manifest.json` | 「릴리스 검증 통과 — 자산 13종(+SHA256SUMS.txt) · 업데이터 4행 전부 서명 일치 · 맥 자산 포함」 · 팩 replay 단조 위반 = E1 최소 재서명 → SUMS 재생성(RELEASE.md:98-117) | — |
| 3-4 | `shasum -a 256 SHA256SUMS.txt`(3-1 ⑤ **뒤** 최종본 · 1.1.9 = 첫 dry-run 10febe52… → 최종 403a8be0…) = **release_bundle_sha256** | 기록 | — |
| 3-7 | dry-run: `gh workflow run release-publish.yml -R oogisoogi/cys-ro --ref main -f tag=v1.1.11 -f release_bundle_sha256=<3-4> -f confirm=PUBLISH`(1.1.9 = `--ref main` 으로 통함 · 그때 main = 6fddbffe) — 지금 main = 502741c7(같은 계열 · dry_run 입력 있음 추정) · ⛔**422 가 나면 멈춤**(dry_run 을 빼고 다시 보내기 금지 · 메모리 reference_cys-release-publish-dryrun-needs-branch-ref) | 「SHA256SUMS.txt 다이제스트: … (입력과 일치)」 · 「맥 자산: 포함」 · 「✅ dry-run 완료 — … 발행은 하지 않았다」 | 바뀌는 것 없음 |
| 3-8 ⛔ | 발행: 3-7 명령 + `-f dry_run=false` → 런이 **승인 대기**(L4 · environment `release-production` · 1.1.9 확정) → `gh api repos/oogisoogi/cys-ro/actions/runs/<RUN>/pending_deployments`(env id 조회 · 1.1.9 = 21524450364) → `gh api -X POST repos/oogisoogi/cys-ro/actions/runs/<RUN>/pending_deployments -F 'environment_ids[]=<id>' -f state=approved -f comment='cysr 1.1.11 발행'` · watch 는 600초를 넘을 수 있다 → 백그라운드 | 로그 「✅ 공개 발행 완료 — tag_name=v1.1.11 · isDraft=false」 · 공개 SUMS 13줄 OK · `releases/latest/download/latest.json` version 1.1.11 · 행 4 · `setup.exe.sig` 200 | ①`gh release edit v1.1.10 -R oogisoogi/cys-ro --tag v1.1.10 --latest` ②`gh release edit v1.1.11 -R oogisoogi/cys-ro --tag v1.1.11 --draft=true` · 삭제 = 최후·오너 지시만 · tag_name 리셋 = PATCH `{"tag_name":"v1.1.11"}`(RELEASE-ROLLBACK.md:53-130) |
| 2-5 ⛔ | (발행 직후) 보관소 게시 — §2 의 2-5 명령 | 2-5 확인 줄 | 2-5 |
| 3-5 ⛔ | main 이동 — ★**이번엔 앞으로 감기**: `502741c7`(현 origin/main = v1.1.10)가 태그 후보의 조상(10-30 실측 `git merge-base --is-ancestor 502741c7 6690f9a8` = 참 · 복구 병합 덕) → cherry-pick·강제 push 불요. 집행 직전 재측: `git fetch origin && git merge-base --is-ancestor origin/main v1.1.11 && echo FF-OK` → 보존 가지 `git push origin 502741c7:refs/heads/archive/main-pre-1111-<발행일>` → `NEW=$(git rev-parse v1.1.11^{commit}); git push origin "${NEW}:refs/heads/main"`(강제 아님 · 중괄호 · L5) | 불변식 「main = 최신 발행 태그 커밋 + CI 전용 패치」 · `gh workflow list -R oogisoogi/cys-ro` 에 refresh-feed active · main 트리 `.github/workflows/refresh-feed.yml:66` `SITE: ${{ vars.CYS_FEED_FETCH_SITE \|\| …}}` 줄 | 보존 가지로: `git push --force-with-lease=main:${NEW} origin 502741c7:refs/heads/main` · FF-OK 가 안 나오면(누가 main 에 새 커밋) **멈춤** |
| 3-6 | 봉투 재료(보관소 6 선행): `for ch in stable next; do gh workflow run refresh-feed.yml -R oogisoogi/cys-ro --ref main -f component=cysr -f channel=$ch -f release_seq=6 -f rollout_pct=100 -f halt=false -f first=false; done`(1.1.9 실제 명령 원문 T1 08:27:20 · seq 만 5) → `gh run download <run> -R oogisoogi/cys-ro -D r3s6/env/<run>` | 「Verify the NEW envelope」 초록 · 아티팩트 `envelope-cysr-stable`·`-next` · **feed_rev 값을 출력 그대로 기록**(A-5 · 추론 4) | 게시 전 — 무해 |
| 3-9 ⛔ | 봉투 게시(stable·next 각각 · 먼저 `--dry-run`): `python3 scripts/update/publish-site.py envelope --r2 cysr-update --file r3s6/env/<run>/envelope-cysr-<ch>/env.json --cys <1.1.11 cys 바이너리> --dry-run` → 같은 명령 `--live-check https://jarvis.godmeyou.kr` | 「update-verify[…] 출발 seq 1,2,3,4,5,6 전부 허용 판정」 줄에 ★**macos-arm64 · macos-x64 · windows-x64 세 대상이 다 나오는지** — ⛔macos-x64 가 없으면 `--live-check` 로 넘어가지 말고 멈춤(1.1.9 는 macos-x64 가 없는데도 경고가 없었다 · L1) · 「라이브 대조 일치」 · `for f in cysr/stable.json cysr/stable.json.minisig cysr/next.json cysr/next.json.minisig; do printf '%s ' "$f"; curl -fsS "https://jarvis.godmeyou.kr/update/$f" \| shasum -a 256 \| cut -c1-64; done` = 아티팩트 sha 4 · 관측용 맥 1.1.10 기기(0-4)에서 `cysr self-update --check --json` = 새 판(seq 6) 있음 쪽 결과(정확 문구 미확인 — 1.1.9 때는 이미 올린 기기에서 `decision="uptodate"` 만 잼) | live-check 어긋남 = 자동 되돌림 rc 4/5 · 같은 rev 다른 내용 재게시 금지 · 비상 = refresh-feed `-f halt=true` → 게시(선례 미확인) · 이미 받은 기기는 못 되돌림 = 더 높은 판으로만(폐기문 = 사건 때만 R-RITUAL.md) |

## 4. 발행 뒤(설치기·사이트·알림)

| # | 할 것 | 확인 줄 | 롤백 |
|---|---|---|---|
| 4-1 ⛔ | 설치기 핀 1.1.10 → 1.1.11(판·크기·sha256·CDHash 를 **발행 자산에서 다시 재서**) — 1.1.9 실제 = habitat `r8/publish-20261017` 143b821(설치기 0.3.40 → 0.3.41) · 라이브 핀 `bootstrap.sh:147` `CYS_FORK_VERSION="1.1.9"` · `bootstrap.ps1:141` `$CysVersion = '1.1.9'` → 공개 jarvis-install main 33447f8 → 16f67c4 · 이번 설치기 판 = **0.3.43** 차례(한 발행에 한 판 · H7:64-72) → `PUBLISH_CONFIRM=yes bash tools/publish-snapshot.sh --src . --dest ~/axdev/jarvis-install --push --terms-check tests/public-terms-check.sh --terms-list …` | 「SNAPSHOT-OK · 적중 0 · 삭제 (없음)」 · 핀 시험(맥·인텔·윈 · 1.1.9 = 17·0 / 11·0 / 12·0) · 함정(H7:64-72): 대상 clone origin = 공개 URL · 원격 git `PATH=/opt/homebrew/bin:$PATH` · x64 는 정적 검사만 · `.DS_Store` 지운 뒤 재실행 · 소요 1.1.9 = 기술 20분 + 라이브 5분 | 이전 핀 커밋으로 |
| 4-2 ⛔ | 사이트(ai-jarvis): 공지 `site/notice/<발행일>/` · 손댈 자리 7(1.1.9 SITE-119 꼴: ①새 공지 index.html ②`site/notice/index.html` 목록 맨 위 ③`site/index.html` 머리 띠 ④`site/get/index.html` 머리 띠 — **끝 문단 링크만** `#install` 꼴이라 같은 치환을 두 파일에 쓰면 한쪽 0건 ⑤`site/devlog/index.html` 새 항목 + 시기 머리 ⑥`site/test/check-render.py` PAGES 한 줄 ⑦「최신 판」 숫자 스윕 `grep -rnI '1\.1\.[0-9]' site \| grep -v '^site/install/'`) → `bash site/test/gate.sh` → `bash web/build-web.sh` → 실렌더 6조합(대문·설치하기·공지 × 390/1440) → `cd web && wrangler deploy` · `bash web-install/deploy.sh --go`(npm ci 먼저) · ★**site/1111 가지를 site/hub 에 병합하고 push**(L11 — 안 하면 다음 배포가 옛 판으로 돌아감) | GATE=PASS · `/notice/<발행일>/` 200 · 띠 2곳 1.1.11 · 「최신 = 1.1.9」 잔존 0(첫 조회 엣지 HIT 가능 · 20초 뒤 재측) · 라이브↔빌드 대조 때 Cloudflare 주입 2조각 제외 · `/install/next` 404(실기 때 썼으면 삭제) · 공개 저장소 checks [사이트] 대조 붉은 창 0(H7:72) | 이전 커밋 재배포 |
| 4-3 | 카톡 문안 `docs/release-1111/KAKAO-1111.draft.md` → 라이브 공지와 대조 → 박사님 전달(발송 = 박사님) · ★보낸 **최종본을 그대로 파일로 커밋**(L10) | 링크 200 · 공지 앵커 | — |
| 4-4 | 실기기 자동 받기 첫 관측(0-4 기기): 어댑터 연결 · 유휴 → 다음 점검 뒤 「자비스가 새 판으로 바뀌었어요」 알림 · `cysr --version` = 1.1.11 · `build-info --json` `release_seq` 6 — 관측 전이면 공지·카톡의 「알아서 받습니다」 = 대체 문장(노트·카톡 초안에 둘 다 준비) | 관측 기록 1줄 | — |

## 5. 미확인 모음(집행 전 master 확정)

1. 관측용 맥 기기 지정(0-4). 2. 윈 재실기 범위 · 갱신 경로 1회 시행 여부(0-3). 3. 윈 1.1.9 기기의 복구기 문제 여부(노트 받는 방법 줄). 4. 봉투 만료 ≈11-06 전 발행 여부 — 밀리면 seq 5 봉투 재게시(10-19 주간 발화는 재료만 만들고 게시 안 함 · 10-26 09:20 launchd 주간 발화 = dispatch 만 · 게시는 사람 손). 5. `state_migration`(§6). 6. 캐너리(R8) 시행 여부. 7. 자동 본문 교체(0-5). 8. §G ⚠ 항목 처분. 9. ⛔`test_phoenix_c6_reap.py` 처분(§I) — 안 고치면 태그 레인 적 · 실패 태그 번호는 재사용 불가(RELEASE-ROLLBACK.md:20-24).

## 6. 본문 칸·팩 하한 1.1.11 권고표(2026-10-30 실측)

| 칸 | 1.1.10 실제 값 | 1.1.11 권고 | 근거 | 확신 |
|---|---|---|---|---|
| `--release-seq` | 5 | **6** | A-5 | High |
| `--min-from-release-seq` | 1(체크리스트 권고 · 실제 본문 대조 = R4 때) | **1** | 계약 `0 ≤ 값 < release_seq` · 열거 폭 6 ≤ 256 | Med |
| `--state-migration` | none | **미판정 — master** | ⚠0.14.52 편입 182커밋 + 설정·장부 신규(컴퓨터 통제권 장부 · 선례 기록)가 있다. 가산이면 none · 1.1.10 은 가산 감사만 했다. 이 준비에서 전수 감사 안 함 | 미확인 |
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
| N1 | 노트 받는 방법 첫 줄 · 카톡 ① | 윈 1.1.9 기기 복구기 상태 | master | ☐ |
| N2 · K② | 노트 받는 방법 맥 줄 | 맥 실기기 자동 받기 관측 | 봉투 게시 뒤 → 기본 = 【대체 문장】 | ☐ |
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
| cu-1111-precedent — **실 크롬 실기(맥·윈 · 켜짐/꺼짐 · 탭 복원 · 경고)** | ⚠**기록 없음** | SS:1419 「§15 실기 = 절단 전 묶음으로 이월」 · TODO:235 ⑥ 미체크 · 윈 실기 ⓐ~ⓔ 에 크롬 칸 없음(검색어 chrome-enable · 크롬 재시작 · §15) |
| hook-slim 677 | **해당 없음(제외)** | 통합표 |
| 윈 복구기 675 | 있음 | 9cb4268d · R4 ACCEPT · 윈 실기 ⓐ 기준선 4·refusal 0 |
| master-send 배선 | 있음 · TODO:87 칸은 미체크 | SS:1166 격리 하네스 3/3·1/1 · 후속 판정기 SS:1178 |
| §3 맥 실기 | 발행 뒤(§7) | 재빌드 금지 판정 SS:1751 |
| §3 윈 실기 | 통과(459d0cca) · **병합 뒤 재확인 대기** | SS:1729 · 0-3 |
| §3 깨끗한 기기 새 설치 | ⚠**기록 없음** | 검색어 「깨끗한 기기」 · SS:1202 는 계획 줄 |
| §4 통합 3자 적대 검토(전체 diff · codex·Fable·agy) | ⚠**기록 없음** | TODO:40 은 계획 줄 · 통합표에 칸 없음(검색어 통합 3자 · 통합 심층) |
| §4 발견 처분표 | ⚠기록 없음(위와 같음) | — |
| 태그 레인 전용 phoenix 시험 | ⚠**c6 적 1**(그 밖 전부 통과) | §I |
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

## I. 로컬 정본 게이트(6690f9a8)

실행 = 21:56~22:45 · 머리 6690f9a8 · 격리(가짜 HOME · `CYS_*` 해제 · 운영 파일 무접촉) · 원문 = 워커 스크래치(발췌는 HANDOFF).

| 게이트 | 결과 |
|---|---|
| version-check v1.1.11 | rc 0(8곳 · 벤더 태그 동명 충돌 없음) |
| lane-parity `--strict` · `--self-test`(bash) | rc 0 · rc 0 |
| scan-pack-secrets · secret-scan --all · H-SECRET-1 | rc 0 · rc 0 · rc 0 |
| ui bun test | 3307 pass · 88 skip · 0 fail |
| tsc(`typescript@7.0.2 -p tsconfig.check.json`) | rc 0 |
| win-typecheck | rc 0 |
| cargo test --lib | 1133 passed · 0 failed |
| cargo test --bin cys | 735 passed · 0 failed |
| cargo test --bin cysd --test-threads=1 | 3222 passed · 0 failed |
| cargo test -p cys-app --bins --test-threads=1(CI 와 같은 준비) | 337 passed · 0 failed |
| 건강성 전체 | 167 PASS · 2 FAIL · 1 SKIP — 적 H-CLT-1·2 = 기존(wintask HANDOFF 게이트 줄과 같음 · 개발 맥 CLT 있음·설치본 경로 해소 차이) |
| 팩 py 전수 199 | 1차 적 7 = 환경 6(`JAVIS_ROOT`·`CYS_PROBE_RUNS` 미설정 2 · macOS 임시 경로 별칭 3 · `CYS_AGORA_ZIP_DIR` 미지정 1) + c6 1 · 환경 맞춰 재실행 = 6건 OK · **남은 적 = c6 1건(아래)** |

### ⚠태그 레인 전용 시험 적 — `test_phoenix_c6_reap.py`

| 대상 | 결과 |
|---|---|
| 6690f9a8 | 4/4 적 · line 147 `queue.list` 의 `restored` 대기 8초 초과 |
| 459d0cca(병합 전) | 2/2 적 · 같은 줄 → **이번 v1.1.10 병합 회귀 아님** |
| bad42c73(0.14.52 편입 병합) | 1/1 적 · 같은 줄 |
| 원작자 v0.14.52 | 1/1 **통과** |
| 공개 v1.1.10 트리 | 2/2 적이나 이유가 다르다 — 옛 판 시험 · 격리 데몬 15.1초 미응답(별건) · 직접 비교 불가 |
| 6690f9a8 + 임시 사본에서 line 147 한 줄 제거 | 2/3 통과 · 1회 line 168(새 좌석 재배치 8초 대기) 적 |

판독(확신 Med-High): 시험은 원작자 전제(역할 좌석 종료 → `restored_queue`)를 기다리는데 우리 포크는 1.1.5 D7⑵ 부터 역할 좌석 큐를 `parked_queues` 로 주차하고 `claim_role` 이 상속한다(`src/bin/cysd/governance.rs:34783` 주석 · `handlers.rs:905`). 0.14.52 편입이 시험을 들여오며 만난 차이다. 브랜치 CI 는 이 시험을 안 돌린다(`.github/workflows/release.yml:444` 글롭 `test_phoenix_*.py` · macOS arm64 레그 · `set -euo pipefail` → 태그 레인 적). line 168 1회 적의 원인은 미규명. 처분 = master(시험 수정 · 태그 전).


## J. 1.1.12 BACKLOG(이 준비에서 나온 것)

- [ ] **int 가지가 발행 태그를 조상으로 갖는지 게이트** — `scripts/pre-tag-ci-check.py` 에 is-ancestor 검사(최신 공개 태그 ∧ origin/main 이 태그 후보의 조상이 아니면 태그 금지 · master#e9af822d). 근거 = §H · L15.
- [ ] 태그 레인 전용 시험(`test_phoenix_*.py`)을 태그 전에 돌리는 길 — 브랜치 CI 또는 pre-tag 수동 줄(L19).
- [ ] 판번 검사(`version-check.sh`)가 `docs/index.html` 을 보지 않는다(L14).
- [ ] (윈 실기 이월 · TODO:83) `\cysd` 재등록이 LeastPrivilege 로 RunLevel Highest 를 덮음 · preflight --fix 가 `~/.claude/settings.json` 을 백업 없이 고침 · ConPTY 꽉 찬 줄 composer 사람 눈 1회 · self-update-check 새 데몬 뒤 첫 발화.
- [ ] (통합표) `d7_prime_seat_cache_never_overwrites_a_tick_value` 상한 5초 플레이크.
- [ ] 677 hook-slim(R3 REVISE) · 윈 휴지통 삭제.
