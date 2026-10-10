# WIN-GATE-1110 — 1.1.10 윈 실기 관문 W-1~W-6 (윈 master 실행표 · 10-16 실기 재료)

> TICKET=cysr-1110-upstream · 대상 빌드 = 병합 f711373a 를 품은 1.1.10 후보 설치본 · 통과 전 라이브 금지(master#60dc9ccf).
> **기대값의 출처는 전부 코드 판독이다 — 이 표의 명령을 윈도우에서 돌려 본 적은 없다**(작성 = 맥 워커). 기대와 다르면 「표가 틀렸다」도 후보다 → 출력 원문을 그대로 붙여 올린다.
> 셸 = PowerShell(관리자 아님). `cysr.exe` = `cys.exe` 와 같은 바이너리(설치기 별칭). 경로의 `$env:USERPROFILE\.cys\claude` = 기본 좌석 설정 폴더(팩 agents.json 의 `${CYS_ACCOUNT_DIR:-$HOME/.cys/claude}`) — 계정 선택으로 좌석에 `~/.claude-N` 을 준 기계는 그 폴더로 바꿔 읽는다.
> ⛔개인 기본 프로필 `$env:USERPROFILE\.claude` 는 어떤 단계에서도 바뀌면 안 된다(매 관문 끝에 해시 대조).

## 0. 시작 전 (한 번)

```powershell
cysr --version                                   # 기대: 1.1.10 후보 판 문자열
$seat = "$env:USERPROFILE\.cys\claude"           # 좌석 설정 폴더(다르면 여기만 고친다)
$S = "$seat\settings.json"; $L = "$env:USERPROFILE\.cys\claude-tui-written.json"
$P = "$env:USERPROFILE\.claude\settings.json"    # 개인 프로필 — 불변 대조용
$h0 = if (Test-Path $P) { (Get-FileHash $P -Algorithm SHA256).Hash } else { 'absent' }; $h0
if (Test-Path $S) { Copy-Item $S "$S.w1110-before" -Force; Get-Content $S -Raw | Select-String '"tui"' }   # 기대(W-1 전제): 출력 없음 = tui 키 없음
Test-Path $L                                     # 기대: False(이전 판에서 쓴 적 없음) — True 면 내용을 먼저 적어 둔다
Get-ChildItem Env:CYS_WIN_TUI_CLASSIC_OFF, Env:CYS_AGY_STATUSLINE -ErrorAction SilentlyContinue   # 기대: 없음
Test-Path "$env:USERPROFILE\.cys\win-tui-classic-off"   # 기대: False
```

- 전제가 안 맞으면(tui 키가 이미 있음) W-1 은 「이미 설정됨 = 무동작」 갈래가 된다 → 그 사실을 적고 W-1b(값이 fullscreen 일 때의 안내)만 본다.

## W-1. classic 고정 — 새로 띄운 claude 좌석에 기록되고 휠이 된다

| # | 실행 | 기대(통과) | 출처 |
|---|---|---|---|
| 1 | 앱에서 worker 좌석 1기 새로 띄움(또는 `cysr launch-agent --role worker --agent claude`) | 좌석이 정상 기동 | — |
| 2 | `Get-Content $S -Raw \| Select-String '"tui"'` | `"tui": "default"` 한 줄 | `src/claude_tui.rs` TUI_KEY·TUI_CLASSIC |
| 3 | `Get-Content $L -Raw` | JSON `{"version":…,"entries":[{"dir":…,"settings":…,"written_at":…,"created":false}]}` — `dir` = `$seat` | 같은 파일 LedgerEntry |
| 4 | `Test-Path "$S.bak-cys-tui"` | True(있던 파일을 고쳤을 때) · `created:true` 면 False | BACKUP_SUFFIX |
| 5 | `Compare-Object (Get-Content "$S.w1110-before") (Get-Content $S)` | 차이 = tui 한 줄(+앞 줄 끝 쉼표)뿐 — 다른 키·순서·들여쓰기 불변 | 「텍스트 외과 수술」 계약 |
| 6 | 그 좌석 pane 에서 긴 출력 뒤 **휠 위로** | 대화가 위로 올라간다(터미널 스크롤백) · 프롬프트에 방향키 흔적 0 | 0.14.45 §1 |
| 7 | `cysr status --json` 에서 그 좌석 `alt_screen` | `false` | classic = 대체 화면 아님 |
| 8 | `(Get-FileHash $P -Algorithm SHA256).Hash -eq $h0`(없었으면 `Test-Path $P` = False) | True | PersonalProfile 불가침 |

- W-1b(값이 이미 `fullscreen`): 기동 로그(좌석을 띄운 창의 stderr · `[launch-agent] 렌더러 설정: …`)에 폴더당 1회 「… "tui": "fullscreen" 이 이미 적혀 있어 cys 는 덮지 않습니다 …」 · `cysr doctor` 의 `claude-tui-fullscreen` 항목이 그 폴더를 보인다 · 파일 무변경.
  - ⚠그 문안 뒤쪽 「전체화면이라 마우스 휠 스크롤이 꺼집니다」 는 **원작자 문면 그대로**라 cysr(휠 번역 유지)에서는 사실과 다를 수 있다 — W-2 결과와 함께 적어 올린다(문안 정정은 병합 검토 뒤 별건).

## W-2. `/tui fullscreen` 좌석 — 우리 번역(altscroll)이 산다

| # | 실행 | 기대(통과) |
|---|---|---|
| 1 | W-1 좌석 pane 에서 `/tui fullscreen`(Claude Code 가 스스로 재시작) | 전체화면으로 뜬다 · `cysr status --json` 그 좌석 `alt_screen` = `true` |
| 2 | `Get-Content $S -Raw \| Select-String '"tui"'` | `"tui": "fullscreen"`(사용자 값 — cysr 이 덮지 않는다) |
| 3 | 긴 대화에서 **휠 위/아래** | 대화가 반 화면씩 올라가고 내려온다(PgUp/PgDn 번역) · 프롬프트 히스토리 오염 0 · 「휠 스크롤 꺼짐」 토스트 **안 뜸** |
| 4 | 그 좌석을 닫고 같은 폴더로 다시 띄움 | `tui` 값 = 여전히 `fullscreen`(되덮기 0) · 기동 로그 W-1b 안내 1회 |

## W-3. ★모달이 떠 있을 때 휠 — 선택 항목이 움직이면 적

1. W-2 의 fullscreen 좌석에서 권한 확인 창이 뜨는 요청을 한다(예: 「현재 폴더에 w1110.txt 를 만들어 줘」 → 쓰기 권한 선택 창). **Enter 를 누르지 않는다.**
2. 선택 창이 떠 있고 강조(❯)가 1번에 있는 상태에서 휠을 **아래로 3칸**, **위로 3칸** 굴린다.
3. 관측을 적는다: ⓐ 강조가 움직였는가(몇 번째로) ⓑ 뒤쪽 대화가 스크롤됐는가 ⓒ 아무 변화 없음.
4. **Esc** 로 창을 닫는다(승인하지 않는다) · `Test-Path .\w1110.txt` = False 확인.

| 관측 | 판정 |
|---|---|
| ⓒ 무변화 또는 ⓑ 대화만 스크롤 · 강조 고정 | **통과** |
| ⓐ 강조가 움직임 | **적 — 라이브 금지 유지**(원작자 58d5c8e2 정적 판독이 실측으로 확인된 것 · master 판단: 모달 중 번역 끔 / fullscreen 번역 기본 끔) |

- 같은 시험을 선택 창 내용이 화면보다 **길 때**(긴 diff 승인)도 1회 — 원작자 판독은 「내용이 화면에 들어갈 때만 페이지 키를 선택 창에 양보」 라서 두 경우가 갈릴 수 있다.

## W-4. 킬스위치·되돌림

| # | 실행 | 기대(통과) |
|---|---|---|
| 1 | (W-2 뒤라 값이 fullscreen 이면) 그 pane 에서 `/tui default` 로 되돌리지 **말고**, 새 좌석 설정 폴더로 W-1 을 한 번 더 해 `"default"` 가 원장에 있는 상태를 만든다 — 또는 W-2 전에 이 관문을 먼저 돈다 | 원장 entries ≥ 1 · 그 폴더 `tui` = `default` |
| 2 | `New-Item "$env:USERPROFILE\.cys\win-tui-classic-off" -ItemType File` 뒤 claude 좌석 1기 기동 | 기동 로그 「… 에 cys 가 넣었던 "tui": "default" 를 제거했습니다」 · `Select-String '"tui"' $S` 출력 없음 · 원장에서 그 항목 빠짐 |
| 3 | (값을 사용자가 `fullscreen` 으로 바꾼 폴더가 원장에 있을 때) 같은 기동 | 그 값은 **그대로** · 원장에서만 빠짐 |
| 4 | 킬스위치 켠 채 새 좌석 기동 | 어떤 폴더에도 새 `tui` 기록 0 |
| 5 | `Remove-Item "$env:USERPROFILE\.cys\win-tui-classic-off"` | 다음 기동부터 W-1 동작 복귀 |
| 6 | (별도 · 파괴적 — 시험 기계에서만) `cysr factory-reset --plan` | 계획 출력에 원장 폴더의 `tui` 되돌림 항목 · 쓰기 0(`--plan`) |

## W-5. agy 상태줄 윈 자동 연결 (agy 가 깔린 기계만 · 없으면 「해당 없음」)

```powershell
$A = "$env:USERPROFILE\.gemini\antigravity-cli\settings.json"
if (Test-Path $A) { Copy-Item $A "$A.w1110-before" -Force; Get-Content $A -Raw }
cysr doctor                                      # agy-statusline 항목을 읽는다
Get-ChildItem "$env:USERPROFILE\.cys\pack\state\agy-statusline-*" -ErrorAction SilentlyContinue
```

| 경우 | 기대(통과) |
|---|---|
| `statusLine` 이 비었거나 없음 + 쓰기 전 실연 검사 통과 | `$A` 에 `"command": "…\.cys\pack\hooks\cys-agy-statusline.cmd --cys-autolink"`(따옴표 없는 경로 · 비ASCII 사용자 폴더면 `%USERPROFILE%\…` 꼴) · `state\agy-statusline-linked` 존재 · 백업 `settings.json.bak-cys` |
| 실연 검사 실패 | `$A` **바이트 동일**(`Compare-Object` 차이 0) · `state\agy-statusline-probe-failed` 존재 · doctor 항목에 사유·버전·나이 · 설치·기동은 계속 |
| 사용자가 직접 넣은 `statusLine` 이 있음 | 무변경 |
| 끄기: `New-Item "$env:USERPROFILE\.cys\agy-statusline-off"` 뒤 `cysr doctor --fix` | cysr 이 넣은(`--cys-autolink` 표지) 연결만 빠짐 |

## W-6. phoenix 자동 복원 — 기본 코드페이지에서 끝까지 돈다

```powershell
[Console]::OutputEncoding.CodePage; chcp          # 기대(한국어 윈): 949 — 적어 둔다
Get-ChildItem Env:PYTHONUTF8, Env:PYTHONIOENCODING -ErrorAction SilentlyContinue   # 기대: 없음(있으면 지우고 진행 — 데몬은 이 변수 없이 phoenix 를 띄운다)
$log = "$env:LOCALAPPDATA\cys\phoenix-restore.log"
```

| # | 실행 | 기대(통과) |
|---|---|---|
| 1 | 좌석 2기 이상(제목·작업 폴더에 **한글** 포함) 띄운 뒤 앱 완전 종료 → 재실행(자동 복원) | 좌석이 복원된다 |
| 2 | `Get-Content $log -Tail 40` | `UnicodeEncodeError`·`UnicodeDecodeError`·`Traceback` **0줄** · 복원 완료 줄 있음 |
| 3 | 최신 세대 스냅샷 폴더의 `manual_restore.sh` 줄바꿈: `(Get-Content <경로>\manual_restore.sh -Raw) -match "\`r\`n"` | False(LF 고정) |
| 4 | `cysr schedule list` | 은퇴한 옛 시드 잡(`fleet-adoption-cost-digest` · `content-channel-health-watch`)이 있으면 줄 끝 `note=retired-seed-text` · 결과 `skipped`(주기 오류 아님) — 승인 흔적이 있는 설치는 종전 오류가 남는 것이 정상 |

## 결과 보고 서식

`W-n: 통과|적|해당 없음 · 관측 1줄 · 붙임 = 명령 출력 원문` — 적이면 그 자리에서 멈추고 설정 파일 before/after 를 함께 올린다. 끝나면 `$h0` 대조(개인 프로필 불변) 1줄.
