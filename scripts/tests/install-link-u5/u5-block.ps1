# ── 자동 갱신 잠금 참가·위임 · 롤백 자산 보존 (cysr 1.1.8 · TICKET=cysr-118-u5-install-link · 설계 AUTO-UPDATE-118 §3-2 · §3-7 ② · 📌13′) ──
#   맥판 bootstrap.sh 「자동 갱신 잠금」 절과 같은 계약 — 다른 것만 적는다.
#   · 잠금 = %LOCALAPPDATA%\cys-update\txn.lock 의 0번 바이트 배타 잠금(LockFileEx · FileStream.Lock) — **이 PowerShell 프로세스가 쥔다**
#     (설치 도우미는 `powershell -File` 로 따로 뜬 프로세스라 끝나면 OS 가 푼다). cys 의 잠금(전 범위)·설치기 ⓪-a(0번 바이트)와 겹쳐 서로 막는다.
#   · 소유자 기록 pid = $PID · start_time = 이 프로세스 생성 시각(FILETIME ÷ 10^7 − 11644473600 = cys 가 sysinfo 로 재는 값과 같은 식).
#   · 위임 = env CYS_UPDATE_TXN(이 프로세스 전체 — 설치기 ⓪-a 는 env 와 /CYSTXN 둘 다 본다) + setup.exe /CYSTXN · init-pack·rotate --txn.
#     ⛔오래 사는 자식(cysr 앱 창 · 이 창에서 띄우는 자비스)에게는 물려주지 않는다 — 그 안의 rotate·팩 명령이 rc 26 이 된다(Invoke-WithoutCysTxnEnv).
#   · 롤백 자산 = 새 cys.exe 의 `self-update --preserve-installer`(본문은 불변 보관소에서 · 검증·놓기는 cys 한 곳 · 여기서는 부르기만).
$CysUpdateDir   = Join-Path $env:LOCALAPPDATA 'cys-update'
$CysTxnRetryMax = 3
$CysTxnRetrySec = $(if ($env:JARVIS_TXN_RETRY_SEC) { [int]$env:JARVIS_TXN_RETRY_SEC } else { 30 })   # 시험만 줄인다(사람이 쓰는 길 = 30)
$CysTxnPrivateSddl = 'D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)'   # cys update::ensure_private_dir 와 같은 값(소유자·SYSTEM 만)
$CysTxnBusySay    = '자비스가 지금 새 판으로 바꾸는 중이에요. 5분 뒤 다시 실행해 주세요.'
$CysTxnRecoverSay = '자비스가 지난번 새 판 바꾸기를 마무리하는 중이에요. 5분 뒤 다시 실행해 주세요.'
$script:CysTxnLock  = $null   # 쥔 FileStream
$script:CysTxnToken = ''
$script:CysTxnOwner = $null   # 소유자 기록 칸(묘비를 쓸 때 다시 쓴다)
$script:CysTxnState = ''

function Get-CysTxnStartTime {
    # 이 프로세스 생성 시각(epoch 초) — sysinfo(windows) compute_start 와 같은 식 · 정수 나눗셈(배정밀도로 18자리를 나누면 끝자리가 흔들린다)
    $ft = [long]([System.Diagnostics.Process]::GetCurrentProcess().StartTime.ToFileTimeUtc())
    $rem = [long]0
    return ([System.Math]::DivRem($ft, [long]10000000, [ref]$rem) - [long]11644473600)
}
function New-CysTxnDir {
    # 없으면 소유자 전용 DACL 로 만든다(못 하면 보통 폴더 — 사용자 프로필 상속 꼴도 cys 가 받아들인다) · rc = 폴더가 있는가
    if (Test-Path -LiteralPath $CysUpdateDir -PathType Container) { return $true }
    try {
        $ds = New-Object System.Security.AccessControl.DirectorySecurity
        $ds.SetSecurityDescriptorSddlForm($CysTxnPrivateSddl)
        [void][System.IO.Directory]::CreateDirectory($CysUpdateDir, $ds)
    } catch {
        try { [void][System.IO.Directory]::CreateDirectory($CysUpdateDir) } catch { }
    }
    return (Test-Path -LiteralPath $CysUpdateDir -PathType Container)
}
function Write-CysTxnFile([string]$Path, [byte[]]$Bytes) {
    # 원자 쓰기(임시 → 바꾸기) — 소유자 기록은 cys·설치기 ⓪-a 가 읽는다(찢어진 내용 0)
    #   ⚠윈은 방금 쓴 파일을 백신·색인이 잠깐 열어 두어 바꾸기가 공유 위반으로 실패한다(CI 37548178821 실측: 두 번째 쓰기 = 묘비가 실패).
    #   ⇒ 100ms 간격 30번(3초)까지 다시 해 보고, 그래도 안 되면 지우고 옮긴다(그 사이 기록 없음 = 위임 자식은 거부 = 안전한 쪽).
    $tmp = $Path + '.u5.' + $PID
    [System.IO.File]::WriteAllBytes($tmp, $Bytes)
    $last = $null
    for ($i = 0; $i -lt 30; $i++) {
        try {
            if (Test-Path -LiteralPath $Path) { [System.IO.File]::Replace($tmp, $Path, $null) } else { [System.IO.File]::Move($tmp, $Path) }
            return
        } catch { $last = $_.Exception.Message; Start-Sleep -Milliseconds 100 }
    }
    try {
        [System.IO.File]::Delete($Path); [System.IO.File]::Move($tmp, $Path)
        Write-Log ('txn: 바꾸기 실패 3초 → 지우고 옮김 · ' + $last)
        return
    } catch {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        throw ('바꾸기 실패: ' + $last + ' · 지우고 옮기기 실패: ' + $_.Exception.Message)
    }
}
function ConvertTo-CysTxnOwnerJson($o) {
    # lock.rs Owner 와 같은 칸 · 들여쓰기 JSON(설치기 ⓪-a 는 공백을 걷어 '"txn_id":"<id>"' · '"epoch":<n>,' 를 찾는다)
    $rel = if ($o.released) { 'true' } else { 'false' }
    $j = "{`n  `"owner`": `"install-link`",`n  `"pid`": $($o.pid),`n  `"txn_id`": `"$($o.txn_id)`",`n  `"epoch`": $($o.epoch),`n  `"started_at`": $($o.started_at),`n  `"boot_id`": $($o.boot_id),`n  `"start_time`": $($o.start_time),`n  `"released`": $rel`n}"
    return (New-Object System.Text.UTF8Encoding($false)).GetBytes($j)
}
function Test-CysTxnFree([string]$Path) {
    # 그 잠금 파일이 지금 비었는가(0번 바이트 배타를 잠깐 잡아 본다 · 잡으면 바로 놓는다) · 못 열면 비지 않은 것으로(조용한 진행 0)
    $f = $null
    try {
        $f = [System.IO.File]::Open($Path, 'OpenOrCreate', 'ReadWrite', 'ReadWrite')
        $f.Lock(0, 1); $f.Unlock(0, 1); return $true
    } catch { return $false } finally { if ($f) { $f.Close() } }
}
function Lock-CysTxnOnce {
    # 한 번 잡아 본다 → $script:CysTxnState = ok · busy · nolock (순서 = lock.rs acquire 그대로)
    $script:CysTxnState = 'nolock'
    if (-not (New-CysTxnDir)) { Write-Log 'txn: 갱신 폴더를 만들 수 없음 — 잠금 없이 진행'; return }
    $lockPath = Join-Path $CysUpdateDir 'txn.lock'
    $ownerPath = Join-Path $CysUpdateDir 'txn.owner.json'
    $lk = $null
    try { $lk = [System.IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'ReadWrite') } catch { Write-Log ('txn: 잠금 파일을 열 수 없음 — 잠금 없이 진행 · ' + $_.Exception.Message); return }
    try { $lk.Lock(0, 1) } catch { $lk.Close(); $script:CysTxnState = 'busy'; Write-Log 'txn: busy txn.lock'; return }
    $prev = $null; $epoch = 1
    if (Test-Path -LiteralPath $ownerPath) {
        try { $prev = [System.IO.File]::ReadAllBytes($ownerPath); $epoch = [long]((([System.Text.Encoding]::UTF8.GetString($prev)) | ConvertFrom-Json).epoch) + 1 } catch { $epoch = 1 }
    }
    $rb = New-Object byte[] 16
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($rb)
    $id = -join ($rb | ForEach-Object { $_.ToString('x2') })
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $boot = $now - [long]([System.Diagnostics.Stopwatch]::GetTimestamp() / [System.Diagnostics.Stopwatch]::Frequency)
    $o = [pscustomobject]@{ pid = $PID; txn_id = $id; epoch = $epoch; started_at = $now; boot_id = $boot; start_time = (Get-CysTxnStartTime); released = $false }
    try { Write-CysTxnFile $ownerPath (ConvertTo-CysTxnOwnerJson $o) } catch { $lk.Unlock(0, 1); $lk.Close(); Write-Log ('txn: 소유자 기록을 쓸 수 없음 — 잠금 없이 진행 · ' + $_.Exception.Message); return }
    # 옛 트랜잭션의 위임 자식·토큰 없는 참가 명령이 아직 일하는 중이면 열지 않는다(소유자 기록을 먼저 쓴 뒤에 본다 · 거절이면 직전 기록 복원)
    $names = @('txn.child.lock') + @(1..4 | ForEach-Object { 'txn.child.lock.' + $_ } | Where-Object { Test-Path -LiteralPath (Join-Path $CysUpdateDir $_) }) + @('txn.part.lock')
    foreach ($n in $names) {
        if (Test-CysTxnFree (Join-Path $CysUpdateDir $n)) { continue }
        try { if ($prev) { Write-CysTxnFile $ownerPath $prev } else { Remove-Item -LiteralPath $ownerPath -Force -ErrorAction SilentlyContinue } } catch { }
        $lk.Unlock(0, 1); $lk.Close()
        $script:CysTxnState = 'busy'; Write-Log ('txn: busy ' + $n); return
    }
    $script:CysTxnLock = $lk; $script:CysTxnOwner = $o; $script:CysTxnToken = ($id + ':' + $epoch); $script:CysTxnState = 'ok'
}
function Unlock-CysTxn {
    # 놓기 = 묘비(released:true)를 먼저 쓰고 잠금을 푼다(lock.rs 와 같은 순서) · env 지움 · 쥔 것이 없으면 env 만 지운다
    if ($script:CysTxnLock) {
        try { $script:CysTxnOwner.released = $true; Write-CysTxnFile (Join-Path $CysUpdateDir 'txn.owner.json') (ConvertTo-CysTxnOwnerJson $script:CysTxnOwner) } catch { Write-Log ('txn: 묘비를 쓰지 못함 · ' + $_.Exception.Message) }
        try { $script:CysTxnLock.Unlock(0, 1) } catch { }
        try { $script:CysTxnLock.Close() } catch { }
        Write-Log ('txn: released ' + $script:CysTxnToken)
    }
    $script:CysTxnLock = $null; $script:CysTxnToken = ''
    Remove-Item Env:CYS_UPDATE_TXN -ErrorAction SilentlyContinue
    Remove-Item Env:CYS_UPDATE_TXN_DEPTH -ErrorAction SilentlyContinue
}
function Invoke-WithoutCysTxnEnv([scriptblock]$Body) {
    # 오래 사는 자식(앱 창 · 자비스)을 띄울 때만 토큰 env 를 잠깐 걷는다 — 띄운 뒤 되돌린다
    $saved = $env:CYS_UPDATE_TXN
    Remove-Item Env:CYS_UPDATE_TXN -ErrorAction SilentlyContinue
    try { return (& $Body) } finally { if ($saved) { $env:CYS_UPDATE_TXN = $saved } }
}
function Get-CysTxnJournalWord([string]$Json) {
    # 순수 — `cys self-update --journal-state --json` 한 줄 → wait(온전한 기록이 끝나지 않음) · go · 빈 값(못 읽음)
    try { $j = $Json | ConvertFrom-Json } catch { return '' }
    if ($null -eq $j -or $null -eq $j.journal) { return '' }
    if (($j.journal -eq 'ok') -and ($null -ne $j.terminal) -and (-not $j.terminal)) { return 'wait' }
    return 'go'
}
function Get-CysSetupArgs([string]$Dir) {
    # 순수 — 설치기 인자 한 문자열(NSIS: /S · 잠금을 쥐었으면 /CYSTXN=<토큰> · /D 는 마지막·따옴표 없이)
    $txnArg = if ($script:CysTxnToken) { ' /CYSTXN=' + $script:CysTxnToken } else { '' }
    return ('/S' + $txnArg + ' /D=' + $Dir)
}
function Get-CysTxnJournalVerdict {
    # go · wait — 지난 갱신 기록이 온전한데 끝나지 않았을 때만 wait · 망가졌거나 판정할 cys 가 없으면 go(📌18 재설치 길)
    if (-not (Test-Path -LiteralPath (Join-Path $CysUpdateDir 'journal.json')) -and -not (Test-Path -LiteralPath (Join-Path $CysUpdateDir 'journal.prev.json'))) { return 'go' }
    $cands = @((Join-Path $CysUpdateDir 'runner\cys.exe'))
    try { $b = Test-CysBody; if ($b.Body -and $b.Cli) { $cands += [string]$b.Cli } } catch { }
    foreach ($c in $cands) {
        if (-not (Test-Path -LiteralPath $c)) { continue }
        try {
            $out = (& $c self-update --journal-state --json 2>$null) -join ''
            if ($LASTEXITCODE -ne 0 -or -not $out) { continue }
            $v = Get-CysTxnJournalWord $out
            if (-not $v) { continue }
            Write-Log ('txn: journal ' + $out + ' (판정 ' + $v + ' · ' + (Redact $c) + ')')
            return $v
        } catch { continue }
    }
    Write-Log 'txn: 저널 판정 불가(판정할 cys 없음) — 진행'
    return 'go'
}
function Enter-CysTxn {
    # 본문 시작 직후 · 0 = 계속 · 26 = 끝(문구·진단 코드를 찍었다)
    if ($Mode -ne 'full') { return 0 }
    $n = 0
    while ($true) {
        Lock-CysTxnOnce
        if ($script:CysTxnState -ne 'busy') { break }
        $n++
        if ($n -gt $CysTxnRetryMax) { break }
        Write-Log ('txn: busy — ' + $CysTxnRetrySec + 's 뒤 다시(' + $n + '/' + $CysTxnRetryMax + ')')
        Start-Sleep -Seconds $CysTxnRetrySec
    }
    if ($script:CysTxnState -eq 'busy') {
        Say $CysTxnBusySay
        Write-JCode 'J-UPD-01' '자비스가 새 판으로 바꾸는 중이라 이번에는 아무것도 바꾸지 않았습니다'
        Set-NextStepRerun '5분 뒤 아래 「다시 하시는 법」대로 다시 실행해 주십시오.'
        return 26
    }
    if ($script:CysTxnState -ne 'ok') { return 0 }
    $env:CYS_UPDATE_TXN = $script:CysTxnToken
    Write-Log ('txn: held ' + $script:CysTxnToken + ' (owner pid ' + $PID + ')')
    if ((Get-CysTxnJournalVerdict) -eq 'wait') {
        Unlock-CysTxn
        Say $CysTxnRecoverSay
        Write-JCode 'J-UPD-02' '지난번 새 판 바꾸기의 마무리를 기다립니다'
        Set-NextStepRerun '5분 뒤 아래 「다시 하시는 법」대로 다시 실행해 주십시오.'
        return 26
    }
    return 0
}
function Invoke-CysTxnLogged($what, $cli, $cmdArgs) {
    # Invoke-Logged 와 같되 잠금을 쥐었으면 --txn 위임 · 위임 거부(rc 26)면 잠금을 놓고 토큰 없이 한 번 더(설치는 끝까지)
    if ($script:CysTxnToken) {
        $rc = Invoke-Logged $what $cli (@($cmdArgs) + @('--txn', $script:CysTxnToken))
        if ($rc -ne 26) { return $rc }
        Write-Log ('txn: ' + $what + ' 위임 거부(rc 26) — 잠금을 놓고 토큰 없이 한 번 더')
        Unlock-CysTxn
    }
    return (Invoke-Logged $what $cli $cmdArgs)
}
function Save-CysRollbackAssets([string]$Dir, [string]$Setup) {
    # 방금 깐 설치기를 자동 갱신의 롤백 자산으로 보존(N7) — cys.exe 가 받고·검증하고·놓는다 · 돌려주는 것 = ok · skip · fail-<rc>
    #   ⚠설치는 이미 끝났다 — 못 챙겨도 지금 쓰는 데는 지장이 없다. 대신 조용히 넘어가지 않고 한 줄로 말한다(자동 갱신이 이 기계에서 멈춰 서는 까닭이 된다).
    $cli = Join-Path $Dir 'cys.exe'
    if (-not (Test-Path -LiteralPath $cli) -or -not (Test-Path -LiteralPath $Setup)) { Write-Log 'rollback assets: cys.exe 또는 설치기 없음 — 건너뜀'; return 'skip' }
    $out = ''; $rc = -1
    try { $out = (& $cli self-update --preserve-installer --setup $Setup --json 2>&1) -join ' '; $rc = $LASTEXITCODE } catch { $out = $_.Exception.Message }
    Write-Log ('rollback assets: rc=' + $rc + ' ' + $out)
    if ($rc -eq 0) { return 'ok' }
    if ($out -match 'unrecognized|unexpected argument') { return 'skip' }   # 옛 판(1.1.7 이하)은 이 입구가 없다 — 그 판엔 자동 갱신도 없다
    Say '     자비스가 나중에 새 판으로 바꿀 때 쓸 되돌림 파일을 이번에는 챙기지 못했습니다. 지금 쓰시는 데는 지장이 없습니다.'
    Say '     이 설치 한 줄을 나중에 다시 실행하시면 다시 챙깁니다.'
    Send-Progress '6/10' 'info' $null ('rollback-assets:fail rc=' + $rc) $null
    return ('fail-' + $rc)
}

