#!/usr/bin/env python3
"""mut_computer_control.py — javis_computer_control.py 뮤턴트 하네스 (TICKET=cu-1111).

각 변이: ⑴원본에 찾을 문자열이 정확히 1회 있는지 ⑵치환 뒤 새 문자열이 실재하는지(적용 단언)
⑶변이 사본으로 test_computer_control 전체를 돌려 **기대 킬러 시험이 적색**인지 — 이름으로 귀속한다.
전 시험이 같은 import 오류로 죽으면 CRASH(측정 무효)로 따로 센다. 기준선(무변이 사본)이 먼저 초록이어야 한다.
사용: python3 tests/mut_computer_control.py [--only M1,M3]
"""
import os, re, shutil, subprocess, sys, tempfile

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BIN, "javis_computer_control.py")

M = [
 ("M1-unknown-ready", "?→바로 — 모름이 섞여도 바로",
  "    if not missing and not unknown:\n        return READY, False, [], \"화면 조작",
  "    if not missing:\n        return READY, False, [], \"화면 조작",
  ["test_unknown_never_ready_screen", "test_self_test_passes"]),
 ("M2-plan-check-off", "요금제(팀·기업) 검사 삭제",
  "    if plan == \"no\":\n",
  "    if False:\n",
  ["test_team_plan_not_now", "test_self_test_passes"]),
 ("M3-ask-user", "경계 — 앱 자동화 탐지가 창을 띄우는 판(askUserIfNeeded=true)",
  "ASK_USER_IF_NEEDED = False",
  "ASK_USER_IF_NEEDED = True",
  ["test_ask_user_flag_is_false", "test_self_test_passes"]),
 ("M4-email-leak", "개인정보 — 로그인 이메일이 커넥터 목록으로 새어 나감",
  "\"connectors\": [str(x) for x in ever if isinstance(x, str)] if isinstance(ever, list) else [],",
  "\"connectors\": ([str(x) for x in ever if isinstance(x, str)] if isinstance(ever, list) else []) + ([str(oa.get(\"emailAddress\"))] if isinstance(oa, dict) else []),",
  ["test_privacy_no_markers_in_any_output"]),
 ("M5-protected-listdir", "경계 — 보호 폴더 내용 열람",
  "        if os.path.isdir(os.path.join(home(), sub)):     # 존재만(내용 열람 0)",
  "        if os.path.isdir(os.path.join(home(), sub)) and os.listdir(os.path.join(home(), sub)) is not None:",
  ["test_no_protected_or_secret_reads"]),
 ("M6-grant-all", "선택 = 사용자 — 고르지 않은 것까지 넘김",
  "    for n in sorted(set(picks)):",
  "    for n in sorted(by_n):",
  ["test_grant_only_picked"]),
 ("M7-revoke-unsaved", "거둠이 장부에 안 남음",
  "    save_grants(g)   # 거둠은 저장이 먼저다",
  "    pass   # 거둠은 저장이 먼저다",
  ["test_revoke_removes"]),
 ("M8-ledger-overwrite", "장부 기록 append 전용 깨기",
  "    with open(path, \"a\", encoding=\"utf-8\") as f:\n        f.write(json.dumps(event",
  "    with open(path, \"w\", encoding=\"utf-8\") as f:\n        f.write(json.dumps(event",
  ["test_ledger_append_only"]),
 ("M9-win-screen", "윈도우에서 화면 조작을 바로로",
  "    if plat != \"darwin\":\n        if plat == \"win\":",
  "    if plat not in (\"darwin\", \"win\"):\n        if plat == \"win\":",
  ["test_windows_screen_not_now", "test_self_test_passes"]),
 ("M10-alt-always", "예비 길을 크롬이 바로일 때도 제시",
  "    if t != READY and c.get(\"app\"):",
  "    if c.get(\"app\"):",
  ["test_browser_alt_only_when_chrome_not_ready"]),
 ("M11-settings-any-url", "설정 열기 허용 목록 우회",
  "    url = SETTINGS_URLS.get(a.pane)\n",
  "    url = SETTINGS_URLS.get(a.pane, a.pane)\n",
  ["test_open_settings_allowlist"]),
 ("M12-say-cap-off", "4군② — say 줄 상한 제거",
  "    if len(lines) > MAX_SAY_LINES - 1:",
  "    if False:",
  ["test_say_line_cap"]),
 ("M13-cu-loose", "computer-use 기록을 상위 폴더(다른 프로젝트)에서 빌려 씀",
  "    for cand in (proj, _git_root(proj)):",
  "    for cand in [proj] + [k for k in keys if proj.startswith(k.rstrip(os.sep) + os.sep)]:",
  ["test_cu_project_lookup_strict"]),
 ("M14-first-use-pending", "처음 쓸 때만 묻는 항목이 영원히 준비 중",
  "        state = \"active\" if it[\"tier\"] == READY or first_use_only(it) else \"pending\"",
  "        state = \"active\" if it[\"tier\"] == READY else \"pending\"",
  ["test_first_use_only_active"]),
 ("M15-disabled-ext-ignored", "꺼진 크롬 확장을 켜짐으로",
  "            if s.get(\"state\") == 0 or (isinstance(dr, list) and dr) or (isinstance(dr, int) and dr):",
  "            if s.get(\"state\") == 0:",
  ["test_chrome_disabled_ext_is_hand"]),
 ("M16-stale-scan", "낡은 분석으로 넘김",
  "    if _now() - float(s.get(\"ts\") or 0) > SCAN_TTL_SEC:",
  "    if False:",
  ["test_grant_gates"]),
 ("M17-stdin-inherit", "윈 콘솔 없는 하위 호출에 표준입력 상속",
  "subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,\n",
  "subprocess.run(argv, capture_output=True,\n",
  ["test_subprocess_stdin_devnull"]),
 ("M18-notnow-granted", "지금은 안 됨 항목을 넘김",
  "        if it[\"tier\"] == NOT_NOW:\n            refused.append(it)",
  "        if False:\n            refused.append(it)",
  ["test_not_now_refused"]),
 ("M19-recheck-no-activate", "다시 확인해도 준비 중에서 안 넘어감",
  "            for m in flip:\n                g[\"items\"][m][\"state\"] = \"active\"",
  "            for m in []:\n                g[\"items\"][m][\"state\"] = \"active\"",
  ["test_hand_is_pending_then_recheck_activates"]),
 ("M20-merged-best", "합친 줄 판정을 가장 좋은 것으로",
  "    worst = max(group, key=lambda it: rank[it[\"tier\"]])",
  "    worst = min(group, key=lambda it: rank[it[\"tier\"]])",
  ["test_merged_id_rejudged_by_members"]),
 ("M21-scan-binding-off", "codex 1R #1 — 사용자가 본 목록 대조 끄기",
  "    if scan_id != s.get(\"scan_id\") or os.path.realpath(_project()) != s.get(\"project\"):",
  "    if False:",
  ["test_grant_bound_to_seen_list"]),
 ("M22-merged-key-stored", "codex 1R #2 — 합친 ID 그대로 저장(구성원 펼침 끄기)",
  "        for mid, mtitle in it.get(\"members\") or [[it[\"id\"], it[\"title\"]]]:\n            g[\"items\"][mid] = {\"state\": state,",
  "        for mid, mtitle in [[it[\"id\"], it[\"title\"]]]:\n            g[\"items\"][mid] = {\"state\": state,",
  ["test_member_revoke_removes_everywhere"]),
 ("M23-revoke-exact-only", "codex 1R #2 — 거둠이 정확히 같은 키만",
  "    mids = [m for m in member_ids(a.id) if m in g[\"items\"]]",
  "    mids = [m for m in [a.id] if m in g[\"items\"]]",
  ["test_member_revoke_removes_everywhere"]),
 ("M24-legacy-not-normalized", "codex 1R #2 — 옛 합친 키 정규화 끄기",
  "        for mid in member_ids(k):\n            cur = items.get(mid)",
  "        for mid in [k]:\n            cur = items.get(mid)",
  ["test_legacy_merged_key_normalized"]),
 ("M25-ledger-after-grant", "codex 1R #3 — 장부를 기록보다 먼저 저장",
  "             \"answer_sha256\": hashlib.sha256(answer.encode(\"utf-8\")).hexdigest()})\n    save_grants(g)",
  "             \"answer_sha256\": hashlib.sha256(answer.encode(\"utf-8\")).hexdigest()}) if save_grants(g) is None else None",
  ["test_ledger_failure_leaves_no_active"]),
 ("M27-recheck-first-member", "codex R2 — 합친 줄을 첫 구성원 상태로 대표(장부에 없는 구성원도 맡는다고 말함)",
  "    held = [m for m in member_ids(a.id) if m in g[\"items\"]]\n    if first_use_only(it):",
  "    held = [m for m in member_ids(a.id) if m in g[\"items\"]]\n    held = member_ids(a.id) if held else held\n    g[\"items\"].update({m: {\"state\": \"active\"} for m in held if m not in g[\"items\"]})\n    if first_use_only(it):",
  ["test_recheck_merged_reports_per_member"]),
 ("M28-recheck-first-only", "codex R2 ② — 첫 구성원만 활성화(다음 구성원 pending 고착)",
  "        flip = [m for m in held if g[\"items\"][m].get(\"state\") != \"active\"]",
  "        flip = [m for m in held[:1] if g[\"items\"][m].get(\"state\") != \"active\"]",
  ["test_recheck_merged_activates_all_pending_members"]),
 ("M26-meaning-gate-off", "codex 1R 논쟁점 — 「아니요」에도 요청 창",
  "    if a.meaning != \"yes\":",
  "    if False:",
  ["test_request_prompt_needs_meaning_yes"]),
 ("M29-stdout-locale", "윈 ① — 출력 UTF-8 고정 제거(cp949 콘솔 rc 1)",
  "        _s.reconfigure(encoding=\"utf-8\", errors=\"replace\")",
  "        pass",
  ["test_cp949_stdout_scan_utf8"]),
 ("M30-decode-utf8-only", "윈 ② — 시스템 코드페이지 무시(UTF-8 로만 풂)",
  "    for enc in _sys_codecs():",
  "    for enc in (\"utf-8\",):",
  ["test_reg_output_cp949_decoded"]),
 ("M31-text-mode", "윈 ② — 하위 출력을 다시 text=True(UTF-8 모드 로케일)로",
  "capture_output=True,\n                           timeout=SUBPROC_TIMEOUT",
  "capture_output=True, text=True,\n                           timeout=SUBPROC_TIMEOUT",
  ["test_reg_output_cp949_decoded"]),
 ("M32-msix-off", "윈 ③ — MSIX 사용자 자료 폴더 근거 제거",
  "             os.path.join(la, \"Packages\", \"%s_%s\" % (WIN_MSIX_NAME, WIN_MSIX_PUBLISHER))]",
  "             ]",
  ["test_win_claude_desktop_msix"]),
 ("M33-denied-as-absent", "윈 ③ — 목록 거부를 「없음」으로 단정",
  "    except OSError:\n        return None\n    return any(n.startswith(WIN_MSIX_NAME",
  "    except OSError:\n        return False\n    return any(n.startswith(WIN_MSIX_NAME",
  ["test_win_claude_desktop_msix"]),
 ("M34-default-absent-unknown", "윈 r2 — 크롬 기본 켜기 키 없음을 다시 「모름」으로",
  "    if \"claudeInChromeDefaultEnabled\" not in d:\n        return False",
  "    if \"claudeInChromeDefaultEnabled\" not in d:\n        return None",
  ["test_chrome_default_key_absent_is_off"]),
 # ── cu-1111-precedent: 크롬 켜기·재시작 = 마스터 직접 ──
 ("M35-auto-ext", "확장 설치(사람 손)까지 마스터가 하는 것으로",
  "CHROME_AUTO = (\"default_on\", \"nmh\")",
  "CHROME_AUTO = (\"default_on\", \"nmh\", \"ext\")",
  ["test_chrome_ext_missing_plus_auto_stays_hand", "test_self_test_passes"]),
 ("M36-force-quit", "크롬 강제 종료(-9)",
  "            return _act(\"quit\", [\"/usr/bin/osascript\", \"-e\", 'tell application \"Google Chrome\" to quit'])",
  "            return _act(\"quit\", [\"/usr/bin/pkill\", \"-9\", \"-x\", \"Google Chrome\"])",
  ["test_restart_only_new_nmh_and_running_graceful"]),
 ("M37-idle-gate-off", "사용자 유휴 20초 관문 끄기",
  "        if idle is not None and idle >= IDLE_GATE_SEC:",
  "        if True:",
  ["test_idle_gate_defers_without_touching_chrome"]),
 ("M38-restart-always", "크롬이 꺼져 있었는데도 다시 켜기(재시작 조건 완화)",
  "    if (created or owed) and was_running:",
  "    if (created or owed) and was_running is not None:",
  ["test_nmh_created_by_headless_claude_in_seat_config"]),
 ("M39-no-notice", "크롬 닫기 전 화면 알림 생략",
  "    notify(\"크롬을 잠깐 다시 켭니다\",",
  "    (lambda *_: None)(\"크롬을 잠깐 다시 켭니다\",",
  ["test_restart_only_new_nmh_and_running_graceful"]),
 ("M40-write-whole-file", ".claude.json 을 크롬 키만 남기고 덮어씀",
  "            json.dump(d, f, ensure_ascii=False, indent=2)\n        os.chmod(tmp, mode)",
  "            json.dump({CHROME_KEY: value}, f, ensure_ascii=False, indent=2)\n        os.chmod(tmp, mode)",
  ["test_enable_writes_only_the_key"]),
 ("M41-key-without-record", "감사 기록 없이 키를 씀",
  "        _ledger({\"event\": \"chrome_enable_key\", \"prior\": {\"present\": has, \"value\": v}})   # 기록 먼저",
  "        pass",
  ["test_ledger_failure_leaves_key_untouched"]),
 ("M42-disable-ignores-prior", "끄기가 원래 값을 무시(늘 False)",
  "    target = (prior[\"value\"] if prior.get(\"present\") else None) if isinstance(prior, dict) else False",
  "    target = False",
  ["test_disable_restores_prior_absent_and_removes_our_nmh"]),
 ("M43-disable-rm-any", "남이 고쳐 쓴 연결 파일까지 지움",
  "            mine = _sha_file(nm[\"path\"]) == nm.get(\"sha256\")",
  "            mine = True",
  ["test_disable_keeps_nmh_rewritten_by_others"]),
 ("M44-wait-cap-off", "4군① — 유휴 기다림 상한(540초) 제거",
  "        a.wait = max(0, min(a.wait, 540))",
  "        a.wait = max(0, a.wait)",
  ["test_wait_is_capped"]),
 ("M45-seat-restart-inline", "좌석 재시작을 분리 없이(이 턴 안에서) 실행",
  "    return _act(\"seat_restart\", argv, detach=True)",
  "    return _act(\"seat_restart\", argv, detach=False)",
  ["test_enable_schedules_seat_restart_detached_after_turn"]),
 ("M46-noop-writes", "이미 켜져 있어도 다시 씀·재시작",
  "    if v is not True:\n        if \"prior_key\" not in st:",
  "    if True:\n        if \"prior_key\" not in st:",
  ["test_enable_already_on_is_noop"]),
 ("M47-nmh-in-master-cwd", "헤드리스 claude 를 마스터 폴더에서 실행",
  "    r = _act(\"nmh\", argv, timeout=CLAUDE_HEADLESS_TIMEOUT, cwd=work)",
  "    r = _act(\"nmh\", argv, timeout=CLAUDE_HEADLESS_TIMEOUT)",
  ["test_nmh_created_by_headless_claude_in_seat_config"]),
 ("M48-win-force", "윈 크롬 강제 종료(Stop-Process -Force)",
  "\"Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object { [void]$_.CloseMainWindow() }\"",
  "\"Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force\"",
  ["test_win_quit_is_close_main_window"]),
 ("M49-pkill-by-name", "허락 없을 때 이름 일괄 종료(pkill)",
  "        return _act(\"quit\", [\"/bin/kill\", \"-TERM\", pid])",
  "        return _act(\"quit\", [\"/usr/bin/pkill\", \"-TERM\", \"-x\", \"Google Chrome\"])",
  ["test_restart_without_automation_permission_terms_one_pid"]),
 ("M50-not-quit-retry-hard", "닫히지 않은 크롬을 그대로 다시 켜기(닫힘 확인 생략)",
  "            _ledger({\"event\": \"chrome_not_quit\"})\n            return \"not_quit:%d\" % t",
  "            break",
  ["test_not_quit_is_left_alone"]),
 ("M51-act-stdin-inherit", "크롬 동작의 하위 호출에 표준입력 상속(윈 콘솔 없는 좌석)",
  "subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, cwd=cwd",
  "subprocess.run(argv, capture_output=True, timeout=timeout, cwd=cwd",
  ["test_act_stdin_devnull_and_cwd"]),
 # ── cu-1111-precedent 2단계: 선례 기반 이양 ──
 ("M52-each-overridable", "건마다 유형(결제·가입·비밀번호)을 상시 기록으로 do 로 뒤집을 수 있음",
  "    if known and CATEGORIES[cat][1] in (EACH, NEVER):",
  "    if known and CATEGORIES[cat][1] == NEVER:",
  ["test_each_and_never_not_recordable", "test_self_test_passes"]),
 ("M53-each-recordable", "건마다·안 함 유형도 상시 기록 허용",
  "    if a.cat in CATEGORIES and CATEGORIES[a.cat][1] in (EACH, NEVER):",
  "    if False:",
  ["test_each_and_never_not_recordable"]),
 ("M54-reask-allowed", "재질문 금지 해제(이미 정한 항목을 다시 기록)",
  "    if key in d[\"items\"] and not a.user_changed:",
  "    if False:",
  ["test_unknown_login_asks_once_then_remembers_no_reask"]),
 ("M55-adopt-ignores-deny", "빼라고 한 항목을 adopt 가 다시 가져옴",
  "        if any((dec.get(\"take:%s\" % m) or {}).get(\"meaning\") == \"deny\" for m in mids):",
  "        if False:",
  ["test_adopt_respects_revoke_and_grant_lifts"]),
 ("M56-revoke-no-record", "거둠이 상시 기록을 안 남김",
  "            d[\"items\"][\"take:%s\" % m] = {\"meaning\": \"deny\", \"condition\": \"\", \"at\": _iso(), \"by\": \"revoke\"}",
  "            pass",
  ["test_adopt_respects_revoke_and_grant_lifts"]),
 ("M57-grant-no-lift", "사용자가 다시 골라도 「빼라」 기록이 남음",
  "    if lift:\n        for k in lift:",
  "    if False:\n        for k in lift:",
  ["test_adopt_respects_revoke_and_grant_lifts"]),
 ("M58-unknown-login-do", "쓰는지 모르는 서비스 로그인을 묻지 않고 함",
  "        return ASK, \"precedent:\" + src, \"이 서비스를",
  "        return DO, \"precedent:\" + src, \"이 서비스를",
  ["test_unknown_login_asks_once_then_remembers_no_reask", "test_self_test_passes"]),
 ("M59-terms-off", "약관 위험 서비스(네이버) 판정 끄기",
  "    if known and cat in (\"login\", \"external_send\") and any(k in _norm(subject) for k in TERMS_SERVICES):",
  "    if False and any(k in _norm(subject) for k in TERMS_SERVICES):",
  ["test_terms_service_is_each", "test_self_test_passes"]),
 ("M60-adopt-takes-hand", "adopt 가 손 칸까지 가져옴",
  "        if it[\"tier\"] == READY or first_use_only(it):\n            if all(",
  "        if it[\"tier\"] != NOT_NOW:\n            if all(",
  ["test_adopt_takes_ready_and_reports"]),
 ("M61-remember-unrecorded", "상시 기록을 감사 기록 없이 씀",
  "             \"answer_sha256\": rec[\"answer_sha256\"]})              # 기록 먼저",
  "             \"answer_sha256\": rec[\"answer_sha256\"]}) if False else None",
  ["test_remember_ledger_first"]),
 # M62(상한에서 오래된 결정 삭제 끄기)는 codex R1 반영으로 대상 코드가 없어져 퇴역 — 반대 방향을 M78 이 잰다
 ("M63-conditional-no-condition", "조건부 허락을 조건 없이 기록",
  "    if a.meaning == \"conditional\" and not (a.condition or \"\").strip():",
  "    if False:",
  ["test_external_send_conditional"]),
 ("M64-new-type-do", "선례에 없는 새 유형을 묻지 않고 함",
  "        return ASK, \"new_type\",",
  "        return DO, \"new_type\",",
  ["test_new_type_asks", "test_self_test_passes"]),
 ("M65-tab-loss-silent", "크롬 다시 켠 뒤 탭이 줄어도 말하지 않음",
  "        if at < bt:",
  "        if False:",
  ["test_tab_count_compared_and_loss_reported"]),
 ("M66-new-type-reask", "새 유형은 상시 기록이 있어도 다시 물음(재질문)",
  "    rec = (decisions or {}).get(decision_key(cat, subject))",
  "    if not known:\n        return ASK, \"new_type\", \"\"\n    rec = (decisions or {}).get(decision_key(cat, subject))",
  ["test_new_type_answer_is_remembered_no_reask"]),
 ("M67-owed-restart-ignored", "agy R1 — 미뤄 둔 크롬 재시작을 다음 호출이 잊음",
  "    if (created or owed) and was_running:",
  "    if created and was_running:",
  ["test_deferred_restart_is_owed_and_paid_next_call"]),
 ("M68-owed-seat-dropped", "agy R1 — 미뤄 둔 좌석 재시작을 다음 호출이 잊음",
  "(changed or bool(st.get(\"pending_seat_restart\"))))",
  "(changed or False))",
  ["test_deferred_restart_is_owed_and_paid_next_call"]),
 ("M69-app-exact-only", "agy R1 minor — 앱 이름에 덧붙은 말이 있으면 모름",
  " or aid in s or (_norm(v.get(\"name\")) and _norm(v.get(\"name\")) in s):",
  ":",
  ["test_usage_app_name_with_extra_words"]),
 # ── codex R1 반영 ──
 ("M70-waiter-no-idle", "codex R1 — 좌석 턴이 안 끝났는데 재시작",
  "        if quiet >= 2:\n            break",
  "        if True:\n            break",
  ["test_seat_waiter_rotates_only_after_turn_ends"]),
 ("M71-waiter-giveup-rotates", "codex R1 — 기다리다 지쳐도 재시작(빚 안 남김)",
  "            _ledger({\"event\": \"seat_restart_gave_up\", \"waited\": waited})\n            return out(",
  "            _ledger({\"event\": \"seat_restart_gave_up\", \"waited\": waited})\n            break\n            return out(",
  ["test_seat_waiter_gives_up_and_owes"]),
 ("M72-cas-off", "codex R1 blocking — 비교-교체 없이 덮어씀",
  "        if _read_raw(path) != raw:          # 그 사이 누가 고쳐 썼다 — 덮지 않는다",
  "        if False:          # 그 사이 누가 고쳐 썼다 — 덮지 않는다",
  ["test_cas_conflict_leaves_file_untouched"]),
 ("M73-prior-after-key", "codex R1 — 되돌리기 정보를 키 뒤에 저장",
  "            _write_json(_p(CHROME_STATE), st)     # ★codex R1: 되돌리기 정보가 키보다 먼저 디스크에(실패면 키 불변)",
  "            pass",
  ["test_prior_saved_before_key_write"]),
 ("M74-win-reg-blind-delete", "codex R1 blocking — 윈 연결 등록을 대조 없이 삭제",
  "            mine = bool(nm.get(\"reg\")) and cur == nm.get(\"reg\") and _sha_file(cur) == nm.get(\"sha256\")",
  "            mine = True",
  ["test_win_disable_keeps_registry_changed_by_others"]),
 ("M75-rm-rc-ignored", "codex R1 — 삭제 실패에도 되돌리기 기록을 지움",
  "            if r is not None and r.returncode == 0:\n                said.append(\"제가 만든 연결 파일도 지웠습니다.\")",
  "            if True:\n                said.append(\"제가 만든 연결 파일도 지웠습니다.\")",
  ["test_disable_remove_failure_keeps_record"]),
 ("M76-mask-off", "codex R1 — 대상·한 일·조건 문자열의 개인정보를 그대로 출력",
  "    s = _EMAIL.sub(\"<이메일>\", s or \"\")\n    return _LONGNUM.sub(\"<번호>\", s)[:limit]",
  "    return (s or \"\")[:limit]",
  ["test_personal_strings_masked_and_keys_hashed"]),
 ("M77-standing-beats-signup", "codex R1 blocking — 상시 허락이 새 가입(건마다)을 덮음",
  "    if known and cat == \"login\" and in_use is False:",
  "    if False:",
  ["test_signup_beats_standing_allow", "test_self_test_passes"]),
 ("M78-cap-forgets", "codex R1 — 상한에서 옛 결정을 잊음(재질문)",
  "    if key not in d[\"items\"] and len(d[\"items\"]) >= MAX_DECISIONS:",
  "    if False:",
  ["test_decisions_cap"]),
 ("M79-no-recheck-after-notice", "codex R1 blocking — 알림 뒤 손을 댔는데도 크롬을 닫음",
  "    if idle is None or idle < IDLE_GATE_SEC:\n        _ledger({\"event\": \"chrome_restart_deferred\", \"after_notice\": True})",
  "    if False:\n        _ledger({\"event\": \"chrome_restart_deferred\", \"after_notice\": True})",
  ["test_touch_after_notice_aborts_quit"]),
 ("M80-nmh-gate-off", "codex R1 blocking — 타이핑 중 연결 파일 만들기(크롬 탭 열림)",
  "_nmh_ok(plat, _chrome_userdata(plat)) is not True and not wait_idle(plat, a.wait):",
  "_nmh_ok(plat, _chrome_userdata(plat)) is not True and False:",
  ["test_idle_gate_defers_without_touching_chrome"]),
]


def run_tests(mod_path):
    env = dict(os.environ, CC_MODULE=mod_path)
    r = subprocess.run([sys.executable, "-m", "unittest", "-v", "tests.test_computer_control"],
                       cwd=BIN, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    out = r.stderr + r.stdout
    failed = set(re.findall(r"^(test_\w+) \(.*?\) \.\.\. (?:FAIL|ERROR)", out, re.M))
    total = len(re.findall(r"^(test_\w+) \(.*?\) \.\.\. ", out, re.M))
    return r.returncode, failed, total, out


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    src = open(SRC, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="cc-mut-")
    try:
        base = os.path.join(tmp, "base.py")
        shutil.copy(SRC, base)
        rc, failed, total, out = run_tests(base)
        if rc != 0 or failed:
            print("기준선 적색 — 측정 무효:", sorted(failed))
            print(out[-3000:])
            return 1
        print("기준선 초록 %d건" % total)
        killed = survived = crashed = 0
        for mut in M:
            mid, why, a, b, killers = mut[:5]
            if only and mid.split("-")[0] not in only and mid not in only:
                continue
            if src.count(a) != 1:
                print("%-24s 적용 불가(찾는 문자열 %d회)" % (mid, src.count(a)))
                crashed += 1
                continue
            s = src.replace(a, b)
            assert b in s
            p = os.path.join(tmp, "%s.py" % mid)
            with open(p, "w", encoding="utf-8") as f:
                f.write(s)
            rc, failed, total2, out = run_tests(p)
            if total2 and len(failed) == total2:
                print("%-24s CRASH(전 시험 적색 — 측정 무효)" % mid)
                crashed += 1
                continue
            hit = [k for k in killers if k in failed]
            if killers and hit:
                killed += 1
                print("%-24s KILLED  by %s  (%s)" % (mid, ",".join(hit), why))
            elif not killers and not failed:
                print("%-24s 생존(예상)  (%s)" % (mid, why))
            else:
                survived += 1
                print("%-24s SURVIVED  기대 %s · 실제 적색 %s  (%s)" % (mid, killers, sorted(failed), why))
        print("합계: KILLED %d · SURVIVED %d · CRASH/적용불가 %d" % (killed, survived, crashed))
        return 0 if survived == 0 and crashed == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
