#!/usr/bin/env python3
"""mut_idle_gate.py — javis_idle_gate.py 뮤턴트 하네스 (TICKET=cysr-no-hands-gui-1118).

각 변이를 임시 사본에 한 곳만 적용하고 IG_MODULE 로 test_idle_gate.py 를 돌린다 — 시험이 붉어야(KILLED) 한다.
원본 파일은 건드리지 않는다(작업 사본에서 적용→원복 하지 않음 · 기억 mutants-need-separate-worktree).
"""
import os
import shutil
import subprocess
import sys
import tempfile

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BIN, "javis_idle_gate.py")
TEST = os.path.join(BIN, "tests", "test_idle_gate.py")

MUTANTS = [
    ("M1 관문 끔(유휴 무시하고 바로 go)", "        if idle is not None and idle >= seconds:\n",
     "        if True:\n"),
    ("M2 못 읽는 유휴를 쉼으로 침(fail-open)", "        if idle is not None and idle >= seconds:\n",
     "        if idle is None or idle >= seconds:\n"),
    ("M3 도중 입력 못 봄", "    return idle + GRACE < now() - float(sess[\"mark\"]), idle\n",
     "    return False, idle\n"),
    ("M4 시간 초과 = 미룸 대신 go", "        if left <= 0:\n            return False, idle, now() - start\n",
     "        if left <= 0:\n            return True, idle, now() - start\n"),
    ("M5 미룬 일을 대기열에 안 올림", "        _write(_p(PENDING), items[-MAX_PENDING:])\n", "        pass\n"),
    ("M6 윈 틱 감김 무시", "        return ((tick - int(lii.dwTime)) & 0xFFFFFFFF) / 1000.0\n",
     "        return (tick - int(lii.dwTime)) / 1000.0\n"),
    ("M7 재개 후 기준점 안 옮김", "    s[\"mark\"] = now()\n    s[\"pauses\"]", "    s[\"pauses\"]"),
    ("M8 시작 알림이 손 떼기를 요청", "하시던 일은 그대로 하셔도 됩니다",
     "잠깐 키보드에서 손을 떼 주세요"),
    ("M9 시간 상한 없음", "    return max(0, min(int(v), MAX_TIMEOUT))\n", "    return max(0, int(v))\n"),
]


def main():
    src = open(SRC, encoding="utf-8").read()
    killed = survived = 0
    tmp = tempfile.mkdtemp(prefix="ig-mut-")
    try:
        for name, old, new in MUTANTS:
            if src.count(old) != 1:
                print("BROKEN  %s — 변이 자리 %d곳" % (name, src.count(old)))
                survived += 1
                continue
            path = os.path.join(tmp, "javis_idle_gate.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(src.replace(old, new))
            r = subprocess.run([sys.executable, TEST], env=dict(os.environ, IG_MODULE=path),
                               capture_output=True, timeout=600)
            ok = r.returncode != 0
            killed += ok
            survived += not ok
            print("%s %s rc=%d" % ("KILLED  " if ok else "SURVIVED", name, r.returncode))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("killed %d / %d" % (killed, len(MUTANTS)))
    return 0 if survived == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
