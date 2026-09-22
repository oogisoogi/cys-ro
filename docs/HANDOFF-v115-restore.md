# HANDOFF — TICKET=v115-restore (트랙 D · worker@surface:906 · 2026-09-22)

브랜치 `fix/v115-restore` ← 377657dc(v1.1.4 태그) · push 0 · 판번 bump 0.

## §0-r2 델타(worker-2@surface:908 · 2026-09-22 13:2x) — B1 ①② 구현 완료
- **B1 ①**: 바닥 고정 재판정을 순수 함수 `ui/src/scrollfollow.ts` `nextFollow(prevFollow, deltaY, atBottom, keyInput)` 로 뺐다. 위로 휠 뒤엔 「아래로 휠 후 바닥 실측(prevFollow ∨ atBottom) 또는 키 입력」 때만 재고정 — 옛 rAF `follow = atBottom()` 되돌림 제거(`main.ts` 휠 핸들러).
- **B1 ②**: 휠 위로 + 뷰포트 맨 위(viewportY ≤ 0) 도달 시 토스트 「더 위의 내용은 클로드가 접어 두었습니다 — Ctrl+O 로 전체 보기」 · 앱 세션당 1회(모듈 전역 `foldHintShown` · pane 무관) · 판정 = `shouldShowFoldHint`.
- 시험 = `ui/src/scrollfollow.test.ts` 7건(트랙패드 소량 델타 유지 · 아래로 휠 재고정 · 키/가로휠 · 안내 1회 · 안내 조건 · 문구 내부용어 0 · 배선 호출부 계수). 뮤턴트 2/2 KILLED(순수 함수 되돌림 복원 · main.ts 배선 되돌림 복원).
- 게이트: ui `bun test` 1072/0 · tsc 신규 0(★이 워크트리는 ui/node_modules 부재로 **HEAD 기준선부터 15건 적색** — 기준선 사본 대조 diff 0으로 판정. 종전 「tsc 0」 표기는 이 축에선 성립 안 함) · secret-scan --all clean · cargo 무재실행(변경 = ui 만 · 전임 실측 승계).
- 손 시험 【미측정】(이 세션 GUI 조작 수단 없음) → master cmux-cua 또는 박사님 윈/맥 실기: 클로드 스트리밍 중 트랙패드로 살짝 위로 → 끌려 내려가지 않는가 · 맨 위에서 안내 1회.
- 알려진 한계: ② 안내는 pane 종류를 묻지 않는다 — 일반 셸 pane 에서 스크롤백 맨 위에 닿아도 같은 문구가 1회 뜬다(브리프 조건 그대로 · 좁히려면 pane→agent 판정 배선 필요).

### 이월(1.1.5 제외 · master 판정 13:0x)
- **B1 ③ fullscreen 계정 우회**: 대체 화면 + 트래킹 미요청일 때 휠을 PgUp/PgDn 대신 앱 보고로 보내는 안. 제외 사유 = ⑴ 그 모드의 클로드가 휠 보고를 실제로 받아 스크롤하는지 【미측정】 ⑵ `wheelgate.ts` 주석의 입력 히스토리 오염 위험(휠이 방향키로 합성되면 프롬프트 히스토리가 뒤섞인다) ⑶ 이 기기에서 관측된 사용자 모드는 inline(`alt_screen=false`)뿐. 재개 조건 = fullscreen 롤아웃 계정 1곳에서 휠 보고 수신 여부를 먼저 실측.

### 이월(Fable 최종 검증 · v115-review-fix · worker-2@surface:909 · 2026-09-22 · master 판정 = 기록만)
- **발견 4 · A4 정착 관측 창 약 29초 【추정】**(`javis_phoenix.py:2434-2445`): 정착 판정이 `agent_alive is True` 를 요구하는데 그 값은 워치독 틱(5초)의 `agent_seen` 뒤에 선다. 관측 창 1+4×1초 · 재시도 3회 합계 ≈29초를 넘기면(윈도 콜드 부팅 · Defender 스캔 · 부서 다수 동시 복원) Phase 11 fresh 폴백으로 가서 worker 는 `dedup_worker_role` 로 worker-N 이 하나 더 뜰 수 있다(RESPAWN_CAP=3 유계). 판단 조건 = 09-23 뒤 윈 실기에서 `phoenix_restore` 저널의 `respawn_count`(VM 축 5) 실측. 수리 후보 = 정착 술어를 「True 또는 (None ∧ seat=occupied ∧ 실패 줄 없음)」으로 완화하거나 창을 워치독 2틱(≥10초)으로.
- **발견 7 · SessionStart 재발화 시 `CLAUDE_ENV_FILE` 중복 append**(`hooks/_lib.sh:291-304` · `session-start.sh:18-19`): `/clear`·compact 에도 SessionStart 가 다시 돌아 export 2줄이 반복된다(PATH 중복 접두 · 무해). 사용자 PATH 무접촉은 시험 `test_v115_dept.py` 가 잰다. 데몬 스케줄 잡은 여전히 PATH `python3`(인지된 잔여).
- **발견 9 · pane 안 boot_node 의 `close_denied`**(`javis_boot_node.py` reap-launch · `handlers.rs:4158-4180`): CSO 가 손으로 `javis_formation.py ensure` 를 돌리거나 master pane 의 `cys boot` 처럼 boot_node 가 pane 안에서 돌면 `surface.close` 소유 게이트가 거부해 reap rc≠0 으로 끝나고 기동은 진행된다 — 옛 빈 좌석이 role 없는 셸로 남는다(무해 · 로그 「reap rc=1」). 심박 경로(익명 caller)는 통과.
- **워커 역할 큐 이관(승계 확장) = 1.1.6 후보**: 이번 수리는 큐가 남은 워커 빈 좌석을 보존(seat.kept · 기동 안 함)만 한다. 근거 = 데몬 좌석 승계·큐 이관(`migrate_seat_queue`)이 `surface.create` 의 `takeover_empty_seat` 게이트에서 `master|cso` 한정(`handlers.rs:3070` · 이관 `:3286-3291`). 보존 좌석은 큐가 비거나 사람이 다룰 때까지 그 역할이 결원으로 남는다(formation 시도 원장 역할당 3회/6h 로 유계).

### CI flake 결정론화(v115-ci-flake · worker-2@surface:913 · 2026-09-22 15:1x · 커밋 abf67dfa · push 완료)
- 계기: 태그 v1.1.5(0aee2cc5) release CI macos aarch64 잡이 두 번 다른 시험에서 적색 — 1차 run 35689538512 `drain_verify_activity_extends_deadline_but_idle_does_not`(기대 Timeout · 실제 Saved) · 2차 같은 run 재실행 job 106630491476 `send_text_clear_first_requires_agent_pane`(`no_agent … bare shell … queued`) + ACL_ENV_LOCK 오염 연쇄. 로컬은 초록.
- 수리(시험 코드만 · 제품 코드 무변):
  - cysd 시험 전용 헬퍼 `governance::test_wait_seat_runs(s, prog, args)` — 좌석 뿌리·자손에 명령 argv 완전 일치가 뜰 때까지 10s 유계 · 50ms 간격 · 초과 시 관측 목록 진단. ⚠`#[cfg(test)]` **첫 등장 뒤**에 둬야 한다(소스핀 `wrapper_delegates_to_the_promoted_collector_source_pin` · `queue_delivery_single_helper_shared_by_tick_and_rpc` 가 그 앵커 앞을 프로덕션으로 자른다 — 앞에 뒀다가 2건 적색 실측).
  - 적용 4곳: `send_text_clear_first_requires_agent_pane`(구 「점유」 3s 대기 교체) · `w3_ceo_delivered_when_seat_occupied` · `w3_cycle_verify_not_auto_routed` · `v115_seat_inject_guarded_holds_vacant_agent_seat`(구 고정 1.5s 교체).
  - cys `drain_verify…`: 가짜 늦은 저장을 벽시계(2.2s 스레드)에서 「마감 폴링 3번째 화면 관측」 기입으로. 관측 주기 400ms · 기본 상한 1s ⇒ 연장 없이 폴링 관측은 최대 2회라 3번째는 연장 시에만 발생. `fake_write_after` 제거.
- 반복 계수: 대상 5시험 각 10회 연속 10/10 · 부하(cysd 전체 스위트 2개 동시 + `yes` 8개) 아래 cysd 3시험 3/3 · cys drain 3/3 · `cargo test --bin cysd` 1012/0/1ign · `--bin cys` 278/0 · secret-scan clean.
- 뮤턴트: cys = 제품 연장 제거 → busy 적색 · 무조건 연장 → idle 적색(2/2 KILLED) · cysd = 헬퍼 즉시 return → clear_first 5/5 적색(KILLED) · 나머지 3시험 0/5(이 기계에선 대기 없이도 초록 — 이 축 그물 아님).
- 【미측정】 원 CI 적색 재현: 구 「점유」 대기로 되돌려 부하 아래 10회 → 0/10 적색. 원인(로그인 셸 프로파일 단계 찰나 자식을 점유로 보고 조기 탈출)은 【추정】. 신 대기는 argv 완전 일치라 그 경로 유무와 무관하게 닫힌다.
- 잔여: cys drain busy 는 연장 뒤 3번째 관측이 하드 상한 2s 안에 와야 함(명목 1.2s · 여유 0.8s — 구판과 같은 급) · 헬퍼 초과 panic 이 ACL_ENV_LOCK 오염 연쇄를 여는 기존 구조는 범위 밖(무변).

## §0 델타(후임 먼저 읽을 것 · 13:0x · CTX 61% 매듭)
- 끝 = A1·A3·A4(조사+수리)·B4·B5·B6 + 게이트 정리 2커밋(d126b525·b326671c). **남은 것 = B1 수리 구현 1건뿐**(판별까지 끝).
- 비가역: push 0(재승인 뒤 1건) · 판번 bump 0 · 라이브 cysr 무접촉(B1 = 코드 판독 + 로컬 pty 탐침만).

### B1 스크롤 — 층 판별 결과
| 축 | 관측/근거 | 판정 |
|---|---|---|
| 클로드 코드 화면 모드 | 【관측】 Claude Code 2.1.278 을 pty 로 12초 띄워 출력 전수(1628B): `?1049h`(대체 화면) 0 · `?1000h/1002h/1003h/1006h`(마우스 트래킹) 0 · `\x1b[3J`(스크롤백 지우기) 0 · `?2004h`·`?1004h` 만 2회. 이 기기 좌석 3개도 cysd `alt_screen=false` | 기본(inline) 상태에선 **클로드가 휠을 삼키지 않는다** → 위로 보기 = 우리 터미널 층(xterm 스크롤백 5000 · `ui/src/main.ts` 2798~2847) 책임 |
| 단, 모드는 계정·롤아웃이 정한다 | 코드 주석 `ui/src/wheelgate.ts` 25~31행(2.1.233 `ra()` 판정 = 서버 기능게이트) · 바이너리에 `?1000h`·`?1006h`·`[3J` 문자열 실재 | fullscreen(대체 화면) 롤아웃 계정에선 스크롤백 자체가 없다 = 클로드 코드 층 |
| 터미널 층 후보 ① 바닥 고정 경주 | `ui/src/main.ts` 2828~2847: 휠 이벤트마다 `follow=false` 후 **rAF 에서 `follow = atBottom()` 재판정** — 트랙패드 소량 델타(1줄 미만)는 첫 프레임에 뷰포트가 안 움직여 `follow=true` 로 되돌고, 클로드 스피너/스트리밍 write 의 `snapToBottom()` 이 바닥으로 끌어내림 【추정 · 코드 판독 · GUI 재현 미실시】 | 1순위 수리 대상 |
| 터미널 층 후보 ② 트래킹 중 휠 | `ui/src/mousefilter.ts` routeOnData: 비-대체화면 휠 보고 → 로컬 스크롤 번역(이미 수리됨 · 대체화면이면 앱으로 forward) | fullscreen 계정에선 앱이 스크롤해야 함 — 앱이 휠을 받는지 【미측정】 |
| 클로드 코드 층 ③ 접힌 출력 | 화면의 「(971 lines hidden)」 = 클로드가 출력 자체를 접어 터미널에 안 쓴 줄 → 스크롤로는 원리적으로 못 봄 · Ctrl+O(전사 보기)가 유일 경로 | 우회 = 안내 1줄 |

⚠ GUI 휠 실사격(휠·Shift+휠·트랙패드·Ctrl+O)은 이 세션에서 **미실시** — 화면 조작 수단 없음(화면 기록 권한 없음 · 라이브 cysr 무접촉 규율). 후임 또는 박사님 1분 손 시험으로 ①을 【관측】으로 올릴 것.

### B1 수리 설계(후임 구현 · 예상 = 코드 20줄 + 시험 2 · 계수 = B5 같은 UI 소수정 ≈15분)
1. **①**(`main.ts` 2828~2847): 사용자가 위로 휠(deltaY<0)을 준 순간부터 **「바닥 도달을 실측할 때까지」 follow=false 유지** — rAF 재판정은 `follow = follow || atBottom()` 이 아니라 「아래로 휠(deltaY>0) 이후에만 atBottom() 으로 재고정」으로. 키 입력 시 재고정은 유지. 순수 판정 함수로 빼 bun 시험(트랙패드 소량 델타 시나리오 = 뮤턴트 대상).
2. **③ 안내**: 휠 위로 + 스크롤백 맨 위 도달 시 1회 토스트 「더 위의 내용은 클로드가 접어 두었습니다 — Ctrl+O 로 전체 보기」.
3. **② fullscreen 계정 우회(선택 · master 판정)**: 대체 화면 + 트래킹 미요청이면 휠→PgUp/PgDn 대신 앱 보고로 보내기 — 입력 히스토리 오염 위험(wheelgate 주석) 때문에 별도 판정 필요.
- 검증 = bun 시험 + 우리 맥 손 시험(휠·트랙패드 스트리밍 중 위로) + 윈 실기.

### 함정(추가)
- cys-app(`src-tauri`) `cargo test` 는 이 워크트리에서 빌드 불가 — `binaries/cysd-aarch64-apple-darwin` 사이드카 부재(제 변경은 src-tauri 0 → 【미측정】 영향 없음).
- 전체 `cargo test --bin cysd` 5회 중 1회 36건 적색(루트 패닉 미포착 · 나머지는 ACL_ENV_LOCK 오염 연쇄) → clear_first 시험 대기 추가 뒤 3회 연속 1012/0. 재발 시 `grep -A2 "panicked at" | grep -v PoisonError` 로 첫 원인부터.
- 경고 신규: `delivery::Origin::SeatTakeover·EnvAdvisory` 미생성(A3 로 입력 주입이 사라짐) — 원장 과거 기록 판독용일 수 있어 지우지 않았다.

## 끝난 것(커밋 순)
| 커밋 | 항목 | 요지 | 시험·뮤턴트 |
|---|---|---|---|
| a7605677 | A1 | phoenix `cys(owner=True)` → 대상 데몬 operator.token 을 CYS_OWNER_TOKEN 으로(stage_reinject·stage_g2_ack) · cysd `reject_send` 거부 줄에 caller_cmd·parent_pid·parent_cmd | test_phoenix_v115_owner_token(M2/2 KILLED) · cysd v115_reject_log_line · 격리 재현: 토큰 없음 = `acl denied external→worker`(caller_cmd = `cys --socket … reinject --check --role worker`) / 수리판 = owner_granted + ACK |
| f2fd9782 | A3 | 승계·npm 고지 = `Daemon::display_notice`(화면 출력 · 입력 주입 0 · 입력 원장 0) · `governance::hold_for_vacant_seat`(send_text 보류 본체 이관) · `seat_inject_guarded`(채널·스케줄·부트감독 통보) · CEO 라우팅 즉시 프로브 · UI role.takeover 토스트 | 실 zsh -f 좌석 시험(뮤턴트 옛 Inject = `zsh: no matches found` KILLED) · seat_inject_guarded 보류(뮤턴트 KILLED) |
| b3a2ee04 | A4 알림 | cysd `restore.retrying`(첫 비0 ∧ master 부재) · UI 「⏳ 자비스 자리를 다시 세우는 중」 | v115_restore_retry_notice |
| 2f693ee1 | A4 수리(master 승인 702eb269·8026e869) | `javis_phoenix.py` run_restore 스폰 재시도 루프 **2413~2438행** 정착 판정 `_revived_seat`(기동 실패 줄 없음 ∧ agent_alive True ∧ seat≠empty — 905 빈 좌석 조건 흡수) | test_phoenix_v115_spawn_settle(뮤턴트 3/3 KILLED) · a3/r4 기대 갱신 · phoenix 시험 17/17 |
| 87aa784f | B6 | `ResetRoots.claude_config_dir`·`defaults_domain`(live() 만 채움) — 시험이 실행자의 실 프로필·앱 설정 도메인을 안 건드림 | lib factory_reset 3회 연속 31/31 · 뮤턴트(env 직접 읽기) KILLED(실 ~/.cys/claude/settings.json 을 집음) |
| f8d59f2e | B4 | `watch_wake::role_held_now` — 감시 각성은 역할표가 가리키는 좌석만(옛 자리 role 칸 잔존) · check_idle·agent.exited 2곳 | stale_role_label_on_old_seat(뮤턴트 KILLED · 사진 문구 그대로 재현) |
| 76d33b4d | B5 | 복원 카드 = 조직 복원 done/error 뒤(신호 없으면 15초 유예) | restorebrief.test 3 · 뮤턴트 KILLED |

A4 원인 정본 = `~/axdev/master/reports/cysr-115-2026-09-22/a4-vm-logs/A4-FINDINGS.md`.

## 미완
- ~~B1 수리 구현~~ → §0-r2 에서 ①② 완료 · ③ 이월.
- 게이트 실측(13:0x): lib 530/0 · cysd 1012/0(3연속) · cys 278/0 · ui 1065/0 · tsc 0 · secret-scan --all clean · cys-app 미측정(사이드카 부재).

## 함정
- `cargo` = `$HOME/.cargo/bin` (PATH 에 없음).
- macOS 에 `timeout` 없음 → `perl -e 'alarm N; exec @ARGV or exit 126'`.
- 격리 cysd 소켓 = `/tmp/cysXXXX`(SUN_LEN) · 좌석 PATH 는 로그인 셸 path_helper 가 재정렬 → 가짜 claude 대신 진짜 claude 가 뜰 수 있다(A4 재현 시 실측).
- VM 재기동 = LaunchAgents 자동 로드로 cysd 가 스스로 뜬다(로그 채집은 켜자마자).
- factory_reset 시험은 종전 판에서 `defaults delete com.cysjavis.terminal` 을 실제로 돌렸다(B6 로 차단) — 이 기기 plist 는 09-15 이후 무변경·빈 도메인 실측.
- A3 의 `display_notice` 한계: 셸 줄 편집기는 이 줄을 모른다(프롬프트가 고지 위에 남아 보임 · 입력 영향 0).
- A4 수리의 `_failed_now` 는 `spawn_production` 출력 800자 절단 뒤를 못 본다(역할 많을 때) — agent_alive·seat 조건이 뒤를 받친다.

## 재현
- phoenix 시험: `for t in cysjavis-pack/bin/tests/test_phoenix_*.py; do python3 $t | tail -1; done`
- cysd: `cargo test --bin cysd v115_` · watch_wake: `cargo test --bin cysd watch_wake`
- ui: `cd ui && bun test src/restorebrief.test.ts`
