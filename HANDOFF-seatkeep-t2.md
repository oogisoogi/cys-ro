# HANDOFF — TICKET=cysr-seatkeep-t2 (좌석 보유 장치 seatkeep 단독 시제품 · 맥 · cysd 미연결)

- 상태 = **독립 검증 대기**(2026-11-11 재개 09:25 → 시험 전부 + codex 1R + 고침 1회 끝 · 【확인요청】 10:14 접수 master#2eb05a66). 검증 좌석 = `~/axdev/.wt/seatkeep-t2-verify`(d41c00eb 스냅샷 · TICKET=cysr-seatkeep-t2-verify) — 결함 표가 오면 그때 1회 고침 · 그 전 코드 수정 0.
- 가지 = `feat/seatkeep-t2`(v1.1.14 `270e3e21` 위) · 커밋 2개(`0704dc03` 시제품 · 이 커밋 = codex 1R 고침 + 시험 결과) · push 0.
- 설계·브리프 = `~/axdev/master/reports/2026-11-11-cysr-holder-design/`(DESIGN.md · T0-surface-state.md · briefs-draft/T2.md · master#a3db2868 결정 5).
- codex 1R = 같은 폴더 `codex-t2-1R.prompt.md`(의뢰문) · `codex-t2-1R.verdict.json`(판정 BLOCK · 대상 `0704dc03`) · `codex-t2-1R.txt`(전 기록).

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
3. **조종자 내보내기 값은 실측 근거 없는 선택**: 칸 1024 프레임(약 16MiB) · 소켓 쓰기 기한 10초 · 입력 대기 1MiB · DRAIN 2초. 내보내진 조종자는 다시 붙을 수 있으나, 멈춘 cysd 가 잠금을 쥐고 있으면 새 cysd 는 못 붙는다(설계상 잠금 = 데몬 하나).
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

## 다음 첫 행동(1줄)
master 가 독립 검증 좌석(브리프 §6 5항 + 뮤턴트) 편성 → 그 결과 + codex 재검(선택)으로 1회 고침. T3(cysd 연결) 착수 조건은 【확인요청】 본문.
