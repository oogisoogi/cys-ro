#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""javis_seat.py — 좌석별 폴더(좌석 cwd · 얇은 CLAUDE.md · 폴더 신뢰 시드)의 단일 소유 모듈.

★무엇을 하나(TICKET=cys-seat-folders · 2026-09-15):
  마스터 좌석은 설치기가 준 폴더(JarvisHome)에서 뜬다. 자식 좌석은 종전(663 · v0.14.34)엔 그
  폴더를 **그대로** 물려받아 함대 전원이 한 폴더를 썼다. 이제 자식은 그 아래 자기 폴더에서 뜬다:
      cso      → <JarvisHome>/cso/
      worker   → <JarvisHome>/workers/w1/      worker-N → <JarvisHome>/workers/wN/
  master·리뷰어·그 밖의 역할은 좌석 폴더를 만들지 않는다(= 종전대로 마스터 좌석 폴더).
  규칙의 골든 표 = cysjavis-pack/templates/seat-layout.json — Rust `cys::seat` 가 같은 표로 시험한다.

★좌석 폴더를 만들 때 함께 하는 일 둘:
  ⓐ 얇은 CLAUDE.md — templates/seat-CLAUDE.md 를 역할로 채워 **없을 때만** 만든다(덮어쓰기 0).
  ⓑ 폴더 신뢰 시드 — 그 좌석이 쓰는 Claude 프로필 설정(<CYS_ACCOUNT_DIR 또는 ~/.cys/claude>/
     .claude.json)의 projects[<좌석 폴더>].hasTrustDialogAccepted=true 를 **키가 없을 때만** 쓴다.
     Claude Code 2.1.272 실측: 신뢰는 부모 폴더에서 상속되지만 **git 저장소 루트에서 멈춘다** —
     워커가 좌석 폴더에서 git init 하면 상속이 끊겨 신뢰 창이 뜬다. 그래서 상속 + 시드 이중이다.
     계약은 Rust `pack::plan_first_run_seed` 와 같다(부재 키만 · 다른 키 보존 · 모르는 형태 거부).
     설정 파일이 아예 없으면 만들지 않는다(그 프로필은 아직 한 번도 안 떴다 — 빈 파일을 만들면
     첫기동 관문 상태를 우리가 지어내는 셈이다).

★실패는 좌석을 막지 않는다: 폴더를 못 만들면 호출부는 마스터 좌석 폴더(종전 동작)로 띄운다.
  CLAUDE.md·신뢰 시드 실패는 결과 dict 의 상태 값으로만 남는다(상속이 여전히 1선이다).

사용:
  python3 javis_seat.py self-test
  python3 javis_seat.py subdir <role>
  python3 javis_seat.py ensure --base <마스터 좌석 폴더> --role <role> [--config <.claude.json>] [--json]
"""
import json
import os
import re
import shutil
import sys

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_REL = ("templates", "seat-CLAUDE.md")
LAYOUT_REL = ("templates", "seat-layout.json")
SEAT_CLAUDE_MD = "CLAUDE.md"
CONFIG_FILE = ".claude.json"
TRUST_KEY = "hasTrustDialogAccepted"
PROJECTS_KEY = "projects"
TRUST_BACKUP = ".claude.json.seat-seed.bak"
CAS_TRIES = 3

_WORKER_N = re.compile(r"worker-([0-9]{1,4})")

_DIRECTIVE = (
    ("master", "MASTER_DIRECTIVE.md"),
    ("cso", "CSO_DIRECTIVE.md"),
    ("worker", "WORKER_DIRECTIVE.md"),
    ("reviewer", "REVIEWER_DIRECTIVE.md"),
)


def _pack_dir():
    return os.environ.get("CYS_PACK_DIR") or os.path.dirname(SELF_DIR)


def seat_subdir(role):
    """역할 → 좌석 폴더 상대경로('/' 구분) 또는 None(좌석 폴더 없음) — 순수·골든 표 핀."""
    role = (role or "").strip()
    if role == "cso":
        return "cso"
    if role == "worker":
        return "workers/w1"
    m = _WORKER_N.fullmatch(role)
    if m:
        n = int(m.group(1))
        if n >= 1:
            return "workers/w%d" % n
    return None


def directive_file(role):
    """역할 → 정본 디렉티브 파일명(없으면 None) — 순수."""
    role = (role or "").strip()
    for prefix, name in _DIRECTIVE:
        if role == prefix or role.startswith(prefix + "-"):
            return name
    return None


def home_like(path):
    """좌석 폴더의 기준으로 쓸 수 없는 폴더인가(빈 값·홈·파일시스템 루트) — 순수.

    홈·루트 밑에 cso/·workers/ 를 만들면 사용자 폴더를 어지럽힌다. 그 경우는 '기준 없음'으로
    보고 종전 동작(좌석 폴더 없음)으로 접는다(javis_phoenix.home_like 와 같은 방향)."""
    p = (path or "").strip()
    if not p:
        return True
    n = os.path.normcase(os.path.normpath(os.path.abspath(os.path.expanduser(p))))
    if n == os.path.normcase(os.path.normpath(os.path.expanduser("~"))):
        return True
    return os.path.dirname(n) == n


def seat_dir(base, role):
    """(마스터 좌석 폴더, 역할) → 좌석 폴더 절대경로 또는 None — 순수(파일 접촉 0)."""
    sub = seat_subdir(role)
    if sub is None or home_like(base):
        return None
    return os.path.join(os.path.abspath(os.path.expanduser(base)), *sub.split("/"))


def render_claude_md(template, role):
    """템플릿의 {{ROLE}}·{{DIRECTIVE}} 를 채운다 — 순수."""
    return (template.replace("{{ROLE}}", role)
            .replace("{{DIRECTIVE}}", directive_file(role) or "WORKER_DIRECTIVE.md"))


def _key_form(path):
    return path.replace("\\", "/") if os.name == "nt" else path


def trust_keys(path):
    """신뢰 시드에 쓸 projects 키 — 절대경로 + (다르면) 실경로. Windows 는 '/' 구분.

    Claude Code 는 키를 '/' 로 정규화해 대조한다(바이너리 fB: Windows 에서 '\\'→'/').
    심볼릭 링크 밑 폴더는 어느 쪽 표기로 조회될지 몰라 둘 다 쓴다(여분 키는 무해)."""
    keys = []
    for p in (os.path.abspath(path), os.path.realpath(path)):
        k = _key_form(p)
        if k not in keys:
            keys.append(k)
    return keys


_HS, _HL, _HV, _HT = 0xAC00, 0x1100, 0x1161, 0x11A7
_LC, _VC, _TC = 19, 21, 28
_NC = _VC * _TC
_SC = _LC * _NC


def hangul_nfd(s):
    """조합형 한글 음절만 자모로 분해 — rust `pack::hangul_nfd` 산술 그대로(그 밖 문자는 보존).

    ★전체 Unicode NFD 를 쓰면 안 된다(codex 1R #5): `cafe\\u0301` 같은 비한글 분해형이 rust 에선 다른
    키, python 에선 같은 키가 되어 기존 false 보존 판정이 두 구현에서 갈린다."""
    out = []
    for ch in s:
        c = ord(ch)
        if _HS <= c < _HS + _SC:
            si = c - _HS
            out.append(chr(_HL + si // _NC))
            out.append(chr(_HV + (si % _NC) // _TC))
            t = si % _TC
            if t:
                out.append(chr(_HT + t))
        else:
            out.append(ch)
    return "".join(out)


def hangul_nfc(s):
    """자모 시퀀스만 조합형 음절로 — rust `pack::hangul_nfc` 산술 그대로."""
    src = list(s)
    out = []
    i = 0
    while i < len(src):
        lc = ord(src[i])
        if _HL <= lc < _HL + _LC and i + 1 < len(src):
            vc = ord(src[i + 1])
            if _HV <= vc < _HV + _VC:
                si = (lc - _HL) * _NC + (vc - _HV) * _TC
                used = 2
                if i + 2 < len(src):
                    tc = ord(src[i + 2])
                    if _HT + 1 <= tc < _HT + _TC:
                        si += tc - _HT
                        used = 3
                out.append(chr(_HS + si))
                i += used
                continue
        out.append(src[i])
        i += 1
    return "".join(out)


def _resolve_key(projects, ws):
    """rust pack::resolve_project_key 동형 — 정확 일치 → 한글 분해 일치 기존 키 → 한글 조합형."""
    if ws in projects:
        return ws
    folded = hangul_nfd(ws)
    # ★정렬 순서로 훑는다(codex 2R #5): rust 는 serde_json Map(BTreeMap · 키 정렬)을 훑어 동등 키가 여럿이면
    #   정렬상 첫 키를 고른다. 삽입 순서로 훑으면 같은 설정에서 두 구현이 다른 기존 키를 고른다.
    #   (UTF-8 바이트 순서 = 코드포인트 순서라 python sorted 와 같다.)
    for k in sorted(projects):
        if hangul_nfd(k) == folded:
            return k
    return hangul_nfc(ws)


def plan_trust(existing, keys):
    """순수 계획기 → (next, added, refused). rust `pack::plan_first_run_seed`(workspaces 절) 동형.

    ① 부재 키만 채운다(false 여도 덮지 않는다) ② 다른 키 전부 보존 ③ 최상위·projects 가 객체가
    아니면 거부 ④ 엔트리가 객체가 아니면 그 엔트리만 건너뛴다(관문이 남는 쪽이 안전)."""
    if not isinstance(existing, dict):
        return existing, [], "최상위가 JSON 객체가 아니다 — 덮지 않는다"
    nxt = dict(existing)
    # ★키 부재와 값 null 을 구분한다(rust `match next.get(..) { None => 새 객체, Some(_) 비객체 => 거부 }`
    #   동형 · codex 1R #2): `projects: null` 은 남이 만든 형태라 거부한다.
    if PROJECTS_KEY not in nxt:
        projects = {}
    else:
        projects = nxt[PROJECTS_KEY]
        if not isinstance(projects, dict):
            return existing, [], "`projects` 가 객체가 아니다 — 덮지 않는다"
    projects = dict(projects)
    added = []
    for ws in keys:
        if not ws:
            continue
        key = _resolve_key(projects, ws)
        # ★키 부재와 값 null 을 구분한다(rust `entry().or_insert_with` 동형): 이미 있는 값이 객체가
        #   아니면(null 포함) 남이 만든 형태라 보존하고 건너뛴다 — `.get() is None` 으로 접으면
        #   null 엔트리를 우리 객체로 덮어써 두 구현이 갈린다(codex 1R 지적).
        if key not in projects:
            entry = {}
        else:
            entry = projects[key]
            if not isinstance(entry, dict):
                continue
        if TRUST_KEY not in entry:
            entry = dict(entry)
            entry[TRUST_KEY] = True
            projects[key] = entry
            added.append("%s[%s].%s" % (PROJECTS_KEY, key, TRUST_KEY))
    if added:
        nxt[PROJECTS_KEY] = projects
    return nxt, added, None


def config_file():
    """좌석이 쓰는 Claude 프로필 설정 파일 — rust lib::resolve_claude_config_dir 와 같은 규칙."""
    d = os.environ.get("CYS_ACCOUNT_DIR") or os.path.join(os.path.expanduser("~"), ".cys", "claude")
    return os.path.join(d, CONFIG_FILE)


def seed_trust(cfg_path, keys):
    """신뢰 시드 IO → (상태, 상세). 상태: seeded·nothing·config-absent·refused·failed·unverified.

    ★교체 직전 재대조: 이 파일은 살아 있는 claude 세션들도 쓴다. 읽은 바이트와 교체 직전 바이트가
      다르면 계획을 다시 세운다(최대 CAS_TRIES). 잠금은 claude 가 잡지 않으므로 무의미하다.
    ⚠원자적 비교-교체가 **아니다**(codex 1R #1 · 2R #1 정정): 재대조와 os.replace 사이에 claude 가 저장하면
      그 저장은 이 교체에 덮여 사라지고 결과는 여전히 seeded 다. 교체 대상이 **설정 파일 전체**라 유실
      범위도 신뢰 키에 한정되지 않는다(그 순간 claude 가 쓴 다른 프로젝트 설정·세션 기록 등 전부).
      창을 좁힐 뿐 닫지 못한다(rust seat::seed_trust · pack::seed_first_run_gates_at 도 같은 창)."""
    if os.path.islink(cfg_path):
        return "refused", "symlink 거부: %s" % cfg_path
    if not os.path.isfile(cfg_path):
        return "config-absent", cfg_path
    import tempfile
    for _ in range(CAS_TRIES):
        try:
            with open(cfg_path, "rb") as f:
                b0 = f.read()
            existing = json.loads(b0.decode("utf-8"))
        except (OSError, ValueError) as e:
            return "refused", "%s 판독 불가 — 보존: %s" % (cfg_path, e)
        nxt, added, refused = plan_trust(existing, keys)
        if refused:
            return "refused", refused
        if not added:
            return "nothing", ""
        cfg_dir = os.path.dirname(cfg_path)
        backup = os.path.join(cfg_dir, TRUST_BACKUP)
        tmp = None
        try:
            if not os.path.exists(backup):
                shutil.copy2(cfg_path, backup)
            mode = os.stat(cfg_path).st_mode & 0o7777
            # ★임시 파일은 생성 시점부터 0600(mkstemp) — 기본 권한으로 연 뒤 chmod 하면 umask 022 에서
            #   설정 전체(계정 정보 포함)가 잠시 0644 로 노출된다(codex 2R #7). 원본 권한은 교체 직전에 입힌다.
            fd, tmp = tempfile.mkstemp(prefix=".claude.json.seat-seed.", dir=cfg_dir)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps(nxt, ensure_ascii=False, indent=2))
            os.chmod(tmp, mode)
            with open(cfg_path, "rb") as f:
                b1 = f.read()
            if b1 != b0:
                os.remove(tmp)
                continue
            os.replace(tmp, cfg_path)
        except OSError as e:
            if tmp:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            return "failed", "%s: %s" % (cfg_path, e)
        try:
            with open(cfg_path, "rb") as f:
                again = json.loads(f.read().decode("utf-8"))
            _n, re_added, re_refused = plan_trust(again, keys)
            # rust 와 같다: 되읽기가 거부 형태로 바뀌었어도 '추가할 것 없음'으로 오판하지 않는다(codex 2R #2).
            ok = re_refused is None and not re_added
        except (OSError, ValueError):
            ok = False
        return ("seeded" if ok else "unverified"), ", ".join(added)
    return "failed", "교체 직전 파일이 %d회 연속 바뀌었다(동시 쓰기 경합) — 상속에 맡긴다" % CAS_TRIES


def _seed_claude_md(seat, role, pack_dir):
    path = os.path.join(seat, SEAT_CLAUDE_MD)
    if os.path.lexists(path):
        return "kept"
    tpl = os.path.join(pack_dir, *TEMPLATE_REL)
    try:
        with open(tpl, encoding="utf-8") as f:
            template = f.read()
    except OSError:
        return "template-absent"
    try:
        with open(path, "x", encoding="utf-8") as f:
            f.write(render_claude_md(template, role))
    except FileExistsError:
        return "kept"
    except OSError as e:
        return "failed: %s" % e
    return "seeded"


def ensure_seat(base, role, pack_dir=None, cfg_path=None):
    """좌석 폴더를 준비한다 → None(좌석 폴더 대상 아님) 또는 결과 dict.

    결과: {"cwd": 좌석 폴더 | None(생성 실패 → 호출부는 base 로 띄운다), "created": bool,
           "claude_md": 상태, "trust": 상태, "trust_detail": 상세, "error": 사유 | None}"""
    d = seat_dir(base, role)
    if d is None:
        return None
    out = {"cwd": None, "created": False, "claude_md": "skipped", "trust": "skipped",
           "trust_detail": "", "error": None}
    try:
        out["created"] = not os.path.isdir(d)
        os.makedirs(d, exist_ok=True)
    except OSError as e:
        out["error"] = "좌석 폴더 생성 실패(%s): %s" % (d, e)
        return out
    out["cwd"] = d
    out["claude_md"] = _seed_claude_md(d, role, pack_dir or _pack_dir())
    out["trust"], out["trust_detail"] = seed_trust(cfg_path or config_file(), trust_keys(d))
    return out


def seat_cwd(base, role, pack_dir=None, cfg_path=None):
    """호출부 편의 — (띄울 폴더, 결과 dict|None). 좌석 폴더 대상이 아니거나 생성 실패면 base."""
    res = ensure_seat(base, role, pack_dir, cfg_path)
    if res is None or not res.get("cwd"):
        return base, res
    return res["cwd"], res


def describe(res):
    if res is None:
        return "좌석 폴더 대상 아님"
    if res.get("error"):
        return res["error"]
    return "좌석 폴더=%s(%s) · CLAUDE.md=%s · 신뢰=%s" % (
        res["cwd"], "신설" if res["created"] else "기존", res["claude_md"], res["trust"])


# ── self-test(순수 판정 + 임시 폴더 IO) ──
def self_test():
    import tempfile
    fails = []

    def ck(cond, msg):
        if not cond:
            fails.append(msg)

    layout = os.path.join(os.path.dirname(SELF_DIR), *LAYOUT_REL)
    try:
        cases = json.load(open(layout, encoding="utf-8"))["cases"]
    except (OSError, ValueError, KeyError) as e:
        cases = []
        fails.append("골든 표 판독 실패: %s" % e)
    ck(len(cases) >= 10, "골든 표 사례 %d < 10(공허 통과 차단)" % len(cases))
    for role, want in cases:
        ck(seat_subdir(role) == want, "seat_subdir(%r)=%r ≠ %r" % (role, seat_subdir(role), want))
    ck(directive_file("worker-3") == "WORKER_DIRECTIVE.md", "worker-3 디렉티브")
    ck(directive_file("cso") == "CSO_DIRECTIVE.md", "cso 디렉티브")
    ck(home_like("~") and home_like("") and home_like("/"), "홈·빈값·루트는 기준 불가")
    ck(seat_dir("~", "cso") is None, "홈 기준에서 좌석 폴더를 만들면 안 된다")
    nxt, added, ref = plan_trust({"projects": {"/a": {TRUST_KEY: False}}, "oauthAccount": {"x": 1}},
                                 ["/a", "/b"])
    ck(ref is None and nxt["projects"]["/a"][TRUST_KEY] is False, "기존 false 를 덮었다")
    ck(nxt["projects"]["/b"][TRUST_KEY] is True and nxt["oauthAccount"] == {"x": 1}, "시드·보존")
    ck(added == ["projects[/b].hasTrustDialogAccepted"], "added=%r" % added)
    ck(plan_trust([], ["/a"])[2] and plan_trust({"projects": []}, ["/a"])[2], "모르는 형태 거부")
    ck(plan_trust({"projects": None}, ["/a"])[2], "`projects: null` 을 덮었다 — rust 는 거부한다")
    nfd_key = hangul_nfd("/좌석")
    nxt_h, added_h, _ = plan_trust({"projects": {nfd_key: {TRUST_KEY: False}}}, ["/좌석"])
    ck(not added_h and nxt_h["projects"] == {nfd_key: {TRUST_KEY: False}},
       "한글 분해형 기존 키(false)를 조합형 요청이 못 찾았다: %r" % (nxt_h,))
    nxt_c, added_c, _ = plan_trust({"projects": {"/café": {TRUST_KEY: False}}}, ["/café"])
    ck(added_c == ["projects[/café].hasTrustDialogAccepted"],
       "비한글 분해형은 rust 처럼 다른 키여야 한다(전체 NFD 폴드 금지): %r" % (nxt_c,))
    # 동등 한글 키가 여럿이면 정렬상 첫 키(rust BTreeMap 순회와 같다 · codex 2R #5)
    k_nfc, k_nfd = "/좌석", hangul_nfd("/좌석")
    ordered = {k_nfc: {}, k_nfd: {TRUST_KEY: False}}          # 삽입 순서는 조합형이 먼저 · 정렬 순서는
    #                                                           분해형(자모 U+110C < 음절 U+C88C)이 먼저
    want_first = sorted([k_nfc, k_nfd])[0]
    probe = hangul_nfd("/좌") + "석"                              # 앞은 분해형 · 뒤는 조합형(세 번째 표기)
    ck(probe not in ordered and want_first != list(ordered)[0],
       "픽스처 전제: 삽입 순서 첫 키와 정렬 순서 첫 키가 달라야 판별력이 있다")
    ck(_resolve_key(ordered, probe) == want_first,
       "동등 키 선택이 정렬 순서가 아니다: got=%r want=%r" % (_resolve_key(ordered, probe), want_first))
    nxt_n, added_n, _ = plan_trust({"projects": {"/n": None, "/s": "x"}}, ["/n", "/s"])
    ck(nxt_n["projects"] == {"/n": None, "/s": "x"} and not added_n,
       "이미 있는 비객체 엔트리(null 포함)를 덮었다 — rust or_insert_with 와 갈린다: %r" % (nxt_n,))
    with tempfile.TemporaryDirectory() as t:
        base = os.path.join(t, "JarvisHome")
        pack = os.path.join(t, "pack")
        os.makedirs(os.path.join(pack, "templates"))
        with open(os.path.join(pack, *TEMPLATE_REL), "w", encoding="utf-8") as f:
            f.write("role={{ROLE}} dir={{DIRECTIVE}}\n")
        cfg = os.path.join(t, "profile", CONFIG_FILE)
        os.makedirs(os.path.dirname(cfg))
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({"numStartups": 3}, f)
        os.chmod(cfg, 0o600)
        cwd, res = seat_cwd(base, "worker-2", pack, cfg)
        ck(cwd == os.path.join(base, "workers", "w2") and os.path.isdir(cwd), "좌석 폴더 cwd=%r" % cwd)
        ck(open(os.path.join(cwd, SEAT_CLAUDE_MD), encoding="utf-8").read()
           == "role=worker-2 dir=WORKER_DIRECTIVE.md\n", "CLAUDE.md 렌더")
        d = json.load(open(cfg, encoding="utf-8"))
        ck(d.get("numStartups") == 3 and all(d["projects"][k][TRUST_KEY] is True
                                            for k in trust_keys(cwd)), "신뢰 시드: %r" % d)
        if os.name != "nt":
            ck(os.stat(cfg).st_mode & 0o777 == 0o600, "설정 파일 권한이 넓어졌다")
        with open(os.path.join(cwd, SEAT_CLAUDE_MD), "w", encoding="utf-8") as f:
            f.write("사용자 수정\n")
        _, res2 = seat_cwd(base, "worker-2", pack, cfg)
        ck(res2["claude_md"] == "kept" and res2["trust"] == "nothing" and not res2["created"],
           "두 번째 호출은 무변경이어야 한다: %r" % res2)
        ck(open(os.path.join(cwd, SEAT_CLAUDE_MD), encoding="utf-8").read() == "사용자 수정\n",
           "기존 CLAUDE.md 를 덮었다")
        cwd_m, res_m = seat_cwd(base, "master", pack, cfg)
        ck(cwd_m == base and res_m is None, "master 는 좌석 폴더 대상이 아니다")
        _, res_a = seat_cwd(base, "cso", pack, os.path.join(t, "none", CONFIG_FILE))
        ck(res_a["trust"] == "config-absent" and not os.path.exists(os.path.join(t, "none")),
           "설정 파일이 없으면 만들지 않는다: %r" % res_a)
    if fails:
        print("javis_seat self-test FAIL: %s" % fails, file=sys.stderr)
        return 1
    print("javis_seat self-test OK (골든 %d · 신뢰 계획 · 좌석 IO)" % len(cases))
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd in ("self-test", "--self-test"):
        return self_test()
    if cmd == "subdir" and len(argv) == 2:
        print(seat_subdir(argv[1]) or "")
        return 0
    if cmd == "ensure":
        import argparse
        ap = argparse.ArgumentParser(prog="javis_seat.py ensure")
        ap.add_argument("--base", required=True)
        ap.add_argument("--role", required=True)
        ap.add_argument("--config", default=None)
        ap.add_argument("--json", action="store_true")
        a = ap.parse_args(argv[1:])
        cwd, res = seat_cwd(a.base, a.role, cfg_path=a.config)
        if a.json:
            print(json.dumps({"cwd": cwd, "seat": res}, ensure_ascii=False))
        else:
            print("%s\t%s" % (cwd, describe(res)))
        return 0
    print("usage: javis_seat.py self-test | subdir <role> | ensure --base B --role R", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
