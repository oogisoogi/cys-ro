"""발행 쪽 공용 도구(1.1.8 U3 · 설계 AUTO-UPDATE-118 §4·§6-1) — 파이썬 표준 라이브러리만.

★검증 함수는 **하나뿐**이다(§6-2 `cys update-verify` · Rust). 여기 있는 검사는 「발행 쪽이 틀린 것을 만들지 않게」
앞단에서 막는 **생산자 검사**일 뿐이고, 서명 진위·판정은 반드시 `cys update-verify` 가 낸다(발행 게이트가 부른다).
그래서 이 모듈은 서명을 검증하지 않는다(ed25519 0).

같은 규칙이 Rust(U1 `src/update/{url,feed}.rs`)에 있다 — 값이 갈리면 발행 게이트의 `cys update-verify` 단계가
잡는다(생산자 검사 통과 · 검증기 거부 = 게이트 실패). 규칙 원문 = 설계 §4-4 표 · §6-1 표 · §3-12.
"""
import base64
import hashlib
import json
import re

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


def find_key(keyring, purpose, key_id):
    for k in keys_by_purpose(keyring, purpose):
        if k["key_id"] == key_id:
            if key_id in keyring.get("revoked_key_ids", []):
                raise PublishError("폐기된 key_id %s" % key_id)
            return k
    raise PublishError("키링에 %s 용도 key_id %s 없음" % (purpose, key_id))
