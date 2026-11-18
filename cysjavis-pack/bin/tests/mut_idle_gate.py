#!/usr/bin/env python3
"""mut_idle_gate.py — javis_idle_gate.py 뮤턴트 하네스 (TICKET=cysr-no-hands-gui-1118).

각 변이를 임시 사본에 한 곳만 적용하고 IG_MODULE 로 test_idle_gate.py 를 돌린다 — 시험이 붉어야(KILLED) 한다.
★전제(codex 1R): 같은 환경에서 원본 시험이 먼저 녹색이어야 한다(아니면 전부 KILLED 로 보이는 가짜 성공) · 변이마다 붉어진 시험 이름을 보인다.
원본 파일은 건드리지 않는다(작업 사본에서 적용→원복 하지 않음 · 기억 mutants-need-separate-worktree).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BIN, "javis_idle_gate.py")
TEST = os.path.join(BIN, "tests", "test_idle_gate.py")

MUTANTS = [
    ("M1 관문 끔(유휴 무시하고 바로 go)", "        if last is not None and t - last >= seconds:\n",
     "        if True:\n"),
    ("M2 못 읽는 유휴를 쉼으로 침(fail-open)", "        if last is not None and t - last >= seconds:\n",
     "        if last is None or t - last >= seconds:\n"),
    ("M3 도중 입력 못 봄", "    return last > float(sess[\"mark\"]), last\n", "    return False, last\n"),
    ("M4 시간 초과 = 미룸 대신 go", "            return False, (None if last is None else t - last), t - start, hi\n",
     "            return True, (None if last is None else t - last), t - start, hi\n"),
    ("M5 미룬 일을 대기열에 안 올림", "        _write(_p(PENDING), items)\n    return tid\n", "        pass\n    return tid\n"),
    ("M6 윈 틱 감김 무시", "        return ((tick - int(lii.dwTime)) & 0xFFFFFFFF) / 1000.0\n",
     "        return (tick - int(lii.dwTime)) / 1000.0\n"),
    ("M7 재개 후 기준점 안 옮김", "        s2.update(mark=t, hi=hi,", "        s2.update(hi=hi,"),
    ("M8 시작 알림이 손 떼기를 요청", "하시던 일은 그대로 하셔도 됩니다", "잠깐 키보드에서 손을 떼 주세요"),
    ("M9 시간 상한 없음", "    return max(0.0, min(float(v), MAX_TIMEOUT))\n", "    return max(0.0, float(v))\n"),
    ("M10 mark 뒤 0.5초 여유 부활(codex 반례)", "    return last > float(sess[\"mark\"]), last\n",
     "    return last > float(sess[\"mark\"]) + 0.5, last\n"),
    ("M11 최고값 추적 끔(뒤로 간 OS 값)", "    return max(last, float(hi)) if hi is not None else last\n", "    return last\n"),
    ("M12 준비 뒤 재확인 없음", "        if last is not None and mono() - last >= a.seconds:", "        if True:"),
    ("M13 복귀가 관문 밖", "        elif hit:\n            restored, why = False, \"user_active\"",
     "        elif False:\n            restored, why = False, \"user_active\""),
    ("M14 시계 기준 변경 무시", "    if not _clock_ok(sess):\n        return True, sess.get(\"hi\")\n", ""),
    ("M15 동시 화면 작업 허용(바쁨 판정 끔)", "    return s is not None and _clock_ok(s) and 0 <= mono() - float(s[\"mark\"]) <= SESSION_TTL\n",
     "    return False\n"),
    ("M16 남의 세션 조작 허용", "    if s.get(\"sid\") != a.sid:", "    if False:"),
    ("M17 대기열 상한 자르기", "        _write(_p(PENDING), items)\n    return tid\n",
     "        _write(_p(PENDING), items[-200:])\n    return tid\n"),
    ("M18 잠금 없음(대기열 경합)", "            fcntl.flock(f.fileno(), fcntl.LOCK_EX)\n", "            pass\n"),
]


def run_test(module):
    r = subprocess.run([sys.executable, TEST], env=dict(os.environ, IG_MODULE=module), capture_output=True, timeout=900)
    err = r.stderr.decode("utf-8", errors="replace")
    names = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+)", err, re.M)))
    return r.returncode, names


def main():
    rc0, names0 = run_test(SRC)
    if rc0 != 0:
        print("ABORT 원본 시험이 붉음(rc=%d · %s) — 뮤턴트 판정 불가" % (rc0, ",".join(names0)))
        return 2
    print("BASE    원본 시험 녹색")
    src = open(SRC, encoding="utf-8").read()
    killed = survived = 0
    tmp = tempfile.mkdtemp(prefix="ig-mut-")
    try:
        for name, old, new in MUTANTS:
            if src.count(old) != 1:
                print("BROKEN   %s — 변이 자리 %d곳" % (name, src.count(old)))
                survived += 1
                continue
            path = os.path.join(tmp, "javis_idle_gate.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(src.replace(old, new))
            rc, names = run_test(path)
            ok = rc != 0
            killed += ok
            survived += not ok
            print("%s %s rc=%d by %s" % ("KILLED  " if ok else "SURVIVED", name, rc, ",".join(names) or "-"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("killed %d / %d" % (killed, len(MUTANTS)))
    return 0 if survived == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
