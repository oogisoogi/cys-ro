#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phoenix_encoding_mutants.py — TICKET=cys-phoenix-korean-windows 뮤테이션 검산(S4 뮤턴트 축)

무엇을 재는가: 이 티켓이 세운 검사 축들이 **실제로 그 수리를 재고 있는가.**
  통과만 보고는 알 수 없다 — 수리를 되돌렸을 때 적색이 되는지가 유일한 증거다.

각 뮤턴트: ⑴대상 파일 백업 → ⑵정확히 한 곳 되돌리기(치환 건수 assert — 미적용은 실패로 보고) →
          ⑶해당 검사 실행 → ⑷종료코드로 판정 → ⑸finally 로 원복(예외·중단에도).

판정 어휘: KILLED = 뮤턴트를 검사가 잡았다(적색) · SURVIVED = 못 잡았다(그 축은 공허하다) ·
          NOT-APPLIED = 뮤턴트가 소스에 적용조차 안 됐다(**측정 실패** — 통과로 읽지 말 것).

exit: 0=전 뮤턴트 KILLED · 1=SURVIVED 있음 · 2=NOT-APPLIED 등 측정 실패.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOENIX = os.path.join(ROOT, "cysjavis-pack", "bin", "javis_phoenix.py")
LIB = os.path.join(ROOT, "src", "lib.rs")
HANDLERS = os.path.join(ROOT, "src", "bin", "cysd", "handlers.rs")
STATE = os.path.join(ROOT, "src", "bin", "cysd", "state.rs")

ENC_SMOKE = [sys.executable, os.path.join(ROOT, "cysjavis-pack", "bin",
                                          "javis_phoenix_encoding_smoke.py")]
CARGO = os.environ.get("CARGO", os.path.expanduser("~/.cargo/bin/cargo"))

MUTANTS = [
    {
        "id": "M1-reconfigure-제거",
        "why": "S1ⓐ — 표준 스트림 utf-8 고정을 지운다. 로그 한 줄의 「—」에서 다시 즉사해야 한다.\n"
               "       ★조준점이 한 번 옮겨졌다: import guard 대응으로 루프를 _pin_utf8_stream 헬퍼로\n"
               "       바꾸면서 옛 앵커가 소멸했고, 그때 이 하네스가 NOT-APPLIED(측정 실패)로 정직하게\n"
               "       울었다 — 초록으로 넘어가지 않은 것이 이 어휘의 존재 이유다.",
        "file": PHOENIX,
        "old": '        stream.reconfigure(encoding="utf-8", errors="backslashreplace")\n        return stream',
        "new": '        return stream  # MUTANT M1',
        "check": ENC_SMOKE,
        "check_name": "phoenix 인코딩 스모크",
    },
    {
        "id": "M2-open-encoding-제거",
        "why": "S1ⓑ — 부활 저널 읽기의 encoding 인자를 지운다. 로케일 코덱으로 되돌아가야 한다.",
        "file": PHOENIX,
        "old": '            return json.load(open(p, encoding="utf-8"))\n        except Exception as _e:',
        "new": '            return json.load(open(p))\n        except Exception as _e:',
        "check": ENC_SMOKE,
        "check_name": "phoenix 인코딩 스모크",
    },
    {
        "id": "M3-데몬-ENV-주입-제거",
        "why": "S2 — 직스폰 팩토리의 PYTHONUTF8/PYTHONIOENCODING 주입을 지운다. 두 층 규약이 갈려야 한다.",
        "file": LIB,
        "old": '    cmd.env(ENV_PY_UTF8, PY_UTF8_ON);\n    cmd.env(ENV_PY_IO_ENCODING, PY_IO_ENCODING_UTF8);',
        "new": '    // MUTANT M3',
        "check": [CARGO, "test", "--lib", "python_encoding_contract"],
        "check_name": "cargo test python_encoding_contract",
    },
    {
        "id": "M4-create-영속-제거",
        "why": "S3 — 역할을 달고 태어난 좌석의 create 시점 영속을 지운다. master 가 디스크에서 사라져야 한다.\n"
               "       ★조준점은 핸들러가 아니라 state.rs 다 — 첫 조준(핸들러)이 SURVIVED 를 내서 가설이 반증됐고,\n"
               "       그때 비로소 영속의 실제 소유자가 create_surface_with_env 말미임이 드러났다.",
        "file": STATE,
        "old": '        if role.is_some() {\n'
               '            crate::governance::persist_topology(self);\n'
               '        }\n',
        "new": '        // MUTANT M4\n',
        "check": [CARGO, "test", "--bin", "cysd", "role_bearing_surface_is_persisted"],
        "check_name": "cargo test role_bearing_surface_is_persisted",
    },
]


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    print("[mutants] 기준선 확인 — 뮤턴트 없이 전 검사가 초록이어야 한다")
    for m in MUTANTS:
        rc, _ = run(m["check"])
        if rc != 0:
            print("  [기준선 적색] %s (rc=%d) — 뮤테이션 판정 불가" % (m["check_name"], rc))
            return 2
    print("  기준선 초록 (%d개 검사)" % len({m["check_name"] for m in MUTANTS}))

    verdicts = []
    for m in MUTANTS:
        path = m["file"]
        orig = open(path, encoding="utf-8").read()
        applied = False
        try:
            cnt = orig.count(m["old"])
            if cnt != 1:
                verdicts.append((m["id"], "NOT-APPLIED", "치환 대상 %d건(예상 1) — 소스가 이동했다" % cnt))
                continue
            open(path, "w", encoding="utf-8").write(orig.replace(m["old"], m["new"], 1))
            applied = True
            # 변이 적용 자체를 단언한다 — '안 움직인다'가 측정 실패일 수 있다.
            assert m["new"] in open(path, encoding="utf-8").read(), "변이가 디스크에 없다"
            rc, out = run(m["check"])
            if rc == 0:
                tail = "\n        | ".join(out.strip().splitlines()[-3:])
                verdicts.append((m["id"], "SURVIVED", "%s 가 초록으로 통과 — 그 축은 공허하다\n        | %s"
                                 % (m["check_name"], tail)))
            else:
                verdicts.append((m["id"], "KILLED", "%s rc=%d" % (m["check_name"], rc)))
        finally:
            if applied:
                open(path, "w", encoding="utf-8").write(orig)

    print("\n[mutants] 판정")
    bad = 0
    for mid, verdict, detail in verdicts:
        print("  [%-11s] %-24s %s" % (verdict, mid, detail))
        if verdict != "KILLED":
            bad += 1
    print("[mutants] 총 %d · KILLED %d · 미달 %d" % (len(verdicts), len(verdicts) - bad, bad))
    if any(v == "NOT-APPLIED" for _, v, _ in verdicts):
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
