"""발행 쪽 공용 도구(1.1.8 U3 · 설계 AUTO-UPDATE-118 §4·§6-1) — 파이썬 표준 라이브러리만.

★검증 함수는 **하나뿐**이다(§6-2 `cys update-verify` · Rust). 여기 있는 검사는 「발행 쪽이 틀린 것을 만들지 않게」
앞단에서 막는 **생산자 검사**일 뿐이고, 서명 진위·판정은 반드시 `cys update-verify` 가 낸다(발행 게이트가 부른다).
그래서 이 모듈은 서명을 검증하지 않는다(ed25519 0).

같은 규칙이 Rust(U1 `src/update/{url,feed}.rs`)에 있다 — 값이 갈리면 발행 게이트의 `cys update-verify` 단계가
잡는다(생산자 검사 통과 · 검증기 거부 = 게이트 실패). 규칙 원문 = 설계 §4-4 표 · §6-1 표 · §3-12.
"""
import base64
import calendar
import email.utils
import hashlib
import json
import os
import re
import time
import urllib.request

COMPONENTS = ("cysr", "agora-client")
CHANNELS = ("stable", "next")
TARGETS = ("macos-arm64", "macos-x64", "windows-x64", "any")
STATE_MIGRATIONS = ("none", "additive", "breaking")
RELEASE_KIND = "component-release"
ENVELOPE_KIND = "component-update-feed"
REVOCATIONS_KIND = "update-revocations"
MAX_ENVELOPE_WINDOW_SECS = 14 * 86400
NOTES_MAX_CHARS = 80
NOTES_FORBIDDEN = ("오류", "실패", "위험", "손상", "경고")
# cysr 릴리스 본문의 필수 기판 행(§7-1 「발행 스크립트가 맥 arm64·윈 x64 행 중 하나라도 빠지면 거부(G3)」).
REQUIRED_CYSR_TARGETS = ("macos-arm64", "windows-x64")

SITE_HOST = "jarvis.godmeyou.kr"
ASSET_HOST = "github.com"
ASSET_REPO = "oogisoogi/cys-ro"
# §4-4 홉 규칙(정규화 뒤 대조 · U1 url.rs 와 같은 정규식).
SITE_PATH_RES = (
    re.compile(r"^/update/(cysr|agora-client)/(stable|next)\.json(\.minisig)?$"),
    re.compile(r"^/update/revocations\.json(\.minisig)?$"),
    re.compile(r"^/update/(cysr|agora-client)/releases/[0-9]+\.json(\.minisig)?$"),
    re.compile(r"^/install/agora-client-[0-9.]+\.zip$"),
)
ASSET_PATH_RE = re.compile(r"^/oogisoogi/cys-ro/releases/download/v[0-9][0-9A-Za-z.+-]*/[A-Za-z0-9._+-]+$")
KEY_ID_RE = re.compile(r"^[0-9A-F]{16}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
# 맥 DR 핀 = cys-local 인증서 leaf sha1(설계 §3-6 ② · 바이너리 내장 값과 같은 것). 본문 dr_pin_id 기본값.
DR_PIN_ID_CYS_LOCAL = "a426231e7dc737ee1d74962b346c23d3acacb18d"
# A2(윈 자산 · 기존 TAURI_SIGNING_PRIVATE_KEY) key id — tauri.conf.json plugins.updater.pubkey 에서 파생(§4-1 · §5-3).
A2_KEY_ID = "831CA9172204E93E"
# A2 공개키(= 1.1.8 U4 이전 tauri.conf.json plugins.updater.pubkey 값 그대로 · 공개 정보). 발행 게이트 7-b 의 암호 검증 기준 —
#   직전 판 conf 에 updater 블록이 없을 때(U4 뒤) 이 값으로 .sig 를 검증한다(codex 1R #4). 시험 핀이 파생 key id = A2_KEY_ID 를 잰다.
A2_PUBKEY = ("dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IDgzMUNBOTE3MjIwNEU5M0UKUldRKzZRUWlGNmtjZzZK"
             "dWluYWlzUytJM3RLUUIrcjJhbjRnYTFCVUt0S0RRd2cwL2NvMjJDd3QK")


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
# 통과 증표의 검증기 이름(증표 읽는 쪽이 기대값으로 대조).
STAMP_BY_U1 = "cys update-verify"
STAMP_BY_PY = "scripts/update/minisign_verify.py"


class PublishError(Exception):
    """생산자 검사 거부 — 발행하지 않는다."""


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def dump_json_bytes(obj):
    """서명 대상 바이트(결정론 — 키 정렬 · UTF-8 · 끝 줄바꿈 1). 서명은 파일 바이트 전체에 대해 한다(§6-1)."""
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def url_ok(url, hops):
    """§4-4 규칙 — `hops` ⊆ {"site", "asset"}. 정규화가 필요한 입력(대문자·끝 점·.. 등)은 **발행 쪽에서는 거부**한다
    (검증기는 정규화 뒤 대조하지만, 우리가 쓰는 url 은 처음부터 정규형이어야 한다 — 생산자 검사가 더 엄격)."""
    m = re.match(r"^https://([^/?#]+)(/[^?#]*)$", url or "")
    if not m:
        return False
    host, path = m.group(1), m.group(2)
    if "%" in path or "/./" in path or "/../" in path or path.endswith("/.") or path.endswith("/.."):
        return False
    if "site" in hops and host == SITE_HOST and any(r.match(path) for r in SITE_PATH_RES):
        return True
    if "asset" in hops and host == ASSET_HOST and ASSET_PATH_RE.match(path):
        return True
    return False


# component 별 자산 홉 — U1 feed.rs ⓜ 와 1:1(codex 1R #12): cysr = github 1홉만 · agora-client = 사이트(/install zip)만.
ASSET_HOPS = {"cysr": ("asset",), "agora-client": ("site",)}


def url_ok_for(component, field, url):
    """`field` = asset | a2_sig. 벡터 = scripts/update/url-vectors.json(U1 과 공유)."""
    if field == "a2_sig":
        return component == "cysr" and url_ok(url, ("asset",))
    return url_ok(url, ASSET_HOPS.get(component, ()))


def load_payload_excludes(path=None):
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "payload-exclude.txt")
    out = {}
    for line in open(p, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if " # " not in line:
            raise PublishError("payload-exclude 줄에 사유(' # ') 없음: %r" % line)
        rel, why = line.split(" # ", 1)
        out[rel.strip().lower()] = why.strip()
    return out


def asset_url(version, filename):
    return "https://%s/%s/releases/download/v%s/%s" % (ASSET_HOST, ASSET_REPO, version, filename)


def site_url(path):
    return "https://%s%s" % (SITE_HOST, path)


def envelope_path(component, channel):
    return "/update/%s/%s.json" % (component, channel)


def archive_path(component, release_seq):
    return "/update/%s/releases/%d.json" % (component, release_seq)


REVOCATIONS_PATH = "/update/revocations.json"


def check_notes_ko(s):
    """§3-12 MI2 — Rust `check_notes_ko` 와 같은 규칙(비어 있지 않음 · ≤80자 · 제어문자 0 · 금지 어휘 0)."""
    if not isinstance(s, str) or not s.strip():
        raise PublishError("notes_ko 비었음")
    if len(s) > NOTES_MAX_CHARS:
        raise PublishError("notes_ko 80자 초과(%d)" % len(s))
    if any(ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F for c in s):
        raise PublishError("notes_ko 제어문자")
    for w in NOTES_FORBIDDEN:
        if w in s:
            raise PublishError("notes_ko 금지 어휘 %s" % w)


def semver_core(v):
    """판 문자열의 앞 3마디(정수) — 표시·게이트용. 순서 판정의 정본은 release_seq 다(§4-2)."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$", v or "")
    if not m:
        raise PublishError("판 문자열 형식 아님: %r" % (v,))
    return tuple(int(x) for x in m.groups())


def pubkey_key_id(pubkey):
    """minisign 공개키(키라인 base64 · 또는 .pub 파일 전문 base64 · 또는 .pub 파일 텍스트) → 16자 대문자 hex key id."""
    text = pubkey.strip()
    raw = None
    try:
        dec = base64.b64decode(text, validate=False)
        if len(dec) == 42:
            raw = dec
        else:
            text = dec.decode("utf-8")
    except Exception:
        pass
    if raw is None:
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("untrusted comment:")]
        if not lines:
            raise PublishError("공개키 키라인 부재")
        raw = base64.b64decode(lines[-1])
    if len(raw) != 42 or raw[:2] != b"Ed":
        raise PublishError("minisign Ed25519 공개키가 아니다(42바이트 · 'Ed')")
    return raw[2:10][::-1].hex().upper()


def pub_file_text(pubkey):
    """키링의 pubkey(.pub 파일 전문 base64) → minisign `-p` 로 줄 수 있는 .pub 텍스트."""
    kid = pubkey_key_id(pubkey)
    try:
        dec = base64.b64decode(pubkey.strip()).decode("utf-8")
        if "untrusted comment:" in dec:
            return dec if dec.endswith("\n") else dec + "\n"
    except Exception:
        pass
    return "untrusted comment: minisign public key: %s\n%s\n" % (kid, pubkey.strip())


def sig_key_id(sig_text):
    """.minisig 텍스트 → 서명한 키의 key id(둘째 줄 = alg 2 + keynum 8 + sig 64)."""
    lines = sig_text.splitlines()
    if len(lines) < 4 or not lines[0].startswith("untrusted comment:") or not lines[2].startswith("trusted comment:"):
        raise PublishError(".minisig 형식 아님")
    raw = base64.b64decode(lines[1])
    if len(raw) != 74 or raw[:2] not in (b"ED", b"Ed"):
        raise PublishError(".minisig 서명 줄 형식 아님")
    return raw[2:10][::-1].hex().upper()


def load_keyring(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def keys_by_purpose(keyring, purpose):
    """trusted-keys.json 에서 `purpose` 키 목록(부재 = pack · §4-1). key_id 오기(공개키 파생값과 다름)는 거부."""
    out = []
    for k in keyring.get("keys", []):
        if (k.get("purpose") or "pack") != purpose:
            continue
        if pubkey_key_id(k["pubkey"]) != k["key_id"]:
            raise PublishError("키링 key_id 오기: %s ≠ 공개키 파생값" % k["key_id"])
        out.append(k)
    return out


def _not_after_epoch(k):
    try:
        return calendar.timegm(time.strptime(k.get("not_after") or "", "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        raise PublishError("키 %s not_after 부재·형식(RFC3339 Z)" % k.get("key_id"))


def find_key(keyring, purpose, key_id, now=None):
    """용도·폐기·**만료**(codex 1R #15 · U1 keys.rs find 와 같은 규칙: now ≥ not_after = 거부)를 따져 키 1개."""
    if key_id in keyring.get("revoked_key_ids", []):
        raise PublishError("폐기된 key_id %s" % key_id)
    for k in keys_by_purpose(keyring, purpose):
        if k["key_id"] == key_id:
            if (now if now is not None else int(time.time())) >= _not_after_epoch(k):
                raise PublishError("만료된 키 %s(not_after %s)" % (key_id, k.get("not_after")))
            return k
    raise PublishError("키링에 %s 용도 key_id %s 없음" % (purpose, key_id))


# ── 개발(시험) 모드 · 신뢰 시각 ─────────────────────────────────────────────────────
def dev_mode():
    """CYS_SIGN_DEV=1 = 파이썬 도구의 시험 시각(CYS_TEST_NOW) 허용만 — 서명 의식 셸 스크립트는 이 값을 읽지 않는다(3판 · 2R #3)."""
    return os.environ.get("CYS_SIGN_DEV") == "1"


TIME_SOURCE = "https://%s/" % SITE_HOST
MAX_CLOCK_SKEW_SECS = 300


def trusted_now():
    """서명 시각(codex 1R #15 — 생성기는 signed_at 을 인자로 받지 않는다): 벽시계를 HTTPS 응답 Date 와 대조해 5분 넘게
    다르면 거부(U1 N13 과 같은 생각 · 발행 쪽은 더 엄격). 대조 못 하면(오프라인) 거부 — 서명 의식은 온라인 기기에서 한다.
    개발 모드만 `CYS_TEST_NOW` 덮어쓰기·대조 생략."""
    if dev_mode():
        v = os.environ.get("CYS_TEST_NOW")
        return int(v) if v else int(time.time())
    now = int(time.time())
    try:
        req = urllib.request.Request(TIME_SOURCE, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as r:
            date = r.headers.get("Date")
    except Exception as e:
        raise PublishError("신뢰 시각 대조 불가(%s 응답 없음: %s) — 네트워크 연결 뒤 다시" % (TIME_SOURCE, e))
    if not date:
        raise PublishError("신뢰 시각 대조 불가(Date 헤더 없음)")
    remote = int(calendar.timegm(email.utils.parsedate_tz(date)[:9]))
    if abs(remote - now) > MAX_CLOCK_SKEW_SECS:
        raise PublishError("벽시계 의심: 이 기기 %d ↔ HTTPS Date %d (차 %d초 > %d)" % (now, remote, now - remote, MAX_CLOCK_SKEW_SECS))
    return now


def check_signed_at(signed_at, now, prev_signed_at=None, what="signed_at"):
    """미래 시각(1분 넘게) · 직전 서명 시각 역행 거부(codex 1R #15)."""
    if not isinstance(signed_at, int):
        raise PublishError("%s 정수 아님" % what)
    if signed_at > now + 60:
        raise PublishError("%s %d 가 미래(지금 %d)" % (what, signed_at, now))
    if prev_signed_at is not None and signed_at <= int(prev_signed_at):
        raise PublishError("%s %d ≤ 직전 %d (시각 역행)" % (what, signed_at, int(prev_signed_at)))


# ── 폐기문 후계 규칙(codex 2R #5 · 생성기·게이트·게시기 공용) ─────────────────────────────
SEVERITY_RANK = {"advisory": 0, "stop_seats": 1}


def check_revocations_successor(prev, new):
    """직전 폐기문의 항목을 **전체 그대로** 보존해야 한다(동일성 비교). 허용되는 변화는 신뢰를 **줄이는** 쪽뿐:
    폐기 key·릴리스·DR 핀 폐기 추가 · 릴리스 severity `advisory → stop_seats` 승격(역방향 거부) · 위임/DR 추가 핀 빼기.
    reason_code 변경 · 위임 항목 변경(공개키·만료 연장 등) = 거부."""
    if not set(prev.get("revoked_key_ids", [])) <= set(new.get("revoked_key_ids", [])):
        raise PublishError("폐기 key 가 직전보다 줄었다(단조 위반)")
    nr = {(r.get("component"), r.get("release_seq")): r for r in new.get("revoked_releases", [])}
    for r in prev.get("revoked_releases", []):
        k = (r.get("component"), r.get("release_seq"))
        n = nr.get(k)
        if n is None:
            raise PublishError("폐기 릴리스 %s/%s 가 빠졌다(단조 위반)" % k)
        if n.get("reason_code") != r.get("reason_code"):
            raise PublishError("폐기 릴리스 %s/%s reason_code 변경 %r → %r(거부)" % (k + (r.get("reason_code"), n.get("reason_code"))))
        a, b = SEVERITY_RANK.get(r.get("severity")), SEVERITY_RANK.get(n.get("severity"))
        if a is None or b is None or b < a:
            raise PublishError("폐기 릴리스 %s/%s severity %s → %s(약화·미지 = 거부 · 허용 = advisory→stop_seats)"
                               % (k + (r.get("severity"), n.get("severity"))))
        if {x: y for x, y in r.items() if x != "severity"} != {x: y for x, y in n.items() if x != "severity"}:
            raise PublishError("폐기 릴리스 %s/%s 항목이 바뀌었다(severity 승격 말고는 동일해야 한다)" % k)
    nd = {d.get("key_id"): d for d in new.get("delegations", [])}
    for d in prev.get("delegations", []):
        if d.get("key_id") in nd and nd[d.get("key_id")] != d:
            raise PublishError("위임 %s 항목이 바뀌었다(빼기만 허용 · 바꾸려면 빼고 새 키로)" % d.get("key_id"))
    pp, np_ = prev.get("dr_pins") or {}, new.get("dr_pins") or {}
    if not set(pp.get("revoke", [])) <= set(np_.get("revoke", [])):
        raise PublishError("DR 핀 폐기가 직전보다 줄었다(단조 위반)")


# ── 암호 검증 + 통과 증표(codex 1R #4) ───────────────────────────────────────────────
def verify_sig(keyring, purpose, key_id, data, sig_text, now):
    """키링의 `purpose` 키(만료·폐기 반영)로 minisign 서명을 **암호 검증**. 서명 key id = 기대 key id 도 강제."""
    import minisign_verify as mv
    k = find_key(keyring, purpose, key_id, now)
    try:
        got = mv.verify(k["pubkey"], data, sig_text)
    except mv.VerifyFail as e:
        raise PublishError("%s 서명 검증 실패(key %s): %s" % (purpose, key_id, e))
    if got != key_id:
        raise PublishError("서명 key id %s ≠ 기대 %s" % (got, key_id))
    return got


def stamp_path(doc_path):
    return doc_path + ".verified.json"


def write_stamp(doc_path, sig_bytes, key_id, purpose, by, now, extra=None):
    """통과 증표 = 검증한 **바이트**의 sha256(본문·서명) + 키 id + 용도 + 시각 + 검증기. 게시기는 이것이 지금 파일과 같을 때만 쓴다."""
    st = {"doc_sha256": sha256_bytes(open(doc_path, "rb").read()), "sig_sha256": sha256_bytes(sig_bytes),
          "key_id": key_id, "purpose": purpose, "verified_at": now, "by": by}
    st.update(extra or {})
    with open(stamp_path(doc_path), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, sort_keys=True)
    return st


def read_stamp(doc_path, doc_bytes, sig_bytes, by=None):
    try:
        st = json.load(open(stamp_path(doc_path), encoding="utf-8"))
    except (OSError, ValueError):
        raise PublishError("검증 증표 없음: %s (발행 게이트를 먼저 통과시켜라)" % stamp_path(doc_path))
    if st.get("doc_sha256") != sha256_bytes(doc_bytes) or st.get("sig_sha256") != sha256_bytes(sig_bytes):
        raise PublishError("검증 증표가 지금 파일과 다르다(검증 뒤 바뀜): %s" % doc_path)
    if by and st.get("by") != by:
        raise PublishError("검증 증표의 검증기 %r ≠ 기대 %r" % (st.get("by"), by))
    return st
