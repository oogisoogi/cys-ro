#!/usr/bin/env python3
"""릴리스 후처리 — CI 완주 후 배포 자산을 완성한다 (2026-07-29 신설).

★배경: 릴리스 CI(`release.yml`)는 DMG 2종 · setup.exe · 업데이터 자산 · 팩 3종까지 만들지만,
**홈페이지가 쓰는 나머지 2종은 만들지 않는다**:
  · `cys_<V>_x64-setup.zip`  — 4번째 다운로드 버튼(.exe 직다운 차단 환경용)
  · `SHA256SUMS.txt`         — 전 자산 무결성 목록
실측(v0.14.2·0.14.3·0.14.4): exe 업로드 03:06 → zip·SUMS 업로드 07:03. 즉 CI 밖의 손절차였다.
이 스크립트가 그 손절차를 **재현 가능하게 고정**한다.

하는 일 (기본은 dry-run — `--apply` 를 줘야 실제로 업로드한다)
  1. GitHub 릴리스에서 전 자산 다운로드 → `~/cys-release-backup/<tag>-assets/`
  2. `make-win-zip.py` 로 zip 변형 생성(기존 발행본 바이트 재현 확인됨)
  3. `SHA256SUMS.txt` 생성 — **자기 자신을 뺀 전 자산**(과거 관례: 13자산)
  4. 자기 검증: zip 왕복 · SUMS 전 줄 재계산 대조 · 누락 0
  5. ★Gatekeeper 게이트(F2 · 2026-08-20 신설): 백업 DMG 2종 = **발행될 실물 바이트**에
     `release-gate-gatekeeper.sh`(정적 실평가)를, 네이티브 아키텍처 DMG 에는 추가로
     `verify-gatekeeper-user-path.sh`(⑥ 봉인 자기파괴 재현 포함)를 돌린다.
     rc≠0(1=FAIL·2=판정 불가) 이면 **전체 비영 종료 — --apply 거부**(측정 불능≠통과).
     macOS 밖에서는 게이트가 못 돈다 = 판정 불가로 fail-closed(무음 skip 금지).
  6. `--apply` 면 zip·SUMS 를 릴리스에 업로드

인증: `git credential fill`(osxkeychain)에서 GitHub 토큰을 얻는다. gh CLI 불요.

사용:
  python3 scripts/release-postprocess.py v0.14.19           # dry-run(다운로드·생성·검증만)
  python3 scripts/release-postprocess.py v0.14.19 --apply   # 업로드까지
  ※예시는 **SEAL 세대 태그**다 — 5단계 게이트의 ⑤ SEAL-2 정적 검사(선컴파일 커버리지)는
    SEAL 도입(2026-08-20) 이후 빌드에서만 성립한다. pre-SEAL 태그 재후처리는 아래
    비상 플래그 없이는 구조적으로 FAIL 한다(docs/RELEASE.md 복구 절차 참조).
  옵션: --unsafe-skip-gatekeeper  Gatekeeper 게이트 생략 — 비상 탈출구(LOUD 경고·평시 금지,
        `--force-no-verify` 선례와 동형: 어떤 자동 경로도 이 플래그를 실어서는 안 된다)
        --repo owner/name        배포 원본 레포(기본 oogisoogi/cys-ro)

★맥 미포함 묶음 (2026-09-09 · 박사님 09:05 「맥 서명 없이 윈도우 먼저」)
  Apple 시크릿 7종이 없는 동안 release.yml 의 macOS 레그는 명시 skip 되고, 그 태그의 드래프트에는
  DMG·맥 업데이터 자산이 **하나도** 오르지 않는다. 종전 이 스크립트는 그런 묶음에서
  ①4단계 `want4` 가 DMG 2종 누락으로 죽고 ②5단계 게이트가 대상 DMG 부재로 rc=2 를 냈다.
  즉 **윈도우 단독 릴리스는 SHA256SUMS.txt 를 만들 수조차 없었다** — 발행 불가의 실질적 원인.
  지금은 「맥 레인 전부-또는-전무」로 판정한다(release-verify.py 와 같은 규율):
    · DMG 2종 + 맥 업데이터 4종이 **전부 있으면** 종전과 똑같이 게이트가 **필수**다.
    · **하나도 없고** latest.json 에 darwin 행도 0이면 「맥 미포함」으로 명시 skip 한다.
    · 그 사이 어떤 상태(반쪽·DMG 만·darwin 행만)도 **판정 불가(2)** 다 — 완화가 아니라 이동이다.
"""
import hashlib
import json
import re
import os
import platform
import subprocess
import sys
import urllib.request

# ★배포 원본 레포 (2026-09-09 정정 · TICKET=cys-release-first-publish)
#   종전 값은 벤더 `idoforgod/cys-terminal` 이었다. 개발자 업데이트 중단으로 우리 포크가
#   배포자가 된 뒤에도 이 줄이 벤더로 남아, 후처리가 **남의 릴리스**를 받아 우리 zip·SUMS 를
#   만들려 했다(= 우리 태그에는 두 자산이 영원히 안 붙는다).
#   ⚠`release-verify.py` 의 `RELEASE_REPO` · `release.yml` 의 `SRC_REPO` ·
#     `src-tauri/tauri.conf.json` 의 updater endpoints 와 **같은 레포**여야 한다.
RELEASE_REPO = "oogisoogi/cys-ro"
REPO = RELEASE_REPO          # 하위 호환 별칭 — main() 이 --repo 로 덮는다
BACKUP_ROOT = os.path.expanduser("~/cys-release-backup")
SUMS_NAME = "SHA256SUMS.txt"          # ★과거 관례 — `SHA256SUMS`(확장자 없음) 아님
HERE = os.path.dirname(os.path.abspath(__file__))


def token():
    """osxkeychain 의 git 자격에서 GitHub 토큰을 얻는다(값은 출력하지 않는다)."""
    p = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                       capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line[len("password="):]
    raise SystemExit("::error::GitHub 토큰을 얻지 못했다(git credential fill)")


def api(path, tok, method="GET", data=None, ctype="application/json"):
    req = urllib.request.Request("https://api.github.com" + path, method=method, data=data)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    if data is not None:
        req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req) as r:
        body = r.read()
    return json.loads(body) if body else {}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, tok):
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/octet-stream")
    with urllib.request.urlopen(req) as r, open(dest, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)


GATE_SCRIPT = os.path.join(HERE, "release-gate-gatekeeper.sh")
USER_PATH_GATE = os.path.join(HERE, "verify-gatekeeper-user-path.sh")


# 맥 레인 전집합 6종 — `release-verify.py` 의 `mac_lane_files()` 와 **같은 목록**이어야 한다.
#   (두 파일이 갈리면 후처리는 통과시킨 묶음을 검증기가 죽인다 — 그 어긋남 자체가 사고다.)
#   ★2026-09-20(TICKET=v110-mac-lane · master 기술 판정): 앞 2종을 DMG → **배포 zip** 으로 옮겼다.
#     우리 포크는 DMG 를 만든 적이 없다(유료 Apple 서명 부재 → CI 맥 레그 비발행 · 로컬
#     자체서명 빌드 산출 = zip). 그래서 종전 상수는 **영원히 없는 자산**을 요구했고 v1.1.0
#     후처리가 실제로 거기서 죽었다: 「::error::배포 자산 누락: cysr_1.1.0_aarch64.dmg,
#     cysr_1.1.0_x64.dmg」. 개수 6과 전부-또는-전무 계약은 그대로다 — 조준만 실재 자산으로.
MAC_LANE = ("cysr-macos-arm64-v{v}.zip", "cysr-macos-x64-v{v}.zip",
            "cysr_aarch64.app.tar.gz", "cysr_aarch64.app.tar.gz.sig",
            "cysr_x64.app.tar.gz", "cysr_x64.app.tar.gz.sig")

# ★맥 **배포 zip** 2종 (2026-09-20 · TICKET=v110-mac-x64) — 설치기가 실제로 받아 까는 자산이다.
#   설치 도우미(install-master/bootstrap.sh)는 이 zip 을 받아 풀어 넣는다. 그래서
#   **설치기 핀(크기·지문·CDHash)의 출처가 바로 이 zip 과 SHA256SUMS.txt** 다.
#   ★2026-09-20 TICKET=v110-mac-lane: 이 2종이 **맥 레인의 다운로드 버튼 자산 그 자체**가 되면서
#     `MAC_LANE` 의 앞 2칸과 같은 이름이 됐다. 이름을 두 벌 적으면 그중 하나가 반드시 뒤처지므로
#     **`MAC_LANE` 에서 파생**한다(`build_decl_line`·`mac_lane_files()` 와 같은 교리).
#     ⇒ `want` 구성에서도 zip 을 두 번 싣지 않는다(아래 4단계 — dmg 2줄은 그래서 삭제됐다).
#   ⚠이 2종은 CI 가 만들지 않는다 — 유료 Apple 서명이 없어 macOS 레그가 macsign 게이트에서 비발행이고
#     (아래 「CI 비발행」 주석), 우리는 로컬에서 자체서명(cys-local)으로 빌드해 손으로 올린다.
#   ⇒ 후처리는 이 2종을 **알아야** 한다: SHA256SUMS.txt 에 줄이 실리고(자산 전수라 자동), 빠졌을 때
#     누락으로 잡힌다(아래 want). 몰랐던 동안 인텔 자산이 없다는 사실을 아무 게이트도 말하지 않았다.
MAC_DIST_ZIPS = tuple(n for n in MAC_LANE if n.endswith(".zip"))


def mac_lane_absent(outdir, version):
    """이 묶음이 **선언된 맥 미포함 묶음**인가? — 맞을 때만 True.

    True 의 조건은 둘 다다: 맥 레인 6종이 **하나도 없고**, latest.json 에 darwin 행이 **0**.
    (latest.json 이 아예 없으면 확인할 근거가 없으므로 False — 판정을 통과 쪽으로 접지 않는다.)

    ★이 함수는 **좁게 설계됐다.** 「맥이 반쪽인가」를 여기서 판정하지 않는다 — 그건 아래 게이트가
      이미 하던 일이다(대상 DMG 부재 = rc 2). 반쪽 묶음은 이 함수가 False 를 주고 종전 경로로
      흘러가 거기서 죽는다. 새 분기를 넓게 잡을수록 기존 fail-closed 경로를 덮어쓸 위험만 커진다.
      즉 이 함수가 여는 문은 **정확히 하나** — 맥이 통째로 없는 윈도우 단독 묶음뿐이다.
    """
    lane = [n.format(v=version) for n in MAC_LANE]
    if any(os.path.exists(os.path.join(outdir, n)) for n in lane):
        return False
    latest = os.path.join(outdir, "latest.json")
    if not os.path.exists(latest):
        return False                      # 근거 부재 = 「미포함」 선언으로 인정하지 않는다
    try:
        with open(latest, encoding="utf-8") as fh:
            platforms = (json.load(fh).get("platforms") or {})
    except (ValueError, OSError):
        return False                      # 읽지 못하면 판정 불가 — 종전 경로로 보낸다
    return not any(k.startswith("darwin-") for k in platforms)


# ★cysr 1.0.0(TICKET=cysr-brand-version): latest.json 의 build_id 는 release.yml `stamp-latest-build-id`
#   잡이 **빌드 뒤에** 병기한다. 이 스크립트는 워크플로 잡이 아니라 사람이 부르는 단계라 `needs:` 로
#   순서를 강제할 수 없다 — 병기 전에 SHA256SUMS.txt 를 만들면 그 해시가 병기 전 latest.json 을 박제해
#   release-verify 5단계에서 멈춘다. 그래서 여기서 **병기 완료를 확인한 뒤에만** SUMS 를 만든다.
#   (agy 1R 지적 2026-09-15: 전제 「후처리 잡이 있다」는 틀렸으나 가리킨 순서 위험은 실재 — 이 가드로 닫는다.)
BUILD_ID_RE = re.compile(r"[0-9a-f]{12}\.[0-9]{8}T[0-9]{4}Z")


def tag_commit12(tag, run=subprocess.run):
    """태그가 가리키는 커밋의 앞 12자(로컬 git) — 확인 불가면 None."""
    try:
        r = run(["git", "-C", HERE, "rev-parse", "--short=12", "%s^{commit}" % tag],
                capture_output=True, text=True)
    except OSError:
        return None
    out = (r.stdout or "").strip()
    return out if r.returncode == 0 and re.fullmatch(r"[0-9a-f]{12}", out) else None


def latest_build_id_problem(outdir, version, commit12):
    """latest.json 에 **이 발행의** build_id 가 병기됐는가 — 문제 문장(차단 사유) 또는 None(통과).

    형식만 보면 남아 있던 옛 latest.json(다른 판·다른 커밋)이 통과한다(agy 2R 지적) — 그래서
    ⑴ version == 이 태그의 판 ⑵ build_id 앞 12자 == 태그 커밋까지 대조한다. 태그 커밋을 확인할 수
    없으면(commit12=None) 통과가 아니라 차단이다(모르는 채 SUMS 를 박제하지 않는다).
    """
    latest = os.path.join(outdir, "latest.json")
    if not os.path.exists(latest):
        return "latest.json 이 릴리스에 없다 — CI 완주를 먼저 확인하라"
    try:
        with open(latest, encoding="utf-8") as fh:
            doc = json.load(fh)
        bid, lv = doc.get("build_id"), doc.get("version")
    except (ValueError, OSError, AttributeError) as e:
        return "latest.json 을 읽을 수 없다(%s)" % e
    if lv != version:
        return "latest.json 판번이 이 태그와 다르다(%r ≠ %s) — 옛 파일이 남았거나 다른 발행이다" % (lv, version)
    if not isinstance(bid, str) or not BUILD_ID_RE.fullmatch(bid):
        return ("latest.json 에 build_id 가 아직 없다(%r) — release.yml stamp-latest-build-id 잡 완료 뒤에 "
                "다시 돌려라(지금 SHA256SUMS 를 만들면 병기 전 해시가 박제된다)" % (bid,))
    if commit12 is None:
        return "태그 커밋을 확인할 수 없다 — git fetch --tags 후 다시 돌려라(build_id 대조 불가 = 통과 아님)"
    if not bid.startswith(commit12 + "."):
        return "latest.json build_id(%s)가 태그 커밋(%s)의 것이 아니다 — 다른 빌드의 파일이다" % (bid, commit12)
    return None


def gatekeeper_gate(outdir, version, unsafe_skip=False,
                    gate_script=GATE_SCRIPT, user_path_script=USER_PATH_GATE,
                    sys_platform=None, machine=None, run=subprocess.run):
    """발행될 실물 바이트(draft 백업 DMG 2종)에 대한 Gatekeeper 실평가 게이트 (F2).

    ★왜 여기인가: CI 게이트(release.yml:429 부근)는 **빌드 산출물**을 업로드 전에 본다.
    그러나 발행 판정의 대상은 이 스크립트가 방금 받은 **백업 자산 = 실제로 발행될 바이트**다.
    그 바이트에 대한 발행 전 로컬 실평가 지점이 없었다 — 4단계(자기 검증) 직후에 세운다.

    fail-closed 계약 (측정 불능은 통과가 아니다 — verify-gatekeeper-user-path.sh 관례):
      · 게이트 rc 1(FAIL)·2(판정 불가) 모두 그대로 비영 반환 → main 이 그 값으로 종료한다.
      · macOS 가 아니면 게이트 자체가 못 돈다(hdiutil·spctl·codesign 부재) = 판정 불가 → 2.
      · 대상 DMG 부재도 판정 불가 = 2. 무음 skip 경로는 없다.

    반환: 0=통과 · 비영=차단(--apply 거부). 키워드 인자(gate_script·user_path_script·
    sys_platform·machine·run)는 테스트 주입 전용이다 — test_release_postprocess_gate.py 가
    페이크 게이트(exit 0/1/2)로 이 계약을 박제한다.
    """
    if unsafe_skip:
        # `--force-no-verify` 선례 동형의 비상 탈출구 — 조용히 열리면 상시 우회가 되므로 LOUD.
        print("!!!! [UNSAFE] --unsafe-skip-gatekeeper — Gatekeeper 게이트를 건너뛴다: 발행될 "
              "바이트가 사용자 머신에서 열리는지 이 실행은 아무것도 증명하지 않는다.", file=sys.stderr)
        print("!!!! 비상 탈출구다(평시 금지 · 측정 불능≠통과) — 사용 사유를 릴리스 기록"
              "(SESSION_STATE·릴리스 노트)에 남겨라.", file=sys.stderr)
        return 0
    # ★맥 미포함 묶음 판정을 **플랫폼 검사보다 먼저** 둔다 (2026-09-09).
    #   평가할 맥 바이트가 0종이면 "macOS 에서 다시 돌려라"는 지시가 성립하지 않는다 —
    #   어떤 맥에서 돌려도 평가할 것이 없다. 그 경우의 정직한 답은 skip 이 아니라 「대상 없음」이다.
    #   ⚠여는 문은 정확히 하나뿐이다(mac_lane_absent 의 좁은 조건). 맥이 반쪽인 묶음은 여기를
    #     통과하지 못하고 아래 「게이트 대상 DMG 없음」에서 종전 그대로 rc=2 로 죽는다.
    if mac_lane_absent(outdir, version):
        print("\n═══ Gatekeeper 게이트 — 대상 없음(맥 미포함 묶음) ═══", flush=True)
        print("  맥 레인 6종 0개 · latest.json darwin 행 0 — 평가할 맥 바이트가 없다.")
        print("  ※이 묶음은 **윈도우 단독 배포**다. 맥 사용자는 이 릴리스를 받지 않는다"
              "(release-verify.py 도 같은 판정을 내고 로그에 「맥 자산 미포함」을 남긴다).")
        return 0

    if sys_platform is None:
        sys_platform = sys.platform
    if machine is None:
        machine = platform.machine()
    if sys_platform != "darwin":
        # macOS 밖 = 게이트 불가. skip 은 곧 무검증 발행이므로 판정 불가(2)로 fail-closed 한다
        # (release-gate-gatekeeper.sh 의 exit 2 계약과 동일 — 통과가 아니다).
        print("::error::Gatekeeper 게이트는 macOS 에서만 돈다(현재 platform=%s) — 판정 불가"
              "=통과 아님. macOS 에서 다시 돌려라(비상시에만 --unsafe-skip-gatekeeper)."
              % sys_platform, file=sys.stderr)
        return 2

    # 상위판(⑥ 봉인 자기파괴 재현 = 동봉 python 실제 스폰)은 **네이티브 아키텍처 DMG 에만**.
    # 비네이티브 쪽을 정적판만으로 두는 근거: verify-gatekeeper-user-path.sh 는 대상 아키텍처
    # python 을 실행하므로 arm64 맥에서 x64 DMG 는 Rosetta 2 의존이 생기고, 없으면 구조적
    # FAIL 이다. 정적판은 실행 0으로 양쪽 결정론 — release-gate-gatekeeper.sh 머리 주석
    # 「scripts/verify-gatekeeper-user-path.sh 와의 관계」(행번호는 병렬 수정으로 유동).
    native_arch = "aarch64" if machine == "arm64" else "x64"
    print("\n═══ Gatekeeper 게이트 — 발행될 실물 바이트(draft 백업 DMG 2종) 실평가 ═══", flush=True)
    for arch in ("aarch64", "x64"):
        dmg = os.path.join(outdir, "cysr_%s_%s.dmg" % (version, arch))
        if not os.path.exists(dmg):
            print("::error::게이트 대상 DMG 없음: %s — 판정 불가=통과 아님" % dmg, file=sys.stderr)
            return 2
        cmds = [["bash", gate_script, dmg]]
        if arch == native_arch:
            cmds.append(["bash", user_path_script, dmg])
        for cmd in cmds:
            print("  → %s %s" % (os.path.basename(cmd[1]), os.path.basename(dmg)), flush=True)
            rc = run(cmd).returncode
            if rc != 0:
                print("::error::Gatekeeper 게이트 차단 rc=%d (%s · %s) — 1=FAIL·2=판정 불가, "
                      "둘 다 발행 금지(--apply 거부)"
                      % (rc, os.path.basename(cmd[1]), os.path.basename(dmg)), file=sys.stderr)
                return rc
    print("  ✓ Gatekeeper 게이트 통과 — DMG 2종(네이티브 %s 는 사용자 경로 재현 ⑥ 포함)" % native_arch)
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    tag = argv[1]
    rest = argv[2:]
    apply_ = "--apply" in argv[2:]
    unsafe_skip = "--unsafe-skip-gatekeeper" in argv[2:]
    # ★매개변수화하되 기본값이 곧 정본이다(마스터 판정 2026-09-09 · REPO 1곳).
    global REPO
    if "--repo" in rest:
        i = rest.index("--repo")
        if i + 1 >= len(rest):
            print("::error::--repo 뒤에 owner/name 이 없다", file=sys.stderr)
            return 2
        REPO = rest[i + 1]
    print("배포 원본 레포: %s%s" % (REPO, "" if REPO == RELEASE_REPO else "  ⚠기본값 아님"))
    version = tag.lstrip("v")
    tok = token()

    # ★draft 릴리스는 `/releases/tags/<tag>` 로 조회되지 않는다(404 — 실측).
    #   목록 조회로 폴백해야 CI 직후(draft 상태)에도 후처리가 돈다.
    try:
        rel = api("/repos/%s/releases/tags/%s" % (REPO, tag), tok)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        rel = None
        for page in (1, 2):
            for r in api("/repos/%s/releases?per_page=50&page=%d" % (REPO, page), tok):
                if r.get("tag_name") == tag:
                    rel = r
                    break
            if rel:
                break
        if rel is None:
            raise SystemExit("::error::릴리스 %s 를 찾지 못했다(draft 포함 조회 실패)" % tag)
        print("  (draft — 목록 조회로 찾음)")
    print("릴리스 %s — draft=%s · 자산 %d종" % (tag, rel.get("draft"), len(rel.get("assets", []))))

    outdir = os.path.join(BACKUP_ROOT, tag + "-assets")
    os.makedirs(outdir, exist_ok=True)

    # ── 1. 전 자산 다운로드 ──
    by_name = {}
    for a in rel.get("assets", []):
        dest = os.path.join(outdir, a["name"])
        # latest.json 은 stamp 잡이 빌드 뒤에 다시 올리는 파일이라 캐시를 믿지 않는다(크기가 우연히 같은 옛 파일 방지).
        if a["name"] != "latest.json" and os.path.exists(dest) and os.path.getsize(dest) == a["size"]:
            print("  (캐시) %-34s %12d" % (a["name"], a["size"]))
        else:
            print("  받는 중 %-34s %12d …" % (a["name"], a["size"]), flush=True)
            download(a["url"], dest, tok)
            got = os.path.getsize(dest)
            if got != a["size"]:
                print("::error::크기 불일치 %s: %d != %d" % (a["name"], got, a["size"]), file=sys.stderr)
                return 1
        by_name[a["name"]] = dest

    # ── 1-b. build_id 병기 완료 확인 (SHA256SUMS 박제 전) ──
    problem = latest_build_id_problem(outdir, version, tag_commit12(tag))
    if problem:
        print("::error::%s" % problem, file=sys.stderr)
        return 1

    # ── 2. zip 변형 (없으면 생성) ──
    exe = "cysr_%s_x64-setup.exe" % version
    zipname = "cysr_%s_x64-setup.zip" % version
    if exe not in by_name:
        print("::error::%s 가 릴리스에 없다 — CI 완주를 먼저 확인하라" % exe, file=sys.stderr)
        return 1
    zippath = os.path.join(outdir, zipname)
    if zipname in by_name:
        print("  zip 이미 릴리스에 있음 — 재생성 생략")
    else:
        r = subprocess.run([sys.executable, os.path.join(HERE, "make-win-zip.py"),
                            by_name[exe], zippath])
        if r.returncode != 0:
            return 1
        by_name[zipname] = zippath

    # ── 3. SHA256SUMS.txt — 자기 자신 제외 전 자산 ──
    names = sorted(n for n in by_name if n != SUMS_NAME)
    lines = ["%s  %s\n" % (sha256_file(by_name[n]), n) for n in names]
    sums_path = os.path.join(outdir, SUMS_NAME)
    with open(sums_path, "w") as fh:
        fh.writelines(lines)
    print("  %s 생성 — %d자산" % (SUMS_NAME, len(names)))

    # ── 4. 자기 검증 ──
    bad = 0
    for line in lines:
        want, name = line.split("  ", 1)
        name = name.strip()
        if sha256_file(by_name[name]) != want:
            print("::error::SUMS 불일치: %s" % name, file=sys.stderr)
            bad += 1
    if bad:
        return 1
    # 홈페이지 다운로드 버튼이 전부 들어 있는가(누락 0 — 오너 지시 ⓑ)
    #   ★2026-09-09: 맥 다운로드 자산은 **맥 레인이 포함된 묶음에서만** 요구한다. 맥이 통째로 빠진
    #   윈도우 단독 묶음에서 그것을 요구하면 SUMS 를 만들지 못해 발행 자체가 불가능해진다.
    #   맥이 반쪽인 묶음은 아래 게이트(mac_lane_state)가 판정 불가로 죽인다 — 여기서 느슨해진
    #   만큼을 거기서 그대로 받는다.
    #   ★2026-09-20 TICKET=v110-mac-lane: 종전에 여기 있던 DMG 2줄을 삭제했다. 우리 포크가
    #   만든 적 없는 자산이라 맥이 실재하는 v1.1.0 묶음을 「누락」으로 죽이고 있었다(실측 오류
    #   원문은 `MAC_LANE` 주석). 맥 다운로드 자산의 정본은 이제 아래 배포 zip 2종 하나뿐이고,
    #   **두 번 싣지 않는다**(MAC_DIST_ZIPS 는 MAC_LANE 에서 파생 — 중복 요구 0).
    win_only = mac_lane_absent(outdir, version)
    want = [exe, zipname]
    if not win_only:
        # ★맥 배포 zip 2종을 요구한다(2026-09-20). 설치기가 받는 자산이 이것이고, 한쪽이 없으면
        #   그 칩의 사람들은 설치가 통째로 막힌다 — 인텔 자산이 없던 1.0.2 가 정확히 그 상태였다.
        #   ⚠1.0.2 이하 태그를 다시 후처리하면 x64 zip 이 없어 여기서 적색이다. 그것이 의도다
        #     (그 태그는 인텔 맥을 덮지 않는다 — 통과시키면 그 사실이 다시 조용해진다).
        want = [n.format(v=version) for n in MAC_DIST_ZIPS] + want
    missing = [w for w in want if w not in by_name]
    if missing:
        print("::error::배포 자산 누락: %s" % ", ".join(missing), file=sys.stderr)
        return 1
    print("  ✓ 자기 검증 통과 — 전 줄 재계산 일치 · 배포 %d종 누락 0%s"
          % (len(want), " (맥 미포함 — 윈도우 단독)" if win_only else ""))

    # ── 5. Gatekeeper 게이트 (F2) — 발행될 실물 바이트를 dry-run·--apply 공통으로 실평가 ──
    #    ★업로드(6단계)·dry-run 성공 판정보다 반드시 앞: rc≠0 이면 여기서 전체가 비영 종료라
    #      --apply 는 게이트를 우회할 수 없다(fail-closed · 측정 불능≠통과).
    gate_rc = gatekeeper_gate(outdir, version, unsafe_skip=unsafe_skip)
    if gate_rc:
        return gate_rc

    # ── 6. 업로드 ──
    if not apply_:
        print("\n[dry-run] 업로드하지 않았다. 실제 업로드는 --apply")
        print("산출물: %s" % outdir)
        return 0

    up_base = rel["upload_url"].split("{")[0]
    existing = {a["name"]: a["id"] for a in rel.get("assets", [])}
    for name, ctype in ((zipname, "application/zip"), (SUMS_NAME, "text/plain")):
        if name in existing:      # --clobber 동등: 기존 자산 삭제 후 재업로드
            api("/repos/%s/releases/assets/%d" % (REPO, existing[name]), tok, method="DELETE")
        with open(os.path.join(outdir, name), "rb") as fh:
            body = fh.read()
        req = urllib.request.Request(up_base + "?name=" + name, method="POST", data=body)
        req.add_header("Authorization", "Bearer " + tok)
        req.add_header("Content-Type", ctype)
        with urllib.request.urlopen(req) as r:
            r.read()
        print("  ✓ 업로드 %s (%d bytes)" % (name, len(body)))
    print("\n✅ 후처리 완료 — %s" % outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
