"""`/update/` 저장소 백엔드(1.1.8 U3 3판 · codex 2R #8) — 게시기·발행 게이트·시험·워커가 **같은 배치**를 읽고 쓴다.

키(워커 update-worker 도 같은 키를 읽는다):
  obj/<sha256>                         불변 객체(본문·서명 바이트) — 새로 쓸 때 `If-None-Match: *`(있으면 바이트 대조만)
  ptr/update/<c>/<ch>.json             봉투 포인터 {json, sig, json_sha256, sig_sha256, …}       — `If-Match: <ETag>` 교체
  ptr/update/revocations.json          폐기문 포인터(같은 모양)                                    — 〃
  ptr/update/<c>/releases/_gen         보관소 **세대 포인터** {max_seq, seqs: {"<seq>": 포인터}}  — 〃(포인터와 색인을 한 객체로
                                       합쳐 한 번의 CAS 로 바뀐다 · 2판의 「포인터 → 색인」 두 쓰기 사이 중단 상태가 없다)
CAS(비교 후 교환): `get` 이 (바이트, ETag) 를 주고 `cas(key, data, etag)` 는 지금 ETag 가 그 값일 때만 쓴다(`etag=None` = 없을
때만). 삭제 API 는 쓰지 않는다 — 없앰 = 묘비 포인터(TOMBSTONE) 조건부 PUT(4판 · R2 조건부 DELETE 미지원). 어긋나면 CasFail — 게시기가 「다른 게시자가 먼저 바꿨다」로 거부한다(재시도는 처음부터 = 재검사).
백엔드:
  FsStore(root)   파일 시스템(시험·드라이런) · ETag = sha256 · CAS = 저장소 잠금(flock) 안 비교+원자 교체(같은 호스트 한정).
  S3Store(...)    R2 S3 호환 API(표준 라이브러리 SigV4 · 조건부 PUT 헤더만) · 자격 = master 로컬 env
                  `R2_ACCOUNT_ID`·`R2_ACCESS_KEY_ID`·`R2_SECRET_ACCESS_KEY`(값 = 저장소 밖 · 워커는 읽기 전용 바인딩).
"""
import datetime
import fcntl
import hashlib
import hmac
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request

import update_common as uc


class CasFail(Exception):
    """조건부 쓰기 실패(지금 ETag ≠ 기대 · 또는 이미 있음)."""


# ★4판(Fable 3R MAJOR-3): R2 DeleteObject 는 조건부(If-Match)를 지원하지 않는다 → 「없앰」 = **묘비 포인터를 조건부 PUT**.
#   읽는 쪽(게시기·게이트·워커)은 묘비를 「없음」으로 읽고, 다음 게시는 그 묘비의 ETag 로 CAS 한다(삭제 API 를 쓰지 않는다).
TOMBSTONE = b'{"tombstone": true}\n'


def load(store, key):
    """(문서 dict 또는 None(없음·묘비), 원 바이트, ETag)."""
    raw, etag = store.get(key)
    if raw is None or raw == TOMBSTONE:
        return None, raw, etag
    return json.loads(raw), raw, etag


def gen_key(component):
    return "ptr/update/%s/releases/_gen" % component


class FsStore:
    def __init__(self, root):
        self.root = os.path.abspath(root)

    def _p(self, key):
        if ".." in key.split("/"):
            raise uc.PublishError("키 경로 탈출: %s" % key)
        return os.path.join(self.root, key)

    def get(self, key):
        p = self._p(key)
        if not os.path.isfile(p):
            return None, None
        b = open(p, "rb").read()
        return b, hashlib.sha256(b).hexdigest()

    def _locked(self):
        os.makedirs(self.root, exist_ok=True)
        f = open(os.path.join(self.root, ".cas.lock"), "a")
        fcntl.flock(f, fcntl.LOCK_EX)
        return f

    def cas(self, key, data, etag):
        with self._locked():
            _, cur = self.get(key)
            if cur != etag:
                raise CasFail("%s: 지금 ETag %s ≠ 기대 %s" % (key, cur, etag))
            p = self._p(key)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p))
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, p)
        return hashlib.sha256(data).hexdigest()

    def describe(self):
        return "--fs %s" % self.root


class S3Store:
    """R2 S3 호환 API — `If-None-Match: *` / `If-Match: "<etag>"` 조건부 **PUT 만**(R2 지원 · DELETE 조건부는 미지원이라 안 쓴다).
    ⚠실측 0(이 기계에 R2 자격 없음) — 시험은 같은 의미의 로컬 가짜 S3 서버로 잰다(`endpoint` 인자)."""

    def __init__(self, bucket, endpoint=None, access_key=None, secret_key=None, region="auto"):
        acct = os.environ.get("R2_ACCOUNT_ID", "")
        self.endpoint = (endpoint or "https://%s.r2.cloudflarestorage.com" % acct).rstrip("/")
        self.bucket, self.region = bucket, region
        self.ak = access_key or os.environ.get("R2_ACCESS_KEY_ID", "")
        self.sk = secret_key or os.environ.get("R2_SECRET_ACCESS_KEY", "")
        if not (self.ak and self.sk) or (not endpoint and not acct):
            raise uc.PublishError("R2 자격 없음 — env R2_ACCOUNT_ID·R2_ACCESS_KEY_ID·R2_SECRET_ACCESS_KEY(master 로컬)")

    def _req(self, method, key, data=b"", headers=None):
        u = urllib.parse.urlsplit(self.endpoint)
        path = "/%s/%s" % (self.bucket, urllib.parse.quote(key, safe="/-_.~"))
        now = datetime.datetime.now(datetime.timezone.utc)
        amz, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
        ph = hashlib.sha256(data).hexdigest()
        h = {"host": u.netloc, "x-amz-content-sha256": ph, "x-amz-date": amz}
        h.update({k.lower(): v for k, v in (headers or {}).items()})
        names = sorted(h)
        creq = "\n".join([method, path, "", "".join("%s:%s\n" % (k, str(h[k]).strip()) for k in names),
                          ";".join(names), ph])
        scope = "%s/%s/s3/aws4_request" % (day, self.region)
        sts = "\n".join(["AWS4-HMAC-SHA256", amz, scope, hashlib.sha256(creq.encode()).hexdigest()])
        k = ("AWS4" + self.sk).encode()
        for part in (day, self.region, "s3", "aws4_request"):
            k = hmac.new(k, part.encode(), hashlib.sha256).digest()
        sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
        h["authorization"] = "AWS4-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s" % (
            self.ak, scope, ";".join(names), sig)
        req = urllib.request.Request(self.endpoint + path, data=data if method == "PUT" else None, method=method,
                                     headers={**{k: v for k, v in h.items() if k != "host"},
                                              "User-Agent": uc.HTTP_USER_AGENT})  # 서명 밖 헤더(SignedHeaders 무관)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read(), (r.headers.get("ETag") or "").strip('"')
        except urllib.error.HTTPError as e:
            return e.code, e.read(), (e.headers.get("ETag") or "").strip('"')

    def get(self, key):
        st, body, etag = self._req("GET", key)
        if st == 404:
            return None, None
        if st != 200:
            raise uc.PublishError("R2 GET %s = HTTP %d" % (key, st))
        return body, etag

    def cas(self, key, data, etag):
        cond = {"If-None-Match": "*"} if etag is None else {"If-Match": '"%s"' % etag}
        st, body, new = self._req("PUT", key, data, dict(cond, **{"Content-Type": "application/json"
                                                                   if key.startswith("ptr/") else "application/octet-stream"}))
        if st == 412:
            raise CasFail("%s: 조건부 PUT 412(%s)" % (key, cond))
        if st != 200:
            raise uc.PublishError("R2 PUT %s = HTTP %d %s" % (key, st, body[:200]))
        got, _ = self.get(key)  # 쓰기 뒤 재독(R2 강한 일관성)
        if got != data:
            raise CasFail("%s: PUT 뒤 재독 불일치(동시 교체)" % key)
        return new

    def describe(self):
        return "--r2 %s" % self.bucket


def put_object(store, key, data):
    """불변 객체: 없으면 `If-None-Match: *` 로 만들고, 있으면 바이트가 같아야 한다(다르면 저장소 손상)."""
    cur, _ = store.get(key)
    if cur is None:
        try:
            store.cas(key, data, None)
            return
        except CasFail:
            cur, _ = store.get(key)
    if cur != data:
        raise CasFail("불변 객체 %s 가 다른 바이트로 있다(저장소 손상)" % key)


def archive_state(store, component):
    """보관소 (max_seq 또는 None, seq → 본문 바이트 함수, seq → 서명 바이트 함수) — 세대 포인터 하나에서."""
    g = load(store, gen_key(component))[0] or {"max_seq": None, "seqs": {}}

    def obj(seq, field):
        e = g["seqs"].get(str(seq))
        return store.get(e[field])[0] if e else None
    return g["max_seq"], (lambda seq: obj(seq, "json")), (lambda seq: obj(seq, "sig"))
