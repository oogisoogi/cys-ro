#!/usr/bin/env python3
"""test_v115_dept — cysr 1.1.5 트랙 P(팩·부서) 수리(TICKET=v115-dept).

  A2 부서장 좌석 회수 오판(1.1.4 VM 904 §5-②):
     ⓐ 편성·phoenix 가 빈 부서장 좌석을 채운다 — boot_node 는 빈 좌석을 「입양-주입」하지 않고 승계 기동,
        (phoenix 스폰 판정의 빈 좌석 제외 = 트랙 D 906 소유 · master#6e260aed B안 — 이 파일 밖)
     ⓑ --cwd 미지정이면 부서 레지스트리 폴더(dept_registry_cwd — lib.rs 미러) · phoenix master_seat_cwd 3순위
     ⓒ 부팅 유예 안의 빈 좌석 = 회수 금지(_reclaim_verdict hold-grace)
  B8 빈 셸 좌석(에이전트가 붙었다 죽은 좌석) = 유예 뒤 회수-재기동(비승계 역할) · 이벤트 1줄
  A5 CSO·워커 사용자 환경 변경 금지 문안 + 스텁뿐인 맥에서 세션 python3 = 번들(CLAUDE_ENV_FILE)
  B2 참가자 좌석 recap 줄 기본 off(preflight C83 · awaySummaryEnabled 사전 기입 · 사용자 값 존중)
  B3 [DRAIN-VERIFY] 발신 주체 문구 = 「오너의 재시작 조작(앱 재시작 단추 · 새 판 설치)」 — 설치기 드레인 포함
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

SELF = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(SELF)
PACK = os.path.dirname(BIN)
REPO = os.path.dirname(PACK)
sys.path.insert(0, BIN)

import javis_boot_node as bn  # noqa: E402

NOW = 1_800_000_000.0


def _st(role="master", seat="empty", created=NOW - 10, agent=None, extra=None):
    s = {"role": role, "exited": False, "seat": seat, "created_at": created, "agent": agent,
         "surface_ref": "surface:1", "pid": 111}
    s.update(extra or {})
    return {"surfaces": [s]}


class A2GraceAndVerdict(unittest.TestCase):
    def test_grace_only_for_young_empty_seat(self):
        self.assertTrue(bn.seat_in_boot_grace(_st(created=NOW - 10), "master", now=NOW, grace=180))
        self.assertFalse(bn.seat_in_boot_grace(_st(created=NOW - 181), "master", now=NOW, grace=180))
        self.assertFalse(bn.seat_in_boot_grace(_st(seat="occupied"), "master", now=NOW, grace=180))
        # 필드 부재·비수치는 판정으로 융합하지 않는다(단방향)
        self.assertFalse(bn.seat_in_boot_grace(_st(created=None), "master", now=NOW, grace=180))
        self.assertFalse(bn.seat_in_boot_grace(_st(created=True), "master", now=NOW, grace=180))

    def test_grace_env_default_180(self):
        old = os.environ.pop(bn.SEAT_BOOT_GRACE_ENV, None)
        try:
            self.assertEqual(bn.seat_boot_grace_s(), 180.0)
            for bad in ("-5", "abc", ""):
                os.environ[bn.SEAT_BOOT_GRACE_ENV] = bad
                self.assertEqual(bn.seat_boot_grace_s(), 180.0, bad)
            os.environ[bn.SEAT_BOOT_GRACE_ENV] = "30"
            self.assertEqual(bn.seat_boot_grace_s(), 30.0)
        finally:
            os.environ.pop(bn.SEAT_BOOT_GRACE_ENV, None)
            if old is not None:
                os.environ[bn.SEAT_BOOT_GRACE_ENV] = old

    def test_reclaim_verdict_holds_in_grace(self):
        # 904 재현: 부팅 3분차(생성 170초 뒤) 빈 부서장 좌석 — 종전엔 kill 이었다
        st = _st(created=NOW - 170)
        self.assertEqual(bn._reclaim_verdict(st, "master", 111, 111, now=NOW, grace=180), "hold-grace")
        # 유예 뒤에는 종전 판정 그대로(kill)
        st2 = _st(created=NOW - 400)
        self.assertEqual(bn._reclaim_verdict(st2, "master", 111, 111, now=NOW, grace=180), "kill")
        # 순서: 생존이 유예보다 먼저 · 상태 불명이 제일 먼저
        self.assertEqual(bn._reclaim_verdict(None, "master", 111, 111, now=NOW, grace=180), "hold-status")

    def test_empty_seat_action_table(self):
        a = lambda **k: bn.empty_seat_action(_st(**k), k.get("role", "master"), now=NOW, grace=180)  # noqa: E731
        # 한 번도 에이전트가 없던 부서장 빈 셸(allocate) = 편성이 곧장 채운다(유예 무관)
        self.assertEqual(a(role="master", agent=None, created=NOW - 5), "takeover")
        self.assertEqual(a(role="cso", agent=None, created=NOW - 5), "takeover")
        # 에이전트가 붙었다 죽은 좌석(B8) = 유예 안 보류 · 유예 뒤 처분
        self.assertEqual(a(role="master", agent="claude", created=NOW - 5), "hold-grace")
        self.assertEqual(a(role="master", agent="claude", created=NOW - 500), "takeover")
        self.assertEqual(a(role="worker", agent="claude", created=NOW - 5), "hold-grace")
        self.assertEqual(a(role="worker", agent="claude", created=NOW - 500), "reap-launch")
        self.assertEqual(a(role="worker", agent=None, created=NOW - 500), "reap-launch")
        # 비어 있지 않거나 좌석 차원 없음 = 비해당(종전 흐름)
        self.assertIsNone(a(role="master", seat="occupied"))
        self.assertIsNone(a(role="master", seat=None))


class A2DeptRegistryCwd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.d1 = os.path.join(self.tmp, "교육부")
        os.makedirs(self.d1)

    def test_socket_match_name_rule_and_dir_required(self):
        reg = {"depts": {
            "dept-1": {"socket": "/s/one.sock", "cwd": self.d1},
            "dept-2": {"socket": "/s/two.sock", "cwd": "/gone/x"},
            "dept-3": {"cwd": self.d1},
        }}
        f = lambda s: bn.dept_registry_cwd(socket=s, reg=reg)  # noqa: E731
        self.assertEqual(f("/s/one.sock"), self.d1)
        self.assertIsNone(f("/s/two.sock"), "없는 폴더를 좌석 cwd 로")
        self.assertIsNone(f("/s/nope.sock"), "남의 부서 폴더")
        self.assertEqual(f("/h/.local/state/cys-dept-dept-3/cys.sock"), self.d1, "이름 규약 미적용")
        self.assertIsNone(bn.dept_registry_cwd(socket="", reg=reg))

    def test_reads_file_from_env(self):
        p = os.path.join(self.tmp, "depts.json")
        json.dump({"depts": {"dept-1": {"socket": "/s/one.sock", "cwd": self.d1}}}, open(p, "w"))
        old = os.environ.get("CYS_DEPTS_JSON")
        os.environ["CYS_DEPTS_JSON"] = p
        try:
            self.assertEqual(bn.dept_registry_cwd(socket="/s/one.sock"), self.d1)
        finally:
            if old is None:
                os.environ.pop("CYS_DEPTS_JSON", None)
            else:
                os.environ["CYS_DEPTS_JSON"] = old

    def test_phoenix_master_seat_cwd_third_candidate(self):
        import javis_phoenix as ph
        p = os.path.join(self.tmp, "depts.json")
        json.dump({"depts": {"dept-1": {"socket": "/s/one.sock", "cwd": self.d1}}}, open(p, "w"))
        saved = (ph._status_json, os.environ.get("CYS_DEPTS_JSON"))
        home = os.path.expanduser("~")
        # 904 재현: 라이브 master = 홈 빈 셸 · 토폴로지 master = 홈(오판 회수가 덮음)
        ph._status_json = lambda s: {"surfaces": [{"role": "master", "exited": False, "cwd": home}]}
        os.environ["CYS_DEPTS_JSON"] = p
        try:
            self.assertEqual(ph.master_seat_cwd("/s/one.sock", {"master": {"cwd": home}}), self.d1)
            self.assertIsNone(ph.master_seat_cwd("/s/base.sock", {"master": {"cwd": home}}), "본부 소켓에 부서 폴더")
        finally:
            ph._status_json = saved[0]
            if saved[1] is None:
                os.environ.pop("CYS_DEPTS_JSON", None)
            else:
                os.environ["CYS_DEPTS_JSON"] = saved[1]



class _FakeCys:
    """boot_node 의 run() 대역 — cys 명령을 기록하고 좌석 표를 바꾼다(라이브 데몬 무접촉)."""

    def __init__(self, rows):
        self.rows = rows      # [{ref, role, pid, exited, seat, agent, created}]
        self.calls = []
        self.next_id = 50

    def status(self):
        return {"surfaces": [{"surface_ref": r["ref"], "role": r["role"], "pid": r["pid"], "exited": False,
                              "seat": r["seat"], "agent": r["agent"], "created_at": r["created"]}
                             for r in self.rows if r["role"]]}

    def __call__(self, args, timeout=15):
        self.calls.append(list(args))
        a = args[1:]
        if a[:2] == ["status", "--json"]:
            return 0, json.dumps(self.status()), ""
        if a[:1] == ["list"]:
            out = "\n".join("%s\trole=%s\tpid=%s\texited=false" % (r["ref"], r["role"] or "-", r["pid"])
                            for r in self.rows)
            return 0, out, ""
        if a[:1] == ["launch-agent"]:
            role = a[a.index("--role") + 1]
            for r in self.rows:           # 승계: 옛 빈 좌석의 role 이 새 좌석으로
                if r["role"] == role:
                    r["role"] = None
            self.rows.append({"ref": "surface:%d" % self.next_id, "role": role, "pid": 900 + self.next_id,
                              "seat": "occupied", "agent": "claude", "created": time.time()})
            self.next_id += 1
            return 0, "", ""
        if a[:1] == ["close-surface"]:
            self.rows = [r for r in self.rows if r["ref"] != a[1]]
            return 0, "", ""
        return 0, "", ""


class A2B8BootNodeRun(unittest.TestCase):
    def _run(self, rows, role, extra_env=None):
        fake = _FakeCys(rows)
        saved = (bn.run, bn._awaken, time.sleep, sys.argv, dict(os.environ))
        bn.run, bn._awaken = fake, None
        time.sleep = lambda s: None
        sys.argv = ["javis_boot_node.py", "--role", role, "--agent", "claude", "--json", "--timeout", "0.5"]
        os.environ.update(extra_env or {})
        out = []
        import io
        import contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = bn.main()
        finally:
            bn.run, bn._awaken, time.sleep, sys.argv = saved[0], saved[1], saved[2], saved[3]
            os.environ.clear()
            os.environ.update(saved[4])
        out = json.loads(buf.getvalue().strip().splitlines()[-1])
        return rc, out, fake

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dept = os.path.join(self.tmp, "교육부")
        os.makedirs(self.dept)
        self.reg = os.path.join(self.tmp, "depts.json")
        json.dump({"depts": {"dept-1": {"socket": "/s/one.sock", "cwd": self.dept}}}, open(self.reg, "w"))
        self.env = {"CYS_SOCKET": "/s/one.sock", "CYS_DEPTS_JSON": self.reg}

    def test_formation_fills_fresh_master_shell_with_dept_cwd(self):
        # allocate 가 만든 부서장 빈 셸(에이전트 한 번도 없음 · 방금 생성) → 입양-주입이 아니라 승계 기동
        rows = [{"ref": "surface:1", "role": "master", "pid": 111, "seat": "empty", "agent": None,
                 "created": time.time() - 5}]
        rc, out, fake = self._run(rows, "master", self.env)
        launches = [c for c in fake.calls if c[1:2] == ["launch-agent"]]
        self.assertEqual(len(launches), 1, fake.calls)
        self.assertIn("--cwd", launches[0])
        self.assertEqual(launches[0][launches[0].index("--cwd") + 1], self.dept, "부서 폴더가 아니다")
        sends_old = [c for c in fake.calls if c[1:2] == ["send"] and fake.calls.index(c) < fake.calls.index(launches[0])]
        self.assertEqual(sends_old, [], "승계 전에 빈 셸에 주입했다")
        self.assertNotEqual(out.get("surface"), "surface:1", "옛 빈 좌석을 결과 좌석으로 보고")

    def test_dead_agent_seat_in_grace_is_left_alone(self):
        rows = [{"ref": "surface:1", "role": "master", "pid": 111, "seat": "empty", "agent": "claude",
                 "created": time.time() - 30}]
        rc, out, fake = self._run(rows, "master", self.env)
        self.assertEqual(out["result"], "seat_in_grace")
        self.assertEqual(rc, 1)
        acted = [c for c in fake.calls if c[1:2] in (["launch-agent"], ["close-surface"], ["send"])]
        self.assertEqual(acted, [], "유예 안 빈 좌석을 건드렸다")

    def test_b8_worker_dead_shell_after_grace_reaped_then_relaunched(self):
        rows = [{"ref": "surface:3", "role": "worker", "pid": 333, "seat": "empty", "agent": "claude",
                 "created": time.time() - 900}]
        rc, out, fake = self._run(rows, "worker", self.env)
        kinds = [c[1] for c in fake.calls if c[1] in ("close-surface", "launch-agent")]
        self.assertEqual(kinds, ["close-surface", "launch-agent"], fake.calls)
        reap = [c for c in fake.calls if c[1] == "close-surface"][0]
        self.assertEqual(reap[2:], ["surface:3", "--reap"])

    def test_base_socket_keeps_old_default_cwd(self):
        rows = []
        env = {"CYS_SOCKET": "/s/base.sock", "CYS_DEPTS_JSON": self.reg}
        rc, out, fake = self._run(rows, "cso", env)
        launch = [c for c in fake.calls if c[1:2] == ["launch-agent"]][0]
        self.assertNotIn("--cwd", launch, "본부 소켓에 부서 폴더를 줬다")


class A5BundlePyEnv(unittest.TestCase):
    def _sh(self, path_dirs, cys_py):
        tmp = tempfile.mkdtemp()
        tb = os.path.join(tmp, "tb")
        os.makedirs(tb)
        for t in ("uname", "sed", "readlink", "dirname", "cat", "head", "tr"):
            try:
                os.symlink("/usr/bin/" + t, os.path.join(tb, t))
            except OSError:
                pass
        ef = os.path.join(tmp, "env")
        open(ef, "w").close()
        env = {"PATH": ":".join([tb] + path_dirs), "CYS_PACK_DIR": PACK, "CLAUDE_ENV_FILE": ef,
               "HOME": tmp}
        r = subprocess.run(["/bin/sh", "-c", '. "$0/hooks/_lib.sh"; CYS_PY="$1"; cys_export_bundle_py_env',
                            PACK, cys_py], capture_output=True, text=True, env=env, timeout=30)
        return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "", open(ef).read()

    @unittest.skipUnless(sys.platform == "darwin", "맥 전용 분기")
    def test_stub_only_mac_gets_bundle_python(self):
        tmp = tempfile.mkdtemp()
        py = os.path.join(tmp, "app", "Resources", "runtime", "python", "bin", "python3")
        os.makedirs(os.path.dirname(py))
        open(py, "w").write("#!/bin/sh\n")
        os.chmod(py, 0o755)
        n, body = self._sh(["/bin", "/usr/sbin"], py)
        self.assertEqual(n, "2")
        self.assertIn("export CYS_PY=", body)
        self.assertIn("runtime/python/bin", body)
        # 진짜 파이썬이 PATH 에 있으면 세션 python3 는 건드리지 않는다
        real = os.path.join(tmp, "real")
        os.makedirs(real)
        open(os.path.join(real, "python3"), "w").write("#!/bin/sh\n")
        os.chmod(os.path.join(real, "python3"), 0o755)
        n2, body2 = self._sh([real, "/bin"], py)
        self.assertEqual((n2, body2), ("0", ""))
        # 번들이 아닌 CYS_PY 면 비발동
        n3, body3 = self._sh(["/bin"], os.path.join(real, "python3"))
        self.assertEqual((n3, body3), ("0", ""))

    def test_session_start_calls_it(self):
        s = open(os.path.join(PACK, "hooks", "session-start.sh"), encoding="utf-8").read()
        self.assertIn("cys_export_bundle_py_env", s)


class A5A2DirectiveContract(unittest.TestCase):
    def _d(self, n):
        return open(os.path.join(PACK, "directives", n), encoding="utf-8").read()

    def test_cso_lines(self):
        t = self._d("CSO_DIRECTIVE.md")
        self.assertIn("부서장 좌석 회수 = 부팅 유예 뒤", t)
        self.assertIn("부서 편성이 띄운다", t)
        self.assertIn("사용자 환경 변경 금지", t)
        self.assertIn("~/.local/bin", t)

    def test_worker_line(self):
        self.assertIn("사용자 환경 변경 금지", self._d("WORKER_DIRECTIVE.md"))


class B2RecapDefault(unittest.TestCase):
    def _pf(self, targets):
        import javis_preflight as pf
        p = pf.Preflight(True, set())
        saved = pf.resolve_registration_targets
        pf.resolve_registration_targets = lambda: (targets, None)
        try:
            p.c83_recap_default()
        finally:
            pf.resolve_registration_targets = saved
        return [r for r in p.results if "C83" in json.dumps(r, ensure_ascii=False, default=str)]

    def test_seeds_false_and_respects_user_value(self):
        tmp = tempfile.mkdtemp()
        a, b = os.path.join(tmp, "a", "settings.json"), os.path.join(tmp, "b", "settings.json")
        os.makedirs(os.path.dirname(a))
        os.makedirs(os.path.dirname(b))
        json.dump({"hooks": {}}, open(a, "w"))
        json.dump({"awaySummaryEnabled": True}, open(b, "w"))
        self._pf([a, b])
        self.assertIs(json.load(open(a))["awaySummaryEnabled"], False)
        self.assertIn("hooks", json.load(open(a)), "다른 키를 잃었다")
        self.assertIs(json.load(open(b))["awaySummaryEnabled"], True, "사용자 값을 덮었다")

    def test_registered_in_run_order(self):
        src = open(os.path.join(BIN, "javis_preflight.py"), encoding="utf-8").read()
        self.assertIn("self.c83_recap_default,", src)


class B3DrainIssuer(unittest.TestCase):
    OLD = ("재시작 단추를 누른", "재시작 단추를 눌러 발신")
    NEW = "새 판 설치"

    def test_no_button_only_issuer_left(self):
        files = [os.path.join(PACK, "directives", n) for n in
                 ("MASTER_DIRECTIVE.md", "CEO_TEMPLATE.md", "CSO_DIRECTIVE.md", "WORKER_DIRECTIVE.md")]
        files += [os.path.join(PACK, "hooks", "session-start.sh"), os.path.join(REPO, "src", "bin", "cys.rs")]
        for f in files:
            with open(f, encoding="utf-8") as fh:
                t = fh.read()
            for o in self.OLD:
                self.assertNotIn(o, t, "%s 에 옛 발신 주체 문구" % f)
            self.assertIn(self.NEW, t, "%s 에 새 문구 없음" % f)


if __name__ == "__main__":
    unittest.main(verbosity=1)
