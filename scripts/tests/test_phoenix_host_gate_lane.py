"""phoenix host-level 게이트 레인 대조(TICKET=cysr-1113-release · 1.1.14) — 두 워크플로가 **같은 한 정의**를 부르는지,
그리고 정규화 TMPDIR 이 그 정의의 파이썬 루프 밖(특히 cargo 시험)으로 새지 않는지를 잰다.

왜 존재하는가: release.yml 「phoenix host-level 로직 게이트 (macOS 네이티브)」 스텝과 ci-branch.yml `phoenix-host-gate` 잡은
1.1.13 까지 문면으로 맞춘 두 블록이었다. 한쪽(release)에만 있던 줄 — 스텝 머리의 `export TMPDIR=… pwd -P` 가 같은 스텝의
`cargo test --bin cys` 까지 걸린 것 — 이 가지 CI 에서는 보이지 않다가 태그 런(42160662015)에서야 드러나 판번을 셋째로 소각했다
(src/bin/cys.rs 시험 3건 · 소켓 경로 8바이트 증가 → SUN_LEN). 이제 두 곳은 scripts/ci/phoenix-host-gate.sh 만 부른다.

재는 것:
  1) 두 스텝이 같은 호출 줄(같은 스크립트 · 같은 글롭)을 정확히 1번씩 갖는다.
  2) 어느 워크플로에도 phoenix 글롭 루프(`for t in …test_phoenix_*.py`)와 스텝 전체 `export TMPDIR=` 가 따로 남지 않았다.
  3) 스크립트의 정규화 export 는 서브셸 `( … )` 안에만 있고, 스크립트는 cargo 시험을 돌리지 않는다(C8 재고 계약 경계 —
     scripts/tests/test_c8_ci_consumer.py 가 워크플로 본문의 cysd 실행을 직접 센다).
  4) 행동: release 스텝 run 본문 그대로를 가짜 cargo·가짜 python3 로 별칭 TMPDIR 아래에서 돌리면 phoenix 파이썬은 정규 경로를,
     cargo 시험 3줄은 부른 쪽 TMPDIR 그대로를 본다 · 파이썬 시험이 실패하면 그 rc 로 끝나고 cargo 시험은 돌지 않는다 ·
     스크립트 인자가 없거나 글롭이 빈 경우 rc 2.
표준 라이브러리만 쓴다(CI 파이썬에 PyYAML 이 없다).

    python3 scripts/tests/test_phoenix_host_gate_lane.py
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_ci_branch_cysd_step import extract_step

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/ci/phoenix-host-gate.sh"
CALL = "bash scripts/ci/phoenix-host-gate.sh cysjavis-pack/bin/tests/test_phoenix_*.py"
STEPS = [
    ("release.yml", "phoenix host-level 로직 게이트 (macOS 네이티브)"),
    ("ci-branch.yml", "phoenix host-level 게이트 — 태그 레인 동일 조건 (macos-latest arm64)"),
]
BASH = shutil.which("bash") or "/bin/bash"


def code_lines(text):
    """주석·빈 줄을 뺀 줄(앞뒤 공백 제거)."""
    out = []
    for raw in text.splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


class Text(unittest.TestCase):
    def test_both_lanes_call_the_same_one_definition(self):
        for wf, step in STEPS:
            with self.subTest(workflow=wf):
                body = extract_step(str(ROOT / ".github/workflows" / wf), step)["run"]
                self.assertEqual([l for l in code_lines(body) if l == CALL], [CALL],
                                 "%s 스텝 %r 은 한 정의 호출 줄을 정확히 1번 가져야 한다: %s" % (wf, step, CALL))
                self.assertFalse([l for l in code_lines(body) if SCRIPT in l and l != CALL],
                                 "같은 스크립트를 다른 인자로 부르면 두 레인이 다시 갈린다")

    def test_no_copied_phoenix_loop_or_step_wide_tmpdir_export_left(self):
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            for line in code_lines(path.read_text(encoding="utf-8")):
                with self.subTest(workflow=path.name, line=line):
                    # 글롭 전체 경로(설명 문자열 속 `test_phoenix_*.py` 낱말은 대상 아님) 또는 그 글롭을 도는 for 루프
                    if "cysjavis-pack/bin/tests/test_phoenix_*" in line or re.search(r"\bfor\s+\w+\s+in\b.*test_phoenix_\*", line):
                        self.assertEqual(line, CALL, "phoenix 글롭은 한 정의 호출 줄에만 있어야 한다(복제 루프 금지)")
                    self.assertIsNone(re.search(r"\bexport\s+TMPDIR=", line),
                                      "스텝 전체에 TMPDIR 를 export 하면 같은 스텝의 다른 명령(cargo 시험 등)까지 바뀐다 — "
                                      "필요한 명령 앞에만 TMPDIR= 를 붙이거나 서브셸에 가둬라")

    def test_script_confines_the_export_to_a_subshell_and_runs_no_cargo_tests(self):
        lines = (ROOT / SCRIPT).read_text(encoding="utf-8").splitlines()
        code = [(i, l.strip()) for i, l in enumerate(lines) if l.strip() and not l.strip().startswith("#")]
        exports = [i for i, l in code if re.match(r"export\s+TMPDIR=", l)]
        self.assertEqual(len(exports), 1, "정규화 export 는 1곳이어야 한다")
        opens = [i for i, l in code if l == "(" and i < exports[0]]
        closes = [i for i, l in code if l == ")" and i > exports[0]]
        self.assertTrue(opens and closes, "정규화 export 는 서브셸 ( … ) 안에 있어야 한다")
        inside = [l for i, l in code if opens[-1] < i < closes[0]]
        self.assertTrue(any("python3" in l for l in inside), "서브셸 안에 파이썬 phoenix 루프가 있어야 한다")
        self.assertFalse([l for _, l in code if re.search(r"\bcargo\s+(test|t|nextest)\b", l)],
                         "스크립트가 cargo 시험을 돌리면 C8 재고 시험이 그 cysd 실행을 못 본다")


class Behaviour(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="phx-lane-")
        self.addCleanup(tmp.cleanup)
        real = Path(os.path.realpath(tmp.name))
        self.root = real / "repo"
        (self.root / "scripts/ci").mkdir(parents=True)
        shutil.copyfile(ROOT / SCRIPT, self.root / SCRIPT)
        tests = self.root / "cysjavis-pack/bin/tests"
        tests.mkdir(parents=True)
        for n in ("test_phoenix_a.py", "test_phoenix_b.py"):
            (tests / n).write_text("# fixture\n", encoding="utf-8")
        # 별칭 TMPDIR: 심링크 경로(러너 /var → /private/var 와 같은 꼴) · 정규 = realpath
        (real / "tmp-real").mkdir()
        os.symlink(real / "tmp-real", real / "tmp-alias")
        self.alias = str(real / "tmp-alias")
        self.norm = str(real / "tmp-real")
        self.rt = real / "runner-temp"
        self.rt.mkdir()
        self.calls = real / "calls"
        bin_ = real / "bin"
        bin_.mkdir()
        (bin_ / "cargo").write_text('#!/bin/sh\nprintf "cargo %s|TMPDIR=%s\\n" "$1" "$TMPDIR" >> "$CALLS"\nexit 0\n', encoding="utf-8")
        (bin_ / "python3").write_text('#!/bin/sh\nprintf "python3 %s|TMPDIR=%s\\n" "$(basename "$1")" "$TMPDIR" >> "$CALLS"\n'
                                      'case "$1" in *"$FAIL_ON"*) exit 7;; esac\nexit 0\n', encoding="utf-8")
        for f in bin_.iterdir():
            f.chmod(0o755)
        self.env = {"PATH": str(bin_) + ":/usr/bin:/bin", "HOME": str(real), "TMPDIR": self.alias,
                    "RUNNER_TEMP": str(self.rt), "CALLS": str(self.calls), "FAIL_ON": "__none__"}

    def run_release_body(self, **extra):
        body = extract_step(str(ROOT / ".github/workflows/release.yml"), STEPS[0][1])["run"]
        script = self.root / "step.sh"
        script.write_text(body, encoding="utf-8")
        env = dict(self.env, **extra)
        self.calls.unlink(missing_ok=True)
        r = subprocess.run([BASH, "--noprofile", "--norc", "-e", "-o", "pipefail", str(script)],
                           cwd=self.root, env=env, capture_output=True, text=True, timeout=60)
        calls = self.calls.read_text().splitlines() if self.calls.exists() else []
        return r, calls

    def test_python_sees_normalized_tmpdir_and_cargo_tests_see_the_callers(self):
        r, calls = self.run_release_body()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        py = [c for c in calls if c.startswith("python3 ")]
        self.assertEqual([c.split("|")[0] for c in py], ["python3 test_phoenix_a.py", "python3 test_phoenix_b.py"])
        self.assertTrue(all(c.endswith("|TMPDIR=" + self.norm) for c in py), py)
        tests = [c for c in calls if c.startswith("cargo test")]
        self.assertEqual(len(tests), 3, calls)
        self.assertTrue(all(c.endswith("|TMPDIR=" + self.alias) for c in tests),
                        "cargo 시험이 정규화 TMPDIR 을 보면 v1.1.13 적색(SUN_LEN)이 돌아온다: %s" % tests)
        self.assertTrue((self.rt / "c8-release-cysd.log").exists(), "C8 로그 경로 계약")

    def test_python_failure_ends_the_step_with_its_rc_before_any_cargo_test(self):
        r, calls = self.run_release_body(FAIL_ON="test_phoenix_a.py")
        self.assertEqual(r.returncode, 7, r.stdout + r.stderr)
        self.assertFalse([c for c in calls if c.startswith("cargo test")], calls)
        self.assertFalse([c for c in calls if "test_phoenix_b.py" in c], "실패 뒤 다음 시험으로 넘어가면 안 된다")

    def test_script_refuses_no_args_and_an_unmatched_glob(self):
        for args in ([], ["cysjavis-pack/bin/tests/test_phoenix_zzz*.py"]):
            with self.subTest(args=args):
                r = subprocess.run([BASH, SCRIPT, *args], cwd=self.root, env=self.env,
                                   capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
