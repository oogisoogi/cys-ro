#!/usr/bin/env python3
"""ci_pack_steps.py — 로컬 게이트가 돌릴 팩 시험 단계를 `.github/workflows/ci-branch.yml` 에서 그대로 떼어 낸다.

왜: 로컬 게이트(gate-1116.sh)의 손 목록 21개가 CI 팩 단계와 갈려, 로컬 밖 151개가 CI 에서만 붉었다(11-19).
   목록을 손으로 맞추면 같은 사고가 다시 난다 → 정의는 워크플로 하나뿐이고, 게이트는 그 본문을 읽어 돌린다.

고르는 규칙(결정론): ci-branch.yml 의 모든 잡·스텝 중 `run:` 본문의 **주석 아닌 줄**에
   `cysjavis-pack/bin/` 또는 `scripts/ci/phoenix-host-gate.sh` 가 나오는 스텝.
   (팩 시험 파일·팩 스모크·건강 러너·phoenix 글롭 게이트 = 전부 이 두 낱말로 시작한다.)

본문은 한 글자도 바꾸지 않는다. 앞에 붙이는 것은 그 잡·스텝의 `env:`(문자 그대로의 값) export 뿐이다.
GitHub Actions 의 bash 스텝 = `bash --noprofile --norc -eo pipefail <파일>` — 게이트도 같은 꼴로 부른다.

판정 불가 = exit 3(조용한 통과 금지):
   · 고른 스텝 0개 · 잡 4개(macos-rust-pack·ubuntu-pack-suite·phoenix-host-gate·boot-health-full) 중 고른 스텝 0개인 잡
   · 고른 스텝에 `${{ … }}` 식 · `if:` · `working-directory:` · `shell:` 이 bash 아님 · 여러 줄 env 값
   · `run:` 이 `|`·`|-`·한 줄이 아닌 블록 스칼라(`>`·`>-`·`|+` 등 — 본문을 버리지 않게) · 워크플로/잡 `defaults:`(shell·폴더 재현 불가)
   CI 시한: 스텝 `timeout-minutes`(없으면 잡 `timeout-minutes`)를 생성물 머리 `# ci-timeout-secs: N` 으로 싣는다 — 게이트가 넘으면 붉힌다
   · 덮개 검사: 그 잡의 **고르지 않은** 스텝 본문(주석 아닌 줄)에 실재 팩 시험 파일 이름이 나온다
     = 고르는 규칙이 워크플로와 어긋남(새 꼴의 팩 스텝이 생김) → 규칙을 고칠 신호

사용:
   python3 docs/integ-1116/ci_pack_steps.py list            # 고른 스텝 목록(이름 · 잡 · 줄 · 시험 수)
   python3 docs/integ-1116/ci_pack_steps.py emit <폴더>      # 스텝마다 <폴더>/<이름>.sh · 목록은 표준 출력(한 줄에 이름 하나)
   python3 docs/integ-1116/ci_pack_steps.py names           # 고른 스텝 본문이 부르는 팩 시험 이름 전부(정렬)
   python3 docs/integ-1116/ci_pack_steps.py unregistered    # lane-parity-rehearsal.sh UNREGISTERED_OK 중 팩 시험 폴더에 실재하고
                                                            #   고른 CI 스텝이 부르지 않는 이름(= CI 0회 · 게이트가 따로 돌릴 몫)
   python3 docs/integ-1116/ci_pack_steps.py --self-test     # 음성 대조(가짜 워크플로)
환경: CI_PACK_YML(기본 = 저장소의 ci-branch.yml) · CI_PACK_ROOT(기본 = 이 파일 기준 저장소 뿌리)
"""
import glob
import os
import re
import shutil
import sys
import tempfile

ROOT = os.environ.get("CI_PACK_ROOT") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
YML = os.environ.get("CI_PACK_YML") or os.path.join(ROOT, ".github", "workflows", "ci-branch.yml")
PACK_TESTS = "cysjavis-pack/bin/tests"
MARKS = ("cysjavis-pack/bin/", "scripts/ci/phoenix-host-gate.sh")
JOBS = ("macos-rust-pack", "ubuntu-pack-suite", "phoenix-host-gate", "boot-health-full")


class Fail(Exception):
    pass


def code_lines(lines):
    return [l for l in lines if not l.lstrip().startswith("#")]


def parse(text):
    """ci-branch.yml 의 잡/스텝을 줄 단위로 읽는다(PyYAML 없이 · 이 저장소 워크플로의 들여쓰기 2/4/6/8/10 꼴)."""
    lines = text.splitlines()
    jobs, job, step, in_jobs, block = [], None, None, False, None
    for n, raw in enumerate(lines, 1):
        if raw.startswith("jobs:"):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if re.match(r"^defaults:", raw):
            raise Fail("줄 %d: 워크플로 defaults: — 게이트가 shell·폴더 기본값을 재현하지 못함" % n)
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*(#.*)?$", raw)
        if m:
            job = {"name": m.group(1), "env": {}, "steps": [], "timeout": None}
            jobs.append(job)
            step, block = None, None
            continue
        if job is None:
            continue
        if re.match(r"^    defaults:", raw):
            raise Fail("줄 %d: 잡 %s defaults: — 게이트가 shell·폴더 기본값을 재현하지 못함" % (n, job["name"]))
        m = re.match(r"^    timeout-minutes:\s*(\d+)\s*(#.*)?$", raw)
        if m:
            job["timeout"] = int(m.group(1))
            continue
        if re.match(r"^    env:\s*(#.*)?$", raw):
            block = ("jobenv", None)
            continue
        if block and block[0] == "jobenv":
            m = re.match(r"^      ([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", raw)
            if m:
                job["env"][m.group(1)] = m.group(2)
                continue
            if raw.strip() == "" or raw.lstrip().startswith("#"):
                continue
            block = None
        if re.match(r"^    [a-z-]+:", raw):
            block = None
            step = None
            continue
        line = raw
        if re.match(r"^      - ", raw):
            step = {"job": job["name"], "line": n, "keys": {}, "run": [], "env": {}}
            job["steps"].append(step)
            line = "        " + raw[8:]
            block = None
        if step is None:
            continue
        m = re.match(r"^        ([a-z-]+):\s*(.*)$", line)
        if m:
            k, v = m.group(1), m.group(2)
            step["keys"][k] = v
            block = None
            if k == "run":
                vv = re.sub(r"\s+#.*$", "", v).strip()
                if vv in ("|", "|-"):
                    block = ("run", None)
                elif vv[:1] in (">", "|"):
                    raise Fail("줄 %d: run: %s 블록 스칼라 — 지원하지 않음(본문을 버리지 않게 fail-closed)" % (n, vv))
                elif v:
                    step["run"].append(v)
            elif k == "env":
                if v and v != "":
                    raise Fail("줄 %d: 한 줄 env(%s) — 판독 불가" % (n, v))
                block = ("env", None)
            continue
        if block and block[0] == "run":
            if raw.startswith("          ") or raw.strip() == "":
                step["run"].append(raw[10:])
                continue
            block = None
        if block and block[0] == "env":
            m = re.match(r"^          ([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", raw)
            if m:
                step["env"][m.group(1)] = m.group(2)
                continue
            if raw.strip() == "" or raw.lstrip().startswith("#"):
                continue
            block = None
    for j in jobs:
        for s in j["steps"]:
            while s["run"] and s["run"][-1].strip() == "":
                s["run"].pop()
    return jobs


def scalar(v, where):
    v = re.sub(r"\s+#.*$", "", v).strip()
    if "${{" in v:
        raise Fail("%s: env 값에 ${{ }} 식" % where)
    if v in ("|", ">", "|-", ">-"):
        raise Fail("%s: 여러 줄 env 값" % where)
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    return v


def slug(s):
    t = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return t or "step"


def pack_test_names(root):
    return {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(root, PACK_TESTS, "test_*.py"))}


def tokens(lines):
    out = set()
    for l in code_lines(lines):
        out |= set(re.findall(r"\btest_[a-z0-9_]+", l))
    return out


def indirect(run, root, real):
    """본문이 부르는 팩 시험 — 이름 토큰 + 글롭(`test_phoenix_*.py`) 전개 + 본문이 부르는 팩 러너 파일
    (`run_bootstrap_health.py` 처럼 test_ 가 아닌 .py)이 이름으로 부르는 시험."""
    out = tokens(run) & real
    body = "\n".join(code_lines(run))
    for pat in re.findall(r"cysjavis-pack/bin/tests/(test_[a-z0-9_]*\*\.py)", body):
        out |= {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(root, PACK_TESTS, pat))}
    for f in set(re.findall(r"cysjavis-pack/bin/tests/([a-z0-9_]+\.py)", body)):
        if f.startswith("test_"):
            continue
        fp = os.path.join(root, PACK_TESTS, f)
        if os.path.isfile(fp):
            out |= tokens(open(fp, encoding="utf-8").read().splitlines()) & real
    return out


def select(text, root):
    jobs = parse(text)
    real = pack_test_names(root)
    chosen, per_job = [], {j: 0 for j in JOBS}
    problems = []
    for j in jobs:
        for s in j["steps"]:
            body = code_lines(s["run"])
            hit = any(mk in l for l in body for mk in MARKS)
            if not hit:
                stray = tokens(s["run"]) & real
                if j["name"] in JOBS and stray and "uses" not in s["keys"]:
                    problems.append("덮개: %s 줄 %d(%s)이 팩 시험 %s 를 부르는데 고르는 규칙에 안 걸림"
                                    % (j["name"], s["line"], (s["keys"].get("name") or "")[:50], sorted(stray)[:5]))
                continue
            name = s["keys"].get("name") or ""
            where = "%s 줄 %d" % (j["name"], s["line"])
            for bad in ("if", "working-directory"):
                if bad in s["keys"]:
                    problems.append("%s: `%s:` 가 있는 스텝 — 조건·폴더를 게이트가 재현하지 못함" % (where, bad))
            sh = s["keys"].get("shell", "bash").strip()
            if sh != "bash":
                problems.append("%s: shell=%s(bash 아님)" % (where, sh))
            if any("${{" in l for l in s["run"]):
                problems.append("%s: 본문에 ${{ }} 식" % where)
            env = {}
            for k, v in list(j["env"].items()) + list(s["env"].items()):
                env[k] = scalar(v, "%s env %s" % (where, k))
            tm = s["keys"].get("timeout-minutes", "").strip()
            limit = int(tm) * 60 if tm.isdigit() else (j["timeout"] * 60 if j["timeout"] else None)
            chosen.append({"job": j["name"], "line": s["line"], "name": name, "run": s["run"], "env": env, "timeout": limit,
                           "id": "ci-%s-L%d" % (slug(j["name"]), s["line"]),
                           "tests": sorted(indirect(s["run"], root, real))})
            if j["name"] in per_job:
                per_job[j["name"]] += 1
    if not chosen:
        problems.append("고른 스텝 0개")
    for j, c in per_job.items():
        if c == 0:
            problems.append("잡 %s 에서 고른 스텝 0개(잡 이름·구조가 바뀜?)" % j)
    if problems:
        raise Fail("\n".join(problems))
    return chosen


def render(s):
    out = ["# 생성물 — docs/integ-1116/ci_pack_steps.py · 원본 = .github/workflows/ci-branch.yml %s 줄 %d"
           % (s["job"], s["line"]),
           "# 스텝 이름: %s" % s["name"],
           "# ci-timeout-secs: %s" % (s["timeout"] if s["timeout"] else "")]
    for k, v in s["env"].items():
        out.append("export %s=%s" % (k, "'" + v.replace("'", "'\\''") + "'"))
    out.extend(s["run"])
    return "\n".join(out) + "\n"


def unregistered(root):
    p = os.path.join(root, "scripts", "lane-parity-rehearsal.sh")
    text = open(p, encoding="utf-8").read()
    names = set(re.findall(r'^UNREGISTERED_OK\["(test_[a-z0-9_]+)"\]', text, re.M))
    m = re.search(r"^UNREGISTERED_OK = \{n: _BASELINE for n in \((.*?)\)\}", text, re.M | re.S)
    if not m:
        raise Fail("lane-parity-rehearsal.sh 에서 UNREGISTERED_OK 기준선 묶음을 못 찾음")
    names |= set(re.findall(r'"(test_[a-z0-9_]+)"', m.group(1)))
    return sorted(names & pack_test_names(root))


def self_test():
    tmp = tempfile.mkdtemp(prefix="cps")
    try:
        os.makedirs(os.path.join(tmp, PACK_TESTS))
        for t in ("test_a", "test_b", "test_c"):
            open(os.path.join(tmp, PACK_TESTS, t + ".py"), "w").close()
        good = """jobs:
  macos-rust-pack:
    runs-on: macos-latest
    steps:
      - uses: x
      - name: one
        shell: bash
        run: |
          # test_c 주석은 세지 않는다
          for t in test_a test_b; do python3 cysjavis-pack/bin/tests/$t.py; done
      - name: other
        run: echo hi
  ubuntu-pack-suite:
    runs-on: ubuntu-latest
    steps:
      - name: u
        env:
          FOO: 'b a r'
        run: |
          python3 cysjavis-pack/bin/tests/test_a.py
  phoenix-host-gate:
    timeout-minutes: 30
    env:
      PYTHONUTF8: '1'   # note
    steps:
      - name: p
        run: bash scripts/ci/phoenix-host-gate.sh x
  boot-health-full:
    steps:
      - name: h
        run: |
          python3 cysjavis-pack/bin/tests/run_bootstrap_health.py
"""
        ch = select(good, tmp)
        assert [c["id"] for c in ch] == ["ci-macos-rust-pack-L6", "ci-ubuntu-pack-suite-L16",
                                          "ci-phoenix-host-gate-L26", "ci-boot-health-full-L30"], [c["id"] for c in ch]
        assert ch[0]["tests"] == ["test_a", "test_b"], ch[0]["tests"]
        assert ch[1]["env"] == {"FOO": "b a r"}, ch[1]["env"]
        assert ch[2]["env"] == {"PYTHONUTF8": "1"}, ch[2]["env"]
        assert ch[2]["timeout"] == 1800 and ch[0]["timeout"] is None, (ch[2]["timeout"], ch[0]["timeout"])
        assert "# ci-timeout-secs: 1800\n" in render(ch[2])
        r = render(ch[0])
        assert "for t in test_a test_b; do python3 cysjavis-pack/bin/tests/$t.py; done\n" in r
        assert "# test_c 주석은 세지 않는다" in r
        bad = {
            "덮개": good.replace("run: echo hi", "run: python3 other/test_c.py"),
            "${{": good.replace("python3 cysjavis-pack/bin/tests/test_a.py", "python3 cysjavis-pack/bin/tests/${{ x }}.py"),
            "`if:`": good.replace("      - name: u\n", "      - name: u\n        if: always()\n"),
            "잡 boot-health-full": good.replace("cysjavis-pack/bin/tests/run_bootstrap_health.py", "x.py"),
            "shell=pwsh": good.replace("        shell: bash\n", "        shell: pwsh\n"),
            "블록 스칼라": good.replace("      - name: u\n        env:\n          FOO: 'b a r'\n        run: |", "      - name: u\n        env:\n          FOO: 'b a r'\n        run: >"),
            "defaults": good.replace("  ubuntu-pack-suite:\n    runs-on: ubuntu-latest\n", "  ubuntu-pack-suite:\n    runs-on: ubuntu-latest\n    defaults:\n      run:\n        shell: sh\n"),
        }
        for want, text in bad.items():
            try:
                select(text, tmp)
            except Fail as e:
                assert want in str(e), (want, str(e))
            else:
                raise AssertionError("음성 대조가 통과함: " + want)
        print("[ci_pack_steps self-test] OK(양성 1 · 음성 %d)" % len(bad))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    if argv[:1] == ["--self-test"]:
        return self_test()
    if not argv or argv[0] not in ("list", "emit", "names", "unregistered"):
        sys.stderr.write(__doc__)
        return 2
    try:
        ch = select(open(YML, encoding="utf-8").read(), ROOT)
        if argv[0] == "unregistered":
            covered = {t for c in ch for t in c["tests"]}
            print("\n".join(n for n in unregistered(ROOT) if n not in covered))
            return 0
    except (Fail, OSError) as e:
        sys.stderr.write("[ci_pack_steps] 판정 불가 — %s\n" % e)
        return 3
    if argv[0] == "list":
        for c in ch:
            print("%-28s %-18s %3d개  %s" % (c["id"], c["job"], len(c["tests"]), c["name"][:70]))
        print("고른 스텝 %d개 · 부르는 팩 시험(이름 기준 · 중복 제외) %d개"
              % (len(ch), len({t for c in ch for t in c["tests"]})))
        return 0
    if argv[0] == "names":
        print("\n".join(sorted({t for c in ch for t in c["tests"]})))
        return 0
    if len(argv) != 2:
        sys.stderr.write("emit <폴더>\n")
        return 2
    os.makedirs(argv[1], exist_ok=True)
    for c in ch:
        with open(os.path.join(argv[1], c["id"] + ".sh"), "w", encoding="utf-8") as f:
            f.write(render(c))
        print(c["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
