#!/usr/bin/env python3
"""1.1.8 U3 발행 쪽 시험(TICKET=cysr-118-u3-publish) — 실키 0 · 격리 tmp · 표준 라이브러리만.

대상: scripts/update/{make-release-json,make-envelope,make-revocations,publish-site,release-gate}.py ·
      sign-release.sh · sign-revocations.sh(맥 = hdiutil 로 만든 **진짜 마운트**를 가짜 매체로) · bundle-prep 수리 핀 ·
      release-verify 7-b A2 기준 · NSIS ⓪-a 소스 핀.
서명 = scripts/tests/fixtures/fake_minisign.py(RFC 8032 · minisign 형식 · 시험 키만).
U1 왕복: env `CYS_UPDATE_VERIFY_BIN` = `update-verify` 를 가진 **디버그** cys(시험 키링·NOW 덮어쓰기는 디버그 빌드만 읽음).
  없으면 그 묶음은 「U1 미머지 — 미실행」을 크게 찍고 건너뛴다(U1 머지 뒤 CI 가 이 env 를 줘야 한다 · HANDOFF-U3).
각 거부 조건은 뮤테이션 1개로 음성 대조한다(양성 = 통과 · 음성 = 정확히 그 이유로 거부).
"""
import base64
import hashlib
import importlib.util
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPD = os.path.join(ROOT, "scripts", "update")
FAKE = os.path.join(ROOT, "scripts", "tests", "fixtures", "fake_minisign.py")
# 1.1.18(838f24421) scripts/update/sign-release.sh 의 바이트 동일 사본 + 그 sha256(test_co_l3_no_flag_same_as_1118 의 비교 대상).
SIGN_1118_FIXTURE = os.path.join(ROOT, "scripts", "tests", "fixtures", "sign-release-1.1.18-838f24421.sh")
SIGN_1118_SHA256 = "09d76522ee0f9fdad252488a91deea6c08763cc0cc89fe2ccb7e72800b51ad27"
sys.path.insert(0, UPD)
sys.path.insert(0, os.path.dirname(FAKE))
import update_common as uc  # noqa: E402
import fake_minisign as fm  # noqa: E402

VERIFY_BIN = os.environ.get("CYS_UPDATE_VERIFY_BIN", "")
# CI(맥 레인)는 1 을 준다 — U1 왕복·hdiutil 매체 묶음이 **반드시** 돈다: 전제 부재 = 모듈 오류 · 건너뜀 1건이라도 = 실패(codex 1R #17).
REQUIRE_ALL = os.environ.get("CYS_U3_REQUIRE_ALL") == "1"
NOW = 1790000000
# 시험 전용 모드(실 키 서명 거부 · 신뢰 시각 덮어쓰기 · 가짜 minisign/매체 허용 — codex 1R #3·#15)
os.environ["CYS_SIGN_DEV"] = "1"
os.environ["CYS_TEST_NOW"] = str(NOW)


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def setUpModule():
    """REQUIRE_ALL 전제 확인 — 건너뛸 이유가 생기기 전에 크게 실패한다(VERIFY_BIN 실행 가능 · hdiutil 로 매체 실제 마운트)."""
    if not REQUIRE_ALL:
        return
    bad = []
    if not VERIFY_BIN or not os.access(VERIFY_BIN, os.X_OK):
        bad.append("CYS_UPDATE_VERIFY_BIN 실행 파일 없음: %r" % VERIFY_BIN)
    elif run([VERIFY_BIN, "update-verify", "--help"]).returncode != 0:
        bad.append("CYS_UPDATE_VERIFY_BIN 에 update-verify 없음(U1 미머지 cys?): %s" % VERIFY_BIN)
    if sys.platform != "darwin" or not shutil.which("hdiutil"):
        bad.append("hdiutil 없음(맥 매체 묶음 실행 불가)")
    else:
        bad.extend(media_probe_failures())
    if bad:
        raise RuntimeError("CYS_U3_REQUIRE_ALL=1 전제 부재 — " + " · ".join(bad))


def media_probe_failures(runner=None, delay=1.0):
    """setUpModule 의 매체 전제 확인(hdiutil 로 실제 생성·마운트) — 반환 = 실패 사유 목록(빈 목록 = 통과).
    1.1.9: create·attach 를 hdiutil_retry 로 부른다 — 맥 러너의 간헐 실패 1회는 사유를 찍고 다시 하고, 2회 실패는
    종전처럼 모듈 오류다(건너뛰기 없음 · REQUIRE_ALL 계약 그대로)."""
    d = tempfile.mkdtemp(prefix="u3-req-")
    stuck = False
    try:
        dmg, mnt = os.path.join(d, "p.dmg"), os.path.join(d, "mnt")
        os.makedirs(mnt)
        for args, partial in ((["create", "-size", "1m", "-fs", "HFS+", "-volname", "U3PROBE", "-quiet", dmg], dmg),
                              (["attach", dmg, "-mountpoint", mnt, "-nobrowse", "-quiet"], None)):
            reasons = hdiutil_retry(args, partial=partial, runner=runner, delay=delay)
            if reasons:
                return ["hdiutil 매체 생성·마운트 실패(hdiutil %s · 2회): %s" % (args[0], " | ".join(reasons))]
        # 1.1.10: detach 도 rc 를 본다 — 1회 재시도 · 2회 실패 = 사유가 실린 모듈 오류(마운트가 남은 채 통과 금지).
        # 1.1.11(review-a B3): 재시도는 -force · 2회 실패면 마운트가 남았으므로 d 를 rmtree 하지 않는다(볼륨 안으로 들어간다).
        reasons = hdiutil_retry(["detach", mnt, "-quiet"], runner=runner, delay=delay, force_retry=True)
        if reasons:
            stuck = True
            return ["hdiutil 매체 분리 실패(hdiutil detach · 2회 · 마운트가 남아 %s 를 지우지 않음): %s" % (d, " | ".join(reasons))]
        return []
    finally:
        if not stuck:
            shutil.rmtree(d, ignore_errors=True)


def py(script, *args, now=None, **kw):
    if now is not None:
        kw["env"] = dict(kw.get("env") or os.environ, CYS_TEST_NOW=str(now))
    return run([sys.executable, os.path.join(UPD, script)] + list(args), **kw)


def u1_stamp(path, purpose="feed"):
    """U1 update-verify 통과를 흉내 낸 증표(시험 전용 · 실제 게시 경로는 release-gate verify --stamp 만 쓴다)."""
    uc.write_stamp(path, open(path + ".minisig", "rb").read(), json.load(open(path)).get("key_id"), purpose,
                   uc.STAMP_BY_U1, NOW)


class Fixture:
    """가짜 릴리스 산출물 + 시험 키 R·U·F + 키링."""

    def __init__(self, d, version="1.1.8", seq=5):
        self.d, self.version, self.seq = d, version, seq
        self.keys = {}
        for k, purpose in (("r", "root"), ("u", "release"), ("f", "feed")):
            kid = fm.generate(os.path.join(d, k + ".pub"), os.path.join(d, k + ".key"))
            self.keys[k] = (kid, purpose)
        self.keyring = os.path.join(d, "keyring.json")
        self.write_keyring()
        self.rel = os.path.join(d, "rel-%s" % version)
        os.makedirs(self.rel)
        with zipfile.ZipFile(os.path.join(self.rel, "cysr-macos-arm64-v%s.zip" % version), "w") as z:
            z.writestr("cysr.app/Contents/MacOS/cys", "m" * 1000 + version)
        with open(os.path.join(self.rel, "cysr_%s_x64-setup.exe" % version), "wb") as f:
            f.write(b"MZ" + os.urandom(4000))
        with open(os.path.join(self.rel, "cysr_%s_x64-setup.exe.sig" % version), "w") as f:
            f.write("sig\n")
        with open(os.path.join(self.rel, "latest.json"), "w") as f:
            f.write('{"version":"%s"}\n' % version)
        self.write_sums()
        self.pay = os.path.join(d, "pay-%s" % version)
        os.makedirs(os.path.join(self.pay, "runtime"))
        open(os.path.join(self.pay, "cys.exe"), "w").write("cys" + version)
        open(os.path.join(self.pay, "runtime", "python312.dll"), "w").write("dll")
        self.bi = {}
        for t in ("macos-arm64", "windows-x64"):
            p = os.path.join(d, "bi-%s-%s.json" % (version, t))
            json.dump({"version": version, "build_id": "abc123def456.20261006T0100Z", "release_seq": seq,
                       "target": t, "features": [], "bundled_pack": {"version": version, "digest": "a" * 64},
                       "keyring_ids": []}, open(p, "w"))
            self.bi[t] = p

    def write_keyring(self, extra=()):
        keys = []
        for k, (kid, purpose) in self.keys.items():
            pub = open(os.path.join(self.d, k + ".pub")).read()
            keys.append({"key_id": kid, "pubkey": base64.b64encode(pub.encode()).decode(),
                         "not_after": "2030-01-01T00:00:00Z", "purpose": purpose})
        json.dump({"keys": keys + list(extra), "revoked_key_ids": []}, open(self.keyring, "w"))

    def write_sums(self):
        with open(os.path.join(self.rel, "SHA256SUMS.txt"), "w") as f:
            for n in sorted(os.listdir(self.rel)):
                if n != "SHA256SUMS.txt":
                    f.write("%s  %s\n" % (uc.sha256_file(os.path.join(self.rel, n)), n))

    def kid(self, k):
        return self.keys[k][0]

    def key(self, k):
        return os.path.join(self.d, k + ".key")

    def gen_args(self, out, **over):
        v = self.version
        a = {"--component": "cysr", "--release-seq": str(self.seq), "--version": v,
             "--min-from-release-seq": "1", "--state-migration": "additive",
             "--notes-ko": "새 판을 받아 두었어요", "--key-id": self.kid("u"),
             "--requires-min-binary-for-pack": "1.1.8", "--release-dir": self.rel, "--out": out}
        a.update(over)
        args = []
        for k, val in a.items():
            if val is not None:
                args += [k, val]
        args += ["--asset", "macos-arm64=cysr-macos-arm64-v%s.zip" % v,
                 "--asset", "windows-x64=cysr_%s_x64-setup.exe" % v,
                 "--build-info", "macos-arm64=" + self.bi["macos-arm64"],
                 "--build-info", "windows-x64=" + self.bi["windows-x64"],
                 "--cdhash", "macos-arm64=" + "b" * 40,
                 "--a2-sig", "windows-x64=cysr_%s_x64-setup.exe.sig" % v,
                 "--payload-dir", "windows-x64=" + self.pay]
        return args

    def body(self, name="body.json", **over):
        out = os.path.join(self.d, name)
        r = py("make-release-json.py", *self.gen_args(out, **over))
        assert r.returncode == 0, r.stderr
        fm.sign(self.key("u"), out, out + ".minisig", "t")
        return out


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="u3-")
        self.fx = Fixture(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestFakeMinisign(unittest.TestCase):
    def test_rfc8032_vector1(self):
        seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        self.assertEqual(fm.ed25519_public(seed).hex(),
                         "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        self.assertTrue(fm.ed25519_sign(seed, b"").hex().startswith("e5564300c360ac729086e2cc806e828a"))

    def test_real_minisign_key_refused(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "real.key")
            open(p, "w").write("untrusted comment: minisign encrypted secret key\nRWQ...\n")
            with self.assertRaises(SystemExit):
                fm.load_secret(p)
        finally:
            shutil.rmtree(d)


class TestGenerator(Base):
    def test_happy_body_shape(self):
        b = json.load(open(self.fx.body()))
        self.assertEqual(b["kind"], "component-release")
        self.assertEqual(sorted(b["assets"]), ["macos-arm64", "windows-x64"])
        w = b["assets"]["windows-x64"]
        self.assertEqual([e["path"] for e in w["payload_manifest"]], ["cys.exe", "runtime/python312.dll"])
        self.assertEqual(w["max_unpacked"], sum(e["size"] for e in w["payload_manifest"]))
        self.assertTrue(w["a2_sig_url"].startswith("https://github.com/oogisoogi/cys-ro/releases/download/v1.1.8/"))
        m = b["assets"]["macos-arm64"]
        self.assertEqual(m["dr_pin_id"], uc.DR_PIN_ID_CYS_LOCAL)
        self.assertEqual(m["max_unpacked"], 1000 + len("1.1.8"))
        self.assertEqual(b["requires"], {"min_binary_for_pack": "1.1.8"})
        self.assertEqual(py("release-gate.py", "body", "--body", os.path.join(self.tmp, "body.json"),
                            "--sig", os.path.join(self.tmp, "body.json.minisig"),
                            "--keyring", self.fx.keyring).returncode, 0)

    def _refused(self, args, needle):
        r = py("make-release-json.py", *args)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(needle, r.stderr)

    def test_mut_missing_windows_row(self):
        a = self.fx.gen_args(os.path.join(self.tmp, "x.json"))
        keep = []
        for i in range(0, len(a), 2):
            if not a[i + 1].startswith("windows-x64="):
                keep += a[i:i + 2]
        self._refused(keep, "필수 기판 행 부재")

    def test_mut_notes_empty_and_forbidden(self):
        self._refused(self.fx.gen_args(os.path.join(self.tmp, "x.json"), **{"--notes-ko": " "}), "notes_ko 비었음")
        self._refused(self.fx.gen_args(os.path.join(self.tmp, "x.json"), **{"--notes-ko": "오류 수정판"}), "금지 어휘")

    def test_mut_min_binary_empty(self):
        self._refused(self.fx.gen_args(os.path.join(self.tmp, "x.json"), **{"--requires-min-binary-for-pack": ""}),
                      "min_binary_for_pack 빈 값")

    def test_mut_build_info_seq_mismatch(self):
        self._refused(self.fx.gen_args(os.path.join(self.tmp, "x.json"), **{"--release-seq": "6"}), "release_seq")

    def test_mut_sums_mismatch(self):
        with open(os.path.join(self.fx.rel, "cysr_1.1.8_x64-setup.exe"), "ab") as f:
            f.write(b"!")
        self._refused(self.fx.gen_args(os.path.join(self.tmp, "x.json")), "SHA256SUMS")

    def test_mut_payload_symlink(self):
        os.symlink("/etc/hosts", os.path.join(self.fx.pay, "evil"))
        self._refused(self.fx.gen_args(os.path.join(self.tmp, "x.json")), "심링크")

    def test_mut_dirty_build(self):
        bi = json.load(open(self.fx.bi["windows-x64"]))
        bi["build_id"] += "-dirty"
        json.dump(bi, open(self.fx.bi["windows-x64"], "w"))
        self._refused(self.fx.gen_args(os.path.join(self.tmp, "x.json")), "-dirty")


class TestEnvelope(Base):
    now = NOW

    def env(self, *extra, name="env.json"):
        b = os.path.join(self.tmp, "body.json")
        if not os.path.exists(b):
            self.fx.body()
        out = os.path.join(self.tmp, name)
        return py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", b,
                  "--release-sig", b + ".minisig", "--key-id", self.fx.kid("f"), "--keyring", self.fx.keyring,
                  "--out", out, *extra, now=self.now), out

    def test_first_and_increment(self):
        r, out = self.env("--first", "--rollout-pct", "10", "--halt", "false")
        self.assertEqual(r.returncode, 0, r.stderr)
        e = json.load(open(out))
        self.assertEqual((e["feed_rev"], e["rollout_pct"], e["halt"]), (1, 10, False))
        self.assertLessEqual(e["expires_at"] - e["signed_at"], 14 * 86400)
        fm.sign(self.fx.key("f"), out, out + ".minisig", "t")
        u1_stamp(out)  # 증표가 있어도(정보용) U1 재검증 인자 없이는 상속 0 — 3판 2R #6
        r0, _ = self.env("--prev-envelope", out, name="env1b.json")
        self.assertEqual(r0.returncode, 2)
        self.assertIn("--cys", r0.stderr)

    def test_mut_no_first(self):
        r, _ = self.env("--rollout-pct", "10", "--halt", "false")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--first", r.stderr)

    def test_mut_ttl_over_14d(self):
        r, _ = self.env("--first", "--rollout-pct", "10", "--halt", "false", "--ttl-days", "15")
        self.assertEqual(r.returncode, 2)

    def test_mut_f_equals_u(self):
        b = self.fx.body()
        r = py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", b,
               "--release-sig", b + ".minisig", "--key-id", self.fx.kid("u"), "--first", "--rollout-pct", "1",
               "--halt", "false", "--keyring", self.fx.keyring, "--out", os.path.join(self.tmp, "e.json"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("용도 분리", r.stderr)

    def test_mut_expired_key(self):
        """codex 1R #15: 신뢰 시각 ≥ 키 not_after(픽스처 2030-01-01) = 거부 — 생성 단계에서."""
        b = self.fx.body()
        r = py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", b,
               "--release-sig", b + ".minisig", "--key-id", self.fx.kid("f"), "--first", "--rollout-pct", "1",
               "--halt", "false", "--keyring", self.fx.keyring, "--out", os.path.join(self.tmp, "e.json"),
               now=1893456000)  # 2030-01-01T00:00:00Z
        self.assertEqual(r.returncode, 2)
        self.assertIn("만료된 키", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "e.json")))

    def test_mut_forged_body_sig_same_key_id(self):
        b = self.fx.body()
        raw = open(b + ".minisig").read().splitlines()
        sraw = bytearray(base64.b64decode(raw[1]))
        sraw[20] ^= 1  # key id 바이트는 그대로 · 서명만 위조
        raw[1] = base64.b64encode(bytes(sraw)).decode()
        open(b + ".minisig", "w").write("\n".join(raw) + "\n")
        r, _ = self.env("--first", "--rollout-pct", "10", "--halt", "false")
        self.assertEqual(r.returncode, 2)
        self.assertIn("서명 검증 실패", r.stderr)


def gate_stamp_body(fx, b):
    """발행 게이트 body 단계(증표 = 정보용 · 3판에서 게시 조건 아님)를 지나게 한 본문."""
    r = py("release-gate.py", "body", "--body", b, "--sig", b + ".minisig", "--keyring", fx.keyring, "--stamp")
    assert r.returncode == 0, r.stderr
    return b


def gen_of(st, comp="cysr"):
    return json.load(open(os.path.join(st, "ptr", "update", comp, "releases", "_gen")))


def publish(fx, kind, f, store, *extra, **kw):
    return py("publish-site.py", kind, "--fs", store, "--file", f, "--keyring", fx.keyring,
              "--lock-file", os.path.join(store + ".lock"), "--rollback-dir", store + ".rollback", *extra, **kw)


class TestPublishSite(Base):
    def test_archive_immutable_and_index(self):
        b = gate_stamp_body(self.fx, self.fx.body())
        st = os.path.join(self.tmp, "store")
        r = publish(self.fx, "archive", b, st)
        self.assertEqual(r.returncode, 3)  # 색인 없음 + --first 없음
        self.assertEqual(publish(self.fx, "archive", b, st, "--first").returncode, 0)
        g = gen_of(st)  # 3판: 포인터 + 색인 = 세대 포인터 한 객체(2R #8)
        self.assertEqual(open(os.path.join(st, g["seqs"]["5"]["json"]), "rb").read(), open(b, "rb").read())
        self.assertEqual(g["max_seq"], 5)
        r = publish(self.fx, "archive", b, st)
        self.assertEqual(r.returncode, 0)
        self.assertIn("멱등", r.stdout)
        b2 = gate_stamp_body(self.fx, self.fx.body(name="body2.json", **{"--notes-ko": "다른 문구예요"}))
        r = publish(self.fx, "archive", b2, st)
        self.assertEqual(r.returncode, 3, r.stderr)  # 같은 seq 다른 바이트 = 불변 보관소 덮어쓰기 거부
        self.assertIn("덮어쓰기 거부", r.stderr)

    def test_retry_after_interrupt_completes_index(self):
        """codex 2R #8 재현의 반대: 객체만 올라가고 세대 포인터 교체 전에 끊긴 상태 → 재실행 = 색인까지 완성(「멱등인데 색인 없음」 0)."""
        b = self.fx.body()
        st = os.path.join(self.tmp, "store")
        for f in (b, b + ".minisig"):
            data = open(f, "rb").read()
            p = os.path.join(st, "obj", uc.sha256_bytes(data))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(data)
        r = publish(self.fx, "archive", b, st, "--first")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("멱등", r.stdout)
        self.assertEqual(gen_of(st)["max_seq"], 5)

    def live_server(self, on_get=None):
        """잘못된 바이트를 주는 로컬 사이트(라이브 대조 불일치 주입) · on_get = 요청 때 부를 함수(경쟁 주입)."""
        import http.server
        import threading

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if on_get:
                    on_get()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"stale bytes")

            def log_message(self, *a):
                pass
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        return "http://127.0.0.1:%d" % srv.server_address[1]

    def test_mut_live_check_rolls_back(self):
        """codex 2R #16: 라이브 불일치 = 옛 포인터로 ETag 조건 자동 되돌리기(rc 4) — 첫 게시면 세대 포인터 삭제."""
        b = self.fx.body()
        st = os.path.join(self.tmp, "store")
        r = publish(self.fx, "archive", b, st, "--first", "--live-check", self.live_server(), "--live-tries", "1")
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn("되돌렸다", r.stderr)
        tomb = open(os.path.join(st, "ptr", "update", "cysr", "releases", "_gen"), "rb").read()
        self.assertEqual(tomb, b'{"tombstone": true}\n')  # 4판: 없앰 = 묘비 포인터(조건부 PUT · 삭제 API 0)
        self.assertEqual(publish(self.fx, "archive", b, st, "--first").returncode, 0)  # 묘비 위 정상 게시(그 ETag 로 CAS)
        self.assertEqual(gen_of(st)["max_seq"], 5)

    def test_mut_live_check_rollback_cas_fails_rc5(self):
        """되돌리기 CAS 마저 실패(대조 중 누가 또 바꿈) = rc 5 + 실행 가능한 restore 명령 1줄 → 그 명령으로 복구."""
        b = self.fx.body()
        st = os.path.join(self.tmp, "store")
        gp = os.path.join(st, "ptr", "update", "cysr", "releases", "_gen")
        intr = lambda: open(gp, "w").write('{"max_seq": 5, "seqs": {}, "intruder": 1}\n')
        r = publish(self.fx, "archive", b, st, "--first", "--live-check", self.live_server(intr), "--live-tries", "1")
        self.assertEqual(r.returncode, 5, r.stderr)
        line = [l for l in r.stderr.splitlines() if " restore " in l]
        self.assertEqual(len(line), 1, r.stderr)
        import shlex
        rr = run(shlex.split(line[0]))
        self.assertEqual(rr.returncode, 0, rr.stderr)
        self.assertEqual(open(gp, "rb").read(), b'{"tombstone": true}\n')  # 첫 게시였으므로 복구 = 묘비

    def test_s3store_conditional_put_against_fake_s3(self):
        """S3Store 의 HTTP 경로(SigV4 헤더 · If-None-Match/If-Match · 412 = CasFail) — 로컬 가짜 S3(R2 실측 0 · 의미 대역)."""
        import hashlib as hl
        import http.server
        import threading
        objs, seen = {}, []

        class H(http.server.BaseHTTPRequestHandler):
            def _etag(self, k):
                return hl.md5(objs[k]).hexdigest()

            def do_GET(self):
                k = self.path
                if k not in objs:
                    self.send_response(404); self.end_headers(); return
                self.send_response(200); self.send_header("ETag", '"%s"' % self._etag(k)); self.end_headers()
                self.wfile.write(objs[k])

            def do_PUT(self):
                seen.append(self.headers.get("Authorization", ""))
                k, body = self.path, self.rfile.read(int(self.headers["Content-Length"]))
                inm, im = self.headers.get("If-None-Match"), self.headers.get("If-Match")
                if (inm == "*" and k in objs) or (im and (k not in objs or im.strip('"') != self._etag(k))):
                    self.send_response(412); self.end_headers(); return
                objs[k] = body
                self.send_response(200); self.send_header("ETag", '"%s"' % self._etag(k)); self.end_headers()

            def do_DELETE(self):
                k, im = self.path, self.headers.get("If-Match")
                if k not in objs or (im and im.strip('"') != self._etag(k)):
                    self.send_response(412); self.end_headers(); return
                del objs[k]; self.send_response(204); self.end_headers()

            def log_message(self, *a):
                pass
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        sys.path.insert(0, UPD)
        import store as stm
        st = stm.S3Store("bkt", endpoint="http://127.0.0.1:%d" % srv.server_address[1], access_key="AK", secret_key="SK")
        e1 = st.cas("ptr/x", b"one", None)
        self.assertEqual(st.get("ptr/x"), (b"one", e1))
        with self.assertRaises(stm.CasFail):
            st.cas("ptr/x", b"two", None)
        e2 = st.cas("ptr/x", b"two", e1)
        with self.assertRaises(stm.CasFail):
            st.cas("ptr/x", b"three", e1)
        e3 = st.cas("ptr/x", stm.TOMBSTONE, e2)                       # 없앰 = 묘비 조건부 PUT(4판 · DELETE 0)
        self.assertEqual(stm.load(st, "ptr/x")[::2], (None, e3))
        self.assertFalse(hasattr(st, "cas_delete"))
        self.assertTrue(all(a.startswith("AWS4-HMAC-SHA256 Credential=AK/") for a in seen))

    def test_mut_cas_etag_mismatch(self):
        """codex 2R #8: 읽은 뒤 다른 게시자가 포인터를 바꾸면(ETag 불일치) 교체 거부 — FsStore·S3 의미 같음."""
        sys.path.insert(0, UPD)
        import store as stm
        st = stm.FsStore(os.path.join(self.tmp, "s"))
        e1 = st.cas("ptr/x", b"one", None)
        with self.assertRaises(stm.CasFail):
            st.cas("ptr/x", b"two", None)            # If-None-Match: * — 이미 있음
        st.cas("ptr/x", b"two", e1)
        with self.assertRaises(stm.CasFail):
            st.cas("ptr/x", b"three", e1)            # If-Match: 낡은 ETag
        self.assertEqual(st.get("ptr/x")[0], b"two")

    def test_stamp_not_required_tamper_refused(self):
        """3판(2R #4): 증표는 게시 조건이 아니다 — 게시기가 직접 서명을 다시 잰다(변조 = 거부 · 위조 증표 무력)."""
        b = self.fx.body()
        st = os.path.join(self.tmp, "store")
        raw = open(b, "rb").read()
        open(b, "ab").write(b" ")
        uc.write_stamp(b, open(b + ".minisig", "rb").read(), "X", "release", uc.STAMP_BY_PY, NOW)  # 위조 증표
        r = publish(self.fx, "archive", b, st, "--first")
        self.assertEqual(r.returncode, 2)
        self.assertIn("서명 검증 실패", r.stderr)
        open(b, "wb").write(raw)
        self.assertEqual(publish(self.fx, "archive", b, st, "--first").returncode, 0)

    def test_mut_low_seq_archive(self):
        st = os.path.join(self.tmp, "store")
        self.assertEqual(publish(self.fx, "archive", gate_stamp_body(self.fx, self.fx.body()), st, "--first").returncode, 0)
        d = os.path.join(self.tmp, "low")
        os.makedirs(d)
        fx4 = Fixture(d, seq=4)
        fx4.keys, fx4.keyring = self.fx.keys, self.fx.keyring
        shutil.copy(self.fx.key("u"), fx4.key("u"))
        b4 = gate_stamp_body(fx4, fx4.body())
        r = publish(self.fx, "archive", b4, st)
        self.assertEqual(r.returncode, 3)
        self.assertIn("최댓값", r.stderr)

    def test_concurrent_publish_two(self):
        b = gate_stamp_body(self.fx, self.fx.body())
        st = os.path.join(self.tmp, "store")
        procs = [subprocess.Popen([sys.executable, os.path.join(UPD, "publish-site.py"), "archive", "--fs", st, "--file", b,
                                   "--keyring", self.fx.keyring, "--lock-file", st + ".lock", "--first"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        rcs = sorted(p.wait() for p in procs)
        self.assertEqual(rcs, [0, 0])  # 하나는 게시 · 하나는 잠금 뒤 재검사 = 멱등(같은 바이트)
        self.assertEqual(gen_of(st)["max_seq"], 5)


class TestGateAssets(Base):
    def test_latest_json_required(self):
        self.assertEqual(py("release-gate.py", "assets", "--release-dir", self.fx.rel).returncode, 0)
        os.remove(os.path.join(self.fx.rel, "latest.json"))
        r = py("release-gate.py", "assets", "--release-dir", self.fx.rel)
        self.assertEqual(r.returncode, 1)
        self.assertIn("latest.json", r.stderr)

    def test_asset_list_lane(self):
        r = py("release-gate.py", "assets", "--release-dir", self.fx.rel, "--asset-list", "pack.tar.gz,pack-manifest.json")
        self.assertEqual(r.returncode, 1)

    def test_tombstone_mode(self):
        tomb = os.path.join(self.tmp, "tomb.json")
        open(tomb, "w").write('{"version":"1.1.8","tomb":1}\n')
        r = py("release-gate.py", "assets", "--release-dir", self.fx.rel, "--tombstone", tomb)
        self.assertEqual(r.returncode, 1)
        self.assertIn("tombstone", r.stderr)
        shutil.copy(tomb, os.path.join(self.fx.rel, "latest.json"))
        self.assertEqual(py("release-gate.py", "assets", "--release-dir", self.fx.rel, "--tombstone", tomb).returncode, 0)

    def test_min_binary_empty(self):
        good, bad = os.path.join(self.tmp, "pm.json"), os.path.join(self.tmp, "pm0.json")
        json.dump({"min_binary_version": "1.1.8"}, open(good, "w"))
        json.dump({"min_binary_version": ""}, open(bad, "w"))
        self.assertEqual(py("release-gate.py", "assets", "--pack-manifest", good).returncode, 0)
        for flag in ("--pack-manifest", "--bundled-manifest"):
            r = py("release-gate.py", "assets", flag, bad)
            self.assertEqual(r.returncode, 1)
            self.assertIn("빈 값", r.stderr)

    def test_nothing_to_measure_is_undetermined(self):
        self.assertEqual(py("release-gate.py", "assets").returncode, 3)


class TestUserAgent(unittest.TestCase):
    """1.1.8 R4 실측(2026-10-08): SITE_HOST 앞단 Cloudflare 가 파이썬 기본 UA(`Python-urllib/…`)만 403 — 발행 도구의
    urllib 요청은 전부 uc.HTTP_USER_AGENT 를 싣는다. 가짜 사이트 = 기본 UA 403 · 그 밖 200 + Date(그 규칙의 대역)."""

    def site(self):
        import http.server
        import threading
        seen = []

        class H(http.server.BaseHTTPRequestHandler):
            def _answer(self):
                ua = self.headers.get("User-Agent", "")
                seen.append(ua)
                self.send_response(403 if ua.startswith("Python-urllib") else 200)
                self.end_headers()

            do_HEAD = do_GET = _answer

            def log_message(self, *a):
                pass
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        return "http://127.0.0.1:%d/" % srv.server_address[1], seen

    def trusted_now_against(self, url, ua):
        old = (uc.TIME_SOURCE, uc.HTTP_USER_AGENT, os.environ.pop("CYS_SIGN_DEV"))
        try:
            uc.TIME_SOURCE, uc.HTTP_USER_AGENT = url, ua
            return uc.trusted_now()
        finally:
            uc.TIME_SOURCE, uc.HTTP_USER_AGENT = old[0], old[1]
            os.environ["CYS_SIGN_DEV"] = old[2]

    def test_trusted_now_sends_publish_ua(self):
        url, seen = self.site()
        self.assertIsInstance(self.trusted_now_against(url, uc.HTTP_USER_AGENT), int)
        self.assertEqual(seen, ["cysr-publish/1"])

    def test_mut_default_python_ua_is_403(self):
        """음성 대조: 상수가 파이썬 기본 UA 와 같으면 가짜 사이트가 403 → 신뢰 시각 대조 불가(그 실측의 재현)."""
        url, seen = self.site()
        import urllib.request
        with self.assertRaises(uc.PublishError) as cm:
            self.trusted_now_against(url, "Python-urllib/%d.%d" % sys.version_info[:2])
        self.assertIn("403", str(cm.exception))
        self.assertEqual(len(seen), 1)
        self.assertTrue(dict(urllib.request.build_opener().addheaders)["User-agent"].startswith("Python-urllib"))

    def test_every_urllib_request_in_publish_tools_carries_ua(self):
        """소스 검사: scripts/update/*.py 의 urllib Request 생성마다 HTTP_USER_AGENT · Request 없이 urlopen(문자열) 0."""
        import re
        found = 0
        for n in sorted(os.listdir(UPD)):
            if not n.endswith(".py"):
                continue
            with open(os.path.join(UPD, n), encoding="utf-8") as f:
                s = f.read()
            for m in re.finditer(r"urllib\.request\.Request\(", s):
                found += 1
                depth, i = 1, m.end()
                while depth:
                    depth += {"(": 1, ")": -1}.get(s[i], 0)
                    i += 1
                self.assertIn("HTTP_USER_AGENT", s[m.end():i], "%s:%d" % (n, s.count("\n", 0, m.start()) + 1))
            for m in re.finditer(r"urlopen\((?!req\b|urllib\.request\.Request\()", s):
                self.fail("%s:%d urlopen 이 Request(UA) 없이 불린다" % (n, s.count("\n", 0, m.start()) + 1))
        self.assertEqual(found, 3)  # update_common.trusted_now · publish-site.live_check · store.S3Store._req


class TestFeedCaps(Base):
    """1.1.8 본체 실기(2026-10-08): 기기 받기 상한(net.rs) 밖 문서를 발행 쪽이 만들지도·통과시키지도·게시하지도 않는다.
    단일 출처 = net.rs — 이 시험이 그 파일의 상수를 읽어 update_common 과 맞춘다(한쪽만 바뀌면 적색)."""

    def rust_caps(self):
        import re
        with open(os.path.join(ROOT, "src", "update", "net.rs"), encoding="utf-8") as f:
            s = f.read()
        caps = {}
        for name in ("FEED_MAX_BYTES", "FEED_BODY_MAX_BYTES", "FEED_ENVELOPE_MAX_BYTES"):
            m = re.search(r"pub const %s: u64 = (\d+) << (\d+);" % name, s)
            self.assertIsNotNone(m, name)
            caps[name] = int(m.group(1)) << int(m.group(2))
        return caps

    def test_caps_match_rust_net_rs(self):
        c = self.rust_caps()
        self.assertEqual(uc.FEED_DOC_MAX_BYTES, c["FEED_MAX_BYTES"])
        self.assertEqual(uc.FEED_BODY_MAX_BYTES, c["FEED_BODY_MAX_BYTES"])
        self.assertEqual(uc.FEED_ENVELOPE_MAX_BYTES, c["FEED_ENVELOPE_MAX_BYTES"])
        self.assertGreater(uc.FEED_BODY_MAX_BYTES, 2474038)  # 1.1.8 실측 본문(윈 payload 11,676 행)

    def test_check_feed_size_boundary(self):
        for kind, cap in uc.FEED_MAX_BYTES_BY_KIND.items():
            uc.check_feed_size(kind, cap)
            with self.assertRaises(uc.PublishError):
                uc.check_feed_size(kind, cap + 1)

    def gen_main(self, script):
        import importlib.util
        spec = importlib.util.spec_from_file_location(script.replace("-", "_")[:-3], os.path.join(UPD, script))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.main

    def check_generator_cap(self, script, kind, args_for):
        """생성기 ±1: 기본 상한으로 한 번 만들어 길이 n 을 잰 뒤 상한 = n → rc 0(파일 생김) · n − 1 → rc 2(파일 0) — 같은 입력."""
        main = self.gen_main(script)
        probe = os.path.join(self.tmp, "%s-probe.json" % kind)
        self.assertEqual(main(args_for(probe)), 0, script)
        n = os.path.getsize(probe)
        old = uc.FEED_MAX_BYTES_BY_KIND[kind]
        try:
            for cap, want in ((n, 0), (n - 1, 2)):
                uc.FEED_MAX_BYTES_BY_KIND[kind] = cap
                out = os.path.join(self.tmp, "%s-cap-%d.json" % (kind, cap))
                self.assertEqual(main(args_for(out)), want, (script, cap))
                self.assertEqual(os.path.exists(out), want == 0, (script, cap))
        finally:
            uc.FEED_MAX_BYTES_BY_KIND[kind] = old

    def test_generator_refuses_over_device_cap(self):
        """본문 생성기(make-release-json) ±1."""
        self.check_generator_cap("make-release-json.py", "body", self.fx.gen_args)

    def test_envelope_generator_refuses_over_device_cap(self):
        """봉투 생성기(make-envelope) ±1 — 봉투는 본문을 base64 로 싣는다(기기 상한 12 MiB)."""
        b = self.fx.body()
        self.check_generator_cap("make-envelope.py", "envelope", lambda out: [
            "--component", "cysr", "--channel", "stable", "--release-body", b, "--release-sig", b + ".minisig",
            "--key-id", self.fx.kid("f"), "--keyring", self.fx.keyring, "--first", "--rollout-pct", "10", "--halt", "false",
            "--out", out])

    def test_revocations_generator_refuses_over_device_cap(self):
        """폐기문 생성기(make-revocations) ±1(기기 상한 1 MiB)."""
        self.check_generator_cap("make-revocations.py", "revocations", lambda out: [
            "--key-id", self.fx.kid("r"), "--keyring", self.fx.keyring, "--first", "--out", out])

    def test_gate_body_refuses_over_device_cap(self):
        """발행 게이트 body: 실제 상한(8 MiB) 바이트 = 통과 · +1 = 실패(끝 공백으로 늘린 같은 JSON)."""
        b = self.fx.body()
        with open(b, "rb") as f:
            raw = f.read()
        for extra, rc in ((0, 0), (1, 1)):
            p = os.path.join(self.tmp, "pad-%d.json" % extra)
            with open(p, "wb") as f:
                f.write(raw + b" " * (uc.FEED_BODY_MAX_BYTES - len(raw) + extra))
            r = py("release-gate.py", "body", "--body", p)
            self.assertEqual(r.returncode, rc, r.stdout + r.stderr)
            if rc:
                self.assertIn("기기 받기 상한", r.stdout + r.stderr)

    def test_publish_site_refuses_over_device_cap(self):
        """게시기: 상한 초과 본문 = rc 2 · 보관소 쓰기 0."""
        b = self.fx.body()
        with open(b, "rb") as f:
            raw = f.read()
        p = os.path.join(self.tmp, "big.json")
        with open(p, "wb") as f:
            f.write(raw + b" " * (uc.FEED_BODY_MAX_BYTES - len(raw) + 1))
        shutil.copy(b + ".minisig", p + ".minisig")
        st = os.path.join(self.tmp, "store")
        r = publish(self.fx, "archive", p, st, "--first")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("기기 받기 상한", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(st, "obj")))


class TestGateBody(Base):
    def store_with(self, b):
        st = os.path.join(self.tmp, "store")
        self.assertEqual(publish(self.fx, "archive", gate_stamp_body(self.fx, b), st, "--first").returncode, 0)
        return st

    def next_body(self, version, seq):
        d = os.path.join(self.tmp, "v%s-%d" % (version, seq))
        os.makedirs(d)
        fx = Fixture(d, version=version, seq=seq)
        fx.keys, fx.keyring = self.fx.keys, self.fx.keyring
        shutil.copy(self.fx.key("u"), fx.key("u"))
        return fx.body()

    def test_seq_progress_and_version_warning(self):
        st = self.store_with(self.fx.body())
        self.assertEqual(py("release-gate.py", "body", "--body", self.next_body("1.1.9", 6), "--archive-fs", st,
                            "--expect-seq", "6").returncode, 0)
        r = py("release-gate.py", "body", "--body", self.next_body("1.1.8", 6), "--archive-fs", st)
        self.assertEqual(r.returncode, 0, r.stderr)  # 판 문자열 = 비보안 경고(codex 1R #19)
        self.assertIn("비보안 경고", r.stderr)
        r = py("release-gate.py", "body", "--body", self.next_body("1.1.10", 7), "--archive-fs", st)
        self.assertEqual(r.returncode, 1)
        self.assertIn("최댓값", r.stderr)  # 건너뜀
        r = py("release-gate.py", "body", "--body", self.next_body("1.1.7", 4), "--archive-fs", st)
        self.assertEqual(r.returncode, 1)  # 역행

    def test_expect_seq_mismatch(self):
        r = py("release-gate.py", "body", "--body", self.fx.body(), "--expect-seq", "9")
        self.assertEqual(r.returncode, 1)
        self.assertIn("vars.CYSR_RELEASE_SEQ", r.stderr)

    def test_archive_same_seq_different_bytes(self):
        st = self.store_with(self.fx.body())
        b2 = self.fx.body(name="b2.json", **{"--notes-ko": "다른 문구예요"})
        r = py("release-gate.py", "body", "--body", b2, "--archive-fs", st)
        self.assertEqual(r.returncode, 1)
        self.assertIn("덮어쓰기 거부", r.stderr)

    def _mutate(self, fn, needle):
        b = json.load(open(self.fx.body()))
        fn(b)
        p = os.path.join(self.tmp, "m.json")
        open(p, "wb").write(uc.dump_json_bytes(b))
        r = py("release-gate.py", "body", "--body", p)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(needle, r.stderr)

    def test_mut_url_outside_rules(self):
        self._mutate(lambda b: b["assets"]["macos-arm64"].update(url="https://evil.example/x.zip"), "url 규칙 밖")

    def test_mut_site_url_for_cysr_asset(self):
        self._mutate(lambda b: b["assets"]["macos-arm64"].update(
            url="https://jarvis.godmeyou.kr/install/agora-client-0.1.11.zip"), "url 규칙 밖")

    def test_mut_future_signed_at(self):
        self._mutate(lambda b: b.update(signed_at=NOW + 3600), "미래")

    def test_mut_requires_empty(self):
        self._mutate(lambda b: b["requires"].update(min_binary_for_pack=""), "빈 값")

    def test_mut_payload_traversal(self):
        self._mutate(lambda b: b["assets"]["windows-x64"]["payload_manifest"].append(
            {"path": "../x", "size": 1, "sha256": "c" * 64}), "payload_manifest 항목")

    def test_mut_sig_wrong_key_and_forged(self):
        b = self.fx.body()
        fm.sign(self.fx.key("f"), b, b + ".minisig", "t")
        r = py("release-gate.py", "body", "--body", b, "--sig", b + ".minisig", "--keyring", self.fx.keyring)
        self.assertEqual(r.returncode, 1)
        fm.sign(self.fx.key("u"), b, b + ".minisig", "t")
        raw = open(b + ".minisig").read().splitlines()
        sraw = bytearray(base64.b64decode(raw[1]))
        sraw[30] ^= 1
        raw[1] = base64.b64encode(bytes(sraw)).decode()
        open(b + ".minisig", "w").write("\n".join(raw) + "\n")
        r = py("release-gate.py", "body", "--body", b, "--sig", b + ".minisig", "--keyring", self.fx.keyring)
        self.assertEqual(r.returncode, 1)
        self.assertIn("서명 검증 실패", r.stderr)  # 같은 key id 위조 서명(codex 1R #4)

    def test_url_vectors_shared_with_u1(self):
        v = json.load(open(os.path.join(UPD, "url-vectors.json")))
        for c in v["cases"]:
            self.assertEqual(uc.url_ok_for(c["component"], c["field"], c["url"]), c["ok"], c)


class TestRevocations(Base):
    def mk(self, *args, now=NOW):
        return py("make-revocations.py", "--key-id", self.fx.kid("r"), "--keyring", self.fx.keyring, *args, now=now)

    def test_rev_and_rules(self):
        out = os.path.join(self.tmp, "rev.json")
        self.assertEqual(self.mk("--first", "--out", out).returncode, 0)
        r = self.mk("--prev", out, "--out", os.path.join(self.tmp, "x.json"), now=NOW + 60)
        self.assertEqual(r.returncode, 2)  # 직전 서명 없음
        fm.sign(self.fx.key("r"), out, out + ".minisig", "t")
        out2 = os.path.join(self.tmp, "rev2.json")
        r = self.mk("--prev", out, "--revoke-release", "cysr:5:stop_seats:bad_build",
                    "--delegate", "feed:%s:1900000000" % os.path.join(self.tmp, "u.pub"), "--out", out2, now=NOW + 60)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out2))
        self.assertEqual((d["rev"], d["signed_at"]), (2, NOW + 60))
        self.assertEqual(d["revoked_releases"][0]["severity"], "stop_seats")
        for bad in (["--delegate", "root:%s:1900000000" % os.path.join(self.tmp, "u.pub")],
                    ["--revoke-key", self.fx.kid("r")], ["--revoke-release", "cysr:5:panic:x"]):
            r = self.mk("--prev", out, "--out", os.path.join(self.tmp, "y.json"), *bad, now=NOW + 60)
            self.assertEqual(r.returncode, 2, bad)
        r = self.mk("--prev", out, "--out", os.path.join(self.tmp, "z.json"), now=NOW)
        self.assertEqual(r.returncode, 2)  # 시각 역행(직전과 같음)

    def test_mut_forged_prev_rev999(self):
        out = os.path.join(self.tmp, "fake.json")
        open(out, "wb").write(uc.dump_json_bytes({"kind": "update-revocations", "rev": 999, "key_id": self.fx.kid("r"),
                                                  "signed_at": NOW - 10, "delegations": [], "revoked_key_ids": [],
                                                  "revoked_releases": [], "dr_pins": {"add": [], "revoke": []}}))
        fm.sign(self.fx.key("f"), out, out + ".minisig", "t")  # R 이 아닌 키로 서명(=위조)
        r = self.mk("--prev", out, "--out", os.path.join(self.tmp, "n.json"), now=NOW + 60)
        self.assertEqual(r.returncode, 2)
        self.assertIn("서명 검증 실패", r.stderr)

    def test_gate_revocations_stage(self):
        out = os.path.join(self.tmp, "rev.json")
        self.mk("--first", "--out", out)
        fm.sign(self.fx.key("r"), out, out + ".minisig", "t")
        self.assertEqual(py("release-gate.py", "revocations", "--doc", out, "--keyring", self.fx.keyring, "--first",
                            "--stamp").returncode, 0)
        st = os.path.join(self.tmp, "store")
        r = publish(self.fx, "revocations", out, st)
        self.assertEqual(r.returncode, 3)  # 첫 폐기문 = --first 명시(3판)
        self.assertEqual(publish(self.fx, "revocations", out, st, "--first").returncode, 0)

    def signed(self, doc, name):
        out = os.path.join(self.tmp, name)
        open(out, "wb").write(uc.dump_json_bytes(doc))
        fm.sign(self.fx.key("r"), out, out + ".minisig", "t")
        return out

    def test_mut_successor_weakening_refused(self):
        """codex 2R #5: R 서명 rev+1 이라도 stop_seats→advisory 약화 · reason 변경 = 게이트·게시기 거부 · 승격은 허용."""
        base = {"kind": "update-revocations", "key_id": self.fx.kid("r"), "delegations": [], "revoked_key_ids": [],
                "dr_pins": {"add": [], "revoke": []}}
        rel = lambda sev, why="bad_build": [{"component": "cysr", "release_seq": 3, "severity": sev, "reason_code": why}]
        p1 = self.signed(dict(base, rev=1, signed_at=NOW - 100, revoked_releases=rel("stop_seats")), "p1.json")
        st = os.path.join(self.tmp, "store")
        self.assertEqual(publish(self.fx, "revocations", p1, st, "--first").returncode, 0)
        for name, rr in (("weak", rel("advisory")), ("reason", rel("stop_seats", "other"))):
            d = self.signed(dict(base, rev=2, signed_at=NOW - 50, revoked_releases=rr), name + ".json")
            g = py("release-gate.py", "revocations", "--doc", d, "--keyring", self.fx.keyring, "--prev", p1)
            self.assertEqual(g.returncode, 1, name)
            self.assertIn("advisory→stop_seats" if name == "weak" else "reason_code", g.stderr)
            r = publish(self.fx, "revocations", d, st)
            self.assertEqual(r.returncode, 2, name)
        a1 = self.signed(dict(base, rev=1, signed_at=NOW - 100, revoked_releases=rel("advisory")), "a1.json")
        up = self.signed(dict(base, rev=2, signed_at=NOW - 50, revoked_releases=rel("stop_seats")), "up.json")
        self.assertEqual(py("release-gate.py", "revocations", "--doc", up, "--keyring", self.fx.keyring,
                            "--prev", a1).returncode, 0)

    def test_tool_upgrade_only(self):
        """make-revocations: 이미 폐기된 릴리스 = advisory→stop_seats(같은 reason) 승격만."""
        p = os.path.join(self.tmp, "p.json")
        self.assertEqual(self.mk("--first", "--revoke-release", "cysr:3:advisory:bad", "--out", p).returncode, 0)
        fm.sign(self.fx.key("r"), p, p + ".minisig", "t")
        ok = self.mk("--prev", p, "--revoke-release", "cysr:3:stop_seats:bad", "--out", os.path.join(self.tmp, "q.json"),
                     now=NOW + 60)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.load(open(os.path.join(self.tmp, "q.json")))["revoked_releases"][0]["severity"], "stop_seats")
        bad = self.mk("--prev", p, "--revoke-release", "cysr:3:stop_seats:other", "--out", os.path.join(self.tmp, "x.json"),
                      now=NOW + 60)
        self.assertEqual(bad.returncode, 2)


class TestGateVerifyBoundaries(Base):
    """codex 2R #11 — 게이트의 출발 seq 계획 자체(U1 없이 · 대역 cys 가 seq 별 판정을 돌려준다).
    agora-client = 명시 설치 seq 경로: low-1 = ⓛ 거부 · lo..seq-1 = 허용 · seq·seq+1 = uptodate · 범위 상한 64."""

    def run_gate(self, plan, seq=5, low=3, component="agora-client"):
        body = {"kind": "component-release", "component": component, "release_seq": seq,
                "min_from_release_seq": low, "assets": {"any": {"url": "u", "sha256": "a" * 64, "size": 1}}}
        env = os.path.join(self.tmp, "env.json")
        json.dump({"release": base64.b64encode(json.dumps(body).encode()).decode()}, open(env, "w"))
        for f in (env + ".minisig", os.path.join(self.tmp, "rev.json"), os.path.join(self.tmp, "rev.json.minisig")):
            open(f, "w").write("x")
        fake = os.path.join(self.tmp, "fake-cys.py")
        open(fake, "w").write("""#!%s
import json, sys
a = sys.argv; i = int(a[a.index("--installed-release-seq") + 1])
v = json.loads(%r).get(str(i), {"verdict": "reject", "step": "ⓩ"})
if v["verdict"] == "apply": v["asset"] = {"url": "u", "sha256": "a" * 64, "size": 1}
print(json.dumps(v)); open(%r, "a").write("%%d\\n" %% i)
""" % (sys.executable, json.dumps(plan), os.path.join(self.tmp, "calls")))
        os.chmod(fake, 0o755)
        return py("release-gate.py", "verify", "--cys", fake, "--component", component, "--channel", "stable",
                  "--envelope", env, "--sig", env + ".minisig", "--revocations", os.path.join(self.tmp, "rev.json"),
                  "--revocations-sig", os.path.join(self.tmp, "rev.json.minisig"))

    GOOD = {"2": {"verdict": "reject", "step": "ⓛ"}, "3": {"verdict": "apply"}, "4": {"verdict": "apply"},
            "5": {"verdict": "uptodate"}, "6": {"verdict": "uptodate"}}

    def test_boundaries_happy(self):
        r = self.run_gate(self.GOOD)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(open(os.path.join(self.tmp, "calls")).read().split(), ["2", "3", "4", "5", "6"])

    def test_mut_boundaries(self):
        for seqk, bad in (("2", {"verdict": "apply"}), ("2", {"verdict": "reject", "step": "ⓖ"}),
                          ("6", {"verdict": "apply"}), ("5", {"verdict": "apply"})):
            plan = dict(self.GOOD, **{seqk: bad})
            r = self.run_gate(plan)
            self.assertEqual(r.returncode, 1, (seqk, bad))
            self.assertIn("installed %s" % seqk, r.stderr)

    def test_mut_range_cap(self):
        r = self.run_gate(self.GOOD, seq=100, low=1)
        self.assertEqual(r.returncode, 1)
        self.assertIn("상한 64", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "calls")))  # U1 을 부르기 전에 거부


NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node 없음 — update-worker 하네스 미실행")
class TestUpdateWorker(Base):
    """update-worker(R2 읽기 전용 · 2판 결정 ①)가 publish-site.py 가 쓴 **같은 배치**를 그대로 내보내는가."""

    def setUp(self):
        super().setUp()
        self.st = os.path.join(self.tmp, "store")
        b = gate_stamp_body(self.fx, self.fx.body())
        self.assertEqual(publish(self.fx, "archive", b, self.st, "--first").returncode, 0)
        self.body = b
        e = os.path.join(self.tmp, "e1.json")
        r = py("make-envelope.py", "--component", "cysr", "--channel", "next", "--release-body", b, "--release-sig",
               b + ".minisig", "--key-id", self.fx.kid("f"), "--keyring", self.fx.keyring, "--out", e, "--first",
               "--rollout-pct", "5", "--halt", "false")
        self.assertEqual(r.returncode, 0, r.stderr)
        fm.sign(self.fx.key("f"), e, e + ".minisig", "t")
        # 봉투 게시는 U1 재검증이 필요하다(3판) — 이 묶음은 워커 서빙만 재므로 같은 배치로 포인터를 직접 놓는다.
        sys.path.insert(0, UPD)
        import store as stm
        fs = stm.FsStore(self.st)
        data, sig = open(e, "rb").read(), open(e + ".minisig", "rb").read()
        for x in (data, sig):
            stm.put_object(fs, "obj/" + uc.sha256_bytes(x), x)
        fs.cas("ptr/update/cysr/next.json", json.dumps({"json": "obj/" + uc.sha256_bytes(data), "sig": "obj/" + uc.sha256_bytes(sig),
                                                         "json_sha256": uc.sha256_bytes(data),
                                                         "sig_sha256": uc.sha256_bytes(sig)}).encode(), None)
        self.env = e
        rv = os.path.join(self.tmp, "rev.json")
        py("make-revocations.py", "--key-id", self.fx.kid("r"), "--keyring", self.fx.keyring, "--first", "--out", rv)
        fm.sign(self.fx.key("r"), rv, rv + ".minisig", "t")
        self.assertEqual(publish(self.fx, "revocations", rv, self.st, "--first").returncode, 0)
        self.rev = rv

    def serve(self, *reqs):
        r = run([NODE, os.path.join(ROOT, "update-worker", "test", "fs-harness.mjs"), self.st,
                 json.dumps([{"method": m, "url": "https://jarvis.godmeyou.kr" + p} for m, p in reqs])])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def sha(self, f):
        return uc.sha256_bytes(open(f, "rb").read())

    def test_serves_published_pairs_with_cache_policy(self):
        got = self.serve(("GET", "/update/cysr/releases/5.json"), ("GET", "/update/cysr/releases/5.json.minisig"),
                         ("GET", "/update/cysr/next.json"), ("GET", "/update/cysr/next.json.minisig"),
                         ("GET", "/update/revocations.json"), ("HEAD", "/update/revocations.json.minisig"))
        want = [self.body, self.body + ".minisig", self.env, self.env + ".minisig", self.rev]
        for g, f in zip(got, want):
            self.assertEqual((g["status"], g["sha256"]), (200, self.sha(f)), f)
        self.assertIn("immutable", got[0]["headers"]["cache-control"])
        for g in got[2:]:
            self.assertEqual(g["headers"]["cache-control"], "no-store")
        self.assertEqual((got[5]["status"], got[5]["size"]), (200, 0))
        self.assertEqual(got[1]["headers"]["content-type"], "text/plain; charset=utf-8")
        self.assertEqual(got[0]["headers"]["etag"], '"%s"' % self.sha(self.body))

    def test_mut_refuses_outside_paths_and_methods(self):
        got = self.serve(("GET", "/update/cysr/releases/_gen"), ("GET", "/update/cysr/stable.json"),
                         ("GET", "/update/cysr%2Fnext.json"), ("GET", "/update/other/next.json"),
                         ("GET", "/install/agora-client-0.1.11.zip"), ("POST", "/update/cysr/next.json"),
                         ("GET", "/update/cysr/releases/5.json.minisig.bak"), ("GET", "/update/cysr/releases/05.json"),
                         ("GET", "/update/cysr/releases/6.json"))
        self.assertEqual([g["status"] for g in got], [404, 404, 404, 404, 404, 405, 404, 404, 404])

    def test_cf_route_probe_dry_run_only(self):
        """탐침 스크립트 기본 = 드라이런(네트워크·CF 0) — 실행은 master 의 --execute 만."""
        r = run(["bash", os.path.join(UPD, "cf-route-probe.sh")], env=dict(os.environ, WRANGLER="false"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("드라이런", r.stdout)
        self.assertIn("/update/__route_probe/*", r.stdout)
        self.assertEqual(run(["bash", os.path.join(UPD, "cf-route-probe.sh"), "--bogus"]).returncode, 2)

    def test_tombstone_pointer_is_404(self):
        open(os.path.join(self.st, "ptr", "update", "cysr", "next.json"), "wb").write(b'{"tombstone": true}\n')
        self.assertEqual([g["status"] for g in self.serve(("GET", "/update/cysr/next.json"),
                                                         ("GET", "/update/cysr/next.json.minisig"))], [404, 404])

    def test_mut_object_tampered_is_502(self):
        ptr = json.load(open(os.path.join(self.st, "ptr", "update", "cysr", "next.json")))
        with open(os.path.join(self.st, ptr["json"]), "ab") as f:
            f.write(b" ")
        got = self.serve(("GET", "/update/cysr/next.json"), ("GET", "/update/cysr/next.json.minisig"))
        self.assertEqual([g["status"] for g in got], [502, 502])  # 2R: 쌍의 한쪽만 나가는 일 0


def hdiutil_retry(args, partial=None, runner=None, delay=1.0, force_retry=False):
    """hdiutil 1회 재시도(1.1.10 · 맥 러너 간헐 실패 10-07 37543589887 = create CalledProcessError · 사유 미출력).
    실패 사유(rc·stderr)를 그 자리에서 stderr 로 내고 1회만 다시 한다 — 성공 = [] · 2회 실패 = 사유 2줄(호출자가 적색).
    partial = 실패한 create 가 남긴 반쪽 dmg(재시도 전에 지운다). 계약 약화 0: 건너뛰기 없음 · 재시도는 1회뿐.
    force_retry = 재시도에 -force 를 붙인다(1.1.11 · detach 전용 — 바쁜 볼륨에 같은 일반 분리를 또 부르지 않는다)."""
    runner = runner or run
    reasons = []
    for attempt in (1, 2):
        if attempt == 2 and force_retry:
            args = list(args) + ["-force"]
        r = runner(["hdiutil"] + list(args))
        if r.returncode == 0:
            return []
        reasons.append("시도%d rc=%d stderr=%s" % (attempt, r.returncode, (r.stderr or "").strip() or "(빈)"))
        sys.stderr.write("[hdiutil %s] %s\n" % (args[0], reasons[-1]))
        if partial and os.path.exists(partial):
            os.unlink(partial)
        if attempt == 1:
            time.sleep(delay)
    return reasons


FAKE_CURL = r"""#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
out = fmt = None
fail = False
i = 0
while i < len(a):
    x = a[i]
    if x in ("-o", "-w", "--proto", "--max-redirs"):
        if x == "-o":
            out = a[i + 1]
        if x == "-w":
            fmt = a[i + 1]
        i += 2
        continue
    if x.startswith("-") and not x.startswith("--") and "f" in x:
        fail = True
    i += 1
url = a[-1]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(url + "\n")
codes = json.loads(os.environ["FAKE_CODES"])
code = next((v for k, v in codes.items() if url.endswith(k)), 404)
if code == "net":
    if fmt:
        sys.stdout.write("000")
    sys.stderr.write("curl: (6) Could not resolve host\n")
    sys.exit(6)
if fail and code >= 400:
    sys.stderr.write("curl: (22) The requested URL returned error: %d\n" % code)
    sys.exit(22)
body = os.path.join(os.environ["FAKE_BODIES"], url.rsplit("/", 1)[-1])
data = open(body, "rb").read() if code == 200 and os.path.exists(body) else b"<html>%d</html>" % code
if out:
    open(out, "wb").write(data)
if fmt:
    sys.stdout.write(str(code))
"""


class TestRefreshFeedFetch(unittest.TestCase):
    """refresh-feed.yml 「Fetch current envelope」 단계 셸을 실제로 돌린다(1.1.10 사전 검토 · master#4a059fc9 ③).
    종전엔 봉투 읽기 실패를 전부(403·5xx·DNS·TLS) 404 와 같이 「게시된 봉투 없음」 notice + exit 0 으로 처리해, 읽기 호스트가
    막히면 주간 재서명이 녹색으로 아무것도 안 하고 봉투가 만료됐다(자동 갱신 정지 · 무증상). 404 만 부재 · 그 밖 = 적색."""

    def step_script(self):
        s = open(os.path.join(ROOT, ".github", "workflows", "refresh-feed.yml"), encoding="utf-8").read()
        i = s.index("- name: Fetch current envelope")
        j = s.index("run: |\n", i) + len("run: |\n")
        lines = []
        for l in s[j:].splitlines():
            if l.strip() and not l.startswith(" " * 10):
                break
            lines.append(l[10:])
        sc = "\n".join(lines)
        sc = sc.replace("${{ github.event_name == 'workflow_dispatch' && inputs.first || false }}", "false")
        sc = sc.replace("${{ github.event_name == 'workflow_dispatch' && inputs.release_seq || '' }}", "")
        self.assertNotIn("${{", sc, "시험이 모르는 식이 단계에 생겼다 — 치환 목록 갱신")
        return sc

    def run_step(self, codes):
        d = tempfile.mkdtemp(prefix="rf-")
        self.addCleanup(shutil.rmtree, d, True)
        binp, bodies = os.path.join(d, "bin"), os.path.join(d, "bodies")
        os.makedirs(binp)
        os.makedirs(bodies)
        with open(os.path.join(binp, "curl"), "w") as f:
            f.write(FAKE_CURL)
        os.chmod(os.path.join(binp, "curl"), 0o755)
        rel = base64.b64encode(b'{"seq":1}').decode()
        for n, b in (("stable.json", json.dumps({"release": rel, "release_sig": rel})), ("stable.json.minisig", "sig"),
                     ("revocations.json", "{}"), ("revocations.json.minisig", "sig")):
            open(os.path.join(bodies, n), "w").write(b)
        out = os.path.join(d, "gh_out")
        env = dict(os.environ, PATH=binp + os.pathsep + os.environ["PATH"], C="cysr", CH="stable",
                   SITE="https://feed.invalid", GITHUB_OUTPUT=out, FAKE_CODES=json.dumps(codes),
                   FAKE_BODIES=bodies, FAKE_LOG=os.path.join(d, "log"))
        r = subprocess.run(["bash", "-c", self.step_script()], cwd=d, env=env, capture_output=True, text=True)
        outs = open(out).read() if os.path.exists(out) else ""
        return r, outs

    def test_404_is_absent_and_green(self):
        r, outs = self.run_step({"/stable.json": 404})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("skip=1", outs)
        self.assertIn("게시된 봉투 없음", r.stdout)

    def test_read_failures_are_red_not_absent(self):
        for code in (403, 500, 503, "net"):
            r, outs = self.run_step({"/stable.json": code})
            self.assertNotEqual(r.returncode, 0, "읽기 실패 %s 가 녹색으로 끝났다(봉투 만료 무증상)" % code)
            self.assertNotIn("skip=1", outs, code)
            self.assertIn("::error::", r.stdout, code)

    def test_signature_read_failure_is_red(self):
        r, outs = self.run_step({"/stable.json": 200, "/stable.json.minisig": 403})
        self.assertNotEqual(r.returncode, 0, "서명 읽기 실패가 녹색으로 끝났다")
        self.assertNotIn("skip=1", outs)

    def test_published_envelope_proceeds(self):
        r, outs = self.run_step({"/stable.json": 200, "/stable.json.minisig": 200, "/revocations.json": 200,
                                 "/revocations.json.minisig": 200})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("have=1", outs)
        self.assertIn("skip=0", outs)


class TestHdiutilRetry(unittest.TestCase):
    """hdiutil_retry 계약 — 가짜 runner(플랫폼 무관)."""

    def fake(self, rcs):
        calls = []
        def runner(argv):
            calls.append(argv)
            rc = rcs[len(calls) - 1]
            return subprocess.CompletedProcess(argv, rc, "", "" if rc == 0 else "hdiutil: create failed - 리소스 일시 사용 불가")
        return runner, calls

    def test_first_ok_no_retry(self):
        runner, calls = self.fake([0])
        self.assertEqual(hdiutil_retry(["create", "x"], runner=runner, delay=0), [])
        self.assertEqual(len(calls), 1)

    def test_transient_failure_retried_once(self):
        runner, calls = self.fake([1, 0])
        self.assertEqual(hdiutil_retry(["create", "x"], runner=runner, delay=0), [])
        self.assertEqual(len(calls), 2)

    def test_two_failures_report_reasons_no_third(self):
        tmp = tempfile.mkdtemp(prefix="hdi-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        partial = os.path.join(tmp, "m.dmg")
        open(partial, "w").close()
        runner, calls = self.fake([1, 1, 0])
        reasons = hdiutil_retry(["create", partial], partial=partial, runner=runner, delay=0)
        self.assertEqual(len(calls), 2, "재시도는 1회뿐")
        self.assertEqual(len(reasons), 2)
        self.assertIn("리소스 일시 사용 불가", reasons[0], "실패 사유(stderr)가 빠졌다")
        self.assertFalse(os.path.exists(partial), "반쪽 dmg 를 남기면 재시도 create 가 「파일 있음」으로 또 실패한다")

    def test_module_probe_survives_one_transient_create_failure(self):
        # 1.1.9: setUpModule 의 매체 전제 확인 — create 첫 실패·둘째 성공이면 통과(create 2 + attach 1 + detach 1).
        runner, calls = self.fake([1, 0, 0, 0])
        self.assertEqual(media_probe_failures(runner=runner, delay=0), [])
        self.assertEqual([c[1] for c in calls], ["create", "create", "attach", "detach"])

    def test_module_probe_two_failures_stay_a_module_error(self):
        # 둘 다 실패 = 사유가 실린 목록 → setUpModule 이 RuntimeError(모듈 오류 · 건너뛰기 아님). attach 는 부르지 않는다.
        runner, calls = self.fake([1, 1, 0])
        bad = media_probe_failures(runner=runner, delay=0)
        self.assertEqual([c[1] for c in calls], ["create", "create"], "재시도는 1회뿐 · 실패한 create 뒤에 attach 금지")
        self.assertEqual(len(bad), 1)
        self.assertIn("리소스 일시 사용 불가", bad[0], "실패 사유(stderr)가 빠졌다")
        mod = sys.modules[__name__]
        with mock.patch.object(mod, "REQUIRE_ALL", True), mock.patch.object(mod, "media_probe_failures", lambda: bad), \
                mock.patch.object(sys, "platform", "darwin"), mock.patch.object(shutil, "which", lambda n: "/usr/bin/" + n):
            with self.assertRaises(RuntimeError) as cm:
                setUpModule()
        self.assertIn(bad[0], str(cm.exception))
        self.assertIn("CYS_U3_REQUIRE_ALL=1 전제 부재", str(cm.exception))

    def test_module_probe_detach_failure_is_retried_then_a_module_error(self):
        # 1.1.10(ChatGPT A/B F2): 전제 확인의 detach rc 를 버리지 않는다 — 1회 실패는 사유를 찍고 다시 하고(통과),
        # 2회 실패는 사유가 실린 목록 = setUpModule 모듈 오류(마운트가 남은 채 「전제 통과」 로 읽히지 않는다).
        runner, calls = self.fake([0, 0, 1, 0])
        self.assertEqual(media_probe_failures(runner=runner, delay=0), [])
        self.assertEqual([c[1] for c in calls], ["create", "attach", "detach", "detach"])
        runner, calls = self.fake([0, 0, 1, 1, 0])
        bad = media_probe_failures(runner=runner, delay=0)
        # 1.1.11(B3): 분리 2회 실패면 임시 폴더를 남긴다(사유에 경로) — 가짜 runner 라 마운트가 없으니 여기서 치운다.
        shutil.rmtree(bad[0].split("마운트가 남아 ", 1)[1].split(" 를 지우지 않음", 1)[0], ignore_errors=True)
        self.assertEqual([c[1] for c in calls], ["create", "attach", "detach", "detach"], "재시도는 1회뿐")
        self.assertEqual(len(bad), 1)
        self.assertIn("detach", bad[0])
        self.assertIn("리소스 일시 사용 불가", bad[0], "실패 사유(stderr)가 빠졌다")

    def test_module_probe_detach_retry_is_forced_and_a_stuck_mount_is_not_rmtreed(self):
        # 1.1.11(review-a B3): 재시도 detach 는 -force 로(같은 일반 detach 를 또 부르면 바쁜 볼륨에서 같은 실패) ·
        # 2회 실패 = 마운트가 남았다는 뜻이라 임시 폴더를 rmtree 하지 않는다(볼륨 안으로 들어가 지운다).
        import re
        runner, calls = self.fake([0, 0, 1, 0])
        self.assertEqual(media_probe_failures(runner=runner, delay=0), [])
        self.assertNotIn("-force", calls[2], "첫 detach 는 일반 분리")
        self.assertIn("-force", calls[3], "재시도 detach 에 -force 가 없다")
        runner, calls = self.fake([0, 0, 1, 1])
        real_rmtree = shutil.rmtree
        with mock.patch.object(shutil, "rmtree") as rm:
            bad = media_probe_failures(runner=runner, delay=0)
        self.assertEqual(len(bad), 1)
        self.assertEqual(rm.call_count, 0, "분리 실패(마운트 남음)인데 임시 폴더를 rmtree 했다: %r" % rm.call_args_list)
        left = re.search(r"(\S*u3-req-\S+?)(?:\)|$| )", bad[0])
        self.assertIsNotNone(left, "남긴 임시 폴더 경로가 사유에 없다: %s" % bad[0])
        real_rmtree(left.group(1), ignore_errors=True)

    def test_every_create_and_attach_goes_through_the_retry_helper(self):
        # 배선 핀: 이 파일에서 hdiutil create·attach 를 도우미 밖에서 직접 부르는 줄은 0 이다(정리용 detach 는 재시도 대상 아님 ·
        # 모듈 전제의 detach 는 1.1.10 부터 도우미 경유).
        # 바늘은 조각으로 이어 이 줄이 자기 자신에 걸리지 않게 한다.
        src = open(os.path.abspath(__file__), encoding="utf-8").read()
        head = '["hdi' + 'util", "'
        for verb in ("create", "attach"):
            self.assertEqual(src.count(head + verb + '"'), 0, "hdiutil %s 직접 호출이 남았다 — hdiutil_retry 로 부른다" % verb)
        self.assertEqual(src.count('runner(["hdi' + 'util"] + list(args))'), 1, "도우미의 실행 줄이 사라졌거나 둘이 됐다")
        self.assertEqual(src.count("hdiutil_" + "retry(args, partial=partial"), 3, "도우미를 거치는 호출부 = 모듈 전제·첫 매체·둘째 매체")


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("hdiutil"), "가짜 매체 = hdiutil 마운트(맥 전용)")
class TestOfflineRitual(Base):
    def setUp(self):
        super().setUp()
        self.mnt = os.path.join(self.tmp, "mnt")
        os.makedirs(self.mnt)
        dmg = os.path.join(self.tmp, "m.dmg")
        for args, partial in ((["create", "-size", "4m", "-fs", "HFS+", "-volname", "U3FAKE", "-quiet", dmg], dmg),
                              (["attach", dmg, "-mountpoint", self.mnt, "-nobrowse", "-quiet"], None)):
            reasons = hdiutil_retry(args, partial=partial)
            if reasons:
                self.fail("가짜 매체 준비 실패(hdiutil %s · 2회): %s" % (args[0], " | ".join(reasons)))
        for k in ("u", "r"):
            shutil.move(self.fx.key(k), os.path.join(self.mnt, k + ".key"))
        self.mini = os.path.join(self.tmp, "mini.sh")
        open(self.mini, "w").write('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, FAKE))
        os.chmod(self.mini, 0o755)
        self.env = dict(os.environ, MINISIGN=self.mini, CYS_SIGN_MEDIA_PREFIX=self.tmp + "/")
        # 시험용 사본 트리(3판 · 2R #3): 실 스크립트·모듈은 심링크 · lib/offline-sign.sh 만 「실 lib + 시험 대역」 두 줄.
        self.dev = os.path.join(self.tmp, "upd-dev")
        os.makedirs(os.path.join(self.dev, "lib"))
        for n in os.listdir(UPD):
            if n not in ("lib", "__pycache__"):
                os.symlink(os.path.join(UPD, n), os.path.join(self.dev, n))
        open(os.path.join(self.dev, "lib", "offline-sign.sh"), "w").write(
            '. "%s"\n. "%s"\n' % (os.path.join(UPD, "lib", "offline-sign.sh"), os.path.join(UPD, "lib", "offline-sign-dev.sh")))

    def tearDown(self):
        subprocess.call(["hdiutil", "detach", self.mnt, "-quiet"])
        super().tearDown()

    def sign(self, body, key, out, media=None):
        return run(["bash", os.path.join(self.dev, "sign-release.sh"), "--body", body, "--media", media or self.mnt,
                    "--key", key, "--keyring", self.fx.keyring, "--out-dir", out, "--wait-eject", "0"], env=self.env)

    def unsigned_body(self):
        out = os.path.join(self.tmp, "b.json")
        self.assertEqual(py("make-release-json.py", *self.fx.gen_args(out)).returncode, 0)
        return out

    def test_happy_and_no_key_copy(self):
        b = self.unsigned_body()
        r = self.sign(b, os.path.join(self.mnt, "u.key"), os.path.join(self.tmp, "out"))
        self.assertEqual(r.returncode, 0, r.stderr)
        sig = os.path.join(self.tmp, "out", "cysr-release-5.json.minisig")
        self.assertTrue(fm.verify(os.path.join(self.tmp, "u.pub"), os.path.join(self.tmp, "out", "cysr-release-5.json"), sig))
        secret = open(os.path.join(self.mnt, "u.key")).read().splitlines()[1]
        for dp, _, fns in os.walk(self.tmp):
            if dp.startswith(self.mnt):
                continue
            for n in fns:
                if n == "m.dmg":
                    continue  # 매체 자체(가짜 매체의 디스크 이미지 = 키가 있어야 하는 곳)
                found = secret in open(os.path.join(dp, n), errors="ignore").read()
                self.assertFalse(found, "개인키가 매체 밖 파일에 복사됨: %s" % os.path.join(dp, n))
        self.assertEqual(sorted(os.listdir(self.mnt)) and [n for n in os.listdir(self.mnt) if n.startswith(".cys-sign")], [])

    def test_mut_key_outside_media(self):
        b = self.unsigned_body()
        local = os.path.join(self.tmp, "u-local.key")
        shutil.copy(os.path.join(self.mnt, "u.key"), local)
        r = self.sign(b, local, os.path.join(self.tmp, "out"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("매체 아래가 아니다", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "out", "cysr-release-5.json.minisig")))

    def test_mut_media_not_mountpoint(self):
        b = self.unsigned_body()
        fake = os.path.join(self.tmp, "notmnt")
        os.makedirs(fake)
        shutil.copy(os.path.join(self.mnt, "u.key"), os.path.join(fake, "u.key"))
        r = self.sign(b, os.path.join(fake, "u.key"), os.path.join(self.tmp, "out"), media=fake)
        self.assertEqual(r.returncode, 2)
        self.assertIn("마운트 지점이 아니다", r.stderr)

    def test_mut_symlink_key(self):
        b = self.unsigned_body()
        link = os.path.join(self.mnt, "link.key")
        os.symlink(os.path.join(self.mnt, "u.key"), link)
        r = self.sign(b, link, os.path.join(self.tmp, "out"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("심링크", r.stderr)

    def test_mut_wrong_key_for_body(self):
        b = self.unsigned_body()
        r = self.sign(b, os.path.join(self.mnt, "r.key"), os.path.join(self.tmp, "out"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("다른 키", r.stderr)

    def test_revocations_ritual(self):
        doc = os.path.join(self.tmp, "rev.json")
        py("make-revocations.py", "--key-id", self.fx.kid("r"), "--keyring", self.fx.keyring, "--first", "--out", doc)
        r = run(["bash", os.path.join(self.dev, "sign-revocations.sh"), "--doc", doc, "--media", self.mnt,
                 "--key", os.path.join(self.mnt, "r.key"), "--keyring", self.fx.keyring,
                 "--out-dir", os.path.join(self.tmp, "rout"), "--wait-eject", "0"], env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)

    # ── 1.1.19 CO-L3(DESIGN §11-5 · TICKET=cysr-1119-s16): 함수 안 명시 검사 · 매체 잔여물 0 · 작업트리 검사(--expect-head) ──
    def _shim_env(self, fail_cp="", fail_mv=""):
        """PATH 앞에 cp·mv 대역 — 인자 하나가 패턴(case 꼴)에 맞으면 그 호출만 실패(rc 1) · 나머지는 /bin 실물."""
        d = os.path.join(self.tmp, "shim")
        os.makedirs(d, exist_ok=True)
        for cmd, pat in (("cp", fail_cp), ("mv", fail_mv)):
            body = '#!/bin/sh\nfor a in "$@"; do case "$a" in %s) echo "shim: %s 실패 주입 $a" >&2; exit 1 ;; esac; done\nexec /bin/%s "$@"\n' % (
                pat or "__never__", cmd, cmd)
            open(os.path.join(d, cmd), "w").write(body)
            os.chmod(os.path.join(d, cmd), 0o755)
        return dict(self.env, PATH=d + os.pathsep + os.environ.get("PATH", ""))

    def _media_residue(self):
        return [n for n in os.listdir(self.mnt) if n.startswith(".cys-sign")]

    def _sign_env(self, body, out, env, extra=()):
        return run(["bash", os.path.join(self.dev, "sign-release.sh"), "--body", body, "--media", self.mnt,
                    "--key", os.path.join(self.mnt, "u.key"), "--keyring", self.fx.keyring, "--out-dir", out,
                    "--wait-eject", "0", *extra], env=env)

    def _counting_minisign(self, tamper=False):
        """가짜 minisign 감싸개 — 부른 횟수를 적고(tamper 면 서명 뒤 -m 파일 1바이트 덧붙임 = 매체 쪽 대상 바뀜)."""
        log = os.path.join(self.tmp, "mini-calls.txt")
        w = os.path.join(self.tmp, "mini-count.sh")
        open(w, "w").write(
            '#!/bin/sh\necho "$1" >> "%s"\nm=""; prev=""\nfor a in "$@"; do [ "$prev" = "-m" ] && m="$a"; prev="$a"; done\n'
            '"%s" "%s" "$@" || exit $?\n%s\n' % (log, sys.executable, FAKE,
                                                  '[ "$1" = "-S" ] && printf x >> "$m"' if tamper else ":"))
        os.chmod(w, 0o755)
        return w, log

    def test_co_l3_mv_failure_is_not_success(self):
        """⑴ 실결함: 서명을 산출 자리로 옮기는 mv 가 실패하면 1.1.18 은 함수가 0 을 돌려 「✅ U 의식 통과」(서명 없이 본문만) — 이제 rc 2 · 산출 0."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        r = self._sign_env(b, out, self._shim_env(fail_mv="*.minisig"))
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        # (codex 1R B5) 주입이 실제로 mv 지점에 닿았음을 단언 — 앞 단계의 다른 실패로 초록이 되지 않게
        self.assertIn("shim: mv 실패 주입", r.stderr)
        self.assertIn("서명을 산출 자리로 옮기지 못했다(mv 실패)", r.stderr)
        self.assertNotIn("통과", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(out, "cysr-release-5.json.minisig")))
        self.assertFalse(os.path.exists(os.path.join(out, "cysr-release-5.json")))
        self.assertEqual(self._media_residue(), [])

    def test_co_l3_sig_copy_out_failure_stops_before_eject(self):
        """⑴ 매체에서 서명을 꺼내는 cp(:110) 실패 = 그 자리에서 rc 2(빈 서명으로 매체 빼기·검증까지 가지 않음) · 매체 잔여물 0."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        r = self._sign_env(b, out, self._shim_env(fail_cp="*/.cys-sign-*/doc.minisig"))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("서명을 꺼내지 못했다", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(out, "cysr-release-5.json.minisig")))
        self.assertEqual(self._media_residue(), [])

    def test_co_l3_doc_copy_failure_refuses_before_minisign(self):
        """⑵ 서명 대상을 매체로 옮기는 cp(:101) 실패 = minisign 을 부르지 않고(비밀번호를 묻지 않음) rc 2 · 매체 잔여물 0."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        w, log = self._counting_minisign()
        env = dict(self._shim_env(fail_cp="*/.cys-sign-*/doc"), MINISIGN=w)
        r = self._sign_env(b, out, env)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("매체로 옮기지 못했다", r.stderr)
        self.assertFalse(os.path.exists(log), "서명 대상이 없는데 minisign 을 불렀다")
        self.assertEqual(self._media_residue(), [])

    def test_co_l3_media_doc_changed_leaves_no_residue(self):
        """⑶ 매체 쪽 서명 대상이 서명 중 바뀜 = 거부(rc 2) · 매체에 doc·doc.minisig·작업 폴더 잔여물 0 · 산출 0."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        w, _ = self._counting_minisign(tamper=True)
        r = self._sign_env(b, out, dict(self.env, MINISIGN=w))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("바뀌었다", r.stderr)
        self.assertEqual(self._media_residue(), [])
        self.assertFalse(os.path.exists(os.path.join(out, "cysr-release-5.json.minisig")))

    def _git_tree(self, script_text=None):
        """git 저장소 안의 시험 사본 트리(<g>/scripts/update = 실 파일 심링크 · lib = 실 lib + 시험 대역) · 커밋 1. → (g, head, sign 경로)."""
        g = os.path.join(self.tmp, "g")
        upd = os.path.join(g, "scripts", "update")
        os.makedirs(os.path.join(upd, "lib"))
        for n in os.listdir(UPD):
            if n not in ("lib", "__pycache__", "sign-release.sh"):
                os.symlink(os.path.join(UPD, n), os.path.join(upd, n))
        if script_text is None:
            os.symlink(os.path.join(UPD, "sign-release.sh"), os.path.join(upd, "sign-release.sh"))
        else:
            open(os.path.join(upd, "sign-release.sh"), "w").write(script_text)
        open(os.path.join(upd, "lib", "offline-sign.sh"), "w").write(
            '. "%s"\n. "%s"\n' % (os.path.join(UPD, "lib", "offline-sign.sh"), os.path.join(UPD, "lib", "offline-sign-dev.sh")))
        open(os.path.join(g, "README"), "w").write("x\n")
        genv = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_AUTHOR_NAME="t",
                    GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        for a in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "t"]):
            self.assertEqual(run(["git", "-C", g, *a], env=genv).returncode, 0, a)
        head = run(["git", "-C", g, "rev-parse", "HEAD"]).stdout.strip()
        return g, head, os.path.join(upd, "sign-release.sh")

    def _sign_at(self, script, body, out, extra=()):
        return run(["bash", script, "--body", body, "--media", self.mnt, "--key", os.path.join(self.mnt, "u.key"),
                    "--keyring", self.fx.keyring, "--out-dir", out, "--wait-eject", "0", *extra], env=self.env)

    def test_co_l3_expect_head_clean_tree_passes(self):
        """(L4) --expect-head = HEAD 와 같고 작업트리가 깨끗하면 통과(rc 0 · 서명 검증)."""
        g, head, script = self._git_tree()
        b = self.unsigned_body()
        r = self._sign_at(script, b, os.path.join(self.tmp, "out"), ("--expect-head", head))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "out", "cysr-release-5.json.minisig")))

    def test_co_l3_expect_head_refuses_dirty_or_other_head(self):
        """(L4) HEAD 다름 · 추적 파일 바뀜 · 추적 안 된 새 파일 = 각각 rc 2 · 산출 0 · 매체에 손대기 전."""
        g, head, script = self._git_tree()
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        other = ("0" if head[0] != "0" else "1") + head[1:]
        r = self._sign_at(script, b, out, ("--expect-head", other))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("HEAD", r.stderr)
        open(os.path.join(g, "README"), "a").write("y\n")
        r = self._sign_at(script, b, out, ("--expect-head", head))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("커밋 안 된 변경", r.stderr)
        run(["git", "-C", g, "checkout", "-q", "--", "README"])
        open(os.path.join(g, "new.txt"), "w").write("n\n")
        r = self._sign_at(script, b, out, ("--expect-head", head))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(out, "cysr-release-5.json.minisig")))
        self.assertEqual(self._media_residue(), [])

    def test_co_l3_expect_head_outside_git_is_refused(self):
        """(L4 · master#26ecbe64 조건 ②) 인자를 줬는데 git 저장소가 아니면 통과가 아니라 rc 2(닫힌 쪽) — 기존 사본 트리 = git 밖."""
        b = self.unsigned_body()
        self.assertNotEqual(run(["git", "-C", os.path.dirname(os.path.dirname(self.dev)), "rev-parse", "--show-toplevel"]).stdout.strip(),
                            os.path.realpath(os.path.dirname(os.path.dirname(self.dev))))
        r = run(
            ["bash", os.path.join(self.dev, "sign-release.sh"), "--body", b, "--media", self.mnt, "--key", os.path.join(self.mnt, "u.key"),
             "--keyring", self.fx.keyring, "--out-dir", os.path.join(self.tmp, "out"), "--wait-eject", "0", "--expect-head", "a" * 40], env=self.env)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("git 작업트리가 아니다", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "out", "cysr-release-5.json.minisig")))

    def test_co_l3_no_flag_same_as_1118(self):
        """(L4 · master#26ecbe64 조건 ①) 인자를 안 주면 1.1.18(838f24421) sign-release.sh 와 같은 동작 — 더러운 git 트리에서도 끝 코드·출력 같음."""
        # 1.1.18 판 = 고정 자료(바이트 동일 사본) — CI 체크아웃은 얕은 받기라 838f24421 객체가 없다(TICKET=cysr-1119-integ2 · run 45374218639).
        raw = open(SIGN_1118_FIXTURE, "rb").read()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SIGN_1118_SHA256, "고정 자료가 바뀌었다")
        spec = "838f24421:scripts/update/sign-release.sh"
        if run(["git", "-C", ROOT, "cat-file", "-e", spec]).returncode == 0:  # 객체가 있는 환경(전체 받기) = 자료 == 원본
            base = subprocess.run(["git", "-C", ROOT, "show", spec], capture_output=True)
            self.assertEqual(base.returncode, 0, base.stderr)
            self.assertEqual(base.stdout, raw, "고정 자료 ≠ git show " + spec)
        res = []
        for tag, text in (("new", None), ("old", raw.decode("utf-8"))):
            g, head, script = self._git_tree(text)
            open(os.path.join(g, "README"), "a").write("dirty\n")  # 더러움 — 인자 없으면 검사 0
            out = os.path.join(self.tmp, "out-" + tag)
            r = self._sign_at(script, self.unsigned_body(), out)
            res.append((r.returncode, r.stdout.replace(out, "<OUT>"), r.stderr.replace(out, "<OUT>")))
            shutil.rmtree(g)
        self.assertEqual(res[0][0], 0, res[0][2])
        self.assertEqual(res[0], res[1])

    # ── codex 1R(TICKET=fix-1119-codex-r1) B1·B2: --expect-head 가 검사를 조용히 건너뛰거나 더러움을 못 보는 길 ──
    def _git(self, g, *a):
        genv = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_AUTHOR_NAME="t",
                    GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        r = run(["git", "-C", g, *a], env=genv)
        self.assertEqual(r.returncode, 0, (a, r.stderr))
        return r.stdout

    def test_co_l3_b1_expect_head_empty_or_missing_value_refused(self):
        """B1: 인자를 「줬는가」 와 「값」 을 따로 본다 — 빈 값 · 값 없이 끝남 · 두 번째에 빈 값 = 전부 rc 2(검사를 건너뛰지 않음 · 산출 0)."""
        g, head, script = self._git_tree()
        open(os.path.join(g, "README"), "a").write("dirty\n")  # 더러운 트리 — 검사를 건너뛰면 서명까지 간다
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        for extra, why in ((("--expect-head", ""), "40자 소문자 sha"), (("--expect-head",), "값이 없다"),
                           (("--expect-head", head, "--expect-head", ""), "두 번 줬다")):
            with self.subTest(extra=extra):
                r = self._sign_at(script, b, out, extra)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("--expect-head", r.stderr)
                self.assertIn(why, r.stderr)
                self.assertFalse(os.path.exists(os.path.join(out, "cysr-release-5.json.minisig")))
                self.assertEqual(self._media_residue(), [])

    def test_co_l3_b2_hidden_dirt_refused(self):
        """B2: git 설정·색인 표시·무시 규칙으로 숨은 더러움 = rc 2. 각 칸은 대조로 「옛 검사(git status --porcelain)에는 안 보임」 을 먼저 단언한다."""
        g, _, script = self._git_tree()
        open(os.path.join(g, ".gitignore"), "w").write("__pycache__/\n*.log\n")
        self._git(g, "add", ".gitignore")
        self._git(g, "commit", "-q", "-m", "ignore")
        head = self._git(g, "rev-parse", "HEAD").strip()
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")

        def plain_status():
            return self._git(g, "status", "--porcelain")

        def case_show_untracked_no():
            self._git(g, "config", "status.showUntrackedFiles", "no")
            open(os.path.join(g, "new.txt"), "w").write("n\n")
            return lambda: (os.remove(os.path.join(g, "new.txt")), self._git(g, "config", "--unset", "status.showUntrackedFiles"))

        def case_ignored_under_update():
            open(os.path.join(g, "scripts", "update", "stray.log"), "w").write("x\n")
            return lambda: os.remove(os.path.join(g, "scripts", "update", "stray.log"))

        def case_assume_unchanged():
            open(os.path.join(g, "README"), "a").write("hidden\n")
            self._git(g, "update-index", "--assume-unchanged", "README")
            return lambda: (self._git(g, "update-index", "--no-assume-unchanged", "README"), self._git(g, "checkout", "-q", "--", "README"))

        def case_skip_worktree():
            open(os.path.join(g, "README"), "a").write("hidden\n")
            self._git(g, "update-index", "--skip-worktree", "README")
            return lambda: (self._git(g, "update-index", "--no-skip-worktree", "README"), self._git(g, "checkout", "-q", "--", "README"))

        def case_stat_preserved_edit():
            # 색인 표시 0 · 크기·mtime 같게 고치고 사용자 설정 core.checkStat=minimal·trustctime=false → status 는 stat 만 믿고 「깨끗」
            rp = os.path.join(g, "README")
            time.sleep(1.1)  # 앞 칸 checkout 직후의 「racy」 항목(git 이 내용을 다시 읽음)을 피함 → 색인 stat 을 안정된 값으로 다시 적음
            self._git(g, "update-index", "--refresh")
            st = os.stat(rp)
            data = open(rp, "rb").read()
            open(rp, "wb").write(data.replace(b"x", b"z", 1))
            os.utime(rp, ns=(st.st_atime_ns, st.st_mtime_ns))
            self._git(g, "config", "core.checkStat", "minimal")
            self._git(g, "config", "core.trustctime", "false")
            return lambda: (self._git(g, "config", "--unset", "core.checkStat"), self._git(g, "config", "--unset", "core.trustctime"),
                            open(rp, "wb").write(data), self._git(g, "update-index", "--refresh"))

        def case_clean_filter():
            # 로컬 .git/info/attributes + 로컬 설정의 clean 필터가 작업 파일을 HEAD 내용으로 「씻어」 status 에 안 보이게 함
            rp = os.path.join(g, "README")
            orig = open(rp, "rb").read()
            open(rp, "wb").write(orig.replace(b"x", b"q", 1))  # 같은 크기(크기가 바뀌면 git 은 필터 없이 「바뀜」 판정 = 숨지 않음)
            os.makedirs(os.path.join(g, ".git", "info"), exist_ok=True)
            open(os.path.join(g, ".git", "info", "attributes"), "w").write("README filter=hide\n")
            self._git(g, "config", "filter.hide.clean", "printf 'x\\n'")
            def undo():
                os.remove(os.path.join(g, ".git", "info", "attributes"))
                self._git(g, "config", "--remove-section", "filter.hide")
                open(rp, "wb").write(orig)
                self._git(g, "update-index", "--refresh")
            return undo

        def case_flag_only():
            # 내용은 그대로지만 assume-unchanged 표시만 있음 — 표시 자체가 다음 수정을 숨기므로 거부(브리프 규칙)
            self._git(g, "update-index", "--assume-unchanged", "README")
            return lambda: self._git(g, "update-index", "--no-assume-unchanged", "README")

        # 이 칸에서 꼭 나와야 할 거부 글(어느 겹이 잡았는지) — None = 겹이 여럿이라 어느 것이든
        for name, case, why in (("status.showUntrackedFiles=no", case_show_untracked_no, "커밋 안 된 변경"),
                                ("scripts/update 아래 무시된 파일", case_ignored_under_update, "서명 코드 자리"),
                                ("assume-unchanged", case_assume_unchanged, None),
                                ("skip-worktree", case_skip_worktree, None),
                                ("stat 보존 수정(checkStat=minimal)", case_stat_preserved_edit, "내용 ≠ HEAD README"),
                                ("clean 필터(info/attributes)", case_clean_filter, "내용 ≠ HEAD README"),
                                ("표시만(내용 같음)", case_flag_only, "색인에")):
            with self.subTest(case=name):
                undo = case()
                out = os.path.join(self.tmp, "out-" + str(abs(hash(name))))  # 칸마다 산출 자리 따로(한 칸 실패가 다음 칸으로 번지지 않게)
                try:
                    self.assertEqual(plain_status(), "", "대조 실패: 이 우회가 옛 검사에 이미 보인다 — 시험이 우회를 재현하지 못함")
                    r = self._sign_at(script, b, out, ("--expect-head", head))
                    self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                    self.assertIn("거부", r.stderr)
                    if why:
                        self.assertIn(why, r.stderr)
                    self.assertFalse(os.path.exists(os.path.join(out, "cysr-release-5.json.minisig")))
                    self.assertEqual(self._media_residue(), [])
                finally:
                    undo()
                self.assertEqual(plain_status(), "")

    def test_co_l3_b2_checkout_eol_conversion_is_clean(self):
        """B2 거짓 거부 0: 저장소 .gitattributes 의 `*.nsh text eol=crlf`(실 저장소 :70 · src-tauri/nsis-hooks.nsh) — 색인 LF · 작업 파일 CRLF 는 깨끗.
        같은 파일 내용을 고치면 거부(바이트 대조가 git 내장 변환으로만 풀림)."""
        g, _, script = self._git_tree()
        open(os.path.join(g, ".gitattributes"), "w").write("* text=auto eol=lf\n*.nsh text eol=crlf\n")
        open(os.path.join(g, "hooks.nsh"), "wb").write(b"!macro A\r\n!macroend\r\n")
        self._git(g, "add", ".gitattributes", "hooks.nsh")
        self._git(g, "commit", "-q", "-m", "crlf")
        head = self._git(g, "rev-parse", "HEAD").strip()
        self.assertEqual(run(["git", "-C", g, "cat-file", "-p", head + ":hooks.nsh"]).stdout, "!macro A\n!macroend\n")  # 색인 = LF
        self.assertEqual(open(os.path.join(g, "hooks.nsh"), "rb").read(), b"!macro A\r\n!macroend\r\n")  # 작업 파일 = CRLF
        self.assertEqual(self._git(g, "status", "--porcelain"), "")
        b = self.unsigned_body()
        r = self._sign_at(script, b, os.path.join(self.tmp, "out-a"), ("--expect-head", head))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        open(os.path.join(g, "hooks.nsh"), "wb").write(b"!macro B\r\n!macroend\r\n")
        r = self._sign_at(script, b, os.path.join(self.tmp, "out-b"), ("--expect-head", head))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "out-b", "cysr-release-5.json.minisig")))

    def test_co_l3_b2_ignored_outside_and_pycache_allowed_but_not_read(self):
        """B2 경계: 서명 코드 자리 밖의 무시된 파일(빌드 산출 꼴) · scripts/update/__pycache__ 는 막지 않는다 —
        단 __pycache__ 는 읽히지도 않아야 한다(PYTHONPYCACHEPREFIX): update_common 을 가로채는 pyc 를 심어도 서명이 정상 통과."""
        g, _, script = self._git_tree()
        open(os.path.join(g, ".gitignore"), "w").write("__pycache__/\n*.log\ntarget/\n")
        self._git(g, "add", ".gitignore")
        self._git(g, "commit", "-q", "-m", "ignore")
        head = self._git(g, "rev-parse", "HEAD").strip()
        os.makedirs(os.path.join(g, "target"))
        open(os.path.join(g, "target", "build.log"), "w").write("x\n")
        src = os.path.join(g, "scripts", "update", "update_common.py")
        hijack = run(["python3", "-c", (
            "import importlib.util as u, importlib._bootstrap_external as e, os, sys\n"
            "src = sys.argv[1]; st = os.stat(src)\n"
            "code = compile('import sys\\nprint(\\'PYC-HIJACK\\', file=sys.stderr)\\nsys.exit(7)\\n', src, 'exec')\n"
            "pyc = u.cache_from_source(src); os.makedirs(os.path.dirname(pyc), exist_ok=True)\n"
            "open(pyc, 'wb').write(e._code_to_timestamp_pyc(code, int(st.st_mtime), st.st_size))\n"
            "print(pyc)\n"), src])
        self.assertEqual(hijack.returncode, 0, hijack.stderr)
        pyc = hijack.stdout.strip()
        self.assertTrue(pyc.startswith(os.path.join(g, "scripts", "update", "__pycache__")), pyc)
        # 대조: 가로채기 pyc 가 실제로 먹힌다(PYTHONPYCACHEPREFIX 없이 같은 python3 로 import)
        probe = run(["python3", "-c", "import sys; sys.path.insert(0, sys.argv[1]); import update_common",
                     os.path.dirname(src)], env={k: v for k, v in os.environ.items() if not k.startswith("PYTHONPYCACHE")})
        self.assertEqual(probe.returncode, 7, probe.stderr)
        self.assertIn("PYC-HIJACK", probe.stderr)
        self.assertEqual(self._git(g, "status", "--porcelain"), "")
        before = open(pyc, "rb").read()
        r = self._sign_at(script, self.unsigned_body(), os.path.join(self.tmp, "out"), ("--expect-head", head))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("PYC-HIJACK", r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "out", "cysr-release-5.json.minisig")))
        self.assertEqual(open(pyc, "rb").read(), before)  # 서명 실행이 source 트리 pyc 를 읽지도 고쳐 쓰지도 않음

    # ── 1.1.20(TICKET=cysr-1120-integ2) #39 python -I · F8 해시 실패 · F9 본문 먼저 · B3 정리 실패 · B4 신호 정리 ──────────
    def _shim_env_any(self, base=None, **pats):
        """PATH 앞에 명령 대역 — pats = {명령: case 패턴}. 인자 하나가 패턴에 맞으면 그 호출만 rc 1(「shim: <명령> 실패 주입」) · 나머지 = 실물."""
        d = tempfile.mkdtemp(prefix="shim2-", dir=self.tmp)  # 부를 때마다 새 폴더(앞 대역이 남지 않게)
        for cmd, pat in pats.items():
            real = shutil.which(cmd, path="/bin:/usr/bin")
            body = '#!/bin/sh\nfor a in "$@"; do case "$a" in %s) echo "shim: %s 실패 주입 $a" >&2; exit 1 ;; esac; done\nexec %s "$@"\n' % (pat, cmd, real)
            open(os.path.join(d, cmd), "w").write(body)
            os.chmod(os.path.join(d, cmd), 0o755)
        e = dict(base or self.env)
        e["PATH"] = d + os.pathsep + e.get("PATH", os.environ.get("PATH", ""))
        return e

    def _out_files(self, out):
        return sorted(os.listdir(out)) if os.path.isdir(out) else []

    def test_i20_cwd_module_hijack_not_read(self):
        """#39: 의식 스크립트의 python3 는 지금 폴더의 json.py·hashlib.py 를 읽지 않는다(-I) — 대조: 같은 폴더에서 맨 python3 -c 는 먹힌다."""
        evil = os.path.join(self.tmp, "evil")
        os.makedirs(evil)
        marker = os.path.join(self.tmp, "hijack-marker.txt")
        for mod in ("json", "hashlib", "secrets"):
            open(os.path.join(evil, mod + ".py"), "w").write(
                "open(%r, 'a').write(%r + '\\n')\nraise SystemExit(9)\n" % (marker, mod))
        ctl = run(["python3", "-c", "import hashlib"], cwd=evil)
        self.assertEqual(ctl.returncode, 9, ctl.stderr)  # 대조: 심은 모듈이 실제로 먹힌다
        self.assertTrue(os.path.exists(marker))
        os.remove(marker)
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        r = run(["bash", os.path.join(self.dev, "sign-release.sh"), "--body", b, "--media", self.mnt,
                 "--key", os.path.join(self.mnt, "u.key"), "--keyring", self.fx.keyring, "--out-dir", out, "--wait-eject", "0"],
                env=self.env, cwd=evil)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(marker), open(marker).read() if os.path.exists(marker) else "")
        doc = os.path.join(self.tmp, "rev.json")
        py("make-revocations.py", "--key-id", self.fx.kid("r"), "--keyring", self.fx.keyring, "--first", "--out", doc)
        r = run(["bash", os.path.join(self.dev, "sign-revocations.sh"), "--doc", doc, "--media", self.mnt,
                 "--key", os.path.join(self.mnt, "r.key"), "--keyring", self.fx.keyring,
                 "--out-dir", os.path.join(self.tmp, "rout"), "--wait-eject", "0"], env=self.env, cwd=evil)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(marker))
        for n in ("lib/offline-sign.sh", "sign-release.sh", "sign-revocations.sh", "gen-offline-key.sh", "cf-route-probe.sh",
                  "collect-inputs.sh", "lib/offline-sign-dev.sh"):  # 1.1.21 N low3: 1.1.20 에 -I 를 넣은 두 파일도 핀
            code = [l for l in open(os.path.join(UPD, n), encoding="utf-8").read().splitlines() if not l.lstrip().startswith("#")]
            bare = [l for l in code if re.search(r"\bpython3\s+(?!-I\b)", l)]
            self.assertEqual(bare, [], n)

    def test_i20_f8_hash_failure_is_refusal(self):
        """F8: offline_sha256 = 계산 실패·빈 출력 = rc 2(빈 값끼리 「같다」 0) · offline_sign 의 두 해시 자리가 이 함수를 쓴다."""
        lib = os.path.join(UPD, "lib", "offline-sign.sh")
        r = run(["bash", "-c", '. "$1"; offline_sha256 "$2"', "_", lib, os.path.join(self.tmp, "none")])
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("sha256 을 계산하지 못했다", r.stderr)
        fake = os.path.join(self.tmp, "fakepy")
        os.makedirs(fake)
        open(os.path.join(fake, "python3"), "w").write("#!/bin/sh\nexit 0\n")  # 아무것도 안 찍고 rc 0
        os.chmod(os.path.join(fake, "python3"), 0o755)
        f = os.path.join(self.tmp, "x.txt")
        open(f, "w").write("x")
        r = run(["bash", "-c", '. "$1"; offline_sha256 "$2"', "_", lib, f], env=dict(os.environ, PATH=fake + ":/usr/bin:/bin"))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("sha256 형식이 아니다", r.stderr)
        r = run(["bash", "-c", '. "$1"; offline_sha256 "$2"', "_", lib, f])
        self.assertEqual((r.returncode, r.stdout.strip()), (0, hashlib.sha256(b"x").hexdigest()))
        body = open(lib, encoding="utf-8").read()
        sign = body[body.index("_offline_sign_body() {"):]
        self.assertEqual(sign.count("offline_sha256 "), 2)
        self.assertNotIn("hashlib", sign)

    def test_i20_f9_body_placed_before_sig_and_rolled_back(self):
        """F9: 산출 자리에 본문 먼저 · 서명 나중 — 서명을 못 놓으면 놓은 본문을 거둔다(산출 0 · 임시 0) · 그 뒤 같은 자리로 다시 돌면 통과."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        r = self._sign_env(b, out, self._shim_env_any(ln="*/cysr-release-5.json.minisig"))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("shim: ln 실패 주입", r.stderr)
        self.assertIn("먼저 놓은 본문을 거뒀다", r.stderr)
        self.assertEqual(self._out_files(out), [])
        self.assertEqual(self._media_residue(), [])
        log = os.path.join(self.tmp, "ln-order.txt")
        d = os.path.join(self.tmp, "lnlog")
        os.makedirs(d)
        open(os.path.join(d, "ln"), "w").write('#!/bin/sh\nfor a in "$@"; do last="$a"; done\necho "$last" >> "%s"\nexec /bin/ln "$@"\n' % log)
        os.chmod(os.path.join(d, "ln"), 0o755)
        r = self._sign_env(b, out, dict(self.env, PATH=d + os.pathsep + os.environ.get("PATH", "")))
        self.assertEqual(r.returncode, 0, r.stderr)
        placed = [os.path.basename(l) for l in open(log).read().split()]
        self.assertEqual(placed, ["cysr-release-5.json", "cysr-release-5.json.minisig"])  # 본문 먼저
        self.assertEqual(self._out_files(out), ["cysr-release-5.json", "cysr-release-5.json.minisig"])  # 임시 0
        self.assertTrue(fm.verify(os.path.join(self.tmp, "u.pub"), os.path.join(out, "cysr-release-5.json"),
                                  os.path.join(out, "cysr-release-5.json.minisig")))
        out2 = os.path.join(self.tmp, "out2")
        w, mlog = self._counting_minisign()
        r = self._sign_env(b, out2, dict(self._shim_env_any(cp="*/.cysr-release-5.json.tmp*"), MINISIGN=w))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("본문을 산출 폴더로 옮기지 못했다", r.stderr)
        self.assertFalse(os.path.exists(mlog), "본문 사본이 없는데 minisign 을 불렀다")
        self.assertEqual(self._out_files(out2), [])

    def test_i20_b3_cleanup_failure_is_refusal(self):
        """B3: 성공 갈래의 매체 작업 폴더 정리(rmdir) · 공개키 임시 파일(rm) 실패 = rc 2 · 산출 0(종전 = 무시하고 rc 0)."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        r = self._sign_env(b, out, self._shim_env_any(rmdir="*/.cys-sign-*"))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("shim: rmdir 실패 주입", r.stderr)
        self.assertIn("매체 작업 폴더를 지우지 못했다", r.stderr)
        self.assertEqual(self._out_files(out), [])
        for n in self._media_residue():  # 남은 것은 빈 작업 폴더(공개 정보도 0)
            self.assertEqual(os.listdir(os.path.join(self.mnt, n)), [])
            os.rmdir(os.path.join(self.mnt, n))
        pt = os.path.join(self.tmp, "pubtmp")
        os.makedirs(pt)
        r = self._sign_env(b, out, self._shim_env_any(base=dict(self.env, TMPDIR=pt), rm="*/cys-sign-pub.*"))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("shim: rm 실패 주입", r.stderr)
        self.assertIn("공개키 임시 파일을 지우지 못했다", r.stderr)
        self.assertEqual(self._out_files(out), [])
        self.assertTrue(any(n.startswith("cys-sign-pub.") for n in os.listdir(pt)), os.listdir(pt))  # 전제: 공개키 임시 = TMPDIR 틀 자리
        self.assertEqual(self._media_residue(), [])

    def test_i20_b4_signal_during_minisign_cleans_up(self):
        """B4: minisign(비밀번호 대기 꼴 = 잠든 대역) 중 TERM → rc 2 · 매체 작업 폴더 0 · 공개키·서명 임시 파일 0 · 산출 0."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        pt = os.path.join(self.tmp, "sigtmp")
        os.makedirs(pt)
        started = os.path.join(self.tmp, "mini-started")
        w = os.path.join(self.tmp, "mini-slow.sh")
        open(w, "w").write('#!/bin/sh\n[ "$1" = "-S" ] && { : > "%s"; sleep 2; }\nexec "%s" "%s" "$@"\n' % (started, sys.executable, FAKE))
        os.chmod(w, 0o755)
        env = dict(self.env, MINISIGN=w, TMPDIR=pt)
        p = subprocess.Popen(["bash", os.path.join(self.dev, "sign-release.sh"), "--body", b, "--media", self.mnt,
                              "--key", os.path.join(self.mnt, "u.key"), "--keyring", self.fx.keyring, "--out-dir", out,
                              "--wait-eject", "0"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(200):
            if os.path.exists(started):
                break
            time.sleep(0.05)
        self.assertTrue(os.path.exists(started), "minisign 대역이 시작되지 않았다")
        self.assertNotEqual(self._media_residue(), [])  # 전제: 지금 매체에 작업 폴더가 있다
        p.terminate()  # bash 에만 TERM(자식 = 비밀번호 대기 꼴) — bash 는 자식이 끝난 뒤 trap 을 돈다
        so, se = p.communicate(timeout=30)
        self.assertEqual(p.returncode, 2, se)
        self.assertIn("신호로 멈췄다", se)
        self.assertEqual(self._media_residue(), [])
        self.assertEqual(os.listdir(pt), [])
        self.assertEqual(self._out_files(out), [])
        self.assertNotIn("통과", so)

    # ── 1.1.20 검증 R2·R3·R4·R6⑵(master#c5a0c510 · VERIFY-SIGNTOOL §2 #14·#31·#11 · §4 f4-9) ───────────────
    def _cmd_shim(self, name, body):
        d = tempfile.mkdtemp(prefix="shim3-", dir=self.tmp)
        open(os.path.join(d, name), "w").write("#!/bin/sh\n" + body)
        os.chmod(os.path.join(d, name), 0o755)
        return d

    def test_i20_r2_signal_between_two_ln_leaves_nothing(self):
        """R2: 본문 ln 직후(서명 ln 전) TERM — 종전 = 서명 없는 본문이 최종 이름으로 남음(rc 2) · 이제 rc 2 · 산출 0 · 임시 0."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        d = self._cmd_shim("ln", 'for a in "$@"; do last="$a"; done\n/bin/ln "$@" || exit $?\n'
                                 'case "$last" in */cysr-release-5.json) kill -TERM $PPID ;; esac\nexit 0\n')
        r = self._sign_env(b, out, dict(self.env, PATH=d + os.pathsep + os.environ.get("PATH", "")))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("신호를 받았다 — 놓은 본문·서명을 거뒀다", r.stderr)
        self.assertEqual(self._out_files(out), [])
        self.assertEqual(self._media_residue(), [])

    def test_i20_r3_rollback_failure_is_reported_truthfully(self):
        """R3: 서명 ln 실패 + 본문 rm 실패 — 종전 = 「거뒀다」 거짓 문구 · 이제 「남았다」 + 그 경로 · rc 2."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        r = self._sign_env(b, out, self._shim_env_any(ln="*/cysr-release-5.json.minisig", rm="*/out/cysr-release-5.json"))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertNotIn("먼저 놓은 본문을 거뒀다", r.stderr)
        self.assertIn("지우지 못해 남았다(서명 없음 · 손으로 지울 것): " + os.path.join(out, "cysr-release-5.json"), r.stderr)

    def test_i20_r4_exit_cleanup_failure_keeps_rc2(self):
        """R4: 임시 rm 실패(그리고 EXIT 정리도 실패) — 종전 = set -e 로 rc 1(계약 0|2 이탈) · 이제 rc 2 · 산출은 거둠."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        r = self._sign_env(b, out, self._shim_env_any(rm="*/.cysr-release-5.json.tmp*"))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("shim: rm 실패 주입", r.stderr)
        self.assertNotIn("cysr-release-5.json", [n for n in self._out_files(out) if not n.startswith(".")])
        self.assertNotIn("cysr-release-5.json.minisig", self._out_files(out))

    def test_i20_r4_revocations_exit_cleanup_failure_keeps_rc2(self):
        """검증 R4(폐기문 길 · 변이 r4-2): 폐기문 임시 rm 실패(EXIT 정리도 실패) = rc 2(계약 0|2) · 산출 0."""
        doc = os.path.join(self.tmp, "rev.json")
        py("make-revocations.py", "--key-id", self.fx.kid("r"), "--keyring", self.fx.keyring, "--first", "--out", doc)
        out = os.path.join(self.tmp, "rout")
        r = run(["bash", os.path.join(self.dev, "sign-revocations.sh"), "--doc", doc, "--media", self.mnt,
                 "--key", os.path.join(self.mnt, "r.key"), "--keyring", self.fx.keyring, "--out-dir", out, "--wait-eject", "0"],
                env=self._shim_env_any(rm="*/.revocations.json.tmp*"))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("shim: rm 실패 주입", r.stderr)
        self.assertNotIn("revocations.json.minisig", self._out_files(out))

    def test_i20_r6_doc_hash_failure_refuses_before_minisign(self):
        """R6⑵: offline_sign 의 서명 대상 해시(3번째 sha256)만 실패 — rc 2 · 「sha256 을 계산하지 못했다」 · minisign 0(비밀번호를 묻지 않음) · 매체 0."""
        b = self.unsigned_body()
        out = os.path.join(self.tmp, "out")
        real = shutil.which("python3")
        cnt = os.path.join(self.tmp, "hash-count")
        d = self._cmd_shim("python3", 'case "$*" in *hashlib*) n=$(($(cat "%s" 2>/dev/null || echo 0) + 1)); echo $n > "%s";'
                                      ' [ "$n" = 3 ] && exit 1 ;; esac\nexec "%s" "$@"\n' % (cnt, cnt, real))
        w, mlog = self._counting_minisign()
        r = self._sign_env(b, out, dict(self.env, PATH=d + os.pathsep + os.environ.get("PATH", ""), MINISIGN=w))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(open(cnt).read().strip(), "3")  # 전제: 앞 두 해시(원본·산출 사본)는 지나고 셋째(서명 대상)에서 멈춤
        self.assertIn("sha256 을 계산하지 못했다", r.stderr)
        self.assertFalse(os.path.exists(mlog), "서명 대상 해시가 없는데 minisign 을 불렀다")
        self.assertEqual(self._media_residue(), [])
        self.assertEqual(self._out_files(out), [])

    # ── codex 1R #3: 시험 손잡이는 개발 모드 전용 · 개발 모드는 실 키 거부 · 키 생성도 매체 안 ─────────────
    def real_env(self, **extra):
        e = {k: v for k, v in os.environ.items() if k not in ("CYS_SIGN_DEV", "CYS_TEST_NOW", "MINISIGN",
                                                              "CYS_SIGN_MEDIA_PREFIX")}
        e.update(extra)
        return e

    def test_real_scripts_have_no_env_handles(self):
        """3판(2R #3): 실 의식 스크립트·lib 에는 손잡이 env 가 **코드로** 없다(주석 밖 0) — 대역은 시험 사본 트리에서만."""
        for n in ("lib/offline-sign.sh", "sign-release.sh", "sign-revocations.sh", "gen-offline-key.sh"):
            code = "\n".join(l for l in open(os.path.join(UPD, n), encoding="utf-8").read().splitlines()
                             if not l.lstrip().startswith("#"))
            for h in ("MINISIGN", "CYS_SIGN_MEDIA_PREFIX", "offline-sign-dev"):
                self.assertNotIn(h, code, (n, h))
            for l in code.splitlines():  # 4판: 시험 시각 손잡이 이름은 「보이면 거부」 줄에만
                if "CYS_SIGN_DEV" in l or "CYS_TEST_NOW" in l:
                    self.assertTrue("+x}" in l or "거부" in l, (n, l))

    def test_mut_real_script_ignores_handles(self):
        """실 스크립트에 손잡이를 줘도 무시된다 — 매체 부모 = /Volumes 고정이라 가짜 매체(임시 폴더) = 거부 · 산출물 0."""
        b = self.unsigned_body()
        r = run(["bash", os.path.join(UPD, "sign-release.sh"), "--body", b, "--media", self.mnt,
                 "--key", os.path.join(self.mnt, "u.key"), "--keyring", self.fx.keyring,
                 "--out-dir", os.path.join(self.tmp, "out")],
                env=self.real_env(MINISIGN=self.mini, CYS_SIGN_MEDIA_PREFIX=self.tmp + "/"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("/Volumes", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "out", "cysr-release-5.json.minisig")))

    def test_mut_wait0_real_script(self):
        b = self.unsigned_body()
        r = run(["bash", os.path.join(UPD, "sign-release.sh"), "--body", b, "--media", self.mnt,
                 "--key", os.path.join(self.mnt, "u.key"), "--keyring", self.fx.keyring,
                 "--out-dir", os.path.join(self.tmp, "out"), "--wait-eject", "0"], env=self.real_env())
        self.assertEqual(r.returncode, 2)
        self.assertIn("실 의식에서 쓸 수 없다", r.stderr)

    def test_mut_real_script_refuses_test_time_env(self):
        """4판(3R MINOR-2): 실 의식 셸 진입에 CYS_SIGN_DEV·CYS_TEST_NOW 가 보이면 거부(rc 2 · 무시가 아니라)."""
        b = self.unsigned_body()
        for k, v in (("CYS_SIGN_DEV", "1"), ("CYS_TEST_NOW", "1790000000"), ("CYS_SIGN_DEV", "")):
            r = run(["bash", os.path.join(UPD, "sign-release.sh"), "--body", b, "--media", self.mnt,
                     "--key", os.path.join(self.mnt, "u.key"), "--keyring", self.fx.keyring,
                     "--out-dir", os.path.join(self.tmp, "out")], env=self.real_env(**{k: v}))
            self.assertEqual(r.returncode, 2, k)
            self.assertIn("시험 시각 손잡이", r.stderr)
        r = self.gen("--media", self.mnt, "--name", "u", env=self.real_env(CYS_TEST_NOW="1"), real=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("시험 시각 손잡이", r.stderr)

    def test_mut_dev_lib_refuses_real_media_parent(self):
        """시험 대역도 매체 부모가 임시 폴더 밖(/Volumes)이면 거부 — 대역으로 실 매체를 여는 길 0."""
        b = self.unsigned_body()
        r = run(
            ["bash", os.path.join(self.dev, "sign-release.sh"), "--body", b, "--media", self.mnt,
             "--key", os.path.join(self.mnt, "u.key"), "--keyring", self.fx.keyring, "--out-dir",
             os.path.join(self.tmp, "out"), "--wait-eject", "0"], env=dict(self.env, CYS_SIGN_MEDIA_PREFIX="/Volumes"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("임시 폴더 밖", r.stderr)

    def test_mut_dev_mode_real_key_id(self):
        real = json.load(open(os.path.join(ROOT, "cysjavis-pack", "trusted-keys.json")))["keys"][0]["key_id"]
        b = self.unsigned_body()
        d = json.load(open(b))
        d["key_id"] = real
        json.dump(d, open(b, "w"))
        r = self.sign(b, os.path.join(self.mnt, "u.key"), os.path.join(self.tmp, "out"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("저장소 실 키링의 key id", r.stderr)

    def second_media(self):
        m2 = os.path.join(self.tmp, "mnt2")
        os.makedirs(m2)
        dmg = os.path.join(self.tmp, "m2.dmg")
        for args, partial in ((["create", "-size", "4m", "-fs", "HFS+", "-volname", "U3FAKE2", "-quiet", dmg], dmg),
                              (["attach", dmg, "-mountpoint", m2, "-nobrowse", "-quiet"], None)):
            reasons = hdiutil_retry(args, partial=partial)
            if reasons:
                self.fail("둘째 가짜 매체 준비 실패(hdiutil %s · 2회): %s" % (args[0], " | ".join(reasons)))
        self.addCleanup(subprocess.call, ["hdiutil", "detach", m2, "-quiet"])
        return m2

    def gen(self, *args, env=None, real=False):
        return run(["bash", os.path.join(UPD if real else self.dev, "gen-offline-key.sh")] + list(args), env=env or self.env,
                   cwd=self.tmp)

    def test_gen_key_r_two_media(self):
        m2 = self.second_media()
        os.remove(os.path.join(self.mnt, "r.key"))
        pub = os.path.join(self.tmp, "new-r.pub")
        r = self.gen("--media", self.mnt, "--name", "r", "--copy-to", m2, "--pub-out", pub)
        self.assertEqual(r.returncode, 0, r.stderr)
        k1, k2 = os.path.join(self.mnt, "r.key"), os.path.join(m2, "r.key")
        self.assertEqual(open(k1, "rb").read(), open(k2, "rb").read())
        kid = uc.pubkey_key_id(open(pub).read())
        self.assertIn(kid, r.stdout)
        secret = open(k1).read().splitlines()[1]
        for dp, _, fns in os.walk(self.tmp):
            if dp.startswith(self.mnt) or dp.startswith(m2):
                continue
            for n in fns:
                if n.endswith(".dmg"):
                    continue
                self.assertNotIn(secret, open(os.path.join(dp, n), errors="ignore").read(),
                                 "개인키가 매체 밖 파일에 생김: %s" % os.path.join(dp, n))
        # 새 키로 R 의식이 실제로 돈다(공개키 = 꺼낸 .pub)
        msg = os.path.join(self.tmp, "m.txt")
        open(msg, "w").write("x")
        fm.sign(k2, msg, msg + ".minisig", "t")
        self.assertTrue(fm.verify(pub, msg, msg + ".minisig"))

    def test_mut_gen_existing_key(self):
        r = self.gen("--media", self.mnt, "--name", "u", "--pub-out", os.path.join(self.tmp, "x.pub"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("이미 있다", r.stderr)

    def test_mut_gen_copy_to_same_media(self):
        os.remove(os.path.join(self.mnt, "r.key"))
        os.makedirs(os.path.join(self.mnt, "sub"))
        pub = os.path.join(self.tmp, "new-r.pub")
        r = self.gen("--media", self.mnt, "--name", "r", "--copy-to", os.path.join(self.mnt, "sub"), "--pub-out", pub)
        self.assertEqual(r.returncode, 2)
        self.assertIn("마운트 지점이 아니다", r.stderr)
        r = self.gen("--media", self.mnt, "--name", "r", "--copy-to", self.mnt, "--pub-out", pub)
        self.assertEqual(r.returncode, 2)
        self.assertIn("같은 장치", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.mnt, "r.key")))

    def test_mut_gen_outside_media_and_handles(self):
        notmnt = os.path.join(self.tmp, "notmnt")
        os.makedirs(notmnt)
        r = self.gen("--media", notmnt, "--name", "u")
        self.assertEqual(r.returncode, 2)
        self.assertIn("마운트 지점이 아니다", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(notmnt, "u.key")))
        r = self.gen("--media", self.mnt, "--name", "u", env=self.real_env(MINISIGN=self.mini), real=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("/Volumes", r.stderr)  # 실 스크립트 = 손잡이 무시 · 가짜 매체 거부
        r = self.gen("--media", self.mnt, "--name", "u", "--copy-to", self.mnt)
        self.assertEqual(r.returncode, 2)
        self.assertIn("R(둘째 벌) 전용", r.stderr)


@unittest.skipUnless(VERIFY_BIN, "U1 미머지 — CYS_UPDATE_VERIFY_BIN(디버그 cys) 없음: update-verify 왕복 미실행")
class TestUpdateVerifyRoundTrip(Base):
    def setUp(self):
        super().setUp()
        self.b = self.fx.body()
        self.rev = os.path.join(self.tmp, "rev.json")
        py("make-revocations.py", "--key-id", self.fx.kid("r"), "--keyring", self.fx.keyring, "--first", "--out", self.rev)
        fm.sign(self.fx.key("r"), self.rev, self.rev + ".minisig", "t")
        self.state = os.path.join(self.tmp, "st")
        os.makedirs(self.state)

    def envelope(self, body, name="env.json"):
        out = os.path.join(self.tmp, name)
        r = py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", body,
               "--release-sig", body + ".minisig", "--key-id", self.fx.kid("f"), "--keyring", self.fx.keyring,
               "--first", "--rollout-pct", "100", "--halt", "false", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        fm.sign(self.fx.key("f"), out, out + ".minisig", "t")
        return out

    def hand_envelope(self, body):
        """생산자 검사를 거치지 않은 봉투(검증기 자체를 재기 위함)."""
        env = {"kind": "component-update-feed", "component": "cysr", "channel": "stable", "feed_rev": 1,
               "key_id": self.fx.kid("f"), "signed_at": NOW, "expires_at": NOW + 86400, "rollout_pct": 100, "halt": False,
               "release": base64.b64encode(open(body, "rb").read()).decode(),
               "release_sig": base64.b64encode(open(body + ".minisig", "rb").read()).decode()}
        out = os.path.join(self.tmp, "hand.json")
        open(out, "wb").write(uc.dump_json_bytes(env))
        fm.sign(self.fx.key("f"), out, out + ".minisig", "t")
        return out

    def gate(self, env, expect="apply", now="1790000100", installed=None, cys=None):
        e = dict(os.environ, CYS_UPDATE_TEST_KEYRING=self.fx.keyring, CYS_UPDATE_STATE_DIR=self.state,
                 CYS_UPDATE_NOW=now)
        extra = ["--installed-release-seq", installed] if installed else []
        return py("release-gate.py", "verify", "--cys", cys or VERIFY_BIN, "--component", "cysr", "--channel", "stable",
                  "--envelope", env, "--sig", env + ".minisig", "--revocations", self.rev,
                  "--revocations-sig", self.rev + ".minisig", "--expect", expect, *extra, env=e)

    def wrapped_cys(self, edit):
        """진짜 U1 cys 를 부르고 JSON 출력만 `edit`(파이썬 식 · 변수 j)로 고치는 대역 — 게이트의 대조 자체를 재기 위함."""
        w = os.path.join(self.tmp, "cys-wrap.py")
        open(w, "w").write("""#!%s
import json, subprocess, sys
p = subprocess.run([%r] + sys.argv[1:], capture_output=True, text=True)
j = json.loads(p.stdout)
%s
sys.stdout.write(json.dumps(j)); sys.exit(p.returncode)
""" % (sys.executable, VERIFY_BIN, edit))
        os.chmod(w, 0o755)
        return w

    def test_apply_both_rows(self):
        r = self.gate(self.envelope(self.b))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count("출발 seq 1,2,3,4,5 전부 허용 판정(열거)"), 2)

    def test_mut_payload_manifest_dropped_or_altered(self):
        """codex 2R #10: 반환 행 전체 대조에 payload_manifest 포함 — 칸 누락·한 항목 변조 = 적색."""
        e = self.envelope(self.b)
        drop = ("for r in j.get('results', []):\n"
                "    a = r['outcome'].get('asset') or {}\n"
                "    a.pop('payload_manifest', None)")
        r = self.gate(e, cys=self.wrapped_cys(drop))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("payload_manifest", r.stderr)
        alter = ("for r in j.get('results', []):\n"
                 "    pm = (r['outcome'].get('asset') or {}).get('payload_manifest')\n"
                 "    if pm: pm[0]['sha256'] = '0' * 64")
        r = self.gate(e, cys=self.wrapped_cys(alter))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("payload_manifest", r.stderr)

    def test_mut_enumerate_range_drift(self):
        """codex 2R #11: 열거 범위가 max(min_from,1)..=seq 와 다르면(하한 빠짐 · 후보 빠짐) 거부."""
        e = self.envelope(self.b)
        for edit in ("j['results'] = j['results'][1:]", "j['results'] = j['results'][:-1]"):
            r = self.gate(e, cys=self.wrapped_cys(edit))
            self.assertEqual(r.returncode, 1, edit)
            self.assertIn("열거 범위", r.stderr)
        r = self.gate(e, cys=self.wrapped_cys("j['results'][-1]['outcome']['verdict'] = 'apply'"))
        self.assertEqual(r.returncode, 1)  # 후보 자신 = uptodate 강제
        self.assertIn("installed 5", r.stderr)

    def test_mut_tampered_body(self):
        raw = bytearray(open(self.b, "rb").read())
        raw[raw.index(b"additive")] = ord("A")
        open(self.b, "wb").write(bytes(raw))
        r = py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", self.b,
               "--release-sig", self.b + ".minisig", "--key-id", self.fx.kid("f"), "--keyring", self.fx.keyring,
               "--first", "--rollout-pct", "100", "--halt", "false", "--out", os.path.join(self.tmp, "x.json"))
        self.assertEqual(r.returncode, 2)  # 생산자가 먼저 막는다(본문 서명 암호 검증)
        r = self.gate(self.hand_envelope(self.b))
        self.assertEqual(r.returncode, 1)  # 검증기도 막는다
        self.assertIn("reject", r.stderr)

    def test_installed_range_default_and_stamp(self):
        e = self.envelope(self.b)
        env = dict(os.environ, CYS_UPDATE_TEST_KEYRING=self.fx.keyring, CYS_UPDATE_STATE_DIR=self.state,
                   CYS_UPDATE_NOW=str(NOW + 100))
        r = py("release-gate.py", "verify", "--cys", VERIFY_BIN, "--component", "cysr", "--channel", "stable",
               "--envelope", e, "--sig", e + ".minisig", "--revocations", self.rev, "--revocations-sig", self.rev + ".minisig",
               "--stamp", env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("1,2,3,4,5", r.stdout)  # min_from 1 .. seq-1 = apply · seq 5 = uptodate
        self.assertEqual(json.load(open(uc.stamp_path(e)))["by"], uc.STAMP_BY_U1)

    def test_mut_expired_envelope(self):
        r = self.gate(self.envelope(self.b), now=str(NOW + 15 * 86400))
        self.assertEqual(r.returncode, 1)

    def test_first_release_seq1_uptodate_only(self):
        """4판(3R MAJOR-2 · master 결정 ①): 첫 판(seq 1 · 허용 출발 seq 없음) = 「후보 uptodate 1행」 으로 통과.
        R0(4d0aab95): U1 cli 의 같은 규칙(SEQ1 · cli.rs first_release)이 병합 트리에 있다 — 대역 없이 실제 U1 으로 잰다."""
        d = os.path.join(self.tmp, "s1")
        os.makedirs(d)
        fx1 = Fixture(d, seq=1)
        fx1.keys, fx1.keyring = self.fx.keys, self.fx.keyring
        for k in ("u", "f"):
            shutil.copy(self.fx.key(k), fx1.key(k))
        e = self.envelope(fx1.body(**{"--min-from-release-seq": "0"}), "s1.json")  # 생성기 규칙 0 ≤ min_from < seq
        r = self.gate(e)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("출발 seq 1 전부 허용 판정(열거)", r.stdout)
        r = self.gate(e, cys=self.wrapped_cys("j['results'][0]['outcome']['verdict'] = 'apply'"))
        self.assertEqual(r.returncode, 1)  # 후보 자신은 여전히 uptodate 여야 한다

    def test_u1_enum_row_keys_source_pin(self):
        """4판(3R MAJOR-1): 게이트가 읽는 열거 행 키 = U1 feed::render_enum_row 가 쓰는 키(소스 대조 · 재발 드리프트 벨트).
        R0(4d0aab95): U1 이 병합 트리에 있다 — 가지 ref 가 아니라 이 트리의 src/update/feed.rs 를 읽는다(건너뜀 0)."""
        feed = open(os.path.join(ROOT, "src", "update", "feed.rs"), encoding="utf-8").read()
        i = feed.find("fn render_enum_row(")
        self.assertGreater(i, 0, "U1 render_enum_row 를 찾지 못함")
        fn = feed[i:feed.find("\n}\n", i)]
        self.assertIn('\\"installed_release_seq\\":', fn)
        self.assertIn('\\"outcome\\":', fn)
        src = open(os.path.join(UPD, "u1verify.py"), encoding="utf-8").read()
        self.assertIn('r.get("outcome")', src)
        self.assertIn('r.get("installed_release_seq")', src)

    def test_mut_cysr_explicit_installed_refused(self):
        """U1 2판 B4: cysr 는 명시 설치 seq 를 받지 않는다 — 게이트가 U1 을 부르기 전에 거부(가짜 설치 seq 경로 봉쇄)."""
        r = self.gate(self.envelope(self.b), expect="uptodate", installed="5")
        self.assertEqual(r.returncode, 1)
        self.assertIn("명시 설치 seq", r.stderr)

    def test_mut_feed_key_used_for_body(self):
        b = json.load(open(self.b))
        b["key_id"] = self.fx.kid("f")
        open(self.b, "wb").write(uc.dump_json_bytes(b))
        fm.sign(self.fx.key("f"), self.b, self.b + ".minisig", "t")
        r = self.gate(self.hand_envelope(self.b))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("reject", r.stderr)

    def test_refresh_chain_inherits_only_verified_current(self):
        """refresh-feed.yml 순서(3판 · codex 2R #6): make-envelope --prev-envelope --cys --revocations 가 현재 봉투를 U1 으로 직접
        다시 검증(만료만 허용) → 새 봉투 verify(출발 seq 전수). 위조 현재 봉투 = U1 거부 = 상속 0(위조 증표가 있어도)."""
        e1 = self.envelope(self.b, "cur.json")
        later = NOW + 15 * 86400  # 현재 봉투는 만료(주간 재서명이 늦은 경우)
        env = dict(os.environ, CYS_UPDATE_TEST_KEYRING=self.fx.keyring, CYS_UPDATE_STATE_DIR=self.state,
                   CYS_UPDATE_NOW=str(later), CYS_TEST_NOW=str(later))

        def inherit(prev, out, body=None):
            body = body or self.b
            return py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", body,
                      "--release-sig", body + ".minisig", "--key-id", self.fx.kid("f"), "--keyring", self.fx.keyring,
                      "--prev-envelope", prev, "--cys", VERIFY_BIN, "--revocations", self.rev, "--out", out, env=env)
        e2 = os.path.join(self.tmp, "env2.json")
        r = inherit(e1, e2)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.load(open(e2))["feed_rev"], 2)
        fm.sign(self.fx.key("f"), e2, e2 + ".minisig", "t")
        r = py("release-gate.py", "verify", "--cys", VERIFY_BIN, "--component", "cysr", "--channel", "stable",
               "--envelope", e2, "--sig", e2 + ".minisig", "--revocations", self.rev,
               "--revocations-sig", self.rev + ".minisig", "--expect", "apply,halt,not_in_rollout", env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("1,2,3,4,5", r.stdout)
        forged = os.path.join(self.tmp, "forged.json")
        d = json.load(open(e1))
        d.update(feed_rev=1000, halt=True, rollout_pct=0)
        open(forged, "wb").write(uc.dump_json_bytes(d))
        fm.sign(self.fx.key("u"), forged, forged + ".minisig", "t")
        u1_stamp(forged)  # 위조 증표 — 3판에서는 아무 효력 없다
        r = inherit(forged, os.path.join(self.tmp, "env3.json"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("U1 재검증 거부", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "env3.json")))

    def test_mut_same_seq_different_body_or_older(self):
        """codex 2R #19: 같은 release_seq 의 다른 U 서명 본문(notes_ko 다름) = 재서명 거부 · 낮은 seq = 후퇴 거부."""
        e1 = self.envelope(self.b, "cur.json")
        env = dict(os.environ, CYS_UPDATE_TEST_KEYRING=self.fx.keyring, CYS_UPDATE_STATE_DIR=self.state,
                   CYS_UPDATE_NOW=str(NOW + 100), CYS_TEST_NOW=str(NOW + 100))
        other = self.fx.body(name="body-other.json", **{"--notes-ko": "다른 문구예요"})
        d = os.path.join(self.tmp, "o")
        os.makedirs(d)
        fx4 = Fixture(d, seq=4)
        fx4.keys = self.fx.keys
        shutil.copy(self.fx.key("u"), fx4.key("u"))
        b4 = fx4.body()
        for body, why in ((other, "재서명 거부"), (b4, "후퇴")):
            r = py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", body,
                   "--release-sig", body + ".minisig", "--key-id", self.fx.kid("f"), "--keyring", self.fx.keyring,
                   "--prev-envelope", e1, "--cys", VERIFY_BIN, "--revocations", self.rev,
                   "--out", os.path.join(self.tmp, "n.json"), env=env)
            self.assertEqual(r.returncode, 2, why)
            self.assertIn(why, r.stderr)

    def test_publish_envelope_reverifies_with_u1(self):
        """codex 2R #4·#15·#19: 봉투 게시 = U1 직접 재검증(--cys 필수) + 실은 본문 = 보관소 객체 + feed_rev 단조."""
        st = os.path.join(self.tmp, "store")
        env = dict(os.environ, CYS_UPDATE_TEST_KEYRING=self.fx.keyring, CYS_UPDATE_STATE_DIR=self.state,
                   CYS_UPDATE_NOW=str(NOW + 100), CYS_TEST_NOW=str(NOW + 100))
        e1 = self.envelope(self.b, "e1.json")
        self.assertEqual(publish(self.fx, "revocations", self.rev, st, "--first", env=env).returncode, 0)
        r = publish(self.fx, "envelope", e1, st, "--cys", VERIFY_BIN, env=env)
        self.assertEqual(r.returncode, 3)  # 보관소에 그 seq 없음
        self.assertIn("보관소", r.stderr)
        self.assertEqual(publish(self.fx, "archive", self.b, st, "--first", env=env).returncode, 0)
        r = publish(self.fx, "envelope", e1, st, env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("--cys", r.stderr)
        r = publish(self.fx, "envelope", e1, st, "--cys", VERIFY_BIN, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("전부 허용 판정(열거)", r.stdout)
        forged = os.path.join(self.tmp, "forged.json")
        d = json.load(open(e1))
        d.update(feed_rev=2, halt=True)
        open(forged, "wb").write(uc.dump_json_bytes(d))
        fm.sign(self.fx.key("u"), forged, forged + ".minisig", "t")
        u1_stamp(forged)
        r = publish(self.fx, "envelope", forged, st, "--cys", VERIFY_BIN, env=env)
        self.assertEqual(r.returncode, 2)  # 위조 증표 무력 · 키링 feed 검증·U1 이 막는다
        # F 로 정상 서명됐고 파이썬 검사(서명·feed_rev·signed_at)는 통과하지만 U1 이 거부하는 봉투(유효창 이미 지남) — U1 재검증만 막는다.
        late = os.path.join(self.tmp, "late.json")
        d = json.load(open(e1))
        d.update(feed_rev=3, signed_at=d["signed_at"] + 1, expires_at=d["signed_at"] + 2)
        open(late, "wb").write(uc.dump_json_bytes(d))
        fm.sign(self.fx.key("f"), late, late + ".minisig", "t")
        r = publish(self.fx, "envelope", late, st, "--cys", VERIFY_BIN, env=env)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("U1 재검증 거부", r.stderr)


# ★CI 전용(TICKET=cysr-test-gatekeeper-crash-1118): collect-inputs.sh 가 갓 서명한 번들을 임시 폴더에 풀어 그 안의 cys 를 실행한 뒤
# 지운다(새 Mach-O 실행 → 삭제 = 사람 맥 syspolicyd 충돌 후보 · 수집기는 제품 스크립트라 여기서 못 바꾼다) → 사람 맥 기본 실행에서는 건너뛴다.
@unittest.skipUnless(sys.platform == "darwin" and shutil.which("codesign") and VERIFY_BIN and os.environ.get("CI"),
                     "맥 재료 수집기 = CI 전용 · codesign + build-info 가진 cys(CYS_UPDATE_VERIFY_BIN) 필요")
class TestCollectMac(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="u3c-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def bundle(self, signed):
        self.n = getattr(self, "n", 0) + 1
        app = os.path.join(self.tmp, "b%d-%d" % (signed, self.n), "cysr.app")
        os.makedirs(os.path.join(app, "Contents", "MacOS"))
        shutil.copy(VERIFY_BIN, os.path.join(app, "Contents", "MacOS", "cys"))
        open(os.path.join(app, "Contents", "Info.plist"), "w").write(
            '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict><key>CFBundleIdentifier</key>'
            '<string>test.u3.fake</string><key>CFBundleExecutable</key><string>cys</string></dict></plist>')
        if signed:
            subprocess.check_call(["codesign", "-s", "-", "--force", app], stderr=subprocess.DEVNULL)
        z = os.path.join(self.tmp, "b%d-%d.zip" % (signed, self.n))
        subprocess.check_call(["ditto", "-c", "-k", "--keepParent", app, z])
        return z

    def test_signed_and_unsigned(self):
        out = os.path.join(self.tmp, "out")
        env = dict(os.environ, CYS_UPDATE_STATE_DIR=os.path.join(self.tmp, "st"), CYS_COLLECT_DR_PIN="none")
        r = run(["bash", os.path.join(UPD, "collect-inputs.sh"), "mac", self.bundle(1), "macos-arm64", out], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(open(os.path.join(out, "cdhash-macos-arm64.txt")).read().strip(), r"^[0-9a-f]{40}$")
        self.assertIn("build_id", json.load(open(os.path.join(out, "build-info-macos-arm64.json"))))
        r = run(["bash", os.path.join(UPD, "collect-inputs.sh"), "mac", self.bundle(0), "macos-arm64",
                 os.path.join(self.tmp, "out2")], env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("봉인되지 않은", r.stderr)  # 링커 서명 Mach-O 만으로도 CDHash 는 읽힌다 — 봉인 검사가 막는다
        env.pop("CYS_COLLECT_DR_PIN")
        r = run(["bash", os.path.join(UPD, "collect-inputs.sh"), "mac", self.bundle(1), "macos-arm64",
                 os.path.join(self.tmp, "out3")], env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("DR 핀 불일치", r.stderr)  # 애드혹 서명 ≠ cys-local leaf


# ★1.1.20 #57(TICKET=cysr-1120-integ2 · master#ddf562c2 A′ · master#58de9790 A): x64 맥 재료 = 실행 0 · 정적 대조.
#   대역 x64 = 시스템 /bin/zsh 의 x86_64 조각을 떼어 __text 를 대역 바이트(빌드 표지·팩 내용·키링)로 덮고 ad-hoc 서명한 번들
#   (strict 검증 통과 · ★이 시험은 그 바이너리를 **실행하지 않는다** — 수집기의 x64 갈래에 실행 줄이 없음은 소스 핀이 잰다).
def _zsh_has_x86_64():
    try:
        return sys.platform == "darwin" and "x86_64" in subprocess.run(["lipo", "-archs", "/bin/zsh"], capture_output=True, text=True).stdout.split()
    except OSError:
        return False


@unittest.skipUnless(_zsh_has_x86_64() and shutil.which("codesign"), "맥 전용(lipo·codesign · /bin/zsh x86_64 조각)")
class TestCollectMacX64Static(unittest.TestCase):
    PACK = {"a.txt": b"alpha\n", "sub/b.md": b"# b\n\xea\xb0\x80\n", "tests/skip.py": b"never\n", ".hidden": b"never\n"}
    KEYS = {"keys": [{"key_id": "A" * 16, "pubkey": "p1", "not_after": "2030-01-01T00:00:00Z"},
                     {"key_id": "B" * 16, "pubkey": "p2", "purpose": "release", "not_after": "2030-01-01T00:00:00Z"},
                     {"key_id": "C" * 16, "pubkey": "p3", "purpose": "root", "not_after": "2030-01-01T00:00:00Z"}]}

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="u3x-")
        g = self.g = os.path.join(self.tmp, "g")
        for rel, data in self.PACK.items():
            os.makedirs(os.path.dirname(os.path.join(g, "cysjavis-pack", rel)), exist_ok=True)
            open(os.path.join(g, "cysjavis-pack", rel), "wb").write(data)
        self.keyring = (json.dumps(self.KEYS, indent=2) + "\n").encode()
        open(os.path.join(g, "cysjavis-pack", "trusted-keys.json"), "wb").write(self.keyring)
        open(os.path.join(g, "Cargo.toml"), "w").write('[package]\nname = "x"\nversion = "1.2.3"\n\n[dependencies]\nversion = "9"\n')
        os.makedirs(os.path.join(g, "scripts", "update"))
        for n in ("collect-inputs.sh", "collect_x64_static.py"):
            os.symlink(os.path.join(UPD, n), os.path.join(g, "scripts", "update", n))
        genv = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_AUTHOR_NAME="t",
                    GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        for a in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "t"]):
            self.assertEqual(run(["git", "-C", g, *a], env=genv).returncode, 0, a)
        self.bid = run(["git", "-C", g, "rev-parse", "--short=12", "HEAD"]).stdout.strip() + ".20261126T0000Z"
        # 시험 쪽 독립 계산(build.rs 규칙: 점·tests 제외 · 바이트 정렬 · rel\0content\0)
        items = sorted(((r, d) for r, d in list(self.PACK.items()) + [("trusted-keys.json", self.keyring)]
                        if not any(c.startswith(".") or c == "tests" for c in r.split("/"))), key=lambda x: x[0].encode())
        self.items = items
        h = hashlib.sha256()
        for r, d in items:
            h.update(r.encode() + b"\0" + d + b"\0")
        self.digest = h.hexdigest()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def bi(self, **over):
        b = {"version": "1.2.3", "build_id": self.bid, "release_seq": 5, "target": "macos-arm64", "features": [],
             "bundled_pack": {"version": "1.2.3", "digest": self.digest},
             "keyring_ids": ["release:" + "B" * 16, "root:" + "C" * 16], "trash_delete_supported": True}
        b.update(over)
        p = os.path.join(self.tmp, "bi-%d.json" % len(os.listdir(self.tmp)))
        json.dump(b, open(p, "w"))
        return p, b

    def payload(self, seq=5, bid=None, marks=1, flip=None, ver="1.2.3", prefix=b"", mark=None, pack=None):
        if mark is None:
            mark = b"cysr-buildmark:seq=%d;build_id=%s;version=%s;pack=%s;" % (
                seq, (bid or self.bid).encode(), ver.encode(), (pack or self.digest).encode())
        body = b"".join(d if r != flip else d[:-1] + bytes([d[-1] ^ 1]) for r, d in self.items)
        return b"\0".join(([prefix] if prefix else []) + [mark] * marks + [body, self.keyring])

    def bundle(self, payload, arch="x86_64"):
        n = len(os.listdir(self.tmp))
        app = os.path.join(self.tmp, "b%d" % n, "cysr.app")
        os.makedirs(os.path.join(app, "Contents", "MacOS"))
        exe = os.path.join(app, "Contents", "MacOS", "cys")
        slices = []
        for a in (["x86_64", "arm64e"] if arch == "fat" else [arch]):
            t = os.path.join(self.tmp, "s%d-%s" % (n, a))
            self.assertEqual(run(["lipo", "-thin", a, "/bin/zsh", "-output", t]).returncode, 0)
            o = run(["otool", "-l", t]).stdout
            m = re.search(r"sectname __text\n\s+segname __TEXT\n\s+addr \S+\n\s+size (0x[0-9a-f]+)\n\s+offset (\d+)", o)
            size, off = int(m.group(1), 16), int(m.group(2))
            self.assertLess(len(payload), size)
            b = bytearray(open(t, "rb").read())
            b[off:off + len(payload)] = payload
            open(t, "wb").write(b)
            slices.append(t)
        if arch == "fat":
            self.assertEqual(run(["lipo", "-create", *slices, "-output", exe]).returncode, 0)
        else:
            shutil.copy(slices[0], exe)
        os.chmod(exe, 0o755)
        open(os.path.join(app, "Contents", "Info.plist"), "w").write(
            '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict><key>CFBundleIdentifier</key>'
            '<string>test.u3.fake</string><key>CFBundleExecutable</key><string>cys</string></dict></plist>')
        subprocess.check_call(["codesign", "-s", "-", "--force", app], stderr=subprocess.DEVNULL)
        z = os.path.join(self.tmp, "b%d.zip" % n)
        subprocess.check_call(["ditto", "-c", "-k", "--keepParent", app, z])
        return z

    def collect(self, z, bi_path=None, target="macos-x64"):
        out = os.path.join(self.tmp, "out-%d" % len(os.listdir(self.tmp)))
        args = ["bash", os.path.join(self.g, "scripts", "update", "collect-inputs.sh"), "mac", z, target, out]
        if bi_path:
            args += ["--from-build-info", bi_path]
        r = run(args, env=dict(os.environ, CYS_COLLECT_DR_PIN="none"))
        return r, out

    def refused(self, r, out, words):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(words, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(out, "build-info-macos-x64.json")))

    def test_same_passes_and_writes_x64_row(self):
        p, b = self.bi()
        r, out = self.collect(self.bundle(self.payload()), p)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("정적 대조 통과", r.stdout)
        self.assertEqual(json.load(open(os.path.join(out, "build-info-macos-x64.json"))), dict(b, target="macos-x64"))
        self.assertRegex(open(os.path.join(out, "cdhash-macos-x64.txt")).read().strip(), r"^[0-9a-f]{40}$")

    def test_build_id_differs(self):
        p, _ = self.bi()
        r, out = self.collect(self.bundle(self.payload(bid=self.bid[:-5] + "0001Z")), p)
        self.refused(r, out, "표지 build_id=")

    def test_seq_only_differs(self):
        p, _ = self.bi()
        r, out = self.collect(self.bundle(self.payload(seq=6)), p)
        self.refused(r, out, "표지 seq=6")

    def test_pack_one_byte_differs(self):
        p, _ = self.bi()
        r, out = self.collect(self.bundle(self.payload(flip="sub/b.md")), p)
        self.refused(r, out, "커밋 팩 내용이 없다 1건(첫: sub/b.md)")

    def test_digest_differs_in_arm64_input(self):
        p, _ = self.bi(bundled_pack={"version": "1.2.3", "digest": "0" * 64})
        r, out = self.collect(self.bundle(self.payload()), p)
        self.refused(r, out, "팩 다시 계산 digest")

    def test_old_binary_without_mark(self):
        p, _ = self.bi()
        r, out = self.collect(self.bundle(self.payload(marks=0)), p)
        self.refused(r, out, "표지가 0번")

    def test_mark_twice_is_ambiguous(self):
        p, _ = self.bi()
        r, out = self.collect(self.bundle(self.payload(marks=2)), p)
        self.refused(r, out, "표지가 2번")

    def test_fat_binary_refused(self):
        p, _ = self.bi()
        r, out = self.collect(self.bundle(self.payload(), arch="fat"), p)
        self.refused(r, out, "x86_64 단독이 아니다")

    def test_arm64_disguised_as_x64_refused(self):
        p, _ = self.bi()
        r, out = self.collect(self.bundle(self.payload(), arch="arm64e"), p)
        self.refused(r, out, "x86_64 단독이 아니다: 'arm64e'")

    def test_unreleased_seq0_and_missing_input_refused(self):
        z = self.bundle(self.payload(seq=0))
        p, _ = self.bi(release_seq=0)
        r, out = self.collect(z, p)
        self.refused(r, out, "release_seq 가 1 이상")
        r, out = self.collect(z)
        self.refused(r, out, "--from-build-info")

    # ── 검증 R5: 수집기 칸 4(키링 바이트 · version · features/trash · -dirty)마다 「그 칸만 다른」 입력 ──
    def test_r5_keyring_bytes_differ(self):
        p, _ = self.bi()
        kr = self.keyring.replace(b'"p2"', b'"pX"')
        self.assertNotEqual(kr, self.keyring)
        mark = b"cysr-buildmark:seq=5;build_id=%s;version=1.2.3;pack=%s;" % (self.bid.encode(), self.digest.encode())
        r, out = self.collect(self.bundle(b"\0".join([mark, b"".join(d for _, d in self.items if _ != "trusted-keys.json"), kr])), p)
        # trusted-keys.json 은 팩 안에도 있어(PACK_ALL) 팩 내용 탐색이 같은 바이트를 먼저 요구한다 — 키링 바이트 칸은 그 뒤의 이중 방어(준등가)
        self.refused(r, out, "x64 바이너리에 커밋 팩 내용이 없다 1건(첫: trusted-keys.json)")

    def test_r5_version_differs(self):
        p, _ = self.bi(version="1.2.4", bundled_pack={"version": "1.2.4", "digest": self.digest})
        r, out = self.collect(self.bundle(self.payload()), p)
        self.refused(r, out, "version: 커밋 Cargo.toml 1.2.3")

    def test_r5_features_or_trash_differ(self):
        for over in ({"features": ["x"]}, {"trash_delete_supported": False}):
            p, _ = self.bi(**over)
            r, out = self.collect(self.bundle(self.payload()), p)
            self.refused(r, out, "코드 상수와 다르다")

    def test_r5_dirty_build_id_refused(self):
        dirty = self.bid[:12] + "-dirty" + self.bid[12:]
        p, _ = self.bi(build_id=dirty)
        r, out = self.collect(self.bundle(self.payload(bid=dirty)), p)
        self.refused(r, out, "build_id 형식")

    # ── 1.1.21 N(agy 서명 도구 검토 med1·med2 · TICKET=cysr-1121-integ) ──
    def test_n_med1_mark_version_differs(self):
        """표지 version 이 커밋 Cargo.toml·arm64 값과 다르면 거부(seq·build_id 는 같음 = 남은 CYSR_BUILD_ID + 판 바꾼 트리 꼴)."""
        p, _ = self.bi()
        r, out = self.collect(self.bundle(self.payload(ver="1.2.4")), p)
        self.refused(r, out, "x64 표지 1.2.4")

    def test_n_med1_old_mark_without_version_refused(self):
        """1.1.20 꼴 표지(version·pack 칸 없음) · version 만 있는 꼴 = 닫힌 꼴 아님 → 거부."""
        p, _ = self.bi()
        for old in (b"cysr-buildmark:seq=5;build_id=%s;" % self.bid.encode(),
                    b"cysr-buildmark:seq=5;build_id=%s;version=1.2.3;" % self.bid.encode()):
            r, out = self.collect(self.bundle(self.payload(mark=old)), p)
            self.refused(r, out, "닫힌 꼴(seq=…;build_id=…;version=…;pack=…;)")

    def test_n_med2_mark_pack_digest_binds(self):
        """표지 pack digest 가 커밋 재계산값과 다르면 거부 — 바이트 사슬이 (가까운 가짜 닻·뒤쪽 사본으로) 이어져도 결속은 digest 다
        (codex N 1R major 반례 꼴: 첫 항목을 깨고 그 원문을 바로 앞에 둠)."""
        p, _ = self.bi()
        r, out = self.collect(self.bundle(self.payload(pack="0" * 64)), p)
        self.refused(r, out, "x64 표지 pack=" + "0" * 64)
        first, data = self.items[0]
        r, out = self.collect(self.bundle(self.payload(prefix=data, flip=first, pack="1" * 64)), p)
        self.refused(r, out, "x64 표지 pack=")

    def test_n_med2_no_offset0_rescan(self):
        """뒤 항목이 깨졌는데 그 원래 바이트가 표지 앞(오프셋 0 쪽)에 있으면 — 옛 길(맨 앞부터 다시 찾기)은 통과 · 지금 = 거부."""
        p, _ = self.bi()
        last, data = "sub/b.md", self.PACK["sub/b.md"]  # 뒤쪽(키링 앞) 항목 — 키링은 본문 뒤에 따로 있어 맨 끝 항목으론 재현 안 됨
        r, out = self.collect(self.bundle(self.payload(flip=last, prefix=data)), p)
        self.refused(r, out, "커밋 팩 내용이 없다 1건(첫: %s)" % last)
        # 대조: 같은 꼴에서 깨지지 않았으면 통과(앞에 놓인 사본이 순차 탐색을 망치지 않음)
        r, out = self.collect(self.bundle(self.payload(prefix=data)), p)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_n_med2_anchor_far_and_decoy_first_item(self):
        """실물 꼴(첫 항목이 64KiB 창보다 훨씬 뒤) + 첫 항목의 사본이 앞쪽에 따로 있음(다른 include_str! 꼴) = 통과 ·
        같은 꼴에서 중간 항목이 깨지면 거부(닻을 바꿔도 사슬이 안 이어짐)."""
        p, _ = self.bi()
        first = self.items[0][1]
        far = self.collect(self.bundle(self.payload(prefix=b"\0" * 100000)), p)[0]  # 사본 없이 멀리만(실물 1.1.20 꼴)
        self.assertEqual(far.returncode, 0, far.stderr)
        decoy = first + b"\0" * 100000
        r, out = self.collect(self.bundle(self.payload(prefix=decoy)), p)
        self.assertEqual(r.returncode, 0, r.stderr)
        r, out = self.collect(self.bundle(self.payload(prefix=decoy, flip="sub/b.md")), p)
        self.refused(r, out, "커밋 팩 내용이 없다 1건(첫: sub/b.md)")

    def test_n_med2_chain_unit(self):
        """pack_chain_missing 단위: 순서 바뀜·겹침·같은 내용 합침 = 빠짐 · 빈 파일 = 통과."""
        spec = importlib.util.spec_from_file_location("cx64", os.path.join(UPD, "collect_x64_static.py"))
        cx = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cx)
        it = [("a", b"AAAA"), ("b", b"BBBB"), ("e", b""), ("c", b"CCCC")]
        self.assertEqual(cx.pack_chain_missing(b"xx" + b"AAAABBBBCCCC", it), [])
        # codex N 1R major 반례: 이른 중간 사본(BBBB @4) 뒤에 유효 사슬(b @65008 · c @66012) — 사본 하나에 고정하면 거짓 거부
        three = [("a", b"AAAA"), ("b", b"BBBB"), ("c", b"CCCC")]
        self.assertEqual(cx.pack_chain_missing(b"AAAABBBB" + b"\0" * 65000 + b"BBBB" + b"\0" * 1000 + b"CCCC", three), [])
        self.assertEqual(cx.pack_chain_missing(b"BBBBAAAACCCC", it), ["b"])                       # 순서 바뀜
        self.assertEqual(cx.pack_chain_missing(b"AAAA" + b"\0" * 70000 + b"BBBBCCCC", it), ["b"])  # 창 밖
        self.assertEqual(cx.pack_chain_missing(b"AAAABBBB", [("a", b"AAAABB"), ("b", b"BBBB")]), ["b"])  # 겹침
        self.assertEqual(cx.pack_chain_missing(b"AAAACCCC", [("a", b"AAAA"), ("a2", b"AAAA"), ("c", b"CCCC")]),
                         ["a2 (앞 항목과 같은 내용)"])                                              # 같은 내용 합침
        self.assertEqual(cx.pack_chain_missing(b"zz", [("e", b"")]), [])
        self.assertEqual(cx.pack_chain_missing(b"zz", [("a", b"AAAA")]), ["a"])

    def test_n_med2_symlink_in_pack_tree_refused(self):
        """팩 트리의 심볼릭 링크(mode 120000)는 typ 이 blob 이어도 거부."""
        os.symlink("a.txt", os.path.join(self.g, "cysjavis-pack", "link.txt"))
        genv = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_AUTHOR_NAME="t",
                    GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        for a in (["add", "-A"], ["commit", "-q", "-m", "link"]):
            self.assertEqual(run(["git", "-C", self.g, *a], env=genv).returncode, 0, a)
        self.assertIn("120000", run(["git", "-C", self.g, "ls-tree", "HEAD", "cysjavis-pack/link.txt"]).stdout)
        bid = run(["git", "-C", self.g, "rev-parse", "--short=12", "HEAD"]).stdout.strip() + ".20261126T0000Z"
        p, _ = self.bi(build_id=bid)
        r, out = self.collect(self.bundle(self.payload(bid=bid)), p)
        self.refused(r, out, "심볼릭 링크 항목: link.txt")

    def test_n_med2_bundle_cys_symlink_refused(self):
        """번들 안 Contents/MacOS/cys 가 심볼릭 링크면 거부(실행·대조 전에). codesign 은 **주 실행 파일**이 링크면 스스로
        서명을 거부하므로(실측) 주 실행 파일 이름을 바꾸고 cys 만 링크로 둔 꼴 = 봉인은 통과하는 꼴로 잰다."""
        p, _ = self.bi()
        z = self.bundle(self.payload())
        d = os.path.join(self.tmp, "relink")
        subprocess.check_call(["ditto", "-x", "-k", z, d])
        app = os.path.join(d, "cysr.app")
        exe = os.path.join(app, "Contents", "MacOS", "cys")
        os.rename(exe, os.path.join(app, "Contents", "MacOS", "cys-real"))
        os.symlink("cys-real", exe)
        plist = os.path.join(app, "Contents", "Info.plist")
        body = open(plist).read()  # 먼저 읽는다(codex N 1R minor: open(…, "w") 가 먼저 비우던 결함)
        self.assertIn("<string>cys</string>", body)
        open(plist, "w").write(body.replace("<string>cys</string>", "<string>cys-real</string>"))
        self.assertEqual(plistlib.load(open(plist, "rb"))["CFBundleExecutable"], "cys-real")
        for t in (os.path.join(app, "Contents", "MacOS", "cys-real"), app):  # 안쪽 실행 파일 서명이 옛 Info.plist 에 묶여 있어 다시
            subprocess.check_call(["codesign", "-s", "-", "--force", t], stderr=subprocess.DEVNULL)
        v = run(["codesign", "--verify", "--deep", "--strict", app])
        self.assertEqual(v.returncode, 0, v.stderr)  # 대조: 봉인은 통과하는 꼴
        z2 = os.path.join(self.tmp, "relink.zip")
        subprocess.check_call(["ditto", "-c", "-k", "--keepParent", app, z2])
        r, out = self.collect(z2, p)
        self.refused(r, out, "심볼릭 링크다")

    def test_x64_branch_never_executes_bundle_binary(self):
        src = open(os.path.join(UPD, "collect-inputs.sh"), encoding="utf-8").read()
        a = src.index('    if [ "$target" = macos-arm64 ]; then')
        e = src.index("    else\n", a)
        f = src.index("    fi\n", e)
        self.assertEqual(src.count('"$bin" build-info'), 1)
        self.assertTrue(a < src.index('"$bin" build-info') < e)  # 실행 줄 = arm64 갈래 안에만
        self.assertNotIn('"$bin"', src[e:f].replace('lipo -archs "$bin"', "").replace('--bin "$bin"', ""))


@unittest.skipUnless(VERIFY_BIN, "빌드된 cys(CYS_UPDATE_VERIFY_BIN) 필요")
class TestBuildMarkInBinary(unittest.TestCase):
    def test_build_mark_once_and_equals_build_info(self):
        """1.1.20 #57 ②: 빌드된 cys 바이트 안에 빌드 표지가 **정확히 1번** · 글자 = 그 바이너리 build-info 의 seq·build_id(개발 빌드 = seq 0)."""
        blob = open(VERIFY_BIN, "rb").read()
        self.assertEqual(blob.count(b"cysr-buildmark:"), 1)
        m = re.search(rb"cysr-buildmark:seq=([0-9]+);build_id=([0-9A-Za-z.\-]+);version=([0-9A-Za-z.+\-]+);pack=([0-9a-f]{64});", blob)
        bi = json.loads(run([VERIFY_BIN, "build-info", "--json"], env=dict(os.environ, CYS_UPDATE_STATE_DIR=tempfile.mkdtemp())).stdout)
        self.assertEqual((int(m.group(1)), m.group(2).decode(), m.group(3).decode(), m.group(4).decode()),
                         (bi["release_seq"], bi["build_id"], bi["version"], bi["bundled_pack"]["digest"]))


class TestOfflinePyLow3(unittest.TestCase):
    """1.1.21 N low3(agy · TICKET=cysr-1121-integ): _offline_py 는 PYTHONPYCACHEPREFIX 가 없어도 소스 옆 __pycache__ 를
    읽지도 쓰지도 않는다(늘 -I -B + 이 호출만의 빈 pycache 자리 · 끝나면 지움 · 종료 코드 그대로)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="u3low3-")
        self.lib = os.path.join(UPD, "lib", "offline-sign.sh")
        self.t = os.path.join(self.tmp, "t")
        os.makedirs(self.t)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
        self.env["TMPDIR"] = self.t

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _py(self, *args):
        return run(["bash", "-c", '. "$1"; shift; _offline_py "$@"', "_", self.lib, *args], env=self.env)

    def test_hijack_pyc_not_read_without_prefix(self):
        d = os.path.join(self.tmp, "m")
        os.makedirs(d)
        src = os.path.join(d, "update_common.py")
        open(src, "w").write("OK = 1\n")
        hj = run(["python3", "-c", (
            "import importlib.util as u, importlib._bootstrap_external as e, os, sys\n"
            "src = sys.argv[1]; st = os.stat(src)\n"
            "code = compile('import sys\\nprint(\\'PYC-HIJACK\\', file=sys.stderr)\\nsys.exit(7)\\n', src, 'exec')\n"
            "pyc = u.cache_from_source(src); os.makedirs(os.path.dirname(pyc), exist_ok=True)\n"
            "open(pyc, 'wb').write(e._code_to_timestamp_pyc(code, int(st.st_mtime), st.st_size))\n"
            "print(pyc)\n"), src])
        self.assertEqual(hj.returncode, 0, hj.stderr)
        pyc = hj.stdout.strip()
        before = open(pyc, "rb").read()
        imp = "import sys; sys.path.insert(0, sys.argv[1]); import update_common"
        ctl = run(["python3", "-I", "-c", imp, d], env=self.env)  # 대조: 옛 갈래(맨 -I)는 먹힌다
        self.assertEqual(ctl.returncode, 7, ctl.stderr)
        r = self._py("-c", imp, d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("PYC-HIJACK", r.stderr)
        self.assertEqual(open(pyc, "rb").read(), before)
        self.assertEqual(os.listdir(self.t), [])  # 빈 임시 자리는 지워졌다

    def test_no_pyc_written_and_rc_passthrough(self):
        d = os.path.join(self.tmp, "w")
        os.makedirs(d)
        open(os.path.join(d, "fresh_mod.py"), "w").write("X = 1\n")
        r = self._py("-c", "import sys; sys.path.insert(0, sys.argv[1]); import fresh_mod", d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(d, "__pycache__")))
        r = self._py("-c", "raise SystemExit(5)")
        self.assertEqual(r.returncode, 5, r.stderr)
        r = self._py("-c", "import sys; print(sys.pycache_prefix, sys.dont_write_bytecode, sys.flags.isolated)")
        self.assertEqual(r.stdout.split(), ["/dev/null/cys-nopyc", "True", "1"])  # 만들 수 없는 자리 = 임시 폴더 0 · 신호로 끊겨도 잔재 0
        self.assertEqual(os.listdir(self.t), [])
        # PYTHONPYCACHEPREFIX 가 있으면 그 자리를 쓴다(새 임시 자리 0 · sign-release --expect-head 갈래 그대로)
        pfx = os.path.join(self.tmp, "pfx")
        os.makedirs(pfx)
        self.env["PYTHONPYCACHEPREFIX"] = pfx
        r = self._py("-c", "import sys; print(sys.pycache_prefix, sys.dont_write_bytecode)")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), [pfx, "True"])
        self.assertEqual(os.listdir(self.t), [])


class TestSourcePins(unittest.TestCase):
    """저장소 소스 핀 — 수리가 되돌려지면 여기서 잡힌다."""

    def test_i20_local_build_shares_one_build_id(self):
        """1.1.20 #57 ③: build-macos-local.sh 가 타깃 반복 **전에** CYSR_BUILD_ID 를 한 번 정해 export(build.rs local_build_id 와 같은 형식) —
        실제 셸로 그 덩어리만 돌려 형식·재사용을 잰다(빌드 0)."""
        src = open(os.path.join(ROOT, "scripts", "build-macos-local.sh"), encoding="utf-8").read()
        i, j = src.index("_bid_now() {"), src.index("export CYSR_BUILD_ID")  # (R1-b) 함수 정의부터
        self.assertLess(j, src.index('for T in "${TARGETS[@]}"; do'))
        chunk = src[i:src.index("\n", j) + 1] + 'printf "%s" "$CYSR_BUILD_ID"\n'
        env = {k: v for k, v in os.environ.items() if k != "CYSR_BUILD_ID"}
        r = run(["bash", "-c", "set -euo pipefail\n" + chunk], cwd=ROOT, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"^[0-9a-f]{12}(-dirty)?\.\d{8}T\d{4}Z$")
        self.assertTrue(r.stdout.startswith(run(["git", "-C", ROOT, "rev-parse", "--short=12", "HEAD"]).stdout.strip()))
        r = run(["bash", "-c", "set -euo pipefail\n" + chunk], cwd=ROOT, env=dict(env, CYSR_BUILD_ID="given.20260101T0000Z"))
        self.assertEqual(r.stdout, "given.20260101T0000Z")
        b = open(os.path.join(ROOT, "build.rs"), encoding="utf-8").read()
        self.assertIn('format!("{sha}{}.{}", if dirty { "-dirty" } else { "" }, utc_stamp(secs))', b)  # 형식 정본(바뀌면 여기도)

    def test_i20_r6_loop_never_changes_build_id(self):
        """검증 R6⑴: 타깃 반복 안에서 CYSR_BUILD_ID 를 바꾸거나 지우는 줄 0(반복 앞에서 한 번 정한 값을 모든 타깃이 받음)."""
        src = open(os.path.join(ROOT, "scripts", "build-macos-local.sh"), encoding="utf-8").read()
        a = src.index('for T in "${TARGETS[@]}"; do')
        loop = src[a:src.index("\ndone\n", a)]
        code = [l for l in loop.splitlines() if not l.lstrip().startswith("#")]
        # 읽어서 대조하는 줄(R1-a 재대조)은 허용 · 바꾸는 줄(대입·unset·export)만 금지
        self.assertEqual([l for l in code if re.search(r"(unset|export)\s+CYSR_(BUILD_ID|RELEASE_SEQ)|CYSR_(BUILD_ID|RELEASE_SEQ)=", l)], [])
        self.assertTrue(any('[ "${CYSR_BUILD_ID%%.*}" = "$_bid_head" ]' in l for l in code), "타깃마다 재대조 줄")

    def test_i20_r1b_local_build_status_failure_and_per_target_recheck(self):
        """검증 R1-a·R1-b(build-macos-local.sh): git status 실패 = rc 2(종전 = 깨끗으로 봄) · 타깃마다 HEAD·dirty 재대조 = 다른 커밋 id 면 rc 2."""
        src = open(os.path.join(ROOT, "scripts", "build-macos-local.sh"), encoding="utf-8").read()
        fn = src[src.index("_bid_now() {"):src.index("\n}\n", src.index("_bid_now() {")) + 3]
        a = src.index('for T in "${TARGETS[@]}"; do')
        k = src.index('  _bid_head="$(_bid_now)" || exit 2\n', a)
        recheck = src[k:src.index("\n", src.index('[ "${CYSR_BUILD_ID%%.*}"', k)) + 1]
        env = {k2: v for k2, v in os.environ.items() if not k2.startswith("GIT_CONFIG")}
        bad = dict(env, GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="status.relativePaths", GIT_CONFIG_VALUE_0="not-a-boolean")
        self.assertEqual(run(["git", "-C", ROOT, "status", "--porcelain"], env=bad).returncode, 128)  # 전제: 이 프로세스만 status 실패
        r = run(["bash", "-c", "set -euo pipefail\n" + fn + '_bid_now >/dev/null\necho OK\n'], cwd=ROOT, env=bad)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("git status 실패", r.stderr)
        head = run(["bash", "-c", fn + "_bid_now"], cwd=ROOT, env=env).stdout.strip()
        for bid, rc in ((head + ".20261126T0800Z", 0), ("fedcba987654.20261126T0800Z", 2)):
            r = run(["bash", "-c", "set -euo pipefail\nT=x\nCYSR_BUILD_ID=%s\n%s%secho OK\n" % (bid, fn, recheck)], cwd=ROOT, env=env)
            self.assertEqual(r.returncode, rc, (bid, r.stderr))
        self.assertIn("빌드 중단", r.stderr)
        lib = open(os.path.join(ROOT, "scripts", "lib", "mac-bundle-common.sh"), encoding="utf-8").read()
        self.assertEqual([l for l in lib.splitlines() if not l.lstrip().startswith("#") and ("CYSR_BUILD_ID" in l or "env -i" in l)], [])

    def test_i20_r1_build_rs_given_id_watches_sources_and_status_failure_stops(self):
        """검증 R3 📌⑴(build.rs a9a2da6b3 의 두 고침 · build.rs 는 시험 하네스가 없어 소스 핀):
        ⑴ CYSR_BUILD_ID 를 받은 갈래 = rerun-if-changed 다섯 경로(src·src-tauri·vendor·Cargo.toml·Cargo.lock · 실재하는 것만)
        ⑵ 그 갈래의 HEAD·dirty 관측 = head_and_dirty_strict(rev-parse·status 실패 = Err → panic · 「깨끗」 으로 보지 않음).
        되돌리면(R3 변이 b1 = 감시 제거 · b2 = status 실패 관대) 같은 커밋 소스 수정·status 실패에도 깨끗한 id 가 통과한다."""
        b = open(os.path.join(ROOT, "build.rs"), encoding="utf-8").read()
        code = lambda s: "\n".join(l.split("//")[0].rstrip() for l in s.splitlines())  # 주석 줄·꼬리 주석 걷기
        a = b.index('Ok(v) if !v.is_empty() => {')
        arm = code(b[a:b.index("_ => local_build_id(&manifest_dir),", a)])
        self.assertIn('for p in ["src", "src-tauri", "vendor", "Cargo.toml", "Cargo.lock"] {', arm)
        loop = arm[arm.index('for p in ["src"'):]
        self.assertRegex(loop, r'^for p in \[[^\]]*\] \{\s*if Path::new\(&manifest_dir\)\.join\(p\)\.exists\(\) \{\s*println!\("cargo:rerun-if-changed=\{p\}"\);')
        self.assertIn("match head_and_dirty_strict(&manifest_dir) {", arm)
        self.assertRegex(arm, r'Err\(why\) => panic!\(')
        self.assertLess(arm.index("head_and_dirty_strict"), arm.index("build_id_guard::given_build_id_problem"))
        self.assertNotIn("unwrap_or", arm)
        f = b.index("fn head_and_dirty_strict(")
        fn = code(b[f:b.index("\n}\n", f) + 3])
        self.assertRegex(fn, r'if !o\.status\.success\(\) \{\s*return Err\(')
        self.assertIn('let head = run(&["rev-parse", "--short=12", "HEAD"])?;', fn)
        self.assertIn('let dirty = !run(&["status", "--porcelain", "--untracked-files=no"])?.is_empty();', fn)
        self.assertNotIn("unwrap_or", fn)

    def test_bundle_prep_passes_min_binary(self):
        s = open(os.path.join(ROOT, "scripts", "bundle-prep.sh"), encoding="utf-8").read()
        line = [l for l in s.splitlines() if 'manifest_cys" pack-manifest' in l]
        self.assertEqual(len(line), 1, line)
        self.assertIn("--min-binary-version", line[0])
        self.assertIn("min_binary 빈 값", s)

    def test_a2_key_id_matches_tauri_conf(self):
        conf = json.load(open(os.path.join(ROOT, "src-tauri", "tauri.conf.json"), encoding="utf-8"))
        pub = ((conf.get("plugins") or {}).get("updater") or {}).get("pubkey")
        if pub:
            self.assertEqual(uc.pubkey_key_id(pub), uc.A2_KEY_ID)
            self.assertEqual(pub, uc.A2_PUBKEY)  # 2판(codex 1R #4): 7-b 암호 검증 기준 상수 = 현 conf 값
        self.assertEqual(uc.pubkey_key_id(uc.A2_PUBKEY), uc.A2_KEY_ID)
        rv = open(os.path.join(ROOT, "scripts", "release-verify.py"), encoding="utf-8").read()
        self.assertIn('A2_KEY_ID = "%s"' % uc.A2_KEY_ID, rv)

    def test_release_verify_pack_keyring_ignores_update_keys(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("rv", os.path.join(ROOT, "scripts", "release-verify.py"))
        rv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rv)
        d = tempfile.mkdtemp()
        try:
            fx = Fixture(d)
            kr = json.load(open(fx.keyring))
            pack = dict(kr["keys"][0], purpose="pack")
            kr["keys"].append(pack)
            json.dump(kr, open(fx.keyring, "w"))
            got, _ = rv.load_pack_keyring(fx.keyring)
            self.assertEqual(list(got), [pack["key_id"]])  # root·release·feed 키는 팩 기준에서 빠진다
        finally:
            shutil.rmtree(d)

    def test_refresh_feed_workflow_shape(self):
        """2판(codex 1R #6·#9·#11·#16): CI = 생성+검증+아티팩트 · 게시·사이트 비밀 0 · 현재 봉투 검증이 상속보다 먼저."""
        s = open(os.path.join(ROOT, ".github", "workflows", "refresh-feed.yml"), encoding="utf-8").read()
        body = "\n".join(l for l in s[s.index("\njobs:"):].splitlines() if not l.lstrip().startswith("#"))
        import re
        self.assertEqual(sorted(set(re.findall(r"secrets\.([A-Z_]+)", body))),
                         ["CYS_FEED_SIGNING_PRIVATE_KEY", "CYS_FEED_SIGNING_PRIVATE_KEY_PASSWORD"])
        for bad in ("wrangler", "git push", "publish-site.py", "--installed-release-seq", "AI_JARVIS", "CLOUDFLARE",
                    "inputs.publish"):
            self.assertNotIn(bad, body, bad)
        self.assertIn("--prev-envelope feed/cur.json --cys target/release/cys --revocations feed/rev.json", body)
        self.assertLess(body.index("cargo build --release --bin cys"), body.index("make-envelope.py"))
        self.assertLess(body.index("make-envelope.py"), body.index("--envelope feed/env.json"))

    def test_workflows_actions_sha_pinned(self):
        """3판(codex 2R #9): 전 워크플로의 서드파티 액션 = 40자 commit SHA(+ 태그 주석) · rust-toolchain 은 toolchain 명시 ·
        F 비밀 잡 = environment feed."""
        import glob
        import re
        for f in glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml")):
            for i, l in enumerate(open(f, encoding="utf-8").read().splitlines(), 1):
                m = re.match(r"^\s*(?:- )?uses:\s*([^\s#]+)", l)
                if m and not m.group(1).startswith("./"):
                    self.assertRegex(m.group(1), r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$", "%s:%d" % (f, i))
                    self.assertIn("#", l, "%s:%d 태그 주석 없음" % (f, i))
                    if "dtolnay/rust-toolchain" in l:
                        nxt = open(f, encoding="utf-8").read().splitlines()[i:i + 4]
                        self.assertTrue(any("toolchain: stable" in x for x in nxt), "%s:%d" % (f, i))
        rf = open(os.path.join(ROOT, ".github", "workflows", "refresh-feed.yml"), encoding="utf-8").read()
        self.assertIn("    environment: feed\n", rf)

    def test_release_yml_seq_and_win_inputs(self):
        """2판(codex 1R #1·#18): release_seq 배선 + 빌드 전 정수 검사(cys 빌드 잡 둘) · 윈 재료 스텝 실패 = 릴리스 실패."""
        s = open(os.path.join(ROOT, ".github", "workflows", "release.yml"), encoding="utf-8").read()
        self.assertIn("  CYSR_RELEASE_SEQ: ${{ vars.CYSR_RELEASE_SEQ }}\n", s[:s.index("\njobs:")])
        chk = "- name: CYSR_RELEASE_SEQ 정수 ≥1"
        self.assertEqual(s.count(chk), 2)
        for job in ("\n  build:\n", "\n  pack-artifacts:\n"):
            a = s.index(job)
            nxt = min(i for i in (s.find("\n  %s" % c, a + len(job)) for c in "abcdefghijklmnopqrstuvwxyz") if i > 0)
            seg = s[a:nxt]
            self.assertIn(chk, seg, job)
            self.assertLess(seg.index(chk), seg.index("cargo build") if "cargo build" in seg else len(seg), job)
        for name in ("자동 갱신 본문 재료 수집 (윈", "자동 갱신 본문 재료 업로드 (윈)"):
            i = s.index("- name: " + name)
            step = s[i:s.index("\n      - ", i + 1)]
            self.assertNotIn("continue-on-error", step, name)
        self.assertIn("if-no-files-found: error", s[s.index("- name: 자동 갱신 본문 재료 업로드 (윈)"):][:400])

    def test_nsis_lock_token_hook(self):
        s = open(os.path.join(ROOT, "src-tauri", "nsis-hooks.nsh"), encoding="utf-8").read()
        i, j = s.find("⓪-a"), s.find("Global\\cys-installer")
        self.assertGreater(i, 0)
        self.assertIn("/CYSTXN=", s)
        self.assertIn("SetErrorLevel 6", s)
        self.assertLess(i, j, "⓪-a 는 ⓪ 뮤텍스 앞에 있어야 한다")

    def test_nsis_lock_token_conditions(self):
        """2판 · codex 1R #13 ⑴~⑷ 소스 핀(실행 증거 아님 — 실행 = 윈 실기 6 시나리오 · docs/update/WIN-NSIS-0A-FIELD.md)."""
        s = open(os.path.join(ROOT, "src-tauri", "nsis-hooks.nsh"), encoding="utf-8").read()
        a, b = s.find("!macro NSIS_HOOK_PREINSTALL"), s.find("cys_txn_free:\n")
        self.assertTrue(0 < a < b)
        blk = [l.strip() for l in s[a:b].splitlines() if l.strip() and not l.strip().startswith(";")]

        def at(line):
            self.assertIn(line, blk)
            return blk.index(line)
        # ⑴ 잠금 없음(파일 없음 · 비차단 잠금 성공) → cys_txn_notheld → 인자 있으면 refuse
        at('IfFileExists "$LOCALAPPDATA\\cys-update\\txn.lock" 0 cys_txn_notheld')
        nh = at("cys_txn_notheld:")
        self.assertEqual(blk[nh + 1], 'StrCmp $CysTxnArg "1" 0 cys_txn_free')
        self.assertIn("Goto cys_txn_refuse", blk[nh + 2:nh + 4])
        jumps_free = [l for l in blk if l.split()[-1:] == ["cys_txn_free"] or l == "Goto cys_txn_free"]
        self.assertEqual(jumps_free, ['StrCmp $CysTxnArg "1" 0 cys_txn_free'], "잠금 없음 갈래가 인자 검사를 건너뛴다")
        # ⑵ 인자 = env(대소문자 구분) · 소유자 기록 대조보다 먼저
        held, env = at("cys_txn_held:"), at('ReadEnvStr $CysTxnTmp "CYS_UPDATE_TXN"')
        cmp_ = at("StrCmpS $CysTxnTmp $CysTxnTok 0 cys_txn_refuse")
        owner = next(i for i, l in enumerate(blk) if "txn.owner.json" in l)
        self.assertTrue(held < env < cmp_ < owner)
        # ⑷ 위임 켜짐 = cys_txn_ok 한 곳뿐 · ⑴⑵ 뒤
        self.assertEqual(s.count('StrCpy $CysTxnDelegated "1"'), 1)
        ok = at("cys_txn_ok:")
        self.assertIn('StrCpy $CysTxnDelegated "1"', blk[ok + 1:ok + 3])
        self.assertTrue(cmp_ < ok)
        self.assertIn('StrCmp $CysTxnDelegated "1" cys_pre_single 0', s)
        # ⑵′ 3판(2R #13 TOCTOU): 소유자 대조 → cys_txn_recheck(같은 핸들 LockFileEx 재시도) → 아직 잡혀 있을 때만 cys_txn_ok
        rc = at("cys_txn_recheck:")
        self.assertTrue(owner < rc < ok)
        self.assertEqual(blk[rc + 1], "IntPtrCmp $CysTxnLk -1 cys_txn_refuse 0 0")
        self.assertIn("LockFileEx(p $CysTxnLk", blk[rc + 2])
        self.assertNotIn("Goto cys_txn_ok", "\n".join(blk[:rc]))
        self.assertEqual([l for l in blk if l.endswith(" cys_txn_ok") or l.endswith(" cys_txn_ok 0")], ["Goto cys_txn_ok"])
        # ⑶ 조상 대조 = 러너 쪽(설계 §3-7 ④ 인용 주석)
        self.assertIn("설계 §3-7 ④", s[a:b])


if __name__ == "__main__":
    _r = unittest.main(verbosity=1, exit=False).result
    if REQUIRE_ALL and _r.skipped:
        print("::error::CYS_U3_REQUIRE_ALL=1 인데 건너뜀 %d건 = 실패(codex 1R #17): %s"
              % (len(_r.skipped), " · ".join("%s(%s)" % (t.id().split(".")[-1], why) for t, why in _r.skipped)))
        sys.exit(1)
    sys.exit(0 if _r.wasSuccessful() else 1)
