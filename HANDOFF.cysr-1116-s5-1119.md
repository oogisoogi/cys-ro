# HANDOFF — TICKET=cysr-1116-s5-1119 (화면 조각 5 · 멈춤·깨우기·다시 켜기·물러남 + S1-5·S1-8·S1-10)

- 브리프 = `master/briefs/1116-full/s5.md`(master#44d5feb1) · 가지 `feat/1116-s5` ← `integ/1116` **dea2e1853** · 좌석 worker-1116s5(surface:2262 · 계정2)
- 설계 = `cysr-ui-research/P2-DESIGN.md` §6(6-1·6-2·6-3) · §7 4군 ①② · §11 조각 5 행 · 시안 `P2-mock` c4-waking·c4-wakefail·c5-*
- 비가역 0: push · 태그 · CI · gh 쓰기 · 서명 · 발행 · 이 기기 앱 교체 · 박사님 데몬/좌석 = **안 함**(실물은 격리 HOME 데몬 · 가짜 claude 만)

## 0. 한눈 요약

| 무엇 | 결과(관측) |
|---|---|
| 판정(순수) `ui/src/views/judge/revive.ts` | 축 6(surface_gone·surface_exited·shell_proc_dead·agent_dead·seat_vacant_no_meta·agent_never_started) + vacant(앱 저장소 `cys-master-seen`·`cys-master-gone`) + 관문(§6-3) + 조용함(§6-1) → 띠 하나 · 길(§6-2 표) · 거절 다음 걸음 · 성공 판정 · 옛 빈 셸 정리 대상 |
| 장부 `ui/src/views/revive.ts` | 깨우기 = `chat_send{kind:auto}` 1건(원문 §6-1) · 5분 거름(저장) · 사람 보내기 뒤 30초 묶임이면 그 뒤 · 120초 무반응 → 「마스터 다시 켜기」+「도움 요청 보내기」 함께 / 다시 켜기 = 누름 1 → `start_master` ≤ 1 · never = 옛 좌석 사람 입력 0 확인 → `close_surface` → `start_master` · 거절 = `role.claim_denied` 의 `seat_not_claimable` ∧ 사람 입력 아님일 때만 65초 뒤 1회 · 복원 중 잠금 · 관문 보류 뒤 잠금 · boot-degraded 안내 · 성공 = 좌석 id 바뀜 ∨ 같은 좌석 되살림(전에 생존 아님) ∧ 생존 ∧ 관문 없음 · 옛 빈 셸 정리 = 신원(번호 + 생성 시각) 일치만 |
| 띠 `ui/src/views/chat/reviveband.ts` | 대화 화면 맨 위(확인 대기 띠 위) · textContent · 신뢰 클릭만 · 잠긴 단추 aria-disabled + 「…중」 · 관문 「작업 화면에서 답하기」 = 전환 + 마스터 창 포커스 + 작업 화면 위 안내 줄(`index.ts` `.vs-hint`) |
| 데몬(가산 · 허용 범위) | `Surface.human_input_seq`(현재 찍기 번호)·`human_input_issued`(발급기 · 줄지 않음) · `surface.send_text` 응답 `human_input_stamp`(S1-5) · 「창이면 쓰지 마라」 원자 제출이 쓰기 줄 인계 전에 끝나면 찍기 되돌림 = drop 가드(S1-10) · `org.status` 행 `human_input_stamp`·`agent_seen` · `role.claim_denied` `seat_human_recent` |
| viewcore | `chat_send{kind:"auto"}` = 큐 · `machine_origin:true` · `human:false` · owner_token 만(operator_token 0 = 원장 기록 · 임무 아님) · 결과 queued/failed/uncertain · S1-8 `write_stalled`·`write_failed` = 못 보냄 + 다시 보내기 |
| 화면 문턱 | S1-5 짝짓기 = 행 `human_input_stamp` = 내 마지막 원자 제출 표지면 「사람 입력 30초」 쉼 면제(입력줄 잔존·바쁨은 그대로 막음) |

## 1. 커밋(dea2e1853 위 · 전부 이 가지)

| 커밋 | 내용 |
|---|---|
| 4390f7a50 | 조각 5 본체 + S1-5·S1-8·S1-10 + 시험 39 |
| 6f4ebeccc | 옛 빈 셸 정리 = 등록 에이전트 좌석만 |
| d989b4e56 | codex 1R(BLOCK) 처분 + 실물 1회차(멱등 재사용) 반영 + e2e revive_gate.py |
| 4f224a25b | 실물 2회차(phoenix 회생 → 자동 1회 기다림 거둠) · 데몬 시험 ⑤ · 실물 증거 |
| 7dcdba6c3 | codex 2R(ESCALATE) 처분 — 가드 꼴 좁힘 · 복원 잠금 권위값 · 빈 좌석 증거 종류별 90초 · 등록 없는 빈 좌석 꺼짐 = 그 좌석 신원 |
| b05cc1a51 | e2e revive_gate 하네스 고침(잠긴 단추 force 클릭 · agent_alive null 행 덮어쓰기 · 클릭 전 기록 비움) |
| (이 HANDOFF 커밋) | 문서 |

## 2. 바뀐 파일(`git diff --numstat dea2e1853..4f224a25b`)

| 파일 | 누구 | +/− |
|---|---|---|
| `src/bin/cysd/handlers.rs` | **원작자** | 195/4(그중 시험 109) |
| `src/bin/cysd/state.rs` | **원작자** | 8/0 |
| `ui/src/main.ts` | **원작자** | 1/1(bootViews 배선 1줄) |
| `src-tauri/src/viewcore.rs` | 우리(조각 1) | 96/8 |
| `ui/src/views/{core,index}.ts` · `judge/gate.ts` · `chat/index.ts` · `views.css` | 우리(조각 1·3·4) | 64/2 · 43/0 · 20/1 · 5/1 · 16/0 |
| `ui/src/views/judge/revive.ts` · `revive.ts` · `chat/reviveband.ts` · `revive.test.ts` · `ui/e2e/revive_gate.py` | 새 | 275 · 455 · 80 · 785 · 210 |
| `docs/ui-p2/evidence/s5/real-daemon.txt` | 새 | 실물 증거 |

## 3. 원작자 파일 변경 줄(NFR-F3 예외 · 브리프 「데몬 변경 허용」)

- **state.rs**: `Surface` 에 칸 2개(`human_input_seq`·`human_input_issued`) + 생성자 2줄. 기존 칸·순서 변경 0.
- **handlers.rs**(운영 코드 · 전부 덧붙임 · 지운 4줄 = 원래 `last_human_input` 찍기 3줄을 함수 호출로 · `seat_blocked` 칸 줄 끝 쉼표):
  1. `try_write` 앞에 `HumanStamp` · `stamp_human_input` · `unstamp_human_input` · `human_input_stamp_label` · `HumanStampGuard`(Drop) 정의(≈57줄).
  2. `surface.create` 특권 역할 거절: `seat_human_recent` 계산 7줄 + `role.claim_denied` payload 에 칸 1개.
  3. `surface.send_text`: 사람 찍기를 `stamp_human_input` 로(같은 조건) + 가드 생성(refuse_on_approval 일 때만) · `try_write` 오류 갈래 주석 1줄 · 쓰기 줄 인계 직후 `stamp_guard.commit()` · 응답 `result["human_input_stamp"]`.
  4. `org.status` 행: `human_input_stamp` · `agent_seen` 가산 키 2개.
  - 키보드(자판) 입력 길(refuse_on_approval 없음)은 바이트 같음 — 가드 없음 · 찍기·번호만 오름(대조 시험 ③).
- **main.ts**: `bootViews({...})` 한 줄에 `focusSeat`(jumpToSurface) · `openHelp`(openFeedbackModal) · `restoring`(briefGate) 세 칸.
- main.rs·index.html·build.sh·governance.rs **0줄**.

## 4. 수용 기준 표(브리프 「시험(조각 5)」 · §6-2 · §11 조각 5 행)

| # | 기준 | 판정 | 근거 |
|---|---|---|---|
| 1 | 축 6 각각 → 글·길 | **통과** | revive.test 「축 6 + vacant + never_started 판정」 6건 · 「surface_gone →…」·「surface_exited · agent_dead · seat_vacant_no_meta · shell_proc_dead → start_master 1」 · 축 이름 = governance.rs `as_str` 핀 |
| 2 | vacant(회수 뒤 · 앱 새로 켬) | **통과** | 「vacant(…앱 새로 켬…) → 꺼짐 띠 즉시 → start_master → 성공 뒤 옛 빈 셸 정리」 · e2e A |
| 3 | never_started 닫기 길(사람 입력 0 확인 → close → start) · 사람 입력 있으면 닫지 않음 | **통과** | 단위 2건(순서 `close_surface:5` → `start_master`) · e2e C·C2(진짜 클릭) |
| 4 | 사람 입력 사유 fixture → 자동 재시도 0 | **통과** | 「거절 사유 = 사람 입력(seat_human_recent · 사유 원문)」 2꼴 · 실물 ⑥ `seat_human_recent:true` 실사건 |
| 5 | 거절 3회 주입 → 자동 재시도 ≤ 1 | **통과** | 「거절 3회 주입 … 30분 지나도 start_master 2」(한 차례 ≤ 1 · 사람이 다시 누르면 새 차례) |
| 6 | 연타 20 → 호출 1 | **통과** | 단위(다시 켜기 20 → 1 · 깨우기 20 → 1) · e2e B(진짜 클릭 20) |
| 7 | 다시 켜기 뒤 CSO·워커 좌석 수 같음(중복 0) | **대역 통과 · 실물(데몬 CLI 길) 통과 · 앱 팀 부트 체인 측정 대기** | 단위·e2e B · 실물 ③⑤ `{master:1,cso:1,worker:1}` 전후 같음. ⚠실물은 `cys launch-agent --role master`(start_master 의 첫 단계)만 — 앱 `start_master` 가 이어 돌리는 `spawn_orchestra_boot`(javis_bootstrap.py run)는 앱 실기에서만 잰다 |
| 8 | 옛 사람 입력줄 바이트 변화 0 | **통과(화면 쪽) · ⚠실물이 찾은 예외 막음** | revive.ts 의 invoke = org_status·start_master·close_surface·chat_send(auto) 만(정적 핀) · 다시 켜기 동안 쓰기 호출 0(단위·e2e). 실물 ⑤-1회차: 120초 안 같은 role+agent+cwd 다시 기동은 launch-agent 가 **같은 좌석을 멱등 재사용**해 기동 줄을 `clear_first` 없이 그 셸에 친다 → 모든 축에서 옛 마스터 창에 초안·30초 안 입력이면 다시 켜지 않음(단위 「다른 축도 초안이면 켜지 않음」·「30초 안 사람 입력」) |
| 9 | 앱 새로 켬 + 마스터 이미 꺼짐 → 꺼짐 띠 | **통과** | 단위 2건(신원 저장 · 놓아짐 기록) · e2e A · 새 설치(기록 0) → 띠 0 |
| 10 | 성공 = 좌석 id 바뀜 ∧ 생존 ∧ 관문 없음 | **통과(+같은 좌석 되살림 · 설계 개정 📌)** | 단위 「성공 판정」 · 실물 ⑤ 2회 모두 같은 좌석(surface:1)에서 되살아남 = id 만 보면 거짓 실패 |
| 11 | 거절 사유 칸 · 65초 1회 | **통과** | 단위 · 실물 ⑤ 2회차 `seat_blocked:"seat_not_claimable"` 실사건 |
| 12 | boot-degraded | **통과** | 단위(다시 켠 뒤 5분 안만) |
| 13 | 복원 중 잠금(phoenix 경합 F5) | **통과** | 단위 2건(사건 · 앱 수명 값) · e2e F |
| 14 | registry 실패 물러남(FR-V7) | **통과** | e2e G(띠 그리기 예외 주입 → 작업 화면 + 물러남 띠) |
| 15 | 관문(§6-3) 띠·작업 화면에서 답하기·통과 뒤 닫힘 | **통과(대역)** · 실물 새 프로필 첫 기동 = 측정 대기 | 단위 · e2e E |
| 16 | S1-5 짝짓기 | **통과** | 단위(표지 같음 = 면제 · 다르면·모름·세대 다름 = 붙잡음 · 잔존·바쁨 그대로) · cysd 시험 · 실물 ② 응답 표지 = 행 표지 |
| 17 | S1-10 승인 창 거부도 사람 입력 시각 → 되돌림 | **통과** | cysd 시험(clear_first_unsupported · typing_guard 초안 게이트 · 성공 commit · ABA) · 실물 ⑦ no_agent 거부 뒤 표지 그대로 |
| 18 | S1-8 write_stalled·write_failed = 못 보냄 + 다시 보내기 | **통과** | viewcore 시험 · codex 1R D 「채널에 못 들어감 = 바이트 0 맞음」 |
| 19 | 윈 실기 | **측정 대기(master 실기)** | 브리프 |

## 5. 시험 숫자 전후(기준 = dea2e1853)

- 틀 = master 게이트 스크립트 `gate-1116.sh`(pubcand 좌석 판) 사본을 `GATE_ONLY` 로 바뀐 대상만 · 격리 HOME/TMPDIR · `CARGO_BUILD_JOBS` 6(1회차) → **4**(2회차 · 운영 공지 master#68fc9186) · 결과 폴더 = 스크래치 `g1/`·`g2/`
- 기준선 화면 수치 = dea2e1853 임시 worktree 실측 · 기준선 cysd·cys-app = 실측 안 함(앞 게이트 값과 내 시험 수로 대조)

| 대상 | 기준 dea2e1853 | 이 가지 | 차이 사유 |
|---|---|---|---|
| bin cysd | (3334 추정 = 아래 1회차 − 내 시험 2) · 0 · 17 ign | 1회차 4390f7a50 = **3336 · 0 · 17**(부하 ~25) · 2회차 4f224a25b = 3320 · **16 붉음**(부하 24) → 16건 단독 재실행 = 15 초록(부하 24) · 남은 1건 `seat_proc::seatkeep_input_ack_waits_while_consumer_runs_and_stdin_unread`(`handshake_timeout`) = 부하 8.7 단독 **2/2 초록** · 그 뒤 7dcdba6c3(가드 조건 좁힘만) = `s5_1116_*` 2/2 | +2 = `s5_1116_claim_denied_carries_seat_human_recent` · `s5_1116_human_input_seq_paired_and_restored_on_refusal`. 16 붉음 = 앞 시험이 `ACL_ENV_LOCK` 을 쥔 채 10초 픽스처 시한으로 죽어 뒤 시험 PoisonError 연쇄(사유 전문 `g2/bin-cysd.log`) · seat_proc·seatkeep·native_publication·pty_admission·receipt_framing·send_settle 파일 변경 0줄 |
| cargo `-p cys-app --bin cys-app` | 348 · 0 · 2(앞 게이트 ea9812306) | **350 · 0 · 2** | +2 = viewcore `auto_params_…`·`classify_auto_…` |
| bun test(ui 전체) | **3747 pass · 0 fail**(3835 · 123 파일) | 2회차 **3795 pass · 1 fail**(3884 · 124 파일) → 붉음 1 = `tickrec.test` 「링 200칸 … 최악 장면」 5초 시한(12.3초 · 부하) · 단독 21/21 초록(부하 18.1 · 8.7 두 번) | +49 = revive.test.ts · tickrec.test 무변경 |
| `bun test ./src/views` | 287 | **336**(287 + 49) | |
| tsc(typescript@7.0.2) | rc 0 | **rc 0**(2회차 · 음성 대조 적색 확인) | 1회차 붉음 = 시험 파일 `toMatchObject`(bun-env 매처 선언 밖) → pick+toEqual 로 바꿈 |
| e2e tickrec_gate(작업 화면 동작 변화 0) | sha 308dd2b91f9a | **PASS · 새 = 기준 sha `308dd2b91f9a`**(꺼짐·켜짐 모두) | main.ts 배선 1줄이 invoke 열·저장소·화면 글자를 안 바꿈 |
| e2e revive_gate(새) | — | **PASS 21 / 0**(A~G · `docs/ui-p2/evidence/s5/revive-gate.txt`) | 2회차 게이트 안 실행은 하네스 결함 3건으로 붉음 → 고친 뒤 단독 PASS(b05cc1a51) |
| e2e chat · confirm · cc_popover_z · restart_confirm · rolereuse · restart | PASS | **전부 PASS** | |
| CI 팩 단계(ci-branch.yml 3잡 · cifix 좌석이 뗀 step 스크립트 그대로 · 실패해도 계속 = LANE-FAIL 줄) | cifix 기준 로그: mack LANE-FAIL 1(`test_hook_r34`) · ubuntuk 1(같은 것) · phx 0 | **mack 7 · ubuntuk 4 · phx 1**(01:08~02:43 · 부하 7~25) → ① `test_hook_r34` = 기준과 같은 붉음(DL-1b 시한) ② `test_role_authority`·`test_role_authority_shell`·`test_owner_desk`·`test_pyseal_negative_specimen`·`test_capgate_hook_shell`·`test_refl_inject_context_role_canon` = 단독 1차에 3건 붉음 → 2차 단독 **6/6 초록**(기준 dea2e1853 worktree 에서도 같은 3건 초록 · 부하 ~9) ③ **`test_phoenix_c6_reap` = 단독(부하 5.7)에서도 「S5 bounded observation timed out」 · 기준 대조 못 함(기준 worktree 에 빌드 없음 · 상한 초과)** → **미판별 · 📌 독립 검증 좌석이 기준·이 가지 같은 틀로 대조** | 팩 파일 변경 0 · ③ 은 phoenix 가 cysd 를 띄워 관측하는 시험이라 데몬 가산 칸과 무관하다고 단정하지 않음 |
| 뮤턴트 | — | TS 15 + 8 + 3 = **26/26 적색** · 데몬 환경값 분기 4 + 3 = **7/7 적색**(S5M=1 「commit 지움」 은 처음 살아남음 → 시험 ⑤b 추가 뒤 적색) | 도구 `docs/ui-p2/evidence/s5/mut_ts*.py` |

## 6. codex

- **1R = BLOCK**(blocking 2 · major 7 · minor 2) — 원문 `docs/ui-p2/evidence/s5/codex-r1.json` · 처분:

| 지적 | 처분 |
|---|---|
| B1 조회 뒤 비원자 close_surface(사람이 그 사이 치기 시작) | **완화** — 누름 안에서 다시 받은 행으로 곧바로 판정·닫기 + 「30초 안 사람 입력 · 입력 시각 모름」도 닫지 않음. 남는 창 = 다시 받은 org.status 응답과 close 요청 사이(같은 이벤트 고리 안 수 ms) ∧ 30초 넘게 조용하던 사람이 그 순간 첫 글자. **원자 조건부 닫기(데몬 `surface.close` 요청 조건 칸) = 허용 범위(응답 칸·사건 칸) 밖 → 📌 P1** |
| B2 저장 번호 재사용으로 엉뚱한 좌석 닫기 | **닫음** — 신원(번호 + 데몬 created_at) 일치 + 등록 에이전트 좌석 + 역할 없음 + Empty + 사람 입력 0 만 · 옛 꼴(번호만) = 닫지 않음 |
| M1 쓰기 0 갈래 되돌림 누락 | **닫음** — drop 가드 · 쓰기 줄 인계 직후 commit(초안 게이트 typing_guard 갈래 시험으로 확인) |
| M2 seq-1 ABA | **닫음** — 발급기 단조 + 표지 `<데몬 기동 ms>:<번호>` |
| M3 복원 잠금 누락(대화 화면 밖 사건) | **닫음** — main.ts briefGate 앱 수명 값 |
| M4 관문 보류 뒤 연타 | **닫음** — gate_wait(최대 30초) |
| M5 사건 없는 등록 없는 빈 마스터 좌석 | **닫음** — 행 증거 90초 ∧ 본 적 있음 |
| M6 같은 좌석 되살림 놓침 | **닫음** — 실물로도 확인(⑤) |
| M7 표식 세대 결속 | **부분** — 정리 근거(SEEN)는 신원 JSON · 꺼짐 띠 표시(파괴 없음)는 그대로(완전 초기화 뒤 남은 표식이 「멈춰 있어요」 띠를 띄울 수 있음 → 누르면 start_master = 마스터를 세움 · 해 없음 판단) |
| m1 깨움 거름 메모리만 | **닫음** — `cys-chat-wake-at` |
| m2 초 버림 | **닫음** — (idle_secs+1)·1000 |

- **2R = ESCALATE**(blocking 1 · major 5 · minor 1) — 원문 `docs/ui-p2/evidence/s5/codex-r2.json` · 1R 지적 closed = M4·M6·m1·m2 · 처분:

| 2R 지적 | 처분 |
|---|---|
| B1(1R B1 남음) 판정과 닫기가 다른 요청 | **📌 P1 = master 결정**(데몬 조건부 닫기 = 요청 칸 = 허용 범위 밖 · codex 도 「범위 확대 결정 필요」로 ESCALATE) |
| B2 잔여: 대조 뒤 close 가 번호만 보냄(그 사이 데몬 재기동·번호 재사용) | **📌 P1 에 묶음**(같은 API 에 expected created_at) · 창 = 같은 누름 안 수 ms ∧ 그 사이 데몬 재기동 |
| M1 인계 뒤 에이전트 작업 결판(RefusedNoWrite)에서 찍기 남음 | **닫음(구조)** — 가드를 「human ∧ !machine_origin ∧ refuse_on_approval」 꼴에만 · 이 꼴은 `direct_agent_intent` 첫 줄(`human && !machine_origin` → None)로 에이전트 작업 길에 안 닿아 인계 = try_write 하나 |
| M2 옛 화면(숫자 human_input_seq) 호환 | **해당 없음(판단)** — 숫자 칸은 이 가지 1R 전 중간판에만 있었고 발행·병합된 적 없음(앞 판 화면·팩·CLI 소비자 0 · `grep human_input_seq ui/ cysjavis-pack/` = 0) |
| M3 start 뒤 detach 로 done 놓친 걸쇠가 영구 잠금 | **닫음** — 앱 수명 값(deps.restoring)이 있으면 권위 · 걸쇠는 없을 때만 |
| M5 두 빈 좌석 증거가 시작 시각 공유 | **닫음** — 종류가 바뀌면 90초 새로 |
| minor 옛 데몬 표식이 새 데몬 빈 좌석에 거짓 꺼짐 | **닫음** — 등록 없는 빈 좌석 꺼짐 = 바로 그 좌석(번호 + 생성 시각)을 살아 있는 마스터로 본 적 있을 때만 |

- 2R 고침분 뮤턴트 3/3 적색(`mut_ts3.py`) · 3R 은 돌리지 않음(남은 것 = master 결정 P1 하나).

## 7. 실물(격리 HOME · `docs/ui-p2/evidence/s5/real-daemon.txt`)

- 데몬 = 이 작업트리 빌드 `target/debug/cysd` · HOME·소켓 = `/private/tmp/claude-501/s5d` · 좌석 = `tests/fixtures/fake_claude.c`(launch-agent --role master/cso/worker) · 좌석 죽이기 = 마스터 셸의 자식 claude pid 를 ps(ppid 대조)로 골라 SIGKILL(이름 일치 종료 0)
- ① 행 가산 칸(agent_seen · human_input_stamp) ② 원자 제출 응답 표지 = 행 표지 ③ 좌석 수 ④ 죽이기 → `agent_alive:false · seat:empty` · (1회차) `master.deadman axis=agent_dead` ⑤ 다시 켜기(`cys launch-agent --role master`): **1회차 = 같은 좌석 멱등 재사용 + 기동 줄 타이핑으로 되살림(rc 0)** · **2회차 = phoenix `restore --auto` 가 먼저 같은 좌석을 살려 `claim_denied(seat_not_claimable · seat_human_recent:false)`** · 둘 다 마스터 1·CSO 1·워커 1 그대로 ⑥ 사람 자판 1글자 직후 다시 켜기 → `claim_denied` + `seat_human_recent:true` ⑦ 빈 셸 원자 제출 → `no_agent` · 표지 전후 같음
- 정리: 1회차 스크립트가 중간 예외로 데몬을 못 끔 → 그 격리 데몬(98674)·자식 셸·가짜 claude 2·(2회차) 재기동된 격리 데몬(28826)·phoenix 파이썬 1 = 경로(`s5d`)·소켓 lsof 확인 뒤 pid 지정 SIGTERM · 잔재 0 확인

## 8. 📌 덧붙임(실행 안 함 · 판단 = master)

1. **P1 원자 조건부 닫기** — `surface.close` 에 「입력줄 비어 있고 최근 사람 입력 없을 때만」 조건 칸(데몬 요청 칸 · 이 갈래 허용 밖) + viewcore 명령. codex 1R B1 의 남는 창을 없앰.
2. **설계 개정 §6-2 성공 판정** — 「좌석 id 바뀜」 → 「id 바뀜 ∨ 같은 좌석이 전엔 생존 아님 → 생존」(실물 ⑤ 멱등 재사용·phoenix 회생 둘 다 같은 좌석).
3. **launch-agent 멱등 재사용이 기동 줄을 clear_first 없이 침** — 120초 안 다시 기동 + 옛 좌석에 사람 초안이면 초안 뒤에 기동 줄이 붙어 셸 명령으로 실행될 수 있음(CLI 쪽 결함 후보 · 화면은 초안이면 켜지 않게 막음).
4. 깨움 말의 「차례 기다림」 줄과 깨우기 띠가 둘 다 보임(말풍선 목록의 자동 안내 줄 + 띠) — 걷기(조각 10)에서 정리 후보.
5. 마스터 띠와 확인 대기 띠는 **따로** 보임(시안은 하나로 합침) — 확인 대기 띠의 「직접 허락」이 마스터 멈춤 때 쓰는 길이라 숨기지 않음. 설계 「한 번에 하나」 문장 개정 후보.
6. 실물 앱 팀 부트 체인(spawn_orchestra_boot) 뒤 CSO·워커 수 · 새 프로필 첫 기동 관문 · 윈 실기 = master 실기.
7. **codex 3R(2R 고침분 7dcdba6c3 검토) = master 대기열**(codex 한도 공지 master#0ad998c8 · 06:29 뒤).
8. `test_phoenix_c6_reap` 기준 대조(§5 ③).

## 9. 함정(다음 좌석에게)

- 새 작업트리 target 은 형제에서 `cp -c` 로 복제했는데 `target/CACHEDIR.TAG` 를 빠뜨려 codex 개인정보 관문이 target 을 빌드 캐시로 못 보고 막음 → 표식 복사 또는 깨끗한 임시 worktree 에서 codex 호출.
- bun-env.d.ts 매처 선언에 `toMatchObject` 없음 → bun 은 초록 · tsc 만 붉음(시험 파일 포함 검사).
- 실물 스크립트가 중간에 죽으면 격리 데몬이 남고, 그 데몬의 phoenix 가 격리 HOME 안에서 좌석을 되살리며 데몬을 다시 띄울 수 있음 → try/finally 로 데몬 pid 종료 + 끝에 `ps | grep 격리경로` 0 확인.
