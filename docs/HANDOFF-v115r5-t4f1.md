# HANDOFF — v1.1.5 11차 짝 T4(복원 카드 참말화) · F-1(부서장 첫 지시 「이상징후」 오경보) · TICKET=v115r5-t4f1

- 브랜치 `fix/v115r5-t4f1` ← f29bb0a5(10차 태그 9d695ec8 + HANDOFF 문서 2커밋) · 작업 좌석 surface:1015
- 입력: 브리프 `~/axdev/master/briefs/2026-09-23-v115r5-t4f1-card-anomaly.md` · VM r3 보고서 §1·§2 곁 ⑴·§4 곁 ⑴·§5
- master 판정: master#6094b7bd(원인표 수용 · F-1 수리 자리 = 데몬 기록부 승인 · 조건 ①② · T4 신호 승인)
- ⛔판번 bump 0 · git push 0 · 태그 0 · VM·라이브 접촉 0 · 짝 티켓 1013 영역(main.ts ↻ 결과 알림 · drainverify.ts · main.rs 복원 판정 · cys.rs · javis_boot_node.py) 무접촉

## 1. 원인표

| 결함 | 원인(파일:행 · 기준 9d695ec8) | 등급 |
|---|---|---|
| T4 첫 기동에도 카드 | `ui/src/main.ts` maybeShowRestoreBrief(7397) = 복원 시작·끝·유예 15초만 봄 → 복원이 없어도 유예 뒤 무조건 표시(8311-8315) · 복원이 있으면 끝난 뒤 표시(7797-7800). 「첫 기동」 축 부재 | 【관측·코드】 |
| T4 (곁) 새 설치도 복원이 돈다 | `src-tauri/src/main.rs:3361-3375` decide_pending_update — 스탬프 부재 + 팩 존재 = Apply → spawn_org_restore. 설치기가 팩을 먼저 깔면 새 설치가 이 갈래 | 【추정】(VM s1 화면과 합치 · 1013 영역이라 무수정 · 1.1.6 후보) |
| T4 빈 문장 | `ui/src/restorebrief.ts:188`「정리된 작업 기록을 찾지 못했습니다」 · `:198-199`「기록한 시각을 알 수 없습니다」 · `:202` 제목이 기록 유무 무관 「하던 일을 복원했어요」 | 【관측·코드】 |
| F-1 거짓 이상징후 | 지시문 주입 `src/bin/cys.rs:1967`(inject_text)·`:13981`(inject_text_on)이 본문을 클라이언트에서 `ESC[200~ … ESC[201~` 로 감싸 보냄 → 데몬 `handlers.rs:3824` → `delivery.rs` record_full_with 가 틀 포함 원문을 해시·조각 기록 → 받는 claude 프롬프트엔 틀이 없어 ⑴전문 해시 불일치 ⑵첫·끝 줄 조각 불일치 ⑶줄 사이 공백 때문에 조각 구간이 합쳐지지 않아 가장 긴 한 줄(583자)이 「연속 구간」 → `javis_mission.py:1512` substr → `delivery_substring` | 【관측·모의】 실 판정 함수로 VM 숫자(583자) 재현 |
| F-1 대조군 | 데몬이 스스로 감싸는 큐 경로(`state.rs:4489` Inject)는 틀 없는 원문으로 기록 → 정상 | 【관측·코드】 |

판정 자체(기계로 접음)는 수리 전에도 옳았다 — 거짓 경보만 났다. 부수 발견: 수리 전에는 **틀을 씌운 한 줄짜리 기계 배달**이 층1 에서 통째로 안 보였다(시험 ⒞ 가 기준선에서 적색 — 전문도 조각도 틀 포함 해시라 어떤 프롬프트와도 안 맞음). 이번 수리로 같이 닫혔다.

## 2. 수리

- T4 (`ui/src/restorebrief.ts` · `ui/src/main.ts`)
  - `isFirstLaunch(savedLayoutRaw)` — 화면 배치 저장본(localStorage `cys-layout-v2`)이 적재 시점에 **없으면(null)** 첫 기동. 키 이름은 v1.0.0·v1.0.2·현행 동일(git show 대조) · render()→saveLayout() 이 첫 화면에서 즉시 저장 → 한 번이라도 켜진 기기엔 반드시 있다. 읽기 실패(undefined) = 모름 → 첫 기동으로 단정하지 않는다.
  - `briefTiming` 에 `firstLaunch` → `"skip"`(복원 신호·유예 무관). 종전 시점 규칙(복원 끝까지 대기 · 기록이 몇 초 늦게 저장되는 사례)은 그대로.
  - `buildBriefCard` — 기록이 없으면 「지난 작업 기록/찾지 못했습니다」 절 삭제 · 꼬리말 빈 값 · 제목 「다시 켜졌어요」(「하던 일을 복원했어요」 빼기). 기록이 있으면 종전 카드 그대로.
  - main.ts: 저장본 적재 지점에서 스냅숏(`briefGate.firstLaunch = isFirstLaunch(savedRaw)`) · 꼬리말 빈 값이면 그리지 않음. ↻ 결과 알림(restore-progress 수신부) 무접촉.
- F-1 (`src/bin/cysd/delivery.rs`)
  - `strip_outer_paste_frame` — 맨 앞 `ESC[200~` 1개 + 맨 끝 `ESC[201~` 1개가 **정확히 짝이고 안쪽에 두 표지가 없을 때만** 벗긴다(master 조건 ①). 안쪽에 섞이면 아무것도 벗기지 않고 원문 기록 → 불일치 유지.
  - `record_full_with` 첫머리에서 적용 — 전문·조각·preview·chars 가 모두 「받는 쪽이 받는 글」 기준. 판정 규칙(mission_gate·javis_mission)·팩 디렉티브·문턱 무변경.

## 3. 진리표·시험·뮤턴트

커밋: 제품 793c421c · 시험 349b6444 · 문서(이 파일).

### 3-1. T4 진리표(판정 = restorebrief.briefTiming · isFirstLaunch)

| 상황 | 저장본(적재 시점) | 복원 신호 | 판정 | 카드 문안 |
|---|---|---|---|---|
| 새 설치 첫 기동 | 없음(null) | 무관(백엔드가 Apply 로 복원을 돌려도) | skip | 없음 |
| 갱신·재시작 · 복원 진행 중 | 있음 | 시작 · 미종료 | wait | — |
| 갱신·재시작 · 복원 끝 | 있음 | 시작 · 종료 | show | 기록 유무에 따라 아래 두 줄 |
| 복원 없는 재시작 | 있음 | 없음 · 유예 15초 경과 | show | 〃 |
| 저장본 읽기 실패 | 모름(undefined) | — | 종전 규칙(첫 기동으로 단정 안 함) | 〃 |
| 기록 없음 | — | — | — | 제목 「다시 켜졌어요」 · 「다시 켜진 창」 절만 · 꼬리말 없음 · [닫기] 1 |
| 기록 있음 | — | — | — | 종전 그대로(「하던 일을 복원했어요」 · 3절 · 기준 시각) |
| 기록이 몇 초 늦게 저장 | — | 복원 끝까지 wait(종전 :211 규칙 유지) | — | 복원 끝난 뒤의 기록으로 조립 |

### 3-2. 시험·기준선·뮤턴트

| 축 | 시험 | 기준선 9d695ec8 | 수리본 |
|---|---|---|---|
| T4 | `ui/src/restorebrief.test.ts` 「v115r5 T4」 7건 | 5 적색(첫 기동 판정 · skip · 빈 문장 0 · 아는 것만 · 배선) · 2 초록(종전 시점 규칙 · 기록 있음 카드 = 회귀 가드) — 기준선엔 isFirstLaunch 가 없어 「항상 false」 자리표만 덧대 행동 적색을 쟀다 | 43/43 초록 |
| F-1 | `cargo test --bin cysd f1_` 4건 | 벗기기 호출 제거(= 기준선 기록 경로) 시 ⒜·⒞ 적색 | 4/4 초록 |

| 뮤턴트 | 결과 | 귀속(적색 시험) |
|---|---|---|
| T4-M1 첫 기동 skip 줄 삭제 | KILLED | 첫 기동이면 … skip |
| T4-M2 isFirstLaunch 상시 false | KILLED | 첫 기동 판정 = … null 일 때만 |
| T4-M3 빈 값도 첫 기동 | KILLED | 〃 |
| T4-M4 기록 없음 꼬리말 복귀 | KILLED | 기록이 없으면 빈 문장 0 |
| T4-M5 제목 무조건 「복원했어요」 | KILLED | 빈 문장 0 · 아는 것만 |
| T4-M6 스냅숏 배선 삭제 | KILLED | 배선 |
| T4-M7 스냅숏을 render 뒤 재독으로 | KILLED | 배선 |
| F1-BASE 벗기기 호출 제거 | KILLED | ⒜ framed_directive · ⒞ unregistered_text |
| F1-M1 전역 치환(안쪽 표지까지 제거) | KILLED | ⒝ inner_paste_marker |
| F1-M2 안쪽 표지 가드 삭제 | KILLED | ⒝ · 틀 단위 시험 |
| F1-M3 앞 표지만 벗김 | KILLED | 틀 단위 시험 |

### 3-3. 전체 회귀(수리본 · CYS_NO_AUTOSTART=1 · 설치본 cys 를 PATH 에서 뺌)

| 단계 | 결과 |
|---|---|
| cargo build -p cys-terminal --bins | rc 0 |
| cargo test --lib -- --test-threads=1 | 534 통과 · 0 실패 · 1 ignored |
| cargo test --bin cysd -- --test-threads=1 | 1044 통과 · 0 실패 · 1 ignored |
| cargo test --bin cys -- --test-threads=1 | 282 통과 · 0 실패 |
| bun test(ui · 절대경로 ~/.bun/bin/bun) | 1108 통과 · 0 실패 |
| 타입검사(bun x tsc 7.0.2 -p tsconfig.check.json) | rc 1 · 7건 = 기준선 사본 7건과 집합 동일(신규 0). 기준선 7건은 생성 파일 누락이 아니라 실제 적색(작업트리도 같은 7건 · 전부 시험 파일 타입 정의 공백 toMatch·require·__dirname) |
| 팩 python(ci-branch 맥 루프 49종 + IG-35 3종 + todo_decl + detect·mission self-test) | 56단계 전부 rc 0 |
| gen --check | GREEN(구판 축 skip = 이 작업트리의 기존 동작 · 일반 PATH 에서도 동일) |
| secret-scan --all | clean(1089 파일) |
| 건강 검체 run_bootstrap_health.py --json | GREEN · 149 통과 · 0 실패 · 1 skip(H-WIN-11 윈 실기 CI 전용) |

정직 고지: 첫 회귀 스크립트에서 bun·tsc 단계가 PATH 에 bun 이 없어 rc 127 로 **아무것도 재지 않았다**(master 22:15 감독 적발). 절대경로로 다시 돌려 위 값을 실측했다. 이 과정에서 새 배선 시험이 기존 관용구(require·__dirname)로 타입 오류 3건을 더한 것을 발견해 무오류 관용구(node:fs + import.meta.url)로 바꿨고, T4 뮤턴트 7/7 을 다시 돌려 유지를 확인했다.

## 4. 재현 명령

- T4: `cd ui && bun test src/restorebrief.test.ts`
- F-1: `cargo test --bin cysd f1_ -- --test-threads=1`
- 모의(F-1 원인 재현 · 저장소 밖): 실 판정 `javis_mission.machine_origin` 에 CEO_TEMPLATE.md 를 틀 포함/미포함으로 기록한 원장을 먹여 비교 — 틀 포함 = substr · 583자 · delivery_substring / 틀 없음 = 전문 일치 · 이상징후 0.

## 5. 4군 점검
- ① 폭주 큐: 카드는 켜질 때 1회(restoreBriefShown) · 첫 기동은 skip 으로 0회. 원장 기록 수리는 배달 수·주입 횟수를 바꾸지 않는다(기록 내용만). 해당 없음.
- ② 무clear 100%+: 해당 없음(컨텍스트·순환 경로 무접촉).
- ③ 자가치유 전멸: 카드 판정은 표시 여부만 바꾼다 — 실제 복원(spawn_org_restore·run_sidecar_restore)·phoenix 무접촉(main.rs 무수정). 원장 수리는 판정 규칙 무변경.
- ④ 전 pane 사망: 해당 없음(좌석 생성·종료 경로 무접촉).

## 6. 곁(1.1.6 후보 · 1013 영역)
- src-tauri/src/main.rs:3361-3375 decide_pending_update 가 새 설치(설치기가 팩을 먼저 깐 경우)를 「갱신 Apply」로 판정해 spawn_org_restore 를 도는 것 【추정】 — 이 티켓은 UI 판정으로 카드만 막았고 백엔드 복원 실행은 그대로다. master 가 1013 과 대조.
- 부수 발견(닫힘): 수리 전에는 틀을 씌운 한 줄짜리 기계 배달이 층1 에서 통째로 안 보였다(전문도 조각도 틀 포함 해시) — 무라벨이면 층2 도 통과할 수 있던 자리. 이번 기록 수리로 같이 닫혔다(시험 ⒞ 기준선 적색이 그 증거).

## 7. 종결
- agy 1R = ACCEPT(판정문 원문 ~/axdev/master/reports/cysr-115-2026-09-22/hetero-agy-v115r5-t4f1.md 1행 「VERDICT: ACCEPT」 · master#e5b2bbaa) · 통합 = 11차 통합 좌석 v115r5-cut 이 이 브랜치를 병합.
