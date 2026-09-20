# 구판(1.0.2) 맥 갱신 레인 — 자산 이름·서명 형식 실측표 + VM 실기 절차

> TICKET=v110-darwin-update · master 판정 **B 조건부 채택**(2026-09-20 · `[master#1c38c0ab]`).
> 1.1 부터 맥은 우리 경로(zip + sha256·CDHash)로 갱신한다. 그러나 **이미 깔린 1.0.2 는 그 코드를
> 모른다** — `tauri-plugin-updater` 로만 갱신한다. 그래서 같은 태그에 구판이 먹을 수 있는 자산을
> 함께 올린다. 아래 표의 값은 **플러그인 소스 실측**이다(추론 아님).

측정 대상: `~/.cargo/registry/src/index.crates.io-*/tauri-plugin-updater-2.10.1/src/updater.rs`
(우리 `src-tauri/Cargo.toml` 이 고정한 그 판본 — 1.0.2 설치본이 품고 나간 코드와 같은 판).

## 1. 구판이 요구하는 것 — 실측표

| 축 | 요구값 | 실측 근거(file:line) |
|---|---|---|
| platforms 행 이름 | `darwin-aarch64` (인텔은 `darwin-x86_64`) | `updater.rs:1329`(os=`darwin`) + `1344`(arch=`aarch64`) |
| 행 필수 칸 | `url`, `signature` **둘 다** | `ReleaseManifestPlatform` `updater.rs:71-77` · `RemoteReleaseInner` 가 `#[serde(untagged)]` (`79-85`) → 한 행만 빠져도 **platforms 전체 역직렬화 실패**(윈도까지 죽는다) |
| 판번 게이트 | `release.version > current_version`(semver) | `updater.rs:532` |
| 내려받는 것 | `url` 이 가리키는 바이트 그대로 | `updater.rs:712` 직전 |
| 서명 검증 대상 | **받은 파일 전체 바이트** | `verify_signature(&buffer, …)` `updater.rs:712` |
| `signature` 칸의 값 | **`.sig` 파일 전문(= minisign 서명문을 base64 로 감싼 문자열)** — base64 디코드 → minisign `Signature::decode` | `verify_signature` `1453-1463` + `base64_to_string` `1465-1471` |
| pubkey | `tauri.conf.json` `plugins.updater.pubkey`(base64 감싼 minisign 공개키) | 같은 함수 `1455-1456` |
| 맥 압축 형식 | **gzip + tar 만**(zip 불가) | `install_inner` `updater.rs:1217` → `GzDecoder` + `tar::Archive` `1232-1233` |
| tar 내부 구조 | 최상위 구성요소 **정확히 1개** — 첫 구성요소는 **버려진다** | `entry.path()?.iter().skip(1)` `updater.rs:1238` |
| 설치 자리 | 실행 중 번들 자리(`extract_path`) — tar 최상위 **이름은 무시** | `1256`·`1302` + `extract_path_from_executable` `319-323` |
| 권한 부족 시 | AppleScript 로 `rm -rf '<app>' && mv …`(삭제가 먼저 = 이동 실패 시 앱 전소) | `1270-1277` |

### 여기서 따라오는 것
- 구판은 우리 **zip 을 절대 못 푼다** — 같은 태그에 `.app.tar.gz` 를 따로 올려야 한다.
- tar 의 최상위 이름은 아무 의미가 없다(버려진다). 따라서 구판 맥은 갱신 뒤에도 **설치본 이름을 유지**한다
  (`/Applications/cys.app` 에 깔린 1.0.2 는 1.1 로 올라가도 `cys.app` 그대로다).
- 자산 **파일 이름**은 플러그인이 보지 않는다. 우리 발행 파이프라인이 본다 —
  `scripts/release-postprocess.py` 의 `MAC_LANE` = `cysr_aarch64.app.tar.gz` / `…​.sig`(+ x64 · DMG 2종).
  그래서 `scripts/make-darwin-updater-tarball.sh` 가 그 이름으로 낸다(시험이 두 곳의 이름을 대조한다).

## 2. 생성 절차(로컬·CI 공통)

```sh
# ① 서명·공증된 .app 이 있는 상태에서(build-macos-signed.sh 산출 또는 zip 해제본)
sh scripts/make-darwin-updater-tarball.sh --app <…>/cysr.app --out dist-mac --arch aarch64
#   키 없음 → rc 3 + cysr_aarch64.app.tar.gz.sig.MISSING (발행 금지 표식)
#   키 있음 → cysr_aarch64.app.tar.gz + .sig

# ② latest.json 맥 행(우리 1.1 경로용 zip 행)
python3 scripts/make-darwin-update-row.py --version 1.1.0 \
    --zip dist-mac/cysr-macos-arm64-v1.1.0.zip --app <…>/cysr.app --merge dist-update/latest.json
```

⚠ **두 행이 한 태그에 공존한다**: `platforms["darwin-aarch64"]` 는 하나뿐이므로, 구판이 먹을 것을
그 행에 둔다 — 즉 **행의 `url`·`signature` 는 tar.gz 쪽**이고, 1.1 앱이 쓰는 `sha256`·`size`·`cdhash` 는
**zip 쪽**이다. 1.1 앱은 `signature` 를 읽지 않고, 구판은 `sha256`·`size`·`cdhash` 를 읽지 않는다
(`ReleaseManifestPlatform` 은 모르는 칸을 버린다 — `serde` 기본).
👉 그래서 행을 합칠 때 **url 은 tar.gz**, **zip 주소는 별도 칸(`zip_url`)** 으로 둬야 한다.
   이 분기는 코드 변경이 필요하다(현재 `macupdate::pick_darwin_asset` 은 `url` 을 zip 으로 읽는다) —
   **VM 게이트 통과 후 B 를 확정할 때 함께 집행할 잔여 1건**이다(아래 §4).

## 3. VM 실기 절차서 (master 집행 · 1쪽)

전제: Tart 맥 VM `jarvis-clean-vanilla`(깨끗한 판본 핀 — 개발기 dry-run 은 거짓 초록이라 쓰지 않는다).

| 단계 | 명령/동작 | 합격 판정(실측) |
|---|---|---|
| 0 | `tart clone jarvis-clean-vanilla vm-darwin-lane && tart run vm-darwin-lane` | 부팅 · 개발자도구 없음 확인(`xcode-select -p` 실패해도 정상) |
| 1 | VM 안에 **1.0.2 설치**(발행본 zip 또는 DMG를 그대로) | 앱 기동 · 헤더 판번 `v1.0.2` |
| 2 | 1.0.2 를 한 번 띄워 `~/.cys` 초기화 완료 | 데몬 pid 표시 · 좌석 1개 이상 |
| 3 | 시험용 latest.json 을 VM 이 보게 한다 — `CYS_UPDATE_MANIFEST_URL` 로 1.1 매니페스트 지정 | 앱 로그에 그 주소 조회 기록 |
| 4 | 앱 내 **Update** 클릭 | 다운로드 → 설치 → 재시작. 오류 토스트 0 |
| 5 | 재기동 후 **헤더 판번 = 1.1.0** | 좌상단 `v1.1.0` · `daemon v1.1.0` |
| 6 | Gatekeeper — `spctl -a -vv /Applications/cys.app` · 첫 실행 경고 유무 | 자체서명(cys-local)이라 `rejected` 가 **정상**(`cysr-mac-asset-two-expected-non-defects`). 앱이 **열리는지**가 판정이고 `spctl` 값은 판정 아님 |
| 7 | 격리 속성 — `xattr -p com.apple.quarantine /Applications/cys.app` | 없음(`No such xattr`) 또는 있어도 앱이 열리면 통과 |
| 8 | 세션 복원 — 재시작 전 좌석이 돌아오는가 | 좌석 수·역할 일치 |

- **전부 통과 = B 확정**(구판 레인 자산을 같은 태그에 발행).
- **한 칸이라도 실패 = C**: 맥 행을 1.1 배포 이후로 미루고, 1.0.2 맥은 **설치 한 줄 재실행으로 이주**
  (안내 문구는 설치 사이트 그대로). 실패 칸·출력을 그대로 기록해 올린다.
- ⛔개발기(이 맥)에서 4~8 단계를 대신 재지 마라 — 이미 1.1 코드가 깔린 기계는 「구판이 먹는가」를
  원리적으로 못 잰다(측정 대상이 다르다).

## 4. 잔여 — B 확정 시 함께 집행할 1건

`platforms["darwin-aarch64"]` 한 행이 **두 소비자**(구판=tar.gz·1.1=zip)를 먹여야 하므로:
- `url` = tar.gz(구판 필수) · `signature` = 그 tar.gz 의 .sig
- zip 주소는 새 칸 `zip_url` 로 두고 `macupdate::pick_darwin_asset` 이 `zip_url` 우선·없으면 `url` 로 읽게 한다.
- 시험: 두 소비자 칸이 서로를 덮지 않는다(구판 칸만 있는 매니페스트 = 1.1 이 zip 을 못 찾아 **거부**해야 한다 — 조용히 tar.gz 를 받지 않는다).

이 변경은 **VM 게이트 결과가 B 로 확정된 뒤**에 한다. C 로 가면 필요 없는 칸이기 때문이다.
