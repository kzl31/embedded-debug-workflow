# 配置文件格式

配置文件路径由 `scripts/path_config.py` 根据 `scripts/skill-config.json` 的 `paths` 生成。

> 多工程共享同一工作区时共用一份配置，统一放在工作区 Skill 专属数据目录下
> （不做向上查找）。
> 工作区根目录与 Skill 仓库目录、Keil 工程目录是三个不同概念。流程引擎虽然沿用
> `--project` 参数名，但参数值必须是当前 VS Code 工作区根目录；不得因为 Skill 仓库是
> 工作区中的一个子目录，就将该子目录作为运行目录。各 Keil 工程目录只记录在
> `projects[*].dir` 中，由后续脚本按目标工程读取。
> 配置、流程状态、报告和日志均位于集中配置定义的工作区 Skill 专属数据目录。每个工程的日志使用独立名称：
> `build_log_p<下标>_<项目名>.txt`、`flash_log_p<下标>_<项目名>.txt`、
> `debug_log_p<下标>_<项目名>.txt` 和 `verify_log_p<下标>_<项目名>.txt`。
> 配置文件为 JSON 格式（不使用空格/竖线对齐的文本表，避免歧义）。每个工程独立携带自己的串口与下载器，从而建立「工程文件路径 ↔ 串口 ↔ 下载器」的一一对应关系。

```json
{
  "_generated": "2026-07-08 23:44:00",
  "ai_progress_display": true,
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

`ai_progress_display` 控制 AI 是否向用户展示流程进度：

- `true`（默认）：每个实际到达的流程步骤至少展示一次，引擎提供可直接输出的
  紧凑步骤信息。AI 在下一次调用引擎前，根据上一次步骤、简要结果和本次调用目的生成独立
  进度消息；引擎调用后不重复展示，且不增加第二次引擎调用。
- `false`：引擎不返回 `user_display`，AI 不输出流程进度；正常提问、人工暂停和最终结果不受影响。
- 该字段必须是 JSON 布尔值 `true` / `false`，不能写成字符串。

> 下载器以串口号（`com`）标识，而非序列号。
> `/kzl 初始化` 默认使用当前 VS Code 工作区根目录，并递归扫描 `.uvprojx` / `.uvproj`；
> 按实际发现的工程生成 `name`、`dir`、`file`，不询问文件路径。
> 用户可自行增加、删除或重排 `projects` 元素；后续始终以数组实际内容为准，`project_count`
> 仅记录扫描数量，不参与运行时判断。下一阶段必须对每个项目分别询问执行模式，不设置
> 默认值或推荐值。四个选项为：`none`（不编译不下载）、`compile_only`（仅编译）、
> `compile_flash`（编译下载但不监听）、`full`（编译下载监听）。允许例如项目 0 选择
> `full`、项目 1 选择 `none`、项目 2 选择 `compile_flash`。
> `skipBuild`、`skipFlash`、`observeExistingSerial`、`finishRequested` 是由 AI 根据用户意图和
> 当前证据自动设置的本次运行参数，禁止逐项询问用户，也不写入工程配置。开始时需要先观察
> 板上已有固件串口，则跳过编译下载并启用 `observeExistingSerial`；用户要求结束流程时启用
> `finishRequested`，即使存在编译错误也应完成临时代码清理并生成注明“编译未通过/未验证”的报告。
> 默认值为：Keil `C:\Keil_v5\UV4\UV4.exe`、串口 `COM1/256000/8N1`、
> 下载器 `JLink/COM1`；工程路径和工程文件由扫描结果直接填入，用户只需按实际硬件修改其他参数。

串口号变更是高频操作，无需重跑 `--init`，直接用 `--set-port` 快捷修改（多工程用 `--project-index` 指定下标）：

```bash
# 快速改第 0 个工程的串口
python scripts/config_reader.py --set-port COM20
# 改第 1 个工程的串口
python scripts/config_reader.py --set-port COM21 --project-index 1
```
