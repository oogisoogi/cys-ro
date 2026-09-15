#!/usr/bin/env python3
"""scripts/key-bridge-install.py 회귀 시험 — 합성 공개키·임시 저장소 사본만 쓴다(실키·네트워크 불요).

python3 scripts/tests/test_key_bridge_install.py
"""
import base64
import importlib.util
import json
import os
import shutil
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.join(_HERE, "..", "..")
_spec = importlib.util.spec_from_file_location("key_bridge_install", os.path.join(_HERE, "..", "key-bridge-install.py"))
kbi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kbi)

OLD_ID = "54FBA04AD0E0F49D"   # 현행 배포 키(저장소 실물)
A2_ID = "A4A538D8989BE09A"
P2_ID = "5BCBD38EADC4D3A8"


def pub(key_id, raw_text=False):
    line = base64.b64encode(b"Ed" + bytes.fromhex(key_id)[::-1] + bytes(range(32))).decode()
    text = "untrusted comment: minisign public key: %s\n%s\n" % (key_id, line)
    return text if raw_text else base64.b64encode(text.encode()).decode()


class KeyBridgeInstallTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = self._td.name
        for rel in ("src-tauri/tauri.conf.json", "cysjavis-pack/trusted-keys.json"):
            os.makedirs(os.path.dirname(os.path.join(self.root, rel)), exist_ok=True)
            shutil.copy(os.path.join(_REPO, rel), os.path.join(self.root, rel))

    def tearDown(self):
        self._td.cleanup()

    def _files(self, **pubs):
        paths = {}
        for name, text in pubs.items():
            p = os.path.join(self.root, name + ".pub")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
            paths[name] = p
        return paths

    def _snapshot(self):
        out = {}
        for rel in ("src-tauri/tauri.conf.json", "cysjavis-pack/trusted-keys.json"):
            with open(os.path.join(self.root, rel), "rb") as fh:
                out[rel] = fh.read()
        return out

    def _run(self, upd, pack, not_after="2030-01-01T00:00:00Z", dry=False):
        p = self._files(a2=upd, p2=pack)
        argv = ["--updater-pub", p["a2"], "--pack-pub", p["p2"], "--pack-not-after", not_after,
                "--root", self.root] + (["--dry-run"] if dry else [])
        return kbi.main(argv)

    def test_k1_installs_both_and_keeps_old_pack_key(self):
        self.assertEqual(self._run(pub(A2_ID), pub(P2_ID, raw_text=True)), 0)
        with open(os.path.join(self.root, "src-tauri/tauri.conf.json"), encoding="utf-8") as fh:
            conf = json.load(fh)
        self.assertEqual(kbi.normalize_pub(conf["plugins"]["updater"]["pubkey"], "x")[1], A2_ID)
        with open(os.path.join(self.root, "cysjavis-pack/trusted-keys.json"), encoding="utf-8") as fh:
            ring = json.load(fh)
        ids = [k["key_id"] for k in ring["keys"]]
        self.assertEqual(ids, [OLD_ID, P2_ID], "옛 키 유지 + P2 추가(이중 신뢰)가 아니다")
        for k in ring["keys"]:
            self.assertEqual(kbi.normalize_pub(k["pubkey"], "x")[1], k["key_id"])

    def test_k2_refusals_change_nothing(self):
        before = self._snapshot()
        cases = [
            (pub(A2_ID), pub(A2_ID)),              # 업데이터 == 팩
            (pub(OLD_ID), pub(P2_ID)),             # 업데이터 키 불변(브리지 아님) · 팩 키링 재사용
            (pub(A2_ID), pub(OLD_ID)),             # P2 가 이미 키링에 있음
            ("garbage", pub(P2_ID)),               # 형식 오류
        ]
        for upd, pack in cases:
            self.assertEqual(self._run(upd, pack), 1, (upd[:20], pack[:20]))
            self.assertEqual(self._snapshot(), before, "거부됐는데 파일이 바뀌었다")
        self.assertEqual(self._run(pub(A2_ID), pub(P2_ID), not_after="2030-01-01"), 1)
        self.assertEqual(self._snapshot(), before)

    def test_k3_dry_run_writes_nothing(self):
        before = self._snapshot()
        self.assertEqual(self._run(pub(A2_ID), pub(P2_ID), dry=True), 0)
        self.assertEqual(self._snapshot(), before)

    def test_k4_refuses_when_old_key_missing_from_pack_ring(self):
        ring_p = os.path.join(self.root, "cysjavis-pack/trusted-keys.json")
        with open(ring_p, "w", encoding="utf-8") as fh:
            json.dump({"keys": [{"key_id": "1111111111111111", "pubkey": pub("1111111111111111"),
                                 "not_after": "2030-01-01T00:00:00Z"}], "revoked_key_ids": []}, fh)
        before = self._snapshot()
        self.assertEqual(self._run(pub(A2_ID), pub(P2_ID)), 1)
        self.assertEqual(self._snapshot(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
