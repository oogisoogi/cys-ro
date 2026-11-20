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

## 후임(worker-1116seatkeep2 · surface:2276 · 계정2 · master#25218fb5 · 브리프 `master/briefs/1116-full/seatkeep2.md`) 델타 — 11-20 02:43~
### 커밋
| 커밋 | 내용 |
|---|---|
| b953e900a | **T4 실결함 고침** — 입양 모드 연결 끝 = seatkeep 끝내기(seat_proc.rs `demux` 끝 · `end_adoptable_keeper` · `detached` 표시) + M6 시험대(`adopt_connect_refuses_fake_server_that_is_not_seatkeep_exe`) |
| ddae58a5f | e2e 터짐 모드 `SKA_BURST=1` + 끊긴 동안 바이트 = 줄마다 실제 길이 — 뮤턴트 M5 판별 복구 |

### 이월 ④ 전사 SEQ 유실 — 이 티켓 탓 아님(대조군 먼저 · 원인 이름은 그 뒤)
- 계측 = scratchpad `txloss.py`(격리 HOME·격리 소켓 · 좌석 1개 50ms 마다 SEQ · 3초 → read-screen(죽기 전 화면) → cysd SIGKILL → transcripts.db 판독 · 빠진 SEQ 마다 좌석 기록 출력 시각 − SIGKILL 시각).
- 결과(앞 좌석 5회 + 내 재현 2회 · 갈래마다): 기준선 dea2e1853 노브 끔 = 4·5·5·5·8 · 7·7줄 · HEAD 노브 끔 = 0·5·5·6·7 · 5·6줄 · HEAD 입양 = 5·5·5·6·6 · 1·5줄. 빠진 줄 **전부** 죽기 전 화면엔 있었음(옛 cysd 가 처리함) · 나이 전부 SIGKILL 직전 −1.0~0초 · 겹침 0.
- 원인(코드 대조): 전사 쓰기 스레드가 첫 줄 뒤 **1초 또는 200건**을 메모리에 모아 한 번에 COMMIT(`src/bin/cysd/recall.rs:130-149`) → SIGKILL 이 그 묶음(채널+버퍼)을 잃음. 직접 PTY 도 같음. 입양은 PROCESSED(처리 완료 = 전사 대기열에 넣음)까지만 보장하므로 이 구간을 재생하지 않는다.
- 폭주(60KB 줄)·터짐 e2e 의 「전사 누락」 15~29줄도 같은 계급(대조군·뮤턴트 같은 크기) → e2e 판정에서 「누락」 칸은 M 판별 근거로 쓰지 않음(겹침 칸만).
- 📌 = 별도 항목 후보(D1 꼬리 유실 근처): 「SIGKILL 시 전사 최대 1초 유실」 — 고치는 길 = 입양 모드에서 PROCESSED 를 「전사 COMMIT 뒤」로 늦추기(재생이 그 구간을 다시 줌 · 화면 중복은 화면 전용 재생 경계로 처리) 또는 COMMIT 주기 단축. 이 티켓 범위 밖(기존 동작).

### 이월 ① 노브 켬 스크립트 — 실결함 1건
- `SEATKEEP_TEST_THREADS=1 scripts/seatkeep-knob-on-tests.sh accounts:: -- seat_proc::`(격리 env -i): 노브 켬(입양 끔) 178/178 · **입양 켬(CYS_SEATKEEP_ADOPT=1) 177/1** — `seat_proc::tests::seatkeep_input_ack_stall_ends_seat_when_consumer_never_resumes`(seatkeep 이 상한 만료 뒤 5초 안에 안 끝남).
- 원인: `abort_link`(입력 확인 상한) · 처리 오프셋 부분 쓰기 차단(seat_proc.rs `processed` 송신) · seatkeep 쪽 끊김은 모두 「끊기면 seatkeep 이 controller_lost 로 끝난다」 전제 → `--adoptable` 은 끊겨도 안 끝남 → cysd 는 좌석을 `seatkeep_disconnected` 로 접었는데 seatkeep·좌석이 고아로 삶 · 막힌 입력이 나중에 적용될 수 있음 · 띄운 seatkeep 회수(`k.wait`) 영구 대기(연결 스레드 누수).
- 고침(b953e900a · 데몬 변경 허용 범위 · seat_proc.rs): `demux` 끝에서 입양 모드 ∧ EXITED 못 받음 ∧ `detach` 아님 → 그 pid 출생 시각 = 연결의 seatkeep 출생 시각일 때만 SIGTERM(seatkeep 은 처리기 없음 = 종료 → PTY 마스터 닫힘 → 좌석 SIGHUP = controller_lost 와 같은 끝). `detach`(입양 등록 실패 — 다음 조종자용으로 살려 둠)는 표시(`detached`)로 제외.
- 고친 뒤: 입양 켬 179/179 · 노브 켬 179/179 · 노브 끔 `seat_proc::` 21/21(+1 = M6 시험). ackstall 입양 켬 = 쓰기 TimedOut 10.09초 · seatkeep·좌석 생존 false · 종료 seatkeep_disconnected.
- e2e(b953e900a 빌드): adopt(교체 1/1 · 겹침 0 · 정리 뒤 0) · reserve(같은 역할 rc 1 · 다른 역할 rc 0 · 풀린 뒤 rc 0) · reserve+위조 pid(registry_pid_live) · exitaway(rc 143 소비 · dead keeper_gone) 통과.

### 이월 ③ 뮤턴트(작업트리 /private/tmp/skmut1119 = b953e900a · 러너 scratchpad `mut.py` · 결과 `e2e/mutants-b953.out`)
| 뮤턴트 | 시험 | 결과 |
|---|---|---|
| M1 늘 --controller-bound | e2e adopt | 붉음(takeovers 0/1 · 좌석 죽음) |
| M2 adopt_on_boot 늘 반환 | e2e adopt | 붉음(takeovers 0 · 정리 뒤 seatkeep·좌석 1) |
| M3 화면 전용 재생 끔 | e2e adopt | 붉음(전사 겹침 7) |
| M4 예약 관문 끔 | e2e reserve | 붉음(같은 역할 rc 0) |
| M5 조종자 없는 동안 역압 끔 | e2e adopt 폭주 → **초록(판별 못 함)** → 터짐(SKA_BURST) | 붉음(끊긴 동안 9,482,370 바이트 · 대조군 1,020,270·1,020,255) |
| M6 adopt_connect 실행 파일 검사 끔 | 단위 M6 시험대(새) | 붉음(rc 101 — 가짜 서버가 입양돼 연결 끝에서 「seatkeep」 = 시험 프로세스 자신에 SIGTERM · 고친 코드가 끝내기 전 출생 시각만 보므로 실행 파일 검사가 그 앞의 유일한 막이라는 뜻) |
| M7 PROCESSED 안 보냄 | e2e adopt | 붉음(전사 겹침 9) |
| M8 연결 끝 seatkeep 끝내기 끔(새 고침) | 입양 켬 ackstall 단위 | 붉음(seatkeep·좌석 생존 true) |
- M5 폭주가 못 가른 이유: 옛 cysd 가 밀린 채 죽으면 seatkeep 읽기 스레드가 큐 자리 대기(`wait_for_room` · seatkeep main.rs 1058~)에 잠들고, 끊김은 그 대기를 깨우지 않는다(깨우는 곳 = 쓰기 스레드 `wake_readers` 1곳) → 끊긴 동안 출력 0 · 역압 줄에 닿지 않음. 결함 아님(유실 0 · 새 조종자가 붙으면 깨움). 앞 좌석의 「M5 붉음」은 2R 처분 전 코드 기준.

### 이월 ② ci-branch 팩 단계(이 가지 yml 996행 스텝 원문을 다시 떼어 · 통합 트리 떼어 둔 것과 본문 같음 · env -i · python 3.12.13 = 앱 번들 런타임 · RUNNER_TEMP 짧은 폴더)
- 원문 1회(뮤턴트 빌드와 겹침 · load 6~10): rc 1 · 382초 · `test_session_start_hook` 13a·13b·13c 3 FAIL 에서 멈춤(원문은 첫 실패에서 멈춘다). 이 가지의 `cysjavis-pack` 변경 = 0줄. 같은 env 단독 실행: HEAD 2/2 · 기준선 트리 2/2 통과 → 부하 흔들림.
- 멈추지 않는 사본(같은 본문 185행에 `|| echo LANE-FAIL` 1줄 · 통합 좌석 step-mack 과 같은 차이) 전량: rc 0 · 2991초 · 검체 165개 · LANE-FAIL 6.
  | 검체 | HEAD 단독 | 기준선 트리(dea2e1853) 단독 | 판정 |
  |---|---|---|---|
  | test_hook_r34 | rc 1(RCF-3·NZ-3·DL-1b·WIN-2 = 1초 시한 계열 3.1~3.9초) | rc 1(같은 계열) | 기준선 같음 · 시한(부하) · 통합 증거 lane3-mack 에도 LANE-FAIL |
  | test_pyseal_negative_specimen | rc 2(ⓒ UNMEASURED — PATH 에 in-tree 비번들 python 없음) | rc 2(같음) | 내 실행 환경 탓(측정 불가) · 기준선 같음 |
  | test_owner_desk | rc 1(R8Codex2R flush request_id 0≠1) | rc 1(같은 시험 + R9Codex3R) | 기준선 같음 |
  | test_role_authority | rc 0 | rc 1 | 흔들림 |
  | test_inject_context_role_seat | rc 0(177초) | rc 0(201초) | 흔들림 |
  | test_refl_inject_context_role_canon | rc 0 | rc 0 | 흔들림 |
  - 결론: 이 가지(팩 변경 0)가 새로 붉힌 팩 검체 = 0. 원문 「첫 실패에서 멈춤」 성질 때문에 로컬 원문 1회만으로는 초록을 못 본다(CI 러너 = 부하 낮음).

### 지시 없이 내린 판단(후임)
1. 입양 모드 연결 끝 = seatkeep SIGTERM(SIGKILL 아님) — seatkeep 은 처리기가 없어 같은 결과이고, 나중에 정리 처리기를 달면 그게 돈다. 대상 확인 = 출생 시각만(실행 파일 재확인 안 함 — 연결 때 이미 확인 · 출생 시각이 같으면 같은 프로세스).
2. 끝내기 자리 = `abort_link` 가 아니라 `demux` 끝 한 곳 — 끊김 원인 셋(상한·부분 쓰기·seatkeep 쪽 끊김)을 모두 덮으려고.
3. e2e 「전사 누락」 칸을 뮤턴트 판별에 쓰지 않음(기존 1초 묶음 유실이 섞여서).
4. 쓰이지 않는 시험 보조 함수 `seat_adopt::test_set_pending`(01b2f57ae · 경고 1건) — 손대지 않음(외과적).

### 남은 것(T4) · 다음 첫 행동
0. codex 5R(master 대기열 · 06:29 뒤) — 범위 **e20850fae..ddae58a5f -- src/ scripts/seatkeep-adopt-e2e.py**(b953e900a 포함으로 넓힘 · 03:00 【경고】 보고함) · 판정 오면 master 처분 줄 대로.
1. T5 = `docs/seatkeep/T5-DESIGN.md`(1단계 문서 · 코드 0) → 【중간보고】 → 구현.

## T5 좌석 토큰 이음(후임 · master#f819c8f1 → 중간보고 04:23 → master#9e1379e9 = A안 승인 · 상한 4h · 04:24~05:1x)
### 커밋
| 커밋 | 내용 |
|---|---|
| 63c332520 | 설계 1단계 `docs/seatkeep/T5-DESIGN.md`(§6 = 구현 결과 · 이 커밋 뒤 보탬) |
| 7487a7126 | 구현 — seatkeep WELCOME 칸 인계 · 세대 정합 · 입양 세대 집합 · 판정 넓힘 · 문구 지우기 · 소스 핀 · e2e token 모드 · test_set_pending 제거(master 허락) |
| d2ca1de03 | 실패 갈래 새지 않음 — `adopted_token_or_skip` 사건 시험 · e2e 훑기에 난수·바꾼 토큰 |

### 원작자 파일 변경 줄(T5)
- state.rs: Daemon 필드 `adopted_token_gens`(+ 생성자 1줄) · `create_surface_core` 입양 분해에 `adopt_token` · 입양 갈래 토큰 줄(옛 토큰 + 세대 등록 · CYS_BOOT_GATES=0 = 무토큰) · `Daemon::seat_token_known_generation`(새 impl 블록 · `seat_token_same_generation` 무변).
- handlers.rs: claim 불일치 갈래 판정 1줄(`seat_token_same_generation(&supplied, daemon.started_at)` → `daemon.seat_token_known_generation(&supplied)`) · 시험 2개.
- (원작자 아닌 이 갈래 파일) seat_proc.rs(SeatLink `adopted_token` · `take_adopted_token` · `welcome_without_tokens` · 오류 문구 1줄) · seat_adopt.rs(`AdoptSeat.token` · `adopted_token_or_skip` · `check_adopted_token` · adopt_one 1줄) · cys-seatkeep/main.rs(Keep `seat_token` · `adopt_seat_token` · `welcome_seat`) · 시험 파일 · e2e.

### 시험(격리 env -i · 기준선 dea2e1853 대비)
| 묶음 | 기준선 | HEAD d2ca1de03 |
|---|---|---|
| cysd 전체(스레드 4 · load 7→5 · 1014초) | 3332 통과 · 2 실패(dbg_r12 ×2) · 17 무시 · 계 3351 | **3351 통과 · 0 실패 · 17 무시 · 계 3368**(+17 = T4 10 · M6 1 · T5 6) |
| cys-seatkeep | 49 | 51(+2 T5) |
| 노브 켬 스크립트 accounts::+seat_proc:: | — | 입양 켬 180/180 · 입양 끔 180/180 |
| e2e token ×5(04:3x~05:1x) | — | own rc 0 · 토큰 없음 rc 6 · 난수만 바꿈 token_mismatch · 고아(ppid 1) · 누출 0 — 5/5 |
| e2e 회귀(T5 빌드) | — | adopt · reserve · 위조 pid · exitaway · 터짐(1.02MB) 통과 · bound·direct = 좌석 죽음(대조군 그대로) |
- 부하 공지(master#6e6d4069 · 04:34~04:49 load 20~27): 그 창 안의 판정 = e2e 회귀 9종(전부 기대대로 · 시간 문턱 붉음 0) · 뮤턴트 붉음은 아래처럼 전부 단언 패닉(0.00~0.06초) 또는 대상 칸 하나만 거짓 → 시한 탓 아님.

### 뮤턴트(T5 · /private/tmp/skmut1119 = 7487a7126 · 러너 scratchpad `mut5.py` · 결과 `e2e/mut5.out`)
| 뮤턴트 | 바꾼 곳 | 시험 | 결과 |
|---|---|---|---|
| T1(ⓜ1) | 세대 정합 비교 끔 | check_adopted_token_generation_and_shape | 붉음(단언) |
| T2(ⓜ2) | 입양 세대 집합에 안 넣음 | e2e token `tamper_mismatch` | 붉음(그 칸만 거짓) |
| T3(ⓜ3) | seatkeep 이 모드 무관 env 읽음 | seat_token_only_in_adoptable_mode | 붉음(단언) |
| T4(ⓜ4) | Surface 에 안 붙임 | e2e token `own_rc0` | 붉음(그 칸만 거짓) |
| T5 | 오류 문구 토큰 지우기 끔 | welcome_without_tokens_strips_only_the_token | 붉음 |
| T6 | 재발급 대입 1줄 끼움 | seat_token_is_assigned_only_at_creation(소스 핀) | 붉음 |
| T7 | 판정 = 현 세대만(넓힘 되돌림) | claim_role_adopted_generation_mismatch_is_rejected_loudly | 붉음 |

### 지시 없이 내린 판단(T5)
1. ⓓ′-1 은 단위 대신 e2e(Surface 토큰 불변 · Arc 공유라 시험에서 못 바꿔 끼움 — 일치 갈래 무변).
2. 입양 세대는 좌석이 끝나도 집합에서 안 뺌(설계 2-2 ④).
3. 거절 문구 「동세대 발급분」 안 바꿈(원작자 문구 · 소스 핀 위험) → 📌.
4. `explain-state` 는 이 트리에 없음 → 진단 표면 = list · status --json · topology · 격리 폴더 전체로 훑음.

### 남은 것 · 다음 첫 행동
0. master: 독립 검증 좌석(인증·비밀값 = 고위험) + codex 1R(T5 · 범위 63c332520..d2ca1de03 -- src/ scripts/seatkeep-adopt-e2e.py) · codex T4 5R(e20850fae..ddae58a5f) = 대기열.
1. 판정·처분 줄이 오면 그대로. 그다음 = HANDOFF 「다음 단계 목록」(T6 → T7 → D1 → 노브 기본 켬 판단).

## 독립 검증(2286 · VERDICT = `~/axdev/workers/cysr-1116-seatkeep-verify-1120/VERDICT.md` · 증거 `evidence/`) 처분 — 후임 seatkeep2 매듭(11-20 06:0x · CTX 53%)
- 최종 판정(master#a0097cf2): **T4 BLOCK · T5 ACCEPT · 노브 끔 ACCEPT**.
| # | 처분 | 커밋 · 시험 |
|---|---|---|
| B1 claim-role 우회 · B2 dedup 우회 | **고침** — 예약 판정 한 곳 `seat_adopt::role_grant_blocked` 를 역할 부여 4입구(surface.create · system.claim_role · reclaim_commit · role.restore_released)가 부름 · worker 번호 배정 = `dedup_worker_role_avoiding(…, role_name_reserved)`(정확히 그 이름만 피함) | 282b1e568 · 검증 탐침 그대로 `scripts/seatkeep-reserve-probe.py`(claim rc 0 → rc 7 claim_denied · dedup worker-2 → worker-3) · 뮤턴트 R1·R2 붉음 |
| 빈칸 2(reclaim · restore_released 반례) | **채움** — `seat_adopt::test_reserve_role`(시험 전용 · cfg!(test) 값 분기) · 단위 2(예약 = 거절·상태 불변 · 걷힘 = 성공 대조) | 80d66308b · 뮤턴트 R3·R4 붉음 |
| **M1** 노브 없는 cysd 재기동 → 옛 seatkeep·좌석 영구 고아 + 같은 역할 새 좌석 | **남음(다음 첫 행동)** | — |
| **M2** 미결 굳음 · 역할 모름 미결이 모든 역할 생성 막음 · 조회 표면 없음 | **남음** | — |
| m1 같은 폴더 소켓 둘 = 남의 종료 기록 소비 | **남음**(고친다) | — |
| m2 종속 모드 WELCOME `"disc_total": null` 칸 | **기록 처분(master)**: 「노브 끔 바이트 같음」의 예외 1건 — `CYS_SEATKEEP=1` 만(T3) 일 때 WELCOME 좌석 칸에 `disc_total: null` 이 붙는다 · cysd 는 `as_u64()` = None 으로 읽어 동작 같음 · 두 노브 다 끔 = seatkeep 미사용이라 해당 없음 | — |
| m3 거절 문구 「동세대 발급분」 | **기록**(📌 · 원작자 문구 · 안 바꿈) | — |

### 다음 첫 행동(후임) — M1 → M2 → m1 → T6a 나머지
1. **M1**(master 처분 원문: 「노브 끔 기동에서도 seatkeep 등록부에 산 seatkeep 이 있으면 입양은 안 하되 관리용 종료(신원 확인 → SIGTERM → 확인) + 역할 phoenix 복원(D2 와 같은 길) · 노브 끔 사용자 = 등록부 비어 있어 바이트 같음 시험 유지 · 실측 20초 반례 그대로 붉음→초록」)
   - 자리: `main.rs` 의 `adopt_on_boot` 호출(accept 전) 옆 — 노브 끔이면 `seat_adopt::end_orphans_on_boot`(새 함수): `seatkeep_base(daemon)/seatkeep/*.json` 등록부를 읽어 산 pid 마다 신원 확인(pid 생존 · 출생 시각 = 등록부 `start_us` · `seat_proc::seatkeep_exe_matches(pid) == Some(true)` · id 잠금 `<skid>.lock` 은 seatkeep 이 쥐므로 「못 잡음 = 산 seatkeep」 확인용) → SIGTERM → 5초 안 사라짐 확인(아니면 SIGKILL) → `consume_dead` 와 같은 정리(id 잠금 잡은 뒤 파일 삭제 · `.log` 남김) · 사건 `seat.adopt_skipped{knob_off_orphan_ended}`. 그 뒤 자동 복원(phoenix)이 그 역할을 topology 로 띄움(예약 안 남김).
   - 함께: D2(기록 없는 산 seatkeep) = 같은 관리용 종료 함수를 노브 켬 `adopt_one` 의 `no_record_live_keeper` 갈래에서 부름(T6a 항목이었음 · 같은 길).
   - 주의: 등록부 없는 dir = 즉시 반환(파일 0 · 노브 끔 바이트 같음) · T3 종속(`--controller-bound`) seatkeep 은 부모 상실로 스스로 끝나므로 대상이 사실상 `--adoptable` 뿐 — 그래도 신원 확인 통과한 산 seatkeep 은 모드 무관 끝냄(조종자 없는 좌석 = 고아).
   - 반례 = `python3 -I scripts/seatkeep-reserve-probe.py <bin> knoboff <out>`(검증 원문 · 고치기 전 = `keepers_after_20s 1 · old_seat_alive_after_20s true · same_role_create_rc 0`) → 고친 뒤 = keepers 0 · 옛 좌석 죽음 · 파일 정리(.log 제외). 뮤턴트 = 노브 끔 정리 호출 끔 → 붉음.
2. **M2**(원문: 「재시도(짧은 간격 N회) → 끝내 못 하면 관리용 종료 + 역할 해제/복원 · 역할 모름 미결이 모든 역할 생성을 막지 않게(그 좌석의 역할이 판명될 때까지만 · 상한 시간) · 조회 1줄(cys status 또는 explain)」)
   - 자리: `adopt_on_boot` 끝 → 미결이 있으면 백그라운드 스레드가 `adopt_one` 을 짧은 간격(예 2초 × 5)으로 재시도(입양되면 예약 풀림) → 끝내 미결 = 1의 관리용 종료 + 예약 걷음 → 그 역할 복원(`cys restore` 와 같은 길 · 또는 자동 복원 재개) · 역할 모름 미결 = 상한 시간(예 60초) 뒤 같은 처리. 조회 = RPC `seat.adopt_status`(SUMMARY + PENDING 의 skid·역할·사유·나이 · 토큰 0) + `cys status --json` 1칸.
   - 시험: 부하 3초 시한 실패 흉내 = 검증 탐침의 `registry_io` 고정물(등록부 권한 0 → 재시도 중에 권한 되돌림 → 입양됨) · 끝내 실패 → 끝남·복원 · 역할 모름 상한 뒤 역할 있는 생성 rc 0.
3. **m1**: 판정 앞에 「그 seatkeep 의 `--lock`(등록부 또는 KERN_PROCARGS2 인자) = 이 cysd 의 시작 잠금 경로」 대조 · 다르면 무접촉(판정·소비·삭제 0) · 시험 = 같은 폴더 소켓 둘.
4. 그다음 T6a 나머지(위 T6 절 · `docs/seatkeep/T6-DESIGN.md` · master#38e51f0e 결정 D1~D5): drain 분리 · 사전 점검 `cysd --adopt-check` · 상한 · A1 rotate 6회(e2e `rotate` 모드 · 2b741e0c6) · D4 launchd(허락됨 · 라벨 `com.cysr.test.t6.<pid>` · try/finally bootout+plist 삭제+`launchctl list | grep com.cysr.test` 0) · D5 claude 기억(허락됨 · 격리 프로필 계정2 `--setting-sources project`) · 뮤턴트 · 【확인요청】.
- 검증 좌석 덧붙임 📌(기록): ⓐ 업데이터가 「옛 번들 지우기 → 새로 복사」 사이에 cysd 를 띄우면 `proc_pidpath` 실패 → 미결(T6b 순서 확인) ⓑ KERN_PROCARGS2 로 같은 사용자가 토큰 env 를 읽을 수 있음(T3 부터 · 경계 안) ⓒ 입양 기록 둘이 같은 비-worker 역할이면 latest-wins 로 앞 좌석 `surface.role` 칸이 남음(기록 쓰기 실패 전제 · 드묾).

### 이 매듭의 시험·커밋 요약
- 커밋: 2b741e0c6(T6a 폴백·e2e rotate) · 282b1e568(B1·B2) · 80d66308b(빈칸 2). 시험: 폴백 단위 1 · dedup 단위 1 · 관련 묶음 125/125 · 빈칸 단위 2 · 탐침 claim/dedup 붉음→초록 · 뮤턴트 R1~R4 붉음 · e2e rotate 2회+drain 1회 rc 0(좌석 생존·작성자 하나).
- 전체 cysd 묶음은 282b1e568·80d66308b 뒤 **안 돌림**(마지막 전체 = d2ca1de03 3351/0) — 후임 첫 전체 실행 때 확인.
- 실사용 cys list 시험 좌석 0(실좌석 2276·2286 만) · 시험 프로세스 잔존 0.

## 후임 3(worker-1116seatkeep3 · surface:2289 · master#2f4011cc · 브리프 `master/briefs/1116-full/seatkeep3.md`) 델타 — 11-20 06:0x~
### 커밋
| 커밋 | 내용 |
|---|---|
| 277c2df57 | **M1** 노브 끔 기동 = 산 seatkeep 관리용 종료(`end_orphans_in` → `end_keeper` → `consume_dead`) · **D2**(T6) 기록 없는 산 seatkeep = 같은 종료 · **m1** 조종자 잠금 결박(`bind_from`·`claimed_lock` · 다르면 `foreign` 무접촉) · seatkeep 등록부·종료 기록 `lock` 칸(입양 모드만) · `seat_proc::controller_lock_path` |
| ead22aa8d | **M2** 미결 재시도(2초 × 5) → 끝내 미결 = 관리용 종료 + 예약 걷음 + 자동 복원 재실행 · 역할 모름 전면 차단 60초 상한(`blocks_all_until` · 재시도도 처음 상한 이음 `carry_pending`) · 조회 `org.status daemon.seat_adopt`(= `cys status --json` · 입양 켬일 때만 칸) |
- 브리프 ④ 빈칸 2(reclaim·restore 관문) = 앞 좌석 80d66308b 에서 끝남 — 이 매듭 전체 실행에서 `reclaim_commit_refuses_…`·`restore_released_refuses_…`·`dedup_avoids_reserved_names` ok 확인(새 작업 0).

### 관리용 종료 신원 규칙(`end_keeper` · 하나라도 안 서면 무접촉 Err)
pid 생존 · 출생 시각 = 기록/등록부 값 · 실행 파일 = 이 cysd 옆 cys-seatkeep(`seatkeep_exe_matches == Some(true)`) · 인자 `--lock`(KERN_PROCARGS2 · `--` 앞만) = 이 cysd 시작 잠금 · `<skid>.lock` 을 그 seatkeep 이 쥐고 있음(못 잡음) → SIGTERM → 5초(끝 = pid 없음/출생 시각 다름) → SIGKILL 2초 → 등록부 `seats` 자식(pid·start_us) 3초 → SIGKILL. 정리 = `consume_dead`(.log 남김).

### 시험(격리 env -i · 짧은 TMPDIR)
| 묶음 | 앞(d2ca1de03 · 검증 4ba42e596) | HEAD ead22aa8d |
|---|---|---|
| cysd 전체(스레드 4 · 07:10~07:27 · load 6→26) | 3351 · 0 · 17 · 계 3368 | **3358 통과 · 3 실패 · 17 무시 · 계 3378**(+10 = B1·B2·빈칸 3 · 이 매듭 7) — 실패 = `seatkeep_input_ack_*` 2(`handshake_timeout` · 3초 시한) · `fv1_paused_daemon_…` 1 → **load 17~19 단독 재실행 3/3 통과** |
| seat_adopt 단위 | 13 | 20(+7) |
| cys-seatkeep | 51 | 52(+1 `registry_lock_field_only_in_adoptable_mode`) |
| 노브 켬 accounts::+seat_proc:: | 180/180 | 180/180 · 입양 켬 180/180 |
| 탐침 knoboff(M1 반례) | keepers 1 · 옛 좌석 산다 · 파일 5 | **keepers 0 · 옛 좌석 끝남 · 파일 = .log 만** · 로그 `ended (knob_off_orphan_ended)` |
| e2e norecord(D2) | — | keepers 0 · 좌석 SIGNAL 1 · 파일 .log 만 · 같은 역할 rc 0 |
| e2e foreign(m1) | — | b 기동 = `foreign (other_controller_lock)` · b 같은 역할 rc 0(남의 역할 예약 0) · a 좌석 생존 · 종료 기록 b 소비 0 → a 재기동이 소비 · `SKA_FOREIGN_B_OFF=1`(노브 끔 b) = `knob_off_end_lock_not_mine` · a 좌석 생존 |
| e2e pending(M2) | — | recover = 재시도로 입양(4.9초) · fail = 10.7초에 `ended (pending_ended(registry_io))` · 좌석 SIGNAL 1 · rc 0 · unknown(역할 없는 좌석 + bin2) = 처음 rc 1 → 62초 뒤 `blocks_all` 거짓 · rc 0 · 고아는 조회 pending 에 남음 |
| e2e 회귀(M2 빌드) | — | adopt 2(교체 3/3 · 겹침 0) · reserve · reserve+위조 pid · exitaway · token 5칸 · norecord · foreign · knoboff 통과 |
- 뮤턴트(/private/tmp/skmut1119 · 파일 스위치 `/private/tmp/sk3mut/<X>` 1빌드 · 결과 scratchpad `e2e/mut-m1.out`·`mut-m2.jsonl`): A 노브 끔 정리 호출 끔 → knoboff 붉음(keepers 1) · B 잠금 결박 끔 → foreign 붉음(b 가 예약 rc 1 · 남의 종료 기록 소비) · C D2 끔 → norecord 붉음(고아·rc 1) · D end_keeper 잠금 검사 끔 → foreign B_OFF 붉음(남의 좌석 SIGHUP) · E 재시도 끔 → recover 붉음 · F 끝내기 끔 → fail 붉음 · G 상한 무시 → unknown 붉음. 재시도 상한 리셋 결함은 첫 unknown 실행이 실제로 잡음(고친 뒤 초록 · 단위 `retry_keeps_first_since_and_block_deadline`).

### 원작자 파일 변경 줄(이 매듭)
- handlers.rs: `org.status` 응답을 `let mut body` 로 받고 `seat_adopt::status_json()` 이 Some 일 때만 `daemon.seat_adopt` 칸 1개(+6줄 · 그 밖 바이트 무변).
- main.rs: `spawn_auto_restore` → `pub(crate)`(1줄).
- (이 갈래 파일) seat_adopt.rs · seat_adopt_tests.rs · seat_proc.rs(`controller_lock_path` 분리) · cys-seatkeep/main.rs(입양 모드 `lock` 칸 3자리 + 시험 1) · scripts/seatkeep-adopt-e2e.py(norecord·foreign·pending 모드).

### 지시 없이 내린 판단(후임 3)
1. m1 결박 근거 순서 = 산 pid 인자 → 등록부 `lock` → 종료 기록 `lock` · 근거 없음(옛 형식) = 종전 판정(산 seatkeep 을 **끝내는** 길은 인자로 확인된 Mine 만).
2. 관리용 종료가 좌석 자식이 3초 안에 안 끝나면 SIGKILL(같은 대화 작성자 둘 차단 우선 · 자식 신원 = 등록부 pid+출생 시각).
3. 노브 끔 기동은 **죽은** seatkeep 파일은 정리하지 않음(종전 · 입양 켬 기동 몫) — 산 고아만.
4. M2 재시도 2초 × 5 · 역할 모름 상한 60초 = 브리프 예시값 그대로 · 상한 재실행 대기 10분.
5. 조회 = JSON 칸만(`cys status` 사람용 줄은 안 바꿈).
6. 자동 복원 재실행의 실물(phoenix 가 풀린 역할을 띄움)은 e2e 에서 재지 않음(시험 env `CYS_NO_AUTORESTORE=1` · 로그 「자동 복원 재실행」 줄까지만 확인) — 측정 대기.

### 다음 첫 행동
1. master 【확인요청】 T4 처분 매듭 회신 대기 중 → T6a 나머지(아래) 착수: drain 분리(입양 좌석 = `org.status daemon.seat_adopt` 에 입양 좌석 목록 칸 → rotate ① 이 그 좌석의 저장 실패를 rc 에서 뺌) · `cysd --adopt-check --json`(잠금·소켓·쓰기 0 · 판정 = judge + 실행 파일 + 핵심 판 + 결박) + rotate ② 앞 점검 · holder 총수 상한(기존 좌석 상한 상수 없음 → 기본값 📌) · A1 rotate 6회 · D4 launchd · D5 claude 5회 · 뮤턴트.

## 후임 3 — T6a 나머지(11-20 07:3x~10:0x)
### 커밋
| 커밋 | 내용 |
|---|---|
| 2656d91e2 | drain 분리(`adoptable_surfaces` · `drain_ok_excluding_adoptable`) · `cysd --adopt-check [--json]` + rotate ① 앞 점검(rc 27 `ROTATE_RC_ADOPT_BLOCKED`) · holder 총수 상한(`CYS_SEATKEEP_MAX_HOLDERS` 기본 64 → 직접 PTY + `seat.seatkeep_capped`) |
| 052bcb18d | e2e `launchd`(D4) |
| e2eda303d | e2e `claude`(A4/D5) · `cost`(A13) · T6-DESIGN §6 결과 표 |
- 앞 좌석 2b741e0c6(폴백 거르개 · rotate 모드) + 후임 3 277c2df57(D2) 포함 = T6a 설계 항목 전부(2-1·2-2·2-5·2-6 · A1 · D4 · D5 · A13).

### 시험(격리 env -i)
| 묶음 | 앞(ead22aa8d) | HEAD e2eda303d |
|---|---|---|
| cysd 전체(스레드 4 · 09:30~09:47 · load 43→20) | 3358/3/17 · 계 3378 | 3360 통과 · 5 실패 · 17 무시 · 계 3382(+4) — 실패 = seatkeep_* 3(`handshake_timeout`) · `settle_hold_denies_…` 1 · `ingest_drain_throughput_bench` 1(941 vs 466ms) → **load 5 단독 재실행 7/7 통과** |
| cys 전체(10:03) | — | **799 통과 · 0 실패 · 2 무시**(+ drain·precheck 단위 2) |
| 입양 켬 accounts::+seat_proc:: | 180/180 | 181/181(+ holder_cap) |
| e2e | — | precheck(rc 27 → rc 0) · cap · rotate 6(A1) · launchd(D4) · claude 5/5(D5) · cost(A13) |
| 뮤턴트 | — | H 사전 점검 끔 · K 점검 실행 파일 검사 끔 · I 상한 끔 — 3/3 붉음(`e2e/mut-t6a.jsonl`) · drain 분리 = 순수 함수 단위 시험이 직접 잡음(뮤턴트 생략) |
- A13 숫자 = T6-DESIGN §6(디버그 빌드 · load 40~50 · 판정선 master).

### 원작자 파일 변경 줄(T6a 나머지)
- cys.rs(원작자): rotate ① 앞 점검 6줄 · ① 결과 판정을 `drain_ok_excluding_adoptable` 로(+4줄) · rc 표 1줄 + `ROTATE_RC_ADOPT_BLOCKED` · 새 함수 4(`drain_ok_excluding_adoptable`·`rotate_adoptable_surfaces`·`adopt_precheck_verdict`·`rotate_adopt_precheck`) · 시험 2.
- main.rs: `CysdCli::AdoptCheck`(+ 파서 7줄 · usage 1줄 · main 분기 1줄 · 시험 1 + 거절 표 2줄).
- handlers.rs: `status_json(daemon)` 인자 1곳.
- (이 갈래) seat_proc.rs(`open` 상한 갈래 · `holder_cap_from`·`holders_over_cap` · `SEATKEEP_CORE_VERSION`) · seat_adopt.rs(`status_json` 입양 좌석 목록 · `check_block_reason`·`adopt_check_main`·`adopt_check_in`) · 시험 · e2e.

### 함정(후임 3)
- zsh 루프 `set -- $x` 는 단어를 안 쪼갬 → 뮤턴트 스위치가 안 켜진 무효 실행 1회(기억 그대로) — 뮤턴트·묶음 실행은 bash 스크립트 파일로.
- claude 신뢰 질문 기본값 = 「No, exit」(Return 만 보내면 rc 1 로 끝남) → Down + Return.
- 화면 전체 낱말 개수 판정 = 읽기 창(400줄)에서 앞 줄이 밀리면 안 늘어남 → 「이번 질문(회차 번호로 유일) 뒤」 판정.
- D5 1회차 실행(중단) 뒤 rotate 가 자동 기동한 시험 cysd 2개가 ppid 1 로 남았음(21202 · 80778 — pid 로 끝냄) → 실물 시험 뒤 `ps | grep /private/tmp/ska-` 0 확인 필수.
- 기계 load 가 이 매듭 중 165 까지(다른 좌석) — 시한 계열 붉음은 단독 재실행으로 가름.

### 지시 없이 내린 판단(T6a)
1. 사전 점검 위치 = rotate ① 저장 지시 **앞**(설계 = ② 앞) — 막힐 거면 좌석에 [DRAIN] 을 보내기 전에 멈추는 편이 부작용 0.
2. 사전 점검 대상 cysd = 이 cys 옆 cysd(비업데이트 rotate 의 다음 데몬). 업데이터 S7 앞 점검(새 번들 cysd) = T6b.
3. 옛 cysd(`--adopt-check` 모름 = 인자 거절 rc 2) = 막힘(rc 27) — 입양을 모르는 판으로의 교체는 2-4 의 관리용 종료 경로(T6b) 전까지 멈춤.
4. holder 상한 = 입양 모드만 · 기본 64(기존 좌석 상한 상수 없음) · 산 좌석 수 = 이 데몬의 seatkeep 좌석(미결 고아 제외).
5. A13 은 디버그 빌드 숫자(릴리스 빌드 측정 = 측정 대기).

### 다음 첫 행동
1. master 회신(T4 처분 · T6a) 대기 — codex 1R(T6a = 업데이터 아닌 rotate·CLI 축) 여부는 master 대기열.
2. T6b: 2-3 업데이트 뒤 신원(D1 = 옛 번들 `.cysr.app.old-<seq>` 자리 허용 + 같은 팀 서명) · 2-4 되감기·판 내림 관리용 종료(`end_keeper` 재사용) · 업데이터 S7 앞 점검 · e2e `update`(격리 번들 두 벌 rename 흉내) · 검증 좌석 📌ⓐ(옛 번들 지우기→복사 사이 기동 = proc_pidpath 실패 → 미결 → M2 가 신원 불성립으로 끝내지 못함).
