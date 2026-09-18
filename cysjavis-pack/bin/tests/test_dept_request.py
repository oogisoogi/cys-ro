#!/usr/bin/env python3
"""test_dept_request.py — javis_dept_request.py 계약 시험 (A1-2 · 적대 2R 치명 3 + 수정 11).

격리: 매 시험이 임시 HOME 을 세우고 가짜 cys·cys-dept·cysd·org 를 PATH/env 로 주입한다.
실 자원 무접촉을 시험 스스로 단언한다(TestNoProduction). 뮤턴트 하네스(mut_dept_request.py)는
DEPT_REQUEST_MODULE 로 변이 사본을 가리키고 이 파일을 그대로 돌린다.
"""
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BIN not in sys.path:
    sys.path.insert(0, BIN)
MOD_PATH = os.environ.get("DEPT_REQUEST_MODULE") or os.path.join(BIN, "javis_dept_request.py")
REAL_HOME = os.path.expanduser("~")
REAL_ROOT = os.path.join(REAL_HOME, ".cys", "dept-requests")


def load_mod():
    spec = importlib.util.spec_from_file_location("javis_dept_request_ut", MOD_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FAKE_CYS = r'''#!/usr/bin/env python3
import json, os, sys
argv = sys.argv[1:]
home = os.environ["HOME"]
log = os.path.join(home, "fake-cys.log")
with open(log, "a") as f:
    f.write(json.dumps(argv, ensure_ascii=False) + "\n")
sock = None
if "--socket" in argv:
    i = argv.index("--socket"); sock = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
cmd = argv[0] if argv else ""
if cmd == "status":
    alive = json.load(open(os.path.join(home, "fake-alive.json"))) if os.path.exists(os.path.join(home, "fake-alive.json")) else {}
    if sock in alive:
        print(json.dumps({"surfaces": alive[sock]})); sys.exit(0)
    sys.exit(1)
if cmd == "send":
    sys.exit(int(os.environ.get("FAKE_SEND_RC", "0")))
if cmd == "tombstone":
    p = os.path.join(os.environ["CYS_BASE_STATE_DIR"], "dept_tombstones.json")
    d = json.load(open(p)) if os.path.exists(p) else {"dept_tombstones": []}
    name = argv[-1]
    s = set(d["dept_tombstones"])
    if os.environ.get("FAKE_TOMB_REMOVE_FAIL") == "1" and "--remove" in argv:
        sys.exit(1)
    (s.discard if "--remove" in argv else s.add)(name)
    json.dump({"dept_tombstones": sorted(s)}, open(p, "w")); sys.exit(0)
sys.exit(0)
'''

FAKE_CYS_DEPT = r'''#!/usr/bin/env python3
import json, os, sys, time
home = os.environ["HOME"]
cmd, arg = sys.argv[1], sys.argv[2]
with open(os.path.join(home, "fake-cys-dept.log"), "a") as f:
    f.write(json.dumps([cmd, arg, os.environ.get("CYS_ROLE"), os.getsid(0) if hasattr(os, "getsid") else 0,
                        os.environ.get("PATH", "").split(os.pathsep)[0]]) + "\n")
reg_p = os.environ["CYS_DEPTS_JSON"]
if cmd == "create":
    time.sleep(float(os.environ.get("FAKE_CREATE_SLEEP", "0")))
    rc = int(os.environ.get("FAKE_CREATE_RC", "0"))
    if rc:
        sys.exit(rc)
    cat = json.load(open(os.environ["CYS_DEPT_CATALOG"]))
    dep = cat["departments"][arg]
    reg = json.load(open(reg_p)) if os.path.exists(reg_p) else {"depts": {}}
    for n, e in reg["depts"].items():
        if e.get("mission_key") == arg:
            print(n); sys.exit(0)
    n = 1
    while "dept-%d" % n in reg["depts"]:
        n += 1
    name = "dept-%d" % n
    reg["depts"][name] = {"socket": os.path.join(home, ".local/state/cys-dept-%s/cys.sock" % name),
                          "mission_key": arg, "display_name": dep["display"], "cwd": dep["cwd"]}
    json.dump(reg, open(reg_p, "w"))
    print("[cys-dept] create 완료", file=sys.stderr)
    print(name); sys.exit(0)
if cmd == "down":
    reg = json.load(open(reg_p)); reg["depts"].pop(arg, None); json.dump(reg, open(reg_p, "w")); sys.exit(0)
sys.exit(0)
'''

FAKE_ORG = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
assert a[0] == "destroy" and os.environ.get("CYS_ROLE") == "cso"
assert "--purge-workdir" not in a
name = a[a.index("--dept") + 1]
reg_p = os.environ["CYS_DEPTS_JSON"]
reg = json.load(open(reg_p)); reg["depts"].pop(name, None); json.dump(reg, open(reg_p, "w"))
p = os.path.join(os.environ["CYS_BASE_STATE_DIR"], "dept_tombstones.json")
d = json.load(open(p)) if os.path.exists(p) else {"dept_tombstones": []}
d["dept_tombstones"] = sorted(set(d["dept_tombstones"]) | {name}); json.dump(d, open(p, "w"))
with open(os.path.join(os.environ["HOME"], "fake-org.log"), "a") as f:
    f.write(json.dumps(a) + "\n")
'''


def _exe(path, text):
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="deptreq-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, "Desktop"))
        self.fbin = os.path.join(self.tmp, "fbin")
        os.makedirs(self.fbin)
        _exe(os.path.join(self.fbin, "cys"), FAKE_CYS)
        _exe(os.path.join(self.fbin, "cys-dept"), FAKE_CYS_DEPT)
        _exe(os.path.join(self.fbin, "cysd"), "#!/bin/sh\nexit 0\n")
        _exe(os.path.join(self.fbin, "org"), FAKE_ORG)
        self.saved = dict(os.environ)
        base_state = os.path.join(self.home, ".local", "state", "cys")
        os.makedirs(base_state)
        acct = os.path.join(self.home, ".cys", "claude")
        os.makedirs(acct)
        env = {
            "HOME": self.home, "PATH": self.fbin + os.pathsep + "/usr/bin:/bin",
            "CYS_BIN": os.path.join(self.fbin, "cys"),
            "CYS_DEPT_BIN": os.path.join(self.fbin, "cys-dept"),
            "CYS_DEPT_ORG_BIN": os.path.join(self.fbin, "org"),
            "CYS_BASE_STATE_DIR": base_state,
            "CYS_DEPT_GATE_OVERRIDE": json.dumps({"verdict": "allow", "measured": {"nodes": 4}}),
            "CYS_DEPTS_JSON": os.path.join(self.home, ".cys", "depts.json"),
            "CYS_DEPT_CATALOG": os.path.join(self.home, ".cys", "dept-catalog.json"),
            "CYS_DEPT_MISSIONS": os.path.join(self.home, ".cys", "dept-missions"),
            "CYS_STATE_DIR": os.path.join(self.home, ".cys", "state"),
            "CYS_SOCKET": os.path.join(base_state, "cys.sock"),
            "CYS_DEPT_CREATE_WAIT_SEC": "20",
        }
        for k in list(os.environ):
            if k.startswith("CYS_") or k.startswith("FAKE_"):
                del os.environ[k]
        os.environ.update(env)
        with open(env["CYS_DEPTS_JSON"], "w") as f:
            json.dump({"depts": {}}, f)
        self.m = load_mod()
        self.m._TEST_HOOK_BEFORE_FINALIZE = None
        self.body = os.path.join(self.tmp, "body.md")
        with open(self.body, "w") as f:
            f.write("## 처음 할 일\n- 본문 연구 자료 목록을 만든다\n## 이 부서의 규칙\n- 오너 말을 따른다\n")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.saved)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers
    def run_cmd(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.m.main(list(argv))
        txt = buf.getvalue()
        try:
            return rc, json.loads(txt) if txt.strip() else {}
        except ValueError:
            return rc, {"raw": txt}

    def tick(self):
        os.environ["CYS_ROLE"] = "cso"
        try:
            return self.run_cmd("tick")[0]
        finally:
            os.environ.pop("CYS_ROLE", None)

    def propose(self, name="설교준비부", first=None):
        args = ["propose", "--name", name, "--mission", "주일 설교 준비를 돕습니다", "--claude-md-file", self.body]
        if first:
            args += ["--first-task", first]
        return self.run_cmd(*args)

    def proposed_confirmed(self, name="설교준비부", first=None):
        rc, o = self.propose(name, first)
        self.assertEqual(rc, 0, o)
        rc2, o2 = self.run_cmd("confirm", o["request"])
        self.assertEqual(rc2, 0, o2)
        return o["request"]

    def req(self, rid):
        return self.m.load_req(rid)

    def reg(self):
        return json.load(open(os.environ["CYS_DEPTS_JSON"]))["depts"]

    def set_alive(self, name, surfaces=None):
        p = os.path.join(self.home, "fake-alive.json")
        d = json.load(open(p)) if os.path.exists(p) else {}
        sock = self.reg()[name]["socket"]
        d[sock] = surfaces if surfaces is not None else [{"role": "master", "gate_pending": None}]
        json.dump(d, open(p, "w"))

    def set_formation(self, name, state="complete"):
        import javis_formation as jf
        sock = self.reg()[name]["socket"]
        fd = os.path.join(os.environ["CYS_STATE_DIR"], "formation")
        os.makedirs(fd, exist_ok=True)
        json.dump({"state": state, "socket": sock}, open(os.path.join(fd, jf._sanitize_key(sock) + ".json"), "w"))

    def cys_log(self):
        p = os.path.join(self.home, "fake-cys.log")
        return [json.loads(l) for l in open(p)] if os.path.exists(p) else []

    def pending_exists(self):
        return os.path.exists(os.path.join(self.m.root_dir(), ".pending"))


class TestHappyPath(Base):
    def test_propose_confirm_tick_creates(self):
        rid = self.proposed_confirmed(first="이번 주 본문 자료 모으기")
        self.assertTrue(self.pending_exists(), "confirm 은 표지를 만든다")
        self.assertEqual(self.tick(), 0)
        r = self.req(rid)
        self.assertEqual(r["state"], "created", r.get("events"))
        self.assertEqual(r["dept_name"], "dept-1")
        cat = json.load(open(os.environ["CYS_DEPT_CATALOG"]))
        self.assertEqual(cat["departments"][r["key"]]["account"], "shared")
        self.assertIn("shared", cat["accounts"], "공유 계정 시드")
        self.assertEqual(r.get("account_seeded"), "shared", "A-7: 시드 사실 기록")
        md = open(os.path.join(r["cwd"], "CLAUDE.md"), encoding="utf-8").read()
        self.assertTrue(md.startswith("<!-- cys-dept-mission request=%s sha256=" % rid))
        self.assertEqual(md, open(os.path.join(self.m.req_dir(rid), "claude_md.txt"), encoding="utf-8").read(),
                         "카드에서 확인받은 바이트 그대로")
        # 결과 알림 1회 · --queued · Return(send-key) 없음
        sends = [a for a in self.cys_log() if a and a[0] == "send"]
        self.assertEqual(len([a for a in sends if "[부서결과] %s" % rid in a]), 1)
        self.assertTrue(all("--queued" in a for a in sends))
        self.assertFalse([a for a in self.cys_log() if a and a[0] == "send-key"], "큐 배달엔 Return 금지")
        # 생성 호출은 CSO 신원 · 새 세션(V-DETACH) · cysd 폴더가 PATH 선두(V-PATH)
        rows = [json.loads(l) for l in open(os.path.join(self.home, "fake-cys-dept.log"))]
        cr = [x for x in rows if x[0] == "create"][0]
        self.assertEqual(cr[2], "cso")
        self.assertNotEqual(cr[3], os.getsid(0), "create 는 틱 세션에서 분리돼야 한다(start_new_session)")
        self.assertEqual(cr[4], self.fbin, "cysd 폴더가 자식 PATH 선두")

    def test_running_notified_once_then_pending_cleared(self):
        rid = self.proposed_confirmed()
        self.tick()
        self.assertTrue(self.pending_exists(), "가동 전에는 표지 유지")
        self.set_alive("dept-1")
        self.set_formation("dept-1")
        self.tick()
        self.tick()
        runs = [a for a in self.cys_log() if a and a[0] == "send" and "[부서가동] %s" % rid in a]
        self.assertEqual(len(runs), 1, "가동 알림은 1회")
        self.assertFalse(self.pending_exists(), "진행 중 0 이면 표지 없음")
        rc, o = self.run_cmd("status", "--say", rid)
        self.assertEqual(o["row"], 12)

    def test_notify_is_once_per_state(self):
        """알림 1회 보장은 호출부 조건과 별개로 _notify 자체의 계약이다(호출부 조건이 층 방어라 따로 잰다)."""
        rid = self.proposed_confirmed()
        r = self.req(rid)
        self.m._notify(r, "부서결과")
        self.m._notify(r, "부서결과")
        sends = [a for a in self.cys_log() if a and a[0] == "send" and "[부서결과] %s" % rid in a]
        self.assertEqual(len(sends), 1, "같은 상태의 같은 알림은 1회")
        r["state"] = "failed"
        self.m._notify(r, "부서결과")
        sends = [a for a in self.cys_log() if a and a[0] == "send" and "[부서결과] %s" % rid in a]
        self.assertEqual(len(sends), 2, "상태가 바뀌면 다시 1회")

    def test_kickoff_once_queued_to_dept_socket(self):
        rid = self.proposed_confirmed(first="본문 자료 모으기")
        self.tick()
        rc, o = self.run_cmd("kickoff", rid)
        self.assertEqual(rc, 7, "가동 전 kickoff 거부")
        self.set_alive("dept-1")
        self.set_formation("dept-1")
        rc, o = self.run_cmd("kickoff", rid)
        self.assertEqual(rc, 0, o)
        sent = [a for a in self.cys_log() if "send" in a and any("[부서시작 %s]" % rid in x for x in a)]
        self.assertEqual(len(sent), 1)
        a = sent[0]
        self.assertEqual(a[a.index("--socket") + 1], self.reg()["dept-1"]["socket"])
        self.assertIn("--queued", a)
        r = self.req(rid)
        self.assertIn(r["claude_md_marker_sha"][:12], a[-1])
        md = open(os.path.join(r["cwd"], "CLAUDE.md"), encoding="utf-8").readline()
        self.assertIn(r["claude_md_marker_sha"], md, "부서장이 대조할 표식과 같은 값")
        self.assertEqual(self.run_cmd("kickoff", rid)[0], 7, "요청당 1회")


class TestCritical1LostUpdate(Base):
    def test_confirm_between_scan_and_finalize_survives(self):
        """2R ①: 틱이 「진행 중 0」을 계산한 뒤 confirm 이 끼어들면 그 표지가 살아남아야 한다."""
        rc, o = self.propose()
        rid = o["request"]
        m = self.m

        def interleave():
            with redirect_stdout(io.StringIO()):
                m.main(["confirm", rid])
        m._TEST_HOOK_BEFORE_FINALIZE = interleave
        m._SELF_HEAL = False           # 두 벨트를 갈라 잰다 — 자가복구가 이 경합을 가리지 않게
        self.assertEqual(self.tick(), 0)
        m._TEST_HOOK_BEFORE_FINALIZE = None
        self.assertEqual(self.req(rid)["state"], "confirmed")
        self.assertTrue(self.pending_exists(), "lost-update: 틱이 방금 만든 표지를 지웠다")

    def test_self_heal_restores_lost_marker(self):
        rid = self.proposed_confirmed()
        os.remove(os.path.join(self.m.root_dir(), ".pending"))
        self.m._SELF_HEAL = True
        os.environ["CYS_DEPT_CREATE_GAP_SEC"] = "100000"
        self.m.atomic_write_json(self.m.tick_state_path(), {"last_create_at": time.time()})
        self.tick()
        self.assertTrue(self.pending_exists(), "자가복구 벨트: 진행 중 요청이 있으면 표지를 다시 세운다")


class TestCritical2SweepUngated(Base):
    def test_sweep_runs_without_marker(self):
        """2R ②: 표지가 없어도 만료·개인정보 수명·고아 청소가 돈다."""
        rid = self.proposed_confirmed()
        os.remove(os.path.join(self.m.root_dir(), ".pending"))
        r = self.req(rid)
        r["confirmed_at"] = time.time() - 3600
        self.m.save_req(r)
        # 8일 된 superseded 제안의 발화 원문
        rc, o = self.propose("다른부서")
        old = self.req(o["request"])
        old["state"] = "superseded"
        self.m.atomic_write_text(os.path.join(self.m.req_dir(old["id"]), "utterance.txt"), "발화 원문")
        self.m.save_req(old)
        rj = os.path.join(self.m.req_dir(old["id"]), "request.json")
        d = json.load(open(rj)); d["updated_at"] = time.time() - 8 * 86400; json.dump(d, open(rj, "w"))
        self.m._SELF_HEAL = False
        self.tick()
        self.assertEqual(self.req(rid)["state"], "expired", "만료가 게이트 뒤에 갇혔다")
        self.assertFalse(os.path.exists(os.path.join(self.m.req_dir(old["id"]), "utterance.txt")),
                         "개인정보 7일 삭제가 게이트 뒤에 갇혔다")
        sends = [a for a in self.cys_log() if a and a[0] == "send" and "[부서결과] %s" % rid in a]
        self.assertEqual(len(sends), 1, "만료도 결과 알림 1회")


class TestCritical3Tombstone(Base):
    def test_reused_number_with_residue_is_running_not_closed(self):
        rid = self.proposed_confirmed()
        os.environ["FAKE_TOMB_REMOVE_FAIL"] = "1"
        tp = os.path.join(os.environ["CYS_BASE_STATE_DIR"], "dept_tombstones.json")
        json.dump({"dept_tombstones": ["dept-1"]}, open(tp, "w"))    # 닫았던 같은 번호의 묘비
        self.tick()
        r = self.req(rid)
        self.assertEqual(r["state"], "created")
        self.assertEqual(r.get("tombstone_retry"), "residue", "해소 재시도 1회의 결과가 기록된다")
        self.set_alive("dept-1")
        self.set_formation("dept-1")
        rc, o = self.run_cmd("status", "--say", rid)
        self.assertEqual(o["row"], 12, "묘비 잔존이라고 가동 중 부서를 닫힘으로 말하면 안 된다: %s" % o)
        self.assertTrue(o.get("tombstone_residue"), "잔존은 결정론 칸으로 표기")

    def test_retry_resolves_residue(self):
        rid = self.proposed_confirmed()
        tp = os.path.join(os.environ["CYS_BASE_STATE_DIR"], "dept_tombstones.json")
        json.dump({"dept_tombstones": ["dept-1"]}, open(tp, "w"))
        self.tick()
        self.assertEqual(self.req(rid).get("tombstone_retry"), "resolved")
        self.assertNotIn("dept-1", json.load(open(tp))["dept_tombstones"])


class TestChainCaps(Base):
    def test_one_create_per_tick_and_gap(self):
        a = self.proposed_confirmed("가부서")
        # 두 번째 제안은 첫 번째를 superseded 로 만들기 전에 확인된 뒤이므로 둘 다 confirmed
        b = self.proposed_confirmed("나부서")
        os.environ["CYS_DEPT_CHAT_CAP"] = "5"
        self.tick()
        states = sorted([self.req(a)["state"], self.req(b)["state"]])
        self.assertEqual(states, ["confirmed", "created"], "한 틱에 생성 1건")
        self.tick()
        states = sorted([self.req(a)["state"], self.req(b)["state"]])
        self.assertEqual(states, ["confirmed", "created"], "간격 10분 전에는 두 번째를 만들지 않는다")
        waiting = [x for x in (self.req(a), self.req(b)) if x["state"] == "confirmed"][0]
        rc, o = self.run_cmd("status", "--say", waiting["id"])
        self.assertIn("10분", o["say"])

    def test_one_per_tick_even_without_gap(self):
        a = self.proposed_confirmed("가부서")
        b = self.proposed_confirmed("나부서")
        os.environ["CYS_DEPT_CHAT_CAP"] = "5"
        os.environ["CYS_DEPT_CREATE_GAP_SEC"] = "0"
        self.tick()
        states = sorted([self.req(a)["state"], self.req(b)["state"]])
        self.assertEqual(states, ["confirmed", "created"], "간격이 0 이어도 한 틱에 생성 1건")

    def test_cap_reached_at_tick_fails(self):
        rid = self.proposed_confirmed()
        reg = {"depts": {"dept-1": {"socket": "/x/cys-dept-dept-1/cys.sock", "mission_key": "zz"},
                         "dept-2": {"socket": "/x/cys-dept-dept-2/cys.sock", "mission_key": "yy"}}}
        json.dump(reg, open(os.environ["CYS_DEPTS_JSON"], "w"))       # 메뉴로 2개가 생겼다
        self.tick()
        r = self.req(rid)
        self.assertEqual(r["state"], "failed")
        self.assertTrue(r["fail_reason"].startswith("cap"))
        self.assertFalse([x for x in open(os.path.join(self.home, "fake-cys-dept.log"))]
                         if os.path.exists(os.path.join(self.home, "fake-cys-dept.log")) else [])

    def test_propose_blocked_at_cap_and_lane(self):
        reg = {"depts": {"dept-1": {"socket": "/x/cys-dept-dept-1/cys.sock"},
                         "dept-2": {"socket": "/x/cys-dept-dept-2/cys.sock"}}}
        json.dump(reg, open(os.environ["CYS_DEPTS_JSON"], "w"))
        rc, o = self.propose()
        self.assertEqual(rc, 5)
        self.assertIn("메뉴로 만드신 부서 포함", o["say"])
        json.dump({"depts": {}}, open(os.environ["CYS_DEPTS_JSON"], "w"))
        os.environ["CYS_SOCKET"] = os.path.join(self.home, ".local/state/cys-dept-dept-1/cys.sock")
        rc, o = self.propose()
        self.assertEqual(rc, 5)
        self.assertIn("본부", o["say"])


class TestOrphanLedgers(Base):
    def _ledger(self, sock):
        import javis_formation as jf
        fd = os.path.join(os.environ["CYS_STATE_DIR"], "formation")
        os.makedirs(fd, exist_ok=True)
        p = os.path.join(fd, jf._sanitize_key(sock) + ".json")
        json.dump({"state": "partial:x", "socket": sock}, open(p, "w"))
        return p

    def test_cleanup_moves_only_dead_dept_ledgers(self):
        base = self._ledger("")
        s1 = os.path.join(self.home, ".local/state/cys-dept-dept-1/cys.sock")
        s2 = os.path.join(self.home, ".local/state/cys-dept-dept-2/cys.sock")
        json.dump({"depts": {"dept-1": {"socket": s1, "mission_key": "k1"}}}, open(os.environ["CYS_DEPTS_JSON"], "w"))
        l1, l2 = self._ledger(s1), self._ledger(s2)
        bs = self._ledger(os.path.join(os.environ["CYS_BASE_STATE_DIR"], "cys.sock"))
        self.tick()                                    # 표지 없음 — 청소는 매 틱 무조건
        self.assertTrue(os.path.exists(base), "본부 원장(base) 절대 제외")
        self.assertTrue(os.path.exists(bs), "본부 소켓 원장 절대 제외")
        self.assertTrue(os.path.exists(l1), "살아 있는 부서 원장 보존")
        self.assertFalse(os.path.exists(l2), "죽은 부서 원장 → 휴지통")
        moved = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(self.home, ".local/state/cys-trash"))
                 for f in fs]
        self.assertEqual(len(moved), 1, "삭제가 아니라 이동")

    def test_long_socket_key_truncation_branch(self):
        longname = "dept-9"
        deep = os.path.join(self.home, "x" * 130, ".local/state/cys-dept-%s/cys.sock" % longname)
        p = self._ledger(deep)
        self.assertLessEqual(len(os.path.basename(p)), 130, "120자 절단 분기 사용")
        self.tick()
        self.assertFalse(os.path.exists(p), "절단 키도 socket 필드 재산출로 판별")


class TestCreateTimeout(Base):
    def test_no_recall_while_first_child_alive(self):
        rid = self.proposed_confirmed()
        os.environ["CYS_DEPT_CREATE_WAIT_SEC"] = "1"
        os.environ["FAKE_CREATE_SLEEP"] = "6"
        self.tick()
        r = self.req(rid)
        self.assertEqual(r["state"], "create-timeout")
        self.tick()
        r = self.req(rid)
        self.assertEqual(r.get("create_calls"), 1, "첫 자식 생존 중 재호출 금지(2R ⑦)")
        time.sleep(6.5)
        os.environ["FAKE_CREATE_SLEEP"] = "0"
        self.tick()
        r = self.req(rid)
        self.assertEqual(r["state"], "created", r.get("events"))
        self.assertEqual(r.get("create_calls"), 1, "첫 자식이 등재했으면 재호출 없이 판정")


class TestMissionDelivery(Base):
    def test_user_claude_md_is_never_overwritten(self):
        rid = self.proposed_confirmed()
        r = self.req(rid)
        os.makedirs(r["cwd"], exist_ok=True)
        with open(os.path.join(r["cwd"], "CLAUDE.md"), "w") as f:
            f.write("사용자 자신의 파일\n")
        self.tick()
        r = self.req(rid)
        self.assertEqual(r["state"], "failed")
        self.assertEqual(r["fail_reason"], "claude_md_conflict")
        self.assertEqual(open(os.path.join(r["cwd"], "CLAUDE.md")).read(), "사용자 자신의 파일\n")
        rc, o = self.run_cmd("status", "--say", rid)
        self.assertIn("CLAUDE.md", o["say"])

    def test_tampered_claude_md_after_confirm_fails(self):
        rid = self.proposed_confirmed()
        with open(os.path.join(self.m.req_dir(rid), "claude_md.txt"), "a") as f:
            f.write("몰래 덧붙인 지시\n")
        self.tick()
        self.assertEqual(self.req(rid)["fail_reason"], "claude_md_changed")


class TestProposalRules(Base):
    def test_duplicate_and_superseded(self):
        rc, o1 = self.propose("가부서")
        rc, o2 = self.propose("나부서")
        self.assertEqual(self.req(o1["request"])["state"], "superseded", "열린 제안은 1장")
        rc, o = self.run_cmd("confirm", o1["request"])
        self.assertEqual(rc, 6)
        self.assertIn("새 제안", o["say"])
        self.run_cmd("confirm", o2["request"])
        self.tick()
        rc, o = self.propose("나부서")
        self.assertEqual(rc, 5)
        self.assertIn("이미", o["say"])

    def test_card_login_line_follows_primary_account(self):
        rc, o = self.propose()
        self.assertIn("따로 로그인하지 않습니다", o["card"])
        os.environ["CYS_PRIMARY_ACCOUNT"] = "shared"
        rc, o = self.propose("둘째부서")
        self.assertIn("로그인을 한 번", o["card"], "2R ④: primary 키 충돌 시 카드 문장 자동 전환")

    def test_card_has_no_internal_terms(self):
        rc, o = self.propose()
        card = o["card"]
        import re
        self.assertIsNone(re.search(r"\bdept-\d", card), "카드에 시스템 이름(dept-N)")
        for term in ("mission_key", "catalog", "socket", "tick", "cso", "CYS_", "레지스트리", "묘비"):
            self.assertNotIn(term, card, "카드에 내부 용어: %s" % term)

    def test_tick_requires_cso_identity(self):
        os.environ.pop("CYS_ROLE", None)
        self.assertEqual(self.run_cmd("tick")[0], 3)


class TestClose(Base):
    def test_close_flow_and_ledger_cleanup(self):
        rid = self.proposed_confirmed()
        self.tick()
        self.set_formation("dept-1", "partial:x")
        rc, o = self.run_cmd("propose", "--close", "설교준비부")
        self.assertEqual(rc, 0, o)
        self.assertIn("dept-1", o["card"])
        self.assertIn("닫을까요", o["card"])
        cid = o["request"]
        self.run_cmd("confirm", cid)
        self.tick()
        self.assertEqual(self.req(cid)["state"], "closed")
        self.assertNotIn("dept-1", self.reg())
        fd = os.path.join(os.environ["CYS_STATE_DIR"], "formation")
        self.assertEqual([f for f in os.listdir(fd) if "dept-1" in f], [], "닫기 직후 원장 청소")
        rc, o = self.run_cmd("status", "--say", rid)
        self.assertEqual(o["row"], 5, o)

    def test_close_ambiguous_and_missing(self):
        json.dump({"depts": {"dept-1": {"socket": "/a/cys-dept-dept-1/cys.sock", "display_name": "같은이름"},
                             "dept-2": {"socket": "/a/cys-dept-dept-2/cys.sock", "display_name": "같은이름"}}},
                  open(os.environ["CYS_DEPTS_JSON"], "w"))
        rc, o = self.run_cmd("propose", "--close", "같은이름")
        self.assertEqual(rc, 5)
        self.assertEqual(o["candidates"], ["dept-1", "dept-2"])
        rc, o = self.run_cmd("propose", "--close", "없는부서")
        self.assertEqual(rc, 4)
        self.assertIn("처음 지은 이름", o["say"])


class TestStatusAll(Base):
    def test_menu_created_dept_is_row1(self):
        json.dump({"depts": {"dept-3": {"socket": "/a/cys-dept-dept-3/cys.sock", "display_name": "메뉴부서"}}},
                  open(os.environ["CYS_DEPTS_JSON"], "w"))
        rc, o = self.run_cmd("status", "--all")
        rows = [r for r in o["rows"] if r["dept"] == "dept-3"]
        self.assertEqual(rows[0]["row"], 1)


class TestSelfTest(Base):
    def test_self_test_passes(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.m.self_test()
        self.assertEqual(rc, 0, buf.getvalue()[-2000:])


class TestNoProduction(unittest.TestCase):
    """하네스가 실 자원을 건드리지 않았다는 것을 시험 스스로 단언한다."""
    def test_real_request_root_untouched(self):
        before = os.path.exists(REAL_ROOT) and sorted(os.listdir(REAL_ROOT))
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestHappyPath)
        unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        after = os.path.exists(REAL_ROOT) and sorted(os.listdir(REAL_ROOT))
        self.assertEqual(before, after, "실 ~/.cys/dept-requests 가 시험으로 바뀌었다")


if __name__ == "__main__":
    unittest.main()
