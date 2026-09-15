#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_nowin_captured_spawns.py — 팩 python 의 「출력을 캡처하는」 subprocess 호출은 전부 창을 숨긴다.

★배경(TICKET=cysr-console-flicker-r2 · master#1330e449 · 박사님 노트북 WMI 1분 실측 2026-09-15):
  윈도우에서 콘솔 없는 부모(cysd·pythonw)의 python 이 콘솔 자식(cys.exe·powershell)을 숨김 없이 낳아
  자식마다 콘솔 창이 깜빡였다. 9501dd6 은 주기 잡 6파일만 목록으로 막았고(test_nowin_periodic_spawns),
  목록 밖 파일의 같은 형태는 그대로였다. 이 시험은 목록이 아니라 **규칙**으로 막는다:

  규칙 = 출력을 캡처하는 호출(check_output · capture_output=True · stdout=<None 아님>)은
         `**NOWIN`(nt 한정 CREATE_NO_WINDOW) 또는 creationflags/startupinfo 를 명시한다.
  제외 = 출력을 부모 터미널로 흘리는 호출 — 창을 숨기면 사용자가 볼 출력이 사라지고, pane(ConPTY)
         자식에 CREATE_NO_WINDOW 를 걸면 pane 에서 떨어진다(vendor/portable-pty psuedocon.rs 제약).

지키는 것
  ① 팩 전체(tests 제외) 캡처 호출 중 숨김 누락 0
  ② `**NOWIN` 을 쓰는 파일은 NOWIN 을 정본 모양으로 정의한다
  ③ 계수 하한 — 스캐너가 대상에 닿았는가(공허 통과 차단)
  ④ 셀프테스트 — 누락 검체 적색 · 정상 검체 초록 · 스트리밍 호출은 제외 · 틀린 정의는 불인정

사거리(정직): `subprocess.<fn>` 으로 부르는 호출만 본다. `from subprocess import run` 별칭·os.system·
  asyncio 스폰은 못 본다(현재 팩 0건은 아래 ⑤가 센다). 윈도우에서 창이 실제로 안 뜨는지는 재지 않는다.

실행: python3 test_nowin_captured_spawns.py   (unittest·파일 직접 실행 — 저장소 관례 준거)
"""
import ast
import glob
import os
import unittest

SELF = os.path.dirname(os.path.abspath(__file__))                        # …/bin/tests
PACK = os.path.dirname(os.path.dirname(SELF))                            # cysjavis-pack
SPAWNS = ("run", "Popen", "check_output", "call", "check_call")
DEF = 'NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}'


def _kw(call, name):
    for k in call.keywords:
        if k.arg == name:
            return k.value
    return None


def _captured(call):
    if call.func.attr == "check_output":
        return True
    v = _kw(call, "capture_output")
    if isinstance(v, ast.Constant) and v.value is True:
        return True
    so = _kw(call, "stdout")
    return so is not None and not (isinstance(so, ast.Constant) and so.value is None)


def _hidden(call):
    return any((k.arg is None and isinstance(k.value, ast.Name) and k.value.id == "NOWIN")
               or k.arg in ("creationflags", "startupinfo") for k in call.keywords)


def scan(src):
    """(captured_count, missing_linenos, uses_nowin_without_def, alias_imports) — 순수 함수."""
    tree = ast.parse(src)
    captured, missing = 0, []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"
                and n.func.attr in SPAWNS and _captured(n)):
            captured += 1
            if not _hidden(n):
                missing.append(n.lineno)
    undefined = "**NOWIN" in src and not any(l.strip() == DEF for l in src.splitlines())
    aliases = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "subprocess")
    return captured, missing, undefined, aliases


def pack_files():
    out = []
    for f in sorted(glob.glob(os.path.join(PACK, "**", "*.py"), recursive=True)):
        rel = os.path.relpath(f, PACK)
        if "/tests/" in "/" + rel or os.path.basename(f).startswith("test_"):
            continue
        out.append((rel, f))
    return out


class NowinCapturedSpawns(unittest.TestCase):
    def test_every_captured_spawn_hides_its_window(self):
        total, files = 0, 0
        for rel, path in pack_files():
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            try:
                captured, missing, undefined, _ = scan(src)
            except SyntaxError:
                continue  # 팩에 동봉된 비-파이썬3 조각은 대상 밖(현재 0건이어야 정상 — 아래 하한이 센다)
            files += 1
            with self.subTest(file=rel):
                self.assertEqual(missing, [], "%s: 캡처 호출에 **NOWIN 없음(줄 %s) — 윈도에서 콘솔 창이 뜬다"
                                 % (rel, missing))
                self.assertFalse(undefined, "%s: **NOWIN 을 쓰는데 정본 정의가 없다" % rel)
            total += captured
        # 계수 하한(2026-09-15 실측: 캡처 호출 213 · 파일 수백) — 스캐너 파손·대상 축소 감지.
        self.assertGreaterEqual(files, 100, "스캔 파일 %d — 수집기 파손 의심" % files)
        self.assertGreaterEqual(total, 200, "캡처 호출 계수 %d — 대상 축소·스캐너 파손 의심" % total)

    def test_no_from_subprocess_import_alias_in_pack(self):
        # ⑤ 사거리 밖 경로가 생기면 적색 — `from subprocess import run` 은 이 스캐너가 못 본다.
        found = []
        for rel, path in pack_files():
            with open(path, encoding="utf-8") as fh:
                try:
                    if scan(fh.read())[3]:
                        found.append(rel)
                except SyntaxError:
                    pass
        self.assertEqual(found, [], "from subprocess import … 사용 파일: %s" % found)

    def test_selftest_scanner(self):
        good = ('import os, subprocess\n' + DEF + '\n'
                'subprocess.run(["cys", "status"], capture_output=True, **NOWIN)\n'
                'subprocess.run(["cys", "run", "--", "x"])\n')          # 스트리밍 = 제외
        self.assertEqual(scan(good)[:3], (1, [], False))
        miss = good + 'subprocess.check_output(["powershell", "-Command", "Get-Acl"])\n'
        self.assertEqual(scan(miss)[1], [5])
        piped = good + 'subprocess.Popen(["cmd", "/C", "x"], stdout=subprocess.PIPE)\n'
        self.assertEqual(scan(piped)[1], [5])
        explicit = good + 'subprocess.run(["x"], capture_output=True, creationflags=0x08000000)\n'
        self.assertEqual(scan(explicit)[1], [])
        no_def = good.replace(DEF, 'NOWIN = {}')
        self.assertTrue(scan(no_def)[2], "틀린 정의를 인정했다")
        other = good.replace("**NOWIN", "**OTHER")
        self.assertEqual(scan(other)[1], [3], "다른 이름 전개를 숨김으로 인정했다")
        alias = good + 'from subprocess import run\n'
        self.assertEqual(scan(alias)[3], 1)


if __name__ == "__main__":
    unittest.main()
