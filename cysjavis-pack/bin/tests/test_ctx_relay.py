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
        self.assertIn("[ctx-threshold] worker@surface:3 컨텍스트 63%", sent[0][4])
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
        self.assertEqual(n, [("4", "master", 65)], "신선한 자기보고 65% 를 못 봤다")
        s["status"]["age_secs"] = 3600
        n, _ = R.decide([seat(2, "cso", 1), s], {}, now, 60)
        self.assertEqual(n, [], "낡은 자기보고로 통지했다")
        s.pop("usage")
        s["status"]["age_secs"] = 10
        n, _ = R.decide([seat(2, "cso", 1), s], {}, now, 60)
        self.assertEqual([x[0] for x in n], ["4"], "관측값 없는 좌석의 자기보고를 버렸다")

    def test_decide_threshold_env(self):
        n, _ = R.decide([seat(2, "cso", 1), seat(3, "worker", 55)], {}, time.time(), 50)
        self.assertEqual([x[0] for x in n], ["3"])


if __name__ == "__main__":
    unittest.main()
