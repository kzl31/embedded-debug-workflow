# /kzl 初始化 — 初始化调试配置

> 此命令处理 `/kzl 初始化` / `/kzl 初始化` 和 `/kzl init`。
> 参数 `$1` 为工作区目录路径；为空时必须直接使用当前 VS Code 工作区根目录，禁止询问路径。
> 此命令是独立快捷命令，不启动、不检查、不推进工作流引擎。

---

## 执行步骤

### Step 1: 确定工作区目录（不询问）

```yaml
action: resolve_workspace
规则:
  - 用户提供目录参数：使用该目录
  - 用户未提供目录参数：使用当前 VS Code 工作区根目录
  - 多根工作区：使用当前活动文件所属的工作区根目录；仍无法确定时才请用户选择
```

> 配置为**工作区级**：`{工作区}/.copilot/embedded-debug-config.json`，存放各工程的
> 路径 ↔ 串口 ↔ 下载器 对应关系。调试报告/日志则写入各自 `{项目目录}/.copilot/`。

### Step 2: 直接运行初始化脚本

```yaml
action: run_script
call: python "{skill_dir}/scripts/config_reader.py" --init "{workspace_dir}"
说明: 每次都扫描当前工作区中的 .uvprojx/.uvproj；已有配置时保留参数并合并新工程
```

运行后脚本会自动执行：
1. 输出“正在扫描”和扫描完成数量，确保扫描过程可见
2. 递归扫描当前工作区中的 `.uvprojx` / `.uvproj`（扩展名大小写不敏感）
3. 同目录同名工程同时存在两种格式时优先采用 `.uvprojx`
4. 按发现的实际工程生成 `name`、`dir`、`file`
5. 已有配置时保留串口、下载器等人工配置，只追加新发现的工程
6. 新工程的 Keil 路径、串口 256000/8N1、JLink、COM 等属性使用默认值
7. 若未发现 Keil 工程则停止，并明确告知扫描目录和没有可初始化项目

需要只检查扫描结果而不写配置时，可运行：

```yaml
action: run_script
call: python "{skill_dir}/scripts/config_reader.py" --scan "{workspace_dir}"
```

## 完成后

*停止执行后续功能*并报告配置文件路径和发现的工程列表；不自动进入流程。
