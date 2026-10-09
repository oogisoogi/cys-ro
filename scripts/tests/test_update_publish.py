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
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPD = os.path.join(ROOT, "scripts", "update")
FAKE = os.path.join(ROOT, "scripts", "tests", "fixtures", "fake_minisign.py")
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
        d = tempfile.mkdtemp(prefix="u3-req-")
        try:
            dmg, mnt = os.path.join(d, "p.dmg"), os.path.join(d, "mnt")
            os.makedirs(mnt)
            r = run(["hdiutil", "create", "-size", "1m", "-fs", "HFS+", "-volname", "U3PROBE", "-quiet", dmg])
            r = r if r.returncode else run(["hdiutil", "attach", dmg, "-mountpoint", mnt, "-nobrowse", "-quiet"])
            if r.returncode:
                bad.append("hdiutil 매체 생성·마운트 실패(rc %d): %s" % (r.returncode, (r.stderr or r.stdout).strip()[-200:]))
            else:
                run(["hdiutil", "detach", mnt, "-quiet"])
        finally:
            shutil.rmtree(d, ignore_errors=True)
    if bad:
        raise RuntimeError("CYS_U3_REQUIRE_ALL=1 전제 부재 — " + " · ".join(bad))


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


def hdiutil_retry(args, partial=None, runner=None, delay=1.0):
    """hdiutil 1회 재시도(1.1.10 · 맥 러너 간헐 실패 10-07 37543589887 = create CalledProcessError · 사유 미출력).
    실패 사유(rc·stderr)를 그 자리에서 stderr 로 내고 1회만 다시 한다 — 성공 = [] · 2회 실패 = 사유 2줄(호출자가 적색).
    partial = 실패한 create 가 남긴 반쪽 dmg(재시도 전에 지운다). 계약 약화 0: 건너뛰기 없음 · 재시도는 1회뿐."""
    runner = runner or run
    reasons = []
    for attempt in (1, 2):
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
        subprocess.check_call(["hdiutil", "create", "-size", "4m", "-fs", "HFS+", "-volname", "U3FAKE2", "-quiet", dmg])
        subprocess.check_call(["hdiutil", "attach", dmg, "-mountpoint", m2, "-nobrowse", "-quiet"])
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


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("codesign") and VERIFY_BIN,
                     "맥 재료 수집기 = codesign + build-info 가진 cys(CYS_UPDATE_VERIFY_BIN) 필요")
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


class TestSourcePins(unittest.TestCase):
    """저장소 소스 핀 — 수리가 되돌려지면 여기서 잡힌다."""

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
