# INTEGRATE-1.1.10 — 1.1.10 통합 가지 `rel/1.1.10` 병합 판정표

> TICKET=cysr-1110-integrate · 워커 546(surface:1545) · 작업트리 `~/cys-terminal-src-wt/rel-1110` · 2026-10-21~22
> 기준 = `rebase/v0.14.51` **8d81d780**(원작자 v0.14.49~51 편입 · `docs/HANDOFF-cysr-1110-vendor-2026-10-21.md`)
> **push 0 · 태그 0 · 판번 올림 0(1.1.9 유지) · 앱 설치/교체 0 · 팩 지침 문구 수정 0** — 전부 로컬 커밋.
> ⑦ `fix/1110-trash-harden` 은 master#f4d3dcf2(10-22 00:12) 추가 지시로 ①~⑥ 뒤 마지막에 합쳤다.

## 1. 병합 순서와 결과

| # | 가지 @ 커밋 | 가지 기준 | 병합 커밋 | 텍스트 충돌 | 의미 충돌(시험으로 드러남) |
|---|---|---|---|---|---|
| ① | `fix/1110-winqueue` @ c0f94df3 (7커밋) | origin/main fb386c49 | `bf3e7666` | 0 (자동 병합 7파일) | **3** — 아래 §2-① |
| — | (연결) 큐 폐기 알림 ↔ ALERTS_QUIET | — | `7bea2400` | — | 위 3건 해소 |
| ② | `fix/1110-minor` @ 2dc0ef15 (8커밋) | fb386c49 | `7b983659` | 0 (자동 병합 2파일) | 0 |
| ③ | `fix/1110-popfont` @ af852096 (1커밋) | v1.1.9 d8e8f0a2 | `51171ad5` | 0 (자동 병합 2파일) | 0 |
| ④ | `feat/menu-top-row` @ c120be7a (1커밋) | v1.1.9 d8e8f0a2 | `0628356c` | 0 (자동 병합 2파일) | 0 |
| ⑤ | `fix/1110-backlog` @ de8e1cd2 (1커밋) | e2532e05 | `51571f59` | 0 | 0 |
| ⑥ | `docs/1110-naming` @ 29f02a2d (4커밋 · 머리 = cysr-1110-docs HANDOFF · 10-10 · master#e6c5cb95) | 4f660dfb | `8875ddca` | **1파일 1덩어리** — §2-⑥ | 0 |
| — | H-SECRET-1 적 해소(master#f55812f6 A안) | — | `349c3ce0` | — | §4 |
| ⑦ | `fix/1110-trash-harden` @ 810dcbd0 (9커밋 · codex 4R ACCEPT · HANDOFF `docs/HANDOFF-cysr-1110-trash-harden-2026-10-21.md`) | 8d81d780(rebase 완료) | `19af40c4` | 0 (자동 병합 1파일: `ui/src/main.ts`) | 0 |

## 2. 덩어리별 판정 (1덩어리 = 1줄)

| # | 파일 · 자리 | 판정 | 근거 |
|---|---|---|---|
| ①-a | `ui/src/main.ts` `queue.dropped` 분기 — `toast(...)` 직접 호출 | **winqueue 뜻 보존 + TOAST 축 래퍼로** — `daemonToast(...)` | winqueue HANDOFF §5 「ALERTS_QUIET 가 들어오면 이 토스트도 그 스위치를 따라야 한다 — 연결은 master 통합 때」 · vendor 의 출처 규칙(데몬 이벤트 출처 = 래퍼 경유 · 직접 호출은 넷뿐) |
| ①-b | `ui/src/toastaxis.test.ts` 출처 핀(onDaemonEvent 직접 호출 rest 0) | 적 → ①-a 로 녹 · `daemonToast` 계수 9 → 10 | 새 분기는 데몬 출처 — 직접 호출 목록(넷)에 넣지 않는다 |
| ①-c | 같은 시험 「전 이벤트 분기를 덮는다」(EVENTS 표 · 분기 22) | EVENTS 표에 `queue.dropped.owner_close` 행 + 퍼즈 이름 + 분기 22 → 23 | 표가 소스의 name 분기와 일치해야 한다는 시험의 뜻 그대로 |
| ①-d | 같은 시험 남긴 자리 지문 `feed-wait-banner` | 재계산 `7e292a7ea0458b84` → `17801e6610300e2c` | 지문은 앞선 제어 흐름 줄을 포함 — 선행 분기 `queue.dropped` 추가로 생긴 의도된 표류(시험 머리 주석 「의도된 변경이면 pin 을 다시 계산해 넣는다」) · 래퍼 변경 전후 같은 값(분기 줄 자체가 원인) |
| ①-e | `ui/src/wswiring.test.ts` 큐 폐기 배선 핀 | `toast("feed", …)` → `daemonToast("feed", …)` | ①-a 와 한 몸 |
| ①-f | `ui/src/queuedropnotice.ts` 머리 주석 「연결은 master 통합 때」 | 「연결됨(daemonToast · 시험 두 값)」 으로 | 사실이 바뀜 |
| ⑦-a | `ui/src/main.ts` 자동 병합(trash-harden 의 휴지통 확인 배선 · `confirmNonce`) | 가지의 추가 10줄 **전부 실재**(줄 단위 대조 10/10) | 다른 가지(winqueue·popfont)가 바꾼 자리와 겹치지 않음 |
| ⑥-a | `docs/RELEASE.md` §1 잠복 DMG 레그 줄(`Install cys.app`·`.support/cys.app`) | **HEAD(8d81d780) 유지** | 같은 줄을 뒤의 cysr-1110-docs-d(`52f5a748`)가 같은 뜻(「원작자 판 DMG 꼴 · 옛 이름 — 우리 포크 자산은 zip 안 cysr.app 하나」)으로 이미 고쳤고 publicdocs 줄 규칙까지 붙었다 — ⑥ ③ 의 뜻(옛 이름 표지) 보존 · 문장만 docs-d 판 |

자동 병합(텍스트 충돌 0) 파일 중 두 가지 이상이 함께 바꾼 것 — 시험으로만 확인(§3):
`src/bin/cys.rs`(vendor · winqueue · minor) · `src/bin/cysd/governance.rs`(vendor · winqueue · minor) · `src/bin/cysd/handlers.rs`·`state.rs`·`delivery.rs`(vendor · winqueue) ·
`ui/src/main.ts`(vendor · winqueue · popfont) · `ui/src/style.css`(popfont · menu-top-row) · `ui/index.html`(menu-top-row) · `cysjavis-pack/bin/tests/run_bootstrap_health.py`(vendor · ⑥).

### ⑦ 휴지통 확인 — 화면과 네이티브가 같은 커밋에 있는가(master#f4d3dcf2)

| 쪽 | 파일 | 병합 커밋 `19af40c4` 에서 |
|---|---|---|
| 화면 | `ui/src/trashconfirm.ts`(거부 문구 `confirm_unbound` 등) · `ui/src/main.ts`(삭제 명령에 `confirmNonce: prev.confirm_nonce` · `typed`) | trashconfirm.ts = 810dcbd0 과 **바이트 동일** · main.ts = 가지 추가 10줄 전부 실재 |
| 네이티브 | `src-tauri/src/main.rs`(`trash_preview_poll` 이 `confirm_nonce` 발급 · `trash_delete` 단회 확인 꺼냄 · `confirm_unbound`/`confirm_expired`/`phrase_mismatch`) | 810dcbd0 과 **바이트 동일** |

⇒ **같은 커밋(`19af40c4`)에 함께 있다** — 구 화면 + 새 네이티브(= `confirm_unbound` 거부 · 삭제 0) 조합은 이 가지에서 생기지 않는다. 앱 번들 하나에 둘 다 실리는지는 §3 앱 빌드에서 확인.
윈도우 교차 컴파일 = 이 맥 불가(`libsqlite3-sys` C 교차 컴파일러 부재 · trash-harden HANDOFF §2-6) → **윈 실기 확인**(CI 윈도우 잡·윈 실기).

### 큐 폐기 알림 ↔ ALERTS_QUIET 시험 두 값(`7bea2400`)

| 스위치 | 기대 | 결과 |
|---|---|---|
| `ALERTS_QUIET=true`(원작자 값 · 샌드박스 주입) | 사람이 닫은 좌석 큐 폐기 2건 → 박스 0 · sticky 0 · OS 배너 0 · 알람 이력 0 | 녹 |
| `ALERTS_QUIET=false`(우리 출하 값) | 박스 1 · sticky 0 · OS 배너 0 · 알람 이력 1(문구 「대기 중이던 지시 2건을 버렸습니다(기록은 남아 있습니다)」) · 회수(owner_close 없음)·0건 = 0 | 녹 |
| 뮤턴트(`daemonToast` → `toast` 되돌림) | 적 | **적 3**(T-1 전수 행 · 두 값 시험 · 출처 핀) → 원복 |

## 3. 전수 시험

(§3 표는 시험 완료 뒤 채운다)

## 4. H-SECRET-1 (발행 차단 게이트)

| 단계 | rc | 내용 |
|---|---|---|
| 8c2e1a24(vendor · 전재 직전) | 0 | 기준선 확인용 |
| **8d81d780(통합 기준)** | **1** | `38508fc4` 가 전재한 `docs/upstream/REVIEW-0.14.49-51-codex-1r.md` 의 개인 경로 — 통합 무관 · 기준부터 적 |
| rel/1.1.10 병합 ①~⑥ 뒤 | 1 | 위 + `docs/HANDOFF-cysr-1110-minor-2026-10-21.md` 윈 실측 원문의 `C:\Users\<사용자>` 2줄(통합 ② 유입 · WIN-PATH) |
| **`349c3ce0` 뒤** | **0** | master#f55812f6 A안: 전재 파일 = `/Users/<사용자>` → `~` 23곳 + 머리 1줄 「경로만 치환 · 그 밖 무편집(원문 = codex 1R 출력)」 · minor HANDOFF = `%USERPROFILE%` 2곳 |

**스캐너 범위 밖 grep 1회**(master 지시 · `git grep` 추적 파일 전수 · 꼴 3종 `/Users/<사용자>` · `C:\Users\<사용자>` · `-Users-<사용자>-` + 계정 메일):
- 인코딩된 개인 경로 `-Users-<사용자>-`(스크래치패드·projects 폴더 이름 속) **7파일 7곳** — 같은 처방(`-Users-USER-`): `HANDOFF-T3.md` · `docs/117/HANDOFF-lead.md` · `docs/HANDOFF-A1-2.md` · `docs/HANDOFF-v116-usage.md` · `docs/WINTEST-v116-bundle-draft.md` · `docs/menu-top-row-evidence/regress-v116-before.txt`(통합 ④ 유입) · `docs/merge/HANDOFF-118-lead.md`.
- 계정 메일 = `README.md`·`README.en.md`·`SECURITY.md`·`src-tauri/src/feedback.rs` 의 **공개 연락처**(`scripts/secret-scan.sh:101` 허용 근거 주석 실재) — 무변경.
- GitHub 계정 이름(`oogisoogi/cys-ro` 등 저장소 주소) — 공개 주소라 무변경.
- 치환 뒤 3꼴 잔존 `git grep` = 0 · H-SECRET-1 GREEN(853파일) · publicdocs 18/0.

## 5. 팩 지침 문구 점검 표 (판단은 master — 이 티켓은 고치지 않았다)

범위 = `origin/main fb386c49 → rel/1.1.10` 의 4파일 덩어리 21개(통합 ①~⑥ 은 이 4파일을 건드리지 않았다 — `git diff 8d81d780 HEAD -- cysjavis-pack/directives/` = 빈 · 전부 vendor 편입분).
「우리 사용자에게 보이는가」 기준: 팩 소유권(`src/pack.rs ownership`) — `*_DIRECTIVE.md` = **User**(기존 설치 = `.new` 병치 → `cys pack-merge` 대화 화면에 diff 로 **보인다** · 새 설치 = 그대로 깔림) · `CEO_TEMPLATE.md` = **System**(갱신 때 전 설치에 강제 반영 · 부서 CEO 승격 때 규약 파일이 된다). 에이전트가 읽고 행동·말투로 옮기는 문면은 「간접 노출」로 적는다.

| # | 파일 · 덩어리 | 원작자 출처 | 우리 사용자에게 보이는가 | cysr 명명 정본과 맞는가 |
|---|---|---|---|---|
| D1 | `CEO_TEMPLATE.md` +59줄 「CEO 와 master 의 차이 — ★오너 복원 조항」 + 「부가 원칙 — CEO 행동규약의 수정 권한」(머리 14행~) | `bec69f49` 「주인님 조항을 발행 라인 CEO 템플릿에 상류화(저자 CEO · 추가 59줄)」 | **예 · 전 설치 강제**(System) — 부서 CEO 승격 때 규약 본문이 된다. 에이전트가 「오너 원문」 으로 인용·집행하는 문면이라 행동·말투로 노출 | 낱말 `cys` 0 · 「자비스」 2(원작자 오너 원문 인용 1 + 적용 주석 1) · `~/Desktop/CYSjavis/_evidence/…`(폴더 이름 = 식별자 예외). ⚠**판단 대상**: 「오너 원문」·「주인님의 명령」·「2026-10-13 dept-6 소실 · 107,320 B」 는 **원작자 쪽 오너·사건**이다 — vendor 가 CEO reap 문장의 「(오너 지시 2026-10-12)」 를 「(원작자 S8 · v0.14.51 편입)」 으로 고친 것과 같은 축의 오인(우리 CEO 가 원작자 오너 말을 박사님 말로 집행) 위험. 우리 호칭(박사님)과도 다름 |
| D2 | `CEO_TEMPLATE.md` 116행 「★이름이 닮은 두 reap」 ⓑ 문장 | S8 `48c8437b`·`fba8da68`(격리분 자동 소거 약속 삭제) + **우리 수정**(출처 표기 「원작자 S8 · v0.14.51 편입」 · vendor 병합 커밋 `ba38b6aa` 충돌 해소) | 예 · 전 설치 강제(System) · 간접(CEO 행동) | `cys reap-surface` = 백틱 속 명령 식별자 ✔ · 「Control Center 의 휴지통」 = 앱 화면 이름(제품명 아님) ✔ |
| D3~D10 | `CEO_TEMPLATE.md` 근거 HTML 주석 8블록 → 한 줄 포인터(553·586·615·632·637·642·646·657행) | `6814a762` 「CEO 가 표시한 근거 주석 10블록을 이관」 | 예(System) — 단 **HTML 주석**이라 마크다운 표시 화면엔 안 보이고 에이전트·파일 열람에만 보인다 | `cys` 0 ✔. ⚠포인터 문면 「CEO 표시 A1~A9·A11」 = 원작자 조직의 CEO 표시 이력 · 포인터 대상 `CHARTER-RATIONALE.md` 는 `directives/` 옆이 아니라 **팩 루트** `cysjavis-pack/CHARTER-RATIONALE.md` 에 있다(상대 경로로 읽으면 없음 · 옮긴 블록 3개 표본 = 원문 그대로 실재 확인 · 그 블록들은 v0.14.48 원작자 원문) |
| M1~M8 | `MASTER_DIRECTIVE.md` 같은 8블록 → 한 줄 포인터(412·445·474·491(2줄)·496·501·505·516행) | `6814a762`(MASTER 가 원본 · CEO 는 `gen_ceo_template.py` 재합성으로 따라옴) | User — 기존 설치 = `.new` 병치 → `cys pack-merge` 화면 diff 로 보임 · 새 설치 = 그대로. HTML 주석이라 표시 화면엔 안 보임 | `cys` 0 ✔ · 위 D3~D10 과 같은 ⚠2건(원작자 CEO 표시 문면 · 포인터 경로) |
| C1 | `CSO_DIRECTIVE.md` 344행 §3-1 제목 「부서 폐역 격리(trash) 소거 — … CSO 소유」 → 「★너의 직무가 아니다(S8 에서 삭제된 조항)」 | S8 `48c8437b`·`fba8da68` | User(pack-merge 화면 diff) · 간접(CSO 행동 — 격리분에 손대지 않음) | `cys` 0 ✔ |
| C2 | `CSO_DIRECTIVE.md` 347~355행 §3-1 본문(만료 reap 점검 지시 삭제 → 허용 = 보고 1줄 · 금지 = 지우는 어떤 조치도) | S8 `48c8437b`·`fba8da68` | User(pack-merge 화면 diff) · 간접(CSO 다이제스트에 「오래된 격리분 N건·총 X GB」 1줄로 노출) | `cys-dept reap` · `TRASH-OLD=` = 백틱 속 식별자 ✔ · 「Control Center 의 휴지통」 = 화면 이름 ✔. ⚠**판단 대상**: 본문 「(**오너 지시 2026-10-12**: 휴지통 삭제는 오너가 명령할 때만 일어난다)」 = 원작자 오너 지시 — CEO 쪽(D2)은 vendor 가 「원작자 S8 · v0.14.51 편입」 으로 고쳤는데 **CSO 쪽은 그대로**라 두 파일 표기가 갈린다 |
| R1 | `RSI_LEARNING_DIRECTIVE.md` 42행 근거 HTML 주석(learn_proposal 6건 적체 · 2026-09-04 전면 감사) → 한 줄 포인터 | `6814a762` | User(pack-merge 화면 diff) · HTML 주석이라 표시 화면엔 안 보임 | `cys` 0 ✔ · D3~D10 과 같은 ⚠2건 |

덩어리 수: CEO_TEMPLATE 10(D1 · D2 · D3~D10) · MASTER 8(M1~M8) · CSO 2(C1 · C2) · RSI 1(R1) = **21**(`git diff -U0 fb386c49 HEAD` 의 `@@` 수와 일치).
같은 편입이 바꾼 짝 파일(이 표 범위 밖 · 참고): `CEO_CORE.md` 6줄 · `MASTER_CORE.md` 2줄 · `RELEASED_MASTER_DIRECTIVE.sha256` +3(vendor HANDOFF §2 — 절 해시 갱신).
master 판단을 요하는 ⚠ 3갈래: ⑴ D1 「오너 원문」 귀속(원작자 오너 ↔ 박사님) ⑵ C2 「오너 지시 2026-10-12」 표기가 D2 와 갈림 ⑶ 포인터 경로 `CHARTER-RATIONALE.md`(팩 루트) 와 원작자 CEO 표시 문면.
