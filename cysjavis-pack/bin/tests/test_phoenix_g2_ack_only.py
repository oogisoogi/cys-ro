#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_g2_ack_only.py — 부활 G2 는 확인 전용이고 ACK 는 줄 단위로만 읽는다 (1.1.7 ③ · TICKET=cysr-117-impl-input).

원작자 U8 P0-M2(6a090055 · test_phoenix_g2_ack_only.py)의 우리 판 취지 이식. 고치는 결함:
  ⑴ stage_g2_ack 가 stage_reinject 와 **같은 명령**(`reinject --check`)이라 복원 1회에 핑 2 + 지침 전문 최대 2회.
  ⑵ ACK 판정이 `"각성" in stdout`(실제 ACK 줄을 한 번도 인정 못 함) · `"awake"`(가드 skip 줄 낱말에 우연히 걸림).

  A1 stage_g2_ack 는 `--check --ack-only` 를 부른다(재주입 없는 확인)
  A2 stage_reinject 는 종전대로 `--check`(재주입 자격은 한 곳 · --ack-only 없음)
  A3 ACK 줄(줄 머리 「디렉티브 생존 확인 (ACK 수신)」) + rc 0 → ACK
  A4 옛 바이너리(플래그 미지원 → clap rc 2) → ACK 아님(주입 0 은 CLI 가 보장 · 여기선 판정만)
  A5 줄 머리가 아닌 문면·「awake」 낱말·「각성」 낱말 → ACK 아님
  A6 ack-only ACK 미수신 줄 → ACK 아님 · rc≠0 + ACK 줄 → ACK 아님
  A7 정본 문면 대조 — src/bin/cys.rs REINJECT_ACK_LINE 과 같은 문면(두 곳이 갈리면 G2 가 영구 degraded)
  M  뮤턴트 2: M1 g2_acked 가 부분 문자열로 되돌아감 · M2 stage_g2_ack 에서 --ack-only 제거 → 적색이어야 한다

실행: python3 cysjavis-pack/bin/tests/test_phoenix_g2_ack_only.py → 종료 토큰 PHOENIX-G2-ACK-ONLY-OK
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.normpath(os.path.join(HERE, "..", "javis_phoenix.py"))
CYS_RS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "src", "bin", "cys.rs"))
fails = []


def check(name, cond, detail="", sink=None):
    if sink is None:
        print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + str(detail)) if detail else ""))
        if not cond:
            fails.append(name)
    elif not cond:
        sink.append(name)


def load_src(src, name, tmp):
    path = os.path.join(tmp, name + ".py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class R:
    def __init__(self, rc, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


ACK = "디렉티브 생존 확인 (ACK 수신) — 재주입 불필요\n"


def run_suite(mod, sink=None):
    calls = []

    def fake_cys(*args, **kw):
        calls.append(list(args))
        return fake_cys.next

    fake_cys.next = R(0, ACK)
    mod.cys = fake_cys
    mod._surface_agent_present = lambda socket, surface: True
    ok, _ev = mod.stage_g2_ack("sock", "worker", "surface:9", False)
    check("A1 G2 = --check --ack-only", calls and "--check" in calls[-1] and "--ack-only" in calls[-1],
          calls[-1] if calls else calls, sink)
    check("A3 ACK 줄 → ACK", ok is True, _ev, sink)
    mod.stage_reinject("sock", "worker", "surface:9", False)
    check("A2 stage_reinject = --check · --ack-only 없음", "--check" in calls[-1] and "--ack-only" not in calls[-1],
          calls[-1], sink)
    fake_cys.next = R(2, "", "error: unexpected argument '--ack-only' found\n")
    ok, _ = mod.stage_g2_ack("sock", "worker", "surface:9", False)
    check("A4 옛 바이너리 rc 2 → ACK 아님", ok is False, sink=sink)
    for out in ["reinject --check skip (surface:9) — awake\n",
                "지침 각성 확인 완료\n",
                "role (BACKEND) 디렉티브 생존 확인 (ACK 수신)\n",
                "재주입 생략(ack-only · ACK 미수신 4s) — surface:9 (worker)\n"]:
        fake_cys.next = R(0, out)
        ok, _ = mod.stage_g2_ack("sock", "worker", "surface:9", False)
        check("A5/A6 ACK 아님: %r" % out.strip(), ok is False, sink=sink)
    check("A6 rc≠0 + ACK 줄 → ACK 아님", mod.g2_acked(1, ACK) is False, sink=sink)
    check("A3′ 가드 기록 ACK 줄도 ACK", mod.g2_acked(0, "디렉티브 생존 확인 (ACK 기록 · 120초 전 · TTL 안 · 재핑 생략) surface:9\n"),
          sink=sink)
    check("A3″ 비슷한 머리의 다른 줄은 ACK 아님", mod.g2_acked(0, "디렉티브 생존 확인 (ACK 없음)\n") is False, sink=sink)


with open(PH, encoding="utf-8") as f:
    SRC = f.read()
with tempfile.TemporaryDirectory() as tmp:
    run_suite(load_src(SRC, "ph_real", tmp))
    # A7 정본 문면 대조
    with open(CYS_RS, encoding="utf-8") as f:
        rs = f.read()
    check("A7 cys.rs REINJECT_ACK_LINE = 「디렉티브 생존 확인 (ACK 수신)」",
          'const REINJECT_ACK_LINE: &str = "디렉티브 생존 확인 (ACK 수신)";' in rs)
    # 뮤턴트 — 변이가 실제로 적용됐는지 먼저 확인한 뒤 적색을 요구한다.
    m1_old = 'return returncode == 0 and _REINJECT_ACK_LINE_RE.search(stdout or "") is not None'
    m1_new = 'return returncode == 0 and ("각성" in (stdout or "") or "awake" in (stdout or "").lower())'
    m2_old = '"--check", "--ack-only", "--role"'
    m2_new = '"--check", "--role"'
    for tag, old, new in [("M1", m1_old, m1_new), ("M2", m2_old, m2_new)]:
        check("%s 변이 적용 대상 실재" % tag, SRC.count(old) == 1)
        sink = []
        run_suite(load_src(SRC.replace(old, new), "ph_" + tag, tmp), sink)
        check("%s 뮤턴트가 적색이다" % tag, len(sink) > 0, sink)

if fails:
    print("FAILED: %s" % fails)
    sys.exit(1)
print("PHOENIX-G2-ACK-ONLY-OK")
