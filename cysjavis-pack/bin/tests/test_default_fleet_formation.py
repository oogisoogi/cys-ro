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
    # ★2R #10 둘째 수리: 종전 검체는 `boot_v2_enabled` 없는 status 를 먹여 **축이 꺼진 채**로
    #   초록이었다(axis=False → 세 목록이 전부 None → `not (...)` 가 자동 참). 축을 **켜고** 잰다.
    _ST_V2 = dict(_ST, boot_v2_enabled=True)
    v, _r = O.check_verdicts(_ST_V2, detect=_detect(False), agents=AGENTS)
    ack = O.ack_axis(_ST_V2, v, _r)
    check("ⓐ4f 기본 함대 ACK 축(켜짐)에 리뷰어 행 0",
          ack.get("axis") is True and ack.get("pending") == [] and ack.get("ok") == []
          and ack.get("unmeasured") == [], repr(ack))

    # ★★2R BLOCKER #7 회귀 핀 — **감지 로스터 밖에서 열린 살아 있는 리뷰어**도 ACK 대상이다.
    #   종전 `ack_axis` 는 대상을 `reviewer_roster()`(2슬롯)로 좁혀, `reviewer-grok` 같은
    #   임의 이름 좌석이 `ack_nonce_ok=false` 여도 pending=[] · exit 0 으로 게이트를 우회했다.
    _ST_GROK = {"boot_v2_enabled": True, "surfaces": [
        {"role": "cso", "exited": False, "awakened_at": 1.0, "ack_nonce_ok": True},
        {"role": "worker", "exited": False, "awakened_at": 1.0, "ack_nonce_ok": True},
        {"role": "reviewer-grok", "exited": False, "agent_alive": True,
         "ack_nonce_ok": False}]}
    v_g, r_g = O.check_verdicts(_ST_GROK, detect=_detect(False), agents=AGENTS)
    check("ⓐ4f-1 살아 있는 임의 이름 리뷰어가 판정 대상에 든다",
          "reviewer-grok" in v_g, repr(sorted(v_g)))
    ack_g = O.ack_axis(_ST_GROK, v_g, r_g)
    check("ⓐ4f-2 그 좌석의 ack_nonce_ok=false 는 **pending 으로 집계**된다(축소 구멍 봉인)",
          ack_g.get("pending") == ["reviewer-grok"], repr(ack_g))
    check("ⓐ4f-3 exit 는 0 이 아니다(12 ack_pending) — 「presence must be awake」",
          O.check_exit_code({"ready_missing": []}, ack_g) == O.CHECK_EXIT_ACK_PENDING,
          repr(O.check_exit_code({"ready_missing": []}, ack_g)))
    # 로스터를 **비워도** 결과가 같아야 한다 = 대상 집합이 로스터에서 왔던 의존이 끊겼다는 증거.
    check("ⓐ4f-4 로스터가 비어도 동일 판정(로스터 의존 제거의 직접 증거)",
          O.ack_axis(_ST_GROK, v_g, [])["pending"] == ["reviewer-grok"],
          repr(O.ack_axis(_ST_GROK, v_g, [])))

    # ★★2R HIGH #9 회귀 핀 — 처방이 **실제로 교정하는가**(맨 boot-reviewers = 스폰 0).
    _rem_known = O.ack_remedy(["reviewer-gemini"])
    check("ⓐ4f-5 처방에 --spawn 이 있다(맨 호출은 리뷰어 0기 스폰 = 무동작)",
          "boot-reviewers --spawn" in _rem_known, _rem_known)
    check("ⓐ4f-6 처방의 per-role 경로에 --agent 가 채워진다(없으면 boot_node 가 exit 2 로 거절)",
          "javis_boot_node.py --role reviewer-gemini --agent gemini" in _rem_known, _rem_known)
    check("ⓐ4f-7 Claude 대체 좌석의 에이전트도 표에서 해소된다",
          O.reviewer_boot_agent("reviewer-claude-2") == "claude"
          and O.reviewer_boot_agent("reviewer-codex") == "codex"
          and O.reviewer_boot_agent("reviewer-grok") is None)
    _rem_unknown = O.ack_remedy(["reviewer-grok"])
    check("ⓐ4f-8 표 밖 좌석은 **교정 불가를 명시**한다(추측 --agent 금지 · 사람이 할 일)",
          "자동 교정 불가" in _rem_unknown and "사람이 할 일" in _rem_unknown
          and "--agent <에이전트>" in _rem_unknown, _rem_unknown)
    check("ⓐ4f-9 표 밖 좌석 처방에 맨 boot-reviewers 를 내지 않는다",
          "boot-reviewers" not in _rem_unknown, _rem_unknown)

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
    # ★프로덕션 함수를 **치환 전에** 붙잡아 둔다 — 아래 ⓐ9a 가 실제 호출 사슬을 재려면
    #   여기서 씌우는 람다가 아니라 원본이 필요하다(치환 후 복원 = 람다 복원이라 무의미).
    _PROD_BOOT_ONE = O._boot_one_node
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

    # ★2R #10 첫째 수리 — 위 ⓐ8·ⓐ9 는 `_boot_one_node` 를 **람다로 치환**해 재므로 실제
    #   호출 사슬(subprocess → javis_boot_node.py → --agent 계약)을 하나도 밟지 않는다.
    #   여기서는 **프로덕션 `_boot_one_node` 를 그대로 두고** 경계를 한 칸 아래(subprocess.run)
    #   로 내려 잡아, 실제로 조립돼 나가는 argv 를 잰다. 데몬·실 스폰은 여전히 무접촉이다.
    class _RC(object):
        returncode = 0

    argvs = []
    _sv_boot, _sv_run = O._boot_one_node, O.subprocess.run
    try:
        O._boot_one_node = _PROD_BOOT_ONE                 # 프로덕션 함수 복원(람다 치환 해제)
        O.subprocess.run = lambda cmd, **kw: (argvs.append(list(cmd)) or _RC())
        O.reviewer_roster = lambda detect=None, agents=None: [
            {"role": "reviewer-gemini", "agent": "gemini", "native": True,
             "substituted_for": None, "reason": "밀폐"},
            {"role": "reviewer-claude-2", "agent": "claude", "native": False,
             "substituted_for": "codex", "reason": "밀폐"}]
        rc_real = O.cmd_boot_reviewers(_Spawn())
    finally:
        O._boot_one_node, O.subprocess.run = _sv_boot, _sv_run
    check("ⓐ9a --spawn 이 **실제 호출 사슬**로 javis_boot_node.py 를 부른다(람다 우회 아님)",
          len(argvs) == 2 and all(a[1].endswith("javis_boot_node.py") for a in argvs),
          repr(argvs))
    check("ⓐ9b 조립된 argv 에 --role/--agent 가 실린다(--agent 부재는 boot_node 가 exit 2 로 거절)",
          [(a[a.index("--role") + 1], a[a.index("--agent") + 1]) for a in argvs]
          == [("reviewer-gemini", "gemini"), ("reviewer-claude-2", "claude")], repr(argvs))
    check("ⓐ9c 실 사슬 경로도 exit 0", rc_real == 0, "rc=%r" % rc_real)

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

    # ★C03 대표 마커가 **preflight 에서 파생**되는가(2026-09-11 · 사본 드리프트 봉인).
    #   종전엔 여기에 리터럴 "4종 의무 노드" 사본이 박혀 있어, 기본 함대 정책으로 디렉티브를
    #   정합시키는 순간 `_c03_pass()` 가 **조용히 False** 가 됐다(정책을 고치면 사본이 거짓말).
    marks = F._c03_marker_pins()
    import javis_preflight as PF
    check("ⓐ18 C03 대표 마커가 preflight SOT(C03_MARKER_PINS)에서 온다(리터럴 사본 0)",
          marks == list(PF.C03_MARKER_PINS) and "4종 의무 노드" not in marks, repr(marks))
    # ★1R codex 지적: 「기본 함대」 두 글자는 **판별력이 없다**(문서 곳곳에 나온다).
    #   정책을 판별하는 고유 문구여야 하고, 그 문구는 CONTENT_PINS 에도 실재해야 한다.
    _pins = [p for p, _l in PF.CONTENT_PINS["MASTER_DIRECTIVE.md"]]
    check("ⓐ18a 대표 마커가 정책을 **판별**한다(구성·리뷰어 경계 고유 문구)",
          "기본 함대 = master · CSO · worker 1기" in marks
          and "리뷰어는 기본 함대가 아니다" in marks and "기본 함대" not in marks, repr(marks))
    check("ⓐ18b 대표 마커(정체 'master' 제외)는 CONTENT_PINS 의 부분집합이다",
          all(m in _pins for m in marks if m != "master"),
          repr([m for m in marks if m != "master" and m not in _pins]))
    check("ⓐ19 repo 디렉티브가 C03 취지를 통과한다(정합 후에도 초록)",
          F._c03_pass() is True)
    # 음성 픽스처: 대표 마커를 지운 문서는 반드시 적색이어야 한다.
    import tempfile
    _sv_dd = F._directives_dir
    try:
        tmp = tempfile.mkdtemp()
        io.open(os.path.join(tmp, "MASTER_DIRECTIVE.md"), "w", encoding="utf-8").write(
            "master 만 있고 대표 마커는 없다\n")
        F._directives_dir = lambda: tmp
        check("ⓐ20 대표 마커 없는 문서는 적색(게이트 실효 증명)", F._c03_pass() is False)
    finally:
        F._directives_dir = _sv_dd

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
    # ★2R codex #2 둘째 구멍 + #10 셋째 — 종전 검체는 혼합 함대의 **실패를 축복**했다("아무것도
    #   덮지 않는다" = 홈에 굳은 cso 가 영영 안 고쳐진다). 이제 계약이 바이너리 능력별로 둘이다.
    check("ⓑ4c 구 바이너리(전역 override)에서는 한 명이라도 작업 폴더면 덮지 않는다(이주 금지)",
          P.restore_cwd_override(ENT_MIX, ["cso", "worker"], "/jarvis") is None)
    check("ⓑ4c-1 신 바이너리(항목별)에서는 홈 좌석이 있으면 덮는다 — 유효 좌석은 바이너리가 지킨다",
          P.restore_cwd_override(ENT_MIX, ["cso", "worker"], "/jarvis", per_entry=True)
          == "/jarvis")
    check("ⓑ4c-2 항목별이라도 **홈 좌석이 하나도 없으면** 덮지 않는다(무의미한 override 금지)",
          P.restore_cwd_override({"cso": {"cwd": "/a/wt"}, "worker": {"cwd": "/b/wt"}},
                                 ["cso", "worker"], "/jarvis", per_entry=True) is None)
    check("ⓑ4d master cwd 미해소면 override 없음(종전 동작)",
          P.restore_cwd_override(ENT_HOME, ["cso"], None) is None)
    check("ⓑ4e 대상이 master 뿐이면 override 없음(자기 기준값을 자기에게 덮지 않는다)",
          P.restore_cwd_override(ENT_HOME, ["master"], "/jarvis") is None)
    # master 부재 케이스 — 라이브에 없으면 **영속 토폴로지**의 master 엔트리가 기준이 된다.
    # ★2R #2 넷째 구멍(2026-09-11): 이제 기준 폴더는 **실재하는 디렉터리**여야 채택된다.
    #   합성 경로(/jarvis·/live)는 실디스크에 없으므로 존재 술어를 주입해 밀폐를 유지한다.
    _sv_status, _sv_isdir = P._status_json, P._isdir
    P._isdir = lambda p: p in ("/jarvis", "/live", "/proj/wt", os.path.expanduser("~"))
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
        # ★2R #2 첫째 구멍 — 라이브 master 가 **홈**이면 채택하지 않고 영속으로 흘려보낸다.
        #   (codex 가 `master_seat_cwd(...) == 홈` 을 직접 재현한 자리다.)
        P._status_json = lambda socket: {"surfaces": [
            {"role": "master", "exited": False, "cwd": HOME}]}
        check("ⓑ4i-1 라이브 master 가 홈이면 기준으로 쓰지 않는다(영속 non-HOME 으로 폴백)",
              P.master_seat_cwd("/s.sock", {"master": {"cwd": "/jarvis"}}) == "/jarvis")
        check("ⓑ4i-2 라이브·영속 둘 다 홈이면 None(홈은 절대 기준이 아니다)",
              P.master_seat_cwd("/s.sock", {"master": {"cwd": HOME}}) is None)
        check("ⓑ4i-3 순수 파서 자체가 홈 좌석을 돌려주지 않는다",
              P.master_seat_cwd_from_status(
                  {"surfaces": [{"role": "master", "exited": False, "cwd": HOME}]}) is None)
        # ★넷째 구멍 — **소실된** 폴더는 채택하지 않는다(cysd 가 PTY 빌더에 그대로 넣는다).
        P._status_json = lambda socket: {"surfaces": [
            {"role": "master", "exited": False, "cwd": "/gone/wt"}]}
        check("ⓑ4i-4 라이브 기준 폴더가 실재하지 않으면 채택 금지(영속으로 폴백)",
              P.master_seat_cwd("/s.sock", {"master": {"cwd": "/jarvis"}}) == "/jarvis")
        check("ⓑ4i-5 영속 기준 폴더도 소실이면 None",
              P.master_seat_cwd("/s.sock", {"master": {"cwd": "/gone/too"}}) is None)
        check("ⓑ4i-6 _dir_ok 진리표(빈 값·소실·실재)",
              P._dir_ok("") is False and P._dir_ok("/gone/wt") is False
              and P._dir_ok("/jarvis") is True)
    finally:
        P._status_json, P._isdir = _sv_status, _sv_isdir

    # ★능력 탐침(2R #2) — 팩↔바이너리 스큐를 **실측**으로 가른다(버전 문자열 추론 금지).
    class _H(object):
        def __init__(self, rc, out):
            self.returncode, self.stdout, self.stderr = rc, out, ""

    _sv_cys_probe = P.cys
    try:
        for name, rc, out, want in (
                ("토큰 있음 → 항목별 지원", 0, "  --cwd <CWD>  ... (per-entry-cwd — ...)", True),
                ("토큰 없음(구 바이너리) → 미지원", 0, "  --cwd <CWD>  복원 폴더", False),
                ("도움말 실패(rc≠0) → 미지원(보수)", 2, "per-entry-cwd", False)):
            P._PER_ENTRY_CACHE.clear()
            P.cys = lambda *a, **kw: _H(rc, out)
            got = P.restore_supports_per_entry_cwd("/s.sock")
            check("ⓑ4p 능력 탐침 — %s" % name, got is want, repr(got))
        # 측정 자체가 던져도 부활 경로를 죽이지 않는다(보수적으로 미지원).
        P._PER_ENTRY_CACHE.clear()
        P.cys = lambda *a, **kw: (_ for _ in ()).throw(OSError("cys 부재"))
        check("ⓑ4p-1 탐침 예외 → 미지원으로 접는다(부활 경로 보존)",
              P.restore_supports_per_entry_cwd("/s.sock") is False)
    finally:
        P.cys = _sv_cys_probe
        P._PER_ENTRY_CACHE.clear()

    # ★배선 소스 핀 — 호출부가 탐침 결과를 override 결정에 **실제로 넘기는가**.
    #   (순수 함수만 재고 배선을 안 재면, 계약이 맞아도 실경로가 구 계약으로 굳는다.)
    _src = io.open(os.path.join(BIN, "javis_phoenix.py"), encoding="utf-8").read()
    check("ⓑ4q 호출부가 restore_supports_per_entry_cwd 결과를 per_entry= 로 전달",
          "restore_supports_per_entry_cwd(socket)" in _src
          and "per_entry=per_entry" in _src,
          "배선이 끊겼다 — 순수 함수는 맞는데 실경로가 종전 계약으로 굳는다")

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


def _apple_secret_names(text):
    """맥 서명 프리플라이트가 요구하는 APPLE_* 이름 목록 — 그 스텝의 `for v in …` 에서 파생."""
    import re
    m = re.search(r"for v in ((?:APPLE_[A-Z0-9_]+|\\\s*|\s)+);\s*do", text)
    if not m:
        return []
    return sorted(set(re.findall(r"APPLE_[A-Z0-9_]+", m.group(1))))


def _has_apple_secrets_expr(text):
    """`HAS_APPLE_SECRETS:` 한 줄의 `${{ … }}` 식(순수). 없으면 None."""
    for ln in text.splitlines():
        if ln.strip().startswith("HAS_APPLE_SECRETS:"):
            return ln.split(":", 1)[1].strip()
    return None


# ── ⓖ 릴리스 본문 = **자산 유무 파생**(2026-09-11 · 항목9) ─────────────────────────────
# ★윈도우 단독 태그(맥 서명 시크릿 부재 → 맥 레그 명시 skip)에서도 본문이 ".dmg 를 받으라"고
#   안내하면, 릴리스 페이지가 **존재하지 않는 자산**을 가리킨다. 본문의 설치 안내 줄은
#   리터럴이 아니라 파생값이어야 한다.
def t_release_body_derived():
    rel = ".github/workflows/release.yml"
    try:
        src = io.open(os.path.join(REPO, rel), encoding="utf-8", errors="replace").read()
    except OSError as e:
        check("ⓖ %s 판독" % rel, False, str(e))
        return
    body = _block_scalar(src, "releaseBody")
    check("ⓖ releaseBody 블록 추출", bool(body), "자리가 사라졌다(측정 불능은 통과가 아니다)")
    check("ⓖ 설치 안내가 **파생값**이다(리터럴 .dmg 금지)",
          bool(body) and ".dmg" not in body
          and "steps.relbody.outputs.install_line" in body,
          (body or "")[:200])
    check("ⓖ 파생 스텝이 실재하고 맥 레그 판정과 같은 소스를 읽는다",
          "id: relbody" in src and "steps.macsign.outputs.enabled" in src,
          "파생 스텝·판정 소스 부재 — 본문이 다시 리터럴로 굳는다")
    # ★1R codex 지적: 인증서 1종만 보면 **부분 설정**(cert 있고 나머지 중 하나 없음)에서
    #   맥 레그는 skip 인데 본문은 .dmg 를 안내한다. 기대 목록을 **맥 프리플라이트에서 파생**해
    #   (사본 금지) 폴백 식이 그 7종을 전부 보는지 대조한다.
    want = _apple_secret_names(src)
    fallback = _has_apple_secrets_expr(src)
    check("ⓖ1 맥 프리플라이트가 요구하는 APPLE_* 목록 추출(7종)",
          len(want) == 7, repr(want))
    check("ⓖ2 윈도우 레그 폴백이 **그 7종 전부**를 본다(인증서 1종 판정 금지)",
          bool(fallback) and all(("secrets.%s != ''" % n) in fallback for n in want),
          (fallback or "")[:200])
    # 음성 픽스처: 인증서 1종만 보는 식으로 되돌리면 반드시 적색이어야 한다.
    mutated = src.replace(fallback or "@@none@@", "${{ secrets.APPLE_CERTIFICATE_B64 != '' }}")
    mfb = _has_apple_secrets_expr(mutated)
    check("ⓖ3 인증서 1종 판정으로 회귀 시 적색(게이트 실효 증명)",
          not (mfb and all(("secrets.%s != ''" % n) in mfb for n in want)),
          "1종 판정으로 되돌려도 초록 — 이 축은 아무것도 재지 않는다")
    # 음성 픽스처: 파생 참조를 지우고 리터럴로 되돌리면 반드시 적색이어야 한다.
    lit = src.replace("${{ steps.relbody.outputs.install_line }}",
                      "macOS는 .dmg, Windows는 -setup.exe를 내려받아 설치하세요.")
    lbody = _block_scalar(lit, "releaseBody")
    check("ⓖ4 리터럴 회귀 시 적색(게이트 실효 증명)",
          bool(lbody) and ".dmg" in lbody,
          "리터럴로 되돌려도 초록 — 이 축은 아무것도 재지 않는다")


# ── ⓗ ACK 처방 동기 — 문서가 **교정하지 않는 명령**을 처방하지 않는가(1R codex 지적) ─────────
# ★`boot-reviewers` 맨 호출은 기본 함대 정책상 리뷰어를 0기 스폰한다(조기 반환). 코드에서
#   처방을 고쳐도 문서 소비자(master·CEO·리뷰어)가 무플래그 줄을 읽으면 결과는 같다 —
#   사람이 명령을 치고도 상태가 그대로인 **무동작 거짓 처방**이다.
ACK_RX_FILES = ["directives/MASTER_DIRECTIVE.md", "directives/CEO_TEMPLATE.md",
                "directives/REVIEWER_DIRECTIVE.md", "CLAUDE.md.template"]
PACK = os.path.join(REPO, "cysjavis-pack")


def _bare_boot_reviewers(text):
    """`javis_orchestra.py boot-reviewers` 중 `--spawn` 이 뒤따르지 않는 출현(순수)."""
    import re
    out = []
    # ★따옴표 허용: 디렉티브는 `"${CYS_PACK_DIR…}/bin/javis_orchestra.py" boot-reviewers` 형태로도
    #   쓴다. `\s+` 만 보면 그 형태를 통째로 놓쳐 게이트에 사각이 생긴다(안 잡는 게이트는 게이트가
    #   아니다 — 이 파일이 ⓕ에서 이미 배운 교훈).
    for m in re.finditer(r"javis_orchestra\.py[\"'`]?\s+boot-reviewers", text):
        tail = text[m.end():m.end() + 12]
        if not tail.lstrip().startswith("--spawn"):
            out.append(text[max(0, m.start() - 40):m.end() + 20].replace("\n", " "))
    return out


def t_ack_remedy_docs():
    for rel in ACK_RX_FILES:
        try:
            src = io.open(os.path.join(PACK, rel), encoding="utf-8", errors="replace").read()
        except OSError as e:
            check("ⓗ %s 판독" % rel, False, str(e))
            continue
        bare = _bare_boot_reviewers(src)
        check("ⓗ %s — 무플래그 boot-reviewers 처방 0" % rel, not bare, repr(bare[:2]))
    # 음성 픽스처: 무플래그 줄을 하나 심으면 반드시 잡혀야 한다.
    check("ⓗ 재출현 탐지(게이트 실효 증명 · 맨 호출)",
          len(_bare_boot_reviewers("처방: javis_orchestra.py boot-reviewers 로 재각성")) == 1)
    check("ⓗ 재출현 탐지(따옴표 경로 형태도 잡는다 — 사각 0)",
          len(_bare_boot_reviewers('`"$P/bin/javis_orchestra.py" boot-reviewers` 로 재각성')) == 1)
    check("ⓗ --spawn 이 붙은 정상 처방은 잡지 않는다(위경보 0)",
          _bare_boot_reviewers('"$P/bin/javis_orchestra.py" boot-reviewers --spawn') == []
          and _bare_boot_reviewers("javis_orchestra.py boot-reviewers --spawn") == [])


def main():
    t_attribution()
    t_release_body_derived()
    t_ack_remedy_docs()
    t_orchestra()
    t_formation()
    t_phoenix()
    t_winjob()
    print("\n=== %d/%d PASS (fails: %s) ===" % (_total[0] - len(fails), _total[0], fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
