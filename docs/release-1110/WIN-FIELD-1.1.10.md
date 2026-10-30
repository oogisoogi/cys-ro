# WIN-FIELD-1.1.10 — cysr 1.1.10 윈도우 실기 확인점 · 윈 master 실기 절차 초안

> 초안 · TICKET=cysr-1110-release-prep · 2026-10-22 · worker-3(surface:1550) · 집행 = 윈 master(노트북 본체) · 판정 = 맥 master
> 시점 규칙 = **절단(금 10-23) 전**(「윈 실기·VM·정밀 디버깅·이종 리뷰는 절단 전」) · 실기 대상 바이트는 체크리스트 0-3 【결정필요】(아래 §2-0).
> 방식 규칙 = 박사님 손 0 · **노트북 본체** · 한 줄 프롬프트(설치 사이트·시험 주소) · **Windows Sandbox 안 씀**(메모리 update-test-body-one-line-no-sandbox · 박사님 2026-10-08 승인) · 윈 실기는 master ↔ 윈 master 자율(메모리 win-field-test-autonomous-via-win-master).
> 모은 곳: `docs/upstream/WIN-GATE-1110.md`(W-0~W-6) · `docs/HANDOFF-cysr-1110-{winqueue,minor,trash-harden,vendor,integrate}-2026-10-21.md` · `docs/upstream/INTEGRATE-1.1.10.md` · `docs/menu-top-row-evidence/REPORT.md` · 커밋 본문(`git log v1.1.9..53031718` 230커밋 중 본문에 윈/Windows 가 든 92개) · 원작자 노트 `docs/RELEASE_NOTES_0.14.49.md`·`0.14.50.md`.
> 표기: 「출처 절차」 = HANDOFF·관문표에 명령이 적혀 있음 · **「제안」** = 출처에 절차가 없어 이 문서가 만든 것(윈에서 돌려 본 적 없음 — 표가 틀렸을 수 있다 → 원문 그대로 회신) · 「해석」 = 출처 문장에서 이끈 판단.

## 0. 먼저 알아야 할 사실

1. **WIN-GATE W-1~W-6 의 1.1.9 통과 기록은 저장소 밖에만 있다.** `docs/release-119/CHECKLIST-1.1.9-publish-2026-10-18.md:13` 은 HEAD 에서도 「미확인(저장소 결과 0건)」 · `docs/RELEASE.md:436` 칸 「★1.1.10 윈도우 실기 확인 — 상태: 실기 미검증」 이 열려 있다. 통과 기록 = `~/axdev/master/SESSION_STATE.md:606` 「WIN-GATE 1.1.9 통과(적 0): W-1·W-2·W-3·W-4(#3 미시행) 통과 · W-5 해당 없음 · W-6 통과」(관문별 상세 606~614 · 원문 = 윈 `C:\Users\<사용자>\w119\w6-result.txt`).
2. **이 관문의 원래 대상은 1.1.9 였다** — `WIN-GATE-1110.md:3` 의 대상 「병합 f711373a 를 품은 1.1.10 후보」 에서 f711373a 는 v1.1.9 의 조상(실측). 「1.1.10」 이름의 관문이 1.1.9 로 출하돼 1.1.9 에서 통과했다.
3. **1.1.10 에서 다시 돌리는 근거**(출처가 직접 「재실기」 라고 하지는 않는다 — 해석): ⓐ `RELEASE.md:436` 칸이 열려 있다 ⓑ 1.1.10 변경이 관문이 재는 자리를 직접 건드린다 — winqueue 축1(fullscreen 휠 계수) → W-2·W-3 · 윈 힌트 문구 → W-1b·W-2 기동 로그 · `factory-reset --plan` 이 창 안에서도 허용됨 → W-4 #6(1.1.9 = 「창 안 거부 → 작업 스케줄러 경유」 SS:607) · trash-harden M3·M4 가 `factory_reset.rs` 를 바꿈 → W-4 #6 ⓒ 표 정정 후보가 아직 반영 안 됨 — 「W-1 before 기준」(SS:614·626) · W-1b 주석(`WIN-GATE-1110.md:38` 「휠 스크롤이 꺼집니다」) ↔ 지금 코드 `src/claude_tui.rs:305-308` 「PgUp/PgDn 키로 바꿔 보냅니다」.
4. **「교차 컴파일 불가」 는 절반만 맞다** — trash-harden HANDOFF §2-6(:50)은 맨 `cargo check --target x86_64-pc-windows-msvc` 가 `libsqlite3-sys` 에서 멈춘다는 뜻이다. 저장소에는 그걸 우회하는 `scripts/win-typecheck.sh`(:25-28 우회 ② `LIBSQLITE3_SYS_USE_PKG_CONFIG=1` · 루트 크레이트 --all-targets + cys-app 를 윈 cfg 로 타입체크)가 있고, 이 맥에 `x86_64-pc-windows-msvc` 타깃이 설치돼 있다. 통합 가지에서는 **아직 안 돌렸다**(INTEGRATE §3 기록 0) → 체크리스트 1-2 의 태그 전 게이트로 돌린다. 링크·실행은 여전히 CI·실기 몫.
5. **윈도우 휴지통 삭제는 이 판에서 꺼진 채 나가는 것이 정상이다** — `src/bin/cysd/trash.rs:1630-1637` `delete_supported()` = 윈에서는 `cfg!(feature = "trash_win_validated")` · `Cargo.toml:31` 그 feature 는 default 에 없음 · 워크플로·스크립트에서 켜는 곳 0(git grep) · `Cargo.toml:27-29` 「켜는 유일한 정당 경로는 12.W(W1~W8)를 통과한 릴리스 단계」 — **12.W 정의 문서는 이 저장소에 없다**(`git grep '12\.W' -- '*.md'` = trash-harden HANDOFF 2줄뿐). 이번 실기는 「꺼져 있음」 을 확인하는 것이지 켜는 시험이 아니다.
6. **지금 가지(`rel/1.1.10`)는 CI push 트리거 밖** — `workflow_dispatch` 로 돌린다(체크리스트 1-1 · 1.1.9 선례 SS:628).

## 1. 확인점 전부(48개)

### A. WIN-GATE-1110(관문표 · 요약 `docs/upstream/HANDOFF-1110.md:17-28`) — 9

기대값 출처는 전부 코드 판독(`WIN-GATE-1110.md:4`). 명령 원문은 관문표에 있으므로 여기에는 줄 번호만 적는다 — 윈 master 에게는 관문표 파일을 그대로 보낸다.

| ID | 출처 | 무엇을 | 어떻게 | 통과 기준 | 1.1.9 결과(저장소 밖) |
|---|---|---|---|---|---|
| WG-0 | :8-22 「0. 시작 전」 | 판번·좌석 폴더·개인 프로필 해시 `$h0`·사전 상태 | :10-19 PowerShell 그대로(`cysr --version` · `$seat` · `$S`/`$L`/`$P` · `Get-FileHash` · `Copy-Item $S "$S.w1110-before"` · env·킬스위치 파일 검사) | :10-19 각 줄 기대값 · `cysr --version` = **1.1.10 의 판 문자열**(해석) · :22 전제(tui 키 없음)가 다르면 W-1b 만 | SS:626 「§0 기대값 전부 ✓ · w1110-before = 설치 뒤 W-1 직전(수용 · 표 수정 후보)」 |
| WG-1 | :24-35 「W-1. classic 고정」 | `src/claude_tui.rs` TUI_KEY·LedgerEntry·BACKUP_SUFFIX | :28-35 #1~#8 | `"tui": "default"` 1줄 · 원장 JSON · `.bak-cys-tui` · 차이 = tui 1줄 · 휠로 위로 · `alt_screen=false` · `$h0` 같음 | SS:611·614 통과(before 기준 = bak-cys-tui · 표 수정 후보) |
| WG-1b | :37-38 | `fullscreen_already_set_line`(`src/claude_tui.rs:305`) · doctor `claude-tui-fullscreen` | 값이 fullscreen 이면 기동 로그 확인 + `cysr doctor` | 폴더당 안내 1회 · doctor 가 그 폴더를 보임 · 파일 무변경 · ⚠:38 주석은 낡음 — 안내 문구 = 「PgUp/PgDn 키로 바꿔 보냅니다」 쪽이 정답(`src/claude_tui.rs:305-308` · `HANDOFF-1110.md:111`) | SS:609 「W-1b 안내 1회」 |
| WG-2 | :40-47 「W-2. /tui fullscreen 좌석」 | 우리 altscroll(휠 → PgUp/PgDn 번역) | :44-47 #1~#4 | `alt_screen=true` · 사용자 값 유지 · 반 화면 스크롤 · 「휠 꺼짐」 토스트 없음 · 재기동 후에도 fullscreen | SS:609·611 통과 · 단 큐 결함 관측(pending 3364 · alt_screen 보류) → 1.1.10 winqueue 의 출처 |
| WG-3 | :49-59 「★모달이 떠 있을 때 휠」 | 권한 선택 창 중 휠 | :51-54(Enter 금지 · 휠 아래 3·위 3 · Esc · `Test-Path .\w1110.txt`) | ⓒ무변화/ⓑ대화만 움직임 = 통과 · ⓐ선택 강조 이동 = **적(라이브 금지)** | SS:608 통과(「1번에 머물러 있다」) · 결함 ①② 재현 1회 |
| WG-3L | :61 | 같은 시험을 화면보다 긴 선택 창으로 | 긴 diff 승인 1회 | WG-3 과 같음 | SS:608 「긴 창(preview 80줄)」 통과 |
| WG-4 | :63-72 「W-4. 킬스위치·되돌림」 | `win-tui-classic-off`·원장 되돌림·`factory-reset --plan` | :67-72 #1~#6(#6 = 시험 기계에서만 `cysr factory-reset --plan`) | 「default 제거」 로그 · 사용자 fullscreen 유지 · 새 기록 0 · 복귀 · plan 에 tui 되돌림 항목 · 쓰기 0 | SS:607 통과(#3 조건 미충족 미시행 · #6 창 안 거부 → 작업 스케줄러 경유 rc 0) · 1.1.10 은 #6 을 **창 안에서 직접**(WINQ-6 · TRASH-3) |
| WG-5 | :74-94 「W-5. agy 상태줄 … 휴면」 | `dormant::AGY_LANE_COMPILED=false`(`src/lib.rs`) · `ensure_linked` · doctor | :83-88 PowerShell | 설정 바이트 동일 · `state\agy-statusline-*` 새로 없음 · doctor 「휴면 · 점검 안 함」 · `--fix` 뒤도 같음 | SS:607 해당 없음(agy 미설치) · 맥 = 단위 시험·뮤턴트(:80) |
| WG-6 | :96-109 「W-6. phoenix 자동 복원」 | 기본 코드페이지(949)에서 자동 복원 | :99-101 + #1~#4(`Get-Content $log -Tail 40` · `manual_restore.sh` LF · `cysr schedule list`) | Traceback·Unicode 오류 0줄 · 복원 완료 줄 · CRLF 없음 · 은퇴 시드 `note=retired-seed-text` | SS:606 통과(phoenix VERIFIED·COMPLETE 4역할 · 한글 cwd · Traceback 0) |

관문 결과 보고 서식(:111-113) = 「W-n: 통과\|적\|해당 없음 · 관측 1줄 · 원문 첨부」 + 마지막에 `$h0` 대조 1줄.

### B. winqueue(`docs/HANDOFF-cysr-1110-winqueue-2026-10-21.md` · 통합 HANDOFF:60 「① winqueue(축1 휠·축2 layout_why·자리표)」) — 8 + 발행 전 검토 2(WINQ-9·10)

| ID | 출처 | 무엇을 | 어떻게 | 통과 기준 | 맥 확인 / 안 된 이유 |
|---|---|---|---|---|---|
| WINQ-1 | :17-33 · :109 「축1 의 윈 효과도 맥 검체로만 확인」 | `state.rs Surface::apply_pending_input` + `governance::is_page_scroll_chunk`(`src/bin/cysd/governance.rs:8827`) — PgUp/PgDn 뿐인 입력은 「사람이 치는 중」 으로 세지 않음 | **제안**: WG-2 좌석에서 휠 수십 칸 → `cysr status --json` 의 그 좌석 `pending_input_human_bytes`·`queue_blocked_by` → `cysr send --queued --to <역할> "핑"` | **제안**: 휠 뒤 계수 0 유지(1.1.9 실측 3364/2776 이 재발하지 않음) · `input_pending` 아님 · 큐 배달 | 맥 검체 `winqueue_alt_screen_page_scroll_keys_are_not_a_draft`·`wq_fullscreen_wheel_scroll_does_not_block_queue` 녹 · 뮤턴트 적 · 윈 휠 번역(`ui/src/altscroll.ts:170`)은 윈 GUI 전용 |
| WINQ-2 | :42 「윈 실기 확인 필요」 · :51-54 「윈 실기 확인 절차(3줄)」 | `readiness::composer_layout_why`(`src/readiness.rs:1454`) → `screen_diag.layout_why` | 출처 절차(:52-53): fullscreen 좌석, 입력줄 비움 → `cys send --queued --to <역할> "핑"` → 10초 뒤 `%LOCALAPPDATA%\cys\queue-blocked.json` 그 행의 `screen_diag.layout_why` + `cys read-screen --surface <ref>` 아래 8줄 기록 | 값과 화면 사본을 **수집**(판정 아님 · 수리는 다음 티켓 :54) | 맥 claude 2.1.306 fullscreen 픽스처 2종은 배달됨 · 윈 화면 사본이 저장소에 없음(:42) |
| WINQ-3 | :68-71 「윈 실기 확인 필요(3줄)」 | `ui/src/placeholderclose.ts:34`(`PLACEHOLDER_MAX_LINES_WIN=4`)·:106 · `ui/src/main.ts` 회수 루프 | 출처 절차(:69-71): 콜드 기동 → 손대지 않음 → 편성 도착 3~6초 안에 자리표 창이 닫히는지 · 안 닫히면 화면 사진 | 사람 손 없이 닫힘 · 안 닫히면 ConPTY 가 배너를 개행으로 다시 찍는 경우 → 기준선 방식(:104) | `placeholderclose.test.ts`·배선 핀 녹 · 뮤턴트 2 적 · 윈 상한 4 는 PowerShell 5.1 배너에서 추론(실측 0 :58) |
| WINQ-4 | :77 ⑴ | `alt_screen_notice`(`src/bin/cys.rs:15578`) 윈 힌트 문구 | **제안**: fullscreen claude 좌석을 `cysr launch-agent` 로 띄우고 stderr hint 줄을 읽음 | **제안**: 「GUI 가 휠을 PgUp/PgDn 키로 바꿔 보내 대화가 반 화면씩 올라갑니다」 있음 · 「비지원·휠 안 됨」 없음 | 진리표 핀 `alt_screen_notice_truth_table` 녹 · 원 결함 관측 = SS:609 「hint 문안 모순」 |
| WINQ-5 | :81 ⑸ · :131 「윈 의미론은 OS 인자판…으로만 쟀다」 | `caller_env_keeps_config_dir(_on)`(`src/bin/cysd/state.rs:3263·3271`) — `C:\Users\x/.cys/claude` 구분자 혼용 | **제안**: `cysr launch-agent --role worker --agent claude` → 계정 표시가 「확인 중」 이 아닌지 · 좌석 `config_dir_trusted` 값 | **제안**: true · 계정 확인됨 | 시험 `winqueue_config_dir_trust_compares_paths_not_spellings_on_windows`(맥에서 윈 의미론) 녹 · 뮤턴트 적 · 윈 바이너리 실행 0 |
| WINQ-6 | :82 ⑹ | `cys factory-reset --plan` 의 「창 안 실행 거부」 를 실집행에만 | **제안**: WG-4 #6 을 좌석 창 안에서 직접 `cysr factory-reset --plan` | **제안**: 거부 없이 계획 출력 · rc 0 · 데몬 무접촉 · 부기(:82): `probe_trash_root` 가 격리 폴더가 없으면 만든다 → W-4 #6 「쓰기 0」 과 미세 차이(해석 — 폴더 생성 1건은 적이 아님) | 전용 시험 이름 없음 · 1.1.9 윈 실측 = 거부(SS:607) |
| WINQ-7 | :80 ⑷ · 커밋 `fa56bd91` 제목 「윈 1.1.9 실기 W-2 문안·관측」 | `directive.verify` 의 `verify_denied` 문구(거부 규칙 무변경) | **제안**: 윈 master 창에서 `cysr launch-agent …` 출력 확인 | **제안**: 「이 launch-agent 가 cys pane 안에서 실행돼 데몬이 검증 상태 기록을 받지 않는다…」 문구 · 「구 데몬?」 없음 | 문구는 플랫폼 공통(해석) · 원 관측 = SS:609 |
| WINQ-8 | :110-111 §8 한계 | cursor 모드 휠(화살표)은 여전히 초안으로 셈 · ~~휠이 `last_human_input` 을 갱신해 3초 직접 send 보류~~ → 발행 전 검토 review-a R1(`b75d8b25`)이 해소(실제 영향은 큐 30초 보류였다 · WINQ-9) | 절차 없음 — 알려진 잔여 | 보이면 「알려진 잔여」 로 분류(적 아님 · 해석) | 의도된 보수 · 범위 밖 |
| WINQ-9 | 발행 전 검토 review-a R1(`b75d8b25` · `docs/HANDOFF-cysr-1110-prerelease-review-a-2026-10-22.md` §2 · master#4a059fc9 ④) | `surface.send_text` 처리기(`src/bin/cysd/handlers.rs` 6362 부근) — 대체화면 + PgUp/PgDn 만인 입력은 타이핑 가드(`last_human_input`)를 찍지 않음(계수 면제와 같은 조건). 수리 전 = 휠마다 가드 → 그 좌석 `--queued` 가 마지막 휠 뒤 30초(`queue_human_quiet_secs`) `human_typing` 보류 | **제안**: WG-2 좌석에서 휠을 위아래로 수 초 굴리는 중에 다른 창에서 `cysr send --queued --to <역할> "핑"` → **휠을 멈추고 시계를 본다** → 들어간 시각 · 들어가기 전 `cysr status --json` 그 좌석 `queue_blocked_by` | **제안**: 휠을 멈춘 뒤 수 초 안에 「핑」 이 들어감(30초 기다림 없음) · 보류 사유에 `human_typing(사람 입력 직후)` 없음 | 맥 = 실 대체화면 좌석 처리기 경유 시험 `alt_screen_page_scroll_wheel_does_not_arm_typing_guard` 녹 · 원 코드·뮤턴트 적 · 윈 휠 번역은 윈 GUI 전용 |
| WINQ-10 | 발행 전 검토 review-a 지적표 A 「자리표 isWrapped」(같은 HANDOFF §3 · 확신도 하) · master#4a059fc9 ④ | `ui/src/placeholderclose.ts:55` 가 줄 접힘을 xterm `isWrapped` 로만 한 줄로 셈 — ConPTY 가 리사이즈 뒤 줄 단위로 다시 찍으면 88자 PowerShell 5.1 안내 줄(「Install the latest PowerShell … https://aka.ms/PSWindows」)이 2~3줄로 세어져 상한 4(`PLACEHOLDER_MAX_LINES_WIN`) 초과 | **제안**: 콜드 기동 직후 자리표 창이 떠 있는 동안 창을 좌우로 쪼개 **88열 미만**으로 만든 뒤 편성 도착을 기다림 | **제안**: 88열 미만이어도 자리표가 사람 손 없이 닫힘 · 안 닫히면 화면 사진 + 그 창 폭(열 수) — 실패 방향은 「안 닫힘」(종전 결함과 같은 꼴 · 데이터 손실 없음) | 맥 = `placeholderclose.test.ts` 녹(접힘 표지 있는 경우만) · ConPTY 재도색 꼴은 윈에만 |

### C. minor(`docs/HANDOFF-cysr-1110-minor-2026-10-21.md` · :129 「③⑥⑦ 은 윈 실기에서 … 확인해야 해소다」) — 3

| ID | 출처 | 무엇을 | 어떻게 | 통과 기준 | 맥 |
|---|---|---|---|---|---|
| MINOR-3 | :16 · :57-69 「판정만 · 윈 실기 필요」 | `interpreter_entry`(`governance.rs:3964`)의 `powershell -Command` 판독 · `windows_exec_flag`(`state.rs:8769`) | 출처(:67) 「윈 좌석 뿌리의 실제 argv — launch-agent 좌석이 `-Command` 로 뜨는지, `-NoExit` 가 붙는지」 · **제안 명령**: `Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" \| Select-Object ProcessId,ParentProcessId,CommandLine \| Format-List` | 출처에 통과 기준 없음 — **수집**(판독 결과로 PowerShell 매개변수 표를 고칠지 정함 :68-69) | `seat1110_windows_shell_root_readings_are_pinned` = 현행 판독 고정 · 코드 변경 0 |
| MINOR-6 | :19 · :84-96 「수리 · 윈 실기 필요」 | `javis_runtime_seal.py classify`(:219) · `DLLS_COPIED_MARKERS`(:206-207) | 출처(:96) 「새 설치 doctor runtime-seal = OK 이고 runtime_managed 목록에 그 파일이 뜨는지 · 실제 파일 sha256 = `mingw64\bin\git.exe` sha256」 · **제안**: `cysr doctor` + `Get-FileHash` 두 파일(`%LOCALAPPDATA%\cys\runtime\git\mingw64\libexec\git-core\dlls-copied.exe` ↔ `…\mingw64\bin\git.exe`) | :96 그대로(1.1.8 윈 doctor 의 `FAIL runtime-seal …dlls-copied.exe` 가 OK 로 바뀜) | `test_runtime_seal` 22 등 녹 · 뮤턴트 적 · 실물 파일은 윈에만 |
| MINOR-7 | :20 · :98-108 「수리 · 윈 실기 필요」 | `diag_dept_awakening_seed`(`src/bin/cys.rs:9324`) — 레지스트리에 없는 부서 제외 | 출처(:108) 「같은 기계 doctor 에서 dept-awakening-seed = OK · detail 에 `pack-dept-dept-1` 잔재 표기」(전제 :99-100: `depts.json {}` + `pack-dept-dept-1` 잔존) | :108 그대로(1.1.8 윈 doctor 의 `WARN dept-awakening-seed` 가 OK 로 바뀜) | `diag_dept_awakening_seed_skips_closed_dept_remnant` 녹 · 수리 전 코드 = 적 |

### D. trash-harden(`docs/HANDOFF-cysr-1110-trash-harden-2026-10-21.md` · INTEGRATE §2 ⑦ :47) — 4 + 발행 전 검토 1(TRASH-5)

| ID | 출처 | 무엇을 | 어떻게 | 통과 기준 | 맥 |
|---|---|---|---|---|---|
| TRASH-1 | :50 §2-6 「윈도우 교차 컴파일 미검증 … 실컴파일은 CI 윈도우 잡이 판정」 · INTEGRATE:47 | 새 `src/dirat.rs`(`#[cfg(unix)] pub mod dirat`) · trash.rs·factory_reset.rs 윈 분기 · `src-tauri/src/main.rs` | 출처 = CI 윈도우 잡 · **제안 추가**: 맥에서 `sh scripts/win-typecheck.sh`(§0-4) | **제안**: windows-build·windows-health(·태그 레인 윈 레그) 같은 SHA 성공(1.1.9 체크리스트 1-1 꼴) · win-typecheck rc 0 | 맨 cargo check = libsqlite3-sys 에서 멈춤 · cfg 분기는 읽어서만 맞춤 |
| TRASH-2 | :49 §2-5 「윈도우 휴지통 삭제는 기본 꺼짐(`delete_supported` · 12.W 게이트)」 · :116 ⒞ | `delete_supported`(`trash.rs:1630-1637`) → 거부 문구 `trash.rs:2139` 「이 빌드에서는 휴지통 삭제가 꺼져 있다 — 윈도우 삭제는 12.W 검증을 통과한 빌드에서만 켠다」 · 화면 쪽 「이 빌드에서는 삭제가 꺼져 있습니다 — 목록과 표시는 그대로 동작합니다.」 · M1 확인(`src-tauri/src/main.rs:5202-5210·5290·5311`) | **제안**: Control Center → 「휴지통」 탭 → 항목 고르기 → 미리보기 → 삭제 모달 → 확인 문구 입력 → 「삭제」 | **제안**: 삭제 단추 꺼짐 또는 데몬 거부(삭제 꺼짐 문구) · 격리 폴더 내용 무변경(전후 `Get-ChildItem -Recurse \| Measure-Object` 수) · **`confirm_unbound`(「지우지 않았습니다 … 새로 미리보기를 하세요」 꼴) 안 뜸** = 화면·네이티브 짝 일치 | M1 tauri 시험 4 · ui 시험 녹 · 윈 실행 0 |
| TRASH-3 | :49 「공장 초기화 윈도우 경로는 결박 없이 종전과 같다」 · 커밋 `68ff7c15` 본문 L9 · `e9083e31` L4·L8(「윈도우에선 C:foo 포함 9종」) | factory_reset.rs 윈 경로 · M3 `.producer-<pid>` · 복구 지도 `to_rel` · 드라이브 접두사 거부 | **제안**(⚠파괴적 · 시험 기계에서만 · 백업 뒤): WG-4 #6 plan → 실집행 → 격리 폴더 journal/manifest 의 `to_rel` · `.producer-<pid>` 확인 → `--undo <격리 폴더>` | **제안**: 계획대로 이동 · 원위치 복구 · 표식이 생산자별 · 드라이브 접두사(`C:foo`) 든 `to_rel` 거부 | factory_reset 시험(m4_* · `undo_rejects_a_bad_to_rel…` · `producer_marker…`) 녹 · C:foo 갈래는 윈에서만 도는 검체 → windows-health `--lib factory_reset` 스텝(`windows-health.yml:227` · 해석) · ⚠실집행은 노트북 본체의 자비스 상태를 옮긴다 → 0-3 결정과 함께 **할지 말지 master 판단**(권고: CI 스텝 결과로 갈음하고 본체 실집행은 생략) |
| TRASH-4 | INTEGRATE:39-47 · trash-harden :116 「화면과 네이티브가 함께 출하되어야 한다」 | 윈 번들에 화면 `confirmNonce` + 네이티브 `confirm_nonce` | **제안**: `Select-String -Path "$env:LOCALAPPDATA\cys\cys-app.exe" -Pattern 'confirmNonce','confirm_nonce' -SimpleMatch -List`(이진 파일 검색 = 해석 · 설치 폴더 경로는 설치본에 맞춰) 또는 TRASH-2 조작으로 갈음 | **제안**: 둘 다 있음 · TRASH-2 에서 `confirm_unbound` 없음 | 맥 번들 `strings` 로 둘 다 확인(INTEGRATE §3) · 윈 NSIS 번들 미확인 |
| TRASH-5 | 발행 전 검토 review-b(master#4e61b71e Q1=B · `docs/HANDOFF-cysr-1110-prerelease-review-b-2026-10-22.md`) | 윈도우 · ★cysr-1110-counsel-off ⓓ(master#9ce4ad21 A)로 뒤집힘: `cys-dept reap` 은 윈도우에서도 격리분을 지우지 않고 `TRASH-OLD` 로 알리기만 한다(종전 Q1=B 의 14일 정리 `TRASH-EXPIRE` 갈래 제거 · 판정 못 하면 지우던 fail-open 이었고 자동 호출 0) | **제안**: ① `cysr build-info --json` 에 `"trash_delete_supported":false` 가 있는지 ② (격리분이 있으면) Git Bash 에서 `bash "$LOCALAPPDATA/cys/pack/bin/cys-dept" reap --dry` 로 판정만(지우지 않음 · 팩 경로는 설치본에 맞춰) — ⛔dry 없이 돌리지 않는다 | **제안**: ① false ② 14일 넘은 항목마다 `reap(dry): TRASH-OLD … kept - this tool no longer deletes it` · `TRASH-EXPIRE` 0건 줄 · 요약에 `TRASH-EXPIRE=0`(dry 는 세지 않음) · 휴지통 탭 안내 「… 오래된 항목은 지난 판처럼 약 14일이 지나면 저절로 정리됩니다.」 | 맥 = 하네스 시험(`test_trash_old_marking.py` ⑤~⑧ · 가짜 uname/build-info) · 맥 build-info = true · 윈 실기 0 |

### E. 원작자 편입분(`docs/HANDOFF-cysr-1110-vendor-2026-10-21.md:106` 「5. 윈 실기 — S8 휴지통(윈 삭제 feature 꺼짐 확인)·TOAST 래퍼·HUD 다리(G1) 는 맥 시험만 했다(윈 0)」 + 원작자 커밋 본문 + 원작자 노트) — 15

| ID | 출처 | 무엇을 | 어떻게 | 통과 기준 | 맥 / 비고 |
|---|---|---|---|---|---|
| V1 | vendor :106 · :41(G9) · :85(Q3 codex 정적 통과) · 커밋 `a11687e1` L44-45(「윈도우에서는 named pipe 경로 · 윈도우 실기 검증 없음」) · `a4202a2d` L26-27 · `f4848d77` L20-28 · `3112e06c` L63-65 · `9fc7b9ca` L38-39 · `6cb142b5` L41 | S8 휴지통 탭 목록·비동기 미리보기·삭제 꺼짐 | **제안**: 휴지통 탭 열기 · 목록 · 미리보기 스피너(「확인하는 중… 노드 N · S초」) → 삭제 시도(TRASH-2 와 같은 조작) | **제안**: 목록·미리보기 동작 · 삭제 거부 · 14일 지난 항목도 저절로 지워지지 않는다(TRASH-5 · cysr-1110-counsel-off ⓓ) · 빈 휴지통이면 「휴지통이 비어 있습니다.」 | 맥 시험만(vendor :106) |
| V2 | vendor :106 · :44(G13 `ALERTS_QUIET=false`(`ui/src/alertquiet.ts:64`)·`ALERT_PROSE_QUIET=false`(`src/bin/cys.rs:3481`)) · 커밋 `c9e84636` L13-14(「앱 번들 변경 — 맥·윈도우 재빌드 · 윈도우 실기」) · `a708ba3d` L12 · `e0661d8a` L12 · `e06477c3` L16 · `1a4e4183` L16(「실제 OS 알림 권한 흐름 · 윈도우 실기」) | TOAST 축 래퍼(데몬 출처 알림) + 큐 폐기 알림 연결(`7bea2400`) | **제안**: ① 큐에 대기 지시를 2건 쌓은 좌석을 사람이 닫는다(창 닫기) → 오른쪽 아래 알림 ② `cysr feed push --wait --title "시험" --body "시험"` → OS 배너 ③ CLI 경보 산문 | **제안**: ① 박스 1 · 문구 「대기 중이던 지시 2건을 버렸습니다(기록은 남아 있습니다)」(INTEGRATE §2 표) · OS 배너 0 · 알람 이력 1 ② 승인 요청 = 오른쪽 아래 박스 1 · ★OS 배너 0(master#4e61b71e Q2=B — 토스트가 보이는 우리 출하 값에서는 R2 배너를 더하지 않는다 = 1.1.9 동작) ③ 1.1.9 와 같은 배너 | toastaxis 시험 두 값 녹(맥) |
| V3 | vendor :106·:38(G1) · `docs/RELEASE_NOTES_0.14.49.md:9` 「재지 않은 것: 윈도우 11 … `office-bridge.log` 판정 · 한글 윈도우(cp949) 실기」 · :48-50 · 커밋 `c8f611ec` L18 · `2f40c8fa` L13 · `b78a58e9` L6 · `1791fc1a` L10 · `b1ef81d2` L8 · `fcf41fe0` L6 · `a3408d5f` L14 · `HANDOFF-1110.md:87` | HUD(오피스 화면) 다리가 비UTF-8 로케일에서 구독 스레드를 잃던 수리 | 판정식 = RN 0.14.49:49 「있음 · 비어 있지 않음 → UnicodeDecodeError 줄 0 → _reader 스레드 예외 줄 0」 · **제안**: 한글 윈(949)에서 오피스 탭 + 한글 이벤트 뒤 `Select-String -Path "$env:LOCALAPPDATA\cys\office-bridge.log" -Pattern 'UnicodeDecodeError','Traceback'`(로그 자리 = cysd `main.rs:2045` state_dir · 윈 state_dir = `%LOCALAPPDATA%\cys` 는 winqueue:53 근거 · 해석) | RN 판정식 + 오피스 화면이 계속 갱신 | 맥 ko_KR.CP949 로케일 41/41 · CI T5c cp1252 42/42(런 38051474831) |
| V4 | vendor :39(G2 「우리 BOM 벗기기를 원작자 단일 디코더 안으로」) · 커밋 `81f99cb5` L14 · `236f3d86` L12(「Not-tested: Windows」) · RN 0.14.50:78 | F7 승인 저장소 단일 디코더(BOM) | **제안**: `cysr feed push --wait --title "시험" --body "시험"` → 허락 1회 왕복(V2 ② 와 같은 조작) | **제안**: rc 0(allow) · 판독 오류 없음 | 21행 parity 말뭉치(맥) · 윈 cysd 레인은 비차단 |
| V5 | 커밋 `48739eb0` L13 · `1b1fa3aa` L11(「two-spelling dedupe of one pack folder on Windows」) · `a93d2ce9` L13 · `82d94dbb` L9 · `1b5da27f` L1 | F10 hooks/ 드리프트 보고 · `cys doctor --lanes`(신설) | **제안**: `cysr doctor --lanes` · `cysr doctor --lanes --json` | **제안**: 같은 팩 폴더가 두 철자로 두 줄 나오지 않음 · 종료코드 0 · CI 차단 스텝(`windows-health.yml:918`) 녹 | FIFO·심링크 검체는 unix 전용 |
| V6 | 커밋 `a72cf169` L23(「H-WIN-17 registered, not run」) · RN 0.14.50:79 | B-057 soul L0(Git Bash L0 블록 · CRLF soul · 제목 0개 경보 · 포인터 경로) | CI windows-health 「부트스트랩 건강성 — H-WIN 검체 실기」(:102)의 H-WIN-17 결과 · 실기 명령 출처 없음 | **제안**: H-WIN-17 PASS | 미실행 |
| V7 | RN 0.14.50:46 「윈도우에서는 『unavailable』이고 자식을 띄우지 않습니다」 · :81 · 커밋 `acad0348` L9·L21 · `488c499d` L14 · `8c2e1a24` L3(우리 NOWIN 추가) | F5 product-cpu | **제안**: 동봉 python 으로 `javis_resource_gate.py product-cpu --json` | RN :46 「항상 종료코드 0」 · unavailable · 콘솔 창 깜빡임 0(제안) | `test_nowin_captured_spawns` 녹 · 픽스처는 POSIX |
| V8 | 커밋 `7e3a1387` L22 · RN 0.14.50:57-62 「새 한도는 다음 릴리스 런에서 처음 윈도우를 만납니다」 | H-SECRET-1 `--all` 한도 624초 | CI(태그 레인 윈 레그 · windows-health) 소요 시간 확인 — 실기 대상 아님(해석) | 한도 안 통과(제안) | 맥 H-SECRET-1 GREEN 853파일 |
| V9 | RN 0.14.50:85-87(윈 cysd 26회 중 17회 간헐 실패 · PoisonError 사슬 · 관문 G6) · 커밋 `f4848d77` L24-26(「continue-on-error … conclusion 을 증거로 인용하지 않는다」) | 윈 cysd 시험 로그를 고정 목록과 대조 | windows-health 「cysd-win 결과 판독」(:687) 로그의 실패 이름 확인 | **제안**: 목록 밖 실패 0 · ⚠`PINNED-SET.json`·`check_health_log.py` 는 우리 저장소에 없음(git ls-files 0) → 우리 판이 G6 을 채택했는지 근거 없음(해석) | — |
| V10 | 커밋 `61d531bb` L75-80(「윈도우 레그는 CI 가 유일 경로」) · `5cd5e55c` L35(차이 없음) | S1/S2 quiescing(`cysr status` 의 `quiescing (stale Ns)`) | CI only · 별도 실기 출처 없음 | CI 녹 | cfg 분기 0 |
| V11 | 커밋 `5f31073b` L6(「윈도우에서만 … 적색」)·L27 · `ee67d72e` L40 · `3510becf` L36 · `15be316f` L28 · `b6ef9f1f` L30 · `729495ef` L32 · `99adfc6c` L26 · `650c2c5e` L128 · `d6ce4660` L109 · `f16cdc8c` L89 · `9bd04c66` L57 · `5102506f` L106 · `aa4a8ac4` L30 · `8bcc2253` L9 | S8 검체·미리보기 성능의 윈 적색 수리 | windows-health cysd 감독자 축(:580 · **continue-on-error**) 로그에서 `trash::` 실패 이름 확인 | **제안**: `trash::` 실패 0 | 맥 debug 측정만 |
| V12 | 커밋 `4148fc13` L48-50(「`find -mtime` … 윈도우에서 이 bash 경로는 돌지 않는다 … 검증은 맥에서만」) · `8211c199` L23 | `cys-dept` sweep/reap 이 지우지 않음 | **제안**: 부서 닫기 뒤 격리분이 지워지지 않는지(해석) | **제안**: 삭제 0 | 맥만 |
| V13 | 커밋 `8c413628` L47 · `019f230e` L47 · `26ed21d6` L44 · `b49da82f` L34 · `8d3ebce4` L31 · `4e802ad9` L42 · `d518be11` L3·L40 | 시험·문서 전용 변경 | CI: windows-build 「Secret/PII scan」(:41) · windows-health `--lib` 는 필터형이라 names 시험이 안 돎(`26ed21d6` L44) | 실기 대상 아님(해석) | — |
| V14 | 커밋 `19c4cc29` L61 · `d1ad4db8` L77 · `39ab25e8` L57 | S7 승인 사유 기록 | vendor :43 G12 「해당 없음 — 17커밋 전부 되돌림(순변화 0)」 | 해당 없음 | — |
| V15 | RN 0.14.50:80 「한글 윈도우(cp949) 실기 · 윈도우 설치 파일을 실제로 실행해 설치하는 것 · 앱 안 Update 버튼」 | 원작자 미측정 3종 | 해석: cp949 = WG-6 · 설치 = 1.1.10 설치본 자체(§2 ⓒ) · 앱 안 Update 버튼은 우리 1.1.8 에서 삭제(`RELEASE.md:429-431`) | — | — |

### F. 우리 소형 가지 — 6

| ID | 출처 | 무엇을 | 어떻게 | 통과 기준 | 맥 |
|---|---|---|---|---|---|
| MENU-1 | 커밋 `c120be7a` 본문 L10 → `docs/menu-top-row-evidence/REPORT.md:37` 「윈은 Segoe UI + 맑은 고딕 … 윈 실측은 없다」 | 위쪽 단추줄의 피드백·상담소·아고라 단추 폭 | **제안**: 창 폭 1280·1024·800·640 에서 위쪽 단추줄 사진 4장 | 맥 기준 「800폭 넘침 0」(:37) · 윈 기준은 제안(단추가 잘리거나 두 줄로 안 감) | 맥 글꼴 헤드리스 실측 |
| MENU-2 | REPORT.md:38 | WebView2 가로 스크롤 막대가 38px 단추줄을 가리는지 | 위와 같이(상담소 뱃지 켬 · 맥 셈으로 ≈772폭부터) | **제안**: 단추 가림 없음 | 셈만 |
| MENU-3 | REPORT.md:39 | 윈 125·150% 화면 배율 → 900폭 이하 여백 규칙 | **제안**: 윈 디스플레이 배율을 바꿔 확인 | **제안**: 단추 좌우 여백 8px(900폭 이하) | — |
| MENU-4 | REPORT.md:41 | 화면 설정 「상단 단추」 11 → 13줄 · 상담소·아고라 토글 | **제안**: 화면 설정 → 상단 단추에서 상담소·아고라 끄고 켜고 순서 바꾸기 | **제안**: 토글·순서 바꾸기 동작 · 다시 켜도 기억 | — |
| MENU-5 | REPORT.md:42 | 저장 배치 새 규칙 — 1.1.9 에서 순서를 저장한 윈 기계를 업그레이드 | **제안**: §2 의 설치(업데이트) 뒤 위쪽 단추줄 확인 | **제안**: 두 단추가 피드백 바로 뒤 | topbarlayout 시험 |
| BACKLOG-1 | 커밋 `de8e1cd2` 본문 L8 「윈 대소문자 무관」 | `src/bin/cysd/accounts.rs` `report_outside_at` 정규화·귀속 | 해석: 공유 projects 심링크 구성(acct-switch.sh = bash)이 윈에서 쓰인다는 근거 없음 → **제안**: 윈 좌석 사용량이 올바른 계정 칸에 붙는지 1회 관측 | 제안 | `accounts::` 153/0 |

윈 항목이 없는 출처: popfont(`af852096` 본문에 윈 언급 없음 — 단 글꼴 크기 체감은 MENU-1 사진에서 화면 설정을 열어 함께 보면 된다 · 제안) · docs/1110-naming(`29f02a2d` · 앱 윈 실기 항목 없음) · 통합 HANDOFF:60·INTEGRATE:47 은 위 B·C·D 를 가리키는 색인.

**합계 48** = WIN-GATE 9 · winqueue 8 + 발행 전 검토 2(WINQ-9·10) · minor 3 · trash-harden 4 + 발행 전 검토 1(TRASH-5) · 원작자 편입 15(그중 V14 해당 없음 · V8·V13 실기 대상 아님 · V6·V9·V10·V11 = CI 로그 판독) · menu-top-row 5 · backlog 1.
노트북 본체에서 사람 화면 조작이 필요한 것 = WG-1~4·6 · WINQ-1~7·9·10 · MINOR-3·6·7 · TRASH-2·4·5 · V1·V2·V3·V4·V5·V7·V12 · MENU-1~5 · BACKLOG-1. CI 로그로 보는 것 = TRASH-1 · V6·V8·V9·V10·V11·V13. 판단 대기 = TRASH-3(본체 실집행 여부).

### G. CI 윈도우 잡(실기 전에 같은 SHA 초록)

| 워크플로 | 잡 · 줄 | 트리거 | 1.1.10 관련 스텝(줄) |
|---|---|---|---|
| `windows-health.yml` 「windows-health (H-WIN 실기)」 | `win-health` :60 · windows-latest :61 | push `feat/**`·`fix/**` · tags `v*` · dispatch(:49-52) | H-WIN :102 · phoenix :216 · lib factory_reset…claude_tui :227 · cysd 감독자 축 :580(**continue-on-error**) · 판독 :687 · hwmon :779 · F10 :918(차단) · UI bun :954 · 스택 :974 |
| `windows-build.yml` 「windows-build (feasibility)」 | `build` :33 · windows-latest :34 | push `feat/windows-x64-dist`·`fix/**`(:18) · dispatch | Secret scan :41 · NSIS 빌드 :126 · 산출물 올리기 :189 · updnotice :150 · VERSIONINFO :202 · 자기완결 :229 · runtime-manifest :316 · PTY :350 · T3 :438 · T4 :690 · T5 :1186 · T5b :1231 · **T5c HUD :1264** · T7 :1422 · T8 :1489 · ⚠이 레인은 `CYSR_RELEASE_SEQ` 를 넘기지 않는다 → 산출물 setup.exe 의 release_seq = 0(`build.rs:308-311` 미지정 = 0) |
| `release.yml` | `windows-health-gate` :112(같은 SHA 의 windows-health 결과 결박) · `build` :163 matrix windows-latest / x86_64-pc-windows-msvc :184-185 | tags `v*` | — |
| `ci-branch.yml` | `macos-rust-pack` :35 의 스텝 「윈도우 교차 타입체크(scripts/win-typecheck.sh …)」 :1605 | push `feat/**`·`fix/**`(:27) | 맥에서 윈 cfg 타입체크 |

## 2. 윈 master 에게 보낼 실기 절차 초안

### 2-0. 먼저 정할 것(맥 master · 체크리스트 0-3)

- **ⓐ 절단 전 기능 확인 = `windows-build` dispatch 산출물**(태그 없이 · 같은 SHA) — 실제 발행 바이트가 아니고 release_seq = 0 이다. 깔면 그 노트북은 자동 갱신 대상에서 빠진다(min_from ≥1). 기능 확인점(§1 의 사람 조작 항목)을 절단 전에 끝낼 수 있다.
- **ⓑ 1.1.9 선례 = 태그 뒤 draft setup.exe** 를 시험 키트(jarvis-install prerelease `wintest-v1.1.10-<날짜>` + bootstrap.ps1 핀 4줄만 교체 · SS:621~626)로 — 실제 발행 바이트 · 「직전 판(1.1.9) → 새 판」 업데이트를 그대로 잰다 · 단 적이 나오면 태그 번호를 다시 쓸 수 없다(`docs/RELEASE-ROLLBACK.md:20-24`).
- 권고 = **ⓐ로 기능 확인점을 절단 전에 · 절단 뒤 ⓑ로 업데이트 1회만**. ⓐ를 깐 노트북은 ⓑ 전에 라이브 한 줄(1.1.9 핀)로 1.1.9 로 되돌린다 — 그래야 ⓑ가 「1.1.9 → 1.1.10」 시험이 된다. 이 노트북은 자동 받기 관측용(체크리스트 0-4)이 될 수 없다.
- 아래 절차는 두 경우 모두에 쓰이게 `<KIT>`(시험 키트 주소)만 바꾸면 되도록 썼다. 1.1.8 u5-body 브리프(`~/axdev/master/relay-acct1/brief-u5-body-20261008c.md`)의 꼴을 따랐다.

### 2-1. 요청문 초안(relay 로 그대로 · `<…>` 만 채움)

```
[실기 · TICKET=cysr-1110-winfield] 노트북 본체 1.1.9 → 1.1.10(<ⓐ 기능 확인 | ⓑ 발행 바이트 업데이트>) · 상한 90분 · 박사님 손 0
너는 지금 업데이트될 바로 그 cys 안의 좌석이다. 설치 도중 데몬이 바뀌는 순간 네 창도 다시 켜진다(대화는 이어진다). 순서대로 따른다.
판정은 맥 master 가 한다 — 해석 없이 출력 원문만 회신한다.

ⓐ 시작 전 기록(전부 파일로 · 복원 뒤 비교)
   $R = "$env:USERPROFILE\w1110"; New-Item -ItemType Directory -Force $R | Out-Null
   & "$env:LOCALAPPDATA\cys\cys.exe" --version                          > $R\a-version.txt
   & "$env:LOCALAPPDATA\cys\cys.exe" build-info --json                  > $R\a-build-info.txt
   & "$env:LOCALAPPDATA\cys\cys.exe" list                               > $R\a-list.txt
   & "$env:LOCALAPPDATA\cys\cys.exe" doctor                             > $R\a-doctor.txt
   Get-ChildItem -Force "$env:USERPROFILE\.cys" | Select-Object Name    > $R\a-cys-items.txt
   $P = "$env:USERPROFILE\.claude\settings.json"; $(if (Test-Path $P) { (Get-FileHash $P -Algorithm SHA256).Hash } else { 'absent' }) > $R\a-h0.txt
   (메모 1줄을 $R\note.txt 에: 「설치 창을 작업 스케줄러로 띄움 · 복원 뒤 ⓓ 부터」)

ⓑ 백업(되돌림 준비)
   Copy-Item -Recurse -Force "$env:USERPROFILE\.cys\pack" "$env:USERPROFILE\.cys-pack-bak-119"
   (이미 같은 이름이 있으면 덮지 말고 -bak-119b 로 · 개수: (Get-ChildItem -Recurse -File <폴더> | Measure-Object).Count > $R\b-pack-files.txt)
   되돌림 = 라이브 한 줄(1.1.9 핀) · 설치기 1.1.9 사본은 따로 받지 않는다.

ⓒ 설치 창을 **작업 스케줄러로** 띄운다(⚠네 셸에서 직접 Start-Process 하지 마라 — 좌석 셸 자식은 데몬 교체 순간 함께 꺼진다)
   irm <KIT>/bootstrap.ps1 -OutFile $env:USERPROFILE\install-jarvis.ps1
   $a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$env:USERPROFILE\install-jarvis.ps1`""
   Register-ScheduledTask -TaskName 'jarvis-w1110' -Action $a -Force | Out-Null
   Start-ScheduledTask -TaskName 'jarvis-w1110'
   Start-Sleep 5; Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Select-Object ProcessId, ParentProcessId, CommandLine | Format-List > $R\c-launch.txt
   → 부모가 svchost(작업 스케줄러)여야 한다. 네 셸이면 즉시 작업을 지우고 회신.
   설치가 끝나면: Unregister-ScheduledTask -TaskName 'jarvis-w1110' -Confirm:$false

ⓓ 설치 뒤 기본 확인(네 창이 다시 켜진 뒤 · note.txt 먼저)
   $C = "$env:LOCALAPPDATA\cys\cys.exe"
   1) & $C --version ; & $C build-info --json      (기대: 1.1.10 · ⓐ키트면 release_seq 0 · ⓑ키트면 5)
   2) & $C self-update --journal-state --json
   3) Select-String -Path "$env:USERPROFILE\install-jarvis\bootstrap.log" -Pattern 'txn: held|txn: released|rollback assets|J-UPD|daemon precheck|rotate'
      (ⓑ 키트 = 발행 전 draft 라 「rollback assets: rc=4 … unreachable」 은 예상 · 1.1.9 실측 SS:614)
   4) & $C list   (ⓐ a-list 와 같은 역할이 살아 있는가)
   5) Get-ChildItem -Force "$env:USERPROFILE\.cys" | Select-Object Name   (ⓐ 와 비교 · 빠진 이름)
   6) & $C doctor   (ⓐ 와 FAIL·WARN 줄 비교 · 기대: runtime-seal dlls-copied.exe FAIL → OK(MINOR-6) · dept-awakening-seed WARN → OK(MINOR-7))
   7) 개인 프로필 해시 = a-h0.txt 와 같음

ⓔ 확인점(첨부 2파일 · 순서대로 · 항목마다 「ID: 통과|적|해당 없음 · 관측 1줄 · 원문」)
   첨부 1 = docs/upstream/WIN-GATE-1110.md(W-0~W-6 명령 원문) — W-4 #6 은 좌석 창 안에서 직접 `cysr factory-reset --plan`(1.1.10 에서 창 안 허용)
   첨부 2 = 이 문서 §1 B·C·D·E·F 표의 사람 조작 항목(WINQ-1~7·9·10 · MINOR-3·6·7 · TRASH-2·4·5 · V1·V2·V3·V4·V5·V7·V12 · MENU-1~5 · BACKLOG-1)
   ⛔TRASH-3(공장 초기화 실집행)은 하지 않는다(맥 master 별도 지시가 있을 때만).
   ⛔휴지통 시험(TRASH-2·V1)은 「삭제」 를 눌러도 지워지지 않는 것이 정상이다 — 지워지면 즉시 멈추고 회신. (단 14일 지난 항목이 정리 작업으로 사라지는 것은 정상이다 — TRASH-5)

막히면(설치 창이 [N/10] 에서 5분 넘게 멈춤 · 네 창이 10분 넘게 안 돌아옴) 그 자리의 화면 글자 원문과 bootstrap.log 마지막 30줄을 회신하고 멈춘다. 되돌림은 맥 master 지시가 있을 때만.

회신: ⓐ 파일 7개 원문 · ⓑ 수 · ⓒ c-launch.txt · ⓓ 1~7 원문 · ⓔ 항목별 줄 + 원문. 정리: 작업 jarvis-w1110 삭제 확인 · 백업 폴더 보존.
```

### 2-2. 맥 master 판정표(회신이 오면)

| 판정 | 조건 |
|---|---|
| 라이브 금지(적) | WG-3·WG-3L ⓐ(선택 강조 이동) · TRASH-2 에서 **실제로 지워짐** 또는 `confirm_unbound` · ⓓ 4) 역할 소실 · ⓓ 7) 개인 프로필 해시 바뀜 · 설치 실패 |
| 통과 | 나머지 기대값 일치 |
| 수집(판정 아님) | WINQ-2 · MINOR-3 · WINQ-8 |
| 알려진 잔여 | WINQ-8(cursor 모드 휠) |
| 표가 틀렸을 수 있음 | **제안** 표시 항목의 기대와 다름 → 원문으로 표를 고칠지 결함인지 맥에서 가린다 |

통과하면 `docs/RELEASE.md:436` 칸 「★1.1.10 윈도우 실기 확인 — 상태: 실기 미검증」 을 결과로 바꾸고(문서 커밋) 결과 원문 경로를 적는다 — 1.1.9 때처럼 결과가 저장소 밖에만 남지 않게(§0-1).
