# 编译与下载

## 编译

使用 Keil UV4 命令行编译工程：

```powershell
Push-Location "<工程目录>"
cmd /c "`"C:\Keil_v5\UV4\UV4.exe`" -b <工程文件.uvprojx> -o build_log.txt"
Pop-Location
```

### 查看编译错误

```powershell
Get-Content "build_log.txt" | Select-String "error" -Context 1,0
```

## 下载

```powershell
Push-Location "<工程目录>"
cmd /c "`"C:\Keil_v5\UV4\UV4.exe`" -f <工程文件.uvprojx> -o flash_log.txt"
Pop-Location
```

## 一步编译+下载

```powershell
Push-Location "<工程目录>"
cmd /c "`"C:\Keil_v5\UV4\UV4.exe`" -b <工程文件.uvprojx> -o build_log.txt && `"C:\Keil_v5\UV4\UV4.exe`" -f <工程文件.uvprojx> -o flash_log.txt"
Pop-Location
```

## 批量编译下载多工程

```mermaid
sequenceDiagram
    participant PC as PC
    participant JL1 as J-Link A(RU2)
    participant JL2 as J-Link B(RU3)
    Note over PC: 确认: 下载器A→RU2, 下载器B→RU3
    PC->>JL1: 编译 RU2
    PC->>JL1: 下载 RU2
    PC->>JL2: 编译 RU3
    PC->>JL2: 下载 RU3
    Note over PC: 串口监听验证
```

批量操作也可使用 `scripts/batch_builder.py` 脚本自动完成。
