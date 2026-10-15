# cysr 1.1.9 발행 집행 체크리스트 — 2026-10-18(일)

초안 · TICKET=cysr-119-release-prep · 2026-10-16 · worker-rel119 · 집행 = master(비가역 줄 ⛔) · U 서명 = 박사님 USB · 카톡 발송 = 박사님
⚠ 브리프·`master/TODO.md:100` 의 「10-18 토」 는 오기 — `date -j -f %Y-%m-%d 2026-10-18 +%A` = **일요일**(`DESIGN-119.md:4` 「10-18(일)」 이 맞다).
정본 순서 = `docs/RELEASE.md:17-28` · 자동 갱신 = `docs/update/HANDOFF-U3.md:59-86`(R0~R8) · 1.1.8 실제 집행 = `~/axdev/.wt/cys-118-master/docs/HANDOFF-118-r7-2026-10-11.md`(이 트리에 없음) · 1.1.8 seq 3 명령서 = `r3-r6-seq3-20261008.md`.
1.1.8 실제 순서 = main 이동 → refresh-feed → 발행 → 봉투 게시(SESSION_STATE.md:994~1001). **발행이 봉투보다 먼저**(봉투를 먼저 내면 기기가 draft 자산 = 공개 404 를 받으러 간다 · HANDOFF-118-r7:55).
실측 출발점(10-16 02:4x): 공개 latest = v1.1.8 · origin main = `6fddbffe`(= v1.1.8 커밋 + refresh-feed CI 패치 · **HEAD 조상 아님**) · 태그 v1.1.9 없음 · 보관소 `releases/3.json` 200 · `releases/4.json` 404 · stable/next 봉투 feed_rev 2 · rollout 100 · halt false.

## 0. 착수 전 — 막히면 그 자리에서 멈춤

| # | 할 것 | 확인 줄 | 상태 |
|---|---|---|---|
| 0-1 | 윈 실기 관문 W-1~W-6 결과(`docs/upstream/WIN-GATE-1110.md` · 「통과 전 라이브 금지」 master#60dc9ccf · 10-16 윈 master 집행) | 6관문 통과 기록 | **미확인**(저장소 결과 0건) |
| 0-2 | 【결정필요】 USER-MANUAL 판번 표기(이 후보 변경을 「1.1.10」 34곳 · 「1.1.9 까지」 6곳 — 1.1.9 로 나가면 한 판씩 어긋남) | 정리 커밋 또는 「그대로」 결정 | 미결 |
| 0-3 | 【결정필요】 release.yml:1296~1299 자동 본문 「앱 내 Update 버튼」(1.1.8 에서 없어진 단추) — 템플릿 수리(태그 전) 또는 draft 뒤 손 수정(1.1.8 방식) | 택일 | 미결 |
| 0-4 | 【결정필요】 `docs/index.html:36` `id="ver"` = 아직 **v1.1.7**(1.1.8 때도 안 올림) — 올리면 `:43·48·53·58` href 4줄 함께 · 시험 `ui/src/publicdocs.test.ts:577-599` · Pages 생존 **미확인** | 택일(태그 전) | 미결 |
| 0-5 | 본문 칸 값: `--min-from-release-seq` · `--notes-ko` · `--requires-min-binary-for-pack` · `PACK_MIN_BINARY`(현 `'1.1.7'` · release.yml:1409 · pack-release.yml:87 동시) | 1.1.8 = `1` · `'cysr 1.1.8 로 새로 갱신되었습니다.'` · `1.1.8` · 1.1.9 값 **미확인** | 미결 |
| 0-6 | 발행 노트·공지·카톡 초안 확정(`docs/release-119/` · 【발행 전 확인】 표시 줄 처리) | 박사님·master 확정 | 대기 |

## 1. 태그 전(가역)

| # | 명령 | 확인 줄 | 롤백 |
|---|---|---|---|
| 1-1 | 가지 `rel/1.1.9-prep`(b3a10860 + 0-2·0-3·0-4 커밋) 미러 push → CI 3런(ci-branch · windows-build · windows-health) 대기 ≈45분 | 3런 success(같은 SHA) | 가지만 — 무해 |
| 1-2 | `PATH=/usr/bin:$PATH sh scripts/version-check.sh v1.1.9` · `sh scripts/win-typecheck.sh` · `python3 scripts/pre-tag-ci-check.py --wait 60` · `bash scripts/scan-pack-secrets.sh` | 넷 다 rc 0(pre-tag rc 2 = 판정 불가 ≠ 통과 · 「58초 태그 금지」 RELEASE.md:171-230) | — |
| 1-3 | `gh variable set CYSR_RELEASE_SEQ -b 4 -R oogisoogi/cys-ro` (보관소 최댓값 3 + 1) | `gh variable list -R oogisoogi/cys-ro` = 4 | 다시 set |

## 2. 태그 → draft → 자동 갱신 재료

| # | 명령 | 확인 줄 | 롤백 |
|---|---|---|---|
| 2-1 ⛔ | `git push origin v1.1.9` (release.yml `tags: 'v*'`) | draft-guard 「✅ … draft 없음 — 진행」 · windows-health-gate 「✅」 · seq 정수 스텝 초록 · ≈53분 · draft 생성 | draft 삭제 가능 · **실패 태그 번호 재사용·태그 삭제 금지**(RELEASE-ROLLBACK.md:20-24) · 재시도 = Re-run failed jobs |
| 2-2 | R3 재료: `export CYSR_RELEASE_SEQ=4` → `bash scripts/build-macos-local.sh aarch64 dist-seq4` (+ x86_64) → `bash scripts/update/collect-inputs.sh mac <zip> macos-arm64 r3s4/inputs` · **`… macos-x64 …` 도 반드시**(생성기 필수 목록 = arm64·win 뿐 · update_common.py:31 → 빠져도 안 막힘 = 인텔 맥 자동 받기 누락) · `gh run download <RUN> -R oogisoogi/cys-ro -n update-inputs-windows-x64 -D r3s4/inputs/` | build-info `release_seq` = 4 · 윈 설치기 sha ≠ 1.1.8 | 산출물 삭제 |
| 2-3 | R4: `python3 scripts/update/make-release-json.py --component cysr --release-seq 4 … --asset macos-x64=… --build-info macos-x64=… --cdhash macos-x64=… --out r3s4/body/cysr-release-4.json` → `python3 scripts/update/release-gate.py body --body … --keyring cysjavis-pack/trusted-keys.json --archive-r2 cysr-update --expect-seq 4` | rc 0 · 본문 자산 행 3(arm64·x64·win) | 다시 생성 |
| 2-4 | R5(박사님 USB 「NO NAME」 + U 비밀번호): `bash scripts/update/sign-release.sh --body r3s4/body/cysr-release-4.json --media "/Volumes/NO NAME" --key "/Volumes/NO NAME/u.key" --out-dir r3s4/signed` → `release-gate.py body … --sig … --expect-seq 4 --stamp` | 「✅ U 의식 통과」 · gate rc 0 | 다시 서명 |
| 2-5 ⛔ | R6 보관소: `python3 scripts/update/publish-site.py archive --r2 cysr-update --file r3s4/signed/cysr-release-4.json --dry-run` → 같은 명령 `--live-check https://jarvis.godmeyou.kr` | `curl -fsS https://jarvis.godmeyou.kr/update/cysr/releases/4.json \| shasum -a 256` = 로컬 sha · `.minisig` 200 | 라이브 어긋남 = 자동 되돌림 rc 4(실패 rc 5 = 인쇄된 restore 1줄) · **보관소 불변 — 같은 seq 다른 바이트 불가** |

## 3. draft 정비 → 발행

| # | 명령 | 확인 줄 | 롤백 |
|---|---|---|---|
| 3-1 | 손대기 전 draft 사본(`~/cys-release-backup/v1.1.9-draft-before-r7/`) → 맥 zip 2종 업로드 → `make-darwin-updater-tarball.sh` → `make-darwin-update-row.py --merge` → `gh release upload … latest.json --clobber` → `python3 scripts/release-postprocess.py v1.1.9` → `… --apply` | 자산 14(13 + SHA256SUMS) | 사본에서 복원 · ⚠`make-update-manifest.sh` 금지(윈 행 소실 · HANDOFF-118-r7:81) · zsh 는 `"${PREV_TAG}:…"` |
| 3-2 | draft 본문 = `docs/release-119/RELEASE_NOTES_1.1.9.md` 「GitHub 릴리스 본문 초안」 (0-3 손 수정 갈래) · 메타 PATCH 시 `-f tag_name=v1.1.9` 동반(release.yml:85-86) | `gh release view v1.1.9 -R oogisoogi/cys-ro --json body,isDraft` | 다시 수정 · 수정 명령 원문 **미확인** |
| 3-3 | 다시 받아 검증: `python3 scripts/release-verify.py --version 1.1.9 --release-dir r7/reviewed --prev-tauri-conf prev-conf.json --prev-pack-keyring prev-keys.json` · `python3 scripts/update/release-gate.py assets --release-dir r7/reviewed --pack-manifest r7/reviewed/pack-manifest.json` | 「릴리스 검증 통과 — 자산 13종(+SHA256SUMS.txt) · 업데이터 4행 전부 서명 일치 · 맥 자산 포함」 · 팩 replay 단조 위반 = E1 최소 재서명 → SUMS 재생성(RELEASE.md:98-117) | — |
| 3-4 | `shasum -a 256 r7/reviewed/SHA256SUMS.txt` = **release_bundle_sha256**(E1 재서명 있었으면 그 뒤 값) | 기록 | — |
| 3-5 ⛔ | main 이동(불변식 = 「main = 최신 발행 태그 커밋 + CI 전용 패치」) · 옛 main 보존 가지(1.1.8 = `archive/main-pre-r7-20260814`) · `--force-with-lease` · **`6fddbffe` 다시 얹기 필수**(빠지면 refresh-feed 가 공개 호스트 403 → 「게시된 봉투 없음」 rc 0 조용한 무동작 · refresh-feed.yml:111-118) | `gh workflow list -R oogisoogi/cys-ro` 에 refresh-feed · main 트리에 `CYS_FEED_FETCH_SITE` 줄 | 보존 가지로 되돌림 · 정확 명령 **미확인** |
| 3-6 | 봉투 아티팩트(보관소 4 선행): `gh workflow run refresh-feed.yml -R oogisoogi/cys-ro -f component=cysr -f channel=stable -f release_seq=4` · 같은 꼴 `channel=next` (`first` 없음 · rollout·halt 빈 값 = 이어받음 · refresh-feed.yml:26-54) | 「Verify the NEW envelope」 초록 · 아티팩트 `envelope-cysr-stable`·`-next` · feed_rev 3(추론) | 게시 전 — 무해 · 명령 원문 **미확인**(입력 정의로 구성) |
| 3-7 | dry-run: `gh workflow run release-publish.yml -R oogisoogi/cys-ro --ref main -f tag=v1.1.9 -f release_bundle_sha256=<3-4> -f confirm=PUBLISH` | 「SHA256SUMS.txt 다이제스트: … (입력과 일치)」 · 「맥 자산: 포함」 · 「✅ dry-run 완료 — … 발행은 하지 않았다」 | 바뀌는 것 없음 |
| 3-8 ⛔ | **박사님 승인 뒤** 발행: 3-7 명령 + `-f dry_run=false` (environment `release-production` 승인 필요 여부 **미확인** — 1.1.8 불요 · 1.1.7 필요) | 로그 「✅ 공개 발행 완료 — tag_name=v1.1.9 · isDraft=false」 · 공개 SUMS 13줄 OK · `releases/latest/download/latest.json` version 1.1.9 · 행 4 | ①`gh release edit v1.1.8 -R oogisoogi/cys-ro --tag v1.1.8 --latest` ②`gh release edit v1.1.9 -R oogisoogi/cys-ro --tag v1.1.9 --draft=true` · 삭제 = 최후·오너 지시만 · tag_name 리셋 = PATCH `{"tag_name":"v1.1.9"}`(RELEASE-ROLLBACK.md:53-130) |
| 3-9 ⛔ | 봉투 게시(stable·next 각각 · 먼저 `--dry-run` 1회): `python3 scripts/update/publish-site.py envelope --r2 cysr-update --file <art-stable>/env.json --cys <1.1.9 cys 바이너리> --live-check https://jarvis.godmeyou.kr` · next 같은 꼴 | `for f in cysr/stable.json cysr/stable.json.minisig cysr/next.json cysr/next.json.minisig; do printf '%s ' "$f"; curl -fsS "https://jarvis.godmeyou.kr/update/$f" \| shasum -a 256 \| cut -c1-64; done` = 아티팩트 sha 4 · 1.1.8 기기 `cys self-update --check --json` = 새 판(seq 4) 있음 쪽 결과(정확 문구 **미확인** — 1.1.8 발행 때 실측은 게시 전 「unreachable」 rc 3 → 게시 후 「uptodate」 rc 0 · HANDOFF-118-r7:136-138) | live-check 어긋남 = 자동 되돌림 rc 4/5 · 같은 rev 다른 내용 재게시 금지 · 비상 = refresh-feed `-f halt=true` → 게시(선례 **미확인**) · 이미 받은 기기는 못 되돌림 = 더 높은 판으로만(폐기문 = 사건 때만 R-RITUAL.md) |

## 4. 발행 뒤(사이트·설치·알림)

| # | 할 것 | 확인 줄 | 롤백 |
|---|---|---|---|
| 4-1 ⛔ | 설치기 핀 1.1.8 → 1.1.9(판·크기·sha256·CDHash 를 **발행 자산에서 다시 재서** · `install-master/bootstrap.sh:146·161-162·165·178-180` · `bootstrap.ps1:140·152·153` · 작업트리 `~/axdev/.wt/hab-r8-119pre`) → `PUBLISH_CONFIRM=yes bash tools/publish-snapshot.sh --src . --dest ~/axdev/jarvis-install --push --terms-check tests/public-terms-check.sh --terms-list …` | 「SNAPSHOT-OK · 적중 0 · 삭제 (없음)」 · 1.1.9 핀 커밋 절차 **미확인**(1.1.8 = 5184260) | 이전 핀 커밋으로 |
| 4-2 ⛔ | 사이트(ai-jarvis): 설치 사본 6파일 바이트 동기 → `docs/release-119/site/SITE-119-notice-draft.md` 손댈 자리 7 → `bash site/test/gate.sh` → `bash web/build-web.sh` → `cd web && wrangler deploy` · `bash web-install/deploy.sh --go` | GATE=PASS · check-dist-cmds PASS · `/notice/2026-10-18/` 200 · 띠 2곳 1.1.9 · 「최신 = 1.1.8」 잔존 0(배포 직후 첫 조회는 옛 값일 수 있음 · web/README.md:18-21) | 이전 커밋 재배포 |
| 4-3 | 카톡 문안 `docs/release-119/KAKAO-119-notice.md` → 라이브 공지와 대조 → 박사님 전달(발송 = 박사님) | 링크 4개 200 · `#reinstall` 앵커 | — |
| 4-4 | 실기기 자동 받기 첫 관측(1.1.8 맥 1 · 윈 1): 어댑터 연결 · 유휴 → 다음 6시간 점검 뒤 「자비스가 새 판으로 바뀌었어요」 알림 · `cysr --version` = 1.1.9 | 관측 전이면 공지·카톡의 「알아서 받습니다」 = 대체 문장 | — |

## 5. 미확인 모음(집행 전 master 확정)

1. 윈 W-1~W-6 결과 2. main 이동 정확 명령 3. refresh-feed 1.1.9 명령 원문(위 3-6 은 입력 정의로 구성) 4. draft 본문 수정 명령 5. 본문 칸 4값·PACK_MIN_BINARY 6. x64 build-info 수집 시 arm64 맥 Rosetta 경고 처리(HANDOFF-118-r7:90-93 함정 10) 7. `release-production` 승인 필요 여부 8. 설치기 1.1.9 핀 커밋 절차 9. docs/index.html Pages 생존 10. 캐너리(R8 · DESIGN-AUTOUPDATE-118.md:650-653) 1.1.9 시행 여부 11. 10-19(월) 09:20 launchd `com.jarvis.cys-ro-refresh-feed` 주간 발화 = dispatch 만 · 게시는 사람 손(3-9 와 같은 날 겹침 주의).
