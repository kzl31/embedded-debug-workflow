# 读取串口日志

## 单次读取

```powershell
$port = New-Object System.IO.Ports.SerialPort <串口号>, <波特率>, None, 8, One
$port.ReadTimeout = 3000
$port.Open()
Start-Sleep -Milliseconds 800
$data = $port.ReadExisting()
Write-Host $data
$port.Close()
```

## 持续监听（推荐调试时使用）

```powershell
$port = New-Object System.IO.Ports.SerialPort <串口号>, <波特率>, None, 8, One
$port.Open()
$logFile = "debug_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

while ($port.IsOpen) {
    $line = $port.ReadLine()
    $ts = Get-Date -Format "HH:mm:ss.fff"
    "$ts $line" | Tee-Object -FilePath $logFile
}
```

> **提示**：持续监听时，在另一个终端窗口执行编译下载操作。

## 使用脚本

也可使用 `scripts/serial_monitor.py` 脚本完成单次读取或持续监听。
