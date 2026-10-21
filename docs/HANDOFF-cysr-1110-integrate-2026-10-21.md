# HANDOFF — TICKET=cysr-1110-integrate (1.1.10 통합 가지)

- 가지: `rel/1.1.10` · 작업트리 `~/cys-terminal-src-wt/rel-1110` · 기준 **8d81d780**(`rebase/v0.14.51` · 원작자 v0.14.49~51 편입) · 좌석 546(surface:1545) · 2026-10-21 23:4x ~ 10-22 01:3x
- 지시: 브리프 cysr-1110-integrate(①~⑥) · master#f55812f6(H-SECRET-1 A안) · master#f4d3dcf2(⑦ trash-harden 추가)
- **push 0 · 태그 0 · 판번 올림 0(1.1.9 유지) · 앱 설치/교체 0 · 발행 0 · 팩 지침 문구 수정 0** — 전부 로컬 커밋.
- 판정표 정본 = `docs/upstream/INTEGRATE-1.1.10.md`(이 문서는 요약 · 덩어리 1줄 판정·시험 표·팩 지침 표는 그쪽).

## 0. 한눈에

| # | 가지 @ 커밋 | 병합 커밋 | 텍스트 충돌 | 의미 충돌 |
|---|---|---|---|---|
| ① | `fix/1110-winqueue` @ c0f94df3 | `bf3e7666` | 0 | 3(toastaxis 시험) → `7bea2400` 로 해소 |
| — | 큐 폐기 알림 ↔ ALERTS_QUIET 연결 | `7bea2400` | — | — |
| ② | `fix/1110-minor` @ 2dc0ef15 | `7b983659` | 0 | 0 |
| ③ | `fix/1110-popfont` @ af852096 | `51171ad5` | 0 | 0 |
| ④ | `feat/menu-top-row` @ c120be7a | `0628356c` | 0 | 0 |
| ⑤ | `fix/1110-backlog` @ de8e1cd2 | `51571f59` | 0 | 0 |
| ⑥ | `docs/1110-naming` @ 29f02a2d(4커밋) | `8875ddca` | 1(`docs/RELEASE.md` → HEAD 유지) | 0 |
| — | H-SECRET-1 적 해소(A안) | `349c3ce0` | — | — |
| ⑦ | `fix/1110-trash-harden` @ 810dcbd0(9커밋) | `19af40c4` | 0 | 0 |
| — | 판정표 | `6872ed07` · `f791b797` · `c95276f9` | — | — |

## 1. 판정 요지

- **①-a 큐 폐기 알림**: `queue.dropped` 분기의 `toast(...)` → 데몬 출처 래퍼 `daemonToast(...)`. ALERTS_QUIET=true(원작자 값) = 박스 0 · false(우리 출하 값) = 박스 1 · 문구 「대기 중이던 지시 2건을 버렸습니다(기록은 남아 있습니다)」. 뮤턴트(되돌림) = 적 3.
- **①-b~f**: toastaxis 출처 핀·EVENTS 표(분기 22→23)·`feed-wait-banner` 지문(`7e292a7ea0458b84`→`17801e6610300e2c`, 선행 분기 추가로 생긴 의도된 표류)·wswiring 핀·queuedropnotice 머리 주석.
- **⑥-a**: `docs/RELEASE.md` 잠복 DMG 레그 줄 = HEAD(뒤의 docs-d `52f5a748` 이 같은 뜻으로 이미 고침) 유지.
- **⑦**: 화면(`ui/src/trashconfirm.ts`·`ui/src/main.ts` 추가 10줄)과 네이티브(`src-tauri/src/main.rs`)가 **같은 커밋 `19af40c4`** 에 있다(trashconfirm.ts·main.rs = 810dcbd0 바이트 동일 · main.ts 10/10 실재). 앱 번들 하나에 둘 다 실림(§2).

## 2. 시험(최종 트리 `f791b797` · 상세 = INTEGRATE §3)

| 시험 | 결과 |
|---|---|
| cargo `--lib` / `--bin cys` / `--bin cysd` | 1100 / 626 / 2698 통과 · 0 실패 |
| 앱(`src-tauri` cargo test) | 309 통과 · 0 실패 |
| ui bun / typecheck | 3173 통과 · 0 실패 / rc 0 |
| 팩 py 137 | 135 녹 · 적 2 = **기준선 8d81d780 도 같은 적**(아래) |
| 팩 추가 3 · `javis_org --self-test` · `test_update_publish` | 녹(phase1 은 격리 env 로 26 OK) · ok · 108 OK |
| `gen_ceo_template --check` · H-SECRET-1 | rc 0 · rc 0 |
| 앱 빌드 `--bundles app` | rc 0 · `cysr.app` 1.1.9 · 번들 `cys --version` = `cysr 1.1.9` · `confirmNonce`(화면)·`confirm_nonce`(네이티브) 둘 다 실림 · 설치·교체 0 |

적 2건(단독 3회 + 기준선 대조):
- `test_hook_r34` — RCF-3·RCF-4a·DL-1b 가 회마다 번갈아 「경과 < 3.0s」 상한을 0.0x~0.5s 넘음(3.00~3.49s) · 기준선도 같은 꼴 · hooks·시험 파일 무변경 ⇒ **시간 경계 플레이크 · 통합 무관**(부하 평균 4~7).
- `test_dept_team_token` — 18/23 적 · 기준선 18 · 적 이름 집합 동일 · 사유 `team_flow_dormant`(team-token 휴면) ⇒ **기준선 적 · 통합 무관**(vendor HANDOFF §4 와 같음 · 별건 티켓 후보).

## 3. H-SECRET-1(master#f55812f6 A안)

- 8d81d780 부터 적(전재 `docs/upstream/REVIEW-0.14.49-51-codex-1r.md` 의 개인 경로) + ② 유입 minor HANDOFF 의 윈 경로 2줄.
- `349c3ce0`: 전재 파일 `/Users/<사용자>`→`~` 23곳 + 머리 1줄 「경로만 치환 · 그 밖 무편집(원문 = codex 1R 출력)」 · minor HANDOFF `%USERPROFILE%` 2곳 · 스캐너 범위 밖 grep 1회 → 인코딩 경로 `-Users-<사용자>-` 7파일 같은 처방(`-Users-USER-`) · 계정 메일(공개 연락처)·GitHub 계정 이름 무변경 ⇒ **GREEN**(853파일).

## 4. master 판단 대상(이 티켓은 고치지 않았다)

팩 지침 문구 점검 표(INTEGRATE §5 · 21덩어리 · 전부 vendor 편입분)의 ⚠ 3갈래:
1. D1 `CEO_TEMPLATE.md` +59줄 「오너 원문」·「주인님의 명령」 = **원작자 오너** — System 소유라 전 설치 강제 · 우리 CEO 가 박사님 말로 오인할 위험.
2. C2 `CSO_DIRECTIVE.md` 「(오너 지시 2026-10-12)」 — CEO 쪽(D2)은 「원작자 S8 · v0.14.51 편입」 으로 고쳤는데 CSO 쪽은 그대로라 표기가 갈림.
3. 근거 주석 포인터 `CHARTER-RATIONALE.md` 는 팩 루트(`cysjavis-pack/CHARTER-RATIONALE.md`)에 있음(지침 옆 상대 경로로는 없음) + 「CEO 표시 A1~A9·A11」 = 원작자 조직 문면.

## 5. 남은 것

- **윈 실기 확인**: ⑦(휴지통 확인 단회 확인 · 뿌리 핸들 결박 — 이 맥에서 윈 교차 컴파일 불가 `libsqlite3-sys`) · ① winqueue(축1 휠·축2 layout_why·자리표) · ② minor ③⑥⑦ — 각 가지 HANDOFF 의 윈 절차대로.
- master 몫: push · 판번 1.1.10 올림 · 태그 · 앱 설치/교체 · 발행 · 위 §4 팩 지침 판단.
- 별건 후보: `test_dept_team_token` 18 적(휴면 ↔ 시험 불일치) · `test_hook_r34` 시간 상한 3.0s 여유(부하 시 0.0x~0.5s 초과).
- 스크래치 기준선 작업트리는 정리함(`git worktree remove`).
