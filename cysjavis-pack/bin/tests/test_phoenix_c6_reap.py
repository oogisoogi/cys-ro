#!/usr/bin/env python3
"""W2/C6 실 잔재 회수 E2E(리포 커밋·mac 게이트). W1 탐지-only 를 P0-6 cause 활용 실 회수로 전환한 것을
격리 cysd 로 실측: exited=true 잔재를 Reap 사유(cys close-surface --reap → CloseCause::Reap)로만 회수 —
라이브 오회수 0·회수분 묘비 0(desired·topology 불변). 바이너리 미발견 시 skip(exit 0). 라이브 무접촉.

실행: python3 cysjavis-pack/bin/tests/test_phoenix_c6_reap.py
"""
import importlib.util, os, sys, time, re, json, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DBG = os.path.join(REPO, "target", "debug")


def _find(name):
    env = os.environ.get("PHOENIX_HARNESS_" + name.upper())
    if env and os.path.exists(env):
        return env
    c = os.path.join(DBG, name)
    return c if os.path.exists(c) else shutil.which(name)


CYSD, CYS = _find("cysd"), _find("cys")
if not (CYSD and CYS):
    print("SKIP: cysd/cys 미발견(빌드 필요) — CI 게이트는 빌드 후 실행. skip(exit 0).")
    sys.exit(0)

os.environ["PHOENIX_HARNESS_CYSD"] = CYSD
os.environ["PATH"] = DBG + ":" + os.environ.get("PATH", "")
os.environ["PHOENIX_CYS"] = CYS
spec = importlib.util.spec_from_file_location("h", os.path.join(HERE, "..", "javis_phoenix_harness.py"))
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
h.CYS = CYS; h.CYSD = CYSD
h.guard_isolation()

PH = os.path.join(HERE, "..", "javis_phoenix.py")
results = []
def check(n, c, d=""):
    results.append(c); print(("PASS " if c else "FAIL ") + n + (" | " + d if d else ""))


def _run_phoenix(args, timeout=60):
    import subprocess
    env = dict(os.environ); env["PHOENIX_CYS"] = CYS
    cmd = [sys.executable, PH, "--socket", h.HARN_SOCK] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    txt = r.stdout or ""
    i = txt.find("{")
    return (json.loads(txt[i:]) if i >= 0 else {}), r


def main():
    h.teardown(verbose=False); h._fresh_harness()
    shutil.rmtree(os.path.join(h.HARN_DIR, "phoenix"), ignore_errors=True)
    for f in ("topology.json", "desired_roster.json"):
        try: os.remove(os.path.join(h.HARN_DIR, f))
        except OSError: pass
    # ★v116-flake-pty ⑴: 하네스 start_daemon 이 멱등이 되어 이 호출은 _fresh_harness 가 띄운 데몬의 준비를
    #   기다릴 뿐 두 번째 cysd 를 띄우지 않는다. 데몬이 응답하지 않으면 그 사실을 첫 판정으로 드러낸다
    #   (종전엔 반환값을 버려 `list=` 빈 출력만 남았다 — 원인이 안 보였다).
    pid = h.start_daemon(wait=12.0)
    ready = bool(pid) and h.harness_ping()
    check("셋업: 격리 데몬 응답", ready, "pid=%s daemon.log=%s" % (pid, h.DAEMON_LOG))
    if not ready:
        # 데몬 없이 진행하면 `cys new-surface` 가 추적 밖 cysd 를 autostart 할 수 있다(CYS_STATE_DIR 격리 없음 —
        # 09-04 라이브 오염 경로 · 적대 1R #4). 여기서 멈춘다(적색 유지 · teardown 은 호출부 finally).
        print("\n=== %d/%d PASS ===" % (sum(1 for c in results if c), len(results)))
        return 1
    try:
        # 라이브 surface 1개(회수 비대상) + exited 잔재 1개 생성.
        def _new_surface():
            r = h.cys("new-surface")
            return (r.stdout or ""), "rc=%s err=%s" % (r.returncode, (r.stderr or "").strip()[:160])
        live, live_diag = _new_surface()
        live_ref = (re.search(r"(surface:\d+)", live) or [None])[0] if re.search(r"(surface:\d+)", live) else None
        if live_ref:
            h.cys("send", "--surface", live_ref, "sleep 3600"); h.cys("send-key", "--surface", live_ref, "Return")
        stale, stale_diag = _new_surface()
        stale_ref = re.search(r"(surface:\d+)", stale)
        stale_ref = stale_ref.group(1) if stale_ref else None
        lst_before = ""
        if stale_ref:
            h.cys("send", "--surface", stale_ref, "exit"); h.cys("send-key", "--surface", stale_ref, "Return")
            # 고정 2초 대기 → exited=true 폴링(상한 20초). 부하에서 셸 종료 관측이 2초를 넘어도 붉지 않되,
            # 잔재가 끝내 안 생기면 종전과 똑같이 붉다(상한 있음).
            t0 = time.time()
            waited = None
            while time.time() - t0 < 20.0:
                lst_before = h.cys("list").stdout or ""
                if any(l.split("\t", 1)[0] == stale_ref and "exited=true" in l for l in lst_before.splitlines()):
                    waited = time.time() - t0
                    break
                time.sleep(0.25)
        else:
            lst_before = h.cys("list").stdout or ""
        exited_present = "exited=true" in lst_before
        # 대기 초를 남긴다 — 종전 고정 2초보다 느려진 종료 관측이 초록 뒤에 숨지 않게(적대 1R #5).
        check("셋업: exited 잔재 생성됨", exited_present, "exited 관측 %s | list=%s | new-surface live[%s] stale[%s]"
              % (("%.2fs" % waited) if stale_ref and waited is not None else "없음(상한 20s)",
                 lst_before.replace("\n", " ")[:120], live_diag, stale_diag))

        # 묘비 스냅샷(회수 전)
        def tombs(path, key="tombstones"):
            p = os.path.join(h.HARN_DIR, path)
            if os.path.exists(p):
                try: return set(json.load(open(p)).get(key, []))
                except Exception: return set()
            return set()

        # phoenix restore → C6 S0 실 회수.
        res, _ = _run_phoenix(["restore", "--stub", "--ticket", "c6r"])
        reaped = res.get("c6_reaped") or []
        detected = res.get("c6_stale_surfaces") or []
        check("C6 exited 잔재 Reap 회수됨", stale_ref in reaped if stale_ref else len(reaped) >= 1,
              "reaped=%s detected=%s" % (reaped, [d.get("surface") for d in detected]))
        # 라이브 오회수 0: live_ref 는 reaped 에 없어야 하고 여전히 살아있어야 함.
        lst_after = h.cys("list").stdout or ""
        live_alive = live_ref and (live_ref in lst_after) and ("exited=true" not in
                     [l for l in lst_after.splitlines() if live_ref in l][0] if any(live_ref in l for l in lst_after.splitlines()) else True)
        check("C6 라이브 오회수 0(live 생존)", (live_ref not in reaped) if live_ref else True,
              "live_ref=%s reaped=%s" % (live_ref, reaped))
        # 회수분 묘비 0: desired·topology tombstones 에 회수 대상 없음(Reap=묘비 미생성).
        d_tombs = tombs("phoenix/desired_roster.json")
        t_tombs = tombs("topology.json")
        check("C6 회수분 묘비 0(desired)", len(d_tombs) == 0, "desired.tombstones=%s" % sorted(d_tombs))
        check("C6 회수분 묘비 0(topology)", len(t_tombs) == 0, "topology.tombstones=%s" % sorted(t_tombs))
    finally:
        h.teardown(verbose=False)

    npass = sum(1 for c in results if c)
    print("\n=== %d/%d PASS ===" % (npass, len(results)))
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    try: sys.exit(main())
    finally:
        try: h.teardown(verbose=False)
        except Exception: pass
