# HANDOFF — cysr 1.1.6 T-SEAT(좌석 기동) · TICKET=v116-seat

작성 = worker-28(surface:1046) · 2026-09-24 · 모델 claude-opus-5-5 · effort high(세션 jsonl `"effort":"high"` 실측)
worktree `~/axdev/.wt/cys-v116-seat` · 브랜치 `fix/v116-seat`(base = 태그 v1.1.5 = 526325bf) · push 0 · 태그 0
표기 = 【관측】 도구 출력으로 확인 · 【추정】 근거는 있으나 미확정 · 【모의】 격리를 위해 흉내 낸 축(스텁 claude)

브리프 = `~/axdev/master/briefs/2026-09-24-v116-seat.md` · 계획서 = `~/axdev/master/reports/cysr-116-plan/PLAN-1.1.6.md` §3-1 T-SEAT 행
master 판정(원장 대조 성립): `master#9a304fb3`(08:09:33 · F2·F3 = A + C · 완료 기준 ⑴ 교체) · `master#292db85e`(08:14:22 · N-4 = 인자 → env)

---

## ★ §0 델타(최신) — 재개 2회차 매듭(2026-09-24 14:2x · master#bb37344b 예산 정지 · 15:20 뒤 재개)

**이 회차에 한 것(커밋 eac5ef5a..HEAD)**: 47ad0e80(기동 줄 통과 시 사망 타이머 해제 — Fable 2R P3 역할 회수 창) · d98d5c4b(시험 · 생존 뮤턴트 대비) · 6d5c9610(agy 2R P2/P3 판정 박제 = 둘 다 반박 · 거부 방향/래퍼는 메타도 래퍼) · 뮤턴트 J1~J4 4/4 KILLED.
**진행 중이던 것 = master#623fa6b9 판정 C**(폐기 지점을 배달 직전 1곳 = governance.rs `deliver_head_locked` 머리로 옮기고 handlers.rs agent_launch 통과 지점 폐기 제거 · 사망 타이머 해제는 그 자리에 유지). 조건 ⑴재현 먼저 ⑵정상 배달 회귀 + 메타 없는 좌석 대조 + 뮤턴트(지점 제거 · 조건 반전) ⑶정본 게이트 전체 직렬(gate_runner.py · secret-scan · boot-health · cysd 직렬 · ENXIO 는 단독 재실행) ⑷범위 안 ①②③ 결과 함께 【확인요청】.
- ⑴ 재현 = **미완(적색 미획득)**: 하네스 scratchpad/h31.sh(WAL queue-state.json 에 1.1.5 식 옛 기동 줄 + 대조 보류 글 → 격리 cysd → launch-agent 스텁). 【관측】 WAL 2건이 새 좌석으로 rehome(queue.rehomed) 됐으나 90초 동안 **둘 다** 미배달 · queue.list blocked_by = `prompt_unknown(프롬프트 경계 관측 불능)`. 원인 = 스텁 화면이 커서를 입력줄에 두지 않음(observe_prompt 는 커서 행에 ❯ 필요) → 스텁에 `ESC[4A ESC[3G` 추가했으나 여전히 미배달(원인 미확정 — 다음: queue.list blocked_by 재확인 · input_line_state 가 Empty 로 읽는지 · pending_input_bytes(각성문 붙여넣기 뒤 CR 로 0 인지) 확인). 코드 수정 0.
- 함정: 격리 cysd 첫 기동이 ≈11초(debug 빌드 · init-pack) — 소켓 대기는 ping 으로 최대 60초.

## ★ §0 델타(이력) — 재개 1회차 매듭(2026-09-24 10:1x · master#b29b9d60 재개 → master#d2e852f0·561dbb60 계정 이관 매듭)

**어디까지 했나(재개 뒤 · 커밋 d5b1bab6..HEAD)**:
- Fable 2-2 = 격리 재현 성립(master 역할 페인 안 node-recover → 스텁은 `--continue` 로 떴는데 set_meta `meta_denied` → rc 1 · run_boot 이면 reclaim=kill) → 수리 12157cce(CLI: meta_denied ∧ 좌석 행 agent·agent_bin 정확 일치일 때만 무해 · 데몬 게이트 불변 · surface.list 에 agent_bin 키) → 격리 재실측 rc 0 · 1초 뒤 alive True · 역할 유지 · 시험 6176dd7e·12128d7c · 뮤턴트 6/6.
- Fable 3-1 = master#4d8f12ec 판정 A → ba4e1cfb(기동 줄 통과 지점 1곳 · 그 좌석 큐의 launch_line_matches_seat 일치분만 폐기 · queue.dropped reason stale_launch_line · count · surface_ref · line_sha8 · WAL 영속) · 시험 3592234d(양방향 · 5회 반복 초록) · 뮤턴트 7/7.
- Fable 4 = 9bcd842e(lib AGENT_LAUNCH_KEY) · b8f8fa85(접미 시험) · 뮤턴트 2/2.
- D3-o·F7·agy 1R 반영분 뮤턴트 8개 — 7 KILLED · 「조립기 실패 폴백의 DRAIN 제거」 생존 → e7bd7df8 시험(F7f) 추가 뒤 KILLED.
- 검증: agy 2R = **ACCEPT**(`~/axdev/master/reports/cysr-116-seat/hetero-agy-seat-2.md` · 1R 6건 전부 CLOSED · 새 P2 1 = 이스케이프 따옴표 · P3 1 = env/sudo 래퍼 cmd — 둘 다 기동 줄을 거부하는 방향(오통과 아님) · 미판정). Fable 2R = **ACCEPT**(`…/fable-adv-seat-2.md` · P2 1 = 3-1 은 node-recover 경로만 덮고 업그레이드 뒤 restore/rehome 경로의 1.1.5 잔재는 미봉합 · P3 = 2-2 무해 경로의 role 회수 창(60s 경계 ±1틱) · 산 좌석 pane-caller rc 0 허위 recovered(근본 = 선재 2-1) · 첫 낱말이 에이전트 이름인 보류 산문 폐기 · 생존 뮤턴트(bin 인자 오전달 · now_empty 분기)). 두 검증자 모두 ACCEPT = 수렴 조건 충족 · 지적 판정은 미완.
- 전체 회귀 1벌(HEAD 3592234d · 격리 HOME · 직렬 · 10:02~10:12): lib 539 passed / 0 failed(1 ignored) · cys 294 passed / 0 failed · cysd(--test-threads=1) 1047 passed / 0 failed(1 ignored) · 빌드 rc 0 【관측】. 팩 훅 시험 8종 rc 0(뮤턴트 기준선 · e7bd7df8 뒤 test_t6 재실행 OK).

**다음 할 일(순서)**:
1. 2R 지적 판정: Fable P2(3-1 범위 — restore/rehome 경로의 옛 기동 줄) = 범위 확대라 **master 판정 요청**부터 · Fable P3 role 회수 창 · 생존 뮤턴트 2 · agy P2/P3 는 반박/수용 근거 정리.
2. 9단계 성찰 2회차(코드) · 정밀 디버깅 패스 · HANDOFF 본문(§3 시험 · §4 4군 · §6 검증) 갱신 · 【확인요청】.

**함정(추가)**: agy headless 는 `--mode plan` 만으로는 명령 권한이 자동 거부돼 출력 0(err 에 jetski 문구) — 1R 선례대로 `--dangerously-skip-permissions` + 의뢰문 읽기 전용 명시. zsh 에서 `for b in "--lib x"` 식 인자 묶음은 한 낱말로 넘어간다(시험 스크립트는 bash 파일로).

## §0 델타(이력) — 파킹(2026-09-24 08:5x · master#85b77a21 「park-for-cysr115-0924」 · 우리 맥 1.0.2→1.1.5 업데이트 대비)

**어디까지 했나**: 필수 3(X-4 · N-4 env · F2) + 가능 3(D3-o · F7 · D4 #15) 구현·커밋 · 격리 실측(X-4 대조 · N-4 구판/신판 스텁 · F2 12칸 표) · 뮤턴트 25/25 KILLED(X-4 7 · F2 6 · N-4 6 · 교체 뮤턴트 1 포함 — D3-o·F7 뮤턴트는 미실행) · 팩 훅 시험 8종 rc 0 · agy 1R(REJECT 6 → 수용 2 커밋 9482ea23 · 반박 4) · Fable 적대 1R(X-4 · ACCEPT · 선재 P2 3건). 최종 커밋 = 이 문서 커밋.

**진행 중이던 검증 라운드 상태**:
- agy = 1R 끝(§6-1) · **2R 미발송**(수용 2건 반영분 9482ea23 + 반박 근거로 재판정 받아야 수렴 판정 가능).
- Fable = 1R 끝(§6-2) · 지적 중 **2-2(pane 호출자 set_meta meta_denied)** 는 대응 착수 직전에 파킹 — 격리 재현 하네스 1차 시도는 하네스 오류(`cys new-surface --cmd` 인자 파싱 · usage rc 2)로 재현 자체가 안 됐다 = 미판정.
- 전체 회귀(lib · cys · cysd 직렬 전건) = **미완** — 첫 시도는 셸 인용 실수로 미실행, 둘째는 두 벌이 겹쳐 돌아(로그 오염) 내가 중단. 개별 v116 시험·팩 훅 시험만 초록.

**다음 할 일(순서)**:
1. Fable 2-2 재현: 격리 cysd 안의 `--role master` 페인 셸에서 `cys node-recover --role worker` → `meta_denied` 여부(하네스 = 페인 명령을 스크립트 파일로 넘겨 인자 파싱 회피). 재현되면 수리안 = CLI boot_agent_on_surface 에서 「set_meta 가 meta_denied 이고 좌석의 현 메타 agent == 요청 agent」면 무해로 받기(데몬 권한은 넓히지 않음 · 사망 감지는 같은 메타로 복귀 관측 시 스스로 재무장 = governance.rs:630~645 agent.recovered) + 시험.
2. Fable 3-1(1.1.5 가 큐에 남긴 옛 재기동 줄 WAL 잔여 → 되살아난 claude 에 사용자 입력으로 배달): 수리(agent_launch 통과 시 그 좌석 큐의 「기동 줄」 항목 폐기) 여부 master 판정 요청.
3. Fable 4: 와이어 키 `agent_launch` lib 상수화 · `ends_with` 뮤턴트 막는 접미 시험(`myclaude --x`) 추가.
4. D3-o·F7 뮤턴트(비복원 상한 되돌림 · master CI_NOTICE 의 DRAIN 제거 · _ss_rules 의 DRAIN 제거).
5. 전체 회귀 직렬 1회(`cargo test --bins --lib --no-run` 뒤 lib → cys → cysd --test-threads=1 · 격리 HOME · **한 벌만**).
6. agy 2R · 9단계 성찰 2회차(코드) · 정밀 디버깅 패스 · 【확인요청】.

**함정(재개자에게)**:
- 이 셸(zsh)에서 `E="env -u …"; $E cmd` 는 한 낱말로 해석돼 실행 0 — 스위트는 bash 스크립트 파일로 돌려라.
- git rerere 가 켜져 있다(공용 .git) — 충돌 해소를 시험 삼아 하면 잘못된 해결본이 기록된다(내가 1건 기록 후 삭제함). cherry-pick 은 `-c rerere.enabled=false`.
- 격리 좌석 스텁은 `exec cat` 이면 안 된다(프로세스가 cat 으로 바뀌어 claude 관측 실패) · 화면에 프레임 줄 + 「? for shortcuts」 를 그려야 준비 판정이 난다 · 격리 cysd 엔 `CYS_NO_AUTORESTORE=1`(자동 복원이 좌석을 되살려 판정을 흐린다).
- 기준선 바이너리용 임시 worktree(cys-v116-seat-base)·`.probe/`(2.6G)·스크래치 사본은 파킹 때 지웠다 — 재개 시 기준선 대조가 필요하면 다시 만든다(`git worktree add --detach … 526325bf` + target APFS 복제).

---

## 0. 무엇을 했나 — 한눈에

| 항목 | 분류 | 결과 | 커밋(제품 · 시험) |
|---|---|---|---|
| X-4 node-recover 재기동 줄이 빈 셸 가드에 막힘 | 필수 | 수리 · 격리 실측 대조 성립(외부 셸 호출) · pane 호출 경로(Fable 2-2) 미판정 | 6206050f · 8dade4f2 · 9482ea23 |
| N-4 Claude 좌석 effort high | 필수 | 선행 5af9ac1d cherry-pick(0ca8a0d0) → **인자 방식이 구판 claude 를 죽여** env 방식으로 교체 | 0ca8a0d0 → 4463ad91 · 7c685cf8 |
| F2 첫 프롬프트 색인 상한 | 필수 | 메모리 색인 2,000자 · 스킬 이름만 3,000자 + Read 포인터(9482ea23 부터 머리 줄 포함) | c39507f0 · 92d68197 · 9482ea23 |
| F3 지침 본문 요지화 | 필수(판정으로 분리) | master 판정 C = 별도 설계 티켓 후보(§9) · 코드 0 | — |
| D3-o 훅 출력 < 10,000자 | 가능 | 비복원도 복원과 같은 상한 | 1803bb7c · f73a905f |
| F7 master·CEO 좌석 DRAIN 줄 | 가능 | 조립기 「역할 재대조 고지」 칸으로 | 1803bb7c · f73a905f |
| D4 #15 「새 탭」 문구 | 가능 | 「자비스 재시작」(윈과 같은 말) | 969858fe · b28a4170 |
| D3-p CEO 조립 절 목차 탈락 | 가능 | **착수 안 함** — 실측 근거와 함께 곁 항목(§10) | — |

---

## 1. 원인표(파일:행은 base 526325bf 기준)

### X-4
- 【관측】 `src/bin/cysd/handlers.rs:3721` `if !human && crate::governance::agent_seat_vacant_now(&surface) {` — 에이전트 메타가 남은 빈 셸 좌석에 온 **기계 본문 전부**를 `hold_for_vacant_seat`(큐 적재)로 돌리고 `no_agent` 오류를 낸다. 이 가드는 지시문이 셸 명령으로 타이핑되는 사고(09-22 VM `zsh: event not found`)를 막으려고 생겼다.
- 【관측】 `src/bin/cys.rs` `boot_agent_on_surface` 가 기동 줄을 `surface.send_text`(authoritative)로 보낸다. 새 좌석(launch-agent)은 이 시점에 메타가 아직 없어(set_meta 는 send 뒤) 가드를 안 탄다. **node-recover·in-seat 복원은 메타가 남은 좌석**에 기동 줄을 쳐서 가드에 걸린다 → `request(...)?` 가 Err → rc=1 → `run_boot` 의 죽음 확정 체인이 reclaim(kill)으로 에스컬레이션.
- 수리: 기동 줄 send 에 `agent_launch: true` 표지(cys.rs) · 데몬은 표지 ∧ `governance::launch_line_matches_seat`(한 줄 ∧ 환경 대입 `KEY="값"`(값 공백 허용)을 건너뛴 첫 낱말의 파일 이름 = 좌석 agent_bin 파일 이름)일 때만 통과 · 표지 + 불일치는 거부하고 **큐에도 넣지 않는다**(셸 명령 줄이 큐에 남으면 뒤에 뜬 에이전트에게 사용자 입력으로 배달된다) · 표지 없음 = 종전 보류. 구 데몬은 모르는 키를 무시 → 신 CLI × 구 데몬 = 종전 동작.

### N-4
- 선행 5af9ac1d 판단: 제품 변경은 v1.1.5 위에 충돌 0, 충돌은 cys.rs 시험 모듈 끝 추가 위치 1곳뿐 → cherry-pick(0ca8a0d0 · 219+/10- = 원 커밋 동일).
- 【관측】 그 뒤 실측에서 결함 발견: 구판 claude 2.1.37(`/opt/homebrew/bin/claude` · 이 기계 PATH 두 번째)에 effort 인자를 주면 「error: unknown option '--effort'」 rc=1(세션 0 · 격리 config dir · `mcp list` 하위 명령으로 인자 검사만 태움 · 대조 = 신판 2.1.281 rc 0 · `--bogus-flag-xyz` 양쪽 rc 1). **PATH 앞에 구판이 있는 기계에서 전 claude 좌석 즉사(4군 ④)**.
- 【관측】 설치본 2.1.281 문자열: 「apply_flag_settings: CLAUDE_CODE_EFFORT_LEVEL overrides effort for this session」 · 「Not applied: CLAUDE_CODE_EFFORT_LEVEL=… overrides effort this session」(좌석 안 `/effort` 변경도 막음) · settings 스키마 `effortLevel`(Persisted effort level).
- 수리(master#292db85e): lib `inject_claude_effort_env`(claude 좌석 ∧ 키 부재 시에만 `CLAUDE_CODE_EFFORT_LEVEL=high` append · 사용자 값 불가침 · 재정렬 금지) · 소비처 2 = 기동 줄 env_pairs(unix 인라인 · 새 좌석·restore·node-recover 공통) · `launch_create_env_pairs`(launch-agent 의 surface.create env 맵 = Windows 에서 pane env 로 실리는 유일한 경로). `compose_agent_cmd` 는 명령 한 줄에 effort 를 붙이지 않는다. `git grep -e '--effort'` = 0 【관측】.

### F2
- 【관측】 base `src/bin/cys.rs` compose_directive: 메모리 색인 **전문** + 스킬 색인(이름: 설명) 전부를 붙였다(상한 0).
- 수리(master#9a304fb3 A): `capped_memory_index`(`- [` 항목 줄만 · 최신(끝)부터 줄 단위 · `MEMORY_INDEX_CAP_CHARS` = 2,000 · 머리 줄 「최신 N항 / 전체 M항 — 전문은 <경로> 를 Read」) · `capped_skill_index`(이름만 쉼표 · local 오버레이 `*` · `SKILL_INDEX_CAP_CHARS` = 3,000 · 초과분 「외 N개(`cys skill list`)」).
- N = 2,000 근거: 저장소 새 팩 워커의 고정분(WORKER 14,268 + RSI 9,036 + soul 1,559 = 24,863자) + 스킬 이름 ≈ 2.4K 에 더해 30K 미만 · 색인 항목 평균 ≈ 200자(박사님 팩 941항 실측) → 최신 약 10항. 새 항목은 색인 끝에 붙는다(javis_memory.py add · 【관측】 :240~262).

### D3-o
- 【관측】 base `cysjavis-pack/hooks/session-start.sh` 비복원 분기 = `_ss_rules` + 각성 헤더 + `cat "$D"` + `_ss_bulk`(soul · 메모리 색인 16,384B) — 워커·CSO 16~17K자 → 10,000자 초과 → 저장 파일 + 앞 2,000자 미리보기(D3-pack.md · 실물 68,516B).
- 수리: 비복원도 복원과 같은 상한(`RESUME_INJECT_CAP` 9,000) · 머리는 언제나 · 원문 블록은 합계가 상한 미만일 때만 · 넘으면 `■ 원문 목차`(경로) + 생략 고지 · 작은 원문은 종전대로 전부.

### F7
- 【관측】 base session-start.sh master 분기가 `_ss_rules` 보다 앞에서 exit → master·CEO 좌석은 훅으로 DRAIN 줄을 못 받음 · CORE-MIN 1,599/1,600자 포화.
- 수리: DRAIN 두 줄을 `_ss_drain_rules` 한 곳으로 떼고 · 비-master = `_ss_rules` 가 · master·CEO = 요지 조립기 `CYS_CI_ROLE_NOTICE` 칸 앞쪽(조립기 LIMIT 가 예산 집행) · 조립기 실패 폴백도 싣는다.
- 【관측】 조립기 `--report`: master 7,916→8,178자 탈락 0 · CEO 8,146→8,408자 탈락 블록 불변(「절 목차」 = 기존 D3-p) · 부트 브리지 양쪽 유지.

### D4 #15
- `install_hint_for("claude", 맥·리눅스)` 「… | bash` 후 새 탭」 → 「… | bash` 후 자비스 재시작」(Windows 분기와 같은 말).

---

## 2. 격리 실측(라이브 무접촉)

격리 조건: `env -i`(HOME·PATH·LANG·TERM·SHELL·USER·CYS_SOCKET·CYS_NO_OFFICE_BRIDGE=1·CYS_BOOT_GATES=0·CYS_NO_AUTOSTART=1·CYS_NO_AUTORESTORE=1) · 격리 HOME = worktree `.probe/<tag>/h`(미추적 · info/exclude) · 소켓 `/tmp/cysiso.XXXX` · launchctl 스텁(rc 1) · 가짜 claude = 절대경로 스텁(agents.json claude.cmd 를 스텁 경로로) — 스텁은 argv·env_effort 를 기록하고 프레임 줄 + ❯ + 「? for shortcuts」 를 그린 뒤 stdin 을 원문 그대로 파일로 받는다(raw 모드). 바이너리는 시험 직전 `cargo build --bins`(mtime 병기). 라이브 cysd pid 62178 기동 시각(09-19 18:17:00) 전·후 불변 【관측】. 각 실행 뒤 스텁·격리 cysd 종료 · 내 `/tmp/cysiso.*` 전부 삭제(남은 5개는 다른 워커 것 — 내 실행 전부터 있었다).

### 2-1 X-4 (기준 ⑶)
| 빌드 | node-recover rc | 스텁 argv(재기동) | 큐 | 데몬 로그 |
|---|---|---|---|---|
| 수리 8dade4f2(08:04 빌드) | **0** | `--dangerously-skip-permissions --continue` 실재 | `[]` | `surface:1 빈 좌석 재기동 줄 타이핑 — agent_launch` |
| 대조 v1.1.5 526325bf(08:05 빌드) | **1** · `no_agent … not typed; queued (prompt_unknown)` | 없음(재기동 0) | 재기동 줄 1건(`… stubbin/claude --dangerously-skip-permissions --continue`) | — |

### 2-2 N-4 (기준 ⑵ — 【모의】 argv/env 층)
| 빌드 × 스텁 | launch rc | recover rc | 스텁 기록 |
|---|---|---|---|
| 수리 7c685cf8 × 신판 흉내 | 0 | 0 | 새 좌석 `env_effort=high` · 재기동 `--continue env_effort=high` |
| 수리 7c685cf8 × **구판 흉내**(effort 인자면 rc 1) | 0 | 0 | 둘 다 생존 · `env_effort=high`(구판은 무시 = medium 으로 삶) |
| 대조 0ca8a0d0(인자) × 구판 흉내 | **1** | 1 | `argv=… --effort high` → `EXIT1 unknown option` · 좌석 닫힘 |

⚠ jsonl `"effort":"high"` 실측(기준 ⑵ 원문)은 **격리 HOME 에서 불가** — 격리 HOME 은 claude 로그인이 따라오지 않는다(장기기억 isolated-home-no-claude-login-macos). 실 로그인 좌석 1석 기동 뒤 jsonl assistant 레코드의 `"effort"`·`"perTurnEffort"` 확인 = **master 게이트**(실 함대/VM).

### 2-3 F2 (기준 ⑴ 교체판 — 격리 좌석이 실제로 받은 첫 붙여넣기 · 스텁 stdin 의 bracketed paste 1건 · 자수)
라이브 팩 = 박사님 팩(1.1.4)의 지침 4종 · soul · MEMORY.md · skills/*/SKILL.md 를 격리 팩에 **읽기 복사**(본문 메모리 파일·로컬 오버레이 제외).

| 좌석 | 팩 | 전(526325bf) | 후(수리) | 메모리 색인 전→후 | 스킬 색인 전→후 |
|---|---|---|---|---|---|
| worker | 새 팩 | 52,277 | **27,774** | 1,177 → 450 | 26,167 → 2,391 |
| worker | 라이브 1.1.4 | 252,950 | **40,189** | 191,272 → 2,287 | 26,167 → 2,391 |
| cso | 새 팩 | 42,285 | **17,779** | 1,174 → 444 | 26,167 → 2,391 |
| cso | 라이브 1.1.4 | 231,930 | **19,166** | 191,269 → 2,281 | 26,167 → 2,391 |
| master | 새 팩 | 82,307 | **57,804** | 1,177 → 450 | 26,167 → 2,391 |
| master | 라이브 1.1.4 | 262,940 | **50,179** | 191,272 → 2,287 | 26,167 → 2,391 |

- 색인 합(후) ≤ 2,287 + 2,391 = 4,678자 — 상한(2,000 + 3,000) + 머리 줄(경로 포함 ≈ 280자) 안 【관측】. 첫 프롬프트 총량 = 지침 전문 + 상한(판정 문구 그대로).
- 메모리 색인 「후」 2,287 은 항목 2,000자 상한 + 머리 줄(포인터) — 상한은 항목 줄만 센다(설계대로).

---

## 3. 시험(파킹 시점)
| 묶음 | 결과 |
|---|---|
| 신규 cysd v116_(2) | 초록 · handlers 행위 시험 경합 수리 뒤 반복 10/10 |
| 신규 cys v116_ · compose_directive · install_hint(12±) | 초록 |
| lib claude_effort_tests(4) | 초록 |
| 팩 훅 시험 8종(test_t6 · session_start · core_inject · event_inject · bootv2_doc_contract · role_bootstrap · hook_timing · hook_launcher_split) | rc 0 |
| 뮤턴트 | X-4 7/7(M6 등가 → M6b) · F2 6/6 · N-4 6/6 KILLED · D3-o·F7 미실행 · 9482ea23 반영분(메타문자 · 머리 줄 상한) 미실행 |
| 전체 회귀(lib · cys · cysd 직렬) | **미완**(§0 델타) |

## 4. 4군 점검(파킹 시점 · 잠정)
- ① 폭주 큐: X-4 는 표지+불일치 거부 시 큐 0 · 통과 시 큐 0(격리 실측 `[]`) — **잔여 = 1.1.5 가 이미 쌓은 옛 재기동 줄(Fable 3-1 · 선재)**.
- ② 무clear 100%+: 출생 크기 실측 라이브 워커 252,950→40,189 · master 262,940→50,179 · CSO 231,930→19,166(§2-3).
- ③ 자가치유 전멸: 외부 셸 호출 node-recover rc 1→0(§2-1) · 산 좌석은 agent_alive 사전 검사로 거부(선재 · Fable 2-1) · **pane 호출(Fable 2-2) 미판정**.
- ④ 전 pane 사망: N-4 인자 방식이 구판 claude 좌석을 죽이던 경로 제거(§2-2 대조) · 윈도 = surface.create env 경로 시험 1(v116_effort_env_reaches_launch_line_and_windows_create_env) · 윈 실기 미측정.

## 6. 검증
### 6-1 agy 1R (`~/axdev/master/reports/cysr-116-seat/hetero-agy-seat-1.md` · REJECT 6)
| # | 지적 | 판정 | 근거 |
|---|---|---|---|
| 1 | send_key Return 이 빈 셸 가드에 막혀 큐로 | 반박 | 가드는 send_text(handlers.rs:3721)에만 · send_key 처리부에 없음(grep 전 호출처 = 2075 CEO · 3721) · 격리 실측에서 `--continue` 스텁이 실제로 떴다(Return 도달) · Fable 1-2 도 같은 반박 |
| 2 | 산 좌석에 기동 줄 | 선재(패치 무관) | 비어 있지 않으면 가드 자체를 안 탄다 · 패치 전후 동일 · node-recover 는 agent_alive 사전 검사 · Fable 2-1 도 선재로 분류 |
| 3 | `_ss_chars` 가 바이트를 센다 | 반박 | 1순위 = 파이썬 글자 수 · `wc -c` 는 인터프리터 없을 때의 기존 폴백(더 적게 싣는 보수 방향 · 주석 명시) |
| 4 | `claude ; rm …` 통과 | **수용**(9482ea23) | 실질 증분은 0(human:true 자기신고로 가드 우회가 원래 가능 · Fable 1-1) 이나 방어 심층으로 거부 |
| 5 | 머리 줄이 상한 밖 | **수용**(9482ea23) | 판정 문구 「색인 합 ≤ 상한」에 정확히 맞춤 |
| 6 | restore 시 env_pairs 비움 → 사용자 max 덮어씀 | 반박 | `env_pairs = agent_env_pairs(spec)`(cys.rs 10685) — 비지 않는다 · agents.json 사용자 값 보존(시험 user_effort_value_wins) |
### 6-2 Fable 적대 1R(X-4 · ACCEPT) — 선재 P2: 2-1 산 좌석 창 · **2-2 pane 호출자 set_meta meta_denied → 기동 뒤 rc 1 → reclaim** · 3-1 1.1.5 큐 잔여 · P3: 메타문자(→ 9482ea23 로 닫음) · 와이어 키 상수 부재 · `ends_with` 뮤턴트 생존.

---

## 8. 알려진 한계(정직 고지)
- **사용자가 max 를 원하면** = 그 어댑터의 agents.json `env` 에 `CLAUDE_CODE_EFFORT_LEVEL` 을 적는다(주입은 키가 없을 때만 한다). 좌석 안의 `/effort` 변경은 env 가 막는다(「Not applied」 · 박사님 정책 「high 고정」과 일치 · master 수용).
- **구판 claude 가 PATH 앞에 있는 기계에서는 effort 가 medium(기본값)으로 떨어진다** — 구판은 이 env 를 모른다(좌석은 산다 · 안전 퇴화). 이 기계에도 `/opt/homebrew/bin/claude` 2.1.37 이 PATH 두 번째에 있다 【관측】.
- jsonl `"effort":"high"` 실측은 실 로그인 좌석에서만 가능(§2-2) — master 게이트.
- F2 는 지침·RSI·soul 전문을 줄이지 않는다(판정 A) — 라이브 팩 워커 40,189자 · master 50,179자.

## 9. 별도 설계 티켓 후보 — injection-slim T3(F3 요지화 · master 판정 C)
- 무엇: launch-agent 붙여넣기의 지침 **본문**을 요지(CORE) + 원문 경로 Read 로 바꿀지.
- 왜 이번에 안 넣었나: 요지화는 좌석이 받는 규범을 줄인다. 포인터 열람 실측 0.3%(cys 각성 훅 335세션 중 1 · 장기기억 hook-output-over-10k-chars-becomes-2k-preview) → 요지만 받은 좌석은 전문 규범(판정 불변식·허브-스포크 등)을 사실상 못 본다.
- 품질 증거 설계(이 티켓은 설계까지만): ⑴대조군 = 전문 붙여넣기 좌석 · 실험군 = 요지 + 경로 좌석(같은 모델·effort·팩·브리프) ⑵과제 = 규범이 갈리는 상황을 담은 고정 시나리오 묶음(예: 판정 지시 문구 수신 · 워커→워커 전달 요청 · [DRAIN] 수신 · 비가역 행동 직전 · 60% 도달 신고) ⑶측정 = 시나리오별 규범 준수 여부(결정론 판정: 인박스 기록·명령 실행 로그·jsonl 도구 호출로 기계 채점 · LLM 채점 금지) + 원문 Read 발생 수 ⑷합격 = 실험군 위반 수 ≤ 대조군(잠근 기준 · 표본 수는 계수 확보 뒤 확정) ⑸비용 = 좌석 CTX 전/후. 요지 파일은 master·CEO 에만 있다(MASTER_CORE · CEO_CORE) — worker·CSO 는 신설(팩 디렉티브 추가 = 합성기 · doc-contract · 줄범위 3줄 의무).

## 10. 곁 항목(이번 범위 밖)
- **D3-p(가능 · 미착수)**: CEO 조립은 목차 없이 8,146자(F7 뒤 8,408자) · 절 목차 1,839자 → 합 9,985자(F7 뒤 10,247자) > 조립기 HARD 9,000 【관측 · core_inject.py --report / toc_block 계수】. 목차를 싣으려면 CEO_CORE 나머지를 ≈ 1,200~1,500자 줄이거나 목차를 압축해야 한다 — 요지 파일(해시 대조 대상)·조립기 설계 변경이라 별도. **F7 이 CEO 조립에 262자를 더했다**(부트 브리지는 유지 · 탈락 블록 불변).
- 이 기계 `/opt/homebrew/bin/claude` = 2.1.37(구판)이 PATH 에 남아 있다 — 좌석 PATH 해소 순서에 따라 구판이 잡힐 수 있다(N-4 의 퇴화 경로).
- 1.1.5 에서 node-recover 가 실패하며 큐에 남긴 옛 재기동 줄(WAL 영속)이 있는 기계라면, 1.1.6 에서 그 좌석이 되살아난 뒤 그 줄이 사용자 입력으로 배달될 수 있다 【추정 — 재현 안 함】(§6 검증 결과 참조).
