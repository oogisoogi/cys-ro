# HANDOFF — TICKET=cysr-seatkeep-t3 (cysd 좌석 생성 경로 = 좌석 프로세스 손잡이 + seatkeep 경유 · 맥 · 노브 기본 끔)

- 가지 = `feat/seatkeep-t3`(← t2 `a48d36e1`) · push 0 · 설계 메모 = `docs/seatkeep/T3-DESIGN.md`
- master 지시: master#c125bc97(고칠 것 3: 잠금 2칸 = 노브 켬만 · `--end-on-controller-loss` · 출력 폭주 실측 / 답: rows·cols 수용 · 등록부 3파일 잔존 = T4) · master#fe07cc6a(D7 = 결정 B · SIGNAL target 칸)
- 시험대 = `~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t3/harness/`(t3life.py · t3a13.py · t3misc.py) · T2 시험대 사본 = `../t2copy/harness/`
- 격리 시험 실행기 = scratchpad `run_tests.sh <label> <cargo test 인자>`(CYS_* 제거 · HOME/XDG 임시 · CYS_SEATKEEP 만 통과)

## 상태 = 【갈무리】(2026-11-12 01:2x · CTX 55%→60% 매듭 · master#77162b13 허용) — 후임이 아래 「다음 첫 행동」부터
- 최종 커밋 = 이 HANDOFF 커밋(코드 마지막 = f4b9b6ab) · push 0 · 라이브 무접촉.

## 다음 첫 행동(1줄)
master#77162b13 「조종자 종속 모드」 구현: cys-seatkeep 의 `--end-on-controller-loss` 를 `--controller-bound` 로 넓혀(아래 결정 그대로) seat_proc.rs 기동 인자도 바꾸고, 시험 ①~④ 를 돌린다.

## master 결정(미구현 · 후임 몫) — master#77162b13 원문 요지
- 출력 폭주 = 결정 **A 를 「조종자 종속 모드」 안으로**(B 흐름 제어 프레임 · C 꼬리 늘리기 안 함). 기동 인자 하나(예 `--controller-bound` · 지금 `--end-on-controller-loss` 를 넓힘)가 있으면 seatkeep 은 **직접 PTY 처럼 투명하게**:
  ⑴ 조종자 연결이 끊기면 PTY 마스터를 닫고 끝남(지금 구현됨 · `end_for_controller_loss`)
  ⑵ 조종자가 밀리면 **PTY 읽기를 멈춘다**(커널 역압 → 자식이 조종자 속도에 맞춰 멈춤 · 유실 0) — 지금은 4MiB 큐 → 「밀림」 → 꼬리 따라잡기(T2)
  ⑶ **write_stalled 로 내보내지 않는다** — 연결이 살아 있는 한 기다린다(멈춘 cysd 아래서 자식도 멈춰 삶 = 직접 PTY 와 같음)
  인자가 없으면 **T2 동작 그대로 한 줄도 안 바뀜**(자식 안 멈춤 · 4MiB 큐 · 꼬리 따라잡기 · write_stalled 10초) — T2 시험 무수정 초록.
- 시험(이 모드): ① 같은 204MB 폭주(`seat_flood_tests`) = 받은 바이트 204,000,011 · 구멍 0 · 순서 어긋남 0 · 시간·RSS 를 노브 끔과 나란히 ② 조종자(격리 cysd)를 SIGSTOP 15초 → SIGCONT = 좌석 생존 · 유실 0 · write_stalled 0 ③ 인자 없는 대조군 = 아래 표 「켬」 줄과 같은 동작(유실 있음 · 자식 안 멈춤) ④ 뮤턴트(역압 줄 · 내보내기 금지 줄 각각).
- 구현 자리(코드 판독 전 · 추정): seatkeep `main.rs` 의 출력 경로(`read_loop` → 조종자 큐에 넣는 함수 · 「밀림」 표시 `behind`) · 쓰기 스레드의 `CTL_WRITE_TIMEOUT` 설정(`write_half.set_write_timeout`) · 쓰기 스레드 오류 갈래의 `evict write_stalled`. 제어 큐 상한(1MiB · `evict_ctl_full`)은 결정에 언급 없음 — 그대로 둘지 master 에 1줄 확인 권고.

## T4 로 넘길 것(master#77162b13 지시)
- 입양을 켤 때(T4) 「조종자가 붙어 있는 동안의 밀림 정책(역압 + 내보내기 vs 흐름 제어 프레임)」을 다시 정한다. 근거 표 = 아래 「출력 폭주」(T2 기본 동작 = 노브 켬 유실 95.3% · 194,422,979 / 204,000,011 바이트).
- `--controller-bound`(지금 `--end-on-controller-loss`)를 빼는 자리 = `src/bin/cysd/seat_proc.rs` seatkeep 기동 인자(주석 있음).
- 끝난 좌석 등록부 3파일(.json·.log·.lock) 정리 · 죽은 pid 의 prepare/committed 무시(T2 인계 7).
- T2 인계 중 T4·T6·T7 몫(입양 규칙 · 번들·봉인·서명 · pkill 폴백 · 윈도우 컴파일) 그대로.

## 실측
### 커밋 · 시험 수
- 커밋: ① bda1f68e(손잡이 + 직접 PTY 옮기기) · ①' 98d03214(옮긴 자리 소스 핀 ⑦ · D7 시험기 좀비 · 선언) · ②③④ 942d6d7e · ba446e5d(Cargo.lock)
- 기준선(옮기기 전 a48d36e1 · 노브 없음): cysd 3224 통과 · 3 실패(native_publication 2 · pending_requests c8registry 1 = `Locked`) · 15 무시 · rc 101
- ① 트리 노브 끔: 3224 통과 · 6 실패 = native_publication 2(기준선과 같음) · pending_requests 1(`Locked` — 기준선과 다른 이름 · 같은 부류 흔들림) · 소스 핀 ⑦(옮긴 자리 · ①'에서 고침) · C8 핀(시험이 디스크 소스를 읽는 중에 ② 코드가 들어감 · 표 등재로 고침) · D7 시험기(좀비 = 산 것으로 셈 · ①'에서 고침)
- ② 트리 노브 끔(942d6d7e 직전 빌드): **3242 통과 · 2 실패(native_publication 2 = 기준선과 같음) · 16 무시** · rc 101
- seatkeep 단위: 30/30(T2 27 + 새 3: reap_marks_before_reaping · signal_target_leader_group_and_refusal · ensure_dir_is_race_safe_on_first_creation)

### 좌석 수명(master#c125bc97 ② · t3life.py · 릴리스 · results/t3life.jsonl)
| 노브 | cysd 내림 | 회차 | 좌석 SIGHUP 으로 끝남 | seatkeep 잔존 | 끝나기까지 ms | seatkeep 기록 사유 |
|---|---|---|---|---|---|---|
| 켬 | SIGKILL | 6 | 6/6 | 0 | 178~452 | controller_lost ×6 · 등록부 ended_controller_lost |
| 켬 | SIGTERM | 6 | 6/6 | 0 | 191~384 | controller_lost ×6 |
| 끔(직접 PTY) | SIGKILL | 6 | 6/6 | — | 74~200 | — |
| 끔(직접 PTY) | SIGTERM | 6 | 6/6 | — | 151~423 | — |
대조군(인자 없는 seatkeep = 자식 생존) = T2 `t2.py all` 의 조종자 SIGKILL 12회(아래 t2 재실행 줄).
- 노브 켬 전체(ba446e5d · CYS_SEATKEEP=1): **3239 통과 · 5 실패 · 17 무시** — native_publication 1(기준선 같음) · r1f 전경 전제(fd ≥ 0 가정) · 시험용 잠금이 쓰기 막힌 데몬 폴더에(unpreservable_queue_wal) · u18 샌드박스 검체 · v116(앞 시험 독 전파) → f4b9b6ab 에서 전제 2건 고친 뒤 그 5건 + D7 3건 재시험 **7/7(필터 합 8 중 7 + u18 포함) 초록**. 노브 켬 전체 재실행은 아직(다음 할 일 ①).
- D7(결정 B 반영 뒤 · 노브 켬): 3/3 초록 = 직접 PTY 표와 같음(o1 생존).

### 출력 폭주(master#c125bc97 ③ · seat_flood_tests · 204.0MB 최대 속도)
| 노브 | 받은 바이트 | 유실 | 순서 어긋남 | 시간 | cysd RSS 최고 | seatkeep RSS 최고 | write_stalled | 좌석 |
|---|---|---|---|---|---|---|---|---|
| 끔 | 204,000,011 | 0 | 0 | 56.6초 | 268.6MB | — | — | 생존 |
| 켬 | 9,577,032 | 194,422,979(95.3%) | 3 | 3.2초 | 116.3MB | 22.1MB | 0 | 생존 |
→ 【결정필요】 올림(01:23 · 선택지 A 권고 = 조종자 붙어 있는 동안 밀리면 PTY 읽기 멈춤 · 프레임 변경 0). 미결.

### 입력→화면 왕복(seat_latency_tests · `surface.send_text` RPC → 파서 화면에 반향 2회 · n=300)
| 노브 | p50 | p90 | p99 | 최대 | 입력 중 전경 질의 |
|---|---|---|---|---|---|
| 끔(옮긴 뒤) | 3.00ms | 3.50ms | 5.13ms | 34.2ms | — |
| 켬 | 2.89ms | 3.47ms | 5.69ms | 17.5ms | 0회 |
- 「옮기기 전」(a48d36e1) 값은 **미실측**(이 시험 파일이 그 커밋에 없음 · 옛 빌드에 시험을 얹어 다시 재야 함).
- 전경 질의 0회 = 이 좌석(`cat`)은 에이전트 그룹 표식이 0 이라 V2 지름길(시스템 콜·소켓 왕복 없음). 에이전트 좌석(표식 섬)에서는 입력 계수마다 FOREGROUND 왕복 1회가 낀다 — **그 경우 지연은 미실측**.

## 지시 없이 내린 판단
1. 손잡이 얼굴 = portable-pty `MasterPty`/`Child` 트레이트(필드 타입 불변 · 시험 구역 86곳 무수정) — 메모 §2(master 수용 c125bc97).
2. 운영 직접 접근 5곳(close_auth·handlers·repaint·governance·state)은 본문을 seat_proc 로 옮기고 옛 이름은 한 줄 위임으로 남김.
3. anyhow 직접 의존 승격(MasterPty 오류 타입 이름 필요 · Cargo.lock 1줄).
4. seatkeep 상태 폴더 동시 첫 만들기 경합 고침(T2 코드 · 노브 켬 시험에서 rc 3 재현 · 회귀 시험).
5. SIGNAL `target` 칸이 문자열이 아니거나 null 이면 모르는 값과 같이 거절 · `child_pid ≤ 0` 이면 어떤 신호도 안 보냄(T2 는 killpg(0) = 자기 그룹이 될 수 있었음).
6. cysd 는 RELEASE 를 쓰지 않음(그룹 SIGHUP = 결정 B 와 어긋남 · T6 판 내림 몫).
7. 시험 빌드 한정: seatkeep 상태 폴더 = 짧은 임시 폴더 `cskt-<pid>` · 조종자 잠금 = 그 안 `locks/<해시>.lock`(시험 데몬은 시작 잠금을 안 잡음 · 맥 소켓 104바이트) — 제품 경로(`state_dir` · `socket.with_extension("lock")`)와 다름.
8. 시험 환경 변수 `CYS_SEATKEEP_TEST_COMMIT_DELAY_MS` = `cfg(debug_assertions)`(릴리스 빌드에 문장 없음 · 제거 아님 — T2 시험대가 디버그 빌드로 씀).

## 확인 못 한 것 · 남은 것
- 노브 켬 **전체** 재실행(f4b9b6ab 이후) · t2 `all`(대조군 = 인자 없는 seatkeep 자식 생존 포함) · A13 1·5·20·40 · 100좌석 잔존 파일 · 40좌석 동시 생성/닫기 · 뮤턴트 표 — 결과 파일 = `seatkeep-t3/results/{t2-all-t3.out,t3a13-on.out,t3misc.out,t3-mutants.tsv}`(돌리는 중 01:24~).
- M09 결정적 시험의 부하 아래 10/10(동시 빌드 중) — 미실행.
- 윈도우·리눅스 컴파일 점검 = 미실측(T2 관측 그대로 · `cfg` 로 가름: seatkeep 경로 = macos 만 · 그 밖 노브 켬 = 생성 실패 + 이유).
- 에이전트 좌석 입력 지연(전경 왕복 낌) 미실측.
- 끝난 좌석 등록부 3파일(.json·.log·.lock) 잔존 = T4 몫(수 측정은 t3misc).
