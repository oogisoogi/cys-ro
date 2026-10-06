# NSIS ⓪-a 윈 실기 검증 — 8 시나리오 (1.1.8 U3 2판 · codex 1R #14 · 3판 +2 = 2R #14)

> 대상 = `src-tauri/nsis-hooks.nsh` PREINSTALL ⓪-a(자동 갱신 잠금 토큰 · 위임 조건 ⑴~⑷) + ⓪(설치기 뮤텍스).
> 왜 실기인가: 이 기계의 근거는 **컴파일**(`scripts/tests/nsis-hook-compile/run.sh`)·**소스 핀**(`test_nsis_lock_token_conditions`)·
> **상태 모델**(3판부터 ⓪-a 결정 나무 270 상태 · Z1~Z6 · `nsis-hook-model/model.py`)뿐이다 — exit 6·낡은 토큰·뮤텍스 수용 **동작**의 증거가 아니다.
> 실행 = 윈 master(실기 W2 와 같은 창 · 1.1.8 빌드 뒤) · 이 문서는 판정 가능한 관측 줄만 정한다. 결과는 아래 표 「결과」 칸에 적는다.

## 0. 준비 (PowerShell · 현재 사용자 · 관리자 아님)
```powershell
$setup = "<1.1.8 cysr_*_x64-setup.exe 경로>"            # 이번 판 설치기
$dir   = "$env:LOCALAPPDATA\cys"                           # 지금 설치 폴더(Get-CysInstallTarget 과 같은 해소)
$ud    = "$env:LOCALAPPDATA\cys-update"; New-Item -ItemType Directory -Force $ud | Out-Null
function Snap { Get-ChildItem -Recurse -File $dir | Get-FileHash -Algorithm SHA256 | ForEach-Object { "$($_.Hash) $($_.Path)" } | Sort-Object }
function Run($tok, $envTok) {                                # 무인 경로 = 러너와 같은 인자(설계 §3-7 ⑤)
  if ($null -ne $envTok) { $env:CYS_UPDATE_TXN = $envTok } else { Remove-Item Env:CYS_UPDATE_TXN -ErrorAction SilentlyContinue }
  $a = @('/S','/P','/UPDATE'); if ($tok) { $a += "/CYSTXN=$tok" }; $a += "/D=$dir"
  (Start-Process -FilePath $setup -ArgumentList $a -Wait -PassThru).ExitCode }
function Hold($id, $epoch) {                                  # 러너 흉내: 잠금(바이트 0..1 배타) + 소유자 기록(serde 들여쓰기 JSON)
  $script:lk = [System.IO.File]::Open("$ud\txn.lock", 'OpenOrCreate', 'ReadWrite', 'ReadWrite'); $script:lk.Lock(0, 1)
  Set-Content -Encoding utf8NoBOM "$ud\txn.owner.json" "{`n  `"txn_id`": `"$id`",`n  `"epoch`": $epoch,`n  `"pid`": $PID`n}" }
function Release { if ($script:lk) { $script:lk.Unlock(0, 1); $script:lk.Close(); $script:lk = $null } }
$id = -join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) }); $tok = "${id}:7"
```
- 모든 시나리오 앞뒤로 `Release` · 뮤텍스 쥔 창은 닫는다. 「무접촉」 판정 = `Compare-Object (Snap) $before` 출력 0줄 + `$dir` 안 `*.new`·`*.prev` 0개.

## 1. 시나리오 × 판정 줄
| # | 시나리오 | 차리기 | 기대(판정 줄) | 결과 |
|---|---|---|---|---|
| F1 | 잠금 없음 · 토큰 없음(종전 경로) | `Release` · `$before = Snap` · `Run $null $null` | exit **0** · 설치판 = 새 판(`& "$dir\cys.exe" build-info --json` 의 version) | |
| F2 | 정상 위임(러너 보유 + 뮤텍스 보유) | `Hold $id 7` · 다른 창에서 `$m = New-Object Threading.Mutex($false,'Global\cys-installer')` 유지 · `Run $tok $tok` | exit **0**(⓪ 뮤텍스 「이미 있음」을 위임으로 수용 = exit 5 아님) · 설치판 = 새 판 | |
| F3a | 변조 토큰(인자 ≠ 소유자 기록) | `Hold $id 7` · `$before = Snap` · `Run "${id}:8" "${id}:8"` | exit **6** · 무접촉(Snap 차이 0) | |
| F3b | 인자 = 소유자 기록 · env 없음/다름 | `Hold $id 7` · `$before = Snap` · `Run $tok $null` 그리고 `Run $tok ("0"*32+":7")` | 둘 다 exit **6** · 무접촉 | |
| F4 | 잠금 해제 뒤 늦은 자식(낡은 위임) | `Hold $id 7` → `Release`(소유자 기록은 남김) · `$before = Snap` · `Run $tok $tok` | exit **6**(⑴ 「/CYSTXN 있는데 잠금 없음」) · 무접촉 | |
| F5 | 타 설치기 뮤텍스(위임 아님) | `Release` · 다른 창에서 `Global\cys-installer` 뮤텍스 유지 · `$before = Snap` · `Run $null $null` | exit **5** · 무접촉(⓪-a 를 지나 ⓪ 에서 끝) | |
| F6 | 사람 실행 중 자동 갱신(잠금 보유 · 토큰 없음) | `Hold $id 7` · `$before = Snap` · `Run $null $null` · 그리고 `/S` 없이 대화형 1회 | 무인 = exit **6** · 무접촉 · 대화형 = 안내 창 1회(「Jarvis is switching to the new version right now…」) 뒤 exit 6 | |
| F7 | 대조 중 잠금 해제(TOCTOU · 3판 ⑵′) | `Hold $id 7` · `$before = Snap` · 설치기를 `Run $tok $tok` 로 띄우면서 **같은 창에서 바로** `Start-Sleep -Milliseconds <N>; Release` — N = 0·20·50·100·200 각 5회(경합 창을 쓸어 본다) | 25회 전부 exit **0**(재확인 때 아직 잡힘) 또는 **6**(재확인 때 풀림) · exit 6 이면 무접촉 · 「잠금이 풀린 뒤 설치가 진행됨」 = 0회(판정 = exit 0 회차마다 `Release` 시각 < 설치기 종료 시각이면 그 회차는 재확인을 통과한 것 — 로그 시각 대조) | |
| F8 | 위임 + 타 프로세스가 뮤텍스 보유(러너 아님) | `Hold $id 7` · **다른** PowerShell 창이 `Global\cys-installer` 뮤텍스 유지 · `Run $tok $tok` | 현 설계 = exit **0**(위임은 뮤텍스 보유자를 묻지 않는다 — 러너가 S7~S9b 동안 쥐는 것이 정상이라 「누가」 를 가릴 수 없다) · **기록할 것** = 두 설치기 동시 진행 여부 · 결과 = 설계 판단 재료(위험 = 낡은 1.1.7 설치기와의 동시 진행) | |

- 공통 「무접촉」의 정직한 범위: 템플릿이 훅보다 먼저 `SetOutPath $INSTDIR` 를 돌리므로 **폴더 생성**은 막지 못한다(⓪ 머리말의 같은 한계) — `$dir` 가 이미 있는 이 시나리오들에서는 차이 0 이어야 한다.
- 판정 불가(잠금 파일을 못 엶 · 예: 다른 사용자 권한) = 「잡혀 있음」으로 읽는다(fail-closed) — 관측되면 결과 칸에 「F? 판정 불가 갈래」로 적는다.

## 2. 관측 결과를 어디에
- 표 「결과」 칸 = `exit <n> · Snap 차이 <줄 수> · <비고>` 한 줄 · 실패 1건이라도 = ⓪-a 채택 보류(설계 §3-7-a 📌12″ 과 같은 규칙) → U3 재작업.
