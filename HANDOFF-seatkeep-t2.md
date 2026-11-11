# HANDOFF — TICKET=cysr-seatkeep-t2 (좌석 보유 장치 seatkeep 단독 시제품 · 맥 · cysd 미연결)

- 상태 = **【확인요청 2】**(master#69b9fe37 · 2차 고침 + codex 2R 고침 + 재실측 끝) — 최종 코드 커밋 `0c3aff2d`(2b2b4d5c D1~D9 → 0c3aff2d codex 2R 5건) · push 0.
- 가지 = `feat/seatkeep-t2`(v1.1.14 `270e3e21` 위) · 커밋 2개(`0704dc03` 시제품 · 이 커밋 = codex 1R 고침 + 시험 결과) · push 0.
- 설계·브리프 = `~/axdev/master/reports/2026-11-11-cysr-holder-design/`(DESIGN.md · T0-surface-state.md · briefs-draft/T2.md · master#a3db2868 결정 5).
- codex 1R = 같은 폴더 `codex-t2-1R.prompt.md`(의뢰문) · `codex-t2-1R.verdict.json`(판정 BLOCK · 대상 `0704dc03`) · `codex-t2-1R.txt`(전 기록).

## 2차 고침(독립 검증 REVISE · master#69b9fe37)
- **D1 안 읽는 조종자**: 프레임 개수(1024 ≈ 실제 1MB · 2ms 멈춤에 쫓겨남) 기준 폐기 → ⓐ **밀린 바이트 상한 4MiB/좌석**(`OUT_QUEUE_BYTES`) — 넘는 실시간 출력은 큐에 안 넣고 꼬리에 둔 채 「밀림」 표시 → 쓰기 스레드가 큐를 반 아래로 비우면 꼬리에서 그 오프셋부터 따라잡기(256KiB 조각) · 꼬리에서 이미 밀려난 부분은 오프셋 건너뜀(= 유실로 보임) · 밀린 좌석의 EXITED 는 따라잡기 뒤 ⓑ **멈춘 시간** = 소켓 쓰기가 10초 동안 진척 0 이면 `evict write_stalled` 후 닫음(EPIPE 등은 내보냄 아님). 값 근거 = 보통 좌석 출력 초당 약 11KB(A13 noisy) → 4MiB = 수 분 분량 · 쏟는 좌석(초당 약 150MB) 약 27ms 분량 · 메모리 = 좌석당 최대 4MiB(평소 0) · tmux `control.c` 도 시간으로 판정(300초 · 답장 버퍼 64MiB). 실측: `vt.py stall_tolerance` 500ms 멈춤 **10/10 생존**(내보냄 0) · 0~250ms 각 2/2 생존 · 영영 안 읽음(`t2.py evict`) = 10.0초에 `evict write_stalled` · 밀린 동안 RSS 증가 4.1~4.8MB(`behind_mem` 5/5) · 꼬리 64MiB 에서 300ms 멈춤 뒤 구멍 0·SEQ 역행 0(`behind` 3/3).
- **D2 교체 기록 찢김**: 쓰기 전 길이를 재고 쓰기 실패면 `ftruncate` 로 되돌림 · 되돌림도 실패하면 다음 줄을 줄바꿈으로 시작 · 시험기 읽는 쪽은 해석 안 되는 줄을 건너뜀. 실측: `vt.py diskfull_ledger_boundary_errout` 주입 성립 회차 6/6(rem 0·60 각 3) 찢긴 줄 0 · A16 = 실제 WELCOME.
- **D3 설계 전제 정정**: `peer.rs` 머리 주석 · DESIGN §3-2 를 커널 동작대로 고침(토큰 = 「지금 그 pid 의 마지막 사용 프로세스」). **(pid, 출생 시각) 짝 대조 추가**: HELLO 뒤 재인증은 (pid·pidversion·출생 시각) 셋 다 같아야 · 잠금 파일 둘째 칸이 있으면 조종자 출생 시각과 같아야(`lock_owner_mismatch`) — 실측 `startpair` 3/3. 실제 pid 재사용 우회는 여전히 못 잼.
- **D4** `eprintln!` → 실패 무시 `warn!`(stderr 가 가득 찬 디스크여도 REJECT 2/2 · 패닉 0). **D5** 소켓 경로 ≥ 104바이트면 어떤 파일도 만들기 전에 rc 2(103 정상 · 104·105 잔재 0). **D6** 상태 폴더 `seatkeep` 이 링크·파일·남의 소유면 거절 · `<id>.log`·`<id>.lock` 은 O_NOFOLLOW(링크 대상 폴더 권한·파일 무변경 확인). **D9** 종료 기록을 30초(`EXIT_PERSIST_MAX`) 넘게 못 남기면 stderr 에 기록을 남기고 rc 6(31.2초 실측).
- **D8 시험 편입**: 검증 좌석 `vt.py`·`vlib.py` 를 시험대로 들여옴(결과·실행 파일 경로만 바꿈) · `t2.py vtport`(dual·torn_read·signal_spam_reap·reauth·busy·디스크 가득 2종) · 새 `behind`·`behind_mem`·`startpair`·`sockpath`·`symlink`·`persistcap` · `replay` = 고정 3초 대신 EXITED 140개 받은 뒤 떠남 · 검증 좌석 `busy` 판정식(거절 줄 4)은 정당 조종자 busy 1줄을 빠뜨려 동작과 무관하게 거짓(검증 좌석 d41c00eb 기록도 같음) → 동작 기준으로 판정.

## 2차 재실측(최종 코드 `0c3aff2d` · 릴리스 고정본 `bin-r2/cys-seatkeep-0c3aff2d-release` · 결과 = results/r2-all-base.out · r2-a11.out · r2-a13b.out · r2-mutant-table.tsv)
| 기준 | 결과 |
|---|---|
| A3 | 3/3(죽인 seatkeep 의 좌석만 사망 · 나머지 2개 생존) · 대조군 판별 1개 = 3개 모두 사망 |
| A8 | ⓐ perl 5/5 `exe_mismatch` · 잠금 없이 5/5 `lock_not_held` · ⓑ 같은 프로세스 둘째 5/5 `controller_alive` · 다른 프로세스 5/5 `lock_pid_mismatch` · ⓕ 죽은 pid 위조 5/5 · 요구사항 1/1 · 재인증(vt reauth) 9/9 · 출생 시각 짝(startpair) 3/3 |
| 조종자 SIGKILL 12회 | 자식 생존 12/12 · 같은 pid · 신호 0 · 누락 0 · 구멍 0 |
| A16 | accept 13 = disconnect 13 = WELCOME 13 · 디스크 가득 짧은 쓰기 주입 성립 회차 찢김 0 · 수락 수 = 실제 |
| 유실 보고 | 3/3 일치 |
| A10 | 조종자 없음 10/10 · 확인 3/3 · 잔여 프로세스 0 |
| A11 | 6/6(대조군 6/6 사망 = 유효) · 뮤턴트 M17(setsid 끔) = 0/2 생존(잡음) |
| A13 | 좌석당 40좌석 RSS 300.6 / 305.8MB(≤320) · 유휴 CPU 0.0%(≤2%) · footprint 98.1 / 104.0MB · 스레드 280 · fd 480 · 소켓 160 · 판별 1개 11.2 / 15.5MB · 첫 일괄의 A13 은 noisy 좌석당 5 에서 기동 확정 미확인으로 1회 멈춤(뮤턴트 빌드와 겹친 때 · 재현 안 됨 · 원인 미상) |
| A14① | 5/5(prepare 중 SIGKILL · 등록부 밖 작성자 0) |
| 2차 고침 시험 | evict 1/1(10.0초 write_stalled) · stdin_block 3/3 · slowhello 3/3 · sameid 3/3 · exitreuse 3/3 · exitorder 3/3 · exitfail 3/3 · commitfail 3/3 · replay 2/2 · behind 3/3 · behind_mem 3/3 · vt_dual · vt_torn_read · vt_signal_spam_reap · vt_busy · 디스크 가득 2종 · sockpath 3/3 · symlink · persistcap · ctlflood 3/3 — 전부 통과 |

### 뮤턴트 재실행(핵심 방어 줄 1곳씩 · 기존 시험 `t2.py all` 이 잡는가 · 병렬 2)
| 뮤턴트 | 결과 | 잡은 시험 |
|---|---|---|
| M01 잠금 pid 비교 생략 | 잡음 | a8b·a8f·vt_reauth |
| M02 잠금 안 잡혀도 통과 | 잡음 | a8a·vt_reauth |
| M03 실행 파일 불일치 통과 | 잡음 | a8a |
| M04 수락 직전 조종자 확인 끔 | 잡음 | vt_dual |
| M05 원자 기록 → 직접 덮어쓰기 | 잡음 | vt_torn_read |
| M06 종료 기록 게이트 끔 | 잡음 | exitfail·persistcap |
| M07 밀림 표시 없이 버림 | 잡음 | behind(구멍) |
| M08 id 잠금 실패 무시 | 잡음 | sameid |
| M09 회수 표시 300ms 늦춤 | **놓침**(이번 일괄) | 첫 일괄에서는 vt_signal_spam_reap 이 잡음 · 단독 재실행 = 새 M09 1/3 · 검증 좌석의 d41c00eb M09 도 지금 0/3 — 부하(평균 6~7)에서 손자에 닿는 SIGWINCH 가 2~65번뿐이라 **시험 감도가 부하에 따라 흔들림**(코드 회귀 아님 · 결정적 시험 필요) |
| M10 HELLO 뒤 재인증 생략 | 잡음 | vt_reauth |
| M11 동시 핸드셰이크 상한 끔 | 잡음 | vt_busy |
| M12 수락 기록 실패 무시 | 잡음 | 디스크 가득 2종 |
| M13 유실 식 틀림 | 잡음 | loss |
| M14 미소비 종료 기록 확인 끔 | 잡음 | exitreuse(+ a14 1회차 흔들림: 죽인 시점이 준비 기록 앞) |
| M15 확정 실패해도 계속 | 잡음 | commitfail |
| M16 종료 알림을 읽기 끝 전에 | **놓침** | 맥은 세션 리더 종료 때 단말이 회수되어 등가 뮤턴트에 가까움(검증 보고와 같음) |
| M17 setsid 끔 | 잡음 | A11(0/2 생존 · `t2.py all` 에는 A11 없음) |
| M18 짧은 쓰기 되돌림 끔 | 잡음 | 디스크 가득 errout |
| M19 밀린 바이트 상한 끔 | 잡음 | behind_mem |
| M20 출생 시각 짝 끔 | 잡음 | startpair |
| M21 소켓 경로 검사 끔 | 잡음 | sockpath |
| M22 링크 폴더 허용 | 잡음 | symlink |
| M23 종료 기록 시도 상한 끔 | 잡음 | persistcap |
| M24 제어 큐 상한 끔 | 잡음 | ctlflood |
- 합계: 검증 좌석 16곳(M01~M17 중 M16 포함 · 번호 16개) 중 `t2.py all` 이 잡음 13 · A11 이 잡음 1(M17) · 놓침 2(M09 시험 감도 · M16 맥 등가). 2차 추가 7곳(M18~M24) 전부 잡음.
- 시험기 결함 고친 것(뮤턴트 첫 일괄에서 드러남): behind 가 부하에서 멈춤 자체를 못 하던 것 · sockpath 고정 경로라 회차끼리 섞이던 것 · 한 시험의 대기 시간 초과 예외가 뒤 시험을 막던 것.

## 만든 것
- 새 실행 파일 `cys-seatkeep`(`src/bin/cys-seatkeep/` 4파일 · `Cargo.toml` [[bin]] 1항). **cysd·cys 기존 파일 수정 0.**
  - `main.rs`: setsid(실패 = 시작 안 함) · **id 잠금(`<id>.lock` flock — 같은 id 두 번째는 어떤 파일도 건드리기 전에 rc 4)** · 미소비 `<id>.exit` 가 있으면 rc 4 · 자기 신원(부팅 id·시작 시각) 못 읽으면 rc 3 · 등록부 준비 → 소켓(0600) → 자식 기동(portable-pty · setsid+TIOCSCTTY) → 확정(3회 재시도 · 끝내 실패 = 자식 SIGHUP→SIGKILL 정리 후 rc 3) · 좌석별 읽기(꼬리 기본 1MiB · 상한 64MiB · 누적 오프셋) · 조종자 1명(살아 있으면 새 접속 거절) · HELLO 핵심 판 비교 · **HELLO 뒤 신원·잠금 재확인(pid·pidversion 같아야)** · 교체 기록이 먼저(실패 = `accept_aborted` 줄 + 거절) · WELCOME + 꼬리 재생(1MiB 조각 · 재생 프레임 수만큼 칸을 더 잡음) · 유실 = max(0, 꼬리 시작 − 재개 오프셋)을 accept 기록에 적음.
  - **막히지 않는 규칙**: 조종자 송신은 상태 잠금 안 `try_send` 만 · 칸(1024 + 재생 수)이 차면 그 조종자 `evict` · 소켓 쓰기 기한 10초 넘으면 쓰기 스레드가 연결을 닫음 → 자식 출력은 계속 꼬리에 쌓임. PTY 입력은 **좌석별 입력 스레드**(대기 바이트 상한 1MiB · 넘으면 받지 않음 = 확인 없음) → 자식이 입력을 안 읽어도 serve 는 끊김을 보고 조종자 자리를 푼다.
  - INPUT(id · 수신 확인 = PTY 에 다 씀 · 중복 제거 4096 · dup=1 = 이미 받음(썼거나 쓰는 중)) · RESIZE · SIGNAL(허용 목록) · RELEASE · FOREGROUND · EXIT_ACK.
  - **회수 순서**: `waitid(WNOWAIT)` 로 끝남만 봄 → 잠금 안에서 `reaped` 표시 → 그 뒤 회수. SIGNAL·RELEASE 는 같은 잠금 안에서 표시를 보고 killpg → 회수된(재사용될 수 있는) pid 를 치지 않음.
  - **종료 알림**: 읽기가 끝났거나 회수 뒤 2초(DRAIN)가 지나면 한 번 — EXITED·`<id>.exit` 에 `final_offset`(누적 출력 끝) · `output_open`(PTY 를 쥔 다른 프로세스가 있어 출력이 더 올 수 있음).
  - **종료 기록 영속 게이트**: `<id>.exit` 쓰기 결과를 상태에 둠 · 실패면 supervise 가 100ms 마다 다시 씀 · **디스크에 남기 전에는 조종자 없이 끝내지 않음**. 모든 자식 끝 + (전부 확인 또는 조종자 없이 2초 + 기록 있음) = 정리 후 종료(`output_open_seats` 기록).
  - 핸드셰이크: 동시 상한 16(`busy`) · 전체 절대 기한 3초(타이머가 소켓을 닫음) · HELLO 본문 상한 4KiB.
  - 거절 기록 = 사유 · 피어 · 현재 세대 · 현재 조종자 · 직전 조종자와 끊긴 시각. `--seats N` = 판별 1개 비교 변형.
  - `peer.rs`: 맥 `LOCAL_PEERTOKEN` 감사 토큰 → Security `SecCodeCopyGuestWithAttributes(kSecGuestAttributeAudit)` → 코드 경로 · (선택) `--requirement` 코드서명 요구사항 · euid · **잠금 파일을 한 번 열어 그 fd 로 보유 여부(flock 비차단 시도)와 pid 를 함께 읽음** · 확인 불가 = 거절 · 맥 밖 = 항상 거절.
  - `registry.rs`: 원자 기록(**대상 파일 이름 전체 + pid + 호출 번호 · create_new** · rename 뒤 폴더 fsync · 실패 시 임시 파일 삭제) · id 잠금 · 교체 기록(O_APPEND · fsync) · 부팅 id(`kern.bootsessionuuid`) · 프로세스 시작 시각(proc_pidinfo).
  - `proto.rs`: `[kind u8][seat u32][len u32][payload]` · CORE_VERSION=1 · 16MiB 상한 · `read_frame_max`(HELLO 4KiB).
- 단위 시험 **15/15**(`cargo test --bin cys-seatkeep` · 신규 3 = 형제 파일 동시 원자 기록 무충돌(뮤턴트 = 옛 `with_extension` 이름이면 실패 확인) · id 잠금 배타 · HELLO 상한).
- 시험대 = `~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t2/harness/`(sk.py · ctl.py · t2.py · seat.py · a11.py · a11_stand.py · a13.py · tcc.py) · 결과 = `../results/`(t2.jsonl 누적 + 회차별 *.out) · 고치기 전 실행 파일 대조본 = `../bin-old/cys-seatkeep-0704dc03-release`.

## 시험 명령
```
cd ~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t2/harness
python3 t2.py all                     # 기준 시험 + 고침 회귀 시험 전부(디버그 빌드)
python3 t2.py fixes                   # 고침 회귀 시험만
SK_BIN=../bin-old/cys-seatkeep-0704dc03-release python3 t2.py fixes   # 옛 실행 파일 대조(갈라져야 의미)
python3 a11.py                        # launchd 격리 라벨(local.skt2.seatkeep-a11) bootout·unload -w 각 3
SK_BIN=<워크트리>/target/release/cys-seatkeep python3 a13.py 1 5 20 40   # 비용
python3 tcc.py                        # TCC 1회 관찰
```

## 잰 것(합격 기준)
모든 수치 = 결과 파일 `~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t2/results/` 의 회차 기록(t2.jsonl 누적 · *.out). 「옛」 = 고치기 전 `0704dc03` 실행 파일.

### 브리프 합격 기준(최종 코드 · 디버그 빌드 · t2-all-postfix-*.out)
| 기준 | 결과 |
|---|---|
| A3 seatkeep 사망 = 그 좌석만 | **3/3** — 죽인 seatkeep 의 좌석만 `SIGNAL 1` · 나머지 2개 생존 · 대조군(판별 1개 · 좌석 3) = 3개 모두 사망 |
| A8ⓐ 다른 실행 파일(perl) | **5/5 거절** `exe_mismatch` |
| A8ⓐ 잠금 없이 접속 | **5/5 거절** `lock_not_held` |
| A8ⓑ 조종자 살아 있을 때 같은 프로세스 두 번째 | **5/5 거절** `controller_alive` |
| A8ⓑ 조종자 살아 있을 때 다른 프로세스 | **5/5 거절** `lock_pid_mismatch` |
| A8ⓕ 죽은 조종자 pid 위조 | **5/5 거절** `lock_pid_mismatch` |
| 코드서명 요구사항 불일치 | **1/1 거절** `requirement_unmet` |
| 조종자 SIGKILL 12회(계획 끊기 6 · 강제 6) | **자식 생존 12/12 · 같은 pid · 신호 0** · 정답 대조 누락 줄 0 · 구멍 0 |
| A16(seatkeep 쪽) | accept 13 = 접속 13 · disconnect 13 · 빠진 줄 0(셈 규칙 = accept − accept_aborted) |
| 유실 보고값 = 실제 구멍(꼬리 4KiB) | **3/3 일치**(5192 · 5624 · 5408바이트 — 꼬리 초과를 실제로 찌름 · 시험기 고침: 고정 2초 → 정답 파일 줄 수로 꼬리 2배 초과 확인) |
| A10 고아 0 | 조종자 없음 10/10(종료 기록 남김 · 소켓 정리 · phase=exited) · 조종자 확인 3/3(기록 삭제) · **남은 seatkeep 프로세스 0** |
| A14① 기동~확정 사이 띄운 쪽 SIGKILL | **5/5** — 죽인 때 phase=prepare · 확정 도달 · 등록부 밖 작성자 0 · 새 조종자 WELCOME |
| A11 launchd 격리 라벨 | **6/6**(bootout 3 · unload -w 3) — 대조군(같은 그룹 일반 자식) 6/6 사망 = 시험 유효 · seatkeep·좌석 생존 · 신호 0 · 새 조종자 WELCOME · 라벨 `local.skt2.seatkeep-a11` 미적재 · plist 삭제 확인 |
| TCC 1회 | 직접 자식·seatkeep 아래 자식 모두 `ls ~/Documents` rc 0 · 걸림 없음(권한 창 없음) — 한계는 아래 |

### A13 비용(릴리스 빌드 · 20초 창 · 같은 좌석 프로그램·부하·조종자 · a13-postfix-0958.out)
판정선(master#a3db2868 ③ · 측정 전 잠금) = 좌석당 방식 40좌석 합 RSS ≤ 320MB · 유휴 CPU 합 ≤ 2% → **통과**(RSS 303.0 / 307.0MB · 유휴 CPU 0.627%). 여유 약 4%.

| 부하 | 좌석 수 | 좌석당 합 RSS | 판별 1개 RSS | 좌석당 실제 점유(footprint) | 판별 1개 점유 | 좌석당 CPU% | 판별 1개 CPU% | 좌석당 스레드/fd/유닉스 소켓 | 판별 1개 스레드/fd/소켓 | 좌석당 동시 기동→전부 확정 / 붙기→전부 WELCOME |
|---|---|---|---|---|---|---|---|---|---|---|
| quiet | 1 | 7.5 | 7.5 | 2.5 | 2.5 | 0.0 | 0.0 | 7/12/4 | 7/12/4 | 0.200 / 0.009초 |
| quiet | 5 | 37.6 | 8.1 | 12.5 | 3.1 | 0.0 | 0.049 | 35/60/20 | 19/24/4 | 0.183 / 0.020초 |
| quiet | 20 | 150.9 | 9.6 | 50.3 | 4.6 | 0.099 | 0.049 | 140/240/80 | 64/69/4 | 0.390 / 0.046초 |
| quiet | 40 | **303.0** | 11.3 | 101.2 | 6.4 | **0.627** | 0.049 | 280/480/160 | 124/129/4 | 0.704 / 0.068초 |
| noisy | 1 | 7.6 | 7.6 | 2.6 | 2.6 | 0.05 | 0.048 | 7/12/4 | 7/12/4 | 0.202 / 0.013초 |
| noisy | 5 | 38.0 | 8.4 | 12.8 | 3.4 | 0.191 | 0.147 | 35/60/20 | 19/24/4 | 0.207 / 0.014초 |
| noisy | 20 | 152.9 | 10.8 | 52.1 | 5.8 | 0.442 | 0.347 | 140/240/80 | 64/69/4 | 0.418 / 0.032초 |
| noisy | 40 | **307.0** | 14.0 | 105.7 | 9.2 | 0.896 | 0.592 | 280/480/160 | 124/129/4 | 0.706 / 0.070초 |

- 단위 MB(RSS·footprint는 1초 표본 합의 창 안 최댓값) · CPU% = 창 동안 누적 CPU 시간 ÷ 경과(ps 해상도 0.01초) · quiet = 좌석당 5초에 1줄 · noisy = 50ms 간격 약 215B/줄.
- 맥 RSS 는 공유 라이브러리를 프로세스마다 중복 계산한다 — 실제 점유(phys_footprint)는 좌석당 약 2.5MB(40좌석 101~106MB). 판정은 잠근 대로 RSS.
- 고치기 전(같은 시험 · a13-run-0937.out): 40좌석 RSS 291.1 / 297.5MB · 유휴 CPU 0.0% · 스레드 6/좌석. 고침으로 좌석당 입력 스레드 1개·소켓 fd 2개가 늘어 RSS +약 12MB(40좌석).
- 고침이 출력 흐름을 늦추지 않았는지 대조: noisy 좌석 5 · 옛/새 실행 파일 교대 4회 = 좌석이 찍은 줄 새 654·656 vs 옛 664·669(차이 약 1.5% · 잡음 수준).

### codex 1R 고침 회귀 시험(최종 코드 vs 옛 실행 파일 — 갈라져야 의미 · fixes-*.out · stdinblock-*.out · inject-*.out)
| codex 지적 | 시험 | 새 | 옛 |
|---|---|---|---|
| #1 안 읽는 조종자 역압(blocking) | `evict` — 조종자가 WELCOME 뒤 25초 안 읽음 · 좌석 고속 출력 | **통과**: 자식 출력 20초 내내 증가(518줄) · 10.0초에 끊김 기록 · 조종자 쪽 소켓 닫힘 | **실패**: 128줄에서 멈춤(자식이 PTY 쓰기에 막힘) · 끊김 기록 0 |
| #2 입력 쓰기 막힘(major) | `stdin_block` — raw 모드로 입력을 안 읽는 자식 + 256KiB INPUT 뒤 조종자 SIGKILL | **통과 3/3**: 새 조종자 0.05~0.07초 만에 WELCOME | **실패 3/3**: 6초 동안 `controller_alive` 13~14회 거절 |
| #13 핸드셰이크 기한(minor) | `slowhello` — HELLO 를 0.8초에 1바이트 | **통과 3/3**: 3.42~3.46초에 끊김(`no_hello`) | **실패 3/3**: 7.7초 뒤 WELCOME |
| #6 같은 id 재기동이 등록부를 덮음(major) | `sameid` | **통과 3/3**: 둘째 rc 4 · 등록부 = 첫째 pid·committed · 첫째 WELCOME | **실패 3/3**: 둘째가 등록부를 자기 pid·prepare 로 덮음 |
| #12 미확인 종료 기록 덮음(major) | `exitreuse` | **통과 3/3**: 둘째 rc 4 · 기록 code 5 그대로 | **실패 3/3**: 기록이 code 9 로 덮임 |
| #11 종료 순서(major) | `exitorder` — 300000바이트를 쏟고 바로 끝남 | **통과 3/3**: EXITED 뒤 출력 0 · final_offset 300000 = 받은 끝 · output_open false | 실패 3/3(필드 없음) — **단, 옛도 순서 자체는 맞았음 = 순서 결함은 이 시험으로 재현 못 함** |
| #5 종료 기록 쓰기 실패 무시(blocking) | `exitfail` — 상태 폴더 쓰기 금지 주입 5초 → 복구 | **통과 3/3**: 막힌 동안 끝내지 않음 · 기록 실패 1줄 · 복구 뒤 기록(code 4) 남기고 종료 | **실패 3/3**: 기록 없이 종료(code 없음) |
| #7 확정 실패 후 계속(major) | `commitfail` — 기동~확정 사이 쓰기 금지 주입 | **통과 3/3**: rc 3 · 자식 정리(생존 0) · `commit_failed` 기록 | **실패 3/3**: 계속 실행 · 등록부 밖 자식 생존(phase=prepare · 자식 목록 없음) |
| #8 재생 프레임 칸 초과 누락(major) | `replay` — 좌석 140 × (꼬리 + 종료) + WELCOME = 281 프레임 | **통과 2/2**: 140/140 좌석 출력·종료 받음 | **실패 2/2**: 132·128 좌석만(8~13개 누락) |
| #4 형제 파일 임시 이름 충돌(blocking) | 단위 시험 `atomic_writes_to_sibling_files_do_not_collide`(두 스레드 × 300회) | **통과** | 뮤턴트(옛 이름 규칙)로 **실패** 확인 |

## 알려진 결함·의문(남은 것)
1. **실행 증거 없는 고침**(코드·추론만): #3 회수 직후 신호(WNOWAIT 순서 — 결정적 재현 수단 없음) · #9 꼬리 64MiB 상한·1MiB 분할(1MiB 넘는 꼬리 재생 미실행) · #10 HELLO 뒤 재인증(확인~HELLO 사이 잠금 해제 시험 없음) · #13 동시 핸드셰이크 상한 16(`busy` 미실행) · #14 거절 기록 칸·`accept_aborted`(fsync 실패 주입 없음). codex 「missing」 중 감사 토큰 판독 실패 주입 · 실제 pid 재사용(pidversion) 시험도 없음.
2. **수용된 경계**(master 판단 11-11): 같은 사용자가 공백 구간에 잠금을 잡고 자기 pid 를 쓰면 통과 — 교체 기록으로 사후 적발. HELLO 뒤 재인증과 수락 사이의 아주 짧은 틈은 남음. 시험용 잠금 파일(flock) = 실제 deadman 연동은 T4.
3. **내보내기 값**: 큐 4MiB·멈춤 10초는 위 D1 근거·실측으로 정함. 입력 대기 1MiB · DRAIN 2초는 여전히 근거 없음(맥은 세션 리더 종료 때 단말이 회수되어 DRAIN 이 거의 안 쓰임 — 검증 관측). 멈춘 cysd 가 잠금을 쥐고 있으면 새 cysd 는 못 붙는다(설계상 잠금 = 데몬 하나).
4. **입력 의미**: dup=1 = 「이미 받음(썼거나 쓰는 중)」 · 대기 상한을 넘거나 쓰기 실패면 확인 없음(NACK 프레임 없음 · 조종자는 「모름」).
5. **확정 실패(rc 3) 경로**는 `prepare` 등록부와 (폴더 쓰기 금지 시) 죽은 소켓 파일을 남긴다 — 다음 기동이 소켓은 지우고, 등록부는 죽은 pid 의 prepare 로 남음(T4 입양 규칙에서 「죽은 pid 의 prepare = 무시」 필요).
6. **TCC 한계**: 부모가 터미널 앱(이 좌석)인 경로만 봄 · TCC 로그에 귀속 줄 0건이라 「책임 프로세스」는 관찰 못 함 · 제품 경로(launchd 로 뜬 cysd 아래 seatkeep)는 미관찰 → T4/T6 에서 실제 서명 앱으로 다시 볼 것.
7. **A11 잔재**: unload -w 가 launchd 금지 목록에 `"local.skt2.seatkeep-a11" => enabled` 1줄을 남김(OS 가 지우지 않음 · enable 로 허용 상태로 되돌려 둠).
8. **A13 여유 약 4%**(307 / 320MB) — 좌석당 스레드 7 · fd 12 · 유닉스 소켓 4(40좌석 = 스레드 280 · fd 480). 판별 1개는 40좌석 14MB. 판정은 master.
9. 감사 토큰 경로가 앱 번들의 **주 실행 파일이면 번들 경로**(실측: Homebrew 파이썬 = `…/Python.app`) — T4 에서 cysd 경로 대조 규칙을 이에 맞춰야 한다.
10. 시험 전용 환경 변수 `CYS_SEATKEEP_TEST_COMMIT_DELAY_MS` — 제품 편입 전 제거 또는 시험 빌드 한정.
11. 맥 밖: 리눅스 = 거절만 · 윈도우 = 「유닉스 전용」 안내 후 종료(T7). **윈도우 대상 컴파일 점검은 이 맥에서 불가**(`cargo check --target x86_64-pc-windows-msvc` 가 의존성 libsqlite3-sys C 빌드에서 실패 · seatkeep 무관) — 실측 없음. 새 [[bin]] 이 CI 에서 걸리는지: CI 빌드는 `--bin cys`·`--bin cysd` 를 명시해 쓰는 곳이 대부분이나 전수 확인은 안 함.
12. 핸드셰이크 기한 타이머 스레드가 성공한 연결에서도 3초 동안 남음(소켓 사본 fd 1개).
13. **A13 결정 = 좌석당 방식**(master#2eb05a66 · 판정선 불변). 단점(40좌석 스레드 280 · fd 480 · RSS 여유 4%)은 **T3 편입 때 같은 표를 다시 재서 판정선을 넘으면 좌석당 스레드 줄이기를 먼저 본다.**

14. **D7(이번에 고치지 않음 · 관측과 선택지만)**: 좌석 리더(자식)가 끝난 뒤 그룹에 남은 손자에는 SIGNAL·RELEASE 가 닿지 않는다(회수 표시 뒤 killpg 금지) — HUP 을 무시하는 손자는 리더 종료·seatkeep 종료 뒤에도 산다(검증 관측 `vt.py signal_right_after_reap`). 선택지: ⓐ 그룹이 살아 있는 동안은 pgid 가 재사용되지 않으므로 「회수 뒤에도 그룹에 살아 있는 프로세스가 있으면 killpg 허용」(kill(-pgid,0) 확인 뒤) ⓑ seatkeep 종료 때 남은 그룹에 SIGHUP→SIGKILL 정리 ⓒ 좌석 수명을 「그룹 기준」으로 바꿈(T0 「좌석 수명 = 자식 기준」과 함께 결정). 결정 = master(T3/T4).
15. **D3 남은 위험**: 토큰은 「마지막 사용 프로세스」라 fd 를 넘겨받아 HELLO 전에 보내는 경로는 재인증이 `peer_changed` 로 막지만, 처음 확인 전에 넘겨받으면 넘겨받은 쪽이 처음부터 확인 대상이 된다(그 프로세스도 실행 파일·잠금·짝 조건을 모두 통과해야 함 = 같은 사용자 경계 안 · 수용 경계와 같음). 잠금 파일 (pid, 출생 시각) 형식은 T4 cysd 쪽 작업.

## 다음 첫 행동(1줄)
master 가 독립 검증 좌석(브리프 §6 5항 + 뮤턴트) 편성 → 그 결과 + codex 재검(선택)으로 1회 고침. T3(cysd 연결) 착수 조건은 【확인요청】 본문.
