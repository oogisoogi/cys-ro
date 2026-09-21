#!/usr/bin/env python3
"""javis_ctx_relay.py — 좌석 컨텍스트 정지선 중계(v113 A3 · ISSUES B9 · TICKET=v113-dept).

왜 있는가(【관측】 2026-09-21): 데몬은 좌석 CTX 가 임계(기본 60% · CYS_CONTEXT_THRESHOLD_PCT)를 넘을 때
`context.threshold` 이벤트를 **발행만** 한다(handlers.rs maybe_fire_context_threshold). 그 이벤트를 소비해
운영 담당(CSO) 좌석을 깨우는 코드는 데몬·팩 어디에도 없었다 — CSO_DIRECTIVE 의 「수신 시 cycle-agent 집행」은
CSO 가 스스로 이벤트를 구독하고 있을 때만 성립한다. 부서 1개 = 좌석 +3 이 상한 없이 늘면 무clear 100%+
(4군②)가 그대로 남는다. 이 도구는 이 레인의 좌석 CTX 를 `cys status --json`(데몬 관측값 · 두 번째 계수기 없음)
에서 읽어, 임계를 넘은 좌석마다 **넘을 때 1회** CSO 에 `[ctx-threshold]` 통지를 큐 배달한다.

  tick   스케줄 잡이 2분마다 부른다(부서 레인 = cys-dept seed_schedule 시드 · 본부 = cysd builtin ctx-relay-base). 언제나 exit 0(fail-open).

판정: role 이 cso 가 아닌 좌석 · CTX ≥ 임계(usage.ctx_pct 관측 · status.context_pct 자기보고 중 신선한 쪽의 큰 값 —
10분 넘은 값은 무시).
재통지: 넘김 통지 뒤 10분이 지나도 임계 위면 딱 1회 다시 깨운다(CSO 무응답 정책 적용 시점 · 넘김당 상한 2통).
재무장: 그 좌석 CTX 가 임계 − 10 아래로 내려오면(순환·clear 뒤) 다음 넘김에 다시 통지한다.
CSO 좌석이 없으면 보내지 않는다(받을 이가 없다 — 다음 틱에 다시 본다).
"""
import json
import os
import subprocess
import sys
import time

NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}
FRESH_SEC = 600
REARM_GAP = 10
REMIND_SEC = 600      # 넘김 통지 뒤 이만큼 지나도 임계 위면 1회만 다시 깨운다(무응답 정책 적용 시점)


def threshold():
    try:
        v = int(os.environ.get("CYS_CONTEXT_THRESHOLD_PCT", "60"))
        return v if 1 <= v <= 100 else 60
    except ValueError:
        return 60


def cys_bin():
    return os.environ.get("CYS_BIN") or "cys"


def state_path():
    sd = os.environ.get("CYS_STATE_DIR") or os.path.join(os.path.expanduser("~"), ".cys", "state")
    lane = os.path.basename(os.path.dirname(os.environ.get("CYS_SOCKET") or "")) or "base"
    return os.path.join(sd, "ctx-relay-%s.json" % lane)


def load_state():
    try:
        with open(state_path(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(d):
    p = state_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = "%s.tmp.%d" % (p, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, p)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def seat_pct(s, now):
    """신선한 두 출처(데몬 관측 usage.ctx_pct · 자기보고 status.context_pct) 중 큰 값 — 데몬 임계 발화도
    두 경로 어느 쪽이든 넘으면 발화한다(handlers.rs maybe_fire_context_threshold 3경로 공유). 낡은 값은 버린다."""
    vals = []
    u = s.get("usage") or {}
    if _num(u.get("ctx_pct")) and _num(u.get("updated_at")) and now - u["updated_at"] <= FRESH_SEC:
        vals.append(u["ctx_pct"])
    st = s.get("status") or {}
    if _num(st.get("context_pct")) and _num(st.get("age_secs")) and st["age_secs"] <= FRESH_SEC:
        vals.append(st["context_pct"])
    return max(vals) if vals else None


def decide(surfaces, st, now, thr):
    """(보낼 통지 [(sid, role, pct, n)], 새 상태) — 순수 판정(시험 대상). n=1 넘김 통지 · n=2 무응답 재통지(1회)."""
    notes = []
    new = dict(st)
    has_cso = any(str(s.get("role") or "").startswith("cso") and not s.get("exited") for s in surfaces)
    for s in surfaces:
        role = str(s.get("role") or "")
        if not role or role.startswith("cso") or s.get("exited"):
            continue
        pct = seat_pct(s, now)
        if pct is None:
            continue
        key = str(s.get("surface_id"))
        if pct >= thr:
            cur = new.get(key)
            if isinstance(cur, (int, float)) and not isinstance(cur, bool):
                cur = {"at": cur, "n": 1}                # 옛 상태(시각만) 호환
            if not cur and has_cso:
                notes.append((key, role, int(pct), 1))
                new[key] = {"at": now, "n": 1}
            elif cur and cur.get("n") == 1 and now - (cur.get("at") or now) >= REMIND_SEC and has_cso:
                # 【관측】(격리 실측): master 가 ack 를 못 하면 CSO 는 「120초 무응답 → 독립 검증」 단계에서 깨울
                # 이가 없어 영원히 기다렸다. 넘김당 딱 1회 재통지(상한 2통) — 폭주 축이 되지 않는다.
                notes.append((key, role, int(pct), 2))
                new[key] = {"at": cur.get("at"), "n": 2}
        elif pct < thr - REARM_GAP:
            new.pop(key, None)
    return notes, new


def notice_text(role, sid, pct, thr, n=1):
    """CSO 에게 가는 통지 한 줄. 【관측】(v113 격리 실측 2026-09-21): 옛 문구를 받은 CSO 가 이 통지 자체를
    「오너 실시간 입력 중」으로 읽어 clear 를 보류했다 — 그 규칙은 **대상 좌석**에서 오너가 치고 있을 때다.
    그래서 출처(데몬 기계 통지 · 오너 입력 아님)와 대상별 첫 행동을 문장에 박는다(되묻기·보류 오독 차단)."""
    head = ("[ctx-threshold] 데몬 기계 통지(오너 입력 아님 · 정기 잡 ctx-relay) — %s@surface:%s 컨텍스트 %d%% · 임계 %d%%. "
            % (role, sid, pct, thr))
    if role == "master":
        step = ("할 일: CSO 규약 §2 master 사이클 ②부터 — 대상 master 입력줄에서 오너가 치는 중이 아니면 "
                "master 에 「[CSO·주인 대신] clear 시점 — 세션 재개 준비하라」 통보 → ack·검증 뒤 "
                "`cys cycle-agent --role master --verifier cso`. 되묻지 말 것.")
    else:
        step = ("할 일: 대상 좌석에 60%% 매듭(새 항목 금지·커밋·HANDOFF)을 알리고, 저장이 확인되면 70%% 이전에 "
                "`cys cycle-agent --surface surface:%s` 집행. 그 과정에서 [CYCLE-VERIFY] 가 너에게 오면 네가 검증자다 — "
                "대상 저장 파일 갱신을 확인하고 `cys feed reply <번호> allow`(오너 승인 대상 아님). 되묻지 말 것." % sid)
    if n >= 2:
        step = ("재통지(마지막 · 첫 통지 뒤 %d분 · 아직 임계 위): ack 가 없었다면 CSO 규약 §2 무응답 정책을 지금 적용하라 — "
                "대상의 저장 상태를 독립 검증해 신선하면 cycle-agent 집행 · 낡았으면 clear 금지·오너 escalation. "
                "되묻지 말 것." % (REMIND_SEC // 60))
    return head + step


def cmd_tick():
    try:
        p = subprocess.run([cys_bin(), "status", "--json"], capture_output=True, text=True, timeout=20, **NOWIN)
        surfaces = (json.loads(p.stdout) or {}).get("surfaces") or []
    except Exception as e:
        sys.stderr.write("[ctx-relay] status 판독 실패 %s — 이번 틱 보류\n" % type(e).__name__)
        return 0
    thr = threshold()
    notes, new = decide(surfaces, load_state(), time.time(), thr)
    for sid, role, pct, n in notes:
        body = notice_text(role, sid, pct, thr, n)
        try:
            subprocess.run([cys_bin(), "send", "--queued", "--to", "cso", body], capture_output=True, text=True,
                           timeout=20, **NOWIN)
        except Exception as e:
            sys.stderr.write("[ctx-relay] 통지 실패 %s\n" % type(e).__name__)
            if n >= 2:                                   # 재통지 실패 = 첫 통지 상태로 되돌려 다음 틱에 재통지만 다시(agy 1R)
                new[sid] = {"at": (new.get(sid) or {}).get("at"), "n": 1}
            else:
                new.pop(sid, None)                       # 다음 틱에 다시 보낸다
    try:
        save_state(new)
    except OSError:
        pass
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["tick"]:
        return cmd_tick()
    sys.stderr.write("usage: javis_ctx_relay.py tick\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
