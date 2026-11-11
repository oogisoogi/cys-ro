#!/usr/bin/env python3
"""agy 좌석 문(TICKET=cysr-agy-policy-exposure) — 팩 쪽 계약 시험.

정본 = 저장소 `src/agy_door.rs`(판정·문 파일) · 이 파일은 팩이 그 문을 **열지 못하고**(⑤) 닫힌 문을 **실패로 읽지
않으며**(복원) 검토자 슬롯이 Claude 대체로 **폴백**하는지(③)를 잰다.

  A. guard.sh — 에이전트가 문 파일을 만들거나 쓰는 평시 경로(touch·리다이렉트·cp·python·`cys send`·Write/Edit)는 DENY ·
     읽기는 통과 · 무관한 명령은 통과.
  B. 팩 전체(지침·스킬·복원기·스크립트)에 문 파일을 여는 코드·지시가 0(guard.sh 의 금지 규칙과 이 시험만 이름을 안다).
  C. phoenix `agy_door_split` — 오라클이 agy_consumer_policy 를 낸 역할만 부활 대상에서 가르고(실패 아님), 오라클이 없으면
     가르지 않는다(종전 동작). 가른 역할은 최종 결과의 빈 좌석(manual_seats)에 다시 들어가지 않는다.
  D. (cys 바이너리가 있을 때) `cys agent-detect --json` 이 문 닫힘이면 gemini=미가용·사유 agy_consumer_policy,
     문 열림이면 종전대로 가용 · 그 오라클로 `javis_orchestra.py boot-reviewers --spawn --plan` 이 reviewer-claude-1 로 폴백.
     바이너리 = env `CYS_TEST_BIN` 또는 저장소 `target/debug/cys` · 없으면 D 만 건너뛴다(사유 출력).

실행: python3 cysjavis-pack/bin/tests/test_agy_door.py  (unittest 로도 돈다)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(HERE)
PACK = os.path.dirname(BIN)
REPO = os.path.dirname(PACK)
GUARD = os.path.join(PACK, "hooks", "guard.sh")
DOOR = "agy-seat-door.json"
ACK = "agy-consumer-plan-warning-v1"
sys.path.insert(0, BIN)


def guard(payload):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CYS_", "AUTOPILOT", "GUARD_"))}
    env.update({"GUARD_TEST_MODE": "1", "CYS_HOOK_LANE_GUARD": "0"})
    r = subprocess.run(["bash", GUARD], input=json.dumps(payload, ensure_ascii=False), env=env,
                       capture_output=True, text=True, timeout=60)
    return r.returncode, r.stderr


class A_GuardDeniesDoorWrites(unittest.TestCase):
    DENY = [
        ("Bash", {"command": "touch ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "echo '{\"open\":true}' > ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "printf x >> \"$HOME/.cys/agy-seat-door.json\""}),
        ("Bash", {"command": "cp /tmp/x \"$HOME/.cys/agy-seat-\"'door.json'"}),
        ("Bash", {"command": "python3 -c \"open('/Users/x/.cys/agy-seat-door.json','w').write('{}')\""}),
        ("Bash", {"command": "echo hi | tee ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "cys send --surface surface:3 \"touch ~/.cys/agy-seat-door.json\""}),
        ("Bash", {"command": "CYS_X=1 install -m 600 /tmp/a ~/.cys/agy-seat-door.json"}),
        ("Write", {"file_path": "/Users/x/.cys/agy-seat-door.json", "content": "{}"}),
        ("Edit", {"file_path": "C:\\Users\\x\\.cys\\agy-seat-door.json", "old_string": "a", "new_string": "b"}),
        ("Write", {"file_path": "/Users/x/.cys/agy-seat-door.json.tmp", "content": "{}"}),
        # codex 1R major: git 출력 옵션으로 쓰기
        ("Bash", {"command": "git show -s --format='{\"open\":true}' --output=\"$HOME/.cys/agy-seat-door.json\" HEAD"}),
        # 2R(읽기 허용을 좁게 연 뒤에도 쓰기 길은 닫혀 있어야 한다)
        ("Bash", {"command": "sed -i '' 's/false/true/' ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "sed -n '1w /tmp/x' ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "sed -n '1p;w ~/.cys/agy-seat-door.json' /tmp/x"}),
        ("Bash", {"command": "sed 's/a/b/' /tmp/x > ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "python3 -m json.tool /tmp/x ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "python3 -m json.tool ~/.cys/agy-seat-door.json ~/.cys/agy-seat-door.json"}),
        # codex 2R major: 문 경로가 든 sed 스크립트(w 명령) · -e 여러 개
        ("Bash", {"command": "printf '{\"open\":true}' | sed -n \"w$HOME/.cys/agy-seat-door.json\""}),
        ("Bash", {"command": "printf x | sed -n -e 1p -e \"w$HOME/.cys/agy-seat-door.json\""}),
        ("Bash", {"command": "sed -n -e 1p ~/.cys/agy-seat-door.json -e w/tmp/x"}),
        ("Bash", {"command": "sed -n ~/.cys/agy-seat-door.json -e"}),
        # 독립 재검(2R 반영분): 붙여 쓴 낱말 회귀 · 명령/프로세스 치환 · rg --pre
        ("Bash", {"command": "cp /tmp/p ~/.cys/agy-seat-door.json;:/agy-seat-x.md"}),
        ("Bash", {"command": "cp /tmp/p ~/.cys/agy-seat-door.json&&echo/agy-seat-x.md"}),
        ("Bash", {"command": "cat $(cp /tmp/p ~/.cys/agy-seat-door.json)"}),
        ("Bash", {"command": "cat `cp /tmp/p ~/.cys/agy-seat-door.json`"}),
        ("Bash", {"command": "cat <(cp /tmp/p ~/.cys/agy-seat-door.json)"}),
        ("Bash", {"command": "rg --pre /tmp/w.sh x ~/.cys/agy-seat-door.json"}),
        # codex 3R: HOME 을 딴 곳으로 돌려도 그 아래 문 파일을 만드는 단계가 막혀야 한다(어느 폴더든 이름으로 거부)
        ("Write", {"file_path": "/tmp/fakehome/.cys/agy-seat-door.json", "content": "{}"}),
        ("Bash", {"command": "mkdir -p /tmp/fh/.cys && cp /tmp/x /tmp/fh/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "HOME=/tmp/fh python3 -c \"open('/tmp/fh/.cys/agy-seat-door.json','w')\""}),
        # 치환 본문이 문 이름을 내놓고 바깥이 쓰는 경우
        ("Bash", {"command": "printf x > \"$(echo ~/.cys/agy-seat-door.json)\""}),
        ("Bash", {"command": "cp /tmp/x `echo ~/.cys/agy-seat-door.json`"}),
        ("Bash", {"command": "cat $(cp /tmp/p ~/.cys/agy-seat-door.json"}),
    ]
    ALLOW = [
        ("Bash", {"command": "cat ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "ls -la ~/.cys/ | grep agy-seat-door"}),
        ("Bash", {"command": "ls -la"}),
        # codex 1R minor(거짓 양성): 읽기 전용 sed·json.tool
        ("Bash", {"command": "sed -n 1p ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "sed -n '1,$p' \"$HOME/.cys/agy-seat-door.json\""}),
        ("Bash", {"command": "python3 -m json.tool ~/.cys/agy-seat-door.json"}),
        ("Bash", {"command": "python3 -m json.tool --sort-keys ~/.cys/agy-seat-door.json | head -5"}),
        ("Bash", {"command": "sed -n -e 1p -e '$p' ~/.cys/agy-seat-door.json"}),
        # codex 2R minor: 이름에 낱말이 든 **다른 파일**(문서) 편집은 문 규칙 대상이 아니다
        ("Bash", {"command": "sed -i '' 's/old/new/' docs/agy-seat-door.md"}),
        # codex 3R minor: 이름만 비슷한 다른 데이터 파일 · 읽기 전용 치환
        ("Bash", {"command": "sed -i s/x/y/ docs/agy-seat-notes.json"}),
        ("Bash", {"command": "printf '%s' \"$(cat ~/.cys/agy-seat-door.json)\""}),
        ("Write", {"file_path": "/Users/x/repo/docs/agy-seat-door.md", "content": "설명 문서"}),   # 문 파일 아님(codex 1R minor)
    ]

    def test_deny(self):
        for tool, ti in self.DENY:
            rc, err = guard({"tool_name": tool, "tool_input": ti})
            self.assertEqual(rc, 2, "%s %s 통과됨: %s" % (tool, ti, err[-300:]))
            self.assertIn("AGY-DOOR", err, "%s %s — 다른 규칙이 막았다(문 규칙 미발동): %s" % (tool, ti, err[-300:]))

    def test_backstop_without_python_still_denies(self):
        # codex 1R major: 파서(python) 부재 → bash 백스톱 — 문 쓰기는 여기서도 거부 · 순수 읽기는 통과
        def g(payload):
            env = {k: v for k, v in os.environ.items() if not k.startswith(("CYS_", "AUTOPILOT", "GUARD_"))}
            env.update({"GUARD_TEST_MODE": "1", "CYS_HOOK_LANE_GUARD": "0", "GUARD_FORCE_NOPY": "1"})
            r = subprocess.run(["bash", GUARD], input=json.dumps(payload, ensure_ascii=False), env=env,
                               capture_output=True, text=True, timeout=60)
            return r.returncode, r.stderr
        for tool, ti in [("Write", {"file_path": "/Users/x/.cys/agy-seat-door.json", "content": "{}"}),
                         ("Bash", {"command": "echo {} > ~/.cys/agy-seat-door.json"}),
                         ("Bash", {"command": "touch ~/.cys/agy-seat-door.json"})]:
            rc, err = g({"tool_name": tool, "tool_input": ti})
            self.assertEqual(rc, 2, "%s %s 백스톱 통과: %s" % (tool, ti, err[-300:]))
            self.assertIn("AGY-DOOR", err)
        # codex 2R major: 첫 낱말이 cat 이어도 복합 명령이면 거부
        for cmd in ["cat /dev/null; cp /tmp/payload \"$HOME/.cys/agy-seat-door.json\"",
                    "cat /dev/null && tee \"$HOME/.cys/agy-seat-door.json\" </tmp/payload",
                    "cat /dev/null | tee ~/.cys/agy-seat-door.json",
                    "cat $(cp /tmp/p ~/.cys/agy-seat-door.json)",
                    "cat /dev/null\ncp /tmp/p ~/.cys/agy-seat-door.json",
                    "cat <(cp /tmp/p ~/.cys/agy-seat-door.json)"]:
            rc, err = g({"tool_name": "Bash", "tool_input": {"command": cmd}})
            self.assertEqual(rc, 2, "%r 백스톱 통과: %s" % (cmd, err[-300:]))
            self.assertIn("AGY-DOOR", err)
        rc, err = g({"tool_name": "Bash", "tool_input": {"command": "cat ~/.cys/agy-seat-door.json"}})
        self.assertEqual(rc, 0, err[-300:])

    def test_allow(self):
        for tool, ti in self.ALLOW:
            rc, err = guard({"tool_name": tool, "tool_input": ti})
            self.assertEqual(rc, 0, "%s %s 막힘: %s" % (tool, ti, err[-300:]))


class B_PackHasNoDoorOpener(unittest.TestCase):
    def test_no_pack_file_names_the_door_except_guard(self):
        allowed = {os.path.realpath(GUARD), os.path.realpath(os.path.abspath(__file__))}
        hits = []
        for root, dirs, files in os.walk(PACK):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
            for f in files:
                p = os.path.join(root, f)
                if os.path.realpath(p) in allowed:
                    continue
                try:
                    with open(p, encoding="utf-8", errors="ignore") as fh:
                        s = fh.read()
                except OSError:
                    continue
                if "agy-seat-door" in s or "agy_seat_door" in s or ACK in s:
                    hits.append(os.path.relpath(p, PACK))
        self.assertEqual(hits, [], "팩이 문 파일을 안다(여는 길 후보): %s" % hits)


class C_PhoenixPolicySplit(unittest.TestCase):
    def setUp(self):
        import javis_phoenix
        self.ph = javis_phoenix

    def test_splits_only_policy_refused_agents(self):
        entries = {"worker": {"agent": "claude"}, "reviewer-gemini": {"agent": "gemini"},
                   "reviewer-codex": {"agent": "codex"}}
        detect = {"claude": "PATH 발견 /x/claude",
                  "gemini": "agy_consumer_policy: Antigravity(agy) 좌석 문 닫힘 — 실행 파일 판정: 실행가능 /x/agy",
                  "codex": "PATH 미발견 codex"}
        keep, skipped = self.ph.agy_door_split(["worker", "reviewer-gemini", "reviewer-codex"], entries, detect=detect)
        self.assertEqual(keep, ["worker", "reviewer-codex"])
        self.assertEqual(skipped, ["reviewer-gemini"])

    def test_no_oracle_means_no_split(self):
        entries = {"reviewer-gemini": {"agent": "gemini"}}
        keep, skipped = self.ph.agy_door_split(["reviewer-gemini"], entries, detect={})
        self.assertEqual((keep, skipped), (["reviewer-gemini"], []))

    def test_rc_matches_rust_and_fresh_76_is_consumed(self):
        with open(os.path.join(REPO, "src", "agy_door.rs"), encoding="utf-8") as fh:
            rs = fh.read()
        self.assertIn("pub const EXIT_AGY_POLICY_REFUSED: i32 = %d;" % self.ph.AGY_POLICY_RC, rs)
        with open(os.path.join(BIN, "javis_phoenix.py"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("res = spawn_fresh_production(socket, role, agent, cwd=fresh_cwd)")
        self.assertIn('if res.get("rc") == AGY_POLICY_RC:', src[i:i + 300], "fresh 76 을 정책 건너뜀으로 소비하지 않는다")

    def test_policy_skipped_role_is_not_a_manual_seat(self):
        # codex 1R minor: 정책으로 건너뛴 agy 좌석이 「빈 좌석 · 사람이 실행」으로 다시 보고되면 안 된다
        live_end = {"reviewer-gemini": [{"exited": False, "seat": "empty"}],
                    "worker": [{"exited": False, "seat": "empty"}],
                    "master": [{"exited": False, "seat": "occupied"}],
                    "-": [{"exited": False, "seat": "empty"}]}
        self.assertEqual(self.ph.manual_seat_roles(live_end), ["reviewer-gemini", "worker"])   # 종전 동작
        self.assertEqual(self.ph.manual_seat_roles(live_end, ["reviewer-gemini"]), ["worker"])
        with open(os.path.join(BIN, "javis_phoenix.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("manual_seats = manual_seat_roles(live_end, _agy_skipped)", src, "결과 배선이 정책 제외를 쓰지 않는다")
        self.assertIn('"agy_policy_skipped_roles": sorted(_agy_skipped)', src, "정책 건너뜀이 결과에 따로 남지 않는다")

    def test_code_matches_rust(self):
        with open(os.path.join(REPO, "src", "agy_door.rs"), encoding="utf-8") as fh:
            rs = fh.read()
        self.assertIn('pub const REFUSE_CODE: &str = "%s";' % self.ph.AGY_POLICY_CODE, rs)


def _cys_bin():
    b = os.environ.get("CYS_TEST_BIN") or os.path.join(REPO, "target", "debug", "cys")
    return b if os.path.isfile(b) and os.access(b, os.X_OK) else None


@unittest.skipUnless(_cys_bin(), "cys 바이너리 없음(CYS_TEST_BIN 또는 target/debug/cys) — D 건너뜀")
class D_OracleAndRosterFallback(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp(prefix="agydoor-")
        self.home = os.path.join(self.td, "home")
        self.pack = os.path.join(self.td, "pack")
        os.makedirs(os.path.join(self.home, ".local", "bin"))
        os.makedirs(os.path.join(self.home, ".cys"))
        os.makedirs(self.pack)
        shutil.copy(os.path.join(PACK, "agents.json"), os.path.join(self.pack, "agents.json"))
        os.makedirs(os.path.join(self.pack, "directives"))
        shutil.copy(os.path.join(PACK, "directives", "REVIEWER_DIRECTIVE.md"),
                    os.path.join(self.pack, "directives", "REVIEWER_DIRECTIVE.md"))
        # 가짜 agy(실제 agy 아님) — 실행되면 표식 파일을 남긴다(이 시험은 실행하지 않는다 · 감지만).
        fake = os.path.join(self.home, ".local", "bin", "agy")
        with open(fake, "w") as f:
            f.write("#!/bin/sh\necho ran >> \"$HOME/agy-ran\"\n")
        os.chmod(fake, 0o755)
        self.pbin = os.path.join(self.td, "pbin")
        os.makedirs(self.pbin)
        os.symlink(_cys_bin(), os.path.join(self.pbin, "cys"))
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("CYS_", "AITERM_"))}
        self.env.update({"HOME": self.home, "CYS_PACK_DIR": self.pack, "CYS_NO_AUTOSTART": "1",
                         "PATH": self.pbin + os.pathsep + "/usr/bin:/bin"})

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def detect(self):
        r = subprocess.run([os.path.join(self.pbin, "cys"), "agent-detect", "--json"], env=self.env,
                           capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["agents"]

    def open_door(self):
        with open(os.path.join(self.home, ".cys", DOOR), "w") as f:
            json.dump({"open": True, "ack": ACK}, f)

    def test_closed_door_reports_unavailable_with_policy_reason(self):
        g = self.detect()["gemini"]
        self.assertFalse(g["installed"], g)
        self.assertTrue(g["reason"].startswith("agy_consumer_policy"), g)
        self.assertIn("실행가능", g["reason"], "실행 파일 판정을 사유에 남겨야 한다")
        self.assertTrue(self.detect()["claude"]["reason"] and not self.detect()["claude"]["reason"].startswith("agy_"))

    def test_open_door_restores_previous_detection(self):
        self.open_door()
        g = self.detect()["gemini"]
        self.assertTrue(g["installed"], g)
        self.assertFalse(g["reason"].startswith("agy_consumer_policy"), g)

    def test_env_var_does_not_open(self):
        for k in ("CYS_AGY_SEAT_DOOR", "CYS_ALLOW_AGY", "CYS_ENABLE_AGY_SEAT", "CYS_ENABLE_AGY_LANE"):
            self.env[k] = "1"
        self.assertFalse(self.detect()["gemini"]["installed"])

    def test_hand_made_door_without_ack_stays_closed(self):
        with open(os.path.join(self.home, ".cys", DOOR), "w") as f:
            json.dump({"open": True}, f)
        self.assertFalse(self.detect()["gemini"]["installed"])

    def test_orchestra_roster_falls_back_to_claude_reviewer(self):
        r = subprocess.run([sys.executable, os.path.join(BIN, "javis_orchestra.py"), "boot-reviewers", "--spawn", "--plan"],
                           env=self.env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, out[-800:])
        self.assertIn("reviewer-claude-1", out, out[-800:])
        self.assertIn("agy_consumer_policy", out, "폴백 사유가 보고에 보여야 한다: " + out[-800:])
        self.assertFalse(os.path.exists(os.path.join(self.home, "agy-ran")), "가짜 agy 가 실행됐다")

    def test_orchestra_roster_native_when_open(self):
        self.open_door()
        r = subprocess.run([sys.executable, os.path.join(BIN, "javis_orchestra.py"), "boot-reviewers", "--spawn", "--plan"],
                           env=self.env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, out[-800:])
        self.assertIn("reviewer-gemini", out)
        self.assertNotIn("reviewer-claude-1", out, out[-800:])


if __name__ == "__main__":
    unittest.main(verbosity=1)
