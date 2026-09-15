#!/usr/bin/env python3
"""test_awaken_enter.py — 자식 좌석 각성 보장 루프 계약 핀 (TICKET=pack-awaken-enter · 2026-09-16).

결함: 자식 자리(cso·worker)의 지침이 입력줄에 붙여넣기만 되고 Enter 가 안 들어가 영구 대기.
처방: javis_awaken.ensure_awake — 세션 jsonl 로 재고 제출 흔적이 없으면 Return(최대 3회) → 기록·보고.

케이스(가짜 jsonl 픽스처 · 가짜 cys):
  A 미제출 → Return → user 1           B 이미 각성 → 무동작·Return 0
  C 3회 실패 → unconfirmed + 기록 + master 보고
  D 지난 세션(시각이 스폰 이전) 은 각성으로 세지 않는다 · D2 옛 파일(mtime) 은 보지 않는다
  E 입양 좌석(may_return=False) = Return 0      F master 자리는 자기에게 보고하지 않는다
  G 슬러그 폴더가 없어도 레코드 cwd 대조로 찾는다   H 한글 NFD cwd 도 NFC 슬러그 폴더와 맞춘다
  I 직접 Return 거부 시 --queued 로 1회 전환
  W 배선 핀: boot_node 는 launch 한 경우에만 · phoenix fresh 는 같은 함수 · may_return=True
뮤턴트: 모듈 사본에 변이를 걸어(적용 1건 선-assert) 위 케이스가 적색이 되는지 잰다.

실행: python3 test_awaken_enter.py   (exit 0=PASS / 1=FAIL)
"""
import ast
import datetime
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import unicodedata

SELF = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.normpath(os.path.join(SELF, ".."))
MODULE = os.path.join(BIN, "javis_awaken.py")

fails = []
_total = [0]


def check(name, cond, detail=""):
    _total[0] += 1
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))
    if not cond:
        fails.append(name)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def write_session(cfg, dirname, cwd, records, sid="s1", mtime=None):
    d = os.path.join(cfg, "projects", dirname)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, sid + ".jsonl")
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "attachment", "cwd": cwd}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def user_rec(cwd, t, with_ts=True):
    r = {"type": "user", "cwd": cwd, "message": {"role": "user", "content": "# WORKER ABSOLUTE DIRECTIVE"}}
    if with_ts:
        r["timestamp"] = iso(t)
    return r


class FakeCys:
    def __init__(self, on_return=None, return_rc=0):
        self.calls = []
        self.on_return = on_return
        self.return_rc = return_rc

    def __call__(self, args):
        args = list(args)
        self.calls.append(args)
        if args and args[0] == "send-key" and "Return" in args:
            if "--queued" in args:
                return 0, ""
            if self.on_return:
                self.on_return()
            return self.return_rc, ""
        return 0, ""

    def returns(self):
        return [c for c in self.calls if c and c[0] == "send-key"]

    def reports(self):
        return [c for c in self.calls if c[:4] == ["send", "--queued", "--to", "master"]]


def run_cases(mod, verbose=True):
    """케이스 전부 — 반환 = 실패 이름 목록(뮤턴트 판정에도 쓴다)."""
    local = []

    def chk(name, cond, detail=""):
        if verbose:
            check(name, cond, detail)
        elif not cond:
            local.append(name)

    root = tempfile.mkdtemp(prefix="awaken-")
    prev_state = os.environ.get("CYS_STATE_DIR")
    os.environ["CYS_STATE_DIR"] = os.path.join(root, "state")
    nosleep = lambda s: None  # noqa: E731
    try:
        cwd = "/tmp/jarvis-home/workers/w1"
        cfg = os.path.join(root, "claude")
        slug_dir = mod.slug(cwd)

        def ensure(role="worker", cfgdir=cfg, c=cwd, runner=None, **kw):
            return mod.ensure_awake(role, "surface:9", c, since, runner, pid=42,
                                    dirs=[cfgdir], sleep=nosleep, **kw)

        # A — 미제출 → Return → user 1
        since = time.time()
        fa = FakeCys(on_return=lambda: write_session(cfg, slug_dir, cwd, [user_rec(cwd, time.time())]))
        ra = ensure(runner=fa)
        chk("A 미제출→Return→confirmed", ra["awaken"] == mod.AWAKEN_CONFIRMED, str(ra["awaken"]))
        chk("A Return 정확히 1회", ra["returns_sent"] == 1 and len(fa.returns()) == 1,
            "returns_sent=%s calls=%s" % (ra["returns_sent"], fa.returns()))
        chk("A 보고 없음", not fa.reports())
        chk("A 근거 = jsonl user 1", ra["evidence"]["user_records"] == 1 and ra["evidence"]["source"] == "slug")

        # B — 이미 각성 → 무동작
        cfg_b = os.path.join(root, "claude-b")
        since = time.time()
        write_session(cfg_b, slug_dir, cwd, [user_rec(cwd, time.time())])
        fb = FakeCys()
        rb = ensure(cfgdir=cfg_b, runner=fb)
        chk("B 이미 각성→confirmed", rb["awaken"] == mod.AWAKEN_CONFIRMED)
        chk("B Return 0회(send-key 호출 0)", rb["returns_sent"] == 0 and not fb.returns(), str(fb.calls))

        # C — 3회 실패 → unconfirmed + 기록 + 보고
        cfg_c = os.path.join(root, "claude-c")
        since = time.time()
        fc = FakeCys()
        rc = ensure(cfgdir=cfg_c, runner=fc)
        chk("C 3회 실패→unconfirmed", rc["awaken"] == mod.AWAKEN_UNCONFIRMED)
        chk("C Return 3회", rc["returns_sent"] == 3 and len(fc.returns()) == 3, str(fc.returns()))
        rep = fc.reports()
        chk("C master 보고 1줄(역할·수동 Enter 명시)",
            len(rep) == 1 and "worker" in rep[0][4] and "각성 미확인" in rep[0][4] and "수동 Enter" in rep[0][4],
            str(rep))
        st = mod.read_state("worker")
        chk("C 상태 기록 awaken=unconfirmed", bool(st) and st.get("awaken") == mod.AWAKEN_UNCONFIRMED
            and st.get("pid") == 42 and st.get("surface") == "surface:9", str(st))

        # D — 지난 세션 레코드(스폰 이전 시각)는 각성이 아니다(파일 mtime 은 새것)
        cfg_d = os.path.join(root, "claude-d")
        since = time.time()
        write_session(cfg_d, slug_dir, cwd, [user_rec(cwd, since - 3600)])
        fd = FakeCys()
        rd = ensure(cfgdir=cfg_d, runner=fd)
        chk("D 스폰 이전 레코드를 각성으로 세지 않음", rd["awaken"] == mod.AWAKEN_UNCONFIRMED, str(rd["evidence"]))

        # D2 — 옛 파일(mtime 이 스폰 이전)은 후보가 아니다(시각 없는 레코드라도)
        cfg_d2 = os.path.join(root, "claude-d2")
        since = time.time()
        write_session(cfg_d2, slug_dir, cwd, [user_rec(cwd, 0, with_ts=False)], mtime=since - 3600)
        rd2 = ensure(cfgdir=cfg_d2, runner=FakeCys())
        chk("D2 옛 세션 파일을 보지 않음", rd2["awaken"] == mod.AWAKEN_UNCONFIRMED, str(rd2["evidence"]))

        # D3 — 빠른 재시작: 직전 세션 레코드가 스폰 1초 전(파일 mtime 여유 안)이어도 각성이 아니다
        cfg_d3 = os.path.join(root, "claude-d3")
        since = time.time()
        write_session(cfg_d3, slug_dir, cwd, [user_rec(cwd, since - 1.0)])
        rd3 = ensure(cfgdir=cfg_d3, runner=FakeCys())
        chk("D3 스폰 1초 전 레코드(재시작 틈)를 각성으로 세지 않음", rd3["awaken"] == mod.AWAKEN_UNCONFIRMED,
            str(rd3["evidence"]))

        # E — 입양 좌석: Return 금지
        cfg_e = os.path.join(root, "claude-e")
        since = time.time()
        fe = FakeCys()
        re_ = ensure(cfgdir=cfg_e, runner=fe, may_return=False)
        chk("E may_return=False → Return 0", not fe.returns() and re_["returns_sent"] == 0, str(fe.calls))
        chk("E 미확인은 그대로 기록", re_["awaken"] == mod.AWAKEN_UNCONFIRMED)

        # F — master 자리는 자기에게 보고하지 않는다
        cfg_f = os.path.join(root, "claude-f")
        since = time.time()
        ff = FakeCys()
        rf = ensure(role="master", cfgdir=cfg_f, runner=ff)
        chk("F master 미확인 → 자기 보고 0", rf["awaken"] == mod.AWAKEN_UNCONFIRMED and not ff.reports(),
            str(ff.reports()))

        # G — 슬러그 폴더가 없어도(긴 경로 등) 레코드 cwd 대조로 찾는다
        cfg_g = os.path.join(root, "claude-g")
        since = time.time()
        write_session(cfg_g, "-some-other-name-hash123", cwd, [user_rec(cwd, time.time())])
        fg = FakeCys()
        rg = ensure(cfgdir=cfg_g, runner=fg)
        chk("G cwd 대조 폴백으로 confirmed · Return 0",
            rg["awaken"] == mod.AWAKEN_CONFIRMED and not fg.returns() and rg["evidence"]["source"] == "cwd-scan",
            str(rg["evidence"]))

        # H — 한글 NFD 로 들어온 cwd 도 NFC 슬러그 폴더와 맞는다
        cfg_h = os.path.join(root, "claude-h")
        nfc = unicodedata.normalize("NFC", "/tmp/내 드라이브/자비스/cso")
        since = time.time()
        write_session(cfg_h, mod.slug(nfc), nfc, [user_rec(nfc, time.time())])
        fh = FakeCys()
        rh = ensure(cfgdir=cfg_h, c=unicodedata.normalize("NFD", nfc), runner=fh)
        chk("H NFD cwd → NFC 슬러그 폴더 confirmed", rh["awaken"] == mod.AWAKEN_CONFIRMED and not fh.returns(),
            str(rh["evidence"]))

        # G2 — 윈도 모양 경로: 역슬래시·드라이브 대소문자가 달라도 cwd 대조 폴백이 맞춘다
        cfg_g2 = os.path.join(root, "claude-g2")
        wcwd = "C:\\Jarvis\\workers\\w1"
        since = time.time()
        write_session(cfg_g2, "-elsewhere", "c:/Jarvis/workers/w1", [user_rec("c:/Jarvis/workers/w1", time.time())])
        fg2 = FakeCys()
        rg2 = ensure(cfgdir=cfg_g2, c=wcwd, runner=fg2)
        chk("G2 윈도 경로 표기 차이 → cwd 대조 confirmed · Return 0",
            rg2["awaken"] == mod.AWAKEN_CONFIRMED and not fg2.returns(), str(rg2["evidence"]))

        # N — master 경로 nudge: 기록된 같은 pid 의 unconfirmed 좌석에만 Return
        cfg_n = os.path.join(root, "claude-n")
        prev_cfg = os.environ.get("CLAUDE_CONFIG_DIR")
        prev_acct = os.environ.get("CYS_ACCOUNT_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = cfg_n
        os.environ["CYS_ACCOUNT_DIR"] = cfg_n
        prev_runner, prev_sleep = mod.default_runner, mod._sleep
        try:
            mod._sleep = nosleep
            listing = "surface:9\trole=worker\tpid=42\texited=false\t9 · worker\t%s\n" % cwd

            class ListCys(FakeCys):
                def __call__(self, args):
                    if list(args) == ["list"]:
                        self.calls.append(["list"])
                        return 0, listing
                    return FakeCys.__call__(self, args)

            def nudge(fake, st):
                if st is None:
                    try:
                        os.unlink(mod.state_path("worker"))
                    except OSError:
                        pass
                else:
                    mod._write_state(st)
                mod.default_runner = lambda socket=None, timeout=12: fake
                import types
                return mod.cmd_nudge(types.SimpleNamespace(role="worker", socket=None, json=True))

            base = {"role": "worker", "surface": "surface:9", "pid": 42, "cwd": cwd,
                    "since": time.time(), "awaken": mod.AWAKEN_UNCONFIRMED}
            n1 = ListCys()
            rc1 = nudge(n1, dict(base))
            chk("N1 같은 pid·unconfirmed → nudge 가 Return 보냄", len(n1.returns()) == 3 and rc1 == 1,
                "rc=%s returns=%d" % (rc1, len(n1.returns())))
            n2 = ListCys()
            rc2 = nudge(n2, dict(base, pid=7))
            chk("N2 pid 가 갈렸으면 Return 0", not n2.returns() and rc2 == 1, "rc=%s %s" % (rc2, n2.returns()))
            n3 = ListCys()
            rc3 = nudge(n3, None)
            chk("N3 기록 없음 → exit 2 · Return 0 · 측정 없음", rc3 == 2 and not n3.returns(),
                "rc=%s calls=%s" % (rc3, n3.calls))
        finally:
            mod.default_runner, mod._sleep = prev_runner, prev_sleep
            for k, v in (("CLAUDE_CONFIG_DIR", prev_cfg), ("CYS_ACCOUNT_DIR", prev_acct)):
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        # I — 직접 Return 거부 → --queued 1회 전환
        cfg_i = os.path.join(root, "claude-i")
        since = time.time()
        fi = FakeCys(return_rc=1)
        ensure(cfgdir=cfg_i, runner=fi, waits=(3,))
        q = [c for c in fi.returns() if "--queued" in c]
        chk("I 직접 Return 거부 → queued 전환", len(q) == 1, str(fi.returns()))
    except Exception as e:  # 뮤턴트가 예외로 죽는 것도 적색이다
        if verbose:
            check("케이스 실행 예외 없음", False, "%s: %s" % (type(e).__name__, e))
        else:
            local.append("예외:%s" % type(e).__name__)
    finally:
        if prev_state is None:
            os.environ.pop("CYS_STATE_DIR", None)
        else:
            os.environ["CYS_STATE_DIR"] = prev_state
        shutil.rmtree(root, ignore_errors=True)
    return local


# ───────────────────────── 배선 핀(AST) ─────────────────────────
def _calls(node, name):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if nm == name:
                out.append(n)
    return out


def _func(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def _kw(call, key):
    for k in call.keywords:
        if k.arg == key:
            return k.value
    return None


def wiring_pins():
    bn_src = open(os.path.join(BIN, "javis_boot_node.py"), encoding="utf-8").read()
    bn = ast.parse(bn_src)
    main = _func(bn, "main")
    guarded = []
    for n in ast.walk(main):
        if isinstance(n, ast.If) and "launched_at is not None" in (ast.get_source_segment(bn_src, n.test) or ""):
            guarded.extend(_calls(n, "ensure_awake"))
    all_calls = _calls(main, "ensure_awake")
    check("W1 boot_node main: ensure_awake 는 launch 한 경우(if launched_at is not None) 안에서만",
          len(guarded) == 1 and len(all_calls) == 1, "guarded=%d all=%d" % (len(guarded), len(all_calls)))
    ok_assign = False
    for n in ast.walk(main):
        if isinstance(n, ast.If) and (ast.get_source_segment(bn_src, n.test) or "").strip() == "row is None":
            for s in n.body:
                if isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "launched_at"
                                                     for t in s.targets):
                    ok_assign = True
    check("W2 boot_node: launched_at 은 row is None(새로 launch) 분기에서만 시각을 받는다", ok_assign)
    if all_calls:
        v = _kw(all_calls[0], "may_return")
        check("W3 boot_node: may_return=True", isinstance(v, ast.Constant) and v.value is True)

    px_src = open(os.path.join(BIN, "javis_phoenix.py"), encoding="utf-8").read()
    px = ast.parse(px_src)
    holders = [f for f in ast.walk(px) if isinstance(f, ast.FunctionDef)
               and _calls(f, "spawn_fresh_production") and f.name != "spawn_fresh_production"]
    check("W4 phoenix: fresh 강등 함수가 fresh_awaken 을 부른다",
          bool(holders) and all(_calls(f, "fresh_awaken") for f in holders), str([f.name for f in holders]))
    fa = _func(px, "fresh_awaken")
    ea = _calls(fa, "ensure_awake") if fa else []
    check("W5 phoenix.fresh_awaken → javis_awaken.ensure_awake(may_return=True) 단일 구현",
          len(ea) == 1 and isinstance(_kw(ea[0], "may_return"), ast.Constant)
          and _kw(ea[0], "may_return").value is True)
    check("W6 사본 금지: 두 소비자에 jsonl 판독 사본이 없다",
          '"type") != "user"' not in bn_src and '"type") != "user"' not in px_src)


# ───────────────────────── 뮤턴트 ─────────────────────────
MUTANTS = [
    ("M1 시각 필터 제거(지난 세션을 각성으로)", "if t is None or t >= rec_floor:", "if True:"),
    ("M10 윈도 경로 정규화 제거", "if _norm(c) in norms:", "if c in variants:"),
    ("M11 nudge 같은 pid 검사 제거", 'and st.get("pid") == row["pid"]', ""),
    ("M12 nudge 기록 없음 가드 제거", 'if not st or st.get("since") is None:', "if False:"),
    ("M13 레코드 시각에 여유 재도입(재시작 틈)", "if t is None or t >= rec_floor:",
     "if t is None or t >= since - SINCE_SLACK_S:"),
    ("M2 이미 각성이어도 Return", 'if m["user"] == 0 and may_return:', "if may_return:"),
    ("M3 Return 미전송", "            send_return(runner, surface)\n", "            pass\n"),
    ("M4 master 보고 제거", 'if awaken == AWAKEN_UNCONFIRMED and report and role != "master":', "if False:"),
    ("M5 입양 좌석에도 Return", 'if m["user"] == 0 and may_return:', 'if m["user"] == 0:'),
    ("M6 파일 mtime 신선도 제거", 'if os.path.getmtime(p) >= floor and (p, "slug") not in found:',
     'if (p, "slug") not in found:'),
    ("M7 master 자기보고 허용", ' and report and role != "master":', " and report:"),
    ("M8 queued 전환 제거", "    if rc != 0:\n        # 타이핑", "    if False:\n        # 타이핑"),
    ("M9 cwd 대조 폴백 제거", "    if found:\n        return found\n", "    return found\n"),
]


def run_mutants():
    src = open(MODULE, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="awaken-mut-")
    try:
        for i, (name, old, new) in enumerate(MUTANTS):
            n = src.count(old)
            if n != 1:
                check("%s 적용(찾을 글 1건)" % name, False, "count=%d — NOT-APPLIED" % n)
                continue
            p = os.path.join(tmp, "javis_awaken_m%d.py" % i)
            with open(p, "w", encoding="utf-8") as f:
                f.write(src.replace(old, new))
            mut = load(p, "javis_awaken_m%d" % i)
            killed = run_cases(mut, verbose=False)
            check("%s KILLED" % name, bool(killed), ", ".join(killed[:3]) or "SURVIVED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    mod = load(MODULE, "javis_awaken")
    run_cases(mod)
    wiring_pins()
    run_mutants()
    print("\n=== %d/%d PASS (fails: %s) ===" % (_total[0] - len(fails), _total[0], fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
