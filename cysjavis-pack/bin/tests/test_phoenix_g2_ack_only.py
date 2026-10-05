#!/usr/bin/env python3
"""★U8 P0-M2(0.14.41): phoenix G2 는 ACK **확인 전용**이고, 재주입 판정 문면을 정직하게 분류한다(데몬·네트워크 불요).

배경(반박 검증 M2 · 09-23 실측): 각성 핑이 Claude 큐에 회색으로 머물면 `cys reinject --check` 가 'ACK 없음' 을
드리프트로 읽고 58KB 디렉티브 전문을 다시 넣었다. phoenix 는 stage_reinject(timeout 6) 뒤 stage_g2_ack(timeout 4)
에서 **같은 명령**을 한 번 더 불러, 핑→전문→핑→전문 순으로 한 좌석에 2회(CEO 3회) 재주입됐고 워커는 부트 5분 뒤
ctx 64% 로 강제 clear 됐다(폭주 ① + 무clear ② 결합).

이 검체가 재는 것:
  A. stage_g2_ack 는 `--ack-only` 를 붙여 부른다(재주입 없는 ACK 확인) — 인자 전량을 대조한다.
  B. G2 의 ACK 판정은 CLI 의 **줄 단위 ACK 문면**(분류기 `ack`)이다 — 종전 `"각성" in stdout` 은 실제 ACK 줄
     ("디렉티브 생존 확인 (ACK 수신)")을 한 번도 인정하지 못했다(항상 degraded · 매 restore 재핑).
  C. 분류기는 새 보류 문면을 성공 증거로 오인하지 않는다: 바쁨(`busy`) · 판정 불가/멱등 소진/ack 전용(`held`).
     둘 다 F-1 인정 종류(ack·injected) 밖이다(주입하지 않은 것을 주입 증거로 세지 않는다).
  D. 구 cys(플래그 미지원 → clap rc 2)는 ACK 아님(degraded)으로 접히고 재주입은 일어나지 않는다(버전 스큐 안전).
  E. 소스 핀: CLI 의 안정 문면이 실제로 cys.rs 에 있다(설치 팩에는 Rust 소스가 없을 수 있다 → SKIP).

실행: python3 cysjavis-pack/bin/tests/test_phoenix_g2_ack_only.py (0=전건 PASS)

★1.1.8 병합(추가·추가 AA 합본): 같은 이름의 두 검체를 한 파일에 둘 다 살린다.
  ① 원작자 판(up/v0.14.43 · U8 P0-M2 · 위 A~E) = main()
  ② 우리 판(1.1.7 ③ · TICKET=cysr-117-impl-input · 아래 ours_suite() 의 A1~A7·M1·M2) — 우리 고유 축:
     가드 「awake」 기록 ACK 줄(「(ACK 기록 · …」)도 ACK · 정본 문면 cys.rs REINJECT_ACK_LINE 대조 · 뮤턴트 2.
     ★병합 적응: M2 뮤턴트 대상 문자열을 원작자 인자 순서(`… "--timeout", "4", "--ack-only",`)로 바꿨다(phoenix 가 원작자 판 기준).
  종료: 둘 다 통과해야 0 · 마지막 줄 PHOENIX-G2-ACK-ONLY-OK.
"""
import importlib.util, os, sys
import os
import sys
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.normpath(os.path.join(HERE, "..", "javis_phoenix.py"))
spec = importlib.util.spec_from_file_location("javis_phoenix", PH)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

_results = []
def check(name, cond):
    _results.append(cond); print(("PASS " if cond else "FAIL ") + name)


ACK = "디렉티브 생존 확인 (ACK 수신) — 재주입 불필요"
BUSY = ("재주입 보류(핑 전달됨·대상 바쁨 · queued_in_agent) — surface:7 (worker-1) · "
        "에이전트 큐에 대기 중인 핑을 '미배달'로 읽지 않는다(폭주 차단)")
HELD_UNKNOWN = "재주입 보류(핑 배달 판정 불가: 세션 기록에 핑 흔적 없음) — surface:7 (worker-1)"
HELD_ONCE = "재주입 보류(이 세션 check 재주입 1회 소진 · 좌석당 멱등) — surface:7 (worker-1)"
ACK_ONLY_MISS = "재주입 생략(ack-only · ACK 미수신: 핑 전달됨·대상 바쁨) — surface:7 (worker-1)"
INJECTED = "reinjected 58588 bytes → surface:7 (worker-1)"


def run_g2(returncode, stdout, stderr=""):
    calls = []
    orig = (m.cys, m._surface_agent_present)
    def fake_cys(*args, socket=None, timeout=None):
        calls.append(args)
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)
    try:
        m.cys = fake_cys
        m._surface_agent_present = lambda socket, surface: True
        ok, ev = m.stage_g2_ack("sock", "worker-1", "surface:7", False)
    finally:
        m.cys, m._surface_agent_present = orig
    return ok, ev, calls


def main():
    _results.clear()
    # A: 인자 전량 — ACK 전용 플래그가 붙고 역할·좌석·짧은 창은 종전 그대로다.
    ok, ev, calls = run_g2(0, ACK)
    check("g2 calls reinject exactly once", len(calls) == 1)
    check("g2 passes --ack-only", calls and calls[0] == ("reinject", "--check", "--role", "worker-1",
                                                         "--surface", "surface:7", "--timeout", "4", "--ack-only"))
    # B: 실제 ACK 줄은 ACK 다(종전 판독은 이것을 degraded 로 읽었다).
    check("g2 acks on the CLI ACK line", ok is True and "ack=True" in ev)
    # B': ACK 아닌 결과는 전부 degraded — 재주입 줄이 와도(구 cys 가 플래그를 무시한 가상) ACK 가 아니다.
    for name, rc, out, err in (
        ("busy", 0, BUSY, "[reinject] ACK 없음 (4s) — 핑 배달 판정(세션 기록)"),
        ("ack-only miss", 0, ACK_ONLY_MISS, ""),
        ("injected", 0, INJECTED, "[reinject] ACK 없음 (4s)"),
        ("old cys rejects flag", 2, "", "error: unexpected argument '--ack-only' found"),
        ("contradiction", 0, ACK, "[reinject] ACK 없음 (4s)"),
        ("empty", 0, "", ""),
    ):
        ok, ev, _ = run_g2(rc, out, err)
        check("g2 degraded on " + name, ok is False and "ack=False" in ev)
    # C: 분류기 — 새 보류 문면은 성공 증거가 아니다.
    table = (
        ("ack", 0, ACK, "", "ack"),
        ("busy", 0, BUSY, "[reinject] ACK 없음 (6s) — 핑 배달 판정(세션 기록)", "busy"),
        ("held unknown", 0, HELD_UNKNOWN, "[reinject] ACK 없음 (6s)", "held"),
        ("held once", 0, HELD_ONCE, "[reinject] ACK 없음 (6s)", "held"),
        ("ack-only miss", 0, ACK_ONLY_MISS, "", "held"),
        ("injected", 0, INJECTED, "[reinject] ACK 없음 (6s)", "injected"),
        ("rc fail beats busy", 1, BUSY, "", "fail"),
        ("queued beats busy", 0, BUSY, "[inject] 사람 입력 감지 — (--queued 1회 전환)", "queued"),
        # 줄 머리 앵커: 다른 줄 **안**의 문면은 보류 종류가 아니다.
        ("mid-line busy is not busy", 0, "note: 재주입 보류(핑 전달됨·대상 바쁨", "", "unknown"),
    )
    for name, rc, out, err, want in table:
        got = m.classify_reinject_result(rc, out, err)
        check("classify %s -> %s (got %s)" % (name, want, got), got == want)
    for kind in ("busy", "held"):
        check("F-1 does not accept " + kind, kind not in m.F1_ACCEPTED_REINJECT_KINDS)
    check("kind regex reads busy", m._reinject_kind("reinject rc=0 kind=busy " + BUSY) == "busy")
    check("kind regex reads held", m._reinject_kind("reinject rc=0 kind=held " + HELD_ONCE) == "held")

    # E: 소스 핀(설치 팩에는 Rust 소스가 없을 수 있다).
    repo = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    try:
        with open(os.path.join(repo, "src", "bin", "cys.rs"), encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print("SKIP source pin src/bin/cys.rs (repo source absent)")
    else:
        for literal in ("재주입 보류(핑 전달됨·대상 바쁨 · queued_in_agent)", "재주입 보류(핑 배달 판정 불가: ",
                        "재주입 보류(이 세션 check 재주입 1회 소진 · 좌석당 멱등)", "재주입 생략(ack-only · ACK 미수신: ",
                        "디렉티브 생존 확인 (ACK 수신)", "[reinject] ACK 없음"):
            check("source pin " + literal, literal in source)

    npass = sum(1 for c in _results if c)
    print("\n=== %d/%d PASS ===" % (npass, len(_results)))
    return 0 if npass == len(_results) else 1


# ════════════════ ② 우리 판(1.1.7 ③) — 원문 그대로 함수로 감쌌다(이름 충돌 회피) ════════════════
def ours_suite():
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
        m2_old = '"--timeout", "4", "--ack-only",'   # 1.1.8 병합: 원작자 인자 순서
        m2_new = '"--timeout", "4",'
        for tag, old, new in [("M1", m1_old, m1_new), ("M2", m2_old, m2_new)]:
            check("%s 변이 적용 대상 실재" % tag, SRC.count(old) == 1)
            sink = []
            run_suite(load_src(SRC.replace(old, new), "ph_" + tag, tmp), sink)
            check("%s 뮤턴트가 적색이다" % tag, len(sink) > 0, sink)

    if fails:
        print("FAILED: %s" % fails)
        return 1
    return 0


if __name__ == "__main__":
    _rc_theirs = main()
    print("\n── ② 우리 판(1.1.7 ③) ──")
    _rc_ours = ours_suite()
    if _rc_theirs or _rc_ours:
        sys.exit(1)
    print("PHOENIX-G2-ACK-ONLY-OK")
