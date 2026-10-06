"""minisign 서명 **검증 전용**(1.1.8 U3 2판 · codex 1R #4) — 파이썬 표준 라이브러리만 · 비밀키 0 · 서명 기능 0.

왜 파이썬인가: 발행 게이트·게시기는 CI 러너(우분투·맥)와 master 기기에서 도는데 `minisign` CLI 가 기본 설치돼 있지 않다
(이 기계 실측 `minisign not found`). 그래서 RFC 8032 §6 참조 구현으로 ed25519 **검증**만 한다 — 검증은 비밀이 없어
시간 부채널 문제가 없고, 형식은 minisign 그대로(공개키 `Ed`+keynum+pk · 서명 `ED`(BLAKE2b-512 선해시) 또는 `Ed`(원문) +
keynum + sig + trusted comment 의 전역 서명). 시험이 같은 서명을 U1 `cys update-verify`(minisign_verify 크레이트)에도 통과시켜
두 검증기가 같은 답을 내는지 잰다.

★클라이언트 판정의 정본은 여전히 `cys update-verify` 하나다(§6-2). 이 모듈은 「발행 쪽이 위조·오기 서명을 게시하지 않게」
막는 생산자 쪽 검증이다.
"""
import base64
import hashlib

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
B = (_xrecover(_By), _By, 1, _xrecover(_By) * _By % _p)


def add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _p
    Bv = (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C = 2 * P[3] * Q[3] * _d % _p
    D = 2 * P[2] * Q[2] % _p
    E, F, G, H = Bv - A, D - C, D + C, Bv + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = add(Q, P)
        P = add(P, P)
        s >>= 1
    return Q


def enc(P):
    zi = pow(P[2], _p - 2, _p)
    x, y = P[0] * zi % _p, P[1] * zi % _p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def dec(s):
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= _p:
        raise ValueError("점 y ≥ p")
    x = _xrecover(y)
    if (x * x * (_d * y * y + 1) - (y * y - 1)) % _p != 0:
        raise ValueError("곡선 밖 점")
    if (x & 1) != sign:
        x = _p - x
    return (x, y, 1, x * y % _p)


def ed25519_verify(pub, msg, sig):
    if len(pub) != 32 or len(sig) != 64:
        return False
    s = int.from_bytes(sig[32:], "little")
    if s >= _L:
        return False
    try:
        A, R = dec(pub), dec(sig[:32])
    except ValueError:
        return False
    k = int.from_bytes(hashlib.sha512(sig[:32] + pub + msg).digest(), "little") % _L
    return enc(mul(s, B)) == enc(add(R, mul(k, A)))


class VerifyFail(Exception):
    pass


def _pub_raw(pubkey):
    """공개키(키라인 base64 · .pub 파일 텍스트 · 그 텍스트의 base64) → 42바이트 raw."""
    text = pubkey.strip()
    try:
        d = base64.b64decode(text)
        if len(d) == 42:
            return d
        text = d.decode("utf-8")
    except Exception:
        pass
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("untrusted comment:")]
    if not lines:
        raise VerifyFail("공개키 키라인 부재")
    raw = base64.b64decode(lines[-1])
    if len(raw) != 42 or raw[:2] != b"Ed":
        raise VerifyFail("minisign Ed25519 공개키 아님")
    return raw


def verify(pubkey, data, sig_text):
    """minisign 서명 검증 — 통과하면 서명 key id(16자 대문자 hex), 아니면 VerifyFail.

    `sig_text` = .minisig 텍스트(4줄) 또는 그 전체의 base64(tauri `.sig` 표기)."""
    if isinstance(sig_text, bytes):
        sig_text = sig_text.decode("utf-8", "replace")
    if not sig_text.lstrip().startswith("untrusted comment:"):
        try:
            sig_text = base64.b64decode(sig_text.strip()).decode("utf-8")
        except Exception:
            raise VerifyFail("서명 형식 아님(minisign 텍스트도 그 base64 도 아님)")
    lines = sig_text.splitlines()
    if len(lines) < 4 or not lines[0].startswith("untrusted comment:") or not lines[2].startswith("trusted comment: "):
        raise VerifyFail("minisign 서명 4줄 형식 아님")
    try:
        sraw = base64.b64decode(lines[1], validate=True)
        gsig = base64.b64decode(lines[3], validate=True)
    except Exception:
        raise VerifyFail("서명 줄 base64 아님")
    if len(sraw) != 74 or sraw[:2] not in (b"ED", b"Ed") or len(gsig) != 64:
        raise VerifyFail("서명 줄 길이·알고리즘")
    praw = _pub_raw(pubkey)
    if praw[2:10] != sraw[2:10]:
        raise VerifyFail("서명 key id ≠ 공개키 key id")
    msg = hashlib.blake2b(data, digest_size=64).digest() if sraw[:2] == b"ED" else data
    if not ed25519_verify(praw[10:], msg, sraw[10:]):
        raise VerifyFail("서명 검증 실패(본문)")
    tc = lines[2][len("trusted comment: "):].encode("utf-8")
    if not ed25519_verify(praw[10:], sraw[10:] + tc, gsig):
        raise VerifyFail("서명 검증 실패(trusted comment 전역 서명)")
    return praw[2:10][::-1].hex().upper()
