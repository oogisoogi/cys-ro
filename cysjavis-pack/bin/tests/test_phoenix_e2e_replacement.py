#!/usr/bin/env python3
"""W6/E1 데몬 교체 시뮬레이션 E2E(리포 커밋·mac 게이트) — a07cc7f Not-tested 봉인.

격리 상태 디렉터리에서 실 cysd 를 기동해 auto-restore(임베드 추출→phoenix restore --auto)가 데몬 자신의
소켓/상태를 타는지(W6 --socket enabler), 그리고 세 게이트 시나리오를 실측한다:
  ① no-target-roles → NOOP(fresh live)
  ② PHOENIX_STRICT_CYS=1 → Rust PHOENIX_CYS/PATH 주입으로 phoenix 해석 성공(폴백 아님·exit6 아님)
  ③ 재기동 후 seeded dead role → 부활 대상 타겟팅(kill→재기동→부활 경로 발화)

바이너리(cysd/cys)는 PHOENIX_HARNESS_CYSD·PATH 또는 <repo>/target/debug 에서 찾는다. 없으면 SKIP(exit 0) —
CI 는 빌드 후 실행(게이트), 로컬 무빌드 실행은 skip. 라이브 무접촉(guard_isolation·격리 소켓 전용).

실행: python3 cysjavis-pack/bin/tests/test_phoenix_e2e_replacement.py
"""
import importlib.util, os, sys, time, json, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))  # tests/../../.. = repo root
DBG = os.path.join(REPO, "target", "debug")


def _find(name):
    env = os.environ.get("PHOENIX_HARNESS_" + name.upper())
    if env and os.path.exists(env):
        return env
    cand = os.path.join(DBG, name)
    if os.path.exists(cand):
        return cand
    return shutil.which(name)


CYSD = _find("cysd")
CYS = _find("cys")
if not (CYSD and CYS):
    print("SKIP: cysd/cys 바이너리 미발견(빌드 필요) — CI 게이트는 빌드 후 실행. skip(exit 0).")
    sys.exit(0)

os.environ["PHOENIX_HARNESS_CYSD"] = CYSD
os.environ["PATH"] = DBG + ":" + os.environ.get("PATH", "")
os.environ["PHOENIX_CYS"] = CYS  # 하네스 self 대조용(cysd 는 자체 주입)
os.environ["CYS_NO_AUTORESTORE"] = "0"  # ★E1 은 cysd auto-restore 를 검증하므로 명시 활성화(하네스 기본=비활성)

HARNMOD = os.path.join(HERE, "..", "javis_phoenix_harness.py")
spec = importlib.util.spec_from_file_location("h", HARNMOD)
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
h.CYS = CYS; h.CYSD = CYSD
h.guard_isolation()

LOG = os.path.join(h.HARN_DIR, "phoenix-restore.log")
results = []


def check(n, c, d=""):
    results.append(c); print(("PASS " if c else "FAIL ") + n + (" | " + d if d else ""))


def _wipe_state():
    h.teardown(verbose=False)  # 실행 중 데몬 밑에서 state 를 지우지 않게 먼저 kill
    shutil.rmtree(os.path.join(h.HARN_DIR, "phoenix"), ignore_errors=True)
    for f in ("topology.json", "desired_roster.json", "phoenix-restore.log"):
        try: os.remove(os.path.join(h.HARN_DIR, f))
        except OSError: pass
    # 이전 추출 잔재
    shutil.rmtree(os.path.join(h.HARN_DIR, "phoenix-embed"), ignore_errors=True)


# ★v116-phoenix-e2e: 재기동 한 번(데몬 준비 + auto-restore 판정 줄)의 대기 **상한**. 종전 고정 12초+20초(③ 8초)는
#   부하에서 phoenix 가 판정 줄을 쓰기 전에 끝나 거짓 적색을 냈다(계수 = docs/HANDOFF-v116-phoenix-e2e.md).
#   판정 줄이 나오면 즉시 반환하므로 초록 경로는 느려지지 않는다. 데몬 즉사·auto-restore 가 판정 줄 없이
#   끝남(daemon.log 종료 줄)은 상한을 기다리지 않고 바로 빠져 적색이 된다.
STAGE_WAIT = 90.0
_AR_END = ("auto-restore finished", "auto-restore non-zero", "auto-restore BREAKER_OPEN",
           "auto-restore CORRUPT", "auto-restore ABORTED", "auto-restore spawn failed",
           "auto-restore skipped", "auto-restore 스레드 panic")


def _daemon_log_size():
    try:
        return os.path.getsize(h.DAEMON_LOG)
    except OSError:
        return 0


def _auto_restore_ended(off):
    """이번 기동이 daemon.log 에 auto-restore 첫 실행 종료 줄을 남겼나(off = 기동 직전 크기)."""
    try:
        with open(h.DAEMON_LOG, "rb") as f:
            f.seek(off)
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return False
    return any(m in tail for m in _AR_END)


def _boot_and_capture(stage, want="티켓="):
    """★교체 시뮬레이션: 기존 데몬 kill → 새 cysd 기동(=교체) → auto-restore 가 phoenix-restore.log 에 판정을
    쓸 때까지 폴링(콜드부트 추출+python 기동 변동 흡수) → 로그 반환 후 teardown. teardown 선행이 없으면
    소켓 점유로 새 데몬이 안 뜨고 auto-restore 재발화가 없다(교체 관측 불가).
    반환 = (로그 본문, 데몬 응답 여부). 준비·판정 경과 초를 stderr 에 남긴다(느려짐이 초록 뒤에 숨지 않게)."""
    h.teardown(verbose=False)  # 기존 데몬 kill = 교체의 'kill' 축 · _tracked_daemon=None → 아래는 늘 새 기동
    off = _daemon_log_size()
    t0 = time.time()
    pid = h.start_daemon(wait=STAGE_WAIT)  # 새 데몬 = 교체의 '재기동' 축
    t_ready = time.time() - t0
    body, t_want, why = "", None, "상한"
    if not pid:
        why = "데몬 미응답"
    while pid and time.time() - t0 < STAGE_WAIT:
        ended = _auto_restore_ended(off)  # 먼저 본다 — 종료 뒤 로그 재독이 자식의 마지막 쓰기까지 담게
        if os.path.exists(LOG):
            body = open(LOG, encoding="utf-8", errors="replace").read()
            i = body.find(want)
            # 판정 줄이 **끝까지**(개행) 쓰였을 때만 — 줄 중간을 읽고 빠지면 뒤 칸(대상역할=)이 잘린다(agy 1R #1).
            if i >= 0 and "\n" in body[i:]:
                t_want = time.time() - t0
                break
        if ended:
            why = "auto-restore 가 판정 줄 없이 끝남"
            break
        if h._tracked_daemon is None or h._tracked_daemon.poll() is not None:
            why = "데몬 종료"
            break
        time.sleep(0.25)
    sys.stderr.write("[e2e] %s 재기동 준비 %s · 판정 줄 %s (상한 %.0fs)\n" % (
        stage, ("%.1fs" % t_ready) if pid else "★미응답",
        ("%.1fs" % t_want) if t_want is not None else "★없음(%s · %.1fs)" % (why, time.time() - t0), STAGE_WAIT))
    h.teardown(verbose=False)
    return body, bool(pid)


def _finish():
    npass = sum(1 for c in results if c)
    print("\n=== %d/%d PASS ===" % (npass, len(results)))
    return 0 if npass == len(results) else 1


def _stage(stage):
    """재기동 1회 — 데몬이 응답하지 않으면 그 사실을 판정으로 남기고 None(호출부가 즉시 중단 · 적색 유지).
    데몬 없이 계속 가면 이후 칸이 원인 없는 빈 로그로만 붉어진다(c6 와 같은 처리)."""
    body, up = _boot_and_capture(stage)
    if not up:
        check("%s 재기동 데몬 응답" % stage, False, "daemon.log=%s" % h.DAEMON_LOG)
        return None
    return body


def main():
    h.teardown(verbose=False)
    ready = bool(h._fresh_harness())
    check("셋업: 격리 데몬 응답(첫 기동)", ready, "daemon.log=%s" % h.DAEMON_LOG)
    if not ready:
        return _finish()

    # ── ① no-target NOOP + --socket enabler(격리 dir 에 로그 생성) ──
    _wipe_state()
    body = _stage("①")
    if body is None:
        return _finish()
    check("① 격리 phoenix-restore.log 생성(--socket enabler 작동)", os.path.exists(LOG) and len(body) > 0,
          "size=%d" % len(body))
    check("① no-target → NOOP(fresh live)", ("죽은 역할 0" in body) or ('"phoenix_restore": "NOOP"' in body),
          body.strip()[-100:].replace("\n", " "))

    # ── ② PHOENIX_STRICT_CYS=1 → Rust 주입으로 해석 성공(폴백 차단인데도 phoenix 가 돎·exit6/FATAL 없음) ──
    _wipe_state()
    os.environ["PHOENIX_STRICT_CYS"] = "1"
    try:
        body = _stage("②")
    finally:
        os.environ.pop("PHOENIX_STRICT_CYS", None)
    if body is None:
        return _finish()
    ran = ("죽은 역할 0" in body) or ("phoenix_restore" in body) or ("티켓=" in body)
    no_fatal = "[phoenix][FATAL]" not in body and "표준경로 폴백 금지" not in body
    check("② STRICT=1 에서 Rust 주입으로 phoenix 해석·실행 성공", ran and no_fatal,
          "ran=%s no_fatal=%s" % (ran, no_fatal))

    # ── ③ 재기동 후 seeded dead role → 부활 대상 타겟팅(kill→재기동→부활 경로) ──
    _wipe_state()
    ph = os.path.join(h.HARN_DIR, "phoenix")
    os.makedirs(ph, exist_ok=True)
    with open(os.path.join(ph, "desired_roster.json"), "w") as f:
        json.dump({"roster": {"worker-e2e": {"role": "worker-e2e"}}, "tombstones": [], "updated_at": 0}, f)
    # fresh-fallback(launch-agent=실 에이전트) 차단 — 타겟팅만 관측(실 스폰 회피).
    os.environ["PHOENIX_POISON_FRESH_FALLBACK"] = "0"
    try:
        body = _stage("③")
    finally:
        os.environ.pop("PHOENIX_POISON_FRESH_FALLBACK", None)
    if body is None:
        return _finish()
    check("③ 재기동 auto-restore 가 seeded dead role 타겟팅(부활 경로 발화)", "worker-e2e" in body,
          body.strip()[-140:].replace("\n", " "))
    check("③ 부활이 격리 desired_roster(라이브 아님)에서 대상 산출", "대상역할=" in body,
          "대상역할 라인 존재")

    return _finish()


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        try: h.teardown(verbose=False)
        except Exception: pass
