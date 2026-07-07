# 配置文件格式

配置文件路径：`{项目根目录}/embedded-debug-config.json`

```json
{
  "_generated": "2026-07-06 15:30:00",
  "keil": { "uv4_path": "C:\\Keil_v5\\UV4\\UV4.exe" },
  "projects": [
    { "name": "RU3主机", "dir": "e:\\proj\\MDK-ARM", "file": "RU3.uvprojx" }
  ],
  "serial": { "port": "COM19", "baud": 256000, "data_bits": 8, "stop_bits": 1, "parity": "None" },
  "debugger": { "type": "JLink", "sn": "123456" },
  "device": { "role": "RU3主机", "comm_link": "RU3 USART3 ↔ RU2 USART3" }
}
```

> `uv4_path` 为固定值 `C:\Keil_v5\UV4\UV4.exe`，不纳入用户采集项，由 `--init` 自动填入。
> 串口号变更是高频操作，无需重跑 `--init`，直接用 `--set-port` 快捷修改：
>
> ```bash
> # 快速改串口（不改其他配置）
> python scripts/config_reader.py --set-port COM20 --path <项目目录>
>
> # 快速改波特率
> python scripts/config_reader.py --set-baud 115200 --path <项目目录>
> ```
