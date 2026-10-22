# cys-samebytes.ps1 - content oracle helper for src-tauri/nsis-hooks.nsh CYS_PLACE step 4-b (1.1.11).
#
# Shipped verbatim into the installer ($PLUGINSDIR) by NSIS_HOOK_POSTINSTALL and run as
#   powershell -NoProfile -ExecutionPolicy Bypass -File cys-samebytes.ps1 <canonical> <new>
#
# Exit code contract (the hook reads only "0"; everything else means "replace"):
#   0 = same bytes (size + SHA-256 equal)
#   1 = different bytes
#   2 = could not decide (missing file, read failure, bad arguments) - fail-closed: the hook replaces
#
# Both files are opened with FileShare ReadWrite+Delete so a running image (cys.exe / cysd.exe held by
# the loader) is still readable. This file must stay pure ASCII: Windows PowerShell 5.1 reads a BOM-less
# script in the ANSI code page.
param([string]$A, [string]$B)
$ErrorActionPreference = 'Stop'

function Get-Sha256Hex([string]$Path) {
  # ConstrainedLanguage (AppLocker/WDAC; $PLUGINSDIR is under %TEMP%) blocks the .NET static calls below, which
  # made every call "could not decide" = replace, even for identical bytes. Get-FileHash is an allowed cmdlet there.
  # Both files of one call go through the same branch, so the two hash strings stay comparable.
  if ($ExecutionContext.SessionState.LanguageMode -ne 'FullLanguage') {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
  }
  $share = [IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete
  $s = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, $share)
  try {
    $h = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($h.ComputeHash($s)) } finally { $h.Dispose() }
  } finally { $s.Dispose() }
}

try {
  if ([string]::IsNullOrEmpty($A) -or [string]::IsNullOrEmpty($B)) { exit 2 }
  $la = (Get-Item -LiteralPath $A).Length
  $lb = (Get-Item -LiteralPath $B).Length
  if ($la -ne $lb) { exit 1 }
  if ((Get-Sha256Hex $A) -eq (Get-Sha256Hex $B)) { exit 0 }
  exit 1
} catch {
  exit 2
}
