# HANDOFF — 1.1.16 원작자 편입 묶음 (TICKET=cysr-1116-vendor-import)

- 좌석 worker-3(surface:2149) · 브리프 = spawn 경로(원장 2026-11-17T21:22:01 · `master/briefs/2026-11-17-cysr-1116-vendor-import.md`)
- 작업 트리 `~/axdev/.wt/cys-1116-vendor` · 가지 `integ/1116-vendor` ← `integ/1115-r2` 3a095c4e · **push·서명·발행·설치 0** · 이 기기 `~/.cys` 무접촉(시험은 전부 격리 HOME)
- 정본 판정표 = `~/axdev/workers/cysr-vendor-0151-judge-1117/JUDGE-v0.14.54-v0.15.1.md`(§1-U U02·U03·U05·U08·7d)

## 1. 커밋 목록(묶음별 · 3a095c4e 위 10개 · push 0)

| 묶음 | 커밋 | 내용 |
|---|---|---|
| U02+U03+7c 저널 | af90b640 | red first — 본부·부서 끊김 재현 시험 3종(고치기 전 붉음) |
| | a942eadd | 재구현 본체(레인 저널 · apply_id · 배치 기록 · 쓴 것만 되돌림 + kept · 권한 · 옛 공유 저널 이관 · doctor · 초기화 목록) |
| | b6547f59 | codex 1R REVISE 6건 반영 |
| | ef96e6e8 | codex 2R REVISE 4건 반영(+1 기록) |
| | 25b4f717 | codex 3R REVISE 3건 반영 |
| | 7fa49942 | codex 4R REVISE 3건 반영 → **5R ACCEPT** |
| 7d | 284b0e57 | `pack-merge --to-local` bin/·hooks/ 쓰기 전 거부(재구현) |
| U08 | cfbca72c | 정지 표지 판독 불가 = 정지(재구현 + 원작자 시험 이식) |
| U05 | bef0e9c4 | `check_macho_arch.py` + 시험(원작자 그대로) · `build-macos-local.sh` 배선 · RELEASE.md |
| 인계 | (이 파일 커밋) | HANDOFF |

## 2. U02 + U03 + 7c 저널 묶음 — 재구현

재구현 사유(1줄): 원작자 T9·WJ1·WJ2 프로토콜(약 5,000줄)은 우리가 들이지 않은 v0.15.1 pack.rs 설치 핵심(R12)·정확 모드 쓰기 위에 서 있고,
첫 고침 커밋 `47df86b1` 단독 cherry-pick 이 pack.rs 충돌 10덩어리(실측: `git cherry-pick -x --no-commit 47df86b1` → `<<<<<<<` 10)이며,
원작자 완료 판정(`.pack-applied.json`)이 우리 U2 `commit.json` 판정을 대체한다 → 같은 동작을 우리 저널 위에 다시 만들었다(폴더 이름·모양은 원작자와 같게).

| 원작자 항목 | 우리 꼴 | 자리 |
|---|---|---|
| GX1 레인마다 저널 | `<팩 부모>/.pack-journal.d/<팩 폴더 이름>/active` | `src/pack.rs` `pack_journal_lane_dir_for`·`pack_journal_dir_for` |
| GX2 끝남 = 그 적용 고유 표지 | 우리 U2 `commit.json` 보존 + `apply_id`(인덱스와 같아야 이 적용의 커밋) | `commit_record_is_this_apply` |
| GX3 살아 있는 쓰는 이 무접촉 | 데몬 기동 복구 = 팩 적용 잠금을 기다리지 않고 잡아 봄 · 남이 쥐면 Busy(복구·자동 설치 둘 다 안 함) | `recover_pack_journal_unless_busy` · `src/bin/cysd/main.rs` |
| GX4 옛 공유 저널 = 아무도 복구 안 함 + 안내 | **다르게 함**: 본부 레인만 이름 바꾸기 한 번으로 자기 저널로 옮겨 복구 · 부서는 무접촉 + 한 번 안내 · doctor 줄 | `adopt_legacy_pack_journal` · `diag_pack_state` |
| GX7 초기화 목록 | `.pack-journal.d` 추가 + 시험 이식 | `src/factory_reset.rs` |
| WJ1 placed.log · 쓴 것만 되돌림 · kept/ | 같음 + 백업 목록 밖 쓰기는 첫 변경 직전 늦은 백업(late.log) | `placement_announce`·`rollback_journal_for`·`KeptFolder` |
| WJ2 손잡이 0 | 줄마다 열고·쓰고·확정하고·닫음 | `placement_announce` |
| M15-가 / 7c 권한 | 저널이 mode 기록 · 되돌림이 바이트+정확한 권한 · 권한 귀속(이 적용이 건드린 이름만) | `JournalEntry.mode`·`set_exact_mode` |
| HE4 SETTLE | active → `done-<시각>` 이름 바꾸기 후 삭제 | `settle_journal` |

원작자와 다른 결정 1건(GX4) 근거: 우리 판에서 `pack-update` 를 부르는 곳은 본부뿐(러너 `src/update/realops.rs:1117·1150` 은 러너 환경 = 본부 ·
`cysjavis-pack/bin/cys-dept`·`src-tauri` 에 pack-update 호출 0 — grep). 원작자처럼 아무도 복구하지 않으면 반쯤 적용된 본부 팩이 사람 손을 기다린다
(박사님 4-4 「박사님 할 일 0」). 옛 저널엔 배치 기록이 없으므로 살아 있는 내용이 백업과 다르면 `kept/` 에 먼저 보관하고 되돌린다(주인 판단이 틀려도 손실 0).

### 2-1. 실제 끊김 재현(실바이너리 · 격리 HOME) — 붉음 → 초록

도구 = scratchpad `e2e_j1116.py`(격리 HOME 에 본부 `~/.cys/pack` + 부서 `~/.cys/pack-dept-d1` · 판 번호를 바이너리보다 높게 둬 데몬 기동 설치가 끼어들지 않게 ·
실 `cysd` 를 부서 팩 → 본부 팩 순으로 띄움 · 자기 자식 프로세스 그룹만 종료). 끊긴 상태 = 본부 팩 업데이트가 install 직후 사망 + 그 사이 본부 데몬이
`schedule.json` 에 예약 작업 저장 + 훅(0775)을 업데이트가 덮음.

| 경우 | 부서 팩(부서 데몬 기동 뒤) | 본부 팩(본부 데몬 기동 뒤) | 판정 |
|---|---|---|---|
| 고치기 전(3a095c4e 의 cysd · 1.1.15 모양 공유 저널) | README·지침·schedule.json·훅이 **본부 것으로 바뀜**(부서 예약 작업 소실 · 훅 0644) — 바뀐 이름 5 | 저널을 부서가 가져가 **반쯤 적용된 채**(README 새것·new.txt 남음·훅 0644) | 붉음 |
| 고친 뒤(이 가지 cysd · 이 판 저널) | 바뀐 이름 0 · 부서 예약 작업·훅 0775 그대로 | README·지침 옛것 · new.txt 없음 · **끊긴 사이 예약 작업 그대로** · 훅 0775 · `kept/<id>/backup/schedule.json` 에 업데이트의 백업 보관 | 초록 |
| 1.1.15 → 1.1.16 올림(1.1.15 모양 공유 저널 + 이 가지 cysd) | 바뀐 이름 0 · 「본부 레인 몫 — 손대지 않음」 안내 1줄 | 옛 저널을 본부 레인으로 옮김 → 되돌림 · 옛 저널 사라짐 · 끊긴 사이 예약 작업은 `kept/legacy-*/live/schedule.json` 에 보관(살아 있는 파일은 백업 「[]」) · 훅 0644 | 초록(아래 한계) |

한계(올림 경우): 1.1.15 저널에는 배치 기록·권한 칸이 없다 → 「그 업데이트가 쓴 것만」을 가를 수 없어 보수 규칙(살아 있는 것을 보관하고 되돌림)이고,
권한은 되살리지 못한다(훅 0644). 손실 0(전부 kept/)이지만 사람이 kept/ 에서 예약 작업을 다시 넣어야 할 수 있다.

### 2-2. 리뷰(codex · 읽기 전용 사본 · 쓰기 0)

| 라운드 | 대상 | 판정 | 처리 |
|---|---|---|---|
| 1R | a942eadd | REVISE(blocking 2 · major 3 · minor 1) | 6건 전부 수용 → b6547f59 |
| 2R | b6547f59(수렴 확인) | REVISE(1R 중 3 닫힘 · 남은 blocking 1 · major 2 · minor 2) | 4건 고침 + 1건 기록만 → ef96e6e8 |
| 3R | ef96e6e8 | REVISE(2R 중 3 닫힘 · .user.tmp = 기록만 동의 · 남은 major 3: 부트 복구↔설치 잠금 틈 · 권한 귀속 · 백업 목록 안 링크) | 3건 고침 → 25b4f717 |
| 4R | 25b4f717 | REVISE(잠금 틈 닫힘 · 남은 major 3: 권한 증거 · 비유닉스 링크 · 링크 되살리기 경합 · minor 3) | 3건 고침 + minor 3 기록만 → 7fa49942 |
| 5R | 7fa49942 | **ACCEPT**(4R major 3 전부 닫힘 · 새 blocking/major 0 · minor 4 = 기록) | — |

5R 남은 minor(기록만 · 1.1.15 보다 발화·손실 조건이 나빠지지 않음 — codex 판정 문구):
1. 링크 되살리기: 현재 것을 kept/ 로 옮긴 뒤 symlink 생성 전 다시 끊기면 다음 복구가 링크를 되살리지 않고 저널을 정리할 수 있음(옮긴 것은 보존) — `src/pack.rs` rollback_link_entry.
2. write_journal 의 종류 검사(symlink_metadata)와 읽기 사이 교체 경합(nofollow 핸들 미사용).
3. 부트 자동 설치가 팩 적용 잠금 안에서 팩 밖 설정 시드(settings 잠금 대기)까지 함 — 교착 미입증 · 잠금 점유가 길어질 수 있음.
4. 비 UTF-8 링크 대상 = 적용 거부(안전한 실패).
그 밖 기록만: byte_backup_user 가 끊기면 팩 안 `<rel>.user.tmp-<pid>` 잔여(1.1.15 와 같은 기존 동작 · codex 3R 동의).

판정 원문 = scratchpad `codex-r1-out.txt` ~ `codex-r5-out.txt`(경로는 §9) · 각 라운드 = 읽기 전용 사본 폴더(git archive + diff)에서 `~/.claude/channels/codex-call.sh`(gpt-5.6-sol · high) · 리뷰어 쓰기 0.

## 3. 7d — `pack-merge --to-local` bin/·hooks/ 쓰기 전 거부(재구현 · 284b0e57)

재구현 사유(1줄): 원작자 8deb3f99 는 R12(업데이트 규칙·vendor-first·등재 목록 수리 흐름 — 판정표 ⓔ) 위의 안내(`parked_copy_routes`·`listed_repair_route`)를 부른다
→ 우리 healed·conflicted 갈래에 같은 거부만 만들었다. 대신 쓸 명령 = `cys pack-adopt <rel>` · `--keep-mine` · 훅은 `~/.cys/local/hooks/<이벤트>.d/`
(`cysjavis-pack/hooks/cys-hook.sh:39` 가 읽는 유일한 자리).

## 4. U08 — 정지 표지 판독 불가 = 정지(재구현 · cfbca72c)

재구현 사유(1줄): 원작자 77d291f3 은 12커밋 S5-PINS 묶음(7파일 겹침 · 회귀 핀 11종)의 한 조각 → `javis_wakeup.py` `paused_evidence()` 한 함수만 같은 꼴로.
시험은 원작자 두 클래스 이식. 남은 틈(기록): `javis_radio.py` `paused_now()` 의 `ROOT/_round/AUTOPILOT_PAUSED` 자체 `os.path.exists`(원작자도 같음).

## 5. U05 — 맥 zip 직전 칩 검사(원작자 파일 그대로 + 우리 배선 · bef0e9c4)

`scripts/check_macho_arch.py`·시험 = v0.15.1 과 바이트 같음 · 배선 = `scripts/build-macos-local.sh`(codesign 검증 뒤 · ditto 앞) + `docs/RELEASE.md` 4단계.
설치 도우미 몫(install-core.sh)은 판정표대로 안 함. 미배선 = 업데이터 tarball(`make-darwin-updater-tarball.sh`).

## 6. 들이지 않은 것

- PO1(원작자 pack-update 안내 줄 stderr 이동) — 브리프 ⑤ · 우리 `src/update/realops.rs` 판독(stdout contains)이 깨짐. 이 가지에 PO1 관련 변경 0.
- U04 — 1.1.15 에 이미(8ed6c44d·3a095c4e) · 다시 넣지 않음.

## 7. 시험 — 기준선(3a095c4e) 대비 · 같은 격리 env(scratchpad `runall.sh` · env -i · 짧은 TMPDIR · PATH 에 /usr/sbin:/sbin)

| 시험 | 기준선 3a095c4e | 이 가지 7fa49942 | 차이 사유 |
|---|---|---|---|
| cargo build --bins --tests | rc 0 | rc 0 | — |
| lib | 1238 · 0 · 2 ign | **1252 · 0** · 3 ign | +14 = 저널 시험 13 + 초기화 목록 1 · +1 ign = 실바이너리 재현 상태 만들기(평소 제외) |
| bin cys | 760 · **1**(dbg_r12_init_pack_wires_profile_skill_links) | **764 · 0** | +3 = 7d 2 + doctor 옛 저널 1 · 기준선 붉음 1 = 이 가지에서 초록(이 티켓이 안 건드림 → 흔들림/환경 · 앞 인계서도 「기준선만 붉던 dbg_r12」) |
| bin cysd | 3273 · **2**(dbg_r12_seat_profile_wired_before_agent_exec · dbg_r12_update_lane_restore_seat_gets_link_before_exec) | **3275 · 0** | 같은 dbg_r12 흔들림 · 핀 시험 2개는 새 부트 함수 기준으로 옮김(같은 보장) |
| bin cys-seatkeep | 49 · 0 | 49 · 0 | — |
| tests/*.rs | hidden 1/0 · rotate 11/0 · seat_group 1/0 · drainhold 4/0 · win 2종 0 | 같음 | — |
| 팩 파이썬(wakeup 4종·radio·computer_control 112·hook_fail 11/10·counsel 118(skip3)·agy_door 20) | 전부 rc 0 · liveness 13 | 전부 rc 0 · **liveness 20**(U08 +7) | — |
| scripts/tests/test_*.py | OK 21 · FAIL 1(test_release_trigger_split) | OK **22** · FAIL 1(같은 것) | +1 = test_check_macho_arch(62) · 같은 FAIL = 기준선부터 |
| bun test(ui) | 3451 pass · 0 fail | 3451 · 0 | ui 변경 0 |
| tsc(typescript@7.0.2) | rc 0 | rc 0 | — |
| health run_bootstrap_health.py | 167 pass · 2 fail(H-CLT-1·2) · 1 skip | 167 · 2(H-CLT-1·2) · 1 | 같은 ID — 앞 인계서의 기존 환경 결함(설치본 python 선택) |
| secret-scan --all | clean 2049 | clean **2051** | +2 = check_macho_arch.py · 그 시험 |
| 화면 게이트 7종 | — | **미실행** | 이 기계에 playwright 파이썬이 없음(찾은 곳 0) · 이 티켓의 ui/·src-tauri/ 변경 0파일(`git diff --stat 3a095c4e HEAD -- ui src-tauri` 빈 출력) |

뮤턴트(고친 줄을 되돌리면 붉어지는가 · `CYS_U1_MUTANT` 시험 빌드 전용): 저널 12종 전부 해당 시험 붉음(J1116-SHARED · LEGACY-ANYLANE · MODE · MODE-EXACT ·
UNDO-ALL · NO-PLACEMENTS · IGNORE-BUSY · ANY-COMMIT · NO-LATE · LATE-ANYKIND · MODE-ANY-TOUCH · LINK-AS-FILE) · 7d J1116-TOLOCAL 붉음 · U08(os.path.exists 로
되돌림) 2 붉음 · U05("ok": True) 9 붉음. 1R 고침 두 시험은 a942eadd 에서 직접 붉음 확인(.user 소실 · 0600→0644).

## 8. 한계 · 남은 것(정직 기록)

- 1.1.15 옛 공유 저널 올림: 배치 기록·권한 칸이 없어 「쓴 것만」 가를 수 없음 → 보수 규칙(살아 있는 것 kept/ 보관 후 되돌림) · 권한 못 되살림 · 손실 0이나
  끊긴 사이 예약 작업은 kept/ 에서 다시 넣어야 할 수 있음(실바이너리 재현 「올림」 줄).
- 옛 저널 이관의 주인 판단 = 「부서 레인은 pack-update 를 부르지 않는다」(제품 경로 grep) — 사람이 부서 팩 경로로 `cys pack-update` 를 손으로 친 1.1.15
  기기면 그 옛 저널은 부서 것인데 본부가 되돌린다(이때도 살아 있는 바이트는 kept/ 보존 · 손실 0).
- 윈도우: 잠금은 표준 라이브러리 LockFileEx 로 맞췄으나 윈도우 실기 시험 0 · 팩 안 링크가 있으면 적용 거부.
- codex 5R minor 4 + .user.tmp 잔여(§2-2).
- 러너 `realops.rs` recover_pack_at 의 사용자 트리 복원(`pack_user_tree_restore`)은 이 티켓 밖 — 팩 되돌림과의 상호작용 미측정.
- U05: 업데이터 tarball 미배선 · 설치본 LSMinimumSystemVersion 10.13 vs 진입점 11.0 경고.
- U08: javis_radio.py 의 자체 표지 판정(원작자도 같음).

## 9. 증거 경로(scratchpad = `/private/tmp/claude-501/-Users-oogisoogi-axdev--wt-cys-1116-vendor/0ac8a2b3-7526-4162-b7c2-fbb6a81fa2b3/scratchpad/` · 재부팅 시 사라질 수 있음)

- 시험 요약 `out-base/summary.txt`(기준선) · `out-head/summary.txt`(최종) · 각 로그 같은 폴더 · 실행 틀 `runall.sh`
- red first `red-j1116.log` · 1R 고침 붉음 `red-codexfix-prev.log` · 뮤턴트 `mutants-j1116*.log` · `mutants-7d.log`
- 실바이너리 재현 `e2e_j1116.py` · 결과 `e2e-final/e2e-{before,after,upgrade}.txt` · 데몬 로그 `e2e-final/cysd-*.log`
- codex `codex-r{1..5}-prompt.md` · `codex-r{1..5}-out.txt`

## 📌 덧붙임(브리프 밖 · 실행 안 함)

1. 저널 묶음이 들어가기 전까지 부서 있는 기기에서 팩 단독 자동 업데이트를 멈출지(판정표 §6 결정 1) — 이 가지가 1.1.16 으로 나가면 그 게이트의 근거가 사라진다.
2. codex 5R minor 1(링크 되살리기 재중단 창) · 2(nofollow 판독) · 3(부트 설치의 팩 밖 시드를 잠금 밖으로) — 1.1.17 후보.
3. 윈도우 실기에서 끊김 재현 1회(레인 저널 · LockFileEx · 링크 거부) — 원작자도 윈 E2E 0.
