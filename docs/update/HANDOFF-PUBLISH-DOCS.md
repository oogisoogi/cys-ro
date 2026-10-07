# HANDOFF — TICKET=cysr-118-publish-docs (1.1.8 발행 전 문서·소수정 묶음)

좌석 = surface:1296(297 u4) · cwd = ~/axdev/.wt/cys-118-u4 · 가지 `docs/publish-118` off `8ba48f9e`
브리프 = `~/axdev/master/briefs/2026-10-07-cysr-118-publish-docs.md` · 발주 master#d93a6088(원장 1건 일치 07:59)
착수 2026-10-07 08:0x · 상한 3h(→ 11:0x) · 매 90분 【진행】 · 커밋 분리 = 문서 / ⑥ / ⑦
(TODO 정본 = 이 파일 §TODO — `cys todo-path` 의 WORKER_4_TODO.md 는 옛 u3 내용이라 쓰지 않는다)

## TODO (브리프 §2)
- [x] 1. 「cys.app」 35+ 전건 판독표 → 현 설치 뜻만 `cysr.app` · 옛 자리 문맥 1줄
      해소 판정: §1 판독표 행 수 = `git grep -c 'cys\.app'`(8ba48f9e · 12 파일) 합계와 일치 · 「현 설치」 행의 잔존 0
- [x] 2. dist-win/README.md · docs/RELEASE.md 우리 채널·절차로 현행화
      해소 판정: dist-win/README.md 원작자 채널 = 「옛 채널 · 따르지 않는다」 1줄만 · docs/RELEASE.md 의 cysinsight·.dmg 줄 전부가 「원작자 레인」 표시 절 안(§2-2 판정 스크립트 · 정정: 처음 적은 「grep 0」 은 이력 삭제를 뜻해 택하지 않음 — §3 참조)
- [x] 3. 내부 잔재 2(DESIGN-factory-reset.md:60 · run_bootstrap_health.py) 삭제 RPC·env·단추 이름 grep 0
      해소 판정: 삭제 이름 목록 grep 이 두 파일에서 0(이력 부기 1줄 제외)
- [x] 4. publicdocs 게이트 음성 패턴 확장 제안 + 구현 · 음성 대조 = 옛 판 문서 각 1 fail
      해소 판정: `bun test src/publicdocs.test.ts` 초록 + 8ba48f9e 판 문서로 되돌린 대조에서 새 패턴마다 적색 1
- [x] 5. ⑥ T3 벽시계 단언 완화(계약 유지) · 로컬 10회 연속 초록
      해소 판정: 10회 루프 출력 10/10 OK · 계약 단언(cap 이 spawn+kill 포함) 줄 그대로
- [x] 6. ⑦ 목 우회 원인 실측 → 수리 2 → 잔존 cysd 0 단언(내가 띄운 pid 만 종료)
      해소 판정: 시험 전후 `pgrep -f '/Applications/cys.app/.*/cysd'` 증가 0 + 새 단언 초록
- [x] 7. 맥 전수 → 미러 `fix/publish-docs-118` push → CI 3런 success
      해소 판정: `gh run list --branch fix/publish-docs-118` 3런 success
- [x] 9. ⑨ 공식 명칭 cysr 통일(master#c33d2ec7 · 범위 결정 #db5ba8ef · 상한 +2h → 13:0x)
      해소 판정: publicdocs 「공식 명칭 = cysr」 초록 + 8ba48f9e 판 문서 음성 대조 적색 · bun 전건 초록
- [x] 8. 이 파일 완성(판독표 · 변경표 · 게이트 범위 제안) → 【확인요청】
      해소 판정: 인박스 헬퍼 재독 일치

## §0 결과 한눈에 (2026-10-07 08:3x)
| 커밋 | 범위 | 검증 |
|---|---|---|
| `81b792db` | 문서(공개 6 · 운영 2 · 내부 2) + publicdocs 게이트 3종 | bun publicdocs 11/0 · 옛 판 문서 음성 대조 3/3 적색 · INSTALL 셸 블록 4종 `sh -n` 0 · 설치 블록 모의(임시 폴더) = 옛 이름 링크 = 우리 것 · 2회째 멱등 · H-SEED-U19·H-TIMEOUT-U29 PASS |
| `174c49a6` | ⑥ T3 counsel 벽시계 판별 | 로컬 10/10 · 부하(load 15 / 16코어) 10/10 · 뮤턴트 적색(5.01 ≥ 4.0) · 파일 63/0 |
| `4de1e817` | ⑦ dept 하네스 목 우회 + 거두기 | 격리 98/0 · 표지 대역 주입 98/0 기동 0(수리 전 29회 · 20 적색) · 실 설치본 경로 주입 98/0 · cysd 전후 = 운영 데몬 1개(7347) 그대로 · 원인 핀 뮤턴트 적색 |
| (이 문서) | HANDOFF | — |

전수(맥): ui bun 2670/71/0 · tsc 0 · win-typecheck 오류 0 · Rust = 아래 §4 · 미러 CI = 아래 §4.

## §1 「cys.app」 판독표 (기반 8ba48f9e · 브리프 12 파일 = 41줄 + 브리프 밖 공개 문서 4줄)
뜻: **현** = 지금 설치되는 앱 → `cysr.app` 으로 · **병기** = 옛 자리 정리 문맥 → `cysr.app`(옛 이름 `cys.app`) 로 · **옛** = 옛 자리 그 자체(그대로 · 문맥 이미 있음) · **이력** = 내부 기록(손대지 않음) · **원작자** = RELEASE.md 원작자 레인 절(절 머리 표시로 갈음)

| 파일:줄(8ba48f9e) | 뜻 | 처리 |
|---|---|---|
| README.md:101 · README.en.md:118 | 현(구조 표 앱 이름) | `cysr.app` |
| docs/INSTALL.md:3 · 81 · 120 · 132 · 149 · 151 | 현 | `cysr.app` |
| docs/INSTALL.md:288 | 현(수동 링크 SRC) | `SRC=/Applications/cysr.app/…` — ★기능 결함 수리: 옛 블록은 cysr.app 설치본에서 없는 자리로 링크를 걸었다 |
| docs/INSTALL.md:299 · 357 · 422 | 병기(링크 소유 판정 패턴) | 버튼 `BUNDLE_LINK_PATTERN`(main.rs:1462)과 같은 4패턴 — ★옛 블록은 cysr.app 링크를 남의 것으로 보아 백업·건너뜀 |
| docs/INSTALL.md:94 · 104 · 147 · 208 · 332 · 342 · 347 · 457 · 629 | 병기 | 「`cysr.app`(옛 이름 `cys.app`)」 |
| docs/RELEASE.md:255 · 256 · 299 · 383 · 447 · 464 · 480 | 원작자 | 절 머리 「원작자 레인」 표시 · 464 = release.yml 실제 경로 서술(→ §3 별건 ①) |
| docs/GUIDE-clean-reset-KR.md:241 | 현(앱 삭제 블록) | `for A in /Applications/cysr.app /Applications/cys.app` — 식별자 검사 그대로 · ★옛 블록은 cysr.app 을 못 지웠다 |
| docs/GUIDE-clean-reset-KR.md:331 · 389 | 병기 | 「cysr.app(또는 옛 이름 cys.app)」 |
| docs/DARWIN-UPDATER-LEGACY-LANE.md:30 · 68 · 69 | 옛(1.0.2 → 1.1 레거시 레인 · 30행이 「cys.app 그대로다」 문맥) | 그대로 |
| docs/CONTROL_CENTER_DESIGN.md:151 · 153 · docs/CYSR-BRAND-VERSION.md:60 · docs/FEEDBACK-MENU.md:63 | 이력(배포·빌드 기록) | 그대로 |
| docs/HANDOFF-usage-noagy.md:66 · HANDOFF-usage-two-accounts.md:116 · HANDOFF-v116-integ.md:230 | 이력 | 그대로 |
| (브리프 밖) USER-MANUAL.md:35 · 1987 · ARCHITECTURE-AND-PHILOSOPHY.md:182 | 현 | `cysr.app` |
| (브리프 밖) USER-MANUAL.md:128 | 병기 | 「`cysr.app`(또는 옛 이름 `cys.app`)」 |
| (브리프 밖) docs/plans·rebase-*-report·fix-dock·superpowers·verdict·USAGE_OBS·HANDOFF-v116-pack·docs/update/HANDOFF-U1·U3·U4 | 이력 | 그대로 |

같은 김에 고친 것(같은 「현 이름·우리 채널」 뜻): INSTALL 윈 제거 항목 이름 'cys' → 'cysr'(옛 판 'cys') · INSTALL 소스 기여 `git clone` = `oogisoogi/cys-ro`(README 와 같음 · 옛 = idoforgod/cys-terminal).

## §2 변경표 (파일:줄 × 시험 × 소요)
| 항목 | 파일 | 시험 | 소요(벽시계) |
|---|---|---|---|
| 1 cys.app | 위 §1 | publicdocs 「앱 이름 = cysr.app」 · clipath 거울쌍(INSTALL 코드블록) · 셸 `sh -n` · 링크 블록 모의 | 07:59→08:06(문서 1~4 합계) |
| 2 채널·절차 | docs/RELEASE.md:3-33(새 「현행 정본」 절 · 35행 = 옛 머리 「이력」 표시) + 절 머리 표시 8곳 · dist-win/README.md:6-8 | (운영 문서 — 게이트 밖 · 근거 = 표 「근거」 칸 실측 출처) | 〃 |
| 3 내부 잔재 | docs/DESIGN-factory-reset.md:60 · 142 · 145-146 · run_bootstrap_health.py 18줄(문구만) | H-SEED-U19 · H-TIMEOUT-U29 PASS · 삭제 이름(GONE 16종 + 「인앱 업데이트」) = DESIGN `.update-attempt.json` 1(코드 factory_reset.rs:77 목록과 같은 파일 이름 · 「1.1.8 에서 삭제됨」 부기) 외 0 | 〃 |
| 4 게이트 | ui/src/publicdocs.test.ts:67-68(cysinsight 전부) · 160-181(새 시험 2) | 11/0 · 음성 대조 3/3 적색 | 〃 |
| ⑥ | cysjavis-pack/bin/tests/test_javis_counsel.py TickCap | 위 §0 | 08:06→08:10 |
| ⑦ | cysjavis-pack/bin/tests/test_dept_create_progress.py Sandbox·SandboxReapGuard·tearDownModule | 위 §0 | 08:10→08:18 |

★⑦ 원인 확정(브리프 【미확정】 해소): 「cys-dept 가 앱 번들 절대 경로를 찾는다」가 아니라 **러너 env 의 `CYS_CYSD_BIN`·`CYS_CYS_BIN`** 이다 — cys 좌석이 모든 pane 에 그 둘을 설치본 절대 경로로 넣고(`src/lib.rs` `self_bin_pairs`) cys-dept 가 PATH 보다 먼저 쓴다(cys-dept:69-73). 같은 원인이 이미 test_team_create_u16(:109-111)·test_dept_name_guard(:170-173) 에서 고쳐져 있었고 이 파일만 이름 목록에 빠져 있었다. 원인 탐색 = 읽기 전용 서브 1기(Explore) · 결론은 표지 대역 재현(29회 → 0)으로 내가 실측.
★⑦ 소유 판정: 이름(pkill) 0 · 「이 케이스 고유 gp-* 폴더 아래 파일을 연 프로세스」(lsof +D) · 나/조상 제외 · SIGKILL 전 다시 대조. 윈·lsof 없는 곳 = 판정 불가 → 거두지 않음(원인 수리는 env 라 플랫폼 무관).
⑦ 비용: 케이스마다 lsof 1~2회 → 파일 46s → 58s(+12s).

## §3 게이트 범위 결정 제안 · 별건 (【결정필요】 후보)
- **게이트 범위(권고 = 지금 꼴 유지)**: 수집 = README(한/영)가 링크하는 .md 전부 + docs/index.html(현 7종). RELEASE.md·dist-win/README 는 운영·내부 문서라 넣지 않는다 — 넣으면 원작자 레인 이력 절을 지워야 통과한다(리베이스 대조 기록 손실). 단점: 운영 문서의 옛 이름은 사람 눈에 남는다(절 머리 표시로 완화).
- **RELEASE.md 해소 판정 정정**: TODO 2 를 처음 「grep 0」 으로 적었으나 그것은 원작자 절 삭제를 뜻해 택하지 않았다 → 맨 위 「현행 정본」 절 + 원작자 절 머리 표시로 현행화. 870줄 전면 재작성·이관(예: docs/RELEASE-UPSTREAM-LEGACY.md 로 분리)이 필요하면 master 결정.
- **별건 ① release.yml:977(코드 · 이 티켓 밖 · 미수정)**: 맥 레그의 IOReport 게이트가 `$SRC/macos/cys.app/Contents/MacOS/cysd` 를 보는데 같은 레그가 만드는 번들은 `cysr.app`(같은 파일 947행 `CYSD_BIN="$SRC/macos/cysr.app/…"`). 맥 레그는 Apple 자격 없음으로 지금 비발행이라 잠복 — 레그가 살아나는 날 「파일 없음」 적색. 수리 1줄(+ 962행 주석) = 별 티켓 권고.
- **별건 ② src-tauri/src/main.rs:4072 · 4104 주석**: 「인앱 재시작 · 인앱 업데이트는 항상 --no-install-hook」 — 동작은 「판 변경 뒤 첫 기동」 으로 그대로이고 주석 낱말만 옛것(시험 문구는 이번에 고침 · 앵커 문자열 「U-19 도달성 앵커」 는 시험이 보므로 건드리지 않음). 코드 주석이라 이 티켓 범위 밖 — 다음 코드 티켓에서.
- **공개 문구 뜻 변경 = 0**(기능 설명·정책 불변 · 이름·자리·채널만 실물에 맞춤). 단 INSTALL 수동 링크·초기화 가이드 앱 삭제 블록은 **동작이 바뀐다**(cysr.app 을 이제 제대로 다룸 = 결함 수리) — 표 §1 ★ 표시.

## §4 전수 · CI
- Rust(격리 · USER-MANUAL 이 cys·cysd 시험의 include_str 대상이라 실행 · lib / --bin cys / --bin cysd / -p cys-app) · 미러 `fix/publish-docs-118` CI 3런(ci-branch · windows-build · windows-health)
  = 결과는 **【확인요청】 인박스 줄**에 싣는다(CI 는 이 커밋 자신에 돌므로 결과를 이 문서에 다시 적으면 커밋이 바뀌어 CI 를 다시 돌려야 한다).
- 상한 3h 대비: 착수 07:59 → 3커밋 08:18 → 이 문서 08:3x.

## §5 ⑨ 공식 명칭 cysr 통일 (박사님 10-07 「우리 자비스 공식명칭은 cysr이다. 이 외 다른 명칭은 쓰지 않는다. 모든 문서를 통일한다.」)
커밋 = `4739c88a`(문서 + 게이트 + cysd 매뉴얼 핀 2) · `d1ac126b`(UI 문자열 + ui 시험 핀 + main.rs 안내 3) — ★두 커밋 한 묶음(문서 커밋 단독이면 clipath 거울쌍 고지 제목 4건 적색 · UI 커밋에서 맞물림).

**규칙(변환기 + 손 판독)**: 산문 CYSJavis·cys 터미널·cys-terminal·단독 cys → cysr(조사 보정 를→을·가→이·는→은·와→과 · 괄호 뒤 조사는 앞말 기준이라 그대로) · 사람이 치는 명령 `cys …` → `cysr …`(펜스·인라인 명령 자리만 — `pkill -x cys`·`for f in cys cysd cysr`·`which -a cys` 같은 파일 이름은 그대로) · 기계 식별자 = 백틱 · 화면 문자열 거울 = 'cys' 홑따옴표 · 원작자 크레딧 줄 = 무접촉.
**명칭이 아니라 파일 이름인 곳은 cysr 로 바꾸지 않았다**: 셸 설치 고지의 탐색 대상은 `which -a cys` 라 「다른 'cys' 가 앞을 가립니다」 등은 'cys' 를 지켰다(cysr 로 바꾸면 거짓 안내). 단추·제목·기능 이름은 cysr.

판독표(5e0949ae → 4739c88a · 열 = 바뀐 줄 · 명칭(CYSJavis·cys 터미널·cys-terminal 지운 수) · 명령(cysr … 로 바뀐 명령 자리) · 식별자(새로 백틱 친 수) · 크레딧 = README 한/영 「…에서 출발」 3줄 무접촉):

| 파일 | 줄 | 명칭 | 명령 | 식별자 |
|---|---|---|---|---|
| ARCHITECTURE-AND-PHILOSOPHY.md | 14 | 10 | 7 | 0 |
| CONTRIBUTING.md | 4 | 1 | 3 | 0 |
| NOTICE.md | 1 | 1 | 1 | 0 |
| README.en.md | 51 | 11 | 48 | 0 |
| README.md | 67 | 11 | 52 | 0 |
| USER-MANUAL.md | 235 | 6 | 204 | 0 |
| docs/GUIDE-clean-reset-KR.md | 22 | 3 | 4 | 0 |
| docs/GUIDE-empty-surface-KR.md | 42 | 1 | 37 | 0 |
| docs/GUIDE-fullauto-cycle-KR.md | 7 | 1 | 7 | 0 |
| docs/GUIDE-policy-json-KR.md | 3 | 0 | 1 | 0 |
| docs/INSTALL-Windows-KR.md | 10 | 1 | 4 | 0 |
| docs/INSTALL.md | 47 | 1 | 21 | 0 |
| docs/RELEASE.md | 24 | 4 | 15 | 0 |
| docs/RELEASE_NOTES_1.0.0.md | 2 | 3 | 0 | 0 |
| docs/RELEASE_NOTES_1.0.1.md | 6 | 3 | 0 | 2 |
| docs/RELEASE_NOTES_1.0.2.md | 5 | 3 | 0 | 0 |
| docs/index.html | 2 | 1 | 0 | 0 |

UI(`d1ac126b` · 바뀐 줄 = git show --stat 실측): clipath.ts 30줄(단추·제목·본문 + 같은 문구 주석) · usagebar.ts 11 · main.ts 5(옛 앱 이름 cys.app 안내 1 포함) · resetconfirm.ts 3 · index.html 단추 1 · feedclass·feedback_u6·feedbackmodal 각 1 · main.rs 사용자 안내 11줄(Translocation·Applications 밖 안내 cys.app → cysr.app = ★옛 이름 결함 정정 포함). 유지 = 팔레트 재기동이 주입하는 `cys launch-agent`(기계 명령 · 별칭 동작) · `[cys-app]` 로그 머리 · ws-credit(원작자 크레딧) · `cys-dept …` 명령 안내(식별자).

게이트(`ui/src/publicdocs.test.ts` 「공식 명칭 = cysr」): 공개 문서 전건(README 링크 수집 10 + index.html) — 「CYSJavis」 0 · 코드 꼴(백틱·펜스·'ASCII'·URL·링크 대상) 밖 `\bcys\b` 0 · 「출발|started from」 줄 예외. 음성 대조 = 8ba48f9e 판 문서 → CYSJavis 5 적색 · INSTALL-Windows-KR 옛 판만 → 코드 꼴 밖 cys 6줄 적색.
시험: bun 2671/0 · tsc 0 · win-typecheck 0 · cys-app 260/0 · cysd accounts:: 146/0 · cys cycle_agent 14/0 · 팩 문서 시험 5종 초록 · 앵커 깨짐 1 → 수리(USER-MANUAL #12-cysr-팩-운용).

**제외·사유**(#db5ba8ef ⑵⑶ · 변환 뒤 되돌림 69 파일): docs/RELEASE_NOTES_0.x = 원작자 판 이력(이름이 역사적으로 정확) · docs/update/* = 296·298 작업 중(병합 충돌) · 내부 HANDOFF·DESIGN·REVIEW·report·rebase·plans 등 = 이력(브리프 §1) · LICENSE 저작권 줄 = 크레딧.
되돌린 파일: docs/CONSOLE-FLICKER-R2.md · docs/CONTROL_CENTER_DESIGN.md · docs/CYSR-BRAND-VERSION.md · docs/DARWIN-UPDATER-LEGACY-LANE.md · docs/DESIGN-dept-by-conversation.md · docs/DESIGN-dept-qualified-keys-v2.md · docs/DESIGN-factory-reset.md · docs/DESIGN-noshutdown-pack-update.md · docs/DESIGN-seamless-update.md · docs/DESIGN-v116-ceo-directive-hold.md · docs/FEEDBACK-MENU.md · docs/HANDOFF-A1-2.md · docs/HANDOFF-A1-2b.md · docs/HANDOFF-usage-two-accounts.md · docs/HANDOFF-v110-integ.md · docs/HANDOFF-v110-panetitle.md · docs/HANDOFF-v111-drain.md · docs/HANDOFF-v111-restore.md · docs/HANDOFF-v112-restore.md · docs/HANDOFF-v113-dept.md · docs/HANDOFF-v113-restore.md · docs/HANDOFF-v114-dept-fd.md · docs/HANDOFF-v115-dept.md · docs/HANDOFF-v115-restore.md · docs/HANDOFF-v115r2-pack.md · docs/HANDOFF-v115r2-ui.md · docs/HANDOFF-v115r3-d7.md · docs/HANDOFF-v115r4-dbg.md · docs/HANDOFF-v115r5-t1.md · docs/HANDOFF-v115r5-t4f1.md · docs/HANDOFF-v116-app-firstrun.md · docs/HANDOFF-v116-ceo-directive-hold.md · docs/HANDOFF-v116-integ.md · docs/HANDOFF-v116-phoenix-e2e.md · docs/HANDOFF-v116-rel.md · docs/HANDOFF-v116-restart-toast.md · docs/HANDOFF-v116-restore-card-producer.md · docs/HANDOFF-v116-seat.md · docs/HANDOFF-v116-usage.md · docs/KEY-ROTATION.md · docs/MIGRATION-seed-once-state-restore.md · docs/RELEASE-ROLLBACK.md · docs/REVIEW-TRIAGE-A1-2.md · docs/REVIEW-factory-reset-simulation.md · docs/RSI_LEARNING_DESIGN.md · docs/RSI_LEARNING_DIRECTIVE.draft.md · docs/SEAT-FOLDERS.md · docs/THREAT-MODEL-mission-gate.md · docs/USAGE_OBSERVABILITY_PHASE2_PLAN.md · docs/WINDOWS-UPGRADE-ATOMICITY-CHECKLIST.md · docs/WINTEST-v116-bundle-draft.md · docs/agy-verdicts-phoenix-korean-windows-2026-09-08.md · docs/agy-verdicts-phoenix-s3-master-persist-2026-09-08.md · docs/backlog-exited-surface-auto-reap-2026-07-13.md · docs/cysjavis-editor-primitives-design.md · docs/design-layout-persistence-2026-07-20.md · docs/fix-dock-ghost-tile-2026-07-20.md · docs/impl-pane-title-numbering-2026-07-27.md · docs/installer-remedy-proposal-pythonutf8-2026-09-08.md · docs/javis-native-features-proposal-2026-06-12.md · docs/participant-formation-findings-2026-09-10.md · docs/rebase-v0.14.10-report-2026-08-02.md · docs/rebase-v0.14.27-report-2026-08-28.md · docs/rebase-v0.14.30-report-2026-09-08.md · docs/report-cys-release-first-publish-2026-09-09.md · docs/s3-master-role-not-persisted-findings-2026-09-08.md · docs/s6-windows-autostart-env-capability-2026-09-08.md · docs/upstream-pr-draft-phoenix-korean-windows-2026-09-08.md · docs/verdict-pane-title-numbering-2026-07-27.md

⑨ 별건(【결정필요】 후보): ① NOTICE.md 3행 「cys-terminal is licensed under the MIT License」 → 「cysr is licensed …」 로 바꿨다(우리 판 라이선스 서술 · 원작자 저작권 줄은 LICENSE 에 그대로) — 법적 고지 문구라 다르게 원하시면 1줄 되돌림. ② CLI `--help`(src/bin/cys.rs 의 about·예시)·팩 지침(directives) 안 `cys …` 명령 예시는 이번 범위 밖(사람 화면이지만 문서·UI 문자열 아님) — 통일하려면 별 티켓. ③ 판독표 수치는 diff 정규식 계수(도구 출력)다.
