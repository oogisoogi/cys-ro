#!/usr/bin/env python3
"""javis_awaken.py — 자식 좌석 각성 보장 루프 (TICKET=pack-awaken-enter · 2026-09-16).

결함(박사님 샌드박스 5회/5회 재현): 참가자 함대에서 cso·worker 자리의 각성 지시가 입력줄에
「[Pasted text #1 +529 lines]」로 붙여넣기만 되고 Enter 가 안 들어가 영구 대기한다.
주입자는 Rust `cys launch-agent` 의 inject_text(붙여넣기 → 0.8s → Return)이고, 콜드스타트에서
그 Return 이 먹히지 않는 경로가 있다(우리 spawn-worker.sh 헤더 F1 실측과 같은 모양).

이 모듈은 그 위에 **각성 보장 루프 하나**를 얹는다. 소비자는 스폰 경로 둘이다 —
javis_boot_node(LAUNCH 직후) · javis_phoenix(fresh 강등 직후). 사본을 두지 않는다.

  1.5s 대기 → 측정 → 제출 흔적 0 이면 Return → 3s → 재측 → (Return → 5s → 재측) → (Return → 8s → 재측)
  → 여전히 0 이면 awaken=unconfirmed 기록 + master 좌석에 1줄 보고.

★판정은 화면이 아니라 세션 jsonl 이다(화면 파싱은 거짓 양성을 냈다 — 09dcab0).
  <설정폴더>/projects/<cwd 슬러그>/<세션>.jsonl 에 `"type":"user"` 레코드가 생겼는가.
  · 슬러그 = cwd 의 [A-Za-z0-9] 가 아닌 글자 하나당 '-' 하나(우리 맥 ~/.cys/claude/projects 실물 대조 ·
    한글도 NFC 글자당 1개). 슬러그 폴더가 없거나 비었으면 projects/ 전체에서 이번 스폰 이후 갱신된
    파일 중 레코드 cwd 가 같은 것을 찾는다(추정 대신 대조).
  · 신선도: 이번 스폰 시각(since) 이후의 레코드만 센다 — 같은 좌석 폴더의 지난 세션을 각성으로 읽지 않는다.

★Return 을 보내도 되는 조건(고스트 제안 제출 차단):
  빈 입력줄의 Enter 는 Claude Code 프롬프트 제안(회색 글씨)을 제출할 수 있다. 제안은 **이전 대화**에서
  만들어진다. 그래서 Return 은 **이 런이 launch-agent 로 방금 띄운 새 프로세스**이고 그 세션의 제출
  흔적이 0 일 때만 보낸다(may_return=True). 입양한 기존 좌석은 측정·기록·보고만 한다.
  nudge(master 수동 경로)는 기록된 unconfirmed 좌석이 같은 pid 로 살아 있을 때만 Return 을 보낸다.

종료코드: 0 = 각성 확인 · 1 = 미확인 · 2 = 인자 오류·대상 해석 불가.
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

AWAKEN_CONFIRMED = "confirmed"
AWAKEN_UNCONFIRMED = "unconfirmed"
FIRST_WAIT_S = 1.5
RETRY_WAITS_S = (3, 5, 8)
# 파일시스템 mtime·레코드 시각의 거칠기 흡수(초). 지난 세션을 끌어들일 만큼 넓히지 않는다.
SINCE_SLACK_S = 2.0


# ───────────────────────── 경로 ─────────────────────────
def config_dirs(env=None):
    """자식 claude 가 쓸 수 있는 설정 폴더 후보(중복 제거·순서 보존).
    agents.json 규칙 = CLAUDE_CONFIG_DIR="${CYS_ACCOUNT_DIR:-$HOME/.cys/claude}" · 부서 팩은 다른 값을
    시드할 수 있으므로 호출자 env 의 CLAUDE_CONFIG_DIR 도 후보에 넣는다."""
    env = os.environ if env is None else env
    out = []
    for v in (env.get("CLAUDE_CONFIG_DIR"), env.get("CYS_ACCOUNT_DIR"),
              os.path.join(os.path.expanduser("~"), ".cys", "claude")):
        v = (v or "").strip()
        if v and v not in out:
            out.append(v)
    return out


def slug(cwd):
    return re.sub(r"[^A-Za-z0-9]", "-", cwd)


def cwd_variants(cwd):
    """같은 폴더의 표기 변형(실경로 · 한글 NFC/NFD). 판정은 이 집합과의 일치다."""
    out = []
    for c in (cwd, os.path.realpath(cwd)):
        for form in ("NFC", "NFD"):
            v = unicodedata.normalize(form, c)
            if v not in out:
                out.append(v)
    return out


def _state_dir():
    return os.path.join(os.environ.get("CYS_STATE_DIR")
                        or os.path.join(os.path.expanduser("~"), ".cys", "state"), "awaken")


def _key(socket, role):
    s = "%s__%s" % (socket or "base", role)
    return re.sub(r"[^A-Za-z0-9_.-]", "_", s)[-150:]


def state_path(role, socket=None):
    return os.path.join(_state_dir(), _key(socket, role) + ".json")


# ───────────────────────── 측정 ─────────────────────────
def _ts_epoch(ts):
    """'2026-09-15T15:12:23.453Z' → epoch. 해석 불가면 None."""
    if not isinstance(ts, str):
        return None
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def _read_records(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for ln in f:
                try:
                    d = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    yield d
    except OSError:
        return


def _candidate_files(cwd, since, dirs):
    """(파일, 출처) 목록 — 1순위 슬러그 폴더 · 없으면 projects/ 전체에서 cwd 대조."""
    floor = since - SINCE_SLACK_S
    variants = cwd_variants(cwd)
    found = []
    for d in dirs:
        for v in variants:
            for p in glob.glob(os.path.join(d, "projects", slug(v), "*.jsonl")):
                try:
                    if os.path.getmtime(p) >= floor and (p, "slug") not in found:
                        found.append((p, "slug"))
                except OSError:
                    pass
    if found:
        return found
    for d in dirs:
        for p in glob.glob(os.path.join(d, "projects", "*", "*.jsonl")):
            try:
                if os.path.getmtime(p) < floor:
                    continue
            except OSError:
                continue
            for rec in _read_records(p):
                c = rec.get("cwd")
                if isinstance(c, str):
                    if c in variants:
                        found.append((p, "cwd-scan"))
                    break
    return found


def measure(cwd, since, dirs=None):
    """이번 스폰(since) 이후 그 cwd 세션에 제출된 user 레코드 수.
    반환 {"user": n, "files": [...], "source": "slug"|"cwd-scan"|"none"}."""
    dirs = config_dirs() if dirs is None else dirs
    files = _candidate_files(cwd, since, dirs)
    floor = since - SINCE_SLACK_S
    users = 0
    for p, _src in files:
        for rec in _read_records(p):
            if rec.get("type") != "user" or rec.get("isMeta"):
                continue
            t = _ts_epoch(rec.get("timestamp"))
            # 시각을 못 읽는 user 레코드는 「제출이 있었다」 쪽으로 센다 — 틀릴 때의 귀결이
            # Return 생략(보고로 드러남)이지 이전 대화가 있는 세션에 Return(고스트 제출)이 아니다.
            if t is None or t >= floor:
                users += 1
    return {"user": users, "files": [p for p, _ in files],
            "source": files[0][1] if files else "none"}


# ───────────────────────── cys 호출 ─────────────────────────
def default_runner(socket=None, timeout=12):
    def _run(args):
        cmd = ["cys"] + list(args)
        env = dict(os.environ)
        if socket:
            env["CYS_SOCKET"] = socket
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env, **NOWIN)
            return r.returncode, r.stdout.decode("utf-8", "replace")
        except Exception:
            return 255, ""
    return _run


def surface_row(runner, surface=None, role=None):
    """`cys list` 행(탭 구분 · 끝 칸 = cwd)에서 surface 또는 role 로 한 행."""
    rc, out = runner(["list"])
    if rc != 0:
        return None
    for ln in (out or "").splitlines():
        cols = ln.split("\t")
        if not cols or not cols[0].startswith("surface:"):
            continue
        kv = dict(c.split("=", 1) for c in cols[1:] if "=" in c)
        if kv.get("exited") == "true":
            continue
        if (surface and cols[0] == surface) or (role and not surface and kv.get("role") == role):
            pid = kv.get("pid", "")
            return {"surface": cols[0], "role": kv.get("role"),
                    "pid": int(pid) if pid.isdigit() else None,
                    "cwd": cols[-1] if len(cols) > 1 and "=" not in cols[-1] else None}
    return None


def send_return(runner, surface):
    rc, _ = runner(["send-key", "--surface", surface, "Return"])
    if rc != 0:
        # 타이핑 가드 등으로 직접 전송이 거부되면 Return 한정 큐로 1회 전환(send-key --queued = Return 전용).
        rc, _ = runner(["send-key", "--queued", "--surface", surface, "Return"])
    return rc


def report_line(role, surface):
    return ("[awaken] %s 자리(%s) 각성 미확인 — 수동 Enter 필요 · 확인·재시도: "
            "python3 \"${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_awaken.py\" nudge --role %s"
            % (role, surface, role))


def _write_state(result, socket=None):
    path = state_path(result["role"], socket)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, path)
        return path
    except OSError as e:
        sys.stderr.write("[awaken] WARN: 상태 기록 실패(%s)\n" % e)
        return None


def read_state(role, socket=None):
    try:
        with open(state_path(role, socket), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ───────────────────────── 루프 ─────────────────────────
def ensure_awake(role, surface, cwd, since, runner, pid=None, may_return=True, socket=None,
                 dirs=None, sleep=time.sleep, first_wait=FIRST_WAIT_S, waits=RETRY_WAITS_S,
                 report=True):
    """각성 보장 루프 — 스폰 경로 공통 진입점. 반환 = 기록한 결과 dict."""
    sleep(first_wait)
    m = measure(cwd, since, dirs)
    returns = 0
    if m["user"] == 0 and may_return:
        for w in waits:
            send_return(runner, surface)
            returns += 1
            sleep(w)
            m = measure(cwd, since, dirs)
            if m["user"] > 0:
                break
    awaken = AWAKEN_CONFIRMED if m["user"] > 0 else AWAKEN_UNCONFIRMED
    result = {
        "role": role, "surface": surface, "pid": pid, "cwd": cwd, "since": since,
        "awaken": awaken, "returns_sent": returns, "may_return": bool(may_return),
        "evidence": {"user_records": m["user"], "jsonl": m["files"], "source": m["source"]},
        "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    result["reported"] = False
    if awaken == AWAKEN_UNCONFIRMED and report and role != "master":
        rc, _ = runner(["send", "--queued", "--to", "master", report_line(role, surface)])
        result["reported"] = rc == 0
    _write_state(result, socket)
    return result


def describe(res):
    return "awaken=%s (user 레코드 %d · 출처 %s · Return %d회%s)" % (
        res["awaken"], res["evidence"]["user_records"], res["evidence"]["source"],
        res["returns_sent"], "" if res["may_return"] else " · 입양 좌석 = 측정만")


# ───────────────────────── CLI ─────────────────────────
def cmd_status(a):
    d = _state_dir()
    rows = []
    for p in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                rows.append(json.load(f))
        except (OSError, ValueError):
            continue
    if a.role:
        rows = [r for r in rows if r.get("role") == a.role]
    if a.json:
        print(json.dumps(rows, ensure_ascii=False))
    else:
        for r in rows:
            print("%s\t%s\t%s\t%s" % (r.get("role"), r.get("surface"), r.get("awaken"), r.get("at")))
    return 1 if any(r.get("awaken") == AWAKEN_UNCONFIRMED for r in rows) else 0


def cmd_nudge(a):
    """master 경로 — 기록된 unconfirmed 좌석이 **같은 pid 로** 살아 있을 때만 Return 루프를 다시 돈다.
    기록이 없거나 pid 가 갈렸으면 측정만 한다(이전 대화가 있을 수 있는 세션에 Return 금지)."""
    runner = default_runner(a.socket)
    st = read_state(a.role, a.socket)
    row = surface_row(runner, role=a.role)
    if row is None:
        print("[awaken] %s 좌석을 cys list 에서 찾지 못함" % a.role)
        return 2
    since = st.get("since") if st else None
    cwd = row.get("cwd") or (st or {}).get("cwd")
    if not cwd:
        print("[awaken] %s 좌석 cwd 해석 불가" % a.role)
        return 2
    same = bool(st) and st.get("surface") == row["surface"] and st.get("pid") == row["pid"]
    may_return = same and st.get("awaken") == AWAKEN_UNCONFIRMED
    res = ensure_awake(a.role, row["surface"], cwd, since if since is not None else 0.0, runner,
                       pid=row["pid"], may_return=may_return, socket=a.socket, report=False)
    print(json.dumps(res, ensure_ascii=False) if a.json else "[awaken] %s %s" % (a.role, describe(res)))
    return 0 if res["awaken"] == AWAKEN_CONFIRMED else 1


def self_test():
    fails = []
    if slug("/Users/oogisoogi/axdev/.wt/cys-awaken") != "-Users-oogisoogi-axdev--wt-cys-awaken":
        fails.append("슬러그 규칙(실물 폴더명) 불일치")
    if slug("/Users/oogisoogi/내 드라이브/01_axdev") != "-Users-oogisoogi--------01-axdev":
        fails.append("한글 NFC 글자당 1 슬러그 불일치")
    if _ts_epoch("2026-09-15T15:12:23.453Z") is None or _ts_epoch("garbage") is not None:
        fails.append("레코드 시각 해석")
    if fails:
        print("self-test FAIL: " + " · ".join(fails))
        return 1
    print("javis_awaken self-test OK (슬러그 실물 2 · 시각 해석)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("status")
    p.add_argument("--role")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("nudge")
    p.add_argument("--role", required=True)
    p.add_argument("--socket")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.cmd == "status":
        return cmd_status(a)
    if a.cmd == "nudge":
        return cmd_nudge(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
