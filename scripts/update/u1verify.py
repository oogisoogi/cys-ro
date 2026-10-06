"""U1 `cys update-verify` 재실행 검증(1.1.8 U3 3판 · codex 2R #4·#6·#15 — 증표 신뢰 폐지).

발행 게이트(release-gate.py verify)·봉투 상속(make-envelope.py)·게시기(publish-site.py envelope)가 **같은 함수**로 U1 검증기를
직접 다시 돌린다 — 통과 증표(.verified.json)는 정보용일 뿐 어디서도 게시·상속 조건이 아니다(서명 없는 JSON 이라 위조 가능).
"""
import base64
import json
import os
import subprocess
import types


class GateFail(Exception):
    pass


class Undetermined(Exception):
    pass


def args(cys, component, channel, envelope, revocations, sig=None, revocations_sig=None, target=None,
         installed_release_seq=None, allow_expired=False):
    return types.SimpleNamespace(cys=cys, component=component, channel=channel, envelope=envelope,
                                 sig=sig or envelope + ".minisig", revocations=revocations,
                                 revocations_sig=revocations_sig or revocations + ".minisig", target=target,
                                 installed_release_seq=installed_release_seq, allow_expired=allow_expired)


# ★3판(U1 2판 CLI 계약 = HANDOFF-U1 ⑨·§7 ⑷): cysr 는 `--installed-release-seq` 를 받지 않는다(주면 rc 2) → 출발 seq 는
#   `--enumerate-installed` 1회(max(min_from,1)..=후보 각각 판정) · agora-client 만 명시 설치 seq 를 하나씩 준다.
MAX_ENUM = 64  # codex 2R #11: 과대 범위(min_from 이 아주 낮은 본문) 반복 상한 — 넘으면 판정하지 않고 거부


def _run_verify(cys, a, target, extra):
    cmd = [cys, "update-verify", "--component", a.component, "--channel", a.channel,
           "--envelope", a.envelope, "--sig", a.sig, "--revocations", a.revocations,
           "--revocations-sig", a.revocations_sig, "--target", target, "--json"] + extra
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        raise Undetermined("update-verify 출력이 JSON 아님(rc %d): %s %s" % (p.returncode, p.stdout[-300:], p.stderr[-300:]))


def _expired_ok(a, v):
    return a.allow_expired and v.get("verdict") == "reject" and v.get("code") == "update.feed_expired" and v.get("step") == "ⓔ"


def _row_check(t, v, body):
    """반환 행 **전체** = 본문 원문 행(codex 1R/2R #10 · U1 2판부터 payload_manifest 포함 — 대기 분기 없음)."""
    got, want = v.get("asset") or {}, body["assets"][t]
    if not got:
        if v.get("verdict") == "apply":
            raise GateFail("update-verify[%s] apply 인데 asset 없음" % t)
        return
    for k in sorted(set(want) | set(got)):
        if got.get(k) != want.get(k) and not (k == "features" and got.get(k) in (None, []) and want.get(k) == []):
            raise GateFail("update-verify[%s] 반환 행 칸 %s 가 원문과 다르다: %r ≠ %r" % (t, k, got.get(k), want.get(k)))


def verify_envelope(cys, a, accept):
    """봉투 쌍 + 폐기문을 U1 으로 검증(발행 게이트 · make-envelope 상속 · publish-site 게시가 같은 함수를 부른다).

    반환 = 요약 줄 목록. 거부 = GateFail · 판정 불가 = Undetermined. `a` 에 component·channel·envelope·sig·revocations·
    revocations_sig·target(목록|None)·installed_release_seq(agora-client 만)·allow_expired 가 있어야 한다."""
    if not cys or not os.access(cys, os.X_OK):
        raise Undetermined("cys 바이너리 없음(update-verify 필요 · U1 2판 이상): %r" % cys)
    env = json.load(open(a.envelope, encoding="utf-8"))
    body = json.loads(base64.b64decode(env["release"]))
    targets = a.target or sorted(body["assets"])
    seq, low = int(body["release_seq"]), int(body["min_from_release_seq"])
    lo = max(low, 1)
    if seq - lo + 1 > MAX_ENUM:
        raise GateFail("출발 seq 범위 %d..%d = %d개 > 상한 %d(min_from_release_seq 를 올려라)" % (lo, seq, seq - lo + 1, MAX_ENUM))
    if lo > seq:
        raise GateFail("허용 출발 seq 가 없다(min_from_release_seq %d > release_seq %d)" % (low, seq))
    # lo == seq(첫 판 seq 1 등 · 4판 master 결정 ①): 출발 seq 없이 「후보 자신 = uptodate」 1행만으로 통과 — U1 cli 도 같은 규칙(291 공동 수정).
    out = []
    for t in targets:
        if a.component == "cysr":
            if a.installed_release_seq is not None:
                raise GateFail("cysr 은 명시 설치 seq 를 받지 않는다(U1 2판 B4 · 열거만) — --installed-release-seq 빼라")
            rc, v = _run_verify(cys, a, t, ["--enumerate-installed"])
            if _expired_ok(a, v):
                out.append("update-verify[%s] 만료(ⓔ)만 — 허용(--allow-expired)" % t)
                continue
            if v.get("mode") != "enumerate" or v.get("verdict") != "ok":
                raise GateFail("update-verify[%s] 열거 = %s/%s(step %s · %s · problems %s) rc %d"
                               % (t, v.get("verdict"), v.get("code"), v.get("step"), v.get("detail"), v.get("problems"), rc))
            # ★4판(3R MAJOR-1 · U1 3판 feed::render_enum_row): 행 = {"installed_release_seq": N, "outcome": {판정 · asset …}}
            #   — 판정 본문은 단일 판정(render_outcome)과 같은 바이트로 `outcome` 안에 있다(키 이름은 U1 소스 핀 시험이 잰다).
            res = v.get("results") or []
            got = [r.get("installed_release_seq") for r in res]
            if got != list(range(lo, seq + 1)):
                raise GateFail("update-verify[%s] 열거 범위 %s ≠ 기대 %d..%d" % (t, got, lo, seq))
            for r in res:
                o = r.get("outcome")
                if not isinstance(o, dict):
                    raise GateFail("update-verify[%s] 열거 행에 outcome 객체가 없다(U1 열거 서식 변경?): %r" % (t, r))
                ok = ["uptodate"] if r["installed_release_seq"] == seq else accept
                if o.get("verdict") not in ok:
                    raise GateFail("update-verify[%s · installed %d] = %s/%s(step %s · %s) — 허용 %s"
                                   % (t, r["installed_release_seq"], o.get("verdict"), o.get("code"), o.get("step"),
                                      o.get("detail"), ok))
                _row_check(t, o, body)
            out.append("update-verify[%s] 출발 seq %s 전부 허용 판정(열거)" % (t, ",".join(str(i) for i in got)))
        else:
            if a.installed_release_seq is not None:
                plan = [(a.installed_release_seq, accept, None)]
            else:  # 경계 포함(codex 2R #11): low-1 = ⓛ 거부 · lo..seq-1 = 허용 · seq·seq+1 = uptodate
                plan = ([(lo - 1, ["reject"], "ⓛ")] + [(i, accept, None) for i in range(lo, seq)]
                        + [(seq, ["uptodate"], None), (seq + 1, ["uptodate"], None)])
            for installed, ok, step in plan:
                rc, v = _run_verify(cys, a, t, ["--installed-release-seq", str(installed)])
                if _expired_ok(a, v):
                    continue
                if v.get("verdict") not in ok or (step and v.get("step") != step):
                    raise GateFail("update-verify[%s · installed %d] = %s/%s(step %s · %s) rc %d — 허용 %s%s"
                                   % (t, installed, v.get("verdict"), v.get("code"), v.get("step"), v.get("detail"), rc,
                                      ok, " @%s" % step if step else ""))
                if v.get("verdict") in ("apply", "halt", "not_in_rollout"):
                    _row_check(t, v, body)
            out.append("update-verify[%s] 출발 seq %s 판정(경계 포함)" % (t, ",".join(str(i) for i, _, _ in plan)))
    return out


