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
| 범위 밖 | 1 | codex F13 |
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
| F13 (med) | 레지스트리 재독과 원장 이동 사이 경합 · 읽은 원장과 옮기는 원장의 동일성 | **범위 밖** | 성립한다(HANDOFF §6 ③ 에 이미 「좁힘 · 닫지 못함」으로 적힌 잔여). 닫으려면 GUI 의 부서 등록(Rust `cys-dept`)과 이 청소가 **같은 잠금**을 써야 한다 — `cys-dept`(bash)·레지스트리 쓰기 쪽 수정이 필요해 이 티켓(팩 도구 1파일)의 범위를 넘는다. 피해 상한 = 원장 1개가 휴지통으로 이동(삭제 아님 · 편성 심박이 다시 쓴다). **다음 티켓**: A1-3(앱·cys-dept 쪽 작업)에 「부서 등록·편성 원장·고아 청소 공통 잠금」 항목으로 이관 제안 — master 판단 | — |
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
