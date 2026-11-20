# HANDOFF — TICKET=cysr-1116-s79-1119 · 화면 조각 7(결과 받기) + 조각 9(작업 화면 쪽 보조) + 1.1.17 당김 4건

- 가지 `feat/1116-s79` ← `integ/1116` dea2e1853 · 작업트리 `~/axdev/.wt/cys-1116-s79` · 지시 master#0fd97c53 · 설계 답 master#cf75d4e2(A 승인)
- push·태그·CI·발행 = 하지 않음 · 데몬 변경 0

## 1. 커밋(dea2e1853..)

| 커밋 | 무엇 |
|---|---|
| efd39e323 | 조각 7 · 조각 9 · S4-7 첫 구현 + `s79.test.ts` |
| 338e79027 | S3-7 하네스 uuid 없는 꼴 글 순서 대조 |
| 60eeac7b8 | I4 화면 게이트 캡처 기본 자리 = 작업트리 밖 |
| 40f13dcaa | cc_popover_z_gate CI 배선 + 화면 게이트 `ui/e2e/s79_gate.py` |
| c45d98f8d | 자체 검토 3건 고침(대화→작업 전환 살핌 끊김 · `.app` 열기 · 확장자 뒤 한글 조사) + F10 순서 |
| b83c60467 | **(별도 커밋 · master#cf75d4e2 조건 ③)** chat_gate E 단언 좁힘 |
| b9113f463 | codex 1R(BLOCK) 6건 처분 — Tauri `result_open` 등 |

## 2. 무엇을 만들었나

### 조각 7 결과 받기(FR-P3·P4 · 없는 파일 = 안내)
- 판정(순수) `ui/src/views/judge/results.ts`: 출처 둘 — ① 데몬 사건 `skill.run_finished {status:"done", artifact_dir}`(본부 slug 만) ② 마스터 답 글 속 **홈 아래** 절대 경로(`~/` 펼침 · 윈도 `C:\`·`/` 둘 다 · 숨은 마디 `.`·`..` = 0 · 코드 울타리 안 = 0 · 백틱 한 쌍 안 띄어쓰기 경로 통째 · 맨글은 확장자까지 이은 후보도 · 확장자 뒤 한글 조사 깎음 · 한 답 5개 상한). 답 속 경로는 **실재 확인된 것만** 카드(설명으로 쓴 경로 = 카드 0) · 스킬 폴더 = 늘(확인 중 → 없으면 「파일을 찾을 수 없어요」).
- 장부 `ui/src/views/results.ts`(ConfirmBook 과 같은 수명 = 대화 화면이 켜졌을 때): 홈 = `home_dir_path` 1회 · 실재 = `list_dir(부모)`(NFC 정규화 · 맥/윈 대소문자 무시) · 틱당 3개 확인 · 저장 `cys-chat-results`(경로·출처·시각·봤음만 · 말 원문 0자 · 50개).
- 열기·폴더 보기 = **새 Tauri 명령 `viewcore::result_open`**(우리 파일 `src-tauri/src/viewcore.rs`): 정규 경로(링크 끝까지 풂)가 정규 홈 **아래** · 홈 아래 마디에 숨은 이름 0 · 열기면 실행 꾸러미(`.app`·`.pkg` 등) 거절(`executable_confirm`) · 그 뒤 기존 `open_path`(실행형 파일 게이트 · **force 없음**)·`reveal_path`. 화면은 누르기 직전 실재 재확인(없으면 호출 0) · 신뢰 클릭만 · 실행형 거절 뒤 다시 묻지 않음.
- 그리기 `ui/src/views/chat/results.ts`: 「결과 N · 새 결과 M」 칸 + 대화 안 카드(그 경로를 말한 마스터 답 말풍선 바로 뒤) · 열기 / 폴더 보기 / 고쳐 달라고 하기(입력칸 **앞에** 「이 결과를 고쳐 주세요 — <경로>」 · 쓰던 글은 뒤에 그대로) / 없는 파일 = 「마스터에게 물어보기」(입력칸 준비 · 보내기는 사람).
- 배선: `core.ts`(장부 생성 · 사건·slug·세션 레코드·poll 틱에 덧붙임) · `chat/index.ts` 두 줄(칸을 **대화 위**에 끼움 · `paint` 끝에 `results.paint()`). ★**rail 끼우기는 통합 때 master** — `results.el` 을 조각 6 rail 의 왼쪽 칸으로 옮기면 됨(그리기 함수는 자리와 무관).

### 조각 9 작업 화면 쪽 보조(FR-C7 · 초안 알림 띠)
- `judge/workband.ts`(순수 · 띠 하나 = 확인 먼저 · 다음 초안) · `work/band.ts`(그리기) · `work/adapter.ts` extra 훅 · `views/index.ts` 배선 · **원작자 `ui/src/main.ts` = 우리 `bootViews(...)` 줄에 `focusSeat: (sid) => jumpToSurface(sid)` 덧붙임(1줄 바뀜)**.
- 확인 띠 = 대화 화면 띠와 **같은 판정**(`confirm.band()` 그대로) · 행동 = 「마스터 창에서 답하기」(마스터 좌석 포커스 · 다른 탭이면 그 탭으로) / 도우미 허락 = 「도우미 창에서 답하기」 · 초안 띠 = 「대화 화면에 쓰다 만 말이 있어요. 마스터 창에는 넣지 않았어요」 → 대화 화면.
- 자료: `core.watchStart/watchStop` — **대화 화면을 이번 실행에서 켠 적이 있을 때만** 작업 화면에서 3초 poll(조회 = feed_list·org_status·chat_transcript) · **살피는 중엔 붙잡은 말 쓰기 0**(poll·pump 둘 다) · 켠 적 없으면 조회 0(tickrec_gate · s79_gate A).
- registry 는 새 화면을 먼저 띄우고 옛 화면을 내린다 → 대화 화면 `detach` 가 살핌을 끄지 않게 막음(`watchOnly` 면 무시 · 끄는 것은 `watchStop`).
- 띠가 보이면 `#body-row` 높이를 띠(48px)만큼 줄임 — `views.css` 의 `.wv-band:not([hidden]) + #body-row`(원작자 style.css 무변경).

### 1.1.17 당김
- **S4-7 F7**: 띠 물음에 「이 물음은 끝났어요」(신뢰 클릭 · 마스터에게 보내는 것 0 · 기록 `cys-chat-decisions` decision=dismiss · 물음 글 0자) · 내린 뒤 해결 없이 같은 글로 다시 물으면 다시 보임(`Question.last`) · 세션 바뀌면 비움.
- **S4-7 F10**: 보던 항목이 사라져 다른 항목이 같은 자리에 저절로 오면 2초(`SWAP_GUARD_MS`) 동안 거절·내림 = 처리 0 + 「보던 항목이 처리되어 다른 요청이 그 자리에 왔어요」 · 「다음」 왕복에도 유지 · 「무엇을 보기」 펼침(의도된 누름) = 풀림 · 허락은 펼침이 먼저라 허락 검사 다음에 둠.
- **S3-7**: msgharness uuid 없는 꼴 = 같은 글의 「전달됨 이상」 수 ≤ 기록 수 · 보낸 순서 k 번째 말 ∈ 기록 순 앞 k 개 주인 · 빈 검사 방지 계수(`noUuidChecked` 106,884).
- **I4**: 화면 게이트 13개 캡처 기본 자리 = `GATE_EVIDENCE_DIR` 또는 `TMPDIR/cys-gate-evidence`(`statusboard_gate.evidence_dir`) · 커밋할 증거는 인자/환경값으로. 게이트를 돌려도 `docs/` 변화 0(실측).
- **cc_popover_z_gate CI 배선**: `ci-branch.yml` ui-check 에 setup-python → 번들 빌드 → playwright 1.60.0 + `--only-shell chromium` → 게이트(캡처 = RUNNER_TEMP) · timeout 15→25분 · `MUST_RUN_TOKENS[ci-branch]` 에 실행 줄 토큰 핀.

## 3. 시험 숫자(기준 dea2e1853 → HEAD)

| 무엇 | 기준 | HEAD |
|---|---|---|
| bun test(ui) | 3747 pass · 88 skip · 0 fail · 123 파일 | **3782 · 88 · 0 · 124 파일**(+35 = s79.test) |
| tsc(typescript 7.0.2 check) | rc 0 | rc 0(출력 0줄) |
| cargo `-p cys-app --bins viewcore` | 11 | **12/0**(+ result_target_confines_to_canonical_home) |
| 화면 게이트(최종 번들) | — | tickrec 28 · chat 62 · confirm 37(원본 그대로) · **s79 46** · cc_popover_z 4 = 전부 PASS |
| 그 밖 게이트(중간 번들 · 회귀 확인) | — | statusboard·focus·race·seatrows·seatgroup·nodept·restart·grid·pillar·cc_button·restart_confirm PASS · baseline(기준판 번들 인자 필요)·wsbar(풀 chromium 필요) = 실행 조건 미충족(판정 아님) |
| 레인 게이트(ci-branch 팩 스위트 레인 대조 파이썬 추출) | — | rc 0 · 음성 대조 2(새 실행 줄 삭제 · `if: false`) = rc 1 · 사유에 토큰 이름 |
| `lane-parity-rehearsal.sh --strict` / `--self-test` | — | rc 0 / rc 0 |
| ci-branch 팩 단계 그대로(격리 env · cargo 없는 10스텝) | — | §6 표 |

- tickrec.test 「최악 장면」 5초 상한 붉음 1회 = 부하 30 대 병렬 실행 때뿐 · 단독 재실행 기준판 4.31s·HEAD 2.85s 둘 다 21/0 · 최종 전체 실행 0 fail.

## 4. 뮤턴트(새 시험이 대상을 잡는가)

| # | 뮤턴트 | 결과 |
|---|---|---|
| M1 | 결과 열기 신뢰 클릭 검사 뺌 | e2e 붉음 3(대본 클릭 open 0 단언) |
| M2 | 누르기 직전 실재 재확인 뺌 | bun 붉음 1 |
| M3 | 작업 화면 살핌 중 poll 보내기 막음 뺌 | bun 붉음 · e2e E2 붉음(0→1) |
| M4 | 대화 화면 안 켰어도 watchStart | bun 붉음 · e2e A 붉음(조회 9) |
| M5 | F10 2초 막음 뺌 | e2e 붉음(G) |
| M6 | 사람이 내린 물음 거르기 뺌 | bun 붉음 |
| M7 | 울타리 안 경로 받음 | bun 붉음 |
| M8 | 숨은 마디 허용 | bun 붉음 |
| M9 | 초안 띠를 확인 띠보다 먼저 | bun 붉음 |
| M10 | 결과 칸을 안 끼움 | e2e 붉음 |
| R1 | 대화 화면 내림이 살핌을 끔(전환 순서) | bun 붉음 |
| R2 | `.app` 열기 허용 | bun 붉음 |
| R3 | 확장자 뒤 한글 조사 안 깎음 | bun 붉음 |
| R4(Rust) | `result_target` = 글 경로 그대로(링크 안 풂) | cargo 붉음(링크 → 홈 밖 단언) |
| P1 | pump 의 살핌 중 막음 뺌 | **생존** — 대역에서는 앞 말 차례 규칙(after_prev)이 먼저 막아 도달 길을 못 만듦 · 방어만 둠(codex 지적 경로) |
| H1 | 같은 글 겹침 막기 끔(S3-7 검사 대상 확인) | 하네스 붉음 — 「uuid 없는 꼴: 다른 말의 레코드에 짝지음(글 순서 대조)」 |
| H2 | uuid 없는 레코드를 최신 말에 짝 | **생존** — 같은 글 겹침 막기 때문에 같은 글 두 말이 동시에 기다리는 일이 하네스에서 없음(S3-7 구멍은 겹침 막기가 이미 닫고 있고 새 검사는 그 막기가 풀릴 때의 회귀 그물) |

## 5. codex 1R(gpt-5.6-sol · high) — 판정 BLOCK → 전부 처분

| 지적 | 처분 |
|---|---|
| blocking 홈 안 링크 → 홈 밖 `.app` = 글 검사 통과 · OS open | **고침** — Tauri `result_open` 정규 경로 가둠 + 실행 꾸러미 거절(R4 뮤턴트 붉음) |
| major 앞 말 전달 중 작업 화면 → pump 가 둘째 말 보냄 | **고침**(pump 에도 막음) · 대역 도달 불가(P1 생존 · 위) |
| major F10 「다음」 왕복으로 보호 우회 | **고침**(arrived 유지 · s79_gate G2) |
| major F7 내린 뒤 같은 글 다시 물음이 안 보임 | **고침**(`Question.last`) |
| major 띄어쓰기 경로 잘림 | **고침**(백틱 통째 · 확장자 이은 후보 — 맨글 둘 다 후보 · 실재가 고름) |
| minor 맥 대소문자·NFC | **고침** |
- codex 가 정본 판정 JSON 을 `~/.cys/…` 에 못 씀(샌드박스) → 작업트리 `.review-verdict-cysr-1.1.16-r1-reviewer1.json` 에 둠(**커밋 안 함 · 지워도 됨**). 원문 = 스크래치 `codex-r1.out`. 고친 뒤 2R 은 안 함(📌).

## 6. ci-branch 팩 단계(브리프 = 로컬 21개가 아니라 워크플로 스텝 그대로)

방법: `ci-branch.yml` 에서 `cysjavis-pack/bin/tests`·`run_bootstrap_health` 를 부르는 cargo 없는 스텝 10개를 YAML 로 떼어 `env -i HOME/TMPDIR/RUNNER_TEMP=짧은 임시 · PATH=파이썬 3.12 심링크:/usr/bin:/bin:/usr/sbin:/sbin` 로 실행(스크래치 `pack/step*.sh` · `packrun.sh`). **이 가지의 팩 파일 변경 = 0**(`git diff dea2e1853..HEAD -- cysjavis-pack` 빈칸).

### 6-1. 스텝별(1차 = 부하 20~38 · 2·3차 = 저부하 재실행 · 운영 공지 master#fff8d726 ② 대로 시간 문턱 붉음은 기준판 단독 대조)

| 스텝 | 1차(HEAD) | 저부하 재실행(HEAD) | 기준판 대조 | 판정 |
|---|---|---|---|---|
| 01 게이트 대장 회귀 + flake N=5 | rc 0 | — | — | 통과 |
| 02 선언 파서 2언어 파리티 | rc 1(0초 · 격리 HOME 에 rustup 기본 툴체인 없음) | **rc 0**(RUSTUP_HOME 넘김 · 1065종 일치 · 39+38 OK) | — | 통과(1차 = 환경) |
| 03 유령 todo·선언 소비자 묶음 | rc 1(test_role_authority_shell H6b · 1122초) | 2차 rc 1(test_pyseal_census — **내 1차 step08 이 작업트리에 남긴 health-full.json** · 지우고 3차) · 3차 rc 1(test_hook_r34 RCF-3·WIN-2 = 1초 시한 3.2초) | role_authority_shell: 기준판도 붉음(4건 · 다른 항목) / hook_r34 단독 2회: 기준판 2·1 FAIL(같은 이름) · HEAD 1·**0** FAIL | 부하 흔들림(팩 파일 차이 0) · 오염은 내 실행 탓 → 지움 |
| 04 레인·상태 격리군 | rc 0 | — | — | 통과 |
| 05 자원 게이트·함대CPU·역할 좌석 | rc 0 | — | — | 통과 |
| 06 수용 검체 4종 | rc 0 | — | — | 통과 |
| 07 todo 스캔 2언어 파리티 | rc 0 | — | — | 통과 |
| 08 부트 건강성 전 검체 | rc 1 = H-SECRET-1(**내 결함** · s79.test 의 홈 경로 견본에 더미 아닌 이름) + H-CLT-1·2 | 2차 rc 1 = B-1(test_role_bootstrap_hook 훅 시간 초과 · 부하 19) + H-CLT-1·2 | H-SECRET-1 → **고침 116da5367**(secret-scan --all clean) · role_bootstrap_hook 단독 = 기준판·HEAD 둘 다 rc 0 · H-CLT-1·2 = integ 인계 기준선(이 기기 python 해소) | 내 결함 1 고침 · 나머지 기준선·흔들림 |
| 09 phoenix host-level | rc 1(0초 · rustup 환경) | 2차 rc 1(c6_reap S5 bounded observation timed out) · **3차 rc 0** | 기준판 저부하 rc 1(AssertionError) | 흔들림(기준판도 붉음) |
| 10 우분투 루프 그대로(154종) | rc 1(test_session_start_hook 3a·3b) | 2차 rc 1(pyseal_census = 같은 오염) · 3차 rc 1(test_hook_r34 = 03 과 같은 시한 시험) | session_start_hook 단독 = 기준판·HEAD 둘 다 rc 0 · hook_r34 = 위 | 흔들림 · 오염 해소 |

- 이 가지가 팩 쪽에 낸 결함 = **H-SECRET-1 하나**(고침). 나머지 붉음은 전부 ① 환경(rustup) ② 내 실행의 작업트리 오염(health-full.json · 지움) ③ 시간 문턱 시험의 부하 흔들림(기준판 같은 사유 또는 HEAD 단독 초록)으로 갈림.
- codex 판정 JSON(`.review-verdict-…json`)도 작업트리 밖(스크래치)으로 옮김 — 작업트리 git 무시 대상 밖 파일 0.

## 6-2. codex 2R(412fdc32e = BLOCK · 원문 master/reports/verify/codex-1120/s79-r2.md) — master#c48208b6 처분대로

| # | 지적 | 처분 | 시험 |
|---|---|---|---|
| 1 | TOCTOU(정규화 뒤 조상 경로를 링크로 바꿔치기) | **고치지 않음 · 문서**(같은 사용자 권한 로컬 프로세스 = 이미 무엇이든 열 수 있음) — 아래 「알려진 한계」 + `viewcore.rs result_open` 주석 | — |
| 2 | URL·바로가기·스크립트 유형 열기 통과 | **고침** — 열기 거절 확장자 한 목록(Rust `OPEN_REFUSED_EXT` = TS `OPEN_REFUSED_EXT` · 57종 · 양 OS 공통 · 대소문자 무시) | bun 「열기 거절 확장자 = Rust viewcore OPEN_REFUSED_EXT 와 같은 목록」 · 「「열기」가 곧 실행인 꾸러미(.app 등) = 막음 …」 · cargo `result_target_confines_to_canonical_home`(webloc·url·lnk·sh·ps1 … 23종) |
| 3 | 홈 아래 네트워크 · UNC 홈 | **윈도만 고침** — 정규 경로가 `\\?\UNC\`·`\\server` 꼴 = `network_path` 거절 · 맥 마운트 판별 = 한계 | cargo 같은 시험(is_network_path 4꼴) · bun 「Tauri 가 홈 밖·숨은 폴더로 이어짐을 거절 … → 안내」(network_path → MSG_NETWORK) |
| 4 | 띄어쓰기 경로의 앞 토막까지 후보 | **고침** — 확장자까지 이은 전체 경로만(3낱말까지) · 4~8낱말 뒤 확장자 = 긴 경로로 보고 후보 0 · 앞 토막 단독 금지 | bun 「띄어쓰기 있는 경로 …」(기대값 고침 · 3낱말 · 4낱말+ = 0) |
| 5 | 같은 글 다시 물음에 옛 uuid | **고침** — 다시 물을 때 uuid 를 새 것으로(없으면 그대로) | bun 「(codex 2R minor) 같은 글로 다시 물으면 대화 자리(uuid)는 가장 최근 물음으로」 |

## 6-3. 독립 검증 2272 VERDICT(BLOCK 조건부 · 원문 ~/axdev/workers/cysr-1116-s79-verify-1119/VERDICT.md) — master#beb80154 처분대로

| # | 지적 | 처분 | 시험 · 뮤턴트 |
|---|---|---|---|
| V1 | 맥 Finder 가명(이름 `행사안내.html` 이어도)·`.fileloc` → 홈 밖 앱 실행 · `.webloc` → URL | **고침 · 설계 뒤집기**: `result_open` 열기 = **허용 목록**(`viewcore::open_verdict` — 꾸러미 아닌 폴더 · 보통 파일 ∧ OPEN_ALLOWED_EXT(웹 페이지·문서·그림 24종) ∧ 가명 아님) · 그 밖 = `executable_confirm`(폴더 보기만) · 가명 = 파일 머리 `book\0\0\0\0mark` 또는 FinderInfo kIsAlias(0x8000) | cargo `viewcore::tests::result_target_confines_to_canonical_home`(가명 이름 행사안내.html · 가명 무확장자 · .fileloc · .webloc · FinderInfo 옛 가명) · 뮤턴트 허용 목록 끔 = 붉음 · 가명 검사 끔 = 붉음 |
| V2 | 윈 거부 목록 밖 처리기(`.url`·`.appref-ms`·`.settingcontent-ms` …) | **고침**(같은 허용 목록이 덮음) · 윈 숨김·시스템 속성 파일 = 거절(cfg(windows) 1줄 · 윈 실기 0) | cargo 같은 시험(2272 윈 목록 27종 = 거절) |
| — | 허용 목록 한 정의 | Rust `OPEN_ALLOWED_EXT` = TS `OPEN_ALLOWED_EXT`(= PAGE·DOC·IMAGE) · 화면 미리 거르기 `openAllowedName` · 거부 목록 57종은 **남김**(이유 = 꾸러미 **폴더**(.app 등) 판정에 필요 + 이중 방어) | bun 「열기 허용 목록 = Rust viewcore OPEN_ALLOWED_EXT 와 같은 목록(한 정의 · 독립 검증 V1·V2)」(두 목록 겹침 0 포함) |
| V3 | 작업 화면 살핌 중 chat_send 1건(deliver 재조회 대기 중 전환) | **고침** — 재조회 await 뒤 · 쓰기 전 `watchOnly` 면 붙잡음(`work_view`) · 대화 화면 돌아오면 poll 이 보냄 | bun 「(독립 검증 V3) deliver 가 쓰기 직전 재조회를 기다리는 사이 작업 화면으로 → chat_send 0 …」 · 뮤턴트 막음 끔 = 붉음 |
| V4 | 살핌 중 list_dir(넷째 조회 종류) · chat_gate 가 3종만 셈 | **고침** — `ResultBook.paused`(살핌 중 실재 확인 0 · 후보는 모아 둠) · chat_gate 대역 = **모든 invoke 종류** 계수 · 기준 창(대화 화면 켜기 전 30초)을 뺀 증가분 중 허용 3종 밖 = 붉음 | bun 「(독립 검증 V4) 작업 화면 살핌 중(paused) = list_dir 0 …」 · 뮤턴트 paused 끔 = 붉음 · chat_gate 「★작업 화면 30초 = 모든 invoke 종류 대조 …」 PASS(org_status 10 · feed_list 10 · 밖 0) |
| V5 | S3-7 검사가 집합 소속만 | **고침** — k 번째 말 = k 번째 기록 주인(자리 대조) | msgharness 200 시나리오 wrong 0 |
| V6 | results.ts 머리 주석 낡음 | **고침** | — |

### 알려진 한계(이번 처분으로 남긴 것)
- **TOCTOU**: `result_open` 은 정규 경로 **이름**을 기존 `open_path`/`reveal_path` 에 넘긴다 — 그 사이 같은 사용자 권한의 로컬 프로세스가 조상 폴더를 링크·정션으로 바꾸면 다른 대상이 열릴 수 있다. 그런 프로세스는 이미 사용자 권한으로 무엇이든 열 수 있어 새 권한을 주지 않는다(master#c48208b6 ①).
- **맥 홈 아래 네트워크 마운트**: 판별하지 않음(드묾 · 윈도 UNC 만 거절).
- **4낱말 넘는 띄어쓰기 맨글 경로**: 카드 0(놓침) — 마스터가 백틱으로 감싸 쓰면 받음.
- (6-3 뒤) 열기는 허용 목록이 정본 — 허용 목록 종류(예 `.html`·`.docx`)라도 그 파일 자체의 내용(스크립트·매크로)은 처리기 몫(브라우저·오피스의 보호에 기댐). 사람이 일부러 만든 가명 결과도 「폴더 보기」만 된다.

## 6-4. codex 3R(8112be285 = BLOCK · 원문 master/reports/verify/codex-1120/s79-r3.md) — master#717eeef1 처분대로(후임 좌석 worker-1116s79b)

| # | 지적 | 처분 | 시험 · 뮤턴트 |
|---|---|---|---|
| ① | 이름 바꾼 앱 꾸러미 폴더(`Report.pdf` · Info.plist APPL)를 `open` 이 실행 | **고침(이중)** — 폴더 「열기」 = **파일 관리자로만**(`viewcore::folder_open_command` = 맥 `/usr/bin/open -a Finder <폴더>` · 윈 `explorer <폴더>` · 그 밖 `xdg-open`) · LaunchServices 기본 열기 0 · 덧붙여 폴더 안 `Contents/Info.plist`·`Contents/PkgInfo`·`Contents/MacOS` 중 하나라도 있으면 `executable_confirm`(폴더 보기만) · `result_open` = `open_plan`(판정 · 실행 0) → `result_open_in`(집행) 으로 나눔 | cargo `renamed_app_bundle_folder_is_refused_and_folders_open_in_file_manager_only`(Report.pdf APPL 꾸러미 · 실행 파일 = 표식 파일 만듦 → 계획 거절 · 집행 거절 · 1.5초 뒤 표식 0 · 표지 하나씩 · 폴더 보기 됨 · 보통 폴더 = Folder · 맥 명령 = `-a Finder` · 집행 길 소스 대조) · 뮤턴트 RM1(표지 검사 뺌)·RM2(Info.plist 만)·RM3(맥 기본 open)·RM4(Folder 갈래 = open_path) = 전부 붉음 |
| ② | `ResultBook.act`(list_dir await 뒤)·`ConfirmBook.decide`(feed/org await 뒤)가 화면을 다시 안 봄 | **고침** — 한 도우미 `ChatCore.onChatScreen`(= `!watchOnly`)을 deliver·두 장부가 함께 씀(장부 deps `onChat`) · act = 실재 재확인 뒤 살핌 중이면 `result_open` 0 + 「작업 화면으로 옮겨서 열지 않았어요」 · decide = recheck 뒤·`confirm_reply` 앞에서 살핌 중이면 0 · 기록 outcome `work_view` | bun 「(codex 3R ②) 결과 열기 — list_dir 대기 중 작업 화면 → result_open 0 …」(core 배선 그대로) · confirm.test 「(codex 3R ②) 직접 허락 — org 재조회 대기 중 작업 화면 → confirm_reply 0 …」 · 뮤턴트 TM1·TM2·TM7(deliver) 붉음 · **TM3(ResultBook 에 도우미 안 넘김) = 생존** — core 가 같은 자리에서 세우는 `paused` 가 같은 막음을 한다(이중 · 대상 누락 아님) |
| ③ | watchStart 가 attach 뒤에 watchOnly/paused 를 세움 → 전환 순간 default_socket_slug·home_dir_path · 게이트는 전환 뒤를 기준으로 셈 | **고침** — 켜기 한 곳 `attachAs(watch)` = 표지를 **먼저** 세움 · 살핌(watch) = 사건 구독·세션 읽기·poll 만(default_socket_slug·home_dir_path 0 · 대화 화면에서 받아 둔 값) · `startListening` = 살핌 중 소켓 이름 모르면 조회·구독 0 · chat_gate E = 계수 기준을 **전환 전**으로(창 길이 30초 그대로 = 100ms + 29.9초) | confirm.test 「(codex 3R ③) … 대화 → 작업 · 대화 → 다른 화면 → 작업 둘 다 0」(harness 의 defaultSlug 도 앱처럼 default_socket_slug 로 셈) · s79.test 「(codex 3R ③) 살핌 중 = default_socket_slug 0(이름 못 받은 경우)」 · 뮤턴트 TM4·TM5·TM6·TM8(표지를 켜기 뒤로) 붉음 · **chat_gate 음성 대조**: 옛 core.ts 번들 = FAIL `{'default_socket_slug': 1}` → 새 번들 PASS |
| ④ | 윈 매핑 네트워크 드라이브(`\\?\H:\…`)가 UNC 검사를 지나감 | **고침** — `result_target` 윈도 갈래: `drive_root(정규 대상)` → `windrive::is_remote_drive` = `GetDriveTypeW(뿌리) == DRIVE_REMOTE(4)` 면 `network_path` 거절(홈 가둠 전) · `extern "system"` 직접 선언(std 만 · 새 의존 0) | cargo `windows_mapped_network_drive_is_refused_static`(drive_root 7꼴 · result_target 소스 대조 · windrive 선언 대조) · **교차 타입체크** = `// ---- windrive 시작/끝` 표지 사이 + drive_root 를 떼어 `rustc --target x86_64-pc-windows-msvc --crate-type lib --emit=metadata` rc 0 · 음성 대조(`GetDriveTypeW(w)` 타입 틀림) rc 1 E0308 · 뮤턴트 RM5(검사 뺌)·RM6(값 3)·RM7(`\\?\` 안 벗김) 붉음 · 윈 실기 0 |
| ⑤ | HTML·SVG 능동 내용(외부 요청·리다이렉트) | **고치지 않음 · 한계 문서**(아래 「알려진 한계」) · 결과 카드 안내 문구 덧붙이지 않음 | — |

- **대조 탐침(① · 고치기 전 · 스크래치 · 표식 파일만 만드는 셸 실행 파일)**: 이 기기(macOS 26 · arm64)에서 ⒜ 이름만 바꾼 APPL 꾸러미 `Report.pdf`(번들 비트 없음)에 `/usr/bin/open` = **실행 0**(표식 0 · `kMDItemContentType = public.folder` · Finder 가 폴더로 엶) ⒝ 번들 비트(FinderInfo 0x2000)까지 켠 꼴 = **실행 0**(표식 0 · 콘텐츠 종류 dyn · LaunchServices 등록 0). ∴ codex ① 의 실행 경로는 이 기기에서 **재현되지 않았다**(다른 판·설정에서의 가능성은 열어 둠) — master 처분대로 방어는 그대로 넣음. 그래서 cargo 반례 시험의 「붉음」은 표식 파일이 아니라 계획·명령 단언에서 난다(옛 코드는 open_verdict = Ok · 기본 open).
- 탐침 부작용: ⒜ 때 Finder 창 1개가 떴다(폴더를 지워 닫음). 미리보기(Preview)는 어제부터 떠 있던 것(pid 687 · 우리가 띄운 것 아님).

### 6-4 시험 숫자(기준 8112be285 → 95224ec7f)

| 무엇 | 기준 | 뒤 |
|---|---|---|
| bun test(ui) | 3787 pass · 88 skip · 0 fail · 124 파일 | **3791 · 88 · 0 · 124 파일**(+4 = s79.test 2 · confirm.test 2) |
| tsc(`bun x --package typescript@7.0.2 tsc -p tsconfig.check.json`) | — | rc 0 · 음성 대조(타입 오류 1줄) rc 1 TS2322 |
| cargo `-p cys-app --bins viewcore` | 12 | **14/0** |
| cargo `-p cys-app --bins` 전체 | (기준 실행 안 함 · 바뀐 파일 = viewcore.rs 하나 · 그 시험 12→14) | **351/0 + 2 무시** |
| 윈 교차 타입체크(windrive 토막) | — | rc 0 · 음성 대조 rc 1 |
| 화면 게이트 4종(최종 번들) | tickrec 28 · chat 63 · confirm 37 · s79 46 | **tickrec 28 · chat 63 · confirm 37 · s79 46 = 전부 PASS** |
| 작업 화면 회귀 게이트(최종 번들 · 06:59~07:21) | — | cc_popover_z · statusboard · focus · race · seatrows · seatgroup · nodept · restart · grid · pillar · cc_button · restart_confirm = **12개 전부 PASS**(rc 0) |
| secret-scan `--all` | — | clean(2193 파일) |
| 팩 | `git diff 8112be285.. -- cysjavis-pack` = 빈칸 | (팩 단계 재실행 안 함 · 팩 파일 변경 0) |

### 알려진 한계(6-4 뒤 덧붙임)
- **HTML·SVG 능동 내용**(master#717eeef1 ⑤): 허용 목록의 `.html`·`.htm`·`.svg` 결과를 열면 브라우저가 그 안의 스크립트·외부 요청·리다이렉트를 처리한다 — 그 파일은 사람이 맡긴 일의 산출물이고, Finder 에서 더블클릭하는 것과 같은 동작이며, 우리 화면이 더하는 바깥 유출은 0이다. 결과 카드에 「웹 페이지는 브라우저로 열려요」 같은 안내는 넣지 않았다.
- 폴더 열기의 Finder 동작: `open -a Finder <꾸러미 표지 없는 폴더>` 는 탐침하지 않았다(실제 창이 뜸) — 꾸러미 표지가 있으면 그 전에 거절되므로 Finder 가 꾸러미를 받는 길은 없다.

## 6-5. codex 4R(3b445dfbd = BLOCK · 원문 master/reports/verify/codex-1120/s79-r4.md) — master#1031d7aa 처분대로(마지막 회차 · 5R 없음)

master 판정: 두 건 다 「같은 사용자 권한의 에이전트가 이미 할 수 있는 일」 이상을 열지 않음 = 배포 차단 사유 아님 · 고치는 값이 싸서 고침.

| # | 지적 | 처분 | 시험 · 뮤턴트 |
|---|---|---|---|
| ① | File·Reveal 이 맨 이름 `open`/`explorer` 를 spawn(맥 = PATH 탐색 · 윈 = 실행 파일 폴더 먼저) | **고침** — `result_open_in` = `open_plan` → `launch_command`(실행기 `launcher()` = 맥 `/usr/bin/open` · 윈 `explorer_path_from(GetWindowsDirectoryW, SystemRoot)` → 없으면 `C:\Windows` 뒤 `\explorer.exe` · 드라이브 절대 꼴만 받음 · 그 밖 `/usr/bin/xdg-open`) · 원작자 `open_path`/`reveal_path` 는 더 부르지 않음(main.rs 무변경) · 옛 open_path 의 **실행 비트 게이트**는 `open_verdict` 로 옮김 · 맥 인자 불변(파일 `open <파일>` · 보기 `open -R <항목>` · 폴더 `open -a Finder <폴더>`) | cargo `launchers_are_absolute_paths_and_no_bare_name_spawn`(세 계획 = 같은 절대 실행기 · 운영 코드 `Command::new(` = `launcher()` 하나뿐 · 맨 이름 문자열 0 · 윈 경로 고르기 4꼴 · 맥 인자) · `result_target_confines_to_canonical_home` 에 실행 비트 `실행.html` 거절 · 뮤턴트 Q1(맥 맨 이름)·Q2(File = 옛 open_path)·Q3(맨 이름 하나 더)·Q4(상대 값 받음)·Q5(SystemRoot 먼저)·Q11(실행 비트 뺌)·Q12(보기 -R 뺌) 붉음 |
| ② | 윈 `이름.{CLSID}` 폴더 · desktop.ini `CLSID=` 폴더 = 탐색기가 COM 이름공간·네트워크로 엮음 | **고침** — 윈 폴더 「열기」 = 들어가지 않고 `explorer.exe /select,<폴더>`(상위 폴더에서 골라 보여 줌 · 보기와 통일) · `open_plan` 윈도 갈래(reveal 보다 **먼저** = 열기·보기 둘 다): 정규 대상과 그 조상(홈 아래만) 중 `is_clsid_name`(`.{8-4-4-4-12 16진}` 끝 · 대소문자 무시) 또는 `desktop_ini_has_clsid`(읽기만 · 앞 64KB · UTF-8/UTF-16LE BOM · 키 `CLSID`·`CLSID2` · 못 읽으면 거절 쪽) = `executable_confirm` · 맥·리눅스 = 판정 안 부름(동작 불변) | cargo `windows_shell_junction_folders_are_refused`(CLSID 이름 2 · 아닌 꼴 6 · 정션 자신·그 안 파일 · desktop.ini 5꼴 · 홈 자신 desktop.ini = 안 봄 · 맥 = Folder 그대로 · open_plan 소스 대조) · 뮤턴트 Q6(이름 판정 끔)·Q7(desktop.ini 끔)·Q8(BOM 해석 뺌)·Q9(조상 안 봄)·Q10b(검사를 reveal 뒤로) 붉음 |

- 뮤턴트 = 12/12 붉음(첫 Q10 은 뮤턴트 자체가 검사를 옮기지 않아 무효 → Q10b 로 다시 · 첫 Q11 생존 → 실행 비트 시험 덧붙인 뒤 붉음).
- **윈 교차 타입체크** = windrive + drive_root + OpenPlan + 정션 판정·explorer_path_from·launcher·launch_command 토막을 `rustc --target x86_64-pc-windows-msvc --crate-type lib --emit=metadata` rc 0 · 음성 대조(`GetWindowsDirectoryW` 크기 인자 타입 틀림) rc 1 E0308 · **윈 실기 0**(`/select,` 가 정션 폴더를 엮지 않는지 · GetWindowsDirectoryW 실제 값 = 미실측).

### 6-5 시험 숫자(기준 3b445dfbd → 이 커밋)

| 무엇 | 기준 | 뒤 |
|---|---|---|
| cargo `-p cys-app --bins viewcore` | 14 | **16/0** |
| cargo `-p cys-app --bins` 전체 | 351/0 + 2 무시 | **353/0 + 2 무시** · viewcore 경고 0 |
| bun test(ui · 이 회차 `ui/` 변경 0) | 3791/0 | 전체 묶음 2회 = 3790 pass · 1 fail(tickrec 「최악 장면」 5초 상한 · 7.6초 · 부하 23~26) · 그 파일 단독 2회 = 21/0 — §3 에 적힌 부하성 흔들림과 같은 시험 |
| secret-scan `--all` | clean | clean(2193 파일) |
| 화면 게이트 | (6-4 PASS) | 다시 안 돌림 — 이 회차 `ui/` 변경 0 · 바뀐 것은 Rust 실행 길뿐(화면 게이트 = 브라우저 대역이라 result_open 을 실제로 안 부름) |

### 알려진 한계(6-5 뒤 덧붙임)
- **같은 사용자 경계**: 결과 열기의 막음(맨 이름 실행기 · 셸 정션 · TOCTOU · 처리기의 능동 내용)은 모두 「같은 사용자 권한으로 이미 무엇이든 실행·열 수 있는 로컬 에이전트·프로세스」를 상대로는 새 권한을 막는 경계가 아니다 — 쉬운 화면의 누름 하나가 그 위에 **더하는** 실행·유출을 0 으로 만드는 것이 목표이고, 그 이상(같은 사용자 안의 격리)은 이 기능의 범위 밖이다(master#1031d7aa).

## 7. 원작자 파일 변경 줄(NFR-F3)
- `src-tauri/src/main.rs` +1: `viewcore::result_open, // (s79 조각 7) …`(generate_handler)
- `ui/src/main.ts` ±1: 우리 `bootViews(...)` 줄에 `focusSeat: (sid) => jumpToSurface(sid)` 덧붙임
- 그 밖 원작자 파일 0 · 데몬 0

## 8. 통합 때 master 가 볼 것
- rail(조각 6): `createResults(...).el` 을 rail 왼쪽 칸으로 · 지금 `chat/index.ts` 의 `root.insertBefore(results.el, log)` 한 줄을 rail 쪽으로 바꾸면 됨.
- (6-4) `core.ts` attach 몸통이 `attachAs(watch)` 로 옮겨감(attach = attachAs(false) · watchStart = attachAs(true)) — 통합 때 attach 에 덧붙인 줄은 attachAs 안에 넣고 살핌 중에도 돌아야 하는지 갈라 둘 것. 장부 deps 에 `onChat` 칸(ConfirmBook·ResultBook).
- 겹칠 자리: `core.ts` attach(구독 콜백·slug then 을 둘로 펼침) · `poll()` `scanStep` 다음 줄 · `readTranscript` onTail 다음 줄 · `chat/band.ts` itemNode·paint · `views.css` 끝 덧붙임 · `chat_gate.py` E 장면(별도 커밋 b83c60467).
- `src-tauri/binaries`·`runtime`·`resources/pack*` 는 형제 작업트리에서 복제한 시험용(전부 git 무시 대상).

## 9. 📌 덧붙임(내가 범위 밖이라 안 한 것)
- 결과 미리보기(쪽 그림 · PRD S5 「미리보기」) — 안 넣음(파일 읽기 길이 새로 필요).
- 대화 화면을 안 켠 실행 동안 끝난 스킬 결과는 못 받음(사건 구독이 대화 화면 수명에 묶임 = S4-3·I3 와 같은 뿌리).
- 맨글 띄어쓰기 경로는 두 후보(이은 것 + 끊긴 것)가 둘 다 실재하면 카드 둘.
- `result_open` 윈도 실기 미확인(`\\?\` 머리 벗기기 · x64 실행 금지라 정적으로만).
- CI 새 스텝 실측 0(CI 금지) — 첫 실행에서 headless shell 받기 시간·`chromium.launch()` 기본 경로 확인 필요.
- s79_gate·chat_gate·confirm_gate 는 여전히 CI 미배선(이번 배선 = cc_popover_z 하나만 지시).
- codex 2R(고친 뒤) 안 함.
