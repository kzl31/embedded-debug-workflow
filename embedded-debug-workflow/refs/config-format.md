# 配置文件格式

配置文件路径：`{工作区第一级目录}/.copilot/embedded-debug-config.json`

> 多工程共享同一工作区时共用一份配置，统一放在工作区第一级的 `.copilot/` 下（不做向上查找）。
> 配置文件为 JSON 格式（不使用空格/竖线对齐的文本表，避免歧义）。每个工程独立携带自己的串口与下载器，从而建立「工程文件路径 ↔ 串口 ↔ 下载器」的一一对应关系。

```json
{
  "_generated": "2026-07-08 23:44:00",
  "keil": { "uv4_path": "C:\\Keil_v5\\UV4\\UV4.exe" },
  "projects": [
    {
      "name": "RU3主机",
      "dir": "e:\\proj\\MDK-ARM",
      "file": "RU3.uvprojx",
      "serial": { "port": "COM19", "baud": 256000, "data_bits": 8, "stop_bits": 1, "parity": "None" },
      "debugger": { "type": "JLink", "com": "COM9" }
    },
    {
      "name": "RU2主机",
      "dir": "e:\\proj\\RU2\\MDK-ARM",
      "file": "RU2.uvprojx",
      "serial": { "port": "COM20", "baud": 256000, "data_bits": 8, "stop_bits": 1, "parity": "None" },
      "debugger": { "type": "JLink", "com": "COM10" }
    }
  ]
}
```

> `uv4_path` 为固定值 `C:\Keil_v5\UV4\UV4.exe`，不纳入用户采集项，由 `--init` 自动填入。
> 下载器以串口号（`com`）标识，而非序列号。

串口号变更是高频操作，无需重跑 `--init`，直接用 `--set-port` 快捷修改（多工程用 `--project-index` 指定下标）：

```bash
# 快速改第 0 个工程的串口
python scripts/config_reader.py --set-port COM20
# 改第 1 个工程的串口
python scripts/config_reader.py --set-port COM21 --project-index 1
```
