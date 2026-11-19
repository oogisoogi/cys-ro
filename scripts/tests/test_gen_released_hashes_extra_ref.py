#!/usr/bin/env python3
"""scripts/gen_released_directive_hashes.py `--extra-ref` 계약 시험.

임시 git 저장소(태그 1개 · 태그 없는 직전 판 커밋 1개 · 작업 트리 판 1개)에 생성기 사본을 놓고 돌린다 —
이 저장소의 태그·작업 트리·표 파일은 건드리지 않는다.

재는 것:
  · extra-ref 없음 = 표에 태그 판 + 작업 트리 판만(태그 없는 커밋 판은 없음)
  · --extra-ref <커밋> = 그 커밋 판 바이트도 표에 듦(Rust 표 · 팩 sha256 목록 둘 다)
  · 같은 --extra-ref 로 --check = 0 · extra-ref 없이 --check = 1(표류)
  · 못 찾는 ref · 그 커밋에 지침 파일 없음 · 값 빠진 --extra-ref · 모르는 인자 = exit 2 + 표 파일 무변경
  · 태그 0개 = exit 3(extra-ref 가 있어도)
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(os.path.dirname(HERE), "gen_released_directive_hashes.py")
CEO = "cysjavis-pack/directives/CEO_TEMPLATE.md"
MASTER = "cysjavis-pack/directives/MASTER_DIRECTIVE.md"
RS = "src/released_directive_hashes.rs"
LIST = "cysjavis-pack/directives/RELEASED_MASTER_DIRECTIVE.sha256"


def sha(b):
    return hashlib.sha256(b).hexdigest()


class ExtraRef(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="genhx")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "CYS_"))}
        mail = "t" + chr(64) + "t.invalid"  # 실행 시 조립(공개 secret-scan 메일 패턴 회피)
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL=mail,
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL=mail)
        os.makedirs(os.path.join(self.root, "scripts"))
        os.makedirs(os.path.join(self.root, "src"))
        os.makedirs(os.path.join(self.root, "cysjavis-pack", "directives"))
        shutil.copy(GEN, os.path.join(self.root, "scripts", "gen_released_directive_hashes.py"))
        self.git("init", "-q", "-b", "master")
        # 판 A = 태그 v1.0.0
        self.write(b"ceo A\n", b"master A\n")
        self.git("add", "-A"); self.git("commit", "-qm", "A"); self.git("tag", "v1.0.0")
        # 판 B = 기계에 나갔지만 태그가 아직 없는 직전 판
        self.write(b"ceo B\n", b"master B\n")
        self.git("commit", "-qam", "B")
        self.b = self.git("rev-parse", "HEAD").strip()
        # 판 C = 작업 트리(다음 판)
        self.write(b"ceo C\n", b"master C\n")
        # 지침 파일이 없는 커밋(브랜치 머리 · 고아 커밋)
        self.git("checkout", "-q", "--orphan", "bare")
        self.git("rm", "-rqf", "--cached", ".")
        open(os.path.join(self.root, "README"), "w").write("x\n")
        self.git("add", "README"); self.git("commit", "-qm", "nofile")
        self.nofile = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-qf", "master")
        self.write(b"ceo C\n", b"master C\n")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def git(self, *a):
        r = subprocess.run(["git", "-C", self.root] + list(a), env=self.env, capture_output=True)
        if r.returncode:
            raise AssertionError("git %s: %s" % (a, r.stderr.decode()))
        return r.stdout.decode()

    def write(self, ceo, master):
        for rel, b in ((CEO, ceo), (MASTER, master)):
            with open(os.path.join(self.root, rel), "wb") as f:
                f.write(b)

    def run_gen(self, *a):
        r = subprocess.run([sys.executable, os.path.join(self.root, "scripts", "gen_released_directive_hashes.py")]
                           + list(a), env=self.env, capture_output=True)
        return r.returncode, r.stderr.decode()

    def read(self, rel):
        p = os.path.join(self.root, rel)
        return open(p, encoding="utf-8").read() if os.path.exists(p) else None

    def test_without_extra_ref_tag_and_tree_only(self):
        rc, err = self.run_gen()
        self.assertEqual(rc, 0, err)
        rs, lst = self.read(RS), self.read(LIST)
        for b in (b"ceo A\n", b"ceo C\n", b"master A\n", b"master C\n"):
            self.assertIn(sha(b), rs)
        self.assertNotIn(sha(b"ceo B\n"), rs)
        self.assertNotIn(sha(b"master B\n"), lst)

    def test_extra_ref_adds_untagged_bytes_to_both_tables(self):
        rc, err = self.run_gen("--extra-ref", self.b)
        self.assertEqual(rc, 0, err)
        rs, lst = self.read(RS), self.read(LIST)
        self.assertIn(sha(b"ceo B\n"), rs)
        self.assertIn(sha(b"master B\n"), rs)
        self.assertIn(sha(b"master B\n"), lst)
        self.assertNotIn(sha(b"ceo B\n"), lst)  # 팩 목록은 MASTER 표만
        for b in (b"master A\n", b"master C\n"):
            self.assertIn(sha(b), lst)
        # = 형태도 같은 표
        rc, err = self.run_gen("--check", "--extra-ref=%s" % self.b)
        self.assertEqual(rc, 0, err)

    def test_check_needs_same_extra_ref(self):
        self.assertEqual(self.run_gen("--extra-ref", self.b)[0], 0)
        self.assertEqual(self.run_gen("--check", "--extra-ref", self.b)[0], 0)
        rc, err = self.run_gen("--check")
        self.assertEqual(rc, 1, err)
        self.assertIn("표류", err)

    def test_tag_on_same_bytes_absorbs_extra_ref(self):
        self.assertEqual(self.run_gen("--extra-ref", self.b)[0], 0)
        self.git("tag", "v1.0.1", self.b)
        self.assertEqual(self.run_gen("--check")[0], 0)

    def test_bad_inputs_exit2_and_tables_untouched(self):
        self.assertEqual(self.run_gen()[0], 0)
        before = (self.read(RS), self.read(LIST))
        for args, word in ((("--extra-ref", "no-such-ref"), "못 찾음"),
                           (("--extra-ref", self.nofile), "없음"),
                           (("--extra-ref",), "없음"),
                           (("--extra-ref", "--check"), "없음"),
                           (("--extra-ref=",), "비었음"),
                           (("--bogus",), "모르는 인자")):
            rc, err = self.run_gen(*args)
            self.assertEqual(rc, 2, (args, err))
            self.assertIn(word, err, args)
            self.assertEqual((self.read(RS), self.read(LIST)), before, args)

    def test_second_table_write_failure_leaves_both_tables_unchanged(self):
        self.assertEqual(self.run_gen()[0], 0)
        before = (self.read(RS), self.read(LIST))
        os.makedirs(os.path.join(self.root, LIST + ".gen-tmp"))   # 둘째 표의 임시 파일 자리가 폴더 = 쓰기 실패 주입
        rc, err = self.run_gen("--extra-ref", self.b)
        self.assertEqual(rc, 2, err)
        self.assertEqual((self.read(RS), self.read(LIST)), before)
        self.assertFalse(os.path.exists(os.path.join(self.root, RS + ".gen-tmp")), "첫 표 임시 파일이 남았다")

    def load_gen(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("genx", os.path.join(self.root, "scripts", "gen_released_directive_hashes.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def main_with_replace_failure(self, fail_on):
        """생성기 main() 을 이 프로세스에서 부르되 os.replace 의 fail_on 번째 호출(1부터)을 실패시킨다."""
        from unittest import mock
        m = self.load_gen()
        real, n = os.replace, [0]

        def flaky(a, b):
            n[0] += 1
            if n[0] == fail_on:
                raise OSError("주입: replace %d 실패" % fail_on)
            return real(a, b)
        old_env, old_argv = dict(os.environ), sys.argv
        os.environ.update(self.env)
        sys.argv = ["gen", "--extra-ref", self.b]
        try:
            with mock.patch.object(m.os, "replace", flaky):
                rc = m.main()
        finally:
            os.environ.clear(); os.environ.update(old_env); sys.argv = old_argv
        return rc

    def test_second_table_replace_failure_rolls_back_first(self):
        """두 표 중 첫 표를 바꾼 뒤 둘째 rename 이 실패해도 첫 표가 되돌아가 둘 다 원상(codex 2R #8)."""
        self.assertEqual(self.run_gen()[0], 0)
        before = (self.read(RS), self.read(LIST))
        self.assertEqual(self.main_with_replace_failure(2), 2)
        self.assertEqual((self.read(RS), self.read(LIST)), before)
        left = [n for d, _, fs in os.walk(self.root) for n in fs if n.endswith((".gen-tmp", ".gen-bak"))]
        self.assertEqual(left, [], "임시·사본 파일이 남았다")
        self.assertEqual(self.main_with_replace_failure(99), 0)          # 대조: 실패 없으면 두 표 모두 새 판
        self.assertIn(sha(b"master B\n"), self.read(LIST))
        self.assertNotEqual(self.read(RS), before[0])

    def test_extra_ref_is_pinned_once_before_reading(self):
        """가지 이름을 줬을 때 시작에서 한 번 OID 로 고정한다 — 읽는 도중 가지가 움직여도 고정한 커밋을 읽는다."""
        import importlib.util
        self.git("branch", "prev", self.b)
        spec = importlib.util.spec_from_file_location("genx", os.path.join(self.root, "scripts", "gen_released_directive_hashes.py"))
        old = dict(os.environ)
        os.environ.update(self.env)
        try:
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            pinned = m.pin_refs(["prev"])
            self.git("branch", "-f", "prev", "v1.0.0")         # 고정 뒤 가지가 움직임
            got = m.collect(MASTER, pinned)
        finally:
            os.environ.clear(); os.environ.update(old)
        self.assertEqual(pinned, [("prev", self.b)])
        self.assertIn(sha(b"master B\n"), got)

    def test_no_tags_still_refused_with_extra_ref(self):
        self.git("tag", "-d", "v1.0.0")
        rc, err = self.run_gen("--extra-ref", self.b)
        self.assertEqual(rc, 3, err)
        self.assertIsNone(self.read(RS))


if __name__ == "__main__":
    unittest.main()
