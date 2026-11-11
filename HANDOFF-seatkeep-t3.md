# HANDOFF — TICKET=cysr-seatkeep-t3 (cysd 좌석 생성 경로 = 좌석 프로세스 손잡이 + seatkeep 경유 · 맥 · 노브 기본 끔)

- 가지 = `feat/seatkeep-t3`(← t2 `a48d36e1`) · push 0 · 설계 메모 = `docs/seatkeep/T3-DESIGN.md`
- master 지시: master#c125bc97(고칠 것 3: 잠금 2칸 = 노브 켬만 · `--end-on-controller-loss` · 출력 폭주 실측 / 답: rows·cols 수용 · 등록부 3파일 잔존 = T4) · master#fe07cc6a(D7 = 결정 B · SIGNAL target 칸)
- 시험대 = `~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t3/harness/`(t3life.py · t3a13.py · t3misc.py) · T2 시험대 사본 = `../t2copy/harness/`
- 격리 시험 실행기 = scratchpad `run_tests.sh <label> <cargo test 인자>`(CYS_* 제거 · HOME/XDG 임시 · CYS_SEATKEEP 만 통과)

## 상태 = 【확인요청 2】(후임 surface:2004 · 검증 1회 고침 · 2026-11-12 05:xx) — 다음 = codex 1R(범위 a48d36e1..최종)
- 전임 = 【갈무리】(01:2x · CTX 60%) · 후임 브리프 = 원장 01:26:58(surface:2004 · kind brief).
- 코드 마지막 = f3252d15(조종자 종속 모드) · push 0 · 라이브 무접촉.
- A13 【결정필요】(02:38) = master#18c2e66e 결정 A 로 닫힘(판정선 = 물리 점유 합 ≤ 160MB) → 통과(아래 표).

## 다음 첫 행동(1줄)
독립 검증 좌석의 기록을 받으면 CONFIRMED 만 1회 고친다 → codex 1R(아래 「codex 1R 꼭 물을 것」)

## master 결정(구현됨 f3252d15 · 후임) — master#77162b13 원문 요지
- 출력 폭주 = 결정 **A 를 「조종자 종속 모드」 안으로**(B 흐름 제어 프레임 · C 꼬리 늘리기 안 함). 기동 인자 하나(예 `--controller-bound` · 지금 `--end-on-controller-loss` 를 넓힘)가 있으면 seatkeep 은 **직접 PTY 처럼 투명하게**:
  ⑴ 조종자 연결이 끊기면 PTY 마스터를 닫고 끝남(지금 구현됨 · `end_for_controller_loss`)
  ⑵ 조종자가 밀리면 **PTY 읽기를 멈춘다**(커널 역압 → 자식이 조종자 속도에 맞춰 멈춤 · 유실 0) — 지금은 4MiB 큐 → 「밀림」 → 꼬리 따라잡기(T2)
  ⑶ **write_stalled 로 내보내지 않는다** — 연결이 살아 있는 한 기다린다(멈춘 cysd 아래서 자식도 멈춰 삶 = 직접 PTY 와 같음)
  인자가 없으면 **T2 동작 그대로**(자식 안 멈춤 · 4MiB 큐 · 꼬리 따라잡기 · write_stalled 10초) — T2 시험 무수정 초록. ⚠(검증 반영) 「한 줄도 안 바뀜」은 과장 = 동작 같음 · 의도된 변경 3곳(SIGNAL child_pid ≤ 0 무신호 · 등록부 폴더 첫 만들기 경합 고침 · 시험 지연 변수 릴리스 무시 — T3-DESIGN §0).
- 시험(이 모드): ① 같은 204MB 폭주(`seat_flood_tests`) = 받은 바이트 204,000,011 · 구멍 0 · 순서 어긋남 0 · 시간·RSS 를 노브 끔과 나란히 ② 조종자(격리 cysd)를 SIGSTOP 15초 → SIGCONT = 좌석 생존 · 유실 0 · write_stalled 0 ③ 인자 없는 대조군 = 아래 표 「켬」 줄과 같은 동작(유실 있음 · 자식 안 멈춤) ④ 뮤턴트(역압 줄 · 내보내기 금지 줄 각각).
- 구현(f3252d15): `send_output` 의 밀림 갈래를 `!controller_bound` 로 막음 · `read_loop` 가 읽기 전에 `wait_for_room`(큐 ≥ `BOUND_QUEUE_BYTES` 256KiB 면 반 아래까지 기다림 · 첫 조종자 전 = 꼬리의 남은 칸만큼만 읽음) · 쓰기 스레드가 한 프레임 쓴 뒤 `wake_readers`(기다리는 수 > 0 이고 반 아래면 상태 잠금 잡고 깨움 — 「기다리는 쪽 = 수 올린 뒤 큐를 봄 / 깨우는 쪽 = 큐 내린 뒤 수를 봄」 SeqCst) · 조종자 종속이면 `set_write_timeout` 안 함. 제어 큐 상한은 그대로(master 답 = 끄지 않음 · 시험 ②에서 0 단언).
- (전임 추정 · 이력) 구현 자리(코드 판독 전 · 추정): seatkeep `main.rs` 의 출력 경로(`read_loop` → 조종자 큐에 넣는 함수 · 「밀림」 표시 `behind`) · 쓰기 스레드의 `CTL_WRITE_TIMEOUT` 설정(`write_half.set_write_timeout`) · 쓰기 스레드 오류 갈래의 `evict write_stalled`. 제어 큐 상한(1MiB · `evict_ctl_full`)은 결정에 언급 없음 — 그대로 둘지 master 에 1줄 확인 권고.

## T4 로 넘길 것(master#77162b13 지시 · 후임 확인함)
- ⛔**노브 기본 켬의 차단 조건(D1 · master#6e60316b)**: 조종자 종속/입양 모드에서 역압 중 자식이 끝날 때 꼬리 ≤ 1KiB 유실 — A(seatkeep 이 슬레이브 fd 를 쥐고 있다가 회수 뒤 커널 버퍼를 비우고 닫기) 또는 역압 대기를 `read()` 안에서 하게 하는 다른 길로 닫기 전에는 **기본 켬 금지**. 시험 `seat_tail_known_limit_stalled_controller_child_exit` 의 노브 켬 갈래를 「모자람 0」으로 뒤집는 것이 닫힘의 증거.
  - 미완 탐침(관측 그대로): A 의 바탕(「다른 프로세스가 슬레이브를 쥐면 자식이 끝나도 꼬리가 남는가」) 파이썬 탐침이 **닫기(os.close)에서 멈춰** 60초 시간 초과 2회 — 결과 없음(`harness/ptyprobe/p5_holder_keeps_slave_UNFINISHED.py` · `results/ptyprobe/p5….out`). 손자가 PTY 를 쥔 꼴의 시험도 60초 안에 자식이 안 끝남(세션 우두머리 종료 = 손자 SIGHUP 추정 · 미확정).
  - 덤 확인(master#6e60316b 4 · 탐침 결과만 · 구현 안 함): 「역압 대기를 마스터 fd 의 블로킹 `read()` 안에서」 = **A 보다 싼 길이 못 된다** — `read()` 안에서 멈춘 독자가 있어도 커널 버퍼를 가득 채우고 끝나는 자식의 꼬리는 첫 줄 102바이트만 남고 1,024바이트를 잃었다(시험 노브 끔 비차단 자식 · 2/2) · 또 `read()` 안의 독자는 데이터가 있으면 바로 가져가므로 역압(안 읽기)과 함께 성립하지 않는다(논리).
- P1·P2(검증 PLAUSIBLE): cysd 연결 스레드 하나가 OUTPUT·INPUT_ACK·FOREGROUND_IS 를 차례로 처리 → 출력 소비가 멎으면 입력 확인(기한 없음)·전경 질의(200ms 뒤 모름)도 멎음 · 약 2시간 막히면 전경 재질의가 seatkeep 제어 큐(1MiB)를 채워 control_queue_full → 조종자 종속이라 좌석 HUP. 고칠 방향 = 확인·전경 답을 OUTPUT 과 다른 대기열로.
- 처리 속도 켬 14~19% 느림(검증 2-5a · 원인 추정 = 바이트당 복사 3~4회 + 256KiB↔128KiB 문턱 잠·깨움 왕복 · 프로파일 미실측) · A13 cysd 증가분 noisy +15MB(검증 1회 · 나는 +6.8MB 1회 · 잡음 폭 모름 → T4 에서 3회 반복) · 첫 조종자 꼬리 재생이 상한과 무관하게 최대 1MiB 한 조각(cysd 쪽 64조각 큐 최악 약 1MiB+63×16KiB).
- 입양을 켤 때(T4) 「조종자가 붙어 있는 동안의 밀림 정책(역압 + 내보내기 vs 흐름 제어 프레임)」을 다시 정한다. 근거 표 = 아래 「출력 폭주」(T2 기본 동작 = 노브 켬 유실 95.3% · 194,422,979 / 204,000,011 바이트) + 「후임 실측」(조종자 종속 = 유실 0 · ^C 뒤 바이트 · 재개 지연).
- `--controller-bound` 를 빼는 자리 = `src/bin/cysd/seat_proc.rs` seatkeep 기동 인자(주석 있음 · f3252d15 에서 옛 `--end-on-controller-loss` 를 이 이름으로 바꿈). 빼면 ⑴ 끊김 종료 ⑵ 역압 ⑶ 쓰기 기한 없음 셋이 함께 빠진다 — 입양을 켜면서 ⑵만 남기려면 인자를 나눠야 한다.
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

## 검증 1회 고침(후임 · master#8193a786 처분 · #a9e47c44 보강 · #6e60316b D1 결정 B · 04:02~)
| # | 처분 | 한 것 | 고치기 전 붉음 | 고친 뒤 | 시험 |
|---|---|---|---|---|---|
| D1 | 결정 B = 알려진 한계 | 고침 없음 · 관측 시험 + 탐침 보관 · T4 차단 조건 | 결정적 시험 79b727a2 노브 켬 3/3 정확히 1,024 모자람 · 기제 = 받는 쪽 아님(실험 1회 final_offset = 받은 바이트) | 켬 모자람 1,024(2/2) · 끔 자식 6초 막힘 + 모자람 0(2/2) | `seat_tail_known_limit_stalled_controller_child_exit` |
| D2 | 고침 | seatkeep 기동 때 부모 pid · supervise 100ms 마다 비교 · 기동 때 1 = 잃음 → `parent_lost` | life.py midcreate 0ms(검증 사본) = 1초·5초 시점 좌석·seatkeep 생존 · 끝 사유 no_first_controller | 0ms 2/2 · 1초 시점 둘 다 끝 · 좌석 HUP · `parent_lost` / 1초·5초 = controller_lost | 단위 `bound_parent_loss_is_seen_only_in_bound_mode` + 검증 사본 midcreate |
| D3 | 고침(시험) | attach 의 확인부를 `greet()` 로 떼고 시험 2 | (뮤턴트 MA·MA2 로 확인 — 아래 표) | 2/2 초록 | `greet_refuses_socket_whose_peer_is_not_the_launched_seatkeep` · `greet_refuses_welcome_from_other_pid` |
| D4 | 차선(타입 막기 = 시험 구역 약 86곳 · 30곳 상한 초과) | 게이트 = `.child`/`.master` 필드 참조 자체 · 넘기는 자리·이름 붙은 예외만 허용 · 대상 = cysd 하위 전체 + src/*.rs · 자기 시험에 별칭 검체 등 9개 | 검증 ME(별칭) = 초록(놓침) | 운영 코드 위반 0 · 자기 시험 초록 | `seat_handle_gate_*` 2 |
| D5 | 고침(시험) | 두 칸 잠금 관문 시험 | 검증 MF = 초록(놓침) | 초록 | `quiescent_gate_blocks_live_cysd_holder_two_field_lock` |
| D6 | 고침(문서) | `startup_lock_holder_pid` 를 BOM 문서 위로 | — | `strip_utf8_bom` 문서 복구 | — |
| D7 | 고침 | seatkeep 자식 작업 폴더 = `"."` 상속 · 그래도 실패 + 폴더 없음 = rc 7 · handlers 시험 make_surface 명시 cwd | cwdrace.py(검증 사본) 켬 3/3 생성 실패(rc 5) | 켬 0/3 실패 · 끔 0/3 | 검증 사본 cwdrace |
| 문구 2 | 고침 | T3-DESIGN §0(인자 없는 경로 = 동작 같음 · 의도된 변경 3곳 · 노브 켬 = 시험 전용 · 구별되는 곳 1) · 이 HANDOFF 21줄 | — | — | — |
- 뮤턴트 v2(`harness/t3mutants2.py` · `MUT_SET=v2` · 별도 git 작업트리 `/private/tmp/sk3mut-wt2` 4638cefa · 끝나고 제거 · 기준 회차 8종 전부 초록 확인 뒤 · 결과 `results/t3-mutants-v2.tsv`): **8/8 잡음**
  | 뮤턴트 | 되돌린 줄 | 잡은 시험 |
  |---|---|---|
  | MA(검증 · 같은 뜻으로 다시 씀) | greet 소켓 상대 pid 대조 끔 | `greet_refuses_socket…`(1 실패) |
  | MA2 | greet WELCOME pid 대조 끔 | `greet_refuses_welcome…`(1 실패) |
  | MD(검증) | governance 에 `surface.child.lock()` 직접 | 게이트(1 실패) |
  | ME(검증) | governance 에 별칭 `let ch = &surface.child; ch.lock()` | 게이트(1 실패 · 전: 놓침) |
  | MF(검증) | factory_reset 옛 판독기 `s.trim().parse::<u32>()` | `quiescent_gate_…two_field_lock`(1 실패 · 전: 놓침) |
  | MG | D2 부모 판정 끔 | 단위 `bound_parent_loss…` · 검증 사본 midcreate 0ms(1초·5초 시점 생존) |
  | MH | D7 작업 폴더 다시 찾기(옛 줄) | 검증 사본 cwdrace 켬 3/3 생성 실패 |
  | MI | 역압 대기 빼기 | known_limit 켬(자식이 안 막혀 60초 안에 안 끝남) |
  (1회차 뮤턴트 17/17 은 그대로 유효 — 이번 고침이 그 줄들을 바꾸지 않음.)
- 전체 시험(4638cefa · 뮤턴트 작업과 동시 실행 · 부하 있음): 노브 끔 cysd **3244 통과 · 3 실패 · 17 무시 · rc 101**(native_publication 2 = 기준선 · `settle_hold_denies…` = 검증 2-1c 에서 기준선 a48d36e1 노브 끔에서도 실패한 부하성) / 노브 켬 **3246 통과 · 1 실패 · 17 무시 · rc 101**(native_publication 1 = 기준선 · D7 흔들림 `b3_status_usage…` 재발 없음) · seat_ 묶음 켬 149/149 · 끔 149/149(2 무시) · seatkeep 단위 34/34 · lib factory_reset 49/49.
- 검증 시험대는 읽기만 하고 내 시험대로 복사(`harness/verifycopy/` · lib.py 의 SNAP/OUT/REL 만 바꿈 · `SK_REL` 로 뮤턴트 빌드 지정).

## 후임 실측(최종 코드 f3252d15 · 2026-11-12 01:3x~02:37)
### 고치기 전/후 — 출력 폭주(seat_flood_tests · 204,000,011 바이트 · 디버그 빌드)
| 회차 | 받은 바이트 | 유실 | 순서 어긋남 | 시간 | cysd RSS 최고 | seatkeep RSS 최고 | 좌석 |
|---|---|---|---|---|---|---|---|
| 켬 · 고치기 전(HEAD f4b9b6ab 코드) | 9,589,170 | 194,410,841 | 3 | 3.26초 | 116.6MB | 22.5MB | 생존 |
| 켬 · 큐 4MiB(첫 구현) | 204,000,011 | 0 | 0 | 73.06초 | 230.2MB | 18.8MB | 생존 |
| 켬 · 큐 256KiB(최종) | 204,000,011 | 0 | 0 | 73.72초 | 246.4MB | 13.3MB | 생존 |
| 끔(같은 날) | 204,000,011 | 0 | 0 | 56.89초 | 267.1MB | — | 생존 |
- 릴리스 실물 cysd(t3rate.py · 같은 204MB): 끔 4.83·5.11초(42.2·39.9MB/s) / 켬 5.61·5.81초(36.4·35.1MB/s) = 켬 약 14% 느림 · 4회 모두 화면 끝 2,000,000 + FLOODDONE · cysd 출력 구멍 줄 0 · cysd RSS 최고 끔 453~457MB / 켬 439~446MB · seatkeep 10~11MB.
### 시험 ②③ + 직접 PTY 대조(seatkeep 단독 t3bound.py · 실물 cysd t3stop.py · 릴리스)
| 경우 | 멈춘 동안 자식 | 유실 | 내보냄 | 재개 지연 | 끝까지 받음 |
|---|---|---|---|---|---|
| 실물 cysd SIGSTOP 15초 → SIGCONT(②) | 멈춤 | 0(구멍 줄 0 · 화면 끝 1,000,000) | 0(write_stalled·control_queue_full 0) | 13.3~18.3ms | 예 · 좌석·seatkeep·cysd 생존 |
| seatkeep 조종자 종속 · 조종자 15초 안 읽음 | 멈춤 | 0 | 0 | 7~20ms(4MiB 때 110ms) | 예 |
| 인자 없음(③ 대조군 = T2) | 안 멈춤 | 8.08~10.86MB | write_stalled | — | 아니오(내보내짐) |
| 직접 PTY(seatkeep 없음) | 멈춤 | 0 | — | 0.2~1.1ms | 예 |
| 첫 조종자 3초 늦게 · 조종자 종속 | 붙기 전 멈춤(진행 10,200 고정) | 0 | 0 | — | 예 |
| 첫 조종자 3초 늦게 · 인자 없음 | 안 멈춤 | 29.55MB(꼬리 1MiB 밖) | — | — | — |
- 역압 중 ^C(읽기 멈춘 채 INPUT ^C): 자식 끝나기까지 조종자 종속 607~637ms / 직접 PTY 612~644ms(같음 — 자식에 닿음). ^C 뒤 조종자에게 더 온 바이트: 직접 PTY 0(커널이 ^C 때 출력 큐 비움) / 조종자 종속 4MiB 큐 3.89~3.93MB → 256KiB 큐 250~252KB.
### 전체 시험(f3252d15)
- 노브 끔 cysd 전체: 3242 통과 · 2 실패(native_publication 2 = 기준선 a48d36e1 과 같음) · 17 무시 · rc 101(567.7초).
- 노브 켬 cysd 전체: 3240 통과 · 4 실패 · 17 무시 · rc 101 — native_publication 2(기준선) + b3_status_usage… · settle_hold_denies…(뮤턴트 작업과 동시 실행 회차 · 따로 3회 = 3/3 초록). b3 실패 사유 = 「seatkeep 이 붙기 전에 끝남 rc 5」 + seatkeep stderr `spawn: No such file or directory` — PLAUSIBLE: 같은 시험 프로세스의 다른 시험들이 HOME 을 프로세스 전체로 바꾸고 지움(handlers.rs set_var("HOME") 12곳) → 좌석 작업 폴더 경합. 직접 PTY 도 같은 부류 · 미확정이라 안 고침.
- seatkeep 단위 33/33(T2 27 + 전임 3 + 후임 3: bound_send_output_never_goes_behind · bound_reads_only_tail_room_before_first_controller · bound_reader_waits_at_cap_and_wakes_below_half).
- T2 `t2.py all`(인자 없는 seatkeep = T2 동작): 판정 48행 · 실패 0 · rc 0(전임 회차는 시험대 결과 폴더 부재로 rc 1 — 폴더 만들고 다시 돌림).
- M09 결정적 시험(reap_marks_before_reaping): 동시 빌드 부하(rustc 2~5 · load 약 11) 아래 10/10.
- 좌석 수명(t3life · 릴리스): 켬 SIGKILL 6/6(91~384ms) · SIGTERM 6/6(160~260ms) — 사유 controller_lost ×12 · 등록부 ended_controller_lost / 끔 SIGKILL 6/6 · SIGTERM 6/6 = 24/24.
- 좌석 100개 만들고 닫기(t3misc 고친 판 · 켬): 닫기 실패 0 · seatkeep 잔존 0 · 남는 파일 300(.json·.log·.lock 각 100) · 105,372 바이트 · .sock 0 · .exit 0 / 끔: 0. 40좌석 동시 생성·동시 닫기: 켬 1.25초/1.72초 · 끔 0.72초/1.10초 · 실패 0 · 시간 초과 0(교착 0).
- A13 = 아래 「A13」 표(판정선 개정 뒤 다시 잼).
### A13(master#18c2e66e 결정 A · 판정선 개정 02:38 — 「40좌석 RSS ≤ 320MB」 → **40좌석 seatkeep 물리 점유 합 ≤ 160MB** · 유휴 CPU ≤ 2% 불변 · 좌석당 RSS > 9MB = 경고(판정 아님))
- 측정 명령: `python3 ~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t3/harness/t3a13.py <target/release> <on|off> 1 5 20 40`(격리 cysd · 합성 좌석 seat.py · quiet = 좌석당 5초에 1줄 / noisy = 50ms 간격 약 215B).
- 물리 점유 = `proc_pid_rusage(pid, RUSAGE_INFO_V2)` 의 `ri_phys_footprint`(시험대 `t2copy/harness/a13.py` `footprint_mb` · 활성 상태 모니터 「메모리」 열과 같은 값) · seatkeep 칸 = 등록부 `seatkeep/*.json` 중 phase committed 이고 살아 있는 pid **전부(40좌석 = 40개)의 합** · 1초 표본 20초 창에서 그 합의 최댓값. RSS = `ps -o rss=` 같은 방식 합. cysd 칸 = cysd 1개의 같은 창 최댓값. CPU = 20초 창 누적 CPU 시간 차 ÷ 경과.
| 노브 · 부하 · 좌석 | seatkeep RSS 합 | seatkeep 물리 점유 합 | 좌석당 RSS / 물리 점유 | seatkeep CPU | 스레드 | cysd RSS | cysd 물리 점유 | cysd CPU |
|---|---|---|---|---|---|---|---|---|
| 켬 quiet 1 | 8.1 | 3.2 | 8.11 / 3.22 | 0.0% | 7 | 41.8 | 9.2 | 0.38% |
| 켬 quiet 5 | 40.4 | 16.0 | 8.08 / 3.20 | 0.0% | 35 | 43.5 | 10.9 | 0.30% |
| 켬 quiet 20 | 161.3 | 63.5 | 8.07 / 3.18 | 0.0% | 140 | 52.0 | 19.4 | 0.58% |
| **켬 quiet 40** | 324.4 | **127.6** | 8.11 / 3.19 | **0.0%** | 280 | 58.8 | 26.1 | 0.52% |
| 켬 noisy 1 | 8.2 | 3.3 | 8.22 / 3.28 | 0.0% | 7 | 44.4 | 11.8 | 0.34% |
| 켬 noisy 5 | 40.9 | 16.4 | 8.18 / 3.28 | 0.0% | 35 | 50.8 | 17.8 | 0.58% |
| 켬 noisy 20 | 163.8 | 66.0 | 8.19 / 3.30 | 0.20% | 140 | 79.2 | 42.6 | 1.57% |
| **켬 noisy 40** | 327.8 | **132.9** | 8.20 / 3.32 | 0.68% | 280 | 119.5 | 86.9 | 2.71% |
| 끔 quiet 1·5·20·40 | — | — | — | — | — | 42.2·43.7·49.9·56.4 | 9.6·11.1·17.3·**23.8** | 0.53·0.43·0.48·0.78% |
| 끔 noisy 1·5·20·40 | — | — | — | — | — | 43.4·49.3·75.6·112.7 | 10.7·16.0·42.7·**80.1** | 0.54·0.82·1.64·2.46% |
(단위 MB · 2026-11-12 02:39~02:50 · 릴리스 · 최종 코드 f3252d15)
- 판정: 40좌석 물리 점유 합 127.6MB(quiet) · 132.9MB(noisy) ≤ 160MB = **통과** · 유휴(quiet) CPU 0.0% ≤ 2% = **통과** · 좌석당 RSS 8.07~8.22MB < 9MB = 경고 없음.
- 비례(조건 ⑵): 좌석당 물리 점유 1→5→20→40 = quiet 3.22→3.20→3.18→3.19 · noisy 3.28→3.28→3.30→3.32MB — 좌석 수가 늘어도 좌석당 값이 늘지 않음(noisy 1→40 +0.04MB).
- cysd 쪽 증가분(조건 ⑷): 40좌석 cysd 물리 점유 켬 − 끔 = quiet 26.1 − 23.8 = **+2.3MB** · noisy 86.9 − 80.1 = **+6.8MB**(각 1회 · 잡음 폭 미측정). 노브 켬 40좌석 기기 부담 합(seatkeep + cysd 증가분) = quiet 약 129.9MB · noisy 약 139.7MB.
- 근거의 약한 곳(조건 ⑶): 「RSS 는 공용 라이브러리 페이지를 프로세스마다 다시 센다」의 직접 관측 = vmmap **표본 1**(seatkeep 1개 · 조종자 없음 · RSS 6.5MB 중 물리 점유 1.86MB · 스레드 5개 스택 상주 합 144KB). 40개 전부의 vmmap 은 안 함. 각 칸은 1회 측정(반복 없음).
- 이전 RSS 값(판정선 개정 전 같은 코드 02:22): quiet 40 = 323.7 · noisy 40 = 327.4(그때 판정선 320MB 초과 → 【결정필요】 02:38 → master#18c2e66e 결정 A).
### 뮤턴트(t3mutants2.py · 별도 git 작업트리 · 기준 회차 14종 전부 초록 확인 뒤)
| 뮤턴트 | 잡은 시험 | 놓친 시험 |
|---|---|---|
| T1~T9 · M09(전임 방어 줄 10) | 각 해당 시험(10/10 잡음) | — |
| M1 조종자 종속에서 밀림 갈래 다시 열기 | 단위 bound_send_output… | bound · flood_on(256KiB 역압이 큐를 4MiB 아래로 묶어 이 줄에 닿지 않음 = 겹 방어) |
| M2 역압 기다림 빼기 | bound(자식 안 멈춤 · 붙기 전 유실 10.79MB) · 실물 cysd stop(자식 안 멈춤) | flood_on(큐가 끝없이 커질 뿐 유실은 없음) |
| M3 조종자 종속에도 쓰기 기한 | bound(write_stalled) · stop(좌석 사망 · controller_lost) | — |
| M4 첫 조종자 전 꼬리 칸 제한 빼기 | 단위 · late_bound(유실 29.55MB) | — |
| M5 깨우기 빼기 | 단위 · bound(멈춘 채 135초 시간 초과) | — |
| M7 cysd 가 인자 안 줌 | stop(자식 안 멈춤 · write_stalled) · life(좌석 생존 = HUP 없음) | — |
| M8 끊김 종료 빼기 | life(좌석 생존) | — |
= 17/17 잡음(전임 표는 build.rs 「git 인덱스 부재」로 10/10 빌드 실패였음).

## 지시 없이 내린 판단
1. 손잡이 얼굴 = portable-pty `MasterPty`/`Child` 트레이트(필드 타입 불변 · 시험 구역 86곳 무수정) — 메모 §2(master 수용 c125bc97).
2. 운영 직접 접근 5곳(close_auth·handlers·repaint·governance·state)은 본문을 seat_proc 로 옮기고 옛 이름은 한 줄 위임으로 남김.
3. anyhow 직접 의존 승격(MasterPty 오류 타입 이름 필요 · Cargo.lock 1줄).
4. seatkeep 상태 폴더 동시 첫 만들기 경합 고침(T2 코드 · 노브 켬 시험에서 rc 3 재현 · 회귀 시험).
5. SIGNAL `target` 칸이 문자열이 아니거나 null 이면 모르는 값과 같이 거절 · `child_pid ≤ 0` 이면 어떤 신호도 안 보냄(T2 는 killpg(0) = 자기 그룹이 될 수 있었음).
6. cysd 는 RELEASE 를 쓰지 않음(그룹 SIGHUP = 결정 B 와 어긋남 · T6 판 내림 몫).
7. 시험 빌드 한정: seatkeep 상태 폴더 = 짧은 임시 폴더 `cskt-<pid>` · 조종자 잠금 = 그 안 `locks/<해시>.lock`(시험 데몬은 시작 잠금을 안 잡음 · 맥 소켓 104바이트) — 제품 경로(`state_dir` · `socket.with_extension("lock")`)와 다름.
8. 시험 환경 변수 `CYS_SEATKEEP_TEST_COMMIT_DELAY_MS` = `cfg(debug_assertions)`(릴리스 빌드에 문장 없음 · 제거 아님 — T2 시험대가 디버그 빌드로 씀).
9.(후임) 조종자 종속 모드 큐 상한 = `BOUND_QUEUE_BYTES` 256KiB(인자 없는 모드의 4MiB 와 따로) — 근거 = ^C 뒤 바이트 3.9MB→252KB · 재개 지연 110ms→7~20ms · 처리량 같음(위 표). 【중간】 01:46 에 알림.
10.(후임) 첫 조종자 전에도 역압: 꼬리의 남은 칸만큼만 읽고 꼬리가 차면 멈춤(cysd 기동~WELCOME 사이에 1MiB 넘게 쏟는 자식의 앞부분 유실 방지 · 시험 late-bound).
11.(후임) 붙을 때 따로 깨우는 줄은 넣지 않음 — 첫 프레임(WELCOME)을 쓴 쓰기 스레드의 `wake_readers` 가 깨움(넣었다가 뺌 · M5 가 깨우기 길 전체를 잡음).
12.(후임) 옛 인자 이름 `--end-on-controller-loss` 는 별칭으로 남기지 않음(바꿈 · 모르는 인자 = rc 2) — 쓰는 곳 cysd 1곳뿐(grep).
13.(후임) 전임 시험대 고침: t3misc 닫기 인자(`--surface N` → `surface:N` 위치 인자 · 시간 초과 셈) · t2copy/results 폴더 만듦 · 뮤턴트는 rsync 사본 대신 git 작업트리(`git worktree add --detach /private/tmp/sk3mut-wt` · 끝나고 제거함).
14.(후임 2회차) D1 시험 설계: 노브 켬 = 비차단 자식(「1초 진척 없음」까지 쓰고 끝남 · 띠 없음) · 노브 끔 = **막히는 256KiB 폭발 자식 + `read()` 안에서 SIGSTOP 한 cat 대역**(cysd 직접 읽기 스레드의 대역 · SIGCONT 뒤 그 대역이 EOF 까지 읽음). 까닭 = 비차단 자식은 직접 PTY 에서도 1,024 를 잃음(관측 2/2) → 차이는 「막히기 전까지 쓸 수 있는 양」이라 그것을 단언.
15.(후임 2회차) D2 부모 판정 = getppid 비교(kqueue 아님 · 간격 100ms = supervise 주기) · 기동 때 이미 1 이면 잃음으로 봄(0ms 시점에 첫 줄 전 cysd 가 죽어 놓친 것을 실측으로 찾음).
16.(후임 2회차) D7 새 끝 코드 rc 7(작업 폴더 사라짐) — cysd 문구 목록에 추가.
17.(후임 2회차) D3 = attach 를 `greet()` 로 쪼갬(검증 MA 패치 문자열은 바뀐 줄에 맞춰 같은 뜻으로 다시 씀 — 뮤턴트 표 「MA(검증)」).
18.(후임 2회차) D4 예외 = `state.rs` `spawned.child`/`spawned.master`(손잡이 결과를 Surface 로 옮기는 자리) · 넘기는 머리에 가져다 쓴 `probe_child(` 포함.
19.(후임 2회차) D1 기제 확인용 받는 쪽 실험 패치 1회(커밋 안 함 · 되돌림 확인).

## 확인 못 한 것 · 남은 것(후임 갱신 — 아래 전임 줄 중 다시 잰 것은 위 「후임 실측」이 정본)
- (후임) cysd 쪽 seatkeep 연결 채널(`OUT_QUEUE_CHUNKS` 64조각 × 최대 16KiB ≈ 1MiB)도 ^C 뒤 화면에 흐를 수 있음 — PLAUSIBLE · 미실측(seatkeep 쪽 252KB 만 잼).
- (후임) 켬이 끔보다 느림: 릴리스 약 14% · 디버그 약 28% — 원인 미규명(seatkeep 한 단계 더 · cysd demux→채널 복사 추정).
- (후임) 역압 중 FOREGROUND 질의는 출력 뒤에 줄 서므로 200ms 상한을 넘겨 「모름」이 될 수 있음(인자 없는 모드도 같음) · 입력 수신 확인도 그 뒤 — 미실측.
- (후임) 100좌석 시험의 남은 .json·.log·.lock 300개 = T4 몫(그대로).
- (후임) 이 맥에 T2 시험대(skt2-a13p5·p40)가 13시간 넘게 남긴 seatkeep 약 86개가 살아 있음(남의 것 · 안 건드림 · PTY 69개 사용 중 / 상한 511).
- 윈도우·리눅스 컴파일 = 미실측(그대로).
- (전임 줄 · 이력)
- 노브 켬 **전체** 재실행(f4b9b6ab 이후) · t2 `all`(대조군 = 인자 없는 seatkeep 자식 생존 포함) · A13 1·5·20·40 · 100좌석 잔존 파일 · 40좌석 동시 생성/닫기 · 뮤턴트 표 — 결과 파일 = `seatkeep-t3/results/{t2-all-t3.out,t3a13-on.out,t3misc.out,t3-mutants.tsv}`(돌리는 중 01:24~).
- M09 결정적 시험의 부하 아래 10/10(동시 빌드 중) — 미실행.
- 윈도우·리눅스 컴파일 점검 = 미실측(T2 관측 그대로 · `cfg` 로 가름: seatkeep 경로 = macos 만 · 그 밖 노브 켬 = 생성 실패 + 이유).
- 에이전트 좌석 입력 지연(전경 왕복 낌) 미실측.
- 끝난 좌석 등록부 3파일(.json·.log·.lock) 잔존 = T4 몫(수 측정은 t3misc).
