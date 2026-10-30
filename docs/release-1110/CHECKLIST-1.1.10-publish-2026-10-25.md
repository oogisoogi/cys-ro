# cysr 1.1.10 발행 집행 체크리스트 — 2026-10-23(금)

> ★발행일 당김(2026-10-23 · TICKET=cysr-1110-publish-today): 10-25(일) → **10-23(금)** — 박사님 「1.1.10 발행을 오늘 할 수 있는가? 내일 오전 워크숍에서 참가자들이 설치하고 올 수 있도록」(11:1x). 절단(태그)과 발행이 같은 날이 된다. 파일 이름의 `2026-10-25` 는 참조(`.github/workflows/release.yml` · `docs/HANDOFF-cysr-1110-integrate-2026-10-21.md`)를 깨지 않으려고 그대로 둔다.

초안 · TICKET=cysr-1110-release-prep · 2026-10-22 · worker-3(surface:1550) · 집행 = master(비가역 줄 ⛔) · U 서명 = 박사님 USB · 카톡 발송 = 박사님
날짜 실측: `date -j -f %Y-%m-%d 2026-10-23 +%A` = 금요일(절단 · 발행 — 당김으로 같은 날 · 원래 발행 `… 2026-10-25 …` = 일요일) · `… 2026-10-31 …` = 토요일(현 봉투 만료일 · §5-12).
견본 = 1.1.9 체크리스트(`git -C ~/cys-terminal-src show d8e8f0a2:docs/release-119/CHECKLIST-1.1.9-publish-2026-10-18.md`) + **1.1.9 의 실제 집행 기록**(아래 「1.1.9 실제」 열 · 출처 = `~/axdev/master/SESSION_STATE.md` 줄 = SS:n · master 대화 기록 10-16~17 = T1 · 설치기·사이트 인계 `~/axdev/.wt/hab-r8-pub119/docs/HANDOFF-119-r7-2026-10-17.md` = H7).
정본 순서 = `docs/RELEASE.md:32-42`(1~7단계) · 자동 갱신 = `docs/update/HANDOFF-U3.md` §1 ③ · 롤백 = `docs/RELEASE-ROLLBACK.md`.
판정표 = `docs/upstream/INTEGRATE-1.1.10.md` · 윈 실기 = 같은 폴더 `WIN-FIELD-1.1.10.md` · 문안 초안 = `RELEASE-NOTES-1.1.10.draft.md` · `KAKAO-1110.draft.md`.

실측 출발점(2026-10-22 01:3x · 읽기만):
- `cys pack-plan`(이 맥 설치본 · 쓰기 없음) = 바이너리 1.1.9 · 항목병합 1(schedule.json) · 보존+병합대기 4(agents.json · CSO/REVIEWER/WORKER 지침) · 보존 5 · 폐기지만보존 1 · 변화없음 481 · 기존 병합대기 13.
- 통합 가지 `rel/1.1.10` = **53031718**(이 문서를 쓴 시점 · 좌석 546 이 지침 출처 표기 3건을 고치는 중이라 머리가 바뀐다 — 태그 커밋은 그 뒤 머리 + 판 올림 + 발행 준비 문서 커밋).
- 판번 = 아직 **1.1.9**(7파일 · §A-3) · `UPSTREAM_BASE` = `v0.14.51`.
- 공개 latest = v1.1.9(2026-10-16T23:25:58Z) · 보관소 `releases/4.json` 200 · **`releases/5.json` 404** · 저장소 변수 `CYSR_RELEASE_SEQ` = 4 · stable/next 봉투 feed_rev **3** · rollout 100 · halt false · signed_at 10-17 08:29/08:31 KST.
- origin/main = **fb386c49**(v1.1.9 d8e8f0a2 + refresh-feed CI 패치) · `git merge-base --is-ancestor fb386c49 53031718` = **참**(이번 판은 main 을 앞으로 감기만 하면 된다 — §3-5).

---

## A. 이번 판 고유 단계(1.1.9 에 없던 것)

### A-1. 원작자 v0.14.51 편입 — 표기·고지

| # | 할 것 | 근거 | 상태 |
|---|---|---|---|
| A-1-1 | `UPSTREAM_BASE` = `v0.14.51` 확인(태그 트리에서 `git show v1.1.10:UPSTREAM_BASE`) | 루트 파일 1줄 · 마지막 변경 `ba38b6aa`(vendor 병합) · 읽는 코드 0(`git grep -i upstream_base -- scripts .github src src-tauri ui cysjavis-pack` 0건) | 값 실재(High) |
| A-1-2 | 태그 메시지에 원작자 판 표기 — 1.1.9 꼴 `cysr v1.1.9 (based on cys 0.14.44~48 · int/1110-upstream)`(T1 23:37:22) → **`cysr v1.1.10 (based on cys 0.14.49~51 · rel/1.1.10)`** 권고 | CYS-UPDATE-POLICY §0-2 7 「About/릴리스 노트 based on cys X.Y.Z」 | 권고 |
| A-1-3 | ⚠**About 화면 「based on cys 0.14.51」 = 구현 안 됨** — 앱·문서 어디에도 그 표기가 없다(`git grep -i 'based on cys'` 0건 · 0.14.48 편입 때도 없었음 · `docs/HANDOFF-cysr-1110-vendor-2026-10-21.md:104` §6-3 「새 기능이라 이 티켓에서 만들지 않았다」). 이번 판은 **발행 노트 끝 줄**(「cysr 는 cys 터미널(github.com/idoforgod/cys-terminal)에서 출발했습니다」 + 개발록판 「원작 판 0.14.51 까지 들여옴」)과 태그 메시지로만 표기한다. About 표기는 다음 판 후보로 남긴다 | 정책 §0-2 7 은 「About/릴리스 노트」 — 노트 쪽으로 요건의 한 갈래는 채운다(해석) | **고지**(master 판단: 이 판은 노트 표기로 갈음 · About = 다음 판) |
| A-1-4 | 편입 판정표·codex 1R 원문이 태그 트리에 있는지: `docs/upstream/MERGE-0.14.49-51-PLAN.md` · `REVIEW-0.14.49-51-codex-1r.md`(개인 경로 `~` 치환 · `349c3ce0`) | INTEGRATE §4 · H-SECRET-1 GREEN(853파일) | 실재 |
| A-1-5 | 편입 실측 기록 표(정책 §0-2 6 · 소요·충돌 파일 수·리뷰·CI·회귀) — vendor HANDOFF §7 이 그 자리. 3회 P50/P90 집계는 이번이 2회째(0.14.44~48 · 0.14.49~51) | vendor HANDOFF §7 | 기록 있음 · 집계 = 다음 편입 뒤 |
| A-1-6 | 팩 지침 문구 ⚠3갈래(원작자 편입분 · INTEGRATE §5) — ⑴ `CEO_TEMPLATE.md` 「오너 원문」·「주인님의 명령」 = **원작자 오너**(System 소유 → 전 설치 강제) ⑵ `CSO_DIRECTIVE.md` 「(오너 지시 2026-10-12)」 표기가 CEO 쪽 「원작자 S8 · v0.14.51 편입」 과 갈림 ⑶ 근거 주석 포인터 `CHARTER-RATIONALE.md` = 팩 루트 | 좌석 546 이 「지침 출처 표기 3건」 을 고치는 중(브리프 §0) — 그 커밋이 ⑴~⑶ 을 덮는지 **태그 전 대조** | **태그 전 확인**(546 커밋 뒤) |

### A-2. 휴지통 — 화면과 네이티브를 같은 판으로 함께 내보내기

1.1.10 의 휴지통 삭제는 **화면(UI)이 받은 1회용 확인을 앱 네이티브가 꺼내 쓴 뒤에만** 데몬에 삭제를 보낸다(trash-harden M1 A안). 화면만 새것이거나 네이티브만 새것이면 정상 삭제가 「지우지 않았습니다」로 거부된다(삭제 0 = 안전 쪽이지만 기능이 막힌다). 그래서 둘이 **한 커밋 · 한 번들**에서 나와야 한다.

| # | 할 것 | 확인 줄 | 상태 |
|---|---|---|---|
| A-2-1 | 같은 커밋: 화면 `ui/src/trashconfirm.ts`·`ui/src/main.ts`(삭제 명령의 `confirmNonce`·`typed`) ↔ 네이티브 `src-tauri/src/main.rs`(`trash_preview_poll` 발급 · `trash_delete` 꺼냄) | 병합 `19af40c4` 에서 trashconfirm.ts·main.rs = 가지 `810dcbd0` 와 바이트 동일 · main.ts 추가 10줄 10/10 실재(INTEGRATE §2 ⑦) | 확인됨(통합 가지) |
| A-2-2 | **맥 zip 2종 = 태그 커밋에서 로컬 빌드**(UI 는 앱 바이너리에 내장) — 빌드 작업트리의 `git rev-parse HEAD` = 태그 커밋 · `git status --porcelain` 빈 줄 | 빌드 직전 2줄 출력 기록 | 집행 때 |
| A-2-3 | 맥 번들 실림: `strings <cysr.app>/Contents/MacOS/cys-app \| grep -c confirmNonce` ≥1 · `… \| grep -c confirm_nonce` ≥1 (arm64·x64 각각) | 통합 가지 1.1.9 판번 번들에서 둘 다 1(INTEGRATE §3) | 집행 때 재측 |
| A-2-4 | 윈 번들 실림 = CI 윈 NSIS(태그 레인) · 실기에서 휴지통 삭제 시도 1회(윈은 삭제 기능 꺼짐 → 「이 빌드에서는 삭제가 꺼져 있습니다」 · `confirm_unbound` 안 뜸) | `WIN-FIELD-1.1.10.md` TRASH-2·TRASH-4 | 윈 실기 |
| A-2-5 | 옛 데몬 + 새 앱 조합(갱신 도중 잠깐): 화면은 빈 휴지통이 아니라 「휴지통을 열 수 없습니다 — 데몬을 업데이트하세요」(`ui/src/main.ts` 휴지통 오류 갈래 · 사용자 변화 조사 2-1) — 삭제 0 쪽이라 발행 차단 아님 | 코드 판독(Med) | 고지 |
| A-2-6 | 윈도우 교차 타입체크(맥): `sh scripts/win-typecheck.sh` rc 0 — 이 맥에 `x86_64-pc-windows-msvc` 타깃 설치됨 · 통합 가지에서 **아직 안 돌림**(INTEGRATE §3 기록 0 · `target/win-typecheck` 없음). `src/dirat.rs`(`#[cfg(unix)]`)·trash.rs·factory_reset.rs 윈 분기를 맥에서 잴 수 있는 유일한 수단 · 링크·실행은 CI·실기 | 1-2 의 4종 안에 이미 있음(1.1.9 체크리스트 1-2) | 1-2 에서 |

### A-3. 판번 1.1.9 → 1.1.10 올림 위치(⚠아직 올리지 않는다 — 판 올림 = master)

1.1.8·1.1.9 판 올림 커밋(`7d7902d9` · `b3a10860`)은 둘 다 **7파일 · 8줄 추가·8줄 삭제 · 덩어리 위치까지 같다**. 정본 = `docs/RELEASE.md:133-165` §0 「게이트 강제 8곳」 · 검사기 = `scripts/version-check.sh:49-56`.

| 파일:줄(53031718 실측) | 지금 문구 | 바꿀 값 |
|---|---|---|
| `Cargo.toml:9` | `version = "1.1.9"` | `"1.1.10"` |
| `src-tauri/Cargo.toml:3` | `version = "1.1.9"` | `"1.1.10"` |
| `src-tauri/tauri.conf.json:4` | `"version": "1.1.9",` | `"1.1.10"` |
| `ui/package.json:4` | `"version": "1.1.9",` | `"1.1.10"` |
| `dist-win/cys.wxs:3` | `… Version="1.1.9"` | `"1.1.10"` |
| `dist-win/cys-x64.wxs:3` | `… Version="1.1.9"` | `"1.1.10"` |
| `Cargo.lock:759`(`name = "cys-app"` :758) | `version = "1.1.9"` | 손으로 고치지 않음 → `cargo update --workspace --offline` |
| `Cargo.lock:777`(`name = "cys-terminal"` :776) | `version = "1.1.9"` | 위와 같음 |

⛔**바꾸면 안 되는 줄**: `Cargo.lock:1199` = 의존 패키지 `flate2` 의 판 `1.1.9`(우리 판번 아님) — **일괄 치환 금지**의 이유.
없는 자리: 루트 `package.json`·`src-tauri/Cargo.lock` 없음 · 앱 상단바 판번(`ui/src/main.ts:10322` `invoke("app_version")`) = 동적.

판 올림 커밋 **밖**, 발행 준비 커밋으로 바꾸는 곳(1.1.9 = `595a887e` · 체크리스트 0-4) — ⚠태그 **전에** 들어가야 태그 트리에 실린다:

| `docs/index.html` 줄 | 지금 | 바꿀 값 |
|---|---|---|
| :36 | `최신 판 <b id="ver">v1.1.9</b>` | `v1.1.10` |
| :43 | `…/download/v1.1.9/cysr-macos-arm64-v1.1.9.zip` | `v1.1.10/cysr-macos-arm64-v1.1.10.zip` |
| :48 | `…/download/v1.1.9/cysr-macos-x64-v1.1.9.zip` | `v1.1.10/cysr-macos-x64-v1.1.10.zip` |
| :53 | `…/download/v1.1.9/cysr_1.1.9_x64-setup.exe` | `v1.1.10/cysr_1.1.10_x64-setup.exe` |
| :58 | `…/download/v1.1.9/cysr_1.1.9_x64-setup.zip` | `v1.1.10/cysr_1.1.10_x64-setup.zip` |
| :69 | 주석 `실패 시 위 정적 v1.1.9 링크가 폴백.` | `v1.1.10` |
| :74 | 주석 `// 예: v1.1.9` | `v1.1.10` |

- Pages(`oogisoogi.github.io/cys-ro/`) = **404**(10-22 실측 · 1.1.9 체크리스트 §5-9 의 「Pages 생존 미확인」 결말) — 이 파일은 공개 화면에 안 보일 수 있다. 바꾸는 이유 = 태그 트리의 문서 현행성(publicdocs 게이트 · `ui/src/publicdocs.test.ts` 가 `docs/index.html` 을 검사 대상에 명시).
- `USER-MANUAL.md`(루트 · `docs/USER-MANUAL.md` 아님) 판번 표기 = **이번엔 바꿀 것 없음**: 「1.1.10」 0 · 「1.1.9」 26(전부 「1.1.9 에서 생긴 기능」 표기 = 역사) · 「1.1.8」 9 · `git diff v1.1.9 HEAD -- USER-MANUAL.md` = 0줄. ⚠그러나 **내용**이 현행과 어긋난 곳 2 → §0-7(이 가지에서 해소).
- 역사 기록이라 바꾸지 않는 `1.1.9` 적중 = 83파일 242줄(코드 주석·시험 픽스처 30 · UI 16 · 문서 37 · 설명서 26줄) — 전체 적중 92파일 284줄.
- 판 올림 뒤 동봉 팩 매니페스트 하한은 자동으로 1.1.10(`scripts/bundle-prep.sh:59` · `CYS_PACK_MIN_BINARY` 를 넘기는 곳 0) ↔ 서명 레인 값(§A-4) — 1.1.9 §7 메모와 같은 꼴 · 동봉본은 그 앱과 함께 가므로 실해 0.
- `docs/RELEASE.md:72` 가 「이 문서 §0-A 2단계의 리터럴」 을 하한과 같은 커밋에서 갱신하라고 적었는데 RELEASE.md 에 §0-A 가 없다 — 그 리터럴은 `docs/legacy/RELEASE-upstream.md:474` 「현행 1.1.7」(이력 문서) · 두 레인 현행 1.1.8 과 어긋남. 문서 끊김 고지(발행 차단 아님).

### A-4. 팩 하한(min_binary) = **1.1.10 확정**(master#c5547f8b ⑵ · 2026-10-22 01:51)

**정본 근거(master 채택)**: 옛 바이너리(1.1.8·1.1.9) + 새 팩(1.1.10) = **옛 14일 자동 삭제는 없어지고(새 팩) 휴지통 화면·데몬 `trash.*` 는 없다(옛 바이너리)** → 지우는 길이 하나도 남지 않아 격리분이 무한히 쌓인다. 새 팩이 새 바이너리의 휴지통만을 유일한 삭제 길로 지시하므로, 「팩이 새 바이너리 표면을 지시하면 그 판으로 상향」 규칙의 뜻에 해당한다(아래 사실 표 「CLI 밖 새 의존 1건」 · 「귀결 — 하한 1.1.8 유지 시」).
집행: 두 레인 `'1.1.10'` = 같은 커밋 · 태그 전(이 가지 별도 커밋 — §7) · 본문 칸 `--requires-min-binary-for-pack 1.1.10`(§6) · 시험 핀 통과 확인.

규칙 = `docs/RELEASE.md:52-82` 「바이너리 릴리스가 새 CLI 표면(플래그·서브커맨드)을 추가하고 팩이 그것을 지시하면 … 하한을 그 버전으로 올려라 · 두 레인 같은 커밋」.
고치기 전 값: `.github/workflows/release.yml:1419`(⑶ 템플릿 수리로 5줄 밀림 · 전 :1414) `PACK_MIN_BINARY: '1.1.8'` · `.github/workflows/pack-release.yml:89` `PACK_MIN_BINARY_OVERRIDE: '1.1.8'` · 시험 핀 `src/bin/cys.rs:29388`(`u8_pack_min_binary_two_lanes_match_and_cover_ack_only` = 「두 값 같음 ∧ ≥1.1.7」 → 1.1.8·1.1.10 둘 다 통과).

| 사실 | 근거(실측) | 확신 |
|---|---|---|
| v1.1.9..HEAD 의 새 CLI 표면 = `cys doctor --lanes` **1건뿐** | `src/bin/cys.rs` diff 의 `#[command]`·`#[arg]`·`long =` 추가 1 · `src/` 전체 clap 추가 1 | High |
| 팩이 `--lanes` 를 실행 경로에서 부르나 | `git grep -- '--lanes' -- cysjavis-pack` = `cysjavis-pack/hooks/README.md:154` 1곳(사람이 읽는 문서) · hooks·bin·directives·skills 실행 경로 0 | High |
| 팩에 새로 붙은 `cys <하위명령>` 호출 | `pack-merge --propose`(v1.1.7~) · `reap-surface`(v1.1.7~) · `schedule remove`(시험) · `events --reconnect --cursor-file`(v1.1.9 에 있음) — 전부 기존 표면 | High |
| 1.1.8 하한 근거는 살아 있음 | `cysjavis-pack/hooks/session-start.sh:200` `cys reclaim-role --auto`(v1.1.7=0 · v1.1.8=1) | High |
| **CLI 밖 새 의존 1건 — 휴지통** | v1.1.9 팩 `cys-dept reap` = 14일 지난 격리분 `rm -rf`(v1.1.9 `cys-dept:3392-3401` `TRASH-EXPIRE`) → HEAD 팩 = 지우지 않고 표시만(`cysjavis-pack/bin/cys-dept:3445-3461` `TRASH-OLD … delete from Control Center > Trash` · `CSO_DIRECTIVE.md:351`). 지우는 유일한 길 = 데몬 `trash.*`(`src/bin/cysd/trash.rs` 신설 · `handlers.rs:5223` 분기 v1.1.9=0 · HEAD=1) + 앱 휴지통 탭 · ★발행 전 검토 review-b(master#4e61b71e Q1=B): **윈도우 예외** — 삭제 꺼진 빌드(`cys build-info --json` 에 `"trash_delete_supported":true` 없음 = 1.1.10 윈 · 그 칸이 없는 1.1.9 이하 바이너리 전부)에서는 HEAD 팩도 1.1.9 처럼 14일 정리(`TRASH-EXPIRE`) | High(사실) |
| 귀결 — 하한 1.1.8 유지 시 | 1.1.8·1.1.9 **맥** 바이너리가 1.1.10 팩을 받으면 **자동 삭제도 화면 삭제도 없이 격리분이 쌓인다**(윈도우는 위 예외로 14일 정리 유지 — 그 바이너리에는 build-info 칸이 없다)(부서당 최대 324MB · `CSO_DIRECTIVE.md` 같은 절) — 오류가 아니라 디스크 누적 | High(사실) · 「그런 기기가 실제로 팩만 받는 경로가 몇 대에 열리나」 = 미확인 |
| 귀결 — 하한 1.1.10 시 | 1.1.9 이하 바이너리는 새 팩을 거부(그 기기는 바이너리를 함께 받는 자동 갱신 또는 설치 한 줄로 1.1.10 이 되면 풀림) · 1.1.7 이하는 원래 자동 갱신 없음 | Med |
| 윈도우 | 윈 1.1.10 은 화면 삭제가 꺼짐(`trash.rs:1631-1637` · feature 기본 꺼짐 `Cargo.toml:31`) — 그런데 v1.1.9 의 `find -mtime` 자동 삭제도 「윈도우에서 이 bash 경로는 돌지 않는다」(원작자 `4148fc13` 본문) → **윈은 잃는 것이 없다**(원래 지우는 길이 없었음 · 해석) | Med |

| 선택 | 근거 | 확신 |
|---|---|---|
| ① 1.1.8 유지 | 규칙 문자 그대로(새 **CLI** 표면을 팩이 지시하는가) = 상향 근거 0 | High(호출 실측) |
| ② 1.1.9 | 근거 없음(1.1.9 신설 `pack-heal --missing-only` 팩 호출 0) | High |
| ③ **1.1.10(채택)** | 규칙의 뜻(「팩이 새 바이너리 표면을 지시」)을 GUI·RPC 표면까지 읽으면 해당 — 새 팩은 옛 자동 삭제를 없애고 **새 바이너리의 휴지통만을 유일한 삭제 길로 지시**한다. 발행 규칙의 예외 선례(09-25 「새 판이 기존 기능의 유일한 길을 없애는가」)와 같은 꼴 | 사실 High · 규칙 적용 = master 채택 |

- 채택 ③: 두 레인 같은 커밋(태그 전)에 `'1.1.10'` · 본문 칸 `--requires-min-binary-for-pack` 도 같은 값(§6).
- ⚠1.1.9 실제: §6 권고 1.1.8 이었는데 본문은 **1.1.9** 로 나갔고(T1 07:57:55 · 공개 봉투 안 `requires.min_binary_for_pack: '1.1.9'`) 팩 매니페스트는 1.1.8 — 근거 기록 없음. 이번엔 **R4 명령을 §6 표와 한 칸씩 대조**하는 줄을 2-3 에 넣었다.

### A-5. 봉투 = release_seq 5

| 칸 | 값 | 근거 |
|---|---|---|
| `CYSR_RELEASE_SEQ` | 4 → **5** | 보관소 `releases/4.json` 200 · `releases/5.json` 404(10-22 실측) · RELEASE.md:33 「보관소 최댓값 + 1」 |
| 본문 `--release-seq` | **5** | 같음 |
| 열거 폭 | 5 − 1 + 1 = 5 ≤ 256 | `--min-from-release-seq 1` 일 때(§6) |
| 봉투 feed_rev | 라이브 3 → 이번 게시 **4**(추론) | 10-19 주간 발화가 feed_rev 4 재료를 만들었으나 **게시 안 함**(SS:429 · 라이브는 지금도 3) — refresh-feed 가 라이브 기준 +1 을 쓰는지 = 미확인 → 3-6 출력의 feed_rev 를 그대로 기록 |
| 인텔 맥 | seq 5 본문에 **macos-x64 행 필수** — ⛔**발행 차단 조건**(master#c5547f8b 경고 ①): `collect-inputs … macos-x64` 0건이거나 본문 자산 행에 `macos-x64` 가 없으면 **발행 중지**(2-2 · 2-3 · 3-9 의 ⛔ 확인 줄) | ⚠seq 4(1.1.9) 본문에는 x64 행이 **없다**(공개 `releases/4.json` 자산 = `macos-arm64`·`windows-x64` 둘 · 10-22 실측) → 인텔 맥 1.1.8 기기는 seq 4(1.1.9)를 자동으로 못 받았을 것(추론 · 관측 0). seq 5 에 x64 행이 실리면 인텔 1.1.8·1.1.9 기기는 seq 5 부터 자동 대상이 된다(추론 · `min_from` 1 이므로) |
| 봉투 만료 | 현 봉투(seq 4 · feed_rev 3) 만료 = 10-31 08:29 KST(stable · next 08:31) | 발행 10-23 에 새 봉투를 게시하므로 **문제 없음**(master#c5547f8b 경고 ②) — 발행이 10-31 뒤로 밀릴 때만 그 전에 seq 4 봉투 재게시(§5-12) |

### A-6. 1.1.9 집행에서 배운 것(이 체크리스트에 반영한 자리)

| # | 1.1.9 에서 일어난 일 | 출처 | 반영 |
|---|---|---|---|
| L1 | **x64 build-info·cdhash 수집 0건 → seq 4 본문에 인텔 행 없음** · 게이트는 통과(생성기 필수 = arm64·win 뿐 `scripts/update/update_common.py:31` `REQUIRED_CYSR_TARGETS = ("macos-arm64", "windows-x64")` — 1.1.10 트리에도 그대로) · 공지·카톡은 「인텔 맥 포함」 으로 나감 | T1 07:57:55 · `ls ~/axdev/.wt/cys-119-r3r4/r3s4/inputs` · 공개 4.json | 2-2 x64 를 R4 **전** 절대 조건 · 2-3 자산 행 3 을 손으로 셈 · 3-9 update-verify 열거에 macos-x64 줄 확인 |
| L2 | `--requires-min-binary-for-pack` 권고 1.1.8 → 실제 1.1.9(근거 기록 0) | T1 07:57:55 · 봉투 디코드 | 2-3 대조 줄 · A-4 |
| L3 | dry-run 1차 적색 = 구판 레인 `cysr_{aarch64,x64}.app.tar.gz(.sig)` 4종 누락 → tarball·update-row 를 뒤늦게 | T1 08:07 · SS:280 「1.1.10 백로그: RELEASE.md 단계 4 에 명시 필요」 | 3-1 순서 고정(tarball → update-row → postprocess → dry-run) · RELEASE.md:35-37 단계 4 에는 아직 그 단계가 없다(문서 수리 = 별건) |
| L4 | `release-production` 승인 **필요** — `gh api …/pending_deployments` 로 승인 · 600초 watch 시간초과 | T1 08:25:02~09 | 3-8 명령 줄 |
| L5 | main 이동 첫 push 실패(zsh `$NEW:refs/heads/main` → 「…efs/heads/main」) | T1 08:27:08~14 | 3-5 = 이번엔 앞으로 감기 · `"${NEW}"` 중괄호 |
| L6 | refresh-feed 는 rollout·halt·first 를 **명시**해서 넘김 | T1 08:27:20 | 3-6 명령 원문 |
| L7 | 순서 실제 = 발행 08:25 → 보관소 08:26 → main 08:27 → refresh-feed 08:27 → 봉투 08:31(계획과 다름 · 문제 없었음) | T1 | §3 순서를 실제대로 |
| L8 | latest.json notes 에 거짓 문장(「앱 내 Update 버튼 … 윈도우 단독 배포」) 그대로 · 원인 = `release.yml:1298·1300` 템플릿(1.1.10 트리에도 그대로) | 공개 latest.json 실측 · H7 | §0-5 이 가지에서 템플릿 수리(해소) |
| L9 | 시험 기기 둘(윈·맥)을 발행 전에 손으로 올려 **1.1.8 → 1.1.9 자동 받기 관측 0건** · 카톡은 단서 없이 「알아서 바꿔 드립니다」 | SS:604·614 · H7:44 | §0-4 관측용 기기 1대 남기기 · 노트·카톡 대체 문장 |
| L10 | 공지·카톡 문안을 발행 **다음 날** 07:33 에 작성(약 23시간) · 보관 파일 `ai-jarvis/docs/KAKAO-119-notice.md` ≠ 실제 보낸 최종본 | SS:302·323~327·400 | §0-6 미리 확정 · 4-3 최종본을 파일로 커밋 |
| L11 | 로컬 `ai-jarvis` site/hub 가 1.1.8 에 머묾 → 다음 배포 회귀 위험 → ff + push 로 해소 | SS:352 | 4-2 확인 줄 |
| L12 | pre-tag 첫 실행 「런 없음 → 태그 금지」(가지가 CI 트리거 밖 → dispatch 3회) | SS:628 · T1 22:42:51 | 1-1 · 1-2 |
| L13 | 봉투 서명 유효 최대 14일(`update_common.py` `MAX_ENVELOPE_WINDOW_SECS = 14 * 86400`) — 현 봉투 만료 **10-31 08:29 KST** | 봉투 디코드 | §5-12 |

---

## 0. 착수 전 — 막히면 그 자리에서 멈춤

| # | 할 것 | 확인 줄 | 상태 |
|---|---|---|---|
| 0-1 | 좌석 546 의 지침 출처 표기 커밋이 `rel/1.1.10` 에 들어온 뒤의 머리 확정 → A-1-6 ⑴~⑶ 대조 | `git log --oneline -3 rel/1.1.10` | 대기 |
| 0-2 | **윈 실기 = 절단(금 10-23) 전**(규칙 「윈 실기·VM·정밀 디버깅·이종 리뷰는 절단 전」) — 확인점 48개·실기 절차 = `WIN-FIELD-1.1.10.md` · `docs/RELEASE.md:436` 칸 「★1.1.10 윈도우 실기 확인 — 상태: 실기 미검증」 이 열려 있다 | 통과 기록(win-reply 원문 + 판정) | **미착수** |
| 0-3 | **윈 실기 대상 바이트 = 확정**(master#c5547f8b ⑴): **절단 전 ⓐ 기능 확인** = `windows-build` dispatch 산출물(NSIS setup.exe · ⚠이 레인은 `CYSR_RELEASE_SEQ` 를 넘기지 않아 release_seq 0 — `.github/workflows/windows-build.yml` 에 그 줄 0 · `build.rs:308-311` 미지정 = 0 → 발행 바이트가 아니고 깐 기기는 자동 갱신 대상 밖) 으로 기능 확인점(WG·WINQ·MINOR·TRASH·V·MENU)을 끝낸다 → **절단 뒤 ⓑ 업데이트 1회** = 태그 draft setup.exe 시험 키트(jarvis-install prerelease `wintest-v1.1.10-…` + bootstrap 핀 4줄 · 1.1.9 선례 SS:621~626)로 「1.1.9 → 1.1.10」. ⓐ를 깐 노트북은 ⓑ 전에 라이브 한 줄(1.1.9 핀)로 1.1.9 로 되돌린다(그래야 ⓑ가 업데이트 시험이 된다) · ⓑ가 적이면 태그 번호를 다시 쓸 수 없다(RELEASE-ROLLBACK.md:20-24 · 수리판 = 다음 번호) · 절차 = `WIN-FIELD-1.1.10.md` §2 | ⓐ 통과 기록 · ⓑ 통과 기록 | **확정**(집행 대기) |
| 0-4 | 자동 받기 **관측용 1.1.9 기기 1대**를 손대지 않고 남긴다(L9) — 후보: 시험 안 쓰는 맥 1 또는 윈 1(어느 기기가 남는지 = master) · 인텔 맥 1.1.9 기기가 있으면 그것도(A-5 인텔 행 실증) | 기기 이름·`cysr --version`·`build-info --json` 의 `release_seq` 4 | 대기 |
| 0-5 | `release.yml` 자동 본문 설치 안내 2줄 = **이 가지에서 태그 전 수리 완료**(master#c5547f8b ⑶ · §7) — 전 :1298 「… 기존 사용자는 앱 내 Update 버튼으로 자동 갱신됩니다.」 · 전 :1300 「… (이 태그는 윈도우 단독 배포입니다 — macOS 자산은 포함되지 않습니다.)」 → 두 줄 다 「새 판은 cysr 릴리스로만 나오며 앱 안 업데이트 단추는 없습니다 — 1.1.8 이상은 자비스가 쉬는 시간에 새 판을 알아서 받고, 1.1.7 이하이거나 처음 설치하시면 https://jarvis.godmeyou.kr/get 의 설치 한 줄을 붙여 넣어 주세요.」 · APPLE_* 부재 줄(우리 실제 갈래)은 맥 zip 2종(`cysr-macos-arm64`·`cysr-macos-x64`)을 안내(우리 포크는 맥 zip 을 로컬 빌드·손 업로드로 발행 전 같은 draft 에 올린다 · `release-postprocess.py` 는 맥 zip 없으면 적색) · 릴리스 본문 = latest.json notes 의 출처 → 1.1.10 부터 notes 거짓 문장 소멸(추론 · 3-8 뒤 `releases/latest/download/latest.json` notes 실측) · 이 문장을 글자로 지키는 시험은 없음(`test_default_fleet_formation.py` ⓖ = 본문이 파생값인지 구조만 · 수리 뒤 126/126 PASS) | 3-2 의 본문 실측 | **해소** |
| 0-6 | 발행 노트·공지·카톡 초안 확정(`docs/release-1110/` · 【발행 전 확인】 줄 처리) — **발행 전까지**(L10 · 원래 「발행 전날까지」 — 발행이 10-23 당일로 당겨져 전날이 없다 → 사이트 공지 배포·카톡 발송 전) | 박사님·master 확정 | 대기 |
| 0-7 | `USER-MANUAL.md` 현행화 = **이 가지에서 완료**(master#c5547f8b ⑷ · §7) — ⑴ §4.1 상단바: `피드백` 바로 뒤 `상담소`·`아고라`(1.1.10 이동 · 하는 일 · 상단 단추에서 끄고 켜기 · 1.1.9 저장 배치여도 피드백 바로 뒤) ⑵ :743(전 :739) 화면 설정 글자 = 기본 125% = 12.5px · 100% = 10px(`ui/src/style.css:506` `calc(10px * var(--ui-chrome-scale))` · `af852096`) ⑶ §9 표에 **휴지통** 행 + 새 절 「### 휴지통 (1.1.10)」(저절로 지워지지 않음 · 보이는 것 · 맥 지우는 순서 · 어긋나면 지우지 않음 · 윈도우는 보기만) ⑷ 완전 초기화 문단에 「보관 폴더는 저절로 지워지지 않는다 — 휴지통에서」 1문장 · 낱말은 앱 화면대로(「부서 삭제」 · `ui/src/main.ts:9431`) | publicdocs·screensettings·clipath bun 326/0 · bootv2 문서 계약 OK · cargo 문서 시험(§7) | **해소** |
| 0-8 | 팩 하한 = **1.1.10 확정**(A-4) — 두 레인 `release.yml:1419` · `pack-release.yml:89` = `'1.1.10'` 이 가지 별도 커밋(§7) · 본문 칸 `--requires-min-binary-for-pack 1.1.10`(§6) | 시험 핀 `u8_pack_min_binary_two_lanes_match_and_cover_ack_only` 녹 | **해소** |

## 1. 태그 전(가역)

| # | 명령 | 확인 줄 | 롤백 |
|---|---|---|---|
| 1-0 | 판 올림 커밋(A-3 표 8곳) + `docs/index.html` 7줄 — `rel/1.1.10` 위 로컬 커밋(0-5 템플릿 · 0-7 설명서 · 0-8 두 레인 하한은 이 가지 docs/1110-release-prep 에 이미 있음 → master 가 합친 뒤) | `PATH=/usr/bin:$PATH sh scripts/version-check.sh v1.1.10` rc 0 · `git grep -n '1\.1\.9' -- Cargo.toml src-tauri/Cargo.toml src-tauri/tauri.conf.json ui/package.json dist-win/` = 0 · `Cargo.lock:1199` flate2 = 1.1.9 그대로 | 커밋 되돌림 |
| 1-1 | 가지 push(미러) → CI **dispatch** 3런(`rel/**` 는 push 트리거 밖 — ci-branch `['feat/**','fix/**']` · windows-build `['feat/windows-x64-dist','fix/**']` · windows-health `['feat/**','fix/**']` + tags `v*`): `for w in ci-branch.yml windows-build.yml windows-health.yml; do gh workflow run "$w" -R oogisoogi/cys-ro --ref rel/1.1.10; done` ≈45분 · ⚠push 전 `bash scripts/secret-scan.sh --all` rc 0(RELEASE.md:10-21 「밀기 전 게이트 — 전 ref 공통」) | 3런 success(같은 SHA · 1.1.9 = 38910007412 · 38910011842 · 38910016488 꼴) · windows-health 「cysd 감독자 축」(:580)은 continue-on-error → 로그의 `trash::` 실패 이름 0 을 따로 확인(WIN-FIELD V9·V11) | 가지만 — 무해 |
| 1-2 | `PATH=/usr/bin:$PATH sh scripts/version-check.sh v1.1.10` · `sh scripts/win-typecheck.sh`(A-2-6) · `python3 scripts/pre-tag-ci-check.py --wait 70`(**dispatch 뒤에** · L12) · `bash scripts/scan-pack-secrets.sh` · `python3 cysjavis-pack/bin/tests/run_bootstrap_health.py --only H-SECRET-1`(통합 때 GREEN 853파일 · 메모리 release-cut-gate-run-health-specimens-locally) | 다섯 다 rc 0(pre-tag rc 2 = 판정 불가 ≠ 통과 · 「58초 태그 금지」 RELEASE.md:171-230) | — |
| 1-3 | `gh variable set CYSR_RELEASE_SEQ -R oogisoogi/cys-ro --body 5`(1.1.9 실제 꼴 · T1 23:37:22) | `gh variable list -R oogisoogi/cys-ro` = 5 | 다시 set |

## 2. 태그(절단 · 금 10-23) → draft → 자동 갱신 재료

| # | 명령 | 확인 줄 | 롤백 |
|---|---|---|---|
| 2-1 ⛔ | `git tag -a v1.1.10 <태그 커밋> -m "cysr v1.1.10 (based on cys 0.14.49~51 · rel/1.1.10)"; git push origin refs/tags/v1.1.10`(1.1.9 꼴 · A-1-2) | draft-guard 「✅ … draft 없음 — 진행」 · windows-health-gate 「✅」 · seq 정수 스텝 초록 · 1.1.9 실측 ≈70분(23:39 → 00:5x) · draft 자산 6 | draft 삭제 가능 · **실패 태그 번호 재사용·태그 삭제 금지**(RELEASE-ROLLBACK.md:20-24) · 재시도 = Re-run failed jobs |
| 2-2 | R3 재료 — ★**x64 를 R4 전에 반드시**(L1): `export CYSR_RELEASE_SEQ=5` → `bash scripts/build-macos-local.sh aarch64 dist-seq5` **+** `bash scripts/build-macos-local.sh x86_64 dist-seq5`(A-2-2 의 HEAD·porcelain 2줄 먼저) → `bash scripts/update/collect-inputs.sh mac <arm64 zip> macos-arm64 r3s5/inputs` **+** `bash scripts/update/collect-inputs.sh mac <x64 zip> macos-x64 r3s5/inputs` → `gh run download <태그 런> -R oogisoogi/cys-ro -n update-inputs-windows-x64 -D r3s5/inputs/` · x64 의 Rosetta 경고 = 정적 처리(`ditto -x -k` + `codesign -dvv` · T1 08:08 · H7:70) | build-info `release_seq` = 5(셋 다) · `ls r3s5/inputs` 에 **arm64·x64·windows 세 묶음** — ⛔**x64 묶음 0건이면 발행 중지**(A-5 · master#c5547f8b 경고 ①) · 윈 설치기 sha ≠ 1.1.9 · A-2-3 strings 2종 | 산출물 삭제 · ⛔본문 보관(2-5) 뒤에는 재빌드 금지(설치기 sha 고정 · 메모리 project_cysr-release-archived-body-forbids-tag-rebuild) |
| 2-3 | R4: `python3 scripts/update/make-release-json.py --component cysr --release-seq 5 --version 1.1.10 --min-from-release-seq 1 --state-migration none --notes-ko 'cysr 1.1.10 으로 새로 갱신되었습니다.' --key-id <U 키> --requires-min-binary-for-pack 1.1.10 --release-dir r3s5/release --asset macos-arm64=… --asset macos-x64=cysr-macos-x64-v1.1.10.zip --asset windows-x64=… --build-info macos-arm64=… --build-info macos-x64=… --build-info windows-x64=… --cdhash macos-arm64=… --cdhash macos-x64=… --a2-sig windows-x64=…sig --payload-dir windows-x64=r3s5/inputs/payload-windows-x64 --out r3s5/body/cysr-release-5.json`(1.1.9 실제 명령 T1 07:57:55 + x64 3칸) → `(set -a; . ~/.config/cysr-update/r2.env; set +a; python3 scripts/update/release-gate.py body --body r3s5/body/cysr-release-5.json --keyring cysjavis-pack/trusted-keys.json --archive-r2 cysr-update --expect-seq 5)` | rc 0 · ★**본문 자산 행을 손으로 센다 = 3(macos-arm64·macos-x64·windows-x64)** — ⛔**`macos-x64` 행이 없으면 서명(2-4)으로 넘어가지 말고 발행 중지**(A-5): `python3 -c "import json;print(sorted(json.load(open('r3s5/body/cysr-release-5.json'))['assets']))"`(키 이름은 본문 구조에 맞춰 · 1.1.9 는 게이트 rc 0 인데 행 2 였다) · ★명령의 칸 6개(seq·min-from·state-migration·notes-ko·min-binary-for-pack·자산 행)를 §6 표와 **한 칸씩 대조**해 기록(L2) | 다시 생성 |
| 2-4 | R5(박사님 USB 「NO NAME」 + U 비밀번호): `~/axdev/master/sign1110.sh`(1.1.9 `sign119.sh` 꼴 · 내용 = `bash scripts/update/sign-release.sh --body r3s5/body/cysr-release-5.json --media "/Volumes/NO NAME" --key "/Volumes/NO NAME/u.key" --out-dir r3s5/signed` · seq·경로만 바꿔 미리 만들어 둠) → master `minisign -V -p ~/axdev/master/keys-118/u.pub -m r3s5/signed/cysr-release-5.json -x …minisig` → `release-gate.py body … --sig … --expect-seq 5 --stamp` | 「✅ U 의식 통과」 · trusted comment seq=5 · gate rc 0 | 다시 서명 |
| 2-5 ⛔ | R6 보관소: `python3 scripts/update/publish-site.py archive --r2 cysr-update --file r3s5/signed/cysr-release-5.json --dry-run` → 같은 명령 `--live-check https://jarvis.godmeyou.kr` (1.1.9 실제 = 발행 **뒤** 08:26 · L7 · 순서는 §3 표대로) | `curl -fsS https://jarvis.godmeyou.kr/update/cysr/releases/5.json \| shasum -a 256` = 로컬 sha · `.minisig` 200 · 「라이브 대조 일치」 | 라이브 어긋남 = 자동 되돌림 rc 4(실패 rc 5 = 인쇄된 restore 1줄) · **보관소 불변 — 같은 seq 다른 바이트 불가** |

## 3. draft 정비 → 발행(금 10-23 · 당김 · 원래 일 10-25) — 순서 = 1.1.9 실제 순서(L7)

| # | 명령 | 확인 줄 | 롤백 |
|---|---|---|---|
| 3-1 | ★**순서 고정**(L3): ① 손대기 전 draft 사본 `~/cys-release-backup/v1.1.10-draft-before-r7/`(1.1.9 는 이 사본이 없고 `v1.1.9-assets/` 만 있었다) ② 맥 zip 2종 `gh release upload v1.1.10 …` ③ **구판 레인 tarball**: `bash scripts/make-darwin-updater-tarball.sh --app <arm64 cysr.app> --arch aarch64` · `… --arch x64`(A2 키 환경변수) → `gh release upload v1.1.10 cysr_{aarch64,x64}.app.tar.gz{,.sig} --clobber`(4종) ④ `python3 scripts/make-darwin-update-row.py --target darwin-aarch64 … --merge latest.json` · `--target darwin-x86_64 …` → `gh release upload … latest.json --clobber` ⑤ `python3 scripts/release-postprocess.py v1.1.10` → `… --apply` | 자산 14(1.1.9 공개 자산 = arm64·x64 zip · setup.exe/.sig/.zip · tar.gz 2 + .sig 2 · latest.json · pack 3종 · SHA256SUMS.txt) · ⚠`make-update-manifest.sh` 금지(윈 행 소실 · HANDOFF-118-r7:81) · zsh 는 `"${VAR}:…"` 중괄호 | 사본에서 복원 |
| 3-2 | GitHub 본문 확인 — 0-5 수리로 자동 본문 설치 안내가 이제 사실대로 나온다(「cysr 터미널 v1.1.10. Windows는 -setup.exe, 맥은 cysr-macos-arm64(애플 실리콘)·cysr-macos-x64(인텔) zip을 … 앱 안 업데이트 단추는 없습니다 …」 + 출발지 줄) → **손 수정 불요가 기본**. 노트 초안의 「GitHub 릴리스 본문」 절(원작 판 0.14.51 표기 · A-1-3)로 바꾸고 싶으면 발행 **뒤** 편집(1.1.9 실제 = 발행 뒤 08:54 `gh release edit v1.1.9 -R oogisoogi/cys-ro --notes-file …` · draft 에서 `--tag` 동반 편집의 tag_name 영향 = 미확인) · 먼저 옛 본문 사본 `gh release view v1.1.10 -R oogisoogi/cys-ro --json body -q .body > r7/body-before.txt` | `gh release view v1.1.10 -R oogisoogi/cys-ro --json tagName,isDraft,body` = tagName v1.1.10 · body 에 「Update 버튼」 0 · 「윈도우 단독 배포」 0 · 3-8 뒤 `releases/latest/download/latest.json` 의 notes 도 같은 두 낱말 0 | `gh release edit v1.1.10 -R oogisoogi/cys-ro --notes-file r7/body-before.txt` |
| 3-3 | 검증 = CI dry-run 의 verify 잡(1.1.9 실제 · 로컬 `release-verify.py`·`release-gate.py assets` 실행 기록 0) — 로컬로도 돌리면: `python3 scripts/release-verify.py --version 1.1.10 --release-dir r7/reviewed --prev-tauri-conf prev-conf.json --prev-pack-keyring prev-keys.json` · `python3 scripts/update/release-gate.py assets --release-dir r7/reviewed --pack-manifest r7/reviewed/pack-manifest.json` | 「릴리스 검증 통과 — 자산 13종(+SHA256SUMS.txt) · 업데이터 4행 전부 서명 일치 · 맥 자산 포함」 · 팩 replay 단조 위반 = E1 최소 재서명 → SUMS 재생성(RELEASE.md:98-117) | — |
| 3-4 | `shasum -a 256 SHA256SUMS.txt`(3-1 ⑤ **뒤** 최종본 · 1.1.9 = 첫 dry-run 10febe52… → 최종 403a8be0…) = **release_bundle_sha256** | 기록 | — |
| 3-7 | dry-run: `gh workflow run release-publish.yml -R oogisoogi/cys-ro --ref main -f tag=v1.1.10 -f release_bundle_sha256=<3-4> -f confirm=PUBLISH`(1.1.9 = `--ref main` 으로 통함 · 그때 main = 6fddbffe) — 지금 main = fb386c49(같은 계열 · dry_run 입력 있음 추정) · ⛔**422 가 나면 멈춤**(dry_run 을 빼고 다시 보내기 금지 · 메모리 reference_cys-release-publish-dryrun-needs-branch-ref) | 「SHA256SUMS.txt 다이제스트: … (입력과 일치)」 · 「맥 자산: 포함」 · 「✅ dry-run 완료 — … 발행은 하지 않았다」 | 바뀌는 것 없음 |
| 3-8 ⛔ | 발행: 3-7 명령 + `-f dry_run=false` → 런이 **승인 대기**(L4 · environment `release-production` · 1.1.9 확정) → `gh api repos/oogisoogi/cys-ro/actions/runs/<RUN>/pending_deployments`(env id 조회 · 1.1.9 = 21524450364) → `gh api -X POST repos/oogisoogi/cys-ro/actions/runs/<RUN>/pending_deployments -F 'environment_ids[]=<id>' -f state=approved -f comment='cysr 1.1.10 발행'` · watch 는 600초를 넘을 수 있다 → 백그라운드 | 로그 「✅ 공개 발행 완료 — tag_name=v1.1.10 · isDraft=false」 · 공개 SUMS 13줄 OK · `releases/latest/download/latest.json` version 1.1.10 · 행 4 · `setup.exe.sig` 200 | ①`gh release edit v1.1.9 -R oogisoogi/cys-ro --tag v1.1.9 --latest` ②`gh release edit v1.1.10 -R oogisoogi/cys-ro --tag v1.1.10 --draft=true` · 삭제 = 최후·오너 지시만 · tag_name 리셋 = PATCH `{"tag_name":"v1.1.10"}`(RELEASE-ROLLBACK.md:53-130) |
| 2-5 ⛔ | (발행 직후) 보관소 게시 — §2 의 2-5 명령 | 2-5 확인 줄 | 2-5 |
| 3-5 ⛔ | main 이동 — ★**이번엔 앞으로 감기**: `fb386c49`(refresh-feed CI 패치)가 이미 태그 커밋의 조상(10-22 실측 `git merge-base --is-ancestor fb386c49 53031718` = 참) → cherry-pick·강제 push 불요. 집행 직전 재측: `git fetch origin && git merge-base --is-ancestor origin/main v1.1.10 && echo FF-OK` → 보존 가지 `git push origin fb386c49:refs/heads/archive/main-pre-1110-20261023` → `NEW=$(git rev-parse v1.1.10^{commit}); git push origin "${NEW}:refs/heads/main"`(강제 아님 · 중괄호 · L5) | 불변식 「main = 최신 발행 태그 커밋 + CI 전용 패치」 · `gh workflow list -R oogisoogi/cys-ro` 에 refresh-feed active · main 트리 `.github/workflows/refresh-feed.yml:66` `SITE: ${{ vars.CYS_FEED_FETCH_SITE \|\| …}}` 줄 | 보존 가지로: `git push --force-with-lease=main:${NEW} origin fb386c49:refs/heads/main` · FF-OK 가 안 나오면(누가 main 에 새 커밋) **멈춤** |
| 3-6 | 봉투 재료(보관소 5 선행): `for ch in stable next; do gh workflow run refresh-feed.yml -R oogisoogi/cys-ro --ref main -f component=cysr -f channel=$ch -f release_seq=5 -f rollout_pct=100 -f halt=false -f first=false; done`(1.1.9 실제 명령 원문 T1 08:27:20 · seq 만 5) → `gh run download <run> -R oogisoogi/cys-ro -D r3s5/env/<run>` | 「Verify the NEW envelope」 초록 · 아티팩트 `envelope-cysr-stable`·`-next` · **feed_rev 값을 출력 그대로 기록**(A-5 · 추론 4) | 게시 전 — 무해 |
| 3-9 ⛔ | 봉투 게시(stable·next 각각 · 먼저 `--dry-run`): `python3 scripts/update/publish-site.py envelope --r2 cysr-update --file r3s5/env/<run>/envelope-cysr-<ch>/env.json --cys <1.1.10 cys 바이너리> --dry-run` → 같은 명령 `--live-check https://jarvis.godmeyou.kr` | 「update-verify[…] 출발 seq 1,2,3,4,5 전부 허용 판정」 줄에 ★**macos-arm64 · macos-x64 · windows-x64 세 대상이 다 나오는지** — ⛔macos-x64 가 없으면 `--live-check` 로 넘어가지 말고 멈춤(1.1.9 는 macos-x64 가 없는데도 경고가 없었다 · L1) · 「라이브 대조 일치」 · `for f in cysr/stable.json cysr/stable.json.minisig cysr/next.json cysr/next.json.minisig; do printf '%s ' "$f"; curl -fsS "https://jarvis.godmeyou.kr/update/$f" \| shasum -a 256 \| cut -c1-64; done` = 아티팩트 sha 4 · 관측용 1.1.9 기기(0-4)에서 `cysr self-update --check --json` = 새 판(seq 5) 있음 쪽 결과(정확 문구 미확인 — 1.1.9 때는 이미 올린 기기에서 `decision="uptodate"` 만 잼) | live-check 어긋남 = 자동 되돌림 rc 4/5 · 같은 rev 다른 내용 재게시 금지 · 비상 = refresh-feed `-f halt=true` → 게시(선례 미확인) · 이미 받은 기기는 못 되돌림 = 더 높은 판으로만(폐기문 = 사건 때만 R-RITUAL.md) |

## 4. 발행 뒤(설치기·사이트·알림)

| # | 할 것 | 확인 줄 | 롤백 |
|---|---|---|---|
| 4-1 ⛔ | 설치기 핀 1.1.9 → 1.1.10(판·크기·sha256·CDHash 를 **발행 자산에서 다시 재서**) — 1.1.9 실제 = habitat `r8/publish-20261017` 143b821(설치기 0.3.40 → 0.3.41) · 라이브 핀 `bootstrap.sh:147` `CYS_FORK_VERSION="1.1.9"` · `bootstrap.ps1:141` `$CysVersion = '1.1.9'` → 공개 jarvis-install main 33447f8 → 16f67c4 · 이번 설치기 판 = **0.3.42** 차례(한 발행에 한 판 · H7:64-72) → `PUBLISH_CONFIRM=yes bash tools/publish-snapshot.sh --src . --dest ~/axdev/jarvis-install --push --terms-check tests/public-terms-check.sh --terms-list …` | 「SNAPSHOT-OK · 적중 0 · 삭제 (없음)」 · 핀 시험(맥·인텔·윈 · 1.1.9 = 17·0 / 11·0 / 12·0) · 함정(H7:64-72): 대상 clone origin = 공개 URL · 원격 git `PATH=/opt/homebrew/bin:$PATH` · x64 는 정적 검사만 · `.DS_Store` 지운 뒤 재실행 · 소요 1.1.9 = 기술 20분 + 라이브 5분 | 이전 핀 커밋으로 |
| 4-2 ⛔ | 사이트(ai-jarvis): 공지 `site/notice/2026-10-23/` · 손댈 자리 7(1.1.9 SITE-119 꼴: ①새 공지 index.html ②`site/notice/index.html` 목록 맨 위 ③`site/index.html` 머리 띠 ④`site/get/index.html` 머리 띠 — **끝 문단 링크만** `#install` 꼴이라 같은 치환을 두 파일에 쓰면 한쪽 0건 ⑤`site/devlog/index.html` 새 항목 + 시기 머리 ⑥`site/test/check-render.py` PAGES 한 줄 ⑦「최신 판」 숫자 스윕 `grep -rnI '1\.1\.[0-9]' site \| grep -v '^site/install/'`) → `bash site/test/gate.sh` → `bash web/build-web.sh` → 실렌더 6조합(대문·설치하기·공지 × 390/1440) → `cd web && wrangler deploy` · `bash web-install/deploy.sh --go`(npm ci 먼저) · ★**site/1110 가지를 site/hub 에 병합하고 push**(L11 — 안 하면 다음 배포가 옛 판으로 돌아감) | GATE=PASS · `/notice/2026-10-23/` 200 · 띠 2곳 1.1.10 · 「최신 = 1.1.9」 잔존 0(첫 조회 엣지 HIT 가능 · 20초 뒤 재측) · 라이브↔빌드 대조 때 Cloudflare 주입 2조각 제외 · `/install/next` 404(실기 때 썼으면 삭제) · 공개 저장소 checks [사이트] 대조 붉은 창 0(H7:72) | 이전 커밋 재배포 |
| 4-3 | 카톡 문안 `docs/release-1110/KAKAO-1110.draft.md` → 라이브 공지와 대조 → 박사님 전달(발송 = 박사님) · ★보낸 **최종본을 그대로 파일로 커밋**(L10) | 링크 200 · 공지 앵커 | — |
| 4-4 | 실기기 자동 받기 첫 관측(0-4 기기): 어댑터 연결 · 유휴 → 다음 점검 뒤 「자비스가 새 판으로 바뀌었어요」 알림 · `cysr --version` = 1.1.10 · `build-info --json` `release_seq` 5 — 관측 전이면 공지·카톡의 「알아서 받습니다」 = 대체 문장(노트·카톡 초안에 둘 다 준비) | 관측 기록 1줄 | — |

## 5. 미확인 모음(집행 전 master 확정)

1~4. (해소 · master#c5547f8b) 윈 실기 대상 바이트 = ⓐ+ⓑ(0-3) · 팩 하한 = 1.1.10(A-4) · 템플릿 수리 = 이 가지(0-5) · USER-MANUAL = 이 가지(0-7) 5. 좌석 546 커밋이 팩 지침 ⚠3갈래를 덮는지(A-1-6) 6. refresh-feed 가 feed_rev 를 라이브+1 로 쓰는지(A-5 · 10-19 미게시 rev 4 재료와의 관계) 7. draft 상태 `gh release edit --tag` 의 tag_name 영향(3-2 · 이번에도 발행 뒤 편집이면 해당 없음) 8. 관측용 기기 지정(0-4) 9. `self-update --check` 의 「새 판 있음」 정확 문구(3-9) 10. 캐너리(R8 · 발행 직후 무기능 소형 판 seq+1 · 메모리 update-test-body-one-line-no-sandbox ②) 1.1.10 시행 여부 — 1.1.9 는 「1.1.9.x 소형 판 없음」(SS:301)으로 미시행 11. `state_migration none`(§6 · Med) 12. 봉투 만료 10-31 08:29 KST(stable · next 08:31) — **발행 10-23 이라 문제 없음**(10-23 에 새 봉투 게시 · master#c5547f8b 경고 ②) · 발행이 10-31 뒤로 밀릴 때만 그 전에 seq 4 봉투 재게시(10-19 주간 발화는 재료만 만들고 게시하지 않음 · SS:429) 13. 10-26(월) 09:20 launchd `com.jarvis.cys-ro-refresh-feed` 주간 발화 = dispatch 만 · 게시는 사람 손.

## 6. 본문 칸·팩 하한 1.1.10 권고표(2026-10-22 실측)

| 칸 | 1.1.9 실제 발행 값(출처) | 1.1.10 권고 | 근거(코드·실측) | 확신 |
|---|---|---|---|---|
| `--release-seq` | 4(T1 07:57:55) | **5** | A-5 · `releases/5.json` 404 · `CYSR_RELEASE_SEQ` 도 5(1-3) | High |
| `--min-from-release-seq` | 1 | **1**(선례 그대로) | 계약 `0 ≤ 값 < release_seq`(`make-release-json.py:101-102`) · 설치판 < 값 = 보류(`src/update/gates.rs` N11) · 열거 폭 5 ≤ 256 · 인텔 1.1.9(seq 4) 기기를 대상에 두려면 ≤4 여야 함(A-5) | Med |
| `--state-migration` | none | **none** | 가산만 확인: ①`#[serde(deny_unknown_fields)]` 추가 0(`git diff v1.1.9 HEAD -- src src-tauri` · 현행 1곳 `src/bin/cys.rs:25729` = 1.1.9 와 같은 자리) ②1.1.10 새 파일 = 휴지통 뿌리 안 `DELETE-LEDGER.jsonl`·`size-cache.json`(`src/bin/cysd/trash.rs`) · `.producer-<pid>` 표식 — 1.1.9 바이너리는 읽지 않음(1.1.9 에 trash.rs 없음) ③허용값 none·additive·breaking(`update_common.py:23`) · breaking 만 자동 제외 | Med(가산 키 관용) · 기존 키의 뜻·형 변경 전수 감사는 안 함 |
| `--notes-ko` | `'cysr 1.1.9 로 새로 갱신되었습니다.'` | **`'cysr 1.1.10 으로 새로 갱신되었습니다.'`**(26자) | ≤80자 · 제어문자 0 · 금지 어휘(오류·실패·위험·손상·경고) 0(`update_common.py:163-170`) · ⚠조사: 「1.1.10」 = 「…점 십」 받침 ㅂ → **「으로」**(1.1.9 「구」 = 받침 없음 → 「로」) — 「1.1.10 로」 그대로 옮기지 말 것 | High |
| `--requires-min-binary-for-pack` | **1.1.9**(권고 1.1.8 과 다름 · 근거 기록 0) | **1.1.10**(A-4 확정 · 두 레인과 같은 값) | 빈 값·파싱 불가 = 발행 거부(`make-release-json.py:111-114` · `feed.rs:469-471` · `release-gate.py:109-111`) · 본문 값 ↔ 팩 매니페스트 값을 대조하는 게이트는 찾지 못함(1.1.9 = 1.1.9 ↔ 1.1.8 로 갈림) | Med |
| `PACK_MIN_BINARY`(`release.yml:1419`) = `PACK_MIN_BINARY_OVERRIDE`(`pack-release.yml:89`) | 1.1.8 · 1.1.8 | **1.1.10 확정**(두 레인 같은 커밋 · 이 가지 §7) | A-4 정본 근거 | 사실 High · 채택 = master |
| 자산 행 | arm64 · win(**x64 누락** · L1) | **arm64 · x64 · win 셋** — ⛔x64 없으면 발행 중지 | 생성기 필수 = arm64·win 뿐(`update_common.py:31`) → x64 는 사람이 넣는다: `--asset macos-x64=cysr-macos-x64-v1.1.10.zip --build-info macos-x64=… --cdhash macos-x64=…` | High |

## 7. 이 체크리스트와 같은 가지(docs/1110-release-prep)의 커밋

- 1차(87380a67 · 38412054 · 5039e1f6): 이 문서 · `WIN-FIELD-1.1.10.md` · `RELEASE-NOTES-1.1.10.draft.md` · `KAKAO-1110.draft.md`(문서만).
- 2차(master#c5547f8b 결정 4건): ⑶ `.github/workflows/release.yml` 자동 본문 설치 안내 2줄 + 근거 주석 5줄(0-5) · ⑷ `USER-MANUAL.md` 현행화(0-7) · 이 문서 결정 반영 · ⑵ 두 레인 팩 하한 `'1.1.10'`(0-8 · 따로 뺄 수 있게 별도 커밋). 판번(1.1.9)·태그·push 는 그대로 0.
- 공개 문안 2종(노트 사용자판·카톡)의 내부 용어 검사 = 1.1.9 설치기 공개 스냅샷과 같은 검사기(`~/axdev/.wt/hab-r8-119pre/tests/public-terms-check.sh` + `public-terms.txt`) — 결과는 커밋 메시지에.

## 8. 【발행 전 확인】 남은 목록(2026-10-23 11:2x · 발행일 당김 뒤 · TICKET=cysr-1110-publish-today)

출처 = `RELEASE-NOTES-1.1.10.draft.md`(사용자판 7곳) · `KAKAO-1110.draft.md`(주석 ①~④). 「오늘 저녁 윈」 = `WIN-TONIGHT-2026-10-23.md` ⓐ 목록으로 닫는다.

| # | 자리(파일:줄) | 무엇을 보면 닫히나 | 언제·누가 | 지금 |
|---|---|---|---|---|
| N1 · K① | 노트:15-16 「받는 방법」 첫 줄 · 카톡 ① 「따로 하실 일이 없습니다 … 알아서 바꿔 드립니다」 | 실기기 1.1.9 → 1.1.10 **자동 받기 관측**(0-4 · 4-4) | 봉투 게시(3-9) **뒤**에야 관측 가능 → 오늘 발행 시점엔 관측 0 이 확실 → **【대체 문장】으로 나가는 것이 기본**(관측 뒤 공지만 고쳐 올리는 길은 master 판단) | ☐ |
| N2 · K② | 노트:20 「인텔 맥도 됩니다」 덧문장 · 카톡 ② 「(인텔 맥 포함)」 | seq 5 본문 자산 행에 `macos-x64` 실림(2-3 손 세기) · 덧문장은 인텔 실기기 관측 뒤 | 2-3(R4) 때 master | ☐ |
| N3 · K③ | 노트:31 휴지통 — 윈 줄 · 맥 줄 · 카톡 ③ 「직접 살펴보실 수」 | 윈: 탭 열림·목록·미리보기·삭제 꺼짐 안내(V1 · TRASH-2) · 맥: 실제 앱에서 미리보기 → 이름 입력 → 삭제 끝까지 1회(기록 없음 · `evidence/MAC-VISUAL-1.1.10.md` 는 상담소만) | 윈 = 오늘 저녁 ⓐ · 맥 = 별도 1회(누가 = master) | ☐ 윈 · ☐ 맥 |
| N4 | 노트:49 상담소·아고라 위쪽 단추줄 「윈도우와 맥」 | 윈 글꼴 좁은 창(800폭 안팎)에서 단추줄 안 잘림 사진(MENU-1~5) | 오늘 저녁 ⓐ | ☐ 윈 |
| N5 | 노트:58-60 하루 한 번 보고(상담소 끄기·켜기 · 첫 안내) | 윈 실기에서 첫 안내 창 · 「자동 보고」 줄 · 끄기/켜기 셋 | 오늘 저녁 ⓐ | ☑ 맥(10-23) · ☐ 윈 |
| N6 | 노트:68 자기 점검 윈 두 줄(닫힌 부서 흔적 · 관리되는 파일) | 윈 doctor 결과(MINOR-6 · MINOR-7) | 오늘 저녁 ⓐ | ☐ 윈 |
| N7 | 노트:80 윈도우 네 줄(휠 · 빈 창 · 계정 「확인 중」 · 오피스 한글) | WINQ-1 · WINQ-3 · WINQ-5 · V3 | 오늘 저녁 ⓐ | ☐ 윈 |
| K④ | 카톡 「달라진 점」 3줄 순서·낱말 | 라이브 공지 첫 부분과 대조(4-2 뒤) | 공지 배포 뒤 · 카톡 발송 전 | ☐ |

- 윈 칸이 ☐ 인 채로 발행 시각이 오면: 그 줄(N3 윈 · N4 · N5 윈 · N6 · N7)은 **빼거나 「맥」으로 좁혀** 공개한다(노트 머리 주석 「【발행 전 확인】 표시 줄은 실측 뒤에만 남긴다」) — 고르는 것은 master.
