# HANDOFF — TICKET=cysr-1110-vendor (원작자 v0.14.50·v0.14.51 편입 · 1.1.10) · 2026-10-21

> 워커 540(surface:1539) · 가지 `rebase/v0.14.51` · 작업트리 `~/cys-terminal-src-wt/rebase-01451` · 기준 = origin/main `fb386c49`(v1.1.9 + 1)
> **push 0 · 태그 0 · 앱 설치/교체 0 · 발행 0 · 편입 제외(ⓔ) 0** — 전부 로컬 커밋.
> 판정표 정본 = `docs/upstream/MERGE-0.14.49-51-PLAN.md` · codex 1R 원문 = `docs/upstream/REVIEW-0.14.49-51-codex-1r.md`(전재 · 무편집)

## 0. 한눈에

| 항목 | 값 |
|---|---|
| 편입 방식 | `git merge --no-ff v0.14.51` 1회(직전 cysr-1110-upstream 과 같은 방식 · 커밋별 rebase 아님 — 우리 쪽 v0.14.48 이후 1,378 커밋) |
| 기준 태그 | 원작자 **발행 태그** v0.14.50 `0a20e3ba` · v0.14.51 `2deb095c` (로컬 태그 = `upstream` 원격 태그 커밋 일치 실측) |
| `UPSTREAM_BASE` | v0.14.48 → **v0.14.51** |
| 원작자 변경 | 176 커밋 · 88 파일 · +17,899/−855 |
| 텍스트 충돌 | **26 파일 · 46 덩어리** |
| 판번 | 우리 **1.1.9** 유지(7파일) · productName `cysr` 유지 · 원작자 판번 올림 3커밋 = 판번 규칙(§0-2 7) 적용 |
| ⓔ 제외 | **0건** |
| codex 1R(ⓓ) | **REVISE** — blocking 2 · major 4 · 병합 해소 결함 0 → master 결정(A안): B1·M2 이 티켓 수리 완료 · B2·M1·M3·M4 = `cysr-1110-trash-harden` 이관 |
| master 결정 | ① 21:49 TOAST 축 = A안(구조 편입 · 스위치 false · S5 제거 미수용) ② 22:09 codex = A안(B1·M2) |

### 커밋(origin/main 위 · 시간순)

| 커밋 | 내용 |
|---|---|
| `ba38b6aa` | 병합 — 충돌 26파일 해소 · UPSTREAM_BASE |
| `234fc129` | 판정표 + 설명서 S5 서술 되돌림 + starved 시험 래퍼 대응 + 휴지통 토스트 원문 → 자세히 |
| `2b2179b7` | 원작자 TOAST 축 시험(862줄)을 우리 main.ts 에 맞춤(quiet true/false 둘 다) — **trash-harden 출발점으로 【기준】 보고한 커밋** |
| `d8e28331` | 편입 회귀 5건(발행 해시 표 · CORE 요지 · CEO §2 줄 · product-cpu 기준 · s5 글자 경계) |
| `eea89fca` | codex B1 수리(hooks 보고 팩 밖 판독 차단) |
| `45939c8e` | codex M2 수리(부서명·도장 경로 성분 검증) |
| `8c2e1a24` | 편입 회귀 2건(F5 ps NOWIN · H-SECRET-1 배선) |
| (이 문서 커밋) | HANDOFF · codex 원문 |

## 1. 판정표 요약 (정본 = MERGE-0.14.49-51-PLAN.md §2)

| 묶음 | 판정 |
|---|---|
| G1 0.14.49 HUD 다리 윈 로케일 · G3 hooks/ 드리프트 보고 · G4 soul L0 머리 · G5 product-cpu · G7 CI·노트 · G8 S1/S2 quiescing · G10 S5 carrier-B(휴면) · G15 codex `--no-daemon` · G16 names 시험 | ⓐ (G3 은 ⓓ 병행) |
| G2 F7 승인 디코더 | ⓑ ⓓ — 우리 BOM 벗기기를 원작자 단일 디코더 안으로 |
| G6 B-070 secret-scan 한도 · G14 지침·헌장 · G17 handlers 검체 · G19 S51 밀기 전 게이트 · G20 CI 목록 | ⓑ |
| G9 **S8 휴지통**(정리 작업이 지우지 않음 · 삭제 = 휴지통에서 오너 명령 · 윈 삭제 feature 기본 꺼짐) | ⓑ ⓓ |
| G11 **S5 큐 막힘 경보 제거** | **ⓑ 우리 유지** · 표시 끄기는 G13 스위치(새 싱크 `starvedNotice`) |
| G12 S7 | 해당 없음 — 원작자가 같은 태그 안에서 17커밋 전부 되돌림(순변화 0) |
| G13 **S10 TOAST 축** | **ⓑ 구조 수용 · `ALERTS_QUIET=false` · `ALERT_PROSE_QUIET=false`**(원작자 true) |
| G18 판번 올림 | 판번 규칙 — 우리 1.1.9 |

## 2. 【경고】 지침 파일이 바뀐다 (denylist② 성격 — master 인지 필요)

편입으로 팩 지침 4파일의 **바이트가 바뀐다**: MASTER_DIRECTIVE.md 86,991 → 84,186 · CSO_DIRECTIVE.md 57,347 → 57,680 · CEO_TEMPLATE.md 95,201 → 99,423(재합성) · RSI_LEARNING_DIRECTIVE.md 5줄.
- 내용: ⑴ 원작자 S8 — 「격리분 TTL 자동 소거 · CSO 소관」 조항 삭제 → 「CSO 는 격리분에 아무것도 하지 않는다 · 삭제 = 오너 휴지통 명령」(CSO_DIRECTIVE §3-1 · CEO 머리 reap 계약) ⑵ 원작자 6814a762 — MASTER/CEO 의 HTML 근거 주석 10블록을 `CHARTER-RATIONALE.md` 로 이관(규칙 본문 불변 · 한 줄 포인터) ⑶ 원작자 bec69f49 — CEO 템플릿에 「주인님 조항」 59줄 상류화.
- 우리가 손댄 것: CEO 머리 reap 문장의 「(오너 지시 2026-10-12)」 → 「(원작자 S8 · v0.14.51 편입)」(원작자 오너의 지시를 우리 박사님 지시로 오인하지 않게) · CEO_CORE 요지의 reap 문장을 S8 계약으로 · MASTER/CEO_CORE 절 해시 갱신.
- `docs/proposals/directives-0.14.51/*.new` 는 원작자 **제안 문서**일 뿐 적용되지 않는다.

## 3. 시험 (실측)

| 레인 | 결과 | 비고 |
|---|---|---|
| UI `cd ui && bun test` | **3154 pass / 85 skip / 0 fail**(97 파일) | 기준선 origin/main 0 fail · 병합 직후 109 fail → 0 |
| cargo `--lib` | **1095 / 0** (2 ignored) | 병합 직후 1093/1(released_tables_cover_current_embed) → 수리 |
| cargo `--bin cys` | **625 / 0** | |
| cargo `--bin cysd` | 2677 / 3 → **3건 단독 재실행 3회씩 전부 녹** | 부하 의존 플레이크 판정: `alert_route::drills::drill_clear_signal_load_does_not_hold_self_heal_alerts` · `…drill_edge_loop_clear_signals_are_never_held_by_the_hourly_cap` · `return_absorb_tests::a2_absorbed_return_never_hits_queue_full` — 첫 전체 실행(22:0x)에선 셋 다 녹 · 편입이 두 파일을 건드리지 않음(`git diff origin/main HEAD -- alert_route.rs return_absorb_tests.rs` = 빈) · 병합 직후 첫 실행 적 1건(s5 source_pin · 글자 경계 패닉)은 수리 |
| 팩 Python(ci-branch 등재 목록 137) | **136 / 1** | 적 1 = `test_dept_team_token`(18건) — **기준선 origin/main 에서도 18건 적**(편입 무관 · D-TEAM 휴면과 시험 불일치로 보임 · 별건) · `test_dept_name_guard` 1회 적은 재실행 75/75 녹(경쟁 기동 타이밍) |
| `run_bootstrap_health.py --only H-SECRET-1` | GREEN(853파일) | 우리 측정 실패 5형 검체 그대로 |
| `gen_ceo_template.py --check` | GREEN(99,423 B) | |
| cargo src-tauri(app) | **305 / 0** (2 ignored) | 1건 적 → 수리(아래) · 기준선 메모 261(1.1.10 선 시점) |
| 앱 빌드 `--bundles app` | **rc 0** | §8 |

### 3-1. app 시험 수리 1건(`#[cfg(test)]` 만)

원작자 S8 핀 `s8_trash_commands_are_registered_and_the_token_attach_list_is_the_locked_set` 가 「운영자 토큰을 붙이는 최상위 명령 = 잠근 5개」를 단언 — 우리 포크는 `run_sidecar_restore_report`(1.1.x 복원 보고 · **편입 전 origin/main 4169행에서도 대상 데몬 토큰을 붙였다**)가 더 있고, 우리 `daemon_state_dir_for` 의 doc 주석이 함수 이름을 적어 시험이 호출로 셌다. → 잠근 집합에 우리 명령을 명시(주석으로 근거) + 주석 줄의 이름 언급은 건너뜀. **부착면을 넓힌 것이 아니라 원래 있던 것을 표에 올렸다** — trash-harden(M1 IPC 결박)이 이 표를 본다.

## 4. codex 1R (ⓓ) — 결과와 처리

원문 전재 = `docs/upstream/REVIEW-0.14.49-51-codex-1r.md`(아래는 처리 표 · 원문 대체 아님).

| # | 등급 | 자리 | 처리 |
|---|---|---|---|
| B1 | blocking | src/pack.rs hooks 드리프트 보고 — `hooks/../..` 키·심링크로 팩 밖 판독 | **수리 `eea89fca`** — `hooks_rel_confined`(성분 전부 Normal · 경로 위 심링크 0) 아니면 열지 않고 「판독 불가」 · 시험 적→녹 · 뮤턴트 적 · 실제 팩 4개의 hooks/ 심링크 0 실측 |
| B2 | blocking | trash.rs:1243/971/1018 비동기 삭제 경로 재해석 TOCTOU | **이관** → `cysr-1110-trash-harden`(master 별 좌석) |
| M1 | major | main.rs:5152 · trashconfirm.ts:27 타이핑 확인이 IPC 경계에 결박 안 됨 | **이관** |
| M2 | major | javis_org.py destroy_dept name·`CYS_TRASH_STAMP` 성분 미검증(+ cys-dept purge-state 도장) | **수리 `45939c8e`** — 실측 재현: 도장 `../../evil` 이면 state 가 `.local/state/evil`(cys-trash 밖)로 이동(rc 0) · 이름 검증 결손은 **편입 전 우리 main 에도 있던 것**(ba38b6aa^1 javis_org.py:665) · 시험 적→녹 · 뮤턴트 둘 다 적 |
| M3 | major | `.producer` 표식 read-then-replace 비원자 | **이관** |
| M4 | major | factory_reset.rs:1622/1656 확인 대기 중 부모 경로 교체 | **이관** |
| Q1 | — | 승인 저장소 판독 fail-closed · 스케줄 건너뜀 관문 | 통과(codex) |
| Q3 | — | 윈 삭제 feature 미활성 빌드 = 꺼짐 · reap 은 지우지 않음 | 통과(codex) |
| Q4 | — | 병합 해소 결함 | 0(HOLD·TRASH-OLD·expect_gen·rc=12 보존 확인) |

## 5. 다른 티켓과 겹치는 파일

**cysr-1110-winqueue(541)·cysr-1110-minor 와 같은 파일**(이 가지가 바꾼 것 · 89 파일 중):
- `src/bin/cysd/governance.rs` — 원작자 S1/S2 quiescing 표지(자동 병합 · 우리 손 0) ← winqueue(큐 input_pending)·minor(①④ occupied·seat_claimable) 와 같은 파일
- `src/bin/cysd/handlers.rs` — 원작자 S8·S2·S74 자동 병합 + 충돌 1(우리 주석)
- `src/bin/cysd/delivery.rs` — MAX_PARTS 우리 6000 유지(충돌 3)
- `src/bin/cys.rs` — `ALERT_PROSE_QUIET=false` · 원작자 TOAST 산문 7곳 래퍼 · S8 휴지통 CLI
- `ui/src/main.ts` — TOAST 래퍼 · **queue.starved 블록 복원(starvedNotice 가드)** · dismissStarvedToast 등 · 휴지통 UI ← winqueue(큐 정지·altscroll) 와 같은 파일
- `ui/src/starvednotice.test.ts` · `ui/src/starvednotice-split.test.ts` — 샌드박스 대역·핀
- `ui/src/alertquiet.ts` · `ui/src/toastaxis.test.ts` — 신규(원작자) + 우리 값
- **trash-harden** 과: `cysjavis-pack/bin/javis_org.py` · `cysjavis-pack/bin/cys-dept` · `cysjavis-pack/bin/tests/test_producer_marker.py`(M2 수리) — 그 좌석은 `2b2179b7` 에서 출발했으므로 `45939c8e` 를 함께 가져가야 한다.

## 6. 남은 것 · 다음 판 후보

1. **【다음 판 후보】 TOAST 축 스위치를 켤지(박사님 화면 정책)** — 1.1.10 범위 밖(master#1a52b068). 켜기 = `ui/src/alertquiet.ts` `ALERTS_QUIET` · `src/bin/cys.rs` `ALERT_PROSE_QUIET` 각 1줄 · 시험은 두 값 모두 녹으로 준비됨.
2. TOAST 축이 덮지 않는 데몬 출처 화면 1곳(서브에이전트 보고 · 수리 안 함): `onDaemonEvent` 맨 앞 `isMasterSeatSignal(...) → maybeShowRestoreBrief()` 복원 카드 — 스위치를 켜도 남는다. 켤 때 함께 판단.
3. **About 「based on cys 0.14.51」**(§0-2 7) — 현재 앱·문서 어디에도 그 표기가 없다(편입 전 v0.14.48 시절에도 없음 · `git grep -i 'based on cys'` 0건). 새 기능이라 이 티켓에서 만들지 않았다.
4. `test_dept_team_token` 18건 적 — 기준선 main 에서도 적(편입 무관) · 별건 티켓 후보.
5. 윈 실기 — S8 휴지통(윈 삭제 feature 꺼짐 확인)·TOAST 래퍼·HUD 다리(G1) 는 맥 시험만 했다(윈 0).
6. codex B2·M1·M3·M4 → `cysr-1110-trash-harden`.

## 7. 실측 기록 (§0-2 6)

| 항목 | 값 |
|---|---|
| 착수 → 병합 커밋 | 21:45 브리프 → 21:54:30 `ba38b6aa` (시험 병합 21:47:17) |
| 충돌 파일 / 덩어리 | 26 / 46 |
| 병합 후 회귀 수리 | UI 109건(TOAST 시험 54 · starved 33+ · publicdocs 2 · D4 2 등) · lib 1 · cysd 1 · 팩 7 |
| 리뷰 | codex 1R 22:01:13~22:07:54(6분 41초 · REVISE) · master 결정 2회(21:49→21:49:49 · 22:09:07→22:09:29) |
| 시험 시간(맥 arm64) | UI 1.3~2.2초 · cargo lib 359초(단독)/858초(부하) · cys 217/290초 · cysd 597/660초 · 팩 목록 137개 26분 47초 |
| 앱 빌드 | 3분 38초(runtime 복제 34초 · precompile 7초 · tauri build 3분 38초 중 대부분) |

## 8. 앱 빌드 결과

| 항목 | 값 |
|---|---|
| 명령 | 저장소 루트에서 runtime = `cp -cR ~/cys-terminal-src/src-tauri/runtime src-tauri/runtime`(APFS 복제 · 원 체크아웃 무접촉) → `sh scripts/precompile-bundled-python.sh`(rc 0) → `unset NODE_OPTIONS; bunx @tauri-apps/cli@2 build --bundles app --config '{"bundle":{"createUpdaterArtifacts":false}}'`(선례 = docs/rebase-v0.14.27-report §5) |
| 결과 | rc 0 · 23:30:22 → 23:34:41 · `target/release/bundle/macos/cysr.app` 1.0 GiB |
| 확인 | Info.plist `CFBundleShortVersionString` = 1.1.9 · `CFBundleIdentifier` = com.cysjavis.terminal · 번들 `Contents/MacOS/cys --version` = `cysr 1.1.9` · 동봉 `pack.tar.gz` 492 파일 · 그 안 `bin/javis_org.py` 에 M2 수리(`invalid_stamp`) 4곳 실재 |
| 하지 않은 것 | `cys-local` 서명 · ditto 설치 · canary — **설치/교체 0**(master/박사님 게이트) |
