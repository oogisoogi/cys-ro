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
import io
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

    # ★1R#1 BLOCKER — **판정의 정본**이 같은 프로파일을 쓰는가. 종전에는 check_verdicts 가
    #   required 를 제 손으로 다시 조립해 리뷰어 2기를 계속 요구했다(스폰 0 · 요구 2 = 영구 결손).
    #   effective_required_roles 만 재는 시험은 그 사실을 볼 수 없었다 — 그래서 정본을 직접 잰다.
    _ST = {"surfaces": [{"role": "cso", "exited": False, "awakened_at": 1.0},
                        {"role": "worker", "exited": False, "awakened_at": 1.0}]}
    v, _r = O.check_verdicts(_ST, detect=_detect(False), agents=AGENTS)
    check("ⓐ4a check_verdicts 필수 역할 == {cso, worker}(정본 파생 일치)",
          sorted(v) == ["cso", "worker"], repr(sorted(v)))
    check("ⓐ4b 두 좌석 생존 → 전원 충족", all(x["satisfied"] for x in v.values()),
          repr({k: x["satisfied"] for k, x in v.items()}))
    has, why = O._shared_verdict_deficit(_ST, detect=_detect(False), agents=AGENTS)
    check("ⓐ4c 참가자 기계 결손 0(부트 ④ 재시도 고리 차단)", has is False, why)
    # 네이티브 기계에서는 같은 status 가 여전히 결손>0 이어야 한다(완화 아님의 증거).
    has_n, _ = O._shared_verdict_deficit(_ST, detect=_detect(True), agents=AGENTS)
    check("ⓐ4d 네이티브 기계에서는 리뷰어 부재가 여전히 결손", has_n is True)
    # ACK 축 — 참가자 프로파일에서는 리뷰어 행 자체가 없어야 한다(없는 좌석의 pending 금지).
    ack = O.ack_axis(_ST, v, _r)
    check("ⓐ4e 참가자 ACK 축에 리뷰어 행 0",
          not (ack.get("pending") or ack.get("unmeasured")), repr(ack))

    # cmd_check 종단 — 데몬 왕복만 스텁하고 **실제 exit code** 를 잰다.
    import argparse
    _saved_status, _saved_roster = O.cys_status, O.reviewer_roster
    _saved_addr = O.addr_registry_roles
    O.cys_status = lambda: _ST
    # 주소 레지스트리는 `cys list` RPC(별도 자료원)라 밀폐 스텁 대상이다 — 이 검체가 재는 것은
    # **프로파일 파생**이지 주소성 축이 아니다(그 축은 자기 검체를 따로 갖고 있다).
    O.addr_registry_roles = lambda: {"cso", "worker"}
    O.reviewer_roster = lambda detect=None, agents=None: [
        {"role": "reviewer-claude-1", "agent": "claude", "native": False,
         "substituted_for": "gemini", "reason": "밀폐"},
        {"role": "reviewer-claude-2", "agent": "claude", "native": False,
         "substituted_for": "codex", "reason": "밀폐"}]
    try:
        rc = O.cmd_check(argparse.Namespace())
    finally:
        O.cys_status, O.reviewer_roster = _saved_status, _saved_roster
        O.addr_registry_roles = _saved_addr
    check("ⓐ4f 참가자 기계 `orchestra check` exit 0(READY)", rc == 0, "rc=%r" % rc)

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

    # ★1R#3 — 프로파일 사실은 **orchestra 해소**에서 온다(formation 의 command -v 아님).
    #   재현 형상: agents.json 의 agy 는 출하 기본이 절대경로(~/.local/bin/agy)라 PATH 에 없다.
    #   그 기계에서 orchestra 는 혼합(네이티브 1 + 대체 1)인데 formation 은 probe 로 참가자라
    #   판정해 **리뷰어를 편성에서 통째로 지웠다**.
    check("ⓐ18 주입된 네이티브 사실이 probe 휴리스틱을 이긴다",
          F.participant_profile({"claude"}, native_reviewer=True) is False)
    check("ⓐ19 그 기계의 편성 역할 = 표준 4역할 + master(혼합 편성 유지)",
          F.profile_required_roles({"claude"}, native_reviewer=True) == F.REQUIRED_ROLES,
          repr(F.profile_required_roles({"claude"}, native_reviewer=True)))
    check("ⓐ20 반대 방향도 주입이 이긴다(agy 설치돼 있으나 네이티브 부재 판정)",
          F.participant_profile({"claude", "agy"}, native_reviewer=False) is True)
    # 해소기 자체 — orchestra 로스터의 native 플래그를 그대로 돌려주는가(폴백 None 포함).
    import javis_orchestra as _O
    _sv = _O.reviewer_roster
    try:
        _O.reviewer_roster = lambda detect=None, agents=None: [
            {"role": "reviewer-gemini", "agent": "gemini", "native": True,
             "substituted_for": None, "reason": "절대경로 실재"},
            {"role": "reviewer-claude-2", "agent": "claude", "native": False,
             "substituted_for": "codex", "reason": "부재"}]
        check("ⓐ21 native_reviewer_present = orchestra 로스터 파생(절대경로 agy → True)",
              F.native_reviewer_present() is True)
        _O.reviewer_roster = lambda detect=None, agents=None: []
        check("ⓐ22 로스터 비었으면 None(판정 불가 — 호출부가 휴리스틱으로 강등)",
              F.native_reviewer_present() is None)
    finally:
        _O.reviewer_roster = _sv

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

    # ★1R#2 — **정상 복원 경로**(bare `cys restore`)가 저장된 홈 cwd 를 그대로 되살리던 자리.
    HOME = os.path.expanduser("~")
    check("ⓑ4a home_like: 홈·빈 값 = '말해 주지 않은 값'",
          P.home_like(HOME) is True and P.home_like("") is True
          and P.home_like("/proj/wt") is False)
    ENT_HOME = {"master": {"cwd": "/jarvis"}, "cso": {"cwd": HOME}, "worker": {"cwd": ""}}
    check("ⓑ4b 자식 전원 홈 → restore --cwd = master 폴더",
          P.restore_cwd_override(ENT_HOME, ["cso", "worker"], "/jarvis") == "/jarvis",
          repr(P.restore_cwd_override(ENT_HOME, ["cso", "worker"], "/jarvis")))
    ENT_MIX = dict(ENT_HOME, worker={"cwd": "/proj/wt"})
    check("ⓑ4c 한 명이라도 진짜 작업 폴더면 **아무것도 덮지 않는다**(함대 이주 금지)",
          P.restore_cwd_override(ENT_MIX, ["cso", "worker"], "/jarvis") is None)
    check("ⓑ4d master cwd 미해소면 override 없음(종전 동작)",
          P.restore_cwd_override(ENT_HOME, ["cso"], None) is None)
    check("ⓑ4e 대상이 master 뿐이면 override 없음(자기 기준값을 자기에게 덮지 않는다)",
          P.restore_cwd_override(ENT_HOME, ["master"], "/jarvis") is None)
    # master 부재 케이스 — 라이브에 없으면 **영속 토폴로지**의 master 엔트리가 기준이 된다.
    _sv_status = P._status_json
    try:
        P._status_json = lambda socket: {"surfaces": []}
        check("ⓑ4f 라이브 master 부재 → 영속 토폴로지 master cwd 로 폴백",
              P.master_seat_cwd("/s.sock", {"master": {"cwd": "/jarvis"}}) == "/jarvis")
        check("ⓑ4g 영속 master 도 홈이면 기준으로 쓰지 않는다(상속해도 관문 그대로)",
              P.master_seat_cwd("/s.sock", {"master": {"cwd": HOME}}) is None)
        check("ⓑ4h master 엔트리 자체가 없으면 None",
              P.master_seat_cwd("/s.sock", {}) is None)
        P._status_json = lambda socket: {"surfaces": [
            {"role": "master", "exited": False, "cwd": "/live"}]}
        check("ⓑ4i 라이브 master 가 1순위(영속보다 우선)",
              P.master_seat_cwd("/s.sock", {"master": {"cwd": "/old"}}) == "/live")
    finally:
        P._status_json = _sv_status

    # 정상 복원이 실제로 --cwd 를 실어 보내는가.
    seen_r = []

    class _RR(object):
        returncode = 0
        stdout = ""
        stderr = ""

    _sv_cys = P.cys
    try:
        P.cys = lambda *a, **kw: (seen_r.append(list(a)) or _RR())
        P.spawn_production("/s.sock", ["cso"], cwd="/jarvis")
        check("ⓑ4j 정상 복원 → cys restore --cwd 전달",
              seen_r and "--cwd" in seen_r[0]
              and seen_r[0][seen_r[0].index("--cwd") + 1] == "/jarvis", repr(seen_r))
        seen_r[:] = []
        P.spawn_production("/s.sock", ["cso"], cwd=None)
        check("ⓑ4k override 없으면 --cwd 미전달(종전 동작 보존)",
              seen_r and "--cwd" not in seen_r[0], repr(seen_r))
    finally:
        P.cys = _sv_cys

    # fresh 강등의 **선택 논리** — 프로덕션 함수를 직접 잰다(호출부 표현식 복제 금지:
    # 1R 이 지적한 "시험이 이미 고른 값만 넣는다"의 재발 방지).
    check("ⓑ4l fresh: 저장 cwd 가 홈 → master 폴더가 이긴다",
          P.fresh_child_cwd(HOME, "/jarvis") == "/jarvis"
          and P.fresh_child_cwd("", "/jarvis") == "/jarvis"
          and P.fresh_child_cwd(None, "/jarvis") == "/jarvis")
    check("ⓑ4m fresh: 진짜 작업 폴더는 그대로 둔다",
          P.fresh_child_cwd("/proj/wt", "/jarvis") == "/proj/wt")
    check("ⓑ4n fresh: master 기준값도 없으면 None(홈 = 종전 동작)",
          P.fresh_child_cwd(HOME, None) is None)

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


# ── ⓒ P3: Windows 자식 수명 결박(Job Object) ────────────────────────────────────────────
# ★1R#4(codex): **문자열 계수 시험은 폐기했다.** 소스에 `assign_child` 가 몇 번 나오는지 세는
#   시험은 죽은 코드·편입 실패·스폰↔편입 경쟁 창을 전부 통과시킨다 — 결박은 커널에 물어야
#   안다. 실측 축은 Rust 로 이사했다: `src/bin/cysd/state.rs::winjob_binding_tests`
#   (IsProcessInJob 으로 실제 자식의 결박을 잰다 · windows-health 레인의
#   `cargo test --bin cysd` 에서 **실기 Windows** 에서 돈다).
#   여기 남기는 유일한 축은 "그 실측 배터리가 조용히 사라지지 않았는가" 하나다.
REPO = os.path.normpath(os.path.join(BIN, "..", ".."))


def t_winjob():
    rel = "src/bin/cysd/state.rs"
    try:
        src = io.open(os.path.join(REPO, rel), encoding="utf-8", errors="replace").read()
    except OSError as e:
        check("ⓒ %s 판독" % rel, False, str(e))
        return
    check("ⓒ Job 결박 **실측** 배터리 상주(문자열 계수 아님)",
          "mod winjob_binding_tests" in src and "IsProcessInJob" in src,
          "실측 축이 사라졌다 — 결박은 소스 grep 으로 증명되지 않는다")
    check("ⓒ 데몬 자기 편입(상속) 진입점 상주",
          "pub fn bind_self()" in src and "fn self_bound()" in src,
          "bind_self/self_bound 부재 — 스폰 후 편입의 경쟁 창이 되살아난다")
    check("ⓒ 편입 실패가 반환형으로 드러난다(조용한 무시 금지)",
          "pub fn assign_child(pid: u32) -> Result<(), String>" in src,
          "assign_child 가 실패를 삼키는 형태로 되돌아갔다")


# ── ⓕ 원작자 표기(박사님 지시 2026-09-10 · 원작자 통화 허락 조건 = 최초 개발자 명시) ──────
# ★1R#6(codex): 종전 축은 「파일 어디든 idoforgod」였다. release.yml 에는 무관한 upstream URL·
#   주석이, pack-release.yml 에는 시험 설명 주석이 이미 그 문자열을 갖고 있어 **실제 표기 블록을
#   지워도 초록**이었다. 이제 자리마다 그 블록을 **파싱해서** 본다 — 그리고 각 축은 그 블록만
#   지운 **음성 픽스처**로 자기 실효를 증명한다(안 잡는 게이트는 게이트가 아니다).
ATTRIB_MUST = ("CYSJavis", "idoforgod", "원작자의 허락을 받아", "oogisoogi",
               "https://github.com/idoforgod/cys-terminal")


def _block_scalar(text, key):
    """YAML 블록 스칼라(`<key>: |`) 본문을 들여쓰기 기준으로 떼어낸다(순수 · yaml 의존 0)."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        st = ln.strip()
        if st.startswith(key + ":") and st.endswith("|"):
            indent = len(ln) - len(ln.lstrip())
            body = []
            for nxt in lines[i + 1:]:
                if not nxt.strip():
                    body.append("")
                    continue
                if (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                body.append(nxt)
            return "\n".join(body)
    return None


def _heredoc(text, marker):
    """셸 heredoc(`<<marker` … `marker`) 본문(순수). 여러 개면 첫 번째."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ("<<" + marker) in ln or ("<<'" + marker + "'") in ln:
            body = []
            for nxt in lines[i + 1:]:
                if nxt.strip() == marker:
                    return "\n".join(body)
                body.append(nxt)
    return None


def _md_section(text, heading):
    """마크다운 `## <heading>` 절 본문(다음 `## ` 전까지 · 순수)."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == heading:
            body = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("## "):
                    break
                body.append(nxt)
            return "\n".join(body)
    return None


def _ws_credit(html):
    """`#ws-credit` 요소의 여는 태그 + 내용(순수). 없으면 None."""
    for ln in html.splitlines():
        if 'id="ws-credit"' in ln:
            return ln
    return None


# (파일, 추출기, 자리 이름, 그 블록만 지우는 음성 변이)
def _kill_block_scalar(text):
    b = _block_scalar(text, "releaseBody")
    return text.replace(b, "          (지움)") if b else text


def _kill_heredoc(text):
    b = _heredoc(text, "NOTES")
    return text.replace(b, "          (지움)") if b else text


def _kill_md(heading):
    def f(text):
        b = _md_section(text, heading)
        return text.replace(b, "\n(지움)\n") if b else text
    return f


def _kill_credit(text):
    ln = _ws_credit(text)
    return text.replace(ln, "      <!-- 지움 -->") if ln else text


ATTRIB_SITES = [
    (".github/workflows/release.yml", lambda t: _block_scalar(t, "releaseBody"),
     "본체 릴리스 본문(releaseBody 블록 스칼라)", _kill_block_scalar),
    (".github/workflows/pack-release.yml", lambda t: _heredoc(t, "NOTES"),
     "팩-only 릴리스 본문(release-notes heredoc)", _kill_heredoc),
    ("README.md", lambda t: _md_section(t, "## 원작자"),
     "포크 README 「원작자」 절", _kill_md("## 원작자")),
    ("README.en.md", lambda t: _md_section(t, "## Original author"),
     "영문 README 「Original author」 절", _kill_md("## Original author")),
    ("ui/index.html", _ws_credit, "앱 안 표기(#ws-credit 요소)", _kill_credit),
]


def _attrib_ok(block, site):
    """그 자리의 표기가 성립하는가(순수). ui 는 요소 한 줄이라 문안이 축약형이다."""
    if not block:
        return False
    if site == "ui/index.html":
        return ("idoforgod" in block and "CYSJavis" in block and "oogisoogi" in block
                and " hidden" not in block)
    return all(w in block for w in ATTRIB_MUST)


def t_attribution():
    for rel, extract, what, kill in ATTRIB_SITES:
        try:
            src = io.open(os.path.join(REPO, rel), encoding="utf-8", errors="replace").read()
        except OSError as e:
            check("ⓕ %s 판독" % rel, False, str(e))
            continue
        block = extract(src)
        check("ⓕ %s — 표기 블록 추출(%s)" % (rel, what), bool(block),
              "추출 실패 = 자리가 사라졌거나 형태가 바뀌었다(측정 불능은 통과가 아니다)")
        check("ⓕ %s — 블록 안에 문안 전문" % rel, _attrib_ok(block, rel),
              (block or "")[:160])
        # ★음성 픽스처: **그 블록만** 지우면 반드시 적색이어야 한다(종전 축은 여기서 초록이었다).
        check("ⓕ %s — 블록 제거 시 적색(게이트 실효 증명)" % rel,
              not _attrib_ok(extract(kill(src)), rel),
              "블록을 지웠는데도 통과 — 파일 어딘가의 무관한 idoforgod 를 세고 있다")


def main():
    t_attribution()
    t_orchestra()
    t_formation()
    t_phoenix()
    t_winjob()
    print("\n=== %d/%d PASS (fails: %s) ===" % (_total[0] - len(fails), _total[0], fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
