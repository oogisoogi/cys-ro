# HANDOFF — TICKET=win-qstarved-ctrl-bytes (2026-10-29 · worker-2@surface:1712)

> 브리프 = master-send 원장 `surface:1712 kind=brief via=spawn-worker.sh 07:29:16`(본문 머리 「# TICKET=win-qstarved-ctrl-bytes」).
> worktree = `~/axdev/.wt/cys-1111-qstarved` · 가지 `fix/1111-qstarved-ctrl` ← `int/1111` `eb4ef98c` · 커밋 1개(이 문서와 같은 커밋).
> 박사님 원문(10-27 윈 실기): 「모든 창에 어떤 입력도 하지 않았다. 그런데 왜 큐막힘이 떴는가?」

## 0. 끝난 것 한눈에

| 할 일 | 결과 | 근거 |
|---|---|---|
| 1. 사람 계수 집계 경로 판독 + 제어 응답이 세이는지 시험으로 확정 | **확정 — xterm.js 5.5 가 스스로 보내는 응답 4종이 사람 입력으로 세였다**(DSR `ESC[0n` · ANSI DECRPM `ESC[n;v$y` · DECRQSS `ESC P1$r…ESC\`/`ESC P0$rESC\` · OSC 4 팔레트). 포커스·CPR·DA·OSC 10/11/12 는 종전부터 면제(시험으로 재확인) | §1 · §3 |
| 2-a. 수리 — 제어 응답 바이트를 사람 몫에서 제외 | `cys::mousereport::is_pure_terminal_autoreply` 인식 목록에 4종 추가(이 술어 하나가 계수·타이핑 가드 둘 다의 정의처) | §2-1 |
| 2-b. 수리 — 다시 그리기가 안 걸린 이유를 payload 에 노출 | `queue.starved`·`queue-blocked.json` 의 `screen_diag` 에 키 5개 추가(`repaint_knob_off`·`rows_too_small`·`repaint_unresolved`·`nudge_ineligible`·`repaint_last_obs`) | §2-2 |
| 3. 시험 | 신규 3건 녹 · 수리 전 코드에서 적 · 뮤턴트 1 적 · 전체 결과 §3-3 | §3 |
| 4. 커밋 + HANDOFF | 가지에만 커밋 · push·병합·빌드·윈 배포 = 안 함(master 게이트) | §5 |

## 1. 원인

### 1-1. 사람 계수가 어디서 오는가(코드 판독 · 확신도 High)
- GUI(`ui/src/main.ts` `term.onData` → `sendRaw` → Tauri `send_input`)는 xterm.js 가 내보내는 **모든** 바이트를 `surface.send_text(human=true)` 로 데몬에 올린다(`src-tauri/src/main.rs` `send_input` — `"human": !q`).
  xterm.js 의 `onData` 에는 사람이 친 키만 오지 않는다 — 앱(Claude Code·ConPTY)이 보낸 **질의에 xterm.js 가 스스로 답한 응답**도 같은 이벤트로 나온다(`coreService.triggerDataEvent`).
- 데몬(`governance.rs` `pending_input_step_model`)은 봉투 밖 세그먼트가 `is_pure_terminal_autoreply` 일 때만 계수에서 뺀다. 그 밖의 바이트는 `count` 와 `human` 에 그대로 더한다.
  같은 술어를 `handlers.rs` `surface.send_text` 의 `last_human_input`(타이핑 가드) 갱신도 쓴다 — 그래서 미인식 응답은 **「마지막 사람 입력」 시각까지 찍는다**(윈 보고 「마지막 사람 입력 09:04:4x · 박사님 실키 없음」과 같은 꼴).

### 1-2. 빠져 있던 응답 4종(관측 = 맥 시험 · 확신도 High)
- `@xterm/xterm@5.5.0`(`ui/package.json` `^5.5.0` · 맥 사본 `~/cys-terminal-src/ui/node_modules/@xterm/xterm/lib/xterm.js`)의 `triggerDataEvent(` 호출을 **전수** 대조했다. 우리 `new Terminal({...})` 옵션에는 `windowOptions` 가 없어 창 보고(`ESC[4;…t`·`ESC[6;…t`·`ESC[8;…t`)는 나가지 않는다. 남는 자동 응답:

| 응답 | 꼴(xterm.js 5.5) | 질의 | 수리 전 |
|---|---|---|---|
| 포커스 | `ESC[I` · `ESC[O` | DECSET 1004 | 면제 |
| CPR · DECXCPR | `ESC[r;cR` · `ESC[?r;cR` | `ESC[6n` · `ESC[?6n` | 면제 |
| DA1 · DA2 | `ESC[?1;2c`(·`ESC[?6c`) · `ESC[>0;276;0c` | `ESC[c` · `ESC[>c` | 면제 |
| private DECRPM | `ESC[?n;v$y` | `ESC[?n$p` | 면제 |
| OSC 10/11/12 | `ESC]1x;rgb:…ESC\` | `ESC]1x;?` | 면제 |
| **DSR 상태** | `ESC[0n` | `ESC[5n` | **사람 4 바이트** |
| **ANSI DECRPM** | `ESC[n;v$y`(? 없음) | `ESC[n$p` | **사람 7~8 바이트** |
| **DECRQSS** | `ESC P1$r<설정>ESC\` · 무효 질의 `ESC P0$rESC\` | `ESC P$q<설정>ESC\` | **사람 6~12 바이트** |
| **OSC 4 팔레트** | `ESC]4;n;rgb:…ESC\` | `ESC]4;n;?` | **사람 20+ 바이트** |

- 수리 전 코드에서 시험을 돌린 실측: `"\u{1b}[0n"` 한 번에 `(count, human) = (4, 4)`(V2·V3 모두 — `qstarved_ctrl_replies_count_zero_human_bytes_but_letters_do` 적 메시지).

### 1-3. 윈 실기 「사람 13 바이트」 가 이 중 무엇이었나 — **추정(관측 아님)**
- 13 은 예컨대 `ESC[0n`(4) + `ESC P1$r0mESC\`(9) 의 합과 맞지만, **윈에서 실제로 흐른 바이트는 아직 보지 못했다.** ConPTY·Claude Code 가 어떤 질의를 보냈는지도 미확인이다.
- 그래서 이 수리가 윈의 13 바이트를 **전부** 없앤다고 단정하지 않는다. 확인 방법 = §4 윈 실기 ②(입력 기록 켜고 원바이트 수집).
- 「High 무결성(08:29~) 관련 여부」 — 코드 경로에 무결성 수준을 읽는 곳이 없어 이 티켓에서 판정하지 않았다(미확인 유지).

### 1-4. 다시 그리기가 한 번도 안 걸린 이유(48건 전부 `repaint_requested_at` None) — 코드 판독 · 확신도 Med
- 다시 그리기 시계는 큐 틱의 분류(`governance.rs` `nudge_screen_obs`)가 **`Unreadable`** 일 때만 간다(`repaint.rs` `note_queue_screen`).
- 1.1.10(`502741c7`)에서 윈 fullscreen 좌석은: 커서 행은 읽힘(`obs.line = Some` · 커서가 `❯` 바로 뒤) → 대체화면이라 `Readable` 갈래가 아니고, 커서 행이 읽혔으니 `desync` 도 거짓 → **`Other`**. 시계가 영영 안 간다.
  같은 때 진단(`input_line_visibility`)은 줄바꿈 표시 행을 이어 붙인 `contents()` 로 편집 영역을 재다 마커 행을 못 찾아 `draft_visible = None` → 처방 `input_pending_unknown` 이 「1분 넘게 못 읽으면 cys 가 다시 그리기를 요청한다」고 **약속했다** — 틱 분류와 처방이 서로 다른 재료를 봐서 생긴 거짓 약속이다.
- `int/1111` 에는 WINQ-2(`c41e12f4`·`ae2ca22c` — 진단·stale 리셋·틱 레이아웃이 **물리 행**(`layout_screen`)으로 잰다)가 이미 들어 있어, 같은 화면이면 이제 `draft_visible = Some(false)` → stale 리셋(빈 composer · 정적)으로 계수가 0 이 되고 처방도 `phantom_count` 로 바뀐다(`winq2_wrapped_rule_row_lets_stale_pending_input_reset` 녹).
- 1.1.10 payload 에 사유 칸이 없었던 것은 사실이다: `502741c7`·`int/1111` 둘 다 `screen_diag_json` 에 `repaint_requested_at` 만 있고 `repaint_knob_off`·`repaint_unresolved` 등은 처방 문장 재료로만 쓰였다(`git show <rev>:src/bin/cysd/governance.rs` grep 대조).

## 2. 수리

### 2-1. `src/lib.rs` `mousereport::match_terminal_autoreply` — 4종 추가
- DSR: `ESC[` + **한 자리** `0`|`3` + `n`. 질의 `ESC[5n`·`ESC[6n`·`ESC[1n`·`ESC[00n`·`ESC[0;0n` 은 여전히 사람 쪽.
- ANSI DECRPM: 파라미터 **정확히 2개** + `$y`. 1개·3개·`$` 절단은 사람 쪽.
- DECRQSS: `ESC P1$r` + 인쇄가능 ASCII 1자 이상 + `ESC\` · `ESC P0$r` + 본문 없음 + `ESC\`. 상태 2·질의(`ESC P$q`)·종결자 없음·본문 제어문자는 사람 쪽.
- OSC 4: `ESC]4;` + 숫자 + `;` + 인쇄가능 1자 이상 + (BEL|`ESC\`). 번호 없음·`;` 없음·빈 본문·종결자 없음은 사람 쪽.
- 오면제 방어 원칙(종전 그대로): 청크 **전체**가 응답의 연접일 때만 참 · 글자가 하나라도 섞이면 거짓 · `ESC[200~` 접두 무조건 거짓.
- 종전 반례 표의 「허용 밖 OSC 코드(4=팔레트)」 줄은 OSC 4 를 이제 인식하므로 「허용 밖 OSC 코드(52=클립보드)」로 바꿨다(그 줄의 뜻 — 목록 밖 OSC 는 사람 쪽 — 은 유지).
- 같은 술어를 쓰는 곳(자동 반영 · 코드 변경 없음): `governance.rs` 계수 · `handlers.rs:6366` `last_human_input`(타이핑 가드).

### 2-2. `screen_diag` 키 5개 추가(진단 전용 — 어떤 게이트·배달·처방 판정도 바꾸지 않는다)
- `repaint.rs`: `RepaintState.last_obs: Option<ScreenObs>` — `note_queue_screen` 이 매 관측 첫 줄에 기록 · `ScreenObs::as_str`(`"unreadable"`·`"readable"`·`"other"`).
- `governance.rs`: `QueueBlockDiag.repaint_last_obs` + `screen_diag_json` 에 `repaint_knob_off`·`rows_too_small`·`repaint_unresolved`·`nudge_ineligible`·`repaint_last_obs`.
- 읽는 법: `repaint_requested_at` 이 null 인데 ⑴ `repaint_knob_off` 참 = 노브 끔 ⑵ `nudge_ineligible` 참 = 대상 아님 ⑶ `rows_too_small` 참 = 창이 작음 ⑷ `repaint_last_obs` 가 `"other"`·`"readable"` = 틱이 판독 불가로 안 봤다(시계 안 감 — 1.1.10 윈 48건이 이 꼴이었을 것으로 본다 · 추정) ⑸ `"unreadable"` 인데 null = 아직 60초 전.
- ⚠ 범위 고지: 브리프는 knob_off·rows_too_small·unresolved 를 예로 들었고 `nudge_ineligible`(같은 구조체에 이미 있던 값)·`repaint_last_obs`(새 기록)는 내가 덧붙였다 — 이번 윈 사례의 실제 사유가 앞 셋이 아니라 틱 분류 쪽이라 그것 없이는 「왜」에 답이 안 된다는 판단이다. 빼라면 두 키만 지우면 된다.
- 손대지 않은 것: 처방 문장(`repaint_promise`)이 틱 분류를 보지 않아 「요청한다」고 약속하는 틈은 남아 있다 — WINQ-2 이후 재현 경로를 맥에서 못 찾았고, 처방 문면 변경은 범위 밖이라 📌 후보로만 남긴다.

## 3. 시험

### 3-1. 신규
| 시험 | 내용 |
|---|---|
| `cys` lib `tests::terminal_autoreply_covers_every_xterm_js_5_5_reply` | xterm.js 5.5 응답 16꼴 단독·연접 참 + 반례 19개 거짓 |
| `cysd` `governance::tests::qstarved_ctrl_replies_count_zero_human_bytes_but_letters_do` | V2·V3 각각 응답 16꼴을 사람 경로로 주입 → `(count, human) = (0, 0)` · 대조군 `abc` → `(3, 3)` · 초안 위 `ESC[0n` → `(3, 3)` 불변 |
| `cysd` `governance::tests::qstarved_ctrl_replies_do_not_starve_queue_but_letters_do` | claude 2.1.280 실화면 좌석 2개 · 응답만 → 큐 배달 · `queue.starved` 0건 / 대조군 `abc` → `input_pending` 보류 · `queue.starved` 의 `pending_input_human_bytes = 3` · `screen_diag.repaint_last_obs = "readable"` · 불리언 넷 false · 틱 전 `repaint_last_obs = null` |
| 갱신 `instr_queue_block_diag_carries_dim_col_alt_and_human_idle` | `screen_diag` 키 집합에 5개 추가 |

### 3-2. 적 증명
- **수리 전**(`src/lib.rs` 만 `HEAD` 로 되돌림): 신규 cysd 2건 적 — `V2: 제어 응답 "\u{1b}[0n" 가 미제출 입력으로 세였다 left: (4, 4) right: (0, 0)` · `제어 응답만 흐른 좌석에 계수가 남았다`.
- **뮤턴트 1**(DSR `matches!(v, 0 | 3)` → `matches!(v, 3)`): cysd 신규 2건 적 + lib `terminal_autoreply_covers_every_xterm_js_5_5_reply` 적(`DSR 정상 미인식`). 되돌림 후 `cmp` 일치 확인.

### 3-3. 전체(맥 · 이 worktree · 2026-10-29)
- `cargo test --lib` = **1102 passed · 0 failed** · 2 ignored(07:53).
- `cargo test --bin cysd` 1회차 = 2709 passed · **2 failed**:
  ⑴ `state::tests::c5_starved_payload_adds_diag_and_remedy_keys_and_keeps_old_keys` — `screen_diag` 객체 전체를 핀하는 시험이라 새 키 5개를 기대값에 더했다(이 티켓의 계약 변경 · 최상위 키 수 16 은 그대로).
  ⑵ `governance::reflect_queue_tests::q7_process_exit_of_a_role_seat_parks_instead_of_dropping` — 이 변경과 무관한 좌석 종료·주차 경로(5초 기한 대기). 단독 실행 3회 3/3 녹 → 전체 병렬 부하에서의 시간 의존 흔들림으로 본다(추정 · 같은 부하의 HEAD 대조는 안 했다).
- `cargo test --bin cysd` 2회차(⑴ 수리 뒤 최종 트리) = **2711 passed · 0 failed** · 9 ignored(08:03).
- 이 가지에서 돌리지 않은 것: `cys` 바이너리 시험 · `src-tauri` · `ui` bun/tsc(손댄 파일 없음 — 술어 API 무변경).

### 3-4. 맥 영향
- 맥도 같은 GUI·같은 xterm.js·같은 데몬 술어다 — 맥에서 이 4종이 흐르면 종전에도 사람 계수였고 이제 빠진다(방향 = 유령 계수 감소). 사람 글자 계수는 대조군 시험으로 불변 확인.
- 계수 모델 노브(`PendingInputModel` 윈 V2 / 맥 V3)·대체화면 PgUp/PgDn 규칙·봉투 규칙은 손대지 않았다. 면제는 「청크 전체가 응답」일 때만이라 키 입력과 섞인 청크는 종전대로 센다.

## 4. 윈 실기 절차(master 게이트 — 빌드·배포 뒤)

① **재현 확인(박사님 원 상황)**: 새 판 설치 → Claude Code 좌석 2개 이상 · **아무 키도 누르지 않고** 1시간 이상 둔다(클릭·창 전환 포함해도 됨 — 포커스 응답은 종전부터 면제).
   - 판정: `cys status --json` 또는 `org.status` 의 각 좌석 `pending_input_human_bytes` 가 **계속 0** · `queue.starved` 의 `remedy_code` 에 `input_pending_unknown`·`human_draft` 가 없다.
② **13 바이트의 정체 수집(추정 → 관측)**: 설치 전에 윈 `%USERPROFILE%\.cys\ime-debug` 빈 파일을 만들고 **새 pane** 을 띄운다(`ime_debug_enabled` 파일 게이트 · `src-tauri/src/main.rs:490`). GUI 가 `onData data="…"` 로 받은 원바이트가 `%TEMP%\cys-ime.log` 에 쌓인다.
   - 키를 안 친 구간의 줄에서 `\x1b` 로 시작하는 꼴을 모아 §1-2 표와 대조 — 표에 없는 꼴이 나오면 그것이 남은 사람 계수의 출처다(그때 이 술어에 같은 방식으로 추가).
   - 끝나면 `ime-debug` 파일을 지운다(평시 비용 0 이지만 로그가 계속 쌓인다).
③ **다시 그리기 사유 칸 확인**: 막힘이 나면 `queue.starved`(또는 데몬 상태 폴더의 `queue-blocked.json` 행)의 `screen_diag` 에 새 키 5개가 보이는지 · `repaint_requested_at` 이 null 이면 §2-2 읽는 법대로 사유가 하나로 짚이는지.
④ **회귀**: 실제로 글자를 쳐 둔 좌석은 여전히 `input_pending` 으로 막히고 `pending_input_human_bytes > 0` 이어야 한다(초안 위 오주입 방지).

## 5. 비가역·비용 결정 — 실행 안 함
- push · `int/1111` 병합 · 빌드·서명·윈 배포 · 윈 노트북 원격 조작 = **전부 안 함**(master 게이트).
- 이 맥의 실제 cysd·`/Applications` 무접촉 · 프로세스 종료 0 · codex 호출 0.

## 6. 다른 워커와 겹치는 파일
- 손댄 파일 = `src/lib.rs`(mousereport 모듈 + 그 시험) · `src/bin/cysd/governance.rs` · `src/bin/cysd/repaint.rs` · 이 문서.
- `fix/1111-worker-cap`(handlers.rs·launchd.rs)과 **파일은 겹치지 않는다.** 다만 `handlers.rs:6366`(타이핑 가드)이 바뀐 술어를 그대로 쓰므로 동작은 함께 바뀐다(코드 충돌 없음 · 병합 시 의미 충돌도 없음 — 같은 방향).
- `src/lib.rs` 는 큰 공용 파일이라 다른 가지가 같은 파일 다른 곳을 고쳤다면 병합 때 문면 충돌만 확인하면 된다(이 가지의 변경은 `mod mousereport` 안과 그 시험 블록뿐).

## 7. 함정·재현
- `cargo` 는 PATH 에 없다 — `export PATH=$HOME/.cargo/bin:$PATH`.
- zsh 에서 `git show $r:path` 는 `:s` 수식자로 깨진다 — `"${r}":path` 로 쓴다.
- 재현 명령: `cargo test --bin cysd -- qstarved_` · `cargo test --lib -- terminal_autoreply`.
