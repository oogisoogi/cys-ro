#!/usr/bin/env python3
"""test_agora_known_authentic — ★cysr-119-defects 2판 ⑨(codex 1R MAJOR): known 표 지문의 **진위**(제작 맥 전용 · 설계상 CI 밖).

재현(codex): 0.1.8 의 트리 지문을 임의 64-hex 로 바꿔도 깨끗한 CI 는 초록이었다 — 재계산 대조가
「사이트 zip 이 있으면」 조건부였고 0.1.4 실트리 시험은 skip 이었다.
택 ⓑ(근거: 옛 공식 zip 15개 합 ≈7.4MB 를 저장소에 고정하면 무겁고 cys-ro 공개 미러에도 오른다):
  · 이 파일 = 게시 zip 폴더(`CYS_AGORA_ZIP_DIR`)로 zip sha256(= known 주석) 과 zip_fingerprint(v2)(= known 줄)를
    **전 판** 재계산한다 · 환경 변수 없음·zip 누락 = **FAIL**(skip 금지) · 0.1.4 실트리 교체/불가침 시험도 여기.
  · CI 몫 = test_javis_counsel `test_known_file_rows` 의 manifest 정합(판본 전건·중복 0·64-hex·주석 sha 전건).
  · 등재 = scripts/lane-parity-rehearsal.sh UNREGISTERED_OK(사유 동반) · 언제 돌리나 = known 표를 고칠 때 · 판 발행 전.

실행: CYS_AGORA_ZIP_DIR=~/axdev/ai-jarvis/site/install python3 test_agora_known_authentic.py
"""
import hashlib
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True
TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)
import test_javis_counsel as tjc  # noqa: E402

jc = tjc.jc
rd = tjc.rd
PACK = os.path.dirname(tjc.BIN)
COMMENT_RE = re.compile(r"^#\s*(\d+\.\d+\.\d+)\s*=.*?sha256\s+([0-9a-f]{64})\b")


def zip_dir():
    d = os.environ.get("CYS_AGORA_ZIP_DIR", "").strip()
    if not d:
        raise AssertionError("CYS_AGORA_ZIP_DIR 없음 — 게시 zip 폴더를 지정하라(skip 금지 · 제작 맥 전용 시험)")
    d = os.path.expanduser(d)
    if not os.path.isdir(d):
        raise AssertionError("CYS_AGORA_ZIP_DIR 가 폴더가 아니다: %s" % d)
    return d


def zip_bytes(ver):
    p = os.path.join(zip_dir(), "agora-client-%s.zip" % ver)
    if not os.path.isfile(p):
        raise AssertionError("게시 zip 누락: %s" % p)
    return rd(p, "rb")


def manifest():
    """known 표 원문 → ({판본: 트리 지문}, {판본: zip sha 주석})."""
    rows, shas = {}, {}
    for line in rd(os.path.join(PACK, "install", jc.KNOWN_FILE), encoding="utf-8").splitlines():
        m = COMMENT_RE.match(line)
        if m:
            shas[m.group(1)] = m.group(2)
        p = line.split()
        if len(p) == 2 and not p[0].startswith("#"):
            rows[p[0]] = p[1]
    return rows, shas


class KnownAuthentic(unittest.TestCase):
    def test_every_old_row_recomputed_from_published_zip(self):
        rows, shas = manifest()
        bundled = jc._read_pin(PACK)["ver"]
        checked = 0
        for ver, fp in sorted(rows.items()):
            if ver == bundled:
                continue   # 동봉 판 = test_javis_counsel 이 동봉 b64 로 잰다(핀 넷째 칸 대조)
            data = zip_bytes(ver)
            self.assertEqual(hashlib.sha256(data).hexdigest(), shas.get(ver), "%s zip sha ≠ known 주석" % ver)
            self.assertEqual(jc.zip_fingerprint(data), fp, "%s 트리 지문 ≠ known 줄" % ver)
            checked += 1
        self.assertEqual(checked, len(rows) - 1, "동봉 판 말고 전 판 재계산")


class Official014RealTree(tjc.Base):
    """D-mac-3 실트리 시험(test_javis_counsel 에서 옮김 · 픽스처 = 게시 0.1.4 zip · 없으면 FAIL)."""

    V014_FP = "c41104a28be325e45a1debe2b4cd4706b9e06eb55fe3f636056830b87eb93502"

    def use_real_bundle(self):
        d = os.path.join(self.pack, "install")
        os.makedirs(d, exist_ok=True)
        pin = jc._read_pin(PACK)
        for name in ("agora-client.pin", "agora-client-%s.zip.b64" % pin["ver"], jc.KNOWN_FILE):
            tjc.shutil.copy(os.path.join(PACK, "install", name), os.path.join(d, name))
        return pin

    def old_014_tree(self, dest):
        os.makedirs(dest)
        jc._extract(zip_bytes("0.1.4"), dest)
        self.assertEqual(jc.tree_fingerprint(dest), self.V014_FP, "픽스처가 0.1.4 가 아니다")

    def lib(self, *p):
        return os.path.join(self.cfg, "lib", *p)

    def test_official_014_replaced_by_bundle(self):
        pin = self.use_real_bundle()
        self.old_014_tree(self.lib())
        self.assertEqual(jc.ensure_client(), "replaced")
        self.assertEqual(jc.tree_fingerprint(self.lib()), pin["fp"])
        ev = [tjc.json.loads(x) for x in rd(os.path.join(self.cfg, "counsel", "tick.log")).splitlines()][-1]
        self.assertEqual((ev["result"], ev["was"], ev["version"]), ("replaced", "0.1.4", pin["ver"]))
        self.assertEqual(self.sig_lines(), [], "교체 성공에 신호를 썼다")

    def test_modified_014_copy_kept(self):
        self.use_real_bundle()
        self.old_014_tree(self.lib())
        with open(self.lib("README.md"), "a", encoding="utf-8") as f:
            f.write("\n# 내가 고침\n")
        snap = jc.tree_fingerprint(self.lib())
        self.assertEqual(jc.ensure_client(), "foreign")
        self.assertEqual(jc.tree_fingerprint(self.lib()), snap, "고친 사본을 건드렸다")


if __name__ == "__main__":
    unittest.main()
