# 1.1.8 U5 — bootstrap.ps1 본문 함수 사본(sync-cys-contract.py 가 뗀다 · 손으로 고치지 마라)
function Invoke-CysCapped([string]$Cli, [string]$ArgLine, [int]$CapMs) {
    # 돌려주는 것 = 표준 출력 글자 · 상한에 닿았거나 실패면 $null(콘솔 입력을 건드리지 않는다)
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Cli
        $psi.Arguments = $ArgLine
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $psi.CreateNoWindow = $true
        $psi.EnvironmentVariables['CYS_NO_AUTOSTART'] = '1'
        $p = [System.Diagnostics.Process]::Start($psi)
        $so = $p.StandardOutput.ReadToEndAsync()
        [void]$p.StandardError.ReadToEndAsync()
        if (-not $p.WaitForExit($CapMs)) { try { $p.Kill() } catch { }; return $null }
        if (-not $so.Wait(2000)) { return $null }
        if ($p.ExitCode -ne 0) { return $null }
        return $so.Result
    } catch { return $null }
}
