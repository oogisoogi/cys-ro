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

## 7. 원작자 파일 변경 줄(NFR-F3)
- `src-tauri/src/main.rs` +1: `viewcore::result_open, // (s79 조각 7) …`(generate_handler)
- `ui/src/main.ts` ±1: 우리 `bootViews(...)` 줄에 `focusSeat: (sid) => jumpToSurface(sid)` 덧붙임
- 그 밖 원작자 파일 0 · 데몬 0

## 8. 통합 때 master 가 볼 것
- rail(조각 6): `createResults(...).el` 을 rail 왼쪽 칸으로 · 지금 `chat/index.ts` 의 `root.insertBefore(results.el, log)` 한 줄을 rail 쪽으로 바꾸면 됨.
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
