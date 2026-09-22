# HANDOFF — TICKET=v115-restore (트랙 D · worker@surface:906 · 2026-09-22)

브랜치 `fix/v115-restore` ← 377657dc(v1.1.4 태그) · push 0 · 판번 bump 0.

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
- B1 스크롤 층 판별·수리/우회(필수) — 착수 전 또는 진행 중(아래 진행 줄 참조).
- 최종 게이트: cargo lib·cysd·cys·cys-app · ui 시험 · secret-scan --all · 【확인요청】.

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
