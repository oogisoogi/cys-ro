#!/usr/bin/env python3
"""dbg-D3 #F1 검출 시험 — cys-dept 가 호출자가 준 cysd/cys 를 PATH 보강으로 덮지 않는가.

결함(2026-09-23 격리 실측): cys-dept 머리의 `export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"`
가 호출자 PATH **앞**에 끼워져, 바로 아래 `CYSD=$(command -v cysd)` · `CYS=$(command -v cys)` 가
틱(javis_dept_request._spawn_create 가 PATH 선두에 dirname(find_cysd) 를 둔다)이 고른 자기 판 바이너리가 아니라
그 보강 경로의 다른 판(옛 cys.app 을 가리키는 /usr/local/bin 링크 등)을 집는다 → 부서 데몬·부서 팩·부서 지침이
본부와 다른 판으로 선다.

재는 법: cys-dept 의 머리(첫 줄 ~ `CYS=` 줄)만 떼어 격리 HOME 에서 실행한다. `$HOME/.local/bin` 에 미끼 cysd·cys 를
두고 호출자 PATH 선두 폴더에 정답 cysd·cys 를 둔다. 정답이 이겨야 초록.
· `/usr/local/bin`·`/opt/homebrew/bin` 은 건드리지 않는다(시스템 경로 무접촉) — 미끼 자리는 같은 줄의 첫 항목
  `$HOME/.local/bin` 하나로 충분하다(세 항목이 같은 prepend 한 줄이다).
· 대조군: `--target <사본>` 으로 수리본을 겨누면 초록이어야 한다(검출 시험이 결함 없는 코드에선 초록인가).

종료코드: 0 = 초록 · 1 = 적색(결함 재현) · 2 = 측정 실패(머리 추출 실패 등 — 초록으로 접지 않는다).
"""
import os
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET = os.path.join(os.path.dirname(HERE), "cys-dept")


def head_of(target):
    with open(target, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("CYS=\"$(command -v cys"):
            return "\n".join(lines[: i + 1])
    return None


def mk_exe(path, tag):
    with open(path, "w") as f:
        f.write("#!/bin/sh\necho %s\n" % tag)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


def main(argv):
    target = DEFAULT_TARGET
    if len(argv) >= 2 and argv[0] == "--target":
        target = argv[1]
    head = head_of(target)
    if head is None:
        print("MEASURE-FAIL: cys-dept 머리(CYS= 줄)를 찾지 못했다 — 시험을 다시 겨눠라: %s" % target)
        return 2
    with tempfile.TemporaryDirectory() as td:
        home = os.path.join(td, "home")
        decoy = os.path.join(home, ".local", "bin")
        caller = os.path.join(td, "caller-bin")
        os.makedirs(decoy)
        os.makedirs(caller)
        for d, tag in ((decoy, "DECOY"), (caller, "CALLER")):
            mk_exe(os.path.join(d, "cysd"), tag)
            mk_exe(os.path.join(d, "cys"), tag)
        script = os.path.join(td, "head.sh")
        with open(script, "w", encoding="utf-8") as f:
            f.write(head + '\nprintf "%s\\n%s\\n" "$CYSD" "$CYS"\n')
        def run(env):
            p = subprocess.run(["/bin/bash", script], env=env, capture_output=True, text=True, timeout=20)
            out = p.stdout.strip().split("\n")
            if p.returncode != 0 or len(out) != 2:
                return None, "rc=%s out=%r err=%r" % (p.returncode, p.stdout, p.stderr[-300:])
            return out, None
        if not os.access(os.path.join(decoy, "cysd"), os.X_OK):
            print("MEASURE-FAIL: 미끼 부재")
            return 2
        want_d, want_c = os.path.join(caller, "cysd"), os.path.join(caller, "cys")
        fails = 0
        # 축 A — 호출자 PATH 선두의 판이 cys-dept 의 PATH 보강(~/.local/bin·brew·/usr/local/bin)에 덮이지 않는다.
        outA, err = run({"HOME": home, "PATH": caller + ":/usr/bin:/bin", "LANG": "C"})
        if outA is None:
            print("MEASURE-FAIL(A): " + err)
            return 2
        okA = outA == [want_d, want_c]
        print("[A] PATH 선두=호출자 → CYSD=%s CYS=%s  %s" % (outA[0], outA[1], "PASS" if okA else "FAIL"))
        fails += 0 if okA else 1
        # 축 B — 옛 판 cysd 가 PATH **선두**에 있어도 CYS_CYSD_BIN(틱이 명시 전달)이 이긴다(master 처방 1순위).
        outB, err = run({"HOME": home, "PATH": decoy + ":" + caller + ":/usr/bin:/bin", "LANG": "C",
                         "CYS_CYSD_BIN": want_d})
        if outB is None:
            print("MEASURE-FAIL(B): " + err)
            return 2
        okB = outB[0] == want_d
        print("[B] PATH 선두=옛 판 + CYS_CYSD_BIN → CYSD=%s  %s" % (outB[0], "PASS" if okB else "FAIL"))
        fails += 0 if okB else 1
        # 축 B 대조 — CYS_CYSD_BIN 없이 옛 판이 선두면 옛 판을 집는다(축 B 가 env 로 이긴 것이지 우연이 아님을 보인다).
        outB0, err = run({"HOME": home, "PATH": decoy + ":" + caller + ":/usr/bin:/bin", "LANG": "C"})
        if outB0 is None or outB0[0] != os.path.join(decoy, "cysd"):
            print("MEASURE-FAIL(B0): 대조군이 옛 판을 집지 않았다 %r %s" % (outB0, err or ""))
            return 2
        print("target=%s" % target)
        if fails:
            print("FAIL(#F1 재현): %d 축 — 부서 데몬이 본부와 다른 판으로 뜰 수 있다" % fails)
            return 1
        print("PASS: 부서 데몬 cysd = 호출자(본부) 판")
        return 0


def tick_passes_cysd(bin_dir):
    """축 C — 틱의 _spawn_create 가 cys-dept 자식 env 에 CYS_CYSD_BIN=find_cysd 결과를 싣는가(Popen 가로채기 · 실행 0)."""
    import importlib.util
    with tempfile.TemporaryDirectory() as td:
        os.environ["HOME"] = td
        spec = importlib.util.spec_from_file_location("jdr_probe", os.path.join(bin_dir, "javis_dept_request.py"))
        m = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(m)
        seen = {}

        class FakeP(object):
            pid = 0

        def fake_popen(args, **kw):
            seen["env"] = kw.get("env") or {}
            return FakeP()
        m.subprocess.Popen = fake_popen
        m.root_dir = lambda: td
        want = "/opt/example/cysr.app/Contents/MacOS/cysd"
        p, lf = m._spawn_create("k", want, 1)
        lf.close()
        got = seen.get("env", {}).get("CYS_CYSD_BIN")
        ok = got == want
        print("[C] 틱 → cys-dept env CYS_CYSD_BIN=%r  %s" % (got, "PASS" if ok else "FAIL"))
        return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    rc = main(a)
    bin_dir = os.path.dirname(a[1]) if len(a) >= 2 and a[0] == "--target" else os.path.dirname(DEFAULT_TARGET)
    if rc != 2 and not tick_passes_cysd(bin_dir):
        rc = 1
    sys.exit(rc)
