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

---

# 후임 2 (worker@surface:896 · 2026-09-21 23:3x ~ 09-22 00:2x · 브리프 master#12be5c62)

## 5. 커밋(끝난 것 · 전부 미push)

| 커밋 | 내용 | 증거 |
|---|---|---|
| `ef6d3ab5` | 본부 ctx-relay-base builtin(2분 · base_only · 마커 ctxrelay) + 중계가 자기보고 status.context_pct 도 판정 | cargo schedule:: 33/33 · relay 4/4 · 뮤턴트 3/3 |
| `64669e21` | B11 공통 잠금 + 세대 검증(gen · down/down-sock 울타리 9/10 · destroy --expect-gen · 닫기 카드 gen · 고아 청소 잠금 안) | test_dept_b11_lock 11/11 · 뮤턴트 8/8 |
| `bd0af1e3` | [heartbeat] phoenix 2종 push→command · BUILTIN_JOBS_VERSION 2→3(master#dc245743 — 트랙 P 단독 1회) · seed learn 버전 3 | cargo 33/33 · phoenix_e2 10/10 · 뮤턴트 2/2 |
| `1500987f` | §0-C 회색 추천 문구 1줄 + 해시 + CEO_TEMPLATE + event_inject 줄 범위 339–381 / 421–463 | 3줄 게이트 초록 |
| `14c649c0` | A3 격리 실측 결함 2 — 통지 출처 명시 · 무응답 재통지 1회(10분) | relay 9/9 · 뮤턴트 5/5 |
| `895b626c` | A5 상태 say 에 dept-N 비노출 핀 | 뮤턴트 1/1 |
| `415b7302` | Q1 Stop 훅 경과 시간 기록(hook-timing.log) | test_hook_timing 5/5 |
| `adfd0ac7` | Q1 hook-missing 판정 근거(기대 vs 등록 command) | cargo cys hook_missing 2/2 |
| `3d2db202` | agy 1R 수용 4(청소 선거름 · 윈 잠금 fail-closed · cys-hook 회전 · 재통지 실패 복원) + 검증자 역할 문구 | b11 14/14 · timing 6/6 · relay 11/11 · 뮤턴트 4/4 |

## 6. A3 격리 실측(관측 결과)
- 본부(격리 cysd · 실 claude haiku CSO+master): 모의 65% → 틱 → CSO 에 통지 도달. 옛 문구 = CSO 가 「오너 입력 중」 오독 보류 → 문구 수리 뒤 §2 ② 통보 개시 → master ack 불가(격리 폴더에 git·SESSION_STATE 없음) → 재통지로 깨어나 무응답 정책 → 검증 불가 → clear 금지·escalation(규약상 안전 분기).
- 부서(부서 모양 소켓 격리 데몬 + 시드 ctx-relay-tick · 실 claude CSO+worker): 통지 → CSO 가 워커에 매듭 지시 → 워커 저장(CYCLE-SAVED) → 재통지 → CSO 가 `cys cycle-agent --surface` 실집행 → 저장 검증 통과 → [CYCLE-VERIFY] 가 CSO 에게 옴 → CSO 가 오너 승인 필요로 오독·대기(문구 수리 3d2db202). clear 완주는 미관측.
- 부서 데몬 에뮬레이션 한계: cys-dept 를 거치지 않았다(라이브 레지스트리 보호). 부서 master 좌석 없음 → 워커 보고가 master 로 못 감.

## 7. 미완
1. **E2E(브리프 7) → 1.1.3 맥 VM 실기로 이관(master#cf08125e C 채택)** — 격리 HOME 에선 로그인이 안 따라온다(Keychain = $HOME/Library).
   **VM 실기 항목**: 실 설치본에서 본부 마스터에게 말로 부서 3개 생성 → 1개 닫기 · 손 횟수 · 카드 문구 · 상한 제거 확인 · 부서 좌석 정지선 발화.
   (관측 포인트 참고: 생성마다 카드 → 사람 「네」 1회 · 3개째도 거부 없이 생성(자원 게이트 hard_block 아닐 때) · 닫기 카드만 dept-N 노출 ·
   부서 좌석 CTX 60% 넘으면 2분 안 부서 CSO 에 `[ctx-threshold] 데몬 기계 통지` 도착 · 10분 뒤 재통지 1회)
2. 기존 cys-dept reg_* 헬퍼 4곳의 윈 msvcrt 잠금 실패 삼킴(agy ①의 기존 부분) = 범위 밖 보고만.
3. 기존 설치의 부서 schedule.json 에는 ctx-relay-tick 이 없다(새로 만드는 부서부터) — 소급 여부 미결.

## 8. 함정(추가)
- 격리 claude 좌석: 새 폴더는 신뢰 창 기본 = No → launch-agent 가 좌석을 닫는다. 이미 신뢰된 폴더를 쓰거나 창에서 Down+Return.
- HOME 격리 = Bypass 면책 창 재등장 + 로그인 소실.
- ctx-relay 모의: set-status 자기보고는 10분 지나면 낡음 → 재통지 관측하려면 다시 set-status.
- 부서 격리 데몬은 팩 폴더 이름도 pack-dept-* 여야 레인 불일치 경고가 안 난다.

## 9. 4군 점검(후임 2 변경분)
- ① 폭주 큐: 재통지 넘김당 상한 2통 · 중계 2분 틱 · heartbeat push 제거로 master stdin 주입 감소 ↓.
- ② 무clear 100%+: 본부 레인 소비자 신설 + 무응답 재통지로 CSO 깨움 경로 완성 ↓(clear 완주는 검증자 단계 문구 수리 뒤 미재관측).
- ③ 자가치유 전멸: 울타리 exit 9/10/11 은 닫기만 거부(생성·복원 무관) · 죽은 표식 무시로 번호 영구 잠김 없음 — 변화 없음.
- ④ 전 pane 사망: 새 코드는 전부 fail-open(중계·계측) 또는 닫기 거부(울타리) — 변화 없음.
