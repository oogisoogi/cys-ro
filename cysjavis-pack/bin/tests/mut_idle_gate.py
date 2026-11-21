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
    ("M1 관문 끔(유휴 무시하고 바로 go)", "        if last is not None and t - last >= seconds:\n            return True, t - last, t - start, hi, raw\n",
     "        if True:\n            return True, (0.0 if last is None else t - last), t - start, hi, raw\n"),
    ("M2 못 읽는 유휴를 쉼으로 침(fail-open)", [
        ("        if last is not None and t - last >= seconds:\n            return True, t - last, t - start, hi, raw\n",
         "        if last is None or t - last >= seconds:\n            return True, (0.0 if last is None else t - last), t - start, hi, raw\n"),
        ("            quiet = last is not None and t - last >= need\n", "            quiet = last is None or t - last >= need\n"),
        ("\"idle_secs\": round(t - last, 1),\n                            \"waited_secs\"", "\"idle_secs\": round(0.0 if last is None else t - last, 1),\n                            \"waited_secs\""),
        ("\"sid\": sid, \"go_at\": t, \"mark\": t, \"hi\": last,", "\"sid\": sid, \"go_at\": t, \"mark\": t, \"hi\": (last or t),"),
    ]),
    ("M3 도중 입력 못 봄", "    return (last > float(sess[\"mark\"])) or (q > 0 and mono() - last < q), last, raw\n",
     "    return (q > 0 and mono() - last < q), last, raw\n"),
    ("M4 시간 초과 = 미룸 대신 go(잠금 뒤 재확인까지 끔)", [
        ("            return False, (None if last is None else t - last), t - start, hi, raw\n",
         "            return True, (None if last is None else t - last), t - start, hi, raw\n"),
        ("            quiet = last is not None and t - last >= need\n", "            quiet = last is not None\n"),
        ("                quiet = idle is not None and idle >= need\n", "                quiet = idle is not None\n"),
    ]),
    ("M5 미룬 일을 대기열에 안 올림", "        _write(_p(PENDING), items)\n    return tid\n", "        pass\n    return tid\n"),
    ("M6 윈 틱 감김 무시", "        return ((tick - int(lii.dwTime)) & 0xFFFFFFFF) / 1000.0\n",
     "        return (tick - int(lii.dwTime)) / 1000.0\n"),
    ("M7 재개 후 기준점 안 옮김", "s.update(mark=t, offset=wall() - t, pauses=", "s.update(offset=wall() - t, pauses="),
    ("M8 시작 알림이 손 떼기를 요청", "하시던 일은 그대로 하셔도 됩니다", "잠깐 키보드에서 손을 떼 주세요"),
    ("M9 시간 상한 없음", "    return max(0.0, min(float(v), MAX_TIMEOUT))\n", "    return max(0.0, float(v))\n"),
    ("M10 mark 뒤 0.5초 여유 부활(codex 반례)", "    return (last > float(sess[\"mark\"])) or",
     "    return (last > float(sess[\"mark\"]) + 0.5) or"),
    ("M11 최고값 추적 끔", "    return (max(cur, float(hi)) if hi is not None else cur), cur\n", "    return cur, cur\n"),
    ("M12 준비 뒤 재확인 없음", "            quiet = last is not None and t - last >= need\n", "            quiet = last is not None\n"),
    ("M14 시계 기준 변경 무시", "    if not _clock_ok(sess):\n        return True, sess.get(\"hi\"), sess.get(\"raw\")\n", ""),
    ("M15 동시 화면 작업 허용(바쁨 판정 끔)", "    return 0 <= age <= SESSION_TTL\n", "    return False\n"),
    ("M16 남의 세션 조작 허용", "    if s.get(\"sid\") != a.sid:", "    if False:"),
    ("M17 대기열 상한 자르기", "        _write(_p(PENDING), items)\n    return tid\n",
     "        _write(_p(PENDING), items[-200:])\n    return tid\n"),
    ("M18 잠금 없음(대기열 경합)", "                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n", "                    pass\n"),
    ("M19 앱별 상향표 끔(카톡·메일·한글도 0)", "            return q\n    return 0.0\n", "            return 0.0\n    return 0.0\n"),
    ("M20 상향표 손잡이 무시", "    return (last > float(sess[\"mark\"])) or (q > 0 and mono() - last < q), last, raw\n",
     "    return (last > float(sess[\"mark\"])), last, raw\n"),
    ("M21 역행 검출 끔", "    if raw is not None and cur < float(raw) - _regress():\n", "    if False:\n"),
    ("M22 역행 기준 = 최고값(영구 정지)", "    if raw is not None and cur < float(raw) - _regress():\n",
     "    if hi is not None and cur < float(hi) - _regress():\n"),
    ("M23 mark 가 역행 기준을 안 남김", "        s[\"raw\"] = raw\n        if last", "        if last"),
    ("M24 준비 되풀이 상한 없음", "    for _attempt in range(MAX_ATTEMPTS):\n", "    while True:\n"),
    ("M25 시계 변경 = 소유권 해제", "    return 0 <= age <= SESSION_TTL\n", "    return _clock_ok(s) and 0 <= age <= SESSION_TTL\n"),
    ("M26 check 가 소유자 생존을 안 갱신", "            _touch_seen(s)\n            task = ", "            task = "),
    ("M27 복귀 직전 재확인 없음", "            elif hit:\n                restored, why = False, \"user_active\"",
     "            elif False:\n                restored, why = False, \"user_active\""),
    ("M28 잠금 대기 상한 없음", "                if time.monotonic() >= deadline:\n                    raise LockBusy()\n", ""),
    ("M29 분해형 한글·표기 정규화 없음", "unicodedata.normalize(\"NFKC\", s or \"\").casefold()", "(s or \"\").casefold()"),
    ("M30 「카톡」 별칭 없음", "(\"kakao\", \"카카오\", \"카톡\")", "(\"kakao\", \"카카오\")"),
    ("M31 check 가 긴 앱별 쉼 무시", "need = max(seconds, float(s.get(\"step_quiet\", 0) or 0))", "need = seconds"),
    ("M32 첫 관문이 긴 앱별 쉼 무시", "    need = max(a.seconds, q) ", "    need = a.seconds "),
    ("M33 check 재개 때 잠금 뒤 재관측 없음", "                quiet = idle is not None and idle >= need\n", "                quiet = True\n"),
    ("M34 check 첫 판정을 잠금 전 값으로", "                hit, hi, raw = touched(s)\n                ok = not hit\n",
     "                hit = float(s[\"hi\"]) > float(s[\"mark\"])\n                ok = not hit\n"),
    ("M35 윈 작은 틱 역행 무시", "    return REGRESS_WIN if platform() == \"win\" else REGRESS\n", "    return REGRESS\n"),
    ("M36 wait 가 마감 뒤에도 go", "            late = quiet and t > deadline ", "            late = False "),
    ("M37 check 가 마감 뒤에도 go", "                late = quiet and t > deadline\n", "                late = False\n"),
    ("M38 재부팅 전 세션이 남음", "    return 0 <= age <= SESSION_TTL\n", "    return age <= SESSION_TTL\n"),
]


def classify(compiled, rc, failed, traces, timed_out):
    """KILLED = 사본이 컴파일되고 · 도구가 죽지 않았고 · unittest 가 계약 위반(FAIL) 또는 멈춤(시간 초과)을 잡았을 때만."""
    if not compiled:
        return "CRASH"
    if rc == 0:
        return "SURVIVED"
    if rc == 1 and not traces and (failed or timed_out):
        return "KILLED"
    return "CRASH"


def run_test(module, trace_log):
    """(rc, FAIL 시험 이름들, 도구 Traceback 목록, 시험의 시간 초과 여부, 진단 한 줄). 전체 시간 초과는 rc=None."""
    if os.path.exists(trace_log):
        os.remove(trace_log)
    try:
        r = subprocess.run([sys.executable, TEST], env=dict(os.environ, IG_MODULE=module, IG_TRACE_LOG=trace_log),
                           capture_output=True, timeout=900)
    except subprocess.TimeoutExpired:
        return None, [], [], False, "timeout 900s"
    err = r.stderr.decode("utf-8", errors="replace")
    failed = sorted(set(re.findall(r"^FAIL: (\w+)", err, re.M)))
    timed_out = "subprocess.TimeoutExpired" in err
    traces = []
    if os.path.exists(trace_log):
        with open(trace_log, encoding="utf-8", errors="replace") as f:
            traces = [ln for ln in f.read().splitlines() if re.match(r"^\w*(Error|Exception)\b", ln)] or ["Traceback"]
    diag = next((ln for ln in reversed(err.splitlines()) if re.match(r"^\w*(Error|Exception)\b", ln)), "")
    return r.returncode, failed, traces, timed_out, diag[:200]


def main():
    tmp = tempfile.mkdtemp(prefix="ig-mut-")
    trace_log = os.path.join(tmp, "traces.log")
    killed = bad = 0
    try:
        rc0, names0, traces0, _t, _d = run_test(SRC, trace_log)
        if rc0 != 0 or traces0:
            print("ABORT 원본 시험이 붉음(rc=%s · %s · %s) — 뮤턴트 판정 불가" % (rc0, ",".join(names0), traces0[:1]))
            return 2
        print("BASE    원본 시험 녹색")
        src = open(SRC, encoding="utf-8").read()
        for name, *spec in MUTANTS:
            pairs = spec[0] if len(spec) == 1 else [tuple(spec)]
            miss = [old[:40] for old, _new in pairs if src.count(old) != 1]
            if miss:
                print("BROKEN   %s — 변이 자리가 정확히 1곳이 아님: %s" % (name, miss))
                bad += 1
                continue
            text = src
            for old, new in pairs:
                text = text.replace(old, new)
            path = os.path.join(tmp, "javis_idle_gate.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            try:
                compile(text, path, "exec")
                compiled = True
            except SyntaxError:
                compiled = False
            rc, failed, traces, timed_out, diag = run_test(path, trace_log) if compiled else (None, [], [], False, "SyntaxError")
            verdict = classify(compiled, rc, failed, traces, timed_out)
            if verdict == "KILLED":
                killed += 1
                print("KILLED   %s by %s · %s" % (name, ",".join(failed) or "시간 초과", diag))
            else:
                bad += 1
                print("%-8s %s rc=%s · %s" % (verdict, name, rc, (traces[:1] or [diag or "-"])[0]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("killed %d / %d" % (killed, len(MUTANTS)))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
