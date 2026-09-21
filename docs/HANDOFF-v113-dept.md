# HANDOFF — TICKET=v113-dept (부서 기능 완결 · 1.1.3 트랙 P)

- 작성: worker@surface:896 · 2026-09-21 23:3x · 매듭 사유 = CTX 60% 매듭선 임박(statusline 53%) · master#643b83fd 지시
- 워크트리 `~/axdev/.wt/cys-v113-dept` · 브랜치 `fix/v113-dept`(base 11845981) · **push 안 함**(재승인 대상)
- 후임 최소 읽기 = 이 파일 + 브리프 `~/axdev/master/briefs/2026-09-21-v113-dept.md`.

## 1. 커밋(끝난 것)

| 커밋 | 내용 | 증거 |
|---|---|---|
| `9c069453` | A1 배선(스킬 `skills/dept-by-chat` · 훅 `hooks/dept-chat-inject.sh` UserPromptSubmit · 본체 `javis_dept_request.py hook-prompt` · 사람 확인 축 `human_axis`/`human_ack.json` · preflight C28 등록+timeout 5 · MASTER_DIRECTIVE 새 절 · CEO 서문 기본 길 · CEO_TEMPLATE 재합성 · CEO_CORE 해시) · A2 상한 제거(CHAT_CAP·DEPT_CAP 삭제 · 자원 hard_block 만 · 거부 대안 문장 · 간격 = 재호출 물러서기 전용 · 카드 「켜진 자리 N→N+3 · 사용량 칸」) · A4 팩 반쪽(워커·CSO 머리 블록 [DRAIN] 명령형 2줄) | test_dept_request 65/65 · 뮤턴트 M4 M5 M10 M21 M21b M22 M46 M47 M48 M49 KILLED |
| `5e4c1cb6` | master#cd94ed88: MASTER_DIRECTIVE 「기계 통지 = 할 일만 · 되묻지 않음」 절(supervisor·heartbeat·부서결과/가동·DRAIN) + §0-C origin 판독표 `supervisor` 칸 · CORE §0-C 해시 2곳 · 훅 755 | gen --check · bootv2_doc_contract · event_inject · core_inject 초록 |
| (이 커밋) | A3 착수분: `bin/javis_ctx_relay.py`(좌석 CTX ≥ 임계 → 부서 CSO 에 `[ctx-threshold]` 큐 통지 1회 · 재무장 −10%p · 낡은 값 10분 무시 · CSO 없으면 보류) + `cys-dept seed_schedule` 에 `ctx-relay-tick`(2분) 시드 · `tests/test_ctx_relay.py` 3건 | 수동 뮤턴트 3/3 KILLED(has_cso 제거 · 재무장 제거 · 신선도 제거) |

## 2. 미완(후임이 할 일 · 순서 권고)

1. **A3 증명**: 격리 cysd + 격리 부서 1개에서 좌석 CTX 모의(`cys set-status --context 65` 또는 usage 주입) → 2분 안 부서 CSO 입력줄에 `[ctx-threshold]` 도착 → CSO 가 cycle-agent 판단 관측. ⚠`cys status --json` 의 `usage.ctx_pct` 는 statusline/관측 출처라 set-status 자기보고(`status.context_pct`)와 칸이 다르다 — 모의 방법을 먼저 정하라(필요하면 decide 가 `status.context_pct` 도 읽게 확장 · 신선도 = status.age_secs).
   - 【관측】 **본부 레인도 같은 소비자 부재**다(context.threshold 소비 코드 0 · 디렉티브만). 본부 schedule 은 팩 임베드 `schedule.json`(user-owned) 또는 schedule.rs builtin 이 경로 — 어느 쪽에 넣을지 master 【질문】 필요(builtin 이면 신규 id 라 버전 범프 불요).
   - 부서 schedule 시드는 **새로 만드는 부서부터** 적용된다(기존 부서 schedule.json 은 그대로) — 기존 부서 소급 여부 판단 필요.
2. **[heartbeat] 산문 주입(893 ⓑ)**: 원인 = `src/bin/cysd/schedule.rs` builtin `phoenix-snapshot-6h`(action push → master · 할 일 없는 기계 산문). 처방 = action `command`(push 없음)로 바꾸고 `BUILTIN_JOBS_VERSION` 2→3 범프(범프는 builtin 전부를 코드 정의로 교체 — 운영자 수기 편집 소실 위험 고지) + cargo 시험(`cargo test --bin cysd schedule::` · `$HOME/.cargo/bin`). phoenix-drill-weekly 도 같은 성격인지 판정.
3. **회색 추천 문구 오독(893 ⓓ)**: master 가 `cys read-screen` 의 입력줄 회색 추천을 미제출 지시로 읽음. 팩 쪽 처방 후보 = MASTER_DIRECTIVE §0-C 귀속 판별 절에 「입력줄 글은 배달 원장·데몬 `seat_input_line` 판정으로만 — read-screen 텍스트만으로 출처 불명 지시라 보고 금지」 1줄(§0-C 해시 갱신 + 3줄 게이트).
4. **Q1 계측(윈 전용 · master#aa33c5cb)**: CSO Stop 훅 1m34s · hook-missing 문자열 — 조사 + 원인 가설 1줄 + 계측(훅 경과 시간 기록 · hook-missing 판정 근거 로그)까지만. 데몬 쪽이면 트랙 D 【질문】. 출처 = `~/axdev/master/SESSION_STATE.md` 161·163·253행.
5. **A5**: 부서 카드·알림 `dept-N` 비노출 재확인(닫기 카드만 예외 — test_card_has_no_internal_terms 존재) · `cys rotate` 부서 미순회 한 줄 = 트랙 D 결정 대기(D 가 안 넣으면 javis_dept_request 상태 문장에).
6. **격리 실측(브리프 7)**: 격리 cysd 에서 실제 claude 본부 마스터 「교육 부서 만들어 줘」→카드→「네」→1~3분 가동→「닫아 줘」→닫힘 · 부서 3개 연속 생성. ⚠훅이 격리 config 에 등록돼야 사람 축이 선다(preflight --fix C28). 실 claude 좌석 3×3 = 사용량 큼 — master 와 규모 합의 권고.
7. **agy 1R**: 커밋 뒤 detached 스냅샷 worktree 로 · `unset NODE_OPTIONS` · `agy -p` 는 본문을 -p 인자에 · `--print-timeout 15m`.
8. B11(레지스트리 공통 잠금): 이번에 손대지 않음 — 【위험】 상한 제거로 동시 생성(틱 직렬 1건/분 + GUI ＋부서)이 겹칠 수 있다. 판단 필요.

## 3. 함정

- 훅 입력 JSON 은 UTF-8 원문이다 — 시험에서 `json.dumps(..., ensure_ascii=False)` 로 보내야 셸 거름(`*부서*`)이 맞는다(ASCII 이스케이프로 보내면 조용히 무출력).
- `human_axis` 는 제안 직전 15분 안에 훅이 돌았을 때만 참 — 훅 없는 기계는 종전 확인 동작(편의 우선).
- 디렉티브 절을 추가하면 `test_event_inject` 줄 범위 상수 2곳(§2 master · CEO)이 밀린다 — 현재 336–378 / 418–460.
- §0-C 안을 고치면 `MASTER_CORE.md`·`CEO_CORE.md` 머리 해시 둘 다 갱신(`core_inject.py verify --directive` 로 확인).
- 뮤턴트 하네스는 원본을 시작 때 1회 읽지만 **시험 파일은 매 변이 실행마다 디스크에서 읽는다** — 도는 동안 test_dept_request.py 수정 금지.

## 4. 4군 점검

- ① 폭주 큐: 상한 제거로 부서 수 증가 가능 ↑ — 방어 = 한 틱 생성 1건(create 직렬 대기) · 요청마다 사람 「네」(사람 축 · LLM 자기 확인 봉쇄) · 훅 주입 5줄·세션 반복 억제(M48) · 소식 세션 1회(M49) · ctx-relay 넘김당 1회.
- ② 무clear 100%+: 부서 좌석 증가 ↑ ↔ A3 중계로 CSO 깨움 경로 신설(부서 레인 · 실측 미완) — 본부 레인은 여전히 소비자 부재.
- ③ 자가치유 전멸: 변화 없음(청소·묘비 규칙 무변경) · 새 훅은 fail-open.
- ④ 전 pane 사망: 변화 없음(집행은 데몬 틱 · 훅·중계 모두 exit 0).
