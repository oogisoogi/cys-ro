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
NOW = 1790000000
# 시험 전용 모드(실 키 서명 거부 · 신뢰 시각 덮어쓰기 · 가짜 minisign/매체 허용 — codex 1R #3·#15)
os.environ["CYS_SIGN_DEV"] = "1"
os.environ["CYS_TEST_NOW"] = str(NOW)


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


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
        r0, _ = self.env("--prev-envelope", out, name="env1b.json")
        self.assertEqual(r0.returncode, 2)  # U1 통과 증표 없는 직전 봉투 = 상속 거부(codex 1R #6)
        self.assertIn("증표", r0.stderr)
        fm.sign(self.fx.key("f"), out, out + ".minisig", "t")
        u1_stamp(out)
        self.now = NOW + 60
        r2, out2 = self.env("--prev-envelope", out, name="env2.json")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        e2 = json.load(open(out2))
        self.assertEqual((e2["feed_rev"], e2["rollout_pct"]), (2, 10))
        self.assertEqual(e2["release"], e["release"])

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

    def test_mut_older_release(self):
        r, out = self.env("--first", "--rollout-pct", "10", "--halt", "false")
        d = os.path.join(self.tmp, "o")
        os.makedirs(d)
        fx2 = Fixture(d, seq=4)
        fx2.keys["u"] = self.fx.keys["u"]
        shutil.copy(self.fx.key("u"), fx2.key("u"))
        b4 = fx2.body()
        r2 = py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", b4,
                "--release-sig", b4 + ".minisig", "--key-id", self.fx.kid("f"), "--prev-envelope", out,
                "--keyring", self.fx.keyring, "--out", os.path.join(self.tmp, "e3.json"))
        self.assertEqual(r2.returncode, 2)
        self.assertIn("증표", r2.stderr)  # 증표 없는 직전 봉투는 상속 자체가 거부된다
        fm.sign(self.fx.key("f"), out, out + ".minisig", "t")
        u1_stamp(out)
        r3 = py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", b4,
                "--release-sig", b4 + ".minisig", "--key-id", self.fx.kid("f"), "--prev-envelope", out,
                "--keyring", self.fx.keyring, "--out", os.path.join(self.tmp, "e4.json"), now=NOW + 60)
        self.assertEqual(r3.returncode, 2)
        self.assertIn("후퇴", r3.stderr)

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
    r = py("release-gate.py", "body", "--body", b, "--sig", b + ".minisig", "--keyring", fx.keyring, "--stamp")
    assert r.returncode == 0, r.stderr
    return b


def publish(fx, kind, f, store, *extra):
    return py("publish-site.py", kind, "--fs", store, "--file", f, "--keyring", fx.keyring,
              "--lock-file", os.path.join(store + ".lock"), *extra)


class TestPublishSite(Base):
    def test_archive_immutable_and_index(self):
        b = gate_stamp_body(self.fx, self.fx.body())
        st = os.path.join(self.tmp, "store")
        r = publish(self.fx, "archive", b, st)
        self.assertEqual(r.returncode, 3)  # 색인 없음 + --first 없음
        self.assertEqual(publish(self.fx, "archive", b, st, "--first").returncode, 0)
        ptr = json.load(open(os.path.join(st, "ptr/update/cysr/releases/5.json")))
        self.assertEqual(open(os.path.join(st, ptr["json"]), "rb").read(), open(b, "rb").read())
        self.assertEqual(json.load(open(os.path.join(st, "ptr/update/cysr/releases/_index")))["max_seq"], 5)
        r = publish(self.fx, "archive", b, st)
        self.assertEqual(r.returncode, 0)
        self.assertIn("멱등", r.stdout)
        b2 = gate_stamp_body(self.fx, self.fx.body(name="body2.json", **{"--notes-ko": "다른 문구예요"}))
        r = publish(self.fx, "archive", b2, st)
        self.assertEqual(r.returncode, 3, r.stderr)  # 같은 seq 다른 바이트 — 색인 단계에서 seq ≠ max+1 로도 거부

    def test_mut_no_stamp_or_tampered(self):
        b = self.fx.body()
        st = os.path.join(self.tmp, "store")
        r = publish(self.fx, "archive", b, st, "--first")
        self.assertEqual(r.returncode, 2)
        self.assertIn("증표", r.stderr)
        gate_stamp_body(self.fx, b)
        open(b, "ab").write(b" ")
        r = publish(self.fx, "archive", b, st, "--first")
        self.assertEqual(r.returncode, 2)
        self.assertIn("검증 뒤 바뀜", r.stderr)

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

    def test_envelope_monotone_and_pair_atomic(self):
        b = self.fx.body()
        st = os.path.join(self.tmp, "store")

        def env(name, *extra, now=NOW):
            out = os.path.join(self.tmp, name)
            r = py("make-envelope.py", "--component", "cysr", "--channel", "next", "--release-body", b, "--release-sig",
                   b + ".minisig", "--key-id", self.fx.kid("f"), "--keyring", self.fx.keyring, "--out", out, *extra, now=now)
            self.assertEqual(r.returncode, 0, r.stderr)
            fm.sign(self.fx.key("f"), out, out + ".minisig", "t")
            u1_stamp(out)
            return out
        e1 = env("e1.json", "--first", "--rollout-pct", "5", "--halt", "false")
        self.assertEqual(publish(self.fx, "envelope", e1, st).returncode, 0)
        e0 = env("e0.json", "--first", "--rollout-pct", "50", "--halt", "false")
        r = publish(self.fx, "envelope", e0, st)
        self.assertEqual(r.returncode, 3)
        self.assertIn("단조 위반", r.stderr)
        e2 = env("e2.json", "--prev-envelope", e1, now=NOW + 60)
        self.assertEqual(publish(self.fx, "envelope", e2, st).returncode, 0)
        ptr = json.load(open(os.path.join(st, "ptr/update/cysr/next.json")))
        self.assertEqual((ptr["feed_rev"], ptr["json_sha256"]), (2, uc.sha256_bytes(open(e2, "rb").read())))
        self.assertEqual(ptr["sig_sha256"], uc.sha256_bytes(open(e2 + ".minisig", "rb").read()))

    def test_concurrent_publish_two(self):
        b = gate_stamp_body(self.fx, self.fx.body())
        st = os.path.join(self.tmp, "store")
        procs = [subprocess.Popen([sys.executable, os.path.join(UPD, "publish-site.py"), "archive", "--fs", st, "--file", b,
                                   "--keyring", self.fx.keyring, "--lock-file", st + ".lock", "--first"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        rcs = sorted(p.wait() for p in procs)
        self.assertEqual(rcs, [0, 0])  # 하나는 게시 · 하나는 잠금 뒤 재검사 = 멱등(같은 바이트)
        self.assertEqual(json.load(open(os.path.join(st, "ptr/update/cysr/releases/_index")))["max_seq"], 5)


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
        self.assertEqual(publish(self.fx, "revocations", out, st).returncode, 0)


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("hdiutil"), "가짜 매체 = hdiutil 마운트(맥 전용)")
class TestOfflineRitual(Base):
    def setUp(self):
        super().setUp()
        self.mnt = os.path.join(self.tmp, "mnt")
        os.makedirs(self.mnt)
        dmg = os.path.join(self.tmp, "m.dmg")
        subprocess.check_call(["hdiutil", "create", "-size", "4m", "-fs", "HFS+", "-volname", "U3FAKE", "-quiet", dmg])
        subprocess.check_call(["hdiutil", "attach", dmg, "-mountpoint", self.mnt, "-nobrowse", "-quiet"])
        for k in ("u", "r"):
            shutil.move(self.fx.key(k), os.path.join(self.mnt, k + ".key"))
        self.mini = os.path.join(self.tmp, "mini.sh")
        open(self.mini, "w").write('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, FAKE))
        os.chmod(self.mini, 0o755)
        self.env = dict(os.environ, MINISIGN=self.mini, CYS_SIGN_MEDIA_PREFIX=self.tmp + "/")

    def tearDown(self):
        subprocess.call(["hdiutil", "detach", self.mnt, "-quiet"])
        super().tearDown()

    def sign(self, body, key, out, media=None):
        return run(["bash", os.path.join(UPD, "sign-release.sh"), "--body", body, "--media", media or self.mnt,
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
        r = run(["bash", os.path.join(UPD, "sign-revocations.sh"), "--doc", doc, "--media", self.mnt,
                 "--key", os.path.join(self.mnt, "r.key"), "--keyring", self.fx.keyring,
                 "--out-dir", os.path.join(self.tmp, "rout"), "--wait-eject", "0"], env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)

    # ── codex 1R #3: 시험 손잡이는 개발 모드 전용 · 개발 모드는 실 키 거부 · 키 생성도 매체 안 ─────────────
    def real_env(self, **extra):
        e = {k: v for k, v in os.environ.items() if k not in ("CYS_SIGN_DEV", "CYS_TEST_NOW", "MINISIGN",
                                                              "CYS_SIGN_MEDIA_PREFIX")}
        e.update(extra)
        return e

    def test_mut_handle_outside_dev(self):
        b = self.unsigned_body()
        for name, val in (("MINISIGN", self.mini), ("CYS_SIGN_MEDIA_PREFIX", self.tmp + "/")):
            r = run(["bash", os.path.join(UPD, "sign-release.sh"), "--body", b, "--media", self.mnt,
                     "--key", os.path.join(self.mnt, "u.key"), "--keyring", self.fx.keyring,
                     "--out-dir", os.path.join(self.tmp, "out")], env=self.real_env(**{name: val}))
            self.assertEqual(r.returncode, 2, name)
            self.assertIn("시험 손잡이 %s" % name, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "out", "cysr-release-5.json.minisig")))

    def test_mut_wait0_outside_dev(self):
        b = self.unsigned_body()
        r = run(["bash", os.path.join(UPD, "sign-release.sh"), "--body", b, "--media", self.mnt,
                 "--key", os.path.join(self.mnt, "u.key"), "--keyring", self.fx.keyring,
                 "--out-dir", os.path.join(self.tmp, "out"), "--wait-eject", "0"], env=self.real_env())
        self.assertEqual(r.returncode, 2)
        self.assertIn("개발 모드 전용", r.stderr)

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

    def gen(self, *args, env=None):
        return run(["bash", os.path.join(UPD, "gen-offline-key.sh")] + list(args), env=env or self.env, cwd=self.tmp)

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
        r = self.gen("--media", self.mnt, "--name", "u", env=self.real_env(MINISIGN=self.mini))
        self.assertEqual(r.returncode, 2)
        self.assertIn("시험 손잡이 MINISIGN", r.stderr)
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

    def gate(self, env, expect="apply", now="1790000100", installed="4"):
        e = dict(os.environ, CYS_UPDATE_TEST_KEYRING=self.fx.keyring, CYS_UPDATE_STATE_DIR=self.state,
                 CYS_UPDATE_NOW=now)
        return py("release-gate.py", "verify", "--cys", VERIFY_BIN, "--component", "cysr", "--channel", "stable",
                  "--envelope", env, "--sig", env + ".minisig", "--revocations", self.rev,
                  "--revocations-sig", self.rev + ".minisig", "--installed-release-seq", installed,
                  "--expect", expect, env=e)

    def test_apply_both_rows(self):
        r = self.gate(self.envelope(self.b))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count("출발 seq 4 전부 허용 판정"), 2)

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

    def test_seq_not_newer_is_uptodate(self):
        self.assertEqual(self.gate(self.envelope(self.b), expect="uptodate", installed="5").returncode, 0)

    def test_mut_feed_key_used_for_body(self):
        b = json.load(open(self.b))
        b["key_id"] = self.fx.kid("f")
        open(self.b, "wb").write(uc.dump_json_bytes(b))
        fm.sign(self.fx.key("f"), self.b, self.b + ".minisig", "t")
        r = self.gate(self.hand_envelope(self.b))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("reject", r.stderr)


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
        # ⑶ 조상 대조 = 러너 쪽(설계 §3-7 ④ 인용 주석)
        self.assertIn("설계 §3-7 ④", s[a:b])


if __name__ == "__main__":
    unittest.main(verbosity=1)
