# HANDOFF-input — 1.1.7 갈래 2 「입력·순환」 (TICKET=cysr-117-impl-input · master#275572ce)

- 좌석: surface:1152 · 117input(계정2) · 브랜치 `fix/117-input`(기준 1bc32693 = SPLIT 커밋 · 그 밑 v1.1.6 = 76d2b5e9)
- 착수 19:18 KST · 6항목 커밋 끝 20:20(62분) · 게이트·성찰 뒤 이 문서.
- 합치는 쪽(151 · int/117) 이 읽을 것: §1 커밋 표 · §3 겹치는 파일 · §5 남은 위험.

## 1. 커밋 표 (갈래 안 순서 = SPLIT §2)

| # | 커밋 | 무엇 | 시험(새) · 뮤테이션 |
|---|---|---|---|
| ⑮ | 40b7567e | 터미널 자동 응답(ESC[I·CPR·마우스 보고…)을 미제출 입력 계수에서 제외 — 타이핑 가드와 같은 술어 1조건 | handlers `terminal_autoreply_does_not_count_as_pending_input` · 적색 확인 |
| ⑭ | 19928670 | 계수 고착 해제 — 쓰기 세대(`input_gen`) + 빈 입력창(가로줄 사이 빈 「❯ 」 행 · framed)·출력 정적·승인 창 없음이 같은 (계수, 세대)로 quiet 초 이상 → input_gate 안 재확인 뒤 0 · 해제 틱 배달 0 · `queue.input_pending_reset` | governance `u14_*` 3 · 뮤턴트 3종 적색 |
| ④ | 3426508d · 71672c42 | 초안 게이트(draft_gate) — Text/SubmitKey/ClearFirst/CancelKey × 사람 초안·기계 잔여·화면 점유 · 사람 바이트 계수 · node-recover 사람 입력 보호 거부 = rc 79(회수 0) · GUI send_input 오류 코드 전달 · 재기동 clear_first 1회 재시도(`ui/src/restartplan.ts`) | cysd `d12_*` 6 · cys `c4_node_recover_…` · cys-app `d12_send_input_…` · ui `restartplan.test.ts` · 뮤턴트 3종 적색 |
| ③ | f7ab5a1f | `reinject --check --ack-only`(확인 전용 · 전문 0) · phoenix G2 = --ack-only + 줄 단위 ACK · 순환·node-recover 깨움 글 제출 1회 · 팩 하한 1.1.7 두 레인 | cys `u8_*` 3 · 팩 `test_phoenix_g2_ack_only.py`(CI 4루프 등재 · 뮤턴트 2 내장) · 뮤턴트 3종 적색 |
| ⑤ | 4680f0db | cycle-agent `verifier_precheck`(저장 지시 주입 전) · 82 충돌/83 증명 불가 · 지침·통지문 4곳 `--verifier worker` · CEO_TEMPLATE 재합성 · 해시 2종 재생성 · MASTER_CORE/CEO_CORE §11 절 해시 재기입 | cys `e5_*` 2 · test_ctx_relay 개정 · 뮤턴트 3종 적색 |
| ⑯ | c5888582 | send_key/send_text 옵션 `refuse_on_approval`(같은 요청 안에서 쓰기 전 판정 · 코드 `approval_screen`) · 순환 4단계 C-u·/clear·Return 에 적용 | cysd `u16_…`(claude 2.1.280 허락 창 실화면) · cys `u16_…` · 뮤턴트 적색 |

## 2. 로컬 게이트 (이 좌석 실측 · 20:2x)
- `cargo test --bin cysd` 1207 통과(전체 7회 중 1회 적색 3건 = ACL 시험 `CYS_PACK_DIR` env 경합 부류 · 재실행 초록 — 아래 §5-⑥)
- `cargo test --bin cys` 347 · `cargo test --lib` 550 · `cargo test -p cys-app --bins` 174(스텁 스테이징 = ci-branch 와 같은 방식 · 스텁은 .gitignore)
- `ui`: `bun test` 1463 통과 · `bun run typecheck` 오류 7 = **기준 커밋 1bc32693 에서도 7**(restorebrief.test.ts·updateplan.test.ts · 이 갈래 무관 · 스크래치 worktree 로 실측)
- 합성기: `gen_ceo_template.py --check` GREEN · `gen_released_directive_hashes.py --check` OK
- 팩 파이썬 루프(ci-branch 목록 57) 전부 통과 · 디렉티브 3줄 증명(gen --check · test_bootv2_doc_contract · test_event_inject) + test_core_inject · test_content_pins_parity · test_ctx_relay
- 건강 검체 `run_bootstrap_health.py` = §6 에 결과

## 3. 겹치는 파일 · 통합 주의 (SPLIT §2 규칙 대비)
- `src/lib.rs`: 상수 4개 추가(DRAFT_GATE_TAG · MSG_DRAFT_GATE_CANCEL_KEY · EXIT_RECOVER_REFUSED=79 · ERR_APPROVAL_SCREEN) — `MSG_TYPING_GUARD` 바로 뒤 · `EXIT_GATE_PENDING` 바로 뒤. 갈래 1 공용 헬퍼와 구역 다름.
- `src/bin/cysd/state.rs`: Surface 필드 3개(input_gen · pending_input_stale · pending_input_human_bytes) — `pending_input_bytes` 곁(L851 부근) + 초기화(L4122 부근). 갈래 1 구역(L3079~ · L4708~)과 떨어짐.
- `governance.rs`: 새 함수 묶음은 `pending_input_after` 뒤 · `approval_screen_now` 뒤 · 배달 틱(⑭ 배선) · `deliver_head_locked`(Inject 뒤 사람 계수 0). **Q2(갈래 1 · L6576 앞 1줄)와 겹침 없음** — 단 줄 번호가 약 +300 밀렸으니 grep 으로 찾을 것.
- `handlers.rs`: send_text·send_key 안(가드 뒤 · 원장 앞 · 계수 갱신) + 테스트. 갈래 1 구역(L7378~ · L7742~)과 떨어짐.
- `src/bin/cys.rs`: clap Reinject · run_reinject · run_boot(79 분기) · run_node_recover · boot_agent_on_surface(인자 `note` 추가 — 호출자 3곳 전부 갱신) · run_cycle_agent · 새 함수 몇 개 · 테스트. 갈래 1(L4003~4950) · 갈래 3(L11-14 · 버전 문자열 시험) 과 구역 다름.
- `src-tauri/src/main.rs`: send_input 끝부분(rpc_full) + 시험 1. `ui/src/main.ts`: import 1줄 · restartNode · 주석 3줄(L3108).
- `.github/workflows/{ci-branch,release,pack-release}.yml`: 팩 루프에 `test_phoenix_g2_ack_only \` **독립 줄**(test_event_inject 다음 줄 · 긴 끝줄은 무접촉 — 갈래 1 이 끝줄에 붙여도 충돌 없게) · release.yml L1047 · pack-release.yml L61 팩 하한 '1.1.7'(+주석 3·2줄). 갈래 3 의 Q1(L978-986 · L457-465)과 구역 다름.
- 디렉티브(갈래 2 전용): CSO_DIRECTIVE §2 · MASTER_DIRECTIVE §11 — **줄 수 불변**(줄 범위 상수 보호). 합성물은 이 브랜치에서 재생성해 커밋했지만 **int/117 병합 뒤 다시 재생성**(SPLIT §2 · 손 병합 금지): `python3 scripts/gen_ceo_template.py` · `python3 scripts/gen_released_directive_hashes.py` · MASTER_CORE/CEO_CORE 머리 주석의 `§11=` 절 해시는 `cysjavis-pack/hooks/core_inject.py` `keyed_sections()` 로 다시 잴 것(다른 갈래가 §11 을 안 바꾸면 그대로).

## 4. 9단계 성찰(갈래 완료 · 코드 성찰 기준 — 30년차 아키텍트 3원칙 × 3층위)
**① 의도(한두 문장)**: 사람이 쓰던 입력줄을 기계가 덮거나 이어 붙이거나 대신 제출하지 않게 하고(④⑭⑮), 순환·복원이 같은 좌석에 같은 목적 글을 두 번 넣거나 스스로 교착하지 않게 한다(③⑤⑯). 새 기능·리팩터링 0 — 원작자 수정의 **우리 판 최소 단위 재구현**이며 커밋 본문에 원작자 해시를 남겼다(다음 통째 편입 때 버릴 수 있게).

**② 영향 범위(파급) — 1층위 사실 매핑**
| 바뀐 축 | 직접 | 호출자·소비자 | 확인 |
|---|---|---|---|
| 입력 계수(⑮⑭④) | handlers send_text/send_key · governance 틱 · state 필드 | 큐 배달 틱 · pane.idle 각성(seat_input_line) · 강제 배달 | cysd 전체 · b1_* 무회귀 |
| 초안 게이트(④) | send_text/send_key 거부 | CLI `cys send`/`send-key`(문면 접두로 --queued 1회 폴백 · 기존 계약) · inject_text(폴백 있음) · node-recover(79) · cycle-agent(C-u 거부 = Err 1 · quiescing 해제) · 팩 send+Return 호출자(awaken·autopilot·verifier = 같은 CLI 폴백) · master-send.sh(C-u → 워커 좌석엔 사람 초안 없음 전제) · GUI(사람 실키 통과 · 조립 문안만) | cys 347 · 팩 57 · ui 1463 |
| 종료코드(④⑤) | 79 · 82 · 83 | run_boot(79 → skipped_unconfirmed = 기존 버킷) · 82/83 소비부 없음(사람·CSO 가 문면을 읽음) | c4 · e5 |
| reinject(③) | clap 1 · run_reinject | phoenix G2 · 팩 하한(두 레인) · 옛 팩 × 새 바이너리 = --check 불변(무회귀) | u8 · 팩 시험 |
| 디렉티브(⑤) | 문면 4곳 | CEO_TEMPLATE(재합성) · released hashes · CORE 절 해시 | 3줄 증명 + core_inject |

**③ 변경 설계 — 2층위 구조(강결합·샷건 서저리 지점, 미리 고지)**
- **문면 결박**: 초안 게이트 거부는 코드가 아니라 **문면 접두**(`MSG_TYPING_GUARD`)로 CLI 폴백을 탄다(와이어가 message 만 넘김 · 기존 계약). 이 접두를 바꾸면 폴백이 조용히 죽는다 — lib 상수 1곳이 정본. C-u 거부만 전용 문면이라 node-recover 판정에 `is_input_guard_refusal` 을 따로 뒀다(**뮤테이션으로 발견한 실제 구멍**: 없으면 rc 1 → 좌석 kill).
- **판정자 단일화**: 승인 축(`seat_approval_pending`)을 초안 게이트·⑯ 옵션이 함께 쓴다(큐 배달자와 같은 재료). 관문 코퍼스·어댑터 문면이 바뀌면 세 곳이 같이 움직인다 — 의도된 결합.
- **boot_agent_on_surface 인자 1개 추가(note)**: 호출자 3곳 · 소스 핀 시험 5개가 이 함수 본문을 본다(서명 무관 · 전부 초록).
- **결합도↓ 기회(제안만 · 미구현)**: 원작자처럼 `pending_input_bytes`·human·stale·gen 을 한 상태 구조체로 묶으면 원자성이 좋아진다 — 1.1.7 범위 밖(리팩터링 금지) → 다음 정기 편입 후보.

**④ 3층위 철학 정합성**: 박사님 범위 밖 새 기능 0 · 문구 손질 0(원작자 C-06 한국어 토스트 번역표는 v4 가 뺐으므로 옮기지 않음 · 재기동 실패 토스트는 기존 제목+원문 칸만) · 원작자 문면 가운데 **우리 판에서 거짓인 근거**(「CSO 는 feed reply 권한 없음」 — 우리 role-capability-gate 는 CSO full-trust)는 옮기지 않았다.

**⑤ 결정론 치환**: 합격 판정은 전부 명령 — 소스 핀(제출 횟수 · 분기 순서 · 옵션 동반) · 두 레인 하한 값 일치 · 줄 단위 ACK 정규식 · 원본 계수 불변.

**⑥ 적대(방어 불가·약한 지점)**: §5.

**⑦ 언어**: 코드 주석·시험 이름 = 파일 관행(한국어 주석 + 영어 식별자) 유지.

**⑧ 필요성**: 6항목 모두 v4 필수 · ⑯ 은 확신 Low(실기 재현 없음) — 최소 단위(옵션 1개 · 호출 3곳)로 한정.

**⑨ 최종**: 이 문서의 줄 번호 언급은 쓰지 않았다(구현이 줄을 밀었다 · grep 으로 찾을 것).

## 5. 남은 위험 · 판단 기록 (정직)
1. **⑭ 판단 1건**: 입력창 모양(framed)인 **대체화면**은 해제를 허용했다 — 배달 게이트 `alt_screen_blocks` 와 같은 규칙(윈 claude 좌석은 본 화면이 대체화면). SPLIT 요약 「alt-screen 이면 비해제」와 다르다 → 메뉴·대화상자 모양 대체화면만 비해제. 마커를 모르거나 가로줄 없는 어댑터(codex·gemini)는 해제 안 됨(종전 보류 유지).
2. **④ 거동 변화(의도)**: `cys send` 로 본문을 **두 번** 나눠 보낸 뒤 Return 하는 흐름은 둘째 본문이 `pending_input` 거부 → CLI 가 --queued 로 돌린다(둘째 본문은 따로 배달). 같은 계약의 원작자 판과 동일. 팩 호출자 grep 에서 두 번 나눠 보내는 곳은 못 찾았다.
3. **④ 화면 축**: 계수 0 · 화면 커서 앞 글자 = 거부(ScreenOccupied). 에이전트 자신이 입력줄에 남긴 글자(드묾)도 막는다 — 원작자와 같음.
4. **⑤**: 기본 편성에 worker 좌석이 없으면(사용자가 지움) CSO 의 master 순환이 83 으로 멈춘다(문면에 다음 행동). 기존 설치의 디렉티브는 사용자 소유라 `.new` 병치로만 닿는다(pack.rs 기존 경로 · 이 티켓 무접촉).
5. **⑯**: 실기 재현 없음(확신 Low) · 판정과 쓰기 사이 틈 = 한 요청 안(파서 락 순서 때문에 input_gate 밖). 옛 데몬 × 새 cys = 옵션 무시(보호 없음·실패 없음).
6. **시험 경합(기지 부류)**: cysd 전체 7회 중 1회, ACL 시험 3건이 동시 적색(내 d12 2건 + 기존 v116 1건) — 거버넌스 시험(QUEUE_ENV_LOCK)과 ACL 시험(ACL_ENV_LOCK)이 **다른 락으로 같은 `CYS_PACK_DIR` env** 를 바꾸는 부류(원작자 0.14.31 이 공용 락으로 고친 것 · 우리 판 미편입). 재실행 6회 초록. 게이트 러너에서 1회 적색이 나면 이 부류를 먼저 의심할 것.
7. **③ 범위**: 원작자 핑 운명 판정(세션 기록 5상태)·재주입 멱등 키는 넣지 않았다(v3 최소 단위) — 우리 `reinject_guard`(시간당 3 · 간격)가 상한. 옛 팩 × 새 바이너리의 `--check`(ACK 없으면 전문 주입)는 무회귀를 위해 그대로다.
8. **③ 팩 하한 1.1.7**: 1.1.7 미만 앱은 새 팩을 인앱으로 못 받는다(1.1.7 은 앱·팩 동시 발행 전제). pack-release 의 하한 검증기는 `v$MIN_BINARY` 태그로 빌드되므로 **v1.1.7 태그가 먼저 있어야** 팩-온리 발행이 통과한다.

## 6. 건강 검체
- `run_bootstrap_health.py`(전 검체 · 20:29~20:36 · 커밋 71672c42 트리): **GREEN — 발효 149 PASS / 0 FAIL / 1 SKIP(적용불가) / 0 OFF · 399.6s**. SKIP 1 = `SKIP H-WIN-11     W4   Windows CI 실기 재실행(부채 V4 해소) — 로컬은 잡 계약 검증`
