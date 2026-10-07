# ── 자동 갱신 잠금 참가·위임 · 롤백 자산 보존 (cysr 1.1.8 · TICKET=cysr-118-u5-install-link · 설계 AUTO-UPDATE-118 §3-2 · §3-7 ② · 📌13′) ──
#   맥판 bootstrap.sh 「자동 갱신 잠금」 절과 같은 계약 — 다른 것만 적는다.
#   · 잠금 = %LOCALAPPDATA%\cys-update\txn.lock 의 0번 바이트 배타 잠금(LockFileEx · FileStream.Lock) — **이 PowerShell 프로세스가 쥔다**
#     (설치 도우미는 `powershell -File` 로 따로 뜬 프로세스라 끝나면 OS 가 푼다). cys 의 잠금(전 범위)·설치기 ⓪-a(0번 바이트)와 겹쳐 서로 막는다.
#   · 소유자 기록 pid = $PID · start_time = 이 프로세스 생성 시각(FILETIME ÷ 10^7 − 11644473600 = cys 가 sysinfo 로 재는 값과 같은 식).
#   · 위임 = setup.exe /CYSTXN · init-pack·rotate --txn + **그 자식에만** env CYS_UPDATE_TXN(Invoke-WithCysTxnEnv · rotate 는 psi 환경) · 데몬을 띄울 수 있는
#     cys 호출(ping·daemon·new-surface·감지 표)도 그 호출에만(잠금을 쥔 동안 토큰 없는 자동 기동은 cys 가 거부한다).
#     ⛔프로세스 전체 $env: 0(2판 agy1·codex4) — 클로드 설치기·로그인·앱 창·자비스는 토큰을 못 본다(그 후손이 토큰으로 참가 명령을 부르면 조상 검증까지 통과한다).
#   · 롤백 자산 = 새 cys.exe 의 `self-update --preserve-installer`(본문은 불변 보관소에서 · 검증·놓기는 cys 한 곳 · 여기서는 부르기만).
$CysUpdateDir   = Join-Path $env:LOCALAPPDATA 'cys-update'
$CysTxnRetryMax = 3
$CysTxnRetrySec = $(if ($env:JARVIS_TXN_RETRY_SEC) { [int]$env:JARVIS_TXN_RETRY_SEC } else { 30 })   # 시험만 줄인다(사람이 쓰는 길 = 30)
$CysTxnPrivateSddl = 'D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)'   # cys update::ensure_private_dir 와 같은 값(소유자·SYSTEM 만)
$CysTxnBusySay    = '자비스가 지금 새 판으로 바꾸는 중이에요. 5분 뒤 다시 실행해 주세요.'
$CysTxnRecoverSay = '자비스가 지난번 새 판 바꾸기를 마무리하는 중이에요. 5분 뒤 다시 실행해 주세요.'
$CysTxnWaitSay    = '자비스가 지금 새 판으로 바꾸는 중이라 잠시 기다려 봅니다(최대 약 2분).'   # 3판(Opus 2R N8): 첫 재시도에 화면 1줄(무화면 ≈130초 제거)
# 3판(Opus 2R N1 · agy 2R): 기다려도 안 풀리는 원인 = J-UPD-03 「잠금 자리 이상」(원인별 문구 · 원격 해결 열림) — busy 만 J-UPD-01(기다림)
$CysTxnOddSay = @{
    unsafe  = '자비스의 새 판 바꾸기 자리(cys-update 폴더)가 이 계정 전용이 아니거나 다른 곳으로 이어져 있어, 안전을 위해 아무것도 바꾸지 않았습니다.'
    nolock  = '자비스의 새 판 바꾸기 자리(잠금 파일)를 열거나 쓰지 못해 아무것도 바꾸지 않았습니다. 백신이나 권한 때문일 수 있습니다.'
    refused = '자비스의 새 판 바꾸기 자리를 이 설치 도우미가 넘겨받지 못해 여기서 멈췄습니다.'
    nojudge = '지난번 새 판 바꾸기 기록이 오래 남아 있는데 판정할 프로그램이 없어, 덮어 깔지 않고 멈췄습니다.'
}
$CysTxnJournalStaleMin = 30   # 3판(N1 ⑥): 판정할 cys 가 없는 저널이 이보다 오래면 기다려도 안 풀린다 = J-UPD-03(종결 저널은 제외 · 4판 m2)
$CysTxnRecheckMax = 3          # 4판(Opus 3R m4): nolock(자리를 못 엶·씀)은 J-UPD-03 전에 제자리 짧은 재확인 — 백신 순간 잠김 흡수 · busy 기다림과 별개
$CysTxnRecheckSec = $(if ($null -ne $env:JARVIS_TXN_RECHECK_SEC) { [int]$env:JARVIS_TXN_RECHECK_SEC } else { 1 })   # 상한 = 3 × 1초(시험만 줄인다)
$CysTxnTerminalStates = @('DONE', 'DEFERRED', 'RB_DONE', 'RB_FAILED', 'PACK_DONE')   # cys journal::State::is_terminal 과 같은 칸
$CysAssetsDlTimeoutSec = $(if ($env:JARVIS_ASSETS_DL_TIMEOUT_SEC) { [int]$env:JARVIS_ASSETS_DL_TIMEOUT_SEC } else { 900 })   # 4판(Opus 3R M1): 본 받기([5/10] -TimeoutSec 900)와 같은 상한
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
function Test-CysTxnSddlPrivate([string]$Sddl, [string]$Me) {
    # 순수 — cys update::sd_is_private 와 같은 규칙: 소유자 = 나·BA·SY · 허용 ACE = OW·SY·BA·나 뿐 · 거부 ACE 무관 · NO_ACCESS_CONTROL·못 읽는 꼴 = 아님
    $alias = $Me
    if ($Me -eq 'S-1-5-18') { $alias = 'SY' } elseif ($Me -match '^S-1-5-21-.*-500$') { $alias = 'LA' } elseif ($Me -match '^S-1-5-21-.*-501$') { $alias = 'LG' }
    $o = $Sddl.IndexOf('O:'); $d = $Sddl.IndexOf('D:')
    if ($o -lt 0 -or $d -lt 0 -or $o -gt $d) { return $false }
    $g = $Sddl.IndexOf('G:', $o + 2)
    $oe = if ($g -ge 0 -and $g -lt $d) { $g } else { $d }
    $owner = $Sddl.Substring($o + 2, $oe - $o - 2)
    if (-not (($owner -ceq $Me) -or ($owner -ceq $alias) -or ($owner -ceq 'BA') -or ($owner -ceq 'SY'))) { return $false }
    $dacl = $Sddl.Substring($d + 2)
    $s = $dacl.IndexOf('S:'); if ($s -ge 0) { $dacl = $dacl.Substring(0, $s) }
    $fe = $dacl.IndexOf('('); if ($fe -lt 0) { $fe = $dacl.Length }
    if ($dacl.Substring(0, $fe).Contains('NO_ACCESS_CONTROL')) { return $false }
    foreach ($ace in @($dacl.Substring($fe) -split '[()]' | Where-Object { $_ })) {
        $f = $ace.Split(';')
        if ($f.Count -ne 6) { return $false }
        if ($f[0] -ceq 'A') { if (-not (($f[5] -ceq 'OW') -or ($f[5] -ceq 'SY') -or ($f[5] -ceq 'BA') -or ($f[5] -ceq $Me) -or ($f[5] -ceq $alias))) { return $false } }
        elseif ($f[0] -cne 'D') { return $false }
    }
    return $true
}
function Test-CysTxnPathPrivate([string]$Path) {
    # 2판(codex 5): 진입마다 — 갱신 폴더·잠금·소유자 기록이 연결점(reparse·junction)이 아니고 소유자 전용(DACL read-back)인가 · 없음 = 참(우리가 만든다) · 못 읽음 = 아님
    if (-not (Test-Path -LiteralPath $Path)) { return $true }
    try {
        $it = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if ($it.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { return $false }
        if ([System.Environment]::OSVersion.Platform -ne 'Win32NT') { return $true }   # 윈 아닌 곳(맥 pwsh 시험) = 연결점만 본다
        $sddl = (Get-Acl -LiteralPath $Path -ErrorAction Stop).Sddl
        return (Test-CysTxnSddlPrivate $sddl ([System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value))
    } catch { return $false }
}
$CysTxnRenameSource = @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
namespace Jarvis {
public static class TxnRename {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern SafeFileHandle CreateFileW(string name, uint access, uint share, IntPtr sa, uint disp, uint flags, IntPtr tmpl);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool SetFileInformationByHandle(SafeFileHandle h, int cls, IntPtr info, uint size);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool MoveFileExW(string src, string dst, uint flags);
    // 0 = 바꿔치기 됨 · 아니면 마지막 Win32 오류. 순서 = Rust std::fs::rename(윈)과 같다: FileRenameInfoEx(바꾸기 + POSIX 꼴) → MoveFileEx(바꾸기)
    public static int Replace(string src, string dst) {
        int err = 0;
        using (SafeFileHandle h = CreateFileW(src, 0x00010000 | 0x00100000, 7, IntPtr.Zero, 3, 0, IntPtr.Zero)) {
            if (h.IsInvalid) { err = Marshal.GetLastWin32Error(); }
            else {
                byte[] name = System.Text.Encoding.Unicode.GetBytes(dst.StartsWith(@"\\?\") ? dst : @"\\?\" + dst);
                int off = 2 * IntPtr.Size + 4;
                int size = off + name.Length + 2;
                IntPtr buf = Marshal.AllocHGlobal(size);
                try {
                    for (int i = 0; i < size; i++) { Marshal.WriteByte(buf, i, 0); }
                    Marshal.WriteInt32(buf, 0, 0x1 | 0x2);
                    Marshal.WriteInt32(buf, 2 * IntPtr.Size, name.Length);
                    Marshal.Copy(name, 0, IntPtr.Add(buf, off), name.Length);
                    if (SetFileInformationByHandle(h, 22, buf, (uint)size)) { return 0; }
                    err = Marshal.GetLastWin32Error();
                } finally { Marshal.FreeHGlobal(buf); }
            }
        }
        if (MoveFileExW(src, dst, 0x1 | 0x8)) { return 0; }
        int e2 = Marshal.GetLastWin32Error();
        return (e2 != 0) ? e2 : err;
    }
}
}
'@
$script:CysTxnRenameOk = $null
function Rename-CysTxnReplace([string]$Src, [string]$Dst) {
    # 임시 → 제자리 바꿔치기 한 번 — cys write_atomic(std::fs::rename)과 같은 운영체제 길(윈) · 그 함수를 못 붙이는 기계·윈 아닌 곳 = File.Replace/Move
    if ($null -eq $script:CysTxnRenameOk) {
        $script:CysTxnRenameOk = $false
        if ([System.Environment]::OSVersion.Platform -eq 'Win32NT') {
            try {
                if (-not ('Jarvis.TxnRename' -as [type])) { Add-Type -TypeDefinition $CysTxnRenameSource -Language CSharp -ErrorAction Stop }
                $script:CysTxnRenameOk = $true
            } catch { Write-Log ('txn: 바꿔치기 함수를 못 붙임 — File.Replace 로 · ' + $_.Exception.Message) }
        }
    }
    if ($script:CysTxnRenameOk) {
        $e = [Jarvis.TxnRename]::Replace([System.IO.Path]::GetFullPath($Src), [System.IO.Path]::GetFullPath($Dst))
        if ($e -ne 0) { throw ('Win32 ' + $e + ' ' + ([System.ComponentModel.Win32Exception]::new([int]$e)).Message) }
        return
    }
    if (Test-Path -LiteralPath $Dst) { [System.IO.File]::Replace($Src, $Dst, $null) } else { [System.IO.File]::Move($Src, $Dst) }
}
function Write-CysTxnFile([string]$Path, [byte[]]$Bytes) {
    # 원자 쓰기(임시 → 바꿔치기) — 소유자 기록은 cys·설치기 ⓪-a 가 읽는다(찢어진 내용 0)
    #   ⚠File.Replace 는 윈 CI 에서 방금 쓴 기록 위로 3초 내내 실패했다(37548178821 · 37548828686 의 [ⓔ] 3.3초 = 옛 「지우고 옮기기」 폴백이 살림)
    #     ⇒ 바꿔치기 = Rename-CysTxnReplace(cys 와 같은 길) · 100ms 간격 30번(3초)까지 다시 해 본다.
    #   ⛔2판(codex 3): 「지우고 옮기기」 폴백 삭제 — 기록이 없는 창은 정상 위임 자식을 rc 26 으로 만든다 · 끝내 못 바꾸면 throw(부르는 쪽이 잠금을 쥔 채 판단).
    $tmp = $Path + '.u5.' + $PID
    [System.IO.File]::WriteAllBytes($tmp, $Bytes)
    $last = ''
    for ($i = 0; $i -lt 30; $i++) {
        try { Rename-CysTxnReplace $tmp $Path; return } catch { $last = $_.Exception.Message; Start-Sleep -Milliseconds 100 }
    }
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    throw ('바꿔치기 실패(3초): ' + $last)
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
    # 한 번 잡아 본다 → $script:CysTxnState = ok · busy(기다림) · nodir(폴더가 없고 만들 수도 없음 = lock.rs participate 처럼 잠금 없이 진행) ·
    #   nolock(폴더는 있는데 잠금·기록을 못 엶·씀) · unsafe(소유자 전용 아님 / 연결점) — nolock·unsafe 는 다시 해 보지 않고 J-UPD-03 (순서 = lock.rs acquire: 배타 잠금 → 기록)
    $script:CysTxnState = 'nolock'
    $existed = Test-Path -LiteralPath $CysUpdateDir
    if (-not (New-CysTxnDir)) { if (-not $existed) { $script:CysTxnState = 'nodir' }; Write-Log 'txn: 갱신 폴더를 만들 수 없음'; return }
    $lockPath = Join-Path $CysUpdateDir 'txn.lock'
    $ownerPath = Join-Path $CysUpdateDir 'txn.owner.json'
    foreach ($pp in @($CysUpdateDir, $lockPath, $ownerPath)) {
        if (-not (Test-CysTxnPathPrivate $pp)) { $script:CysTxnState = 'unsafe'; Write-Log ('txn: 소유자 전용이 아니거나 연결점 — 끝(2판 codex 5) · ' + (Redact $pp)); return }
    }
    $lk = $null
    try { $lk = [System.IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'ReadWrite') } catch { Write-Log ('txn: 잠금 파일을 열 수 없음(nolock) · ' + $_.Exception.Message); return }
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
    try { Write-CysTxnFile $ownerPath (ConvertTo-CysTxnOwnerJson $o) } catch { $lk.Unlock(0, 1); $lk.Close(); Write-Log ('txn: 소유자 기록을 쓸 수 없음(nolock) · ' + $_.Exception.Message); return }
    # 옛 트랜잭션의 위임 자식·토큰 없는 참가 명령이 아직 일하는 중이면 열지 않는다(소유자 기록을 먼저 쓴 뒤에 본다 · 거절이면 직전 기록 복원)
    $names = @('txn.child.lock') + @(1..4 | ForEach-Object { 'txn.child.lock.' + $_ } | Where-Object { Test-Path -LiteralPath (Join-Path $CysUpdateDir $_) }) + @('txn.part.lock')
    foreach ($n in $names) {
        if (Test-CysTxnFree (Join-Path $CysUpdateDir $n)) { continue }
        $restored = $true
        try { if ($prev) { Write-CysTxnFile $ownerPath $prev } else { Remove-Item -LiteralPath $ownerPath -Force -ErrorAction Stop } } catch { $restored = $false; Write-Log ('txn: 직전 소유자 기록 복원 실패 — 끝(3판 N6 · ' + $_.Exception.Message + ')') }
        $lk.Unlock(0, 1); $lk.Close()
        $script:CysTxnState = $(if ($restored) { 'busy' } else { 'nolock' }); Write-Log ('txn: ' + $script:CysTxnState + ' ' + $n); return
    }
    $script:CysTxnLock = $lk; $script:CysTxnOwner = $o; $script:CysTxnToken = ($id + ':' + $epoch); $script:CysTxnState = 'ok'
}
function Unlock-CysTxn {
    # 놓기 = 묘비(released:true)를 먼저 쓰고 잠금을 푼다(lock.rs 와 같은 순서) · 토큰·env 는 언제나 거둔다 · 쥔 것이 없으면 env 만 지운다
    #   ⛔2판(codex 3): 묘비를 못 쓰면 **잠금을 쥔 채** 둔다 — 「잠금 풀림 + 묘비 없는 옛 기록 + 이 창 생존」 이면 새 러너가 잠금을 잡고 기록을 쓰기 전 창에서
    #     옛 토큰이 새 세대 잠금 아래 받아들여질 수 있다. 쥔 채면 이 창이 끝날 때 OS 가 풀고(그때 옛 토큰의 조상 검증이 깨진다) · 다음 Unlock-CysTxn 이 묘비를 다시 해 본다.
    if ($script:CysTxnLock) {
        $tomb = $false
        try { $script:CysTxnOwner.released = $true; Write-CysTxnFile (Join-Path $CysUpdateDir 'txn.owner.json') (ConvertTo-CysTxnOwnerJson $script:CysTxnOwner); $tomb = $true } catch { Write-Log ('txn: 묘비를 쓰지 못함 — 잠금은 이 창이 끝날 때까지 쥔다(2판 codex 3) · ' + $_.Exception.Message) }
        if ($tomb) {
            try { $script:CysTxnLock.Unlock(0, 1) } catch { }
            try { $script:CysTxnLock.Close() } catch { }
            $script:CysTxnLock = $null
            Write-Log ('txn: released ' + $script:CysTxnOwner.txn_id + ':' + $script:CysTxnOwner.epoch)
        }
    }
    $script:CysTxnToken = ''
    Remove-Item Env:CYS_UPDATE_TXN -ErrorAction SilentlyContinue
    Remove-Item Env:CYS_UPDATE_TXN_DEPTH -ErrorAction SilentlyContinue
}
function Invoke-WithCysTxnEnv([scriptblock]$Body) {
    # 2판(agy1·codex4): 이 블록에서 띄우는 프로세스에만 토큰 env(참가 명령 · 설치기 · 데몬을 띄울 수 있는 cys 호출) · 쥔 것이 없으면 그대로 · 뒤에 지운다
    if (-not $script:CysTxnToken) { return (& $Body) }
    $env:CYS_UPDATE_TXN = $script:CysTxnToken
    try { return (& $Body) } finally { Remove-Item Env:CYS_UPDATE_TXN -ErrorAction SilentlyContinue }
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
    # go · wait · nojudge — 온전한데 끝나지 않았으면 wait · 망가졌으면(cys 가 degraded·corrupt 라고 말함) go(📌18 재설치 길) ·
    #   판정할 cys 가 없으면 nojudge(덮지 않는다 · 2판 codex 6 · 저널이 오래면 Enter-CysTxn 이 J-UPD-03) · cys 호출 시한 20초(3판 N11 · 맥 alarm 20 짝)
    if (-not (Test-Path -LiteralPath (Join-Path $CysUpdateDir 'journal.json')) -and -not (Test-Path -LiteralPath (Join-Path $CysUpdateDir 'journal.prev.json'))) { return 'go' }
    $cands = @((Join-Path $CysUpdateDir 'runner\cys.exe'))
    try { $b = Test-CysBody; if ($b.Body -and $b.Cli) { $cands += [string]$b.Cli } } catch { }
    foreach ($c in $cands) {
        if (-not (Test-Path -LiteralPath $c)) { continue }
        try {
            $out = [string](Invoke-CysCapped $c 'self-update --journal-state --json' 20000)
            if (-not $out) { continue }
            $v = Get-CysTxnJournalWord $out
            if (-not $v) { continue }
            Write-Log ('txn: journal ' + $out + ' (판정 ' + $v + ' · ' + (Redact $c) + ')')
            return $v
        } catch { continue }
    }
    if (Test-CysTxnJournalTerminal) { Write-Log 'txn: 판정할 cys 없음 · 저널 = 종결 상태 — 진행(4판 m2)'; return 'go' }
    Write-Log 'txn: 저널 판정 불가(판정할 cys 없음) — 덮지 않는다(2판 codex 6)'
    return 'nojudge'
}
function Enter-CysTxn {
    # 본문 시작 직후 · 0 = 계속 · 26 = 끝(문구·진단 코드를 찍었다)
    if ($Mode -ne 'full') { return 0 }
    Remove-Item Env:CYS_UPDATE_TXN -ErrorAction SilentlyContinue   # 2판(agy1·codex4): 물려받은 토큰도 프로세스 전체에 두지 않는다
    Remove-Item Env:CYS_UPDATE_TXN_DEPTH -ErrorAction SilentlyContinue
    $n = 0
    while ($true) {
        Lock-CysTxnOnce
        if ($script:CysTxnState -ne 'busy') { break }   # 3판(N1): 다시 해 볼 값어치가 있는 것 = busy(남이 쥠) 하나뿐
        $n++
        if ($n -gt $CysTxnRetryMax) { break }
        if ($n -eq 1) { Say $CysTxnWaitSay }
        Write-Log ('txn: busy — ' + $CysTxnRetrySec + 's 뒤 다시(' + $n + '/' + $CysTxnRetryMax + ')')
        Start-Sleep -Seconds $CysTxnRetrySec
    }
    if ($script:CysTxnState -eq 'nolock') {
        # 4판(m4): 「자리 이상」 판정 전 제자리 재확인(최대 $CysTxnRecheckMax × $CysTxnRecheckSec 초) — 그사이 busy 가 되면 그대로 J-UPD-01(기다림 루프로 되돌아가지 않는다)
        for ($i = 1; $i -le $CysTxnRecheckMax -and $script:CysTxnState -eq 'nolock'; $i++) {
            Write-Log ('txn: nolock — 재확인 ' + $i + '/' + $CysTxnRecheckMax)
            Start-Sleep -Seconds $CysTxnRecheckSec
            Lock-CysTxnOnce
        }
    }
    if ($script:CysTxnState -eq 'nodir') {
        Write-Log 'txn: 갱신 폴더가 없고 만들 수도 없음 — 잠금 없이 진행(lock.rs participate 와 같이 · 3판 N1)'
        return 0
    }
    if ($script:CysTxnState -eq 'busy') {
        Say $CysTxnBusySay
        Write-JCode 'J-UPD-01' '자비스가 새 판으로 바꾸는 중이라 이번에는 아무것도 바꾸지 않았습니다'
        Set-NextStepRerun '5분 뒤 아래 「다시 하시는 법」대로 다시 실행해 주십시오.'
        return 26
    }
    if ($script:CysTxnState -ne 'ok') { Write-CysTxnOdd $script:CysTxnState; return 26 }
    Write-Log ('txn: held ' + $script:CysTxnToken + ' (owner pid ' + $PID + ')')
    $v = Get-CysTxnJournalVerdict
    if ($v -eq 'go') { return 0 }
    Unlock-CysTxn
    if (($v -eq 'nojudge') -and (Test-CysTxnJournalStale)) { Write-CysTxnOdd 'nojudge'; return 26 }
    Say $CysTxnRecoverSay
    Write-JCode 'J-UPD-02' '지난번 새 판 바꾸기의 마무리를 기다립니다'
    Set-NextStepRerun '5분 뒤 아래 「다시 하시는 법」대로 다시 실행해 주십시오.'
    return 26
}
function Test-CysTxnJournalTerminal {
    # 4판(Opus 3R m2) · 5판(Opus 4R n1): 판정할 cys 가 없을 때만 — 두 슬롯(journal.json · journal.prev.json) 중 generation 큰 쪽(= cys 가 최신으로 읽는 쪽 ·
    #   journal.rs commit_next 가 번갈아 쓴다)의 state 가 종결(cys is_terminal 과 같은 칸)이면 참 · 한쪽만 읽히면 그쪽 · 둘 다 못 읽음 = 거짓(종전 갈래)
    $best = $null
    foreach ($n in @('journal.json', 'journal.prev.json')) {
        try { $j = [System.IO.File]::ReadAllText((Join-Path $CysUpdateDir $n)) | ConvertFrom-Json } catch { continue }
        if ($null -eq $j -or $null -eq $j.state) { continue }
        $g = [long]0; if ($null -ne $j.generation) { $g = [long]$j.generation }
        if ($null -eq $best -or $g -gt $best.g) { $best = [pscustomobject]@{ g = $g; s = [string]$j.state } }
    }
    if ($null -eq $best) { return $false }
    return ($CysTxnTerminalStates -contains $best.s)
}
function Test-CysTxnJournalStale {
    # 저널(journal.json · journal.prev.json 중 새 것)이 $CysTxnJournalStaleMin 분보다 오래됐는가 — 복구기가 도는 중이면 저널은 금방 바뀐다
    $ts = @(@('journal.json', 'journal.prev.json') | ForEach-Object { Join-Path $CysUpdateDir $_ } | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { (Get-Item -LiteralPath $_).LastWriteTimeUtc })
    if ($ts.Count -eq 0) { return $false }
    return ((([DateTime]::UtcNow) - ($ts | Sort-Object -Descending | Select-Object -First 1)).TotalMinutes -gt $CysTxnJournalStaleMin)
}
function Write-CysTxnOdd([string]$Why) {
    # J-UPD-03 「잠금 자리 이상」 — 기다려도 풀리지 않는 원인(unsafe · nolock · refused · nojudge) · 원인별 문구 1줄 · 원격 해결은 열린다(J-UPD-01·02 와 다르다)
    Say $CysTxnOddSay[$Why]
    Write-Log ('txn: J-UPD-03 ' + $Why)
    Write-JCode 'J-UPD-03' ('자비스의 새 판 바꾸기 자리가 이상해 멈췄습니다(' + $Why + ')')
}
function Stop-CysTxnRefused([string]$What) {
    # 위임이 거부됐다(cys rc 26 · 설치기 exit 6) — 설계 §3-2 「못 잡으면 문구로 끝」 · 잠금은 본문 finally 가 놓는다
    #   3판(N1): 위임 거부는 기계 결정적(시작 시각·기록 불일치)이라 기다려도 안 풀린다 = J-UPD-03(원격 해결 열림)
    Write-Log ('txn: ' + $What + ' 위임 거부 — 끝(2판 codex 1 · 무잠금 재실행 0)')
    Write-CysTxnOdd 'refused'
    exit 26
}
function Invoke-CysTxnLogged($what, $cli, $cmdArgs) {
    # Invoke-Logged 와 같되 잠금을 쥐었으면 --txn 위임(env 는 이 호출에만) · 위임 거부(rc 26)면 J-UPD-03 + 끝(2판 codex 1 · 3판 N1)
    if ($script:CysTxnToken) {
        $rc = Invoke-WithCysTxnEnv { Invoke-Logged $what $cli (@($cmdArgs) + @('--txn', $script:CysTxnToken)) }
        if ($rc -ne 26) { return $rc }
        Stop-CysTxnRefused $what   # 2판(codex 1): 위임 거부 = 문구 1줄 + 끝(잠금 없이 다시 하지 않는다)
    }
    return (Invoke-Logged $what $cli $cmdArgs)
}
function Get-CysAssetsWord([string]$Json) {
    # 순수 — `cys self-update --journal-state --json` 의 n7_installer → $true · $false · $null(그 칸 없음 = 옛 판 · 못 읽음)
    try { $j = $Json | ConvertFrom-Json } catch { return $null }
    if ($null -eq $j -or $null -eq $j.n7_installer) { return $null }
    if ($j.seq -eq 0) { return $null }   # 미발행 빌드(release_seq 0) = 놓을 자산이 없다(보관소 행 없음) — 다시 받지 않는다
    return [bool]$j.n7_installer
}
function Test-CysRollbackAssetsPresent([string]$Dir) {
    # 2판(codex7·agy2) · 3판(Opus 2R N10): 깔린 판의 롤백 자산이 쓸 만한가 = **cys 의 판정**(check::installer_assets_ok 재검증 · 러너 N7 과 같은 값)을 쓴다 —
    #   없으면 [5/10] 이 같은 판이어도 핀 설치기를 받아 두고 [6/10] 건너뜀 갈래가 Save-CysRollbackAssets 를 다시 부른다(러너 보관소 받기 = U2 후속 · master#c72a59df).
    #   판정할 cys 가 없거나 그 칸이 없는 옛 판(1.1.7 이하 = 자동 갱신 없음) = 참(챙길 것이 없다) · 시한 20초
    $cli = Join-Path $Dir 'cys.exe'
    if (-not (Test-Path -LiteralPath $cli)) { return $true }
    $w = Get-CysAssetsWord ([string](Invoke-CysCapped $cli 'self-update --journal-state --assets --json' 20000))   # 4판 m3: 재검증은 --assets 를 줄 때만
    Write-Log ('rollback assets: n7_installer=' + $w)
    return ($w -ne $false)
}
function Receive-CysSetupForAssets([string]$Dst) {
    # 3판(Opus 2R N2): 같은 판 + 롤백 자산 없음 = 설치기만 받는 갈래 — 한 번만 해 보고, 못 받으면(404·410·망) 기록·화면 1줄 뒤 설치는 이어 간다
    #   (설계 결정 4 「못 챙기면 설치 계속」 · J-DL 막힘·연결 기다림 0) · 0 = 언제나 계속
    if ($Mode -eq 'dry') { Say "[5/10] (dry-run) 되돌림 파일용 설치 파일을 받을 것입니다. 받을 곳 = $CysDownloadUrl"; return 0 }
    $tmp = $Dst + '.u5part'
    try {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dst) | Out-Null
        if ((Test-Path -LiteralPath $Dst) -and ((Get-CysFileSha256 $Dst) -eq $CysWinSha256)) { return 0 }
        $pp = $ProgressPreference; $ProgressPreference = 'SilentlyContinue'
        try { Invoke-WebRequest -Uri $CysDownloadUrl -OutFile $tmp -UseBasicParsing -TimeoutSec $CysAssetsDlTimeoutSec -ErrorAction Stop } finally { $ProgressPreference = $pp }   # 4판 M1: 상한 = 본 받기와 같게(기본 무한 금지)
        if (((Get-Item -LiteralPath $tmp).Length -ne $CysWinBytes) -or ((Get-CysFileSha256 $tmp) -ne $CysWinSha256)) { throw '크기·지문 불일치' }
        Move-Item -LiteralPath $tmp -Destination $Dst -Force
        [void](Clear-WebMark $Dst 'cys setup')
        Say '[5/10] 받았습니다 (되돌림 파일용 · 크기·지문 확인).'
    } catch {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        Say '[5/10] 자동 갱신을 위한 준비 파일을 이번에는 받지 못했습니다 — 설치는 계속됩니다(이 설치 한 줄을 다시 실행하시면 다시 받아 봅니다).'
        Write-Log ('rollback assets: 설치기 받기 실패 — 자동 갱신 hold(N7) · [6/10] 건너뜀으로 계속(3판 N2 · 4판 M1·m1) · ' + $_.Exception.Message)
        Send-Progress '5/10' 'info' $null 'rollback-assets:dl-fail' $null
    }
    return 0
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
    Say '     그 파일이 없는 동안 자비스의 자동 새 판 바꾸기는 멈춰 있습니다 — 이 설치 한 줄을 나중에 다시 실행하시면 다시 챙겨 봅니다.'   # 3판: 「챙긴다」 약속 삭제 · 4판(m8): 개발 일정 약속 괄호 삭제(공개 문구 규칙)
    Write-Log ('rollback assets: 못 챙김 rc=' + $rc + ' — 자동 갱신 hold(N7 설치판 자산 없음) · 설치 링크 재실행 = 다시 챙김(2판 codex7 · master#c72a59df ⓑ)')
    Send-Progress '6/10' 'info' $null ('rollback-assets:fail rc=' + $rc) $null
    return ('fail-' + $rc)
}

