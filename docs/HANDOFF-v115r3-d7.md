# HANDOFF — v1.1.5 7차 트랙 D7⑴ (부서장 좌석 빈 셸 선행) · TICKET=v115r3-d7

작성 2026-09-23 · 브랜치 `fix/v115r3-d7` (← 27e4627e = 6차 절단) · 워커 surface:934
결함 정본 = `~/axdev/master/reports/cysr-115-2026-09-22/DEFECTS-2026-09-23.md` D7
선행 = `docs/HANDOFF-v115r2-daemon.md` §1(원인 「takeover_failed 유력」 — **이 라운드 관측으로 정정됨**)

> 상태를 복제하지 않는다 — 커밋·시험 결과는 명령으로 읽는다.
> `git log --oneline 27e4627e..HEAD` · `python3 -m unittest tests.test_v115_dept`(cwd = `cysjavis-pack/bin`)

## 1. 원인 【관측】 — 916 의 유력 가설(takeover_failed)은 틀렸다

`javis_boot_node.main` 은 **처음 받은 `cys status` 스냅샷** 으로 `empty_seat_action` 을 판정한다.
데몬의 `seat_cache` 는 좌석 생성 시 0(Unknown · `state.rs` `seat_cache: AtomicU8::new(0)`)이고
첫 워치독 틱(`WATCHDOG_INTERVAL_SECS`=5)이 처음 채운다. 부서 allocate 직후 편성이 바로 부르면
스냅샷의 `seat` 는 늘 `"unknown"` → `empty_seat_action` = None(비해당) → 흐름이 **입양-주입** 으로
떨어져 claude 없는 빈 셸에 각성문(505B)을 큐잉 → ack 없음 → rc=1 → 편성 「기동=cso,worker」.
승계(takeover)는 **시도조차 안 됐다** — 그래서 `role.claim_denied` 가 0건이다.

증거(같은 모양 두 곳):
| 출처 | sid=1 생성 후 | 이벤트 |
|---|---|---|
| VM 교육부 `events-cys-dept-dept-1.jsonl` | +4.5s | `queue.enqueued` sid=1 **505B from=null** · claim_denied 0 |
| 격리 재현(수리 전 boot_node) | +6.2s | `queue.enqueued` sid=1 **505B from=null** · claim_denied 0 · boot_node JSON `precheck: 입양해 주입` → `injected_unverified` rc=1 |
| 격리 status 폴링 | 0.4s·1.3s = `unknown` · 2.3s~ = `empty` | — |

## 2. 수리 — 두 층(master 지시 c22f2860 · 판정 f0bb40a5)

| 층 | 커밋 | 무엇 |
|---|---|---|
| 데몬 | `c1c5b8a3` · `8e23b19b` | `governance::prime_seat_cache_at_create` — surface.create 성공 아크에서 응답 **전** 1회 판정 · **Empty 일 때만** · Unknown 일 때만 CAS(틱 값 불덮음). 판정은 `cache_seat_verdict` 한 곳(틱과 공유). SEAT 게이트 보류가 새로 선 틱에만 `queue.held`(reason=empty_seat · role · surface_ref · depth) — `mark_queue_blocked` 가 전이 여부 반환 |
| 팩 | `7d85ddc6` (+시험 보강) | `javis_boot_node.settle_unknown_seat` — seat=unknown ∧ agent 없음이면 워치독 2틱(10s·남은 데드라인 이하) 안에서 1초 재조회 뒤 판정 · 근거 줄 · 입양 분기 로그에 판정 seat 값. `javis_formation._boot_verdict_text` + detail 「기동실패=<역할>:<result/reason>」(cys-dept 가 formation.log 에 기록) |

★Empty 한정의 근거(【관측】): 생성 순간의 Occupied 는 `zsh -l` 초기화 자손(path_helper)의 일시값 — 1차 수리(Unknown 만
제외) 뒤 race 0 1/3 에서 prime 이 Occupied 를 굳혀 입양 분기로 샜다(`queue.held` +8.95s 로 원장 관측). Empty 한정 뒤 5/5 승계.

## 3. 검증
- race 0(935 §5 run.sh 동형 · stub · `/tmp/cysrace.*`): 수리 후 5/5 = t0 seat=empty → `role.takeover` +0.87~0.95s ·
  입양 0 · 빈 셸 주입 0. (최종 rc=1 은 stub 이 세션 jsonl·ack 를 못 내는 【모의】 한계)
- 편성 E2E(stub): 「기동=cso,master,worker」 · master 좌석 agent=claude. 대조군(수리 전 임베드) = 「기동=cso,worker」 · 505B +6.5s.
- 시험(데몬): `d7_new_seat_is_judged_at_create_not_left_unknown` · `d7_prime_seat_cache_never_overwrites_a_tick_value` ·
  `d7_empty_role_seat_hold_emits_queue_held_once` · v113 배선 핀 재조준.
- 시험(팩): `test_d7_fresh_master_shell_unknown_seat_is_taken_over_not_adopted` · `test_d7_settle_unknown_seat_pure` ·
  `D7FormationRecordsBootReason` 2건.
- 뮤턴트: 팩 8종(M1~M6 · FM1~FM2) · 데몬 5종(DM1~DM5) — 결과는 【확인요청】 표(하네스 = 스크래치 사본·별도 worktree).

## 4. 함정(다음 사람)
- **격리 하네스에서 실 claude 가 뜬다**: 좌석 로그인 셸이 PATH 를 재구성해 `/opt/homebrew` claude 가
  잡힌다(PATH 앞에 가짜를 둬도 못 막음) → OAuth 브라우저·키체인 대화상자(09-23 실사고).
  정답 = 격리 팩 `agents.json` 의 `claude.cmd` 를 **절대경로 stub** 로 · env `BROWSER=/usr/bin/false`.
- **팩 파일을 격리 팩에 복사해도 데몬 기동 시 heal 이 임베드본으로 되돌린다** — 팩 수정 후엔
  바이너리를 다시 빌드해야 격리 재현에 반영된다(`fix_in_pack` 계수로 확인).

## 5. 미결·곁
- 【관측】 boot_node 의 기존 `_seat_event`(승계·회수·seat.kept)는 `javis_event.py emit` 을 부르는데 그 도구는 wire 한 줄을
  stdout 에 찍을 뿐이고 boot_node 가 capture 해 버린다 → 데몬 원장 0건. DEFECTS D7 「설계 이벤트
  seat.reaped_after_succession 0건」의 원인 = 발행 경로 부재. 수리 안 함(범위 밖 · master 보고).
- 【추정】 잔여 창: prime 이 Unknown 을 남긴 좌석에 첫 틱이 셸 초기화 순간(수백 ms)에 떨어지면 Occupied 로 읽혀 입양 분기
  가능. race 0 5/5 에선 0회. 입양이 나면 `queue.held` 가 원장에 찍힌다(관측 가능).
- 916 곁 3건(should_delegate_autostart 등) = 1.1.6 · 무접촉.

## 6. agy 1R(REJECT · 4건) — **미착수 · 후임 r2 소관**(master 정지 지시 d2a61a8a · effort high 후임)
원문 = `~/axdev/master/reports/cysr-115-2026-09-22/hetero-agy-d7-1.md`. 934 는 판정 관측만 하고 수리는 커밋하지 않았다.
- #1 P2 settle 뒤 `row` 재조회 없음 · #2 P2 `time.sleep(tick_s)` 가 상한 초과 가능(`min(tick_s, limit-waited)`) · #4 P2 sleep 호출 계수 무단언 — 미착수.
- #3 P1(빈 셸 배달) 판정 【관측】(격리 · stub · `probe3.sh`): **틱 배달 경로 = 재현 0**(틱은 refresh_seat_cache 직후
  deliver_queued — 배달 시점 캐시는 생성 직후 Unknown 이 아니다 · 수리 전/후 모두 INJECTED=no 5/5).
  **강제 배달(`cys queue deliver`) 경로 = 실재**: 수리 전 빌드에서 생성 +1.3s seat=unknown 빈 zsh 에 `touch` 가 실행됨(2/2) ·
  수리 후엔 거부(3/3)였으나 queued 3회 중 2회 enqueue 시점 seat=unknown(prime 이 셸 초기화 자손 때문에 무기록) → 같은 창이 남는다.
- #3 수리안 판단 메모(934 · 미확정): ⓐ `role_seat_hold()` 단일 술어 — 역할 좌석이 Empty 이거나 **생성 후 첫 틱+1s 안의 Unknown** 이면
  틱·강제 두 게이트가 보류(창 밖 Unknown = 프로브 실패 = 종전 통과 유지 · 거부 코드 empty_seat 그대로 → CLI exit 7 불변).
  ⓑ prime 재시도 2×500ms 는 모든 create 응답을 최대 1s 늦추고 느린 셸 초기화면 여전히 창이 남아 열위로 봤다.
  ⓐ 초안(시험 미작성 · 미빌드) = `docs/r2-wip-934.patch`(governance.rs 만). ⚠기존 핀 `force_deliver_empty_seat_refused_unknown_passes`
  의 Unknown 대조군은 생성 직후 좌석이라 ⓐ 적용 시 적색이 난다 — 대조군을 「창 밖 Unknown」(created_at 을 과거로)으로 재겨눠야 한다.
- 하네스 경로(스크래치 · 세션 소멸성 — 재현 절차는 여기 3줄이 정본):
  1. race0/probe: 스크래치 `race/{bin,pack,stub/claude,run.sh,probe3.sh}` — pack 사본 `agents.json` 의 `claude.cmd` = 절대경로 stub · env -i + `BROWSER=/usr/bin/false` · 데몬 종료 = 소켓 소유 pid.
  2. probe3 = new-surface --role master → 즉시 `cys send --queued --surface surface:1 "touch <표식>"` → (forced 모드) 0.3s 간격 `cys queue deliver` → 7s 뒤 표식 파일 존재 = 빈 셸 타이핑.
  3. 대조군 바이너리 = `~/axdev/.wt/cys-v115-integ6/target/release/{cys,cysd}`(27e4627e).

## 7. ⚠통합 검증 중 저장소 팩 오염(09:05 · 원인 미확정)
통합 검증(작업트리 f65be129) 도중 09:05:00~07 에 **옛 1.0.2 임베드 팩이 저장소 `cysjavis-pack/` 에 설치**됐다(추적 92파일 변경 · 모드
100644→100755 · `.user` 16 + `.new` 4 + `.pristine/`·`.merge-pending.json`·`.pack-version`(1.0.2) · 루트 `claude/`). `.user` 16건 = HEAD 와 동일(내 커밋본이 병치로 밀림).
그 뒤에 돈 `gen --check`(rc=1)·건강 검체 `H-PACK-TRACK-1`(fail · 누락 = 그 `.user` 들)은 **오염된 트리를 잰 값**이다. 복구 = `git checkout -- .` + 미추적 24 삭제.
원인 후보 【추정】: 같은 시각대 팩 CI 루프 말미 검체 또는 병행한 격리 프로브 — 어느 쪽이 CYS_PACK_DIR 를 저장소 팩으로 잡고 1.0.2 `cys`(PATH 의 /usr/local/bin/cys)로 설치했는지 미확정.
라이브 `~/.cys/pack` 은 무접촉(마지막 쓰기 09-22 12:33). 재검증 = 별도 worktree(`vwt`)에서 gen→health→팩 루프(검체마다 `git status` 오염 가드) 순.
