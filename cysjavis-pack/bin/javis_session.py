#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SESSION_STATE 예약 엔티티 ensure-X (T3-5).

penpot ensure-hidden-theme 패턴의 *개념만* 클린룸 차용 — Clojure 코드복사 0(MPL-2.0 파일전염
회피, well-known idempotent upsert는 보호 대상 아님). 복원 핵심 필드(restore_pointer·open_gates)를
부재 시 idempotent 생성하고, ensure-then-verify 라운드트립으로 그 존재·파싱가능을 결정론 보장한다
(hide≠lose 가드 — 숨김이 손실이 되지 않게).

★R5 FIX: verify는 substring 매칭이 아니라 STRUCTURAL 파싱(블록 구조를 파싱해 orphan/corrupt 탐지).
ensure의 corrupt 경로는 DUPLICATE append가 아니라 in-place REPAIR(깨진 블록을 정상 블록으로 교체).

사용:
    javis_session.py ensure [--file PATH]   # exit 0=ensure 완료(생성·무변형·복구), 2=I/O오류
    javis_session.py verify [--file PATH] [--json]
                                            # exit 0=두 예약 필드 정상, 1=불변식 위반, 2=I/O
    javis_session.py --self-test            # exit 0=배터리 ok, 1=fail (JSON 출력)
    javis_session.py path                   # ★D14 SESSION_STATE 정본 경로(자기 레인 팩 round/)
    javis_session.py adopt [--cwd D] [--apply]
                                            # 옛 위치(<cwd>/_round) → 정본 이관 판정/집행(JSON)
"""
import argparse
import json
import os
import re
import shutil
import sys
import time

RESERVED_SENTINEL = "__CYS__RESERVED__"
FIELDS = ("restore_pointer", "open_gates")

# (open_marker, default_body, close_marker) — penpot hidden-theme-name sentinel 등가.
BLOCKS = {
    "restore_pointer": (
        "<!-- CYS:RESERVED:restore_pointer %s -->" % RESERVED_SENTINEL,
        "- 복원 포인터: (없음)",
        "<!-- /CYS:RESERVED:restore_pointer -->",
    ),
    "open_gates": (
        "<!-- CYS:RESERVED:open_gates %s -->" % RESERVED_SENTINEL,
        "## 미해결 게이트\n- (없음)",
        "<!-- /CYS:RESERVED:open_gates -->",
    ),
}


def _open_re(field):
    # open 마커는 sentinel 토큰을 반드시 보유해야 정상(R5: sentinel 없는 마커 = corrupt).
    return re.compile(
        r"<!--\s*CYS:RESERVED:%s\s+%s\s*-->" % (re.escape(field), re.escape(RESERVED_SENTINEL))
    )


def _close_re(field):
    return re.compile(r"<!--\s*/CYS:RESERVED:%s\s*-->" % re.escape(field))


def _scan(text, field):
    """STRUCTURAL 파싱(R5): 블록 상태를 분류한다.

    반환: ('absent'|'ok'|'corrupt', span) — span은 복구가 교체할 (start,end) 또는 None.
      - absent : open/close 둘 다 없음 → ensure가 새로 생성.
      - corrupt: open만 / close만 / 순서뒤집힘 / 중복(orphan stranded) → ensure가 in-place 교체.
      - ok     : 정상 1쌍(open … close) → 무변형.
    """
    opens = list(_open_re(field).finditer(text))
    closes = list(_close_re(field).finditer(text))
    if not opens and not closes:
        return ("absent", None)
    # 정확히 1쌍이고 open이 close보다 앞 → 정상.
    if len(opens) == 1 and len(closes) == 1 and opens[0].start() < closes[0].start():
        return ("ok", (opens[0].start(), closes[0].end()))
    # 그 외 전부 corrupt(open-only/close-only/중복/역순). 복구 교체 범위 = 마커들의 최소~최대 스팬.
    marks = [m.span() for m in opens] + [m.span() for m in closes]
    start = min(s for s, _ in marks)
    end = max(e for _, e in marks)
    return ("corrupt", (start, end))


def verify_text(text):
    """STRUCTURAL 채점 — substring 아님. orphan/corrupt를 위반으로 잡는다."""
    fields = {}
    violations = []
    for f in FIELDS:
        st, _ = _scan(text, f)
        fields[f] = st == "ok"
        if st == "absent":
            violations.append("예약 필드 '%s' 부재" % f)
        elif st == "corrupt":
            violations.append("예약 필드 '%s' 마커 깨짐(orphan/중복/역순)" % f)
    return {"ok": not violations, "fields": fields, "violations": violations}


def _block_text(field):
    o, body, c = BLOCKS[field]
    return "%s\n%s\n%s" % (o, body, c)


def ensure_text(text):
    """penpot (if (contains? data X) data (assoc ...)) 등가 + R5 REPAIR.

    - ok      : 무변형(바이트 보존, idempotent).
    - corrupt : 깨진 스팬을 정상 블록으로 in-place 교체(DUPLICATE append 아님 — orphan 잔류 0).
    - absent  : 말미에 정상 블록 생성.
    """
    for f in FIELDS:
        st, span = _scan(text, f)
        if st == "ok":
            continue
        block = _block_text(f)
        if st == "corrupt":
            start, end = span
            text = text[:start] + block + text[end:]
        else:  # absent
            if text and not text.endswith("\n"):
                text += "\n"
            text += "\n%s\n" % block
    return text


def _write_atomic(path, text):
    """★G1(a): wakeup._write_json_atomic 동형 텍스트판 — tmp→flush→fsync→os.replace.
    SESSION_STATE는 재부팅 복원의 단일 진실이라 크래시 시점의 반쪽 파일이 곧 복원 실패다."""
    tmp = "%s.tmp.%d.%d" % (path, os.getpid(), time.time_ns())
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class _FileLock:
    """★G1(b): wakeup._FileLock 이식 — mkdir 원자성 락. stale(30초+)은 rename으로 원자 회수."""

    def __init__(self, path, timeout=5.0, stale_sec=30.0):
        self.path, self.timeout, self.stale_sec = path, timeout, stale_sec

    def __enter__(self):
        deadline = time.time() + self.timeout
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        while True:
            try:
                os.mkdir(self.path)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.stat(self.path).st_mtime > self.stale_sec:
                        os.rename(self.path, "%s.stale.%d" % (self.path, time.time_ns()))
                        continue
                except OSError:
                    pass
                if time.time() > deadline:
                    raise TimeoutError("lock timeout: %s" % self.path)
                time.sleep(0.02)

    def __exit__(self, *exc):
        try:
            os.rmdir(self.path)
        except OSError:
            pass


def cmd_ensure(path):
    try:
        # ★G1(b): read-modify-write 전체를 배타락으로 직렬화(동시 ensure 경쟁 차단).
        with _FileLock(path + ".lock"):
            text = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
            out = ensure_text(text)
            if out != text:  # diff0: 변화 없으면 쓰지 않음(idempotent·mtime 보존)
                # ★G1(c): corrupt 복구는 원문 스팬을 지우므로 교체 전 백업(증거 보존).
                if os.path.isfile(path) and any(_scan(text, f)[0] == "corrupt" for f in FIELDS):
                    shutil.copy2(path, "%s.bak-corrupt-%s" % (path, time.strftime("%Y%m%dT%H%M%S")))
                _write_atomic(path, out)  # ★G1(a): 크래시에도 반쪽 파일 0
            # ensure-then-verify(R5 hide≠lose 가드): 재읽기 후 verify 통과해야 성공.
            re_read = open(path, encoding="utf-8").read()
            return 0 if verify_text(re_read)["ok"] else 2
    except (OSError, TimeoutError):
        return 2


def cmd_verify(path, as_json):
    try:
        r = verify_text(open(path, encoding="utf-8").read())
    except OSError:
        print("읽기 불가: %s" % path, file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["ok"] else 1


def self_test():
    failures = []
    # ① 빈 입력 → 두 필드 정상 생성.
    t = ensure_text("")
    if not verify_text(t)["ok"]:
        failures.append("빈입력 ensure가 필드 미생성")
    # ② idempotent: 정상 파일 2회 적용 바이트 동일(diff0).
    if ensure_text(t) != t:
        failures.append("ensure 비멱등(바이트 변형)")
    # ③ 사용자 산문 보존(블록 내부 채운 내용 무변형).
    user = t.replace("- 복원 포인터: (없음)", "- 복원 포인터: ▶Phase3 게이트2")
    if ensure_text(user) != user:
        failures.append("사용자 내용 보존 실패")
    # ④ corrupt-recover 배터리(R5 핵심): close 마커 제거 → verify FAIL → ensure REPAIR → verify PASS.
    #    그리고 복구가 DUPLICATE가 아닌 in-place 교체임을 증명(마커 쌍이 정확히 1개).
    broken = t.replace("<!-- /CYS:RESERVED:open_gates -->", "", 1)
    if verify_text(broken)["ok"]:
        failures.append("corrupt(close 제거) 미탐지 — verify가 hollow(substring)")
    repaired = ensure_text(broken)
    if not verify_text(repaired)["ok"]:
        failures.append("corrupt 복구 후 verify 실패(REPAIR 미작동)")
    if len(_open_re("open_gates").findall(repaired)) != 1 \
            or len(_close_re("open_gates").findall(repaired)) != 1:
        failures.append("복구가 DUPLICATE append(마커 중복 — orphan stranded)")
    # ⑤ orphan(open만 떠도는 sentinel) → corrupt 탐지 + 복구.
    orphan = "<!-- CYS:RESERVED:restore_pointer %s -->\n없는 close" % RESERVED_SENTINEL
    if verify_text(orphan)["fields"]["restore_pointer"]:
        failures.append("open-only orphan을 ok로 오판")
    print(json.dumps(
        {"self_test": "ok" if not failures else "fail", "failures": failures},
        ensure_ascii=False, indent=2,
    ))
    return 0 if not failures else 1


# ── ★D14(1.1.8 · 윈 결함 보고 2026-10-05): SESSION_STATE 정본 경로 = 이 함수 하나 ──────────────
# 실측(윈 cysr 1.1.7): orchestra next-action·gate-status 는 `<pack>/round` 를 읽고, 복원 주입 훅·
#   preflight·스냅샷은 `<cwd>/_round` 를 읽었다 → master 는 훅이 보여 준 `install-jarvis/_round` 에 쓰고
#   (35,843B · 당일), 판정기는 10일 묵은 팩 골격(2,063B)을 읽어 큐가 늘 빈 것으로 나왔다(안전 쪽 실패라 은폐).
# 정본 = **자기 레인 팩의 round/** — 지침(MASTER_DIRECTIVE §0 ③·§9 · CSO §1-2)·`cys todo-path`·
#   cycle_autopilot resolve_save_files(결재 7ⓐ)·Rust cycle 저장 검증(앵커5·6)이 이미 그쪽이다.
#   부서 레인은 CYS_PACK_DIR=pack-dept-<이름> 이라 같은 함수가 부서 정본을 낸다(레인 교차 0).
# 키 목록·순서·'첫 값이 이긴다' = `PACK_DIR_ENV_KEYS` 정본(Rust src/pack.rs 기계 대조 · 시험
#   test_todo_shared_constants). 셸 쌍둥이 = hooks/_lib.sh `cys_session_state_path`(시험 test_session_state_canon).
PACK_DIR_ENV_KEYS = ("CYS_PACK_DIR", "JAVIS_PACK_DIR", "AITERM_PACK_DIR", "AITERM_JARVIS_DIR")
LEGACY_MOVED_SUFFIX = ".moved-to-pack"


def lane_pack_dir(env=None):
    """자기 레인 팩 경로 — 팩 env 키 중 첫 비어 있지 않은 값, 없으면 `~/.cys/pack`."""
    env = os.environ if env is None else env
    for key in PACK_DIR_ENV_KEYS:
        v = env.get(key, "")
        if v:
            return v
    home = env.get("HOME") if env is not os.environ else None
    return os.path.join(home or os.path.expanduser("~"), ".cys", "pack")


def session_state_path(env=None, pack=None):
    """SESSION_STATE 정본 절대경로 — 읽는 쪽·쓰는 쪽·검증 쪽 전부 이 함수만 쓴다(D14)."""
    return os.path.join(pack or lane_pack_dir(env), "round", "SESSION_STATE.md")


def legacy_candidates(cwd, root=None):
    """정본이 아닌 옛 위치 `<…>/_round/SESSION_STATE.md` 후보 — cwd 상향탐색 + ACTIVE_PROJECT 포인터.

    1.1.7 까지 복원 훅이 이 자리를 작업기억으로 주입해 master 가 거기에 썼다. 이제 정본이 아니므로
    `adopt` 가 내용을 정본으로 옮기고 이 파일을 치운다(남아 있는 골격이 검증자를 조용히 오판시킨다).
    """
    out = []
    d, prev = cwd, None
    while d and os.path.isabs(d) and d != prev and os.path.dirname(d) != d:
        f = os.path.join(d, "_round", "SESSION_STATE.md")
        if os.path.isfile(f):
            out.append(f)
            break
        prev, d = d, os.path.dirname(d)
    if root:
        try:
            with open(os.path.join(root, "_round", "ACTIVE_PROJECT"), "r", encoding="utf-8") as fh:
                ap = fh.readline().strip()
            f = os.path.join(ap, "_round", "SESSION_STATE.md") if ap else ""
            if f and os.path.isfile(f) and f not in out:
                out.append(f)
        except OSError:
            pass
    return out


def is_skeleton(text):
    """설치 골격(round/SESSION_STATE.md · SeedOnce) 그대로인가 — master 가 한 번도 쓰지 않은 정본.
    판정 = 제목 줄의 「(골격)」 + 「마지막 갱신: (시각)」 자리표시자 둘 다(master 첫 기록이 둘 다 지운다)."""
    first = (text or "").lstrip("\ufeff").split("\n", 1)[0]
    return "(골격)" in first and "마지막 갱신: (시각)" in (text or "")


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def adopt_plan(legacy, canonical):
    """옛 위치 → 정본 이관 판정(순수 · 쓰기 0). 반환 dict(action=adopt|same|keep, reason).

    - 같은 파일(정본 자신)             → keep  (same-file)
    - 내용 같음                        → same  (이미 정본에 있음)
    - 정본 부재 · 정본이 설치 골격 그대로 → adopt (옛 내용이 실제 작업기억 — 정본으로 복사)
    - 정본에 master 기록이 있음        → keep  (canonical-written · 어느 쪽이 참인지 사람 판단 — 경고만)
    """
    try:
        if os.path.exists(canonical) and os.path.samefile(legacy, canonical):
            return {"action": "keep", "reason": "same-file"}
    except OSError:
        pass
    try:
        ltext = _read(legacy)
    except OSError:
        return {"action": "keep", "reason": "legacy-unreadable"}
    if not os.path.exists(canonical):
        return {"action": "adopt", "reason": "canonical-missing"}
    try:
        ctext = _read(canonical)
    except OSError:
        return {"action": "keep", "reason": "canonical-unreadable"}
    if ltext == ctext:
        return {"action": "same", "reason": "identical"}
    if is_skeleton(ctext) and not is_skeleton(ltext):
        return {"action": "adopt", "reason": "canonical-skeleton"}
    return {"action": "keep", "reason": "canonical-written"}


def adopt(legacy, canonical, retire=False, now=None):
    """`adopt_plan` 집행 — 되돌릴 수 있게만 쓴다(삭제 0). adopt = 정본을 `.bak-<시각>` 로 백업한 뒤
    옛 내용을 원자 복사. 옛 파일은 기본 **손대지 않는다**(그 `_round` 를 다른 작업이 함께 쓸 수 있다) —
    `retire=True` 이고 이관이 끝난 경우(adopt·same)에만 `<이름>.moved-to-pack-<시각>` 으로 개명한다."""
    plan = adopt_plan(legacy, canonical)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    plan.update({"legacy": legacy, "canonical": canonical})
    if plan["action"] == "adopt":
        text = _read(legacy)
        os.makedirs(os.path.dirname(canonical), exist_ok=True)
        if os.path.exists(canonical):
            bak = "%s.bak-%s" % (canonical, stamp)
            shutil.copy2(canonical, bak)
            plan["backup"] = bak
        _write_atomic(canonical, text)
    if retire and plan["action"] in ("adopt", "same"):
        moved = "%s%s-%s" % (legacy, LEGACY_MOVED_SUFFIX, stamp)
        os.replace(legacy, moved)
        plan["moved"] = moved
    return plan


def say_line(row):
    """복원 훅(inject-context)이 그대로 싣는 1줄 — 이관 결과를 좌석이 알게 한다(무음 이관 금지)."""
    act, leg, canon = row.get("action"), row.get("legacy"), row.get("canonical")
    if act == "adopt":
        bak = row.get("backup")
        return ("■ 작업기억 이관(D14): 옛 위치 %s 의 기록을 정본 %s 로 옮겼다%s. 이제부터 정본만 읽고 쓴다 — 옛 파일은 손대지 않았다."
                % (leg, canon, (" (설치 골격은 %s 로 백업)" % bak) if bak else ""))
    if act == "same":
        return "ℹ 옛 위치 %s 는 정본 %s 와 같은 내용이다 — 정본만 쓴다." % (leg, canon)
    if act == "keep" and row.get("reason") == "canonical-written":
        return ("⚠ 옛 위치 %s 에 정본(%s)과 다른 작업기억이 남아 있다 — 정본은 하나다(옛 파일은 이제 아무도 읽지 않는다). "
                "옛 내용 중 필요한 것은 정본으로 옮겨 적고 옛 파일은 정리하라." % (leg, canon))
    return ""


def _default_path():
    return session_state_path()


def main():
    ap = argparse.ArgumentParser(description="SESSION_STATE 예약 엔티티 ensure/verify")
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("ensure", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--file", default=None)
        if name == "verify":
            p.add_argument("--json", action="store_true")
    sub.add_parser("path", help="SESSION_STATE 정본 경로 1줄(D14 단일 해소)")
    pa = sub.add_parser("adopt", help="옛 위치(<cwd>/_round) SESSION_STATE → 정본 이관(기본 = 판정만)")
    pa.add_argument("--cwd", default=None)
    pa.add_argument("--root", default=None, help="ACTIVE_PROJECT 포인터 루트(기본 CYS_ROOT 또는 HOME)")
    pa.add_argument("--apply", action="store_true", help="실제 이관(정본 백업 뒤 복사 · 삭제 0)")
    pa.add_argument("--say", action="store_true", help="복원 훅용 사람 말 1줄씩(JSON 대신)")
    pa.add_argument("--retire", action="store_true", help="이관이 끝난 옛 파일을 .moved-to-pack-<시각> 으로 개명")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.cmd == "path":
        print(session_state_path())
        return 0
    if a.cmd == "adopt":
        canon = session_state_path()
        root = a.root or os.environ.get("CYS_ROOT") or os.path.expanduser("~")
        rows = []
        for leg in legacy_candidates(os.path.abspath(a.cwd or os.getcwd()), root):
            rows.append(adopt(leg, canon, retire=a.retire) if a.apply else dict(adopt_plan(leg, canon),
                                                             legacy=leg, canonical=canon))
        if a.say:
            for line in filter(None, (say_line(r) for r in rows)):
                print(line)
            return 0
        print(json.dumps({"canonical": canon, "applied": bool(a.apply), "items": rows},
                         ensure_ascii=False))
        return 0
    path = (a.file or _default_path()) if a.cmd else _default_path()
    if a.cmd == "ensure":
        return cmd_ensure(path)
    if a.cmd == "verify":
        return cmd_verify(path, getattr(a, "json", False))
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
