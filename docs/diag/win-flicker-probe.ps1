# 윈 콘솔 창 깜빡임 — 스폰 주체 실측 프로브 (TICKET=v113-restore B10 · 읽기 전용 · 아무것도 바꾸지 않는다)
#
# 쓰는 법(박사님 윈 기기 · PowerShell 창 하나):
#   powershell -ExecutionPolicy Bypass -File win-flicker-probe.ps1            # 기본 10분
#   powershell -ExecutionPolicy Bypass -File win-flicker-probe.ps1 -Minutes 30
# 창이 깜빡이는 걸 보시면 그 시각만 메모해 주세요. 끝나면 바탕화면에 flicker-probe-<시각>.tsv 가 남습니다.
#
# 무엇을 재는가: 1초마다 프로세스 표를 떠서 **새로 생긴 프로세스**를 부모 이름·부모 명령줄과 함께 적는다.
# 콘솔 창은 「콘솔이 없는 부모(cysd·cys-app·node 등)가 콘솔 프로그램을 창 숨김 없이 낳을 때」 뜬다 —
# conhost.exe 가 새로 생긴 줄의 바로 앞 줄(같은 초)이 스폰 주체다.
# 1초보다 짧게 살다 가는 프로세스는 놓칠 수 있다(표본 간격 한계 — 놓친 것이 곧 「없음」은 아니다).
param([int]$Minutes = 10)

$out = Join-Path ([Environment]::GetFolderPath('Desktop')) ("flicker-probe-{0}.tsv" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
"time`tpid`tname`tparent_pid`tparent_name`tparent_cmd`tcmd" | Out-File -FilePath $out -Encoding utf8

function Snap { $h = @{}; Get-CimInstance Win32_Process | ForEach-Object { $h[[int]$_.ProcessId] = $_ }; $h }

$prev = Snap
$end = (Get-Date).AddMinutes($Minutes)
Write-Host "기록 중 — $Minutes 분 · 결과: $out"
while ((Get-Date) -lt $end) {
    Start-Sleep -Seconds 1
    $cur = Snap
    foreach ($id in $cur.Keys) {
        if ($prev.ContainsKey($id)) { continue }
        $p = $cur[$id]
        $pp = $null
        if ($cur.ContainsKey([int]$p.ParentProcessId)) { $pp = $cur[[int]$p.ParentProcessId] }
        elseif ($prev.ContainsKey([int]$p.ParentProcessId)) { $pp = $prev[[int]$p.ParentProcessId] }
        $row = @(
            (Get-Date -Format 'HH:mm:ss'), $p.ProcessId, $p.Name, $p.ParentProcessId,
            $(if ($pp) { $pp.Name } else { '?' }),
            $(if ($pp -and $pp.CommandLine) { $pp.CommandLine -replace "`t|`r|`n", ' ' } else { '' }),
            $(if ($p.CommandLine) { $p.CommandLine -replace "`t|`r|`n", ' ' } else { '' })
        ) -join "`t"
        $row | Out-File -FilePath $out -Append -Encoding utf8
    }
    $prev = $cur
}
Write-Host "끝 — $out 파일을 master 에게 전달해 주세요."
