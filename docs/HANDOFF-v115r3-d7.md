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

## 11. r5(master · CI 7차 맥 aarch64 레인 적색 · run 35808969481 · job 107015966746)
원인 두 갈래 — 둘 다 **시험이 호출자 환경을 전제**한 결함이고 제품은 무접촉이다. 앞 라운드의 로컬 초록(§8-8·§9-1 cysd 1033/1034 pass)은
로컬 SHELL=zsh·stdin EOF 에서만 잰 값이라 CI 러너 조건을 한 번도 만나지 않았다(초록불이 대상을 안 만남).

| # | 증상 | 원인 【관측】 | 수리(커밋) | 시험 · 뮤턴트 |
|---|---|---|---|---|
| ⑴ | `d7_new_seat_is_judged_at_create_not_left_unknown`(unknown) · `d7_prime_seat_cache_never_overwrites_a_tick_value`(None) | 좌석은 `$SHELL -lc "<PATH 선두주입>; <cmd>"` 로 뜬다(state.rs create_surface_with_env). 러너 SHELL=bash 3.2 는 목록의 마지막 `sleep 30` 을 **fork** → 뿌리의 영구 자손 → 판정 Occupied → prime(Empty 한정 설계) 무기록. zsh 는 exec. 탐침 15회: bash `sleep 30` 15/15 unknown · zsh 15/15 empty · `exec sleep 30` 두 셸 15/15 empty. 빈 CYS_PACK_DIR·직렬 순서는 무관 | 95944e9f — 픽스처 `exec sleep 30` · ⑴은 3회 중 1회 이상 empty(생성 순간이 셸 초기화 자손과 겹치면 Unknown 을 남기는 것도 제품 설계 · §6 ⓐ 창 보류가 덮음) + 어느 회차도 occupied 아님 단언 추가 · ⑵ 대조군은 자손 0 을 상태로 대기(5s 상한 · 전제 실패 시 적색) | M1 생성 경로 prime 호출 삭제 · M2 prime 무기록 · M3 CAS 기대값=현재값(틱 값 덮음) · M4 Empty 한정 해제 — 4/4 KILLED(SHELL=/bin/bash) |
| ⑵ | `cargo test --bin cys -- --test-threads=1` 27분 정지(로컬 · CI 명령 release.yml:361 그대로) | `tests::take_new_on_constitution_file_declines_noninteractive_without_promoting` 이 프로세스 stdin EOF 를 전제 — 닫히지 않는 stdin(에이전트 셸 소켓·열린 파이프)에선 `confirm_stdin` read_line 무한 대기. `--exact` 재현: stdin=/dev/null 0.03s · 열린 파이프 = 파이프 닫힐 때까지(84s). CI 는 stdin EOF 라 6차 aarch64(run 35791525423)에서 ok · cys 280 pass 53.6s → CI 재발 아님 | e4687d0e — 시험 전용 `StdinEofGuard`(unix: fd0 을 /dev/null 로 dup2 · Drop 복원 · 윈도우 무동작) | SM1 가드 삭제 → 60s 타임아웃 · SM2 fd 오조준 → 적색 — 2/2 KILLED · 열린 파이프 stdin 으로 cys 전체 280 pass(같은 전제 시험 0건 추가) |

- 4군 축(시험·좌석 판정 층): ③자가치유 — 제품 코드 무변경이라 좌석 캐시·틱·prime 거동 불변. ④전 pane 사망 — 좌석 생성·판정 경로 무변경 · 시험 픽스처만 exec 로 바뀜.
  시험 쪽 부수 효과: ⑴ 시험이 master 역할 좌석을 3회까지 만든다(승계 경로를 탄다 · 시험 데몬 한정). StdinEofGuard 는 ENV_LOCK 아래 한 시험에서만 fd0 을 바꾼다.
- 판단 1건(지시 밖 · master 확인 대상): ⑴의 「3회 중 1회」는 단일 발 단언을 완화한 것이 아니라 제품 설계(Empty 한정 · 셸 초기화 겹침 시 Unknown)를 시험에 옮긴 것으로 판단했다. prime 호출 삭제 뮤턴트는 3/3 unknown 으로 적색.
- 재현 함정(재발 방지): zsh 에서 `cargo test $a` 는 인자를 쪼개지 않는다(1회 게이트 무효 · bash 스크립트로 재실행). 백그라운드 Bash 도구의 stdin 은 닫히지 않는 소켓이라 ⑵ 가 이 조건에서 드러났다.

### 11-1. 통합 검증(r5 · HEAD e4687d0e · 12:05:32~12:21:58 · 단계마다 dirty=0)
CI 3명령은 release.yml 356·357·361 글자 그대로 + `SHELL=/bin/bash`(러너 조건). 건강 검체는 §8-5 격리 env 한 줄.
| 단계 | rc | 초 | 건수 |
|---|---|---|---|
| cargo test --bin cysd -- --test-threads=1 --skip hwmon:: | 0 | 122 | 1033 pass · 0 fail · 1 ignored |
| cargo test --lib -- --test-threads=1 | 0 | 319 | 533 pass · 0 fail · 1 ignored |
| cargo test --bin cys -- --test-threads=1 | 0 | 124 | 280 pass · 0 fail |
| 전체 건강 검체(직렬 · 격리 env) | 0 | 421 | pass 149 · fail 0 · skip 1 · GREEN |
뮤턴트 6/6 KILLED(M1~M4 · SM1~SM2 · 변이 적용 assert · 복원 해시 대조). 추가: 열린 파이프 stdin 으로 cys 전체 280 pass(94s).

## 12. r6(master · CI 8차 맥 aarch64 레인 적색 · run 35814642386 · job 107033449900)
r5 의 ⑴ 진단(bash 가 마지막 명령을 fork)은 맞았지만 **그것만으로는 러너 적색이 설명되지 않았다**. r5 수리 뒤에도 러너에서는 생성
순간 판정이 empty 가 아니었고, 3회 재시도 루프가 2회차에서 특권 역할 `master` 를 다시 잡으려다 claim_denied 로 죽었다
(패닉 = handlers.rs:14943 「surface.create 실패 … privileged role 'master' is held by a live surface」). 두 번째 시험은 러너에서 통과.

### 12-1. 원인 【관측 · 로컬 재현】
- 좌석은 `$SHELL -lc "<PATH 선두주입>; exec sleep 30"` 로 뜬다(state.rs create_surface_with_env). 로그인 셸은 cmd 를 돌리기 전에
  로그인 프로파일(bash = /etc/profile → `~/.bash_profile`)을 읽고, 거기서 띄운 자식이 **생성 순간** 뿌리의 자손으로 잡힌다 →
  판정 Occupied → prime 은 설계대로(Empty 한정) 싣지 않는다 → 다음 status = "unknown".
- 로컬 재현: `SHELL=/bin/bash` + 가짜 HOME 의 `.bash_profile` = `sleep 0.3` 로 종전 시험을 3회 → **3/3 적색 · 같은 줄(14943) · 같은
  claim_denied 문장**. 같은 조건에서 실 HOME(프로파일 없음) = 3/3 초록.
- 탐침(임시 · 미커밋): 실 HOME·bash/zsh 에서 생성 직후 40회 표집 → 매 표집 Empty · 뿌리 이름은 3ms 째 이미 `sleep`. 즉 이 기계에서는
  생성 순간 자손이 0 이라 종전 시험이 초록이었다 — 초록은 제품이 아니라 **이 기계의 로그인 프로파일이 가벼움**을 잰 값이었다.
- 러너 쪽 프로파일 내용 자체는 이번에 보지 않았다 【추정: GitHub macOS 이미지의 로그인 프로파일이 자식을 띄움】 — 기전은 위 재현으로 확정.

### 12-2. 재설계(시험만 · 제품 무접촉) — 계약을 두 층으로
| 층 | 시험 | 무엇을 재나 | 환경 의존 |
|---|---|---|---|
| (i) 의미 | `d7_prime_seat_cache_never_overwrites_a_tick_value`(기존 · 무변경) | 자손 0 → Empty 를 싣는다 · 자손 ≥1 → 안 싣는다 · 틱 값을 안 덮는다. 자손 0 은 **상태 대기**(5s 상한 · 미성립 시 전제 실패 적색)로 세운 뒤 판정 | 없음(대기가 프로파일 시간을 흡수) |
| (ii) 배선 | `d7_create_arc_primes_seat_cache_before_reply`(신규 · 종전 `d7_new_seat_is_judged_at_create_not_left_unknown` 대체) | 소스(테스트 모듈 앞 · 줄 주석 제거 · 줄 수 보존)에서 ⑴ 생산 코드의 prime 호출 = 정확히 1자리 ⑵ `"surface.create"` 아크의 `Ok(s)` 본문 **최상위(들여쓰기 20칸 = 무조건)** 에 `let _ = crate::governance::prime_seat_cache_at_create(&s);` ⑶ 그 자리가 같은 아크의 `Reply::Single(ok_response(` 보다 앞 | 없음 |
| (ii) 실행 축 | 같은 시험 후반 | 실 dispatch 로 비특권 역할(`worker-d7-arc`) 1회 생성 → status 좌석 ≠ "occupied"(시험 데몬엔 틱이 없으므로 prime 이 유일 writer · Empty 한정) — 재시도 없음 | 없음(불변식) |
(i)∧(ii) ⇒ 생성 순간 자손 0 인 좌석은 응답 전에 "empty" 로 실린다. 버린 단언 = 「이 호스트에서 생성 순간 판정이 empty 다」 — 제품 계약이
아니라 호스트 사실이라 게이트에 둘 수 없다(`#[ignore]`·조건 스킵 0 · occupied 불적재 단언은 그대로 유지).

### 12-3. 뮤턴트(CI 유사 조건 = SHELL=/bin/bash + 가짜 HOME 프로파일 · 변이 적용 assert · 매회 백업 복원)
| # | 변이 | 결과 · 잡은 단언 |
|---|---|---|
| M1 | 생성 아크의 prime 호출 삭제 | KILLED — (ii) 「prime 호출 자리가 정확히 하나가 아니다 · left 0」 |
| M2 | 호출을 `if role_for_announce.is_empty() { … }` 안으로 | KILLED — (ii) 「성공 아크 최상위(무조건)에 prime(&s) 호출이 없다」 |
| M3 | prime 이 Unknown 외 모든 판정을 적재 | KILLED — (i) 「생성 순간의 점유를 좌석 사실로 굳혔다」 + (ii) 실행 축 occupied |
| M4 | prime 이 Occupied 만 적재(Empty 미적재) | KILLED — (i) Unknown→Empty 대조군 + (ii) 실행 축 |
(ii) 실행 축의 M3·M4 적색은 생성 순간 자손이 있는 조건에서만 난다(환경 의존 킬) — 그 축의 역할은 불변식 고정이고, 배선 킬은 M1·M2 가 진다.

### 12-4. 통합 검증(r6 · HEAD 1e9cbbb5)
CI 3명령은 release.yml 356·357·361 글자 그대로를 bash 로 · 빈 CYS_PACK_DIR · 직렬 · **CI 유사 로그인 조건**(`SHELL=/bin/bash` + 가짜 HOME
`.bash_profile`=`sleep 0.3` — 종전 시험이 3/3 적색이던 조건). 건강 검체는 §8-5 격리 env 한 줄. 12:48:38~13:03:59 · 단계마다 dirty=0.
| 단계 | rc | 초 | 건수 |
|---|---|---|---|
| cargo test --bin cysd -- --test-threads=1 --skip hwmon:: | 0 | 139 | 1033 pass · 0 fail · 1 ignored |
| cargo test --lib -- --test-threads=1 | 0 | 242 | 533 pass · 0 fail · 1 ignored |
| cargo test --bin cys -- --test-threads=1 | 0 | 104 | 280 pass · 0 fail |
| 전체 건강 검체(직렬 · 격리 env) | 0 | 436 | pass 149 · fail 0 · skip 1 · GREEN |
대상 2시험 반복: 실 HOME 3회 + 가짜 HOME 프로파일 3회 = 6/6 초록.

- 4군 축(좌석 판정 층): ③자가치유 — 제품 무변경(`git diff 5f8ea61c --stat` = handlers.rs 1파일 +70/−44 · 헝크 2개 모두 `mod tests {`(7804행) 아래 14916·14930행) · 좌석 캐시·틱·prime 거동 불변.
  ④전 pane 사망 — 좌석 생성·판정 경로 무변경 · 시험이 만드는 좌석은 비특권 1개(종전 master 최대 3개 → 승계 경로 미경유).
- 판단 1건(지시 밖 · master 확인 대상): 의미 층을 제품 seam(판정 주입) 신설 없이 기존 실 프로세스 단위 시험으로 두었다 — 그 시험은
  상태 대기로 전제를 세우므로 결정론이고 러너에서 이미 초록(8차)이며, seam 신설은 「제품 무접촉」과 충돌한다.
- 곁 관측 【미측정 · 제품 결함 아님】: D7⑴ prime 의 효과는 호스트 의존이다 — 로그인 프로파일이 생성 순간 자식을 띄우는 사용자 기계
  (예: `.zprofile` 의 명령 치환)에서는 prime 이 Unknown 을 남기고 §6 ⓐ 창 보류 + boot_node settle 이 덮는다(설계대로). 실사용자
  프로파일에서의 빈도는 재지 않았다.
- 재현 함정: 가짜 HOME 을 줄 때 `CARGO_HOME`·`RUSTUP_HOME` 을 실경로로 고정하지 않으면 cargo 가 툴체인을 못 찾아 **무출력으로** 끝난다
  (첫 시도 0줄 — 「안 쟀다」).

## 13. r7(master#715eb7ec · agy 6R REJECT = hetero-agy-d7-6.md) — 배선 구조 단언 강화
master 판정: P2 채택·강화(3점) · P3(a) 현행 유지 + 두 층 관계 주석 · P3(b) 시험 좌석 close 추가. 시험만 · 제품 무접촉.

| agy 6R | 조치(940ad8c7 · `d7_create_arc_primes_seat_cache_before_reply`) | 뮤턴트 |
|---|---|---|
| P2a 블록 주석 우회 | 줄 주석 제거 뒤 `/* … */` 구간을 줄바꿈만 남기고 제거(중첩 불요 — 생산부 `/*` 0건을 grep 으로 확인 · 닫히지 않은 `/*` 는 적색) | M5 호출을 `/*`·`*/` 두 줄로 감쌈 → KILLED(「prime 호출 자리가 정확히 하나가 아니다 · 0」) |
| P2b 조기 반환 우회 | `Ok(s) => {` 줄과 호출 줄 사이에 `return`·`Reply::` 를 담은 줄이 있으면 적색(줄 번호·원문 출력) | M6 호출 직전에 `if … { return Reply::Single(err_response(…)); }` → KILLED(「Ok(s) 와 prime 호출 사이에 조기 반환 후보가 있다(+66줄)」) |
| P2c 20칸 리터럴 취약 | 판정을 **trim 한 줄 == 호출문 전체** + **줄 인덱스**로 바꿈. 「무조건」은 상대 들여쓰기(호출 줄 = Ok 아크 꼬리 응답 줄과 같은 깊이) · 아크 경계도 상대 들여쓰기 | 대조군 C1 Ok 아크 본문 전체 +4칸 재들여쓰기 → 초록(포맷 둔감 확인) |
| P3a 실행 축 공허 통과 | 현행 유지 · 「실행 축은 prime 이 빠져도 unknown 이라 통과 — 배선은 구조 단언, Empty 적재는 의미 층이 진다」 주석 1줄 | — |
| P3b `exec sleep 30` 누수 | 시험 끝에 `close_surface_rpc(&daemon, sid, None, None)` + ok 단언(자식 트리 kill) | — |
기존 M1~M4 재실행: M1 호출 삭제 · M2 조건부 · M3 모든 판정 적재 · M4 Empty 미적재 → 전부 KILLED(귀속 패닉문 동일). 합계 **6/6 KILLED + 대조군 1 초록**.
측정 조건 = CI 유사 로그인 조건(`SHELL=/bin/bash` + 가짜 HOME `.bash_profile`=`sleep 0.3`) · 변이 적용 assert · 매회 백업 복원(cmp 확인) ·
**두 대상 시험이 실제로 돌았는지(2건) 계수 확인** — 첫 배터리는 zsh 에서 `$T` 가 쪼개지지 않아 0건 실행(전부 「ok · 0 passed」)이었고
그 결과는 버리고 bash 스크립트로 다시 쟀다(계수 가드 추가).

### 13-1. 통합 검증(r7 · HEAD 940ad8c7)
CI 유사 로그인 조건(`SHELL=/bin/bash` + 가짜 HOME 프로파일) · bash · 빈 CYS_PACK_DIR · 직렬 · 13:15:45~13:24:57 · 단계마다 dirty=0.
| 단계 | rc | 초 | 건수 |
|---|---|---|---|
| cargo test --bin cysd -- --test-threads=1 --skip hwmon:: | 0 | 130 | 1033 pass · 0 fail · 1 ignored |
| 전체 건강 검체(직렬 · 격리 env) | 0 | 422 | pass 149 · fail 0 · skip 1 · GREEN |
(lib·cys 는 r7 이 cysd 시험 모듈만 바꿔 master 지시 게이트에서 빠짐 — r6 §12-4 값이 이 트리의 해당 부분과 동일)
- 4군 축: ③④ — 제품 무변경(헝크는 전부 `mod tests` 안) · 좌석 판정 층 거동 불변. 시험이 만든 비특권 좌석 1개는 끝에 닫는다(종전: 30초 잔류).
- 판단(지시 밖) 1건: 조기 반환 검사의 대상 문자열을 `return`·`Reply::` 두 개로 한정했다(master 지시 그대로). `?` 는 이 아크를 품은 `dispatch` 가 `Reply` 를 돌려주므로(handlers.rs:2626) 컴파일되지 않는다. `break`·`continue` 우회는 검사하지 않았다(잔여).
