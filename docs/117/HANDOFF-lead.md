# HANDOFF-lead — 1.1.7 갈래1(fix/117-store) + 통합 담당 (TICKET=cysr-117-impl-lead)

- 좌석: 151 · 117lead(계정2 · Opus 5.5) · worktree `~/axdev/.wt/cys-117-lead` · 브랜치 `fix/117-store`(작업) · `fix/117-lead`(= SPLIT 커밋) · `int/117`(= 1bc32693 · 아직 병합 0)
- 원장 지시: master#75ed3b05(브리프) · #4ead2ecd(Q1~Q4 판정) · #5daf328b(bundle-prep 편입) · #a62921f6(⑲ 주석 2곳 · ⑧ 경보 청취 단언)
- 소요 계수(다음 티켓용): SPLIT 10분(19:04→19:15) · 갈래1 구현 8항목 31분(19:15→19:46) · 게이트 전체 21분(19:47→20:08) · 적대 검증 R1(Fable) ≈20분

## 1. 끝난 것 (fix/117-store · 전부 로컬 커밋 · push 는 R2 판정 뒤)
| 항목 | 커밋 | 시험(새) · 뮤테이션 |
|---|---|---|
| ⑰ schedule.json | 4fca9226 | cys 2 · cysd 2 · 락 제거/판독 접기 복귀 = 적색 |
| ⑧ 큐 WAL | fd751152 · dfb127c8 · 31bd4a5d | state 2(보존 · 권한 0 · 재부팅 누적 0 · CSO 구독 `--category queue` 단언) |
| ⑩ pause (+Q2) | 791b600c | state 1 · handlers 1 · governance 소스 핀 1 |
| ⑨ 승인 키·목록 | 64519b13 · 86dedf77(tmp 순번) · 31bd4a5d(락·게시 폴백) | approval 5 |
| ⑲ cmux 포팅 재작성 | e547c0e7(골든 핀 먼저) · 86dedf77 · dfb127c8(주석 2곳) | 골든 6(서명 원문 = 파이썬 hmac 독립 계산) · 합격 grep 0 |
| ① cys-dept·GUI | 8813fae0 · 31bd4a5d | name_guard RegistryUnreadable 3 · list_depts 1 · deptreg 5 |
| ⑥ secret-scan | bc41de4b · 31bd4a5d | H-SECRET-1 ⓓ 5형(v1.1.6 스캐너 = 4형 exit 0 적색) |
| bundle-prep 644 | 244236c2 | H-BUNDLE-PERM-1(옛 cp 복귀 = 적색) |

로컬 게이트(244236c2 기준 · 20:08): cargo --lib 550 · --bin cys 344 · --bin cysd 1210 · cys-app 174 · gen_ceo/hash --check · ui 1465 · 팩 파이썬 루프 전건(0바이트 target/debug 함정 1건 = 빌드 후 PASS) · 건강 검체 150 PASS/1 SKIP. 31bd4a5d 뒤 재실행 = 영향 모듈만(cysd approval·queue_wal · cys-app · ui · name_guard · dept_request · H-SECRET-1) 초록 — **전체 재실행은 push 전 필수**.

## 1-1. 적대 검증 · push 결과(20:5x 갱신)
- R1 Fable REVISE(MAJOR 3) → 31bd4a5d · R2 Fable REVISE(MAJOR 1 = 복원 skip 을 UI 가 안 들음) → 79190615 · R3 Fable REVISE(MAJOR 1 = error 경로) → ebe0430f(3라운드 상한 · 수렴 판정 = master).
- agy: 1·2차 산출 0(헤드리스 command 권한 거부) · 3차(.git 없는 사본 · --dangerously-skip-permissions --sandbox) BLOCK 주장 3 → #1 「분류기 도구 8개 누락」 = 사실 아님(v1.1.6 classifier.rs 303줄 · 그 이름 0건 · L1975 부재) · #2 소비처 4곳 = 기존 동작 기록 · #3 윈도 락 = 헬퍼 한계 기록.
- push: fix/117-store @ebe0430f(force 0). CI(ebe0430f) = ci-branch 36563307307 · windows-build 36563307316 · windows-health 36563307309 (79190615 판 = 36563029335·36563029275·36563029456).
- 남은 MINOR(기록): 초기화 모달 본문 「부서 0」 · kill 뒤 경로 시험 없음 · dept_logdir 미단언 · rotate 가 launch 12 를 1 로 가림(선재) · create acctdir 선생성(선재) · 소비처 4곳 Err→부서 0(기존) · 윈도 락 없음 · ⑨ 키 판독 실패 eprintln 뿐 · WAL 사본 초 단위 이름.

## 2. 진행 중 / 남은 것
- 적대 검증 R2: Fable(31bd4a5d · 스크래치 rev-fable2/out.md) + agy(3차 시도 · `.git` 없는 사본 rev-agy2 · 샌드박스) — agy 1·2차는 헤드리스 「command 권한」 자동 거부로 산출 0(도구 문제 · 결함 아님).
- R2 반영 → 전체 게이트(스크래치 gates.sh) → `git push origin fix/117-store`(force 금지) → int/117 병합(no-ff) → 합성물 재생성 확인 → `fix/117-int` push(Q4=A) → 【확인요청】.
- 통합: 갈래2(153 · fix/117-input) · 갈래3(154 · fix/117-brand) 는 각 좌석이 push → 내가 int/117 에 1→2→3 순으로 병합.
- ★갈래3 brand = master 수용(master#193559c7 · 20:3x) · 머리 fix/117-brand @27e92f62 · 조건 = CI 3개(ci-branch 36562175238 · windows-build 36562175298 T8 · windows-health 36562175264) 초록(154 추적). 통합 주의: scripts/tests/test_mac_cli_alias_link.py = CI 미편입(레인 대조 ALLOWED 필요) · 겹침 = cys.rs L1-16·시험 L20120대 · main.ts L3880·import 1줄 · release.yml·pack-release.yml 크레딧 블록.

## 3. 함정 (재현·다음 사람용)
- cargo 는 PATH 에 없다 → `export PATH="$HOME/.cargo/bin:$HOME/.bun/bin:$PATH"`. TMPDIR 은 짧게(`/tmp/c117s`) — 소켓 SUN_LEN.
- cys-app 시험은 CI 처럼 자리표시자 필요: `mkdir -p ui/dist src-tauri/binaries src-tauri/resources src-tauri/runtime` + `touch src-tauri/binaries/{cys,cysd}-<triple> src-tauri/resources/pack.tar.gz src-tauri/resources/pack-manifest.json`(git 무시됨).
- `target/debug/cys·cysd` 가 0바이트로 생기는 일이 있었다(19:41 · 원인 미규명) → test_v116_auto_restore_status 가 PermissionError. `cargo build --bin cys --bin cysd` 로 해소.
- test_dept_teardown_atomicity 는 이 기계 Python 3.14 에서 rmtree ENOTEMPTY 적색 — v1.1.6 스냅샷에서도 같음(선재 · CI 3.12 는 무관 추정).
- ui typecheck 는 node_modules 없어 15 오류(전부 모듈 부재 · 변경 전후 같은 수). node_modules 는 git 무시 대상 아님 → 설치 금지(오염).
- Fable 헤드리스는 `--add-dir` 뒤에 프롬프트를 인자로 주면 디렉터리로 먹힌다 → **stdin** 으로.
- agy 헤드리스는 `--mode plan` 이어도 명령 실행 도구를 쓰려다 거부돼 산출 0 → `.git` 없는 사본에서 `--dangerously-skip-permissions --sandbox`.

## 4. 결정·설계 차이(정직)
- ⑧ 「저장 실패 = 호출자 오류」 대신 버스 경보(master 수용 · 조건 = CSO 구독 단언 → 충족).
- ⑨ 키 판독 실패는 eprintln 만(버스 없음 — signing_secret 에 데몬 핸들 없음) → 사용자는 「승인 계속 거부」 로만 봄. 다음 정기 후보.
- ⑰·⑨ 락 = 기존 `acquire_settings_lock`(윈도 None) → 윈도는 원자 저장만(lost-update 잔존 · 헬퍼 한계).
- ⑩ Q2 는 소스 핀만(행동 시험 없음).

## 5. 9단계 성찰(갈래1 · 요지)
1·2 의도: 「못 읽으면 빈 것으로 접고 덮는다」 4곳+예약·발행 위생·포팅 재작성 — 새 기능 0. 3 파급: 종료코드 12 는 dept_request 가 `create_rc:12` 로 실패 처리(무파괴) · list_depts Err 는 소비처 8곳 중 4곳이 영향 → R1 #3 으로 3곳 수리(prior_install_evidence 는 Err=증거 있음 = 의도 방향). 4 결함 재조사: 수리 자체의 결함 3건을 적대 검증이 적발(tmp 충돌 · 하드링크 폴백 · approvals 무락) — **「판독 실패 = 무변경」 을 넣으면 자가 치유가 사라지므로 쓰기 경합이 영구 잠금으로 격상된다**(이번 티켓의 핵심 교훈). 5 결정론: 모든 합격 = 바이트 해시·grep·rc 단언. 6 방어 불가: 윈도 락 부재(헬퍼 한계). 8 필요성: MINOR #8 은 헬퍼 교체가 범위 밖이라 남김.
