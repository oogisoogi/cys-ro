#!/usr/bin/env python3
"""D2(1.1.8 · 윈 실측) — 윈(named pipe)에서 deadman·영수증 회수 불가는 「해당 없음」(INFO)이지 상시 WARN 이 아니다."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.dont_write_bytecode = True
import javis_report_gate as R  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — %s" % (detail,)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


src = open(os.path.join(os.path.dirname(HERE), "javis_report_gate.py"), encoding="utf-8").read()
check("N1 이 기계(unix) = 구조적 해당 없음 아님", R.DEADMAN_STRUCTURALLY_NA is (os.name == "nt"))
check("N2 윈 사유 = deadman_poll_not_applicable:windows", '"deadman_poll_not_applicable:windows" if DEADMAN_STRUCTURALLY_NA' in src)
check("N3 윈 영수증 배지 = INFO(해당 없음) · unix = WARN 그대로",
      'self._badge("ack-unavailable", SEV_INFO,' in src and 'self._badge("ack-unavailable", SEV_WARN,' in src)
print("\n=== %s ===" % ("ALL PASS" if not fails else "FAIL %d: %s" % (len(fails), fails)))
sys.exit(1 if fails else 0)
