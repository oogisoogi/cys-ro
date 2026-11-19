# HANDOFF — TICKET=cysr-1116-seatkeep-1119 (좌석 생존 T4 입양 → T5 토큰 이음 · 1.1.16)

- 좌석 = worker-1116seatkeep(surface:2267) · 가지 `feat/1116-seatkeep` ← `integ/1116` dea2e1853 · cwd `/Users/oogisoogi/axdev/.wt/cys-1116-seatkeep` · push 0 · 태그 0 · CI 0 · 라이브 무접촉.
- master 지시: master#19167ab7(브리프 `master/briefs/1116-full/seatkeep.md`) → 【중간보고】 23:24 → master#7065425a(범위 C 단계 매듭 = **T4 입양 + T5 토큰 이음** · 노브 기본 끔 · T4 끝·T5 끝 각각 【확인요청】 + codex 1R · T1 = 다른 좌석 · T6·T7·D1·슬레이브 탐침 = 다음 단계 목록 · ②③ = 다른 좌석) · master#a651807e(부하 공지 = JOBS 4 · 시한 시험 붉으면 부하 낮을 때 단독 재실행 대조).
- 설계 메모 = `docs/seatkeep/T4-DESIGN.md` · TODO = `WORKER_TODO.cysr-1116-seatkeep-1119.md`.

## 1단계 실측(dea2e1853 · 문서만)
- T2·T3 편입됨(c0736dfb1) · 노브 `CYS_SEATKEEP=1` 기본 끔 · `--controller-bound` = cysd 죽으면 좌석도 죽음 · 입양 코드 0 · T1(feat/seatkeep-t1 r5c BLOCK 4) 미편입 · 차용 ② OSC 7501 = 운영 소스 0건 · ③ 가벼운 시작 = MASTER_DIRECTIVE.md:162 그대로(둘 다 목록만 · 다른 좌석).

## 커밋(T4)
| 커밋 | 내용 |
|---|---|
| d32b1c7eb | T4 핵심: seatkeep `--adoptable` · cysd 입양 노브 `CYS_SEATKEEP_ADOPT` · seat_adopt.rs · create_surface_core 입양 갈래 · e2e |
| 7966e3d3f | 기록 없는 산 seatkeep 미결 · T4-DESIGN.md · e2e A5/A16 |
| 4b3a9dccb | e2e 폭주 모드 |
| 01b2f57ae | codex T4 1R BLOCK 처분(차단 3·주요 5·경미 1) — 아래 표 |
| 43eab104a | HANDOFF 첫판 |
| df024d83b | e2e 전사 겹침(transcripts.db)·조종자 없는 동안 출력 상한 판정 — 뮤턴트 M3·M5·M7 을 잡게 |
| 0ed8c5611 | codex T4 2R BLOCK 처분(차단 1·주요 5) — 아래 표 |
| f3f5ca3e3 | HANDOFF 2R 반영 |
| f5ad568cf | codex T4 3R BLOCK 처분(차단 1·주요 2·경미 1) — 아래 표 |
| e20850fae | HANDOFF 3R 반영 |
| dc5bbf00e | codex T4 4R BLOCK 처분(차단 2·주요 1·경미 1) — 아래 표 · **T4 마지막 코드** |

## codex T4 1R(판정 BLOCK · 4b3a9dccb · 판정문 `~/axdev/master/reviews/codex-1116-seatkeep/t4.r1.verdict.md` · 의뢰문 `t4.r1.prompt.md`) 처분
| # | 지적 | 처분(01b2f57ae) | 시험 |
|---|---|---|---|
| 차단1 | 미결 보류가 자동 복원 1곳뿐 → 수동 restore·phoenix 재시도가 작성자 둘 | 미결 좌석 역할 예약(데몬 수명) → `surface.create` 입구 `surface_create_blocked` 거절(forbidden · seat_adopt_reserved) · seatkeep 끝나면 풀림 · 역할 모름 = 역할 있는 생성 전부 거절 + 자동 복원 보류 · 역할 = 기록 → 없으면 seatkeep env `CYS_ROLE`(KERN_PROCARGS2) · 임시본 기록을 자식 기동 전에(못 쓰면 좌석 안 만듦) | 단위 `reservation_*` · e2e `reserve`(같은 역할 rc1·다른 역할 rc0·seatkeep 끝난 뒤 rc0) |
| 차단2 | 위조 기록·가짜 소켓·pid 재사용 | 소켓 = `<dir>/<skid>.sock` · 연결 **뒤** 상대 pid=등록부 pid·출생 시각=판정 값·실행 파일(proc_pidpath)=cysd 옆 cys-seatkeep · 기록에 seatkeep 출생 시각 결박 | e2e `reserve`(다른 경로 cysd → 「실행 파일 ≠」 로 미결) |
| 차단3 | 등록부 읽기 오류 = 죽음 → 산 좌석 파일 삭제 | pid 생존+출생 시각 먼저 · 등록부 없음·오류·해석 실패 + 산 pid = 미결 · 기록만 어긋남 = 미결 | 단위 `registry_missing_or_unreadable_never_kills_a_live_keeper` · `judge_alive_dead_unknown` |
| 주요4 | disc_total 이 미처리 출력 포함 | 새 프레임 PROCESSED(11) — cysd 읽기 얼굴이 read() 재진입마다 처리 완료 오프셋 · seatkeep disc_total = 그 값 · DSR 꼬리 이음 | e2e 폭주(순번 빠짐 0·겹침 0) |
| 주요5 | 기록 동시 쓰기 찢김·퇴행 | 한 잠금 안 스냅샷+고유 임시 파일+rename(0600) | (구조) |
| 주요6 | .exit 미소비 삭제 | `seat.exited_while_away` 발행 뒤 정리 · phase exited 산 seatkeep = 입양 | e2e `exitaway`(rc 143 소비 · 파일 0 · 같은 역할 rc0) |
| 주요7 | reopen 0행 성공 · 실패 되돌림 spawn_failed | 영향 행 확인 · 행 없으면 INSERT · boot_orphan 아니면 PkConflict · 입양 실패 = boot_orphan 로 | (단위 없음 — 아래 남은 것) |
| 주요8 | 크기 흔들기 = 300ms 타이머 | 재생 전부 소비 직후 1회 | e2e(화면 반영) |
| 경미 | 입양 끔 경로 로그 문구 바뀜 | 원복 | — |

## codex T4 2R(판정 BLOCK · df024d83b · 판정문 `t4.r2.verdict.md` · 1R 상태 = 닫힘 4(차단1·차단2·주요5·경미) · 부분 5) 처분(0ed8c5611)
| 지적 | 처분 |
|---|---|
| 차단: 산 pid + 출생 시각 다름 + 등록부 없음/오류 = 죽음 → 산 좌석 파일 삭제 | 지금 그 pid 실행 파일이 cys-seatkeep 이 **아니라는** 양성 증거(proc_pidpath)일 때만 죽음 · 그 밖 미결(start_mismatch_live) · 단위 표 3×3 |
| 주요: PROCESSED 가 읽기 스레드에서 막히는 소켓 쓰기 · 노브 끔 좌석에도 | 입양 연결만(report_processed) · 읽기 얼굴 = 최신값 덮어쓰기 · 좌석마다 송신 스레드(최신값만) · 노브 끔 = 프레임·잠금 0 |
| 주요: DSR 꼬리 덮어씀 | 이전 꼬리 + 화면 전용 조각 → 마지막 3바이트 |
| 주요: 흔들기가 마지막 재생 조각 처리보다 먼저 | 그 조각의 화면·파서·전사 뒤 |
| 주요: .exit 미검증 삭제·중복 | id 확인 · 못 읽음/해석 실패/id 다름 = 무삭제 미결 · 발행 뒤 `.exit.consumed` 표식 → 정리(적어도 한 번 · skid 멱등 키) |
| 주요: reopen PkConflict 뒤 입양 계속 | 입양 실패(예약) · 등록 실패 = 붙은 연결 끊기(`SeatLink::detach`) · 단위 `numbers_reopen_variants` |
## codex T4 3R(판정 BLOCK · 0ed8c5611 · 판정문 `t4.r3.verdict.md` · 앞 지적 닫힘 6 · 부분 5) 처분(f5ad568cf)
| 지적 | 처분 |
|---|---|
| 차단: 기록 pid A ≠ 등록부 pid B · A 죽음 → B 의 산 파일 삭제 | 등록부 pid 가 살아 있고 cys-seatkeep 이 아니라는 증거가 없으면 미결(registry_pid_live) |
| 주요: PROCESSED 송신이 공용 쓰기 잠금 안에서 무기한 write_all | try_lock + 송신 버퍼 남은 자리 ≥ 17바이트일 때만 MSG_DONTWAIT · 못 보내면 50ms 뒤 최신값 · 부분 쓰기 = 연결 끊기 |
| 주요: .exit·표식이 skid 만 공유 | seatkeep 이 .exit 에 pid·start_us 기록 · cysd 가 판정한 세대와 대조(다르면 무삭제 미결) · 표식 = 지문 원자 쓰기 · 다른 파일 다 지운 뒤에만 표식 삭제 · .exit 만 남은 id 도 스캔 |
| 경미: 노브 끔도 처리 상태 잠금 | report_processed 조건 안으로 |
## codex T4 4R(판정 BLOCK · e20850fae · 판정문 `t4.r4.verdict.md` · 3R 지적 닫힘 2(PROCESSED 잠금·경미) · 부분 7) 처분(dc5bbf00e)
| 지적 | 처분 |
|---|---|
| 차단: A 죽음·B 산 → 미결로 바꾸되 예약이 A 를 가리켜 곧 풀림 | 예약·역할(env) = B 세대 · e2e `SKA_FORGE_PID=1 … reserve`(기록 pid 위조 → registry_pid_live · 같은 역할 rc 1 · 다른 역할 rc 0 · B 끝난 뒤 rc 0) |
| 차단: 삭제 전 실제 잠금·소켓 보유자 확인 없음 | seatkeep id 잠금(`<skid>.lock` flock — seatkeep 이 사는 동안 쥔다)을 비차단으로 잡아 정리 끝까지 쥠 · 못 잡으면 무삭제 미결(id_lock_held) · 소켓 접속 확인은 안 함(접속 자체가 seatkeep 기록에 거절 줄을 남겨서 — 잠금이 더 강한 증거) |
| 주요: 표식 = pid:start 뿐 · 부분 정리 뒤 스캔 앵커 소실 | 지문 = 세대 + 종료 기록 바이트 sha256 · 정리 순서 기록·등록부·소켓·잠금 → 종료 기록 → 표식 · 스캔 앵커에 .sock·.lock·.exit.consumed |
| 경미: 노브 끔 종료 기록에도 세대 칸 | 입양 모드만 |
- **codex 5R = master 대기열**(master#d111188d · codex 5h 한도 리셋 06:29 · 범위 = `git diff e20850fae..dc5bbf00e -- src/` · 의뢰문 = `t4.r4.prompt.md` 를 「4R 처분 확인」 으로 바꿔 쓰면 됨).
- 수렴 관찰: 1R→4R 지적의 축이 「같은 사용자 파일 위조·pid 재사용 조합」 으로 깊어지는 중(신뢰 경계 = 같은 사용자 · master 11-11). 4R 처분의 id 잠금이 그 축의 가장 강한 증거라 5R 에서 닫힐 것으로 보나 **확신도 중**.

## 뮤턴트(분리 작업트리 `/private/tmp/skmut1119` · 한 줄씩 → 빌드 → e2e → git checkout · 러너 = scratchpad `mut.py` · 결과 `e2e/mutants*.out`)
| 뮤턴트 | 바꾼 줄 | e2e | 결과 |
|---|---|---|---|
| M1 | seatkeep 인자 늘 --controller-bound | adopt | 붉음(좌석 죽음) |
| M2 | adopt_on_boot 늘 반환 | adopt | 붉음(목록 없음 · 정리 뒤 좌석 남음) |
| M3 | 화면 전용 재생 끔 | adopt | 처음 초록 → 전사 겹침 판정 추가 뒤 붉음(같은 SEQ 7건) |
| M4 | surface_create_blocked 늘 None | reserve | 붉음(같은 역할 rc 0) |
| M5 | 조종자 없는 동안 역압 끔 | adopt 폭주(60KB 줄) | 처음 초록(4KB 줄은 꼬리를 못 넘김) → 60KB·상한 판정 뒤 붉음(끊긴 동안 112줄 = 6.7MB) |
| M7 | PROCESSED 안 보냄 | adopt | 처음 초록 → 전사 겹침 판정 뒤 붉음(7건) |
| M6 | adopt_connect 실행 파일 검사 끔 | — | **시험 없음**(가짜 서버 흉내 시험대 미작성 · reserve 는 seatkeep 쪽 검사가 먼저 막아 가르지 못함) |
- 뮤턴트는 0ed8c5611(2R 처분) **전** 코드에 대해 돌림 — 2R 처분 뒤 재실행 = 남은 것.

## 시험
- seatkeep 단위: 49/49(기준선 49 · 고침 전·후 모두).
- seat_adopt 단위: 8/8(+ record_start_mismatch 단언).
- 격리 HOME 실물(`scripts/seatkeep-adopt-e2e.py` · 결과 = scratchpad `e2e/*.jsonl`):
  - adopt 6회(d32b1c7eb): 좌석-종료 21건 전부 생존 · 역할 · 끊긴 동안 출력 화면 · 입력 왕복 · 정리 뒤 seatkeep·좌석 0
  - 대조군 bound·direct: SIGNAL 1(SIGHUP)로 죽음(시험이 가른다)
  - 폭주(4KB 줄·1ms): 끊긴 동안 118~137줄에서 역압 정지 · 재부착 뒤 3000줄 순번 빠짐 0·겹침 0 · A16 교체 줄 3/3 · 입양 전 RPC 0
  - 처분 뒤(01b2f57ae 직전 빌드): adopt 3회 교체 6/6 · 폭주 2회 3/3 · reserve · exitaway 통과
- cysd 전체(노브 끔 · d32b1c7eb · 스레드 4 · load 20~38): 3330 통과 · 7 실패 · 17 무시 — 소스 핀 1(내 변경 · 01b2f57ae 에서 고침) · seatkeep 핸드셰이크 3초 시한 3 · 10초 시한 1 · PoisonError 2. 시한 계열 = 부하 낮을 때 단독 재실행 대조 필요(공지 a651807e).
- cysd 전체(01b2f57ae · load 높음 · 2066초): 3327 통과 · 15 실패 · 17 무시 — boot_supervisor c6c·h5 5 · channels c6b·h3 6 · seatkeep 핸드셰이크 4 (전부 시한·전달 계수). **두 실행의 실패 22개 이름 + 같은 접두 = 37개를 부하 6 에서 단독 재실행 = 37/37 통과**(`tests/head2-rerun.out`).
- **기준선 dea2e1853 전체**(load 10 → · 1014초): 3332 통과 · **2 실패**(`state::tests::dbg_r12_seat_profile_wired_before_agent_exec` · `state::tests::dbg_r12_update_lane_restore_seat_gets_link_before_exec`) · 17 무시 · 계 3351.
- **HEAD f5ad568cf 전체**(load 10 · 1006초): 3341 통과 · 3 실패(seatkeep_input_ack ×2 · seatkeep_stalled_consumer_does_not_block_close — 핸드셰이크 3초 시한) · 17 무시 · 계 3361(= 기준선 3351 + 새 10). 기준선의 dbg_r12 2건은 여기선 통과. **3건 포함 seatkeep_ 5개를 load 4.8 · 스레드 1 단독 재실행(dc5bbf00e) = 5/5 통과**(`tests/r4-seatkeep-only.out`). (앞 head3 실행 = 3R 고치는 도중 컴파일이라 무효 · 내 작업트리 cargo 1개만 pid 로 끝냄.)
- 4R 처분 뒤(dc5bbf00e): seat_adopt 10/10 · seatkeep 49/49 · e2e adopt 2(교체 3/3 · 전사 겹침 0) · reserve · reserve+위조 pid · exitaway 통과.
- 기준선 대비 요약: 기준선 3332/2 실패 → HEAD 3341/3 실패(시한 계열 · 단독 재실행 초록). 내 변경이 새로 붉힌 시험 = 0(소스 핀 1건은 01b2f57ae 에서 고침).
- 3R 처분 뒤(f5ad568cf): seat_adopt 10/10 · seatkeep 49/49 · e2e adopt 2(교체 3/3 · 전사 겹침 0) · reserve · exitaway · 큰 폭주(60KB 줄 · 출력 상한 OK) 통과.
- 2R 처분 뒤(0ed8c5611): seat_adopt 9/9 · e2e adopt 2회(교체 3/3 · 전사 겹침 0 · 출력 상한 OK) · reserve · exitaway 통과.
- 관측(기존 동작 추정 · 원인 미확인): cysd SIGKILL 마다 전사(transcripts.db)에서 좌석당 SEQ 약 3줄 빠짐(폭주 시험은 0) — PROCESSED 는 「파서·전사 대기열에 넣음」까지라 전사 쓰기 스레드가 디스크에 쓰기 전 줄은 잃는다고 봄(직접 PTY 의 SIGKILL 도 같은 대기열을 잃음).

## 남은 것(T4) · 다음 첫 행동
0. codex 5R(master 대기열) 판정 → 닫힘이면 T4 끝 · 아니면 처분(후임).
1. (끝남) 기준선·HEAD 전체 대조 · 시한 계열 단독 재실행.
2. 노브 켬 스크립트 `SEATKEEP_TEST_THREADS=1 scripts/seatkeep-knob-on-tests.sh accounts::` · `seat_proc::` · 입양 켬 상태 cysd 시험(CYS_SEATKEEP_ADOPT=1 붙인 같은 스크립트).
3. CI 팩 단계(`.github/workflows/ci-branch.yml` · 떼어 둔 스크립트 `~/axdev/.wt/cys-1116-integ-cifix-evidence/step-mac.sh`) 1회.
4. 뮤턴트 2R 처분 뒤 재실행(`python3 -I <scratchpad>/mut.py` · 작업트리 /private/tmp/skmut1119 를 HEAD 로 `git -C … checkout --detach <HEAD>` 뒤) · M6 시험대(가짜 소켓 서버) 작성.
5. codex 2R(BLOCK 처분 확인 · 범위 4b3a9dccb..HEAD) → 【확인요청】 T4.
6. 그다음 T5(아래).

## T5 설계 실마리(조사만 · 코드 0)
- 좌석 토큰 = `"{started_at:x}-{cysd pid:x}.{128bit}"`(state.rs `mint_seat_token`) · `Surface.seat_token` 은 생성 때 1회·불변 · claim 은 대상 좌석 토큰과 상수시간 일치면 인가(handlers.rs ~10024) · 불일치+같은 세대 = 시끄러운 거절 · 불일치+다른 세대 = 체인 폴백.
- seatkeep 은 cysd 가 준 env 를 그대로 자식에 넘기므로 **자기 env 에 같은 토큰을 이미 쥔다** → 디스크에 쓰지 않고: seatkeep 이 시작 때 `CYS_SEAT_TOKEN` 을 메모리로 읽어 두고, 인증된 조종자의 TOKEN_GET 에만 TOKEN_IS 로 답(확장 프레임). 새 cysd = 토큰 접두 세대가 skid 의 (pid·started_at)과 맞는지 확인 → `Surface.seat_token = Some(옛 토큰)` · 「입양 세대 집합」(Daemon 필드)에 넣어 `seat_token_same_generation` 판정을 현 세대 ∪ 입양 세대로 넓힘(A8ⓓ′: 다른 좌석이 그 토큰을 쓰면 시끄러운 거절).

## 다음 단계 목록(순서 · 이 좌석 다음 · 지금 안 함)
T6 rotate·업데이터(계획 교체 = 화면 저장+이어받기 · 사전 실행 · RELEASE · 판 처리 · 기록 없는 산 seatkeep 정리 규칙) → T7 윈도우 → D1 꼬리 ≤1KiB 유실 · 슬레이브 보유 탐침 → 노브 기본 켬 판단(T1·T5·D1 닫힌 뒤 근거 숫자).

## 지시 없이 내린 판단
1. 노브를 하나 더 둠(`CYS_SEATKEEP_ADOPT`) — `CYS_SEATKEEP=1` 만 켠 종전(T3 종속 모드)을 그대로 남기려고.
2. 미결 예약 거절 코드 = 기존 `forbidden` 재사용(신설 코드는 구 CLI 가 rc 3 미도달로 오진한다는 handlers.rs 주석 선례).
3. 역할 모르는 미결 = 역할 있는 생성 전부 거절(보수) — 기록·env 둘 다 못 읽는 경우뿐.
4. 입양 직후 큐 3초 멈춤 = A7 관문의 최소 대역(screen_exact 규칙 = 미구현).
5. 시험대 CYS_NO_AUTOSTART — 데몬 없는 틈에 `cys` 가 노브 없는 cysd 를 띄워 잠금을 먼저 잡는 경합을 실측으로 찾음(reserve 첫 실행 rc 1).

## 원작자 파일 변경 줄(데몬 변경 허용 · 브리프)
- state.rs: create_surface_with_env 감싸개 + create_surface_core(입양 갈래 · 임시본 기록) · adopt_display · DisplayGrant.adopt · replay_screen_only · 읽기 스레드 재생 나눔·흔들기·DSR 잇기 · EOF forget_surface
- handlers.rs: surface.create 예약 관문 1블록 · governance.rs: persist_topology 첫머리 record_all 1줄 · recall.rs: surface_numbers_reopen · main.rs: mod · adopt_on_boot 호출 · 자동 복원 보류 블록
- (줄 번호 = `git diff dea2e1853..HEAD --stat` · 확인요청 때 표로)
