# HANDOFF-U5 — 설치 링크 잠금 참가·위임 + 윈 롤백 자산 보존 (TICKET=cysr-118-u5-install-link)

- 브리프 = `~/axdev/master/briefs/2026-10-07-cysr-118-u5-install-link.md`(master#fb5f4165) · 착수 2026-10-07 07:25 · 좌석 u5@surface:1297
- 트리 2: cys `~/axdev/.wt/cys-118-u5`(가지 u5/install-link-118 off 8bcd39aa) · ai-jarvis `~/axdev/.wt/aj-118-u5`(같은 가지명 · push 0)
- 설계 정본 = `DESIGN-AUTOUPDATE-118.md` §3-2(136~142행) · §3-7 ②(245행) · 계약 정본 = 코드(`src/update/lock.rs`)

## §0-5 5판 델타(master#1e386cf2 · Opus 4R 수렴 예 MINOR 2 · agy 4R 수렴 예 · cys 쪽 = merge/v0.14.43 fb6fbf37 병합 진행)
- ① n1 = 판정 cys 없음일 때 종결 판정을 두 슬롯 중 `generation` 큰 쪽으로(cys journal.rs commit_next 와 같은 최신 판별 · 한쪽만 = 그쪽 · 둘 다 못 읽음 = 종전 갈래) — aj 2a091fc · 시험 맥 ⓓ 2(음성 대조 = 한 슬롯만 읽으면 적색) · pwsh 순수 2 · 사본·핀 재동기.
- ② n2 = §0-4 ① 에 잔여 고지 1줄(본문 받는 중 정지 = 시한 밖일 수 있음 · 미실측).

## §0-4 4판 델타(master#c60b7de4 · agy 3R 수렴 예 · Opus 3R MAJOR 1·MINOR 9 · 전건 채택 · 상한 1.5h · 원문 = docs/update/REVIEW-U5-{agy,opus}-3r.md untracked)
| # | 지적 | 4판 수리 | 커밋(aj · cys) |
|---|---|---|---|
| ① | M1 자산용 설치기 받기 시한 없음 | `-TimeoutSec $CysAssetsDlTimeoutSec`(900 = 본 받기와 같게 · 시험만 env 로 줄임) · 시한 초과 = catch = 설치 계속 · 맥 = 이 갈래 없음(롤백 자산 = 윈 전용 · 맥 cys 받기 = `curl --max-time 900` 확인) · ⚠잔여(5판 n2 · **미실측**): `-TimeoutSec` 은 응답 머리 전 정지만 끊는다고 알려져 있다 — 본문을 받는 도중 멈추면(PS 7.4+ 등) 이 시한이 안 걸릴 수 있다 · 본 받기([5/10] `-TimeoutSec 900`)와 같은 잔여 · 시험은 「붙기만 하고 머리 전 무응답」 꼴만 잰다 | aj 38244b5 |
| ② | m1·m9 실패 갈래 무화면·무집계 · 시험 0 | 화면 1줄 「자동 갱신을 위한 준비 파일을 이번에는 받지 못했습니다 — 설치는 계속됩니다(이 설치 한 줄을 다시 실행하시면 다시 받아 봅니다)」(위협·일정 약속 0) + 기록 1줄 + `Send-Progress '5/10' info rollback-assets:dl-fail` · 시험 = 답 없는 TCP(붙기만) 서버로 그 갈래를 실제 통과(pwsh 맥·윈 · 맥 셸 = 해당 갈래 없음) | aj 38244b5 |
| ③ | m2 종결 저널까지 J-UPD-03 | 판정 cys 없음일 때 journal.json `state` 가 종결(DONE·DEFERRED·RB_DONE·RB_FAILED·PACK_DONE = cys is_terminal)이면 go · 맥 ⓓ · 윈 순수 1 | aj 38244b5 |
| ④ | m4 순간 실패까지 J-UPD-03 | nolock 만 제자리 재확인 3회(1초 · 맥은 회당 배경 perl 응답 대기 ≤10초 = 상한 ≈33초) 뒤 J-UPD-03 · 그사이 busy = J-UPD-01 즉시(기다림 루프 재진입 0) · 맥 ⓙ(재확인 정확히 3) · 윈 분류 1 | aj 38244b5 |
| ⑤ | m3 저널 판정에 132MB 재검증 | `--journal-state` = 저널만(seq 포함) · `--assets` 를 줄 때만 n7_installer · 소비자 = bootstrap 두 갈래뿐(runner·U2·check grep 0 — U2 러너 결과 계약 무관) | cys bb7fe634 · aj 38244b5 |
| ⑥ | m5·m6 CI 403 · 핀 = 파일 커밋 | CI 403 = 「러너 차단 · 대조 0」 따로 이름 · §6·§0-3 ③ 문구 정정 · `--check` 판정 = 해시 줄만(aj_commit = 정보) — 블록 밖 수정 = same · 맥 ⓘ′ | aj 38244b5 · cys (이 커밋) |
| ⑦ | m7·m8 낡은 주석 · 일정 약속 문구 | sh·ps1·맥·윈 시험 머리·HANDOFF §2·§0 결정 3 · 「고치는 중입니다」 괄호 삭제 · nolock 복원 실패 기록 줄 = 실제 상태 | aj 38244b5 · cys |
| ⑧ | m9 윈 분류 시험 · 하네스 대역 | 윈 nodir/nolock 분류 + 재확인 시험 · 하네스 = 본문에서 뗀 `u5-deps.ps1`(핀 3번째 줄) + 실 경로 단언(출력 · rc≠0 null · 상한 null) | aj 38244b5 · cys |
- 설계 문서(DESIGN-AUTOUPDATE-118 §3-2 140행)에 J-UPD-03·nodir 편입 줄 = master 문서(3R m7 끝 · 워커 무접촉).
- 잔여 고지(3R N4): 맥 `txn_check_holder` 는 창을 좁힐 뿐 닫지 않는다 — 확인(kill -0) ↔ 위임 cys 호출 사이(rotate 쪽 최대 약 10초 = 기준선 list·--version) 창은 남는다(배경 perl 만 따로 SIGKILL 되는 빈도 낮은 꼴).

## §0-3 3판 델타(master#2f038a50 · 적대 agy 2R BLOCK 1·MINOR 1 + Opus 2R MAJOR 3·MINOR 9 · 전건 채택 · 상한 1.5h · 원문 = docs/update/REVIEW-U5-{agy,opus}-2r.md untracked)
| # | 지적 | 3판 수리 | 커밋(aj · cys) |
|---|---|---|---|
| ① | 「기다림」 오분류 4(N1 · agy BLOCK·MINOR) | busy 만 J-UPD-01(재시도 3 · 첫 재시도 화면 1줄) · unsafe · nolock(자리는 있는데 못 엶·씀·복원 실패 · 파일이 폴더 자리 차지) · 위임 거부 · 판정 cys 없는 30분+ 저널 = **J-UPD-03 「잠금 자리 이상」**(원인별 문구 · 재시도 0 · 원격 해결 열림 · help/J-UPD-03) · 폴더 없고 못 만듦 = nodir → lock.rs participate 처럼 잠금 없이 진행 + 기록 1줄 · 판정 cys 없음 + 저널 방금 = J-UPD-02 | ca9cec9 |
| ② | 같은 판 자산 없음 재다운 실패 = 막힘(N2) | `Receive-CysSetupForAssets` = 1회만 받기 · 실패(404·410·망·지문) = 화면·기록 1줄 + return 0 → [6/10] 건너뜀(설계 결정 4 복원) | ca9cec9 |
| ③ | CI 대조 = 사본↔핀뿐(codex8/agy2 잔여) | §6 스테이징 배포 필수 관문 `sync --check <cys main>`(master 집행) · CI 계약 스텝 = 공개 /install/next/ 블록 ↔ 핀(불일치 적색 · 404·블록 없음 = skip 명시 · 망 = 경고 · ⚠4판 정정: GitHub 러너 = 403 차단이라 **지금 대조 0**(경고) — 실효 관문 = §6 sync --check) · yml 주석 정정 | (이 커밋) |
| ④ | 위임 거부 단언 1갈래(N3) | Stop-CysTxnRefused **실본문**을 자식 프로세스로(문구 · J-UPD-03 · exit 26) · 구조 단언 = rotate rc 26 · 설치기 exit 6 · setup.exe `Invoke-WithCysTxnEnv` 포장 | ca9cec9 |
| ⑤ | acquire 순서 서술 · perl 단독 SIGKILL · 복원 실패 삼킴(N4·N6) | HANDOFF:13·94 정정 · 맥 `txn_check_holder`(위임 init-pack·rotate 직전 perl 생존 → 죽었으면 J-UPD-03 끝) + `cys_txn_env` 토큰 미적재 · 복원 실패 = 기록 1줄 + nolock(J-UPD-03) | ca9cec9 |
| ⑥ | 묘비 실패 + 창 폴백 · 재시도 무화면(N5·N8) | 창 폴백 직전 안내 1줄(맥 TXN_STUCK · 윈 CysTxnLock 남음) · 첫 재시도 화면 1줄 | ca9cec9 |
| ⑦ | 주석·문서 잔존 · 맥 감지 표 미포장 · ping 서술(N7·N9) | sh·ps1 저널 판정 머리 · u5-mac-lock.sh:8 · HANDOFF:28-29 폐기 표시 · yml · 맥 phoenix-identity·agent-detect·doctor = cys_txn_env · HANDOFF:14 정정 | ca9cec9 · (이 커밋) |
| ⑧ | 자산 = 존재만 · 윈 journal-state 시한 0(N10·N11) | cys `--journal-state` 에 `seq`·`n7_installer`(check::installer_assets_ok 재검증) · ps1 = Get-CysAssetsWord · journal-state·자산 판정 = Invoke-CysCapped 20초 | cys 6baee372 · ca9cec9 |
- 덧붙인 것(고지): 자산 판정 seq 0(미발행 빌드) = 판정 없음(aj 9f0ab37 · 실측: 로컬 debug cys `--journal-state` = seq 0 · n7 false → 그대로면 [5/10] 이 매번 받음) · 롤백 자산 못 챙김 문구 「챙깁니다」 → 「챙겨 봅니다」(Opus codex7 부분 지적 · 404 지속 때 거짓 약속) aj a0827c9 · 맥 「폴더 자리에 파일」 = nolock(lock.rs 「있는데 못 씀」 짝 · nodir 아님).
- 시험(맥): u5-mac-lock 36/0(ⓙ′ nodir · ⓝ perl 단독 사망 · ⓓ 오래된 저널 J-UPD-03 · ⓒ 기다림 1줄 · ⓕ 실본문 문구) · 음성 대조 = ⓝ(holder 확인 제거 → 위임 호출이 나감 = 적색) · pwsh 32/0 · 하네스 20/0 · CI 스텝 본문 맥 실행 = 실 스테이징 skip(옛 판) · 모의 같음 ok · 모의 1바이트 다름 적색.

## §0-2 2판 델타(master#9502b67b · 적대 codex 1R BLOCK 3·MAJOR 5 + agy 1R BLOCK 1·MAJOR 2 · 전건 채택 · 상한 2.5h · 원문 = docs/update/REVIEW-U5-{codex,agy}-1r.md untracked)
- ★1판 설계 결정 2(위임 거부 → 무잠금 재실행)·nolock 폴백·결정 3 의 「판정할 cys 없음 = go」 는 **폐기**(설계 §3-2 140행이 이긴다). 아래 수리 설계가 2판 정본.
| # | 지적 | 2판 수리(파일·자리) | 상태 |
|---|---|---|---|
| ① codex1 BLOCK | 위임 거부 시 무잠금 재실행 | sh `txn_invoke_logged`·`cys_rotate_state` rc26 갈래 · ps1 `Invoke-CysTxnLogged`·`Get-CysRotateState` rc26 · `Step-InstallCys` exit 6 갈래 → 전부 「J-UPD-01 + 문구 + 설치 즉시 끝(rc 26)」 · 재실행 삭제 | ✅ 맥 aj 554ba4c · 윈 aj(이 커밋 다음) · 사본 재동기 |
| ② codex2 BLOCK | nolock = 성공처럼 진행 | sh `txn_hold_try` nolock → busy 와 같은 재시도(4번) 뒤 끝 · ps1 `Lock-CysTxnOnce`·`Enter-CysTxn` 같음 · 시험 = 폴더 쓰기 불가 주입 → rc 26 | ✅ 맥 aj 554ba4c · 윈 aj(이 커밋 다음) · 사본 재동기 |
| ③ codex3 BLOCK | 묘비 실패 삼킴 · Delete→Move 창 | ps1 `Write-CysTxnFile` 폴백 삭제(임시 → Replace 재시도만 · 실패 = throw) · `Unlock-CysTxn` 묘비 실패 = **잠금을 쥔 채** 재시도(100ms×30) 뒤 그래도 실패면 쥔 채 종료(프로세스 끝 = OS 해제 · 묘비 없는 낡은 기록은 ② 로 걸러짐 — 단 codex 시나리오는 「잠금 풀림 + 묘비 없음」 창이라 프로세스 종료 전까지 쥐는 것이 핵심) · sh perl `wr` 실패 = 해제 0 · 쥔 채 종료 · lock.rs:326-350 무수정(관찰: 검증이 「잠금 held + 기록 두 번 동일」 이라 묘비 없는 옛 기록 + 새 러너 잠금 창을 구조로 못 가른다 — acquire 순서 = 배타 잠금(flock/LockFileEx) → 새 소유자 기록 — 그 사이 창은 새 소유자가 잠금을 쥔 뒤라 구조로 남는다 · 이 창을 닫는 것은 「옛 소유자가 묘비 없이 잠금을 놓지 않는다」(③) 쪽이다 · 3판 정정(Opus 2R N4)) | ✅ aj 1d7c8b0 · cys df427993 — 바꿔치기 = FileRenameInfoEx(바꾸기+POSIX) → MoveFileEx(Rust std::fs::rename 과 같은 길 · CI [ⓔ] 3.3초 = File.Replace 상시 실패 실측 → 폴백 삭제만 하면 적색이라 바꿈) · 맥 ⓚ 2 · 윈 ⓚ 2 + 구조 1 |
| ④ agy1 BLOCK · codex4 | 토큰 env 프로세스 전체 | sh: `export CYS_UPDATE_TXN` 삭제 → `txn_invoke_logged`·rotate 호출 줄에만 `CYS_UPDATE_TXN="$TXN_TOKEN"` 앞붙이기 · 데몬 자동 기동이 필요한 일반 cys 호출(new-surface·daemon install·list 등 — ping·daemon status 는 순수 프로브라 자동 기동 0 · cys.rs:2795-2799 · 3판 정정 N9)은 잠금 쥔 동안 자동 기동 거부(cys.rs:4665) → 그 호출들에도 토큰 env 를 줄 것인가 = 자동 기동 가드는 env **존재만** 본다 → 일반 cys 호출 래퍼 1개(`cys_txn_env`)로 그 호출에만 env · `open -a` = `env -u CYS_UPDATE_TXN` · `exec claude` = 해제 → 즉시 exec(그 사이 cys 호출 0 · TOCTOU 사유: 러너는 N2 사람 입력 20분 유휴·지터 0~45분이라 해제~exec 수 ms 창에 S7 진입 불가 + exec 대상은 claude(러너 교체 대상 아님)) · ps1: `$env:` 전역 대신 `Invoke-WithCysTxnEnv { … }`(참가 명령·setup.exe·daemon 자동 기동 호출만) · Claude 설치기/로그인 = 토큰 0 | ✅ aj 6bdde7b · cys 4e35a19e — 맥 cys_txn_env 7곳 + rotate 앞붙이기 · 윈 Invoke-WithCysTxnEnv 11곳 + rotate psi · 물려받은 토큰도 진입에서 지움 · `open -a`·`env -u` 는 불요(셸에 토큰이 없다) · 맥 ⓛ 2 · 윈 ⓛ 실물 1 + 순수 1 + 구조 1 |
| ⑤ codex5 MAJOR | 기존 폴더 DACL·reparse 미검사 | ps1 `New-CysTxnDir` → 진입마다 `Get-Acl` SDDL read-back(소유자 = 나 · 허용 ACE = OW·SY·나·BA 상속 꼴만 = cys sd_is_private 규칙) + `(Get-Item).Attributes -band ReparsePoint` = 0 · txn.lock·txn.owner.json 파일도 같은 검사 · 불일치 = J-UPD-01 끝 · sh = `stat` uid=나·mode&077=0·심링크 아님(perl 안 lstat) | ✅ aj 3cc3e2f · cys 6418abee — 윈 Test-CysTxnPathPrivate(ReparsePoint + SDDL = sd_is_private 이식 · 벡터 20 그대로) · 맥 perl priv · 불일치 = unsafe(재시도 0) → J-UPD-01 · 맥 ⓜ 3 · 윈 실물 3 + 순수 1 |
| ⑥ codex6 MAJOR | 저널 있음 + 판정 cys 없음 = go | sh `txn_journal_verdict`·ps1 `Get-CysTxnJournalVerdict` 끝 줄 go → **wait** · 재설치 허용 = cys 가 degraded·corrupt 를 명시한 때만 | ✅ 맥 aj 554ba4c · 윈 aj(이 커밋 다음) · 사본 재동기 |
| ⑦ codex7·agy2 MAJOR | 본문 404 → N7 영구 hold | 실측(10-07 09:4x): 러너는 보관소에서 받지 않는다 — `grep 'releases/\|archive' src/update/{realops,check,auto}.rs` = 0(N7 = 검증만 `check.rs:547-570`) ⇒ bootstrap: 설치판 자산이 없으면(`cys self-update --preserve-installer` 가 아니라 먼저 판정 — `installers\<seq>` 4파일 없음) 같은 판이어도 [5/10] 이 핀 설치기를 다시 받고 [6/10] 건너뜀 갈래에서 `Save-CysRollbackAssets` 재시도(설치 재실행 때마다) + 296(u2-followup n17)에 【질문】 1줄(러너 S8 보관소 받기 미구현) | ✅ aj 1232238 · 8fd43bc · cys 78221478 — Test-CysRollbackAssetsPresent(seq = VERSIONINFO 4번째) · [5/10] 같은 판이어도 자산 없으면 설치기만 받음 · [6/10] 재실행마다 재시도 · hold 사유 = 화면·bootstrap.log 1줄 · 296 【질문】 발신(10:15) → master#c72a59df 답: 러너 S8 받기 = U2 후속 2판 발주 · 접점 계약 무변경 |
| ⑧ codex8·agy3 MAJOR | sync --check CI 미실행 | windows-health 계약 스텝 run 머리: 사본 sha256 핀 대조(`scripts/tests/install-link-u5/CONTRACT.sha256` = aj 원본 커밋 SHA + 원본 블록·시험 sha256 · sync 도구가 --write 때 생성) → 사본 해시 ≠ 핀 = 적색 · 음성 대조 1 = 사본 1바이트 변조 → 그 검사 적색(스텝 안 자기시험) | ✅ aj 8fd43bc · cys 18a92a12 — sync --write 가 CONTRACT.sha256(원본 마지막 커밋 + 사본 sha256) · dirty 원본이면 --write 거부 rc 3 · CI 계약 스텝 머리 = 핀 대조 + 음성 대조 1(1바이트 변조본) · 맥에서 스텝 본문 실행 = 양성 rc 0 · 사본 변조 = 적색 |
- ★순환 지점(10-07 · CTX 59% jsonl 라이브): ①②⑥ 끝(맥 u5-mac-lock 23/0 · pwsh 22/0 · 하네스 12/0) · **다음 = ③ → ④ → ⑤ → ⑦ → ⑧ 순서** · 각 항목 = 위 표의 「2판 수리」 칸이 설계 정본 · ⑦ 은 296 에 보낼 【질문】 1줄을 master 경유(허브-스포크)로 · 미러 push 는 ⑧ 까지 끝낸 뒤 1회 · 채택/반박 표 11행은 §7(신설)에 · 시험 재현 = §5.
- ★2판 수리 끝(10-07 10:3x · ③④⑤⑦⑧): 맥 u5-mac-lock 31/0 · pwsh 28/0 · 하네스 17/0 · update:: 227/0 · secret-scan clean · 미러 push 1회 b6bb636e..18a92a12 · 3런 = §4 2판 칸.
- 완료 = 맥 전수 0 실패(update::·cys·u5-mac-lock·pwsh) + 미러 3런 success(⑧ 실제 실행) + 채택/반박 표 11행 → 【확인요청】.

## §0 델타(다음 사람이 먼저 읽을 것)
- 브리프 §2 1~7 구현·커밋 끝. 남은 것 = 미러 CI 판정(아래 §4 CI 칸) · master 게이트 · 적대 리뷰(master 발주) · 스테이징 배포·윈 실기(master).
- ★설계 결정 1(브리프 §2-1 「네 설계」): **잠금을 쥐는 것 = 설치 도우미 스크립트 자신(ⓐ)** — 맥 = 배경 perl 의 flock(소유자 pid = 설치기 셸 `$$`) · 윈 = 설치기 PowerShell 프로세스의 `FileStream.Lock(0,1)`(소유자 pid = `$PID`).
  근거 1줄: 설치 **전**엔 믿을 cys 가 없고(윈은 NSIS 안 cys.exe 를 꺼낼 수 없다) · 위임 검증 ③ 이 「소유자 pid = 자식의 조상」을 요구해 따로 뜬 도우미 프로세스는 소유자가 될 수 없다.
  대가: 소유자 기록·시작 시각을 스크립트가 cys 와 같은 식으로 만든다(③′ 짝) → 맥은 실 cys 위임 수용 + 뮤테이션으로 실증 · 윈은 windows-health 계약 스텝이 실물로 잰다.
- ~~★설계 결정 2~~(2판 폐기 → 위임 거부 = J-UPD-01 끝 → 3판 J-UPD-03 끝): 위임이 거부되면(cys rc 26 · 설치기 exit 6 — 시작 시각을 못 맞춘 기계 등) **잠금을 놓고 토큰 없이 한 번 더**(설치는 끝까지 · 그 명령은 평소 참가자). 설치를 깨뜨리는 쪽보다 보호를 한 단계 낮추는 쪽을 골랐다.
- ★설계 결정 3(「판정할 cys 없음 = 진행」 부분은 2판 폐기 → J-UPD-02 · 3판: 저널 30분+ = J-UPD-03): 저널 판정은 스크립트가 하지 않고 cys 새 입구 `self-update --journal-state`(러너 사본 → 설치본 순) — 온전·비종결 = 「복구 대기」(J-UPD-02) · 손상(degraded·corrupt) = 📌18 재설치 길이라 진행 · ~~판정할 cys 없음 = 진행(기록 1줄)~~(2판 폐기).
- ★설계 결정 4: 롤백 자산 = cys 새 입구 `self-update --preserve-installer --setup <설치기>`(본문 받기·검증·놓기 = cys 한 곳 · 러너 S11 보존과 같은 꼴). 못 챙기면(보관소 404 등) 설치는 계속하되 화면 2줄 + 진행 info(조용한 hold 0).
- 덧붙인 것(브리프 밖 · 고지): ① J-UPD-01·02 도움말 페이지 2 + 목록 1줄(설치 창이 그 주소를 안내) ② 두 코드는 「기다림」이라 원격 해결을 열지 않음(맥·윈 각 1줄) ③ 이 창에서 자비스를 띄우는 길(맥 `exec claude` · 윈 `& claude`) 직전 잠금 놓기 — 안 놓으면 자비스 세션 내내 잠금·토큰 env 잔존(그 안 rotate·팩 명령 rc 26).
- 이월 해소: U2 HANDOFF §5 ⓒ(pack-update·pack-plan·init-pack 잠금 배선)는 **이미 병합 트리에 있다**(`src/bin/cys.rs` InitPack·PackUpdate·PackPlan 의 `txn_participate` · 2판 C1) — 이 티켓에서 cys CLI 배선 보강 0.

## §1 변경표(파일:줄은 커밋 시점)
| # | 항목 | 파일 | 커밋 | 시험 |
|---|---|---|---|---|
| ③④ | 입구 2 · N7 판정 함수 분리 | cys `src/update/install_link.rs`(신규) · `cli.rs`(플래그 5 · 갈래 3) · `check.rs`(`installer_assets_ok(_with)` · `rollback_assets_ok_at`) · `mod.rs` | fa3c2c1a · b5646df2 | `cargo test --lib update::install_link` 4/0 · `update::` 227/0 |
| ①②⑤ | 맥 잠금 참가·위임 | aj `site/install/bootstrap.sh`(「자동 갱신 잠금」 절 · 본문 `txn_enter` · init-pack `txn_invoke_logged` · rotate `--txn` + rc 26 재시도 · closing_note 머리 · `exec claude` 앞 · remote_help 기다림 코드) | aj 7acdc76 · 8ddfb0d · 98af5e9 | `tests/install-u5/u5-mac-lock.sh --cys <debug cys> --cys-tree <cys>` 23/0 |
| ①②③ | 윈 잠금 참가·위임·자산 | aj `site/install/bootstrap.ps1`(같은 이름 절 · Enter-CysTxn · Get-CysSetupArgs `/CYSTXN` · Invoke-CysTxnLogged · rotate `--txn` · exit 6 재시도 · Save-CysRollbackAssets · Invoke-WithoutCysTxnEnv(앱·곁 프로그램) · `& claude` 앞 · finally 첫 줄 · Invoke-RemoteHelp) | aj 98af5e9 · 4c404d6 | `tests/install-u5/u5-win-lock.ps1` 맥 pwsh 22/0(순수·구조·시작 시각 식) · 윈 실물 = CI |
| ④ | 윈 CI 계약 | cys `scripts/tests/install-link-u5/{u5-block.ps1(사본),u5-harness.ps1,u5-win-lock.ps1(사본)}` · `.github/workflows/windows-health.yml` 스텝 1 | 8adc9247 · 18880edb · 0f38e898 | 사본 = 원본 바이트(`aj tests/install-u5/sync-cys-contract.py --check`) |
| ⑥ | 도움말 | aj `site/help/J-UPD-01.html` · `J-UPD-02.html` · `index.html` | aj 98af5e9 | — |
| ⑦ | 윈 실기 요청문 | aj `docs/WIN-FIELD-TEST-U5.md` | aj 8909984 | (master 발신) |
- 소요: 착수 07:25 → 커밋 묶음 07:5x(도구 `date` · 커밋 시각) · 계수 = 스크립트 2 + Rust 입구 2 + CI 1 ≈ 30분대(+ CI 대기).

## §2 계약 1줄씩(다음 사람·리뷰어용)
- `cys self-update --journal-state --json` → `{journal: none|ok|degraded|corrupt, state, terminal, lock_held, detail}` · rc 0(3 = 상태 폴더 판정 불가) · 쓰기·잠금 0.
- `cys self-update --preserve-installer --setup <p> [--setup-sig <p>] --json` → rc 0 놓음+N7 참 · 2 거부 · 3 쓰기/seq 0 · 4 받지 못함 · seq = 이 바이너리(`--seq` = 시험 빌드 전용) · 호출자가 txn.lock 을 쥔 채.
- 설치 도우미 소유자 기록 = `{owner:"install-link", pid, txn_id(32 hex), epoch(+1), started_at, boot_id, start_time, released}` · 순서 = lock.rs acquire(배타 → 기록 → 자식·참가자 잠금 확인 → 아니면 직전 기록 복원) · 놓기 = 묘비 → 해제.
- 위임 = 참가 명령에만 `--txn`/`/CYSTXN=` + **그 호출에만** env `CYS_UPDATE_TXN`(맥 `cys_txn_env` · 윈 `Invoke-WithCysTxnEnv`·rotate psi) · 데몬을 띄울 수 있는 cys 호출도 그 호출에만 · 프로세스 전체 env 0(2판 ④).
- 기다림 rc = 26(설치 도우미 끝 코드) · 진단 코드 J-UPD-01(busy = 남이 쥠 · 30초 × 3 재시도 뒤 · 첫 재시도 화면 1줄) · J-UPD-02(복구 대기 · 판정 cys 없음 + 비종결 저널 방금) · J-UPD-03(잠금 자리 이상 = unsafe · nolock(제자리 재확인 3 뒤) · 위임 거부 · 판정 cys 없음 + 비종결 저널 30분+ · 원격 해결 열림) · nodir(폴더 없고 못 만듦) = 잠금 없이 진행 · 판정 cys 없음 + 종결 저널 = 진행(4판).
- 놓기 = 묘비 → 해제 · 묘비를 3초 안에 못 쓰면 **쥔 채**(맥 perl 은 소유 셸이 끝날 때까지 · 윈은 FileStream 유지 · 다음 Unlock 이 재시도) · 토큰·env 는 언제나 거둠(2판 ③).
- 핀 = `scripts/tests/install-link-u5/CONTRACT.sha256`(`# aj_commit <40hex>` + 사본 sha256 2줄) — 손으로 고치지 않는다(sync --write 만).

## §3 안 한 것 · 함정(정직)
- ⓐ NSIS exit 6 「env 누락」 뮤테이션은 **설치기 실물로 못 돌렸다**(맥 = NSIS 없음) — 같은 축을 cys rc 26(⓪ env 누락)으로 맥·윈 CI 에서 재고, 설치기 쪽은 U3 `WIN-NSIS-0A-FIELD.md` F3b + 이 티켓 실기 ①d 몫.
- ⓑ 윈 「미설치 상태」 실기는 Windows Sandbox 전제(노트북 지금 설치·좌석 3 무접촉) — Sandbox 가 없으면 master 가 자리를 정한다(요청문 §0 P4).
- ⓒ 손상 저널 기기에서 설치 도우미는 끝까지 가지만, 그 뒤 좌석이 서는지는 U2 복구기 재구성 몫(설치 도우미는 저널을 지우지 않는다).
- ⓓ reset-clean·reinstall 스크립트는 설계 참가자 목록 밖이라 잠금 무변경.
- ⓔ 윈 PowerShell 7 에서 `Directory.CreateDirectory(path, DirectorySecurity)` 가 없으면 보통 폴더로 만든다(사용자 프로필 상속 꼴 — cys sd_is_private 가 받는 꼴) · 5.1(실 설치 셸)은 보호 DACL.
- ⓕ 미러 첫 런 windows-build 적색 = secret-scan WIN-PATH(시험 더미 경로 `C:\Users\…`) → 0f38e898 에서 제거 · scan clean 실측.

## §4 시험 결과
- cys: `CYS_PACK_DIR=$(mktemp -d) cargo test --lib update:: -- --test-threads=1` → 227 passed 0 failed(07:4x) · `update::install_link` 4/0.
- 맥 실물: `bash tests/install-u5/u5-mac-lock.sh --cys target/debug/cys --cys-tree <cys>` → ok 23 · FAIL 0(실 cys pack-plan 위임 수용 · env 누락/epoch 틀림/토큰 없음/시작 시각 틀림 = rc 26 · 셸 SIGKILL 뒤 1.5초 안 묘비+해제 · 남이 쥠 = 4번 시도 뒤 J-UPD-01 · 자식 잠금 쥠 = 직전 기록 복원 · 저널 4갈래 · 거부 → 한 번 더 · 구조 3 · 사본 대조).
- pwsh(맥): `u5-win-lock.ps1` 22/0 · 하네스 12/0 · `scripts/secret-scan.sh --all` clean.
- 미러 CI(fix/u5-install-link-118 @0f38e898): ci-branch success · windows-build success · windows-health **failure 1건 = U5 계약 스텝**(37543489313 · ok 18 · FAIL 7).
  · 윈 실물 **통과**: [ⓐ] 잡기 · 쥔 동안 남 배타 불가 · **실 cys.exe 가 PowerShell 이 쓴 소유자 기록으로 위임을 받음**(= FILETIME 식 시작 시각 ③′ 짝 · LockFile(0,1) ↔ LockFileEx 교차 · 손 JSON ↔ serde 실증) · [ⓒ] 남이 쥠 = busy·J-UPD-01·기록 무변화 · [ⓖ] 실 기록 = ⓪-a 꼴.
  · 적색 7: 거부 갈래(env 누락·epoch 틀림·토큰 없음·시작 시각 틀림)마다 **debug cys.exe 가 `thread 'main' has overflowed its stack`(0xC00000FD)** — 거부 rc 26 대신 죽음. 그 뒤 놓기·자식 잠금·재시도 시험이 연쇄 적색(죽은 프로세스 정리 중 소유자 기록 교체 실패로 추정 — 덤프 추가).
  · 조치(f1819e50): 계약 스텝을 **출시 빌드 cys.exe** 로(제품 형상) + 적색 시 txn 기록 덤프. 출시 빌드도 넘치면 = U2 참가 거부 갈래의 윈 제품 결함(【경고】 대상 · 이 티켓 밖 수리).
  · 2차(f1819e50 · 37548178821 · 출시 빌드): 거부 갈래 3 = **rc 26 정상**(스택 넘침 = debug 전용 확정 · U2 제품 결함 아님) · 남은 적색 4 = 소유자 기록 **두 번째 바꾸기(묘비) 실패**에서 연쇄(윈 `File.Replace` · 방금 쓴 파일 공유 위반 꼴).
  · 3차(b6bb636e · windows-health 37548828686 **success** · windows-build success): `Write-CysTxnFile` 재시도 100ms×30 → 지우고 옮기기 폴백 → **PowerShell 5.1 ok 25 · FAIL 0 · 7 ok 25 · FAIL 0 · real=1**.
  · ★2판(18a92a12 · 10-07): ci-branch 37556601892 **success** · windows-build 37556601987 **success** · windows-health 37556602014 **success** — U5 스텝: U5-PIN ok(음성 대조 「핀 불일치: u5-block.ps1」 적색 확인 · aj_commit 8fd43bc) · PowerShell 5.1 ok 36 · FAIL 0 · 7 ok 36 · FAIL 0 · real=1(ⓚ 묘비 실패 쥔 채 · ⓛ 자식 env 0 · ⓜ Everyone ACE·junction = unsafe · SDDL 벡터 20 · 롤백 자산 판정).
  · ★[ⓔ] 놓기(묘비 쓰기) = ⓖ 뒤 16ms(1차 3.3초 = File.Replace 30번 실패 후 폴백) — FileRenameInfoEx 바꿔치기가 윈 러너에서 첫 시도에 통과.
  · 맥: u5-mac-lock 31/0 · pwsh 28/0 · 하네스 17/0 · `cargo test --lib update::` 227/0 · `cargo test --bin cys` 589/0 · secret-scan clean.
  · ★3판(a56d010e · 10-07): ci-branch 37562611253 **success** · windows-build 37562611247 **success** · windows-health 37562611289 1차 **failure** = 상담소 팩 `test_writers_vs_mover`(교차 잠금 경합 · 줄 유실 — U5 무관 · 18a92a12 이후 cysjavis-pack 변경 0) → 실패 잡만 재실행(attempt 2) **success**(그 시험 ok ×2). U5 스텝 두 번 다 PS 5.1·7 각 ok 39 FAIL 0 real=1 · U5-PIN ok(aj 9f0ab37).
  · ⚠U5-NEXT(스테이징 블록 ↔ 핀) = GitHub 러너에서 **403**(맥 로컬 curl = 200) → 경고 skip. 러너 IP 차단(Cloudflare 규칙)으로 추정 — 이 대조는 지금 러너에서 실제로 돌지 않는다. 실효 관문 = §6 배포 전 `sync --check`(master). 러너에서 돌리려면 사이트 쪽 허용 규칙 = master 판단.
  · 맥(3판): u5-mac-lock 37/0 · pwsh 32/0 · 하네스 20/0 · `update::` 228/0 · `--bin cys` 589/0 · secret-scan clean.
  · ★4판(fecf311d · 10-07): ci-branch 37568832613 · windows-build 37568832619 · windows-health 37568832575 = 셋 다 1차 **success** · U5 스텝 PS 5.1·7 각 ok 43 FAIL 0 real=1([받기] 답 없는 서버 3초 상한 · [분류] 재확인 3 · [실경로] 윈 실물 통과) · U5-PIN ok(aj 38244b5 · 핀 3줄) · U5-NEXT = 「러너 차단 403 · 대조 0」 경고(정정된 이름).
  · 맥(4판): u5-mac-lock 39/0(ⓘ′ 블록 해시) · pwsh 36/0 · 하네스 24/0 · `update::` 228/0 · `--bin cys` 589/0 · secret-scan clean · M1 음성 대조 = 시한 제거본이 45초 알람까지 멈춤.
  · ⚠debug cys.exe 의 윈 주 스레드 스택 넘침(거부 갈래 = 0xC00000FD)은 시험 빌드 한정 관측 — 출시 무관이나 윈에서 debug cys 로 참가 거부를 재는 시험은 같은 함정(기록만).

## §5 재현
```
cd ~/axdev/.wt/cys-118-u5 && cargo build --bin cys
bash ~/axdev/.wt/aj-118-u5/tests/install-u5/u5-mac-lock.sh --cys target/debug/cys --cys-tree ~/axdev/.wt/cys-118-u5
pwsh -NoProfile -File ~/axdev/.wt/aj-118-u5/tests/install-u5/u5-win-lock.ps1            # 윈: -Cys <cys.exe> 를 주면 실물까지
python3 ~/axdev/.wt/aj-118-u5/tests/install-u5/sync-cys-contract.py --check ~/axdev/.wt/cys-118-u5   # bootstrap.ps1 을 고쳤으면 --write 후 cys 쪽 커밋
```

## §6 master 몫(비가역 · 워커 실행 0)
- ★3판(Opus 2R · codex8/agy2 잔여) **스테이징 배포 필수 관문**: 배포 직전 `python3 <aj>/tests/install-u5/sync-cys-contract.py --check <cys main 작업 트리>` = 전부 `same`(사본·핀이 배포할 aj 원본과 같다) (4판: 판정 = 블록·시험·본문 대역 해시만 — 원본의 블록 밖 수정은 `same`(aj_commit 다름 = 정보 줄) · 블록 안 변경 = DIFF → `--write` + cys 커밋 + CI 뒤 배포) — 아니면 배포 중단. CI 가 실제로 재는 것 = 사본↔핀(음성 대조 포함)뿐 — 공개 /install/next/ 블록↔핀 스텝은 GitHub 러너가 403 차단이라 **지금 대조 0**(경고 1줄 · 4판 정정) ⇒ 이 관문이 유일한 실효 대조다. help 장 = J-UPD-01·02·03 3장.
- 스테이징 `/install/next/` 배포(aj bootstrap.sh·.ps1 + help 3장 · 라이브 무접촉) → 윈 실기 `docs/WIN-FIELD-TEST-U5.md` relay(267) · 라이브 `/install/` 교체 · 핀 1.1.8 올림 · 보관소 본문 게시는 U3 의식.

## §7 적대 1R 채택/반박 표(codex 8 + agy 3 = 11행 · 원문 = docs/update/REVIEW-U5-{codex,agy}-1r.md)
- ⚠번호 정정: §0-2 표 머리의 agy 번호(⑦=agy2 · ⑧=agy3)는 원문 파일 순서와 엇갈린다 — 원문 순서 = agy1 open-a·TOCTOU · agy2 sync 미실행 · agy3 롤백 자산 hold(아래 표가 원문 순서).
| # | 지적(등급) | 판정 | 수리·근거 | 커밋(aj · cys) | 시험 |
|---|---|---|---|---|---|
| codex1 | 위임 거부 → 무잠금 재실행(BLOCK) | 채택 | rc 26·exit 6 = J-UPD-01 + 끝 · 재실행 삭제(설계 §3-2 140행) | 554ba4c·aa7d9e7 · 사본 | 맥 ⓕ · 윈 ⓕ |
| codex2 | nolock = 성공처럼 진행(BLOCK) | 채택 | nolock = busy 와 같게 4번 시도 뒤 끝 | 554ba4c·aa7d9e7 | 맥 ⓙ |
| codex3 | 묘비 실패 삼킴 · Delete→Move 창(BLOCK) | 채택 | 묘비 실패 = 쥔 채 · 폴백 삭제 · 바꿔치기 = FileRenameInfoEx→MoveFileEx · lock.rs 무수정(그 창(새 러너 잠금 → 기록 사이)은 acquire 순서상 남는다 — 닫는 것은 「묘비 없이 놓지 않기」 · 3판 정정 N4) | 1d7c8b0 · df427993 | 맥 ⓚ 2(음성 대조 적색) · 윈 ⓚ 2 + 구조 |
| codex4 | 토큰 env 프로세스 전체(MAJOR) | 채택 | ④ = agy1 앞 절반과 같은 수리 | 6bdde7b · 4e35a19e | 맥 ⓛ 2(음성 대조 적색) · 윈 ⓛ 3 |
| codex5 | 기존 폴더 DACL·reparse 미검사(MAJOR) | 채택 | 진입마다 폴더·txn.lock·txn.owner.json 검사 · 불일치 = J-UPD-01 즉시 | 3cc3e2f · 6418abee | 맥 ⓜ 3(음성 대조 적색 2) · 윈 ⓜ 3 + 벡터 20 |
| codex6 | 저널 있음 + 판정 cys 없음 = go(MAJOR) | 채택 | wait(J-UPD-02) · 재설치 = cys 가 degraded·corrupt 를 명시한 때만 | 554ba4c·aa7d9e7 | 맥 ⓓ 4 |
| codex7 | 본문 404 → N7 영구 hold(MAJOR) | 채택(분담) | 설치 링크 = 같은 판이어도 설치기 받기 + 재실행마다 --preserve-installer · hold 사유 화면·기록 1줄 · 러너 S8 보관소 받기 = master#c72a59df ⓐ U2 후속 2판(296) 발주 · 접점 `installers/<seq>/` 4파일 + verify_installer_dir 무변경 | 1232238·8fd43bc · 78221478 | 윈 순수 1 + 구조 1 |
| codex8 | sync --check CI 미실행 · 블록 하네스에 배선 검사 없음(MAJOR) | 부분 채택 | 앞 절반 = 핀 대조 + 음성 대조(CI) · 뒤 절반(전체 bootstrap 배선 검사를 윈 CI 에서) = 반박: 배선 구조 검사는 맥 시험 ⓗ·ⓛ 와 pwsh [구조] 10줄이 **원본 전체**로 이미 잰다(윈 CI 가 원본을 체크아웃하려면 aj 저장소 접근 = 비밀 토큰 신설 = 범위 밖) | 8fd43bc · 18a92a12 | CI 스텝 음성 대조 · 맥 ⓘ |
| agy1 | `open -a` 토큰 유출 · exec 직전 해제 TOCTOU(BLOCK) | 앞 = 채택 · 뒤 = 반박 | 앞: 셸에 토큰이 없다(④ · `env -u` 불요). 뒤: 해제~exec 는 같은 셸의 연속 두 줄(그 사이 cys 호출 0 · ms 창) · 러너 진입 = N2 사람 입력 20분 유휴 + 지터 0~45분이라 설치 직후 그 창에 S7 진입 불가 · exec 대상 = claude(러너 교체 대상 아님) | 6bdde7b | 맥 ⓗ·ⓛ |
| agy2 | sync --check 주석에만(MAJOR) | 채택 | codex8 앞 절반과 같은 수리 | 8fd43bc · 18a92a12 | CI 음성 대조 |
| agy3 | 롤백 자산 실패 → 조용한 hold(MAJOR) | 채택 | codex7 과 같은 수리 · 설치 중단은 반박(이미 깔린 판은 쓸 수 있다 — 깨는 쪽보다 재실행 안내) | 1232238·8fd43bc | 윈 순수 1 |

## §8 적대 2R 채택/반박 표(agy 2 + Opus 12 = 14행 · master#2f038a50 전건 채택)
| # | 지적(등급) | 판정 | 수리·근거 | 커밋 | 시험 |
|---|---|---|---|---|---|
| agy-B1 | nolock 영구 오류에 90초 대기(BLOCK) | 채택 | nolock = 재시도 0 · J-UPD-03 | aj ca9cec9 | 맥 ⓙ(재시도 0 단언) |
| agy-m1 | unsafe 에 「바꾸는 중」 문구(MINOR) | 채택 | J-UPD-03 원인별 문구 | ca9cec9 | 맥 ⓜ · 윈 ⓜ 2 |
| N1 | 기다림 오분류 4(MAJOR) | 채택 | §0-3 ① | ca9cec9 | 맥 ⓙ·ⓙ′·ⓓ·ⓕ · 윈 순수 nojudge |
| N2 | 같은 판 자산 재다운 실패 = 막힘(MAJOR) | 채택 | §0-3 ② | ca9cec9 | 윈 구조 1(실 다운로드 = 윈 실기 몫) |
| codex8/agy2 잔여 | CI = 사본↔핀뿐(MAJOR) | 채택 | §0-3 ③ — aj 원본 직접 대조는 CI 밖(저장소 접근 0) → 배포 관문으로 | cys (이 커밋) | CI 스텝 맥 실행 3갈래 |
| N3 | 위임 거부 단언 1(MINOR) | 채택 | §0-3 ④ | ca9cec9 | 윈 실본문 1 + 구조 1 · 맥 ⓕ 문구 |
| N4 | acquire 서술 · perl 단독 SIGKILL(MINOR) | 채택 | §0-3 ⑤ · 윈은 해당 없음(잠금 = 설치 도우미 프로세스 자신) | ca9cec9 | 맥 ⓝ(음성 대조 적색) |
| N5 | 묘비 실패 + 창 폴백(MINOR) | 채택 | §0-3 ⑥ | ca9cec9 | 맥 ⓗ 구조 · 윈 구조 |
| N6 | 직전 기록 복원 실패 삼킴(MINOR) | 채택 | §0-3 ⑤ | ca9cec9 | (주입 시험 없음 — 복원 실패 주입 = 폴더 쓰기 막힘이 잡기 전 단계에서 먼저 걸려 갈래를 못 가른다 · 정직) |
| N7 | 주석·문서 잔존 5(MINOR) | 채택 | §0-3 ⑦ | ca9cec9 · cys | — |
| N8 | 재시도 ≈130초 무화면(MINOR) | 채택 | §0-3 ⑥ | ca9cec9 | 맥 ⓒ(1줄 단언) |
| N9 | 맥 감지 표 미포장 · ping 서술(MINOR) | 채택 | §0-3 ⑦ | ca9cec9 | — |
| N10 | 자산 판정 = 존재만(MINOR) | 채택 | §0-3 ⑧ | cys 6baee372 · ca9cec9 | cys link_state 1 · 윈 순수 2 |
| N11 | 윈 journal-state 시한 0(MINOR) | 채택 | §0-3 ⑧ | ca9cec9 | 윈 순수(nojudge 경로) |

## §9 적대 3R 채택/반박 표(agy 0 + Opus 10 = 10행 · master#c60b7de4 전건 채택)
| # | 지적(등급) | 판정 | 수리 | 시험(음성 대조) |
|---|---|---|---|---|
| M1 | 자산 받기 시한 없음(MAJOR) | 채택 | §0-4 ① | pwsh [받기] 답 없는 서버 3초 상한 — 시한 제거 시 45초 알람까지 멈춤(적색 확인) |
| m1 | 실패 갈래 무화면·무집계(MINOR) | 채택 | §0-4 ② — 문구는 master 견본의 「다음에 자동으로 다시 받습니다」 대신 「이 설치 한 줄을 다시 실행하시면 다시 받아 봅니다」(러너 받기 = 296 미출고 · 지금 거짓이 될 약속 0) | [받기] 문구·기록 단언 |
| m2 | 종결 저널까지 J-UPD-03(MINOR) | 채택 | §0-4 ③ | 맥 ⓓ · 윈 순수 |
| m3 | 저널 판정에 재검증 묶임(MINOR) | 채택 | §0-4 ⑤ | cys link_state(--assets 없으면 칸 0) |
| m4 | 순간 실패까지 J-UPD-03(MINOR) | 채택 | §0-4 ④ | 맥 ⓙ 재확인 3 · 윈 [분류] |
| m5 | CI 403 인데 「잰다」(MINOR) | 채택 | §0-4 ⑥ | — |
| m6 | 핀 = 파일 커밋(MINOR) | 채택(배포 입구 배선 = 범위 밖 · master) | §0-4 ⑥ | 맥 ⓘ′(블록 밖 same · 블록 안 DIFF) |
| m7 | 낡은 주석·문서(MINOR) | 채택(설계 문서 = master) | §0-4 ⑦ | — |
| m8 | 일정 약속 문구(MINOR) | 채택 | §0-4 ⑦ | — |
| m9 | 시험이 경로를 안 지남(MINOR) | 채택 | §0-4 ②⑧ | [받기] · [분류] · [실경로] |
