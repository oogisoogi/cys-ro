#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
javis_phoenix_encoding_smoke.py — 불사조 인코딩 독립성 스모크(TICKET=cys-phoenix-korean-windows S4ⓐⓑ)

무엇을 재는가: **로케일 기본 코덱이 UTF-8 이 아닌 기계에서 피닉스가 자기 상태파일을 읽고 로그를 쓸 수 있는가.**
  한국어 윈도우(cp949)에서 콜드부트 부활이 즉사한 실사고(오너 실측 2026-09-08)의 재현·회귀 축이다.

  실사고 연쇄(오너 로그 원문):
    load_journal → json.load(open(p))            → UnicodeDecodeError: 'cp949' … 0xe2   (저널의 UTF-8 「—」)
    → 예외 처리 중 log() → sys.stdout.write(…)   → UnicodeEncodeError: 'cp949' … '—'
    ⇒ 부활 0. 그리고 read_topology 는 같은 예외를 삼켜 **엔트리 0**(조용한 오판: 「죽은 역할 0」)으로 돌려준다.

적대 로케일 재현(이 스모크가 자식 프로세스에 주는 환경):
  · Windows CI  : chcp 949 (실 cp949) 또는 아래 mac 레버와 동일 env
  · mac/linux   : PYTHONUTF8=0 · LC_ALL=C · PYTHONCOERCECLOCALE=0 → open() 기본 코덱 = US-ASCII
                  PYTHONIOENCODING=cp949                          → stdout 코덱 = cp949(오너와 동일 예외 문구)
  두 기계에서 **코덱 이름만 다르고 병은 같다** = 「로케일 기본 코덱 ≠ utf-8」. 그래서 mac 에서도 결정론 재현된다.

격리: 자기 임시 디렉터리만 쓴다. 라이브 상태 디렉터리·데몬·앱 무접촉(자식이 state_dir_for 를 임시 경로로 고정).

exit: 0=전건 통과 · 1=하나 이상 실패 · 2=하네스 자체 오류(대상 미도달 — 통과로 읽지 말 것).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PHOENIX = os.path.join(HERE, "javis_phoenix.py")

# 로그·상태파일에 실제로 등장하는 비-ASCII(오너 로그의 그 문자들). 문구를 ASCII 로 바꿔 회피하지 않는다.
EM_DASH = "—"
SAMPLE_LOG = "★A-S1: legacy topology 통합 " + EM_DASH + " 완료"   # ★A-S1: legacy topology 통합 — 완료
SAMPLE_TEXT = "부활 대상 죽은 역할 0 " + EM_DASH        # 부활 대상 죽은 역할 0 —

# ⚠ 이 파일은 자기 stdout 을 모듈 첫머리에서 고치지 **않는다**.
#   자식(--case)의 stdout 을 여기서 utf-8 로 되돌리면 적대 코덱이 사라져 log() 축이 상시 초록이 된다
#   (측정기가 결함과 같은 자리에서 눈이 머는 형태 — 실제로 초판이 그렇게 거짓 초록을 냈다).
#   자식의 stdout 을 고쳐도 되는 유일한 주체는 **검사 대상인 javis_phoenix.py 자신**이다.
#   부모(요약 출력)만 main() 안에서 자기 stdout 을 utf-8 로 세운다.


def hostile_env():
    """자식에게 줄 적대 로케일 환경(부모 환경 복사 + 덮어쓰기)."""
    e = dict(os.environ)
    e["PYTHONUTF8"] = "0"                 # UTF-8 모드 off → open() 이 로케일 코덱을 쓴다
    e["PYTHONCOERCECLOCALE"] = "0"        # C 로케일 강제 승격(UTF-8 화) 차단
    e["LC_ALL"] = "C"
    e["LANG"] = "C"
    e["PYTHONIOENCODING"] = "cp949"       # stdout/stderr = cp949 (오너 로그와 동일 코덱)
    e["PHOENIX_FORBID_LIVE"] = "1"        # 라이브 상태 디렉터리 대상 실행 원천 거부
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return e


# 자식(적대 로케일)에서 실행되는 케이스 본문. 부모가 --case 로 하나씩 호출한다.
CASES = ["log_em_dash", "journal_utf8_read", "journal_corrupt_read",
         "journal_roundtrip", "topology_read", "roster_status_valid", "desired_roster_read"]


def _load_module(tmp):
    import importlib.util
    spec = importlib.util.spec_from_file_location("javis_phoenix_under_test", PHOENIX)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # 격리: 상태 디렉터리를 임시 경로로 고정(phoenix_home 는 실물 그대로 동작 — 하위 phoenix/ 를 만든다)
    mod.state_dir_for = lambda socket, _d=tmp: _d
    return mod


def _write_bytes(path, text):
    """의도적으로 **UTF-8 바이트**로 쓴다 — 라이브 데몬(Rust)이 UTF-8 로 쓰는 실제 상황 재현."""
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))


def run_case(name, tmp):
    mod = _load_module(tmp)
    sock = os.path.join(tmp, "cys.sock")
    ticket = "encsmoke"

    if name == "log_em_dash":
        mod.log(SAMPLE_LOG)
        return "log() wrote em-dash line"

    if name == "journal_utf8_read":
        p = mod.journal_path(sock, ticket)
        _write_bytes(p, json.dumps({"ticket_id": ticket, "roles": {"master": {"note": SAMPLE_TEXT}},
                                    "events": [], "created": 0}, ensure_ascii=False))
        j = mod.load_journal(sock, ticket)
        got = j.get("roles", {}).get("master", {}).get("note")
        assert got == SAMPLE_TEXT, "journal note mismatch: %r" % (got,)
        return "load_journal preserved non-ascii journal"

    if name == "journal_corrupt_read":
        p = mod.journal_path(sock, ticket + "-corrupt")
        _write_bytes(p, "{ this is not json " + SAMPLE_TEXT)
        j = mod.load_journal(sock, ticket + "-corrupt")   # 손상 분기 + log(「—」) 를 함께 태운다
        assert j.get("roles") == {}, "corrupt journal should yield fresh dict, got %r" % (j,)
        return "corrupt-journal branch survived (isolate + log with em-dash)"

    if name == "journal_roundtrip":
        j = {"ticket_id": ticket, "roles": {"cso": {"msg": SAMPLE_LOG}}, "events": [], "created": 0}
        mod.save_journal(sock, ticket + "-rt", j)
        back = mod.load_journal(sock, ticket + "-rt")
        assert back["roles"]["cso"]["msg"] == SAMPLE_LOG, "roundtrip mismatch: %r" % (back,)
        return "save_journal -> load_journal roundtrip preserved non-ascii"

    if name == "topology_read":
        p = os.path.join(tmp, "topology.json")
        _write_bytes(p, json.dumps({"entries": [{"role": "master", "agent": "claude",
                                                 "title": SAMPLE_TEXT}], "updated_at": 1},
                                   ensure_ascii=False))
        t = mod.read_topology(sock)
        # ★조용한 실패 축: 인코딩 예외를 삼키면 entries=[] 로 돌아온다(= 「죽은 역할 0」 오판)
        assert "_error" not in t, "read_topology swallowed an error: %s" % t.get("_error")
        assert len(t.get("entries", [])) == 1, "read_topology lost entries: %r" % (t,)
        assert t["entries"][0]["title"] == SAMPLE_TEXT, "topology title mangled: %r" % (t,)
        return "read_topology parsed non-ascii topology (entries=1)"

    if name == "roster_status_valid":
        p = os.path.join(tmp, "roster-probe.json")
        _write_bytes(p, json.dumps({"roster": {"master": {"n": SAMPLE_TEXT}}}, ensure_ascii=False))
        st = mod._roster_file_status(p)
        assert st == "valid", "_roster_file_status misread non-ascii file as %r" % (st,)
        return "_roster_file_status classified non-ascii file as valid"

    if name == "desired_roster_read":
        p = mod.desired_roster_path(sock)
        _write_bytes(p, json.dumps({"roster": {"master": {"agent": "claude", "note": SAMPLE_TEXT}},
                                    "tombstones": []}, ensure_ascii=False))
        roster, tombs = mod.load_desired_roster(sock)
        assert "master" in roster, "desired roster lost entries: %r" % (roster,)
        assert roster["master"]["note"] == SAMPLE_TEXT, "desired roster mangled: %r" % (roster,)
        return "load_desired_roster preserved non-ascii roster"

    raise SystemExit("unknown case: %s" % name)


def main():
    if "--case" in sys.argv:
        i = sys.argv.index("--case")
        name = sys.argv[i + 1]
        tmp = sys.argv[sys.argv.index("--tmp") + 1]
        try:
            detail = run_case(name, tmp)
        except Exception as e:
            # 자식 stdout 은 적대 코덱이므로 진단문에 비-ASCII 를 싣지 않는다(진단이 진단을 죽이지 않게).
            sys.stdout.write("CASE-FAIL %s :: %s: %s\n" % (name, type(e).__name__, str(e)[:400].encode(
                "ascii", "backslashreplace").decode("ascii")))
            return 1
        sys.stdout.write("CASE-PASS %s :: %s\n" % (name, detail))
        return 0

    # ---- 부모: 케이스마다 적대 로케일 자식 1개 ----
    try:  # 부모만 — 요약을 utf-8 로 낸다(자식은 적대 코덱을 그대로 쓴다)
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
    env = hostile_env()
    print("[enc-smoke] target   = %s" % PHOENIX)
    print("[enc-smoke] hostile  = PYTHONUTF8=0 LC_ALL=C PYTHONCOERCECLOCALE=0 PYTHONIOENCODING=cp949")
    print("[enc-smoke] cases    = %d" % len(CASES))
    failed = []
    ran = 0
    for name in CASES:
        tmp = tempfile.mkdtemp(prefix="phx-enc-")
        try:
            r = subprocess.run([sys.executable, os.path.abspath(__file__), "--case", name, "--tmp", tmp],
                               env=env, capture_output=True, timeout=120)
            ran += 1
            out = (r.stdout or b"").decode("utf-8", "backslashreplace").strip()
            err = (r.stderr or b"").decode("utf-8", "backslashreplace").strip()
            ok = (r.returncode == 0) and ("CASE-PASS" in out)
            print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
            if not ok:
                failed.append(name)
                for line in (out + ("\n" + err if err else "")).splitlines():
                    print("        | %s" % line[:300])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("[enc-smoke] ran=%d pass=%d fail=%d" % (ran, ran - len(failed), len(failed)))
    if ran != len(CASES):
        print("[enc-smoke] HARNESS-ERROR: 실행 케이스 수 불일치 — 측정 실패(통과로 읽지 말 것)")
        return 2
    if failed:
        print("[enc-smoke] FAILED: %s" % ", ".join(failed))
        return 1
    print("[enc-smoke] OK — 로케일 기본 코덱이 utf-8 이 아니어도 피닉스는 자기 상태를 읽고 로그를 쓴다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
