#!/usr/bin/env python3
"""test_dept_name_guard.py — cys-dept 이름 검증·A11 dedupe·승격 영수증·demote 경보 핀 (v4 스펙 §D3(i)·A11·A6·G0 D3/D10).

`launch --help` 실사고(문자 이름 '--help' 유령 부서 등재→껍데기 CEO 승격) 봉합의 회귀 핀.
격리 HOME + 목 cys/cysd($HOME/.local/bin — cys-dept PATH prepend 1순위)로 실 데몬 무접촉:
  1) 수용/거부표 — 화이트리스트 ^[A-Za-z0-9][A-Za-z0-9_-]*$·≤40자. 경계: 빈·'-'선두·'.'포함·
     41자·한글·공백·'/'. 거부=exit 2+부작용 0(state/pack 디렉토리·레지스트리 등재 부재).
  2) cmd 위치 --help/-h = usage(stdout·exit 0·부작용 0) / name 위치 --help = exit 2·부작용 0.
  3) create — key 화이트리스트(카탈로그 존재 검사보다 선행)·3분기 공통 관문(REUSE 비정형 등재
     exit 2+자동 삭제 금지)·NEW 정상 경로 무회귀(stdout 마지막 줄=name).
  4) rotate — 등재된 비정형명은 kill 이전 exit 2(cys 호출 0·소켓 불변 = graceful_kill 미도달).
     ※ kill은 bash builtin이라 PATH 목 로깅 불가 — '검증이 ping/identify(kill 선행 단계)보다
     앞에서 끊는다'를 cys 호출 0+소켓 잔존으로 단언(동등 증거).
  5) CYS_DEPT_ROTATE=1이어도 launch 검증 유지.
  6) passthrough — 실존(비정형 포함) 통과 / 비실존·정형 통과+CYS_NO_AUTOSTART=1(G0 D10) /
     비실존·비정형 exit 2. sock 동사 '-' 선두 exit 2(레거시 비정형 등재명은 fan-out 호환 통과).
  7) 인자 위생 — cys tombstone 호출이 `--dept [--remove] -- <name>`(clap `--` 종단) 형식.
  8) 기존명 재-launch 통과(slug-fold 자기 제외) / slug 충돌쌍(대소·'.'-fold) 거부.
  9) 승격 영수증 — promote 시 directives/.ceo-template-applied=적용 템플릿 sha256, 강등 시 삭제.
 10) demote 무음 경보 — 승격 표지+.pre-ceo 부재='강등 불능' stderr 경보+feed push(비대기),
     미승격 머신은 무경보(위경보 금지).
 11) A11 — promote-if-pending --request-only가 미해결 동종(제목 'CEO 승격 대기') pending 존재 시
     push 생략(로그 1줄), 부재 시 발행.
"""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile

# ★T10(DCE-3) 픽스처 계약: CEO 템플릿 = MASTER 전문의 상위집합(합성 계약 동형) — 스왑 직전
#   런타임 상위집합 검사를 통과해야 승격 계열 테스트가 승격 상태에 도달한다.
CEO_BODY = "CEO-HEADER\n---\nSTANDARD-MASTER\n"
import time
import unittest

SELF = os.path.dirname(os.path.abspath(__file__))
DEPT = os.path.join(SELF, "..", "cys-dept")
# ★v116-pack(CSO 실측 2026-09-24 · 시험 cysd 누수): 이 실행의 임시 폴더는 전부 RUN_ROOT 아래 — 케이스마다
#   띄운 프로세스 회수·폴더 삭제(Base._cleanup) + 모듈 끝 「잔존 0」 단언(tearDownModule)의 범위가 된다.
RUN_ROOT = tempfile.mkdtemp(prefix="deptguard-run-")


def _pids_holding(root, deep=False):
    """root 아래 파일을 열어 둔(또는 그 안이 작업 폴더인) 프로세스 pid — 이 시험이 띄운 데몬의 표지.
    cys-dept 는 데몬 출력을 $HOME(=root 아래)/.local/state/cys-dept-*/…/cysd.log 로 돌리므로 진짜·목 데몬
    어느 쪽이든 잡힌다. Linux = /proc(fd·cwd) · 그 밖 = lsof. 자기 자신은 제외.
    deep=True(모듈 끝 안전망) = 폴더가 이미 지워져 +D 로 못 찾는 경우까지 — 전 프로세스 열린 경로를 접두 대조."""
    root = os.path.realpath(root)
    me = os.getpid()
    found = set()
    if os.path.isdir("/proc/self/fd"):
        for pid in os.listdir("/proc"):
            if not pid.isdigit() or int(pid) == me:
                continue
            links = []
            try:
                links.append(os.readlink("/proc/%s/cwd" % pid))
                fd = "/proc/%s/fd" % pid
                links += [os.readlink(os.path.join(fd, x)) for x in os.listdir(fd)]
            except OSError:
                continue
            if any(l == root or l.startswith(root + os.sep) for l in links):
                found.add(int(pid))
        return sorted(found)
    if deep:
        try:
            r = subprocess.run(["lsof", "-Fpn"], capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            return []
        pid = None
        for line in r.stdout.splitlines():
            if line.startswith("p"):
                pid = int(line[1:]) if line[1:].isdigit() else None
            elif line.startswith("n") and pid and pid != me and (
                    line[1:] == root or line[1:].startswith(root + os.sep)):
                found.add(pid)
        return sorted(found)
    try:
        r = subprocess.run(["lsof", "-t", "+D", root], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return sorted({int(x) for x in r.stdout.split() if x.isdigit() and int(x) != me})


def _reap(root, deep=False):
    """root 를 쥔 프로세스를 TERM → (3초) → KILL. 반환 = 처음 발견한 pid 목록."""
    pids = _pids_holding(root, deep)
    for p in pids:
        try:
            os.kill(p, signal.SIGTERM)
        except OSError:
            pass
    deadline = time.time() + 3
    while pids and time.time() < deadline and _pids_holding(root, deep):
        time.sleep(0.1)
    for p in _pids_holding(root, deep):
        try:
            os.kill(p, signal.SIGKILL)
        except OSError:
            pass
    return pids


def tearDownModule():
    # 「이 실행이 띄운 데몬 잔존 0」 — 케이스 정리(Base._cleanup)가 빠뜨린 것이 있으면 회수한 뒤 적색.
    left = _pids_holding(RUN_ROOT, deep=True)
    _reap(RUN_ROOT, deep=True)
    shutil.rmtree(RUN_ROOT, ignore_errors=True)
    if left:
        raise AssertionError("시험이 띄운 프로세스가 끝나지 않고 남음(누수): pid=%s" % left)


def _write_exec(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.chmod(path, 0o755)


def make_home(tmp):
    """격리 HOME + 목 cys/cysd. cys ping은 CYS_SOCKET 파일 실존으로 생사 재현(죽은 소켓=exit 1 —
    allocate/create lowest-unused 루프가 '모든 소켓 생존' 목에서 무한루프하는 픽스처 결함 방지)."""
    home = os.path.join(tmp, "home")
    bindir = os.path.join(home, ".local", "bin")
    os.makedirs(bindir, exist_ok=True)
    os.makedirs(os.path.join(home, ".cys"), exist_ok=True)
    log = os.path.join(tmp, "calls.log")
    feedlist = os.path.join(tmp, "feed-list.txt")
    _write_exec(os.path.join(bindir, "cys"),
                '#!/bin/sh\n'
                'echo "cys $@" >> "%(log)s"\n'
                'case "$1" in\n'
                '  ping) [ -e "$CYS_SOCKET" ] && exit 0 || exit 1 ;;\n'
                '  status) exit 1 ;;\n'
                '  identify) exit 1 ;;\n'
                '  feed) if [ "$2" = "list" ]; then [ -f "%(fl)s" ] && cat "%(fl)s"; exit 0; fi; exit 0 ;;\n'
                '  list) exit 0 ;;\n'
                'esac\nexit 0\n' % {"log": log, "fl": feedlist})
    # 목 cysd: 소켓 파일 생성 후 즉시 종료(ready()의 ping 파일-실존 프로브와 정합).
    _write_exec(os.path.join(bindir, "cysd"),
                '#!/bin/sh\nmkdir -p "$(dirname "$CYS_SOCKET")"\ntouch "$CYS_SOCKET"\nexit 0\n')
    return home, log, feedlist


def make_env(home):
    env = dict(os.environ)
    # ★v116-pack: 상속 CYS_* 는 전부 지운다(아래 update 전에). 종전 목록은 CYS_CYSD_BIN·CYS_CYS_BIN(cys-dept 1순위 ·
    #   1.1.5 데몬이 좌석 env 로 주입)을 빠뜨려, 좌석 안에서 돌리면 목 대신 /Applications 의 진짜 cysd·cys 가 격리
    #   HOME 에서 떠 끝나지 않았다(09-24 18기 누수 · 이 시험 적색 8건의 원인). 필요한 CYS_* 는 각 시험이 명시로 넣는다.
    for k in [k for k in env if k.startswith("CYS_")]:
        env.pop(k, None)
    env.update({"HOME": home,
                "CYS_DEPTS_JSON": os.path.join(home, ".cys", "depts.json"),
                "PATH": os.path.join(home, ".local", "bin") + os.pathsep + env.get("PATH", "")})
    return env


def write_reg(env, depts):
    with open(env["CYS_DEPTS_JSON"], "w", encoding="utf-8") as f:
        json.dump({"depts": depts}, f, ensure_ascii=False)


def read_reg(env):
    try:
        return json.load(open(env["CYS_DEPTS_JSON"], encoding="utf-8")).get("depts", {})
    except (OSError, ValueError):
        return {}


def seed_sock(home, name):
    """부서 소켓 파일 시드 — 목 ping이 '가동 중(재사용)'으로 판정(launch가 cysd spawn 없이 완주)."""
    d = os.path.join(home, ".local", "state", "cys-dept-%s" % name)
    os.makedirs(d, exist_ok=True)
    sock = os.path.join(d, "cys.sock")
    open(sock, "w").close()
    return sock


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="deptguard-", dir=RUN_ROOT)
        self.addCleanup(self._cleanup)  # 예외·실패 경로에서도 돈다(setUp 이후 전부)
        self.home, self.log, self.feedlist = make_home(self.tmp)
        self.env = make_env(self.home)

    def _cleanup(self):
        """이 케이스가 띄운 프로세스(데몬 등) 회수 + 임시 폴더 삭제."""
        _reap(self.tmp)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_dept(self, *args, env=None):
        r = subprocess.run(["bash", DEPT] + list(args), capture_output=True, text=True,
                           encoding="utf-8", env=env or self.env, timeout=60)
        return r.returncode, r.stdout, r.stderr

    def calls(self):
        return open(self.log, encoding="utf-8").read() if os.path.exists(self.log) else ""

    def assert_no_side_effects(self, name):
        self.assertFalse(os.path.exists(os.path.join(
            self.home, ".local", "state", "cys-dept-%s" % name)),
            "거부됐는데 state 디렉토리 생성(%s)" % name)
        self.assertFalse(os.path.exists(os.path.join(
            self.home, ".cys", "pack-dept-%s" % name)),
            "거부됐는데 pack 디렉토리 생성(%s)" % name)
        self.assertNotIn(name, read_reg(self.env), "거부됐는데 레지스트리 등재(%s)" % name)

    def _seed_promotable(self, ndepts=1):
        """승격 가능 상태 시드: 디렉티브 쌍 + 부트 마커 + 부서 n개(승격·강등·A11 계열 공용).
        ★T10(DCE-3): CEO 템플릿은 합성 계약(머리글+구분선+MASTER 전문 verbatim)과 동형인
        **상위집합**이어야 스왑 직전 런타임 검사를 통과한다(스텁 픽스처는 보류가 정답 —
        test_ceo_pending_gate #7이 그 축을 핀)."""
        pack = os.path.join(self.home, ".cys", "pack", "directives")
        os.makedirs(pack, exist_ok=True)
        with open(os.path.join(pack, "MASTER_DIRECTIVE.md"), "w", encoding="utf-8") as f:
            f.write("STANDARD-MASTER\n")
        with open(os.path.join(pack, "CEO_TEMPLATE.md"), "w", encoding="utf-8") as f:
            f.write(CEO_BODY)
        with open(os.path.join(self.home, ".cys", ".master-bootstrapped"), "w") as f:
            f.write("{}")
        write_reg(self.env, {("d%d" % i): {"socket": "", "pack_dir": ""}
                             for i in range(ndepts)})
        return pack

    def _receipt(self):
        return os.path.join(self.home, ".cys", "pack", "directives", ".ceo-template-applied")


class AcceptRejectTable(Base):
    # 1) 거부표: 경계 이름 전부 exit 2 + 부작용 0 (launch = 부작용-이전 검증의 대표 생성 동사)
    def test_reject_table_exit2_no_side_effects(self):
        for bad in ["", "-x", "--help", "-h", "a.b", ".x", "a" * 41, "한글부서", "a b", "a/b", "a..b"]:
            rc, out, err = self.run_dept("launch", bad)
            self.assertEqual(rc, 2, "launch %r: exit=%d(≠2)\n%s" % (bad, rc, err))
            self.assertIn("usage: cys-dept launch", err,
                          "launch %r: 거부 진단에 동사 usage 1줄 부재" % bad)
            if bad and "/" not in bad:
                self.assert_no_side_effects(bad)
        # 레지스트리 파일 자체가 안 생겼어야 한다(검증이 reg_init보다 앞 = 부작용-이전)
        self.assertFalse(os.path.exists(self.env["CYS_DEPTS_JSON"]),
                         "거부만 했는데 depts.json 생성(검증이 부작용 이전이 아님)")

    # 1) 수용표: 정형 이름은 launch 완주(소켓 시드=재사용 경로·exit 0)
    def test_accept_table_launch_ok(self):
        write_reg(self.env, {})
        for good in ["a", "A-1_b", "x" * 40, "dept-1", "Z9"]:
            seed_sock(self.home, good)
            rc, out, err = self.run_dept("launch", good)
            self.assertEqual(rc, 0, "launch %r: exit=%d(≠0)\n%s%s" % (good, rc, out, err))
            self.assertIn(good, read_reg(self.env), "수용 이름 미등재(%s)" % good)


class HelpContract(Base):
    # 2) cmd 위치 --help/-h = usage(stdout)·exit 0·부작용 0 — 단일소유 가드(exit 7)보다 앞(역할 무관)
    def test_cmd_help_usage_stdout_exit0(self):
        for flag in ("--help", "-h"):
            rc, out, err = self.run_dept(flag)
            self.assertEqual(rc, 0, "%s: exit=%d(≠0)" % (flag, rc))
            self.assertIn("usage: cys-dept", out, "%s: usage가 stdout이 아님" % flag)
        # 역할 무관(가드 이전): CYS_ROLE=master여도 usage exit 0
        env = dict(self.env); env["CYS_ROLE"] = "master"
        rc, out, _ = self.run_dept("--help", env=env)
        self.assertEqual(rc, 0, "role=master cmd --help가 가드에 걸림(exit=%d)" % rc)
        self.assertIn("usage: cys-dept", out)
        self.assertFalse(os.path.exists(self.env["CYS_DEPTS_JSON"]), "--help가 부작용 발생")

    # 2) name 위치 --help = 검증 거부 exit 2 (usage 아님 — 실사고 재발 차단 핵심 핀)
    def test_name_position_help_rejected(self):
        rc, out, err = self.run_dept("launch", "--help")
        self.assertEqual(rc, 2)
        self.assertNotIn("usage: cys-dept <verb>", out, "name 위치 --help가 전체 usage로 오응답")
        self.assert_no_side_effects("--help")


class CreateGate(Base):
    def _seed_catalog(self, key, mkey):
        acct = os.path.join(self.home, "acct")
        os.makedirs(acct, exist_ok=True)
        cat = os.path.join(self.home, ".cys", "dept-catalog.json")
        with open(cat, "w", encoding="utf-8") as f:
            json.dump({"accounts": {"test": acct},
                       "departments": {key: {"display": "테스트부", "account": "test",
                                             "mission_key": mkey, "cwd": self.home}}},
                      f, ensure_ascii=False)
        # seed_agents_account 소스(메인 팩 agents.json — env 맵 구조)
        pack = os.path.join(self.home, ".cys", "pack")
        os.makedirs(pack, exist_ok=True)
        with open(os.path.join(pack, "agents.json"), "w", encoding="utf-8") as f:
            json.dump({"claude": {"cmd": "claude", "env": {"CLAUDE_CONFIG_DIR": "/base"}}}, f)

    # 3) key 화이트리스트 — 카탈로그 존재 검사(exit 3)보다 선행: 부적격 key는 카탈로그 없이도 exit 2
    def test_create_key_whitelist_before_catalog(self):
        for bad in ("bad.key", "--help", ""):
            rc, out, err = self.run_dept("create", bad)
            self.assertEqual(rc, 2, "create %r: exit=%d(≠2)\n%s" % (bad, rc, err))
            self.assertIn("usage: cys-dept create", err)

    # 3) 3분기 공통 관문: REUSE(mission_key 매칭 기존 엔트리)가 비정형이면 exit 2·자동 삭제 금지
    def test_create_reuse_nonconforming_reported_not_deleted(self):
        self._seed_catalog("k1", "m1")
        write_reg(self.env, {"we.ird": {"socket": os.path.join(self.home, "nosock"),
                                        "pack_dir": "", "mission_key": "m1",
                                        "reserved_at": time.time()}})
        rc, out, err = self.run_dept("create", "k1")
        self.assertEqual(rc, 2, "REUSE 비정형 등재인데 exit=%d(≠2)\n%s%s" % (rc, out, err))
        self.assertIn("비정형 등재", err, "비정형 등재 stderr 보고 부재")
        self.assertIn("we.ird", read_reg(self.env), "자동 삭제 금지 위반 — REUSE 엔트리 소실")

    # 3) NEW 정상 경로 무회귀: 관문이 정상 create를 막지 않는다(stdout 마지막 줄=name)
    def test_create_new_happy_path(self):
        self._seed_catalog("k2", "m2")
        write_reg(self.env, {})
        rc, out, err = self.run_dept("create", "k2")
        self.assertEqual(rc, 0, "정상 create 실패: exit=%d\n%s%s" % (rc, out, err))
        self.assertEqual(out.strip().splitlines()[-1], "dept-1", "stdout 마지막 줄=name 계약 위반")
        self.assertIn("dept-1", read_reg(self.env))


class RotateGuard(Base):
    # 4) 등재된 비정형명 rotate: kill 이전 exit 2 — cys 호출 0(ping/identify는 kill 선행 단계)·소켓 불변
    def test_rotate_precheck_before_kill(self):
        sock = seed_sock(self.home, "we.ird")
        write_reg(self.env, {"we.ird": {"socket": sock, "pack_dir": ""}})
        rc, out, err = self.run_dept("rotate", "we.ird")
        self.assertEqual(rc, 2, "rotate 비정형 등재인데 exit=%d(≠2)\n%s" % (rc, err))
        self.assertIn("kill 미수행", err, "kill 미수행 안내 부재")
        self.assertIn("down-sock", err, "down-sock/수동 정리 안내 부재")
        self.assertNotIn("ping", self.calls(), "검증 이전에 데몬 프로브(ping) 발생 — kill 경로 진입 의심")
        self.assertTrue(os.path.exists(sock), "kill 이전 거부인데 소켓 소실(rm 도달 = half-op)")
        self.assertIn("we.ird", read_reg(self.env), "rotate 거부가 등재를 파괴")

    # 4) 미등재 rotate는 기존 계약 유지(등재 게이트 exit 8 — 검증은 게이트 직후)
    def test_rotate_unregistered_still_exit8(self):
        write_reg(self.env, {})
        rc, out, err = self.run_dept("rotate", "ghost")
        self.assertEqual(rc, 8, "미등재 rotate exit=%d(≠8 — 기존 부활 금지 계약 회귀)" % rc)

    # 5) CYS_DEPT_ROTATE=1(rotate 재귀 신호)이어도 launch 검증 유지
    def test_launch_validates_even_under_rotate_env(self):
        write_reg(self.env, {"we.ird": {"socket": "", "pack_dir": ""}})
        env = dict(self.env); env["CYS_DEPT_ROTATE"] = "1"
        rc, out, err = self.run_dept("launch", "we.ird", env=env)
        self.assertEqual(rc, 2, "CYS_DEPT_ROTATE=1에서 launch 검증 우회(exit=%d)" % rc)


def _wait_lock_opener(lock_path, timeout=20.0):
    """다른 프로세스가 레지스트리 잠금 파일을 **열었음**(= 셸 빠른 길을 지나 잠금 블록에 들어서 flock 대기)을 lsof 로
    관측할 때까지 기다린다 — 시간 대기·자식 생존 추정 대신 실제 진입 신호(codex 4R)."""
    end = time.time() + timeout
    me = str(os.getpid())
    while time.time() < end:
        r = subprocess.run(["lsof", "-t", lock_path], capture_output=True, text=True)
        if any(x != me for x in r.stdout.split()):
            return True
        time.sleep(0.05)
    return False


def _make_winlock_sim(sim_dir, counter=False):
    """윈 잠금 실패 흉내 폴더(PYTHONPATH 로 끼움) — **sitecustomize 로 주입**한다. 가짜 msvcrt.py 를 모듈 파일로 두면
    파이썬 3.14 의 subprocess 가 `import msvcrt` 성공을 윈도 판정으로 삼아 try 밖에서 `import _winapi` 를 해 맥에서 즉사한다
    (3.9 는 같은 try 로 삼킴 — 해석기 판에 따라 갈림 · master#0a5cd587 실측). 그래서 표준 라이브러리를 **먼저** 실제
    플랫폼으로 불러 두고, 그 뒤에 sys.modules 에 fcntl=None(= import 실패)·가짜 msvcrt 를 넣어 cys-dept 블록의 import 만
    흉내에 걸리게 한다. counter=True = N번째 잠금부터 실패(SIMLOCK_COUNTER·SIMLOCK_FAIL_AT · 블록마다 새 프로세스라 파일)."""
    os.makedirs(sim_dir, exist_ok=True)
    body = (
        "import sys, types, os\n"
        "import subprocess, tempfile, socket, shutil, getpass, selectors  # 실제 플랫폼 판정을 먼저 굳힌다\n"
        "sys.modules['fcntl'] = None\n"
        "_m = types.ModuleType('msvcrt'); _m.LK_LOCK = 1; _m.LK_UNLCK = 0\n"
    )
    if counter:
        body += (
            "def _locking(fd, mode, n):\n"
            "    c = os.environ['SIMLOCK_COUNTER']\n"
            "    k = int(open(c).read() or 0) if os.path.exists(c) else 0\n"
            "    open(c, 'w').write(str(k + 1))\n"
            "    if k >= int(os.environ['SIMLOCK_FAIL_AT']):\n"
            "        raise OSError(36, 'sim: lock timeout')\n"
        )
    else:
        body += "def _locking(fd, mode, n):\n    raise OSError(36, 'sim: lock timeout')\n"
    body += "_m.locking = _locking\nsys.modules['msvcrt'] = _m\n"
    with open(os.path.join(sim_dir, "sitecustomize.py"), "w") as f:
        f.write(body)
    return sim_dir


def _dept_py_block(header):
    """cys-dept 안 `header` 가 든 줄에서 시작하는 인용 heredoc(<<'PY' … PY) 파이썬 본문을 그대로 떼어 낸다."""
    src = open(DEPT, encoding="utf-8").read()
    i = src.index(header)
    j = src.index("<<'PY'\n", i) + len("<<'PY'\n")
    k = src.index("\nPY\n", j)
    return src[j:k + 1]


class WinLockFailure(unittest.TestCase):
    """1.1.7 fix-blockers A1-F3 · master#6e5aef09·af0da6d9 판정 A: 윈도 레지스트리 잠금(msvcrt) 실패를 삼키고 무잠금으로
    진행하던 5곳 = 「잠금 실패 = 읽지도 쓰지도 않음 · exit 11 다시 시도」(선례 = 울타리·예약 블록). 0바이트 규칙과 결합하면
    무잠금 판독이 쓰는 중인 목록을 「등록 없음」 으로 보아 등록을 지우는 경로가 되므로(데이터 손실 가족) 막는다.
    흉내: fcntl 부재 + msvcrt.locking 이 OSError(10초 재시도 뒤 실패와 같은 모양) — _make_winlock_sim(해석기 판 무관)."""

    TARGETS = {                                   # header → 인자(REG 뒤)
        "reg_upsert(){": ["d1", "/s", "/k"],
        "reg_remove(){": ["keep1"],
        "reg_set_meta(){": ["keep1", "표시", "acct"],
        "reg_set_field(){": ["keep1", "gen", "g1"],
        "snap=$(python3 - \"$REG\" <<'PY'": [],   # reap 스냅샷(읽기 전용)
    }
    CONTROLS = {                                  # 이미 exit 11 인 선례(흉내가 실제로 잠금 실패를 만드는지 대조)
        "reg_fence_close(){": ["keep1", ""],
        "name=$(reg_init; python3 - \"$REG\" <<'PY'": [],                          # allocate 예약
        "res=$(reg_init; CYS_GRACE=": ["k9", "/tmp/nowhere-k9", "/tmp/nowhere-acct"],  # create 예약
    }

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="winlock-")
        sim = _make_winlock_sim(os.path.join(self.tmp, "sim"))
        self.env = {"HOME": self.tmp, "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONPATH": sim}
        self.reg = os.path.join(self.tmp, "depts.json")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _run(self, header, args, data):
        with open(self.reg, "wb") as f:
            f.write(data)
        r = subprocess.run([sys.executable, "-", self.reg] + args, input=_dept_py_block(header), capture_output=True,
                           text=True, encoding="utf-8", env=self.env, timeout=60)
        with open(self.reg, "rb") as f:
            after = f.read()
        return r.returncode, r.stdout, r.stderr, after

    def test_simulation_really_fails_the_lock(self):
        for header, args in self.CONTROLS.items():
            rc, out, err, _ = self._run(header, args, json.dumps({"depts": {"keep1": {}}}).encode())
            self.assertEqual(rc, 11, "%s: 흉내가 잠금 실패를 만들지 못함\n%s" % (header, err))

    def test_lock_failure_never_reads_or_writes(self):
        keep = json.dumps({"depts": {"keep1": {"socket": "", "pack_dir": ""}}}).encode()
        for header, args in self.TARGETS.items():
            for data in (keep, b""):
                rc, out, err, after = self._run(header, args, data)
                self.assertEqual(rc, 11, "%s(%r): 잠금 실패인데 exit=%d\n%s" % (header, data[:10], rc, err))
                self.assertEqual(after, data, "%s: 잠금 실패인데 목록을 바꿨다" % header)
                self.assertEqual(out.strip(), "", "%s: 잠금 실패인데 판독 결과를 내보냈다(무잠금 판독)" % header)
                self.assertIn("다시", err, "%s: 「다시 시도」 안내 부재" % header)

    def test_lock_blocks_zero_byte_rule_and_notice_direct(self):
        """판독 9곳 중 잠금 블록 8곳을 직접: 0바이트 입력 → 12 아님 · 0바이트 알림(잠금 성공 경로 = 실제 fcntl)."""
        env = {"HOME": self.tmp, "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        for header, args in list(self.TARGETS.items()) + list(self.CONTROLS.items()):
            with open(self.reg, "wb") as f:
                f.write(b"")
            r = subprocess.run([sys.executable, "-", self.reg] + args, input=_dept_py_block(header),
                               capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
            self.assertNotEqual(r.returncode, 12, "%s: 0바이트가 판독 실패\n%s" % (header, r.stderr))
            self.assertIn("빈 목록으로 다룹니다", r.stderr, "%s: 0바이트 알림 부재" % header)


class WinLockFailureCallers(Base):
    """codex 4R: 잠금 실패 11 이 호출 쪽에서 성공처럼 삼켜지지 않는다 — reap 스냅샷 11 보존 · down-sock 은 울타리를
    지나 목록 제거만 실패해도(보류) 비0 으로 끝나 reap 이 「완료」 로 세지 않는다. 흉내 = fcntl 부재 + 계수형 msvcrt
    (N번째 잠금부터 실패 · 파이썬 블록마다 새 프로세스라 계수기는 파일)."""

    def _sim(self, fail_at):
        sim = _make_winlock_sim(os.path.join(self.home, "sim"), counter=True)
        env = dict(self.env)
        env.update({"PYTHONPATH": sim, "SIMLOCK_COUNTER": os.path.join(self.home, "simlock.cnt"),
                    "SIMLOCK_FAIL_AT": str(fail_at)})
        return env

    def test_reap_snapshot_lock_failure_keeps_exit_11(self):
        write_reg(self.env, {"keep1": {"socket": "", "pack_dir": ""}})
        before = open(self.env["CYS_DEPTS_JSON"], "rb").read()
        rc, out, err = self.run_dept("reap", env=self._sim(0))
        self.assertEqual(rc, 11, "reap 스냅샷 잠금 실패가 %d 로 바뀌었다\n%s" % (rc, err))
        self.assertNotIn("reap 완료", out)
        self.assertEqual(open(self.env["CYS_DEPTS_JSON"], "rb").read(), before)

    def test_down_sock_list_removal_held_is_nonzero_and_told(self):
        sock = seed_sock(self.home, "a")
        write_reg(self.env, {"a": {"socket": sock, "pack_dir": ""}})
        rc, out, err = self.run_dept("down-sock", sock, env=self._sim(1))   # 울타리(1번째) 통과 · 목록 제거(2번째) 실패
        self.assertNotEqual(rc, 0, "목록 정리 보류인데 성공 종료 — reap 이 「완료」 로 센다\n%s%s" % (out, err))
        self.assertIn("목록 정리 보류", out + err)
        self.assertIn("a", read_reg(self.env), "잠금 실패인데 목록을 바꿨다")


class RegistryUnreadable(Base):
    """①(TICKET=cysr-117-impl-lead · MUST-DO-117 ①) 부서 목록 판독 실패 = 무변경(exit 12).
    종전: 8곳이 판독 실패를 빈 목록으로 접어 다음 저장이 등록 부서를 전멸시켰고, rotate 는 판독 실패를
    「미등재(exit 8)」 로 읽었다(kill 뒤 재확인이면 데몬만 죽은 반쪽 상태)."""

    BAD = {
        "truncated": b'{"depts":{"a":{"socket":"',
        "utf16": '{"depts":{"a":{}}}'.encode("utf-16"),
        "not_dict": b'{"depts":["a"]}',
        "array": b'[1,2]',
        # 1.1.7 fix-blockers A1-F3: 복구는 「정확히 0바이트」 만 — 공백만 · BOM 만은 비어 있지 않은 손상(12 유지)
        "blank": b" \n",
        "bom_only": b"\xef\xbb\xbf",
    }

    def _write_raw(self, data):
        with open(self.env["CYS_DEPTS_JSON"], "wb") as f:
            f.write(data)

    def _raw(self):
        with open(self.env["CYS_DEPTS_JSON"], "rb") as f:
            return f.read()

    def test_bom_registry_is_read_not_destroyed(self):
        self._write_raw(b'\xef\xbb\xbf' + json.dumps({"depts": {"keep1": {"socket": "", "pack_dir": ""}}}).encode())
        rc, out, err = self.run_dept("list")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.split(), ["keep1"], "BOM 레지스트리를 못 읽음")
        seed_sock(self.home, "new1")
        rc, out, err = self.run_dept("launch", "new1")
        self.assertEqual(rc, 0, "BOM 레지스트리 위 launch 실패: %s" % err)
        self.assertEqual(sorted(read_reg(self.env)), ["keep1", "new1"], "BOM 한 글자로 기존 부서 전멸")

    def test_unreadable_registry_every_verb_exit12_bytes_unchanged(self):
        for tag, data in self.BAD.items():
            for args in (["list"], ["rotate", "a"], ["promote-ceo"], ["down", "a"],
                         ["launch", "b"], ["allocate"], ["create", "k9"], ["reap"]):
                self._write_raw(data)
                seed_sock(self.home, "b")
                CreateGate._seed_catalog(self, "k9", "m9")  # create 가 카탈로그 검사를 지나 레지스트리까지 가게
                rc, out, err = self.run_dept(*args)
                self.assertEqual(rc, 12, "%s %s: exit=%d(≠12)\n%s%s" % (tag, args, rc, out, err))
                self.assertIn("판독 실패", err, "%s %s: 사유 안내 부재" % (tag, args))
                self.assertEqual(self._raw(), data, "%s %s: 판독 불가 레지스트리가 바뀌었다" % (tag, args))
                if args[0] == "launch":
                    self.assertFalse(os.path.exists(os.path.join(self.home, ".cys", "pack-dept-b")),
                                     "%s: 판독 실패인데 부서 팩 폴더를 만들었다" % tag)

    def test_zero_byte_registry_reinitialized_every_verb(self):
        """A1-F3(1.1.7 fix-blockers · codex 1R 차단): 0바이트 = 지킬 부서가 없는 파일 — v1.1.6 처럼 빈 목록으로
        다시 만든다(영구 exit 12 회귀 금지). 목록 초기화는 알리되 「복구」 가 아님을 말한다."""
        for args in (["list"], ["rotate", "a"], ["promote-ceo"], ["down", "a"],
                     ["launch", "b"], ["allocate"], ["create", "k9"], ["reap"]):
            self._write_raw(b"")
            seed_sock(self.home, "b")
            CreateGate._seed_catalog(self, "k9", "m9")
            rc, out, err = self.run_dept(*args)
            self.assertNotEqual(rc, 12, "%s: 0바이트가 영구 판독 실패로 남았다\n%s%s" % (args, out, err))
            self.assertIn("목록 초기화", err, "%s: 0바이트 초기화 안내 부재" % (args,))
            self.assertIn("돌아오지 않습니다", err, "%s: 옛 부서가 복구된 것처럼 들린다" % (args,))
            d = json.loads(self._raw().decode("utf-8"))
            self.assertIsInstance(d.get("depts"), dict, "%s: 초기화 결과가 유효한 부서 목록이 아니다" % (args,))

    def test_zero_byte_then_launch_registers(self):
        self._write_raw(b"")
        seed_sock(self.home, "new1")
        rc, out, err = self.run_dept("launch", "new1")
        self.assertEqual(rc, 0, err)
        self.assertEqual(sorted(read_reg(self.env)), ["new1"])
        rc, out, err = self.run_dept("list")
        self.assertEqual((rc, out.split()), (0, ["new1"]), err)
        self.assertNotIn("목록 초기화", err, "비어 있지 않은 목록에 초기화 안내가 또 나왔다")

    def test_absent_registry_created_silently(self):
        os.remove(self.env["CYS_DEPTS_JSON"]) if os.path.exists(self.env["CYS_DEPTS_JSON"]) else None
        rc, out, err = self.run_dept("list")
        self.assertEqual(rc, 0, err)
        self.assertNotIn("목록 초기화", err, "처음 만들기(부재)는 초기화가 아니다")
        self.assertEqual(json.loads(self._raw().decode("utf-8")), {"depts": {}})

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), "POSIX 권한 비트 · 비루트 한정")
    def test_zero_byte_read_rule_holds_when_reinit_fails(self):
        """초기화(쓰기)가 권한으로 실패해도 판독은 같은 0바이트 규칙 — 목록 = 비어 있음(12 아님) · 파일 무변경."""
        self._write_raw(b"")
        d = os.path.dirname(self.env["CYS_DEPTS_JSON"])
        lock = self.env["CYS_DEPTS_JSON"] + ".lock"
        if os.path.exists(lock):
            os.remove(lock)
        os.chmod(d, 0o555)
        try:
            rc, out, err = self.run_dept("list")
        finally:
            os.chmod(d, 0o755)
        self.assertEqual((rc, out.split()), (0, []), err)
        self.assertIn("초기화 실패", err)
        self.assertEqual(self._raw(), b"")

    @unittest.skipIf(os.name == "nt", "fcntl 잠금 — POSIX 한정")
    def test_reinit_rechecks_under_lock_and_keeps_concurrent_write(self):
        """결정적 경합: reg_init 이 셸 빠른 길에서 0바이트를 본 뒤 잠금을 기다리는 동안 다른 쓰기가 목록을 채우면,
        잠금을 얻은 reg_init 은 다시 재서 아무것도 덮지 않는다(잠금 밖 판정 → 잠금 안 쓰기 금지)."""
        import fcntl
        self._write_raw(b"")
        lf = open(self.env["CYS_DEPTS_JSON"] + ".lock", "w")
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            proc = subprocess.Popen(["bash", DEPT, "list"], env=self.env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding="utf-8")
            self.assertTrue(_wait_lock_opener(self.env["CYS_DEPTS_JSON"] + ".lock"), "자식이 초기화 잠금 블록에 들어서지 않았다")
            write_reg(self.env, {"held1": {"socket": "", "pack_dir": ""}})
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
            lf.close()
        out, err = proc.communicate(timeout=60)
        self.assertEqual(proc.returncode, 0, err)
        self.assertEqual(sorted(read_reg(self.env)), ["held1"], "잠금을 기다린 초기화가 그 사이의 등록을 덮었다")
        self.assertNotIn("목록 초기화", err)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), "POSIX 권한 비트 · 비루트 한정")
    def test_unreadable_zero_byte_file_is_not_replaced(self):
        """codex 2R: 크기만 보고 교체하면 읽기 권한 오류인 빈 파일을 덮는다 — 잠금 안에서 실제로 읽어 판정."""
        self._write_raw(b"")
        rp = self.env["CYS_DEPTS_JSON"]
        ino = os.stat(rp).st_ino
        os.chmod(rp, 0)
        try:
            rc, out, err = self.run_dept("list")
            st = os.stat(rp)
        finally:
            os.chmod(rp, 0o644)
        self.assertEqual(rc, 12, err)
        self.assertEqual((st.st_ino, st.st_size), (ino, 0), "읽을 수 없는 빈 파일이 교체됐다")
        self.assertNotIn("목록 초기화이지", err)

    @unittest.skipIf(os.name == "nt", "fcntl 잠금 — POSIX 한정")
    def test_locked_block_reading_zero_bytes_announces_reset(self):
        """초기화(빠른 길) 뒤·잠금 블록 판독 전에 목록이 0바이트가 되는 경로 — 잠금 블록도 같은 규칙 + 같은 알림."""
        import fcntl
        write_reg(self.env, {"keep1": {"socket": "", "pack_dir": ""}})
        lf = open(self.env["CYS_DEPTS_JSON"] + ".lock", "w")
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            proc = subprocess.Popen(["bash", DEPT, "reap", "--dry"], env=self.env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding="utf-8")
            self.assertTrue(_wait_lock_opener(self.env["CYS_DEPTS_JSON"] + ".lock"), "자식이 스냅샷 잠금 블록에 들어서지 않았다")
            self._write_raw(b"")
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
            lf.close()
        out, err = proc.communicate(timeout=60)
        self.assertEqual(proc.returncode, 0, err)
        self.assertIn("빈 목록으로 다룹니다", err)
        self.assertIn("돌아오지 않습니다", err)

    def test_zero_byte_concurrent_verbs_converge_and_keep_launch(self):
        """reg_init 복구와 등록 쓰기가 겹쳐도 등록이 사라지지 않는다(잠금 안 재판정 · 원자 게시)."""
        for _ in range(5):
            self._write_raw(b"")
            seed_sock(self.home, "c1")
            env = dict(self.env)
            procs = [subprocess.Popen(["bash", DEPT, "list"], env=env, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL) for _ in range(6)]
            procs.append(subprocess.Popen(["bash", DEPT, "launch", "c1"], env=env, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL))
            rcs = [p.wait(timeout=60) for p in procs]
            self.assertNotIn(12, rcs, "동시 호출 중 판독 실패")
            self.assertIn("c1", read_reg(self.env), "0바이트 복구가 동시 등록을 지웠다")
            write_reg(self.env, {})

    def test_rotate_rechecks_registry_before_kill(self):
        # 사전 게이트 통과 뒤·kill 직전에 레지스트리가 판독 불가가 되면 데몬을 죽이지 않고 exit 12.
        victim = subprocess.Popen(["sleep", "60"])
        self.addCleanup(lambda: (victim.kill(), victim.wait()))
        sock = seed_sock(self.home, "a")
        write_reg(self.env, {"a": {"socket": sock, "pack_dir": ""}})
        _write_exec(os.path.join(self.home, ".local", "bin", "cys"),
                    '#!/bin/sh\n'
                    'case "$1" in\n'
                    '  ping) exit 0 ;;\n'
                    '  identify) printf \'{"depts":{"a":\' > "$CYS_DEPTS_JSON";'
                    ' echo \'{"version":"1.0.0","daemon_pid":%d}\'; exit 0 ;;\n'
                    'esac\nexit 0\n' % victim.pid)
        rc, out, err = self.run_dept("rotate", "a")
        self.assertEqual(rc, 12, "kill 전 판독 재확인 부재: exit=%d\n%s" % (rc, err))
        self.assertIsNone(victim.poll(), "판독 불가인데 데몬을 죽였다(반쪽 상태)")


class PassthroughArm(Base):
    # 6) 실존(등재) 이름은 비정형이라도 통과 — 기존 부서 컨텍스트 실행 불차단(정리 동사형 규칙)
    def test_existing_nonconforming_passes(self):
        write_reg(self.env, {"a.b": {"socket": "", "pack_dir": ""}})
        rc, out, err = self.run_dept(
            "a.b", "--", "sh", "-c", 'echo "NA=${CYS_NO_AUTOSTART:-unset}"')
        self.assertEqual(rc, 0, "실존 비정형 passthrough 차단됨\n%s" % err)
        self.assertIn("NA=unset", out, "실존 이름인데 CYS_NO_AUTOSTART 오동봉")

    # 6) 비실존·정형 = 통과 + CYS_NO_AUTOSTART=1 동반(G0 D10 — autostart 유령 생성 봉합)
    def test_nonexistent_conforming_gets_no_autostart(self):
        write_reg(self.env, {})
        rc, out, err = self.run_dept(
            "ghostx", "--", "sh", "-c", 'echo "NA=${CYS_NO_AUTOSTART:-unset}"')
        self.assertEqual(rc, 0, "비실존·정형 passthrough 차단됨\n%s" % err)
        self.assertIn("NA=1", out, "비실존·정형인데 CYS_NO_AUTOSTART=1 미동봉(D10)")

    # 6) 비실존+비정형 = exit 2 (verb 오타 흡수 → 유령 생성 사고 절반 봉합)
    def test_nonexistent_nonconforming_rejected(self):
        write_reg(self.env, {})
        rc, out, err = self.run_dept("no.pe", "--", "sh", "-c", "echo run")
        self.assertEqual(rc, 2, "비실존·비정형 passthrough 통과(exit=%d)" % rc)
        self.assertNotIn("run", out, "거부인데 명령 실행됨")

    # 6) sock: '-' 선두 exit 2 / 레거시 비정형 등재명은 통과(fan-out 루프 `sock "$d"` 호환)
    def test_sock_partial_validation(self):
        rc, out, err = self.run_dept("sock", "--help")
        self.assertEqual(rc, 2, "sock --help가 경로를 오출력(exit=%d)" % rc)
        self.assertNotIn("cys-dept---help", out)
        rc, out, err = self.run_dept("sock", "a.b")
        self.assertEqual(rc, 0, "레거시 비정형 등재명 sock 회귀(fan-out 파손)")
        self.assertIn("cys-dept-a.b", out)


class ArgHygiene(Base):
    # 7) cys tombstone 인자 위생: down(set)·launch(remove) 모두 `--dept [--remove] -- <name>` 형식
    def test_tombstone_double_dash(self):
        sock = seed_sock(self.home, "d1")
        write_reg(self.env, {"d1": {"socket": sock, "pack_dir": ""}})
        rc, out, err = self.run_dept("down", "d1")
        self.assertEqual(rc, 0, "down 실패\n%s%s" % (out, err))
        self.assertIn("tombstone --dept -- d1", self.calls(),
                      "down의 데몬 묘비 set이 `--dept -- <name>` 형식이 아님")
        # launch 성공 말미의 묘비 해소(remove)도 동일 위생
        seed_sock(self.home, "d2")
        write_reg(self.env, {"d2": {"socket": "", "pack_dir": ""}})
        rc, out, err = self.run_dept("launch", "d2")
        self.assertEqual(rc, 0, "launch 실패\n%s%s" % (out, err))
        self.assertIn("tombstone --dept --remove -- d2", self.calls(),
                      "launch의 묘비 해소가 `--dept --remove -- <name>` 형식이 아님")


class SlugFold(Base):
    # 8) 기존명 재-launch 통과(자기 제외 — GUI 복원·rotate 재귀 무회귀 핀)
    def test_existing_name_relaunch_passes(self):
        seed_sock(self.home, "sales")
        write_reg(self.env, {"sales": {"socket": "", "pack_dir": ""}})
        rc, out, err = self.run_dept("launch", "sales")
        self.assertEqual(rc, 0, "기존명 재-launch가 거부됨(자기 제외 결여)\n%s" % err)

    # 8) slug 충돌쌍 거부: 대소(Sales↔sales)·'.'-fold(ab↔a.b — win pipe_slug 점 소거 정합)
    def test_slug_collision_pairs_rejected(self):
        write_reg(self.env, {"sales": {"socket": "", "pack_dir": ""},
                             "a.b": {"socket": "", "pack_dir": ""}})
        for newname, existing in (("Sales", "sales"), ("SALES", "sales"), ("ab", "a.b")):
            rc, out, err = self.run_dept("launch", newname)
            self.assertEqual(rc, 2, "launch %r: 충돌쌍(기존 %r) 미거부(exit=%d)"
                             % (newname, existing, rc))
            self.assertIn("slug 충돌", err)
            self.assertNotIn(newname, read_reg(self.env), "충돌 거부인데 등재됨(%s)" % newname)


class PromotionReceiptAndDemote(Base):
    # 9) 승격 영수증: _swap 후 적용 템플릿 sha256(hex 1줄) 기록 → 강등 시 삭제
    def test_receipt_written_and_deleted(self):
        pack = self._seed_promotable(ndepts=1)
        rc, out, err = self.run_dept("promote-ceo")
        self.assertEqual(rc, 0, "promote-ceo 실패\n%s%s" % (out, err))
        expected = hashlib.sha256(
            open(os.path.join(pack, "CEO_TEMPLATE.md"), "rb").read()).hexdigest()
        self.assertTrue(os.path.exists(self._receipt()), "승격 영수증 미기록")
        self.assertEqual(open(self._receipt(), encoding="utf-8").read().strip(), expected,
                         "영수증 내용≠적용 템플릿 sha256")
        self.assertTrue(os.path.exists(os.path.join(pack, "MASTER_DIRECTIVE.md.pre-ceo")))
        # 마지막 부서 down → ceo_demote: 원복+영수증 삭제
        rc, out, err = self.run_dept("down", "d0")
        self.assertEqual(rc, 0, "down 실패\n%s%s" % (out, err))
        self.assertEqual(open(os.path.join(pack, "MASTER_DIRECTIVE.md"),
                              encoding="utf-8").read(), "STANDARD-MASTER\n", "강등 원복 실패")
        self.assertFalse(os.path.exists(self._receipt()), "강등 후 영수증 잔존(stale)")

    # 10) demote 무음 경보: 승격 표지(md==템플릿)+.pre-ceo 부재 → stderr 경보+feed push(비대기)
    def test_demote_missing_backup_alerts(self):
        pack = self._seed_promotable(ndepts=1)
        with open(os.path.join(pack, "MASTER_DIRECTIVE.md"), "w", encoding="utf-8") as f:
            f.write(CEO_BODY)   # 승격 표지(md==템플릿) — .pre-ceo는 없음(비가역 상태)
        rc, out, err = self.run_dept("down", "d0")
        self.assertEqual(rc, 0, "경보 경로가 teardown을 파괴(exit=%d)" % rc)
        self.assertIn("강등 불능", err, "무음 no-op 잔존 — stderr 경보 부재")
        self.assertIn("feed push --title CEO 강등 불능", self.calls(), "feed push 경보 부재")

    # 10) 미승격 머신: .pre-ceo 부재는 정상 no-op — 위경보 금지
    def test_demote_unpromoted_no_false_alarm(self):
        pack = self._seed_promotable(ndepts=1)   # md=STANDARD(미승격)·pre-ceo 無
        rc, out, err = self.run_dept("down", "d0")
        self.assertEqual(rc, 0)
        self.assertNotIn("강등 불능", err, "미승격 머신에 위경보")
        self.assertNotIn("CEO 강등 불능", self.calls(), "미승격 머신에 feed 위경보")


class FeedDedupe(Base):
    def _pend_state(self):
        state = os.path.join(self.home, ".cys", "state")
        os.makedirs(state, exist_ok=True)
        with open(os.path.join(state, "ceo-pending"), "w") as f:
            f.write("pending\n")

    # 11) A11: 미해결 동종 pending 존재 → push 생략(로그 1줄) / 부재 → 발행
    def test_request_only_dedupe(self):
        self._seed_promotable(ndepts=1)
        self._pend_state()
        with open(self.feedlist, "w", encoding="utf-8") as f:
            f.write("id1\t[pending]\tgeneric\tCEO 승격 대기\tdecision=-\n")
        rc, out, err = self.run_dept("promote-if-pending", "--request-only")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("재발행 생략", out, "dedupe 생략 로그 1줄 부재")
        self.assertNotIn("feed push --title CEO 승격 대기", self.calls(),
                         "동종 pending 존재인데 push 재발행(A11 위반)")
        # pending 항목 소거 → 발행 재개(과차단 금지)
        os.unlink(self.feedlist)
        open(self.log, "w").close()
        rc, out, err = self.run_dept("promote-if-pending", "--request-only")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("알림 발행", out)
        self.assertIn("feed push --title CEO 승격 대기", self.calls(),
                      "동종 pending 부재인데 push 미발행(과차단)")

    # 11) 제목이 다른 pending(무관 항목)은 dedupe 비대상
    def test_request_only_unrelated_pending_not_deduped(self):
        self._seed_promotable(ndepts=1)
        self._pend_state()
        with open(self.feedlist, "w", encoding="utf-8") as f:
            f.write("id9\t[pending]\tgeneric\t다른 승인 요청\tdecision=-\n")
        rc, out, err = self.run_dept("promote-if-pending", "--request-only")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("feed push --title CEO 승격 대기", self.calls(),
                      "무관 pending에 오-dedupe(제목 정합 검사 결여)")


class DaemonLeakGuard(Base):
    # v116-pack: 케이스 정리가 띄운 데몬을 실제로 끝내는가 — 끝나지 않는 목 cysd 로 launch 해 잔존을 만든 뒤
    #   _cleanup 이 0 으로 만드는지 본다(목이 즉시 끝나는 다른 케이스로는 정리 경로가 검증되지 않는다).
    def test_spawned_daemon_reaped_by_cleanup(self):
        _write_exec(os.path.join(self.home, ".local", "bin", "cysd"),
                    '#!/bin/sh\nmkdir -p "$(dirname "$CYS_SOCKET")"\ntouch "$CYS_SOCKET"\nexec sleep 600\n')
        write_reg(self.env, {"leakprobe": {"socket": "", "pack_dir": ""}})
        self.run_dept("launch", "leakprobe")
        spawned = _pids_holding(self.tmp)
        self.assertTrue(spawned, "전제 실패: launch 가 목 데몬을 띄우지 않음(이 검사가 공허해짐)")
        self._cleanup()
        self.assertEqual(_pids_holding(self.tmp), [], "정리 뒤에도 띄운 데몬이 남음")
        for p in spawned:
            with self.assertRaises(OSError, msg="pid %d 생존" % p):
                os.kill(p, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
