#!/bin/bash
# u1-mutants.sh — 1.1.8 U1 수리 증명(codex 1R·2R「각 수리 = 뮤테이션 1」): 수리마다 「수리 있음 = 녹 · 수리 없음 = 적」 을 기계로 본다.
#
# 두 종류:
#   ① 가드 뮤테이션 — `update::mutant("<번호>")` 가드(시험 빌드에서만 켜짐)를 `CYS_U1_MUTANT=<번호>` 로 끄고 같은 시험을 돌린다.
#   ② 소스 변이 patch — scripts/tests/u1-mutants/<이름>.patch 를 실제로 적용(수리 코드 삭제·되돌림) → 시험 적색 확인 → 되돌림.
#      가드 이름과 무관한 진짜 소스 변이(codex 2R N8 지목 4: B5-any · B7 슬롯 삭제 · M4 부분 fetch · 열거 JSON).
#
# 사용: scripts/tests/u1-mutants.sh            (저장소 안 · 작업트리 깨끗할 것 — patch 적용·되돌림이 작업트리를 만진다)
#   격리: 환경변수 U1_ISO 에 격리 래퍼 경로를 주면 cargo 를 그 안에서 돌린다(예: U1_ISO=/path/isoenv.sh). 없으면 그대로.
# exit 0 = 전건 OK · 1 = 하나라도 BAD(녹이 아니거나 적이 아님) · 2 = 판정 불가(작업트리 더러움·patch 적용 실패)
set -u
ROOT=$(git rev-parse --show-toplevel) || exit 2
cd "$ROOT" || exit 2
ISO=${U1_ISO:-}
run() { if [ -n "$ISO" ]; then "$ISO" "$@"; else "$@"; fi; }
t() { run cargo test -q --lib "$@" -- --exact >/dev/null 2>&1; }
if [ -n "$(git status --porcelain -- src)" ]; then echo "u1-mutants: 판정 불가 — src/ 작업트리가 깨끗하지 않다" >&2; exit 2; fi
fail=0
report() { if [ "$2" -eq 0 ] && [ "$3" -ne 0 ]; then v=OK; else v=BAD; fail=1; fi; printf '%-4s %-16s 녹=%s 적=%s  %s\n' "$v" "$1" "$2" "$3" "$4"; }

# ① 가드 뮤테이션(번호 시험)
while read -r id test; do
  [ -z "$id" ] && continue
  t "$test"; g=$?
  run env CYS_U1_MUTANT="$id" cargo test -q --lib "$test" -- --exact >/dev/null 2>&1; r=$?
  report "$id" "$g" "$r" "$test"
done <<'LIST'
B1 update::buildinfo::tests::b1_release_ignores_env_override_and_never_falls_back_to_dot
B2 update::feed::tests::b2_same_feed_rev_different_envelope_is_replay
B3 update::feed::tests::b3_installed_stop_seats_survives_later_failures
B3 update::check::tests::b3_revocations_copy_freshness_and_integrity
B3r update::cli::tests::b3r_record_revocations_regardless_of_verdict
B4 update::cli::tests::b4_cysr_refuses_caller_installed_seq
B5 update::feed::tests::b5_second_anchor_required_per_target
B6 update::lock::tests::b6_arg_must_equal_env
B6 update::lock::tests::b6_handover_race_and_pid_reuse_rejected
B6g update::lock::tests::b6g_delegated_guard_holds_generation_after_parent_death
B7 update::journal::tests::b7_post_side_effect_slot_corruption_never_runs_prev
M1 update::sched::tests::m1_structure_damage_is_unknown_not_empty
M2 update::win::tests::m2_only_file_not_found_is_absent
M2 update::gates::tests::each_gate_true_false
M3 update::lock::tests::m3_private_permissions
M3 update::lock::tests::m3_existing_wide_lock_file_rejected
M4 update::clock::tests::m4_every_response_date_is_checked
M6 update::feed::tests::accepted_record_roundtrip_and_no_regression
M7 update::hold::tests::m7_readonly_last_seq_validates_monotonic_and_hash
M8 update::gates::tests::m8_seat_fact_requires_every_instrument
M9 update::feed::tests::m9_common_required_fields
SM update::feed::tests::sm_breaking_release_is_feed_reject
RF update::keys::tests::rf_future_signed_revocations_rejected
PM update::feed::tests::pm_payload_manifest_required_on_windows_rows
N4 update::feed::tests::revoked_releases_and_installed_revoked
N4c update::check::tests::n4c_stop_seats_is_forced_decision
N5 update::keys::tests::n5_r_key_expiry_uses_trusted_time
N5r update::check::tests::n5r_suspect_record_keeps_trusted_time
F1 update::check::tests::f1_trusted_lock_excludes_second_writer
F2 update::cli::tests::f2_first_release_still_checks_requires_and_urls
SEQ1 update::cli::tests::seq1_first_release_enumerates_as_single_uptodate_row
LIST

# ② 소스 변이 patch(이름 시험)
while read -r name test; do
  [ -z "$name" ] && continue
  p="scripts/tests/u1-mutants/$name.patch"
  t "$test"; g=$?
  if ! git apply "$p"; then echo "u1-mutants: 판정 불가 — $p 적용 실패(소스가 바뀌었으면 patch 를 다시 만든다)" >&2; exit 2; fi
  trap 'git apply -R "$p" 2>/dev/null' EXIT INT TERM
  t "$test"; r=$?
  git apply -R "$p" || { echo "u1-mutants: $p 되돌림 실패 — 작업트리 확인" >&2; exit 2; }
  trap - EXIT INT TERM
  report "patch:$name" "$g" "$r" "$test"
done <<'LIST'
b5-any update::feed::tests::b5_cysr_any_row_rejected
b7-single-slot update::journal::tests::b7_single_slot_with_missing_peer_is_degraded
m4-partial-fetch update::check::tests::m4_partial_fetch_keeps_every_success_date
enum-json update::cli::tests::n2_enumerate_rows_are_single_verdict_bytes
LIST
exit $fail
