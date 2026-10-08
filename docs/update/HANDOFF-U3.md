# HANDOFF-U3 — 1.1.8 데몬 자동 갱신 U3(발행 쪽 · 스크립트·CI·게이트) · TICKET=cysr-118-u3-publish

- 좌석 = worker surface:1293(294 118u3) · 계정2 · Opus · 가지 `u3/publish-118`(off `7e7aa5da`) · **push 0 · 실키 0 · 게시 0 · 설치기 빌드 0**
- 브리프 = [master#1b3b04af] 2026-10-06 09:21:02(원장 submitted=yes 대조) · 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md` 4판
- 서식 소비 = U1 가지 `u1/autoupdate-118` **커밋본 `102859e3`**(작업트리의 2판 진행분은 미커밋이라 쓰지 않았다 · 2판 추가 필수 칸 — features·bundled_pack digest·맥 cdhash/dr_pin_id·윈 a2_sig_url — 은 생성기·게이트가 **이미 낸다**). U1 은 이 가지에 머지하지 않았다 — 별도 작업트리(scratch `u1ref`)에서 디버그 `cys` 를 빌드해 `update-verify` 왕복에만 썼다.
- 이 문서의 시각·수는 전부 도구 출력(git 커밋 시각 · `date` · 시험 결과 줄)에서 옮겼다.

## §0 델타(먼저 읽을 것)
- ★**피드 상한 홉별 분리(2026-10-08 · TICKET=cysr-118-body-cap · [master#1a18914e] · 가지 `fix/body-cap` off `8278fef3`)** — 윈 본체 실기 ⓓ3 `--preserve-installer` rc 4 `body_unreachable`(curl rc 63): 기기 `net.rs` 단일 상한 1 MiB ↔ 게시 본문 `cysr/releases/1.json` 2,474,038 B(윈 `payload_manifest` 11,676 행) · 같은 본문을 base64 로 싣는 봉투(≥3,299,192 B)도 같은 상한 = 자동 갱신 첫 받기부터 끊김. 처방 = `feed_max_bytes(rel)`: 본문 8 MiB · 봉투 12 MiB(≥ 본문 base64 + 64 KiB 컴파일 단언) · 폐기문·`.minisig`·그 밖 1 MiB 유지 · file 갈래도 같은 상한 · 발행 쪽 대칭 = `update_common.FEED_*_MAX_BYTES`(net.rs 와 대조 시험) 를 생성기 3(본문·봉투·폐기문) · 게이트 3단계(body·revocations·verify) · 게시기가 거부. ⚠1.1.8(53007bde) 바이너리는 옛 상한이라 보관소 seq 1 본문을 받지 못한다 = 이 수리는 재빌드·seq 2 로만 기기에 닿는다.
- ★**UA 수정(2026-10-08 · TICKET=cysr-118-ua-fix · [master#cd7ff43c] · 가지 `fix/ua-publish` off `53007bde`=v1.1.8)** — R4 실측: `jarvis.godmeyou.kr` 앞단 Cloudflare 가 파이썬 기본 UA(`Python-urllib/…`)만 **403**(curl·UA 없음·`cysr-publish/1` = 200 · `/`·`/update/`·`/get` 같음) → `trusted_now()` 를 부르는 생성기·게이트·게시기 전부 rc 2. 처방 = `update_common.HTTP_USER_AGENT = "cysr-publish/1"` 1곳 정의 · urllib Request 3곳 전부 사용(`trusted_now` · `publish-site.live_check` · `store.S3Store._req`(R2 · 서명 밖 헤더)) · refresh-feed.yml 의 사이트 호출 = curl(무관) · 그 밖 파이썬 도구(`release-verify`·`release-postprocess`·`pre-tag-ci-check`) = github.com 만 부름(무관). 시험 `TestUserAgent` 3(UA 실림 · 기본 UA 403 음성 · 소스 검사 = Request 마다 상수 · 3곳 고정). ★**v1.1.8 산출물·서명 본문 무관**: `scripts/update/` 는 앱 번들·팩 밖(발행 기기에서만 도는 도구)이고 본문 바이트는 스크립트가 아니라 입력(자산·build-info·CDHash·payload)이 정한다 — 고친 스크립트로 같은 입력을 다시 만든 본문 = `signed_at` 외 동일(실측) · R5 서명 대상 본문(sha256 `42f3b190…`)도 고친 게이트로 rc 0.
- ★★★★★**R0 = `4d0aab95` 기준(14:3x · [master#f752aed4] · TICKET=cysr-118-u3-publish-R0)** — `u3/publish-118`(@`64d755dd` · 백업 가지 `backup/u3-pre-R0-64d755dd`)을 origin/merge/v0.14.43 `4d0aab95`(U1 5판 `ecc13660` 병합) 위로 rebase · 충돌 0 · U3 파일 내용 변경 0(겹친 2 파일: `url-vectors.json` = 기반과 바이트 동일 → U3 쪽 추가분 소멸 · `windows-health.yml` = 기반 +6줄만) · seq 1 대역 제거 = `b91a142a`(첫 판 시험 = 병합 트리 실제 U1 SEQ1 · 열거 행 키 소스 핀 = 이 트리 `src/update/feed.rs`). 게이트(병합 트리 `cargo build --bin cys` 디버그 sha256 `8f4adf96…`): test_update_publish strict **91/0 · 건너뜀 0** · 단독 91/0 + 14 건너뜀 · 음성 대조 = SEQ1 이전 U1(`e1034052` 사본 `05336d34…`)로 seq1 시험 FAILED · test_release_verify 140/0 · nsis 컴파일 OK · 모델 39082 + ⓪-a 270 OK · lane-parity strict/self-test 0 · secret-scan clean(41 파일) · 워커 node --check OK · push 0.
- ★★★★**4판 끝(12:1x · 【확인요청】 4판 · [master#4468fec2] · Fable 3R = 머지 BLOCK 0 · 소수정)** — `a0afcb09`(MAJOR-1 열거 행 outcome 중첩 + U1 소스 핀 · MAJOR-2 첫 판 seq 1 = 후보 uptodate 1행) · `c786d463`(MAJOR-3 묘비 포인터) · `d60139ff`(MINOR-2 시험 시각 env 거부 · tauri-action 주석) · 이 문서(§6 · §9-2). 게이트 = U1 HEAD `e1034052` 사본 빌드(라이브 트리 아님 · scratch `u1head` 워크트리) strict — 실측 §9-2 · ⚠MAJOR-2 의 U1 cli 쪽(「허용 출발 seq 없음」 거부 해제)은 291 몫 — 그 전까지 seq 1 시험은 U1 출력에서 그 거부만 걷는 대역으로 게이트 규칙을 잰다.
- ★★★**3판 끝(11:4x · 【확인요청】 3판)** — 지시 = [master#9219ca05](codex 2R = `~/axdev/master/reports/REVIEW-U3-codex-2r.md` · master 가 **머지 기준**(3판 코드)과 **발행 기준**(§1 ⑥ 표)을 갈랐다) · 반영표 = **§9**(19행).
  - 커밋: `4991230b`(U1 2판 계약 · #10 · #11) · `cd4c7152`(#4·#5·#6·#8·#15·#16·#19 + 워커 502) · `d45255b9`(#3) · `90af8cd9`(#9) · `e6e7ae5c`(#13·#14 모델) · 이 문서.
  - 게이트(11:4x 실측): `CYS_U3_REQUIRE_ALL=1 CYS_UPDATE_VERIFY_BIN=<U1 2판 디버그 cys(~/axdev/.wt/cys-118-u1 · 0fb4d824 빌드 11:07 사본 sha256 7f976fc6…)>` test_update_publish **87/0 · 건너뜀 0** · 단독 87/0 + 12 건너뜀 · test_release_verify 140/0 · nsis 컴파일 OK · 모델 39082 + ⓪-a 270(Z1~Z6) OK · lane-parity strict/self-test 0 · secret-scan clean(26 파일).
  - 다음 = codex 3R(마지막) + master 게이트 → 머지(U1 머지 뒤 rebase).
- ★★**2판 끝(11:1x · 【확인요청】 2판 · [master#f9d48c3c] 재개 지시분)** — 지시 = [master#f151182e] 10:14:56(codex 1R 판정표 · 원문 `~/axdev/master/reports/REVIEW-U3-codex-1r.md`) · 결정 = [master#8db3b908] 10:04(① /update/* 전용 워커 + R2 · CI 게시 0 ② `vars.CYSR_RELEASE_SEQ` ③ 키 만료 R 2036 · U·F·A2 2028).
  - 1/2 = `ca4c7b6a` · 2/2 = `181fd516`(#3) · `9a2489f3`(#13) · `ea940902`(refresh-feed) · `cc7390e8`(#17) · `bc1ab479`(#1·#18) · `b155da22`(#4 A2) · `62a6f1fa`(update-worker·탐침) · `c11ee1d8`(윈 실기 문안·U5 포인터) · 이 문서.
  - 번호별 처방·커밋·시험 = **§8 1R 반영표**(19행). 남은 것 = 전부 「코드 밖」(U1 머지 · 윈 실기 · U5 · CF 실측 · 키 생성 — §8 잔여 열).
  - 게이트(11:1x 실측): `CYS_U3_REQUIRE_ALL=1 CYS_UPDATE_VERIFY_BIN=<U1 102859e3 디버그 cys>` test_update_publish **72/0 · 건너뜀 0** · 단독 72/0 + 8 건너뜀(맥 매체 아님 → U1 왕복 7 + 맥 수집 1) · test_release_verify **140/0** · nsis 컴파일 OK(N1~N8) · 모델 39082 OK · lane-parity `--strict` 0 · `--self-test` 0 · secret-scan clean(변경 19 파일).
  - 함정(다음 사람): 시험은 모듈 머리에서 `CYS_SIGN_DEV=1`·`CYS_TEST_NOW=1790000000` 을 켠다 · 실 의식(개발 모드 밖)에서는 `MINISIGN`·`CYS_SIGN_MEDIA_PREFIX`·`CYS_TEST_NOW`·`--wait-eject 0` 이 **거부**된다 · U1 왕복 바이너리 = scratch `u1ref`(102859e3) 디버그 빌드(`CARGO_TARGET_DIR` 를 따로 줘서 빌드 · ~25초 증분).
- 끝난 것 = 브리프 §2 의 1~9 전부(아래 §5 표) · 커밋 6개(`329c1ae5`·`09a79e7f`·`db2f7cbf`·`2cfb9117`·`0ea451cc` + 이 문서).
- 【결정필요】 3건 = §3 ①②③(전부 master 결정 범위 · 박사님 결정 항목 0).
- **설계·U2 에 알릴 실측 2건**: ⑴ 맥 DR 핀 대조의 `codesign -R` 문법 — 설계 §3-6 ② 의 `-R='=designated => identifier … and certificate leaf = H"…"'` 는 이 macOS 에서 **문법 오류**(`line 1:1: unexpected token: =`)이고 `-R='identifier "com.cysjavis.terminal" and certificate leaf = H"a426…b18d"'` 가 맞다(실 `/Applications/cys.app` 양성 rc 0 · 엉뚱한 leaf 음성 rc 3). ⑵ **CDHash 가 읽힌다고 서명된 번들이 아니다** — 애플 실리콘 링커가 Mach-O 를 자동 서명해서 봉인 안 된 번들도 `codesign -dvvv` 가 CDHash 를 낸다(실측) → 수집기는 `--verify --deep --strict` + DR 핀까지 본다. U2 의 S2 검증 3겹도 같은 함정이 있는지 대조 필요.
- **U2 에 넘기는 서식 1건**: 윈 행 `payload_manifest[{path,size,sha256}]` 를 본문에 싣는다(경로 = `/` 구분 상대 · 정렬 · 대소문자 무시 중복 거부). U1 `Asset` 구조체에는 아직 칸이 없다(serde 기본 = 모르는 칸 무시라 지금도 검증은 통과 — 왕복 시험 실측) → U2 가 S9b 용으로 칸을 더해야 한다.

## §1 master 집행 체크리스트(전부 비가역 · 워커 실행 0)

### ① R·U·F 키 생성
- 준비: master 기기에 `brew install minisign`(U·R 의식이 `minisign -S` 를 부른다 · 이 기계엔 지금 없다 — 실측 `minisign not found`).
- **R**(오프라인 2벌 · 서로 다른 장소 · 📌11): R 매체 두 개를 꽂고 `scripts/update/gen-offline-key.sh --media /Volumes/<R1> --name r --copy-to /Volumes/<R2> --pub-out r.pub`(키 생성 = 매체 안 · 둘째 벌 = 매체→매체 복사 + 바이트 대조 · 두 매체가 같은 장치·마운트 아님·빌드 디스크와 같은 장치면 거부 · 비밀번호 = minisign 이 직접 묻는다) → 두 매체 분리 보관. `r.pub` 은 공개 정보(저장소에 둬도 됨).
- **U**(빌드 기기 밖 매체 · 📌11): `scripts/update/gen-offline-key.sh --media /Volumes/<U> --name u --pub-out u.pub`.
- ⚠정직(codex 1R #3 잔여): minisign 은 이 기기의 프로세스라 생성·서명 순간 개인키 바이트는 이 기기 메모리를 지난다(파일·클립보드 0). 네트워크와 분리된 서명 기기/HSM 은 범위 밖 — 위협 모델상 필요하면 별도 결정(§8 #3 잔여).
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
                        "not_after": {"root": "2036-01-01T00:00:00Z"}.get(purpose, "2028-01-01T00:00:00Z"),  # 결정 ③
                        "purpose": purpose, "comment": "용도=%s · 1.1.8 자동 갱신" % purpose}, ensure_ascii=False))
  PY
  ```
- **A2** 항목도 같은 파일에 `purpose: "win-asset"` 로: `key_id` = `831CA9172204E93E` · `pubkey` = `src-tauri/tauri.conf.json` `plugins.updater.pubkey` 값 그대로(시험 핀 `test_a2_key_id_matches_tauri_conf` 가 그 파생값 = 상수임을 잰다).
- 기입 뒤: `cys build-info --json` 의 `keyring_ids` 가 4개(`root:…`·`release:…`·`feed:…`·`win-asset:…`)인지 · `cargo test --lib packsig::` 의 키링 파생 대조 초록.

### ③ 첫 게시(외부 발행) — 순서 고정(봉투 CI 가 라이브의 보관소·폐기문을 읽으므로) · 게시 = R2 + `/update/*` 전용 워커(결정 ①)
0. **준비(1회)**: R2 버킷 생성(이름 = master 결정 → `update-worker/wrangler.jsonc` `bucket_name` 자리) → `scripts/update/cf-route-probe.sh`(드라이런으로 명령 확인) → `--execute`(실행 직전 확인 대상 · 탐침 워커를 스테이징 경로에만 올렸다 지움) **rc 0 일 때만** → `cd update-worker && bunx wrangler@3 deploy`. rc 1(커스텀 도메인이 이김) = 배포 금지 · 대안 결정 필요.
1. **R-의식 전 seq 변수 갱신**(결정 ②): 저장소 변수 `CYSR_RELEASE_SEQ` = 보관소 최댓값 + 1(첫 판 = 1) → 그 뒤에 태그(release.yml 빌드 전 스텝이 정수 ≥1 을 강제 · 게시기가 「최댓값 + 1」 아니면 거부).
2. 보관소: U 의식 산출 `dist/update/cysr-release-<seq>.json(.minisig)` → `release-gate.py body --body … --sig … --keyring cysjavis-pack/trusted-keys.json --archive-r2 <버킷> --expect-seq <seq> --first`(★2R 정정: 첫 판은 게이트에도 `--first` · 둘째 판부터 둘 다 없음) → `python3 scripts/update/publish-site.py archive --r2 <버킷> --file dist/update/cysr-release-<seq>.json --first --live-check https://jarvis.godmeyou.kr`. R2 자격 = master 로컬 env `R2_ACCOUNT_ID`·`R2_ACCESS_KEY_ID`·`R2_SECRET_ACCESS_KEY`(S3 API 토큰 · 그 버킷 객체 읽기·쓰기만 · 저장소·CI 에 값 0) · 라이브 불일치 = 자동 되돌리기(rc 4) · 되돌리기도 실패 = rc 5 + 인쇄된 `restore` 1줄.
3. 폐기문(첫 = 빈 목록): `python3 scripts/update/make-revocations.py --key-id <R id> --first --out revocations.json` → `scripts/update/sign-revocations.sh --doc revocations.json --media /Volumes/<R1> --key /Volumes/<R1>/r.key --out-dir dist/update` → `release-gate.py revocations --doc dist/update/revocations.json --keyring … --first` → `publish-site.py revocations --r2 <버킷> --file dist/update/revocations.json --first --live-check https://jarvis.godmeyou.kr`(둘째부터 게이트 `--prev prev.json` · 게시 `--first` 없음 · 게시기가 게시본 대비 rev+1·후계 규칙을 다시 잰다).
4. 첫 봉투(F = CI 만 · CI 는 만들고 검증만): `gh workflow run refresh-feed.yml -R oogisoogi/cys-ro -f component=cysr -f channel=next -f release_seq=<seq> -f rollout_pct=100 -f halt=false -f first=true` → 아티팩트 `envelope-cysr-next` 받기 → `publish-site.py envelope --r2 <버킷> --file env.json --cys <U1 출시 cys> --live-check https://jarvis.godmeyou.kr`(★3판: 게시기가 U1 을 **직접 다시 돌린다**(게시된 폐기문과 함께 · cysr = 열거) · 실은 본문 = 보관소 객체 바이트 동일 · 증표 파일은 정보용).
5. 주 1회: cron 이 네 봉투를 재서명·검증해 아티팩트로 남긴다 → master 가 4 와 같은 게시 1줄(자동 게시 0 — 결정 ①). 봉투 유효창 14일 · 7일 넘게 안 바뀌면 기기 daily 칸이 잡는다.

### ④ CI 비밀·변수 이름(값 = master 가 GitHub 설정에 · 저장소에 값 0)
| 이름 | 종류 | 쓰는 곳 |
|---|---|---|
| `CYS_FEED_SIGNING_PRIVATE_KEY` · `CYS_FEED_SIGNING_PRIVATE_KEY_PASSWORD` | 비밀 | refresh-feed.yml 서명 |
| `CYS_FEED_KEY_ID` | 변수 | refresh-feed.yml(F key id · 내장 키링 feed 에 있어야 함 — 스텝이 대조) |
| environment `feed` | 설정 | refresh-feed 잡 — F 비밀 두 개를 여기에 · 보호 = 배포 브랜치 `main` 만(reviewer 0 · 주간 무인) |
| (CI 아님) `R2_ACCOUNT_ID` · `R2_ACCESS_KEY_ID` · `R2_SECRET_ACCESS_KEY` | master 로컬 env | publish-site.py `--r2`(S3 API · 그 버킷만) |
| `CYSR_RELEASE_SEQ` | 변수 | release.yml 최상위 env → U1 build.rs 가 build-info release_seq 로 굽는다(태그 전 갱신 · 정수 ≥1) |
| (2판에서 삭제) `AI_JARVIS_PUSH_TOKEN` · `CLOUDFLARE_*` · `UPDATE_FEED_PUBLISH` | — | CI 게시 0(결정 ①) — 설정에 넣지 않는다(이미 넣었으면 지워도 됨) |
| (기존) `TAURI_SIGNING_PRIVATE_KEY`(A2) · `CYS_PACK_SIGNING_PRIVATE_KEY`(P2) | 비밀 | 변화 없음 |

### ⑤ 발행 리허설 순서(태그 드라이런)
| 단계 | 무엇 | 판정 |
|---|---|---|
| R0 | U1 2판 머지 → 이 가지 rebase(★U1 2판 CLI 계약 = HANDOFF-U1 ⑨·§7 ⑷: cysr 에 `--installed-release-seq` 금지 · 출발 seq = `--enumerate-installed`) → `CYS_U3_REQUIRE_ALL=1 CYS_UPDATE_VERIFY_BIN=<머지 트리 디버그 cys> python3 scripts/tests/test_update_publish.py` · CI 맥 두 레인 초록 | 4판 = 91/0(0 건너뜀 · 실측 §9-2) |
| R1 | ①② 키 생성·키링 기입·④ 비밀·변수 | `cys build-info` keyring_ids 4 |
| R2 | 변수 `CYSR_RELEASE_SEQ` 갱신(§1 ③ 1) 뒤 태그 → release.yml draft | 새 스텝 초록: 「CYSR_RELEASE_SEQ 정수 ≥1」(두 잡) · 맥·윈 「동봉 매니페스트 min_binary」 · pack-artifacts 「min_binary」 · 윈 「본문 재료 수집·업로드」(2판: 실패 = 릴리스 실패) |
| R3 | 맥 로컬 빌드 zip → `scripts/update/collect-inputs.sh mac <zip> macos-arm64 inputs/` · `gh run download <run> -n update-inputs-windows-x64 -D inputs/` · draft 자산 받기 | 재료 4종(cdhash·build-info×2·payload 트리) |
| R4 | `make-release-json.py … --build-info macos-arm64=inputs/build-info-macos-arm64.json --build-info windows-x64=inputs/build-info-windows-x64.json --cdhash macos-arm64=$(cat inputs/cdhash-macos-arm64.txt) --a2-sig windows-x64=cysr_<v>_x64-setup.exe.sig --payload-dir windows-x64=inputs/payload-windows-x64 …` → `release-gate.py body --body … --keyring cysjavis-pack/trusted-keys.json --archive-r2 <버킷> --expect-seq <seq>` | rc 0 |
| R5 | U 의식(`sign-release.sh` · 박사님 매체 1단계) → `release-gate.py body --sig …` | rc 0 |
| R6 | §1 ③ 0~4(탐침 rc 0 → 워커 배포 → 보관소 → 폐기문 → 봉투 아티팩트 → 게시) | 각 게시 `--live-check` rc 0 · refresh-feed verify 두 스텝 초록 |
| R7 | release-publish.yml dry_run(새 게이트 = latest.json·min_binary 두 잡) → 승인 → 발행 | — |
| R8 | 캐너리 C1(설계 §7-4) | — |

### ⑥ 발행 기준(3판 · master 가 머지 기준과 가른 것 · 코드 0 · 전부 1.1.8 발행 전 필수)
| 2R # | 항목 | 해소 판정 |
|---|---|---|
| 1 | U1 머지 → 실 R·U·F·A2 공개키 내장(§1 ②) | `cys build-info --json` keyring_ids 4개 · `cargo test --lib packsig::` 초록 |
| 2 | 설치 링크 잠금·위임·윈 본문 보존 = 티켓 `cysr-118-u5-install-link` | U5 완료 보고 + 윈 실기 |
| 14 | ⓪-a 윈 실기 **8** 시나리오(`WIN-NSIS-0A-FIELD.md`) | 결과 칸 8/8 기대대로(F7·F8 = 3판 추가) |
| 17 | strict 0-skip 초록 = 머지 트리 + 맥 CI(ci-branch·release aarch64) | 두 레인 U3 스텝 초록 · 「건너뜀 0」 출력 |
| 18 | payload 제외 규칙 = U2 S9b 가 같은 `scripts/update/payload-exclude.txt` 를 로드 + 불일치 시험(U2 브리프에 master 기록) | U2 시험 이름 1줄 |
| R10 | 서명 기기 분리 안 함 = 잔여 위험 명시(§6 첫 줄) | 이 표의 이 줄이 있음 |

## §2 어느 레인이 어느 게이트를 부르나
| 레인 · 잡 | `release-gate.py` 단계 | 재는 것 |
|---|---|---|
| release.yml build(맥) · build(윈 NSIS) | assets `--bundled-manifest` | 앱 동봉 팩 매니페스트 min_binary 빈 값 = 거부(bundle-prep 수리의 이중 벨트) |
| release.yml pack-artifacts | assets `--pack-manifest` | 서명 팩 매니페스트 min_binary 빈 값 = 거부 |
| pack-release.yml | assets `--asset-list … --pack-manifest` | 팩 단독 릴리스도 latest.json 의무 + min_binary |
| release-publish.yml verify · publish(대칭) | assets `--release-dir --pack-manifest` | latest.json 의무(tombstone 파일이 있으면 바이트 고정) + min_binary · 게이트 자기시험 선행 |
| refresh-feed.yml | verify ×2(U1 `cys update-verify` · 출시 빌드 내장 키링) | ① 현재 봉투 쌍 `--allow-expired --stamp`(통과해야 상속) ② 새 봉투 = 허용 출발 seq 전수 · apply/halt/not_in_rollout 만 · 증표 |
| ci-branch(맥) · release(맥 aarch64) | 시험 test_update_publish `CYS_U3_REQUIRE_ALL=1` + 그 가지 디버그 cys | 건너뜀 1건 = 실패 · ⚠U1 머지 전 적색 = 의도 |
| master(발행 의식) | body · verify | §1 ⑤ R4·R5·R6 |
- 시험 `scripts/tests/test_update_publish.py` 등재 = ci-branch(맥) · release(맥 aarch64) · pack-release + release-publish 두 잡(자기시험) — `lane-parity-rehearsal.sh --strict` rc 0 · `--self-test` rc 0.

## §3 【결정필요】(master 범위 · 각 권고 + 단점 1줄) — ★2판: ①②③ 전부 [master#8db3b908] 로 결정됨(아래는 기록)
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
- 2판 소요(실측 · 커밋 시각): 1/2 = 10:14 지시 → 10:26 `ca4c7b6a`(12분 · 순환 전) · 2/2 = 10:3x 재개 → #3 10:56 · #13 10:59 · refresh-feed 11:01 · #17 11:04 · #1·#18 11:05 · #4 A2 11:08 · worker 11:10 · 윈 문안 11:11 · 게이트·문서 11:1x–11:2x ⇒ **2/2 ≈ 45분**(9항목 · 항목당 ≈ 5분 · 상한 2h 대비 0.4배).
- 저장소 게이트: 브리프의 `tests/commit_gate` 류 파일은 이 저장소에 **없다**(`git ls-files | grep -i commit.gate` 0건) → 대신 secret-scan(변경 파일 전수 clean) · lane-parity(--strict·--self-test) · test_release_verify · nsis 컴파일 하네스 · nsis 모델을 돌렸다.

## §6 미측정 · 남은 위험(정직)
- ★3판 잔여 위험(master 결정으로 수용 · 발행 기준 표에 명시): **F 탈취 = 봉투 halt/동결 권한**(코드 설치 불가 — 본문은 U 서명이 따로 · F 로 본문 서명 = U1 거부) · 완화 = 액션 SHA 핀 · environment `feed` 브랜치 제한 · R 위임문으로 F 폐기. **R10 = 빌드 호스트 장악 시 U 안전을 주장하지 않는다**(minisign 이 이 기기 프로세스라 서명 순간 개인키가 메모리를 지난다 · 네트워크 단절 서명기/HSM 없음 · master 결정 「비용 0」).
- S3Store(R2 조건부 PUT · SigV4)는 **R2 실측 0** — 로컬 가짜 S3 로 의미만 잰다. ★4판(Fable 3R MAJOR-3): **R2 DeleteObject 는 조건부(If-Match)를 지원하지 않는다**(R2 문서) → 삭제 API 를 아예 쓰지 않고 「없앰」 = 묘비 포인터(`{"tombstone": true}`) 조건부 PUT. 첫 R2 게시 전 1회 실측 = 빈 키에 `If-None-Match: *` PUT 두 번(둘째 412) · 낡은 ETag 로 `If-Match` PUT(412).
- BACKLOG(다음 판 · Fable 3R MINOR 9 · master 판정): restore 탈출구 입력 무검증 · 중복 revoked_releases 거부 · agora-client min_from=0 경계 · rc 5 인쇄 형식 · 묘비 위 봉투 단조 시험 · ETag `W/` 접두 · 주석 3.
- 윈 재료 수집(무인 설치로 payload 측정)과 refresh-feed.yml 은 **러너에서 한 번도 안 돌았다**(이 기계엔 윈 실행 기층·GitHub 실행 0) — 첫 발행 리허설(§1 ⑤ R2·R6)이 첫 실측. 2판부터 윈 수집 실패 = 릴리스 실패(첫 실측에서 수집기가 틀리면 태그가 적색 — 되돌리기 = 그 스텝 수리 뒤 재태그).
- update-worker · cf-route-probe 는 **Cloudflare 에서 한 번도 안 돌았다**(워커는 node 하네스로 같은 배치를 서빙해 잼 · 탐침의 `wrangler delete --force` 철자 미확인) — §1 ③ 0 이 첫 실측.
- ⓪-a 의 동작 증거 = 윈 실기 8 시나리오(`WIN-NSIS-0A-FIELD.md`)가 첫 실측 — 이 기계 근거는 컴파일·소스 핀·모델(3판: ⓪-a 결정 나무 270 상태 · 손으로 맞춘 거울)뿐.
- payload 제외 규칙(`scripts/update/payload-exclude.txt` · 수집기 무삭제)이 S9b 와 맞는지(설치기 생성 파일이 판마다 같은지 미측정) = U2 S9b 설계와 대조 필요.
- GitHub 맥 러너에서 `hdiutil attach`(가짜 매체 시험)가 되는지 미측정 — 안 되면 그 묶음만 실패한다(ci-branch 맥 첫 실행이 잰다).
- `bunx wrangler@3` 판 고정은 실제 사용 판과 대조하지 않았다(update-worker 배포·R2 게시 첫 실행이 잰다).

## §7 재현
- `git log --oneline 7e7aa5da..HEAD` · `python3 scripts/tests/test_update_publish.py`(단독) · U1 왕복 = U1 커밋본 작업트리에서 `cargo build --bin cys` → `CYS_UPDATE_VERIFY_BIN=<그 cys> python3 scripts/tests/test_update_publish.py`
- `bash scripts/tests/nsis-hook-compile/run.sh` · `python3 scripts/tests/nsis-hook-model/model.py` · `bash scripts/lane-parity-rehearsal.sh --strict`
- 2판: CI 와 같은 엄격 모드 = `CYS_U3_REQUIRE_ALL=1 CYS_UPDATE_VERIFY_BIN=<디버그 cys> python3 scripts/tests/test_update_publish.py`(건너뜀 = 실패) · `python3 scripts/tests/test_release_verify.py` · update-worker = 같은 스위트의 `TestUpdateWorker`(node 필요) · `bash scripts/update/cf-route-probe.sh`(드라이런) · `bash scripts/secret-scan.sh $(git diff --name-only c3582be6..HEAD)`

## §8 codex 1R 반영표(2판 · 원문 `~/axdev/master/reports/REVIEW-U3-codex-1r.md` · BLOCK 14 · MAJOR 5)
| # | 지적(요지) | 처방(이 가지) | 커밋 | 시험(음성 = 뮤테이션) | 잔여(코드 밖 · 누가) |
|---|---|---|---|---|---|
| 1 | release_seq 미주입 · 키링 미기입 | release.yml 최상위 env `CYSR_RELEASE_SEQ` + 두 빌드 잡 「정수 ≥1」 스텝 · 게이트 `--expect-seq` · 게시기 「최댓값 + 1」 | `ca4c7b6a` · `bc1ab479` | `test_release_yml_seq_and_win_inputs`(스텝 삭제 = 적색) · 보관소 역행·건너뜀 거부 | 키 생성·키링 기입 = U1 머지 뒤 master(§1 ①②) |
| 2 | 설치 링크 참가자 미구현 | 명세 유지 + 별도 티켓 포인터 | `c11ee1d8` | — | **`cysr-118-u5-install-link`**(외부 저장소 · 윈 실기) |
| 3 | 오프라인 서명 우회 손잡이 · 키가 호스트에 닿음 | 손잡이 3종 = `CYS_SIGN_DEV=1` 전용(밖에서 보이면 거부) · 개발 모드 실 키링 key id 거부 · `gen-offline-key.sh`(생성 = 매체 안 · R 둘째 벌 매체→매체) | `181fd516` | 손잡이 밖 거부 2 · 대기 0 거부 · 실 key id 거부 · 생성 4(뮤테이션 3 적색) | 서명 기기/HSM 분리 = 범위 밖(§1 ① ⚠ · master 판단) |
| 4 | 게이트·게시기 서명 진위 미검증 · A2 key id 만 | U·R·F 암호 검증 + 통과 증표(게시기는 증표 + 재검증) · 7-b = 자산 바이트 암호 검증(직전 conf pubkey · 없으면 `A2_PUBKEY`) | `ca4c7b6a` · `b155da22` | 같은 key id 위조 서명 · 다른 바이트 서명 = 거부(검증 삭제 = 적색 2) · test_release_verify 픽스처 = 실서명 | — |
| 5 | R 생성기 직전 폐기문 미인증 | 직전 `.minisig` R 암호 검증 · rev = 직전 + 1 · 집합 단조 포함 · 시각 단조 | `ca4c7b6a` | 위조 prev(rev 999 · R 아닌 키) · 시각 역행 · 집합 단조 = 구조(직전 집합 ∪ 새 항목 · 빼기 = `--drop-delegation` 만 · 음성 시험 없음) | — |
| 6 | 주간 CI 가 미인증 현재 봉투 상속 | make-envelope = U1 증표 있는 직전만 · refresh-feed = 현재 봉투 verify `--allow-expired --stamp` 먼저 | `ca4c7b6a` · `ea940902` | 워크플로 사슬 U1 왕복(위조 현재 봉투 = 증표 0 = 상속 0 · 증표 확인 삭제 = 적색) | — |
| 7 | 게시기 전역 seq 단조 없음 | archive = 색인 최댓값 + 1 만(첫 = `--first`) | `ca4c7b6a` | 역행·건너뜀·색인 없음 | — |
| 8 | 게시 TOCTOU · 쌍 비원자 | 불변 객체 `obj/<sha>` + 단일 포인터 교체 · flock + 잠금 안 재검사 | `ca4c7b6a` | 동시 게시 2 · 포인터 원자 | — |
| 9 | CI 게시 스위치 = 승인 게이트 아님 · 비밀 과다 | CI 게시 **삭제**(생성+검증+아티팩트) · 사이트·CF·PAT 비밀 0 · 게시 = master 로컬 R2(전용 워커) | `ea940902` · `62a6f1fa` | 워크플로 형태 핀(비밀 = F 둘뿐 · wrangler/push/publish 0) | 액션 SHA 고정·F 서명 잡 보호 환경 = 미처리(📌 master) |
| 10 | payload_manifest = U1 계약 밖 | 게이트 = 반환 행 **전체** 대조(칸 대기 = 사유 인쇄) | `ca4c7b6a` | 양성만(U1 왕복 apply 행 전체 일치) · 음성(칸 불일치) **미시험**(U1 반환을 변조할 손잡이 없음) | U1 `Asset` 에 칸 추가 = U1/U2(master 전달) |
| 11 | refresh 가 installed 0 으로 검증 | 기본 = 허용 출발 seq 전수 + seq 자신 uptodate · 워크플로에서 `--installed-release-seq` 삭제 | `ca4c7b6a` · `ea940902` | `1,2,3,4,5` 전수 · 형태 핀 | — |
| 12 | URL 생산자 검사 > U1 | component별 홉 표 = U1 과 같은 벡터(`url-vectors.json`) | `ca4c7b6a` | 벡터 양쪽 | — |
| 13 | NSIS ⓪-a 조건 3개 생략 | ⑴ 토큰+잠금 없음 = exit 6 ⑵ 인자 = env(StrCmpS) ⑶ 조상 = 러너 §3-7 ④(인용 주석) ⑷ 위임 = ⑴⑵ 뒤 한 곳 | `9a2489f3` | 소스 핀(뮤테이션 3 적색) · 컴파일 · 모델 재핀 | 실행 증거 = #14 |
| 14 | ⓪-a 실행 시험 0 | 윈 실기 6 시나리오 문안(차리기 PowerShell + 판정 줄) | `c11ee1d8` | — | **윈 master 실기**(`WIN-NSIS-0A-FIELD.md` · 실패 1 = 채택 보류) |
| 15 | 키 만료·서명 시각 역행 미검사 | `find_key` 만료 · 신뢰 시각(HTTPS Date 대조) · 미래·역행 거부(생성·서명·게시) | `ca4c7b6a` | 만료 키(`test_mut_expired_key` · 2판 추가) · 미래 signed_at · 역행 | — |
| 16 | 배포·커밋 비원자 · 라이브 서명 미확인 | CI 게시 삭제 · 게시기 `--live-check` = 본문·서명 두 sha 대조(아니면 rc 4 + 되돌리기 명령) | `ca4c7b6a` · `ea940902` | 형태 핀(CI 게시 0) · live-check 불일치 **미시험**(재시도 30초 · 로컬 서버 필요) | 첫 R2 게시가 잰다 |
| 17 | 시험 수 재현 안 됨 · U1 왕복 skip | CI 맥 레인 = 디버그 cys 주입 + `CYS_U3_REQUIRE_ALL=1`(전제 부재 = 모듈 오류 · 건너뜀 = 실패) | `cc7390e8` | 전제 부재 rc 1 실측 · 72/0 건너뜀 0 | U1 머지 전 두 레인 적색 = 의도 · hdiutil 러너 가능 여부 = 첫 CI 실행이 잰다 |
| 18 | 윈 payload 실패해도 릴리스 · uninstall.exe 임의 제외 | 수집·업로드 `continue-on-error` 삭제(`if-no-files-found: error`) · 수집기 무삭제 + 공유 제외 규칙 `payload-exclude.txt` | `ca4c7b6a` · `bc1ab479` | 형태 핀(되돌리면 적색) | 제외 규칙을 U2 S9b 와 대조 = U2 |
| 19 | `--allow-older-release` 우회 · 판 문자열 과잉 강제 | 후퇴 예외 삭제(같은 본문 재서명만 seq 같음 허용) · 순서 = release_seq 하나 · 판 문자열 = 비보안 경고 | `ca4c7b6a` | 채널 후퇴 거부 | — |
- 📌 내가 범위 밖이라 **하지 않은 것**(필요하면 지시): ① #9 의 액션 SHA 고정·F 서명 잡 `environment:` 보호(설정 = GitHub · master) ② #14 를 이 기계에서 더 당기는 「⓪-a 블록 미니 해석기 시험」(소스 텍스트를 그대로 실행하는 파이썬 해석기 · 실기 대체 아님) ③ #3 서명 기기 분리.

## §9 codex 2R 반영표(3판 · 원문 `~/axdev/master/reports/REVIEW-U3-codex-2r.md` · master 판정 [master#9219ca05] = 머지 기준 / 발행 기준)
| # | 2R 지적(요지) | 분류 | 처방(이 가지) | 커밋 | 음성 시험(뮤테이션 = 적색 확인) |
|---|---|---|---|---|---|
| 1 | 실 키링 비어 있음 | 발행 | §1 ⑥ 표 · U1 머지 뒤 §1 ② | — | — |
| 2 | 설치 링크 = 명세뿐 | 발행 | U5 티켓 · §1 ⑥ | — | — |
| 3 | `CYS_SIGN_DEV` 하나로 우회 | 머지 | 실 의식 lib·스크립트 env 손잡이 **0**(고정값) · 대역 = `lib/offline-sign-dev.sh`(시험 사본 트리만 · 매체 부모 = 임시 폴더만 · 실 키링 id 거부) | `d45255b9` | 손잡이 코드 0 핀 · 실 스크립트에 손잡이 줘도 /Volumes 거부 · 대기 0 거부 · 대역의 /Volumes 거부 |
| 4 | 증표 = 서명 없는 JSON | 머지 | 증표 신뢰 **폐지**(정보용) · `u1verify.verify_envelope` 한 함수 · 게시기 envelope = `--cys` 필수 U1 직접 재실행(게시된 폐기문과 함께) · archive·revocations = 키링 암호 재검증 | `cd4c7152` | 위조 증표+변조 본문 = rc 2 · F 정상 서명이지만 U1 만 거부하는 봉투 = 「U1 재검증 거부」(U1 호출 삭제 = 적색) |
| 5 | severity 약화 통과 | 머지 | `check_revocations_successor`(항목 전체 보존 · advisory→stop_seats 만 · reason 변경 거부 · 위임 항목 변경 거부) — 생성기·게이트·게시기 공용 · 생성기 = 승격만 | `cd4c7152` | stop_seats→advisory · reason 변경 = 게이트 rc 1 · 게시 rc 2(약화 허용 뮤테이션 = 적색) · 승격 = rc 0 |
| 6 | 상속기 = 증표만 신뢰 | 머지 | make-envelope `--prev-envelope` = `--cys`·`--revocations` 필수 U1 재검증(만료 ⓔ 만 허용) · refresh-feed 배선 | `cd4c7152` | 위조 현재 봉투 + 위조 증표 = 「U1 재검증 거부」 · `--cys` 없음 = rc 2 |
| 7 | — | 해소(2R) | — | — | — |
| 8 | R2 무조건 PUT · 포인터→색인 중단 | 머지 | store = CAS(`If-None-Match: *` 객체 · `If-Match` 포인터 · FsStore flock · S3Store 표준 라이브러리 SigV4) · 보관소 = **세대 포인터 한 객체**(포인터+색인) | `cd4c7152` | ETag 불일치·이미 있음 = CasFail(Fs·가짜 S3 둘 다) · 객체만 있는 중단 상태 재실행 = 색인까지 완성(멱등 아님) |
| 9 | F environment 없음 · 가변 태그 | 머지 | 전 워크플로 서드파티 액션 48곳 SHA 핀(+ 태그 주석) · rust-toolchain `toolchain: stable` 명시 · refresh-feed `environment: feed`(브랜치 제한만 · reviewer 0 = master 결정) · 잔여 위험 §6 | `90af8cd9` | 핀 시험(40자 SHA · 주석 · toolchain · environment) |
| 10 | payload_manifest 비교 생략 | 머지 | U1 2판 칸 → 전체 행 대조에 포함 · 대기 분기 삭제 | `4991230b` | U1 반환에서 칸 누락 · 한 항목 sha 변조(대역 래퍼) = rc 1 |
| 11 | low-1·seq+1 경계 미검사 | 머지 | cysr = 열거 범위 = max(min_from,1)..=seq **정확 일치** · 후보 = uptodate · agora-client = low-1 ⓛ 거부·seq·seq+1 uptodate · 상한 64 | `4991230b` | 범위 하한·후보 빠짐 · 후보 apply · low-1 apply/엉뚱한 단계 · seq+1 apply · 상한 초과(U1 호출 전 거부) |
| 12 | — | 해소(2R) | — | — | — |
| 13 | NSIS 잠금 해제 경합 · 조상 pid | 머지 | 핸들을 끝까지 쥐고 대조 뒤 같은 핸들로 재시도(`cys_txn_recheck`) · 풀렸으면 exit 6 · 판정 불가 = 위임 불가 · 조상 pid = 러너 유지(기각 · §3-7 ④ 주석) | `e6e7ae5c` | 소스 핀(재확인 우회 뮤테이션 = 적색) · 모델 Z6 |
| 14 | ⓪-a 실행 0 · 모델 제외 | 머지+발행 | model.py = ⓪-a 결정 나무 포함(270 상태 · Z1~Z6) · 윈 실기 = 8 시나리오(F7 대조 중 해제 · F8 타 프로세스 뮤텍스) | `e6e7ae5c` · 이 문서 | 모델에서 재확인 갈래 삭제 = Z1 위반 · 실기 = 발행 기준 |
| 15 | 게시기 signed_at 직접 검사 안 함 | 머지 | 게시 단계에서 신뢰 시각(미래 거부) + 직전 게시본 signed_at(역행 거부) — 세 종류 모두 | `cd4c7152` | (생성 쪽 미래·역행 시험 유지) · 게시 쪽 = U1 재검증 음성과 같은 경로 |
| 16 | live-check 실패 뒤 복구 없음 | 머지 | 불일치 = 옛 포인터로 ETag 조건 자동 되돌리기(rc 4 · 첫 게시 = 조건부 삭제) · 되돌리기 CAS 실패 = rc 5 + 실행 가능한 `restore` 1줄 | `cd4c7152` | 로컬 서버 불일치 주입 = rc 4 + 세대 포인터 원복 · 경쟁 주입 = rc 5 → 인쇄 명령 실행 = 복구 |
| 17 | strict 0 tests | 발행 | §1 ⑥ 표(머지 트리 + 맥 CI) · 이 기계 strict 87/0 건너뜀 0 | — | — |
| 18 | 제외 파일 U3 만 읽음 | 발행 | §1 ⑥ 표(U2 S9b 로드 + 불일치 시험) | — | — |
| 19 | 같은 seq 다른 본문 허용 | 머지 | make-envelope = 같은 seq 면 직전 봉투 원문·서명과 바이트 동일만 · 게시기 envelope = 실은 본문·서명 = 보관소 세대 포인터 객체와 바이트 동일 | `cd4c7152` | 다른 notes_ko 같은 seq = 「재서명 거부」 · 보관소에 없는 seq 봉투 게시 = rc 3 |
| 워커 | 502 한쪽만 | 머지 | 포인터의 두 객체 모두 검사 · 하나라도 불일치 = 둘 다 502 · 세대 포인터 정확 키 조회(`05` 404) | `cd4c7152` | 본문 객체 변조 = [502, 502] |
| HANDOFF | 첫 게시 `--first` 누락 | 머지 | §1 ③ 2·3 정정(게이트·게시 둘 다 · 둘째부터 없음) | 이 문서 | — |
- 잔여(정직): S3Store = **R2 실측 0**(가짜 S3 로만) — R2 조건부 DELETE 지원 여부 미확인(§6) · 모델의 ⓪-a 는 손으로 맞춘 거울(훅을 실행하지 않음) · agora-client 열거 경계는 대역 cys 로만 쟀다(U1 실물 agora 픽스처 없음).

## §9-2 Fable 3R 반영표(4판 · 원문 `~/axdev/master/reports/REVIEW-U3-fable-3r.md` · master 판정 [master#4468fec2] = 머지 BLOCK 0 · 소수정)
| 항목 | 처방 | 커밋 | 시험 |
|---|---|---|---|
| MAJOR-1 열거 행 중첩 드리프트 | u1verify = 행 `outcome` 안의 판정·asset 을 읽음(없으면 GateFail) · 대역 래퍼 편집도 중첩으로 | `a0afcb09` | U1 가지 `feed::render_enum_row` 소스 핀(키 `installed_release_seq`·`outcome`) · U1 HEAD 사본 빌드 왕복 |
| MAJOR-2 첫 판 seq 1 영원 거부 | `lo == seq` = 후보 uptodate 1행으로 통과(`lo > seq` 만 거부) · U1 cli 공동 수정 = 291 | `a0afcb09` | seq 1(min_from 0) 봉투 = 통과 · 후보 apply = 거부(U1 의 「출발 seq 없음」 거부만 대역이 걷음) |
| MAJOR-3 R2 조건부 DELETE 미지원 | 삭제 API 제거 · 없앰 = 묘비 포인터 조건부 PUT · load 가 묘비 = 없음 · 워커 묘비 = 404 | `c786d463` | live 불일치 되돌리기 = 묘비 · 묘비 위 재게시 · rc 5 → restore = 묘비 · 가짜 S3 = DELETE 0 · 워커 [404, 404] |
| MINOR-2 시험 시각 env | 실 의식 셸 진입에 `CYS_SIGN_DEV`·`CYS_TEST_NOW` 가 있으면(빈 값 포함) rc 2 | `d60139ff` | sign-release 3 · gen-offline-key 1 · 손잡이 핀 = 그 이름은 거부 줄에만 |
| 주석 | tauri-action 핀 = `action-v0.6.2`(gh api 로 같은 커밋 확인) | `d60139ff` | SHA 핀 시험 |
| MINOR 9 | 다음 판 BACKLOG(§6 1줄) | 이 문서 | — |
- 게이트(12:1x 실측 · U1 HEAD `e1034052` 사본 빌드 sha256 `05336d34…` · 라이브 트리 아님): test_update_publish strict **91/0 · 건너뜀 0** · 단독 91/0 + 14 건너뜀 · test_release_verify 140/0 · nsis 컴파일 OK · 모델 39082 + ⓪-a 270 OK · lane-parity strict/self-test 0 · secret-scan clean(4판 변경 7 파일) · 워커 node --check OK.

