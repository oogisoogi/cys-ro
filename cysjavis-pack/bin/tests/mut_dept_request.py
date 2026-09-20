#!/usr/bin/env python3
"""mut_dept_request.py — javis_dept_request.py 뮤턴트 하네스.

각 변이: ⑴원본에 찾을 문자열이 정확히 1회 있는지 ⑵치환 뒤 새 문자열이 실재하는지(적용 단언)
⑶변이 사본으로 test_dept_request 전체를 돌려 **기대 킬러 시험이 적색**인지 — 이름으로 귀속한다.
전 시험이 같은 import 오류로 죽으면 CRASH(측정 무효)로 따로 센다. 기준선(무변이 사본)이 먼저 초록이어야 한다.
사용: python3 tests/mut_dept_request.py [--only M1,M3]
"""
import os, re, shutil, subprocess, sys, tempfile

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BIN, "javis_dept_request.py")

M = [
 ("M1-lost-update", "치명① — 틱 끝에서 표지를 지우는 옛 순서",
  "    if any_in_progress:\n        touch_pending()\n",
  "    if any_in_progress:\n        touch_pending()\n    else:\n        _rm(pending_path())\n",
  ["test_confirm_between_scan_and_finalize_survives"]),
 ("M2-sweep-gated", "치명② — 청소·만료를 표지 게이트 뒤로",
  "changed, moved = _sweep(reqs)                   # ★매 틱 무조건(2R ②)",
  "changed, moved = (_sweep(reqs) if os.path.exists(pending_path()) else ([], []))",
  ["test_sweep_runs_without_marker", "test_cleanup_moves_only_dead_dept_ledgers"]),
 ("M3-tomb-row5", "치명③ — 옛 5행(묘비만으로 닫힘)",
  '(5, "closed", lambda x: x["R"] == "closed" or (x["T"] and not x["G"])),',
  '(5, "closed", lambda x: x["R"] == "closed" or x["T"]),',
  ["test_reused_number_with_residue_is_running_not_closed", "test_self_test_passes"]),
 ("M4-gap-off", "연쇄 — 생성 간격 10분 끄기",
  "    if t - last < CREATE_GAP_SEC():\n        r[\"waiting_gap\"] = True\n",
  "    if False:\n        r[\"waiting_gap\"] = True\n",
  ["test_one_create_per_tick_and_gap"]),
 ("M5-cap-off", "연쇄 — 틱 시점 상한 재점검 끄기",
  "    if len(live) >= chat_cap():\n        _fail(r, \"cap:%d\" % len(live))\n",
  "    if False:\n        _fail(r, \"cap:%d\" % len(live))\n",
  ["test_cap_reached_at_tick_fails"]),
 ("M6-many-per-tick", "연쇄 — 한 틱에 확인 요청 전부 생성",
  "                r = creates[0]\n                before = r[\"state\"]\n",
  "                for _r in creates[:-1]:\n                    _create_step(_r, st, reqs); save_req(_r)\n                r = creates[-1]\n                before = r[\"state\"]\n",
  ["test_one_per_tick_even_without_gap"]),
 ("M7-base-exclusion+regex", "B-1/R4 — 본부 제외 끄기 + 부서 모양 판별 끄기(두 벨트 동시)",
  "        if key in base_keys:\n            continue\n",
  "        if False:\n            continue\n",
  ["test_cleanup_moves_only_dead_dept_ledgers"],
  [('m = re.search(r"cys-dept-([A-Za-z0-9][A-Za-z0-9_-]{0,39})", sock)',
    'm = re.search(r"[\\\\/]([^\\\\/]+)[\\\\/]cys\\.sock$", sock)')]),
 ("M7a-base-exclusion-only", "B-1/R4 — 본부 제외만 끄기(부서 모양 판별이 두 번째 벨트 — 생존 예상)",
  "        if key in base_keys:\n            continue\n",
  "        if False:\n            continue\n",
  []),
 ("M8-cleanup-off", "B-1 — 고아 원장 청소 끄기",
  "    moved = cleanup_orphan_ledgers()\n",
  "    moved = []\n",
  ["test_cleanup_moves_only_dead_dept_ledgers"]),
 ("M9-recall-while-alive", "2R ⑦ — 첫 자식 생존 확인 끄기",
  "        if pid and _pid_alive(pid):\n            # ★2R ⑦",
  "        if False:\n            # ★2R ⑦",
  ["test_no_recall_while_first_child_alive"]),
 ("M10-lane-off", "4군① — 레인 판정 끄기",
  "    env = os.environ if env is None else env\n    s = env.get(\"CYS_SOCKET\", \"\") or \"\"\n",
  "    return True\n    env = os.environ if env is None else env\n    s = env.get(\"CYS_SOCKET\", \"\") or \"\"\n",
  ["test_propose_blocked_at_cap_and_lane", "test_self_test_passes"]),
 ("M11-primary-collision", "2R ④ — CYS_PRIMARY_ACCOUNT 대조 끄기",
  "    if account_mode() == \"shared\" and SHARED_ACCOUNT_KEY != primary_key():\n",
  "    if account_mode() == \"shared\":\n",
  ["test_card_login_line_follows_primary_account", "test_self_test_passes"]),
 ("M12-path-convention", "A-5 — 작업 폴더 규약 한 글자",
  '    return os.path.join(home(), "Desktop", "CYSjavis", display)\n',
  '    return os.path.join(home(), "Desktop", "CYSJavis", display)\n',
  ["test_self_test_passes"]),
 ("M13-user-claude-md", "§5-1 — 사용자 CLAUDE.md 보존 끄기",
  "        return None if same else \"claude_md_conflict\"",
  "        return None",
  ["test_user_claude_md_is_never_overwritten"]),
 ("M14-notify-dup", "4군① — 알림 1회 보장 끄기",
  "    if key in (r.get(\"notified\") or []):\n        return\n",
  "    if False:\n        return\n",
  ["test_notify_is_once_per_state"]),
 ("M15-detach-off", "V-DETACH — start_new_session 끄기",
  "                             start_new_session=(os.name != \"nt\"))",
  "                             start_new_session=False)",
  ["test_propose_confirm_tick_creates"]),
 ("M16-tamper", "A-2 — sha 잠금 재대조 끄기",
  "    if sha256_text(text) != r[\"claude_md_sha256\"]:\n        return \"claude_md_changed\"\n",
  "    if False:\n        return \"claude_md_changed\"\n",
  ["test_tampered_claude_md_after_confirm_fails"]),
 # ── A1-2b · agy 1R F1 + codex 1R 수용분(수리 1건당 뮤턴트 1) ──
 ("M17-agy-crash", "agy F1 — 요청 단위 예외 격리 끄기(틱 전체 사망)",
  "        _fail(r, \"crash:%s\" % type(e).__name__)\n",
  "        raise\n",
  ["test_agy_f1_step_crash_fails_request_not_tick"]),
 ("M18-utter-updated", "codex F1 — 발화 원문 기한을 updated_at 기준으로",
  "        if t - (r.get(\"created_at\") or t) > 7 * DAY and os.path.exists(utter):\n",
  "        if t - (r.get(\"updated_at\") or t) > 7 * DAY and os.path.exists(utter):\n",
  ["test_f1_utterance_deleted_7d_after_proposal_in_any_state"]),
 ("M19-reentry-timeout-only", "codex F2 — 재진입을 create-timeout 상태로만",
  "    reentry = r[\"state\"] == \"create-timeout\" or bool(r.get(\"create_calls\"))\n",
  "    reentry = r[\"state\"] == \"create-timeout\"\n",
  ["test_f2_no_respawn_when_tick_died_mid_wait"]),
 ("M20-claimed-dept-name", "codex F3 — --all 이 옛 dept_name 으로 번호를 가림",
  "        claimed = {reg_name_for_key(r.get(\"key\"), reg) for r in reqs\n",
  "        claimed = {r.get(\"dept_name\") for r in reqs} | {reg_name_for_key(r.get(\"key\"), reg) for r in reqs\n",
  ["test_f3_reused_number_listed_in_status_all"]),
 ("M21-cap-excludes-tomb", "codex F4 — 상한에서 묘비 부서 빼기",
  "    reg = registry() if reg is None else reg\n    return dict(reg)\n",
  "    reg = registry() if reg is None else reg\n    return {n: e for n, e in reg.items() if n not in (tombstones() if ts is None else ts)}\n",
  ["test_f4_tombstone_residue_counts_toward_cap"]),
 ("M22-retry-skips-gap", "codex F5 — 재호출이 간격 검사를 건너뜀",
  "    if t - last < CREATE_GAP_SEC():\n        r[\"waiting_gap\"] = True\n",
  "    if not reentry and t - last < CREATE_GAP_SEC():\n        r[\"waiting_gap\"] = True\n",
  ["test_f5_retry_respects_gap"]),
 ("M23-marker-only", "codex F6 — 표식만 보고 같은 파일로 치기(사람이 고친 생성 파일)",
  "                same = f.read() == text\n",
  "                same = f.readline().startswith(MARKER_PREFIX)\n",
  ["test_f6_edited_generated_claude_md_is_conflict"]),
 ("M24-retry-skips-md", "codex F7 — 재호출이 안내문 대조를 건너뜀",
  "    err = _write_claude_md(r)                            # 재호출 직전에도",
  "    err = None if reentry else _write_claude_md(r)  # 재호출 직전에도",
  ["test_f7_retry_rechecks_claude_md"]),
 ("M25-supersede-stale", "codex F8 — 제안 교체가 잠금 재독 없이 옛 객체 저장",
  "            transition(r[\"id\"], (\"proposed\",), sup)",
  "            sup(r); save_req(r)",
  ["test_f8_stale_writers_do_not_revert_confirm"]),
 ("M26-lock-always", "codex F9 — 틱 잠금이 보유자를 무시",
  "    if lk.acquire() != javis_lock.ACQUIRED:\n        return False\n    _LOCK = lk\n",
  "    lk.acquire()\n    _LOCK = lk\n",
  ["test_f9_tick_lock_is_kernel_held"]),
 ("M27-close-identity-off", "codex F10 — 닫기 대상 동일성 대조 끄기",
  "        if f_req in r and r.get(f_req) != cur.get(f_reg):\n",
  "        if False:\n",
  ["test_f10_close_refuses_when_number_now_other_dept"]),
 ("M28-discard-unlocked", "codex F11 — 지우기가 틱 잠금을 무시",
  "    if not acquire_lock():\n        return _refuse(\"지금 부서 일을",
  "    if not (acquire_lock() or True):\n        return _refuse(\"지금 부서 일을",
  ["test_f11_discard_waits_for_tick_lock"]),
 ("M29-registry-lenient", "codex F12 — 못 읽은 레지스트리 = 부서 없음",
  "        raise RegistryUnreadable(\"%s: %s\" % (type(e).__name__, e))\n",
  "        return {}\n",
  ["test_f12_unreadable_registry_holds_destruction"]),
 ("M30-running-save-after", "codex F14 — 가동 알림 기록을 보낸 뒤에 저장"
  "(★A1-2c #4 이후 재판정 — 이 벨트 단독 제거는 이제 층 방어로 생존 예상. 근거는 M30a)",
  "                        r[\"running_notified\"] = now()\n                        save_req(r)\n",
  "                        r[\"running_notified\"] = now()\n",
  []),
 ("M30a-running+notify-save-after", "codex F14 + A1-2c #4 — 두 벨트 동시 끄기(층 방어 실증 · M7/M7a 동형 —"
  " M30 단독은 _notify 자신의 선저장(A1-2c #4)이 받쳐 생존하고, 둘 다 끄면 다시 중복 발송이 드러난다)",
  "                        r[\"running_notified\"] = now()\n                        save_req(r)\n",
  "                        r[\"running_notified\"] = now()\n",
  ["test_f14_running_notify_not_duplicated_after_crash"],
  [('    key = "%s:%s" % (tag, r.get("state"))\n    if key in (r.get("notified") or []):\n        return\n    r.setdefault("notified", []).append(key)\n    save_req(r)\n    body = "[%s] %s" % (tag, r["id"])\n    try:\n        env = dict(os.environ)\n        p = subprocess.run([_cys_bin(), "send", "--queued", "--to", "master", body], capture_output=True,\n                           text=True, timeout=20, env=env, **NOWIN)\n        rc = p.returncode\n    except Exception:\n        rc = 127\n    _event(r, "notify %s rc=%s" % (tag, rc))\n',
    '    key = "%s:%s" % (tag, r.get("state"))\n    if key in (r.get("notified") or []):\n        return\n    body = "[%s] %s" % (tag, r["id"])\n    try:\n        env = dict(os.environ)\n        p = subprocess.run([_cys_bin(), "send", "--queued", "--to", "master", body], capture_output=True,\n                           text=True, timeout=20, env=env, **NOWIN)\n        rc = p.returncode\n    except Exception:\n        rc = 127\n    r.setdefault("notified", []).append(key)\n    _event(r, "notify %s rc=%s" % (tag, rc))\n')]),
 ("M31-md-read-raises", "codex F15 — 안내문 읽기 실패가 요청 판정이 아니라 예외",
  "        return \"claude_md_changed\"\n    if sha256_text(text) != r[\"claude_md_sha256\"]:\n        return \"claude_md_changed\"\n    dest",
  "        raise\n    if sha256_text(text) != r[\"claude_md_sha256\"]:\n        return \"claude_md_changed\"\n    dest",
  ["test_f15_missing_claude_md_is_request_failure"]),
 ("M32-stdout-pipe", "codex F16 — 떼어 낸 자식 stdout 을 틱 파이프로",
  "[cys_dept_bin(), \"create\", key], stdout=of,",
  "[cys_dept_bin(), \"create\", key], stdout=subprocess.PIPE,",
  ["test_f16_detached_child_output_survives_tick_exit"]),
 ("M33-fresh-tomb-removed", "codex F17 — 생성 뒤 새 묘비까지 해소",
  "    if name in (r.get(\"pre_ts\") or []) and name in tombstones():\n",
  "    if name in tombstones():\n",
  ["test_f17_fresh_tombstone_after_create_is_kept"]),
 # ── A1-2b 2R(agy·codex) 수용분 ──
 ("M34-row7-gap-say", "2R agy — 7행 자동 재시도 대기 문장 끄기",
  "        if (r or {}).get(\"state\") == \"create-timeout\" and r.get(\"waiting_gap\"):\n",
  "        if False:\n",
  ["test_2r_agy_row7_waiting_gap_says_auto_retry"]),
 ("M35-failsay-crash", "2R agy — crash 사유 문장 빼기",
  "    \"crash\": \"부서 일을 처리하던 중",
  "    \"crash-x\": \"부서 일을 처리하던 중",
  ["test_2r_agy_fail_say_has_no_raw_reason"]),
 ("M36-unknown-child", "2R codex F1 — pid 없는 재진입(생사 불명) 대기 끄기",
  "        if not pid and t - (r.get(\"create_started_at\") or t) < CREATE_HANG_SEC():\n",
  "        if False:\n",
  ["test_2r_f1_unknown_child_blocks_recall"]),
 ("M37-discard-stale", "2R codex F2 — discard 가 옛 객체로 저장",
  "    ok, cur = transition(r[\"id\"], DISCARDABLE, disc)\n",
  "    disc(r); save_req(r); ok, cur = True, r\n",
  ["test_2r_f2_discard_stale_read_keeps_confirm"]),
 ("M38-claimed-close", "2R codex F3 — 닫기 요청도 --all 소유 주장",
  "                   if r.get(\"key\") and r.get(\"kind\") == \"create\"}",
  "                   if r.get(\"key\")}",
  ["test_2r_f3_closed_menu_dept_reregistered_is_listed"]),
 ("M39-orphan-utter", "2R codex F8 — 기록 없는 요청 폴더 원문 청소 끄기",
  "    for n in orphans:",
  "    for n in []:",
  ["test_2r_f8_orphan_request_dir_utterance_7d"]),
 ("M40-rm-oserror", "2R codex F9 — 삭제 OSError 격리 끄기",
  "    except OSError as e:                                   # 2R(codex F9)",
  "    except ZeroDivisionError as e:  # 2R(codex F9)",
  ["test_2r_f9_rm_failure_does_not_kill_tick"]),
 ("M41-kickoff-marker", "2R codex F11 — 미전송 시 kickoff 표지 해제 끄기",
  "        _rm(kp)                                            # 2R(codex F11)",
  "        pass  # 2R(codex F11)",
  ["test_2r_f11_kickoff_unsent_releases_marker"]),
 ("M42-discard-edited-md", "2R codex F12 — 사람이 고친 CLAUDE.md 도 지우기",
  "            if _generated_untouched(cm):\n",
  "            if True:\n",
  ["test_2r_f12_discard_keeps_edited_claude_md"]),
 # ── A1-2c · VERIFY-dept-impl-r1.md 「수정 필수 표」 반영(수리 1건당 뮤턴트 1 · #3 은 시험만이라 뮤턴트 없음) ──
 ("M43-schema-mismatch-lenient", "VERIFY #1 — depts 스키마 불일치를 「부서 없음」으로",
  '    if not isinstance(d, dict) or not all(isinstance(e, dict) for e in d.values()):\n        raise RegistryUnreadable("스키마 불일치(depts 가 객체의 객체가 아님)")\n',
  '    if not isinstance(d, dict) or not all(isinstance(e, dict) for e in d.values()):\n        return {}\n',
  ["test_a1_2c_1_schema_mismatch_registry_holds_destruction"]),
 ("M44-discard-exists-off", "VERIFY #2 — 가동 부서가 있는 create 요청도 discard 허용",
  '    if r.get("kind") == "create" and r.get("key") and reg_name_for_key(r["key"], reg):\n        return _refuse("이미 만들어진 부서가 있어 지울 수 없습니다 — 닫기로 말씀해 주세요.", code=7, reason="exists")\n',
  '    if False:\n        return _refuse("이미 만들어진 부서가 있어 지울 수 없습니다 — 닫기로 말씀해 주세요.", code=7, reason="exists")\n',
  ["test_a1_2c_2_discard_refuses_when_dept_exists"]),
 ("M45-notify-save-after-send", "VERIFY #4 — 「부서결과」 알림 기록·저장을 전송 뒤로(중복 창 되돌리기)",
  '    key = "%s:%s" % (tag, r.get("state"))\n    if key in (r.get("notified") or []):\n        return\n    r.setdefault("notified", []).append(key)\n    save_req(r)\n    body = "[%s] %s" % (tag, r["id"])\n    try:\n        env = dict(os.environ)\n        p = subprocess.run([_cys_bin(), "send", "--queued", "--to", "master", body], capture_output=True,\n                           text=True, timeout=20, env=env, **NOWIN)\n        rc = p.returncode\n    except Exception:\n        rc = 127\n    _event(r, "notify %s rc=%s" % (tag, rc))\n',
  '    key = "%s:%s" % (tag, r.get("state"))\n    if key in (r.get("notified") or []):\n        return\n    body = "[%s] %s" % (tag, r["id"])\n    try:\n        env = dict(os.environ)\n        p = subprocess.run([_cys_bin(), "send", "--queued", "--to", "master", body], capture_output=True,\n                           text=True, timeout=20, env=env, **NOWIN)\n        rc = p.returncode\n    except Exception:\n        rc = 127\n    r.setdefault("notified", []).append(key)\n    _event(r, "notify %s rc=%s" % (tag, rc))\n',
  ["test_a1_2c_4_result_notify_recorded_before_send"]),
]


def run(mod_path):
    env = dict(os.environ, DEPT_REQUEST_MODULE=mod_path, PYTHONWARNINGS="ignore")
    p = subprocess.run([sys.executable, "-m", "unittest", "tests.test_dept_request"], cwd=BIN,
                       capture_output=True, text=True, env=env, timeout=600)
    out = p.stdout + p.stderr
    red = set(re.findall(r"^(?:FAIL|ERROR): (test_\w+)", out, re.M))
    total = re.search(r"Ran (\d+) tests", out)
    crash = total is None or (red and len(red) == int(total.group(1)) and "SyntaxError" in out)
    return p.returncode, red, crash, out


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    src = open(SRC, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="mutdept-")
    try:
        base = os.path.join(tmp, "base.py")
        open(base, "w", encoding="utf-8").write(src)
        rc, red, crash, out = run(base)
        print("BASELINE rc=%d red=%s" % (rc, sorted(red)))
        if rc != 0:
            print(out[-3000:]); return 2
        bad = 0
        for spec in M:
            mid, why, old, new, killers = spec[:5]
            extra = spec[5] if len(spec) > 5 else []
            if only and mid.split("-")[0] not in only and mid not in only:
                continue
            s = src
            pairs = [(old, new)] + list(extra)
            ok = True
            for o, n in pairs:
                c = s.count(o)
                if c != 1:
                    print("NOT-APPLICABLE %s — 찾을 문자열 %d회" % (mid, c)); ok = False; break
                s = s.replace(o, n)
                if n not in s:
                    print("NOT-APPLIED %s" % mid); ok = False; break
            if not ok:
                bad += 1; continue
            mp = os.path.join(tmp, mid + ".py")
            open(mp, "w", encoding="utf-8").write(s)
            rc, red, crash, out = run(mp)
            if crash:
                print("CRASH %s — 측정 무효" % mid); bad += 1; continue
            if not killers:
                verdict = "SURVIVED(예상 — 층 방어)" if rc == 0 else "KILLED(예상 밖) by %s" % sorted(red)
                print("%s %s — %s" % (verdict, mid, why)); continue
            hit = sorted(set(killers) & red)
            if rc != 0 and hit:
                print("KILLED %s by %s (적색 전체 %d) — %s" % (mid, hit, len(red), why))
            else:
                print("SURVIVED %s — 기대 킬러 %s 적색 아님 (적색=%s) — %s" % (mid, killers, sorted(red), why))
                bad += 1
        print("MUTANTS %s" % ("ALL-KILLED" if not bad else "%d PROBLEM" % bad))
        return 0 if not bad else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
