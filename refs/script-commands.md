# 脚本一键执行（AI 自动调用）

使用 Python 运行自动化脚本：

```bash
# ── Python 版（首选） ──

# 增量编译（默认，只编译当前文档所属项目中修改过的文件）
python scripts/keil_build.py --project "RU3.uvprojx"

# 全编译（首次调试或宏变化时使用）
python scripts/keil_build.py --project "RU3.uvprojx" --rebuild

# 编译+下载（仅在用户明确确认 full 模式后使用；自动先增量编译，成功后下载）
python scripts/build_and_flash.py

# 串口抓日志
python scripts/serial_monitor.py --duration 15 --save .copilot/logs/output.log
```

Keil 的完整编译输出固定保存为工作区根目录下的 `build_log.txt`。日志位置仅由
`--config-dir` 指定的工作区（或配置中的 `workspace`）决定，不会扫描工程子目录中的
`.copilot`。需要自定义位置时可显式传入 `--log <路径>`。

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
