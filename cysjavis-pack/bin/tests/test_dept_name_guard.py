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
 12) K2-07(2026-09-17 한글 사용자명 감사 · 2라운드) — unix 소켓 sun_path 초과는 **cysd 의 bind 가 판정**하고
     cys-dept 는 "데몬 기동 실패" 에 사유(sock_len_diag)만 덧붙인다. 스폰 전 exit 2 가드는 이 하네스
     (격리 HOME=mkdtemp → macOS /var/folders 50B 라 1글자 부서명도 105B · 목 cysd 는 bind 안 함)를
     깨뜨렸던 결함 — mkdtemp HOME 이 상한을 넘어도 목 cysd 로 launch 가 완주한다(회귀 표본).
 13) CRLF 위생 census — `read < <(python3 …)` 파이프 소비자 전부 `| tr -d '\r'`(cys-dept reg_names 규칙).
 14) K2-03 범위 일치 — depts.json 판독 전 지점 utf-8-sig(BOM 레지스트리가 RMW 에서 비워지지 않는다).
     P1(2026-09-17 부트체인 감사): 비UTF-8·손상 JSON 은 exit 12(1.1.8 병합: 우리 번호 — 원작자 원판 10)·원본 보존(빈 등재 복구·CEO 오강등 금지).
 15) R6/S1 — 스폰 경쟁 패자의 사망 뒤 rc 12 회수에서도 살아 있는 승자의 소켓/lock·목 ping 응답 보존.
"""
import ast
import hashlib
import json
import os
import shutil
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import unicodedata

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


def startup_lock(sock):
    """cysd 의 startup-lock 경로 — Rust 는 `socket_path.with_extension("lock")` 로 만든다
    (src/bin/cysd/main.rs:1132·1137). 즉 `…/cys-dept-<n>/cys.sock` 의 락은 `cys.sock.lock` 이 아니라
    **`cys.lock`** 이다. 검체가 실재하지 않는 파일을 지키면 '보존됐다' 는 단언이 공허해진다
    (2026-09-17 8라운드 · codex 4차 minor)."""
    return os.path.splitext(sock)[0] + ".lock"


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
    # ★1.1.8(원작자 v0.14.43 1b40379c 「레지스트리 판독 fail-closed」): reg_* 머리 줄이 `<<'PY' || return $?` 처럼
    #   heredoc 표지 뒤에 꼬리를 단다 — 종전 `<<'PY'\n` 탐색은 그 줄을 건너뛰어 **다음 함수의 블록**(reg_fence_close ·
    #   인자 3개)을 떼어 와 「expected 3, got 2」로 죽었다. 표지는 머리 줄 안에서 찾고 본문은 그 줄 끝 다음부터다.
    eol = src.index("\n", i)
    m = src.index("<<'PY'", i)
    assert m < eol, "머리 줄(%r)에 <<'PY' 가 없다 — 다른 블록을 떼어 오지 않는다" % header
    j = eol + 1
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
        # ★1.1.8: 원작자 03bbe37c(allocate --team-spec-b64)가 머리에 선택 인자 4개를 더했다(빈 값 = 종전 동작).
        "name=$(reg_init; python3 - \"$REG\" \"$TEAM_B64\"": [],                     # allocate 예약
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
def _await_pid(pidfile, deadline=4.0):
    """목 데몬이 자기 pid 를 적을 때까지 유계 대기(무한 대기 금지) — 빈 값이면 픽스처 결함이다."""
    end = time.time() + deadline
    while time.time() < end:
        if os.path.exists(pidfile):
            with open(pidfile, encoding="utf-8") as f:
                v = f.read().strip()
            if v:
                return v
        time.sleep(0.02)
    return ""


class RotatePostKillRegistryCorruption(Base):
    """16) J4 — rotate 본체의 **kill 직후** 레지스트리 손상은 재기동을 막지 못한다(반파괴 차단).

    근거: K8(bin/tests/test_role_authority_shell.py:470-479 "unreadable registry keeps the rotate
    exemption (no post-kill half-op)") 과 T11('면제 정책 반전'). K8 은 재귀 `launch <name> --rotate`
    의 **게이트 rc** 만 핀한다 — 게이트를 통과하고도 그 뒤 어느 단계든 판독 실패로 끊기면 결과는
    똑같이 '데몬은 죽고 등재만 남는' 반파괴다. 그 구간을 여기서 **행동으로** 핀한다.

    형상: 등재·가동 중 부서를 rotate → `graceful_kill` 이 보낸 SIGTERM 을 받은 목 데몬이 죽으면서
    depts.json 을 손상시킨다(kill 이전 판독은 성공 · 이후 전부 실패 = 실제 경합의 최악 시점).

    단언 3축:
      ⓐ **데몬 재기동 완료** — 소켓이 다시 생기고 목 `cys ping`(파일 실존 프로브)이 0 을 낸다.
         (mutation: cys-dept 의 kill 직후 TOCTOU 재확인을 `|| exit $?` 로 되돌리면 여기서 red)
      ⓑ **rc 계약** — 손상 레지스트리라 마지막 조회가 실패하므로 rc 12(판독 실패 · 1.1.8 병합: 우리 번호)이다.
         '미등재'(exit 8)로 오판하지 않는다 — 판독 불가는 미등재가 아니다.
      ⓒ **원본 바이트 보존** — 손상된 파일에 아무것도 쓰이지 않는다(RegistryBom 과 같은 축).
    """
    CORRUPT = b'{"depts":{"d1":'

    def _arm(self):
        bindir = os.path.join(self.home, ".local", "bin")
        pidfile = os.path.join(self.tmp, "victim.pid")
        sock = seed_sock(self.home, "d1")
        write_reg(self.env, {"d1": {"socket": sock, "pack_dir": ""}})
        with open(self.env["CYS_DEPTS_JSON"], "rb") as f:
            before_ok = f.read()

        # 목 데몬(실 프로세스): SIGTERM 에 레지스트리를 손상시키고 죽는다 = kill 직후 판독 실패.
        victim = os.path.join(self.tmp, "victim.py")
        with open(victim, "w", encoding="utf-8") as f:
            f.write(
                "import os, signal, sys, time\n"
                "from pathlib import Path\n"
                "def bye(*a):\n"
                "    Path(sys.argv[2]).write_bytes(%r)\n"
                "    os._exit(0)\n"
                "signal.signal(signal.SIGTERM, bye)\n"
                "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                "while True: time.sleep(0.05)\n" % (self.CORRUPT,))
        proc = subprocess.Popen([sys.executable, victim, pidfile, self.env["CYS_DEPTS_JSON"]])
        self.addCleanup(lambda: (proc.poll() is None) and (proc.kill(), proc.wait()))
        pid = _await_pid(pidfile)
        self.assertTrue(pid, "픽스처 결함: 목 데몬 pid 미기록")

        # ping=소켓 파일 실존(생사) · identify=살아 있는 목 데몬의 pid/version 을 낸다.
        _write_exec(os.path.join(bindir, "cys"),
                    '#!/bin/sh\n'
                    'echo "cys $@" >> "%(log)s"\n'
                    'case "$1" in\n'
                    '  ping) [ -e "$CYS_SOCKET" ] && exit 0 || exit 1 ;;\n'
                    '  identify) printf \'{"daemon_pid":"%(pid)s","version":"0.0.1"}\\n\'; exit 0 ;;\n'
                    'esac\nexit 0\n' % {"log": self.log, "pid": pid})
        return sock, before_ok, proc

    def test_post_kill_corruption_still_relaunches(self):
        sock, before_ok, proc = self._arm()
        rc, out, err = self.run_dept("rotate", "d1")
        with open(self.env["CYS_DEPTS_JSON"], "rb") as f:
            corrupted = f.read()

        # 전제: 픽스처가 실제로 kill 직후 손상을 만들었다(안 그러면 아래 단언이 공허해진다).
        self.assertNotEqual(corrupted, before_ok,
                            "픽스처 전제 붕괴: 목 데몬이 SIGTERM 에 레지스트리를 손상시키지 않았다")
        self.assertEqual(corrupted, self.CORRUPT, "픽스처 손상 바이트 불일치")

        # ⓐ 데몬 재기동 완료 — 소켓 부활 + 목 ping 0. 이것이 반파괴(데몬 사망·등재 잔존)의 부정이다.
        self.assertTrue(os.path.exists(sock),
                        "★kill 뒤 판독 실패로 재기동이 끊겼다 — 데몬 사망·등재 잔존(반파괴)\nrc=%d\n%s"
                        % (rc, err))
        ping = subprocess.run(["bash", "-c", '"$0" ping', os.path.join(
            self.home, ".local", "bin", "cys")],
            env=dict(self.env, CYS_SOCKET=sock), capture_output=True, text=True, timeout=30)
        self.assertEqual(ping.returncode, 0, "재기동 소켓이 응답하지 않는다")

        # ⓑ rc 계약 — 판독 실패는 10. '미등재'(8)로 오판하지 않는다.
        self.assertEqual(rc, 12, "판독 실패 rotate rc=%d(≠12)\n%s" % (rc, err))
        self.assertNotIn("미등재(down됨·rotate 중 폐기)", err,
                         "판독 불가를 '미등재'로 오판 — 판독 불가는 미등재가 아니다(K8)")
        self.assertIn("kill 이후이므로 재기동 진행(반파괴 차단)", err,
                      "kill 이후 진행 고지 부재(침묵한 강등 금지)")

        # ⓒ 원본 바이트 보존 — 손상 파일에 아무것도 쓰이지 않는다.
        with open(self.env["CYS_DEPTS_JSON"], "rb") as f:
            self.assertEqual(f.read(), self.CORRUPT,
                             "★손상 레지스트리가 재기록됐다(원본 보존 계약 위반)")

    def test_post_kill_unregistered_still_exit8(self):
        """음성 대조: 판독이 **되는데** 정말 폐기된 경우는 종전대로 exit 8(부활 금지) — 새 허용 0."""
        bindir = os.path.join(self.home, ".local", "bin")
        pidfile = os.path.join(self.tmp, "victim2.pid")
        sock = seed_sock(self.home, "d1")
        write_reg(self.env, {"d1": {"socket": sock, "pack_dir": ""}})
        victim = os.path.join(self.tmp, "victim2.py")
        with open(victim, "w", encoding="utf-8") as f:
            f.write(
                "import os, signal, sys, time, json\n"
                "from pathlib import Path\n"
                "def bye(*a):\n"
                "    Path(sys.argv[2]).write_text(json.dumps({'depts': {}}))\n"
                "    os._exit(0)\n"
                "signal.signal(signal.SIGTERM, bye)\n"
                "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                "while True: time.sleep(0.05)\n")
        proc = subprocess.Popen([sys.executable, victim, pidfile, self.env["CYS_DEPTS_JSON"]])
        self.addCleanup(lambda: (proc.poll() is None) and (proc.kill(), proc.wait()))
        pid = _await_pid(pidfile)
        _write_exec(os.path.join(bindir, "cys"),
                    '#!/bin/sh\n'
                    'echo "cys $@" >> "%(log)s"\n'
                    'case "$1" in\n'
                    '  ping) [ -e "$CYS_SOCKET" ] && exit 0 || exit 1 ;;\n'
                    '  identify) printf \'{"daemon_pid":"%(pid)s","version":"0.0.1"}\\n\'; exit 0 ;;\n'
                    'esac\nexit 0\n' % {"log": self.log, "pid": pid})
        rc, out, err = self.run_dept("rotate", "d1")
        self.assertEqual(rc, 8, "판독 가능한 '폐기됨'은 종전대로 exit 8 이어야 한다(rc=%d)\n%s" % (rc, err))
        self.assertIn("미등재(down됨·rotate 중 폐기)", err, "폐기 사유 문면 소실")
        self.assertFalse(os.path.exists(sock), "부활 금지인데 소켓이 다시 생겼다")


class J5PyShim(Base):
    """17) J5·J6 — codex 9차 major 3건 + 10차 minor 1건의 회귀 핀
    (M1 기록시점 손상 · M2 교차계정 토큰 · M3 CRLF · J6 선포착 표식 위생).

    공통 하네스: `$HOME/.local/bin/python3` **투명 shim**(PATH 1순위). 모든 호출을 로그에 적고
    실 python 으로 exec 한다 — cys-dept 의 python 사용은 전부 그대로 동작한다. 세 축만 주입한다:
      · `PYSHIM_CORRUPT_ON_SET_FIELD=<field>` — `reg_set_field`(=`python3 - <REG> <n> <f> <v>` · 인자 5개)
        직전에 레지스트리를 손상시킨다 ⇒ **조회는 성공했고 기록 시점에 깨진** 경합의 결정론 재현.
      · `PYSHIM_CRLF_AGENTS=1` — `pack_seeded_acct`(=`python3 - <pack>/agents.json` · 인자 2개) 출력만
        CRLF 로 바꾼다 ⇒ Windows PortableGit 네이티브 python 의 텍스트 모드 재현.
      · 로그(`self.pylog`)로 `resolve_default_base`(=`python3 - <catalog> <acct>`) 호출 여부·인자를 본다
        ⇒ '어떤 계정이 자격증명 시드의 원천으로 결정됐는가' 를 macOS 에서도 관측한다.
        (`seed_credentials_win` 본체는 uname 으로 Windows 한정이라 복사 자체는 여기서 안 일어난다 —
         그래서 **복사를 결정하는 단계**를 본다. 양성 대조가 이 관측이 살아 있음을 증명한다.)
    """
    CORRUPT = b'{"depts":{"d1":'

    def _shim(self):
        bindir = os.path.join(self.home, ".local", "bin")
        self.pylog = os.path.join(self.tmp, "py-calls.log")
        _write_exec(os.path.join(bindir, "python3"),
                    '#!/bin/sh\n'
                    'echo "$*" >> "%(log)s"\n'
                    'if [ -n "$PYSHIM_CORRUPT_ON_SET_FIELD" ] && [ "$#" -eq 5 ] \\\n'
                    '   && [ "$1" = "-" ] && [ "$4" = "$PYSHIM_CORRUPT_ON_SET_FIELD" ]; then\n'
                    '  printf %%s "$PYSHIM_CORRUPT_BYTES" > "$2"\n'
                    'fi\n'
                    'if [ -n "$PYSHIM_CRLF_AGENTS" ] && [ "$#" -eq 2 ] && [ "$1" = "-" ]; then\n'
                    '  case "$2" in\n'
                    '    *agents.json) "%(py)s" "$@" | awk \'{printf "%%s\\r\\n", $0}\'; exit 0 ;;\n'
                    '  esac\n'
                    'fi\n'
                    'exec "%(py)s" "$@"\n' % {"log": self.pylog, "py": sys.executable})
        self.env.setdefault("PYSHIM_CORRUPT_ON_SET_FIELD", "")
        self.env.setdefault("PYSHIM_CORRUPT_BYTES", "")
        self.env.setdefault("PYSHIM_CRLF_AGENTS", "")
        return bindir

    def _pycalls(self):
        if not os.path.exists(self.pylog):
            return []
        with open(self.pylog, encoding="utf-8") as f:
            return [l.rstrip("\n") for l in f if l.strip()]

    def _assert_shim_alive(self):
        """shim 이 실제로 끼어 있었는지 — 아니면 아래 '호출 0' 단언이 전부 공허해진다."""
        self.assertTrue(self._pycalls(), "픽스처 결함: python3 shim 이 한 번도 불리지 않았다")

    # ── M1: 조회 성공 → 기록 시점 손상 ───────────────────────────────────────
    def test_m1_cwd_write_corruption_after_successful_read_still_spawns(self):
        """★J5 M1 — `reg_get_field cwd` 성공 뒤 `reg_set_field` 의 판독 시점에 손상되면 setter
        **안쪽의 `exit 12`** 가 셸을 끝내 스폰 전에 중단됐다(`|| rot_reg_degraded` 로는 못 잡는다).
        서브셸 포착 뒤에는 재기동이 완주하고 rc 12·원본 보존만 남아야 한다.
        (mutation: 서브셸 괄호를 벗기면 여기서 red)"""
        self._shim()
        sock = seed_sock(self.home, "d1")
        os.remove(sock)                                   # rotate 가 rm 한 직후 형상
        write_reg(self.env, {"d1": {"socket": sock, "pack_dir": ""}})   # cwd 필드 없음 → setter 도달
        self.env.update({"PYSHIM_CORRUPT_ON_SET_FIELD": "cwd",
                         "PYSHIM_CORRUPT_BYTES": self.CORRUPT.decode()})
        rc, out, err = self.run_dept("launch", "d1", "--rotate")
        self._assert_shim_alive()

        with open(self.env["CYS_DEPTS_JSON"], "rb") as f:
            after = f.read()
        self.assertEqual(after, self.CORRUPT,
                         "★기록 시점 손상인데 setter 가 레지스트리를 다시 썼다(원본 보존 위반)")
        self.assertTrue(os.path.exists(sock),
                        "★조회 성공→기록 실패에서 재기동이 끊겼다 — 데몬 사망·등재 잔존(반파괴)\n"
                        "rc=%d\n%s" % (rc, err))
        self.assertEqual(rc, 12, "판독 실패 rc=%d(≠12)\n%s" % (rc, err))
        self.assertIn("기록 시점 손상", err, "기록 시점 관용 고지 부재(침묵한 강등 금지)")

    def test_m1_non_rotate_write_failure_keeps_exit10(self):
        """음성 대조: **비-rotate** `launch` 에서는 종전 계약 그대로 exit 12(관용 누수 0 · 1.1.8 병합: 우리 번호)."""
        self._shim()
        write_reg(self.env, {"d1": {"socket": "", "pack_dir": ""}})
        self.env.update({"PYSHIM_CORRUPT_ON_SET_FIELD": "cwd",
                         "PYSHIM_CORRUPT_BYTES": self.CORRUPT.decode()})
        rc, out, err = self.run_dept("launch", "d1")
        self._assert_shim_alive()
        self.assertEqual(rc, 12, "비-rotate 기록 실패가 exit 12 가 아니다(rc=%d) — 쓰기 계약 누수\n%s"
                         % (rc, err))
        self.assertNotIn("기록 시점 손상", err, "비-rotate 에 rotate 관용이 샜다")

    # ── M2: 계정 판독 실패 → 교차계정 토큰 주입 ─────────────────────────────
    def _creds_fixture(self, corrupt, keep_sock=False):
        """B dir 을 CYS_ACCOUNT_DIR 로 고정하고(격리 유지) 기본계정 A 의 토큰을 심어 둔다.

        `keep_sock=True` 는 소켓을 남겨 '이미 가동 중 — 재사용' 분기로 보낸다(자격증명 계정 결정은
        데몬 스폰 **이전**이라 관측에 영향 0 · `ready` 의 12s 부재 프로브를 치르지 않는다).
        손상 갈래는 rotate 면제 조건이 '소켓 부재'라 반드시 지운다."""
        self._shim()
        acct_b = os.path.join(self.tmp, "accounts", "B-d1")
        os.makedirs(acct_b, exist_ok=True)
        for key in ("default", "bkey"):
            base = os.path.join(self.home, ".cys", "claude-%s" % key)
            os.makedirs(base, exist_ok=True)
            with open(os.path.join(base, ".credentials.json"), "w", encoding="utf-8") as f:
                f.write('{"token":"%s"}' % key)
        catalog = os.path.join(self.home, ".cys", "dept-catalog.json")
        with open(catalog, "w", encoding="utf-8") as f:
            json.dump({"accounts": {}}, f)
        sock = seed_sock(self.home, "d1")
        if not keep_sock:
            os.remove(sock)
        write_reg(self.env, {"d1": {"socket": sock, "pack_dir": "", "account": "bkey"}})
        if corrupt:
            with open(self.env["CYS_DEPTS_JSON"], "wb") as f:
                f.write(self.CORRUPT)
        self.env.update({"CYS_DEPT_SEED_CREDS": "1", "CYS_ACCOUNT_DIR": acct_b,
                         "CYS_DEPT_CATALOG": catalog, "CYS_DEPT_DEFAULT_ACCOUNT": "default"})
        return sock, acct_b, catalog

    def test_m2_positive_control_account_resolution_is_observable(self):
        """양성 대조 — 레지스트리가 **읽히면** 등재 account('bkey')가 시드 원천으로 결정된다.
        이 관측이 살아 있어야 아래 음성 단언('호출 0')이 공허하지 않다."""
        sock, acct_b, catalog = self._creds_fixture(corrupt=False, keep_sock=True)
        rc, out, err = self.run_dept("launch", "d1", "--rotate")
        self._assert_shim_alive()
        picked = [c for c in self._pycalls() if c.startswith("- %s " % catalog)]
        self.assertTrue(picked, "양성 대조 붕괴: 시드 계정 해석(resolve_default_base)이 아예 안 불렸다\n%s" % err)
        self.assertTrue(any(c.endswith(" bkey") for c in picked),
                        "등재 account 가 아닌 값으로 시드 원천이 정해졌다: %r" % picked)

    def test_m2_degraded_account_never_falls_back_to_default(self):
        """★J5 M2 — 판독 실패에서 기본계정('default')으로 접으면 A 의 토큰이 B dir 에 심기고
        copy-if-absent 라 **복구 뒤에도 남는다**. 확정 못 하면 시드를 생략해야 한다.
        (mutation: 생략 분기를 없애고 기본계정 강등으로 되돌리면 여기서 red)"""
        sock, acct_b, catalog = self._creds_fixture(corrupt=True)
        rc, out, err = self.run_dept("launch", "d1", "--rotate")
        self._assert_shim_alive()
        picked = [c for c in self._pycalls() if c.startswith("- %s " % catalog)]
        self.assertFalse(any(c.endswith(" default") for c in picked),
                         "★판독 실패가 기본계정으로 접혔다 — 교차계정 토큰 주입 경로: %r" % picked)
        self.assertIn("자격증명 시드 생략", err, "시드 생략 고지 부재(침묵한 강등 금지)")
        self.assertFalse(os.path.exists(os.path.join(acct_b, ".credentials.json")),
                         "★다른 계정의 .credentials.json 이 부서 dir 에 심겼다(복구 후에도 잔존)")
        self.assertTrue(os.path.exists(sock), "시드 생략이 재기동까지 막았다(반파괴)")

    def _arm_victim(self, corrupt_bytes):
        """`graceful_kill` 의 SIGTERM 을 받고 죽으면서 레지스트리를 손상시키는 실 프로세스 +
        그 pid 를 내는 목 `cys identify`. kill **이전** 판독은 성공하고 이후는 전부 실패한다."""
        bindir = os.path.join(self.home, ".local", "bin")
        pidfile = os.path.join(self.tmp, "victim-m2a.pid")
        victim = os.path.join(self.tmp, "victim-m2a.py")
        with open(victim, "w", encoding="utf-8") as f:
            f.write(
                "import os, signal, sys, time\n"
                "from pathlib import Path\n"
                "def bye(*a):\n"
                "    Path(sys.argv[2]).write_bytes(%r)\n"
                "    os._exit(0)\n"
                "signal.signal(signal.SIGTERM, bye)\n"
                "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                "while True: time.sleep(0.05)\n" % (corrupt_bytes,))
        proc = subprocess.Popen([sys.executable, victim, pidfile, self.env["CYS_DEPTS_JSON"]])
        self.addCleanup(lambda: (proc.poll() is None) and (proc.kill(), proc.wait()))
        pid = _await_pid(pidfile)
        self.assertTrue(pid, "픽스처 결함: 목 데몬 pid 미기록")
        _write_exec(os.path.join(bindir, "cys"),
                    '#!/bin/sh\n'
                    'echo "cys $@" >> "%(log)s"\n'
                    'case "$1" in\n'
                    '  ping) [ -e "$CYS_SOCKET" ] && exit 0 || exit 1 ;;\n'
                    '  identify) printf \'{"daemon_pid":"%(pid)s","version":"0.0.1"}\\n\'; exit 0 ;;\n'
                    'esac\nexit 0\n' % {"log": self.log, "pid": pid})

    def test_m2a_precaptured_account_survives_post_kill_corruption(self):
        """★J5 M2 ⓐ — `rotate` 본체는 kill **이전**(아직 읽히는 시점)에 등재 account 를 선포착한다.
        그래서 kill 뒤 판독이 깨져도 시드 원천이 기본계정으로 강등되지 **않고** 등재 account('bkey')
        그대로다 — 격리를 유지하면서 시드도 생략하지 않는다(ⓑ 생략보다 나은 결과).
        (mutation: 선포착 블록을 지우면 ⓑ 로 떨어져 '시드 생략'이 되고 여기서 red)"""
        sock, acct_b, catalog = self._creds_fixture(corrupt=False, keep_sock=True)
        self._arm_victim(self.CORRUPT)
        rc, out, err = self.run_dept("rotate", "d1")
        self._assert_shim_alive()

        with open(self.env["CYS_DEPTS_JSON"], "rb") as f:
            self.assertEqual(f.read(), self.CORRUPT,
                             "픽스처 전제 붕괴: kill 시점 손상이 일어나지 않았다")
        picked = [c for c in self._pycalls() if c.startswith("- %s " % catalog)]
        self.assertTrue(any(c.endswith(" bkey") for c in picked),
                        "★선포착 account 가 재기동에 전달되지 않았다(시드 원천 결정 로그: %r)\n%s"
                        % (picked, err))
        self.assertFalse(any(c.endswith(" default") for c in picked),
                         "★기본계정으로 강등됐다 — 교차계정 토큰 주입 경로: %r" % picked)
        self.assertIn("kill 이전에 확인한 등재 account", err, "선포착 사용 고지 부재")
        self.assertTrue(os.path.exists(sock), "재기동이 끊겼다(반파괴)\nrc=%d\n%s" % (rc, err))

    # ── J6(codex 10차 minor · 보안축): 선포착 표식 `_CYS_ROTATE_ACCT` 위생 ──────
    def test_j6_exported_marker_from_outside_is_not_adopted(self):
        """★J6 ⓐ — 외부에서 `_CYS_ROTATE_ACCT` 를 export 한 채 손상 레지스트리로
        `launch <name> --rotate` 를 돌리면, 선포착을 **한 번도 하지 않고** 그 외부 값이 자격증명
        시드의 원천 계정으로 채택됐다(그 값이 '누구의 .credentials.json 을 복사하는가'를 정하고
        copy-if-absent 라 되돌릴 수 없다). 진입부 `unset` 뒤에는 종전 생략 갈래로 떨어져야 한다.
        (mutation: `unset _CYS_ROTATE_ACCT` 를 지우면 여기서 red)"""
        sock, acct_b, catalog = self._creds_fixture(corrupt=True)
        polluted = os.path.join(self.home, ".cys", "claude-POLLUTED")
        os.makedirs(polluted, exist_ok=True)
        with open(os.path.join(polluted, ".credentials.json"), "w", encoding="utf-8") as f:
            f.write('{"token":"POLLUTED"}')
        self.env["_CYS_ROTATE_ACCT"] = "POLLUTED"          # ← 오염(export)
        rc, out, err = self.run_dept("launch", "d1", "--rotate")
        self._assert_shim_alive()

        picked = [c for c in self._pycalls() if c.startswith("- %s " % catalog)]
        self.assertFalse(any(c.endswith(" POLLUTED") for c in picked),
                         "★외부 export 표식이 시드 원천으로 채택됐다: %r" % picked)
        self.assertFalse(picked,
                         "선포착 없는 판독 실패인데 시드 계정 해석이 일어났다(생략이어야 한다): %r" % picked)
        self.assertNotIn("kill 이전에 확인한 등재 account", err,
                         "★하지도 않은 선포착을 했다고 보고했다(외부 값 채택)")
        self.assertIn("자격증명 시드 생략", err, "시드 생략 고지 부재")
        self.assertFalse(os.path.exists(os.path.join(acct_b, ".credentials.json")),
                         "★오염 계정의 .credentials.json 이 부서 dir 에 심겼다")

    def test_j6_marker_is_not_inherited_by_the_spawned_daemon(self):
        """★J6 ⓑ — 선포착 대입이 **export 속성을 물려받지 않는다**(진입부가 `=""` 가 아니라
        `unset` 인 이유). 외부가 export 해 둔 채 실 `rotate` 를 돌려도 자식 cysd env 에
        `_CYS_ROTATE_ACCT` 가 없어야 한다 — 상속되는 노브는 그 부서에서 영구히 산다(P6 R1 의 교훈).
        (mutation: `unset` 을 지우면 외부 export 가 재대입 뒤에도 남아 자식에게 전달돼 red)"""
        sock, acct_b, catalog = self._creds_fixture(corrupt=False, keep_sock=True)
        dump = os.path.join(self.tmp, "cysd-env.txt")
        _write_exec(os.path.join(self.home, ".local", "bin", "cysd"),
                    '#!/bin/sh\nenv > "%s"\n'
                    'mkdir -p "$(dirname "$CYS_SOCKET")"\ntouch "$CYS_SOCKET"\nexit 0\n' % dump)
        self._arm_victim(self.CORRUPT)
        self.env["_CYS_ROTATE_ACCT"] = "POLLUTED"          # ← 오염(export)
        rc, out, err = self.run_dept("rotate", "d1")

        self.assertTrue(os.path.exists(dump),
                        "픽스처 전제 붕괴: 자식 cysd 가 스폰되지 않아 env 를 못 봤다\nrc=%d\n%s" % (rc, err))
        with open(dump, encoding="utf-8", errors="replace") as f:
            lines = f.read().split("\n")
        # 양성 대조 — env 덤프가 실제로 이 스폰의 것이다(이게 없으면 아래 '부재' 단언이 공허하다).
        self.assertTrue(any(l.startswith("CYS_SOCKET=") for l in lines),
                        "픽스처 결함: env 덤프에 스폰 env 가 없다")
        self.assertFalse(any(l.startswith("_CYS_ROTATE_ACCT=") for l in lines),
                         "★선포착 표식이 자식 cysd 에 상속됐다: %r"
                         % [l for l in lines if l.startswith("_CYS_ROTATE_ACCT=")])

    # ── M3: Windows 팩 시드 폴백의 CR ────────────────────────────────────────
    def test_m3_pack_seeded_acct_strips_cr(self):
        """★J5 M3 — Windows 네이티브 python 의 CRLF 가 `pack_seeded_acct` 폴백에만 남아
        `acctdir='…\\r'` 가 됐다(`reg_get_field` 경로는 `tr -d '\\r'` 로 벗긴다).
        (mutation: `| tr -d '\\r'` 를 지우면 여기서 red)"""
        self._shim()
        acct = os.path.join(self.tmp, "accounts", "packseed")
        os.makedirs(acct, exist_ok=True)
        pack = os.path.join(self.home, ".cys", "pack-dept-d1")
        os.makedirs(pack, exist_ok=True)
        with open(os.path.join(pack, "agents.json"), "w", encoding="utf-8") as f:
            json.dump({"claude": {"env": {"CLAUDE_CONFIG_DIR": acct}}}, f)
        # 계정 dir 유도는 데몬 스폰 이전이라 '재사용' 분기로 충분하다(ready 12s 부재 프로브 회피).
        sock = seed_sock(self.home, "d1")
        write_reg(self.env, {"d1": {"socket": sock, "pack_dir": pack}})   # account_dir 없음 → 팩 폴백
        self.env["PYSHIM_CRLF_AGENTS"] = "1"
        self.env.pop("CYS_ACCOUNT_DIR", None)
        rc, out, err = self.run_dept("launch", "d1")
        self._assert_shim_alive()
        self.assertEqual(rc, 0, "launch 실패(rc=%d)\n%s" % (rc, err))
        m = re.search(r"acct=(\S*)", out)
        self.assertIsNotNone(m, "확정 출력에 acct= 필드 부재\n%s" % out)
        self.assertNotIn("\r", m.group(1), "★acctdir 에 CR 이 남았다: %r" % m.group(1))
        self.assertEqual(m.group(1), acct, "acctdir 이 팩 시드값과 다르다: %r" % m.group(1))
        self.assertFalse(os.path.exists(acct + "\r"), "★CR 달린 계정 dir 이 새로 만들어졌다")


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

    # R4/T9: depts.json 손상은 doctor --fix 진입을 막을 근거가 아니다. 디스크 실존과
    # account_dir의 명시/agents.json 폴백을 각각 검증한다(EISDIR=권한/root 비의존 판독 불가).
    def test_unreadable_registry_existing_disk_repair_and_account_fallback(self):
        for unreadable in (False, True):
            reg = self.env["CYS_DEPTS_JSON"]
            if os.path.isfile(reg):
                os.unlink(reg)
            if unreadable:
                os.mkdir(reg)
            else:
                with open(reg, "wb") as f:
                    f.write(b'{"depts":')
            for disk in ("state", "pack"):
                with self.subTest(unreadable=unreadable, disk=disk):
                    name = "repair.%s.%s" % (disk, unreadable)
                    env = dict(self.env)
                    env.pop("CYS_ACCOUNT_DIR", None)
                    acct = os.path.join(self.home, "repair-account")
                    os.makedirs(acct, exist_ok=True)
                    pack = os.path.join(self.home, ".cys", "pack-dept-" + name)
                    state = os.path.join(self.home, ".local", "state", "cys-dept-" + name)
                    os.makedirs(state if disk == "state" else pack)
                    if disk == "state":
                        env["CYS_ACCOUNT_DIR"] = acct
                    else:
                        with open(os.path.join(pack, "agents.json"), "w", encoding="utf-8") as f:
                            json.dump({"claude": {"env": {"CLAUDE_CONFIG_DIR": acct}}}, f)
                    rc, out, err = self.run_dept(name, "--", "sh", "-c",
                        'printf "REPAIR=%s|%s|%s|%s\\n" "$CYS_SOCKET" "$CYS_PACK_DIR" '
                        '"$CYS_ACCOUNT_DIR" "${CYS_NO_AUTOSTART:-unset}"', env=env)
                    self.assertEqual(rc, 0, "기존 부서 수리 경로 차단\n" + err)
                    self.assertIn("REPAIR=%s|%s|%s|unset" % (
                        os.path.join(state, "cys.sock"), pack, acct), out)
                    self.assertEqual(self.calls(), "", "수리 진입에서 데몬 호출 발생")
            if unreadable:
                self.assertTrue(os.path.isdir(reg), "판독 불가 registry 경로 변조")
            else:
                with open(reg, "rb") as f:
                    self.assertEqual(f.read(), b'{"depts":', "수리 진입이 registry를 변경")

    def test_corrupt_registry_unknown_names_keep_validation_and_no_autostart(self):
        with open(self.env["CYS_DEPTS_JSON"], "wb") as f:
            f.write(b'{"depts":')
        rc, out, err = self.run_dept("unknown.bad", "--", "sh", "-c", "echo RAN")
        self.assertEqual(rc, 2, "손상 registry가 비실존·비정형 검증을 우회\n" + err)
        self.assertNotIn("RAN", out)
        rc, out, err = self.run_dept("unknown-good", "--", "sh", "-c",
                                    'echo "NA=${CYS_NO_AUTOSTART:-unset}"')
        self.assertEqual(rc, 0, err)
        self.assertIn("NA=1", out, "손상 registry에서 유령 autostart 차단 소실")
        self.assertEqual(self.calls(), "", "읽기 전용 컨텍스트가 데몬 호출")

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
class SockLenDiag(Base):
    """12) K2-07: sock_len_diag 는 진단 전용(항상 0 반환·스폰 전 거부 없음) — 상한은 OS 별(darwin/BSD 104 · Linux 108 ·
    NUL 포함 = Rust std `UnixListener::bind` 의 "path must be shorter than SUN_LEN"). 제품 함수 **그 자체**를 소스에서
    추출해 실행한다(javis_bootstrap self-test 의 dept_name_ok 소스 대조와 같은 방식 — 사본 금지)."""

    def _func_src(self):
        src = open(DEPT, encoding="utf-8").read()
        m = re.search(r"^sock_len_diag\(\)\{\n.*?^\}\n", src, re.S | re.M)
        self.assertIsNotNone(m, "cys-dept 에 sock_len_diag 정의 부재(K2-07 진단 소실)")
        return m.group(0)

    def _run_diag(self, path, uname):
        env = dict(self.env)
        bindir = os.path.join(self.tmp, "unamebin-" + uname.split("_")[0])
        os.makedirs(bindir, exist_ok=True)
        _write_exec(os.path.join(bindir, "uname"), "#!/bin/sh\necho %s\n" % uname)
        env["PATH"] = bindir + os.pathsep + env["PATH"]
        r = subprocess.run(["bash", "-c", self._func_src() + '\nsock_len_diag "$1"\n', "x", path],
                           capture_output=True, text=True, encoding="utf-8", env=env, timeout=30)
        return r.returncode, r.stdout, r.stderr

    @staticmethod
    def _path_of_bytes(n):
        head, tail = "/h/.local/state/cys-dept-", "/cys.sock"
        p = head + "a" * (n - len(head) - len(tail)) + tail
        assert len(p.encode("utf-8")) == n
        return p

    # 12) 순수 판정: 상한-1 무출력 / 상한 = 사유 1줄(바이트 수·상한 병기) · 두 OS · 항상 rc 0 · stdout 무오염
    def test_pure_threshold_per_os(self):
        for uname, lim in (("Darwin", 104), ("Linux", 108)):
            rc, out, err = self._run_diag(self._path_of_bytes(lim - 1), uname)
            self.assertEqual((rc, out, err), (0, "", ""), "%s: 상한-1 에서 오경보 (%r)" % (uname, err))
            rc, out, err = self._run_diag(self._path_of_bytes(lim), uname)
            self.assertEqual((rc, out), (0, ""), "%s: 진단이 rc/stdout 을 오염(rc=%d out=%r)" % (uname, rc, out))
            self.assertIn("sun_path", err, "%s: 상한 도달인데 사유 부재" % uname)
            self.assertIn("%dB ≥ %dB" % (lim, lim), err, "%s: 바이트 수·상한 병기 부재: %r" % (uname, err))

    # 12) 문자 수가 아니라 **바이트** 수: NFD 한글 홈 + 40자(계약 상한 안) = 106B → darwin 사유
    def test_nfd_home_counts_bytes_not_chars(self):
        nfd = unicodedata.normalize("NFD", "홍길동")
        self.assertNotEqual(nfd, "홍길동")   # 픽스처가 실제로 NFD 인지(핀 무효화 방지)
        p = "/Users/" + nfd + "/.local/state/cys-dept-" + "a" * 40 + "/cys.sock"
        self.assertEqual(len(p.encode("utf-8")), 106)
        rc, out, err = self._run_diag(p, "Darwin")
        self.assertEqual(rc, 0)
        self.assertIn("106B ≥ 104B", err, "NFD 홈을 문자 수로 재어 사유를 놓침: %r" % err)
        rc, out, err = self._run_diag(p, "Linux")
        self.assertEqual((rc, err), (0, ""), "Linux(108) 에서 106B 를 오경보")

    # 12) Windows named pipe 는 상한 없음 — 무출력
    def test_named_pipe_never_flagged(self):
        rc, out, err = self._run_diag("\\\\.\\pipe\\cys-dept-" + "a" * 200, "MINGW64_NT-10.0")
        self.assertEqual((rc, out, err), (0, "", ""))

    # 12) ★회귀 표본: 격리 HOME 아래 소켓이 상한을 넘어도(어떤 TMPDIR 이든 보장) 목 cysd 로 launch 완주 — 스폰 전 거부 금지
    def test_mkdtemp_home_over_limit_is_not_rejected_before_spawn(self):
        home, log, feedlist = make_home(os.path.join(self.tmp, "x" * 80))
        env = make_env(home)
        sock = os.path.join(home, ".local", "state", "cys-dept-a", "cys.sock")
        self.assertGreaterEqual(len(sock.encode("utf-8")), 104, "픽스처가 상한을 넘지 않음")
        write_reg(env, {})
        rc, out, err = self.run_dept("launch", "a", env=env)          # 목 cysd 스폰 경로(bind 없이 touch)
        self.assertEqual(rc, 0, "상한 초과 경로를 스폰 전에 거부(하네스 파손 회귀): exit=%d\n%s%s" % (rc, out, err))
        self.assertNotIn("sun_path", err, "성공 경로에 소켓 길이 사유가 섞임")
        self.assertIn("a", read_reg(env), "launch 완주인데 미등재")

    # 12) 기동 실패 경로: 소켓을 만들지 않는 목 cysd(bind 실패 재현) → exit 1 · 등재 회수 · 상한 초과일 때만 사유
    def test_daemon_start_failure_names_sock_len(self):
        _write_exec(os.path.join(self.home, ".local", "bin", "cysd"), "#!/bin/sh\nexit 0\n")
        write_reg(self.env, {})
        sock = os.path.join(self.home, ".local", "state", "cys-dept-a", "cys.sock")
        lim = 108 if sys.platform.startswith("linux") else 104
        over = len(sock.encode("utf-8")) >= lim
        rc, out, err = self.run_dept("launch", "a")
        self.assertEqual(rc, 1, "기동 실패 exit 계약(1) 회귀: %d\n%s%s" % (rc, out, err))
        self.assertIn("데몬 기동 실패", out + err)
        if over:
            self.assertIn("%dB" % len(sock.encode("utf-8")), err, "상한 초과 실패인데 소켓 길이 사유 부재: %r" % err)
        else:
            self.assertNotIn("sun_path", err, "상한 미만 실패에 소켓 길이 오진단")
        self.assertNotIn("a", read_reg(self.env), "기동 실패인데 등재 잔존(롤백 회귀)")

    # 12) 배선 census: "데몬 기동 실패" 를 내는 전 지점이 sock_len_diag 를 부른다 · 스폰 전 가드(assert_sock_len) 부활 금지
    def test_failure_sites_wired_and_no_prespawn_guard(self):
        src = open(DEPT, encoding="utf-8").read()
        sites = [l for l in src.splitlines() if "데몬 기동 실패" in l and "echo" in l and not l.lstrip().startswith("#")]
        self.assertGreaterEqual(len(sites), 3, "launch/allocate/create 기동 실패 지점 수 변동: %r" % sites)
        for l in sites:
            self.assertIn("sock_len_diag", l, "기동 실패 지점에 사유 배선 없음: %s" % l.strip())
        self.assertIsNone(re.search(r"^\s*assert_sock_len\b", src, re.M),
                          "스폰 전 소켓 길이 거부(assert_sock_len)가 부활 — 목 cysd 하네스·Linux 108 과 충돌")


class CrlfHygiene(Base):
    # 13) `read < <(python3 …)` 파이프 소비자는 전부 `| tr -d '\r'` — Windows 임베디드 python 의 \r\n(cys-dept reg_names 규칙)
    def test_procsub_consumers_strip_cr(self):
        src = open(DEPT, encoding="utf-8").read()
        lines = [l for l in src.splitlines() if "< <(python3" in l and not l.lstrip().startswith("#")]
        self.assertGreaterEqual(len(lines), 1, "process-substitution 소비자 0 — 검사 대상이 사라짐(census 갱신 필요)")
        for l in lines:
            self.assertIn("tr -d '\\r'", l, "\\r 미소거 파이프 소비자(create cwd 등재 \\r 오염 경로): %s" % l.strip())


class PostSpawnRegistryFailure(Base):
    """R4/Q3: 판독 실패 EXIT는 이번 호출이 만든 PID만 정리한다(실제 생존 목으로 검증).

    ready 파일을 공개하기 전에 오염을 완료하므로 시간 경합 없이 후행 read가 실패한다.
    allocate는 정상 후행 read가 없어 계정시드 실패→down의 read 실패(rc10)로 들어간다.
    테스트 정리는 픽스처가 기록한 자기 PID만 대상으로 하므로 변이 실행도 orphan을 남기지 않는다.
    """
    BAD_REGISTRY = b'{"depts":{"keep":'

    def _fixture(self, verb, reuse_dead=False, existing=False, competing=False):
        CreateGate._seed_catalog(self, "k1", "m1")
        directives = self._seed_promotable(ndepts=0)
        self.env.pop("CYS_ACCOUNT_DIR", None)
        self.env["CYS_DEPT_DEFAULT_ACCOUNT"] = "test"
        # create/allocate 모두 미승격 상태에서 시작한다. 실패 전에 신규 CEO 승격이
        # 일어나지 않아야 한다(이미 승격된 fixture만 쓰면 순서 결함을 놓친다).
        paths = [os.path.join(directives, n) for n in (
            "MASTER_DIRECTIVE.md", "MASTER_DIRECTIVE.md.pre-ceo", "CEO_TEMPLATE.md",
            ".ceo-template-applied")]
        paths.append(os.path.join(self.home, ".cys", "state", "ceo-pending"))
        self.ceo_before = {p: self._bytes_or_missing(p) for p in paths}
        self.sock = os.path.join(self.home, ".local", "state", "cys-dept-dept-1", "cys.sock")
        if reuse_dead:
            write_reg(self.env, {"dept-1": {"socket": self.sock, "mission_key": "m1",
                                            "reserved_at": 0}})
        self.pidfile = os.path.join(self.tmp, "owned-daemon.pid")
        self.termfile = os.path.join(self.tmp, "owned-daemon.term")
        self.startfile = os.path.join(self.tmp, "daemon-starts")
        self.env.update({"GUARD_PID_FILE": self.pidfile, "GUARD_TERM_FILE": self.termfile,
                         "GUARD_START_FILE": self.startfile, "GUARD_CALL_LOG": self.log,
                         "GUARD_PING_COUNT": os.path.join(self.tmp, "ping-count"),
                         "GUARD_TARGET_SOCKET": self.sock,
                         "GUARD_EXISTING": "1" if existing else "0",
                         "GUARD_COMPETING": "1" if competing else "0",
                         "GUARD_FAIL_SEED": "1" if verb == "allocate" else "0"})
        helper = os.path.join(self.tmp, "owned-daemon-fixture.py")
        with open(helper, "w", encoding="utf-8") as f:
            f.write('''import os, signal, sys, time
from pathlib import Path
env = os.environ
def corrupt():
    Path(env["CYS_DEPTS_JSON"]).write_bytes(%r)
    if env["GUARD_FAIL_SEED"] == "1":
        # 실제 계정시드 fail-closed → down의 registry read rc10 경로를 유발한다.
        (Path(env["HOME"]) / ".cys/pack/agents.json").write_text('{"claude":{}}')
if sys.argv[1] == "winner":
    # 이번 cys-dept의 자식이 스폰되고 경쟁 패자로 사망한 뒤에만 승자의 ready를 공개한다.
    # 실제 두 프로세스를 쓰되 소켓은 기존 하네스처럼 파일 기반 목(실 bind 불필요)이다.
    pidfile = Path(env["GUARD_PID_FILE"])
    while True:
        try:
            loser = int(pidfile.read_text())
            break
        except (OSError, ValueError):
            time.sleep(0.02)
    while True:
        try:
            os.kill(loser, 0)
        except ProcessLookupError:
            break
        time.sleep(0.02)
    corrupt()
    sock = Path(env["GUARD_TARGET_SOCKET"])
    sock.parent.mkdir(parents=True, exist_ok=True)
    Path(str(sock)).with_suffix(".lock").write_text(str(os.getpid()))
    sock.write_text(str(os.getpid()))
    while True:
        signal.pause()
elif sys.argv[1] == "daemon":
    def terminate(signum, frame):
        Path(env["GUARD_TERM_FILE"]).write_text(str(os.getpid()))
        sys.exit(0)
    signal.signal(signal.SIGTERM, terminate)
    Path(env["GUARD_PID_FILE"]).write_text(str(os.getpid()))
    with open(env["GUARD_START_FILE"], "a") as out:
        out.write(str(os.getpid()) + "\\n")
    if env["GUARD_COMPETING"] == "1":
        sys.exit(0)  # singleton 경쟁 패자: 소켓/lock을 소유하지 않은 채 종료
    if env["GUARD_EXISTING"] != "1":
        corrupt()
    sock = Path(env["CYS_SOCKET"])
    sock.parent.mkdir(parents=True, exist_ok=True)
    Path(str(sock)).with_suffix(".lock").write_text(str(os.getpid()))
    sock.touch()
    while True:
        signal.pause()
else:
    args = sys.argv[2:]
    with open(env["GUARD_CALL_LOG"], "a") as out:
        out.write("cys " + " ".join(args) + "\\n")
    if args and args[0] == "ping":
        sock = env.get("CYS_SOCKET", "")
        if env["GUARD_COMPETING"] == "1":
            if sock != env["GUARD_TARGET_SOCKET"]:
                sys.exit(1)
            try:
                winner = int(Path(sock).read_text())
                os.kill(winner, 0)  # 파일 존재만으로 성공시키지 않는다: 실제 승자가 살아 있어야 응답
            except (OSError, ValueError):
                sys.exit(1)
            with open(env["GUARD_CALL_LOG"], "a") as out:
                out.write("pong " + str(winner) + "\\n")
            print(winner)
            sys.exit(0)
        if env["GUARD_EXISTING"] == "1" and sock == env["GUARD_TARGET_SOCKET"]:
            # 예약 시 미생존 → 직후 ready에서 기존 데몬이 응답하는 경합을 재현.
            counter = Path(env["GUARD_PING_COUNT"])
            count = int(counter.read_text()) + 1 if counter.exists() else 1
            counter.write_text(str(count))
            if count == 1:
                sys.exit(1)
            corrupt()
        sys.exit(0 if sock and Path(sock).exists() else 1)
    if args and args[0] == "identify":
        print(Path(env["GUARD_PID_FILE"]).read_text())
    sys.exit(0)
''' % self.BAD_REGISTRY)
        bindir = os.path.join(self.home, ".local", "bin")
        for name, mode in (("cys", "client"), ("cysd", "daemon")):
            _write_exec(os.path.join(bindir, name), "#!/bin/sh\nexec %s %s %s \"$@\"\n" % (
                shlex.quote(sys.executable), shlex.quote(helper), mode))
        # Mutation control may leave the newly spawned child running. Always reclaim that exact PID.
        self.addCleanup(self._cleanup_owned_daemon)
        if competing:
            self.winner_process = subprocess.Popen(
                [sys.executable, helper, "winner"], env=self.env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.addCleanup(self._cleanup_winner)
            self.assertIsNone(self.winner_process.poll(), "경쟁 승자 fixture 미기동")
        if existing:
            env = dict(self.env, CYS_SOCKET=self.sock)
            proc = subprocess.Popen([sys.executable, helper, "daemon"], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.addCleanup(lambda: proc.wait(timeout=5))
            # addCleanup is LIFO: signal before wait, and wait only our direct child.
            self.addCleanup(self._cleanup_owned_daemon)
            self.assertTrue(self._wait_for(lambda: os.path.exists(self.sock)), "기존 데몬 fixture 미기동")
            self.assertIsNone(proc.poll(), "기존 데몬 positive control이 이미 사망")
            self.existing_process = proc

    @staticmethod
    def _bytes_or_missing(path):
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    @staticmethod
    def _wait_for(predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.02)
        return predicate()

    @staticmethod
    def _pid_alive(pid):
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False

    def _cleanup_owned_daemon(self):
        if not os.path.exists(self.pidfile):
            return
        if hasattr(self, "existing_process") and self.existing_process.poll() is not None:
            return
        with open(self.pidfile) as f:
            pid = int(f.read())
        try:
            if self._pid_alive(pid):
                os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass  # 정상 EXIT cleanup과 fixture 종료가 겹칠 수 있다.

    def _cleanup_winner(self):
        proc = self.winner_process
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    def _assert_failure(self, verb, existing=False, reuse_dead=False, competing=False):
        self._fixture(verb, reuse_dead=reuse_dead, existing=existing, competing=competing)
        args = ("create", "k1") if verb == "create" else ("allocate",)
        rc, out, err = self.run_dept(*args)
        self.assertEqual(rc, 12, "스폰 이후 판독 실패가 exit12로 전파되지 않음\n" + out + err)
        self.assertIn("판독 실패", err)   # 1.1.8 병합: 우리 문면(「부서 목록(…) 판독 실패(…)」)
        with open(self.pidfile) as f:
            pid = int(f.read())
        with open(self.startfile) as f:
            self.assertEqual(f.read().splitlines(), [str(pid)], "중복 데몬 스폰")
        if competing:
            winner = self.winner_process
            self.assertNotEqual(pid, winner.pid, "경쟁 승자/패자 PID가 같음")
            self.assertFalse(self._pid_alive(pid), "스폰 경쟁 패자가 아직 생존")
            self.assertIn("pong %d\n" % winner.pid, self.calls(), "후행 ready가 경쟁 승자의 응답을 못 받음")
            self.assertIsNone(winner.poll(), "스폰 경쟁 승자를 EXIT가 죽임")
            self.assertTrue(os.path.exists(self.sock), "경쟁 승자의 소켓을 EXIT가 삭제")
            self.assertEqual(self._bytes_or_missing(self.sock), str(winner.pid).encode())
            self.assertEqual(self._bytes_or_missing(startup_lock(self.sock)), str(winner.pid).encode(),
                             "경쟁 승자의 startup-lock(cys.lock)을 EXIT가 변경/삭제")
            probe = subprocess.run([os.path.join(self.home, ".local", "bin", "cys"), "ping"],
                                   env=dict(self.env, CYS_SOCKET=self.sock),
                                   capture_output=True, text=True, timeout=5)
            self.assertEqual(probe.returncode, 0, "회수 뒤 경쟁 승자의 소켓 응답 단절: " + probe.stderr)
            self.assertEqual(probe.stdout.strip(), str(winner.pid))
            self.assertFalse(os.path.exists(self.termfile), "이미 죽은 경쟁 패자에 SIGTERM 발생")
        elif existing:
            self.assertIsNone(self.existing_process.poll(), "ready 재사용 데몬을 EXIT가 죽임")
            self.assertTrue(os.path.exists(self.sock), "ready 재사용 소켓을 EXIT가 삭제")
            self.assertFalse(os.path.exists(self.termfile), "기존 PID에 SIGTERM 발송")
        else:
            self.assertTrue(self._wait_for(lambda: not self._pid_alive(pid)),
                            "판독 실패 뒤 이번 호출의 cysd PID %d가 orphan으로 생존" % pid)
            self.assertTrue(os.path.exists(self.termfile), "신규 PID의 graceful SIGTERM 정리 미수행")
            self.assertTrue(os.path.exists(self.sock), "소유권 미확인 소켓을 EXIT가 삭제")
        self.assertTrue(os.path.exists(startup_lock(self.sock)), "소유권 미확인 startup-lock(cys.lock)을 EXIT가 삭제")
        self.assertEqual(self._bytes_or_missing(self.env["CYS_DEPTS_JSON"]), self.BAD_REGISTRY,
                         "실패 정리가 손상 레지스트리 바이트를 변경")
        self.assertNotIn("tombstone", self.calls(), "판독 실패 정리가 묘비를 변경")
        for path, before in self.ceo_before.items():
            self.assertEqual(self._bytes_or_missing(path), before, "판독 실패 중 CEO 변경: " + path)

    def test_create_new_read_failure_reclaims_only_spawned_pid(self):
        self._assert_failure("create")

    def test_create_reuse_dead_read_failure_reclaims_only_spawned_pid(self):
        self._assert_failure("create", reuse_dead=True)

    def test_allocate_read_failure_reclaims_only_spawned_pid(self):
        self._assert_failure("allocate")

    def test_create_read_failure_keeps_ready_existing_daemon(self):
        self._assert_failure("create", existing=True)

    def test_allocate_read_failure_keeps_ready_existing_daemon(self):
        self._assert_failure("allocate", existing=True)

    def test_create_spawn_loser_preserves_live_winner(self):
        self._assert_failure("create", competing=True)

    def test_windows_cleanup_maps_owned_pid_and_never_targets_unowned_pid(self):
        """실기 검증 아님: 실제 함수 + uname/ps/taskkill/kill/wait 목으로 MSYS 분기 계약만 검증."""
        with open(DEPT, encoding="utf-8") as f:
            src = f.read()
        funcs = []
        for name in ("graceful_kill", "cleanup_owned_dept_spawn"):
            match = re.search(r"^%s\(\)\{\n.*?^\}\n" % name, src, re.M | re.S)
            self.assertIsNotNone(match, name + " 정의 부재")
            funcs.append(match.group(0))
        for mode in ("mapped", "unowned", "unmapped", "zero", "system", "survivor"):
            with self.subTest(mode=mode):
                sock = seed_sock(self.home, "win-cleanup-" + mode)
                env = dict(self.env, GUARD_WIN_LOG=os.path.join(self.tmp, "win-" + mode),
                           GUARD_WIN_PS="PPID PID WINPID COMMAND\n1 12345 92345 cysd.exe",
                           GUARD_WIN_CHILD="" if mode == "unowned" else "12345",
                           GUARD_WIN_MODE=mode)
                if mode == "unmapped":
                    env["GUARD_WIN_PS"] = "PID PPID COMMAND\n12345 1 cysd.exe"
                elif mode in ("zero", "system"):
                    env["GUARD_WIN_PS"] = "PID PPID WINPID COMMAND\n12345 1 %s cysd.exe" % (
                        "0" if mode == "zero" else "1")
                # 셸 builtin까지 목으로 가려 임의 숫자 PID를 실 OS에 전달할 수 없다.
                script = '''set -euo pipefail
uname(){ echo MINGW64_NT-10.0; }
kill(){ printf 'kill %s\\n' "$*" >> "$GUARD_WIN_LOG"; [ "${GUARD_WIN_KILLED:-0}" != 1 ]; }
wait(){ printf 'wait %s\\n' "$*" >> "$GUARD_WIN_LOG"; return 0; }
ps(){ printf '%s\\n' "$GUARD_WIN_PS"; }
sleep(){ :; }
taskkill(){
  printf 'taskkill %s\\n' "$*" >> "$GUARD_WIN_LOG"
  if [ "$GUARD_WIN_MODE" != survivor ]; then GUARD_WIN_KILLED=1; fi
  return 0
}
''' + "\n".join(funcs) + '''
_dept_spawn_pid="$GUARD_WIN_CHILD"
sock="$1"
cleanup_owned_dept_spawn
'''
                r = subprocess.run(["bash", "-c", script, "cleanup-pin", sock], env=env,
                                   capture_output=True, text=True, timeout=10)
                self.assertEqual(r.returncode, 0, r.stderr)
                calls = self._bytes_or_missing(env["GUARD_WIN_LOG"]) or b""
                if mode == "mapped":
                    self.assertIn(b"taskkill //PID 92345 //T //F\n", calls)
                    self.assertNotIn(b"taskkill //PID 12345", calls, "POSIX PID를 native taskkill에 전달")
                    self.assertIn(b"wait 12345\n", calls)
                    self.assertTrue(os.path.exists(sock), "소유 자식 종료만으로 소켓을 삭제")
                elif mode == "survivor":
                    self.assertIn(b"taskkill //PID 92345 //T //F\n", calls)
                    self.assertNotIn(b"wait ", calls, "종료 미확인 자식을 무기한 wait")
                    self.assertTrue(os.path.exists(sock), "종료 미확인 소켓을 삭제")
                    self.assertIn("종료 미확인", r.stderr)
                    self.assertLess(calls.count(b"kill -0 "), 20, "bounded 종료 확인 퇴행")
                else:
                    self.assertNotIn(b"taskkill", calls, "소유/매핑 미확정 PID를 종료")
                    self.assertTrue(os.path.exists(sock), "소유/매핑 미확정 소켓을 삭제")
                    if mode == "unowned":
                        self.assertEqual(calls, b"", "ready 재사용 경로에서 PID probe/종료 발생")
                    else:
                        self.assertIn("WINPID 미확인", r.stderr)


class RegistryBom(Base):
    def _registry_python(self):
        """$REG 를 받는 Python 본문 전수 추출 — 변수명이 아닌 호출 인자로 판독 범위를 정한다."""
        with open(DEPT, encoding="utf-8") as f:
            src = f.read()
        blocks = [(m.start(2), m.group(2)) for m in re.finditer(
            r"^([^\n]*\bpython3\b[^\n]*<<'PY'[^\n]*)\n(.*?)^PY\s*$", src, re.M | re.S)
                  if '"$REG"' in m.group(1)]
        for line in src.splitlines():
            if "python3 -c " in line and '"$REG"' in line and not line.lstrip().startswith("#"):
                args = shlex.split(line)
                body = args[args.index("-c") + 1]
                if body.startswith("$"):
                    # 1.1.8 병합: 우리 공용 판독 본문(`reg_read_py='…'` 셸 변수)을 정의 원문으로 풀어 census 에 넣는다.
                    mv = re.search(r"^%s='(.*?)'$" % re.escape(body[1:].strip("{}")), src, re.M | re.S)
                    self.assertIsNotNone(mv, "셸 변수 본문 %s 정의를 찾지 못했다 — census 추출 규칙 갱신 필요" % body)
                    body = mv.group(1)
                blocks.append((src.index(line), body))
        self.assertTrue(blocks, "레지스트리 Python 본문 0 — census 추출 규칙 갱신 필요")
        return [(src.count("\n", 0, pos), ast.parse(body)) for pos, body in blocks]

    # 14) census: 모든 레지스트리 read open 은 명시적 utf-8-sig — utf-8 로 퇴행해도 실패해야 한다.
    def test_no_encoding_blind_registry_reader(self):
        readers, blind = 0, []
        for line, tree in self._registry_python():
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"):
                    continue
                kw = {k.arg: k.value for k in node.keywords}
                mode = ast.literal_eval(kw.get("mode", node.args[1] if len(node.args) > 1 else ast.Constant("r")))
                if not mode.startswith("r"):
                    continue    # .lock / 원자 교체 tmp 쓰기는 별도 계약(UTF-8 출력).
                readers += 1
                encoding = kw.get("encoding")
                if "b" in mode:
                    # 1.1.8 병합: 우리 판독(A1-F3 · 정확히 0바이트 판정)은 바이트로 읽고 같은 본문에서 `.decode("utf-8-sig")` 한다.
                    if not any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "decode"
                               and c.args and isinstance(c.args[0], ast.Constant) and c.args[0].value == "utf-8-sig"
                               for c in ast.walk(tree)):
                        blind.append(line + node.lineno)
                    continue
                if not (isinstance(encoding, ast.Constant) and encoding.value == "utf-8-sig"):
                    blind.append(line + node.lineno)
        self.assertGreater(readers, 0, "레지스트리 read open 0 — census가 무효")
        self.assertEqual(blind, [], "utf-8-sig 아닌 레지스트리 판독 잔존(cys-dept 줄): %r" % blind)

    # P1: except Exception → 빈 레지스트리 복구는 cp949/잘린 JSON 을 원자 덮어쓰기하던 데이터 소실 원인.
    def test_no_exception_resets_registry(self):
        resets = []
        for line, tree in self._registry_python():
            for node in ast.walk(tree):
                if not (isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name)
                        and node.type.id == "Exception"):
                    continue
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Assign):
                        try:
                            if ast.literal_eval(stmt.value) == {"depts": {}}:
                                resets.append(line + stmt.lineno)
                        except (ValueError, TypeError):
                            pass
        self.assertEqual(resets, [], "Exception 을 빈 레지스트리로 접는 경로 잔존(cys-dept 줄): %r" % resets)

    def test_rmw_read_failure_survives_fail_open_or_consumer(self):
        # R4/Q1: allocate cwd WARN 리터럴은 CI 계약이다. 호출부의 `|| echo WARN`가 RMW
        # 판독 실패를 삼키지 못하도록 실제 reg_set_field 경계의 exit12(1.1.8 병합: 우리 번호)를 행동으로 검증한다.
        with open(DEPT, encoding="utf-8") as f:
            src = f.read()
        init = re.search(r"^reg_init\(\)\{.*?^\}\n", src, re.M | re.S)   # 1.1.8 병합: 우리 reg_init = 여러 줄(잠금 안 0바이트 재판정)
        setter = re.search(r"^reg_set_field\(\)\{.*?^\}\n", src, re.M | re.S)
        self.assertIsNotNone(init, "reg_init 정의 부재")
        self.assertIsNotNone(setter, "reg_set_field 정의 부재")
        script = ('set -euo pipefail\nREG="$1"\n' + init.group(0) + setter.group(0)
                  + '\nreg_set_field keep cwd "$HOME" || echo WARN-CONSUMED\necho SURVIVED\n')
        write_reg(self.env, {"keep": {}})
        good = subprocess.run(["bash", "-c", script, "rmw-pin", self.env["CYS_DEPTS_JSON"]],
                              env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("SURVIVED", good.stdout, "정상 RMW positive control 실패")
        self.assertEqual(read_reg(self.env)["keep"]["cwd"], self.home)
        data = b'{"depts":{"keep":'
        self._write_bad_registry(data)
        bad = subprocess.run(["bash", "-c", script, "rmw-pin", self.env["CYS_DEPTS_JSON"]],
                             env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(bad.returncode, 12, "OR 소비자가 판독 실패를 삼킴\n" + bad.stdout + bad.stderr)
        self.assertEqual(bad.stdout, "", "판독 실패 뒤 WARN/후행 명령 실행")
        self.assertIn("판독 실패", bad.stderr)   # 1.1.8 병합: 우리 문면
        with open(self.env["CYS_DEPTS_JSON"], "rb") as f:
            self.assertEqual(f.read(), data, "실패 뒤 원본 바이트 변경")

    def _write_bad_registry(self, data):
        with open(self.env["CYS_DEPTS_JSON"], "wb") as f:
            f.write(data)

    def _assert_registry_read_failure(self, data, *args):
        self._write_bad_registry(data)
        rc, out, err = self.run_dept(*args)
        self.assertEqual(rc, 12, "%r: 손상 레지스트리 exit=%d(≠12)\n%s%s" % (args, rc, out, err))
        self.assertEqual(len(err.splitlines()), 1, "판독 실패 사유는 stderr 1줄이어야 한다: %r" % err)
        # 1.1.8 병합: 우리 문면(「부서 목록(<경로>) 판독 실패(<사유>) — 등록 부서를 지키려고 아무것도 바꾸지 않았습니다」)
        self.assertIn("[cys-dept] 부서 목록(" + self.env["CYS_DEPTS_JSON"] + ") 판독 실패(", err)
        with open(self.env["CYS_DEPTS_JSON"], "rb") as f:
            self.assertEqual(f.read(), data, "판독 실패 뒤 원본 레지스트리 바이트 변동")
        return out

    # P1: launch 의 slug 확인·RMW 어느 단계에서도 디코딩/파싱 실패를 빈 등재로 바꿀 수 없다.
    def test_cp949_registry_launch_preserves_bytes(self):
        data = json.dumps({"depts": {"keep": {"display_name": "영업부(한국)"}}}, ensure_ascii=False).encode("cp949")
        self._assert_registry_read_failure(data, "launch", "newer")

    def test_truncated_registry_launch_preserves_bytes(self):
        self._assert_registry_read_failure(b'{"depts":{"keep":{"account":"work"}', "launch", "newer")

    def test_utf16_registry_launch_preserves_bytes(self):
        data = json.dumps({"depts": {"keep": {"mission_key": "m1"}}}).encode("utf-16")
        self._assert_registry_read_failure(data, "launch", "newer")

    def test_invalid_registry_list_is_not_empty_success(self):
        out = self._assert_registry_read_failure(b'{"depts":', "list")
        self.assertEqual(out, "", "판독 실패 list가 정상 목록을 출력")

    # P1: reg_count 소비자도 실패를 0개로 접지 않는다(승격/강등 판단에 빈 값 사용 금지).
    def test_invalid_registry_promote_count_fails_closed(self):
        pack = self._seed_promotable(ndepts=1)
        self._assert_registry_read_failure(b'{"depts":', "promote-ceo")
        with open(os.path.join(pack, "MASTER_DIRECTIVE.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "STANDARD-MASTER\n", "판독 실패인데 CEO 승격 발생")
        self.assertFalse(os.path.exists(self._receipt()), "판독 실패인데 승격 영수증 생성")

    # P1: 등재/역인덱스 판독 실패 시 teardown·reg_count=0 오판·CEO 강등 모두 금지.
    def test_invalid_registry_teardown_keeps_ceo_and_socket(self):
        pack = self._seed_promotable(ndepts=1)
        rc, out, err = self.run_dept("promote-ceo")
        self.assertEqual(rc, 0, out + err)
        sock = seed_sock(self.home, "d0")
        paths = [os.path.join(pack, "MASTER_DIRECTIVE.md"),
                 os.path.join(pack, "MASTER_DIRECTIVE.md.pre-ceo"), self._receipt()]
        before = {}
        for p in paths:
            with open(p, "rb") as f:
                before[p] = f.read()
        for args in (("down", "d0"), ("down-sock", sock), ("rotate", "d0")):
            with self.subTest(args=args):
                seed_sock(self.home, "d0")
                before_calls = self.calls()
                self._assert_registry_read_failure(b'{"depts":', *args)
                self.assertTrue(os.path.exists(sock), "판독 실패인데 소켓 teardown 발생")
                self.assertEqual(self.calls(), before_calls, "판독 실패인데 cys 프로브/teardown 호출")
                for p, data in before.items():
                    with open(p, "rb") as f:
                        self.assertEqual(f.read(), data, "판독 실패인데 CEO 강등/영수증 변경: %s" % p)

    # 14) 동작: BOM 달린 depts.json(기존 등재 1건) → list 에 보이고, 다른 이름 launch(reg_upsert RMW) 뒤에도 기존 등재·메타 보존
    def test_bom_registry_survives_rmw(self):
        keep_sock = seed_sock(self.home, "keep")
        keep = {"socket": keep_sock, "pack_dir": "", "display_name": "영업부(한국)",
                "account": "work", "mission_key": "sales", "cwd": self.home}
        with open(self.env["CYS_DEPTS_JSON"], "wb") as f:
            f.write(b"\xef\xbb\xbf" + json.dumps(
                {"depts": {"keep": keep}}, ensure_ascii=False).encode("utf-8"))
        rc, out, err = self.run_dept("list")
        self.assertEqual(rc, 0, err)
        self.assertIn("keep", out.split(), "BOM 레지스트리의 등재가 list 에 안 보임")
        seed_sock(self.home, "newer")
        rc, out, err = self.run_dept("launch", "newer")
        self.assertEqual(rc, 0, "launch 실패\n%s%s" % (out, err))
        reg = read_reg(self.env)
        self.assertIn("newer", reg)
        self.assertIn("keep", reg, "BOM 레지스트리가 RMW 에서 비워짐(기존 등재 소실 · K2-03 회귀)")
        self.assertEqual(reg["keep"], keep, "기존 부서 display_name/account/mission_key/cwd 메타 소실")


if __name__ == "__main__":
    unittest.main(verbosity=2)
