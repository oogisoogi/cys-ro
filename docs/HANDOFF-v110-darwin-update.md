# HANDOFF — 맥 앱 내 업데이트(B7) · 데몬 교체 안내(B15) · 재시작 잔재 정리(B17)

> TICKET=v110-darwin-update · 브랜치 `fix/v110-darwin-update`(기준 `d22f7f6a` = fix/v110-app) · 2026-09-20

## 1. 끝난 것 (실측 근거 포함)

| 항목 | 무엇을 했나 | 어디 |
|---|---|---|
| B7 판정 | 맥 자산 행 해석·판번/build_id 게이트·검증 5축의 **순수 판정** | `src-tauri/src/macupdate.rs` (단위시험 14건) |
| B7 집행 | latest.json 조회 → 다운로드(진행률) → 크기·sha256 → `ditto` 해제 → `codesign --verify` → CDHash → mv 2회 원자 교체 → 재시작 안내 | `src-tauri/src/main.rs` `install_update_darwin` |
| B7 분기 | `check_update`·`install_update` 가 **cfg 로 기판을 가른다**(맥=우리 경로·그 밖=플러그인) | 같은 파일, 두 함수 머리 |
| B7 매니페스트 | darwin 행 생성·병합기(sha256·size·cdhash 실측 · signature 키 강제) | `scripts/make-darwin-update-row.py` (시험 8건) |
| B15 | 교체 완료 → 「눌러서 재시작」 지속 토스트 → `restart_after_update`(drain→마커→구 데몬 종료→재시작) | `ui/src/main.ts`, `main.rs` |
| B15 | 헤더에 **데몬 판번 상시 표시**(종전엔 스큐일 때만) | `ui/src/headerlabels.ts` `daemonInfoLabel` |
| B15 | 자동 교대 보류 시 **사유 표기**(세션 N개/확인 실패/기타) | `holdReasonText` + `checkVersionSkew` |
| B17 | 복원 완료(restore-progress done) 직후 **1회** 옛 자리(`exited=true`) 스윕 | `ui/src/exitedsweep.ts` + `refreshPaneTitles` 배선 |

측정된 사실(도구 출력):
- 발행본 `latest.json`(v1.0.2)에 **darwin 행 0건** · 릴리스에는 `cysr-macos-arm64-v1.0.2.zip` **471,899,457 B** 가 이미 있다(2026-09-20 `curl` 실측).
- `tauri-plugin-updater` 2.10.1 의 맥 설치 경로는 **tar.gz 전용**(`updater.rs:1233`) — 우리 zip 을 못 푼다. 그래서 맥은 자체 경로.
- 판번 정본은 `src-tauri/tauri.conf.json`(1.0.2) + `src-tauri/Cargo.toml`(1.0.2) + 루트 `Cargo.toml`(1.0.2). **브리프의 「tauri.conf.json 은 0.14.37」은 이 기준 커밋에서는 사실이 아니다**(이미 1.0.2로 정렬돼 있다). 판번은 이 티켓에서 바꾸지 않았다.

## 1-b. master 판정 B(2026-09-20 `[master#1c38c0ab]`) 로 추가된 것

| 항목 | 무엇을 했나 | 어디 |
|---|---|---|
| 구판 레인 자산 | 1.0.2 가 먹는 `cysr_<arch>.app.tar.gz`(+`.sig`) 생성 — 최상위 1개 강제 · AppleDouble 거부 · 키 없으면 rc 3 + 자리표시 | `scripts/make-darwin-updater-tarball.sh` (시험 5건) |
| 실측표 | 구판이 요구하는 자산 이름·서명 형식·tar 구조를 `updater.rs` 줄번호와 함께 표로 | `docs/DARWIN-UPDATER-LEGACY-LANE.md` §1 |
| VM 절차서 | Tart `jarvis-clean-vanilla` 8단계 · 합격 판정 · 실패 시 C 경로 | 같은 문서 §3 |

★그 문서 §4 = **B 확정 시 함께 집행할 잔여 1건**(한 행이 두 소비자를 먹여야 하는 충돌 — `zip_url` 분리).
  이것은 master 결정 사항이라 이 티켓에서 집행하지 않았다.

## 2. 미완 · 다음 사람이 이어받을 것

0. **한 행 두 소비자 충돌(B 확정 시 필수)** — `platforms["darwin-aarch64"].url` 은 구판이 받는 주소다.
   1.1 앱은 지금 그 `url` 을 zip 으로 읽으므로, 구판 레인을 함께 올리면 **둘 중 하나가 틀린 것을 받는다**.
   처방 = `zip_url` 칸 분리(1.1 은 `zip_url` 우선·없으면 거부). 상세 = `docs/DARWIN-UPDATER-LEGACY-LANE.md` §4.
1. **B16 배치 규칙 미편입** — `fix/v110-panetitle` 브랜치가 없다(`git branch -a` 실측). `ui/src/exitedsweep.ts` 의
   `applyB16Placement()` 가 **이음매**로 남아 있고 지금은 `{applied:false, reason:…}` 를 돌려주며 호출부가 로그를 남긴다.
   그 브랜치가 오면 이 함수 본문만 채우면 된다(호출부는 그대로).
2. **실기 교체 미실행** — 브리프의 금지선대로 이 맥에서 실제 교체를 돌리지 않았다. 격리 경로 2개가 준비돼 있다:
   `CYS_UPDATE_APP_PATH=<시험용 번들>` · `CYS_UPDATE_DRY_RUN=1`(검증까지만·교체 안 함, UI 에 「드라이런」 토스트).
   다음 라운드에서 이 두 env 로 **1회 실사격**(가짜 zip 으로 5종 실패 + 진짜 zip 으로 성공)이 필요하다.
3. **맥 로컬 전체 빌드(`build-macos-signed.sh`) 미실행** — `runtime/`(439MB: python·node·git) 조립 + 서명 + zip 까지
   가는 경로라 이 티켓의 상한 안에서 돌리지 못했다. 대신 `cargo check/test -p cys-app` 이 초록이고 사이드카
   빌드(`bundle-prep.sh`)는 rc 0 으로 완주했다(그 스크립트가 `cargo build --release --bin cys --bin cysd` 를 포함).
4. **`release-verify.py` · `release-postprocess.py` 의 맥 레인 규칙은 아직 「tar.gz 4종」 기준** — 우리가 zip 으로
   발행하면 그 검사가 「반쪽(판정 불가·rc 2)」으로 읽는다. 발행 파이프라인을 zip 레인으로 넓히는 것은 별도 티켓.

## 3. 함정 (다음 사람이 반드시 알아야 할 것)

- 🔴 **darwin 행의 `signature` 키는 비워서라도 반드시 넣는다.** `ReleaseManifestPlatform` 이 `url`+`signature` 를
  요구하고 `RemoteReleaseInner` 가 `#[serde(untagged)]` 라(`updater.rs:71-85`), 한 행이라도 그 키가 없으면
  **platforms 전체 역직렬화가 실패해 윈도 사용자의 업데이트까지 죽는다.** 생성기·시험이 이것을 못박는다.
- 🔴 **구 맥 클라이언트(1.0.2) 회귀 위험** — darwin 행이 latest.json 에 올라가는 순간, 아직 1.0.2 인 맥은
  플러그인 경로로 그 행을 집어 **471MB zip 을 받고 minisign/tar 에서 실패**한다(업데이트가 「없음」에서
  「오류」로 바뀐다). 이 티켓은 그것을 고칠 수 없다(구판 코드는 이미 배포돼 있다). 발행 시 master 판단 필요 —
  선택지는 ⑴그대로 발행(맥 구판은 1회 오류 후 수동 설치 안내) ⑵같은 태그에 `cysr_aarch64.app.tar.gz`+`.sig` 를
  **함께** 올려 구판도 성립시키기 ⑶맥 행을 1.1 배포 이후로 미루기.
- `codesign -dvvv` 의 출력은 **stderr** 다. stdout 으로 읽으면 CDHash 가 언제나 빈 값이 돼 상시 실패한다.
- 백업은 교체 대상과 **같은 부모 폴더**에 둔다(다른 볼륨이면 rename 이 복사가 되고 되돌리기 전제가 깨진다).
- `#[cfg(target_os = …)]` 를 **최상위 아이템에 걸지 마라** — `blockb_no_new_file_level_cfg_gated_items` 핀이 막는다.
  함수는 모든 기판에서 컴파일되게 두고 본문(또는 호출부)에서 `cfg!()` 로 갈라라. 이 티켓도 처음에 그 핀에 걸렸다.
- `gui_spec_w3_sites_consume_sealed_builder` 핀의 조준을 **이 티켓에서 옮겼다**: `install_update`(이제 얇은
  분기 함수) → `install_update_plugin` + `restart_after_update`. 옛 조준을 그대로 뒀으면 빈 dispatcher 를 재는
  상시 초록이 됐을 자리다. 뮤턴트 `m7-w3-seal` 이 그 핀이 아직 무는지 확인한다.

## 4. 재현 명령

```sh
cd ~/axdev/.wt/cys-v110-darwin-update
sh scripts/bundle-prep.sh                     # 사이드카·UI (최초 1회 · rc 0)
cargo test -p cys-app                         # 앱 크레이트 전건(맥 업데이트 판정 14건 포함)
bun test ui/src                               # UI 전건
python3 scripts/tests/test_darwin_update_row.py      # latest.json 맥 행 생성기
python3 scripts/tests/test_darwin_updater_tarball.py # 구판 레인 tar.gz 생성기
python3 scripts/tests/mutants-darwin-update.py    # 뮤턴트 배터리(새 축이 무는지)
```

드라이런 실사격(다음 라운드):

```sh
CYS_UPDATE_DRY_RUN=1 CYS_UPDATE_MANIFEST_URL=file:///…/latest.json open -a cysr   # 교체 없이 검증만
```
