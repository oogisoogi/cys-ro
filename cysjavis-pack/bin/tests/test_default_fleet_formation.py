#!/usr/bin/env python3
"""test_default_fleet_formation.py — 참가자 프로파일 + 자식 좌석 cwd 상속 회귀 핀
(TICKET=pack-participant-formation · 2026-09-10).

봉인 대상(참가자 기계 실측 3건 · 박사님 노트북 · 우리 빌드 0.14.33 · 설치기 v0.3.7):
  ⓐ P1 — agy·codex 가 **없는** 기계에서 `boot-reviewers` 가 Claude 대체 리뷰어 2기를 매 부팅
     세웠다(리뷰 의뢰 0인데 「86% weekly limit」 · 사용자가 닫아도 결손 판정이 되살림).
     계약: 네이티브 리뷰어 CLI 전무 = **참가자 프로파일** → 리뷰어 스폰 0 · 의무 역할에서도 제외.
  ⓐ′ 반대 방향(완화 아님의 증거) — 네이티브가 하나라도 있으면 **현행 편성이 그대로** 선다.
  ⓑ P2 — 편성·phoenix 가 자식 좌석을 홈 cwd 로 띄워 폴더 신뢰 관문(기본 선택 = No, exit)에
     갇혔다. 계약: 자식 cwd = master 좌석의 **생성 cwd**(설치기가 신뢰를 심어 둔 JarvisHome).

전부 순수/스텁 — 라이브 데몬·실 스폰 무접촉. 실행: python3 test_default_fleet_formation.py
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

    # ⓐ 기본 함대 — 의무 역할은 **감지와 무관하게** cso·worker. 감지 코드가 판정에 없으면
    #   파일 간 판정 불일치(1R HIGH ③)도 구조적으로 불가능하다.
    mix = lambda a, ag=None: (a == "gemini", "mix")   # noqa: E731
    for name, d in (("미감지", _detect(False)), ("전부 감지", _detect(True)), ("혼합", mix)):
        got = O.effective_required_roles(detect=d, agents=AGENTS)
        check("ⓐ1 의무 역할이 감지(%s)와 무관하게 cso·worker" % name,
              got == ["cso", "worker"], repr(got))
    check("ⓐ2 REQUIRED_ROLES 에 리뷰어 없음(상시 점유 부활 차단)",
          not any(r.startswith("reviewer") for r in O.REQUIRED_ROLES), repr(O.REQUIRED_ROLES))
    check("ⓐ3 BOOT_PLAN(=cys boot 대상)에도 리뷰어 없음",
          [r for r, _a, _p in O.BOOT_PLAN] == ["cso", "worker"],
          repr([r for r, _a, _p in O.BOOT_PLAN]))
    check("ⓐ3b 리뷰어 슬롯 표는 **살아 있다**(열 때 누가 채우는가 — 능력 제거 아님)",
          [s[0] for s in O.REVIEWER_SLOTS] == ["reviewer-gemini", "reviewer-codex"],
          repr(O.REVIEWER_SLOTS))

    # ★1R#1 BLOCKER — **판정의 정본**이 같은 목록을 쓰는가. 종전에는 check_verdicts 가 required 를
    #   제 손으로 다시 조립해 리뷰어 2기를 계속 요구했다(스폰 0 · 요구 2 = 영구 결손).
    _ST = {"surfaces": [{"role": "cso", "exited": False, "awakened_at": 1.0},
                        {"role": "worker", "exited": False, "awakened_at": 1.0}]}
    for name, d in (("미감지", _detect(False)), ("전부 감지", _detect(True))):
        v, _r = O.check_verdicts(_ST, detect=d, agents=AGENTS)
        check("ⓐ4a check_verdicts 필수 역할 == {cso, worker} (%s)" % name,
              sorted(v) == ["cso", "worker"], repr(sorted(v)))
        check("ⓐ4b 두 좌석 생존 → 전원 충족 (%s)" % name,
              all(x["satisfied"] for x in v.values()), repr(v))
        has, why = O._shared_verdict_deficit(_ST, detect=d, agents=AGENTS)
        check("ⓐ4c 기본 함대 결손 0 — 부트 ④ 재시도 고리 차단 (%s)" % name, has is False, why)
    # 완화 아님: 의무 역할이 빠지면 여전히 결손이다.
    _ST1 = {"surfaces": [{"role": "cso", "exited": False, "awakened_at": 1.0}]}
    check("ⓐ4d worker 부재는 여전히 결손",
          O._shared_verdict_deficit(_ST1, detect=_detect(True), agents=AGENTS)[0] is True)
    # 리뷰어를 **연 뒤**의 계약은 required 주입으로 그대로 살아 있다(능력 제거 아님).
    _REQ = ["cso", "worker", "reviewer-gemini", "reviewer-codex"]
    v_open, _ = O.check_verdicts(_ST, detect=_detect(True), agents=AGENTS, required=_REQ)
    check("ⓐ4e required 주입 시 리뷰어 좌석도 판정 대상이 된다(온디맨드 경로 계약 보존)",
          sorted(v_open) == sorted(_REQ) and v_open["reviewer-gemini"]["satisfied"] is False,
          repr(sorted(v_open)))
    # ★기본 함대 정책의 **짝**: 연 리뷰어는 판정 대상이 된다(부재는 요구하지 않지만, 띄운
    #   좌석의 각성 여부는 누군가 말해야 한다 — ACK 축이 리뷰어 전용이라 이게 없으면 통째로 죽는다).
    _ST_OPEN = {"surfaces": [
        {"role": "cso", "exited": False, "awakened_at": 1.0},
        {"role": "worker", "exited": False, "awakened_at": 1.0},
        {"role": "reviewer-gemini", "exited": False, "agent_alive": True}]}
    v_live, _ = O.check_verdicts(_ST_OPEN, detect=_detect(False), agents=AGENTS)
    check("ⓐ4e-1 살아 있는 리뷰어 좌석은 판정 대상에 편입된다",
          sorted(v_live) == ["cso", "reviewer-gemini", "worker"], repr(sorted(v_live)))
    check("ⓐ4e-2 그러나 **부재** 리뷰어는 여전히 요구하지 않는다(결손 0)",
          O._shared_verdict_deficit(_ST, detect=_detect(False), agents=AGENTS)[0] is False)

    # ACK 축 — 기본 함대에서는 리뷰어 행 자체가 없다(없는 좌석의 pending 금지).
    v, _r = O.check_verdicts(_ST, detect=_detect(False), agents=AGENTS)
    ack = O.ack_axis(_ST, v, _r)
    check("ⓐ4f 기본 함대 ACK 축에 리뷰어 행 0",
          not (ack.get("pending") or ack.get("unmeasured")), repr(ack))

    # cmd_check 종단 — 데몬 왕복만 스텁하고 **실제 exit code** 를 잰다.
    import argparse
    _sv = (O.cys_status, O.reviewer_roster, O.addr_registry_roles)
    O.cys_status = lambda: _ST
    O.addr_registry_roles = lambda: {"cso", "worker"}
    O.reviewer_roster = lambda detect=None, agents=None: [
        {"role": "reviewer-claude-1", "agent": "claude", "native": False,
         "substituted_for": "gemini", "reason": "밀폐"},
        {"role": "reviewer-claude-2", "agent": "claude", "native": False,
         "substituted_for": "codex", "reason": "밀폐"}]
    try:
        rc = O.cmd_check(argparse.Namespace())
    finally:
        O.cys_status, O.reviewer_roster, O.addr_registry_roles = _sv
    check("ⓐ4g 기본 함대 `orchestra check` exit 0(READY)", rc == 0, "rc=%r" % rc)

    # ⓐ 실스폰 — boot-reviewers 는 **기본 스폰 0**, `--spawn` 일 때만 연다.
    class _Args(object):
        plan = False
        spawn = False

    booted = []
    O._boot_one_node = lambda role, agent, timeout=None: (
        booted.append((role, agent)) or (True, 0, O.EXIT_CLASS_OK, "stub"))
    # ★우리 맥 형상(네이티브 2기 실재)에서도 기본은 0 이어야 한다 — 정책이 보편이라는 증거.
    O.reviewer_roster = lambda detect=None, agents=None: [
        {"role": "reviewer-gemini", "agent": "gemini", "native": True,
         "substituted_for": None, "reason": "밀폐"},
        {"role": "reviewer-codex", "agent": "codex", "native": True,
         "substituted_for": None, "reason": "밀폐"}]
    rc = O.cmd_boot_reviewers(_Args())
    check("ⓐ5 네이티브 실재 기계에서도 기본 스폰 0(보편 정책)", booted == [], repr(booted))
    check("ⓐ6 기본 스폰 0 → exit 0(Degrade 아님)", rc == 0, "rc=%r" % rc)
    # 미감지 로스터에서도 마찬가지(대체 2기를 몰래 세우지 않는다)
    booted[:] = []
    O.reviewer_roster = lambda detect=None, agents=None: [
        {"role": "reviewer-claude-1", "agent": "claude", "native": False,
         "substituted_for": "gemini", "reason": "밀폐"},
        {"role": "reviewer-claude-2", "agent": "claude", "native": False,
         "substituted_for": "codex", "reason": "밀폐"}]
    check("ⓐ7 미감지 로스터에서도 기본 스폰 0",
          O.cmd_boot_reviewers(_Args()) == 0 and booted == [], repr(booted))

    # ★온디맨드 기동 1회 — `--spawn` 이면 실제로 연다(능력이 살아 있다는 증거).
    class _Spawn(object):
        plan = False
        spawn = True

    booted[:] = []
    O.reviewer_roster = lambda detect=None, agents=None: [
        {"role": "reviewer-gemini", "agent": "gemini", "native": True,
         "substituted_for": None, "reason": "밀폐"},
        {"role": "reviewer-codex", "agent": "codex", "native": True,
         "substituted_for": None, "reason": "밀폐"}]
    rc = O.cmd_boot_reviewers(_Spawn())
    check("ⓐ8 --spawn → 리뷰어 2기 실제 기동(온디맨드 경로 성공)",
          booted == [("reviewer-gemini", "gemini"), ("reviewer-codex", "codex")], repr(booted))
    check("ⓐ9 --spawn 2기 각성 → exit 0", rc == 0, "rc=%r" % rc)

    # 훅 안내 문구도 같은 정책에서 파생된다(리터럴 금지).
    note = O.team_roster_note()
    check("ⓐ10 팀 안내 = master·cso·worker 3노드 · 리뷰어 온디맨드 고지",
          "총 3노드" in note and "reviewer" not in note
          and O.ONDEMAND_REVIEWER_NOTE in note, note)


def t_formation():
    F = _load("javis_formation")

    check("ⓐ11 편성 로스터 = master·cso·worker(리뷰어 부재)",
          F.REQUIRED_ROLES == ("master", "cso", "worker"), repr(F.REQUIRED_ROLES))
    check("ⓐ12 필수 CLI = claude 하나(agy·codex 부재가 partial 을 만들지 않는다)",
          F.REQUIRED_CLIS == {"claude"}, repr(F.REQUIRED_CLIS))
    check("ⓐ13 3기 생존 = complete(구: partial:agy,codex 영구 고정)",
          F.classify(installed={"claude"}, live={"master", "cso", "worker"},
                     resource_ok=True) == "complete",
          F.classify(installed={"claude"}, live={"master", "cso", "worker"}, resource_ok=True))
    check("ⓐ14 결원은 여전히 complete 아님(완화 아님)",
          F.classify(installed={"claude"}, live={"master", "cso"},
                     resource_ok=True) != "complete")
    check("ⓐ15 리뷰어 CLI 유무가 판정에 **무관**(감지 부활 차단)",
          F.classify(installed={"claude"}, live={"master", "cso", "worker"},
                     resource_ok=True)
          == F.classify(installed={"claude", "agy", "codex"},
                        live={"master", "cso", "worker"}, resource_ok=True))
    check("ⓐ16 완결 피드 본문에 리뷰어 잔존 0(거짓 보고 차단)",
          "reviewer" not in F._complete_feed_body(), F._complete_feed_body())
    check("ⓐ17 편성 모듈에 프로파일 감지 함수가 없다(불일치의 씨앗 제거)",
          not hasattr(F, "participant_profile") and not hasattr(F, "native_reviewer_present"))

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
