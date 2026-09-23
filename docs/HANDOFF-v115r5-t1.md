# HANDOFF — v1.1.5 11차 t1: ↻ 결과 알림 참말화(T1) + 승계 좌석 대화 잇기(T3)

TICKET=v115r5-t1 · 워커 surface:1013 · 브랜치 `fix/v115r5-t1` ← f29bb0a5(10차 9d695ec8 + HANDOFF 2커밋)
커밋: 451d7861(제품 + 옛 동작을 고정하던 기존 시험 갱신) · 9a0e4d7e(새 시험) · 이 문서(문서).
표식: 【관측】 = 로그·도구 출력으로 확인 · 【추정】 = 관측에서 끌어낸 해석.

## 1. 원인표

| # | 증상(VM r3 §3-4) | 원인 | 자리 | 판정 |
|---|---|---|---|---|
| T1① | ↻ 뒤 「⚠ 재시작 후 부서 복원 실패」인데 좌석 9/9 claude | ↻ 뒤 부서마다 복원자 셋이 겹친다 — ⑴ phoenix 콜드부트 `cys restore` ⑵ `rotate_dept_daemon` 사이드카 `cys restore --include-master` ⑶ 편성(formation → javis_boot_node → launch-agent). `run_restore` 는 시작 때 찍은 live 스냅샷으로 판단하고, 락 대기 사이에 다른 복원자가 역할을 세우면 기동이 `claim_denied (held by live surface)` 로 끝나 **실패로 셌다** → rc 1 → `restore_ok=false`. 부서 경로에는 본부의 요약 판독·재실측·사정별 문안이 없었다 | `src/bin/cys.rs` run_restore 실패 분기 · `src-tauri/src/main.rs` rotate_dept_daemon(구 `run_sidecar_restore` = 종료 코드 단독) | 【관측】 VM r3 `events-cys-dept-dept-N.jsonl` caller_pid 귀속(dept-3: 39150 = phoenix 1차 · 39155 cso·master denied · dept-1: 32281 cso·master denied) + **헤드리스 재현**(§4) · 사이드카 pid 는 소거법 【추정】 |
| T1② | 「재시작 완료 — 일부 자리는 마지막 저장을 못 했어요 … 대화는 트랜스크립트로 복원했어요 … 행정부 / master(surface:2) 마커 미확인(시간초과)」 | 확인 못 함(timeout)을 「못 했어요」로 단정 · 드레인은 재시작 **전** 단계인데 복원 결과를 측정 없이 약속 · 자리 번호는 재시작 전 번호 | `ui/src/drainverify.ts` drainVerifyNotice | 【관측】 코드 · 행정부 부서장은 그 자리에서 새 대화로 시작(T3) — 약속이 사실과 반대 |
| T3 | 승계 좌석(dept-1·dept-3 부서장)이 `--resume` 없이 새 대화 | **가설 교정**: 데몬 takeover 가 핀을 떨어뜨린 것이 아니다. 편성 `_ensure_master_seat` 가 빈 셸을 만들고 `javis_boot_node` 가 `cys launch-agent`(resume=false · 핀 없음)로 승계 기동 → phoenix 의 `--resume` 기동보다 먼저 앉아 phoenix 쪽이 claim_denied. 핀은 있었다(dept-3 desired_roster master = 103401b6… · 관측 3bf5c161… → phoenix `unverified(fork)`) | `cysjavis-pack/bin/javis_formation.py` _ensure_master_seat · `javis_boot_node.py` LAUNCH · `src/bin/cys.rs` run_launch_agent | 【관측】 events(11:48:29 takeover 6→7 caller 39446 · 11:48:44/46 phoenix master denied) · phoenix journal |

T3 억제 관문: 조사 21:24~21:29 · 데몬 프로토콜·topology 스키마 변경 0(topology `saved` 를 읽기만) → 구현.

## 2. 수리

- **T1①** `run_restore`: 기동 실패 뒤 `system.topology` 를 다시 읽어 그 역할이 **앉은 좌석(occupied)** 에 있으면 「다른 복원 경로가 먼저 세움 — 건너뜀」(실패 아님). unknown·empty 는 앉았다고 보지 않는다 → 그 경우는 아래 재실측이 잡는다.
- **T1① 공용화** `run_sidecar_restore_judged`(요약 판독 + 실패면 15초 뒤 1회 재실측 · 관문 보류만이면 재실행 없음) · `restore_note(place, summary)` · `restore_should_retry` · `RESTORE_RETRY_WAIT` — 본부(spawn_org_restore)·부서 순회·`rotate_dept_daemon` 이 같은 함수를 쓴다(복제 0). `rotate_dept_daemon` 은 실패면 `restore_note`(부서 표시 이름)를 싣고 UI 경보 본문이 그 문안을 쓴다.
- **T1②** 드레인 알림 = 「재시작 전에 저장을 확인하지 못한 자리가 있어요」 + 자리별 쉬운 말 사유(괄호·자리 번호 없음). 복원 약속 삭제.
- **T1③** `restart_continuity`(tauri, 읽기만): 본부·등록 부서의 phoenix 원장 `journal-default.json` 을 **이번 회차**(verify 단계 ts ≥ ↻ 누른 시각)로만 판정 — verified = 이어짐 · fresh 또는 unverified·fork = 새 대화 · 그 밖 = 말하지 않음 · 전원 판정되거나 상한(UI 120초 · 코드 상한 180초)까지 3초 간격 읽기. UI 는 새 대화 자리가 있을 때만 「일부 자리는 새 대화로 시작했어요 — 〈부서〉 〈역할〉 자리는 이전 대화를 잇지 못해 새 대화로 시작했어요.」
- **T3** `cys launch-agent --resume-saved`: 저장 topology 의 그 역할 핀(묘비 아님 · 같은 agent · 빈 값 아님)을 고르고, **세션 파일이 실재해 resume 인자가 붙을 때만** restore 와 같은 인자(resume·핀·계정 dir·restore 글)로 기동한다. 못 이으면 종전과 같은 새 기동(resume 을 켠 채 파일이 없으면 짧은 복귀 글만 받은 새 대화 = 절대지침 누락이 되므로 미리 잰다). `javis_boot_node` 는 이 플래그로 기동하고, 옛 cys 가 플래그를 모르면(rc 2 + stderr 에 플래그 이름) 플래그 없이 1회만 재시도.

## 3. 상황 → 알림 진리표(수리본 · ↻ 1회)

| 상황(실측) | ① 재시작 결과 | ② 재시작 전 저장 | ③ 재시작 뒤 대화 |
|---|---|---|---|
| 모두 착석 + 모두 이어짐 | ✅ 데몬 재시작 완료 | 전원 확인 = 없음 · 확인 못 한 자리 = 사실 알림 | 없음(조용한 성공) |
| 착석 + 일부 새 대화 | ✅ 데몬 재시작 완료 | 위와 같음 | 「일부 자리는 새 대화로 시작했어요」 + 부서·역할 |
| 겹친 복원자가 먼저 세움(VM r3 형태) | ✅(종전 ⚠ 거짓 경보) — 건너뜀으로 셈 · 그래도 실패면 15초 뒤 재실측 | 위와 같음 | 이어짐이면 없음 |
| 일부 미착석(재실측까지 실패) | ⚠ 재시작 후 부서 복원 실패 — 본문 「〈부서〉 자리 N곳을 세우지 못했습니다 — …」 | 위와 같음 | 판정된 자리만 |
| 관문 대기 | ⚠ … 「〈부서〉 자리 N곳이 첫 실행 확인을 기다립니다 — 그 창에서 확인을 한 번 눌러 주세요.」(재실행 없음) | 위와 같음 | 판정 전 = 말하지 않음 |
| 사이드카 불통(요약 없음) | ⚠ … 「〈부서〉 복원을 실행하지 못했습니다(데몬 응답 없음) — …」(1회 재실측 뒤) | 위와 같음 | 원장 없으면 말하지 않음 |
| 판정 전(재핀 전 · 상한 도달) | 위 규칙 | 위 규칙 | 말하지 않음 |

## 4. 헤드리스 재현(T1① · 격리 cysd · 진짜 claude 0 · 토큰 0) 【관측】

방법: 격리 HOME·소켓(`/tmp/cysrr.*`)에 cysd → cso(agent claude) 좌석을 세웠다가 `--reap` 으로 닫아 저장 핀만 남김 → boot 락을 6초 쥔 채 `cys restore --include-master` 기동(스냅샷 = cso 없음, 락 대기) → 그 사이 다른 경로 흉내로 cso 좌석(셸 아래 자손 = occupied) 세움 → 락 해제.

| 바이너리 | restore 출력 | rc |
|---|---|---|
| 기준선(HEAD cys) | `· cso: 기동 실패 — 나머지 역할 계속 진행` · `restore 완료: 재기동 0 · 실패 1 · 관문 보류 0` · stderr `claim_denied … held by a live surface` | **1** |
| 수리본 | `· cso: 다른 복원 경로가 먼저 세움 — 건너뜀` · `restore 완료: 재기동 0 · 실패 0 · 관문 보류 0` | **0** |

두 회차 모두 격리 HOME 아래 claude 프로세스 0 · 끝난 뒤 잔존 cysd 0. (첫 시도의 가짜 좌석 `--cmd sleep` 은 자손이 없어 seat=empty 였다 — 진짜 claude 좌석은 셸 아래 자손이라 `/bin/sh -c 'sleep 300; :'` 로 맞췄다.)

## 5. 시험 · 기준선 · 뮤턴트

- 새 시험: cys `v115r5_saved_resume_pin_table` · `v115r5_role_held_by_live_seat_table` · `v115r5_restore_and_resume_saved_wiring` / src-tauri `v115r5_dept_rotate_uses_shared_restore_judgment` · `v115r5_phoenix_continuity_table` / ui `continuityNotice` 3 · `manualRestartAllDaemons — 결과 알림은 실측에서 파생` 1 · 재작성 `drainVerifyNotice … 사실만` / pack `V115r5T3BootNodeResumesSaved` 2(test_v115_dept.py — CI 3레인 기존 등재 파일).
- 기준선(HEAD) 적색 → 수리본 초록(직접 재실측): boot_node 2/2 적색(기준선 javis_boot_node.py 로 교체 실행) · drainverify 2 적색(T1② · 배선 — 기준선 drainverify.ts/main.ts + 이어짐 함수만 이식) · Rust 새 순수 함수 시험은 기준선에 함수가 없어 컴파일 적색 — 행동 기준선은 §4 헤드리스 재현.
- 뮤턴트 15/15 KILLED(하네스 = 변이 적용 count==1 선단언 · 조준 시험 rc 판정 · finally 원복 + sha 대조):

| # | 결함 | 변이 | 잡은 시험 |
|---|---|---|---|
| M1 | T1① | 앉은 좌석 판정을 `!= "empty"` 로 | v115r5_role_held_by_live_seat_table |
| M2 | T1① | run_restore 재실측 분기 삭제 | v115r5_restore_and_resume_saved_wiring |
| M3 | T1① | rotate_dept_daemon 이 판정 층 대신 1회 실행 | v115r5_dept_rotate_uses_shared_restore_judgment |
| M4 | T1① | 재실측 판정 무력화 | v113_hq_restore_retries_before_reporting |
| M5 | T1② | 「대화는 트랜스크립트로 복원했어요」 복귀 | drainVerifyNotice 사실만 |
| M6 | T1② | 사유 문구 「마커 미확인(시간초과)」 복귀 | drainVerifyNotice 사실만 |
| M7 | T1③ | 이번 회차 조건 무시 | v115r5_phoenix_continuity_table |
| M8 | T1③ | transient 까지 새 대화로 | v115r5_phoenix_continuity_table |
| M9 | T1③ | 판정 전 자리까지 알림 | continuityNotice 2건 |
| M10 | T1③ | ↻ 흐름에서 이어짐 알림 호출 삭제 | manualRestartAllDaemons 배선 |
| M11 | T3 | boot_node 가 --resume-saved 안 씀 | test_takeover_launch_asks_for_saved_conversation(+폴백 시험) |
| M12 | T3 | 옛 cys 재시도에 플래그 유지 | test_old_cys_without_flag_falls_back_to_plain_launch_once |
| M13 | T3 | 묘비 역할 핀 허용 | v115r5_saved_resume_pin_table |
| M14 | T3 | 다른 CLI 세션 허용 | v115r5_saved_resume_pin_table |
| M15 | T3 | 이을 수 있는지 사전 측정 삭제 | v115r5_restore_and_resume_saved_wiring |

## 6. 전체 회귀(수리본)

cargo `--lib` 534/0(1 ignored) · `--bin cys` 285/0 · `--bin cysd -- --test-threads=1` 1040/0(1 ignored) · `-p cys-app` 165/0(1 ignored) · 팩 python CI 목록 50 + test_phoenix_v115_spawn_settle = 51 실행 0 실패 · javis_detect --self-test rc 0 · `bun test` 1106/0 · ui typecheck 신규 오류 0(기준선 archive 사본 대조 · 기존 7건 그대로) · `run_bootstrap_health.py` GREEN 149 PASS / 0 FAIL / 1 SKIP · secret-scan --all clean(1089 파일) · 디렉티브 무접촉(gen --check 대상 없음).
정직 고지: `--bin cys` 첫 전체 실행에서 `doctor_fix_then_rediag_ok` 1건 적색(잔여 락 Warn) — 같은 시각 건강 러너·재현이 병행 중이었다. 단독 3/3 초록 · 병행 없는 전체 재실행 285/0.

## 7. 4군

① 폭주 큐: 재실측은 공용 함수 한 곳 1회 상한(뮤턴트 M3·M4 · 시험이 호출 수 2 를 단언) · boot_node 폴백 재시도 1회(rc 2 + 플래그 이름 조건) · 이어짐 측정은 읽기만(기동·재시도 0 · 180초 상한).
② 무clear: `--resume-saved` 의 핀 원천 = restore 와 같은 topology `saved`(순환 뒤 등록 경로 교체 추종 = D2 R2 그대로) · 묘비 역할 핀 거부 · 세션 파일 없으면 새 기동 — 옛 대화를 새로 되살리는 경로 없음. cysd 전체(D2 R2 시험 포함) 1040/0.
③ 자가치유: 본부 판정 규칙은 바이트 같은 로직을 공용 함수로 옮김(v113 시험 3종 초록 · health GREEN) · phoenix 는 무접촉 · 겹친 복원자가 먼저 세운 경우 이제 성공으로 수렴.
④ 전 pane 사망: 닫기·reap 경로 변경 0 · 재분류는 `system.topology` 읽기만 · 헤드리스 재현에서 좌석 닫힘 0.

## 8. 남은 것 · 함정

- VM ↻ 재확인(부서 3 · 알림 = 좌석 실측 일치 · 부서장 `--resume`) = master 별도 발주 몫. 이 티켓은 VM 무접촉.
- `restart_continuity` 는 phoenix 원장 경로를 소켓 상태 폴더/phoenix/journal-default.json 으로 읽는다(맥 실측 경로). 윈도는 `daemon_state_dir_for` 가 cysd 규약 미러로 푸는데 윈도 phoenix 원장 위치는 【미측정】 — 못 읽으면 말하지 않을 뿐(거짓 알림 0).
- 부서 번호 재사용 + 같은 폴더 이름으로 부서를 다시 만들면 옛 topology 핀이 남아 있을 수 있다 — 이것은 phoenix 콜드부트 복원도 똑같이 읽는 원천이라 이번 변경이 새로 연 문은 아니다(묘비가 있으면 둘 다 거부).
- 시험용 번들 자리표(src-tauri/binaries·resources·runtime · ui/dist — gitignore)를 두고 cys-app 시험을 돌리면 target/debug/cysd·cys 가 0바이트로 덮인다 — 이후 `cargo build --bin cysd --bin cys` 필수(이 티켓에서도 발생 · 재빌드함).
- T2(본부 cso 3초 닫힘)·T4(새 설치 「복원」 카드)·F-1 = 1.1.6(무접촉).

## 9. 판정

- 이종 agy 1R = ACCEPT(diff 만 · 원문 `~/axdev/master/reports/cysr-115-2026-09-22/hetero-agy-v115r5-t1.md`) · 통합 = v115r5-cut 좌석(master 배정).
