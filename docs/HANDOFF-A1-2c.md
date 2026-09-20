# HANDOFF — TICKET=dept-impl-A1-2c (VERIFY-dept-impl-r1.md 수정 필수 표 반영)

- 작성: worker@surface:821 · 2026-09-19 07:2x · 전임 819(A1-2b) 후임
- 워크트리 `~/axdev/.wt/cys-v110-dept` · 브랜치 `fix/v110-dept`
- ★후임 최소 읽기 = 이 파일 + `docs/HANDOFF-A1-2b.md`(전전임 인계서 · 함정 §5 전부 유효 유지).

## 1. 커밋

| 커밋 | 내용 |
|---|---|
| (이 커밋) | VERIFY-dept-impl-r1.md 수정 필수 표 #1~#5 반영 · 시험 55→59 · 뮤턴트 43→47 |

## 2. 상태(실측)

- `python3 -W ignore -m unittest tests.test_dept_request`(bin 폴더) → 59건 OK(약 46~53초)
- `python3 tests/mut_dept_request.py` → 47종 = 45 KILLED + M7a·M30 예상 생존(둘 다 층 방어) · `MUTANTS ALL-KILLED`(백그라운드 실행 · 약 6분 — 이번 라운드는 이전 라운드의 「30분」보다 빨랐다, 시험 수 증가에도 불구하고. 재현성 확인 안 함)
- self-test PASS · 팩 계약 5종 OK(`test_import_guard.py` 138/138 · `test_pack_syntax_warnings` ALL PASS · `test_nowin_captured_spawns` 3/3 · `test_nowin_periodic_spawns` 2/2 · `test_contracts_ct` 16/16) · 비밀 스캔 2종 clean(`secret-scan.sh` 대상 4파일 지정 · `scan-pack-secrets.sh` 전수)

## 3. 반영 내역(VERIFY-dept-impl-r1.md 「수정 필수 표」 대응)

| # | 처방 | 반영 |
|---|---|---|
| 1 | 스키마만 어긋난 `depts.json`(`{"depts": []}`) → `RegistryUnreadable` → 지우기·원장 이동 보류 | `test_a1_2c_1_schema_mismatch_registry_holds_destruction` + 뮤턴트 `M43-schema-mismatch-lenient`(KILLED) |
| 2 | 가동 부서가 있는 create 요청에 discard → exit 7 `exists` ∧ 카탈로그·미션·CLAUDE.md 불변 | `test_a1_2c_2_discard_refuses_when_dept_exists` + 뮤턴트 `M44-discard-exists-off`(KILLED) |
| 3 | `_close_step` 예외 격리 시험(다음 틱 rc 0) | `test_a1_2c_3_close_step_crash_isolated` — **함정 있음, §5 참조**(뮤턴트 없음 · 브리프 지시대로) |
| 4 | 「부서결과」 알림 전송~저장 사이 중복 창 봉합(기록+저장 → 전송, 가동 알림과 동형) | `_notify`(:1152) 수리 + `test_a1_2c_4_result_notify_recorded_before_send` + 뮤턴트 `M45-notify-save-after-send`(KILLED) — **부작용 있음, §4 참조** |
| 5 | `docs/HANDOFF-A1-2.md` §5 T0 정직 고지 1줄 | 완료 |

## 4. ★기능 변경의 부작용 — M30 이 층 방어로 재분류됨(중요)

#4(`_notify` 수리)는 **가동 알림(`running_notified`) 벨트와 별개로 설계됐던 기존 코드**를 우연히
겹치게 만들었다. `_notify` 가 이제 자기 자신 안에서 `notified` 키를 저장하기 **전에** 전체 `r` 객체를
디스크에 쓰므로, 호출부(가동 알림 콜사이트 `:1652~1653`)가 `running_notified` 를 미리 저장해 두던
**옛 벨트가 중복 방어(redundant)** 가 됐다 — `_notify` 호출 한 번이 `running_notified` 까지 함께 실어
저장하기 때문이다.

- **실증**: 뮤턴트 `M30-running-save-after`(가동 알림 콜사이트의 선저장만 제거)가 **생존**했다. 코드 읽기로
  추정에 그치지 않고 **결합 실험**으로 확인했다 — `M30-running-save-after` 단독은 생존, **M30 + `_notify`
  내부 수리를 함께 되돌리면(M30a) 다시 KILLED**(가동 알림이 정말 중복 발송된다: `2 != 1`). 두 벨트 중
  하나만 있어도 막힌다는 뜻이라 **결함이 아니라 의도치 않은 이중 방어**로 판정했다.
- **처방**: `M30` 을 `M7a`(본부 제외 이중 벨트)와 같은 패턴으로 재분류 — killers를 빈 목록으로 바꾸고
  「예상 생존 — 층 방어」 주석을 달았다. 새 뮤턴트 `M30a-running+notify-save-after`(두 벨트 동시 제거)를
  추가해 **정말 둘 다 없으면 중복이 재현되는지**를 증명하고 이것을 진짜 킬러로 지정했다(M7/M7a 와 동형).
- ★**교훈**: 기존 벨트와 새 벨트가 같은 자원(`r`·`save_req`)을 공유하면, 새 벨트가 옛 벨트를 조용히
  흡수해 뮤턴트 하나가 "결함"에서 "층 방어"로 성격이 바뀔 수 있다 — SURVIVED 를 보면 먼저 결합 실험으로
  등가/층방어/그물없음 셋 중 무엇인지 갈라야 한다([[layered-defense-hides-each-mutation]]).

## 5. ★판단 1건 — #3 시험 메커니즘을 브리프 지시와 다르게 구현함(보고 의무)

브리프는 "`CYS_DEPT_ORG_BIN` = 없는 파일"로 `_close_step` 에 예외를 주입하라고 지시했다. **실측 결과
이 방법은 예외를 내지 않는다** — `_close_step` 은 `subprocess.run([sys.executable, org, "destroy", ...])`
형태로 `org` 를 **직접 실행하지 않고 파이썬 인터프리터의 인자로만 넘긴다**. `org` 경로가 없으면
`sys.executable` 이 "can't open file" 메시지를 내고 **rc=2 로 정상 종료**한다(예외 0 — 직접 확인:
`subprocess.run(["python3","/no/such/path","destroy"], capture_output=True)` → `returncode=2`, 예외 없음).
이는 생성 경로(`test_agy_f1_step_crash_fails_request_not_tick`)가 `CYS_DEPT_BIN` 을 `subprocess.Popen`
**argv[0]** 으로 직접 실행해 `FileNotFoundError` 를 내는 것과 다른 호출 형태다(대칭이 아니다).

**대체 구현**: 이 파일의 기존 관례(`test_2r_f11_kickoff_unsent_releases_marker`)를 따라 `subprocess.run`
자체를 몽키패치해(`"destroy" in argv` 일 때 `RuntimeError` 주입) 진짜 예외를 만들었다. 결과는 브리프가
원했던 것과 동일(`failed(crash:...)` 기록 · 다음 틱 rc 0)하나, **주입 지점이 env 변수가 아니라
subprocess.run 몽키패치**라는 점이 다르다. 뮤턴트는 만들지 않았다(브리프 지시대로 #3 은 시험만).

## 6. 이월 — HANDOFF-A1-2b 이후 유효한 것

- §5 함정 전부 유효(벨트 추가 시 옛 시험 공허화 주의 · 첫 자식 기동 대기 후 kill · TestReviewR2 상속·초기화 패턴 · 뮤턴트 앵커 재조준).
- B11(공통 잠금·세대 ID) 은 ISSUES 이관 그대로 — 이번 라운드 무접촉.
- 4군 판정표(HANDOFF-A1-2 §6) 무변경 — 이번 코드 변경(#4 알림 순서)은 4군 ①(폭주·큐 남발) 방어를 강화하는 쪽이라 표 자체는 다시 쓸 필요 없음.
- T0(§5) 은 여전히 VM 실기 없이 못 닫는다(정직 고지 1줄 추가만 · master 게이트 불변).

## 7. 다음 라운드 주의(새로 밟은 함정)

- **벨트가 같은 저장 함수(`save_req`)를 공유하면 이중 방어가 생길 수 있다** — 새 수리 전에 「이 자원을
  이미 누가 저장하고 있나」를 먼저 grep 하라(§4).
- **subprocess 호출이 `[sys.executable, <path>, ...]` 형태면 `<path>` 를 없는 파일로 둬도 예외가 아니라
  rc≠0 이다** — argv[0] 자체가 없어야(직접 실행) `FileNotFoundError` 가 난다. 예외 주입 브리프를 받으면
  호출 형태부터 확인할 것(§5).
- 뮤턴트 하네스가 도는 동안 `tests/test_dept_request.py` 를 고치지 마라(HANDOFF-A1-2 §7 재확인 — 여전히 유효).
