#!/usr/bin/env python3
"""test_preflight_fresh_full_json — ★1.1.8 윈 CI 회귀(windows-build run 37366770227 · T3-c03 · master#53919d55).

증상: 신선 팩(`~/.cys/pack`)에서 `javis_preflight.py --safe --json` 이 C03.pin.master/worker/cso/reviewer/ceo 를 **하나도**
안 냈다(「미발화」). 원인: D14(fda3906f)가 C61 에서 SESSION_STATE 줄과 함께 상대 경로 해석 루트 `root` 대입까지 지워,
경로형 상대 토큰 하나에 NameError → preflight 전체가 JSON 없이 죽음. 단위 시험은 검사를 낱개로 불러 이 길을 못 밟았다 —
여기서는 CI 와 같은 꼴(신선 HOME 의 ~/.cys/pack · --safe --json 전수)로 **전체 실행**을 핀한다.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PACK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NEED = ("C03.pin.master", "C03.pin.worker", "C03.pin.cso", "C03.pin.reviewer", "C03.pin.ceo")


class T(unittest.TestCase):
    def test_fresh_pack_full_run_emits_json_and_c03(self):
        home = tempfile.mkdtemp(prefix="pf-fresh-")
        self.addCleanup(shutil.rmtree, home, True)
        dst = os.path.join(home, ".cys", "pack")
        shutil.copytree(PACK, dst, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
        env = {"PATH": "/usr/bin:/bin", "HOME": home, "TMPDIR": home, "LANG": "en_US.UTF-8"}
        r = subprocess.run([sys.executable, os.path.join(dst, "bin", "javis_preflight.py"), "--safe", "--json"],
                           capture_output=True, text=True, encoding="utf-8", env=env, cwd=home, timeout=900,
                           stdin=subprocess.DEVNULL)
        self.assertNotIn("Traceback", r.stderr, "preflight 전체 실행이 예외로 죽었다(JSON 없음 = C03 등 전 검사 미발화)\n"
                         + r.stderr[-1500:])
        doc = json.loads(r.stdout)
        ids = {c["id"]: c["status"] for c in doc["checks"]}
        self.assertIn("C61.doc-code-sot", ids, "C61 이 결과에 없다")
        for cid in NEED:
            self.assertEqual(ids.get(cid), "PASS", "%s = %s(신선 팩 CI T3-c03 계약)" % (cid, ids.get(cid, "미발화")))


if __name__ == "__main__":
    unittest.main()
