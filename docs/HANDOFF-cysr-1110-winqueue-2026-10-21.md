# HANDOFF — cysr-1110-winqueue (2026-10-21 · worker-3 surface:1540)

가지 `fix/1110-winqueue` ← origin/main `fb386c49` · 로컬 커밋 8개(HANDOFF 포함) · **push 0 · 태그 0 · 설치 0**.
브리프 = 원장 대조 성립(surface:1540 · kind=brief · 21:47:43 · submitted=true). master 답 `master#904c96af`(22:25:14 · 원장 대조 성립)로 Q1-A·Q2-A 집행.

| 커밋 | 항목 | 한 줄 |
|---|---|---|
| `854c8724` | 축1 | 대체화면에서 PgUp/PgDn 만으로 된 입력은 「미제출 입력」 계수에 넣지 않는다 |
| `80c615ca` | 축2 | 대체화면 큐 보류 때 어느 레이아웃 규칙이 거짓인지 사유 코드(`screen_diag.layout_why`)를 낸다 + 맥 fullscreen 실화면 배달 핀 |
| `c4bfb0d8` | 자리표 | 회수 판정의 줄 수를 데몬 `line_count` 대신 그 pane 화면의 비어 있지 않은 논리 줄로 · 윈도우 상한 4 |
| `fa56bd91` | 문안 ⑴⑷⑸⑹ | fullscreen 힌트 문구 · verify_denied 문구 · 계정 폴더 경로 비교 · factory-reset `--plan` |
| `a68abf4f` | Q1-A·Q2-A | 사람이 닫은 좌석의 큐 폐기 1줄 알림 · 주차 만기·초과 원장 묘비 · 맥 D5 설계 의도 주석 |
| `8fdd7c14` | 축2 | `queue.starved` screen_diag 키 핀에 `layout_why`(null) 반영 |

---

## 1. 큐 배달 정지 — 축1(휠 번역 바이트가 사람 입력으로 세어짐)

**현상(윈 1.1.9 실기 W-2 10-17 01:5x)**: fullscreen(`/tui fullscreen`) 좌석에서 휠·트랙패드 스크롤 → `pending_input_human_bytes=3364`(입력줄은 빈 화면) → `queue_blocked_by=input_pending` → 기계 배달 무기한 정지. Enter 로만 풀렸다(SESSION_STATE 578행).

**원인(코드 근거 · 확신 High)**:
- 윈도우 GUI 는 대체화면 pane 의 휠을 `ESC[5~`/`ESC[6~`(PgUp/PgDn)로 번역해 보낸다 — `ui/src/altscroll.ts:170`, `ui/src/main.ts`(win 휠 처리기 `sendRaw(act.data)`).
- `sendRaw` 는 사람 키 경로라 `send_input`(human=true)로 가고 → 데몬 `handlers.rs` 가 `InputOrigin::Human` 으로 `Surface::apply_pending_input` 에 넣는다.
- 계수 규칙 `governance::pending_input_step_model` 은 단독 ESC·BS/DEL 만 면제하고, `ESC[5~`(4바이트) 세그먼트는 그대로 센다. 840 노치 ≈ 3360 바이트 = 실측 3364 와 같은 규모다.

**수리(`854c8724`)**: `state.rs Surface::apply_pending_input` — **대체화면 ∧ 붙여넣기 봉투 밖 ∧ 이월 꼬리 없음 ∧ 청크가 PgUp/PgDn 반복뿐**(`governance::is_page_scroll_chunk` · 순수)이면 상태를 바꾸지 않는다. 더하지도 빼지도 않는다(기존 초안 계수 보존).
- 화살표(cursor 모드 `ESC[A`·`ESC OA`)는 **면제하지 않았다** — 입력 기록을 줄에 불러오는 키라 실제 글자를 남긴다(V3 doc 과 같은 입장). ⇒ cursor 모드(옵트인 게이트 키)를 켠 윈 사용자는 같은 정지가 남는다(잔여 · 아래 §8).
- 본 화면에서는 면제하지 않는다 — 셸 줄 편집기는 묶이지 않은 키의 꼬리(`~`)를 글자로 남길 수 있다.

**1.1.8 재현 여부**: 재현된다(정적 근거 · 실기 0) — 같은 번역(`v1.1.8:ui/src/altscroll.ts:170` · 도입 `614f5c51` v1.1.5)과 같은 계수 경로(`v1.1.8 state.rs apply_pending_input` · human 출처)가 그대로 있다.

**시험**: `state::tests::winqueue_alt_screen_page_scroll_keys_are_not_a_draft`(① 대체화면 휠 840키 → 0 ② 사람 초안 `abc` 위 휠 → 3 그대로 ③ 화살표는 셈 ④ 본 화면 PgUp 은 셈) · `governance::tests::wq_fullscreen_wheel_scroll_does_not_block_queue`(실화면 픽스처 + 휠 → 큐 배달) · `wq_page_scroll_chunk_pure`.
**뮤턴트**: 가드 끔 → 2 적색 · 본 화면까지 면제 → 1 적색.

## 2. 큐 배달 정지 — 축2(`alt_screen` 보류)

**현상(02:0x)**: 사람 입력 계수가 0 으로 풀린 뒤에도 `queue_blocked_by=alt_screen` → `--queued` 만 무기한 보류 · 직접 send(비큐)는 즉시 도달.

**사실 확인(이 티켓에서 실측)**:
- 보류 사유 `alt_screen(전체화면 · 프롬프트 레이아웃 미확인)` 은 `prompt_gate_verdict` 의 대체화면 갈래에서 **마커 보임 ∧ 커서행 입력줄 빔 ∧ 레이아웃 증거(`layout_ok`) 거짓**일 때만 난다(`governance.rs` BLOCKED_ALT_SCREEN). 즉 윈 화면에서 `readiness::composer_layout_static_ok` 가 거짓이었다.
- 맥에서 claude **2.1.306** 을 fullscreen 렌더러(`CLAUDE_CODE_NO_FLICKER=1`)로 PTY 에 띄워 실화면 원바이트 2종을 떴다 — ⓐ 유휴(빈 composer `❯\u{a0}` · 위아래 괘선 · 커서 (35,2)) ⓑ 숫자 120줄 응답 뒤 PgUp 3회(`Jump to bottom` 표지 · 맨 위 고정 머리 `❯ <지난 질문>`). **둘 다 현행 게이트를 통과해 배달됐다**(`wq_fullscreen_idle_composer_delivers`). 유휴 fullscreen 은 첫 0.8초 뒤 출력이 멈춘다(10.7초에 44바이트 1회) — 정적 축 기아 없음.
- ∴ 윈 화면의 무엇이 다른지는 **저장소·기록에 근거가 없다**(윈 W-2 화면 사본 없음) → **윈 실기 확인 필요**.

**수리(`80c615ca` · 판정 무변경 · 진단만)**: `readiness::composer_layout_why` — 레이아웃 판정이 거짓인 **이유 코드**를 낸다. `queue-blocked.json`·`queue.starved` 의 `screen_diag.layout_why`(추가형 키 · 대체화면 마커 좌석만 · 그 밖 null).
코드: `ok` · `no_marker_row` · `marker_row_text` · `marker_below` · `nothing_below_no_evidence` · `marker_row_in_draft` · `box_rules_<0|1|2+>_first_<rule|status|other>` · `weak_not_quiet`.
- 검체 `winqueue_composer_layout_why_codes_agree_with_the_verdict` 가 같은 화면들로 `"ok"` ⇔ `composer_layout_static_ok` 일치를 대조한다(진단과 판정이 갈라지면 엉뚱한 규칙을 고친다).
- `wq_fullscreen_layout_block_names_the_failed_rule`: 같은 실화면에 괘선 1줄을 더 그리면 `alt_screen` 보류 + `box_rules_2+_first_rule`.
- 뮤턴트: 약한 증거 갈래를 무조건 `ok` → 일치 검체 적색.
- 한계(정직): 진단의 마커 선택은 `pick_marker_for_screen`(화면 전체)이고 틱은 커서행 선두 후보를 먼저 본다 — claude(마커 1개)에서는 같고, 마커 후보가 여럿인 어댑터에서 드물게 다른 마커를 볼 수 있다.

**윈 실기 확인 절차(3줄)**:
1. 윈 새 판에서 claude 좌석 하나를 `/tui fullscreen` 으로 두고 입력줄을 비운 채 `cys send --queued --to <그 역할> "핑"` 1건.
2. 10초 뒤 데몬 상태 폴더의 `queue-blocked.json`(기본 데몬 = `%LOCALAPPDATA%\cys\queue-blocked.json` · `governance.rs QUEUE_BLOCKED_FILE` = `state_dir` 아래)에서 그 좌석 행의 `screen_diag.layout_why` 값과 `cys read-screen --surface <ref>` 아래 8줄을 함께 적는다(`cys queue list --json` 에는 `blocked_by`·`remedy` 만 있고 `screen_diag` 는 없다).
3. 그 코드가 가리키는 규칙(괘선 개수·첫 줄 종류·마커 위치)을 윈 화면 사본으로 고치는 것은 다음 수리 티켓(사본을 픽스처로 넣고 실패 먼저).

## 3. 윈 기동 자리표 맨 셸이 안 닫힘(`c4bfb0d8`)

**원인(확신 High)**: 회수 판정(`ui/src/placeholderclose.ts`)의 「화면 줄 수」 입력이 데몬 `surface.list` 의 `line_count` 였는데, 그 값은 화면 줄이 아니라 **PTY 출력 개행의 누적 커서**다(`state.rs ingest_output` · 줄지 않는다 · `read_text since_line` 등의 커서로도 쓰여 의미를 바꾸면 안 된다). 윈도우는 ConPTY 다시 그리기·편성 도착 때 칸 폭 변화로 개행이 계속 쌓여 화면 4줄 ↔ 466 이 됐다(466 의 정확한 생성 기제는 추론 · 실측 0).
- `line_count` 의 뜻 = **버퍼 행(누적 개행) 쪽이다** — 화면 줄이 아니다(코드 근거 `state.rs` T3-14 주석·`fetch_add`). 별도 근거: master SESSION_STATE 「line_count 는 alt_screen 좌석에서 불변(802331 고정)」.

**수리**:
- `placeholderScreenLines(term)` — 그 pane xterm 의 **바닥 페이지**(baseY 부터 rows 줄)에서 비어 있지 않은 **논리 줄**(자동 줄바꿈 이어짐 `isWrapped` 는 앞 줄과 한 줄)을 센다. pane 이 없거나 읽다 실패하면 `null`(닫지 않음).
- ★지시 없이 내린 판단 1건: **윈도우 상한 4**(`PLACEHOLDER_MAX_LINES_WIN`). 입력만 바꾸면 윈도우는 여전히 안 닫힌다 — 윈 맨 셸은 인자 없는 `powershell.exe`(5.1 · `state.rs` 윈 셸 선택)라 프롬프트 앞에 배너 3줄(`Windows PowerShell` · `Copyright …` · `Install the latest PowerShell … aka.ms/PSWindows`)을 스스로 찍는다 = 배너 3 + 프롬프트 1 = 4. 실기 「화면 4줄」 과 맞는다. 유닉스 상한 3 은 무변경.
- 배선: `main.ts` 회수 루프의 한 줄(`lineCount: placeholderScreenLines(panes.get(paneKey(sid, ws.socket))?.term)` + `isWindows: IS_WINDOWS`).
- 시험: `placeholderclose.test.ts`(PowerShell 첫 화면 = 4 · 화면 위 스크롤백 466줄은 세지 않음 · 좁은 칸 줄바꿈 = 한 줄 · 빈 화면 0 · 부재·예외 null · 윈 4 닫음/5 안 닫음 · 유닉스 4 안 닫음) · `wswiring.test.ts` 배선 핀(`su?.line_count` 직결 금지).
- 뮤턴트: `line_count` 재배선 → 배선 핀 적색 · 윈 상한 제거 → 상한 검체 적색.

**윈 실기 확인 필요(3줄)**:
1. 윈 새 판 콜드 기동 → 자리표 맨 셸이 뜨고 편성이 도착할 때까지 손대지 않는다.
2. 편성 도착 뒤 3~6초 안에 자리표 pane 이 사람 손 없이 닫히는지 본다(해소 판정 = TODO 110행).
3. 안 닫히면 그 pane 화면을 사진으로 남긴다 — ConPTY 가 칸 폭 변화 때 배너를 **자동 줄바꿈이 아니라 개행으로** 다시 찍으면 논리 줄이 5 이상이 된다(이 경우 상한이 아니라 기준선 방식이 필요).

## 4. 문안·관측 ⑴~⑹(`fa56bd91`)

| # | 판정 | 내용 |
|---|---|---|
| ⑴ | 수리 | `cys.rs alt_screen_notice`(윈 힌트): 「Windows fullscreen 비지원 · 휠로 대화가 올라가지 않습니다」 → 「GUI 가 휠을 PgUp/PgDn 키로 바꿔 보내 대화가 반 화면씩 올라갑니다(classic 처럼 스크롤백으로 올라가지는 않습니다)」. 휠 가드 끄기 안내는 「끄면 번역도 꺼지고 방향키 합성이 되살아나므로 끄지 않는 것을 권합니다」 로 — 근거 `ui/src/wheelgate.ts:305`(가드 끔 = 처리기 `none`). 문서가 지키라던 세 조건절(가드 우선·env 는 새 surface 에서만·윈 D5 옵트인)은 그대로 둠. 진리표 핀 `alt_screen_notice_truth_table` 녹. |
| ⑵ | 설계 의도 | `launch-agent --cwd` 미지정 = 호출 폴더 상속(`cys.rs run_launch_agent_opts` · 주석 「워커는 워크플로우 폴더에서 산다 — cwd 미지정이면 호출 폴더가 워크플로우 폴더다」 · `cysjavis-pack/directives/CEO_TEMPLATE.md:439-441`). 역할별 기본 cwd 개념은 없다(부서 단위 `dept_registry_cwd` 만). 141 사례는 master 폴더에서 `--cwd` 없이 띄운 운용 문제 → 지침의 `--cwd` 예시 강화가 맞다(코드 변경 0). |
| ⑶ | master Q1-A 집행 | §5 |
| ⑷ | 수리(문구만) | `directive.verify` 가 `verify_denied` 로 거부되면 「구 데몬?」 이 아니라 「이 launch-agent 가 cys pane 안에서 실행돼 데몬이 검증 상태 기록을 받지 않는다(pane 의 자기 선언 금지 규칙 · 기동은 그대로 진행)」. 거부 규칙 자체(`handlers.rs` caller 가 pane 이면 거부)는 무변경 — 좁히려면(`cs == sid` 만 거부) 보안 판단이 필요해 손대지 않음. 부기: master pane 에서 직접 `cys launch-agent` 하면 이 기록은 **항상** 거부된다(조상 프로세스 추적 때문). |
| ⑸ | 수리 | `state.rs caller_env_keeps_config_dir`: 계정 폴더 env 값을 데몬 해소값과 **글자로** 비교해, 윈도우의 `C:\Users\x/.cys/claude`(agents.json `$HOME/.cys/claude` 전개 · 구분자 혼용) ↔ `C:\Users\x\.cys\claude` 가 다르다고 읽혔다 → 윈도우 launch-agent 좌석 전부 `config_dir_trusted=false`(계정 표시 「확인 중」·회수 인증 축 약화 · 탐사 근거 `accounts.rs`). 비교를 `reclaim::norm_path_on`(구분자 통일·드라이브 문자 소문자)으로. 빈 값·다른 폴더는 종전대로 거짓. 시험 `winqueue_config_dir_trust_compares_paths_not_spellings_on_windows`(OS 인자판 `caller_env_keeps_config_dir_on` · 맥에서 윈 의미론 실행) · 위조 차단 기존 시험 녹 · 뮤턴트(글자 비교 복귀) 적색. 문자열 혼용 자체(`resolve_env_value`)는 그대로 둠 — 다른 소비처·시험 2곳이 그 표기를 고정한다. |
| ⑹ | 수리 | `cys factory-reset --plan` 의 「surface 안 실행 거부」 를 실집행에만 — 바로 아래 GUI 실행 중 검사가 이미 `!plan_only` 예외를 두고 있었다. `--plan` 경로는 데몬 무접촉(계획 출력 뒤 `return 0`). 부기: 계획 단계는 격리 폴더 쓰기 가능 여부를 임시 파일 생성·삭제로 재고(`probe_trash_root`) 폴더가 없으면 만든다 — 기존 동작이며 「쓰기 0」 문구와 미세하게 다르다(이번 변경과 무관). |

## 5. 좌석 닫힘 큐 폐기를 보이게 — master Q1-A(`a68abf4f`)

**사실(이전)**: 사람 닫기(`surface.close` 기본 = OwnerClose)는 `governance.rs close_surface` 에서 큐를 폐기하고 원장 묘비(`record_active_drain` · reason `surface_closed` · `~/.cys/state/delivery-<lane>.jsonl` · 본문 없이 sha256)와 버스 이벤트 `queue.dropped` 를 남겼다 — 원장에는 남았지만 **사람에게 알리는 경로가 0**(GUI 가 이 이벤트를 소비하지 않음). 주차(역할 좌석의 셸 자력 종료) 만기·상한 초과는 **이벤트만 있고 묘비 0**.

**수리**:
- ① 데몬 `queue.dropped(surface_closed)` payload 에 추가형 키 `owner_close`(OwnerClose 만 true · reason 무변경 — 소비처 `javis_report_gate.py` 보호). GUI `ui/src/queuedropnotice.ts`(순수) — `owner_close` ∧ 1건 이상일 때만 「대기 중이던 지시 N건을 버렸습니다(기록은 남아 있습니다)」 토스트 1줄(OS 배너 없음). 0건·회수(Reap)·옛 데몬(키 없음) = 알림 0. 문구에 경고 표지·위협 표현 없음(시험).
- ② 원장 묘비(같은 서식): 주차 만기 3경로 — 워치독 스윕(`governance sweep_parked_queues`) · 자력 종료 주차 길(`state.rs` 다른 역할 만기 걷이) · 역할 상속(`handlers inherit_parked_queue`) + 주차 상한 초과(`parked_overflow`).
- 시험: `winqueue_owner_close_drop_event_carries_owner_close_and_count`(0건 = 이벤트 없음 · 1건 · 3건 · Reap = false · reason 불변) · 묘비 3경로(기존 d7 시험 2개 + 스윕 시험에 원장 대조 추가) · `winqueue_parked_overflow_leaves_ledger_tombstones` · `queuedropnotice.test.ts` · `wswiring.test.ts` 배선 핀.
- 뮤턴트: 상속 길 묘비 제거 → `d7_expired_parked_queue_is_dropped_with_reason_not_inherited` 적색 · UI `owner_close` 검사 제거 → 적색.
- 검체 함정(기록): 같은 초에 뜬 검체 데몬끼리 원장 갈래와 큐 id(`q<started_at>.<seq>`)가 겹쳐 「묘비 목록 == [id]」 가 다른 검체 줄을 함께 읽는다 → 그 검체들은 id 에 고유 꼬리를 붙여 대조한다.
- ⚠경보 숨김 스위치(ALERTS_QUIET · 540 `rebase/v0.14.51` 가지)가 들어오면 이 토스트도 그 스위치를 따라야 한다 — 연결은 master 통합 때(`queuedropnotice.ts` 머리 주석에 표기).

## 6. 맥 D5 env vs `/tui fullscreen` ⑽ — master Q2-A

1.1.10 = 현행 유지. `cys.rs boot_agent_on_surface` 의 D5 주입 자리에 설계 의도 주석 3줄(맥은 D5 가 settings `tui` 보다 앞서 사용자 fullscreen 도 classic · 맥은 `tui:"default"` 를 선기록하지 않아 Claude Code 자동 승격 값과 사용자 선택을 구분 못 함). 소스 핀 `prompt_suggestion_injection_wired_in_both_consumers`·`d5_env_injection_covers_both_consumers` 녹.

## 7. 다음 판 후보

- **1.1.11 맥 = 윈 모델**: D5 env 대신 settings `tui:"default"` 선기록(자동 승격 차단) + 사용자 `/tui fullscreen` 존중 + 맥 함대 실기. 같이 볼 것: 맥 기동 WARN(`alt_screen_notice` 맥 분기)의 「settings tui 키 등으로 우회된 상태」 문구는 env 가 `tui` 보다 앞선다는 `claude_tui.rs` 모듈 doc 과 어긋난다(탐사 지적 · 이번 미수정). 맥에는 휠 PgUp/PgDn 번역이 없다(앱 마우스 보고로 감 · 실기 0).
- 축2 윈 화면 사본 → 픽스처 → 레이아웃 규칙 수리(§2 절차).
- 자리표: ConPTY 가 배너를 개행으로 다시 찍는 것으로 확인되면 상한 대신 「기동 직후 기준선 대비 증가분」 판정.
- ⑷ 거부 규칙을 진짜 자기 선언(`cs == sid`)으로 좁힐지 — 보안 판단.

## 8. 남은 것·한계(정직)

- 윈 실기 0 — 축2·자리표는 「윈 실기 확인 필요」. 축1 의 윈 효과도 맥 검체로만 확인(같은 바이트·같은 경로).
- cursor 모드(옵트인) 휠 = 화살표 → 여전히 사람 초안으로 센다(의도된 보수 · 그 사용자에게는 축1 정지가 남는다).
- 휠 바이트는 여전히 타이핑 가드(`last_human_input`)를 갱신한다 — 스크롤 중 3초간 직접 send 보류는 남는다(무기한 아님 · 이번 범위 밖).
- 픽스처 2종은 중첩 기동이라 꼬리에 `⚠ Transcript saving is off …` 1줄이 있다(괘선 아래 정체 모를 문면 1줄이 있어도 배달된다는 것까지 함께 재는 셈 · 개인정보 없음 확인).

## 9. 겹친 파일(동시 진행 티켓 · 통합 때 충돌 후보)

- `cysr-1110-minor`(`fix/1110-minor` @ a2688514): `src/bin/cys.rs` · `src/bin/cysd/governance.rs`
- `cysr-1110-vendor`(540 · `rebase/v0.14.51` @ 8c2e1a24): `src/bin/cys.rs` · `src/bin/cysd/delivery.rs` · `src/bin/cysd/governance.rs` · `src/bin/cysd/handlers.rs` · `src/bin/cysd/state.rs` · `ui/src/deptprogresswiring.test.ts` · `ui/src/main.ts` — ★ALERTS_QUIET 연결 지점 = `ui/src/main.ts` 의 `queue.dropped` 처리(§5).
- 이 티켓만: `src/readiness.rs` · `ui/src/placeholderclose.ts(.test)` · `ui/src/queuedropnotice.ts(.test)` · `ui/src/wswiring.test.ts` · 픽스처 2종(`src/bin/cysd/testdata/claude_2_1_306_*_fullscreen.raw`).

## 10. 시험 전건(최종 트리 · 맥 · 2026-10-21 22:5x~23:20)

| 묶음 | 결과 |
|---|---|
| `cargo test --lib` | 1078 passed · 0 failed · 2 ignored |
| `cargo test --bin cys` | 612 passed · 0 failed |
| `cargo test --bin cysd` | 2621 passed · 0 failed · 8 ignored (첫 실행 1 실패 = `c5_starved_payload_adds_diag_and_remedy_keys_and_keeps_old_keys` 의 `screen_diag` 정확 일치 핀 — 추가형 키 `layout_why` 미반영 → `8fdd7c14` 로 핀 갱신 후 전건 녹) |
| `ui bun test` | 3087 tests · 0 fail · 85 skip |
| `ui typecheck`(`tsc -p tsconfig.check.json`) | 오류 0(`ui/node_modules` 는 이 worktree 에서 `bun install --frozen-lockfile` 로 설치 · gitignore 대상) |

뮤턴트 8개(축1 2 · 축2 1 · 자리표 2 · ⑸ 1 · Q1-A 2) 전부 적색 확인 후 원복(원복은 grep 으로 원문 존재 재확인).
윈 레인 시험은 돌리지 않았다(맥 호스트) — 윈 의미론은 OS 인자판(`caller_env_keeps_config_dir_on`)·순수 함수로만 쟀다.
