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
  "        if t - last < CREATE_GAP_SEC():\n",
  "        if False:\n",
  ["test_one_create_per_tick_and_gap"]),
 ("M5-cap-off", "연쇄 — 틱 시점 상한 재점검 끄기",
  "        if len(live) >= chat_cap():\n            _fail(r, \"cap:%d\" % len(live))\n",
  "        if False:\n            _fail(r, \"cap:%d\" % len(live))\n",
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
  "    if os.path.exists(dest) and not claude_md_marker(dest):\n",
  "    if False:\n",
  ["test_user_claude_md_is_never_overwritten"]),
 ("M14-notify-dup", "4군① — 알림 1회 보장 끄기",
  "    if key in (r.get(\"notified\") or []):\n        return\n",
  "    if False:\n        return\n",
  ["test_notify_is_once_per_state"]),
 ("M15-detach-off", "V-DETACH — start_new_session 끄기",
  "                         start_new_session=(os.name != \"nt\"))",
  "                         start_new_session=False)",
  ["test_propose_confirm_tick_creates"]),
 ("M16-tamper", "A-2 — sha 잠금 재대조 끄기",
  "    if sha256_text(text) != r[\"claude_md_sha256\"]:\n        return \"claude_md_changed\"\n",
  "    if False:\n        return \"claude_md_changed\"\n",
  ["test_tampered_claude_md_after_confirm_fails"]),
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
