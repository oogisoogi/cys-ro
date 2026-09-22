# HANDOFF — TICKET=v115-dept (cysr 1.1.5 트랙 P · 팩·부서)

브랜치 `fix/v115-dept` ← `377657dc`(v1.1.4 태그 커밋). 판번 bump 없음(1.1.5 절단 = master).

## 무엇을 고쳤나 (증상 → 원인 【관측】 → 수리)

| 티켓 | 증상(1.1.4 VM 904 §5-② · 윈 실기) | 원인 | 수리(파일) |
|---|---|---|---|
| A2 ⓐ | 교육부 부서장 좌석이 빈 셸로 굳고 큐 7건 적체 · formation.log 「기동=cso,worker」 | 편성은 부서장 좌석을 띄우려 했으나 `javis_boot_node` 가 빈 셸 좌석을 **입양**해 claude 없는 셸에 각성문만 넣었다 | `javis_boot_node.py` `empty_seat_action` — 빈 좌석(seat=empty)은 입양 금지: master·cso = launch-agent 승계 기동(`takeover_empty_seat`) · 그 밖 = 회수(reap) 뒤 기동 · 승계 거절 시 빈 셸 주입 0(`takeover_failed`) |
| A2 ⓐ | ↻ 3회에도 부서장 좌석 안 돌아옴 · phoenix `manual_seats:["master"]` · `fresh_fallback_roles=[]` | phoenix 생산 스폰 판정(기준 377657dc 2394행 alive)이 비종료 좌석이면 **빈 셸도 성공**으로 셌다 → fresh 폴백에 도달 못 함 | **수리 소유 = 트랙 D 906**(master#6e260aed B안 · 남의 좌석 제외 술어와 한 줄 합성) · 이 브랜치는 a4f24dde 에서 넣었다가 되돌림 |
| A2 ⓑ | 오판 회수 뒤 새 좌석 cwd = 홈 | `--cwd` 없이 띄우면 부서 데몬 기본(홈) · 라이브·토폴로지 둘 다 홈이 돼 phoenix 기준 폴더 소실 | `dept_registry_cwd`(lib.rs `cys::dept_registry_cwd` 의 python 미러) — boot_node `--cwd` 미지정 기본 · phoenix `master_seat_cwd` 3순위 |
| A2 ⓒ | 부서 CSO 가 부팅 3분차 빈 부서장 좌석을 `--reclaim` | 회수 게이트에 유예 없음 | `seat_in_boot_grace`(기본 180초 · `CYS_SEAT_BOOT_GRACE_S`) → `_reclaim_verdict` `hold-grace` · CSO §2 「부서장 좌석 회수 = 부팅 유예 뒤 · 근거 로그」 |
| B8 | 빈 셸 좌석(claude 만 사망) 방치 | 위 입양 경로 | 같은 `empty_seat_action` — 에이전트가 붙었다 죽은 좌석은 유예 뒤에만 처분 · `agent.error` 이벤트 1줄(`_seat_event`) · 실행 주체 = formation 심박(부서) |
| A5 | 부서 CSO 가 `~/.local/bin/python3` 링크 신설 | CLT 없는 맥 `python3` 스텁을 「PATH 파손」으로 판단 | `_lib.sh cys_export_bundle_py_env` + `session-start.sh` 1줄: **PATH 에 스텁 아닌 파이썬이 없을 때만** `CLAUDE_ENV_FILE`(공식 SessionStart 기능 · hooks.md 원문 확인)에 번들 python PATH·`CYS_PY` export — 사용자 dotfile 무접촉 · CSO §5-0 · WORKER §5 문안 · CONTENT_PINS 3 |
| B2 | 참가자 좌석 「※ recap」 줄 | Claude Code 설정 `awaySummaryEnabled`(2.1.278 바이너리 스키마 원문 「When false, the session recap … 」) | preflight **C83.recap-default**: `resolve_registration_targets()` 대상 settings.json 에 `awaySummaryEnabled:false` setdefault(사용자 값 존중 · FAIL 없음) |
| B3 | 설치기 재설치 드레인인데 「오너가 재시작 단추를 눌러」 | 발신 주체 단정 | MASTER·CSO·WORKER 드레인 절 · session-start 머리 · **`src/bin/cys.rs` 13631행 1줄**(master#ccb93cb2 승인) → 「오너의 재시작 조작(앱 재시작 단추 · 새 판 설치)에서 cys 코어가 보낸 기계 통지」 · CEO_TEMPLATE 재합성 |
| B7 | 기존 부서 schedule 에 ctx-relay-tick 소급 | 이미 구현(Fable 1.1.3 M6) | 신규 코드 0 · 기존 시험 `schedule.rs v113_dept_lane_ctx_relay_backfill` + 부트 배선 `main.rs:1304 ensure_builtin_jobs` 실재 확인 |

## 재는 법
- `python3 cysjavis-pack/bin/tests/test_v115_dept.py` (20건)
- 뮤턴트: 스크래치 `mut.py` 형태 — 사본 트리에 변이·적용 선-assert·시험 rc. 결과 = 표는 【확인요청】 참조.
- 게이트: `python3 scripts/gen_ceo_template.py --check` · `test_bootv2_doc_contract` · `test_event_inject` · `test_core_inject` · `test_content_pins_parity` · `bash scripts/secret-scan.sh --all`.

## 함정 · 남은 것
- 승계 뒤 옛 빈 셸 좌석(master#0e579100): `_reap_after_succession` — 옛 좌석 큐가 **비었다고 잴 수 있을 때만** `close-surface --reap`(best-effort) + 이벤트 1줄(승계 뒤 옛 좌석 회수 = seat.reaped_after_succession 뜻) · 큐가 남았거나(`queue_nonempty(N)`) 못 쟀으면(`queue_unknown`) 보존 + 이벤트 1줄. 큐는 좌석 단위이고 데몬도 큐가 찬 좌석 reap 을 거부한다(handlers.rs 시험 reap_denies_queue_nonempty…) — 큐 이전은 범위 밖(handlers.rs 무접촉). 옛 셸에 가는 승계 고지 문구의 zsh 오류(904 §5-③)는 트랙 D 소관.
- ctx-relay 잡(`python3 …javis_ctx_relay.py`)·본부 builtin 잡이 PATH `python3` 를 쓴다 — CLT 없는 맥에서는 스텁이다(데몬 스케줄 잡은 세션 env 파일 밖). Rust 잡 상수 = 트랙 D/후속 판단 대상으로 보고만.
- M7(recap 덮어쓰기) 단일 변이는 앞단 필터가 막아 생존 = 층 방어 · 겹침 변이 M7c KILLED.
- 906 인계: 2394행에 `seat != "empty"` 가 들어가면 `test_phoenix_r4_restore` D3 이 적색이 된다(실측 r1=VERIFIED_FRESH · r2=NOOP — 1사이클 안에 빈 좌석 재사용까지 끝나므로 2번째 실행은 NOOP). D3 기대를 「r1 = VERIFIED_FRESH」로 옮겨야 한다.
- cargo `drain_verify_activity_extends_deadline_but_idle_does_not` 는 병렬 부하에서 1회 적색 → 단독 3/3 · 재실행 29/0(타이밍 간헐 · 문구 무관).
- 이 시험 파일은 CI 레인 목록 밖(`test_v113_review_fix` 선례) — 편입은 3레인 동시 등재가 필요(ci-branch·release·pack-release).

## 이월(1.1.5 제외 · master#0e579100)
- **B8 본부 빈 셸 자동 처분**: 주기 실행 주체인 builtin 잡 formation-heartbeat(src/bin/cysd/schedule.rs 212~216행)가 `for d in $(cys-dept list)` 로 부서 소켓만 돌며 javis_formation ensure 를 부른다 — 본부 소켓은 루프에 없어 본부 빈 셸 좌석은 boot_node 처분 술어에 닿지 않는다. 본부 포함 시 예상 = Rust schedule.rs 명령 문자열 1줄(루프 앞 본부 ensure 1회) + builtin 잡 갱신 전파용 BUILTIN_JOBS_VERSION 범프 여부 확인 + 시험 1건 ≈ 파일 1 · 5~15줄. 제외 사유 = 본부 master 가 cys 밖 외부 세션인 기계에서 유령 master 좌석 위험(CYS_FORMATION_EXTERNAL_ROLES 미설정) · 트랙 D 영역 · 본부 master 공백은 A4(906)로 닫힘.
