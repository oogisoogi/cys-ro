#!/usr/bin/env python3
"""W5 축D Windows 격납 — 플랫폼 무관 로직 게이트(리포 커밋). Windows Job Object kill-on-close 실거동·msvcrt
이중스폰 차단 실거동·CI 실 cysd.exe 부활은 **Windows 러너에서만 검증 가능**(설계 D4/E1) — 이 파일은 mac/Linux
에서도 돌릴 수 있는 계약(_try_lock_nb 상호배제·lease 통합·open 모드)만 결정론 검증한다. Windows 런타임 게이트는
.github/workflows(windows-build.yml T5 real-path)·decide_auto_restore Rust 단위테스트가 담당.

실행: python3 cysjavis-pack/bin/tests/test_phoenix_w5_windows.py  (0=전건 PASS)
"""
import importlib.util, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.normpath(os.path.join(HERE, "..", "javis_phoenix.py"))
spec = importlib.util.spec_from_file_location("javis_phoenix", PH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

_results = []
def check(name, cond, detail=""):
    _results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (" | " + detail if detail else ""))


def main():
    td = tempfile.mkdtemp(prefix="phoenix-w5-")

    # ── D2 통합 락 헬퍼 _try_lock_nb: 상호배제 계약(unix flock·Windows msvcrt 공통) ──
    #   같은 파일을 두 핸들로 열어 첫 핸들이 락을 잡으면 둘째는 False(경합)여야 한다. 해제(close) 후 재획득 True.
    lockp = os.path.join(td, "x.lock")
    f1 = open(lockp, "a+")
    r1 = m._try_lock_nb(f1)
    check("D2 _try_lock_nb 최초 획득 → True", r1 is True, "r1=%s" % r1)
    f2 = open(lockp, "a+")
    r2 = m._try_lock_nb(f2)
    check("D2 _try_lock_nb 보유 중 둘째 → False(상호배제)", r2 is False, "r2=%s" % r2)
    f2.close()
    f1.close()
    f3 = open(lockp, "a+")
    r3 = m._try_lock_nb(f3)
    check("D2 _try_lock_nb 해제(close) 후 재획득 → True", r3 is True, "r3=%s" % r3)
    f3.close()

    # ── D2 restore lease: 통합 헬퍼 경유 이중 스폰 차단(보유 중 재획득 실패) ──
    home = os.path.join(td, "state", "phoenix")
    os.makedirs(home, exist_ok=True)
    sock = os.path.join(td, "state", "cys.sock")
    m.CYS = os.path.join(td, "nonexistent-cys")
    ok1, h1 = m._acquire_restore_lease(sock)
    check("D2 restore lease 최초 획득", ok1 is True and h1 is not None, "ok=%s" % ok1)
    ok2, h2 = m._acquire_restore_lease(sock)
    check("D2 restore lease 보유 중 재획득 → False(이중 스폰 차단·Windows fail-open 제거)",
          ok2 is False, "ok2=%s" % ok2)
    m._release_lease(h1)
    ok3, h3 = m._acquire_restore_lease(sock)
    check("D2 restore lease 해제 후 재획득 → True", ok3 is True, "ok3=%s" % ok3)
    m._release_lease(h3)

    # ── D2 roster/dept 락: 통합 헬퍼 경유(P1-8 Windows fail-open 제거) ──
    hl = m._acquire_roster_lock(sock, "roster")
    check("D2 roster lock 획득(핸들 반환)", hl is not None)
    # 보유 중 외부 핸들 획득 실패(상호배제)
    ext = open(os.path.join(home, "roster.lock"), "a+")
    check("D2 roster lock 보유 중 외부 → False", m._try_lock_nb(ext) is False)
    ext.close()
    m._release_lease(hl)

    # ── open 모드 계약: lease/lock 파일은 truncate 금지(a+)여야 Windows msvcrt byte0 영역이 일치한다 ──
    #   (회귀 핀: 과거 "w" 는 truncate 로 동시 open 시 msvcrt 영역/락이 어긋날 수 있었다 — 소스 문자열 검증.)
    #
    # ★2026-09-09 수리(TICKET=cys-release-first-publish): 종전 이 두 줄은 **완전 리터럴**
    #   `open(lease_path, "a+")` 를 찾았다. 그런데 229df16(2026-09-08 · 로케일 코덱 독립화)이
    #   같은 호출에 `encoding="utf-8"` 을 **덧붙이면서** 리터럴이 어긋나 핀이 적색이 됐다 —
    #   모드는 여전히 `a+` 이고 계약은 지켜졌는데 검사만 깨진 것이다. 실측: javis_phoenix.py:1594
    #   `open(lease_path, "a+", encoding="utf-8")` · :935 `open(p, "a+", encoding="utf-8")`.
    #   ⚠이 핀은 태그 push 에서만 도는 release 전용 스위트라(ci-branch 는 `test_phoenix_*` 를
    #     돌리지 않는다) 09-08 부터 오늘 첫 태그까지 **아무도 못 봤다.**
    #   고친 방향: 핀을 **약화하지 않고** 인자 추가에 둔감하게 바꿨다. 대상 호출을 전부 찾아
    #   **모드가 하나도 빠짐없이 `a+` 인지**를 본다 — 하나라도 "w"(truncate)로 회귀하면 죽고,
    #   호출이 아예 사라져도 죽는다(빈 목록 = 실패). 종전 리터럴보다 잡는 범위가 넓다.
    src = open(PH, encoding="utf-8").read()
    for label, target in (("restore.lease", "lease_path"), ("roster/dept lock", "p")):
        modes = re.findall(r'open\(%s,\s*"([^"]+)"' % re.escape(target), src)
        check("D2 %s open 모드 a+(무truncate) · 실측 %r" % (label, modes),
              bool(modes) and all(m == "a+" for m in modes))
    check("D2 _try_lock_nb 에 msvcrt.locking(LK_NBLCK) 배선", "msvcrt.locking" in src and "LK_NBLCK" in src)

    import shutil
    shutil.rmtree(td, ignore_errors=True)
    npass = sum(1 for c in _results if c)
    print("\n=== %d/%d PASS ===" % (npass, len(_results)))
    return 0 if npass == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
