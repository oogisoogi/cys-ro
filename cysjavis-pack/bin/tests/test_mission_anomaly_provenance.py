#!/usr/bin/env python3
"""D15(1.1.8 · 윈 결함 보고 2026-10-05) — 이상징후 출처·재생 표지·중복 키 회귀 잠금(python 판).

실측 결함: 대장(mission.json)에 영속된 이상징후가 code·detail 두 필드뿐이라, 다른 좌석이 전에 남긴 기록의
재생이 「지금 재발」로 보고됐고(오보 1건), 중복 키 (code,detail) 가 동일 문구의 진짜 재발을 조용히 합쳤다.
⚠ 운영 대장의 writer 는 Rust(`cys hook user-prompt-submit` · src/mission_gate.rs) 다 — 이 시험은 python
reader(status·gate 보고)와 deprecated python writer(구팩 스큐 폴백)만 잠근다.
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(HERE)
fails = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — %s" % (detail,)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def load(tag):
    sys.dont_write_bytecode = True
    if BIN not in sys.path:
        sys.path.insert(0, BIN)
    spec = importlib.util.spec_from_file_location("jm_" + tag, os.path.join(BIN, "javis_mission.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    st = tempfile.mkdtemp(prefix="jmprov.", dir=os.environ.get("TMPDIR") or None)
    os.environ["CYS_STATE_DIR"] = st
    os.environ["CYS_SURFACE_ID"] = "105"
    m = load("a")
    m.ENV_ANOMALIES[:] = []
    m._ANOMALY_SINK[:] = []
    m._OBS_PROMPT_SHA[0] = "abc123def456"
    m._push_anomaly("delivery_substring", "프롬프트 61458자 / 구간 61403자")
    got = m.collected_anomalies()
    check("P1 출처 3필드(ts·surface·prompt_sha)",
          len(got) == 1 and got[0].get("ts") and got[0].get("surface") == "105"
          and got[0].get("prompt_sha") == "abc123def456", got)
    line = m.anomaly_line(got[0])
    check("P2 지금 관측 문구", "지금 관측" in line and "좌석 105" in line and "abc123def456" in line, line)

    # 대장에 기록된 옛 항목(출처 없음) + 출처 있는 항목 → 재생 표지
    old_ts = "2026-10-05T08:58:34+0900"
    recorded = [{"code": "delivery_substring", "detail": "프롬프트 61458자 / 구간 61403자",
                 "ts": old_ts, "surface": "103", "prompt_sha": "ffff00001111"},
                {"code": "ledger_rotated", "detail": "회전"}]
    merged = m._merge_anomalies(recorded)
    rep = [a for a in merged if a.get("replay")]
    check("P3 대장 항목 = 재생 표지", len(rep) == 2, merged)
    l1 = m.anomaly_line(rep[0])
    check("P4 재생 문구 = 기록 시각·좌석", "재생(기록 시각 %s · 좌석 103" % old_ts in l1, l1)
    l2 = m.anomaly_line(rep[1])
    check("P5 출처 없는 옛 기록 = 「지금 난 일이 아니다」", "옛 판이 남긴 기록" in l2, l2)
    check("P6 같은 문구라도 다른 관측 시각이면 둘 다 보인다(진짜 재발 묻힘 0)",
          sum(1 for a in merged if a["code"] == "delivery_substring") == 2, merged)

    # 상태 유래 코드는 시각과 무관하게 (code,detail) 키 — 매 판독 재관측이 대장을 채우지 않는다
    a1 = {"code": "ledger_rotated", "detail": "x", "ts": "t1"}
    a2 = {"code": "ledger_rotated", "detail": "x", "ts": "t2"}
    check("P7 상태 유래 = 시각 무관 키", m._anomaly_key(a1) == m._anomaly_key(a2))
    b1 = {"code": "delivery_concatenated", "detail": "x", "ts": "t1"}
    b2 = {"code": "delivery_concatenated", "detail": "x", "ts": "t2"}
    check("P8 프롬프트 유래 = 시각 포함 키", m._anomaly_key(b1) != m._anomaly_key(b2))

    # python writer 폴백: 영속에 출처가 남고 replay 표지는 남지 않는다
    lp = m.ledger_path()
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    with open(lp, "w", encoding="utf-8") as f:
        json.dump({"schema": m.SCHEMA_VERSION, "mission": None, "source": "anomaly_only", "reason": "",
                   "surface": "103", "ts": old_ts, "ts_epoch": 0, "boot_epoch": None,
                   "ledger_status": "ok", "anomalies": recorded}, f, ensure_ascii=False)
    rec = m._persist_anomalies("ok")
    an = (rec or {}).get("anomalies") or []
    check("P9 영속 = 옛 2 + 새 1(같은 문구 다른 시각)", len(an) == 3, an)
    check("P10 영속에 replay 표지 0", not any("replay" in a for a in an), an)
    check("P11 새 항목 출처 영속", any(a.get("prompt_sha") == "abc123def456" for a in an), an)
    print("\n=== %s ===" % ("ALL PASS" if not fails else "FAIL %d: %s" % (len(fails), fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
