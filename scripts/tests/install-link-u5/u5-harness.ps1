# 1.1.8 U5 — 설치 링크 「자동 갱신 잠금」 블록(u5-block.ps1 = ai-jarvis site/install/bootstrap.ps1 의 그 절 · 바이트 그대로 사본)을
#   설치 도우미 본문 없이 읽어 들이는 하네스. 블록이 부르는 본문 함수만 같은 이름·같은 뜻의 최소 대역으로 둔다(화면·기록·진행 전송).
#   ⛔블록을 여기서 고치지 마라 — 원본(bootstrap.ps1)을 고치고 ai-jarvis tests/install-u5/sync-cys-contract.py --write 로 다시 옮긴다
#   (그 도구의 --check 가 사본 = 원본 바이트를 잰다 · 다르면 이 CI 초록은 거짓).
$ErrorActionPreference = 'Continue'
$Mode = 'full'
$JarvisHome = if ($env:JARVIS_HOME) { $env:JARVIS_HOME } else { Join-Path ([System.IO.Path]::GetTempPath()) 'u5-harness' }
$LogFile = Join-Path $JarvisHome 'bootstrap.log'
$script:JCode = ''
$script:NextStep = ''
function Write-Log($msg) { try { Add-Content -LiteralPath $LogFile -Value ((Get-Date).ToString('s') + ' ' + $msg) -Encoding UTF8 } catch { } }
function Say($msg) { Write-Host $msg; Write-Log $msg }
function Write-JCode($code, $desc) { $script:JCode = $code; Say ('     진단 코드: ' + $code + ' — ' + $desc) }
function Set-NextStepRerun($text) { $script:NextStep = $text }
function Send-Progress($step, $ev, $elapsed, $detail, $envInfo, $extra) { }
function Redact($s) { return $s }
function Test-CysBody { return [pscustomobject]@{ Body = $false; Cli = ''; Path = '' } }
function Invoke-Logged($what, $cmd, $cmdArgs) {
    $out = & $cmd @cmdArgs 2>&1
    $code = $LASTEXITCODE
    foreach ($ln in $out) { Say "       $ln" }
    Write-Log "[$what] rc=$code"
    return $code
}
function Invoke-CysCapped([string]$Cli, [string]$ArgLine, [int]$CapMs) {
    # 본문(bootstrap.ps1)과 같은 뜻 — 표준 출력 · 상한·실패·rc ≠ 0 = $null · CYS_NO_AUTOSTART=1
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Cli; $psi.Arguments = $ArgLine; $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.CreateNoWindow = $true
        $psi.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $psi.EnvironmentVariables['CYS_NO_AUTOSTART'] = '1'
        $p = [System.Diagnostics.Process]::Start($psi)
        $so = $p.StandardOutput.ReadToEndAsync(); [void]$p.StandardError.ReadToEndAsync()
        if (-not $p.WaitForExit($CapMs)) { try { $p.Kill() } catch { }; return $null }
        if (-not $so.Wait(2000)) { return $null }
        if ($p.ExitCode -ne 0) { return $null }
        return $so.Result
    } catch { return $null }
}
. (Join-Path $PSScriptRoot 'u5-block.ps1')
