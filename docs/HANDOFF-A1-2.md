# HANDOFF — TICKET=dept-impl-A1-2 (대화로 부서 만들기 · 구현)

- 작성: worker@surface:818 · 2026-09-18 21:1x · 매듭 사유 = master 매듭 예약(`master#50b5645e` · CTX 51.3% jsonl 라이브 실측)
- 워크트리 `~/axdev/.wt/cys-v110-dept` · 브랜치 `fix/v110-dept`
- ★**후임 최소 읽기 범위 = 이 파일 하나.** 설계 정본(DESIGN-v2.1)·적대 2R 을 다시 읽지 않는다 — 필요한 줄은 아래와 `docs/DESIGN-dept-by-conversation.md`(CLI 계약 · 이 티켓 산출물)에 옮겨 두었다.

## 0. 후임이 가장 먼저 할 일(순서대로)

1. **agy 1R REVISE F1 수리(high · 타당 — 내가 확인함)**: 틱이 요청을 집행하다 예외(예: `javis_org` I/O 오류 · `Popen` 실패 · `_close_step` 의 `subprocess.run` OSError)로 죽으면 요청이 `confirmed` 로 남아 **매분 같은 요청에서 다시 죽는다**(나머지 요청 전부 영구 정지 · 매분 schedule.error). 처방: `cmd_tick` 안의 `_create_step(r, …)` / `_close_step(r)` 호출을 각각 `try/except Exception as e:` 로 감싸 `_fail(r, "crash:%s" % type(e).__name__)` → `save_req(r)` → `_notify(r, "부서결과")`. 시험 1건(가짜 cys-dept 경로를 없는 파일로 → 1틱 뒤 `failed(crash:…)` · 2틱째 rc 0) + 뮤턴트 1종(try 제거 → 적색)을 `tests/test_dept_request.py`·`tests/mut_dept_request.py` 에 추가.
   - 원문: `~/.cys/pack/round/_reviews/dept-A1-2/agy-r1.out`
2. **codex 1R 결과 회수**: 매듭 시점에 아직 실행 중이었다. 출력 = `/private/tmp/claude-501/-Users-oogisoogi-axdev--wt-cys-v110-dept/ff1bba40-47bf-48f0-afc8-3eafa7d4f9e3/scratchpad/codex-r1.out`(끝에 `RC=`가 붙으면 완료). 중간 산문에서 codex 가 짚고 있던 후보 5개(확정 아님): ⑴발화 원문 보관이 7일로 제한되지 않는 경로 ⑵생성 도중 틱이 죽으면 살아 있는 자식을 두고 재호출할 수 있는 경로 ⑶번호 재사용 판정 ⑷요청 파일(request.json) 동시 저장 ⑸재시도 시 검증 누락. 파일이 없거나 비어 있으면 같은 의뢰문으로 다시 돌린다: `~/.cys/pack/round/_reviews/dept-A1-2/review-prompt-r1.txt`(`unset NODE_OPTIONS; codex exec -s read-only --skip-git-repo-check -C <빈폴더> "$(cat …)"` — 10분을 넘기니 백그라운드로).
3. 수리분 커밋 → 테스트·뮤턴트·cargo 재실행(§3 명령) → agy/codex 2R(같은 의뢰문 + 「1R 지적 반영 확인」) → 【단계완료】.
4. T0 감시 결과 회수(§5).

## 1. 커밋

| 커밋 | 내용 |
|---|---|
| `095de5ba` | 도구·시험 27건·뮤턴트 하네스·schedule.rs 틱·factory_reset·CI 3레인 등재·CLI 계약 문서 |
| (이 HANDOFF 커밋) | 창 숨김 계약 수리(Popen `creationflags` 명시) · 뮤턴트 M15 재조준 · HANDOFF |

## 2. 브리프 항목 ↔ 코드 위치(전부 `cysjavis-pack/bin/javis_dept_request.py`)

| 브리프·2R 항목 | 상태 | 위치(함수) |
|---|---|---|
| 치명① `.pending` lost-update | 완료·뮤턴트 M1 킬 | `cmd_confirm`(request.json 먼저 → 표지) · `_pending_claim`(스캔 전 rename) · `_pending_finalize`(지우지 않음) · 자가복구 `_sweep` 말미 |
| 치명② 청소가 게이트 뒤 | 완료·M2 킬 | `cmd_tick` 첫 단계 `_sweep` 무조건 · 잡 명령에 표지 셸 게이트 없음(Rust 핀) |
| 치명③ 묘비 이름 재사용 | 완료·M3 킬 | `_row_rules` 5행 = `R=closed ∨ (T ∧ ¬G)` · `verdict_for` 의 `tombstone_residue` · `_retry_tombstone_remove`(자기 생성 직후 1회만) |
| 2R 1-A A-1 기전 정정 | 완료(문서) | `build_claude_md` docstring · 계약 문서 §8 |
| 2R ④ 계정 키 충돌 | 완료·M11 킬 | `account_plan` |
| 2R ⑤ 폴더 신뢰 | 완료(카드 문장 · 읽기 전용) | `trust_state` · `login_line` |
| 2R ⑥ 좌석 계수 재사용 | 완료 | `resource_check` → `measured.nodes` |
| 2R ⑦ create 재호출 | 완료·M9 킬 | `_create_step` create-timeout 분기(`_pid_alive` · 1시간 hang 실패) |
| 4군① 레인 판정 결정론 | 완료·M10 킬 | `lane_is_base`(CYS_SOCKET·CYS_PACK_DIR 부서 모양) |
| 연쇄 상한(1건/틱·2개·10분) | 완료·M4·M5·M6 킬 | `cmd_tick`(creates[0]) · `_create_step` |
| B-1 고아 원장 청소 | 완료·M7·M8 킬(M7a 층 방어 생존 = 예상값) | `cleanup_orphan_ledgers` |
| V-DETACH · V-PATH | 완료·M15 킬 | `_spawn_create` · `find_cysd` |
| D2 shared(cys-dept 무수정) | 완료 · 폴백 = `CYS_DEPT_ACCOUNT_MODE=fork` / 상수 `ACCOUNT_MODE_DEFAULT` | `_seed_account` · `account_plan` |
| 미션 배달 CLAUDE.md + kickoff 1회 | 완료·M13·M16 킬 | `_write_claude_md` · `cmd_kickoff`(`--queued`·Return 없음) |
| 판정 13행 결정 트리 전 조합 | 완료 | `self_test`(1296 조합 · 13행 36개 전수 출력 · 내장 뮤턴트 2) |
| 카드 문안(내부 용어 0) | 완료(시험) | `render_create_card` · `test_card_has_no_internal_terms` |
| schedule.rs 틱 + 핀 4 | 완료 · cargo 33/33 | `builtin_jobs()` 끝 · 시험 `builtin_jobs_ensure_idempotent_and_versioned` 안 블록 + `builtin_dept_request_tick_conflict_when_id_preempted` |
| factory_reset `dept-requests` | 완료 · cargo 30/30 | `CYS_BASE_EXACT`(25→26) |
| **T0** | **부분** — §5 | — |
| 이종 리뷰 | agy 1R REVISE(1건) · codex 1R 진행 중 | §0 |

## 3. 시험 상태(매듭 시점 실측 · 전부 초록)

- `cd cysjavis-pack/bin && python3 -W ignore -m unittest tests.test_dept_request` → 27건 OK(약 20초 · 6.5초 대기 1건 포함)
- `python3 tests/mut_dept_request.py` → BASELINE 초록 · 17종 중 16 KILLED + M7a 예상 생존 · `MUTANTS ALL-KILLED`(약 6분 · `--only M1,M3` 로 부분 실행)
- `python3 javis_dept_request.py self-test` → PASS
- 팩 계약: `tests/test_import_guard.py` 138/138 · `test_pack_syntax_warnings` OK · `test_nowin_captured_spawns` OK(한 번 적색 → Popen 에 `creationflags` 명시로 수리) · `test_nowin_periodic_spawns` OK · `test_contracts_ct` OK
- Rust: `PATH="$HOME/.cargo/bin:$PATH" cargo test --bin cysd schedule::` 33/33 · `cargo test --lib factory_reset` 30/30(첫 빌드 수 분 — 작업트리에 target 없음)
- 비밀 스캔: `scripts/secret-scan.sh`(staged) clean · `scripts/scan-pack-secrets.sh` OK
- CI: `test_dept_request` 를 ci-branch · pack-release · release(2곳) 의 mac 팩 루프에 등재(레인 대칭 게이트 때문에 3파일 모두). Windows 레인에는 **넣지 않았다**(가짜 실행 파일이 shebang 파이썬·`os.getsid` 의존).

## 4. 내가 내린 판단(지시 없이 · master 확인 필요)

1. **틱이 매분 파이썬을 띄운다**(설계 §3-2 의 `.pending` 셸 게이트 삭제). 근거 = 브리프 「만료·고아 청소·개인정보 7일 삭제를 `.pending` 게이트 밖(매 틱 무조건)」 + 2R ②. 실측 비용 = 빈 상태 틱 1회 0.04초(첫 회 0.15초) · 하루 약 1분 CPU. 대안 = 셸 게이트를 `.pending ∨ 마지막 청소 N분 초과` 로 넓히기(2R 처방) — 브리프 문구와 다르다고 봐서 안 했다.
2. **P 축 「닫힘」**: 모든 좌석 `gate_pending` 이 null 이고 `javis_boot_node.gate_pending_axis_enabled()` 가 참일 때만 닫힘, 아니면 모름. 설계 표는 null=모름만 적었다 — 그대로 두면 12행 「가동」에 항상 확인 창 안내가 붙는다.
3. **T 축 = base 데몬 묘비 파일만**(`~/.local/state/cys/dept_tombstones.json`). phoenix 미러는 안 읽는다(리바이버를 실제로 막는 쪽이 데몬 묘비).
4. **설계 문장 정정**: 「8행을 지우면 13번」 → 실제로는 9행(「켜는 중」)이 받는다. self-test 내장 뮤턴트는 9로 단언.
5. **닫기 요청은 결정 트리 밖의 짧은 표**로 판정(트리에 넣으면 `confirmed ∧ G` 가 「가동」으로 떨어진다).
6. 브리프 동사 나열의 `apply` 는 별도 동사로 만들지 않고 틱의 생성 단계로 두었다(집행은 틱만 — 설계 §3-4).
7. `status --pending` = 「아직 말하지 않은 판정」(`--say` 가 행·상태를 기록) · 7일 넘게 움직임 없는 요청 제외.

## 5. T0 — 설정 폴더 공유의 토큰 갱신 경합(부분)

- 방법(격리 · 자격증명 복사 0 · 비밀값 미열람): 본부 설정 폴더 `~/.cys/claude` 는 **이미 본부 좌석 여럿이 함께 쓰는 공유 상태**다(= 공유안의 현행 실물). 키체인 항목 `Claude Code-credentials-a5d624bb`(경로 sha256 앞 8자리 — 공유 메모리의 `c45eaec5` 는 현재 경로 해시와 다르다)의 **속성만** 읽어 수정 시각(mdat) 변화 = 토큰 갱신으로 보고, 그 앞뒤로 같은 폴더의 세션 jsonl 에서 성공 응답·인증 오류를 센다.
- 관측 1(과거 갱신 1회 · 2026-09-18 14:18:22 KST): ±10분 창 활동 세션 1개(갱신 전 19·후 33 성공 응답) · ±60분 창 3개(걸친 것 1개) · 최근 48시간 인증 오류 API 메시지 **0건** · `.claude.json` 유효 JSON · projects 136키.
- 관측 2(진행 중): 감시기 `~/.cys/pack/round/_reviews/dept-A1-2/t0_watch.sh` 가 21:03 부터 최대 약 23:23 까지 1분마다 mdat 를 읽고, 바뀌면 10분 뒤 ±10분 창을 센다. 로그 = scratchpad `t0_watch.log`(§0-2 와 같은 폴더). 매듭 시점까지 갱신 없음(동시 활동 세션 2개).
- **정직한 한계**: 동시 갱신의 순간에 6좌석이 창 안에 있는 조건은 이 기계에서 만들 수 없다(갱신 시각을 당기려면 자격증명을 건드려야 한다). 설계 §10-2 의 합격 조건(갱신 시점 전후 10분 여섯 좌석 응답 · 공유 `.claude.json` 유효 + 신뢰 키 6개 잔존)은 **VM 실기(master 게이트)** 에서만 닫힌다. 지금 증거는 「공유 설정 폴더에서 갱신 1회 전후로 인증 오류 0 · 세션 지속」 수준이다.
- 폴백 설계(완료): T0 불성립 시 `ACCOUNT_MODE_DEFAULT = "fork"` 한 줄 → 계정 키 = `CYS_PRIMARY_ACCOUNT` → 현행 포크 경로(로그인 1회) · 카드 로그인 줄 자동 전환.

## 6. 4군 점검

| 군 | 이 구현의 꼴 | 방어(코드) | 남는 것 |
|---|---|---|---|
| ① 폭주·큐 남발 | 1분 틱 · 연쇄 생성 · 알림 폭주 | 한 틱 생성 1건(M6) · 상한 2 메뉴 포함(M5) · 간격 10분(M4) · 열린 제안 1장 · 알림 상태 전이당 1회(M14) · 레인 결정론(M10) · 빈 틱 0.04초 | **agy F1 — 예외 시 매분 같은 요청에서 크래시(미수리 · §0-1)** · 편성 심박 600초 캡 오보(기지) |
| ② 무clear | 부서 1개 = 좌석 +3 | 상한 2 → 최대 9좌석 · 카드 고지 | A1-2e(좌석 컨텍스트 정지선) 선결 전 배포 금지 — 이 티켓으로 안 닫힌다 |
| ③ 자가치유가 결정을 되돌림 | 닫은 부서 부활 · 옛 편성 원장 래치 · 사용자 CLAUDE.md 덮기 · 묘비 강제 해소 | 닫기 = 기존 destroy(묘비) · 고아 원장 휴지통(M7·M8 · 본부 제외 2벨트) · CLAUDE.md 표식 있는 것만 교체(M13) · 묘비 재시도는 자기 생성 직후 1회만 | 매분 청소가 GUI 동시 생성 원장을 옮길 창(이동 직전 레지스트리 재독으로 좁힘 · 닫지는 못함) |
| ④ 전 pane 사망 | 확인 뒤 마스터·앱 사망 · 틱 중 데몬 종료 · 절전 | 집행 = 데몬 틱 · 잠금 pid 사망 회수 · create pid 기록 후 대기 · 30분 만료 · 자가복구 표지 | base 데몬 자체 사망 시 30분 넘으면 만료로 정직 보고 |

## 7. 함정(이 기계 · 이 저장소)

- `timeout` 명령 없음(맥) · `pytest` 없음(팩 시험은 `python3 tests/<파일>.py` 또는 `-m unittest`) · `cargo` 는 PATH 밖(`$HOME/.cargo/bin`).
- 같은 프로세스 안에서 틱을 돌리는 시험은 끝난 자식이 좀비로 남아 「살아 있음」으로 읽혔다 → `_pid_alive` 가 먼저 `waitpid(WNOHANG)` 로 회수한다(실제 틱에도 무해).
- 뮤턴트 찾을 문자열은 **더 깊은 들여쓰기 줄의 부분 문자열**이 되기 쉽다(M9 가 그랬다 — 잠금 코드와 겹침). 치환 대상에 다음 줄 주석까지 넣어 유일하게 만든다.
- 팩 창 숨김 계약 시험은 출력을 받는 `subprocess.*` 호출에 `**NOWIN` 또는 `creationflags=` 키워드가 **글자로** 있어야 통과한다.
- 뮤턴트 하네스가 도는 동안 `tests/test_dept_request.py` 를 고치지 마라(매 변이 실행이 디스크의 시험 파일을 읽는다).

## 8. 범위 밖 · 다음 티켓

A1-2d(스킬 `dept-by-conversation` · MASTER_DIRECTIVE 포인터 · CEO_TEMPLATE 재생성) · A1-3 앱(M1·M7) · Feed T6 · Windows purge-state(N3) · A1-4 VM 실기(T0 합격 조건 포함) · Rust 빌드·서명·배포 = master 게이트.
