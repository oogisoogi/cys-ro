# HANDOFF — TICKET=cysr-1118-seat (갈래 B = 좌석·복원·주입 · master#77bf576d · 추가 ④ master#06f081e8 · ③ 처분 master#44ce6e4c)

- 작업트리 `~/axdev/.wt/cys-1118-seat` · 가지 `feat/1118-seat` · 기점 v1.1.16 `bc8156865`
- 빌드 캐시 = `~/axdev/.wt/cys-1116-rel-c12/target/debug` APFS 복제(같은 기점 · 원본 무변경)
- 시험: `cargo test --lib registry_tests` · `cargo test --test session_lease_e2e residual_focus`

## ① 복원 「명령줄에 대화 id 없는 주인」 구멍

**원인** — 복원 전 「이 대화를 쓰는 작성자가 살아 있나」 바깥 증거가 두 개뿐이었다(`session_lease_cli.rs` `CliWorld::evidence`):
ⓐ 데몬 좌석(topology live) ⓑ 같은 사용자 프로세스 argv 에 대화 id. cysr 밖에서 `claude --continue`(명령줄에 id 없음)로 연 대화,
세션 안 `/resume` 으로 옮겨 간 작성자는 둘 다 못 본다 → `NoneConfirmed` → 같은 대화에 두 번째 작성자를 띄운다.

**증거 ⓒ(새로)** — claude 가 대화형 프로세스마다 쓰는 등록 파일 `<설정 폴더>/sessions/<pid>.json`.
- `sessionId` = 그 프로세스가 **지금 쓰는** 대화. 실측(맥 2.1.330): `claude -r A` → sessionId = A · CSO pid 27336 명령줄 `--resume 69a3…` 인데
  sessionId `da8b…`(세션 안 전환을 따라 갱신 = argv 보다 정확). 원리상 `--continue` 도 같다(sessionId = 쓰는 jsonl 이름 — 이어 쓰면 원 id ·
  갈라지면 새 id = 충돌 없음). ⚠`--continue` 대화형 실측은 하네스(입력 제출) 한계로 미완 — 실기 1회 = 해소 판정 항목.
- 강제 종료 뒤 파일이 남는다(실측) → pid 생존 + 출생 대조 필수.
- 출생 값 `procStart`: 맥 = `LC_ALL=C TZ=UTC ps -o lstart=` 문자열(초 정밀도 · claude 판독 `tRt`) · 윈 = FILETIME(UTC 100ns) 십진
  (윈 master 실측 11-23 00:3x: 살아 있는 4개 모두 `Get-Process … StartTime.ToFileTimeUtc()` 와 자리까지 같음 · `procStartFt` 키는 없음 —
  claude 판독 순서 `procStartFt ?? procStart` 그대로 둘 다 읽음).
- 윈 등록 위치 = `%USERPROFILE%\.cys\claude\sessions`(윈 실측 · `.claude\sessions` 는 0개).

**판정**(`session_lease.rs` `classify_registry` 순수): sessionId 일치 ∧ pid 살아 있음 ∧ 출생 일치 = Seen(rc 92 · 안 띄움) ·
pid 없음 / 같은 pid 다른 출생 = 낡은 파일(건너뜀) · 판독 실패(폴더 권한 · 깨진 파일 · pid 불일치 · sessionId 없음 · 출생 값 못 읽음 ·
생존 판독 실패) = 판정 불가(rc 93) — 단, 죽음 확인된 pid 의 깨진 파일은 건너뜀. 윈 = µs 까지 정확 일치(identity 와 같은 버림 규칙).
- 설정 폴더 전수(`registry_dirs`): `$CLAUDE_CONFIG_DIR` · `$CYS_ACCOUNT_DIR` · `~/.claude` · `~/.cys/claude` · `~/.claude-*` · `~/.cys/claude-*`
  — 심볼릭 링크 폴더는 실체 한 번만(acct2/sessions → ~/.claude/sessions 실측).
- 배선: 등록 Seen 이면 argv 훑기 없이 막음 · 그 밖 = `combine_evidence(argv, reg)`(하나라도 판정 불가면 판정 불가).
- 사유 토큰 `reg:<종류>:<pid>` → `next_action` 안내 1줄(맥 ps · 윈 Get-Process).

**시험** — `registry_tests` 11건(순수 판정 9 + 폴더 중복 제거 + 실제 자식 대조군).
대조군 `real_child_without_id_in_argv_is_seen_only_through_registry`(맥): 명령줄에 id 없는 살아 있는 자식 + 등록 파일 →
붉음 = 종전 argv 훑기 `NoneConfirmed`(구멍) · 초록 = 등록 훑기 `Seen` · 자식 종료 뒤 = `NoneConfirmed`.

**윈 동일성** — 같은 `classify_registry`(win=true 규칙) · 출생 = `process_observation::identity`(윈 = 핸들 GetProcessTimes → µs) ·
⚠윈 identity 는 `observe`(argv 판독 포함)라 상승 프로세스면 판정 불가로 떨어짐(안전 쪽 · 거짓 막힘 가능).

**남는 것** — ⑴ `--continue` 실기 1회(맥·윈) ⑵ 리눅스 procStart 형식 미확인(리눅스면 판정 불가 쪽) ⑶ 등록 파일이 없는 판의 claude(구판) = 종전과 같음.

## ② 재연결 주입 전 터미널 모드 잔류(DECSET 1004)

**원인**(하위 조사 + 코드 확인) — 강제 종료된 claude 가 `ESC[?1004l` 을 못 보내 **뷰어(xterm.js 5.5 `sendFocus`)** 에 포커스 보고가 켜진 채 남고,
포커스가 바뀔 때마다 GUI `send_input`(human) 이 `ESC[O`/`ESC[I` 를 맨 셸로 보낸다(데몬은 자동 응답으로 쳐 초안 계수 0 · 데몬 vt100 은 1004 를 모델링 안 함).
복원 세 경로 중 **in-seat**(`restore_in_seat_boot`)만 기동 글 앞 선정리(C-u)가 없었다(node-recover · launch-agent 재사용은 있음 · 주석은 「C-u + 기동」 이라 적혀 있었음).
결함 실측 = **윈 PowerShell**(SESSION_STATE 11-22 11:2x 「[O[Iclaude … PowerShell 구문 오류」) — ESC 가 빠지고 `[O[I` 글자가 남음.
맥 zsh·readline 은 ESC 열을 키로 삼켜 드러나지 않는다(대조 실측: 맥 기본 셸에서는 고침 없이도 초록).

**고침** — `in_seat_preclear_keys(windows)` 를 기동 글 앞에 보낸다(200ms 쉼): 유닉스 = `C-u` · 윈 = `C-u`(사람 초안 관문) → `Backspace`(PowerShell 이 0x15 를 글자로 넣음 · 1.1.12 r7-7)
→ `Escape`(PSReadLine Windows 모드 = RevertLine · 줄째 비움). Escape 를 node-recover 처럼 빼지 않는 까닭 = 이 경로는 `empty_seats`(에이전트 없음)에서만 열림.
선정리 거부(사람 초안) = 바깥 Err = 0바이트 · 건너뜀 · fresh 폴백 0(호출부 문구도 「준비 실패 — 건너뜀(주입 0 · 좌석 보존 · fresh 폴백 0)」 로).

**시험** — e2e `residual_focus_report_bytes_do_not_break_in_seat_reconnect`(실 cys·cysd·가짜 claude · 좌석 셸 = `bash --noediting`(잔재가 글자 그대로 남는 꼴의 맥 재현)):
첫 복원 → 작성자 SIGKILL → GUI 와 같은 인자로 `ESC[O ESC[I` 2회 → 재복원. 붉음(고침 없음) = 「좌석 내 재연결 실패(command error) → fresh 폴백 → 새 대화」 ·
초록 = 같은 좌석 · 작성자 1 · 같은 대화.

**윈 동일성** — 윈 갈래는 맥에서 시험 못 함 → 윈 실기 측정 명령(읽기 전용에 가까운 빈 셸 좌석 1개 사용)을 master 에 넘김:
빈 PowerShell 좌석 S 에 `cys send --surface S '[O[I'` → `cys send-key --surface S Escape` → 0.3초 → `cys send --surface S 'echo ok'` → `cys send-key --surface S Return` → read-screen 에 `ok`(구문 오류 없음).
⚠남는 틈: C-u 와 기동 Return 사이(≈200ms + 왕복)의 새 포커스 보고 · ⚠윈 ConPTY 가 Escape 뒤 바로 오는 바이트를 Alt+키로 묶을 가능성(200ms 쉼으로 피함 · 실기 확인 필요).
📌(범위 밖) 뷰어 1004 끄기(agent.exited 때 출력 쪽 `ESC[?1004l` 방송) = 틈까지 막는 2순위 — 박사님/master 판단.

## ③ cys send 「OK 인데 도달 0」(처분 = master#44ce6e4c A + 보강)

**원인(코드 확정 · High)** — 0.14.52(82a261d71)~ 데몬은 Return 없는 에이전트 좌석 본문을 치지 않고 잡아 둔다(`handlers.rs` `direct_agent_intent` = Held →
`hold_direct_body` 0바이트 · 응답 `held: awaiting_submit` · 창 60초). 붙는 Return = **같은 호출자 키**(`submit_caller_key`: 검증 좌석 → 자기신고 좌석 번호 →
pane 밖 = cys 의 부모 pid + 출생). VM 하네스는 send 와 send-key 를 서로 다른 ssh(다른 부모 셸)로 보내 키 불일치 → 60초 뒤 폐기(종전엔 버스에만 기록) ·
CLI(`Command::Send`)는 `held` 를 안 보고 늘 `OK`. probe123·probeTO 는 Return 자체를 안 보냄(설계대로 무도달).

**고침** — ⑴ CLI `held_send_warning`: held ∧ pane 밖이면 stderr 2줄(잡아 둠·request_id·60초·같은 셸 Return · 다른 셸이면 `--clear-first`(비우고 바로 제출 = 데몬 OwnedClear) /
`--queued`(조용할 때 제출)) · stdout `OK` · rc 0 무변경 · pane 안 = 경고 없음. ⑵ 새 `--submit` 은 만들지 않음(한 번에 제출하는 길이 이미 둘 · 시험이 두 옵션 실재를 clap 정의로 검사).
⑶ 데몬 `dispose_held_bodies` 가 만료·교체·에이전트 바뀜 폐기도 `submit-held-undelivered.jsonl` 에 남김(글자 없이 해시·길이 · 1MB 회전 기존) + doctor `held-dropped`
「최근 24시간 버려진 입력 N건」(WARN · 마지막 시각·좌석·사유·글자 수) · 0건 OK.

**master 발신 래퍼(읽기만)** — 에이전트 좌석 = `bk_send_submit`(`--clear-first` → Held 아님 → 경고 0) · `bk_send` 는 stderr 를 rc≠0 일 때만 원장 `send_err` 로 ·
성공 stderr 는 버림 → 무수정 동작.

**VM 하네스 처방** — 고칠 것은 스크립트가 아니라 호출 꼴: `~/axdev/workers/cysr-1116-release-1122/vm/harness/vmssh.exp` 는 ssh 1회 1명령 래퍼 →
한 vmssh 호출 안에 `cys send --surface N '글'; cys send-key --surface N Return` 또는 `cys send --clear-first`/`--queued` 1회. 기록할 곳 = 그 폴더 `RUNBOOK.md`
(남의 좌석 폴더라 이 갈래는 손대지 않음).

**시험** — e2e `held_send_outside_a_pane_warns_and_same_shell_return_still_submits`(실 cys·cysd·가짜 claude got.log): 한 셸 send→send-key = 제출 ·
stdout 첫 줄 OK · 경고 stderr 만 / 다른 셸 = 미도달 + 경고. bin 단위 `held_send_warning_only_outside_a_pane_and_names_real_options` ·
`held_dropped_counts_recent_evidence_lines_only` · cysd `the_return_binds_inside_the_window_and_after_60001_ms_the_body_expires_untyped` 에 증거 파일 단언.

**해소 판정 갱신 대비** — 다른 셸 send 뒤 경고 보임(e2e ⑵) ∧ 같은 셸 send→Return 제출 유지(e2e ⑴) ∧ 래퍼 무수정 동작(판독 + e2e 래퍼 꼴). VM 실기 1회는 master 몫.

## ④ master 좌석 RC 기본 켜짐(master#06f081e8)

**사실** — 좌석 기동 설정은 한 지점 `apply_seat_settings_arg`(← `boot_agent_on_surface` = launch-agent·GUI·node-recover·in-seat restore·fresh restore·phoenix
`cys restore --auto`·갱신 뒤 사이드카 restore 공통)에서 `--settings ~/.cys/seat-settings/<역할>.json` 으로 실린다. 종전 master = 빈 객체 → `--settings` 없음 →
사용자 설정(윈 설치기 = `remoteControlAtStartup=false`)이 이겨 매번 손으로 켬.

**우선순위 근거(공식 문서 · https://code.claude.com/docs/en/settings)** — 「Settings precedence, highest first: managed settings, command line, project local,
shared project, user. A key set at a higher level overrides the same key set lower down.」 · `--settings` 는 「A key you set there overrides the same key in your project
and user settings files」. remote-control 문서: `remoteControlAtStartup` true 는 user·managed 에서 켬 · project/local 의 true 는 무시(false 만 존중).
⚠`--settings`(command line) 의 true 를 따로 적은 문장은 없다 — 일반 규칙(상위 출처 스칼라가 이김)으로 판단 · 실측 1회(아래)가 확정.

**고침** — `claude_seat_settings(.., rc_autostart)`: RC 허용(`rc_allowed_for` = 부서 아님 ∧ 허용 목록) ∧ 역할 `master` ∧ 노브 켬 → `remoteControlAtStartup:true`.
cso·worker·부서 데몬 좌석 = 끄기 두 키 그대로 · 허용 목록의 다른 역할(relay) = 켜지 않음 · 허용 목록에서 master 를 빼면 꺼짐(노브보다 먼저).
노브 = `~/.cys/policy.json` `rc_master_autostart`(기본 켬 · `false` 일 때만 끔 · BOM 허용) — `docs/GUIDE-policy-json-KR.md` 표 1행.
기동 뒤 데몬 감시(`cysd/rc_guard.rs`)는 같은 술어(`rc_allowed_for`)라 master 를 끄지 않음.

**설치기 false 쓰기 판정(이 판 무수정)** — 위치 = jarvis-habitat `install-master/bootstrap.ps1` 503~516행(커밋 38e4ff5 · T-W10).
판정 = **빼지 않아도 된다**(master 좌석은 `--settings` 가 이김) · 남기는 이득 = cysr 밖에서 띄운 claude·`--settings` 를 직접 넣은 사용자 cmd 좌석에서도 RC 꺼짐 기본.
단, agents.json claude cmd 에 사용자가 `--settings` 를 넣었으면 cysr 이 둘째를 붙이지 않아(`cmd_has_settings_flag`) 그 기계의 master 는 사용자 설정(false)을 따른다 = 알려진 한계.

**시험** — lib `rc_master_autostart_only_for_the_hq_master_seat`(master=true · cso/worker/부서=끄기 · relay=무 · 노브 끔=키 0 · 허용 목록 제외=꺼짐 · 노브 해석 7꼴)
· 기존 `d25_claude_seat_settings_table`(노브 끔 인자로 종전 표 유지).
**실측(master 몫 · 워커 좌석 RC 금지라 이 갈래는 못 켬)** — 이 가지 빌드로 master 좌석 재기동 → footer `/rc` 가 손 0 으로 켜짐 ∧
`<설정 폴더>/sessions/<master pid>.json` 에 `bridgeSessionId` ∧ `~/.cys/seat-settings/master.json` = `{"remoteControlAtStartup":true}` · 비-master 좌석 footer 에 /rc 없음.

## codex 1R(REVISE · major 6 · minor 1) 처분 — 판정문 정본 `~/.cys/pack/round/_reviews/cysr-1118-seat-r1-codex.json`(revision d97843b7b)

| # | 지적 | 처분 |
|---|---|---|
| 1 | ① 조상 claude 를 등록 증거에서 제외(cysr 밖 `claude --continue` 도구 셸에서 `cys restore`) | **수용** — 등록 훑기는 조상 제외 없음(등록은 claude 만 씀 · argv 제외와 이유가 다름) · 시험 `restore_cfg_dir_outside_name_patterns_is_scanned_and_ancestors_count` |
| 2 | ① 복원 대상 cfg 폴더(`~/accounts/work` 등 이름 꼴 밖)를 안 훑음 | **수용** — `CliWorld::with_cfg(lease_gate 의 검증 cfg)` → 등록 훑기 필수 후보 · 같은 시험(대조 = 후보 없이는 NoneConfirmed) |
| 3 | ① 빈·공백 sessionId 를 「다른 대화」로 건너뜀 | **수용** — 정규화 실패 = 키 없음과 같음(살아 있음 = `reg:nosid` 판정 불가) · 시험 `blank_session_id_is_unknown_unless_stale` |
| 4 | ① 후보 열거 실패를 빈 목록으로 숨김 | **수용** — `dir_names` = Result(없음만 빈 목록 · 목록·항목·종류 판독 실패 = Err) → Seen 없으면 `reg:dir:enum-…` 판정 불가 |
| 5 | ② 윈 Backspace·Escape 가 C-u 뒤 별도 요청 — 그 사이 사람 입력을 지울 수 있음 · 부분 진행 뒤 「주입 0」 오표기 | **부분 수용** — 문구 정확화(「이미 보낸 키 …· 기동 글 0」 · 호출부 「기동 글 0」). 한 작업 직렬화(데몬 원자 선정리)는 **보류**: 형제 경로 node-recover 의 윈 Backspace 와 같은 성질 · 창 = 수 ms(빈 셸 좌석 · 사람이 그 좌석에 막 치는 순간만) · 데몬 새 RPC = 1.1.17 마감 안 회귀 면 큼 → 📌 |
| 6 | ④ 본부·부서 master 가 `seat-settings/master.json` 한 파일 공유(켬↔끄기 경합 · 부서 좌석이 RC 켬을 집을 수 있음) | **수용** — 경로 = `<역할>-<내용 sha256 앞 8자>.json`(`seat_settings_stem`) · 내용 다르면 파일 다름 · 시험(본부≠부서 · 같은 내용 = 같은 줄기) |
| 7 | ④ BOM 이 새 노브에만 — 허용 목록 파서는 BOM 실패 → 기본 `["master"]` 로 되돌아가 master 제외 정책을 넘어 켬 | **수용** — `rc_allowed_roles_from` 도 BOM 허용 · 시험(BOM + 빈 목록 = 빈 목록) |
| 8(minor) | ③ doctor 가 판독 실패·깨진 줄을 0건 OK 로 | **수용** — 없음만 기록 없음 · 못 읽은 파일·깨진 줄 = WARN(0건 확정 안 함) · 시험 2꼴 추가 |
| missing | sessionId 없는 낡은 등록이 pid 재사용으로 영구 93 | **수용** — 출생 불일치면 건너뜀(3 의 시험에 포함) |
| missing | pane 판정이 env 존재만 봄 | **수용** — 유효 좌석 번호(`parse_surface_ref`)일 때만 pane 안 |
| missing | `rc_master_autostart:false` = 강제 끄기 아님 | **수용(문서)** — 정책 안내에 「끔 = 켜는 값을 싣지 않을 뿐 · 사용자 설정을 따름」 |
| missing | `--continue` 실기 · 윈 ConPTY Escape · RC 실측 · 포커스 보고 꼬리 틈 | **남음** — 실기 측정은 master 몫(위 ①②④ 절) · 꼬리 틈 = 📌 뷰어 1004 끄기 |
