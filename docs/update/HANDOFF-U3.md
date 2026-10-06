# HANDOFF-U3 — 1.1.8 데몬 자동 갱신 U3(발행 쪽 · 스크립트·CI·게이트) · TICKET=cysr-118-u3-publish

- 좌석 = worker surface:1293(294 118u3) · 계정2 · Opus · 가지 `u3/publish-118`(off `7e7aa5da`) · **push 0 · 실키 0 · 게시 0 · 설치기 빌드 0**
- 브리프 = [master#1b3b04af] 2026-10-06 09:21:02(원장 submitted=yes 대조) · 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md` 4판
- 서식 소비 = U1 가지 `u1/autoupdate-118` **커밋본 `102859e3`**(작업트리의 2판 진행분은 미커밋이라 쓰지 않았다 · 2판 추가 필수 칸 — features·bundled_pack digest·맥 cdhash/dr_pin_id·윈 a2_sig_url — 은 생성기·게이트가 **이미 낸다**). U1 은 이 가지에 머지하지 않았다 — 별도 작업트리(scratch `u1ref`)에서 디버그 `cys` 를 빌드해 `update-verify` 왕복에만 썼다.
- 이 문서의 시각·수는 전부 도구 출력(git 커밋 시각 · `date` · 시험 결과 줄)에서 옮겼다.

## §0 델타(먼저 읽을 것)
- 끝난 것 = 브리프 §2 의 1~9 전부(아래 §5 표) · 커밋 6개(`329c1ae5`·`09a79e7f`·`db2f7cbf`·`2cfb9117`·`0ea451cc` + 이 문서).
- 【결정필요】 3건 = §3 ①②③(전부 master 결정 범위 · 박사님 결정 항목 0).
- **설계·U2 에 알릴 실측 2건**: ⑴ 맥 DR 핀 대조의 `codesign -R` 문법 — 설계 §3-6 ② 의 `-R='=designated => identifier … and certificate leaf = H"…"'` 는 이 macOS 에서 **문법 오류**(`line 1:1: unexpected token: =`)이고 `-R='identifier "com.cysjavis.terminal" and certificate leaf = H"a426…b18d"'` 가 맞다(실 `/Applications/cys.app` 양성 rc 0 · 엉뚱한 leaf 음성 rc 3). ⑵ **CDHash 가 읽힌다고 서명된 번들이 아니다** — 애플 실리콘 링커가 Mach-O 를 자동 서명해서 봉인 안 된 번들도 `codesign -dvvv` 가 CDHash 를 낸다(실측) → 수집기는 `--verify --deep --strict` + DR 핀까지 본다. U2 의 S2 검증 3겹도 같은 함정이 있는지 대조 필요.
- **U2 에 넘기는 서식 1건**: 윈 행 `payload_manifest[{path,size,sha256}]` 를 본문에 싣는다(경로 = `/` 구분 상대 · 정렬 · 대소문자 무시 중복 거부). U1 `Asset` 구조체에는 아직 칸이 없다(serde 기본 = 모르는 칸 무시라 지금도 검증은 통과 — 왕복 시험 실측) → U2 가 S9b 용으로 칸을 더해야 한다.

## §1 master 집행 체크리스트(전부 비가역 · 워커 실행 0)

### ① R·U·F 키 생성
- 준비: master 기기에 `brew install minisign`(U·R 의식이 `minisign -S` 를 부른다 · 이 기계엔 지금 없다 — 실측 `minisign not found`).
- **R**(오프라인 2벌 · 서로 다른 장소 · 📌11): R 매체 1 을 꽂고 `minisign -G -p r.pub -s /Volumes/<R1>/r.key`(비밀번호 설정) → 매체 2 로 `cp /Volumes/<R1>/r.key /Volumes/<R2>/r.key`(매체→매체 · 빌드 디스크 경유 0) → 두 매체 분리 보관. `r.pub` 은 공개 정보(저장소에 둬도 됨).
- **U**(빌드 기기 밖 매체 · 📌11): `minisign -G -p u.pub -s /Volumes/<U>/u.key`.
- **F**(CI 비밀): `bunx @tauri-apps/cli@2.11.4 signer generate -w "$TMPDIR/f.key"` → `f.key` 파일 **내용 전문** = 비밀 `CYS_FEED_SIGNING_PRIVATE_KEY` · 입력한 비밀번호 = `CYS_FEED_SIGNING_PRIVATE_KEY_PASSWORD`(팩 키 P2 와 같은 형식 · release.yml 서명 스텝과 같은 도구) → 등록 뒤 로컬 `f.key` 삭제 권고(분실해도 R 위임으로 새 F 를 들인다).
- key id 확인: `python3 -c 'import sys; sys.path.insert(0,"scripts/update"); import update_common as uc; print(uc.pubkey_key_id(open(sys.argv[1]).read()))' u.pub`(R·U·F·A2 넷이 서로 달라야 한다).

### ② 1.1.8 키링 공개키 기입 자리 — `cysjavis-pack/trusted-keys.json`
- ⚠**U1 머지 뒤에만**: 이 가지(U1 없음)의 `packsig` 는 `purpose` 를 모른다 — 지금 넣으면 R·U·F 가 **팩 키로도** 신뢰된다. U1 의 packsig 「팩 용도 거르기」(HANDOFF-U1 §1 ①)가 들어온 뒤 기입. 발행 게이트 8-a(`release-verify.py load_pack_keyring`)는 이 가지에서 이미 purpose 를 거른다(`0ea451cc`).
- 항목 서식(기존 키와 같음 · `pubkey` = .pub 파일 텍스트 전문의 base64):
  ```
  python3 - r.pub root u.pub release f.key.pub feed <<'PY'
  import sys, json, base64; sys.path.insert(0, "scripts/update"); import update_common as uc
  a = sys.argv[1:]
  for path, purpose in zip(a[::2], a[1::2]):
      t = open(path).read()
      try: t = base64.b64decode(t).decode()   # tauri .pub 는 이미 base64
      except Exception: pass
      print(json.dumps({"key_id": uc.pubkey_key_id(t), "pubkey": base64.b64encode(t.encode()).decode(),
                        "not_after": "<결정 ③>", "purpose": purpose, "comment": "용도=%s · 1.1.8 자동 갱신" % purpose}, ensure_ascii=False))
  PY
  ```
- **A2** 항목도 같은 파일에 `purpose: "win-asset"` 로: `key_id` = `831CA9172204E93E` · `pubkey` = `src-tauri/tauri.conf.json` `plugins.updater.pubkey` 값 그대로(시험 핀 `test_a2_key_id_matches_tauri_conf` 가 그 파생값 = 상수임을 잰다).
- 기입 뒤: `cys build-info --json` 의 `keyring_ids` 가 4개(`root:…`·`release:…`·`feed:…`·`win-asset:…`)인지 · `cargo test --lib packsig::` 의 키링 파생 대조 초록.

### ③ 첫 게시(외부 발행) — 순서 고정(봉투 CI 가 라이브의 보관소·폐기문을 읽으므로)
1. 보관소: U 의식 산출 `dist/update/cysr-release-<seq>.json(.minisig)` → `python3 scripts/update/publish-site.py archive --site-dir ~/axdev/ai-jarvis/site --file dist/update/cysr-release-<seq>.json`
2. 폐기문(첫 = 빈 목록): `python3 scripts/update/make-revocations.py --key-id <R id> --first --out revocations.json` → `scripts/update/sign-revocations.sh --doc revocations.json --media /Volumes/<R1> --key /Volumes/<R1>/r.key --out-dir dist/update` → `publish-site.py revocations --site-dir … --file dist/update/revocations.json`
3. 사이트 배포(master 수동 · 지금 관행): `cd ~/axdev/ai-jarvis && bash web/build-web.sh && (cd web && bunx wrangler deploy)` → `curl -fsS https://jarvis.godmeyou.kr/update/cysr/releases/<seq>.json | shasum -a 256` = 로컬 · revocations 도 같게 · 그 뒤 ai-jarvis 커밋.
4. 첫 봉투(F = CI 만): `gh workflow run refresh-feed.yml -R oogisoogi/cys-ro -f component=cysr -f channel=next -f release_seq=<seq> -f rollout_pct=100 -f halt=false -f first=true -f publish=false` → 아티팩트 `envelope-cysr-next` 확인 → 같은 명령 `-f publish=true`.
5. 주 1회 자동 재서명 켜기 = 저장소 변수 `UPDATE_FEED_PUBLISH=on`(켜기 전까지 cron 은 만들고 검증만 · 게시 0).

### ④ CI 비밀·변수 이름(값 = master 가 GitHub 설정에 · 저장소에 값 0)
| 이름 | 종류 | 쓰는 곳 |
|---|---|---|
| `CYS_FEED_SIGNING_PRIVATE_KEY` · `CYS_FEED_SIGNING_PRIVATE_KEY_PASSWORD` | 비밀 | refresh-feed.yml 서명 |
| `AI_JARVIS_PUSH_TOKEN` | 비밀 | refresh-feed.yml 사이트 저장소 push(배포 성공 뒤) |
| `CLOUDFLARE_API_TOKEN` · `CLOUDFLARE_ACCOUNT_ID` | 비밀 | refresh-feed.yml `wrangler deploy`(jarvis-site 워커) — 결정 §3 ① 에 따라 바뀔 수 있음 |
| `CYS_FEED_KEY_ID` | 변수 | refresh-feed.yml(F key id · 내장 키링 feed 에 있어야 함 — 스텝이 대조) |
| `UPDATE_FEED_PUBLISH` | 변수 | `on` = cron 게시 |
| (기존) `TAURI_SIGNING_PRIVATE_KEY`(A2) · `CYS_PACK_SIGNING_PRIVATE_KEY`(P2) | 비밀 | 변화 없음 |

### ⑤ 발행 리허설 순서(태그 드라이런)
| 단계 | 무엇 | 판정 |
|---|---|---|
| R0 | U1 2판 머지 → 이 가지 rebase → `CYS_UPDATE_VERIFY_BIN=<머지 트리 디버그 cys> python3 scripts/tests/test_update_publish.py` | 46/0(0 건너뜀) |
| R1 | ①② 키 생성·키링 기입·④ 비밀·변수 | `cys build-info` keyring_ids 4 |
| R2 | `CYSR_RELEASE_SEQ` 값 결정·주입(결정 §3 ②) 뒤 태그 → release.yml draft | 새 스텝 초록: 맥·윈 「동봉 매니페스트 min_binary」 · pack-artifacts 「min_binary」 · 윈 「본문 재료 수집」(아티팩트 `update-inputs-windows-x64` 존재 — continue-on-error 라 **눈으로 확인**) |
| R3 | 맥 로컬 빌드 zip → `scripts/update/collect-inputs.sh mac <zip> macos-arm64 inputs/` · `gh run download <run> -n update-inputs-windows-x64 -D inputs/` · draft 자산 받기 | 재료 4종(cdhash·build-info×2·payload 트리) |
| R4 | `make-release-json.py … --build-info macos-arm64=inputs/build-info-macos-arm64.json --build-info windows-x64=inputs/build-info-windows-x64.json --cdhash macos-arm64=$(cat inputs/cdhash-macos-arm64.txt) --a2-sig windows-x64=cysr_<v>_x64-setup.exe.sig --payload-dir windows-x64=inputs/payload-windows-x64 …` → `release-gate.py body --body … --keyring cysjavis-pack/trusted-keys.json --archive-dir ~/axdev/ai-jarvis/site/update` | rc 0 |
| R5 | U 의식(`sign-release.sh` · 박사님 매체 1단계) → `release-gate.py body --sig …` | rc 0 |
| R6 | §1 ③ 1~4(publish=false 먼저) | 봉투 아티팩트 + verify 스텝 초록 |
| R7 | release-publish.yml dry_run(새 게이트 = latest.json·min_binary 두 잡) → 승인 → 발행 | — |
| R8 | 캐너리 C1(설계 §7-4) | — |

## §2 어느 레인이 어느 게이트를 부르나
| 레인 · 잡 | `release-gate.py` 단계 | 재는 것 |
|---|---|---|
| release.yml build(맥) · build(윈 NSIS) | assets `--bundled-manifest` | 앱 동봉 팩 매니페스트 min_binary 빈 값 = 거부(bundle-prep 수리의 이중 벨트) |
| release.yml pack-artifacts | assets `--pack-manifest` | 서명 팩 매니페스트 min_binary 빈 값 = 거부 |
| pack-release.yml | assets `--asset-list … --pack-manifest` | 팩 단독 릴리스도 latest.json 의무 + min_binary |
| release-publish.yml verify · publish(대칭) | assets `--release-dir --pack-manifest` | latest.json 의무(tombstone 파일이 있으면 바이트 고정) + min_binary · 게이트 자기시험 선행 |
| refresh-feed.yml | verify(U1 `cys update-verify` · 출시 빌드 내장 키링) | 새 봉투 서명·서식·URL — apply/halt/not_in_rollout 만 통과 |
| master(발행 의식) | body · verify | §1 ⑤ R4·R5·R6 |
- 시험 `scripts/tests/test_update_publish.py` 등재 = ci-branch(맥) · release(맥 aarch64) · pack-release + release-publish 두 잡(자기시험) — `lane-parity-rehearsal.sh --strict` rc 0 · `--self-test` rc 0.

## §3 【결정필요】(master 범위 · 각 권고 + 단점 1줄)
- ① **봉투 CI 게시가 사이트 전체를 배포한다**: refresh-feed.yml 은 ai-jarvis `main` 머리로 `build-web.sh` → `wrangler deploy`(jarvis-site 워커 = 사이트 전체)를 한다 → master 가 main 에 올려 두고 아직 배포 안 한 사이트 변경이 있으면 **주간 cron 이 그것까지 공개**한다. 권고 = `/update/*` 전용 워커(정적 자산 = update/ 만 · 경로 라우트 `jarvis.godmeyou.kr/update/*`)로 분리하고 CI 는 그 워커만 배포 · 단점 = 커스텀 도메인(jarvis-site)과 경로 라우트의 우선순위를 CF 에서 실측해야 한다(이 티켓은 미측정 · 외부 계정 = master). 분리 전까지는 `UPDATE_FEED_PUBLISH` 를 켜지 말고 dispatch 게시만 쓰는 것이 안전.
- ② **`release_seq` 값의 출처**: U1 build.rs 는 `CYSR_RELEASE_SEQ` env 를 굽는데 release.yml 은 아직 그 값을 주지 않는다(주지 않으면 build-info `release_seq=0` → 생성기가 「build-info release_seq ≠」 로 거부 = fail-closed). 판 번호 = master 결정이라 배선하지 않았다. 권고 = release.yml 최상위 env `CYSR_RELEASE_SEQ: ${{ vars.CYSR_RELEASE_SEQ }}` + 태그 전 변수 갱신(값은 직전 보관소 seq + 1 · 게이트가 역행·판 미증가를 잡음) · 단점 = 변수 갱신을 잊으면 같은 seq 재사용 → 게이트 body 가 「보관소 seq 이미 있음·바이트 다름」으로 막는다(발행 지연 · 위험 0).
- ③ **키 만료(`not_after`)**: 권고 = R 2036-01-01 · U·F·A2 2028-01-01(교체는 R 위임으로 새 바이너리 없이) · 단점 = U·F 만료 전 위임을 잊으면 그날 전 기기 갱신이 「만료된 키」로 멈춘다(daily 칸에 보임) → BACKLOG 에 2027-10 위임 알림 1줄.

## §4 설계·브리프와 다른 점 · 보충(정직)
- 봉투 URL: 브리프 §2-3 의 `/update/<component>/<channel>/feed.json` 이 아니라 **설계 §4-4·§6-1 과 U1 url.rs 의 `/update/<component>/<channel>.json`** 을 따랐다(정본 = 설계 + 검증기 규칙표 · 브리프 표기와 다르면 기기가 거부한다).
- NSIS ⓪-a 사람 안내 문구 = 영어(훅 계약 「사용자에게 보이는 문자열은 ASCII」 · 설계 한국어 문안의 영어판). 조상 pid 대조(위임 ③)는 NSIS 에서 하지 않는다 — 러너의 CREATE_SUSPENDED 이미지 대조(§3-7 ④)와 128비트 토큰이 맡는다(훅 주석에 명기). 판정 불가(잠금 파일 못 엶) = 「잡혀 있음」(fail-closed · 대가 = 그동안 수동 설치도 exit 6).
- nsis-hook-model: ⓪-a 를 「not modeled — invariant-neutral」 목록에 근거와 함께 올리고 GUARD_PIN 재핀(그 파일 규칙 = 훅 수정과 같은 커밋 → `db2f7cbf` 에 amend 로 함께 넣음) — 39082 종단 상태 I1/I3/I4 유지.
- harness.nsi 에 FileFunc·WordFunc include 추가(템플릿 순서 패리티 · ⓪-a 가 GetOptions·WordFindS 를 쓴다).
- 7-b: 직전 판 conf 에 `plugins.updater` 블록이 **없으면** A2 상수 · 블록이 있는데 pubkey 가 비면 종전대로 거부 — test_release_verify kb9 를 두 갈래로 고쳤다(행동 변경이 티켓 범위라 기존 핀 수정 · 둘 다 rc 1 유지).
- bundle-prep 의 min_binary 기본값 = 이 앱 자신의 판(Cargo.toml) — `CYS_PACK_MIN_BINARY` 가 있으면 그것. release.yml 은 그 env 를 안 준다 → 지금 이 가지에서는 동봉본·서명 레인(`PACK_MIN_BINARY`) 둘 다 1.1.7 이지만, **1.1.8 판 올림 뒤엔 동봉본 = 1.1.8 · 서명 레인 = `PACK_MIN_BINARY` 값으로 갈릴 수 있다**(동봉본은 그 앱 안에서만 쓰여 더 높아도 무해 · 같게 하려면 빌드 잡 env 에 `CYS_PACK_MIN_BINARY: ${{ env.PACK_MIN_BINARY }}` 류 배선 = master 판단).
- 게이트 「release_seq 증가 ⇒ 판 증가」: 앞 3마디가 커져야 통과 · 같은 3마디 + 빌드 꼬리(`1.1.8+canary.1`)는 `--allow-canary` 일 때만(설계 §7-4 캐너리) — 판 문자열 순서는 표시용이고 정본은 release_seq(§4-2).
- `scripts/release/latest-tombstone.json` 은 **만들지 않았다**(내용 = 1.1.8 발행 뒤의 그 latest.json 바이트 · 다리 기간 끝 = master 결정 · 파일이 생기는 순간 게이트가 바이트 고정 모드로 바뀐다).
- refresh-feed.yml 은 출시 빌드 `cys` 로 검증하려고 매 회 `cargo build --release --bin cys`(러너 시간 계수 = 미측정).
- 설치 링크 잠금·위임·윈 본문 보존 = 저장소 밖 파일이라 **명세 1쪽**(`docs/update/INSTALL-LINK-LOCK.md`)만 · 실행 0.

## §5 산출 × 시험 × 소요(실측 · 소요 = 커밋 시각 차)
| # | 브리프 항목 | 파일 | 시험(뮤테이션) | 커밋 |
|---|---|---|---|---|
| 1 | 본문 생성기 | `scripts/update/make-release-json.py` · `update_common.py` · `collect-inputs.sh` | 정상 1 · 윈 행 부재 · notes 빈/금지 어휘 · min_binary 빈 값 · build-info seq 불일치 · SUMS 불일치 · payload 심링크 · -dirty · 맥 수집 봉인/DR 음성 | 329c1ae5 · 0ea451cc |
| 2 | U 의식 | `sign-release.sh` · `lib/offline-sign.sh` | 정상(키 복사 0 스캔) · 매체 밖 키 · 마운트 아닌 폴더 · 심링크 키 · 다른 키(R 로 U 본문) | 329c1ae5 |
| 3 | refresh-feed(F) | `.github/workflows/refresh-feed.yml` · `make-envelope.py` | 첫 봉투 --first · feed_rev +1·rollout 이어받음 · ttl>14일 · F=U · 채널 후퇴 | 2cfb9117 · 329c1ae5 |
| 4 | 보관소 · latest.json | `publish-site.py` · `release-gate.py assets` | 보관소 다른 바이트 거부·같은 바이트 멱등 · 봉투 feed_rev 단조 · latest.json 부재 · tombstone 불일치 · 자산 목록 레인 | 329c1ae5 |
| 5 | R 의식 | `make-revocations.py` · `sign-revocations.sh` · `docs/update/R-RITUAL.md` | rev 단조·--first · root 위임 거부 · R 자기 폐기 거부 · 미지 severity 거부 · 매체 의식 정상 | 329c1ae5 · 0ea451cc |
| 6 | 발행 게이트 | `release-gate.py` + 레인 4곳 + `bundle-prep.sh` + `release-verify.py`(7-b A2 · 8-a purpose) | min_binary 빈 값(팩·동봉) · seq 역행 · 판 미증가 · 캐너리 플래그 · URL 밖 · requires 빈 값 · payload `..` · 서명 키 불일치 · 판정 대상 0 = rc 3 | 329c1ae5 · 09a79e7f · 2cfb9117 · 0ea451cc |
| 7 | NSIS ⓪-a | `src-tauri/nsis-hooks.nsh` · harness · model | 컴파일(-WX) OK · N1~N8 음성 대조 OK · 모델 39082 상태 OK · 소스 핀(⓪-a 가 ⓪ 앞) | db2f7cbf |
| 8 | 시험 | `scripts/tests/test_update_publish.py` · `fixtures/fake_minisign.py` | **46/0**(U1 디버그 cys `102859e3` 왕복 = apply 2행 · 본문 변조 reject · 만료 · seq 같음 uptodate · F 키 본문 reject) · 단독 40/0 + 6 건너뜀 · test_release_verify 137/0 · lane-parity --strict 0 · --self-test 0 · secret-scan clean · fake_minisign RFC 8032 벡터 1 일치 | 전 커밋 |
| 9 | HANDOFF | 이 문서 | — | (이 커밋) |
- 소요: 브리프 09:21 → 설계·U1 정독·TODO 09:21–09:24 · 스크립트·시험 1차 커밋 09:41(17분) · bundle-prep·7-b·NSIS 09:41 · CI·레인 09:49(8분) · 수집기·문서 09:57(8분) · HANDOFF 09:5x–10:0x. **총 ≈ 40분**(계수 = U1 51분 대비 · 「스크립트·YAML 2배」 추정은 과대였다 — 실측은 0.8배).
- 저장소 게이트: 브리프의 `tests/commit_gate` 류 파일은 이 저장소에 **없다**(`git ls-files | grep -i commit.gate` 0건) → 대신 secret-scan(변경 파일 전수 clean) · lane-parity(--strict·--self-test) · test_release_verify · nsis 컴파일 하네스 · nsis 모델을 돌렸다.

## §6 미측정 · 남은 위험(정직)
- 윈 재료 수집(무인 설치로 payload 측정)과 refresh-feed.yml 은 **러너에서 한 번도 안 돌았다**(이 기계엔 윈 실행 기층·GitHub 실행 0) — 첫 발행 리허설(§1 ⑤ R2·R6)이 첫 실측. 윈 수집 스텝은 continue-on-error 라 실패해도 릴리스는 나가고, 재료 부재는 본문 생성 단계에서 막힌다(R3 에서 아티팩트 존재를 **눈으로** 확인).
- uninstall.exe 를 payload 에서 뺀 것이 S9b 와 맞는지(설치기 생성 파일이 판마다 같은지 미측정) = U2 S9b 설계와 대조 필요.
- GitHub 맥 러너에서 `hdiutil attach`(가짜 매체 시험)가 되는지 미측정 — 안 되면 그 묶음만 실패한다(ci-branch 맥 첫 실행이 잰다).
- `bunx wrangler@3` 판 고정은 사이트 저장소의 실제 사용 판과 대조하지 않았다(§3 ① 결정과 함께).

## §7 재현
- `git log --oneline 7e7aa5da..HEAD` · `python3 scripts/tests/test_update_publish.py`(단독) · U1 왕복 = U1 커밋본 작업트리에서 `cargo build --bin cys` → `CYS_UPDATE_VERIFY_BIN=<그 cys> python3 scripts/tests/test_update_publish.py`
- `bash scripts/tests/nsis-hook-compile/run.sh` · `python3 scripts/tests/nsis-hook-model/model.py` · `bash scripts/lane-parity-rehearsal.sh --strict`
