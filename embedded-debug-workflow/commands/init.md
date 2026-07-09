# /kzl 初始化 — 初始化调试配置

> 此命令处理 `/kzl 初始化` 和 `/kzl init`。
> 参数 `$1` 为项目目录路径，为空则默认为当前工作目录。

---

## 执行步骤

### Step 1: 确认工作区目录

```yaml
type: ask_user
question: 要初始化的「工作区」目录是？（配置文件将生成在 {工作区}/.copilot/ 下）
default: $PWD
```

> 配置为**工作区级**：`{工作区}/.copilot/embedded-debug-config.json`，存放各工程的
> 路径 ↔ 串口 ↔ 下载器 对应关系。调试报告/日志则写入各自 `{项目目录}/.copilot/`。

### Step 2: 运行 config_reader.py --init

```yaml
type: run_script
script: python "{skill_dir}/scripts/config_reader.py" --init "{project_dir}"
说明: 自动扫描 Keil 工程 → 逐工程采集串口与下载器 → 在工作区 .copilot/ 生成配置
```

运行后脚本会交互式采集：
1. **工程选择** — 自动扫描 `.uvprojx`，用户选择采用哪些
2. **串口参数** — 端口号、波特率、数据位、停止位、校验位
3. **下载器信息** — 类型（JLink/ST-Link）、串口号（COM，而非序列号）
4. （每个工程独立采集，建立工程路径 ↔ 串口 ↔ 下载器 的对应）

### Step 3: 验证配置生成

```yaml
type: check_file
path: "{project_dir}/.copilot/embedded-debug-config.json"
on_success: ✅ 配置已生成，可以开始调试
on_failure: ⚠️ 配置未生成，请检查脚本输出
```

---

## 完成后

*停止执行后续功能*并告知用户初始化完成，并提示可以直接描述故障现象进入调试流程。
