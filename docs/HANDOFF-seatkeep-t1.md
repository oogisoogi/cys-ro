# HANDOFF — TICKET=cysr-seatkeep-t1 (한 대화에 작성자 하나 · 대화 소유 임대)

- 좌석 = worker-3(surface:1938) · 가지 `feat/seatkeep-t1`(기준 v1.1.14 `270e3e21`) · push 0 · HEAD = 이 파일의 커밋
- 브리프 = `~/axdev/master/briefs/2026-11-11-cysr-seatkeep-t1.md` · 설계 = `docs/DESIGN-seatkeep-t1.md`(master#78599b55 승인 · 조건 4 반영 · §6·§11·§13 갱신)
- master 지시: master#2f22d811 · master#388727f0(고침 순서·M3=B) · master#e4e51cd1(순환·재개) · master#ae3bad7d(codex 6R 마지막 · ESCALATE 먼저 보고 · 92 거짓 막힘·실제 HOME 사고 항목) · master#6b1291a0(부하 관문) · master#3e08c923(codex 한도 · 사후 codex 줄)
- TODO = `WORKER_TODO.cysr-seatkeep-t1.md`(작업 폴더 · `cys todo-path` 는 다른 티켓 잔재)
- 상태 = **【매듭】 r5b 끝(master#9d4f5a54 · r5c BLOCK · 1.1.15 = 노브 끔 · 더 고치지 않음)** — 아래 「【매듭】 r5b 끝」 · 이전:
- 옛 상태 = **【확인요청 8-2】 상신(r5b-2 · REVISE master#b444f7fa 처분)** — 아래 「확인요청 8-2 본문」 · 이전:
- 옛 상태 = **【확인요청 8】 상신(r5b · master 재검증 ⓐ 92 고착 · worker-t1fix5b · 브리프 master#4712c43a)** — 아래 「확인요청 8 본문」 · 이전:
- 옛 상태 = **【확인요청 7】 상신(r5 · codex r4 BLOCK 8건 · worker-t1fix5 · 브리프 master#b9481fc8 · T1 마지막 왕복)** — 아래 「확인요청 7 본문」 · 이전:
- 옛 상태 = **【확인요청 6】 상신(r4 뿌리 고침 A+B · worker-10 surface:2021 · 설계 master#c4d14766 → 결정 master#149f4de2)** — codex 3R(BLOCK · 28347181..ec73647d) #1~#6 · 이전 상태(확인요청 5·4·3)는 아래 그대로

## 【매듭】 r5b 끝 — 다음 판(1.1.16) 출발점(11-16 02:54~ · master#9d4f5a54)

- **master 결정**: 1.1.15 = T1 **노브 끔으로만** 싣는다(사전 규칙 · 이중 작성자 급) · 이 좌석은 더 고치지 않는다. HEAD = 이 절의 커밋(코드 마지막 = `9a5d1dc8` · 문서 `7434ebfe` 뒤 이 매듭 커밋) · push 0.
- 판정문 = `~/axdev/master/reviews/codex-queue-2026-11-13/r4/3-seatkeep-t1.r5c.verdict.md`(codex r5c **BLOCK** · 대상 7434ebfe) · master 재검증 로그 = 같은 폴더 `t1-7434ebfe-msv.log` · 그 전 = `t1-c45d7932-msv.log` · 탐침 `t1-c45d7932-hp-probe.rs`·`t1-c45d7932-hp-msv.log`·`t1-e83118df-hp-msv.log` · r4 판정문 `3-seatkeep-t1.r4.verdict.md`.

### r5c 판정 4건(전부 노브 켬 · 요지 — 원문은 판정문)
| # | 등급 | 요지 | 누가 만들었나 |
|---|---|---|---|
| 1 | blocking | **낡은·가짜·헬퍼 등록**으로 `unknown@W` 가 풀려 둘째 작성자 — 풀림이 등록 문자열 하나만 보고 발신자·최상위 에이전트·에이전트 세대·등록 시각을 안 본다(`registered_transcript` 는 매 등록 덮고 에이전트 교체에도 안 지움 · 좌석 밖 호출 `caller_sid=None` 통과 · 파일 존재 무검사 · 중첩 `claude -p` 헬퍼 등록이 덮음) | r5b 1차(unknown@W 풀림 갈래) · 2차가 못 닫음 |
| 2 | blocking | **정상 S 등록을 읽고도 #1 방어 통과** → W2 — 방어가 「등록 있음」만 보고 그 값이 **S 자신**인지 안 본다 · 관문 증거는 topology(수집기 2초 주기)라 등록 직후 창에서 둘 다 놓침 | r5b 2차 |
| 3 | major | Tauri `restore_judge_two`(`src-tauri/src/main.rs:4277`·4289)가 topology `session_id`(휴리스틱 핀) 8자 접두로 첫 93 을 「복원됨」으로 접음 | r4 #3 미폐쇄 |
| 4 | major | 등록 경로가 없는 **Codex 좌석**(rollout 관측으로 topology 대화는 있으나 `registered_session_id` null)이 같은 역할에 있으면 93 → 92 고착(기다려도 안 풀림) | r5b 2차 |
- r5c 의 r4 8건 표: #1·#3 부분 · #2·#4·#5·#6·#8 닫힘 · #7 한계 기록. ⓓ 는 「해당 지점 성립」이나 `run_sidecar_restore_judged` 안쪽(첫 자식 → 15초 → 둘째 자식) 회차 확인 없음(피해 미확인).

### master 재검증이 코드로 읽은 의심(다음 판 시험 후보)
- 좌석 밖 발신의 **가짜 등록**(`cys usage-register --surface W --transcript /x/T.jsonl` · 소유 게이트가 None 통과 · 경로 존재 무검사)
- **보조 claude 등록 덮기**(좌석 안 `claude -p` 헬퍼의 SessionStart 가 `registered_transcript` 를 덮음 · `repin_anchor` 만 헬퍼를 거름)
- **낡은 등록 창**(같은 좌석 에이전트 교체 뒤에도 옛 등록 잔존 · 훅 없는 후속 에이전트가 좌석 안 `/resume S`)
- **codex 좌석 영구 93/92**(r5c #4 와 같음)

### 이 좌석의 붉은 e2e(전부 `tests/session_lease_e2e.rs` · 다음 판 회귀 묶음)
- `a_live_seat_of_unknown_conversation_is_not_given_a_second_writer`(UW · r5 #1) · `a_saved_conversation_never_gets_another_conversations_seat_back`(IR) · `a_seat_revealed_as_another_conversation_frees_the_saved_restore`(RV · 등록 T 로 풀림 · 가짜 claude `FAKE_REG_GATE`) · `a_heuristic_pin_on_a_hookless_seat_never_frees_the_saved_restore`(HP · master 탐침) · `a_hookless_seat_pinned_by_heuristic_before_restore_is_still_unverified`(HQ)
- 아직 e2e 없음(r5c 재현 순서 = 판정문): 낡은 등록 · 가짜 등록 · 헬퍼 등록 · 「등록 S 를 읽고 통과」 · codex 좌석 · Tauri 휴리스틱 「복원됨」.

### 좌석 의견(3줄 · 확신도 중)
- `unknown@W` 를 **판정(judge) 쪽에서 등록 문자열로 푸는 갈래 자체를 걷어내야 한다** — 풀림은 「W 의 **바로 그 에이전트 개체**(93 때 관측한 최상위 에이전트 pid+birth)가 훅 follow 로 다른 대화의 작성자가 됐다」일 때만, follow 안에서(작성자 신원 결속) 일어나야 한다(문자열·시각·세대만으로는 r5c #1 의 세 순서를 못 가른다).
- #1 방어는 3값으로: 등록 = S → 92(살아 있는 작성자) · 등록 = 다른 대화 → 진행 · 없음/판독 불가 → 93 — 그리고 관문 증거와 **같은 신원 원천**을 써야 한다(r5c #2).
- 에이전트별 「현재 대화 증거」 표(claude = 훅 등록+작성자 결속 · codex = rollout 관측 · gemini = 없음 → 노브가 그 역할만 끔)가 먼저 있어야 codex 고착(#4)과 안내 문구가 함께 닫힌다.

### 노브 끔일 때 7434ebfe ≟ 1.1.14(270e3e21) — 코드 대조(실행 실측 아님)
1. **CLI(cys) 임대 길은 끔 = 종전**: `lease_gate`·`restore_lease_pick`·`lease_resume_unheld`·`lease_note_surface`·`lease_follow_on_register` = `sl::enabled()` 먼저 · `lease_role_seat_unverified`·`lease_judge_reused_seat`·`inject_claim_or_lease` 추가 갈래 = `lease_mine`(끔이면 거짓) · 토큰 접두 `L` = 켬일 때만 · `close_failure_rc` = lease_sent 거짓 · 92/93 소비(phoenix `_LEASE_REFUSAL_RE` · `javis_boot_node.py` rc 92/93 · RecoverDisposition)는 끔에서 92/93 이 안 나 무동작 · `run_launch_agent_opts` 반환 꼴만 바뀜.
2. **⚠닿는 줄 1 — `launch_idem_key`(`src/bin/cys.rs:20635`)**: 잇는 기동(`--resume`+대화)의 멱등 키에 `-s<대화>` 를 **노브와 무관하게** 붙인다(r4 A) → 끔에서도 120초 안 같은 역할·폴더 평범 기동 좌석을 재반환받지 않고 새 좌석을 만든다(1.1.14 = 재반환 → 기동 건너뜀 rc 0 · 거짓 성공). 끔에서 1.1.14 와 똑같게 하려면 이 접미를 `sl::enabled()` 안에 넣어야 함(1줄 · 이 좌석은 안 고침 = master 판단).
3. **⚠앱(Tauri·UI)은 노브를 아예 읽지 않는다** → 끔에서도 이번 T1 의 앱 변경이 전부 돈다: `restore_merge_retry`(`main.rs:4436` · 첫 회차 관문 보류·재실행 요약 없음 보존) · `wait_auto_restore_settled_on`/`_for`(`:4201` · 명시 done·off 때만 끝 · 상한) · 죽은 부서 재기동도 같은 판정 층(2r1)·`dept_relaunch_unconfirmed_note`(`:4416` · pending) · done 알림의 pending 반영(「완료」 대신 진행 중) · 후속 감시 B(`followup_restore_with` `:4807` · 30분 + 끝점×10분 · sticky `restore-unconfirmed` `ui/src/main.ts:10983`) · `RESTORE_ROUND`/round(ⓓⓔ) · 초기화 관문을 사이드카 자식 수명 동안 닫음.
4. 앱의 92/93 전용 판독(`restore_judge_two`·`parse_restore_unknown_refusals`·`dept_restore_lease_note`)은 끔에서 93 줄이 없어 무동작(첫 93 비면 topology 판독도 안 함).
5. 결론: **CLI 임대 = 끔이면 종전 · 단 멱등 키 1줄 + 앱 쪽 복원 알림·대기·후속 감시 묶음은 끔과 무관하게 1.1.14 와 다르다** — 1.1.15 를 「T1 끔」 으로 낼 때 이 둘을 싣는지(앱 쪽은 T1 의 정직 알림 개선 · 노브 밖) master 가 정할 것.

## 확인요청 8-2 본문(r5b-2 · master 재검증 REVISE master#b444f7fa · 범위 답 master#a07afa3f · 01:15~)

- 지적 = 새 풀림 갈래가 믿은 topology `session_id` 는 등록만의 값이 아니다(데몬 `agent_session_id` = 등록 없으면 mtime 휴리스틱 1회 핀) → 훅 없는 W 가 93 뒤 무관한 jsonl 로 핀되면 S 재시도 rc 0·W2. master 탐침 = c45d7932 2/2 rc 0 · e83118df 2/2 rc 92.
- 고침(데몬 무변경 · 수용 ①) = 「등록」 판독을 `org.status` `surfaces[].registered_session_id`(cysd `handlers.rs:11954` · `registered_transcript` 의 stem)로. 두 자리:
  - ① 풀림: `CliWorld::seat_conversation`(`src/session_lease_cli.rs:111-126` · 같은 세대 앞뒤 확인 · 칸 없음(옛 데몬)·null·빈 값·형식 이상·좌석 없음·판독 실패 = Err/None = 막음 92)
  - ② #1 방어: `role_seat_unverified`(`src/session_lease_cli.rs:422-432`) = 등록(Ok(Some)) 아닌 살아 있는 같은 역할 좌석 = 모름(93) · 판독 불가 = 모름 쪽 · `lease_role_seat_unverified`(`:437-451`) = 같은 역할 살아 있는 좌석이 있을 때만 org.status 1회 · 순수 판독 `registered_session_in`(`:403-415`)
  - 93 처방 문구(채택) `src/bin/cys.rs:20861-20867`(ERR_REUSED_UNKNOWN 갈래만) · 등록 판독 불가 줄 `src/bin/cys.rs:20747`
- **채우는 자리 전수 grep(조건 ⓐ)** — `grep -n registered_transcript src/bin/cysd/*.rs`(운영 코드 = 각 파일 시험 모듈 앞 · handlers `mod tests` 14021 · usage `mod tests` 3326): **쓰기 = 2곳뿐** — `handlers.rs:11363`(`usage.register` 처리부 `mem::replace(.., Some(path))` · 발신 좌석 = 자기 좌석 게이트 11326) · `state.rs:8098`(`create_surface_with_env` 초기값 None). 읽기 = handlers 11410(clear 재핀 남 좌석 판정)·11954(org.status 노출) · usage 1494(세션 파일 결정 · 등록 우선)·1928·1944(외부 추적 가드). 시험 안 쓰기 = handlers 14건 · usage 9건(전부 시험 모듈). `usage.register` RPC 호출자 = `cys usage-register`(`src/bin/cys.rs:6534`) 하나 · 그것을 부르는 것 = 팩 `hooks/session-start.sh:88·92·98`. ⇒ 등록 경로로만 채워짐 확인(멈출 사유 없음).
- 재기동·세대: `registered_transcript` 는 데몬 메모리 · 재기동 = 새 세대 → 임대의 `daemon_gen` 과 달라 `seat_conversation` = Err(other-gen) · 판독 앞뒤로 세대 확인 → 새 갈래 안 닿음(그대로).

### 탐침 e2e 전/후(원문)
- ① `a_heuristic_pin_on_a_hookless_seat_never_frees_the_saved_restore`(master 탐침 편입) — 전(c45d7932): `HP rc=Some(0) W=surface:1 pin=7a7a7a7a-0000-4000-8000-000000000001 W2=Some(2) seats=[1, 2] writers=1` · 후(9a5d1dc8): `HP rc=Some(92) W=surface:1 pin=7a7a7a7a-0000-4000-8000-000000000001 W2=None seats=[1] writers=0`
- ② `a_hookless_seat_pinned_by_heuristic_before_restore_is_still_unverified`(성립 · 재현됨) — 전: `HQ rc=Some(0) W=surface:1 pin=7a7a7a7a-0000-4000-8000-000000000002 W2=Some(2) seats=[1, 2] writers=1` · 후: `HQ rc=Some(93) W=surface:1 pin=7a7a7a7a-0000-4000-8000-000000000002 W2=None seats=[1] writers=0`
- RV(등록으로 풀림)·UW·IR 초록 유지.

### 뮤턴트(4 KILLED / 0 · 앞 6 그대로)
| | 되돌림 | 결과 |
|---|---|---|
| M17a | ① 판독을 topology session_id 로 | HP 붉음(rc 93 — ② 층이 뒤에서 막음 · 작성자 0) |
| M17a+b | ①② 둘 다 topology 로 | HP 붉음 **rc 0 · W2 · 작성자 1**(두 층 각각 의미 있음) |
| M17b | ② 판독을 topology session_id 로 | HQ 붉음(rc 0 · W2 · 작성자 1) |
| M17c | ② 판독 불가를 등록으로 침 | 단위 `role_seat_of_unknown_conversation_truth_table` 붉음 |

### org.status 판독 실패 때(막음 쪽) 사용자 줄(원문)
- 「error: session_lease: 역할 R 좌석 대화 판정 불가(org-status-unreadable) — 새 좌석을 만들지 않음 · 확인: `cys status` 로 데몬이 응답하는지 본 뒤 다시 실행하세요」(rc 93 · 고치기 전에는 「· 확인 …」 없이 끝났다 → 다음 행동 1줄 추가)
- 풀림 판독 실패 = 92 줄(결과 불명)의 종전 처방 그대로(「막 뜬 것이면 잠시 뒤 다시 … 계속 막히면 read-screen …」).

### 형제 — topology `session_id` 를 등록/소유 증거로 읽는 다른 자리(목록만 · 고치지 않음)
| 자리 | 읽는 뜻 | 휴리스틱 핀일 때 방향 |
|---|---|---|
| `src/session_lease_cli.rs:140` `CliWorld::evidence` | 이 대화를 잇는 좌석이 있으면 거절 | 거짓 막힘(92 · 안전 쪽) |
| `src/session_lease_cli.rs:454-461` `lease_judge_reused_seat`(재반환 좌석) | = 이 대화 → 잇는 중(rc 0 · 기동 건너뜀) · 다른 대화 → 93 | 거짓 성공(대화가 실제로 안 이어졌는데 rc 0 · 작성자 둘 아님) |
| `src-tauri/src/main.rs:4289` `restore_judge_two` | 그 역할 점유 좌석이 그 대화면 첫 93 풀림 | 거짓 「복원됨」(알림이 판정 불가를 안 셈) |
| `src/bin/cys.rs:25981` `run_restore`(D-mac-2) | 살아 있는 좌석의 대화 = 같은 id 두 번째 `--resume` 막기 | 거짓 막힘(안전 쪽) |

### R1 시간(잇는 기동마다 org.status) 
- 코드: R1(작성자만 죽은 뒤 같은 데몬 재복원)은 같은 역할 **살아 있는** 좌석이 없어 org.status 를 부르지 않는다(먼저 topology·surface.list 로 후보를 걸러 없으면 종전 그대로 반환) — 비용은 같은 역할 살아 있는 좌석 옆 잇는 기동에서만 1회.
- 실측(같은 기계 · 번갈아 · `SLE_RR=10` R1 단독 · 01:33~01:51 · 1분 부하 4~13): 고치기 전 c45d7932 = median **9.575 / 9.408**s(p95 14.462 / 9.573) · 고친 뒤 9a5d1dc8 = median **9.507 / 9.468**s(p95 9.809 / 9.580) ⇒ 차이 없음(잡음 범위). master 재검증 8.921/8.928 과의 차는 기계 부하(그때 다른 좌석 부하 낮음)로 봄 — 같은 기계 같은 때 A/B 로 가름. e2e 전체 안 R1 5회(01:27 · 부하 13→6) median 9.534.

### 회귀
- lib `session_lease` **22/0** · bin `session_lease` **26/0** · cys bin 전체(병렬 4) **782/0**(1 무시 · 01:52~02:05) · Tauri 전체 **347/0** · tsc rc 0 · phoenix OK · cysd = 무변경(시험 대상 없음)
- e2e 전체(`SLE_RR=5 SLE_ROUNDS=5 SLE_DD=10 SLE_RN=1 SLE_RN3=20` · 01:27~01:33) **9/9**: R1 5 소실 0·rc93 0 · R3 5 작성자 2 0·고아 0 · DD 20 소실 0·rc93 0 · 남 데몬 93 ✓ · 인수 ✓ · RN3 20/20 · IR rc 0 · UW rc 93 · RV rc 0 · **HP rc 92 · HQ rc 93**
- 반복 5(02:06~02:14): HP 5/5 rc 92·작성자 0 · HQ 5/5 rc 93·W2 없음 · RV 5/5 rc 0 · IR 5/5 rc 0
- 위생: 실제 HOME 임대 폴더 없음 · `readlink ~/.local/bin/claude` = 2.1.325 · `/tmp/cys-sle-*` 0 · codex 0

## 확인요청 8 본문(r5b · master 재검증 「정당한 복원이 92 로 굳는 길」 · 11-16 00:09~ · TICKET=cysr-seatkeep-t1-r5b)

- 브리프 = `~/axdev/master/briefs/2026-11-16-cysr-seatkeep-t1-r5b-stuck92.md`(master#4712c43a) · 좌석 = worker-t1fix5b · TODO = `WORKER_TODO.cysr-seatkeep-t1-r5b.md` · codex 0 · 처분 정본 = `docs/DESIGN-seatkeep-t1-r4.md` §7

### ⓐ 성립 — 붉은 e2e `a_seat_revealed_as_another_conversation_frees_the_saved_restore`
- 꾸밈: 가짜 claude 새 노브 `FAKE_REG_GATE`(화면은 띄우고 등록 `cys usage-register` 만 관문 파일까지 자식에서 미룸 = 정상 기동 직후 SessionStart 등록 전 창 · 등록은 실제 훅과 같은 길 = 임대 follow 포함) · 시험이 직접 `usage.register` 하지 않는다.
- 순서: W(새 대화) 기동 · 등록 전 → S `--resume-saved` = 93(좌석 [W] · 작성자 0 · 임대 `unknown·writer null·surface W`) → 관문 열기 → W 등록 = T(≠S) 확인 → S 재시도.
- **고치기 전(HEAD e83118df) 출력**: `RV rc=Some(92) W=surface:1 reg=a0ed5547-… W2=None writers=0` · 임대 전후 동일(`fence 1 · state unknown · writer null · surface_id 1`) = 92 고착 실측.
- 고친 뒤: `RV rc=Some(0) W=surface:1 reg=45b549be-… W2=Some(2) writers=1` · 임대 = 새 좌석 2 · 작성자 = 그 claude · W 등록 T 그대로.

### 고친 파일:줄
| 무엇 | 파일:줄 |
|---|---|
| ⓐ `World::seat_conversation`(기본 = 판독 불가 · 보수) | `src/session_lease.rs:124-128` |
| ⓐ judge 3) 결과 불명 ∧ 좌석 살아 있음 ∧ 등록 = 다른 대화 → 풀림 | `src/session_lease.rs:503-510` |
| ⓐ(b) 92 줄(결과 불명)에 다음 행동 1줄(문구 1곳) | `src/session_lease.rs:511-522` |
| ⓐ 운영 판독 = 같은 데몬 세대 topology live `session_id`(세대 다름·없음·판독 실패·형식 이상 = Err) | `src/session_lease_cli.rs:112-122` |
| ⓑ `require` → `import { readFileSync } from "node:fs"` | `ui/src/restoredone.test.ts:4·63·78` |
| ⓓ probe 뒤 `current()` 재확인 | `src-tauri/src/main.rs:4844-4847` |
| ⓔ 조직 복원 본체 `skip`×6·`error`×1 에 `round` | `src-tauri/src/main.rs` `spawn_org_restore`(4607·4624·4678·4687·4707·4712·4731 근처) · 소스 핀 2곳 갱신(dept 없는 skip · 확인 못 함 skip) |
| 시험 | 단위 `unknown_seat_registered_as_another_conversation_is_freed`(`src/session_lease.rs`) · e2e RV(`tests/session_lease_e2e.rs` 끝) · Tauri `seatkeep_r5b2_round_change_during_probe_spawns_no_judge_and_every_org_event_has_round` · 가짜 `tests/fixtures/fake_claude.c` `FAKE_REG_GATE` |

### 닫혀야 하는 성질 둘
- ⑴ W 가 S 를 쓰는 중일 수 있는 동안(등록 없음 · 판독 실패 · 다른 데몬 세대 · 등록 = S) 둘째 작성자 0 — UW e2e 초록 그대로(rc 93 · 좌석 [1] · claude 1 · 재시도 92 · W 내려간 뒤 인수 rc 0) · 단위 진리표 4칸(등록 없음 · 판독 불가 · 같은 대화(대소문자) · 빈 등록) = 막음 · 기동 중 임대(복원기 죽음) = 넓히지 않음(막음).
- ⑵ W 가 다른 대화임이 등록으로 확인되면 풀림 — RV e2e 초록 · 단위 `T5` 칸 Granted.

### 전문가 칸 — 「W 가 S 로 뒤늦게 등록」 순서 표(고친 뒤)
| # | 순서 | 판정 | 작성자 |
|---|---|---|---|
| 1 | W 등록 없음 → S 복원 | #1 = 93 · 임대 unknown@W | 1(W 가 S 를 쓰고 있었다면 W 하나) |
| 2 | (1) 뒤 S 등록 도착 전 S 재시도 | 등록 없음 → 새 갈래 안 탐 → 92 | 1 |
| 3 | (1) 뒤 W 의 등록이 **S** 로 도착 | follow: 임대 writer null ∧ surface W ∧ 같은 세대 → 승계(writer = W 의 claude · held) | 1 |
| 4 | (3) 뒤 S 재시도 | judge 1) 작성자 W 살아 있음 → 92 · 새 갈래는 결과 불명 임대에만 → 닿지 않음 | 1 |
| 5 | (1) 사이 등록이 S 라면 어느 순간에도 seat_conversation = 다른 대화가 아니다 → 풀리는 순간 0 | — | 1 |
| 6 | ⚠ W 가 먼저 **T 로 등록된 뒤** 좌석 안 `/resume S` · S 등록 도착 전 S 재시도 | 등록 T → 풀림 → 바깥 증거(topology S · argv) 아직 없음 → 새 좌석 | **2 가능** — 새 창 아님: 같은 창이 고침 전부터 수용된 IR 흐름(T 등록 좌석 옆 S 새 좌석 · `role_seat_unverified` 통과)에 있다 · 고침 전에는 93 이 한 번 났던 경우에만 92 고착이 우연히 덮었음(값 = W 가 사는 동안 영구 막힘). 닫으려면 등록 지연을 재는 규약 = 【결정필요】 감. 그 뒤 S 등록이 W 에서 오면 follow = Conflict(살아 있는 W2 를 안 빼앗음 · 사건만). |

### (b) 훅 없는 좌석 — 안내 문구
- 첫 93(launch-agent): 「error: session_lease:reused-unknown: 역할 R 의 좌석 surface:W 가 어느 대화를 잇는지 모름(등록 없음) — …」 + 「[launch-agent] 저장 대화를 띄우지 않음(rc 93) — 확인: `cys read-screen --surface surface:W` 로 그 좌석이 어느 대화를 잇는지 보고, 이 대화가 아니면 그 좌석을 닫은 뒤 다시 실행하세요」 = (b)에 맞음 · ⚠(a) 흔한 경우(막 띄운 좌석 · 곧 등록됨)에는 「닫아라」가 과함 → **문구 후보(이번엔 안 고침 · master 판단)**: 「… 확인: 그 좌석을 막 띄웠다면 잠시 뒤 다시 실행하세요(그 좌석이 다른 대화로 등록되면 풀립니다) · 계속 막히면 `cys read-screen --surface surface:W` 로 보고, 이 대화가 아니면 그 좌석을 닫은 뒤 다시 실행하세요」(`src/bin/cys.rs` 93 처방 줄 · ERR_REUSED_UNKNOWN 갈래만).
- 재시도 92(이번에 고친 1곳): 종전 「· R: 대화 X — 좌석 surface:W 가 이 대화를 잇는 중일 수 있음(기동 결과 불명) — 띄우지 않음(…)」 = 무엇을 하라는지 없음 → 새 줄 「· R: 대화 X — 좌석 surface:W 가 이 대화를 잇는 중일 수 있음(기동 결과 불명) · 확인: 그 좌석이 막 뜬 것이면 잠시 뒤 다시 실행하세요(다른 대화로 등록되면 풀립니다) · 계속 막히면 `cys read-screen --surface surface:W` 로 그 좌석이 이 대화를 잇는지 보고, 아니면 그 좌석을 닫은 뒤 다시 실행하세요 — 띄우지 않음(…)」 · phoenix `_LEASE_REFUSAL_RE` 가 그대로 읽음(정규식 대조 실측) · 기동 중 임대 92 줄은 종전 그대로.

### ⓒ
- ⓓ 성립 → 고침(위) · ⓔ 성립 → 고침(위). 「기록만」 3건 = DESIGN r4 §7.

### 뮤턴트(6 KILLED / 0 SURVIVED)
| | 되돌림 | 결과 |
|---|---|---|
| M15a | judge 새 갈래 끔(`if false && …`) | e2e RV 붉음(rc 92 · writers 0) |
| M15b | `CliWorld::seat_conversation` 상시 Err | e2e RV 붉음(rc 92) |
| M15c | 같은 대화여도 풀림 | 단위 붉음 |
| M15d | 결과 불명 한정 제거(기동 중까지) | 단위 붉음 |
| M16a | ⓓ 재확인 제거 | Tauri r5b2 붉음(판정 층 1회 호출) |
| M16b | ⓔ error 의 round 제거 | Tauri r5b2 붉음(핀) |

### 회귀
- 단위: `cargo test --lib session_lease` **22 통과 · 0 실패**(새 1) · `cargo test --bin cys session_lease` **26 통과 · 0 실패**
- Tauri 전체 **347 통과 · 0 실패**(2 무시 · 기준 346 + 새 1) · seatkeep 10 통과 · phoenix `test_phoenix_seatkeep_t1_lease_hold.py` OK · 새 92 줄을 phoenix `_LEASE_REFUSAL_RE` 가 읽음(정규식 대조)
- UI bun 전체 **3334 통과 · 0 실패**(88 건너뜀 · 기준과 같음) · 타입 `bunx --package typescript@7.0.2 tsc -p tsconfig.check.json` **rc 0** · 음성 대조(HEAD 의 restoredone.test.ts) rc 1 · TS2591 62·77 두 줄(node_modules = cys-1115-integ 에서 `cp -Rc` · 커밋 0 · .gitignore)
- e2e 전체(`SLE_RR=5 SLE_ROUNDS=5 SLE_DD=10 SLE_RN=1 SLE_RN3=20` · 00:26~00:31) **7 통과**: R1 5 소실 0·rc93 0(중앙 9.211s) · R3 5 소실 0·작성자 2 0·고아 0 · DD 20 소실 0·rc93 0 · 남 데몬 93 ✓ · 인수 ✓ · RN3 20/20 거절 · IR rc 0 · UW rc 93·좌석 [1]·claude 1 · **RV rc 0·작성자 1**
- 반복 20(`SLE_RR=20 SLE_ROUNDS=20 SLE_DD=20` · 00:31~00:40 · 1분 부하 ≈5): R1 20 소실 0·**rc93 0**(중앙 9.314s · p95 10.429) · R3 20 소실 0·작성자 2 0·고아 0 · DD 40 소실 0·**rc93 0**
- IR·RV 단독 20회(동시 실행 · 00:31~): IR **20/20 rc 0·작성자 1** · RV **20/20 rc 0·작성자 1**(00:31~00:53 · 0 실패)
- 위생: 실제 HOME 임대 폴더(`~/.local/state/cys/session-leases`) = 없음 · `readlink ~/.local/bin/claude` = `…/versions/2.1.325`(시작과 같음) · `/tmp/cys-sle-*` 잔재 0 · 진짜 claude 0 · codex 0
- 못 본 것: 진짜 Claude 의 SessionStart 등록 지연 실측(가짜의 관문으로 대신) · 실제 앱 화면(ⓔ round 는 소스 핀 + 기존 `restoreEventIsStale` 단위) · 순서 표 6행 창의 실측(코드 추론)

### master 재검 명령
```bash
cd ~/axdev/.wt/cys-seatkeep-t1 && export PATH=$HOME/.cargo/bin:$PATH CARGO_TARGET_DIR=target/s1
cargo test --lib session_lease && cargo test --bin cys session_lease && cargo test --manifest-path src-tauri/Cargo.toml seatkeep
SLE_RR=5 SLE_ROUNDS=5 SLE_DD=10 SLE_RN=1 SLE_RN3=20 cargo test --test session_lease_e2e -- --nocapture   # 7 · RV 포함
```

## 확인요청 7 본문(r5 · codex r4 BLOCK 8건 처분 · 11-15 21:42~ · TICKET=cysr-seatkeep-t1-r5)

- 브리프 = `~/axdev/master/briefs/2026-11-15-cysr-seatkeep-t1-r5-fix.md` · 판정문 = `~/axdev/master/reviews/codex-queue-2026-11-13/r4/3-seatkeep-t1.r4.verdict.md`(BLOCK · blocking 3 · major 4 · minor 1) · 좌석 = worker-t1fix5 · TODO = `WORKER_TODO.cysr-seatkeep-t1-r5.md`
- 커밋: **1d6d9cee**(#1·#2) · **651fcb07**(#3 · B 축소 · #7 문서) · 문서 = 이 HANDOFF 커밋
- **노브 기본값 = 켬** — `src/session_lease.rs:24-26`(`enabled_from(None)` = true · `off`/`0`/`false`/`no` 만 끔). 노브 끔이면 T1 이 고치려던 「같은 데몬 600초 안 재복원 대화 소실」을 사용자가 그대로 겪는다(끔 대조군 실측 = 이 HANDOFF §F S4 재측정 HEAD 242a035c: R1 재복원 20/20 소실 · 두 입구 동시 19/20 · 두 데몬 38/40) · 앱 쪽 후속 감시(B)는 노브와 무관하게 돈다(DESIGN r4 §4 ⑵ 미이행 그대로).
- codex 줄: **이 좌석은 codex 를 부르지 않았다**(master 가 건다) · 대상 = `1753aa2e..<이 HANDOFF 커밋>`

### 8건 처분 표
| # | 판정문 | 재현 | 처분 · 고친 파일:줄(HEAD 651fcb07) | 재는 시험(뮤턴트) |
|---|---|---|---|---|
| 1 blocking | 옛 키 무등록 W 옆에 W2 = 작성자 둘 | **성립**(e2e 실측: 고치기 전 rc 0 · 좌석 [1,2] · claude 2) | 고침 — 좌석 만들기 전 같은 역할 살아 있는 미등록 좌석 = rc 93 · 새 좌석 0 · 임대 = 그 좌석(결과 불명) `src/bin/cys.rs:20736`(방어) · `:20840`(93 좌석 규칙) · `src/session_lease_cli.rs:390`(순수 판정)·`:400`(운영) | e2e `a_live_seat_of_unknown_conversation_is_not_given_a_second_writer`(93 → 재시도 92 → W 내려간 뒤 인수 rc 0) · 대조 = `a_saved_conversation_never_gets_another_conversations_seat_back`(W 등록 T → 새 좌석 rc 0) · 단위 `role_seat_of_unknown_conversation_truth_table` · M11a·M11b·M11c·M11d KILLED |
| 2 blocking | 낡은 argv 가 등록 T 를 덮어 rc 0 | **성립(코드 · 진리표)** — 순수 판정 `argv_writer → Continues` 가 등록 T·판독 실패보다 앞섬(단위 붉음 확인) · 전체 경합(좌석 안 자식이 조상 제외로 관문 통과)은 e2e 로 세우지 않음(조상 제외 = `CliWorld.exclude` 코드 확인) | 고침 — 등록 다른 대화 + argv = Unknown · 판독 실패 + argv = Unknown · 등록 없음 + argv = 잇는 중(종전) `src/session_lease_cli.rs:375` | `reused_seat_verdict_and_idem_key` · M12a·M12b KILLED |
| 3 major | 새 93 이 Tauri 재실측에서 성공으로 접힘 · 새 93 표준 줄 없음 | **성립(코드)** — 재실측 `cys restore` 가 `live.contains(role)` 로 건너뜀 → `restore_merge_retry` 가 첫 unknown 을 버림(고치기 전 = 뮤턴트 M13a 붉음) | 고침 — ① 복원 fresh 안쪽 92·93 표준 거절 줄 `src/bin/cys.rs:26242` · `src/session_lease_cli.rs:592` ② 판정 층 `restore_judge_two` `src-tauri/src/main.rs:4277`(첫 93 = 그 역할 점유 좌석이 그 대화로 등록됐다고 볼 때만 풀림) · 93 줄 판독 `:4262` | Tauri `seatkeep_r5_3_first_unknown_is_kept_until_that_conversation_is_seen` · cys `restore_inner_refusals_print_the_standard_line` · phoenix `test_phoenix_seatkeep_t1_lease_hold.py` R5 축 · M13a·M13b·M13c KILLED |
| 4 blocking | 판정 await 에 30분 상한 안 걸림 | **성립(코드)** | B 축소 — 판정 기다림 10분 시한(`FOLLOWUP_JUDGE_CAP` `main.rs:4791`) · 기다리는 동안 1분 진행 sticky · 넘으면 그 끝점 = 확인 못 함 · 초기화 관문 = 사이드카 자식 수명(`main.rs:4307`) · 본체 `followup_restore_with` `main.rs:4807` | Tauri `seatkeep_r5b_followup_reports_per_end_only_and_always_ends`(정지 Future → 150ms 시한 · heartbeat ≥3 · 다른 끝점 확인됨) · M14a(시한 제거 = 시험 안 끝남) · M14b · M14g KILLED |
| 5 major | 옛 감시 × 새 회차 겹침 | **성립(코드)** | B 축소 — 회차 번호 `RESTORE_ROUND` `main.rs:4559` · 옛 감시 = 회차 바뀌면 무발행 종료(판정 결과도 버림) · 모든 후속 이벤트에 `round` `main.rs:4891` · 화면 = 옛 round 버림 `ui/src/main.ts:10926` · `ui/src/restoredone.ts:70` | 같은 Tauri 시험(판정 도중 회차 바뀜 → Heartbeat 1 뿐) · bun `restoredone.test.ts` 회차·배선 · M14c·M14d·M14i KILLED |
| 6 major | 늦은 성공이 첫 실패를 덮어 「✅ 완료」 | **성립(코드)** | B 축소 — 조직 「완료」 이벤트 자체를 없앰(`settled` 삭제) · 끝점별 `followup-ok` 만 · 「✅ 직원 복귀 완료」 문자열 = `ui/src/restoredone.ts:36`(첫 회차 done) 한 곳뿐(grep 전수: ui/src·src-tauri/src) · 쓸기 무장 = done 만 | bun 배선(「완료」 문자열 1곳 · followup 갈래 armSweep 0) · M14e·M14h KILLED |
| 7 major | 앱 재실행 뒤 감시 소멸 | (재현 안 함 · 처분 = 한계) | **알려진 한계** — `docs/DESIGN-seatkeep-t1-r4.md` §6 에 판정문 원문 · 1.1.16 후보 · 아래 릴리스 노트 후보 | — |
| 8 minor | 30분 경고가 8초 알림 | **성립(코드)** | B 축소 — 확인 못 함 = sticky `restore-unconfirmed`(60초 + 알람 이력 · 다음 회차 start 가 걷음) `ui/src/main.ts:10983` · `ui/src/restoredone.ts:59` | bun 배선 · M14f KILLED |


### 3R #1~#6 다시(판정문 「3R 처분 확인」 표 → r5 뒤)
| 3R | r4 판정문 | r5 뒤 | 근거 |
|---|---|---|---|
| #1 topology 재판독 실패 | 부분만(낡은 argv 로 남의 W·rc 0) | **닫힘** | 판독 실패·등록 충돌 + argv = Unknown 93·임대 유지(#2) |
| #2 다른 대화인데 성공 | 부분만(Tauri 재실측이 역할 생존만 봄) | **닫힘** | `restore_judge_two`(#3) · 새 93 표준 줄 |
| #3 등록 없음 뒤 임대 해제 | 안 닫힘(종전 키 W 에 새 작성자) | **닫힘** | 좌석 만들기 전 같은 역할 미등록 좌석 = 93·새 좌석 0(#1 · e2e 실측) |
| #4 pending 종결(앱 몫) | 부분만(판정 await 정지·회차 중첩·앱 재실행) | **부분** — 정지·중첩 닫힘 · **앱 재실행 = 알려진 한계(#7)** · 데몬 `child.wait()` 무제한 = T1 밖 | 판정 시한 · 회차 번호 |
| #5 늦은 92·93 사람말 | 부분만(새 Other 93 소실 · 후속 성공이 최초 실패 덮음) | **닫힘** | #3 고침 · 조직 「완료」 없음 |
| #6 직렬 대기 중 무표시 | 닫힘 | **닫힘 유지** | + 판정 기다리는 동안에도 heartbeat |


### 새 화면 문구 후보(최종 = master)
- 「👥 {끝점} 직원 복귀 확인됨 — 늦게 끝난 자동 복원을 확인했습니다.」(끝점별 · 일회성)
- 「⚠ 직원 복귀를 확인하지 못함 — {끝점들}의 자동 복원이 끝났는지 아직 확인하지 못했습니다 — 잠시 뒤 ↻ 재시작을 눌러 다시 확인하세요.」(sticky · 다음 회차 시작에서 걷음)
- 없앤 문구: 「✅ 직원 복귀 완료 — 늦게 끝난 자동 복원까지 확인했습니다 (N곳).」 · 「⚠ 직원 복귀가 끝나지 않음 — … 30분 …」(8초) · 「⚠ 직원 복귀 일부 보류 — 늦게 끝난 …」
- 복원 출력 새 줄(사람·phoenix 공용): 「· {역할}: 대화 {앞 8자} 작성자 생존 판정 불가(seat-unverified) — 띄우지 않음 · 확인: `cys read-screen --surface surface:W` 로 그 좌석이 이 대화를 잇는지 보세요」 · 「· {역할}: 대화 {앞 8자} — 그 대화를 잇는 좌석이 이미 있음 — 띄우지 않음 · 확인: …」
- launch-agent 새 오류 줄: 「error: session_lease:reused-unknown: 역할 R 의 좌석 surface:W 가 어느 대화를 잇는지 모름(등록 없음) — 이 대화를 쓰고 있을 수 있어 새 좌석을 만들지 않음」 + 종전 「[launch-agent] 저장 대화를 띄우지 않음(rc 93) — 확인: …」

### 릴리스 노트 후보(추가)
- 「같은 역할 창이 어느 대화를 잇는지 알 수 없을 때(대화 등록 전) 저장된 대화를 이어 켜면, 이제 새 창을 띄우지 않고 그 창을 확인하라고 알립니다(같은 대화에 두 창이 쓰는 것을 막기 위해서입니다).」
- 알려진 한계(1.1.16): 「업데이트 뒤 직원 복귀 확인 중에 앱을 닫았다 다시 열면, 그 확인 결과 알림이 나오지 않습니다.」(codex r4 #7 · DESIGN r4 §6 원문)

### 전체 시험(HEAD 651fcb07 · 22:24~23:18 · 1분 부하 2.8~9.5 · 시험 일꾼 4)
- UI(bun) **3334 통과 · 0 실패**(88 건너뜀 · 기준 3333 + 순증 1 = settled 2 삭제 · 새 3)
- lib **1224 통과 · 0 실패** · Tauri **346 통과 · 0 실패**(r4b 1 → r5b 1 + r5_3 1) · phoenix seatkeep 임대 시험 OK(R5 축 추가)
- cys bin(병렬 4) 1회차 = **중단**: `tests::a3_strip_hook_digits_only_for_the_seven_target_verbs_when_the_rest_is_leftover_args` 스택 넘침(SIGABRT · 그때까지 217 ok) → 단독 = 통과 · 단일 스레드 전체 = **782 통과 · 0 실패** · 병렬 4 재실행 = **782 통과 · 0 실패**. 그 시험은 `Cli::try_parse_from`(clap 전체 트리)을 2MB 시험 스레드에서 돈다 · 이번 차이는 CLI 정의 무변경 → 병렬 스레드 스택 흔들림으로 판정(기준선 확인요청 6 = 0 실패 · 같은 이름 실패 기록 없음 = 새 이름이지만 재현 0/2)
- e2e(임대 켬 · `SLE_RR=5 SLE_ROUNDS=5 SLE_DD=10 SLE_RN=1 SLE_RN3=20`) **6 통과**: R1 5 소실 0·rc93 0(중앙 9.241s) · R3 5 소실 0·작성자 2 0·고아 0 · DD 20 소실 0·rc93 0 · 남 데몬 93 ✓ · 인수 ✓ · RN3 20/20 거절 · IR(T 등록 좌석 옆 S) rc 0·새 좌석 2·작성자 1 · **UW(#1)** rc 93·좌석 [1]·claude 1·임대 unknown→surface 1
- **전문가 칸(정상 흐름 93 이 늘지 않는가 · 23:18~23:39 · 부하 2.3~3)**: `SLE_RR=20 SLE_ROUNDS=20 SLE_DD=20` = R1 20 소실 0·**rc93 0**(중앙 9.667s) · R3 20 소실 0·작성자 2 0·고아 0 · DD 40 소실 0·**rc93 0** · IR(T 등록 좌석 옆 S 새 좌석) 단독 20회 = **20/20 rc 0**
- 실제 HOME 임대 폴더(`~/.local/state/cys/session-leases`) = 없음 · `readlink ~/.local/bin/claude` = `…/versions/2.1.325`(시작 21:43 과 같음) · `/tmp/cys-sle-*` 잔재 0
- 뮤턴트 **18 KILLED / 0 SURVIVED**(#1 M11a~d · #2 M12a~b · #3 M13a~c · B M14a~i)
- ⚠못 본 것: `ui/src/main.ts` 타입 검사(node_modules 없음 · `bun build --no-bundle` 변환만 통과) · 실제 앱 화면 · 진짜 Claude · #2 전체 경합 e2e · 판정 시한 넘긴 실제 사이드카 자식(주입 시험만)

## 확인요청 6 본문(r4 뿌리 고침 A+B · 11-13 12:24~)

- 판정문 = `~/axdev/master/reviews/codex-queue-2026-11-13/r3/3-seatkeep-t1.r3.verdict.md`(BLOCK · blocking 3 · major 2 · minor 1) · 설계 = `docs/DESIGN-seatkeep-t1-r4.md`(8f15f067 · master 승인 = A+B · 1.1.15) · 갈래별 땜질 대신 뿌리 셋(R1 멱등 키에 대화 ID 없음 · R2 비성공이 rc 0 · R3 pending 에 끝 없음)을 고쳤다.
- 커밋: **A 4c9db9fd** · **B d1efaa6d** · 문서 = 이 HANDOFF 커밋.
- **codex 줄**: codex 미수행(master 발사 예정) · 대상 = `ec73647d..<이 HANDOFF 커밋>` · **codex 다음 회차에 꼭 물을 것**:
  1. 멱등 키에 대화 ID 를 넣은 뒤에도 재반환 + 건너뜀으로 「남의 대화 좌석」을 이 대화 임대에 적거나, 비성공을 rc 0·commit·ok 로 세는 갈래가 남았는가(3갈래 · rc 93 좌석 규칙 = 좌석이 남은 93 만 유지).
  2. 후속 감시가 명시 done·off 전에 판정 층(사이드카)을 돌리거나, 끝내 Settled 를 못 내거나, 감시 중 초기화와 겹쳐 부서·좌석을 되살리는 길이 있는가(관문은 판정 층 동안만 닫음).
  3. done → followup → settled 이벤트 순서에서 화면이 「완료」와 「끝나지 않음/일부 보류」를 함께 말하거나, 끝나지 않은 끝점이 있는데 옛 자리를 쓰는 조합이 있는가.

### 판정문 #1~#6 닫힘 표

| # | 지적 | 처분 | 커밋 · 고친 줄(HEAD) | 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 blocking | topology 판독 실패 → 남의 좌석 임대 | **닫힘** — 키에 대화 ID(`launch_idem_key` cys.rs:20635 · 배선 :20713) → 다른 대화 좌석은 재반환 안 됨 · 남는 재반환(같은 대화 재시도)에서 판독 실패 = 판정 불가 rc 93 + 임대 유지(`reused_seat_verdict` session_lease_cli.rs:373 · 판정 배선 cys.rs:20782 · 93 갈래 :20838) | 4c9db9fd | e2e `a_saved_conversation_never_gets_another_conversations_seat_back`(고치기 전 = 뮤턴트 M9a 붉음) · 단위 진리표 · M9c KILLED |
| 2 major | 다른 대화 확인 뒤 rc 0·성공 1 | **닫힘** — 다른 대화 = rc 93 + 임대 되돌림 · 복원 commit·ok 0(rc 93 좌석 규칙 cys.rs:20819 · `lease_finish_by_rc` session_lease_cli.rs:618 · 복원 fresh cys.rs:26218) | 4c9db9fd | `rc93_keeps_the_lease_only_when_a_seat_may_be_writing`(launch-agent·복원 fresh) · M9d·M9e·M9f KILLED |
| 3 blocking | 등록 없음 → 되돌림 = 작성자 둘 | **닫힘** — 등록 없음 ∧ argv 없음 = 판정 불가(임대 유지 · 93) · 「다른 대화」로 단정 0 | 4c9db9fd | 진리표 · M9b·M9g KILLED |
| 4 blocking | pending 에 끝 없음 | **닫힘(앱) · 부분(데몬)** — 후속 감시(`followup_restore_with` main.rs:4733 · 대상 수집 :4511·:4649 · done 뒤 실행 :4681 · 판독 :4722)가 명시 done·off 뒤 판정 층 1회 · 반드시 settled · 30분 상한 안내 | d1efaa6d | `seatkeep_r4b_…`(주입 판독·판정 · 상한 300ms) · M10a·M10b·M10d·M10e KILLED |
| 5 major | 상한 뒤 92·93 사람말 없음 | **닫힘** — 감시가 판정 층을 돌려 `restore_note`(92·93·관문·실패)를 `skip` 으로(`emit_followup` main.rs:4780) | d1efaa6d | 같은 시험(본부 늦은 결과 = 관문 + 92 문구) · M10c KILLED |
| 6 minor | 직렬 대기 > 3분 진행 토스트 꺼짐 | **닫힘** — 부서 대기 전 `start` 재방출(main.rs:4632) · 감시 중 1분마다 `followup` sticky(ui/src/main.ts:10966) | d1efaa6d | 같은 시험(heartbeat ≥3) · bun restoredone(settled·followup 배선) · M10g·M10h·M10i~k KILLED |

- **데몬 티켓 후보(이번 범위 밖 · #4 남는 부분)**: cysd 자동 복원 자식 `child.wait()` 무제한(src/bin/cysd/main.rs `loop_auto_restore` 계열) — 자식이 멈추면 데몬 단계가 영구 `running` · 앱은 30분 안내까지만. 데몬 쪽 시한·취소·인계 규약이 필요.
- **새 동작 1 · 릴리스 노트 후보 문장**: 「같은 역할이 다른 대화로 이미 떠 있을 때 저장된 대화를 이어 켜면, 이제 그 창을 다시 쓰지 않고 새 창에서 저장된 대화를 잇습니다(종전에는 2분 안이면 그 창을 그대로 두고 저장된 대화는 열리지 않았습니다).」
- **새 화면 문구 3**(최종 = master): 「👥 직원 복귀 확인 중 — 자동 복원이 끝나면 결과를 알려 드립니다(최대 30분).」 · 「✅ 직원 복귀 완료 — 늦게 끝난 자동 복원까지 확인했습니다 (N곳).」 · 「⚠ 직원 복귀가 끝나지 않음 — 자리 N곳의 자동 복원이 30분이 지나도 끝나지 않았습니다 — ↻ 재시작을 눌러 다시 시도하세요.」(+ 늦은 실패 「⚠ 직원 복귀 일부 보류 — 늦게 끝난 자동 복원 N곳 중 M곳은 다 세우지 못했습니다 — 바로 앞 알림의 안내를 따라 주세요.」)

### 전체 시험(HEAD d1efaa6d · 12:40~13:17 · 1분 부하 8~23 · JOBS 4 · 시험 일꾼 4)
- UI(bun) **3333 통과** · 0 실패(88 건너뜀) · lib **1224 통과** · 0 실패 · Tauri **345 통과** · 0 실패(344 + r4B 1) · cys bin(병렬 4) **780 통과** · 0 실패(779 + r4A 단위 1 · 옛 3R ① 단위 1 은 새 진리표로 교체)
- e2e(임대 켬 · `SLE_RR=5 SLE_ROUNDS=5 SLE_DD=10 SLE_RN=1 SLE_RN3=20`) **5 통과**: R1 5 소실 0·rc93 0(중앙 9.692s) · R3 5 작성자 2 0·고아 0 · DD 20 소실 0·rc93 0 · 남 데몬 93 ✓ · 인수 ✓ · RN 세 번째 좌석 20/20 거절 · **IR(r4 A)** = T 좌석 W(1) 있을 때 S → 새 좌석 2 · S 작성자 1 · 임대 held = 2 · 작성자 = 그 claude
- 실제 HOME 임대 폴더 = 없음
- 뮤턴트 **17 KILLED / 0 SURVIVED**(A 7 = M9a(종전 키 = 고치기 전 붉음)~M9g · B 10 = M10a~M10e·M10g~M10k)
- ⚠못 본 것: `ui/src/main.ts` 타입 검사·번들(node_modules 없음) · 실제 앱 화면(sticky·settled 토스트 실물) · 실 데몬 자동 복원이 120초를 넘는 실제 장면(감시는 주입 시험으로만) · 진짜 Claude

## 확인요청 5 본문(codex 3R 처분 · 11-13 07:28~)

- 판정문 = `~/axdev/master/reviews/codex-queue-2026-11-13/3-seatkeep-t1.verdict.md`(BLOCK · blocking 2 · major 3 · 범위 7e70cdf2..28347181) · 처분 = **5건 모두 수용**(반론 0 — 다섯 다 판정문 재현 순서를 시험으로 만들어 고치기 전 붉음을 실측).
- **codex 줄**: 이 고침 뒤 codex 미수행(master#5eb8d1fc · 호출 금지) · **사후 codex 필요 = 예** · 대상 = `28347181..<이 HANDOFF 커밋>` · **codex 다음 회차에 꼭 물을 것**:
  1. 멱등 재반환 + 건너뜀 갈래의 「등록 대화 ≠ 요청 대화(등록 없음 포함) → 임대 되돌림」이 작성자 둘을 여는 길이 있는가 — 특히 등록 없음 + argv 증거 없음인데 그 좌석 에이전트가 실제로 저장 대화를 쓰는 경우(한계 2 갈래와 같은가).
  2. `auto_restore_settled`(명시 done·off 만) + 시도 2초·전체 120초 대기가 본부·부서 어디서든 「자동 복원 도는 중 사이드카 실행」(794 r2)이나 영구 대기를 다시 여는가 — 옛 데몬(칸 없음)은 이제 120초 뒤 hq_pending 이 된다.
  3. done 의 `pending` 과 부서 사정 알림(관문 포함 필터)이 어떤 조합에서 「완료」와 「확인 못 함/관문」을 함께 말하거나 관문·92·93 을 숨기는가(`ui/src/restoredone.ts` 진리표 밖 조합).

### codex 3R 처분 표

| # | 심각도 | 처분 | 커밋 | 시험 · 뮤턴트 |
|---|---|---|---|---|
| ① 멱등 재반환 좌석 ≠ 만든 좌석 | blocking | **수용·고침** — `launch_boot_skip`(재반환 + 살아 있음) 갈래에서 좌석 등록 대화 = 요청 대화일 때만 임대에 남김 · 다르거나 등록 없음 = `lease_note_launch(sid,false)` → 마무리 되돌림 · 판독 실패 = 종전 · rc 는 종전 0(역할이 앉음) + stderr 1줄 | 2e9f8026 | e2e `idempotent_reuse_of_a_seat_on_another_conversation_does_not_take_the_lease`(판정문 재현 그대로 · **고치기 전 붉음 실측** = 임대 surface=W · writer null · launching → 초록 = 임대 없음 · S 작성자 0) · 단위 진리표 4 + 배선 핀 · 뮤턴트 M5a·M5b·M5c KILLED |
| ② org.status 오류 = 복원 끝 | blocking | **수용·고침** — 끝 = 명시 `done`·`off` 만 · 오류·시한·깨진 답·칸 없음 = 계속 대기 → 상한에서 확인 못 함 | bac8bba9 | `seatkeep_3r25_…`(가짜 데몬 7모양 · **고치기 전 붉음 실측** = 연결 즉시 끊김을 즉시 「끝」) · 뮤턴트 M6a(종전 판정) KILLED |
| ⑤ RPC 정지 시 무한 대기 | major | **수용·고침** — 시도마다 일회성 연결 + 2초 시한 · 전체 = `Instant` 기한 120초 | bac8bba9 | 같은 시험(답 멈춤 → 2초 상한 안 false · 4초 안) · 뮤턴트 M6b(시도 시한 제거)·M6c(기한 제거) KILLED |
| ④ 상한 초과를 성공으로 셈 → 「완료」와 상충 | major | **수용·고침**(판단 「실패로 세지 않음」은 유지 · 성공으로도 안 셈) — `pending` 집계 · done 에 실음 · UI 「완료」 대신 「진행 중」 · 옛 자리 쓸기 무장 안 함 | 35a0d615 | `ui/src/restoredone.test.ts`(32칸 진리표 = pending 이면 어느 칸도 「완료」 낱말 0 · 다른 원인 없으면 「…결과를 확인하지 못했습니다」 = 부서 알림과 같은 말) · Rust 배선 핀 · 뮤턴트 M7a~M7d KILLED |
| ③ 부서 경로가 실패+관문 혼합을 숨김 | major | **수용·고침** — 부서 사정 알림 필터 = 관문·92·93 중 하나 | 0192bb22 | `seatkeep_3r3_…`(판정문 재현을 **부서 생산 경로**로 · 고치기 전 붉음 실측) + 16칸 · 뮤턴트 M8a(종전 필터)·M8b KILLED |
| C3 제목 표현 | 문서 | **고침** — 한계 5·6·7 머리를 「C3 = 부분만(로컬 정전에만 반론 성립) · C4·C5 = 안 닫힘·안전 반론 성립」으로 | (문서 커밋) | — |

### 바뀐 사용자 화면(새 문구 1)
- done 알림(부서 확인 못 함이 있고 다른 원인이 없을 때): 「👥 직원 복귀 진행 중 — 부서 N곳은 다시 켰지만 직원 자리 복귀가 아직 끝나지 않아 결과를 확인하지 못했습니다 — 잠시 뒤 ↻ 재시작을 눌러 다시 확인하세요.」(부서 개별 알림 「OO: 다시 켰지만 …」과 같은 말 · master 확정 문형을 따름)
- `ui/src/main.ts` 를 이번엔 고쳤다(done 갈래를 `ui/src/restoredone.ts` 로 옮김 · 종전 갈래 문안 바이트 같음 · 기존 핀 `restorebrief.test.ts` 794 r3 갱신) — ⚠t3 가지와는 안 겹침(t3 = ui 무수정).

### 전체 시험(HEAD 0192bb22 · 07:50~08:31 · 1분 부하 15~43 · JOBS 4 · 시험 일꾼 4)
- UI(bun · `ui/`) **3331 통과** · 0 실패(88 건너뜀 · 106파일) · lib **1224 통과** · 0 실패 · Tauri(cys-app bins) **344 통과** · 0 실패(앞 회차 342 + 새 시험 2) · cys bin(병렬 4) **779 통과** · 0 실패(778 + 새 시험 1)
- e2e(임대 켬 · `SLE_RR=5 SLE_ROUNDS=5 SLE_DD=10 SLE_RN=1 SLE_RN3=20`) **5 통과**: R1 5회 소실 0·rc93 0(중앙 9.331s) · R3 5회 소실 0·작성자 2 0·고아 0 · DD 복원 20 소실 0·rc93 0 · 남 데몬 93 ✓ · 인수 ✓ · RN 1회 · 세 번째 좌석 20/20 거절 · **IR(새 · ①)** 임대 없음 · S 작성자 0
- 실제 HOME 임대 폴더 = 없음(시험 뒤 `ls -ld`)
- 이번 회차 뮤턴트 **12 KILLED / 0 SURVIVED**(① 3 · ②⑤ 3 · ④ 4 · ③ 2 · ① M5b 는 e2e 가 아닌 단위 시험이 잡음 — e2e 의 가짜 claude 좌석은 다른 대화로 등록돼 있어 「등록 없음」 칸은 단위 진리표 몫)
- ⚠못 본 것: `ui/src/main.ts` 타입 검사(tsc)·번들 빌드 — 작업 폴더에 `ui/node_modules` 없음 · bun 시험은 `restoredone.ts` 를 직접 실행하고 `main.ts` 는 원문 핀으로만 본다. 실제 앱 화면의 토스트 실물·RPC 단절 주입 화면도 못 봄.

- **매듭(master#27da18af · 11-12 21:09 · 주간 한도 98% 정지)**: 하던 고침 없음 · 마지막 = 28347181(문구 결정 반영) · 다음 첫 행동 = 리셋(금 06:00) 뒤 master 지시 · 사후 codex 판정이 오면 그 판정문만 이 처분 표 형식으로 처분.

## 확인요청 4 본문(codex 2R 처분 고침 · fix2 · 11-12 08:39 착수 → 08:43 예산 정지 → 16:51 재개)

- 판정문 = `~/axdev/master/reports/2026-11-11-post-codex/codex-seatkeep-t1-1r.md`(codex 2R · BLOCK · blocking 2 · major 2) · master 처분 = 브리프 §1(전부 성립).
- **codex 줄**: 이 고침 뒤 **codex 미수행**(브리프 · master#67780dc1 ① — 내일 06:47 뒤 master 가 돌림) · **사후 codex 필요 = 예** · 대상 = `7e70cdf2..<이 HANDOFF 커밋>` · codex 에 꼭 물을 것:
  1. `run_launch_agent_opts` 가 돌려주는 「만든 좌석」이 rc 0·78·90·91 과 복원 fresh 갈래 전부에서 임대 마무리의 좌석인가 — 멱등 재반환(`idempotent_reuse`)·건너뜀(`launch_boot_skip`) 갈래에서 그 좌석이 남의 좌석일 수 있는가.
  2. 죽은 부서 재기동의 유계 대기(`wait_auto_restore_settled_on` 120초 · 막 띄운 데몬이 running/held 를 소켓 수락 전에 찍는다는 전제 = cysd `post_listen_boot`) 뒤 판정 층 1회가 794 r2(같은 역할 둘) 를 다시 열 수 있는가.
  3. `restore_note` 의 독립 원인 덧붙임 · `remeasure_failed` 꼬리가 관문·92·93 을 숨기거나 오래된 수를 지금 값처럼 말하는 길이 남았는가.

### codex 2R 처분 표

| # | codex 심각도 | 처분 | 커밋 | 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 죽은 부서 Relaunch 가 C6 알림을 안 거침 | blocking | **고침** — launch 성공 → 그 부서 소켓 자동 복원 끝을 유계 대기(240×0.5초 = 120초 · 본부와 같은 상한) → `run_sidecar_restore_judged` → `dept_restore_lease_note`(살아 있던 부서와 한 블록) · 상한 초과 = 사이드카 0 + 「확인 못 함」 `skip` 알림(실패로 안 셈 · 조용한 성공 0 · ⚠지시 없이 내린 판단 = 아래 「판단」) · launch 실패 = 종전 실패 1 | 54150878 | `seatkeep_2r1_dead_dept_relaunch_goes_through_the_same_judgment`(문안 + 배선 핀 4) · 뮤턴트 M1a(대기 생략)·M1b(알림 삭제)·M1c(launch 실패를 확인 못 함으로)·M1d(판정 층 우회)·M1e(상한 2회) **KILLED** |
| 2 rc 0·78 역할 이름 조회가 `worker→worker-N` 에서 남의 좌석 | blocking | **고침** — `run_launch_agent_opts` → `(rc, 만든 좌석)` · `RestoreLauncher::fresh` 도 같은 모양 · `lease_finish_by_rc(g, rc, seat, sess)` 0·78·90·91 전부 그 좌석 · 복원 fresh 0·78·90·91 도 · 전역 `CREATED`·`lease_note_created`·`lease_take_created` **삭제**(남길 까닭 없음) | 63696e15 | e2e `resume_saved_into_a_renamed_worker_seat_records_the_seat_it_made` — **고치기 전 붉음 실측**: 임대 `surface_id`=W1(1) · `writer`=null · state launching(판정문 재현 그대로) → 고친 뒤 W2 · 작성자 = W2 의 claude · 단위 `restore_fresh_success_finishes_the_lease_on_the_seat_it_made`(rc 0·78) · 뮤턴트 M2a(launch-agent 이름 조회)·M2b(복원 fresh 이름 조회)·M2c(90·91 좌석 None)·M2d(반환 좌석 None) **KILLED** |
| 2 전문가 칸 | — | **측정** — W1 을 닫은 직후 · W2 의 SessionStart 등록 전(가짜 claude = 훅 없음 = 등록 0) 창에서 세 번째 `--resume-saved` 20회 = **20/20 rc 92 · 작성자 1 · 새 좌석 0** | 63696e15 | 같은 e2e(`SLE_RN3=20`) |
| 3 실패+관문 섞이면 관문 알림 사라짐 | major | **고침** — `restore_note` 가 실패·관문·92·93 을 독립 원인으로 모두 덧붙임(`restore_note_base` 우선순위 삭제) · 단일 원인 문안은 바이트 같음 | f7eb0039 | `seatkeep_2r3_every_cause_is_named_truth_table`(16칸 + 판정문 재현 {관문1·92 1} → 재실측 {실패1} → 두 문안 다) · 뮤턴트 M3a(종전 「실패가 관문을 가림」)·M3b·M3c·M3d **KILLED** |
| 4 재실측 못 읽으면 첫 92·93 버림 | major | **고침** — `RestoreSummary.remeasure_failed`(앱 안 구조체 · 임대 파일 형식·판 번호 무변경) · 재실측 요약 없음 + 첫 결과에 관문·92·93 = 첫 요약 + 재확인 실패 표시 · 문안 꼬리 · 부서 알림도 같은 요약 · 첫 결과 실패뿐 = 종전 | 59bf281c | `seatkeep_2r4_failed_remeasure_keeps_the_first_lease_measure` · C7 기대값 1줄 갱신(관문 첫 요약에 재확인 실패 표시) · 뮤턴트 M4a(종전 동작 = 고치기 전 붉음)·M4b·M4c·M4d **KILLED** |
| C3·C4·C5 | 알려진 한계 | **고치지 않음** — DESIGN 「알려 두는 한계 5·6·7」에 판정문 문장 그대로 | (문서 커밋) | — |
| C8 | 문서 | **사실화** — DESIGN §11 #8 을 「본부 · 살아 있던 부서 · 다시 띄운 부서 세 갈래가 같은 판정 층」으로(#1 고침 뒤 실제와 같음) + #3·#4 문안 | (문서 커밋) | — |

### 새 알림 문구 후보(최종 = master)
- #1 상한 초과(부서 · `dept` 없는 skip 토스트): **확정(master#6706603c ①)** 「OO: 다시 켰지만 직원 자리 복귀가 아직 끝나지 않아 결과를 확인하지 못했습니다 — 잠시 뒤 ↻ 재시작을 눌러 다시 확인하세요.」 — 조사 고르는 함수·문형이 코드에 없어(`src`·`src-tauri/src`·`ui/src` 검색 · 기존 알림은 조사를 고정으로 쓴다) 이름 뒤 쌍점(후보 「OO을」은 폐기).
- #4 재확인 실패 꼬리(본부·부서) **확정(master#6706603c ② · 후보 그대로)**: 「다만 다시 확인하지 못해 위 내용은 처음 확인한 결과입니다 — 잠시 뒤 ↻ 재시작을 눌러 다시 확인하세요.」
- #3 은 새 낱말 없음(기존 네 문안을 이어 붙임).

### 판단(지시 없이 내린 것 1건)
- #1 상한 초과를 **실패로 세지 않음**(부서 집계 ok) — 데몬은 떴고 자동 복원이 아직 도는 중이라 「실패」는 사실이 아니다 · 대신 별도 알림으로 드러낸다. 실패로 세길 원하면 한 줄(`true` → `false`).

### 재현 전제 메모(#2)
- 판정문 재현(「빈 셸 W1 이 `worker` 보유 + 저장 핀 S」)은 **정상 순서로는 안정 상태가 아니다**: W1 을 만드는 순간 `persist_topology` 가 영속본의 `worker` 칸을 W1(대화 없음)로 덮어 `--resume-saved` 가 「저장 대화 없음」이 된다(실측). 실제로 열리는 창 = `launch-agent` 가 핀을 읽은 뒤 `surface.create` 전에 다른 경로가 `worker` 를 세운 경우 → 시험은 W1 생성 뒤 영속본 핀을 S 로 되돌려 이 창을 결정론으로 만든다(데몬 `system.topology` saved = 매번 디스크 판독).

### 전체 시험(HEAD f7eb0039 · 17:14~17:48 · 1분 부하 5.7~7.1 · JOBS 4 · 시험 일꾼 4)
- lib **1224 통과** · 0 실패(3 무시 · 기준선 1224 와 같음) · Tauri(cys-app bins) **342 통과** · 0 실패(2 무시 · 기준선 339 + 새 시험 3) · cys bin(병렬 4) **778 통과** · 0 실패(1 무시 · 기준선 777 + 새 시험 1 · stack overflow 0)
- e2e(임대 켬 · `SLE_RR=5 SLE_ROUNDS=5 SLE_DD=10 SLE_RN=3 SLE_RN3=20`) **4 통과**: R1 5회 소실 0·rc93 0(중앙 9.508s · p95 9.922) · R3 5회 소실 0·작성자 2 0·고아 0 · DD 복원 20 소실 0·rc93 0 · 남의 데몬 살아 있음 = 93 ✓ · 죽은 뒤 인수 ✓ · **RN(새 · #2)** 3회 · 세 번째 좌석 60/60 거절(rc 92) · 작성자 1
- 실제 HOME 임대 폴더(`~/.local/state/cys/session-leases`) = 없음(시험 뒤 `ls -ld` · No such file)
- 이번 라운드 뮤턴트 **17 KILLED / 0 SURVIVED**(#2 4 · #1 5 · #4 4 · #3 4)

### 이전 라운드 뮤턴트 19 재확인
- 원 목록(이름·변이 문자열)은 보존되지 않았다 → **같은 고침을 되돌리는 변이로 재구성 14개 = 14 KILLED / 0 SURVIVED**: C1·C2 7(`lease_launch_sent` = 기록만 있으면 참 · 새 대화 기동 유지 · 기록 없음 유지 · 쓰기 결과 불명 되돌림 · 접미 없는 마무리 되돌림 제거 · 좌석 모르는 90 되돌림 · 91 을 쓰기 결과 불명으로 안 봄) · C7 4(관문+92·93 재실측 생략 · 관문 수 합치기 제거 · 합친 결과 성공 · 판정 층 합치기 우회) · C6 3(성공 부서도 알림 · 93 만 남은 부서 알림 0 · `dept` 키 붙임 = UI 버림).
- C2 보강 3(`CREATED` 기록 · 지우기 순서)은 그 장치를 이번에 걷어 냈으므로 대상 없음 → #2 뮤턴트 M2a~M2d 가 같은 뜻(좌석 = 만든 좌석)을 잡는다.

### 겹치는 파일(병합 안 함 · master 통합 리허설 몫)
- `feat/seatkeep-t2` = 겹침 0(6파일) · `feat/seatkeep-t3` = `src-tauri/src/main.rs` · `src/bin/cys.rs`(32파일 중). ⚠두 가지 모두 `270e3e21`(v1.1.14)에서 갈라졌다 — t1 위에 쌓인 가지가 아니다(`git merge-base --is-ancestor 7e70cdf2` = no).

## 확인요청 3 본문(codex 1R 처분 고침 · 3회차 · 18:41~)

- master 결정(브리프 §1): ① M3 = **B 유지** — 「업데이트 창이 겹칠 때 그 역할이 새 대화로 바뀜(5/12 · 회귀 아님)」은 이 티켓에서 고치지 않음 → 아래 「다음 티켓 후보」 C · ② F1 = **지금은 문서만** — DESIGN 한계 2 에 결정 줄 + USER-MANUAL 복원 절 1줄(8a14eada).
- **codex 줄**: codex 1R(스냅샷 ecd8a67a · BLOCK) 뒤 고침 = **codex 미수행**(좌석은 codex 를 돌리지 않음 · 브리프 §4) · **사후 codex 필요 = 예** · 대상 = `630f1706..<이 HANDOFF 커밋>` · codex 에 꼭 물을 것:
  1. 기동 오류 뒤 임대 처분(`lease_settle_after_error` · `lease_settle_kept_rc`)이 모든 갈래(node-recover · 좌석 재연결 거절/불명/일반 오류 · 복원 fresh 90/91 · launch-agent 90/91 · 닫기 실패 91)에서 「잇는 기동 글 수락 뒤 = 유지 · 새 대화 기동 = 되돌림 · 기록 없음 = 쓰기 결과 불명만 유지」와 맞는가 — 특히 기록이 프로세스 전역(좌석 번호 키)이고 rc 갈래가 「그 기동이 만든 좌석」 기록을 쓰는 것이 다른 좌석을 가리키는 길이 있는가.
  2. C1·C2 뒤에도 작성자 없는 임대의 엄격 좌석 판정·결과 불명 유지가 정상 조건(작성자만 죽은 재복원 · 두 입구 동시 · 부서 데몬 2개)에서 거짓 93 을 만드는 전이가 남았는가 · 반대로 되돌림이 작성자 둘을 여는 길이 생겼는가.
  3. 앱 판정 층(관문 + 92·93 섞임 재실측 · 첫 결과 관문 합치기 · 부서 dept 없는 skip 알림)이 관문 알림을 잃거나 재시도 상한(1회)을 넘거나 92·93 자리를 숨기는 길이 있는가.

### codex 1R 처분 표(최종)

| # | codex 심각도 | 처분 | 커밋 | 시험 · 뮤턴트 |
|---|---|---|---|---|
| C1 새 대화 기동인데 임대 유지 | blocking | **고침** — `lease_launch_sent` = 잇는 기동(`Some(true)`)만 · 공용 처분 `lease_settle_after_error`: 새 대화 기동(`Some(false)`) = 모든 갈래 되돌림(node-recover · 좌석 재연결 불명 · fresh/launch-agent 91 · 닫기 실패 91 의 입력) | b531034d | `launch_error_disposal_follows_the_seats_launch_record`(처분 12칸) · `launch_record_decides_the_next_restore_both_ways`(복원 왕복) · 뮤턴트 M-C1a·M-C1b KILLED |
| C2 0바이트 거절도 유지 | blocking | **고침** — 거절은 그 좌석에 「잇는 기동 글 수락」 기록이 있을 때만 유지 · 기록 없음 = 기동 전 = 되돌림(쓰기 결과 불명은 기록 없어도 유지 — 기동 글이 아직 쳐질 수 있다) · 배선 = node-recover · 좌석 재연결 거절 · 복원 fresh 90 · launch-agent 90 · **보강 62f9e121**: rc 90·91 의 좌석 = 그 기동이 만든 좌석(역할 이름 조회는 `worker`→`worker-N` 이름 바꿈에서 남의 좌석을 가리켜 작성자 둘을 열 수 있었다 — b531034d 에서 내가 들인 길 · 자체 발견) | b531034d · 62f9e121 | 같은 두 시험(양쪽 = 거짓 93 0 · 작성자 둘 0) · 뮤턴트 M-C2a·M-C2b·배선 3·CR-1~3 KILLED |
| C3 rename 뒤 폴더 fsync 실패 무시 | blocking | **반론 유지(코드 무변경)** — 폴더 항목이 사라지는 경우 = 정전·커널 패닉 = 재부팅 = 모든 작성자 죽음(독립 검증 §4 「실해 없음」) · 실패를 93 으로 올리면 지원 안 하는 파일시스템에서 모든 복원이 막힘. 앞 좌석이 제안한 「실패 사건 1줄(관측)」은 브리프 할 일 밖이라 넣지 않음(📌 원하면 다음 라운드) | — | — |
| C4 되돌림 실패 무시 | blocking | **반론 유지(코드 무변경)** — 되돌림 실패 = 내 launching 기록이 남음 → 복원기가 끝나면 좌석 기록 없음 = 인수 · 좌석 있음 = 엄격 판정(빈 셸이면 93) → 작성자 둘로 가는 길 없음(보수 쪽). 사건 1줄은 C3 과 같음 | — | — |
| C5 hold/keep_unknown 쓰기 실패가 93 아님 | major | **반론 유지** — 그때는 이미 기동됨(좌석 실재) · 좌석은 기동 전에 적혀 있어 임대는 보수 상태 · 93 을 내면 「안 띄움」으로 잘못 읽힘 · 진단 줄 유지 | — | — |
| C6 부서 순회가 92·93 자리를 안 알림 | blocking | **고침** — 부서 순회가 판정 층 요약을 버리지 않고, 끝내 성공이 아니고 92·93 자리가 남은 부서만 사정 문안을 `dept` 키 없는 `skip` 으로 냄 → UI 「직원 복귀 일부 보류」 토스트(`ui/src/main.ts` 무수정 · UI 갈래 핀) · 92·93 없는 부서 실패 = 종전(집계 알림) | 8a14eada | `seatkeep_c6_org_restore_names_dept_lease_seats` · 뮤턴트 4 KILLED |
| C7 관문 + 92/93 섞이면 재실측 건너뜀 | major | **고침(합치는 방식)** — codex 안(제외 조건을 관문 단독으로 좁히기만)은 재실행이 관문을 「이미 가동 중」으로 접어 알림 0(Fable 1.1.3 M1)을 되살림 → 「관문만」(실패·92·93 0)일 때만 재실행 생략 · 섞이면 15초 뒤 1회 재실측 + `restore_merge_retry`(첫 결과 관문 있으면 최종 = 성공 아님 · 관문 수 = 큰 쪽 · 재실행 요약 없으면 첫 요약) | abd1b3c9 | `seatkeep_c7_gate_mixed_with_lease_seats_retries_and_keeps_the_gate`(재실행 6칸 · 합치기 6칸 · 배선 핀) · 뮤턴트 5 KILLED |
| C8 DESIGN §11 #8 모순 서술 | minor | **고침** — 본부·부서 공용 판정 층(F2 · C7 · 문안 · 부서 알림)을 한 서술로 | 8a14eada | — |

### 전체 시험(HEAD 62f9e121 · 19:05~19:36 · 1분 부하 3.4~4.4 · JOBS 4 · 시험 일꾼 4)
- lib **1224 통과** · 0 실패(3 무시) · Tauri(cys-app bins) **339 통과** · 0 실패(2 무시 · 새 시험 2 포함) · cys bin(병렬 4) **777 통과** · 0 실패(1 무시 · 새 시험 2 포함 · stack overflow 재발 0)
- e2e(임대 켬): R1 `SLE_RR=5` 5회 소실 0·rc93 0(중앙 9.28s · 첫 전체 실행은 기본 3회였어서 R1 만 5회로 다시 돌림) · R3 `SLE_ROUNDS=5` 소실 0·작성자 2 0·고아 0 · DD `SLE_DD=10` 복원 20 소실 0·rc93 0 · 남의 데몬 살아 있음 = 93 ✓ · 죽은 뒤 인수 ✓
- 실제 HOME 임대 폴더(`~/.local/state/cys/session-leases`) = 없음(시험 뒤 `ls -ld` 확인)
- 뮤턴트(이번 라운드) **19 KILLED / 0 SURVIVED**: C1·C2 7 · C2 보강 3 · C7 5 · C6 4(각 고침을 되돌리면 새 시험이 붉어짐 = 고치기 전 붉음과 같음)

### 이번 라운드에서 본 것 · 못 본 것
- 관측(PLAUSIBLE · 고치지 않음 · 재현 안 함): rc **0·78**(관문) 마무리는 아직 역할 이름(`system.resolve_role`)으로 좌석을 찾는다(`lease_finish_by_rc` · 복원 fresh rc 0 갈래 — 6R 이전부터). 복원 fresh 는 D-mac-2 가 이름 바꿈 기동을 막아 해당 없음 · `launch-agent --resume-saved` 를 정확히 `worker` 역할로 부르는 경로(formation)가 있으면 이름 바뀐 좌석 대신 남의 좌석을 임대에 적을 수 있다(결과 = 그 좌석 기준 판정 · 작성자 탐색 실패 → 작성자 없는 임대). 같은 「만든 좌석」 기록으로 바꾸면 되지만 브리프 범위 밖이라 목록만.
- 못 본 것: 진짜 Claude 칸(종전과 같음) · 앱 화면에서 부서 skip 토스트 실물(코드·UI 갈래 핀으로만 확인 · 헤드리스 화면 재현 안 함).

### 다음 티켓 후보(master 결정 ①② · 이월)
- **C = 업데이트 절차·데몬 쪽 관문**(결정 ① · 근거 = 위 결정 표 ① · DESIGN §6 실측 「바꿔 끼움 5/12 · 작성자 둘 0/12」): 옛 사이드카와 새 판 복원의 겹침이 실제 업데이트 창에서 생기는지 **먼저 실 앱 업데이트로 겹침 빈도 1회 측정** → 겹침 0 이면 불요 · 있으면 새 데몬이 임대를 쥔 대화의 옛 CLI `--resume`·새 대화 기동을 거절하거나 업데이트 순서에서 옛 앱 사이드카 복원을 생략.
- **F1 「같은 폴더 claude → 93」 차단**(결정 ②): 진짜 Claude 격리 프로필에서 「역할 폴더에서 사람이 claude 를 직접 켜는 빈도·프로세스 모양(argv·cwd)」으로 거짓 막힘 폭을 잰 뒤 정함.
- T1 밖 기존 결함 P1·P2 · 의문 Q1·Q2 = 아래 목록 그대로.

## 확인요청 2 본문(독립 검증 REVISE 1회 고침 · master#5e05611e)

- 독립 검증 보고 = `~/axdev/.wt/cys-seatkeep-t1-verify/docs/VERIFY-seatkeep-t1.md`(스냅샷 5e3d2a54 · REVISE · blocking 0 · major 4 · minor 4).
- **codex 줄(master#30132cb7 형식)**: 독립 재검 1회(5e3d2a54..1fb3e3a3 · REVISE → ecd8a67a 고침) + codex 1R 1회(한도 풀린 창 16:5x~17:5x · 스냅샷 ecd8a67a · BLOCK · 아래 표 · 처분 진행 = C1·C2·C6·C7 고침은 순환 뒤) · 그 뒤 고침은 **codex 미수행** · **사후 codex 필요 = 예** · 대상 = `630f1706..<C1~C7 고침 뒤 HEAD>`(복원·기동 경로의 작성자 결정 · 임대 파일 쓰기·되돌림 = 데이터 쓰기) · codex 에 꼭 물을 것:
  1. 기동 명령 「글 수락」 기록(`lease_note_launch` · 접미 부착 여부)을 기준으로 한 임대 유지/되돌림이 모든 갈래(node-recover · 좌석 재연결 · 새 좌석 실패 · rc 마무리)에서 「거절 0바이트 = 되돌림 · 수락 뒤 = 유지 · 새 대화 = 되돌림」과 맞는가.
  2. 작성자 없는 임대의 엄격 좌석 판정(빈 셸 ≠ 죽음)과 결과 불명 유지가 정상 조건(작성자만 죽은 재복원 · 두 입구 동시 · 부서 데몬 2개)에서 거짓 93 을 만드는 전이가 있는가.
  3. 앱(Tauri) 복원 판정(92 = 성공 아님 · 1회 재실측 · 관문 섞임 합치기 · 부서 경로 알림)이 관문 알림을 잃거나 재시도 상한을 넘거나 92·93 자리를 숨기는 길이 있는가.

### 처분 표

| # | 심각도 | 처분 | 커밋 | 시험·근거 |
|---|---|---|---|---|
| F1 cys 밖 argv 없는 작성자 | major | **막지 않음 — 「알려 두는 한계 2」로 문서**(사용자 값 1줄 포함) · 막는 정책은 아래 결정 표 ② | 1fb3e3a3 | 확정 판별 근거 없음(쓰기 흔적은 쉬는 세션·죽은 세션을 못 가름) |
| F2 앱 경로 92 = 성공 → 재시도 없음 | major | **고침** — 종료 코드 0 만 성공 · 기존 판정 층 1회 재실측(15초)이 92 회차에도 돎 · 남으면 「다른 프로세스가 아직 쓰는 중 — 끝난 뒤 ↻」 | a3c97b3d | Tauri restore 시험 12 초록(92 → 재시도 판정 · 성공 판정 문자열 핀 · 문안) |
| F3 6R 고침 두 갈래 시험 없음 | major | **고침** — node-recover 마무리를 `lease_settle_boot` 로 빼 행동 시험 + 배선 핀 · launch-agent 닫기 실패 = `close_failure_rc` + 배선 핀 | a3c97b3d | M25 · M26a(함수) · M26b(호출 자리) **KILLED** |
| F4 「남는 창」 서술이 실제와 다름 | major(문서) | **고침** — DESIGN §6 실측으로 고쳐 씀(작성자 둘 0/12 · 바꿔 끼움 5/12 · 옛 판은 비키지 않고 새 대화로 · 회귀 아님) · M3 재판단 표 ① | 1fb3e3a3 | — |
| F5 M05·M11·M12·M16 | minor | **고침** — 시험 추가(M11 `opened_verdict` · M12 `scan_argv_with` 주입 · M16 실제 경합 시험) | 6ebe8e93 | 네 뮤턴트 **KILLED**(M16 은 시한·경합 두 시험이 붉음) |
| F6 쓰기 실패 다음 행동 | minor | **고침** — `lease:write:*` · 「df -h · ls -ld」 | 6ebe8e93 | 시험 |
| F7 부모 심링크 · 폴더 fsync | minor | fsync **고침** · 부모 심링크 = 문서(한계 4) | 6ebe8e93 · 1fb3e3a3 | — |
| F8 비-Claude id 없는 대체 접미 | minor | 문서(한계 3) — 키 = 대화 id 라 설계상 밖 | 1fb3e3a3 | — |

### 결정 표 ① — M3 = B 를 다시 볼 근거(결정 = master)

| 선택지 | 무엇 | 업데이트 창에서 사용자 체감 | 비용·위험 |
|---|---|---|---|
| **B(지금)** | 60초 옛 claim 동률만 · 원자화 안 함 | 옛 사이드카와 새 판이 겹치면(겹침 자체 빈도 미측정) 그 역할이 **이전 대화 대신 새 대화로** 시작(5/12 · 조용함 · 이전 대화 파일은 남음) · 작성자 둘 0/12 | 변경 0 · 옛+옛보다 나음(6/8 → 5/12) |
| A | 옛 claim 잠금과 임대 판정을 한 잠금 순서로 | **바꿔 끼움은 그대로 남음** — 옛 판은 claim 을 보면 새 대화로 띄우므로(옛 판 동작은 못 바꿈) A 가 막는 것은 이미 0/12 인 「작성자 둘」뿐 | cys.rs 복원 루프·claim 잠금 재배치 · 회귀 위험 |
| C | 업데이트 절차에서 옛 사이드카의 복원을 막음(예: 새 데몬이 임대를 쥔 대화의 옛 CLI `--resume`·새 대화 기동을 거절 · 또는 업데이트 순서에서 옛 앱 사이드카 복원 생략) | 바꿔 끼움 0 을 목표로 할 수 있는 유일한 길 | 데몬 쪽 새 관문 = T1 범위 밖 · 새 티켓 |

- **권고(확신도 중)**: **B 유지 + C 를 📌 새 티켓**(먼저 「실제 업데이트 창에서 겹침이 생기는가」(검증 7항 · 아직 못 잼)를 실 앱 업데이트로 1회 잰다 — 겹침 0 이면 C 불요). A 는 사용자 체감을 못 바꾸므로 비권고. 단점: B 를 유지하면 겹침이 실제로 있는 동안 바꿔 끼움이 조용히 남는다.

### 결정 표 ② — F1(cys 밖 argv 없는 작성자)을 막을지(결정 = master)

| 선택지 | 무엇 | 사용자 체감 | 비용·위험 |
|---|---|---|---|
| **문서만(지금)** | 한계 2 로 명시 | 터미널에서 `claude --continue` 를 켠 채 업데이트/복원하면 같은 대화에 두 Claude(rc 0 · 경고 없음) | 거짓 막힘 0 |
| 폴더 관측 93 | cys 좌석 밖 + 그 대화의 프로젝트 폴더를 cwd 로 둔 claude 프로세스 → 판정 불가(93 · 「그 창을 닫거나 다른 대화임을 확인한 뒤 다시」) | 같은 폴더에서 다른 대화를 연 claude 가 있어도 그 역할이 안 뜸(사람이 닫아야) | 진짜 Claude 의 프로세스 모양(argv·cwd 판독)·빈도 미측정 → 거짓 막힘 폭 모름 · 구현·시험 반나절 |

- **권고(확신도 낮음~중)**: 지금은 문서만 + 독립 검증 좌석(진짜 Claude 격리 프로필)에서 「역할 폴더에서 사람이 claude 를 직접 켜는 빈도·프로세스 모양」을 잰 뒤 폴더 관측을 정한다. 단점: 그때까지 이 구멍은 열려 있다(드묾 근거 = 역할 폴더에서 사람이 따로 claude 를 켜야 함 · 실측 없음).

### T1 밖 기존 결함·의문(목록만 · 노브 끔에서도 같음 · 별도 티켓감)
- **P1** 복원 도중 데몬이 1초 넘게 지나 죽으면 새 데몬에서의 재복원 rc 1 「좌석 계정 프로필 미관측 — 자동 이어 기동 중단」 · 작성자 0(V4 d≥1000).
- **P2** `cys restore` 가 좌석을 만든 뒤 급사하면 다음 `cys restore` 가 rc 0 「agent 미상 — 건너뜀(claim-role로 등록된 pane)」 · 작성자 0(V6) — 「rc 0 인데 대화 안 이어짐」 모양.
- **Q1** V6 에서 부하 ≈30 때 두 번 「이미 가동 중 — 건너뜀」인데 작성자 0(표적 재현 4회 안 나옴).
- **Q2** 진짜 Claude 에서 마무리 작성자 탐색이 성공하는가(판단 ② 빈도) — 못 잼.

### 독립 재검(맥락 없는 서브에이전트 · 범위 5e3d2a54..1fb3e3a3 · 읽기만) = REVISE → 1회 고침 ecd8a67a
- 판정: blocking 0 · major 1 · minor 11. 확인된 것: F3a 닫힘(옛 갈래와 같은 뜻) · F3b 임대 없을 때 91 불가 · M05·M11·M12·F6 닫힘 · **새 「판정 불가 = 없음」 길 0 · 새 정상 조건 거짓 93 0** · Tauri 재시도 고리 없음(2회 핀).
- 처분: M1(관문·실패와 섞이면 92 자리 침묵) **고침** · m1(부서 경로는 bool 만 = 종전 문구) **문서**(UI 무수정) · m2(같은 회차 중복 92 문구) **고침**(「또는 같은 대화를 저장한 다른 역할」) · m3(93 자리 숨김) **고침**(`unknown` 칸 + 문구) · m4(배선 핀이 일부 변이를 못 잡음) **고침**(뮤턴트 return 삭제·주석 처리 KILLED) · m5(M16 시험 시간 의존) **고침**(진 쪽 판정 불가도 붉음 · 무잠금 뮤턴트 KILLED) · m6(심은 링크도 디스크 문구) **고침** · m7(F_FULLFSYNC) **고침**(libc::fsync) + bench 재측정(아래) · m8·m9 **문서 고침** · m10(거절된 기동 글도 「보냄」 = 다음 93) **고침**(기록 = 글 수락 뒤) · m11(닫기 실패 91 의 stdout 계약) **고침**(좌석 줄 · `record_kept_pane` 은 안 붙임 — 그 기록의 쓰기 종류 분류가 이 갈래에 없음).
- 재검이 못 본 것: 컴파일·실행·뮤턴트 실측(→ 위 뮤턴트는 이 좌석이 돌림) · APFS 폴더 F_FULLFSYNC 성공 여부 · 데몬 자체 복원의 92 처리 · boot_node·phoenix 의 닫기 실패 91 처리.

### codex 1R(master#6d59afca · 한도 풀림 · 스냅샷 clone `ecd8a67a` · 범위 630f1706..ecd8a67a = 6R 고침 + 이번 고침 · codex-call.sh --effort high) = **BLOCK**(blocking 5 · major 2 · minor 1)
- 판정 원문 = 스크래치 `codex-7.txt` · `codex-7.verdict.json`(이 좌석 scratchpad). 조건 5(정상 조건 거짓 93 새로 안 만듦) = **closed**.
- **이 좌석은 아직 고치지 않았다**(CTX 57%→ 순환 뒤 1회 · 아래 처분 = 내 판단 · 결정·편성 = master).

| # | codex 심각도 | 지적 | 내 판단 | 처분(제안) |
|---|---|---|---|---|
| C1 | blocking | 접미 없는 새 대화 기동(`resumed=false`)인데 기동 뒤 오류·닫기 실패에서 저장 대화 임대를 유지(`lease_launch_sent` 가 resumed 를 버림) | **맞음** — 단 결과 = 작성자 둘이 아니라 **거짓 93**(A 임대가 쓸데없이 남음) | 고침: 유지 판정을 `launched == Some(true)` 로 · `Some(false)` 면 모든 갈래에서 되돌림 + 시험 |
| C2 | blocking | 첫 기동 글 0바이트 저널 거절도 keep_unknown(기동 전인데) | **맞음** — 결과 = **거짓 93** | 고침: 저널 거절은 그 좌석에 「글 수락」 기록이 있을 때만 유지(node-recover · 좌석 재연결 · launch-agent rc 90 마무리) + 시험 |
| C3 | blocking | rename 뒤 폴더 fsync 실패를 무시 | **반론** — 폴더 항목이 사라지는 경우 = 정전·커널 패닉 = 재부팅 = 모든 작성자 죽음(독립 검증 §4 도 「실해 없음」) · fsync 실패를 93 으로 올리면 지원 안 하는 파일시스템에서 모든 복원이 막힘 | 고치지 않음 · 실패 사건 1줄만 추가(관측) |
| C4 | blocking | 되돌림의 잠금·판독·쓰기·삭제 실패를 무시 | **부분 반론** — 되돌림 실패 = **내 launching 기록이 남음** → 나(복원기)가 끝나면 좌석 기록 없음 = 인수 · 좌석 있음 = 엄격 판정(빈 셸이면 93) → 작성자 둘로 가는 길 없음(보수 쪽) | 실패 사건 1줄 추가 · 93 승격은 안 함 |
| C5 | major | hold/keep_unknown 마무리 쓰기 실패가 93 으로 안 드러남 | **반론** — 그때는 이미 기동됨(좌석 실재) · 좌석은 기동 전에 적혀 있어 임대는 보수 상태 · 93 을 내면 「안 띄움」으로 잘못 읽힘 | 진단 줄 유지(종전) |
| C6 | blocking | 조직 복원 부서 순회가 RestoreSummary 를 버려 남은 92·93 자리를 안 알림 | **맞음(가시성)** — 독립 재검 m1 과 같은 것 · 지금은 문서로만 처리 | 고침 제안: 부서 결과에 restore_note 를 실어 내보냄(Tauri 만 · `ui/src/main.ts` 무수정이 가능한지 확인 뒤) |
| C7 | major | 관문 보류 + live/unknown 이 섞이면 92 재실측을 건너뜀 | **맞음** — 단 codex 의 고침(제외 조건을 관문 단독으로 좁힘)은 재실행이 관문을 「이미 가동 중」으로 접어 관문 알림을 잃는 옛 결함(Fable 1.1.3 M1)을 되살림 | 고침 제안: 섞이면 재실행하되 첫 결과의 관문 수를 최종 요약에 합침 + 진리표 시험 |
| C8 | minor | DESIGN §11 #8 이 부서 경로를 모순되게 서술 | 맞음 | C6 과 함께 정리 |

### 전체 시험·측정(HEAD ecd8a67a · 16:48~18:01 · 1분 부하 11~13)
- lib **1224 통과** · 0 실패 · Tauri(cys-app bins) **337 통과** · 0 실패
- cys bin = **rc 101 · 「fatal runtime error: stack overflow」(SIGABRT)** — 병렬 실행 중 어느 시험이 스택을 넘김(e2bf9d77 전체 실행에선 초록) → 단일 스레드 재실행으로 범인 찾는 중(결과 = 아래 줄)
- cys 단일 스레드 재실행(load 7.9): **775 통과 · 0 실패** → 병렬에서만 죽음 = 시험 스레드 스택(2MB) 문제 · 병렬 재실행 + 완료 목록 대조 = 죽을 때 돌던 시험 = `session_lease_cli_tests::unknown_outcome_is_not_released_…`·`unknown_write_outcome_keeps_…`(임대 켬으로 `run_restore_with` 를 도는 복원 루프 시험 — 디버그 큰 프레임 + 임대 관문·argv 훑기 프레임) → **시험 helper 가 복원 루프를 32MB 스택 스레드에서 돌림**(운영은 주 스레드 8MB · 시험 쪽만) · 고친 뒤 병렬 전체 재실행(18:27~18:40 · --test-threads=4 · load 9~14) = **775 통과 · 0 실패**
- e2e(켬 · SLE 5): R1 5 소실 0·rc93 0(중앙 9.20s) · R3 5 소실 0·작성자 2 0·고아 0 · DD 10 복원 소실 0·rc93 0 · 남의 데몬 살아 있음 = 93 ✓ · 죽은 뒤 인수 ✓
- bench(부하 관문 load1 8.08 · 프로세스 1,350 · 폴더 fsync(2) 들어간 판): 중앙 **22.6ms** · p95 30.3 · 최대 37.1 / 반복 중앙 24.0 · p95 33.1 · 최대 42.4 — 12:35(fsync 전) 중앙 22.6 과 같음 = fsync 비용 무시 가능
- 실제 HOME 임대 폴더 = 없음(시험 뒤 확인)

## 확인요청 본문(1차 · 15:29)

### A. codex 라운드 표 (2R~6R · 1R 은 참고)

| 라운드 | HEAD | 판정 | 지적 | 처분 | 고침 커밋 |
|---|---|---|---|---|---|
| 1R | e0b90fca | BLOCK | B1~B3 · M1~M5 · minor(Tauri 93 문안) + 잠금 시한(master 지시) | M1 은 73a50cda · 나머지 순환 뒤 | 13dabb20 · ec019350 · 2fe84708 · e458c5ca · 3c968fe8 · ed2f113f · 7c67612d · 7f2b1c29(2데몬 e2e) |
| 2R | 7f2b1c29 | BLOCK(2 blocking · 6 major) | [b] M4 낡은 argv 제외가 진짜 작성자를 지움 · [b] B3 세대 결측 = 지금 데몬 목록으로 죽음 · [M] 등록부(MINE) 단독 기동 권한 · [M] 임대 파일 있으면 옛 claim 동률 생략 · [M] claim 판독 오류=없음·FIFO 멈춤 · [M] 기동 전 좌석 기록 실패 무시 · [M] 열거 실패 빈 목록=없음 · [M] FIFO 시험 cfg(unix) 누락 | 전부 고침 · **M4 는 되돌림(고치지 않음 = 판단 ①)** | 5c277e2b · 4181d197 |
| 3R | 4181d197 | REVISE(1 major · 1 minor) | [M] 데몬 응답 원소의 판정 필드 손상(빈 객체 · agent_alive 형식)이 없음/죽음으로 감 · [m] hold/keep_unknown 마무리 실패 무시 | 고침(데몬 생산 계약 대조 검증 · 실패 진단) + 전체 시험이 드러낸 S2 이래 붉은 시험 6 | 50fc4d51 |
| 4R | 50fc4d51 | BLOCK(1 blocking · 1 minor) | [b] 결과 불명(⑪) 임대를 빈 셸 관측으로 풀어 재획득 · [m] 시험 helper 노브 미고정·rc 버림 | 고침(결과 불명 = 엄격 판정) | 90286064 |
| 5R | 90286064 | ESCALATE | 기동 중(launching) 임대의 복원기 급사 창(빈 셸 = 죽음) — 범위 밖 상태 전이 미확인 | 고침(작성자 없는 임대는 엄격 = 판단 ②) · ⚠ESCALATE 를 master 보고 없이 닫음(이 규칙은 그 뒤 master#ae3bad7d 로 받음 · 이후 준수) | 630f1706 |
| 6R(마지막) | 630f1706 | BLOCK(1 blocking · 2 major) | [b] 기동 명령 뒤 일반 오류 = 「안 떴다」 처리(node-recover 되돌림 · in-seat → fresh 폴백 · 닫기 실패 되돌림) · [M] --no-resume·접미 없는 기동이 저장 대화 임대를 쥠 · [M] held 무작성자 모순 기록 | 전부 고침 1회(7R 없음) | e2bf9d77 |

- **codex 줄(master#3e08c923)**: codex 1R~6R 수행 완료(한도 소진 14:5x 전 · 끊긴 라운드 없음) · **6R 고침(630f1706..HEAD = e2bf9d77 · 242a035c)은 codex·독립 재검 미수행**(master#ae3bad7d: 6R 마지막 · 7R 금지) · **사후 codex 필요: 예** — 범위 `git diff 630f1706..HEAD`(복원·기동 경로 = 대화 jsonl 을 잇는 작성자 결정 · 임대 파일 쓰기 = 데이터 쓰기) · 11-13 06:47 전 발행 묶음·운영 이주 제외.

### B. 판단 ① — 남는 거짓 막힘(92 · 낡은 argv)
- 어떤 조작에서: 프로세스가 `claude --resume A` 로 떠서(argv 에 A) 그 안에서 다른 대화로 옮긴 뒤(/clear · /resume) **살아 있는 동안**, 누가 A 를 복원하면.
- 사용자에게 보이는 문구(cys restore 줄 / launch-agent 는 `[launch-agent] --resume-saved: ` 머리):
  `· <역할>: 대화 <id 앞 8자> — pid <N>(<argv 앞 4개>) 가 이 대화를 인자로 쥐고 있음 — 띄우지 않음(같은 대화 작성자 둘 차단 · 새 대화로도 띄우지 않음)` · 요약 줄 꼬리 `· 대화 작성자 살아 있음 1` · rc 92 · Tauri = 실패 토스트 없음(92 만 = 성공 bool) · phoenix = 그 역할 복원 보류(재시도·새 대화 0).
- 푸는 방법: `ps -p <N> -o pid,lstart,command` 로 그 프로세스가 A 를 쓰지 않음을 확인 → 그 프로세스(지금 B 를 쓰는 세션)를 끝낸 뒤 `cys restore` 다시. 우회 플래그 없음(노브 `CYS_SESSION_LEASE=off` 는 임대 전체를 끄므로 권하지 않음).
- 빈도 추정 근거(실측 없음 · 구조 근거): ⑴ cys 좌석 안 /clear 는 데몬이 좌석 대화 핀을 새 대화로 옮기고(handlers.rs usage-register clear 재핀) persist_topology 가 저장 핀을 갱신 → 그 역할의 복원 대상이 A 가 아니게 됨 ⑵ 복원은 좌석이 앉은(occupied) 역할을 건너뜀 → 같은 좌석 경로로는 거의 안 생김. 남는 길 = **cys 좌석 밖**(일반 터미널에서 직접 `claude --resume A` 후 /clear 등)에서 연 프로세스가 살아 있는데 A 의 역할을 복원 · 또는 여러 역할이 같은 대화를 가리키는 저장 상태.
- 재현 장면(독립 검증 좌석용): 격리 상자에서 일반 셸로 `claude --resume <A>` → 그 안에서 /clear → 그 프로세스 살린 채 `cys restore`(A 를 저장한 역할) → rc 92 + 위 문구.

### C. 판단 ② — 작성자 없는 임대는 언제나 엄격(93)
- 어떤 조작에서: 기동 쓰기 결과 불명(⑪) · 복원기가 기동 명령 뒤 결과를 적기 전 급사 · 기동 명령 뒤 일반 오류 · 마무리에서 작성자를 못 찾은 기동(실제 Claude 빈도 미실측) — 그 좌석이 빈 셸로 남아 있는 동안 같은 대화 복원.
- 문구: `· <역할>: 대화 <8자> 작성자 생존 판정 불가(lease:outcome-unknown:daemon:seat-empty-unconfirmed:<sid>:<sid> 또는 daemon:seat-empty-unconfirmed:<sid>) — 띄우지 않음 · 확인: `cys read-screen --surface surface:<sid>` 로 그 좌석이 이 대화를 잇는지 보고, 아니면 그 좌석을 닫은 뒤 다시 실행하세요` · rc 93.
- 푸는 방법: `cys read-screen --surface surface:<sid>` 확인 → 빈 셸이면 `cys close-surface surface:<sid>` → `cys restore`.
- 빈도 근거: 정상 흐름은 마무리(hold)·등록(follow)이 작성자를 적어 이 상태가 남지 않음(e2e R1·R3·DD 정상 조건 rc93 = S4 수치) · ⚠마무리 작성자 탐색(argv + 좌석 뿌리 자손 · 3회×500ms)이 **실제 Claude** 에서 실패하는 빈도는 미실측(독립 검증 좌석 몫 · 6R missing 과 같은 항목).

### D. 사고(실제 HOME 임대 폴더) — 라이브 무영향 근거 + 재발 방지
- 근거: 라이브 데몬 pid 90624 = `/Applications/cys.app/Contents/MacOS/cysd`(1.1.14) · 라이브 `cys`·`cys-app`·`cysr`·`/usr/local/bin/cys` 바이너리와 `~/.cys/pack/bin` 에 `session-leases`·`CYS_SESSION_LEASE` 참조 0(strings/grep 실측) → 그 폴더를 읽는 코드가 라이브 판에 없음 · 폴더 내용 = 12:59:53 한 프로세스(시험 pid 85589) 단독 기록 69줄.
- 재발 방지: e963c78f — 시험 빌드에서 lease_store 가 실제 계정 HOME(passwd)이면 디스크 접근 전 실패 · 뮤턴트(가드 무력화) KILLED · 전체 시험 뒤 실제 폴더 미재생성 확인(full.sh 끝 검사).

### E. 전체 시험(HEAD e2bf9d77 · 13:29~14:03 · 부하 고지 전 시작)
- lib 1222/1223 — 붉음 1 = raw_command_new_census_is_frozen(내 시험의 원시 Command::new) → 242a035c 고침 · 단독 재실행 초록
- cys 전부 초록(rc 0)
- cysd 3226/3227 — 붉음 1 = native_publication np_native_same_pid_exec_is_changed_not_agent_death("fixture did not establish same-PID exec Changed") — 이 가지 무관 영역 · 부하 내려간 뒤(15:2x · 1분 부하 10.4) 단독 재실행 = **초록**(1 passed · 6.0s) → 부하 탓(이 가지 무관)
- python phoenix 시험: 붉음 2(test_phoenix_e2e_replacement · test_phoenix_w2_untomb_fullcycle) = `_HarnessError(aliased_harness_root)` — **기준 판 270e3e21 의 팩으로도 같은 실패**(git archive 대조) · TMPDIR 를 정규 경로(/private/var/…)로 주면 둘 다 rc 0 = 환경(/var → /private/var 별칭) · boot_node 시험 = 파일 없음(글롭 불일치 · 실패 아님)

### F. S4 재측정(HEAD 242a035c · 격리 상자 · 가짜 claude · 부하 관문 통과 load1=7.98 · 14:37:29 시작 · 켬 끝 15:13 load {10.38 13.40 14.20} · 끔 끝 15:21 load {12.02 10.56 12.09})

| 측정 | 켬(기본) | 끔(대조군) |
|---|---|---|
| R1 같은 데몬 600초 안 재복원 | 100회 · **소실 0 · rc93 0** · `cys restore` 벽시계 중앙 9.702s · p95 10.208 · 최대 11.017(기동 포함 · 측정 중 부하 10~14 로 올라감) | 20회 · 소실 20/20(붉음 = 시험이 임대를 잰다) |
| R3 restore ∥ launch-agent --resume-saved | 100회 · **소실 0 · 작성자 2 0 · 저장 핀 고아 0** | 20회 · 소실 19 · 고아 19 |
| DD 부서 데몬 2개(같은 HOME) 동시 재복원 | 100회(복원 200) · **소실 0 · rc93 0**(조건 ③ 두 데몬 거짓 막힘 0) · ⑵ 살아 있는 남의 데몬 좌석의 결과 불명 임대 = 93 other-gen-alive ✓ · ⑶ 그 데몬 죽은 뒤 = 인수 rc 0 ✓ | 20회(복원 40) · 소실 38 |
| 임대 판정 구간(bench · 잠금→판정→기록→argv 훑기 · 데몬 조회 제외 · n=100) | 15:26 load 8.71 · 프로세스 ~1,350 → 중앙 69.7ms · p95 140.9 · 최대 816.1 / 반복 3회(load 10.1·13.3·12.2) 중앙 44.7·41.7·100.9ms | — |

- ⚠bench 는 부하에 크게 흔들린다: 같은 판정 경로가 12:35(load ~7 · 프로세스 ~1,180)에는 중앙 22.6ms · p95 36.6 이었다 — 그 뒤 bench 경로의 코드 변화 = 열거 자기 확인 1줄 · held 무작성자 판독 검사 1줄뿐 → 증가분은 환경(14:23~ master 새 좌석 10기 부하)으로 본다. **조용한 기계에서의 재측정은 독립 검증 좌석 몫**(남는 창 길이 근거).
- 끔 대조군은 붉어야 정상(rc 101 = 시험 3개 붉음).

## 남는 창 — 옛 판·새 판 동시 복원(M3 = B 로 지원 범위 밖 · 숨기지 않음)

> ⚠이 절은 1차 서술(이론)이다 — 실측(독립 검증 F4)으로 고친 정본 = DESIGN §6 「남는 창」 · 위 확인요청 2 결정 표 ①. 실제 위험 = 작성자 둘(0/12)이 아니라 대화 바꿔 끼움(5/12).

- 조건: 같은 대화를 **임대를 모르는 옛 판 `cys restore`**(업데이트 창의 옛 앱 사이드카) 와 새 판 복원이 **거의 같은 순간**에 잇는다.
- 경로: 새 판이 「옛 판 60초 claim 없음」을 본 뒤 임대를 잡고 바깥 증거를 보는 사이(임대 판정 + argv 훑기 시간 — S4 숫자 참조) 옛 판이 claim 파일을 만들고 데몬 live 를 본다(새 판 좌석은 아직 등록 전) → 둘 다 `--resume` = 이론상 작성자 2.
- 지속 시간: 새 판의 「옛 claim 확인 → 호환 claim 만들기」 구간 ≈ 임대 판정 구간 실측(중앙 22.4ms · 최대 43.2ms · 데몬 조회 제외) + 데몬 조회 — 수십 ms 자릿수. 옛 판 쪽 claim→기동 시간이 더해지면 창이 더 넓을 수 있다(고침 뒤 재측정).
- 왜 받아들이나: 옛 판 사이드카는 교체 직후 사라지고, 같은 대화를 같은 순간 두 판이 잇는 길은 업데이트 창의 앱 사이드카 하나뿐이다(설계 §4 입구 6). 검증에서 실제 겹침이 관측되면 A(옛 claim 잠금과 임대 판정을 한 잠금 순서로)로 간다.

## 독립 검증 좌석이 볼 것(DESIGN §7 5항 + master 추가 + 이번 라운드)

1. 임대 키가 같은 대화를 하나로 묶는가(경로 제외 근거 · 대소문자 · 공백).
2. 판정 불가 경로가 실제로 안 띄우는가(생존 판독 실패 · 권한 · pid 재사용 · 깨진 임대 · FIFO · 데몬 무응답 · argv 판독 실패 · 열거 실패 · 응답 원소 형식).
3. 보유자 죽음 뒤 인수 경합(두 복원자 동시)에서 하나만 이기는가 · 옛 가드 ABA(token).
4. 이유 표시가 rc(92/93)로도 드러나는가 · rc 0 새 대화 은폐 0.
5. 모든 복원 입구가 임대를 거치는가 — 설계 §4 입구 9개 독립 재계수 + `boot_agent_on_surface` 불변식(`lease_resume_unheld` · 디스크 임대 대조).
6. 진짜 Claude 0/9(master 가 격리 프로필 로그인으로 마련 · 이 좌석은 못 잼).
7. 실제 업데이트 창에서 옛 사이드카와 새 판의 복원이 겹치는 순간이 생기는가 — 생기면 M3 를 A 로.
8. **판단 ① 재현**(위 B 장면) · **판단 ② 의 실제 Claude 빈도** — 마무리 작성자 탐색(argv + 좌석 뿌리 자손 · 3회×500ms)이 진짜 Claude·관문 보류(EXIT_GATE_PENDING)에서 성공하는가(실패하면 작성자 없는 임대가 남아 그 좌석이 빈 셸일 때 93).
9. 조용한 기계에서 bench(`cargo test --lib session_lease::bench -- --ignored --nocapture`) 재측정 — 남는 창 길이 근거.
10. 6R 고침(630f1706..HEAD)은 리뷰 미수행 — 사후 codex(11-13 06:47 뒤 · master).

## 다음 첫 행동(순환 뒤 1줄)

master 답(【확인요청 7】)을 기다린다 — r5 = T1 마지막 왕복(ACCEPT 아니면 master 가 노브 끔으로 1.1.15 · 뿌리 고침 1.1.16) · ⛔codex 직접 호출 금지. (옛 줄:) master 답(【확인요청 3】)을 기다린다 — 수용이면 좌석 닫힘 · 사후 codex 결과가 오면 그 판정문만 처분(같은 처분 표 형식) · ⛔codex 직접 호출 금지.

## 함정

- 진짜 Claude 0/9 칸 = **못 잼**(master D1=A · 격리 프로필 로그인은 master 가 독립 검증 단계에서).
- 윈도우 대상 빌드 점검 = **못 잼**: 기준선부터 `libsqlite3-sys` 가 맥에서 `cc --target=x86_64-pc-windows-msvc` 로 C 컴파일 실패(11-11 10:28 · `target/wincheck`). 윈 실기는 master 편성.
- 빌드 폴더: 운영 `target/` 은 다른 cargo 와 잠금 다툼 → 이 티켓은 `CARGO_TARGET_DIR=target/s1` 을 쓴다.
- e2e 상자: env 를 비우고 HOME·CYS_SOCKET·TMPDIR 을 `/tmp/cys-sle-<pid>-<tag>` 로 · `CYS_NO_AUTORESTORE=1` · 가짜 claude = `tests/fixtures/fake_claude.c` 를 상자 `sbin/claude` 로 컴파일 · 프로세스 종료 = 환경 HOME 이 상자인 가짜 claude pid 만 · 좌석 정리 = `surface.close cause=reap only_if_empty`(묘비 0).
- `launch-agent --resume-saved` 시험은 `--cwd <proj>` 필수(안 주면 시험 프로세스 cwd 로 떠서 저장 jsonl 을 못 찾고 새 대화).
- 작성자 죽인 직후 데몬 좌석 상태는 watchdog 틱만큼 늦게 「empty」가 된다 — R1 은 `wait_seat_empty` 로 기다린다.
- 옛 claim 600초 TTL 상수는 그대로 · 임대 켬일 때 판정에 쓰지 않고 옛 판 복원기의 60초 안 claim 만 동률(`FOREIGN_CLAIM_TIE_SECS`) · 임대 파일이 있는 대화는 claim 을 아예 안 봄.
- CliWorld.seat 는 「데몬 세대가 다르면 그 좌석은 죽음」 전제(T1 = 좌석이 데몬과 함께 SIGHUP) — **T2~T4(좌석 보유 장치)가 켜지면 깨진다**. T4 입양이 임대를 다시 확인해야 함(코드 주석 + DESIGN T0 §3 단계 4).
- ⚠(r5 정정) 가짜 claude(`tests/fixtures/fake_claude.c`)는 기동 때 `cys usage-register` 로 **등록을 한다**(옛 「훅 없음 = 등록 0」 서술은 틀림) — 등록 없는 좌석이 필요하면 데몬 env 에 `FAKE_NO_REG=1`(e2e `Box_.no_reg`).
- 훅이 없는 좌석(격리 시험 구성 등)은 follow 가 안 돈다 → 그 좌석의 대화 교체는 같은 데몬 live 증거로만 막힘.

## 재현

```bash
cd ~/axdev/.wt/cys-seatkeep-t1
export PATH=$HOME/.cargo/bin:$PATH CARGO_TARGET_DIR=target/s1
cargo test --lib session_lease                 # leaf 12
cargo test --bin cys session_lease_cli_tests   # R2 + 주입 표식 2
SLE_ROUNDS=5 cargo test --test session_lease_e2e   # R1 · R3(실 cysd · 가짜 claude)
CYS_SESSION_LEASE=off SLE_ROUNDS=5 cargo test --test session_lease_e2e   # 대조군(붉어야 함 · S4 에서 시험 이름으로 고정 예정)
```
