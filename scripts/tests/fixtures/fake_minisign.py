#!/usr/bin/env python3
"""★시험 전용 minisign 대역(1.1.8 U3 · TICKET=cysr-118-u3-publish) — 실키 0.

왜 있는가: 발행 쪽 스크립트(U 의식 `scripts/update/sign-release.sh` · R 의식 · 발행 게이트)를 **진짜 서명**으로
시험해야 하는데, 이 기계·CI 러너에는 `minisign` 이 없고 파이썬 표준 라이브러리에는 ed25519 가 없다. 그래서
RFC 8032 참조 구현(순수 파이썬)으로 **minisign 과 같은 바이트 형식**의 공개키·서명을 만든다 — 우리 검증기
(`packsig::verify_minisign` → `minisign_verify`)가 그대로 받아들인다(시험이 그것을 잰다).

★이 파일이 다루는 비밀키는 **시험 안에서 만든 일회용 키**뿐이다. 비밀키 파일 형식은 minisign 의 암호화 상자가
아니라 이 대역 전용 평문(첫 줄 `fake-minisign test secret key`)이라, 진짜 minisign 키 파일을 줘도 읽지 않는다
(실키를 이 도구로 쓰는 사고를 형식으로 막는다).

CLI(진짜 minisign 의 쓰는 갈래만 같은 철자로):
  fake_minisign.py -G -p <pub> -s <key> [-W]
  fake_minisign.py -S -s <key> -m <file> [-x <sig>] [-t <trusted comment>]
  fake_minisign.py -V -p <pub> -m <file> [-x <sig>]
"""
import argparse
import base64
import hashlib
import os
import sys

# ── RFC 8032 §6 참조 구현(느리지만 정확 · 시험용) ─────────────────────────────────────
_p = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_d = -121665 * pow(121666, _p - 2, _p) % _p
_I = pow(2, (_p - 1) // 4, _p)


def _xrecover(y):
    xx = (y * y - 1) * pow(_d * y * y + 1, _p - 2, _p)
    x = pow(xx, (_p + 3) // 8, _p)
    if (x * x - xx) % _p != 0:
        x = (x * _I) % _p
    if x % 2 != 0:
        x = _p - x
    return x


_By = 4 * pow(5, _p - 2, _p) % _p
_B = (_xrecover(_By), _By, 1, _xrecover(_By) * _By % _p)


def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C = 2 * P[3] * Q[3] * _d % _p
    D = 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _enc(P):
    zi = pow(P[2], _p - 2, _p)
    x, y = P[0] * zi % _p, P[1] * zi % _p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _dec(s):
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _xrecover(y)
    if (x & 1) != sign:
        x = _p - x
    return (x, y, 1, x * y % _p)


def _h(m):
    return hashlib.sha512(m).digest()


def _secret_expand(seed):
    h = _h(seed)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def ed25519_public(seed):
    a, _ = _secret_expand(seed)
    return _enc(_mul(a, _B))


def ed25519_sign(seed, msg):
    a, prefix = _secret_expand(seed)
    A = _enc(_mul(a, _B))
    r = int.from_bytes(_h(prefix + msg), "little") % _L
    R = _enc(_mul(r, _B))
    k = int.from_bytes(_h(R + A + msg), "little") % _L
    s = (r + k * a) % _L
    return R + int.to_bytes(s, 32, "little")


def ed25519_verify(pub, msg, sig):
    if len(sig) != 64:
        return False
    R, s = sig[:32], int.from_bytes(sig[32:], "little")
    if s >= _L:
        return False
    A = _dec(pub)
    k = int.from_bytes(_h(R + pub + msg), "little") % _L
    return _enc(_mul(s, _B)) == _enc(_add(_dec(R), _mul(k, A)))


# ── minisign 형식 ───────────────────────────────────────────────────────────────────
SECRET_MAGIC = "fake-minisign test secret key"


def key_id_hex(keynum):
    """minisign 표기(리틀엔디언 keynum 을 뒤집은 16자 대문자 hex)."""
    return keynum[::-1].hex().upper()


def generate(pub_path, key_path):
    seed = os.urandom(32)
    keynum = os.urandom(8)
    pk = ed25519_public(seed)
    kid = key_id_hex(keynum)
    with open(pub_path, "w", encoding="utf-8") as f:
        f.write("untrusted comment: minisign public key: %s\n" % kid)
        f.write(base64.b64encode(b"Ed" + keynum + pk).decode() + "\n")
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(SECRET_MAGIC + "\n")
        f.write(base64.b64encode(keynum + seed).decode() + "\n")
    return kid


def load_secret(key_path):
    with open(key_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines or lines[0] != SECRET_MAGIC:
        raise SystemExit("fake-minisign: 시험 키 파일이 아니다(진짜 minisign 키는 읽지 않는다): %s" % key_path)
    raw = base64.b64decode(lines[1])
    return raw[:8], raw[8:]


def sign(key_path, msg_path, sig_path, trusted):
    keynum, seed = load_secret(key_path)
    with open(msg_path, "rb") as f:
        msg = f.read()
    sig = ed25519_sign(seed, hashlib.blake2b(msg, digest_size=64).digest())
    tc = trusted.encode()
    gsig = ed25519_sign(seed, sig + tc)
    with open(sig_path, "w", encoding="utf-8") as f:
        f.write("untrusted comment: signature from fake-minisign test key\n")
        f.write(base64.b64encode(b"ED" + keynum + sig).decode() + "\n")
        f.write("trusted comment: %s\n" % trusted)
        f.write(base64.b64encode(gsig).decode() + "\n")


def verify(pub_path, msg_path, sig_path):
    with open(pub_path, encoding="utf-8") as f:
        pl = [l for l in f.read().splitlines() if l and not l.startswith("untrusted comment:")]
    praw = base64.b64decode(pl[-1])
    with open(sig_path, encoding="utf-8") as f:
        sl = f.read().splitlines()
    sraw = base64.b64decode(sl[1])
    tc = sl[2][len("trusted comment: "):].encode()
    gsig = base64.b64decode(sl[3])
    if praw[2:10] != sraw[2:10]:
        return False
    with open(msg_path, "rb") as f:
        msg = f.read()
    m = hashlib.blake2b(msg, digest_size=64).digest() if sraw[:2] == b"ED" else msg
    return ed25519_verify(praw[10:], m, sraw[10:]) and ed25519_verify(praw[10:], sraw[10:] + tc, gsig)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fake-minisign")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("-G", action="store_true")
    g.add_argument("-S", action="store_true")
    g.add_argument("-V", action="store_true")
    ap.add_argument("-p")
    ap.add_argument("-s")
    ap.add_argument("-m")
    ap.add_argument("-x")
    ap.add_argument("-t", default="fake-minisign test signature")
    ap.add_argument("-W", action="store_true")
    a = ap.parse_args(argv)
    if a.G:
        print(generate(a.p, a.s))
        return 0
    if a.S:
        sign(a.s, a.m, a.x or a.m + ".minisig", a.t)
        return 0
    ok = verify(a.p, a.m, a.x or a.m + ".minisig")
    print("Signature and comment signature verified" if ok else "Signature verification failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
