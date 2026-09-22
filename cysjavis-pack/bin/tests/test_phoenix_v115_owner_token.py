#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phoenix_v115_owner_token.py — phoenix 의 각성 핑(reinject)이 데몬 operator.token 을 싣는다 (TICKET=v115-restore A1).

실측 계기(904 VM ↻ · 4/4): 부서 cysd 가 띄운 phoenix 는 pane 무귀속이라 그 자식 `cys reinject --check --role worker`
가 `external` 로 판정돼 부서 ACL `{"from":"external","to":"worker*","allow":false}` 에 막혔다
(`acl denied: external → worker`). 수리 = 앱 사이드카(수리 15)와 같게 CYS_OWNER_TOKEN 전달.

  U1 cys(owner=True) → 자식 env 에 대상 데몬 상태 디렉터리의 operator.token
  U2 cys(owner=False·기본) → 자식 env 에 CYS_OWNER_TOKEN 없음(조회 동사엔 안 싣는다 · 부모 env 누출도 없음)
  U3 토큰 파일 부재 → 싣지 않음(빈 값 금지)
  S1 stage_reinject · S2 stage_g2_ack → 둘 다 토큰을 싣는다(실제 주입 경로)
  M 뮤턴트 2(변이 적용 선-assert 동반): M1 env 대입 제거 · M2 stage_reinject 의 owner=True 제거 → 적색이어야 한다

실행: python3 cysjavis-pack/bin/tests/test_phoenix_v115_owner_token.py → 종료 토큰 PHOENIX-V115-OWNER-TOKEN-OK
"""
import importlib.util
import os
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.normpath(os.path.join(HERE, "..", "javis_phoenix.py"))
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


def run_axes(src, tmp, tag, sink=None):
    """축 전부를 한 모듈 사본에 대해 돈다. sink 가 주어지면 실패 이름만 모은다(뮤턴트 판정용)."""
    work = tempfile.mkdtemp(prefix="ph-" + tag + "-", dir=tmp)
    # 모듈 사본은 형제 모듈(javis_state_snapshot 등)을 bin 에서 찾으므로 bin 을 경로에 둔다.
    mod = load_src(src, "ph_" + tag, work)
    sd = os.path.join(work, "state")
    os.makedirs(sd)
    sock = os.path.join(sd, "cys.sock")
    out = os.path.join(work, "env.out")
    fake = os.path.join(work, "fakecys")
    with open(fake, "w") as f:
        f.write('#!/bin/sh\nprintf "%s" "${CYS_OWNER_TOKEN-<unset>}" > "' + out + '"\n')
    os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
    mod.CYS = fake
    os.environ.pop("CYS_OWNER_TOKEN", None)

    def got():
        try:
            with open(out) as f:
                return f.read()
        finally:
            if os.path.exists(out):
                os.remove(out)

    # U3 먼저(토큰 파일 부재)
    mod.cys("reinject", "--check", socket=sock, owner=True)
    check("U3 토큰 파일 부재 → 미부착", got() == "<unset>", sink=sink)
    with open(os.path.join(sd, "operator.token"), "w") as f:
        f.write("tok-abc123\n")
    mod.cys("reinject", "--check", socket=sock, owner=True)
    v = got()
    check("U1 owner=True → 대상 데몬 operator.token 부착", v == "tok-abc123", v, sink=sink)
    os.environ["CYS_OWNER_TOKEN"] = "parent-leak"
    try:
        mod.cys("list", socket=sock)
        v = got()
    finally:
        os.environ.pop("CYS_OWNER_TOKEN", None)
    check("U2 owner 기본 → 토큰 안 싣는다(부모 값 그대로 = 추가 부착 없음)", v == "parent-leak", v, sink=sink)
    mod.cys("list", socket=sock)
    check("U2b owner 기본 · 부모 env 없음 → 미부착", got() == "<unset>", sink=sink)
    mod._surface_agent_present = lambda s, sf: True
    mod.stage_reinject(sock, "worker", "surface:7", False)
    v = got()
    check("S1 stage_reinject → 토큰 부착", v == "tok-abc123", v, sink=sink)
    mod.stage_g2_ack(sock, "worker", "surface:7", False)
    v = got()
    check("S2 stage_g2_ack → 토큰 부착", v == "tok-abc123", v, sink=sink)


def main():
    sys.path.insert(0, os.path.dirname(PH))
    with open(PH, encoding="utf-8") as f:
        src = f.read()
    tmp = tempfile.mkdtemp(prefix="ph-v115-")
    run_axes(src, tmp, "base")

    mutants = [
        ("M1 env 대입 제거", '            env["CYS_OWNER_TOKEN"] = tok\n', '            pass\n'),
        ("M2 stage_reinject owner=True 제거",
         '            socket=socket, timeout=12, owner=True)', '            socket=socket, timeout=12)'),
    ]
    for name, a, b in mutants:
        n = src.count(a)
        check(name + " 변이 적용 선-assert(정확 1곳)", n == 1, "count=%d" % n)
        if n != 1:
            continue
        sink = []
        run_axes(src.replace(a, b), tmp, "m%d" % mutants.index((name, a, b)), sink=sink)
        check(name + " → KILLED", bool(sink), "적색 축=%s" % sink)

    if fails:
        print("FAIL 합계 %d: %s" % (len(fails), fails))
        sys.exit(1)
    print("PHOENIX-V115-OWNER-TOKEN-OK")


if __name__ == "__main__":
    main()
