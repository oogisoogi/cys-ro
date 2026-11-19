# HANDOFF — 화면 조각 6 + 6b(맡긴 일·팀 = 대화 화면 왼쪽 메뉴바 + 팀별 기계 장치) · TICKET=cysr-1116-s6-1119

- 좌석 worker-1116s6 · 작업트리 `~/axdev/.wt/cys-1116-s6` · 가지 `feat/1116-s6` ← dea2e1853 · 브리프 master#4a485888(원장 대조 성립)
- 추가 공지 반영: master#4f286501(부하 — cargo JOBS 4 · 시간 문턱 시험 단독 재실행 대조) · master#d0920326 → master#ebd716dc(codex 한도 — **codex 1R = master 대기열**)
- push · 태그 · CI · gh 쓰기 · 서명 · 발행 · 앱 교체 · 실사용 데몬/좌석 접촉 = 0(시험 = `env -i` 격리 HOME/TMPDIR)
- 편성: 화면·팩 = 이 좌석 · 데몬 6b = 이 좌석 내부 fork(같은 작업트리 · 커밋 2개) — 독립 검증 좌석은 master 몫

## 1. 커밋(순서대로)

| 커밋 | 무엇 |
|---|---|
| c57d60ac9 | feat(ui) 대화 화면 왼쪽 메뉴바 — 맡긴 일·팀·부서(조각 6) · 빠른 답 · 부서 가이드 |
| 5d3ca2fc6 | feat(pack) `javis_dept_request.py promote-check`·`promote-decline` + 닫기 카드 「하던 일이 있으면 그 자리에서 멈춰요.」 |
| 4dfe954d0 | **pack(팩 지침 별도 커밋)** MASTER_DIRECTIVE 「★ 대화 화면 표식」 절 + MASTER_CORE·CEO_CORE 요지 1줄 · CEO_TEMPLATE 재합성 · 해시표 재생성 · 바이트 예산 상향 ⑦ |
| 8c90f7860 | feat(cysd) 조각 6b — ⑦ 대기열 몫 · ⑧ 도우미 상한 · ⑨ 정지 스위치 · ⑩ 【진행】 묶음 · team.stats · CLI |
| a91898964 | test(ui) `ui/e2e/rail_gate.py`(수동 · CI 미배선) |
| ff9e38262 | docs `docs/1116-s6/DAEMON-6b.md`(데몬 설계 · 바뀐 원작자 줄 · 시험 · 뮤턴트 · 한계) |
| (이 커밋) | HANDOFF · `docs/1116-s6/codex-r1-prompt.md`(codex 1R 질문지 — master 대기열용) · TODO |

## 2. 무엇을 만들었나

### 2-1. 화면(조각 6 · P2-DESIGN §11 조각 6 행 · §5-1 · §5-4 · §16-5 · §16-6 · 개정 E1·E2)
- 대화 화면이 `.cv-wrap` 한 줄 = 왼쪽 `aside.cv-rail`(320px · 시안 P2-mock `rail()`) + 가운데 대화. 폭 600px 이하만 숨김(시안 선 그대로 · 윈 노트북 배율 125~150% 의 CSS 폭 1024~1100 에서 보임 — rail_gate A2 실측).
- 마스터 카드(HEALTH_LABEL 그대로) · **맡긴 일 N**: 카드 = 같은 팀 안 같은 일감 이름 좌석 묶음(제목 = 자기보고 task 첫 줄, 없으면 데몬 제목 마지막 조각 = seatrows.seatName) · 상태 ●일하는 중 / ◆기다림 / ▲확인 필요(승인 대기) / ○조용함(10분 · FR-P2 — 출력·자기보고 둘 다 10분 넘게 없으면 일하는 중으로 칠하지 않음) / 「이 일의 소식을 못 받고 있어요」(관측 없음) · 마지막 소식(방금·N분 전) · 도우미 N명 · 좌석 번호·모델·CTX 0(FR-P1).
- **팀 = 작업 화면 묶음 탭과 같은 모델**: `seatrows.buildSeatRows` + `seatgroup.effectiveGroup`(데몬이 정한 값 > 앱 기록 `cys-seat-group` > 생성 폴더) — main.ts `refreshSeatRows` 와 같은 길 · 팀 머리는 묶음 2개 이상만(`showGroupHeaders` = 탭 줄 판정 · FR-L1) · 팀 머리 요약(▲확인 필요 n > ●일하는 중 n > ○조용함 > ◆기다림).
- **「팀 만드는 중」**(FR-L3 · §5-1 개정 E1): 결속 세션 기록의 마스터 답 줄머리 `⟪팀 만드는 중: <팀>⟫`(코드 울타리 밖 · 정리 = cleanGroupName) → 점선 카드 · 본부 slug 의 `surface.group.changed` 또는 3초 목록에 그 이름 묶음이 생기면 내림 · 30분 상한(설계 목표값 · 실측 없음).
- **부서 N 줄**(개정 E2 · 진실원 `list_depts` · 팀으로 세지 않음) · `⟪부서로 올리는 중: <팀>⟫` → 「부서로 올리는 중」 카드(등록부에 그 이름이 생기면 부서 줄로).
- **빠른 답**(§5-4 D7 · §16-5 ①): 마지막 말인 마스터 답에 `⟪팀 제안⟫` → 「네, 팀으로 나눠 주세요」·「아니요, 지금처럼 해 주세요」 · `⟪부서 제안: <팀>⟫` → 「네, 부서로 올려 주세요」·「지금은 아니요」 · 신뢰 클릭만 · 누르면 단추 글을 **그대로** 일반 사람 보내기 길(`act.submit`)로(화면 판정 0 · 문턱·원자 제출 그대로) · 보낸 뒤 마지막 말이 아니게 되어 단추 사라짐.
- **부서 가이드**(§16-5 ② 원문 5줄 · 3번 줄 운영체제별 = 닫기 카드 `keep` 분기와 같은 판정): 처음 부서가 생기고 `cys-dept-guide-seen` 이 없으면 대화 목록에 1회(「알겠어요」 = 기록) · 머리 줄 「부서 안내」 단추 = 늘 다시 보기. 꼬리 문구만 실제 자리에 맞춤(「오른쪽 위 「부서 안내」 단추로 다시 볼 수 있어요」 — 시안은 「메뉴 → 부서 안내」 · 이 화면엔 메뉴가 없음).
- **결과 자리**: `[data-rail=results]` 만 두고 비면 숨김 · 판정 0(조각 7 몫).
- 조회: 대화 화면이 켜져 있을 때만 core 3초 조회 뒤 `list_surfaces`(본부 · 상한 500ms · 실패 = 직전 값) 1회 · `list_depts` 처음 + 30초마다 · **쓰기 직전 재조회(fetchFresh)에는 넣지 않음**(사람 말 쓰기 시간 예산 불변). 작업 화면만 쓰면 invoke 0(tickrec_gate 기준 sha 같음).
- 파일: `ui/src/views/judge/rail.ts`(순수) · `ui/src/views/rail.ts`(장부) · `ui/src/views/chat/rail.ts`(그리기) · `chat/index.ts`·`core.ts`(배선 · core = +16줄) · `views.css`(끝에 덧붙임).

### 2-2. 팩 도구(§16-3 · §16-4 ①)
- `promote-check --team <팀> [--stats-file]` → `{team, ask, R, C, D, cooldown_until, thresholds, reason}` · 판정 = 이 도구만 · 데이터 = `cys team-stats`(맥·윈 같은 길) · R(60분 보고) ≥ 4 ∧ C(working) ≥ 2 ∧ D(7일 중 날) ≥ 3 · 하루 1회(전체 `last_ask_day`) · 거절 쉼 14일(그 팀만) · reason ∈ threshold_met / below_threshold / cooldown / asked_today / no_such_team / stats_unavailable / state_unwritable(앞 4개 밖 = 늘 ask:false · 안전 쪽) · D 는 본 날을 `~/.cys/dept-requests/promote-cooldown.json` 에 더해 데몬 재시작 너머로 이어 감.
- `promote-decline --team <팀>` → 14일 쉼 + §16-5 「아니요」 뒤 답 문구(`say`).
- 닫기 카드(`render_close_card`) 끝 「닫을까요?」 앞에 「하던 일이 있으면 그 자리에서 멈춰요.」.

### 2-3. 팩 지침(별도 커밋 4dfe954d0)
- MASTER_DIRECTIVE 「★ 대화 화면 표식」: 표식 꼴 1줄(`⟪부서 제안: <팀 이름>⟫` · `⟪부서로 올리는 중: <팀 이름>⟫`) + 1문단(팀 = 도우미를 작업 폴더 아래 `<팀 이름>` 하위 폴더에서 띄우고 `cys seat-group` — §5-4 📌 「팀 폴더 = 작업 폴더 아래 하위 폴더」 결정 · 갈래 셋 이상 ∧ 팀 ≤ 1 → 시작 전 `⟪팀 제안⟫`(D7) · 팀 일 한 단락 끝 = promote-check → ask:true 일 때만 `⟪부서 제안⟫`(문턱 눈대중·덮어쓰기 금지 · 장점 2~3줄 + 사용량 1줄 + 닫을 수 있음 1줄 · `⟪팀 제안⟫` 과 겹쳐 내지 않음) · 「지금은 아니요」 = promote-decline · 부서 닫은 뒤 「남은 일을 팀으로 다시 맡을까요?」 1회).
- ★**CORE 요지 1줄씩(MASTER_CORE · CEO_CORE)** — 이 절은 §14 뒤 ★ 절이라 **주입 목차 밖**이고 새(startup) 마스터에게는 원문이 닿지 않았다(조각 4 표식도 같은 처지였음 · `core_inject.py session` 출력에 절 이름 0 실측). 요지에 표식 꼴·도구를 실어 닿게 함. 주입 크기(브리지 1,500자 가정): MASTER 8,076 → 8,141(낙하 0) · CEO 8,401 → 8,268(「절 목차」 낙하 = 이 커밋 전부터 같음 · 📌 P3).
- 바이트 예산 ⑦(`test_cso_directive_rev` 역사 주석): MASTER 86,625 → 87,810 · CEO 102,111 → 103,296(+1,185 B · 새 절 0).
- 합성기 `gen_ceo_template.py --check` GREEN · `gen_released_directive_hashes.py --check` OK(지금 판 1개 교체 = 45bb7848f 와 같은 꼴).

### 2-4. 데몬(조각 6b · 상세 = `docs/1116-s6/DAEMON-6b.md`)
- 팀 판정 `team::team_of` = 명시 묶음 > 생성 cwd 마지막 이름(앱 folderKey 규칙) · master*·cso* 제외 · ⑦⑩ = 살아 있는 팀 ≥ 2 일 때만(팀 1개 = 지금 동작).
- ⑦ `queue_full_team`(사건 `team.queue_full`) · `CYS_TEAM_QUEUE_SHARE`=30 · 같은 큐 잠금 안 · 전체 100 그대로.
- ⑧ `team_worker_limit_exceeded`(사건 `team.worker_limit_denied`) · `CYS_MAX_TEAM_WORKERS`=0(무제한).
- ⑨ `surface.group_pause {group, paused}`(호출자 = set_group 게이트) · 사건 `team.paused`/`team.resumed` · CLI `cys seat-group-pause|seat-group-resume <팀>` · 그 팀 좌석 큐 배달 동결 + 그 팀 → 마스터 항목 보류 · 보류가 머리면 안정 재배치(다른 팀 먼저 · 팀 안 순서 유지) · 직접 보내기·운영자 강제 배달 통과.
- ⑩ `cys send --queued --progress`(`kind:"progress"`) · `CYS_PROGRESS_BUNDLE_SECS`=600 · `【진행 묶음】 <팀> N건` + `[i/N · 발신] 원문` 1건 · 급한 머리표 5종 = 즉시.
- `team.stats` / `cys team-stats`(JSON 한 줄) · 메모리 링 7일 · 팀별 5000.

## 3. 원작자 파일 바뀐 줄(NFR-F3 예외 · 브리프 「데몬 변경 허용」)
- 표 전문 = `docs/1116-s6/DAEMON-6b.md` §2(8c90f7860 기준 `git diff -U0 dea2e1853..8c90f7860`): `src/bin/cysd/main.rs`(mod 2줄) · `state.rs`(필드 1 + 초기값 1) · `handlers.rs`(enqueue_bound_body 4곳 · surface.create ⑧ · send_text queued 3곳 · 새 메서드 2) · `governance.rs`(TeamPre·team_pre_delivery · deliver_head_locked 판정·보류 거름·묶음·병합 끊기·묶음 본문) · `src/bin/cys.rs`(--progress · 새 동사 3 · 소스 핀 앵커 문자열 5곳 = 뜻 불변).
- 화면·팩 쪽 원작자 파일 변경 = 0(views/·팩은 우리 파일 · `views.css` 우리 파일 · 원작자 style.css·main.ts 무변경).

## 4. 시험 — 숫자 전후

| 대상 | 기준선 | 이 가지 | 비고 |
|---|---|---|---|
| bun test(ui 전체) | 3747 · 88 skip · 0(dea2e1853 통합 값) | **3771 · 88 · 1** | +25 = 새 시험(judge/rail 18 · rail 7) · 붉음 1 = `tickrec.test.ts` 최악 장면 덤프 **5초 시한**(부하 35 · 5.57s) → 부하 5.3 단독 재실행 **21/0**(첫 전체 실행 2 붉음 = 부하 35 · 이름 미기록) |
| `bun test ./src/views` | 287 · 0 | **312 · 0**(부하 낮을 때) | — |
| tsc(typescript 7.0.2 · tsconfig.check) | rc 0 | **rc 0** | 음성 대조(일부러 넣은 TS2322 를 잡음) 확인 |
| cargo `--bin cysd` | 3308 · 0 · 17 | **3348 · 3 · 17** | 붉음 3 = seatkeep `handshake_timeout`(부하 15~19) → 단독(부하 14.8) **5/0** · 이 가지 seat_proc 무접촉 · 통합 인계서 §4-1 과 같은 이름·사유 · 새 17 |
| cargo `--bin cys` | 765 · 0 · 2 | **796 · 0 · 2** | 스택 시험(j3·aid_s5·cli_parse_*) 전부 ok |
| cargo `--lib` | 1256 · 0 · 3 | **1268 · 0 · 3** | lib 무접촉(수 차이 = dea2e1853 까지 들어온 시험) |
| test_dept_request.py | (112) | **120 · 0** | +8 |
| javis_dept_request self-test | PASS | PASS 21 | — |
| test_cso_directive_rev · bootv2_doc_contract · event_inject · core_inject | — | **75/0 · ALL PASS · ALL PASS · ALL PASS** | core_inject E1 startup 8,209 ≤ 9,000 |
| gen_ceo_template --check · gen_released_directive_hashes --check | — | GREEN · OK | — |
| **ci-branch.yml 팩 4단계 그대로**(`유령 todo…` 루프 · 레인·상태 격리군 · 자원 게이트… · 수용 검체 4종 · 추출 스크립트로 run 블록 원문 실행) | — | 1회차(부하 24 · set -e): 루프 31번째 `test_session_start_hook` 19b 붉음에서 멈춤 → 단독(부하 6.2) 초록 · 2회차(실패 계속 · 164 시험): **붉음 2** — `test_pyseal_negative_specimen` = UNMEASURED(비번들 python 없음 · **기준선 dea2e1853 같은 사유 rc 2**) · `test_role_authority_shell` = 단독 HEAD·기준선 둘 다 rc 0 · 나머지 3단계 rc 0 | 19b 는 2회차 전체 실행에서 초록 |
| 화면 게이트 15종(79a56603 판과 같은 목록) | 앞 좌석 값 | **전부 PASS · 같은 수**(race 108 · focus 72 · seatrows 75 · pillar 77 · seatgroup 8 · rolereuse 11 · stty 7 · nodept 16 · restart 6 · hidden_block 18 · chat 59 · confirm 37 · cc_popover_z 4 · restart_confirm 13 · tickrec 34) | tickrec 꺼짐 = 기준 번들(dea2e1853) sha `308dd2b91f9a` 같음 · invoke 1088 = 1088 |
| **rail_gate.py(새)** | — | **PASS 25 / 0** | §2-1 전부 · 캡처 스크래치 |

### 4-1. 뮤턴트
- 화면 15개(rail 시험 2파일): 14 붉음(이름까지 의도한 시험) · 1 생존 = 「마스터·운영 좌석 제외」 `continue` — buildSeatRows 가 이미 고정 좌석을 묶음에서 빼므로 **등가 뮤턴트**(동작 같음 · 일을 덜 하는 줄).
- 데몬 7개(m1~m7): 7 전부 의도한 시험(DAEMON-6b.md §3-1).
- 팩: 문턱 셋 각각 빼기 = `test_each_threshold_is_needed` 하위 시험 3이 판정(시험 안 subTest) · 닫기 줄 = `TestCloseCardStopsWork`.

## 5. 수용 기준 표(§11 조각 6·6b 행)

| 기준 | 판정 | 근거 |
|---|---|---|
| FR-P1 카드(제목·단계·마지막 소식·도우미 N · 번호 숨김) | 통과 | judge/rail.test · rail_gate A |
| FR-P2 조용함(10분) | 통과 | judge/rail.test 카드 상태 · 뮤턴트 |
| FR-L1 팀 2+ 만 팀 층 · 팀 머리 요약 | 통과 | judge/rail.test · rail_gate B |
| FR-L2·D7 마스터 먼저 제안(지침 + 빠른 답) | 통과(화면·지침) · **P1 실물 1회 = 냄** | rail_gate D · 지침 4dfe954d0 · P1(master#fbf34c5a · `docs/1116-s6/P1-measure.md`): 헤드리스 Opus 5.5 high · 주입 = CORE 요지만(★ 절 원문 주입 0) · 「갈래 셋」 1턴째 답 첫 줄 `⟪팀 제안⟫` → 화면 판정 quickReplyOf = team(단추 2) · 요지 1줄 안내대로 원문 절을 먼저 읽음 |
| P1 팀 폴더에서 띄움 · seat-group | **P1 실물 1회 = 함** | 3턴째(자원 게이트 = 시험 대역): 팀 폴더 `교회홈페이지/홈페이지개편팀/`(작업 폴더 아래 하위 폴더) · `launch-agent --role worker --cwd <팀 폴더>` ×3 · `seat-group --surface 11·12·13 홈페이지개편팀` ×3 · 2턴째 진짜 게이트는 이 기계 창 37 > 18 로 거절(정상) |
| P1 ⟪팀 만드는 중: <팀>⟫ | **P1 실물 1회 = 안 냄** → 「팀 만드는 중」 카드 안 뜸 | 3턴 세션 기록 전수 표식 = ⟪팀 제안⟫ 1 · ⟪확인 요청⟫ 3 뿐 · 원인 가설(확신도 중): 한 턴 도구 연속이라 도구 앞 글 없음 · 지침이 「어느 답에·언제」를 말하지 않음 · 끝 답이 막힘 보고 · **지침 고침안(제안만 · 코드 0)** = 「팀을 만들기로 한 그 답의 첫 줄(도구보다 먼저 · 막혀도 씀)」 — P1-measure.md §고침안 |
| FR-L3 「팀 만드는 중」 → 진행(묶음 사건) | 통과(대역) | rail_gate C · rail.test |
| 개정 E1 팀 이름·도우미 = 작업 화면 묶음 탭(같은 seatrows 모델 · bun 대조) | 통과 | judge/rail.test 첫 묶음 · rail_gate B(site·home = 작업 화면 이름) |
| 부서 카드는 팀으로 세지 않음 · 부서 N 줄 | 통과 | judge/rail.test · rail_gate E |
| 마스터 1기(새 마스터 좌석 0) | 통과(설계) | 지침 「새 마스터 0」 · 화면은 좌석을 만들지 않음 |
| 빠른 답 = 원문 그대로 1건 · 표식 없으면 카드 0 | 통과 | rail_gate D · quickReplyOf 시험 |
| §16 제안 카드 단추·가이드(운영체제별)·「부서 안내」·promote-check·닫기 카드 1줄·닫은 뒤 1회 질문 | 통과(닫은 뒤 질문 = 지침 문장) | rail_gate E · test_dept_request +8 · 지침 |
| 6b 한 팀 폭주 시 다른 팀 `queue_full` 0 | 통과(cargo) | t7_share_rejects_only_the_flooding_team |
| 6b 상한 넘는 create 거절 | 통과(cargo) | t8_* |
| 6b 정지 중 그 팀 큐 배달 0 · 다른 팀 안 막힘 | 통과(cargo) | t9_* |
| 6b 묶음 = 꼬리표 단 기계 문안만 · 그 밖 즉시 원문 | 통과(cargo) | t10_* |
| 6b 실물 1기 | **측정 대기** | 시험 프로필 실물 데몬 1회 미실행(시간·부하) |
| codex 1R(배달 경로) | **master 대기열**(codex 한도 · master#ebd716dc) | 질문지 = `docs/1116-s6/codex-r1-prompt.md` · 깨끗한 작업트리 `~/axdev/.wt/cys-1116-s6-codex`(detached ff9e38262 · 이 HANDOFF 커밋 전 머리 — 쓰기 전 `git -C … checkout --detach feat/1116-s6`) |

## 6. 함정 · 재현
- 화면 게이트 실행 = `gates.sh <tag> <dist> <base_dist> [게이트…]`(이 좌석 스크래치 · tickrec·chat_gate 의 SHIM 재사용) · playwright venv `~/axdev/.wt/.gate-pw-venv` · chromium_headless_shell-1248 · `cys run --` 로. 게이트가 커밋된 캡처 2장(docs/evidence-cc-popover-z · evidence-restart-confirm)을 덮어쓰고 `docs/evidence-tabs-sidebar/` 를 남김 → `git checkout --` · 스크래치로 옮김(통합 인계서 I4 와 같음).
- CI 팩 단계 실행 = 워크플로 run 블록 추출(`macos-rust-pack` 잡 · 스텝 이름 부분 일치) → `env -i HOME TMPDIR PATH LANG` 로 bash · 원 스텝은 `set -e` 라 첫 붉음에서 루프가 멈춘다 → 판독용으로 `|| echo @@FAIL` 판을 한 번 더.
- 부하 30+ 에서 시간 문턱 시험(tickrec 5초 · session_start 19b · seatkeep handshake · role_authority_shell)이 붉어짐 — 모두 단독 재실행 초록(§4).
- 화면 시험 문자열에 홈 꼴 경로(`/Users/…`)를 쓰지 말 것(공개 secret-scan · 메모리) → `/w/proj/…` 로 바꿈.

## 7. 📌 덧붙임(실행 안 함 · 판단 = master)

| # | 내용 | 제안 |
|---|---|---|
| P1 | 실물 대화 1회(시험 프로필): 「갈래 셋」 일을 맡기면 마스터가 CORE 요지만으로 `⟪팀 제안⟫` 을 내는가 · 팀 폴더에서 띄우고 seat-group 하는가(메모리 「지침 규칙은 CORE 요지까지 · 실 헤드리스로 시험」) | 1.1.16 전 측정 |
| P2 | 6b 실물 1기(시험 프로필 데몬): 두 팀 좌석으로 몫·정지·묶음 실제 배달 | 1.1.16 전 측정 |
| P3 | CEO 좌석 주입에서 「절 목차」 블록이 상한(8,800)에 밀려 빠진다 — **이 티켓 전부터**(8,401자 · 브리지 1,500자 가정) · CEO_CORE 요지 압축 또는 목차 우선순위 | 1.1.17 또는 별 티켓 |
| P4 | 「★」 절(§14 뒤)이 주입 목차(toc_block)에 아예 안 나온다 — 조각 4 표식 절 · 컴퓨터 통제 절 · 손 빌리지 않기 절 모두 · 이번엔 CORE 요지로만 우회 | 별 티켓(주입기) |
| P5 | ⑧ 도우미 상한은 `role:"worker"` 요청만 센다(번호 붙은 역할 `worker-3` 등 = 기존 active-limit 과 같은 한계) | 1.1.17 |
| P6 | 대화 화면 「팀 만드는 중」 표식은 **대화 화면을 연 뒤** 기록만 읽음(조각 4 앞 훑기 같은 과거 훑기 없음) — 연 시점보다 앞에 낸 표식은 놓침(30분 상한이라 영향 작음) | 1.1.17 |
| P7 | 맡긴 일 카드는 누를 수 없다(시안은 버튼 · FR-L4 엿보기 = 범위 밖) | 조각 다음 |
| P8 | 데몬 재시작 = 정지·꼬리표·보고 시각 비움(DAEMON-6b.md §4 전부) · 앱 사람 묶음 기록을 데몬이 모름 | 기록 |
| P9 | 대화 화면 사건 구독이 이제 셋(조각 3 listen · 조각 4 listenDaemon(조각 6 메뉴바가 같이 씀)) — 통합 인계서 I3 과 같은 성격 | 1.1.17 |

- 증류: 메모리 1건 후보 = 「★ 절(§14 뒤)은 주입 목차 밖 → 새 마스터에게 안 닿음 · CORE 요지로」 — 기존 메모리 pack-directive-rule-must-reach-core-summary 에 한 줄 덧붙임(이 좌석이 함).
