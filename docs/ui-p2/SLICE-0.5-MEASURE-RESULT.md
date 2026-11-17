# 조각 0.5 실측 결과 — cysr 화면 개편 2단계

- TICKET=cysr-ui-slice05-measure-1117 · 2026-11-17 21:20~ · 워커 surface:2145 · 브리프 [master 925ea80a](원장 대조 성립) · 계획 = `SLICE-0.5-MEASURE-PLAN.md`
- 환경: tart VM 복제본 **`s05-measure`**(← `jarvis-clean-vanilla` · macOS 26.6.2 · CLT 없음) · 앱 = 이 가지 **048610cc** 시험 전용 빌드(업데이터 산출 끔 · ad-hoc 서명 · 서명 키 사용 0) zip sha256 `04a8889e2eaa8fbd68200b277765da16ff6cbce6a82275c91c2cffd95e0ff47a`(반입 전 = VM 안 반입 뒤 · 같음) · VM 안 `codesign --verify --deep --strict` 통과 · Claude Code 2.1.326
- 원 출력 = `docs/ui-p2/evidence/s05/`(VM 홈 경로 → `~` · VM IP 가림 외 원문 그대로)(M1.txt · M1b.txt · M2.txt · M2b.txt · M2c.txt · M2race.txt · M2mid.txt · M3.txt · M10.txt · M11.txt · M12.txt) — 이 문서의 수는 전부 그 파일에서 옮김.
- 대역 좌석 = `tests/fixtures/fake_claude.c` 사본에 「받은 덩이마다 CLOCK_MONOTONIC 시각·길이·16진」 1줄 기록을 더한 것(호스트 스크래치에서 컴파일 · VM 안 `~/fakebin/claude` · 원본 무변경). 좌석은 `cys launch-agent --role worker-fake --agent claude`(= agent_meta 등록 좌석 · clear_first 허용 대상) · VM `.zshrc` 에 「cwd = ~/m1 이면 대역 폴더 먼저」 1줄(VM 한정).
- 보낸 요청 = 계획서 §2 공통 원자 제출 그대로(`surface.send_text {human, quiet, queued:false, clear_first, machine_origin:false, refuse_on_approval}` + VM `operator.token` 을 `operator_token`·`owner_token` 에) — 앱 `send_input` 과 같은 조건 + `refuse_on_approval`.

## G1 경과(관측)

- C(`vm-v117-login-base`) 복제본에서 `claude -p` 1회 → `Failed to authenticate: OAuth session expired and could not be refreshed` → C 복제본 지움 → A(`jarvis-clean-vanilla`) 복제. 원본 2기 무변경(`tart clone` 이 원본의 「Accessed」 시각만 갱신 — 내용 무접촉).

## 결과표

| # | 항목 | 판정 | 실측값(관측) | 출처 파일 | 설계에 주는 것 |
|---|---|---|---|---|---|
| M1 | 원자 제출 바이트·Enter | **성립** | 5/5 회 바이트 순서 = `0x15`(Ctrl-U) → `ESC[200~` + 본문 UTF-8 + `ESC[201~`(한 덩이) → `0x0d` 1개. 간격: Ctrl-U→붙여넣기 **191.6 / 292.6 / 299.9 ms**(최소/중앙/최대) · 붙여넣기→Enter **468.0 / 535.3 / 549.7 ms** · Ctrl-U→Enter 합계 **728.1 / 767.9 / 835.2 ms** · 응답 `{"sent":true}` 왕복 0.45~0.72 ms(쓰기를 기다리지 않고 먼저 돌아옴) | M1.txt · M1b.txt | 설계 「400ms 뒤 Enter」 → 실제 ≈ 470~550 ms · 한 번 보내기가 좌석에 머무는 시간 ≈ 0.73~0.84 초 · 「보냄」 응답은 쓰기 끝이 아님(전달 판정은 세션 기록으로 — 설계대로) |
| M1-b | 여러 줄 본문 | **성립** | 줄바꿈 = 울타리 안 `0x0a` 그대로(Enter 로 바뀌지 않음) · Enter 는 끝에 1개 | M1b.txt | — |
| M2 | 승인 창 떠 있을 때 거부 | **성립(조건부)** | 실제 Claude 꼴 화면(가로줄 + 허락 문구 + `❯ 1. Yes` + 꼬리) = **거부 2/2** · 코드 `approval_screen` · 「nothing written」 · 바이트 0 · 대조(같은 화면 · `refuse_on_approval` 없음) = Ctrl-U·붙여넣기·Enter **모두 들어감**(R1 위험 실재) | M2c.txt | `refuse_on_approval` 은 필수 — Tauri `send_input` 에 그대로 쓰면 R1 이 난다(설계 결정 확인) |
| M2-주 | 거부 판정의 화면 조건 | 관측 | 가로줄이 없는 화면(첫 견본)에서는 쓰기 직전 판정이 거짓 → 보냄·Enter 들어감 · 그런데 승인 대기 항목(`daemon-…`)은 그 뒤 생김 = **대기 항목을 만드는 판정과 쓰기 직전 판정이 다른 술어**(governance.rs `approval_in_prompt_tail` — 가로줄 아래 꼬리 · 가로줄 없으면 커서 행이 번호 선택 줄일 때만) | M2.txt · M2b.txt | 화면 문턱 「승인 창 없음」을 feed 대기 항목으로 잡으면 데몬 거부보다 넓게(먼저) 막는다 — 두 신호를 둘 다 본다 |
| M2-b | 경합 ① 창을 띄운 직후 보냄 | **성립** | 5/5 거부 · 바이트 0 | M2race.txt | — |
| M2-c | 경합 ② **쓰는 도중** 창이 뜸 | **불성립(남는 창)** | 보낸 뒤 0.15 · 0.45 · 0.6 초에 창 → 3/3 모두 Ctrl-U·붙여넣기·**Enter 까지 들어감** · 원자 제출 경로엔 Enter 직전 재판정이 없음 | M2mid.txt | 남는 창 = M1 의 Ctrl-U→Enter 구간 **≈ 0.73~0.84 초**. 설계 R6 「수십 ms」 보다 큼 → 데몬 변경 후보(원자 Inject 의 Enter 직전 승인 재판정) 또는 「알려진 남은 위험」 기록 |
| M3 ⓐ | 사람 표지 초안 있음 | **단점 성립** | `pending_input_human_bytes = 12` 인 상태에서 원자 제출 = 거부 없음 → Ctrl-U 로 그 초안을 지우고 제출(초안 12바이트 → 0) | M3.txt | 설계 「단점(정직)」 그대로 실재 · CLI `--clear-first`(사람 표지 없음)의 「사람 초안이면 거부」와 다름 → 화면 문턱 「입력줄 빈칸」(pending 두 칸 = 0)이 유일한 방어 · 조각 1 수용 기준에 「초안 있음 → 쓰기 0(붙잡음)」 필수 |
| M3 ⓑ | 기계 잔여 | 관측 | 사람 표지 없는 미제출 글은 데몬이 쓰지 않고 `{"held":"awaiting_submit"}` 로 붙잡음 → 입력줄 잔여 0 → 원자 제출 정상 | M3.txt | 「기계 잔여가 입력줄에 남는」 장면은 이 길로는 안 생김(잔여의 출처는 다른 길) |
| M3 ⓒ | 방금 사람 키(1초 안) | 관측 | 사람 표지 `End` 키 1초 뒤 원자 제출 = 통과(타이핑 가드 없음) · `pending_input_bytes=3`(ESC[F) 이었고 Ctrl-U 뒤 0 | M3.txt | 화면 문턱의 `last_human_input` 30초 붙잡기가 이 경우의 유일한 장치(데몬은 막지 않음) |
| M4 | 좌석 안 `javis_mission.py status` | **보류** | 진짜 Claude 로그인 필요 — 재개 조건 = 내일 아침 master 가 `/tmp/claude-501/s05-login-code` 기록(아래 「재개 절차」) | — | — |
| M5 | U25 답하는 중 받은 말 | **보류** | 같음 | — | — |
| M6 | U21 둘째 줄 `/` | **보류(바이트 절반만)** | 보내지는 쪽: 둘째 줄은 울타리 안 `0x0a` 뒤에 놓인다(M1-b) — 받는 쪽 해석(명령 실행 여부)은 진짜 Claude 필요 | M1b.txt | — |
| M7 ⓐ | U20 긴 붙여넣기 기록 꼴 | **보류** | 진짜 Claude 필요 | — | — |
| M7 ⓑ | U20 큐 묶음 배달 | **보류(바이트 절반만)** | 같은 발신자 큐 2건을 0.1초 간격 적재 → **한 덩이로 배달**: 울타리 안 `[큐 다이제스트 2건 · 발신 chat-auto]` / `[1/2] …` / `[2/2] …` → Enter 1개 · 적재→배달 ≈ 1.7초 | M7b-bytes.txt | 「기계 문안끼리만 묶음」(chat-auto) 확인 · 사람 말로 다루는지는 진짜 Claude 몫 |
| M8 | 세션 레코드 `uuid`/`parentUuid` | **보류** | 진짜 Claude 필요(대역 기록은 그 칸을 쓰지 않음) | — | — |
| M9 맥 | U26 세션 id → 파일 | **부분 성립** | cysr 좌석 env = `CLAUDE_CONFIG_DIR=~/.cys/claude` → 세션 파일 = **`~/.cys/claude/projects/<cwd 슬러그>/<id>.jsonl`**(VM 에 `~/.claude*` 폴더 자체가 없음 · 대역 기준 — 대역은 Claude Code 와 같은 규칙으로 쓴다: fake_claude.c:15~16) · 데몬 `control.session_detail` 은 대역 기록(사용량 칸 없음)이라 빈 결과 = 판정 불가 | M9mac.txt | **설계 §13-2 의 `~/.claude*/projects/*/<id>.jsonl` 꼴로는 cysr 좌석을 못 찾는다** → `chat_transcript` 는 좌석 목록의 `claude_config_dir` 칸 + `/projects/` 로 찾아야 함 |
| M9 윈 | U26 윈 | **보류** | 재개 조건 = 조각 10 윈 실기 착수(master G4) | — | — |
| M10 | R3 30초 큐 묶임 | **성립** | 대조(사람 보내기 없음): 큐 적재 → 배달 **2.98 초** · 원자 사람 보내기 직후 적재 → 배달 **31.16 초** | M10.txt | 30초(`CYS_QUEUE_HUMAN_QUIET_SECS` 기본) 실재 · 승계 거절 사유 글은 이번에 안 잼(승계 장면 미구성 — 진짜 마스터 좌석 재개 때) |
| M11 | V-N1 이름 보고자 칸 | **성립(조건 있음)** | `usage.report_named {cwd:~/axdev,…}` → `{"named":"master"}` · 목록 행 = `{name:"master", ctx_pct, ctx_tokens, ctx_window, source, updated_at}` · 대응 없는 cwd = `{"named":null}`(행 안 생김) | M11.txt | 「마스터」 는 `name` 칸으로 읽힌다 · 단 그 이름은 **cwd 접두 대응표**(`CYS_NAMED_REPORTERS` 또는 기본표 = 홈 아래 axdev → master · named.rs:113~150)로만 정해짐 → 참가자 기기엔 기본표 경로가 없어 행이 안 생김 = 설계 대체(「불가 판정 0 = 늘 가능」)가 그 기기의 기본값 |
| M12 | R6 목록 왕복(데몬 몫) | **성립** | `surface.list` 100회: 좌석 1개 p50 **0.10** · p95 0.14 · 최대 0.23 ms(응답 1.4 KB) / 좌석 11개 p50 **0.31** · p95 0.39 · 최대 0.50 ms(응답 12.5 KB) | M12.txt | 데몬 몫은 1 ms 미만 → 「수십 ms」 의 대부분은 웹뷰→Tauri 구간(조각 1 대역 하네스) |

## 설계에 돌려줄 숫자 · 사실(요약 아님 — 위 표의 「설계에 주는 것」 칸 모음)

1. 원자 제출 Ctrl-U→Enter = **0.73~0.84 초**(붙여넣기→Enter 0.47~0.55 초 · 설계의 400 ms 는 실제보다 작음).
2. **쓰는 도중 승인 창 = 막히지 않음**(3/3 · Enter 까지 들어감) — 남는 창 ≈ 0.8 초. 설계 R6 의 「수십 ms」 를 고쳐야 함 · 데몬 변경 후보: 원자 Inject 의 Enter 직전 승인 재판정.
3. 쓰기 직전 판정(가로줄 아래 꼬리)과 승인 대기 항목 판정은 술어가 다르다 → 화면 문턱은 feed 대기 항목도 본다.
4. 사람 표지 원자 제출은 **사람 초안을 지운다**(12 → 0 · 거부 없음) → 화면 문턱 「입력줄 빈칸」 필수 · 조각 1 수용 기준에 넣을 것.
5. 사람 보내기 뒤 큐 배달 묶임 = **31.2 초**(대조 3.0 초).
6. 세션 파일 = **`<좌석 claude_config_dir>/projects/<cwd 슬러그>/<id>.jsonl`** — `~/.claude*` 꼴 아님.
7. 이름 보고자: 역할 = `name` 칸 · cwd 대응표에 기댐(참가자 기기 = 행 없음이 기본).
8. 데몬 목록 왕복 < 1 ms(좌석 11개 p95 0.39 ms).

## 오염 0 지문 F1~F7 (이 기기 · 읽기 전용 · 시작 21:20 표지 파일 기준)

| 지문 | 전 | 뒤 | 판정 |
|---|---|---|---|
| F1 데몬 | cysd pid 90624 · cys-app pid 91537(둘 다 11-07 01:46 시작) | 같음 | **같음**(재기동 0) |
| F2 좌석 표 | 좌석 5 · 해시 fe335e05… | 좌석 6 · 해시 0fd7696e… | **다름 — 측정 밖**: 2148 사라짐 · 2149(worker-3)·2150(worker-4) 생김 = master 편성. 이 티켓에서 이 기기에 친 cys 명령 = `list`·`status`·`identify`·`set-status`·`run`(빌드 묶음)뿐 · 좌석을 만들거나 닫는 명령 0 |
| F3 팩 | 바뀐 파일 0 | 6 | **다름 — 측정 밖**: `round/WORKER_{2,3,4}_TODO.md`(다른 워커 역할 · 21:22~21:35) · `memory/MEMORY.md`·`memory/project_cysr-dept-close-actual-behavior.md`(다른 워커의 기억 · 21:30~21:34) · `state/evt_spool.jsonl`(데몬 상태). 내 역할 파일(`WORKER_TODO.md`) 무변경 |
| F4 앱 | `/Applications/cys.app` 1.1.14 · CDHash f5832925… | 같음 | **같음** · `~/Applications/cys.app` 없음(전후) |
| F5 launchd | 9e4a5eef… · LaunchAgents 80158b6c… | 같음 | **같음** |
| F6 마스터 대화 | 측정 명령은 모두 `tart`·VM ssh(`admin@<VM IP>`)·VM scp 접두 | — | 구조상 0 |
| F7 인박스·원장 | 인박스 173,214줄 · 원장 14,076줄 | 173,295 · 14,087 | 늘어난 인박스 81줄 중 이 좌석 = **1줄(【질문】 21:29)** · 나머지 = sentinel·CSO·worker-2 · 원장 +11 = master 발신(워커는 원장에 쓰지 않음) |

- 이 기기에 남긴 것: 작업트리 `src-tauri/runtime`(1111-int 에서 APFS 복제 · 무시 파일) · 작업트리 `target/release`(시험 빌드 산출) · `/tmp/claude-501/s05-cysr-048610cc.zip` · 스크래치 파일들. 설치·서명 키·`/Applications`·`~/Applications` 쓰기 0.

## VM 복제본

- **`s05-measure` 남김**(master 지시 · 내일 재사용) · 원본 `jarvis-clean-vanilla`·`vm-v117-login-base` 무변경.
- VM 안 상태: cysr 048610cc 설치 · 앱·데몬 실행 중 · 대역 좌석 surface:3(worker-fake · cwd ~/m1) · Claude Code 2.1.326(로그인 안 됨) · VM `.zshrc` 끝 1줄(대역 PATH) · VM `~/.ssh/authorized_keys` 에 시험 공개 키 1개(개인 키 = 이 좌석 스크래치 `vmkey`) · VM `~/rpc.py`·`m3.sh`·`m10.sh`·`m12.py`·`approval*.bin`(16진 견본)·`clear.bin`.
- 지금 VM 은 켜진 채(`tart run` 백그라운드). 내일까지 둘지·멈출지 = master(멈춰도 복제본 디스크는 남음 · `tart stop s05-measure`).

## 재개 절차(M4~M8 · 내일 아침)

- 재사용 도구 사본 = `docs/ui-p2/evidence/s05/tools/`(VM 쪽 `rpc.py`·`m3.sh`·`m10.sh`·`m12.py` · 암호 ssh 도우미 `vmsh`(VM 기본 계정 admin/admin · `VMIP=<ip> vmsh <명령>`) · 대역 원본 `fake_claude_t.c`). 시험 키(`vmkey`)는 이 좌석 스크래치에만 있어 지워졌을 수 있다 — 그러면 `vmsh` 로 접속. VM `/tmp/login.exp` 는 VM 재기동 때 사라질 수 있다 — 사본 = `tools/login.exp`(VM `/tmp/` 로 다시 복사).

1. `tart run --no-graphics s05-measure &` (멈췄다면) → `tart ip s05-measure`.
2. VM 안 `security unlock-keychain -p admin ~/Library/Keychains/login.keychain-db` → `nohup /usr/bin/expect -f /tmp/login.exp &`(VM 안 그대로 있음 · 코드 파일 `/tmp/code` 를 기다려 넣음).
3. 새 승인 주소 → 호스트 `/tmp/claude-501/s05-login-url.txt` 덮어쓰기 · 【질문】 1줄 · master 가 `/tmp/claude-501/s05-login-code` 기록 → VM `/tmp/code` 로 옮김 → `claude auth status`.
4. 대역이 아닌 진짜 마스터 좌석(cwd ≠ ~/m1)으로 계획서 §2 M4·M5·M6·M7ⓐ·M8 · M9 맥의 `control.session_detail` 칸 · M10 의 승계 거절 사유 글.
