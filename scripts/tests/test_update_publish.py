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


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def py(script, *args, **kw):
    return run([sys.executable, os.path.join(UPD, script)] + list(args), **kw)


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
             "--requires-min-binary-for-pack": "1.1.8", "--release-dir": self.rel,
             "--signed-at": "1790000000", "--out": out}
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
    def env(self, *extra, name="env.json"):
        b = os.path.join(self.tmp, "body.json")
        if not os.path.exists(b):
            self.fx.body()
        out = os.path.join(self.tmp, name)
        return py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", b,
                  "--release-sig", b + ".minisig", "--key-id", self.fx.kid("f"), "--out", out, *extra), out

    def test_first_and_increment(self):
        r, out = self.env("--first", "--rollout-pct", "10", "--halt", "false")
        self.assertEqual(r.returncode, 0, r.stderr)
        e = json.load(open(out))
        self.assertEqual((e["feed_rev"], e["rollout_pct"], e["halt"]), (1, 10, False))
        self.assertLessEqual(e["expires_at"] - e["signed_at"], 14 * 86400)
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
               "--halt", "false", "--out", os.path.join(self.tmp, "e.json"))
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
                "--out", os.path.join(self.tmp, "e3.json"))
        self.assertEqual(r2.returncode, 2)
        self.assertIn("후퇴", r2.stderr)


class TestPublishSite(Base):
    def test_archive_immutable(self):
        b = self.fx.body()
        site = os.path.join(self.tmp, "site")
        self.assertEqual(py("publish-site.py", "archive", "--site-dir", site, "--file", b).returncode, 0)
        p = os.path.join(site, "update", "cysr", "releases", "5.json")
        self.assertTrue(os.path.isfile(p) and os.path.isfile(p + ".minisig"))
        r = py("publish-site.py", "archive", "--site-dir", site, "--file", b)
        self.assertEqual(r.returncode, 0)
        self.assertIn("멱등", r.stdout)
        b2 = self.fx.body(name="body2.json", **{"--notes-ko": "다른 문구예요"})
        r = py("publish-site.py", "archive", "--site-dir", site, "--file", b2)
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("덮어쓰기 거부", r.stderr)
        self.assertEqual(open(p, "rb").read(), open(b, "rb").read())

    def test_envelope_monotone(self):
        b = self.fx.body()
        site = os.path.join(self.tmp, "site")
        e1 = os.path.join(self.tmp, "e1.json")
        py("make-envelope.py", "--component", "cysr", "--channel", "next", "--release-body", b, "--release-sig",
           b + ".minisig", "--key-id", self.fx.kid("f"), "--first", "--rollout-pct", "5", "--halt", "false",
           "--signed-at", "1790000000", "--out", e1)
        fm.sign(self.fx.key("f"), e1, e1 + ".minisig", "t")
        self.assertEqual(py("publish-site.py", "envelope", "--site-dir", site, "--file", e1).returncode, 0)
        e0 = os.path.join(self.tmp, "e0.json")
        py("make-envelope.py", "--component", "cysr", "--channel", "next", "--release-body", b, "--release-sig",
           b + ".minisig", "--key-id", self.fx.kid("f"), "--first", "--rollout-pct", "50", "--halt", "false",
           "--signed-at", "1790000001", "--out", e0)
        fm.sign(self.fx.key("f"), e0, e0 + ".minisig", "t")
        r = py("publish-site.py", "envelope", "--site-dir", site, "--file", e0)
        self.assertEqual(r.returncode, 3)
        self.assertIn("단조 위반", r.stderr)
        e2 = os.path.join(self.tmp, "e2.json")
        py("make-envelope.py", "--component", "cysr", "--channel", "next", "--release-body", b, "--release-sig",
           b + ".minisig", "--key-id", self.fx.kid("f"), "--prev-envelope", e1, "--out", e2)
        fm.sign(self.fx.key("f"), e2, e2 + ".minisig", "t")
        self.assertEqual(py("publish-site.py", "envelope", "--site-dir", site, "--file", e2).returncode, 0)


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
    def archive(self, b):
        site = os.path.join(self.tmp, "site")
        self.assertEqual(py("publish-site.py", "archive", "--site-dir", site, "--file", b).returncode, 0)
        return os.path.join(site, "update")

    def next_body(self, version, seq):
        d = os.path.join(self.tmp, "v%s-%d" % (version, seq))
        os.makedirs(d)
        fx = Fixture(d, version=version, seq=seq)
        fx.keys["u"] = self.fx.keys["u"]
        shutil.copy(self.fx.key("u"), fx.key("u"))
        return fx.body()

    def test_seq_and_version_progress(self):
        arch = self.archive(self.fx.body())
        ok = self.next_body("1.1.9", 6)
        self.assertEqual(py("release-gate.py", "body", "--body", ok, "--archive-dir", arch).returncode, 0)
        same = self.next_body("1.1.8", 7)
        r = py("release-gate.py", "body", "--body", same, "--archive-dir", arch)
        self.assertEqual(r.returncode, 1)
        self.assertIn("판 증가 위반", r.stderr)
        older = self.next_body("1.1.7", 4)
        r = py("release-gate.py", "body", "--body", older, "--archive-dir", arch)
        self.assertEqual(r.returncode, 1)
        self.assertIn("역행", r.stderr)

    def test_canary_needs_flag(self):
        arch = self.archive(self.fx.body())
        can = self.next_body("1.1.8+canary.1", 6)
        self.assertEqual(py("release-gate.py", "body", "--body", can, "--archive-dir", arch).returncode, 1)
        self.assertEqual(py("release-gate.py", "body", "--body", can, "--archive-dir", arch,
                            "--allow-canary").returncode, 0)

    def test_archive_same_seq_different_bytes(self):
        arch = self.archive(self.fx.body())
        b2 = self.fx.body(name="b2.json", **{"--notes-ko": "다른 문구예요"})
        r = py("release-gate.py", "body", "--body", b2, "--archive-dir", arch)
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

    def test_mut_requires_empty(self):
        self._mutate(lambda b: b["requires"].update(min_binary_for_pack=""), "빈 값")

    def test_mut_payload_traversal(self):
        self._mutate(lambda b: b["assets"]["windows-x64"]["payload_manifest"].append(
            {"path": "../x", "size": 1, "sha256": "c" * 64}), "payload_manifest 항목")

    def test_mut_sig_wrong_key(self):
        b = self.fx.body()
        fm.sign(self.fx.key("f"), b, b + ".minisig", "t")
        r = py("release-gate.py", "body", "--body", b, "--sig", b + ".minisig")
        self.assertEqual(r.returncode, 1)
        self.assertIn("서명 key id", r.stderr)


class TestRevocations(Base):
    def test_rev_and_rules(self):
        out = os.path.join(self.tmp, "rev.json")
        self.assertEqual(py("make-revocations.py", "--key-id", self.fx.kid("r"), "--first", "--out", out).returncode, 0)
        r = py("make-revocations.py", "--key-id", self.fx.kid("r"), "--out", os.path.join(self.tmp, "x.json"))
        self.assertEqual(r.returncode, 2)
        out2 = os.path.join(self.tmp, "rev2.json")
        r = py("make-revocations.py", "--key-id", self.fx.kid("r"), "--prev", out,
               "--revoke-release", "cysr:5:stop_seats:bad_build",
               "--delegate", "feed:%s:1900000000" % os.path.join(self.tmp, "u.pub"), "--out", out2)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out2))
        self.assertEqual(d["rev"], 2)
        self.assertEqual(d["revoked_releases"][0]["severity"], "stop_seats")
        self.assertEqual(d["delegations"][0]["key_id"], self.fx.kid("u"))
        for bad in (["--delegate", "root:%s:1900000000" % os.path.join(self.tmp, "u.pub")],
                    ["--revoke-key", self.fx.kid("r")],
                    ["--revoke-release", "cysr:5:panic:x"]):
            r = py("make-revocations.py", "--key-id", self.fx.kid("r"), "--prev", out, "--out",
                   os.path.join(self.tmp, "y.json"), *bad)
            self.assertEqual(r.returncode, 2, bad)


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
        py("make-revocations.py", "--key-id", self.fx.kid("r"), "--first", "--out", doc)
        r = run(["bash", os.path.join(UPD, "sign-revocations.sh"), "--doc", doc, "--media", self.mnt,
                 "--key", os.path.join(self.mnt, "r.key"), "--keyring", self.fx.keyring,
                 "--out-dir", os.path.join(self.tmp, "rout"), "--wait-eject", "0"], env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)


@unittest.skipUnless(VERIFY_BIN, "U1 미머지 — CYS_UPDATE_VERIFY_BIN(디버그 cys) 없음: update-verify 왕복 미실행")
class TestUpdateVerifyRoundTrip(Base):
    def setUp(self):
        super().setUp()
        self.b = self.fx.body()
        self.rev = os.path.join(self.tmp, "rev.json")
        py("make-revocations.py", "--key-id", self.fx.kid("r"), "--first", "--signed-at", "1790000000", "--out", self.rev)
        fm.sign(self.fx.key("r"), self.rev, self.rev + ".minisig", "t")
        self.state = os.path.join(self.tmp, "st")
        os.makedirs(self.state)

    def envelope(self, body, name="env.json", signed_at="1790000000", **kw):
        out = os.path.join(self.tmp, name)
        r = py("make-envelope.py", "--component", "cysr", "--channel", "stable", "--release-body", body,
               "--release-sig", body + ".minisig", "--key-id", self.fx.kid("f"), "--first", "--rollout-pct", "100",
               "--halt", "false", "--signed-at", signed_at, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
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
        self.assertEqual(r.stdout.count("= apply"), 2)

    def test_mut_tampered_body(self):
        raw = bytearray(open(self.b, "rb").read())
        raw[raw.index(b"additive")] = ord("A")
        open(self.b, "wb").write(bytes(raw))
        r = self.gate(self.envelope(self.b))
        self.assertEqual(r.returncode, 1)
        self.assertIn("reject", r.stderr)

    def test_mut_expired_envelope(self):
        r = self.gate(self.envelope(self.b), now=str(1790000000 + 15 * 86400))
        self.assertEqual(r.returncode, 1)

    def test_seq_not_newer_is_uptodate(self):
        self.assertEqual(self.gate(self.envelope(self.b), expect="uptodate", installed="5").returncode, 0)

    def test_mut_feed_key_used_for_body(self):
        # 생산자(make-envelope)는 F=U 를 먼저 막는다 — 여기서는 봉투를 손으로 만들어 **검증기**의 용도 대조(ⓗ)를 잰다.
        b = json.load(open(self.b))
        b["key_id"] = self.fx.kid("f")
        open(self.b, "wb").write(uc.dump_json_bytes(b))
        fm.sign(self.fx.key("f"), self.b, self.b + ".minisig", "t")
        env = {"kind": "component-update-feed", "component": "cysr", "channel": "stable", "feed_rev": 1,
               "key_id": self.fx.kid("f"), "signed_at": 1790000000, "expires_at": 1790000000 + 86400,
               "rollout_pct": 100, "halt": False,
               "release": base64.b64encode(open(self.b, "rb").read()).decode(),
               "release_sig": base64.b64encode(open(self.b + ".minisig", "rb").read()).decode()}
        out = os.path.join(self.tmp, "hand.json")
        open(out, "wb").write(uc.dump_json_bytes(env))
        fm.sign(self.fx.key("f"), out, out + ".minisig", "t")
        r = self.gate(out)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("reject", r.stderr)


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

    def test_nsis_lock_token_hook(self):
        s = open(os.path.join(ROOT, "src-tauri", "nsis-hooks.nsh"), encoding="utf-8").read()
        i, j = s.find("⓪-a"), s.find("Global\\cys-installer")
        self.assertGreater(i, 0)
        self.assertIn("/CYSTXN=", s)
        self.assertIn("SetErrorLevel 6", s)
        self.assertLess(i, j, "⓪-a 는 ⓪ 뮤텍스 앞에 있어야 한다")


if __name__ == "__main__":
    unittest.main(verbosity=1)
