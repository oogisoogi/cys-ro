#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TICKET=v116-num 설계 §9 T14 — `cys list` 소비자 호환.

cys 1.1.6 은 `cys list` 한 줄에 보이는 번호 칸 `no=50`(없으면 `no=-`)을 **4번 자리**(exited 뒤·제목 앞)에
넣는다. 이 출력을 탭으로 쪼개 읽는 팩 파서(저장소 9곳)가 **바뀌기 전과 같은 결과**를 돌려주는지 잰다
(특히 boot_node 의 좌석 찾기 · awaken 의 cwd — 틀어지면 중복 기동(4군 ③ 인접)·엉뚱한 폴더).
M25(새 칸을 맨 앞/맨 뒤에 둠)면 적색이 되는지도 같은 픽스처로 함께 잰다(음성 대조).
사용자본 javis_reconstruct_state.py 는 저장소 밖이라 그 파일의 --self-test 가 같은 사례를 진다.

실행: python3 cysjavis-pack/bin/tests/test_v116_num_cys_list_compat.py
"""
import importlib.util
import io
import os
import subprocess
import sys
import unittest
from unittest import mock

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLD = (
    "surface:1049\trole=worker-3\tpid=111\texited=false\t50 · Opus · worker3\t/Users/x/axdev/research\n"
    "surface:1050\trole=master\tpid=222\texited=false\t51 · master\t/Users/x/jarvis\n"
    "surface:1051\trole=cso\tpid=333\texited=true\t52 · cso\t/Users/x/jarvis/cso\n"
    "surface:1052\trole=-\tpid=444\texited=false\tsurface 1052\t/Users/x\n"
)


def with_no(text, where):
    """OLD 각 행에 no= 칸을 넣는다 — where: 4(설계 자리) · 0(맨 앞) · -1(맨 뒤)."""
    out = []
    for i, ln in enumerate(text.splitlines()):
        cols = ln.split("\t")
        cell = "no=-" if i == 3 else "no=%d" % (50 + i)
        if where == -1:
            cols.append(cell)
        else:
            cols.insert(where, cell)
        out.append("\t".join(cols))
    return "\n".join(out) + "\n"


NEW = with_no(OLD, 4)


def load(name, fname=None):
    path = os.path.join(BIN, fname or name + ".py")
    spec = importlib.util.spec_from_file_location(name + "_v116t14", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dept_live_roles(text):
    """cys-dept 의 dept_live_roles() 안 파이썬 조각을 그대로 떼어 실행한다(사본을 손으로 쓰지 않는다)."""
    with open(os.path.join(BIN, "cys-dept"), encoding="utf-8") as f:
        src = f.read()
    head = src.index("dept_live_roles(){")
    body = src[src.index("<<'PY'\n", head) + len("<<'PY'\n"): src.index("\nPY\n", head)]
    out = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(text)), mock.patch("sys.stdout", out):
        exec(compile(body, "cys-dept:dept_live_roles", "exec"), {})
    return out.getvalue()


def results(text):
    """9개 파서의 결과를 한 표로."""
    awaken = load("javis_awaken")
    boot_node = load("javis_boot_node")
    autopilot = load("javis_cycle_autopilot")
    formation = load("javis_formation")
    wakeup = load("javis_wakeup")
    bootstrap = load("javis_bootstrap")
    orchestra = load("javis_orchestra")
    runner = lambda args: (0, text)  # noqa: E731
    r = {
        "awaken.surface_row(surface)": awaken.surface_row(runner, surface="surface:1049"),
        "awaken.surface_row(role)": awaken.surface_row(runner, role="master"),
        "boot_node._parse_cys_list": boot_node._parse_cys_list(text),
        "cycle_autopilot.parse_cys_list": autopilot.parse_cys_list(text),
        "formation._roster_from_list_tsv": formation._roster_from_list_tsv(text),
        "wakeup.live_target_rows": wakeup.live_target_rows(text),
        "cys-dept.dept_live_roles": dept_live_roles(text),
    }
    with mock.patch.object(bootstrap, "_run", lambda *a, **k: (0, text)):
        r["bootstrap._live_role_names"] = bootstrap._live_role_names()
        r["bootstrap._live_node_count"] = bootstrap._live_node_count()
    fake = subprocess.CompletedProcess(["cys", "list"], 0, stdout=text.encode(), stderr=b"")
    with mock.patch.object(orchestra.shutil, "which", lambda _: "/usr/bin/cys"), \
            mock.patch.object(orchestra.subprocess, "run", lambda *a, **k: fake):
        r["orchestra._cys_list_masters"] = orchestra._cys_list_masters()
    return r


class CysListNoColumnCompat(unittest.TestCase):
    def test_new_column_at_slot4_gives_identical_results(self):
        old, new = results(OLD), results(NEW)
        for k in old:
            self.assertEqual(new[k], old[k], "%s: no= 칸(4번 자리)으로 결과가 바뀌었다" % k)
        # 결과가 비어 있어서 같은 것이 아님을 확인(측정력)
        self.assertEqual(old["awaken.surface_row(surface)"]["cwd"], "/Users/x/axdev/research")
        self.assertEqual(old["cycle_autopilot.parse_cys_list"][1050]["cwd"], "/Users/x/jarvis")
        self.assertTrue(any(r["surface_ref"] == "surface:1049" for r in old["boot_node._parse_cys_list"]))
        self.assertEqual(old["orchestra._cys_list_masters"], [1050])

    def test_m25_column_at_front_or_back_breaks_parsers(self):
        """음성 대조 — 맨 앞/맨 뒤에 두면 파서가 깨진다(이 시험이 공허하지 않다는 증거)."""
        old = results(OLD)
        for where in (0, -1):
            broken = results(with_no(OLD, where))
            self.assertTrue(any(broken[k] != old[k] for k in old),
                            "no= 칸을 %s 에 두어도 모든 파서가 같다 — 시험이 칸 자리를 재지 못한다" % where)


if __name__ == "__main__":
    unittest.main()
