너는 적대적 코드 검증자다. 파일 생성·수정·커밋·빌드·시험 실행·네트워크 사용 금지 — 읽기와 판정만 한다. 지정 범위 밖 배회 금지.

## 대상
- 저장소 = 지금 폴더(git worktree · 가지 feat/1116-skt1). 고침 범위 = `git diff 0eff2a6f1..HEAD`(그 앞 0eff2a6f1 은 옛 가지 feat/seatkeep-t1 e2f2ae889 를 1.1.16 위로 옮긴 커밋 · 51c556a1c 는 CI 등재만).
- 직전 판정문(네가 r5c 에서 낸 BLOCK 4건) = `~/axdev/master/reviews/codex-queue-2026-11-13/r4/3-seatkeep-t1.r5c.verdict.md` — 먼저 읽어라.
- 처분 표·설계 요지 = `HANDOFF.cysr-1116-skt1-1119.md` §0·§2·§3·§7.
- 주 파일: `src/session_lease.rs`(leaf: seat_bound_conversation · held_by_live_writer · argv_is_agent_exec · lineage_proves_not_top_hook · judge 의 unknown 풀림) · `src/session_lease_cli.rs`(seat_conversation_now · role_seat_verdict · lease_role_seat_verdict · lease_judge_reused_seat · lease_follow_on_register · follow_lineage_not_top) · `src/bin/cys.rs`(run_launch_agent_opts 의 #1 방어 배선과 rc 93 안내 · run_boot 의 rc 92 · run_launch_agent_resume_saved) · `src-tauri/src/main.rs`(restore_judge_two · run_sidecar_restore_judged · restore_lease_held · read_daemon_gen · parse_restore_unknown_refusals) · `cysjavis-pack/bin/javis_boot_node.py`(_lease_refusal_line · resume_refused) · 시험(`tests/session_lease_e2e.rs` FR·SR · `tests/fixtures/fake_claude.c` · `src/session_lease_cli_tests.rs` role_seat_verdict_truth_table · Tauri seatkeep_r5_3).
- 데몬 쪽 근거(읽기만): `src/bin/cysd/handlers.rs` usage.register(소유 게이트 · registered_transcript · repin_anchor) · `src/bin/cysd/usage.rs` lineage_proves_not_top_hook · `src/bin/cysd/governance.rs` caller_lineage·cmdline_matches_agent_exec.

## 물음
1. r5c #1~#4 각각: 이 고침으로 판정문의 재현 순서가 닫혔는가? 순서를 코드에 다시 대입해 결과(rc · 좌석 수 · S 작성자 수 · 임대 상태)를 적어라. 닫히지 않았으면 남은 순서를 구체적으로.
2. 새 증거 원천(「산 작성자에게 묶인 작성 중 임대」 = follow 만 만든다)이 새로 여는 길: (a) follow 가 계통 판독 불가(None)일 때 옮기는 것(윈도우·argv 미관측) (b) 같은 에이전트 프로세스가 좌석 안 /resume S 를 했는데 그 SessionStart 훅의 등록이 실패한 경우(결속이 옛 T 로 남음) (c) 결속 판독을 잠금 없이 읽는 것(acquire 의 잠금 안 judge 에서 다른 파일을 읽음) (d) 산 결속 둘 = Err 로 막는 것이 정상 흐름을 고착시키는가 (e) codex 등 비-claude 좌석의 topology 관측을 「다른 대화」 증거로 쓰는 것(가짜 등록이 데몬 세션 파일 결정·핀을 덮는 길이 있는가 · usage.rs 1494 근처) — 각각 실제 피해(작성자 둘 · 대화 소실 · 영구 고착)로 이어지는지 판정.
3. 1.1.16 편입(§2): rc 93 공유(조각 1 EXIT_RESUME_HELD = 임대 생존 판정 불가) · boot_node 끝 코드 1→93 · run_boot 92 = resume_held 가 소비자(run_boot·javis_bootstrap·phoenix·앱)에서 잘못 읽히는 곳이 있는가.
4. 정상 복원 차단(거짓 막힘)이 이 고침으로 새로 생기거나 넓어진 곳(특히 훅 있는 정상 claude 좌석 · 막 뜬 좌석 · 부서 데몬 둘).
5. 시험이 대상을 실제로 잡는가(FR·SR·진리표·Tauri r5_3) — 픽스처(가짜 claude 의 FAKE_CYS · session-start.sh 셸)가 진짜 claude 와 다른 탓에 놓치는 것.

## 형식
첫 줄 `VERDICT: ACCEPT | REVISE | BLOCK`. 그다음 발견 목록(등급 blocking/major/minor · 확신도 · 위치 file:line · 근거 · 재현 순서 · 고침 방향 · 이번 차이가 만든 것인가). 그다음 r5c 4건 처분 확인 표. 마지막에 「검토했지만 문제없다고 본 것」·「확인하지 못한 것」. 실행 실측이 아니라 코드 대입 판정임을 밝혀라.
