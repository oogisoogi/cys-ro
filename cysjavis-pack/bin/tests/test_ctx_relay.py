#!/usr/bin/env python3
"""test_ctx_relay — v113 A3 좌석 컨텍스트 정지선 중계(javis_ctx_relay) · 가짜 cys 로 격리(라이브 무접촉)."""
import json, os, stat, subprocess, sys, tempfile, time, unittest

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BIN)
import javis_ctx_relay as R

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
h = os.environ["HOME"]
if sys.argv[1:3] == ["status", "--json"]:
    print(open(os.path.join(h, "status.json")).read()); sys.exit(0)
with open(os.path.join(h, "sent.log"), "a") as f: f.write(json.dumps(sys.argv[1:], ensure_ascii=False) + "\n")
'''


def seat(sid, role, pct, age=5, exited=False):
    return {"surface_id": sid, "role": role, "exited": exited,
            "usage": {"ctx_pct": pct, "updated_at": time.time() - age}}


class T(unittest.TestCase):
    def setUp(self):
        self.h = tempfile.mkdtemp()
        cys = os.path.join(self.h, "cys")
        open(cys, "w").write(FAKE)
        os.chmod(cys, 0o755)
        self.env = dict(os.environ, HOME=self.h, CYS_BIN=cys, CYS_STATE_DIR=os.path.join(self.h, "st"),
                        CYS_SOCKET=os.path.join(self.h, "cys-dept-dept-1", "cys.sock"))
        self.env.pop("CYS_CONTEXT_THRESHOLD_PCT", None)

    def tick(self, seats):
        json.dump({"surfaces": seats}, open(os.path.join(self.h, "status.json"), "w"))
        p = subprocess.run([sys.executable, os.path.join(BIN, "javis_ctx_relay.py"), "tick"],
                           env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        lp = os.path.join(self.h, "sent.log")
        return [json.loads(l) for l in open(lp)] if os.path.exists(lp) else []

    def test_crossing_notifies_cso_once_then_rearms(self):
        s = [seat(1, "master", 30), seat(2, "cso", 20), seat(3, "worker", 63)]
        sent = self.tick(s)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][:4], ["send", "--queued", "--to", "cso"])
        self.assertIn("worker@surface:3 컨텍스트 63%", sent[0][4])
        self.assertIn("오너 입력 아님", sent[0][4], "출처 고지가 없으면 CSO 가 오너 입력으로 오독해 보류한다(격리 실측)")
        self.assertIn("cys cycle-agent --surface surface:3", sent[0][4])
        self.assertEqual(len(self.tick(s)), 1, "임계 위 체류 중 재통지")
        s[2] = seat(3, "worker", 12)                     # 순환 뒤 재무장
        self.tick(s)
        s[2] = seat(3, "worker", 61)
        self.assertEqual(len(self.tick(s)), 2, "재무장 뒤 다음 넘김을 못 알렸다")

    def test_skips_cso_stale_and_no_receiver(self):
        self.assertEqual(self.tick([seat(2, "cso", 90), seat(3, "worker", 70, age=3600)]), [],
                         "CSO 자신·낡은 값에 통지했다")
        self.assertEqual(self.tick([seat(3, "worker", 70)]), [], "받을 CSO 가 없는데 보냈다")

    def test_self_report_status_counts_when_fresh(self):
        now = time.time()
        s = {"surface_id": 4, "role": "master", "usage": {"ctx_pct": 20, "updated_at": now - 5},
             "status": {"context_pct": 65, "age_secs": 30}}
        n, _ = R.decide([seat(2, "cso", 1), s], {}, now, 60)
        self.assertEqual(n, [("4", "master", 65, 1)], "신선한 자기보고 65% 를 못 봤다")
        s["status"]["age_secs"] = 3600
        n, _ = R.decide([seat(2, "cso", 1), s], {}, now, 60)
        self.assertEqual(n, [], "낡은 자기보고로 통지했다")
        s.pop("usage")
        s["status"]["age_secs"] = 10
        n, _ = R.decide([seat(2, "cso", 1), s], {}, now, 60)
        self.assertEqual([x[0] for x in n], ["4"], "관측값 없는 좌석의 자기보고를 버렸다")

    def test_master_notice_names_handshake(self):
        t = R.notice_text("master", "2", 65, 60)
        self.assertIn("오너 입력 아님", t)
        self.assertIn("--role master --verifier cso", t, "master 는 self-clear 금지 — 검증자 핸드셰이크를 지시해야 한다")
        self.assertNotIn("--surface surface:2", t)

    def test_decide_threshold_env(self):
        n, _ = R.decide([seat(2, "cso", 1), seat(3, "worker", 55)], {}, time.time(), 50)
        self.assertEqual([x[0] for x in n], ["3"])

    def test_one_reminder_after_quiet_then_silent(self):
        now = time.time()
        seats = [seat(2, "cso", 1), seat(3, "worker", 70)]
        n, st = R.decide(seats, {}, now, 60)
        self.assertEqual([x[3] for x in n], [1])
        n, st = R.decide(seats, st, now + R.REMIND_SEC - 5, 60)
        self.assertEqual(n, [], "재통지 간격 전에 다시 보냈다")
        for s in seats:
            s["usage"]["updated_at"] = now + R.REMIND_SEC
        n, st = R.decide(seats, st, now + R.REMIND_SEC, 60)
        self.assertEqual([x[3] for x in n], [2], "무응답 재통지를 안 보냈다(CSO 가 영원히 기다린다)")
        self.assertIn("무응답 정책", R.notice_text("worker", "3", 70, 60, 2))
        for s in seats:
            s["usage"]["updated_at"] = now + 5 * R.REMIND_SEC
        n, st = R.decide(seats, st, now + 5 * R.REMIND_SEC, 60)
        self.assertEqual(n, [], "넘김당 상한 2통을 넘겼다(폭주)")

    def test_tick_sends_reminder_text(self):
        st = os.path.join(self.env["CYS_STATE_DIR"], "ctx-relay-cys-dept-dept-1.json")
        os.makedirs(os.path.dirname(st), exist_ok=True)
        json.dump({"3": {"at": time.time() - R.REMIND_SEC - 5, "n": 1}}, open(st, "w"))
        sent = self.tick([seat(2, "cso", 1), seat(3, "worker", 70)])
        self.assertEqual(len(sent), 1)
        self.assertIn("무응답 정책", sent[0][4], "틱이 재통지 문구를 싣지 않았다")

    def test_reminder_send_failure_keeps_first_notice_state(self):
        # agy 1R: 재통지 전송 실패 → 상태를 지우지 않고 첫 통지(n=1)로 되돌린다(다음 틱에 재통지만 다시).
        now = time.time()
        st_path = os.path.join(self.env["CYS_STATE_DIR"], "ctx-relay-cys-dept-dept-1.json")
        os.makedirs(os.path.dirname(st_path), exist_ok=True)
        json.dump({"3": {"at": now - R.REMIND_SEC - 5, "n": 1}}, open(st_path, "w"))
        status = json.dumps({"surfaces": [seat(2, "cso", 1), seat(3, "worker", 70)]})
        calls = []

        def fake_run(argv, **kw):
            calls.append(argv[1])
            if argv[1] == "status":
                return subprocess.CompletedProcess(argv, 0, status, "")
            raise OSError("send failed")
        old_env, old_run = dict(os.environ), R.subprocess.run
        os.environ.update(self.env)
        R.subprocess.run = fake_run
        try:
            R.cmd_tick()
        finally:
            R.subprocess.run = old_run
            os.environ.clear()
            os.environ.update(old_env)
        self.assertEqual(calls, ["status", "send"])
        st = json.load(open(st_path))
        self.assertEqual(st["3"]["n"], 1, st)
        self.assertLess(st["3"]["at"], now - R.REMIND_SEC, "첫 통지 시각을 잃었다")

    def test_worker_notice_names_cso_as_verifier(self):
        t = R.notice_text("worker", "6", 66, 60)
        self.assertIn("네가 검증자", t)
        self.assertIn("오너 승인 대상 아님", t)

    def test_legacy_float_state_is_read(self):
        now = time.time()
        n, st = R.decide([seat(2, "cso", 1), seat(3, "worker", 70)], {"3": now - R.REMIND_SEC - 1}, now, 60)
        self.assertEqual([x[3] for x in n], [2], "옛 상태(시각만)를 못 읽었다")


if __name__ == "__main__":
    unittest.main()
