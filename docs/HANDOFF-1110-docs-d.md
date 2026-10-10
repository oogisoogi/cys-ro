# HANDOFF — 1.1.10 문서 묶음 D + 파이썬 이름 일치 종료 6곳 (TICKET=cysr-1110-docs-d)

가지 `fix/1110-docs` · 기준 `e2532e05`(1.1.10 선) · 워커 324(surface:1323) · 2026-10-10 15:49~ · push 0 · 실 홈 쓰기 0.
브리프 = `~/axdev/master/briefs/2026-10-10-cysr-1110-docs-d.md`(master#b24f81b1) · 추가 ⑤ = master#d902f510.

## 0. 델타(이 티켓이 바꾼 것)

| 항목 | 커밋 | 바뀐 파일 | 한 줄 |
|---|---|---|---|
| ① 공개 문서 `cys.app` 3분류 + 줄 규칙 | `52f5a748` | `ui/src/publicdocs.test.ts` · `docs/RELEASE.md`(1줄) | 현행형 잔존 1줄 고침 · 현행 안내 문서 19파일에 거는 줄 규칙 1개 |
| ② RELEASE.md 를 정본 줄과 맞춤 | `ae4a9a78` | `docs/RELEASE.md`(4곳) | 후처리 조준 DMG → zip 속 .app · 없는 체크리스트 행 가리키던 문장 · 고아 3줄 |
| ③ 옛 인앱 갱신 현행형 | `3bfefec8` | `docs/RELEASE.md`(3곳) | 「인앱 업데이트」·없는 단추·없는 기록 파일 → 데몬 자동 갱신 |
| ⑤ 내부 절차 3문서 | `71cef030` | `docs/RELEASE-ROLLBACK.md` · `docs/KEY-ROTATION.md` · `docs/WINDOWS-UPGRADE-ATOMICITY-CHECKLIST.md` | ③ 과 같은 기준 · 시험 추가 없음 |
| ④ 파이썬 이름 일치 종료 6곳 → pid/pgid 장부 + 검체 2 | `a6401ee1` | `cysjavis-pack/bin/javis_phoenix_harness.py` · `cysjavis-pack/bin/tests/test_d1_dept_ready_probe.py` · `cysjavis-pack/bin/tests/run_bootstrap_health.py` | 하네스 5곳 · d1 시험 1곳 · H-PY-PKILL-1(정적) · H-PY-PKILL-2(행동) |

Rust·UI 제품 코드 변경 0. 팩에서 바뀐 것은 시험 하네스·시험·검체뿐(디렉티브·훅·합성기 무접촉).

## 1. `cys.app` 3분류 표(①)

실측: `git grep -n 'cys\.app' -- '*.md'` = **139건 · 121줄 · 29파일**(기준 `e2532e05`).

**현행 안내 문서**(= `publicdocs.test.ts` 명칭 매니페스트 22개에서 판별 릴리스 노트 3개를 뺀 19파일) 안 = 4파일 20줄 26건.

| 분류 | 줄 | 처리 |
|---|---|---|
| 현행형(틀린 글) | `docs/RELEASE.md:249` — 맥 CI 레그 절이 원작자 판 DMG 꼴(`Install cys.app` · `.support/cys.app`)을 표지 없이 적음 | 고침: 「원작자 판 DMG 꼴 … 옛 이름 — 우리 포크 자산은 zip 안 `cysr.app` 하나다」 |
| 옛 자리 서술(맞는 글) | `USER-MANUAL.md` 128·2060 · `docs/INSTALL.md` 94·104·147·208·333·343·348·458·630 · `docs/GUIDE-clean-reset-KR.md` 239·335·393 · `docs/RELEASE.md` 15 (15줄) | 유지 |
| 코드·경로 리터럴 | `docs/INSTALL.md` 299·358·423(case 식이 두 자리를 나란히) · `docs/GUIDE-clean-reset-KR.md` 243(`for A in /Applications/cysr.app /Applications/cys.app`) (4줄) | 유지 |
| 0건 | README 한/영 · SECURITY · NOTICE · CONTRIBUTING · ARCHITECTURE-AND-PHILOSOPHY · INSTALL-Windows-KR · GUIDE-empty-surface/fullauto-cycle/policy-json · `dist-win/README.md` · `docs/index.html` · `ui/index.html` · 오피스 화면 2파일 | — |

**이력·내부 문서**(무수정) = 25파일 101줄 113건.

| 묶음 | 파일 | 줄 | 왜 그대로인가 |
|---|---|---|---|
| `docs/plans/` | 2 | 40 | 그 날짜의 설계·계획 |
| `docs/update/`(HANDOFF-PUBLISH-DOCS·U1·U3·U4) | 4 | 20 | 인수인계 기록 |
| `docs/rebase-*` 보고 | 3 | 17 | 리베이스 보고(그 판의 실측) |
| `docs/legacy/RELEASE-upstream.md` | 1 | 4 | 원작자 레인 이력(비실행) |
| 릴리스 노트 1.0.1 · 0.2.2 · 0.14.43 | 3 | 3 | 그 판 시점의 기록(1.0.1 = 「이미 `cys.app` 으로 설치하신 분은」 = 옛 자리 서술) |
| `HANDOFF-*`(뿌리·docs) | 4 | 4 | 인수인계 기록 |
| `docs/DARWIN-UPDATER-LEGACY-LANE.md` | 1 | 3 | 1.0.2 → 1.1 옛 레인(「`cys.app` 그대로다」 가 주제) |
| `docs/fix-dock-ghost-tile-2026-07-20.md` | 1 | 3 | 날짜 박힌 수리 기록 |
| `docs/CONTROL_CENTER_DESIGN.md` | 1 | 2 | 2026-06-17 배포 기록 |
| `docs/FEEDBACK-MENU.md` · `docs/CYSR-BRAND-VERSION.md` | 2 | 2 | 그날 로컬 빌드 산출 경로 기록(`target/release/bundle/macos/cys.app`) |
| `docs/USAGE_OBSERVABILITY_PHASE2_PLAN.md` · superpowers spec · verdict-pane-title | 3 | 3 | 계획·판정 기록 |

PLAN 의 「35곳」 은 2026-10-07 publish-docs-118(`81b792db` · `docs/update/HANDOFF-PUBLISH-DOCS.md` §1 판독표)에서 이미 처리된 계수였다. 이번 실측의 현행형 잔존은 1줄이다.

### 새 줄 규칙(publicdocs 검사 1개 추가)

기존 「앱 이름 = cysr.app」 검사의 구멍 둘: ⑴ 대상이 README 링크 수집 11개뿐(`dist-win/README.md` · `docs/RELEASE.md` · README 가 링크하지 않는 GUIDE 3개를 안 본다) ⑵ 같은 줄에 `cysr.app` 만 있으면 통과(「받은 cysr.app 을 /Applications/cys.app 으로 옮깁니다」 가 초록).

- 대상 = 현행 안내 문서 19파일.
- 산문 줄(펜스 밖): `cys.app` 이 나오면 같은 줄에 옛 자리 표지(옛 · 이전 판/이름/자리/버전 · 0.14 · old · legacy · previous) 필수.
- 코드 줄(펜스 안): `cysr.app` 짝이 있거나 표지가 있어야 한다.
- 「이전」 맨 낱말은 표지가 아니다(「…로 이전합니다」 = 옮긴다). 브리프의 「이전」 을 좁힌 것 — master 수용(master#d902f510).
- 반례: 잡음 4 · 통과 4. 음성 대조(RELEASE.md:249 수정 전) = 17 / 1. 뮤턴트(실파일 심기 · 복원): README 현행형 1줄 = 16 / 2 · README 「받은 cysr.app 을 /Applications/cys.app 으로」 = 17 / 1(옛 검사는 통과) · dist-win/README 현행형 = 17 / 1(옛 검사 대상 밖) · 규칙 끔 = 17 / 1 · 복원 18 / 0.

## 2. RELEASE.md(②③) · 내부 절차 3문서(⑤)

② 정본 줄 `:12`(맥 자산 = 자체서명 zip 안 `cysr.app` 하나 · 공증 없음)·`:24`(후처리)와 모순되던 4곳:

1. 「발행 층위 훅」: draft 백업 DMG 2종 + 네이티브 DMG 에 `verify-gatekeeper-user-path.sh` → **배포 zip 2종 속 `.app` · `--lane self-signed`** · user-path 게이트는 DMG 전용이라 대상 아님(근거 = `scripts/release-postprocess.py` 머리 주석 5단계 · `MAC_LANE` 주석).
2. ⑦ DMG 봉투 축의 「왜 여기인가」: 후처리가 DMG 에 재실행 → 원작자 레인 = DMG · 우리 포크 = zip 속 `.app`(⑦ 축은 「대상 아님」 1줄).
3. IOReport 게이트 「보지 못하는 것」: 「공증된 DMG 의 데몬 … 아래 체크리스트의 별도 행」 → 그 행이 없다(`grep -n NPU docs/RELEASE.md` = 이 절 2줄뿐). 「이 게이트가 재지 않는다 — 실기 확인 몫」 으로.
4. 「비기술자 배포 전 게이트 체크리스트」 머리 아래 고아 3줄 삭제 — `29c29859` 가 원작자 레인 두 항목의 머리만 legacy 로 옮기고 둘째 항목의 이어지는 문단을 남겼다. 지운 원문은 커밋 `ae4a9a78` 메시지에 그대로 있다(머리 = `docs/legacy/RELEASE-upstream.md:189`).

`dist-win/README.md` = 고칠 줄 0(자산 이름 = `release-verify.py` `REQUIRED_ASSETS` · `*.wxs` 2개 추적 · `.gitignore` `dist-win/*.msi`·`*.zip`·`zip/` 전부 일치).

③ 옛 인앱 갱신 현행형 = **실측 3곳**(PLAN 계수 2곳과 다름 · 전부 `docs/RELEASE.md`):

1. §0-B 하한 계약 「인앱 업데이트가 제거 후 설치로 빠진다」 → 자동 갱신(데몬이 설치기를 `/S /P /UPDATE …` 로 실행 · `src/update/win_install.rs:22`).
2. 릴리스 전 체크리스트 「Windows 업데이트 시도 기록의 기준 시각 다시 쓰기 실기」 행(없는 단추 [본체 패치 설치] · 없는 기록 파일) → 「Windows 자동 갱신 실기」 행. 실기 상태 정본 = `docs/update/U2-FIELD-TESTS.md`(윈 W1~W4) · `docs/update/WIN-NSIS-0A-FIELD.md`. **실기 PASS 여부는 이 티켓이 재지 않았다.**
3. 「스마트 앱 컨트롤이 켜진 PC 의 업데이트 차단 알림」 → 자동 갱신 보류(게이트 N12 · `win_sac_on` · `src/update/gates.rs`).

⑤ 내부 절차 3문서(매니페스트 밖 — publicdocs 대상 아님 · 문구만):

- `docs/RELEASE-ROLLBACK.md` §5: 「앱 내 업데이트 확인」 서술에 「1.1.7 이하 설치본」 표지 + 1.1.8 현행 1문장. **맥 자산이 빠진 릴리스에서 1.1.8 자동 갱신 판정이 무엇으로 끝나는지는 재지 않았다**(문서에 「미확인」 이라 적었다 — 지어내지 않음).
- `docs/KEY-ROTATION.md` :9·:61·:82: 「지금은」 → 「작성 시점(2026-09-15 · 0.14.x)에는」 · 0.14.x 설치본의 단추 서술 두 줄에 「그 판의 Update · 1.1.8 부터 없음」 표지.
- `docs/WINDOWS-UPGRADE-ATOMICITY-CHECKLIST.md` P8: 「인앱 업데이터 경로」 → 「자동 갱신 경로(1.1.8~ · 1.1.7 까지 = 앱 안 갱신 단추 경로)」 + 결과 표 행 이름. **줄 수 523 유지**(§4 함정).

## 3. 파이썬 이름 일치 종료 6곳(④)

| 자리(기준 `e2532e05` 줄) | 옛 꼴 | 지금 |
|---|---|---|
| 하네스 `cmd_phoenix_p5_redelivery` :1273 · :1298 | 명령 문자열 `sleep 600` 일치 종료(머신 전역 · SIGKILL) | `_reap_harness_children()` — pid 장부만 · 재기동 전 `_note_harness_children()` 1줄 추가(s1 의 stub) |
| 하네스 `cmd_phoenix_p7_inherit` :1463 · :1491 | 같음 | 데몬 kill 전 `_note…` → kill 뒤 `_reap…` · teardown 뒤 `_reap…` |
| 하네스 `cmd_phoenix_p9_catastrophe` :1679 | 같음 | teardown 뒤 `_reap…` |
| `test_d1_dept_ready_probe.py` :84 `tearDown` | 임시 폴더 이름 일치 종료 | `cys-dept` 실행 4곳을 `_run()`(새 세션 = 새 프로세스 그룹 · 그룹 id 장부)으로 묶고 `os.killpg` 로 그 그룹만 |

새 도우미(하네스): `_child_ledger`(pid → `ps lstart` 원문) · `_proc_started` · `_note_harness_children`(격리 데몬의 현재 자손을 적는다 — 데몬을 죽이기 **전**에) · `_reap_harness_children`(시작 시각이 그대로인 pid 만 SIGKILL · 장부 비움 · 멱등). `teardown()` 이 처음에 적고 데몬 kill 뒤 끝낸다 — 그래서 teardown 을 거치는 모든 경로가 같은 정리를 받는다.

왜 장부인가: stub(`exec sleep 600`)은 PTY 자식이라 데몬과 프로세스 그룹이 다르다(`_kill_pg` 가 닿지 않는다). 데몬이 죽으면 부모체인이 끊겨 그 뒤에는 「우리 것」 을 가려낼 길이 이름뿐이다 — 그래서 죽이기 전에 적는다.

검체(boot-health · W6 · ci-branch 전량 레인 자동 편입 — `H-CI-COVER-1` 「등재 168종 · 미실행 0 · 유령 ID 0」):

- **H-PY-PKILL-1**(정적 · AST): 팩 `*.py` + 레포 `scripts/*.py` 에서 ⑴ argv 리터럴(리스트·튜플에 실행 파일 이름 pkill + `-f`·묶음 `-9f`) ⑵ 독스트링이 아닌 문자열 상수의 셸 꼴 줄(`pkill … -f`). 주석·독스트링은 세지 않는다. 러너 파일 자신은 ⑴ 만(합성 반례 문자열을 들고 있다). 합성 양성 8 / 8 · 음성 8 / 8. 못 보는 것: 조각내어 붙인 argv · 변수로 받은 실행 파일 이름.
- **H-PY-PKILL-2**(행동 · posix): 가짜 격리 데몬(자식 = 다른 세션의 `sleep 600`)과 **자손이 아닌** `sleep 600` 을 하나 띄우고 `teardown()` → stub 사망 · 바깥 것 생존 · 이름 일치 도구 호출 0 · 장부 비움 · 재호출 무동작. 하네스는 자식 프로세스에서 임포트한다(임포트가 종료 훅·신호 처리기를 건다). **안전 그물**: 시험 PATH 맨 앞의 가짜 이름 일치 도구가 호출을 적고 이 시험이 띄운 두 pid 에만 닿는다 — 옛 꼴이 되살아나도 머신의 다른 프로세스는 무접촉.

뮤턴트(실파일 심기 → 두 검체 실행 → 복원 · 전부 안전 그물 안):

| 뮤턴트 | H-PY-PKILL-1 | H-PY-PKILL-2 |
|---|---|---|
| A teardown 의 장부 정리를 옛 이름 일치 줄로 복원 | FAIL(`javis_phoenix_harness.py:501`) | FAIL — 「바깥의 sleep 600 이 죽었다」 · 가짜 도구 호출 기록 `-9 -f sleep 600` |
| B 드릴 호출 자리 1곳에 옛 줄 복원 | FAIL(`:1318`) | PASS(드릴 함수는 실 데몬이 있어야 돈다 — 이 검체 밖) |
| C teardown 에서 장부 적기 제거 | PASS | FAIL(stub 생존) |
| D teardown 에서 장부 정리 제거 | PASS | FAIL(stub 생존) |
| E 장부가 자손 아닌 pid 까지 적음 | PASS | FAIL — 「바깥의 sleep 600 이 죽었다」 |
| F d1 뒷정리 옛 줄 복원(정적만 · 실행 안 함) | FAIL(`test_d1_dept_ready_probe.py:107`) | PASS |
| 복원 뒤 | PASS | PASS |

## 4. 게이트

실행 조건: 맥 · 이 작업 트리 · 좌석 `CYS_*` env 전부 제거 · 단계마다 새 임시 HOME(phoenix 3종만 같은 HOME 순차) · 순차 1회.
1차 = ①②③ 뒤 머리 `3bfefec8` · 2차 = ④⑤ 내용(커밋 `a6401ee1` 과 같은 트리).

| 단계 | 1차(`3bfefec8`) | 2차(④⑤ 뒤) |
|---|---|---|
| publicdocs(`bun test src/publicdocs.test.ts`) | 18 / 0 · expect 296(기준 17 / 0 · 262) | 18 / 0 · expect 296 |
| ui `bun test` 전체 | 2918 pass / 85 skip / 0 fail(3003 시험 · 92 파일 · 기준 2917 + 새 시험 1) | 같음 |
| tsc(`typescript@7.0.2` · `tsconfig.check.json`) | rc 0 · 오류 0(음성 대조: 타입 오류 1줄 심기 = rc 1 · TS2322) | rc 0 · 오류 0 |
| `gen_ceo_template.py --check` | GREEN(드리프트 0 · 95201 bytes) | 같음 |
| doc-contract(`test_bootv2_doc_contract.py`) | rc 0 | rc 0 |
| pins(`test_content_pins_parity.py`) | rc 0 | rc 0 |
| cysd `manual_`(설명서 include_str 핀) | 6 / 0(2602 걸러짐) | 6 / 0(최종 머리에서 다시 잼) |
| secret-scan `--all` | clean(1656 파일) | clean(1656 파일) · 이 문서를 커밋한 최종 머리 = clean(1657 파일) |
| `scan-pack-secrets.sh` | — | OK |
| phoenix 3종 같은 HOME 순차 | — | c6 7 / 7 · e2e_replacement 7 / 7 · f1 63 / 63 · 그 HOME 에 `.cys` 0 |
| `test_d1_dept_ready_probe.py` | — | 11 / 0(81.9초) |
| boot-health 전량 | — | **165** PASS / 2 FAIL / 1 SKIP — 전임(`HANDOFF-1110-merge` §1) 163 PASS 와의 차이 = 새 검체 2(`H-PY-PKILL-1`·`H-PY-PKILL-2`) · FAIL 2 = `H-CLT-1`·`H-CLT-2`(이 맥 환경성 · 전임과 같은 두 id) · SKIP = `H-WIN-11` |
| `H-CI-COVER-1` | — | PASS 「등재 168종 · 미실행 0 · 유령 ID 0」 |
| `test_pack_syntax_warnings.py` | — | rc 0(boot-health 잔재 폴더를 지운 뒤 — §5) |

실 데몬 드릴 손 실행(바꾼 호출 자리 · 바깥에 `sleep 600` 1개를 띄워 두고):

| 드릴 | 내 트리 | 기준 `e2532e05` 트리(이름 일치 도구를 가짜로 받음) |
|---|---|---|
| `phoenix-p9-catastrophe` | rc 0 · `p9_pass` true | (돌리지 않음) |
| `phoenix-p5-redelivery` | rc 1 · `queue_empty_after` false · `delivered_to_new_worker` false | rc 1 · **결과 JSON 전문 동일** |
| `phoenix-p7-inherit` | rc 1 · `explicit_tombstone_removes` false | rc 1 · **결과 JSON 전문 동일** |

세 드릴 뒤 바깥 `sleep 600` 생존 · 남은 stub 0(`ps` 관측 = 바깥 것 1개뿐). p5·p7 의 rc 1 은 이 변경 이전부터의 드릴 본문 실패다(§6).

실행하지 않은 것: Rust 전량(`--lib`·`--bin cys`·`--bin cysd` 전수·`-p cys-app` — Rust 변경 0) · 윈 컴파일·실기 · 팩 시험 전수(바꾼 파일을 읽는 것만 돌림).

## 5. 함정(다음 사람에게)

- **뮤턴트로 옛 이름 일치 종료를 되살릴 때는 진짜 도구가 불리지 않게 하라.** 되살린 줄이 실행되면 그 순간 머신의 같은 이름 프로세스가 전부 죽는다(이 티켓이 없애려던 바로 그 사고). H-PY-PKILL-2 는 PATH 맨 앞의 가짜 도구로 받는다. 절대 경로(`/usr/bin/…`)로 부르는 꼴은 가짜를 지나치므로 **정적 검체로만** 재고 실행하지 않는다(뮤턴트 F).
- **하네스를 러너 프로세스에 임포트하지 마라.** `javis_phoenix_harness.py` 는 임포트 시 `atexit` 에 `teardown` 을 걸고 SIGINT·SIGTERM 처리기를 바꾼다. 검체는 자식 `python -c` 에서 임포트한다.
- **`docs/WINDOWS-UPGRADE-ATOMICITY-CHECKLIST.md` 는 줄 번호로 참조된다**(`javis_preflight.py:7199` 의 `:140`). 고칠 때 줄 수를 유지하거나 참조를 함께 고친다. `scripts/tests/nsis-hook-compile/run.sh` N6 은 이 문서에 나오는 `CYS_…`·`cys_x_y` 꼴 낱말이 훅에 실재하는지 본다 — 그런 꼴의 새 낱말을 적으면 적색.
- **`bun x tsc` 는 `typescript` 가 아니다.** `ui/node_modules` 에 typescript 가 없으면 `bun x tsc` 는 이름이 `tsc` 인 다른 패키지를 받아 rc 0 으로 끝난다(거짓 초록). `bun x --package typescript@7.0.2 tsc -p tsconfig.check.json` 으로 부르고, 타입 오류 1줄을 심어 rc 1 이 나오는지 한 번 본다.
- **이 좌석의 PATH 에는 bun·cargo 가 없다.** `~/.bun/bin` · `~/.cargo/bin` 을 앞에 붙인다. 격리 HOME 으로 cargo 를 부를 때는 `CARGO_HOME`·`RUSTUP_HOME` 을 실 홈의 것으로 지정한다(도구 읽기만).
- **빌드 자리·ui 의존 모듈**: 같은 머리의 작업 트리(`~/axdev/.wt/cys-1110-upstream`)에서 `cp -c -R`(APFS 복제 · 원본 쓰기 0)로 `target/debug` · `ui/node_modules` 를 가져오면 `cargo test --bin cysd manual_` 이 웜으로 돈다(둘 다 추적 제외).
- **하네스 드릴(p5·p7·p9)을 격리 HOME 에서 돌리면 그 HOME 에 cysd 1개가 남는다.** 드릴이 「라이브 무접촉」 을 재려고 부르는 `live_surfaces()`(= 소켓 지정 없는 `cys list`)가 빈 HOME 의 기본 소켓에 데몬을 자동 기동하고, `teardown()` 은 격리 폴더에 묶인 데몬만 끝낸다. 기준 트리도 같다(이번 손 실행 2회에서 각 1개 · `lsof` 로 내 임시 HOME 에 묶인 것을 확인하고 pid 로 종료). c6·e2e·f1 시험은 남기지 않는다(그 HOME 은 비어 있었다).
- **py_compile 은 `cysjavis-pack/bin/__pycache__` 를 만든다**(추적 제외지만 봉인 시험이 오염으로 본다) — 지운다. 팩 시험은 `PYTHONDONTWRITEBYTECODE=1` 로 돌린다.

## 6. 남은 일 · 범위 밖 관찰(무수정)

- `docs/RELEASE-ROLLBACK.md` §5 는 「맥이 빠진 릴리스(2026-09-09 현재)」 가 전제다. 지금 발행은 맥 zip 2종을 손으로 올리므로(RELEASE.md 순서 4) 절 전체가 옛 전제일 수 있다 — 이 티켓은 인앱 갱신 문장만 고쳤다.
- `docs/RELEASE.md` §1 「맥 CI 레그 게이트」 본문은 DMG·stapler·공증 실측(v0.14.19 · v0.14.29)을 그대로 들고 있다. 절 머리와 `:6` 이 「잠복 레그 기록」 이라 밝혀 두어 손대지 않았다.
- `docs/RELEASE.md:182` 「공증까지 마친 build 3잡」(v0.14.39 사고 경위) = 날짜 박힌 경위라 유지.
- 하네스의 `p5`·`p7`·`p9-catastrophe` 드릴은 어느 시험·CI 레인도 부르지 않는다(`git grep` = 하네스 파일 자신뿐). 이번에는 손으로 1회씩 돌렸다(§4). **`phoenix-p5-redelivery`(재기동 뒤 큐 재배달 미도달)와 `phoenix-p7-inherit`(명시 폐역이 roster 에서 안 빠짐)는 기준 트리에서도 rc 1 이다** — 드릴이 낡았는지 제품 회귀인지는 가리지 않았다(별 티켓 후보).
- 윈도우: H-PY-PKILL-2 는 posix 전용(SKIP). 하네스의 윈도우 종료 경로는 이 티켓 범위 밖.

## 7. 재현 명령

```bash
ISO() {  # 좌석 CYS_* env 제거 · 새 임시 HOME · 도구는 실 홈의 것을 읽기만
  local a=(); while IFS= read -r n; do a+=(-u "$n"); done < <(env | grep -o '^CYS_[A-Z0-9_]*')
  env "${a[@]}" -u CLAUDE_CONFIG_DIR HOME="$(mktemp -d)" CARGO_HOME=/Users/$USER/.cargo RUSTUP_HOME=/Users/$USER/.rustup \
      PATH="/Users/$USER/.bun/bin:/Users/$USER/.cargo/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin" PYTHONDONTWRITEBYTECODE=1 "$@"; }
( cd ui && ISO bun test src/publicdocs.test.ts )                                    # 18 / 0 · expect 296
( cd ui && ISO bun test )                                                           # 2918 pass / 85 skip / 0 fail
( cd ui && ISO bun x --package typescript@7.0.2 tsc -p tsconfig.check.json )        # rc 0
( cd cysjavis-pack/bin/tests && ISO python3 run_bootstrap_health.py --only H-SH-PKILL-1,H-PY-PKILL-1,H-PY-PKILL-2,H-CI-COVER-1 )
( cd cysjavis-pack/bin/tests && ISO python3 test_d1_dept_ready_probe.py )
( cd cysjavis-pack/bin/tests && ISO sh -c 'python3 test_phoenix_c6_reap.py; python3 test_phoenix_e2e_replacement.py; python3 test_phoenix_f1_production_path.py; ls -A "$HOME"' )
ISO python3 scripts/gen_ceo_template.py --check
ISO bash scripts/secret-scan.sh --all
ISO cargo test --bin cysd manual_                                                   # 6 / 0
```
