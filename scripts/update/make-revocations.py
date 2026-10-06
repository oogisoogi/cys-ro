#!/usr/bin/env python3
"""폐기문(R) 생성기(1.1.8 U3 · 설계 AUTO-UPDATE-118 §4-1 R 행 · U1 keys.rs 서식) — **서명 없는** revocations.json 을 만든다.

R 의식은 **사건 때만** 돈다(키 위임·폐기 · 특정 릴리스 무효화 · DR 핀 교체 · 정기 0). 절차 1쪽 = docs/update/R-RITUAL.md.
서식(U1 `src/update/keys.rs` RawRevocations 와 같은 칸 · 보충 3 = HANDOFF-U1 §2 ③④⑤):
  {kind:"update-revocations", rev, key_id(R), signed_at,
   delegations[{key_id, purpose(release|feed|win-asset), pubkey, not_after(정수 초)}],
   revoked_key_ids[], revoked_releases[{component, release_seq, severity(advisory|stop_seats), reason_code}],
   dr_pins{add[], revoke[]}}

입력 = 직전 폐기문(있으면 그 위에 **더한다** — 빼는 것은 `--drop-*` 로 명시) + 이번 사건 칸. 규칙(어기면 rc 2):
  · ★2판(codex 1R #5·#15): 직전 폐기문은 `.minisig` 를 키링 root 키로 **암호 검증**한 것만 받는다 · 폐기 집합(revoked_key_ids ·
    revoked_releases · dr_pins.revoke)은 직전의 **상위집합**이어야 한다 · signed_at = 신뢰 시각(인자 0)이고 직전보다 뒤.
  · rev = 직전 + 1(직전 없음 = `--first` 명시 → 1) · 위임 용도는 root·pack 불가 · 위임 key_id = 공개키 파생값 ·
    severity ∈ {advisory, stop_seats} · component ∈ {cysr, agora-client} · R 키 자신을 revoked_key_ids 에 넣지 못함.
  · 7-b 기준 A2 key id(설계 §5-3) = update_common.A2_KEY_ID — A2 교체는 여기 `--delegate win-asset:…` 로 한다.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_common as uc  # noqa: E402

DELEGABLE = ("release", "feed", "win-asset")
SEVERITIES = ("advisory", "stop_seats")


def build(a):
    if not uc.KEY_ID_RE.match(a.key_id or ""):
        raise uc.PublishError("R key_id 형식")
    now = uc.trusted_now()
    keyring = uc.load_keyring(a.keyring)
    uc.find_key(keyring, "root", a.key_id, now)
    if a.prev:
        pb = open(a.prev, "rb").read()
        prev = json.loads(pb)
        if prev.get("kind") != uc.REVOCATIONS_KIND:
            raise uc.PublishError("직전 폐기문 kind")
        uc.verify_sig(keyring, "root", prev.get("key_id"), pb, open(a.prev + ".minisig", encoding="utf-8").read(), now)
        uc.check_signed_at(now, now, prev.get("signed_at"), "새 폐기문 signed_at")
        rev = int(prev["rev"]) + 1
    elif a.first:
        prev, rev = {}, 1
    else:
        raise uc.PublishError("직전 폐기문이 없으면 --first 를 명시하라(rev 1)")

    deleg = [d for d in prev.get("delegations", []) if d["key_id"] not in set(a.drop_delegation or [])]
    for spec in a.delegate or []:
        # purpose:pubkey_file:not_after_epoch
        try:
            purpose, pub_file, not_after = spec.split(":", 2)
            not_after = int(not_after)
        except ValueError:
            raise uc.PublishError("--delegate 형식 = purpose:pub파일:not_after(정수 초): %r" % spec)
        if purpose not in DELEGABLE:
            raise uc.PublishError("위임 불가 용도 %s(root·pack 불가)" % purpose)
        pub_text = open(pub_file, encoding="utf-8").read()
        kid = uc.pubkey_key_id(pub_text)
        line = [l for l in pub_text.splitlines() if l.strip() and not l.startswith("untrusted comment:")][-1].strip()
        if any(d["key_id"] == kid for d in deleg):
            raise uc.PublishError("이미 위임된 key_id %s" % kid)
        deleg.append({"key_id": kid, "purpose": purpose, "pubkey": line, "not_after": not_after})

    revoked_keys = sorted(set(prev.get("revoked_key_ids", [])) | set(a.revoke_key or []))
    if a.key_id in revoked_keys:
        raise uc.PublishError("R 키 자신을 폐기할 수 없다(R 교체 = 새 바이너리)")
    for k in a.revoke_key or []:
        if not uc.KEY_ID_RE.match(k):
            raise uc.PublishError("폐기 key_id 형식 %r" % k)

    rr = list(prev.get("revoked_releases", []))
    for spec in a.revoke_release or []:
        # component:release_seq:severity:reason_code
        try:
            comp, seq, sev, reason = spec.split(":", 3)
            seq = int(seq)
        except ValueError:
            raise uc.PublishError("--revoke-release 형식 = component:seq:severity:reason_code: %r" % spec)
        if comp not in uc.COMPONENTS or seq < 1 or sev not in SEVERITIES or not reason.strip():
            raise uc.PublishError("--revoke-release 값: %r" % spec)
        if any(r["component"] == comp and r["release_seq"] == seq for r in rr):
            raise uc.PublishError("이미 폐기된 릴리스 %s/%d" % (comp, seq))
        rr.append({"component": comp, "release_seq": seq, "severity": sev, "reason_code": reason})

    pins = prev.get("dr_pins") or {"add": [], "revoke": []}
    add = list(pins.get("add", [])) + [p.lower() for p in a.dr_pin_add or []]
    revoke = list(pins.get("revoke", [])) + [p.lower() for p in a.dr_pin_revoke or []]
    for p in add + revoke:
        if not uc.HEX40_RE.match(p):
            raise uc.PublishError("DR 핀 형식(40 hex) %r" % p)
    # 폐기 집합 단조(직전의 상위집합) — 위 구성이 직전에서 출발하므로 늘 참이어야 하고, 아니면 도구 결함이다(fail-closed).
    def rr_keys(lst):
        return {(r["component"], r["release_seq"]) for r in lst}
    if not (set(prev.get("revoked_key_ids", [])) <= set(revoked_keys)
            and rr_keys(prev.get("revoked_releases", [])) <= rr_keys(rr)
            and set((prev.get("dr_pins") or {}).get("revoke", [])) <= set(revoke)):
        raise uc.PublishError("폐기 집합이 직전보다 줄었다(단조 위반)")
    return {
        "kind": uc.REVOCATIONS_KIND,
        "rev": rev,
        "key_id": a.key_id,
        "signed_at": now,
        "delegations": deleg,
        "revoked_key_ids": revoked_keys,
        "revoked_releases": rr,
        "dr_pins": {"add": add, "revoke": revoke},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="폐기문(서명 없음) 생성 — 설계 §4-1")
    ap.add_argument("--key-id", required=True, help="R 키 key id")
    ap.add_argument("--prev", default=None, help="직전 폐기문(같은 자리에 .minisig 필수 · R 서명 암호 검증)")
    ap.add_argument("--first", action="store_true")
    ap.add_argument("--keyring", default=os.path.join(uc.REPO_ROOT, "cysjavis-pack", "trusted-keys.json"))
    ap.add_argument("--delegate", action="append", help="purpose:pub파일:not_after")
    ap.add_argument("--drop-delegation", action="append")
    ap.add_argument("--revoke-key", action="append")
    ap.add_argument("--revoke-release", action="append", help="component:seq:severity:reason_code")
    ap.add_argument("--dr-pin-add", action="append")
    ap.add_argument("--dr-pin-revoke", action="append")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        doc = build(a)
    except (uc.PublishError, OSError, ValueError, KeyError) as e:
        print("::error::폐기문 생성 거부 — %s" % e, file=sys.stderr)
        return 2
    data = uc.dump_json_bytes(doc)
    with open(a.out + ".tmp", "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(a.out + ".tmp", a.out)
    print("✅ 폐기문(서명 없음) %s · rev=%d · 위임 %d · 폐기 키 %d · 폐기 릴리스 %d"
          % (a.out, doc["rev"], len(doc["delegations"]), len(doc["revoked_key_ids"]), len(doc["revoked_releases"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
