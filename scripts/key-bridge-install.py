#!/usr/bin/env python3
"""키 브리지 공개키 기입 — master 가 새 키쌍을 만든 **뒤** 공개키 두 개를 저장소에 넣는다 (2026-09-15).

TICKET=key-bridge · 절차 전문 = docs/KEY-ROTATION.md

하는 일(두 파일만 · 비밀키는 절대 받지 않는다):
  ① src-tauri/tauri.conf.json  plugins.updater.pubkey  ← 새 업데이터 공개키(A2)
     (다음 판 1.0.1 을 검증할 키. 이 판 1.0.0 자산은 여전히 옛 키로 서명한다 — CI 비밀은 그대로 둔다)
  ② cysjavis-pack/trusted-keys.json  keys[]  ← 새 팩 공개키(P2) 항목 추가(옛 키 항목은 남긴다 = 이중 신뢰)

거부하는 것(전부 파일을 건드리기 **전에** 판정 — 거부 = 아무 일도 없음):
  · 공개키 형식이 minisign 이 아님 · 업데이터 키 id == 팩 키 id(분리 위반)
  · 새 업데이터 키 id 가 팩 키링의 어느 항목과 같음(업데이터 키를 팩 신뢰에 재사용 = 결합 재발)
  · 새 업데이터 키 == 현재 업데이터 키(브리지가 아니다) · P2 key id 가 키링에 이미 있음
  · not_after 가 RFC3339(끝 Z) 아님

사용:
  python3 scripts/key-bridge-install.py --updater-pub A2.key.pub --pack-pub P2.key.pub \
      --pack-not-after 2030-01-01T00:00:00Z [--dry-run] [--root <저장소 루트>]

.pub 파일은 tauri `signer generate` 산출(전체 .pub 텍스트를 base64 로 감싼 한 줄)과
minisign 원문(.pub 두 줄) 둘 다 받는다.

종료코드: 0=기입(또는 dry-run 통과) · 1=거부 · 2=인자 오류
"""
import argparse
import base64
import json
import os
import re
import sys

KEY_ID_RE = re.compile(r"^[0-9A-F]{16}$")
NOT_AFTER_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


class Refuse(Exception):
    pass


def normalize_pub(raw, what):
    """tauri 표기(base64 로 감싼 .pub 텍스트)로 정규화하고 (표기, key id) 를 돌려준다."""
    raw = raw.strip()
    if raw.startswith("untrusted comment:"):
        text = raw + "\n"
    else:
        try:
            text = base64.b64decode(raw, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as e:
            raise Refuse("%s 가 minisign 공개키가 아니다(base64/텍스트 해독 실패): %s" % (what, e))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    body = next((ln for ln in lines if not ln.startswith("untrusted comment:")), None)
    if body is None:
        raise Refuse("%s 에 키 본문 줄이 없다" % what)
    try:
        key = base64.b64decode(body, validate=True)
    except ValueError as e:
        raise Refuse("%s 키 본문이 base64 가 아니다: %s" % (what, e))
    if len(key) != 42 or key[:2] != b"Ed":
        raise Refuse("%s 키 본문이 minisign Ed25519 공개키(42바이트 · 'Ed')가 아니다" % what)
    key_id = key[2:10][::-1].hex().upper()
    canon = "untrusted comment: minisign public key: %s\n%s\n" % (key_id, body)
    return base64.b64encode(canon.encode()).decode(), key_id


def plan(root, updater_pub_raw, pack_pub_raw, not_after):
    conf_p = os.path.join(root, "src-tauri", "tauri.conf.json")
    ring_p = os.path.join(root, "cysjavis-pack", "trusted-keys.json")
    with open(conf_p, encoding="utf-8") as fh:
        conf_text = fh.read()
    with open(ring_p, encoding="utf-8") as fh:
        ring = json.load(fh)

    if not NOT_AFTER_RE.match(not_after or ""):
        raise Refuse("--pack-not-after 는 RFC3339 UTC(예 2030-01-01T00:00:00Z)여야 한다: %r" % not_after)
    a2_pub, a2_id = normalize_pub(updater_pub_raw, "업데이터 공개키(A2)")
    p2_pub, p2_id = normalize_pub(pack_pub_raw, "팩 공개키(P2)")
    if a2_id == p2_id:
        raise Refuse("업데이터 키와 팩 키가 같다(%s) — 키 분리 위반" % a2_id)

    cur_pub = json.loads(conf_text)["plugins"]["updater"]["pubkey"]
    cur_id = normalize_pub(cur_pub, "현재 업데이터 공개키")[1]
    if a2_id == cur_id:
        raise Refuse("새 업데이터 키가 현재 키와 같다(%s) — 브리지가 아니다" % a2_id)
    ring_ids = [k.get("key_id") for k in ring.get("keys", [])]
    if a2_id in ring_ids:
        raise Refuse("새 업데이터 키(%s)가 팩 키링에 있다 — 업데이터 키를 팩 신뢰에 재사용하면 결합이 재발한다" % a2_id)
    if p2_id in ring_ids:
        raise Refuse("팩 키 %s 가 키링에 이미 있다" % p2_id)
    if cur_id not in ring_ids:
        # 브리지 판의 옛 키 서명 팩을 받으려면 옛 키가 팩 키링에 명시돼 있어야 한다.
        raise Refuse("현재(옛) 키 %s 가 팩 키링에 없다 — 이대로면 브리지 판이 옛 키 서명 팩을 거부한다" % cur_id)

    if conf_text.count('"%s"' % cur_pub) != 1:
        raise Refuse("tauri.conf.json 에서 현재 pubkey 문자열이 정확히 1회 나타나지 않는다")
    new_conf = conf_text.replace('"%s"' % cur_pub, '"%s"' % a2_pub)
    ring["keys"].append({
        "key_id": p2_id,
        "pubkey": p2_pub,
        "not_after": not_after,
        "comment": "용도=pack · P2(키 브리지로 추가 — 신뢰 시작 = 이 키가 박힌 바이너리 배포 시점). docs/KEY-ROTATION.md",
    })
    new_ring = json.dumps(ring, ensure_ascii=False, indent=2) + "\n"
    return (conf_p, new_conf), (ring_p, new_ring), {"updater_old": cur_id, "updater_new": a2_id, "pack_new": p2_id}


def main(argv=None):
    ap = argparse.ArgumentParser(description="키 브리지 공개키 기입(비밀키 불요)")
    ap.add_argument("--updater-pub", required=True, help="새 업데이터 공개키(A2) .pub 경로")
    ap.add_argument("--pack-pub", required=True, help="새 팩 공개키(P2) .pub 경로")
    ap.add_argument("--pack-not-after", required=True, help="P2 만료 RFC3339 UTC")
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--dry-run", action="store_true", help="판정·요약만 출력하고 쓰지 않는다")
    args = ap.parse_args(argv)
    try:
        with open(args.updater_pub, encoding="utf-8") as fh:
            upd = fh.read()
        with open(args.pack_pub, encoding="utf-8") as fh:
            pack = fh.read()
        (conf_p, new_conf), (ring_p, new_ring), ids = plan(args.root, upd, pack, args.pack_not_after)
    except (Refuse, OSError, ValueError, KeyError) as e:
        print("거부 — %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 1
    print("업데이터 pubkey: %s → %s (1.0.0 자산은 여전히 %s 로 서명)" % (ids["updater_old"], ids["updater_new"], ids["updater_old"]))
    print("팩 키링 추가: %s (옛 키 %s 유지 = 이중 신뢰)" % (ids["pack_new"], ids["updater_old"]))
    if args.dry_run:
        print("dry-run — 파일 무변경")
        return 0
    for path, text in ((ring_p, new_ring), (conf_p, new_conf)):
        tmp = path + ".key-bridge.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    print("기입 완료 — cargo test --lib packsig 로 key_id↔pubkey 대조를 돌려라")
    return 0


if __name__ == "__main__":
    sys.exit(main())
