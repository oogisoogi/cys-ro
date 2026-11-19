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
