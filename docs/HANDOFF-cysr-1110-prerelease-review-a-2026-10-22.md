# HANDOFF — cysr-1110-prerelease-review-a (1.1.10 발행 전 정밀 검토 · 2026-10-22)

- 좌석: worker@surface:1551 · 가지 `fix/1110-prerelease-review` ← `1c2f3a14`(rel/1.1.10 · 판번 1.1.9 · 태그 전)
- 브리프: master spawn 경로 02:43(원장 `kind:brief` · 본문 sha256 `3f101ea8…` = 브리프 파일 rstrip 해시 일치 실측)
- 범위: `git log --first-parent v1.1.9..rel/1.1.10` 27커밋 중 원작자 병합 `ba38b6aa` 를 뺀 26커밋의 diff(원작자 코드 제외)
- push · 태그 · 판번 · 설치 · 발행 = 0

## 1. 방법

1. 읽기 검토 4갈래 병렬(하위 에이전트 · 읽기 전용 · 기존 시험만 실행 허용)
   - A = winqueue `bf3e7666` + 큐 폐기 알림 연결 `7bea2400`
   - B = minor `7b983659` · backlog `51571f59` · 편입 후속 `eea89fca`·`45939c8e`·`d8e28331`·`8c2e1a24`
   - C = trash-harden `19af40c4`
   - D = popfont `51171ad5` · menu-top-row `0628356c` · 편입 후속 `234fc129`·`2b2179b7` · release-prep `76e1eda5` · refresh-feed `fb386c49` · 지침 표기 `e22af6e3`
2. 지적마다 직접 코드 재확인 → 확신도 상·중은 재현 시험 먼저(빨강 실측) → 수리 → 녹 → 뮤턴트 1.
3. 이미 한 검토(codex 1R vendor B1·M2 · trash-harden 4R ACCEPT · 통합 시험 전건 녹)는 다시 하지 않았다.

## 2. 수리 3건(커밋 · 각각 빨강 → 녹 → 뮤턴트 빨강 실측)

| # | 커밋 | 무엇이 틀렸나 | 사용자가 언제 겪나 | 시험 |
|---|---|---|---|---|
| R1 | `b75d8b25` | 윈 GUI 가 대체화면(전체화면 TUI) pane 의 휠을 PgUp/PgDn 으로 번역해 human=true 로 보내는데, winqueue 축1 은 미제출 **계수**에서만 뺐고 `surface.send_text` 처리기(`src/bin/cysd/handlers.rs` 6362 부근)는 휠마다 `last_human_input` 을 찍었다 → 그 pane 의 `--queued` 배달이 **마지막 휠 뒤 30초**(`queue_human_quiet_secs` · `governance.rs:13787` `human_typing`)까지 보류 · 노드의 제출 Return 은 `typing_guard` 로 거부. 맥의 같은 스크롤은 SGR 마우스 보고라 A9 로 면제(윈만 다름). winqueue HANDOFF §8 은 「3초 직접 send 보류」로만 적어 큐 30초 보류를 빠뜨렸다. | 윈 · `/tui fullscreen` 좌석을 오너가 스크롤해 읽는 동안 master 의 `--queued` 지시가 안 들어간다(스크롤을 멈춘 뒤 30초) | `handlers::tests::alt_screen_page_scroll_wheel_does_not_arm_typing_guard` — 실 대체화면 좌석(`printf '\033[?1049h'` · 에코 끔). 원 코드 = 빨강 · 뮤턴트(대체화면 조건 제거) = 빨강(본 화면 대조군) |
| R2 | `aec4972c` | preflight 선택 도구 ②: 부트 ⓪ 표준 호출(`--fix` · `--allow-irreversible` 없음)은 **구버전 korean-law · 판독불가 · 불완전 harness-creator 클론**에서도 「비가역 변경(…) 보류」 WARN 행을 세운다. 이 행을 부재 문구 머리로만 판정해 「선택 · 없음」 INFO 로 덮었다 → 같은 점검에 「없음」 과 「구버전/불완전」 이 함께 뜸(② 가 고치려던 혼동 그대로). | korean-law 0.9.1 처럼 옛 판이 깔린 기기에서 부트 사전 점검이 「없음」 과 「구버전」 을 동시에 말한다(READY 등급은 무영향 — WARN 행이 따로 남음) | `test_javis_counsel.OptionalToolGrade.test_fix_mode_hold_row_not_absent_when_installed`(빨강 → 녹) + `test_fix_mode_absent_stays_info`(부재는 종전대로 INFO). 뮤턴트(꼬리 판정 제거) = 빨강 |
| R3 | `ac5d0ac5` | `cys factory-reset` 계획 화면이 「격리본은 약 14일 뒤 정리 작업에서 소거될 수 있습니다(직접 지우려면 rm -rf)」 라고 말했다 — 1.1.10 은 자동 소거가 없고(설명서 「저절로 지워지지 않습니다」) 지우는 길은 휴지통이다. 문구만 고침(흐름 무변경 · 설명서 「완전 초기화」 절과 같은 말). | 완전 초기화 미리보기를 보는 모든 사용자(이제 cys pane 안에서도 `--plan` 이 돈다) | `tests::factory_reset_plan_does_not_promise_auto_purge`(소스 핀 · 원 문구에서 빨강) |

수리 방식 요약
- R1: `let page_scroll = surface.alt_screen ∧ is_page_scroll_chunk(text)` → `human ∧ ¬page_scroll ∧ ¬autoreply` 일 때만 가드 갱신. 조건은 계수 면제(`state.rs` 축1)와 같다 · 본 화면 PgUp · 글자 섞인 청크는 종전대로.
- R2: `may_mutate(..., present=None)` 인자 추가 — 대상이 이미 있으면 보류 행 꼬리에 「 · 현 설치: <판 | 경로 불완전>」 · `_optional_tool_grade` 는 그 꼬리가 있으면 부재로 보지 않는다. 호출 2곳(C21 · C24)만 넘긴다.
- R3: 문구 1줄 + 근거 주석 1줄.

## 3. 지적표 전체(수리 안 한 것 포함)

확신도: 상/중/하 · 판정: 수리 / 불성립 / 다음 판 후보

| 갈래 | 위치(HEAD) | 내용 | 확신도 | 판정 |
|---|---|---|---|---|
| A | handlers.rs `send_text` | 윈 대체화면 휠이 타이핑 가드를 찍어 큐 30초 보류 | 중상 | **수리 R1** |
| A | governance.rs:6365 · handlers.rs:363 | `owner_close=true` = 「reap 아닌 모든 닫기」(CLI `cys close-surface`·GUI 자동 닫기 포함) → 에이전트가 닫아도 「대기 중이던 지시 N건을 버렸습니다」 토스트 | 중 | **불성립** — 토스트 문구는 닫은 주체를 단정하지 않고 지시가 버려진 것은 사실(정보로서 맞음). 좌석 번호를 문구에 싣는 것은 다음 판 후보 |
| A | ui/src/placeholderclose.ts:55 | 윈 자리표 닫기가 xterm `isWrapped` 에 기댐 — ConPTY 가 리사이즈 뒤 줄 단위로 다시 찍으면 88자 PS 안내 줄이 2~3줄로 세어져 상한 4 초과 → 자리표 안 닫힘(안전 방향 실패) | 하 | 다음 판 후보 · **윈 실기 확인점**(88열 미만으로 쪼갠 뒤 `placeholderScreenLines` 기록) |
| A | governance.rs:10010 | `layout_why` 진단이 실제 틱 판정과 다른 마커 선택(codex `»` 꼬리) · 자리표+아래 선택행 꼴에서 `marker_row_text` 오표기 | 하중 | 다음 판 후보(진단 전용 · 배달 판정 무영향) |
| A | state.rs:7967 | `parked_overflow` 묘비의 `surface` 가 주차 출처가 아니라 나가는 좌석 | 하 | 다음 판 후보(소비자 0 — `javis_snapshot.py` 는 배달 계수에서 제외만) |
| A | cys.rs:11152 | factory-reset 계획 화면의 14일 자동 소거·rm -rf 안내 | 상 | **수리 R3** |
| B | javis_preflight.py:74-75 | 구버전·불완전에서도 보류 행이 「없음」 INFO | 상(재현) | **수리 R2** |
| B | cys-dept:365-369 | `CYS_TRASH_STAMP` 검증이 teardown 뒤(`dept_purge_state` 안) — 나쁜 값이면 반쯤 된 down | 상(순서) · 하(도달) | 다음 판 후보 — 이 변수는 시험만 쓴다(javis_org 경로는 먼저 검증) |
| B | javis_org.py:708 | 스탬프 검증 `str.isdigit()` 가 유니코드 숫자(`²`·`٣`) 통과 · bash 는 거부 · 빈 값 처리도 갈림 | 중(기제) · 하(도달) | 다음 판 후보 — `re.fullmatch(r"[0-9]+", ts)` 1줄 · 시험 전용 변수 |
| B | scripts/tests/test_update_publish.py:76-81 | hdiutil detach 2회 실패 뒤 `rmtree` 가 마운트된 볼륨 안으로 들어감 · 재시도에 `-force` 없음 | 중 | 다음 판 후보 — 시험 하네스 전용(사용자 경로 아님) |
| B | accounts.rs:1455-1466 | 프로필 통째 별칭(`~/.claude-acctN → ~/.claude`)이면 첫 일치 프로필로 귀속 | 하 | 다음 판 후보 — 종전 코드도 같은 순서(이번 회귀 아님) |
| C | src-tauri/src/main.rs:5142 · factory_reset.rs:2050 | 휴지통 이름 하나 지울 때 화면은 완전 NFC · 네이티브는 한글 조합만 → 분해형 라틴(`é`) 이름은 화면 통과·네이티브 `phrase_mismatch` 반복(여럿 고르면 「삭제 N」 으로 우회) | 하중 | 다음 판 후보 — 코드 주석에 「한계 · 지우지 않는 쪽 실패」 로 이미 기록 · 부서명 대부분 ASCII · 윈은 삭제 꺼짐 |
| C | src/dirat.rs:137-164 | 하위 객체 동시 소실(ENOENT)이 오류로 전파 → `partial` · `.deleting-*` 잔여 · 잔여는 목록에서 `deletable:false` 인데 안내는 「새 미리보기」 | 하 | 다음 판 후보 — 휴지통 설계 판단(잔여 삭제 경로 vs 문구) |
| C | trash.rs:1741 | `producer_active` 거부 원장의 경계 경로가 `<entry>/.producer`(새 생산자는 `.producer-<pid>`) | 상(표기만) | 다음 판 후보 — 판정 무영향 |
| C | trash.rs:1715-1717 | 휴지통 뿌리가 그냥 지워졌을 때도 「다른 폴더·링크로 바뀜」 문구 | 중(문구) | 다음 판 후보 |
| C | ui/src/main.ts:1965 · src-tauri main.rs:5175 | 확인 토큰 미발급(맵 mutex 오염)이면 「삭제」 가 무소식 종료 | 하 | 다음 판 후보 — 정상 흐름 도달 곤란 |
| D | .github/workflows/refresh-feed.yml:110-118 | 봉투 읽기 실패(403·5xx·DNS)를 404 와 같이 「게시된 봉투 없음」 notice + exit 0 로 처리 → 읽기 호스트가 막히면 주간 갱신이 녹색으로 아무것도 안 하고 봉투가 만료될 수 있음 | 중 | 다음 판 후보 — **main 가지 워크플로**(rel/1.1.10 수정은 효과 없음) · fb386c49 이전부터 있던 결함. 실측: 10-19 정기 실행은 cysr 두 레그 정상 갱신 · 404 는 실제 미게시 레그(agora-client/next)뿐 → 지금 사고 아님 |
| D | release.yml · pack-release.yml | 팩 하한 1.1.10 → 발행 창(체크리스트 3-8 ~ 새 바이너리 수신) 동안 1.1.8/1.1.9 기기가 갱신 확인마다 `update.binary_too_old` 상담 신호 누적(중복 제거 없음 · 2MB 상한) · 판번 안 올린 가지의 수동 release.yml 실행은 「Verify signed pack」 단계 적 | 하중 | 다음 판 후보 — 깨지는 것 없음(소음) · 태그 실행은 판번을 먼저 올리므로 녹 |
| D | ui/src/style.css:506 | 메뉴 크기 80% 에서 화면 설정 팝오버 글자 8px · 되돌릴 조절이 팝오버 안 | 하 | 다음 판 후보 — 박사님 「절반」 지시 결과 · 바닥 `max(9px, …)` 안 |
| D | #topbar | 상담소·아고라 상단 이동으로 윈(Segoe·맑은 고딕) 좁은 폭 넘침·가로 스크롤바 가림 위험 | 하 | WIN-FIELD MENU-1~3 이 이미 다룸 — 실기에서 실제로 돌릴 것 |

## 4. 갈래별 「정상으로 판정한 것」(재검토 중복 방지)

- A: `is_page_scroll_chunk`(4바이트 배수 · PgUp/PgDn 만 · 수식키·화살표·SS3 거부) · `apply_pending_input` 조기 반환이 계수·사람 몫·세대·거울·Esc 표지를 안 바꿈 · 데몬 `alt_screen` = reader 파서 · 락 중첩 없음 · 묘비 이중 기록 없음 · `queue.dropped` 페이로드 필드명과 UI 소비 일치 · `daemonToast` 가 ALERTS_QUIET 따름 · `verify_denied` 판독 · `caller_env_keeps_config_dir_on` 윈 정규화 · `factory-reset --plan` 이 데몬을 안 건드림.
- B: ④ `seat_claimable` 조기 반환 = 기존 판정과 전 조합 동일 · ① `--rcfile` 가드 · ③ PowerShell 핀 · ⑥ dlls-copied 판정 · ⑦ 닫힌 부서 잔재(BOM·비객체 depts 포함) · accounts.rs 공유 projects 심링크 귀속(타 프로필로 향한 링크는 거부 = fail-closed) · pack.rs `hooks_rel_confined`(`..`·루트·드라이브·심링크 성분·윈 정션) · javis_org 이름 검증 · NOWIN · s5 글자 경계.
- C: 윈 = `dirat` 은 `#[cfg(unix)]` · 윈 대체 경로 신원 (0,0) 일관 · 삭제 기본 꺼짐(교차 컴파일은 libsqlite3-sys C 빌드로 막혀 미실측 → 윈 CI·실기 확인) · 맥 `$INODE64` 링크 이름 · 한글·긴 경로·깊은 트리 · 읽기 전용 파일 · 생산자 표식 1.1.9 호환 · 1.1.9 휴지통 항목 1.1.10 에서 미리보기·삭제 가능 · 1.1.9 manifest(`to_rel` 없음) 복구 폴백 · M4 부모 신원 오탐 없음(firmlink·$HOME 심링크) · 확인 모달 취소·연타·늦은 폴링 · 새 거부 코드 재전송 허용.
- D: 옮긴 버튼 id·핸들러 · 화면 설정 목록 자동 편입 · 1.1.9 저장 배치에 새 버튼 끼우기 · 팝오버 폭 · 조용 모드 전 호출부 방향 · 휴지통 토스트 서명 · release.yml 설치 안내 출력 · 팩 하한 두 레인 값과 핀 · `requires.min_binary_for_pack` 은 형식만 검사 · `vars` 문맥 · 지침 표기 커밋은 `gen_ceo_template --check`·`gen_released_directive_hashes --check` 녹.

## 5. 시험 전건(이 가지 최종 트리)

맥 · 2026-10-22 03:1x~03:5x · 수리 3커밋(`aec4972c`·`b75d8b25`·`ac5d0ac5`) 반영 트리.

| 묶음 | 결과 |
|---|---|
| `cargo test --lib` | 1100 통과 · 0 실패 · 2 ignored |
| `cargo test --bin cys` | 627 통과(통합 626 + 신규 1) · 0 실패 |
| `cargo test --bin cysd` | 2699 통과(통합 2698 + 신규 1) · 0 실패 · 9 ignored |
| ui `bun test` / `tsc -p tsconfig.check.json` | 3173 통과 · 0 실패 · 85 skip / rc 0 |
| 팩 py `test_*.py` 189 파일 개별 실행 | 185 녹 · 적 4 = 전부 **기준선 `1c2f3a14` 임시 작업트리에서 같은 적**(아래) |
| `test_javis_counsel` | 78 OK(신규 2 포함) |
| `test_verify_gate` · `test_preflight_phase1_checks` | 격리 env(`JAVIS_ROOT`·`CYS_PROBE_RUNS`)로 OK |
| 앱 `src-tauri` cargo test | 미실행 — 이번 수리는 src-tauri 무변경 |

팩 적 4(기준선 대조):
- `test_agora_known_authentic` 3 — `CYS_AGORA_ZIP_DIR 없음(제작 맥 전용 시험)` · 적 이름 집합 해시 HEAD = 기준선.
- `test_dept_team_token` 18 — 기준선 18(통합 HANDOFF 와 같은 `team_flow_dormant`).
- `test_dept_name_guard` 1 — `test_create_spawn_loser_preserves_live_winner`(경쟁 승자 pong 타이밍) · 기준선 3회 중 2회 같은 적 · 단독 재실행은 녹/적 번갈아 = 플레이크(부하 평균 2.5~3.6).
- `test_verify_gate` — 격리 env 없이 돌린 일괄 실행의 REFUSE · 격리 env 로 OK.

## 6. 남은 것·한계(정직)

- R1 은 윈 실기 0 — 맥에서 실 대체화면 좌석으로 같은 바이트·같은 처리기 경로를 쟀다. 윈 실기 확인점: fullscreen 좌석 스크롤 중 `--queued` 1건이 스크롤을 멈추자마자(30초 대기 없이) 들어가는지.
- C 의 윈 교차 컴파일은 하위 에이전트 환경에서 실측 못 함(정적 cfg 전수 확인만).
- 내가 코드·실행으로 직접 재확인한 지적 = A 휠 가드(R1) · A owner_close · A 14일 문구(R3) · B preflight(R2) · C NFC 한계(코드 주석 실재) · D refresh-feed(워크플로 본문 + 10-19 실행 로그). 그 밖의 「다음 판 후보」 행과 §4 「정상 판정」 목록은 하위 에이전트 보고를 옮긴 것이다(파일:줄은 에이전트가 HEAD 에서 읽은 값 · 내가 전부 재확인하지는 않음 — 다음 판 착수 시 재측정).

## 7. [덧붙임] rel/1.1.10 병합 때 R3 처리(TICKET=cysr-1110-review-merge · master#4a059fc9)

- review-b(`d9def91a`·`416c06da`)가 같은 줄을 먼저 고쳤다 — 맥 갈래 = 앱 정본 `TRASH_KEEP_NOTICE`(「그대로 보관 — 스스로 지우지 않음 · 삭제는 Control Center 휴지통」) · 윈 갈래(`trash_delete_supported()` 거짓 · Q1=B) = 「지난 판처럼 약 14일이 지나면 저절로 정리」.
- 병합 해소 = review-b 블록 채택(`cys.rs` 결과 = review-b 판 바이트 동일). R3 의 뜻(맥 = 자동 소거 없음 · 휴지통에서 지움)은 정본 문장이 이미 말한다. R3 문장을 맥 갈래에 넣으면 review-b 시험(CLI 맥 갈래 = 앱 정본 글자 그대로)이 깨지고 CLI·앱 문장이 갈리므로 넣지 않았다.
- R3 시험 `factory_reset_plan_does_not_promise_auto_purge` 는 걷어냈다 — review-b `factory_reset_trash_notice_tests` 와 겹치고, 「저절로 지워지지 않습니다」 요구가 윈 갈래 문장과 맞지 않는다.
- ⚠ 위 §2 R3 행·§3 의 「1.1.10 은 자동 소거가 없다」 서술은 **맥 한정**이다(윈도우 1.1.10 = 14일 정리 유지 · Q1=B).
