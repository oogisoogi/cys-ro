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
  "    save_grants(g)\n    _ledger({\"event\": \"revoke\"",
  "    _ledger({\"event\": \"revoke\"",
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
  "subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True",
  "subprocess.run(argv, capture_output=True",
  ["test_subprocess_stdin_devnull"]),
 ("M18-notnow-granted", "지금은 안 됨 항목을 넘김",
  "        if it[\"tier\"] == NOT_NOW:\n            refused.append(it)",
  "        if False:\n            refused.append(it)",
  ["test_not_now_refused"]),
 ("M19-recheck-no-activate", "다시 확인해도 준비 중에서 안 넘어감",
  "        if cur is not None and cur.get(\"state\") != \"active\":\n            cur[\"state\"] = \"active\"",
  "        if False:\n            cur[\"state\"] = \"active\"",
  ["test_hand_is_pending_then_recheck_activates"]),
 ("M20-merged-best", "합친 줄 판정을 가장 좋은 것으로",
  "    worst = max(group, key=lambda it: rank[it[\"tier\"]])",
  "    worst = min(group, key=lambda it: rank[it[\"tier\"]])",
  ["test_merged_id_rejudged_by_members"]),
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
