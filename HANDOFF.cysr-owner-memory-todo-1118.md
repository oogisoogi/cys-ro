# HANDOFF — cysr 1.1.16 「한 번 시킨 것은 잊지 않고, 시킨 일은 밀리지 않게」 (TICKET=cysr-owner-memory-todo-1118)

> **지침(디렉티브) 바이트 변경 0** — MASTER_DIRECTIVE 에 절을 넣었다가 되돌렸다(4fb67599 · 바이트 예산 래칫 · master#0f87e12f 「지침 바이트 변경 0 유지」). 해시표 재생성 불요.
> 가지 `feat/owner-memory-todo-1118` ← integ/1116 머리 7d25c38e · 좌석 worker-ownermem(surface:2185) · push·태그·서명·발행 0.

## 0. 무엇이 바뀌었나(사용자에게 보이는 것)

| 사용자가 | 마스터가(새 동작) | 장치 |
|---|---|---|
| 「앞으로 ○○ 해 줘」(지속 지시) | 그 턴 안에 저장 + 「이렇게 저장했습니다: …」 1줄 · 다음 대화·순환·재시작 뒤에도 매 세션 시작에 실림 | `javis_owner.py rule add` → 기존 `javis_memory`(feedback_owner-rule-*.md + 색인 1줄) · `owner-desk.sh` SessionStart |
| 「지금 기억하는 규칙 보여 줘」 / 「2번 지워」 | 번호 목록(저장 순서) / 「이렇게 지웠습니다: …」 | `rule list` · `rule remove` → `javis_memory retire`(신설 · `.retired/` 이동 = 물리 삭제 아님) |
| 일을 시킴(여럿도) | 원장에 1줄씩 · 여럿이면 「이 순서로 할게요: …」(급한 것→짧은 것→받은 순) | `todo add --what … [--urgent N] [--short N] [--notify]` · `~/.cys/owner/todo.json` |
| 그날 처음 말을 검 | 답 첫 줄 「밀린 일 n건 · 가장 오래된 것 받은 지 n일(#id …)」(오너 전체 하루 1번 · 말했음이 확인될 때까지) · 사흘 넘은 일 = 「계속할까요, 미룰까요, 취소할까요?」(한 번에 5건) | UserPromptSubmit(오너 입력만 · 기계 입력 제외) · `todo keep`(= 지금부터 다시 셈 · 미룸 해제) · `defer --days N`(그날 다시 질문) · `cancel` |
| 「끝나면 알려 줘」 | 끝 표시 순간 앱 알림 1회(도구가 직접 · 실패하면 다음 훅에서 재시도 · 데몬 request-id 중복 거절) + 폰/바탕화면 = 모델이 PushNotification(`do_now` 로 그 자리에서 · 안 보내면 Stop 이 막음 · (#번호)별 정산 · 2번 일러 준 뒤 포기 기록) | `todo done` · `notify set --channel app|phone|both|off` · `--all-done on`(늘) |
| 생각 깊이 | 변경 없음 — 1.1.6 부터 좌석 env `CLAUDE_CODE_EFFORT_LEVEL=high`(master#0f87e12f 결정 1 = 현행 유지) · 매뉴얼에 「이미 높음으로 고정」 | 실측 = 설치본 1.1.14 라이브 Claude 좌석 12/12 high(`ps eww`) |
| 카톡으로 받고 싶음 | 「컴퓨터 조작으로 카톡 보내기는 불안정할 수 있어요」 1줄 안내 뒤 사용자 선택 → 기존 computer-control 길(master#0f87e12f 결정 2 · 카카오 API·새 로그인 0) | 세션 규약 줄 · USER-MANUAL §5.8 |

## 1. 바뀐 파일

- 신규 `cysjavis-pack/bin/javis_owner.py` — rule/todo/notify/hook(auto = 훅 JSON 의 hook_event_name).
- 신규 `cysjavis-pack/hooks/owner-desk.sh` — master 전용(첫 줄 역할 가드) · 안쪽 상한 8초 · fail-open · 하위 에이전트 거름은 파이썬이 사건별로(PushNotification 정산은 함).
- `cysjavis-pack/bin/javis_memory.py` — `retire --name <slug> [--reason]`(색인 잠금 안에서 찾기·읽기·이동·색인 링크 정확 일치 삭제 · 실패 롤백) · `update` 의 찾기·읽기도 잠금 안으로(retire 와 경합 시 은퇴 규칙 부활 0 · codex 2R #6).
- `cysjavis-pack/bin/javis_preflight.py` — C28 `SELFCORR_HOOKS` 에 owner-desk 4사건(SessionStart·UserPromptSubmit·Stop·PostToolUse `PushNotification`) · `HOOK_TIMEOUT_S` 4행 = 10초. Rust AWAKENING_HOOKS 무접촉(비각성 훅 = C28 단독 등록 선례).
- 신규 시험 `bin/tests/test_owner_desk.py`(35) · 뮤턴트 `bin/tests/mut_owner_desk.py`(45 · 기준선 초록 선행 확인 · 별도 작업트리 전용).
- `USER-MANUAL.md` §5.8(왕초보 말투 · 카톡 안내 · 생각 깊이 · 파일 로컬 vs 모델·푸시 전달 구분).
- Rust·UI 소스 변경 0.

## 2. 설계 판단(지시 없이 내린 것 · 근거)

1. **안전망 = 막기 최소화 + 다음 턴 이월**(master#0f87e12f 수용). 처음엔 Stop 훅 「자기 점검」을 막기로 시켰으나 실좌석 `claude -p` 에서 막기 → 빈 답 → 하네스가 「보이는 답」 강요 → **같은 표가 한 턴에 3번**. 막기는 ①「저장했습니다」인데 저장 근거 0(이번 턴 rule add · 이월된 확인 줄 · 같은 지시 재저장 모두 없음) ②이 좌석이 맡은 폰 알림 미발송 둘만(턴당 최대 2회). 확인 줄 누락·기록 0건 오너 턴(「직전 오너 입력 다시 보기」)은 **다음 오너 입력·세션 시작에서 정산**(settle_turn — 끊긴 턴 포함 · 턴 안 「보였다」 누적).
2. **지속 지시 판정 = 뜻(모델)** · 고정 낱말 사전 0. 기계 = 저장·대조·날짜·개수·보고 시점·알림 의무.
3. **오너 입력 판별** = `javis_mission.machine_origin` 재사용(실패 시 `[` 라벨 폴백).
4. **디렉티브 무변경** — 마스터 세션 주입은 CORE 요지뿐이고 바이트 예산 래칫(85,365B)이 기준선부터 넘쳐 있다(86,642B). 규약은 훅이 매 세션·매 오너 입력에 싣는다.
5. **원장 위치** = `${CYS_OWNER_DIR:-~/.cys/owner}`(팩 밖) · 규칙 = 팩 `memory/`.
6. **출력 상한** = 훅 JSON 직렬화 길이 9,500 · must(규약·점검·아침 보고) 늘 보존 · 그룹(이월·폰·질문)은 실린 것만 소비.

## 3. 검증

| 항목 | 결과 |
|---|---|
| test_owner_desk(35 · R1~R8 · 윈 경로·UTF-8 단위 포함) | 기준선 7d25c38e = 첫 17건 **17/17 붉음** · codex 2R 시험 8건 = 직전 머리 83b5d5cc **8/8 붉음** → 머리 **35/35 초록** |
| 뮤턴트 mut_owner_desk | 1차 26 → 22 처치(생존 4 = 중복 거름 2곳 단순화 · 시험 보강) · 2차 37 → 35(생존 2 = 시험 보강 후 처치) · 최종 45종 = §4 |
| 실좌석 `claude -p`(로그인 프로필 그대로 · `--setting-sources project` 로 owner-desk 훅만 · 격리 팩/원장) | u1~u5(초판) · v1·v2(1R 수리판): 지속 지시 2건 저장·「이렇게 저장했습니다」·**새 세션에서 두 규칙 모두 지켜짐(표 + 3줄 이내)** · 아침 보고 첫 줄 · 잡담 저장 0 / w1(2R 수리판): 끝 표시 → 앱 알림 1회(request-id 포함) · `do_now` 로 PushNotification 즉시 호출(CC 「터미널 활성이라 생략」 = 문서화된 동작) · 앱·폰 의무 모두 정산(sent/sent) · Stop 막기 0 |
| 팩 파이썬 전수(별도 작업트리 · 4596a2f4) | 208 중 194 rc 0 · 붉음 12 = 기준선 7d25c38e 에서도 붉은 10 + **내 결함 2(dept_tick_stdin · nowin_captured_spawns = 윈 하위 프로세스 stdin·NOWIN) → 4f5833ee 고침** |
| 팩 전수 스캔·훅·문서 계약 14본(최종 머리 4ce6a80c) | agy_door · dept_tick_stdin · pyseal_census · nowin_captured_spawns · session_start_hook · preflight_hook_body · preflight_win_hook_launcher · capgate_registration · dept_chat_inject_timeout · hook_fail_log · bootv2_doc_contract · event_inject · core_inject · t6_injection_policy = **전부 rc 0** · javis_memory --self-test ok |
| health run_bootstrap_health | 167 PASS / 2 FAIL(H-CLT-1·2 = 기준선과 같은 ID · 이 기기 python 선택 환경) |
| gen_ceo_template --check | GREEN(디렉티브 무변경) |
| cargo lib / bin cys | 1256·0·3 ign / 765·0·2 ign(통합 기준선과 같은 수) |
| cargo bin cysd | 3303 pass · 4 fail(native_publication 3 · handlers u18 1) → **단독 재실행 초록**(native 3/3 반복 · u18 1/1) = 부하 흔들림 · Rust 변경 0 |
| bun test(ui 전체) | 3747 pass · 0 fail(USER-MANUAL 거울 시험 clipath 276/0 포함) |
| tsc(typescript@7.0.2 · tsconfig.check) | rc 1 — `ui/src/main.ts:4669·4678` TS7006(2026-06-14 줄 · 이 가지 UI 무변경 = 기준선과 같은 코드) → 이 작업트리 환경 차이로 추정 · 통합 좌석 값(rc 0)과 다름 · 📌 통합 좌석 확인 |

## 4. codex

| 회차 | 판정 | 요지 | 처분 |
|---|---|---|---|
| 1R(e28a3a7b 기준) | REVISE · 9 MAJOR · 1 MINOR | 발송 실패 영구 누락 · 폰 일별 대조 없음 · 정상 확인을 거짓으로 막음 · retire 롤백 덮어쓰기 · 출력 잘림 · 윈 자식 인코딩 · 중단 시 아침 보고 소실 · retire 가 다른 색인 줄 삭제 · 설정 동시 변경 · 매뉴얼 개인정보 문구 | 83b5d5cc 전부 수리 · 논쟁점(하루 1회 범위·keep/defer 뜻·사건 잠금·뮤턴트 기준선)도 반영 |
| 2R(83b5d5cc) | REVISE · 1R #5 미닫힘 + 6 MAJOR · 2 MINOR(나머지 1R 9건 닫힘 확인) | 출력 맞춤 소비 범위 · 배치 중 종료 재발송 · 두 좌석 폰 이중 · 하위 에이전트 정산 · 아침 보고 좌석 중복 · retire/update 경합 · Stop 후속 응답 · 시험 경합 | 4ce6a80c 전부 수리 · 시험 8건(직전 머리 8/8 붉음) |
| 3R(4ce6a80c) | (§ 확인요청 시점 값) | | |

원문 = 스크래치 `codex/r1.out`·`r2.out`·`r3.out`(이 좌석 세션 스크래치 — 필요하면 HANDOFF 커밋 때 docs 로 옮김).

## 5. 남은 것 · 함정

- 윈 실기 = master 몫(이 좌석은 윈 경로·UTF-8·NOWIN 단위까지). 윈은 훅을 bash 로 돌린다(팩 공통) — bash 없으면 셸 훅 전체 미등록인 기존 한계 그대로.
- 부서 마스터(CYS_ROLE=master)에도 같은 훅이 돈다 — 원장은 기기당 하나(`~/.cys/owner`) · 아침 보고는 좌석 예약으로 오너 전체 하루 1번.
- PushNotification = Claude Code 기능 — 화면을 보고 있으면 CC 가 생략 · 폰까지는 Remote Control 연결 필요 · Bedrock 등엔 없음 · 도구가 없으면 2번 일러 준 뒤 `unsent` 로 포기 기록.
- 지속 지시를 모델이 끝내 놓치면: 같은 턴 점검 줄 → 다음 오너 입력 「다시 보기」 → (순환이면) 세션 시작 「다시 보기」 세 번의 기회 뒤엔 잃는다(뜻 판단을 기계가 대신하지 않는 설계의 한계).
- 아침 보고 「말했다」 확인은 Stop 의 마지막 답에서 「밀린 일」을 찾는다 — 보고를 앞 답에 하고 도구 호출 뒤 마지막 답에 없으면 다음 입력에 한 번 더 나올 수 있다(중복 1회 · 누락 0 쪽으로 기움).
- 팩 전수 루프·뮤턴트는 편집 중 작업트리에서 돌리지 마라(팩이 덮이거나 원복이 편집을 지운다).
- 재현: `python3 cysjavis-pack/bin/tests/test_owner_desk.py` · `git worktree add --detach <임시> HEAD && (cd <임시> && python3 cysjavis-pack/bin/tests/mut_owner_desk.py)`.
