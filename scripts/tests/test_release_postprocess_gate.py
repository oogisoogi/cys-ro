"""release-postprocess.py 의 Gatekeeper 게이트 훅(F2)의 밀폐 unittest — 네트워크·토큰·실 DMG 불요.

★왜 이 테스트가 필요한가
  후처리(`scripts/release-postprocess.py`)는 **발행될 실물 바이트**(draft 백업 자산)를 만지는
  마지막 로컬 지점이다. 거기 신설된 Gatekeeper 게이트(`gatekeeper_gate`)가 fail-open 이면 —
  게이트 rc 1(FAIL)·2(판정 불가)를 통과로 세거나, macOS 밖에서 조용히 skip 하거나, main 이
  업로드 **뒤에** 게이트를 부르면 — 봉인 파손 DMG 가 그대로 --apply 되어 2026-08-01 사고
  ("손상되었기 때문에 열 수 없습니다")가 발행 층위에서 재발한다.
  **"통과해선 안 될 rc"를 여기 전부 못박는다.**

★설계
  실제 게이트 스크립트(hdiutil·spctl — macOS 전용·무겁다) 대신 **페이크 게이트**(호출을 기록
  파일에 남기고 지정 rc 로 죽는 셸 스크립트)를 주입한다. 주입 지점은 `gatekeeper_gate` 의
  테스트 전용 키워드 인자(gate_script·user_path_script·sys_platform·machine)다.
  실물 대조는 별도다 — `python3 scripts/release-postprocess.py v0.14.19`(dry-run · 백업 실물
  DMG 에 실평가). 경로는 전부 tempfile — 개인 경로·실 홈 디렉터리 금지(test_release_verify.py 관례).

★확장(2026-08-20 · codex REVISE 수리): 이 파일은 release-gate-gatekeeper.sh 의 두 계약도 박제한다.
  · F1 — SEAL-2 전칭 검사 적대 픽스처 2종(총계 상쇄·표본 밖 flags 변조 → FAIL) — 합성 트리
    (tempfile · 라이브 앱·저장소 무접촉)에 --seal2-only(진단 전용 · ⑤ 단독)로 실검증.
  · F2 — degraded(spctl 실평가 불능)=판정 불가(exit 2) 폐쇄 + 진단 플래그
    (--diagnose-degraded-ok·--seal2-only)가 발행 경로(release-postprocess.py·release.yml)에
    실리지 않는다는 문자열 핀 2건.
  · ⑦ — DMG 봉투 축(격리 사본 DMG 자체의 stapler validate + spctl --type open
    --context context:primary-signature · W-C C2 2026-09-03)의 소스 계약·음성 대조·.app 모드
    비적용·release.yml 요약 승격 4건(DmgAxisTests).

사용: python3 scripts/tests/test_release_postprocess_gate.py
"""

import contextlib
import importlib.util
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

# ★하이픈 파일명(`release-postprocess.py`)은 `import` 문으로 못 부른다 — importlib 로 직접
#   적재한다(test_release_verify.py 와 같은 이유·같은 관례).
_RP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "release-postprocess.py")
_spec = importlib.util.spec_from_file_location("release_postprocess", _RP_PATH)
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)

_HERE = os.path.dirname(os.path.abspath(__file__))
_GATE_SH = os.path.join(_HERE, "..", "release-gate-gatekeeper.sh")
_RELEASE_YML = os.path.join(_HERE, "..", "..", ".github", "workflows", "release.yml")

V = "0.14.19"


def write_app_zip(path, apps=("cysr.app",)):
    """맥 배포 zip 픽스처 — 최상위가 `.app` 디렉터리인 **실물 zip**(cysr 1.0.1 자산 형태).

    ★페이크 바이트로 못 대신한다: gatekeeper_gate 가 `ditto -x -k` 로 실제로 풀고 최상위
      `.app` 이 정확히 1개인지 센다. 그 계약을 시험이 우회하면 초록이 아무것도 증명하지 않는다.
    """
    with zipfile.ZipFile(path, "w") as z:
        if not apps:
            z.writestr("README.txt", b"no app here")
        for app in apps:
            z.writestr("%s/Contents/Info.plist" % app, b"<plist/>")
            z.writestr("%s/Contents/MacOS/cys-app" % app, b"fake-macho")


class GatekeeperGateHookTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        # ★2026-09-20 전환: 게이트 대상이 DMG → **배포 zip 속 .app** 이다. 페이크로는 안 된다 —
        #   gatekeeper_gate 가 `ditto -x -k` 로 실제로 풀고 최상위 .app 이 1개인지 세기 때문이다.
        for name in ("cysr-macos-arm64-v%s.zip" % V, "cysr-macos-x64-v%s.zip" % V):
            write_app_zip(os.path.join(self.root, name))
        self.log = os.path.join(self.root, "calls.log")

    def tearDown(self):
        self._tmp.cleanup()

    # ── 헬퍼 ──────────────────────────────────────────────────────────────
    def fake_gate(self, name, rc):
        """호출을 기록하고 지정 rc 로 끝나는 페이크 게이트를 만든다(exit 0/1/2 주입 지점)."""
        path = os.path.join(self.root, name)
        with open(path, "w") as fh:
            fh.write('#!/bin/sh\necho "%s $*" >> "%s"\nexit %d\n' % (name, self.log, rc))
        os.chmod(path, 0o755)
        return path

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as fh:
            return fh.read().splitlines()

    def run_gate(self, gate_rc=0, user_rc=0, **kw):
        kw.setdefault("sys_platform", "darwin")
        kw.setdefault("machine", "arm64")
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = rp.gatekeeper_gate(self.root, V,
                                    gate_script=self.fake_gate("gate.sh", gate_rc),
                                    user_path_script=self.fake_gate("userpath.sh", user_rc),
                                    **kw)
        return rc, err.getvalue()

    # ── 0. 기준선 ─────────────────────────────────────────────────────────
    def test_00_exit0_passes_and_covers_both_mac_zips(self):
        """이게 깨지면 정상 릴리스가 발행 불능(과차단) — 또는 배포 zip 한쪽이 무검증으로 샌다."""
        rc, _ = self.run_gate(gate_rc=0, user_rc=0)
        self.assertEqual(rc, 0)
        static_calls = [c for c in self.calls() if c.startswith("gate.sh")]
        self.assertEqual(len(static_calls), 2, "정적판이 배포 zip 2종 전부를 보지 않았다")
        for c in static_calls:
            self.assertIn("--lane self-signed", c,
                          "레인 축을 안 주면 게이트가 공증 2축을 요구해 우리 산출은 상시 FAIL 이다")
            self.assertRegex(c, r"\.app(\s|$)", "게이트 대상이 .app 이 아니다: %r" % c)

    def test_01_user_path_gate_is_not_called_and_reason_is_printed(self):
        """★무음 제거 금지 — verify-gatekeeper-user-path.sh 는 DMG 전용(hdiutil attach)이라
        이 레인의 대상이 아니다. **부르지 않되 사유를 출력에 남긴다.**"""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = rp.gatekeeper_gate(self.root, V, sys_platform="darwin", machine="arm64",
                                    gate_script=self.fake_gate("gate.sh", 0),
                                    user_path_script=self.fake_gate("userpath.sh", 0))
        self.assertEqual(rc, 0)
        self.assertEqual([c for c in self.calls() if c.startswith("userpath.sh")], [],
                         "DMG 전용 게이트를 .app 레인에서 불렀다")
        printed = out.getvalue()
        self.assertIn("verify-gatekeeper-user-path.sh", printed,
                      "부르지 않은 사실이 출력에 없다 — 조용한 제거는 fail-open 과 구별되지 않는다")
        self.assertIn("DMG 전용", printed)

    def test_02_lane_flag_is_not_silently_droppable(self):
        """레인 인자를 빼면 자체서명 산출이 공증 축에서 죽는다 — 인자 자체를 계약으로 박는다."""
        self.run_gate()
        for c in [c for c in self.calls() if c.startswith("gate.sh")]:
            self.assertIn("--lane", c)

    def test_03_native_arch_is_reported_from_host(self):
        """네이티브 아키 판정은 사라진 게 아니라 **출력으로** 남는다(호스트를 따라야 한다)."""
        for machine, token in (("arm64", "aarch64"), ("x86_64", "x64")):
            with self.subTest(machine=machine):
                self._tmp.cleanup()
                self.setUp()
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    rp.gatekeeper_gate(self.root, V, sys_platform="darwin", machine=machine,
                                       gate_script=self.fake_gate("gate.sh", 0),
                                       user_path_script=self.fake_gate("userpath.sh", 0))
                self.assertIn("네이티브 아키텍처 = %s" % token, out.getvalue())

    # ── 1. fail-closed: 통과해선 안 될 rc ─────────────────────────────────
    def test_04_gate_exit1_blocks_with_nonzero(self):
        """rc=1(FAIL)을 통과로 세면 봉인 파손 산출물이 그대로 --apply 된다."""
        rc, err = self.run_gate(gate_rc=1)
        self.assertEqual(rc, 1)
        self.assertIn("::error::", err)

    def test_05_gate_exit2_blocks_identically(self):
        """rc=2(판정 불가)를 통과로 세면 '측정 불능=통과' 구멍 — 1과 똑같이 죽어야 한다."""
        rc, err = self.run_gate(gate_rc=2)
        self.assertEqual(rc, 2)
        self.assertIn("::error::", err)

    def test_06_user_path_rc_cannot_affect_verdict(self):
        """DMG 전용 게이트를 안 부르므로 그 rc 는 판정에 **닿지 않는다**(호출 0이 근거)."""
        rc, _ = self.run_gate(gate_rc=0, user_rc=1)
        self.assertEqual(rc, 0)
        self.assertEqual([c for c in self.calls() if c.startswith("userpath.sh")], [])

    def test_07_non_macos_is_fail_closed_not_skip(self):
        """macOS 밖 무음 skip = 무검증 발행. 판정 불가(비영)로 죽고, 게이트를 돌린
        척(호출 기록)도 남기면 안 된다."""
        rc, err = self.run_gate(sys_platform="linux")
        self.assertEqual(rc, 2)
        self.assertIn("::error::", err)
        self.assertEqual(self.calls(), [])

    def test_08_missing_mac_zip_is_fail_closed(self):
        """대상 배포 zip 부재를 통과로 세면 '자산이 없어서 검사를 못 한 묶음'이 발행된다."""
        os.remove(os.path.join(self.root, "cysr-macos-x64-v%s.zip" % V))
        rc, err = self.run_gate()
        self.assertEqual(rc, 2)
        self.assertIn("::error::", err)

    def test_08b_unextractable_zip_is_undecidable_not_pass(self):
        """풀리지 않는 zip = 측정 불능. skip 도 통과도 아니다."""
        with open(os.path.join(self.root, "cysr-macos-x64-v%s.zip" % V), "wb") as fh:
            fh.write(b"PK\x03\x04not-a-real-zip")
        rc, err = self.run_gate()
        self.assertEqual(rc, 2)
        self.assertIn("::error::", err)

    def test_08c_zip_without_exactly_one_app_is_undecidable(self):
        """최상위 .app 이 0개거나 2개면 **무엇을 쟀는지 알 수 없다** — 아무거나 고르지 않는다."""
        for apps in ([], ["cysr.app", "other.app"]):
            with self.subTest(apps=apps):
                self._tmp.cleanup()
                self.setUp()
                write_app_zip(os.path.join(self.root, "cysr-macos-x64-v%s.zip" % V), apps=apps)
                rc, err = self.run_gate()
                self.assertEqual(rc, 2)
                self.assertIn("::error::", err)

    # ── 2. 비상 탈출구 ────────────────────────────────────────────────────
    def test_09_unsafe_skip_opens_loudly_and_runs_nothing(self):
        """탈출구는 열리되 **조용히** 열리면 안 된다 — LOUD 경고 2줄이 사라지면
        평시 우회 플래그로 변질된다(--force-no-verify 선례 동형)."""
        rc, err = self.run_gate(unsafe_skip=True)
        self.assertEqual(rc, 0)
        self.assertEqual(self.calls(), [])
        loud = [ln for ln in err.splitlines() if ln.startswith("!!!!")]
        self.assertGreaterEqual(len(loud), 2, "LOUD 경고 2줄 계약 위반: %r" % err)


class MacAbsentBundleTests(unittest.TestCase):
    """★2026-09-09 신설 — 「맥 미포함 묶음」 skip 이 **정확히 하나의 문**만 여는지 못박는다.

    이 분기는 발행 게이트를 건너뛰는 유일한 비-LOUD 경로다. 그래서 여기서 물어야 할 것은
    "통과하는가"가 아니라 **"통과하지 말아야 할 이웃 상태들이 전부 죽는가"** 다:
      · 근거(latest.json)가 없는 0종 묶음      → 판정 불가
      · latest.json 이 darwin 을 주장하는 0종  → 판정 불가(없는 파일을 받으러 가는 묶음)
      · DMG 가 한 짝만 있는 반쪽 묶음          → 판정 불가(종전 경로 그대로)
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.log = os.path.join(self.root, "calls.log")

    def tearDown(self):
        self._tmp.cleanup()

    def fake_gate(self, name, rc=0):
        path = os.path.join(self.root, name)
        with open(path, "w") as fh:
            fh.write('#!/bin/sh\necho "%s $*" >> "%s"\nexit %d\n' % (name, self.log, rc))
        os.chmod(path, 0o755)
        return path

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as fh:
            return fh.read().splitlines()

    def write_latest(self, platform_keys):
        obj = {"version": V, "notes": "n", "pub_date": "2026-09-09T00:00:00Z",
               "platforms": {k: {"signature": "s", "url": "u"} for k in platform_keys}}
        with open(os.path.join(self.root, "latest.json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh)

    def add_mac_zip(self, arch):
        """맥 레인의 다운로드 자산 = 배포 zip (2026-09-20 · TICKET=v110-mac-lane 전환 후).

        ★`mac_lane_absent()` 는 `MAC_LANE` 이름으로만 존재를 센다 — 그 목록 밖 자산(예 DMG)을
          아무리 넣어도 「맥 포함」이 되지 않는다. 이 헬퍼가 그 목록 안의 이름을 만든다.
        """
        name = {"aarch64": "cysr-macos-arm64-v%s.zip" % V,
                "x64": "cysr-macos-x64-v%s.zip" % V}[arch]
        # 실물 zip 이어야 한다 — 게이트가 ditto 로 풀어 최상위 .app 을 센다(write_app_zip 주석).
        write_app_zip(os.path.join(self.root, name))

    def run_gate(self, **kw):
        kw.setdefault("sys_platform", "darwin")
        kw.setdefault("machine", "arm64")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = rp.gatekeeper_gate(self.root, V,
                                    gate_script=self.fake_gate("gate.sh"),
                                    user_path_script=self.fake_gate("userpath.sh"), **kw)
        return rc, out.getvalue(), err.getvalue()

    # ── 여는 문 하나 ──────────────────────────────────────────────────────
    def test_30_windows_only_bundle_skips_with_stated_reason(self):
        """맥 0종 + darwin 행 0 = 대상 없음. 게이트는 **돌지도 않아야** 한다(척도 남기기 금지)."""
        self.write_latest(["windows-x86_64", "windows-x86_64-nsis"])
        rc, out, _ = self.run_gate()
        self.assertEqual(rc, 0)
        self.assertEqual(self.calls(), [], "평가할 대상이 없는데 게이트를 돌린 기록이 남았다")
        self.assertIn("맥 미포함", out)
        self.assertIn("윈도우 단독", out)

    def test_31_skip_holds_off_macos_too(self):
        """맥 바이트가 0종이면 어느 OS 에서 돌리든 답이 같다 — 리눅스 러너에서도 대상 없음."""
        self.write_latest(["windows-x86_64", "windows-x86_64-nsis"])
        rc, _, _ = self.run_gate(sys_platform="linux")
        self.assertEqual(rc, 0)

    # ── 죽어야 할 이웃 상태들 ─────────────────────────────────────────────
    def test_32_no_latest_json_is_not_a_declaration(self):
        """latest.json 이 없으면 「미포함」을 확인할 근거가 없다 — 통과로 접지 않는다."""
        rc, _, err = self.run_gate()
        self.assertEqual(rc, 2)
        self.assertIn("::error::", err)
        self.assertEqual(self.calls(), [])

    def test_33_darwin_rows_without_mac_assets_is_fail_closed(self):
        """latest.json 은 맥을 주장하는데 맥 자산이 0종 = 맥 사용자가 없는 파일을 받으러 간다."""
        self.write_latest(["windows-x86_64", "windows-x86_64-nsis",
                           "darwin-aarch64", "darwin-aarch64-app",
                           "darwin-x86_64", "darwin-x86_64-app"])
        rc, _, err = self.run_gate()
        self.assertEqual(rc, 2)
        self.assertIn("::error::", err)

    def test_34_half_mac_lane_still_fail_closed(self):
        """배포 zip 한 짝만 있는 묶음은 skip 대상이 아니다 — 종전 경로에서 그대로 죽는다."""
        self.add_mac_zip("aarch64")
        self.write_latest(["windows-x86_64", "windows-x86_64-nsis"])
        rc, _, err = self.run_gate()
        self.assertEqual(rc, 2)
        self.assertIn("::error::", err)

    def test_35_updater_tarball_alone_blocks_skip(self):
        """배포 zip 은 없고 맥 업데이터 tar 만 남은 묶음도 「미포함」이 아니다."""
        with open(os.path.join(self.root, "cysr_aarch64.app.tar.gz"), "wb") as fh:
            fh.write(b"\x1f\x8bfake")
        self.write_latest(["windows-x86_64", "windows-x86_64-nsis"])
        rc, _, _ = self.run_gate()
        self.assertEqual(rc, 2)

    def test_36_full_mac_bundle_still_gated(self):
        """맥이 전부 있는 묶음은 종전과 똑같이 **게이트 필수** — 완화가 새지 않았는지 본다."""
        for arch in ("aarch64", "x64"):
            self.add_mac_zip(arch)
        for n in ("cysr_aarch64.app.tar.gz", "cysr_aarch64.app.tar.gz.sig",
                  "cysr_x64.app.tar.gz", "cysr_x64.app.tar.gz.sig"):
            with open(os.path.join(self.root, n), "wb") as fh:
                fh.write(b"x")
        self.write_latest(["windows-x86_64", "windows-x86_64-nsis",
                           "darwin-aarch64", "darwin-aarch64-app",
                           "darwin-x86_64", "darwin-x86_64-app"])
        rc, _, _ = self.run_gate()
        self.assertEqual(rc, 0)
        self.assertEqual(len([c for c in self.calls() if c.startswith("gate.sh")]), 2,
                         "맥 포함 묶음인데 정적 게이트가 배포 zip 2종을 보지 않았다")


class ReleaseRepoPinTests(unittest.TestCase):
    """배포 원본 레포 = 우리 포크. `release-verify.py` 와 **같은 값**이어야 한다 —
    두 스크립트가 갈리면 후처리가 만든 묶음을 검증기가 죽인다(또는 그 반대)."""

    def test_37_default_repo_is_our_fork(self):
        self.assertEqual(rp.RELEASE_REPO, "oogisoogi/cys-ro")

    def test_38_matches_release_verify(self):
        rv_path = os.path.join(_HERE, "..", "release-verify.py")
        spec = importlib.util.spec_from_file_location("release_verify_pin", rv_path)
        rv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rv)
        self.assertEqual(rp.RELEASE_REPO, rv.RELEASE_REPO,
                         "후처리와 검증기의 배포 원본이 갈렸다")

    def test_39_mac_lane_matches_release_verify(self):
        """맥 레인 목록도 두 파일이 같아야 한다(주석이 아니라 검사로 묶는다)."""
        rv_path = os.path.join(_HERE, "..", "release-verify.py")
        spec = importlib.util.spec_from_file_location("release_verify_pin2", rv_path)
        rv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rv)
        self.assertEqual(sorted(n.format(v=V) for n in rp.MAC_LANE),
                         rv.mac_lane_files(V),
                         "후처리 MAC_LANE 과 검증기 mac_lane_files() 가 갈렸다")


class MainWiringContractTests(unittest.TestCase):
    """main() 배선 계약 — 함수가 아무리 옳아도 main 이 안 부르거나(또는 업로드 뒤에 부르면)
    게이트는 장식이다. main 은 token()이 필요해 밀폐 실행이 불가하므로 원문으로 박제한다
    (javis_cycle_verifier.py 의 소스 계약 검사 관례)."""

    def setUp(self):
        with open(_RP_PATH, encoding="utf-8") as fh:
            self.src = fh.read()

    def test_10_gate_called_after_selfverify_and_before_upload(self):
        call = self.src.index("gate_rc = gatekeeper_gate(")
        selfverify = self.src.index("자기 검증 통과")
        upload = self.src.index("── 6. 업로드")
        self.assertGreater(call, selfverify, "게이트가 자기 검증(4단계)보다 앞이다")
        self.assertLess(call, upload, "게이트가 업로드 뒤다 — --apply 를 못 막는다")

    def test_11_unsafe_flag_parsed_from_argv_default_off(self):
        self.assertIn('"--unsafe-skip-gatekeeper" in argv', self.src)

    def test_12_gate_return_value_terminates_main(self):
        """반환값을 버리면(호출만 하면) 비영 rc 가 통과로 둔갑한다."""
        self.assertIn("if gate_rc:\n        return gate_rc", self.src)

    def test_12b_mac_dist_zips_required_when_mac_lane_present(self):
        """맥 배포 zip 2종(설치기가 실제로 받는 자산)이 **누락 검사에 실려 있는가**.

        ★이 두 줄이 없던 동안 v1.0.2 는 인텔용 zip 이 **아예 없는 채로** 발행됐고, 어떤 게이트도
          그것을 말하지 않았다(인텔 맥은 설치기가 원작자 판으로 갈라졌다 — 2026-09-20 전환의 계기).
        main 은 토큰이 필요해 밀폐 실행이 불가하므로 위 test_10~12 와 같은 소스 계약으로 박는다.
        """
        self.assertEqual(rp.MAC_DIST_ZIPS,
                         ("cysr-macos-arm64-v{v}.zip", "cysr-macos-x64-v{v}.zip"),
                         "맥 배포 zip 이름이 바뀌었다 — 설치기 핀(CYS_FORK_FILE·CYS_FORK_X64_FILE)과 함께 봐야 한다")
        # 맥 레인이 있는 묶음에서만 요구한다(윈도우 단독 묶음은 종전대로 통과) — 그 조건 안에 있는지까지 본다.
        block = self.src[self.src.index("win_only = mac_lane_absent("):self.src.index("missing = [w for w in want")]
        self.assertIn("if not win_only:", block)
        self.assertIn("want = [n.format(v=version) for n in MAC_DIST_ZIPS] + want",
                      block.split("if not win_only:", 1)[1],
                      "배포 zip 요구가 맥 레인 조건 안에 없다 — 윈도우 단독 발행이 막히거나(위) 인텔 누락이 조용하다(아래)")


class DiagnoseFlagAbsencePins(unittest.TestCase):
    """F2 핀 — 진단 전용 플래그(--diagnose-degraded-ok·--seal2-only)가 발행 경로에 실리는
    순간 빨개진다. 게이트 스크립트가 아무리 옳아도 발행 경로가 진단 플래그를 실으면
    degraded 가 도로 rc=0 이 된다 — 문자열 층위에서 못박는다(F2 수리 2026-08-20)."""

    DIAG_FLAGS = ("--diagnose-degraded-ok", "--seal2-only")

    def test_13_postprocess_source_carries_no_diagnose_flag(self):
        with open(_RP_PATH, encoding="utf-8") as fh:
            src = fh.read()
        for flag in self.DIAG_FLAGS:
            self.assertNotIn(flag, src,
                             "release-postprocess.py 가 진단 전용 플래그를 실었다: %s" % flag)

    def test_14_release_yml_carries_no_diagnose_flag(self):
        with open(_RELEASE_YML, encoding="utf-8") as fh:
            yml = fh.read()
        # 핀의 전제: 게이트 스텝 실재 — 스텝 자체가 사라지면 플래그 부재 단언은 공허하다.
        self.assertIn("release-gate-gatekeeper.sh", yml,
                      "게이트 스텝이 release.yml 에서 사라졌다 — 무검증 발행 경로")
        for flag in self.DIAG_FLAGS:
            self.assertNotIn(flag, yml,
                             "release.yml 이 진단 전용 플래그를 실었다: %s" % flag)


class Seal2UniversalCheckTests(unittest.TestCase):
    """F1 적대 픽스처 — SEAL-2 전칭 검사(파일별 대응·고아·flags 전수)를 합성 트리로 박제.

    구판(레벨별 총계 동일성 + 표본 25개 flags)이 통과시키던 두 결함을 FAIL 로 못박는다:
      (a) 결손 1 + 동수 고아 1 = 총계 상쇄   (b) 구판 표본 밖 1개 flags 변조.
    트리는 tempfile 합성(라이브 앱·저장소 무접촉) — 검사는 파일명 + 헤더 8바이트만 보므로
    pyc 본문은 위조로 충분하다. 호출은 --seal2-only(⑤ 단독 · hdiutil/spctl 불요)."""

    TAG = "cpython-312"   # 픽스처 안 태그 — 게이트는 이 값을 하드코딩하지 않고 파일명에서 추출한다

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.app = os.path.join(self._tmp.name, "Fake.app")
        self.pkg = os.path.join(self.app, "Contents", "Resources", "runtime",
                                "python", "lib", "pkg")
        self.cache = os.path.join(self.pkg, "__pycache__")
        os.makedirs(self.cache)
        # 3N > 25(구판 표본 상한) — "표본 밖" 변조 지점이 실제로 존재하도록 N=12(pyc 36개).
        for i in range(12):
            with open(os.path.join(self.pkg, "m%02d.py" % i), "w") as fh:
                fh.write("x = %d\n" % i)
            for opt in ("", ".opt-1", ".opt-2"):
                self._pyc(os.path.join(self.cache, "m%02d.%s%s.pyc" % (i, self.TAG, opt)))

    def tearDown(self):
        self._tmp.cleanup()

    def _pyc(self, path, flags=1):
        with open(path, "wb") as fh:
            fh.write(b"\x6f\x0d\x0d\x0a")          # magic 4B — 게이트는 값 대조를 안 한다(버전 무관)
            fh.write(struct.pack("<I", flags))     # flags 4B (PEP 552 · 1 = unchecked-hash)
            fh.write(b"\x00" * 8)                  # source-hash 8B — 내용 무관

    def _run(self):
        p = subprocess.run(["bash", _GATE_SH, "--seal2-only", self.app],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def test_15_baseline_synthetic_tree_passes(self):
        """기준선 rc=0 — 이게 깨지면 아래 FAIL 단언들은 '무조건 빨간 검사'를 오독한 것이다."""
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        self.assertIn("OK:", out)

    def test_16_missing_plus_orphan_cancellation_fails(self):
        """(a) 한 소스의 pyc 1종 삭제 + 동수 고아 추가 — 레벨별 총계가 그대로라 구판은 초록."""
        os.remove(os.path.join(self.cache, "m00.%s.opt-2.pyc" % self.TAG))
        self._pyc(os.path.join(self.cache, "ghost.%s.opt-2.pyc" % self.TAG))  # 소스 없는 고아
        rc, out = self._run()
        self.assertEqual(rc, 1, out)
        self.assertIn("MISSING", out)
        self.assertIn("ORPHAN", out)

    def test_17_out_of_sample_flags_tamper_fails(self):
        """(b) 구판 표본(정렬 선두 25개) 밖의 1개를 flags=3 으로 변조 — 전수 판독만 잡는다."""
        victim = sorted(os.listdir(self.cache))[-1]   # 정렬 마지막 = 36개 중 36번째 — 구판 [:25] 밖
        self._pyc(os.path.join(self.cache, victim), flags=3)
        rc, out = self._run()
        self.assertEqual(rc, 1, out)
        self.assertIn("BADFLAGS", out)


@unittest.skipUnless(sys.platform == "darwin",
                     "게이트 전체 실행은 macOS 도구(hdiutil·spctl 등)가 필요하다")
class DegradedClosureTests(unittest.TestCase):
    """F2 — degraded(spctl 실평가 불능)는 기본 모드에서 판정 불가(exit 2)로 폐쇄된다.
    주입점 CYS_GATE_FORCE_DEGRADED=1 은 degraded **방향으로만** 강제한다(full 을 강제하는
    주입점은 우회 벡터라 없다)."""

    def _mini_app(self, root):
        pkg = os.path.join(root, "Fake.app", "Contents", "Resources", "runtime",
                           "python", "lib", "pkg")
        cache = os.path.join(pkg, "__pycache__")
        os.makedirs(cache)
        with open(os.path.join(pkg, "a.py"), "w") as fh:
            fh.write("x = 1\n")
        for opt in ("", ".opt-1", ".opt-2"):
            with open(os.path.join(cache, "a.cpython-312%s.pyc" % opt), "wb") as fh:
                fh.write(b"\x6f\x0d\x0d\x0a" + struct.pack("<I", 1) + b"\x00" * 8)
        return os.path.join(root, "Fake.app")

    def test_18_degraded_closes_exit2_with_gate_mode_line(self):
        env = dict(os.environ, CYS_GATE_FORCE_DEGRADED="1")
        p = subprocess.run(["bash", _GATE_SH, "/nonexistent-target.dmg"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        # 폐쇄 직전 GATE_MODE=degraded 를 stdout 마지막 줄로 출력한다(헤더 GATE_MODE 계약).
        lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
        self.assertEqual(lines[-1], "GATE_MODE=degraded", p.stdout)
        # 폐쇄는 대상 평가 이전이다 — 개별 검사(①-⑤)가 하나도 돌지 않아야 한다.
        self.assertNotIn("── 대상 앱", p.stdout)

    def test_19_diagnose_flag_keeps_degraded_open_with_loud_notice(self):
        """진단 옵트인은 폐쇄를 열되(판정 도달 exit 0·1) LOUD 고지를 남긴다 — 가짜 앱은
        codesign 에서 FAIL 이므로 판정 도달 = exit 1 + GATE_MODE=degraded 마지막 줄."""
        with tempfile.TemporaryDirectory() as td:
            app = self._mini_app(td)
            env = dict(os.environ, CYS_GATE_FORCE_DEGRADED="1")
            p = subprocess.run(["bash", _GATE_SH, "--diagnose-degraded-ok", app],
                               capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)   # 판정 도달(폐쇄 아님)
        lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
        self.assertEqual(lines[-1], "GATE_MODE=degraded", p.stdout)
        loud = [ln for ln in p.stdout.splitlines() if ln.startswith("!!!!")]
        self.assertGreaterEqual(len(loud), 2, "LOUD 고지 2줄 계약 위반: %r" % p.stdout)


class DmgAxisTests(unittest.TestCase):
    """⑦ DMG 봉투 축 — 격리 사본 **DMG 자신**의 공증 티켓·Gatekeeper 열기 평가 (W-C C2 · 2026-09-03).

    ★왜 이 축이 필요한가: ①~⑥ 은 DMG **안의 앱**만 평가한다. 그런데 사용자가 브라우저로 받은
      격리 DMG 를 여는 순간 Gatekeeper 가 보는 것은 DMG 자신의 서명·staple 이다 — 봉투가
      빠지거나 깨지면 앱이 온전해도 열리지 않는다. 그 계급을 이 축이 본다.
    ★여기서 못박는 것: (a) 소스 계약(라벨 문자열 + 호출 위치가 ① 부착 뒤·마운트 앞)
      (b) 음성 대조 — 미서명·미공증 합성 DMG 는 두 검사 모두 FAIL 이고 게이트가 비영 종료한다
      (c) `.app` 직접 지정 모드에서는 PASS 를 만들지 않고 "대상 아님" 으로만 남는다
      (d) release.yml 이 ⑦ 라인을 요약으로 승격한다.
    ★(b)(c) 는 macOS 도구(hdiutil·spctl·codesign)를 요구해 darwin 한정이고, (a)(d) 는
      소스 문자열 검사라 플랫폼 무관이다 — 그래서 클래스 단위 skip 을 걸지 않고 메서드별로 건다
      (플랫폼 무관 핀이 macOS 밖 레인에서 조용히 사라지지 않게).
    """

    # ⑦ 라벨 — 게이트 스크립트와 **글자 단위로** 같아야 한다(release.yml 승격 grep 도 이 형식을 본다).
    A_LABEL = "⑦-a stapler validate(DMG)"
    B_LABEL = "⑦-b spctl --assess --type open --context context:primary-signature(DMG)"
    APP_MODE_INFO = "⑦ DMG 축: .app 직접 지정 모드 — 대상 아님(DMG 없음)"

    @staticmethod
    def _gate_src():
        with open(_GATE_SH, encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _fake_app_tree(root):
        """실행 가능 바이너리만 가진 최소 .app — 서명·공증이 없다(음성 대조의 재료)."""
        macos = os.path.join(root, "Fake.app", "Contents", "MacOS")
        os.makedirs(macos)
        exe = os.path.join(macos, "fake")
        with open(exe, "w") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(exe, 0o755)
        return os.path.join(root, "Fake.app")

    @staticmethod
    def _mini_python_app(root):
        """SEAL-2(⑤)를 통과하는 합성 .app — DegradedClosureTests._mini_app 과 동형 픽스처."""
        pkg = os.path.join(root, "Fake.app", "Contents", "Resources", "runtime",
                           "python", "lib", "pkg")
        cache = os.path.join(pkg, "__pycache__")
        os.makedirs(cache)
        with open(os.path.join(pkg, "a.py"), "w") as fh:
            fh.write("x = 1\n")
        for opt in ("", ".opt-1", ".opt-2"):
            with open(os.path.join(cache, "a.cpython-312%s.pyc" % opt), "wb") as fh:
                fh.write(b"\x6f\x0d\x0d\x0a" + struct.pack("<I", 1) + b"\x00" * 8)
        return os.path.join(root, "Fake.app")

    def _run_gate(self, target):
        p = subprocess.run(["bash", _GATE_SH, target], capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    # ── (a) 소스 계약 — 플랫폼 무관 ────────────────────────────────────────
    def test_20_dmg_axis_source_pins(self):
        """라벨이 바뀌거나 호출이 마운트 뒤로 밀리면 이 핀이 빨개진다.

        위치가 계약인 이유: ⑦ 은 **격리 속성이 붙은 사본**을 평가해야 하고(부착 전이면 격리
        경로가 아니다), 마운트 뒤로 밀면 봉투가 깨진 DMG 가 attach 단계에서 먼저 죽어 어느
        검사도 그 사실을 이름으로 지목하지 못한다.
        """
        src = self._gate_src()
        for token in (self.A_LABEL, self.B_LABEL, self.APP_MODE_INFO,
                      'xcrun stapler validate "$DMG"',
                      "--context context:primary-signature"):
            self.assertIn(token, src, "⑦ 계약 문자열 부재: %r" % token)
        i_quarantine = src.index('ok "① quarantine 부착(DMG)"')
        i_axis = src.index('xcrun stapler validate "$DMG"')
        i_attach = src.index('hdiutil attach "$DMG"')
        self.assertLess(i_quarantine, i_axis, "⑦ 가 ① quarantine 부착보다 앞이다")
        self.assertLess(i_axis, i_attach, "⑦ 가 hdiutil attach 뒤로 밀렸다")
        # ⑦-b 는 ④ 와 같은 관례로 full 모드에서만 돈다(측정 불능을 통과로 세지 않는다).
        self.assertIn('if [ "$MODE" = "full" ]', src)
        # ★기본(발행) 모드의 degraded 는 F2 폐쇄(exit 2)가 ⑦ 보다 앞이라 ⑦ 이 실행되지 않는다.
        #   그 순서가 뒤집히면 fail-closed 이전에 ⑦ 가 도는 동작 회귀다 — 위 quarantine·attach
        #   순서 핀과 같은 계급이라 여기서 잡는다.
        #   (주석 문구 자체를 매칭하던 단언은 2026-09-04 오너 지시 §4 '텍스트 매칭 게이트 신설
        #    금지'에 따라 제거했다 — 게이트는 시스템의 실제 동작을 재는 것만 둔다.)
        i_f2_close = src.index("✗ degraded(spctl assessments disabled)")
        self.assertLess(i_f2_close, i_axis, "F2 degraded 폐쇄가 ⑦ 뒤로 밀렸다")

    # ── (b) 음성 대조 — darwin 한정 ───────────────────────────────────────
    @unittest.skipUnless(sys.platform == "darwin",
                         "합성 DMG 생성·평가는 macOS 도구(hdiutil·spctl)를 요구한다")
    def test_21_unsigned_dmg_fails_dmg_axis(self):
        """미서명·미공증 DMG 가 ⑦ 에서 FAIL 하고 게이트가 비영 종료한다.

        이 음성 대조가 없으면 ⑦ 은 '항상 초록인 검사'일 수 있다(vacuous pass).
        종료 코드는 1(FAIL) 또는 2(판정 불가)를 모두 허용한다 — 합성 DMG 에는 동봉 python
        런타임이 없어 ⑤ SEAL-2 가 대상 0으로 폐쇄(2)되는 경로가 정상이기 때문이다.
        어느 쪽이든 **0 이 아니어야** 한다(업로드 금지).
        """
        with tempfile.TemporaryDirectory() as td:
            src_dir = os.path.join(td, "src")
            os.makedirs(src_dir)
            self._fake_app_tree(src_dir)
            dmg = os.path.join(td, "fake-unsigned.dmg")
            mk = subprocess.run(["hdiutil", "create", "-volname", "FakeNeg",
                                 "-srcfolder", src_dir, "-ov", "-format", "UDZO", dmg],
                                capture_output=True, text=True)
            if mk.returncode != 0 or not os.path.exists(dmg):
                # 측정 불능은 통과가 아니다 — 그러나 밀폐 테스트가 러너 환경 문제로 CI 를
                # 세우는 것도 옳지 않으므로 사유를 남기고 skip 한다(판정은 실물 게이트 실행이 진다).
                self.skipTest("hdiutil create 실패 — 합성 DMG 없음: %s"
                              % (mk.stderr or mk.stdout).strip()[:200])
            rc, out = self._run_gate(dmg)
            self.assertIn("FAIL " + self.A_LABEL, out, out[-2000:])
            self.assertIn("FAIL " + self.B_LABEL, out, out[-2000:])
            self.assertNotEqual(rc, 0, "미서명 DMG 가 통과했다(rc=0)\n%s" % out[-2000:])
            self.assertIn(rc, (1, 2), "예상 밖 종료 코드 rc=%d\n%s" % (rc, out[-2000:]))

    # ── (c) .app 모드 비적용 — darwin 한정 ────────────────────────────────
    @unittest.skipUnless(sys.platform == "darwin",
                         "게이트 전체 실행은 macOS 도구(codesign·spctl 등)를 요구한다")
    def test_22_app_mode_marks_dmg_axis_not_applicable(self):
        """`.app` 직접 지정 모드에서 ⑦ 은 '대상 아님' info 로만 남고 PASS 를 만들지 않는다.

        PASS 를 만들면 DMG 봉투를 **평가하지 않은 실행**이 봉투 통과로 집계돼, 로컬 스모크가
        발행 승인 신호를 위조하게 된다(측정 불능 ≠ 통과).
        """
        with tempfile.TemporaryDirectory() as td:
            app = self._mini_python_app(td)
            rc, out = self._run_gate(app)
            self.assertIn(self.APP_MODE_INFO, out, out[-2000:])
            axis_pass = [ln for ln in out.splitlines() if ln.startswith("PASS ⑦")]
            self.assertEqual(axis_pass, [], "app 모드에서 ⑦ PASS 가 났다: %r" % axis_pass)
            # 합성 앱은 서명·공증이 없어 ②③(④)이 FAIL 이다 — 판정에 도달했음을 함께 확인한다
            # (게이트가 ⑦ info 만 찍고 조용히 성공하는 경로가 없어야 한다).
            self.assertNotEqual(rc, 0, out[-2000:])

    # ── (d) CI 승격 배선 — 플랫폼 무관 ────────────────────────────────────
    def test_23_release_yml_promotes_dmg_axis_lines(self):
        """release.yml 이 ⑦ 라인을 GITHUB_STEP_SUMMARY 로 승격한다(+ 진단 플래그 부재 유지).

        승격이 없으면 ⑦ 의 FAIL·미출력이 20분짜리 로그 안에만 남아 라운드 감사에서 묻힌다
        (GATE_MODE 승격을 넣은 F1 검증 공백 수리와 같은 근거).
        """
        with open(_RELEASE_YML, encoding="utf-8") as fh:
            yml = fh.read()
        # 핀의 전제: 게이트 스텝 실재(스텝이 사라지면 승격 단언은 공허하다 — test_14 관례).
        self.assertIn("release-gate-gatekeeper.sh", yml,
                      "게이트 스텝이 release.yml 에서 사라졌다 — 무검증 발행 경로")
        # 승격 grep 은 게이트 스크립트가 내는 라벨 형식(^PASS/FAIL + ⑦)과 결박된다.
        needle = 'grep -E \'^(PASS|FAIL) ⑦\' "$GLOG"'
        self.assertIn(needle, yml, '⑦ 라인 요약 승격 배선이 없다')
        for flag in DiagnoseFlagAbsencePins.DIAG_FLAGS:
            self.assertNotIn(flag, yml,
                             "release.yml 이 진단 전용 플래그를 실었다: %s" % flag)


class LaneAxisTests(unittest.TestCase):
    """레인 축 — 공증 2축(③ stapler · ④ spctl)의 적용 여부 (2026-09-20 · TICKET=v110-mac-lane).

    ★왜 이 축이 생겼나: 이 게이트는 **공증 레인 전용으로 태어났다**. 우리 포크의 맥 산출은
      cys-local 자체서명(공증 없음)이라 ③④ 가 원리적으로 성립하지 않는다. 그대로 두면 게이트가
      상시 적색이 되어 결국 우회되고, 조용히 빼면 무음 fail-open 이다. 그래서 **이름 붙여 가르고
      SKIP 으로 센다**.
    ★여기서 못박는 것:
      (a) 소스 계약 — SKIP 이 계수·인쇄되고, 판별기가 값을 stdout 으로 돌려주지 않는다.
      (b) 동작 — self-signed 레인은 ③④ 를 SKIP(사유 동반)하고 PASS 로 세지 않는다.
      (c) 뮤턴트 — 같은 자체서명 앱을 notarized 레인으로 강제하면 ③④ 가 FAIL 로 죽는다
          (= 이 두 축이 '항상 초록인 검사'가 아님을 음성 대조로 증명).
      (d) fail-closed — 판별 불가(서명 없음)는 관용이 아니라 **엄격한 쪽(notarized)** 으로 접는다.
    """

    @staticmethod
    def _gate_src():
        with open(_GATE_SH, encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _mini_app(root, adhoc_sign):
        """⑤ SEAL-2 를 통과하는 합성 .app. adhoc_sign=True 면 **임시(ad-hoc) 서명**을 붙인다.

        ad-hoc 서명은 `Authority=` 권위 사슬이 없다 — 즉 우리 cys-local 자체서명과 **같은 축**에
        떨어진다(Developer ID 아님). 그래서 레인 판별의 재료로 쓸 수 있다.
        """
        app = os.path.join(root, "Fake.app")
        pkg = os.path.join(app, "Contents", "Resources", "runtime", "python", "lib", "pkg")
        cache = os.path.join(pkg, "__pycache__")
        macos = os.path.join(app, "Contents", "MacOS")
        os.makedirs(cache)
        os.makedirs(macos)
        # ★번들 골격(Info.plist + 주 실행파일)이 없으면 codesign 이 'bundle format unrecognized'
        #   로 거절한다(실측) — 서명 픽스처는 형태를 갖춰야 재료가 된다.
        with open(os.path.join(app, "Contents", "Info.plist"), "w", encoding="utf-8") as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                     '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                     '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                     '<plist version="1.0"><dict>\n'
                     '<key>CFBundleExecutable</key><string>fake</string>\n'
                     '<key>CFBundleIdentifier</key><string>com.example.fake</string>\n'
                     '<key>CFBundleName</key><string>Fake</string>\n'
                     '<key>CFBundlePackageType</key><string>APPL</string>\n'
                     '<key>CFBundleShortVersionString</key><string>1.0</string>\n'
                     '</dict></plist>\n')
        exe = os.path.join(macos, "fake")
        with open(exe, "w") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(exe, 0o755)
        with open(os.path.join(pkg, "a.py"), "w") as fh:
            fh.write("x = 1\n")
        for opt in ("", ".opt-1", ".opt-2"):
            with open(os.path.join(cache, "a.cpython-312%s.pyc" % opt), "wb") as fh:
                fh.write(b"\x6f\x0d\x0d\x0a" + struct.pack("<I", 1) + b"\x00" * 8)
        if adhoc_sign:
            # ad-hoc(-s -) 서명은 Authority= 권위 사슬이 없다 = 우리 cys-local 자체서명과 같은 축.
            p = subprocess.run(["codesign", "-s", "-", "--force", app],
                               capture_output=True, text=True)
            if p.returncode != 0:      # 측정 재료를 못 만들면 그 시험은 공허하다 — 조용히 넘기지 않는다
                raise unittest.SkipTest("ad-hoc 서명 실패: %s" % (p.stderr or p.stdout).strip()[:200])
        return app

    @staticmethod
    def _run(target, *args):
        p = subprocess.run(["bash", _GATE_SH, *args, target], capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    # ── (a) 소스 계약 — 플랫폼 무관 ────────────────────────────────────────
    def test_50_skip_is_counted_and_printed(self):
        """★'무음 제외' 로 바꾸면 여기서 죽는다 — SKIP 은 세어지고 인쇄돼야 한다.

        이 단언이 없으면 누군가 `skipped()` 를 no-op 으로 만들어도 스위트가 전부 초록이고,
        판정 줄에는 「전 항목 PASS」만 남는다(= 안 돈 축이 통과로 둔갑).
        """
        src = self._gate_src()
        self.assertIn("SKIP_N=$((SKIP_N+1))", src, "SKIP 계수기가 사라졌다")
        self.assertIn("printf 'SKIP %s | %s\\n'", src, "SKIP 인쇄가 사라졌다")
        self.assertIn('echo "PASS=$PASS_N · FAIL=$FAIL_N · SKIP=$SKIP_N"', src,
                      "판정 줄에서 SKIP 계수가 빠졌다")
        self.assertIn("GATE_SKIPPED=$SKIP_N", src, "기계 요약에서 SKIP 계수가 빠졌다")
        # 제외에는 사유가 붙어야 한다 — 사유 없는 skip 은 미탐과 구별되지 않는다.
        for axis in ("③ stapler validate", "④ spctl --assess --type execute"):
            i = src.index('skipped "%s($APP_NAME)"' % axis)
            line = src[i:src.index("\n", i)]
            self.assertIn("자체서명 레인 = 대상 아님", line, "제외 사유가 없다: %r" % line)

    def test_51_detect_lane_does_not_return_through_stdout(self):
        """★2026-09-20 실사격 회귀 핀 — 판별기가 근거를 stdout 에 찍으면서 값도 stdout 으로
        돌려주면 `$(detect_lane …)` 가 근거 문장을 통째로 삼켜 레인 값이 쓰레기가 된다
        (그 상태에서 self-signed 분기를 못 타 FAIL=2·rc 1 이 났다). 전역 변수 반환이 계약이다.
        """
        src = self._gate_src()
        self.assertIn('DETECTED_LANE="self-signed"', src)
        self.assertIn('DETECTED_LANE="notarized"', src)
        # ★주석은 빼고 **선언문만** 본다 — 이 규율을 설명하는 주석 자체에 금지 형태가 등장하므로,
        #   원문 그대로 묻으면 가드가 자기 설명에 걸린다(실측: 여기서 실제로 걸렸다).
        code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
        self.assertNotIn('$(detect_lane', code,
                         "판별기를 명령 치환으로 부르면 근거 인쇄가 반환값에 섞인다(실측 회귀)")
        self.assertIn('detect_lane "$APP"; APP_LANE="$DETECTED_LANE"', code)

    def test_52_unknown_lane_value_is_rejected(self):
        """레인 값 오타를 조용히 받으면(=auto 로 접으면) 지정한 줄 알고 안 지정된다."""
        rc, out = self._run("/nonexistent.app", "--lane", "bogus")
        self.assertEqual(rc, 2)
        self.assertIn("--lane 은 auto|self-signed|notarized", out)

    # ── (b)(c)(d) 동작 — darwin 한정 ──────────────────────────────────────
    @unittest.skipUnless(sys.platform == "darwin",
                         "게이트 실행은 macOS 도구(codesign·spctl·xcrun)를 요구한다")
    def test_53_self_signed_lane_skips_notarization_axes(self):
        with tempfile.TemporaryDirectory() as td:
            app = self._mini_app(td, adhoc_sign=True)
            _rc, out = self._run(app, "--lane", "self-signed")
            self.assertIn("SKIP ③ stapler validate", out, out[-1500:])
            self.assertIn("SKIP ④ spctl --assess --type execute", out, out[-1500:])
            self.assertIn("PASS=", out)
            self.assertIn("SKIP=2", out, "제외 2축이 계수되지 않았다\n%s" % out[-1500:])
            self.assertIn("GATE_LANE=self-signed GATE_SKIPPED=2", out, out[-1500:])
            # 제외를 PASS 로 세면 안 된다 — 안 돈 축이 통과로 집계되는 것이 이 절의 금지선이다.
            self.assertEqual([ln for ln in out.splitlines()
                              if ln.startswith(("PASS ③", "PASS ④"))], [])

    @unittest.skipUnless(sys.platform == "darwin", "macOS 도구 필요")
    def test_54_forcing_notarized_lane_kills_the_same_app(self):
        """★음성 대조(뮤턴트) — 같은 앱을 공증 레인으로 강제하면 ③④ 가 FAIL 로 죽는다.

        이것이 없으면 (b)의 SKIP 은 '원래 통과했을 축을 뺀 것'과 구별되지 않는다.
        """
        with tempfile.TemporaryDirectory() as td:
            app = self._mini_app(td, adhoc_sign=True)
            rc, out = self._run(app, "--lane", "notarized")
            self.assertIn("FAIL ③ stapler validate", out, out[-1500:])
            self.assertNotEqual(rc, 0, "공증 축이 실패했는데 게이트가 통과했다")
            self.assertIn("GATE_SKIPPED=0", out, out[-1500:])

    @unittest.skipUnless(sys.platform == "darwin", "macOS 도구 필요")
    def test_55_auto_detects_self_signed_and_prints_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            app = self._mini_app(td, adhoc_sign=True)
            _rc, out = self._run(app, "--lane", "auto")
            self.assertIn("레인 판별 근거(codesign -dv)", out,
                          "판별 근거를 인쇄하지 않으면 판정을 사람이 감사할 수 없다")
            self.assertIn("GATE_LANE=self-signed", out, out[-1500:])

    @unittest.skipUnless(sys.platform == "darwin", "macOS 도구 필요")
    def test_56_undecidable_signature_folds_to_strict_lane(self):
        """★fail-closed — 서명이 아예 없어 판별이 불가하면 **관용 쪽으로 접지 않는다**.

        여기를 self-signed 로 접으면 '서명을 지우는 것'이 곧 공증 축 면제가 된다.
        """
        with tempfile.TemporaryDirectory() as td:
            app = self._mini_app(td, adhoc_sign=False)
            rc, out = self._run(app, "--lane", "auto")
            self.assertIn("GATE_LANE=notarized", out, out[-1500:])
            self.assertNotEqual(rc, 0)


class RuntimeManifestAxisTests(unittest.TestCase):
    """⑧ runtime-manifest 축 — 합성 .app 으로 양·음성을 전부 잰다(부트 v2 §2-10 G5 · W-C C1).

    이 축이 존재하는 이유: ②(codesign)는 **이 산출물이 mac 에서 봉인돼 있는가**를 보고,
    ⑧ 은 **배송될 매니페스트가 실제 트리와 맞는가**를 본다. 그 매니페스트는 Windows 설치본에서
    코드서명이 없는 자리를 대신할 유일한 변조 탐지 수단이라, 틀린 채로 나가면 그 레인의 봉인이
    통째로 거짓이 된다. 등급은 FAIL 이다(발행 차단 — master 판정 2026-09-04 D1 레인 분리).

    호출은 --runtime-manifest-only(⑧ 단독 · hdiutil/spctl/codesign 불요)라 macOS 도구 없이 돈다.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.app = os.path.join(self._tmp.name, "Fake.app")
        self.res = os.path.join(self.app, "Contents", "Resources")
        self.rt = os.path.join(self.res, "runtime")
        os.makedirs(os.path.join(self.rt, "python", "bin"))
        with open(os.path.join(self.rt, "python", "bin", "python3"), "w") as fh:
            fh.write("ELF-ish\n")
        os.makedirs(os.path.join(self.rt, "node", "bin"))
        os.makedirs(os.path.join(self.rt, "node", "lib", "node_modules", "npm", "bin"))
        with open(os.path.join(self.rt, "node", "lib", "node_modules", "npm", "bin",
                               "npm-cli.js"), "w") as fh:
            fh.write("#!/usr/bin/env node\n")
        os.symlink("../lib/node_modules/npm/bin/npm-cli.js",
                   os.path.join(self.rt, "node", "bin", "npm"))
        self.man = os.path.join(self.res, "runtime-manifest.json")
        self._emit()

    def tearDown(self):
        self._tmp.cleanup()

    def _emit(self):
        seal = os.path.join(_HERE, "..", "..", "cysjavis-pack", "bin", "javis_runtime_seal.py")
        p = subprocess.run([sys.executable, seal, "emit", "--root", self.rt,
                            "--out", self.man, "--app-version", V, "--source", "test"],
                           capture_output=True, text=True)
        self.assertEqual(0, p.returncode, "픽스처 매니페스트 산출 실패: %s" % (p.stdout + p.stderr))

    def _run(self):
        p = subprocess.run(["bash", _GATE_SH, "--runtime-manifest-only", self.app],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def test_20_baseline_matching_manifest_passes(self):
        """기준선 rc=0 — 이게 깨지면 아래 FAIL 단언들은 '무조건 빨간 검사'를 오독한 것이다."""
        rc, out = self._run()
        self.assertEqual(0, rc, out)
        self.assertIn("PASS ⑧", out)

    def test_21_added_file_blocks_release(self):
        """설치 후 오염 계급(npm i -g 가 번들 안으로) — 2026-09-04 오너 머신 실사고와 같은 형상."""
        d = os.path.join(self.rt, "node", "lib", "node_modules", "@openai", "codex")
        os.makedirs(d)
        with open(os.path.join(d, "package.json"), "w") as fh:
            fh.write("{}\n")
        rc, out = self._run()
        self.assertEqual(1, rc, out)
        self.assertIn("FAIL ⑧", out)
        self.assertIn("@openai", out, "원인 파일을 지목해야 안내다")

    def test_22_symlink_replaced_by_copy_blocks_release(self):
        """★`find -type f` 기반 매니페스트가 구조적으로 눈머는 자리 — 링크가 실복사본이 되면
        번들 npm 호출 전체가 MODULE_NOT_FOUND 로 깨진다(restore-runtime-symlinks.sh:11-13)."""
        link = os.path.join(self.rt, "node", "bin", "npm")
        target = os.path.join(self.rt, "node", "lib", "node_modules", "npm", "bin", "npm-cli.js")
        os.remove(link)
        with open(target) as src, open(link, "w") as dst:
            dst.write(src.read())
        rc, out = self._run()
        self.assertEqual(1, rc, out)
        self.assertIn("node/bin/npm", out)

    def test_23_missing_manifest_blocks_release(self):
        """산출물이 runtime/ 을 실으면서 매니페스트를 빠뜨리면 발행 금지 — Windows 레인의
        변조 탐지가 통째로 사라지기 때문이다(그 레인엔 코드서명 대체물이 없다)."""
        os.remove(self.man)
        rc, out = self._run()
        self.assertEqual(1, rc, out)
        self.assertIn("매니페스트 부재", out)

    def test_24_no_runtime_tree_is_undecidable_not_pass(self):
        """런타임 미동봉 앱은 '통과'가 아니라 '대상 아님/판정 불가'(exit 2)다 — 측정 불능을
        초록으로 접지 않는다(이 게이트 전체의 규율)."""
        import shutil as _sh
        _sh.rmtree(self.rt)
        rc, out = self._run()
        self.assertEqual(2, rc, out)
        self.assertNotIn("PASS ⑧", out)

    def test_25_release_paths_carry_no_diagnostic_flag(self):
        """--runtime-manifest-only 는 진단 전용이다. 발행 경로가 이걸 실으면 ⑧ 만 돌고
        ①~⑦ 이 통째로 건너뛰어진다 — --seal2-only 와 같은 계급의 핀."""
        for path in (_RP_PATH, _RELEASE_YML):
            with open(path, encoding="utf-8") as fh:
                self.assertNotIn("--runtime-manifest-only", fh.read(),
                                 "발행 경로가 진단 전용 플래그를 실었다: %s" % path)


class BuildIdStampedTests(unittest.TestCase):
    """1-b 단계 — **이 발행의** build_id 병기 전에는 SHA256SUMS 를 만들지 않는다(TICKET=cysr-brand-version)."""

    C12 = "0123456789ab"
    BID = "0123456789ab.20260915T1030Z"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def write_latest(self, obj):
        with open(os.path.join(self.root, "latest.json"), "w", encoding="utf-8") as fh:
            fh.write(obj if isinstance(obj, str) else json.dumps(obj))

    def problem(self, version="1.0.0", commit12=C12):
        return rp.latest_build_id_problem(self.root, version, commit12)

    def test_40_stamped_this_release_passes(self):
        self.write_latest({"version": "1.0.0", "build_id": self.BID})
        self.assertIsNone(self.problem())

    def test_41_unstamped_blocks(self):
        self.write_latest({"version": "1.0.0"})
        self.assertIn("stamp-latest-build-id", self.problem())

    def test_42_malformed_or_trailing_newline_blocks(self):
        for bad in ("", "0123456789ab-dirty.20260915T1030Z", self.BID + "\n", 12):
            with self.subTest(bad=bad):
                self.write_latest({"version": "1.0.0", "build_id": bad})
                self.assertIsNotNone(self.problem())

    def test_43_missing_or_unreadable_blocks(self):
        self.assertIsNotNone(self.problem())
        self.write_latest("{not json")
        self.assertIsNotNone(self.problem())
        self.write_latest("[1, 2]")
        self.assertIsNotNone(self.problem())

    def test_44_main_checks_before_writing_sums(self):
        with open(_RP_PATH, encoding="utf-8") as fh:
            src = fh.read()
        main = src[src.index("def main(argv):"):]
        self.assertLess(main.index("latest_build_id_problem(outdir"), main.index("SHA256SUMS.txt — 자기 자신 제외"),
                        "build_id 확인이 SUMS 생성보다 뒤에 있다 — 병기 전 해시가 박제된다")

    def test_45_stale_latest_from_other_version_blocks(self):
        self.write_latest({"version": "0.14.37", "build_id": self.BID})    # 형식은 맞는 옛 파일
        self.assertIn("판번이 이 태그와 다르다", self.problem())

    def test_46_build_id_of_other_commit_blocks(self):
        self.write_latest({"version": "1.0.0", "build_id": "fedcba987654.20260915T1030Z"})
        self.assertIn("태그 커밋", self.problem())

    def test_47_unresolvable_tag_commit_is_block_not_pass(self):
        self.write_latest({"version": "1.0.0", "build_id": self.BID})
        self.assertIn("git fetch --tags", self.problem(commit12=None))

    def test_48_tag_commit12_reads_git_and_rejects_garbage(self):
        class R:
            def __init__(self, rc, out): self.returncode, self.stdout = rc, out
        self.assertEqual(rp.tag_commit12("v1.0.0", run=lambda *a, **k: R(0, self.C12 + "\n")), self.C12)
        self.assertIsNone(rp.tag_commit12("v1.0.0", run=lambda *a, **k: R(128, "")))
        self.assertIsNone(rp.tag_commit12("v1.0.0", run=lambda *a, **k: R(0, "not-a-sha\n")))

    def test_49_latest_json_is_never_taken_from_cache(self):
        with open(_RP_PATH, encoding="utf-8") as fh:
            src = fh.read()
        # ★2026-09-24(X-6 곁): 캐시 판정이 크기 대조 → cache_hit(digest 대조)로 바뀌었다. latest.json 예외는
        #   그대로다 — 이 핀은 **예외가 판정식 앞에 남아 있는가**를 본다(실행 증명은 test_70).
        self.assertIn('a["name"] != "latest.json" and cache_hit(dest, a)', src)


# ─────────────────────────────────────────────────────────────────────────────
# X-6 (2026-09-24 · TICKET=v116-rel) — 옛 exe 를 담은 zip 재사용 · 크기-같음 캐시
# ─────────────────────────────────────────────────────────────────────────────
def _sha(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()


def _zip_bytes(member, payload):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(member, payload)
    return buf.getvalue()


class _Resp:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return b"{}"


class MockReleaseMainTests(unittest.TestCase):
    """main() 을 **가짜 릴리스**로 끝까지 돌린다 — GitHub 호출 0(token·api·download·업로드 urlopen 전부 주입).

    ★왜 소스 핀이 아니라 실행인가: X-6 사고는 「있음 → 생략」이라는 **분기의 결과**가 틀린 것이었다.
      문자열이 있는지로는 분기 결과를 못 잰다 — 옛 exe zip 이 있는 드래프트를 모의로 세우고 main 이
      실제로 무엇을 만들고 무엇을 올리는지를 본다. make-win-zip.py 는 **진짜**를 돌린다(재생성 실물).
    묶음 = 윈도우 단독(맥 레인 0 · latest.json darwin 행 0) — 게이트는 「대상 없음」 경로라 플랫폼 무관.
    """

    V = "1.1.6"
    TAG = "v1.1.6"
    C12 = "0123456789ab"
    EXE = "cysr_1.1.6_x64-setup.exe"
    ZIP = "cysr_1.1.6_x64-setup.zip"
    SIG = "cysr_1.1.6_x64-setup.exe.sig"
    NEW_EXE = b"MZ-new-exe-" + b"\x01" * 4096
    OLD_EXE = b"MZ-old-exe-" + b"\x02" * 4096          # 같은 크기 · 다른 바이트(5차 ae8bec15 재현)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.backup = os.path.join(self.root, "backup")
        self.outdir = os.path.join(self.backup, self.TAG + "-assets")
        self.calls = []                 # (종류, 상세) — 네트워크 모의 기록
        self.downloads = []
        latest = json.dumps({"version": self.V, "build_id": self.C12 + ".20260924T0000Z",
                             "platforms": {"windows-x86_64": {"url": "u", "signature": "s"}}}).encode()
        self.assets = {self.EXE: self.NEW_EXE, self.SIG: b"sig-new-" + b"A" * 404, "latest.json": latest}
        self.digests = True             # False = 자산 JSON 에 digest 칸 없음
        self.served = {}                # 이름 → 다운로드가 실제로 돌려줄 바이트(기본 = assets)
        self.saved = {}
        for name in ("token", "api", "download", "tag_commit12", "BACKUP_ROOT", "HERE"):
            self.saved[name] = getattr(rp, name)
        self.saved_urlopen = rp.urllib.request.urlopen
        rp.token = lambda: "mock-token"
        rp.api = self._api
        rp.download = self._download
        rp.tag_commit12 = lambda tag, run=None: self.C12
        rp.BACKUP_ROOT = self.backup
        rp.urllib.request.urlopen = self._urlopen

    def tearDown(self):
        for name, v in self.saved.items():
            setattr(rp, name, v)
        rp.urllib.request.urlopen = self.saved_urlopen
        self._tmp.cleanup()

    # ── 모의 네트워크 ──
    def _rel(self):
        assets = []
        for i, (name, data) in enumerate(sorted(self.assets.items())):
            a = {"name": name, "size": len(data), "url": "mock://asset/%s" % name, "id": 100 + i}
            if self.digests:
                a["digest"] = "sha256:" + _sha(data)
            assets.append(a)
        return {"draft": True, "assets": assets,
                "upload_url": "https://uploads.invalid/repos/x/releases/1/assets{?name,label}"}

    def _api(self, path, tok, method="GET", data=None, ctype="application/json"):
        self.calls.append((method, path))
        if method == "GET" and path.endswith("/releases/tags/%s" % self.TAG):
            return self._rel()
        if method == "DELETE" and "/releases/assets/" in path:
            return {}
        raise AssertionError("모의 밖 API 호출: %s %s" % (method, path))

    def _download(self, url, dest, tok):
        name = url.rsplit("/", 1)[1]
        self.downloads.append(name)
        with open(dest, "wb") as fh:
            fh.write(self.served.get(name, self.assets[name]))

    def _urlopen(self, req, *a, **k):
        url = req.full_url
        if not url.startswith("https://uploads.invalid/"):
            raise AssertionError("모의 밖 네트워크 호출: %s" % url)
        self.calls.append(("POST", url.split("?name=", 1)[1], req.data))
        return _Resp()

    # ── 도우미 ──
    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = rp.main(["release-postprocess.py", self.TAG] + list(args))
        return rc, out.getvalue(), err.getvalue()

    def local(self, name):
        with open(os.path.join(self.outdir, name), "rb") as fh:
            return fh.read()

    def inner_sha(self, zbytes):
        with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
            self.assertEqual(z.namelist(), [self.EXE])
            return _sha(z.read(self.EXE))

    def sums(self, text):
        return {ln.split("  ", 1)[1]: ln.split("  ", 1)[0] for ln in text.splitlines() if ln}

    def posts(self):
        return {c[1]: c[2] for c in self.calls if c[0] == "POST"}

    # ── ⑴ 옛 exe 를 담은 zip 이 드래프트에 있다 → 재생성 + 대조 1줄 일치 ──
    def test_60_stale_zip_is_regenerated_and_crosscheck_matches(self):
        self.assets[self.ZIP] = _zip_bytes(self.EXE, self.OLD_EXE)
        rc, out, err = self.run_main()
        self.assertEqual(rc, 0, err)
        self.assertIn("≠ 현 exe", out)
        self.assertIn("재생성", out)
        self.assertNotIn("재생성 생략", out)
        self.assertEqual(self.inner_sha(self.local(self.ZIP)), _sha(self.NEW_EXE))
        self.assertIn("✓ zip 내부 대조: zip 속 %s sha=%s · SUMS %s 행=%s → 일치"
                      % (self.EXE, _sha(self.NEW_EXE), self.EXE, _sha(self.NEW_EXE)), out)
        self.assertFalse([c for c in self.calls if c[0] in ("POST", "DELETE")], "dry-run 이 올렸다")

    def test_61_apply_replaces_old_zip_asset_with_regenerated_one(self):
        self.assets[self.ZIP] = _zip_bytes(self.EXE, self.OLD_EXE)
        zip_id = [a["id"] for a in self._rel()["assets"] if a["name"] == self.ZIP][0]
        rc, out, err = self.run_main("--apply")
        self.assertEqual(rc, 0, err)
        self.assertIn(("DELETE", "/repos/%s/releases/assets/%d" % (rp.REPO, zip_id)), self.calls)
        up = self.posts()
        self.assertEqual(self.inner_sha(up[self.ZIP]), _sha(self.NEW_EXE), "옛 exe zip 을 다시 올렸다")
        sums = self.sums(up[rp.SUMS_NAME].decode())
        self.assertEqual(sums[self.EXE], _sha(self.NEW_EXE))
        self.assertEqual(sums[self.ZIP], _sha(up[self.ZIP]), "SUMS 의 zip 행이 올린 zip 과 다르다")
        # 순서: 옛 자산 삭제가 새 zip 업로드보다 앞
        kinds = [(c[0], c[1]) for c in self.calls if c[0] in ("DELETE", "POST")]
        self.assertLess(kinds.index(("DELETE", "/repos/%s/releases/assets/%d" % (rp.REPO, zip_id))),
                        kinds.index(("POST", self.ZIP)))

    # ── ⑵ 같은 exe 를 담은 zip → 생략 ──
    def test_62_matching_zip_is_kept_byte_for_byte(self):
        zb = _zip_bytes(self.EXE, self.NEW_EXE)
        self.assets[self.ZIP] = zb
        rc, out, err = self.run_main()
        self.assertEqual(rc, 0, err)
        self.assertIn("zip 속 exe sha = 현 exe sha(%s…) — 재생성 생략" % _sha(self.NEW_EXE)[:16], out)
        self.assertEqual(self.local(self.ZIP), zb, "생략 분기인데 zip 바이트가 바뀌었다")
        self.assertIn("✓ zip 내부 대조", out)

    def test_63_unreadable_zip_is_regenerated_not_trusted(self):
        self.assets[self.ZIP] = b"PK-not-really-a-zip"
        rc, out, err = self.run_main()
        self.assertEqual(rc, 0, err)
        self.assertIn("판독 불가", out)
        self.assertEqual(self.inner_sha(self.local(self.ZIP)), _sha(self.NEW_EXE))

    # ── ⑶ 대조 불일치 → rc≠0 · 업로드 0 ──
    def test_64_crosscheck_mismatch_blocks_apply(self):
        """재생성기가 틀린 zip 을 만들어도(포장 사고 모의) 대조 줄이 --apply 전에 막는다."""
        self.assets[self.ZIP] = _zip_bytes(self.EXE, self.OLD_EXE)
        fake = os.path.join(self.root, "fakebin")
        os.makedirs(fake)
        with open(os.path.join(fake, "make-win-zip.py"), "w") as fh:
            fh.write("import sys, zipfile\n"
                     "with zipfile.ZipFile(sys.argv[2], 'w') as z:\n"
                     "    z.writestr(%r, b'wrong-bytes')\n" % self.EXE)
        rp.HERE = fake
        rc, out, err = self.run_main("--apply")
        self.assertNotEqual(rc, 0)
        self.assertIn("✗ zip 내부 대조", out)
        self.assertIn("불일치", out)
        self.assertIn("X-6", err)
        self.assertFalse(self.posts(), "대조 불일치인데 업로드했다")
        self.assertFalse([c for c in self.calls if c[0] == "DELETE"], "대조 불일치인데 자산을 지웠다")

    def test_65_crosscheck_unit_contract(self):
        z = os.path.join(self.root, "w.zip")
        good = ["%s  %s\n" % (_sha(self.NEW_EXE), self.EXE)]
        cases = [
            ("일치", {self.EXE: self.NEW_EXE}, good, True),
            ("zip 속 옛 exe", {self.EXE: self.OLD_EXE}, good, False),
            ("엔트리 2개", {self.EXE: self.NEW_EXE, "x.txt": b"x"}, good, False),
            ("SUMS exe 행 없음", {self.EXE: self.NEW_EXE}, ["%s  other\n" % ("0" * 64)], False),
            # agy 1R #4: 판독 불가(None) × 행 없음(None) — None == None 을 일치로 접으면 fail-open.
            ("판독 불가 × 행 없음", {"x.txt": b"x"}, ["%s  other\n" % ("0" * 64)], False),
        ]
        for label, members, lines, want in cases:
            with self.subTest(label):
                with zipfile.ZipFile(z, "w") as zf:
                    for n, b in members.items():
                        zf.writestr(n, b)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertIs(rp.win_zip_crosscheck(z, self.EXE, lines), want)

    # ── 1단계 캐시: 적중 = 로컬 sha256 = 자산 digest 일 때만 ──
    def prefill(self, name, data):
        os.makedirs(self.outdir, exist_ok=True)
        with open(os.path.join(self.outdir, name), "wb") as fh:
            fh.write(data)

    def test_66_same_size_stale_cache_is_redownloaded(self):
        """.sig 는 9·10·11차 전부 412 바이트였다 — 크기-같음 캐시는 항상 옛 서명을 SUMS 에 박았다."""
        self.assets[self.ZIP] = _zip_bytes(self.EXE, self.NEW_EXE)
        stale_sig = b"sig-old-" + b"B" * 404
        self.assertEqual(len(stale_sig), len(self.assets[self.SIG]))
        self.prefill(self.SIG, stale_sig)
        self.prefill(self.EXE, self.OLD_EXE)                 # exe 도 같은 크기의 옛 바이트
        rc, out, err = self.run_main("--apply")
        self.assertEqual(rc, 0, err)
        self.assertIn(self.SIG, self.downloads)
        self.assertIn(self.EXE, self.downloads)
        sums = self.sums(self.posts()[rp.SUMS_NAME].decode())
        self.assertEqual(sums[self.SIG], _sha(self.assets[self.SIG]))
        self.assertEqual(sums[self.EXE], _sha(self.NEW_EXE))

    def test_67_no_digest_means_no_cache(self):
        self.assets[self.ZIP] = _zip_bytes(self.EXE, self.NEW_EXE)
        self.digests = False
        self.prefill(self.SIG, self.assets[self.SIG])        # 바이트까지 같아도 근거 없으면 불신
        rc, out, err = self.run_main()
        self.assertEqual(rc, 0, err)
        self.assertIn(self.SIG, self.downloads)

    def test_68_digest_match_uses_cache(self):
        self.assets[self.ZIP] = _zip_bytes(self.EXE, self.NEW_EXE)
        self.prefill(self.SIG, self.assets[self.SIG])
        rc, out, err = self.run_main()
        self.assertEqual(rc, 0, err)
        self.assertNotIn(self.SIG, self.downloads)
        self.assertIn("(캐시 · digest 일치) %s" % self.SIG, out)

    def test_69_downloaded_bytes_not_matching_digest_block(self):
        self.assets[self.ZIP] = _zip_bytes(self.EXE, self.NEW_EXE)
        self.served[self.SIG] = b"sig-tampered" + b"C" * 400     # 크기는 같다 — 크기 검사는 통과
        rc, out, err = self.run_main("--apply")
        self.assertEqual(rc, 1)
        self.assertIn("digest 불일치 %s" % self.SIG, err)
        self.assertFalse(self.posts())

    def test_70_latest_json_is_redownloaded_even_on_digest_match(self):
        self.assets[self.ZIP] = _zip_bytes(self.EXE, self.NEW_EXE)
        self.prefill("latest.json", self.assets["latest.json"])
        rc, out, err = self.run_main()
        self.assertEqual(rc, 0, err)
        self.assertIn("latest.json", self.downloads)

    def test_71_digest_parser_rejects_malformed(self):
        h = "a" * 64
        self.assertEqual(rp.asset_digest({"digest": "sha256:" + h.upper()}), h)
        for bad in (None, "", "sha256:", "sha1:" + h, "sha256:" + h[:-1], "sha256:" + "g" * 64, 12):
            with self.subTest(bad=bad):
                self.assertIsNone(rp.asset_digest({"digest": bad}))
        self.assertIsNone(rp.asset_digest({}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
