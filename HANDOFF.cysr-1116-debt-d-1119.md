# HANDOFF — TICKET=cysr-1116-debt-d-1119 (worker-1116debt-d · surface:2265 · 11-19 23:1x ~ 11-20 00:5x)

- 브리프 `master/briefs/1116-full/debt-d.md`([master#fb4dbbf0]) · 추가 1 [master#2a8340b0] · 추가 2 [master#df5b0a33] → 정정 [master#1a7e7b90](`debt-d-add2-correction.md`) ·
  추가 3 [master#ce9b60a5] · S4-4 ③ 답 [master#75867925] · 부하 공지 [master#e6c36de9](JOBS=4 · threads=4) · 순환 준비 [master#4dee4ecf] — 전부 원장 대조 성립.
- 작업트리 2개(★둘 다): cys `~/axdev/.wt/cys-1116-debt-d` 가지 `feat/1116-debt-d` ← dea2e1853 · 설치기 `~/axdev/.wt/habitat-1116-debt-d` 가지
  `feat/1116-debt-d-installer` ← jarvis-habitat `r13/scrub-v3-port` 0c58fff(설치기 정본 = jarvis-habitat install-master · jarvis-install 은 공개 사본).
- push·태그·CI·발행 0. 이 기기 데몬·좌석 무접촉(시험 = 격리 HOME · 대역).
- target = `../cys-1116-integ/target/debug` APFS 복제. ui/node_modules = `../cys-1116-integ/ui/node_modules` 복제(커밋 안 함 · .gitignore).

## 1. 항목 표(항목 · 판정 · 커밋 · 시험)

| 항목 | 판정 | 커밋 | 시험(전 → 후) |
|---|---|---|---|
| 추가1 같은 판 재실행 rotate | 성립 → 고침: rotate_plan/Get-RotatePlan 에 데몬 build_id(identify) = 프로그램 build_id(phoenix-identity) 대조 → `skip:same-build`(스케줄은 데몬이 틱마다 다시 읽음 · schedule.rs HotReload). W6 되돌림(1.1.16→1.1.14)은 build 가 달라 run:same 유지 = **rotate 가 실제로 필요**(옛 데몬 교체) | habitat fdef84a | v0330-emu-run 25 → 31 ok · 뮤턴트 2(윈·맥) 붉음 · d5-x5-f13 214 ok |
| 추가3 [5/10] 출처 문구 | 성립(윈 `원 = oogisoogi/cys-ro v…` 박은 글자 · 맥은 출처 없음) → 받은 주소에서(Get-CysSourceLabel · cys_source_label) | habitat fdef84a | 새 debt-d-1116-source-label 5 ok(기준선 0c58fff 5 FAIL) |
| 추가2 ① RunLevel 보존 | 성립: `cys daemon install`(rotate 가 매번 부름)이 작업 XML 을 LeastPrivilege 로 /F 덮음 → 기존 HighestAvailable 보존 · 같은 데몬이면 재등록 0 | fa789ffde | cys debt_d_daemon_install 1 |
| 추가2 ② 무결성 = 작업 RunLevel | 성립: 윈 rotate 의 새 데몬 = `identify` 자동 기동 = 이 CLI 토큰으로 형제 직접 스폰 → 기본 소켓은 작업 스케줄러 cysd 작업을 먼저(schtasks /Run) · 데몬 identify `token_elevated` · doctor 윈 행 `daemon-integrity` 갈림 Warn | fa789ffde | cys debt_d_ 2 · 윈 교차 타입체크 오류 0 |
| 추가2 ③ J-UPD-03 | 성립: 갱신 러너 작업 LeastPrivilege 고정 → cysd 작업 Highest ∧ 등록자 상승이면 러너도 Highest(win_task::runner_run_level · install_at) + 설치기 끝맺음 「관리자 창에서 같은 한 줄」(U5 블록·호출 줄 무접촉 = cys 계약 사본 유지) | fa789ffde · habitat fdef84a | lib win_task 15(새 1 · 소스 핀 install_at) · debt-d-1116-admin-mode-jupd03 4 ok |
| V7 | 성립 → U08 꼴(lstat · 판독 불가 = 정지) 3곳 | e132ea232 | V7SiblingPauseReaders 3: 기준선 3 FAIL → 3 OK · test_wakeup_liveness 23 · formation 90/90 · radio 297/0 |
| V10 칩 검사 | 성립 → tarball 서명 전 check_macho_arch(필수 런타임 4) + **실측 발견**: bsdtar 가 확장 속성을 PAX 'x' 로 넣어 검사기 「평이한 꼴」 밖(rc 2) → `--format ustar --no-xattrs --no-mac-metadata --no-acls --no-fflags` | fd2c7873c | 새 2: 기준선 2 FAIL → tarball 7 OK · 정렬 3 OK · macho 62 OK |
| V10 LSMinimumSystemVersion | 바꾸지 않음 — 검사기 머리 「RULINGS BQ1(e) = 오너 결정」(tauri 기본 10.13 · 진입점 minos 11.0) | — | 📌 |
| S3-1 | 성립(화면이 request_id 버림) → 번호 짝짓기 · 먼저 온 사건 보관 · 번호 없는 사건만 좌석·5초 | ca39f41b8 | slice3 65 → 67 · 뮤턴트 2 붉음 |
| S3-2 | 성립 → canonicalize 슬러그 둘째 후보(open_bound 그대로) | 2a700cad4 | debt_d_s32 2 — **결과 대기**(§3) · codex 재검토 대상(조각 3 HANDOFF) |
| S4-4 지문 계약 | 성립(데몬 지문 0) → ①②④ + ③ = A(지문 실은 요청만 대조) + 작업 화면 Allow 지문(master#75867925) · CLI `--screen-fingerprint` 선택 | e143ac859 | debt_d_s44 2(데몬) · debt_d_s44_feed_reply(cys) · feedwiring 16/16 — 데몬 결과 **대기** |
| B5 | 성립(응답 버림) → submitted:false = 즉시 not_cleared · DRAIN 은 데몬이 그 칸을 안 냄(Held 길) = 고칠 것 없음(쓰기 전 거부는 이미 Err) | e143ac859 | debt_d_b5 — **대기** |
| B6 | 성립 → vendor `tool-permission-tail`(scope prompt_tail) + 디스크 옛 vendor 값 메모리 이관 | e143ac859 | debt_d_b6(vendor·옛 디스크 두 꼴 · 인용 0 · 실제 창 1) — **대기** |
| B7 | 성립 둘 다 → 각성 Return 재판정 + InjectRefusing 생산자 핀 | e143ac859 | debt_d_b7 · h7 — **대기** |
| B4(backlog:206 #1) | 이미 고쳐짐: agents.json file-write-permission · plan-approval(scope prompt_tail · block_only) — 원작자 환류만 남음 | — | — |
| CI 📌 load_topology · phoenix:2412 | 성립 → 함수 삭제(운영 호출 0 · 메모 「운영 코드 #[cfg(test)] 금지」 때문에 cfg 대신 삭제) + 시험 6곳 load_saved_topology(..).0 · 주석 2곳 정정 | e143ac859 | topology 묶음 — **대기** |
| V6 | 성립(데몬은 먼저 멈춤 확인 · pack-update 잠금은 안 봄) → 잠금 만들지 않고 try_lock_shared | cb6544066 | v6_quiescent_gate — **대기** · codex 대상 |
| V9 | 성립 → 쓰는 이 표식 잠금(.pack-journal.d/.writer.lock) · 본부만 | cb6544066 | j1116_v9 + 기존 j1116 묶음 — **대기** · codex 대상 |
| V2-1 | 성립 → 의도 줄(link-restore-pending:) | cb6544066 | j1116_v21 — **대기** |
| V2-2 nofollow | **안 함**(남음) — 핸들 하나 읽기(O_NOFOLLOW) 고침안 = 조사 A §V2-2 | — | 📌 |
| V2-3 부트 설치 잠금 안 설정 시드 | **안 함**(남음) — 소스 핀 2곳(main.rs:5446·8122) 함께 고쳐야 함 | — | 📌 |
| V2-4 비 UTF-8 링크 | 고칠 것 없음(안전한 실패) · 시험 0 = 남음 | — | 📌 |
| V2-5 | 성립 → 죽은 pid tmp 치움 | cb6544066 | j1116_v25 — **대기** |
| V4 | 성립 → 본부 0건 ∧ **부서 ≥1건** 일치일 때만 안 옮김(양성 증거 · 기존 시험이 본부 자신의 0건 일치 저널 꼴) | cb6544066 | j1116_v4 + 기존 legacy 시험 — **대기** |
| V5 F3 | 고침(좁히기만 되돌림) | cb6544066 | F3 3줄 — **대기** |
| V5 F2(나) · minor ② | 안 고침 — 서로 맞바꿈(②를 고치면 F2(가)가 다시 열림 · 둘 다 바이트 손실 0) | — | 기록 |
| V5 minor ① | 안 고침 — 부서 기동이 공용 잠금을 보게 하면 본부 기동(공용 잠금을 설치 내내 쥠)과 동시 부팅 시 부서가 설치를 건너뜀(회귀) | — | 기록 |
| B1 census → proc-macro2 | **안 함**(남음) — 토크나이저 교체만이 아니라 항목 경계 규칙 재작성 · 자체 codex 라운드 필요 · 결함 = 계측 도구 거짓 초록만(제품 무관) | — | 📌 |
| B2 열 0 cfg(test) 블록 끝 | **안 함**(남음) — 고침안 = lib.rs:7089-7092 를 lexed.block_end_line(h) + 7062 에 code_start 조건(조사 D §B2) | — | 다음 좌석 |
| 미등재 팩 시험 | 판단 자료만(§2) — 등재 = ci-branch·release·pack-release 3레인 5루프 + lane-parity-rehearsal UNREGISTERED_OK 지우기(debt-u 좌석 ci-branch 정렬과 충돌 지점) | — | §2 |
| poison × Login expired | **이 저장소에 그 규칙 없음**: `git grep -i "login expired"` 0 · poison = phoenix Phase 11 재시도 소진(javis_phoenix.py 3714 「· <역할>: 기동 실패」 · 3893) · jsonl 은 존재만 봄(cys.rs resolve_resume_suffix) · 화면 health 룰은 300초 창(state.rs 9794) | — | 원인 = 윈 실기 그 회차에서 resume 기동이 실제로 실패한 까닭(로그인 만료 중 claude 가 resume 을 거부?) — 윈 phoenix 130줄에서 「기동 실패」 줄 원문 확인 필요(📌) |
| J-UPD-03 정적 분석 | 막는 곳 = Test-CysTxnPathPrivate 의 `Get-Acl` 예외 → catch → unsafe(소유자 BA 는 규칙상 허용인데 **읽지 못해서**) · Write-CysTxnOdd 에 Set-NextStepRerun 없음 = 할 일 0 | 위 ③ | — |

## 2. 미등재 23개 격리 실행(env -i · HOME 스크래치 · /usr/bin/python3 · 120초 상한)

rc 0(19): cli_probe 0s · completion_guard_notice 1s · contracts_ct 1s · dept_list_unregistered 1s · dept_ticket_deficit_zero 31s · dept_ticket_request 36s ·
distill_fx 4s · hud_bridge_master_idle 1s · memory_desc_drift 12s · mission_boot_command_filter 3s · mission_harness_filter 32s · orchestra_ticket_snapshot 1s ·
orchestra_todo_path 0s · org_audit 5s · pack_syntax_warnings 2s · preflight_nlm_pin 0s · vibecheck 3s · viberoute 2s.
붉음·멈춤(5): agora_known_authentic rc 1(설계상 제작 맥 전용 · zip 필요) · dept_creds_seed **rc 142 = 120초 상한 걸림(멈춤)** · preflight_phase1_checks·verify_gate rc 2
(격리 env JAVIS_ROOT·CYS_PROBE_RUNS 요구 = 하네스 전제) · seat_revival rc 1(aliased_harness_root — 스크래치 TMPDIR 경로 별칭).
권고: rc 0 인 19개 = 등재 후보(우분투에서 한 번 재확인 뒤) · dept_creds_seed 는 멈춤 원인부터. 원자료 = scratchpad `z23/`.

## 3. 진행 중 명령(매듭 시점) · 결과 대기

- 백그라운드 `t-all1.txt`(scratchpad) — lib(j1116 · quiescent · v6_ · win_task) · cysd(debt_d_ · d24_ · h7_ · b16fix_approval_scan · approval_patterns_union ·
  watch_wake · feed_push_rejects_reserved · topology · b16fix2_) · cys(debt_d_ · u16_cycle · b360_r2c · feed_reply) · cys-app(debt_d_ · feed_reply · confirm_reply · slug).
  **커밋 e143ac859·cb6544066·2a700cad4 의 시험은 이 결과로만 판정한다**(앞선 묶음 1회는 시험 모듈 상수 경로 누락 컴파일 오류 → 고친 뒤 이 묶음).
- 다시 돌리는 법: `cd ~/axdev/.wt/cys-1116-debt-d; CARGO_BUILD_JOBS=4 cargo test --bin cysd debt_d_ -- --test-threads=4`(이하 같은 꼴).

### 3-1. t-all1 결과(01:0x 끝 · exit 0 · 원문 scratchpad `t-all1.txt`) — 붉음 0 · 판정 불가 1

| 묶음 | 통과 | 실패 | 무시 |
|---|---|---|---|
| lib(j1116 · quiescent · v6_ · win_task) | 40 | 0 | 1 |
| cysd debt_d_ | 4 | 0 | 0 |
| cysd d24_ | 4 | 0 | 0 |
| cysd h7_ | 1 | 0 | 0 |
| cysd b16fix_approval_scan | 1 | 0 | 0 |
| cysd approval_patterns_union | 2 | 0 | 0 |
| cysd watch_wake | 12 | 0 | 0 |
| cysd feed_push_rejects_reserved | 1 | 0 | 0 |
| cysd topology | 16 | 0 | 0 |
| cysd b16fix2_ | 3 | 0 | 0 |
| cys debt_d_ | 5 | 0 | 0 |
| cys u16_cycle | 1 | 0 | 0 |
| cys b360_r2c | 19 | 0 | 1 |
| cys feed_reply | 3 | 0 | 0 |
| cys-app(debt_d_ · feed_reply · confirm_reply · slug) | **판정 불가** — 빌드 스크립트 실패 `resource path binaries/cysd-aarch64-apple-darwin doesn't exist`(작업트리에 tauri 리소스 준비물 없음 · 코드 무관) → S3-2 debt_d_s32 2건·작업 화면 feed_reply 인자는 미실행 | — | — |

- 붉은 이름 0. 이 묶음은 필터 묶음이다(전량 아님) — 전량·뮤턴트·codex 는 §4.

## 4. 남은 일(후임)

1. §3 결과 판독 → 붉으면 고침(내 새 시험 · 소스 핀 · agents.json 이름 바뀜이 다른 핀을 깨는지).
2. 뮤턴트: J1116-V9-NO-MARKER · J1116-V21-NO-PENDING · J1116-V25-KEEP · J1116-V4-OFF · J1116-F3-OFF(환경값 분기 · 1빌드) + S4-4(actuate 대조 줄 제거) · B5 · B7.
3. B2 고침 · V2-2 · V2-3 · V2-4 시험 · (B1 은 📌 판단).
4. 전체: cargo bin cys(전량 · j3 스택 메모) · bin cysd · lib · cys-app · tests/*.rs · bun 전량 · tsc · 팩 = ci-branch 팩 단계 그대로(`.wt/cys-1116-integ-cifix-evidence/step-mac.sh` 를
   이 가지 yml 에서 다시 떼어) · secret-scan · 윈 교차 타입체크.
5. codex 1R(필수): S4-4(결정 A + 작업 화면 지문 포함) · V6 · V9 · 추가2(RunLevel 보존·작업 경유 기동·러너 Highest) — 읽기 전용 사본에서.
6. 설치기 가지: 맥 쪽 동형 시험은 함수 단위(흉내 [8/10] 실행은 윈만) · 설치기 전체 시험 묶음은 안 돌림.

## 5. 함정(이번에 밟은 것)

- zsh 는 `$opts` 를 단어로 안 나눈다 → 옵션 여러 개 시험은 bash -c 로(메모 그대로 재발).
- 설치기 흉내 시험(v0330-emu-run 등)의 정리 줄이 `pkill -f` → PATH 앞 무동작 pkill 대역(scratchpad shim)으로 돌림.
- cys 계약 시험 u5-win-lock.ps1 [구조] 가 설치기 `$rc = Enter-CysTxn; if ($rc -ne 0) { exit $rc }` 줄을 글자로 고정 → 설치기 U5 블록·호출 줄은 건드리지 말 것.
- bsdtar 확장 속성 PAX 머리(위 V10).
- 메모 「운영 코드 #[cfg(test)] 금지」 → load_topology 는 cfg 대신 삭제.

## 6. 📌 덧붙임(실행 안 함)

1. LSMinimumSystemVersion 10.13 → 11.0(진입점 minos) 여부 = 오너 결정(x64 판 minos 실측 먼저).
2. 맥 sudo 실행 설치기·CLI → root 데몬 가능(launchd kickstart gui/0 실패 → 형제 기동) — 정정 지시가 권한 낮추기를 철회해 넣지 않음(넣었다가 뺌).
3. 부서 데몬(cys-dept 파이썬)이 관리자 설치기 아래서 뜨면 같은 High 상속 — 작업 경유 아님(부서는 작업이 없음).
4. 작업 스케줄러 Highest + 다른 cysd 경로(판 이동) = daemon install 이 Highest 로 재등록 시도 → 일반 창이면 실패(rc 22) — 조용히 Limited 로 되돌리는 것보다 낫다고 판단.
5. B6: claude 도구 허락 창이 늘 가로줄 아래인지 실화면 실측(가로줄 없고 커서가 번호 행도 아니면 감지 0).
6. poison 원인 확인 = 윈 phoenix 로그의 「기동 실패」 줄 원문.

## 7. 후임 좌석 델타(worker-1116debt-d2 · surface:2271 · 11-20 01:07 ~ · 브리프 debt-d2.md [master#668a596a])

### 7-1. 커밋(이 좌석 · 모두 feat/1116-debt-d · push 0)

| 커밋 | 무엇 | 시험 · 뮤턴트 |
|---|---|---|
| 60bc82c6a | B2: census 열 0 `#[cfg(test)]` 블록 끝 = 중괄호 짝(lexed.block_end_line) · 머리 = 코드 시작 줄만 · 짝이 열 0 `}` 아니면 실패 · schtasks 계수 4→7(fa789ffde 3곳) | 단언 4(가~라) · B2CS·B2END 붉음 |
| 31e4d290c | V2-2 write_journal = O_NOFOLLOW·O_NONBLOCK 한 핸들 읽기 · V2-3 부트 config 시드 = 팩 적용 잠금 밖(ConfigSeed::Defer · 시드 지점 간 설치만) · V2-4 시험 · cysd main.rs 핀 갱신 | j1116_v22·v23·v24 · J1116-V22-FOLLOW·J1116-V23-SEED-IN-LOCK 붉음 |
| 9aaafdf33 | B7 동작 시험(실 tick_probes · 실 PTY master · 승인 대기 = Return 0 · 대조군 Return 1) | 뮤턴트 B7 = 이 시험만 붉음(옛 글자 핀은 못 잡음) |
| d94094a9c | V6 codex 1R: 쓰는 이 = 공용 잠금 뒤 초기화 센티널 확인(with_lane_apply_lock_gated) · 레인 목록 판독 오류 = Err | j1116_v6 2 · J1116-V6-NO-SENTINEL·DIR-ERR-OPEN 붉음 |
| 667506fac | S4-4 codex 1R: Daemon.approval_fps(감지 때 지문) · 목록 = 그 값 · check_approvals 재결박(approval_rebind_stale) · 지문 실은 키 = SubmitAfterGap.refuse(쓰기 직전 재계산) · ActuationClaim | s44 새 3 + 기존 1 갱신 · S44-NO-REBIND·NO-WRITER-RECHECK·NO-CLAIM 붉음 |
| 0461f82aa | 추가2 codex 1R: query_task_xml(질의 실패 ≠ 작업 없음 · 작업 파일 NotFound 만 없음) · run_level_of(요소 판독 · 모르는 값 = 덮지 않음) · runner_run_level → Result(관리자 모드 기기 + 일반 창 = 등록 거부 안내) · B5 시험 #[cfg(unix)](윈 타입체크 오류 6→0) | win_task 새 1 · 표 갱신 |
| 4b5cb2133 | d16 글자 핀 `Ok(_)`→`Ok(r)`(e143ac859 B5 가 깸 · 전량에서만 보임) + 거부 return < 송신 마커 단언 | — |
| ba20e3aae | 내 리팩터가 깬 핀 2: install_entries(→ install_from_iter_with) · schtasks 7→6 | — |

원작자 파일 변경 줄(데몬 변경 허용 갈래): state.rs(Daemon.approval_fps 필드·초기화 · push_feed_notification 지문 결박 블록) · handlers.rs(ActuationClaim 구조체 · feed.reply 점유 블록 · feed.list 지문 출처 · 시험 4) · governance.rs(check_approvals 코얼레싱 3줄 · approval_rebind_stale · actuate_screen_approval_checked 쓰기 요청 · 시험 0) · main.rs(시험 핀 1) · watch_wake.rs(시험 1).

### 7-2. codex
- 1R(e81abb15c 기준 · S4-4·V6·V9·추가2) = **REVISE** blocking 6 · major 2 · minor 1 · V9 = ACCEPT. 원문 = 이 좌석 scratchpad `codex-r1-out.txt`(사본 폴더 `codex-r1/` · 개인정보 관문 위해 이메일·전화 꼴만 자리표시로 바꿈).
- 처분: S4-4 ①②③ · V6 blocking·major · 추가2 질의 실패·러너 = 고침(위 3커밋). **안 고침 2**: ⓐ 추가2 「작업 기동 실패 → 형제 직접 기동(Medium)」 = 정정 지시 ② 가 「갈리면 doctor 경고」 로 예정한 갈림 · 거부로 바꾸면 작업이 망가진 기기에서 데몬이 안 뜸(📌 오너) ⓑ S4-4 minor(정규화가 명령 안 공백·│·❯ 차이를 지움) = 기록.
- 2R = **codex 한도로 판정 없이 끊김**(「try again at 6:29 AM」) → master 공지 [master#822421fb] 대로 **codex 2R = master 대기열(debt-d 2R)**. 사본 폴더 `codex-r2/` · 질문지 `codex-r2-prompt.md` 그대로 다시 쓰면 된다.
- 내 자체 재검(2R 대신 · 판정 아님): writer 의 refuse 탐침이 좌석 파서 잠금을 잡는 것 = 기존 승인 탐침(approval_screen_now)과 같은 꼴 · ActuationClaim 은 RAII 라 조기 return 전부 풀림 · 재결박은 다시 그리는 도중 화면에서 항목을 한 번 더 세울 수 있음(각성 줄은 같은 문구 300초 억제).

### 7-3. 게이트(격리 env = env -i · HOME 빈 폴더 · PATH 에 실 cys 없음 · /tmp/d2ci · ci-branch.yml 단계 run 블록 그대로 떼어 · 원자료 /tmp/d2ci/logs)

| 단계(ci-branch idx) | 결과 | 판정 |
|---|---|---|
| cargo `--bin cys` threads=1 (22) | 1차 800 ok · 1 FAIL(d16 핀 = e143ac859 가 깸) → 4b5cb2133 뒤 2차 **801 ok · 0 FAIL** · 2 ign | 초록 |
| cargo `--bin cysd` threads=1 (25) | **3341 ok · 0 FAIL** · 17 ign · 1 filtered(hwmon) | 초록 |
| cargo `--lib` threads=1 (35) | 1차 1278 ok · 2 FAIL(내 리팩터가 깬 핀 2) → ba20e3aae 뒤 2차 **1280 ok · 0 FAIL** · 3 ign | 초록 |
| drainhold e2e (36) · cys-app --bins (37) · 윈 교차 타입체크 (38) | 4 ok · **350 ok** · 오류 0(경고 123) | 초록 |
| PTY·C8·가짜 cargo 대조·IOReport (24·26~30·33·34) | 전부 rc 0 | 초록 |
| UI bun (55) · tsc 7.0.2 (56) | **3749 pass · 0 fail**(3837 · 88 skip) · tsc 오류 0(버전 줄 실측) | 초록 |
| phoenix-host-gate (44) · 팩 0·1·4·7·8·10~21·31·32 | 전부 rc 0 | 초록 |
| boot-health 전량 (40) | 167 pass · **2 FAIL = H-CLT-1·2** · 1 skip | 환경성: 훅 프리루드 2순위가 이 기계 실설치 `/Applications/cys.app/.../python3` 를 집음(CI 러너엔 앱 없음) · 훅·검체 기준점 diff 0 · 📌 시험이 실 /Applications 를 읽는 격리 구멍 |
| 팩 스위트 (9 · 계속 돌기 꼴 = evidence step-mack.sh 글자 일치) · 우분투 루프 (51 · 계속 돌기 = step-ubuntuk.sh 글자 일치) | 계속 돌기 900: LANE-FAIL 5 · 901: 6(합 7종 + r34) — **04:34~04:49 다른 좌석 부하 주입(load 20~27 · [master#f640c115]) + 내 cargo 줄기 겹침 시간대** | 단독 재실행(04:51~04:57 · load 7~11): capgate_hook_shell · inject_context_role_seat · refl_inject_context_role_canon = **초록** · 남은 5 = **판정 대기**(아래) |

남은 5(단독 재실행에도 붉음 · 판정 대기 — 회귀로 부르지 않음):
- test_v116_auto_restore_status: PermissionError `target/debug/cysd` — **그 파일이 0바이트·644(11-20 03:14 생성 · 출처 미상 · 지우지 않음)**. cargo 단계는 deps/ 실행 파일만 만든다. 누가 만들었는지(가짜 cargo 대조 단계 28~30 의심) 먼저.
- test_hook_r34: 1초 시한 단언(RCF-3·NZ-3·DL-1b 3.2~3.5s) — 부하 7 이상에서 붉음 · 1차 단독 3회 = 초록 1 · 붉음 2. master 공지의 「새로 쓴 실행 파일 첫 exec 검사 0.3~3.6s」(feat/1116-flaky 55e7e7e99 prime_exec) 꼴 의심.
- test_resource_gate_product_cpu 9c: 「ps timeout 1.5 s」 = 시한 · 부하성 의심.
- test_role_authority: backoff.log FileNotFound(스텁 첫 실행 시한 의심) · test_owner_desk R8Codex2R app_flush 0≠1.
- 다음 좌석: load<5 에서 단독 3회 + 기준점 dea2e1853 작업트리(target 복제)에서 같은 시험 → 「사유 전문 일치 + 티켓 이전 기준」 으로 가른다. 이 가지의 cysjavis-pack 변경 = 앞 좌석 6파일(agents.json · javis_phoenix.py · V7 3파일)뿐 — 위 5 시험이 그 파일을 쓰는지부터.

- secret-scan --all: clean(2186 파일).

### 7-4. 남은 일(다음 좌석)
1. 위 「판정 대기 5」 가르기. 2. codex 2R = master 대기열(06:29 뒤) · 판정 뒤 고침. 3. B1(census proc-macro2) · 미등재 팩 시험 등재 = 앞 좌석 §4 그대로(손대지 않음).
4. 설치기 가지(habitat-1116-debt-d) 는 이 좌석 무접촉.

### 7-5. 📌 덧붙임(실행 안 함)
1. 추가2 「작업 기동 실패 → 형제 직접 기동(Medium 데몬)」 유지 vs 거부(가용성 vs 무결성) = 오너 결정.
2. boot-health H-CLT 시험이 실 `/Applications/cys.app` 을 읽음(CYS_TEST_SYSROOT 가 고정 설치 위치를 안 가림) — 시험 격리 결함 후보.
3. S4-4 정규화 minor(명령 안 공백·│·❯ 차이) — 구조적 제거로 좁힐지.
4. runner_run_level 이 관리자 모드 기기 + 질의 실패를 Err 로 = 갱신 등록이 일시 실패할 수 있음(종전 = 조용히 Limited) — 엄격 쪽을 택함.

## 8. 같은 좌석 추가 회차([master#6f7634b4] ①~④ · [master#10a4cfa7] ⑤ · 05:00~05:2x · CTX 50.9% → 매듭)

| 처분 | 결과 |
|---|---|
| ③ H-CLT 시험 격리 | **고침 e1d75b0bd**: _u15_sandbox CYS_TEST_SYSROOT(빈 뿌리) · _u15_resolve 「격리 실패」 가드 · H-CLT-2 실기 축 = 빈 뿌리 + PATH cys 가 앱 번들이면 적용 불가(우리 판 = 맥 동봉 우선 · `_lib.sh` cys_resolve_py 의 `_cys_bundle_py \|\|` 가 의도). 실 cys 없는/있는 PATH 둘 다 4/4 초록(이 기계 = 실설치 있음) · 음성 대조(빈 뿌리 제거) = H-CLT-1 「격리 실패」 붉음 |
| ① 팩 붉음 5 | **v116_auto_restore_status** = 환경성: `target/debug/cysd`·`cys` 가 0바이트·644(둘 다 03:14 · 그 시각 cargo 줄기 = IOReport 단계 33·34 · 출처 단정 못 함) → 이 worktree 에서 `cargo build --bin cysd/cys` 뒤 **3/3 초록**. **resource_gate_product_cpu** 3/3 초록(load 5~10) · **role_authority** 3/3 초록 · **owner_desk** 0·0·1 → 55e7e7e99(feat/1116-flaky prime_exec) 시험 고침을 잠깐 얹으면 owner_desk·role_authority **3/3 초록**(얹은 것 원상복구) = 그 가지 통합으로 사라질 붉음. **hook_r34** 3/3 붉음(1초 시한 단언 RCF-3·RCF-4a·NZ-3·DL-1b·WIN-2 · 3.2~4.3s · load 9~12) · 55e7e7e99 범위 밖 · 훅·시험 파일 기준점 dea2e1853 diff 0 = 이 가지 회귀 아님 · 원인 후보 = 새 스텁 첫 exec 검사(시한 안 첫 실행) → feat/1116-flaky 쪽 같은 prime_exec 처방 후보(📌) |
| ④ | 📌3 정규화 = 1.1.17 기록 · 📌4 엄격 Err 수용 — 재시도: `update/auto.rs:128` spawn_runner 실패 = `update.spawn_failed`(RC_SPAWN) 반환뿐 · 막는 표식 없음 → 다음 자동 확인이 같은 길로 다시 등록(정적 확인 · 윈 실기 미측정) |
| ② 형제 직접 기동 유지 + 보강 | **안 함(후임)** — 착수 시 CTX 60% 전에 끝낼 수 없음(윈도우 기동 경로 + 대역 시험 + 뮤턴트) |
| ⑤ 바이너리 미리 데우기(A안) | **안 함(후임)** — 같은 사유 · 설치기 가지(habitat) + cys 업데이터 두 저장소 |

### 8-1. 후임 설계 메모(이 좌석 판단 · 실행 안 함)
- **②** 자리 = `src/bin/cys.rs` 자동 기동(지금 `win_autostart_route(...) == TaskThenSibling && win_run_cysd_task()` → poll 2회 → 형제 spawn). 보강안: ⓐ `win_run_cysd_task()` 실패·8초 무응답이면 짧게 2회 재시도(각 /Run + poll 4초) ⓑ 그래도 실패 → 형제 직접 기동 + **표식 파일**(상태 폴더 `daemon-integrity-fallback` · 시각·사유) ⓒ doctor `daemon-integrity` 행이 표식을 보면 Warn 1줄(지금 행과 합침) ⓓ **다음 기회 자동 복귀** = 다음 `cys daemon rotate`·재시작(autostart) 진입 때 표식이 있고 작업이 Highest 면 데몬 정지 → 작업 경유 재기동 → 성공 시 표식 삭제. 순수 판정 함수로 떼면(입력 = 작업 존재·RunLevel·표식·토큰 상승) 맥에서 표 시험 + 뮤턴트 가능 · 실 schtasks 는 대역 실행기(함수 주입).
- **⑤** 「한 함수」 = lib 에 `prime_binaries(dir) -> Vec<(이름, Duration, rc)>`(cys·cysd·cysr 있으면 `--version` 1회 · 실패 무시 · 로그 1줄) · 부르는 자리 = 업데이터 교체 직후(src/update — 교체 성공 뒤 · 재기동 전) · 설치기 = habitat `install-master/bootstrap.sh`·`bootstrap.ps1` 의 설치 끝(같은 일을 셸로 · 또는 설치된 `cys prime-binaries` 하위 동사 1회 — 메모 「최상위 Command 인자 = j3 스택 넘침」 → 하위 동사 enum 에) · NSIS = nsis-hooks.nsh 설치 끝 `cys prime-binaries` 1회. 시험 = 대역 바이너리(호출 기록 스크립트)로 「교체 직후 1회」 단언 + 뮤턴트(호출 줄 제거).

### 8-2. codex 2R 범위(대기열 · 갱신)
1R 고침 3(d94094a9c · 667506fac · 0461f82aa) + 31e4d290c(V2-2·3) + 60bc82c6a(B2) + e1d75b0bd(H-CLT 격리) · 질문지 = scratchpad `codex-r2-prompt.md`(H-CLT 1줄 덧붙일 것) · 사본 폴더는 HEAD 로 다시 떠야 함.
