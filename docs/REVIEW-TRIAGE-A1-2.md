# 리뷰 심사표 — A1-2 이종 1R (agy F1 · codex F1~F17)

- 작성: worker-3@surface:819 · 2026-09-18 · TICKET=dept-impl-A1-2b(전임 818 의 A1-2 후속)
- 대상 코드: `cysjavis-pack/bin/javis_dept_request.py`(아래 줄 번호 = **이 커밋 기준**. codex 가 인용한 줄 번호는 수리 전 판이라 함수 이름으로 대조한다)
- 리뷰 원문: `~/.cys/pack/round/_reviews/dept-A1-2/agy-r1.out`(REVISE · F1) · `codex-r1.out`(REVISE · F1~F17 · RC=0)
- 판정 3종: **수용**(수리함) · **반박**(코드 줄 근거로 지적이 성립하지 않음) · **범위 밖**(다음 티켓). 한 항목 안에서 일부만 성립하면 「부분 수용」으로 적고 성립 부분·불성립 부분을 갈라 적는다.
- 수리 1건당 시험 1 + 뮤턴트 1 원칙. 시험 = `tests/test_dept_request.py` 의 `TestReviewR1`. 뮤턴트 = `tests/mut_dept_request.py` 의 M17~M33.

## 요약

| 판정 | 건수 | 항목 |
|---|---|---|
| 수용 | 13 | agy F1 · codex F1 F2 F4 F5 F7 F8 F9 F10 F11 F12 F15 F16 |
| 부분 수용 | 4 | codex F3 · F6 · F14 · F17(성립 부분 수리 · 불성립·잔여 부분은 칸 안에 근거) |
| 반박(단독) | 0 | 반박은 부분 수용 항목 안에만 있다(F3 의 A 요청 판정 행 주장 · F14 의 정확히-1회 요구) |
| 범위 밖 | 1 | codex F13 → ISSUES B11 |
| 합계 | 18 | agy 1 + codex 17 |

## agy 1R

| ID | 지적 | 판정 | 근거·수리 | 시험 / 뮤턴트 |
|---|---|---|---|---|
| agy F1 (high) | 틱이 요청 집행 중 예외로 죽으면 요청이 `confirmed` 로 남아 매분 같은 자리에서 틱 전체가 죽는다(poison pill) | **수용** | 수리 전 `cmd_tick` 은 `_create_step(r, st, reqs)` · `_close_step(r)` 를 감싸지 않았다. 수리 = `_run_step`(L1514): 예외 → `_fail(r, "crash:<예외 이름>")` → `save_req` → `tick-errors.log`. 레지스트리 판독 실패(`RegistryUnreadable`)만은 실패로 닫지 않고 보류(F12) | `test_agy_f1_step_crash_fails_request_not_tick` / M17 |

## codex 1R

| ID | 지적 | 판정 | 근거·수리 | 시험 / 뮤턴트 |
|---|---|---|---|---|
| F1 (high) | 발화 원문 수명이 7일로 제한되지 않는다(완료·실패 30일 · proposed·가동 전 created 는 삭제 분기 없음 · `updated_at` 기준이라 저장마다 연장) | **수용** | 수리 전 `_sweep` 은 상태별 분기 + `age = t - updated_at`. 수리 = 모든 상태에서 `created_at`(불변) 7일 뒤 `utterance.txt` 삭제(L1196). 폴더 보존(30일)은 따로 계산 | `test_f1_utterance_deleted_7d_after_proposal_in_any_state` / M18 |
| F2 (high) | 첫 자식이 도는 동안 디스크 상태는 `confirmed` — 틱이 기다리다 죽으면 다음 틱이 살아 있는 `create_pid` 를 무시하고 다시 부른다 · spawn 과 pid 저장 사이 창 | **수용**(실행 시험으로 재현 확인) | 수리 전 생존 검사는 `if r["state"] == "create-timeout"` 안에만 있었고, 간격 기준 `last_create_at` 은 `_create_step` 이 끝난 **뒤** 저장됐다. 재현: 틱을 하위 프로세스로 띄워 기다리는 중 SIGKILL → 다음 틱이 두 번째 create 를 불렀다(수리 전 판). 수리 = `reentry = state == "create-timeout" or create_calls`(L1393) — 한 번이라도 부른 요청은 언제나 생존·등재부터 본다 + 호출 수·시각·간격 기준을 spawn **전에** 영속(L1446). 남은 창: spawn 과 pid 기록 사이(마이크로초) — 그때도 간격·요청당 2회 상한은 지켜진다(계약 문서 §4-2) | `test_f2_no_respawn_when_tick_died_mid_wait`(간격 0 으로 벨트를 갈라 생존 검사만 잰다) / M19 |
| F3 (high) | 번호 재사용 시 키 조회 실패 → G=없음 → 옛 `dept_name` 복원 → 5행 닫힘 · `tombstone_residue` 누락 · R=closed 무조건 닫힘 | **부분 수용** | **불성립 부분(반박)**: 요청 A 의 판정은 「A 가 만든 부서」에 대한 것이다. `axes_for`(L763~) 는 G 를 A 의 키로 찾는다(L771 `G = bool(name and name in reg)` — name 은 `reg_name_for_key(key)`) — 같은 번호를 다른 키의 부서가 쓰면 A 의 부서는 실제로 없으므로 A 에 5행 「닫혀 있습니다」는 참이다. `tombstone_residue` 는 「이 판정 대상 부서가 묘비와 함께 살아 있다」는 칸이라 A 의 행에 붙으면 오히려 거짓이다. R=closed 는 닫기 요청에서만 나오고 닫기 요청의 말은 `say_for` 의 짧은 표(L800 `if r and r.get("kind") == "close"`)가 정하므로 트리 5행의 무조건 분기는 말에 닿지 않는다(HANDOFF §4 판단 5 · master 승인). **성립 부분(수용)**: `status --all` 이 옛 요청의 `dept_name` 을 「이미 보고됨」으로 가려, 번호를 재사용한 **새 부서**(묘비 잔존 포함)가 표에서 통째로 빠졌다. 수리 = `claimed` 를 키로 지금 소유가 확인되는 이름만으로(L896) → 새 부서가 1행 + `tombstone_residue` 로 나온다 | `test_f3_reused_number_listed_in_status_all` / M20 |
| F4 (high) | 묘비 잔존 부서를 상한 계산에서 뺀다 → 2개인데 1개로 세어 추가 생성 허용 | **수용** | 수리 전 `live_depts` = `{n: e for n, e in reg.items() if n not in ts}`. 수리 = 레지스트리 항목 전부(L329) — 닫는 중(묘비 선기록·등재 잔존)도 세는 쪽이 거부 방향이라 보수적 | `test_f4_tombstone_residue_counts_toward_cap` / M21 |
| F5 (high) | 타임아웃 재시도가 상한·10분 간격·자원 검사를 건너뛴다 | **수용** | 수리 전 검사는 `else`(첫 호출) 분기에만. 수리 = 재진입이 생존·등재·호출 수 판정 뒤 첫 호출과 **같은** 상한·간격·자원 검사를 지난다(`_create_step` 본문 · 계약 문서 §4-2) | `test_f5_retry_respects_gap` / M22 |
| F6 (high) | 표식이 있는 파일은 요청 ID·내용을 확인하지 않고 덮는다(사람이 표식을 남긴 채 고친 파일 소실) · 존재 검사와 교체 사이 경합 | **부분 수용** | 수리 = `_write_claude_md`(L1299): ⑴이 요청 바이트와 같으면 그대로 ⑵표식 자기 해시가 맞는(사람이 안 고친) 생성 파일만 교체(`_generated_untouched` L1287) ⑶그 밖 충돌 · 새 파일은 임시 파일 `os.link` no-clobber(L1332). **남은 부분**: ⑵의 대조와 교체 사이에 사람이 고치는 경합은 닫지 못했다(파일 시스템에 조건부 교체 원시 연산이 없다 — 창 = 수 밀리초). 계약 문서 §8 에 명시 | `test_f6_edited_generated_claude_md_is_conflict` · `test_f6_untouched_generated_claude_md_is_replaced`(과차단 없음) / M23 |
| F7 (high) | 재시도가 안내문(`claude_md.txt`·설치된 `CLAUDE.md`)을 다시 대조하지 않는다 | **수용** | 수리 전 `_write_claude_md` 호출은 `else` 분기 안. 수리 = 모든 create 호출 직전에 호출(재진입 포함) | `test_f7_retry_rechecks_claude_md` / M24 |
| F8 (high) | 요청 수정자 사이에 잠금·버전 검사가 없다 — `status --say` 가 옛 객체를 저장해 confirmed 를 proposed 로 되돌리는 lost-update | **수용** | 수리 = 쓰는 이 줄이기 + 전이 잠금: ⑴`status --say` 는 `said.json` 에만 쓴다(L879 · request.json 무접촉) ⑵kickoff 1회는 `kickoff.json` O_EXCL 원자 표지(L976) ⑶proposed 에서 떠나는 두 전이(교체 `_supersede_open` L529 · 확인 `cmd_confirm` L673)는 요청별 잠금 안에서 **다시 읽은** 상태가 proposed 일 때만 쓴다(`transition` L208) ⑷discard 는 틱 잠금 안(F11). 남은 쓰는 이 = 틱(잠금으로 직렬) · 전이 두 개(잠금) · discard(틱 잠금) | `test_f8_stale_writers_do_not_revert_confirm`(옛 객체로 교체 시도 + `--say` 가 request.json 바이트 불변) / M25 |
| F9 (high) | stale 잠금 회수가 동시 실행에 안전하지 않다 — 같은 죽은 owner 를 읽은 두 틱 중 늦은 쪽이 앞선 틱의 새 잠금을 rename | **수용** | 수리 전 `acquire_lock` = mkdir + owner.json 읽기 → rename 두 단계(경합 성립 — 코드 읽기로 확인). 수리 = `javis_lock.FileLock`(flock/msvcrt · 비차단) — 보유 프로세스가 죽으면 커널이 풀어 회수 단계가 없다(L1007·L1039). 파일 이름 `.tick.lock` 으로 옛 `.lock/` 과 분리 | `test_f9_tick_lock_is_kernel_held`(다른 프로세스가 잡으면 틱 skip · SIGKILL 뒤 다음 틱 진행) / M26 |
| F10 (high) | 닫기 확인 뒤 같은 번호로 다른 부서가 생기면 새 부서를 destroy | **수용** | 수리 = `_close_step` 이 카드에 기록한 키·폴더·소켓을 지금 그 번호의 레지스트리 항목과 대조, 하나라도 다르면 `failed(target_changed:<칸>)`(L1485). 닫기 카드에 소켓 칸 추가. 옛 요청(소켓 칸 없음)은 있는 칸만 대조 | `test_f10_close_refuses_when_number_now_other_dept` / M27 |
| F11 (high) | discard 가 실행 중인 생성과 직렬화되지 않는다 | **수용** | 수리 = `cmd_discard`(L906)가 틱 잠금을 잡은 뒤에만 `_discard_locked`(L920) — 못 잡으면 exit 7 `busy`. 잠금 안에서 재독해 `confirmed` 이거나 첫 자식 생존이면 exit 7 `in_flight` | `test_f11_discard_waits_for_tick_lock` / M28 · `test_f11_discard_refuses_live_create`(생존 검사 · 뮤턴트 없음 — 아래 「정직 고지」) |
| F12 (high) | 레지스트리 손상·일시 판독 실패가 「부서 없음」으로 바뀐다 → 상한 통과 · 가동 부서 원장 이동 · discard 삭제 | **수용**(실행 시험으로 확인) | 수리 전 `registry()` 는 `load_json` 의 `(OSError, ValueError) → default`. 수리 = `registry()`(L254) 가 파일 없음만 빈 목록, 판독·해석·스키마 오류는 `RegistryUnreadable`. 틱: 고아 청소 보류 · 생성·닫기·가동 판정 보류(L1544~) · 동사: exit 2 `registry_unreadable` · discard: exit 7 | `test_f12_unreadable_registry_holds_destruction`(반쯤 쓰인 depts.json → 원장 보존 · 요청 confirmed 유지 · propose exit 2) / M29 |
| F13 (med) | 레지스트리 재독과 원장 이동 사이 경합 · 읽은 원장과 옮기는 원장의 동일성 | **범위 밖 → ISSUES B11** | 성립한다(HANDOFF §6 ③ 에 이미 「좁힘 · 닫지 못함」으로 적힌 잔여). 닫으려면 GUI 의 부서 등록(Rust `cys-dept`)과 이 청소가 **같은 잠금**을 써야 한다 — `cys-dept`(bash)·레지스트리 쓰기 쪽 수정이 필요해 이 티켓(팩 도구 1파일)의 범위를 넘는다. 피해 상한 = 원장 1개가 휴지통으로 이동(삭제 아님 · 편성 심박이 다시 쓴다). **다음 티켓 = ISSUES B11**(master 판정 2026-09-18 `master#7ed4c8f4` — 레지스트리·편성 원장 쓰기 측 공통 잠금 또는 세대 검증 · cys-dept 수정 동반 · A1-3 이관은 범위 확장이라 불가) | — |
| F14 (med) | 상태 전이당 알림 1회가 보장되지 않는다(저장 후 전송 전 사망 = 유실 · 전송 후 저장 전 사망 = 중복 · 실패도 notified) | **부분 수용** | **수용 부분**: 가동 알림은 보낸 뒤 저장해 사망 시 **중복**이 났다 — 수리 = `running_notified` 를 먼저 영속하고 보낸다(L1583). **반박 부분**: 「정확히 1회(outbox·수신측 중복 제거)」 요구는 이 설계의 계약이 아니다 — 알림은 최대 1회 보조 신호이고, 유실·전송 실패는 마스터가 매 턴 부르는 `status --pending`(「아직 말하지 않은 판정」)이 받친다(`_notify` docstring L1100~ 「ACL 에 막혀도 기능은 선다(마스터가 턴마다 status --pending 을 부른다)」). 계약 문서 §4 6 에 「보장 = 최대 1회」로 명시 | `test_f14_running_notify_not_duplicated_after_crash` / M30 |
| F15 (med) | 확인 뒤 안내문 파일 삭제·해독 불가 → 틱 전체 exit 1 · 매분 반복 | **수용** | 수리 전 `_write_claude_md` 의 `open` 은 예외 처리 없음. 수리 = 판독 실패 = `claude_md_changed`(요청 단위 실패) · 그 밖의 예외도 `_run_step`(agy F1)이 요청 단위로 가둔다 | `test_f15_missing_claude_md_is_request_failure` / M31 |
| F16 (med) | 분리 실행한 자식의 stdout 이 틱 파이프 — 틱이 먼저 끝나면 이후 출력에서 SIGPIPE/EPIPE | **수용**(master 권고대로) | 수리 = `_spawn_create`(L1265)의 stdout 을 호출 번호별 파일 `.create-<키>-<n>.out` 로, 부모는 `p.wait` 뒤 파일에서 마지막 줄을 읽는다 | `test_f16_detached_child_output_survives_tick_exit`(틱을 하위 프로세스로 · 기다림 1초 · 자식은 3초 뒤 출력 → 자식이 끝까지 출력) / M32 |
| F17 (high) | 생성 직후라는 시점만으로 묘비가 옛 잔존물임을 보장 못 한다 — GUI 가 방금 닫으며 쓴 새 묘비를 지울 수 있다 | **부분 수용** | 수리 = 첫 create 호출 **전** 묘비 스냅샷(`pre_ts` L1439)에 있던 이름만 해소 재시도(L1379) — 생성 뒤 새로 생긴 묘비는 건드리지 않는다. **남은 부분**: 옛 잔존 묘비가 있던 번호를 GUI 가 생성 직후 또 닫는 경우(두 묘비가 같은 이름)는 여전히 구별 못 한다 — 묘비에 세대·의도 ID 를 적는 것은 Rust 데몬 묘비 형식 변경이라 범위 밖(A1-3 이관 제안) | `test_f17_fresh_tombstone_after_create_is_kept` / M33 |

## 정직 고지

- **뮤턴트 실측(34종)**: 전수 실행 1회 = 32 KILLED · M7a 생존(예상 — 층 방어) · **M9 SURVIVED**. 원인 = 이 라운드의 F5 수리(재호출도 10분 간격을 지난다)가 두 번째 벨트가 되어, 기본 간격 600초로 돌던 옛 시험 `test_no_recall_while_first_child_alive` 에서 생존 검사를 가렸다(시험이 공허해진 것이 아니라 층 방어). 처방 = 그 시험에 `CYS_DEPT_CREATE_GAP_SEC=0` 을 넣어 생존 축만 재게 함(F2 시험과 같은 방식) → `--only M9,M19,M22` 재실행 = 3종 전부 KILLED. 바뀐 시험 파일은 그 한 시험뿐이라 나머지 31종의 귀속은 유효하다.

- **수리 전 판 대조(실측)**: 새 시험 19건(`TestReviewR1`)을 수리 전 판(HEAD `254bd4fa` 의 `javis_dept_request.py`)에 `DEPT_REQUEST_MODULE` 로 돌렸다 → **18건 적색 · 1건 초록**(초록 = `test_f6_untouched_generated_claude_md_is_replaced` — 과차단이 없음을 재는 양성 시험이라 수리 전에도 초록이 맞다). 즉 수용·부분 수용한 결함은 전부 수리 전 코드에서 시험으로 드러난다.
  - 단 F9 는 예외로 읽어야 한다: 수리 전 판의 적색은 「경합 재현」이 아니라 새 잠금 파일(`.tick.lock`)을 옛 코드가 모른다는 뜻이다. F9 의 경합(두 틱의 회수 교차) 자체는 **코드 읽기로 성립 확인**했고 실행 재현은 하지 않았다 — 수리가 회수 단계를 없애 경합이 생길 자리 자체가 사라졌다.

- `test_f11_discard_refuses_live_create` 는 뮤턴트가 없다(F11 수리 한 건 = 잠금 · 생존 검사는 같은 수리의 두 번째 벨트). 생존 검사를 끄는 뮤턴트를 더하면 잠금 뮤턴트와 한 시험이 층 방어로 서로를 가릴 수 있어, 이번 라운드는 잠금 축(M28)만 귀속했다.
- master 사전 판단의 「반박하려면 실행 시험」 5건(F9·F8·F12·F2·F15)은 **전부 수용**했다 — 반박이 없으므로 반박용 실행 시험은 없고, 수용한 수리의 시험이 실행 시험이다(F2·F9·F16 은 틱을 실제 하위 프로세스로 띄워 죽인다).

---

# 2R 심사표 (agy REVISE · codex REVISE — 커밋 521ed966 대상)

- 리뷰 원문: `_reviews/dept-A1-2/agy-r2.out` · `codex-r2.out`(둘 다 RC=0). 수리 커밋 = 이 문서를 담은 다음 커밋.
- 시험 = `TestReviewR2`(9건) · 뮤턴트 = M34~M42 + 재조준 M13·M20·M23.
- **수리 전 판 대조(실측)**: `TestReviewR2` 9건을 521ed966 판에 돌리면 **9건 전부 적색**.

## agy 2R

| ID | 지적 | 판정 | 근거·수리 | 시험 / 뮤턴트 |
|---|---|---|---|---|
| C1~C12 · 1R 수용 반영 확인 | 전건 충족 · 1R 수용 13건 반영 확인 · F6·F14·F17·F13 판정 타당 | 확인(조치 없음) | — | — |
| F3-Refutation (med) | 1R F3 반박은 부당 — 「2R 수리(L700)에서 T∧¬G 로 고친 것」이 지적이 옳았음을 증명 | **반박** | 전제가 사실과 다르다: 5행 `R == "closed" or (T and not G)` 는 이 티켓 **이전**부터 있었다(`git show 254bd4fa:cysjavis-pack/bin/javis_dept_request.py` 648행 — 전임 818 의 적대 2R ③ 수리 · 뮤턴트 M3). 이 티켓이 F3 에서 고친 것은 `status --all` 의 `claimed`(새 부서가 표에서 빠지는 결함)이고, 1R 반박은 「요청 A 의 행」에 대한 것이다. 단 codex 2R F3 이 지적한 닫기 요청 쪽 결함은 별개로 수용했다(아래) | — |
| F5-Regression (high) | F5 수리로 재시도가 간격 대기(`waiting_gap`)에 들어가도 7행이 「만들다 멈췄습니다. 이어서 만들까요, 지울까요?」로 사람 개입을 요구 | **수용** | `say_for` 7행: `create-timeout ∧ waiting_gap` 이면 「10분이 지나면 자동으로 다시 만듭니다」 | `test_2r_agy_row7_waiting_gap_says_auto_retry` / M34 |
| Missing-FailSay (low) | `create_timeout_exhausted` 가 날것 사유로 노출 | **수용**(범위 넓힘) | `FAIL_SAY` 에 `create_timeout_exhausted` · `crash` · `target_changed` · `close_rc` 추가 · 닫기 실패 문장도 `FAIL_SAY` 를 거친다 | `test_2r_agy_fail_say_has_no_raw_reason` / M35 |

## codex 2R

| ID | 지적 | 판정 | 근거·수리 | 시험 / 뮤턴트 |
|---|---|---|---|---|
| F1 (high) | spawn 뒤 pid 기록 전 사망 → 간격·호출 수는 종료의 증명이 아닌데 10분 뒤 재호출 | **수용** | 재진입에서 pid 가 없으면(생사 불명) 등재를 먼저 보고, 없으면 hang 상한(1시간)까지 재호출하지 않는다 | `test_2r_f1_unknown_child_blocks_recall` / M36 |
| F2 (high) | discard(틱 잠금) 와 confirm(요청 잠금)이 다른 잠금 — discard 의 옛 객체가 확인을 지움 | **수용** | discard 의 상태 쓰기를 `transition(…, DISCARDABLE, …)`(요청 잠금 안 재독)으로 · 걷기는 전이 성립 뒤에만 | `test_2r_f2_discard_stale_read_keeps_confirm` / M37 |
| F3 (high) | 닫기 요청이 closed 인데 같은 키 부서가 다시 등록되면 「닫혀 있습니다」 · closed 기록이 현재 부서 행을 가림 | **수용** | 닫기 요청의 closed 문장은 G 이면 「닫았으나 지금 다시 등록돼 있습니다」 · `--all` 의 소유 주장은 생성 요청만 | `test_2r_f3_closed_menu_dept_reregistered_is_listed` / M38 |
| F4 (high) | 자기 해시 대조 뒤 교체 전 사람이 고치면 덮는다(1R 에서 남긴 창) | **수용** | 교체 분기 자체를 없앴다 — 기존 `CLAUDE.md` 는 이 요청 바이트와 같을 때만 그대로, 다르면 무엇이든 충돌(옛 실패 요청의 잔여물은 그 요청의 「지우기」로 걷는다). 1R 양성 시험은 충돌 기대로 뒤집었다 | `test_f6_other_request_generated_claude_md_is_conflict` · `test_f6_edited…` / M13·M23 재조준 |
| F5 (med) | 알림 최대 1회 완화는 C9 「전이당 1회」 위반 — outbox·재시도·수신측 중복 제거 필요 | **반박 유지 → 【결정필요】 master** | 코드 근거: `status --pending` 은 `said.json` 의 (행·상태)와 지금 판정이 다르면 다시 올린다 — 마스터는 알림 유실과 무관하게 **현재 상태**는 반드시 받는다. codex 의 지적 중 맞는 부분 = 마스터 턴 사이에 지나간 **중간 전이**(예: created→가동)는 따로 알려지지 않는다. 설계가 요구하는 것이 「전이마다」인지 「지금 상태를 놓치지 않음」인지는 계약 해석이라 워커가 정하지 않는다 | — |
| F6 (high) | 대조와 destroy 사이 번호 재사용 · 키 없는 메뉴 부서는 세 칸이 같아 교체 탐지 불가 | **범위 밖 → ISSUES B11** | 부서 세대 ID(생성마다 불변)와 destroy 의 기대 세대 원자 대조가 필요 — Rust 레지스트리·`cys-dept` 수정 | — |
| F7 (high) | `pre_ts` 는 이름 비교라 스냅샷 묘비가 해소된 뒤 GUI 가 새로 쓴 같은 이름의 묘비를 지울 수 있다 | **범위 밖 → ISSUES B11**(+ 【결정필요】) | 묘비 세대·의도 ID 는 데몬 묘비 형식 변경. codex 의 대안 「재시도 중단 + residue 보고」는 전임 2R ③(잔존 묘비 → 재시작 시 부서 reap 위험)과 맞바꾸는 결정이라 master 판단 | — |
| F8 (med) | request.json 저장 전 사망 시 원문만 남은 폴더는 청소 대상 밖 | **수용** | `_sweep` 이 기록 없는 `dr-*` 폴더의 `utterance.txt` 를 파일 시각 7일로 지운다 | `test_2r_f8_orphan_request_dir_utterance_7d` / M39 |
| F9 (med) | 원문 삭제 PermissionError 가 청소·틱 전체를 죽인다 · `save_req` 실패도 `_run_step` 밖 | **부분 수용** | `_rm` 이 `OSError` 를 항목 단위로 기록하고 계속. **남은 것**: 요청 저장(`save_req`) 자체의 I/O 실패는 여전히 틱을 끝낸다 — 저장이 안 되는 디스크에서는 어떤 상태도 영속할 수 없어 「실패로 기록」이 불가능하다(다음 틱 재시도가 유일한 경로) | `test_2r_f9_rm_failure_does_not_kill_tick` / M40 |
| F10 (med) | 원장 청소의 등록 경합 · 읽은 파일과 옮기는 파일 동일성 | **범위 밖 → ISSUES B11**(1R F13 과 같은 결함) | — | — |
| F11 (med) | kickoff O_EXCL 표지가 실행 파일 부재·timeout 에서도 남아 영구 「이미 전했습니다」 | **수용** | 보내기 시작도 못 한 `OSError` = 표지 해제 · timeout = 표지에 `uncertain` 기록 + 「전해졌는지 확인하지 못했습니다」(재발송 금지 — 중복보다 확인 요청이 안전) | `test_2r_f11_kickoff_unsent_releases_marker` / M41 |
| F12 (high) | discard 가 사람이 고친 `CLAUDE.md` 를 지운다 | **수용** | 표식이 이 요청 것이어도 자기 해시가 맞을 때만 지우고, 아니면 `kept` 로 남기고 알린다 | `test_2r_f12_discard_keeps_edited_claude_md` / M42 |
| F13 (med) | 동시 propose 둘이 둘 다 proposed 로 남는다 | **수용**(시험·뮤턴트 없음) | 새 제안 저장 + 옛 제안 교체를 제안 잠금(`.propose.lock`) 하나 안에서(`_publish`). **정직 고지**: 두 프로세스의 교차를 결정론으로 만드는 훅이 없어 이번 라운드는 시험을 세우지 못했다 | — |
| F14 (high) | 상한 검사 뒤 메뉴가 부서를 등록하면 상한 2 초과 | **범위 밖 → ISSUES B11** | 메뉴 생성(Rust/`cys-dept`)과 대화 생성이 같은 레지스트리 잠금 아래에서 정원을 예약해야 닫힌다 | — |
| F15 (med) | 간격 기준 시각이 자원 검사 전 시각 | **수용**(시험·뮤턴트 없음) | `last_create_at` = spawn 직전 `now()`. 60초 이내 오차를 재는 결정론 시험은 자원 게이트를 지연시키는 훅이 필요해 이번 라운드는 세우지 않았다 | — |
