#!/usr/bin/env python3
"""javis_ctx_relay.py — 좌석 컨텍스트 정지선 중계(v113 A3 · ISSUES B9 · TICKET=v113-dept).

왜 있는가(【관측】 2026-09-21): 데몬은 좌석 CTX 가 임계(기본 60% · CYS_CONTEXT_THRESHOLD_PCT)를 넘을 때
`context.threshold` 이벤트를 **발행만** 한다(handlers.rs maybe_fire_context_threshold). 그 이벤트를 소비해
운영 담당(CSO) 좌석을 깨우는 코드는 데몬·팩 어디에도 없었다 — CSO_DIRECTIVE 의 「수신 시 cycle-agent 집행」은
CSO 가 스스로 이벤트를 구독하고 있을 때만 성립한다. 부서 1개 = 좌석 +3 이 상한 없이 늘면 무clear 100%+
(4군②)가 그대로 남는다. 이 도구는 이 레인의 좌석 CTX 를 `cys status --json`(데몬 관측값 · 두 번째 계수기 없음)
에서 읽어, 임계를 넘은 좌석마다 **넘을 때 1회** CSO 에 `[ctx-threshold]` 통지를 큐 배달한다.

  tick   스케줄 잡(부서 레인 = cys-dept seed_schedule 이 시드)이 2분마다 부른다. 언제나 exit 0(fail-open).

판정: role 이 cso 가 아닌 좌석 · usage.ctx_pct ≥ 임계 · usage.updated_at 이 10분 안(낡은 값 무시).
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


def decide(surfaces, st, now, thr):
    """(보낼 통지 [(sid, role, pct)], 새 상태) — 순수 판정(시험 대상)."""
    notes = []
    new = dict(st)
    has_cso = any(str(s.get("role") or "").startswith("cso") and not s.get("exited") for s in surfaces)
    for s in surfaces:
        role = str(s.get("role") or "")
        if not role or role.startswith("cso") or s.get("exited"):
            continue
        u = s.get("usage") or {}
        pct, at = u.get("ctx_pct"), u.get("updated_at")
        if not isinstance(pct, (int, float)) or isinstance(pct, bool):
            continue
        if not isinstance(at, (int, float)) or now - at > FRESH_SEC:
            continue
        key = str(s.get("surface_id"))
        if pct >= thr:
            if not new.get(key) and has_cso:
                notes.append((key, role, int(pct)))
                new[key] = now
        elif pct < thr - REARM_GAP:
            new.pop(key, None)
    return notes, new


def cmd_tick():
    try:
        p = subprocess.run([cys_bin(), "status", "--json"], capture_output=True, text=True, timeout=20, **NOWIN)
        surfaces = (json.loads(p.stdout) or {}).get("surfaces") or []
    except Exception as e:
        sys.stderr.write("[ctx-relay] status 판독 실패 %s — 이번 틱 보류\n" % type(e).__name__)
        return 0
    thr = threshold()
    notes, new = decide(surfaces, load_state(), time.time(), thr)
    for sid, role, pct in notes:
        body = ("[ctx-threshold] %s@surface:%s 컨텍스트 %d%% — 임계 %d%% 도달. 60%% 매듭(새 항목 금지·커밋·HANDOFF) · "
                "70%% 이전 순환: 운영 담당 규약대로 `cys cycle-agent` 집행을 판단하라(되묻지 말 것 · 기계 통지)."
                % (role, sid, pct, thr))
        try:
            subprocess.run([cys_bin(), "send", "--queued", "--to", "cso", body], capture_output=True, text=True,
                           timeout=20, **NOWIN)
        except Exception as e:
            sys.stderr.write("[ctx-relay] 통지 실패 %s\n" % type(e).__name__)
            new.pop(sid, None)                           # 다음 틱에 다시 보낸다
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
