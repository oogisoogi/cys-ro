#!/usr/bin/env python3
import subprocess, sys, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]  # 저장소 뿌리
F = ROOT / "scripts/tests/test_update_publish.py"
ISO = sys.argv[1]
ORIG = F.read_bytes(); src = ORIG.decode()
M = [
 ("P1 둘째 매체를 직접 호출로 되돌림",
  '            reasons = hdiutil_retry(args, partial=partial)\n            if reasons:\n                self.fail("둘째 가짜 매체',
  '            reasons = [] if subprocess.call(["hdiutil", args[0]] + args[1:]) == 0 else ["x"]\n            if reasons:\n                self.fail("둘째 가짜 매체'),
 ("P2 재시도 0(도우미 1회만)", "    for attempt in (1, 2):", "    for attempt in (1,):"),
 ("P3 모듈 전제 확인이 실패를 무시",
  '                return ["hdiutil 매체 생성·마운트 실패(hdiutil %s · 2회): %s" % (args[0], " | ".join(reasons))]',
  '                continue'),
 ("P4 setUpModule 이 전제 실패를 버림", "        bad.extend(media_probe_failures())", "        media_probe_failures()"),
 ("P5 모듈 전제 확인이 도우미를 안 거침(직접 1회)",
  "            reasons = hdiutil_retry(args, partial=partial, runner=runner, delay=delay)",
  "            r = (runner or run)([\"hdiutil\"] + list(args)); reasons = [] if r.returncode == 0 else [r.stderr]"),
]
try:
    for name, old, new in M:
        n = src.count(old)
        if n != 1:
            print(name, "→ 적용 불가", n); continue
        F.write_text(src.replace(old, new))
        p = subprocess.run([ISO, "python3", str(F), "-v", "TestHdiutilRetry"], cwd=ROOT, capture_output=True, text=True)
        bad = re.findall(r"^(?:FAIL|ERROR): (\S+)", p.stderr, re.M)
        print(f"{name} → {'잡음' if bad else '놓침'} rc={p.returncode} {sorted(set(bad))}")
finally:
    F.write_bytes(ORIG); print("복원:", F.read_bytes() == ORIG)
