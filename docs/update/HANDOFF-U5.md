# HANDOFF-U5 — 설치 링크 잠금 참가·위임 + 윈 롤백 자산 보존 (TICKET=cysr-118-u5-install-link)

- 브리프 = `~/axdev/master/briefs/2026-10-07-cysr-118-u5-install-link.md`(master#fb5f4165) · 착수 2026-10-07 07:25 · 좌석 u5@surface:1297
- 트리 2: cys `~/axdev/.wt/cys-118-u5`(가지 u5/install-link-118 off 8bcd39aa) · ai-jarvis `~/axdev/.wt/aj-118-u5`(같은 가지명 · push 0)
- 설계 정본 = `DESIGN-AUTOUPDATE-118.md` §3-2(136~142행) · §3-7 ②(245행) · 계약 정본 = 코드(`src/update/lock.rs`)

## §0-2 2판 델타(master#9502b67b · 적대 codex 1R BLOCK 3·MAJOR 5 + agy 1R BLOCK 1·MAJOR 2 · 전건 채택 · 상한 2.5h · 원문 = docs/update/REVIEW-U5-{codex,agy}-1r.md untracked)
- ★1판 설계 결정 2(위임 거부 → 무잠금 재실행)·nolock 폴백·결정 3 의 「판정할 cys 없음 = go」 는 **폐기**(설계 §3-2 140행이 이긴다). 아래 수리 설계가 2판 정본.
| # | 지적 | 2판 수리(파일·자리) | 상태 |
|---|---|---|---|
| ① codex1 BLOCK | 위임 거부 시 무잠금 재실행 | sh `txn_invoke_logged`·`cys_rotate_state` rc26 갈래 · ps1 `Invoke-CysTxnLogged`·`Get-CysRotateState` rc26 · `Step-InstallCys` exit 6 갈래 → 전부 「J-UPD-01 + 문구 + 설치 즉시 끝(rc 26)」 · 재실행 삭제 | ✅ 맥 aj 554ba4c · 윈 aj(이 커밋 다음) · 사본 재동기 |
| ② codex2 BLOCK | nolock = 성공처럼 진행 | sh `txn_hold_try` nolock → busy 와 같은 재시도(4번) 뒤 끝 · ps1 `Lock-CysTxnOnce`·`Enter-CysTxn` 같음 · 시험 = 폴더 쓰기 불가 주입 → rc 26 | ✅ 맥 aj 554ba4c · 윈 aj(이 커밋 다음) · 사본 재동기 |
| ③ codex3 BLOCK | 묘비 실패 삼킴 · Delete→Move 창 | ps1 `Write-CysTxnFile` 폴백 삭제(임시 → Replace 재시도만 · 실패 = throw) · `Unlock-CysTxn` 묘비 실패 = **잠금을 쥔 채** 재시도(100ms×30) 뒤 그래도 실패면 쥔 채 종료(프로세스 끝 = OS 해제 · 묘비 없는 낡은 기록은 ② 로 걸러짐 — 단 codex 시나리오는 「잠금 풀림 + 묘비 없음」 창이라 프로세스 종료 전까지 쥐는 것이 핵심) · sh perl `wr` 실패 = 해제 0 · 쥔 채 종료 · lock.rs:326-350 무수정(관찰: 검증이 「잠금 held + 기록 두 번 동일」 이라 묘비 없는 옛 기록 + 새 러너 잠금 창을 구조로 못 가른다 — 새 소유자가 기록을 먼저 쓰는 acquire 순서가 그 창을 닫는다) | 미착수 |
| ④ agy1 BLOCK · codex4 | 토큰 env 프로세스 전체 | sh: `export CYS_UPDATE_TXN` 삭제 → `txn_invoke_logged`·rotate 호출 줄에만 `CYS_UPDATE_TXN="$TXN_TOKEN"` 앞붙이기 · 데몬 자동 기동이 필요한 일반 cys 호출(ping·list 등)은 잠금 쥔 동안 자동 기동 거부(cys.rs:4665) → 그 호출들에도 토큰 env 를 줄 것인가 = 자동 기동 가드는 env **존재만** 본다 → 일반 cys 호출 래퍼 1개(`cys_txn_env`)로 그 호출에만 env · `open -a` = `env -u CYS_UPDATE_TXN` · `exec claude` = 해제 → 즉시 exec(그 사이 cys 호출 0 · TOCTOU 사유: 러너는 N2 사람 입력 20분 유휴·지터 0~45분이라 해제~exec 수 ms 창에 S7 진입 불가 + exec 대상은 claude(러너 교체 대상 아님)) · ps1: `$env:` 전역 대신 `Invoke-WithCysTxnEnv { … }`(참가 명령·setup.exe·daemon 자동 기동 호출만) · Claude 설치기/로그인 = 토큰 0 | 미착수 |
| ⑤ codex5 MAJOR | 기존 폴더 DACL·reparse 미검사 | ps1 `New-CysTxnDir` → 진입마다 `Get-Acl` SDDL read-back(소유자 = 나 · 허용 ACE = OW·SY·나·BA 상속 꼴만 = cys sd_is_private 규칙) + `(Get-Item).Attributes -band ReparsePoint` = 0 · txn.lock·txn.owner.json 파일도 같은 검사 · 불일치 = J-UPD-01 끝 · sh = `stat` uid=나·mode&077=0·심링크 아님(perl 안 lstat) | 미착수 |
| ⑥ codex6 MAJOR | 저널 있음 + 판정 cys 없음 = go | sh `txn_journal_verdict`·ps1 `Get-CysTxnJournalVerdict` 끝 줄 go → **wait** · 재설치 허용 = cys 가 degraded·corrupt 를 명시한 때만 | ✅ 맥 aj 554ba4c · 윈 aj(이 커밋 다음) · 사본 재동기 |
| ⑦ codex7·agy2 MAJOR | 본문 404 → N7 영구 hold | 실측(10-07 09:4x): 러너는 보관소에서 받지 않는다 — `grep 'releases/\|archive' src/update/{realops,check,auto}.rs` = 0(N7 = 검증만 `check.rs:547-570`) ⇒ bootstrap: 설치판 자산이 없으면(`cys self-update --preserve-installer` 가 아니라 먼저 판정 — `installers\<seq>` 4파일 없음) 같은 판이어도 [5/10] 이 핀 설치기를 다시 받고 [6/10] 건너뜀 갈래에서 `Save-CysRollbackAssets` 재시도(설치 재실행 때마다) + 296(u2-followup n17)에 【질문】 1줄(러너 S8 보관소 받기 미구현) | 미착수 |
| ⑧ codex8·agy3 MAJOR | sync --check CI 미실행 | windows-health 계약 스텝 run 머리: 사본 sha256 핀 대조(`scripts/tests/install-link-u5/CONTRACT.sha256` = aj 원본 커밋 SHA + 원본 블록·시험 sha256 · sync 도구가 --write 때 생성) → 사본 해시 ≠ 핀 = 적색 · 음성 대조 1 = 사본 1바이트 변조 → 그 검사 적색(스텝 안 자기시험) | 미착수 |
- ★순환 지점(10-07 · CTX 59% jsonl 라이브): ①②⑥ 끝(맥 u5-mac-lock 23/0 · pwsh 22/0 · 하네스 12/0) · **다음 = ③ → ④ → ⑤ → ⑦ → ⑧ 순서** · 각 항목 = 위 표의 「2판 수리」 칸이 설계 정본 · ⑦ 은 296 에 보낼 【질문】 1줄을 master 경유(허브-스포크)로 · 미러 push 는 ⑧ 까지 끝낸 뒤 1회 · 채택/반박 표 11행은 §7(신설)에 · 시험 재현 = §5.
- 완료 = 맥 전수 0 실패(update::·cys·u5-mac-lock·pwsh) + 미러 3런 success(⑧ 실제 실행) + 채택/반박 표 11행 → 【확인요청】.

## §0 델타(다음 사람이 먼저 읽을 것)
- 브리프 §2 1~7 구현·커밋 끝. 남은 것 = 미러 CI 판정(아래 §4 CI 칸) · master 게이트 · 적대 리뷰(master 발주) · 스테이징 배포·윈 실기(master).
- ★설계 결정 1(브리프 §2-1 「네 설계」): **잠금을 쥐는 것 = 설치 도우미 스크립트 자신(ⓐ)** — 맥 = 배경 perl 의 flock(소유자 pid = 설치기 셸 `$$`) · 윈 = 설치기 PowerShell 프로세스의 `FileStream.Lock(0,1)`(소유자 pid = `$PID`).
  근거 1줄: 설치 **전**엔 믿을 cys 가 없고(윈은 NSIS 안 cys.exe 를 꺼낼 수 없다) · 위임 검증 ③ 이 「소유자 pid = 자식의 조상」을 요구해 따로 뜬 도우미 프로세스는 소유자가 될 수 없다.
  대가: 소유자 기록·시작 시각을 스크립트가 cys 와 같은 식으로 만든다(③′ 짝) → 맥은 실 cys 위임 수용 + 뮤테이션으로 실증 · 윈은 windows-health 계약 스텝이 실물로 잰다.
- ★설계 결정 2: 위임이 거부되면(cys rc 26 · 설치기 exit 6 — 시작 시각을 못 맞춘 기계 등) **잠금을 놓고 토큰 없이 한 번 더**(설치는 끝까지 · 그 명령은 평소 참가자). 설치를 깨뜨리는 쪽보다 보호를 한 단계 낮추는 쪽을 골랐다.
- ★설계 결정 3: 저널 판정은 스크립트가 하지 않고 cys 새 입구 `self-update --journal-state`(러너 사본 → 설치본 순) — 온전·비종결 = 「복구 대기」(J-UPD-02) · 손상(degraded·corrupt) = 📌18 재설치 길이라 진행 · 판정할 cys 없음 = 진행(기록 1줄).
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
- 위임 = env `CYS_UPDATE_TXN`(설치 도우미 프로세스 전체) + 참가 명령에만 `--txn`/`/CYSTXN=` · 오래 사는 자식(앱 창·자비스)엔 토큰 env 0.
- 기다림 rc = 26(설치 도우미 끝 코드) · 진단 코드 J-UPD-01(잡혀 있음 · 30초 × 3 재시도 뒤) · J-UPD-02(복구 대기).

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
  · ⚠debug cys.exe 의 윈 주 스레드 스택 넘침(거부 갈래 = 0xC00000FD)은 시험 빌드 한정 관측 — 출시 무관이나 윈에서 debug cys 로 참가 거부를 재는 시험은 같은 함정(기록만).

## §5 재현
```
cd ~/axdev/.wt/cys-118-u5 && cargo build --bin cys
bash ~/axdev/.wt/aj-118-u5/tests/install-u5/u5-mac-lock.sh --cys target/debug/cys --cys-tree ~/axdev/.wt/cys-118-u5
pwsh -NoProfile -File ~/axdev/.wt/aj-118-u5/tests/install-u5/u5-win-lock.ps1            # 윈: -Cys <cys.exe> 를 주면 실물까지
python3 ~/axdev/.wt/aj-118-u5/tests/install-u5/sync-cys-contract.py --check ~/axdev/.wt/cys-118-u5   # bootstrap.ps1 을 고쳤으면 --write 후 cys 쪽 커밋
```

## §6 master 몫(비가역 · 워커 실행 0)
- 스테이징 `/install/next/` 배포(aj bootstrap.sh·.ps1 + help 2장 · 라이브 무접촉) → 윈 실기 `docs/WIN-FIELD-TEST-U5.md` relay(267) · 라이브 `/install/` 교체 · 핀 1.1.8 올림 · 보관소 본문 게시는 U3 의식.
