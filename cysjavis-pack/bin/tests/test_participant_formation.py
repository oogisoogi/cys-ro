#!/usr/bin/env python3
"""test_participant_formation.py — 참가자 프로파일 + 자식 좌석 cwd 상속 회귀 핀
(TICKET=pack-participant-formation · 2026-09-10).

봉인 대상(참가자 기계 실측 3건 · 박사님 노트북 · 우리 빌드 0.14.33 · 설치기 v0.3.7):
  ⓐ P1 — agy·codex 가 **없는** 기계에서 `boot-reviewers` 가 Claude 대체 리뷰어 2기를 매 부팅
     세웠다(리뷰 의뢰 0인데 「86% weekly limit」 · 사용자가 닫아도 결손 판정이 되살림).
     계약: 네이티브 리뷰어 CLI 전무 = **참가자 프로파일** → 리뷰어 스폰 0 · 의무 역할에서도 제외.
  ⓐ′ 반대 방향(완화 아님의 증거) — 네이티브가 하나라도 있으면 **현행 편성이 그대로** 선다.
  ⓑ P2 — 편성·phoenix 가 자식 좌석을 홈 cwd 로 띄워 폴더 신뢰 관문(기본 선택 = No, exit)에
     갇혔다. 계약: 자식 cwd = master 좌석의 **생성 cwd**(설치기가 신뢰를 심어 둔 JarvisHome).

전부 순수/스텁 — 라이브 데몬·실 스폰 무접촉. 실행: python3 test_participant_formation.py
"""
import importlib.util
import os
import sys

SELF = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.normpath(os.path.join(SELF, ".."))
# 밀폐: 라이브 팩(~/.cys/pack) 상속 금지 — 리포 팩만 읽는다(test_formation.py 와 동일 규약).
os.environ["CYS_PACK_DIR"] = os.path.normpath(os.path.join(BIN, ".."))
os.environ.pop("CYS_FORMATION_EXTERNAL_ROLES", None)

fails = []
_total = [0]


def check(name, cond, detail=""):
    _total[0] += 1
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))
    if not cond:
        fails.append(name)


def _load(mod):
    path = os.path.join(BIN, mod + ".py")
    spec = importlib.util.spec_from_file_location(mod, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod] = m
    spec.loader.exec_module(m)
    return m


# 밀폐 감지기: 실디스크의 agy/codex 실재와 무관하게 프로파일을 **구성**해서 잰다.
def _detect(native):
    def d(agent, agents=None):
        return bool(native), "밀폐 주입(native=%r)" % bool(native)
    return d


AGENTS = {"gemini": {"cmd": "/x/agy"}, "codex": {"cmd": "/x/codex"}, "claude": {"cmd": "claude"}}


def t_orchestra():
    O = _load("javis_orchestra")

    # ⓐ 판정 — 네이티브 전무 = 참가자 · 하나라도 있으면 아니다.
    check("ⓐ1 네이티브 전무 → 참가자 프로파일",
          O.participant_profile(detect=_detect(False), agents=AGENTS) is True)
    check("ⓐ2 네이티브 실재 → 참가자 아님(우리 맥 현행 보존)",
          O.participant_profile(detect=_detect(True), agents=AGENTS) is False)
    mix = lambda a, ag=None: (a == "gemini", "mix")  # noqa: E731
    check("ⓐ3 네이티브 1종만 실재 → 참가자 아님(혼합 = 현행 대체 폴백 유지)",
          O.participant_profile(detect=mix, agents=AGENTS) is False)

    # ⓐ 의무 역할 — 참가자에서 리뷰어가 required 밖(결손 판정이 되살리지 못하는 근거).
    check("ⓐ4 참가자 유효 의무역할 = cso·worker",
          O.effective_required_roles(detect=_detect(False), agents=AGENTS) == ["cso", "worker"],
          repr(O.effective_required_roles(detect=_detect(False), agents=AGENTS)))
    check("ⓐ5 네이티브 실재 유효 의무역할 = 표준 4역할(현행 보존)",
          O.effective_required_roles(detect=_detect(True), agents=AGENTS) == O.REQUIRED_ROLES,
          repr(O.effective_required_roles(detect=_detect(True), agents=AGENTS)))

    # ⓐ 실스폰 — boot-reviewers 가 참가자 기계에서 **한 좌석도** 띄우지 않는다.
    class _Args(object):
        plan = False

    booted = []
    O._boot_one_node = lambda role, agent, timeout=None: (
        booted.append((role, agent)) or (True, 0, O.EXIT_CLASS_OK, "stub"))

    O.reviewer_roster = lambda detect=None, agents=None: [
        {"role": "reviewer-claude-1", "agent": "claude", "native": False,
         "substituted_for": "gemini", "reason": "밀폐"},
        {"role": "reviewer-claude-2", "agent": "claude", "native": False,
         "substituted_for": "codex", "reason": "밀폐"}]
    rc = O.cmd_boot_reviewers(_Args())
    check("ⓐ6 참가자 프로파일 boot-reviewers → 스폰 0", booted == [], repr(booted))
    check("ⓐ7 참가자 프로파일 boot-reviewers → exit 0(Degrade 아님·정상 상태)", rc == 0, "rc=%r" % rc)

    # ⓐ′ 네이티브 로스터에서는 종전대로 2기를 띄운다(기능 제거 아님).
    booted[:] = []
    O.reviewer_roster = lambda detect=None, agents=None: [
        {"role": "reviewer-gemini", "agent": "gemini", "native": True,
         "substituted_for": None, "reason": "밀폐"},
        {"role": "reviewer-codex", "agent": "codex", "native": True,
         "substituted_for": None, "reason": "밀폐"}]
    rc = O.cmd_boot_reviewers(_Args())
    check("ⓐ8 네이티브 로스터 boot-reviewers → 2기 스폰 유지",
          booted == [("reviewer-gemini", "gemini"), ("reviewer-codex", "codex")], repr(booted))
    check("ⓐ9 네이티브 2기 각성 → exit 0", rc == 0, "rc=%r" % rc)


def t_formation():
    F = _load("javis_formation")

    check("ⓐ10 formation 참가자 판정(claude 단독)", F.participant_profile({"claude"}) is True)
    check("ⓐ11 formation 네이티브 실재 → 참가자 아님",
          F.participant_profile({"claude", "agy"}) is False)
    check("ⓐ12 CLI 전무는 판정 유보(온보딩 pending-cli 보존)",
          F.participant_profile(set()) is False)
    check("ⓐ13 참가자 3기 = complete(구: partial:agy,codex 영구 고정)",
          F.classify(installed={"claude"}, live={"master", "cso", "worker"},
                     resource_ok=True) == "complete",
          F.classify(installed={"claude"}, live={"master", "cso", "worker"}, resource_ok=True))
    check("ⓐ14 참가자여도 결원은 complete 아님(완화 아님)",
          F.classify(installed={"claude"}, live={"master", "cso"},
                     resource_ok=True) != "complete")
    check("ⓐ15 네이티브 반쪽 설치는 여전히 complete 아님(Sim S2-5 보존)",
          F.classify(installed={"claude", "agy"}, live=set(F.REQUIRED_ROLES),
                     resource_ok=True) != "complete")
    check("ⓐ16 참가자 편성 대상 역할 = master·cso·worker",
          F.profile_required_roles({"claude"}) == ("master", "cso", "worker"),
          repr(F.profile_required_roles({"claude"})))
    check("ⓐ17 complete 피드 본문이 프로파일을 정직하게 말한다",
          "reviewer-gemini" not in F._complete_feed_body({"claude"})
          and "reviewer-gemini" in F._complete_feed_body({"claude", "agy", "codex"}),
          F._complete_feed_body({"claude"}))

    # ⓑ 자식 cwd 상속 — 순수 파서(생성 cwd 우선 · live_cwd 아님 · exited 무시).
    obj = {"surfaces": [
        {"role": "master", "exited": True, "cwd": "/dead"},
        {"role": "worker", "exited": False, "cwd": "/w"},
        {"role": "master", "exited": False, "cwd": "/jarvis", "live_cwd": "/tmp/elsewhere"}]}
    check("ⓑ1 formation: master 좌석의 생성 cwd 선택(live_cwd 아님)",
          F._master_seat_cwd_from_status(obj) == "/jarvis",
          repr(F._master_seat_cwd_from_status(obj)))
    check("ⓑ2 formation: master 부재·빈 cwd → None(홈 폴백 = 종전 동작)",
          F._master_seat_cwd_from_status({"surfaces": [{"role": "cso", "exited": False,
                                                        "cwd": "/c"}]}) is None
          and F._master_seat_cwd_from_status(
              {"surfaces": [{"role": "master", "exited": False, "cwd": ""}]}) is None)


def t_phoenix():
    P = _load("javis_phoenix")
    obj = {"surfaces": [
        {"role": "master", "exited": True, "cwd": "/dead"},
        {"role": "master", "exited": False, "cwd": "/jarvis", "live_cwd": "/tmp/elsewhere"}]}
    check("ⓑ3 phoenix: master 좌석의 생성 cwd 선택",
          P.master_seat_cwd_from_status(obj) == "/jarvis",
          repr(P.master_seat_cwd_from_status(obj)))
    check("ⓑ4 phoenix: master 부재 → None",
          P.master_seat_cwd_from_status({"surfaces": []}) is None)

    # fresh 강등이 --cwd 를 실제로 실어 보내는가(관문 회피의 유일한 수단).
    seen = []

    class _R(object):
        returncode = 0
        stdout = "surface:9"
        stderr = ""

    P.cys = lambda *a, **kw: (seen.append(list(a)) or _R())
    P.spawn_fresh_production("/s.sock", "cso", "claude", cwd="/jarvis")
    check("ⓑ5 phoenix fresh 강등 → launch-agent --cwd 전달",
          seen and "--cwd" in seen[0] and seen[0][seen[0].index("--cwd") + 1] == "/jarvis",
          repr(seen))
    seen[:] = []
    P.spawn_fresh_production("/s.sock", "cso", "claude", cwd=None)
    check("ⓑ6 cwd 미해소면 --cwd 자체를 넣지 않는다(종전 동작 보존)",
          seen and "--cwd" not in seen[0], repr(seen))


def main():
    t_orchestra()
    t_formation()
    t_phoenix()
    print("\n=== %d/%d PASS (fails: %s) ===" % (_total[0] - len(fails), _total[0], fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
