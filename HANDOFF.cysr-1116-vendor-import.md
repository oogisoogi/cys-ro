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

## 9. 증거 경로(scratchpad = `/private/tmp/claude-501/-Users-<사용자>-axdev--wt-cys-1116-vendor/0ac8a2b3-7526-4162-b7c2-fbb6a81fa2b3/scratchpad/` · 재부팅 시 사라질 수 있음)

- 시험 요약 `out-base/summary.txt`(기준선) · `out-head/summary.txt`(최종) · 각 로그 같은 폴더 · 실행 틀 `runall.sh`
- red first `red-j1116.log` · 1R 고침 붉음 `red-codexfix-prev.log` · 뮤턴트 `mutants-j1116*.log` · `mutants-7d.log`
- 실바이너리 재현 `e2e_j1116.py` · 결과 `e2e-final/e2e-{before,after,upgrade}.txt` · 데몬 로그 `e2e-final/cysd-*.log`
- codex `codex-r{1..5}-prompt.md` · `codex-r{1..5}-out.txt`

## 📌 덧붙임(브리프 밖 · 실행 안 함)

1. 저널 묶음이 들어가기 전까지 부서 있는 기기에서 팩 단독 자동 업데이트를 멈출지(판정표 §6 결정 1) — 이 가지가 1.1.16 으로 나가면 그 게이트의 근거가 사라진다.
2. codex 5R minor 1(링크 되살리기 재중단 창) · 2(nofollow 판독) · 3(부트 설치의 팩 밖 시드를 잠금 밖으로) — 1.1.17 후보.
3. 윈도우 실기에서 끊김 재현 1회(레인 저널 · LockFileEx · 링크 거부) — 원작자도 윈 E2E 0.

---

## 10. 델타 — 독립 검증 1118 1회 고침 (TICKET=cysr-1116-vendor-fix-1118 · worker-3 surface:2163 · 2026-11-18 01:1x~03:4x)

- 입력 = 독립 검증 원문 `~/axdev/.wt/cys-1116-vendor-verify/VERIFY.cysr-1116-vendor-verify-1118.md`(F1~F7) · push·서명·발행·설치 0 · 실제 `~/.cys` 무접촉(시험 = 격리 HOME `env -i`).
- 증거 경로(scratchpad = `/private/tmp/claude-501/-Users-<사용자>-axdev--wt-cys-1116-vendor/410f637d-ac6a-4ccd-9e2b-642e51cf6cd6/scratchpad/` · 재부팅 시 사라질 수 있음): `red-f1.log`·`red-f2.log`(붉음 먼저) · `mut-*.log`·`r1-mut-*.log`(뮤턴트) · `xlock/`(실바이너리 잠금 6줄) · `e2e/`(저널 실바이너리 재현) · `out-head/`·`out-base/`·`out-r1/`(전체 시험) · `v1118-on-head.log`(검증 좌석 시험 10개를 이 가지에서) · `codex-f1-prompt.md`·`codex-f1-out.txt`(codex 1R 원문).

### 10-1. 커밋(fcc0cc73 위 · push 0)

| 커밋 | 내용 |
|---|---|
| 9b2ce1bf | test — F1 붉음 먼저(본부 레인이 잠금을 쥔 동안 부서 기동이 `Ok((Busy, None))`) |
| 0f6c1929 | fix F1 — 적용 잠금을 레인마다 |
| d19264da | test — F2(가) 붉음 먼저(적용 전 0775 가 0644 로 남음) |
| 105b9b61 | fix F2(가) — 권한 귀속 = 끝의 의도 줄을 건너뛴 마지막 확정 줄 |
| 714ae7c5 | fix F5 — doctor pack-state 가 이 레인 진행 중 저널을 이름 댐 + 데몬 로그가 doctor 를 가리킴 |
| 828bbcff | fix codex 1R REVISE 반영(F1 역방향 major · F5 doctor 거짓 Fail minor) |
| (이 절 커밋) | HANDOFF 델타 · TODO |

### 10-2. F1 고침 — 방향 ⓐ 레인마다 잠금(근거 1줄: 데몬 기동 설치가 쓰는 것은 그 레인 팩과 레인/pid 별 형제뿐이고 레인 사이 공유 파일 `.pack-staging`·`.pack-download`·`.pack-accepted.json` 은 `cys pack-update` 만 쓰므로, 공용 잠금은 쓰는 이끼리만 지키면 되고 기다림(ⓑ)·재시도(ⓒ)처럼 소켓 바인드 앞 기동을 늦추거나 「설치 전 바인드」를 바꾸지 않는다)

- 잠금 자리: 레인 잠금 `<팩 부모>/.pack-journal.d/<팩 폴더 이름>/.apply.lock`(`src/pack.rs` `lane_apply_lock_path`) · 공용 `<팩 부모>/.pack-apply.lock` 은 그대로.
- 쓰는 이(`src/bin/cys.rs` `with_apply_lock`): 공용 → 레인 순서로 둘 다 **기다려** 쥠(`cys::pack::with_lane_apply_lock`).
- 데몬 기동(`with_apply_lock_nonblocking`): 이 레인 잠금을 비차단 · 남이 쥐면 Busy(= **같은 레인** 진행 중 적용 보호 · 시험 `j1116_daemon_recovery_skips_a_live_apply` 는 이제 쓰는 이가 실제로 쥐는 잠금 둘 다를 쥐고 잼). 부서 레인은 공용 잠금을 보지 않음.
  본부 레인만 공용 잠금도 비차단으로 잡아 봄(본부 레인만 1.1.15 옛 공유 저널을 옮기는데 1.1.15 쓰는 이는 공용 잠금만 쥠) — ★codex 1R 반영: 못 잡아도 옛 공유 저널이 **없으면** 이관 단계만 빼고 자기 레인 복구·자동 설치를 함 · **있으면** Busy.
- 공유 자원 실측(같은 부모 아래): 데몬 설치 = 그 레인 팩 + `<팩>.prev`·`<팩>.swap`·`.pack-staging-init-<pid>`(레인/pid 별) · 레인 사이 공유 = 위 셋(쓰는 이만) · 옛 공유 저널(본부 레인만 옮김) · 공장 초기화 목록은 `.pack-journal.d` 통째(레인 잠금 파일 포함).
- 시험(붉음 → 초록): `j1116_dept_boot_installs_while_base_apply_holds_its_lock`(F1 정방향) · `j1116_base_boot_installs_while_a_dept_apply_holds_the_shared_lock`(codex 1R 역방향) · `j1116_shared_lock_only_writer_still_stops_the_base_lane`(1.1.15 쓰는 이 + 옛 저널 = 본부 Busy · 부서는 설치).
- 뮤턴트(시험 빌드 전용): J1116-LANE-SHARED(레인 잠금 대신 공용 = 고치기 전) → 4 붉음 · J1116-SHARED-BUSY-SKIPS(공용 Busy = 건너뜀 = 1R 전) → 역방향 1 붉음 · J1116-BASE-NO-SHARED → 1.1.15 쓰는 이 시험 1 붉음 · J1116-IGNORE-BUSY → 같은 레인 보호 붉음.

### 10-3. e2e_xlock(검증 좌석 도구 그대로 · 실바이너리 · 격리 HOME · 25초 뒤 팩 상태) — 전후

| 줄 | 고치기 전(검증 좌석 · fcc0cc73 cysd) | 고친 뒤(이 가지 cysd · 5개 동시 실행) | 고친 뒤(단독 실행) |
|---|---|---|---|
| 본부 먼저 · 0초 | 본부 **설치 안 됨**(apply-lock 로그) | 둘 다 설치 중 · apply-lock 로그 0 | 둘 다 설치됨(496개 · 판 1.1.14) |
| 부서 먼저 · 0초 | 본부 **설치 안 됨** | 둘 다 설치 중 · 로그 0 | 둘 다 설치됨 |
| 본부 먼저 · 1초 | 부서 **설치 안 됨** | 둘 다 설치 중 · 로그 0 | 둘 다 설치됨 |
| 부서 먼저 · 1초 | 본부 **설치 안 됨** | 둘 다 설치 중 · 로그 0 | 둘 다 설치됨 |
| 본부 먼저 · 3초(동시 실행 중) | 부서 **설치 안 됨** | 둘 다 설치 중 · 로그 0 | 둘 다 설치됨 |
| 본부 먼저 · 3초(단독) | 부서 **설치 안 됨** | — | 둘 다 설치됨(496 · 1.1.14) |

건너뜀: 6/6 → **0/11**. (「설치 중」 = 동시 실행 부하로 25초 안에 판 표지까지 못 간 것 — 건너뜀 여부만 읽을 것 · 검증 좌석 표와 같은 읽기.) 이 표는 0f6c1929 의 cysd 다 — 828bbcff(codex 1R)는 본부 기동이 공용 잠금을 못 잡은 경우만 바꾸므로(두 데몬 기동끼리는 공용 잠금을 쥐어도 곧 놓음) 이 6줄의 경로와 겹치지 않는다 — 그래도 828bbcff cysd 로 6줄을 다시 단독 실행했다: **6줄 모두 두 레인 설치됨(판 1.1.14) · apply-lock 로그 0**(`xlock/r1-r1·r2` · `xlock/r1b-r3~r6` · 03:0x 첫 회는 load 100 이라 r3~r5 가 25초 안에 설치 중이었고 건너뜀 로그 0 → 부하 낮을 때 03:24 단독 재실행).
저널 실바이너리 재현(`e2e_j1116.py` after · upgrade · 0f6c1929 cysd) = 앞 좌석 §2-1 과 같은 초록(본부 되돌림 · 예약 작업 생존 · 훅 0775 / 올림 = kept/ 보관).

### 10-4. 지적별 처분(F1~F7)

| 지적 | 처분 | 근거·자리 |
|---|---|---|
| F1 높음 | **고침** | §10-2 · 0f6c1929 + 828bbcff |
| F2 낮음 | **(가) 고침 · (나) 일부러 안 고침** | 105b9b61 — 의도 확정 뒤 chmod 전 끊김은 앞 내용 줄(해시 + 놓인 권한)이 증거. (나) chmod 뒤 · 성공 줄 전 끊김은 지금 권한(0755) = 의도 값인데, 끊긴 뒤 사용자의 `chmod +x` 와 구별이 안 되므로 의도를 증거로 삼지 않음(codex 3R 「의도 ≠ 성공」 원칙 유지 · 결과 = 셔뱅 파일에 실행 비트가 남는 쪽 = 새 팩이 원하던 권한) |
| F3 낮음 | 📌 기록만 | 0600 파일 + 끊긴 뒤 내용만 고침 → 적용이 넓힌 0644 남음 · codex 4R 「해시와 함께 확정된 놓인 권한만 증거」의 귀결 · 사용자 바이트 손실 0 |
| F4 낮음~중간 | 📌 기록만 | 1.1.15 에서 **부서** 팩에 수동 pack-update 하다 끊긴 옛 저널이 남은 기기만(자동 경로 0) → 본부가 옮겨 되돌리면 본부 팩이 부서의 옛 백업으로 바뀜 · 부서 팩은 아무도 안 되돌림. 값싼 가름(검증 좌석 제안) = 옛 저널 백업 해시가 본부 매니페스트·살아 있는 본부 파일과 한 건도 안 맞으면 옮기지 않고 안내만 → 1.1.17 후보 |
| F5 낮음 | **고침(안내)** | 714ae7c5 + 828bbcff — `cys doctor` pack-state: 이 레인 진행 중 저널이 있으면 이름을 댐(복구가 실제로 읽을 인덱스·늦은 백업 칸·배치 기록을 못 읽으면 Fail + 「지우지 말 것 · 데몬 로그 사유 확인」 · 아니면 Warn) · 데몬 `pack journal recovery failed` 로그가 doctor 를 가리킴. 자동 해소(사람 손 0)는 하지 않음 — 손상된 기록을 자동으로 되돌리는 것은 더 위험 |
| F6 기록 | **정정**(§10-5) | 기준선 사본을 임시 폴더 밖에 둠 |
| F7 기록 | 📌 기록만 | ① `javis_formation.py:207`·`javis_cycle_autopilot.py:230` 의 `os.path.exists` 정지 표지 판정(U08 과 같은 꼴 · 원작자도 같음) ② 줄 확정 뒤 · 이름 바꾸기 전 끊김의 임시 조각 잔여(기준선과 같음) ③ 윈도우 1.1.15 러너 사본 ↔ 1.1.16 데몬(미재현) ④ 1.1.16 → 1.1.15 되돌림 시 레인 저널 미인식(되돌림 절차 한 줄 필요) ⑤ 「배치 중」 끊김 = 패닉 갈고리 흉내 |

### 10-5. §7 정정(F6) — dbg_r12 3개는 「흔들림/환경」이 아니라 「임시 폴더 위치 의존 고정 붉음」

- §7 의 「기준선 붉음 1·2 = 흔들림/환경」 → **기준선 사본이 `/private/tmp/…` 아래라서 언제나 붉음**(이 시험들은 `<저장소>/target/…` 에 팩을 깔고 `javis_preflight.py --wire-seat` 를 부르는데, 그 도구는 임시 폴더 아래 팩을 격리 팩으로 보고 배선하지 않음 — 검증 좌석 대조 탐침으로 확정).
- 실측: 기준선 3a095c4e 를 임시 폴더 **밖** `~/axdev/.wt/cys-1116-base-1118`(detached)에 두고 3회 = `dbg_r12_init_pack_wires_profile_skill_links` 3/3 초록 · `dbg_r12_seat_profile_wired_before_agent_exec`·`dbg_r12_update_lane_restore_seat_gets_link_before_exec` 3/3 초록(`out-base/dbgr12-*.log`). → 「기준선 붉음 → 이 가지 초록」은 개선이 아니라 위치 차이였다. 기준선 사본은 앞으로 임시 폴더 밖에.

### 10-6. 시험 — 기준선(3a095c4e · 임시 폴더 밖) 대비 · 같은 격리 env(`runall.sh` · env -i · 짧은 TMPDIR)

| 시험 | 기준선 3a095c4e(밖) | 이 가지 714ae7c5(전체) | 이 가지 828bbcff(codex 1R 뒤 · Rust 3종) | 차이 사유 |
|---|---|---|---|---|
| cargo build --bins --tests | rc 0 | rc 0 | rc 0 | — |
| lib | 1238 · 0 · 2 ign | 1255 · 0 · 3 ign | **1256 · 0** · 3 ign | +17 = 앞 좌석 저널 14 + 이 티켓 3(F1 · 1.1.15 쓰는 이 · F2) · 828bbcff +1 = F1 역방향 |
| bin cys | **761 · 0** · 2 ign | 765 · 0 | **765 · 0** | +4 = 앞 좌석 3 + F5 doctor 1 · 기준선 밖 = 0 붉음(F6) |
| bin cysd | 3274 · **1**(`pending_requests::…loaded_id_bookkeeping_is_reclaimed_with_the_row` · `Err(Locked)`) | 3274 · **1**(`pending_requests::…c8registry_registration_counter_exhaustion_never_wraps_or_overwrites` · `Err(Locked)`) | **3275 · 0** | 둘 다 병렬 부하 흔들림: 두 시험을 두 트리에서 단독 3회씩 = 6/6 초록(`pr-*.log`) · 이 티켓이 안 건드린 파일 |
| cys-seatkeep · tests/*.rs · 팩 파이썬 · scripts/tests · bun · tsc · health · secret | (앞 좌석 out-base 와 같음 — 이 티켓 Rust 만 바꿈) | 49/0 · hidden 1 · rotate 11 · seat_group 1 · drainhold 4 · win 0 · 파이썬 전부 rc 0(liveness 20 · computer_control 112 · hook_fail 11/10 · counsel 118 skip3 · agy_door 20) · scripts OK 22 FAIL 1(test_release_trigger_split — 기준선부터) · bun 3451/0 · tsc OK · health 167/2(H-CLT-1·2 — 기존)/1 · secret clean 2053 | — | 앞 좌석 §7 과 같음 |
| 검증 좌석 시험 10개(이 가지에 갈고리 붙인 임시 사본 · 커밋 안 함) | — | 7 초록 · 3 붉음 = F2(나)·F3·F4(일부러 안 고친 셋) · **배치 끊김 116지점 어긋남 0**(F2(가) 닫힘) · 되돌림 140지점 0 · F1 시험 초록 | — | `v1118-on-head.log` |

### 10-7. codex 1R(02:51 · gpt-5.6-sol high · 읽기 전용 사본 · 쓰기 0 · 대상 714ae7c5)

- 판정 **REVISE**(major 1 · minor 3). 원문 = `codex-f1-out.txt`.
- major: 모든 pack-update 가 공용 잠금을 먼저 쥐므로 **부서 레인 pack-update → 본부 데몬 기동** 방향은 여전히 건너뜀 → **반영**(828bbcff · §10-2 · 역방향 시험 + 뮤턴트).
- minor ①: 1.1.15 쓰는 이의 대상 레인을 공용 잠금만으로 가를 수 없어 1.1.15 **부서** 수동 쓰는 이 ↔ 1.1.16 부서 데몬 설치가 겹칠 수 있음 → 기록만(기준선은 데몬 기동이 잠금 없이 설치 = 나빠지지 않음 · codex 도 minor).
- minor ②: F2 — 의도 줄 뒤 chmod 성공 · 성공 줄 전 끊김 뒤 사용자가 바이트 그대로 권한만 앞 확정 값(0644)으로 되돌리면 그 사용자 권한을 적용 것으로 보고 적용 전 권한으로 되돌림 → 기록만(그 창 = 파일 하나 · 성공 줄 확정 시간 + 사용자가 정확히 그 값으로 chmod · 사용자 바이트 손실 0).
- minor ③: F5 doctor 가 복구가 읽지 않는 배치 기록까지 봐 거짓 Fail 가능 → **반영**(828bbcff · 시험에 커밋됨 = Warn 갈래 추가).
- missing 2: `pack_state_base()` = `pack_dir().parent()`(src/bin/cys.rs `fn pack_state_base` — 확인함 · 쓰는 이 `lock_path.parent()` 와 데몬 `pack_dir().parent()` 는 같은 값) · 공장 초기화가 `.pack-journal.d` 를 옮길 때 열린 레인 잠금(유닉스 inode 갈림 · 윈도우 이동 실패) → 기록만(📌).
- **codex 2R(03:27 · master 지시 [master#acb32445] · 대상 0f6c1929 포함 ~ 3100450c) = ACCEPT** — 1R major·minor ③·missing ① 닫힘 · minor ①② 기록만 동의 · 새 minor 1(본부 기동의 「공용 잠금 실패 → 옛 저널 없음」 검사와 1.1.15 쓰는 이의 저널 생성 사이 경합 · 기준선도 잠금 없이 설치 = 나빠지지 않음 → 📌) · 원문 = scratchpad `codex-f2r-out.txt`.

### 10-8. 자원 규칙(master 03:07 [master#a745e394] · 원장 대조 성립) 이후

- 그 시점 이미 돌던 lib·cys·cysd 동시 실행(828bbcff)은 끝까지 둠(전부 초록 · load 30~100 구간). 그 뒤 cargo 실행 0(실바이너리 xlock 만) · 하네스 `iso.sh` 에 `CARGO_BUILD_JOBS=6` 반영.

## 📌 덧붙임(이 티켓 밖 · 실행 안 함)

1. codex 2R(828bbcff 수렴 확인) — 브리프가 1R 1회라 하지 않음. 고위험(데몬 기동·잠금)이라 master 판단으로 1회 권함.
2. F4 값싼 가름(옛 저널 백업 해시가 본부와 한 건도 안 맞으면 옮기지 않고 안내) — 1.1.17 후보.
3. F3 · F2(나) · codex 1R minor ①②(1.1.15 부서 수동 쓰는 이 ↔ 부서 데몬 · 의도 줄 뒤 사용자 권한만 되돌림) — 기록. 셋 다 기준선보다 나빠지지 않음.
4. 공장 초기화가 `.pack-journal.d` 를 옮길 때 열린 레인 잠금(유닉스 inode 갈림 · 윈도우 이동 실패) — 초기화가 데몬을 먼저 멈추는지 미확인(codex 1R missing).
5. F7 ①(`javis_formation.py`·`javis_cycle_autopilot.py` 정지 표지 `os.path.exists`) · ④(1.1.16 → 1.1.15 되돌림 절차에 「레인 저널 남았는지 확인」 한 줄).
6-1. codex 2R minor: 공용 잠금 실패 뒤 옛 저널 부재 검사는 원자적이지 않음(살아 있는 1.1.15 쓰는 이가 저널을 만들기 전 창) — 후속 = 제한 재시도 또는 세대·레인 표식 + 「공용 잠금만 · 옛 저널 아직 없음」 시험 · F2 권한만 되돌린 사용자 시험.
6. 남은 「공용 잠금 Busy = 본부 건너뜀」 경우 = 1.1.15 옛 공유 저널이 **남아 있고** 어느 레인이든 pack-update 가 진행 중일 때뿐(1회성 올림 기기) — 다음 기동에서 복구·설치.
7. 기준선 worktree `~/axdev/.wt/cys-1116-base-1118`(detached 3a095c4e · 깨끗) — 다음 비교에 재사용하거나 `git worktree remove` 로 치움.
