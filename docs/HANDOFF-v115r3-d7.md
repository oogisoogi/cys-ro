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

## 8. r2(TICKET=v115r3-d7-r2 · surface:943) — agy 1R 4건 대응 + master D안 + 팩 오염 규명

> 상태를 복제하지 않는다 — `git log --oneline 0de7a4b4..HEAD` · 시험은 아래 명령으로 다시 잰다.

### 8-1. agy 1R 대응표
| # | 판정 | 수리 자리 | 시험(뮤턴트 킬러) |
|---|---|---|---|
| #3 P1 생성 직후 Unknown 창 | **실재**(강제 배달 경로) — 수리 ⓐ | governance.rs `SEAT_UNKNOWN_HOLD_SECS`(첫 틱+1s) · `role_seat_hold`(단일 술어) · 강제 게이트 · 틱 게이트 | `d7_role_seat_hold_table_unknown_only_inside_creation_window` · `d7_fresh_unknown_role_seat_tick_holds_with_reason` · `force_deliver_empty_seat_refused_unknown_passes`(대조군 재조준 = 창 밖 Unknown 통과) |
| #1 P2 settle 뒤 stale row | 수리 | javis_boot_node.py settle 직후 `row = status_surface(status, a.role)` | `test_d7_seat_replaced_during_settle_targets_the_new_seat` · `test_d7_seat_gone_during_settle_launches_fresh` |
| #2 P2 sleep 상한 초과 | 수리 | `step = min(tick_s, limit - waited)` | `test_d7_settle_unknown_seat_pure`(조각 목록 [1,1,0.5]·[0.5]) · `test_d7_settle_never_sleeps_past_the_limit_wall_clock`(실경과 <0.6s) |
| #4 P2 M1(sleep 삭제) 생존 | 수리 | settle 시험이 잔 횟수·길이 단언 | PM1 KILLED |

### 8-2. #3 격리 재현(스크래치 `race/probe4.sh` · stub · `.zshenv` 의 `/bin/sleep N` 으로 셸 초기화를 늘려 창을 결정론으로 세움)
| 빌드 | 경로 | 초기화 | 결과 |
|---|---|---|---|
| 기준선 27e4627e | 강제(queue deliver) | 1.5s | 1/1 seat=unknown 인 채 +1.16s 배달 → 빈 셸 실행 |
| HEAD 0de7a4b4 | 강제 | 1.5s | 2/3 같은 모양(+1.15·+1.21s) · 1/3 은 prime 이 Empty 를 실어 보류 |
| ⓐ | 강제 | 1.5s | 4/4 거부(0.13~4.19s 전 구간 empty_seat 코드) · 실행 0 |
| 기준선·HEAD·ⓐ | 틱 | 7s | **4/4 빈 셸 실행**(+4.16~4.25s queue.delivered forced=false) — 틱이 초기화 자손을 보고 Occupied 로 적고, 초기화 중엔 출력이 없어 quiet 3s 를 채운다(ⓐ 로 안 닫히는 창 · 기준선부터 있던 창) |
| D(94b280c7) · 부서 소켓 | 틱 | 7s | 2/2 보류(+4.2s queue.held reason=seat_no_agent seat=occupied → 이후 empty_seat) · 실행 0 |
| D · 부서 | 강제 | 1.5s | 거부 · 실행 0 |
| D · 부서 · 에이전트 좌석(뿌리=stub) | 틱 | 0 | +4.21s 배달(엄격 관측이 풀어 줌 — 무한 정지 없음) |
| D · 부서 · `CYS_SEAT_BOOT_GRACE_S=3` | 틱 | 7s | 배달(유예 뒤 종전 판정 복귀 = 설계대로의 폴백) |
| D · 본부 소켓 | 틱 | 7s | 배달 = **종전 그대로**(본부 좌석 정책 무접촉 — 남은 창 · 1.1.6) |

ⓑ(prime 재시도 2×500ms)는 1.5s 초기화에서 1s 뒤에도 Occupied 라 창이 남아 열위.

### 8-3. D안(master#3b5500f0) — `role_seat_hold` 셋째 팔
부서 소켓(`cys::is_dept_socket` — 경로에 `cys-dept-` 성분)의 역할 좌석 ∧ 메타 없음 ∧ `seat_agent_cache`(뿌리 포함 엄격 매칭) 미관측 ∧ 생성 후
유예(`CYS_SEAT_BOOT_GRACE_S` · 기본 180 · boot_node 미러) 안 → 보류(reason=seat_no_agent). 유예 뒤 종전 판정 · 본부 = `dept_grace=None`.
시험 = 표(유예 초과 폴백·본부 무접촉·관측 해제·메타 좌석 비대상) + `d7_dept_role_seat_without_observed_agent_tick_holds`(`cys-dept-*` 폴더 소켓 데몬).

### 8-4. 뮤턴트(스크래치 `mut2.py`·`dmut.py` · 별도 worktree · 판정 = 종료코드 · CRASH 분리)
데몬 9/9 KILLED: DA1 Unknown 팔 삭제 · DA2 창 조건 삭제 · DA3 강제 게이트 Empty 전용 복귀 · DA4 틱 게이트 Empty 전용 복귀 ·
DD1 유예 한정 해제(폴백 제거) · DD2 부서 한정 해제 · DD3 엄격 관측 조건 삭제 · DD4 부서 팔 무력화 · DD5 틱 경로 부서 배선 끊기.
팩 3/3 KILLED: PM1 sleep 삭제 · PM2 조각=틱 통째 · PM3 settle 뒤 row 재결정 삭제. (PM4 row None 가드 삭제 = 등가 뮤턴트 → 가드를 코드에서 걷음)

### 8-5. 팩 오염(§7) 규명 【관측】
사슬: `tests/test_formation.py:27`(CYS_PACK_DIR=저장소 팩) → `:206`·`:249` `m.ensure(socket="/tmp/b1.sock"|"/tmp/b5.sock")`(결원 로스터 2건) →
`javis_formation.py:1119` `_master_seat_cwd(socket)` — `_ensure_harness` 모킹 목록 밖 → `:514` 실 `cys status --json`(PATH 의 /usr/local/bin/cys 1.0.2) →
그 소켓에 데몬 없음 → CLI 자동 기동 → `/usr/local/bin/cysd`(1.0.2)가 상속 env(CYS_PACK_DIR=저장소 팩)로 부팅 팩 설치 → 1.0.2 임베드가 저장소 팩에.
증거: 09-23 09:41 `ps` 에 고아 `/usr/local/bin/cysd` 2개(시작 09:04:59·09:05:11 · ppid 1 · env CYS_SOCKET=/tmp/b1.sock·/tmp/b5.sock · CYS_STATE_DIR=…/fmens-*(= test_formation.py:192 접두) ·
CYS_PACK_DIR=이 worktree 팩 · cwd=이 worktree). 두 데몬은 실행파일·소켓·cwd 3축 확인 뒤 TERM(라이브 pid 62178 무접촉).
CI 러너엔 `cys` 가 없어 이 경로가 안 돌고(=CI 초록), 로컬에서만 설치본 cys 가 붙어 오염된다.
재발 차단(통합 검증 정본 한 줄): `env -u CYS_SURFACE_ID -u CYS_SURFACE_REF -u CYS_SEAT_TOKEN -u CYS_ROLE -u CYS_PACK_DIR PATH="$HOME/.cargo/bin:$HOME/.bun/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" CYS_SOCKET="$(mktemp -d)/none/cys.sock" CYS_NO_AUTOSTART=1 <단계>`
+ 단계마다 `git status --short` 가드. (근본 수리 = test_formation 이 `_master_seat_cwd` 도 모킹 — 1.1.6 후보 · 범위 밖이라 미수리)
부수 관측: 934 팩 루프(`for … done`)의 종료코드는 마지막 검체 것뿐이라 중간 적색을 삼킨다 — r2 루프는 적색 수를 누적해 종료코드로 낸다.

### 8-6. gen --check(2-1) 【관측】
기준선 27e4627e worktree rc=0 · HEAD rc=0(둘 다 GREEN 87739B). 934 의 rc=1(커밋본 81001B)은 오염으로 CEO_TEMPLATE 가 1.0.2 판으로 덮인 트리를 잰 값 → 수리 불요.

### 8-7. 남은 것
- 본부 소켓 역할 좌석의 「초기화 > 첫 틱」 창(8-2 마지막 줄) = 1.1.6(본부 좌석 정책 변경 = 오너 결정 사안).
- 【추정 · 미실측】 부서에서 느린 셸이면 boot_node settle 이 occupied 를 받아 입양 분기로 가지만, 이제 그 큐는 seat_no_agent 로 보류돼 빈 셸 타이핑은 없다 — boot_node 결과는 injected_unverified(rc=1) 로 남고 다음 편성 심박이 empty 를 보고 승계한다.
- 곁 「_seat_event stdout 만」 = 1.1.6(수리 금지 · 이월 그대로).

### 8-8. 통합 검증(r2 · HEAD 94b280c7 · 격리 env 8-5 · 09:42:54~10:01:19 · 단계마다 dirty=0)
| 단계 | rc | 초 | 건수 |
|---|---|---|---|
| cargo test --lib(--test-threads=1) | 0 | 228 | 533 pass · 0 fail |
| cargo test --bin cysd(직렬) | 0 | 105 | 1033 pass · 0 fail |
| cargo test --bin cys | 0 | 103 | 280 pass · 0 fail |
| ui bun test | 0 | 1 | 1102 pass · 0 fail |
| 팩 CI 루프 45검체(적색 누적 판정) | 0 | 293 | PACK-FAILS=0 |
| secret-scan --all | 0 | 4 | clean · 1082 파일 |
| gen --check | 0 | 0 | GREEN · 87739B |
| 전체 건강 검체(직렬) | 0 | 371 | pass 149 · skip 1 · GREEN |
2-0 재현(버리는 worktree · 비격리 env): `test_formation` 단독 1/1 오염(새 cysd 2 · 추적 116파일 · `.pack-version` 기록) — 재현분 고아 2개도 3축 확인 뒤 TERM, worktree 폐기.

### 8-9. 오염 경로 봉합(master#a8ad3256 · 검증 위생 · 제품 동작 무접촉)
`tests/test_formation.py` `_ensure_harness` 가 `_master_seat_cwd` 도 모킹(저장·복원 목록 포함) + 트립와이어 검체 **9z**(ensure 절 동안 `subprocess.run` 의 실 `cys` 호출을
가로채 기록·실행 0 → 0건 단언). 실측: 설치본 cys 가 PATH 에 있는 비격리 env 로 돌려도 43/43 · 트리 무변경 · `/usr/local/bin/cysd` 0 → 0.
뮤턴트 TM1(하네스 모킹 삭제) = KILLED(9z 적색 · `cys status --json` 2건 가로챔 · 데몬 기동 0).

## 9. r3(master#bb06acb1 · agy 2R REJECT — 1R 4건 전부 수정 확인 · 신규 4건)

| # | 판정 | 수리 자리 | 시험 · 뮤턴트 |
|---|---|---|---|
| 2R#1 P2 settle 기본 분기(None → 2틱) 호출처 0 | 수리 | javis_boot_node.py `settle_unknown_seat(..., *, max_wait_s)` 필수 키워드 · `limit = float(max_wait_s)` | `test_d7_settle_requires_explicit_limit`(누락 원인 문구까지 단언) · PR1(기본값만 복원)·PR2(원본 전체 복원) KILLED |
| 2R#2 P2 부서 판별이 경로 전체 any() | 수리 | governance.rs `dept_seat_agent_grace_secs` 가 `cys::dept_name_from_socket`(직계 부모 폴더·윈 파이프 끝 성분) | 표 시험에 `/Users/x/cys-dept-project/w/.local/state/cys/cys.sock = 본부` 반례 · R1(any() 복귀) KILLED |
| 2R#3 P3 queue.clear 뒤 낡은 blocked | 수리 | handlers.rs queue.clear drain 직후 `queue_blocked = None` | `queue_clear_allows_self` 단언 · R4 KILLED |
| 2R#4 P3 유예 만료 경계 배달 실패 시 낡은 좌석 사유 | 수리 | governance.rs `release_stale_seat_hold_reason` — 좌석 보류가 풀린 틱에 좌석 사유만 배달 시도 **전**에 걷음(타 게이트 사유 불변) | `d7_released_seat_hold_clears_only_seat_reason_before_delivery`(행위 + 호출 위치 핀) · R2(헬퍼 무력화)·R3(호출 삭제) KILLED |

- 한계(정직): 2R#4 의 「배달 실패」 자체는 단일 스레드 시험에서 결정론으로 만들 수 없다(`write_tx` 는 교체 불가 필드 · 입력줄 대조는 동시성 필요) → 헬퍼 행위 + 호출 위치(배달 시도 앞) 소스 핀으로 잰다.
- 곁(미수리 · 범위 밖): `src/lib.rs` `is_dept_socket`(경로 전체 any())은 다른 소비자(채널 브리지 스폰 거부 등)가 그대로 쓴다 — 같은 반례 부류. 1.1.6 후보.
- 곁(선재 간헐 · r3 무관): `handlers::tests::reap_denies_queue_nonempty_then_queue_clear_exited_reclaim` 는 필터 묶음(`d7_ force_deliver queue_clear`) 직렬 실행에서 간헐 적색 — r3 이전 94b280c7 에서도 5회 중 3회 · 단독 3/3 초록. 뮤턴트 킬러 목록에 섞여 나오므로 귀속은 각 뮤턴트의 고유 킬러로 판정했다. 전체 cysd 스위트 직렬에선 r2·r3 모두 초록.
- agy 2R 부기 「javis_formation.py isinstance(obj, dict) 삭제 뮤턴트 생존」 = 이번 티켓 수리 범위 밖(선재 코드) · 미수리 · 1.1.6 후보.

### 9-1. 통합 검증(r3 · HEAD eda4f205 · 격리 env · 10:17:41~10:43:31 · 단계마다 dirty=0)
| 단계 | rc | 초 | 건수 |
|---|---|---|---|
| cargo test --lib(직렬) | 0 | 392 | 533 pass · 0 fail |
| cargo test --bin cysd(직렬) | 0 | 129 | 1034 pass · 0 fail |
| cargo test --bin cys | 0 | 113 | 280 pass · 0 fail |
| ui bun test | 0 | 0 | 1102 pass · 0 fail |
| 팩 CI 루프 45검체 | 0 | 369 | PACK-FAILS=0 |
| secret-scan --all | 0 | 10 | clean · 1082 파일 |
| gen --check | 0 | 1 | GREEN |
| 전체 건강 검체(직렬) | 0 | 536 | pass 149 · skip 1 |
(10:12 에 02ffad23 로 시작한 1차 실행은 도중 시험 파일 수정·커밋으로 트리가 바뀌어 중단·폐기 — 위 표는 eda4f205 단일 트리 값.)

## 10. r4(master#5008bf71 · agy 3R REJECT — 2R 4건 CLOSED · 신규 2건)
| # | master 판정 | 조치 | 시험 · 뮤턴트 |
|---|---|---|---|
| 3R#2 P3 queue.clear ↔ deliver_queued 경쟁(clear 가 지운 직후 옛 머리로 mark) | 채택 | 47437b1c — deliver_queued 가 빈 큐면 continue 전에 queue_blocked=None(큐 락을 놓은 뒤 · 두 락 미결합) · clear 측 지움 존치 | `d7_empty_queue_tick_clears_stale_blocked_reason` · M1(틱 측 지움 삭제) KILLED |
| 3R#1 P3 dept_name_from_socket 윈 rsplit | 기각 + 1줄 강화 | 47437b1c — 후행 `\`·`/` trim 뒤 마지막 성분 · 주석 「윈은 명명 파이프만」 | `d9_dept_name_from_socket_both_platforms` 에 후행 구분자 → Some("edu") · M2(trim 삭제) KILLED |
| 3R#3·#4 | SAFE | 조치 0 | — |
시험 커밋 = d246aa3d(제품·시험 분리). 전체 건강 검체(HEAD d246aa3d · 격리 env) = rc 0 · 451s · pass 149 · skip 1 · GREEN · dirty 0.
표적 cysd 묶음 32건 중 적색 1 = 선재 간헐 reap 시험(§9 곁 · 기준선 동일).
