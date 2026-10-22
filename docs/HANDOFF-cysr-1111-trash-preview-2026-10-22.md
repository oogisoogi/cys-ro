# HANDOFF — TICKET=cysr-1111-trash-preview (2026-10-22 · worker@surface:1575)

가지 `fix/1111-trash-preview`(worktree `~/cys-terminal-src-wt/1111-trash`) ← `fix/1111-installer` 307eca98.
이월 4커밋(설치기 내용 오라클 · dist-info 정리 · 공개 릴리스 가드 · HANDOFF)은 건드리지 않았다.
push · 태그 · 판번 · 설치 · 발행 · rel/1.1.10 쓰기 · 윈 기기 접촉 = 0.

## 끝난 것

| 건 | 커밋 | 한 줄 |
|---|---|---|
| T1 | `b73fb075` | 삭제 꺼진 빌드에 「크기 미리 보기」 입구 — 윈 휴지통 미리보기가 안 나오던 원인 |
| T2 | `ff6225f5` | 세션 예산 시험을 가짜 시계로 결정론화 |

---

## T1 — 윈 휴지통 미리보기(크기 측정)가 안 나옴

### 원인(코드 읽기 · 확신도 높음 · 데몬 원인 아님)

- 미리보기(크기 측정)를 여는 입구는 **「고른 항목 삭제」 단추 하나**였다:
  `ui/src/main.ts` 의 `btn-cc-trash-delete` 클릭 → `trashDeleteFlow` → `trashConfirmModal` → `trash_preview_start`.
- 그 단추는 `delete_supported=false` 이면 꺼진다: `trashSyncDeleteButton` 의
  `btn.disabled = trashDeleting || !supported || n === 0;`.
- `delete_supported` 는 lib `trash_delete_supported()`(`src/lib.rs:3369`)가 정본이고, **윈 + `trash_win_validated` 꺼짐**
  일 때만 false 다(맥은 항상 true).
- 목록(`trash.list` · `src/bin/cysd/trash.rs` `list_payload`)은 걷지 않으므로 크기는 캐시에 있을 때만 숫자다.
  ⇒ 윈 출하본에서는 미리보기에 닿을 길이 0 이고, 크기 칸은 영구히
  「크기 미측정 — 미리보기에서 측정합니다」(`ui/src/trashconfirm.ts` `trashSizeText`)로 남는다 — 그 문구가 가리키는
  미리보기가 없는 모순.
- 박사님 실기(배너 · 단추 흐림 · 파일 보존 정상)와 정확히 맞는다: 흐림이 정상이므로 미리보기도 열리지 않은 것이다.
- 맥 = 삭제 켜짐이라 증상 없음. `CYS_TRASH_DELETE=off` 킬스위치는 `list` 의 `delete_supported` 를 바꾸지 않으므로
  맥 실물로는 재현되지 않는다 — 원인 논리는 플랫폼 공통(화면이 payload `delete_supported=false` 를 받으면 같다).
- 1.1.10 윈 실기표 V1(`docs/release-1110/WIN-FIELD-1.1.10.md:75`)은 「목록·미리보기 동작 · 삭제 거부」를 기대했다
  — 설계 기대와도 어긋나 있었다.

### 수리(master#84adde96 결정 A · 문안 원문 그대로)

- 새 단추 「크기 미리 보기」(`ui/index.html` · 기본 `hidden disabled`). 보임 판정 = 순수 함수
  `trashPreviewOnlyVisible(deleteSupported)` = `!deleteSupported` ⇒ **삭제 켜진 빌드(맥)에서는 보이지 않는다**(시험 고정).
- 모달 미리보기 전용 갈래(`trashConfirmModal(names, previewOnly = true)`):
  제목 = 「크기 미리 보기」 · 닫기 = 기존 「닫기」 문구 · 입력칸·「삭제」 단추 숨김 ·
  결과 위 한 줄 「이 판에서는 휴지통 비우기가 꺼져 있어서 크기만 보여 드려요. 파일은 그대로 남아 있습니다.」 ·
  거부 사유는 기존 문구(`trashRefusalText`) 그대로. 이 갈래는 nonce 가드·타이핑 열기보다 **앞에서** 끝난다(삭제 명령 0).
- 닫은 뒤 목록을 다시 읽는다 — 미리보기가 끝나면 데몬이 크기 캐시를 쓰므로(`size_cache_flush`) 목록 크기 칸이 잰 값으로 바뀐다.
- 무변경: 「고른 항목 삭제」 흐림 판정(함수 본문을 바이트로 시험에 핀) · 배너 · 삭제 흐름 · 데몬 · 네이티브(tauri).
- 손댄 구조 1건: 항목 줄 조립을 `trashEntryLines` 로 떼어 삭제 모달과 공유(`trashModalLines` 출력 불변 — 시험이 대조).
  `trashConfirmModal` 안의 「잰 항목 → 모달 항목」 조립을 `trashMeasuredEntries` 로 떼었다(같은 값).
- 바뀐 기존 시험 1건: 「패널 단추는 삭제 하나」 → 「삭제 하나 + 크기 미리 보기 하나」(Q2 금지 단추 검사는 그대로).
- 남는 작은 사실(정직): 윈에서 미리보기가 ready 로 끝나면 네이티브가 단회 확인(confirm_nonce)을 발급한다
  (`trash_issue_typed_gate` — 네이티브 무변경 조건). 화면은 그것을 쓰지 않고, 네이티브가 수명(TTL)으로 버린다. 데몬의
  확인 레코드도 같다(`delete` 는 윈에서 어차피 거부).

### 1.1.11 윈 실기 확인 절차(V1 칸 · 박사님 손 · ⛔워커 접촉 0)

1. 1.1.11 후보를 설치한 시험 좌석에서 Control Center → 「휴지통」 탭.
2. 기대: 삭제 꺼짐 배너 · 「고른 항목 삭제」 흐림(1.1.11 이전과 같음) · 그 왼쪽에 **「크기 미리 보기」 단추가 보이고 흐림**(고른 항목 0).
3. 항목 하나의 체크박스를 고른다 → 「크기 미리 보기」가 켜진다(「고른 항목 삭제」는 계속 흐림).
4. 「크기 미리 보기」를 누른다 → 모달 제목 「크기 미리 보기」 · 스피너와 「확인하는 중… 노드 N · S초」.
5. 끝나면: 맨 위 「이 판에서는 휴지통 비우기가 꺼져 있어서 크기만 보여 드려요. 파일은 그대로 남아 있습니다.」 ·
   그 아래 항목 줄(크기 · 개수 · 시점 · 안에 있는 것). 입력칸·「삭제」 단추 **없음** · 단추는 「닫기」 하나.
   (내용이 10분(600초) 안에 바뀐 항목은 기존 거부 문구 「이 항목이 방금 쓰였습니다(또는 판정할 수 없습니다) — 지우지 않았습니다.」가
   나온다 — 그 경우 크기 줄 대신 그 문구가 보이는 것이 정상이다. 10분 넘게 지난 항목으로 본다.)
6. 「닫기」 → 목록의 그 항목 크기 칸이 「크기 미측정 — …」에서 **「<크기> · <N>개 항목」** 으로 바뀐다.
7. 파일 보존: 전후 `Get-ChildItem -Recurse <휴지통 뿌리> | Measure-Object` 수가 같다.
8. 통과 기준: 2~7 전부. 2에서 새 단추가 안 보이면 = 이 커밋이 번들에 없다(빌드 출처 확인).

---

## T2 — 시간 의존 시험 플레이크

### 원인

`cysd` `trash::tests::a_name_set_whose_session_budget_runs_out_ends_the_job_instead_of_showing_a_preview` 는
⑴예산 없이 한 번 걸어 이 기계의 순회 시간 `whole` 을 재고 ⑵`whole / 2` 를 예산으로 두 번째 순회를 시켰다.
두 순회의 속도는 같다는 보장이 없다 — 첫 순회는 차가운 캐시, 두 번째는 데워진 캐시이고, 전체 병렬 실행에서는 첫 순회만
부하에 걸려 느려질 수도 있다. 두 번째가 첫 번째의 절반보다 빨리 끝나면 예산 안에 끝나 `Done` 이 나온다.
현장 메시지 「shown 0 · refusals 1」은 그 `Done` 에서 방금 만든 파일 3,000개 항목이 recent(600초)로 거부된 모양과 정확히 같다.
(아래 뮤턴트 ⑶ — 가짜 시계를 우회해 실제 시계만 쓰면 **같은 메시지**로 적이 된다.)

### 수리(시험 약화 0 · 운영 동작 0 변화)

- `src/bin/cysd/trash.rs` 에 `session_now()` — 운영에서는 `Instant::now()` 그대로. `#[cfg(test)]` 에서만 **스레드 지역**
  가짜 시계(`FAKE_SESSION_CLOCK` = (다음 시각, 걸음))가 걸려 있으면 읽을 때마다 1 걸음 흐른 값을 준다.
  스레드 지역이라 병렬 시험·배경 잡 스레드는 실제 시계 그대로다.
- 세션 마감 판정 네 자리만 `session_now()` 로 바꿨다: 항목 시작 전(`certify_names_into`) · 디렉터리 머리 · 자식 루프 간격
  (`TRASH_CERTIFY_BUDGET_CHECK_NODES` = 128 노드마다) · 루프 뒤. 항목별 상한(`TRASH_CERTIFY_MAX_SECS`)의 `t0`·양보 간격은
  실제 시계 그대로다(운영에서는 같은 값이고, 시험에서는 만료가 먼저 걸려 그 판정까지 가지 않는다).
- 검체: 걸음 1초 · 마감 = 시작 + 1.5 걸음 ⇒ 읽기 0(항목 시작 전) 통과 · 읽기 1(디렉터리 머리) 통과 · 읽기 2(자식 루프 첫 간격
  = 128번째 노드) 만료. 기계 속도와 무관하게 「순회 도중」 만료다.
- **강화** 1건: 만료 경계가 항목 뿌리가 아닌 **항목 안의 자식 경로**임을 단언 — 항목 시작 전 검사나 루프 뒤 검사로 끝나면 적
  (이 두 검사는 경계를 항목 뿌리로 적는다). 종전 단언(결말 `SessionExpired` · 코드 · 단계 `Failed` · 결과 없음 · 거부 코드)은 그대로.
- T1 과의 관계: 같은 기능(휴지통 미리보기)이지만 층이 다르다(T1 = 화면 배선 · T2 = 데몬 시험의 시계) — 원인은 이어지지 않는다.

### 뮤턴트(전부 적 → 복원 뒤 녹)

| # | 바꾼 것 | 결과 |
|---|---|---|
| ⑴ | `certify_names_into` 의 「세션 만료면 잡 종결」 갈래를 끔(항목 거부로 처리) | 적 — 「예산을 넘긴 순회가 Done 으로 끝났다(= Ready) — shown 0 · refusals 1」 |
| ⑵ | 자식 루프 안 세션 마감 검사를 끔 | 적 — 「순회 도중이 아니라 항목 경계에서 끊겼다」(새 경계 단언) |
| ⑶ | 가짜 시계 우회(`#[cfg(any())]` = 실제 시계만) | 적 — 현장과 같은 「shown 0 · refusals 1」 |

### 남은 위험(범위 밖 · 고치지 않음 · 보고만)

같은 묶음의 이웃 두 검체도 실제 시계를 쓴다 — 여유가 커서 이번에 적이 관측되지 않았을 뿐이다:
- `a_budget_that_runs_out_inside_one_directory_refuses_instead_of_certifying` — 마감 50 ms · 노드당 500 µs 지연 384 노드.
  마감 계산과 디렉터리 머리 검사 사이가 50 ms 를 넘으면(극심한 부하) 경계가 항목 뿌리가 되어 적.
- `a_tree_smaller_than_the_check_cadence_still_cannot_certify_past_the_budget` — 마감 4 ms. 머리 검사에서 만료돼도 경계가
  같은 항목 뿌리라 단언은 녹으로 남는다(적은 아니지만 「루프 뒤 검사가 잡았다」는 주장을 증명하지 못하는 실행이 생길 수 있다).
같은 `FAKE_SESSION_CLOCK` 으로 결정론화할 수 있다 — 필요하면 별 티켓.

---

## 검증(숫자)

| 항목 | 결과 |
|---|---|
| cargo `--lib --bin cys --bin cysd` 전체 병렬 1회차 | lib 1101 pass · 0 fail(2 ignored) · cys 627 pass · 0 fail · **cysd 2703 pass · 1 fail**(`trash::tests::c4_a_deleted_root_is_reported_missing_not_changed` — 아래 【별건】) |
| 2회차 | lib 1101/0 · cys 627/0 · **cysd 2704 pass · 0 fail**(9 ignored) |
| 3회차(cysd 만) | **cysd 2704 pass · 0 fail**(9 ignored) ⇒ **2·3회차가 연속 실패 0** |
| T2 검체 단독 반복 | 30/30 녹 |
| `trash::` 모듈 병렬 반복 | 5/5 녹(T2 직후) · 25/25 녹(c4 재현 시도) |
| ui `bun test` | 3184 pass · 85 skip · 0 fail(98 파일 · 3269) |
| ui `tsc -p tsconfig.check.json` | rc 0 |
| `sh scripts/win-typecheck.sh` | rc 0 · 판정 0(오류 0) · 경고 65 — trash.rs 경고는 `:1057 execute_one` dead_code 1건(이 가지 전부터 있던 것) |

정직 고지: cargo 1~3회차는 T2 커밋을 amend 하기 **전** 트리에서 돌았다. amend 차이는 `thread_local!` 위의 `///` 주석을
매크로 안 static 위로 옮긴 것 하나(첫 win-typecheck 가 `trash.rs:349 unused_doc_comments` 로 잡은 내 경고)이고 코드 의미는 같다.
amend 뒤 T2 검체 녹 · win-typecheck 재실행 rc 0(경고 66 → 65)을 확인했다.

### 【별건】 c4 검체 병렬 경쟁(범위 밖 · 고치지 않음)

- 1회차의 적: `c4_a_deleted_root_is_reported_missing_not_changed` 가 `trash.rs:3257`
  (`assert_eq!(v["error"]["code"], "trash_root_missing")`)에서 panicked. 2·3회차·trash:: 반복 30회에서는 재현 0.
- 이번 변경과 무관(근거): 이 검체는 `delete`·`certify_names(…, None, …)` 만 부른다 — 세션 마감이 `None` 이라 `session_now()`
  를 한 번도 읽지 않는다. 검체 자체는 `fa5e3790`(1.1.11 후보 C4 · 이 가지 시작점 307eca98 이전)에서 들어왔다.
- 추정 원인(코드 읽기 · 확신도 중 · 실패 메시지 원문은 grep 필터로 놓쳐 미확보): 이 검체는 전역 `confirms()` 맵에 확인 레코드를
  넣고 `delete` 를 부르는데 **`PREVIEW_TEST_SERIAL` 을 잡지 않는다**. 같은 시각 다른 검체의 `reset_state_for_test()` 가
  `confirms()` 를 비우면 `delete` 는 `confirms().remove(cid)` 에서 못 찾고 `confirm_expired` 로 돌아온다 ⇒ 3257 단언 적.
- 제안(별 티켓): 이 검체 머리에 `let _g = PREVIEW_TEST_SERIAL.lock()…` 를 두고, `reset_state_for_test()` 를 부르는 검체도 모두
  같은 자물쇠를 잡는지 대조(뮤턴트 = 자물쇠 제거 + 경쟁 주입 훅으로 적 확인).

## 함정

- 이 worktree 에는 처음에 `ui/node_modules` 가 없어 `tsc` 가 모듈 부재로 실패한다 — `cd ui && bun install --frozen-lockfile` 뒤 rc 0.
- 셸에 `cargo` 가 PATH 에 없을 수 있다 — `export PATH="$HOME/.cargo/bin:$PATH"`.

## 증류

- `feedback_cysd-trash-session-clock-seam`(팩 메모리 · 가짜 시계 패턴 + thread_local! 주석 함정)
- `feedback_cysd-trash-c4-confirms-race`(팩 메모리 · c4 경쟁 추정 · 확신도 중)
- 스킬 수확: 대상 없음(도구 5회+ 막힘 돌파에 해당하는 새 절차 없음).
