<#
.SYNOPSIS
    Serial read once (PowerShell)
.DESCRIPTION
    Quick serial read, fallback for serial_read.py
.PARAMETER Port
    COM port
.PARAMETER Baud
    Baud rate
.PARAMETER Timeout
    Read timeout in seconds
#>

param(
    [string]$Port = "",
    [int]$Baud = 0,
    [float]$Timeout = 3.0
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cfgScript = Join-Path $scriptDir "config_reader.ps1"
. $cfgScript

$cfg = Load-Cfg
if (-not $Port) { $Port = $cfg.serial.port }
if ($Baud -eq 0) { $Baud = $cfg.serial.baud }

Write-Host "read $Port @ $Baud"

try {
    $sp = New-Object System.IO.Ports.SerialPort $Port, $Baud, None, 8, One
    $sp.ReadTimeout = [int]($Timeout * 1000)
    $sp.Open()
} catch { Write-Host "open fail: $_"; exit 1 }

Start-Sleep -Milliseconds 500
try { $raw = $sp.ReadExisting() } catch { $raw = "" }
finally { if ($sp.IsOpen) { $sp.Close() } }

$lines = @($raw -split "`r`n" | Where-Object { $_ -ne "" })
Write-Host "got $($lines.Count) lines, $($raw.Length) chars"
if ($raw) { Write-Host $raw }
