# HANDOFF — TICKET=cysr-1115-reassemble (worker-integ2 · surface:2092 · 2026-11-16 06:05~)

> 가지 `integ/1115-r2`(작업트리 `~/axdev/.wt/cys-1115-integ2`) · 기준 = 태그 `v1.1.14`(270e3e21) · push 0 · 태그 0 · 판 올림 0 · 조각 가지 무변경.
> 표기: 「관측」 = 이번에 명령으로 잰 것 · 「판독」 = 코드를 읽고 판단한 것(실행 근거 없음).

## 0. 한눈 요약

- **조각 8개 전부 들어감**: dev-opt1(맨 앞) → smalls 4커밋 · 상담소 4커밋(집어 올림) → tabs → 큐 배달 → 윈 훅 시간 기록 → T3 → agy(맨 뒤). 그 위 시험 커밋 1개(`test(integ)`).
- **섞임 0**(관측): 빠지는 가지 5개(t1·a1a3·winhook·smalls 나머지·caller-r3)와 patch-id 겹침 0 · ② 1차판 ee66148b·d604dd9d 는 조상 아님 · ② 1차판 대표 글자 7종이 합친 나무에 0건(d604dd9d 에는 있음 = 양성 대조) · 병합 6번 모두 「자동 병합이 만든 나무」와 같고 다른 곳은 state.rs 충돌 덩이 하나뿐.
- **충돌 1덩이**: agy × T3 `src/bin/cysd/state.rs`(1차의 C3 와 같은 모양 · rerere 가 1차 해법을 재생 · 뜻 확인함).
- **B(큐 배달 × agy)**: 「버린 항목」에는 재전송·재검사·만료 알림이 **붙지 않고 큐도 멈추지 않는다**(관측 · 시험 커밋). 그러나 **이미 배달된 항목**의 Return 재전송은 agy 문을 보지 않는다 — 문이 닫힌 agy 좌석에 Return 을 다시 쓰는 것을 임시 탐침으로 **관측**했다 → 【결정필요】(§4-3). 고치지 않았다.
- **전체 시험**: 새로 붉은 것 = 조각 단독 결함 3(T3 census · tabs·agy 의 공개 secret-scan 적발) + 흔들림 1(조각 무관 파일). 통합 결함 0. 화면 게이트 7종 통과 수 = 1차·tabs 기록과 같음. 1차의 통합 결함 I1~I3 고침은 **필요 없음**(호출자 판정 조각이 빠져서 · agy 수용 34/34 가 `--operator` 없이 PASS).

## 1. 조각 표(06:06 재측정 · 갈림점 전부 270e3e21)

| 조각 | 가지 | 머리 | 합친 커밋(integ/1115-r2) | 들어온 파일 |
|---|---|---|---|---|
| dev-opt1 스택 여유 | fix/1115-dev-opt1-stack-budget | 227dc123 | 86f3ea47(병합) | — |
| smalls ①④⑦⑤⑥ | fix/1115-smalls 의 4커밋 | 7876d2d3 · efad92ec · 322a606c · 43d9d13a | baed6914 · ff9fa02e · 38c09d43 · 9bbedf7c(`cherry-pick -x`) | 2·4·3·2 |
| 상담소 안내문 | fix/1115-counsel-notice 의 4커밋 | 8599d13b · c7ea898e · 94ff0a63 · 91151527 | ebf7f465 · f256af86 · f4b05cc6 · 8bc11074(`cherry-pick -x`) | 8·1·7·3 |
| 탭 + 왼쪽 좌석 막대 | feat/tabs-sidebar | cc460b17 | 9baa1633(병합) | 61 |
| 큐 배달 접힘 수리 | fix/cysr-queued-paste-submit | 247d571c | 9bc1a3ec(병합) | 11 |
| 윈 훅 실패 시간 기록 | fix/cysr-win-boot-hook-timeout-code | d45de957 | 505629b5(병합) | **0**(smalls ④ 와 같은 변경 · 관측) |
| seatkeep-t3(노브 끔 · T2 포함) | feat/seatkeep-t3 | e568aa6c | c0736dfb(병합) | 34 |
| agy 자동 실행 문 | fix/agy-policy-exposure | 09df73fa | f41a0024(병합 · 충돌 1) | 80 |
| (통합 시험) | — | — | **3d2d4e88** `test(integ)` 큐 배달 × agy 순서 | 1 |

- 머리 = **3d2d4e88**(그 위에 이 인계서 커밋) · v1.1.14 위 167커밋 · 200파일 +38,566/−368(3d2d4e88 직전 f41a0024 기준).
- 집어 올린 8커밋은 원본과 **patch-id 8/8 같음**, 상담소 4커밋 묶음의 차이(`d604dd9d..91151527`)는 집어 올린 묶음 차이(`9bbedf7c..8bc11074`)와 바이트 같음(관측).
- 순서는 브리프 그대로(1차 인계서에 다른 순서를 강제할 까닭 없음 — 1차 순서의 까닭 3 「agy 맨 뒤」는 지킴).
- 머리 6개(227dc123 cc460b17 247d571c d45de957 e568aa6c 09df73fa)는 전부 `integ/1115-r2` 의 조상(관측 `merge-base --is-ancestor`).

## 2. 충돌 기록

쌍별 예측(`git merge-tree --write-tree` · 7개 조각 21쌍 · 상담소는 91151527 로 셈): 충돌 = **agy × t3 `state.rs` 1쌍뿐**. 실제 차례 병합도 같음.

| # | 병합 | 파일 · 자리 | 두 조각 | 푼 방법 | 두 쪽 뜻을 다 살렸다는 근거 |
|---|---|---|---|---|---|
| R1 | agy(f41a0024) | `src/bin/cysd/state.rs` `create_surface_with_env` 의 PTY fd 캐시 줄(8091행대) | t3: `pty_master_fd = spawned.foreground_fd()` + `#[cfg(macos)] seat_link = spawned.link()` / agy: 옛 줄 `pair.master.as_raw_fd()…` + `cmd_for_kind = cmd.clone()` | rerere 가 1차 C3 해법 재생 = t3 두 줄 + agy 의 `cmd_for_kind` 줄(옛 `pair.master` 줄은 t3 가 없앤 변수라 버림) | ① 자동 병합 나무와의 차이가 이 덩이뿐(아래 §3-③ 출력) ② `cmd` 는 함수 머리(7839행)~이 줄 사이에서 `&cmd` 빌림 2곳뿐이고 처음 소비는 아래 `cmd: cmd.unwrap_or_else(..)`(8103행) → agy 의도(셸 기본값 채우기 **전** cmd 로 좌석 종류 판정) 유지(판독) ③ 뮤턴트 A-M1(`agy_kind` → false) 붉음 · cysd 전체 초록(t3 쪽 fd 캐시 시험 포함)(관측 §6) |

1차의 C1·C2·C4·C5·C6·C7 은 상대 조각(a1a3·caller·t1)이 빠져서 생기지 않음(관측: 쌍별·차례 모두 0).

## 3. 섞임 0 증명(관측 · 출력 원문)

① 빠지는 가지와 같은 변경이 있는가 — 범위 `v1.1.14..integ/1115-r2` 의 비병합 커밋 patch-id 대 각 빠지는 가지(관측 f41a0024):
```
feat/seatkeep-t1 고유커밋=67 같은패치=0
feat/1115-a1-a3 고유커밋=30 같은패치=0
fix/1115-win-hook-launcher 고유커밋=25 같은패치=0
fix/1115-smalls 고유커밋=15 같은패치=4      ← 실을 4개(7876d2d3·efad92ec·322a606c·43d9d13a)뿐
feat/1115-caller-r3 고유커밋=52 같은패치=0   (caller-check·mid·묘비·r3·창 관문을 다 품은 가지)
ee66148b 없음(조상 아님) · d604dd9d 없음(조상 아님) · 두 커밋의 patch-id 범위 안 0건
```
② ② 1차판 대표 글자(`git show ee66148b d604dd9d` 에서 뽑음) — `git grep -c` 합(합친 나무 / v1.1.14 / d604dd9d):
```
reviewer_seat_blocks_autostart   0 / 0 / 6
REVIEWER_NO_AUTOSTART_NOTE       0 / 0 / 3
autostart_blocked_in_seat        0 / 0 / 11
CODEX_SANDBOX_NETWORK_DISABLED   0 / 0 / 2     (CODEX_SANDBOX 낱말 자체도 합친 나무 0)
s1115_reviewer_seat_blocks       0 / 0 / 1
s1115_connect_reviewer_gate      0 / 0 / 1
s1115_codex_sandbox_blocks       0 / 0 / 1
```
   다른 빠지는 조각 표지(합친 나무 / v1.1.14 / 조각): session_lease 0/0/112 · CYS_SESSION_LEASE 0/0/18 · arm_operator_mark 0/0/9 · privileged_create_gate 0/0/5 · tombstone_denied 0/0/202 · a3_approval_hook_tests 0/0/12 · modal_outside_unmarked 0/0/8.
③ 조각 밖 변경 = 충돌 해소 줄뿐 — 병합마다 「그 병합의 두 부모를 `git merge-tree --write-tree` 로 자동 병합한 나무」와 실제 병합 나무 비교:
```
86f3ea47 dev-opt1 · 9baa1633 tabs · 9bc1a3ec 큐 배달 · 505629b5 윈훅 · c0736dfb t3 = 차이 파일 없음
f41a0024 agy = src/bin/cysd/state.rs 뿐 — 차이 = 충돌 표식 3줄 삭제 + 옛 `pair.master` 줄 1줄 삭제(나머지 줄은 양쪽 그대로)
```
   파일 단위(f41a0024): 바뀐 200파일 = 조각 합집합 200 · 조각 밖 파일 0 · 한 조각만 바꾼 185파일은 조각 머리와 내용(blob) 같음 · 여러 조각이 바꾼 15파일(Cargo.lock·Cargo.toml·USER-MANUAL.md·팩 시험 3·_lib.sh·src-tauri/main.rs·cys.rs·governance.rs·handlers.rs·state.rs·lib.rs·main.ts·toastaxis.test.ts)은 위 ③ 으로 자동 병합 그대로임을 보임.
   (브리프의 `git diff <조각 머리>...integ/1115-r2 --stat` 는 다른 조각 변경이 전부 섞여 나와 판정에 못 써 위 두 가지로 바꿨다 — 지시 없이 내린 판단 1건.)
   재현: 스크립트 `/private/tmp/claude-501/-Users-oogisoogi-axdev--wt-cys-1115-integ/a28a3eeb-ef91-4e4c-9396-c1c0d24bdf0d/scratchpad/pidcheck.sh`·`filecheck.py`(스크래치 · 재부팅 시 사라짐 — 명령 뼈대는 위와 같음).

## 4. B — 뜻 충돌 점검

### 4-1. 큐 배달 수리 × agy 문 — 「버린 항목」(VERIFY.md 의 물음 그대로)
- 코드(합친 판): `governance.rs` `deliver_head_locked`(12851행) 머리에서 `drop_stale_launch_lines(..) + drop_agy_door_closed(..)`(12874행)로 큐에서 **빼고**, 머리가 바뀌었으면 그 틱은 `None`(12879행). 버린 항목은 `record_queue_tombstones`(묘비 · 사유 `agy_consumer_policy`) + `queue.dropped` 1건(4631~4635행).
- 큐 배달 수리의 제출 확인 기록은 **쓰기 결판 `WrittenSubmitted` 에서만** 선다: `settle_queue_write` → `arm_queue_submit_check(..)`(12161행). 버린 항목은 인계·쓰기가 없으므로 기록이 서지 않는다 → 재전송(`recheck_queue_submits` 7962행)·재검사 대상이 아니다.
- 만료 유실 알림(`queue.expired` → `ui/src/main.ts` 11058행 `noteQueueExpired`)의 재료는 만료 큐다. 버린 항목은 활성 큐에서 빠져 만료 큐로 가지 않는다.
- 큐 멈춤: 큐가 비면 `queue_blocked = None`(4629행) · 남은 항목은 다음 틱에 머리로 나간다.
- **시험(커밋 3d2d4e88)** `governance::tests::integ_1115_agy_door_drop_gets_no_submit_check_and_does_not_stall_queue` — 닫힌 문의 agy 좌석 큐 = 기계 2 + 사람 자판 1 → 첫 틱 배달 0 · 남은 것 = 사람 자판 1 · 제출 확인 기록 없음 · `recheck_queue_submit_one` = "none" · 만료 큐·`queue.expired`·`queue.delivered`·재전송 계열 이벤트 0 · `queue.dropped` 1건(사유 agy) · 둘째 틱에 사람 자판 항목 배달. 초록(관측) · 뮤턴트 I-M1(폐기 호출 → 0) 붉음(관측).
- 답: **버린 항목에는 재전송·재검사가 붙지 않고, 그 좌석 큐가 멈추지 않으며, 유실 알림이 거짓으로 뜨지 않는다**(코드 + 시험 관측).

### 4-2. tabs × 큐 배달 · T3 × 큐 배달 — 판독 문제 없음
- tabs × 큐 배달(`state.rs`·`main.ts`·`toastaxis.test.ts`): 글자 충돌 0 · tabs 의 state.rs 변경(좌석 묶음 `group` · 부모 판독)과 큐 배달의 `InjectTrack.submit_check` 는 서로 다른 칸. main.ts 의 만료 알림(`noteQueueExpired`)은 tabs 구조 위에서 tsc 초록(음성 대조 rc 1 확인) · `toastaxis.test.ts` 포함 bun 3451/0 · 화면 게이트 7종 PASS(관측). 실제 앱 창에서 토스트가 탭 구조 안 제자리에 뜨는지는 **안 봄**(헤드리스 게이트에 그 장면 없음).
- T3 × 큐 배달(`governance.rs`·`state.rs`): T3 는 좌석 프로세스 손잡이(종료·전경 질의)만 옮기고 `write_tx`·`inject_track`·`pending_queue` 를 건드리지 않음 · 큐 배달은 PTY 손잡이·전경 fd 를 건드리지 않음(관측: 두 diff 에서 상대 쪽 낱말 0) · 노브 끔이라 전경 질의는 같은 `tcgetpgrp(캐시 fd)`. 큐 배달 시험 `qps_*` 14건 · cysd 전체 초록(관측).

### 4-3. 큐 배달의 Return 재전송은 agy 좌석 문을 보지 않는다(관측) — **결정 = A(master · 11-16 07:4x · master#65cc8eea)**

- **결정 = A**: 그대로 싣고 알려진 한계 1줄 「agy 문을 연 동안 이미 입력줄에 들어간 본문의 Return 마무리는 문이 닫힌 뒤에도 한 번 나갈 수 있다 · 창 ≈35초」 → 1.1.16 에서 고침. 까닭(master) = 그 본문은 문이 열렸을 때 정당하게 배달된 것이고 새 본문이 들어가는 길이 아니다 · 통합에서 고치면 큐 배달 codex 4R 판정이 무효.

- **무엇**: 큐 배달 수리가 더한 데몬 내부 쓰기(먹힌 Return 재전송 · `recheck_queue_submit_one` 의 `Resend` → `WriteReq::SubmitAfterGap`)는 판정에 agy 문을 넣지 않는다 — 쓰기 직전 거부 탐침 `queue_retry_cancel_probe`(7917행)의 조건에도 문 상태가 없다. agy 문은 「적재 뒤 문이 닫혔으면 배달하지 않는다」(배달 직전 재판정 `drop_agy_door_closed`)인데, 이 새 쓰기 길은 그 재판정을 지나지 않는다.
- **관측(임시 탐침 · 커밋 안 함)**: 닫힌 문(격리 HOME) · 좌석 메타 (`gemini`,`agy`) = 출하 어댑터 = agy · 마커 `>` · 기계 본문 기록 + 제출 확인 기록 · 입력줄 `> [Pasted text #9 +3 lines]` → 2.1초 틱 = `resent` · PTY 쓰기 +1 · `queue.submit_retried` 1건. (정정: 앞서 내 판독 「agy 좌석은 마커가 없어 재전송 불가」는 틀렸다 — 출하 `gemini` 어댑터가 agy 이고 마커가 있다.)
- **언제 생기나(판독)**: 기록은 쓰기 결판에서만 서므로 ⑴ 문이 **열린** 동안 기계 항목이 agy 좌석에 배달되고 그 Return 이 먹힌 뒤 ~35초(재시도 간격 2·4·8초 + 틱) 안에 문을 닫은 경우 ⑵ 인계 중(쓰는 중)에 문이 닫힌 경우. 사람 자판 출처(`send_human`) 항목은 문이 닫혀도 배달되는 설계라 그 Return 재전송은 문 정책과 어긋나지 않는다. 문은 기본 닫힘 · 여는 것은 앱 화면의 명시 조작뿐이라 창은 좁다.
- **부기(판독 · 큐 배달 조각이 만든 것 아님)**: ⑵ 의 경우 agy 문 폐기가 `inject_reserved` 검사보다 앞이라 인계 중인 항목을 큐에서 빼 묘비를 남기고, 곧 쓰기 결판이 같은 항목에 배달 영수증·`queue.delivered` 를 남긴다(같은 항목에 묘비와 배달이 둘 다). 옛 기동 줄 폐기(v1.1.14 부터 같은 자리)와 같은 모양 — agy × 기존 배달 길의 일.
- 선택지:
  - **A(권고) 그대로 싣고 「알려진 한계」 1줄** — 근거: 문을 연 동안 이미 입력줄에 들어간 본문의 제출을 마무리하는 Return 이고(새 글을 넣지 않음), 창이 ~35초로 좁고, 두 조각 다 바깥 판정이 끝났다(뜻을 바꾸면 판정 무효). 귀결: 1.1.15 에 이 틈이 남음 · 1.1.16 에서 고침. 단점: agy 문 설명(「문이 닫히면 자동 입력 0」)과 글자로는 어긋난다.
  - B 통합 가지에서 고침 — 재검사 단계에서 `agy_door_seat_closed` ∧ 기계 출처면 기록을 닫음(출처를 `SubmitCheck` 에 실어야 함). 귀결: 큐 배달 codex 4R ACCEPT 가 무효 → 바깥 검토 1R 필요(11-18 동결과 부딪힘).
  - C 큐 배달 조각 좌석에서 고친 새 머리를 받아 다시 합침 — B 와 같은 검토 비용 + 다시 모으기 1회.
- **미결 시 막히는 것**: 없음(판 올림 전 결정이면 됨). A 면 설명서·출시 안내 1줄이 남은 일에 더해진다.

## 5. 격리 방법(시작 전 1줄 기록 · 관측)

- 시험 env = `env -i` + HOME·TMPDIR = `/private/tmp/claude-501/r2/{h,t}-<이름>`(짧은 경로) · `CYS_*`/`XDG_*` 0개 · `DISABLE_AUTOUPDATER=1` · PATH = cargo·bun·시스템 폴더만(/usr/local/bin 없음) · `CARGO_TARGET_DIR` = 이 작업트리 `target`.
- 소켓: 시험 기본 소켓 = `<격리 HOME>/.local/state/cys/cys.sock`(`cys::default_socket_path` = `dirs::state_dir()` 없으면 HOME) ≠ 라이브 `~/.local/state/cys/cys.sock`(mtime 11-07 01:46 · 끝난 뒤도 같음). 내 경로 아래 남은 cysd·cys-seatkeep 프로세스 0(관측).
- `readlink ~/.local/bin/claude` = 시작·끝 모두 `…/claude/versions/2.1.325`.
- ⚠함정(내 실수 · 정직 기록): 처음엔 TMPDIR 을 긴 스크래치 경로로 줘서 cys 시험 4건이 `path must be shorter than SUN_LEN`(유닉스 소켓 경로 104자 제한)으로 붉었다 → 짧은 경로로 다시 돌려 4건 초록(§6 의 cys 숫자는 다시 돈 값). 첫 cysd 실행은 같은 까닭으로 내가 중간에 멈췄다(내 pgid 만).

## 6. C — 합친 판 전체 시험(머리 3d2d4e88 · 기준선 = v1.1.14 · 1차 리허설 값은 1차 인계서 §6)

| 대상 | 합친 판 r2 | 1차 리허설 합친 판(고친 뒤) | 기준선 v1.1.14(1차 §6-3 기록) |
|---|---|---|---|
| 빌드 `cargo build --bins` + `test --no-run --bins --lib --tests` | rc 0 | rc 0 | — |
| UI 번들 `sh ui/build.sh` | rc 0 | rc 0 | — |
| tsc `bun x --package typescript@7.0.2 tsc -p tsconfig.check.json` | rc 0 · **음성 대조**(타입 오류 1줄 심음) rc 1 TS2322 | rc 0(⚠아래) | — |
| bun test(ui) | **3451 pass · 88 skip · 0 fail** | 3445 / 0 | 3329 · 88 skip · 0(상담소 보고서) |
| lib | 1237 · **1** · 2 | 1259 · 1 → 0(census 고침 뒤) | 1203 · 0 · 2 |
| bin cys | **761 · 0** · 2 | 797 · 0 | 755 · 1 · 1 |
| bin cysd | 3271 · **1** · 17 | 3304 · 0 · 18 | 3225 · 2 · 15 |
| bin cys-seatkeep | 49 · 0 | 34 · 0 | (없음) |
| tests/*.rs | hidden_seat_screen 1/0 · rotate_autorestore_hold 11/0 · seat_group **1/0** · update_drainhold_e2e 4/0 · win_job_exit 0 · win_pack_swap 0 | 8개 전부 초록(고친 뒤) | rotate 11/0 · drainhold 4/0 · win 0 |
| 화면 게이트 7종 | race 108/0 · focus 72/0 · seatrows 75/0 · pillar 77/0 · seatgroup 8/0 · rolereuse 11/0 · stty 7/0 — 전부 PASS | 같은 수 | — |
| agy 수용 하네스 `acceptance.py` | **종합 PASS 34/34**(`--operator` 없이) | 34/34(I2 고친 뒤) | — |
| 팩 파이썬 | computer_control 112 OK · agents_notes_personal_hooks OK · dept_chat_inject_timeout 3 OK · hook_fail_log 11 OK · hook_fail_timing 10 OK · javis_counsel 118 OK(skip 3) · agy_door 20 OK · agy_door_phoenix_loop OK | 같은 묶음 rc 0 | — |
| health `run_bootstrap_health.py --json` | 166 PASS · **3 FAIL** · 1 SKIP / 170 | (1차 미실행) | 아래 |

실패 **이름 + 사유** 대조:

| 실패 이름 | r2 | 기준선 | 판정 |
|---|---|---|---|
| lib `spawn_policy_tests::raw_command_new_census_is_frozen` | 붉음 · 사유 = `src/bin/cys-seatkeep/main.rs` 실측 10 ≠ 동결 2 | 초록 | **조각 단독 결함 CONFIRMED(T3)** — T3 머리 e568aa6c 단독 작업트리에서 같은 시험이 같은 사유(10 ≠ 2)로 붉음(관측) · 합친 판의 그 파일은 T3 머리와 바이트 같음. 1차 때 고친 fcc6896f(동결 2) 뒤의 T3 커밋 5개(d9f8f44a · b5ee4392 · 08bc92d7 · 08f6d1dd · f95cd5d4 = fix1~r4)가 그 파일에 `Command::new` 를 8개 더함(`git log -S` 관측). 고칠 곳 = T3 좌석(동결표 갱신 또는 hidden_command) |
| cysd `pending_requests::tests::exact_plan_roundtrip_and_recovered_join_never_make_a_permit` | 전체 실행에서 붉음 · 사유 `Err(Locked)`(1639행 재열기) | (1차 기록에 없음) | **흔들림** — 단독 재실행 3/3 초록 · 모듈 99/0(관측) · 이 파일은 어느 조각도 안 바꿈(v1.1.14 그대로). 부하 중 잠금 경합으로 봄(판독) |
| health `H-SECRET-1`(공개 secret-scan) | 붉음 · `scripts/secret-scan.sh --all` 적발 75건 → **2차에서 0건으로 고침(62f51ef0 · §12-1)** | v1.1.14 작업트리에서 rc 0 · 적발 0(관측) | **조각 단독 결함 CONFIRMED(tabs · agy · 상담소)** — ⚠정정: 1차 보고는 tabs·agy 만 적었으나 상담소 2파일(5건)도 있었다(가림 표시 줄만 셌던 내 계수 실수 · §12-1 표가 정본) — tabs 머리 단독 rc 1 · 적발 50(`docs/CODEX-R1-tabs-sidebar.txt`·`docs/CODEX-R1-2d-tabs-sidebar.txt`·`docs/HANDOFF-tabs-sidebar.md` 등 개인 경로) · agy 머리 단독 rc 1 · 적발 11(`src/agy_door.rs` 시험 문자열 `…/Library/Application Support/claude` 꼴 7 + .md 3 + WIN-PATH .py 1). ⚠**발행 차단 게이트**다 — 판 올림 전에 두 조각 좌석이 고쳐야 한다 |
| health `H-CLT-1` · `H-CLT-2` | 붉음 · 사유 = 프리루드가 `/Applications/cys.app/…/python3` 를 고름 | **같은 사유 글자 그대로 붉음**(v1.1.14 작업트리 `--only H-CLT-1,H-CLT-2` 관측) | 기존 결함(이 기계 환경) · agy 인계서 46행 「기존 결함」과 같음 |
| health `H-WIN-11` | skip | — | 맥에서는 skip(윈 CI 몫) |
| cys `b360_r3_k12…` 외 3건(첫 실행) | 첫 실행만 붉음 · `SUN_LEN` | — | **내 시험 환경 탓** — 짧은 TMPDIR 로 다시 돌려 761/0(§5) |
| (기준선만 붉던) `dbg_r12_*` 3건 | 초록 | 붉음 | 1차와 같음 — 회귀 아님 |

- 새 적색(기준선 대비) = **3종**(census · H-SECRET-1 · 흔들림 1) — 셋 다 통합이 만든 것이 아님(앞 둘 = 조각 단독 · 뒤 하나 = 조각 무관 파일).
- 1차 통합 결함 I1(caller 핀 창) · I2(agy 하네스 `--operator`) · I3(seat_group owner_token) = **이 구성에서 해당 없음**(관측: cys 761/0 · acceptance 34/34 · seat_group 1/0 — 고침 커밋 없이 초록).
- ⚠1차 리허설의 tsc 「rc 0」은 거짓 초록이었을 수 있다(판독 · 1차 작업트리 `ui/node_modules` 에 typescript 없음 → `bunx tsc` 는 다른 `tsc` 패키지를 받아 rc 0 · 장기기억 bunx-tsc-wrong-package-false-green). 이번 값은 typescript@7.0.2 지정 + 음성 대조로 잰 것.

### 6-1. 상담소 조각(② 1차판 없는 나무에서 처음 잼)

| 무엇 | 결과(관측) |
|---|---|
| `test_javis_counsel.py` | Ran 118 · OK(skip 3) — 조각 보고서 ⑤ 뒤 값과 같음 |
| `bun test src/counselwiring.test.ts` | 20 pass · 0 fail |
| 뮤턴트 M1 `daily_body` 가 `since` 칸을 더 보냄 | **붉음** — `Lists differ … 'payload.since'` 외 1(실패 2) |
| 뮤턴트 M2 안내문에서 「생긴 시각」 삭제 | **붉음** — `'생긴 시각' not found …` · 도움말 문장 불일치(실패 2) |
| 뮤턴트 M3 화면 `REPORT_NOTICE` 에 띄어쓰기 1칸 | **붉음** — bun `(fail) 상담소 끄기/켜기 · 첫 안내 > 안내문 = 팩 HELP_NOTICE 와 글자 그대로…` 19 pass · 1 fail |

(뮤턴트는 같은 머리의 별도 작업트리 `~/axdev/.wt/cys-1115-integ2-mut`(detached)에서 · 매번 원본 바이트 복원 확인 · `git status` 깨끗.)

### 6-2. 조각 자기 뮤턴트(합친 판에서도 그 조각의 그물이 사는가 · 관측 · 전부 원복 확인)

| # | 조각 · 바꾼 것 | 지킨 시험 | 결과 |
|---|---|---|---|
| Q-M1 | 큐 배달 · 결판의 `arm_queue_submit_check` 호출 제거 | `send_settle_tests::qps_queue_delivery_arms_submit_check` | 붉음(13/1) |
| Q-M2 | 큐 배달 · 재시도 상한 `>=` → `>` | `qps_submit_check_step_table` · `qps_giveup_checks_transcript_first` · `qps_swallowed_queue_return_retried_three_times_then_alerts_once` | 붉음(11/3) |
| Q-M3 | 큐 배달 · 거부 탐침의 기록 결속·승인 판정 제거 | `qps_handed_retry_cr_not_written_after_approval_rose` · `…_after_record_closed` · `qps_retry_cancel_probe_refuses_on_each_broken_premise` | 붉음(11/3) |
| A-M1 | agy · state.rs `agy_kind` → false(충돌 R1 의 agy 쪽) | lib `agy_door::tests::every_other_entry_is_gated_source_pin` | 붉음(33/1) |
| A-M3 | agy · new-surface 문 줄 삭제 | cys `agy_door_wiring_tests::restore_new_surface_and_detect_are_gated` | 붉음(2/1) |
| A-M6 | agy · phoenix `need` 의 agy 거름 삭제 | `test_agy_door_phoenix_loop.py` P1·P2 | 붉음 · ⚠`test_agy_door.py` 로는 살아남음(1차와 같음) |
| I-M1 | (통합 시험) agy 폐기 호출 → 0 | `integ_1115_agy_door_drop_gets_no_submit_check_and_does_not_stall_queue` | 붉음 |

## 7. master 가 다시 돌릴 명령(깨끗한 스냅숏 · 격리 env)

```sh
W=~/axdev/.wt/cys-1115-integ2; cd $W && git log -1 --format=%h        # 기대: 인계서 커밋(그 아래 3d2d4e88)
# 격리 env 틀: env -i HOME=<짧은 임시 폴더> TMPDIR=<짧은 임시 폴더> PATH=$HOME/.cargo/bin:$HOME/.bun/bin:/usr/bin:/bin \
#   CARGO_HOME=$HOME/.cargo RUSTUP_HOME=$HOME/.rustup DISABLE_AUTOUPDATER=1 <명령>   (⚠ TMPDIR 이 길면 SUN_LEN 적색)
cargo build --bins && cargo test --lib -- --test-threads=4          # 기대 실패 = census 1(T3 몫)
cargo test --bin cys -- --test-threads=4                            # 기대 761/0
cargo test --bin cysd -- --test-threads=4                           # 기대 0 실패(흔들림 pending_requests 1건 가능 → 단독 재실행)
cargo test --bin cys-seatkeep && for t in hidden_seat_screen rotate_autorestore_hold seat_group update_drainhold_e2e; do cargo test --test $t; done
cargo test --bin cysd integ_1115_agy_door_drop                       # B 시험
(cd ui && bun install --frozen-lockfile && sh build.sh && bun test && bun x --package typescript@7.0.2 tsc -p tsconfig.check.json)
python3 docs/agy-door-evidence/acceptance.py; git checkout -- docs/agy-door-evidence/   # 기대 종합 PASS 34/34
python3 cysjavis-pack/bin/tests/run_bootstrap_health.py --json      # 기대 FAIL = H-SECRET-1(tabs·agy 몫) · H-CLT-1/2(기존)
# 화면 게이트: CHROME_PATH=<chrome-headless-shell> <playwright python3> ui/e2e/{race,focus,seatrows,pillar,seatgroup,rolereuse,stty}_gate.py
#   (focus_gate 는 docs/evidence-tabs-sidebar/948-focus 에 캡처를 쓴다 → 끝나면 옮기거나 지운다)
```

## 8. 윈 실기에서 볼 것

1. 큐 배달 W1~W7 — 원문 = 이 가지 `REPORT.md` 193~199행(W1 수리 전 판 현장 조건 재현 · W2 같은 조건 수리판 · W3 오너 초안 보존 · W4 포기 경로 · W5 만료 알림 토스트+배너 · W6 윈 CI `qps_*` · W7 모형 e2e 이식은 선택).
2. 윈 컴파일·윈 CI — `tests/win_job_exit.rs`·`win_pack_swap.rs` 는 맥에서 0건(맥 결과 = 실행 0). 모든 조각 공통 미확인(1차와 같음).
3. 윈 훅 실패 기록의 `took`·`dstart` 칸(smalls ④ = 윈 훅 rc124 원인 가름 계측)이 실제 윈 훅 실패 줄에 찍히는지.
4. health `H-WIN-11`(맥 skip).
5. (§4-3 를 A 로 정하면) 해당 없음 — 윈·맥 공통 동작.

## 9. 판 올림 전에 남은 일

1. **T3 census 동결표**(lib `raw_command_new_census_is_frozen`) — §12-2 【결정필요】 답에 따라.
2. ~~공개 secret-scan 적발~~ → 2차에서 고침(62f51ef0 · §12-1). 조각 가지 자신은 그대로 붉다 — 조각 가지를 따로 발행·병합할 일이 생기면 같은 고침이 필요.
3. §4-3 = A 확정 → 설명서·출시 안내에 알려진 한계 1줄.
4. 1~2 의 새 머리가 오면 이 가지에 `--no-ff` 로 덧붙이고 §7 재실행(1차 인계서 C7 처럼 같은 이름 새 파일이 둘이면 add/add — 차례 병합으로 미리 볼 것).
5. 윈 실기(§8) · master 깨끗한 스냅숏 재검증 · 판 번호·서명·발행(정책 §0 · 이 좌석 범위 밖).

## 10. 함정

- **TMPDIR·HOME 은 짧게** — 유닉스 소켓 경로 104자 제한. 스크래치 폴더(약 120자)를 그대로 주면 cys·cysd 시험이 `SUN_LEN` 으로 붉다.
- 내 셸 스크립트에서 `echo "$(date) rc=$?"` 는 date 의 rc 를 찍는다 — rc 는 먼저 변수에 받아라(이번 1차 사슬의 `rc=0` 표기는 무효였고 결과는 로그의 `test result` 로만 읽었다).
- `bunx tsc` 거짓 초록 — `--package typescript@7.0.2` + 음성 대조. 새 작업트리는 `bun install --frozen-lockfile` 먼저.
- `focus_gate.py` 는 캡처 폴더 인자를 안 받아 `docs/evidence-tabs-sidebar/948-focus` 에 쓴다(커밋 전 치움 · 이번엔 스크래치로 옮김).
- `acceptance.py` 는 `docs/agy-door-evidence/acceptance-result.json` 을 덮어쓴다 → 실행 뒤 `git checkout --`.
- 팩 파일 뮤턴트를 본 작업트리에서 cargo 와 동시에 돌리지 말 것(build.rs 가 팩을 git ls-files 로 임베드 → 뮤턴트가 바이너리에 실릴 수 있음) — 이번엔 별도 작업트리에서 함.
- rerere 공용 캐시(`~/cys-terminal-src/.git/rr-cache`)가 1차 C3 해법을 자동 재생한다 — 재생 결과는 반드시 §3-③ 식으로 자동 병합 나무와 대조해 덩이 1개뿐임을 볼 것.
- 남이 띄운 headless 크롬(pid 78754 계열 · 1차 인계서에도 있음)은 손대지 않음.

## 11. 정리 상태

- 내가 만든 임시 작업트리: `~/axdev/.wt/cys-1115-integ2-mut`(detached 3d2d4e88 · 상담소·agy 팩 뮤턴트용) · `/private/tmp/claude-501/r2/wt-{base,tabs,agy,t3}`(기준선·조각 단독 대조용 · detached · wt-t3 에 target 있음). 모두 커밋 0 — master 가 `git worktree remove --force <경로>` 로 치워도 잃는 것 없음(지우지 않고 남겨 둠 · 재검증에 쓸 수 있게).
- `WORKER_TODO.cysr-1115-reassemble.md` = 커밋 안 함(브리프).
- 증류 2건 = 저장소 장기기억(`~/.claude-acct2/projects/-Users-oogisoogi-cys-terminal-src/memory/`)에 기록: `test-env-tmpdir-length-sun-len` · `agy-seat-is-gemini-adapter-has-marker`(팩 `~/.cys/pack` 은 브리프상 손대지 않아 팩 기억 도구는 안 씀).

## 12. 2차(master#65cc8eea · 08:0x) — H-SECRET-1 · T3 census · 흔들림

### 12-1. H-SECRET-1(공개 secret-scan · 발행 차단) — 75건 → 0건(고침 커밋 62f51ef0)

**진짜 비밀 0**(관측): 적발 75건이 전부 경로 규칙(PATH 65 · WIN-PATH 10) — 비밀값 규칙(토큰·키 = SECRET) · EMAIL · PROFILE · HANDLE 0건. 경로의 사용자 이름은 오너 실제 계정 1종(문서 3개)과 지어낸 이름 6종(시험 자료).

| 파일 | 규칙 | 꼴(사용자 이름 · 건수) | 성격 | 넣은 커밋(조각) | 처분 |
|---|---|---|---|---|---|
| `docs/CODEX-R1-2d-tabs-sidebar.txt` | PATH | 오너 실제 계정 · 20 | codex 원문 기록의 작업 경로 | 05ab8f1b(tabs) | `~` 로(뜻 = 같은 홈) |
| `docs/CODEX-R1-tabs-sidebar.txt` | PATH | 오너 실제 계정 · 15 | 〃 | f79f175c(tabs) | `~` 로 |
| `docs/HANDOFF-tabs-sidebar.md` | PATH | 오너 실제 계정 · 2 | playwright 경로 | baddfb9a(tabs) | `~` 로 |
| `ui/e2e/seatrows_gate.py` | PATH 10 · WIN-PATH 2 | `u` · 12 | 지어낸 좌석 cwd | b98bce33(tabs) | 더미 `x` |
| `ui/src/seatrows.test.ts` | PATH 3 · WIN-PATH 2 | `u` · 5 | `folderKey` 입력 | 08d97e3a(tabs) | 더미 `x`(기대값 = 끝 폴더 이름 · 불변) |
| `ui/e2e/focus_gate.py` | PATH | `sim` · 2 | 가짜 cwd · 끌어 놓기 경로 | 6a8840c5 · fe235975(tabs) | `/Users/x/`·`/Users/x/proj` |
| `ui/e2e/race_gate.py` | PATH | `sim` · 1 | 가짜 cwd | d8eef9a3(tabs) | `/Users/x/` |
| `src/agy_door.rs` | PATH 9 · WIN-PATH 5 | `agy` 9 · `me` 1 · `u` 4 | 시험 입력(사용자 이름이 agy 인 경로 = 뜻) · 주석 1 | fd73d38e · f4576ffa(agy) | `agy` = `concat!("/Users", "/agy/…")` 실행 시 조립(같은 `&'static str`) · `me`·`u` → `x` · 주석 = `/Users/<사용자 agy>/…` |
| `docs/agy-door-evidence/ENTRY-MODES.md` | PATH | `agy` · 4 | 표의 입력 예 | c5d2bca2 · 996ee189(agy) | `~agy/`(사용자 agy 의 홈 = 같은 뜻) |
| `cysjavis-pack/bin/tests/test_agy_door.py` | WIN-PATH | `u` · 1 | 시험 입력 | fd73d38e(agy) | 더미 `x` |
| `cysjavis-pack/bin/tests/test_javis_counsel.py` | PATH | `hong-gildong` · 4 | 「개인정보처럼 보이는 글자가 전송에 안 실린다」 미끼 | 8599d13b(상담소) | `"/Users" "/hong-gildong/…"` 실행 시 조립(파이썬 문자열 이어 붙이기 · 실행 중 값 동일 — 미끼 목록 `planted` 그대로) |
| `docs/1115/COUNSEL-NOTICE-FIX.md` | PATH | `hong-gildong` · 1 | 보고서 설명 | c7ea898e(상담소) | `/Users/<지어낸 이름 hong-gildong>/…` |

- 고른 방식 = ⓐ(글자를 바꿈). 까닭: 이 저장소의 허용 방식은 `scripts/secret-scan.sh` 의 **더미 이름 목록 하나**(`user|x|youruser|USERNAME|runner|home`)뿐이고, 줄 단위 허용 표식은 없으며, 파일 통째 제외는 「오탐 확대 경로」로 폐기된 이력이 스크립트 주석에 있다(96~104행). 그래서 목록을 넓히지 않고(ⓑ 안 씀) 시험 자료를 그 목록의 이름이나 실행 시 조립으로 바꿨다(장기기억 test-strings-trip-public-secret-scan 관례).
- 함정 1건: 더미 판정은 이름 뒤가 `/`·`"`·줄끝일 때만 — `'/Users/x'`(홑따옴표 끝)는 여전히 적발 → `'/Users/x/'` 로(폴더 이름 판정 `folderKey` 는 끝 `/` 를 무시 · 게이트 초록으로 확인).
- 조각 시험이 여전히 초록(관측 · 고친 뒤): `secret-scan.sh --all` = `✓ clean (2049 파일)` · health `--only H-SECRET-1` = PASS(합성 변조 7/7 FIRE · 음성 대조 0) · lib `agy_door` 34/0 · cys `agy` 13/0 · `test_agy_door.py` 20 OK · `test_javis_counsel.py` 118 OK(skip 3) · bun 3451/0 · 화면 게이트 seatrows 75/0 · race 108/0 · focus 72/0(전부 앞 실행과 같은 수).
- 조각 가지 자체(tabs·agy·counsel)는 그대로다 — 이 고침은 통합 가지에만 있다.

### 12-2. T3 census(lib `spawn_policy_tests::raw_command_new_census_is_frozen`) — 【결정필요】

- **환경 의존 아님**(관측·판독): 이 시험은 소스 파일 글자를 세는 정적 검사다(`production_slice(src).matches("Command::new").count()` · lib.rs 7324행대). 살아 있는 좌석·프로세스를 보지 않는다. 격리 env(`env -i` · 짧은 HOME/TMPDIR)에서 합친 판·T3 단독(e568aa6c 별도 작업트리) 둘 다 붉음 · 같은 사유.
- v1.1.14: 시험은 있다(lib.rs 7324행 · 그때 초록 — 1차 기준선 lib 1203/0) · `src/bin/cys-seatkeep/main.rs` 파일은 없다(T3 가 만든 파일).
- **까닭(판독 + 관측)**: 세는 10개 = 전부 `mod imp` 안쪽 **들여쓴** `    #[cfg(test)]`(main.rs 1662행) 시험 모듈의 `Command::new`(2073~2608행 · 운영 코드 쪽 0개). `production_slice` 는 들여쓰지 않은 `#[cfg(test)]` 줄만 시험 구간으로 걷어 내므로(lib.rs 7005행 `lines[i] != "#[cfg(test)]"`) 이 모듈이 운영 코드로 셈에 들어간다. 1차 때 고친 fcc6896f 는 그때의 2개로 동결했고, 그 뒤 T3 커밋 5개(fix1~r4)가 같은 시험 모듈에 8개를 더했다. → **운영 스폰 증가 0 · 시험 자료(동결표)가 낡은 것**.
- 재현 한 줄: `git -C ~/cys-terminal-src worktree add --detach /tmp/t3 feat/seatkeep-t3 && cd /tmp/t3 && cargo test --lib raw_command_new_census_is_frozen`(기대 = FAILED · `"src/bin/cys-seatkeep/main.rs": 10` 대 동결 2).
- 선택지:
  - **A(권고) 통합 가지에서 동결표 1칸 2 → 10**(시험 자료 1줄 · 운영 코드 0 · 고친 뒤 lib 초록 확인) — 근거: 세는 10개가 전부 시험 코드라 위험 판단이 바뀌지 않는다 · T3 판정(codex r5 ACCEPT)의 대상인 운영 코드를 건드리지 않는다. 단점: 「시험 모듈이 운영으로 세어지는」 세는 쪽의 사각(들여쓴 `#[cfg(test)]`)은 그대로 남는다(1.1.16 후보).
  - B 세는 쪽(`production_slice`)이 들여쓴 `#[cfg(test)]` 도 걷어 내게 고침 — 다른 파일 계수도 바뀔 수 있어 동결표 전체 재측정 · 공용 그물을 바꾸는 일이라 이번 판엔 과함.
  - C T3 좌석에서 새 머리(동결표 갱신)를 받아 덧붙여 합침 — A 와 같은 결과 · 좌석 1회 + 다시 모으기.
- 고치지 않았다(지시대로). A 면 바로 1커밋으로 한다.

### 12-3. 흔들림 목록

| 이름 | 조건 | 단독 |
|---|---|---|
| cysd `pending_requests::tests::exact_plan_roundtrip_and_recovered_join_never_make_a_permit` | cysd 전체(`--test-threads=4`) · 동시에 agy 수용 하네스·health 가 돌던 부하 · `Err(Locked)`(1639행 저장소 재열기) | 3/3 초록 · 모듈 `pending_requests::` 99/0 · 이 파일은 어느 조각도 안 바꿈 |
