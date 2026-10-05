#!/usr/bin/env python3
"""test_boot_preflight_degraded — ★D7+D8(1.1.8 · 윈 실측 boot-last-._pipe_cys-dept-dept-1.json).

D7: ①preflight detail 이 정확히 2000자 · `[FAIL]` 행 0(꼬리 절단이 앞쪽 FAIL 행을 지웠다) → FAIL 행·판정 줄은 절단에서 뺀다.
D8: preflight NOT READY(FAIL 4)인데 result = ok·completed·exit 0 · [부서가동] 문구에 그 사실 없음 →
    종료 상태값·exit 는 그대로(비치명 계약 · completed_degraded 는 러너 전용 값) · 결과/최종 JSON 에 degraded·preflight 가산 ·
    부서 가동 문구가 그것을 싣는다.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BIN)


def load(name):
    spec = importlib.util.spec_from_file_location(name + "_d8", os.path.join(BIN, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PF_OUT = "\n".join(["[OK] C%02d — %s" % (i, "가" * 60) for i in range(30)]
                   + ["[FAIL] C07 — 디렉티브 핀 어긋남", "[FAIL] C33 — hook 미등록"]
                   + ["[WARN] C%02d — %s" % (i, "나" * 60) for i in range(40, 70)]
                   + ["FAIL 항목을 수리하고 재실행하라. 이 출력 외의 추론으로 READY를 선언하지 마라.",
                      "preflight: NOT READY — FAIL 2 · WARN 30 · 미측정 0 · 검사 84"])


class Boot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = load("javis_bootstrap")

    def test_short_detail_unchanged(self):
        self.assertEqual(self.b._clip_detail("  a\nb  "), "a\nb")

    def test_no_fail_lines_keeps_old_tail(self):
        t = "x" * 5000
        self.assertEqual(self.b._clip_detail(t), t[-2000:])

    def test_fail_rows_survive_truncation(self):
        self.assertGreater(len(PF_OUT), 2000)
        self.assertNotIn("[FAIL]", PF_OUT[-2000:], "고정물이 윈 사건 모양(꼬리에 FAIL 없음)이 아니다")
        d = self.b._clip_detail(PF_OUT)
        self.assertIn("[FAIL] C07 — 디렉티브 핀 어긋남", d)
        self.assertIn("[FAIL] C33 — hook 미등록", d)
        self.assertIn("preflight: NOT READY — FAIL 2", d)
        self.assertTrue(d.endswith(PF_OUT[-2000:]), "종전 꼬리 2000자 보존")

    def test_keep_section_is_capped(self):
        many = "\n".join("[FAIL] C%03d — %s" % (i, "다" * 200) for i in range(200))
        d = self.b._clip_detail(many)
        self.assertLess(len(d), self.b.DETAIL_KEEP_CAP + self.b.DETAIL_TAIL_CAP + 300)

    def test_outcome_not_ready(self):
        st, v, rows = self.b._preflight_outcome(1, PF_OUT)
        self.assertEqual(st, "not_ready")
        self.assertTrue(v.startswith("preflight: NOT READY"))
        self.assertEqual(rows, ["[FAIL] C07 — 디렉티브 핀 어긋남", "[FAIL] C33 — hook 미등록"])

    def test_outcome_without_verdict_is_error(self):
        st, v, rows = self.b._preflight_outcome(124, "")
        self.assertEqual((st, rows), ("error", []))
        self.assertIn("rc=124", v)

    def test_degraded_fields(self):
        self.assertEqual(self.b._degraded_fields({}), {})
        self.assertEqual(self.b._degraded_fields({"preflight_state": "absent"}), {})
        f = self.b._degraded_fields({"preflight_state": "not_ready", "preflight_verdict": "preflight: NOT READY — FAIL 4",
                                     "preflight_fail_rows": ["[FAIL] C1 — x"]})
        self.assertEqual(f["degraded"], ["preflight_not_ready"])
        self.assertEqual(f["preflight"], "preflight: NOT READY — FAIL 4")

    def test_terminal_values_unchanged_and_degraded_on_all_success_paths(self):
        with open(os.path.join(BIN, "javis_bootstrap.py"), encoding="utf-8") as f:
            src = f.read()
        # 호출 줄 불변(골든 생산 호출부 핀) · 러너 전용 값 미사용
        self.assertIn('log.result(ok=True, state="completed", exit=EXIT_OK)', src)
        self.assertNotIn('state="completed_degraded"', src, "러너 전용 값을 파이썬 부트가 내면 파리티가 깨진다")
        # 최종 JSON 세 갈래(완주·결손 0·단독 각성)가 같은 가산을 싣는다
        self.assertEqual(src.count('"boot_last": log.path, **_degraded_fields(log.data)}'), 2)
        self.assertEqual(src.count("summary.update(_degraded_fields(log.data))"), 1)

    def test_log_result_merges_degraded_only_on_ok(self):
        tmp = tempfile.mkdtemp(prefix="d8-log-")
        try:
            lg = self.b._Log.__new__(self.b._Log)
            lg.data = {"preflight_state": "not_ready", "preflight_verdict": "preflight: NOT READY — FAIL 4"}
            lg.surface = "7"
            lg._attributed = lambda d: d
            lg._persist = lambda: None
            lg.result(ok=True, state="completed", exit=0)
            r = lg.data["result"]
            self.assertEqual((r["state"], r["exit"], r["degraded"]), ("completed", 0, ["preflight_not_ready"]))
            lg.result(ok=None, state="declined")
            self.assertNotIn("degraded", lg.data["result"], "완주 아닌 결과에는 싣지 않는다")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Dept(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="d8-")
        self._env = {k: os.environ.get(k) for k in ("CYS_STATE_DIR", "HOME")}
        os.environ["CYS_STATE_DIR"] = os.path.join(self.tmp, "state")
        os.environ["HOME"] = self.tmp
        self.dr = load("javis_dept_request")
        import javis_lane
        self.sock = os.path.join(self.tmp, "dept-1.sock")
        self.reg = {"dept-1": {"socket": self.sock}}
        self.bl = javis_lane.lane_state_path("boot_last", self.sock)
        os.makedirs(os.path.dirname(self.bl), exist_ok=True)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, result):
        with open(self.bl, "w", encoding="utf-8") as f:
            json.dump({"result": result}, f, ensure_ascii=False)

    def test_note_when_degraded(self):
        self.write({"ok": True, "state": "completed", "degraded": ["preflight_not_ready"],
                    "preflight": "preflight: NOT READY — FAIL 4 · WARN 21 · 미측정 0 · 검사 84"})
        n = self.dr.dept_preflight_note("dept-1", self.reg)
        self.assertIn("준비 안 됨(점검 실패 4건)", n)
        x = {"G": True, "D": True, "F": "complete", "P": "closed"}
        s = self.dr.say_for(12, {"display": "시험부"}, "dept-1", x, reg=self.reg)
        self.assertTrue(s.startswith("「시험부」이 가동 중입니다."), s)
        self.assertIn("점검 실패 4건", s)

    def test_no_note_when_clean_or_unreadable(self):
        self.assertEqual(self.dr.dept_preflight_note("dept-1", self.reg), "")      # 파일 없음
        self.write({"ok": True, "state": "completed"})
        self.assertEqual(self.dr.dept_preflight_note("dept-1", self.reg), "")
        with open(self.bl, "w") as f:
            f.write("{깨진")
        self.assertEqual(self.dr.dept_preflight_note("dept-1", self.reg), "")
        self.assertEqual(self.dr.dept_preflight_note(None, self.reg), "")


if __name__ == "__main__":
    unittest.main()
