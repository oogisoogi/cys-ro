# HANDOFF — TICKET=dept-impl-A1-2b (대화로 부서 만들기 · 이종 1R·2R 반영)

- 작성: worker-3@surface:819 · 2026-09-18 22:1x · 전임 818(A1-2) 후임
- 워크트리 `~/axdev/.wt/cys-v110-dept` · 브랜치 `fix/v110-dept`
- ★후임 최소 읽기 = 이 파일 + `docs/REVIEW-TRIAGE-A1-2.md`(1R·2R 심사표 — 판정·근거·시험·뮤턴트 대응표가 전부 거기 있다). 전임 `HANDOFF-A1-2.md` 는 §7 함정만 다시 볼 것.

## 1. 커밋

| 커밋 | 내용 |
|---|---|
| `521ed966` | 1R 반영(agy F1 + codex F1~F17 심사 · 수용 13 · 부분 4 · 범위 밖 1) · 시험 27→46 · 뮤턴트 17→34 |
| (다음 커밋) | 2R 반영(agy 2 수용 · codex 수용 10(부분 1 포함) · 범위 밖 4 → B11 · 반박 유지 1) · 시험 46→55 · 뮤턴트 34→43 |

## 2. 상태(실측)

- `python3 -W ignore -m unittest tests.test_dept_request`(bin 폴더) → 55건 OK(약 47초)
- `python3 tests/mut_dept_request.py` → 43종 = 42 KILLED + M7a 예상 생존(층 방어) · `MUTANTS ALL-KILLED`(2026-09-18 22:37 실측 · 약 30분 · 백그라운드 필수 — 포그라운드 10분 상한)
- self-test PASS · 팩 계약 5종 OK · cargo schedule 33/33 · factory_reset 30/30(Rust 무변경) · 비밀 스캔 2종 clean
- T0 감시 = pid 55470(자기 세션 · 23:23 종료) · 로그 `~/.cys/pack/round/_reviews/dept-A1-2/t0_watch.log`

## 3. master 결정 대기(【결정필요】 2건 — 워커가 정하지 않는다)

1. **알림 계약(codex 2R F5)**: 지금 = 「최대 1회 + `status --pending` 이 현재 상태를 받친다」. codex 요구 = 「전이마다 정확히 1회(outbox·재시도·수신측 중복 제거)」. 차이 = 마스터 턴 사이에 지나간 **중간 전이**가 따로 알려지느냐.
2. **묘비 해소 재시도(codex 2R F7)**: 지금 = 첫 호출 전 스냅샷에 있던 **이름**만 재시도. codex 대안 = 세대 ID 계약 전까지 재시도 중단 + residue 보고 — 전임 2R ③(잔존 묘비 = 재시작 시 부서 reap 위험)과 맞바꾸는 결정.

## 4. 범위 밖 → ISSUES B11(master 등재 · 레지스트리·편성 원장 쓰기 측 공통 잠금 또는 세대 검증 · cys-dept 수정 동반)

1R F13 · 2R F6(닫기 대상 세대) · F7(묘비 세대) · F10(원장 청소 경합) · F14(메뉴 생성과 상한 원자성)

## 5. 함정(이번 라운드에서 새로 밟은 것)

- **벨트를 더하면 옛 시험이 공허해진다**: 1R F5(재호출도 간격 검사)가 옛 `test_no_recall_while_first_child_alive` 의 생존 축을 가려 M9 가 생존했다 → 간격 0 으로 축 격리. 새 검사를 재진입 경로에 넣을 때마다 그 경로의 옛 시험이 무엇을 재는지 다시 볼 것.
- 하위 프로세스 틱을 죽이는 시험은 자식이 로그를 쓰기 **전**에 죽이면 계수가 0 이 된다 → 「첫 자식 기동」 대기 후 kill.
- `TestReviewR2` 는 `TestReviewR1` 을 상속하고 상위 시험을 `None` 으로 지운다(헬퍼 재사용 · 중복 실행 없음).
- 뮤턴트 앵커는 수리가 문장을 바꾸면 조용히 죽는다(M13·M20·M23 두 번 재조준) — 하네스 시작 전에 전 앵커 `count == 1` 을 먼저 찍어 볼 것.
