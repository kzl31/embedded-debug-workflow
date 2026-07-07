<#
.SYNOPSIS
    Serial monitor (PowerShell)
.DESCRIPTION
    Monitor serial port, log to file, wait for keyword
.PARAMETER Port
    COM port
.PARAMETER Baud
    Baud rate
.PARAMETER Duration
    Monitor duration in seconds
.PARAMETER Continuous
    Run until Ctrl+C
.PARAMETER Save
    Save log to file
.PARAMETER Wait
    Wait for keyword then stop
#>

param(
    [string]$Port = "",
    [int]$Baud = 0,
    [float]$Duration = 10.0,
    [switch]$Continuous,
    [string]$Save = "",
    [string]$Wait = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cfgScript = Join-Path $scriptDir "config_reader.ps1"
. $cfgScript

$cfg = Load-Cfg
if (-not $Port) { $Port = $cfg.serial.port }
if ($Baud -eq 0) { $Baud = $cfg.serial.baud }

Write-Host "monitor $Port @ $Baud"

try {
    $sp = New-Object System.IO.Ports.SerialPort $Port, $Baud, None, 8, One
    $sp.ReadTimeout = 500
    $sp.Open()
} catch { Write-Host "open fail: $_"; exit 1 }

$lines = @()
$start = Get-Date

try {
    while ($true) {
        if (-not $Continuous) {
            $elapsed = (Get-Date) - $start
            if ($elapsed.TotalSeconds -ge $Duration) { break }
        }
        try { $line = $sp.ReadLine() } catch { continue }
        $ts = Get-Date -Format "HH:mm:ss.fff"
        $log = "[$ts] $line"
        Write-Host $log
        $lines += $log
        if ($Wait -and $line -match [regex]::Escape($Wait)) {
            Write-Host "keyword found: $Wait"
            break
        }
    }
} finally { if ($sp.IsOpen) { $sp.Close() } }

$sec = ((Get-Date) - $start).TotalSeconds
Write-Host "done: $($lines.Count) lines, $([math]::Round($sec,1))s"

if ($Save -and $lines.Count -gt 0) {
    $d = Split-Path $Save -Parent
    if ($d -and -not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    $lines -join "`r`n" | Out-File $Save -Encoding UTF8
    Write-Host "saved: $Save"
}
