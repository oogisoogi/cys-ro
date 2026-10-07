# 1.1.8 U5 — 설치 링크(bootstrap.ps1)의 자동 갱신 잠금 참가·위임 실측(TICKET=cysr-118-u5-install-link · 설계 AUTO-UPDATE-118 §3-2 · §3-7 ②).
#
# 두 길
#   · 어디서나(맥 pwsh 포함) = 순수 함수·구조 — 저널 판정 낱말 · 설치기 인자(/CYSTXN 바이트) · 소유자 기록 JSON(설치기 ⓪-a 가 찾는 꼴 · cys Owner 칸) ·
#     시작 시각 식(맥은 ps 의 커널 시작 시각과 대조) · 토큰 env 걷기 · 놓기·위임 자리 구조
#   · 윈도우 + -Cys <cys.exe>(1.1.8 debug 또는 설치본) = 실물 — 잡기 → 실 cys 가 --txn 위임을 받음 · 뮤테이션(env 누락 · 토큰 틀림 · 토큰 없음 ·
#     시작 시각 틀림 = 전부 rc 26) · 남이 쥠(다른 프로세스) = 재시도 뒤 rc 26 + J-UPD-01 + 소유자 기록 무변화 · 위임 자식 잠금 쥠 = busy ·
#     놓기 = 묘비 뒤 해제 · 위임 거부(rc 26) → 놓고 토큰 없이 한 번 더
# 쓰는 법: pwsh -NoProfile -File tests/install-u5/u5-win-lock.ps1 [-Cys <cys.exe>] [-Ps1 <bootstrap.ps1>]   · rc 0 = 통과
# ⛔바깥에 닿지 않는다 — LOCALAPPDATA·JARVIS_HOME 을 임시 폴더로 · 진행 전송 끔(JARVIS_LIB_ONLY) · 이 시험이 띄운 프로세스만 거둔다.
param([string]$Cys = '', [string]$Ps1 = '')
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$script:real = 0   # 실물 갈래가 돌았는가(CI 가 ASCII 마지막 줄로 읽는다)
if (-not $Ps1) { $Ps1 = Join-Path $PSScriptRoot '..\..\site\install\bootstrap.ps1' }
$Ps1 = (Resolve-Path $Ps1).Path
$base = Join-Path ([System.IO.Path]::GetTempPath()) ('u5winlock-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $base | Out-Null
$script:pass = 0; $script:fail = 0
function T([bool]$ok, [string]$name, [string]$why) {
    if ($ok) { $script:pass++; Write-Host ('  ok   ' + $name) } else { $script:fail++; Write-Host ('  FAIL ' + $name + '  <- ' + $why) }
}
$isWin = ($PSVersionTable.PSVersion.Major -le 5) -or $IsWindows
$env:LOCALAPPDATA = Join-Path $base 'lad'
New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA | Out-Null
$env:JARVIS_HOME = Join-Path $base 'install-jarvis'
New-Item -ItemType Directory -Force -Path $env:JARVIS_HOME | Out-Null
$env:JARVIS_LIB_ONLY = '1'
$env:JARVIS_TXN_RETRY_SEC = '0'
Remove-Item Env:CYS_UPDATE_TXN -ErrorAction SilentlyContinue
Remove-Item Env:CYS_UPDATE_STATE_DIR -ErrorAction SilentlyContinue
$env:CYS_PACK_DIR = Join-Path $base 'pack'
. $Ps1 *> $null
$U = $CysUpdateDir
$txt = Get-Content -LiteralPath $Ps1 -Raw -Encoding UTF8

# ── 순수·구조 (어디서나) ──
T ((Get-CysTxnJournalWord '{"detail":null,"journal":"ok","lock_held":true,"state":"STOPPED","terminal":false}') -eq 'wait') '[순수] 온전·비종결 저널 = wait' 'x'
T ((Get-CysTxnJournalWord '{"detail":"x","journal":"corrupt","lock_held":true,"state":null,"terminal":null}') -eq 'go') '[순수] 손상 저널 = go(📌18 재설치 길)' 'x'
T ((Get-CysTxnJournalWord '{"detail":"x","journal":"degraded","lock_held":false,"state":"STOPPED","terminal":null}') -eq 'go') '[순수] 한 슬롯 손상 = go' 'x'
T ((Get-CysTxnJournalWord '{"detail":null,"journal":"ok","lock_held":false,"state":"DONE","terminal":true}') -eq 'go') '[순수] 종결 = go' 'x'
T ((Get-CysTxnJournalWord 'error: unexpected argument') -eq '') '[순수] 못 읽음(옛 판) = 빈 값 → 다음 후보' 'x'
$script:CysTxnToken = ''
T ((Get-CysSetupArgs 'D:\app data\cys') -ceq '/S /D=D:\app data\cys') '[순수] 잠금 없음 = 종전 인자 그대로' (Get-CysSetupArgs 'C:\x')
$script:CysTxnToken = ('ab' * 16) + ':7'
T ((Get-CysSetupArgs 'C:\x') -ceq ('/S /CYSTXN=' + ('ab' * 16) + ':7 /D=C:\x')) '[순수] 잠금 쥠 = /CYSTXN=<토큰> 바이트 그대로 · /D 마지막' (Get-CysSetupArgs 'C:\x')
$script:CysTxnToken = ''
$o = [pscustomobject]@{ pid = 4242; txn_id = ('cd' * 16); epoch = 7; started_at = 1790000000; boot_id = 1789990000; start_time = 1789999999; released = $false }
$js = [System.Text.Encoding]::UTF8.GetString((ConvertTo-CysTxnOwnerJson $o))
$flat = ($js -replace '\s', '')
T ($flat.Contains('"txn_id":"' + ('cd' * 16) + '"') -and $flat.Contains('"epoch":7,')) '[순수] 소유자 기록 = 설치기 ⓪-a 가 찾는 꼴("txn_id":"…" · "epoch":7,)' $flat
$pj = $js | ConvertFrom-Json
T (($pj.owner -eq 'install-link') -and ($pj.pid -eq 4242) -and ($pj.start_time -eq 1789999999) -and ($pj.released -eq $false) -and ($null -ne $pj.boot_id) -and ($null -ne $pj.started_at)) '[순수] 소유자 기록 = cys Owner 칸 8개' $js
$o.released = $true
T (([System.Text.Encoding]::UTF8.GetString((ConvertTo-CysTxnOwnerJson $o)) -replace '\s', '').Contains('"released":true}')) '[순수] 묘비 = released:true' 'x'
$script:CysTxnToken = ('ef' * 16) + ':3'
$in1 = Invoke-WithCysTxnEnv { [string]$env:CYS_UPDATE_TXN }
$after1 = [string]$env:CYS_UPDATE_TXN
$script:CysTxnToken = ''
$in2 = Invoke-WithCysTxnEnv { [string]$env:CYS_UPDATE_TXN }
T (($in1 -eq (('ef' * 16) + ':3')) -and (-not $after1) -and (-not $in2)) '[순수] 토큰 env = Invoke-WithCysTxnEnv 블록 안에만 · 뒤에 지움 · 쥔 것 없으면 0(2판 agy1·codex4)' ("in=$in1 after=$after1 none=$in2")
$edef = [string](Get-Command Enter-CysTxn -CommandType Function -ErrorAction SilentlyContinue).Definition
T (($edef -match 'Remove-Item Env:CYS_UPDATE_TXN') -and ($edef -notmatch '\$env:CYS_UPDATE_TXN\s*=')) '[구조] Enter-CysTxn = 프로세스 전체 토큰 env 0 · 물려받은 것도 지움' 'x'
$env:CYS_UPDATE_TXN = 'zz'
$inside = Invoke-WithoutCysTxnEnv { [string]$env:CYS_UPDATE_TXN }
T (($inside -eq '') -and ($env:CYS_UPDATE_TXN -eq 'zz')) '[순수] 오래 사는 자식을 띄우는 동안만 토큰 env 0 · 뒤에 되돌림' ('inside=' + $inside + ' after=' + $env:CYS_UPDATE_TXN)
Remove-Item Env:CYS_UPDATE_TXN -ErrorAction SilentlyContinue
$st = Get-CysTxnStartTime
if (-not $isWin) {
    $ls = (& /bin/sh -c ('TZ=UTC0 LC_ALL=C ps -o lstart= -p ' + $PID)).Trim()
    $ref = (& /bin/sh -c ("TZ=UTC0 LC_ALL=C date -j -f '%a %b %e %T %Y' '" + $ls + "' '+%s'")).Trim()
    T ("$st" -eq "$ref") '[식] 시작 시각 식 = 커널 시작 시각(맥 ps 대조 · FILETIME 식의 정수 나눗셈 검사)' ("ps1=$st ps=$ref")
} else {
    T ($st -gt 1700000000) '[식] 시작 시각 = epoch 초(윈 · 실 대조는 아래 실 cys 위임 수용)' "$st"
}
# 구조 — 놓기·위임 자리(맥판 ⓗ 짝) · cys 저장소 계약 하네스(블록만)에서는 본문이 없어 건너뛴다(그 대조는 맥 시험 --cys-tree 가 원본으로 한다)
$wdef = [string](Get-Command Write-CysTxnFile -CommandType Function -ErrorAction SilentlyContinue).Definition
T (($wdef -match 'Rename-CysTxnReplace') -and ($wdef -notmatch '::Delete\(')) '[구조] 소유자 기록 바꿔치기 = 지우고 옮기기 폴백 0(2판 codex 3)' 'x'
if ($txt -match 'function Step-InstallCys') {
T ($txt -match "(?m)^\s+Unlock-CysTxn\r?\n\s+& \`$fallbackExe --dangerously-skip-permissions") '[구조] 이 창에서 자비스를 띄우기 바로 앞에 Unlock-CysTxn' 'x'
T ($txt -match "(?m)^\s+try \{ Unlock-CysTxn \} catch \{ \}\s+# 1\.1\.8 U5[^\n]*\r?\n\s+try \{ Write-ClosingNote \}") '[구조] 본문 finally 첫 줄 = Unlock-CysTxn(끝맺음·원격 해결 전)' 'x'
T ($txt -match "(?m)^\s+\`$rc = Enter-CysTxn; if \(\`$rc -ne 0\) \{ exit \`$rc \}") '[구조] 본문 시작에 Enter-CysTxn' 'x'
T ($txt -match "Invoke-WithoutCysTxnEnv \{ \[void\]\(Start-Process -FilePath \`$exe") '[구조] 앱 창 = 토큰 env 0' 'x'
T ($txt -match "Invoke-WithoutCysTxnEnv \{ Start-Process -FilePath \`$sideCar") '[구조] 곁 프로그램 직접 켜기 = 토큰 env 0' 'x'
T ($txt -match "Invoke-CysTxnLogged 'init-pack' \`$cli @\('init-pack'\)") '[구조] init-pack = 위임 입구' 'x'
T ($txt -match "' --txn ' \+ \`$script:CysTxnToken") '[구조] rotate = --txn 위임' 'x'
T ($txt -match "Get-CysSetupArgs \`$dir\) -PassThru") '[구조] 설치기 = Get-CysSetupArgs(/CYSTXN)' 'x'
T ($txt -match "\[void\]\(Save-CysRollbackAssets \`$dir \`$dst\)") '[구조] 설치 확인 뒤 롤백 자산 보존' 'x'
T ($txt -match "if \(\`$script:JCode -in @\('J-UPD-01', 'J-UPD-02'\)\) \{ return \}") '[구조] 기다림 코드(J-UPD-01·02)는 원격 해결을 열지 않는다' 'x'
} else { Write-Host '  (구조 생략 — 블록만 읽은 하네스)' }

# ── 실물 (윈도우 + 실 cys) ──
$kids = @()
if ($isWin -and $Cys) {
    $Cys = (Resolve-Path $Cys).Path
    function Probe([string[]]$CysArgs, [bool]$NoEnv) {
        # NoEnv = 보통 호출(토큰 env 0) · 아니면 Invoke-WithCysTxnEnv(그 호출에만 토큰 env — 설치 도우미가 참가 명령을 부르는 꼴)
        if ($NoEnv) { $o = (& $Cys @CysArgs 2>&1) -join ' ' } else { $o = Invoke-WithCysTxnEnv { (& $Cys @CysArgs 2>&1) -join ' ' } }
        $rc = $LASTEXITCODE
        return @($rc, $o)
    }
    function HolderProc([string]$Path) {
        # 다른 프로세스가 0번 바이트를 배타로 쥔다(가짜 러너 · 30초)
        $ps = (Get-Process -Id $PID).Path
        $cmd = "`$f=[IO.File]::Open('" + $Path + "','OpenOrCreate','ReadWrite','ReadWrite'); `$f.Lock(0,1); Start-Sleep 30"
        return (Start-Process -FilePath $ps -ArgumentList @('-NoProfile', '-Command', $cmd) -PassThru -WindowStyle Hidden)
    }
    $script:real = 1
    $rc = Enter-CysTxn
    T (($rc -eq 0) -and ($script:CysTxnState -eq 'ok') -and $script:CysTxnToken) '[ⓐ] 잡기 = 0 · 토큰 있음' ("rc=$rc state=$($script:CysTxnState)")
    $childEnv = ((& (Get-Process -Id $PID).Path -NoProfile -Command '[string]$env:CYS_UPDATE_TXN') -join '').Trim()   # 실제 자식 프로세스가 물려받는 env
    T (-not $childEnv) '[ⓛ] 잡은 뒤 프로세스 전체 토큰 env 0(클로드 설치기·로그인 꼴 자식이 못 본다 · 2판 agy1·codex4)' ("env=" + $childEnv)
    T (-not (Test-CysTxnFree (Join-Path $U 'txn.lock'))) '[ⓐ] 쥔 동안 0번 바이트 배타 불가' 'x'
    $tok = $script:CysTxnToken
    $r = Probe @('pack-plan', '--txn', $tok) $false
    T (($r[0] -ne 26) -and ($r[1] -notmatch 'txn_busy')) '[ⓐ] 실 cys 가 위임을 받는다(pack-plan --txn + env · rc ≠ 26)' ("rc=" + $r[0] + ' ' + $r[1])
    $r = Probe @('pack-plan', '--txn', $tok) $true
    T ($r[0] -eq 26) '[ⓑ] 뮤테이션: env 누락 = rc 26(⓪)' ("rc=" + $r[0])
    $r = Probe @('pack-plan', '--txn', ($tok.Split(':')[0] + ':999')) $false
    T ($r[0] -eq 26) '[ⓑ] 뮤테이션: 토큰 epoch 틀림 = rc 26(①)' ("rc=" + $r[0])
    $r = Probe @('pack-plan') $true
    T ($r[0] -eq 26) '[ⓑ] 토큰 없는 참가 명령 = rc 26(잠금 소유 중)' ("rc=" + $r[0])
    $raw = [System.IO.File]::ReadAllText((Join-Path $U 'txn.owner.json')) -replace '\s', ''
    T ($raw.Contains('"txn_id":"' + $tok.Split(':')[0] + '"') -and $raw.Contains('"epoch":' + $tok.Split(':')[1] + ',')) '[ⓖ] 실 소유자 기록 = 설치기 ⓪-a 가 찾는 꼴' $raw
    Unlock-CysTxn
    $ow = [System.IO.File]::ReadAllText((Join-Path $U 'txn.owner.json')) | ConvertFrom-Json
    T (($ow.released -eq $true) -and (Test-CysTxnFree (Join-Path $U 'txn.lock')) -and (-not $env:CYS_UPDATE_TXN)) '[ⓔ] 놓기 = 묘비 + 해제 + env 지움' ("released=" + $ow.released)
    # ⓚ 묘비를 못 쓰면 놓지 않는다(2판 codex 3) — 소유자 기록을 읽기 전용으로(바꿔치기 거부 주입) → 잠금 쥔 채 · 묘비 없음 · 토큰·env 거둠 · 다시 놓으면 묘비 + 해제
    [void](Enter-CysTxn)
    $own = Join-Path $U 'txn.owner.json'
    Set-ItemProperty -LiteralPath $own -Name IsReadOnly -Value $true
    Unlock-CysTxn
    $rel = ([System.IO.File]::ReadAllText($own) | ConvertFrom-Json).released
    T ((-not (Test-CysTxnFree (Join-Path $U 'txn.lock'))) -and ($rel -eq $false) -and ($null -ne $script:CysTxnLock) -and (-not $script:CysTxnToken) -and (-not $env:CYS_UPDATE_TXN)) '[ⓚ] 묘비 실패 = 잠금 쥔 채 · 묘비 없음 · 토큰·env 거둠(2판 codex 3)' ("released=$rel lock=" + ($null -ne $script:CysTxnLock))
    Set-ItemProperty -LiteralPath $own -Name IsReadOnly -Value $false
    Unlock-CysTxn
    $rel = ([System.IO.File]::ReadAllText($own) | ConvertFrom-Json).released
    T (($rel -eq $true) -and (Test-CysTxnFree (Join-Path $U 'txn.lock')) -and ($null -eq $script:CysTxnLock) -and (@(Get-ChildItem -LiteralPath $U -Filter '*.u5.*').Count -eq 0)) '[ⓚ] 다시 놓기 = 묘비 + 해제 · 임시 파일 0' ("released=$rel")
    # ⓑ′ 시작 시각 틀림
    function Get-CysTxnStartTime { return [long]1000000000 }
    [void](Enter-CysTxn)
    $r = Probe @('pack-plan', '--txn', $script:CysTxnToken) $false
    T ($r[0] -eq 26) '[ⓑ′] 뮤테이션: 시작 시각 틀림 = rc 26(③′ · 위 ⓐ 수용이 식 덕분임을 가른다)' ("rc=" + $r[0] + ' ' + $r[1])
    Unlock-CysTxn
    Remove-Item Function:\Get-CysTxnStartTime
    . $Ps1 *> $null   # 함수 원래대로
    # ⓒ 남이 쥠
    $h = HolderProc (Join-Path $U 'txn.lock'); $kids += $h; Start-Sleep -Seconds 3
    $before = (Get-FileHash -LiteralPath (Join-Path $U 'txn.owner.json')).Hash
    $script:JCode = ''
    $rc = Enter-CysTxn *> $null; $rc = $script:CysTxnState
    T (($script:JCode -eq 'J-UPD-01') -and ($rc -eq 'busy')) '[ⓒ] 남이 쥠 = 재시도 뒤 busy · J-UPD-01' ("state=$rc jcode=$($script:JCode)")
    T ((Get-FileHash -LiteralPath (Join-Path $U 'txn.owner.json')).Hash -eq $before) '[ⓒ] 남의 잠금 앞에서 소유자 기록 무변화' 'x'
    Stop-Process -Id $h.Id -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 1
    # ⓒ′ 위임 자식 잠금을 남이 쥠
    $h2 = HolderProc (Join-Path $U 'txn.child.lock'); $kids += $h2; Start-Sleep -Seconds 3
    $before = (Get-FileHash -LiteralPath (Join-Path $U 'txn.owner.json')).Hash
    Lock-CysTxnOnce
    T (($script:CysTxnState -eq 'busy') -and ((Get-FileHash -LiteralPath (Join-Path $U 'txn.owner.json')).Hash -eq $before) -and (Test-CysTxnFree (Join-Path $U 'txn.lock'))) '[ⓒ′] 위임 자식 잠금 쥠 = busy · 직전 기록 복원 · txn.lock 놓음' ("state=" + $script:CysTxnState)
    Stop-Process -Id $h2.Id -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 1
    # ⓕ 위임 거부 → 놓고 한 번 더
    $fake = Join-Path $base 'fakecli.cmd'
    Set-Content -LiteralPath $fake -Encoding ASCII -Value "@echo off`r`necho %*>>`"$base\calls.txt`"`r`necho %* | findstr /C:`"--txn`" >nul && exit /b 26`r`nexit /b 0`r`n"
    [void](Enter-CysTxn)
    function Stop-CysTxnRefused([string]$What) { throw ('U5REFUSED:' + $What) }   # 진짜는 exit 26 — 시험 프로세스를 끝내지 않게 표지로 바꿔 잰다
    $refused = ''
    try { [void](Invoke-CysTxnLogged 'init-pack' $fake @('init-pack')) } catch { $refused = [string]$_.Exception.Message }
    $calls = @(Get-Content -LiteralPath (Join-Path $base 'calls.txt'))
    T (($refused -eq 'U5REFUSED:init-pack') -and ($calls.Count -eq 1)) '[ⓕ] 위임 거부(rc 26) = 끝 · 무잠금 재실행 0(호출 1회 · 2판 codex 1)' ("refused=$refused calls=" + ($calls -join '|'))
    Unlock-CysTxn
    . $Ps1 *> $null
} elseif ($isWin) {
    Write-Host '  (실물 생략 — -Cys <1.1.8 cys.exe> 를 주면 잠금·위임 실측까지 돈다)'
}
foreach ($k in $kids) { Stop-Process -Id $k.Id -Force -ErrorAction SilentlyContinue }
Unlock-CysTxn
Remove-Item -Recurse -Force -LiteralPath $base -ErrorAction SilentlyContinue
if ($script:fail -gt 0) {
    # 적색이면 설치 도우미 기록(txn 줄)을 그대로 찍는다 — 원격 CI 에서 원인을 재현 없이 읽게
    $lf = $LogFile
    Write-Host ('--- bootstrap.log (' + $lf + ' · 있음=' + (Test-Path -LiteralPath $lf) + ') ---')
    if (Test-Path -LiteralPath $lf) { Get-Content -LiteralPath $lf -Encoding UTF8 | Select-Object -Last 40 | ForEach-Object { Write-Host ('  LOG ' + $_) } }
}
Write-Host ("== 합계: ok " + $script:pass + " · FAIL " + $script:fail + " ==")
Write-Host ("U5-RESULT ok=" + $script:pass + " fail=" + $script:fail + " real=" + $script:real)   # ASCII 판정 줄(CI 콘솔 글자표와 무관)
if ($script:fail -gt 0) { exit 1 } else { exit 0 }
