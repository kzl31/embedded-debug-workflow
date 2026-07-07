# 脚本一键执行（AI 自动调用）

优先使用 Python；若环境无 Python，自动降级为 PowerShell：

```bash
# ── Python 版（首选） ──

# 增量编译（默认，只编译修改过的文件）
python scripts/keil_build.py --project "RU3.uvprojx"

# 全编译（首次调试或宏变化时使用）
python scripts/keil_build.py --project "RU3.uvprojx" --rebuild

# 编译+下载（自动先增量编译，成功后下载）
python scripts/build_and_flash.py

# 串口抓日志
python scripts/serial_monitor.py --duration 15 --save logs/output.log


# ── PowerShell 版（备用） ──

# 编译+下载
powershell -File scripts/build_and_flash.ps1

# 所有工程批量处理
powershell -File scripts/build_and_flash.ps1 -AllProjects

# 串口监听
powershell -File scripts/serial_monitor.ps1 -Duration 15
```

## 脚本索引

### Python 版（首选）

| 脚本 | 用途 | 依赖 |
|------|------|------|
| `scripts/config_reader.py` | 读取/写入配置（支持 `--init` / `--set-port` / `--set-baud`） | 无 |
| `scripts/keil_build.py` | Keil 编译（单工程） | 无 |
| `scripts/keil_flash.py` | Keil 下载固件 | 无 |
| `scripts/build_and_flash.py` | 一键编译+下载 | 无 |
| `scripts/serial_read.py` | 串口单次读取 | pyserial |
| `scripts/serial_monitor.py` | 串口持续监听 | pyserial |
| `scripts/batch_build.py` | 多工程批量编译下载 | 无 |

### PowerShell 版（备用）

| 脚本 | 用途 | 对应 Python 版 |
|------|------|----------------|
| `scripts/config_reader.ps1` | 读取/写入配置 | config_reader.py |
| `scripts/build_and_flash.ps1` | 编译+下载（支持 -AllProjects） | build_and_flash.py |
| `scripts/serial_read.ps1` | 串口单次读取 | serial_read.py |
| `scripts/serial_monitor.ps1` | 串口持续监听 | serial_monitor.py |
