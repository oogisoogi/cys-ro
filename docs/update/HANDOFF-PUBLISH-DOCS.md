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

## §0-4 4판 지시(master#141c5b48 · 2026-10-07 · 원문 그대로 · ★순환 선행)
【4판 지시 · TICKET=cysr-118-publish-docs · ★순환 선행】 3판 판정: 게이트 = lead 진행 중 · 적대 = **agy 3R 수렴 아니오(0·0·MINOR 1)** + **Opus 3R 수렴 아니오(BLOCK 0 · MAJOR 1 · MINOR 6 · 2R = 해소 9 · 부분 1(m3) · 이월 1(m7))**. 원문 = 네 트리 docs/update/REVIEW-PD-agy-3r.md · REVIEW-PD-opus-3r.md(ignored).
★절차: 네 CTX 63% → **먼저 이 지시 본문을 HANDOFF-PUBLISH-DOCS.md §0-4 「4판 지시(master#이 메시지)」 로 그대로 옮겨 커밋** → `cys cycle-agent` 순환 요청을 [순환 통보]로 CSO 에(재개 줄 = 「TICKET=cysr-118-publish-docs 4판 · HANDOFF §0-4 ①~⑥ 집행 → 전수 · 미러 push 1회 · 3런 success 뒤 【확인요청】」) → 후임이 집행. master 가 CSO 에 집행 허가를 같이 보낸다.
① [MAJOR·M-1] Control Center 기본 탭 `cysjavis-pack/web/office3d.html`·`office-boot.js` 명칭 미통일: 제목 「CYSJAVIS · Metaverse Office」 → cysr · 단추 「지시 전송 → cys-terminal」·상태 「cys-terminal 반영」 5곳 → cysr · 배너의 사람이 칠 명령 `cys init-pack --force` → `cysr init-pack --force`(사람이 치는 명령 = cysr 규칙) · 기계 식별자(파일명·경로·RPC 이름)는 불변. 게이트 = 수집 매니페스트에 pack web 사용자 화면 HTML/JS 추가 · HTML 검사가 `<script>` 를 통째로 지우지 말고 사용자 노출 문자열(textContent·title·label 리터럴) 검사 · `CYSJavis` 검사 대소문자 무시. 음성 대조 = 3판 트리 office3d.html 적색 실측. (팩 web 은 디렉티브 아님 — 단 팩 매니페스트·서명 대상이면 해시 갱신 절차 따르라.)
② [MINOR·m-1] README.md:106 `cys actions` 펜스 명령 머리 누락 + 인라인 코드·sudo/env 앞머리·닫는 펜스 판정 구멍 → 각 반례 1 적색.
③ [MINOR·m-2] USER-MANUAL.md:1087·1425 스크립트가 실제로 부르는 `cys` 를 `cysr` 로 오변환 → 원래 `cys` 복원(기계 호출).
④ [MINOR·m-3·m-4·m3] RELEASE.md:330 `cys.app` → 코드와 같은 `cysr.app` · :45 【미확정】 = 해소 판정 1줄 붙이거나 내부 티켓 이름 빼고 공개 문서 밖(HANDOFF)으로.
⑤ [MINOR·m-5] [SKIP·판정 제한] = stderr 만 → 시험 결과 요약에도(stdout 집계 줄) · 윈 경로도 같은 표시.
⑥ [MINOR·m-6·agy] CYS_STATE_DIR 음성 대조 = 대상 미통과 → 실제로 그 변수를 읽는 경로로 음성 대조(뮤턴트 적색 실측) · agy 「제거 목록 → 화이트리스트」 = 반박 가능(근거 1줄) 또는 채택 — 판단 근거 HANDOFF.
상한 1.5h(순환 포함) · 본 가지 push 0.

후임 첫 행동: 이 §0-4 Read → docs/update/REVIEW-PD-opus-3r.md · REVIEW-PD-agy-3r.md(ignored · 추적 금지) Read → ①~⑥ 집행. 이월 맥락: 게이트 = ui/src/publicdocs.test.ts `nameViolations`·NAME_MANIFEST·NAME_CREDITS·NAME_QUOTED_PHRASES · dept 하네스 = cysjavis-pack/bin/tests/test_dept_create_progress.py Sandbox·SandboxReapGuard · 격리 실행 = 스크래치 isoenv.sh(HOME 임시·CYS_* 제거) · 음성 대조·되돌림은 python try/finally(zsh 루프 금지) · 미러 push = `/usr/bin/git push origin HEAD:refs/heads/fix/publish-docs-118`.

## §0-3 3판 델타 (master#62af6f8e · 2026-10-07 12:00 착수 → 12:2x)
2판 적대 = agy 2R(BLOCK 0 · MAJOR 0 · MINOR 1) + Opus 2R(BLOCK 0 · MAJOR 2 · MINOR 8 · 1R 22건 = 해소 15 · 반박 타당 1 · 부분 5) · codex = 한도 0.
★정정(Opus M1): 2판 §0-2 c5 「반례 2 적색 시험」은 **틀린 진술**이었다 — 반례 시험이 codex 원 반례 「제품 이름은 'cys' 입니다」 뒤에 승인 토큰이 아닌 `'cys 터미널'` 을 덧붙여 그 덧붙인 조각에서 적색이 났고, 원문 자체는 초록이었다. 3판은 원문 그대로 적색을 실측했다(아래 ①).

| # | 지시 | 처분 | 해소 판정 실측 |
|---|---|---|---|
| ① | M1 홑따옴표 'cys' 전역 면제 | 채택 | 승인 = 정확한 조각 4개(화면 알림 문구 거울 · NAME_QUOTED_PHRASES)만 · 반례 시험 = codex 원 반례 **원문 그대로** 2문장 → 둘 다 `lines:[1]` 적색(publicdocs 「판정기 반례」) |
| ② | M2 펜스 통째 면제 · GUIDE-empty-surface 상자 6줄 | 채택 | 상자 6줄 `cysr …`(테두리 폭 유지 · 글자 수 동일) · 게이트 = 펜스 안 명령 머리(줄머리·`$ `·`→`·`;`·`&&`·`\|\|`·`\|`·`$(` 다음 · 상자 줄 │ 안) 검사 · **전수(같은 규칙 파이썬 판): 0f3e1863 = 6줄(GUIDE-empty-surface 303·305-309) → 3판 0줄** · 0f3e1863 판 그 문서 = 게이트 적색(303~309) |
| ③ | m1 「1.0.0 이전 판이면 옛 이름 cys.app」 사실 오류 | 채택 | **실측**: tauri-plugin-updater 2.10.1 `updater.rs:1238` 이 tar 최상위 이름을 버리고(`skip(1)`) `:1302` 가 기존 번들 자리(`extract_path` = 실행 중 번들)로 rename → 앱 안 갱신으로 올라온 맥은 **판과 무관하게 cys.app**. 8곳 정정(main.rs 안전모드 안내 · INSTALL 94·104·147·630 · USER-MANUAL 1987 · GUIDE-clean-reset 239 · RELEASE 15) — 「둘 다 확인」 꼴 · 공개 문서는 U4 게이트(「Update」 낱말 0)에 맞춰 「옛 판의 앱 안 갱신 단추로 새 판을 받은 맥」 |
| ④ | m2 팀 기동 「cys boot」 2곳 | 채택 | main.rs 6346·6462 = `cysr boot` · 시험 핀 12860 동기 |
| ⑤ | m3 RELEASE.md 머리말이 옛 절차를 현행으로 | 채택 | 머리 = §1 맥 CI 레그 게이트는 **잠복 레그 기록**(현행 순서가 부르지 않음) · §0-P = 현행 `pack-v*` 태그 레인(`pack-release.yml` · 승인 게이트 없이 공개 경고) · CI 이전 수동 팩 절차(앱 배지 확인 포함) 16줄 → legacy(8ba48f9e 원문) · 1.1.8 기기 팩 적용 확인법 = 【미확정】 1줄(자동 갱신 설계 정본이 이 저장소에 없음) |
| ⑥ | m4 legacy 문서에 1판 오변환 이식 | 채택 | legacy 본문 = 8ba48f9e 원문으로 재구성(5e0949ae↔8ba48f9e 줄 정렬 · 범위 7개 전부 연속) · 본문 354줄 전부 기반 파일에 그대로 있음(불일치 0) · `cysd·cys`·`cys status` 원문 |
| ⑦ | m5 CYS_ACCOUNT_DIR 누설 | 채택 | 좌석 env 실측(`CYS_CYS_BIN CYS_CYSD_BIN CYS_PACK_DIR CYS_ROLE CYS_SEAT_TOKEN CYS_SOCKET CYS_SURFACE_ID CYS_SURFACE_REF`) + cys-dept 가 읽는 CYS_* 29종 실측 → 실 경로·좌석 신원 15종 제거 목록 추가(CYS_PY·CYS_PY_ORIGIN 은 인터프리터 해소라 유지) · 음성 대조 = 없는 표지 경로 2개(CYS_ACCOUNT_DIR·CYS_STATE_DIR)를 심고 launch → 생성 0 · 뮤턴트(목록에서 뺌) = 표지 계정 폴더 생성 적색 |
| ⑧ | m6·agy 판정 불가 조용한 초록 | 채택 | `[SKIP·판정 제한]` stderr 1줄 + 모듈 끝 집계 · ps 만 막히면 대체 판정(이 gp-* 폴더를 연 프로세스 · 조상 제외 = 나·부모)으로 **계속 거둠**(시험: ps 차단에서 남긴 자식 거둠·적색·표시) · lsof 까지 막히면 판정 불가 표시(거두지 않음) |
| ⑨ | m8 게이트 구조 구멍 | 채택 | 반례 시험(전부 적색 실측): 꺾쇠 `<cys 터미널 안내>` · `<img alt="cys 로고">` · 홑따옴표 속성 `title='cys …'` · 닫히지 않은 펜스(`unclosedFenceAt` = 여는 줄) · ``` 와 ~~~ 교차 · md 태그 제거 = 실 HTML 태그 이름 목록만 · 자동 링크 `<https…>` 만 면제 |
| ⑩ | m7 build.rs:300 FileDescription 「(CYSJavis terminal)」 | 이월(master 처분) | **1.1.9 식별자 전환 티켓** — 바이너리 메타데이터 = 빌드 산출물 변경 · 이 티켓 범위 밖 |
| ⑪ | 【결정필요】 1 ws-credit | 유지(master 처분) | 게이트 허용 = 그 정확한 문자열 1개(NAME_CREDITS["ui/index.html"]) |

범위 밖(master): CLI --help·팩 지침 명령 예시 = 1.1.9.
**순환 경계(master#92293cb4 · CTX 61.9% · 12:1x)**: 3판 ①~⑪ 전부 완료·커밋. **남은 항목 = ⓐ 미러 `fix/publish-docs-118` CI 3런(ci-branch·windows-build·windows-health) success 확인 → ⓑ 【확인요청】(채택/반박 표 = 이 절 · 해소 판정 실측 = 위 표 · 「반례 2 적색」 정정 포함)**.
해소 판정: `gh run list -R oogisoogi/cys-ro --branch fix/publish-docs-118 --json headSha,name,conclusion -L 6` 에서 HEAD sha 3런이 모두 success.
시험(맥): bun 2673/0 · tsc 0 · win-typecheck 0 · cys-app 260/0 · cysd accounts:: 146/0 · pyseal census OK · default_fleet 128/128 · SandboxReapGuard 5/5 · dept 파일 격리 OK · 실 설치본 경로 + CYS_ACCOUNT_DIR 주입 OK(cysd 1=1 · 주입 경로 생성 0).

## §0-2 2판 델타 (master#0885ae7a · 2026-10-07 10:45 착수 → 11:0x)
1판 적대 = codex 1R(BLOCK 1 · MAJOR 8 · MINOR 4) + agy 1R(BLOCK 1 · MAJOR 5 · MINOR 3) 수렴 아니오 → master 채택 전건 + 별건 처분 4.
커밋 = `1d835a29`(앱 코드·워크플로) · `a5d02646`(팩 시험 ⑤) · `f01b630b`(UI ④) · `29c29859`(문서·게이트 ②③⑥⑦⑨ⓐ) · 이 문서. ★`f01b630b`·`29c29859` 한 묶음(clipath 거울쌍·명칭 매니페스트가 서로의 파일을 본다).
시험(맥): bun 2673/0 · tsc 0 · win-typecheck 0 · cys-app 260/0 · cysd accounts:: 146/0 · cys cycle_agent 14/0 · lane-parity --strict 0 · --self-test 0 · test_dept_create_progress 격리 OK · 실 설치본 경로 주입 OK(cysd 1=1) · SandboxReapGuard 3/3 · pyseal census OK · default_fleet 128/128 · 문서 계약 3종 OK.
반박 2(아래 표): agy1 BLOCK(CYSR_RELEASE_SEQ 가 정본) · ④ 중 ui/index.html:58 출발지 표기 유지(박사님 09-27 결정 결박).

### 채택/반박 표 (codex 13 · agy 9 = 22행 — master 지시 「21행(codex 12)」 대비 codex 원문 실측 13건)
| # | 출처·등급 | 지적 | 처분 | 근거·커밋 |
|---|---|---|---|---|
| c1 | codex BLOCK | main.rs 안전모드·CLI 거부문 옛 cys.app·DMG | 채택 | `1d835a29` — 962·969·2103·2120·5068 = cysr.app · DMG→zip · 시험 3 교체(translocation 2 · pull 1) |
| c2 | codex MAJOR | GUIDE-clean-reset:20 펜스 안 백틱 명령치환 | 채택 | `29c29859` — "$HOME/…" 인용 · 원인 = 블록인용 펜스(`> ```) 미인식 → 같은 꼴 전수 스캔 3건(나머지 1건 정상) |
| c3 | codex MAJOR | GUIDE:173 작업 관리자 검색 cysr | 채택 | `cys` 검색(cys·cysd·cys-app 셋) · 같은 종류 = 앱 목록 검색도 `cys`(새·옛 이름 둘 다) |
| c4 | codex MAJOR | RELEASE_NOTES_1.0.x 역사 뒤집힘·원작자 허위 | 채택 | 옛 이름 `cys` 4곳 · 원작자 문장 원문 3곳 |
| c5 | codex MAJOR | 게이트 예외 과다(홑따옴표·「출발」 줄 통째) | 채택 | 크레딧 = 파일별 정확한 문장 · 홑따옴표 = 승인 토큰 2 · 반례 2 적색 시험 |
| c6 | codex MAJOR | 수집 집합에 dist-win·1.x 노트·ui/index.html 없음 | 채택 | NAME_MANIFEST 20 + 「⊇ README 링크」 시험 · dist-win 합성 적색 |
| c7 | codex MAJOR | ps PermissionError → 오류 3건 | 채택 | `a5d02646` — 선검사 + 예외 = 판정 불가 · 권한 차단 시험 |
| c8 | codex MAJOR | RELEASE.md 원작자 절의 명령형 「현행」 | 채택 | docs/legacy/RELEASE-upstream.md 로 419줄 격리(비실행 머리) · 상단 1줄 링크 |
| c9 | codex MAJOR | ui/index.html CYSJavis Terminal·cys 터미널·cys launch-agent | 부분 채택 | `f01b630b` — 제목 cysr · launch-agent cysr · ★58 출발지 표기 유지(박사님 09-27 「도의상 출발지 표시」 · 5자리 결박 · README 정확한 문장 = 게이트 허용 등재) → 【결정필요】 |
| c10 | codex MINOR | INSTALL:168 가림 대상 cysr 오변환 | 채택 | `cys` 복원 |
| c11 | codex MINOR | main.rs:3015 「cysr 가」 · 시험이 앞부분만 | 채택 | 「cysr 이」 · 시험 = 완전 문장 2 |
| c12 | codex MINOR | main.rs:6294 cys boot exit | 채택 | 「cysr boot exit」 |
| c13 | codex MINOR | RELEASE.md:478 백틱 깨짐 | 채택 | 한 줄 코드 꼴 · 현 빌드 이름 cysr.app |
| a1 | agy BLOCK | RELEASE.md:19 CYS_RELEASE_SEQ → CYSR_ 오변환 | **반박** | 정본 = `CYSR_RELEASE_SEQ`(release.yml·build.rs·scripts 32곳 · `CYS_RELEASE_SEQ` 0곳) · 그 줄은 1판에 손으로 쓴 것(변환기 무관) — 바꾸면 릴리스 seq 가 끊긴다 |
| a2 | agy MAJOR | INSTALL:299 다중 슬래시 정규화 없음 | 채택 | 3블록 = SHELL_PATH_NORMALIZER 같은 sed 두 식 · 모의 `//`·끝 `/` = 우리 것 |
| a3 | agy MAJOR | 「출발」 줄 통째 예외 | 채택 | c5 와 같은 수리 |
| a4 | agy MAJOR | dist-win 수집 누락 | 채택 | c6 와 같은 수리 |
| a5 | agy MAJOR | CYS_ 접두 일괄 삭제 | 채택 | 원인 3변수만 · 원인 핀 뮤턴트 2 적색 |
| a6 | agy MAJOR | NOTICE 라이선스 고지 | 채택(master ⑨ⓐ 문안) | 원문 복원 + 파생 1줄 |
| a7 | agy MINOR | clipath:338 경고 cys 기준 | 채택 | 「PATH 앞의 다른 'cys' 가 cysr 설치를 가립니다」(탐침 사실 유지) · 문서 거울 2 |
| a8 | agy MINOR | 1.0.1 원작자 계정명 오변환 | 채택 | c4 와 같은 수리 |
| a9 | agy MINOR | RELEASE.md 옛 절차 본문 잔존 | 채택 | c8 와 같은 수리 |

별건 처분(master): ⓐ NOTICE = a6 · ⓑ release.yml:977 + 주석 = `1d835a29`(ci-branch 필수 실행 줄 핀·lane-parity 변이 앵커 동기 · 잠복 결함) · ⓒ main.rs 옛 주석 2 = `1d835a29` · ⓓ CLI --help·팩 지침 명령 예시 = **1.1.9 식별자 전환 티켓(이 티켓 밖)**.
【결정필요】 1: ui/index.html 출발지 표기(ws-credit 「cys 터미널에서 출발」 꼬리표 + README 문장 툴팁) — 박사님 09-27 결정과 ⑨ 「크레딧 README 1문장만」 이 충돌 · 권고 = 유지(문장은 README 정확한 1문장 · 꼬리표만 다름) · 단점 = 화면에 「cys 터미널」 4글자가 남는다.

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
