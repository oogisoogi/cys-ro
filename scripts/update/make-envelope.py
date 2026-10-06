#!/usr/bin/env python3
"""봉투(F) 생성기(1.1.8 U3 · 설계 AUTO-UPDATE-118 §6-1 봉투 표 · §4-2 `feed_rev`) — **서명 없는** 봉투 JSON 을 만든다.

봉투는 U 서명 릴리스 본문 원문과 그 서명을 base64 로 실어 나를 뿐이고 **내용을 바꿀 수 없다**(F 권한 = 만료·단계 배포·
정지). 그래서 이 생성기는 본문을 열어 보기만 하고(서식·key_id 대조) 바이트는 그대로 싣는다.

규칙(어기면 rc 2 · 봉투 0):
  · `feed_rev` = 직전 봉투 + 1(`--prev-envelope`) · 직전 봉투가 없으면 `--first` 를 명시해야 1(실수로 1 로 되돌아가 replay 거부를
    부르는 사고 차단).
  · `expires_at − signed_at` ≤ 14일(기본 14일).
  · ★2판(codex 1R #6·#19): 직전 봉투는 **U1 `cys update-verify` 통과 증표**(`release-gate.py verify --stamp`)가 그 바이트와 같을
    때만 상속한다 · 직전보다 낮거나 같은 `release_seq` 의 새 본문 = 예외 없이 거부(같은 본문 재서명은 본문 그대로라 seq 같음 허용) ·
    본문 서명은 키링 release 키로 **암호 검증** · signed_at = 신뢰 시각(인자 0)이고 직전 봉투보다 뒤.
  · `rollout_pct`·`halt` 는 명시하지 않으면 직전 봉투 값을 이어받는다(주간 재서명은 만료만 연장). 첫 봉투는 둘 다 명시.
  · 본문 `.minisig` 의 key id = 본문 `key_id`(U) · 본문 서식 = component-release · component 일치.
"""
import argparse
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_common as uc  # noqa: E402


def b64(b):
    return base64.b64encode(b).decode("ascii")


def build(a):
    if a.component not in uc.COMPONENTS or a.channel not in uc.CHANNELS:
        raise uc.PublishError("component/channel 값")
    if not uc.KEY_ID_RE.match(a.key_id or ""):
        raise uc.PublishError("F key_id 형식")
    now = uc.trusted_now()
    body_bytes = open(a.release_body, "rb").read()
    sig_text = open(a.release_sig, encoding="utf-8").read()
    body = json.loads(body_bytes)
    if body.get("kind") != uc.RELEASE_KIND or body.get("component") != a.component:
        raise uc.PublishError("본문 서식·component 불일치")
    if a.key_id == body.get("key_id"):
        raise uc.PublishError("F key_id 가 U key_id 와 같다(용도 분리 위반)")
    keyring = uc.load_keyring(a.keyring)
    uc.find_key(keyring, "feed", a.key_id, now)
    uc.verify_sig(keyring, "release", body.get("key_id"), body_bytes, sig_text, now)

    prev = None
    if a.prev_envelope:
        pb = open(a.prev_envelope, "rb").read()
        if not os.path.isfile(a.prev_envelope + ".minisig"):
            raise uc.PublishError("직전 봉투 서명(.minisig) 없음 — U1 검증 증표가 있을 수 없다")
        uc.read_stamp(a.prev_envelope, pb, open(a.prev_envelope + ".minisig", "rb").read(), by=uc.STAMP_BY_U1)
        prev = json.loads(pb)
        if prev.get("kind") != uc.ENVELOPE_KIND or prev.get("component") != a.component or prev.get("channel") != a.channel:
            raise uc.PublishError("직전 봉투 서식·component·channel 불일치")
        feed_rev = int(prev["feed_rev"]) + 1
        prev_body = json.loads(base64.b64decode(prev["release"]))
        if int(prev_body.get("release_seq", 0)) > int(body["release_seq"]):
            raise uc.PublishError("직전 봉투 release_seq %s > 새 본문 %s — 채널 내용 후퇴(예외 없음)"
                                  % (prev_body.get("release_seq"), body["release_seq"]))
        uc.check_signed_at(now, now, prev.get("signed_at"), "새 봉투 signed_at")
    elif a.first:
        feed_rev = 1
    else:
        raise uc.PublishError("직전 봉투가 없으면 --first 를 명시하라(feed_rev 1)")

    rollout = a.rollout_pct if a.rollout_pct is not None else (prev or {}).get("rollout_pct")
    halt = {"true": True, "false": False}.get(a.halt) if a.halt is not None else (prev or {}).get("halt")
    if rollout is None or halt is None:
        raise uc.PublishError("첫 봉투는 --rollout-pct 와 --halt 를 명시하라")
    if not isinstance(rollout, int) or not 0 <= rollout <= 100 or not isinstance(halt, bool):
        raise uc.PublishError("rollout_pct 0~100 · halt true/false")
    ttl = int(a.ttl_days * 86400)
    if ttl <= 0 or ttl > uc.MAX_ENVELOPE_WINDOW_SECS:
        raise uc.PublishError("유효창 0 < ttl ≤ 14일")
    env = {
        "kind": uc.ENVELOPE_KIND,
        "component": a.component,
        "channel": a.channel,
        "feed_rev": feed_rev,
        "key_id": a.key_id,
        "signed_at": now,
        "expires_at": now + ttl,
        "rollout_pct": rollout,
        "halt": halt,
        "release": b64(body_bytes),
        "release_sig": b64(sig_text.encode("utf-8")),
    }
    if a.prev_release:
        env["prev_release"] = b64(open(a.prev_release, "rb").read())
        env["prev_release_sig"] = b64(open(a.prev_release + ".minisig", "rb").read())
    return env


def main(argv=None):
    ap = argparse.ArgumentParser(description="봉투(서명 없음) 생성 — 설계 §6-1")
    ap.add_argument("--component", required=True)
    ap.add_argument("--channel", required=True)
    ap.add_argument("--release-body", required=True, help="U 서명 릴리스 본문(보관소 원문)")
    ap.add_argument("--release-sig", required=True)
    ap.add_argument("--prev-envelope", default=None)
    ap.add_argument("--first", action="store_true")
    ap.add_argument("--key-id", required=True, help="F 키 key id")
    ap.add_argument("--keyring", default=os.path.join(uc.REPO_ROOT, "cysjavis-pack", "trusted-keys.json"))
    ap.add_argument("--ttl-days", type=float, default=14)
    ap.add_argument("--rollout-pct", type=int, default=None)
    ap.add_argument("--halt", choices=("true", "false"), default=None)
    ap.add_argument("--prev-release", default=None, help="선택(§6-1 · 정본은 보관소) — <파일> 과 <파일>.minisig")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        env = build(a)
    except (uc.PublishError, OSError, ValueError, KeyError) as e:
        print("::error::봉투 생성 거부 — %s" % e, file=sys.stderr)
        return 2
    data = uc.dump_json_bytes(env)
    with open(a.out + ".tmp", "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(a.out + ".tmp", a.out)
    print("✅ 봉투(서명 없음) %s · %s/%s feed_rev=%d · 만료 %d · rollout %d · halt %s"
          % (a.out, env["component"], env["channel"], env["feed_rev"], env["expires_at"], env["rollout_pct"], env["halt"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
