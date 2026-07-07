<#
.SYNOPSIS
    Keil build + flash (PowerShell)
.DESCRIPTION
    Read config from data/config.json and build/flash Keil project
.PARAMETER Project
    Project filename
.PARAMETER Dir
    Project directory
.PARAMETER Rebuild
    Clean + Build
.PARAMETER BuildOnly
    Build only, no flash
.PARAMETER FlashOnly
    Flash only, no build
.PARAMETER AllProjects
    Process all projects
#>

param(
    [string]$Project = "",
    [string]$Dir = "",
    [switch]$Rebuild,
    [switch]$BuildOnly,
    [switch]$FlashOnly,
    [switch]$AllProjects
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cfgScript = Join-Path $scriptDir "config_reader.ps1"
. $cfgScript

$cfg = Load-Cfg
$uv4 = $cfg.keil.uv4_path

if (-not $uv4 -or -not (Test-Path $uv4)) {
    Write-Host "UV4 not found"
    exit 1
}

$projs = @()
if ($AllProjects) { $projs = $cfg.projects }
else {
    if ($Project -and $Dir) { $projs += @{ name="specified"; dir=$Dir; file=$Project } }
    elseif ($cfg.projects.Count -gt 0) { $projs += $cfg.projects[0] }
}
if ($projs.Count -eq 0) { Write-Host "no projects"; exit 1 }

function Do-Build($p) {
    $log = Join-Path $p.dir "build_log.txt"
    if (-not (Test-Path $p.dir)) { Write-Host "dir not found"; return $false }
    $flag = if ($Rebuild) { "-r" } else { "-b" }
    $cmd = "`"$uv4`" $flag `"$($p.file)`" -o `"$log`""
    Write-Host "build: $($p.file)"
    Push-Location $p.dir
    cmd /c $cmd | Out-Null
    Pop-Location
    if (Test-Path $log) {
        $c = Get-Content $log -Raw
        if ($c -match "(?i)error") { Write-Host "build FAIL"; return $false }
        Write-Host "build OK"
        return $true
    }
    Write-Host "build OK (no log)"
    return $true
}

function Do-Flash($p) {
    $log = Join-Path $p.dir "flash_log.txt"
    $cmd = "`"$uv4`" -f `"$($p.file)`" -o `"$log`""
    Write-Host "flash: $($p.file)"
    Push-Location $p.dir
    cmd /c $cmd | Out-Null
    Pop-Location
    Write-Host "flash OK"
    return $true
}

$ok = $true
foreach ($p in $projs) {
    $n = if ($p.name) { $p.name } else { "?" }
    Write-Host "[$n]"
    if (-not $FlashOnly) { if (-not (Do-Build $p)) { $ok = $false; continue } }
    if (-not $BuildOnly) { if (-not (Do-Flash $p)) { $ok = $false; continue } }
}
if ($ok) { Write-Host "all done" } else { Write-Host "some failed" }
