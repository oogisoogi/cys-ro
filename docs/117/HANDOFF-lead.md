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
- `target/debug/cys·cysd` 가 0바이트로 생기는 일 = **원인 규명(순환 1 · 21:1x 재현)**: `cargo test -p cys-app` 이 tauri externalBin 자리표시자(src-tauri/binaries/*-<triple> 0바이트)를 `target/debug/cys·cysd` 로 복사해 덮는다(53MB/72MB → 0 → 재빌드 복구). → test_v116_auto_restore_status 가 PermissionError. 로컬 게이트는 cys-app 뒤 `cargo build --bin cys --bin cysd` 재빌드 필수(CI 무관 · CI 초록).
- test_dept_teardown_atomicity 는 이 기계 Python 3.14 에서 rmtree ENOTEMPTY 적색 — v1.1.6 스냅샷에서도 같음(선재 · CI 3.12 는 무관 추정). → **정정(순환 1)**: 좌석 env 누출로 설치본 데몬이 임시 폴더에 쓰던 탓으로 보인다【추정】 · 수리(e8de7be6·ec777382) 뒤 로컬 ALL PASS 실측(§6).
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

## 6. 순환 1(후임 159 · 원 계정 · 20:46~) — int/117 통합
- 브리프 원장 = spawn-worker brief surface:1158 20:45:55 · 판정 master#2c56ce50(누수 ⑴⑵⑶ 수용 · 부수 고지 처분).
- 병합(int/117 · 로컬): c4d7c43f ← fix/117-store 49881db7 · 그다음 ← fix/117-brand 27e92f62(master 수용 머리 · 로컬 f59dd8e4 는 그 위 HANDOFF-brand 문서 1커밋이라 제외) · 텍스트 충돌 0 · 합성물 `gen_ceo_template --check`·`gen_released_directive_hashes --check` GREEN(재생성 불요).
- 시험 cysd 누수(CSO 20:43 · 고아 9 · 약 340MB): 원인 = cys-dept:29-35 가 좌석 env `CYS_CYSD_BIN`·`CYS_CYS_BIN`(앱이 넣은 설치본 경로)을 1순위 채택 → 시험 가짜 대신 설치본이 가짜 HOME 에서 돌아 데몬 자동 기동. 걸린 시험 = test_dept_b11_lock(대체 호출 6) · test_dept_teardown_atomicity(9 · A4 적색) · test_dept_creds_seed(대체 cysd · 2 적색) — 부서 시험 19개 전수 실측(두 키를 기록용 가짜로) · 나머지 16 = 0. 수리 e8de7be6 = 세 시험 env 에서 두 키 제거(test_ceo_pending_gate:75 선례) → 대체 호출 0 · 3개 초록. CI 러너엔 두 키가 없어 CI 초록은 원래 가짜 경로(유효).
  · §3 의 「teardown_atomicity 는 Python 3.14 rmtree ENOTEMPTY 선재 적색」 은 이 누출(임시 폴더에 데몬이 계속 씀)로 보인다【추정】 — 수리 뒤 로컬 ALL PASS 실측.
  · 게이트 스크립트는 좌석 `CYS_*` env 를 전부 비우고 돈다(CI 대칭 · 같은 누출 재발 차단).
- 부수 기록: 20:46 `javis_todo_stamp.py --apply`(cys todo-path 안내 문구대로 실행)가 팩 round/ 의 다른 todo 54개에도 선언 블록을 넣었다(mtime 보존 · 내용 추가만) — master 처분 = 되돌리지 않음 · 유지보수 후보(「--apply 기본값이 남의 todo 까지 고친다」).
- CI 편입 18d7fa6d: scripts/tests/test_mac_cli_alias_link.py → ci-branch(macOS) 스텝 + 레인 대조 ALLOWED {ci-branch}(대상 lib 는 팩 밖 · 소비 = 로컬 맥 빌드 스크립트 2개). 레인 대조 로컬 실행 초록 · 등재 제거 뮤테이션 rc=1. 그 밖 새 시험: ui/*.test.ts 3개(deptreg·droppoint·restartplan)는 release.yml `bun test` 글롭이 자동 포함(ci-branch 는 파일 머리 주석대로 UI 잡 없음) · nsis-template/check.py 는 갈래3 가 이미 편입 · test_phoenix_g2_ack_only(갈래2)는 ci 1·release 2 등장.
- ACL flaky(`CYS_PACK_DIR` env 경합): v1.1.6 에 이미 공용 락 `governance::PACK_DIR_ENV_LOCK`(QUEUE_ENV_LOCK·ACL_ENV_LOCK 별칭 · governance.rs:6607·11327 · handlers.rs:8433) 있음. cysd 크레이트 안 `ENV_PACK_DIR` set/remove 106곳 정적 대조 = 락 밖 0(예외 daemon_with_acl·daemon_auto = 호출자가 ACL_ENV_LOCK 보유 헬퍼). 즉 input HANDOFF §5-⑥ 의 「원작자 공용 락 우리 판 미편입」 은 사실과 다름 · 남은 경합 원인은 미특정(다른 env 키 또는 가드 밖 스레드 추정) → 기록만.
- 소비처 grep 교훈: 18d7fa6d 에서 「release 는 mac-bundle-common.sh 를 source 안 함(.github grep 0)」 이라 적었다가 적대 R1(agy BLOCK · Fable MAJOR)에 적발 — release.yml:684 → build-macos-signed.sh:37 간접 소비. **소비처는 직접 참조 grep 이 아니라 호출 사슬(워크플로 → 스크립트 → source)로 센다.** 92c79e41 로 release 맥 레그 편입 + ALLOWED {ci-branch, release}.
- R1 반영: ec777382(부서 시험 3 = CYS_* 전량 제거 · b11·teardown cysd 스텁 + CYS_NO_AUTOSTART=1 · creds_seed 는 launch 시험이라 자동 기동 금지 제외) · 2d72faa2(UI typecheck 8 → 0 · bun-env.d.ts toMatch · restorebrief readFileSync(URL)).
- 게이트(20:57~21:2x ≈ 27분 · 좌석 CYS_* 비움): lib 550 · cys 344 · cysd 1212 · app 174 · gen 2 · UI 1471 · typecheck 0 · 팩 62/62 · 건강 150/0/1 · NSIS 3 · mac-alias · 레인 대조 0. ⚠ 게이트 스크립트를 실행 중 편집해 bash 가 어긋나 끝 단계가 문법 오류 → 남은 단계 따로 실행(실행 중 스크립트 편집 금지).
- push(master#a4c6daf5 재승인): fix/117-int @ec777382 · CI = ci-branch 36567990615 · windows-build 36567990669 · windows-health 36567990826.
- E2 「앱 데이터까지 지우기」 = **박사님 결정 완료(21:1x · 유지)** — 칸 없이 자동 보관 + 사용법 「완전히 지우려면」 한 줄(BACKLOG-117 · 문서 몫).
- 갈래1 내부 MINOR(적대 R1 Fable 범위 밖 관찰 · 수리 안 함): cys-dept:1855 down-sock 역인덱스가 `json.load(open(p))` 라 BOM 흡수 미적용.
- 남음: 적대 R2 판정 · CI 3 결과 · 갈래2 input 병합(153 R2 중 → master 수용 뒤).
- 적대 R2(스냅샷 ec777382 · 수리 3커밋): Fable **ACCEPT**(MINOR 2 · NIT 2) · agy **REVISE**(MINOR 1 = release 스텝이 맥 두 레그 중복 실행 · 관례 = `matrix.target == 'aarch64-apple-darwin'`) → 반영 커밋(release.yml 조건 + 「적색 = 윈도 단독 발행도 막힘」 주석 = Fable MINOR #2). 레인 대조 초록.
  · 기록만(범위 밖): Fable MINOR #1 — 부서 시험 3개(b11_lock·creds_seed·teardown_atomicity)는 **어느 워크플로에도 이름 등재 0 = 0레인 실행**(v1.1.6 선재 · 이번 env 수리를 되돌려도 CI 가 모른다) → 편입은 다음 정기 후보. NIT #3 레인 대조가 스텝 `if:` 조건을 안 봄(조건이 좁혀져 실행 0 이 돼도 초록). NIT #4 인용 선례 test_ceo_pending_gate.py:73-80 은 update 뒤 pop 이라 CYS_DEPTS_JSON 이 지워짐(cys-dept:25 $HOME 폴백이 같은 경로라 우연히 동작) → 별도 티켓 후보.
- 갈래2 병합(master#e77bbb4c 병합 가): f3c916da ← fix/117-input @19dac8e8(F4 수리 3285af12 포함) · 텍스트 충돌 0 · 합성물 --check 2종 GREEN · 레인 대조 비대칭 0.
  · `#[cfg(` 시험 속성 diff(master 조건 · 스크래치 cfgdiff.py = 시험 함수마다 붙은 #[cfg…]/#[ignore] 목록을 두 리비전에서 비교): v1.1.6=2270 → f3c916da=2313 · 사라짐 0 · 새로 43 · **속성 바뀐 시험 0**. 도구 검산 = F4 결함판 e980d563 에 대면 `governance.rs::v115_seat_inject_guarded_holds_vacant_agent_seat` 1건(#[cfg(unix)] 상실)을 잡고 수리판 19dac8e8 은 0.
  · 1.1.8 후보(갈래2 남은 위험 · master 지정): F1 사람 키가 CR 전 수백 ms 창에 섞이면 사람 몫 잔존 · F2 µs 창 · F3 열거 시험의 문자열 앵커.
- 윈 스모크 ③ 판정 교체 f8260cdd(master#55edc55d) · 갈래2 통합 적대(Fable ACCEPT MINOR 3 · agy BLOCK 1 = 실측 반증 기각) → 9d52157e(문서 주석 4곳 v1.1.6 배치 복귀 · handlers pause 시험 #[cfg(unix)]).
- 게이트 run2(3916b8ef · 21:56~22:21 · 25분 · cys-app 뒤 재빌드 포함): lib 550 · cys 351 · cysd 1226 · app 175 · gen 2 · UI 1474 · typecheck 0 · 팩 63/63 · 건강 150/0/1 · NSIS 3 · mac-alias · 레인 대조 0 · 남은 cysd 0.
- push 3(master#0a98321b): fix/117-int @9d52157e(25a1601e..9d52157e FF) · CI **3종 초록** = ci-branch 36575046483 · windows-build 36575046447 · windows-health 36575046286.
  · 윈 스모크 ③(windows-build 36575046447): ⓐ 대상 데몬 pid 소멸 PASS(3172) · ⓑ 파이프 해제 PASS · 재기동 pong·새 세대 PASS · ⓒ 고아 없음 PASS(해당 없음 = taskkill 이 트리 전부 종료) · WARN 0 · win_smoke PASS.
  · ⚠ 정직 고지: 트리 조회(Win32_Process)로 pong→identify 가 약 5.6초(13:52:54.7→13:53:00.3)로 늘었다 — 기동 직후 자식 트리가 끝날 시간이 생겨 경합 창 자체가 줄었을 수 있다【추정】. 새 판정의 WARN·ⓒ 경로는 이번 표본에서 실측되지 않았다.
  · 이전 통합판 2/2 적색(36567990669 · 36568135853)은 교체 전 판정(rc0)의 결과. 통합판 윈도 표본 3개 중 교체 판정 = 1개(초록).

## 7. precut(TICKET=cysr-117-precut · 09-30 07:36~)
- master 정본 게이트 9d52157e = 106 스텝 rc 0 · 사라진 스텝 0(master#f3625453). 계획서 docs/117/PRECUT-117.md + 박사님 윈 확인표 docs/117/WIN-CHECK-117.md = 9b741944 · master 수용(master#e134e519).
- P1 판 번호 범프 dfcfe2e8(버전 SOT 8곳 · version-check 상호·v1.1.7 단언 rc 0 · test_version_sot_mutation 14건 · cys 351 · app 175 · UI 1474 · cysr --version = cysr 1.1.7) → push fix/117-int 9d52157e..dfcfe2e8(b83086e0·9b741944 문서 2개 동반) · CI = ci-branch 36641441026 · windows-build 36641440849 · windows-health 36641441087.
- 자기 정정: E3 「같은 판이면 다른 갈래」 주장 틀림(installer.nsi:265-267·335-337 = 같은 판·높은 판 같은 자동 경로) → P1 사유 = 판 표시·갱신 판정.
- 다음(master 발주): §1 정밀 디버깅 = 계정2 3좌석(S1 A1+A2 · S2 B1+B2 · S3 C1+C3+C2 정독 · 보고만) → 차단 4종 결함은 이 좌석으로 라우팅(수리 · 건당 K2 25분) · §2 VM 축 4·2·3 = P1 push 뒤 계정2 VM 좌석 · WIN-CHECK = master 보관 · 박사님 실기 시각 = 준비 완료 뒤 master.
- 남은 것: CI 3종 @dfcfe2e8 결과 · 새 windows-build 아티팩트 이름·바이트 【진행】 · 디버깅 결과 대기.

## 8. fix-blockers(TICKET=cysr-117-fix-blockers · master#2f4fc93f · 09-30 08:2x) — 순환 뒤 새 세션이 할 일
- 확정 차단 2건(S1 디버깅 발견 · agy BLOCK + codex astra BLOCK 수렴). 근거 원문 = `~/axdev/master/reports/cysr-117-plan/dbg/codex-1R-out.md`(52줄 · 먼저 읽는다) · agy = 같은 폴더 `agy-1R-out.md` · 재현 = `c3_repro_test.py` · `a1_repro_empty_files.py`(v1.1.6 대조 `a1_repro_empty_files_v116.py`) · `a1_dept_unreadable_ext.py` · 변이 = `a1_mutations.py`·`c3-mutate.py`.
- 순서(master 지정): ① C3-F1(작음) → ② A1 설계 1쪽(잠금·게시 규약) → ③ codex astra 1R 설계 검토 → ④ 실패 시험 먼저 → ⑤ 구현 → ⑥ 변이 → ⑦ 게이트 전체(스크래치 gates.sh 형식 · 좌석 CYS_* 비움 · cys-app 뒤 재빌드) → 【확인요청】. **push = master 게이트(master 정본 게이트 재실행 뒤).**
- ⑴ C3-F1 거짓 안심 알림(20~40줄 · 시험 5~6): `cysjavis-pack/bin/javis_dept_request.py` — `_create_step`(:1698 · catalog_upsert → write_mission → ensure_dirs 순) · `_run_step`(:1840 · 일반 예외 = `_fail(r,"crash:…")` 만) · `_fail`(:1656 · leftover 있을 때만 기록) · 알림 `row == 4`(:1033-1036 · leftover 부재 = 「남은 것은 없습니다」). 수리 = 완료 효과·확인 가능한 잔여물 기록 · 잔여 확인 실패 = 「남은 항목을 확인하지 못했습니다」 · 확인된 경우에만 「남은 것은 없습니다」 · **자동 삭제 추가 금지** · 「모든 예외에 카탈로그 1개」 식 고정 문구 금지(카탈로그 생성 전 실패에서 거짓). 시험 = 두 폴더 예외 · 카탈로그 생성 전 실패 · 잔여 확인 실패 · 중복 재제안(rc 5) · discard 후 재생성.
- ⑵ A1-F1~F3 0바이트 = 영구 잠금 = 1.1.7 회귀(v1.1.6 자가 치유) · 100~180줄 · 시험 12~16. **원칙 = 정확히 0바이트만 복구 · 권한 오류·비어 있지 않은 손상 = 계속 무변경 거부**(v1.1.6 「모든 오류 = 빈 상태」 회귀 금지).
  · F1 `.approval-secret` — `src/bin/cysd/approval.rs` `signing_secret_at`(:427 · hard_link 게시 :453 · create_new :482): 공통 프로세스 간 잠금 → 잠금 안 재판독 → 임시 키 작성·권한·동기화 → 게시. 부재 생성·빈 파일 복구·create_new 대체 경로 **전부 같은 규약** · 게시 실패를 성공으로 반환 금지 · 옛 승인 자동 재서명 금지 · 옛 데몬은 새 잠금을 모름 = 갱신 시 데몬 종료 필요(기록). 잠금 헬퍼 후보 = `src/pack.rs:681 acquire_settings_lock`(윈 None = 헬퍼 한계 · HANDOFF §4).
  · F2 `approvals.json` — `load_records_at`(:555): 기존 읽기·변경·저장 잠금 안에서 0바이트 = 빈 목록 · 선두 BOM 뒤 유효 JSON = BOM 만 제거하고 파싱(BOM 파일 전체를 빈 목록으로 접지 않는다).
  · F3 `depts.json` — `cysjavis-pack/bin/cys-dept` `reg_init`(:293 · `[ -f ]` + 잠금 밖 `printf >`) → 공통 잠금(:341-348 fcntl.flock 관례) + 원자 게시 · 읽기·쓰기 경로 같은 0바이트 규칙 · 「목록 초기화」 와 「기존 부서 복구」 알림 구분(부서 폴더·데몬은 복구 안 됨) · 비어 있지 않은 손상 보존. GUI/Rust 쪽 list_depts(src-tauri main.rs list_depts_at)도 같은 규칙인지 대조.
  · 시험 필수: 세 파일 0바이트 회귀 · 비어 있지 않은 손상 보존 · BOM 보존 · 다중 프로세스 게시 · create_new 직후 중단점 결정적 경합.
- 함정 이월: §3 전부 + 좌석 env CYS_* 누출(시험·게이트) · externalBin 0바이트(cys-app 뒤 재빌드) · 실행 중 스크립트 편집 금지 · zsh 는 따옴표 없는 변수를 안 쪼갠다(`${=V}`) · `$r:s` 는 zsh 수식어(`${r}:` 로).
- 상태: fix/117-int 원격 = dfcfe2e8(1.1.7 범프) · 로컬 int/117 = 그 위 225cb312(HANDOFF §7) + 이 §8 커밋 = 미push.
