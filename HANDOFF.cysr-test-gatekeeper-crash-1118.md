# HANDOFF — TICKET=cysr-test-gatekeeper-crash-1118

cysd 시험이 맥 보안 검사(syspolicyd)를 죽여 맥이 멈춘 사고(11-18)의 재발 방지.
가지 = `fix/test-gatekeeper-crash`(integ/1116 머리 `fd9f0cc7` 에서 갈라냄) · 작업 폴더 = `.wt/cys-1116-gkfix` · push 0.

## 1. 원인 사슬

1. 시험이 **새 Mach-O 실행 파일을 만들어(복사·cc·rustc) 실행한 뒤 폴더째 지웠다.** 대표 = `seat_proc_tests.rs`
   `audit_code_path_matches_security_framework`(942d6d7e · 11-12 01:04): `/bin/sleep` 을 임시 폴더 가짜 번들에 복사 → 실행 → kill →
   `remove_dir_all`. 복사본은 x86_64+arm64e 플랫폼 바이너리라 서명 지위를 잃고 실행 즉시 「Code Signature Invalid」 SIGKILL
   (`~/Library/Logs/DiagnosticReports/fake*.ips` 162건의 정체).
2. 새 실행 파일이 처음 실행될 때 syspolicyd 가 큐 `syspolicyd.evaluations.scans` 에서 그 파일을 검사한다
   (`SecStaticCodeCheckValidityWithErrors` → `SecStaticCode::staticValidate` → `cdHash` → `MachORep::signingData` →
   `Universal::architecture`). 검사 도중 파일이 사라지면 `Universal*` 가 null 이라 **0x8 역참조 SIGSEGV**
   (`/Library/Logs/DiagnosticReports/syspolicyd-*.ips` 26건 전부 이 자리 · `KERN_INVALID_ADDRESS at 0x8`).
3. launchd 가 SIGSEGV 뒤 syspolicyd 재기동을 늦춘다(「security.syspolicy throttled after SIGSEGV」) →
   tccd 가 `SecAssessmentTicketRegisterXPC` 로 syspolicyd 를 기다림 → tccd/authd 동기 대기 → **WindowServer 워치독 강제 종료**
   (11-18 13:43(재부팅) · 14:59 · 15:02 · 15:03).

### 가설 반증 시도(정직 기록)
- syspolicyd 26건 중 fake 실행 ±2초 안 = 3건(11-12 01:05 · 03:54 · 11-18 11:50:52) · 11:51~12:03 9건은 그 뒤 연쇄로 보임.
- **11-11 16:45 1건은 942d6d7e 이전**이고 근처 fake 실행 0 → 이 시험 하나가 유일 원인은 아니다. 같은 꼴(새 Mach-O 실행 → 삭제)이
  기본 시험 묶음에 4곳 더 있었다(아래 2-②) → 원인 = 「새 Mach-O 실행 → 삭제」 꼴 전체.
- 11-18 13:57~14:13 fake 27회 실행 동안 syspolicyd 보고 0 · 12:03 뒤 보고 자체 없음 · 통합 로그 그 시간대 미보존 = 판정 불가.
- 더해 **cargo 자체**가 worktree 에서 매 실행 cys·cysd 를 다시 링크하고 있었다(아래 2-⑤ · 새 Mach-O 를 매 빌드 만든다).

## 2. 고친 곳(커밋 순)

| 커밋 | 무엇 |
|---|---|
| `5f2a60e1` | `seat_proc_tests.rs` 방아쇠 시험 = 정적 코드 객체 대조(`SecStaticCodeCreateWithPath` · 실행 0) + 가짜 번들을 `target/<profile>/cys-test-fixtures/t3-secpath/` 에 1회·삭제 안 함 · pid 경로는 제자리 `/bin/sleep` 1회로 「pid 답 = 정적 답 = 규칙」 · CONTRIBUTING 반복 루프 금지 |
| `979d148b` | 형제 처방: cysd `native_publication_transition_tests.rs`(cc 에이전트 → `c8-native/`) · lib `realops.rs` `fake_cysd_bin()`(→ `fake-cysd/cysd`) · `tests/support/fixed_fixture.rs` 신설(통합 시험 공용 · `CARGO_TARGET_TMPDIR/cys-test-fixtures/<용도>/`) → `rotate_autorestore_hold`(rah-claude · rah-bin · rah-owner) · `update_drainhold_e2e`(drainhold-claude) · `parity_todo_decl/scan.py` 덤퍼 고정 자리(원문 sha256) · `test_update_publish.py` `TestCollectMac` = CI 전용 · CONTRIBUTING 수동·VM 전용 2곳(`installer-atomic-demo.sh` spctl · `test_release_postprocess_gate.py` test_30 gktool) |
| `3ba23763` | 임시 원문 이름을 `.c` 로 끝나게(`<이름>.c.part-<pid>` 는 cc 가 링커 입력으로 넘겨 링크 실패 — 979d148b 통제 실행 적색) |
| `37943fe1` | rah-bin(cys·cysd 이동본) = 같은 inode 거나 바이트 전수 같으면 손대지 않음 · 다르면 복사 대신 하드 링크(새 내용 0) · `.stamp` 폐기 |
| `5d5e7979` | **근본**: `build.rs` `rerun-if-changed=.git/HEAD` → `head_watch_paths` = 실제 HEAD 파일(`git rev-parse --path-format=absolute --git-path HEAD`) + HEAD 가 가리키는 ref 느슨한 파일(없으면 packed-refs) · 존재하는 것만 · 못 구하면 옛 폴백. worktree 의 `.git` 은 파일이라 `.git/HEAD` 가 없어 cargo 가 매번 빌드 스크립트를 다시 돌리고 build_id(UTC 분)가 바뀌어 cys·cysd 가 매 빌드 새 Mach-O 였다 |
| `fc7c16a0` | build.rs 문서 줄 자리 정리(코드 변경 0) |
| (이 HANDOFF 커밋) | HANDOFF · TODO |

잃는 것: 번들 주 실행 파일을 **실행 중 프로세스(pid 경로)** 로 대조하는 것(정적·동적이 같은 판정을 쓴다는 가정 — 정적 쪽은
`codesign -dv` 실측 + 통제 실행 초록으로 확인) · 고정 자리 파일은 `cargo clean` 전까지 남는다(용도별 고정 이름 = 쌓이지 않음).

## 3. 통제 실행 결과(master · msv 스냅샷 · 2회전 × 5단계 · GUARD = syspolicyd·fake 계수)

| 머리 | 결과 | 로그 |
|---|---|---|
| `979d148b` | 계수 26·162 불변 · seat_proc 초록 · native/drainhold/rotate 적색(cc 링크 실패 → 3ba23763) | `master/logs-gk-979d148b-suite.log` |
| `3ba23763` | 시험 전부 초록 · 계수 불변 · **FIXTURES-CHANGED**(rah-bin cys·cysd 2회전 재기록 → 37943fe1·5d5e7979) | `master/logs-gk-3ba23763-suite.log` |
| `5d5e7979` | **gate_rc 0 · FIXTURES-STABLE · 2회전 × 5단계 rc 0 · syspolicyd 26 · fake 162 처음부터 끝까지 그대로**(18:00:40~18:39:19) | `master/logs-gk-5d5e7979-suite.log` |

통제 실행 명령(모듈 필터): `cargo test --bin cysd seat_proc::tests::audit_code_path_matches_security_framework` ·
`cargo test --bin cysd native_publication::native_transition_tests::` · `cargo test --lib update::realops::tests::<각 1개씩 2회>` ·
`cargo test --test update_drainhold_e2e` · `cargo test --test rotate_autorestore_hold`.

## 4. 제품 경로(읽기만 · 위험 낮음)
- seatkeep `peer.rs:133-160` = 감사 토큰 → `SecCodeCopyGuestWithAttributes` → `SecCodeCopyStaticCode` → `SecCodeCopyPath`(제 프로세스 안 ·
  설치된 cysd 대상 · 검증 플래그 0 · 제품 requirement None · 노브 CYS_SEATKEEP 기본 끔).
- seatkeep 기동 = cysd 옆 설치본 실행(만들기·지우기 없음).
- 업데이터 = 새 번들 `codesign --verify`(별 프로세스 정적) → rename 교환(`mac.rs` `swap_forward` · `macupdate.rs` `atomic_swap`) ·
  옛 번들은 `.cysr.app.old-<seq>` 로 남김.

## 5. 남은 위험
- 로컬 build_id 의 시각·`-dirty` 는 이제 **HEAD·ref·팩 변경 때만** 갱신된다(옛: worktree 에서 매 빌드). 릴리스 CI 는 `CYSR_BUILD_ID`
  를 넘기므로 무관.
- `scripts/update/collect-inputs.sh`(제품 수집기)는 여전히 번들을 임시 폴더에 풀어 실행 → 지운다(CI 전용 표지로만 막음 · 별 티켓 후보).
- `installer-atomic-demo.sh`(spctl) · `test_release_postprocess_gate.py` test_30(gktool scan · 아무 맥에서 기본 실행)은 문서 표지뿐.
- master 스냅샷의 고정 자리 폴더에 실패 회차 `*.c.part-<pid>`·옛 `.stamp` 찌꺼기 가능(무해).
- cargo 자체의 테스트 실행 파일 재빌드(deps/ 해시 이름 덮어쓰기)는 이 티켓 범위 밖.

## 6. integ/1116 병합 목록·순서
`integ/1116` 머리 = `fd9f0cc7`(이 가지의 밑) → 이 가지는 그 위 선형 7커밋이라 **빨리감기 1회**로 올라간다.
순서: `5f2a60e1` → `979d148b` → `3ba23763` → `37943fe1` → `5d5e7979` → `fc7c16a0` → (HANDOFF 커밋).
충돌 확인 = 【완료】 보고의 `git merge-tree` 줄 참조. 실제 병합은 master 지시 뒤.

## 7. 재현·주의
- ⛔사람 맥에서 cysd 시험 반복 루프 금지(CONTRIBUTING) · 흔들림 재현은 VM 또는 모듈 필터.
- 고정 자리를 새로 만들려면 해당 `cys-test-fixtures/<용도>/` 를 지우면 다음 실행에 1회 다시 만든다(그 1회는 새 Mach-O 첫 실행).
