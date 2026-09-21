# HANDOFF — v111-drain (재시작 드레인 3결함 + 확인 창 폐기)

TICKET=v111-drain · 2026-09-21 · 브랜치 `fix/v111-drain`(← rebase/v1.1 e2ca5f66) · 커밋 57879eaf, f5614919.

## 무엇이 바뀌었나

| 축 | 1.1.0(구) | 1.1.1(신) |
|---|---|---|
| 지시문 | `[DRAIN-VERIFY] 재시작 전 체크포인트 검증…` | 앞에 **오너 권한 표식**(오너가 재시작 단추를 눌러 보낸 것 · 대기/보류/정지보다 우선 · 되묻지 말고 즉시 집행) |
| 마커 자리 | `<cwd>/_round/SESSION_STATE.md`(공유) | `<cwd>/_round/checkpoint-<소켓구별자>-<surface>.md`(노드 전용) · 검증은 **전용 ∪ 레거시** |
| 미제출 판정 | 화면 어디든 sentinel 매치 → `delivery_failed` | 제출 실측 3상태(Submitted/NotSubmitted/Unmeasured) · 「입력 미제출」은 **입력창 앵커 실측**일 때만 |
| 대기 | 고정 `timeout` | 노드별 **마지막 활동(화면 변화) 기준 연장** · 하드 상한 `timeout×2` · 리포트 `max_wait_secs` |
| 확인 창 | 진입 1개 + 부분 실패 1개 | **0개** — ↻ 한 번 = 드레인 → 재시작 · 결과는 재시작 뒤 알림 1줄 |

## 재현·검증하는 법

- 단위: `cargo test --bin cys drain_verify`(27) · `cd ui && bun test src/drainverify.test.ts`(10).
- 뮤턴트: Rust 6/6 KILLED · UI 4/5 KILLED(U1 = `all_saved` 무시는 **등가 뮤턴트** — 코어가
  `all_saved ⇔ 미확인 0` 으로 계산해 두 술어가 구조상 일치한다. 방어로 남겨 둠).
- 3자리 실사격(격리 cysd · 토큰 0): 소켓은 `/tmp` 단축 경로(SUN_LEN) · `HOME` 격리 ·
  `cys new-surface --agent claude --cmd <bash 노드>` 로 좌석 3개 · 노드 스크립트가 OSC 7 로 live_cwd 를 낸다.
  결과 = `all_saved=true` · 3/3 · 파일 3개 분리 · 공용 SESSION_STATE 마커 0 · 되묻기 0 · 잔존 프로세스 0.
  **대조군**(노드가 구 스킴대로 공용 파일에 기록) = 1/3 saved + 2 timeout → 09-21 결함 재현.

## 잔여 위험 · 미결

- ⚠ **CORE-MIN 미편입** — 드레인 규칙은 원문 디렉티브 3종(MASTER·WORKER·CSO) 맨 앞 1절에만 있다.
  `CORE-MIN.md` 는 1,599/1,600자로 포화라 한 줄도 못 넣었다(`test_core_inject` C82 가 초과를 FAIL).
  **훅 출력 절단이 일어나면 이 규칙이 모델에 안 닿아 되묻기가 재발할 수 있다** = 잔여 위험.
  해소하려면 CORE-MIN 기존 규칙 1~6 중 하나를 압축해야 하고 그것은 헌법 변경(박사님 게이트) — 1.1.2 후보.
- 마커 검증은 여전히 **기입 확인**이지 내용 최신성 보증이 아니다([F2] 한계 불변).
- 옛 기기(1.1.0) 호환은 **읽기**로만 성립한다 — 1.1.0 바이너리가 보내는 지시문은 여전히 공유 파일을
  지목하므로, 그 기기에서는 충돌이 그대로 남는다(해소 = 바이너리 갱신).
