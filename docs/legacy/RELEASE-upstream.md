# (이력 · 비실행) 원작자·0.14.x 시절 릴리스 절차

> **이 문서는 따라 하는 절차가 아니다.** 원작자(벤더) 레인과 0.14.x 시절의 기록을 리베이스 대조용으로 남긴 것이다 —
> DMG·Apple 서명·공증·인앱 Update 버튼·원작자 홈페이지(`www.cysinsight.com`)·`cys-terminal` 저장소 절차는 **우리 포크(cysr · `oogisoogi/cys-ro`)가 쓰지 않는다**.
> 아래 본문의 「현행」「필수」「정본」 같은 말은 **그 시절의 말**이다. 지금 발행 절차의 정본 = [`docs/RELEASE.md`](../RELEASE.md) 맨 위 「현행 정본」 절.
> 옮긴 날 = 2026-10-07(TICKET=cysr-118-publish-docs 2판 · master#0885ae7a ⑥ · codex 1R MAJOR · agy 1R MINOR). 본문 = 기반 `8ba48f9e` 의 원문 그대로(3판 · master#62af6f8e ⑥ — 2판 이식본에 섞였던 1판 명칭 변환을 걷어 냄 · 절 머리의 「— 원작자 레인…」 꼬리표도 없는 원문).

---

## (이력) 옛 표준 절차 상자(원작자·0.14.x 시절)

> **현행 표준 절차(2026-07 정정)**: 릴리스는 **release.yml 자동화**가 정본이다 —
> ①버전 범프(아래 §0 **8곳** = 수동 6 + `Cargo.lock` 2패키지)+`cargo build`(Cargo.lock 재생성)
> +로컬 `bash scripts/secret-scan.sh --all` clean 확인
> ②main push ③`git tag vX.Y.Z && git push origin vX.Y.Z`(태그=오너 직접·가드)
> ④CI 4잡(mac signed·mac x86 sidecar·**windows NSIS**·pack) green + windows-build.yml T5 green
>  (windows-build.yml PTY 스모크는 **pane env 실주입 관측** — U-20 `CLAUDE_CODE_GIT_BASH_PATH`·
>  좌석 토큰 `CYS_SEAT_TOKEN` — 까지 게이트한다. 단 **벤더 링크 분절**(claude 가 그 env 로 훅을
>  **실발화**하는가)은 claude 인증 필요로 CI 게이트化 불가 — §4 「Windows 실기 수동 체크리스트」
>  수동 행이 그 몫이다. CI 초록을 그 분절의 증거로 읽지 마라. ★windows-build.yml 은
>  **태그 push 에 자동 트리거되지 않는다**(트리거=feat/windows-x64-dist push+workflow_dispatch
>  한정) — 릴리스 SHA 에서 **수동 dispatch** 로 돌려 green 을 받아라. 이전 런의 초록은
>  릴리스 증거가 아니다)
> ⑤릴리스 자산·`latest.json`(tauri v2 — darwin-aarch64·darwin-x86_64·windows-x86_64 3키) 실측 확인.
> Windows 인스톨러는 **NSIS**다(`src-tauri/tauri.windows.conf.json targets:["nsis"]`) — 아래 §2·부록의
> 수동 MSI/WiX 경로는 **legacy(폐기·참고용)**이며 따르지 마라.


---

## (이력) §0-A 업데이트 발행 이원화 정책(인앱 Update 버튼·홈페이지 시절)

## 0-A. 업데이트 발행 이원화 정책 (2026-07-12 오너 확정)

> **두 레인으로 발행한다.**
> ① **팩-온리 패치 (기본)** — Rust/GUI 코드가 안 바뀐 릴리스는 pack 3종
> (pack-manifest.json / .minisig / pack.tar.gz)만 발행. 사용자는 인앱 Update 버튼으로
> **무중단**(재시작 없음 · 세션/부서/직원 유지) 적용.
> ② **바이너리 릴리스 (드묾)** — 본체(Rust/GUI) 변경 시에만. v0.12.51+부터 인앱 원클릭
> 본체 설치는 제거되고 배지는 **안내 + 홈페이지(www.cysinsight.com) 다운로드 링크**만
> 제공한다(본체 교체 = 홈페이지 풀 설치본). v0.12.50 이하 사용자에게는 이 전환 릴리스가
> **마지막 인앱 바이너리 업데이트**로 배달된다.

**레인 판정 게이트(결정론)**: `git diff <직전태그>..HEAD --stat -- src/ src-tauri/ ui/ build.rs Cargo.toml`
출력이 비어 있으면(=`cysjavis-pack/`·docs만 변경) 팩-온리 대상. 한 줄이라도 있으면 바이너리 릴리스.

> ⚠ **레거시 도달 예외(2026-07-12 오너 확정)**: 수정이 팩에만 있어도 **구버전(≤0.12.50) 사용자에게
> 반드시 도달해야 하는 심각한 버그 수정이면 바이너리 릴리스로 발행**한다. 구버전의 유일한 수신
> 통로는 인앱 바이너리 업데이트(latest.json)뿐이고, 팩-온리는 min_binary 하한이 구버전을 (의도적으로)
> 차단하기 때문이다. 바이너리 릴리스의 latest.json·업데이터 자산 발행은 계속 유지한다 — 이것이
> 구버전 사용자의 원클릭 업그레이드 통로다("본체=홈페이지"는 v0.12.51+ 화면 동작이지 채널 폐쇄가 아님).


---

## (이력) §1 macOS 빌드 — DMG·Apple 서명·공증·실사용자 경로 게이트

## 1. macOS 빌드 (DMG + 앱 번들 + 업데이트 아티팩트)

> **자동 업데이트가 켜져 있으므로(`createUpdaterArtifacts: true`) 빌드 시 서명 키가 필요합니다.**
> 키 없이 빌드하면 `.app.tar.gz.sig`가 안 생기고 업데이트 manifest를 만들 수 없습니다.

```sh
# 사전: bun, rustup(aarch64-apple-darwin / x86_64-apple-darwin)
#       서명 키: ~/.tauri/cys-updater.key (최초 1회 `bun x @tauri-apps/cli signer generate`로 생성, 분실 시 자동업데이트 영구 불가)
export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/cys-updater.key)"
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD=""   # 키에 암호를 걸었다면 그 값

bun x @tauri-apps/cli build
#  → target/release/bundle/dmg/cys_0.2.0_aarch64.dmg
#  → target/release/bundle/macos/cys.app             (cysd·cys externalBin 동봉)
#  → target/release/bundle/macos/cys.app.tar.gz(.sig) (자동 업데이트용 — 서명 키 있을 때만)

# 배포본으로 정리 (아키텍처 접미사 표준화)
cp target/release/bundle/dmg/cys_0.2.0_aarch64.dmg dist-mac/cys-0.2.0-macos-arm64.dmg

# 업데이트 manifest(latest.json) + 자산 생성
sh scripts/make-update-manifest.sh 0.2.0 <OWNER> cys-terminal
#  → dist-update/latest.json, dist-update/cys-0.2.0-macos-aarch64.app.tar.gz
```

`beforeBuildCommand`(scripts/bundle-prep.sh)가 UI 번들 + cys/cysd 릴리스 빌드 + `externalBin` 배치를
자동 수행합니다. Intel 빌드가 필요하면 `--target x86_64-apple-darwin` 추가(manifest의 `darwin-x86_64`에 키 추가).

### ★Apple 서명·공증 (다른 맥 배포의 유일한 정공법 — 2026-06-15)

**왜 필수인가**: ad-hoc 서명 빌드는 *빌드한 맥*에선 우클릭→열기로 되지만, **다른 맥으로
전송하면** 파일에 `com.apple.quarantine`가 붙고 macOS(Sequoia+)가 **ad-hoc·미공증 앱을
"손상됨"으로 차단**한다(실측 2026-06-15: `spctl -a`=rejected). 공증해야만 어떤 맥에서도
경고/손상됨 없이 열린다.

**1회 셋업 (사람 단계)**:
1. **Apple Developer Program 가입**($99/년, developer.apple.com)
2. **Developer ID Application 인증서** 발급 → Keychain 설치
   (Xcode > Settings > Accounts > Manage Certificates > + > Developer ID Application,
    또는 developer.apple.com > Certificates)
3. **notarytool 자격증명** — 둘 중 하나:
   - app-specific password: appleid.apple.com > 로그인 및 보안 > 앱 암호 생성
   - 또는 App Store Connect API key(.p8 + Key ID + Issuer ID)
4. **Team ID** 확인: developer.apple.com > Membership

**빌드 (자격증명 env + 헬퍼 스크립트가 자동 codesign+공증+staple+검증)**:
```sh
export APPLE_SIGNING_IDENTITY="Developer ID Application: NAME (TEAMID)"
export APPLE_ID="you@example.com" APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx" APPLE_TEAM_ID="TEAMID"
#   (또는 API key: APPLE_API_KEY_PATH=…/AuthKey_XXXX.p8 APPLE_API_KEY=KEYID APPLE_API_ISSUER=ISSUER)
export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/cys-updater.key)" TAURI_SIGNING_PRIVATE_KEY_PASSWORD=""

bash scripts/build-macos-signed.sh  # env 검증 → tauri build(자동 공증) → spctl/stapler 검증 → dist-mac + manifest
#  (반드시 bash — 스크립트가 프로세스 치환 `< <(...)`(bash 전용)을 쓴다. `sh`로 실행하면 line 57 syntax error.)
```
- 배선: `tauri.conf.json > bundle.macOS.entitlements = entitlements.plist`(hardened runtime +
  사이드카 cysd·cys 로드 허용). Tauri가 빌드 중 Developer ID codesign + notarytool 제출 +
  staple 을 자동 수행한다(별도 `codesign`/`notarytool` 수동 호출 불요).
- **검증 통과 기준**: `spctl -a -vv cys.app` = **accepted**. (rejected면 공증 실패 — 빌드
  로그의 notarization 결과 확인.)
  ⚠**이것만으로는 부족하다**(2026-08-01 실사고). 빌드 직후의 `.app`은 accepted 인데
  **사용자가 브라우저로 받아 설치하면 "손상되었기 때문에 열 수 없습니다"로 차단**될 수 있다.
  반드시 아래 실사용자 경로 게이트를 함께 돌려라.
- 공증 빌드는 **ad-hoc 재서명·`xattr` 우회가 전혀 불필요**하다.

#### ★실사용자 경로 게이트 — `scripts/verify-gatekeeper-user-path.sh` (2026-08-01 신설·필수)

```sh
bash scripts/verify-gatekeeper-user-path.sh dist-mac/cys-<V>-macos-arm64.dmg  # 로컬 빌드 산출물
bash scripts/verify-gatekeeper-user-path.sh --version <V> --arch aarch64      # 발행본(원격)
bash scripts/verify-gatekeeper-user-path.sh https://…/downloads/cys_<V>_x64.dmg  # 임의 URL
#   exit 0 = PASS · 1 = FAIL(배포 금지) · 2 = 판정 불가(도구·자산 문제 — 통과 아님)
```

**왜 필요한가 — 2026-08-01 사고의 근본원인**: 앱 번들의 **동봉 Python 이 실행 중
`Contents/Resources/runtime/python/lib/python3.12/**/__pycache__/*.pyc` 를 번들 안에 새로
써서 코드서명 봉인을 스스로 깨뜨린다**. `codesign --verify` 진단 원문:
`a sealed resource is missing or invalid / file added: …/__pycache__/_compression.cpython-312.pyc`.
공증·staple 자체는 **정상**이다. 그런데 사용자가 브라우저로 받으면 파일에
`com.apple.quarantine` 이 붙고, **첫 실행 시 Gatekeeper 가 전체 재검증**을 돌려 깨진 봉인을
잡아내 실행을 차단한다.

**검증 구멍**: 지금까지의 릴리스 검증(ⓓ)은 `curl` 사본만 봤다 — `curl` 로 받은 파일에는
quarantine 이 **안 붙어서** Gatekeeper 전체 재검증 경로 자체가 돌지 않는다. 그래서 이 사고
경로를 **한 번도 재현하지 못했다**. 이 스크립트가 그 구멍을 닫는다.

**하는 일 6단계** — ① 실제 브라우저 다운로드에서 실측한 형식으로 DMG 에 `com.apple.quarantine`
부착 → ② 마운트(격리 볼륨 확인) → ③ `ditto` 로 드래그 설치 모사 + **quarantine 상속 확인** →
④ `spctl --assess --type execute --verbose=4` = accepted → ⑤ `codesign --verify --deep --strict`
+ `stapler validate` → ⑥ ★**봉인 자기파괴 재현**: 동봉 python 을 1회 돌린 뒤 `codesign --verify`
재실행 → `file added` 가 나오면 **FAIL**.

**⑥ 판정의 두 갈래**
- **⑥-A**(판정 본체): env 완화를 못 타는 경로(셸·훅·pane 에서 도는 python)에서도 번들이 안
  깨져야 한다 = **패키징 층위 불변식**. 닫는 방법은 둘뿐이다 — 서명 **전** `compileall
  --invalidation-mode unchecked-hash` 로 stdlib `.pyc` 를 **서명 대상에 포함**시키거나,
  런타임을 봉인 밖으로 빼는 것.
- **⑥-B**: 앱이 python 을 스폰할 때 얹는 `PYTHONDONTWRITEBYTECODE=1`(SEAL-1 완화)이 실제로
  쓰기를 막는지. 실측 v0.14.9: **⑥-B PASS**(.pyc 3→3) · **⑥-A FAIL**(.pyc 3→30).
  즉 스폰 env 완화는 유효하지만 **번들 자체는 아직 깨질 수 있는 상태**다.

**⑥ 이 `.app` 확장자를 뗀 사본에서 도는 이유**(실측 2026-08-01, macOS 25.5.0): macOS 는
`.app` 번들에서 바이너리를 한 번이라도 exec 하면 그 번들을 **앱 번들 보호**로 잠가서, 그 뒤
셸이 띄운 python 의 쓰기를 EPERM 으로 막는다 → **결함이 있어도 아무 일 없는 것처럼 보인다**
(측정: `.app` 사본은 .pyc 3→3, codesign exit 0 = **거짓 PASS**). 실제 사고 경로에서는 쓰는
주체가 **앱 자신**(같은 Team ID)이라 이 보호를 통과해 쓰기가 성사된다. 확장자를 떼는 것은
검사를 약화시키는 우회가 아니라, **검증기 머신에서만 발생하는 OS 보호가 결함을 가리는 것을
걷어내는 조치**다(서명·봉인 내용은 동일).

**전제·비용**: macOS + Xcode CLT · 임시폴더에 약 2GB(DMG 227MB + 앱 사본 492MB × 3, 종료 시
자동 삭제) · 로컬 DMG 기준 약 1분 · **앱을 실행하지 않는다**(동봉 python 만 1회 스폰).
arm64 머신에서 x64 DMG 를 볼 땐 Rosetta 2 필요(없으면 ⑥-A 가 "검사 불성립"으로 FAIL —
측정 불능은 통과가 아니다).

**`scripts/verify-release-remote.py` 와의 관계 (직교 · 둘 다 필수)**

| | `verify-release-remote.py` | `verify-gatekeeper-user-path.sh` |
|---|---|---|
| 시점 | 발행 **후** | 빌드 직후 + 발행 후 |
| 보는 것 | 홈페이지 표기·링크·용량·SHA256 (=**올바른 파일이 올라갔나**) | 그 파일을 **받아서 설치했을 때 열리나** |
| 대상 | 원격 HTML·HTTP 헤더·SHA256SUMS.txt | DMG 바이트 → 마운트 → 앱 번들 서명·봉인 |
| 못 잡는 것 | 자산이 정상 링크·정상 해시로 올라가 있으면서 **열리지 않는 것** | 홈페이지 표기 오류·링크 누락 |

즉 앞의 것은 "제대로 배포됐나", 뒤의 것은 "제대로 열리나"다. **하나가 다른 하나를 대신하지
못한다.**


---

## (이력) D6 체크리스트 중 원작자 레인 두 줄(공증 빌드·DMG 실사용자 경로)

- [ ] **공증 빌드**(`spctl -a -vv cys.app` = accepted) — 미공증은 비기술자 배포 금지(다른 맥에서 "손상됨" 차단).
- [ ] **실사용자 경로 게이트 exit 0** — `bash scripts/verify-gatekeeper-user-path.sh <DMG>`.

---

## (이력) §2 Windows 수동 빌드(MSI)·크로스빌드 · §3 저장소 최초 설정 · §4 GitHub 릴리스 · 옛 자동 업데이트 동작 요약

## 2. [LEGACY·폐기] Windows 수동 빌드 (MSI + ZIP) — 현행은 CI NSIS, 따르지 말 것

> Windows 머신(또는 Parallels Win11 ARM64)에서 수행. 코어는 검증 완료.

```powershell
# 사전: rustup target add x86_64-pc-windows-msvc aarch64-pc-windows-msvc
cargo build --release --bin cys --bin cysd --target x86_64-pc-windows-msvc
cargo build --release --bin cys --bin cysd --target aarch64-pc-windows-msvc

# WiX(candle/light)로 MSI 생성 — dist-win/cys.wxs(arm64)·cys-x64.wxs(x64) 사용
#   ProgramFiles에 cys.exe·cysd.exe 설치 + PATH 등록
candle dist-win\cys-x64.wxs -o cys-x64.wixobj
light  cys-x64.wixobj -o dist-win\cys-0.2.0-windows-x64.msi
candle dist-win\cys.wxs    -o cys.wixobj
light  cys.wixobj    -o dist-win\cys-0.2.0-windows-arm64.msi

# ZIP (설치 없이)
Compress-Archive target\x86_64-pc-windows-msvc\release\cys.exe,cysd.exe `
  dist-win\cys-0.2.0-windows-x64.zip
```

GUI 앱의 Windows Tauri 빌드는 잔여 — 현재 Windows는 CLI+데몬 중심 배포.

### ★macOS에서 Windows 크로스빌드 (Windows 머신 없이 — 2026-06-15 실증)

Windows 머신이 없어도 macOS에서 MSI까지 만들 수 있다. **windows-gnu 타깃**(wxs Source가
가리키는 `x86_64-pc-windows-gnu`·`aarch64-pc-windows-gnullvm`)을 zig 링커로 크로스컴파일하고,
WiX 대신 **msitools(wixl)**로 MSI를 만든다. (cys.wxs는 표준 WiX v3라 wixl이 그대로 읽는다.)

```sh
# 사전: rustup(homebrew rust와 별개) · cargo-zigbuild · zig · msitools(wixl)
#   brew install zig msitools && cargo install cargo-zigbuild
#   curl --proto '=https' -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
rustup target add x86_64-pc-windows-gnu aarch64-pc-windows-gnullvm

# 바이너리 크로스컴파일 (GUI 없이 cys+cysd만)
cargo zigbuild --release --target x86_64-pc-windows-gnu      --bin cys --bin cysd
cargo zigbuild --release --target aarch64-pc-windows-gnullvm --bin cys --bin cysd

# MSI (wixl — wxs Source 상대경로가 ../target/... 이므로 dist-win에서 실행)
cd dist-win
wixl -o cys-0.2.1-windows-x64.msi   cys-x64.wxs
wixl -o cys-0.2.1-windows-arm64.msi cys.wxs
cd ..
# ZIP
zip -j dist-win/cys-0.2.1-windows-x64.zip   target/x86_64-pc-windows-gnu/release/cys.exe target/x86_64-pc-windows-gnu/release/cysd.exe
zip -j dist-win/cys-0.2.1-windows-arm64.zip target/aarch64-pc-windows-gnullvm/release/cys.exe target/aarch64-pc-windows-gnullvm/release/cysd.exe
```

⚠ **한계(정직)**: 크로스빌드 산출물은 PE 포맷·아키텍처는 검증되나(`file`로 PE32+ x86-64 /
Aarch64 확인) **실제 Windows에서 실행 검증은 불가**하다. 광범위 배포 전 Windows 머신에서
스모크테스트(설치→`cys status`) 권장.

## 3. GitHub 저장소 최초 설정 (1회)

자동 업데이트의 endpoint가 GitHub Releases이므로 **공개 repo가 있어야** 작동합니다.

```sh
# 1) GitHub에 공개 repo 생성 (이름은 cys-terminal 권장 — endpoint와 일치)
gh repo create <OWNER>/cys-terminal --public --source . --remote origin

# 2) tauri.conf.json의 updater.endpoints에서 OWNER를 실제 GitHub 사용자명으로 치환
#    "https://github.com/<OWNER>/cys-terminal/releases/latest/download/latest.json"
#    → 치환 후 반드시 앱을 다시 빌드해야 새 endpoint가 번들에 박힌다.

git push -u origin main
```

## 4. GitHub 릴리스

`latest.json`을 **항상 최신 릴리스에 포함**해야 updater가 찾습니다(endpoint가 `/releases/latest/`).

```sh
# ★태그 전 사전 게이트 4종 rc=0 필수 — §0-C (version-check · win-typecheck · pre-tag-ci-check · scan-pack-secrets)
# 태그
git tag -a v0.2.0 -m "cys 0.2.0 — 자비스 네이티브 기능 19건 + zero-setup 온보딩 + 자동 업데이트"

# gh CLI 릴리스 (드래프트로 먼저 검토 권장)
gh release create v0.2.0 --draft --title "cys 0.2.0" --notes-file docs/RELEASE_NOTES_0.2.0.md \
  dist-update/latest.json \
  dist-update/cys-0.2.0-macos-aarch64.app.tar.gz \
  dist-mac/cys-0.2.0-macos-arm64.dmg \
  dist-win/cys-0.2.0-windows-x64.msi \
  dist-win/cys-0.2.0-windows-arm64.msi \
  dist-win/cys-0.2.0-windows-x64.zip
```

### 자동 업데이트 동작 요약 (사용자 입장)
- 앱이 시작 시 + 6시간마다 `latest.json`을 조용히 확인 → 새 버전이면 상단 **Update** 버튼에 `!` 배지.
- 버튼 클릭 → 세션이 0개면 자동 설치, 세션이 있으면 "N개 종료됩니다" 확인 후 설치.
- 설치 = 새 `.app` 교체 + 구 데몬 SIGTERM + 앱 재시작(새 cysd 자동 기동). **재설치 불필요.**

⚠ **`git push`·`gh release`·`gh repo create`는 외부 발행(비가역)** — 오너 명시 승인 후에만 실행.
본 문서의 명령은 절차 기록일 뿐, 에이전트가 임의 실행하지 않는다.


---

## (이력) 체크리스트 — DMG 실사용자 경로 게이트 · 원작자 메인 페이지(cysinsight) 원격 검증

- [ ] **★★실사용자 경로 게이트 — DMG 2종 전부 exit 0 (2026-08-01 신설 · 필수 · 생략 불가)**

      ```sh
      # 로컬 빌드 산출물 이름은 dist-mac/cys-<V>-macos-{arm64,x64}.dmg 다
      # (발행본 이름 cys_<V>_{aarch64,x64}.dmg 와 다르다 — build-macos-signed.sh:221)
      bash scripts/verify-gatekeeper-user-path.sh dist-mac/cys-<V>-macos-arm64.dmg  # rc=0 필수
      bash scripts/verify-gatekeeper-user-path.sh dist-mac/cys-<V>-macos-x64.dmg    # rc=0 필수
      ```
      `spctl -a -vv` accepted **만으로는 부족하다**. 2026-08-01 사고에서 공증·staple 이 전부
      정상인 빌드가 사용자 머신에서 "손상되었기 때문에 열 수 없습니다"로 차단됐다 — 동봉
      Python 이 실행 중 번들 안에 `.pyc` 를 써서 **코드서명 봉인을 스스로 깨뜨렸고**,
      브라우저로 받은 사본에 붙은 `com.apple.quarantine` 때문에 첫 실행에서 Gatekeeper
      전체 재검증에 걸린 것이다. **이 게이트가 없으면 같은 사고가 그대로 재발한다.**
      · 실패 시 원인·수정 방향은 §1 「★실사용자 경로 게이트」 절 참조.
      · **exit 2(판정 불가)도 통과가 아니다** — 도구·자산 문제를 고치고 다시 돌려라.
      · 발행 후에는 원격 자산에 대고 한 번 더 돌린다:
        `bash scripts/verify-gatekeeper-user-path.sh --version <V> --arch aarch64` (x64 도)
      · **아키텍처별 머신에서 각자 돌리는 것이 정확하다**(교차 실행은 Rosetta 2 필요).
      · ★후처리 자동판(F2 · 2026-08-20): `scripts/release-postprocess.py` 가 draft 백업
        DMG 2종 = **발행될 실물 바이트**에 `release-gate-gatekeeper.sh` 실평가를 자동
        수행한다(네이티브 아키텍처 DMG 는 본 게이트 ⑥ 포함까지) — rc≠0(1·2 모두)이면
        postprocess 비영 종료·`--apply` 거부(fail-closed · §1 「★CI 자동판 게이트」 절 참조).
      · 복구 절차 주의 — **pre-SEAL 태그**(2026-08-20 SEAL 게이트 도입 이전 발행분)를 자산
        유실 복구 등으로 재후처리할 때는 ⑤ SEAL-2 정적 검사가 구조적으로 FAIL 한다: 이미
        발행·검증된 과거 실물 바이트에 한해 `--unsafe-skip-gatekeeper` 로 우회한다
        (LOUD 경고 감수 · 신규 발행에는 절대 사용 금지).
- [ ] **★메인 페이지(`/`) 원격 검증 — 6항목 전부 (S28 + 2026-07-29 오너 지시 ⓐⓑⓒ · 자동화 밖의 수동 게이트)**

      원 레인에서 이 격차의 형태는 "원격 검증기(`verify-release-remote.sh`)·조립기
      (`release-assemble.py`)가 `/downloads/` 만 보고 메인 페이지는 아예 보지 않는다"였다.
      **이 레인에는 그 두 스크립트가 존재하지 않았다**(실측) — 그래서 메인 페이지 검증은
      100% 수동 게이트였다. ★**2026-07-29 해소**: `scripts/verify-release-remote.py` 신설로
      6항목 전부를 기계로 돌린다(라이브 0.14.4 로 교정 — 6/6 PASS). 아래 수동 명령은
      그 스크립트가 못 돌 때의 폴백이자 판정 기준의 서술로 남긴다. 그래서 메인 밴드 누락은
      404 가 아니라 **무증상 구버전 배포**로 나타난다(구자산이 보존돼 링크는 200). v0.13.17 에서
      실제로 발생했다. 아래 4항목은 아무 스크립트도 대신해 주지 않으므로 **사람이 손으로 돌리고
      결과를 릴리스 노트에 붙인다.**

      선행: `cys-homepage/_round/dlhero/RELEASE_BUMP_CHECK.md` 5지점(링크 3개·S 슬롯 카피·
      용량·zip 전환 경로) 반영 → 업로드 → 그 다음 아래를 원격에 대고 실행한다.

      - [ ] ① **구버전 문자열 0** — `curl -s https://www.cysinsight.com/ | grep -c '<이전버전>'` → **0**
      - [ ] ② **신버전 문자열 9** — `curl -s https://www.cysinsight.com/ | grep -c '<신버전>'` → **9**
            (0 이면 미반영, 9 미만이면 부분 반영 = 밴드 일부가 구버전을 계속 배포한다)
      - [ ] ③ **용량 4토큰 개별 재계산** — ★버전 grep 이 **못 잡는 별개 축**이다.
            `sed 's/0.14.1/0.14.2/g'` 류 일괄 치환은 버전 9토큰만 바꾸고 페이지에 적힌 용량
            4토큰(예: 340MB·358MB·226MB·226MB)은 **그대로 남긴다** — 버전은 전부 새 값이라
            ①②는 통과하는데 표시 용량만 조용히 거짓이 된다. 자산 4종의 실제 바이트를
            `curl -sI` 의 `content-length` 로 **하나씩** 받아 페이지 표기와 대조하라:

            ```sh
            V=X.Y.Z; B=https://www.cysinsight.com/downloads
            for f in "cys_${V}_aarch64.dmg" "cys_${V}_x64.dmg" \
                     "cys_${V}_x64-setup.exe" "cys_${V}_x64-setup.zip"; do
              L=$(curl -sI "$B/$f" | awk 'tolower($1)=="content-length:"{print $2}' | tr -d '\r')
              printf '%-32s %s bytes  = %s MB\n' "$f" "$L" "$((L/1024/1024))"
            done
            ```
            4줄 전부 값이 나와야 하고(빈 값 = 자산 부재), MB 표기가 메인 페이지 4토큰과
            일치해야 한다. 불일치 1건이라도 있으면 **미완**이다.
            ★**단위는 MiB(1024) 버림**이다 — 십진 MB(1000)로 계산하면 정상 배포에서도 어긋난다
            (실측: 231,644,695B → 라이브 표기 **220MB** · 1000 기준이면 231 · 반올림이면 221).
      - [ ] ④ **버튼 href 4종 HEAD 200** — 페이지에 박힌 다운로드 링크를 눈이 아니라 HTTP 로 확인.
            ★**정적 `href="…"` 만 grep 하면 3개만 잡힌다** — zip 링크는 JS 가
            `setAttribute('href', '/downloads/…zip')` 로 붙이기 때문이다(실측). 양쪽을 봐야 4개다.
            아래 명령은 정적만 본다 → **`python3 scripts/verify-release-remote.py <V> <구버전>` 을 쓰라**
            (6항목 전부를 기계로 돌리고 JS 주입 링크까지 센다):

            ```sh
            curl -s https://www.cysinsight.com/ \
              | grep -oE 'href="[^"]*(dmg|setup\.exe|setup\.zip)"' | sed 's/href="//;s/"$//' \
              | sort -u | while read -r u; do
                  case "$u" in http*) U="$u";; *) U="https://www.cysinsight.com${u#.}";; esac
                  printf '%-70s %s\n' "$u" "$(curl -s -o /dev/null -w '%{http_code}' -I "$U")"
                done
            ```
            **4개 URL 이 나와야 하고 전부 200** 이어야 한다. 개수가 4 미만이면 밴드에 링크가
            빠진 것이고, 200 이 아니면 자산 경로가 어긋난 것이다.

      - [ ] ⑤ **Windows Defender/SmartScreen 안내 섹션 잔존** (2026-07-29 오너 지시 ⓐ·ⓒ)
            버전 범프 일괄 치환이 밴드 카피를 통째로 갈아끼우면 이 안내가 **조용히 사라진다**.
            사라지면 Windows 사용자가 SmartScreen 경고에서 그냥 이탈한다(설치 실패로 나타나지 않고
            **다운로드 후 침묵**으로 나타나므로 아무도 신고하지 않는다 — §2.6 관측 침묵과 같은 구조).

            ★**오너 체크리스트 정본 문언**(2026-07-29 · 이 문단이 그 문언의 리포 내 정본이다):
            > ⓐ **다운로드 페이지** Defender 안내 섹션 잔존 grep 확인
            > ⓑ SHA256SUMS 전 자산 갱신 · 누락 0
            > ⓒ **원격 검증(verify-release-remote)에 안내 섹션 출현 포함**

            ★2026-08-18 교정 — 검사 **대상 페이지와 방법이 둘 다 바뀌었다**. 종전 이 항목은
            루트(`/`)에서 낱말 grep 만 했다. 두 가지가 틀렸다:
              · **대상** — ⓐ 가 못박은 페이지는 루트가 아니라 **`/downloads/`** 다. 안내 섹션의
                실체는 그쪽의 `<section data-cys-release-marker="windows-defender-guidance-v2">`
                이고, 루트에는 밴드 카피의 낱말만 흩어져 있다
                (읽기 전용 실측 2026-08-18: 루트 마커 **0건** · `/downloads/` 마커 **1건**).
                즉 구 명령은 ⓐ 가 지목한 페이지를 **한 번도 받지 않았다** = ⓒ 미구현이었다.
              · **방법** — 낱말 grep 은 섹션이 통째로 사라져도 페이지 어딘가에 'Defender' 한
                낱말만 남아 있으면 통과한다(무증상 통과). 마커는 섹션 자체의 지문이라 섹션이
                빠지면 즉시 0이 되고, **개수까지 단언**하므로 중복 삽입(2건)도 잡는다.
            낱말 grep 은 **없애지 않고 보조 축으로 AND** 유지한다(회귀 감시 축을 줄이지 않는다).
            단, 낱말을 세기 전에 `data-cys-release-marker="…"` 속성을 **제거**한다 — 마커 문자열
            자체에 `defender` 가 들어 있어 제거하지 않으면 "마커가 있으면 낱말도 있다"가
            항진명제가 되고 보조 축이 무력해진다(실측으로 반증된 지점).

            ```sh
            # 정본 = 기계 검사. 6항목 전부를 한 번에 돌린다(⑤ 포함).
            python3 scripts/verify-release-remote.py <신버전> <구버전>
            #   ★구버전은 필수다(0.14.41 · U4 C4-⑦) — 빼면 원격 수신 전에 exit 2. 종전엔 ① 을 조용히
            #     빼고 분모 7 로 'N/7 PASS' 를 냈다. 두 인자를 준 정상 실행의 합격은 **8/8 PASS** 다.
            #     구버전이 정말 없을 때만 `--no-prev` 를 명시한다(요약 줄에 ①SKIP 병기).

            # 손으로 볼 때(참고용) — 대상은 루트가 아니라 /downloads/ 다.
            curl -s https://www.cysinsight.com/downloads/ \
              | grep -c 'data-cys-release-marker="windows-defender-guidance-v2"'
            ```
            마커가 **정확히 1건**이어야 한다. 0 이면 안내 섹션이 사라진 것이고 2 이상이면 중복
            삽입이다 — 어느 쪽이든 복원·정리할 때까지 **미완**이다. 보조 축(마커 속성을 뺀
            `/downloads/` 본문 낱말 ≥1 · 루트 낱말 ≥1)도 함께 만족해야 통과다
            (읽기 전용 실측 2026-08-18: 마커 1 · 다운로드 본문 낱말 4 · 루트 낱말 8 → 통과).

      - [ ] ⑥ **SHA256SUMS 신버전 전체 갱신 · 누락 0** (2026-07-29 오너 지시 ⓑ)
            ★파일명은 **`SHA256SUMS.txt`** 다(`SHA256SUMS` 는 404 — 실측). CI 가 아니라
            **`scripts/release-postprocess.py`** 가 CI 완주 후 로컬에서 만든다(자기 자신을 뺀
            **전 자산** — 배포 4종만이 아니다. v0.14.4 기준 13줄). 홈페이지에도 같은 파일이
            올라가야 하고, **구버전 줄이 섞여 있으면 안 된다**:
            ```sh
            V=X.Y.Z; B=https://www.cysinsight.com/downloads
            curl -s "$B/SHA256SUMS.txt" | tee /tmp/sums.txt
            test "$(grep -c "cys_${V}_" /tmp/sums.txt)" -ge 4   # 신버전 4줄 이상(전 자산 등재)
            # 구버전 자산 줄 0 (버전 없는 공용 자산 cys_aarch64.app.tar.gz 등은 정상)
            test "$(grep -cE "cys_[0-9]+\\.[0-9]+\\.[0-9]+_" /tmp/sums.txt)" \
               -eq "$(grep -c "cys_${V}_" /tmp/sums.txt)"
            # 실자산과 대조(다운로드 후 검증) — 표기만 갱신되고 바이트가 구버전인 사고 차단
            cd "$(mktemp -d)" && for f in "cys_${V}_aarch64.dmg" "cys_${V}_x64.dmg" \
                 "cys_${V}_x64-setup.exe" "cys_${V}_x64-setup.zip"; do curl -sO "$B/$f"; done
            curl -sO "$B/SHA256SUMS.txt" && shasum -a 256 -c SHA256SUMS.txt
            ```
            **4줄 전건 OK** 여야 한다. 1건이라도 FAILED 면 미완이다.
            ★2026-09-27(0.14.42 발행 준비) — 위 손 명령은 배포 4종만 본다. **정본인 기계 검사**
            (`verify-release-remote.py` ⑥)는 이제 SUMS 에 **기준 13종 전부**(버전 붙은 5종 =
            aarch64.dmg·x64.dmg·x64-setup.exe·x64-setup.exe.sig·x64-setup.zip + 무버전 8종 =
            업데이터 tar.gz 2·.sig 2·latest.json·pack.tar.gz·pack-manifest.json·.minisig)의 등재를
            요구한다 — 종전엔 나머지 9종이 SUMS·서버에서 통째로 빠져도 ⑥ 이 PASS 였다(오너 지시 ⓑ
            '전 자산 · 누락 0' 의 기계화). 기준 목록은 발행 전 관문 `release-verify.py` 의 정본과
            같은지 `--self-test` ⑥ⓖ 가 대조한다.
            ⚠**우리 포크(1.1.8 편입 시점)**: 위 13종은 원작자 발행 형상(DMG 2종 상시)이다. 우리 발행은 DMG 를 만들지 않고
            맥 레인이 선택(배포 zip — `release-verify.py` `MAC_ASSETS`)이라 이 기준이 우리 정본과 어긋난다(`--self-test` ⑥ⓖ
            적색 실측). 결정 전까지 이 ⑥ 판정을 우리 발행의 합격 근거로 쓰지 않는다(1.1.8 병합 판정 갈림 목록의 결정 대기 항목).

      ⚠**이 6항목이 보지 않는 것 — 2026-08-01 사고의 정확한 사각지대**: 여기서 자산을 받는
      수단은 `curl` 이다. **`curl` 로 받은 파일에는 `com.apple.quarantine` 이 붙지 않는다.**
      quarantine 이 없으면 첫 실행 시 Gatekeeper 전체 재검증 경로가 **아예 돌지 않아서**,
      봉인이 깨진 앱도 이 6항목을 전부 통과한다(v0.14.9 실측: 링크·용량·해시 전건 정상,
      그런데 사용자 설치 시 차단). 그래서 위 체크리스트의 **★★실사용자 경로 게이트**가
      **별도 필수 항목**이다 — 이 6항목이 그것을 대신하지 못한다.

      ⚠**남은 한계**: 이 검증은 홈페이지의 SOT(밴드 구조·카피 규약)를 알지 못하고 **결과만** 본다.
      "링크가 200이고 버전이 맞다"는 "밴드가 의도대로 구성됐다"를 뜻하지 않는다.
      구조 자체의 게이트는 홈페이지 리포(`cys-homepage/_round/dlhero/RELEASE_BUMP_CHECK.md`)에
      두는 것이 옳다 — 여기서는 배포 결과 게이트로 고정한다.

---

## (이력) 체크리스트 — 공증된 DMG 실기

- [ ] **★공증된 DMG 실기 — 상태: 실기 미검증 (0.14.43 E2 · 바이너리 릴리스 발행 뒤)** ⚠원작자 공증 레인 항목이다 — 우리 포크는 공증 DMG 를 발행하지 않는다(자체서명 맥 레인에서는 같은 확인을 설치된 앱의 cysd 로 한다). 공증된 DMG 의 cysd 에서 `control.hw` 의 `npu.status` 가 `ok` 인가(강화 런타임에서 시스템 dylib dlopen — 실패해도 데몬은 뜬다: `unavailable` + `reason`).

---

## (이력) CI 이전 수동 팩 발행 절차(1.1.7 이하 앱 배지 확인 포함 · 현행 = docs/RELEASE.md §0-P `pack-v*` 태그 레인)

### 팩-온리 발행 절차 (현행 수동 — CI 자동화는 Phase2 별도 과제)

pack_version은 빌드 시점 `CARGO_PKG_VERSION`에 용접돼 있어(`cys.rs build_pack_manifest_value`)
팩만 발행해도 **버전 범프 + cys 재빌드**가 필요하다(§0 전 위치 갱신 — version-check.sh 통과).

1. 버전 범프(§0) → `cargo build --release --bin cys` (Tauri 빌드 불요 — cys 단독).
2. pack 3종 생성 — release.yml `pack-artifacts` 잡과 동일 파라미터(스캔 게이트 2종 선행 포함):
   `cys pack-manifest --key-id … --signed-at … --expires-at … --min-binary-version $PACK_MIN_BINARY > pack-manifest.json`
   (`$PACK_MIN_BINARY` = release.yml `PACK_MIN_BINARY` env 와 **동일값** — 현행 1.1.7(2026-09-29 상향 · phoenix G2 `reinject --check --ack-only` · 그 전 1.0.0 = 2026-09-16 · 아래 근거 항목). 수기 리터럴 금지:
   두 레인 값보다 낮게 서명하면 아래 불변 규칙이 막은 스큐가 이 수동 문으로 재개방된다.)
   → 결정론 tar(`--mtime` 고정) → minisign 서명.
3. **직전 릴리스의 latest.json + 바이너리 업데이트 자산을 그대로 동봉**해 새 릴리스를 만들고
   `--latest`로 마킹한다(바이너리 버전은 그대로 → 바이너리 배지 안 뜸).
4. 검증: 앱 배지 = `↻`(무중단 팩)만 표시, `!`(바이너리) 미표시. 구버전(min_binary 하한 미만) 기기는
   "바이너리 업데이트 필요" 안내가 뜨는 것이 정상(하한 게이트 동작).
