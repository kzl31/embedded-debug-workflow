<#
.SYNOPSIS
    Embedded debug config reader (PowerShell)
.DESCRIPTION
    Read/write shuju/config.json
.PARAMETER Validate
    Check config integrity
.PARAMETER Get
    Get field value (keil/serial/projects/debugger)
.PARAMETER Path
    Custom config path
#>

param(
    [switch]$Validate,
    [string]$Get = "",
    [string]$Path = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillDir  = Join-Path $scriptDir ".."
function Get-Cfg { if ($Path) { $Path } else { Join-Path $skillDir "data\config.json" } }

function Load-Cfg {
    $p = Get-Cfg
    if (-not (Test-Path $p)) { return @{} }
    try {
        $c = Get-Content $p -Raw -Encoding UTF8
        if (-not $c) { return @{} }
        return ($c | ConvertFrom-Json -ErrorAction Stop)
    } catch { return @{} }
}

function Test-Cfg {
    param($C)
    if (-not $C.keil -or -not $C.keil.uv4_path) { return $false }
    if (-not $C.projects -or @($C.projects).Count -eq 0) { return $false }
    if (-not $C.serial -or -not $C.serial.port) { return $false }
    return $true
}

function Main {
    if ($Validate) {
        $d = Load-Cfg
        if (Test-Cfg $d) { Write-Host "OK" } else { Write-Host "FAIL" }
        return
    }
    if ($Get) {
        $d = Load-Cfg
        switch ($Get.ToLower()) {
            "keil"     { Write-Host $d.keil.uv4_path }
            "serial"   { Write-Host "$($d.serial.port),$($d.serial.baud)" }
            "projects" { foreach ($p in $d.projects) { Write-Host "$($p.name)|$($p.dir)|$($p.file)" } }
            "debugger" { Write-Host "$($d.debugger.type),$($d.debugger.sn)" }
        }
        return
    }
    $d = Load-Cfg
    if ($d.PSObject.Properties.Count -gt 0) { $d | ConvertTo-Json -Depth 10 }
    else { Write-Host "no config"; exit 1 }
}

Main
