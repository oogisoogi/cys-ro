# HANDOFF — TICKET=cysr-seatkeep-t2 (좌석 보유 장치 seatkeep 단독 시제품 · 맥 · cysd 미연결)

- 상태 = **매듭 후 정지**(master#c495a902 · 2026-11-11 01:00 · 계정 주간 한도) · 재개는 master 1줄.
- 가지 = `feat/seatkeep-t2`(v1.1.14 `270e3e21` 위) · push 0.
- 설계·브리프 = `~/axdev/master/reports/2026-11-11-cysr-holder-design/`(DESIGN.md · T0-surface-state.md · briefs-draft/T2.md · master#a3db2868 결정 5).

## 한 것
- 새 실행 파일 `cys-seatkeep`(`src/bin/cys-seatkeep/` 4파일 · `Cargo.toml` [[bin]] 1항). cysd·cys 기존 파일 수정 0.
  - `main.rs`: setsid · 등록부 준비 → 소켓(0600) → 자식 기동(portable-pty · setsid+TIOCSCTTY) → 확정 · 좌석별 읽기(꼬리 기본 1MiB · 누적 오프셋) · 조종자 1명(살아 있으면 새 접속 거절) · HELLO 핵심 판 비교 · 교체 기록이 먼저(실패 = 거절) · WELCOME + 오프셋 기준 꼬리 재생(유실 = max(0, 꼬리 시작 − 재개 오프셋) 을 accept 기록에 적음) · INPUT(id·수신 확인·중복 제거 4096) · RESIZE · SIGNAL(허용 목록 · 회수된 자식엔 안 보냄) · RELEASE · FOREGROUND · EXIT_ACK · 종료 기록 `<id>.exit`(확인까지 보존) · 모든 자식 끝 + (전부 확인 또는 조종자 없이 2초) = 정리 후 종료. `--seats N` = 판별 1개 비교 변형.
  - `peer.rs`: 맥 `LOCAL_PEERTOKEN` 감사 토큰 → Security `SecCodeCopyGuestWithAttributes(kSecGuestAttributeAudit)` → 코드 경로 · (선택) `--requirement` 코드서명 요구사항 · euid · 잠금 실제 보유(flock 비차단 시도) + 잠금 파일 pid = 토큰 pid. 확인 불가 = 거절 · 맥 밖 = 항상 거절.
  - `registry.rs`: 등록부 원자 기록 · 교체 기록(O_APPEND · fsync) · 부팅 id(`kern.bootsessionuuid`) · 프로세스 시작 시각(proc_pidinfo).
  - `proto.rs`: `[kind u8][seat u32][len u32][payload]` · CORE_VERSION=1 · 16MiB 상한.
- 단위 시험 12/12(`cargo test --bin cys-seatkeep`).
- 시험대 = `~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t2/harness/`(sk.py · ctl.py · t2.py · seat.py) · 결과 = `../results/t2.jsonl`.

## 잰 것(합격 기준 · 디버그 빌드)
| 기준 | 결과 |
|---|---|
| A3 (seatkeep 사망 = 그 좌석만) | **3/3** — 죽인 seatkeep 의 좌석만 `SIGNAL 1` · 나머지 2개 생존 · 대조군(판별 1개 · 좌석 3) = 3개 모두 사망 |
| A8ⓐ 다른 실행 파일(perl) | **5/5 거절** `exe_mismatch` |
| A8ⓐ 잠금 없이 접속(공백 구간) | **5/5 거절** `lock_not_held` |
| A8ⓑ 조종자 살아 있을 때 같은 프로세스의 두 번째 접속 | **5/5 거절** `controller_alive` |
| A8ⓑ 조종자 살아 있을 때 다른 파이썬 프로세스 | **5/5 거절** `lock_pid_mismatch` |
| A8ⓕ 죽은 조종자 pid 를 잠금 파일에 위조 | **5/5 거절** `lock_pid_mismatch` |
| 코드서명 요구사항 불일치 | 1/1 거절 `requirement_unmet` |

## 남은 것(이 순서)
1. `python3 t2.py ctlcrash` — 조종자 graceful 6 + SIGKILL 6 동안 자식 생존·같은 pid · 정답 대조 · A16(seatkeep 쪽 기록 수 = 접속 수).
2. `python3 t2.py loss` — 꼬리 4KiB 로 유실 보고값 = 실제 구멍 크기 3회.
3. `python3 t2.py a10` · `python3 t2.py a14` — 고아 0 · 기동~확정 사이 띄운 쪽 SIGKILL 5회.
4. A11 launchd 격리 라벨(bootout·unload -w 각 3 · 끝에 plist 삭제 확인) — 시험기 미작성.
5. A13 비용 — `cargo build --release --bin cys-seatkeep` 후 좌석 1·5·20·40 좌석당 vs 판별 1개(판정선 = 40좌석 합 RSS ≤ 320MB · 유휴 CPU 합 ≤ 2% · master#a3db2868) — 시험기 미작성.
6. TCC 1회 관찰(보호 폴더 읽기) — 미실행.
7. 【확인요청】 TICKET=cysr-seatkeep-t2 + 커밋 해시(→ master 가 독립 검증 좌석 + codex 1R).

## 알려진 결함·의문
- 조종자가 읽지 않으면 채널(256 프레임)이 차고 읽기 스레드가 막혀 자식 출력이 멈춘다(역압) — 허더와 같은 성질이나 상한·끊기 규칙 없음.
- 감사 토큰 경로가 앱 번들의 **주 실행 파일이면 번들 경로**가 나온다(시험 실측: Homebrew 파이썬 = `…/Python.app`). T4 에서 cysd 경로 대조 규칙을 이에 맞춰야 한다.
- 잠금 「보유」 확인은 flock 비차단 시도라, 같은 사용자가 공백 구간에 잠금을 잡고 자기 pid 를 쓰면 통과한다 — master 판단 11-11 의 수용된 경계(교체 기록으로 사후 적발).
- 시험 전용 환경 변수 `CYS_SEATKEEP_TEST_COMMIT_DELAY_MS`(기동~확정 지연) — 제품 편입 전 제거 또는 시험 빌드 한정 필요.
- 맥 밖(리눅스·윈도우)은 거절만 하는 상태 · 윈도우는 실행 파일이 「유닉스 전용」 안내 후 종료(T7).
- 새 [[bin]] 이 릴리스 포장·CI 시험(실행 파일 목록을 세는 것)에 걸리는지 확인 안 함.

## 다음 첫 행동(1줄)
`cd ~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t2/harness && ~/.claude/channels/canon-verify.sh && python3 t2.py ctlcrash` 후 위 「남은 것」 2부터.
