# 서명 키 분리·회전 런북 — 키 브리지 (1.0.0 → 1.0.1)

> TICKET=key-bridge · 2026-09-15 작성 · 근거 = 설치 연구 v2 결정 ⑶(팩 서명 키 ↔ 업데이터 키 분리 + 회전 절차)
> ⚠ 이 문서의 **키 생성·CI 비밀 등록·실키 커밋·발행은 master 집행**이다. 워커·에이전트가 대신 실행하지 않는다.
> 무비용 원칙: minisign(tauri signer)만 쓴다. 유료 인증서 0.

## 0. 한 문단 요약

지금은 **한 개의 키**(key id `54FBA04AD0E0F49D`, 이하 「옛 키」)가 두 가지를 서명한다 — ① 앱 내 업데이트 자산(tauri updater) ② 팩 매니페스트(`pack-manifest.json.minisig`). 이 키를 둘로 가른다: 업데이터용 **A2**, 팩용 **P2**. 이미 설치된 앱은 **자기 바이너리에 박힌 공개키로만** 다음 판을 검증하므로, 키를 한 번에 바꾸면 전 사용자의 업데이트가 끊긴다. 그래서 두 판에 걸쳐 건넌다:

| 판 | 바이너리에 박힌 업데이터 공개키 | 업데이터 자산 서명 키 | 팩 키링(바이너리 내장) | 팩 서명 키 |
|---|---|---|---|---|
| 0.14.x (현행 설치본) | 옛 키 | 옛 키 | 옛 키 | 옛 키 |
| **1.0.0 (브리지 · 오늘)** | **A2** | **옛 키** | **옛 키 + P2** | **옛 키** |
| 1.0.1 (회전 완료) | A2 | **A2** | 옛 키 + P2 | **P2** |
| 회전 정리 판(1.0.2 이후) | A2 | A2 | **P2만** | P2 |

- 0.14.x 앱 → 1.0.0: 옛 키 서명이라 받는다. 받은 순간 앱에 A2 가 박힌다.
- 1.0.0 앱 → 1.0.1: A2 서명이라 받는다.
- ⚠ **1.0.0 을 건너뛴 앱은 1.0.1 을 받지 못한다**(0.14.x 는 A2 서명을 거부한다 — `src/packsig.rs` 시험 `updater_bridge_old_signed_accepted_by_old_rejected_by_a2` 의 대조 판정). 앱 업데이터는 항상 **latest 한 판**만 보므로, 1.0.1 발행 뒤에 처음 업데이트를 누른 0.14.x 앱은 끊긴다. 대처는 §6.

## 1. 이번 판(브리지)에서 코드가 바뀐 것

1. **팩 키링이 업데이터 공개키에서 떨어졌다.** 종전 `build.rs` 는 `tauri.conf.json` 의 updater pubkey 를 `cysjavis-pack/trusted-keys.json` 의 빈 `pubkey` 칸에 주입했다. 업데이터 키를 A2 로 바꾸면 그 주입이 팩 키 항목(`54FB…`)에 **A2 공개키**를 넣어, 옛 키로 서명한 팩이 전부 거부됐을 것이다. 이제 공개키는 `trusted-keys.json` 에 명시돼 있고 주입은 없다. 빈 pubkey·형식이 틀린 key_id 는 빌드를 죽인다.
2. **시험이 키링 정합을 잰다** (`cargo test --lib packsig`): 모든 항목의 key_id == 공개키에서 파생한 key_id · 내장 키링 == 파일 원문(주입 재발 검출) · 업데이터 브리지 3판정 · 팩 이중 신뢰.
3. **발행 게이트** (`scripts/release-verify.py` 7-b): 업데이터 서명(.sig) **전부**의 key id 가 **직전 공개 판 태그의 `tauri.conf.json` pubkey** key id 와 같아야 발행된다. `release-publish.yml` 두 잡이 직전 판 태그의 conf 를 꺼내 `--prev-tauri-conf` 로 넘긴다. 1.0.0 을 A2 로 서명하는 실수도, 1.0.1 을 옛 키로 서명하는 실수도 여기서 죽는다.
   - 사거리: key id 대조까지다. 서명의 암호학적 진위는 CI 실서명 경로와 앱 업데이터가 진다.
4. **공개키 기입 도구** `scripts/key-bridge-install.py`: A2·P2 공개키 파일을 받아 두 파일을 한 번에 고친다(비밀키는 받지 않는다). 거부 조건은 스크립트 머리말 참조 — 거부되면 파일은 바뀌지 않는다.

## 2. 1.0.0(브리지) 준비 — master 집행 순서

1. **키쌍 2개 생성**(로컬 · 오프라인 권장)
   ```sh
   bunx @tauri-apps/cli@2.11.4 signer generate -w ~/.tauri/cys-updater-A2.key
   bunx @tauri-apps/cli@2.11.4 signer generate -w ~/.tauri/cys-pack-P2.key
   ```
   - 암호: 현행 CI 는 `TAURI_SIGNING_PRIVATE_KEY_PASSWORD: ''` 로 돈다. 암호를 걸면 1.0.1 에서 해당 비밀도 함께 등록해야 한다(§4).
   - 비밀키 백업 = 암호 관리자 + 오프라인 사본. git 커밋 금지. 분실 = 그 키로 서명하는 채널 영구 중단.
2. **공개키 기입**(저장소 루트)
   ```sh
   python3 scripts/key-bridge-install.py \
     --updater-pub ~/.tauri/cys-updater-A2.key.pub \
     --pack-pub ~/.tauri/cys-pack-P2.key.pub \
     --pack-not-after 2030-01-01T00:00:00Z --dry-run      # 판정만
   python3 scripts/key-bridge-install.py ...(같은 인자, --dry-run 없이)
   ```
3. **검증**
   ```sh
   cargo test --lib packsig                      # key_id↔pubkey · 이중 신뢰 · 브리지 판정
   python3 scripts/tests/test_release_verify.py
   python3 scripts/tests/test_key_bridge_install.py
   git diff src-tauri/tauri.conf.json cysjavis-pack/trusted-keys.json   # 두 파일만 바뀌었는지
   ```
4. **CI 비밀은 건드리지 않는다.** `TAURI_SIGNING_PRIVATE_KEY` = 옛 키 그대로. 워크플로의 팩 `KEY_ID` 도 `54FBA04AD0E0F49D` 그대로.
5. 빌드 로그에 tauri CLI 의 경고 「The updater secret key from `TAURI_SIGNING_PRIVATE_KEY` does not match the public key from `plugins > updater > pubkey`」가 **뜨는 것이 정상**이다(브리지 판의 정의 그 자체). tauri-cli 2.11.4 `crates/tauri-cli/src/bundle.rs` 에서 이 불일치는 `log::warn!` 뿐이고 빌드를 멈추지 않는다(2026-09-15 소스 확인).
   - ⚠ 반대로 **1.0.1 빌드에서 이 경고가 뜨면 사고다**(A2 비밀로 바꾸지 않았다는 뜻).
6. 발행 → `release-publish.yml` 7-b 가 「서명 key id(옛 키) == 직전 판(0.14.x) conf pubkey key id(옛 키)」를 확인한다.

## 3. 1.0.0 발행 뒤 확인

- 0.14.x 설치본에서 앱 내 Update → 1.0.0 설치 성공.
- 1.0.0 설치본의 팩 갱신이 옛 키 서명 팩을 계속 받는지(`cys pack-update --dry-run`).

## 4. 1.0.1(회전 완료) — master 집행 순서

1. **CI 비밀 교체/추가**
   - `TAURI_SIGNING_PRIVATE_KEY` ← A2 비밀키(업데이터 서명). 옛 키 비밀은 저장소 비밀에서 내리되 **오프라인 백업은 유지**(§6 긴급 경로용).
   - 팩 서명: 현재 `release.yml`·`pack-release.yml` 의 「Sign pack-manifest.json」 단계는 `TAURI_SIGNING_PRIVATE_KEY` 를 **재사용**한다. 이 판에서 팩 전용 비밀(예: `CYS_PACK_SIGNING_PRIVATE_KEY` ← P2)로 갈라야 한다. **그 워크플로 수정은 이 티켓 범위 밖**(1.0.1 티켓에서 한다).
   - 두 워크플로의 팩 `KEY_ID` ← P2 key id.
2. 빌드 로그에 위 tauri 불일치 경고가 **없어야** 한다.
3. 발행 게이트 7-b 가 「서명 key id(A2) == 직전 판(1.0.0) conf pubkey key id(A2)」를 확인한다. `release.yml` 의 「Verify signed pack end-to-end」 단계가 P2 서명 팩을 새 바이너리(키링 = 옛 키 + P2)로 검증한다.
4. ⚠ **팩 채널의 구멍**: 0.14.x 바이너리는 P2 를 모른다. 1.0.1 부터 팩을 P2 로 서명하면 **아직 1.0.0 으로 올리지 않은 앱은 팩 갱신을 받지 못한다**(서명 단계 거부 · fail-closed라 설치 손상은 없다). 앱 업데이트를 먼저 받으면 풀린다. 1.0.1 을 서두르지 않고 1.0.0 보급률을 본 뒤 전환하는 것을 권한다(판단 = master/박사님).

## 5. 회전 정리(옛 키 제거) — 1.0.1 이후 별도 판

1. `cysjavis-pack/trusted-keys.json` 에서 `54FBA04AD0E0F49D` 항목을 **삭제**하거나 `revoked_key_ids` 에 추가한다(유출 의심이면 revoked — 즉시 거부 · 아니면 삭제로 충분).
2. `cargo test --lib packsig` — `embedded_keyring_parses_with_bootstrap_pubkey` 시험이 옛 key id 를 찾으므로 **그 시험의 기준 key id 를 P2 로 바꾸는 것이 이 단계의 일부**다.
3. 이 판을 받은 바이너리는 옛 키 서명 팩을 거부한다 — 옛 키로 서명한 팩이 더 이상 latest 가 아님을 먼저 확인한다.

## 6. 끊긴 사용자 대처(1.0.0 을 건너뛴 0.14.x)

- 증상: 앱 내 Update 가 서명 검증 실패로 멈춘다.
- 대처 A(권장): 설치본 수동 재설치(다운로드 페이지의 최신 설치기). 설치기는 업데이터 서명 검증을 거치지 않는다.
- 대처 B: 1.0.1 발행 전에 1.0.0 보급률을 확인하고, 전환 시점을 늦춘다(§4-4 와 같은 판단).

## 7. 판정 근거(재현 명령)

| 주장 | 확인 방법 |
|---|---|
| 팩 키링이 업데이터 pubkey 와 독립 | `cargo test --lib packsig embedded_keyring_is_trusted_keys_file_verbatim` |
| key_id 오기 검출 | `cargo test --lib packsig embedded_keyring_key_ids_match_pubkeys` |
| 브리지 3판정·팩 이중 신뢰 | `cargo test --lib packsig updater_bridge` · `pack_dual_trust` |
| 잘못된 키로 서명한 판 발행 거부 | `python3 scripts/tests/test_release_verify.py KeyBridgeGateTests` |
| 기입 도구 거부 = 무변경 | `python3 scripts/tests/test_key_bridge_install.py` |
