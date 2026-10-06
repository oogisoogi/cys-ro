# U2 실기 문안 — 맥 VM M1~M3 · 윈 W1~W4 (TICKET=cysr-118-u2-runner · 문안만 · 집행 0)

> 설계 정본 = `~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md` §7-3 · §3-7-a(P1~P5) · §12(D1~D11).
> **집행 결정 = master**(VM M1~M3) · **윈 W1~W4 = 윈 master**(267 경유 · master 발송). 이 문서는 절차·판정 기준·원문 회신 목록만이다.
> 채택 게이트(📌12″) = **W1~W4 에서 P1~P5 전건 PASS** — 하나라도 FAIL·미실행 = §3-7-b 폴백(코드/리소스 슬롯 A/B) 전환.

## 0. 공통 준비(빌드 · 시험 키 · 시험 피드)

- 빌드: 이 가지(`u2/runner-118`)의 **디버그 빌드 2판** A·B — 판마다 `CYSR_RELEASE_SEQ` 를 다르게(A = n, B = n+1) · B 에만 보이는 표지 1개(`CYS_BUILD_ID`).
  디버그 빌드여야 `CYS_UPDATE_FEED_URL`(file://)·`CYS_UPDATE_FAULT`·`CYS_UPDATE_NO_JITTER`·`CYS_UPDATE_SETTLE_SECS`·`CYS_UPDATE_LAUNCHAGENTS_DIR` 가 듣는다
  (출시 빌드는 전부 무시 — `net::feed_base`·`runner::Fault::from_env`·`launch::agents_dir` 가 `cfg!(debug_assertions)` 로 막음).
- 시험 키 4개(R·U·F·A2)는 U1 시험 도구(`minisign` dev 의존)로 **시험 안에서** 만든다 — 실키 0 · 키 파일을 기기에 남기지 않는다.
  시험 키 공개키는 시험 빌드의 `trusted-keys.json`(purpose 칸) 에만 넣는다(출시 키링 무변경).
- 시험 피드 폴더(`<sandbox>/feed/`): `cysr/stable.json(.minisig)` · `revocations.json(.minisig)` · 본문 보관소 `releases/<seq>.json(.minisig)` ·
  자산(맥 zip / 윈 setup.exe + `.sig`) — U3 `scripts/update/make-release-json.py`·`make-envelope.py`·`make-revocations.py` 를 시험 키로.
- 격리 env(§7-2 · `env -i` 로 시작): `HOME`·`CYS_SOCKET`·`CYS_STATE_DIR`·`CYS_PACK_DIR`·`CYS_CONFIG_DIR`·`CYS_LOCAL_DIR`·`CYS_ACCOUNT_DIR`·
  `CYS_DEPTS_JSON`·`CYS_ROOT`·`CYS_ROUND_DIR`·`CYS_PACK_CAPTURES_DIR`·`CYS_FLEET_SCREENS_DIR`·`CYS_CYSD_BIN`·`CYS_CYS_BIN`·`CYS_NO_AUTOSTART=1` 명시 ·
  좌석 신원(`CYS_SEAT_TOKEN`·`CYS_OWNER_TOKEN`·`CYS_CHANNEL_TOKEN`·`CYS_SURFACE_*`·`CYS_ROLE`·`CYS_BOOT_NONCE`)·`AITERM_*`·`JAVIS_*`·`CLAUDE_CONFIG_DIR` 금지 +
  갱신 전용 `CYS_UPDATE_FEED_URL=file://<sandbox>/feed` · `CYS_UPDATE_APP_PATH=<sandbox>/Applications/cysr.app`(맥) · `CYS_UPDATE_STATE_DIR=<sandbox>/update` ·
  `CYS_UPDATE_NO_JITTER=1`(지터·부팅 15분 생략 — 실 운용 경로는 VM 1회에서만 기본값으로 따로 잰다) · `CYS_UPDATE_SETTLE_SECS=5`.
- 이 맥에서 이미 돈 것(실기 아님 · 근거): `scripts/tests/u2-smoke.sh` 10/10(부팅 가드 rc 75 · 손상 저널 → seats_blocked · `--auto --spawn` ·
  rotate 잠금 경합) · 강제 종료 행렬 78칸(가짜 실행층) · 실 APFS `RENAME_SWAP` 왕복 시험 1 · `scripts/tests/u2-mutants.sh` 10/10.

## 1. 맥 VM(Tart · `docs/DARWIN-UPDATER-LEGACY-LANE.md` 8단계 VM 절차 재사용)

| 단계 | 무엇 | 판정(통과 기준) | 회신 원문 |
|---|---|---|---|
| **M0** | A 판 설치(`/Applications/cysr.app` = VM 안 정식 자리) · 좌석 2~3개 기동 · 사용자 잡 1개(`bulk:false`·`publish:false`) · `~/.cys/local/x.md` 1줄 | `cys self-update --check --json` 의 `gates.first_hold` = 없음(또는 N2 대기) · `facts.recover_agent_ok=true`(첫 `--auto --spawn` 뒤) · `rollback_assets_ok=true` | `--check --json` 원문 · `ls ~/Library/LaunchAgents/com.cysjavis.cysr-update-recover.plist` · `plutil -p` 원문 |
| **M1** | 사람 입력 없이 20분(N2) → 6h 잡 대신 `cys self-update --auto --spawn` 1회 실행 | `cys build-info --json` = B · 좌석 집합(역할·세션) = 전 · `~/.cys/local/x.md` 바이트 동일 · `~/.cys/update/state.json` `last_result.kind=ok` · `~/.config/agora/counsel/updates.jsonl` 1줄 · 러너 사본은 cysd 정지(S7~S10) 동안 생존(위험 R1 · `ps` 로 러너 pid 가 S7 전후 같음) · 옛 번들 = `/Applications/.cysr.app.old-<A seq>` | journal.json·state.json·attempt.json 원문 · 좌석 목록 전/후 · doctor FAIL 전/후 · 러너 pid 기록 |
| **M1′** | 같은 VM · `CYS_UPDATE_NO_JITTER` 없이 1회(실 지터 경로) | 러너가 부팅 15분 + 지터(0~45분) 뒤 판정 · 단조 시계(VM 절전 1회 끼워도 잡 중복 0) | 시작·판정 시각 |
| **M2** | A 로 되돌린 뒤 `CYS_UPDATE_FAULT=verify_v3` 로 M1 반복 | `build-info` = A · 팩·좌석 집합·사용자 트리 해시 = 전 · `state.json` `last_result.kind=rollback` · `failures` 칸(transient · 6h) · 상담소 신호 대기열 1건 | 같은 원문 + `ls /Applications/.cysr.app.*` |
| **M3** | A 로 되돌린 뒤 `CYS_UPDATE_FAULT=pause@S9`(표지 `~/.cys/update/fault-pause-S9_SWAPPED.marker` 생김) → 표지 뒤 10초 안 **VM 강제 정지**(전원 차단 모사) → 재부팅 → 로그인 | 정식 자리 번들 1개(`/Applications/cysr.app` 존재 · A 또는 B 전수) · 복구기(LaunchAgent RunAtLoad)가 저널 종결 · cysd 는 복구 **뒤에만** 좌석 생성(부팅 직후 `cysd` 로그에 「갱신 복구 대기」 rc 75 가 있을 수 있음 = 정상) · 저널 종결 상태 | journal 원문 · `cysd.log` 머리 · build-info |
| **M3b** | (D9) 저널 두 슬롯을 손으로 손상(`echo '{' > journal.json; echo '{' > journal.prev.json`) → 재부팅 | 번들이 A·B 중 하나와 일치하면 재구성 → 종결 저널 + `update.journal_corrupt` 1통 · 아니면 좌석 0 + `state.json seats_blocked{reason:"journal_unrecoverable"}` | state.json · journal.corrupt.* 파일 목록 |
| **M-proxy** | (D4) 프록시 캡처 1회 — 실 피드 URL(사이트 `/update/`) redirect 홉 | `net` 규칙표 허용 홉만 | 캡처 요약 |

정직: M1 의 러너 생존(R1)은 `ChildLifetime::Survivor`(세션 분리)로 띄웠다는 코드 사실뿐이고 **실측 0** — 실패하면 launchd 일회 작업(설계 대안)으로 바꾼다.

## 2. 윈 실기 요청문(267 relay 로 그대로 · 설계 §7-3 원문 + U2 구현 반영 칸)

```
[실기 요청 · TICKET=win-118-autoupdate · 쓰기 있음(시험 설치 폴더 한정) · 롤백 · 전원 차단 포함]
목적: 1.1.8 데몬 자동 갱신이 윈 참가자 PC 에서 사람 손 0 으로 돌고, 실패·정전 때 스스로 되돌아오는지 잰다.
준비물: 우리가 보내는 zip 1개(1.1.8 시험 빌드 2판 = A·B 의 설치 파일과 .sig + 시험 피드·폐기문·본문 보관소 폴더 + 시험 키로 서명) · 설명서 1장(아래 3절).
W1(읽기 전용 · 10분): 지금 설치본에서
  1) cysr --version · cys doctor --json(요약 줄) · cys schedule list(id 만) · ~/.cys/pack/agents.json 의 각 cmd 줄
  2) %LOCALAPPDATA%\cys 폴더 크기(바이트) · 그 안 runtime 폴더 크기 · 디스크 여유 공간
  3) reg query "HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy" /v VerifiedAndReputablePolicyState 원문(스마트 앱 컨트롤 상태)
  4) 설치 링크가 받은 설치 파일(cysr_1.1.7_x64-setup.exe 또는 그 판)이 PC 어디에 남아 있는지(경로·없으면 없음)
  5) 사용자 권한(관리자 아님) PowerShell 에서 설명서 「시험 작업 만들기·읽기·지우기」 3줄 실행 → 원문
  → 원문 그대로 회신(백업 크기·권한 계수용).
W2(시험 폴더에서 · 자동 갱신 1회): 설명서 순서대로 A 판을 시험 폴더에 깔고(실 설치본 무접촉),
  CYS_UPDATE_FEED_URL=시험 피드 로 cys self-update --check --json 을 1회 실행 → 원문 회신.
  이어 사람 입력 없이 20분 둔다(게이트 N2 기본값) → cys self-update --auto --spawn --json 1회 → 자동 갱신이 일어났는지:
  cys build-info --json(B 여야 함) · %LOCALAPPDATA%\cys-update(시험) 의 journal.json·state.json 원문 · 좌석 목록 전/후 ·
  doctor FAIL 전/후 · 갱신 중 화면에 창(설치 창·확인 창)이 떴는지 여부(떴으면 사진 1장).
  ⑥(P1) 설명서의 「같은 설치기 다시 실행」 1줄을 실행 → cys self-update --verify-payload --json 원문(B 매니페스트 전수 일치여야 함 · rc 0).
  ⑦(P4) cys self-update --check --json 의 facts.recover_agent_ok 원문 → 설명서대로 복구 작업을 지움 → --check 다시(N14 보류여야 함) →
     cys self-update --auto --spawn --json(다시 등록) → --check 원문(recover_agent_ok=true).
W3(롤백 · 같은 시험 폴더): A 로 되돌린 뒤 CYS_UPDATE_FAULT=verify_v3 를 걸고 W2 반복 →
  cys build-info --json(A 로 돌아와야 함) · state.json 의 failures·last_result · 신호 대기열 파일 1건 원문 ·
  cys self-update --verify-payload --json(A 매니페스트 전수 일치 · B 전용 파일 0 = P2).
W4(전원 차단 3지점 · 같은 시험 폴더 · 각 지점마다 A 로 되돌린 뒤 시작):
  ① CYS_UPDATE_FAULT=pause@S9 — 설치 창이 도는 중(표지 파일 fault-pause-S9_SWAPPED.marker 가 생긴 뒤 10초 안)
  ② CYS_UPDATE_FAULT=pause@S9b — 「대조 중」 표지 fault-pause-S9b_PAYLOAD_OK.marker 가 생긴 뒤 10초 안
  ③ CYS_UPDATE_FAULT=verify_v3,pause@RB_SWAPPED — 롤백의 「옛 판 설치기 실행 중」 표지 fault-pause-RB_SWAPPED.marker 가 생긴 뒤 10초 안
  각 지점: 노트북 전원 버튼을 길게 눌러 끈다 → 다시 켜고 로그인 → 5분 기다림 →
  cys build-info --json · cys self-update --verify-payload --json · journal.json 원문 · stage·installers 파일 sha256 목록 · 좌석 목록 · doctor.
  (다른 작업 중이면 미뤄 주세요 — 강제 종료입니다.)
판정은 우리가 한다 — 원문만 보내 주세요(해석·요약 불요). 각 단계 시작·끝 시각을 적어 주세요(계수용).
중단 조건: 실 설치본(%LOCALAPPDATA%\cys) 의 파일 시각이 바뀌면 즉시 멈추고 그 사실만 회신.
```

P↔W 대응(판정 = master): P1 = W2 ⑥ + W4 · P2 = W3 · P3 = W4(stage·installers sha256 = 저널 기록) · P4 = W1 ⑤ + W2 ⑦ · P5 = W4 ①②③.

## 3. 윈 시험 설명서(시험 폴더 격리 · 「실 설치본 무접촉」을 윈 master 가 스스로 잴 수 있게)

1. **기준 시각 기록**: `Get-Date -Format o > $env:TEMP\u2-start.txt` · 실 설치본 표지: `Get-ChildItem $env:LOCALAPPDATA\cys -Recurse -File | Sort LastWriteTime -Desc | Select -First 5 FullName,LastWriteTime`(원문 보관).
2. **시험 폴더**: `$T = "$env:USERPROFILE\u2test"` · `$env:LOCALAPPDATA` 를 바꾸지 않는다 — 대신 아래 env 로 상태·갱신 폴더를 시험 폴더로 돌린다:
   `CYS_STATE_DIR=$T\cys` · `CYS_UPDATE_STATE_DIR=$T\cys-update` · `CYS_SOCKET=\\.\pipe\cys-u2test` · `CYS_PACK_DIR=$T\home\.cys\pack` · `CYS_ROOT=$T\home\.cys` ·
   `CYS_NO_AUTOSTART=1` · `CYS_UPDATE_FEED_URL=file:///<zip 푼 곳>/feed` · `CYS_UPDATE_NO_JITTER=1` · `CYS_UPDATE_SETTLE_SECS=5`.
   ★설치 폴더 = 상태 폴더 규칙 재현(§7-3 ⚠): A 설치는 `setup-A.exe /S /P /D=$T\cys`(`/D` 마지막·따옴표 없음).
   + `CYS_UPDATE_INSTALL_DIR=$T\cys`(디버그 빌드 전용 · 러너의 설치 폴더·상태 폴더를 시험 폴더로 — 기본은 `%LOCALAPPDATA%\cys` = 설계 L4).
3. **시험 작업 만들기·읽기·지우기(W1 ⑤ · 사용자 권한 PowerShell · COM — 러너와 같은 경로)**:
   `cys self-update --auto --spawn --json`(시험 env 아래) → 결과 `recover_agent` 칸 · 작업 스케줄러 폴더 `\cysr\<install_id>\recover` 존재 확인:
   `(New-Object -ComObject Schedule.Service).Connect(); $s=...; $s.GetFolder("\cysr").GetFolders(0) | % Path` →
   지우기 = `$s.GetFolder("\cysr\<install_id>").DeleteTask("recover",0)`.
4. **같은 설치기 다시 실행(W2 ⑥)**: `setup-B.exe /S /P /UPDATE /D=$T\cys` — ⚠잠금이 없을 때만(러너 종료 뒤) · 잠금이 잡혀 있으면 우리 설치기는 exit 6(⓪-a)이 정상.
5. **끝**: 기준 시각 뒤 실 설치본 파일 시각 대조(1번과 같은 명령) — 바뀐 파일 0 이어야 한다.
