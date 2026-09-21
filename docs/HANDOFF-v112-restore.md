# HANDOFF — TICKET=v112-restore (재시작 복원 주입 · 2회 배달 · 「복원 중」 드레인 건너뜀 · cys rotate)

브랜치 `fix/v112-restore` (← 438d7113 · v1.1.1 드래프트) · 워커 surface:891 · 2026-09-21

## 커밋
| sha | 내용 |
|---|---|
| 0c44273a · 666b994e | 890(v112-wake) 공용 제출 판정기 `src/submit_probe.rs` 2건 cherry-pick(원 sha f850f6b2 · 3097c185 — master 조정: 판정기는 lib 단일 소유) |
| ededc48a | ①②③ 본 수리 — 겹친 복원 1회 배달 · 제출 실측+재제출 · 복원 가드 종결 판정 · 윈 상태 폴더 |
| d7cb7827 | claude 입력창 실측 전 주입 금지(격리 재현이 찾아낸 추가 결함) |
| 0c5ac5a8 | ④ `cys rotate` |
| (이 커밋) | 표식 쓰기 실패 경고 · 이 문서 |

## 원인(코드 특정 + 격리 대조군으로 확인)
1. **2회 배달**: 복원은 설계상 겹친다(사이드카 restore + 콜드부트 auto-restore). 두 번째 `run_restore` 의
   `run_launch_agent_opts` 가 같은 멱등키로 `surface.create` → 데몬 create_idem(TTL 120s)이 **같은 자리를
   재반환**(idempotent_reuse) → 클라이언트가 새 자리로 알고 기동 명령 + 복원 글을 또 친다. 복원 1회 표식은
   이 경로에서 주입 **뒤**에야 찍혔다. 윈에서는 추가로 표식 폴더(소켓 부모)가 `\\.\pipe\` 라 쓰기가 늘 실패
   → fail-open. image(71) 의 「[RESTORE] → claude … --continue → [RESTORE]」(살아 있는 claude 입력창 안)가 이것.
2. **미제출**: ready 판정의 안전 밸브(커널 생존 + 맨 셸 아님)가 claude TUI 가 그려지기 **전**에 발화한다
   (셸에 친 기동 명령 줄 때문에 「맨 셸 아님」). 그 창에 붙여넣은 글은 셸 입력 버퍼로 가서 claude 가 뜬 뒤
   입력창에 미제출로 남는다. 기동이 느린 기기(윈)에서 창이 넓어진다.
3. **「복원 중」 드레인 건너뜀**: 가드가 「started ∧ ¬g2_ack.done」 이었는데 g2_ack 는 no-ping/degraded 로
   done=false 인 채 복원이 끝난다(라이브 저널 20역할 전부) → 저널 저장 뒤 5분간 전 자리 skip. 윈은 저널 폴더를
   못 찾아(파이프 부모) 가드 자체가 꺼져 있었다 — 그래서 맥 VM 만 skip 이었다.

## 수리
- `cys::daemon_state_dir`(lib) — 데몬 `state_dir` 과 같은 규칙(윈 `%LOCALAPPDATA%\cys` + 파이프 슬러그).
  복원 표식·복원 가드가 사용.
- launch 경로: 기동 **전** 표식 claim · `launch_boot_skip` 표(표식 진 복원 = 건너뜀 · 재반환 + 에이전트 생존 = 건너뜀).
- 주입 직전 claude 계열은 빈 입력창(`input_line_empty == Some(true)`) 실측 대기(상한 30s) → 못 보면 주입 0 ·
  관문 보류(gate `claude_input_not_ready`).
- 주입 뒤 `settle_submit`: 제출 실측 → 미제출이면 Return 1회 → 재실측 → `~/.cys/state/boot-submit-<레인>.jsonl`
  (256KB 회전). 못 재면 키 0.
- UI: 복원 카드 + 복원 완료 알림에 「그 창 안내 미전달」 1줄(not_submitted · held_input_not_ready · 자리별 최신 기록 · 15분 창).
- 드레인 가드 종결 = 이번 회차 verify 기록(ts 대조) · 표지가 남아도 입력창이 빈 자리는 진행(상세에 사유).
- `cys rotate` — 5단(drain --verify → 데몬 교체 → 표식 → init-pack → restore) · rc 표는 `rotate_rc` doc.

## 격리 재현(맥 · 격리 cysd /tmp · 실 claude(haiku) 자리 · 팩 사본 · 라이브 무접촉 · 잔존 프로세스 0)
| 항목 | 수리본 | 대조군(438d7113) |
|---|---|---|
| ⓑ 재시작 + 동시 restore 2개 | 자리 3개 각각 기동명령 1 · [RESTORE] 1 · 제출 3/3 · 두 번째 경로 「맡았다」 3회 | 자리마다 기동명령 2~3 · [RESTORE] 2~3 · worker-5 자리 2개 증식 |
| ⓐ 복원 직후 드레인 | saved 3/3 · 체크포인트 3 | skipped_restoring 5/6 |
| 같은 저널에서 드레인 | 건너뜀 0(saved 4 · timeout 2 = 대조군이 망가뜨린 지연 자리) | — |
| ⓒ 기동 10초 지연 자리 | 셸 붙여넣기 0 · 입력창 실측 뒤 주입 · 제출 · 응답 | (수리 1차본에서도) 셸로 들어가 미제출 |
| ④ rotate(비-기본 소켓) | rc=0 · 78s · 3/3 · 데몬 pid 교체 · 자리마다 1+1 | — |

재현 방법: `mktemp -d /tmp/cysiso.XXXX`(SUN_LEN) · 팩 rsync 사본(`agents.json` claude cmd 를 haiku 로 ·
WORKER_DIRECTIVE 를 짧은 격리 문구로) · env `CYS_SOCKET` `CYS_PACK_DIR` `CYS_STATE_DIR` `CYS_NO_OFFICE_BRIDGE=1` ·
cysd 는 python `start_new_session` 으로 · 지연 자리 = 팩 사본에 `claudeslow`(cmd `sleep 10; claude …`) 추가.
★`CYS_BOOT_GATES=0` 은 넣지 마라 — 준비 판정이 옛 방식으로 내려가 실제 설치와 조건이 달라진다.

## 앱 [재시작] 단추 ↔ `cys rotate` 대조(전환은 안 함 — 비쌈)
| 단계 | 앱(rotate_daemon · maybe_apply_pending_update · spawn_org_restore) | cys rotate |
|---|---|---|
| 저장 검증 | UI 가 drain_verify 를 따로 부르고 결과를 재시작 뒤 알림 | 내부 1회 · 결과는 요약 줄 |
| 데몬 교체 | SIGTERM/taskkill → ensure_daemon(launchd 위임 · 형제 spawn) | 맥 takeover / 윈 등록+정지 / 비-기본 정지 → 자동 기동 |
| 팩 반영 판정 | decide_pending_update(표식·스탬프·앱 판본) | 무조건 init-pack(표식 → 성공 시 제거+스탬프) |
| 복원 | 본부 + **부서 순회**(묘비 게이트·생존 확인·재기동) + restore-progress 이벤트 | 본부(현재 소켓) restore 1회 — **부서 순회 없음** |
전환 비용 = 부서 순회·진행 이벤트·업데이트 판정을 CLI 로 옮기거나 앱이 rotate 출력을 해석해야 함.

## 잔여 위험 · 미결
- **미실측**: 윈 전 경로(master 실기) · 맥 기본 소켓 rotate(launchd 이관 — 라이브를 건드려 이 기계 불가).
- 공용 판정기(890 lib) `input_region_anchored` 는 셸에 되찍힌 본문의 `> ` 줄·전역 `❯` 를 앵커로 잡을 수 있다 →
  기동 전 화면에서 거짓 Submitted. 부트 경로는 이제 입력창 실측 뒤에만 주입해 닿지 않지만, 판정기 자체는 그대로(890 권고 전달).
- 입력창 대기는 claude 계열만 — codex·gemini 좌석은 여전히 밸브 조기 발화 창이 있다.
- 드레인은 「표지 잔존 + 빈 입력창」이면 진행한다(브리프 지시). phoenix 가 실제로 진행 중일 때(ⓐ 의 worker 자리)도
  진행하므로, 그 직후 phoenix ACK 핑과 드레인 지시가 같은 자리에 겹칠 수 있다(관측된 파손은 없음).
- 복원 표식 fail-open 유지(쓰기 실패 시 주입 · 이제 stderr 경고). 선택지는 【확인요청】 참조.
- UI 카드는 기본 레인 `~/.cys/state/boot-submit-base.jsonl` 만 읽는다 — `CYS_STATE_DIR` 재정의 기기·부서 레인은 표기 안 됨.
- 콜드부트 phoenix 의 「각성 확인 핑」(reinject --check)은 복원 글이 아닌 별도 주입으로 남는다(설계).
- `cargo test --bin cys` 는 stdin 이 열린 채 백그라운드로 옮겨지면 대화형 시험 하나가 멈춘다 — `< /dev/null` 로 돌려라.
