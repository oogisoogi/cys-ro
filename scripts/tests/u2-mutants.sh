#!/bin/bash
# u2-mutants.sh — 1.1.8 U2 수리 증명(브리프 §2-8 「뮤테이션 각 축 1」 · U1 u1-mutants.sh 와 같은 꼴): 가드마다 「가드 있음 = 녹 · 가드 끔 = 적」.
#   축 = 교체 중 kill(U2-CANON) · 롤백 경로(U2-QUAR) · 저널 손상(U2-RECON) · 잠금 경합(U2-TOK) + 보조(부팅 가드·최대 한 번·정확히 한 번·
#   S5 재검사·V3·RENAME_NOFOLLOW_ANY). 가드는 `update::mutant("<번호>")`(시험 빌드에서만 켜짐 · env `CYS_U1_MUTANT` 공용).
#   U2-IMG(윈 이미지 대조)는 윈 전용 코드라 이 맥 목록 밖(윈 러너 몫).
# 사용: U1_ISO=<격리 래퍼> scripts/tests/u2-mutants.sh   · exit 0 = 전건 OK · 1 = BAD 있음 · 2 = 판정 불가(src/ 더러움)
set -u
ROOT=$(git rev-parse --show-toplevel) || exit 2
cd "$ROOT" || exit 2
ISO=${U1_ISO:-}
run() { if [ -n "$ISO" ]; then "$ISO" "$@"; else "$@"; fi; }
if [ -n "$(git status --porcelain -- src)" ]; then echo "u2-mutants: 판정 불가 — src/ 작업트리가 깨끗하지 않다" >&2; exit 2; fi
run cargo test -q --lib --no-run >/dev/null 2>&1 || { echo "u2-mutants: 판정 불가 — 시험 빌드 실패" >&2; exit 2; }
run cargo test -q --bin cys --no-run >/dev/null 2>&1 || { echo "u2-mutants: 판정 불가 — cys 시험 빌드 실패" >&2; exit 2; }
fail=0
# 적 = 「test result: FAILED」 가 실제로 찍힘(컴파일 실패 101 을 적으로 세지 않는다 — U1 3R F11 교훈)
# 대상 = 기본 lib · 「bin:<이름>」 = cys 바이너리 시험(★후속 n12·n13 — 바이너리 쪽 스위치는 cys.rs 안 같은 env)
tgt() { case "$1" in bin:*) echo "--bin cys ${1#bin:}" ;; *) echo "--lib $1" ;; esac; }
red() { run env CYS_U1_MUTANT="$1" cargo test -q $(tgt "$2") -- --exact 2>&1 | grep -q 'test result: FAILED'; }
green() { run cargo test -q $(tgt "$1") -- --exact 2>&1 | grep -q 'test result: ok. 1 passed'; }
while read -r id test; do
  [ -z "$id" ] && continue
  if green "$test"; then g=0; else g=1; fi
  if red "$id" "$test"; then r=1; else r=0; fi
  if [ "$g" -eq 0 ] && [ "$r" -eq 1 ]; then v=OK; else v=BAD; fail=1; fi
  printf '%-4s %-12s 녹=%s 적=%s  %s\n' "$v" "$id" "$g" "$r" "$test"
done <<'LIST'
U2-CANON update::runner::tests::kill_matrix_every_state_before_and_after_recovers_to_one_consistent_version
U2-QUAR update::snapshot::tests::take_verify_restore_file_level_table
U2-RECON update::runner::tests::corrupt_journal_blocks_boot_then_reconstruct_or_seats_blocked
U2-TOK update::quiesce::tests::owner_token_must_match_and_lock_must_be_held
U2-BOOT update::runner::tests::boot_blocked_allows_only_live_lock_holder_for_non_terminal_journal
U2-ATMOST update::quiesce::tests::b8_crash_matrix_replay_exactly_once_and_inject_at_most_once
U2-REPLAY update::quiesce::tests::b8_crash_matrix_replay_exactly_once_and_inject_at_most_once
U2-S5OUT update::quiesce::tests::s5_recheck_flags_each_change_and_unknown
U2-V3 update::verify::tests::each_violation_fails_its_row
U2-NOFOLLOW update::mac::tests::swap_forward_then_rb_swap_is_idempotent_on_real_apfs
U2-NEST update::lock::tests::nested_delegation_reenters_child_lock_but_siblings_still_exclude
U2-PRIVDIR update::lock::tests::participate_refuses_existing_dir_with_wrong_mode_but_passes_uncreatable
U2-NESTSIB update::lock::tests::nested_siblings_at_same_depth_exclude_each_other
U2-ATTEMPT update::realops::tests::stale_attempt_from_previous_txn_is_never_a_restore_source
U2-PACKCOMMIT update::realops::tests::pack_recovery_keeps_committed_pack_and_restores_only_uncommitted
U2-PACKGATE update::auto::tests::pack_route_uses_pack_only_gate_subset
U2-RESTART update::realops::tests::corrupt_journal_recover_reconstructs_from_this_attempt_and_restarts_daemon
U2-RESTART update::realops::tests::reconstruct_restarts_by_daemon_liveness_and_keeps_guard_until_restarted
U2-ATTEMPTOPEN update::realops::tests::reconstruct_fails_closed_when_this_attempt_is_missing_corrupt_or_foreign
U2-PACKPRO update::realops::tests::pack_recovery_pro_revision_advance_uses_commit_record_and_tuple
U2-PACKPRO pack::tests::pro_revision_advance_kill_matrix_recovers_by_commit_record
U2-V5PRISTINE update::verify::tests::v5_allows_vendor_refresh_of_unmodified_directive_but_guards_user_edits
U2-LINEAGE update::realops::tests::reconstruct_lineage_survives_restart_failure_then_one_more_torn_slot
U2-ENDFIRST update::runner::tests::attempt_end_marks_ended_before_removing
U2-STAGETXN update::realops::tests::stage_is_the_journal_origin_never_the_attempt_or_recovery_token
U2-RECONROUTE update::runner::tests::new_reconstruct_routes_through_s9_row_v_checks_and_single_ok
U2-JCOPY update::runner::tests::new_reconstruct_routes_through_s9_row_v_checks_and_single_ok
U2-TAKEORDER update::runner::tests::takeover_writes_lineage_before_journal_token_and_stops_on_failure
U2-TXNFORM update::runner::tests::malformed_attempt_tokens_are_never_a_source
U2-CANDSEQ update::realops::tests::reconstruct_new_needs_restored_candidate_of_the_same_release
U2-PVATTEMPT update::realops::tests::post_verify_baseline_only_from_live_attempt_of_this_lineage
U2-FILL update::realops::tests::win_s8_fills_missing_rollback_assets_from_archive_or_holds_with_reason
U2-HOLDMEMO bin:tests::pack_auto_hold_memo_skips_download_until_inputs_change
U2-TXNGLUE bin:tests::pack_update_txn_glue_holds_in_a_real_process
U2-MEMOCHECK bin:tests::pack_auto_hold_memo_rejects_forged_unreadable_and_clears_on_manual_apply
U2-MEMOCLEAR bin:tests::pack_auto_hold_memo_rejects_forged_unreadable_and_clears_on_manual_apply
LIST
exit $fail
