"""`/update/` 저장소 백엔드(1.1.8 U3 2판) — 게시기·발행 게이트·시험이 **같은 배치**를 읽고 쓴다(워커 update-worker 도 같은 키).

키: obj/<sha256>(불변 객체) · ptr/<공개 경로>(본문·서명 쌍 포인터) · ptr/update/<c>/releases/_index({max_seq}).
"""
import json
import os
import subprocess
import tempfile

import update_common as uc


class FsStore:
    def __init__(self, root):
        self.root = os.path.abspath(root)

    def get(self, key):
        p = os.path.join(self.root, key)
        return open(p, "rb").read() if os.path.isfile(p) else None

    def put(self, key, data):
        p = os.path.join(self.root, key)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p))
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)  # 키 하나 = 원자 교체


class R2Store:
    def __init__(self, bucket, wrangler):
        self.bucket, self.wrangler = bucket, wrangler

    def get(self, key):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o")
            p = subprocess.run(self.wrangler + ["r2", "object", "get", "%s/%s" % (self.bucket, key), "--file", out,
                                                "--remote"], capture_output=True, text=True)
            if p.returncode != 0:
                if "not found" in (p.stderr + p.stdout).lower() or "does not exist" in (p.stderr + p.stdout).lower():
                    return None
                raise uc.PublishError("R2 get 실패 %s: %s" % (key, (p.stderr or p.stdout)[-300:]))
            return open(out, "rb").read()

    def put(self, key, data):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "o")
            open(f, "wb").write(data)
            ct = "application/json" if not key.startswith("obj/") else "application/octet-stream"
            p = subprocess.run(self.wrangler + ["r2", "object", "put", "%s/%s" % (self.bucket, key), "--file", f,
                                                "--content-type", ct, "--remote"], capture_output=True, text=True)
            if p.returncode != 0:
                raise uc.PublishError("R2 put 실패 %s: %s" % (key, (p.stderr or p.stdout)[-300:]))
        if self.get(key) != data:  # 쓰기 뒤 읽어 대조(R2 강한 일관성)
            raise uc.PublishError("R2 put 뒤 재독 불일치 %s" % key)




def archive_state(store, component):
    """보관소 (max_seq 또는 None, seq → 본문 바이트 함수)."""
    raw = store.get("ptr/update/%s/releases/_index" % component)
    top = json.loads(raw)["max_seq"] if raw else None

    def body(seq):
        pr = store.get("ptr" + uc.archive_path(component, seq))
        if not pr:
            return None
        return store.get(json.loads(pr)["json"])
    return top, body
