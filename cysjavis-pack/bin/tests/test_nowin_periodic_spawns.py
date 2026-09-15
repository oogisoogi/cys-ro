#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_nowin_periodic_spawns.py — 주기 잡 python 의 콘솔 자식 스폰에 창 숨김(NOWIN)이 빠지지 않았는가.

★배경(TICKET=cysr-brand-version · 2026-09-15 워크숍 관측): 윈도우 참가자 기계에서 콘솔 창이
  주기적으로 깜빡였다. 사슬 = cysd(콘솔 없음) → 동봉 bash(CREATE_NO_WINDOW) → python(스케줄 잡)
  → **숨김 없는** cys.exe·powershell·python 스폰 → 새 콘솔 창 할당. 같은 계열의 실사고가
  javis_hud_bridge.py(2026-07-11 · NOWIN 주석)에 이미 기록돼 있었고, 그 처방이 그 파일에만 있었다.
  `cycle-autopilot-tick` 은 **매분** 돌며 틱마다 cys.exe 를 두 번 이상 부른다(gate-check·status).

지키는 것
  ① 대상 파일마다 NOWIN 이 `{"creationflags": 0x08000000} if os.name == "nt" else {}` 로 정의된다
  ② 대상 파일의 **모든** subprocess.run/Popen/check_output/call/check_call 호출이 `**NOWIN` 을 전개한다
  ③ 셀프테스트 — 스캐너가 숨김 누락 검체를 반드시 적색으로, 정상 검체를 초록으로 판정한다
     (스캐너가 대상에 닿지 않아 상시 초록이 되는 공허 통과 방지)

사거리(정직): 정적 검사다. 윈도우에서 창이 실제로 안 뜨는지는 재지 않는다. bash 스크립트(cys-dept)의
  스폰은 python 이 아니라 여기서 못 본다. 대상 목록 밖의 새 주기 잡 스크립트는 목록에 올려야 잡힌다.

실행: python3 test_nowin_periodic_spawns.py   (unittest·파일 직접 실행 — 저장소 관례 준거)
"""
import ast
import os
import unittest

SELF = os.path.dirname(os.path.abspath(__file__))                        # …/bin/tests
BIN = os.path.dirname(SELF)                                              # cysjavis-pack/bin

# 데몬 builtin 잡(schedule.rs builtin_jobs)이 주기로 실행하는 python 과 그 python 이 직접 부르는 형제.
TARGETS = (
    "javis_cycle_autopilot.py",   # cycle-autopilot-tick(매분) · cycle-verifier-watchdog(10분)
    "javis_cycle_verifier.py",
    "javis_formation.py",         # formation-heartbeat(10분)
    "javis_boot_node.py",         # formation ensure 가 부른다
    "javis_learn.py",             # learn-ttl-audit(1일)
    "javis_fleet_report.py",      # fleet-digest(7일)
    "javis_hud_bridge.py",        # 원조 처방 — 회귀 방지로 함께 묶는다
)
SPAWNS = ("run", "Popen", "check_output", "call", "check_call")
CREATE_NO_WINDOW = 0x08000000


def _is_nowin_def(node):
    """`NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}` 모양인가."""
    if not (isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "NOWIN"):
        return False
    v = node.value
    if not isinstance(v, ast.IfExp):
        return False
    body, test, orelse = v.body, v.test, v.orelse
    ok_body = (isinstance(body, ast.Dict) and len(body.keys) == 1
               and isinstance(body.keys[0], ast.Constant) and body.keys[0].value == "creationflags"
               and isinstance(body.values[0], ast.Constant) and body.values[0].value == CREATE_NO_WINDOW)
    ok_test = (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
               and isinstance(test.left, ast.Attribute) and test.left.attr == "name"
               and isinstance(test.left.value, ast.Name) and test.left.value.id == "os"
               and isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value == "nt")
    ok_else = isinstance(orelse, ast.Dict) and not orelse.keys
    return ok_body and ok_test and ok_else


def scan(src):
    """(nowin_defined, spawn_count, missing_linenos) — 순수 함수(셀프테스트 대상)."""
    tree = ast.parse(src)
    defined = any(_is_nowin_def(n) for n in tree.body)
    count, missing = 0, []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"
                and n.func.attr in SPAWNS):
            count += 1
            if not any(k.arg is None and isinstance(k.value, ast.Name) and k.value.id == "NOWIN"
                       for k in n.keywords):
                missing.append(n.lineno)
    return defined, count, missing


class NowinPeriodicSpawns(unittest.TestCase):
    def test_targets_define_nowin_and_spread_it_on_every_spawn(self):
        total = 0
        for name in TARGETS:
            with self.subTest(file=name):
                with open(os.path.join(BIN, name), encoding="utf-8") as f:
                    defined, count, missing = scan(f.read())
                self.assertTrue(defined, "%s: NOWIN 정의(nt 한정 CREATE_NO_WINDOW)가 없다" % name)
                self.assertGreater(count, 0, "%s: subprocess 호출 0건 — 스캐너가 대상에 안 닿았다" % name)
                self.assertEqual(missing, [], "%s: **NOWIN 없는 스폰 줄 %s — 윈도우에서 콘솔 창이 뜬다"
                                 % (name, missing))
                total += count
        # 계수 하한 — 대상이 통째로 비거나 호출이 조용히 사라지면 적색(2026-09-15 실측 27건).
        self.assertGreaterEqual(total, 20, "스폰 계수 %d — 대상 축소·스캐너 파손 의심" % total)

    def test_selftest_scanner_red_on_missing_green_on_good(self):
        good = ('import os, subprocess\n'
                'NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}\n'
                'subprocess.run(["cys"], capture_output=True, **NOWIN)\n')
        self.assertEqual(scan(good), (True, 1, []))
        bad_missing = good + 'subprocess.Popen(["cys", "status"])\n'
        self.assertEqual(scan(bad_missing)[2], [4])
        bad_flag = good.replace("0x08000000", "0x00000200")
        self.assertFalse(scan(bad_flag)[0], "틀린 flag 값을 정의로 인정했다")
        bad_gate = good.replace('"nt"', '"posix"')
        self.assertFalse(scan(bad_gate)[0], "틀린 OS 조건을 정의로 인정했다")
        other_kw = good.replace("**NOWIN", "**OTHER")
        self.assertEqual(scan(other_kw)[2], [3], "다른 이름의 전개를 NOWIN 으로 인정했다")


if __name__ == "__main__":
    unittest.main()
