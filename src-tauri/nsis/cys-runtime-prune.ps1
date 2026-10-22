# cys-runtime-prune.ps1 - stale dist-info cleanup for src-tauri/nsis-hooks.nsh POSTINSTALL (1.1.11).
#
# Shipped verbatim into the installer ($PLUGINSDIR) and run on the success branch as
#   powershell -NoProfile -ExecutionPolicy Bypass -File cys-runtime-prune.ps1 <install root>
#
# Why: the installer extracts runtime\ over the previous one file by file and never empties it, so a
# bundled package whose version changed leaves its old <name>-<old>.dist-info folder behind
# (2026-10-22: pip-26.2.2.dist-info next to the shipped pip-26.2.1.dist-info -> runtime-seal "added").
#
# What it removes - ONLY this, nothing else:
#   a folder <parent>\<name>-<ver>.dist-info under runtime\ that is NOT in runtime-manifest.json while
#   the manifest ships a dist-info of the SAME distribution name in the SAME parent folder
#   (= an older/newer version of a package we ship). Names compare like pip does: case-insensitive,
#   runs of - _ . are one separator.
# What it never touches: package code folders, dist-info of packages we do not ship (a user's own
# pip install stays as it is - the seal reports it), a folder that is or contains a reparse point
# (junction/symlink - a recursive delete through one would reach outside), anything when the manifest
# is missing or unreadable.
#
# The manifest is scanned as text (Windows PowerShell 5.1 ConvertFrom-Json refuses inputs over 2 MB);
# a stray match can only ADD a name to the shipped set, which makes the prune remove less, never more.
# Output: one summary line (logged by nsExec::ExecToLog). Exit 0 always except bad arguments (2) -
# the installer result does not depend on it; leftovers stay visible to the seal.
# This file must stay pure ASCII: Windows PowerShell 5.1 reads a BOM-less script in the ANSI code page.
param([string]$Root)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrEmpty($Root)) { Write-Output 'cys-runtime-prune: no install root given'; exit 2 }

function Get-DistKey([string]$DirName) {
  # "<name>-<version>.dist-info" -> normalized <name>
  $stem = $DirName.Substring(0, $DirName.Length - '.dist-info'.Length)
  # split at the LAST '-': a version never holds '-', a non-normalized name may (python-dateutil vs python-jose)
  $i = $stem.LastIndexOf('-')
  if ($i -le 0) { return $null }
  return ([regex]::Replace($stem.Substring(0, $i), '[-_.]+', '_')).ToLowerInvariant()
}

function Test-HasReparse([IO.DirectoryInfo]$Dir) {
  # own walk, never through a link (5.1 Get-ChildItem -Recurse / Remove-Item -Recurse may follow junctions)
  if ($Dir.Attributes -band [IO.FileAttributes]::ReparsePoint) { return $true }
  foreach ($e in $Dir.GetFileSystemInfos()) {
    if ($e.Attributes -band [IO.FileAttributes]::ReparsePoint) { return $true }
    if ($e -is [IO.DirectoryInfo] -and (Test-HasReparse $e)) { return $true }
  }
  return $false
}

$removed = 0; $failed = 0; $kept = 0
try {
  $rt = Join-Path $Root 'runtime'
  $man = @((Join-Path $Root 'runtime-manifest.json'), (Join-Path $Root 'resources\runtime-manifest.json')) |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
  if (-not $man -or -not (Test-Path -LiteralPath $rt -PathType Container)) {
    Write-Output 'cys-runtime-prune: skipped (no runtime-manifest.json or no runtime folder)'
    exit 0
  }
  $text = [IO.File]::ReadAllText($man)
  # shipped[parent lowercased] = @{ path = parent as written ; keys = dist names ; dirs = dist-info folder names }
  $shipped = @{}
  foreach ($m in [regex]::Matches($text, '"((?:[^"/\\]+/)*)([^"/\\]+\.dist-info)/')) {
    $parent = $m.Groups[1].Value
    $dir = $m.Groups[2].Value
    $key = Get-DistKey $dir
    if (-not $key) { continue }
    $pk = $parent.ToLowerInvariant()
    if (-not $shipped.ContainsKey($pk)) { $shipped[$pk] = @{ path = $parent; keys = @{}; dirs = @{} } }
    $shipped[$pk].keys[$key] = $true
    $shipped[$pk].dirs[$dir.ToLowerInvariant()] = $true
  }
  foreach ($pk in $shipped.Keys) {
    $s = $shipped[$pk]
    $pdir = Join-Path $rt ($s.path.TrimEnd('/') -replace '/', [IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $pdir -PathType Container)) { continue }
    foreach ($d in @(Get-ChildItem -LiteralPath $pdir -Directory -Force)) {
      if (-not $d.Name.EndsWith('.dist-info', [StringComparison]::OrdinalIgnoreCase)) { continue }
      if ($s.dirs.ContainsKey($d.Name.ToLowerInvariant())) { continue }
      $key = Get-DistKey $d.Name
      if (-not $key -or -not $s.keys.ContainsKey($key)) { $kept++; continue }
      try {
        if (Test-HasReparse $d) { $kept++; continue }
        Remove-Item -LiteralPath $d.FullName -Recurse -Force
        $removed++
        Write-Output ('cys-runtime-prune: removed ' + $s.path + $d.Name)
      } catch { $failed++ }
    }
  }
} catch {
  Write-Output ('cys-runtime-prune: stopped (' + $_.Exception.Message + ')')
}
Write-Output ('cys-runtime-prune: stale-dist-info removed=' + $removed + ' failed=' + $failed + ' kept-unshipped=' + $kept)
exit 0
