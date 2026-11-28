#!/usr/bin/env python3
"""cys 1.1.21 A — 동봉 dugite git 감싸개(scripts/mac-runtime/git-wrapper.sh) 실행 시험.

가짜 git 트리(진짜 바이너리 대신 env 를 찍는 sh)로 자리 해소·env 규약만 잰다 — 네트워크·동봉 바이너리 불요.
감싸개 위치 = env CYS_GIT_WRAPPER(기본 = 저장소 scripts/mac-runtime/git-wrapper.sh).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
WRAPPER = os.environ.get("CYS_GIT_WRAPPER") or os.path.join(REPO, "scripts", "mac-runtime", "git-wrapper.sh")

def parse(out):
    d = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k] = v
    return d


@unittest.skipUnless(os.path.exists("/bin/sh"), "sh 없음")
class WrapperTest(unittest.TestCase):
    """감싸개 → 가짜 진짜-바이너리(env 를 찍는 sh) — 자리 해소·env 규약만 잰다."""

    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="cys-gitw-")
        self.root = os.path.join(self.t, "rt", "git")
        core = os.path.join(self.root, "libexec", "git-core")
        os.makedirs(core)
        os.makedirs(os.path.join(self.root, "cysbin"))
        os.makedirs(os.path.join(self.root, "share", "git-core", "templates"))
        fake = os.path.join(core, "git")
        with open(fake, "w") as fh:
            # 감싸개의 init.templateDir 조회(`config --get init.templateDir`)에는 FAKE_TPLCFG=1 일 때만 0(설정 있음).
            fh.write('#!/bin/sh\ncase " $* " in *" config --get init.templateDir "*) echo "$*" >> "$PROBELOG"; '
                     '[ "${FAKE_TPLCFG-}" = 1 ]; exit $?;; esac\n'
                     'echo "EXEC=$GIT_EXEC_PATH"\necho "TPL=${GIT_TEMPLATE_DIR-<unset>}"\n'
                     'echo "SYS=${GIT_CONFIG_SYSTEM-<unset>}"\necho "ARGS=$*"\n')
        os.chmod(fake, 0o755)
        self.w = os.path.join(self.root, "cysbin", "git")
        shutil.copy(WRAPPER, self.w)
        os.chmod(self.w, 0o755)

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def call(self, argv0, cwd=None, extra=None, args=("a b", "c")):
        env = {"PATH": "/usr/bin:/bin", "HOME": self.t, "PROBELOG": os.path.join(self.t, "probe.log")}
        env.update(extra or {})
        r = subprocess.run([argv0, *args], env=env, cwd=cwd, capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        return parse(r.stdout)

    def real(self, p):
        return os.path.realpath(p)

    def test_absolute(self):
        d = self.call(self.w)
        self.assertEqual(d["EXEC"], self.real(os.path.join(self.root, "libexec", "git-core")), "정규화된 절대 경로여야 한다")
        self.assertEqual(d["TPL"], "<unset>", "init·clone 이 아닌 명령엔 템플릿 env 를 세우지 않는다")
        self.assertEqual(d["SYS"], "<unset>", "GIT_CONFIG_SYSTEM 을 세우면 안 된다(번들 쓰기·자식 git 가림)")
        self.assertEqual(d["ARGS"], "a b c")

    def tpl(self, args, extra=None, cwd=None):
        return self.call(self.w, args=args, extra=extra, cwd=cwd)["TPL"]

    def test_template_default_only_for_init_clone(self):
        ours = self.real(os.path.join(self.root, "share", "git-core", "templates"))
        self.assertEqual(self.real(self.tpl(("init", "x"))), ours)
        self.assertEqual(self.real(self.tpl(("clone", "u", "d"))), ours)
        os.makedirs(os.path.join(self.t, "init"), exist_ok=True)  # -C 의 값이 이름 'init' 인 실재 폴더
        self.assertEqual(self.real(self.tpl(("-C", "init", "-c", "a=b", "--bare", "init", "x"), cwd=self.t)), ours,
                         "값 받는 전역 옵션(-C·-c)의 값이 하위 명령으로 오인되면 안 된다")
        self.assertEqual(self.real(self.tpl(("--attr-source", "HEAD", "init", "x"))), ours, "--attr-source 의 값은 하위 명령이 아니다")
        self.assertEqual(self.tpl(("status",)), "<unset>")
        self.assertEqual(self.tpl(("-C", "init", "status"), cwd=self.t), "<unset>", "-C 의 값 'init' 은 하위 명령이 아니다")

    def test_template_user_choice_wins(self):
        self.assertEqual(self.tpl(("init", "--template=/t", "x")), "<unset>")
        self.assertEqual(self.tpl(("init", "--template", "/t", "x")), "<unset>")
        self.assertEqual(self.tpl(("init", "x"), extra={"FAKE_TPLCFG": "1"}), "<unset>", "init.templateDir 설정이 이겨야 한다")
        self.assertEqual(self.tpl(("init", "x"), extra={"GIT_TEMPLATE_DIR": ""}), "", "빈 값도 사용자 선택이다")

    def test_probe_carries_only_command_line_config(self):
        """조회에는 -c·--config-env 만 실리고 -C·--git-dir 등은 빠진다(init·clone 이 읽는 설정 문맥)."""
        log = os.path.join(self.t, "probe.log")
        self.call(self.w, args=("-C", "/", "-c", "a=b", "--git-dir", "/g", "--config-env=x=Y", "--config-env", "z=W", "init", "q"))
        with open(log) as fh:
            line = fh.read().strip().splitlines()[-1]
        self.assertEqual(line, "-c a=b --config-env=x=Y --config-env z=W config --get init.templateDir")

    def test_probe_skips_values_of_other_global_options(self):
        """-C·--git-dir 등의 값이 -c·--config-env= 처럼 생겨도 조회 설정으로 오인하지 않는다(codex r6)."""
        log = os.path.join(self.t, "probe.log")
        os.makedirs(os.path.join(self.t, "--config-env=init.templateDir=TPL"), exist_ok=True)
        os.makedirs(os.path.join(self.t, "-c"), exist_ok=True)
        self.call(self.w, cwd=self.t, args=("-C", "--config-env=init.templateDir=TPL", "--git-dir", "-c", "-c", "k=v", "init", "x"))
        with open(log) as fh:
            self.assertEqual(fh.read().strip().splitlines()[-1], "-c k=v config --get init.templateDir")

    def test_probe_drops_legacy_git_config_env(self):
        """조회는 GIT_CONFIG(옛 env · git config 명령 전용)를 지우고 돈다 — init·clone 의 설정 읽기와 같게."""
        log = os.path.join(self.t, "probe.log")
        fake = os.path.join(self.root, "libexec", "git-core", "git")
        with open(fake) as fh:
            body = fh.read()
        with open(fake, "w") as fh:
            fh.write(body.replace('echo "$*" >> "$PROBELOG";', 'echo "GC=${GIT_CONFIG-<unset>} $*" >> "$PROBELOG";'))
        self.call(self.w, args=("init", "x"), extra={"GIT_CONFIG": "/dev/null"})
        with open(log) as fh:
            self.assertTrue(fh.read().strip().splitlines()[-1].startswith("GC=<unset> "))

    def test_relative_config_env_withholds_default(self):
        """상대 경로 GIT_CONFIG_GLOBAL·GIT_CONFIG_SYSTEM·XDG_CONFIG_HOME 이면 조회 없이 보류(원시 git 그대로)."""
        for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "XDG_CONFIG_HOME"):
            self.assertEqual(self.tpl(("init", "x"), extra={k: "rel/cfg"}), "<unset>", k)
            ours = self.real(os.path.join(self.root, "share", "git-core", "templates"))
            self.assertEqual(self.real(self.tpl(("init", "x"), extra={k: "/abs/cfg"})), ours, k + " 절대 경로는 평소대로")

    def test_relative_and_cwd_independent(self):
        d = self.call("./cysbin/git", cwd=self.root)
        self.assertTrue(d["EXEC"].startswith("/"), d["EXEC"])
        self.assertEqual(self.real(d["EXEC"]), self.real(os.path.join(self.root, "libexec", "git-core")))

    def test_symlink_chain(self):
        l1 = os.path.join(self.t, "l1")
        os.symlink(self.w, l1)
        l2 = os.path.join(self.t, "bin2", "git")
        os.makedirs(os.path.dirname(l2))
        os.symlink("../l1", l2)
        d = self.call(l2)
        self.assertEqual(self.real(d["EXEC"]), self.real(os.path.join(self.root, "libexec", "git-core")))

    def test_user_template_dir_respected(self):
        d = self.call(self.w, extra={"GIT_TEMPLATE_DIR": "/mine"}, args=("init", "x"))
        self.assertEqual(d["TPL"], "/mine")

    def test_exec_path_always_ours(self):
        d = self.call(self.w, extra={"GIT_EXEC_PATH": "/other/git-core"})
        self.assertEqual(self.real(d["EXEC"]), self.real(os.path.join(self.root, "libexec", "git-core")))

    def test_symlink_loop_terminates(self):
        a = os.path.join(self.t, "loopa")
        b = os.path.join(self.t, "loopb")
        os.symlink(b, a)
        os.symlink(a, b)
        # 순환 링크는 커널이 실행 전에 거부한다(ELOOP) — 감싸개까지 오지 않음을 확인만 한다.
        with self.assertRaises(OSError):
            subprocess.run([a], capture_output=True, timeout=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
