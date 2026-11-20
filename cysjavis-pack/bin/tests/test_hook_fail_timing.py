"""test_hook_fail_timing — 훅 실패 한 줄에 「훅이 그때까지 걸린 시간」과 「데몬 시작 시각」을 싣는다.

왜: 윈도우에서 훅 안쪽 상한 초과(rc124)가 상한 길이(2·5·8초)와 무관하게 간간이 난다. 원인 후보(기기 환경의 간헐 정지 ·
훅 도중 절전 복귀 · 좌석 동시 기동)를 가르려면 실패 순간의 두 값이 필요하다:
  · took = 훅 셸이 시작된 뒤 지난 초(bash 내장 SECONDS — 외부 프로세스 0). 상한과 비슷하면 「그만큼 멈췄다」,
    상한보다 훨씬 크면(분·시간) 「훅 도중 잠들었다 깨어났다」 쪽이다.
  · dstart = 데몬 시작 시각(<상태 dir>/delivery-base.epoch.json 의 started — 데몬 write_epoch 가 기동 때 1회 씀).
    실패 시각과 빼면 「데몬 시작 뒤 경과」가 나온다(신호의 last_boot 와 같은 출처).
계약: ①두 칸은 rc 바로 뒤 · path 는 여전히 맨 끝(PATH 에 공백이 있을 수 있다) ②셸 내장만(PATH 가 빈 순간에도)
③없거나 이상한 값은 「-」 ④stdout 무출력 · 종료 코드 불변(기존 계약 그대로).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks")
# 윈 Git Bash·맥 /bin/sh 는 bash 다 — 계측 칸은 bash 로 시험하고, SECONDS·read -n 이 없는 dash 는 강등만 따로 본다.
BASH = shutil.which("bash")
DASH = shutil.which("dash")
BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP_CYS = ("CYS_PY", "CYS_PY_ORIGIN")


def _base_env():
    # 상담소 신호 쓰기는 끈다(이 시험은 로컬 한 줄만 본다 — 실 상담소 폴더 오염 방지).
    env = {k: v for k, v in os.environ.items() if not k.startswith("CYS_") or k in KEEP_CYS}
    env["CYS_PACK_DIR"] = "/nonexistent-pack-for-hook-timing-test"
    return env


@unittest.skipUnless(BASH, "bash 없음")
class T(unittest.TestCase):
    def setUp(self):
        self.st = tempfile.mkdtemp(prefix="hft-")
        self.env = dict(_base_env(), CYS_STATE_DIR=self.st, CYS_ROLE="master", CYS_SURFACE_ID="7")
        self.log = os.path.join(self.st, "hook-errors.log")
        self.epoch = os.path.join(self.st, "delivery-base.epoch.json")

    def tearDown(self):
        shutil.rmtree(self.st, ignore_errors=True)

    def run_sh(self, body, sh=None):
        r = subprocess.run([sh or BASH, "-c", '. "%s/_lib.sh"; %s' % (HOOKS, body)], capture_output=True, text=True,
                           env=self.env, timeout=30)
        ln = open(self.log, encoding="utf-8").read().splitlines() if os.path.exists(self.log) else []
        return r, ln

    def write_epoch(self, started):
        # 데몬 delivery.rs write_epoch 와 같은 꼴(serde_json to_string = 공백 없는 한 줄 · 끝 개행 없음).
        with open(self.epoch, "w", encoding="utf-8") as f:
            f.write(json.dumps({"v": 1, "daemon_epoch": 1793983606.13, "started": started, "pid": 90624,
                                "socket": "/x/cys.sock"}, separators=(",", ":")))

    def test_took_counts_hook_wall_seconds(self):
        r, ln = self.run_sh('sleep 2; cys_hook_fail dept-chat-inject 124 x; exit 0')
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual(len(ln), 1, ln)
        m = re.search(r" rc=124 took=(\d+)s dstart=", ln[0])
        self.assertIsNotNone(m, ln[0])
        self.assertGreaterEqual(int(m.group(1)), 2, ln[0])
        self.assertLess(int(m.group(1)), 20, ln[0])

    def test_dstart_from_daemon_epoch(self):
        self.write_epoch("2026-11-08T22:53:01Z")
        _, ln = self.run_sh('cys_hook_fail session-start 124 "core_inject:5초 초과"')
        self.assertIn(" dstart=2026-11-08T22:53:01Z why=core_inject:5초 초과 ", ln[0])

    def test_dstart_absent_or_odd_is_dash(self):
        _, ln = self.run_sh('cys_hook_fail h 124 y')
        self.assertIn(" dstart=- why=y ", ln[0])
        for bad in ("garbage", "2026-11-08 22:53:01", "2026-11-08T22:53:01Z" + "9" * 40, "2026-11-08T22:53:0"):
            os.remove(self.log)
            self.write_epoch(bad)
            _, ln = self.run_sh('cys_hook_fail h 124 y')
            self.assertIn(" dstart=- why=y ", ln[0], bad)

    def test_truncated_epoch_is_dash(self):
        # 쓰다 만 파일(닫는 따옴표 없음) — 그 시각을 채택하지 않는다.
        with open(self.epoch, "w") as f:
            f.write('{"v":1,"started":"2026-11-08T22:53:01Z')
        _, ln = self.run_sh('cys_hook_fail h 124 y')
        self.assertIn(" dstart=- why=y ", ln[0])

    def test_huge_epoch_read_is_bounded(self):
        # 앞 512자만 읽는다 — 32MB 한 줄이어도 실패 기록이 훅을 다시 늦추지 않는다.
        with open(self.epoch, "w") as f:
            f.write('{"started":"2026-11-08T22:53:01Z","pad":"' + "x" * (32 << 20) + '"}')
        t0 = time.monotonic()
        r, ln = self.run_sh('cys_hook_fail h 124 y; exit 0')
        self.assertLess(time.monotonic() - t0, 2.0)
        self.assertEqual(r.returncode, 0)
        self.assertIn(" dstart=2026-11-08T22:53:01Z ", ln[0])

    def test_counsel_reader_still_counts_line(self):
        # hook-errors.log 판독자(javis_counsel _utc_head · probe_errors)는 줄 앞 시각만 본다 — 새 칸이 집계를 바꾸지 않는다.
        self.write_epoch("2026-11-08T22:53:01Z")
        _, ln = self.run_sh('cys_hook_fail dept-chat-inject 124 x')
        sys.path.insert(0, BIN)
        import javis_counsel
        self.assertIsNotNone(javis_counsel._utc_head(ln[0]), ln[0])
        old = os.environ.get("CYS_STATE_DIR")
        os.environ["CYS_STATE_DIR"] = self.st
        try:
            got = javis_counsel.probe_errors(0, time.time() + 60)
        finally:
            if old is None:
                os.environ.pop("CYS_STATE_DIR", None)
            else:
                os.environ["CYS_STATE_DIR"] = old
        self.assertIsNotNone(got)
        self.assertEqual(got["hook_rc_nonzero"], 1, got)

    @unittest.skipUnless(DASH, "dash 없음")
    def test_dash_degrades_quietly(self):
        # SECONDS·read -n 없는 POSIX sh — 두 칸 「-」 · 종료 코드·stdout 불변 · set -u 에서도.
        self.write_epoch("2026-11-08T22:53:01Z")
        r, ln = self.run_sh('set -u; cys_hook_fail h 124 y; exit 5', sh=DASH)
        self.assertEqual((r.returncode, r.stdout), (5, ""))
        #   dash 에는 read -n 이 없어 dstart 도 「-」 로 강등될 수 있다 — 둘 다 정상.
        self.assertRegex(ln[0], r" rc=124 took=- dstart=(-|2026-11-08T22:53:01Z) why=y ")

    def test_epoch_fifo_does_not_hang(self):
        # 상태 dir 의 그 이름이 FIFO 로 바뀌어 있어도 판독이 훅을 붙잡지 않는다(-f 거름).
        os.mkfifo(self.epoch)
        r, ln = self.run_sh('cys_hook_fail h 124 y; exit 0')
        self.assertEqual(r.returncode, 0)
        self.assertIn(" dstart=- ", ln[0])

    def test_builtins_only_when_path_empty(self):
        self.write_epoch("2026-11-08T22:53:01Z")
        r, ln = self.run_sh('PATH=""; cys_hook_fail inject-background 124 x; exit 0')
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertRegex(ln[0], r" rc=124 took=\d+s dstart=2026-11-08T22:53:01Z why=x ")

    def test_path_stays_last(self):
        _, ln = self.run_sh('cys_hook_fail h 1 y')
        self.assertRegex(ln[0], r" cys=(yes|no) cat=yes path=[^ ]")


if __name__ == "__main__":
    unittest.main()
